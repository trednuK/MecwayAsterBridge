# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
2D analyses (STAPPENPLAN S16a; Scripts/bridge_plane.py): Mecway Static 2D
(S20, plane stress -> C_PLAN, plane strain -> D_PLAN) and Static
Axisymmetric (SA0 -> AXIS), linear static (MECA_STATIQUE). Explanation:
docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-01-n*  plate with a hole in tension, plane stress (C_PLAN), quad8,
          quarter model: the 2D counterpart of AD-01 (same geometry, Kt
          against Peterson, the same tolerances), plus the reaction sum
          (thickness factor) and Mecway's own solution (headless).
PL-02     the same plate in plane strain (D_PLAN): Kt as in plane stress
          (independent of nu), sigma_zz = nu (sxx + syy) at the hole.
PL-03-n*  thick-walled cylinder under internal pressure, plane strain
          (D_PLAN), quarter ring quad8: the 2D counterpart of LS-04 (Lame,
          the same tolerances).
PL-04-n*  the same cylinder axisymmetric (AXIS): a ring of axial length
          LZ with Y fixed on both ends (plane strain), Lame: u_r, sigma_r,
          hoop stress (Mecway: stresszz), sigma_z; axial reaction over 360
          degrees.
PL-05     load types in plane stress (strip, t = 10 mm): nodal force,
          force on an edge, traction, gravity; sum of the reactions exact.
PL-06     load types axisymmetric (ring): nodal force, force on an edge,
          gravity along Y, centrifugal about Y; sum of the reactions exact
          (360 degrees).

Mecway's own solution (Mecway 34, mw_solve.py, 28 Oct 2026) of the same
models is in the checks "= Mecway" (tolerance 1e-6): displacements and
reactions are identical, nodal stresses only where they are uniform
(Mecway's stress recovery differs, KNOWN_BUGS 3).
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect, static_check

GROUP = "2D en axisymmetrisch"
E, NU = 210e9, 0.3
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7800 kg/m&#179;" />'
RHO = 7800.0


def _tol(tol_f, h, h_f, p):
    """Tolerance of a mesh in a series (as tests_lineair_statisch)."""
    return max(tol_f, min(0.5, tol_f * (float(h) / h_f) ** p))


# ------------------------------------------------------------------
# PL-01 / PL-02 Plate with a hole (2D counterpart of AD-01)
# ------------------------------------------------------------------
R = 0.010                   # m, hole radius
WH = 0.050                  # m, half width (W = 0.1)
LH = 0.150                  # m, half length (L = 3 W)
T1 = 0.001                  # m, thickness (plane stress)
SIG = 100.0e6               # Pa, traction on the end edge
BETA = 2 * R / (2 * WH)
SIG_NOM = SIG / (1.0 - BETA)
KT_PETERSON = (2.0 + 0.284 * (1 - BETA) - 0.600 * (1 - BETA) ** 2 +
               1.32 * (1 - BETA) ** 3)


def _blocks():
    """Ring around the hole (u radial, v angle): block A 0..45 degrees ->
    edge x = WH, block B 45..90 -> edge y = WH (as tests_adaptief)."""
    def block_a(u, v):
        t = v * math.pi / 4
        p0 = (R * math.cos(t), R * math.sin(t))
        p1 = (WH, WH * v)
        return (p0[0] + u * (p1[0] - p0[0]), p0[1] + u * (p1[1] - p0[1]),
                0.0)

    def block_b(u, v):
        t = math.pi / 4 + v * math.pi / 4
        p0 = (R * math.cos(t), R * math.sin(t))
        p1 = (WH * (1 - v), WH)
        return (p0[0] + u * (p1[0] - p0[0]), p0[1] + u * (p1[1] - p0[1]),
                0.0)
    return block_a, block_b


def build_plate(n, strain=False):
    def build():
        m = Model("S20")
        m.elset("Plaat", "Staal")
        block_a, block_b = _blocks()
        a = quadmesh(m, "Plaat", 2 * n, 2 * n, block_a, order=2)
        b = quadmesh(m, "Plaat", 2 * n, 2 * n, block_b, order=2)
        c = quadmesh(m, "Plaat", 2 * n, 2 * n, rect(WH, LH, 0, WH), order=2)
        m.mat("Staal", '<geometric type="Plate" thickness="%g mm"%s />' % (
            T1 * 1000, ' planestrain="1"' if strain else ""), STEEL)
        m.face_selection("SymX", b["edges"]["v1"])
        m.face_selection("SymY", a["edges"]["v0"] + c["edges"]["v0"])
        m.face_selection("Trek", c["edges"]["u1"])
        m.node_selection("SymXn", sorted(b["nodes"]["v1"]))
        m.add('<symmetry selection="SymX"><x>1</x><y>0</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymY"><x>0</x><y>1</y><z>0</z>'
              '</symmetry>')
        m.add('<traction selection="Trek"><x>%g Pa</x><y>0 Pa</y>'
              '<z>0 Pa</z></traction>' % SIG)
        _fields(m)
        return m
    return build


def kt(r):
    """Kt_n from sigma_xx at the node (0, r)."""
    return r.at("stressxx", (0.0, R, 0.0)) / SIG_NOM


# Mecway 34's own solution (headless) of PL-01-n16 / PL-02: displacement
# u_y of the node (0, r) and u_x of the node (LH, 0)
MW_PL01 = {"uy": -5.39372794019e-06, "ux": 7.37744876795e-05}
MW_PL02 = {"uy": -4.90829719272e-06, "ux": 6.71347692892e-05}
# PL-04-n8: u_r of the node (a, 0); PL-05: u_x of (L, H/2); PL-06: u_r of
# (b, h) and u_y of (a, h)
MW_PL04 = {"ur": 9.07932730082e-05}

_UNIFORM = ((1, 0.30), (2, 0.16), (4, 0.08), (8, 0.03), (16, 0.02))

TESTS = []
for _n, _t in _UNIFORM:
    _checks = [
        Check("Kt_n", kt, ref=KT_PETERSON, tol=_t,
              source="Peterson chart 4.1 (Pilkey & Pilkey 2008), as AD-01"),
        Check("som R_x symmetrie x=0",
              lambda r: r.total("reactionforcex", "SymXn"),
              ref=-SIG * WH * T1, tol=1e-6, unit="N", in_series=False,
              source="evenwicht: sigma x WH x t (dikte t = 1 mm)")]
    if _n == 16 and MW_PL01["uy"] is not None:
        _checks += [
            Check("u_y(0, r) = Mecway", lambda r: r.at("disply",
                                                        (0.0, R, 0.0)),
                  ref=MW_PL01["uy"], tol=1e-6, unit="m", in_series=False,
                  source="Mecway 34 headless, eigen S20-oplossing"),
            Check("u_x(L/2, 0) = Mecway", lambda r: r.at("displx",
                                                          (LH, 0.0, 0.0)),
                  ref=MW_PL01["ux"], tol=1e-6, unit="m", in_series=False,
                  source="Mecway 34 headless, eigen S20-oplossing")]
    TESTS.append(Case(
        "PL-01-n%d" % _n, GROUP,
        "Plaat met gat, vlakke spanning (C_PLAN), quad8 n = %d" % _n,
        "lin_static_3d", build_plate(_n), _checks,
        series="PL-01 quad8", h=R * math.pi / 4 / (2 * _n),
        note="Kwartmodel, symmetry x = 0 en y = 0, traction 100 MPa; "
             "Mecway S20 met dikte 1 mm."))


# ------------------------------------------------------------------
# PL-03 / PL-04 Thick-walled cylinder (2D counterpart of LS-04, Lame)
# ------------------------------------------------------------------
RA, RB, P3 = 0.1, 0.2, 100.0e6
T3 = 0.01                   # m, thickness (S20) / axial length (SA0)
A3 = P3 * RA ** 2 / (RB ** 2 - RA ** 2)
B3 = P3 * RA ** 2 * RB ** 2 / (RB ** 2 - RA ** 2)
SIGT3 = A3 + B3 / RA ** 2                     # hoop stress, inner wall
SIGZ3 = 2 * NU * A3                           # plane strain
UR3 = (1 + NU) / E * ((1 - 2 * NU) * A3 * RA + B3 / RA)


def _ring(u, v):
    r = RA + u * (RB - RA)
    t = v * math.pi / 2
    return (r * math.cos(t), r * math.sin(t), 0.0)


def build_ring_plane(nr, nt):
    """Quarter ring in plane strain (S20, D_PLAN), symmetry x = 0, y = 0."""
    def build():
        m = Model("S20")
        m.elset("Cilinder", "Staal")
        q = quadmesh(m, "Cilinder", nr, nt, _ring, order=2)
        m.mat("Staal", '<geometric type="Plate" thickness="%g mm" '
              'planestrain="1" />' % (T3 * 1000), STEEL)
        e = q["edges"]
        m.face_selection("Binnenwand", e["u0"])
        m.face_selection("SymY0", e["v0"])
        m.face_selection("SymX0", e["v1"])
        m.add('<surfacepressure selection="Binnenwand"><normal>%g Pa'
              '</normal></surfacepressure>' % P3)
        m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
              '</symmetry>')
        _fields(m)
        return m
    return build


def build_ring_axis(nr, extra=()):
    """Ring r = RA..RB, y = 0..T3 (SA0, AXIS), Y fixed on both ends (plane
    strain), pressure on the inner wall. extra: more material lines."""
    def build():
        m = Model("SA0")
        m.elset("Cilinder", "Staal")
        q = quadmesh(m, "Cilinder", nr, 1, rect(RA, RB, 0.0, T3), order=2)
        m.mat("Staal", STEEL, *extra)
        e = q["edges"]
        m.face_selection("Binnenwand", e["u0"])
        m.face_selection("Onder", e["v0"])
        m.face_selection("Boven", e["v1"])
        m.node_selection("Bovenn", sorted(q["nodes"]["v1"]))
        m.add('<surfacepressure selection="Binnenwand"><normal>%g Pa'
              '</normal></surfacepressure>' % P3)
        for sel in ("Onder", "Boven"):
            m.add('<displacement selection="%s"><value>0 m</value><x>0</x>'
                  '<y>1</y><z>0</z></displacement>' % sel)
        _fields(m)
        return m
    return build


def _fields(m):
    for fv in ("displacement", "stress", "von Mises stress",
               "reaction force"):
        m.add('<fieldvariable name="%s" />' % fv)


_NS = (1, 2, 4, 8)
_HF = (RB - RA) / _NS[-1]
for _n in _NS:
    _h = (RB - RA) / _n
    _pin = (RA, 0.0, 0.0)
    TESTS.append(Case(
        "PL-03-n%d" % _n, GROUP,
        "Dikwandige cilinder, vlakke rek (D_PLAN), quad8 %dx%d" % (_n, 2 * _n),
        "lin_static_3d", build_ring_plane(_n, 2 * _n),
        [Check("u_r binnenwand", lambda r: r.at("displx", _pin), ref=UR3,
               tol=_tol(0.001, _h, _HF, 3), unit="m",
               source="Lame, vlakke rek (Timoshenko & Goodier par. 28)"),
         Check("sigma_theta binnenwand", lambda r: r.at("stressyy", _pin),
               ref=SIGT3, tol=_tol(0.005, _h, _HF, 1), unit="Pa",
               source="p (b^2+a^2)/(b^2-a^2) (Lame)"),
         Check("sigma_zz binnenwand", lambda r: r.at("stresszz", _pin),
               ref=SIGZ3, tol=_tol(0.01, _h, _HF, 2), unit="Pa",
               source="2 nu p a^2/(b^2-a^2) (vlakke rek)")],
        series="PL-03 quad8", h=_h,
        note="2D-tegenhanger van LS-04: kwart ring, symmetry x = 0 en "
             "y = 0, Mecway S20 plane strain (dikte 10 mm)."))
    TESTS.append(Case(
        "PL-04-n%d" % _n, GROUP,
        "Dikwandige cilinder, axisymmetrisch (AXIS), quad8 %dx1" % _n,
        "lin_static_3d", build_ring_axis(_n),
        [Check("u_r binnenwand", lambda r: r.at("displx", _pin), ref=UR3,
               tol=_tol(0.001, _h, _HF, 3), unit="m",
               source="Lame, vlakke rek (Timoshenko & Goodier par. 28)"),
         Check("sigma_theta binnenwand (stresszz)",
               lambda r: r.at("stresszz", _pin),
               ref=SIGT3, tol=_tol(0.006, _h, _HF, 1.5), unit="Pa",
               source="p (b^2+a^2)/(b^2-a^2) (Lame)"),
         Check("sigma_r binnenwand (stressxx)",
               lambda r: r.at("stressxx", _pin),
               ref=-P3, tol=_tol(0.012, _h, _HF, 2), unit="Pa",
               source="sigma_r(a) = -p (Lame)"),
         Check("sigma_z binnenwand (stressyy)",
               lambda r: r.at("stressyy", _pin),
               ref=SIGZ3, tol=_tol(0.01, _h, _HF, 2), unit="Pa",
               source="2 nu p a^2/(b^2-a^2) (vlakke rek)"),
         Check("som R_y boven (360 graden)",
               lambda r: r.total("reactionforcey", "Bovenn"),
               ref=SIGZ3 * math.pi * (RB ** 2 - RA ** 2), tol=1e-6,
               unit="N", in_series=False,
               source="sigma_z x pi (b^2 - a^2), Lame vlakke rek")] + (
            [Check("u_r binnenwand = Mecway",
                   lambda r: r.at("displx", _pin), ref=MW_PL04["ur"],
                   tol=1e-6, unit="m", in_series=False,
                   source="Mecway 34 headless, eigen SA0-oplossing")]
            if _n == _NS[-1] else []),
        series="PL-04 quad8", h=_h,
        note="Ring r = 0,1..0,2 m, lengte 10 mm, Y vast op beide einden "
             "(vlakke rek), Mecway SA0."))


# ------------------------------------------------------------------
# PL-02 Plate with a hole in plane strain (D_PLAN)
# ------------------------------------------------------------------
def _szz_ratio(r):
    """sigma_zz / (nu (sigma_xx + sigma_yy)) at the node (0, r)."""
    p = (0.0, R, 0.0)
    return r.at("stresszz", p) / (NU * (r.at("stressxx", p) +
                                        r.at("stressyy", p)))


_pl02 = [Check("Kt_n", kt, ref=KT_PETERSON, tol=0.02,
               source="Peterson chart 4.1; Kt hangt niet af van nu"),
         Check("sigma_zz / nu (sxx + syy) bij het gat", _szz_ratio, ref=1.0,
               tol=1e-6, in_series=False, source="vlakke rek: eps_zz = 0"),
         Check("som R_x symmetrie x=0",
               lambda r: r.total("reactionforcex", "SymXn"),
               ref=-SIG * WH * T1, tol=1e-6, unit="N", in_series=False,
               source="evenwicht: sigma x WH x t (dikte t = 1 mm)"),
         Check("u_y(0, r) = Mecway", lambda r: r.at("disply", (0.0, R, 0.0)),
               ref=MW_PL02["uy"], tol=1e-6, unit="m", in_series=False,
               source="Mecway 34 headless, eigen S20-oplossing (plane "
                      "strain)"),
         Check("u_x(L/2, 0) = Mecway", lambda r: r.at("displx",
                                                      (LH, 0.0, 0.0)),
               ref=MW_PL02["ux"], tol=1e-6, unit="m", in_series=False,
               source="Mecway 34 headless, eigen S20-oplossing (plane "
                      "strain)")]
TESTS.append(Case(
    "PL-02", GROUP, "Plaat met gat, vlakke rek (D_PLAN), quad8 n = 16",
    "lin_static_3d", build_plate(16, strain=True), _pl02,
    note="Als PL-01-n16 met planestrain=\"1\" in het materiaal."))


# ------------------------------------------------------------------
# PL-05 Load types in plane stress (strip, t = 10 mm)
# ------------------------------------------------------------------
L5, H5, T5 = 0.1, 0.02, 0.01
FN5, FF5, TR5, G5 = 100.0, 200.0, 1.0e6, 9.81
SUM5 = FN5 + FF5 + TR5 * H5 * T5 + RHO * G5 * L5 * H5 * T5
SIG5 = (FN5 + FF5 + TR5 * H5 * T5) / (H5 * T5) + RHO * G5 * L5 / 2
ACC = u"m/s²"


def build_pl05():
    m = Model("S20")
    m.elset("Strip", "Staal")
    q = quadmesh(m, "Strip", 8, 2, rect(0.0, L5, 0.0, H5), order=2)
    m.mat("Staal", '<geometric type="Plate" thickness="%g mm" />' % (
        T5 * 1000), STEEL, DENS)
    e, nd = q["edges"], q["nodes"]
    m.face_selection("Links", e["u0"])
    m.face_selection("Rechts", e["u1"])
    m.node_selection("Linksn", sorted(nd["u0"]))
    m.node_selection("Rechtsn", sorted(nd["u1"]))
    m.node_selection("Oorsprong", [m.node(0.0, 0.0, 0.0)])
    m.add('<displacement selection="Links"><value>0 m</value><x>1</x>'
          '<y>0</y><z>0</z></displacement>')
    m.add('<displacement selection="Oorsprong"><value>0 m</value><x>0</x>'
          '<y>1</y><z>0</z></displacement>')
    m.add('<force selection="Rechtsn"><x>%g N</x><y>0 N</y><z>0 N</z>'
          '</force>' % FN5)
    m.add('<force selection="Rechts"><x>%g N</x><y>0 N</y><z>0 N</z>'
          '</force>' % FF5)
    m.add('<traction selection="Rechts"><x>%g Pa</x><y>0 Pa</y><z>0 Pa</z>'
          '</traction>' % TR5)
    m.add(u'<gravity><x>%g %s</x><y>0 %s</y><z>0 %s</z></gravity>' % (
        G5, ACC, ACC, ACC))
    _fields(m)
    return m


MW_PL05 = {"ux": 1.1881829099e-06}
_P5 = (L5 / 2, H5 / 2, 0.0)
_pl05 = [Check("som R_x links", lambda r: r.total("reactionforcex", "Linksn"),
               ref=-SUM5, tol=1e-6, unit="N", in_series=False,
               source="evenwicht: knoopkracht + kracht op rand + traction "
                      "x H t + rho g L H t (dikte t = 10 mm)"),
         Check("principal1 (L/2, H/2)", lambda r: r.at("principal1", _P5),
               ref=SIG5, tol=0.005, unit="Pa",
               source="F / (H t) + rho g L/2 (staaf onder trek)"),
         Check("massa (BRIDGE_STATCHECK)", lambda r: static_check(r, "M"),
               ref=RHO * L5 * H5 * T5, tol=1e-6, unit="kg", in_series=False,
               source="rho L H t"),
         Check("tresca - (principal1 - principal3)",
               lambda r: r.at("tresca", _P5) - (r.at("principal1", _P5) -
                                                r.at("principal3", _P5)),
               ref=0.0, tol_abs=1e-3, unit="Pa", in_series=False,
               source="definitie (Mecway, S34)")]
if MW_PL05["ux"] is not None:
    _pl05.append(Check("u_x(L, H/2) = Mecway",
                       lambda r: r.at("displx", (L5, H5 / 2, 0.0)),
                       ref=MW_PL05["ux"], tol=1e-6, unit="m",
                       in_series=False,
                       source="Mecway 34 headless, eigen S20-oplossing"))
TESTS.append(Case(
    "PL-05", GROUP, "Belastingtypen vlakke spanning (C_PLAN): knoopkracht, "
    "kracht op rand, traction, zwaartekracht", "lin_static_3d", build_pl05,
    _pl05, settings={"fields": ["displacements", "stresses", "vonmises",
                                "reactions", "principal_stresses"]},
    note="Strook 100 x 20 mm, dikte 10 mm, quad8 8x2; alle lasten in +x."))


# ------------------------------------------------------------------
# PL-06 Load types axisymmetric (ring)
# ------------------------------------------------------------------
H6 = 0.02
FN6, FF6, TR6, G6, W6 = 1000.0, 2000.0, 1.0e6, 9.81, 100.0
SUM6 = FN6 + FF6 + RHO * G6 * math.pi * (RB ** 2 - RA ** 2) * H6


def build_pl06():
    m = Model("SA0")
    m.elset("Ring", "Staal")
    q = quadmesh(m, "Ring", 4, 2, rect(RA, RB, 0.0, H6), order=2)
    m.mat("Staal", STEEL, DENS)
    e, nd = q["edges"], q["nodes"]
    m.face_selection("Onder", e["v0"])
    m.face_selection("Boven", e["v1"])
    m.face_selection("Buiten", e["u1"])
    m.node_selection("Ondern", sorted(nd["v0"]))
    m.node_selection("Bovenn", sorted(nd["v1"]))
    m.add('<displacement selection="Onder"><value>0 m</value><x>0</x>'
          '<y>1</y><z>0</z></displacement>')
    m.add('<force selection="Bovenn"><x>0 N</x><y>%g N</y><z>0 N</z>'
          '</force>' % FN6)
    m.add('<force selection="Boven"><x>0 N</x><y>%g N</y><z>0 N</z>'
          '</force>' % FF6)
    m.add('<traction selection="Buiten"><x>%g Pa</x><y>0 Pa</y><z>0 Pa</z>'
          '</traction>' % TR6)
    m.add(u'<gravity><x>0 %s</x><y>%g %s</y><z>0 %s</z></gravity>' % (
        ACC, G6, ACC, ACC))
    m.add('<centrifugal><x>0 rad/s</x><y>%g rad/s</y><z>0 rad/s</z>'
          '</centrifugal>' % W6)
    _fields(m)
    return m


MW_PL06 = {"ur": 2.42109201279e-06, "uy": -1.49641179426e-07}
_pl06 = [Check("som R_y onder (360 graden)",
               lambda r: r.total("reactionforcey", "Ondern"),
               ref=-SUM6, tol=1e-6, unit="N", in_series=False,
               source="evenwicht: knoopkracht + kracht op rand + rho g "
                      "pi (b^2 - a^2) h"),
         Check("massa (BRIDGE_STATCHECK)", lambda r: static_check(r, "M"),
               ref=RHO * math.pi * (RB ** 2 - RA ** 2) * H6, tol=1e-6,
               unit="kg", in_series=False, source="rho pi (b^2 - a^2) h")]
if MW_PL06["ur"] is not None:
    _pl06 += [Check("u_r(b, h) = Mecway", lambda r: r.at("displx",
                                                         (RB, H6, 0.0)),
                    ref=MW_PL06["ur"], tol=1e-6, unit="m", in_series=False,
                    source="Mecway 34 headless, eigen SA0-oplossing"),
              Check("u_y(a, h) = Mecway", lambda r: r.at("disply",
                                                         (RA, H6, 0.0)),
                    ref=MW_PL06["uy"], tol=1e-6, unit="m", in_series=False,
                    source="Mecway 34 headless, eigen SA0-oplossing")]
TESTS.append(Case(
    "PL-06", GROUP, "Belastingtypen axisymmetrisch (AXIS): knoopkracht, "
    "kracht op rand, traction, zwaartekracht, centrifugaal", "lin_static_3d",
    build_pl06, _pl06,
    note="Ring r = 0,1..0,2 m, hoogte 20 mm, quad8 4x2; Y vast onder."))


# ==================================================================
# S16b: Dynamic Response 2D (D20) and Axisymmetric (DA0) -> dyna_impl_3d
# with schema NEWMARK and deformation PETIT (Mecway's linear Newmark, as
# D30 in MD-07); one calculation step per Mecway step, also with
# keepeverynthtimestep > 1 (PL-11, PL-12; before the fix,
# substeps_per_output had to equal n).
# ==================================================================
DYN = {"schema": "NEWMARK", "deformation": "PETIT", "substeps_per_output": 1}
# Mecway 34's own D20/DA0 solution (headless) at a few output times:
# {case: (variable, point, [(t, value)])}
MW_DYN = {
    "PL-10": ("displx", (1.0, 0.0, 0.0), [
        (0.000319923, 7.90231184855e-05), (0.000643701, 3.13634042654e-05),
        (0.000963624, 4.74623117396e-05), (0.001283547, 6.39566817617e-05),
        (0.001607325, 1.69444673304e-05), (0.001927248, 9.26726594906e-05)]),
    "PL-11": ("displx", (0.1, 0.0, 0.0), [
        (5e-05, 5.60926320036e-05), (0.0001, 8.06380925274e-05),
        (0.00015, 8.82500459927e-05), (0.0002, 9.01397571642e-05),
        (0.00025, 9.06283357198e-05), (0.0003, 9.07481008291e-05)]),
    "PL-12": ("disply", (0.1, 0.005, 0.0), [
        (0.0007, -0.000151446644005), (0.0013, -0.000209043106673),
        (0.002, -0.000191118075325), (0.0027, -0.000173853406235),
        (0.0033, -0.000208873305134), (0.004, -0.000160622543659)]),
}


def _mw_hist_dev(cid):
    """Largest |bridge - Mecway| over the stored times, relative to the
    largest |Mecway| value."""
    var, pt, ref = MW_DYN[cid]

    def value(r):
        h = dict((round(t, 9), v) for t, v in r.history(var, pt))
        scale = max(abs(v) for _t, v in ref)
        return max(abs(h[round(t, 9)] - v) for t, v in ref) / scale
    return value


def _period_mean(var, pt, level):
    """(period, time mean over whole periods) of a history around level."""
    import tests_dynamisch as td

    def get(r):
        h = r.history(var, pt)
        cr = td.crossings(h, level)
        per = td.period(h, level)
        t0, t1 = cr[0], cr[0] + per * int((cr[-1] - cr[0]) / per)
        pts = [(t, v) for t, v in h if t0 <= t <= t1]
        mean = sum(0.5 * (a[1] + b[1]) * (b[0] - a[0])
                   for a, b in zip(pts, pts[1:])) / (pts[-1][0] - pts[0][0])
        return per, mean
    return get


# PL-10 Longitudinal wave in a strip (plane stress, nu = 0): a fixed-free
# bar under a step traction; period 4L/c, mean = static elongation
L10, H10, T10, P10 = 1.0, 0.05, 0.01, 10.0e6
C10 = math.sqrt(E / RHO)
PER10 = 4.0 * L10 / C10
U10 = P10 * L10 / E
DT10 = PER10 / 200.0
STEEL0 = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="0" />')


def build_pl10():
    m = Model("D20", timesteps={"timeperiod": "%r s" % (2.5 * PER10),
                                "stepsize": "%r s" % DT10})
    m.elset("Strook", "Staal")
    q = quadmesh(m, "Strook", 40, 1, rect(0.0, L10, 0.0, H10), order=2)
    m.mat("Staal", '<geometric type="Plate" thickness="%g mm" />' % (
        T10 * 1000), STEEL0, DENS)
    e = q["edges"]
    m.face_selection("Links", e["u0"])
    m.face_selection("Rechts", e["u1"])
    m.face_selection("Onder", e["v0"])
    m.add('<displacement selection="Links"><value>0 m</value><x>1</x>'
          '<y>0</y><z>0</z></displacement>')
    m.add('<displacement selection="Onder"><value>0 m</value><x>0</x>'
          '<y>1</y><z>0</z></displacement>')
    m.add('<traction selection="Rechts"><x>%g Pa</x><y>0 Pa</y><z>0 Pa</z>'
          '</traction>' % P10)
    for fv in ("displacement", "velocity", "stress"):
        m.add('<fieldvariable name="%s" />' % fv)
    return m


_P10 = (L10, 0.0, 0.0)
_pm10 = _period_mean("displx", _P10, U10)
_pl10 = [Check("periode tip", lambda r: _pm10(r)[0], ref=PER10, tol=0.01,
               unit="s", source="4 L / c, c = sqrt(E / rho) (staafgolf, "
               "nu = 0)"),
         Check("gemiddelde u_x tip", lambda r: _pm10(r)[1], ref=U10,
               tol=0.01, unit="m", source="statische rek P L / E")]
TESTS.append(Case(
    "PL-10", GROUP, "Staafgolf in een strook, vlakke spanning (D20), "
    "staplast", "dyna_impl_3d", build_pl10, _pl10, settings=DYN,
    timeout=900, note="Strook 1 m x 50 mm, dikte 10 mm, nu = 0, quad8 40x1, "
    "traction 10 MPa vanaf t = 0, Newmark stap T/200."))


# PL-11 Thick-walled ring (DA0) under a step pressure with Rayleigh
# damping: the response settles to the static Lame solution of PL-04
A11 = 8.0e4        # rad/s, mass proportional damping (alpha)
DT11 = 1.0e-6


def build_pl11():
    m = build_ring_axis(4, (DENS,))()
    m.analysis = "DA0"
    m.timesteps = {"timeperiod": "0.0003 s", "stepsize": "%r s" % DT11,
                   "keepeverynthtimestep": "10"}
    m.add('<rayleighdamping selection=""><alpha>%r rad/s</alpha>'
          '<beta>0 s</beta></rayleighdamping>' % A11)
    m.add('<fieldvariable name="velocity" />')
    return m


_pl11 = [Check("u_r binnenwand na uitdempen", lambda r: r.at(
    "displx", (RA, 0.0, 0.0)), ref=UR3, tol=0.002, unit="m",
    source="Lame, vlakke rek (statische eindwaarde; PL-04-n4 statisch "
    "-0,006%)")]
TESTS.append(Case(
    "PL-11", GROUP, "Dikwandige ring axisymmetrisch (DA0), stapdruk met "
    "Rayleigh-demping", "dyna_impl_3d", build_pl11, _pl11,
    settings=DYN, timeout=900,
    note="Model PL-04-n4 met dichtheid, alpha = 8e4 rad/s, Newmark stap "
    "1e-6 s, uitvoer elke 10e stap."))


# PL-12 Cantilever (D20, plane stress) with a force as a time table
def build_pl12():
    m = Model("D20", timesteps={"timeperiod": "0.004 s",
                                "stepsize": "0.00002 s",
                                "keepeverynthtimestep": "5"})
    m.elset("Balk", "Staal")
    q = quadmesh(m, "Balk", 20, 2, rect(0.0, 0.1, 0.0, 0.01), order=2)
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />', STEEL,
          DENS)
    m.face_selection("Links", q["edges"]["u0"])
    m.node_selection("Rechts", sorted(q["nodes"]["u1"]))
    m.add('<fixed selection="Links" />')
    m.add('<force selection="Rechts"><x>0 N</x>'
          '<y time="0 s">0 N</y><y time="0.001 s">-100 N</y>'
          '<y time="0.004 s">-100 N</y><z>0 N</z></force>')
    for fv in ("displacement", "velocity", "stress"):
        m.add('<fieldvariable name="%s" />' % fv)
    return m


TESTS.append(Case(
    "PL-12", GROUP, "Console vlakke spanning (D20), kracht als tijdtabel",
    "dyna_impl_3d", build_pl12, [], settings=DYN,
    timeout=900, note="Console 100 x 10 mm, dikte 10 mm, quad8 20x2; "
    "-100 N op het eindvlak, oplopend tot 1 ms."))

for _c in TESTS:
    if _c.id in MW_DYN:
        _c.checks.append(Check(
            "verloop = Mecway", _mw_hist_dev(_c.id), ref=0.0, tol_abs=1e-6,
            unit="-", in_series=False,
            source="max |bridge - Mecway| / max |Mecway| op de opgeslagen "
                   "tijden; Mecway 34 headless, eigen D20/DA0-oplossing"))
