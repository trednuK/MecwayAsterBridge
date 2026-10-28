# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_orthotropic.py
#
# Responsibility: Mecway's Orthotropic, Stiffness matrix and Compliance
# matrix materials on solid elements (linear static, modal, buckling) ->
# DEFI_MATERIAU ELAS_ORTH, with the
# material axes U, V, W of Mecway's element orientation as AFFE_CARA_ELEM
# MASSIF ANGL_REP per group of elements with the same orientation
# (STAPPENPLAN S13a).
#
#   parse(mech_node, dens_node, mech_type, mat_name, model_data)
#                       material -> props with "ortho" (bridge_from_liml)
#   prepare(model_data) orientation groups BRORI<n> (extra_ma_groups) and
#                       model_data["massif_orientations"]
#                       (bridge_to_aster.generate_AsterSolver_files)
#   check(model_data, analysis)  scope: ERROR and False outside it
#   elas_text(props, thermal)    "ELAS_ORTH=_F(...)" for DEFI_MATERIAU
#   massif_entries(model_data)   MASSIF entries of AFFE_CARA_ELEM
#   export_arg(model_data, fields)  axes for Mecway's "stress in element
#                       coordinates" (aster_results_export, S13d)
#
# MECWAY (manual v34 par. 8.5 and 7.4.2, attribute names in mecway.exe,
# semantics measured with headless Mecway 34 solves of cubes under an
# imposed homogeneous strain, 28 Oct 2026, STAPPENPLAN S13 findings):
#   <mechanical type="Orthotropic" youngsmodulusu/v/w poissonratiouv/vw/wu
#     shearmodulusuv/vw/wu [thermalexpansionu/v/w] />
#   <mechanical type="StiffnessMatrix" c11 c12 .. c66 />  (upper triangle)
#   <mechanical type="ComplianceMatrix" s11 s12 .. s66 />
#   - Poisson ratios are major: nu_uv = -eps_v / eps_u under stress in U
#     (manual par. 8.5), nu_vw likewise, nu_wu = -eps_u / eps_w;
#   - matrix rows/columns 1..6 = UU, VV, WW, VW, WU, UV with engineering
#     shear strains (measured: c14 couples eps_UU with gamma_VW, c16 with
#     gamma_UV; the stiffness and the compliance matrix alike), although the
#     Orthotropic tab lists the shear moduli as 12 (UV), 23 (VW), 31 (WU);
#   - an element with only a U or only a V vector, or with U parallel to V,
#     is not solved by Mecway (no solution); an angle without vectors has
#     no effect (global axes);
#   - material axes = the element axes U, V, W; for solids by default the
#     global X, Y, Z (manual par. 8.5).
#
# CODE-ASTER (catalogue defi_materiau.py and affe_cara_elem.py, v17.4):
#   ELAS_ORTH E_L, E_T, E_N, NU_LT, NU_LN, NU_TN, G_LT, G_LN, G_TN, RHO,
#   ALPHA_L/T/N; L, T, N = the local axes x, y, z of MASSIF ANGL_REP
#   (alpha, beta, gamma) in degrees, nautical angles (U4.42.01 par. 13.3;
#   without MASSIF (L, T, N) = (X, Y, Z), par. 13.6, whose example
#   ANGL_REP = (0, 0, -90) -> (L, T, N) = (X, -Z, Y) fixes the signs): local
#   x = (cos a cos b, sin a cos b, -sin b) (code_aster/MacroCommands/
#   observation_ops.py, anglnaut and the matrix in its comment). NU_LT is
#   the major ratio like Mecway's (U4.43.01 par. 3.5.2: under tension along
#   L, eps_T = -NU_LT sig_L / E_L; NU_LN, NU_TN likewise; checked by the
#   verification OR-01). There is no general anisotropic elasticity for
#   volume elements in DEFI_MATERIAU (only ELAS_ORTH / ELAS_ISTR; ELAS_COQUE
#   is for shells): a stiffness or compliance matrix is translated only if
#   it is orthotropic in the element axes (all coupling terms zero),
#   otherwise ERROR.
#
# Compatible with IronPython 2.7.9 (Mecway scripting engine).

import math
from collections import OrderedDict

from bridge_utils import log, tr, parse_and_convert

TYPES = ("Orthotropic", "StiffnessMatrix", "ComplianceMatrix")
SOLIDS = frozenset(["hex8", "hex20", "tet4", "tet10", "pyr5", "pyr13",
                    "wedge6", "wedge15"])

# Index pairs of Mecway's matrix rows/columns 1..6 (measured, see header):
# 1 = UU, 2 = VV, 3 = WW, 4 = VW, 5 = WU, 6 = UV, engineering shear strain.
_VOIGT = ((0, 0), (1, 1), (2, 2), (1, 2), (2, 0), (0, 1))
# Relative size of a coupling term (normal-shear or shear-shear) that still
# counts as zero when a matrix is checked for orthotropy.
_ORTHO_TOL = 1.0e-9


# ------------------------------------------------------------------
# Small linear algebra (no NumPy in IronPython)
# ------------------------------------------------------------------
def _inv3(a):
    """Inverse of a 3x3 matrix (list of rows) or None if singular."""
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
           - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    scale = max(abs(x) for row in a for x in row) or 1.0
    if abs(det) <= 1.0e-14 * scale ** 3:
        return None
    c = [[0.0] * 3 for _i in range(3)]
    for i in range(3):
        for j in range(3):
            r = [k for k in range(3) if k != j]
            s = [k for k in range(3) if k != i]
            minor = a[r[0]][s[0]] * a[r[1]][s[1]] - a[r[0]][s[1]] * a[r[1]][s[0]]
            c[i][j] = (-1.0) ** (i + j) * minor / det
    return c


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _unit(v):
    n = _norm(v)
    return tuple(x / n for x in v) if n > 0.0 else None


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _fmt(v):
    """Shortest of %.15g / %.17g that reads back as the same double, so the
    .comm is the same from CPython and IronPython (whose repr(0.3) is
    0.29999999999999999)."""
    v = float(v)
    text = "%.15g" % v
    if float(text) != v:
        text = "%.17g" % v
    if "e" not in text and "." not in text and "n" not in text:
        text += ".0"
    return text


# ------------------------------------------------------------------
# Material
# ------------------------------------------------------------------
def _matrix(mech_node, prefix, quantity):
    """Symmetric 6x6 from the attributes <prefix>ij (i <= j, Mecway writes
    the upper triangle); a missing attribute is 0."""
    m = [[0.0] * 6 for _i in range(6)]
    for i in range(6):
        for j in range(i, 6):
            val = mech_node.get("{0}{1}{2}".format(prefix, i + 1, j + 1))
            v = parse_and_convert(val, quantity) if val else 0.0
            m[i][j] = m[j][i] = v
    return m


def _engineering(c, mat_name, kind):
    """Engineering constants from an orthotropic 6x6 stiffness (kind
    'stiffness') or compliance ('compliance') matrix in Mecway's order;
    (dict, None) or (None, reason)."""
    big = max(abs(c[i][i]) for i in range(6)) or 1.0
    coupled = [(i + 1, j + 1) for i in range(6) for j in range(i + 1, 6)
               if (i >= 3 or j >= 3) and abs(c[i][j]) > _ORTHO_TOL * big]
    if coupled:
        return None, tr(
            u"de matrix koppelt normaal- en schuifrekken of schuifrekken "
            u"onderling (termen {0} niet nul); Code-Aster heeft voor "
            u"volume-elementen alleen orthotrope elasticiteit (ELAS_ORTH)",
            u"the matrix couples normal and shear strains or shear strains "
            u"with each other (terms {0} not zero); Code-Aster only has "
            u"orthotropic elasticity (ELAS_ORTH) for volume elements").format(
                ", ".join("{0}{1}{2}".format(
                    "c" if kind == "stiffness" else "s", i, j)
                    for i, j in coupled[:6]))
    normal = [row[:3] for row in c[:3]]
    if kind == "stiffness":
        s = _inv3(normal)
        if s is None or min(c[3][3], c[4][4], c[5][5]) <= 0.0:
            return None, tr(u"de stijfheidsmatrix is niet inverteerbaar of "
                            u"niet positief definiet",
                            u"the stiffness matrix cannot be inverted or is "
                            u"not positive definite")
        # (G_LT, G_TN, G_LN) = (UV, VW, WU) = Mecway's 66, 44, 55
        g = (c[5][5], c[3][3], c[4][4])
    else:
        s = normal
        if min(c[3][3], c[4][4], c[5][5]) <= 0.0:
            return None, tr(u"de compliantiematrix is niet positief "
                            u"definiet",
                            u"the compliance matrix is not positive "
                            u"definite")
        g = (1.0 / c[5][5], 1.0 / c[3][3], 1.0 / c[4][4])
    if min(s[0][0], s[1][1], s[2][2]) <= 0.0:
        return None, tr(u"de matrix is niet positief definiet",
                        u"the matrix is not positive definite")
    e = [1.0 / s[k][k] for k in range(3)]
    return OrderedDict([
        ("E_L", e[0]), ("E_T", e[1]), ("E_N", e[2]),
        # major ratios: nu_ij = -s_ji / s_ii = -s_ij E_i
        ("NU_LT", -s[0][1] * e[0]), ("NU_LN", -s[0][2] * e[0]),
        ("NU_TN", -s[1][2] * e[1]),
        ("G_LT", g[0]), ("G_LN", g[2]), ("G_TN", g[1])]), None


def _positive_definite(ortho):
    """True if the orthotropic compliance is positive definite (the 3x3
    normal block; shear moduli > 0)."""
    e = (ortho["E_L"], ortho["E_T"], ortho["E_N"])
    if min(e) <= 0.0 or min(ortho["G_LT"], ortho["G_LN"],
                            ortho["G_TN"]) <= 0.0:
        return False
    s = [[1.0 / e[0], -ortho["NU_LT"] / e[0], -ortho["NU_LN"] / e[0]],
         [-ortho["NU_LT"] / e[0], 1.0 / e[1], -ortho["NU_TN"] / e[1]],
         [-ortho["NU_LN"] / e[0], -ortho["NU_TN"] / e[1], 1.0 / e[2]]]
    m1 = s[0][0]
    m2 = s[0][0] * s[1][1] - s[0][1] ** 2
    m3 = (s[0][0] * (s[1][1] * s[2][2] - s[1][2] ** 2)
          - s[0][1] * (s[0][1] * s[2][2] - s[1][2] * s[0][2])
          + s[0][2] * (s[0][1] * s[1][2] - s[1][1] * s[0][2]))
    return m1 > 0.0 and m2 > 0.0 and m3 > 0.0


def _error(model_data, mat_name, mech_type, why):
    model_data.setdefault("skipped_loads", []).append(
        tr(u"materiaal '{0}' ({1})", u"material '{0}' ({1})").format(
            mat_name, mech_type))
    log(tr(u"ERROR: Materiaal '{0}' ({1}): {2}. Het materiaal wordt NIET "
           u"vertaald.",
           u"ERROR: Material '{0}' ({1}): {2}. The material is NOT "
           u"translated.").format(mat_name, mech_type, why))


def parse(mech_node, dens_node, mech_type, mat_name, model_data):
    """Mecway material of a type in TYPES -> props for
    model_data["materials"], or None (ERROR logged). props has "ortho"
    (ELAS_ORTH values in SI, L/T/N = U/V/W), "alpha" (ALPHA_L/T/N), "rho",
    and "E"/"NU"/"Texp" as isotropic stand-ins for code that needs one
    value (largest modulus; only used outside the scope of check())."""
    if mech_type == "Orthotropic":
        def val(name, quantity):
            return parse_and_convert(mech_node.get(name, "0"), quantity)
        e_u = val("youngsmodulusu", "pressure")
        e_v = val("youngsmodulusv", "pressure")
        e_w = val("youngsmodulusw", "pressure")
        nu_uv = val("poissonratiouv", "dimensionless")
        nu_vw = val("poissonratiovw", "dimensionless")
        nu_wu = val("poissonratiowu", "dimensionless")
        ortho = OrderedDict([
            ("E_L", e_u), ("E_T", e_v), ("E_N", e_w),
            # Mecway's nu_wu = -eps_u / eps_w (stress in W) is the minor
            # ratio of the pair UW; ELAS_ORTH wants NU_LN = -eps_N / eps_L
            # (stress in L): NU_LN = nu_wu E_L / E_N (symmetry of the
            # compliance, manual par. 8.5).
            ("NU_LT", nu_uv), ("NU_LN", nu_wu * e_u / e_w if e_w else 0.0),
            ("NU_TN", nu_vw),
            ("G_LT", val("shearmodulusuv", "pressure")),
            ("G_LN", val("shearmoduluswu", "pressure")),
            ("G_TN", val("shearmodulusvw", "pressure"))])
        alpha = (val("thermalexpansionu", "inversetemp"),
                 val("thermalexpansionv", "inversetemp"),
                 val("thermalexpansionw", "inversetemp"))
        if not _positive_definite(ortho):
            _error(model_data, mat_name, mech_type, tr(
                u"de constanten geven geen positief definiete stijfheid "
                u"(een modulus <= 0 of te grote Poisson-getallen; Mecway "
                u"rekent dit ook niet)",
                u"the constants do not give a positive definite stiffness "
                u"(a modulus <= 0 or too large Poisson ratios; Mecway does "
                u"not solve this either)"))
            return None
    else:
        stiffness = mech_type == "StiffnessMatrix"
        c = _matrix(mech_node, "c" if stiffness else "s",
                    "pressure" if stiffness else "inverse_pressure")
        ortho, why = _engineering(c, mat_name,
                                  "stiffness" if stiffness else "compliance")
        if ortho is None:
            _error(model_data, mat_name, mech_type, why)
            return None
        # Mecway: no thermal expansion for anisotropic materials (message
        # in mecwayf.dll: "Thermal expansion is no longer supported for
        # anisotropic materials")
        alpha = (0.0, 0.0, 0.0)
    rho = parse_and_convert(dens_node.get("density", "0"), "density") \
        if dens_node is not None else 0.0
    props = {"E": max(ortho["E_L"], ortho["E_T"], ortho["E_N"]),
             "NU": ortho["NU_LT"], "Texp": max(alpha), "rho": rho,
             "ortho": ortho, "alpha": alpha, "mecway_type": mech_type}
    log("INFO: Material '{0}' ({1}) -> ELAS_ORTH {2}, ALPHA_L/T/N={3}, "
        "rho={4} kg/m3".format(
            mat_name, mech_type, ", ".join(
                "{0}={1:.6g}".format(k, v) for k, v in ortho.items()),
            alpha, rho))
    return props


def elas_text(props, thermal, rayleigh=None):
    """Keyword ELAS_ORTH=_F(...) for DEFI_MATERIAU (U4.43.01; catalogue
    defi_materiau.py v17.4). ALPHA_* only with thermal stress (like ELAS in
    bridge_to_aster._elas_args); AMOR_ALPHA/AMOR_BETA for Rayleigh damping in
    DYNA_NON_LINE (ELAS_ORTH has them too; AMOR_ALPHA = Mecway's beta,
    AMOR_BETA = Mecway's alpha, as in _elas_args)."""
    args = ["{0}={1}".format(k, _fmt(v)) for k, v in props["ortho"].items()]
    args.append("RHO={0}".format(_fmt(props.get("rho", 0.0))))
    if thermal:
        args += ["{0}={1}".format(k, _fmt(a)) for k, a in
                 zip(("ALPHA_L", "ALPHA_T", "ALPHA_N"), props["alpha"])]
    if rayleigh:
        args += ["AMOR_ALPHA={0}".format(_fmt(rayleigh["beta"])),
                 "AMOR_BETA={0}".format(_fmt(rayleigh["alpha"]))]
    return "ELAS_ORTH=_F({0})".format(", ".join(args))


def is_ortho(props):
    return bool(props and props.get("ortho"))


# ------------------------------------------------------------------
# Orientation
# ------------------------------------------------------------------
def frame(u, v, angle=0.0):
    """Material axes (U, V, W) as unit vectors from Mecway's U and V
    vectors (zero vector or None = not given) and the angle (rad): V is
    projected perpendicular to U and turned about U by the angle (manual
    v34 par. 7.4.2 and 8.5; measured, see the header). Neither vector: the
    global axes (an angle alone has no effect, as in Mecway). Returns None
    if only one vector is given or U is parallel to V (Mecway does not
    solve such a model)."""
    u = _unit(u) if u else None
    v = _unit(v) if v else None
    if u is None and v is None:
        return (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
    if u is None or v is None:
        return None
    vp = tuple(b - _dot(v, u) * a for a, b in zip(u, v))
    if _norm(vp) <= 1.0e-9:
        return None
    vp = _unit(vp)
    w = _cross(u, vp)
    if angle:
        c, s = math.cos(angle), math.sin(angle)
        vp, w = (tuple(c * a + s * b for a, b in zip(vp, w)),
                 tuple(-s * a + c * b for a, b in zip(vp, w)))
    return u, vp, w


def angl_rep(axes):
    """Nautical angles (alpha, beta, gamma) in degrees of the local frame
    axes = (x, y, z) unit vectors in global coordinates, like
    code_aster/MacroCommands/observation_ops.py anglnaut: alpha about Z,
    beta about the new Y (local x = (cos a cos b, sin a cos b, -sin b)),
    gamma about the new X."""
    xg, yg = axes[0], axes[1]
    nx = math.sqrt(xg[0] ** 2 + xg[1] ** 2)
    if nx < 1.0e-12:
        ar = 0.0
    else:
        ar = math.atan2(xg[1] / nx, xg[0] / nx)
    beta = math.atan2(-xg[2], nx)
    y1 = (-math.sin(ar), math.cos(ar), 0.0)
    gamma = math.atan2(_dot(xg, _cross(y1, yg)), _dot(y1, yg))
    return tuple(math.degrees(a) for a in (ar, beta, gamma))


def _elem_axes(model_data, eid):
    """(u, v, angle) of a solid element: an Element orientation card
    (bridge_orientation, solid_orientations) wins over the element
    attributes (as for beams); none = Mecway's default."""
    card = model_data.get("solid_orientations", {}).get(eid)
    if card is not None:
        return card
    u = model_data.get("elem_u_axes", {}).get(eid)
    v = model_data.get("elem_v_axes", {}).get(eid)
    angle = model_data.get("elem_angles", {}).get(eid, 0.0)
    return (u, v, angle)


def prepare(model_data):
    """Group the solid elements with an ELAS_ORTH material by material
    frame: model_data["massif_orientations"] = [(group, (a, b, g))] and the
    groups in model_data["extra_ma_groups"] (DEFI_GROUP); returns that
    list, or None after an ERROR (unusable orientation). Elements of
    other dimensions with such a material are reported by check()."""
    mats = model_data.get("materials", {})
    elsets = model_data.get("elsets", {})
    elem_elset = model_data.get("_elem_elset", {})
    groups = OrderedDict()
    frames = {}
    bad = []
    for eid, shape, _nodes, elset in model_data.get("mesh_elements", []):
        es = elem_elset.get(eid, elset)
        if shape not in SOLIDS or not is_ortho(mats.get(elsets.get(es))):
            continue
        u, v, angle = _elem_axes(model_data, eid)
        axes = frame(u, v, angle)
        if axes is None:
            bad.append(eid)
            continue
        key = tuple(round(a, 6) + 0.0 for a in angl_rep(axes))
        groups.setdefault(key, []).append(eid)
        frames.setdefault(key, axes)
    if bad:
        log(tr(u"ERROR: Element orientation van {0} volume-element(en) met "
               u"orthotroop materiaal ({1}): alleen een U- of alleen een "
               u"V-vector, of U evenwijdig aan V. Mecway rekent zo'n model "
               u"niet; geef U en een V-vector die niet evenwijdig is aan U.",
               u"ERROR: Element orientation of {0} solid element(s) with "
               u"orthotropic material ({1}): only a U or only a V vector, "
               u"or U parallel to V. Mecway does not solve such a model; "
               u"give U and a V vector that is not parallel to U.").format(
                   len(bad), ", ".join(str(e) for e in bad[:10]) +
                   (" ..." if len(bad) > 10 else "")))
        return None
    extra = model_data.setdefault("extra_ma_groups", OrderedDict())
    out = []
    for i, (key, eids) in enumerate(groups.items()):
        name = "BRORI{0}".format(i + 1)
        extra[name] = eids
        out.append((name, key))
    model_data["massif_orientations"] = out
    # axes per group for the field "stress in element coordinates"
    # (export_arg)
    model_data["massif_frames"] = [(frames[key], groups[key])
                                   for _name, key in out]
    if out:
        log("INFO: Orthotropic material axes: {0} group(s) of solid "
            "elements with the same orientation (AFFE_CARA_ELEM MASSIF "
            "ANGL_REP): {1}{2}.".format(len(out), ", ".join(
                "{0} {1} ({2} el.)".format(n, k, len(groups[k]))
                for n, k in out[:5]), " ..." if len(out) > 5 else ""))
        if len(out) > 1000:
            log(tr(u"WARNING: {0} verschillende materiaalorientaties "
                   u"(bijv. een formule per element): AFFE_CARA_ELEM wordt "
                   u"groot en traag.",
                   u"WARNING: {0} different material orientations (e.g. a "
                   u"formula per element): AFFE_CARA_ELEM becomes large and "
                   u"slow.").format(len(out)))
    return out


def export_arg(model_data, fields):
    """", solid_frames=[...]" for aster_results_export.export_results:
    the axes (rows U, V, W, 9 numbers) of the orthotropic solids with their
    element numbers as ranges, so that the job writes Mecway's "stress in
    element coordinates" (lamuu .. lamwu, S13d) with the field
    "stresses"; "" without orthotropic solids or without that field."""
    frames = model_data.get("massif_frames") or []
    if not frames or "stresses" not in (fields or []):
        return ""
    out = []
    for axes, eids in frames:
        ranges = []
        for eid in sorted(eids):
            if ranges and ranges[-1][1] == eid - 1:
                ranges[-1][1] = eid
            else:
                ranges.append([eid, eid])
        rows = tuple(float(_fmt(c)) for vec in axes for c in vec)
        out.append((rows, [tuple(r) for r in ranges]))
    log("INFO: Field 'stress in element coordinates' (lamuu .. lamwu) of "
        "the orthotropic solids is written with the stresses.")
    return ", solid_frames={0!r}".format(out)


def massif_entries(model_data):
    """MASSIF entries for AFFE_CARA_ELEM (catalogue affe_cara_elem.py
    v17.4: GROUP_MA + ANGL_REP, 3 angles in 3D, degrees)."""
    return ["        _F(GROUP_MA='{0}', ANGL_REP=({1}, {2}, {3})),"
            .format(name, _fmt(a), _fmt(b), _fmt(g))
            for name, (a, b, g) in model_data.get("massif_orientations", [])]


# ------------------------------------------------------------------
# Scope
# ------------------------------------------------------------------
# Analyses in which ELAS_ORTH with MASSIF is verified: linear static
# (OR-01 .. OR-06, OR-09), modal and linear buckling (CALC_MODES with
# TYPE_RESU DYNAMIQUE / MODE_FLAMB of the structure: OR-07, OR-08, OR-10),
# nonlinear static (RELATION ELAS, GREEN_LAGRANGE with large
# displacements: OR-12, OR-13) and implicit dynamics (OR-14).


def _supported(analysis):
    """True for linear static, modal and buckling of the structure (not the
    acoustic or vibro-acoustic CALC_MODES variants)."""
    cmd = analysis.get("solver_command")
    if cmd in ("MECA_STATIQUE", "STAT_NON_LINE"):
        return True
    if cmd == "DYNA_NON_LINE":
        # implicit only: the explicit critical time step estimates the
        # wave speed from one E and NU (_critical_time_step)
        return analysis.get("schema") not in ("DIFF_CENT", "TCHAMWA")
    return (cmd == "CALC_MODES" and not analysis.get("phenomene") and
            not analysis.get("vibroacoustic") and
            analysis.get("type_resu", "DYNAMIQUE") in ("DYNAMIQUE",
                                                       "MODE_FLAMB"))


def check(model_data, analysis):
    """ERROR (False) for an orthotropic/anisotropic material outside the
    verified scope: other element types than solids (STAPPENPLAN S13b),
    other analyses than linear static, modal and buckling (S13c). True
    without such materials."""
    mats = model_data.get("materials", {})
    elsets = model_data.get("elsets", {})
    ortho_sets = sorted(e for e, m in elsets.items()
                        if is_ortho(mats.get(m)))
    if not ortho_sets:
        return True
    solver_cmd = analysis.get("solver_command")
    import bridge_thermomech
    if str(solver_cmd or "").startswith("THER") and \
            not bridge_thermomech.enabled(model_data):
        return True     # thermal only: own materials (bridge_thermal)
    import bridge_failure
    names = ", ".join(bridge_failure.mecway_name(model_data, e)
                      for e in ortho_sets)
    ok = True
    mods = model_data.get("elset_modelisations", {})
    not_solid = sorted(bridge_failure.mecway_name(model_data, e)
                       for e in ortho_sets
                       if not str(mods.get(e, "3D")).startswith("3D"))
    if not_solid:
        log(tr(u"ERROR: Orthotroop/anisotroop materiaal op schalen, "
               u"membranen of balken (elset {0}) wordt nog niet vertaald "
               u"(alleen volume-elementen, STAPPENPLAN S13b). Gebruik op "
               u"deze elementen een isotroop materiaal.",
               u"ERROR: Orthotropic/anisotropic material on shells, "
               u"membranes or beams (elset {0}) is not translated yet "
               u"(solid elements only, STAPPENPLAN S13b). Use an isotropic "
               u"material on these elements.").format(", ".join(not_solid)))
        ok = False
    if not _supported(analysis):
        log(tr(u"ERROR: Orthotroop/anisotroop materiaal (elset {0}) wordt "
               u"nu alleen vertaald in Lineair en Niet-lineair statisch, "
               u"Modaal, Knik en impliciete Dynamica; andere analyses "
               u"(expliciet, modale basis, harmonisch, spectrum, keten "
               u"thermisch -> mechanisch, akoestiek) volgen (STAPPENPLAN "
               u"S13c).",
               u"ERROR: Orthotropic/anisotropic material (elset {0}) is "
               u"currently translated in Linear and Nonlinear static, Modal, "
               u"Buckling and implicit Dynamics only; other analyses "
               u"(explicit, mode superposition, harmonic, spectrum, thermal "
               u"-> mechanical chain, acoustics) follow (STAPPENPLAN "
               u"S13c).").format(names))
        ok = False
    return ok
