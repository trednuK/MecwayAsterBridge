# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Dynamica (Mecway D31 -> DYNA_NON_LINE; dyna_impl_3d met HHT/NEWMARK en
dyna_expl_3d met DIFF_CENT). Referenties: analytische oplossingen van een
massa-veersysteem, een Euler-Bernoulli-balk en een 1D-staafgolf, en de
periodefout van het tijdschema (Hughes, "The Finite Element Method", 2000,
par. 9.3; Hilber, Hughes & Taylor 1977). Toelichting: doc_dynamisch.md.
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, quadmesh, box, \
    rect

GROUP = "Dynamica"


# ==========================================
# HULPFUNCTIES (tijdreeksen [(t, waarde)])
# ==========================================
def crossings(hist, level=0.0, t_min=0.0):
    """Tijden waarop de reeks level kruist (lineair geinterpoleerd)."""
    out = []
    for (t0, u0), (t1, u1) in zip(hist, hist[1:]):
        if t0 < t_min:
            continue
        a, b = u0 - level, u1 - level
        if (a < 0.0 <= b) or (a > 0.0 >= b):
            out.append(t0 + (t1 - t0) * a / (a - b))
    return out


def period(hist, level=0.0, t_min=0.0):
    """
    Periode uit de kruisingen van level: kleinste-kwadratenlijn door de
    kruistijden tegen het nummer van de halve periode. Zo middelen
    bemonsteringsfouten en een storing door hogere eigenmodes uit.
    """
    cr = crossings(hist, level, t_min)
    if len(cr) < 3:
        raise ValueError("te weinig kruisingen (%d)" % len(cr))
    n = len(cr)
    xm, ym = (n - 1) / 2.0, sum(cr) / n
    sxy = sum((i - xm) * (t - ym) for i, t in enumerate(cr))
    sxx = sum((i - xm) ** 2 for i in range(n))
    return 2.0 * sxy / sxx


def peak(hist, t_max=None):
    """Maximum met een parabool door het grootste monster en zijn buren
    (gelijke tijdstappen)."""
    pts = [p for p in hist if t_max is None or p[0] <= t_max]
    vals = [v for _t, v in pts]
    i = vals.index(max(vals))
    if i == 0 or i == len(vals) - 1:
        return vals[i]
    a, b, c = vals[i - 1], vals[i], vals[i + 1]
    den = a - 2.0 * b + c
    if den == 0.0:
        return b
    return b - 0.125 * (a - c) ** 2 / den


def mean_between(hist, t0, t1):
    """Gemiddelde van de monsters met t0 <= t <= t1."""
    vals = [v for t, v in hist if t0 <= t <= t1]
    return sum(vals) / len(vals)


def time_reaching(hist, level):
    """Eerste tijd waarop de reeks level bereikt (lineair
    geinterpoleerd)."""
    for (t0, u0), (t1, u1) in zip(hist, hist[1:]):
        if (u0 - level) * (u1 - level) <= 0.0 and u1 != u0:
            return t0 + (t1 - t0) * (level - u0) / (u1 - u0)
    raise ValueError("niveau %g niet bereikt" % level)


def _hht_par(schema, alpha):
    """(alpha, gamma, beta): Newmark = trapeziumregel (Code-Aster
    standaard beta=1/4, gamma=1/2, U4.53.01); HHT gamma = 1/2 - alpha,
    beta = (1 - alpha)^2 / 4 (Hughes par. 9.3.2, U2.06.13)."""
    if schema == "NEWMARK":
        return 0.0, 0.5, 0.25
    return alpha, 0.5 - alpha, (1.0 - alpha) ** 2 / 4.0


def _step(u, v, a, f1, f0, m, k, dt, al, g, b):
    """Een stap van HHT (al = 0: Newmark) voor m a + k u = f:
    m a1 + (1+al) k u1 - al k u0 = (1+al) f1 - al f0."""
    up = u + dt * v + dt * dt * (0.5 - b) * a
    a1 = ((1.0 + al) * f1 - al * f0 - k * u - (1.0 + al) * k * (up - u)) / \
        (m + (1.0 + al) * k * b * dt * dt)
    return up + b * dt * dt * a1, v + dt * ((1.0 - g) * a + g * a1), a1


def scheme_period_ratio(wdt, schema="NEWMARK", alpha=0.0):
    """
    (discrete periode / exacte periode, algoritmische dempingsverhouding)
    van een ongedempte 1-vrijheidsgraad bij w*dt: uit de complexe
    eigenwaarden van de versterkingsmatrix van het schema (Hughes par.
    9.3.1): T/T_exact = w dt / arg(lambda), xi = -ln|lambda| / arg(lambda).
    """
    al, g, b = _hht_par(schema, alpha)
    cols = [_step(e[0], e[1], e[2], 0.0, 0.0, 1.0, wdt ** 2, 1.0, al, g, b)
            for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    A = [[cols[j][i] for j in range(3)] for i in range(3)]
    tr = A[0][0] + A[1][1] + A[2][2]
    c1 = sum(A[i][i] * A[j][j] - A[i][j] * A[j][i]
             for i, j in ((0, 1), (0, 2), (1, 2)))
    det = (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) -
           A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0]) +
           A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))
    # lambda^3 - tr lambda^2 + c1 lambda - det = 0; de reele (spurieuze)
    # wortel ligt bij 0 (Newton), daarna lambda^2 + p lambda + q
    r = 0.0
    for _i in range(100):
        f = ((r - tr) * r + c1) * r - det
        df = (3.0 * r - 2.0 * tr) * r + c1
        r -= f / df
    p = r - tr
    q = c1 + r * p
    im = math.sqrt(q - p * p / 4.0)
    theta = math.atan2(im, -p / 2.0)
    return wdt / theta, -math.log(math.sqrt(q)) / theta


def sdof_response(dt, n, schema, alpha, m, k, f):
    """
    Verplaatsingen u_0..u_n van het schema voor m a + k u = f (staplast op
    t = 0, start uit rust), zoals Code-Aster 17.4 het rekent: beginversnelling
    uit het evenwicht op t = 0 (a_0 = f/m), en in de eerste HHT-stap
    f_0 = 0 in de term -alpha f_0. Dat laatste is gemeten (DY-01a: met
    f_0 = f wijkt de reeks 1,5% van de amplitude af, met f_0 = 0 1e-7),
    niet in de documentatie gevonden.
    """
    al, g, b = _hht_par(schema, alpha)
    u, v, a = 0.0, 0.0, f / m
    out = [u]
    for i in range(n):
        u, v, a = _step(u, v, a, f, f if i else 0.0, m, k, dt, al, g, b)
        out.append(u)
    return out


def modal_step_response(modes, dt, n, schema, alpha):
    """
    Staplast-respons sum c_i x_i(t) van ongekoppelde modes [(c_i, w_i)]
    (c_i = statische bijdrage), elke mode met het tijdschema
    (sdof_response). Voor een lineair systeem is dit exact wat het schema
    met die eigenmodes rekent. Returns [(t, u)].
    """
    tot = [0.0] * (n + 1)
    for c, w in modes:
        x = sdof_response(dt, n, schema, alpha, 1.0, w * w, w * w)
        for i in range(n + 1):
            tot[i] += c * x[i]
    return [(i * dt, tot[i]) for i in range(n + 1)]


def max_dev(hist, ref):
    """max |hist - ref| / max |ref| op dezelfde tijden (ref [(t, u)])."""
    if len(hist) != len(ref):
        raise ValueError("%d uitvoertijden, verwacht %d"
                         % (len(hist), len(ref)))
    for (t, _u), (tr, _r) in zip(hist, ref):
        if abs(t - tr) > 1e-6 * max(abs(tr), ref[1][0]):
            raise ValueError("uitvoertijd %g, verwacht %g" % (t, tr))
    return max(abs(u - r) for (_t, u), (_tr, r) in zip(hist, ref)) / \
        max(abs(r) for _t, r in ref)


# ==========================================
# DY-01 Massa-veersysteem onder een staplast
# ==========================================
K1 = 1000.0                         # N/m
T1 = 1.0                            # s, eigenperiode
M1 = K1 * T1 ** 2 / (4.0 * math.pi ** 2)
F1 = 10.0                           # N
U1 = F1 / K1                        # statische verplaatsing
W1 = 2.0 * math.pi / T1
N_PER1 = 5                          # gerekende perioden


def _timesteps(t_end, dt):
    return {"timeperiod": "%r s" % t_end, "automatictimestepping": "false",
            "outputtimes": "regular", "timepointsstart": "0 s",
            "timepointsincrement": "%r s" % dt}


def build_dy01(dt):
    def build():
        m = Model("D31", timesteps=_timesteps(N_PER1 * T1, dt))
        m.elset("Veer", "Veer")
        _e, nids = linemesh(m, "Veer", 1, (0, 0, 0), (1.0, 0, 0))
        m.mat("Veer", '<mechanical type="Spring" springconstant="%r N/m" />'
              % K1)
        m.node_selection("Grond", [nids[0]])
        m.node_selection("Massa", [nids[1]])
        m.add('<fixed selection="Grond" />')
        # massaknoop alleen vrij in X (Mecway: de component langs de
        # richting ligt vast, loodrecht blijft vrij)
        for d in ((0, 1, 0), (0, 0, 1)):
            m.add('<displacement selection="Massa"><value>0 m</value>'
                  '<x>%d</x><y>%d</y><z>%d</z></displacement>' % d)
        m.add('<mass2 selection="Massa"><value>%r kg</value></mass2>' % M1)
        m.add('<force selection="Massa"><x>%r N</x><y>0 N</y><z>0 N</z>'
              '</force>' % F1)
        return m
    return build




def _expected_tol(expected, ref, margin):
    """Tolerantie = 1,5 x de verwachte discretisatiefout (|expected - ref|
    / |ref|, uit een onafhankelijke berekening met hetzelfde schema) +
    margin, naar boven afgerond op 2 cijfers. Returns (tol, verwachte
    relatieve afwijking)."""
    dev = (expected - ref) / abs(ref)
    tol = 1.5 * abs(dev) + margin
    scale = 10.0 ** (math.floor(math.log10(tol)) - 1)
    return math.ceil(tol / scale - 1e-9) * scale, dev


def _dy01_checks(dt, schema, alpha):
    n = int(round(N_PER1 * T1 / dt))
    ref = [(i * dt, u) for i, u in enumerate(
        sdof_response(dt, n, schema, alpha, M1, K1, F1))]
    pt = (1, 0, 0)

    def per(h):
        return period(h, U1)

    def pk(h):
        return peak(h, t_max=T1)

    tol_t, dev_t = _expected_tol(per(ref), T1, 1e-3)
    tol_u, dev_u = _expected_tol(pk(ref), 2.0 * U1, 1e-3)
    ratio, _xi = scheme_period_ratio(W1 * dt, schema, alpha)
    return [
        Check("periode", lambda r: per(r.history("displx", pt)),
              ref=T1, tol=tol_t, unit="s",
              source="T = 2 pi sqrt(m/k); periodefout %s bij w dt = %.3f: "
                     "%+.2f%% (Hughes par. 9.3), verwacht in deze meting "
                     "%+.3f%%; tol = 1,5 x verwacht + 0,1%%"
                     % (schema, W1 * dt, 100 * (ratio - 1), 100 * dev_t)),
        Check("max. verplaatsing", lambda r: pk(r.history("displx", pt)),
              ref=2.0 * U1, tol=tol_u, unit="m",
              source="u = F/k (1 - cos wt), max 2 F/k (Clough & Penzien "
                     "par. 4-1); verwacht %+.3f%%; tol = 1,5 x verwacht + "
                     "0,1%%" % (100 * dev_u)),
        Check("verloop t.o.v. schema", lambda r: max_dev(
            r.history("displx", pt), ref), ref=0.0, tol_abs=1e-5, unit="-",
              source="max |u_FEM - u_schema| / max u_schema; u_schema = "
                     "dezelfde recursie in Python (sdof_response)"),
    ]


def _dy01(id_, title, dt, schema, alpha=0.0, series=None):
    settings = {"schema": schema}
    if schema == "HHT":
        settings["hht_alpha"] = alpha
    return Case(id_, GROUP, title, "dyna_impl_3d", build_dy01(dt),
                _dy01_checks(dt, schema, alpha), settings=settings,
                series=series, h=dt, timeout=600,
                note="Veer (line2, DIS_T K_T_D_L) + knoopmassa (POI1), "
                     "alleen X vrij; staplast vanaf t = 0.")


# ==========================================
# DY-02 Ingeklemde balk (POU_D_E), staplast op de tip, vrije trilling
# ==========================================
L2, D2, N2 = 1.0, 0.020, 20
E2, RHO2 = 210e9, 7850.0
A2 = math.pi * D2 ** 2 / 4.0
I2 = math.pi * D2 ** 4 / 64.0
F2 = 10.0


def _cantilever_roots(n):
    """Wortels van 1 + cos x cosh x = 0 (Blevins tabel 8-1); boven x = 30
    is (2i+1) pi/2 exact op 1e-12."""
    out = []
    for i in range(n):
        x = (2 * i + 1) * math.pi / 2.0
        while x < 30.0:
            dx = (1.0 + math.cos(x) * math.cosh(x)) / \
                (-math.sin(x) * math.cosh(x) + math.cos(x) * math.sinh(x))
            x -= dx
            if abs(dx) < 1e-14:
                break
        out.append(x)
    return out


# modes van de console: (c_i, w_i), c_i = 4 F L^3 / (E I lambda_i^4) (modes
# genormeerd op int phi^2 dx = L, dan phi_i(L) = 2); sum c_i = F L^3 / 3EI
MODES2 = [(4.0 * F2 * L2 ** 3 / (E2 * I2 * lam ** 4),
           lam ** 2 * math.sqrt(E2 * I2 / (RHO2 * A2 * L2 ** 4)))
          for lam in _cantilever_roots(30)]
W2 = MODES2[0][1]
T2 = 2.0 * math.pi / W2             # f1 = 1,875^2/(2 pi) sqrt(EI/(m L^4))
U2 = F2 * L2 ** 3 / (3.0 * E2 * I2)
N_PER2 = 6
DT2 = T2 / 40.0


def beam_tip_step(t):
    """Exacte tipverplaatsing (Euler-Bernoulli, modale superpositie):
    sum c_i (1 - cos w_i t)."""
    return sum(c * (1.0 - math.cos(w * t)) for c, w in MODES2)


def build_dy02():
    m = Model("D31", timesteps=_timesteps(N_PER2 * T2, DT2))
    m.elset("Balk", "Rond20")
    _e, nids = linemesh(m, "Balk", N2, (0, 0, 0), (L2, 0, 0))
    m.mat("Rond20", '<geometric type="CircularBar" roundod="20 mm" />',
          '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="0.3" />',
          u'<density type="Simple" density="7850 kg/m³" />')
    m.node_selection("Inklemming", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%r N</z></force>'
          % F2)
    return m


def _tip2(r):
    return [(t, -u) for t, u in r.history("displz", (L2, 0, 0))]


def _dy02_checks():
    n = int(round(N_PER2 * T2 / DT2))
    exp = modal_step_response(MODES2, DT2, n, "HHT", -0.1)
    peak_exact = max(beam_tip_step(T2 * i / 4000.0) for i in range(4001))
    tol_t, dev_t = _expected_tol(period(exp, U2), T2, 1e-3)
    tol_u, dev_u = _expected_tol(peak(exp, t_max=T2), peak_exact, 2e-3)
    ratio, _xi = scheme_period_ratio(W2 * DT2, "HHT", -0.1)
    return [
        Check("periode 1e mode", lambda r: period(_tip2(r), U2), ref=T2,
              tol=tol_t, unit="s",
              source="f1 = 1,875^2/(2 pi) sqrt(EI/(m L^4)) (Blevins tabel "
                     "8-1, Roark tabel 16.1); HHT %+.3f%% (1 mode), verwacht "
                     "met 30 modes %+.3f%%; tol = 1,5 x verwacht + 0,1%%"
                     % (100 * (ratio - 1), 100 * dev_t)),
        Check("max. doorbuiging tip", lambda r: peak(_tip2(r), t_max=T2),
              ref=peak_exact, tol=tol_u, unit="m",
              source="exact (modale superpositie, %.4f x F L^3/3EI); "
                     "verwacht met HHT %+.3f%%; tol = 1,5 x verwacht + 0,2%%"
                     % (peak_exact / U2, 100 * dev_u)),
        Check("verloop t.o.v. modaal schema", lambda r: max_dev(_tip2(r),
                                                                exp),
              ref=0.0, tol_abs=2e-3, unit="-",
              source="max |u_FEM - u_modaal| / max u; u_modaal = 30 exacte "
                     "modes, elk met HHT (modal_step_response); tol 0,2%: "
                     "meshfout hogere modes (20 elementen)"),
    ]


# ==========================================
# DY-03 Longitudinale golf in een ingeklemde staaf (hex8, nu = 0)
# ==========================================
L3, B3, NX3 = 1.0, 0.010, 100
E3, RHO3 = 210e9, 7850.0
A3 = B3 * B3
H3 = L3 / NX3
C3 = math.sqrt(E3 / RHO3)           # 1D-golfsnelheid (nu = 0: exact 1D)
TC3 = L3 / C3                       # looptijd over de staaf
F3 = 1000.0
V3 = 0.25                           # opgelegde snelheid [m/s]
DTO3, TEND3 = 5e-6, 6e-4            # expliciet: uitvoerinterval, eindtijd
T_IMPL3 = 4.0 * TC3                 # periode 1e mode staaf vast-vrij
DTI3, TENDI3 = 1e-5, 2.4e-3         # impliciet: dt ~ T/77


def bar_chain(times, nsub, implicit, alpha=0.0, force=0.0, velocity=None):
    """
    De staaf als 1D-keten van NX3 tweeknoopselementen (knoop 0 vast). Met
    nu = 0 en een doorsnede van 1 element is dat exact het hex8-model:
    trek/druk uniform over de doorsnede, stijfheid EA/h, massa van een
    hex8 = die van een staafelement (tensorproduct-vormfuncties).
      implicit: consistente massa, HHT (alpha) zoals sdof_response
                (a_0 uit het evenwicht, eerste stap f_0 = 0);
      anders  : diagonale massa, centrale differenties (Newmark beta = 0,
                gamma = 1/2, zoals DIFF_CENT, U2.06.13).
    times: uitvoertijden, nsub: rekenstappen per uitvoerinterval.
    velocity: opgelegde snelheid van het vrije eind (alleen expliciet).
    Returns [(t, {"tip": u_N, "vtip": v_N, "mid": u_N/2,
                  "smid": spanning midden (gemiddelde van de twee
                  elementen), "reac": E A u_1 / h})].
    """
    n = NX3
    k = E3 * A3 / H3
    me = RHO3 * A3 * H3
    al, g, b = _hht_par("HHT", alpha) if implicit else (0.0, 0.5, 0.0)
    f = [0.0] * n
    f[-1] = force

    def ku(u):
        out = []
        for j in range(n):
            left = u[j - 1] if j else 0.0
            if j < n - 1:
                out.append(k * (2.0 * u[j] - left - u[j + 1]))
            else:
                out.append(k * (u[j] - left))
        return out

    def solve(c, rhs):
        """(M + c K) x = rhs, tridiagonaal (Thomas); M consistent of
        diagonaal."""
        if implicit:
            d = [4.0 * me / 6.0 + 2.0 * c * k] * (n - 1) + \
                [2.0 * me / 6.0 + c * k]
            e = me / 6.0 - c * k
        else:
            d = [me + 2.0 * c * k] * (n - 1) + [me / 2.0 + c * k]
            e = -c * k
        cp, dp = [0.0] * n, [0.0] * n
        cp[0], dp[0] = e / d[0], rhs[0] / d[0]
        for j in range(1, n):
            den = d[j] - e * cp[j - 1]
            cp[j] = e / den
            dp[j] = (rhs[j] - e * dp[j - 1]) / den
        x = [0.0] * n
        x[-1] = dp[-1]
        for j in range(n - 2, -1, -1):
            x[j] = dp[j] - cp[j] * x[j + 1]
        return x

    u, v = [0.0] * n, [0.0] * n
    if velocity is not None:
        v[-1] = velocity
    a = solve(0.0, f)
    if velocity is not None:
        a[-1] = 0.0

    def state():
        mid = n // 2
        return {"tip": u[-1], "vtip": v[-1], "mid": u[mid - 1],
                "smid": E3 * (u[mid] - u[mid - 2]) / (2.0 * H3),
                "reac": k * u[0]}

    t, out, first = 0.0, [(0.0, state())], True
    for t_out, ns in zip(times, nsub):
        dt = (t_out - t) / ns
        for _s in range(ns):
            up = [u[j] + dt * v[j] + dt * dt * (0.5 - b) * a[j]
                  for j in range(n)]
            f0 = [0.0] * n if first else f
            kup, ku0 = ku(up), ku(u)
            rhs = [(1.0 + al) * f[j] - al * f0[j] - ku0[j] -
                   (1.0 + al) * (kup[j] - ku0[j]) for j in range(n)]
            a1 = solve((1.0 + al) * b * dt * dt, rhs)
            if velocity is not None:
                a1[-1] = 0.0
            u = [up[j] + b * dt * dt * a1[j] for j in range(n)]
            v = [v[j] + dt * ((1.0 - g) * a[j] + g * a1[j])
                 for j in range(n)]
            a = a1
            first = False
        t = t_out
        out.append((t, state()))
    return out


def _times(dt_out, t_end):
    return [dt_out * (i + 1) for i in range(int(round(t_end / dt_out)))]


def _series(chain, key):
    return [(t, s[key]) for t, s in chain]


def _tip3(r, var="displx"):
    return r.history(var, (L3, 0, 0))


def _reac3(r):
    """[(t, -som reactiekracht X op de inklemming)] (trek > 0)."""
    nids = r.model.nodesel["InklemKnopen"]
    return [(t, -sum(d["reactionforcex"].get(n, 0.0) for n in nids))
            for t, d in r.steps if "reactionforcex" in d]


def _mid3(r, var="stressxx"):
    return r.history(var, (L3 / 2.0, 0, 0))


def build_dy03(load, t_end, dt_out):
    def build():
        m = Model("D31", timesteps=_timesteps(t_end, dt_out))
        m.elset("Staaf", "Staal")
        h = hexmesh(m, "Staaf", NX3, 1, 1, box(0, L3, 0, B3, 0, B3))
        m.mat("Staal", '<mechanical type="Isotropic" '
              'youngsmodulus="210000 MPa" poissonratio="0" />',
              u'<density type="Simple" density="7850 kg/m³" />')
        m.face_selection("Inklemming", h["faces"]["u0"])
        m.face_selection("Eindvlak", h["faces"]["u1"])
        m.node_selection("InklemKnopen", sorted(h["nodes"]["u0"]))
        m.add('<fixed selection="Inklemming" />')
        if load == "force":
            m.add('<force selection="Eindvlak"><x>%r N</x><y>0 N</y>'
                  '<z>0 N</z></force>' % F3)
        else:
            m.add('<velocity selection="Eindvlak"><value>%r m/s</value>'
                  '<x>1</x><y>0</y><z>0</z></velocity>' % V3)
        return m
    return build


def _analytic_checks(items, chain):
    """items: [(naam, fn(reeks) -> waarde, get(r) -> reeks, sleutel in de
    keten, ref, eenheid, bron, margin)]. De verwachte waarde is fn op de
    reeks van de 1D-keten."""
    out = []
    for name, fn, get, key, ref, unit, source, margin in items:
        tol, dev = _expected_tol(fn(_series(chain, key)), ref, margin)
        out.append(Check(name, (lambda fn, get: lambda r: fn(get(r)))(
            fn, get), ref=ref, tol=tol, unit=unit,
            source="%s; verwacht (1D-keten) %+.3f%%; tol = 1,5 x verwacht + "
                   "%g%%" % (source, 100 * dev, 100 * margin)))
    return out


# expliciet: per uitvoerinterval ceil(dt_uit / (0,5 h/c)) gelijke stappen
# (bridge: explicit_dt_factor 0,5 x kleinste ribbe / c, docs/Instellingen_
# contact_en_nietlineair.md par. 2.1)
_T3E = _times(DTO3, TEND3)
_NS3E = [int(math.ceil(DTO3 / (0.5 * H3 / C3)))] * len(_T3E)
_T3I = _times(DTI3, TENDI3)
CHAIN3A = bar_chain(_T3E, _NS3E, False, force=F3)
CHAIN3B = bar_chain(_T3E, _NS3E, False, velocity=V3)
CHAIN3C = bar_chain(_T3I, [1] * len(_T3I), True, alpha=-0.1, force=F3)
V3F = F3 / (RHO3 * C3 * A3)
U3S = F3 * L3 / (E3 * A3)


def _w(t0, t1):
    return lambda h: mean_between(h, t0 * TC3, t1 * TC3)


DY03A = _analytic_checks([
    ("tipsnelheid", _w(0.25, 1.75), lambda r: _tip3(r, "velx"), "vtip",
     V3F, "m/s", "v = F/(rho c A), c = sqrt(E/rho) (Graff, Wave Motion in "
     "Elastic Solids par. 2.1); gemiddelde 0,25..1,75 L/c", 2e-3),
    ("spanning midden", _w(0.75, 1.25), _mid3, "smid", F3 / A3, "Pa",
     "sigma = F/A achter het front; gemiddelde 0,75..1,25 L/c", 2e-3),
    ("aankomsttijd inklemming", lambda h: time_reaching(h, F3), _reac3,
     "reac", TC3, "s", "L/c: reactie bereikt F (halverwege de sprong naar "
     "2F)", 2e-3),
    ("reactie na reflectie", _w(1.25, 2.75), _reac3, "reac", 2.0 * F3, "N",
     "verdubbeling aan een vast einde: 2F tussen L/c en 3L/c", 2e-3),
    ("max. tipverplaatsing", lambda h: peak(h, t_max=3.0 * TC3), _tip3,
     "tip", 2.0 * U3S, "m", "u = v t tot t = 2L/c: 2 F L/(E A)", 2e-3),
], CHAIN3A) + [
    Check("verloop t.o.v. 1D-keten", lambda r: max_dev(
        _tip3(r), _series(CHAIN3A, "tip")), ref=0.0, tol_abs=1e-5, unit="-",
          source="max |u_tip,FEM - u_tip,keten| / max u; keten = zelfde "
                 "schema en stappen in Python (bar_chain)"),
]

DY03B = _analytic_checks([
    ("spanning midden", _w(0.75, 1.25), _mid3, "smid", RHO3 * C3 * V3, "Pa",
     "sigma = rho c v (Graff par. 2.1); gemiddelde 0,75..1,25 L/c", 2e-3),
    ("reactie na reflectie", _w(1.25, 2.75), _reac3, "reac",
     2.0 * RHO3 * C3 * V3 * A3, "N", "2 rho c v A tussen L/c en 3L/c", 2e-3),
    ("tipverplaatsing eind", lambda h: h[-1][1], _tip3, "tip", V3 * TEND3,
     "m", "opgelegd: u = v t", 1e-4),
    ("tipsnelheid", _w(0.25, 2.75), lambda r: _tip3(r, "velx"), "vtip", V3,
     "m/s", "opgelegd", 1e-4),
], CHAIN3B) + [
    Check("verloop t.o.v. 1D-keten", lambda r: max_dev(
        _mid3(r, "displx"), _series(CHAIN3B, "mid")), ref=0.0,
          tol_abs=1e-5, unit="-",
          source="max |u_midden,FEM - u_midden,keten| / max u (bar_chain)"),
]

DY03C = _analytic_checks([
    ("periode 1e mode", lambda h: period(h, U3S), _tip3, "tip", T_IMPL3, "s",
     "T = 4 L/c (staaf vast-vrij, Graff par. 2.2)", 1e-3),
    ("tipsnelheid", _w(0.25, 1.75), lambda r: _tip3(r, "velx"), "vtip",
     V3F, "m/s", "v = F/(rho c A); gemiddelde 0,25..1,75 L/c", 2e-3),
    ("max. tipverplaatsing", lambda h: peak(h, t_max=T_IMPL3), _tip3,
     "tip", 2.0 * U3S, "m", "2 F L/(E A)", 2e-3),
], CHAIN3C) + [
    Check("verloop t.o.v. 1D-keten", lambda r: max_dev(
        _tip3(r), _series(CHAIN3C, "tip")), ref=0.0, tol_abs=1e-5, unit="-",
          source="max |u_tip,FEM - u_tip,keten| / max u; keten met "
                 "consistente massa en HHT (bar_chain)"),
]


# ==========================================
# DY-20 Expliciet: andere opgelegde bewegingen omgezet naar versnellingen
# (bridge_to_aster._explicit_kinematics)
# ==========================================
UC20 = 1.0e-5                       # constante van de constraint equation [m]


def build_dy20_frictionless():
    """DY-03b met frictionless (FACE_IMPO DNOR) op het eindvlak in plaats
    van een opgelegde snelheid: normaalverplaatsing -V3 t (positief = het
    vlak in, manual v33 par. 9.2), dus dezelfde beweging u = V3 t."""
    def build():
        m = build_dy03("velocity", TEND3, DTO3)()
        m.items = [i for i in m.items if "<velocity" not in i]
        m.add('<frictionless selection="Eindvlak">'
              '<displacement time="0 s">0 m</displacement>'
              '<displacement time="%r s">%r m</displacement>'
              '</frictionless>' % (TEND3, -V3 * TEND3))
        return m
    return build


def build_dy20_constraint():
    """DY-03-staaf zonder last; de vier knopen van het eindvlak elk met een
    constraint equation 1 ux = UC20 (manual v33 par. 9.42)."""
    def build():
        m = build_dy03("velocity", TEND3, DTO3)()
        m.items = [i for i in m.items if "<velocity" not in i]
        tip = [i + 1 for i, p in enumerate(m.nodes)
               if abs(p[0] - L3) < 1e-12]
        m.node_selection("Tipknopen", tip)
        for n in tip:
            m.add('<constraintequation><term coefficient="1 1/m" nid="%d" '
                  'dof="ux" /><constant>%r</constant></constraintequation>'
                  % (n, UC20))
        return m
    return build


def build_dy20_shell():
    """Vlakke plaat (quad4, DKT) met frictionless op het hele schaalvlak
    (LIAISON_OBLIQUE DX, bridge_bcs.FrictionlessBC) en normaalverplaatsing
    -V3 t: de plaat beweegt als star lichaam langs z."""
    def build():
        m = Model("D31", timesteps=_timesteps(TEND3, DTO3))
        m.elset("Plaat", "Staal")
        g = quadmesh(m, "Plaat", 4, 2, rect(0, 0.2, 0, 0.1))
        m.mat("Staal", '<geometric type="Plate" thickness="5 mm" />',
              '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
              'poissonratio="0.3" />',
              u'<density type="Simple" density="7850 kg/m³" />')
        m.face_selection("Vlak", g["faces"])
        m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
        m.add('<frictionless selection="Vlak">'
              '<displacement time="0 s">0 m</displacement>'
              '<displacement time="%r s">%r m</displacement>'
              '</frictionless>' % (TEND3, -V3 * TEND3))
        return m
    return build


def _const_dev(hist, ref, t_min):
    """Grootste |u - ref| / |ref| op de uitvoertijden vanaf t_min."""
    return max(abs(u - ref) for t, u in hist if t >= t_min) / abs(ref)


DY20B = [
    Check("tipverplaatsing eind", lambda r: _tip3(r)[-1][1], ref=UC20,
          tol=1e-6, unit="m", source="constraint equation: u = C"),
    Check("tipverplaatsing vanaf de eerste uitvoertijd",
          lambda r: _const_dev(_tip3(r), UC20, DTO3), ref=0.0,
          tol_abs=1e-6, unit="-",
          source="max |u_tip - C| / C: C bereikt in de eerste rekenstap"),
]

DY20C = [
    Check("normaalverplaatsing eind (|uz| gemiddeld)",
          lambda r: abs(r.mean("displz", "Alle")), ref=V3 * TEND3,
          tol=1e-6, unit="m", source="opgelegd: |u| = v t"),
    Check("normaalsnelheid (|vz| gemiddeld, laatste uitvoertijd)",
          lambda r: abs(r.mean("velz", "Alle")), ref=V3, tol=1e-4,
          unit="m/s", source="opgelegd"),
]


TESTS = [
    _dy01("DY-01a", "Massa-veer, staplast, HHT alpha=-0,1 (dt=T/20)",
          T1 / 20.0, "HHT", -0.1),
    _dy01("DY-01b", "Massa-veer, staplast, Newmark (dt=T/10)",
          T1 / 10.0, "NEWMARK", series="DY-01 Newmark dt"),
    _dy01("DY-01c", "Massa-veer, staplast, Newmark (dt=T/20)",
          T1 / 20.0, "NEWMARK", series="DY-01 Newmark dt"),
    _dy01("DY-01d", "Massa-veer, staplast, Newmark (dt=T/40)",
          T1 / 40.0, "NEWMARK", series="DY-01 Newmark dt"),
    Case("DY-02", GROUP, "Ingeklemde balk, staplast tip, 1e eigenperiode "
         "(POU_D_E, HHT, dt=T1/40)", "dyna_impl_3d", build_dy02,
         _dy02_checks(), timeout=600,
         note="20 balkelementen, vrije trilling rond de statische stand."),
    Case("DY-03a", GROUP, "Staafgolf, staplast, expliciet (hex8, nu=0)",
         "dyna_expl_3d", build_dy03("force", TEND3, DTO3), DY03A,
         settings={"deformation": "PETIT"}, timeout=900,
         note="100 x 1 x 1 hex8, DIFF_CENT, dt = 0,5 h/c; PETIT."),
    Case("DY-03b", GROUP, "Staafgolf, opgelegde snelheid, expliciet",
         "dyna_expl_3d", build_dy03("velocity", TEND3, DTO3), DY03B,
         settings={"deformation": "PETIT"}, timeout=900,
         note="Opgelegde snelheid als versnelling "
              "(FORMULATION='ACCELERATION'); PETIT."),
    Case("DY-20a", GROUP, "Staafgolf, frictionless met normaal"
         "verplaatsing, expliciet (FACE_IMPO)", "dyna_expl_3d",
         build_dy20_frictionless(), DY03B,
         settings={"deformation": "PETIT"}, timeout=900,
         note="Als DY-03b, de beweging als frictionless met "
              "normaalverplaatsing -v t op het eindvlak (FACE_IMPO DNOR, "
              "omgezet naar een versnelling)."),
    Case("DY-20b", GROUP, "Staaf, constraint equation ux = C, expliciet",
         "dyna_expl_3d", build_dy20_constraint(), DY20B,
         settings={"deformation": "PETIT"}, timeout=900,
         note="LIAISON_DDL met COEF_IMPO als functie (AFFE_CHAR_MECA_F): "
              "C in de eerste rekenstap, daarna constant."),
    Case("DY-20c", GROUP, "Plaat, frictionless schaalvlak met "
         "normaalverplaatsing, expliciet (LIAISON_OBLIQUE)", "dyna_expl_3d",
         build_dy20_shell(), DY20C,
         settings={"deformation": "PETIT"}, timeout=900,
         note="Vlak schaalvlak: LIAISON_OBLIQUE DX = -v t, omgezet naar "
              "een versnelling; de plaat beweegt star."),
    Case("DY-03c", GROUP, "Staafgolf, staplast, impliciet (HHT, dt=T/77)",
         "dyna_impl_3d", build_dy03("force", TENDI3, DTI3), DY03C,
         settings={"deformation": "PETIT"}, timeout=900,
         note="Zelfde staaf als DY-03a; PETIT."),
]
