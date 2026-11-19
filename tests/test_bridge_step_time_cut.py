# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (CPython and IronPython 2.7) of the time list of Nonlinear
# Static without Quasi-static (no <timesteps>): like Mecway, every load
# table only up to t = 1 s (bridge_to_aster._cut_at_step_time,
# _build_listinst_block).
#
#   python tests/test_bridge_step_time_cut.py

from __future__ import print_function

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils as u  # noqa: E402
import bridge_to_aster as b  # noqa: E402

LOG = []
b.log = lambda msg: LOG.append(msg)
ANALYSIS = {"substeps_per_interval": 10, "default_time_end": 1.0}
FAILS = []


def check(name, ok):
    print(("OK   " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


def times_of(funcs, model_data, analysis=ANALYSIS):
    """(DEBUT, [JUSQU_A ...], t_end, warnings) of _build_listinst_block."""
    del LOG[:]
    block, t_end = b._build_listinst_block(funcs, analysis, model_data)
    debut = float(re.search(r"DEBUT=([-+0-9.eE]+)", block).group(1))
    upto = [float(x) for x in re.findall(r"JUSQU_A=([-+0-9.eE]+)", block)]
    warns = [m for m in LOG if m.startswith("WARNING")]
    return debut, upto, t_end, warns


NO_TS = {}                                        # no <timesteps>
TP = {"timesteps": {"period": 2.0}}               # time points, no step

# 1. a table that runs past 1 s: cut at 1 s, one WARNING (both languages:
#    same placeholders)
for lang in ("nl", "en"):
    u.CONFIG_BRIDGE["language"] = lang
    d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 2100.0)])], NO_TS)
    check("long table: 0 -> 1 s (%s)" % lang,
          d == 0.0 and up == [1.0] and te == 1.0)
    check("long table: one WARNING naming 2 s and 1 s (%s)" % lang,
          len(w) == 1 and "t = 2 s" in w[0] and "t = 1 s" in w[0])
u.CONFIG_BRIDGE["language"] = "en"

# 1b. round-off around 1 s: no cut, no WARNING; just above: cut
d, up, te, w = times_of([("f", [(0.0, 0.0), (1.0000000001, 1.0)])], NO_TS)
check("1 s + 1e-10: not cut", te == 1.0000000001 and not w)
d, up, te, w = times_of([("f", [(0.0, 0.0), (1.0000000001, 1.0),
                                (2.0, 0.0)])], NO_TS)
check("1 s + 1e-10 and 2 s: ends at 1 s", te in (1.0, 1.0000000001)
      and up[-1] == te and len(w) == 1)

# 2. a table that ends before 1 s: unchanged, no WARNING
d, up, te, w = times_of([("f", [(0.0, 0.0), (0.5, 10.0)])], NO_TS)
check("short table unchanged", d == 0.0 and up == [0.5] and te == 0.5
      and not w)

# 3. two tables, one short and one long: the short kink stays
d, up, te, w = times_of([("f", [(0.0, 0.0), (0.5, 1.0)]),
                         ("g", [(0.0, 0.0), (3.0, 1.0)])], NO_TS)
check("short + long: 0.5 and 1 s", up == [0.5, 1.0] and te == 1.0
      and len(w) == 1)

# 4. a kink exactly at 1 s: no duplicate time
d, up, te, w = times_of([("f", [(0.0, 0.0), (1.0, 5.0), (2.0, 0.0)])], NO_TS)
check("kink at 1 s: once", up == [1.0] and te == 1.0)

# 5. a table that starts at or after 1 s: from 0 to 1 s
d, up, te, w = times_of([("f", [(1.5, 0.0), (3.0, 1.0)])], NO_TS)
check("late table: 0 -> 1 s", d == 0.0 and up == [1.0] and te == 1.0)
d, up, te, w = times_of([("f", [(1.0, 0.0), (3.0, 1.0)])], NO_TS)
check("table from 1 s: 0 -> 1 s", d == 0.0 and up == [1.0] and te == 1.0)

# 6. <timesteps> without step size (time points): up to the period, like
#    Mecway (INFO, no WARNING); also when the tables end earlier
INFOS = lambda: [m for m in LOG if m.startswith("INFO: Load table")]
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)])], TP)
check("time points: table to the period: unchanged", up == [2.0] and te == 2.0
      and not w and not INFOS())
TP15 = {"timesteps": {"period": 1.5, "increment": 0.5}}
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)])], TP15)
check("time points: table past the period ends at 1.5 s",
      up == [1.5] and te == 1.5 and not w and len(INFOS()) == 1)
del LOG[:]
block, te = b._build_listinst_block([("f", [(0.0, 0.0), (1.0, 1.0)])],
                                    ANALYSIS, TP15)
check("time points: short table held up to the period (INFO)",
      te == 1.5 and "JUSQU_A=1.0, NOMBRE=10" in block
      and "JUSQU_A=1.5, NOMBRE=10" in block
      and len([m for m in LOG if "held up to" in m]) == 1)
d, up, te, w = times_of([], {"timesteps": {"period": 3.0}},
                        {"substeps_per_interval": 10, "default_time_end": 1.0})
check("time points, no table: 0 -> period (not default_time_end)",
      d == 0.0 and up == [3.0] and te == 3.0)
d, up, te, w = times_of([("f", [(0.0, 0.0), (1.5, 1.0), (2.0, 0.0)])], TP15)
check("time points: kink at the period once", up == [1.5] and te == 1.5)
d, up, te, w = times_of([("f", [(0.0, 0.0), (1.5000000001, 1.0)])], TP15)
check("time points: period + 1e-10 not a separate time",
      te in (1.5, 1.5000000001) and len(up) == 1)
d, up, te, w = times_of([("f", [(2.0, 0.0), (3.0, 1.0)])], TP15)
check("time points: table after the period: 0 -> period",
      d == 0.0 and up == [1.5] and te == 1.5)
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)]),
                         ("_temp", [(0.0, 300.0), (3.0, 400.0)])], TP15)
check("time points: temperature history cut at the period too", te == 1.5)
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)])],
                        {"timesteps": {"period": 0.0}})
check("period 0: old behaviour (not cut)", te == 2.0)
# automatic time stepping in the model but the setting off: this branch
md_auto = {"timesteps": {"period": 1.5, "increment": 0.5, "automatic": True}}
an_off = dict(ANALYSIS, auto_time_stepping=False)
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)])], md_auto, an_off)
check("automatic in the model, setting off: cut at the period", te == 1.5)

# 7. model_data None: not cut (old callers)
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)])], None)
check("model_data None: not cut", te == 2.0 and not w)

# 8. no table at all: 0 -> default_time_end (unchanged, also when that
#    setting is not 1)
d, up, te, w = times_of([], NO_TS, {"substeps_per_interval": 10,
                                    "default_time_end": 3.0})
check("no table: default_time_end", up == [3.0] and te == 3.0 and not w)

# 9. the step time does not follow default_time_end
d, up, te, w = times_of([("f", [(0.0, 0.0), (2.0, 1.0)])], NO_TS,
                        {"substeps_per_interval": 10,
                         "default_time_end": 0.5})
check("step time stays 1 s", te == 1.0)

# 10. temperature tables are cut at the same time
md = {"thermal_stress": {"tref": 293.15},
      "temperatures": [{"value": [(0.0, 300.0), (1.0, 390.0),
                                  (2.0, 340.0)]}]}
md["temperatures"][0]["selection"] = "All"
del LOG[:]
h = b._temperature_histories(md, b._MECWAY_STEP_TIME)
check("temperature cut at the step time",
      h and h[0][1][-1][0] == b._MECWAY_STEP_TIME)
check("temperature cut: one WARNING", len([m for m in LOG
                                          if m.startswith("WARNING")]) == 1)
# (_build_nonlin_static passes _MECWAY_STEP_TIME, not default_time_end:
# checked by reading the code; the verification cases NL-75..75d run with
# default_time_end = 1.)

# 11. end state only to Mecway (NL-75e/f/g): flag only for time points
#     with Mecway's Automatic time stepping off
def end_flag(md, analysis=ANALYSIS):
    md = dict(md)
    b._build_listinst_block([("f", [(0.0, 0.0), (2.0, 1.0)])], analysis, md)
    return md.get("_end_only")
check("end only: time points, automatic off", end_flag(TP15) == 1.5)
check("end only: not with Mecway's automatic on (setting off)",
      end_flag(md_auto, an_off) is None)
check("end only: not without <timesteps>", end_flag({}) is None)

# 12. the export filter (aster_results_export runs in Code-Aster's
#     Python 3; only checked under CPython 3)
if sys.version_info[0] >= 3:
    import aster_results_export as x
    T3 = {0: 0.0, 1: 0.5, 2: 1.0, 3: 1.5}
    check("export: end reached -> t = 0 and the end",
          x._end_state_only(T3, [0, 1, 2, 3], 1.5) == [0, 3])
    check("export: stopped early -> every step",
          x._end_state_only(T3, [0, 1, 2], 1.5) == [0, 1, 2])
    check("export: end within 1e-9", x._end_state_only(
        {0: 0.0, 1: 0.5, 2: 1.5 * (1 + 1e-12)}, [0, 1, 2], 1.5) == [0, 2])
    check("export: two steps unchanged",
          x._end_state_only({0: 0.0, 1: 1.5}, [0, 1], 1.5) == [0, 1])
    check("export: unknown last time -> every step",
          x._end_state_only({0: 0.0, 1: 0.5}, [0, 1, 2], 1.5) == [0, 1, 2])

# 13. gating in the generated job (NL-75e: CCX time points, Automatic time
#     stepping off): end_only in study.comm, not with fatigue (#ASTER-WOHLER)
#     (smoke test as in AGENTS.md: CPython only)
import io as _io
import shutil
import tempfile
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402
from bridge_to_aster import generate_AsterSolver_files  # noqa: E402
SRC = os.path.join(_HERE, "..", "TestFiles", "Verificatie", "modellen",
                   "NL-75e.liml")


def comm_of(liml_text):
    tmp = tempfile.mkdtemp(prefix="steptime_")
    try:
        _io.open(os.path.join(tmp, "model.liml"), "w",
                 encoding="utf-8").write(liml_text)
        u.CONFIG_BRIDGE["work_dir"] = tmp
        u.CONFIG_BRIDGE["active_analysis"] = "nonlin_static_3d"
        md = extract_aster_data_from_liml(os.path.join(tmp, "model.liml"))
        if not write_mesh(os.path.join(tmp, "model_mesh.mail"), md):
            return ""
        if not generate_AsterSolver_files(tmp, md, os.path.join(
                tmp, "model_mesh.mail"), "test.resu"):
            return ""
        return _io.open(os.path.join(tmp, "study.comm"),
                        encoding="utf-8").read()
    finally:
        shutil.rmtree(tmp, True)


if sys.version_info[0] < 3:
    print("SKIP job checks: CPython 3 only (write_mesh without Mecway)")
elif os.path.exists(SRC):
    text = _io.open(SRC, encoding="utf-8").read()
    c = comm_of(text)
    check("job: time points -> end_only=1.5 in study.comm",
          "end_only=1.5" in c)
    wohler = (u"<ccxmodeldefinition>** ASTER-WOHLER Staal: S = [100, 150, "
              u"250, 400] MPa, N = [1e7, 2e6, 2e5, 1e4]</ccxmodeldefinition>")
    c = comm_of(text.replace(u"</liml>", wohler + u"\n</liml>"))
    check("job: with #ASTER-WOHLER no end_only", c and "end_only" not in c)
else:
    print("SKIP job checks: " + SRC)

print("{0} failure(s)".format(len(FAILS)))
sys.exit(1 if FAILS else 0)
