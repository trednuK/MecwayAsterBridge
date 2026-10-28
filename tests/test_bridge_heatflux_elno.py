# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 3 with numpy, as in the job) of the heat flux per
# element node (GitHub issue #8: Mecway formulas with qf.x/y/z):
#   - aster_results_export.FIELD_TABLE writes FLUX_ELNO as element-node
#     heatfluxx/y/z, _elem_magnitude_var adds heatfluxmag per element node;
#   - bridge_thermal: with a rotated mesh (flat shells outside Z = constant)
#     and volume elements, FLUX_ELNO of the volumes is rotated back too
#     (_elno_rotation); without volumes or without rotation nothing extra.
# Result formulas themselves (Solution > Formula): tests/test_bridge_formula.py.
# Model: TestFiles/Verificatie/modellen/TH-01a.liml (hex8 wall), plus a
# quad4 plate in the plane y = 0.05 for the rotated case.
#
#   python tests/test_bridge_heatflux_elno.py

from __future__ import print_function

import io
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
                      "TH-01a.liml")


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def test_field_table():
    rows = [r for r in are.FIELD_TABLE if r[2] == "FLUX_ELNO"]
    check(sorted(r[4] for r in rows) == ["heatfluxx", "heatfluxy",
                                         "heatfluxz"] and
          all(r[0] == "heat_flux" and r[1] == "res_flux" and
              r[5] == are.ELEMKNOOP for r in rows),
          "FIELD_TABLE: FLUX_ELNO as element-node heatfluxx/y/z")


def test_elem_magnitude():
    ids = np.array([1, 2], dtype="<i4")
    vals = {"x": np.array([3.0, 0.0, 1.0]), "y": np.array([4.0, 0.0, 2.0]),
            "z": np.array([0.0, 5.0, 2.0])}
    parts = [are._Var("heatflux" + c, True, ids,
                      (lambda c: lambda f: vals[c])(c)) for c in "xyz"]
    mag = are._elem_magnitude_var("heatfluxmag", parts)
    check(mag is not None and mag.element and
          np.allclose(mag.getter(None), [5.0, 5.0, 3.0]),
          "element-node magnitude sqrt(x^2+y^2+z^2)")
    parts[2] = are._Var("heatfluxz", True, np.array([1], dtype="<i4"),
                        lambda f: vals["z"])
    check(are._elem_magnitude_var("heatfluxmag", parts) is None,
          "element-node magnitude: components on other elements -> None")


def _comm(tmp, plate):
    work = tempfile.mkdtemp(dir=tmp)
    with io.open(_MODEL, encoding="utf-8") as f:
        s = f.read()
    if plate:
        nodes = []
        for i, x in enumerate((0.0, 0.025, 0.05, 0.075, 0.1)):
            nodes.append('  <node nid="%d" x="%g" y="0.05" z="0" />'
                         % (37 + 2 * i, x))
            nodes.append('  <node nid="%d" x="%g" y="0.05" z="0.02" />'
                         % (38 + 2 * i, x))
        elems = ['    <elem eid="%d" shape="quad4" nodes="%d %d %d %d" />'
                 % (9 + i, 37 + 2 * i, 39 + 2 * i, 40 + 2 * i, 38 + 2 * i)
                 for i in range(4)]
        k = s.index("  <elset ")
        s = s[:k] + "\n".join(nodes) + "\n" + s[k:]
        s = s.replace(
            "  <mat ",
            '  <elset name="Plaat" material="Plaat">\n' + "\n".join(elems) +
            '\n  </elset>\n  <temperature2 selection="PlaatL"><value>400 K'
            '</value><starttime>0 s</starttime><endtime>0 s</endtime>'
            '</temperature2>\n  <mat name="Plaat">\n    <geometric '
            'type="Plate" thickness="0.002 m" />\n    <thermal '
            'type="Isotropic" thermalconductivity="50 W/m/K" />\n  </mat>\n'
            '  <mat ', 1)
        s = s.replace("</liml>", '  <nodeselection name="PlaatL">\n'
                      '    <node nid="37" />\n    <node nid="38" />\n'
                      '  </nodeselection>\n</liml>')
    liml = os.path.join(work, "model.liml")
    with io.open(liml, "w", encoding="utf-8") as f:
        f.write(s)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = "ther_3d"
    md = extract_aster_data_from_liml(liml)
    mail = os.path.join(work, "m.mail")
    ok = (md is not None and write_mesh(mail, md) and
          generate_AsterSolver_files(work, md, mail, "test.resu"))
    check(bool(ok), "{0}: files generated".format(
        "wall + plate" if plate else "wall"))
    if not ok:
        return ""
    return io.open(os.path.join(work, "study.comm"), encoding="utf-8").read()


def test_rotation(tmp):
    comm = _comm(tmp, plate=False)
    check("FLUX_ELNO" in comm and "ELNO_FLUX_R" not in comm,
          "wall only: FLUX_ELNO computed, no rotation block")
    comm = _comm(tmp, plate=True)
    check("ROTATION=" in comm and
          "res_flux.setField(fe_g, 'FLUX_ELNO', nume_r)" in comm and
          "_F(GROUP_MA=('Wand',), CHAM_GD=fe_r" in comm and
          "CHAM_GD=fe_r" not in comm.replace(
              "GROUP_MA=('Wand',), CHAM_GD=fe_r", ""),
          "wall + plate in y = 0.05: FLUX_ELNO rotated back on the solids")


def main():
    saved = dict(u.CONFIG_BRIDGE)
    tmp = tempfile.mkdtemp(prefix="bridge_heatflux_elno_")
    try:
        test_field_table()
        test_elem_magnitude()
        test_rotation(tmp)
    finally:
        u.CONFIG_BRIDGE.clear()
        u.CONFIG_BRIDGE.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
