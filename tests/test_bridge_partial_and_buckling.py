# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (CPython) van twee vervolgmeldingen op GitHub-issues:
#   #5: resultaten na een andere fout dan MECANONLINE in de stappenlus
#       (bridge_failure.PARTIAL_EXCEPT, de melding in bridge_run_aster);
#   #6: lineaire knik met trusses: ERROR voor Code-Aster
#       (bridge_to_aster._check_buckling_trusses).
#
#   python tests/test_bridge_partial_and_buckling.py

from __future__ import print_function

import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils as u  # noqa: E402
import bridge_failure  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402
from bridge_to_aster import generate_AsterSolver_files  # noqa: E402
from bridge_run_aster import aster_mess_errors  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []
_TRUSS_MODEL = os.path.join(_HERE, "..", "TestFiles", "Verificatie",
                            "modellen", "MO-08.liml")


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


class _Err(Exception):
    def __init__(self, idm):
        Exception.__init__(self, idm)
        self.id_message = idm


class _Res(object):
    def __init__(self, inst):
        self.inst = inst

    def getAccessParameters(self):
        return {"INST": self.inst}


def _clause(err, res):
    """Voert try/raise + PARTIAL_EXCEPT uit zoals in study.comm."""
    code = ("try:\n    raise err\n" + bridge_failure.PARTIAL_EXCEPT)
    out = []
    ns = {"err": err, "print": lambda *a: out.append(a)}
    if res is not None:
        ns["res"] = res
    try:
        exec(code, ns)
    except (_Err, ValueError):
        return "raised", out
    return "continued", out


def test_partial_except():
    st, out = _clause(_Err("DVP_2"), _Res([0.0, 0.05, 0.1]))
    check(st == "continued" and ("BRIDGE_FOUT_ID", "DVP_2") in out and
          ("BRIDGE_ONVOLLEDIG", 0.1) in out,
          "DVP_2 after converged steps: continue with t = 0.1")
    st, _ = _clause(_Err("DVP_2"), _Res([0.0]))
    check(st == "raised", "DVP_2 without a step beyond 0: raise")
    st, _ = _clause(_Err("CALCUL_37"), None)
    check(st == "raised", "error without 'res': raise")
    st, out = _clause(_Err("MECANONLINE9_7"), _Res([0.0]))
    check(st == "continued" and ("BRIDGE_ONVOLLEDIG", 0.0) in out,
          "MECANONLINE: continue as before")
    st, _ = _clause(ValueError("python"), _Res([0.0, 1.0]))
    check(st != "continued", "Python error (no id_message): raise")


_MESS = (u"Instant de calcul:  5.500000000000e-01\n"
         u" ║ <EXCEPTION> <DVP_2>                ║\n"
         u" ║ Erreur numérique (floating point exception). ║\n"
         u"\n"
         u"BRIDGE_FOUT_ID DVP_2\n"
         u"BRIDGE_ONVOLLEDIG 0.5\n"
         u"<FIN>\n"
         u"--- DIAGNOSTIC JOB : OK\n")


def test_mess_message(tmp):
    work = tempfile.mkdtemp(dir=tmp)
    u.CONFIG_BRIDGE["work_dir"] = work
    with io.open(os.path.join(work, u.run_name(".mess")), "w",
                 encoding="utf-8") as f:
        f.write(_MESS)
    msgs = aster_mess_errors(work)
    dvp = [m for m in msgs if "<DVP_2>" in m]
    check(len(dvp) == 1 and "too distorted" in dvp[0] and
          "Last time with results: 0.5 s." in dvp[0],
          "DVP_2 message: hint and last time with results")


def test_buckling_truss(tmp):
    work = tempfile.mkdtemp(dir=tmp)
    liml = os.path.join(work, "model.liml")
    shutil.copy(_TRUSS_MODEL, liml)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = "buckling_3d"
    md = extract_aster_data_from_liml(liml)
    mail = os.path.join(work, "m.mail")
    ok = (md is not None and write_mesh(mail, md) and
          generate_AsterSolver_files(work, md, mail, "test.resu"))
    log = io.open(os.path.join(work, "bridge_log.txt"),
                  encoding="utf-8").read()
    check(not ok and "ERROR: Linear buckling is not possible with trusses"
          in log, "buckling with trusses: ERROR before Code-Aster")
    u.CONFIG_BRIDGE["active_analysis"] = "modal_3d"
    md = extract_aster_data_from_liml(liml)
    ok = (md is not None and write_mesh(mail, md) and
          generate_AsterSolver_files(work, md, mail, "test.resu"))
    check(bool(ok), "modal with the same trusses: files generated")


def main():
    saved = dict(u.CONFIG_BRIDGE)
    tmp = tempfile.mkdtemp(prefix="bridge_partial_buckling_")
    try:
        test_partial_except()
        test_mess_message(tmp)
        test_buckling_truss(tmp)
    finally:
        u.CONFIG_BRIDGE.clear()
        u.CONFIG_BRIDGE.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
