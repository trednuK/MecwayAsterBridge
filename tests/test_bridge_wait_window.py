# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the wait window (bridge_gui.wait_open / wait_step /
# wait_close), in Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1),
# with the window off the screen (_WAIT_POSITION):
#   - enabled=False and close without open: nothing;
#   - closed within the delay: no window, the thread has ended;
#   - a busy main thread (3 s): the window appears after the delay and
#     keeps refreshing on its own thread; wait_step changes the state;
#   - close (also twice) ends the thread within the join time;
#   - open while one is open closes the first one.
# Under CPython it only starts the IronPython run (or skips without Mecway).
#
#   python tests/test_bridge_wait_window.py

from __future__ import print_function

import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "Scripts"))

IRONPYTHON = sys.platform == "cli"
FAILED = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


def busy(seconds):
    """Keep this thread busy without pumping messages (like _run)."""
    end = time.time() + seconds
    n = 0
    while time.time() < end:
        n += 1
    return n


def tests():
    import bridge_gui as g
    g._WAIT_POSITION = (-4000, -4000)
    g.wait_close()
    check("close without open: nothing", g._WAIT["state"] is None)
    g.wait_open(u"step", enabled=False)
    check("enabled=False: no window", g._WAIT["state"] is None)

    g.wait_open(u"short")
    state, thread = g._WAIT["state"], g._WAIT["thread"]
    busy(0.5)
    g.wait_close()
    check("closed within the delay: never shown", not state["shown"],
          state)
    check("closed within the delay: thread ended", not thread.IsAlive)

    g.wait_open(u"Reading the model")
    state, thread = g._WAIT["state"], g._WAIT["thread"]
    busy(2.6)
    ticks = state["ticks"]
    g.wait_step(u"Writing the mesh (.mail)")
    busy(1.0)
    check("busy main thread: the window was shown (Shown event)", state["shown"], state)
    check("busy main thread: it keeps refreshing on its own thread",
          state["ticks"] > ticks >= 1, (ticks, state["ticks"]))
    check("wait_step: the state holds the new text",
          state["step"] == u"Writing the mesh (.mail)")
    g.wait_open(u"second")             # closes the first one
    check("open while open: the first thread ended", not thread.IsAlive)
    second = g._WAIT["thread"]
    g.wait_close()
    g.wait_close()
    check("close twice: no error, thread ended", not second.IsAlive and
          g._WAIT["state"] is None)


def run_in_ironpython():
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="wait_window_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_wait_window.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_bridge_wait_window as t\n"
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
    if IRONPYTHON:
        import bridge_utils
        tmp = tempfile.mkdtemp(prefix="wait_window_")
        saved = bridge_utils.CONFIG_BRIDGE.get("work_dir", "")
        bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp   # in memory only
        try:
            tests()
        finally:
            bridge_utils.CONFIG_BRIDGE["work_dir"] = saved
            shutil.rmtree(tmp, True)
    else:
        run_in_ironpython()
    if FAILED:
        print("{0} failure(s): {1}".format(len(FAILED), ", ".join(FAILED)))
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
