# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the VTU/PVD export (aster_vtu.VtuSeries), called the way
# the job does it (aster_results_export._vtu_series, _failed_var and
# add_cells("T_BEZWIJK", ...)): a fake model with one hex8 and one line2
# beam, two steps with displacements, a beam section force and the element
# variable "failed". Checks the .pvd and .vtu files, the array names (no
# BEZWEKEN any more), a few values, and that no beam sidecar (_beams.json)
# or node series (_knopen.csv) is written. Needs numpy (CPython 3, as in
# the job); without numpy the test is skipped.
#
#   python tests/test_aster_vtu.py

from __future__ import print_function

import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))

try:
    import numpy as np
except ImportError:
    np = None

FAILED = []


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        FAILED.append(name)


class _Fields(object):
    """Stand-in for aster_results_export._Fields: only the step index."""

    def __init__(self, index):
        self.index = index


def _model():
    coords = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
              (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 1, 3)]
    return {"coords": coords,
            "elements": {1: ("hex8", list(range(1, 9))),
                         2: ("line2", [8, 9])}}


def _read_vtu(path):
    """(header text, {array name: numpy array}) of a raw appended .vtu."""
    with open(path, "rb") as f:
        raw = f.read()
    cut = raw.index(b'<AppendedData encoding="raw">')
    head = raw[:cut].decode("utf-8")
    start = raw.index(b"_", cut) + 1
    types = {"Float32": np.float32, "Float64": np.float64,
             "Int32": np.int32, "Int64": np.int64, "UInt8": np.uint8}
    arrays = {}
    for m in re.finditer(r'<DataArray type="(\w+)"(?: Name="([^"]*)")?'
                         r'(?: NumberOfComponents="\d+")? format="appended"'
                         r' offset="(\d+)"/>', head):
        pos = start + int(m.group(3))
        size = int(np.frombuffer(raw[pos:pos + 8], dtype=np.uint64)[0])
        arrays[m.group(2) or "Points"] = np.frombuffer(
            raw[pos + 8:pos + 8 + size], dtype=types[m.group(1)])
    return head, arrays


def main():
    if np is None:
        print("SKIP: numpy not available (the VTU export runs in the "
              "Code-Aster job, which has numpy)")
        return 0
    import aster_results_export as are
    import bridge_utils
    bridge_utils.CONFIG_BRIDGE["language"] = "en"

    tmp = tempfile.mkdtemp(prefix="test_aster_vtu_")
    env_saved = os.environ.get(are.VTU_ENV)
    try:
        model = _model()
        times = {0: 0.5, 1: 1.0}
        nodes = np.arange(1, 10, dtype="<i4")

        def displ(scale):
            return lambda fields: scale * (fields.index + 1) * np.arange(
                1.0, 10.0)
        variables = [are._Var(name, False, nodes, displ(s))
                     for name, s in (("displx", 1.0), ("disply", 2.0),
                                     ("displz", 3.0))]
        # beam section force per element node: 10 at the first, 20 at the
        # last node, times the step number
        variables.append(are._Var(
            "tensileforce", True, np.array([2], dtype="<i4"),
            lambda fields: (fields.index + 1) * np.array([10.0, 20.0])))
        failed_at = {2: 1.0}     # the beam fails at t = 1 (second step)
        variables.append(are._failed_var(failed_at, model, times))

        out_path = os.path.join(tmp, "model_20261110_results.xml")
        os.environ.pop(are.VTU_ENV, None)
        check("no VTU without the environment variable",
              are._vtu_series(out_path, model, variables, "single",
                              None) is None)
        os.environ[are.VTU_ENV] = "1"
        vtu = are._vtu_series(out_path, model, variables, "single", None)
        check("VtuSeries made", vtu is not None)
        if vtu is None:
            return 1
        check("no skipped shapes", not vtu.skipped)
        vtu.add_cells("T_BEZWIJK", lambda k: failed_at)
        for k in (0, 1):
            fields = _Fields(k)
            vtu.step(k, times[k], [v.getter(fields) for v in variables])
        pvd = vtu.close()
        base = os.path.join(tmp, "model_20261110")
        check(".pvd written", pvd == base + ".pvd" and os.path.isfile(pvd))
        with open(pvd) as f:
            text = f.read()
        check(".pvd lists both steps",
              'file="model_20261110_0.vtu"' in text and
              'file="model_20261110_1.vtu"' in text and
              'timestep="0.5"' in text and 'timestep="1.0"' in text)
        for k in (0, 1):
            path = "{0}_{1}.vtu".format(base, k)
            check("step {0}: .vtu written".format(k), os.path.isfile(path))
            if not os.path.isfile(path):
                continue
            head, arrays = _read_vtu(path)
            for name in ("failed", "EFGE_N_1", "EFGE_N_2", "DEPL",
                         "NODE_ID", "ELEMENT_ID", "T_BEZWIJK", "displx",
                         "tensileforce"):
                check("step {0}: array {1}".format(k, name),
                      'Name="{0}"'.format(name) in head)
            check("step {0}: no array BEZWEKEN".format(k),
                  "BEZWEKEN" not in head)
            check("step {0}: 2 cells, 9 points".format(k),
                  'NumberOfPoints="9" NumberOfCells="2"' in head)
            cell_ids = list(arrays.get("ELEMENT_ID", []))
            check("step {0}: ELEMENT_ID 1, 2".format(k), cell_ids == [1, 2])
            f = 1.0 + k
            efge1 = arrays.get("EFGE_N_1", np.zeros(2))
            efge2 = arrays.get("EFGE_N_2", np.zeros(2))
            check("step {0}: EFGE_N_1/_2 at both beam ends".format(k),
                  np.isnan(efge1[0]) and efge1[1] == 10.0 * f and
                  np.isnan(efge2[0]) and efge2[1] == 20.0 * f)
            failed = list(arrays.get("failed", []))
            check("step {0}: failed {1}".format(k, [0.0, float(k)]),
                  failed == [0.0, float(k)])
            depl = arrays.get("DEPL", np.zeros(0)).reshape(-1, 3)
            check("step {0}: DEPL of node 9".format(k),
                  depl.shape == (9, 3) and
                  list(depl[8]) == [9.0 * f, 18.0 * f, 27.0 * f])
        names = os.listdir(tmp)
        check("no node series _knopen.csv",
              not any(n.endswith("_knopen.csv") for n in names))
        check("no beam sidecar _beams.json",
              not any(n.endswith("_beams.json") for n in names))
        check("no files left behind but .pvd and .vtu",
              sorted(names) == ["model_20261110.pvd",
                                "model_20261110_0.vtu",
                                "model_20261110_1.vtu"])
    finally:
        if env_saved is None:
            os.environ.pop(are.VTU_ENV, None)
        else:
            os.environ[are.VTU_ENV] = env_saved
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(FAILED)))
    return 1 if FAILED else 0


if main():
    sys.exit(1)
