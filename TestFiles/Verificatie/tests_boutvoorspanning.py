# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Pre-tension section (bolt pretension, Mecway manual v34 par. 9.11; step
S15): bridge_pretension cuts the prism and couples the two sides with
LIAISON_DDL to a reference node (DX = shortening); force -> FORCE_NODALE FX,
length adjustment -> DDL_IMPO DX on that node.

References: hand calculation (bar in tension, bolt/clamped-member joint
diagram) and Mecway 34 headless with CCX (TestFiles/Tools/mw_solve.py, the
same .liml with solver="ccx" and the stress field; numbers below).
Explanation: docs/Verificatie.md (PT-01 .. PT-05).
"""
from verif_lib import Case, Check, Model, hexmesh, box

GROUP = "Boutvoorspanning"
E = 200e9
STEEL = ('<mechanical type="Isotropic" youngsmodulus="200 GPa" '
         'poissonratio="0.3" />')
# nu = 0 for the columns of the joint (exactly uniaxial) and plates 1000x
# stiffer (rigid compared with the columns)
COLUMN = ('<mechanical type="Isotropic" youngsmodulus="200 GPa" '
          'poissonratio="0" />')
PLATE = ('<mechanical type="Isotropic" youngsmodulus="200000 GPa" '
         'poissonratio="0" />')


def _pret(sel, force=None, adjustment=None, time=False):
    """<pretensionsection> as Mecway 34 writes it: adjustment="true" for the
    length adjustment (found with headless solves), else the force."""
    if adjustment is not None:
        return ('<pretensionsection selection="%s" adjustment="true">'
                '<force>0 N</force><adjustment>%s</adjustment>'
                '</pretensionsection>' % (sel, adjustment))
    return ('<pretensionsection selection="%s" force="true"><force>%s</force>'
            '<adjustment>0 m</adjustment></pretensionsection>' % (sel, force))


# ------------------------------------------------------------------
# Bar 10 x 100 x 10 mm along Y (hex20 2 x 10 x 2), frictionless at both
# ends and on the planes x = 0 and z = 0: uniaxial. Section in the middle
# (faces of layers 4 and 5: y = 40 .. 60 mm, section at 50 mm).
# ------------------------------------------------------------------
L, A = 0.1, 1e-4


def _bar(load):
    m = Model("S30", solver="ccx")
    m.elset("Staaf", "Staal")
    h = hexmesh(m, "Staaf", 2, 10, 2, box(0, 0.01, 0, L, 0, 0.01), order=2)
    m.mat("Staal", STEEL)
    m.face_selection("Onder", h["faces"]["v0"])
    m.face_selection("Boven", h["faces"]["v1"])
    m.face_selection("X0", h["faces"]["u0"])
    m.face_selection("Z0", h["faces"]["w0"])
    m.node_selection("OnderN", sorted(h["nodes"]["v0"]))
    els = h["elems"]
    m.face_selection("Bout", [(els[(1, j, k)], 4) for j in (4, 5)
                              for k in range(2)] +
                     [(els[(i, j, 1)], 2) for j in (4, 5) for i in range(2)])
    for sel in ("Onder", "Boven", "X0", "Z0"):
        m.add('<frictionless selection="%s" />' % sel)
    m.add(load)
    return m


def build_pt01():
    return _bar(_pret("Bout", force="10 kN"))


def build_pt02():
    return _bar(_pret("Bout", adjustment="0.01 mm"))


# Mecway 34 headless (mw_solve.py, CCX, 28 Oct 2026) on modellen/PT-*.liml
# with the stress field: stressyy in (5, 20, 5) mm; disply in (0, 20, 0) and
# (0, 80, 0) mm equal to the hand calculation (1e-5 / -1e-5 m for PT-01,
# 2e-6 / -2e-6 m for PT-02). The small difference in stress is Mecway's
# thin element layer at the section (manual par. 9.11). PT-03: bolt force
# 1531.71 N, sleeve 933.088 N; PT-04: bolt force 999.928 N (t = 0.5) and
# 999.929 N (t = 1), sleeve -199.524 N (t = 1).
MW = {
    "PT-01": {"syy": 9.9996e7},
    "PT-02": {"syy": 1.99992e7},
    "PT-05": {"syy": 1.0e8},
}
P25 = (0.0, 0.02, 0.0)      # nodes in each half, away from the section
P75 = (0.0, 0.08, 0.0)


def _bar_checks(n, mw):
    """n = axial force [N] (tension); ends held, so delta = n L / (E A)."""
    return [
        Check("stressyy", lambda r: r.at("stressyy", (0.005, 0.02, 0.005)),
              ref=n / A, tol=1e-4, unit="Pa", source="N / A"),
        Check("reactie onder", lambda r: -r.total("reactionforcey", "OnderN"),
              ref=n, tol=1e-4, unit="N",
              source="N (de onderkant houdt de staaf omlaag)"),
        Check("disply y = 20 mm", lambda r: r.at("disply", P25),
              ref=n * 0.02 / (E * A), tol=1e-4, unit="m",
              source="N y / (E A), onderste helft rekt omhoog"),
        Check("disply y = 80 mm", lambda r: r.at("disply", P75),
              ref=-n * 0.02 / (E * A), tol=1e-4, unit="m",
              source="-N (L - y) / (E A)"),
        Check("stressyy = Mecway", lambda r: r.at("stressyy",
                                                  (0.005, 0.02, 0.005)),
              ref=mw["syy"], tol=1e-3, unit="Pa",
              source="Mecway 34 headless (CCX)", in_series=False)]


# ------------------------------------------------------------------
# The same bar in tet4 (every hex cell split into 6 tetrahedra along its
# main diagonal, conforming): the faces of layers 4 .. 6 put the section
# at y = 55 mm, inside layer 5, so the cut zig-zags over tetrahedron faces
# and edges. A uniform stress is exact in tet4.
# ------------------------------------------------------------------
_KUHN = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
_TET_FACES = {1: (0, 2, 1), 2: (0, 1, 3), 3: (2, 3, 1), 4: (0, 3, 2)}


def _tet_bar(load):
    m = Model("S30", solver="ccx")
    m.elset("Staaf", "Staal")
    m.mat("Staal", STEEL)
    nu, nv, nw = 2, 10, 2
    size = (0.01, L, 0.01)
    faces = {"x0": [], "x1": [], "y0": [], "y1": [], "z0": [], "z1": []}
    bolt = []
    for i in range(nu):
        for j in range(nv):
            for k in range(nw):
                for perm in _KUHN:
                    c = [0, 0, 0]
                    pts = [tuple(c)]
                    for ax in perm:
                        c[ax] += 1
                        pts.append(tuple(c))
                    xyz = [((i + p[0]) * size[0] / nu, (j + p[1]) * size[1] / nv,
                            (k + p[2]) * size[2] / nw) for p in pts]
                    a, b, cc, d = xyz
                    v = [[b[q] - a[q] for q in range(3)],
                         [cc[q] - a[q] for q in range(3)],
                         [d[q] - a[q] for q in range(3)]]
                    det = (v[0][0] * (v[1][1] * v[2][2] - v[1][2] * v[2][1]) -
                           v[0][1] * (v[1][0] * v[2][2] - v[1][2] * v[2][0]) +
                           v[0][2] * (v[1][0] * v[2][1] - v[1][1] * v[2][0]))
                    if det < 0:
                        xyz = [xyz[0], xyz[2], xyz[1], xyz[3]]
                    nids = [m.node(*p) for p in xyz]
                    eid = m.elem("Staaf", "tet4", nids)
                    for fid, idx in _TET_FACES.items():
                        fp = [xyz[q] for q in idx]
                        for name, ax, val in (("x0", 0, 0.0), ("x1", 0, 0.01),
                                              ("y0", 1, 0.0), ("y1", 1, L),
                                              ("z0", 2, 0.0), ("z1", 2, 0.01)):
                            if all(abs(p[ax] - val) < 1e-12 for p in fp):
                                faces[name].append((eid, fid))
                                if name in ("x1", "z1") and j in (4, 5, 6):
                                    bolt.append((eid, fid))
    m.face_selection("Onder", faces["y0"])
    m.face_selection("Boven", faces["y1"])
    m.face_selection("X0", faces["x0"])
    m.face_selection("Z0", faces["z0"])
    m.face_selection("Bout", bolt)
    m.node_selection("OnderN", sorted(set(
        n for es in m.elsets for e in es[2] for n in e[2]
        if abs(m.nodes[n - 1][1]) < 1e-12)))
    for sel in ("Onder", "Boven", "X0", "Z0"):
        m.add('<frictionless selection="%s" />' % sel)
    m.add(load)
    return m


def build_pt05():
    return _tet_bar(_pret("Bout", force="10 kN"))


TESTS = [
    Case("PT-01", GROUP, "Staaf met pre-tension section, kracht 10 kN "
         "(lineair statisch)", "lin_static_3d", build_pt01,
         _bar_checks(10e3, MW["PT-01"]),
         note="FORCE_NODALE FX op het referentieknooppunt; de doorsnede op "
              "y = 50 mm (midden van de geselecteerde vlakken)."),
    Case("PT-02", GROUP, "Idem, length adjustment 0,01 mm",
         "lin_static_3d", build_pt02,
         _bar_checks(E * A * 1e-5 / L, MW["PT-02"]),
         note="DDL_IMPO DX = 1e-5 m op het referentieknooppunt: N = E A "
              "delta / L = 2000 N."),
    Case("PT-05", GROUP, "Staaf in tet4, kracht 10 kN, doorsnede zigzag "
         "door laag 5", "lin_static_3d", build_pt05,
         _bar_checks(10e3, MW["PT-05"]),
         note="Doorsnede op y = 55 mm binnen een elementlaag: zijden per "
              "zwaartepunt van de tetraeder, knopen die alleen via een ribbe "
              "of hoekpunt aan beide zijden liggen worden ook gesplitst."),
]


# ------------------------------------------------------------------
# Joint: rigid plates (y = 0 .. 10 and 110 .. 120 mm, x = 0 .. 50 mm, E x
# 1000) joined by a bolt column (x = 20 .. 30 mm) and two sleeve columns
# (x = 0 .. 10 and 40 .. 50 mm), columns 10 x 10 mm, length 100 mm, nu = 0.
# Bottom fixed, external force P upward on the top. Bolt stiffness kb = E
# Ab / L, clamped member kc = E Ac / L (Ac = 2 Ab).
# ------------------------------------------------------------------
LC = 0.1
AB, AC = 1e-4, 2e-4
KB, KC = E * AB / LC, E * AC / LC


def _joint(loads, analysis="S30", timesteps=None):
    m = Model(analysis, timesteps=timesteps, solver="ccx")
    m.elset("Platen", "Plaat")
    m.elset("Bout", "Kolom")
    m.elset("Huls", "Kolom")
    m.mat("Plaat", PLATE)
    m.mat("Kolom", COLUMN)
    bot = hexmesh(m, "Platen", 5, 1, 1, box(0, 0.05, 0, 0.01, 0, 0.01),
                  order=2)
    top = hexmesh(m, "Platen", 5, 1, 1, box(0, 0.05, 0.11, 0.12, 0, 0.01),
                  order=2)
    bolt = hexmesh(m, "Bout", 1, 10, 1, box(0.02, 0.03, 0.01, 0.11, 0,
                                            0.01), order=2)
    hexmesh(m, "Huls", 1, 10, 1, box(0, 0.01, 0.01, 0.11, 0, 0.01), order=2)
    hexmesh(m, "Huls", 1, 10, 1, box(0.04, 0.05, 0.01, 0.11, 0, 0.01),
            order=2)
    m.face_selection("Onder", bot["faces"]["v0"])
    m.face_selection("Boven", top["faces"]["v1"])
    els = bolt["elems"]
    m.face_selection("BoutVlakken", [(els[(0, j, 0)], 6) for j in (4, 5)] +
                     [(els[(0, j, 0)], 1) for j in (4, 5)])
    m.add('<fixed selection="Onder" />')
    for load in loads:
        m.add(load)
    return m


def build_pt03():
    return _joint([_pret("BoutVlakken", adjustment="0.01 mm"),
                   '<force selection="Boven"><x>0 N</x><y>600 N</y>'
                   '<z>0 N</z></force>'])


def build_pt04():
    return _joint([_pret("BoutVlakken", force="1000 N"),
                   '<force selection="Boven"><x>0 N</x>'
                   '<y unit="N" timeunit="s" positionunit="m">1200*t</y>'
                   '<z>0 N</z></force>'],
                  analysis="L30",
                  timesteps={"timeperiod": "1 s", "stepsize": "0.25 s"})


PB = (0.02, 0.03, 0.0)      # bolt column, lower half
PC = (0.0, 0.03, 0.0)       # sleeve column
FP3 = KB * KC / (KB + KC) * 1e-5          # preload by the adjustment
NB3 = FP3 + 600.0 * KB / (KB + KC)        # bolt force with P = 600 N
NC3 = NB3 - 600.0                         # clamped member (compression)

TESTS += [
    Case("PT-03", GROUP, "Boutverbinding (stijve platen): length adjustment "
         "0,01 mm plus externe kracht 600 N", "lin_static_3d", build_pt03, [
             Check("boutkracht", lambda r: r.at("stressyy", PB) * AB,
                   ref=NB3, tol=2e-3, unit="N",
                   source="Fp + P kb/(kb+kc), Fp = kb kc/(kb+kc) delta "
                          "(VDI 2230-verbindingsdiagram)"),
             Check("klemkracht huls", lambda r: -r.at("stressyy", PC) * AC,
                   ref=NC3, tol=2e-3, unit="N", source="Fb - P"),
             Check("boutkracht = Mecway", lambda r: r.at("stressyy", PB) * AB,
                   ref=1531.71, tol=1e-3, unit="N",
                   source="Mecway 34 headless (CCX)", in_series=False)],
         note="Lengteverandering: de bout is 'vergrendeld', de externe last "
              "verhoogt de boutkracht met P kb / (kb + kc)."),
    Case("PT-04", GROUP, "Idem met kracht 1000 N en externe kracht 1200 t N "
         "(niet-lineair statisch)", "nonlin_static_3d", build_pt04, [
             Check("boutkracht t = 0,5", lambda r: r.at(
                 "stressyy", PB, 0.5) * AB, ref=1000.0, tol=2e-3, unit="N",
                 source="Mecway: de kracht blijft opgelegd (CCX *CLOAD)"),
             Check("boutkracht t = 1", lambda r: r.at(
                 "stressyy", PB, 1.0) * AB, ref=1000.0, tol=2e-3, unit="N",
                 source="idem"),
             Check("klemkracht huls t = 1", lambda r: -r.at(
                 "stressyy", PC, 1.0) * AC, ref=-200.0, tol_abs=2.0,
                 unit="N", source="F - P = 1000 - 1200 N (huls op trek)"),
             Check("boutkracht t = 1 = Mecway", lambda r: r.at(
                 "stressyy", PB, 1.0) * AB, ref=999.929, tol=1e-3, unit="N",
                 source="Mecway 34 headless (CCX)", in_series=False)],
         note="Krachtgestuurd: de boutkracht blijft F, ook onder de "
              "externe last (geen vergrendeling, zoals Mecway/CCX)."),
]


# ------------------------------------------------------------------
# S15b: the same joint in Dynamic Response (dyna_impl_3d). The top plate is
# a heavy rigid mass (density 2e6 kg/m3: m = 10 kg), the columns nearly
# massless (7.85 kg/m3), so the top plate is a single degree of freedom:
#   force F (step):        m u'' + kc u = -F          -> T = 2 pi sqrt(m/kc),
#                          u from 0 to -2 F/kc (the bolt force stays F)
#   adjustment d (step):   m u'' + (kb + kc) u = -kb d -> T = 2 pi
#                          sqrt(m/(kb+kc)), u from 0 to -2 kb d/(kb+kc)
#   force F t/tr (ramp):   u = -F/kc (t/tr - sin(w t)/(w tr))
# Mecway 34 (CCX deck of a headless D30/D31 solve, 28 Oct 2026): one
# *DYNAMIC step with AMPLITUDE=STEP, *CLOAD / *BOUNDARY on the pre-tension
# node; no static preload step.
# ------------------------------------------------------------------
from tests_dynamisch import period, peak
import math

MDYN = 0.05 * 0.01 * 0.01 * 2.0e6          # top plate [kg]
TDF = 2.0 * math.pi * math.sqrt(MDYN / KC)
TDA = 2.0 * math.pi * math.sqrt(MDYN / (KB + KC))
TEND, DTD = 3.0e-3, 2.0e-5
PTOP = (0.025, 0.12, 0.0)
COLUMN_D = (COLUMN, u'<density type="Simple" density="7.85 kg/m³" />')
PLATE_D = (PLATE, u'<density type="Simple" density="2000000 kg/m³" />')


def _dyn_joint(load, analysis="D31"):
    m = Model(analysis, solver="ccx", timesteps={
        "timeperiod": "%r s" % TEND, "automatictimestepping": "false",
        "outputtimes": "regular", "timepointsstart": "0 s",
        "timepointsincrement": "%r s" % DTD, "stepsize": "%r s" % DTD})
    m.elset("Platen", "Plaat")
    m.elset("Bout", "Kolom")
    m.elset("Huls", "Kolom")
    m.mat("Plaat", *PLATE_D)
    m.mat("Kolom", *COLUMN_D)
    bot = hexmesh(m, "Platen", 5, 1, 1, box(0, 0.05, 0, 0.01, 0, 0.01),
                  order=2)
    hexmesh(m, "Platen", 5, 1, 1, box(0, 0.05, 0.11, 0.12, 0, 0.01), order=2)
    bolt = hexmesh(m, "Bout", 1, 10, 1, box(0.02, 0.03, 0.01, 0.11, 0,
                                            0.01), order=2)
    hexmesh(m, "Huls", 1, 10, 1, box(0, 0.01, 0.01, 0.11, 0, 0.01), order=2)
    hexmesh(m, "Huls", 1, 10, 1, box(0.04, 0.05, 0.01, 0.11, 0, 0.01),
            order=2)
    m.face_selection("Onder", bot["faces"]["v0"])
    els = bolt["elems"]
    m.face_selection("BoutVlakken", [(els[(0, j, 0)], 6) for j in (4, 5)] +
                     [(els[(0, j, 0)], 1) for j in (4, 5)])
    m.add('<fixed selection="Onder" />')
    m.add(load)
    return m


def build_pt06():
    return _dyn_joint(_pret("BoutVlakken", force="1000 N"))


def build_pt07():
    return _dyn_joint(_pret("BoutVlakken", adjustment="0.01 mm"))


def build_pt08():
    return _dyn_joint('<pretensionsection selection="BoutVlakken" '
                      'force="true"><force unit="N" timeunit="s" '
                      'positionunit="m">1000*t/0.003</force>'
                      '<adjustment>0 m</adjustment></pretensionsection>',
                      analysis="D30")


def _utop(r):
    return [(t, -u) for t, u in r.history("disply", PTOP)]


def _per(r, level):
    return period(_utop(r), level)


# Mecway 34 headless (mw_solve.py, CCX, 28 Oct 2026) on modellen/PT-06..08:
# PT-06 period 0.995693 ms (mean level), peak 5.0147e-6 m, bolt force
# 999.93 N at t = 2.5 ms; PT-07 period 0.813096 ms, peak 6.66678e-6 m;
# PT-08 (D30) u(3 ms) = -2.49738e-6 m.
MWD = {"PT-06": (0.995693e-3, 5.0147e-6), "PT-07": (0.813096e-3, 6.66678e-6),
       "PT-08": -2.49738e-6}
U6 = 1000.0 / KC
U7 = KB * 1e-5 / (KB + KC)
W8 = 2.0 * math.pi / TDF
U8 = -U6 * (1.0 - math.sin(W8 * TEND) / (W8 * TEND))


def _dyn_checks(key, ustat, tper):
    return [
        Check("periode", lambda r: _per(r, ustat), ref=tper, tol=1e-2,
              unit="s", source="2 pi sqrt(m/k), massa-veersysteem "
              "(k = kc bij kracht, kb + kc bij lengteverandering)"),
        Check("max. verplaatsing", lambda r: peak(_utop(r)), ref=2 * ustat,
              tol=1e-2, unit="m", source="2 x statisch (staplast vanaf "
              "t = 0, zoals Mecway: AMPLITUDE=STEP)"),
        Check("periode = Mecway", lambda r: _per(r, ustat),
              ref=MWD[key][0], tol=5e-3, unit="s",
              source="Mecway 34 headless (CCX)", in_series=False),
        Check("max. verplaatsing = Mecway", lambda r: peak(_utop(r)),
              ref=MWD[key][1], tol=5e-3, unit="m",
              source="Mecway 34 headless (CCX)", in_series=False)]


TESTS += [
    Case("PT-06", GROUP, "Boutverbinding dynamisch (D31): kracht 1000 N als "
         "staplast, zware bovenplaat", "dyna_impl_3d", build_pt06,
         _dyn_checks("PT-06", U6, TDF) + [
             Check("boutkracht t = 2,5 ms", lambda r: r.at(
                 "stressyy", PB, 2.5e-3) * AB, ref=1000.0, tol=5e-3,
                 unit="N", source="de kracht blijft opgelegd (CCX *CLOAD)")],
         note="Geen statische voorstap: de voorspanning werkt als staplast "
              "vanaf t = 0 en de bovenplaat trilt om -F/kc."),
    Case("PT-07", GROUP, "Idem, length adjustment 0,01 mm als staplast",
         "dyna_impl_3d", build_pt07, _dyn_checks("PT-07", U7, TDA),
         note="DDL_IMPO DX = 1e-5 m op het referentieknooppunt vanaf "
              "t = 0; stijfheid kb + kc."),
    Case("PT-08", GROUP, "Idem in D30, kracht als formule 1000 t / 0,003 N "
         "(helling)", "dyna_impl_3d", build_pt08, [
             Check("verplaatsing t = 3 ms", lambda r: r.at(
                 "disply", PTOP, TEND), ref=U8, tol=1e-2, unit="m",
                 source="-F/kc (t/tr - sin(w t)/(w tr)), helling op een "
                        "massa-veersysteem"),
             Check("verplaatsing t = 3 ms = Mecway", lambda r: r.at(
                 "disply", PTOP, TEND), ref=MWD["PT-08"], tol=5e-3,
                 unit="m", source="Mecway 34 headless (CCX)",
                 in_series=False)],
         note="De tijdsfunctie van de kracht volgt hetzelfde pad als een "
              "gewone kracht (Mecway: *CLOAD met AMPLITUDE)."),
]


# ------------------------------------------------------------------
# S15b: the spring element variant (internal solver, manual par. 9.11):
# two springs in series between two held nodes, the first one shortened by
# d (pre-tension section on its face). The middle node moves towards the
# first spring by k1 d / (k1 + k2); both springs carry k1 k2 d / (k1 + k2)
# in tension. Mecway's <fixed> on a node selection did not hold these
# spring-only nodes in Mecway 34 (the model was singular), so the ends are
# held with displacement constraints in x, y and z; the middle node is held
# across the springs (oblique displacement constraints for PT-10).
# Mecway 34 headless (internal solver, 28 Oct 2026): faceid 1, 2 and 3 of
# the line element give the same result; force="true" with force 0 N and
# adjustment 1 mm also shortens by 1 mm; force 5 N with adjustment 0 m
# does nothing.
# ------------------------------------------------------------------
def _springs(direction, k1, k2, adjustment, attr='adjustment="true"'):
    m = Model("S30")
    m.elset("Veer1", "V1")
    m.elset("Veer2", "V2")
    n0 = m.node(0, 0, 0)
    n1 = m.node(*direction)
    n2 = m.node(*[2 * c for c in direction])
    e1 = m.elem("Veer1", "line2", [n0, n1])
    m.elem("Veer2", "line2", [n1, n2])
    m.mat("V1", '<mechanical type="Spring" springconstant="%r N/m" />' % k1)
    m.mat("V2", '<mechanical type="Spring" springconstant="%r N/m" />' % k2)
    m.node_selection("Grond", [n0, n2])
    m.node_selection("Eind0", [n0])
    m.node_selection("Midden", [n1])
    m.face_selection("VeerVlak", [(e1, 1)])
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        m.add('<displacement selection="Grond"><value>0 m</value>'
              '<x>%d</x><y>%d</y><z>%d</z></displacement>' % d)
    e = _unitv(direction)
    p1 = _unitv((-e[1], e[0], 0.0) if abs(e[2]) < 0.9 else (1.0, 0.0, 0.0))
    p2 = (e[1] * p1[2] - e[2] * p1[1], e[2] * p1[0] - e[0] * p1[2],
          e[0] * p1[1] - e[1] * p1[0])
    for p in (p1, p2):
        m.add('<displacement selection="Midden"><value>0 m</value>'
              '<x>%r</x><y>%r</y><z>%r</z></displacement>' % tuple(p))
    m.add('<pretensionsection selection="VeerVlak" %s><force>0 N</force>'
          '<adjustment>%s</adjustment></pretensionsection>'
          % (attr, adjustment))
    return m


def _unitv(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def build_pt09():
    return _springs((1.0, 0.0, 0.0), 1000.0, 3000.0, "1 mm",
                    attr='force="true"')


DIR10 = (1.0, 2.0, 2.0)


def build_pt10():
    return _springs(DIR10, 1000.0, 4000.0, "2 mm")


U9 = -1000.0 * 1e-3 / 4000.0             # middle node along the axis
N9 = 1000.0 * 3000.0 * 1e-3 / 4000.0     # spring force (tension)
E10 = _unitv(DIR10)
U10 = -1000.0 * 2e-3 / 5000.0
N10 = 1000.0 * 4000.0 * 2e-3 / 5000.0
P9, P10 = (1.0, 0.0, 0.0), DIR10
# Mecway 34 headless (internal solver) on modellen/PT-09/10: displx of the
# middle node -2.5e-4 m, reactions -0.75 / 0.75 N (PT-09); displacement
# (-1.3333e-4, -2.6667e-4, -2.6667e-4) m = -4e-4 m along the axis,
# reaction x -0.53333 N (PT-10)
MW10 = -0.0004


def _along(r, point, e):
    return sum(r.at(v, point) * c for v, c in
               zip(("displx", "disply", "displz"), e))


TESTS += [
    Case("PT-09", GROUP, "Veervariant: twee veren in serie, length adjustment "
         "1 mm op veer 1 (force=\"true\", zoals Mecway gebruikt)",
         "lin_static_3d", build_pt09, [
             Check("verplaatsing midden", lambda r: r.at("displx", P9),
                   ref=U9, tol=1e-6, unit="m",
                   source="-k1 d / (k1 + k2)"),
             Check("reactie x knoop 0", lambda r: r.total(
                 "reactionforcex", "Eind0"), ref=-N9, tol=1e-6, unit="N",
                 source="-k1 k2 d / (k1 + k2) (veer 1 trekt knoop 0 mee)"),
             Check("verplaatsing midden = Mecway", lambda r: r.at(
                 "displx", P9), ref=-0.00025, tol=1e-6, unit="m",
                 source="Mecway 34 headless (interne solver)",
                 in_series=False)],
         note="Mecway gebruikt bij een veer altijd de length adjustment, "
              "ook met force=\"true\"; de bridge zet die om in twee "
              "knoopkrachten k d naar elkaar toe."),
    Case("PT-10", GROUP, "Idem, veren schuin langs (1, 2, 2), k2 = 4000 N/m, "
         "length adjustment 2 mm", "lin_static_3d", build_pt10, [
             Check("verplaatsing midden langs de as", lambda r: _along(
                 r, P10, E10), ref=U10, tol=1e-6, unit="m",
                 source="-k1 d / (k1 + k2)"),
             Check("reactie x knoop 0", lambda r: r.total(
                 "reactionforcex", "Eind0"), ref=-N10 * E10[0], tol=1e-6,
                 unit="N", source="-k1 k2 d / (k1 + k2) e_x"),
             Check("verplaatsing midden langs de as = Mecway",
                   lambda r: _along(r, P10, E10), ref=MW10, tol=1e-6,
                   unit="m", source="Mecway 34 headless (interne solver)",
                   in_series=False)],
         note="Richting van de knoopkrachten = as van de veer; het "
              "middelste knooppunt is dwars vastgehouden met schuine "
              "verplaatsingsvoorwaarden."),
]
