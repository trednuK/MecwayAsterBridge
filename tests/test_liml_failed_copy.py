# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Scripts/liml_failed.py is an unchanged copy of AdvancedToolsHub's
# common/liml_failed.py (contract failed/1, AGENTS.md). This test pins the
# pair (VERSION, sha256 with LF line endings) that the hub's own test pins,
# compares the copy with its source when that repository is next to this
# one (skipped otherwise), and runs the vendored golden fixture
# (tests/data/liml_failed, from the hub) through process() and scan().
# Python 2.7 (IronPython) and 3; under CPython it also runs itself once in
# Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1) when Mecway is
# installed.
#
#   python tests/test_liml_failed_copy.py

from __future__ import print_function

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_SCRIPTS = os.path.join(_HERE, "..", "Scripts")
sys.path.insert(0, _SCRIPTS)
sys.dont_write_bytecode = True
import liml_failed as L  # noqa: E402

# The same pair as PIN_VERSION / PIN_SHA256 in AdvancedToolsHub's
# tests/unit/test_liml_failed.py. Update both together, with the copy.
PIN_VERSION = "1.0.2"
PIN_SHA256 = "26e0b15ceea7f19c46d1ab39c50cf80f43a13229469f1c8cec12f5247789f04c"
# sha256 (LF) of the golden input and of its processed output, as the hub
GOLDEN_INPUT_SHA = "02b067d37bd2e3f01fb82eedefc0a17bb96ee4cf6751bb9566ccdf5b4770a85c"
GOLDEN_OUTPUT_SHA = "23fa0420221c7a56f44dc3d6c4bbb49b75737d05b0ec199bd05ae02fa4e78101"

DATA = os.path.join(_HERE, "data", "liml_failed")
GOLDEN = os.path.join(DATA, "golden_failed.liml")
GOLDEN_JSON = os.path.join(DATA, "golden_failed_expected.json")
IRONPYTHON = sys.platform == "cli"
FAILED = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def lf_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def hub_core():
    """common/liml_failed.py of AdvancedToolsHub next to this repository (a
    folder above it holds that repository), or None. Elsewhere there is
    nothing to compare with: the bridge itself never needs it."""
    env = os.environ.get("ADVANCEDTOOLSHUB_DIR")
    if env:
        path = os.path.join(env, "common", "liml_failed.py")
        return path if os.path.isfile(path) else None
    here = os.path.abspath(_HERE)
    while True:
        up = os.path.dirname(here)
        if up == here:
            return None
        here = up
        path = os.path.join(here, "AdvancedToolsHub", "common",
                            "liml_failed.py")
        if os.path.isfile(path):
            return path


def test_pin():
    print("-- pin of the copy")
    check("VERSION is {0}".format(PIN_VERSION), L.VERSION == PIN_VERSION,
          L.VERSION)
    check("contract is failed/1", L.CONTRACT_FAILED == "failed/1")
    sha = lf_sha(read(os.path.join(_SCRIPTS, "liml_failed.py")))
    check("LF-sha256 of Scripts/liml_failed.py is pinned",
          sha == PIN_SHA256, sha)


def test_source():
    print("-- copy against its source")
    path = hub_core()
    if path is None:
        print("     source not present, copy not compared")
        return
    theirs = read(path).replace(b"\r\n", b"\n")
    ours = read(os.path.join(_SCRIPTS, "liml_failed.py")).replace(
        b"\r\n", b"\n")
    check("liml_failed.py is an unchanged copy", theirs == ours,
          "Scripts/liml_failed.py: copy differs from AdvancedToolsHub's "
          "common/liml_failed.py; copy it over and update the pin")


def test_golden(tmp):
    print("-- golden fixture")
    with io.open(GOLDEN_JSON, "r", encoding="utf-8") as f:
        exp = json.load(f)
    check("fixture contract", exp["contract"] == L.CONTRACT_FAILED)
    check("fixture input sha", lf_sha(read(GOLDEN)) == GOLDEN_INPUT_SHA)
    want = dict((int(k), v) for k, v in exp["failed"].items())
    out = os.path.join(tmp, "golden_out.liml")
    rep = L.process(GOLDEN, out)
    check("provider {0}".format(exp["provider"]),
          rep["provider"] == exp["provider"], rep["provider"])
    check("failed steps {0}".format(sorted(want.items())),
          rep["failed"] == want, rep["failed"])
    # marker of core 1.0.1: <globalvariable name="failed_hidden">N</...>,
    # the hidden count as text
    check("written with the marker (hidden count)", rep["written"] and
          L.processed_marker(out) == u"{0}".format(len(want)) and
          L.marker_count(L.processed_marker(out)) == len(want),
          L.processed_marker(out))
    check("output sha", lf_sha(read(out)) == GOLDEN_OUTPUT_SHA)
    rep2 = L.scan(GOLDEN, solver="aster")
    check("scan(solver='aster') gives the same steps",
          rep2["failed"] == want and not rep2["written"])
    try:
        L.process(out, os.path.join(tmp, "again.liml"))
        code, info = None, {}
    except L.LimlFailedError as e:
        code, info = e.code, e.info
    check("a processed file is refused", code == "already_processed", code)
    check("... with the hidden count in info",
          info.get("hidden_count") == len(want), info)


def run_in_ironpython():
    """The same test in Mecway's IronPython 2.7.9 (run_ipy.ps1 runs the
    script with __name__ != '__main__': a wrapper imports it)."""
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="liml_failed_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_liml_failed_copy.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_liml_failed_copy as t\n"
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
    tmp = tempfile.mkdtemp(prefix="liml_failed_copy_")
    try:
        test_pin()
        test_source()
        test_golden(tmp)
    finally:
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
