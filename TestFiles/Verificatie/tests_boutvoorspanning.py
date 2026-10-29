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
from verif_lib import Case, Check, Model, hexmesh, box, static_check

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
              source="Mecway 34 headless (CCX)", in_series=False),
        # self-equilibrated: the reference node (its DX "reaction" is the
        # pretension force) must not count (GUI finding 28 Oct 2026: the
        # status box showed FX -10000 N)
        Check("som reacties X (BRIDGE_STATREAC)",
              lambda r: static_check(r, "FX"), ref=0.0, tol_abs=1e-3 * n,
              unit="N", source="voorspanning is inwendig: som 0",
              in_series=False),
        Check("som reacties Y (BRIDGE_STATREAC)",
              lambda r: static_check(r, "FY"), ref=0.0, tol_abs=1e-3 * n,
              unit="N", source="idem", in_series=False),
        Check("som reactionforcex Mecway-knopen",
              lambda r: sum(r.step()["reactionforcex"].values()), ref=0.0,
              tol_abs=1e-3 * n, unit="N",
              source="idem (geen reactie van het referentieknooppunt op "
                     "een Mecway-knoop)", in_series=False)]


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


# ------------------------------------------------------------------
# Irregular mesh: the bar of PT-01 (10 x 100 x 10 mm along Y, frictionless
# at both ends and on x = 0 and z = 0) as a 3 x 12 x 3 hex grid whose nodes
# are moved randomly (fixed seed): interior nodes in x, y and z, nodes on a
# side face only within that face, nodes on an edge only along the edge;
# every distorted cell is split into 6 tetrahedra (Kuhn), tet10 with
# straight mid-side nodes or tet4. The node layers are wavy, so the middle
# of the selected faces (layers 3 .. 9 on the faces x = 10 and z = 10 mm)
# cuts through tetrahedra of different sizes and orientations at random
# heights: the section zig-zags over faces, edges and corner nodes (PT-05
# has a zig-zag too, but in a regular grid at one height).
# A uniaxial stress is exact in tet4 and tet10 on any straight-sided mesh,
# so a missing or stray node pair shows up as a stress error.
# ------------------------------------------------------------------
import glob
import io
import os
import random
import re

NUJ, NVJ, NWJ = 3, 12, 3
JIT_XZ, JIT_Y = 0.3, 0.35            # fraction of the cell size
J_SEL = range(3, 10)                 # cell layers of the selected faces
_TET10_MID = [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]


def _jitter_grid(seed=1511):
    """{(i, j, k): (x, y, z)} of the distorted grid (deterministic)."""
    rnd = random.Random(seed)
    h = (0.01 / NUJ, L / NVJ, 0.01 / NWJ)
    n = (NUJ, NVJ, NWJ)
    jit = (JIT_XZ, JIT_Y, JIT_XZ)
    grid = {}
    for i in range(NUJ + 1):
        for j in range(NVJ + 1):
            for k in range(NWJ + 1):
                idx = (i, j, k)
                p = []
                for ax in range(3):
                    d = rnd.uniform(-1.0, 1.0)      # always drawn: same stream
                    inner = 0 < idx[ax] < n[ax]
                    p.append((idx[ax] + (jit[ax] * d if inner else 0.0)) *
                             h[ax])
                grid[idx] = tuple(p)
    return grid


def _det(a, b, c, d):
    v = [[q[r] - a[r] for r in range(3)] for q in (b, c, d)]
    return (v[0][0] * (v[1][1] * v[2][2] - v[1][2] * v[2][1]) -
            v[0][1] * (v[1][0] * v[2][2] - v[1][2] * v[2][0]) +
            v[0][2] * (v[1][0] * v[2][1] - v[1][1] * v[2][0]))


def _jitter_bar(load, shape="tet10"):
    m = Model("S30", solver="ccx")
    m.elset("Staaf", "Staal")
    m.mat("Staal", STEEL)
    grid = _jitter_grid()
    faces = {"x0": [], "y0": [], "y1": [], "z0": []}
    bolt = []
    for i in range(NUJ):
        for j in range(NVJ):
            for k in range(NWJ):
                for perm in _KUHN:
                    c = [0, 0, 0]
                    idx = [(i, j, k)]
                    for ax in perm:
                        c[ax] += 1
                        idx.append((i + c[0], j + c[1], k + c[2]))
                    # orientation from the undistorted cell; the distorted
                    # tetrahedron must still be positive
                    if _det(*idx) < 0:
                        idx[1], idx[2] = idx[2], idx[1]
                    xyz = [grid[q] for q in idx]
                    assert _det(*xyz) > 0, "inverted tetrahedron"
                    if shape == "tet10":
                        xyz += [tuple(0.5 * (xyz[a][r] + xyz[b][r])
                                      for r in range(3))
                                for a, b in _TET10_MID]
                    eid = m.elem("Staaf", shape, [m.node(*p) for p in xyz])
                    for fid, cs in _TET_FACES.items():
                        fi = [idx[q] for q in cs]
                        for name, ax, val in (("x0", 0, 0), ("y0", 1, 0),
                                              ("y1", 1, NVJ), ("z0", 2, 0),
                                              ("x1", 0, NUJ), ("z1", 2, NWJ)):
                            if all(q[ax] == val for q in fi):
                                if name in faces:
                                    faces[name].append((eid, fid))
                                elif j in J_SEL:
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


def build_pt11():
    return _jitter_bar(_pret("Bout", force="10 kN"))


def build_pt12():
    return _jitter_bar(_pret("Bout", adjustment="0.01 mm"))


def build_pt13():
    return _jitter_bar(_pret("Bout", force="10 kN"), shape="tet4")


def _expected_cut(m):
    """
    Own recount of the section the bridge must find on model m (Mecway's
    rule, manual par. 9.11, as bridge_pretension applies it: axis +Y here,
    section in the middle of the axial extent of the nodes of the selected
    faces, side of a tetrahedron by the centroid of its corners; the prism
    is every tetrahedron within the extent, one connected bar here).
    Returns (below, above, node pairs).
    """
    y = dict((i + 1, p[1]) for i, p in enumerate(m.nodes))
    elems = dict((e[0], e[2]) for es in m.elsets for e in es[2])
    sel_nodes = set()
    for txt in m.selections:
        if 'faceselection name="Bout"' not in txt:
            continue
        for eid, fid in re.findall(r'eid="(\d+)" faceid="(\d+)"', txt):
            nids = elems[int(eid)]
            fc = set(nids[q] for q in _TET_FACES[int(fid)])
            sel_nodes |= fc
            # the mid-side nodes of the face count for the extent too
            for (a, b), mid in zip(_TET10_MID, nids[4:]):
                if nids[a] in fc and nids[b] in fc:
                    sel_nodes.add(mid)
    s_min = min(y[n] for n in sel_nodes)
    s_max = max(y[n] for n in sel_nodes)
    s_cut, tol = 0.5 * (s_min + s_max), 1e-6 * (s_max - s_min)
    below, above = set(), set()
    for eid, nids in elems.items():
        if not all(s_min - tol <= y[n] <= s_max + tol for n in nids):
            continue
        yc = sum(y[n] for n in nids[:4]) / 4.0
        (below if yc < s_cut - tol else above).add(eid)
    nb = set(n for e in below for n in elems[e])
    na = set(n for e in above for n in elems[e])
    return len(below), len(above), len(nb & na)


def _log_section(r):
    """(area, below, above, pairs) from the INFO line of the bridge log."""
    logs = glob.glob(os.path.join(os.path.dirname(r.mess),
                                  "*bridge_log.txt"))
    txt = io.open(logs[0], encoding="utf-8", errors="replace").read()
    mt = re.search(r"Pre-tension section 'Bout':.*? area (\S+) m2.*?\((\d+) "
                   r"below, (\d+) above\), (\d+) node pair", txt)
    return (float(mt.group(1)), int(mt.group(2)), int(mt.group(3)),
            int(mt.group(4)))


def _ynode(r, p):
    return r.model.nodes[r.nearest(p) - 1][1]


def _eps_below(r):
    """u_y / y of the node nearest (0, 20 mm, 0): the strain of the lower
    part (the node sits at a random height, so the strain is checked)."""
    return r.at("disply", P25) / _ynode(r, P25)


def _eps_above(r):
    return -r.at("disply", P75) / (L - _ynode(r, P75))


PMID = (0.005, 0.03, 0.005)          # interior node of the lower half
# Mecway 34 headless (mw_solve.py, CCX, 29 Oct 2026) on modellen/PT-11..13:
# stressyy uniform in all nodes (min = max): 99.999 MPa, 19.9998 MPa and
# 100.000 MPa; strain u_y / y below and above the section 5e-4 / 1e-4
# within 3e-7 relative (Mecway's own section, with its thin layer)
MWJ = {"PT-11": 9.9999e7, "PT-12": 1.99998e7, "PT-13": 1.0e8}


def _jitter_checks(n, build, mw=None):
    """n = axial force [N]; ends held, so the strain is n / (E A) on both
    sides and the bar material elongates by n L / (E A) = the shortening."""
    exp = _expected_cut(build())
    out = [
        Check("stressyy binnenknoop", lambda r: r.at("stressyy", PMID),
              ref=n / A, tol=1e-4, unit="Pa",
              source="N / A (uniaxiaal, exact in tet4/tet10)"),
        Check("stressyy max", lambda r: r.extreme("stressyy"), ref=n / A,
              tol=1e-4, unit="Pa",
              source="N / A in alle knopen: geen piek bij de doorsnede"),
        Check("stressyy min", lambda r: r.extreme("stressyy", fn=min),
              ref=n / A, tol=1e-4, unit="Pa", source="idem"),
        Check("reactie onder", lambda r: -r.total("reactionforcey", "OnderN"),
              ref=n, tol=1e-4, unit="N",
              source="N (de onderkant houdt de staaf omlaag)"),
        Check("rek onderste deel u_y / y", _eps_below, ref=n / (E * A),
              tol=1e-4, unit="-", source="N / (E A)"),
        Check("rek bovenste deel -u_y / (L - y)", _eps_above,
              ref=n / (E * A), tol=1e-4, unit="-", source="N / (E A)"),
        Check("verlenging staafmateriaal = verkorting",
              lambda r: 0.5 * (_eps_below(r) + _eps_above(r)) * L,
              ref=n * L / (E * A), tol=1e-4, unit="m",
              source="N L / (E A)"),
        Check("oppervlak doorsnede (bridge-log)",
              lambda r: _log_section(r)[0], ref=A, tol=1e-5, unit="m2",
              source="10 x 10 mm (zigzagvlak geprojecteerd)",
              in_series=False),
        Check("elementen onder (bridge-log)", lambda r: _log_section(r)[1],
              ref=exp[0], tol_abs=0, unit="",
              source="eigen telling (zwaartepunt onder het midden)",
              in_series=False),
        Check("elementen boven (bridge-log)", lambda r: _log_section(r)[2],
              ref=exp[1], tol_abs=0, unit="", source="eigen telling",
              in_series=False),
        Check("knoopparen (bridge-log)", lambda r: _log_section(r)[3],
              ref=exp[2], tol_abs=0, unit="",
              source="eigen telling (knopen van onder en boven)",
              in_series=False),
        Check("som reacties Y (BRIDGE_STATREAC)",
              lambda r: static_check(r, "FY"), ref=0.0, tol_abs=1e-3 * n,
              unit="N", source="voorspanning is inwendig: som 0",
              in_series=False)]
    if mw is not None:
        out.append(Check("stressyy = Mecway", lambda r: r.at("stressyy", PMID),
                         ref=mw, tol=1e-3, unit="Pa",
                         source="Mecway 34 headless (CCX)", in_series=False))
    return out


TESTS += [
    Case("PT-11", GROUP, "Staaf in een onregelmatig tet10-mesh (verschoven "
         "knopen), kracht 10 kN", "lin_static_3d", build_pt11,
         _jitter_checks(10e3, build_pt11, MWJ["PT-11"]),
         note="Doorsnede in het midden van de geselecteerde vlakken door "
              "tetraeders van wisselende grootte en stand; zijde per "
              "zwaartepunt."),
    Case("PT-12", GROUP, "Idem, length adjustment 0,01 mm", "lin_static_3d",
         build_pt12, _jitter_checks(E * A * 1e-5 / L, build_pt12,
                                     MWJ["PT-12"]),
         note="DDL_IMPO DX = 1e-5 m: N = E A delta / L = 2000 N; de "
              "verlenging van het staafmateriaal is de verkorting."),
    Case("PT-13", GROUP, "Idem in tet4, kracht 10 kN", "lin_static_3d",
         build_pt13, _jitter_checks(10e3, build_pt13, MWJ["PT-13"]),
         note="Zelfde verschoven knopen, lineaire tetraeders."),
]
