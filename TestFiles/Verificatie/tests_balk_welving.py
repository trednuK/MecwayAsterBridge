# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Beams with warping: elem_beam = POU_D_TG (STAPPENPLAN S19, KNOWN_BUGS 115).
Shear centre (EY, EZ), warping constant (JG) and the warping DOF GRX at
supports (setting beam_warping, Scripts/bridge_warping.py). Explanation:
docs/Verificatie.md (par. Balken met welving).

- BU-38: the C column of BU-35/36 (C 100 x 50 x 6 mm, fixed foot, 1000 N)
  with POU_D_TG: flexural-torsional buckling against the hex20 model BU-36
  (Mecway 34 = Code-Aster) and thin-walled theory (Timoshenko & Gere 1961
  par. 5.3); the auto rule restrains the warping at the Fixed support.
- BU-39: I 100/50/10/8 mm, L = 1.5 m, fork supports at both ends (pinned
  and roller, rotation about the beam axis fixed, warping free), uniform
  moment: lateral-torsional buckling M_cr = pi/L sqrt(E I_z G J (1 + pi^2 E
  C_w/(G J L^2))) (Timoshenko & Gere 1961 par. 6.2).
- BU-41: Code-Aster test case ssll103a (angle 120 x 120 x 8 mm, L = 1200
  mm, pinned ends with the twist fixed, warping free, POU_D_TG): the
  section from the test as a Mecway general section with an #ASTER-SECTIE
  line (JG, EY, IYR2 as MecwaySectionProps writes them); factors equal to
  VALE_CALC. BU-41b: the same with Mecway's L profile (section computed by
  the bridge, bridge_warping.section_props).
- BU-42: T column (fixed foot), flexural-torsional buckling against
  thin-walled theory (Timoshenko & Gere 1961 par. 5.3, C_w = 0).
- LS-90: cantilever I 100/50/10/8 mm, L = 1 m, end torque T = 100 N m,
  Fixed support (warping restrained, auto): phi(L) = T/(G J) (L -
  tanh(kL)/k), k = sqrt(G J/(E C_w)) (Timoshenko & Gere 1961 par. 5.4;
  Trahair 1993 ch. 3). LS-90b: the same with beam_warping = free: T L/(G J).
- LS-91: the I beam on fork supports (warping free), T at midspan:
  phi = T/(2 G J) (L/2 - tanh(kL/2)/k) (each half: warping restrained at
  midspan by symmetry, free at the support).
- LS-90c: default POU_D_E unchanged (T L/(G J), no warping); BU-35 stays
  the POU_D_E reference (KNOWN_BUGS 115).
- LS-90d/LS-90e: the bimoment BX at the clamp of LS-90 with its sign, for
  both torque signs (Code-Aster: BX = +E I_w phi'').
- LS-94/94b, LS-95/95b: shear centre of C and L profiles (twist under a
  transverse load through the centroid) and Mecway's section axes.
- BU-43/43b, BU-44/44b: lateral-torsional buckling of mono-symmetric
  sections (T; C bent about its minor axis), both moment signs, against
  the mono-symmetric formula with the Wagner parameter (Trahair 1993 ch. 6).
  BU-43c: the T at L = 4 m, also against a shell model in Mecway 34.
"""
import math
from verif_lib import Case, Check, Model, SCRIPTS, quadmesh
import tests_balkorientatie as BO
import tests_knik_balk as KB

GROUP = "Knik"
E, G = BO.E, BO.G
STEEL, DENS = BO.STEEL, BO.DENS
TG = {"elem_beam": "POU_D_TG"}

# I 100/50/10/8 mm: A, I about V (weak), J as the bridge (Mecway's values)
I_A, I_V, I_J = BO.IP_A, BO.IP_IV, BO.IP_J
# Warping constant of the I profile, centre-line: t_f b^3 h^2/24 with
# h = a - t_f (Timoshenko & Gere 1961 par. 5.4; Trahair 1993 app.). The
# bridge adds the thickness warping of the plates (+1.0 %, bridge_warping).
I_CW = 0.010 * 0.050 ** 3 * (0.100 - 0.010) ** 2 / 24.0


def _line(m, p0, p1, n, elset="Balk"):
    return KB._line(m, p0, p1, n, elset)


def _fork(m, name, nid, axial):
    """Fork support: translations (axial=True: also along the beam axis X)
    and the rotation about the beam axis X fixed; warping and bending
    rotations free."""
    m.node_selection(name, [nid])
    if axial:
        m.add('<pinnedsupport selection="%s" />' % name)
    else:
        for d in ("<x>0</x><y>1</y><z>0</z>", "<x>0</x><y>0</y><z>1</z>"):
            m.add('<displacement selection="%s"><value>0 mm</value>%s'
                  '</displacement>' % (name, d))
    m.add('<noderotation selection="%s"><value>0 rad</value><x>1</x>'
          '<y>0</y><z>0</z></noderotation>' % name)


# ------------------------------------------------------------------
# BU-38: C column with POU_D_TG
# ------------------------------------------------------------------
TESTS = [
    Case("BU-38", GROUP, "Flexural-torsional buckling, C column, beam "
         "with warping (POU_D_TG)", "buckling_3d", KB.build_bu35,
         [Check("factor 1 (uncoupled)", lambda r: r.mode(1),
                ref=KB.MW_BU36[0], tol=0.01, unit="-", in_series=False,
                source="BU-36: hex20, Code-Aster = Mecway 34"),
          Check("factor 2 vs flexural-torsional theory", lambda r: r.mode(2),
                ref=KB.P_FT / KB.P, tol=0.01, unit="-",
                source="Timoshenko & Gere 5.3, thin-walled channel "
                       "(tests_knik_balk._ft_channel)"),
          Check("factor 2 vs hex20 (BU-36)", lambda r: r.mode(2),
                ref=KB.MW_BU36[1], tol=0.03, unit="-", in_series=False,
                source="BU-36: hex20, Code-Aster = Mecway 34 = CCX")],
         general=TG,
         note="C 100 x 50 x 6 mm, L = 1 m, 20 POU_D_TG, P = 1000 N; "
              "EZ = -29.33 mm and C_w = 4.058e-10 m^6 computed by the bridge "
              "(bridge_warping), warping restrained at the Fixed support "
              "(beam_warping auto). With POU_D_E 616 (BU-35, KNOWN_BUGS "
              "115). With the warping free at the foot (beam_warping free) "
              "343.8 (run 28 Oct 2026)."),
]


# ------------------------------------------------------------------
# BU-39: lateral-torsional buckling of an I beam on fork supports
# ------------------------------------------------------------------
L39 = 1.5
M39 = 1000.0


def _mcr(length, cw):
    """M_cr of a simply supported (fork) I beam under uniform moment
    (Timoshenko & Gere 1961 par. 6.2)."""
    return (math.pi / length * math.sqrt(E * I_V * G * I_J) *
            math.sqrt(1.0 + math.pi ** 2 * E * cw / (G * I_J * length ** 2)))


def _min_abs(r):
    """Smallest |factor| (Code-Aster lists the +- pair in value order)."""
    return min(abs(v) for v in r.modes.values())


def build_bu39():
    """I beam along X (V = Y: web along Y, strong axis about Z), 30
    elements; fork supports; end moments -M/+M about Z (uniform moment)."""
    m = Model("B30", attrs={"maxmode": 4, "shift": 1})
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (L39, 0, 0), 30)
    m.mat("Mat", BO.IPROF, STEEL, DENS)
    _fork(m, "VorkA", nids[0], True)
    _fork(m, "VorkB", nids[-1], False)
    m.node_selection("EindA", [nids[0]])
    m.node_selection("EindB", [nids[-1]])
    m.add('<moment selection="EindA"><x>0 N.m</x><y>0 N.m</y>'
          '<z>%g N.m</z></moment>' % -M39)
    m.add('<moment selection="EindB"><x>0 N.m</x><y>0 N.m</y>'
          '<z>%g N.m</z></moment>' % M39)
    return m


TESTS.append(Case(
    "BU-39", GROUP, "Lateral-torsional buckling, I beam on fork supports, "
    "uniform moment (POU_D_TG)", "buckling_3d", build_bu39,
    [Check("smallest |factor| vs M_cr", _min_abs,
           ref=_mcr(L39, I_CW) / M39, tol=0.01, unit="-",
           source="Timoshenko & Gere 6.2 with C_w = t_f b^3 h^2/24"),
     Check("smallest |factor| / M_cr without warping",
           lambda r: _min_abs(r) / (_mcr(L39, 0.0) / M39),
           ref=_mcr(L39, I_CW) / _mcr(L39, 0.0), tol=0.01, unit="-",
           in_series=False,
           source="ratio M_cr(C_w)/M_cr(0) of Timoshenko & Gere 6.2")],
    general=TG,
    note="I 100/50/10/8 mm, L = 1.5 m, 30 POU_D_TG, fork supports (warping "
         "free: beam_warping auto, only translations and the rotation about "
         "the beam axis fixed), M = 1000 N m. The warping adds 5% to M_cr. "
         "The buckling factor comes as a +- pair (the sign of a uniform "
         "moment does not matter for a doubly symmetric section)."))


# ------------------------------------------------------------------
# BU-41: Code-Aster test case ssll103a through the bridge
# ------------------------------------------------------------------
# ssll103a.comm (17.4): A = 1856 mm^2, IY = 4167339, IZ = 1045547 mm^4,
# AY = AZ = 1, EY = 41.012 mm, EZ = 0, JX = 39595 mm^4, JG = 44398819
# mm^6, IYR2 = 84948392 mm^5, IZR2 = 0; E = 210000 MPa, NU = 0.3; 8 SEG2
# over 1200 mm; A1 pinned, A2 transverse fixed, twist fixed at both ends,
# GRX free; unit compression. VALE_CALC of modes 1, 8 and 19.
SS103 = (6.91154293e05, 1.49004790e06, 9.69429478e06)
SS103_REF = (6.9253170999999996e5, 1.5048738999999999e6, 1.0058989e7)
UGS103 = ('<geometric type="UniformGeneralSection" area="1856 mm²" '
          'iyy="4167339 mm⁴" izz="1045547 mm⁴" torsionconstant="39595 mm⁴" />')
SECTIE103 = ("#ASTER-SECTIE Hoek: A=1.856e-3, IY=4.167339e-6, "
             "IZ=1.045547e-6, JX=3.9595e-8, AY=1, AZ=1, EY=0.041012, EZ=0, "
             "JG=4.4398819e-11, IYR2=8.4948392e-8, IZR2=0")
MAT103 = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="0.3" />')


def build_bu41(section=None):
    """Column along Z, 1200 mm, 8 elements, 1 N compression; section None:
    the general section of the test with its #ASTER-SECTIE line."""
    m = Model("B30", attrs={"maxmode": 20, "shift": 1})
    m.elset("Balk", "Hoek")
    nids = _line(m, (0, 0, 0), (0, 0, 1.2), 8)
    m.mat("Hoek", section or UGS103, MAT103)
    for name, nid, axial in (("A1", nids[0], True), ("A2", nids[-1], False)):
        m.node_selection(name, [nid])
        if axial:
            m.add('<pinnedsupport selection="%s" />' % name)
        else:
            for d in ("<x>1</x><y>0</y><z>0</z>", "<x>0</x><y>1</y><z>0</z>"):
                m.add('<displacement selection="%s"><value>0 mm</value>%s'
                      '</displacement>' % (name, d))
        m.add('<noderotation selection="%s"><value>0 rad</value><x>0</x>'
              '<y>0</y><z>1</z></noderotation>' % name)
    m.add('<force selection="A2"><x>0 N</x><y>0 N</y><z>-1 N</z></force>')
    if section is None:
        m.add(u"<ccxmodeldefinition>%s</ccxmodeldefinition>" % SECTIE103)
    return m


def _pos(r, k):
    return sorted(v for v in r.modes.values() if v > 0)[k - 1]


TESTS.append(Case(
    "BU-41", GROUP, "Code-Aster test case ssll103a: angle, "
    "flexural-torsional buckling (POU_D_TG, #ASTER-SECTIE)", "buckling_3d",
    build_bu41,
    [Check("mode 1 vs ssll103a", lambda r: _pos(r, 1), ref=SS103[0],
           tol=1e-5, unit="-", in_series=False,
           source="ssll103a VALE_CALC (same mesh and section)"),
     Check("mode 8 vs ssll103a", lambda r: _pos(r, 8), ref=SS103[1],
           tol=1e-5, unit="-", in_series=False,
           source="ssll103a VALE_CALC"),
     Check("mode 19 vs ssll103a", lambda r: _pos(r, 19), ref=SS103[2],
           tol=1e-5, unit="-", in_series=False,
           source="ssll103a VALE_CALC"),
     Check("mode 1 vs reference", lambda r: _pos(r, 1), ref=SS103_REF[0],
           tol=0.003, unit="-",
           source="ssll103a VALE_REFE (REFERENCE 'NON_DEFINI', PRECISION "
                  "0.3%)")],
    general=TG,
    note="Angle 120 x 120 x 8 mm, L = 1200 mm, 8 POU_D_TG, 1 N. Section "
         "values of the test (JG, EY, IYR2) through an #ASTER-SECTIE line "
         "on a general section. The bridge computes the same angle as an "
         "L profile with EZ = -40.96 mm (test EY 41.012), JG = 4.43988e-11 "
         "m^6 and IZR2 = -8.4848e-8 m^5 (test IYR2 8.4948e-8; bridge_warping, "
         "heel at +W)."))


def build_bu41b():
    """BU-41 with Mecway's L profile 120 x 120 x 8 mm instead of the
    general section: the bridge computes EY/EZ, JG, IYR2/IZR2."""
    return build_bu41('<geometric type="L" la="120 mm" lb="120 mm" '
                      'lc="8 mm" ld="0 mm" />')


TESTS.append(Case(
    "BU-41b", GROUP, "ssll103a with Mecway's L profile (POU_D_TG, section "
    "computed by the bridge)", "buckling_3d", build_bu41b,
    [Check("mode 1 vs reference", lambda r: _pos(r, 1), ref=SS103_REF[0],
           tol=0.03, unit="-",
           source="ssll103a VALE_REFE (REFERENCE 'NON_DEFINI')"),
     Check("mode 1 vs ssll103a (VALE_CALC)", lambda r: _pos(r, 1),
           ref=SS103[0], tol=0.03, unit="-", in_series=False,
           source="ssll103a VALE_CALC (section of the test)")],
    general=TG,
    note="L 120 x 120 x 8 mm (sharp corner, no root radius). -2.2%: "
         "Mecway's torsion constant (Roark, as Mecway shows it) is 38845 "
         "mm^4, the test's 39595 (-1.9%), and AY = AZ = 2.4 (bridge "
         "estimate) instead of 1. The bridge's EZ = -40.96 mm, JG = "
         "4.43988e-11 m^6 and IZR2 = -8.4848e-8 m^5 equal the test's EY, JG "
         "and IYR2 within 0.12% up to the common sign (the test's axes y/z are the bridge's "
         "z/y: Mecway's V is the minor axis of the angle)."))


# ------------------------------------------------------------------
# BU-42: T column, flexural-torsional buckling
# ------------------------------------------------------------------
# T 100 x 10 x 10 x 90 mm (Mecway: ta flange width, tb web thickness, tc
# flange thickness, td web height), fixed column L = 1 m along Z, 1000 N.
TPROF = ('<geometric type="T" ta="100 mm" tb="10 mm" tc="10 mm" '
         'td="90 mm" />')


def _ft_tee(length):
    """Flexural-torsional buckling load of the fixed T column (effective
    length 2L for bending and twist), Timoshenko & Gere 1961 par. 5.3:
    i0^2 (P - P_V)(P - P_T) - P^2 y0^2 = 0 with the twist coupled to the
    bending about V (the axis of symmetry); thin-walled: shear centre at
    the junction of the flange and web centre lines, C_w = 0."""
    a, tw, tf, d = 0.100, 0.010, 0.010, 0.090
    area = a * tf + tw * d
    yc = (a * tf * (d + tf / 2.0) + tw * d * d / 2.0) / area
    y0 = (d + tf / 2.0) - yc
    i_v = tf * a ** 3 / 12.0 + d * tw ** 3 / 12.0
    i_w = (a * tf ** 3 / 12.0 + a * tf * (d + tf / 2.0 - yc) ** 2 +
           tw * d ** 3 / 12.0 + tw * d * (d / 2.0 - yc) ** 2)
    # J as the bridge (Roark, _profile_props) so that only the coupling
    # is compared
    import sys
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    from bridge_from_liml import _profile_props
    j = _profile_props("T", a, tw, tf, d)[3]
    i02 = (i_v + i_w) / area + y0 ** 2
    p_v = math.pi ** 2 * E * i_v / (4 * length ** 2)
    p_t = G * j / i02
    beta = 1 - y0 ** 2 / i02
    s = p_v + p_t
    return (s - math.sqrt(s * s - 4 * beta * p_v * p_t)) / (2 * beta)


P_FT_T = _ft_tee(1.0)


def build_bu42():
    m = Model("B30", attrs={"maxmode": 4, "shift": 1})
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (0, 0, 1.0), 20)
    m.mat("Mat", TPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-1000 N</z>'
          '</force>')
    return m


TESTS.append(Case(
    "BU-42", GROUP, "Flexural-torsional buckling, T column (POU_D_TG)",
    "buckling_3d", build_bu42,
    [Check("factor 1 vs flexural-torsional theory", lambda r: r.mode(1),
           ref=P_FT_T / 1000.0, tol=0.02, unit="-",
           source="Timoshenko & Gere 5.3, thin-walled T (C_w = 0)")],
    general=TG,
    note="T 100 x 10 x 10 x 90 mm, L = 1 m, 20 POU_D_TG, P = 1000 N. The "
         "bridge adds the thickness warping C_w = 3.08e-11 m^6 of the "
         "plates (thin-walled theory: 0), restrained at the foot."))


# ------------------------------------------------------------------
# LS-90/91: torsion with restrained and free warping
# ------------------------------------------------------------------
T90 = 100.0
L90 = 1.0
K90 = math.sqrt(G * I_J / (E * I_CW))


def build_ls90(torque=T90):
    m = Model("S30")
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (L90, 0, 0), 20)
    m.mat("Mat", BO.IPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<moment selection="Tip"><x>%g N.m</x><y>0 N.m</y><z>0 N.m</z>'
          '</moment>' % torque)
    return m


def build_ls91():
    m = Model("S30")
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (L90, 0, 0), 20)
    m.mat("Mat", BO.IPROF, STEEL, DENS)
    _fork(m, "VorkA", nids[0], True)
    _fork(m, "VorkB", nids[-1], False)
    m.node_selection("Midden", [nids[10]])
    m.add('<moment selection="Midden"><x>%g N.m</x><y>0 N.m</y>'
          '<z>0 N.m</z></moment>' % T90)
    return m


PHI_CLAMP = T90 / (G * I_J) * (L90 - math.tanh(K90 * L90) / K90)
PHI_FREE = T90 * L90 / (G * I_J)
PHI_FORK = T90 / (2 * G * I_J) * (L90 / 2 - math.tanh(K90 * L90 / 2) / K90)
SRC_CLAMP = ("T/(GJ) (L - tanh(kL)/k), k = sqrt(GJ/(E C_w)) (Timoshenko & "
             "Gere 5.4)")
TIP = (L90, 0.0, 0.0)
MID = (L90 / 2, 0.0, 0.0)

TESTS += [
    Case("LS-90", "Lineair statisch", "Torsion with restrained warping, "
         "I cantilever (POU_D_TG)", "lin_static_3d", build_ls90,
         [Check("twist at the tip", lambda r: r.at("rotx", TIP),
                ref=PHI_CLAMP, tol=0.005, unit="rad", source=SRC_CLAMP),
          Check("twist vs free warping (ratio)",
                lambda r: r.at("rotx", TIP) / PHI_FREE,
                ref=PHI_CLAMP / PHI_FREE, tol=0.005, unit="-",
                in_series=False, source="(L - tanh(kL)/k)/L")],
         general=TG,
         note="I 100/50/10/8 mm, L = 1 m, 20 POU_D_TG, T = 100 N m about "
              "the beam axis; Fixed support: GRX = 0 (beam_warping auto). "
              "Restrained warping makes the tip twist 15% smaller."),
    Case("LS-90b", "Lineair statisch", "Torsion, I cantilever, warping "
         "free (POU_D_TG, beam_warping free)", "lin_static_3d", build_ls90,
         [Check("twist at the tip", lambda r: r.at("rotx", TIP),
                ref=PHI_FREE, tol=1e-4, unit="rad",
                source="T L/(G J) (Saint-Venant)")],
         general=dict(TG, beam_warping="free"),
         note="As LS-90 with beam_warping = free: uniform torsion."),
    Case("LS-90c", "Lineair statisch", "Torsion, I cantilever, default "
         "POU_D_E (no warping)", "lin_static_3d", build_ls90,
         [Check("twist at the tip", lambda r: r.at("rotx", TIP),
                ref=PHI_FREE, tol=1e-6, unit="rad",
                source="T L/(G J) (Saint-Venant)")],
         note="Default element unchanged: no warping."),
    Case("LS-91", "Lineair statisch", "Torsion at midspan, I beam on fork "
         "supports (POU_D_TG)", "lin_static_3d", build_ls91,
         [Check("twist at midspan", lambda r: r.at("rotx", MID),
                ref=PHI_FORK, tol=0.005, unit="rad",
                source="T/(2GJ) (L/2 - tanh(kL/2)/k): warping free at the "
                       "forks, restrained at midspan by symmetry")],
         general=TG,
         note="I 100/50/10/8 mm, L = 1 m, 20 POU_D_TG, fork supports "
              "(beam_warping auto leaves GRX free there), T = 100 N m at "
              "midspan."),
]


# ------------------------------------------------------------------
# LS-90d/e: the bimoment at the clamp of LS-90, both torque signs
# ------------------------------------------------------------------
# The bimoment (EFGE_ELNO component BX of POU_D_TG) is not sent to Mecway.
# The case prints it with #ASTER-POST code into the .mess and reads it
# there, with its sign, and also the warping DOF GRX. Cantilever, warping
# restrained at x = 0 and free at the tip, end torque T about +X:
# G J phi' - E C_w phi''' = T gives phi'(x) = T/(G J) (1 - cosh kx +
# tanh kL sinh kx) and E C_w phi''(x) = T sinh(k (L - x))/(k cosh kL), so
# E C_w phi''(0) = T tanh(kL)/k and phi'(L) = T/(G J) (1 - 1/cosh kL)
# (Vlasov; Trahair 1993 ch. 3; Timoshenko & Gere 1961 par. 5.4).
# Code-Aster's sign (measured with Code-Aster 17.4, 29 Oct 2026, LS-90d
# and LS-90e): BX = +E JG d(GRX)/dx with GRX = +d(DRX)/dx (GRX is also
# positive under a positive torque in test case ssll102d), i.e.
# BX = +E I_w phi'', the opposite sign of Vlasov's B = -E I_w phi''. The
# U4.42.01 and R3.08.01 documents do not define the sign of BX.
BX_POST = (u"<ccxmodeldefinition>"
           u"#ASTER-POST _tbx = CREA_TABLE(RESU=_F(RESULTAT=res, "
           u"NOM_CHAM='EFGE_ELNO', NOM_CMP='BX', TOUT='OUI', "
           u"TOUT_ORDRE='OUI'))\n"
           u"#ASTER-POST print('BRIDGE_BX_CLAMP %.12e' % max(_tbx.EXTR_TABLE()"
           u".values()['BX'], key=abs))\n"
           u"#ASTER-POST _tgx = CREA_TABLE(RESU=_F(RESULTAT=res, "
           u"NOM_CHAM='DEPL', NOM_CMP='GRX', TOUT='OUI', "
           u"TOUT_ORDRE='OUI'))\n"
           u"#ASTER-POST print('BRIDGE_GRX_TIP %.12e' % max(_tgx.EXTR_TABLE()"
           u".values()['GRX'], key=abs))"
           u"</ccxmodeldefinition>")


def _mess_value(r, tag):
    """Last value printed as '<tag> <value>' into the .mess (BX_POST)."""
    import io
    import re
    text = io.open(r.mess, encoding="utf-8", errors="replace").read()
    return float(re.findall(tag + r" (\S+)", text)[-1])


def _bx_clamp(r):
    """BX with the largest magnitude along the beam (at the clamp), with
    its sign."""
    return _mess_value(r, "BRIDGE_BX_CLAMP")


def _grx_tip(r):
    """GRX with the largest magnitude (at the free tip), with its sign."""
    return _mess_value(r, "BRIDGE_GRX_TIP")


def build_ls90d(torque=T90):
    m = build_ls90(torque)
    m.add(BX_POST)
    return m


B90 = T90 * math.tanh(K90 * L90) / K90
GRX90 = T90 / (G * I_J) * (1.0 - 1.0 / math.cosh(K90 * L90))
SRC_BX = ("BX = +E C_w phi''; E C_w phi''(0) = T tanh(kL)/k (Vlasov; "
          "Trahair 1993 ch. 3)")
SRC_GRX = "GRX = phi'(L) = T/(G J) (1 - 1/cosh kL)"

TESTS += [
    Case("LS-90d", "Lineair statisch", "Bimoment at the clamp, I cantilever "
         "under torque (POU_D_TG)", "lin_static_3d", build_ls90d,
         [Check("bimoment BX at the clamp (signed)", _bx_clamp,
                ref=B90, tol=0.02, unit="N m^2", source=SRC_BX),
          Check("warping GRX at the tip (signed)", _grx_tip,
                ref=GRX90, tol=0.01, unit="rad/m", in_series=False,
                source=SRC_GRX),
          Check("twist at the tip", lambda r: r.at("rotx", TIP),
                ref=PHI_CLAMP, tol=0.005, unit="rad", in_series=False,
                source=SRC_CLAMP)],
         general=TG,
         note="LS-90 with #ASTER-POST lines that print BX of EFGE_ELNO "
              "(largest magnitude, with its sign) and GRX into the .mess "
              "(the bimoment is not sent to Mecway). T = +100 N m about "
              "+X gives BX > 0 at the clamp: Code-Aster's BX = +E I_w "
              "phi''."),
    Case("LS-90e", "Lineair statisch", "Bimoment at the clamp, torque "
         "reversed (POU_D_TG)", "lin_static_3d", lambda: build_ls90d(-T90),
         [Check("bimoment BX at the clamp (signed)", _bx_clamp,
                ref=-B90, tol=0.02, unit="N m^2", source=SRC_BX),
          Check("warping GRX at the tip (signed)", _grx_tip,
                ref=-GRX90, tol=0.01, unit="rad/m", in_series=False,
                source=SRC_GRX),
          Check("twist at the tip", lambda r: r.at("rotx", TIP),
                ref=-PHI_CLAMP, tol=0.005, unit="rad", in_series=False,
                source=SRC_CLAMP)],
         general=TG,
         note="LS-90d with T = -100 N m: BX, GRX and the twist change "
              "sign."),
]


# ------------------------------------------------------------------
# Mecway's section axes of C and L profiles (measured)
# ------------------------------------------------------------------
# Mecway 34 headless (mw_solve.py, own solver, 29 Oct 2026): cantilever
# along X, 10 line2, V = +Y (explicit orientation; the default is the
# same), so W = U x V = +Z; end moment 100 N m about global Y (= about V)
# or Z (= about W). Mecway's stress recovery point stresspt1 of the C
# 100 x 50 x 6 mm (corner of the web) and stresspt2 of the L 120 x 80 x 8
# mm (tip of leg a). sigma = M_V w/I_V - M_W v/I_W at a point (v, w):
# tension at the web of the C under +M_V puts the web at +W.
MW_C_PT1_MV = 5600470.990694939
MW_L_PT2_MV = -3092623.1056702053
MW_L_PT2_MW = -3302304.500811057


def _frame_stress(kind, dims, point, m_v, m_w):
    """sigma at a drawing point with the bridge's map of Mecway's axes
    (bridge_warping.mecway_frame) and its I about V and W."""
    import sys
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    import bridge_warping
    from bridge_from_liml import _profile_props
    v, w = bridge_warping.mecway_frame(kind, *dims)[1](*point)
    i_v, i_w = _profile_props(kind, *dims)[1:3]
    return m_v * w / i_v - m_w * v / i_w


def _j_mecway(kind, dims):
    """Torsion constant as Mecway (bridge_from_liml._profile_props)."""
    import sys
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    from bridge_from_liml import _profile_props
    return _profile_props(kind, *dims)[3]


# ------------------------------------------------------------------
# LS-94: C cantilever, transverse tip load through the centroid
# ------------------------------------------------------------------
# C 100 x 50 x 6 mm (ca flange width, cb height, cc/cd thicknesses), along
# X with V = +Y (web along Y, flanges along Z), Fixed at x = 0 (warping
# restrained, auto), F = 1000 N along +Y at the tip node (the centroid).
# The shear centre lies on the web side, at +W (Mecway's axes, see above):
# the load passes the shear centre at a distance e and twists the beam by
# T = F e about +X (r_G - r_S = -e W, (-e W) x (F V) = +F e U).
C_DIMS = (0.050, 0.100, 0.006, 0.006)
F92 = 1000.0
L92 = 1.0


def _channel_cl():
    """(e, C_w) of the C on its centre line: shear centre e_s = 3 b^2/(6 b
    + h) from the web centre line, centroid x_c = b^2/(2 b + h) on the
    other side, e = e_s + x_c; C_w = t b^3 h^2/12 (3b + 2h)/(6b + h)
    (Timoshenko & Gere 1961 par. 5.3; Trahair 1993 app.)."""
    b, h, t = 0.047, 0.094, 0.006
    e = 3 * b * b / (6 * b + h) + b * b / (2 * b + h)
    cw = t * b ** 3 * h ** 2 / 12.0 * (3 * b + 2 * h) / (6 * b + h)
    return e, cw


E92, CW92 = _channel_cl()
J92 = _j_mecway("C", C_DIMS)
K92 = math.sqrt(G * J92 / (E * CW92))
T92 = F92 * E92
PHI92 = T92 / (G * J92) * (L92 - math.tanh(K92 * L92) / K92)
SRC92 = ("T/(GJ) (L - tanh(kL)/k) with T = F e, e = 29.375 mm (thin-walled "
         "channel, Timoshenko & Gere 5.3/5.4), J as Mecway")


def build_ls92(vdir=None):
    """vdir: explicit V direction of the beam elements (None: default)."""
    m = Model("S30")
    m.elset("Balk", "Mat")
    nids = [m.node(L92 * i / 20.0, 0, 0) for i in range(21)]
    attrs = ("" if vdir is None else
             'orientationvx="%g" orientationvy="%g" orientationvz="%g"'
             % vdir)
    for i in range(20):
        m.elem("Balk", "line2", [nids[i], nids[i + 1]], attrs)
    m.mat("Mat", KB.CPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>0 N</z>'
          '</force>' % F92)
    return m


TIP92 = (L92, 0.0, 0.0)
TESTS += [
    Case("LS-94", "Lineair statisch", "Shear centre of a C profile: "
         "cantilever with a transverse tip load through the centroid "
         "(POU_D_TG)", "lin_static_3d", build_ls92,
         [Check("twist at the tip (sign: shear centre at +W)",
                lambda r: r.at("rotx", TIP92), ref=PHI92, tol=0.02,
                unit="rad", source=SRC92),
          Check("Mecway stresspt1 (web) vs the bridge's axes",
                lambda r: MW_C_PT1_MV / _frame_stress(
                    "C", C_DIMS, (0.0, 0.0), 100.0, 0.0),
                ref=1.0, tol=1e-6, unit="-", in_series=False,
                source="Mecway 34 headless, end moment 100 N m about V "
                       "(29 Oct 2026)")],
         general=TG,
         note="C 100 x 50 x 6 mm, L = 1 m, 20 POU_D_TG, V = +Y (default), "
              "F = 1000 N along +Y at the tip; Fixed: warping restrained. "
              "The bridge's EZ = -29.33 mm (centroid - shear centre). "
              "Mecway's own beam does not twist here (no shear centre, "
              "manual par. 7.5). Before 29 Oct 2026 the bridge put the "
              "shear centre at -W: the twist had the opposite sign."),
    Case("LS-94b", "Lineair statisch", "Shear centre of a C profile, beam "
         "turned over (V = -Y, POU_D_TG)", "lin_static_3d",
         lambda: build_ls92((0.0, -1.0, 0.0)),
         [Check("twist at the tip (opposite sign)",
                lambda r: r.at("rotx", TIP92), ref=-PHI92, tol=0.02,
                unit="rad", source=SRC92 + "; W = -Z, so the shear centre "
                "is at -Z")],
         general=TG,
         note="LS-94 with an explicit orientation V = (0, -1, 0): the "
              "section is turned over, the load is now along -V and the "
              "twist changes sign."),
]


# ------------------------------------------------------------------
# LS-95: L cantilever with the horizontal leg longer (a > b)
# ------------------------------------------------------------------
# L 120 x 80 x 8 mm (la horizontal leg, lb vertical leg, lc thickness),
# along X (V = +Y, W = +Z: Mecway's principal axes), Fixed at x = 0,
# F = 1000 N along +Y and 1000 N along +Z at the tip. Mecway uses the principal axes with the angle wrapped into (-45,
# 45] degrees; for a > b its V is the major axis (bridge before 30 Oct
# 2026: the minor axis, IY and IZ swapped). LS-95: POU_D_E against
# Mecway's own solver (same Euler-Bernoulli beam). LS-95b: POU_D_TG, the
# twist from the shear centre at the heel (crossing of the leg centre
# lines) and C_w = t^3/36 (a'^3 + b'^3) (thickness warping of the legs,
# a' = a - t/2, b' = b - t/2; AISC Design Guide 9, Seaburg & Carter 1997).
L_DIMS = (0.120, 0.080, 0.008, 0.0)
LPROF = '<geometric type="L" la="120 mm" lb="80 mm" lc="8 mm" ld="0 mm" />'
F93 = 1000.0
L93 = 1.0
# Mecway 34 headless (mw_solve.py on modellen/LS-95.liml, own solver,
# 29 Oct 2026): tip displacement
MW93 = {"disply": 0.003368385981291101, "displz": 0.0006006251923444849}


def _heel_offset():
    """Local (v, w) of the heel (centre-line crossing, drawing point (t/2,
    t/2)) in Mecway's principal axes, written out independently of the
    bridge: centroid of the two legs, principal angle wrapped into (-45,
    45] degrees, V = (-sin, cos), W along -(cos, sin) (measured, see
    MW_L_PT2_*)."""
    a, b, t = L_DIMS[:3]
    rects = [(0.0, a, 0.0, t), (0.0, t, t, b)]
    area = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in rects)
    cx = sum((x1 - x0) * (y1 - y0) * (x0 + x1) / 2 for x0, x1, y0, y1
             in rects) / area
    cy = sum((x1 - x0) * (y1 - y0) * (y0 + y1) / 2 for x0, x1, y0, y1
             in rects) / area
    iw = iv = ivw = 0.0
    for x0, x1, y0, y1 in rects:
        w, h = x1 - x0, y1 - y0
        dx, dy = (x0 + x1) / 2 - cx, (y0 + y1) / 2 - cy
        iw += w * h ** 3 / 12 + w * h * dy * dy
        iv += h * w ** 3 / 12 + w * h * dx * dx
        ivw += w * h * dx * dy
    th = 0.5 * math.atan2(-2 * ivw, iw - iv)
    while th > math.pi / 4 + 1e-12:
        th -= math.pi / 2
    while th <= -math.pi / 4 + 1e-12:
        th += math.pi / 2
    dx, dy = t / 2 - cx, t / 2 - cy
    return (-math.sin(th) * dx + math.cos(th) * dy,
            -(math.cos(th) * dx + math.sin(th) * dy))


V93S, W93S = _heel_offset()
# r_G - r_S = (-v_S, -w_S) in (V, W) = (Y, Z); F = (0, F, F):
# T_x = dy F_z - dz F_y = (-v_S + w_S) F
T93 = (W93S - V93S) * F93
CW93 = L_DIMS[2] ** 3 / 36.0 * ((L_DIMS[0] - L_DIMS[2] / 2) ** 3 +
                                (L_DIMS[1] - L_DIMS[2] / 2) ** 3)
J93 = _j_mecway("L", L_DIMS)
K93 = math.sqrt(G * J93 / (E * CW93))
PHI93 = T93 / (G * J93) * (L93 - math.tanh(K93 * L93) / K93)


def build_ls93():
    m = Model("S30")
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (L93, 0, 0), 20)
    m.mat("Mat", LPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>%g N</z>'
          '</force>' % (F93, F93))
    return m


TIP93 = (L93, 0.0, 0.0)
TESTS += [
    Case("LS-95", "Lineair statisch", "L profile with the horizontal leg "
         "longer: principal axes as Mecway (POU_D_E)", "lin_static_3d",
         build_ls93,
         [Check("tip DZ vs Mecway", lambda r: r.at("displz", TIP93),
                ref=MW93["displz"], tol=1e-4, unit="m",
                source="Mecway 34 headless, same .liml (own solver)"),
          Check("tip DY vs Mecway", lambda r: r.at("disply", TIP93),
                ref=MW93["disply"], tol=1e-4, unit="m",
                source="Mecway 34 headless, same .liml (own solver)"),
          Check("Mecway stresspt2 (leg a, M about V) vs the bridge's axes",
                lambda r: MW_L_PT2_MV / _frame_stress(
                    "L", L_DIMS, (0.120, 0.0), 100.0, 0.0),
                ref=1.0, tol=1e-6, unit="-", in_series=False,
                source="Mecway 34 headless, end moment 100 N m about V "
                       "(29 Oct 2026)"),
          Check("Mecway stresspt2 (leg a, M about W) vs the bridge's axes",
                lambda r: MW_L_PT2_MW / _frame_stress(
                    "L", L_DIMS, (0.120, 0.0), 0.0, 100.0),
                ref=1.0, tol=1e-6, unit="-", in_series=False,
                source="Mecway 34 headless, end moment 100 N m about W "
                       "(29 Oct 2026)")],
         note="L 120 x 80 x 8 mm, L = 1 m, 20 POU_D_E, F = 1000 N along "
              "+Y and +Z at the tip (DY with I about W, DZ with I about V). "
              "Before 29 Oct 2026 the bridge swapped IY and IZ of an L "
              "with a > b."),
    Case("LS-95b", "Lineair statisch", "Shear centre of an L profile: "
         "cantilever with a transverse tip load through the centroid "
         "(POU_D_TG)", "lin_static_3d", build_ls93,
         [Check("twist at the tip (shear centre at the heel)",
                lambda r: r.at("rotx", TIP93), ref=PHI93, tol=0.02,
                unit="rad",
                source="T/(GJ) (L - tanh(kL)/k), T = F x (heel offset), "
                       "C_w = t^3/36 (a'^3 + b'^3) (AISC DG9), J as "
                       "Mecway")],
         general=TG,
         note="As LS-95 with POU_D_TG. The heel lies %.2f mm along V and "
              "%.2f mm along W from the centroid (Mecway's principal "
              "axes); the load twists the beam by T = %.2f N m."
              % (V93S * 1e3, W93S * 1e3, T93)),
]


# ------------------------------------------------------------------
# BU-43/44: lateral-torsional buckling of mono-symmetric sections
# ------------------------------------------------------------------
# Simply supported (fork) beam under a uniform moment, sine modes (exact
# for this case). Coordinates: y along the axis of symmetry of the section
# (the plane of bending), x across it (the lateral direction), y0 the shear
# centre, M > 0 when the fibres at +y are in tension (sigma = M y/I_x, I_x
# = int y^2 dA). Energy (Trahair 1993 ch. 6, mono-symmetric beams; SSRC
# Guide, Galambos 1998, ch. 5; z_j of NCCI SN030 is |beta|/2):
#   1/2 int [E I_y u''^2 + E I_w phi''^2 + G J phi'^2 + 2 M u'' phi
#            + M beta phi'^2] dz,
#   beta = (1/I_x) int y (x^2 + y^2) dA - 2 y0   (Wagner, "beta_x"),
# gives M^2 - P beta M - P (G J + pi^2 E I_w/L^2) = 0 with P = pi^2 E I_y
# / L^2 (I_y = int x^2 dA, lateral bending):
#   M_cr = P [beta/2 +- sqrt(beta^2/4 + I_w/I_y + G J L^2/(pi^2 E I_y))].
# beta < 0 when the shear centre lies at +y (T: flange at +y; C: web at
# +y); the larger |M_cr| then comes with compression at +y, the side of
# the shear centre (flange of the T, web of the C). The section values
# below are written out independently of the bridge: exact rectangles for
# the centroid, the inertias and the Wagner integral, thin-walled formulas
# for the shear centre and I_w (as bridge_warping), J as Mecway.


def _rect_section(rects):
    """(area, cx, cy, int dx^2, int dy^2, int dy (dx^2 + dy^2)) of
    rectangles (x0, x1, y0, y1) of the drawing, about the centroid."""
    area = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in rects)
    cx = sum((x1 - x0) * (y1 - y0) * (x0 + x1) / 2 for x0, x1, y0, y1
             in rects) / area
    cy = sum((x1 - x0) * (y1 - y0) * (y0 + y1) / 2 for x0, x1, y0, y1
             in rects) / area
    ixx = iyy = wag = 0.0
    for x0, x1, y0, y1 in rects:
        a0, a1, b0, b1 = x0 - cx, x1 - cx, y0 - cy, y1 - cy
        ixx += (a1 ** 3 - a0 ** 3) / 3 * (b1 - b0)
        iyy += (a1 - a0) * (b1 ** 3 - b0 ** 3) / 3
        wag += ((a1 ** 3 - a0 ** 3) / 3 * (b1 ** 2 - b0 ** 2) / 2 +
                (a1 - a0) * (b1 ** 4 - b0 ** 4) / 4)
    return area, cx, cy, ixx, iyy, wag


def _mcr_pair(i_lat, i_w, j, beta, length):
    """(M_cr > 0, M_cr < 0) of the fork beam under uniform moment."""
    p = math.pi ** 2 * E * i_lat / length ** 2
    root = math.sqrt(beta ** 2 / 4 + i_w / i_lat +
                     G * j * length ** 2 / (math.pi ** 2 * E * i_lat))
    return p * (beta / 2 + root), p * (beta / 2 - root)


# T 100 x 10 x 10 x 90 mm of BU-42 (flange width a, web thickness tw,
# flange thickness tf, web height d); drawing x horizontal, y vertical,
# flange on top; Mecway's V = drawing y (mecway_frame): y = V, x = W.
T_DIMS = (0.100, 0.010, 0.010, 0.090)


def _tee_beta():
    a, tw, tf, d = T_DIMS
    area, cx, cy, ixx, iyy, wag = _rect_section(
        [(0.0, a, d, d + tf), ((a - tw) / 2, (a + tw) / 2, 0.0, d)])
    y0 = d + tf / 2 - cy               # shear centre: flange centre line
    beta = wag / iyy - 2 * y0
    # I_w of a tee (thickness warping of the plates; AISC Design Guide 9,
    # Seaburg & Carter 1997): (tf^3 a^3/4 + tw^3 h'^3)/36, h' = d + tf/2
    i_w = (tf ** 3 * a ** 3 / 4 + tw ** 3 * (d + tf / 2) ** 3) / 36
    return ixx, i_w, beta


L43 = 2.0
M43 = 1000.0
T43_ILAT, T43_IW, T43_BETA = _tee_beta()
T43_J = _j_mecway("T", T_DIMS)
# (M > 0: flange in tension, M < 0: flange in compression)
T43_POS, T43_NEG = _mcr_pair(T43_ILAT, T43_IW, T43_J, T43_BETA, L43)
SRC43 = ("M_cr = P [beta/2 +- sqrt(beta^2/4 + I_w/I_y + GJL^2/(pi^2 E I_y))]"
         ", mono-symmetric beam (Trahair 1993 ch. 6; SSRC Guide ch. 5)")


def build_bu43(sign=1.0, length=L43):
    """T beam along X (V = +Y: flange at +Y), 40 POU_D_TG, fork supports,
    end moments -sign M (A) and +sign M (B) about Z: internal M_z = +sign
    M, sigma = -M_z y/I, so sign = +1 puts the flange in compression."""
    m = Model("B30", attrs={"maxmode": 8, "shift": 1})
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (length, 0, 0), 40)
    m.mat("Mat", TPROF, STEEL, DENS)
    _fork(m, "VorkA", nids[0], True)
    _fork(m, "VorkB", nids[-1], False)
    m.node_selection("EindA", [nids[0]])
    m.node_selection("EindB", [nids[-1]])
    for name, f in (("EindA", -sign), ("EindB", sign)):
        m.add('<moment selection="%s"><x>0 N.m</x><y>0 N.m</y>'
              '<z>%g N.m</z></moment>' % (name, f * M43))
    return m


def _pos_min(r):
    """Smallest positive buckling factor (the applied load)."""
    return min(v for v in r.modes.values() if v > 0)


def _neg_min(r):
    """Negative buckling factor of smallest magnitude (load reversed)."""
    return max(v for v in r.modes.values() if v < 0)


# C 100 x 50 x 6 mm (C_DIMS, LS-94) bent about Mecway's V (the minor axis):
# the plane of bending is the axis of symmetry W, the web lies at +W
# (mecway_frame), lateral buckling along V (about the major axis W) with
# twist: y = W, x = V. Shear centre e_s = 3 b^2/(6 b + h) beyond the web
# centre line (centre-line dimensions; Timoshenko & Gere 1961 par. 5.3).
def _channel_beta():
    a, h_out, tf, tw = C_DIMS
    # drawing: web at x in [0, tw], flanges towards +x; W = -x
    area, cx, cy, ixx, iyy, wag = _rect_section(
        [(0.0, a, 0.0, tf), (0.0, a, h_out - tf, h_out),
         (0.0, tw, tf, h_out - tf)])
    b, h = a - tw / 2, h_out - tf
    x_s = tw / 2 - 3 * b * b / (6 * b + h)        # drawing x of the shear centre
    w0 = -(x_s - cx)                              # W of the shear centre
    # int w (v^2 + w^2) dA with w = -dx, v = dy: -(int dx (dx^2 + dy^2))
    wag_w = -(_rect_wag_x([(0.0, a, 0.0, tf), (0.0, a, h_out - tf, h_out),
                           (0.0, tw, tf, h_out - tf)], cx, cy))
    beta = wag_w / ixx - 2 * w0
    return iyy, beta


def _rect_wag_x(rects, cx, cy):
    """int dx (dx^2 + dy^2) dA of rectangles about (cx, cy)."""
    out = 0.0
    for x0, x1, y0, y1 in rects:
        a0, a1, b0, b1 = x0 - cx, x1 - cx, y0 - cy, y1 - cy
        out += ((a1 ** 4 - a0 ** 4) / 4 * (b1 - b0) +
                (a1 ** 2 - a0 ** 2) / 2 * (b1 ** 3 - b0 ** 3) / 3)
    return out


L44 = 4.0
M44 = 1000.0
C44_ILAT, C44_BETA = _channel_beta()
C44_IW = CW92                                     # centre-line C_w (LS-94)
# (M > 0: web in tension, M < 0: web in compression)
C44_POS, C44_NEG = _mcr_pair(C44_ILAT, C44_IW, J92, C44_BETA, L44)


def build_bu44(sign=1.0):
    """C beam along X (V = +Y, web at +W = +Z), 40 POU_D_TG, fork supports,
    end moments -sign M (A) and +sign M (B) about Y (= V, the minor axis):
    internal M_y = +sign M, sigma = +M_y z/I, so sign = +1 puts the web in
    tension and the flange tips in compression."""
    m = Model("B30", attrs={"maxmode": 12, "shift": 1})
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (L44, 0, 0), 40)
    m.mat("Mat", KB.CPROF, STEEL, DENS)
    _fork(m, "VorkA", nids[0], True)
    _fork(m, "VorkB", nids[-1], False)
    m.node_selection("EindA", [nids[0]])
    m.node_selection("EindB", [nids[-1]])
    for name, f in (("EindA", -sign), ("EindB", sign)):
        m.add('<moment selection="%s"><x>0 N.m</x><y>%g N.m</y>'
              '<z>0 N.m</z></moment>' % (name, f * M44))
    return m


TESTS += [
    Case("BU-43", GROUP, "Lateral-torsional buckling, T beam, flange in "
         "compression (POU_D_TG)", "buckling_3d", build_bu43,
         [Check("factor (flange in compression)", _pos_min,
                ref=-T43_NEG / M43, tol=0.02, unit="-", source=SRC43),
          Check("factor of the reversed load (stem in compression)",
                _neg_min, ref=-T43_POS / M43, tol=0.02, unit="-",
                source=SRC43)],
         general=TG,
         note="T 100 x 10 x 10 x 90 mm (flange at +Y), L = 2 m, 40 "
              "POU_D_TG, fork supports (warping free), end moments 1000 N m "
              "about Z that compress the flange. beta = %.1f mm (Wagner, "
              "shear centre at the flange). The flange in compression "
              "buckles at a %.2f times higher moment than the stem in "
              "compression; with POU_D_E both would be %.0f N m (no Wagner "
              "term)." % (T43_BETA * 1e3, T43_NEG / -T43_POS,
                          _mcr_pair(T43_ILAT, 0.0, T43_J, 0.0, L43)[0])),
    Case("BU-43b", GROUP, "Lateral-torsional buckling, T beam, stem in "
         "compression (POU_D_TG)", "buckling_3d", lambda: build_bu43(-1.0),
         [Check("factor (stem in compression)", _pos_min,
                ref=T43_POS / M43, tol=0.02, unit="-", source=SRC43),
          Check("factor of the reversed load (flange in compression)",
                _neg_min, ref=T43_NEG / M43, tol=0.02, unit="-",
                source=SRC43)],
         general=TG,
         note="BU-43 with the end moments reversed: the free end of the "
              "stem is in compression."),
    Case("BU-44", GROUP, "Lateral-torsional buckling, C beam bent about "
         "the minor axis, flange tips in compression (POU_D_TG)",
         "buckling_3d", build_bu44,
         [Check("factor (flange tips in compression)", _pos_min,
                ref=C44_POS / M44, tol=0.03, unit="-", source=SRC43),
          Check("factor of the reversed load (web in compression)",
                _neg_min, ref=C44_NEG / M44, tol=0.02, unit="-",
                source=SRC43)],
         general=TG,
         note="C 100 x 50 x 6 mm (web at +Z), L = 4 m, 40 POU_D_TG, fork "
              "supports, end moments 1000 N m about Y (Mecway's V, the "
              "minor axis) that put the web in tension. beta = %.1f mm "
              "(shear centre beyond the web). A linear buckling check of "
              "the shear-centre and Wagner terms along W: in practice a C "
              "bent about its minor axis does not buckle laterally (the "
              "in-plane bending governs)." % (C44_BETA * 1e3)),
    Case("BU-44b", GROUP, "Lateral-torsional buckling, C beam bent about "
         "the minor axis, web in compression (POU_D_TG)", "buckling_3d",
         lambda: build_bu44(-1.0),
         [Check("factor (web in compression)", _pos_min,
                ref=-C44_NEG / M44, tol=0.02, unit="-", source=SRC43),
          Check("factor of the reversed load (flange tips in compression)",
                _neg_min, ref=-C44_POS / M44, tol=0.03, unit="-",
                source=SRC43)],
         general=TG,
         note="BU-44 with the end moments reversed."),
]


# ------------------------------------------------------------------
# BU-43c: the T beam against a shell model in Mecway (second reference)
# ------------------------------------------------------------------
# Shell model (build_tee_shell; not a bridge case): the T on its centre
# lines, quad4 shells, flange plate at the flange centre line, stem plate
# from the stem tip (y = 0) to that line, L = 4 m (at 2 m the stem in
# compression would buckle locally at about the same factor: outstand
# 95 x 10 mm, k = 0.65 for the stress gradient, EN 1993-1-5 table 4.2).
# End moments as nodal forces of the linear stress M (y - y_c)/I over the
# end sections (consistent loads of the plate edges); fork supports: Y and
# Z fixed at every node of both end sections (the section cannot twist or
# move sideways, warping free), X at one node. The shell model has no
# Wagner or shear-centre input, so it checks the formula and its sign
# independently of the beam element.
# Mecway 34 headless (mw_solve.py, own solver, 29 Oct 2026), smallest
# factor, flange in compression / stem in compression (end moments
# reversed), 100 / 200 / 400 elements along the beam (10 across each
# plate): 27.944 / 27.257 / 27.081 and 20.720 / 20.337 / 20.228
# (Richardson about 27.02 and 20.18); the formula with the section of the
# shell model (tee_shell_ref: centre-line plates, J = sum b t^3/3) gives
# 27.72 and 20.65: the shells are 2.5% lower (probably the distortion of
# the section, which the beam theory leaves out; NOT verified).
# Code-Aster's DKT cannot be used for this model: its RIGI_GEOM only has
# the out-of-plane terms of each plate (R3.07.03 par. 4.6), so the
# in-plane displacement of the stem gets no geometric stiffness; the same
# model through the bridge gives 18.76 and -7.77 with spurious in-plane
# modes (KNOWN_BUGS 132).
MW_T43C = (27.080705962484, 20.2283397825036)
L43C = 4.0
T43C_POS, T43C_NEG = _mcr_pair(T43_ILAT, T43_IW, T43_J, T43_BETA, L43C)


def _tee_shell(dims):
    """(rects, y of the flange centre line) of the shell model."""
    a, tw, tf, d = dims
    yf = d + tf / 2
    return [(-a / 2, a / 2, d, d + tf), (-tw / 2, tw / 2, 0.0, yf)], yf


def tee_shell_ref(dims, length):
    """((M_cr > 0, M_cr < 0), y_c) of the shell model (M > 0: flange in
    tension)."""
    a, tw, tf, d = dims
    rects, yf = _tee_shell(dims)
    area, cx, cy, ixx, iyy, wag = _rect_section(rects)
    beta = wag / iyy - 2 * (yf - cy)
    j = (a * tf ** 3 + yf * tw ** 3) / 3
    i_w = (tf ** 3 * a ** 3 / 4 + tw ** 3 * yf ** 3) / 36
    return _mcr_pair(ixx, i_w, j, beta, length), cy


def build_tee_shell(dims, length, nx, moment=M43):
    """T beam of shells along X, flange at +Y; the end moments (-M at x =
    0, +M at x = L about Z) compress the flange. Reference model for
    Mecway (Model.write, then TestFiles/Tools/mw_solve.py)."""
    a, tw, tf, d = dims
    rects, yf = _tee_shell(dims)
    yc = tee_shell_ref(dims, length)[1]
    m = Model("B30", attrs={"maxmode": 8, "shift": 1})
    m.elset("Flens", "MatF")
    m.elset("Lijf", "MatL")
    fl = quadmesh(m, "Flens", nx, 10, lambda u, v: (u * length, yf,
                                                     -a / 2 + v * a))
    st = quadmesh(m, "Lijf", nx, 10, lambda u, v: (u * length, v * yf, 0.0))
    for name, t in (("MatF", tf), ("MatL", tw)):
        m.mat(name, '<geometric type="Plate" thickness="%g mm" />' % (t * 1e3),
              STEEL, DENS)

    def coord(n):
        return m.nodes[n - 1]

    # consistent nodal loads of sigma = y - y_c on the edge segments
    weights = {}
    for side in ("u0", "u1"):
        out = weights.setdefault(side, {})
        for grid, along, t in ((fl, 2, tf), (st, 1, tw)):
            nodes = sorted(grid["nodes"][side], key=lambda n: coord(n)[along])
            for n0, n1 in zip(nodes[:-1], nodes[1:]):
                p0, p1 = coord(n0), coord(n1)
                h = math.sqrt(sum((p1[i] - p0[i]) ** 2 for i in range(3)))
                s0, s1 = p0[1] - yc, p1[1] - yc
                out[n0] = out.get(n0, 0.0) + t * h * (2 * s0 + s1) / 6
                out[n1] = out.get(n1, 0.0) + t * h * (s0 + 2 * s1) / 6
    for side, sign in (("u0", 1.0), ("u1", -1.0)):
        w = weights[side]
        scale = sum(f * (coord(n)[1] - yc) for n, f in w.items())
        name = "Eind%s" % side
        m.node_selection(name, sorted(w))
        for comp in ("<x>0</x><y>1</y><z>0</z>", "<x>0</x><y>0</y><z>1</z>"):
            m.add('<displacement selection="%s"><value>0 mm</value>%s'
                  '</displacement>' % (name, comp))
        for k, n in enumerate(sorted(w)):
            sel = "F%s_%d" % (side, k)
            m.node_selection(sel, [n])
            m.add('<force selection="%s"><x>%r N</x><y>0 N</y><z>0 N</z>'
                  '</force>' % (sel, sign * moment * w[n] / scale))
    m.node_selection("Axiaal", [m.node(0.0, 0.0, 0.0)])
    m.add('<displacement selection="Axiaal"><value>0 mm</value><x>1</x>'
          '<y>0</y><z>0</z></displacement>')
    return m


SRC43C = ("Mecway 34 headless, T of quad4 shells (build_tee_shell, 400 x 20 "
          "elements, own solver)")
TESTS.append(Case(
    "BU-43c", GROUP, "Lateral-torsional buckling, T beam L = 4 m, against "
    "a shell model in Mecway (POU_D_TG)", "buckling_3d",
    lambda: build_bu43(1.0, L43C),
    [Check("factor (flange in compression)", _pos_min,
           ref=-T43C_NEG / M43, tol=0.02, unit="-", source=SRC43),
     Check("factor of the reversed load (stem in compression)", _neg_min,
           ref=-T43C_POS / M43, tol=0.02, unit="-", source=SRC43),
     Check("factor (flange in compression) vs shells", _pos_min,
           ref=MW_T43C[0], tol=0.03, unit="-", in_series=False,
           source=SRC43C),
     Check("factor of the reversed load vs shells", _neg_min,
           ref=-MW_T43C[1], tol=0.03, unit="-", in_series=False,
           source=SRC43C + ", end moments reversed")],
    general=TG,
    note="BU-43 with L = 4 m. Second reference: the same T as a shell model "
         "in Mecway 34 (no Wagner or shear-centre input), %.2f / %.2f, "
         "ratio %.2f (formula %.2f)." % (
             MW_T43C[0], MW_T43C[1], MW_T43C[0] / MW_T43C[1],
             T43C_NEG / -T43C_POS)))
