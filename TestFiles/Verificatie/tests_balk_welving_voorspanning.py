# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
POU_D_TG: nodal reactions and the stress state for RIGI_GEOM, which do not
come from MECA_STATIQUE (SIEF_ELGA of te0342.F90 is wrong, KNOWN_BUGS 123,
bridge_to_aster._stress_step). Explanation: docs/Verificatie.md (par. Balken
met welving).

- LS-96: the C cantilever of LS-94: reactions against equilibrium, also
  at free nodes (136 kN at the free tip before the fix).
- LS-96b: C beam on fork supports, load at midspan: 500 N per support
  (about 50 kN before the fix).
- LS-96c: I cantilever with only an imposed tip displacement (no external
  force, the convergence criterion must not stick) against the closed form.
- LS-96d: C cantilever with a plate at the tip (POU_D_TG with DKT).
- LS-96e: the same with the plate on elastic support (springs BRES*).
- LS-96f: I beam clamped at both ends, uniform temperature: E A alpha dT.
- LS-96g: the same with a free end: no reaction (te0342 has no thermal
  strain, a constant field gives none in STAT_NON_LINE).
- BU-45: C cantilever under a transverse tip load: twist in the base state
  with EZ <> 0, the case where MECA_STATIQUE gives a wrong moment in
  RIGI_GEOM (factor 1.6 before the fix). Against BU-45b.
- BU-45b: the same cantilever as hex20; Code-Aster = Mecway 34's own solver.
- BU-45c/BU-45d: the same pair with a dead axial load (#ASTER-CONSTANT).
- BU-46: restrained thermal expansion as the stress state of buckling.
- MP-20/MP-20b: the BU-45 pair as modal with prestress.
"""
import math
from verif_lib import Case, Check, Model, hexmesh, quadmesh, box, rect
import tests_balkorientatie as BO
import tests_knik_balk as KB

TG = {"elem_beam": "POU_D_TG"}
TESTS = []
STEEL, DENS = BO.STEEL, BO.DENS
E, G = BO.E, BO.G
F = 1000.0
L = 1.0
ROOT, TIP, MID = (0.0, 0.0, 0.0), (L, 0.0, 0.0), (L / 2, 0.0, 0.0)
EQ = "equilibrium of the whole beam"


def _beam(n=20, analysis="S30", attrs=None):
    m = Model(analysis, attrs=attrs or {})
    m.elset("Balk", "Mat")
    nids = [m.node(L * i / float(n), 0, 0) for i in range(n + 1)]
    for i in range(n):
        m.elem("Balk", "line2", [nids[i], nids[i + 1]])
    return m, nids


def _free_nodes(r, skip):
    """Largest reaction force at a node that is not supported."""
    forces = r.step()["reactionforcemag"]
    return max(abs(v) for n, v in forces.items() if n not in skip)


def build_ls96():
    m, nids = _beam()
    m.mat("Mat", KB.CPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>0 N</z></force>' % F)
    return m


TESTS.append(Case(
    "LS-96", "Lineair statisch", "Reactions of POU_D_TG: C cantilever",
    "lin_static_3d", build_ls96,
    [Check("clamp, force along Y", lambda r: r.at("reactionforcey", ROOT),
           ref=-F, tol=1e-6, unit="N", source=EQ),
     Check("clamp, moment about Z", lambda r: r.at("reactionmomz", ROOT),
           ref=-F * L, tol=1e-6, unit="N m", source=EQ),
     Check("clamp, moment about X", lambda r: r.at("reactionmomx", ROOT),
           ref=0.0, tol_abs=1e-6, unit="N m",
           source="T about the mesh line is 0: load through the centroid"),
     Check("largest force at a free node",
           lambda r: _free_nodes(r, [1]), ref=0.0, tol_abs=1e-6, unit="N",
           source="no support, no reaction")],
    general=TG,
    note="Model of LS-94. REAC_NODA of MECA_STATIQUE gives -15670 N at the "
         "clamp and +136260 N at the free tip."))


def build_ls96b():
    m, nids = _beam()
    m.mat("Mat", KB.CPROF, STEEL, DENS)
    for name, nid, axial in (("A1", nids[0], True), ("A2", nids[-1], False)):
        m.node_selection(name, [nid])
        for d, on in (("<x>1</x><y>0</y><z>0</z>", axial),
                      ("<x>0</x><y>1</y><z>0</z>", True),
                      ("<x>0</x><y>0</y><z>1</z>", True)):
            if on:
                m.add('<displacement selection="%s"><value>0 mm</value>%s'
                      '</displacement>' % (name, d))
        m.add('<noderotation selection="%s"><value>0 rad</value><x>1</x>'
              '<y>0</y><z>0</z></noderotation>' % name)
    m.node_selection("Midden", [nids[10]])
    m.add('<force selection="Midden"><x>0 N</x><y>%g N</y><z>0 N</z></force>'
          % F)
    return m


TESTS.append(Case(
    "LS-96b", "Lineair statisch", "Reactions of POU_D_TG: C on fork supports",
    "lin_static_3d", build_ls96b,
    [Check("support 1, force along Y", lambda r: r.at("reactionforcey", ROOT),
           ref=-F / 2, tol=1e-6, unit="N", source=EQ),
     Check("support 2, force along Y", lambda r: r.at("reactionforcey", TIP),
           ref=-F / 2, tol=1e-6, unit="N", source=EQ),
     Check("largest force at a free node",
           lambda r: _free_nodes(r, [1, 21]), ref=0.0, tol_abs=1e-6, unit="N",
           source="no support, no reaction")],
    general=TG, note="REAC_NODA of MECA_STATIQUE gives -49696 N (other "
                     "material constants) against -500 N."))

# I 100/50/10/8 mm as the bridge computes it (.comm of LS-90)
I_A, I_IZ, I_AY = 0.00164, 2.3746666666666665e-06, 2.2777777777777777
D96 = 0.001
FLEX96 = L ** 3 / (3 * E * I_IZ) + L * I_AY / (G * I_A)


def build_ls96c():
    m, nids = _beam()
    m.mat("Mat", BO.IPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<displacement selection="Tip"><value>%r m</value><x>0</x><y>1</y>'
          '<z>0</z></displacement>' % D96)
    return m


SRC96C = "delta = F L^3/(3 E I) + F L AY/(G A), Timoshenko cantilever"
TESTS.append(Case(
    "LS-96c", "Lineair statisch", "Reactions of POU_D_TG: only an imposed "
    "displacement", "lin_static_3d", build_ls96c,
    [Check("force at the tip", lambda r: r.at("reactionforcey", TIP),
           ref=D96 / FLEX96, tol=1e-4, unit="N", source=SRC96C),
     Check("force at the clamp", lambda r: r.at("reactionforcey", ROOT),
           ref=-D96 / FLEX96, tol=1e-4, unit="N", source=SRC96C)],
    general=TG, note="No external force: RESI_GLOB_RELA alone would stick."))


def _with_plate(support):
    """C cantilever that runs on along the middle of a plate 200 x 200 mm at
    its tip; load at the end of that line."""
    m, nids = _beam()
    m.elset("Blad", "Plaat")
    q = quadmesh(m, "Blad", 2, 2, rect(L, L + 0.2, -0.1, 0.1))
    last = nids[-1]
    for x in (L + 0.1, L + 0.2):
        nid = m.node(x, 0, 0)
        m.elem("Balk", "line2", [last, nid])
        last = nid
    m.mat("Mat", KB.CPROF, STEEL, DENS)
    m.mat("Plaat", '<geometric type="Plate" thickness="10 mm" />', STEEL,
          DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Last", [last])
    m.add('<force selection="Last"><x>0 N</x><y>%g N</y><z>%g N</z></force>'
          % (F, F))
    if support:
        m.face_selection("Vlak", q["faces"])
        m.add('<elasticsupport selection="Vlak"><modulus>1e8 N/m³</modulus>'
              '<tangential>0 N/m³</tangential></elasticsupport>')
    return m


def _all_y(r):
    return sum(r.step()["reactionforcey"].values())


def _all_z(r):
    return sum(r.step()["reactionforcez"].values())


R_TIP = L + 0.2
TESTS.append(Case(
    "LS-96d", "Lineair statisch", "Reactions of POU_D_TG with a plate (DKT)",
    "lin_static_3d", lambda: _with_plate(False),
    [Check("clamp, force along Y", lambda r: r.at("reactionforcey", ROOT),
           ref=-F, tol=1e-6, unit="N", source=EQ),
     Check("clamp, force along Z", lambda r: r.at("reactionforcez", ROOT),
           ref=-F, tol=1e-6, unit="N", source=EQ),
     Check("clamp, moment about Y", lambda r: r.at("reactionmomy", ROOT),
           ref=F * R_TIP, tol=1e-6, unit="N m", source=EQ),
     Check("clamp, moment about Z", lambda r: r.at("reactionmomz", ROOT),
           ref=-F * R_TIP, tol=1e-6, unit="N m", source=EQ)],
    general=TG))
TESTS.append(Case(
    "LS-96e", "Lineair statisch", "Reactions of POU_D_TG with elastic "
    "support (springs)", "lin_static_3d", lambda: _with_plate(True),
    [Check("sum along Z, clamp plus springs", _all_z, ref=-F, tol=1e-6,
           unit="N", source=EQ),
     Check("sum along Y (no spring along Y)", _all_y, ref=-F, tol=1e-6,
           unit="N", source=EQ),
     Check("clamp, force along Y", lambda r: r.at("reactionforcey", ROOT),
           ref=-F, tol=1e-6, unit="N", source=EQ)],
    general=TG))

ALPHA96, DT96 = 1.2e-5, 100.0
STEEL_T = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
           'poissonratio="0.3" thermalexpansion="%g 1/K" />' % ALPHA96)


def build_ls96f(free=False, analysis="S30", attrs=None):
    m, nids = _beam(analysis=analysis, attrs=attrs)
    m.mat("Mat", BO.IPROF, STEEL_T, DENS)
    m.node_selection("Einden", nids[:1] if free else [nids[0], nids[-1]])
    m.add('<fixed selection="Einden" />')
    m.node_selection("AlleKnopen", nids)
    m.add('<thermalstress><referencetemperature>293 K</referencetemperature>'
          '</thermalstress>')
    m.add('<temperature2 selection="AlleKnopen"><value>%g K</value>'
          '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
          % (293.0 + DT96))
    return m


N96F = E * I_A * ALPHA96 * DT96
TESTS.append(Case(
    "LS-96f", "Lineair statisch", "Reactions of POU_D_TG: restrained thermal "
    "expansion", "lin_static_3d", build_ls96f,
    [Check("support force along X", lambda r: r.at("reactionforcex", TIP),
           ref=-N96F, tol=1e-3, unit="N", source="N = E A alpha dT")],
    general=TG))


def build_ls96g():
    m = build_ls96f(free=True)
    return m


TESTS.append(Case(
    "LS-96g", "Lineair statisch", "Reactions of POU_D_TG: free thermal "
    "expansion", "lin_static_3d", build_ls96g,
    [Check("clamp, force along X", lambda r: r.at("reactionforcex", ROOT),
           ref=0.0, tol_abs=1e-3, unit="N", source="free end: no reaction"),
     Check("expansion of the free end", lambda r: r.at("displx", TIP),
           ref=ALPHA96 * DT96 * L, tol=1e-6, unit="m",
           source="alpha dT L")],
    general=TG, note="REAC_NODA of MECA_STATIQUE gives E A alpha dT here "
                     "(te0342 has no thermal strain)."))

# Weak axis of the I, clamped at both ends: P_e = 4 pi^2 E I/L^2 with the
# shear correction P_cr = P_e/(1 + P_e AZ/(G A))
I_IY, I_AZ = 2.1174666666666665e-07, 1.9679999999999995
PE46 = 4 * math.pi ** 2 * E * I_IY / L ** 2
PCR46 = PE46 / (1 + PE46 * I_AZ / (G * I_A))
def build_bu46():
    """LS-96f as buckling, with the small load that the bridge requires
    (at midspan, 1 N: 2e-4 % of the thermal force)."""
    m = build_ls96f(analysis="B30", attrs={"maxmode": 2, "shift": 1})
    m.node_selection("Midden", [11])
    m.add('<force selection="Midden"><x>1 N</x><y>0 N</y><z>0 N</z></force>')
    return m


TESTS.append(Case(
    "BU-46", "Knik", "Buckling of a POU_D_TG beam under restrained thermal "
    "expansion", "buckling_3d",
    build_bu46,
    [Check("factor 1", lambda r: r.mode(1), ref=PCR46 / N96F, tol=0.02,
           unit="-", source="P_cr/(E A alpha dT), clamped-clamped weak axis")],
    general=TG, note="The stress state is the thermal force alone: "
                     "SIEF_ELGA of MECA_STATIQUE has N = 0 here."))


# ------------------------------------------------------------------
# Transverse load on a C cantilever: buckling and modal with prestress
# ------------------------------------------------------------------
def _c_beam(analysis, attrs, force):
    m = Model(analysis, attrs=attrs)
    m.elset("Balk", "Mat")
    nids = KB._line(m, (0, 0, 0), (0, 0, KB.L), 20)
    m.mat("Mat", KB.CPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>0 N</z></force>'
          % force)
    return m


def _c_hex(analysis, attrs, force):
    """The mesh of KB.build_bu36 with a uniform traction along the web on
    the free end: resultant through the centroid, free warping there."""
    a, b, c, d = 0.050, 0.100, 0.006, 0.006
    m = Model(analysis, attrs=attrs)
    m.elset("Kolom", "Staal")
    blocks = [(0, d, -b / 2, -b / 2 + c, 2, 2),
              (d, a, -b / 2, -b / 2 + c, 8, 2),
              (0, d, b / 2 - c, b / 2, 2, 2),
              (d, a, b / 2 - c, b / 2, 8, 2),
              (0, d, -b / 2 + c, b / 2 - c, 2, 16)]
    bot, top = [], []
    for x0, x1, y0, y1, nx, ny in blocks:
        ms = hexmesh(m, "Kolom", nx, ny, 50, box(x0, x1, y0, y1, 0.0, KB.L),
                     order=2)
        bot += ms["faces"]["w0"]
        top += ms["faces"]["w1"]
    m.mat("Staal", STEEL, DENS)
    m.face_selection("Voet", bot)
    m.face_selection("Kop", top)
    m.add('<fixed selection="Voet" />')
    m.add('<traction selection="Kop"><x>0 Pa</x><y>%r Pa</y><z>0 Pa</z>'
          '</traction>' % (force / KB.C_A))
    m.top_faces = top
    return m


def _smallest(r):
    return min(abs(v) for v in r.modes.values())


BUCKLE = {"maxmode": 4, "shift": 1}
BUCKLE_HEX = {"maxmode": 2, "shift": 1}
# Mecway 34 headless (own solver) on modellen/BU-45b.liml and MP-20b.liml,
# 7 Nov 2026
MW_BU45 = 54.3221362526269
MW_MP20 = (42.3545471741512, 67.0429777332579, 143.659201183615)
SRC45 = "hex20, Mecway 34 headless = Code-Aster"
TESTS += [
    Case("BU-45", "Knik", "Lateral-torsional buckling of a C cantilever "
         "under a transverse load (POU_D_TG)", "buckling_3d",
         lambda: _c_beam("B30", BUCKLE, F),
         [Check("smallest |factor|", _smallest, ref=MW_BU45, tol=0.02,
                unit="-", in_series=False, source=SRC45)], general=TG,
         note="MECA_STATIQUE as the stress state gives 1.60."),
    Case("BU-45b", "Knik", "The same cantilever as hex20", "buckling_3d",
         lambda: _c_hex("B30", BUCKLE_HEX, F),
         [Check("smallest |factor|", _smallest, ref=MW_BU45, tol=1e-5,
                unit="-", in_series=False,
                source="Mecway 34 headless, own solver")],
         note="Uniform traction on the free end: resultant through the "
              "centroid. maxmode 2: the +/- pairs stop CALC_MODES with more "
              "modes (ALGELINE5_75)."),
]
# Dead axial load plus the live transverse load (#ASTER-CONSTANT)
P_DEAD = 5000.0


def _dead_beam():
    m = _c_beam("B30", BUCKLE, F)
    m.node_selection("KopD", m.nodesel["Tip"])
    m.add('<force selection="KopD"><x>0 N</x><y>0 N</y><z>-%g N</z></force>'
          % P_DEAD)
    m.add("<ccxmodeldefinition>** ASTER-CONSTANT KopD</ccxmodeldefinition>")
    return m


def _dead_hex():
    m = _c_hex("B30", BUCKLE_HEX, F)
    m.face_selection("KopD", m.top_faces)
    m.add('<traction selection="KopD"><x>0 Pa</x><y>0 Pa</y><z>-%r Pa</z>'
          '</traction>' % (P_DEAD / KB.C_A))
    m.add("<ccxmodeldefinition>** ASTER-CONSTANT KopD</ccxmodeldefinition>")
    return m


HEX_BU45D = 53.4737979337767     # BU-45d, Code-Aster 17.4, 7 Nov 2026
TESTS += [
    Case("BU-45c", "Knik", "BU-45 with a dead axial load (#ASTER-CONSTANT)",
         "buckling_3d", _dead_beam,
         [Check("smallest |factor|", _smallest, ref=HEX_BU45D, tol=0.02,
                unit="-", in_series=False, source="BU-45d (hex20)")],
         general=TG),
    Case("BU-45d", "Knik", "BU-45b with a dead axial load", "buckling_3d",
         _dead_hex,
         [Check("smallest |factor|", _smallest, ref=HEX_BU45D, tol=1e-4,
                unit="-", in_series=False,
                source="own value (Mecway has no #ASTER-CONSTANT)")]),
]
PRE = {"maxmode": 3}
F_MP = 20000.0
TESTS += [
    Case("MP-20", "Modaal (voorspanning)", "Modal with prestress, C "
         "cantilever under a transverse load (POU_D_TG)", "modal_3d",
         lambda: _c_beam("V30", PRE, F_MP),
         [Check("mode %d" % (k + 1), lambda r, k=k: r.mode(k + 1),
                ref=MW_MP20[k], tol=0.02, unit="Hz", in_series=False,
                source=SRC45) for k in range(3)], general=TG,
         note="MECA_STATIQUE as the stress state gives -21.4, 109.6 and "
              "232.4 Hz."),
    Case("MP-20b", "Modaal (voorspanning)", "The same cantilever as hex20",
         "modal_3d", lambda: _c_hex("V30", PRE, F_MP),
         [Check("mode %d" % (k + 1), lambda r, k=k: r.mode(k + 1),
                ref=MW_MP20[k], tol=1e-5, unit="Hz", in_series=False,
                source="Mecway 34 headless, own solver") for k in range(3)]),
]
