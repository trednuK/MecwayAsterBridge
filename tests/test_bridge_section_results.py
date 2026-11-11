# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 2.7 and 3, also IronPython via TestFiles/Tools/
# run_ipy.ps1) of bridge_results_liml.add_section_view: the shells of a section
# view with their values in the <solution> of a .liml, and of the table route
# (bridge_from_aster) with such a solution. The .liml files are generated here
# and read back with ElementTree, not with the code under test.
#
# bridge_results_liml works on binary strings as IronPython gives them: str
# with one character per byte. Under CPython LatinFile gives the same.
#
#   python tests/test_bridge_section_results.py
#   powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1
#       -Script tests/test_bridge_section_results.py

from __future__ import print_function

import array
import base64
import io
import json
import math
import os
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
TMP = tempfile.mkdtemp(prefix="section_results_")
bridge_utils.CONFIG_BRIDGE["work_dir"] = TMP      # in memory only
bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
import bridge_from_aster  # noqa: E402
import bridge_from_liml  # noqa: E402
import bridge_results_liml as brl  # noqa: E402
import bridge_section_view as sv  # noqa: E402
import bridge_hide_failed as bhf  # noqa: E402

STRESS = "longitudinalstress"
LOG = []
sv.log = LOG.append
bridge_from_aster.log = LOG.append
_builtin_open = open
PY3 = sys.version_info[0] >= 3


class LatinFile(object):
    """A binary file as IronPython has it, and the largest read."""
    largest = [0]

    def __init__(self, path, mode):
        self.f = _builtin_open(path, mode)
        self.text = "b" not in mode or not PY3

    def read(self, *size):
        data = self.f.read(*size)
        LatinFile.largest[0] = max(LatinFile.largest[0], len(data))
        return data if self.text else data.decode("latin-1")

    def write(self, data):
        self.f.write(data if self.text else data.encode("latin-1"))

    def seek(self, pos):
        self.f.seek(pos)

    def close(self):
        self.f.close()

    def __iter__(self):
        for line in self.f:
            yield line if self.text else line.decode("latin-1")


brl.open = LatinFile


def check(name, cond):
    print(("OK   " if cond else "FOUT ") + name)
    check.count += 1
    if not cond:
        check.failed = True


check.failed = False
check.count = 0


def close(a, b, tol=1e-12):
    return (len(a) == len(b) and
            all(abs(x - y) <= tol * (1.0 + abs(y)) for x, y in zip(a, b)))


# ==========================================
# GENERATED FILES
# ==========================================
HEAD = u"""<liml version="35">
  <analysis type="S30" />{conf}
  <node nid="1" x="0" y="0" z="0" />
  <node nid="2" x="1" y="0" z="0" />
  <node nid="3" x="2" y="0" z="0" />
  <node nid="4" x="0" y="1" z="0" />
  <node nid="5" x="1" y="1" z="0" />
  <node nid="6" x="1" y="2" z="0" />
  <node nid="7" x="0" y="2" z="0" />
  <elset name="Beam" colorrgb="DADADA" material="Sect">
    <elem eid="1" shape="line2" nodes="1 2" />
    <elem eid="2" shape="line2" nodes="2 3" />
  </elset>
  <elset name="Plaat" colorrgb="DADADA" material="Sheet">
    <elem eid="3" shape="quad4" nodes="4 5 6 7" />
  </elset>{mid}
  <mat name="Sect">
    <geometric type="UniformGeneralSection" area="0.0008 m\xb2" iyy="2.667e-08 m⁴" izz="1.067e-07 m⁴" torsionconstant="7.3e-08 m⁴" perimeter="0.12 m" />
    <mechanical type="Isotropic" youngsmodulus="210000000000 Pa" poissonratio="0.3" />{plastic}
  </mat>
  <mat name="Sheet">
    <geometric type="Plate" thickness="0.01 m" />
    <mechanical type="Isotropic" youngsmodulus="210000000000 Pa" poissonratio="0.3" />
  </mat>
  <nodeselection name="Clamp">
    <node nid="1" />
  </nodeselection>
  <fixed selection="Clamp" />
  <ccxmodeldefinition>** SECTIE-VORM Sect: N=4, A=0.0008
** SECTIE-VORM Sect: P=-0.02 -0.01 0.02 -0.01 0.02 0.01 -0.02 0.01</ccxmodeldefinition>
  <fieldvariable name="displacement" displayunit="m" expanded="true" />
"""
ALL_NODES = list(range(1, 8))
BEAM_NODES = [1, 2, 3]
NODE_VARS = {"displmag": ALL_NODES, "displx": ALL_NODES, "disply": ALL_NODES,
             "displz": ALL_NODES, "rotx": BEAM_NODES, "roty": BEAM_NODES,
             "rotz": BEAM_NODES, "reactionforcex": [1],
             "vonmises": [4, 5, 6, 7], "tensileforce": BEAM_NODES}
ELEMENT_VARS = {"tensileforce": [1, 2], "bendingmomv": [1, 2],
                "bendingmomw": [1, 2], "sheary": [2], "plate": [3]}
SLOTS = {1: 2, 2: 2, 3: 4}


def value(name, nid, step, k=0):
    """A number per variable, node or element, step and end. Rotations are
    small, so that the shells stay near the beams."""
    code = sum(ord(c) for c in name) % 97 + 1
    return (code * 1.25 + nid * 3.5 + step * 0.5 + k * 7.0) * 1.0e-3


def encode(data):
    text = base64.b64encode(data)
    if not isinstance(text, str):
        text = text.decode("ascii")
    lines = [text[i:i + 64] for i in range(0, len(text), 64)]
    return "\r\n".join(lines) + "\r\n"


def to_bytes(values, code):
    a = array.array(code, values)
    return a.tobytes() if hasattr(a, "tobytes") else a.tostring()


def block(kind, tag, name, comps, data, code, indent, aster):
    lines = [indent + '<{0} name="{1}">'.format(kind, name),
             indent + "  <maxandmin>"]
    for comp in comps:
        lines.append(indent + '    <component name="{0}" max="1" min="0" />'
                     .format(comp))
    lines.append(indent + "  </maxandmin>")
    text = "\r\n".join(lines) + "\r\n" + indent + "  <" + tag + ">" + \
        encode(to_bytes(data, code)) + "</" + tag + ">\r\n"
    if aster:
        text += "{0}  <nodes />\r\n{0}  <values />\r\n".format(indent)
    return text + indent + "</" + kind + ">\r\n"


def results(precision="double", steps=None, node_vars=None, element_vars=None,
            aster=False, monitor=False, kind="timestep", scale=1.0):
    """<results>: steps None is static, otherwise a list of step ids."""
    code = "d" if precision == "double" else "f"
    tag = "valuesdouble" if code == "d" else "valuessingle"
    node_vars = NODE_VARS if node_vars is None else node_vars
    element_vars = ELEMENT_VARS if element_vars is None else element_vars
    out = ['    <results precision="{0}">'.format(precision)]
    if monitor:
        out.append("\r\n      <savedmonitor>\r\n        <output>x &lt;nodeids"
                   " &gt;</output>\r\n      </savedmonitor>")
    out.append("\r\n")
    for name in sorted(node_vars):
        out.append('      <nodeids name="{0}">{1}</nodeids>\r\n'.format(
            name, encode(to_bytes(node_vars[name], "i"))))
    for name in sorted(element_vars):
        out.append('      <elementnodeids name="{0}">{1}</elementnodeids>\r\n'
                   .format(name, encode(to_bytes(element_vars[name], "i"))))
    for step in (steps if steps is not None else [None]):
        indent = "      " if step is None else "        "
        if step is not None:
            out.append('      <{0} id="{1}" {2}>\r\n'.format(
                kind, step, 'time="%g s"' % step if kind == "timestep"
                else 'frequency="%g Hz"' % step))
        s = step or 0
        for name in sorted(node_vars):
            comps = ["Beam"] if node_vars[name][0] <= 3 else []
            if node_vars[name][-1] > 3:
                comps.append("Plaat")
            data = [scale * value(name, n, s) for n in node_vars[name]]
            out.append(block("nodevariable", tag, name, comps, data, code,
                             indent, aster))
        for name in sorted(element_vars):
            comps = ["Beam"] if element_vars[name][0] <= 2 else ["Plaat"]
            data = [scale * value(name, e, s, k)
                    for e in element_vars[name] for k in range(SLOTS[e])]
            out.append(block("elementnodevariable", tag, name, comps, data,
                             code, indent, aster))
        if step is not None:
            out.append("      </{0}>\r\n".format(kind))
    out.append("    </results>\r\n")
    return "".join(out)


def copy_of(head):
    """The model copy as Mecway writes it (with CRLF, without the
    <fieldvariable>)."""
    lines = []
    for line in head.split("\n")[1:]:
        if line.strip() and "<fieldvariable" not in line:
            lines.append(("  " + line) if line.startswith("  ") else line)
    return "\r\n".join(lines) + "\r\n"


def make(name, text_results="", conf=u"", mid=u"", plastic=u"", head=None,
         solutions=None):
    """path of a new .liml; solutions: the text after the model instead of
    one <solution> with text_results."""
    head = HEAD.format(conf=conf, mid=mid, plastic=plastic) if head is None \
        else head
    if solutions is None:
        solutions = ("  <solution>\r\n" + copy_of(head.encode("latin-1", "ignore").decode("latin-1")) + text_results + "  </solution>\r\n")
    data = (head.replace(u"\n", u"\r\n") + solutions + u"</liml>\r\n"
            ).encode("utf-8")
    path = os.path.join(TMP, name)
    f = _builtin_open(path, "wb")
    try:
        f.write(data)
    finally:
        f.close()
    for suffix in (".bak", ".tmp"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    return path


def raw(path):
    f = _builtin_open(path, "rb")
    try:
        return f.read()
    finally:
        f.close()


def b(text):
    return text.encode("ascii") if PY3 else text


def untouched(path, before):
    """The file is as before, no .tmp and no .bak."""
    return (raw(path) == before and not os.path.exists(path + ".tmp") and
            not os.path.exists(path + ".bak"))


def view_of(path):
    del LOG[:]
    md = bridge_from_liml.extract_aster_data_from_liml(path)
    shapes = sv.current_shapes(
        sv.parse_shapes(md["aster_custom"]["section_shapes"]), md)
    return sv.build_view(md, shapes), md


# ==========================================
# READING BACK
# ==========================================
def decode(text, code):
    data = base64.b64decode("".join(text.split()))
    a = array.array(code)
    if hasattr(a, "frombytes"):
        a.frombytes(data)
    else:
        a.fromstring(data)
    return [float(v) for v in a] if code != "i" else [int(v) for v in a]


def solution_of(path, configuration=None):
    root = ET.parse(path).getroot()
    for sol in root.findall("solution"):
        if sol.get("configuration") == configuration:
            return sol
    return None


def read(path, configuration=None):
    """{"ids", "elids", "steps": [{"vars", "elvars": {name: (components,
    {id: value} or {id: [values]})}}]} of a solution."""
    sol = solution_of(path, configuration)
    res = sol.find("results")
    ids = dict((e.get("name"), decode(e.text, "i"))
               for e in res.findall("nodeids"))
    elids = dict((e.get("name"), decode(e.text, "i"))
                 for e in res.findall("elementnodeids"))
    counts = {}
    for elset in sol.findall("elset"):
        for e in elset.findall("elem"):
            counts[int(e.get("eid"))] = len(e.get("nodes").split())
    steps = res.findall("timestep") + res.findall("mode")
    out = []
    for step in steps or [res]:
        item = {"vars": {}, "elvars": {}, "id": step.get("id")}
        for e in step.findall("nodevariable"):
            name = e.get("name")
            single = e.find("valuessingle")
            vals = decode((e.find("valuesdouble") if single is None
                           else single).text, "d" if single is None else "f")
            comps = dict((c.get("name"), (float(c.get("max")),
                                          float(c.get("min"))))
                         for c in e.find("maxandmin"))
            item["vars"][name] = (comps, dict(zip(ids[name], vals)))
        for e in step.findall("elementnodevariable"):
            name = e.get("name")
            single = e.find("valuessingle")
            vals = decode((e.find("valuesdouble") if single is None
                           else single).text, "d" if single is None else "f")
            comps = dict((c.get("name"), (float(c.get("max")),
                                          float(c.get("min"))))
                         for c in e.find("maxandmin"))
            per = {}
            pos = 0
            for eid in elids[name]:
                per[eid] = vals[pos:pos + counts[eid]]
                pos += counts[eid]
            item["elvars"][name] = (comps, per) if pos == len(vals) \
                else (comps, None)
        out.append(item)
    return {"ids": ids, "elids": elids, "steps": out, "solution": sol}


def beam_dofs(step):
    d = dict((n, tuple(value(v, n, step) for v in ("displx", "disply",
                                                   "displz")))
             for n in BEAM_NODES)
    r = dict((n, tuple(value(v, n, step) for v in ("rotx", "roty", "rotz")))
             for n in BEAM_NODES)
    return d, r


def beam_forces(step):
    return dict((e, tuple(tuple(value(v, e, step, k) for v in (
        "tensileforce", "bendingmomv", "bendingmomw")) for k in (0, 1)))
        for e in (1, 2))


def end_node(view, nid):
    """(beam, end) of a shell node."""
    index, end, _v, _w = view["origin"][nid - view["nids"][0]]
    return view["beams"][index], end


# ==========================================
# STATIC, DOUBLE, FORCES PRESENT
# ==========================================
TEXT = results(node_vars=dict(NODE_VARS, stressptu=BEAM_NODES),
               element_vars=dict(ELEMENT_VARS, stressptu=[1, 2]))
path = make("static.liml", TEXT)
before = raw(path)
view, md = view_of(path)
check("view: two beams with a rectangle", view is not None and
      len(view["beams"]) == 2 and len(view["nids"]) == 24 and
      len(view["elements"]) == 10)
out = brl.add_section_view(path, view, md)
check("static: accepted, " + out["text"], out["ok"] is True and
      out["steps"] == 1)
check("static: routes", out["routes"] == {"forces": 2, "kinematics": 0})
check("static: a section view is not a file with hidden failed elements",
      not bhf.is_processed(path))
after = raw(path)
sol_at = before.index(b("<solution"))
check("static: model part byte-identical",
      after[:sol_at] == before[:sol_at] and before.count(b("Doorsnede")) == 0
      and after[:sol_at].count(b("Doorsnede")) == 0)
check("static: end of the file byte-identical",
      after.endswith(b("    </results>\r\n  </solution>\r\n</liml>\r\n")))
check("static: previous version in .bak, no .tmp",
      raw(path + ".bak") == before and not os.path.exists(path + ".tmp"))
data = read(path)
sol = data["solution"]
check("static: nodes and elset in the copy",
      len(sol.findall("node")) == 7 + 24 and
      [e.get("name") for e in sol.findall("elset")] ==
      ["Doorsnede", "Beam", "Plaat"])
check("static: all nodes before the first elset", [
    c.tag for c in sol].index("elset") == 1 + 31)
check("static: shell elset has no material",
      sol.find("elset").get("material") is None)
vars_ = data["steps"][0]["vars"]
d, r = beam_dofs(0)
expected = sv.shell_values(view, d, r, md, beam_forces(0))
check("static: expected values have the force route",
      expected["stress_routes"]["forces"] == 2)
for name in ("displx", "disply", "displz", "displmag"):
    check("static: " + name + " on the shells", close(
        [vars_[name][1][n] for n in view["nids"]], expected[name]))
    check("static: " + name + " on the model unchanged", close(
        [vars_[name][1][n] for n in ALL_NODES],
        [value(name, n, 0) for n in ALL_NODES], 0.0))
for name in ("rotx", "roty", "rotz"):
    check("static: " + name + " = rotation of the beam node", all(
        vars_[name][1][n] == value(name, end_node(view, n)[0]["nodes"][
            end_node(view, n)[1]], 0) for n in view["nids"]))
check("static: nodeids stay ascending", all(
    v == sorted(v) for v in data["ids"].values()))
check("static: stressptu node values are the section stress", close(
    [vars_["stressptu"][1][n] for n in view["nids"]],
    expected["sectionsigma"]))
check("static: new variable on shell nodes only", sorted(
    vars_[STRESS][1]) == view["nids"] and close(
        [vars_[STRESS][1][n] for n in view["nids"]],
        expected["sectionsigma"]))
check("static: Dutch name not used", "langsspanning" not in vars_)
comp = vars_["displx"][0]
check("static: maxandmin has a component for the shells", set(comp) ==
      set(["Doorsnede", "Beam", "Plaat"]) and
      comp["Doorsnede"][0] == float("%.15G" % max(expected["displx"])) and
      comp["Doorsnede"][1] == float("%.15G" % min(expected["displx"])))
check("static: other components unchanged", comp["Beam"] == (1.0, 0.0))
text = after.decode("latin-1")
at = text.index('name="displx">', text.index("<nodevariable"))
check("static: shell component first", text.index(
    'component name="Doorsnede"', at) < text.index('component name="Beam"',
                                                   at))
body = [ln for ln in text[text.index("<results"):].split("\r\n")
        if ln and "<" not in ln]
check("static: base64 lines of at most 64 characters",
      body and max(len(ln) for ln in body) <= 64)
evars = data["steps"][0]["elvars"]
for name in ("tensileforce", "bendingmomv", "bendingmomw", "sheary",
             "stressptu"):
    check("static: element ids of " + name, data["elids"][name] ==
          sorted(data["elids"][name]) and evars[name][1] is not None)
ok = True
for eid, _shape, nodes in view["elements"]:
    got = evars["tensileforce"][1][eid]
    want = []
    for nid in nodes:
        beam, end = end_node(view, nid)
        want.append(value("tensileforce", beam["eid"], 0, end))
    ok = ok and close(got, want, 0.0)
check("static: element values per end, in the node order of the shell", ok)
check("static: quads span both ends", any(
    len(set(evars["tensileforce"][1][e[0]])) == 2 for e in view["elements"]))
check("static: element stressptu is copied from the beam", all(
    close(evars["stressptu"][1][e[0]],
          [value("stressptu", end_node(view, n)[0]["eid"], 0,
                 end_node(view, n)[1]) for n in e[2]], 0.0)
    for e in view["elements"]))
ok = True
first = view["nids"][0]
for eid, _shape, nodes in view["elements"]:
    ok = ok and close(evars[STRESS][1][eid],
                      [expected["sectionsigma"][n - first] for n in nodes])
check("static: new variable as element-node values", ok and
      data["elids"][STRESS] == [e[0] for e in view["elements"]])
check("static: its components", set(evars[STRESS][0]) ==
      set(["Doorsnede"]) and set(vars_[STRESS][0]) ==
      set(["Doorsnede"]))
check("static: plate values unchanged", close(
    evars["plate"][1][3], [value("plate", 3, 0, k) for k in range(4)], 0.0)
    and sorted(evars["plate"][1]) == [3])

# None stays None
check("copy: a variable the beam has not: no shell values",
      sorted(vars_["vonmises"][1]) == [4, 5, 6, 7] and
      "vonmises" in out["not_on_shells"] and "plate" in out["not_on_shells"])
want = [n for n in view["nids"] if 1 in [end_node(view, n)[0]["nodes"][
    end_node(view, n)[1]]]]
check("copy: reaction only on the shells at that beam node",
      sorted(vars_["reactionforcex"][1]) == [1] + want and all(
          vars_["reactionforcex"][1][n] == value("reactionforcex", 1, 0)
          for n in want))
check("copy: node variable of an element type, same rule",
      sorted(vars_["tensileforce"][1]) == [1, 2, 3] + view["nids"])
want = [e[0] for e in view["elements"]
        if end_node(view, e[2][0])[0]["eid"] == 2]
check("copy: element variable only on the shells of that beam",
      data["elids"]["sheary"] == [2] + want and
      sorted(evars["sheary"][1]) == [2] + want)

# ==========================================
# REPLACING AN EARLIER CALL
# ==========================================
first_text = raw(path)
out2 = brl.add_section_view(path, view, md)
check("replace: accepted", out2["ok"])
check("replace: same file as after the first call", raw(path) == first_text)
check("replace: .bak with shells is reported", raw(path + ".bak") == first_text
      and "previous version" in out2["text"] and
      "previous version" not in out["text"])
bridge_utils.CONFIG_BRIDGE["language"] = "nl"
out2 = brl.add_section_view(path, view, md)
data2 = read(path)
check("replace: other language, one stress variable", out2["ok"] and
      "langsspanning" in data2["ids"] and
      "longitudinalstress" not in data2["ids"])
bridge_utils.CONFIG_BRIDGE["language"] = "en"
out2 = brl.add_section_view(path, view, md)
data2 = read(path)
check("replace: English name, the Dutch one gone", out2["ok"] and
      "longitudinalstress" in data2["ids"] and
      "langsspanning" not in data2["ids"] and
      "longitudinalstress" in data2["elids"] and
      "langsspanning" not in data2["elids"] and
      "langsspanning" not in data2["steps"][0]["vars"] and
      "langsspanning" not in data2["steps"][0]["elvars"])
bridge_utils.CONFIG_BRIDGE["language"] = "nl"
brl.add_section_view(path, view, md)
bridge_utils.CONFIG_BRIDGE["language"] = "en"
md_one = dict(md)
md_one["mesh_elements"] = [e for e in md["mesh_elements"] if e[0] != 2]
view_one = sv.build_view(md_one, sv.current_shapes(sv.parse_shapes(
    md["aster_custom"]["section_shapes"]), md))
out2 = brl.add_section_view(path, view_one, md_one)
data2 = read(path)
check("replace: fewer shells, the old ones are gone", out2["ok"] and
      sorted(data2["ids"]["displx"]) == ALL_NODES + view_one["nids"] and
      len(data2["solution"].findall("node")) == 7 + len(view_one["nids"]) and
      len(data2["solution"].findall("elset")) == 3)
check("replace: shell elements gone from the element ids",
      data2["elids"]["tensileforce"] == [1, 2] +
      [e[0] for e in view_one["elements"]])

# ==========================================
# PRECISION, TIME STEPS, ASTER FORMAT, MONITOR
# ==========================================
path = make("steps.liml", results(
    "single", [1, 2, 3], dict(NODE_VARS, stressptu=BEAM_NODES),
    aster=True, monitor=True))
view, md = view_of(path)
before = raw(path)
out = brl.add_section_view(path, view, md)
check("steps: accepted", out["ok"] and out["steps"] == 3)
data = read(path)
ok = True
for i, stepid in enumerate((1, 2, 3)):
    vars_ = data["steps"][i]["vars"]
    d, r = beam_dofs(stepid)
    d = dict((n, tuple(float(array.array("f", [c])[0]) for c in v))
             for n, v in d.items())
    r = dict((n, tuple(float(array.array("f", [c])[0]) for c in v))
             for n, v in r.items())
    forces = dict((e, tuple(tuple(float(array.array("f", [c])[0]) for c in q)
                            for q in v))
                  for e, v in beam_forces(stepid).items())
    want = sv.shell_values(view, d, r, md, forces)
    ok = ok and close([vars_["displz"][1][n] for n in view["nids"]],
                      want["displz"], 1e-6)
    ok = ok and close([vars_[STRESS][1][n] for n in view["nids"]],
                      want["sectionsigma"], 1e-6)
    ok = ok and data["steps"][i]["id"] == str(stepid)
check("steps: every step its own values, single precision", ok)
text = raw(path).decode("latin-1")
check("steps: no double tag", "valuesdouble" not in text)
check("steps: the tags of the Code-Aster format stay",
      text.count("<nodes />") == 3 * (len(NODE_VARS) + 1 + len(ELEMENT_VARS)))
check("steps: values in single precision are copied exactly", all(
    data["steps"][2]["vars"]["rotz"][1][n] ==
    float(array.array("f", [value("rotz", end_node(view, n)[0]["nodes"][
        end_node(view, n)[1]], 3)])[0]) for n in view["nids"]))
check("steps: monitor text stays", "x &lt;nodeids &gt;" in text and
      text.index("<savedmonitor>") < text.index("<nodeids"))
check("steps: a step per variable, both toggles", all(
    STRESS in s["vars"] and STRESS in s["elvars"]
    for s in data["steps"]))
first_text = raw(path)
check("steps: second call is stable",
      brl.add_section_view(path, view, md)["ok"] and raw(path) == first_text)

path = make("forces_off.liml", results(element_vars={}))
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
data = read(path)
d, r = beam_dofs(0)
want = sv.shell_values(view, d, r, md)
check("no forces: kinematic route", out["ok"] and
      out["routes"] == {"forces": 0, "kinematics": 2} and close(
          [data["steps"][0]["vars"][STRESS][1][n]
           for n in view["nids"]], want["sectionsigma"]))
check("no forces: stressptu absent, not created",
      "stressptu" not in data["ids"])
check("no forces: element ids of the new variable anyway",
      data["elids"].keys() == {STRESS: 0}.keys() and
      sorted(data["steps"][0]["elvars"]) == [STRESS])

# ==========================================
# OTHER SOLUTIONS
# ==========================================
CONF = u'\n  <configuration name="A" />\n  <configuration name="B" />'
head = HEAD.format(conf=CONF, mid=u"", plastic=u"")
bare = HEAD.format(conf=u"", mid=u"", plastic=u"")
sol_a = (u'  <solution configuration="A">\r\n' + copy_of(bare) +
         results(scale=2.0) + u"  </solution>\r\n")
sol_b = (u'  <solution configuration="B">\r\n' + copy_of(bare) + results() +
         u"  </solution>\r\n")
path = make("conf.liml", head=head, solutions=sol_a + sol_b)
view, md = view_of(path)
before = raw(path)
out = brl.add_section_view(path, view, md, "A")
after = raw(path)
at = before.index(b('<solution configuration="B">'))
check("configuration: accepted", out["ok"])
check("configuration: solution B and the model byte-identical",
      after.endswith(before[at:]) and
      after[:before.index(b("<solution"))] ==
      before[:before.index(b("<solution"))])
check("configuration: shells in A only",
      len(solution_of(path, "A").findall("node")) == 7 + 24 and
      len(solution_of(path, "B").findall("node")) == 7)
out = brl.add_section_view(path, view, md, "B")
check("configuration: B next, A keeps its shells", out["ok"] and
      len(solution_of(path, "A").findall("node")) == 7 + 24 and
      len(solution_of(path, "B").findall("node")) == 7 + 24)
path = make("conf2.liml", head=head, solutions=sol_a + sol_b)
bridge_utils.CONFIG_BRIDGE["configuration"] = "B"
out = brl.add_section_view(path, view, md)
bridge_utils.CONFIG_BRIDGE.pop("configuration")
check("configuration: None uses the choice of pick_configuration",
      out["ok"] and len(solution_of(path, "B").findall("node")) == 7 + 24 and
      len(solution_of(path, "A").findall("node")) == 7)
path = make("conf3.liml", head=head, solutions=sol_a)
before = raw(path)
out = brl.add_section_view(path, view, md, "Z")
check("configuration: a name without a solution refused",
      not out["ok"] and "configuration Z" in out["text"] and
      untouched(path, before))
stub = u'  <solution configuration="A" />\r\n' + sol_b
path = make("stub.liml", head=head, solutions=stub)
before = raw(path)
out = brl.add_section_view(path, view, md, "A")
check("configuration: stub solution refused", not out["ok"] and
      "no results" in out["text"] and untouched(path, before))
monitor_only = results(node_vars={}, element_vars={})
path = make("monitor_only.liml", monitor_only)
before = raw(path)
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
check("empty results refused", not out["ok"] and "no results" in out["text"]
      and untouched(path, before))

# ==========================================
# MODES
# ==========================================
path = make("modes.liml", results("double", [1, 2], dict(
    NODE_VARS, stressptu=BEAM_NODES), kind="mode"))
view, md = view_of(path)
before = raw(path)
del LOG[:]
out = brl.add_section_view(path, view, md)
data = read(path)
check("modes: accepted, no stress", out["ok"] and out["steps"] == 2 and
      STRESS not in data["ids"] and "no stress" in out["text"] and
      out["routes"] == {"forces": 0, "kinematics": 0})
d, r = beam_dofs(2)
want = sv.shell_values(view, d, r, md)
check("modes: displacement per mode", close(
    [data["steps"][1]["vars"]["disply"][1][n] for n in view["nids"]],
    want["disply"]))
check("modes: stressptu falls back on a copy", all(
    data["steps"][0]["vars"]["stressptu"][1][n] == value(
        "stressptu", end_node(view, n)[0]["nodes"][end_node(view, n)[1]], 1)
    for n in view["nids"]))

# ==========================================
# NO STRESS
# ==========================================
PLASTIC = u'\n    <plastic type="Isotropic" />'
path = make("plastic.liml", TEXT, plastic=PLASTIC)
view, md = view_of(path)
if md["materials"]["Sect"].get("plastic_type") is None:
    md["materials"]["Sect"]["plastic_type"] = "Isotropic"
out = brl.add_section_view(path, view, md)
data = read(path)
check("nonlinear material: no stress variable", out["ok"] and
      STRESS not in data["ids"] and
      "Nonlinear material" in out["text"])
path = make("no_e.liml", results(element_vars={}, node_vars=dict(
    NODE_VARS, stressptu=BEAM_NODES)))
view, md = view_of(path)
md2 = dict(md)
md2["materials"] = {"Sect": {}}
del LOG[:]
out = brl.add_section_view(path, view, md2)
data = read(path)
check("no E: displacement only, one warning", out["ok"] and
      STRESS not in data["ids"] and
      len([m for m in LOG if m.startswith("WARNING")]) == 1 and
      "missing" in out["text"])
check("no E: stressptu copied, so no black item",
      sorted(data["ids"]["stressptu"]) == [1, 2, 3] + view["nids"])
path = make("no_e_steps.liml", results(element_vars={}, steps=[1, 2, 3]))
del LOG[:]
out = brl.add_section_view(path, view, md2)
check("no E: one warning over the steps too", out["ok"] and
      len([m for m in LOG if m.startswith("WARNING")]) == 1)

# ==========================================
# REFUSALS
# ==========================================
no_rot = dict((k, v) for k, v in NODE_VARS.items()
              if not k.startswith("rot"))
path = make("no_rot.liml", results(node_vars=no_rot))
view, md = view_of(path)
before = raw(path)
out = brl.add_section_view(path, view, md)
check("no rotations: refused, nothing written", not out["ok"] and
      "rotation" in out["text"] and out["steps"] == 0 and
      untouched(path, before))
part = dict(NODE_VARS, rotx=[1, 2])
path = make("part_rot.liml", results(node_vars=part))
before = raw(path)
del LOG[:]
out = brl.add_section_view(path, view, md)
check("rotation missing on a beam end: refused", not out["ok"] and
      untouched(path, before))
path = make("no_sol.liml", solutions=u"")
before = raw(path)
out = brl.add_section_view(path, view, md)
check("no solution: refused", not out["ok"] and untouched(path, before))
out = brl.add_section_view(os.path.join(TMP, "nothing.liml"), view, md)
check("no file: refused", not out["ok"] and "not found" in out["text"])
path = make("no_view.liml", TEXT)
before = raw(path)
check("no view: refused", not brl.add_section_view(path, None, md)["ok"] and
      untouched(path, before))
CYCLIC = u'\n  <cyclicsymmetry axis="3" segments="4" />'
path = make("cyclic.liml", TEXT, mid=CYCLIC)
before = raw(path)
out = brl.add_section_view(path, view, md)
check("cyclic: refused", not out["ok"] and "Cyclic" in out["text"] and
      untouched(path, before))
head_moved = HEAD.format(conf=u"", mid=u"", plastic=u"")
solved = make("moved.liml", TEXT)
sol_part = raw(solved).decode("utf-8")
sol_part = sol_part[sol_part.index(u"  <solution>"):sol_part.index(u"</liml>")]
sol_part = sol_part.replace(u'<node nid="2" x="1"', u'<node nid="2" x="1.5"')
path = make("moved.liml", head=head_moved, solutions=sol_part)
before = raw(path)
out = brl.add_section_view(path, view, md)
check("mesh changed after the solve: refused", not out["ok"] and
      "changed after" in out["text"] and untouched(path, before))
sol_part = sol_part.replace(u'<node nid="2" x="1.5"', u'<node nid="2" x="1"')
sol_part = sol_part.replace(
    u'    <elset name="Beam"',
    u'    <node nid="99" x="0" y="0" z="0" />\r\n    <elset name="Beam"')
path = make("clash.liml", head=head_moved, solutions=sol_part)
before = raw(path)
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
check("a node in the solution where a shell comes: refused", not out["ok"] and
      untouched(path, before))
text = results("double", [1, 2])
at = text.rindex("</valuesdouble>")
text = text[:at - 40] + text[at - 24:]
path = make("broken.liml", text)
before = raw(path)
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
check("a broken last variable: refused, nothing written", not out["ok"] and
      untouched(path, before))

# ==========================================
# NAMES AND LINE ENDS
# ==========================================
OWN = u"""
  <elset name="Doorsnede" colorrgb="DADADA" material="Sheet">
    <elem eid="4" shape="quad4" nodes="4 5 6 7" />
  </elset>"""
path = make("own_name.liml", TEXT, mid=OWN)
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
first_text = raw(path)
out2 = brl.add_section_view(path, view, md)
names = [e.get("name") for e in solution_of(path).findall("elset")]
check("name: a component Doorsnede of the model stays", out["ok"] and
      out2["ok"] and raw(path) == first_text and
      names == ["Doorsnede_1", "Beam", "Plaat", "Doorsnede"])
check("name: components in maxandmin of the view elset",
      "Doorsnede_1" in read(path)["steps"][0]["vars"]["displx"][0])
path = make("lf.liml", TEXT)
view, md = view_of(path)
data_ = raw(path).replace(b(chr(13)), b(""))
f = _builtin_open(path, "wb")
f.write(data_)
f.close()
out = brl.add_section_view(path, view, md)
data = read(path)
check("LF file: accepted, values read back", out["ok"] and
      sorted(data["ids"]["displx"]) == ALL_NODES + view["nids"] and
      STRESS in data["steps"][0]["elvars"])
first_text = raw(path)
check("LF file: stable", brl.add_section_view(path, view, md)["ok"] and
      raw(path) == first_text)

# ==========================================
# THE REST OF bridge_results_liml WITH SHELLS IN THE FILE
# ==========================================
path = make("rest.liml", TEXT)
view, md = view_of(path)
model_only = raw(path)
model_only = model_only[:model_only.index(b("<solution"))]
fragment = os.path.join(TMP, "fragment.xml")
f = _builtin_open(fragment, "wb")
f.write(results(element_vars={}).encode("ascii"))
f.close()
fit_before = brl.check_results_fit(path, fragment)
brl.add_section_view(path, view, md)
check("has_results: still True", brl.has_results(path))
check("check_results_fit: same answer",
      brl.check_results_fit(path, fragment) == fit_before and fit_before[0])
check("model reader: same nodes with shells in the solution",
      view_of(path)[1]["mesh_nodes"] == md["mesh_nodes"])
ok, _msg = brl.splice_results(path, fragment, path)
check("splice_results: rebuilds the copy without shells", ok and
      b("Doorsnede") not in raw(path) and
      len(solution_of(path).findall("node")) == 7 and
      raw(path)[:len(model_only)] == model_only)
view, md = view_of(path)
brl.add_section_view(path, view, md)
ok, _msg = brl.strip_results(path)
check("strip_results: no solution, shells gone", ok and
      not brl.has_results(path) and b("<solution") not in raw(path) and
      raw(path).startswith(model_only.rstrip()))
path = make("read_step.liml", TEXT)
brl.add_section_view(path, view, md)
step = brl.read_step(path)
check("read_step: shell values in a list per node",
      len(step["displx"]) == 31 and step["displx"][30] is not None)


# ==========================================
# TABLE ROUTE
# ==========================================
class Point(object):
    def __init__(self, xyz):
        self.x, self.y, self.z = xyz


class FakeMw(object):
    def __init__(self, nodes):
        self.xyz = nodes

    def all_nodes(self):
        return sorted(self.xyz)

    def node(self, nid):
        return Point(self.xyz[nid])

    def set_solution_active(self):
        pass

    def display(self):
        pass


class FakeSolution(object):
    def __init__(self, nodes, shells=None, name="Doorsnede", old=None):
        self.xyz = nodes
        self.shells = shells
        self.name = name
        self.old = old or {}
        self.written = {}

    def all_nodes(self):
        return sorted(self.xyz)

    def node(self, nid):
        return Point(self.xyz[nid])

    def components(self):
        return ["Beam"] + ([self.name] if self.shells else [])

    def component_elements(self, name):
        return [100] if name == self.name else [1]

    def nodes(self, eid):
        return self.shells if eid == 100 else [1, 2]

    def node_value(self, name, nid, time_step=None):
        if name not in self.old:
            raise SystemError("Solution variable does not exist")
        return self.old[name].get(nid)

    def set_variable(self, name, values, time_step=None, mode=None):
        self.written[name] = list(values)


NODES = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0)}
WITH = dict(NODES)
WITH.update({3: (0.0, 0.1, 0.0), 4: (1.0, 0.1, 0.0)})
mw = FakeMw(NODES)
check("table: plain solution", bridge_from_aster.check_solution_mesh(
    mw, FakeSolution(NODES)) == (True, ""))
check("table: shells tolerated", bridge_from_aster.check_solution_mesh(
    mw, FakeSolution(WITH, [3, 4])) == (True, ""))
check("table: suffix of the elset name",
      bridge_from_aster.check_solution_mesh(
          mw, FakeSolution(WITH, [3, 4], "Doorsnede_1")) == (True, ""))
check("table: other extra nodes still a mismatch",
      not bridge_from_aster.check_solution_mesh(
          mw, FakeSolution(WITH))[0])
check("table: extra nodes in an other component still a mismatch",
      not bridge_from_aster.check_solution_mesh(
          mw, FakeSolution(WITH, [3, 4], "Doorsnede2"))[0])
check("table: only part of the extra nodes in the shells",
      not bridge_from_aster.check_solution_mesh(
          mw, FakeSolution(WITH, [3]))[0])
FEWER = {1: (0.0, 0.0, 0.0)}
check("table: too few nodes still a mismatch",
      not bridge_from_aster.check_solution_mesh(
          mw, FakeSolution(FEWER))[0])

RESU = ("INTITULE NOEUD DX DY DZ DRX DRY DRZ\n"
        "displacements 1 0.0 0.0 0.0 0.0 0.0 0.0\n"
        "displacements 2 1.0 2.0 2.0 0.1 0.2 0.3\n")
f = _builtin_open(os.path.join(TMP, "t.resu"), "w")
f.write(RESU)
f.close()
del LOG[:]
plain = FakeSolution(NODES)
check("table: plain run loads", bridge_from_aster.AsterToMecway_results(
    TMP, "t.resu", mw, plain))
check("table: plain run writes model values", plain.written["displx"] ==
      [0.0, 1.0] and plain.written["displmag"] == [0.0, 3.0] and
      not [m for m in LOG if "section view" in m])
OLD = {"displx": {3: 5.0, 4: 6.0}, "disply": {3: 7.0, 4: 8.0},
       "displz": {3: 9.0, 4: 1.5}, "displmag": {3: 11.0, 4: 12.0},
       "rotx": {3: 0.5, 4: 0.6}}
del LOG[:]
fake = FakeSolution(WITH, [3, 4], old=OLD)
check("table: run with shells loads", bridge_from_aster.AsterToMecway_results(
    TMP, "t.resu", mw, fake))
check("table: shell values stay", fake.written["displx"] ==
      [0.0, 1.0, 5.0, 6.0] and fake.written["displmag"] ==
      [0.0, 3.0, 11.0, 12.0] and fake.written["rotx"] == [0.0, 0.1, 0.5, 0.6])
check("table: no None over a value of a shell", all(
    v is not None for name in OLD for v in fake.written[name]))
check("table: variable without an old value: None, no error",
      fake.written["roty"] == [0.0, 0.2, None, None])
check("table: the user hears that the shells are old",
      len([m for m in LOG if "previous calculation" in m]) == 1)

# ==========================================
# A LARGE FILE IS NOT LOADED WHOLE
# ==========================================
N = 100000
names = ["extra{0}".format(i) for i in range(16)]
line = '<node nid="{0}" x="9" y="9" z="9" />'.format(N)
ids = encode(to_bytes(list(range(1, N + 1)), "i"))
vals = encode(to_bytes([0.5] * N, "d"))
parts = ['    <results precision="double">\r\n']
for name in ["displx", "disply", "displz", "rotx", "roty", "rotz"] + names:
    parts.append('      <nodeids name="{0}">{1}</nodeids>\r\n'.format(
        name, ids))
for step in (1, 2, 3, 4, 5):
    parts.append('      <timestep id="{0}" time="{0} s">\r\n'.format(step))
    for name in ["displx", "disply", "displz", "rotx", "roty", "rotz"] + names:
        parts.append('        <nodevariable name="{0}">\r\n          '
                     '<maxandmin>\r\n          </maxandmin>\r\n          '
                     '<valuesdouble>{1}</valuesdouble>\r\n        '
                     '</nodevariable>\r\n'.format(name, vals))
    parts.append("      </timestep>\r\n")
parts.append("    </results>\r\n")
path = make("large.liml", "".join(parts))
data_ = raw(path)
at = data_.index(b("    <results"))
tail = data_[at:]
head_part = data_[:at] + b("    " + line + "\r\n")
f = _builtin_open(path, "wb")
f.write(head_part + tail)
f.close()
size = os.path.getsize(path)
view, md = view_of(path)
md = dict(md)
nodes = dict(md["mesh_nodes"])
nodes[N] = (9.0, 9.0, 9.0)
md["mesh_nodes"] = nodes
view = sv.build_view(md, sv.current_shapes(sv.parse_shapes(
    md["aster_custom"]["section_shapes"]), md))
del data_, tail, head_part, parts
LatinFile.largest[0] = 0
start = time.time()
out = brl.add_section_view(path, view, md)
spent = time.time() - start
check("large: accepted", out["ok"] and out["steps"] == 5)
print("large: {0:.1f} MB in {1:.2f} s, largest read {2:.1f} MB".format(
    size / 1.0e6, spent, LatinFile.largest[0] / 1.0e6))
check("large: no read of more than a block",
      LatinFile.largest[0] <= brl._CHUNK and size > 5 * brl._CHUNK)
check("large: nothing left behind", not os.path.exists(path + ".tmp"))
got = brl.read_step(path, 3, N + 24)
check("large: step 3 reads back", got["extra3"][N - 1] == 0.5 and
      got["extra3"][N] is not None and got["rotx"][N] == 0.5)

# --- the beams on a thin bar in the copy, the model part as it was ----------
path = make("thin.liml", results())
view, md = view_of(path)
head_before = raw(path).split(b("<solution"))[0]
out = brl.add_section_view(path, view, md)
sol = solution_of(path)
mats = dict((m.get("name"), m) for m in sol.findall("mat"))
thin = "Sect" + sv.THIN_SUFFIX
beam = [e for e in sol.findall("elset") if e.get("name") == "Beam"][0]
check("thin: the copy has the bar, sized from the outline",
      out["ok"] and mats[thin].find("geometric").get("type") == "RectBar" and
      mats[thin].find("geometric").get("recta") == "0.0012 m" and
      "Sect" in mats and beam.get("material") == thin)
check("thin: the model part is byte-identical",
      raw(path).split(b("<solution"))[0] == head_before)
out = brl.add_section_view(path, view, md)
sol = solution_of(path)
check("thin: a second call does not stack",
      out["ok"] and len([m for m in sol.findall("mat")
                         if m.get("name") == thin]) == 1)

# ==========================================
# SHEAR AND VON MISES FROM THE TABLE OF THE JOB
# ==========================================
FORCES = ("tensileforce", "bendingmomv", "bendingmomw", "sheary", "shearz",
          "torsion")
ALL_FORCES = dict(ELEMENT_VARS, sheary=[1, 2], shearz=[1, 2], torsion=[1, 2])
SHEAR, VM = "sectionshear", "sectionvonmises"


def table_file(view, name, entry=None, version=1, unit=None):
    """A _section.json as bridge_section_stress writes it, with one row per
    point of the view; the unit values follow from the place on the section."""
    rows = {}
    for _i, _e, v, w in view["origin"]:
        rows[(v, w)] = [v, w, 1.0 + v, 2.0 + w, 3.0, 4.0 + v, 5.0 + w, 6.0]
    data = {"material": "Sect", "loops": [[list(p) for p in
                                           view["shapes"]["Sect"]["loops"][0]]],
            "nu": 0.3, "A": 0.0008, "IY": 2.667e-08, "IZ": 1.067e-07,
            "EY": 0.002, "EZ": -0.001, "points": list(rows.values())}
    data.update(entry or {})
    if unit:
        data["points"] = unit(data["points"])
    path = os.path.join(TMP, name)
    f = _builtin_open(path, "w")
    try:
        f.write(json.dumps({"version": version, "warnings": ["WARNING: one"],
                            "sections": [data]}))
    finally:
        f.close()
    return path


def expected_shear(view, step):
    out = {}
    for nid, (index, end, v, w) in zip(view["nids"], view["origin"]):
        eid = view["beams"][index]["eid"]
        vv = value("sheary", eid, step, end)
        vw = value("shearz", eid, step, end)
        ts = (value("torsion", eid, step, end) + 0.002 * vw + 0.001 * vv)
        out[nid] = math.hypot(vv * (1.0 + v) + vw * 3.0 + ts * (5.0 + w),
                              vv * (2.0 + w) + vw * (4.0 + v) + ts * 6.0)
    return out


def clear_tables():
    for name in os.listdir(TMP):
        if name.endswith("_section.json"):
            os.remove(os.path.join(TMP, name))


path = make("tau.liml", results(element_vars=ALL_FORCES))
view, md = view_of(path)
table_file(view, "tau_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
data = read(path)
vars_ = data["steps"][0]["vars"]
check("table: accepted and named, " + out["text"],
      out["ok"] and SHEAR in out["text"] and VM in out["text"])
check("table: both variables on every shell node",
      list(data["ids"][SHEAR]) == view["nids"] and
      list(data["ids"][VM]) == view["nids"])
want = expected_shear(view, 0)
check("table: tau = |Vv a + Vw b + T_S c| of the end of that node", close(
    [vars_[SHEAR][1][n] for n in view["nids"]],
    [want[n] for n in view["nids"]]))
sigma = vars_[STRESS][1]
check("table: von Mises from sigma and tau", close(
    [vars_[VM][1][n] for n in view["nids"]],
    [math.sqrt(sigma[n] ** 2 + 3.0 * want[n] ** 2) for n in view["nids"]]))
elems = data["steps"][0]["elvars"][VM][1]
shell = [e for e in view["elements"]]
check("table: element values follow the nodes of each shell", all(
    close(list(elems[e[0]]), [vars_[VM][1][n] for n in e[2]]) for e in shell))
check("table: maxandmin of the shells", abs(
    vars_[SHEAR][0][view["elset"]][0] - max(want.values())) <=
    1e-9 * max(want.values()))
out = brl.add_section_view(path, view, md)
data2 = read(path)
check("table: a second call replaces them", out["ok"] and
      len([e for e in data2["solution"].find("results").findall("nodeids")
           if e.get("name") == SHEAR]) == 1 and
      close([data2["steps"][0]["vars"][SHEAR][1][n] for n in view["nids"]],
            [want[n] for n in view["nids"]]))

# --- time steps ---------------------------------------------------------
path = make("tau2.liml", results(steps=[1, 2], element_vars=ALL_FORCES))
view, md = view_of(path)
table_file(view, "tau2_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
data = read(path)
check("table: every step its own forces", out["ok"] and all(
    close([data["steps"][k]["vars"][SHEAR][1][n] for n in view["nids"]],
          [expected_shear(view, k + 1)[n] for n in view["nids"]])
    for k in (0, 1)))
clear_tables()

# --- which table --------------------------------------------------------
path = make("pick.liml", results(element_vars=ALL_FORCES))
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
check("no table: the rest stands and the text says why", out["ok"] and
      SHEAR not in read(path)["ids"] and STRESS in read(path)["ids"] and
      "_section.json" in out["text"])
table_file(view, "pick_20260101_120000_section.json", {"IY": 3.0e-08})
out = brl.add_section_view(path, view, md)
check("a table of another IY is not used", SHEAR not in read(path)["ids"])
table_file(view, "pick_20260101_120001_section.json", {"nu": 0.25})
out = brl.add_section_view(path, view, md)
check("nor of another nu", SHEAR not in read(path)["ids"])
table_file(view, "pick_20260101_120002_section.json", {"EZ": 0.004})
out = brl.add_section_view(path, view, md)
check("without #ASTER-SECTIE in the model EY and EZ are not compared",
      SHEAR in read(path)["ids"])
entry = {"nu": 0.3, "A": 0.0008, "IY": 2.667e-08, "IZ": 1.067e-07, "EY": 0.002,
         "EZ": -0.001, "loops": view["shapes"]["Sect"]["loops"]}
stated = dict(md)
geom = dict(md["mat_geometrics"]["Sect"])
geom["cara"] = tuple(geom["cara"]) + ("EY", "EZ")
geom["vale"] = tuple(geom["vale"]) + (0.002, -0.001)
stated["mat_geometrics"] = {"Sect": geom}
check("with it they count: the same", sv.match_table(
    entry, view["shapes"]["Sect"], stated, "Sect"))
check("with it they count: another EZ", not sv.match_table(
    dict(entry, EZ=0.004), view["shapes"]["Sect"], stated, "Sect"))
loop = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
clear_tables()
table_file(view, "pick_20260101_120003_section.json", {"loops": [loop]})
out = brl.add_section_view(path, view, md)
check("nor of another outline", SHEAR not in read(path)["ids"])
table_file(view, "pick_20260101_120004_section.json", version=2)
del LOG[:]
keep_log = brl.log
brl.log = LOG.append
try:
    out = brl.add_section_view(path, view, md)
    check("nor of an unknown version", SHEAR not in read(path)["ids"])
    check("an unknown version is logged once, with both versions",
          len([m for m in LOG if m.startswith("WARNING") and
               "version 2" in m and "version 1" in m]) == 1)
    del LOG[:]
    out = brl.add_section_view(path, view, md)
    check("... and not again on the next view",
          not [m for m in LOG if "version 2" in m])
finally:
    brl.log = keep_log
bad = os.path.join(TMP, "pick_20260101_120005_section.json")
f = _builtin_open(bad, "w")
f.write("{not json")
f.close()
out = brl.add_section_view(path, view, md)
check("a broken file is passed over", out["ok"])
for number, damage in enumerate(({"nu": "0.3"}, {"loops": None}, {"EY": None},
                                 {"points": None}, {"points": [[0.0, 1.0]]},
                                 {"points": [["a"] * 8]})):
    table_file(view, "pick_20260101_12001%d_section.json" % number, damage)
    out = brl.add_section_view(path, view, md)
    check("a damaged entry costs the two shear variables only (%d)" % number,
          out["ok"] and SHEAR not in read(path)["ids"] and
          STRESS in read(path)["ids"])
f = _builtin_open(bad, "w")
f.write(json.dumps({"version": 1, "sections": ["no entry", None]}))
f.close()
out = brl.add_section_view(path, view, md)
check("so does a list of something else", out["ok"])
table_file(view, "pick_20260101_120006_section.json")
out = brl.add_section_view(path, view, md)
check("an older, matching run still counts behind the bad ones",
      SHEAR in read(path)["ids"])
clear_tables()
table_file(view, "other_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
check("a file of another model is not looked at",
      SHEAR not in read(path)["ids"])
clear_tables()

# --- only some beams ----------------------------------------------------
path = make("part.liml", results(element_vars=dict(
    ELEMENT_VARS, sheary=[1], shearz=[1, 2], torsion=[1, 2])))
view, md = view_of(path)
table_file(view, "part_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
data = read(path)
first = [n for n, o in zip(view["nids"], view["origin"]) if o[0] == 0]
own = set(e[0] for e in view["parts"][0]["elements"])
check("forces on one beam: only its shells, and the text says so",
      out["ok"] and list(data["ids"][SHEAR]) == first and
      list(data["elids"][SHEAR]) == sorted(own) and "nodes" in out["text"])
check("the longitudinal stress stays on all shells",
      list(data["ids"][STRESS]) == view["nids"])
want = expected_shear(view, 0)
check("and the values are of the right shells", close(
    [data["steps"][0]["vars"][SHEAR][1][n] for n in first],
    [want[n] for n in first]))
clear_tables()

path = make("later.liml", results(element_vars=ALL_FORCES, steps=[1, 2]))
text = raw(path)
at = text.rindex(b('<elementnodevariable name="torsion"'))
stop = text.index(b("</elementnodevariable>"), at)
f = _builtin_open(path, "wb")
f.write(text[:at] + b('<!-- -->') + text[stop + len("</elementnodevariable>"):])
f.close()
view, md = view_of(path)
table_file(view, "later_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
check("a later step without a force: the shells stay, without the two",
      out["ok"] and SHEAR not in read(path)["ids"] and
      STRESS in read(path)["ids"])
clear_tables()

path = make("noforce.liml", results())
view, md = view_of(path)
table_file(view, "noforce_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
check("no shear forces: a table alone gives nothing, the text names the "
      "field", out["ok"] and SHEAR not in read(path)["ids"] and
      "beam_forces" in out["text"])
clear_tables()

# --- corner zone --------------------------------------------------------


def two_exits(rows):
    return [r + [10.0 * x for x in r[2:]] for r in rows]


path = make("zone.liml", results(element_vars=ALL_FORCES))
view, md = view_of(path)
table_file(view, "zone_20260101_120000_section.json", unit=two_exits)
out = brl.add_section_view(path, view, md)
data = read(path)
want = expected_shear(view, 0)
check("two exits of a corner zone: the larger of the two", out["ok"] and close(
    [data["steps"][0]["vars"][SHEAR][1][n] for n in view["nids"]],
    [10.0 * want[n] for n in view["nids"]]))
clear_tables()

# --- no shear where the stress does not hold ----------------------------
path = make("modes2.liml", results("double", [1, 2], element_vars=ALL_FORCES,
                                   kind="mode"))
view, md = view_of(path)
table_file(view, "modes2_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
check("modes: no shear", out["ok"] and SHEAR not in read(path)["ids"])
clear_tables()
path = make("plast2.liml", results(element_vars=ALL_FORCES), plastic=(
    u'\n    <plastic type="Isotropic"><hardeningcurve strain="0" '
    u'stress="235 MPa" /><hardeningcurve strain="0.1" stress="300 MPa" />'
    u'</plastic>'))
view, md = view_of(path)
table_file(view, "plast2_20260101_120000_section.json")
out = brl.add_section_view(path, view, md)
check("plastic: no shear", out["ok"] and SHEAR not in read(path)["ids"])
clear_tables()

# --- the warnings of the job reach the log of the run -------------------
path = make("notes.liml", results())
view, md = view_of(path)
fragment = os.path.join(TMP, "notes_20260101_120000_results.xml")
f = _builtin_open(fragment, "w")
f.write(results())
f.close()
table_file(view, "notes_20260101_120000_section.json")
del LOG[:]
keep_log = brl.log
brl.log = LOG.append
ok, _why = brl.splice_results(path, fragment, path)
brl.log = keep_log
check("splice_results logs the warnings of the sidecar",
      ok and "WARNING: one" in LOG)
clear_tables()


def splice_log(name, version=None, text=None):
    """The log of splice_results with a sidecar of this version, or with
    this text in it."""
    fragment = os.path.join(TMP, name + "_results.xml")
    f = _builtin_open(fragment, "w")
    f.write(results())
    f.close()
    if text is None:
        table_file(view, name + "_section.json", version=version)
    else:
        f = _builtin_open(os.path.join(TMP, name + "_section.json"), "w")
        f.write(text)
        f.close()
    del LOG[:]
    keep = brl.log
    brl.log = LOG.append
    try:
        good, _why = brl.splice_results(path, fragment, path)
    finally:
        brl.log = keep
    clear_tables()
    return good, list(LOG)


ok, got = splice_log("notes_20260101_120001", version=2)
check("sidecar of an unknown version: one WARNING with the versions, and "
      "its warnings still reach the log", ok and len(
          [m for m in got if m.startswith("WARNING") and "version 2" in m and
           "version 1" in m]) == 1 and "WARNING: one" in got)
ok, got = splice_log("notes_20260101_120002", text="{not json")
check("sidecar that cannot be read: one WARNING that its warnings are lost",
      ok and len([m for m in got if m.startswith("WARNING")]) == 1)
ok, got = splice_log("notes_20260101_120003", version=1)
check("sidecar of version 1: only its own warnings",
      ok and got == ["WARNING: one"])
ok, got = splice_log("notes_20260101_120004", text=json.dumps(
    {"version": 3, "warnings": [{"en": "x"}, "WARNING: two", None]}))
check("another version with other items: only the texts are logged",
      ok and "WARNING: two" in got and len(got) == 2)
try:
    import bridge_section_stress
except ImportError:         # no numpy: the writer cannot be compared
    bridge_section_stress = None
if bridge_section_stress is not None:
    check("the version read is the version the job writes",
          brl.SECTION_FORMAT == bridge_section_stress.FORMAT_VERSION)


# ==========================================
# HIDE FAILED ELEMENTS (bridge_hide_failed) AFTER A SECTION VIEW
# ==========================================
# The run order: the section view first, then hiding. Beam 2 fails at step
# 2 (element variable failed, contract failed/1); its shells copy the flag.
_value = value


def value(name, nid, step, k=0):
    if name == "failed":
        return 1.0 if nid == 2 and step >= 2 else 0.0
    return _value(name, nid, step, k)


path = make("hide.liml", results(steps=[1, 2, 3], aster=True,
                                 element_vars=dict(ELEMENT_VARS,
                                                   failed=[1, 2, 3])))
view, md = view_of(path)
out = brl.add_section_view(path, view, md)
check("hide: section view added to the time steps", out["ok"] is True and
      out["steps"] == 3)
check("hide: the section view alone is not processed",
      not bhf.is_processed(path))
del LOG[:]
keep_log = bhf.log
bhf.log = LOG.append
try:
    status, text = bhf.apply(path, expected=set(["2"]))
finally:
    bhf.log = keep_log
check("hide: the core accepts a solution with shells",
      status == "done" and
      text.startswith(u"1 failed element(s) hidden") and
      u"section view of those beams is hidden with them" in text and
      u"stay visible" not in text)
check("hide: the log counts the shells separately", [
    m for m in LOG if u"1 element(s) hidden in" in m and
    u"{0} section-view shell(s)".format(
        len(view["parts"][1]["elements"])) in m])
bhf.finish(path)
check("hide: processed (marker)", bhf.is_processed(path))
processed = raw(path)
# the core's marker counts the shells too (they copy the 'failed' of their
# beam): the 'already hidden' warning then names no count
check("hide: the marker counts the beam and its shells",
      bhf.liml_failed.processed_marker(path) == u"{0}".format(
          1 + len(view["parts"][1]["elements"])))
keep_log = bhf.log
bhf.log = LOG.append
try:
    status, text = bhf.apply(path)
finally:
    bhf.log = keep_log
check("hide: again: the 'already hidden' warning, without the count of "
      "beam and shells", status == "warning" and
      u"already have the failed elements hidden (marker failed_hidden)"
      in text and raw(path) == processed)
# the marker line gone (as a save in Mecway 35 drops the attribute of core
# 1.0.0): the node copies remain
start = processed.find(b('<globalvariable name="failed_hidden">'))
start = processed.rfind(b("\n"), 0, start) + 1
stripped = os.path.join(TMP, "hide_stripped.liml")
f = _builtin_open(stripped, "wb")
try:
    f.write(processed[:start] +
            processed[processed.find(b("\n"), start) + 1:])
finally:
    f.close()
check("hide: marker removed in the copy",
      bhf.liml_failed.processed_marker(stripped) is None and
      b("failed_hidden") not in raw(stripped))
check("hide: still processed by the node copies of model elements",
      bhf.is_processed(stripped))
before = raw(stripped)
view2, md2 = view_of(stripped)
out = brl.add_section_view(stripped, view2, md2)
check("hide: Section in results on it is refused anyway (backstop), the "
      "file unchanged", out["ok"] is False and raw(stripped) == before)

shutil.rmtree(TMP, ignore_errors=True)

print("{0} checks".format(check.count))
if check.failed:
    print("FOUT: test_bridge_section_results")
    sys.exit(1)
print("Alle controles OK")
