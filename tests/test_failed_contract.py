# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Contract failed/1 (AGENTS.md): the bridge's writer of the element variable
# "failed" (aster_results_export._failed_var, written with _write_fragment
# as in the job) read by the core liml_failed.py (copy of AdvancedToolsHub's
# common/liml_failed.py). A mini model of four hex8 elements, four time
# steps (t = 0.25, 0.5, 0.75, 1.0) and these failure times:
#   element 1: 0.5  (exactly a step time: failed from the next step, k = 2)
#   element 2: 1.0  (the last step: stays visible, not failed)
#   element 3: 0.3  (between two steps: k = 1)
#   element 4: 0.1  (before the first step: k = 0)
# Cases: one solution; with a Saved monitor (<savedmonitor> right after
# <results>); a model with two configurations (name passed: the steps of
# that solution; None: the core's refusal "configurations").
#
# Stage 1 (CPython with numpy, as the job; reruns itself with Code-Aster's
# Python when numpy is missing): writes the fragments, splices them into
# the model by hand (the layout of bridge_results_liml.splice_results) and
# checks scan(solver="aster") and process(). Stage 2 (Mecway's IronPython
# 2.7.9 through TestFiles/Tools/run_ipy.ps1, skipped without Mecway): the
# same fragments through the real splice_results (IronPython only), then
# the same checks.
#
#   python tests/test_failed_contract.py

from __future__ import print_function

import glob
import io
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
IRONPYTHON = sys.platform == "cli"
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import liml_failed as L  # noqa: E402

FAILED = []
TIMES = {0: 0.25, 1: 0.5, 2: 0.75, 3: 1.0}
FAIL_AT = {1: 0.5, 2: 1.0, 3: 0.3, 4: 0.1}
EXPECTED = {1: 2, 3: 1, 4: 0}
# configuration B: element 2 fails at 0.6 (k = 2), the others never
FAIL_AT_B = {2: 0.6}
EXPECTED_B = {2: 2}
MONITOR = u"Code-Aster summary (test)\nline 2"


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


# ==========================================
# THE MODEL
# ==========================================
def _nodes():
    """20 nodes: five squares of four at x = 0, 1, 2, 3, 4."""
    out = []
    for i in range(5):
        for y, z in ((0, 0), (1, 0), (1, 1), (0, 1)):
            out.append((len(out) + 1, float(i), float(y), float(z)))
    return out


def _elements():
    """{eid: node list}: hex8 element e between squares e - 1 and e."""
    out = {}
    for e in range(1, 5):
        a = [4 * (e - 1) + k for k in (1, 2, 3, 4)]
        b = [4 * e + k for k in (1, 2, 3, 4)]
        out[e] = [a[0], b[0], b[1], a[1], a[3], b[3], b[2], a[2]]
    return out


def model_text(configurations=()):
    nl = u"\r\n"
    lines = [u'<liml version="34">']
    lines += [u'  <configuration name="{0}" />'.format(c)
              for c in configurations]
    lines.append(u'  <analysis type="N31" />')
    lines += [u'  <node nid="{0}" x="{1:g}" y="{2:g}" z="{3:g}" />'.format(*n)
              for n in _nodes()]
    lines.append(u'  <elset name="Bar" material="Steel" colorrgb="00C800">')
    for e, nodes in sorted(_elements().items()):
        lines.append(u'    <elem eid="{0}" shape="hex8" nodes="{1}" />'.format(
            e, u" ".join(str(n) for n in nodes)))
    lines.append(u"  </elset>")
    lines.append(u'  <material name="Steel">')
    lines.append(u'    <mechanical type="Isotropic" youngsmodulus="210 GPa" '
                 u'poissonratio="0.3" />')
    lines.append(u"  </material>")
    lines.append(u'  <timesteps timeperiod="1 s" />')
    return nl.join(lines) + nl + u"</liml>" + nl


# ==========================================
# STAGE 1: THE WRITER (CPython with numpy)
# ==========================================
def numpy_or_rerun():
    """numpy is there, or this script reruns with Code-Aster's Python
    (exit code of that run), or None when there is no such Python."""
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        pats = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                      "code_aster", "*", "*", "Python*",
                                      "python.exe"))
        if not pats:
            return None
        sys.exit(subprocess.call([sorted(pats)[-1],
                                  os.path.abspath(__file__)]))


class _Data(object):
    """Stand-in for aster_results_export._Fields: only the step index."""

    def __init__(self):
        self.index = None

    def set_index(self, index):
        self.index = index


def write_fragment(path, fail_at, precision):
    """A result fragment as the job writes it: displacements and failed."""
    import numpy as np
    import aster_results_export as are
    elems = _elements()
    model = {"elements": dict((e, ("hex8", n)) for e, n in elems.items()),
             "elsets": {"Bar": sorted(elems)}}
    nodes = np.arange(1, 21, dtype="<i4")

    def displ(c):
        return lambda d: 1e-3 * (d.index + 1) * c * np.arange(1.0, 21.0)
    variables = [are._Var(name, False, nodes, displ(c)) for name, c in
                 (("displx", 1.0), ("disply", 0.5), ("displz", 0.25))]
    variables.append(are._Var(
        "vonmises", True, np.array(sorted(elems), dtype="<i4"),
        lambda d: np.full(32, 100.0 * (d.index + 1))))
    variables.append(are._failed_var(fail_at, model, TIMES))
    elset_nodes, free_nodes = are._group_nodes(model, 20)
    for var in variables:
        are._assign_groups(var, model, elset_nodes, free_nodes)
    with open(path, "wb") as f:
        are._write_fragment(f, variables, _Data(), sorted(TIMES), TIMES,
                            precision, model)


def _copy_lines(model, configuration):
    """The model copy inside <solution>, as bridge_results_liml._model_copy
    (two spaces deeper, without <configuration> definitions)."""
    body = model.split(u"\r\n")[1:]
    out = []
    for line in body:
        if not line.strip() or line.startswith(u"</liml"):
            continue
        if line.lstrip().startswith(u"<configuration "):
            continue
        out.append(u"  " + line)
    return out


def hand_splice(model, fragments, monitor=None):
    """model text with one <solution> per (configuration, fragment text)."""
    import bridge_monitor
    head = model[:model.index(u"</liml>")]
    parts = [head]
    for conf, frag in fragments:
        parts.append(u"  <solution>\r\n" if conf is None else
                     u'  <solution configuration="{0}">\r\n'.format(conf))
        parts.append(u"\r\n".join(_copy_lines(model, conf)) + u"\r\n")
        if monitor is not None:
            end = frag.index(u">", frag.index(u"<results")) + 1
            frag = (frag[:end] +
                    u"{0}".format(bridge_monitor.savedmonitor_block(monitor))
                    + frag[end:])
        parts.append(frag)
        parts.append(u"  </solution>\r\n")
    parts.append(u"</liml>\r\n")
    return u"".join(parts)


def _write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _read_text(path):
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def stage1(tmp):
    print("-- stage 1: writer (CPython), hand splice")
    write_fragment(os.path.join(tmp, "frag_a.xml"), FAIL_AT, "double")
    write_fragment(os.path.join(tmp, "frag_b.xml"), FAIL_AT_B, "single")
    _write(os.path.join(tmp, "model.liml"), model_text())
    _write(os.path.join(tmp, "model_conf.liml"), model_text(("A", "B")))
    frag_a = _read_text(os.path.join(tmp, "frag_a.xml"))
    frag_b = _read_text(os.path.join(tmp, "frag_b.xml"))
    check("fragment holds the empty <nodes /> tails",
          frag_a.count(u"<nodes />") == 3 * 4 and
          frag_a.count(u"<elements />") == 2 * 4)
    one = os.path.join(tmp, "hand_one.liml")
    _write(one, hand_splice(model_text(), [(None, frag_a)]))
    mon = os.path.join(tmp, "hand_monitor.liml")
    _write(mon, hand_splice(model_text(), [(None, frag_a)], MONITOR))
    conf = os.path.join(tmp, "hand_conf.liml")
    _write(conf, hand_splice(model_text(("A", "B")),
                             [("A", frag_a), ("B", frag_b)]))
    verify(tmp, one, mon, conf, "hand")


# ==========================================
# THE CHECKS (both stages)
# ==========================================
def _code(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except L.LimlFailedError as e:
        return e.code
    return None


def _count(path, token):
    with open(path, "rb") as f:
        return f.read().count(token)


def verify(tmp, one, mon, conf, tag):
    rep = L.scan(one, solver="aster")
    check(tag + ": scan accepts the writer, provider failed",
          rep["provider"] == "failed" and rep["code"] == "scanned",
          (rep["provider"], rep["code"]))
    check(tag + ": failure steps {0}".format(sorted(EXPECTED.items())),
          rep["failed"] == EXPECTED, rep["failed"])
    rep = L.scan(mon, solver="aster")
    check(tag + ": with Saved monitor the same steps",
          rep["failed"] == EXPECTED, rep["failed"])
    rep = L.scan(conf, solver="aster", configuration="A")
    check(tag + ": configuration A", rep["failed"] == EXPECTED, rep["failed"])
    rep = L.scan(conf, solver="aster", configuration="B")
    check(tag + ": configuration B", rep["failed"] == EXPECTED_B,
          rep["failed"])
    code = _code(L.scan, conf, solver="aster")
    check(tag + ": two solutions without a name are refused",
          code == "configurations", code)
    for name, src, kw in (("one", one, {}), ("monitor", mon, {}),
                          ("conf", conf, {"configuration": "B"})):
        out = os.path.join(tmp, "{0}_{1}_out.liml".format(tag, name))
        rep = L.process(src, out, solver="aster", others="zero", **kw)
        check(tag + ": process {0} written".format(name),
              rep["written"] and rep["code"] == "done", rep["code"])
        check(tag + ": {0} keeps the <nodes /> and <elements /> tails"
              .format(name),
              _count(out, b"<nodes />") == _count(src, b"<nodes />") and
              _count(out, b"<elements />") == _count(src, b"<elements />"))
        check(tag + ": {0} has the marker".format(name),
              L.processed_marker(out, kw.get("configuration")) ==
              L.VERSION)
    check(tag + ": the Saved monitor stays",
          _count(os.path.join(tmp, tag + "_monitor_out.liml"),
                 b"<savedmonitor>") == 1)


# ==========================================
# STAGE 2: THE REAL SPLICE (IronPython)
# ==========================================
def stage2(tmp):
    print("-- stage 2: splice_results (IronPython)")
    import bridge_results_liml as brl
    import bridge_monitor
    frag_a = os.path.join(tmp, "frag_a.xml")
    frag_b = os.path.join(tmp, "frag_b.xml")
    one = os.path.join(tmp, "ipy_one.liml")
    shutil.copy(os.path.join(tmp, "model.liml"), one)
    ok, reason = brl.splice_results(one, frag_a, one)
    check("splice one", ok, reason)
    mon = os.path.join(tmp, "ipy_monitor.liml")
    shutil.copy(os.path.join(tmp, "model.liml"), mon)
    ok, reason = brl.splice_results(mon, frag_a, mon, monitor=MONITOR)
    check("splice with monitor", ok, reason)
    check("<savedmonitor> right after <results>",
          bridge_monitor is not None and _monitor_first(mon))
    conf = os.path.join(tmp, "ipy_conf.liml")
    shutil.copy(os.path.join(tmp, "model_conf.liml"), conf)
    ok, reason = brl.splice_results(conf, frag_a, conf, "A")
    ok2, reason2 = brl.splice_results(conf, frag_b, conf, "B")
    check("splice configurations A and B", ok and ok2, (reason, reason2))
    verify(tmp, one, mon, conf, "ipy")


def _monitor_first(path):
    with open(path, "rb") as f:
        lines = [x.strip() for x in f.read().split(b"\n")]
    for i, line in enumerate(lines):
        if line.startswith(b"<results"):
            return lines[i + 1] == b"<savedmonitor>"
    return False


def run_stage2(tmp):
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP stage 2 (needs Mecway's IronPython)")
        return
    wrapper = os.path.join(tmp, "run_failed_contract.py")
    with io.open(wrapper, "w", encoding="utf-8") as f:
        f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                u"import test_failed_contract as t\n"
                u"sys.exit(t.ipy_main(sys.argv[1]))\n".format(
                    os.path.abspath(_HERE)))
    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         os.path.abspath(ps), "-Script", wrapper, "-ScriptArgs", tmp],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.communicate()[0].decode("utf-8", "replace")
    print("--- IronPython 2.7.9 ---")
    print(out.strip())
    check("IronPython stage without failures", proc.returncode == 0 and
          "FAIL" not in out and "All tests passed." in out)


def ipy_main(tmp):
    stage2(tmp)
    return finish()


def finish():
    if FAILED:
        print("{0} failure(s): {1}".format(len(FAILED), ", ".join(FAILED)))
        return 1
    print("All tests passed.")
    return 0


def main():
    if IRONPYTHON:
        print("run this test with CPython (stage 1 needs numpy)")
        return 2
    if numpy_or_rerun() is None:
        print("SKIP: no Python with numpy (the writer runs in the "
              "Code-Aster job)")
        return 0
    tmp = tempfile.mkdtemp(prefix="failed_contract_")
    try:
        stage1(tmp)
        run_stage2(tmp)
    finally:
        shutil.rmtree(tmp, True)
    return finish()


if __name__ == "__main__":
    sys.exit(main())
