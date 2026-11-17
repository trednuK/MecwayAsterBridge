# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Axisymmetric shells (STAPPENPLAN S44e piece 1; Scripts/bridge_plane.py):
Mecway Static 3D (S30) or Nonlinear Static (L30) with line3 elements in the
XY plane (X = radius, Y = axis) and the lines '**ASTER-PLANE AXIS' and
'**ASTER-SHELL <material>: EPAIS=<t>' -> MODELISATION 'COQUE_AXIS' (SEG3),
AFFE_CARA_ELEM COQUE EPAIS. Explanation: docs/Verificatie.md chapter 2D and
axisymmetric (PL). Closed forms: Timoshenko & Woinowsky-Krieger, "Theory of
plates and shells" (membrane cylinder and sphere, clamped circular plate,
edge-loaded long cylinder: beta^4 = 3 (1 - nu^2) / (R^2 t^2)).

PL-60  thin cylinder, internal pressure, axially free: u_r = p R^2 / (E t)
       and the axial shortening nu p R L / (E t).
PL-61  thin sphere, internal pressure (quarter meridian, symmetry at the
       equator and the pole): u = p R^2 (1 - nu) / (2 E t).
PL-62  clamped circular plate under pressure: w0 = q a^4 / (64 D), the
       rotation about Z at r = a/2 (+3 q a^3 / (128 D), the DRZ sign) and
       the sum of the reactions q pi a^2.
PL-63  long cylinder clamped at one end, internal pressure, axially free:
       the reaction moment per circumference M0 = p / (2 beta^2) and the
       radial reaction per circumference -p / beta.
PL-64  Code-Aster test case ssls114i rebuilt (R = 1, L = 0.5, t = 0.05,
       2 SEG3, pressure 10 Pa, DY = 0 at the bottom): DX = 1.0000e-9
       (VALE_CALC of FORCE_COQUE with MODI_METRIQUE 'NON'); the side of the
       pressure (pushes along n = Z x U, as Mecway draws it).
PL-65  PL-60 in L30 with the pressure as a time table: small
       displacements forced (WARNING), u_r at t = 0.5 and 1 s.
PL-66  cylinder with an axial force on its bottom node (FORCE_NODALE / 2
       pi): the elongation F L / (2 pi R t E) and the reaction F.
PL-67  long cylinder with a ring moment on its free end (MZ / 2 pi): the
       edge displacement M0 / (2 beta^2 D) and rotation M0 / (beta D).
PL-68  cylinder under its own weight (gravity along -Y): the reaction
       rho g 2 pi R t L and the bridge's mass check (BRIDGE_STATCHECK:
       MASS_INER of COQUE_AXIS is already the mass of 360 degrees,
       rho 2 pi R t L = 123.3 kg, measured with Code-Aster 17.4).
"""
import math

from verif_lib import Case, Check, Model, static_check

GROUP = "2D en axisymmetrisch"
E, NU = 210e9, 0.3
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
RHO = 7850.0
DENS = '<density type="Simple" density="7850 kg/m&#179;" />'


def linemesh3(m, elset, n, curve, reverse=True):
    """n line3 elements along curve(s), s = 0 .. 1 (Mecway's node order:
    end, mid, end). Returns (eids, nids of the end nodes in the order of
    s). reverse (default): every element runs against s (node 1 at the
    larger s), so that a positive pressure, which pushes along n = Z x U as
    Mecway draws it, is an internal pressure on a chain drawn upwards at
    X > 0 and pushes along -Y on a plate drawn outwards."""
    ends = [m.node(*curve(float(i) / n)) for i in range(n + 1)]
    eids = []
    for i in range(n):
        mid = m.node(*curve((i + 0.5) / n))
        nodes = [ends[i], mid, ends[i + 1]]
        if reverse:
            nodes.reverse()
        eids.append(m.elem(elset, "line3", nodes))
    return eids, ends


def line(p0, p1):
    def f(s):
        return (p0[0] + (p1[0] - p0[0]) * s, p0[1] + (p1[1] - p0[1]) * s,
                0.0)
    return f


def _custom(m, mat, t, extra=""):
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE AXIS\n"
          u"**ASTER-SHELL %s: EPAIS=%r%s</ccxmodeldefinition>" % (
              mat, t, extra))


def _pressure(m, sel, eids, value):
    m.face_selection(sel, [(e, 1) for e in eids])
    m.add('<surfacepressure selection="%s">%s</surfacepressure>' % (
        sel, value))


def _hold(m, sel, nids, comps):
    """Displacement 0 along each axis of comps ('x', 'y')."""
    m.node_selection(sel, nids)
    for c in comps:
        m.add('<displacement selection="%s"><value>0 m</value><x>%d</x>'
              '<y>%d</y><z>0</z></displacement>' % (sel, c == "x", c == "y"))


def _symmetry(m, sel, nids, normal):
    m.node_selection(sel, nids)
    m.add('<symmetry selection="%s"><x>%d</x><y>%d</y><z>0</z></symmetry>'
          % (sel, normal == "x", normal == "y"))


# ------------------------------------------------------------------
# PL-60 / PL-65 thin cylinder under internal pressure
# ------------------------------------------------------------------
R60, T60, L60, P60 = 0.5, 0.005, 1.0, 1.0e6
U60 = P60 * R60 ** 2 / (E * T60)
V60 = -NU * P60 * R60 * L60 / (E * T60)


def build_pl60(analysis="S30"):
    def build():
        m = Model(analysis, timesteps=(
            {"timeperiod": "1 s", "stepsize": "0.5 s"}
            if analysis == "L30" else None))
        m.elset("Buis", "Staal")
        eids, ends = linemesh3(m, "Buis", 20, line((R60, 0.0), (R60, L60)))
        m.mat("Staal", STEEL)
        if analysis == "L30":
            value = ('<normal time="0 s">0 Pa</normal>'
                     '<normal time="1 s">%r Pa</normal>' % P60)
        else:
            value = '<normal>%r Pa</normal>' % P60
        _pressure(m, "Binnen", eids, value)
        _hold(m, "Onder", [ends[0]], "y")
        _custom(m, "Staal", T60)
        return m
    return build


# ------------------------------------------------------------------
# PL-61 thin sphere under internal pressure
# ------------------------------------------------------------------
R61, T61, P61 = 1.0, 0.01, 1.0e5
U61 = P61 * R61 ** 2 * (1.0 - NU) / (2.0 * E * T61)


def build_pl61():
    m = Model("S30")
    m.elset("Bol", "Staal")
    eids, ends = linemesh3(m, "Bol", 32, lambda s: (
        R61 * math.cos(0.5 * math.pi * s), R61 * math.sin(0.5 * math.pi * s),
        0.0))
    # thickness from the Shell/membrane geometry; the line gives the same
    # value (INFO)
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />', STEEL)
    _pressure(m, "Binnen", eids, '<normal>%r Pa</normal>' % P61)
    _symmetry(m, "Evenaar", [ends[0]], "y")
    _symmetry(m, "Pool", [ends[-1]], "x")
    _custom(m, "Staal", T61)
    return m


# ------------------------------------------------------------------
# PL-62 clamped circular plate under pressure
# ------------------------------------------------------------------
A62, T62, Q62 = 1.0, 0.01, 1000.0
D62 = E * T62 ** 3 / (12.0 * (1.0 - NU ** 2))
W62 = Q62 * A62 ** 4 / (64.0 * D62)
ROT62 = 3.0 * Q62 * A62 ** 3 / (128.0 * D62)


def build_pl62():
    m = Model("S30")
    m.elset("Plaat", "Staal")
    eids, ends = linemesh3(m, "Plaat", 20, line((0.0, 0.0), (A62, 0.0)))
    # thickness from a RectBar (dimension a in the XY plane, default V)
    m.mat("Staal", '<geometric type="RectBar" recta="10 mm" rectb="20 mm" />',
          STEEL)
    _pressure(m, "Druk", eids, '<normal>%r Pa</normal>' % Q62)
    m.node_selection("Rand", [ends[-1]])
    m.add('<fixed selection="Rand" />')
    _symmetry(m, "As", [ends[0]], "x")
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE AXIS</ccxmodeldefinition>")
    return m


# ------------------------------------------------------------------
# PL-63 long cylinder with a clamped end
# ------------------------------------------------------------------
R63, T63, L63, P63, N63 = 1.0, 0.01, 0.5, 1.0e5, 100
BETA63 = (3.0 * (1.0 - NU ** 2) / (R63 ** 2 * T63 ** 2)) ** 0.25
M063 = P63 / (2.0 * BETA63 ** 2)
Q063 = -P63 / BETA63


def build_pl63():
    m = Model("S30")
    m.elset("Buis", "Staal")
    eids, ends = linemesh3(m, "Buis", N63, line((R63, 0.0), (R63, L63)))
    m.mat("Staal", STEEL)
    _pressure(m, "Binnen", eids, '<normal>%r Pa</normal>' % P63)
    m.node_selection("Klem", [ends[0]])
    m.add('<fixed selection="Klem" />')
    _custom(m, "Staal", T63)
    return m


# ------------------------------------------------------------------
# PL-64 Code-Aster test case ssls114i
# ------------------------------------------------------------------
# Mesh ssls114i.mail: B (1, 0), N3, N2, N1, A (1, 0.5), M1 = B N2 N3 and
# M2 = N2 A N1 (SEG3: end, end, mid); Mecway's line3 is end, mid, end.
# E = 2e11, nu = 0.3, EPAIS 0.05; DDL_IMPO DY = 0 at B; FORCE_COQUE PRES =
# 10 Pa with ORIE_NORM_COQUE VECT_NORM (-1, 0) (the normal towards the
# axis). Here the elements run A -> B (linemesh3 reverse): Code-Aster's own
# cell normal U x Z is then -X = VECT_NORM, and the bridge's PRES = +p pushes
# along n = Z x U = +X: ssls114i without ORIE_NORM_COQUE. TEST_RESU of RESM (CARA_ELEM CA, MODI_METRIQUE
# 'NON'): DX = 1.00000000e-09 at A, B and N1 (VALE_CALC).
def build_pl64():
    m = Model("S30")
    m.elset("Cilinder", "Staal")
    eids, ends = linemesh3(m, "Cilinder", 2, line((1.0, 0.0), (1.0, 0.5)))
    m.mat("Staal", '<mechanical type="Isotropic" youngsmodulus="200000 MPa" '
          'poissonratio="0.3" />')
    _pressure(m, "Druk", eids, '<normal>10 Pa</normal>')
    _hold(m, "PB", [ends[0]], "y")
    m.node_selection("PA", [ends[-1]])
    _custom(m, "Staal", 0.05)
    return m


# ------------------------------------------------------------------
# PL-66 axial force, PL-67 ring moment, PL-68 own weight
# ------------------------------------------------------------------
F66 = 1000.0
DY66 = -F66 * L60 / (2.0 * math.pi * R60 * T60 * E)


def build_pl66():
    m = Model("S30")
    m.elset("Buis", "Staal")
    _eids, ends = linemesh3(m, "Buis", 20, line((R60, 0.0), (R60, L60)))
    m.mat("Staal", STEEL)
    _hold(m, "Boven", [ends[-1]], "y")
    m.node_selection("Onder", [ends[0]])
    m.add('<force selection="Onder"><x>0 N</x><y>%r N</y><z>0 N</z>'
          '</force>' % -F66)
    _custom(m, "Staal", T60)
    return m


M067 = 100.0                      # N m per m of circumference
D67 = E * T63 ** 3 / (12.0 * (1.0 - NU ** 2))
W67 = M067 / (2.0 * BETA63 ** 2 * D67)
ROT67 = M067 / (BETA63 * D67)
L67 = 0.6


def build_pl67():
    m = Model("S30")
    m.elset("Buis", "Staal")
    _eids, ends = linemesh3(m, "Buis", 120, line((R63, 0.0), (R63, L67)))
    m.mat("Staal", STEEL)
    m.node_selection("Klem", [ends[-1]])
    m.add('<fixed selection="Klem" />')
    m.node_selection("Rand", [ends[0]])
    m.add('<moment selection="Rand"><x>0 N.m</x><y>0 N.m</y><z>%r N.m</z>'
          '</moment>' % (M067 * 2.0 * math.pi * R63))
    _custom(m, "Staal", T63)
    return m


G68 = 9.81
W68 = RHO * G68 * 2.0 * math.pi * R60 * T60 * L60


def build_pl68():
    m = Model("S30")
    m.elset("Buis", "Staal")
    _eids, ends = linemesh3(m, "Buis", 20, line((R60, 0.0), (R60, L60)))
    m.mat("Staal", STEEL, DENS)
    _hold(m, "Boven", [ends[-1]], "y")
    m.add(u'<gravity><x>0 m/s&#178;</x><y>%r m/s&#178;</y><z>0 m/s&#178;</z>'
          u'</gravity>' % -G68)
    _custom(m, "Staal", T60)
    return m


# Stresses and section forces (S44e piece 2): top (u1) = the face a positive
# pressure acts on (where Mecway draws the arrows, the side U x Z); stresszz = hoop, the meridional
# stress in stressxx/yy/xy; forceperlengthu/momentu along the meridian,
# forceperlengthv/momentv hoop; momentu > 0 = tension on top.
FIELDS_AX = ["displacements", "stresses", "vonmises", "reactions",
             "shell_stresses", "shell_forces", "principal_stresses"]
S60 = P60 * R60 / T60                       # hoop p R / t
S61 = P61 * R61 / (2.0 * T61)               # sphere p R / (2 t)
S62 = 3.0 * Q62 * A62 ** 2 / (4.0 * T62 ** 2)     # radial at the clamp
S62C = 3.0 * (1.0 + NU) * Q62 * A62 ** 2 / (8.0 * T62 ** 2)   # centre
R62B = 0.9 * A62                            # a corner node near the clamp
# Timoshenko, clamped plate: M_r and M_theta at r (positive: sagging)
MR62 = Q62 * (A62 ** 2 * (1.0 + NU) - R62B ** 2 * (3.0 + NU)) / 16.0
MT62 = Q62 * (A62 ** 2 * (1.0 + NU) - R62B ** 2 * (1.0 + 3.0 * NU)) / 16.0
S63 = 6.0 * M063 / T63 ** 2                 # bending at the clamp
N66 = F66 / (2.0 * math.pi * R60)           # axial force per circumference
C45 = 0.5 * math.sqrt(2.0)


def _stress_checks_60(t=None, factor=1.0):
    at = (R60, 0.5 * L60, 0.0)
    return [
        Check("hoop midden" + ("" if t is None else " t = %g s" % t),
              lambda r: r.at("stresszzm1", at, time=t), ref=S60 * factor,
              tol=0.005, unit="Pa", source="membraan: p R / t"),
        Check("meridiaan midden", lambda r: r.at("stressyym1", at, time=t),
              ref=0.0, tol_abs=1e-3 * S60, unit="Pa", in_series=False,
              source="axiaal vrij: 0")]


TESTS = []
TESTS.append(Case(
    "PL-60", GROUP, "Dunne cilinder, inwendige druk (S30 + #ASTER-PLANE "
    "AXIS, COQUE_AXIS)", "lin_static_3d", build_pl60(),
    [Check("u_r halverwege", lambda r: r.at("displx", (R60, 0.5 * L60, 0.0)),
           ref=U60, tol=0.005, unit="m", source="membraan: p R^2 / (E t)"),
     Check("u_y boven", lambda r: r.at("disply", (R60, L60, 0.0)),
           ref=V60, tol=0.005, unit="m",
           source="membraan, axiaal vrij: -nu p R L / (E t)")] +
    _stress_checks_60() + [
     Check("von Mises boven", lambda r: r.at(
         "vonmisesu1", (R60, 0.5 * L60, 0.0)), ref=S60, tol=0.005,
         unit="Pa", source="membraan: alleen de ringspanning"),
     Check("N_v (ring) midden", lambda r: r.at(
         "forceperlengthv", (R60, 0.5 * L60, 0.0)), ref=P60 * R60,
         tol=0.005, unit="N/m", source="membraan: p R"),
     Check("hoofdspanning 1 boven", lambda r: r.at(
         "principal1u1", (R60, 0.5 * L60, 0.0)), ref=S60, tol=0.005,
         unit="Pa", source="membraan: p R / t")],
    settings={"fields": FIELDS_AX},
    note="R = 0,5 m, t = 5 mm (#ASTER-SHELL), L = 1 m, 20 line3, p = 1 MPa "
         "op faceid 1, Y vast in de onderste knoop."))
TESTS.append(Case(
    "PL-61", GROUP, "Dunne bol, inwendige druk (COQUE_AXIS)",
    "lin_static_3d", build_pl61,
    [Check("u_r evenaar", lambda r: r.at("displx", (R61, 0.0, 0.0)),
           ref=U61, tol=0.005, unit="m",
           source="membraan: p R^2 (1 - nu) / (2 E t)"),
     Check("u_y pool", lambda r: r.at("disply", (0.0, R61, 0.0)),
           ref=U61, tol=0.005, unit="m",
           source="membraan: p R^2 (1 - nu) / (2 E t)"),
     Check("ring evenaar", lambda r: r.at("stresszzm1", (R61, 0.0, 0.0)),
           ref=S61, tol=0.005, unit="Pa", source="membraan: p R / (2 t)"),
     Check("meridiaan evenaar", lambda r: r.at(
         "stressyym1", (R61, 0.0, 0.0)), ref=S61, tol=0.005, unit="Pa",
         source="membraan: p R / (2 t), langs Y"),
     Check("xx bij 45 graden", lambda r: r.at(
         "stressxxm1", (C45 * R61, C45 * R61, 0.0)), ref=0.5 * S61,
         tol=1e-5, unit="Pa", source="draaiing: sigma / 2"),
     Check("xy bij 45 graden", lambda r: r.at(
         "stressxym1", (C45 * R61, C45 * R61, 0.0)), ref=-0.5 * S61,
         tol=1e-5, unit="Pa",
         source="draaiing met de raaklijn: -sigma / 2 (koorde: 1e-3)")],
    settings={"fields": FIELDS_AX},
    note="R = 1 m, t = 10 mm (Shell/membrane en #ASTER-SHELL gelijk), kwart "
         "meridiaan 32 line3, p = 0,1 MPa; symmetrie Y in de evenaar, X in "
         "de pool (houdt ook de rotatie om Z vast)."))
TESTS.append(Case(
    "PL-62", GROUP, "Ingeklemde ronde plaat onder druk (COQUE_AXIS)",
    "lin_static_3d", build_pl62,
    [Check("w midden", lambda r: r.at("disply", (0.0, 0.0, 0.0)),
           ref=-W62, tol=0.005, unit="m",
           source="Timoshenko: q a^4 / (64 D), D = E t^3 / (12 (1 - nu^2))"),
     Check("rotatie om Z bij r = a/2", lambda r: r.at(
         "rotz", (0.5 * A62, 0.0, 0.0)), ref=ROT62, tol=0.005, unit="rad",
         source="dw/dr = 3 q a^3 / (128 D) (rechtsom om +Z)"),
     Check("som R_y rand", lambda r: r.total("reactionforcey", "Rand"),
           ref=Q62 * math.pi * A62 ** 2, tol=1e-6, unit="N",
           in_series=False, source="evenwicht: q pi a^2 (360 graden)"),
     Check("radiaal boven r = 0,9 a", lambda r: r.at(
         "stressxxu1", (R62B, 0.0, 0.0)), ref=-6.0 * MR62 / T62 ** 2,
         tol=0.005, unit="Pa",
         source="Timoshenko: -6 M_r / t^2 (trek aan de drukzijde)"),
     Check("radiaal onder r = 0,9 a", lambda r: r.at(
         "stressxxb1", (R62B, 0.0, 0.0)), ref=6.0 * MR62 / T62 ** 2,
         tol=0.005, unit="Pa", source="Timoshenko: 6 M_r / t^2"),
     Check("ring boven r = 0,9 a", lambda r: r.at(
         "stresszzu1", (R62B, 0.0, 0.0)), ref=-6.0 * MT62 / T62 ** 2,
         tol=0.005, unit="Pa", source="Timoshenko: -6 M_theta / t^2"),
     Check("ring boven midden", lambda r: r.at(
         "stresszzu1", (0.0, 0.0, 0.0)), ref=-S62C, tol=0.005, unit="Pa",
         source="Timoshenko: -3 (1 + nu) q a^2 / (8 t^2)"),
     Check("M_u r = 0,9 a", lambda r: r.at("momentu", (R62B, 0.0, 0.0)),
           ref=-MR62, tol=0.005, unit="N m/m",
           source="Timoshenko: -M_r (trek boven)"),
     Check("M_v r = 0,9 a", lambda r: r.at("momentv", (R62B, 0.0, 0.0)),
           ref=-MT62, tol=0.005, unit="N m/m",
           source="Timoshenko: -M_theta (trek boven)"),
     Check("radiaal boven rand", lambda r: r.at(
         "stressxxu1", (A62, 0.0, 0.0)), ref=S62, tol=0.05, unit="Pa",
         in_series=False,
         source="3 q a^2 / (4 t^2); in de klemknoop lineair per element "
                "(gemeten -4,4 % met 20 line3)")],
    settings={"fields": FIELDS_AX},
    note="a = 1 m, t = 10 mm (RectBar a = 10 mm, b = 20 mm, geen regel), "
         "20 line3 van de rand naar het midden, q = 1000 Pa op faceid 1 "
         "(duwt langs -Y); "
         "rand Fixed, midden symmetrie X."))
TESTS.append(Case(
    "PL-63", GROUP, "Lange cilinder met ingeklemd uiteinde, inwendige druk "
    "(COQUE_AXIS)", "lin_static_3d", build_pl63,
    [Check("M0 per omtrek", lambda r: r.total("reactionmomz", "Klem") /
           (2.0 * math.pi * R63), ref=M063, tol=0.02, unit="N m/m",
           source="Timoshenko: M0 = p / (2 beta^2), beta^4 = 3 (1 - nu^2) / "
                  "(R^2 t^2)"),
     Check("Q0 per omtrek", lambda r: r.total("reactionforcex", "Klem") /
           (2.0 * math.pi * R63), ref=Q063, tol=0.02, unit="N/m",
           source="Timoshenko: Q0 = p / beta (naar de as)"),
     Check("meridiaan boven klem", lambda r: r.at(
         "stressyyu1", (R63, 0.0, 0.0)), ref=S63, tol=0.02, unit="Pa",
         source="6 M0 / t^2, trek aan de binnenkant (boven)"),
     Check("meridiaan onder klem", lambda r: r.at(
         "stressyyb1", (R63, 0.0, 0.0)), ref=-S63, tol=0.02, unit="Pa",
         source="-6 M0 / t^2"),
     Check("M_u klem", lambda r: r.at("momentu", (R63, 0.0, 0.0)),
           ref=M063, tol=0.02, unit="N m/m",
           source="Timoshenko: M0 (trek boven)")],
    settings={"fields": FIELDS_AX},
    note="R = 1 m, t = 10 mm (R/t = 100), L = 0,5 m = %.1f / beta, 100 line3 "
         "(%.2f / beta), p = 0,1 MPa; Fixed in de onderste knoop, axiaal "
         "vrij." % (L63 * BETA63, L63 / N63 * BETA63)))
TESTS.append(Case(
    "PL-64", GROUP, "ssls114i: cilinder COQUE_AXIS onder druk",
    "lin_static_3d", build_pl64,
    [Check("DX in A (ssls114i)", lambda r: r.at("displx", (1.0, 0.5, 0.0)),
           ref=1.0e-9, tol=1e-6, unit="m",
           source="ssls114i TEST_RESU RESM DX (VALE_CALC, MODI_METRIQUE "
                  "'NON')"),
     Check("DX in B (ssls114i)", lambda r: r.at("displx", (1.0, 0.0, 0.0)),
           ref=1.0e-9, tol=1e-6, unit="m",
           source="ssls114i TEST_RESU RESM DX (VALE_CALC)"),
     Check("DX in N1 (ssls114i)", lambda r: r.at("displx",
                                                 (1.0, 0.375, 0.0)),
           ref=1.0e-9, tol=1e-6, unit="m",
           source="ssls114i TEST_RESU RESM DX (VALE_CALC)")],
    note="Het net van ssls114i (2 SEG3 van A naar B), E = 200000 MPa, "
         "t = 0,05 m, druk 10 Pa op faceid 1, Y vast in B."))
TESTS.append(Case(
    "PL-65", GROUP, "Dunne cilinder, druk als tijdtabel (L30 + "
    "#ASTER-PLANE AXIS)", "nonlin_static_3d", build_pl60("L30"),
    [Check("u_r t = %g s" % t, lambda r, t=t: r.at(
        "displx", (R60, 0.5 * L60, 0.0), time=t), ref=U60 * t, tol=0.005,
        unit="m", source="membraan: p(t) R^2 / (E t)") for t in (0.5, 1.0)] +
    _stress_checks_60(0.5, 0.5)[:1],
    settings={"fields": FIELDS_AX},
    note="PL-60 als L30, druk 0 .. 1 MPa over 1 s in twee stappen, "
         "deformation GROT_GDEP (standaard) -> PETIT met een WARNING."))
TESTS.append(Case(
    "PL-66", GROUP, "Cilinder met een axiale knoopkracht (COQUE_AXIS)",
    "lin_static_3d", build_pl66,
    [Check("u_y onder", lambda r: r.at("disply", (R60, 0.0, 0.0)),
           ref=DY66, tol=0.005, unit="m",
           source="F L / (2 pi R t E)"),
     Check("R_y boven", lambda r: r.total("reactionforcey", "Boven"),
           ref=F66, tol=1e-6, unit="N", in_series=False,
           source="evenwicht (360 graden)"),
     Check("N_u midden", lambda r: r.at(
         "forceperlengthu", (R60, 0.5 * L60, 0.0)), ref=N66, tol=0.005,
         unit="N/m", source="F / (2 pi R), trek (per lengte omtrek)"),
     Check("meridiaan midden", lambda r: r.at(
         "stressyym1", (R60, 0.5 * L60, 0.0)), ref=N66 / T60, tol=0.005,
         unit="Pa", source="F / (2 pi R t)")],
    settings={"fields": FIELDS_AX},
    note="De buis van PL-60, Y vast boven, kracht -1000 N langs Y op de "
         "onderste knoop (de hele ring)."))
TESTS.append(Case(
    "PL-67", GROUP, "Lange cilinder met een randmoment (COQUE_AXIS)",
    "lin_static_3d", build_pl67,
    [Check("u_r rand", lambda r: r.at("displx", (R63, 0.0, 0.0)),
           ref=W67, tol=0.02, unit="m",
           source="Timoshenko: M0 / (2 beta^2 D)"),
     Check("rotatie om Z rand", lambda r: r.at("rotz", (R63, 0.0, 0.0)),
           ref=ROT67, tol=0.02, unit="rad",
           source="Timoshenko: M0 / (beta D)"),
     Check("M_z inklemming", lambda r: r.total("reactionmomz", "Klem"),
           ref=0.0, tol_abs=2e-3 * M067 * 2.0 * math.pi * R63,
           unit="N m", in_series=False,
           source="randverstoring uitgedempt (L = %.1f / beta)" % (
               L67 * BETA63))],
    note="R = 1 m, t = 10 mm, L = 0,6 m, 120 line3, Fixed boven, moment "
         "M_z = 2 pi R x 100 N m/m op de onderste knoop."))
TESTS.append(Case(
    "PL-68", GROUP, "Cilinder onder eigen gewicht (COQUE_AXIS)",
    "lin_static_3d", build_pl68,
    [Check("R_y boven", lambda r: r.total("reactionforcey", "Boven"),
           ref=W68, tol=1e-6, unit="N", in_series=False,
           source="evenwicht: rho g 2 pi R t L"),
     Check("massa (controle)", lambda r: static_check(r, "M"),
           ref=W68 / G68, tol=1e-6, unit="kg", in_series=False,
           source="rho 2 pi R t L (POST_ELEM MASS_INER, 360 graden)")],
    note="De buis van PL-60 met rho = 7850 kg/m3, Y vast boven, "
         "zwaartekracht -9,81 m/s2 langs Y."))
