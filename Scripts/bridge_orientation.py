# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_orientation.py
#
# Responsibility: Mecway's Element orientation as a Loads & Constraints
# item (<orientation>) to the same data as the per-element attributes
# (orientationvx/vy/vz + angle, orientationux/uy/uz).
#
#   parse(item, model_data)   <orientation> from the .liml
#                             (bridge_from_liml, item loop)
#   apply(model_data)         resolve the cards per element, after the
#                             modelisations are known (bridge_from_liml,
#                             STEP 4)
#
# MECWAY (manual v34 par. 7.4.2 and 7.5: orientation "in two places -
# Element properties and Loads & Constraints > Element orientation", the
# latter "applied to a selection of elements" and allowing "a formula ...
# as a function of element center position"). Found in the fork by
# MishalTPC (github.com/mishal0488/MecwayAsterBridge). Measured headless
# with Mecway 34 (TestFiles/Tools/mw_solve.py, 16 Oct 2026; Mecway writes
# the card back like this in its solution file, it does not convert it to
# element attributes):
#   <orientation selection="All">
#     <ux>0</ux><uy>0</uy><uz>0</uz>        U axis (shells, gaps, solids)
#     <vx>0</vx><vy>0</vy><vz>1</vz>        V axis (beams)
#     <angleu>30 °</angleu>                 rotation of V about U (beams)
#   </orientation>
#   - always all seven children; a zero vector = not given; an angle
#     without unit is in rad ("30" -> Mecway writes "30 rad");
#   - a formula: <vy unit="" timeunit="s" positionunit="m">x</vy>,
#     <angleu unit="°" ...>30*x</angleu>, evaluated per element (centre);
#   - beam: same tip displacements as the attributes with the same vector
#     and angle (V = Z, and V = Z + 30 degrees on an inclined beam), also
#     for a card on part of the elements; selection = an element
#     selection; a card on a component name (no selection of that name)
#     has no effect; suppressed="true" has no effect;
#   - Mecway refuses to solve (no solution) a card on elements that
#     already have an orientation (attributes, even the same values, or a
#     second card: "... is applied to already has its orientation defined
#     elsewhere"), a card with a U axis on beams, and a card with a V axis
#     or angle on shells ("The orientation type, ..., can not be used with
#     an element that it is applied to"); a beam card without V vector
#     gives a singular result (displacement 1e15).
# The bridge translates the first and reports the others (WARNING); with
# overlapping orientations the card wins, and of two cards the later one
# in the file.
#
# Use per element type:
#   beams (POU_*)     V and angle -> model_data["beam_orientations"]
#                     (bridge_mesh: VECT_Y per beam cell)
#   gaps              U -> model_data["elem_u_axes"] (gap direction,
#                     bridge_to_aster._prepare_gaps)
#   shells            U -> model_data["card_u_axes"] (U,V of the result
#                     field shell_forces, aster_results_export u_axes);
#                     no effect on the solution with isotropic material
#   solids, trusses, cables, springs, dampers: no effect (INFO; orthotropic
#                     material is STAPPENPLAN S13)
#
# Compatible with IronPython 2.7.9 (Mecway scripting engine).

import re
from collections import OrderedDict

from bridge_utils import log, tr, parse_and_convert
from bridge_bcs import (_FormulaParser, _FORMULA_VARS, _is_formula,
                        _unit_map, _unit_si, FormulaError)

TAG = "orientation"
_U_KEYS = ("ux", "uy", "uz")
_V_KEYS = ("vx", "vy", "vz")
_SHELLS = frozenset(["tri3", "tri6", "quad4", "quad8"])
_LINES = frozenset(["line2", "line3"])
_NUMBER = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*"
                     r"[^\s\d()*+/^-]*\s*$")


class _PointParser(_FormulaParser):
    """_FormulaParser with x, y, z as separate variables: the closures get
    a dict {"x": .., "y": .., "z": ..} instead of the time."""

    def _atom(self):
        kind, text = self._peek()
        nxt = (self.tokens[self.pos + 1]
               if self.pos + 1 < len(self.tokens) else None)
        if kind == "name" and text in _FORMULA_VARS and nxt != ("op", "("):
            self.pos += 1
            self.used.add(text)
            return lambda env, n=text: env[n]
        return _FormulaParser._atom(self)


def _value(node, quantity):
    """SI value of a child of <orientation>: a float, or a function of
    the element centre (x, y, z in m) for a formula. FormulaError if it
    cannot be translated."""
    text = (node.text or "").strip()
    if not _is_formula(node):
        if not text:
            return 0.0
        if not _NUMBER.match(text):
            raise FormulaError(u"'{0}' is geen getal;",
                               u"'{0}' is not a number;", text)
        return parse_and_convert(text, quantity)
    parser = _PointParser(text)
    try:
        fn = parser.parse()
    except ValueError as e:
        raise FormulaError(u"formule '{0}' niet te lezen ({1});",
                           u"formula '{0}' cannot be read ({1});", text, e)
    if "t" in parser.used:
        raise FormulaError(
            u"formule '{0}' hangt af van de tijd t; een orientatie is "
            u"niet tijdsafhankelijk;",
            u"formula '{0}' depends on time t; an orientation is not "
            u"time-dependent;", text)
    a, b = _unit_map(node.get("unit"), quantity)
    pu = _unit_si(node.get("positionunit"), "length")

    def at(point, fn=fn, a=a, b=b, pu=pu, text=text):
        env = {"x": point[0] / pu, "y": point[1] / pu, "z": point[2] / pu,
               "t": 0.0}
        try:
            v = float(fn(env))
        except (ValueError, ZeroDivisionError, OverflowError,
                TypeError) as e:
            raise FormulaError(
                u"formule '{0}' niet te berekenen in ({1}) ({2});",
                u"formula '{0}' cannot be evaluated at ({1}) ({2});", text,
                ", ".join("%.6g" % c for c in point), e)
        if v != v or v in (float("inf"), float("-inf")):
            raise FormulaError(u"formule '{0}' geeft geen getal in ({1});",
                               u"formula '{0}' gives no number at ({1});",
                               text, ", ".join("%.6g" % c for c in point))
        return a * v + b
    return at


def _what(sel):
    return tr("element orientation op '{0}'",
              "element orientation on '{0}'").format(sel)


def _not_translated(model_data, sel, why):
    model_data["skipped_loads"].append(_what(sel))
    log(tr("ERROR: {0}: {1} NIET meegenomen.",
           "ERROR: {0}: {1} NOT included.").format(_what(sel), why))


def parse(item, model_data):
    """<orientation> -> model_data["orientation_cards"] (in file
    order)."""
    sel = item.get("selection", "")
    values = {}
    for key in _U_KEYS + _V_KEYS + ("angleu",):
        node = item.find(key)
        if node is None:
            continue
        try:
            values[key] = _value(node, "angle" if key == "angleu"
                                 else "dimensionless")
        except FormulaError as e:
            _not_translated(model_data, sel, e.text())
            return
    model_data.setdefault("orientation_cards", []).append(
        {"selection": sel, "values": values})
    log("INFO: Element orientation card on '{0}' read.".format(sel))


def _centre(model_data, nodes):
    """Element centre for a formula: mean of all element nodes (for line2
    equal to Mecway, LS-81; quadratic elements and shells NOT verified,
    KNOWN_BUGS 116)."""
    xyz = model_data["mesh_nodes"]
    pts = [xyz[n] for n in nodes if n in xyz]
    if not pts:
        return (0.0, 0.0, 0.0)
    return tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))


def _resolve(card, point):
    """(U, V, angle) of a card at point (FormulaError possible)."""
    vals = card["values"]

    def get(key):
        v = vals.get(key, 0.0)
        return v(point) if callable(v) else v
    return (tuple(get(k) for k in _U_KEYS), tuple(get(k) for k in _V_KEYS),
            get("angleu"))


def _ids(eids):
    eids = sorted(eids)
    return ", ".join(str(e) for e in eids[:10]) + (
        " ..." if len(eids) > 10 else "")


def apply(model_data):
    """Apply the orientation cards (parse) to the elements of their
    element selection; see the header for the rules. After STEP 3 of
    bridge_from_liml (elset_modelisations, discrete_sections and the
    truss split known)."""
    cards = model_data.get("orientation_cards") or []
    if not cards:
        return
    mods = model_data.get("elset_modelisations", {})
    disc = model_data.get("discrete_sections", {})
    elems = dict((e[0], e) for e in model_data.get("mesh_elements", []))
    selections = model_data.get("element_selections", {})
    beam_or = model_data.setdefault("beam_orientations", {})
    u_axes = model_data.setdefault("elem_u_axes", {})
    card_u = model_data.setdefault("card_u_axes", {})
    # elements with an orientation from their attributes, then per card
    owner = dict((eid, None) for eid in list(beam_or) + list(u_axes))
    for card in cards:
        sel = card["selection"]
        eids = selections.get(sel)
        if eids is None:
            _not_translated(model_data, sel, tr(
                "geen elementselectie met die naam (Mecway gebruikt de "
                "kaart dan ook niet);",
                "no element selection with that name (Mecway does not use "
                "the card then either);"))
            continue
        counts = OrderedDict()
        overlap, ignored = [], OrderedDict()
        try:
            for eid in eids:
                e = elems.get(eid)
                if e is None:
                    continue
                _eid, shape, nodes, elset = e
                u, v, angle = _resolve(card, _centre(model_data, nodes))
                has_u, has_v = any(u), any(v)
                mod = mods.get(elset, "")
                if shape in _LINES and mod.startswith("POU_"):
                    kind = "beam"
                    if has_u:
                        ignored.setdefault("beam_u", []).append(eid)
                    if not has_v:
                        ignored.setdefault("beam_no_v", []).append(eid)
                        continue
                    new = {"vec": v, "angle": angle}
                    target = beam_or
                elif shape in _LINES and disc.get(elset, {}).get(
                        "kind") == "gap":
                    kind = "gap"
                    if not has_u:
                        ignored.setdefault("no_effect", []).append(eid)
                        continue
                    new, target = u, u_axes
                elif shape in _SHELLS:
                    kind = "shell"
                    if has_v or angle:
                        ignored.setdefault("shell_v", []).append(eid)
                    if not has_u:
                        continue
                    new, target = u, u_axes
                    card_u[eid] = u
                else:
                    ignored.setdefault("no_effect", []).append(eid)
                    continue
                if eid in owner:
                    overlap.append(eid)
                owner[eid] = sel
                target[eid] = new
                counts[kind] = counts.get(kind, 0) + 1
        except FormulaError as err:
            _not_translated(model_data, sel, err.text())
            continue
        _report(sel, card, counts, overlap, ignored, owner)


def _report(sel, card, counts, overlap, ignored, owner):
    """Log lines of one card."""
    vals = dict((k, "formula" if callable(v) else v)
                for k, v in card["values"].items())
    log("INFO: Element orientation '{0}' ({1}) applied to: {2}.".format(
        sel, ", ".join("{0}={1}".format(k, vals[k]) for k in sorted(vals)),
        ", ".join("{0} {1}".format(n, k) for k, n in counts.items())
        or "no element"))
    if "shell" in counts:
        log("INFO: Element orientation '{0}': the U axis of shells only "
            "sets the U,V axes of the result field shell_forces (no effect "
            "on the solution with isotropic material).".format(sel))
    if overlap:
        log(tr("WARNING: Element orientation '{0}': {1} element(s) hebben al "
               "een orientatie (elementeigenschappen of een eerdere kaart): "
               "{2}. Mecway rekent zo'n model niet ('already has its "
               "orientation defined elsewhere'); de bridge gebruikt deze "
               "kaart (van twee kaarten de laatste in het bestand).",
               "WARNING: Element orientation '{0}': {1} element(s) already "
               "have an orientation (element properties or an earlier "
               "card): {2}. Mecway does not solve such a model ('already "
               "has its orientation defined elsewhere'); the bridge uses "
               "this card (of two cards the last one in the file).").format(
                   sel, len(overlap), _ids(overlap)))
    texts = {
        "beam_u": (u"de U-as heeft bij balken geen betekenis (Mecway rekent "
                   u"het model dan niet); genegeerd",
                   u"the U axis has no meaning for beams (Mecway does not "
                   u"solve the model then); ignored"),
        "beam_no_v": (u"geen V-vector (Mecway geeft dan een singuliere "
                      u"oplossing); standaardorientatie van Mecway gebruikt",
                      u"no V vector (Mecway then gives a singular "
                      u"solution); Mecway's default orientation used"),
        "shell_v": (u"V-as en hoek gelden alleen voor balken (Mecway rekent "
                    u"het model dan niet); genegeerd",
                    u"V axis and angle only apply to beams (Mecway does not "
                    u"solve the model then); ignored"),
    }
    for key, eids in ignored.items():
        if key == "no_effect":
            log("INFO: Element orientation '{0}': no effect on {1} "
                "element(s) ({2}): solids, trusses, cables, springs and "
                "dampers have no section orientation and the material is "
                "isotropic (the bridge does not translate orthotropic "
                "material yet).".format(
                    sel, len(eids), _ids(eids)))
            continue
        nl, en = texts[key]
        log(tr(u"WARNING: Element orientation '{0}', {1} element(s) ({2}): "
               + nl + u".",
               u"WARNING: Element orientation '{0}', {1} element(s) ({2}): "
               + en + u".").format(sel, len(eids), _ids(eids)))
