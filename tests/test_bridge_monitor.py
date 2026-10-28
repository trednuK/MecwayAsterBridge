# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of Mecway's Saved monitor written by the bridge (GitHub
# issue #7; Scripts/bridge_monitor.py and bridge_results_liml.splice_results
# with monitor=...), Python 2.7 (IronPython) and 3:
#   - the summary of a .mess of a successful run (DIAGNOSTIC JOB, version,
#     bridge lines, timing table, no blank lines from CR CR LF) and of a
#     failed run (every error/alarm box once with its count, <EXCEPTION>,
#     Python error from the console output, failed nonlinear step, no
#     DIAGNOSTIC JOB, the end of the .mess);
#   - "full" (truncation with a note) and "off";
#   - the XML text: escaped, ASCII with character references, without
#     control characters, CRLF; it reads back to the same text;
#   - splice_results (IronPython 2.7.9 only: it works on byte strings):
#     <savedmonitor> first in <results>, one top-level <savedmonitor />,
#     none in the model copies, a solution with only the monitor, and a
#     second splice does not add a second tree item; has_results (a failed
#     run writes the monitor-only solution only when it is False: stub and
#     monitor-only solutions do not count, a solution with results does). Under CPython this
#     part runs through TestFiles/Tools/run_ipy.ps1 if Mecway is installed.
#
#   python tests/test_bridge_monitor.py

from __future__ import print_function

import io
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_monitor as bm  # noqa: E402
import bridge_results_liml as brl  # noqa: E402

DATA = os.path.join(_HERE, "data")
MODEL = os.path.join(DATA, "config_model.liml")
FRAGMENT = os.path.join(DATA, "config_model_results.xml")
IRONPYTHON = sys.platform == "cli"


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        check.failed = True


check.failed = False

TOP = u" \u2554" + u"\u2550" * 40 + u"\u2557"
BOTTOM = u" \u255a" + u"\u2550" * 40 + u"\u255d"


def box(*lines):
    return [TOP] + [u" \u2551 " + l.ljust(38) + u" \u2551" for l in lines] \
        + [BOTTOM]


HEADER = [u"-- CODE_ASTER -- VERSION : EXPLOITATION (stable) --",
          u"                Version 17.4.0 modifi\u00e9e le 22/01/2026"]

GOOD = HEADER + [
    u"res = MECA_STATIQUE(...)",
    u"[ 50%] Instant calcul\u00e9 : 5.00000e-01, dernier instant",
    u"[100%] Instant calcul\u00e9 : 1.00000e+00, dernier instant",
    u"BRIDGE_STATCHECK M=7.85 ZWP=0,0,0",
    u"aster_results_export: x_results.xml geschreven: 1 stap(pen)",
] + box(u"<I> <CATAMESS_89>", u"", u"aucune alarme") + [
    u"<I> <FIN> ARRET NORMAL DANS \"FIN\" PAR APPEL A \"JEFINI\".",
    u" " + u"*" * 40 + u"\r",
    u" * COMMAND        :  USER : ELAPSED *\r",
    u" " + u"*" * 40 + u"\r",
    u" * DEBUT          :  0.09 :    0.00 *\r",
    u" * TOTAL_JOB      :  0.52 :    0.00 *\r",
    u" " + u"*" * 40 + u"\r",
    u"End of the Code_Aster execution",
    u"--- DIAGNOSTIC JOB : OK",
]

BAD = HEADER + [
    u"res = STAT_NON_LINE(INCREMENT=_F(LIST_INST=times))",
    u"Instant de calcul:  5.000000000000e-01 - Niveau de d\u00e9coupe: 1",
    u"|     NEWTON     |     RESIDU     |     RESIDU     |     OPTION     |",
    u"|    ITERATION   |     RELATIF    |     ABSOLU     |   ASSEMBLAGE   |",
    u"|                | RESI_GLOB_RELA | RESI_GLOB_MAXI |(+ TYPE MATRICE)|",
    u"|     0        X | 3.13655E-04  X | 4.94908E+00    |TANGENTE   (SYM)|",
    u"|     1          | 1.08852E-10    | 1.71799E-06    |TANGENTE   (SYM)|",
    u"Crit\u00e8re(s) de convergence atteint(s)",
    u"* Nombre d'it\u00e9rations de Newton                     : 2",
    u"[ 50%] Instant calcul\u00e9 : 5.00000e-01, dernier instant",
    u"Instant de calcul:  1.000000000000e+00 - Niveau de d\u00e9coupe: 1",
    u"|     NEWTON     |     RESIDU     |     RESIDU     |     OPTION     |",
    u"|    ITERATION   |     RELATIF    |     ABSOLU     |   ASSEMBLAGE   |",
    u"|                | RESI_GLOB_RELA | RESI_GLOB_MAXI |(+ TYPE MATRICE)|",
    u"|     0        X | 3.13655E-01  X | 4.94908E+04    |TANGENTE   (SYM)|",
    u"|     1        E | 2.13655E-01  X | 3.94908E+04    |TANGENTE   (SYM)|",
    u"<Erreur> Le nombre maximum d'it\u00e9rations est atteint.",
] + box(u"<A> <MECANONLINE5_21>", u"pas de temps red\u00e9coup\u00e9") + \
    box(u"<A> <MECANONLINE5_21>", u"pas de temps red\u00e9coup\u00e9") + \
    box(u"<A> <MECANONLINE5_21>", u"pas de temps red\u00e9coup\u00e9") + \
    box(u"<EXCEPTION> <MECANONLINE9_7>", u"Arr\u00eat par manque de",
        u"temps CPU ou divergence") + \
    box(u"<F> <DVP_1>", u"Erreur de programmation \x1b[0m") + [
    u"<E> <SUPERVIS_99> erreur sans cadre",
    u"Traceback (most recent call last):",
    u"  File \"study.comm\", line 12, in <module>",
    u"libaster.ConvergenceError: <MECANONLINE9_7>",
    u"EXECUTION_CODE_ASTER_EXIT_1234=1",
]

CONSOLE = (u"Traceback (most recent call last):\n"
           u"  File \"C:\\w\\study.comm\", line 40, in <module>\n"
           u"    FOO(1)\n"
           u"NameError: name 'FOO' is not defined\n")


def write(path, lines, nl=u"\r\n"):
    f = io.open(path, "w", encoding="utf-8", newline="")
    try:
        f.write(nl.join(lines) + nl)
    finally:
        f.close()


work = tempfile.mkdtemp()
try:
    good = os.path.join(work, "m_20261028_120000.mess")
    bad = os.path.join(work, "bad.mess")
    console = os.path.join(work, "bad_console.txt")
    write(good, GOOD)
    write(bad, BAD)
    write(console, CONSOLE.split(u"\n")[:-1], u"\n")

    # 1. Successful run
    head = [u"MecwayAsterBridge test", u"Model: m.liml"]
    t = bm.monitor_text(good, "summary", None, head)
    check("summary starts with the header", t.startswith(u"MecwayAsterBridge "
                                                         u"test\nModel: "))
    check("full .mess path in the summary", good in t)
    check("Code-Aster version", u"Code-Aster 17.4.0" in t)
    check("DIAGNOSTIC JOB line", u"--- DIAGNOSTIC JOB : OK" in t)
    check("no errors", u"No errors or alarms." in t)
    check("alarm list of FIN", u"aucune alarme" in t)
    check("bridge lines", u"BRIDGE_STATCHECK M=7.85" in t and
          u"aster_results_export: x_results.xml" in t)
    check("progress lines without nonlinear steps",
          u"== Progress ==" in t and u"[100%]" in t)
    check("timing table", u"* TOTAL_JOB" in t and u"* DEBUT" in t)
    i = t.index(u"== Time and memory ==")
    check("no blank lines in the timing table (CR CR LF)",
          u"\n\n *" not in t[i:t.index(u"== End of the .mess ==")])
    check("end of the .mess after the table",
          t.rstrip().endswith(u"--- DIAGNOSTIC JOB : OK") and
          t.count(u"* TOTAL_JOB") == 1)

    # 2. Failed run
    t = bm.monitor_text(bad, "summary", console, head)
    check("missing DIAGNOSTIC JOB reported", u"No DIAGNOSTIC JOB" in t)
    errors = t[t.index(u"== Errors and alarms =="):
               t.index(u"== Python errors (console) ==")]
    check("repeated alarm once with count",
          errors.count(u"<A> <MECANONLINE5_21>  (3 times)") == 1 and
          errors.count(u"pas de temps red\u00e9coup\u00e9") == 1)
    check("exception box complete", u"<EXCEPTION> <MECANONLINE9_7>" in t and
          u"temps CPU ou divergence" in t)
    check("<F> box", u"<F> <DVP_1>" in t)
    check("<E> message without a frame, once",
          errors.count(u"<E> <SUPERVIS_99>") == 1 and
          u"erreur sans cadre" in errors)
    check("Python error of the console",
          u"NameError: name 'FOO' is not defined" in t)
    check("nonlinear steps with the failed one",
          u"2 attempts, 1 converged, 1 failed" in t and u"FAILED" in t)
    check("end of the .mess (traceback)",
          u"libaster.ConvergenceError" in t.split(u"== End of the .mess ==")[1])
    order = [t.index(s) for s in (u"== Errors and alarms ==",
                                  u"== Python errors (console) ==",
                                  u"== Steps (nonlinear) ==",
                                  u"== End of the .mess ==")]
    check("sections in order", order == sorted(order))

    # 3. Modes full / off, limits
    check("off gives None", bm.monitor_text(good, "off") is None)
    check("unknown mode gives None", bm.monitor_text(good, "x") is None)
    check("missing .mess gives None",
          bm.monitor_text(os.path.join(work, "none.mess")) is None)
    full = bm.monitor_text(good, "full", None, head)
    check("full contains the whole .mess", u"res = MECA_STATIQUE(...)" in full
          and full.startswith(u"MecwayAsterBridge test"))
    old = bm.FULL_MAX_CHARS
    bm.FULL_MAX_CHARS = 200
    try:
        full = bm.monitor_text(bad, "full")
        check("full truncated with a note", u"characters skipped" in full and
              u"EXECUTION_CODE_ASTER_EXIT_1234=1" in full and
              len(full) < 600)
    finally:
        bm.FULL_MAX_CHARS = old
    old = bm.SUMMARY_MAX_CHARS
    bm.SUMMARY_MAX_CHARS = 300
    try:
        t2 = bm.monitor_text(bad, "summary")
        check("summary truncated with a note",
              t2.endswith(u"... truncated; see the full .mess.") and
              len(t2) < 400)
    finally:
        bm.SUMMARY_MAX_CHARS = old

    # 4. XML text
    raw = u"a < b & c > d\r\n\u00e9t\u00e9 \u2551\x1b[0m\tend\nx"
    esc = bm.xml_escape(raw)
    check("escaped ASCII text", esc == u"a &lt; b &amp; c &gt; d\r\n"
          u"&#233;t&#233; &#9553;[0m\tend\r\nx")
    block = bm.savedmonitor_block(t)
    elem = ET.fromstring(block.strip())
    check("block: <savedmonitor><output>", elem.tag == "savedmonitor" and
          [c.tag for c in elem] == ["output"])
    back = elem.find("output").text
    expect = bm._XML_BAD.sub(u"", t)
    check("block reads back to the same text", back == expect)

    # 5. splice_results (IronPython: byte strings)
    def splice_check():
        liml = os.path.join(work, "model.liml")
        shutil.copy(MODEL, liml)
        check("has_results: stub solutions do not count",
              not brl.has_results(liml, "ULS") and
              not brl.has_results(liml, None))
        ok, reason = brl.splice_results(liml, FRAGMENT, liml, "ULS",
                                        monitor=t)
        check("has_results: ULS after the splice, G not",
              brl.has_results(liml, "ULS") and
              not brl.has_results(liml, "G"))
        check("splice with monitor ok ({0})".format(reason), ok)
        root = ET.parse(liml).getroot()
        tops = [c for c in root if c.tag == "savedmonitor"]
        check("one top-level <savedmonitor />", len(tops) == 1 and
              len(list(tops[0])) == 0)
        sols = dict((s.get("configuration"), s) for s in root
                    if s.tag == "solution")
        check("no <savedmonitor> in the model copies",
              all(c.tag != "savedmonitor" for s in sols.values() for c in s))
        res = sols["ULS"].find("results")
        check("<savedmonitor> first in <results>",
              res is not None and res[0].tag == "savedmonitor" and
              res[0].find("output").text == expect)
        check("result variables still there",
              len(res.findall("nodevariable")) > 0 or
              len(res.findall("nodeids")) > 0)
        ok, reason = brl.splice_results(liml, FRAGMENT, liml, "ULS",
                                        monitor=u"second run")
        root = ET.parse(liml).getroot()
        check("second splice: still one tree item",
              len([c for c in root if c.tag == "savedmonitor"]) == 1)
        res = [s for s in root if s.tag == "solution" and
               s.get("configuration") == "ULS"][0].find("results")
        check("second splice: the new text",
              res[0].find("output").text == u"second run" and
              len([c for c in res if c.tag == "savedmonitor"]) == 1)
        # A run without results: a solution with only the monitor
        ok, reason = brl.splice_results(liml, None, liml, "ULS",
                                        monitor=u"failed run")
        check("monitor-only splice ok ({0})".format(reason), ok)
        root = ET.parse(liml).getroot()
        res = [s for s in root if s.tag == "solution" and
               s.get("configuration") == "ULS"][0].find("results")
        check("monitor-only: <results> with only <savedmonitor>",
              [c.tag for c in res] == ["savedmonitor"] and
              res[0].find("output").text == u"failed run")
        check("has_results: a monitor-only solution does not count",
              not brl.has_results(liml, "ULS"))
        # Model without configurations: no solution, results, monitor only
        plain = os.path.join(work, "plain.liml")
        f = io.open(plain, "w", encoding="utf-8", newline="")
        f.write(u'<liml version="34">\r\n  <analysis type="S30" />\r\n'
                u'</liml>\r\n')
        f.close()
        check("has_results: model without a solution",
              not brl.has_results(plain))
        brl.splice_results(plain, None, plain, None, monitor=u"x")
        check("has_results: plain monitor-only solution does not count",
              not brl.has_results(plain))
        f = io.open(plain, "w", encoding="utf-8", newline="")
        f.write(u'<liml version="34">\r\n  <analysis type="S30" />\r\n'
                u'  <solution>\r\n    <analysis type="S30" />\r\n'
                u'    <results precision="double">\r\n'
                u'      <savedmonitor>\r\n        <output>x</output>\r\n'
                u'      </savedmonitor>\r\n'
                u'      <nodeids name="displx">AQAAAA==\r\n</nodeids>\r\n'
                u'    </results>\r\n  </solution>\r\n</liml>\r\n')
        f.close()
        check("has_results: plain solution with results and a monitor",
              brl.has_results(plain))
        ok, _r = brl.splice_results(liml, None, liml, "ULS")
        check("no fragment and no monitor refused", not ok)
        # Without monitor the result is as before (no tree item added)
        shutil.copy(MODEL, liml)
        brl.splice_results(liml, FRAGMENT, liml, "ULS")
        check("without monitor: no <savedmonitor>",
              u"savedmonitor" not in io.open(liml, encoding="utf-8").read())
        # Model copy leaves out a multi-line <savedmonitor> element
        lines = brl._model_copy(u'<liml version="34">\r\n  <a />\r\n'
                                u'  <savedmonitor>\r\n    <output>x\r\n'
                                u'y</output>\r\n  </savedmonitor>\r\n'
                                u'  <b />\r\n', u"\r\n")
        check("model copy without <savedmonitor>",
              lines == [u"    <a />", u"    <b />"])

    if IRONPYTHON:
        splice_check()
finally:
    shutil.rmtree(work, True)

if not IRONPYTHON:
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps):
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", os.path.abspath(ps), "-Script",
             os.path.abspath(__file__)])
        out = out.decode("utf-8", "replace")
        print("--- IronPython 2.7.9 ---")
        print(out.strip())
        check("IronPython run without failures",
              "FAIL" not in out and "All tests passed." in out)
    else:
        print("SKIP splice_results (needs Mecway's IronPython)")

if check.failed:
    sys.exit(1)
print("All tests passed.")
