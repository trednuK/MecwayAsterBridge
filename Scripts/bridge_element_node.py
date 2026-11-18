# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_element_node.py
# Route 'tabel' (bridge_from_aster.AsterToMecway_results): replace the
# values per element node that Mecway's own solve left (KNOWN_BUGS 7) with
# Code-Aster's nodal values, through solution.set_element_node_variable()
# (Mecway 36 and later). Compatible with IronPython 2.7.9 and Python 3 (no
# mw import; test: python tests/test_bridge_element_node.py, also under
# run_ipy.ps1).
#
# Mecway behaviour, measured in a hidden Mecway 36.0.9815 (18 Nov 2026; a
# solid block, a mixed hex8/quad4/line2 model with a shell island, a block
# of 27000 hex8):
#   - after Mecway's solve vonmises has values per element node on solid
#     elements only (None on shells and beams), vonmisesu1/m/b on shells
#     only; stressxx gives None per element node until set_variable creates
#     the node variable, and then Mecway's own stress per element node;
#   - after set_variable the node value is the new one but the value per
#     element node can stay Mecway's own (stale), which Mecway shows;
#   - set_element_node_variable(name, values): one list per element, index
#     0 = element 1, length = highest element number; per element the
#     values in the order of solution.nodes(e); None for an element or a
#     node is stored as None. The node value then follows the values per
#     element node: a node that lies only in elements given None loses its
#     node value;
#   - cost: 27000 elements in 0.06 s, 40000 element_node_value calls in
#     0.03 s.
# NOT verified: solutions with time steps or modes (skipped here), what
# Mecway shows for its derived variables (principal stresses, Tresca,
# formulas) after the replacement.
#
# Which elements are replaced is decided by what Mecway has, not by the
# element shape: an element counts when element_node_value(name, e, 1) is
# not None before or after the node values were written (solids, shells,
# 2D elements alike). Feature detection (AGENTS.md, Mecway versions):
# hasattr(solution, "set_element_node_variable"); without it the stale
# variables are named in one WARNING.

from bridge_utils import log, tr

# Variables Mecway keeps per element node and route 'tabel' writes per
# node (bridge_from_aster.RESULT_FIELD_SPECS / STRUCT_FIELD_SPECS). Beam
# variables (beam forces, beamsixx*) are element-node values by nature and
# are read by MecwayAdvancedBeamAnalysis: not touched.
CANDIDATES = tuple(
    ["stress" + c for c in ("xx", "yy", "zz", "xy", "yz", "zx")] +
    ["vonmises", "vonmisesu1", "vonmisesm", "vonmisesb",
     "equivalentplasticstrain"] +
    ["lstrain" + c for c in ("xx", "yy", "zz", "xy", "yz", "zx")] +
    ["plasticstrain" + c for c in ("xx", "yy", "zz", "xy", "yz", "zx")] +
    ["greenlagrangestrain" + c for c in ("xx", "yy", "zz", "xy", "yz",
                                         "zx")])


def _present(solution, name, element):
    """True if Mecway has a value of name at local node 1 of element; None
    when the call raised."""
    try:
        return solution.element_node_value(name, element, 1) is not None
    except Exception:
        return None


def _with_values(solution, name, elements):
    """The elements with a value of name per element node. Stops after a
    few failing calls (each one is an exception in IronPython)."""
    found, errors = set(), 0
    for e in elements:
        got = _present(solution, name, e)
        if got:
            found.add(e)
        elif got is None:
            errors += 1
            if errors >= 3:
                break
    return found


def _elements(solution):
    try:
        return [int(e) for e in solution.all_elements()]
    except Exception:
        return []


def _has_steps(solution):
    """True if the solution has time steps or modes, or that cannot be read
    (then the unprobed case is skipped too)."""
    for attr in ("time_steps", "modes"):
        try:
            if list(getattr(solution, attr)()):
                return True
        except Exception:
            return True
    return False


def prepare(solution, names, section_nodes=None, cleared=()):
    """
    Before route 'tabel' writes its node values: which elements have a
    value per element node of each candidate in names and of the shell
    components that may be cleared (Mecway's own solve). Returns the state
    for finish(), or None when this Mecway cannot read values per element
    node (nothing to do, no message).
    """
    if not hasattr(solution, "element_node_value"):
        return None
    elements = _elements(solution)
    if not elements:
        return None
    given = set(names)
    wanted = [n for n in CANDIDATES if n in given] + list(cleared)
    state = {"elements": elements, "names": wanted, "skip": None,
             "before": {}}
    if _has_steps(solution):
        state["skip"] = tr(u"de solution heeft tijdstappen of modes",
                           u"the solution has time steps or modes")
    elif section_nodes:
        state["skip"] = tr(u"er staat een doorsnede in de solution",
                           u"the solution holds a section view")
    for name in wanted:
        state["before"][name] = _with_values(solution, name, elements)
    return state


def finish(solution, state, arrays, cleared=()):
    """
    After route 'tabel' wrote its node values (arrays: {name: [value per
    node, index 0 = node 1]}): replace the values per element node of the
    written candidates by the node value of each element node, on the
    elements that have values per element node; clear them for the names
    in cleared (written as all None). Returns (replaced, stale): the names
    replaced or cleared, and [(name, reason)] of the names whose values per
    element node stay Mecway's (one WARNING in the log).
    """
    if state is None:
        return [], []
    elements = state["elements"]
    can_write = hasattr(solution, "set_element_node_variable")
    replaced, stale = [], []
    nodes = {}

    def nodes_of(e):
        if e not in nodes:
            try:
                nodes[e] = [int(n) for n in solution.nodes(e)]
            except Exception:
                nodes[e] = []
        return nodes[e]
    top = max(elements)
    todo = [n for n in state["names"] if n not in cleared and
            arrays.get(n) is not None] + list(cleared)
    covered_by = {}
    for name in todo:
        values = arrays.get(name) or []
        after = _with_values(solution, name, elements)
        mask = state["before"].get(name, set()) | after
        if not mask:
            continue
        if state["skip"]:
            stale.append((name, state["skip"]))
            continue
        if not can_write:
            stale.append((name, tr(
                u"Mecway zonder set_element_node_variable; Mecway 36 of "
                u"later vervangt ze",
                u"a Mecway without set_element_node_variable; Mecway 36 or "
                u"later replaces them")))
            continue
        clear = name in cleared
        if not clear:
            key = frozenset(mask)
            if key not in covered_by:
                covered_by[key] = set()
                for e in mask:
                    covered_by[key].update(nodes_of(e))
            covered = covered_by[key]
            lost = [i + 1 for i, v in enumerate(values)
                    if v is not None and (i + 1) not in covered]
            if lost:
                stale.append((name, tr(
                    u"knoop {0} heeft een waarde maar ligt in geen element "
                    u"met waarden per elementknoop",
                    u"node {0} has a value but lies in no element with "
                    u"values per element node").format(lost[0])))
                continue
        lists = [None] * top
        for e in mask:
            if clear:
                lists[e - 1] = [None] * len(nodes_of(e))
            else:
                lists[e - 1] = [values[n - 1] if 0 < n <= len(values)
                                else None for n in nodes_of(e)]
        try:
            solution.set_element_node_variable(name, lists)
            replaced.append(name)
        except Exception as exc:
            stale.append((name, u"{0}".format(exc)))
    if replaced:
        log(u"INFO: Values per element node replaced by Code-Aster's node "
            u"values (set_element_node_variable): {0}".format(
                u", ".join(replaced)))
    if stale:
        log(tr(u"WARNING: Mecway's eigen waarden per elementknoop blijven "
               u"staan voor {0}; de knoopwaarden zijn die van Code-Aster. "
               u"Route 'liml' geeft de waarden van Code-Aster per element.",
               u"WARNING: Mecway's own values per element node remain for "
               u"{0}; the node values are Code-Aster's. Route 'liml' gives "
               u"Code-Aster's values per element.").format(
                   u"; ".join(u"{0} ({1})".format(n, r) for n, r in stale)))
    return replaced, stale
