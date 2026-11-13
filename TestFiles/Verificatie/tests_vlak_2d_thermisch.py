# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Thermal stress in 2D and axisymmetric (STAPPENPLAN S44c; Scripts/
bridge_plane.py): Mecway Static 2D (S20 -> C_PLAN / D_PLAN) and Static
Axisymmetric (SA0 -> AXIS) with Thermal stress and Temperature / Node
temperature, linear static (MECA_STATIQUE, AFFE_VARC TEMP). Explanation:
docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-20  ring (AXIS), uniform temperature on a node selection, free:
       u = alpha dT x, all stress components zero.
PL-21  plate (C_PLAN), uniform temperature on an element selection, free.
PL-22  the same plate held on all edges (C_PLAN):
       sigma_xx = sigma_yy = -E alpha dT / (1 - nu), sigma_zz = 0.
PL-23  the same in plane strain (D_PLAN):
       sigma_xx = sigma_yy = sigma_zz = -E alpha dT / (1 - 2 nu).
PL-24  thick tube with the steady radial temperature T(r) = T_a + (T_b -
       T_a) ln(r/a) / ln(b/a) as Node temperatures, AXIS, both ends held
       axially (plane strain): sigma_r, sigma_theta, sigma_z against the
       closed form (Timoshenko & Goodier par. 150), 8 quad8 through the
       wall; u_r at both walls; the axial reaction over 360 degrees.
PL-25  the same tube with plane free ends (AXIS, top edge LIAISON_UNIF DY
       from #ASTER lines): generalised plane strain, u_y of the top edge.
PL-26  the same tube in plane strain (D_PLAN, quarter ring).
PL-27  solid disc (AXIS, nodes on the axis held in X), free: u_r = alpha
       dT r, no stress.
PL-28  the plate of PL-21 with the temperature on a face selection of the
       right edge only (the other nodes at the reference): = Mecway.

Mecway's own solution (Mecway 35.0.9802, headless, 13 Nov 2026) of the same
models: displacements and reactions equal to the bridge within 1e-13 in
PL-20 .. PL-24, PL-26 .. PL-28 (so Mecway interpolates the node
temperatures within the element in 2D too, KNOWN_BUGS 17), stresses of the
held plates (sigma_zz of D_PLAN included) within 1e-15; nodal stresses of
the tube differ by Mecway's stress recovery (KNOWN_BUGS 3: 0.5 .. 5%).
PL-25 has no Mecway counterpart (Mecway ignores the #ASTER line). A
Temperature with a time table (0/1/2 s: 293/393/493 K) in PL-21 gives no
expansion in Mecway's S20, as the bridge's WARNING says (the bridge drops
it in MECA_STATIQUE). The "= Mecway" checks hold the values.
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
E, NU, ALPHA = 210e9, 0.3, 1.2e-5
TREF, DT = 293.0, 100.0
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" thermalexpansion="1.2e-05 1/K" />')
SCALE = E * ALPHA * DT          # stress scale for "no stress" checks
_COMPS = ("stressxx", "stressyy", "stresszz", "stressxy")


def _fields(m):
    for fv in ("displacement", "stress", "von Mises stress",
               "reaction force"):
        m.add('<fieldvariable name="%s" />' % fv)


def _thermal(m):
    m.add('<thermalstress><referencetemperature>%g K</referencetemperature>'
          '</thermalstress>' % TREF)


def _uniform(m, sel):
    m.add('<temperature2 selection="%s"><value>%g K</value>'
          '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
          % (sel, TREF + DT))


def _max_stress(r):
    """Largest |sigma_ij| over all nodes and in-plane/zz components."""
    return max(max(abs(v) for v in r.step()[c].values()) for c in _COMPS)


def _no_stress():
    return Check("max |sigma_ij|", _max_stress, ref=0.0,
                 tol_abs=1e-6 * SCALE, unit="Pa",
                 source="vrije uitzetting: geen spanning (alle componenten)")


def _no_shear():
    return Check("max |sigma_xy|",
                 lambda r: max(abs(v) for v in r.step()["stressxy"].values()),
                 ref=0.0, tol_abs=1e-6 * SCALE, unit="Pa",
                 source="uniforme toestand: geen schuifspanning")


# ------------------------------------------------------------------
# PL-20 free ring, PL-27 solid disc, uniform temperature (AXIS)
# ------------------------------------------------------------------
RA, RB, H = 0.1, 0.2, 0.01


def build_ring(r0, n):
    def build():
        m = Model("SA0")
        m.elset("Ring", "Staal")
        q = quadmesh(m, "Ring", n, 1, rect(r0, RB, 0.0, H), order=2)
        m.mat("Staal", STEEL)
        m.face_selection("Onder", q["edges"]["v0"])
        m.add('<displacement selection="Onder"><value>0 m</value><x>0</x>'
              '<y>1</y><z>0</z></displacement>')
        if r0 == 0.0:
            # Mecway manual v34 par. 7.2: nodes on the axis held in X
            m.face_selection("As", q["edges"]["u0"])
            m.add('<displacement selection="As"><value>0 m</value><x>1</x>'
                  '<y>0</y><z>0</z></displacement>')
        m.node_selection("Alle", range(1, len(m.nodes) + 1))
        _thermal(m)
        _uniform(m, "Alle")
        _fields(m)
        return m
    return build


# ------------------------------------------------------------------
# PL-21 .. PL-23, PL-28 plate, uniform temperature (C_PLAN / D_PLAN)
# ------------------------------------------------------------------
LX, LY, T2 = 0.1, 0.05, 0.01


def build_plate(held=False, strain=False, edges=False):
    def build():
        m = Model("S20")
        m.elset("Plaat", "Staal")
        q = quadmesh(m, "Plaat", 4, 2, rect(0.0, LX, 0.0, LY), order=2)
        m.mat("Staal", '<geometric type="Plate" thickness="%g mm"%s />' % (
            T2 * 1000, ' planestrain="1"' if strain else ""), STEEL)
        e = q["edges"]
        if held:
            m.face_selection("Rand", e["u0"] + e["u1"] + e["v0"] + e["v1"])
            m.add('<fixed selection="Rand" />')
        else:
            m.face_selection("SymX", e["u0"])
            m.face_selection("SymY", e["v0"])
            m.add('<symmetry selection="SymX"><x>1</x><y>0</y><z>0</z>'
                  '</symmetry>')
            m.add('<symmetry selection="SymY"><x>0</x><y>1</y><z>0</z>'
                  '</symmetry>')
        _thermal(m)
        if edges:
            m.face_selection("Rechts", e["u1"])
            _uniform(m, "Rechts")
        else:
            m.element_selection("Alles", sorted(q["elems"].values()))
            _uniform(m, "Alles")
        _fields(m)
        return m
    return build


SIG_CPLAN = -E * ALPHA * DT / (1.0 - NU)
SIG_DPLAN = -E * ALPHA * DT / (1.0 - 2.0 * NU)
_MID = (LX / 2, LY / 2, 0.0)


def _free_plate_checks():
    return [Check("u_x rechts", lambda r: r.at("displx", (LX, LY, 0.0)),
                  ref=ALPHA * DT * LX, tol=1e-6, unit="m",
                  source="vrije uitzetting: alpha dT x"),
            Check("u_y boven", lambda r: r.at("disply", (LX, LY, 0.0)),
                  ref=ALPHA * DT * LY, tol=1e-6, unit="m",
                  source="vrije uitzetting: alpha dT y"),
            _no_stress()]


# ------------------------------------------------------------------
# PL-24 .. PL-26 thick tube, logarithmic temperature
# ------------------------------------------------------------------
TA, TB = TREF + DT, TREF          # inner wall hot, outer at the reference
NR = 8                            # quad8 through the wall


def theta(r):
    """Temperature above the reference at radius r."""
    return TA - TREF + (TB - TA) * math.log(r / RA) / math.log(RB / RA)


def _integral(r, n=2000):
    """int_a^r theta(s) s ds (Simpson)."""
    if r <= RA:
        return 0.0
    h = (r - RA) / n
    s = theta(RA) * RA + theta(r) * r
    for i in range(1, n):
        x = RA + i * h
        s += (4 if i % 2 else 2) * theta(x) * x
    return s * h / 3.0


_IB = _integral(RB)
_K = ALPHA * E / (1.0 - NU)
EPS0 = 2.0 * ALPHA * _IB / (RB ** 2 - RA ** 2)   # free ends: axial strain


def sig_r(r):
    return _K / r ** 2 * ((r ** 2 - RA ** 2) / (RB ** 2 - RA ** 2) * _IB -
                          _integral(r))


def sig_t(r):
    return _K / r ** 2 * ((r ** 2 + RA ** 2) / (RB ** 2 - RA ** 2) * _IB +
                          _integral(r) - theta(r) * r ** 2)


def sig_z(r, free):
    """free: generalised plane strain with zero axial resultant; else
    plane strain (eps_z = 0)."""
    c = 2.0 if free else 2.0 * NU
    return _K * (c * _IB / (RB ** 2 - RA ** 2) - theta(r))


def u_r(r, free):
    """Radial displacement (Timoshenko & Goodier par. 150): plane strain,
    and for free ends minus nu eps0 r (a uniform axial strain eps0 with a
    free lateral contraction)."""
    u = (1.0 + NU) / (1.0 - NU) * ALPHA * (
        _integral(r) / r + ((1.0 - 2.0 * NU) * r ** 2 + RA ** 2) /
        (r * (RB ** 2 - RA ** 2)) * _IB)
    return u - NU * EPS0 * r if free else u


def _node_temps(m, axis):
    """Node temperatures T(r); radius = X in SA0 (Y is the axis), the
    distance to the origin in the plane quarter ring."""
    def radius(p):
        return p[0] if axis else math.hypot(p[0], p[1])
    lines = "".join('<nodetemperature nid="%d" value="%.12g K" />' % (
        i + 1, TREF + theta(radius(p))) for i, p in enumerate(m.nodes))
    m.add("<temperature3>%s</temperature3>" % lines)


def build_tube_axis(free):
    def build():
        m = Model("SA0")
        m.elset("Buis", "Staal")
        q = quadmesh(m, "Buis", NR, 1, rect(RA, RB, 0.0, H), order=2)
        m.mat("Staal", STEEL)
        e = q["edges"]
        m.face_selection("Onder", e["v0"])
        m.face_selection("Boven", e["v1"])
        m.node_selection("Ondern", sorted(q["nodes"]["v0"]))
        m.add('<displacement selection="Onder"><value>0 m</value><x>0</x>'
              '<y>1</y><z>0</z></displacement>')
        if free:
            m.add(u"<ccxmodeldefinition>#ASTER vlak = AFFE_CHAR_MECA("
                  u"MODELE=model, LIAISON_UNIF=_F(GROUP_MA="
                  u"'&lt;&lt;Boven&gt;&gt;', DDL='DY'))\n"
                  u"#ASTER-EXCIT vlak</ccxmodeldefinition>")
        else:
            m.add('<displacement selection="Boven"><value>0 m</value>'
                  '<x>0</x><y>1</y><z>0</z></displacement>')
        _thermal(m)
        _node_temps(m, True)
        _fields(m)
        return m
    return build


def _ring(u, v):
    r = RA + u * (RB - RA)
    t = v * math.pi / 2
    return (r * math.cos(t), r * math.sin(t), 0.0)


def build_tube_plane():
    m = Model("S20")
    m.elset("Buis", "Staal")
    q = quadmesh(m, "Buis", NR, 4 * NR, _ring, order=2)
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" '
          'planestrain="1" />', STEEL)
    e = q["edges"]
    m.face_selection("SymY0", e["v0"])
    m.face_selection("SymX0", e["v1"])
    m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
          '</symmetry>')
    m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
          '</symmetry>')
    _thermal(m)
    _node_temps(m, False)
    _fields(m)
    return m


RM = 0.5 * (RA + RB)
# Mecway 35 headless, own S20/SA0 solution (see the header)
MW = {"PL-22": -360000000.0, "PL-23": -629999999.9999999,
      "PL-24": (6.053106114619562e-05, 0.00012106083609759922,
                9215506.401755054),
      "PL-26": (6.053095396682345e-05, 0.000121060803295287),
      "PL-28": (-8.820038430787978e-06, 2.725955332871129e-05)}
_MW_SRC = "Mecway 35 headless, eigen S20/SA0-oplossing"


def _mw_ur(cid):
    return [Check("u_r binnenwand = Mecway",
                  lambda r: r.at("displx", (RA, 0.0, 0.0)), ref=MW[cid][0],
                  tol=1e-6, unit="m", in_series=False, source=_MW_SRC),
            Check("u_r buitenwand = Mecway",
                  lambda r: r.at("displx", (RB, 0.0, 0.0)), ref=MW[cid][1],
                  tol=1e-6, unit="m", in_series=False, source=_MW_SRC)]


def _tube_checks(free, comp):
    """comp: Mecway names of (sigma_r, sigma_theta, sigma_z)."""
    sr, st, sz = comp
    src = ("Timoshenko & Goodier par. 150, " +
           ("vrije vlakke einden" if free else "vlakke rek"))
    return [
        Check("u_r binnenwand", lambda r: r.at("displx", (RA, 0.0, 0.0)),
              ref=u_r(RA, free), tol=1e-4, unit="m", source=src),
        Check("u_r buitenwand", lambda r: r.at("displx", (RB, 0.0, 0.0)),
              ref=u_r(RB, free), tol=1e-4, unit="m", source=src),
        # sigma_r (small, 13% of the peak hoop stress) converges as h^2
        # from the integration points: 4.28 / 1.04 / 0.26% at 4 / 8 / 16
        # quad8 through the wall (AXIS); tolerance 1.2% as sigma_r of
        # PL-04 (the same recovery under pressure)
        Check("sigma_r midden", lambda r: r.at(sr, (RM, 0.0, 0.0)),
              ref=sig_r(RM), tol=0.012, unit="Pa", source=src),
        Check("sigma_theta binnenwand", lambda r: r.at(st, (RA, 0.0, 0.0)),
              ref=sig_t(RA), tol=0.01, unit="Pa", source=src),
        Check("sigma_theta buitenwand", lambda r: r.at(st, (RB, 0.0, 0.0)),
              ref=sig_t(RB), tol=0.01, unit="Pa", source=src),
        Check("sigma_z binnenwand", lambda r: r.at(sz, (RA, 0.0, 0.0)),
              ref=sig_z(RA, free), tol=0.01, unit="Pa", source=src),
        Check("sigma_z buitenwand", lambda r: r.at(sz, (RB, 0.0, 0.0)),
              ref=sig_z(RB, free), tol=0.01, unit="Pa", source=src)]


TESTS = []

TESTS.append(Case(
    "PL-20", GROUP, "Vrije ring, uniforme temperatuur (AXIS)",
    "lin_static_3d", build_ring(RA, 4),
    [Check("u_r binnenwand", lambda r: r.at("displx", (RA, 0.0, 0.0)),
           ref=ALPHA * DT * RA, tol=1e-6, unit="m",
           source="vrije uitzetting: alpha dT r"),
     Check("u_r buitenwand", lambda r: r.at("displx", (RB, 0.0, 0.0)),
           ref=ALPHA * DT * RB, tol=1e-6, unit="m",
           source="vrije uitzetting: alpha dT r"),
     Check("u_y boven", lambda r: r.at("disply", (RB, H, 0.0)),
           ref=ALPHA * DT * H, tol=1e-6, unit="m",
           source="vrije uitzetting: alpha dT h"),
     _no_stress()],
    note="Ring r = 0,1..0,2 m, h = 10 mm, quad8 4x1, Y vast onder, "
         "temperature2 +100 K op een knoopselectie."))

TESTS.append(Case(
    "PL-21", GROUP, "Vrije plaat, uniforme temperatuur (C_PLAN)",
    "lin_static_3d", build_plate(), _free_plate_checks(),
    note="Plaat 100 x 50 mm, t = 10 mm, quad8 4x2, symmetrie x = 0 en "
         "y = 0, temperature2 +100 K op een elementselectie."))

TESTS.append(Case(
    "PL-22", GROUP, "Plaat rondom vast, uniforme temperatuur (C_PLAN)",
    "lin_static_3d", build_plate(held=True),
    [Check("sigma_xx", lambda r: r.at("stressxx", _MID), ref=SIG_CPLAN,
           tol=1e-6, unit="Pa", source="-E alpha dT / (1 - nu)"),
     Check("sigma_yy", lambda r: r.at("stressyy", _MID), ref=SIG_CPLAN,
           tol=1e-6, unit="Pa", source="-E alpha dT / (1 - nu)"),
     Check("sigma_zz", lambda r: r.at("stresszz", _MID), ref=0.0,
           tol_abs=1e-6 * SCALE, unit="Pa", source="vlakke spanning"),
     _no_shear(),
     Check("sigma_xx = Mecway", lambda r: r.at("stressxx", _MID),
           ref=MW["PL-22"], tol=1e-6, unit="Pa", in_series=False,
           source=_MW_SRC)],
    note="Als PL-21, fixed op alle randen."))

TESTS.append(Case(
    "PL-23", GROUP, "Plaat rondom vast, uniforme temperatuur (D_PLAN)",
    "lin_static_3d", build_plate(held=True, strain=True),
    [Check("sigma_xx", lambda r: r.at("stressxx", _MID), ref=SIG_DPLAN,
           tol=1e-6, unit="Pa", source="-E alpha dT / (1 - 2 nu)"),
     Check("sigma_yy", lambda r: r.at("stressyy", _MID), ref=SIG_DPLAN,
           tol=1e-6, unit="Pa", source="-E alpha dT / (1 - 2 nu)"),
     Check("sigma_zz", lambda r: r.at("stresszz", _MID), ref=SIG_DPLAN,
           tol=1e-6, unit="Pa", source="-E alpha dT / (1 - 2 nu)"),
     _no_shear(),
     Check("sigma_zz = Mecway", lambda r: r.at("stresszz", _MID),
           ref=MW["PL-23"], tol=1e-6, unit="Pa", in_series=False,
           source=_MW_SRC)],
    note="Als PL-22 met planestrain=\"1\"."))

TESTS.append(Case(
    "PL-24", GROUP, "Dikwandige buis, ln-temperatuur, vlakke rek (AXIS)",
    "lin_static_3d", build_tube_axis(False),
    _tube_checks(False, ("stressxx", "stresszz", "stressyy")) + [
        Check("som R_y onder (360 graden)",
              lambda r: r.total("reactionforcey", "Ondern"),
              ref=2.0 * math.pi * ALPHA * E * _IB, tol=1e-4, unit="N",
              in_series=False,
              source="-int sigma_z 2 pi r dr = 2 pi alpha E int theta r "
                     "dr (vlakke rek)"),
        Check("som R_y onder = Mecway",
              lambda r: r.total("reactionforcey", "Ondern"),
              ref=MW["PL-24"][2], tol=1e-6, unit="N", in_series=False,
              source=_MW_SRC)] + _mw_ur("PL-24"),
    note="Ring r = 0,1..0,2 m, h = 10 mm, quad8 8x1, Y vast op beide "
         "einden, Node temperature T(r) = 393 .. 293 K (ln)."))

TESTS.append(Case(
    "PL-25", GROUP, "Dikwandige buis, ln-temperatuur, vrije vlakke einden "
    "(AXIS)", "lin_static_3d", build_tube_axis(True),
    _tube_checks(True, ("stressxx", "stresszz", "stressyy")) + [
        Check("u_y bovenrand", lambda r: r.at("disply", (RB, H, 0.0)),
              ref=EPS0 * H, tol=1e-4, unit="m",
              source="eps0 h, eps0 = 2 alpha int theta r dr / (b^2 - a^2)"),
        Check("som R_y onder (axiale resultante)",
              lambda r: r.total("reactionforcey", "Ondern"), ref=0.0,
              tol_abs=1e-6 * SCALE * math.pi * (RB ** 2 - RA ** 2),
              unit="N", in_series=False,
              source="vrije einden: geen axiale kracht")],
    note="Als PL-24, bovenrand vlak maar vrij (#ASTER LIAISON_UNIF DY)."))

TESTS.append(Case(
    "PL-26", GROUP, "Dikwandige buis, ln-temperatuur, vlakke rek (D_PLAN)",
    "lin_static_3d", build_tube_plane,
    _tube_checks(False, ("stressxx", "stressyy", "stresszz")) +
    _mw_ur("PL-26"),
    note="Kwart ring quad8 8x32, symmetrie x = 0 en y = 0, Node "
         "temperature T(r)."))

TESTS.append(Case(
    "PL-27", GROUP, "Volle schijf, uniforme temperatuur (AXIS)",
    "lin_static_3d", build_ring(0.0, 4),
    [Check("u_r buitenwand", lambda r: r.at("displx", (RB, 0.0, 0.0)),
           ref=ALPHA * DT * RB, tol=1e-6, unit="m",
           source="vrije uitzetting: alpha dT r"),
     Check("u_y boven", lambda r: r.at("disply", (RB, H, 0.0)),
           ref=ALPHA * DT * H, tol=1e-6, unit="m",
           source="vrije uitzetting: alpha dT h"),
     _no_stress()],
    note="Schijf r = 0..0,2 m, h = 10 mm, quad8 4x1, knopen op de as X "
         "vast, Y vast onder."))

TESTS.append(Case(
    "PL-28", GROUP, "Plaat, temperatuur op een rand (C_PLAN)",
    "lin_static_3d", build_plate(edges=True),
    [Check("u_x(L, H) = Mecway", lambda r: r.at("displx", (LX, LY, 0.0)),
           ref=MW["PL-28"][0], tol=1e-6, unit="m", in_series=False,
           source=_MW_SRC),
     Check("u_y(L, H) = Mecway", lambda r: r.at("disply", (LX, LY, 0.0)),
           ref=MW["PL-28"][1], tol=1e-6, unit="m", in_series=False,
           source=_MW_SRC)],
    note="Als PL-21, temperature2 +100 K op een vlakselectie van alleen "
         "de rechterrand (de andere knopen op de referentie)."))
