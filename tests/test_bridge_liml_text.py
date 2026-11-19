# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of Scripts/bridge_liml_text.py (mw.liml_text() of Mecway 36),
# with a fake mw and texts recorded from a hidden Mecway 36.0.9815
# (tests/data/liml_text: <model>_text.txt = liml_text(False),
# <model>_saved.liml = save_as of the same model; Voorbeeld_A with kg/m3
# superscript, LS-97a with ** ASTER-SECTIE and SECTIE-VORM lines):
#   - feature detection: without the method every function returns None;
#   - a call that raises, an empty text, a text that is no .liml: None and
#     a WARNING;
#   - a stray <solution> block is cut (not <solutions...>), CRLF from the
#     text is normalised;
#   - write_snapshot: CRLF only, UTF-8 without BOM, equal to the saved file
#     minus its <solution> block; a failing write leaves no file;
#   - model_data read from the snapshot equals model_data read from the
#     saved file (two parser paths in bridge_from_liml: ET.parse without
#     <solution>, ET.fromstring with one);
#   - temp_snapshot / remove leave nothing behind.
# Python 2.7 (IronPython) and 3; under CPython it also runs once in
# Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1) when Mecway is
# installed.
#
#   python tests/test_bridge_liml_text.py

from __future__ import print_function

import glob
import io
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
sys.dont_write_bytecode = True
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_liml_text as blt  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402

DATA = os.path.join(_HERE, "data", "liml_text")
IRONPYTHON = sys.platform == "cli"
FAILED = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


def read_text(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as f:
        return f.read().replace(u"\r\n", u"\n")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


class FakeMw(object):
    """mw with liml_text(solution) returning text (or raising it)."""

    def __init__(self, text):
        self.text = text
        self.calls = []

    def liml_text(self, solution=True):
        self.calls.append(solution)
        if isinstance(self.text, Exception):
            raise self.text
        return self.text


class OldMw(object):
    """mw of Mecway 33-35: no liml_text."""

    def file_name(self):
        return u"model.liml"


def test_detection(tmp):
    old = OldMw()
    check("without liml_text: not available", not blt.available(old))
    check("without liml_text: model_text None", blt.model_text(old) is None)
    path = os.path.join(tmp, "old.liml")
    check("without liml_text: no snapshot, no file",
          blt.write_snapshot(old, path) is None and not os.path.exists(path))
    check("without liml_text: no temporary snapshot",
          blt.temp_snapshot(old) is None)
    mw = FakeMw(u'<liml version="36">\n</liml>\n')
    check("with liml_text: available", blt.available(mw))
    blt.model_text(mw)
    check("liml_text called with solution=False", mw.calls == [False],
          mw.calls)


def test_refusals():
    for name, value in (("raises", RuntimeError("boom")), ("empty", u""),
                        ("None", None), ("no .liml", u"<html></html>")):
        check("liml_text {0}: model_text None".format(name),
              blt.model_text(FakeMw(value)) is None)


def test_cut_and_newlines():
    text = (u'<liml version="36">\r\n  <solutions-note a="1" />\r\n'
            u'  <solution>\r\n    <x />\r\n  </solution>\r\n</liml>\r\n')
    got = blt.model_text(FakeMw(text))
    check("stray <solution> cut, <solutions-note> kept, LF only",
          got == u'<liml version="36">\n  <solutions-note a="1" />\n  '
                 u'</liml>', repr(got))
    got = blt.model_text(FakeMw(u'\ufeff<liml version="36" />'))
    check("a leading BOM is accepted", got is not None)


def test_snapshot_bytes(tmp):
    for model in ("voorbeeld_a", "ls97a"):
        text = read_text(model + "_text.txt")
        path = os.path.join(tmp, model + "_snap.liml")
        check(model + ": write_snapshot returns the path",
              blt.write_snapshot(FakeMw(text), path) == path)
        data = read_bytes(path)
        check(model + ": no BOM, no declaration",
              not data.startswith(b"\xef\xbb\xbf") and
              data.startswith(b"<liml"))
        check(model + ": CRLF only", b"\r\r\n" not in data and
              data.count(b"\n") == data.count(b"\r\n"))
        saved = read_bytes(os.path.join(DATA, model + "_saved.liml"))
        saved = saved.replace(b"\r\n", b"\n")
        start = saved.find(b"  <solution>")
        end = saved.find(b"</solution>\n") + len(b"</solution>\n")
        expected = saved[:start] + saved[end:] if start >= 0 else saved
        check(model + ": equal to the saved file without <solution>",
              data.replace(b"\r\n", b"\n") == expected)
    data = read_bytes(os.path.join(tmp, "voorbeeld_a_snap.liml"))
    check("UTF-8 superscript three kept", b"kg/m\xc2\xb3" in data)


def _strip(model_data):
    d = dict(model_data)
    d.pop("liml_path", None)
    return d


def test_model_data(tmp):
    for model in ("voorbeeld_a", "ls97a"):
        snap = os.path.join(tmp, model + "_md.liml")
        blt.write_snapshot(FakeMw(read_text(model + "_text.txt")), snap)
        saved = os.path.join(tmp, model + "_saved.liml")
        shutil.copy(os.path.join(DATA, model + "_saved.liml"), saved)
        a = extract_aster_data_from_liml(snap)
        b = extract_aster_data_from_liml(saved)
        check(model + ": model_data read", a is not None and b is not None)
        if a is None or b is None:
            continue
        same = _strip(a) == _strip(b)
        diff = [k for k in set(a) | set(b)
                if k != "liml_path" and a.get(k) != b.get(k)]
        check(model + ": model_data of the snapshot equals the saved file",
              same, diff)
        check(model + ": liml_path is the snapshot", a["liml_path"] == snap)
    md = extract_aster_data_from_liml(os.path.join(tmp, "ls97a_md.liml"))
    shapes = (md or {}).get("aster_custom", {}).get("section_shapes")
    check("ls97a: section outline lines read from the snapshot",
          bool(shapes), shapes)


def test_write_failure(tmp):
    missing = os.path.join(tmp, "no_such_folder", "x.liml")
    check("write into a missing folder: None, no file",
          blt.write_snapshot(FakeMw(u'<liml version="36" />'), missing)
          is None and not os.path.exists(missing))
    if not IRONPYTHON:
        # a lone surrogate cannot be encoded in Python 3: no partial file
        path = os.path.join(tmp, "surrogate.liml")
        got = blt.write_snapshot(FakeMw(u'<liml a="\ud800" />'), path)
        check("unencodable text: None, no partial file",
              got is None and not os.path.exists(path))


def test_temp_snapshot():
    pattern = os.path.join(tempfile.gettempdir(), "mab_model_*.liml")
    before = set(glob.glob(pattern))
    path = blt.temp_snapshot(FakeMw(u'<liml version="36" />'))
    check("temp_snapshot writes a file", path is not None and
          os.path.exists(path))
    blt.remove(path)
    check("remove deletes it", path is not None and not os.path.exists(path))
    blt.remove(path)
    blt.remove(None)
    check("remove of a missing path or None is quiet", True)
    check("temp_snapshot of a failing liml_text leaves nothing",
          blt.temp_snapshot(FakeMw(RuntimeError("x"))) is None and
          set(glob.glob(pattern)) == before)


def test_decisions(tmp):
    saved = os.path.join(tmp, "m.liml")
    check("saved_path: a full path", blt.saved_path(saved) == saved)
    check("saved_path: untitled (None, empty, bare name)",
          blt.saved_path(None) is None and blt.saved_path("") is None and
          blt.saved_path("Untitled") is None)
    check("wants_snapshot: no API -> save first (Mecway 33-35)",
          not blt.wants_snapshot(False, "tabel", saved) and
          not blt.wants_snapshot(False, "liml", saved))
    check("wants_snapshot: route tabel, saved and untitled",
          blt.wants_snapshot(True, "tabel", saved) and
          blt.wants_snapshot(True, "tabel", None) and
          blt.wants_snapshot(True, "tabel", "Untitled"))
    check("wants_snapshot: route liml only for a saved model",
          blt.wants_snapshot(True, "liml", saved) and
          not blt.wants_snapshot(True, "liml", None) and
          not blt.wants_snapshot(True, "liml", "Untitled"))
    check("save_problem: folder gone",
          blt.save_problem(os.path.join(tmp, "gone", "m.liml")) == "folder")
    check("save_problem: new file in an existing folder",
          blt.save_problem(saved) is None)
    with io.open(saved, "w", encoding="utf-8") as f:
        f.write(u"<liml />")
    check("save_problem: writable file", blt.save_problem(saved) is None)
    os.chmod(saved, 0o444)
    try:
        check("save_problem: read-only file",
              blt.save_problem(saved) == "readonly")
    finally:
        os.chmod(saved, 0o666)
    snap = os.path.join(tmp, "snap.liml")
    text = u'<liml version="36">\n  <node nid="1" x="0" />\n</liml>'
    blt.write_snapshot(FakeMw(text), snap)
    check("same_text: unchanged model", blt.same_text(text, snap) is True)
    check("same_text: changed model", blt.same_text(
        text.replace(u'x="0"', u'x="1"'), snap) is False)
    check("same_text: no text -> None", blt.same_text(None, snap) is None)
    check("same_text: missing snapshot -> False",
          blt.same_text(text, os.path.join(tmp, "none.liml")) is False)
    check("clean_end: finished, no errors",
          blt.clean_end("finished", 0, [], False))
    check("clean_end: errors or exit code keep the copy",
          not blt.clean_end("finished", 0, ["x"], False) and
          not blt.clean_end("finished", 1, [], False))
    check("clean_end: stopped, closed, running keep the copy",
          not blt.clean_end("stopped", 0, [], True) and
          not blt.clean_end("closed", 0, [], True) and
          not blt.clean_end("running", 0, [], True))
    check("clean_end: confirmed follows the .mess",
          blt.clean_end("confirmed", 0, [], True) and
          not blt.clean_end("confirmed", 0, [], False))


def test_run_files_model(tmp):
    import bridge_results_liml as brl
    stem = "Plaat_20261119_101500"
    comm = os.path.join(tmp, stem + ".comm")
    for liml, expect in (
            (os.path.join(tmp, stem + "_model.liml"), "Plaat.liml"),
            (os.path.join(tmp, "elsewhere", "Plaat.liml"),
             os.path.join(tmp, "elsewhere", "Plaat.liml"))):
        with io.open(comm, "w", encoding="utf-8") as f:
            f.write(u"export_results(res, r'frag.xml', r'{0}')\n".format(
                liml))
        got = brl.run_files(os.path.join(tmp, stem + "_results.xml"))
        check("run_files names the model, not the copy ({0})".format(
            os.path.basename(liml)), got["model"] == expect, got["model"])


def run_in_ironpython():
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="liml_text_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_liml_text.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_bridge_liml_text as t\n"
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
    tmp = tempfile.mkdtemp(prefix="liml_text_")
    # the log of the tests goes to the temporary folder (in memory only)
    saved = bridge_utils.CONFIG_BRIDGE.get("work_dir", "")
    bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
    try:
        test_detection(tmp)
        test_refusals()
        test_cut_and_newlines()
        test_snapshot_bytes(tmp)
        test_model_data(tmp)
        test_write_failure(tmp)
        test_temp_snapshot()
        test_decisions(tmp)
        test_run_files_model(tmp)
        with io.open(os.path.join(tmp, bridge_utils.log_file_name()),
                     encoding="utf-8") as f:
            text = f.read()
        check("log: WARNING for the failing call and the bad text",
              u"WARNING: mw.liml_text() failed (boom)" in text and
              u"WARNING: mw.liml_text() returned no .liml text" in text)
    finally:
        bridge_utils.CONFIG_BRIDGE["work_dir"] = saved
        shutil.rmtree(tmp, True)
    if not IRONPYTHON:
        run_in_ironpython()
    if FAILED:
        print("{0} failure(s): {1}".format(len(FAILED), ", ".join(FAILED)))
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
