# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Extra resultaatvelden naar Mecway (fields: beam_forces, shell_stresses,
shell_forces, strain, safety_factor, contact; aster_results_export
_plan_derived en FIELD_TABLE). Elke case controleert de waarden onder
Mecway's eigen variabelenamen tegen een analytische oplossing (statica,
balk- en plaattheorie, homogene rek). Mecway's namen, assen en tekens zijn
headless nagelopen met Mecway 34 op dezelfde modellen (docs/Verificatie.md,
LS-30 .. LS-32).

Families: LS-30.. (lineair statisch), NL-30.. (niet-lineair), MO-30
(modaal), DY-30 (dynamica).
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, quadmesh, box

GROUP_LS = "Lineair statisch"
GROUP_NL = "Niet-lineair statisch"
GROUP_MO = "Modaal"
GROUP_DY = "Dynamica"
E, NU = 210e9, 0.3
G = E / (2 * (1 + NU))
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = u'<density type="Simple" density="7850 kg/m³" />'
S_T = 250e6                                    # Pa, tensilestrength
FAIL = ('<failure type="VonMises" tensilestrength="%g MPa" />'
        % (S_T / 1e6))
SRC_MW = "Mecway 34 headless, zelfde model"


def _fields(*extra):
    return ["displacements", "stresses", "vonmises", "reactions"] + \
        list(extra)


def _mean(r, var, nids, time=None):
    d = r.step(time)[var]
    return sum(d[n] for n in nids) / float(len(nids))


def _nodes_where(r, cond):
    return [i + 1 for i, p in enumerate(r.model.nodes) if cond(p)]


# ------------------------------------------------------------------
# LS-30 Snedekrachten van een ingeklemde balk (beam_forces)
# ------------------------------------------------------------------
# Balk L = 1 m langs de as u (4 POU_D_E-elementen), rechthoek 20 x 30 mm,
# tipkracht (in lokale assen) N = 1000 N, V_v = 200 N, V_w = -300 N en
# torsiemoment 50 N.m. Statica: N, V en T constant; M_v(x) = -V_w (L - x),
# M_w(x) = V_v (L - x). Mecway (headless): tensileforce = 1000,
# sheary = 200, shearz = -300, torsion = 50, bendingmomv = 300 en
# bendingmomw = 200 in de inklemming, ook voor de schuine balk (lokale
# assen; V = Z x U voor een horizontale balk).
L30, N30, VV30, VW30, T30 = 1.0, 1000.0, 200.0, -300.0, 50.0


def build_ls30(angle):
    def build():
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        m = Model("S30")
        m.elset("Balk", "Rect")
        _e, nids = linemesh(m, "Balk", 4, (0, 0, 0), (L30 * c, L30 * s, 0))
        m.mat("Rect", '<geometric type="RectBar" recta="0.02 m" '
              'rectb="0.03 m" />', STEEL)
        m.node_selection("Inklemming", [nids[0]])
        m.node_selection("Tip", [nids[-1]])
        m.add('<fixed selection="Inklemming" />')
        # lokaal u = (c, s, 0), v = (-s, c, 0), w = Z
        m.add('<force selection="Tip"><x>%r N</x><y>%r N</y><z>%r N</z>'
              '</force>' % (N30 * c - VV30 * s, N30 * s + VV30 * c, VW30))
        m.add('<moment selection="Tip"><x>%r N.m</x><y>%r N.m</y>'
              '<z>0 N.m</z></moment>' % (T30 * c, T30 * s))
        return m
    return build


def _ls30_checks(angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    root, mid = (0, 0, 0), (0.5 * L30 * c, 0.5 * L30 * s, 0)
    src = "statica (balk, lokale assen); tekens als " + SRC_MW
    return [
        Check("N (tensileforce)", lambda r: r.at("tensileforce", mid),
              ref=N30, tol=1e-6, unit="N", source=src),
        Check("V_v (sheary)", lambda r: r.at("sheary", mid), ref=VV30,
              tol=1e-6, unit="N", source=src),
        Check("V_w (shearz)", lambda r: r.at("shearz", mid), ref=VW30,
              tol=1e-6, unit="N", source=src),
        Check("T (torsion)", lambda r: r.at("torsion", mid), ref=T30,
              tol=1e-6, unit="N.m", source=src),
        Check("M_v inklemming (bendingmomv)",
              lambda r: r.at("bendingmomv", root), ref=-VW30 * L30,
              tol=1e-6, unit="N.m", source=src),
        Check("M_w midden (bendingmomw)", lambda r: r.at("bendingmomw", mid),
              ref=VV30 * L30 / 2, tol=1e-6, unit="N.m", source=src),
    ]


# ------------------------------------------------------------------
# LS-31 Schaalstrook, scheef in de ruimte (shell_stresses, shell_forces,
# strain, safety_factor)
# ------------------------------------------------------------------
# Strook L x b = 100 x 20 mm, t = 2 mm, langs e1 = (2, 2, 1)/3, breedte
# langs e2, normaal n = e1 x e2 (niet langs een globale as: de globale
# tensor en Mecway's U-as worden echt gedraaid). Ingeklemd op u = 0; op het
# eindvlak trek F = 600 N langs e1 en P = 3 N langs -n. Op x = L/2
# (Saint-Venant): N_u = F/b = 30000 N/m, M_u = P (L - x)/b = 7,5 N
# (Mecway: momentu > 0 geeft trek boven = kant +n), Q_u = -P/b = -150 N/m;
# sigma_uu = N/t +- 6 M/t^2 = 26,25 / 3,75 MPa (boven/onder),
# sigma_vv ~ 0. Globaal: sigma_g = sigma_uu e1 e1^T (vlak, boven en
# onder geen dwarsschuif). Totale rek in de schaal: eps_uu = sigma/E,
# eps_vv = -nu sigma/E, eps_ww = 0 (Mecway en Code-Aster);
# lstrain<ij> met schuif als gamma. Factor of safety (Mecway, manual v34
# par. 8.7): S / max(von Mises boven, onder) = 250/26,25.
L31, B31, T31, F31, P31 = 0.100, 0.020, 0.002, 600.0, 3.0
X31 = L31 / 2


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


E1_31 = _unit([1.0, 1.0, 0.5])
E2_31 = _unit(_cross([0.3, -0.2, 1.0], E1_31))
N_31 = _cross(E1_31, E2_31)
SIG_TOP31 = F31 / (B31 * T31) + 6 * P31 * (L31 - X31) / B31 / T31 ** 2
SIG_BOT31 = F31 / (B31 * T31) - 6 * P31 * (L31 - X31) / B31 / T31 ** 2
SIG_MID31 = F31 / (B31 * T31)
_IJ = {"xx": (0, 0), "yy": (1, 1), "zz": (2, 2), "xy": (0, 1),
       "yz": (1, 2), "zx": (2, 0)}


def build_ls31(order, orient=None):
    def build():
        def f(u, v):
            return tuple(L31 * u * E1_31[k] + B31 * v * E2_31[k]
                         for k in range(3))
        m = Model("S30")
        m.elset("Strook", "Plaat2")
        mesh = quadmesh(m, "Strook", 10, 2, f, order=order)
        if orient:
            att = ('orientationux="%r" orientationuy="%r" '
                   'orientationuz="%r"' % tuple(orient))
            name, mat, elems = m.elsets[0]
            m.elsets[0] = (name, mat, [(e, sh, n, att)
                                       for e, sh, n, _a in elems])
        m.mat("Plaat2", '<geometric type="Plate" thickness="%g m" />' % T31,
              STEEL, FAIL)
        m.face_selection("Inklemming", mesh["edges"]["u0"])
        m.face_selection("Eind", mesh["edges"]["u1"])
        m.add('<fixed selection="Inklemming" />')
        fv = [F31 * E1_31[k] - P31 * N_31[k] for k in range(3)]
        m.add('<force selection="Eind"><x>%r N</x><y>%r N</y><z>%r N</z>'
              '</force>' % tuple(fv))
        return m
    return build


def _mid31(r):
    """Knopen op x = L/2."""
    return _nodes_where(r, lambda p: abs(sum(p[k] * E1_31[k]
                                             for k in range(3)) - X31)
                        < 1e-9)


def _center31(r):
    """Knoop op x = L/2 in het midden van de breedte."""
    return [n for n in _mid31(r) if abs(sum(
        r.model.nodes[n - 1][k] * E2_31[k] for k in range(3)) - B31 / 2)
        < 1e-9]


def _width_mean31(r, var):
    """Gemiddelde over de breedte op x = L/2 (trapeziumregel over de
    knopen)."""
    d = r.step()[var]
    pts = sorted((sum(r.model.nodes[n - 1][k] * E2_31[k] for k in range(3)),
                  d[n]) for n in _mid31(r))
    area = sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in zip(pts,
                                                                 pts[1:]))
    return area / (pts[-1][0] - pts[0][0])


def _glob(sig_uu, comp, nu_ratio=0.0):
    """Globale component van sigma_uu e1 e1^T (+ nu_ratio x sigma_uu op
    e2 e2^T); schuif als tensor."""
    i, j = _IJ[comp]
    return sig_uu * (E1_31[i] * E1_31[j] + nu_ratio * E2_31[i] * E2_31[j])


def _ls31_checks(order, swap=False):
    src_t = ("plaattheorie op x = L/2: sigma_uu = N/t +- 6M/t^2, globaal "
             "sigma_uu e1 e1^T (" + SRC_MW + ")")
    u, v = ("v", "u") if swap else ("u", "v")
    out = [
        Check("N_%s (forceperlength%s)" % ("u", u),
              lambda r: _mean(r, "forceperlength" + u, _mid31(r)),
              ref=F31 / B31, tol=0.001, unit="N/m",
              source="evenwicht F/b; U-as van Mecway"),
        Check("M_%s (moment%s)" % ("u", u),
              lambda r: _mean(r, "moment" + u, _center31(r)),
              ref=P31 * (L31 - X31) / B31, tol=0.01, unit="N",
              source="P (L - x)/b; teken als " + SRC_MW),
    ]
    if swap:
        return out + [
            Check("N_v (forceperlengthu)",
                  lambda r: _mean(r, "forceperlengthu", _mid31(r)),
                  ref=0.0, tol_abs=30.0, unit="N/m",
                  source="U-as langs de breedte (orientationu*)")]
    for comp, lvl, sig in (("xx", "u1", SIG_TOP31), ("zz", "u1", SIG_TOP31),
                           ("xy", "u1", SIG_TOP31), ("xy", "b1", SIG_BOT31),
                           ("xx", "m1", SIG_MID31)):
        out.append(Check(
            "stress%s%s" % (comp, lvl),
            (lambda c, l: lambda r: _mean(r, "stress" + c + l,
                                          _center31(r)))(comp, lvl),
            ref=_glob(sig, comp), tol=0.01, unit="Pa", source=src_t))
    for comp, lvl, sig in (("xx", "u", SIG_TOP31), ("xy", "u", SIG_TOP31),
                           ("xx", "b", SIG_BOT31)):
        i, j = _IJ[comp]
        factor = 2.0 if i != j else 1.0
        out.append(Check(
            "lstrain%s%s" % (comp, lvl),
            (lambda c, l: lambda r: _mean(r, "lstrain" + c + l,
                                          _center31(r)))(comp, lvl),
            ref=factor * _glob(sig / E, comp, -NU), tol=0.01, unit="-",
            source="eps_uu = sigma/E, eps_vv = -nu sigma/E, eps_ww = 0; "
                   "schuif als gamma (" + SRC_MW + ")"))
    out.append(Check("factorofsafety", lambda r: _mean(
        r, "factorofsafety", _center31(r)), ref=S_T / SIG_TOP31, tol=0.01,
        source="S / max(sigma_vM boven, onder) (Mecway manual v34 par. "
               "8.7)"))
    if order == 2:
        out.append(Check("Q_u (shearuw), gemiddeld over de breedte",
                         lambda r: _width_mean31(r, "shearuw"),
                         ref=-P31 / B31, tol=0.01, unit="N/m",
                         source="dwarskracht -P/b; teken als " + SRC_MW +
                         " (verloopt over de breedte, ook in Mecway)"))
    return out


# ------------------------------------------------------------------
# LS-32 Totale rek en factor of safety in volume-elementen (strain,
# safety_factor)
# ------------------------------------------------------------------
# a) Staaf 100 x 10 x 10 mm (hex8), symmetrievlakken x, y, z = 0, trek
#    100 MPa op x = L: eps_xx = sigma/E, eps_yy = eps_zz = -nu sigma/E,
#    factor of safety S/sigma = 2,5.
# b) Kubus 10 mm (hex8) met zuivere afschuiving tau = 50 MPa op de vier
#    zijvlakken (evenwicht zonder steunpunten; alleen starre bewegingen
#    vastgezet): gamma_xy = tau/G (Mecway: lstrainxy is gamma, gemeten),
#    von Mises sqrt(3) tau, factor of safety S/(sqrt(3) tau).
L32, A32, SIG32, TAU32 = 0.100, 0.010, 100e6, 50e6


def build_ls32a():
    m = Model("S30")
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 4, 1, 1, box(0, L32, 0, A32, 0, A32))
    m.mat("Staal", STEEL, FAIL)
    for name, side, ax in (("SymX", "u0", "x"), ("SymY", "v0", "y"),
                           ("SymZ", "w0", "z")):
        m.node_selection(name, sorted(g["nodes"][side]))
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value><x>{x}</x>'
              '<y>{y}</y><z>{z}</z></displacement>'.format(name, **d))
    m.face_selection("Eind", g["faces"]["u1"])
    m.add('<traction selection="Eind"><x>%g MPa</x><y>0 Pa</y><z>0 Pa</z>'
          '</traction>' % (SIG32 / 1e6))
    return m


def build_ls32b():
    m = Model("S30")
    m.elset("Kubus", "Staal")
    g = hexmesh(m, "Kubus", 1, 1, 1, box(0, A32, 0, A32, 0, A32))
    m.mat("Staal", STEEL, FAIL)
    t = TAU32 / 1e6
    for side, vec in (("u0", (0, -t)), ("u1", (0, t)), ("v0", (-t, 0)),
                      ("v1", (t, 0))):
        m.face_selection("F_" + side, g["faces"][side])
        m.add('<traction selection="F_%s"><x>%g MPa</x><y>%g MPa</y>'
              '<z>0 Pa</z></traction>' % (side, vec[0], vec[1]))
    p0 = m.node(0, 0, 0)
    px = m.node(A32, 0, 0)
    py = m.node(0, A32, 0)
    m.node_selection("P0", [p0])
    m.node_selection("PX", [px])
    m.node_selection("PY", [py])
    m.add('<fixed selection="P0" />')
    for sel, ax in (("PX", "y"), ("PX", "z"), ("PY", "z")):
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value><x>{x}</x>'
              '<y>{y}</y><z>{z}</z></displacement>'.format(sel, **d))
    return m


def _ls32a_checks():
    mid = (L32 / 2, A32 / 2, A32 / 2)
    src = "eenassige trek: eps = sigma/E, -nu sigma/E"
    return [
        Check("lstrainxx", lambda r: r.at("lstrainxx", mid),
              ref=SIG32 / E, tol=1e-4, source=src),
        Check("lstrainyy", lambda r: r.at("lstrainyy", mid),
              ref=-NU * SIG32 / E, tol=1e-4, source=src),
        Check("lstrainzz", lambda r: r.at("lstrainzz", mid),
              ref=-NU * SIG32 / E, tol=1e-4, source=src),
        Check("factorofsafety", lambda r: r.at("factorofsafety", mid),
              ref=S_T / SIG32, tol=1e-4,
              source="S/sigma_vM (Mecway manual v34 par. 8.7)"),
    ]


def _ls32b_checks():
    c = (A32, A32, A32)
    return [
        Check("lstrainxy (gamma)", lambda r: r.at("lstrainxy", c),
              ref=TAU32 / G, tol=1e-4,
              source="zuivere afschuiving gamma = tau/G; Mecway: "
                     "technische schuifrek (gemeten)"),
        Check("lstrainxx", lambda r: r.at("lstrainxx", c), ref=0.0,
              tol_abs=1e-9, source="zuivere afschuiving"),
        Check("factorofsafety", lambda r: r.at("factorofsafety", c),
              ref=S_T / (math.sqrt(3) * TAU32), tol=1e-4,
              source="S / (sqrt(3) tau)"),
    ]


# ------------------------------------------------------------------
# NL-30 Contactdruk en contactstatus (contact)
# ------------------------------------------------------------------
# a) Contact-patchtest van NL-03 met hex8 en passende meshes (lineaire
#    vlakken: integratie in de knopen, Code-Aster maakt CONT_NOEU),
#    STANDARD: p = F/A = 10 MPa, status 1 op alle slave-knopen (CONT = 2
#    zonder wrijving wordt 1).
# b) Idem hex20 met PENALISATION (NL-03d; geen CONT_NOEU, alarm
#    CONTACT3_16: status uit de contactdruk).
# c) Twee balken met de tips op elkaar (NL-03b): status 1 aan de tip, 0
#    (open) aan het begin van de slave-zone, contactdruk daar 0.
def _nl():
    import tests_niet_lineair as T
    return T


def _patch_order1(T):
    """De patchtest van NL-03 (tests_niet_lineair.build_nl03_patch) met
    hex8 i.p.v. hex20."""
    m = Model("L30", timesteps=T._timesteps(1.0))
    m.elset("Onderblok", "Staal")
    # passende meshes (3 x 3 op 3 x 3): integratie in de knopen haalt de
    # patchtest met niet-passende meshes niet exact (NL-03, KNOWN_BUGS 43)
    lo = hexmesh(m, "Onderblok", 3, 3, 1, box(0, T.A4, 0, T.A4, -T.H4, 0))
    m._index = {}
    m.elset("Bovenblok", "Staal")
    up = hexmesh(m, "Bovenblok", 3, 3, 1, box(0, T.A4, 0, T.A4, 0, T.H4))
    T._elastic_mat(m, "Staal", T.NU4)
    m.node_selection("SymX", sorted(lo["nodes"]["u0"] | up["nodes"]["u0"]))
    m.node_selection("SymY", sorted(lo["nodes"]["v0"] | up["nodes"]["v0"]))
    m.node_selection("Bodem", sorted(lo["nodes"]["w0"]))
    for name, ax in (("SymX", "x"), ("SymY", "y"), ("Bodem", "z")):
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value><x>{x}</x>'
              '<y>{y}</y><z>{z}</z></displacement>'.format(name, **d))
    m.face_selection("Bovenkant", up["faces"]["w1"])
    m.face_selection("ContactOnder", lo["faces"]["w1"])
    m.face_selection("ContactBoven", up["faces"]["w0"])
    m.node_selection("SlaveKnopen", sorted(up["nodes"]["w0"]))
    m.add('<force selection="Bovenkant"><x>0 N</x><y>0 N</y>{0}</force>'
          .format(T._history("z", [(0.0, 0.0), (1.0, -T.F4)], "N")))
    m.add('<contact2 selectionmaster="ContactOnder" selectionslave='
          '"ContactBoven" type="unilateralelastic"><tolerance>0 m'
          '</tolerance><normalstiffness>%g GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>'
          % (T.KN4 / 1e9))
    return m


def build_nl30b():
    T = _nl()
    m = T.build_nl03_patch()
    return m


def _slave_mean(r, var):
    nids = [n for n in r.step()[var]]
    return sum(r.step()[var][n] for n in nids) / float(len(nids))


def _nl30_patch_checks():
    T = _nl()
    return [
        Check("contactpressure (gemiddeld)",
              lambda r: _slave_mean(r, "contactpressure"), ref=T.P4,
              tol=0.005, unit="Pa",
              source="patchtest: p = F/A (Mecway CCX: 9,99974e6 Pa)"),
        Check("contactpressure (kleinste)",
              lambda r: r.extreme("contactpressure", fn=min), ref=T.P4,
              tol=0.005, unit="Pa", source="p = F/A op elke slave-knoop"),
        Check("contactstate (kleinste)",
              lambda r: r.extreme("contactstate", fn=min), ref=1.0,
              tol_abs=1e-9, source="overal gesloten"),
    ]


def _nl30c_checks():
    T = _nl()
    # slave-zone: laatste 4 elementen van de bovenste balk; begin van de
    # zone x = L - 4 L/N ligt open (spleet 4/20 x 0,5 mm voor de last)
    x_open = T.L3 - 4 * T.L3 / T.N3

    def at_slave(r, var, x):
        d = r.step()[var]
        nids = [n for n in d if abs(r.model.nodes[n - 1][0] - x) < 1e-9]
        return max(d[n] for n in nids)
    return [
        Check("contactstate aan de tip", lambda r: at_slave(
            r, "contactstate", T.L3), ref=1.0, tol_abs=1e-9,
            source="lijncontact op x = L (NL-03)"),
        Check("contactstate begin zone", lambda r: at_slave(
            r, "contactstate", x_open), ref=0.0, tol_abs=1e-9,
            source="spleet blijft open"),
        Check("contactpressure begin zone", lambda r: at_slave(
            r, "contactpressure", x_open), ref=0.0, tol_abs=2.0e3,
            unit="Pa", source="open: druk 0 (Mecway CCX: 0); LAGS_C "
            "is daar niet exact 0 (~0,1% van de piek)"),
    ]


# ------------------------------------------------------------------
# NL-31 Green-Lagrange-rek bij grote rek (strain, niet-lineair)
# ------------------------------------------------------------------
# Staaf als NL-01 (hex20, symmetrievlakken), elastisch, opgelegde
# verlenging 5%: E_xx = (lambda^2 - 1)/2 = 0,05125 (kinematica, exact bij
# homogene rek). Mecway's niet-lineaire analyse geeft greenlagrangestrain*
# (CCX, headless gezien).
LAM31 = 1.05


def build_nl31():
    T = _nl()
    m = Model("L30", timesteps=T._timesteps(1.0))
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 2, 1, 1, box(0, T.L1, 0, T.A1, 0, T.A1),
                order=2)
    m.mat("Staal", STEEL)
    for name, side, ax in (("SymX", "u0", "x"), ("SymY", "v0", "y"),
                           ("SymZ", "w0", "z")):
        m.node_selection(name, sorted(g["nodes"][side]))
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value><x>{x}</x>'
              '<y>{y}</y><z>{z}</z></displacement>'.format(name, **d))
    m.node_selection("Trek", sorted(g["nodes"]["u1"]))
    m.add('<displacement selection="Trek">{0}<x>1</x><y>0</y><z>0</z>'
          '</displacement>'.format(T._history(
              "value", [(0.0, 0.0), (1.0, (LAM31 - 1) * T.L1 * 1e3)],
              "mm")))
    return m


def _nl31_checks():
    T = _nl()
    mid = (T.L1 / 2, T.A1 / 2, T.A1 / 2)
    return [Check("greenlagrangestrainxx", lambda r: r.at(
        "greenlagrangestrainxx", mid), ref=(LAM31 ** 2 - 1) / 2, tol=1e-4,
        source="E_xx = (lambda^2 - 1)/2 (homogene rek)")]


# ------------------------------------------------------------------
# NL-32 Snedekrachten van balken in STAT_NON_LINE (beam_forces)
# ------------------------------------------------------------------
# Model van LS-30 (recht) als L30: kleine verplaatsingen (balken blijven
# geometrisch lineair, KNOWN_BUGS 11), dus dezelfde statica op t = 1.
def build_nl32():
    m = build_ls30(0.0)()
    m.analysis = "L30"
    m.timesteps = _nl()._timesteps(1.0)
    return m


# ------------------------------------------------------------------
# MO-30 Snedekrachten per trillingsvorm (beam_forces, modaal)
# ------------------------------------------------------------------
# Ingeklemde balk van MO-01 (20 POU_D_E, 20 x 30 mm, L = 1 m). Eerste
# buigvorm W(x) (Blevins tabel 8-1): W''(0) = 2 lambda^2/L^2 en W(L) = 2,
# dus |M(0)| / |w(L)| = E I lambda1^2 / L^2, onafhankelijk van de
# normering (lambda1 = 1,8751, I = b a^3/12 om de zwakke as).
LAM_CF1 = 1.87510407
A_MO, B_MO = 0.02, 0.03
I_MO = B_MO * A_MO ** 3 / 12.0


def build_mo30():
    m = Model("V30", attrs={"maxmode": 2})
    m.elset("Balk", "Staal")
    _e, nids = linemesh(m, "Balk", 20, (0, 0, 0), (1.0, 0, 0))
    m.mat("Staal", '<geometric type="RectBar" recta="%g m" rectb="%g m" />'
          % (A_MO, B_MO), STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    return m


def _mo30_checks():
    def ratio(r):
        m = math.hypot(r.at("bendingmomv", (0, 0, 0), time=1),
                       r.at("bendingmomw", (0, 0, 0), time=1))
        w = math.hypot(r.at("disply", (1, 0, 0), time=1),
                       r.at("displz", (1, 0, 0), time=1))
        return m / w
    return [Check("|M(0)|/|w(L)| mode 1", ratio,
                  ref=E * I_MO * LAM_CF1 ** 2, tol=0.01, unit="N",
                  source="Euler-Bernoulli: E I lambda1^2 / L^2 (Blevins "
                         "tabel 8-1: W''(0) = 2 lambda^2, W(L) = 2)")]


# ------------------------------------------------------------------
# DY-30 Snedekrachten in DYNA_NON_LINE (beam_forces, dynamica)
# ------------------------------------------------------------------
# Balk van LS-30 (recht, met dichtheid), tipkracht V_w lineair opgebouwd in
# 2 s (eerste eigenperiode ~0,04 s: quasi-statisch), daarna constant tot
# 2,5 s. M_v in de inklemming = -V_w L op t = 2,5 s, binnen 2% (restant van
# de trilling, HHT-demping).
def build_dy30():
    import tests_dynamisch as D
    m = Model("D31", timesteps=D._timesteps(2.5, 0.05))
    m.elset("Balk", "Rect")
    _e, nids = linemesh(m, "Balk", 10, (0, 0, 0), (L30, 0, 0))
    m.mat("Rect", '<geometric type="RectBar" recta="0.02 m" '
          'rectb="0.03 m" />', STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y>%s</force>'
          % _nl()._history("z", [(0.0, 0.0), (2.0, VW30), (2.5, VW30)],
                           "N"))
    return m


TESTS = [
    Case("LS-30", GROUP_LS, "Snedekrachten ingeklemde balk (beam_forces)",
         "lin_static_3d", build_ls30(0.0), _ls30_checks(0.0),
         note="POU_D_E; EFGE_ELNO/EFGE_NOEU, Mecway-namen en -tekens."),
    Case("LS-30b", GROUP_LS, "Snedekrachten schuine balk (lokale assen)",
         "lin_static_3d", build_ls30(30.0), _ls30_checks(30.0),
         note="Balk onder 30 graden in het XY-vlak."),
    Case("LS-31", GROUP_LS, "Schaalstrook scheef in de ruimte: tensor, "
         "rek, krachten per lengte, factor of safety (quad4, DKT)",
         "lin_static_3d", build_ls31(1), _ls31_checks(1),
         settings={"fields": _fields("shell_stresses", "shell_forces",
                                     "strain", "safety_factor")},
         note="Lokale assen van Code-Aster (projectie van X) en Mecway "
              "(rand 1-2) verschillen; de bridge draait beide."),
    Case("LS-31b", GROUP_LS, "Idem quad8 (COQUE_3D), ook de dwarskracht",
         "lin_static_3d", build_ls31(2), _ls31_checks(2),
         settings={"fields": _fields("shell_stresses", "shell_forces",
                                     "strain", "safety_factor")}),
    Case("LS-31c", GROUP_LS, "Idem quad4 met een eigen U-as "
         "(orientationu* = breedterichting)", "lin_static_3d",
         build_ls31(1, orient=E2_31), _ls31_checks(1, swap=True),
         settings={"fields": _fields("shell_forces")},
         note="Mecway's U langs e2: N_u wordt forceperlengthv."),
    Case("LS-32", GROUP_LS, "Totale rek en factor of safety, eenassige "
         "trek (hex8)", "lin_static_3d", build_ls32a, _ls32a_checks(),
         settings={"fields": _fields("strain", "safety_factor")}),
    Case("LS-32b", GROUP_LS, "Totale rek en factor of safety, zuivere "
         "afschuiving (hex8)", "lin_static_3d", build_ls32b,
         _ls32b_checks(),
         settings={"fields": _fields("strain", "safety_factor")}),
    Case("NL-30", GROUP_NL, "Contactdruk en -status, patchtest hex8 "
         "(CONT_NOEU)", "nonlin_static_3d", lambda: _patch_order1(_nl()),
         _nl30_patch_checks(), settings={"contact_algo": "STANDARD"}),
    Case("NL-30b", GROUP_NL, "Contactdruk en -status, patchtest hex20 "
         "(PENALISATION, LAGS_C)", "nonlin_static_3d", build_nl30b,
         _nl30_patch_checks(), settings={"contact_algo": "PENALISATION"}),
    Case("NL-30c", GROUP_NL, "Contactstatus open/gesloten, balktips "
         "(PENALISATION)", "nonlin_static_3d", lambda: _nl().build_nl03(),
         _nl30c_checks(), settings={"contact_algo": "PENALISATION"}),
    Case("NL-31", GROUP_NL, "Green-Lagrange-rek bij 5% rek (strain)",
         "nonlin_static_3d", build_nl31, _nl31_checks(),
         settings={"fields": _fields("strain")}),
    Case("NL-32", GROUP_NL, "Snedekrachten balk in STAT_NON_LINE",
         "nonlin_static_3d", build_nl32, _ls30_checks(0.0)),
    Case("MO-30", GROUP_MO, "Buigmoment per trillingsvorm (beam_forces)",
         "modal_3d", build_mo30, _mo30_checks(),
         settings={"fields": ["displacements", "beam_forces"]}),
    Case("DY-30", GROUP_DY, "Snedekrachten in DYNA_NON_LINE, quasi-statisch",
         "dyna_impl_3d", build_dy30,
         [Check("M_v inklemming", lambda r: r.at("bendingmomv", (0, 0, 0)),
                ref=-VW30 * L30, tol=0.02, unit="N.m",
                source="statica (last in 50 eigenperiodes opgebouwd)")]),
]
