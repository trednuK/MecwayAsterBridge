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
#   - is_processed: the marker, and the node numbers when the marker is
#     gone.
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
    status, text = bhf.apply(liml, expected=5)
    check("status done", status == "done", (status, text))
    check("text names the count and the way back",
          text.startswith(u"3 failed element(s) hidden") and
          u"Results... > Load" in text, text)
    check("two failed at the last step stay visible (note)",
          u"2 failed element(s) stay visible" in text, text)
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
    check("is_processed by the node numbers", bhf.is_processed(stripped))
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
