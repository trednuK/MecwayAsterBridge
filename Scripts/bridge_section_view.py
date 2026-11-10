# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_section_view.py
#
# Responsibility: the swept shape of general-section beams, and the results
# on it. Mecway has no shape for a general-section beam; MecwaySectionProps
# stores the outline in the model (** SECTIE-VORM lines, bridge_custom.py).
# From that outline this module makes shells as plain data (build_view: ids,
# coordinates, shapes, per beam, no XML). That data serves two routes:
# temporary elements through the Mecway API before a calculation (not in this
# module), and the model copy inside <solution> of the .liml (solution_lines),
# so that Mecway shows the shells in its own window together with the results.
# The model part of the file is not touched.
#
# Pure: no mw calls and no file writing, Python 2.7 (IronPython 2.7.9) and 3.
#
#   parse_shapes(bodies)            lines -> {material: {"loops", "area"}}
#   current_shapes(shapes, md)      only shapes that still match the material
#   find_beams(md, shapes)          beams to draw, with frame and offset
#   build_view(md, shapes)          shell nodes and elements, plain data
#   solution_lines / solution_text  that data as text for the model copy
#   insert_into_copy(lines, view)   that text in the lines of the model copy
#   thin_beam_lines(lines, view)    Mecway's drawing of those beams made small
#   shell_values(view, d, r, md)    displacement and stress per shell node
#   match_table / shear_points      the section table of a run per shell node
#   shell_shear(view, ...)          shear stress and von Mises per shell node
#
# CONTRACT (comment lines in any custom text field, in file order):
#   ** SECTIE-VORM <material>: N=<points of loop 1> <points of loop 2> ...,
#      A=<area in m2>                                   (on one line)
#   ** SECTIE-VORM <material>: P=v w v w ...
# v, w in metres, principal axes about the centroid, V = Mecway V, W = U x V.
# Loops are closed implicitly, the interior is even-odd. P lines concatenate
# in order. A new N= for a material replaces what was read before, so the
# newest wins. Material name: split on the last colon.
#   ** SECTIE-RICHTING <material>: V=vx vy vz, U=ux uy uz
# Global unit vectors the section was made for, a check only, no part of the
# shape: bridge_custom.report_directions, here on the drawn beams.
#
# GEOMETRY:
#   One closed ring per element end, own nodes per element, one quad4 per
#   outline segment. Contours therefore stay element-wise, as is right for
#   beams; rings of adjacent elements do not meet at a kink. A line3 uses its
#   corners only (Mecway order c0, m, c1) and the frame of the chord, as
#   bridge_mesh does for the direction check. Caps at free ends only (a node used
#   by one drawn beam): trapezoids between consecutive W levels of the loop
#   points, which handles holes without triangulation.
#
# RESULTS (displacement and rotation only, which Mecway always stores):
#   ring point: r = v V + w W, displacement d + theta x (r + offset).
#   Longitudinal stress, two routes, both measured on Mecway 35.0.9802 against
#   stressptu on 7 beams in all orientation types, 14 element ends
#   (tests/test_bridge_section_view.py):
#   1. Section forces, when the solution has them: N = tensileforce, Mv =
#      bendingmomv, Mw = bendingmomw at that element end
#        sigma(v, w) = N / A + Mv w / iyy - Mw v / izz
#   2. Kinematics of the element, the fallback: displacement and rotation
#      are always stored.
#        strain = (d2 - d1).U / L
#        Hermite on (d.V, theta.W) gives v'', on (d.W, -theta.V) gives w''
#        sigma(v, w) = E (strain - v'' v - w'' w)
#   On a Mecway solve the two agree (N = E A strain, Mv = -E iyy w'', Mw = E
#   izz v''), also with a load inside the element: Mecway's own element values
#   carry the same error of about q h^2 / 12, and the section forces do not
#   correct it. The internal general-section beam has no shear deformation.
#   Limits: no warping bimoment. Route 2 only: a flexible joint at a beam end
#   is not known here, shear deformation of a Code-Aster Timoshenko beam is
#   not in the Hermite field, a line3 is one Hermite element over its chord,
#   linear elastic only. Route 1 on a Code-Aster solution: names and signs of
#   the export are Mecway's (aster_results_export, MFY/MFZ); this formula
#   against statics in LS-97a, measured.
#   Element offset (bridge_offset: global x, y, z, line2 only): the element
#   ends move with the arm, d' = d + theta x offset, so strain and curvature
#   use d'. As bridge_offset.link_entries; against Mecway NOT verified.
#
#   Shear stress and von Mises: numpy has to make the fields, so the job does
#   (bridge_section_stress, table in <run>_section.json). Shear is linear in Vv,
#   Vw and T_S = T + EY Vw - EZ Vv, so that this module only sums the table per
#   step. von Mises = sqrt(sigma^2 + 3 tau^2) with the sigma above. Only with
#   the section forces of the solution and only with a table of this section.
#
# Mecway draws a general section as a small rectangle, which would stand in
# the shells. The API has no display control, but the model copy is ours: in
# that copy only, the beams get a material with a thin RectBar (thin_size: from
# the size and the wall thickness of the section, at most THIN_MAX). The stored
# results and
# the model part do not change. User check on Mecway 35, 2 x 2 mm on an
# L 60 x 40: small enough.
#
# Measured on Mecway 35.0.9802: shells in the model copy inside <solution>,
# with no counterpart in the model part, open without a dialog, stay after a
# save and a reopen, and were seen in Mecway's window with their colours on a
# chain of 7 beams with an L section (user check, 5 Nov 2026). On a real
# Code-Aster solution opened hidden, values read through the API (LS-97a, c);
# colours there NOT verified. Not on line3 or an element offset.
#
# Compatible with IronPython 2.7.9.

import io
import math
from collections import OrderedDict

from bridge_utils import log, tr
from bridge_custom import report_directions
from bridge_from_liml import _SECTION_MATCH_TOL
from bridge_mesh import _mecway_v_axis
from bridge_offset import _BEAMS as _OFFSET_BEAMS

ELSET = "Doorsnede"
ELSET_COLOR = "DADADA"      # as the hand-written file measured in Mecway 35
# Refused above this number of side quads (no coarser outline: the outline
# belongs to MecwaySectionProps, which already limits it).
MAX_QUADS = 200000
# Indentation of a top-level element in the model copy inside <solution>:
# Mecway's two spaces plus the two of bridge_results_liml._model_copy.
COPY_INDENT = "    "
GENERAL_SECTION = "UniformGeneralSection"
_BEAM_SHAPES = ("line2", "line3")
_CORNERS = {"line2": (0, 1), "line3": (0, 2)}       # Mecway: c0, m, c1
_REL_TOL = 1.0e-12          # of the section size: coinciding points
THIN_FRACTION = 0.03        # of the largest size of the section
THIN_WALL = 0.25            # of the wall thickness
THIN_MAX = 0.002            # m
THIN_SUFFIX = "__doorsnede_lijn"


# ==========================================
# VECTORS
# ==========================================
def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a, f):
    return (a[0] * f, a[1] * f, a[2] * f)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


# ==========================================
# READING THE LINES
# ==========================================
def _number(text):
    """float of text, or None; 'nan' and 'inf' are no numbers here."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _read_head(rest):
    """'N=17 6, A=1.5e-3' -> state of a material (see parse_shapes)."""
    state = {"counts": None, "area": None, "values": [], "error": None}
    for part in rest.split(","):
        key, eq, raw = part.partition("=")
        key = key.strip()
        if eq and key == "N" and state["counts"] is None:
            try:
                state["counts"] = [int(t) for t in raw.split()]
            except ValueError:
                state["counts"] = None
        elif eq and key == "A" and state["area"] is None:
            state["area"] = _number(raw.strip())
        else:
            state["counts"] = None
            break
    if not state["counts"] or min(state["counts"]) < 3:
        state["error"] = tr(u"N= verwacht minstens 3 punten per lus",
                            u"N= expects at least 3 points per loop")
    elif state["area"] is None or state["area"] <= 0.0:
        state["error"] = tr(u"A= ontbreekt of is geen oppervlak > 0",
                            u"A= is missing or not an area > 0")
    return state


def _read_points(rest, state):
    """Add the numbers of a P= line to state, or set its error."""
    values = [_number(t) for t in rest.split()]
    if None in values:
        state["error"] = tr(u"P= bevat iets anders dan getallen",
                            u"P= holds something else than numbers")
    else:
        state["values"].extend(values)


def _clean_loop(points):
    """Without repeated points: the file rounds to a few digits, so that
    neighbours can coincide, also the last with the first."""
    out = []
    for p in points:
        if not out or p != out[-1]:
            out.append(p)
    while len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _finish(state):
    """(loops, error) of a material after all its lines."""
    if state["error"]:
        return None, state["error"]
    values = state["values"]
    if len(values) != 2 * sum(state["counts"]):
        return None, tr(u"{0} getallen in P=, {1} verwacht uit N=",
                        u"{0} numbers in P=, {1} expected from N=").format(
                            len(values), 2 * sum(state["counts"]))
    loops, pos = [], 0
    for n in state["counts"]:
        chunk = values[pos:pos + 2 * n]
        pos += 2 * n
        loop = _clean_loop(list(zip(chunk[0::2], chunk[1::2])))
        if len(loop) < 3:
            return None, tr(u"een lus heeft minder dan 3 verschillende "
                            u"punten",
                            u"a loop has less than 3 different points")
        loops.append(loop)
    return loops, None


def parse_shapes(bodies):
    """
    {material: {"loops": [[(v, w), ...], ...], "area": m2}} from the bodies
    of the SECTIE-VORM lines (bridge_custom: out["section_shapes"]), in file
    order. Bad data skips that material with a log line; never raises. A new
    N= replaces what was read before, also an error, and when that newest N=
    is itself bad the material is skipped: an older outline does not come
    back.
    """
    states = OrderedDict()
    for body in bodies:
        name, sep, rest = body.rpartition(":")
        name = name.strip()
        rest = rest.strip()
        if not sep or not name:
            log(tr(u"WARNING: SECTIE-VORM '{0}' wordt overgeslagen: verwacht "
                   u"'<materiaal>: N=...' of '<materiaal>: P=...'.",
                   u"WARNING: SECTIE-VORM '{0}' is skipped: expected "
                   u"'<material>: N=...' or '<material>: P=...'.").format(
                       body))
            continue
        if rest.startswith("N="):
            states[name] = _read_head(rest)
            continue
        state = states.setdefault(name, {"counts": None, "area": None,
                                         "values": [], "error": None})
        if state["error"]:
            continue
        if not rest.startswith("P="):
            state["error"] = tr(u"onbekende regel '{0}'",
                                u"unknown line '{0}'").format(rest)
        elif state["counts"] is None:
            state["error"] = tr(u"P= voor N=", u"P= before N=")
        else:
            _read_points(rest[2:], state)
    out = OrderedDict()
    for name, state in states.items():
        loops, error = _finish(state)
        if error:
            log(tr(u"WARNING: SECTIE-VORM van materiaal '{0}' wordt "
                   u"overgeslagen: {1}.",
                   u"WARNING: SECTIE-VORM of material '{0}' is skipped: "
                   u"{1}.").format(name, error))
            continue
        out[name] = {"loops": loops, "area": state["area"]}
    return out


def has_shape_lines(liml_path):
    """True when the model part of the .liml holds SECTIE-VORM lines: a quick
    look that spares a run without them a second parse of the model. Stops
    at <solution>, which can be hundreds of MB."""
    with io.open(liml_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "SECTIE-VORM" in line:
                return True
            if "<solution" in line:
                return False
    return False


def current_shapes(shapes, model_data):
    """
    The shapes whose A still matches the general section of their material
    (model_data["mat_geometrics"]), with the tolerance of the #ASTER-SECTIE
    check. A material changed or renamed after MecwaySectionProps keeps its
    old lines in the model, so that its outline may belong to something else.
    """
    out = OrderedDict()
    geoms = model_data.get("mat_geometrics", {})
    for name, shape in shapes.items():
        geom = geoms.get(name)
        if geom is None or geom.get("geom_type") != GENERAL_SECTION:
            log(tr(u"WARNING: SECTIE-VORM '{0}': geen materiaal met een "
                   u"General section met deze naam (hernoemd?); de vorm "
                   u"wordt genegeerd.",
                   u"WARNING: SECTIE-VORM '{0}': no material with a general "
                   u"section of this name (renamed?); the shape is ignored."
                   ).format(name))
            continue
        ref = dict(zip(geom.get("cara", ()), geom.get("vale", ()))).get(
            "A", 0.0)
        if abs(shape["area"] - ref) > _SECTION_MATCH_TOL * max(abs(ref),
                                                               1e-30):
            log(tr(u"WARNING: SECTIE-VORM '{0}': A = {1} in de regel, maar "
                   u"{2} in het materiaal; de doorsnede is na "
                   u"MecwaySectionProps gewijzigd. De vorm wordt genegeerd.",
                   u"WARNING: SECTIE-VORM '{0}': A = {1} in the line, but "
                   u"{2} in the material; the section was changed after "
                   u"MecwaySectionProps. The shape is ignored.").format(
                       name, "%.6g" % shape["area"], "%.6g" % ref))
            continue
        out[name] = shape
    return out


# ==========================================
# BEAMS
# ==========================================
def beam_frame(p1, p2, orient):
    """(U, V, W) of the beam p1 -> p2 as in Mecway: V from
    bridge_mesh._mecway_v_axis, W = U x V. orient: as there."""
    d = _sub(p2, p1)
    u = _scale(d, 1.0 / math.sqrt(_dot(d, d)))
    v = _mecway_v_axis(p1, p2, orient)
    return u, v, _cross(u, v)


def beam_offsets(model_data):
    """
    {eid: (x, y, z)} global element offset per beam (m): the rule of
    bridge_offset.prepare for beams, where the first offset of an element
    applies and an offset on a line3 is not used. Without its logging and
    its entries in model_data, which belong to a run.
    """
    shapes = model_data.get("elem_shapes", {})
    selections = model_data.get("element_selections", {})
    out = {}
    for off in model_data.get("element_offsets") or []:
        if off.get("xyz") is None or not any(off["xyz"]):
            continue
        for eid in selections.get(off.get("selection")) or ():
            if shapes.get(eid) in _OFFSET_BEAMS and eid not in out:
                out[eid] = tuple(off["xyz"])
    return out


def find_beams(model_data, shapes):
    """
    (beams, skipped): the beams to draw and {"no_shape": n, "invalid": n}.

    model_data: from extract_aster_data_from_liml, before write_mesh (which
    renames the elset keys). A beam as in bridge_mesh: line2/line3 with a
    MODELISATION POU_*, so no trusses (BARRE), cables or springs. Skipped
    beams: no usable shape for their material; "invalid": a node is missing
    or both ends coincide.
    beam: {"eid", "nodes": (n1, n2), "material", "ends": (p1, p2), "frame":
    (U, V, W), "length", "offset", "element_nodes": (k1, k2)}. element_nodes:
    place of the two ends in <elem nodes>, 1-based, the k of
    solution.element_node_value (measured on line2; line3 NOT verified).
    """
    xyz = model_data.get("mesh_nodes", {})
    mods = model_data.get("elset_modelisations", {})
    elsets = model_data.get("elsets", {})
    orient = model_data.get("beam_orientations", {})
    offsets = beam_offsets(model_data)
    beams = []
    skipped = {"no_shape": 0, "invalid": 0}
    for eid, shape, nodes, elset in model_data.get("mesh_elements", []):
        if (shape not in _BEAM_SHAPES or
                not mods.get(elset, "").startswith("POU_")):
            continue
        material = elsets.get(elset)
        if material not in shapes:
            skipped["no_shape"] += 1
            continue
        first, last = _CORNERS[shape]
        if len(nodes) <= last or nodes[first] not in xyz or \
                nodes[last] not in xyz:
            skipped["invalid"] += 1
            continue
        n1, n2 = nodes[first], nodes[last]
        p1, p2 = xyz[n1], xyz[n2]
        d = _sub(p2, p1)
        length = math.sqrt(_dot(d, d))
        if length == 0.0:
            skipped["invalid"] += 1
            continue
        beams.append({"eid": eid, "nodes": (n1, n2), "material": material,
                      "ends": (p1, p2),
                      "frame": beam_frame(p1, p2, orient.get(eid)),
                      "length": length,
                      "offset": offsets.get(eid, (0.0, 0.0, 0.0)),
                      "element_nodes": (first + 1, last + 1)})
    return beams, skipped


# ==========================================
# CAPS
# ==========================================
def _v_at(edge, w):
    a, b = edge
    return a[0] + (b[0] - a[0]) * (w - a[1]) / (b[1] - a[1])


def polygon_area(points):
    """Signed area (shoelace) of a closed polygon; > 0 anticlockwise."""
    total = 0.0
    for i in range(len(points)):
        a, b = points[i - 1], points[i]
        total += a[0] * b[1] - b[0] * a[1]
    return 0.5 * total


def cap_pieces(loops):
    """
    The even-odd interior of the loops as pieces [(v, w), ...] of 4 or 3
    points, anticlockwise seen from +U (V x W = U). Between two consecutive W
    levels of the loop points no vertex lies inside the band, so that every
    edge crossing the band spans all of it: the crossings at mid-band, sorted
    on v and paired, give the trapezoids. A side of length 0 gives a
    triangle; pieces of area 0 are dropped.
    """
    points = [p for loop in loops for p in loop]
    size = max(max(p[0] for p in points) - min(p[0] for p in points),
               max(p[1] for p in points) - min(p[1] for p in points))
    tol = _REL_TOL * size
    edges = []
    for loop in loops:
        for i in range(len(loop)):
            a, b = loop[i - 1], loop[i]
            if a[1] < b[1]:
                edges.append((a, b))
            elif b[1] < a[1]:
                edges.append((b, a))
    levels = sorted(set(p[1] for p in points))
    pieces = []
    for low, high in zip(levels[:-1], levels[1:]):
        mid = 0.5 * (low + high)
        crossing = sorted([(_v_at(e, mid), i) for i, e in enumerate(edges)
                           if e[0][1] < mid < e[1][1]])
        for k in range(0, len(crossing) - 1, 2):
            left = edges[crossing[k][1]]
            right = edges[crossing[k + 1][1]]
            corners = [(_v_at(left, low), low), (_v_at(right, low), low),
                       (_v_at(right, high), high), (_v_at(left, high), high)]
            if abs(corners[1][0] - corners[0][0]) <= tol:
                corners.pop(1)
            elif abs(corners[2][0] - corners[3][0]) <= tol:
                corners.pop(2)
            if len(corners) >= 3 and polygon_area(corners) > tol * size:
                pieces.append(corners)
    return pieces


# ==========================================
# SWEEP
# ==========================================
def thin_size(loops, area):
    """
    Side of the thin bar that replaces Mecway's drawing of a beam: the
    smallest of THIN_MAX, a fraction of the largest size and a fraction of
    the wall thickness. Wall thickness of a thin-walled section: 2 A / P, with
    P the length of all loops (an L 60 x 40 x 6 gives 5.64 mm, a tube its
    wall); a solid section gets a large value, so the other two decide.
    """
    vs = [p[0] for loop in loops for p in loop]
    ws = [p[1] for loop in loops for p in loop]
    perimeter = sum(math.hypot(loop[i][0] - loop[i - 1][0],
                               loop[i][1] - loop[i - 1][1])
                    for loop in loops for i in range(len(loop)))
    return min(THIN_MAX,
               THIN_FRACTION * max(max(vs) - min(vs), max(ws) - min(ws)),
               THIN_WALL * 2.0 * area / perimeter)


def _in_file(name):
    """A material name as it stands in the bytes of the .liml."""
    text = (name.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
    return text.encode("utf-8").decode("latin-1")


def thin_beam_lines(lines, view, indent=COPY_INDENT):
    """
    The lines of the model copy with the beams of view on a thin bar: for
    every material in view["thin"] a copy of its <mat> named <material> +
    THIN_SUFFIX with a RectBar as geometry, and the elsets of that material
    on it. What an earlier call did is undone first, so a second call gives
    the same text. Elsets and mats are looked for at the indentation of the
    copy, so the top level of the file is never touched.
    """
    mat_tag = indent + "<mat "
    set_tag = indent + "<elset "
    out, skip = [], False
    for line in lines:
        if skip:
            skip = line.strip() != "</mat>"
            continue
        if line.startswith(mat_tag) and \
                (THIN_SUFFIX + '"') in line.split(">")[0]:
            skip = not line.rstrip().endswith("/>")
            continue
        if line.startswith(set_tag):
            line = line.replace(THIN_SUFFIX + '"', '"')
        out.append(line)
    for material, size in sorted(view.get("thin", {}).items()):
        name = _in_file(material)
        start = None
        for i, line in enumerate(out):
            if line.startswith(mat_tag) and ('name="%s"' % name) in line:
                start = i
                break
        if start is None:
            continue
        stop = start
        while out[stop].strip() != "</mat>":
            stop += 1
        block = []
        for line in out[start:stop + 1]:
            if line.startswith(mat_tag):
                line = line.replace('name="%s"' % name,
                                    'name="%s%s"' % (name, THIN_SUFFIX))
            elif "<geometric " in line:
                line = '%s  <geometric type="RectBar" recta="%.6g m" ' \
                    'rectb="%.6g m" />' % (indent, size, size)
            block.append(line)
        out[start:start] = block
        old = 'material="%s"' % name
        new = 'material="%s%s"' % (name, THIN_SUFFIX)
        out = [line.replace(old, new) if line.startswith(set_tag) else line
               for line in out]
    return out


def side_quads(beams, shapes):
    """Number of quads of the sides: one per outline segment per beam."""
    return sum(sum(len(lp) for lp in shapes[b["material"]]["loops"])
               for b in beams)


def _section_point(beam, end, v, w):
    """Global position of section point (v, w) at element end 0 or 1."""
    _u, vv, ww = beam["frame"]
    centre = _add(beam["ends"][end], beam["offset"])
    return _add(_add(centre, _scale(vv, v)), _scale(ww, w))


def _free_name(name, taken):
    """name, or name_<k> when the model has a component of that name."""
    k, out = 0, name
    while out in taken:
        k += 1
        out = "{0}_{1}".format(name, k)
    return out


def build_view(model_data, shapes, max_quads=MAX_QUADS, warn_directions=True):
    """
    The swept beams, or None when above max_quads (ERROR in the log) or
    when there is nothing to draw (INFO in the log).

    shapes: from current_shapes. Plain data, no XML: usable for temporary
    elements through the API as well as for solution_lines. Shell node ids
    are contiguous from max(model node id) + 1, element ids from
    max(model element id) + 1. warn_directions False: no check of the
    SECTIE-RICHTING lines, for the view at the end of a run, whose write_mesh
    made it already. Returns dict:
      nids     : [nid] shell nodes, ascending
      xyz      : [(x, y, z)] position per shell node
      origin   : [(beam index, end 0/1, v, w)] section point per shell node
      elements : [(eid, "quad4"/"tri3", (nid, ...))]
      parts    : per beam, in the order of beams: {"eid": beam element,
                 "nodes": [(nid, (x, y, z))], "elements": as above}
      elset    : name of the component
      thin     : {material: size of the thin bar in the model copy, metres}
      shapes   : {material: shape} of the drawn beams
      beams    : as find_beams
      skipped  : as find_beams
      quads, tris : number of elements
      direction_warnings : texts of report_directions, on the drawn beams
    """
    beams, skipped = find_beams(model_data, shapes)
    notes = []
    if warn_directions:
        notes = report_directions(
            model_data.get("aster_custom", {}).get("section_directions"),
            [(b["material"], b["frame"][0], b["frame"][1]) for b in beams])
    if skipped["no_shape"] or skipped["invalid"]:
        log(tr(u"WARNING: Doorsnede: {0} balken zonder bruikbare vorm en {1} "
               u"ongeldige balken worden niet getekend.",
               u"WARNING: Section view: {0} beams without a usable shape and "
               u"{1} invalid beams are not drawn.").format(
                   skipped["no_shape"], skipped["invalid"]))
    if not beams:
        log("INFO: Section view: no beam to draw.")
        return None
    n_side = side_quads(beams, shapes)
    if n_side > max_quads:
        log(tr(u"ERROR: Doorsnede: {0} quads over {1} balken, de grens is "
               u"{2}. De vorm wordt niet gemaakt.",
               u"ERROR: Section view: {0} quads over {1} beams, the limit "
               u"is {2}. The shape is not made.").format(
                   n_side, len(beams), max_quads))
        return None
    next_nid = max(model_data.get("mesh_nodes") or [0]) + 1
    next_eid = max([e[0] for e in model_data.get("mesh_elements", [])] +
                   [0]) + 1
    view = {"nids": [], "xyz": [], "origin": [], "elements": [],
            "parts": [{"eid": b["eid"], "nodes": [], "elements": []}
                      for b in beams],
            "elset": _free_name(ELSET, set(
                e[3] for e in model_data.get("mesh_elements", []))),
            "beams": beams, "skipped": skipped, "quads": 0, "tris": 0,
            "direction_warnings": notes,
            "thin": dict((m, thin_size(shapes[m]["loops"], shapes[m]["area"]))
                         for m in set(b["material"] for b in beams)),
            "shapes": dict((m, shapes[m])
                           for m in set(b["material"] for b in beams))}

    def add_node(index, end, v, w):
        nid = next_nid + len(view["nids"])
        xyz = _section_point(beams[index], end, v, w)
        view["nids"].append(nid)
        view["xyz"].append(xyz)
        view["origin"].append((index, end, v, w))
        view["parts"][index]["nodes"].append((nid, xyz))
        return nid

    def add_element(index, nodes):
        shape = "quad4" if len(nodes) == 4 else "tri3"
        element = (next_eid + len(view["elements"]), shape, tuple(nodes))
        view["elements"].append(element)
        view["parts"][index]["elements"].append(element)
        view["quads" if len(nodes) == 4 else "tris"] += 1

    use = {}
    for beam in beams:
        for nid in beam["nodes"]:
            use[nid] = use.get(nid, 0) + 1
    for index, beam in enumerate(beams):
        loops = shapes[beam["material"]]["loops"]
        rings = [[[add_node(index, end, v, w) for v, w in loop]
                  for loop in loops] for end in (0, 1)]
        for ring0, ring1 in zip(rings[0], rings[1]):
            for i in range(len(ring0)):
                add_element(index, (ring0[i - 1], ring0[i], ring1[i],
                                    ring1[i - 1]))
        for end in (0, 1):
            if use[beam["nodes"][end]] == 1:
                _add_cap(view, index, end, loops, add_node, add_element)
    return view


def _add_cap(view, index, end, loops, add_node, add_element):
    """Cap with its own nodes, shared within the cap; the normal points
    out of the beam (-U at end 0, +U at end 1)."""
    pieces = cap_pieces(loops)
    span = max(abs(c) for p in pieces for q in p for c in q) if pieces else 0
    tol = max(span, 1e-30) * 1.0e-10
    nodes = {}
    for piece in pieces:
        ids = []
        for v, w in (piece if end == 1 else piece[::-1]):
            key = (int(round(v / tol)), int(round(w / tol)))
            if key not in nodes:
                nodes[key] = add_node(index, end, v, w)
            ids.append(nodes[key])
        add_element(index, ids)


# ==========================================
# TEXT FOR THE MODEL COPY IN <solution>
# ==========================================
def _num(x):
    """Number in the file. % formatting: IronPython's str.format follows the
    Windows locale. 17 digits give the same double back; + 0.0: no '-0'."""
    return "%.17g" % (float(x) + 0.0)


def solution_lines(view, indent=COPY_INDENT):
    """
    Lines for the model copy inside <solution>: the <node> lines, then one
    <elset> with the shells, without material or anything else that would
    make it part of the analysis. Indentation as _solution_copy in
    bridge_results_liml, whose lines these join.
    """
    out = []
    for nid, p in zip(view["nids"], view["xyz"]):
        out.append('{0}<node nid="{1}" x="{2}" y="{3}" z="{4}" />'.format(
            indent, nid, _num(p[0]), _num(p[1]), _num(p[2])))
    out.append('{0}<elset name="{1}" colorrgb="{2}">'.format(
        indent, view["elset"], ELSET_COLOR))
    for eid, shape, nodes in view["elements"]:
        out.append('{0}  <elem eid="{1}" shape="{2}" nodes="{3}" />'.format(
            indent, eid, shape, " ".join(str(n) for n in nodes)))
    out.append("{0}</elset>".format(indent))
    return out


def solution_text(view, nl="\r\n", indent=COPY_INDENT):
    """solution_lines as one text; every line ends with nl."""
    return nl.join(solution_lines(view, indent)) + nl


def insert_into_copy(copy_lines, view, indent=COPY_INDENT):
    """
    New list: the lines of the model copy (bridge_results_liml._solution_copy)
    with solution_lines after the last top-level <node>, so that all nodes
    stay together before the first <elset>. Only an exact indent counts: the
    <node> lines of a <nodeselection> lie deeper. The model copy itself stays
    as it is, line by line.
    """
    tag = indent + "<node "
    last = -1
    for i, line in enumerate(copy_lines):
        if line.startswith(tag):
            last = i
    return (list(copy_lines[:last + 1]) + solution_lines(view, indent) +
            list(copy_lines[last + 1:]))


# ==========================================
# RESULTS
# ==========================================
def point_displacement(d, theta, r):
    """d + theta x r, small rotations; r from the node, offset included."""
    return _add(d, _cross(theta, r))


def match_table(entry, shape, model_data, material):
    """
    True when entry (one section of a <run>_section.json) was made for this
    section: the outline, nu, A, IY, IZ and, when the model states them, EY and
    EZ. Numbers, not text: .NET and CPython can differ in the last digit of a
    parsed number. shape: from current_shapes.
    """
    geom = model_data.get("mat_geometrics", {}).get(material) or {}
    cara = dict(zip(geom.get("cara", ()), geom.get("vale", ())))
    nu = (model_data.get("materials", {}).get(material) or {}).get("NU")

    def same(a, b):
        return (a is not None and b is not None and
                abs(a - b) <= _SECTION_MATCH_TOL * max(abs(a), abs(b), 1e-30))

    if nu is None or abs(entry.get("nu", -9.0) - nu) > 1.0e-9:
        return False
    for key in ("A", "IY", "IZ"):
        if not same(entry.get(key), cara.get(key)):
            return False
    for key in ("EY", "EZ"):
        if key in cara and abs(entry.get(key, 1.0e30) - cara[key]) > \
                _SECTION_MATCH_TOL * math.sqrt(cara["A"]):
            return False
    theirs, ours = entry.get("loops") or [], shape["loops"]
    size = math.sqrt(shape["area"])
    if [len(lp) for lp in theirs] != [len(lp) for lp in ours]:
        return False
    return all(abs(a - b) <= 1.0e-8 * size
               for lt, lo in zip(theirs, ours) for pt, po in zip(lt, lo)
               for a, b in zip(pt, po))


def _nearest_row(rows, v, w, tol):
    best, row = tol, None
    for item in rows:
        dist = abs(item[0] - v) + abs(item[1] - w)
        if dist <= best:
            best, row = dist, item
    return row


def shear_points(view, tables):
    """
    Per shell node its row of the table, or None. tables: {material: entry of
    <run>_section.json}. A row: v, w, then six unit values (Vv on v, w; Vw; T_S),
    or twelve inside a corner zone (bridge_section_stress).
    """
    seen, out = {}, []
    for index, _end, v, w in view["origin"]:
        material = view["beams"][index]["material"]
        key = (material, v, w)
        if key not in seen:
            entry = tables.get(material)
            seen[key] = None if entry is None else _nearest_row(
                entry["points"], v, w,
                1.0e-6 * math.sqrt(entry.get("A", 0.0)))
        out.append(seen[key])
    return out


def shear_at(row, vv, vw, ts):
    """|tau| at a shell point; in a corner zone the larger of the two exits."""
    best = 0.0
    for k in range(2, len(row) - 5, 6):
        best = max(best, math.hypot(vv * row[k] + vw * row[k + 2] +
                                    ts * row[k + 4],
                                    vv * row[k + 1] + vw * row[k + 3] +
                                    ts * row[k + 5]))
    return best


def shell_shear(view, points, tables, forces, sigma, wanted):
    """
    ([tau], [von Mises]) for the positions wanted in view["nids"]. points: from
    shear_points. forces: {beam eid: ((Vv, Vw, T) at end 0, at end 1)}, in
    element axes, the element values of the solution. sigma: per shell node.
    """
    tau, vm = [], []
    for pos in wanted:
        index, end = view["origin"][pos][:2]
        beam = view["beams"][index]
        entry = tables[beam["material"]]
        vv, vw, torque = forces[beam["eid"]][end]
        value = shear_at(points[pos], vv, vw,
                         torque + entry["EY"] * vw - entry["EZ"] * vv)
        tau.append(value)
        vm.append(math.sqrt(sigma[pos] ** 2 + 3.0 * value ** 2))
    return tau, vm


def _curvature(s, length, y1, slope1, y2, slope2):
    """Second derivative at s of the Hermite cubic through the end values
    and end slopes."""
    x = s / length
    return ((-6.0 + 12.0 * x) * y1 / length ** 2 +
            (-4.0 + 6.0 * x) * slope1 / length +
            (6.0 - 12.0 * x) * y2 / length ** 2 +
            (-2.0 + 6.0 * x) * slope2 / length)


def stress_from_kinematics(e_mod, beam, d1, theta1, d2, theta2, s, v, w):
    """
    Longitudinal stress at section point (v, w), distance s from end 0, from
    the displacements and rotations of the end nodes; see the file header
    for the formula and its limits. With an element offset the element ends
    move with the arm.
    """
    offset = beam["offset"]
    d1 = point_displacement(d1, theta1, offset)
    d2 = point_displacement(d2, theta2, offset)
    u, vv, ww = beam["frame"]
    length = beam["length"]
    strain = (_dot(d2, u) - _dot(d1, u)) / length
    v2 = _curvature(s, length, _dot(d1, vv), _dot(theta1, ww),
                    _dot(d2, vv), _dot(theta2, ww))
    w2 = _curvature(s, length, _dot(d1, ww), -_dot(theta1, vv),
                    _dot(d2, ww), -_dot(theta2, vv))
    return e_mod * (strain - v2 * v - w2 * w)


def stress_from_forces(normal, moment_v, moment_w, section, v, w):
    """
    Longitudinal stress at section point (v, w) from the section forces at
    an element end (tensileforce, bendingmomv, bendingmomw) and section:
    {"A", "iyy", "izz"}; see the file header.
    """
    return (normal / section["A"] + moment_v * w / section["iyy"] -
            moment_w * v / section["izz"])


def section_values(model_data, material):
    """{"A", "iyy", "izz"} of a material for stress_from_forces, or None.
    IY and IZ in the section dict are Mecway's iyy and izz
    (bridge_from_liml._parse_geometric_props)."""
    geom = model_data.get("mat_geometrics", {}).get(material) or {}
    cara = dict(zip(geom.get("cara", ()), geom.get("vale", ())))
    out = {"A": cara.get("A"), "iyy": cara.get("IY"), "izz": cara.get("IZ")}
    if not all(out.values()):
        return None
    return out


def _young(model_data, material):
    try:
        value = float(model_data.get("materials", {})[material]["E"])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value > 0.0 else None


def _vector(values, nid):
    """Result of a node, or None: solution.node_value gives None on a node
    without a value (measured), so that a component can be None as well."""
    value = values.get(nid)
    if value is None or None in value:
        return None
    return value


def _end_forces(forces, eid):
    """The section forces of a beam, or None when they are not complete."""
    ends = (forces or {}).get(eid)
    if ends is None or None in ends or any(None in e for e in ends):
        return None
    return ends


def shell_values(view, displacements, rotations, model_data, forces=None):
    """
    Values per shell node, in the order of view["nids"], or None (ERROR in
    the log) when a beam end has no result.

    displacements, rotations: {nid: (x, y, z)} of the model nodes, SI.
    forces: optional {beam eid: ((N, Mv, Mw) at end 0, (N, Mv, Mw) at end
    1)}: the element values (solution.element_node_value, k in
    beam["element_nodes"]), not the node values, which are a mean of elements
    in their own axes. A beam without complete forces uses the kinematics.
    Returns {"nids", "displx", "disply", "displz", "displmag",
    "sectionsigma", "stress_routes": {"forces": beams, "kinematics": beams}};
    "sectionsigma" is missing when a drawn beam has neither route (WARNING in
    the log). Only for a linear elastic solution: the caller decides that.
    """
    routes = []
    missing = set()
    for beam in view["beams"]:
        section = section_values(model_data, beam["material"])
        ends = _end_forces(forces, beam["eid"])
        e_mod = _young(model_data, beam["material"])
        if ends is not None and section is not None:
            routes.append((ends, section))
        elif e_mod is not None:
            routes.append(e_mod)
        else:
            missing.add(beam["material"])
    if missing:
        log(tr(u"WARNING: Doorsnede: geen E voor {0}; geen spanning, alleen "
               u"verplaatsing.",
               u"WARNING: Section view: no E for {0}; no stress, only "
               u"displacement.").format(u", ".join(sorted(missing))))
    dofs = []
    for beam in view["beams"]:
        n1, n2 = beam["nodes"]
        ends = (_vector(displacements, n1), _vector(rotations, n1),
                _vector(displacements, n2), _vector(rotations, n2))
        if None in ends:
            log(tr(u"ERROR: Doorsnede: geen resultaat op de knopen {0} en "
                   u"{1} van balk {2}.",
                   u"ERROR: Section view: no result on nodes {0} and {1} "
                   u"of beam {2}.").format(n1, n2, beam["eid"]))
            return None
        dofs.append(ends)
    out = {"nids": list(view["nids"]), "displx": [], "disply": [],
           "displz": [], "displmag": []}
    sigma = []
    for index, end, v, w in view["origin"]:
        beam = view["beams"][index]
        d1, t1, d2, t2 = dofs[index]
        _u, vv, ww = beam["frame"]
        arm = _add(_add(_scale(vv, v), _scale(ww, w)), beam["offset"])
        d = point_displacement(d1 if end == 0 else d2,
                               t1 if end == 0 else t2, arm)
        out["displx"].append(d[0])
        out["disply"].append(d[1])
        out["displz"].append(d[2])
        out["displmag"].append(math.sqrt(_dot(d, d)))
        if not missing:
            route = routes[index]
            if isinstance(route, tuple):
                sigma.append(stress_from_forces(
                    route[0][end][0], route[0][end][1], route[0][end][2],
                    route[1], v, w))
            else:
                sigma.append(stress_from_kinematics(
                    route, beam, d1, t1, d2, t2, beam["length"] * end, v, w))
    if not missing:
        out["sectionsigma"] = sigma
        n_forces = len([r for r in routes if isinstance(r, tuple)])
        out["stress_routes"] = {"forces": n_forces,
                                "kinematics": len(routes) - n_forces}
    return out
