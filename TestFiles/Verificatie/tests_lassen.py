# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Lassen (stap S4a): transient thermisch met een bewegende bron (Mecway T31 ->
ther_3d, THER_LINEAIRE / THER_NON_LINE; bron via #ASTER-LASBRON,
bridge_welding.py, of als Mecway-formule in x, y, z, t).

Referenties:
  Rosenthal, D. (1946). The theory of moving sources of heat and its
  application to metal treatments. Transactions ASME 68, 849-866.
  Quasi-stationaire puntbron Q op een half-oneindig lichaam met
  geisoleerd oppervlak, snelheid v in +x:
      T - T0 = Q / (2 pi k R) * exp(-v (R + xi) / (2 a)),
      xi = x - v t (t.o.v. de bron), R = afstand tot de bron, a = k/(rho c).
  Goldak, J., Chakravarti, A. & Bibby, M. (1984). A new finite element
  model for welding heat sources. Metallurgical Transactions B 15, 299-305
  (dubbel-ellipsoide; over de halve ruimte integraal Q).
  Energiebalans (geisoleerd): int rho c (T - T0) dV = Q t.

Model WE-01/02/03/05: halve plaat (symmetrievlak y = 0, Q/2 in het mesh),
55 x 15 x 15 mm, hex8 met 0,5 mm langs de baan en tot 7 mm ervan; bron
r = 0,75 mm (halve Gauss-bol) of Goldak 1/2/1/1 mm; v = 5 mm/s over 30 mm
in 6 s. Pe = v L/(2a) groot: de randen (15 mm) spelen niet mee
(exp(-v R/(2a)) < 3e-3 op 15 mm). Controlepunten liggen op knopen (_snap).
"""
import math
from verif_lib import Case, Check, Model, hexmesh

GROUP = "Lassen"

K, RHO, CP = 30.0, 7800.0, 600.0            # W/m/K, kg/m3, J/kg/K
A = K / (RHO * CP)                           # m2/s
QW = 1000.0                                  # W (eta * Q, hele bron)
V = 0.005                                    # m/s
X0 = 0.010                                   # start van de baan [m]
TEND = 6.0                                   # s
T0 = 293.15                                  # K


def _axis(pieces):
    """Knoopcoordinaten uit stukken (begin, eind, aantal elementen)."""
    out = [pieces[0][0]]
    for a, b, n in pieces:
        out += [a + (b - a) * (i + 1) / float(n) for i in range(n)]
    return out


def _graded(fine_to, h, end, n):
    """0 .. fine_to met stap h, daarna n elementen geometrisch tot end."""
    pts = [i * h for i in range(int(round(fine_to / h)) + 1)]
    # groeifactor g: h g + h g^2 + ... + h g^n = end - fine_to
    lo, hi = 1.0, 3.0
    for _ in range(80):
        g = 0.5 * (lo + hi)
        s = sum(h * g ** (k + 1) for k in range(n))
        if s > end - fine_to:
            hi = g
        else:
            lo = g
    x = fine_to
    for k in range(n):
        x += h * g ** (k + 1)
        pts.append(x)
    pts[-1] = end
    return pts


# Raster: 0,5 mm in x langs de baan (8..44 mm) en in y/z tot 7 mm van de
# baan, daarna 5 elementen geometrisch tot 15 mm (35 600 knopen).
H = 0.0005
XS = _axis([(0.0, 0.008, 8), (0.008, 0.044, 72), (0.044, 0.055, 8)])
YS = _graded(0.007, H, 0.015, 5)
ZS = [-z for z in reversed(_graded(0.007, H, 0.015, 5))]


def _grid(xs, ys, zs):
    def f(u, v, w):
        def pick(arr, s):
            i = s * (len(arr) - 1)
            k = int(math.floor(i + 1e-9))
            if k >= len(arr) - 1:
                return arr[-1]
            return arr[k] + (arr[k + 1] - arr[k]) * (i - k)
        return (pick(xs, u), pick(ys, v), pick(zs, w))
    return f


def _plate(m, tempdep=None):
    m.elset("Plaat", "Staal")
    g = hexmesh(m, "Plaat", len(XS) - 1, len(YS) - 1, len(ZS) - 1,
                _grid(XS, YS, ZS))
    lines = ['<density type="Simple" density="%g kg/m³" />' % RHO]
    if tempdep:
        rows = "".join('<thermalconductivity temp="%g K" value="%g W/m/K" />'
                       % tv for tv in tempdep[0])
        rows += "".join('<specificheat temp="%g K" value="%g J/kg/K" />'
                        % tv for tv in tempdep[1])
        lines.append('<thermal type="TempDependent" thermalconductivity='
                     '"%g W/m/K" specificheat="%g J/kg/K">%s</thermal>'
                     % (K, CP, rows))
    else:
        lines.append('<thermal type="Isotropic" thermalconductivity='
                     '"%g W/m/K" specificheat="%g J/kg/K" />' % (K, CP))
    m.mat("Staal", *lines)
    m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
    m.add(u'<initialconditions>\n    <temperature2 selection="Alle"><value>'
          u'%.12g K</value><starttime>0 s</starttime><endtime>0 s</endtime>'
          u'</temperature2>\n  </initialconditions>' % T0)
    return g


def build_we(source, dt=0.15, tempdep=None):
    """source: tekst van de #ASTER-LASBRON-regels (zonder voorvoegsel)."""
    def build():
        m = Model("T31", timesteps={"timeperiod": "%g s" % TEND,
                                    "stepsize": "%g s" % dt})
        _plate(m, tempdep)
        m.add(u"<ccxmodeldefinition>%s</ccxmodeldefinition>" % "\n".join(
            u"** ASTER-LASBRON " + line for line in source))
        return m
    return build


SRC_GAUSS = ["Q=%g, v=%g, start=(%g, 0, 0), richting=(1, 0, 0)"
             % (QW, V, X0),
             "r=0.00075, symmetrie=1"]
SRC_GOLDAK = ["Q=%g, eta=0.8, v=%g, start=(%g, 0, 0), richting=(1, 0, 0)"
              % (QW / 0.8, V, X0),
              "af=0.001, ar=0.002, b=0.001, c=0.001, symmetrie=1"]


def rosenthal(p, t=TEND, q=QW):
    """T - T0 van de puntbron (Rosenthal 1946) in punt p op tijd t."""
    xs = X0 + V * t
    xi = p[0] - xs
    r = math.sqrt(xi ** 2 + p[1] ** 2 + p[2] ** 2)
    return q / (2.0 * math.pi * K * r) * math.exp(-V * (r + xi) / (2.0 * A))


def goldak_exact(p, af, ar, b, c, t=TEND, q=QW, n=4000):
    """
    T - T0 van de bewegende Goldak-bron (vermogen q = eta Q, ff = 2 af/(af
    + ar), fr = 2 ar/(af + ar)) op een geisoleerd half-oneindig lichaam,
    aan vanaf t = 0 in x = X0: de bronfunctie gevouwen met de Green-functie
    van de warmtevergelijking (Carslaw & Jaeger 1959),
        T = 1/(rho c) int_0^t int q(r', t - tau) G(r - r', tau) dr' dtau,
    G = (4 pi a tau)^(-3/2) exp(-|r - r'|^2/(4 a tau)); het oppervlak z = 0
    als spiegelvlak (geisoleerd). In y en z is de vouwing van twee Gauss-
    krommen exact (variantie b^2/6 + 2 a tau), in x per halve Gauss-kromme
    met erf. Over tau numeriek (middelpuntregel in u = sqrt(tau)).
    Onafhankelijk van de bridge: controleert de bronvorm in de .comm.
    """
    ff, fr = 2.0 * af / (af + ar), 2.0 * ar / (af + ar)
    c0 = 6.0 * math.sqrt(3.0) * q / (b * c * math.pi ** 1.5)

    def half(xx, var, a_, f_, sign):
        al = 3.0 / a_ ** 2
        s2 = 1.0 / (2.0 * al + 1.0 / var)
        m = xx * s2 / var
        return (f_ / a_) * math.exp(-xx * xx * al / (1.0 + 2.0 * al * var)) \
            * math.sqrt(s2) * math.sqrt(math.pi / 2.0) * \
            (1.0 + sign * math.erf(m / math.sqrt(2.0 * s2)))

    total = 0.0
    umax = math.sqrt(t)
    for i in range(n):
        u = (i + 0.5) / n * umax
        tau = u * u
        var = 2.0 * A * tau
        xx = p[0] - (X0 + V * (t - tau))
        ix = (half(xx, var, af, ff, 1.0) + half(xx, var, ar, fr, -1.0)) / \
            math.sqrt(2.0 * math.pi * var)
        vb, vc = b * b / 6.0, c * c / 6.0
        iy = math.sqrt(vb / (vb + var)) * math.exp(-p[1] ** 2 /
                                                   (2.0 * (vb + var)))
        iz = math.sqrt(vc / (vc + var)) * math.exp(-p[2] ** 2 /
                                                   (2.0 * (vc + var)))
        total += c0 * ix * iy * iz * 2.0 * u * umax / n
    return total / (RHO * CP)


# Controlepunten (xi, y, z) t.o.v. de bron op t = 6 s: naast, achter,
# onder en schuin achter; buiten de bron (R >= 4 r).
POINTS = [(0.0, 0.003, 0.0), (0.0, 0.005, 0.0), (-0.003, 0.003, 0.0),
          (-0.006, 0.0, 0.0), (0.0, 0.0, -0.003), (-0.005, 0.002, -0.002)]


def _snap(p):
    """Het rasterpunt (knoop) het dichtst bij p: de referentie wordt in de
    knoop zelf berekend (een verschuiving van 0,1 mm geeft bij de steile
    gradient naast de bron al ~5%)."""
    return tuple(min(axis, key=lambda c: abs(c - p[i]))
                 for i, axis in enumerate((XS, YS, ZS)))


def _rosenthal_checks(tol=0.05, points=POINTS):
    out = []
    xs = X0 + V * TEND
    for xi, y, z in points:
        p = _snap((xs + xi, y, z))
        out.append(Check(
            "T-T0 xi=%g y=%g z=%g mm" % (xi * 1e3, y * 1e3, z * 1e3),
            (lambda p_: lambda r: r.at("temperature", p_) - T0)(p),
            ref=rosenthal(p), tol=tol, unit="K",
            source="Rosenthal (1946), puntbron op half-oneindig lichaam: "
                   "Q/(2 pi k R) exp(-v (R + xi)/(2a)), Q = %g W" % QW))
    return out


def _goldak_checks(af, ar, b, c, tol=0.02, points=POINTS):
    out = []
    xs = X0 + V * TEND
    for xi, y, z in points:
        p = _snap((xs + xi, y, z))
        out.append(Check(
            "T-T0 xi=%g y=%g z=%g mm (Goldak)" % (xi * 1e3, y * 1e3, z * 1e3),
            (lambda p_: lambda r: r.at("temperature", p_) - T0)(p),
            ref=goldak_exact(p, af, ar, b, c), tol=tol, unit="K",
            source="Goldak-bron %g/%g/%g/%g mm gevouwen met de Green-functie "
                   "(goldak_exact; Green-functie, Carslaw & Jaeger 1959)"
                   % (af * 1e3, ar * 1e3, b * 1e3, c * 1e3)))
    return out


# ------------------------------------------------------------------
# Energie uit de knooptemperaturen (hex8-blokken, trilineair)
# ------------------------------------------------------------------
_GP = (0.5 - 0.5 / math.sqrt(3.0), 0.5 + 0.5 / math.sqrt(3.0))


def _enthalpy_fn(cp_table):
    """H(T) - H(T0) per kg voor een cp-tabel [(T in K, cp)] (lineair
    geinterpoleerd, buiten de tabel constant: Mecway manual par. 8.6)."""
    if cp_table is None:
        return lambda t: CP * (t - T0)
    pts = sorted(cp_table)

    def cp(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
            if t <= t1:
                return c0 + (c1 - c0) * (t - t0) / (t1 - t0)
        return pts[-1][1]

    def h(t, n=64):
        lo, hi, sgn = (T0, t, 1.0) if t >= T0 else (t, T0, -1.0)
        step = (hi - lo) / n
        return sgn * sum(cp(lo + (k + 0.5) * step) for k in range(n)) * step
    return h


def _energy(r, time=None, cp_table=None, rho=RHO):
    """int rho (H(T) - H(T0)) dV over het mesh: per hex8-blok 2x2x2
    Gauss-punten met de trilineaire temperatuur (zelfde integratie als
    Code-Aster voor HEXA8). Constante cp: rho cp (T - T0), exact met het
    gemiddelde van de hoekknopen."""
    temps = r.step(time)["temperature"]
    nodes = r.model.nodes
    h = _enthalpy_fn(cp_table)
    total = 0.0
    for _name, _mat, elems in r.model.elsets:
        for _eid, _shape, nids, _a in elems:
            pts = [nodes[n - 1] for n in nids]
            vol = abs((pts[1][0] - pts[0][0]) * (pts[3][1] - pts[0][1]) *
                      (pts[4][2] - pts[0][2]))
            tn = [temps[n] for n in nids]
            if cp_table is None:
                total += vol * sum(t - T0 for t in tn) / 8.0
                continue
            for u in _GP:
                for v in _GP:
                    for w in _GP:
                        wts = [(1 - u) * (1 - v) * (1 - w),
                               u * (1 - v) * (1 - w), u * v * (1 - w),
                               (1 - u) * v * (1 - w), (1 - u) * (1 - v) * w,
                               u * (1 - v) * w, u * v * w, (1 - u) * v * w]
                        t = sum(a * b for a, b in zip(wts, tn))
                        total += vol / 8.0 * h(t)
    return rho * (CP * total if cp_table is None else total)


def _energy_check(t=TEND, q=QW, tol=0.02, cp_table=None):
    return Check("energie t=%g s" % t,
                 lambda r: _energy(r, t, cp_table),
                 ref=0.5 * q * t, tol=tol, unit="J",
                 source="energiebalans, geisoleerd: int rho (H(T) - H(T0)) "
                        "dV = Q t (halve plaat: Q/2)")


def _power_check(q=QW, tol=0.005):
    """Energiecontrole van de job (bridge_welding._energy_block, regels
    BRIDGE_LASBRON in de .mess): kleinste opgenomen vermogen."""
    def value(r):
        import sys
        from verif_lib import SCRIPTS
        if SCRIPTS not in sys.path:
            sys.path.insert(0, SCRIPTS)
        import bridge_welding
        rows = bridge_welding.read_energy(r.mess)[1]
        return min(p for _t, p, _q in rows)
    return Check("opgenomen vermogen (job)", value, ref=0.5 * q, tol=tol,
                 unit="W", in_series=False,
                 source="BRIDGE_LASBRON in de .mess: som van de knooplasten "
                        "(CALC_VECT_ELEM CHAR_THER) = Q/2")


# ------------------------------------------------------------------
# Mecway-formule (heat generation in x, y, z, t) in plaats van
# #ASTER-LASBRON: dezelfde halve Gauss-bol als WE-01
# ------------------------------------------------------------------
R_G = 0.00075
C_G = 6.0 * math.sqrt(3.0) * QW / (math.pi ** 1.5 * R_G ** 3)   # W/m3
FORMULA_G = ("%.10g*e^(-3*((x-%g-%g*t)^2+y^2+z^2)/%g^2)"
             % (C_G, X0 * 1e3, V * 1e3, R_G * 1e3))           # x in mm


def build_we_formula(dt=0.05):
    def build():
        m = Model("T31", timesteps={"timeperiod": "%g s" % TEND,
                                    "stepsize": "%g s" % dt})
        _plate(m)
        # Elementen binnen 3 r van de baan (zoals de automatische
        # brongroep van #ASTER-LASBRON)
        lim = 3.0 * R_G + 0.0006
        eids = []
        for _n, _m, els in m.elsets:
            for eid, _s, nids, _a in els:
                cen = [sum(m.nodes[n - 1][k] for n in nids) / 8.0
                       for k in range(3)]
                if math.hypot(cen[1], cen[2]) < lim and \
                        X0 - lim < cen[0] < X0 + V * TEND + lim:
                    eids.append(eid)
        m.element_selection("Rups", eids)
        m.add(u'<heatgeneration selection="Rups"><value unit="W/m³" '
              u'timeunit="s" positionunit="mm">%s</value></heatgeneration>'
              % FORMULA_G)
        return m
    return build


# ------------------------------------------------------------------
# Temperatuurafhankelijke lambda en cp (Mecway TempDependent)
# ------------------------------------------------------------------
LB, AB = 0.1, 0.01                      # staaf 100 x 10 x 10 mm
K_T = [(300.0, 20.0), (1300.0, 40.0)]   # W/m/K, lineair in T
CP_T = [(300.0, 450.0), (800.0, 600.0), (1300.0, 750.0)]


def _bar(m, n, k_table, cp_table, length=LB):
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", n, 1, 1, _grid(
        [length * i / float(n) for i in range(n + 1)], [0.0, AB],
        [0.0, AB]))
    rows = "".join('<thermalconductivity temp="%g K" value="%g W/m/K" />'
                   % tv for tv in k_table)
    rows += "".join('<specificheat temp="%g K" value="%g J/kg/K" />'
                    % tv for tv in cp_table)
    m.mat("Staal", '<density type="Simple" density="%g kg/m³" />' % RHO,
          '<thermal type="TempDependent" thermalconductivity="%g W/m/K" '
          'specificheat="%g J/kg/K">%s</thermal>' % (K, CP, rows))
    return g


def build_we04a():
    """Stationair: T(0) = 300 K, T(L) = 1300 K, lambda(T) lineair."""
    m = Model("T30")
    g = _bar(m, 20, K_T, CP_T)
    m.node_selection("Links", sorted(g["nodes"]["u0"]))
    m.node_selection("Rechts", sorted(g["nodes"]["u1"]))
    for sel, t in (("Links", 300.0), ("Rechts", 1300.0)):
        m.add('<temperature2 selection="%s"><value>%g K</value><starttime>'
              '0 s</starttime><endtime>0 s</endtime></temperature2>'
              % (sel, t))
    return m


def kirchhoff_t(x):
    """Stationair 1D met lambda = 20 + 0.02 (T - 300): F(T) = int lambda dT
    is lineair in x (Kirchhoff-transformatie; Carslaw & Jaeger 1959)."""
    f = (20.0 * 1000.0 + 0.01 * 1000.0 ** 2) * x / LB
    u = (-20.0 + math.sqrt(400.0 + 0.04 * f)) / 0.02
    return 300.0 + u


QF, TQ = 1.0e7, 2.0                     # W/m2 op x = 0, s
LB2 = 0.02


def build_we04b(dt=0.02):
    """Transient: staaf 20 mm, geisoleerd, flux QF op x = 0 gedurende TQ."""
    def build():
        m = Model("T31", timesteps={"timeperiod": "%g s" % TQ,
                                    "stepsize": "%g s" % dt})
        g = _bar(m, 40, [(300.0, 50.0), (1300.0, 25.0)], CP_T, length=LB2)
        m.face_selection("Warm", g["faces"]["u0"])
        m.add('<heatflux selection="Warm"><value>%g W/m²</value></heatflux>'
              % QF)
        m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
        m.add(u'<initialconditions>\n    <temperature2 selection="Alle">'
              u'<value>%.12g K</value><starttime>0 s</starttime><endtime>'
              u'0 s</endtime></temperature2>\n  </initialconditions>' % T0)
        return m
    return build


def _bar_energy(r, time, cp_table):
    temps = r.step(time)["temperature"]
    h = _enthalpy_fn(cp_table)
    total = 0.0
    for _name, _mat, elems in r.model.elsets:
        for _eid, _shape, nids, _a in elems:
            pts = [r.model.nodes[n - 1] for n in nids]
            vol = abs((pts[1][0] - pts[0][0]) * AB * AB)
            ta = sum(temps[n] for n in (nids[0], nids[3], nids[4],
                                        nids[7])) / 4.0
            tb = sum(temps[n] for n in (nids[1], nids[2], nids[5],
                                        nids[6])) / 4.0
            for u in _GP:
                total += vol / 2.0 * h(ta + (tb - ta) * u)
    return RHO * total


# Mecway 33 headless (TestFiles/Tools/mw_solve.py, interne solver) op
# modellen/WE-*.liml, 7 okt 2026: temperatuur [K] in de genoemde punten.
MECWAY = {
    # stationair: Mecway = Kirchhoff tot 1e-11 (ook x = 25 en 75 mm)
    "WE-04a": {"T x=L/2": 881.1388300826047},
    # Mecway's energiebalans: -0,34% (t = 1 s) / -0,22% (t = 2 s)
    "WE-04b": {"T x=0 t=2": 1623.686482291939,
               "T x=2 mm t=2": 1017.046827563669,
               "T x=0 t=1": 1196.7871367924536},
    # 244 s; energie uit Mecway's knooptemperaturen (_energy): 3001,76 J,
    # gelijk aan de bridge (zelfde Gauss-integratie van de formule).
    # Temperaturen: Mecway rekent de last op het einde van de stap
    # (KNOWN_BUGS 14), de bron loopt dan v dt/2 = 0,125 mm voor: naast de
    # bron exp(v d/(2a)) = +5%, Mecway ligt binnen 1,5% van de analytische
    # oplossing op t + dt/2.
    "WE-03": {"T xi=0 y=3": 867.3021212605198,
              "T xi=-6 y=0": 1150.954887788228,
              "energie": 3001.761318650116},
}


def _mecway_checks(case_id, points, tol):
    out = []
    for name, p, time in points:
        ref = MECWAY.get(case_id, {}).get(name)
        if ref is None:
            continue
        out.append(Check(
            "Mecway " + name,
            (lambda p_, t_: lambda r: r.at("temperature", p_, time=t_))(
                p, time),
            ref=ref, tol=tol, unit="K", in_series=False,
            source="Mecway 33 headless (mw_solve.py, interne solver), "
                   "zelfde .liml"))
    return out


WE03_MW = [("T xi=0 y=3", _snap((X0 + V * TEND, 0.003, 0.0)), TEND),
           ("T xi=-6 y=0", _snap((X0 + V * TEND - 0.006, 0.0, 0.0)), TEND)]
WE04B_MW = [("T x=0 t=2", (0.0, 0.0, 0.0), TQ),
            ("T x=2 mm t=2", (0.002, 0.0, 0.0), TQ),
            ("T x=0 t=1", (0.0, 0.0, 0.0), 1.0)]
WE04A_MW = [("T x=L/2", (LB / 2, 0.0, 0.0), None)]

TESTS = [
    Case("WE-01", GROUP, "Bewegende Gauss-bron (r = 0,75 mm), Rosenthal",
         "ther_3d", build_we(SRC_GAUSS, dt=0.05),
         _rosenthal_checks() + [_energy_check(), _power_check()],
         note="#ASTER-LASBRON r = 0,75 mm, symmetrie = 1; hex8 0,5 mm "
              "langs de baan; dt = 0,05 s (v dt = (af+ar)/6)"),
    Case("WE-01b", GROUP, "Idem, dt = 0,15 s (v dt = (af+ar)/2, grens)",
         "ther_3d", build_we(SRC_GAUSS, dt=0.15),
         _rosenthal_checks() + [_energy_check()],
         note="de grens van de tijdstapmelding (bridge_welding.MAX_JUMP)"),
    Case("WE-02", GROUP, "Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8",
         "ther_3d", build_we(SRC_GOLDAK, dt=0.1),
         _goldak_checks(0.001, 0.002, 0.001, 0.001) +
         [_energy_check(), _power_check()],
         note="Q = 1250 W, eta = 0,8; dt = 0,1 s (v dt = (af+ar)/6); "
              "referentie: dezelfde bron analytisch gevouwen"),
    Case("WE-03", GROUP, "Gauss-bron als Mecway-formule (heat generation)",
         "ther_3d", build_we_formula(),
         _rosenthal_checks() + _goldak_checks(R_G, R_G, R_G, R_G) +
         [_energy_check(),
          Check("Mecway energie t=6 s", lambda r: _energy(r, TEND),
                ref=MECWAY["WE-03"]["energie"], tol=1e-4, unit="J",
                in_series=False,
                source="Mecway 33 headless (mw_solve.py, interne solver), "
                       "zelfde .liml: int rho c (T - T0) dV")] +
         _mecway_checks("WE-03", WE03_MW, 0.06),
         note="heatgeneration op een elementselectie met de formule in "
              "x, y, z (mm) en t; zelfde bron als WE-01"),
    Case("WE-04a", GROUP, "Temperatuurafhankelijke lambda, stationair",
         "ther_3d", build_we04a,
         [Check("T x=%g mm" % (x * 1e3),
                (lambda x_: lambda r: r.at("temperature", (x_, 0, 0)))(x),
                ref=kirchhoff_t(x), tol=1e-4, unit="K",
                source="Kirchhoff-transformatie, lambda lineair in T "
                       "(Carslaw & Jaeger 1959); nodaal exact")
          for x in (0.025, 0.05, 0.075)] +
         _mecway_checks("WE-04a", WE04A_MW, 0.001),
         note="Mecway TempDependent -> THER_NL, THER_NON_LINE"),
    Case("WE-04b", GROUP, "Temperatuurafhankelijke lambda en cp, transient",
         "ther_3d", build_we04b(),
         [Check("energie t=%g s" % t,
                (lambda t_: lambda r: _bar_energy(r, t_, CP_T))(t),
                ref=QF * AB * AB * t, tol=0.005, unit="J",
                source="energiebalans, geisoleerd: int rho H(T) dV = q A t")
          for t in (1.0, TQ)] +
         _mecway_checks("WE-04b", WE04B_MW, 0.02),
         note="flux 1e7 W/m2 op x = 0; cp(T) 450..750 J/kg/K"),
    Case("WE-05", GROUP, "Goldak-bron met temperatuurafhankelijke lambda en cp",
         "ther_3d", build_we(SRC_GOLDAK, dt=0.1,
                             tempdep=([(293.15, 30.0), (1800.0, 20.0)],
                                      CP_T)),
         [_energy_check(cp_table=CP_T), _power_check()],
         note="lasbron + THER_NON_LINE; energiebalans met de enthalpie"),
]


# ------------------------------------------------------------------
# WE-06: formules in x, y, z in andere thermische lasten (voorheen KNOWN_BUGS 45)
# ------------------------------------------------------------------
def build_we06():
    """Staaf 100 x 10 x 10 mm (20 x 2 x 2 hex8), stationair: temperatuur
    links 100 + y [graden C, y in mm], convectie rechts h = 25 (1 + 100 y)
    [y in m] naar 300 K, flux boven 1000 x [W/m2, x in mm]."""
    m = Model("T30")
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 20, 2, 2, _grid(
        [0.005 * i for i in range(21)], [0.0, 0.005, 0.01],
        [0.0, 0.005, 0.01]))
    m.mat("Staal", '<density type="Simple" density="%g kg/m³" />' % RHO,
          '<thermal type="Isotropic" thermalconductivity="%g W/m/K" '
          'specificheat="%g J/kg/K" />' % (K, CP))
    m.node_selection("Links", sorted(g["nodes"]["u0"]))
    m.face_selection("Rechts", g["faces"]["u1"])
    m.face_selection("Boven", g["faces"]["w1"])
    m.add(u'<temperature2 selection="Links"><value unit="°C" timeunit="s" '
          u'positionunit="mm">100+y</value><starttime>0 s</starttime>'
          u'<endtime>0 s</endtime></temperature2>')
    m.add(u'<convectionbc selection="Rechts"><ambienttemp>300 K</ambienttemp>'
          u'<coefficient unit="W/m²/K" timeunit="s" positionunit="m">'
          u'25*(1+100*y)</coefficient></convectionbc>')
    m.add(u'<heatflux selection="Boven"><value unit="W/m²" timeunit="s" '
          u'positionunit="mm">1000*x</value></heatflux>')
    return m


# Mecway 33 headless (mw_solve.py, interne solver) op modellen/WE-06.liml,
# 7 okt 2026; grootste verschil over alle knopen 7e-12 K.
WE06_MW = [((0.0, 0.01, 0.0), 383.15), ((0.05, 0.005, 0.01),
                                        1081.1841582558877),
           ((0.1, 0.0, 0.0), 1352.2313809418197),
           ((0.1, 0.01, 0.01), None)]

TESTS.append(Case(
    "WE-06", GROUP, "Formules in x, y, z: temperatuur, convectie, flux",
    "ther_3d", build_we06,
    [Check("T (%g, %g, %g) mm" % tuple(c * 1e3 for c in p),
           (lambda p_: lambda r: r.at("temperature", p_))(p),
           ref=ref, tol=1e-9, unit="K", in_series=False,
           source="Mecway 33 headless (mw_solve.py, interne solver), "
                  "zelfde .liml")
     for p, ref in WE06_MW if ref is not None],
    note="TEMP_IMPO, ECHANGE COEF_H en FLUX_REP FLUN als FORMULE van X, Y, "
         "Z; eenheden mm/m/graden C uit de attributen"))
