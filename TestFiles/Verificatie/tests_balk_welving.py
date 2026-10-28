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
"""
import math
from verif_lib import Case, Check, Model, SCRIPTS
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
              "EZ = 29.33 mm and C_w = 4.058e-10 m^6 computed by the bridge "
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
         "L profile with EY = 40.96 mm (test 41.012), JG = 4.43988e-11 m^6 "
         "and IYR2 = 8.4848e-8 m^5 (bridge_warping)."))


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
         "estimate) instead of 1. The bridge's EZ = 40.96 mm, JG = "
         "4.43988e-11 m^6 and IZR2 = 8.4848e-8 m^5 equal the test's EY, JG "
         "and IYR2 within 0.12% (the test's axes y/z are the bridge's "
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


def build_ls90():
    m = Model("S30")
    m.elset("Balk", "Mat")
    nids = _line(m, (0, 0, 0), (L90, 0, 0), 20)
    m.mat("Mat", BO.IPROF, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    m.add('<moment selection="Tip"><x>%g N.m</x><y>0 N.m</y><z>0 N.m</z>'
          '</moment>' % T90)
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
