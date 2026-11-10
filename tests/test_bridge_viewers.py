# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_viewers (buttons ParaView and AsterStudy of the
# Results dialog and the convergence window), CPython 3 and IronPython 2.7:
# the Salome-Meca search and the ParaView search on fake installations in a
# temporary folder (never the real ones of this PC), the choice of the
# result file of a run, the command lines with a fake Popen (nothing is
# started), refused paths for .bat launchers, the session script for
# AsterStudy (a Python 3 literal for any path; under CPython it is also
# compiled), the guard against a second Salome start and the messages in
# both languages. Only CONFIG_BRIDGE in memory.
#
#   python tests/test_bridge_viewers.py
#   (IronPython: TestFiles/Tools/run_ipy.ps1 tests/test_bridge_viewers.py)

from __future__ import print_function

import ast
import io
import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
import bridge_viewers as v  # noqa: E402

CFG = bridge_utils.CONFIG_BRIDGE
# bridge_viewers logs a start: not into the real work folder's log
bridge_utils.log = lambda *args, **kw: None
CFG["language"] = "en"
CFG["paraview_exe"] = ""
CFG["salome_meca_dir"] = ""
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _norm(p):
    return os.path.normcase(os.path.normpath(p))


def _touch(path, text=u""):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    f = io.open(path, "w", encoding="utf-8")
    f.write(text)
    f.close()
    return path


def _salome(root, version=None, asterstudy=True, paraview=True):
    if version:
        _touch(os.path.join(root, "README"),
               u"Application: SALOME-{0}\n".format(version))
    if asterstudy:
        _touch(os.path.join(root, "run_salome.bat"))
        _touch(os.path.join(root, "salome"))
        os.makedirs(os.path.join(root, "W64", "ASTERSTUDY"))
    if paraview:
        _touch(os.path.join(root, "run_paraview.bat"))
        _touch(os.path.join(root, "W64", "ParaView", "bin", "paraview.exe"))
    return root


class FakePopen(object):
    calls = []

    def __init__(self, cmd, **kw):
        FakePopen.calls.append((cmd, kw))
        self.pid = 4242


def build(tmp):
    """Fake drive with three Salome trees and three official ParaViews."""
    drive = os.path.join(tmp, "C")
    pf = os.path.join(drive, "Program Files")
    t = {"env": {"SystemDrive": drive, "ProgramFiles": pf},
         "new": _salome(os.path.join(drive, "SALOME-MECA", "2025"),
                        "9.13.0"),
         "old": _salome(os.path.join(drive, "Salome_meca", "V2023"),
                        "9.10.0", paraview=False),
         "noname": _salome(os.path.join(drive, "Salome_meca", "V2099"),
                           None, paraview=False),
         "pvonly": _salome(os.path.join(pf, "SALOME-9.12"), None,
                           asterstudy=False),
         "pv510": _touch(os.path.join(pf, "ParaView 5.10.1", "bin",
                                      "paraview.exe")),
         "pv62": _touch(os.path.join(
             pf, "ParaView 6.2.0-Windows-Python3.12-msvc2017-AMD64", "bin",
             "paraview.exe")),
         "pv610": _touch(os.path.join(pf, "ParaView 6.10.0", "bin",
                                      "paraview.exe"))}
    t["bases"] = v.salome_bases(t["env"])
    return t


def test_salome_search(t):
    bases = t["bases"]
    check(any(_norm(b).endswith(_norm(os.path.join("C", "SALOME-MECA")))
              for b in bases), "bases include %SystemDrive%\\SALOME-MECA")
    check(_norm(v.find_salome("", bases)) == _norm(t["new"]),
          "AsterStudy root: the newest version (9.13 before 9.10, and "
          "before V2099 that only has a folder name)")
    check(v.find_salome("", [os.path.join(t["env"]["ProgramFiles"])]) == "",
          "a Salome without AsterStudy is no AsterStudy root")
    check(_norm(v.find_salome(t["old"], bases)) == _norm(t["old"]),
          "setting = a root: that root")
    check(_norm(v.find_salome(os.path.dirname(t["new"]), bases)) ==
          _norm(t["new"]), "setting = a folder of roots: the newest in it")
    os.environ["MAB_TEST_SALOME"] = os.path.dirname(t["old"])
    try:
        check(_norm(v.find_salome("%MAB_TEST_SALOME%", bases)) ==
              _norm(t["old"]), "setting with an environment variable")
    finally:
        os.environ.pop("MAB_TEST_SALOME", None)
    CFG["salome_meca_dir"] = t["old"]
    check(_norm(v.find_salome(None, bases)) == _norm(t["old"]),
          "None = the setting salome_meca_dir")
    CFG["salome_meca_dir"] = ""
    check(v.salome_version(t["pvonly"]) == "SALOME-9.12",
          "version from the folder name without README")
    bats = [_norm(p) for p in v.salome_paraviews("", bases)]
    check(bats == [_norm(os.path.join(t["new"], "run_paraview.bat")),
                   _norm(os.path.join(t["pvonly"], "run_paraview.bat"))],
          "Salome ParaViews: own check (also without AsterStudy), newest "
          "first")


def test_paraview_search(t):
    env, bases = t["env"], t["bases"]
    new_bat = os.path.join(t["new"], "run_paraview.bat")
    old_bat = os.path.join(t["pvonly"], "run_paraview.bat")
    got = [_norm(p) for p in v.paraview_candidates(False, "", bases, env)]
    check(got == [_norm(p) for p in (t["pv610"], t["pv62"], new_bat,
                                     old_bat, t["pv510"])],
          ".pvd: ParaView 6.x (newest first), Salome's, then 5.10")
    got = [_norm(p) for p in v.paraview_candidates(True, "", bases, env)]
    check(got == [_norm(p) for p in (new_bat, old_bat)],
          ".rmed: only Salome's (official 6.x does not load MEDReader, "
          "5.10 has none)")
    check(v.paraview_version(t["pv62"]) == (6, 2, 0) and
          v.paraview_version(t["pv510"]) == (5, 10, 1),
          "version from the folder name")
    check(_norm(v.paraview_exe(t["pv510"], True, "", bases, env)) ==
          _norm(t["pv510"]), "a filled-in setting always wins")
    salome_exe = os.path.join(t["new"], "W64", "ParaView", "bin",
                              "paraview.exe")
    check(_norm(v.paraview_exe(salome_exe, False, "", bases, env)) ==
          _norm(new_bat),
          "Salome's paraview.exe is started through run_paraview.bat")
    check(_norm(v.paraview_exe("", True, "", bases, env)) == _norm(new_bat),
          "empty setting, .rmed: Salome's ParaView")
    check(v.paraview_exe("", False, "", [], {}) == "",
          "nothing installed: empty")


def test_files(tmp):
    work = os.path.join(tmp, "work")
    base = os.path.join(work, "Model_20261110_120000")
    check(v.run_base(base + "_results.xml") == base and
          v.run_base(base + ".mess") == base, "run base from a run file")
    check(v.choose_file(v.result_files(base)) == (None, []),
          "no result files")
    _touch(base + ".rmed")
    check(v.choose_file(v.result_files(base)) == (base + ".rmed", []),
          "only the .rmed")
    _touch(base + ".pvd")
    check(v.choose_file(v.result_files(base)) == (base + ".pvd",
                                                  [base + ".rmed"]),
          ".pvd before .rmed for ParaView")
    check(v.choose_file(v.result_files(base), True) == (base + ".rmed", []),
          "AsterStudy: MED only")
    _touch(base + "_verfijnd.rmed")
    _touch(base + "_xfem.rmed")
    path, others = v.choose_file(v.result_files(base))
    check(path == base + "_verfijnd.rmed" and others == [
        base + "_xfem.rmed", base + ".pvd", base + ".rmed"],
        "refined mesh first, then the crack mesh, then .pvd, .rmed")
    return base


def test_open_paraview(t, base):
    env, bases = t["env"], t["bases"]
    FakePopen.calls[:] = []
    ok, text = v.open_paraview(base + "_none", "", "", FakePopen, bases, env)
    check(not ok and "vtu_export" in text and "med_export" in text and
          not FakePopen.calls, "no result file: message, nothing started")
    os.remove(base + "_verfijnd.rmed")
    os.remove(base + "_xfem.rmed")
    ok, text = v.open_paraview(base, "", "", FakePopen, bases, env)
    cmd, kw = FakePopen.calls[-1]
    check(ok and [_norm(c) for c in cmd] == [_norm(t["pv610"]),
                                             _norm(base + ".pvd")],
          ".pvd opens in the newest official ParaView")
    check(kw["creationflags"] == v.CREATE_NO_WINDOW and kw["stdout"]
          is not None and "PYTHONPATH" not in kw["env"],
          "no window, output to a log, clean environment")
    check("Model_20261110_120000.rmed" in text,
          "message names the other result file")
    os.remove(base + ".pvd")
    ok, text = v.open_paraview(base, "", "", FakePopen, bases, env)
    check(ok and _norm(FakePopen.calls[-1][0][0]) == _norm(os.path.join(
        t["new"], "run_paraview.bat")), ".rmed opens in Salome's ParaView")
    ok, text = v.open_paraview(base, "", "", FakePopen, [], {})
    check(not ok and "paraview_exe" in text, "no ParaView: message")
    bad = os.path.join(os.path.dirname(base), "A&B", "M_20261110_120000")
    _touch(bad + ".rmed")
    n = len(FakePopen.calls)
    ok, text = v.open_paraview(bad, "", "", FakePopen, bases, env)
    check(not ok and "A&B" in text and len(FakePopen.calls) == n,
          "& in the path of a .bat launch: refused, nothing started")
    ok, text = v.open_paraview(bad, t["pv62"], "", FakePopen, bases, env)
    check(ok, "the same path with a plain paraview.exe (no cmd.exe): "
          "started")


def test_asterstudy(t, tmp):
    bases = t["bases"]
    FakePopen.calls[:] = []
    folder = os.path.join(tmp, u"Mödel's werk (1)")
    base = os.path.join(folder, "M_20261110_130000")
    ok, text = v.open_asterstudy(base, "", FakePopen, bases)
    check(not ok and "med_export" in text and not FakePopen.calls,
          "no .rmed: message names med_export")
    _touch(base + ".pvd")
    ok, text = v.open_asterstudy(base, "", FakePopen, bases)
    check(not ok and not FakePopen.calls, "only a .pvd: no converter")
    med = _touch(base + ".rmed")
    ok, text = v.open_asterstudy(base, "", FakePopen, [])
    check(not ok and "salome_meca_dir" in text, "no Salome: message")
    def broken(cmd, **kw):
        raise OSError("python3.exe missing")
    ok, text = v.open_asterstudy(base, "", broken, bases)
    check(not ok and "python3.exe missing" in text and not os.path.isfile(
        v.salome_files(med)[1]), "failed start: message, no busy session "
          "log left")
    ok, text = v.open_asterstudy(base, "", FakePopen, bases)
    script, session_log, launch_log = v.salome_files(med)
    cmd, kw = FakePopen.calls[-1]
    check(ok and [_norm(c) for c in cmd] == [
        _norm(os.path.join(t["new"], "W64", "Python", "python3.exe")),
        _norm(os.path.join(t["new"], "salome")), "start", _norm(script)],
        "command: Salome's Python, the launcher, start, the script")
    check(_norm(kw["cwd"]) == _norm(t["new"]) and kw["env"].get("DEBUG")
          == "-1" and kw["env"].get("ASTER_NO_EXCEPTHANDLER") == "1" and
          "PYTHONHOME" not in kw["env"], "cwd root, Salome's environment")
    check(script.endswith("M_20261110_130000_salome.py") and
          os.path.isfile(script) and os.path.isfile(session_log),
          "session script and log next to the .rmed")
    f = io.open(script, "r", encoding="utf-8")
    text_script = f.read()
    f.close()
    m = re.search(r"^MED_PATH = (.*)$", text_script, re.M)
    check(m is not None and ast.literal_eval(u"u" + m.group(1)) ==
          os.path.abspath(med),
          "MED path as a literal (non-ASCII, quote, spaces, backslashes)")
    # e acute, quotes, a backslash, U+1F600 (a surrogate pair in
    # IronPython), the euro sign
    odd = (u"C:/x/\u00e9 \"q\" \\ " + u"\ud83d\ude00" + u" \u20ac"
           if sys.version_info[0] < 3 else
           u"C:/x/\u00e9 \"q\" \\ \U0001f600 \u20ac")
    # u prefix: Python 2 semantics under IronPython (\u only in u"")
    check(ast.literal_eval(u"u" + v._literal(odd)) == odd,
          "literal round trip: quote, backslash, astral and BMP characters")
    check(all(ord(c) < 128 for c in text_script),
          "session script is pure ASCII (same from IronPython and CPython)")
    if sys.version_info[0] >= 3:
        try:
            compile(text_script, script, "exec")
            compiled = True
        except SyntaxError:
            compiled = False
        check(compiled, "session script compiles under Python 3")
    n = len(FakePopen.calls)
    ok, text = v.open_asterstudy(base, "", FakePopen, bases)
    check(not ok and len(FakePopen.calls) == n and "already" in text,
          "second click within 60 s: message, no second Salome")
    later = os.path.getmtime(session_log) + v.SALOME_BUSY_SECONDS + 1
    ok, text = v.open_asterstudy(base, "", FakePopen, bases, now=later)
    check(ok and len(FakePopen.calls) == n + 1, "after 60 s: a new session")
    comma = os.path.join(tmp, "a,b", "M_20261110_140000")
    _touch(comma + ".rmed")
    n = len(FakePopen.calls)
    ok, text = v.open_asterstudy(comma, "", FakePopen, bases)
    check(not ok and len(FakePopen.calls) == n and "a,b" in text,
          "comma in the script path: refused (launcher argument separator)")
    _touch(base + "_xfem.rmed")
    ok, text = v.open_asterstudy(base, "", FakePopen, bases,
                                 now=later + 1000)
    check(ok and FakePopen.calls[-1][0][-1].endswith("_xfem_salome.py") and
          "M_20261110_130000.rmed" in text,
          "XFEM: the crack mesh, the other file named")


def test_languages(t, base):
    seen = {}
    for lang in ("nl", "en"):
        CFG["language"] = lang
        seen[lang] = [
            v.open_paraview(base + "_none", "", "", FakePopen, [], {})[1],
            v.open_asterstudy(base + "_none", "", FakePopen, [])[1],
            v._unsafe_text(u"X&Y")]
    CFG["language"] = "en"
    check(all(a != b for a, b in zip(seen["nl"], seen["en"])),
          "messages differ per language")
    check(not any(re.search(r"\{\d\}", s) for s in seen["nl"] + seen["en"]),
          "no placeholder left unfilled")


def main():
    tmp = tempfile.mkdtemp(prefix="mab_viewers_")
    try:
        t = build(tmp)
        test_salome_search(t)
        test_paraview_search(t)
        base = test_files(tmp)
        test_open_paraview(t, base)
        test_asterstudy(t, tmp)
        test_languages(t, base)
    finally:
        CFG["salome_meca_dir"] = ""
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
