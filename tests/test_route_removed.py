# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (CPython) of the removal of the result route 'tabel'
# (V2026.15): a bridge_utils.py kept from an older bridge with
# "result_route": "tabel" gives one WARNING (bridge_utils.legacy_route_note)
# and the same .comm as without the key; the start screen leaves that line
# alone when it saves other settings (bridge_gui.save_to_bridge_utils, on a
# copy); no module reads the setting any more. Only CONFIG_BRIDGE in memory;
# the repository's bridge_utils.py is not written.
#
#   python tests/test_route_removed.py

from __future__ import print_function

import glob
import io
import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
SCRIPTS = os.path.join(_HERE, "..", "Scripts")
sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True
import bridge_utils as u  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def test_note():
    u._LEGACY_ROUTE["noted"] = False
    check(u.legacy_route_note({}) == u"", "no key: no note")
    check(u.legacy_route_note({"result_route": "liml"}) == u"",
          "liml: no note")
    note = u.legacy_route_note({"result_route": "tabel"})
    check(note.startswith(u"WARNING: The result route 'tabel'") and
          u"result_route" in note and u"Results..." in note,
          "tabel: WARNING with the value and the hint")
    check(u.legacy_route_note({"result_route": "tabel"}) == u"",
          "the note comes once per session")
    u._LEGACY_ROUTE["noted"] = False
    check(u"'foo'" in u.legacy_route_note({"result_route": "foo"}),
          "any other value: the note")
    u._LEGACY_ROUTE["noted"] = False


def test_no_reader():
    readers = []
    for path in glob.glob(os.path.join(SCRIPTS, "*.py")):
        text = io.open(path, encoding="utf-8").read()
        for m in re.finditer(r"""(\.get\(\s*|\[)["']result_route["']""",
                             text):
            readers.append((os.path.basename(path), m.group(0)))
    check([r[0] for r in readers] == ["bridge_utils.py"],
          "only bridge_utils.legacy_route_note reads result_route: "
          "{0}".format(readers))
    check(not os.path.exists(os.path.join(SCRIPTS, "bridge_element_node.py")),
          "bridge_element_node.py is gone")


def test_same_comm(tmp):
    from bridge_from_liml import extract_aster_data_from_liml
    from bridge_mesh import write_mesh
    from bridge_to_aster import generate_AsterSolver_files
    src = os.path.join(_HERE, "..", "TestFiles", "Voorbeelden",
                       "Voorbeeld_A.liml")
    cfg = u.CONFIG_BRIDGE
    saved = dict((k, cfg.get(k)) for k in ("work_dir", "active_analysis"))
    texts = []
    try:
        for value in (None, "tabel"):
            work = os.path.join(tmp, "w_{0}".format(value))
            os.makedirs(work)
            shutil.copy(src, os.path.join(work, "model.liml"))
            cfg["work_dir"] = work
            cfg["active_analysis"] = "lin_static_3d"
            if value is None:
                cfg.pop("result_route", None)
            else:
                cfg["result_route"] = value
            md = extract_aster_data_from_liml(os.path.join(work,
                                                           "model.liml"))
            ok = (md is not None and
                  write_mesh(os.path.join(work, "model_mesh.mail"), md) and
                  generate_AsterSolver_files(
                      work, md, os.path.join(work, "model_mesh.mail"),
                      "test.resu"))
            check(bool(ok), "files generated (result_route {0})".format(
                value))
            comm = io.open(os.path.join(work, "study.comm"),
                           encoding="utf-8").read()
            texts.append(comm.replace(work.replace("\\", "\\\\"),
                                      "<WORK>").replace(work, "<WORK>"))
            export = io.open(os.path.join(work, "study.export"),
                             encoding="utf-8").read()
            check(" R 8" not in export and ".resu" not in export,
                  "no .resu in the .export (result_route {0})".format(value))
        check(texts[0] == texts[1],
              "a kept result_route 'tabel' gives the same .comm")
        check("POST_RELEVE_T(" not in texts[0] and
              "aster_results_export" in texts[0],
              "the .comm has the result export, no tables")
    finally:
        cfg.pop("result_route", None)
        cfg.update(saved)


def test_save_keeps_line(tmp):
    import bridge_gui
    path = os.path.join(tmp, "bridge_utils_copy.py")
    shutil.copy(os.path.join(SCRIPTS, "bridge_utils.py"), path)
    text = io.open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    text = text.replace('    "ncpus":', '    "result_route":    "tabel",' +
                        nl + '    "ncpus":', 1)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    errors = bridge_gui.save_to_bridge_utils(
        [(None, "ncpus", "int", 1, 4)], path)
    after = io.open(path, encoding="utf-8", newline="").read()
    check(errors == [], "save of another setting: no errors {0}".format(
        errors))
    check(after.count('"result_route":    "tabel",') == 1 and
          re.search(r'"ncpus":\s+4,', after) is not None,
          "the orphan result_route line stays once; ncpus saved")


def main():
    tmp = tempfile.mkdtemp(prefix="route_removed_")
    saved = u.CONFIG_BRIDGE.get("work_dir", "")
    u.CONFIG_BRIDGE["work_dir"] = tmp
    try:
        test_note()
        test_no_reader()
        test_same_comm(tmp)
        test_save_keeps_line(tmp)
    finally:
        u.CONFIG_BRIDGE["work_dir"] = saved
        shutil.rmtree(tmp, True)
    if _FAILED:
        print("{0} failure(s)".format(len(_FAILED)))
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
