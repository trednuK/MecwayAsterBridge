# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (CPython) of the time limit of a Code-Aster run:
#   - the time guard of the step loops (bridge_failure.time_guard_check, in
#     the failure loop and the welding birth loop): only in those loops, the
#     clock before DEBUT, the .comm is valid Python;
#   - the extra time after a TimeLimitError (bridge_failure._time_extra in
#     PARTIAL_EXCEPT and GUARD_EXCEPT);
#   - the messages (bridge_run_aster.aster_mess_errors, bridge_convergence).
#
#   python tests/test_bridge_time_guard.py

from __future__ import print_function

import ast
import io
import os
import shutil
import sys
import tempfile
import types

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_REPO = os.path.join(_HERE, "..")
sys.path.insert(0, os.path.join(_REPO, "Scripts"))
import bridge_utils as u  # noqa: E402
import bridge_failure  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402
from bridge_to_aster import generate_AsterSolver_files  # noqa: E402
from bridge_run_aster import aster_mess_errors  # noqa: E402
from bridge_convergence import ConvergenceParser  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _parse(text):
    """The .comm runs in Code-Aster's Python 3; IronPython's ast cannot
    parse every expression of it, so only check it in CPython 3."""
    if sys.version_info[0] >= 3:
        ast.parse(text)


def _comm(tmp, liml, analysis, **settings):
    """Generated .comm text of liml for analysis (settings in memory)."""
    work = tempfile.mkdtemp(dir=tmp)
    model = os.path.join(work, "model.liml")
    shutil.copy(liml, model)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = analysis
    saved = dict(u.CONFIG_BRIDGE["analyses"][analysis])
    u.CONFIG_BRIDGE["analyses"][analysis].update(settings)
    try:
        md = extract_aster_data_from_liml(model)
        mail = os.path.join(work, "model_mesh.mail")
        assert write_mesh(mail, md)
        assert generate_AsterSolver_files(work, md, mail, "test.resu")
    finally:
        u.CONFIG_BRIDGE["analyses"][analysis] = saved
    with io.open(os.path.join(work, u.run_name(".comm")),
                 encoding="utf-8") as f:
        return f.read()


def _post_time(text):
    """bridge_failure.POST_TIME directly after the (last) t_res line."""
    i = text.rfind("t_res = res.getAccessParameters()['INST'][-1]\n")
    after = text[i:].split("\n", 1)[1] if i >= 0 else ""
    return after.startswith(bridge_failure.POST_TIME) and \
        "print(" not in bridge_failure.POST_TIME


def test_comm(tmp):
    bar = os.path.join(_REPO, "TestFiles", "BezwijkenTrekstaaf.liml")
    text = _comm(tmp, bar, "nonlin_static_3d", time_limit=1000)
    debut = text.find("DEBUT(")
    check(0 <= text.find("_bt_t0 = _bt_time.time()") < debut,
          "failure loop: clock before DEBUT")
    check("_bt_limit = 900.0\n" in text and "_bt_post = 100.0" in text,
          "failure loop: limit time_limit x 0.9, post max(60, 10 %)")
    loop = text[text.find("    for _bz_i in range"):]
    check(loop.find("print('BRIDGE_FOUT_ID', 'BRIDGE_TIJD')") <
          loop.find("res = STAT_NON_LINE(") and "    break\n" in loop and
          "_bz_seg = _bt_time.time() - _bz_t1" in loop,
          "failure loop: guard before the solve, time of the solve")
    check("type(err).__name__ == 'TimeLimitError'" in text,
          "failure loop: extra time after a TimeLimitError")
    check(_post_time(text), "failure loop: silent extra time after t_res")
    _parse(text)
    check(True, "failure loop: .comm is valid Python")

    text = _comm(tmp, bar, "nonlin_static_3d", element_failure=False)
    check("_bt_" not in text and
          "type(err).__name__ == 'TimeLimitError'" in text and
          _post_time(text),
          "single STAT_NON_LINE: no guard, extra time in the except and "
          "after t_res")
    _parse(text)

    plate = os.path.join(_REPO, "TestFiles", "Verificatie", "modellen",
                         "AD-11.liml")
    if os.path.isfile(plate):
        text = _comm(tmp, plate, "nonlin_static_3d", adapt_homard=True,
                     adapt_homard_target=0.4, adapt_homard_max_loops=10)
        loop = text[text.find("for _adapt_k in"):
                    text.find("_adapt_run.summary()")]
        check(text.count(bridge_failure.POST_TIME) == 1 and
              loop.rstrip("\n").endswith(bridge_failure.POST_TIME.rstrip(
                  "\n")) and
              "environ.get('BRIDGE_TIJD_STOP')" in loop,
              "adaptive loop: extra time once after the loop, time stop "
              "ends the loop")
        _parse(text)

    lin = os.path.join(_REPO, "TestFiles", "Voorbeelden", "Voorbeeld_A.liml")
    text = _comm(tmp, lin, "lin_static_3d")
    check("_bt_" not in text and "TimeLimitError" not in text and
          "BRIDGE_TPMAX0" not in text,
          "linear static: unchanged (no guard, no extra time)")

    weld = os.path.join(_REPO, "TestFiles", "Verificatie", "modellen",
                        "WE-12.liml")
    if os.path.isfile(weld):
        text = _comm(tmp, weld, "ther_3d", time_limit=600)
        debut = text.find("DEBUT(")
        loop = text[text.find("    for _gm_k in"):]
        check(0 <= text.find("_bt_t0 = _bt_time.time()") < debut and
              "_bt_limit = 540.0\n" in text and
              loop.find("'BRIDGE_TIJD'") < loop.find("res = STAT_NON_LINE(")
              and _post_time(text),
              "welding birth loop: clock, guard, extra time after t_res")
        _parse(text)


class _Clock(object):
    def __init__(self, now):
        self.now = now

    def time(self):
        return self.now


class _Res(object):
    def __init__(self, inst):
        self.inst = inst

    def getAccessParameters(self):
        return {"INST": self.inst}


def test_guard_runs():
    """The guard lines in a small loop with a fake clock (and without
    code_aster: the extra time then only prints a message)."""
    code = ("for _i in range(1, 4):\n"
            "    if _i > 1:\n" + bridge_failure.time_guard_check(8, "_seg") +
            "    done.append(_i)\n")
    for now, expect in ((10.0, [1, 2, 3]), (860.0, [1])):
        out, done = [], []
        ns = {"_bt_time": _Clock(now), "_bt_t0": 0.0, "_bt_limit": 900.0,
              "_bt_post": 50.0, "_seg": 2.0, "res": _Res([0.0, 0.5]),
              "done": done, "print": lambda *a: out.append(a)}
        exec(code, ns)
        stopped = ("BRIDGE_FOUT_ID", "BRIDGE_TIJD") in out
        check(done == expect and stopped == (now > 847.0) and
              (not stopped or ("BRIDGE_ONVOLLEDIG", 0.5) in out),
              "guard at {0} s: steps {1}, stop {2}".format(now, done,
                                                          stopped))
    check("{" not in bridge_failure.time_guard_check(4, "_x") and
          "{" not in bridge_failure.time_guard_setup(60) and
          "{" not in bridge_failure.PARTIAL_EXCEPT and
          "{" not in bridge_failure.GUARD_EXCEPT,
          "no braces in the template parts")


class TimeLimitError(Exception):
    def __init__(self, idm):
        Exception.__init__(self, idm)
        self.id_message = idm


class _Err(Exception):
    def __init__(self, idm):
        Exception.__init__(self, idm)
        self.id_message = idm


class _Params(object):
    options = {"tpmax": 36.0}

    def get_option(self, name):
        return self.options[name]

    def set_option(self, name, value):
        self.options[name] = value


def _fake_code_aster(present):
    """code_aster.Utilities.ExecutionParameter in sys.modules (or not)."""
    for name in ("code_aster", "code_aster.Utilities"):
        sys.modules.pop(name, None)
    if present:
        pkg = types.ModuleType("code_aster")
        sub = types.ModuleType("code_aster.Utilities")
        sub.ExecutionParameter = _Params
        pkg.Utilities = sub
        sys.modules["code_aster"] = pkg
        sys.modules["code_aster.Utilities"] = sub


def _run(clause, err, inst):
    code = "try:\n    raise err\n" + clause
    out = []
    ns = {"err": err, "res": _Res(inst), "_gs_t": None,
          "print": lambda *a: out.append(a)}
    try:
        exec(code, ns)
    except Exception:
        return "raised", out, ns
    return "continued", out, ns


def _fresh(tpmax):
    """A new job: original tpmax not yet stored."""
    os.environ.pop("BRIDGE_TPMAX0", None)
    os.environ.pop("BRIDGE_TIJD_STOP", None)
    _Params.options["tpmax"] = tpmax


def test_time_extra():
    _fake_code_aster(True)
    try:
        _fresh(36.0)
        exec(bridge_failure.POST_TIME, {})
        check(_Params.options["tpmax"] == 636.0 and
              "BRIDGE_TIJD_STOP" not in os.environ,
              "after the solve: silent extra time, no time stop")
        _fresh(36.0)
        st, out, _ns = _run(bridge_failure.PARTIAL_EXCEPT,
                            TimeLimitError("MECANONLINE9_1"), [0.0, 0.3])
        check(st == "continued" and _Params.options["tpmax"] == 636.0 and
              ("BRIDGE_TIJD_EXTRA 600.0",) in out and
              ("BRIDGE_ONVOLLEDIG", 0.3) in out and
              os.environ.get("BRIDGE_TIJD_STOP") == "1",
              "TimeLimitError: tpmax + max(600, tpmax), partial, time stop: "
              "{0}".format(out))
        st, out, _ns = _run(bridge_failure.PARTIAL_EXCEPT,
                            TimeLimitError("MECANONLINE9_1"), [0.0, 0.3])
        check(st == "continued" and _Params.options["tpmax"] == 636.0 and
              not [a for a in out if "BRIDGE_TIJD_EXTRA" in a[0]],
              "second stop in the same job: no more extra time")
        _fresh(1620.0)
        st, out, _ns = _run(bridge_failure.PARTIAL_EXCEPT,
                            TimeLimitError("SUPERVIS_63"), [0.0, 0.3])
        check(st == "continued" and _Params.options["tpmax"] == 3240.0,
              "SUPERVIS_63 in the loop: tpmax doubled")
        _fresh(36.0)
        st, out, _ns = _run(bridge_failure.PARTIAL_EXCEPT,
                            _Err("MECANONLINE9_7"), [0.0, 0.3])
        check(st == "continued" and _Params.options["tpmax"] == 36.0 and
              not [a for a in out if "BRIDGE_TIJD_EXTRA" in a[0]],
              "other error: no extra time")
        st, out, ns = _run(bridge_failure.GUARD_EXCEPT,
                           TimeLimitError("MECANONLINE9_1"), [0.0, 0.3])
        check(st == "continued" and ns["_gs_t"] is None and
              ("BRIDGE_ONVOLLEDIG", 0.3) in out and
              _Params.options["tpmax"] == 636.0,
              "step guard: a time limit is no guard end, partial")
        st, out, ns = _run(bridge_failure.GUARD_EXCEPT,
                           _Err("MECANONLINE9_50"), [0.0, 0.3])
        check(st == "continued" and ns["_gs_t"] == 0.3,
              "step guard: MECANONLINE9_50 still continues")
        # the time guard gives the same extra time before its break
        _fresh(900.0)
        out = []
        ns = {"_bt_time": _Clock(860.0), "_bt_t0": 0.0, "_bt_limit": 900.0,
              "_bt_post": 50.0, "_seg": 2.0, "res": _Res([0.0, 0.5]),
              "print": lambda *a: out.append(a)}
        exec("for _i in range(2, 4):\n" +
             bridge_failure.time_guard_check(4, "_seg"), ns)
        check(_Params.options["tpmax"] == 1800.0 and
              ("BRIDGE_TIJD_EXTRA 900.0",) in out and
              out.index(("BRIDGE_TIJD_EXTRA 900.0",)) <
              out.index(("BRIDGE_FOUT_ID", "BRIDGE_TIJD")),
              "time guard: extra time before the stop: {0}".format(out))
    finally:
        _fake_code_aster(False)
        os.environ.pop("BRIDGE_TPMAX0", None)
        os.environ.pop("BRIDGE_TIJD_STOP", None)
    st, out, _ns = _run(bridge_failure.PARTIAL_EXCEPT,
                        TimeLimitError("MECANONLINE9_1"), [0.0, 0.3])
    check(st == "continued" and
          [a for a in out if a[0] == "BRIDGE_TIJD_EXTRA_FOUT"] and
          ("BRIDGE_ONVOLLEDIG", 0.3) in out,
          "without ExecutionParameter: message, still partial")
    os.environ.pop("BRIDGE_TIJD_STOP", None)


_END = u"<FIN>\n--- DIAGNOSTIC JOB : OK\n"


def _mess(tmp, text, export=True):
    work = tempfile.mkdtemp(dir=tmp)
    u.CONFIG_BRIDGE["work_dir"] = work
    with io.open(os.path.join(work, u.run_name(".mess")), "w",
                 encoding="utf-8") as f:
        f.write(text)
    if export:
        with io.open(os.path.join(work, u.run_name(".export")), "w",
                     encoding="utf-8") as f:
            f.write(u"P actions make_etude\nP time_limit 1800\n")
    return aster_mess_errors(work)


def test_messages(tmp):
    msgs = _mess(tmp, u"BRIDGE_FOUT_ID BRIDGE_TIJD\n"
                      u"BRIDGE_ONVOLLEDIG 0.55\n" + _END)
    check(len(msgs) == 1 and "t = 0.55 s" in msgs[0] and "= 1800 s" in
          msgs[0] and "Raise 'Time limit run_aster'" in msgs[0],
          "time guard: one error with t and limit: {0}".format(msgs))
    msgs = _mess(tmp, u" ║ <TimeLimitError> <MECANONLINE9_1>   ║\n"
                      u"BRIDGE_TIJD_EXTRA 1620.0\n"
                      u"BRIDGE_FOUT_ID MECANONLINE9_1\n"
                      u"BRIDGE_ONVOLLEDIG 0.5535\n" + _END)
    check(len(msgs) == 1 and "extra time for the post-processing" in
          msgs[0] and "Last time with results: 0.5535 s." in msgs[0],
          "MECANONLINE9_1: hint and last time")
    msgs = _mess(tmp, u" ║ <TimeLimitError> <SUPERVIS_63>   ║\n" + _END)
    check(len(msgs) == 1 and "skips every next command" in msgs[0],
          "SUPERVIS_63 without extra time: results lost")
    msgs = _mess(tmp, u" ║ <TimeLimitError> <SUPERVIS_63>   ║\n"
                      u"BRIDGE_TIJD_EXTRA 36.0\n"
                      u"BRIDGE_FOUT_ID SUPERVIS_63\n"
                      u"BRIDGE_ONVOLLEDIG 0.4\n" + _END)
    check(len(msgs) == 1 and "extra time" in msgs[0] and
          "Last time with results: 0.4 s." in msgs[0],
          "SUPERVIS_63 caught in the loop: loaded")
    msgs = _mess(tmp, u" ║ <TimeLimitError> <MECANONLINE9_1>   ║\n"
                      u"BRIDGE_TIJD_EXTRA 1620.0\n"
                      u"BRIDGE_FOUT_ID MECANONLINE9_1\n"
                      u"BRIDGE_ONVOLLEDIG 0.5535\n"
                      u" ║ <TimeLimitError> <SUPERVIS_63>   ║\n" + _END)
    check(len(msgs) == 2 and
          all("skips every next command" in m for m in msgs) and
          not [m for m in msgs if "Last time with results" in m],
          "post-processing out of time after the extra time: lost")
    msgs = _mess(tmp, u" ║ <TimeLimitError> <MECANONLINE9_1>   ║\n"
                      u"BRIDGE_TIJD_EXTRA_FOUT ImportError()\n"
                      u"BRIDGE_FOUT_ID MECANONLINE9_1\n"
                      u"BRIDGE_ONVOLLEDIG 0.5535\n" + _END)
    check(len(msgs) == 1 and "skips every next command" in msgs[0],
          "extension failed: not loaded")
    msgs = _mess(tmp, u"BRIDGE_TIJD_EXTRA 900.0\n"
                      u"BRIDGE_FOUT_ID BRIDGE_TIJD\n"
                      u"BRIDGE_ONVOLLEDIG 0.55\n"
                      u" ║ <TimeLimitError> <SUPERVIS_63>   ║\n" + _END)
    check(len(msgs) == 2 and [m for m in msgs if "ran out of time too" in m],
          "time guard, post-processing out of time: {0}".format(msgs))


def _parsed(text):
    p = ConvergenceParser()
    p.feed(text)
    p.close()
    return [m["text"] for m in p.data.messages
            if m["code"] == u"BRIDGE_ONVOLLEDIG"]


def test_convergence():
    check(_parsed(u"BRIDGE_FOUT_ID BRIDGE_TIJD\nBRIDGE_ONVOLLEDIG 0.5\n") ==
          [u"Stopped by the bridge before the time limit; results up to "
           u"t = 0.5 s."], "convergence: time guard")
    check(_parsed(u"BRIDGE_FOUT_ID MECANONLINE9_1\n"
                  u"BRIDGE_ONVOLLEDIG 0.5\n") ==
          [u"Code-Aster's time limit reached; results up to t = 0.5 s."],
          "convergence: Code-Aster time limit")
    p = ConvergenceParser()
    p.feed(u"BRIDGE_TIJD_EXTRA 600.0\n")
    p.close()
    check(p.data.time_extra, "convergence: extra time seen (status box)")
    check(_parsed(u"BRIDGE_FOUT_ID MECANONLINE9_7\n"
                  u"BRIDGE_ONVOLLEDIG 0.5\n") ==
          [u"Not converged; results up to t = 0.5 s."],
          "convergence: not converged as before")


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    work_dir = u.CONFIG_BRIDGE["work_dir"]
    try:
        test_comm(tmp)
        test_guard_runs()
        test_time_extra()
        test_messages(tmp)
        test_convergence()
    finally:
        u.CONFIG_BRIDGE["work_dir"] = work_dir
        shutil.rmtree(tmp, ignore_errors=True)
    if _FAILED:
        print("\n{0} FAILED".format(len(_FAILED)))
        sys.exit(1)
    print("\nAll OK")
