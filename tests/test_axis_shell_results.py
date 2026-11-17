# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 3 with numpy, as in the job) of the stresses and
# section forces of axisymmetric shells (COQUE_AXIS, STAPPENPLAN S44e
# piece 2):
#   - aster_results_export: the frame [t, Z, t x Z] per point of a SEG3 cell
#     (tangent from the shape functions, cell order end, end, middle), the
#     rotation of the meridional stress, SIXZ left out, von Mises, the
#     levels (u1 = SUP, the face with Mecway's pressure arrows) and the
#     section forces (momentu = MXX);
#   - bridge_to_aster: POST_CHAMP EXTR_COQUE without SIEQ on the shells,
#     res_efs in S30, no res_efs (INFO) in L30.
# Verification in Code-Aster: PL-60 .. PL-66 (TestFiles/Verificatie/
# tests_vlak_2d_coque.py).
#
#   python tests/test_axis_shell_results.py

from __future__ import print_function

import io
import math
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import numpy as np  # noqa: E402
import aster_results_export as are  # noqa: E402
import bridge_utils as u  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402
from bridge_to_aster import generate_AsterSolver_files  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []
_MODEL = os.path.join(_HERE, "..", "TestFiles", "Verificatie", "modellen",
                      "PL-60.liml")
_MODEL_L30 = os.path.join(os.path.dirname(_MODEL), "PL-65.liml")


def check(cond, what):
    print("{0}: {1}".format("OK  " if cond else "FAIL", what))
    if not cond:
        _FAILED.append(what)


def test_frames():
    # straight cell along +Y at X = 1 (cell order: end 1, end 2, middle)
    xyz = np.array([[1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [1.0, 0.5, 0.0]])
    fr = are._axis_frames(xyz, [0, 1, 2])
    check(fr is not None and len(fr) == 3 and
          all(np.allclose(r[:, 0], [0, 1, 0]) and
              np.allclose(r[:, 1], [0, 0, 1]) and
              np.allclose(r[:, 2], [1, 0, 0]) for r in fr),
          "straight SEG3 along +Y: t = +Y, hoop = Z, t x Z = +X (SUP side)")
    # curved cell: quarter circle (1, 0) -> (0, 1), middle on the arc
    c = 0.5 * math.sqrt(2.0)
    xyz = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [c, c, 0.0]])
    fr = are._axis_frames(xyz, [0, 1, 2])
    t1 = -1.5 * xyz[0] - 0.5 * xyz[1] + 2.0 * xyz[2]
    t2 = 0.5 * xyz[0] + 1.5 * xyz[1] - 2.0 * xyz[2]
    check(np.allclose(fr[0][:, 0], t1 / np.linalg.norm(t1)) and
          np.allclose(fr[1][:, 0], t2 / np.linalg.norm(t2)) and
          np.allclose(fr[2][:, 0], [-c, c, 0.0]),
          "curved SEG3: tangent per point, not the chord")
    check(are._axis_frames(xyz, [0, 1]) is None and
          are._axis_frames(np.zeros((3, 3)), [0, 1, 2]) is None,
          "no frame for a SEG2 or a degenerate cell")


class _Fields(object):
    """Just enough of aster_results_export._Fields for _shell_tensor and
    _axis_forces: one field of one result."""

    def __init__(self, cmps, vals):
        self.cmps, self.vals, self.data = list(cmps), np.asarray(vals), {}

    def get(self, rkey, field, elno):
        return self.cmps, self.vals, np.ones_like(self.vals, dtype=bool)


def test_rotation():
    c = 0.5 * math.sqrt(2.0)
    r = np.column_stack(([-c, c, 0.0], [0, 0, 1], np.cross([-c, c, 0.0],
                                                           [0, 0, 1])))
    plan = {"rows": np.array([0]), "rot": np.array([r])}
    f = _Fields(["SIXX", "SIYY", "SIZZ", "SIXZ"], [[2.0, 5.0, 0.0, 7.0]])
    m = are._shell_tensor(f, plan, "res_inf", "SIGM_ELNO", are._AXIS_SIGM_IJ)
    # xx, yy, zz, xy, yz, zx
    check(np.allclose(m[0], [1.0, 1.0, 5.0, -1.0, 0.0, 0.0]),
          "meridian at 45 degrees: xx = yy = s/2, xy = -s/2, zz = hoop, "
          "SIXZ left out")
    vm = are._von_mises_columns(m)
    check(np.allclose(vm[0, 0], math.sqrt(4.0 + 25.0 - 10.0)),
          "von Mises of meridional 2 and hoop 5 (no transverse shear)")
    check(are._AXIS_LEVELS[0] == ("sup", "u") and
          are._AXIS_LEVELS[2] == ("inf", "b"),
          "u1 from SUP (the side U x Z, where the pressure acts), b1 from "
          "INF")
    f = _Fields(["NXX", "NYY", "NXY", "MXX", "MYY", "MXY"],
                [[1.0, 2.0, 0.0, 3.0, 4.0, 0.0]])
    out = are._axis_forces(f, {"rows": np.array([0])}, "res_efs")
    check(np.allclose(out[0], [1.0, 2.0, 3.0, 4.0]),
          "forceperlengthu/v = NXX/NYY, momentu/v = MXX/MYY")


def test_named_and_padded():
    """AXIS continuum: radial/axial/hoop/shearstressrz after stresszx with
    the ids and values of stressxx/yy/zz/xy (own _Var objects); 2D contact:
    contactpressure on every node of the model elements, 0 elsewhere."""
    from collections import OrderedDict
    ids = np.array([1, 2, 3], dtype="<i4")
    vals = dict((c, np.array([1.0, 2.0, 3.0]) * (k + 1))
                for k, c in enumerate(("xx", "yy", "zz", "xy", "yz", "zx")))
    v = OrderedDict(("stress" + c, are._Var("stress" + c, False, ids,
                                             (lambda c: lambda f: vals[c])(c)))
                    for c in ("xx", "yy", "zz", "xy", "yz", "zx"))
    v["vonmises"] = are._Var("vonmises", False, ids, lambda f: vals["xx"])
    are._axis_named_stresses(v)
    names = list(v)
    check(names[6:10] == ["radialstress", "axialstress", "hoopstress",
                          "shearstressrz"] and names[-1] == "vonmises",
          "aliases right after stresszx ({0})".format(names))
    check(np.allclose(v["hoopstress"].getter(None), vals["zz"]) and
          v["hoopstress"] is not v["stresszz"] and
          v["hoopstress"].ids is v["stresszz"].ids,
          "hoopstress = stresszz, own _Var with the same ids")
    model = {"elements": {1: ("quad4", [1, 2, 5, 4]),
                          2: ("quad4", [2, 3, 6, 5])}}
    c = OrderedDict([("contactpressure", are._Var(
        "contactpressure", False, np.array([2, 5], dtype="<i4"),
        lambda f: np.array([7.0, 8.0])))])
    are._pad_contact(c, model)
    cp = c["contactpressure"]
    check(list(cp.ids) == [1, 2, 3, 4, 5, 6] and
          np.allclose(cp.getter(None), [0, 7, 0, 0, 8, 0]),
          "contactpressure padded with 0 on every node")
    # element-node aliases, contactstate and a step without values
    e = OrderedDict([("stresszz", are._Var("stresszz", True, ids,
                                             lambda f: vals["zz"]))])
    are._axis_named_stresses(e)
    check("hoopstress" in e and e["hoopstress"].element and
          np.allclose(e["hoopstress"].getter(None), vals["zz"]),
          "element-node hoopstress alias")
    c = OrderedDict([("contactstate", are._Var(
        "contactstate", False, np.array([5], dtype="<i4"),
        lambda f: np.array([1.0]))), ("contactpressure", are._Var(
            "contactpressure", False, np.array([5], dtype="<i4"),
            lambda f: None))])
    are._pad_contact(c, model)
    check(np.allclose(c["contactstate"].getter(None), [0, 0, 0, 0, 1, 0])
          and c["contactpressure"].getter(None) is None,
          "contactstate padded; a step without values stays None")
    check(are._bridge_alias("hoopstress") and
          are._bridge_alias("meridionalstressb1") and
          not are._bridge_alias("stresszz"),
          "bridge alias names (a formula with such a name wins)")


def _comm(tmp, analysis, fields):
    work = tempfile.mkdtemp(dir=tmp)
    liml = os.path.join(work, "model.liml")
    model = _MODEL if analysis == "lin_static_3d" else _MODEL_L30
    with io.open(model, encoding="utf-8") as f:
        s = f.read()
    # a von Mises failure criterion, so that safety_factor applies
    k = s.index("<mechanical ")
    s = (s[:k] + '<failure type="VonMises" tensilestrength="250 MPa" />'
         + s[k:])
    with io.open(liml, "w", encoding="utf-8") as f:
        f.write(s)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = analysis
    u.CONFIG_BRIDGE["analyses"][analysis]["fields"] = list(fields)
    md = extract_aster_data_from_liml(liml)
    mail = os.path.join(work, "m.mail")
    ok = (md is not None and write_mesh(mail, md) and
          generate_AsterSolver_files(work, md, mail, "test.resu"))
    check(bool(ok), "{0}: files generated".format(analysis))
    if not ok:
        return "", ""
    comm = io.open(os.path.join(work, "study.comm"), encoding="utf-8").read()
    log = io.open(os.path.join(work, "bridge_log.txt"),
                  encoding="utf-8").read()
    return comm, log


def test_comm(tmp):
    fields = ["displacements", "stresses", "vonmises", "reactions",
              "shell_stresses", "shell_forces", "safety_factor", "strain"]
    comm, log = _comm(tmp, "lin_static_3d", fields)
    check("NIVE_COUCHE='SUP'" in comm and "NIVE_COUCHE='INF'" in comm and
          "SIEQ_NOEU" not in comm.split("res_sup = POST_CHAMP")[-1]
          .split("export_results")[0],
          "S30: EXTR_COQUE SUP/MOY/INF, no SIEQ on the axisymmetric shells")
    check("res_efs = CALC_CHAMP" in comm and "'axis_shells': True" in comm,
          "S30: res_efs and plane={... 'axis_shells': True}")
    check("safety_factor: not for axisymmetric shells" in log and
          "strain: not for axisymmetric shells" in log,
          "safety_factor WARNING and strain INFO")
    comm, log = _comm(tmp, "nonlin_static_3d", fields)
    check("res_efs = CALC_CHAMP" not in comm and
          "shell_forces: on axisymmetric shells" in log,
          "L30: no EFGE_ELNO (DVP_1 in te0185), INFO")

    # the ParaView script of the revolved view: only for an axisymmetric
    # run with vtu_export (bridge_to_aster._write_axis_paraview)
    def axis_script(model, vtu):
        u.CONFIG_BRIDGE["vtu_export"] = vtu
        work = tempfile.mkdtemp(dir=tmp)
        liml = os.path.join(work, "model.liml")
        shutil.copy(model, liml)
        u.CONFIG_BRIDGE["work_dir"] = work
        u.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
        md = extract_aster_data_from_liml(liml)
        mail = os.path.join(work, "m.mail")
        ok = (md is not None and write_mesh(mail, md) and
              generate_AsterSolver_files(work, md, mail, "test.resu"))
        return bool(ok) and os.path.isfile(os.path.join(
            work, u.run_name("_paraview_axis.py")))
    plate = os.path.join(os.path.dirname(_MODEL), "PL-01-n1.liml")
    check(axis_script(_MODEL, True) and not axis_script(_MODEL, False) and
          not axis_script(plate, True),
          "paraview_axis.py: axisymmetric + vtu_export only (not without "
          "vtu_export, not for C_PLAN)")


def main():
    saved = dict(u.CONFIG_BRIDGE)
    saved_vtu = u.CONFIG_BRIDGE.get("vtu_export", False)
    saved_fields = dict((k, list(v.get("fields", [])))
                        for k, v in u.CONFIG_BRIDGE["analyses"].items())
    tmp = tempfile.mkdtemp(prefix="bridge_axis_shell_")
    try:
        test_frames()
        test_rotation()
        test_named_and_padded()
        test_comm(tmp)
    finally:
        for k, v in saved_fields.items():
            u.CONFIG_BRIDGE["analyses"][k]["fields"] = v
        u.CONFIG_BRIDGE["vtu_export"] = saved_vtu
        u.CONFIG_BRIDGE.clear()
        u.CONFIG_BRIDGE.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
