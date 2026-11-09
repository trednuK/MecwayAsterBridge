# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline tests of bridge_to_aster (Python 3; the locale part also under
# Mecway's IronPython 2.7.9), without Mecway and Code-Aster:
#   - no locale-dependent number formatting reaches a .comm (a numeric
#     format spec in str.format follows the Windows locale in IronPython:
#     "{0:.15g}".format(0.5) == "0,5" under nl-NL);
#   - line pressure on trusses (BARRE) on the merge route of
#     _prepare_beam_loads (overlapping and time-dependent line pressures);
#   - hydrostatic pressure stays a fixed load next to a uniform follower
#     pressure on the same selection (_render_charges);
#   - the bridge's own nodes (flexible joint, element offset, pre-tension
#     copy) get the temperature of their Mecway node
#     (_build_temperature_field, _bridge_node_temps in the job);
#   - support decisions of modal and buckling (_support_state,
#     _prestress_plan, MO-10 with gravity).
# The Code-Aster runs: TestFiles/Verificatie.
#
#   python tests/test_bridge_to_aster.py
#   powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1
#       -Script tests/test_bridge_to_aster.py      (locale part only)

from __future__ import print_function

import ast
import copy
import io
import os
import re
import shutil
import sys
import tempfile
from collections import OrderedDict

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_SCRIPTS = os.path.join(_HERE, "..", "Scripts")
sys.path.insert(0, _SCRIPTS)
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
_CONFIG = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_to_aster as b2a  # noqa: E402
b2a.log = _log

IRONPYTHON = sys.platform == "cli"
FAILS = []


def check(cond, text):
    print("{0:4s} {1}".format("OK" if cond else "FAIL", text))
    if not cond:
        FAILS.append(text)


# ------------------------------------------------------------------
# 1. Locale
# ------------------------------------------------------------------
_SPEC = re.compile(r"\{[^{}]*:[^{}]*[eEfFgGn%]\}")


def _strings(node):
    """Literal text of a string node, of a concatenation, or of the
    arguments of tr(nl, en); None otherwise."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _strings(node.left), _strings(node.right)
        if a is not None and b is not None:
            return a + b
        return a or b
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "tr"):
        out = []
        for arg in node.args:
            out += _strings(arg) or []
        return out
    return None


def _inside_log(node):
    while node is not None:
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "log"):
            return True
        node = getattr(node, "_parent", None)
    return False


def test_no_locale_format_into_comm():
    """Every str.format with a numeric format spec in bridge_to_aster.py
    is a log line (log(...)); anything else may reach the .comm."""
    if IRONPYTHON:
        return
    path = os.path.join(_SCRIPTS, "bridge_to_aster.py")
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._parent = parent
    bad = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                node.func.attr == "format"):
            continue
        texts = _strings(node.func.value) or []
        if any(_SPEC.search(t.replace("{{", "").replace("}}", ""))
               for t in texts) and not _inside_log(node):
            bad.append(node.lineno)
    check(not bad, "locale: no numeric format spec outside log() "
          "(lines {0})".format(bad))


def test_coef_mult_locale():
    """COEF_MULT of the bridge's own bonded relations (_render_mpcs)
    with a decimal point; under IronPython with the nl-NL culture."""
    md = {"constraint_equations": [],
          "bonded": [{"relations": [((1, 2, 3), ("DX", "DX", "DX"),
                                     (1.0, -0.5, -0.25))]}]}
    culture = None
    if IRONPYTHON:
        import clr  # noqa: F401
        from System.Threading import Thread
        from System.Globalization import CultureInfo
        culture = Thread.CurrentThread.CurrentCulture
        Thread.CurrentThread.CurrentCulture = CultureInfo("nl-NL")
    try:
        if IRONPYTHON:
            # the trap itself, and the formatting the bridge relies on
            check("{0:.15g}".format(0.5) == "0,5",
                  "locale: IronPython format spec follows nl-NL "
                  "(precondition of this test)")
            check("%.15g" % 0.5 == "0.5" and repr(0.5) == "0.5" and
                  "{0!r}".format(0.5) == "0.5" and
                  "{0}".format(0.5) == "0.5",
                  "locale: %-formatting, repr and {0} stay invariant")
        out = b2a._render_mpcs(md)
    finally:
        if culture is not None:
            Thread.CurrentThread.CurrentCulture = culture
    entry = out["LIAISON_DDL"][0]
    check("COEF_MULT=(1, -0.5, -0.25,)" in entry,
          "locale: COEF_MULT with decimal points: " + entry)


# ------------------------------------------------------------------
# 2. Line pressure on trusses (_prepare_beam_loads)
# ------------------------------------------------------------------
def _truss_model(bcs):
    return {
        "elset_modelisations": OrderedDict([("BEAMS", "POU_D_E"),
                                            ("TRUSS", "BARRE")]),
        "mesh_elements": [(1, "line2", [1, 2], "BEAMS"),
                          (2, "line2", [2, 3], "BEAMS"),
                          (3, "line2", [3, 4], "TRUSS")],
        "element_selections": {"ALL": [1, 2, 3], "B": [1, 2]},
        "materials": {"M": {"rho": 1000.0}},
        "elsets": {"BEAMS": "M", "TRUSS": "M"},
        "beam_sections": {"BEAMS": {"area": 0.01},
                          "TRUSS": {"area": 0.02, "truss": True}},
        "bcs": bcs}


def _lp(sel, fz):
    return {"type": "linepressure", "selection": sel,
            "aster_keyword": "FORCE_POUTRE", "aster_target": "GROUP_MA",
            "params": {}, "aster_dict": OrderedDict([("FZ", fz)])}


def _brlp(md):
    """{cell: FZ} of the BRLP groups."""
    out = {}
    for bc in md["bcs"]:
        if (bc["selection"] or "").startswith("BRLP") and bc["aster_dict"]:
            for c in md["extra_ma_groups"][bc["selection"]]:
                out[c] = bc["aster_dict"]["FZ"]
    return out


def test_truss_line_pressure_overlap():
    md = _truss_model([_lp("ALL", -1.0), _lp("B", -10.0)])
    b2a._prepare_beam_loads(md, "MECA_STATIQUE")
    fz = _brlp(md)
    check(fz.get(1) == -11.0 and fz.get(2) == -11.0,
          "truss: beams get the sum of the overlap ({0})".format(fz))
    check(fz.get(3) == -1.0,
          "truss: the truss keeps its line pressure ({0})".format(fz))


def test_truss_line_pressure_timed_gravity():
    hist = [(0.0, 0.0), (1.0, -1.0)]
    grav = {"type": "gravity", "selection": None,
            "aster_keyword": "PESANTEUR", "params": {},
            "aster_dict": {"GRAVITE": 10.0, "DIRECTION": [0.0, 0.0, -1.0]}}
    md = _truss_model([_lp("ALL", hist), grav])
    del LOG[:]
    b2a._prepare_beam_loads(md, "STAT_NON_LINE")
    fz = _brlp(md)
    # truss: line pressure + rho A g = -1000 * 0.02 * 10 = -200 N/m
    t3 = fz.get(3)
    check(isinstance(t3, list) and abs(t3[-1][1] - (-1.0 - 200.0)) < 1e-9,
          "truss: time-dependent line pressure + rho A g ({0})".format(t3))
    check(not any("TRUSS" in s for s in md.get("skipped_loads", [])),
          "truss: gravity on the truss not skipped ({0})".format(
              md.get("skipped_loads")))


# ------------------------------------------------------------------
# 3. Hydrostatic pressure stays fixed (_render_charges)
# ------------------------------------------------------------------
def test_hydrostatic_not_follower():
    charges = [
        ("AFFE_CHAR_MECA", OrderedDict([("PRES_REP", [
            "_F(GROUP_MA='P', PRES=1000.0)"])]), None),
        ("AFFE_CHAR_MECA_F", OrderedDict([("PRES_REP", [
            "_F(GROUP_MA='P', PRES=FHYD1)"])]), None),
        ("AFFE_CHAR_MECA_F", OrderedDict([("PRES_REP", [
            "_F(GROUP_MA='P', PRES=FPOS1)"])]), None),
        ("AFFE_CHAR_MECA_F", OrderedDict([("PRES_REP", [
            "_F(GROUP_MA='P', PRES=FN_P_PRES)"])]), None)]
    md = {"_follower_groups": set(["P"]), "aster_custom": {}}
    _block, clause = b2a._render_charges(charges, md)
    suiv = dict((m.group(1), "SUIV" in m.group(0)) for m in re.finditer(
        r"_F\(CHARGE=(load_\d+)[^)]*\)", clause))
    check(suiv == {"load_1": True, "load_2": False, "load_3": False,
                   "load_4": True},
          "follower: uniform and time table SUIV, hydrostatic and x,y,z "
          "formula fixed ({0})".format(suiv))


# ------------------------------------------------------------------
# 4. Temperatures of the bridge's own nodes
# ------------------------------------------------------------------
def _temp_model(value):
    """Mecway nodes 1..4; own nodes: 5 = joint at node 1, 6 = offset node
    of node 2, 7 = pre-tension copy of node 3, 8 = its reference node.
    Node temperature 500 K on node 1, a Temperature on node selection NS
    (nodes 2, 3)."""
    return {
        "thermal_stress": {"tref": 293.15},
        "temperatures": [{"selection": "NS", "target": "GROUP_NO",
                          "value": value}],
        "node_temperatures": {1: 500.0},
        "node_groups": {"NS": ["N2", "N3"]},
        "mesh_nodes": OrderedDict((n, (float(n), 0.0, 0.0))
                                  for n in range(1, 5)),
        "joint_nodes": {5: 1},
        "offset_links": [{"new": 6, "orig": 2}],
        "offset_new_nids": [6],
        "constraint_equations": [
            {"source": "pretension",
             "terms": [(3, "DX", 1.0), (7, "DX", -1.0), (8, "DX", 1.0)]},
            {"source": "pretension", "terms": [(8, "DY", 1.0)]}],
        "pretension_sections": [{"pairs": 1, "ref": 8}],
        "line_quad": True}


class _Field(object):
    def __init__(self, n, value):
        self.vals = [value] * n

    def getValues(self):
        return list(self.vals)

    def getValuesWithDescription(self, cmp):
        return list(self.vals), (list(range(1, len(self.vals) + 1)), [cmp])

    def setValues(self, vals):
        self.vals = list(vals)


class _Coords(object):
    def __init__(self, xyz):
        self.xyz = xyz

    def getValues(self):
        return [c for p in self.xyz for c in p]


class _Mesh(object):
    """Mesh file nodes 1..8 plus a LINE_QUAD midside node 9 between own
    node 5 and Mecway node 4 (cell 5-4-9, 0-based 4, 3, 8)."""
    def __init__(self):
        self.xyz = [(float(n), 0.0, 0.0) for n in range(1, 9)]
        self.xyz[4] = (0.0, 1.0, 0.0)           # own node 5 elsewhere
        self.xyz[3] = (4.0, 0.0, 0.0)
        self.xyz.append((2.0, 0.5, 0.0))        # midside of 5 and 4

    def getNumberOfNodes(self):
        return len(self.xyz)

    def getCoordinates(self):
        return _Coords(self.xyz)

    def getConnectivity(self):
        return [[4, 3, 8]]


def _numpy():
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def test_own_node_temperatures():
    md = _temp_model(400.0)
    block, _varc = b2a._build_temperature_field(md)
    m = re.search(r"_bridge_node_temps\(temp_fld, mesh, (\{.*?\}), (\d+)\)",
                  block, re.S)
    check(m is not None, "own nodes: _bridge_node_temps called")
    if m is None:
        return
    temps = ast.literal_eval(m.group(1))
    per_node = dict((n, k) for k, ns in temps.items() for n in ns)
    want = {1: 500.0, 5: 500.0, 2: 400.0, 6: 400.0, 3: 400.0, 7: 400.0}
    check(all(per_node.get(n) == k for n, k in want.items()),
          "own nodes: joint/offset/pre-tension nodes have the temperature "
          "of their Mecway node ({0})".format(per_node))
    check(m.group(2) == "8", "own nodes: n = Mecway + own nodes in the "
          "mesh file ({0})".format(m.group(2)))
    if not _numpy():
        return
    ns = {}
    exec(b2a._NODE_TEMPS_FUNC, ns)
    fld, mesh = _Field(9, 293.15), _Mesh()
    ns["_bridge_node_temps"](fld, mesh, temps, int(m.group(2)))
    check(abs(fld.vals[4] - 500.0) < 1e-9 and abs(fld.vals[6] - 400.0) <
          1e-9, "own nodes: job sets joint and copy node ({0})".format(
              fld.vals))
    check(abs(fld.vals[8] - 0.5 * (500.0 + 293.15)) < 1e-9,
          "own nodes: LINE_QUAD midside between own and Mecway node "
          "interpolated ({0})".format(fld.vals[8]))


def test_own_node_temperatures_history():
    md = _temp_model([(0.0, 293.15), (1.0, 393.15)])
    timeline = {"t0": 0.0, "t_end": 1.0, "ramp": False}
    block, _varc = b2a._build_temperature_field(md, timeline)
    check("_temp_sel" in block, "own nodes (history): _temp_sel written")
    if not _numpy() or "_temp_sel" not in block:
        return
    made = []

    def crea_champ(**kw):
        made.append(_Field(9, 293.15))
        return made[-1]

    ns = {"CREA_CHAMP": crea_champ, "CREA_RESU": lambda **kw: None,
          "_F": dict, "mesh": _Mesh()}
    exec(block, ns)
    last = made[-1].vals          # t = 1 s: 393.15 K on NS
    check(abs(last[1] - 393.15) < 1e-9 and abs(last[5] - 393.15) < 1e-9
          and abs(last[6] - 393.15) < 1e-9 and abs(last[4] - 500.0) < 1e-9,
          "own nodes (history): offset/copy follow the table, joint the "
          "Node temperature ({0})".format(last))


# ------------------------------------------------------------------
# 5. Supports in modal and buckling
# ------------------------------------------------------------------
_BOND = ("AFFE_CHAR_MECA", OrderedDict([("LIAISON_MAIL", [
    "_F(GROUP_MA_MAIT='A', GROUP_NO_ESCL='B', TYPE_RACCORD='MASSIF')"])]),
    None)
_GRAV = ("AFFE_CHAR_MECA", OrderedDict([("PESANTEUR", [
    "_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0))"])]), None)
_FIX = ("AFFE_CHAR_MECA", OrderedDict([("DDL_IMPO", [
    "_F(GROUP_NO='F', DX=0.0)"])]), None)


def test_support_state():
    st = b2a._support_state
    check(st({}, [_GRAV]) == "none", "support: none")
    check(st({}, [_BOND, _GRAV]) == "connections", "support: connections")
    check(st({}, [_FIX, _GRAV]) == "support", "support: DDL_IMPO")
    check(st({"aster_custom": {"excit": ["MYBC"]}}, [_GRAV]) == "support",
          "support: #ASTER-EXCIT counts")


def test_prestress_plan():
    md = {"bcs": []}
    del LOG[:]
    check(b2a._prestress_plan(md, [_BOND, _GRAV], ["load_1"],
                              ["load_2"]) is None and
          any("only on connections" in m for m in LOG),
          "prestress: only connections -> ERROR naming the cause")
    md = {"bcs": [], "aster_custom": {"excit": ["MYBC"]}}
    check(b2a._prestress_plan(md, [_GRAV], [], ["load_1"]) is not None,
          "prestress: support via #ASTER-EXCIT -> no ERROR")
    md = {"bcs": [], "cyclic": {"n": 6}}
    check(b2a._prestress_plan(md, [_BOND, _GRAV], ["load_1"],
                              ["load_2"]) is not None,
          "prestress: cyclic route unchanged")


def test_mo10_gravity_prestress():
    """MO-10 (free bar of two bonded blocks) with gravity: prestress
    (default on) stops before Code-Aster; without prestress free-free."""
    src = os.path.join(_HERE, "..", "TestFiles", "Verificatie", "modellen",
                       "MO-10.liml")
    if not os.path.exists(src):
        return
    import bridge_from_liml
    import bridge_mesh
    for mod in (bridge_from_liml, bridge_mesh):
        mod.log = _log
    text = io.open(src, encoding="utf-8").read()
    text = text.replace(
        "</contact2>", "</contact2>\n  <gravity><x>0 m/s²</x><y>0 "
        "m/s²</y><z>-9.81 m/s²</z></gravity>", 1)
    work = tempfile.mkdtemp()
    try:
        liml = os.path.join(work, "model.liml")
        io.open(liml, "w", encoding="utf-8").write(text)
        cfg = bridge_utils.CONFIG_BRIDGE
        cfg["work_dir"] = work
        cfg["active_analysis"] = "modal_3d"
        for prestress, ok in ((True, False), (False, True)):
            cfg["analyses"]["modal_3d"]["modal_prestress"] = prestress
            del LOG[:]
            md = bridge_from_liml.extract_aster_data_from_liml(liml)
            mail = os.path.join(work, "model_mesh.mail")
            check(md is not None and bridge_mesh.write_mesh(mail, md),
                  "MO-10: mesh")
            res = b2a.generate_AsterSolver_files(work, md, mail, "t.resu")
            if ok:
                check(bool(res) and any("free-free" in m for m in LOG),
                      "MO-10 + gravity, prestress off: free-free")
            else:
                check(not res and any("only on connections" in m
                                      for m in LOG),
                      "MO-10 + gravity, prestress on: ERROR before "
                      "Code-Aster")
    finally:
        bridge_utils.CONFIG_BRIDGE.clear()
        bridge_utils.CONFIG_BRIDGE.update(copy.deepcopy(_CONFIG))
        shutil.rmtree(work, ignore_errors=True)


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            if IRONPYTHON and name != "test_coef_mult_locale":
                continue
            fn()
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(_CONFIG)
    if FAILS:
        print("FAILED (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("OK: test_bridge_to_aster")
    return 0


# run_ipy.ps1 executes the file with another __name__
if __name__ == "__main__" or IRONPYTHON:
    sys.exit(main())
