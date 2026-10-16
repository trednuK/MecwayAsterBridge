# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Balkorientatie (Mecway orientationvx/vy/vz + angle per <elem>) in modaal
(MO-20 ... MO-29), lineair statisch (LS-70 ... LS-78) en knik (BU-20 ...
BU-24). Toelichting: docs/Verificatie.md (par. Balkorientatie).

Mecway-regel (Mecway-manual v33 par. 7.5): U = balkas (knoop 1 -> 2); V =
de orientatievector geprojecteerd loodrecht op U en daarna rechtsom om U
gedraaid met 'angle'; zonder vector V = Z x U (genormeerd), voor een balk
langs Z V = Y. W = U x V. RectBar: recta langs V, rectb langs W, dus
I_V = recta rectb^3/12 (buiging met uitwijking langs W) en
I_W = rectb recta^3/12 (uitwijking langs V).

De verwachte V per case staat hieronder met de hand uitgerekend (niet met
de code van de bridge, bridge_mesh._mecway_v_axis); de referenties zijn
analytisch (Euler-Bernoulli) en Mecway 34 headless (TestFiles/Tools/
mw_solve.py, 15 okt 2026, zelfde .liml): frequenties, verplaatsingen en
kniklastfactoren waren daar gelijk aan de bridge tot ~1e-8 relatief.
"""
import math
from verif_lib import Case, Check, Model, linemesh

E, NU, RHO = 210e9, 0.3, 7850.0
G = E / (2 * (1 + NU))
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7850 kg/m³" />'

# RectBar 40 x 10 mm: sterk niet-vierkant (I_W = 16 I_V)
RA, RB = 0.040, 0.010
RECT = '<geometric type="RectBar" recta="40 mm" rectb="10 mm" />'
AREA = RA * RB
I_V = RA * RB ** 3 / 12.0          # zwak: uitwijking langs W
I_W = RB * RA ** 3 / 12.0          # sterk: uitwijking langs V
# I-profiel 100/50/10/8 mm (hoogte a langs V): waarden zoals Mecway 33 ze in
# het materiaalvenster toont (zie bridge_from_liml._profile_props)
IPROF = '<geometric type="I" ia="100 mm" ib="50 mm" ic="10 mm" id="8 mm" />'
IP_A, IP_IV, IP_IW = 1640e-6, 211746.67e-12, 2374666.67e-12
IP_J = 47132.76e-12
L = 1.0
N_EL = 20
LAMBDA_CF = (1.87510407, 4.69409113, 7.85475744, 10.99554073)
S2, S3, S6 = math.sqrt(2.0), math.sqrt(3.0), math.sqrt(6.0)
C30, SN30 = math.cos(math.radians(30)), math.sin(math.radians(30))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


# ------------------------------------------------------------------
# Orientaties: (naam, U, orientatie-attributen, V met de hand)
# ------------------------------------------------------------------
_UX, _UY, _UZ = (1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0)
_US = (1 / S3, 1 / S3, 1 / S3)
ORIENT = {
    # langs X zonder vector: V = Z x X = Y
    "X": (_UX, None, (0.0, 1.0, 0.0)),
    # langs Y zonder vector: V = Z x Y = -X
    "Y": (_UY, None, (-1.0, 0.0, 0.0)),
    # langs Z zonder vector: V = Y (bijzondere regel van Mecway)
    "Z": (_UZ, None, (0.0, 1.0, 0.0)),
    # schuin (1,1,1) zonder vector: V = Z x U = (-1, 1, 0)/sqrt 2
    "S": (_US, None, (-1 / S2, 1 / S2, 0.0)),
    # langs X, vector Z: V = Z (doorsnede 90 graden gedraaid t.o.v. "X")
    "Xv": (_UX, ((0, 0, 1), None), (0.0, 0.0, 1.0)),
    # schuin, vector Z, 30 graden: V0 = (-1,-1,2)/sqrt 6, U x V0 =
    # (1,-1,0)/sqrt 2, V = cos30 V0 + sin30 U x V0
    "Sa": (_US, ((0, 0, 1), 30),
           tuple(C30 * a / S6 + SN30 * b / S2
                 for a, b in zip((-1, -1, 2), (1, -1, 0)))),
    # langs Z, vector X, 30 graden: V = cos30 X + sin30 (Z x X = Y)
    "Za": (_UZ, ((1, 0, 0), 30), (C30, SN30, 0.0)),
    # langs Y, vector X, 90 graden: V = Y x X = -Z
    "Ya": (_UY, ((1, 0, 0), 90), (0.0, 0.0, -1.0)),
}


def _attrs(orient):
    if not orient:
        return ""
    vec, ang = orient
    s = 'orientationvx="%g" orientationvy="%g" orientationvz="%g"' % vec
    if ang is not None:
        s += ' angle="%g °"' % ang
    return s


def _vw(key):
    u, _o, v = ORIENT[key]
    return u, v, _cross(u, v)


def _card(sel, orient, angle=None):
    """Element orientation as a Loads & Constraints item, as Mecway 34
    writes it (all seven children, zero U = not given). angle: text of
    <angleu> (e.g. a formula element), otherwise from orient."""
    vec, ang = orient
    if angle is None:
        angle = "<angleu>%s</angleu>" % (
            "0 rad" if ang is None else "%g °" % ang)
    return ('<orientation selection="%s"><ux>0</ux><uy>0</uy><uz>0</uz>'
            '%s%s</orientation>' % (sel, "".join(
                c if isinstance(c, str) else "<v%s>%g</v%s>" % (x, c, x)
                for x, c in zip("xyz", vec)), angle))


def _beam(m, p0, p1, orient, card=None):
    """20 elements from p0 to p1; orient as element attributes, or with
    card (name of an element selection) as an Element orientation card."""
    nids = [m.node(*[p0[d] + (p1[d] - p0[d]) * i / float(N_EL)
                     for d in range(3)]) for i in range(N_EL + 1)]
    eids = [m.elem("Balk", "line2", [nids[i], nids[i + 1]],
                   "" if card else _attrs(orient)) for i in range(N_EL)]
    if card and orient:
        m.element_selection(card, eids)
        m.add(_card(card, orient))
    return nids


def _cantilever(analysis, key, section=RECT, attrs=None, length=L,
                card=False):
    u, orient, _v = ORIENT[key]
    m = Model(analysis, attrs=attrs)
    m.elset("Balk", "Mat")
    nids = _beam(m, (0, 0, 0), tuple(length * c for c in u), orient,
                 "Orient" if card else None)
    m.mat("Mat", section, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.node_selection("Rail", nids[1:])
    return m, nids


# Raamwerk: kolom langs Z (zonder vector), ligger langs X (vector (0,1,1),
# 30 graden), schuine staaf (1,0,1) -> (1,1,1.5) (vector Z).
FRAME = [((0, 0, 0), (0, 0, 1), None), ((0, 0, 1), (1, 0, 1), ((0, 1, 1), 30)),
         ((1, 0, 1), (1, 1, 1.5), ((0, 0, 1), None))]
FRAME_TIP = (1, 1, 1.5)


def _frame(analysis, attrs=None, section=RECT, card=False):
    m = Model(analysis, attrs=attrs)
    m.elset("Balk", "Mat")
    first = None
    for k, (p0, p1, o) in enumerate(FRAME):
        nids = _beam(m, p0, p1, o, "Orient%d" % (k + 1) if card else None)
        first = first or nids[0]
    m.mat("Mat", section, STEEL, DENS)
    m.node_selection("Inklemming", [first])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    return m


def _tipvec(r, var, tip, k=None):
    st = r.step(k)
    return [st[var + c][r.nearest(tip)] for c in "xyz"]


def _dir_check(name, tip, e, k=None, var="displ", source=""):
    """|u . e| / |u| in de tip (1 = uitwijking precies langs e)."""
    def value(r, tip=tip, e=e, k=k):
        u = _tipvec(r, var, tip, k)
        n = math.sqrt(_dot(u, u))
        return abs(_dot(u, e)) / n
    return Check(name, value, ref=1.0, tol_abs=1e-4, unit="-",
                 source=source, in_series=False)


# ==================================================================
# MODAAL (MO-20 ... MO-29)
# ==================================================================
def f_cf(lam, inertia, area=AREA, length=L):
    """Euler-Bernoulli ingeklemd-vrij (Blevins 1979, tabel 8-1)."""
    return lam ** 2 / (2 * math.pi * length ** 2) * math.sqrt(
        E * inertia / (RHO * area))


# De laagste 6 buigmodes van de RectBar: (f, "W"/"V", orde). Zwak (I_V):
# uitwijking langs W; sterk (I_W): langs V.
MODES_R = sorted([(f_cf(l, I_V), "W", i + 1) for i, l in
                  enumerate(LAMBDA_CF)] +
                 [(f_cf(l, I_W), "V", i + 1) for i, l in
                  enumerate(LAMBDA_CF)])[:6]
# Torsie ingeklemd-vrij: f = 1/(4L) sqrt(G J/(rho I_p)), I_p = I_V + I_W
# (polair, massatraagheid van de doorsnede); J van de rechthoek 2a x 2b
# (a = 20, b = 5 mm): J = a b^3 (16/3 - 3,36 b/a (1 - b^4/(12 a^4)))
# (Roark, 7e druk, tabel 10.7, geval 4). Langs: f = sqrt(E/rho)/(4L).
_a, _b = RA / 2, RB / 2
J_R = _a * _b ** 3 * (16 / 3.0 - 3.36 * _b / _a * (1 - _b ** 4 / (12 * _a ** 4)))
F_TORS = 1 / (4 * L) * math.sqrt(G * J_R / (RHO * (I_V + I_W)))
F_AXIAL = math.sqrt(E / RHO) / (4 * L)

# Mecway 34 headless (mw_solve.py) op modellen/<id>.liml, 15 okt 2026:
# frequenties [Hz] van mode 1 en 2 (bij MO-28: modes 1 ... 8).
MECWAY_F = {
    "MO-20": (8.35516633438181, 33.4206655668892),
    "MO-21": (8.35516634615583, 33.4206655171055),
    "MO-22": (8.35516635551394, 33.4206655301173),
    "MO-23": (8.35516645347992, 33.4206655706892),
    "MO-24": (8.35516644147208, 33.4206655610414),
    "MO-25": (8.35516640059515, 33.4206655614027),
    "MO-26": (8.3551664081098, 33.42066557429),
    "MO-27": (32.8875933830736, 108.280997199524, 110.13494274214),
    # orientatiekaart (16 okt 2026): gelijk aan MO-25
    "MO-31": (8.35516640059515, 33.4206655614027),
}


def _mode_checks(cid, key, n=6, effmass=False):
    _u, v, w = _vw(key)
    tip = tuple(L * c for c in ORIENT[key][0])
    out = []
    for k, (f, axis, i) in enumerate(MODES_R[:n]):
        src = ("Euler-Bernoulli %s%d, I = %s (Blevins 8-1)"
               % ("zwak" if axis == "W" else "sterk", i,
                  "recta rectb^3/12" if axis == "W" else "rectb recta^3/12"))
        out.append(Check("f%d" % (k + 1), lambda r, k=k: r.mode(k + 1),
                         ref=f, tol=0.002, unit="Hz", source=src))
        out.append(_dir_check("mode %d langs %s" % (k + 1, axis), tip,
                              w if axis == "W" else v, k=k + 1,
                              source="uitwijking tip langs %s = (%.4f, "
                              "%.4f, %.4f) (Mecway-regel, met de hand)"
                              % ((axis,) + tuple(w if axis == "W" else v))))
    for k, ref in enumerate(MECWAY_F.get(cid, ())):
        out.append(Check("f%d t.o.v. Mecway" % (k + 1),
                         lambda r, k=k: r.mode(k + 1), ref=ref, tol=1e-4,
                         unit="Hz", in_series=False,
                         source="Mecway 34 headless, zelfde .liml"))
    if effmass:
        # effectieve massa (fractie) van mode 1 (zwak, langs W) en 2 (sterk,
        # langs V): 0,6131 (Euler-Bernoulli, zie tests_modaal FRAC_T) maal
        # het kwadraat van de richtingscosinus
        frac = 0.61308
        for k, e in ((1, w), (2, v)):
            for d, c in zip("XYZ", e):
                out.append(Check(
                    "eff. massa %s mode %d" % (d, k),
                    lambda r, k=k, d=d: r.mode_param(k, "MASS_EFFE_UN_D" + d),
                    ref=frac * c * c, tol_abs=2e-4, unit="-",
                    source="0,6131 x (%s . e_%s)^2 = 0,6131 x %.4f"
                    % ("W" if k == 1 else "V", d, c * c)))
    return out


def _how(key, card):
    if not ORIENT[key][1]:
        return "geen orientatie (standaard)"
    if card:
        return "Element orientation-kaart (%s)" % _attrs(ORIENT[key][1])
    return _attrs(ORIENT[key][1])


def _mo(cid, key, title, n_modes=6, extra=None, effmass=False, card=False):
    def build():
        return _cantilever("V30", key, attrs={"maxmode": n_modes},
                           card=card)[0]
    return Case(cid, "Modaal", title, "modal_3d", build,
                _mode_checks(cid, key, effmass=effmass) + (extra or []),
                note="RectBar 40 x 10 mm, L = 1 m, 20 POU_D_E; %s" %
                _how(key, card))


TESTS = [
    _mo("MO-20", "X", "Balkorientatie modaal: langs X, standaard",
        n_modes=14,
        extra=[Check("f7 torsie", lambda r: r.mode(7), ref=F_TORS, tol=0.002,
                     unit="Hz", source="1/(4L) sqrt(GJ/(rho I_p)), J Roark "
                     "tabel 10.7, I_p = I_V + I_W"),
               _dir_check("mode 7 torsie om U", (L, 0, 0), (1, 0, 0), k=7,
                          var="rot", source="tiprotatie langs de balkas"),
               Check("f14 langs", lambda r: r.mode(14), ref=F_AXIAL,
                     tol=0.001, unit="Hz", source="sqrt(E/rho)/(4L)"),
               _dir_check("mode 14 langs U", (L, 0, 0), (1, 0, 0), k=14,
                          source="tipverplaatsing langs de balkas")]),
    _mo("MO-21", "Y", "Balkorientatie modaal: langs Y, standaard"),
    _mo("MO-22", "Z", "Balkorientatie modaal: langs Z, standaard (V = Y)"),
    _mo("MO-23", "S", "Balkorientatie modaal: schuin (1,1,1), standaard",
        effmass=True),
    _mo("MO-24", "Xv", "Balkorientatie modaal: langs X, vector Z"),
    _mo("MO-25", "Sa", "Balkorientatie modaal: schuin, vector Z + 30 graden",
        effmass=True),
    _mo("MO-26", "Za", "Balkorientatie modaal: langs Z, vector X + 30 graden"),
]


# MO-27: I-profiel langs Y, vector X + 90 graden (V = -Z, W = -X)
def build_mo27():
    return _cantilever("V30", "Ya", section=IPROF, attrs={"maxmode": 3})[0]


def _mo27_checks():
    # mode 1 zwak (langs W), mode 2 torsie (108 Hz: 1/(4L) sqrt(GJ/(rho
    # I_p)) met J = 47132,76 mm4 en I_p = I_V + I_W zoals Mecway), mode 3
    # sterk (langs V)
    u, v, w = _vw("Ya")
    f_t = 1 / (4 * L) * math.sqrt(G * IP_J / (RHO * (IP_IV + IP_IW)))
    out = [Check("f2 torsie", lambda r: r.mode(2), ref=f_t, tol=0.002,
                 unit="Hz", source="1/(4L) sqrt(GJ/(rho I_p)), J en I_p "
                 "zoals Mecway 33 ze toont"),
           _dir_check("mode 2 torsie om U", (0, L, 0), u, k=2, var="rot",
                      source="tiprotatie langs de balkas")]
    for k, (f, axis, i) in ((0, (f_cf(LAMBDA_CF[0], IP_IV, IP_A), "W", 1)),
                            (2, (f_cf(LAMBDA_CF[0], IP_IW, IP_A), "V", 1))):
        out.append(Check("f%d" % (k + 1), lambda r, k=k: r.mode(k + 1),
                         ref=f, tol=0.002, unit="Hz",
                         source="Euler-Bernoulli %s%d, I_V/I_W en A zoals "
                         "Mecway 33 ze toont" % (
                             "zwak" if axis == "W" else "sterk", i)))
        out.append(_dir_check("mode %d langs %s" % (k + 1, axis), (0, L, 0),
                              w if axis == "W" else v, k=k + 1,
                              source="V = -Z, W = -X (met de hand)"))
    for k, ref in enumerate(MECWAY_F.get("MO-27", ())):
        out.append(Check("f%d t.o.v. Mecway" % (k + 1),
                         lambda r, k=k: r.mode(k + 1), ref=ref, tol=1e-4,
                         unit="Hz", in_series=False,
                         source="Mecway 34 headless, zelfde .liml"))
    return out


TESTS.append(Case(
    "MO-27", "Modaal", "Balkorientatie modaal: I-profiel langs Y, vector X + "
    "90 graden", "modal_3d", build_mo27, _mo27_checks(),
    note="I 100/50/10/8 mm (GENERALE zoals Mecway), 20 POU_D_E."))


# MO-28: raamwerk met drie staven in verschillende richtingen
def build_mo28():
    return _frame("V30", attrs={"maxmode": 8})


# Mecway 34 headless: frequenties [Hz] en de genormeerde tipverplaatsing
# van mode 1 ... 3 (teken willekeurig)
MECWAY_MO28_F = (1.39868852517298, 1.67958369750139, 4.75548922175271,
                 6.42482882942216, 8.73515760422151, 21.2432435886332,
                 35.7517275991549, 47.8613087988752)
MECWAY_MO28_U = ((0.836353, -0.236933, -0.494344),
                 (0.387413, -0.727366, 0.566436),
                 (-0.376405, 0.079984, -0.922996))


def _mo28_checks():
    out = [Check("f%d t.o.v. Mecway" % (k + 1), lambda r, k=k: r.mode(k + 1),
                 ref=f, tol=1e-4, unit="Hz",
                 source="Mecway 34 headless, zelfde .liml")
           for k, f in enumerate(MECWAY_MO28_F)]
    out += [_dir_check("mode %d tiprichting als Mecway" % (k + 1), FRAME_TIP,
                       e, k=k + 1, source="Mecway 34 headless: (%.4f, %.4f, "
                       "%.4f)" % tuple(e))
            for k, e in enumerate(MECWAY_MO28_U)]
    return out


TESTS.append(Case(
    "MO-28", "Modaal", "Balkorientatie modaal: raamwerk (3 staven, 3 "
    "orientaties)", "modal_3d", build_mo28, _mo28_checks(),
    note="RectBar 40 x 10 mm; kolom Z (standaard), ligger X (vector "
    "(0,1,1) + 30 graden), schuine staaf (vector Z)."))


# MO-29: korte balk L = 0,1 m (L/h = 2,5 in de sterke richting): Mecway en
# POU_D_E rekenen zonder rotatietraagheid van de doorsnede bij buiging
# (Euler-Bernoulli exact; een Rayleigh-/Timoshenko-balk zou lager liggen).
L29 = 0.1


def build_mo29():
    return _cantilever("V30", "X", attrs={"maxmode": 2}, length=L29)[0]


TESTS.append(Case(
    "MO-29", "Modaal", "Korte balk L/h = 2,5: buiging zonder "
    "rotatietraagheid (als Mecway)", "modal_3d", build_mo29,
    [Check("f1 zwak", lambda r: r.mode(1), ref=f_cf(LAMBDA_CF[0], I_V,
                                                     length=L29),
           tol=1e-4, unit="Hz", source="Euler-Bernoulli zonder "
           "rotatietraagheid (Blevins 8-1)"),
     Check("f2 sterk", lambda r: r.mode(2), ref=f_cf(LAMBDA_CF[0], I_W,
                                                      length=L29),
           tol=1e-4, unit="Hz", source="Euler-Bernoulli zonder "
           "rotatietraagheid; Mecway 34 headless 3342,0666 Hz")],
    note="RectBar 40 x 10 mm, L = 0,1 m, 20 POU_D_E."))


# ==================================================================
# LINEAIR STATISCH (LS-70 ... LS-78)
# ==================================================================
FORCE = (100.0, 200.0, 300.0)       # N, op de tip


def _static_ref(key, iv=I_V, iw=I_W, area=AREA):
    """Tipverplaatsing (Euler-Bernoulli) en sigma_xx max/min in de
    inklemming (RectBar) voor FORCE op de tip."""
    u, v, w = _vw(key)
    fu, fv, fw = _dot(FORCE, u), _dot(FORCE, v), _dot(FORCE, w)
    du = fu * L / (E * area)
    dv = fv * L ** 3 / (3 * E * iw)     # uitwijking langs V: buiging om W
    dw = fw * L ** 3 / (3 * E * iv)     # uitwijking langs W: buiging om V
    disp = tuple(du * u[i] + dv * v[i] + dw * w[i] for i in range(3))
    # moment in de inklemming: M = (L U) x F; component om V en om W
    mom = _cross(tuple(L * c for c in u), FORCE)
    mv, mw = _dot(mom, v), _dot(mom, w)
    sig_b = abs(mv) * (RB / 2) / iv + abs(mw) * (RA / 2) / iw
    return disp, fu / area + sig_b, fu / area - sig_b


def _ls_checks(key, iv=I_V, iw=I_W, area=AREA, stress=True):
    disp, smax, smin = _static_ref(key, iv, iw, area)
    tip = tuple(L * c for c in ORIENT[key][0])
    mag = math.sqrt(_dot(disp, disp))
    out = [Check("tip %s" % var, lambda r, var=var: r.at(var, tip),
                 ref=disp[i], tol_abs=1e-4 * mag, unit="m",
                 source="Euler-Bernoulli: F_U L/(EA) U + F_V L^3/(3EI_W) V + "
                 "F_W L^3/(3EI_V) W")
           for i, var in enumerate(("displx", "disply", "displz"))]
    if stress:
        out += [Check("beamsixxmax inklemming",
                      lambda r: r.at("beamsixxmax", (0, 0, 0)), ref=smax,
                      tol=1e-3, unit="Pa", source="N/A + |M_V| (rectb/2)/I_V"
                      " + |M_W| (recta/2)/I_W, M = L U x F"),
                Check("beamsixxmin inklemming",
                      lambda r: r.at("beamsixxmin", (0, 0, 0)), ref=smin,
                      tol=1e-3, unit="Pa", source="N/A - |M_V| (rectb/2)/I_V"
                      " - |M_W| (recta/2)/I_W")]
    return out


def _ls_build(key, section=RECT, card=False):
    def build():
        m, _n = _cantilever("S30", key, section=section, card=card)
        m.add('<force selection="Tip"><x>%g N</x><y>%g N</y><z>%g N</z>'
              '</force>' % FORCE)
        return m
    return build


# Mecway 34 headless (mw_solve.py) op modellen/<id>.liml, 16 okt 2026:
# tipverplaatsing en -rotatie (dx, dy, dz [m], rx, ry, rz [rad]).
MECWAY_TIP = {
    # gelijk aan Mecway met de attributen (LS-75 en experiment met 4
    # elementen; LS-80 = MECWAY_LS78)
    "LS-79": (-0.04761666667147458, 0.02232380952643751, 0.0253000000021799,
              0.002577456558507215, -0.06314768569811616,
              0.06057022913954277),
    "LS-80": (-0.29293607634255237, -0.0135615668239756, 0.5295669346620123,
              0.23932999086837636, -0.2636845840425713,
              -0.0031322266992829966),
    "LS-81": (1.1904761904761654e-06, 0.06173638728323854,
              0.0038067386299123875, 0.0, -0.01116270147650637,
              0.07190865760070607),
    "LS-82": (1.1904761904761654e-06, 0.084077380946095, 0.025669642857140497,
              0.0, -0.06361607142856247, 0.10937499999218932),
}


def _mecway_tip(cid, tip):
    """Tip t.o.v. Mecway: tolerantie 1e-4 x de grootste component van de
    verplaatsing resp. de rotatie."""
    ref = MECWAY_TIP.get(cid, ())
    if not ref:
        return []
    tol_d = 1e-4 * max(abs(c) for c in ref[:3])
    tol_r = 1e-4 * max(abs(c) for c in ref[3:])
    return [Check("tip %s t.o.v. Mecway" % var,
                  lambda r, var=var: r.at(var, tip), ref=ref[i],
                  tol_abs=tol_d if i < 3 else tol_r,
                  unit="m" if i < 3 else "rad", in_series=False,
                  source="Mecway 34 headless, zelfde .liml")
            for i, var in enumerate(("displx", "disply", "displz", "rotx",
                                     "roty", "rotz"))]


def _ls(cid, key, title, card=False):
    return Case(cid, "Lineair statisch", title, "lin_static_3d",
                _ls_build(key, card=card), _ls_checks(key) +
                _mecway_tip(cid, tuple(L * c for c in ORIENT[key][0])),
                note="RectBar 40 x 10 mm, L = 1 m, 20 POU_D_E, F = (100, "
                "200, 300) N op de tip; %s" % _how(key, card))


TESTS += [
    _ls("LS-70", "X", "Balkorientatie statisch: langs X, standaard"),
    _ls("LS-71", "Y", "Balkorientatie statisch: langs Y, standaard"),
    _ls("LS-72", "Z", "Balkorientatie statisch: langs Z, standaard (V = Y)"),
    _ls("LS-73", "S", "Balkorientatie statisch: schuin (1,1,1), standaard"),
    _ls("LS-74", "Xv", "Balkorientatie statisch: langs X, vector Z"),
    _ls("LS-75", "Sa", "Balkorientatie statisch: schuin, vector Z + 30 "
        "graden"),
    _ls("LS-76", "Za", "Balkorientatie statisch: langs Z, vector X + 30 "
        "graden"),
    Case("LS-77", "Lineair statisch", "Balkorientatie statisch: I-profiel "
         "langs Y, vector X + 90 graden", "lin_static_3d",
         _ls_build("Ya", IPROF),
         _ls_checks("Ya", IP_IV, IP_IW, IP_A, stress=False),
         note="I 100/50/10/8 mm (I_V, I_W en A zoals Mecway 33 ze toont)."),
]


# LS-78: raamwerk (als MO-28), F op de tip; referentie Mecway 34 headless
MECWAY_LS78 = (-0.29293607634255237, -0.0135615668239756, 0.5295669346620123,
               0.23932999086837636, -0.2636845840425713,
               -0.0031322266992829966)


def build_ls78():
    m = _frame("S30")
    m.add('<force selection="Tip"><x>%g N</x><y>%g N</y><z>%g N</z>'
          '</force>' % FORCE)
    return m


TESTS.append(Case(
    "LS-78", "Lineair statisch", "Balkorientatie statisch: raamwerk (3 "
    "staven, 3 orientaties)", "lin_static_3d", build_ls78,
    [Check("tip %s t.o.v. Mecway" % var,
           lambda r, var=var: r.at(var, FRAME_TIP), ref=MECWAY_LS78[i],
           tol=1e-4, unit="m" if var.startswith("d") else "rad",
           source="Mecway 34 headless, zelfde .liml")
     for i, var in enumerate(("displx", "disply", "displz", "rotx", "roty",
                              "rotz")) if MECWAY_LS78],
    note="RectBar 40 x 10 mm, staven als MO-28, F = (100, 200, 300) N."))


# ==================================================================
# KNIK (BU-20 ... BU-24)
# ==================================================================
P = 1000.0                          # N drukkracht op de tip
P_V = math.pi ** 2 * E * I_V / (4 * L ** 2)   # ingeklemd-vrij, zwak
P_W = math.pi ** 2 * E * I_W / (4 * L ** 2)   # sterk


def _bu_build(key, rail=None, card=False):
    """Kolom langs U, drukkracht P op de tip; rail = (x, y, z)-vlaggen van
    een verplaatsing 0 op alle knopen behalve de inklemming (knik alleen
    in de andere richting)."""
    def build():
        m, _n = _cantilever("B30", key, attrs={"maxmode": 3, "shift": 1},
                            card=card)
        u = ORIENT[key][0]
        m.add('<force selection="Tip"><x>%r N</x><y>%r N</y><z>%r N</z>'
              '</force>' % tuple(-P * c for c in u))
        if rail:
            m.add('<displacement selection="Rail"><value>0 m</value>'
                  '<x>%d</x><y>%d</y><z>%d</z></displacement>' % rail)
        return m
    return build


def _ei_eff(key, axis):
    """I van de buiging met de kromming om de globale as 'axis' (de andere
    buigrichting is verhinderd): I_V (axis.V)^2 + I_W (axis.W)^2."""
    _u, v, w = _vw(key)
    return I_V * _dot(axis, v) ** 2 + I_W * _dot(axis, w) ** 2


MECWAY_BU = {"BU-20": 1.72718086145198, "BU-21": 27.634893780999,
             "BU-22": 27.6348937769274, "BU-23": 8.2041090899062,
             "BU-24": 1.72718086142993,
             # orientatiekaart (16 okt 2026): gelijk aan BU-23
             "BU-25": 8.2041090899062}


def _bu(cid, key, rail, axis, title, card=False):
    ieff = _ei_eff(key, axis)
    ref = math.pi ** 2 * E * ieff / (4 * L ** 2) / P
    checks = [Check("factor 1", lambda r: r.mode(1), ref=ref, tol=0.002,
                    unit="-", source="Pcr/P, Pcr = pi^2 E I/(4L^2), I = I_V "
                    "(a.V)^2 + I_W (a.W)^2 = %.4g m4 (Timoshenko & Gere 2.1)"
                    % ieff)]
    if cid in MECWAY_BU:
        checks.append(Check("factor 1 t.o.v. Mecway", lambda r: r.mode(1),
                            ref=MECWAY_BU[cid], tol=1e-4, unit="-",
                            in_series=False,
                            source="Mecway 34 headless, zelfde .liml"))
    return Case(cid, "Knik", title, "buckling_3d",
                _bu_build(key, rail, card), checks,
                note="RectBar 40 x 10 mm, L = 1 m, 20 POU_D_E, P = "
                "1000 N; %s" % (_how(key, card) if card or ORIENT[key][1]
                                else "standaard"))


TESTS += [
    # langs X, Y vast: knik in Z, kromming om Y. Standaard V = Y -> I_V (zwak)
    _bu("BU-20", "X", (0, 1, 0), (0, 1, 0),
        "Balkorientatie knik: langs X, Y vast, standaard (zwakke as)"),
    # vector Z: V = Z, W = -Y -> I_W (sterk)
    _bu("BU-21", "Xv", (0, 1, 0), (0, 1, 0),
        "Balkorientatie knik: langs X, Y vast, vector Z (sterke as)"),
    # langs Z, X vast: knik in Y, kromming om X. Standaard V = Y, W = -X ->
    # I_W (sterk)
    _bu("BU-22", "Z", (1, 0, 0), (1, 0, 0),
        "Balkorientatie knik: langs Z, X vast, standaard (sterke as)"),
    # vector X + 30 graden: V = (cos30, sin30, 0) -> 0,75 I_V + 0,25 I_W
    _bu("BU-23", "Za", (1, 0, 0), (1, 0, 0),
        "Balkorientatie knik: langs Z, X vast, vector X + 30 graden"),
]


# BU-24: schuine kolom (vector Z + 30 graden) zonder geleiding: de factoren
# hangen niet van de orientatie af, de knikvorm wel (mode 1 langs W, de
# sterke knik langs V).
def _bu24_checks():
    _u, v, w = _vw("Sa")
    tip = tuple(L * c for c in _US)
    out = [Check("factor %d" % k, lambda r, k=k: r.mode(k), ref=f / P,
                 tol=0.002, unit="-", source=src)
           for k, f, src in ((1, P_V, "pi^2 E I_V/(4L^2)"),
                             (2, 9 * P_V, "9 pi^2 E I_V/(4L^2)"),
                             (3, P_W, "pi^2 E I_W/(4L^2)"))]
    out += [_dir_check("knikvorm 1 langs W", tip, w, k=1,
                       source="W = U x V (met de hand)"),
            _dir_check("knikvorm 3 langs V", tip, v, k=3,
                       source="V (met de hand)")]
    if "BU-24" in MECWAY_BU:
        out.append(Check("factor 1 t.o.v. Mecway", lambda r: r.mode(1),
                         ref=MECWAY_BU["BU-24"], tol=1e-4, unit="-",
                         in_series=False,
                         source="Mecway 34 headless, zelfde .liml"))
    return out


TESTS.append(Case(
    "BU-24", "Knik", "Balkorientatie knik: schuin, vector Z + 30 graden, "
    "knikvorm", "buckling_3d", _bu_build("Sa"), _bu24_checks(),
    note="RectBar 40 x 10 mm, L = 1 m, 20 POU_D_E, P = 1000 N."))


# ==================================================================
# ELEMENT ORIENTATION ALS KAART (MO-31, LS-79 ... LS-82, BU-25)
# ==================================================================
# Mecway 34 slaat de orientatie ook op als Loads & Constraints-item
# <orientation selection="..."> met <ux>..<vz> en <angleu> (gevonden in de
# fork van MishalTPC, github.com/mishal0488/MecwayAsterBridge; formaat en
# betekenis headless gemeten, bridge_orientation.py). Dezelfde balken als
# hierboven, nu met een kaart op een elementselectie in plaats van de
# attributen: zelfde analytische referentie, en Mecway 34 headless op de
# kaart-.liml zelf.

TESTS += [
    _mo("MO-31", "Sa", "Orientatiekaart modaal: schuin, vector Z + 30 graden "
        "(als MO-25)", effmass=True, card=True),
    _ls("LS-79", "Sa", "Orientatiekaart statisch: schuin, vector Z + 30 "
        "graden (als LS-75)", card=True),
    _bu("BU-25", "Za", (1, 0, 0), (1, 0, 0),
        "Orientatiekaart knik: langs Z, X vast, vector X + 30 graden (als "
        "BU-23)", card=True),
]


def build_ls80():
    m = _frame("S30", card=True)
    m.add('<force selection="Tip"><x>%g N</x><y>%g N</y><z>%g N</z>'
          '</force>' % FORCE)
    return m


TESTS.append(Case(
    "LS-80", "Lineair statisch", "Orientatiekaart statisch: raamwerk, een "
    "kaart per staaf (als LS-78)", "lin_static_3d", build_ls80,
    [Check("tip %s als LS-78 (attributen, Mecway)" % var,
           lambda r, var=var: r.at(var, FRAME_TIP), ref=MECWAY_LS78[i],
           tol=1e-4, unit="m" if var.startswith("d") else "rad",
           in_series=False, source="Mecway 34 headless, LS-78 (attributen)")
     for i, var in enumerate(("displx", "disply", "displz", "rotx", "roty",
                              "rotz"))] + _mecway_tip("LS-80", FRAME_TIP),
    note="Staven als MO-28; ligger en schuine staaf elk met een eigen "
    "kaart, kolom zonder (standaard)."))

# LS-81: V en hoek als formule van de plaats (Mecway: per element in het
# middelpunt): V = (0, x, 1 - x), hoek 30 x graden (x in m).
_FORMULA = 'unit="" timeunit="s" positionunit="m"'


def _ls_x_card(card_xml_fn):
    """Uitkragende balk langs X (F op de tip) met een kaart op een deel
    van de elementen; card_xml_fn(m) voegt selectie en kaart toe."""
    def build():
        m, _n = _cantilever("S30", "X")
        card_xml_fn(m)
        m.add('<force selection="Tip"><x>%g N</x><y>%g N</y><z>%g N</z>'
              '</force>' % FORCE)
        return m
    return build


def _ls81_card(m):
    m.element_selection("Orient", range(1, N_EL + 1))
    m.add(_card("Orient", ((0, '<vy %s>x</vy>' % _FORMULA,
                            '<vz %s>1-x</vz>' % _FORMULA), None),
                angle='<angleu unit="°" timeunit="s" positionunit="m">'
                '30*x</angleu>'))


def _ls82_card(m):
    m.element_selection("Orient", range(1, N_EL // 2 + 1))
    m.add(_card("Orient", ((0, 0, 1), None)))


TESTS += [
    Case("LS-81", "Lineair statisch", "Orientatiekaart statisch: vector en "
         "hoek als formule van de plaats", "lin_static_3d",
         _ls_x_card(_ls81_card), _mecway_tip("LS-81", (L, 0, 0)),
         note="RectBar 40 x 10 mm langs X, 20 POU_D_E, F = (100, 200, 300) "
         "N; V = (0, x, 1 - x), angleu = 30 x graden."),
    Case("LS-82", "Lineair statisch", "Orientatiekaart statisch: kaart op "
         "de helft van de elementen", "lin_static_3d",
         _ls_x_card(_ls82_card), _mecway_tip("LS-82", (L, 0, 0)),
         note="RectBar 40 x 10 mm langs X, 20 POU_D_E; elementen 1-10 "
         "vector Z (kaart), 11-20 standaard."),
]
