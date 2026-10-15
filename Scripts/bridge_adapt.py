# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_adapt.py
# Responsibility: adaptive refinement (step S7) of a linear static
# model (lin_static_3d) with Mecway's own refinement: after a run
# with the error estimator (CALC_ERREUR ERME, bridge_to_aster.
# _error_estimator_block) select the elements with the largest estimated
# error, refine them in Mecway (mw.refine_x2) and solve again, until a
# target (global relative error) or a limit (number of loops, elements).
# User doc: docs/Foutschatter.md par. 6.
#
#   adapt_settings(analysis, options) - settings (+ #ASTER-OPTIE), or
#                                       None if refinement is off
#   read_element_errors(fragment, ..) - eta_e per element from the
#                                       result file (ERME_ELNO)
#   select_elements(errors, ..)       - elements to refine (Dorfler,
#                                       fraction or factor x mean)
#   node_bc_conflicts(model_data, ..) - node selections with a condition
#                                       on an edge that gets refined
#   after_run(history, ...)           - decision after a run (loop of the
#                                       main script, MecwayAsterBridgeMain)
#   refine_in_mecway(mw, eids)        - mw.refine_x2 + check
#
# What Mecway's refine_x2 does (measured headless, mecway.exe <model> script,
# Mecway 33; docs/Foutschatter.md par. 6.4):
# - each selected element becomes 2 x 2 x 2 elements of the same shape; the
#   neighbours get transition elements (hex8 -> hex8 + pyr5 + tet4, hex20 ->
#   hex20 + pyr13 + tet10), the mesh stays conforming (no hanging nodes;
#   manual par. 4.4.1 "correctly connected"). Midside nodes of pyr13/tet10
#   lie at the middle of their edge, in the order of bridge_mesh.
#   _MID_EDGES (checked on all elements of a refined hex20 block);
# - face selections (and hence face loads and conditions), element
#   selections and parts (elset, material) carry over to the new elements;
#   node selections do NOT: the new nodes on an edge or face of a
#   node selection are not included (also manual par. 9: "loads and
#   constraints applied to nodes remain at the same point locations");
# - new nodes lie on the (quadratic) element geometry: with hex20
#   a circular edge stays a circle (deviation 5e-4 r after one refinement
#   of a 45-degree arc), with hex8 on the chord (the edge stays the
#   polygon of the coarse mesh);
# - elements and nodes are renumbered (the refined and the
#   transition elements get new numbers);
# - after a few loops the transitions can produce bad elements: with
#   thin elements (thickness 1/40 of the width) after 2 loops nearly flat
#   hex20 (scaled Jacobian 0.015) and a rising error estimate; with
#   tet10 already after the first loop (transitions with wedge15/pyr13);
#   with hex20 at an aspect ratio ~1 (verification AD-02) the error
#   decreased monotonically over 5 loops (docs/Verificatie.md, AD).
#
# Compatible with IronPython 2.7.9 and CPython 3 (verification; standard
# library only).

import base64
import math
import re
import struct

from bridge_utils import log, tr, parse_yes_no

# Default settings (also in CONFIG_BRIDGE["analyses"]["lin_static_3d"];
# here as a fallback for an older bridge_utils.py).
DEFAULTS = {
    "adapt_refine":       False,
    "adapt_target_error": 2.0,
    "adapt_max_loops":    5,
    "adapt_select":       "dorfler",
    "adapt_fraction":     0.5,
    "adapt_neighbours":   False,
    "adapt_max_elements": 200000,
}
SELECT_METHODS = ("dorfler", "fraction", "factor")

# Error field per element in the result file (aster_results_export
# FIELD_TABLE: ERME_ELNO ERREST -> elementnodevariable "errorestimate").
ERROR_VARIABLE = "errorestimate"

# Growth of the number of elements per refined element (8 children plus the
# transition elements in the neighbours), for the limit adapt_max_elements
# in advance. Measured (headless Mecway 33): 2 of 8 hex8 -> 46 elements (19
# per refined element); plate with hole hex20 38 to 70 per element. After
# the first loop the measured growth of the previous loop counts (_growth).
_GROWTH = 40.0

# Corner pairs of the edges per volume shape (Mecway node order = Code-
# Aster order for volumes, bridge_mesh._ASTER_TYPES; edges as
# bridge_mesh._MID_EDGES).
_EDGES = {
    "hex": [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 5), (2, 6), (3, 7),
            (4, 5), (5, 6), (6, 7), (4, 7)],
    "tet": [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)],
    "pyr": [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 4), (2, 4), (3, 4)],
    "wedge": [(0, 1), (1, 2), (0, 2), (0, 3), (1, 4), (2, 5), (3, 4), (4, 5),
              (3, 5)],
}


# ==========================================
# SETTINGS
# ==========================================
def _option_value(old, raw):
    """#ASTER-OPTIE text to the type of the default value (like
    bridge_custom.apply_options). Not a valid yes/no word or number:
    ValueError (the default value stays; apply_options gives the
    WARNING)."""
    if isinstance(old, bool):
        value = parse_yes_no(raw)
        if value is None:
            raise ValueError(raw)
        return value
    if isinstance(old, int):
        return int(raw)
    if isinstance(old, float):
        return float(raw)
    return raw.strip("'\"")


def adapt_settings(analysis, options=None):
    """
    Settings of the adaptive refinement for the analysis (dict from
    CONFIG_BRIDGE["analyses"]) with the #ASTER-OPTIE values of the model
    (model_data["aster_custom"]["options"]; these win, invalid values
    are already reported by bridge_custom.apply_options). Returns the dict
    with the adapt_* keys, or None if refinement is off or not possible (no
    MECA_STATIQUE or no error estimator).
    """
    options = options or {}
    out = {}
    for key, default in DEFAULTS.items():
        value = analysis.get(key, default)
        raw = options.get(key)
        if raw is not None:
            try:
                value = _option_value(default, "{0}".format(raw))
            except ValueError:
                pass
        out[key] = value
    if not out["adapt_refine"]:
        return None
    est = analysis.get("error_estimator", False)
    raw = parse_yes_no(options.get("error_estimator"))
    if raw is not None:
        est = raw
    if analysis.get("solver_command") != "MECA_STATIQUE" or not est:
        log(tr("WARNING: Adaptieve verfijning (adapt_refine) vraagt een "
               "lineair statische analyse met de foutschatter "
               "(error_estimator aan); niet verfijnd.",
               "WARNING: Adaptive refinement (adapt_refine) needs a linear "
               "static analysis with the error estimator (error_estimator "
               "on); not refined."))
        return None
    if out["adapt_select"] not in SELECT_METHODS:
        log(tr("WARNING: adapt_select '{0}' onbekend (bekend: {1}); "
               "dorfler gebruikt.",
               "WARNING: adapt_select '{0}' unknown (known: {1}); dorfler "
               "used.").format(out["adapt_select"],
                               ", ".join(SELECT_METHODS)))
        out["adapt_select"] = "dorfler"
    return out


# ==========================================
# ERROR PER ELEMENT FROM THE RESULT FILE
# ==========================================
_TAG = re.compile(r'<(results|elementnodeids|elementnodevariable|'
                  r'nodevariable|valuessingle|valuesdouble)\b([^>]*)>')
_NAME = re.compile(r'name="([^"]*)"')


def _text(line):
    if not isinstance(line, str):           # CPython 3: bytes
        line = line.decode("utf-8", "replace")
    return line


def _unpack(chunks, code):
    raw = base64.b64decode("".join(chunks))
    size = struct.calcsize(code)
    return struct.unpack("<%d%s" % (len(raw) // size, code), raw)


def read_element_errors(fragment_path, elements, variable=ERROR_VARIABLE):
    """
    Estimated error eta_e per element (ERME_ELNO, component ERREST;
    constant per element) from a result file of the bridge
    (aster_results_export, also a .liml with <results>).

    elements : [(eid, shape, [nid, ...], elset)] of the model
               (model_data["mesh_elements"]): the number of values per
               element is its number of nodes (elementnodevariable, nodes in
               the order of <elem nodes>).
    Returns {eid: eta_e}; {} if the field is missing (error estimator off,
    or route 'tabel').
    """
    n_nodes = dict((e[0], len(e[2])) for e in elements)
    ids_chunks, val_chunks = None, None
    code = "f"
    target = None
    in_var = False
    f = open(fragment_path, "rb")
    try:
        for line in f:
            line = _text(line)
            if target is not None:
                part = line.split("<", 1)[0].strip()
                if part:
                    target.append(part)
                if "<" in line:
                    target = None
                continue
            m = _TAG.search(line)
            if m is None:
                continue
            kind, attrs = m.group(1), m.group(2)
            name = _NAME.search(attrs)
            name = name.group(1) if name else None
            sink = None
            if kind == "results":
                code = "d" if 'precision="double"' in attrs else "f"
            elif kind == "elementnodeids" and name == variable:
                ids_chunks = sink = []
            elif kind == "elementnodevariable":
                in_var = name == variable and val_chunks is None
            elif kind == "nodevariable":
                in_var = False
            elif kind in ("valuessingle", "valuesdouble") and in_var:
                code = "d" if kind == "valuesdouble" else "f"
                val_chunks = sink = []
                in_var = False
            if sink is not None:
                rest = line[m.end():]
                part = rest.split("<", 1)[0].strip()
                if part:
                    sink.append(part)
                if "<" not in rest:
                    target = sink
    finally:
        f.close()
    if not ids_chunks or not val_chunks:
        return {}
    eids = _unpack(ids_chunks, "i")
    vals = _unpack(val_chunks, code)
    out = {}
    pos = 0
    for eid in eids:
        n = n_nodes.get(eid)
        if n is None or pos + n > len(vals):
            log(tr("WARNING: Adaptieve verfijning: element {0} van het "
                   "resultaat past niet bij het model; foutwaarden niet "
                   "gelezen.",
                   "WARNING: Adaptive refinement: element {0} of the result "
                   "does not fit the model; error values not read.").format(
                       eid))
            return {}
        # float(): IronPython returns a System.Single/Double from struct.
        out[eid] = float(vals[pos])
        pos += n
    return out


# ==========================================
# SELECTION OF THE ELEMENTS
# ==========================================
def select_elements(errors, method="dorfler", value=0.5):
    """
    Elements to refine from {eid: eta_e}:
      dorfler  - the smallest group of elements with the largest error that
                 together carry a fraction value (0 < value <= 1) of the
                 total squared error (sum eta_e^2) ("bulk criterion",
                 Dorfler 1996); default 0.5;
      fraction - the fraction value of the elements with the largest error
                 (0.1 = 10%);
      factor   - the elements with eta_e > value x the mean of eta_e.
    Equal values: lower element number first. Returns a sorted list.
    """
    items = sorted(errors.items(), key=lambda kv: (-kv[1], kv[0]))
    if not items:
        return []
    if method == "fraction":
        n = int(math.ceil(max(0.0, min(1.0, value)) * len(items) - 1e-9))
        chosen = items[:max(1, n)]
    elif method == "factor":
        mean = sum(v for _e, v in items) / float(len(items))
        chosen = [kv for kv in items if kv[1] > value * mean]
    else:
        total = sum(v * v for _e, v in items)
        goal = max(0.0, min(1.0, value)) * total
        chosen, acc = [], 0.0
        for kv in items:
            if acc >= goal and chosen:
                break
            chosen.append(kv)
            acc += kv[1] * kv[1]
    return sorted(e for e, _v in chosen)


def _shape_family(shape):
    for fam in ("hex", "tet", "pyr", "wedge"):
        if shape.startswith(fam):
            return fam
    return None


def add_neighbours(elements, eids):
    """
    eids plus all volume elements that share a node with one of eids
    (a buffer layer; setting adapt_neighbours). Measured (headless
    Mecway 33, thin plate with hole, hex20 1/40 of the width thick):
    refine_x2 on only the selected elements gave, in the second loop where
    the selection bordered the transition elements of the first loop,
    nearly flat hex20 (scaled Jacobian 0.015; global estimate from 3.7%
    to 19.6%); with the buffer layer the worst hex stayed 0.68 up to and
    including loop 3, dropping only in loop 4 (0.009). For the thick plate
    (AD-02) the buffer only costs elements: Kt within 2% at 22956 instead of
    15810 elements. elements: model_data["mesh_elements"].
    """
    wanted = set(eids)
    by_node = {}
    solid = []
    for eid, shape, nids, _elset in elements:
        if _shape_family(shape) is None:
            continue
        solid.append((eid, nids))
        for n in nids:
            by_node.setdefault(n, []).append(eid)
    out = set(wanted)
    for eid, nids in solid:
        if eid in wanted:
            for n in nids:
                out.update(by_node[n])
    return sorted(out)


# Corner nodes of each vertex and its three edges (Mecway order):
# hex via the derivatives of the trilinear mapping at the corners; tet,
# wedge, pyr (base) with the three edges from that vertex.
_HEX_RST = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
_CORNER_EDGES = {
    "tet": [(0, 1, 2, 3), (1, 2, 0, 3), (2, 0, 1, 3), (3, 0, 1, 2)],
    "wedge": [(0, 1, 2, 3), (1, 2, 0, 4), (2, 0, 1, 5), (3, 5, 4, 0),
              (4, 3, 5, 1), (5, 4, 3, 2)],
    "pyr": [(0, 1, 3, 4), (1, 2, 0, 4), (2, 3, 1, 4), (3, 0, 2, 4)],
}


def _det(a, b, c):
    return (a[0] * (b[1] * c[2] - b[2] * c[1]) -
            a[1] * (b[0] * c[2] - b[2] * c[0]) +
            a[2] * (b[0] * c[1] - b[1] * c[0]))


def _scaled(a, b, c):
    la = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    lb = math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2)
    lc = math.sqrt(c[0] ** 2 + c[1] ** 2 + c[2] ** 2)
    if la * lb * lc <= 0.0:
        return 0.0
    return abs(_det(a, b, c)) / (la * lb * lc)


def scaled_jacobian(shape, pts):
    """
    Smallest scaled Jacobian at the corners (|det| of the three edges /
    their lengths; 1 = right angles, 0 = flat), corner nodes only
    (not midside nodes). pts: node coordinates in Mecway order.
    """
    fam = _shape_family(shape)
    if fam == "hex":
        worst = 1.0
        for r, s, t in _HEX_RST:
            d = [[0.0, 0.0, 0.0] for _k in range(3)]
            for (ri, si, ti), p in zip(_HEX_RST, pts[:8]):
                w = (ri * (1 + si * s) * (1 + ti * t),
                     si * (1 + ri * r) * (1 + ti * t),
                     ti * (1 + ri * r) * (1 + si * s))
                for k in range(3):
                    for j in range(3):
                        d[k][j] += w[k] * p[j]
            worst = min(worst, _scaled(*d))
        return worst
    worst = 1.0
    for i, a, b, c in _CORNER_EDGES.get(fam, []):
        o = pts[i]
        worst = min(worst, _scaled(*[[pts[x][j] - o[j] for j in range(3)]
                                     for x in (a, b, c)]))
    return worst


# Limit for a "bad" element (scaled Jacobian of a hex):
# choice of the bridge; the coarse plate model has 0.71, the bad
# transitions 0.002 to 0.02. Hex only: for tet/pyr/wedge the measure
# also depends on the slenderness (a sound tet in a thin layer already
# gives 0.02).
BAD_ELEMENT = 0.1


def bad_elements(model_data):
    """Hex elements with a scaled Jacobian < BAD_ELEMENT:
    [(eid, value)], worst first."""
    nodes = model_data.get("mesh_nodes", {})
    out = []
    for eid, shape, nids, _elset in model_data.get("mesh_elements", []):
        if _shape_family(shape) != "hex":
            continue
        try:
            q = scaled_jacobian(shape, [nodes[n] for n in nids])
        except KeyError:
            continue
        if q < BAD_ELEMENT:
            out.append((eid, q))
    return sorted(out, key=lambda x: x[1])


def node_bc_conflicts(model_data, eids):
    """
    Node selections with a load or condition (aster_target GROUP_NO)
    of which two corner nodes form an edge of an element to be refined:
    Mecway does not put the new node on that edge in the selection, so
    after refinement the condition would be missing there. Returns
    [(selection, kind)].
    """
    groups = model_data.get("node_groups", {})
    node_bcs = []
    for bc in model_data.get("bcs", []):
        if bc.get("aster_target") != "GROUP_NO":
            continue
        # node_groups: Code-Aster names "N<nid>" (bridge_from_liml STAP 1)
        nodes = set()
        for n in groups.get(bc.get("selection"), []):
            try:
                nodes.add(int("{0}".format(n).lstrip("N")))
            except ValueError:
                pass
        if len(nodes) > 1:
            node_bcs.append((bc.get("selection"), bc.get("type"), nodes))
    if not node_bcs:
        return []
    wanted = set(eids)
    edges = set()
    for eid, shape, nids, _elset in model_data.get("mesh_elements", []):
        if eid not in wanted:
            continue
        fam = _shape_family(shape)
        for a, b in _EDGES.get(fam, []):
            if a < len(nids) and b < len(nids):
                edges.add((nids[a], nids[b]))
    out = []
    for sel, kind, nodes in node_bcs:
        if any(a in nodes and b in nodes for a, b in edges):
            if (sel, kind) not in out:
                out.append((sel, kind))
    return out


# ==========================================
# DECISION AFTER A RUN
# ==========================================
def _fmt(v, digits=3):
    # %-formatting: "{0:.3g}".format() follows the Windows locale in
    # IronPython (MecwayAsterBridgeMain._report_modes).
    return ("%." + str(digits) + "g") % v


def summary_lines(history):
    """Table of the loops for log and status box."""
    lines = [tr(u"Adaptieve verfijning: lus, elementen (volume), globale "
                u"relatieve fout, verfijnd:",
                u"Adaptive refinement: loop, elements (solid), global "
                u"relative error, refined:")]
    for h in history:
        lines.append(u"  {0}: {1}, {2}%, {3}".format(
            h["loop"], h["n_elem"], _fmt(h["rel"]),
            h.get("n_refined", "-")))
    return lines


def _growth(history):
    """New elements per refined element in the previous loop (history[-2]
    -> history[-1]), otherwise _GROWTH. Counts volume elements only."""
    if len(history) >= 2 and history[-2].get("n_refined"):
        grow = (history[-1]["n_elem"] - history[-2]["n_elem"]) / float(
            history[-2]["n_refined"])
        if grow > 0:
            return grow
    return _GROWTH


def after_run(history, settings, model_data, fragment_path, error_summary):
    """
    Decision after a run of the loop (MecwayAsterBridgeMain._adapt_step).

    history       : list of previous loops (extended here with a
                    dict {"loop", "n_elem", "rel", "abs", "n_refined"})
    settings      : adapt_settings()
    model_data    : of this run (mesh_elements, bcs, node_groups)
    fragment_path : result file of this run
    error_summary : last dict of bridge_results_liml.read_error_summary
                    (global error from the .mess) or None

    Returns {"refine": bool, "elements": [eid], "notes": [text for the
    status box]}; all messages are also in the log.
    """
    notes = []

    def stop(text, level="INFO"):
        log(u"{0}: {1}".format(level, text))
        notes.append(text)
        notes.extend(summary_lines(history))
        for line in summary_lines(history):
            log(u"INFO: " + line)
        return {"refine": False, "elements": [], "notes": notes}

    loop = len(history)
    if not error_summary:
        history.append({"loop": loop, "n_elem": 0, "rel": float("nan"),
                        "abs": float("nan")})
        return stop(tr(u"Adaptieve verfijning gestopt: geen globale "
                       u"foutschatting in de .mess (foutschatter niet "
                       u"gedraaid of afgebroken).",
                       u"Adaptive refinement stopped: no global error "
                       u"estimate in the .mess (error estimator did not run "
                       u"or was aborted)."), "WARNING")
    errors = read_element_errors(fragment_path,
                                 model_data.get("mesh_elements", []))
    rec = {"loop": loop, "n_elem": len(errors), "rel": error_summary["rel"],
           "abs": error_summary.get("abs")}
    history.append(rec)
    log(u"INFO: Adaptive refinement loop {0}: {1} volume elements, "
        u"global relative error {2}%.".format(loop, len(errors),
                                               _fmt(rec["rel"])))
    bad = bad_elements(model_data)
    if bad:
        text = tr(u"WARNING: Adaptieve verfijning: {0} element(en) met een "
                  u"slechte vorm (geschaalde Jacobiaan < {1}; slechtste: "
                  u"element {2}, {3}). Daar zijn spanning en foutschatting "
                  u"onbetrouwbaar; bekijk het mesh in Mecway.",
                  u"WARNING: Adaptive refinement: {0} element(s) with a poor "
                  u"shape (scaled Jacobian < {1}; worst: element {2}, {3}). "
                  u"Stress and error estimate are unreliable there; check "
                  u"the mesh in Mecway.").format(
                      len(bad), BAD_ELEMENT, bad[0][0], _fmt(bad[0][1], 2))
        log(text)
        notes.append(text[len("WARNING: "):])
    target = float(settings["adapt_target_error"])
    if rec["rel"] <= target:
        return stop(tr(u"Adaptieve verfijning: doel bereikt (globale "
                       u"relatieve fout {0}% <= {1}%).",
                       u"Adaptive refinement: target reached (global "
                       u"relative error {0}% <= {1}%).").format(
                           _fmt(rec["rel"]), _fmt(target)))
    if loop >= 1 and rec["rel"] >= history[-2]["rel"]:
        return stop(tr(u"WARNING: Adaptieve verfijning gestopt: de globale "
                       u"fout daalt niet meer ({0}% -> {1}%). Mogelijk een "
                       u"singulariteit (scherpe hoek, puntlast, rand van een "
                       u"inklemming) of een last die de schatter niet kent "
                       u"(docs/Foutschatter.md par. 2.3).",
                       u"WARNING: Adaptive refinement stopped: the global "
                       u"error no longer decreases ({0}% -> {1}%). Possibly "
                       u"a singularity (sharp corner, point load, edge of a "
                       u"clamp) or a load the estimator does not know "
                       u"(docs/en/Error_estimator.md sec. 2.3).").format(
                           _fmt(history[-2]["rel"]), _fmt(rec["rel"]))
                    [len("WARNING: "):], "WARNING")
    if loop >= int(settings["adapt_max_loops"]):
        return stop(tr(u"Adaptieve verfijning: maximaal aantal lussen ({0}) "
                       u"bereikt; globale relatieve fout {1}% (doel {2}%).",
                       u"Adaptive refinement: maximum number of loops ({0}) "
                       u"reached; global relative error {1}% (target "
                       u"{2}%).").format(settings["adapt_max_loops"],
                                         _fmt(rec["rel"]), _fmt(target)))
    if not errors:
        return stop(tr(u"Adaptieve verfijning gestopt: geen fout per element "
                       u"in het resultaatbestand (veld errorestimate; "
                       u"resultaatroute 'liml' nodig).",
                       u"Adaptive refinement stopped: no error per element "
                       u"in the result file (field errorestimate; result "
                       u"route 'liml' needed)."), "WARNING")
    chosen = select_elements(errors, settings["adapt_select"],
                             float(settings["adapt_fraction"]))
    # Optionally a buffer layer (add_neighbours; thin elements).
    eids = chosen
    if settings.get("adapt_neighbours"):
        eids = add_neighbours(model_data.get("mesh_elements", []), chosen)
    n_all = len(model_data.get("mesh_elements", []))
    estimate = n_all + _growth(history) * len(eids)
    if estimate > int(settings["adapt_max_elements"]):
        return stop(tr(u"Adaptieve verfijning gestopt: na verfijnen van {0} "
                       u"elementen zou het model ongeveer {1} elementen "
                       u"hebben (grens adapt_max_elements {2}).",
                       u"Adaptive refinement stopped: after refining {0} "
                       u"elements the model would have about {1} elements "
                       u"(limit adapt_max_elements {2}).").format(
                           len(eids), int(estimate),
                           settings["adapt_max_elements"]))
    conflicts = node_bc_conflicts(model_data, eids)
    if conflicts:
        return stop(tr(u"ERROR: Adaptieve verfijning gestopt: de "
                       u"knoopselectie(s) {0} met een belasting of "
                       u"voorwaarde liggen op ribben die verfijnd worden. "
                       u"Mecway zet de nieuwe knopen daar niet in de "
                       u"selectie, dus de voorwaarde zou na het verfijnen "
                       u"gaten krijgen. Leg de voorwaarde op vlakken "
                       u"(vlakselectie; die verfijnt Mecway mee) en start "
                       u"opnieuw.",
                       u"ERROR: Adaptive refinement stopped: the node "
                       u"selection(s) {0} with a load or constraint lie on "
                       u"edges that would be refined. Mecway does not add "
                       u"the new nodes there to the selection, so the "
                       u"constraint would get gaps after refining. Apply "
                       u"it to faces (face selection; Mecway refines those "
                       u"along) and start again.").format(
                           u", ".join(u"'{0}' ({1})".format(s, k)
                                      for s, k in conflicts))
                    [len("ERROR: "):], "ERROR")
    rec["n_refined"] = len(eids)
    rec["n_chosen"] = len(chosen)
    text = tr(u"Adaptieve verfijning lus {0}: globale relatieve fout {1}% > "
              u"doel {2}%; {3} van {4} volume-elementen worden verfijnd "
              u"(mw.refine_x2, keuze {5} {6}{7}).",
              u"Adaptive refinement loop {0}: global relative error {1}% > "
              u"target {2}%; {3} of {4} solid elements are refined "
              u"(mw.refine_x2, selection {5} {6}{7}).").format(
                  loop, _fmt(rec["rel"]), _fmt(target), len(eids),
                  len(errors), settings["adapt_select"],
                  _fmt(float(settings["adapt_fraction"])),
                  tr(u"; {0} gekozen plus de buren",
                     u"; {0} chosen plus their neighbours").format(
                         len(chosen)) if len(eids) != len(chosen) else u"")
    log(u"INFO: " + text)
    notes.append(text)
    return {"refine": True, "elements": eids, "notes": notes}


# ==========================================
# REFINING IN MECWAY
# ==========================================
def refine_in_mecway(mw, eids):
    """
    mw.refine_x2 on the elements eids (API: refine_x2(node_ids, face_ids,
    element_ids), exactly one of the three). Returns the number of elements
    afterwards, or None on an error (ERROR in the log).
    """
    before = len(mw.all_elements())
    try:
        mw.refine_x2(None, None, list(eids))
    except Exception as e:
        log(tr(u"ERROR: Mecway-verfijning (refine_x2) mislukt: {0}",
               u"ERROR: Mecway refinement (refine_x2) failed: {0}").format(e))
        return None
    after = len(mw.all_elements())
    log(u"INFO: Adaptive refinement: refine_x2 on {0} elements: {1} -> "
        u"{2} elements, {3} nodes.".format(len(eids), before, after,
                                              len(mw.all_nodes())))
    if after <= before:
        log(tr(u"ERROR: Mecway-verfijning (refine_x2) gaf geen nieuwe "
               u"elementen.",
               u"ERROR: Mecway refinement (refine_x2) gave no new "
               u"elements."))
        return None
    return after
