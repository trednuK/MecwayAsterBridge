# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Nonlinear static in 2D and axisymmetric (STAPPENPLAN S44a, route A;
Scripts/bridge_plane.py): Mecway Nonlinear Static (L30) or Static 3D (S30)
with plane shell elements in the XY plane and the line '#ASTER-PLANE
C_PLAN|D_PLAN|AXIS' -> STAT_NON_LINE / MECA_STATIQUE on C_PLAN, D_PLAN or
AXIS. Explanation: docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-30  thick cylinder a = 0.1, b = 0.2 m, von Mises elastic-perfectly
       plastic, internal pressure in time steps (0.5 s: c = 0.13 m, 1 s:
       c = 0.16 m by Hill's relation), plane strain (D_PLAN, quarter ring):
       u_b = 2 (1 - nu^2) sigma_y c^2 / (sqrt3 E b) and the elastic-plastic
       boundary within one element of c.
PL-31  the same cylinder axisymmetric (AXIS, ring with both ends held
       axially = plane strain).
PL-32  plate with a hole in plane stress (C_PLAN, the geometry of PL-01,
       n = 16), traction rising in time steps: the nominal stress at first
       yield (first step with plastic strain) = sigma_y / Kt.
PL-33  route A linear: the plate of PL-01-n16 as S30 + '#ASTER-PLANE
       C_PLAN' = the S20 result (the same displacement).
PL-34  thermal stress in L30 route A: the tube of PL-24 (AXIS) = its
       MECA_STATIQUE result.
"""
import math

import tests_vlak_2d as p2d
import tests_vlak_2d_thermisch as p2t
from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
E, NU, SY = 210e9, 0.3, 250.0e6
RA, RB, H = 0.1, 0.2, 0.01
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
PERFECT = ('<plastic type="BilinearIsotropic" yieldstrength="%g Pa" '
           'tangentmodulus="0 Pa" />' % SY)
NR = 16                         # quad8 through the wall


def _switch(m, mod):
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE %s</ccxmodeldefinition>" % mod)


def _fields(m, plastic=True):
    for fv in ("displacement", "stress", "von Mises stress",
               "reaction force") + (("plastic strain",) if plastic else ()):
        m.add('<fieldvariable name="%s" />' % fv)


def _table(tag, points, unit):
    return "".join('<%s time="%g s">%.12g %s</%s>' % (tag, t, v, unit, tag)
                   for t, v in points)


# ------------------------------------------------------------------
# PL-30 / PL-31 thick cylinder, elastic-perfectly plastic (Hill)
# ------------------------------------------------------------------
def p_hill(c):
    """Internal pressure for a plastic zone a..c (Hill 1950, plane strain,
    von Mises with sigma_z the mean of sigma_r and sigma_theta)."""
    return SY / math.sqrt(3.0) * (1.0 - c ** 2 / RB ** 2 +
                                  2.0 * math.log(c / RA))


def u_b(c):
    """Outer wall displacement for a plastic radius c (elastic zone c..b,
    plane strain Lame with the yield pressure at c)."""
    return 2.0 * (1.0 - NU ** 2) * SY * c ** 2 / (math.sqrt(3.0) * E * RB)


C1, C2 = 0.13, 0.16
P1, P2 = p_hill(C1), p_hill(C2)
P_LIMIT = 2.0 / math.sqrt(3.0) * SY * math.log(RB / RA)
TS = {"timeperiod": "1 s", "stepsize": "0.05 s"}
_PRESSURE = _table("normal", [(0.0, 0.0), (0.5, P1), (1.0, P2)], "Pa")


def _ring(u, v):
    r = RA + u * (RB - RA)
    t = v * math.pi / 2
    return (r * math.cos(t), r * math.sin(t), 0.0)


def build_cyl(axis):
    def build():
        m = Model("L30", timesteps=TS)
        m.elset("Cilinder", "Staal")
        if axis:
            q = quadmesh(m, "Cilinder", NR, 1, rect(RA, RB, 0.0, H), order=2)
        else:
            q = quadmesh(m, "Cilinder", NR, 8, _ring, order=2)
        m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />',
              STEEL, PERFECT)
        e = q["edges"]
        m.face_selection("Binnenwand", e["u0"])
        m.add('<surfacepressure selection="Binnenwand">%s</surfacepressure>'
              % _PRESSURE)
        if axis:
            m.face_selection("Onder", e["v0"])
            m.face_selection("Boven", e["v1"])
            for sel in ("Onder", "Boven"):
                m.add('<displacement selection="%s"><value>0 m</value>'
                      '<x>0</x><y>1</y><z>0</z></displacement>' % sel)
        else:
            m.face_selection("SymY0", e["v0"])
            m.face_selection("SymX0", e["v1"])
            m.node_selection("SymX0n", sorted(q["nodes"]["v1"]))
            m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
                  '</symmetry>')
            m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
                  '</symmetry>')
        _switch(m, "AXIS" if axis else "D_PLAN")
        _fields(m)
        return m
    return build


def _plastic_radius(t):
    """Largest radius of a node with equivalent plastic strain > 1e-9 on
    the line y = 0 (AXIS: the bottom edge) at time t."""
    def f(r):
        d = r.step(t)["equivalentplasticstrain"]
        rad = [math.hypot(p[0], p[1]) for i, p in enumerate(r.model.nodes)
               if abs(p[1]) < 1e-12 and d.get(i + 1, 0.0) > 1e-9]
        return max(rad) if rad else RA
    return f


_HEL = (RB - RA) / NR


def _cyl_checks(reaction=None):
    """reaction: tolerance of the reaction check on x = 0 (D_PLAN only;
    the follower pressure of GDEF_LOG acts on the deformed wall)."""
    out = []
    for t, c in ((0.5, C1), (1.0, C2)):
        out += [
            Check("u_b t = %g s (c = %g m)" % (t, c),
                  lambda r, t=t: r.at("displx", (RB, 0.0, 0.0), time=t),
                  ref=u_b(c), tol=0.02, unit="m",
                  source="Hill (1950): 2 (1 - nu^2) sigma_y c^2 / "
                         "(sqrt3 E b)"),
            Check("plastische straal t = %g s" % t, _plastic_radius(t),
                  ref=c, tol_abs=_HEL, unit="m",
                  source="Hill: p = (sigma_y / sqrt3) (1 - c^2/b^2 + "
                         "2 ln(c/a)); binnen een element")]
        if reaction:
            out.append(Check(
                "som R_x op x = 0, t = %g s" % t,
                lambda r, t=t: r.total("reactionforcex", "SymX0n", time=t),
                ref=-p_of(t) * RA * 0.01, tol=reaction, unit="N",
                in_series=False,
                source="evenwicht kwart ring: -p a t (dikte 10 mm)"))
    return out


def p_of(t):
    return P1 if t == 0.5 else P2


# ------------------------------------------------------------------
# PL-32 plate with a hole, first yield (C_PLAN)
# ------------------------------------------------------------------
# Nominal stress at first yield: sigma_y / Kt (Peterson, as PL-01). Code-
# Aster yields first at the integration points next to the hole, where the
# stress is a little below the nodal value: with n = 16 +3.0% (the
# elastic nodal Kt of that mesh is -0.79%), so the case uses n = 32.
N32 = 32
S_YIELD = SY / p2d.KT_PETERSON
TS32 = {"timeperiod": "1 s", "stepsize": "0.02 s"}
# traction from 0.9 to 1.1 x the expected first-yield traction
_T0 = 0.9 * S_YIELD * (1.0 - p2d.BETA)
_T1 = 1.1 * S_YIELD * (1.0 - p2d.BETA)


def build_pl32():
    m = p2d.build_plate(N32)()
    m.analysis = "L30"
    m.timesteps = TS32
    m.mats = []
    m.mat("Staal", '<geometric type="Plate" thickness="1 mm" />', STEEL,
          '<plastic type="BilinearIsotropic" yieldstrength="%g Pa" '
          'tangentmodulus="%g Pa" />' % (SY, 0.01 * E))
    m.items = [it for it in m.items if "<traction" not in it]
    m.add('<traction selection="Trek">%s<y>0 Pa</y><z>0 Pa</z></traction>'
          % _table("x", [(0.0, _T0), (1.0, _T1)], "Pa"))
    _switch(m, "C_PLAN")
    m.add('<fieldvariable name="plastic strain" />')
    return m


def _first_yield(r):
    """Nominal stress (net section) at the first step with plastic
    strain: the mean of that step and the one before."""
    prev = None
    for t in r.times():
        if t <= 0.0:
            continue
        if max(r.step(t)["equivalentplasticstrain"].values()) > 1e-12:
            tt = t if prev is None else 0.5 * (t + prev)
            return (_T0 + (_T1 - _T0) * tt) / (1.0 - p2d.BETA)
        prev = t
    return float("nan")


# ------------------------------------------------------------------
# PL-33 route A linear = route B; PL-34 thermal stress in L30
# ------------------------------------------------------------------
def build_pl33():
    m = p2d.build_plate(16)()
    m.analysis = "S30"
    _switch(m, "C_PLAN")
    return m


def build_pl34():
    m = p2t.build_tube_axis(False)()
    m.analysis = "L30"
    m.timesteps = {"timeperiod": "1 s", "stepsize": "1 s"}
    m.mats = []
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />',
          p2t.STEEL)
    _switch(m, "AXIS")
    return m


TESTS = []
TESTS.append(Case(
    "PL-30", GROUP, "Dikwandige cilinder, ideaal plastisch, vlakke rek "
    "(L30 + #ASTER-PLANE D_PLAN)", "nonlin_static_3d", build_cyl(False),
    _cyl_checks(reaction=0.01),
    note="a = 0,1, b = 0,2 m, sigma_y = 250 MPa, H = 0, kwart ring quad8 "
         "16x8; p = %.4g / %.4g MPa (p_L = %.4g MPa)." % (
             P1 / 1e6, P2 / 1e6, P_LIMIT / 1e6)))
TESTS.append(Case(
    "PL-31", GROUP, "Dikwandige cilinder, ideaal plastisch, axisymmetrisch "
    "(L30 + #ASTER-PLANE AXIS)", "nonlin_static_3d", build_cyl(True),
    _cyl_checks(),
    note="Als PL-30, ring 16x1 met Y vast op beide einden."))
TESTS.append(Case(
    "PL-32", GROUP, "Plaat met gat, eerste vloei (L30 + #ASTER-PLANE C_PLAN)",
    "nonlin_static_3d", build_pl32,
    [Check("nominale spanning bij eerste vloei", _first_yield, ref=S_YIELD,
           tol=0.02, unit="Pa",
           source="sigma_y / Kt_n (Peterson chart 4.1, als PL-01)"),
     Check("som R_x symmetrie x = 0, t = 1 s",
           lambda r: r.total("reactionforcex", "SymXn", time=1.0),
           ref=-_T1 * p2d.WH * p2d.T1, tol=1e-3, unit="N", in_series=False,
           source="evenwicht: traction x WH x t (dikte 1 mm); GDEF_LOG "
                  "2e-4, PETIT exact (KNOWN_BUGS 140)")],
    timeout=3600,
    note="Geometrie PL-01 met n = 32, t = 1 mm, bilineair H = 0,01 E, traction "
         "0,9 .. 1,1 x de verwachte waarde in 50 stappen."))
TESTS.append(Case(
    "PL-33", GROUP, "Plaat met gat, S30 + #ASTER-PLANE C_PLAN = S20",
    "lin_static_3d", build_pl33,
    [Check("u_y(0, r) = PL-01-n16", lambda r: r.at("disply",
                                                    (0.0, p2d.R, 0.0)),
           ref=p2d.MW_PL01["uy"], tol=1e-6, unit="m", in_series=False,
           source="PL-01-n16 (route B, = Mecway S20)"),
     Check("u_x(L/2, 0) = PL-01-n16", lambda r: r.at("displx",
                                                     (p2d.LH, 0.0, 0.0)),
           ref=p2d.MW_PL01["ux"], tol=1e-6, unit="m", in_series=False,
           source="PL-01-n16 (route B, = Mecway S20)")],
    note="Het model van PL-01-n16 met analysetype S30 en de regel "
         "#ASTER-PLANE C_PLAN."))
TESTS.append(Case(
    "PL-34", GROUP, "Dikwandige buis, ln-temperatuur, L30 + #ASTER-PLANE "
    "AXIS", "nonlin_static_3d", build_pl34,
    [Check("u_r binnenwand = PL-24", lambda r: r.at(
        "displx", (RA, 0.0, 0.0), time=1.0), ref=p2t.MW["PL-24"][0],
        tol=1e-6, unit="m", in_series=False,
        source="PL-24 (MECA_STATIQUE, = Mecway SA0)"),
     Check("u_r buitenwand = PL-24", lambda r: r.at(
         "displx", (RB, 0.0, 0.0), time=1.0), ref=p2t.MW["PL-24"][1],
         tol=1e-6, unit="m", in_series=False,
         source="PL-24 (MECA_STATIQUE, = Mecway SA0)")],
    settings={"deformation": "PETIT"},
    note="Het model van PL-24 als L30 (een stap van 1 s) met "
         "#ASTER-PLANE AXIS en deformation PETIT (met de standaard "
         "GROT_GDEP -> GREEN_LAGRANGE 1,5e-4 hoger: geometrisch "
         "niet-lineair bij een rek van 1,2e-3)."))


# ------------------------------------------------------------------
# PL-35 Code-Aster test case ssnp159b (AXIS, VMIS_ISOT_LINE, GDEF_LOG)
# ------------------------------------------------------------------
# One QUAD4 r = 0 .. 1 m, y = 0 .. 1 m (mesh hsna106a.mail in mm),
# E = 200000 MPa, nu = 0.3, ECRO_LINE SY = 1000 MPa, D_SIGM_EPSI = 2000 MPa,
# DY = 0 at the bottom corners, the top edge pulled to DY = 290 mm at t = 2
# in two steps. Mecway's tangent modulus is the plastic modulus H
# (bridge_from_liml._parse_bilinear): H = E ET / (E - ET). TEST_RESU at t = 2
# (VALE_CALC, Code-Aster 17.4): SIYY = 1494.79546 MPa (PRECISION 1%), V1 =
# 0.247145796 (1.5%); the fields are uniform, so the node values are the
# Gauss values.
E159, ET159, SY159 = 200000e6, 2000e6, 1000e6
H159 = E159 * ET159 / (E159 - ET159)


def build_pl35():
    m = Model("L30", timesteps={"timeperiod": "2 s", "stepsize": "1 s"})
    m.elset("Blok", "Staal")
    q = quadmesh(m, "Blok", 1, 1, rect(0.0, 1.0, 0.0, 1.0), order=1)
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />',
          '<mechanical type="Isotropic" youngsmodulus="200000 MPa" '
          'poissonratio="0.3" />',
          '<plastic type="BilinearIsotropic" yieldstrength="%g Pa" '
          'tangentmodulus="%.12g Pa" />' % (SY159, H159))
    e = q["edges"]
    m.face_selection("Onder", e["v0"])
    m.face_selection("Boven", e["v1"])
    m.face_selection("As", e["u0"])
    m.add('<displacement selection="Onder"><value>0 m</value><x>0</x>'
          '<y>1</y><z>0</z></displacement>')
    # Mecway manual v34 par. 7.2: nodes on the axis held in X
    m.add('<displacement selection="As"><value>0 m</value><x>1</x>'
          '<y>0</y><z>0</z></displacement>')
    m.add('<displacement selection="Boven">%s<x>0</x><y>1</y><z>0</z>'
          '</displacement>' % _table("value", [(0.0, 0.0), (2.0, 0.29)],
                                     "m"))
    _switch(m, "AXIS")
    _fields(m)
    return m


TESTS.append(Case(
    "PL-35", GROUP, "ssnp159b: trekproef axisymmetrisch, grote rek "
    "(L30 + #ASTER-PLANE AXIS)", "nonlin_static_3d", build_pl35,
    [Check("SIYY t = 2 s (ssnp159b)", lambda r: r.at(
        "stressyy", (1.0, 1.0, 0.0), time=2.0), ref=1494.79546e6, tol=0.01,
        unit="Pa", source="ssnp159b TEST_RESU SIEF_ELGA SIYY (VALE_CALC, "
                          "PRECISION 1%)"),
     Check("V1 t = 2 s (ssnp159b)", lambda r: r.at(
         "equivalentplasticstrain", (1.0, 1.0, 0.0), time=2.0),
         ref=0.247145796, tol=0.015, unit="-",
         source="ssnp159b TEST_RESU VARI_ELGA V1 (VALE_CALC, PRECISION "
                "1.5%)")],
    note="Een quad4 1 x 1 m, de belasting van ssnp159b in SI; deformation "
         "GROT_GDEP (standaard) -> GDEF_LOG zoals de test."))

# PL-30p: PL-30 with small displacements (deformation PETIT, pressure not
# a follower load); the default (PL-30) is GDEF_LOG with a follower pressure
TESTS.append(Case(
    "PL-30p", GROUP, "Dikwandige cilinder, ideaal plastisch, vlakke rek, "
    "PETIT", "nonlin_static_3d", build_cyl(False), _cyl_checks(reaction=1e-6),
    settings={"deformation": "PETIT"},
    note="Als PL-30 met deformation = PETIT."))


# ------------------------------------------------------------------
# PL-36 plate in L30 with a Temperature as a time table (C_PLAN)
# ------------------------------------------------------------------
# STAPPENPLAN S44c Done-when "plate in L30 with a temperature = Mecway":
# the free plate of PL-21 as L30 (CCX in Mecway) with #ASTER-PLANE C_PLAN;
# the table 0 / 1 / 2 s: 293 / 393 / 493 K follows the steps (STAT_NON_LINE,
# EVOL_THER; MECA_STATIQUE drops a table).
def build_pl36():
    m = p2t.build_plate()()
    m.analysis = "L30"
    m.solver = "ccx"
    m.timesteps = {"timeperiod": "2 s", "stepsize": "1 s"}
    m.items = [it for it in m.items if "<temperature2" not in it]
    m.add('<temperature2 selection="Alles">%s</temperature2>' % _table(
        "value", [(0.0, p2t.TREF), (1.0, p2t.TREF + 100.0),
                  (2.0, p2t.TREF + 200.0)], "K"))
    _switch(m, "C_PLAN")
    return m


TESTS.append(Case(
    "PL-36", GROUP, "Vrije plaat, temperatuur als tijdtabel (L30 + "
    "#ASTER-PLANE C_PLAN)", "nonlin_static_3d", build_pl36,
    [Check("u_x rechts t = %g s" % t, lambda r, t=t: r.at(
        "displx", (p2t.LX, p2t.LY, 0.0), time=t),
        ref=p2t.ALPHA * 100.0 * t * p2t.LX, tol=1e-6, unit="m",
        source="vrije uitzetting: alpha dT(t) x") for t in (1.0, 2.0)],
    settings={"deformation": "PETIT"},
    note="De plaat van PL-21 als L30, temperature2 293 / 393 / 493 K op "
         "0 / 1 / 2 s, deformation PETIT."))
