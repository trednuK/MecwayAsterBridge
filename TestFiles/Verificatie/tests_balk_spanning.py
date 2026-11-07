# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Stress over beam sections from the section forces of Code-Aster (STAPPENPLAN
S41, Scripts/bridge_section_stress.py). Explanation: docs/Verificatie.md
(LS-97). Every reference is by hand, statics plus beam theory; the numbers
against SectionField are in tests/test_bridge_section_stress.py.

Cantilevers along X, V = Y, W = Z, E = 210 GPa, nu = 0.3, L = 1 m, 8 elements.

- LS-97a: T section (general section with SECTIE-VORM), POU_D_E, tip force
  along the symmetry axis, so no torque. At the clamp sigma = M c / I, at the
  neutral axis tau = V Q / (I t); at the tip the stress is shear only.
  Also the shells: the same numbers at the ring points.
- LS-97b: U section, POU_D_TG, #ASTER-SECTIE, tip force through the shear
  centre (force at the centroid plus a torque -EY F): T_S = 0, so the shear is
  V Q / (I t) in the web. A wrong sign of the torque term shows here.
- LS-97c: the same force at the centroid without the torque: T_S = EY F, the
  torsion shear of the open section dominates, T_S t / J in the flange.
- LS-97d: Mecway's I profile without an outline, POU_D_E, force along V.
- LS-97e: Mecway's C profile without an outline, POU_D_E, force along V.
- LS-97f: Mecway's L profile: force along V, a principal axis of the section.
- LS-97g: T section, one element, line load (FORCE_POUTRE): the end values of
  EFGE_ELNO are exact, so the stress at the clamp is that of q L^2 / 2.
- LS-97h: T section, 4 POU_D_TG, own weight: the element values carry the known
  error, V is the mid-element value and M is q h^2 / 12 too small at the clamp
  (measured in MecwayAdvancedBeamAnalysis, tests/test_beam_aster.py). Stated
  here so that a change of this behaviour shows.
- LS-97i: the T of LS-97a in steps (nonlinear static, load ramp): every time
  step its own stress.
- LS-97j: the T on POU_D_T. LS-97k: on 4 line3, also at the middle node of
  the element. LS-97l: on POU_D_T_GD, small load: SIEF_ELNO is constant in an
  element, so that the stress at the clamp is that of the middle of the first
  element, 15/16 of M c / I with 8 elements.
"""
import glob
import math
import os

from verif_lib import Case, Check, Model
from tests_balken_grote_rotaties import _ramp

GROUP = "Lineair statisch"
LENGTH = 1.0
FORCE = 1000.0
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7850 kg/m³" />'
TG = {"elem_beam": "POU_D_TG"}
RHO_G = 7850.0 * 9.80665

# T: flange 100 x 8 mm at the bottom, web 6 x 92 mm, symmetric about W
T_B, T_TF, T_TW, T_H = 0.100, 0.008, 0.006, 0.092
T_A = T_B * T_TF + T_TW * T_H
T_Z = (T_B * T_TF * T_TF / 2 + T_TW * T_H * (T_TF + T_H / 2)) / T_A
T_IVV = (T_B * T_TF ** 3 / 12 + T_B * T_TF * (T_TF / 2 - T_Z) ** 2 +
         T_TW * T_H ** 3 / 12 + T_TW * T_H * (T_TF + T_H / 2 - T_Z) ** 2)
T_IWW = (T_TF * T_B ** 3 + T_H * T_TW ** 3) / 12
T_J = (T_B * T_TF ** 3 + T_H * T_TW ** 3) / 3
T_C = T_TF + T_H - T_Z              # neutral axis to the web tip
T_Q = T_TW * T_C ** 2 / 2           # first moment of the web above the axis
# The outline, with two points where the neutral axis crosses the web
T_LOOP = [(-T_B / 2, -T_Z), (T_B / 2, -T_Z), (T_B / 2, T_TF - T_Z),
          (T_TW / 2, T_TF - T_Z), (T_TW / 2, 0.0), (T_TW / 2, T_C),
          (-T_TW / 2, T_C), (-T_TW / 2, 0.0), (-T_TW / 2, T_TF - T_Z),
          (-T_B / 2, T_TF - T_Z)]

# U: height 100, flanges 50 x 8, web 6 mm; flanges towards +V, web along W
U_H, U_B, U_TF, U_TW = 0.100, 0.050, 0.008, 0.006
U_WEB = U_H - 2 * U_TF
U_A = 2 * U_B * U_TF + U_TW * U_WEB
U_V = (2 * U_B * U_TF * U_B / 2 + U_TW * U_WEB * U_TW / 2) / U_A
U_IVV = (U_B * U_H ** 3 - (U_B - U_TW) * U_WEB ** 3) / 12
U_IWW = (2 * (U_TF * U_B ** 3 / 12 + U_B * U_TF * (U_B / 2 - U_V) ** 2) +
         U_WEB * U_TW ** 3 / 12 + U_WEB * U_TW * (U_TW / 2 - U_V) ** 2)
U_J = 2.2046016926022174e-08        # FE value of the section, not thin-walled
U_EY = 0.03193220491300617          # the same; shear centre at -EY from G
U_Q = U_B * U_TF * (U_H - U_TF) / 2 + U_TW * (U_WEB / 2) ** 2 / 2
U_LOOP = [(-U_V, -U_H / 2), (U_B - U_V, -U_H / 2),
          (U_B - U_V, -U_H / 2 + U_TF), (U_TW - U_V, -U_H / 2 + U_TF),
          (U_TW - U_V, 0.0), (U_TW - U_V, U_H / 2 - U_TF),
          (U_B - U_V, U_H / 2 - U_TF), (U_B - U_V, U_H / 2),
          (-U_V, U_H / 2), (-U_V, 0.0)]
U_ASTER = ("** ASTER-SECTIE U: A={0!r}, IY={1!r}, IZ={2!r}, JX={3!r}, AY=2.0, "
           "AZ=1.5, EY={4!r}, EZ=0.0, JG=5e-10, IYR2=0, IZR2=0".format(
               U_A, U_IVV, U_IWW, U_J, U_EY))

# I 100/50/10/8 mm, Mecway's profile: height along V
I_H, I_B, I_TF, I_TW = 0.100, 0.050, 0.010, 0.008
I_IWW = (I_B * I_H ** 3 - (I_B - I_TW) * (I_H - 2 * I_TF) ** 3) / 12
I_Q = (I_B * I_TF * (I_H - I_TF) / 2 +
       I_TW * ((I_H - 2 * I_TF) / 2) ** 2 / 2)
IPROF = '<geometric type="I" ia="100 mm" ib="50 mm" ic="10 mm" id="8 mm" />'

# C 100 x 50 x 6 mm, Mecway's profile: height along V
C_H, C_B, C_T = 0.100, 0.050, 0.006
C_IWW = (C_B * C_H ** 3 - (C_B - C_T) * (C_H - 2 * C_T) ** 3) / 12
CPROF = '<geometric type="C" ca="50 mm" cb="100 mm" cc="6 mm" cd="6 mm" />'

# L 80 x 50 x 8 mm, Mecway's profile, in the drawing
LPROF = '<geometric type="L" la="80 mm" lb="50 mm" lc="8 mm" />'
L_POINTS = [(0.0, 0.0), (0.080, 0.0), (0.080, 0.008), (0.008, 0.008),
            (0.008, 0.050), (0.0, 0.050)]


def _general(area, ivv, iww, j):
    return ('<geometric type="UniformGeneralSection" area="%r m²" '
            'iyy="%r m⁴" izz="%r m⁴" torsionconstant="%r m⁴" '
            'perimeter="0.3 m" />' % (area, ivv, iww, j))


def _shape(name, loop, area):
    flat = " ".join("%.12g" % c for p in loop for c in p)
    return ("** SECTIE-VORM %s: N=%d, A=%r\n** SECTIE-VORM %s: P=%s\n" %
            (name, len(loop), area, name, flat))


def _beam(section, custom="", tip="", moment="", n=8, extra=None,
          analysis="S30", timesteps=None, line3=False):
    m = Model(analysis, timesteps=timesteps)
    m.elset("Balk", "Mat")
    if line3:
        nids = [m.node(LENGTH * i / float(2 * n), 0, 0)
                for i in range(2 * n + 1)]
        eids = [m.elem("Balk", "line3", [nids[2 * i], nids[2 * i + 1],
                                         nids[2 * i + 2]]) for i in range(n)]
    else:
        nids = [m.node(LENGTH * i / float(n), 0, 0) for i in range(n + 1)]
        eids = [m.elem("Balk", "line2", [nids[i], nids[i + 1]])
                for i in range(n)]
    m.mat("Mat", section, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    m.node_selection("Tip", [nids[-1]])
    if tip:
        m.add('<force selection="Tip">%s</force>' % tip)
    if moment:
        m.add('<moment selection="Tip">%s</moment>' % moment)
    if extra:
        extra(m, eids)
    if custom:
        m.add(u"<ccxmodeldefinition>%s</ccxmodeldefinition>" % custom)
    return m


def _force(y=0.0, z=0.0):
    return "<x>0 N</x><y>%r N</y><z>%r N</z>" % (y, z)


def build_t(n=8):
    return _beam(_general(T_A, T_IVV, T_IWW, T_J), _shape("Mat", T_LOOP, T_A),
                 tip=_force(z=FORCE), n=n)


def _build_u(torque):
    return _beam(_general(U_A, U_IVV, U_IWW, U_J).replace("Mat", "U"),
                 _shape("Mat", U_LOOP, U_A) + U_ASTER.replace("U:", "Mat:"),
                 tip=_force(z=FORCE),
                 moment="<x>%r N.m</x><y>0 N.m</y><z>0 N.m</z>" % torque)


def build_u_shear_centre():
    return _build_u(-U_EY * FORCE)


def build_u_centroid():
    return _build_u(0.0)


def build_i():
    return _beam(IPROF, tip=_force(y=FORCE))


def build_c():
    return _beam(CPROF, tip=_force(y=FORCE))


def build_l():
    return _beam(LPROF, tip=_force(y=FORCE))


Q_LINE = 2000.0


def _line_load(m, eids):
    m.element_selection("Last", eids)
    m.add(u'<linepressure selection="Last"><x>0 N/m</x><y>0 N/m</y>'
          u'<z>%r N/m</z></linepressure>' % Q_LINE)


def build_line():
    return _beam(_general(T_A, T_IVV, T_IWW, T_J), _shape("Mat", T_LOOP, T_A),
                 n=1, extra=_line_load)


def _gravity(m, _eids):
    m.add(u'<gravity><x>0 m/s²</x><y>0 m/s²</y><z>9.80665 m/s²</z></gravity>')


def _t_section(**keys):
    return _beam(_general(T_A, T_IVV, T_IWW, T_J), _shape("Mat", T_LOOP, T_A),
                 **keys)


def build_steps():
    return _t_section(analysis="L30", tip="<x>0 N</x><y>0 N</y>%s" %
                      _ramp("z", FORCE, "N"),
                      timesteps={"timeperiod": "1 s", "stepsize": "0.5 s"})


def build_line3():
    return _t_section(tip=_force(z=FORCE), n=4, line3=True)


def build_gd():
    return _t_section(analysis="L30", tip="<x>0 N</x><y>0 N</y>%s" %
                      _ramp("z", 10.0, "N"),
                      timesteps={"timeperiod": "1 s", "stepsize": "1 s"})


def build_weight():
    return _beam(_general(T_A, T_IVV, T_IWW, T_J), _shape("Mat", T_LOOP, T_A),
                 n=4, extra=_gravity)


# ------------------------------------------------------------------
# reading
# ------------------------------------------------------------------
def _clamp(r, name, time=None):
    """Value at the clamp: element 1, its first node."""
    return r.elem(name, time)[1][0]


def _tip(r, name):
    """Value at the free end: last element, its last node."""
    values = r.elem(name)
    return values[max(values)][-1]


def _shells(r):
    """What the shells get: {name: {(end of the beam, v, w): value}} for the
    first element at its clamp (end 0) and the last at its tip (end 1), by the
    functions of bridge_results_liml and bridge_section_view on this run, with
    the table of the job. Writing them into a .liml: tests/
    test_bridge_section_results.py and the open in Mecway."""
    import bridge_from_liml
    import bridge_results_liml as brl
    import bridge_section_view as sv
    import bridge_utils
    folder = os.path.dirname(r.mess)
    liml = [p for p in glob.glob(os.path.join(folder, "*.liml"))][0]
    keep = bridge_utils.CONFIG_BRIDGE["work_dir"]
    bridge_utils.CONFIG_BRIDGE["work_dir"] = folder
    try:
        md = bridge_from_liml.extract_aster_data_from_liml(liml)
        shapes = sv.current_shapes(
            sv.parse_shapes(md["aster_custom"]["section_shapes"]), md)
        view = sv.build_view(md, shapes, warn_directions=False)
        tables = brl.section_tables(liml, view, md)
    finally:
        bridge_utils.CONFIG_BRIDGE["work_dir"] = keep
    if not tables:
        raise ValueError("no table of this section")

    def ends(names):
        rows = [r.elem(n) for n in names]
        return dict((b["eid"], tuple(tuple(row[b["eid"]][k - 1] for row in rows)
                                     for k in b["element_nodes"]))
                    for b in view["beams"])

    points = sv.shear_points(view, tables)
    forces = ends(("tensileforce", "bendingmomv", "bendingmomw"))
    shear = ends(("sheary", "shearz", "torsion"))
    sigma = []
    for index, end, v, w in view["origin"]:
        beam = view["beams"][index]
        sigma.append(sv.stress_from_forces(
            forces[beam["eid"]][end][0], forces[beam["eid"]][end][1],
            forces[beam["eid"]][end][2],
            sv.section_values(md, beam["material"]), v, w))
    wanted = list(range(len(view["nids"])))
    tau, vm = sv.shell_shear(view, points, tables, shear, sigma, wanted)
    last = len(view["beams"]) - 1
    out = {"sigma": {}, "tau": {}, "vm": {}}
    for pos, (index, end, v, w) in enumerate(view["origin"]):
        if (index, end) in ((0, 0), (last, 1)):
            key = (end, round(v, 7), round(w, 7))
            out["sigma"][key] = sigma[pos]
            out["tau"][key] = tau[pos]
            out["vm"][key] = vm[pos]
    return out


def _at(r, name, end, v, w):
    return _shells(r)[name][(end, round(v, 7), round(w, 7))]


def _largest(r, name, end):
    return max(abs(x) for k, x in _shells(r)[name].items() if k[0] == end)


# ------------------------------------------------------------------
# references
# ------------------------------------------------------------------
T_SIGMA = FORCE * LENGTH * T_C / T_IVV
T_TAU = FORCE * T_Q / (T_IVV * T_TW)
U_SIGMA = FORCE * LENGTH * (U_H / 2) / U_IVV
U_TAU = FORCE * U_Q / (U_IVV * U_TW)
I_SIGMA = FORCE * LENGTH * (I_H / 2) / I_IWW
I_TAU = FORCE * I_Q / (I_IWW * I_TW)
C_SIGMA = FORCE * LENGTH * (C_H / 2) / C_IWW


def _l_reference():
    """Largest |sigma| of the L at the clamp under F along V, by hand. The
    beam's V lies on Mecway's principal axis (default V = Y), so that this is
    plain bending about W: M v / I, with the axes from Mohr's circle, the angle
    wrapped into (-45, 45] degrees as Mecway does (measured, section_profiles)."""
    pairs = _pairs(L_POINTS)
    a = sum((p[0] * q[1] - q[0] * p[1]) / 2 for p, q in pairs)
    cx = sum((p[0] + q[0]) * (p[0] * q[1] - q[0] * p[1]) / 6
             for p, q in pairs) / a
    cy = sum((p[1] + q[1]) * (p[0] * q[1] - q[0] * p[1]) / 6
             for p, q in pairs) / a
    pts = [(p[0] - cx, p[1] - cy) for p in L_POINTS]
    pairs = _pairs(pts)
    ixx = sum((p[1] ** 2 + p[1] * q[1] + q[1] ** 2) *
              (p[0] * q[1] - q[0] * p[1]) / 12 for p, q in pairs)
    iyy = sum((p[0] ** 2 + p[0] * q[0] + q[0] ** 2) *
              (p[0] * q[1] - q[0] * p[1]) / 12 for p, q in pairs)
    ixy = sum((p[0] * q[1] + 2 * p[0] * p[1] + 2 * q[0] * q[1] + q[0] * p[1]) *
              (p[0] * q[1] - q[0] * p[1]) / 24 for p, q in pairs)
    t = 0.5 * math.atan2(-2.0 * ixy, ixx - iyy)
    while t > math.pi / 4.0:
        t -= math.pi / 2.0
    while t <= -math.pi / 4.0:
        t += math.pi / 2.0
    v = [-math.sin(t) * x + math.cos(t) * y for x, y in pts]
    i_w = (iyy * math.sin(t) ** 2 + ixx * math.cos(t) ** 2 -
           2.0 * ixy * math.sin(t) * math.cos(t))
    return FORCE * LENGTH * max(abs(x) for x in v) / i_w


def _pairs(points):
    return [(points[i - 1], points[i]) for i in range(len(points))]


TESTS = [
    Case("LS-97a", GROUP, "Stress over a T section, general section with an "
         "outline: tip force along the symmetry axis (POU_D_E)", "lin_static_3d",
         build_t,
         [Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=T_SIGMA, tol=1e-6, unit="Pa", source="M c / I"),
          Check("von Mises at the clamp",
                lambda r: _clamp(r, "beamvonmisesmax"), ref=T_SIGMA, tol=2e-3,
                unit="Pa", source="M c / I, free web tip"),
          Check("tau at the clamp", lambda r: _clamp(r, "beamtaumax"),
                ref=T_TAU, tol=0.03, unit="Pa", source="V Q / (I t)"),
          Check("von Mises at the tip", lambda r: _tip(r, "beamvonmisesmax"),
                ref=math.sqrt(3.0) * T_TAU, tol=0.03, unit="Pa",
                source="sqrt(3) V Q / (I t), M = 0"),
          Check("shells: sigma at the web tip, compression",
                lambda r: _at(r, "sigma", 0, T_TW / 2, T_C),
                ref=-T_SIGMA, tol=1e-6, unit="Pa",
                source="M c / I; F along +Z pushes the +Z side of the clamp "
                       "into compression"),
          Check("shells: largest sigma = the beam maximum",
                lambda r: _largest(r, "sigma", 0) /
                _clamp(r, "beamsixxabsmax"), ref=1.0, tol=1e-6, unit="-",
                source="the same point"),
          Check("shells: von Mises at the web tip",
                lambda r: _at(r, "vm", 0, T_TW / 2, T_C),
                ref=T_SIGMA, tol=2e-3, unit="Pa", source="M c / I"),
          Check("shells: tau at the neutral axis, web edge",
                lambda r: _at(r, "tau", 0, T_TW / 2, 0.0),
                ref=T_TAU, tol=0.03, unit="Pa", source="V Q / (I t)"),
          Check("shells: tau at the tip, neutral axis",
                lambda r: _at(r, "tau", 1, -T_TW / 2, 0.0),
                ref=T_TAU, tol=0.03, unit="Pa", source="V Q / (I t)")],
         note="T 100 x 8 + 92 x 6 mm, F = 1000 N along W, L = 1 m, 8 "
              "elements. Force through the centroid and the shear centre."),
    Case("LS-97b", GROUP, "Stress over a U section: force through the shear "
         "centre, T_S = 0 (POU_D_TG)", "lin_static_3d", build_u_shear_centre,
         [Check("torque MT = -EY F", lambda r: _clamp(r, "torsion"),
                ref=-U_EY * FORCE, tol=1e-6, unit="N m", source="statics"),
          Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=U_SIGMA, tol=1e-6, unit="Pa", source="M c / I"),
          Check("tau = shear only", lambda r: _clamp(r, "beamtaumax"),
                ref=U_TAU, tol=0.06, unit="Pa",
                source="V Q / (I t) in the web"),
          Check("shells: tau on the web, neutral axis, outside",
                lambda r: _at(r, "tau", 0, -U_V, 0.0),
                ref=U_TAU, tol=0.06, unit="Pa", source="V Q / (I t)"),
          Check("shells: tau on the web, neutral axis, inside",
                lambda r: _at(r, "tau", 0, U_TW - U_V, 0.0),
                ref=U_TAU, tol=0.06, unit="Pa", source="V Q / (I t)")],
         general=TG,
         note="U 100 x 50 x 8/6 mm, #ASTER-SECTIE with EY = 31.93 mm, F = "
              "1000 N along W at the centroid plus T = -EY F. T_S = MT + EY "
              "VZ = 0, so that both web faces carry the same shear. A wrong "
              "sign of the term gives 2 EY F, a shear of about 25 MPa."),
    Case("LS-97c", GROUP, "Stress over a U section: force through the "
         "centroid, T_S = EY F (POU_D_TG)", "lin_static_3d", build_u_centroid,
         [Check("torque MT = 0", lambda r: _clamp(r, "torsion"), ref=0.0,
                tol_abs=1e-6, unit="N m", source="statics"),
          Check("tau = torsion in the flange",
                lambda r: _clamp(r, "beamtaumax"),
                ref=U_EY * FORCE * U_TF / U_J, tol=0.10, unit="Pa",
                source="T_S t / J"),
          Check("shells: the two web faces together",
                lambda r: _at(r, "tau", 0, -U_V, 0.0) +
                _at(r, "tau", 0, U_TW - U_V, 0.0),
                ref=2.0 * U_EY * FORCE * U_TW / U_J, tol=0.10, unit="Pa",
                source="2 T_S t / J: torsion +/- on the faces, larger than "
                       "the shear, so that the shear cancels in the sum"),
          Check("shells: the difference of the two web faces",
                lambda r: abs(_at(r, "tau", 0, -U_V, 0.0) -
                              _at(r, "tau", 0, U_TW - U_V, 0.0)),
                ref=2.0 * U_TAU, tol=0.06, unit="Pa",
                source="2 V Q / (I t)")],
         general=TG,
         note="As LS-97b without the torque. No warping stress: the "
              "longitudinal stress is M c / I (see the limits in the user "
              "guide)."),
    Case("LS-97d", GROUP, "Stress over Mecway's I profile, no outline "
         "(POU_D_E)", "lin_static_3d", build_i,
         [Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=I_SIGMA, tol=1e-6, unit="Pa", source="M c / I, about W"),
          Check("tau at the clamp", lambda r: _clamp(r, "beamtaumax"),
                ref=I_TAU, tol=0.03, unit="Pa", source="V Q / (I t)")],
         note="I 100/50/10/8 mm, F = 1000 N along V: V along the height."),
    Case("LS-97e", GROUP, "Stress over Mecway's C profile, no outline "
         "(POU_D_E)", "lin_static_3d", build_c,
         [Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=C_SIGMA, tol=1e-6, unit="Pa", source="M c / I, about W")],
         note="C 100 x 50 x 6 mm, F = 1000 N along V: V along the height."),
    Case("LS-97f", GROUP, "Stress over Mecway's L profile, no outline "
         "(POU_D_E)", "lin_static_3d", build_l,
         [Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=_l_reference(), tol=1e-5, unit="Pa",
                source="M v / I in the principal axes")],
         note="L 80 x 50 x 8 mm, F = 1000 N along Y = V, which is Mecway's "
              "principal axis: the section lies turned in the model."),
    Case("LS-97g", GROUP, "Stress under a line load, one element: end values "
         "are exact (POU_D_E)", "lin_static_3d", build_line,
         [Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=Q_LINE * LENGTH ** 2 / 2 * T_C / T_IVV, tol=1e-6, unit="Pa",
                source="q L^2 / 2 c / I"),
          Check("|sigma| at the tip", lambda r: _tip(r, "beamsixxabsmax"),
                ref=0.0, tol_abs=1.0, unit="Pa", source="M = 0")],
         note="T section of LS-97a, q = 2000 N/m, FORCE_POUTRE on one "
              "element: EFGE_ELNO gives the end values themselves."),
    Case("LS-97h", GROUP, "Stress under own weight on POU_D_TG: the element "
         "error stays visible", "lin_static_3d", build_weight,
         [Check("|sigma| at the clamp, q L^2/2 - q h^2/12",
                lambda r: _clamp(r, "beamsixxabsmax"),
                ref=(RHO_G * T_A) * (LENGTH ** 2 / 2 - LENGTH ** 2 / 16 / 12) *
                T_C / T_IVV, tol=1e-5, unit="Pa",
                source="Measured behaviour of POU_D_TG under PESANTEUR")],
         general=TG,
         note="T section, 4 elements. V is the mid-element value and M lacks "
              "q h^2 / 12; a finer mesh takes it away (user guide)."),
    Case("LS-97i", GROUP, "Stress over a T section per time step (nonlinear "
         "static, load ramp)", "nonlin_static_3d", build_steps,
         [Check("|sigma| at the clamp, t = 0.5",
                lambda r: _clamp(r, "beamsixxabsmax", 0.5), ref=T_SIGMA / 2,
                tol=1e-5, unit="Pa", source="half the load"),
          Check("|sigma| at the clamp, t = 1",
                lambda r: _clamp(r, "beamsixxabsmax", 1.0), ref=T_SIGMA,
                tol=1e-5, unit="Pa", source="M c / I"),
          Check("tau at the clamp, t = 0.5",
                lambda r: _clamp(r, "beamtaumax", 0.5), ref=T_TAU / 2,
                tol=0.03, unit="Pa", source="half the load")],
         note="T section of LS-97a, two steps."),
    Case("LS-97j", GROUP, "Stress over a T section on POU_D_T", "lin_static_3d",
         build_t,
         [Check("|sigma| at the clamp", lambda r: _clamp(r, "beamsixxabsmax"),
                ref=T_SIGMA, tol=1e-6, unit="Pa", source="M c / I"),
          Check("tau at the clamp", lambda r: _clamp(r, "beamtaumax"),
                ref=T_TAU, tol=0.03, unit="Pa", source="V Q / (I t)")],
         general={"elem_beam": "POU_D_T"},
         note="As LS-97a, Timoshenko beam."),
    Case("LS-97k", GROUP, "Stress over a T section on line3", "lin_static_3d",
         build_line3,
         [Check("|sigma| at the clamp, first node",
                lambda r: r.elem("beamsixxabsmax")[1][0],
                ref=T_SIGMA, tol=1e-5, unit="Pa", source="M c / I"),
          Check("|sigma| at the middle node of element 1",
                lambda r: r.elem("beamsixxabsmax")[1][1],
                ref=T_SIGMA * 7.0 / 8.0, tol=1e-5, unit="Pa",
                source="M at x = L/8"),
          Check("|sigma| at the end node of element 1",
                lambda r: r.elem("beamsixxabsmax")[1][2],
                ref=T_SIGMA * 3.0 / 4.0, tol=1e-5, unit="Pa",
                source="M at x = L/4"),
          Check("shells: sigma at the web tip",
                lambda r: _at(r, "sigma", 0, T_TW / 2, T_C),
                ref=-T_SIGMA, tol=1e-5, unit="Pa", source="M c / I")],
         note="T section, 4 line3 in Mecway's node order: end, middle, end."),
    Case("LS-97l", GROUP, "Stress over a T section on POU_D_T_GD, small load",
         "nonlin_static_3d", build_gd,
         [Check("|sigma| at the clamp, value of mid-element",
                lambda r: _clamp(r, "beamsixxabsmax"),
                ref=T_SIGMA / 100.0 * 15.0 / 16.0, tol=1e-3, unit="Pa",
                source="M at x = L/16, 8 elements"),
          Check("the same value at both ends of the element",
                lambda r: r.elem("beamsixxabsmax")[1][1] /
                r.elem("beamsixxabsmax")[1][0], ref=1.0, tol=1e-9, unit="-",
                source="one integration point"),
          Check("tau at the clamp", lambda r: _clamp(r, "beamtaumax"),
                ref=T_TAU / 100.0, tol=0.04, unit="Pa",
                source="V Q / (I t)")],
         general={"elem_beam": "POU_D_T_GD"},
         note="F = 10 N: small deflection. Section forces from SIEF_ELNO, "
              "constant per element, so that the moment at a clamp is low by "
              "half an element."),
]
