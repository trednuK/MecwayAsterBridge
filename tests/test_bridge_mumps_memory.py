# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the setting mumps_memory (bridge_utils.mumps_keywords,
# mumps_solveur, mumps_memory_note) and of the report after a run when
# MUMPS went out of core (bridge_run_aster.mumps_memory_report):
#   - auto writes nothing, low_rank ACCELERATION='LR+' with
#     LOW_RANK_SEUIL=1.0e-9 only where allowed, out_of_core
#     GESTION_MEMOIRE='OUT_OF_CORE' everywhere; an unknown value is auto
#     with one WARNING;
#   - in a generated .comm: Static, Nonlinear (implicit; explicit without
#     low rank), Modal (eigen solve without low rank, prestress step with);
#     #ASTER-OPTIE mumps_memory overrides the setting; GCPC gets a WARNING;
#   - the report: a WARNING with the in-core estimate when the last
#     factorization of the static solve ran out of core, none when it ran
#     in core or out_of_core was asked for, no number with low_rank.
# Every analysis and every MUMPS call: TestFiles/Tools/regression_scope.py
# --set mumps_memory=<value> --dump DIR over all verification cases.
# Python 2.7 and 3.
#
#   python tests/test_bridge_mumps_memory.py

from __future__ import print_function

import glob
import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "Scripts"))

import bridge_utils as u                               # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh                     # noqa: E402
from bridge_to_aster import generate_AsterSolver_files  # noqa: E402
import bridge_run_aster                                # noqa: E402

FAILED = []
LR = ", ACCELERATION='LR+', LOW_RANK_SEUIL=1.0e-9"
OOC = ", GESTION_MEMOIRE='OUT_OF_CORE'"


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


def log_text():
    path = os.path.join(u.work_dir_path(), u.log_file_name())
    if not os.path.exists(path):
        return u""
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def test_helpers():
    check("auto: no keywords", u.mumps_keywords({}) == "" and
          u.mumps_keywords({"mumps_memory": "auto"}) == "")
    check("low_rank: LR+ and threshold",
          u.mumps_keywords({"mumps_memory": "low_rank"}) == LR)
    check("low_rank not allowed: nothing",
          u.mumps_keywords({"mumps_memory": "low_rank"}, False) == "")
    check("out_of_core: also where low rank is not allowed",
          u.mumps_keywords({"mumps_memory": "out_of_core"}) == OOC and
          u.mumps_keywords({"mumps_memory": "out_of_core"}, False) == OOC)
    check("case and spaces", u.mumps_memory({"mumps_memory": " Low_Rank "})
          == "low_rank")
    check("unknown value: auto", u.mumps_keywords({"mumps_memory": "lr"}) ==
          "" and u.mumps_memory({"mumps_memory": "lr"}) == "auto")
    check("mumps_solveur: none for auto",
          u.mumps_solveur({"mumps_memory": "auto"}) == "")
    check("mumps_solveur: SOLVEUR line",
          u.mumps_solveur({"mumps_memory": "out_of_core"}) ==
          "    SOLVEUR=_F(METHODE='MUMPS'" + OOC + "),")
    before = len(log_text())
    u.mumps_memory_note({"mumps_memory": "bogus"})
    u.mumps_memory_note({"mumps_memory": "out_of_core", "lin_solver": "GCPC"})
    u.mumps_memory_note({"mumps_memory": "out_of_core"}, "harmonic_3d")
    new = log_text()[before:]
    check("note: WARNING for an unknown value",
          u"WARNING: Unknown value 'bogus' for mumps_memory" in new, new)
    check("note: WARNING for GCPC", u"with lin_solver GCPC it has no effect"
          in new, new)
    check("note: WARNING for complex matrices", u"keeps complex matrices in "
          u"memory anyway" in new, new)
    check("every analysis has the setting, default auto",
          all(a.get("mumps_memory") == "auto"
              for a in u.CONFIG_BRIDGE["analyses"].values()),
          [k for k, a in u.CONFIG_BRIDGE["analyses"].items()
           if a.get("mumps_memory") != "auto"])


def _comm(tmp, model, analysis, settings):
    d = tempfile.mkdtemp(dir=tmp)
    liml = os.path.join(d, "model.liml")
    shutil.copy(model, liml)
    cfg = u.CONFIG_BRIDGE
    saved = dict(cfg["analyses"][analysis])
    cfg["work_dir"] = d
    cfg["active_analysis"] = analysis
    cfg["analyses"][analysis].update(settings)
    try:
        md = extract_aster_data_from_liml(liml)
        mail = os.path.join(d, "model.mail")
        if not (md and write_mesh(mail, md) and
                generate_AsterSolver_files(d, md, mail, "test.resu")):
            return None
        with io.open(glob.glob(os.path.join(d, "*.comm"))[0],
                     encoding="utf-8") as f:
            return f.read()
    finally:
        cfg["analyses"][analysis].clear()
        cfg["analyses"][analysis].update(saved)
        cfg["work_dir"] = tmp


def _mumps_lines(text):
    return [line.strip() for line in (text or u"").splitlines()
            if u"METHODE='MUMPS'" in line and
            not line.strip().startswith(u"#")]


def test_comm(tmp):
    static = os.path.join(_REPO, "TestFiles", "Voorbeelden", "Voorbeeld_A.liml")
    nonlin = os.path.join(_REPO, "TestFiles", "BezwijkenTrekstaaf.liml")
    base = _comm(tmp, static, "lin_static_3d", {})
    lines = _mumps_lines(base)
    check("static auto: one MUMPS line without the keywords",
          len(lines) == 1 and u"ACCELERATION" not in lines[0] and
          u"GESTION_MEMOIRE" not in lines[0], lines)
    lines = _mumps_lines(_comm(tmp, static, "lin_static_3d",
                               {"mumps_memory": "low_rank"}))
    check("static low_rank", len(lines) == 1 and lines[0].endswith(
        u"RESI_RELA=1e-05" + LR + u"),"), lines)
    lines = _mumps_lines(_comm(tmp, static, "lin_static_3d",
                               {"mumps_memory": "low_rank",
                                "lin_solver": "GCPC"}))
    check("static GCPC: no MUMPS line", lines == [], lines)
    # #ASTER-OPTIE: generate_AsterSolver_files passes the analysis through
    # bridge_custom.apply_options before the builders
    override = u.mumps_keywords(__import__("bridge_custom").apply_options(
        u.CONFIG_BRIDGE["analyses"]["lin_static_3d"],
        {"mumps_memory": "out_of_core"}))
    check("#ASTER-OPTIE mumps_memory overrides the setting", override == OOC,
          override)
    lines = _mumps_lines(_comm(tmp, nonlin, "nonlin_static_3d",
                               {"mumps_memory": "low_rank"}))
    check("nonlinear low_rank", lines and all(l.endswith(LR + u"),")
                                              for l in lines), lines)
    explicit = [k for k, a in u.CONFIG_BRIDGE["analyses"].items()
                if a.get("solver_command") == "DYNA_NON_LINE"]
    for name in explicit:
        lines = _mumps_lines(_comm(tmp, nonlin, name,
                                   {"mumps_memory": "low_rank",
                                    "schema": "DIFF_CENT"}))
        check(name + " explicit: no low rank",
              lines and not any(u"ACCELERATION" in l for l in lines), lines)
        lines = _mumps_lines(_comm(tmp, nonlin, name,
                                   {"mumps_memory": "low_rank",
                                    "schema": "HHT"}))
        check(name + " implicit: low rank",
              lines and all(l.endswith(LR + u"),") for l in lines), lines)
    lines = _mumps_lines(_comm(tmp, static, "modal_3d",
                               {"mumps_memory": "low_rank"}))
    check("modal low_rank: eigen solve full rank",
          any(u"ACCELERATION" not in l for l in lines), lines)
    lines = _mumps_lines(_comm(tmp, static, "modal_3d",
                               {"mumps_memory": "out_of_core"}))
    check("modal out_of_core: every MUMPS line",
          lines and all(OOC in l for l in lines), lines)


_MESS = u"""Entering DMUMPS 5.6.2 with JOB, N, NNZ =   1      216849        8049376
ICNTL(22)  Out-of-core option (1=on, off otherwise)=      -999
    Total space in MBytes, IC factorization      (INFOG(17)):        3800
    Total space in MBytes,  OOC factorization    (INFOG(27)):         988
Entering DMUMPS 5.6.2 with JOB, N, NNZ =   2      216849        8049376
 ICNTL(22) Out-of-core option               =               {0}
"""


def _report(tmp, body, solver=u"METHODE='MUMPS',"):
    d = tempfile.mkdtemp(dir=tmp)
    mess = os.path.join(d, "m_1.mess")
    text = (u"res = MECA_STATIQUE(\n    SOLVEUR=_F(" + solver +
            u" NPREC=8),\n    INFO=2)\n"
            u"  Le système linéaire à résoudre a 216849 "
            u"degrés de liberté:\n" + body +
            u"# Fin commande #0010\n")
    with io.open(mess, "w", encoding="utf-8") as f:
        f.write(text)
    with io.open(os.path.join(d, "m_1.export"), "w", encoding="utf-8") as f:
        f.write(u"P actions make_etude\nP memory_limit 2048\n")
    return bridge_run_aster.mumps_memory_report(mess)


def test_report(tmp):
    got = _report(tmp, _MESS.format(1))
    check("report: out of core -> WARNING with estimate and memory_limit",
          len(got) == 1 and u"3800 MB" in got[0] and u"2048" in got[0] and
          u"low_rank" in got[0], got)
    check("report: in core -> nothing", _report(tmp, _MESS.format(0)) == [])
    check("report: out_of_core asked -> nothing",
          _report(tmp, _MESS.format(1), u"GESTION_MEMOIRE='OUT_OF_CORE', "
                  u"METHODE='MUMPS',") == [])
    got = _report(tmp, _MESS.format(1), u"ACCELERATION='LR+', "
                  u"METHODE='MUMPS',")
    check("report: low_rank -> no estimate", len(got) == 1 and
          u"3800" not in got[0] and u"2048" in got[0], got)
    # retry: first factorization in core failed, second out of core
    retry = _MESS.format(0) + _MESS.format(1)
    check("report: the last factorization counts",
          len(_report(tmp, retry)) == 1)
    check("report: no MUMPS statistics -> nothing",
          _report(tmp, u"nothing\n") == [])


def main():
    tmp = tempfile.mkdtemp(prefix="mumps_memory_")
    cfg = u.CONFIG_BRIDGE
    saved = (cfg.get("work_dir", ""), cfg.get("active_analysis"),
             cfg.get("language"))
    cfg["work_dir"] = tmp              # in memory only: log goes here
    cfg["language"] = "en"
    try:
        test_helpers()
        test_comm(tmp)
        test_report(tmp)
    finally:
        cfg["work_dir"], cfg["active_analysis"], cfg["language"] = saved
        shutil.rmtree(tmp, True)
    if FAILED:
        print("{0} failure(s): {1}".format(len(FAILED), ", ".join(FAILED)))
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
