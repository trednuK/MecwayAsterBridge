# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of Scripts/bridge_element_node.py (route 'tabel', values per
# element node, KNOWN_BUGS 7) with a fake solution that behaves as a hidden
# Mecway 36.0.9815 did (see the header of the module):
#   - a mixed model (hex8, a quad4 shell on them, a line2 beam): Mecway's
#     vonmises per element node on the solids is replaced, stressxx (derived
#     by Mecway once the node variable exists) too; shells and beams stay
#     None, the node values equal Code-Aster's;
#   - a 2D model: the quad elements that have values are replaced (decided
#     by what Mecway has, not by the shape);
#   - shell components that route 'tabel' cleared are cleared per element
#     node too;
#   - non-contiguous element numbers: one list per number, None between;
#   - skips with the WARNING: a node with a value outside every element
#     with values (island), a Mecway without set_element_node_variable,
#     time steps, a section view, a failing call;
#   - a Mecway without element_node_value: nothing, no message.
# Python 2.7 (IronPython) and 3; under CPython it also runs once in
# Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1) when Mecway is
# installed.
#
#   python tests/test_bridge_element_node.py

from __future__ import print_function

import io
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
sys.dont_write_bytecode = True
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_element_node as ben  # noqa: E402

IRONPYTHON = sys.platform == "cli"
FAILED = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


class FakeSolution(object):
    """
    elements: {eid: [node ids]}; env: {name: {eid: [values]}} Mecway's own
    values per element node; derived: {name: {eid: [values]}} values that
    Mecway shows per element node once the node variable exists (stressxx).
    """

    def __init__(self, elements, env=None, derived=None, steps=()):
        self.elements = elements
        self.env = dict((k, dict(v)) for k, v in (env or {}).items())
        self.derived = dict((k, dict(v)) for k, v in (derived or {}).items())
        self.nodevals = {}
        self.steps = list(steps)
        self.calls = []

    def all_elements(self):
        return sorted(self.elements)

    def nodes(self, e):
        return list(self.elements[e])

    def time_steps(self):
        return list(self.steps)

    def modes(self):
        return []

    def element_node_value(self, name, e, k):
        if k < 1 or k > len(self.elements[e]):
            raise ValueError("Local node {0} does not exist".format(k))
        if e in self.env.get(name, {}):
            return self.env[name][e][k - 1]
        if name in self.nodevals and e in self.derived.get(name, {}):
            return self.derived[name][e][k - 1]
        return None

    def node_value(self, name, n):
        return self.nodevals.get(name, [None] * n)[n - 1]

    def set_variable(self, name, values, time_step=None, mode=None):
        self.nodevals[name] = list(values)    # Mecway's own per element stays
        return name

    def set_element_node_variable(self, name, values, time_step=None,
                                  mode=None):
        top = max(self.elements)
        if len(values) != top:
            raise ValueError("Solution has a highest element number of {0} "
                             "but the list ... {1}".format(top, len(values)))
        self.calls.append(name)
        self.env[name] = dict((e + 1, list(v)) for e, v in enumerate(values)
                              if v is not None and (e + 1) in self.elements)
        self.derived.pop(name, None)
        n = len(self.nodevals.get(name, [])) or max(
            x for ns in self.elements.values() for x in ns)
        out = [None] * n
        for e, vals in self.env[name].items():
            for node, v in zip(self.elements[e], vals):
                if v is not None:
                    out[node - 1] = v
        self.nodevals[name] = out
        return name


class NoWrite(FakeSolution):
    set_element_node_variable = None

    def __getattribute__(self, name):
        if name == "set_element_node_variable":
            raise AttributeError(name)
        return object.__getattribute__(self, name)


class NoRead(FakeSolution):
    def __getattribute__(self, name):
        if name in ("element_node_value", "set_element_node_variable"):
            raise AttributeError(name)
        return object.__getattribute__(self, name)


class Failing(FakeSolution):
    def set_element_node_variable(self, *a, **k):
        raise RuntimeError("boom")


# mixed: hex 1 (nodes 1-8), hex 2 (2 9 10 3 6 11 12 7), quad 3 on top of
# hex 1 (5 6 7 8), line 4 (1 2); node 13 only in quad 5 (an island)
MIXED = {1: [1, 2, 3, 4, 5, 6, 7, 8], 2: [2, 9, 10, 3, 6, 11, 12, 7],
         3: [5, 6, 7, 8], 4: [1, 2]}
OWN = {"vonmises": {1: [99.0] * 8, 2: [98.0] * 8},
       "vonmisesu1": {3: [5.0] * 4},
       "stressxxu1": {3: [4.0] * 4}}
DERIVED = {"stressxx": {1: [77.0] * 8, 2: [76.0] * 8}}
CA = [float(10 + i) for i in range(12)]          # Code-Aster, nodes 1-12


class DropOnSet(FakeSolution):
    """set_variable drops Mecway's own values per element node (as seen for
    vonmises in one probe): only the 'before' scan finds them."""

    def set_variable(self, name, values, time_step=None, mode=None):
        self.env.pop(name, None)
        return FakeSolution.set_variable(self, name, values)


class BrokenSteps(FakeSolution):
    def time_steps(self):
        raise RuntimeError("no steps")


def run(solution, arrays, cleared=(), section=None):
    state = ben.prepare(solution, list(arrays), section, list(cleared))
    for name, values in arrays.items():
        solution.set_variable(name, values)
    for name in cleared:
        solution.set_variable(name, [None] * 12)
    return ben.finish(solution, state, arrays, list(cleared))


def test_mixed():
    s = FakeSolution(MIXED, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": list(CA), "stressxx": list(CA),
                              "displx": list(CA)}, cleared=["stressxxu1"])
    check("mixed: vonmises, stressxx replaced, stressxxu1 cleared",
          sorted(replaced) == ["stressxx", "stressxxu1", "vonmises"] and
          not stale, (replaced, stale))
    check("mixed: hex values per element node are Code-Aster's",
          s.env["vonmises"][2] == [CA[n - 1] for n in MIXED[2]] and
          s.env["stressxx"][1] == [CA[n - 1] for n in MIXED[1]])
    check("mixed: shell and beam stay without values",
          3 not in s.env["vonmises"] and 4 not in s.env["vonmises"] and
          s.element_node_value("vonmises", 3, 1) is None)
    check("mixed: node values unchanged (Code-Aster's)",
          s.nodevals["vonmises"] == CA)
    check("mixed: shell layer variable not written (not in arrays)",
          s.env["vonmisesu1"] == {3: [5.0] * 4})
    check("mixed: cleared shell component is None per element node",
          s.element_node_value("stressxxu1", 3, 2) is None)
    check("mixed: displacements not touched", "displx" not in s.calls)


def test_before_scan():
    s = DropOnSet(MIXED, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": list(CA)}, cleared=["stressxxu1"])
    check("values found before set_variable are replaced and cleared",
          sorted(replaced) == ["stressxxu1", "vonmises"] and
          s.env["vonmises"][1] == [CA[n - 1] for n in MIXED[1]] and
          s.element_node_value("stressxxu1", 3, 1) is None, (replaced, stale))
    s = BrokenSteps(MIXED, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": list(CA)})
    check("time steps unreadable: skipped", replaced == [] and stale, stale)
    gl = FakeSolution(MIXED, {"greenlagrangestrainxx": {1: [1.0] * 8}})
    replaced, stale = run(gl, {"greenlagrangestrainxx": CA[:8] + [None] * 4})
    check("Green-Lagrange strain replaced",
          replaced == ["greenlagrangestrainxx"], replaced)


def test_2d():
    quads = {1: [1, 2, 5, 4], 2: [2, 3, 6, 5]}
    s = FakeSolution(quads, {"vonmises": {1: [1.0] * 4, 2: [2.0] * 4}})
    vals = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    replaced, stale = run(s, {"vonmises": vals})
    check("2D: quads with values are replaced", replaced == ["vonmises"] and
          s.env["vonmises"][2] == [1.5, 2.5, 5.5, 4.5], s.env)


def test_gaps():
    s = FakeSolution({1: [1, 2, 3, 4], 3: [3, 4, 5, 6]},
                     {"vonmises": {1: [1.0] * 4, 3: [1.0] * 4}})
    run(s, {"vonmises": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    check("element numbers with a gap: list per number, None between",
          s.env["vonmises"][3] == [3.0, 4.0, 5.0, 6.0] and 2 not in
          s.env["vonmises"])


def test_skips():
    island = dict(MIXED)
    island[5] = [13, 1, 2, 9]
    s = FakeSolution(island, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": CA + [7.0]})
    check("island node with a value: skipped, Mecway's own stay",
          replaced == [] and stale and "node 13" in stale[0][1] and
          s.env["vonmises"][1] == [99.0] * 8, stale)
    s = NoWrite(MIXED, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": list(CA), "stressxx": list(CA)})
    check("no set_element_node_variable: both named, nothing written",
          replaced == [] and sorted(n for n, _ in stale) ==
          ["stressxx", "vonmises"] and "36 or later" in stale[0][1], stale)
    s = FakeSolution(MIXED, OWN, DERIVED, steps=[1, 2])
    replaced, stale = run(s, {"vonmises": list(CA)})
    check("time steps: skipped with the reason", replaced == [] and
          stale and "time steps" in stale[0][1], stale)
    s = FakeSolution(MIXED, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": list(CA)}, section={40, 41})
    check("section view: skipped with the reason", replaced == [] and
          stale and "section view" in stale[0][1], stale)
    s = Failing(MIXED, OWN, DERIVED)
    replaced, stale = run(s, {"vonmises": list(CA)})
    check("a failing call: named, the run goes on", replaced == [] and
          stale == [("vonmises", "boom")], stale)
    s = NoRead(MIXED, OWN, DERIVED)
    check("no element_node_value: nothing, no message",
          run(s, {"vonmises": list(CA)}) == ([], []))
    s = FakeSolution(MIXED)
    check("no values per element node at all: nothing",
          run(s, {"vonmises": list(CA)}) == ([], []))


def run_in_ironpython():
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="element_node_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_element_node.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_bridge_element_node as t\n"
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
    tmp = tempfile.mkdtemp(prefix="element_node_")
    saved = bridge_utils.CONFIG_BRIDGE.get("work_dir", "")
    bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
    try:
        test_mixed()
        test_before_scan()
        test_2d()
        test_gaps()
        test_skips()
        with io.open(os.path.join(tmp, bridge_utils.log_file_name()),
                     encoding="utf-8") as f:
            text = f.read()
        check("log: INFO for a replacement, WARNING for a skip",
              u"INFO: Values per element node replaced" in text and
              u"WARNING: Mecway's own values per element node remain"
              in text)
    finally:
        bridge_utils.CONFIG_BRIDGE["work_dir"] = saved
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
