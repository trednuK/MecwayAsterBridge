# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_orthotropic (Python 2.7 and 3, without Mecway and
# Code-Aster): Mecway's Orthotropic / Stiffness matrix / Compliance matrix
# XML -> ELAS_ORTH constants (major Poisson ratios, nu_wu -> NU_LN), a
# coupled matrix refused, the material frame from U/V/angle, the nautical
# angles of AFFE_CARA_ELEM MASSIF ANGL_REP (rebuilt with Code-Aster's
# rotation matrix), grouping of elements and the scope check. The results
# of a run: TestFiles/Verificatie (OR-01 .. ).
#
#   python tests/test_bridge_orthotropic.py

from __future__ import print_function

import math
import os
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_orthotropic as bo  # noqa: E402
bo.log = _log

FAILS = []


def _xml(text):
    """Element from XML text; UTF-8 bytes, which IronPython's ElementTree
    needs for non-ASCII characters (CPython accepts them too)."""
    if not isinstance(text, bytes):
        text = text.encode("utf-8")
    return ET.fromstring(text)


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL: " + msg)


def close(a, b, tol=1e-9):
    if isinstance(a, (tuple, list)):
        return all(close(x, y, tol) for x, y in zip(a, b))
    return abs(a - b) <= tol * max(1.0, abs(b))


ORTHO = ('<mechanical type="Orthotropic" youngsmodulusu="100 GPa" '
         'youngsmodulusv="20 GPa" youngsmodulusw="10 GPa" '
         'poissonratiouv="0.3" poissonratiovw="0.2" poissonratiowu="0.05" '
         'shearmodulusuv="7 GPa" shearmodulusvw="4 GPa" '
         'shearmoduluswu="5 GPa" thermalexpansionu="1e-6 1/K" '
         'thermalexpansionv="2e-6 1/K" thermalexpansionw="3e-6 1/K" />')


def _compliance(o):
    """6x6 compliance in Mecway's order from ELAS_ORTH constants."""
    s = [[0.0] * 6 for _i in range(6)]
    s[0][0], s[1][1], s[2][2] = 1 / o["E_L"], 1 / o["E_T"], 1 / o["E_N"]
    s[0][1] = s[1][0] = -o["NU_LT"] / o["E_L"]
    s[0][2] = s[2][0] = -o["NU_LN"] / o["E_L"]
    s[1][2] = s[2][1] = -o["NU_TN"] / o["E_T"]
    # Mecway's order of rows 4..6: VW, WU, UV (measured, S13 findings)
    s[3][3], s[4][4], s[5][5] = 1 / o["G_TN"], 1 / o["G_LN"], 1 / o["G_LT"]
    return s


def _inv6(a):
    """Gauss-Jordan inverse (test helper)."""
    n = 6
    m = [list(r) + [1.0 if i == j else 0.0 for j in range(n)]
         for i, r in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        piv = m[c][c]
        m[c] = [x / piv for x in m[c]]
        for r in range(n):
            if r != c:
                f = m[r][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [r[n:] for r in m]


def _matrix_xml(kind, mat, unit):
    pre = "c" if kind == "StiffnessMatrix" else "s"
    return '<mechanical type="{0}" {1} />'.format(kind, " ".join(
        '{0}{1}{2}="{3!r} {4}"'.format(pre, i + 1, j + 1, mat[i][j], unit)
        for i in range(6) for j in range(i, 6)))


def test_orthotropic():
    md = {"skipped_loads": []}
    p = bo.parse(_xml(ORTHO), _xml(
        u'<density type="Simple" density="1500 kg/m³" />'),
        "Orthotropic", "O", md)
    o = p["ortho"]
    check(close([o[k] for k in ("E_L", "E_T", "E_N", "NU_LT", "NU_TN",
                                "G_LT", "G_LN", "G_TN")],
                [100e9, 20e9, 10e9, 0.3, 0.2, 7e9, 5e9, 4e9]),
          "constants: {0}".format(o))
    # nu_wu = -eps_u / eps_w (stress in W) -> NU_LN = nu_wu E_L / E_N
    check(close(o["NU_LN"], 0.05 * 100 / 10), "NU_LN: {0}".format(o))
    check(close(p["alpha"], (1e-6, 2e-6, 3e-6)) and p["rho"] == 1500.0,
          "alpha/rho: {0}".format(p))
    txt = bo.elas_text(p, thermal=True)
    check(txt.startswith("ELAS_ORTH=_F(E_L=100000000000.0") and
          "ALPHA_N=3e-06" in txt and "RHO=1500.0" in txt, txt)
    check("ALPHA" not in bo.elas_text(p, thermal=False), "ALPHA without "
          "thermal stress")
    # not positive definite (nu_uv too large) -> ERROR, None
    del LOG[:]
    bad = _xml(ORTHO.replace('poissonratiouv="0.3"',
                                      'poissonratiouv="3"'))
    check(bo.parse(bad, None, "Orthotropic", "Bad", md) is None and
          any(l.startswith("ERROR: Material 'Bad'") for l in LOG),
          "not positive definite: {0}".format(LOG))


def test_matrices():
    md = {"skipped_loads": []}
    ref = bo.parse(_xml(ORTHO), None, "Orthotropic", "O",
                   md)["ortho"]
    s = _compliance(ref)
    c = _inv6(s)
    for kind, mat, unit, scale in (
            ("StiffnessMatrix", c, "GPa", 1e-9),
            ("ComplianceMatrix", s, u"m²/N", 1.0)):
        m = [[x * scale for x in row] for row in mat]
        p = bo.parse(_xml(_matrix_xml(kind, m, unit)), None, kind,
                     kind, md)
        check(p is not None and all(close(p["ortho"][k], ref[k], 1e-7)
                                    for k in ref),
              "{0}: {1} vs {2}".format(kind, p and p["ortho"], ref))
        check(p is None or p["alpha"] == (0.0, 0.0, 0.0), "alpha " + kind)
    # a coupling term -> ERROR (Code-Aster has no 3D anisotropy)
    del LOG[:]
    c2 = [[x * 1e-9 for x in row] for row in c]
    c2[0][3] = c2[3][0] = 1.0
    check(bo.parse(_xml(_matrix_xml("StiffnessMatrix", c2, "GPa")),
                   None, "StiffnessMatrix", "Aniso", md) is None and
          any("c14" in l and l.startswith("ERROR") for l in LOG),
          "coupled matrix: {0}".format(LOG))


def _aster_axes(a, b, g):
    """Local axes of Code-Aster's nautical angles (rows of the matrix in
    code_aster/MacroCommands/observation_ops.py)."""
    a, b, g = (math.radians(x) for x in (a, b, g))
    ca, sa, cb, sb, cg, sg = (math.cos(a), math.sin(a), math.cos(b),
                              math.sin(b), math.cos(g), math.sin(g))
    return ((ca * cb, sa * cb, -sb),
            (ca * sb * sg - sa * cg, sa * sb * sg + ca * cg, cb * sg),
            (ca * sb * cg + sa * sg, sa * sb * cg - ca * sg, cb * cg))


def test_angles():
    cases = [((1, 0, 0), (0, 1, 0), 0.0), ((1, 1, 0), (-1, 1, 1), 0.0),
             ((0, 0.6, 0.8), (1, 0, 0), 0.0), ((0, 0, 1), (1, 0, 0), 0.0),
             ((0, 0, -1), (0, 1, 0), 0.0), ((1, 2, 3), (0, 0, 1), 0.7),
             ((-1, 0, 0), (0, 0, 1), -1.2)]
    for u, v, ang in cases:
        axes = bo.frame(u, v, ang)
        rebuilt = _aster_axes(*bo.angl_rep(axes))
        check(all(close(x, y, 1e-9) for x, y in zip(rebuilt, axes)),
              "angles of {0}: {1} vs {2}".format((u, v, ang), rebuilt, axes))
    # right-handed, U along the given vector, V in the U-V plane
    u, v, w = bo.frame((1, 1, 0), (0, 1, 0))
    check(close(u, (2 ** -0.5, 2 ** -0.5, 0)) and
          close(v, (-2 ** -0.5, 2 ** -0.5, 0)) and close(w, (0, 0, 1)),
          "frame: {0}".format((u, v, w)))
    check(bo.frame((1, 0, 0), (2, 0, 0)) is None, "parallel U and V")
    check(bo.frame(None, None) == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                                   (0.0, 0.0, 1.0)), "default frame")
    # Mecway does not solve only U or only V; an angle alone does nothing
    check(bo.frame((0, 1, 0), None) is None and
          bo.frame(None, (0, 0, 1)) is None, "only one vector")
    check(bo.frame(None, None, 0.5) == bo.frame(None, None), "angle alone")


def test_prepare_and_check():
    md = {"skipped_loads": []}
    props = bo.parse(_xml(ORTHO), None, "Orthotropic", "O", md)
    md.update({
        "materials": {"O": props, "Iso": {"E": 1.0, "NU": 0.0}},
        "elsets": {"Blok": "O", "Staal": "Iso"},
        "mesh_elements": [(1, "hex8", [], "Blok"), (2, "hex8", [], "Blok"),
                          (3, "tet4", [], "Blok"), (4, "hex8", [], "Staal")],
        "elem_u_axes": {2: (1.0, 1.0, 0.0), 4: (0.0, 1.0, 0.0)},
        "elem_v_axes": {2: (-1.0, 1.0, 0.0)},
        "solid_orientations": {3: ((1.0, 1.0, 0.0), (0.0, 1.0, 0.0), 0.0)},
        "elset_modelisations": {"Blok": "3D", "Staal": "3D"}})
    out = bo.prepare(md)
    groups = dict(out)
    check(len(out) == 2 and md["extra_ma_groups"]["BRORI1"] == [1] and
          md["extra_ma_groups"]["BRORI2"] == [2, 3] and
          close(groups["BRORI2"], (45.0, 0.0, 0.0)),
          "groups: {0} {1}".format(out, md.get("extra_ma_groups")))
    ent = bo.massif_entries(md)
    check(ent[1].strip() == "_F(GROUP_MA='BRORI2', ANGL_REP=(45.0, 0.0, "
          "0.0)),", "entry: {0}".format(ent))
    check(bo.check(md, {"solver_command": "MECA_STATIQUE"}), "linear ok")
    # only a U vector on an orthotropic solid -> ERROR, None
    md2 = dict(md)
    md2["elem_v_axes"] = {}
    md2["solid_orientations"] = {}
    del md2["extra_ma_groups"]
    del LOG[:]
    check(bo.prepare(md2) is None and any(
        l.startswith("ERROR: Element orientation of 1 solid") for l in LOG),
        "U only: {0}".format(LOG))
    del LOG[:]
    check(not bo.check(md, {"solver_command": "STAT_NON_LINE"}) and
          any("S13c" in l for l in LOG), "nonlinear refused: {0}".format(LOG))
    md["elset_modelisations"]["Blok"] = "DKT"
    del LOG[:]
    check(not bo.check(md, {"solver_command": "MECA_STATIQUE"}) and
          any("S13b" in l for l in LOG), "shell refused: {0}".format(LOG))
    check(bo.check(md, {"solver_command": "THER_LINEAIRE"}), "thermal ok")
    md["elset_modelisations"]["Blok"] = "3D"
    check(bo.check(md, {"solver_command": "CALC_MODES",
                        "type_resu": "MODE_FLAMB"}), "buckling ok")
    check(not bo.check(md, {"solver_command": "CALC_MODES",
                            "phenomene": "ACOUSTIQUE"}), "acoustic refused")


if __name__ == "__main__":
    test_orthotropic()
    test_matrices()
    test_angles()
    test_prepare_and_check()
    if FAILS:
        print("{0} FAIL(S)".format(len(FAILS)))
        sys.exit(1)
    print("OK: orthotropic and matrix materials, frame and ANGL_REP, "
          "orientation groups, scope")
