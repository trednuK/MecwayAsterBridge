# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of waiting for Code-Aster (bridge_run_aster: launch command
# with aster_launch.bat and the end marker, AsterJob end detection, Stop,
# window closed, status texts). Windows only (cmd.exe, taskkill).
#
#   python tests/test_bridge_wait.py
#
# A fake Code-Aster installation in a temporary folder whose path contains
# spaces, '&', brackets and a non-ASCII character: bin\run_aster.bat
# simulates run_aster (a run_aster_* folder with fort.6 and a copy of the
# .export, after a while the .mess with DIAGNOSTIC JOB, then the exit code),
# tools\tee.exe is copied from the real installation if there is one. The
# cmd windows are started without a console window (CREATE_NO_WINDOW).
# Every process this test starts is ended by the test itself.

from __future__ import print_function

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
sys.path.insert(0, _HERE)
import bridge_utils  # noqa: E402
import bridge_run_aster as ra  # noqa: E402
import bridge_convergence as bc  # noqa: E402
import test_bridge_convergence as samples  # noqa: E402

bridge_utils.CONFIG_BRIDGE["language"] = "en"
CREATE_NO_WINDOW = 0x08000000
FAILED = []

FAKE_RUN_ASTER = u"""@echo off
rem Fake run_aster.bat for tests/test_bridge_wait.py
setlocal EnableDelayedExpansion
echo FAKE run_aster start
if exist "%~1" (echo EXPORT FOUND) else (echo EXPORT MISSING)
set "RUNDIR=%FAKE_TMP%\\run_aster_fake%RANDOM%"
mkdir "%RUNDIR%"
> "%RUNDIR%\\1.export" echo F mess !FAKE_MESS! R 6
copy /y "%FAKE_FORT6%" "%RUNDIR%\\fort.6" > nul
ping -n %FAKE_SECONDS% 127.0.0.1 > nul
copy /y "%RUNDIR%\\fort.6" "%FAKE_MESS%" > nul
>> "%FAKE_MESS%" echo --- DIAGNOSTIC JOB : OK
rmdir /s /q "%RUNDIR%"
echo FAKE run_aster end
exit /b %FAKE_RC%
"""


def check(cond, text):
    if cond:
        print(u"OK   " + text)
    else:
        print(u"FAIL " + text)
        FAILED.append(text)


def _pids_alive(pids):
    """Subset of pids that still run (tasklist)."""
    alive = []
    for pid in pids:
        out = subprocess.check_output(
            ["tasklist", "/FI", "PID eq {0}".format(pid), "/NH", "/FO",
             "CSV"], creationflags=CREATE_NO_WINDOW).decode("mbcs",
                                                             "replace")
        if '"{0}"'.format(pid) in out:
            alive.append(pid)
    return alive


def _descendants(pid):
    """All descendants of pid (PowerShell / CIM: ParentProcessId)."""
    script = ("$all = Get-CimInstance Win32_Process | Select-Object "
              "ProcessId,ParentProcessId; $todo = @({0}); $out = @(); "
              "while ($todo.Count) {{ $p = $todo[0]; $todo = @($todo | "
              "Select-Object -Skip 1); foreach ($c in $all) {{ if "
              "($c.ParentProcessId -eq $p) {{ $out += $c.ProcessId; "
              "$todo += $c.ProcessId }} }} }}; $out -join ','").format(pid)
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", script],
        creationflags=CREATE_NO_WINDOW).decode("mbcs", "replace").strip()
    return [int(x) for x in out.split(",") if x.strip()]


class Fake(object):
    """Fake installation, work folder and environment."""

    def __init__(self, base):
        self.root = os.path.join(base, u"Code Aster & (x) \u00e9")
        os.makedirs(os.path.join(self.root, "bin"))
        os.makedirs(os.path.join(self.root, "tools"))
        os.makedirs(os.path.join(self.root, "share", "aster"))
        self.tmp = os.path.join(base, u"tmp dir")
        os.makedirs(self.tmp)
        with io.open(os.path.join(self.root, "share", "aster",
                                  "config.json"), "w",
                     encoding="utf-8") as f:
            f.write(json.dumps({"tmpdir": self.tmp}, ensure_ascii=False))
        self.exe = os.path.join(self.root, "bin", "run_aster.bat")
        with io.open(self.exe, "w", encoding="ascii", newline="\r\n") as f:
            f.write(FAKE_RUN_ASTER)
        real_tee = os.path.join(os.path.dirname(os.path.dirname(
            ra.exe_aster_path())), "tools", "tee.exe")
        self.tee = os.path.isfile(real_tee)
        if self.tee:
            shutil.copy(real_tee, os.path.join(self.root, "tools"))
        self.work = os.path.join(base, u"work dir & (1)")
        os.makedirs(self.work)
        self.export = os.path.join(self.work, ra.run_name(".export"))
        with io.open(self.export, "w", encoding="utf-8") as f:
            f.write(u"P time_limit 600\nF mess {0} R 6\n".format(
                os.path.join(self.work, ra.run_name(".mess"))))
        self.fort6 = os.path.join(base, "sample_fort6.txt")
        with io.open(self.fort6, "w", encoding="utf-8") as f:
            f.write(samples.MESS_CONTACT.split(u"--- DIAGNOSTIC")[0])
        bridge_utils.CONFIG_BRIDGE["exe_aster"] = self.exe

    def clean_run(self):
        for suffix in (".mess", ra.CONSOLE_SUFFIX, ra.DONE_SUFFIX):
            p = os.path.join(self.work, ra.run_name(suffix))
            for _i in range(40):     # tee of the previous run may still
                try:                 # hold the console file for a moment
                    if os.path.exists(p):
                        os.remove(p)
                    break
                except OSError:
                    time.sleep(0.25)

    def start(self, seconds, rc):
        """Start the launch command as run_AsterSolver does (without a
        console window). Returns (process, marker, captured, marked)."""
        self.clean_run()
        marker = os.path.join(self.work, ra.run_name(ra.DONE_SUFFIX))
        console = os.path.join(self.work, ra.run_name(ra.CONSOLE_SUFFIX))
        cmd, captured, marked = ra._launch_command(self.export, console,
                                                   marker)
        env = dict(os.environ)
        env.update({"FAKE_TMP": self.tmp,
                    "FAKE_MESS": os.path.join(self.work,
                                              ra.run_name(".mess")),
                    "FAKE_FORT6": self.fort6,
                    "FAKE_SECONDS": str(seconds), "FAKE_RC": str(rc)})
        proc = subprocess.Popen(cmd, cwd=self.work, env=env,
                                creationflags=CREATE_NO_WINDOW)
        return proc, marker, captured, marked


def wait_job(job, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if job.poll():
            return True
        time.sleep(0.25)
    return False


def test_launch_and_finish(fake):
    start = time.time()
    proc, marker, captured, marked = fake.start(3, 3)
    check(marked, u"launch command uses aster_launch.bat (end marker)")
    check(captured == fake.tee, u"tee captured if tee.exe exists")
    job = ra.AsterJob(proc, fake.work, fake.export, start, marker)
    check(job.time_limit == 600.0, u"time limit from the .export")
    seen_live = False
    deadline = time.time() + 30
    while time.time() < deadline and not job.poll():
        st = job.status()
        if u"reached t =" in st["detail"]:
            seen_live = True
        time.sleep(0.25)
    check(job.state == "finished", u"end detected: {0}".format(job.state))
    check(job.exit_code == 3, u"exit code from the marker: {0}".format(
        job.exit_code))
    check(seen_live, u"live status from fort.6 (step/time/iteration): "
          u"{0}".format(job.status()["detail"]))
    st = job.status()
    check(u"Messages so far" in st["messages"], u"messages counted: " +
          st["messages"])
    if captured:
        console = os.path.join(fake.work, ra.run_name(ra.CONSOLE_SUFFIX))
        time.sleep(0.5)
        text = io.open(console, encoding="utf-8", errors="replace").read()
        check(u"EXPORT FOUND" in text and u"FAKE run_aster end" in text,
              u"export path with spaces/&/() arrived; console captured")
    else:
        print(u"(no tee.exe: console capture not tested)")
    check(proc.poll() is None, u"cmd /k window stays open after the run")
    ra.kill_process_tree(proc.pid)
    proc.wait()


def test_stop(fake):
    start = time.time()
    proc, marker, _c, _m = fake.start(120, 0)
    job = ra.AsterJob(proc, fake.work, fake.export, start, marker)
    # A sleeper outside the tree must survive the stop.
    other = subprocess.Popen(["ping", "-n", "30", "127.0.0.1"],
                             stdout=subprocess.PIPE,
                             creationflags=CREATE_NO_WINDOW)
    deadline = time.time() + 30
    while time.time() < deadline and job._fort6 is None:
        job.poll()
        time.sleep(0.25)
    check(job._fort6 is not None, u"live fort.6 found before the stop")
    run_dir = os.path.dirname(job._fort6) if job._fort6 else None
    tree = _descendants(proc.pid)
    check(len(tree) >= 2, u"process tree of the run: {0}".format(tree))
    job.stop()
    check(job.state == "stopped", u"state after Stop: " + job.state)
    check(proc.poll() is not None, u"cmd process ended")
    time.sleep(0.5)
    check(not _pids_alive(tree), u"whole tree ended (left: {0})".format(
        _pids_alive(tree)))
    check(other.poll() is None, u"process outside the tree still runs")
    other.kill()
    other.wait()
    mess = os.path.join(fake.work, ra.run_name(".mess"))
    check(os.path.exists(mess), u".mess written from the live fort.6")
    data = bc.parse_file(mess)
    check(data.stopped == "user" and data.steps,
          u".mess: BRIDGE_GESTOPT user and the steps so far")
    check(run_dir is not None and not os.path.exists(run_dir),
          u"temporary run_aster folder removed")
    errors = ra.aster_mess_errors(fake.work, start)
    check(not any(u"not closed" in e for e in errors),
          u"no 'not closed' error for a stopped run: {0}".format(errors))
    check(not os.path.exists(marker), u"no end marker after a stop")


def test_window_closed(fake):
    start = time.time()
    proc, marker, _c, _m = fake.start(120, 0)
    job = ra.AsterJob(proc, fake.work, fake.export, start, marker)
    deadline = time.time() + 30
    while time.time() < deadline and job._fort6 is None:
        job.poll()
        time.sleep(0.25)
    tree = _descendants(proc.pid)
    # Closing the window ends the cmd process; here only the cmd itself.
    subprocess.call(["taskkill", "/F", "/PID", str(proc.pid)],
                    stdout=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
    proc.wait()
    for pid in _pids_alive(tree):   # the rest of the tree (ours)
        subprocess.call(["taskkill", "/F", "/PID", str(pid)],
                        stdout=subprocess.PIPE,
                        creationflags=CREATE_NO_WINDOW)
    time.sleep(0.5)
    check(job.poll() and job.state == "closed",
          u"window closed detected: " + job.state)
    data = bc.parse_file(os.path.join(fake.work, ra.run_name(".mess")))
    check(data.stopped == "window", u".mess: BRIDGE_GESTOPT window")
    check(u"Code-Aster window was closed" in job.status()["headline"],
          u"headline: " + job.status()["headline"])


def test_mess_fallback(fake):
    """Without an end marker (aster_launch.bat missing): the end from
    DIAGNOSTIC JOB in the .mess."""
    start = time.time()
    proc, marker, _c, _m = fake.start(2, 0)
    job = ra.AsterJob(proc, fake.work, fake.export, start, None)
    check(wait_job(job, 30) and job.state == "finished" and
          job.exit_code is None, u"end from the .mess without a marker")
    ra.kill_process_tree(proc.pid)
    proc.wait()


def test_helpers(base):
    p = os.path.join(base, "marker.txt")
    check(ra.read_marker(p) is None, u"read_marker: missing -> None")
    with open(p, "w") as f:
        f.write("0 \n")
    check(ra.read_marker(p) == 0, u"read_marker: '0 ' -> 0")
    with open(p, "w") as f:
        f.write("ECHO is off.\n")
    check(ra.read_marker(p) == -1, u"read_marker: unreadable -> -1")
    check(ra._duration(3725) == "1:02:05" and ra._duration(65) == "1:05",
          u"_duration")
    cmd, _cap, marked = ra._launch_command(u"C:\\a b\\x.export", None,
                                           u"C:\\a b\\x_done.txt")
    check(marked and cmd.startswith(u'cmd /k ""') and
          cmd.endswith(u'"C:\\a b\\x_done.txt""'),
          u"command without tee: " + cmd)
    cmd, _cap, marked = ra._launch_command(u"C:\\a b\\x.export", None)
    check(not marked and u"aster_launch.bat" not in cmd,
          u"without a marker the launcher is called directly")


def main():
    if os.name != "nt":
        print(u"Windows only; skipped.")
        return 0
    exe_saved = bridge_utils.CONFIG_BRIDGE["exe_aster"]
    base = tempfile.mkdtemp(prefix="bridge_wait_")
    try:
        fake = Fake(base)
        test_helpers(base)
        test_launch_and_finish(fake)
        test_mess_fallback(fake)
        test_stop(fake)
        test_window_closed(fake)
    finally:
        bridge_utils.CONFIG_BRIDGE["exe_aster"] = exe_saved
        shutil.rmtree(base, ignore_errors=True)
    if FAILED:
        print(u"{0} test(s) failed.".format(len(FAILED)))
        return 1
    print(u"OK: waiting for Code-Aster (launch command, end marker, "
          u"Stop, window closed, .mess fallback)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
