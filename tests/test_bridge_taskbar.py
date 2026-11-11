# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the taskbar ID the convergence window gets so that it sits
# under Mecway's taskbar button (bridge_run_aster.taskbar_id, passed as
# --taskbar-id): the implicit ID of a program in Program Files, nothing for
# other folders. Fake environment, nothing is started.
#
#   python tests/test_bridge_taskbar.py

from __future__ import print_function

import os
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_run_aster as r  # noqa: E402

_FAILED = []
X64 = "{6D809377-6AF0-444B-8957-A3773F02200E}"
X86 = "{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}"


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def main():
    sep = "\\"
    pf = sep.join(["C:", "Program Files"])
    pf86 = sep.join(["C:", "Program Files (x86)"])
    env = {"ProgramFiles": pf, "ProgramW6432": pf, "ProgramFiles(x86)": pf86}
    exe = sep.join([pf, "Mecway", "mecway.exe"])
    if os.sep == sep:
        check(r.taskbar_id(exe, env) == X64 + sep + "Mecway" + sep +
              "mecway.exe", "Program Files: {6D809377-...}\\Mecway\\"
              "mecway.exe (verified with Mecway 35)")
        check(r.taskbar_id(sep.join([pf86, "Mecway", "mecway.exe"]), env)
              == "" and r.taskbar_id(sep.join([pf86, "Mecway",
                                               "mecway.exe"]),
                                     {"ProgramW6432": pf,
                                      "ProgramFiles": pf86}) == "",
              "Program Files (x86): no ID (NOT verified), also in a 32-bit "
              "process where ProgramFiles is the x86 folder")
        check(X86 not in r.taskbar_id(exe, env), "x86 folder ID never used")
        check(r.taskbar_id(exe, {"ProgramW6432": pf,
                                 "ProgramFiles": pf86}) ==
              X64 + sep + "Mecway" + sep + "mecway.exe",
              "a 32-bit process (ProgramFiles = x86) still finds x64 via "
              "ProgramW6432")
        check(r.taskbar_id(sep.join(["D:", "Tools", "Mecway", "mecway.exe"]),
                           env) == "",
              "another folder: no ID (NOT verified, own button stays)")
    check(r.taskbar_id("", env) == "" and r.taskbar_id(None, env) == "",
          "no path: no ID")
    check(r.taskbar_id(sep.join([pf, "Mecway", "readme.txt"]), env) == "",
          "not an .exe: no ID")
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
