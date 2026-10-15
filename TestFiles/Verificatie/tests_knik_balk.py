# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Linear buckling of beams: torsional buckling and frames with bending
moments (BU-30 ... BU-34), the two differences with Mecway in KNOWN_BUGS
112 and 113. Each beam model has an independent reference that does not
come from a beam formulation: a volume (hex20) or shell model of the same
structure, computed by the bridge (Code-Aster) and by Mecway 34 headless
(own solver and CCX, TestFiles/Tools/mw_solve.py, 15 Oct 2026, the same
.liml), or the reference of Code-Aster test case ssll105. Explanation:
docs/Verificatie.md (par. Knik van balken: torsie en raamwerken).

- BU-30/31: fixed column L = 1 m, I 100/50/10/8 mm, 1000 N compression.
  Torsional buckling without warping: P = G J A / I_p (Timoshenko & Gere,
  Theory of Elastic Stability, 2nd ed., 1961, par. 5.3, with C_w = 0). The
  hex20 model gives 2384 (-1.2%). Mecway's own beam has no torsional
  buckling at all: its 4th factor 2743.03 is the third flexural mode
  (25 x factor 1), also with J doubled.
- BU-32: L frame of KNOWN_BUGS 113 (column along Z, girder along X, 1 m
  each, RectBar 40 x 10 mm, 100 N downwards at the end of the girder). The
  out-of-plane mode: bridge 44.53, hex20 44.86 (converged; Code-Aster,
  Mecway and CCX equal on the same mesh), Mecway beam 19.71.
- BU-33/34: right-angle frame of Code-Aster test case ssll105 (legs
  240 mm, section 30 x 0.6 mm, E = 71240 MPa, end force F_X = -1 N):
  reference 0.68 and -1.088 (VALE_REFE of ssll105a/b). Mecway 34 beam:
  0.4226 (with shift 0.3; with its default shift 1 Mecway skips it and
  starts at 2.905), with F_X = +1: 0.5525 instead of 1.088. Shell model
  (DKT): Code-Aster, Mecway and CCX equal (0.70).

The bridge (RIGI_GEOM of POU_D_E, R3.08.01 par. 6) has the terms of the
moments at the nodes (moderate rotations), Mecway's beam does not:
reproduced with an own beam code (without those terms 19.71 / 0.4225 /
0.5526 as Mecway, with them 44.53 / 0.6813 / 1.0901 as Code-Aster).
"""
import math
from verif_lib import Case, Check, Model, hexmesh, quadmesh, box, rect
import tests_balkorientatie as BO

GROUP = "Knik"
E, G = BO.E, BO.G
STEEL = BO.STEEL


def _line(m, p0, p1, n, elset="Balk"):
    """n line2 elements from p0 to p1 (Mecway default orientation)."""
    nids = [m.node(*[p0[d] + (p1[d] - p0[d]) * i / float(n)
                     for d in range(3)]) for i in range(n + 1)]
    for i in range(n):
        m.elem(elset, "line2", [nids[i], nids[i + 1]])
    return nids


def _pos(r, k):
    """k-th smallest positive buckling factor."""
    return sorted(v for v in r.modes.values() if v > 0)[k - 1]


def _neg(r, k):
    """k-th negative buckling factor by magnitude (buckling under the
    reversed load)."""
    return sorted((v for v in r.modes.values() if v < 0), key=abs)[k - 1]


# ------------------------------------------------------------------
# BU-30/31: I column, torsional buckling
# ------------------------------------------------------------------
P = 1000.0
L = 1.0
I_A, I_V, I_W, I_J = BO.IP_A, BO.IP_IV, BO.IP_IW, BO.IP_J
P_EV = math.pi ** 2 * E * I_V / (4 * L ** 2)
P_EW = math.pi ** 2 * E * I_W / (4 * L ** 2)
# Torsional buckling without warping (Timoshenko & Gere 1961 par. 5.3,
# C_w = 0): independent of the length and the support of the twist.
P_T = G * I_J * I_A / (I_V + I_W)
SRC_T = ("P = G J A/I_p, I_p = I_V + I_W, J as Mecway (Timoshenko & Gere "
         "5.3 without warping)")
# Mecway 34 headless on modellen/BU-31.liml: own solver 2384.2765, CCX
# 2384.2767 (factor 4); Code-Aster through the bridge the same.
MW_BU31 = 2384.2765


def build_bu30():
    m = Model("B30", attrs={"maxmode": 6, "shift": 1})
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (0, 0, L), 20)
    m.mat("Mat", BO.IPROF, STEEL, BO.DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%g N</z></force>'
          % P)
    return m


def _tip_purity(r):
    """|u_tip| / (|rot_z,tip| x 50 mm) of mode 4: 0 = pure torsion."""
    tip = (0.0, 0.0, L)
    u = math.sqrt(sum(r.at("displ" + c, tip, time=4) ** 2 for c in "xyz"))
    return u / (abs(r.at("rotz", tip, time=4)) * 0.05)


def build_bu31():
    """I section as hex20 (height 100 along Y, flanges 50 x 10, web 8):
    flange 4 + 2 + 4 elements, 2 over the thickness, web 2 x 10, 50 over
    the length (3000 hex20). Bottom face fixed (warping restrained), top
    face uniform compression."""
    m = Model("B30", attrs={"maxmode": 6, "shift": 1})
    m.elset("Kolom", "Staal")
    xs = (-0.025, -0.004, 0.004, 0.025)
    blocks = [(xs[i], xs[i + 1], y0, y1, (4, 2, 4)[i], 2)
              for y0, y1 in ((-0.05, -0.04), (0.04, 0.05)) for i in range(3)]
    blocks.append((-0.004, 0.004, -0.04, 0.04, 2, 10))
    bot, top = [], []
    for x0, x1, y0, y1, nx, ny in blocks:
        ms = hexmesh(m, "Kolom", nx, ny, 50, box(x0, x1, y0, y1, 0.0, L),
                     order=2)
        bot += ms["faces"]["w0"]
        top += ms["faces"]["w1"]
    m.mat("Staal", STEEL)
    m.face_selection("Voet", bot)
    m.face_selection("Kop", top)
    m.add('<fixed selection="Voet" />')
    m.add('<traction selection="Kop"><x>0 Pa</x><y>0 Pa</y><z>-%r Pa</z>'
          '</traction>' % (P / I_A))
    return m


TESTS = [
    Case("BU-30", GROUP, "Torsional buckling, I column, beam (POU_D_E)",
         "buckling_3d", build_bu30,
         [Check("factor 1", lambda r: r.mode(1), ref=P_EV / P, tol=0.002,
                unit="-", source="pi^2 E I_V/(4L^2) (Timoshenko & Gere 2.1)"),
          Check("factor 2", lambda r: r.mode(2), ref=9 * P_EV / P,
                tol=0.002, unit="-", source="9 pi^2 E I_V/(4L^2)"),
          Check("factor 3", lambda r: r.mode(3), ref=P_EW / P, tol=0.002,
                unit="-", source="pi^2 E I_W/(4L^2)"),
          Check("factor 4 (torsion)", lambda r: r.mode(4), ref=P_T / P,
                tol=1e-4, unit="-", source=SRC_T),
          Check("mode 4 pure torsion", _tip_purity, ref=0.0, tol_abs=1e-6,
                unit="-", source="|u_tip| / (|rot_z| x 50 mm)"),
          Check("factor 4 vs hex20 (BU-31)", lambda r: r.mode(4),
                ref=MW_BU31, tol=0.025, unit="-", in_series=False,
                source="BU-31: hex20, Code-Aster = Mecway 34 = CCX")],
         note="I 100/50/10/8 mm, L = 1 m, 20 POU_D_E, P = 1000 N. The "
              "torsional factor is a multiple eigenvalue (one per "
              "element; Sturm alarm ALGELINE5_23). Mecway 34 beam: "
              "109.72 / 987.46 / 1230.44 / 2743.03 = 25 x factor 1, no "
              "torsional buckling (KNOWN_BUGS 112)."),
    Case("BU-31", GROUP, "Torsional buckling, I column, volume (hex20)",
         "buckling_3d", build_bu31,
         [Check("factor 1", lambda r: r.mode(1), ref=P_EV / P, tol=0.005,
                unit="-", source="pi^2 E I_V/(4L^2)"),
          Check("factor 4 (torsion) vs Mecway", lambda r: r.mode(4),
                ref=MW_BU31, tol=1e-4, unit="-", in_series=False,
                source="Mecway 34 headless, same .liml (CCX: 2384.2767)"),
          Check("factor 4 (torsion) vs G J A/I_p", lambda r: r.mode(4),
                ref=P_T / P, tol=0.025, unit="-", source=SRC_T)],
         note="3000 hex20. Below G J A/I_p despite the restrained warping "
              "at the foot: the exact J of the section is 1.7% smaller "
              "than Mecway's formula (finite differences: 46.3e3 mm^4) and "
              "the web distorts. With warping (POU_D_TG, C_w = 4.22e-10 "
              "m^6): 2552.5."),
]


# ------------------------------------------------------------------
# BU-32: L frame of KNOWN_BUGS 113
# ------------------------------------------------------------------
F_L = 100.0
# Euler: the column as a cantilever about its weak axis (the girder adds
# no rotational restraint at the top).
P_LF1 = math.pi ** 2 * E * BO.I_V / (4 * L ** 2)
# hex20 of the frame (column x = +-5 mm, girder z = 1 +- 5 mm, 40 mm along
# Y; 200 x 8 x 4 elements per member): Mecway 34 own solver 17.3085 /
# 44.8612 / 124.1153 (positive factors only). The same model with
# 100 x 4 x 2 through the bridge (static step with RESI_RELA off,
# KNOWN_BUGS 114): -53.543 / 17.315 / 45.030 / 124.64, equal to Mecway and
# CCX on that mesh.
SOLID_L = {"pos2": 44.8612, "pos3": 124.1153, "neg1": -53.543}
SRC_SOLID = "hex20 of the frame (Mecway 34 / CCX / Code-Aster equal)"


def build_bu32():
    m = Model("B30", attrs={"maxmode": 8, "shift": 1})
    m.elset("Balk", "Mat")
    col = _line(m, (0, 0, 0), (0, 0, L), 20)
    gir = _line(m, (0, 0, L), (L, 0, L), 20)
    m.mat("Mat", BO.RECT, STEEL, BO.DENS)
    m.node_selection("Inklemming", [col[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [gir[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%r N</z></force>'
          % F_L)
    return m


TESTS.append(Case(
    "BU-32", GROUP, "Frame in L, bending moments, beams (POU_D_E)",
    "buckling_3d", build_bu32,
    [Check("positive factor 1 (in plane)", lambda r: _pos(r, 1),
           ref=P_LF1 / F_L, tol=0.002, unit="-",
           source="pi^2 E I_V/(4L^2) of the column"),
     Check("positive factor 2 (out of plane)", lambda r: _pos(r, 2),
           ref=SOLID_L["pos2"], tol=0.02, unit="-", in_series=False,
           source=SRC_SOLID),
     Check("positive factor 3 (out of plane)", lambda r: _pos(r, 3),
           ref=SOLID_L["pos3"], tol=0.02, unit="-", in_series=False,
           source=SRC_SOLID),
     Check("negative factor 1 (reversed load)", lambda r: _neg(r, 1),
           ref=SOLID_L["neg1"], tol=0.02, unit="-", in_series=False,
           source="hex20 of the frame, Code-Aster (100 x 4 x 2)")],
    note="RectBar 40 x 10 mm, 20 POU_D_E per member, 100 N. Mecway 34 "
         "beam: 17.27 / 19.71 / 127.30 / 155.45 (only positive factors; "
         "the out-of-plane mode 19.71 is 56% too low, KNOWN_BUGS 113)."))


# ------------------------------------------------------------------
# BU-33/34: right-angle frame of Code-Aster test case ssll105
# ------------------------------------------------------------------
LA = 0.24
MAT_A = ('<mechanical type="Isotropic" youngsmodulus="71240 MPa" '
         'poissonratio="0.3" />')
UGS_A = ('<geometric type="UniformGeneralSection" area="18 mm²" '
         'iyy="0.54 mm⁴" izz="1350 mm⁴" torsionconstant="2.16 mm⁴" />')
SRC_A = ("ssll105a/b VALE_REFE (REFERENCE 'NON_DEFINI'; the literature "
         "source behind it NOT verified)")
# ssll105a (POU_D_E, 10 elements per leg): VALE_CALC -1.090064344 for
# F_X = -1, -0.681323581 for F_X = +1 (= +0.6813 for F_X = -1).
CA_A = (0.681323581, -1.090064344)
# Mecway 34 headless on modellen/BU-34.liml: own solver 0.7036 / 2.5625,
# CCX 0.7085; with F_X = +1 (same mesh): 1.1894 (CCX 1.2045).
MW_BU34 = (0.7036, 1.1894)


def build_bu33():
    m = Model("B30", attrs={"maxmode": 4, "shift": 1})
    m.elset("Balk", "Mat")
    a = _line(m, (0, 0, 0), (LA, 0, 0), 10)
    b = _line(m, (LA, 0, 0), (LA, -LA, 0), 10)
    m.mat("Mat", UGS_A, MAT_A)
    m.node_selection("PA", [a[0]])
    m.node_selection("PC", [b[-1]])
    m.add('<fixed selection="PA" />')
    m.add('<force selection="PC"><x>-1 N</x><y>0 N</y><z>0 N</z></force>')
    return m


def build_bu34():
    """Strip 30 mm wide, 0.6 mm thick in the XY plane: legs and a 30 x 30
    mm corner, quad4 DKT of 5 mm (6 over the width); edge x = 0 fixed,
    line load on the end edge (F_X = -1 N in total)."""
    m = Model("B30", attrs={"maxmode": 4, "shift": 1})
    m.elset("Plaat", "Mat")
    w, nw = 0.03, 6
    n1 = int(round((LA - w / 2) / 0.005))
    a = quadmesh(m, "Plaat", n1, nw, rect(0, LA - w / 2, -w / 2, w / 2))
    quadmesh(m, "Plaat", nw, nw, rect(LA - w / 2, LA + w / 2, -w / 2, w / 2))
    b = quadmesh(m, "Plaat", nw, n1, rect(LA - w / 2, LA + w / 2, -LA,
                                          -w / 2))
    m.mat("Mat", '<geometric type="Plate" thickness="0.6 mm" />', MAT_A)
    m.face_selection("PA", a["edges"]["u0"])
    m.face_selection("PC", b["edges"]["v0"])
    m.add('<fixed selection="PA" />')
    m.add('<linepressure selection="PC"><x>%r N/m</x><y>0 N/m</y>'
          '<z>0 N/m</z></linepressure>' % (-1.0 / w))
    return m


TESTS += [
    Case("BU-33", GROUP, "Right-angle frame ssll105, beams (POU_D_E)",
         "buckling_3d", build_bu33,
         [Check("positive factor 1", lambda r: _pos(r, 1), ref=0.68,
                tol=0.01, unit="-", source=SRC_A),
          Check("negative factor 1", lambda r: _neg(r, 1), ref=-1.088,
                tol=0.01, unit="-", source=SRC_A),
          Check("positive factor 1 vs ssll105", lambda r: _pos(r, 1),
                ref=CA_A[0], tol=1e-4, unit="-", in_series=False,
                source="ssll105a VALE_CALC (same mesh)"),
          Check("negative factor 1 vs ssll105", lambda r: _neg(r, 1),
                ref=CA_A[1], tol=1e-4, unit="-", in_series=False,
                source="ssll105a VALE_CALC (same mesh)")],
         note="Legs 240 mm, A = 18 mm^2, I = 0.54 / 1350 mm^4, J = 2.16 "
              "mm^4, E = 71240 MPa, 10 POU_D_E per leg, F_X = -1 N at the "
              "free end. Mecway 34 beam: 0.4226 / 2.905 (shift 0.3; "
              "with shift 1 the 0.4226 is skipped), with F_X = +1: 0.5525 "
              "/ 3.303; KNOWN_BUGS 113."),
    Case("BU-34", GROUP, "Right-angle frame ssll105, shell (DKT)",
         "buckling_3d", build_bu34,
         [Check("positive factor 1 vs Mecway", lambda r: _pos(r, 1),
                ref=MW_BU34[0], tol=0.002, unit="-", in_series=False,
                source="Mecway 34 headless, same .liml (CCX 0.7085)"),
          Check("negative factor 1 vs Mecway (F_X = +1)",
                lambda r: -_neg(r, 1), ref=MW_BU34[1], tol=0.005,
                unit="-", in_series=False,
                source="Mecway 34 headless, same mesh with F_X = +1 "
                       "(CCX 1.2045)"),
          Check("positive factor 1 vs beam reference", lambda r: _pos(r, 1),
                ref=0.68, tol=0.05, unit="-", in_series=False,
                source=SRC_A)],
         note="Strip 30 x 0.6 mm, quad4 DKT 5 mm. Higher than the line "
              "model (+3% and +9%): the 30 x 30 mm corner is stiff and "
              "shortens the legs."),
]


# ------------------------------------------------------------------
# BU-35/36: C column, flexural-torsional buckling (KNOWN_BUGS 115)
# ------------------------------------------------------------------
# C 100 x 50 x 6 mm (Mecway: ca flange width incl. web, cb height, cc
# flange, cd web), fixed column L = 1 m along Z, 1000 N compression. The
# bridge (GENERALE, values from the bridge log) has no shear centre and no
# warping: factor 1 pi^2 E I_V/(4L^2) = 136.02 (bending in the plane of
# symmetry, uncoupled), then G J A/I_p = 616.43 (multiple) and the strong
# axis 864.25. In reality the strong-axis bending couples with the twist
# about the shear centre.
C_A, C_IV, C_IW, C_J = 1.128e-3, 2.6251591489361716e-07, 1.667936e-06, \
    1.3061359970630146e-08
CPROF = '<geometric type="C" ca="50 mm" cb="100 mm" cc="6 mm" cd="6 mm" />'


def _ft_channel():
    """Flexural-torsional buckling load of the fixed C column (warping
    restrained at the foot, free at the top: effective length 2L), thin-
    walled centre-line formulas: b = 47, h = 94, t = 6 mm; shear centre
    e = 3 b^2 t/(6 b t + h t) from the web, C_w = t b^3 h^2/12 (3 b + 2 h)/
    (6 b + h); i0^2 = I_p/A + x0^2; P from i0^2 (P - P_x)(P - P_T) - P^2
    x0^2 = 0 (Timoshenko & Gere 1961 par. 5.3; the section formulas are the
    usual thin-walled ones, NOT checked against a book in this repo)."""
    b, h, t = 0.047, 0.094, 0.006
    e = 3 * b * b * t / (6 * b * t + h * t)
    xc = (2 * b * t * b / 2) / (2 * b * t + h * t)
    x0 = e + xc
    cw = t * b ** 3 * h ** 2 / 12.0 * (3 * b + 2 * h) / (6 * b + h)
    i02 = (C_IV + C_IW) / C_A + x0 ** 2
    p_t = (G * C_J + math.pi ** 2 * E * cw / (4 * L ** 2)) / i02
    p_x = math.pi ** 2 * E * C_IW / (4 * L ** 2)
    beta = 1 - x0 ** 2 / i02
    s = p_x + p_t
    return (s - math.sqrt(s * s - 4 * beta * p_x * p_t)) / (2 * beta)


P_FT = _ft_channel()
# Mecway 34 headless on modellen/BU-36.liml (own solver; CCX the same):
# 135.4126 / 393.0329. Mecway's beam with the C profile gave no solution
# headless (as with L before).
MW_BU36 = (135.4126, 393.0329)


def build_bu35():
    m = Model("B30", attrs={"maxmode": 6, "shift": 1})
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (0, 0, L), 20)
    m.mat("Mat", CPROF, STEEL, BO.DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%g N</z></force>'
          % P)
    return m


def build_bu36():
    """C section as hex20: web x = 0 ... 6 mm (2 x 16 elements), flanges
    y = +-(44 ... 50) mm to x = 50 mm (2 + 8 by 2 elements), 50 over the
    length (3600 hex20); bottom face fixed, top face uniform compression."""
    a, b, c, d = 0.050, 0.100, 0.006, 0.006
    m = Model("B30", attrs={"maxmode": 6, "shift": 1})
    m.elset("Kolom", "Staal")
    blocks = [(0, d, -b / 2, -b / 2 + c, 2, 2), (d, a, -b / 2, -b / 2 + c, 8, 2),
              (0, d, b / 2 - c, b / 2, 2, 2), (d, a, b / 2 - c, b / 2, 8, 2),
              (0, d, -b / 2 + c, b / 2 - c, 2, 16)]
    bot, top = [], []
    for x0, x1, y0, y1, nx, ny in blocks:
        ms = hexmesh(m, "Kolom", nx, ny, 50, box(x0, x1, y0, y1, 0.0, L),
                     order=2)
        bot += ms["faces"]["w0"]
        top += ms["faces"]["w1"]
    m.mat("Staal", STEEL)
    m.face_selection("Voet", bot)
    m.face_selection("Kop", top)
    m.add('<fixed selection="Voet" />')
    m.add('<traction selection="Kop"><x>0 Pa</x><y>0 Pa</y><z>-%r Pa</z>'
          '</traction>' % (P / C_A))
    return m


TESTS += [
    Case("BU-35", GROUP, "Flexural-torsional buckling, C column, beam "
         "(POU_D_E)", "buckling_3d", build_bu35,
         [Check("factor 1 (uncoupled)", lambda r: r.mode(1),
                ref=MW_BU36[0], tol=0.01, unit="-", in_series=False,
                source="BU-36: hex20, Code-Aster = Mecway 34"),
          Check("factor 2 vs G J A/I_p", lambda r: r.mode(2),
                ref=G * C_J * C_A / (C_IV + C_IW) / P, tol=1e-4, unit="-",
                source="what POU_D_E computes: torsion about the centroid, "
                       "no warping"),
          Check("factor 2 vs flexural-torsional", lambda r: r.mode(2),
                ref=MW_BU36[1], tol=0.05, unit="-", in_series=False,
                known="KNOWN_BUGS 115",
                source="BU-36: hex20 (theory %.1f)" % (P_FT / P))],
         note="C 100 x 50 x 6 mm, L = 1 m, 20 POU_D_E, P = 1000 N. The "
              "beam misses the flexural-torsional mode (616 instead of "
              "393, +57%): POU_D_E has no shear centre. The bridge warns "
              "for T, C and L in buckling."),
    Case("BU-36", GROUP, "Flexural-torsional buckling, C column, volume "
         "(hex20)", "buckling_3d", build_bu36,
         [Check("factor 1 vs pi^2 E I_V/(4L^2)", lambda r: r.mode(1),
                ref=math.pi ** 2 * E * C_IV / (4 * L ** 2) / P, tol=0.01,
                unit="-", source="Euler, bending in the plane of symmetry"),
          Check("factor 2 vs Mecway", lambda r: r.mode(2), ref=MW_BU36[1],
                tol=1e-4, unit="-", in_series=False,
                source="Mecway 34 headless, same .liml"),
          Check("factor 2 vs flexural-torsional theory", lambda r: r.mode(2),
                ref=P_FT / P, tol=0.03, unit="-",
                source="Timoshenko & Gere 5.3, shear centre and C_w of the "
                       "thin-walled channel (see _ft_channel)")],
         note="3600 hex20. Theory (thin-walled, with warping) %.1f." % (
             P_FT / P)),
]
