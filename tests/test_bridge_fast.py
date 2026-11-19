# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_fast must extract the same model_data mesh fields as ElementTree
# and write the same .mail bytes as _write_aster_mail_py. No Mecway.
#
#   python tests/test_bridge_fast.py

from __future__ import print_function

import os
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))

import bridge_fast  # noqa: E402
import bridge_mesh  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402

_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _diff(a, b, path):
    """First mismatch path, or None. Skips the fast-path marker."""
    if path == "_fast_mesh" or path.endswith("._fast_mesh"):
        return None
    if type(a) != type(b) and not (
            isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return path + " type {0} vs {1}".format(type(a).__name__,
                                                type(b).__name__)
    if isinstance(a, dict):
        if set(a) - set(["_fast_mesh"]) != set(b) - set(["_fast_mesh"]):
            extra = sorted((set(a) ^ set(b)) - set(["_fast_mesh"]))
            return path + " keys {0}".format(extra[:8])
        for key in a:
            if key == "_fast_mesh":
                continue
            found = _diff(a[key], b[key], path + "." + str(key))
            if found:
                return found
        return None
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return path + " len {0} vs {1}".format(len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            found = _diff(x, y, "{0}[{1}]".format(path, i))
            if found:
                return found
        return None
    if isinstance(a, float) or isinstance(b, float):
        if a != b:
            return path + " {0!r} vs {1!r}".format(a, b)
        return None
    if a != b:
        return path + " {0!r} vs {1!r}".format(a, b)
    return None


def _extract(path, fast):
    if fast:
        os.environ.pop("ASTER_FAST", None)
    else:
        os.environ["ASTER_FAST"] = "0"
    t0 = time.time()
    data = extract_aster_data_from_liml(path, warn_supports=False)
    return data, time.time() - t0


def _compare_liml(path):
    name = os.path.basename(path)
    fast, dt_fast = _extract(path, True)
    slow, dt_slow = _extract(path, False)
    if fast is None or slow is None:
        check(False, name + ": extract returned None")
        return
    found = _diff(fast, slow, name)
    check(found is None, name + ": model_data"
          + ("" if found is None else " " + found))
    check(fast.get("_fast_mesh") is True, name + ": used aster_fast")
    print("  {0}: rust {1:.3f}s, python {2:.3f}s, nodes {3}".format(
        name, dt_fast, dt_slow, len(fast.get("mesh_nodes", {}))))


def _mail():
    nodes = {}
    nids = list(range(1, 2001))
    # Deterministic values, including the %.15g edges.
    specials = {
        1: (0.0, -0.0, 1.0e-5),
        2: (1.0e15, 1.0e20, 9.99e-5),
        3: (3.141592653589793, 9999999.0, 10.0),
        4: (1.0e-4, -1.0e-5, 123456.78901234567),
        5: (8.881784197001252e-16, 1.25, -3.5),
    }
    for nid in nids:
        if nid in specials:
            nodes[nid] = specials[nid]
        else:
            nodes[nid] = ((nid * 17 % 1000) * 1.0e-6,
                          -float(nid) * 0.25,
                          float(nid) * 1.0e-8)
    extra = [(2001, (1.0, 2.0, 3.0)), (2002, (-0.0, 1.0e20, -3.5))]
    cn = list(range(1, 21))
    by_type = {
        "HEXA20": [("M{0}".format(i), cn) for i in range(1, 40)],
        "SEG2": [("M100", [1, 2])],
    }
    group_ma = {"ALL": ["M{0}".format(i) for i in range(1, 40)]}
    group_no = {"NODES": ["N{0}".format(n) for n in range(1, 80)]}
    fd, py_path = tempfile.mkstemp(suffix=".mail")
    os.close(fd)
    fd, rs_path = tempfile.mkstemp(suffix=".mail")
    os.close(fd)
    try:
        bridge_mesh._write_aster_mail_py(
            py_path, nids, nodes, extra, by_type, group_ma, group_no)
        ok = bridge_fast.write_mail(
            rs_path, nids, nodes, extra, by_type, group_ma, group_no)
        check(ok, "aster_fast mail ran")
        if not ok:
            return
        py = open(py_path, "rb").read()
        rs = open(rs_path, "rb").read()
        check(py == rs, "mail bytes ({0})".format(len(py)))
        if py != rs:
            n = min(len(py), len(rs))
            i = next((k for k in range(n) if py[k] != rs[k]), n)
            print("  first byte {0}: py {1!r} rs {2!r}".format(
                i, py[max(0, i - 40):i + 40], rs[max(0, i - 40):i + 40]))
    finally:
        os.remove(py_path)
        os.remove(rs_path)


def _synthetic():
    xml = """<liml version="1">
  <analysis type="S30" />
  <node nid="1" x="0" y="0" z="0" />
  <node nid="2" x="1.5" y="-2" z="1e-5" />
  <elset name="PLACE" material="Staal">
    <elem eid="1" shape="line2" nodes="1 2" truss="true" />
    <elem eid="2" shape="line2" nodes="2 1"
          orientationvx="0" orientationvy="1" orientationvz="0"
          angle="90 deg" />
  </elset>
  <nodeselection name="Vast">
    <node nid="01" />
  </nodeselection>
  <faceselection name="Zijde">
    <face eid="1" faceid="2" />
  </faceselection>
  <elementselection name="Alles">
    <element eid="2" />
  </elementselection>
  <mat name="Staal">
    <geometric type="CircularBar" roundod="10 mm" />
    <mechanical type="Isotropic" youngsmodulus="210000 MPa"
                poissonratio="0.3" />
  </mat>
  <solution>
    <node nid="9" x="4" y="4" z="4" />
    <elset name="Ghost"><elem eid="9" shape="hex8" nodes="1 2" /></elset>
  </solution>
</liml>
"""
    xml = xml.replace("PLACE", "A" + chr(38) + "amp;B")
    fd, path = tempfile.mkstemp(suffix=".liml")
    os.close(fd)
    try:
        with open(path, "w") as f:
            f.write(xml)
        fast, _dt = _extract(path, True)
        check(fast is not None, "synthetic extract")
        if fast is None:
            return
        check(9 not in fast["mesh_nodes"], "solution node is not in the mesh")
        check(fast["node_groups"].get("Vast") == ["N01"],
              "node group keeps the nid text")
        check(len(fast["mesh_elements"]) == 2, "two elements, not the solution elset")
        check("A&B" in fast["materials"] or "A&B" in str(fast.get("elsets")),
              "escaped elset name")
        _compare_liml(path)
    finally:
        os.remove(path)


def main():
    exe = bridge_fast.find_exe()
    if not exe:
        print("SKIP aster_fast not built")
        return 0
    print("aster_fast:", exe)
    _mail()
    _synthetic()
    root = os.path.join(_HERE, "..", "TestFiles")
    names = [
        os.path.join(root, "Voorbeelden", "Voorbeeld_A.liml"),
        os.path.join(root, "Foutschatter_Balk.liml"),
        os.path.join(root, "Verificatie", "modellen", "MO-08.liml"),
        os.path.join(root, "Verificatie", "modellen", "OR-20.liml"),
        os.path.join(root, "BezwijkenTrekstaaf.liml"),
        os.path.join(root, "Verificatie", "modellen", "BR-09.liml"),
    ]
    for path in names:
        if os.path.isfile(path):
            _compare_liml(path)
    if _FAILED:
        print("{0} FAILED".format(len(_FAILED)))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
