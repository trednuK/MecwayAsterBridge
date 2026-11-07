# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_manifest.py (Python 2.7 and 3, without Mecway and
# Code-Aster): the setting keep_base, the base line in the .export, the
# manifest, the fingerprint and the clean-up of old bases.
#
#   python tests/test_bridge_manifest.py

from __future__ import print_function

import io
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_manifest as bm  # noqa: E402

LOG = []
bm.log = LOG.append
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _model():
    return {
        "mesh_nodes": {1: (0.0, 0.0, 0.0), 2: (0.1, 0.0, 0.0),
                       3: (0.1, 0.2, 0.0), 4: (0.0, 0.2, 0.3)},
        "mesh_elements": [(7, "tet4", [1, 2, 3, 4], "P")],
        "configuration": None,
        "skin_parents": {"K1": [[7, 1]], "K2": [[7, 2]]},
        "cell_names": ["M2", "M1", "K1"],
        "deformation_by_elset": {"P": "GDEF_LOG"},
    }


def test_fingerprint():
    n = {1: (0.0, 0.0, 0.0), 2: (0.1, -0.2, 0.3)}
    a = bm.mesh_fingerprint(n, [5, 6])
    check(a == bm.mesh_fingerprint(dict(reversed(list(n.items()))), [6, 5]),
          "fingerprint does not depend on the order")
    check(a != bm.mesh_fingerprint({1: n[1], 2: (0.1, -0.2, 0.300000002)},
                                   [5, 6]),
          "a shift of 2 nm changes the fingerprint")
    check(a == bm.mesh_fingerprint({1: n[1], 2: (0.1, -0.2, 0.3000000001)},
                                   [5, 6]),
          "a shift of 0.1 nm does not")
    check(a != bm.mesh_fingerprint(n, [5, 7]), "element ids count")
    check(a != bm.mesh_fingerprint({1: n[1], 3: n[2]}, [5, 6]),
          "node ids count")
    check(len(a) == 64, "sha256 hex")


def test_run_name_split():
    check(bm.split_run_name("Beam_A_20261107_101500") ==
          ("Beam_A", "20261107_101500"), "model and run id")
    check(bm.split_run_name("study") == ("study", None), "outside a run")


def test_bases_to_remove():
    runs = ["20261101_100000", "20261102_100000", "20261103_100000",
            "20261104_100000"]
    names = ["M_{0}_base".format(r) for r in runs]
    names += ["M_{0}_manifest.json".format(r) for r in runs]
    names += ["M_B_20261101_100000_base", "M_B_20261101_100000_manifest.json",
              "M_x_base", "other", "M_20261105_100000_base"]
    check(bm.bases_to_remove(names, "M", 2) ==
          ["M_20261101_100000_base", "M_20261102_100000_base"],
          "oldest usable of this model only; a base without manifest "
          "does not count")
    check(bm.bases_to_remove(names, "M", 10) == [], "fewer than keep")
    check(bm.orphan_bases(names, "M", None) == ["M_20261105_100000_base"],
          "a base without manifest is an orphan")
    check(bm.orphan_bases(names, "M", "M_20261105_100000_base") == [],
          "but not that of the current run")
    check(bm.bases_to_remove(names, "M", 0) == names[:3],
          "at least the newest one stays")


def test_prune(tmp):
    for run in ("20261101_100000", "20261102_100000", "20261103_100000"):
        base = os.path.join(tmp, "M_{0}_base".format(run))
        os.mkdir(base)
        with open(os.path.join(base, "glob.1"), "w") as f:
            f.write("x")
        with open(os.path.join(tmp, "M_{0}_manifest.json".format(run)),
                  "w") as f:
            f.write("{}")
    os.mkdir(os.path.join(tmp, "M_20261102_100000_base", "sub"))
    bm.prune_bases(tmp, "M", 1)
    left = sorted(os.listdir(tmp))
    check("M_20261101_100000_base" not in left and
          "M_20261101_100000_manifest.json" not in left,
          "old base removed with its manifest")
    check("M_20261102_100000_base" in left and
          "M_20261102_100000_manifest.json" in left,
          "a folder with a subfolder stays, with its manifest")
    check("M_20261103_100000_base" in left, "newest stays")


def _read(path):
    # Closed at once: IronPython has no reference counting
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _export(tmp):
    path = os.path.join(tmp, "M_20261107_101500.export")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"P memory_limit 2048\nF comm x.comm D 1")
    return path


def test_finish_export(tmp):
    cfg = bridge_utils.CONFIG_BRIDGE
    bridge_utils.set_run_log("20261107_101500", "M.liml")
    bm.run_name = bridge_utils.run_name
    path = _export(tmp)
    cfg["keep_base"] = False
    static = {"solver_command": "MECA_STATIQUE"}
    nonlin = {"solver_command": "STAT_NON_LINE", "deformation": "GROT_GDEP"}
    check(not bm.prepare_base(path, tmp, _model(), static, False, False),
          "setting off: nothing")
    check(_read(path).count("R base") == 0,
          "setting off: .export unchanged")

    cfg["keep_base"] = True
    for analysis, adaptive in (({"solver_command": "CALC_MODES"}, False),
                               (static, True)):
        check(not bm.prepare_base(path, tmp, _model(), analysis, adaptive,
                                  False),
              "no base for {0}, adaptive {1}".format(analysis, adaptive))
    check(_read(path).count("R base") == 0,
          "still no base line")

    # A good older run of this model stays when a new run fails
    old = os.path.join(tmp, "M_20261101_100000")
    os.mkdir(old + "_base")
    with open(old + "_manifest.json", "w") as f:
        f.write("{}")
    cfg["keep_base_runs"] = 1
    model = _model()
    check(bm.prepare_base(path, tmp, model, nonlin, False, True),
          "static: base kept")
    check(os.listdir(tmp).count("M_20261107_101500_manifest.json") == 0,
          "no manifest before the run")
    with open(os.path.join(tmp, "M_20261107_101500_base", "glob.1"), "w") as f:
        f.write("x")
    check(not bm.finish_run(tmp, model, path, False), "failed run: no manifest")
    check(not os.path.exists(os.path.join(tmp, "M_20261107_101500_base")),
          "failed run: its base folder is gone")
    check(os.path.isdir(old + "_base") and
          os.path.exists(old + "_manifest.json"),
          "failed run: the older good base stays")
    os.mkdir(os.path.join(tmp, "M_20261107_101500_base"))
    check(bm.finish_run(tmp, model, path, True, "17.4"), "good run")
    check(not os.path.exists(old + "_base") and
          not os.path.exists(old + "_manifest.json"),
          "good run: the older base goes, keep_base_runs 1")
    cfg["keep_base_runs"] = 3
    text = _read(path)
    base = os.path.join(tmp, "M_20261107_101500_base")
    check("\nR base {0} R 0".format(base) in text, "base line in the .export")
    check(os.path.isdir(base), "base folder exists")
    man = json.loads(_read(os.path.join(
        tmp, "M_20261107_101500_manifest.json")))
    check(man["schema"] == 1 and man["run_id"] == "20261107_101500" and
          man["model"] == "M", "run and model")
    check(man["aster_version"] == "17.4", "version that really ran")
    check(man["extra_nodes"] is False, "no extra nodes")
    check(man["deformation"] == "GROT_GDEP", "choice of the run")
    check(man["deformation_by_component"] == {"P": "GDEF_LOG"},
          "what the component computed with")
    check(man["memory_limit"] == 2048, "memory limit from the .export")
    check(man["solver"] == "STAT_NON_LINE", "solver")
    check(man["base"] == "M_20261107_101500_base", "base without a path")
    check(man["concepts"]["result"] == "res" and
          man["concepts"]["cara"] == "cara", "concept names")
    check(man["cells"] == ["M2", "M1", "K1"], "cells in file order")
    check(man["skin"] == {"K1": [[7, 1]], "K2": [[7, 2]]}, "skin parents")
    check(man["not_shared"] == [], "nothing special")
    check(tmp not in json.dumps(man), "no paths in the manifest")
    cfg["keep_base"] = False
    bridge_utils.set_run_log(None)


def test_deformation_by_component():
    md = {"deformation_by_elset": {"F": "GROT_GDEP", "F_TRUSS": "PETIT",
                                   "G": "PETIT", "G_TRUSS": "PETIT"},
          "group_renames": {"Part one": "P1"}}
    md["deformation_by_elset"]["P1"] = "GDEF_LOG"
    check(bm._deformation_by_component(md) ==
          {"F": "MIXED", "G": "PETIT", "Part one": "GDEF_LOG"},
          "truss part joins its component; a difference shows as MIXED")


def test_orphan_age(tmp):
    young = os.path.join(tmp, "M_20261106_100000_base")
    old = os.path.join(tmp, "M_20261105_100000_base")
    os.mkdir(young)
    os.mkdir(old)
    past = bm.time.time() - 2 * bm.ORPHAN_AGE
    os.utime(old, (past, past))
    bm.prune_bases(tmp, "M", 3)
    check(os.path.isdir(young), "a young base without manifest stays")
    check(not os.path.exists(old), "an old one goes")


def test_not_shared():
    md = _model()
    md["offset_links"] = [1]
    md["contacts"] = [1]
    md["bonded"] = [1]
    md["couplings"] = [1]
    md["constraint_equations"] = [1]
    md["pretension_sections"] = [1]
    md["flexible_joints"] = [1]
    check(bm._not_shared(md) == ["offset", "contact", "bonded", "coupling",
                                 "constraint", "pretension",
                                 "flexible_joint"], "all named")


def main():
    test_fingerprint()
    test_run_name_split()
    test_bases_to_remove()
    test_deformation_by_component()
    for fn in (test_prune, test_finish_export, test_orphan_age):
        tmp = tempfile.mkdtemp()
        try:
            fn(tmp)
        finally:
            shutil.rmtree(tmp)
    test_not_shared()
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
