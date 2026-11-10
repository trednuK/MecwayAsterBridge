# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of Scripts/bridge_hide_failed.py (setting hide_failed), on
# copies of the golden fixture tests/data/liml_failed/golden_failed.liml
# and with a fake core for the refusals:
#   - success: the model is the processed file, the unprocessed one is
#     <liml>.unhidden.tmp until finish() (or restore() puts it back), no
#     .hide.tmp is left; the note on elements that stay visible;
#   - silent skip for no_timesteps, modal_result, no_flag_source and for
#     "nothing failed", with the file unchanged;
#   - a WARNING for other refusals and for an already processed file, with
#     the model unchanged and the temporary file removed;
#   - is_processed: the marker, and the node copies of model elements when
#     the marker is gone (Mecway 35 drops it on a save); apply then warns;
#   - hide_and_open with a fake Mecway: success, open failure (restore and
#     open again, both opens failing, restore failing), errors in apply
#     before and after the rename, a failing rename, a stale
#     .unhidden.tmp, the configuration passed on.
# The section view (shells above the model's numbers) is tested in
# tests/test_bridge_section_results.py.
# Python 2.7 (IronPython) and 3; under CPython it also runs once in
# Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1) when Mecway is
# installed.
#
#   python tests/test_bridge_hide_failed.py

from __future__ import print_function

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
import bridge_hide_failed as bhf  # noqa: E402
import liml_failed as L  # noqa: E402

GOLDEN = os.path.join(_HERE, "data", "liml_failed", "golden_failed.liml")
IRONPYTHON = sys.platform == "cli"
FAILED = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def leftovers(liml):
    return [s for s in (bhf.TMP_SUFFIX, bhf.KEEP_SUFFIX)
            if os.path.exists(liml + s)]


class FakeCore(object):
    """Replaces liml_failed.process for one call."""

    def __init__(self, code=None, write=False):
        self.code = code
        self.write = write
        self.saved = L.process

    def __enter__(self):
        def process(in_path, out_path, **kw):
            if self.write:
                with open(out_path, "wb") as f:
                    f.write(b"partial")
            if self.code == "nothing":
                return {"written": False, "failed_count": 0,
                        "messages": []}
            raise L.LimlFailedError(self.code, *([u"x"] * 3))
        L.process = process
        return self

    def __exit__(self, *exc):
        L.process = self.saved


def test_success(tmp):
    print("-- success")
    liml = os.path.join(tmp, "model.liml")
    shutil.copy(GOLDEN, liml)
    original = read(liml)
    check("not processed before", not bhf.is_processed(liml))
    status, text = bhf.apply(liml, expected=set([u"1", u"2", u"4", u"5",
                                                  u"6"]))
    check("status done", status == "done", (status, text))
    check("text names the count and the way back",
          text.startswith(u"3 failed element(s) hidden") and
          u"Results... > Load" in text, text)
    check("two failed elements of the run not hidden stay visible (note)",
          u"2 failed element(s) of the run stay visible" in text, text)
    check("no section-view sentence without shells",
          u"section view" not in text, text)
    check("model is the processed file",
          L.processed_marker(liml) == L.VERSION)
    check("unprocessed file kept until finish",
          read(liml + bhf.KEEP_SUFFIX) == original)
    check("no .hide.tmp left", not os.path.exists(liml + bhf.TMP_SUFFIX))
    check("is_processed by the marker", bhf.is_processed(liml))
    processed = read(liml)
    check("restore puts the unprocessed file back",
          bhf.restore(liml) and read(liml) == original and
          not leftovers(liml))
    status, _text = bhf.apply(liml)
    bhf.finish(liml)
    check("finish drops the unprocessed copy",
          status == "done" and not leftovers(liml) and
          read(liml) == processed)
    # already processed: WARNING, unchanged
    status, text = bhf.apply(liml)
    check("a processed file gives a warning", status == "warning" and
          u"already have the failed elements hidden" in text, text)
    check("... and stays unchanged", read(liml) == processed and
          not leftovers(liml))
    # the marker gone (a re-save that drops it, NOT verified): node numbers
    stripped = os.path.join(tmp, "stripped.liml")
    with open(stripped, "wb") as f:
        f.write(processed.replace(b' limlfailed="' +
                                  L.VERSION.encode("ascii") + b'"', b""))
    check("marker removed in the copy", L.processed_marker(stripped) is None)
    check("is_processed by the node copies of model elements",
          bhf.is_processed(stripped))
    stripped_before = read(stripped)
    status, text = bhf.apply(stripped)
    check("a processed file without marker gives the 'already hidden' "
          "warning", status == "warning" and
          u"already have the failed elements hidden (marker lost" in text,
          text)
    check("... and stays unchanged", read(stripped) == stripped_before and
          not leftovers(stripped))
    check("the original is not processed", not bhf.is_processed(GOLDEN))


def test_skip_and_refusals(tmp):
    print("-- skip and refusals")
    liml = os.path.join(tmp, "fake.liml")
    shutil.copy(GOLDEN, liml)
    original = read(liml)
    for code in ("no_timesteps", "modal_result", "no_flag_source",
                 "nothing"):
        with FakeCore(code, write=True):
            status, text = bhf.apply(liml)
        check("{0}: silent skip".format(code),
              status == "skip" and text == u"", (status, text))
        check("{0}: model unchanged, no temporary file".format(code),
              read(liml) == original and not leftovers(liml))
    with FakeCore("nothing"):
        status, text = bhf.apply(liml, expected=set([u"7"]))
    check("nothing written but a failed element of the run: the note "
          "reaches the status box", status == "skip" and
          u"1 failed element(s) of the run stay visible" in text,
          (status, text))
    for code in ("failed_contract", "configurations", "value_count",
                 "layout"):
        with FakeCore(code, write=True):
            status, text = bhf.apply(liml)
        check("{0}: warning with the core's text".format(code),
              status == "warning" and
              text.startswith(u"Failed elements not hidden: ") and
              text.endswith(u"The model is unchanged."), (status, text))
        check("{0}: model unchanged, temporary file removed".format(code),
              read(liml) == original and not leftovers(liml))
    bridge_utils.CONFIG_BRIDGE["language"] = "nl"
    try:
        with FakeCore("configurations"):
            status, text = bhf.apply(liml)
    finally:
        bridge_utils.CONFIG_BRIDGE["language"] = "en"
    check("Dutch: the core's Dutch text", status == "warning" and
          u"kies een configuratie" in text, text)
    status, text = bhf.apply(os.path.join(tmp, "missing.liml"))
    check("missing file: warning", status == "warning" and
          u"file not found" in text, text)
    static = os.path.join(tmp, "static.liml")
    with io.open(static, "w", encoding="utf-8", newline="") as f:
        f.write(u'<liml version="34">\r\n  <node nid="1" x="0" y="0" z="0" />'
                u'\r\n</liml>\r\n')
    status, text = bhf.apply(static)
    check("model without results: warning (no_solution)",
          status == "warning" and u"no solved results" in text, text)
    check("restore without a kept file is False", not bhf.restore(static))


class FakeMecway(object):
    """open_fn and activate_fn of hide_and_open; fail: how many opens
    raise before one works."""

    def __init__(self, fail=0):
        self.fail = fail
        self.opened = []
        self.active = []

    def open(self, path):
        self.opened.append(read(path))
        if self.fail:
            self.fail -= 1
            raise RuntimeError("cannot open")

    def activate(self, configuration):
        self.active.append(configuration)


def hide(liml, mw, configuration=None, expected=None):
    return bhf.hide_and_open(liml, configuration, expected,
                             open_fn=mw.open, activate_fn=mw.activate)


def fresh(tmp, name):
    liml = os.path.join(tmp, name)
    shutil.copy(GOLDEN, liml)
    for suffix in (bhf.TMP_SUFFIX, bhf.KEEP_SUFFIX):
        bhf._remove(liml + suffix)
    return liml, read(liml)


def test_hide_and_open(tmp):
    print("-- hide_and_open (fake Mecway)")
    config = bridge_utils.CONFIG_BRIDGE
    saved = config.get("hide_failed", False)
    try:
        config["hide_failed"] = False
        liml, original = fresh(tmp, "open_off.liml")
        mw = FakeMecway()
        check("option off: nothing done", hide(liml, mw) ==
              (False, True, u"") and not mw.opened and
              read(liml) == original)
        config["hide_failed"] = True
        # success
        liml, original = fresh(tmp, "open_ok.liml")
        mw = FakeMecway()
        opened, ok, text = hide(liml, mw)
        check("success: opened once, the processed file", opened and ok and
              len(mw.opened) == 1 and L.processed_marker(liml) == L.VERSION
              and mw.opened[0] == read(liml), text)
        check("success: unprocessed copy dropped, no configuration made "
              "active", not leftovers(liml) and mw.active == [])
        # the open fails, the restored file opens
        liml, original = fresh(tmp, "open_fail.liml")
        mw = FakeMecway(fail=1)
        opened, ok, text = hide(liml, mw)
        check("open failure: restored and opened again", opened and ok and
              len(mw.opened) == 2 and mw.opened[1] == original and
              read(liml) == original and not leftovers(liml) and
              u"were put back" in text, text)
        # both opens fail
        liml, original = fresh(tmp, "open_fail2.liml")
        mw = FakeMecway(fail=2)
        opened, ok, text = hide(liml, mw)
        check("both opens fail: not ok, the file is the unprocessed one",
              opened and not ok and read(liml) == original and
              not leftovers(liml) and u"are back in" in text, text)
        # the open fails and restore fails: not ok, the kept file named
        liml, original = fresh(tmp, "open_norestore.liml")
        mw = FakeMecway(fail=1)
        keep_restore = bhf.restore
        bhf.restore = lambda path: False
        try:
            opened, ok, text = hide(liml, mw)
        finally:
            bhf.restore = keep_restore
        check("open and restore fail: not ok, names the kept file",
              opened and not ok and len(mw.opened) == 1 and
              (liml + bhf.KEEP_SUFFIX) in text, text)
        check("... which holds the unprocessed results",
              read(liml + bhf.KEEP_SUFFIX) == original)
        bhf.restore(liml)
        # an error in apply before the rename: model untouched
        liml, original = fresh(tmp, "apply_error.liml")
        mw = FakeMecway()
        keep_max = bhf._model_max_eid

        def broken(path):
            raise ValueError("broken")
        bhf._model_max_eid = broken
        try:
            opened, ok, text = hide(liml, mw)
        finally:
            bhf._model_max_eid = keep_max
        check("apply error before the rename: model untouched, caller "
              "opens it, bilingual text", not opened and ok and
              read(liml) == original and not leftovers(liml) and
              text.startswith(u"Failed elements not hidden: broken") and
              not mw.opened, text)
        # an error in apply after the second rename: restored
        liml, original = fresh(tmp, "apply_late_error.liml")
        mw = FakeMecway()
        keep_log = bhf.log

        def failing_log(line):
            if u"element(s) hidden in" in line:
                raise ValueError("late")
            keep_log(line)
        bhf.log = failing_log
        try:
            opened, ok, text = hide(liml, mw)
        finally:
            bhf.log = keep_log
        check("apply error after the rename: the original is put back",
              not opened and ok and read(liml) == original and
              not leftovers(liml) and u"late" in text, text)
        # the second rename fails: renamed back, model unchanged
        liml, original = fresh(tmp, "rename_fail.liml")
        liml2, original2 = fresh(tmp, "rename_fail2.liml")
        keep_rename = os.rename
        back = [True]

        def rename(src, dst):
            if src.endswith(bhf.TMP_SUFFIX) and dst in (liml, liml2):
                raise OSError("locked")
            if src.endswith(bhf.KEEP_SUFFIX) and not back[0]:
                raise OSError("locked too")
            keep_rename(src, dst)
        os.rename = rename
        try:
            status, text = bhf.apply(liml)
            same = read(liml) == original and not leftovers(liml)
            back[0] = False
            status2, text2 = bhf.apply(liml2)
        finally:
            os.rename = keep_rename
        check("second rename fails: renamed back, warning", same and
              status == "warning" and u"locked" in text, text)
        check("... and when the rename back fails too, the warning names "
              "the file to rename", status2 == "warning" and
              not os.path.exists(liml2) and
              (liml2 + bhf.KEEP_SUFFIX) in text2 and
              read(liml2 + bhf.KEEP_SUFFIX) == original2, text2)
        mw = FakeMecway()
        opened, ok, text = hide(liml2, mw)
        check("hide_and_open on the missing model: not ok, not opened, "
              "names the kept file", opened and not ok and not mw.opened and
              (liml2 + bhf.KEEP_SUFFIX) in text, text)
        check("leftover_text names the kept file",
              (liml2 + bhf.KEEP_SUFFIX) in bhf.leftover_text(liml2))
        os.rename(liml2 + bhf.KEEP_SUFFIX, liml2)
        check("leftover_text without a kept file is empty",
              bhf.leftover_text(liml2) == u"" and
              bhf.leftover_text("") == u"")
        # a stale .unhidden.tmp of an earlier session
        liml, original = fresh(tmp, "stale.liml")
        with open(liml + bhf.KEEP_SUFFIX, "wb") as f:
            f.write(b"old")
        mw = FakeMecway(fail=1)
        opened, ok, text = hide(liml, mw)
        check("stale kept file: removed, never put over the model",
              opened and ok and read(liml) == original and
              not leftovers(liml), text)
        # the configuration reaches the core and activate_fn
        liml, original = fresh(tmp, "configuration.liml")
        seen = []
        keep_process = L.process

        def process(in_path, out_path, **kw):
            seen.append(kw.get("configuration"))
            kw["configuration"] = None      # the fixture has none
            return keep_process(in_path, out_path, **kw)
        L.process = process
        mw = FakeMecway()
        try:
            opened, ok, text = hide(liml, mw, configuration=u"Case B")
        finally:
            L.process = keep_process
        check("configuration passed to the core and made active",
              opened and ok and seen == [u"Case B"] and
              mw.active == [u"Case B"], (seen, mw.active, text))
    finally:
        config["hide_failed"] = saved


def run_in_ironpython():
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="hide_failed_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_hide_failed.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_bridge_hide_failed as t\n"
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
    tmp = tempfile.mkdtemp(prefix="hide_failed_")
    # the log of the tests goes to the temporary folder (in memory only)
    saved = bridge_utils.CONFIG_BRIDGE.get("work_dir", "")
    bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
    try:
        test_success(tmp)
        test_skip_and_refusals(tmp)
        test_hide_and_open(tmp)
        with io.open(os.path.join(tmp, bridge_utils.log_file_name()),
                     encoding="utf-8") as f:
            text = f.read()
        check("log: WARNING for the refusals and INFO for the skips",
              text.count(u"WARNING: Failed elements not hidden") >= 6 and
              u"INFO: Hide failed elements: not applied (no_timesteps"
              in text and u"element(s) hidden in" in text)
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
