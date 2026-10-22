# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the work folder logic in bridge_utils (CPython, no
# Windows Forms): work_dir_beside_model puts the run files in <model>_aster
# next to the open .liml (set_model_path), falls back to work_dir without a
# model, path_too_long() follows the folder in use, and the automatic search
# for ParaView prefers a ParaView with a MED reader (Salome-Meca). Only
# CONFIG_BRIDGE in memory; bridge_utils.py itself is not written.
#
#   python tests/test_bridge_work_dir.py

from __future__ import print_function

import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils as u  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _norm(p):
    return os.path.normcase(os.path.normpath(p))


def test_work_dir(tmp):
    cfg = u.CONFIG_BRIDGE
    fixed = os.path.join(tmp, "Werk")
    liml = os.path.join(tmp, "Projecten", "Mijn Model (v2).liml")
    beside = os.path.join(tmp, "Projecten", "Mijn_Model_v2_aster")

    cfg["work_dir"], cfg["work_dir_beside_model"] = fixed, False
    u.set_model_path(liml)
    check(_norm(u.work_dir_path()) == _norm(fixed),
          "setting off: work_dir")

    cfg["work_dir_beside_model"] = True
    check(_norm(u.work_dir_path()) == _norm(beside),
          "setting on: <model>_aster next to the .liml (model_stem)")
    check(u.model_path() == liml, "model_path() returns the open model")

    u.set_model_path("")
    check(_norm(u.work_dir_path()) == _norm(fixed),
          "setting on, model not saved: fallback to work_dir")
    cfg["work_dir"] = ""
    check(_norm(u.work_dir_path()) == _norm(u.default_work_dir()),
          "setting on, no model, empty work_dir: default WorkDir")

    os.environ["BRIDGE_TEST_ROOT"] = tmp
    check(_norm(u.resolve_work_dir("%BRIDGE_TEST_ROOT%\\Werk", False, liml))
          == _norm(fixed), "resolve_work_dir: environment variables expanded")
    check(_norm(u.resolve_work_dir(fixed, True, liml)) == _norm(beside),
          "resolve_work_dir (start screen fields): next to the model")
    check(u.model_work_dir(None) is None, "model_work_dir without model: None")

    # run_name and the log follow the folder next to the model
    u.set_model_path(liml)
    cfg["work_dir"] = fixed
    u.set_run_log("20261022_120000", liml)
    log_path = os.path.join(beside, u.log_file_name())
    u.log("INFO: test")
    check(os.path.isfile(log_path), "log written in <model>_aster")
    check(not u.path_too_long(), "short folder: path not too long")
    u.set_run_log(None)

    # path_too_long() is computed with the folder next to the model
    deep = os.path.join(tmp, *(["x" * 40] * 6))
    u.set_model_path(os.path.join(deep, "Model.liml"))
    u.set_run_log("20261022_120000", "Model.liml")
    check(u.path_too_long(), "long model folder: path_too_long()")
    u.set_run_log(None)
    u.set_model_path(None)
    cfg["work_dir_beside_model"] = False


def test_paraview(tmp):
    cfg = u.CONFIG_BRIDGE
    pf = os.path.join(tmp, "Program Files")
    plain = os.path.join(pf, "ParaView 5.10.1", "bin", "paraview.exe")
    salome = os.path.join(pf, "SALOME-9.12", "W64", "ParaView", "bin",
                          "paraview.exe")
    for path in (plain, salome):
        os.makedirs(os.path.dirname(path))
        open(path, "w").close()
    saved = dict((k, os.environ.get(k)) for k in
                 ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"))
    try:
        for k in saved:
            os.environ.pop(k, None)
        os.environ["ProgramFiles"] = pf
        found = [p for p in u._paraview_candidates()
                 if _norm(p).startswith(_norm(tmp))]
        check([_norm(p) for p in found] == [_norm(salome), _norm(plain)],
              "candidates: Salome ParaView (MED reader) before plain one")
        cfg["paraview_exe"] = "%ProgramFiles%\\ParaView 5.10.1\\bin\\" \
                              "paraview.exe"
        check(_norm(u.paraview_exe_path()) == _norm(plain),
              "setting with environment variable is expanded")
        check(_norm(u.paraview_exe_path(plain)) == _norm(plain),
              "start screen field overrides the setting")
        cfg["paraview_exe"] = ""
        auto = u.paraview_exe_path()
        check(auto != "" and not _norm(auto).endswith(
            _norm(os.path.join("ParaView 5.10.1", "bin", "paraview.exe"))),
            "empty setting: a ParaView with MED reader is chosen first")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        cfg["paraview_exe"] = ""


def main():
    tmp = tempfile.mkdtemp(prefix="bridge_work_dir_")
    work_dir = u.CONFIG_BRIDGE.get("work_dir")
    try:
        test_work_dir(tmp)
        test_paraview(tmp)
    finally:
        u.CONFIG_BRIDGE["work_dir"] = work_dir
        u.set_model_path(None)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
