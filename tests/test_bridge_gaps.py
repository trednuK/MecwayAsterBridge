# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_to_aster._prepare_gaps and the AFFE_CARA_ELEM
# entries of gaps (KNOWN_BUGS 23), on synthetic model_data:
#   - U along node 1 -> 2 (no U, or a parallel U): no ORIENTATION,
#     DIST_1 + DIST_2 = L - c, K_T_D_L in REPERE='LOCAL';
#   - coincident nodes with U: VECT_X_Y without PRECISION, D = 0;
#   - U oblique or a lateral offset: VECT_X_Y with PRECISION above the
#     cell length, D = (x2 - x1) . U - c; U perpendicular: D = 0;
#   - one group per (D, k, U); a deterministic y axis;
#   - refused (ERROR, element skipped): tension gap on separate nodes,
#     clearance on coincident nodes, coincident nodes without U (also a
#     zero U vector), clearance larger than the distance along U;
#   - round-off: a nearly coincident cell counts as coincident.
# The results against Mecway 35 are verification cases NL-92 .. NL-92m.
# Python 2.7 (IronPython) and 3; under CPython it also runs once in
# Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1) when Mecway is
# installed.
#
#   python tests/test_bridge_gaps.py

from __future__ import print_function

import io
import math
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_to_aster as bta  # noqa: E402
bta.log = _log

FAILS = []


def check(text, cond, detail=""):
    if cond:
        print("ok   " + text)
    else:
        print("FAIL " + text + (" " + repr(detail) if detail else ""))
        FAILS.append(text)


def model(gaps, clearance=0.0):
    """gaps: [(p1, p2, U or None)], one line2 gap each in elset Spleet."""
    nodes, elems, u_axes = {}, [], {}
    for i, (p1, p2, u) in enumerate(gaps):
        nodes[2 * i + 1], nodes[2 * i + 2] = tuple(p1), tuple(p2)
        elems.append((i + 1, "line2", [2 * i + 1, 2 * i + 2], "Spleet"))
        if u is not None:
            u_axes[i + 1] = tuple(u)
    return {"mesh_nodes": nodes, "mesh_elements": elems,
            "elem_u_axes": u_axes,
            "discrete_sections": {"Spleet": {
                "kind": "gap", "k": 1.0e9, "clearance": clearance}}}


def prepare(gaps, clearance=0.0):
    del LOG[:]
    md = model(gaps, clearance)
    bta._prepare_gaps(md)
    return md


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_parallel():
    for u in (None, (2.0, 0.0, 0.0)):
        md = prepare([((1, 0, 0), (1.01, 0, 0), u)], clearance=0.004)
        g = md["gap_groups"].get("BRGAP1", {})
        check("parallel U {0}: one group, no own U".format(u),
              list(md["gap_groups"]) == ["BRGAP1"] and g["u"] is None, g)
        check("parallel U {0}: D = L - c".format(u),
              close(g["dist"], 0.006), g.get("dist"))
        check("parallel U {0}: no ORIENTATION".format(u),
              bta._gap_orientation_entries(md) == [])
    cara = bta._discrete_cara_entries(md)
    check("K_T_D_L of the gap group in REPERE='LOCAL'",
          any("BRGAP1" in e and "K_T_D_L" in e and "REPERE='LOCAL'" in e
              for e in cara), cara)


def test_coincident():
    md = prepare([((1, 0, 0), (1, 0, 0), (0, 0, -3))])
    g = md["gap_groups"]["BRGAP1"]
    check("coincident with U: D = 0, unit U",
          g["dist"] == 0.0 and g["u"] == (0.0, 0.0, -1.0), g)
    ent = bta._gap_orientation_entries(md)
    check("coincident: VECT_X_Y without PRECISION",
          len(ent) == 1 and "VECT_X_Y" in ent[0] and
          "PRECISION" not in ent[0], ent)
    # nearly coincident (round-off below the written 15 digits)
    md = prepare([((1, 0, 0), (1 + 1e-13, 0, 0), (0, 1, 0))])
    g = md["gap_groups"]["BRGAP1"]
    check("nearly coincident: D = 0 (not a tension gap)",
          g["dist"] == 0.0 and g["u"] == (0.0, 1.0, 0.0), g)
    check("nearly coincident: PRECISION written (length > 0 for Code-Aster)",
          "PRECISION" in bta._gap_orientation_entries(md)[0])


def test_oblique():
    r2 = math.sqrt(0.5)
    md = prepare([((1, 0, 0), (1.01, 0, 0), (1, 1, 0)),
                  ((1, 0, 0), (1.01, 0.005, 0), (1, 0, 0)),
                  ((1, 0, 0), (1.01, 0, 0), (0, 1, 0)),
                  ((2, 0, 0), (2.01, 0, 0), (1, 1, 0))], clearance=0.0)
    groups = md["gap_groups"]
    check("oblique: three groups (equal D, k and U share one)",
          list(groups) == ["BRGAP1", "BRGAP2", "BRGAP3"] and
          md["extra_ma_groups"]["BRGAP1"] == [1, 4], md["extra_ma_groups"])
    check("oblique 45 degrees: D = L cos 45",
          close(groups["BRGAP1"]["dist"], 0.01 * r2), groups["BRGAP1"])
    check("lateral offset: D = projection on U",
          close(groups["BRGAP2"]["dist"], 0.01), groups["BRGAP2"])
    check("U perpendicular: D = 0", groups["BRGAP3"]["dist"] == 0.0,
          groups["BRGAP3"])
    ent = bta._gap_orientation_entries(md)
    check("oblique: VECT_X_Y with PRECISION > cell length",
          len(ent) == 3 and all("PRECISION" in e for e in ent), ent)
    prec = float(ent[1].split("PRECISION=")[1].split(")")[0])
    check("PRECISION = 2 x the longest cell", close(
        prec, 2 * math.sqrt(0.01 ** 2 + 0.005 ** 2)), prec)
    for u in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (r2, r2, 0), (0.6, 0, 0.8)):
        y = bta._gap_y_axis(u)
        check("y axis unit and perpendicular for U {0}".format(u),
              close(sum(c * c for c in y), 1.0) and
              abs(sum(a * b for a, b in zip(u, y))) < 1e-12, y)
    check("y axis deterministic",
          bta._gap_y_axis((1.0, 0.0, 0.0)) == bta._gap_y_axis((1.0, 0, 0)))


def test_refused():
    cases = [
        ("tension gap on separate nodes",
         [((1, 0, 0), (1.01, 0, 0), (-1, 0, 0))], 0.0, "tension gap"),
        ("clearance on coincident nodes",
         [((1, 0, 0), (1, 0, 0), (1, 0, 0))], 0.001,
         "clearance on coincident nodes"),
        ("coincident nodes without U",
         [((1, 0, 0), (1, 0, 0), None)], 0.0, "without a U axis"),
        ("coincident nodes with a zero U vector",
         [((1, 0, 0), (1, 0, 0), (0, 0, 0))], 0.0, "without a U axis"),
        ("clearance larger than the element (parallel)",
         [((1, 0, 0), (1.01, 0, 0), None)], 0.02, "along U"),
        ("clearance larger than the distance along an oblique U",
         [((1, 0, 0), (1.01, 0, 0), (1, 1, 0))], 0.008, "along U"),
    ]
    for text, gaps, c, words in cases:
        md = prepare(gaps, clearance=c)
        errors = [m for m in LOG if m.startswith("ERROR")]
        check("refused: " + text,
              not md["gap_groups"] and md.get("skipped_loads") ==
              ["gap element 1"] and len(errors) == 1 and words in errors[0],
              (md["gap_groups"], errors))
    md = prepare([((1, 0, 0), (1.01, 0, 0), (0, 0, 0))])
    check("zero U vector on separate nodes = no U (node 1 -> 2)",
          md["gap_groups"]["BRGAP1"]["u"] is None and
          close(md["gap_groups"]["BRGAP1"]["dist"], 0.01), md["gap_groups"])


def run_in_ironpython():
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="gaps_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_gaps.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_bridge_gaps as t\n"
                    u"sys.exit(t.main())\n".format(os.path.abspath(_HERE)))
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", os.path.abspath(ps), "-Script", wrapper],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.communicate()[0].decode("utf-8", "replace")
        print("--- IronPython 2.7.9 ---")
        print(out.strip())
        check("IronPython run without failures", proc.returncode == 0 and
              "FAIL" not in out and "All tests passed." in out)
    finally:
        shutil.rmtree(tmp, True)


def main():
    test_parallel()
    test_coincident()
    test_oblique()
    test_refused()
    if FAILS:
        print("{0} FAILED".format(len(FAILS)))
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    rc = main()
    if rc == 0 and sys.version_info[0] >= 3:
        run_in_ironpython()
        rc = 1 if FAILS else 0
    sys.exit(rc)
