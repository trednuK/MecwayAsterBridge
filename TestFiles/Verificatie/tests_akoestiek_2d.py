# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Acoustic Resonance 2D (Mecway A20 -> PHENOMENE='ACOUSTIQUE', MODELISATION
'PLAN', CALC_MODES; bridge analysis acoustic_modes_3d, STAPPENPLAN S16d,
Scripts/bridge_plane._apply_acoustic + bridge_acoustic.py). Explanation:
docs/Verificatie.md (AK) and docs/2D_en_axisymmetrisch.md.

AK-10  rectangle a x b = 1.0 x 0.7 m, hard walls, quad8 10 x 7: the 2D
       counterpart of AK-04.
AK-11  the same with p = 0 on the edge x = a (face selection) and a
       Shell/membrane thickness of 10 mm (Mecway ignores it, the bridge too).
AK-12  hard walls, tri6 (every quad of 20 x 14 split in two).
AK-13  quad4 in two elsets (left and right half), p = 0 on the nodes of
       x = a (node selection).
AK-14  impedance Z = 2000 Pa.s/m on the edge x = a: complex modes
       (PLAN_ABSO, aster_acoustic_complex).
AK-15  hard walls, tri3 (20 x 14 split in two).

quad4/quad8 are identical to Mecway (<= 1e-6); triangles are not:
Code-Aster's plane acoustic elements integrate the mass with the RIGI
family (tri3 1 point, tri6 3 points), Mecway exactly (KNOWN_BUGS 128).

References:
  - rectangle with hard walls (separation of variables, cos modes):
        f_mn = c/2 sqrt((m/a)^2 + (n/b)^2);
    with p = 0 on x = a and dp/dx = 0 on x = 0: cos((2m - 1) pi x / (2a)),
        f_mn = c/2 sqrt(((2m - 1)/(2a))^2 + (n/b)^2)
    (the same source as AK-04: Kinsler, Frey, Coppens & Sanders,
    Fundamentals of Acoustics, not consulted locally);
  - normalisation p^T M p = 1 with M = int N N / c^2 dA per unit thickness
    (measured in Mecway 34: the constant mode is c / sqrt(a b), with and
    without a thickness);
  - impedance on x = a, the modes without y variation are those of the tube
    (tests_akoestiek_impedantie, tube_roots): s_n = (c/a)(-artanh(rho c/Z)
    + i pi n), so f_n = n c / (2a) and sigma = (c/a) artanh(rho c / Z);
  - Mecway 34 headless (TestFiles/Tools/mw_solve.py, internal solver) on
    the same .liml (modellen/AK-1*.liml), values in MECWAY below.
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect
from tests_akoestiek_impedantie import (_lam, _f, _decay, RHOC,
                                        tube_roots)

GROUP = "Akoestiek"
C_AIR = 340.0
A, B = 1.0, 0.7
AIR = ['<mechanical type="Isotropic" speedofsound="340 m/s" />',
       u'<density type="Simple" density="1.2 kg/m³" />']
Z_IMP = 2000.0

# Mecway 34 headless (mw_solve.py) on modellen/AK-1*.liml, 28 Oct 2026:
# frequencies [Hz] per mode and the largest |p| of every mode (AK-14:
# (f, decay rate) per mode).
MECWAY = {
    "AK-10": {"f": (0.0, 170.001144062645, 242.863913831974, 296.451172986835,
                    340.036057597543, 417.861076785986, 485.924463095875,
                    510.267159780874),
              "pmax": (406.3777271737379, 574.7125791484837, 574.736519726137,
                       812.6989024610135, 574.8236261394176, 812.5201664932249,
                       575.1752109575878, 575.2706903437171)},
    "AK-11": {"f": (85.0000358901502, 255.008632489117, 257.30893589303,
                    352.153986243296, 425.108815934793, 489.59330110447,
                    493.302768206879, 548.775543309729),
              "pmax": (574.7053777678973, 574.7432417094274, 812.772822574348,
                       812.6022094724688, 574.9870826148422, 812.5005791330124,
                       813.309451108532, 813.851725134213)},
    "AK-12": {"f": (0.0, 170.000060897444, 242.857504849885, 296.446661320573,
                    340.001939220149, 417.836887443615, 485.725729030172,
                    510.01458084241),
              "pmax": (406.37772901842766, 574.7067616994974,
                       574.7126480438505, 812.7893743153694, 574.7345490105939,
                       812.8884322190193, 574.8272112291851,
                       574.8532895616586)},
    "AK-13": {"f": (85.0054618003764, 255.147491241787, 257.424590383691,
                    352.337527784501, 425.68303693088, 490.150527010849),
              "pmax": (574.7787535591063, 575.369977904496, 813.7130988006234,
                       814.5500938894614, 576.5542472393387,
                       816.2266615504748)},
    "AK-15": {"f": (4.75889160909226e-05, 170.145746301045, 243.282364561069,
                    297.626707783202, 341.168374823125, 421.152484908301,
                    489.130189048035, 513.956532046341),
              "pmax": (406.37772717378544, 576.282571756858, 577.9290905695824,
                       819.5561746904988, 581.0407230964199, 826.3151704550847,
                       587.7063082543339, 589.0547194676244)},
    "AK-14": {"modes": ((6.0297276545554e-12, -6.32088712281368e-11),
                        (170.001115565514, 70.3487853681979),
                        (244.45235693626, 32.5108305672279),
                        (296.960479613318, 71.7263764879966),
                        (340.035849831299, 70.3757461789113),
                        (417.944885637087, 70.8564441374815))},
}


def _pmax(r, k):
    return max(abs(v) for v in r.step(float(k))["pressure"].values())


def rect_modes(count, open_x=False):
    out = []
    for m in range(6):
        for n in range(5):
            kx = (2 * m - 1) / (2.0 * A) if open_x else m / A
            if open_x and m == 0:
                continue
            out.append((C_AIR / 2.0 * math.sqrt(kx ** 2 + (n / B) ** 2),
                        (m, n)))
    return sorted(out)[:count]


def _analytic(count, open_x, tol):
    src = ("f_mn = c/2 sqrt(((2m-1)/(2a))^2 + (n/b)^2) (p = 0 on x = a)"
           if open_x else "f_mn = c/2 sqrt((m/a)^2 + (n/b)^2) (hard walls)")
    out = []
    for k, (f, (m, n)) in enumerate(rect_modes(count, open_x)):
        if f == 0.0:
            out.append(Check("f1 (constante druk)", lambda r: r.mode(1),
                             ref=0.0, tol_abs=0.01, unit="Hz", source=src))
        else:
            out.append(Check("f%d mode %d%d" % (k + 1, m, n),
                             lambda r, k=k: r.mode(k + 1), ref=f, tol=tol,
                             unit="Hz", source=src))
    return out


def _mecway(case_id, first=1, tol=1e-6, ptol=1e-6):
    ref = MECWAY.get(case_id)
    if not ref:
        return []
    src = "Mecway 34 headless (mw_solve.py), eigen A20-oplossing"
    out = []
    for k, f in enumerate(ref["f"], start=1):
        if k < first:
            continue
        out.append(Check("f%d = Mecway" % k, lambda r, k=k: r.mode(k),
                         ref=f, tol=tol, unit="Hz", in_series=False,
                         source=src))
    for k, p in enumerate(ref["pmax"], start=1):
        out.append(Check("max|p| mode %d = Mecway" % k,
                         lambda r, k=k: _pmax(r, k), ref=p, tol=ptol,
                         unit="Pa", in_series=False,
                         source=src + "; normering p^T M p = 1 per "
                         "eenheidsdikte"))
    return out


def trimesh(m, elset, nu, nv, mapping, order=1):
    """Structured triangles: every cell of nu x nv split in two along
    alternating diagonals; tri3 or tri6 (Mecway's order corner, mid,
    corner, mid, corner, mid). Returns {"nodes": {side: set(nid)}}."""
    shape = "tri3" if order == 1 else "tri6"
    side_nodes = dict((s, set()) for s in ("u0", "u1", "v0", "v1"))
    for i in range(nu):
        for j in range(nv):
            c = [((i + a) / float(nu), (j + b) / float(nv))
                 for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
            tris = ((0, 1, 2), (0, 2, 3)) if (i + j) % 2 == 0 else \
                ((0, 1, 3), (1, 2, 3))
            for tri in tris:
                pts = [c[t] for t in tri]
                if order == 2:
                    full = []
                    for k in range(3):
                        p, q = pts[k], pts[(k + 1) % 3]
                        full += [p, (0.5 * (p[0] + q[0]),
                                     0.5 * (p[1] + q[1]))]
                    pts = full
                nids = [m.node(*mapping(*p)) for p in pts]
                m.elem(elset, shape, nids)
                for p, n in zip(pts, nids):
                    for side, idx, val in (("u0", 0, 0.0), ("u1", 0, 1.0),
                                           ("v0", 1, 0.0), ("v1", 1, 1.0)):
                        if abs(p[idx] - val) < 1e-12:
                            side_nodes[side].add(n)
    return {"nodes": side_nodes}


def build_ak10():
    m = Model("A20", attrs={"maxmode": 8})
    m.elset("Lucht", "Lucht")
    quadmesh(m, "Lucht", 10, 7, rect(0, A, 0, B), order=2)
    m.mat("Lucht", *AIR)
    return m


def build_ak11():
    m = Model("A20", attrs={"maxmode": 8})
    m.elset("Lucht", "Lucht")
    q = quadmesh(m, "Lucht", 10, 7, rect(0, A, 0, B), order=2)
    m.mat("Lucht", '<geometric type="Plate" thickness="10 mm" />', *AIR)
    m.face_selection("Open", q["edges"]["u1"])
    m.add('<fluidpressure selection="Open"><value>0 Pa</value>'
          '</fluidpressure>')
    return m


def build_ak12():
    m = Model("A20", attrs={"maxmode": 8})
    m.elset("Lucht", "Lucht")
    trimesh(m, "Lucht", 20, 14, rect(0, A, 0, B), order=2)
    m.mat("Lucht", *AIR)
    return m


def build_ak13():
    m = Model("A20", attrs={"maxmode": 6})
    m.elset("Links", "Lucht")
    m.elset("Rechts", "Lucht")
    quadmesh(m, "Links", 20, 28, rect(0, A / 2, 0, B), order=1)
    q = quadmesh(m, "Rechts", 20, 28, rect(A / 2, A, 0, B), order=1)
    m.mat("Lucht", *AIR)
    m.node_selection("Open", sorted(q["nodes"]["u1"]))
    m.add('<fluidpressure selection="Open"><value>0 Pa</value>'
          '</fluidpressure>')
    return m


def build_ak15():
    m = Model("A20", attrs={"maxmode": 8})
    m.elset("Lucht", "Lucht")
    trimesh(m, "Lucht", 20, 14, rect(0, A, 0, B), order=1)
    m.mat("Lucht", *AIR)
    return m


def build_ak14():
    m = Model("A20", attrs={"maxmode": 6})
    m.elset("Lucht", "Lucht")
    q = quadmesh(m, "Lucht", 10, 7, rect(0, A, 0, B), order=2)
    m.mat("Lucht", *AIR)
    m.face_selection("Absorber", q["edges"]["u1"])
    m.add('<impedance selection="Absorber"><specificimpedancer>%g'
          '</specificimpedancer><specificimpedancei>0</specificimpedancei>'
          '</impedance>' % Z_IMP)
    return m


def _impedance_checks():
    src = ("modes without y variation = tube with impedance (s_n = (c/a)"
           "(-artanh(rho c/Z) + i pi n))")
    out = []
    for n, s in tube_roots(complex(Z_IMP, 0.0), 3, L=A)[1:]:
        f = s.imag / (2.0 * math.pi)
        out.append(Check("f (n=%d, zonder y-variatie)" % n,
                         lambda r, s=s: _f(r, s), ref=f, tol=0.005,
                         unit="Hz", source=src))
        out.append(Check("decay rate (n=%d)" % n,
                         lambda r, s=s: _decay(r, s), ref=-s.real,
                         tol=0.005, unit="1/s", source=src))
    ref = MECWAY.get("AK-14")
    if ref:
        msrc = "Mecway 34 headless (mw_solve.py), eigen A20-oplossing"
        for f, d in ref["modes"]:
            if f <= 1e-3 and abs(d) < 1e-3:
                continue
            lam = _lam(f, d)
            if f > 1e-3:
                out.append(Check("f %.6g Hz = Mecway" % f,
                                 lambda r, lam=lam: _f(r, lam), ref=f,
                                 tol=1e-6, unit="Hz", in_series=False,
                                 source=msrc))
            out.append(Check("decay %.6g 1/s = Mecway" % d,
                             lambda r, lam=lam: _decay(r, lam), ref=d,
                             tol=1e-6, unit="1/s", in_series=False,
                             source=msrc))
    return out


TESTS = [
    Case("AK-10", GROUP, "2D (A20): rechthoek 1,0 x 0,7 m, harde wanden, "
         "quad8 10x7", "acoustic_modes_3d", build_ak10,
         _analytic(8, False, 0.005) +
         [Check("max|p| mode 1 = c / sqrt(A)", lambda r: _pmax(r, 1),
                ref=C_AIR / math.sqrt(A * B), tol=1e-6, unit="Pa",
                in_series=False,
                source="normering p^T M p = 1, M = int N N / c^2 dA per "
                       "eenheidsdikte (zoals Mecway)")] +
         _mecway("AK-10", first=2),
         note="De 2D-tegenhanger van AK-04 (MODELISATION 'PLAN')."),
    Case("AK-11", GROUP, "2D (A20): rechthoek, p = 0 op x = a (vlakselectie), "
         "dikte 10 mm", "acoustic_modes_3d", build_ak11,
         _analytic(8, True, 0.005) + _mecway("AK-11"),
         note="De dikte telt niet (Mecway evenmin)."),
    Case("AK-12", GROUP, "2D (A20): rechthoek, harde wanden, tri6 20x14x2",
         "acoustic_modes_3d", build_ak12,
         _analytic(8, False, 0.005) +
         _mecway("AK-12", first=2, tol=2e-4, ptol=5e-4),
         note="tri6: Code-Aster integreert de massa met de RIGI-familie "
              "(3 punten), Mecway exact: <= 0,02% verschil (KNOWN_BUGS "
              "128)."),
    Case("AK-13", GROUP, "2D (A20): quad4 in twee elsets, p = 0 op de "
         "knopen van x = a", "acoustic_modes_3d", build_ak13,
         _analytic(6, True, 0.01) + _mecway("AK-13"),
         note="Lineaire quads, twee elsets; knoopselectie."),
    Case("AK-15", GROUP, "2D (A20): rechthoek, harde wanden, tri3 20x14x2",
         "acoustic_modes_3d", build_ak15,
         _analytic(8, False, 0.03) +
         _mecway("AK-15", first=2, tol=0.01, ptol=0.01),
         note="tri3: Code-Aster integreert de massa met 1 punt, Mecway "
              "exact (consistent): de bridge ligt hoger (KNOWN_BUGS 128)."),
    Case("AK-14", GROUP, "2D (A20): impedantie Z = 2000 Pa.s/m op x = a "
         "(complexe modes)", "acoustic_modes_3d", build_ak14,
         _impedance_checks(),
         note="PLAN_ABSO-randen, aster_acoustic_complex."),
]
