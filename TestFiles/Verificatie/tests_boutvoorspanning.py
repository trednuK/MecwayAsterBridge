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
