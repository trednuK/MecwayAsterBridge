# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_xfem.py
# Fracture mechanics with XFEM (STAPPENPLAN S6b): a crack that is not in the
# mesh but runs through the elements as level sets. K_I/K_II/K_III and G
# along the front, as with a meshed crack (bridge_fracture.py, S6a), for a
# linear static analysis (lin_static_3d, MECA_STATIQUE). User doc:
# docs/Breukmechanica.md par. 7 (EN: docs/en/Fracture_mechanics.md).
# Compatible with IronPython 2.7.9 (Mecway); the .comm code runs in
# Code-Aster (Python 3).
#
# Input: a line '#ASTER-XFEM' in a free text field of Mecway
# (bridge_custom.py), e.g.
#   #ASTER-XFEM vorm=CIRKEL, centrum=(0, 0, 0), r=0.02, normaal=(0, 0, 1)
#   #ASTER-XFEM vorm=HALFVLAK, front=(0.05, 0, 0), normaal=(0, 1, 0),
#   #ASTER-XFEM     richting=(1, 0, 0)
# A line that starts with 'vorm=' (or 'shape=') starts a new crack;
# the other lines belong to the previous one. Lengths in m (like all #ASTER
# lines) or with a unit ('20 mm'). Keys: _KEYS.
#
# Or a face selection in Mecway with prefix XFEM_
# (e.g. XFEM_A; XFEM is the same in both languages): the faces of
# solid elements in the crack plane (free shape; the crack plane then lies
# on a layer of nodes). bridge_mesh.write_mesh writes them via mesh_cells as
# QUAD4/TRIA3 (normals oriented consistently) in group BRXF<n>S and the edge
# of the face inside the volume (the front) as SEG2 in BRXF<n>F; DEFI_FISS
# GROUP_MA_FISS/GROUP_MA_FOND (catalogue defi_fiss_xfem.py; likewise the
# test cases sslv314b, sslv320d). Those cells are not in the model.
#
# Translation (catalogue Code-Aster 17.4, Cata/Commands):
#   - DEFI_FISS_XFEM (defi_fiss_xfem.py) with DEFI_FISS FORM_FISS='ELLIPSE'/
#     'RECTANGLE'/'DEMI_PLAN', optionally GROUP_MA_ENRI;
#     MODI_MODELE_XFEM (modi_modele_xfem.py) turns the model of the
#     bridge (renamed to model_sain) into the XFEM model 'model'; the loads
#     and MECA_STATIQUE use that model (model_block).
#   - After MECA_STATIQUE (result_block): POST_MAIL_XFEM + POST_CHAM_XFEM give
#     the physical displacement and the stress on a mesh that follows the
#     crack (post_mail_xfem.py, post_cham_xfem.py); PROJ_CHAMP
#     COLLOCATION puts DEPL, SIGM_NOEU and SIEQ_NOEU back on the nodes of
#     the original mesh (every Mecway node is a node of that
#     mesh); REAC_NODA comes from the XFEM result (components DX/DY/DZ).
#     That result is called 'res' again and goes to Mecway as always.
#     With the setting med_export (MED file for ParaView) also
#     IMPR_RESU of res_xvisu (the mesh that follows the crack, DEPL,
#     SIGM_NOEU, SIEQ_NOEU) to <model>_<run_id>_xfem.rmed (UNITE 81):
#     there the opening of the crack can be seen (export_lines).
#   - After the export (k_block): per crack and per front CALC_G_XFEM
#     OPTION='CALC_K_G' (calc_g_xfem.py; THETA R_INF/R_SUP, NB_POINT_FOND,
#     LISSAGE) and POST_K1_K2_K3 FISSURE= (post_k1_k2_k3.py), tables in the
#     .mess and as <model>_<run_id>_xfem.csv; report() puts a summary
#     in the log and the status box.
#
# Measured during development (Code-Aster 17.4, docs/Verificatie.md
# BR-07..10): hex8 and hex20 work (XFEM knows linear and quadratic
# elements; alarm XFEM_63 for quadratic); the front may run through the
# elements and the crack plane may pass through nodes.

import io
import math
import os
import re
from collections import OrderedDict

from bridge_utils import (log, tr, run_name, CONFIG_BRIDGE,
                          get_active_analysis, parse_and_convert,
                          work_dir_path)

# Suffix of the table in the working directory
CSV_SUFFIX = "_xfem.csv"
# MED file for ParaView with the mesh that follows the crack (med_export)
MED_SUFFIX = "_xfem.rmed"
MED_UNIT = 81
# Crack from a face selection: prefix of the Mecway name
# (case-insensitive) and the groups in the mesh (BRXF<n>S crack plane,
# BRXF<n>F front; reserved in bridge_mesh._GENERATED_NAME_RE)
SEL_PREFIX = "XFEM_"
SEL_GROUP = "BRXF"

# Shapes: input name -> own kind. CIRKEL is an ELLIPSE with a = b and a
# normal; HALFVLAK is Code-Aster's DEMI_PLAN (straight front, crack on
# one side of it).
_SHAPES = {
    "ELLIPSE": "ELLIPSE", "ELLIPS": "ELLIPSE",
    "CIRKEL": "CIRKEL", "CIRCLE": "CIRKEL",
    "RECTANGLE": "RECTANGLE", "RECHTHOEK": "RECTANGLE",
    "DEMI_PLAN": "DEMI_PLAN", "HALFVLAK": "DEMI_PLAN",
    "HALF_PLANE": "DEMI_PLAN", "HALFPLANE": "DEMI_PLAN",
}
# Shape -> required keys
_REQUIRED = {
    "ELLIPSE": ("centre", "a", "b", "vect_x", "vect_y"),
    "CIRKEL": ("centre", "r", "normal"),
    "RECTANGLE": ("centre", "a", "b", "vect_x", "vect_y"),
    "DEMI_PLAN": ("point", "normal", "dtan"),
}
# Curved front (no curvature correction in CALC_G_XFEM, see _warn_curved)
_CURVED = ("ELLIPSE", "CIRKEL")

_KEYS = OrderedDict([
    # key -> (kind, synonyms)
    ("shape", ("txt", ("vorm", "shape", "form_fiss"))),
    ("centre", ("vec", ("centrum", "centre", "center"))),
    ("a", ("len", ("a", "demi_grand_axe"))),
    ("b", ("len", ("b", "demi_petit_axe"))),
    ("r", ("len", ("r", "straal", "radius"))),
    ("vect_x", ("dir", ("vect_x",))),
    ("vect_y", ("dir", ("vect_y",))),
    ("normal", ("dir", ("normaal", "normal", "normale"))),
    ("point", ("vec", ("front", "pfon", "punt", "point"))),
    ("dtan", ("dir", ("richting", "direction", "dtan"))),
    ("fillet", ("len", ("afronding", "fillet", "rayon_conge"))),
    ("group", ("sel", ("groep", "group"))),
    ("name", ("txt", ("naam", "name"))),
    ("points", ("int", ("punten", "points", "nb_point_fond"))),
    ("smoothing", ("txt", ("glad", "smoothing", "lissage"))),
    ("degree", ("int", ("graad", "degree", "degre"))),
    ("r_inf", ("len", ("r_inf",))),
    ("r_sup", ("len", ("r_sup",))),
])
_ALIAS = dict((a, k) for k, (_s, names) in _KEYS.items() for a in names)
_SEL_RE = re.compile(r"^<<([^<>]+)>>$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,16}$")

# Solid elements that Code-Aster's XFEM knows (linear and quadratic;
# hex8 and hex20 measured, the rest NOT verified)
_XFEM_TYPES = ("HEXA", "PENTA", "PYRAM", "TETRA")

# Mesh advice: WARNING if the elements at the front are larger than
# crack size / _H_RATIO (crack size = smallest semi-axis or radius).
# Measured (BR-08, circular crack, hex8): see docs/Breukmechanica.md par. 7.4.
_H_RATIO = 10.0


# ==========================================
# READING
# ==========================================
def _split(body):
    """Pieces 'key = value' separated by commas outside parentheses."""
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _length(text):
    """Length in m: a number (SI) or a number with a unit ('20 mm')."""
    text = text.strip()
    if re.match(r"^[-+]?[0-9.]+(?:[eE][-+]?[0-9]+)?$", text):
        return float(text)
    if not re.match(r"^[-+]?[0-9.]", text):
        raise ValueError(text)
    return float(parse_and_convert(text, "length"))


def _vector(raw, as_length):
    """'(x, y, z)' or '(x, y, z) mm' -> tuple of three floats."""
    raw = raw.strip()
    unit = ""
    if raw.startswith("(") and ")" in raw:
        unit = raw[raw.rindex(")") + 1:].strip()
        raw = raw[:raw.rindex(")") + 1]
    if not (raw.startswith("(") and raw.endswith(")")):
        raise ValueError(raw)
    vals = []
    for x in raw[1:-1].split(","):
        x = x.strip()
        if as_length:
            vals.append(_length(x + (" " + unit if unit else "")))
        else:
            vals.append(float(x))
    if len(vals) != 3:
        raise ValueError(raw)
    return tuple(vals)


def group_lines(bodies):
    """Merge #ASTER-XFEM lines into cracks: a line that starts with
    'vorm=' (or 'shape=') starts a new crack."""
    cracks = []
    for body in bodies:
        text = body.strip().rstrip(",")
        if not text:
            continue
        key = text.split("=", 1)[0].strip().lower()
        if _ALIAS.get(key) == "shape" or not cracks:
            cracks.append([])
        cracks[-1].append(text)
    return [", ".join(c) for c in cracks]


def parse_specs(bodies):
    """
    [spec] from the #ASTER-XFEM lines; spec = dict with the keys of
    _KEYS (numbers in SI, vectors as tuple, selections as Mecway name).
    None (with ERROR in the log) on an error.
    """
    specs = []
    names = set()
    for k, text in enumerate(group_lines(bodies)):
        spec = {"index": k + 1, "text": text}
        for part in _split(text):
            key, sep, raw = part.partition("=")
            key = key.strip().lower()
            raw = raw.strip()
            name = _ALIAS.get(key)
            if not sep or name is None:
                log(tr("ERROR: #ASTER-XFEM: onbekend of onvolledig '{0}'. "
                       "Bekend: {1}.",
                       "ERROR: #ASTER-XFEM: unknown or incomplete '{0}'. "
                       "Known: {1}.").format(part, ", ".join(sorted(_ALIAS))))
                return None
            kind = _KEYS[name][0]
            try:
                if kind == "len":
                    spec[name] = _length(raw)
                elif kind == "vec":
                    spec[name] = _vector(raw, True)
                elif kind == "dir":
                    spec[name] = _vector(raw, False)
                elif kind == "int":
                    spec[name] = int(raw)
                elif kind == "sel":
                    m = _SEL_RE.match(raw)
                    if not m:
                        raise ValueError(raw)
                    spec[name] = m.group(1).strip()
                else:
                    if not raw:
                        raise ValueError(raw)
                    spec[name] = raw.strip("'\"")
            except ValueError:
                log(tr("ERROR: #ASTER-XFEM: '{0}' heeft geen geldige waarde "
                       "({1}).",
                       "ERROR: #ASTER-XFEM: '{0}' has no valid value "
                       "({1}).").format(key, {
                           "len": tr("lengte in m of met eenheid",
                                     "length in m or with a unit"),
                           "vec": "(x, y, z)", "dir": "(dx, dy, dz)",
                           "int": tr("geheel getal", "integer"),
                           "sel": "<<Mecway-selectie>>",
                           "txt": tr("tekst", "text")}[kind]))
                return None
        if not _complete(spec):
            return None
        if spec["name"] in names:
            log(tr("ERROR: #ASTER-XFEM: twee scheuren met naam '{0}'.",
                   "ERROR: #ASTER-XFEM: two cracks named '{0}'.").format(
                       spec["name"]))
            return None
        names.add(spec["name"])
        specs.append(spec)
    return specs


def _complete(spec):
    """Checks and default values of a crack; False (ERROR) on an
    error. Fills spec["form"] (Code-Aster shape) and the axes."""
    k = spec["index"]

    def err(nl, en):
        log(tr("ERROR: #ASTER-XFEM (scheur {0}): " + nl,
               "ERROR: #ASTER-XFEM (crack {0}): " + en).format(k))
        return False
    shape = _SHAPES.get(str(spec.get("shape", "")).upper())
    if shape is None:
        return err("geef de vorm: vorm=ELLIPSE, CIRKEL, RECHTHOEK of "
                   "HALFVLAK.",
                   "give the shape: shape=ELLIPSE, CIRCLE, RECTANGLE or "
                   "HALF_PLANE.")
    spec["kind"] = shape
    missing = [key for key in _REQUIRED[shape] if key not in spec]
    if missing:
        return err("ontbreekt bij {0}: {1}.".format(
            shape, ", ".join(_KEYS[m][1][0] for m in missing)),
            "missing for {0}: {1}.".format(
            shape, ", ".join(_KEYS[m][1][1] for m in missing)))
    for key in ("a", "b", "r"):
        if key in spec and spec[key] <= 0.0:
            return err("{0} moet > 0 zijn.".format(key),
                       "{0} must be > 0.".format(key))
    for key in ("vect_x", "vect_y", "normal", "dtan"):
        if key in spec:
            if _norm(spec[key]) <= 0.0:
                return err("{0} is een nulvector.".format(key),
                           "{0} is a zero vector.".format(key))
            spec[key] = _unit(spec[key])
    if shape == "CIRKEL":
        ex, ey = _plane_axes(spec["normal"])
        spec.update({"form": "ELLIPSE", "a": spec["r"], "b": spec["r"],
                     "vect_x": ex, "vect_y": ey})
    else:
        spec["form"] = shape
    if spec["form"] in ("ELLIPSE", "RECTANGLE"):
        if abs(_dot(spec["vect_x"], spec["vect_y"])) > 1.0e-3:
            return err("vect_x en vect_y staan niet loodrecht op elkaar.",
                       "vect_x and vect_y are not perpendicular.")
        spec["normal"] = _unit(_cross(spec["vect_x"], spec["vect_y"]))
    if spec["form"] == "DEMI_PLAN":
        if abs(_dot(spec["normal"], spec["dtan"])) > 1.0e-3:
            return err("richting (de groeirichting van het front, in het "
                       "scheurvlak) moet loodrecht op de normaal staan.",
                       "direction (the growth direction of the front, in "
                       "the crack plane) must be perpendicular to the "
                       "normal.")
    if spec.get("fillet") is not None and spec["form"] != "RECTANGLE":
        return err("afronding hoort alleen bij RECHTHOEK.",
                   "fillet only belongs to RECTANGLE.")
    if spec.get("fillet", 0.0) < 0.0:
        return err("afronding moet >= 0 zijn.", "fillet must be >= 0.")
    name = spec.get("name") or str(k)
    if not _NAME_RE.match(name):
        return err("naam '{0}': alleen letters, cijfers en _ (max. 16)."
                   .format(name),
                   "name '{0}': only letters, digits and _ (max. 16)."
                   .format(name))
    spec["name"] = name
    smooth = spec.get("smoothing")
    if smooth is None:
        # Default (measured during development, docs/Breukmechanica.md
        # par. 7.3): LAGRANGE for a straight front (the front points are then
        # evenly spaced), LEGENDRE for a curved front (irregular
        # intersections with the element faces: LAGRANGE oscillates there).
        smooth = "LEGENDRE" if shape in _CURVED else "LAGRANGE"
    smooth = smooth.upper()
    if smooth not in ("LEGENDRE", "LAGRANGE"):
        return err("glad={0}: kies LEGENDRE of LAGRANGE.".format(smooth),
                   "smoothing={0}: choose LEGENDRE or LAGRANGE.".format(
                       smooth))
    spec["smoothing"] = smooth
    if spec.get("degree") is not None and not 0 <= spec["degree"] <= 7:
        return err("graad {0}: toegestaan 0 .. 7.".format(spec["degree"]),
                   "degree {0}: allowed 0 .. 7.".format(spec["degree"]))
    if spec.get("points") is not None and spec["points"] < 2:
        return err("punten moet >= 2 zijn.", "points must be >= 2.")
    return True


def specs(model_data):
    """Cracks from model_data["aster_custom"]["xfem"] (cached), [] without,
    None on an error."""
    if "_xfem_specs" in model_data:
        return model_data["_xfem_specs"]
    bodies = (model_data.get("aster_custom") or {}).get("xfem") or []
    out = parse_specs(bodies) if bodies else []
    model_data["_xfem_specs"] = out
    return out


def is_requested(model_data):
    """True if the model has #ASTER-XFEM lines or XFEM_ face
    selections."""
    return bool((model_data.get("aster_custom") or {}).get("xfem") or
                selection_names(model_data))


def selection_names(model_data):
    """Mecway names of the face selections with prefix XFEM_
    (case-insensitive), in the order of the .liml."""
    return [n for n in model_data.get("face_selection_faces", {})
            if n.upper().startswith(SEL_PREFIX) and len(n) > len(SEL_PREFIX)]


def active_here():
    """True if the active analysis is linear static (MECA_STATIQUE)."""
    try:
        return get_active_analysis().get("solver_command") == "MECA_STATIQUE"
    except KeyError:
        return False


# ==========================================
# GEOMETRY (level sets as Code-Aster builds them for the shape)
# ==========================================
def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    n = _norm(a)
    return tuple(c / n for c in a)


def _plane_axes(normal):
    """Two perpendicular unit vectors in the plane with this normal: the
    global axis least aligned with the normal, projected (fixed
    choice, so that the same input gives the same axes)."""
    n = _unit(normal)
    axes = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    e = min(axes, key=lambda v: abs(_dot(v, n)))
    ex = _unit([e[i] - _dot(e, n) * n[i] for i in range(3)])
    ey = _unit(_cross(n, ex))
    return ex, ey


def levelsets(spec, p):
    """(lsn, lst) of point p: lsn = distance to the crack plane, lst < 0
    inside the crack (> 0 outside it). Approximation of what DEFI_FISS_XFEM
    builds; only the sign is used (do the crack and the
    front cut elements?)."""
    if spec["form"] == "DEMI_PLAN":
        d = _sub(p, spec["point"])
        return _dot(d, spec["normal"]), _dot(d, spec["dtan"])
    d = _sub(p, spec["centre"])
    lsn = _dot(d, spec["normal"])
    u, v = _dot(d, spec["vect_x"]), _dot(d, spec["vect_y"])
    a, b = spec["a"], spec["b"]
    if spec["form"] == "ELLIPSE":
        return lsn, (math.sqrt((u / a) ** 2 + (v / b) ** 2) - 1.0) * min(a, b)
    return lsn, max(abs(u) - a, abs(v) - b)


def crack_size(spec):
    """Smallest dimension of the crack (semi-axis or radius), or None
    (HALFVLAK: no dimension of its own)."""
    if spec["form"] in ("DEMI_PLAN", "MAILLAGE"):
        return None
    return min(spec["a"], spec["b"])


def _cut_elements(model_data, spec, conn):
    """(cut elements, front elements, element size at the front).
    Cut: lsn changes sign over the corner nodes and at least one
    corner node lies inside the crack (lst < 0); front: in addition lst is
    >= 0 somewhere (a front on an element boundary, lst = 0 in the nodes,
    counts)."""
    nodes = model_data.get("mesh_nodes", {})
    import bridge_fracture
    cut, front, h = [], [], 0.0
    for eid in sorted(conn):
        atype, cn = conn[eid]
        base = None
        for prefix in _XFEM_TYPES:
            if atype.startswith(prefix):
                base = prefix
        if base is None:
            continue
        corners = cn[:bridge_fracture._CORNERS[base]]
        ls = [levelsets(spec, nodes[n]) for n in corners]
        lsn = [x[0] for x in ls]
        lst = [x[1] for x in ls]
        if not (min(lsn) <= 0.0 <= max(lsn)) or min(lst) >= 0.0:
            continue
        cut.append(eid)
        if max(lst) >= 0.0:
            front.append(eid)
            # Size perpendicular to the front (the directions that matter
            # for K): the range of lsn and lst over the corner nodes
            # (both are distances, or approximately so for the ellipse)
            h = max(h, max(lsn) - min(lsn), max(lst) - min(lst))
    return cut, front, h


# ==========================================
# CRACK FROM A FACE SELECTION (XFEM_<name>)
# ==========================================
def _volume_base(atype):
    """Volume type (HEXA, PENTA, PYRAM, TETRA) of a Code-Aster type, or
    None."""
    for prefix in _XFEM_TYPES:
        if atype.startswith(prefix):
            return prefix
    return None


def _ring(corners):
    return list(zip(corners, corners[1:] + corners[:1]))


def _skin_edges(conn):
    """Edges (frozenset of two corner nodes) of the outside of the
    volume: of the faces that belong to exactly one solid element."""
    import bridge_mesh
    counts = {}
    for eid in conn:
        atype, cn = conn[eid]
        base = _volume_base(atype)
        if base is None:
            continue
        for corners in bridge_mesh._FACE_CORNERS[base].values():
            face = [cn[i] for i in corners]
            key = frozenset(face)
            counts[key] = (counts.get(key, (0, face))[0] + 1, face)
    edges = set()
    for n, face in counts.values():
        if n == 1:
            edges.update(frozenset(e) for e in _ring(face))
    return edges


def _orient(faces, nodes):
    """Orients the faces (lists of corner nodes) consistently: two neighbouring
    faces traverse their shared edge in opposite directions. Then per
    connected piece a fixed choice, so that the same crack always gets the
    same normal, whichever side the user chose: the normal of the
    level set (LNNO > 0 on that side) has its largest component positive.
    Measured (Code-Aster 17.4, LNNO/LTNO with CREA_CHAMP EXTR compared with
    DEMI_PLAN): LNNO lies on the side opposite to the right-handed
    normal of the node order of the cells; therefore the sum of the
    face normals (Newell) is made negative here. With normal +y, LNNO and
    LTNO of BR-13 equal those of BR-09 (HALFVLAK, normal +y). Why
    a fixed choice: with a crack plane on a layer of nodes (level set 0 in
    those nodes) the solution depends slightly on the normal; with the other
    normal the upper lip in BR-13 opened 1.8 % further than the lower lip
    (K equal within 0.05 %).
    Returns (faces, error) with error "vertakt" (an edge in more than two
    faces) or None."""
    by_edge = {}
    for i, f in enumerate(faces):
        for e in _ring(f):
            by_edge.setdefault(frozenset(e), []).append(i)
    if any(len(v) > 2 for v in by_edge.values()):
        return faces, "vertakt"
    out = list(faces)
    done = set()
    for start in range(len(faces)):
        if start in done:
            continue
        done.add(start)
        todo = [start]
        piece = [start]
        while todo:
            i = todo.pop()
            for a, b in _ring(out[i]):
                for j in by_edge[frozenset((a, b))]:
                    if j in done:
                        continue
                    # the neighbouring face must traverse the edge as (b, a)
                    if (a, b) in _ring(out[j]):
                        out[j] = list(reversed(out[j]))
                    done.add(j)
                    todo.append(j)
                    piece.append(j)
        normal = [0.0, 0.0, 0.0]
        for i in piece:
            for a, b in _ring(out[i]):
                pa, pb = nodes[a], nodes[b]
                for c, (p, q) in enumerate(((1, 2), (2, 0), (0, 1))):
                    normal[c] += (pa[p] - pb[p]) * (pa[q] + pb[q])
        big = max(range(3), key=lambda c: abs(normal[c]))
        if normal[big] > 0.0:
            for i in piece:
                out[i] = list(reversed(out[i]))
    return out, None


def _front_pieces(edges):
    """Edges (a, b) of the front as connected pieces: [[nodes]]
    along the line (a branch ends a piece)."""
    nbr = {}
    for a, b in edges:
        nbr.setdefault(a, set()).add(b)
        nbr.setdefault(b, set()).add(a)
    seen = set()
    pieces = []
    ends = sorted(n for n in nbr if len(nbr[n]) == 1)
    for start in ends + sorted(nbr):
        if start in seen:
            continue
        line = [start]
        seen.add(start)
        cur = start
        while True:
            nxt = sorted(n for n in nbr[cur] if n not in seen)
            if not nxt:
                break
            cur = nxt[0]
            seen.add(cur)
            line.append(cur)
        pieces.append(line)
    return pieces


def mesh_cells(model_data, conn, faces_of=None):
    """
    Cells of the cracks from XFEM_ face selections for
    bridge_mesh.write_mesh: per crack the crack plane as QUAD4/TRIA3
    (corner nodes; normals oriented consistently, _orient) in group BRXF<n>S
    and the front as SEG2 in BRXF<n>F. Front = the edge of the face that does
    not lie on the outside of the volume (an edge on a free surface or
    a symmetry plane is the mouth of the crack). Linear cells also for
    quadratic elements: DEFI_FISS_XFEM only computes distances with them
    (level sets; NOT verified in the Fortran source, but measured: BR-13).
    faces_of(eid, fid) -> nodes of the face (Mecway API), else the
    table bridge_mesh._FACE_CORNERS. Fills model_data["_xfem_sel_specs"]
    (cracks for model_block).

    Returns OrderedDict {group: [(type, [nodes])]} ({} without XFEM_
    selections or in another analysis), None on an error (ERROR).
    """
    import bridge_fracture
    import bridge_mesh
    model_data["_xfem_sel_specs"] = []
    out = OrderedDict()
    if not active_here():
        return out
    for kind, key in (("node", "node_groups"),
                      ("element", "element_selections")):
        wrong = [n for n in model_data.get(key, {})
                 if n.upper().startswith(SEL_PREFIX)]
        if wrong:
            log(tr("WARNING: XFEM: '{0}' is een {1}; alleen een "
                   "vlakselectie met voorvoegsel XFEM_ is een scheur "
                   "(docs/Breukmechanica.md par. 7.8).",
                   "WARNING: XFEM: '{0}' is a {1}; only a face selection "
                   "with prefix XFEM_ is a crack "
                   "(docs/en/Fracture_mechanics.md par. 7.8).").format(
                       wrong[0], tr("knoopselectie", "node selection")
                       if kind == "node" else tr("elementselectie",
                                                 "element selection")))
    names = selection_names(model_data)
    if not names:
        return out
    nodes = model_data.get("mesh_nodes", {})
    skin = _skin_edges(conn)
    for k, sel in enumerate(names):
        def err(nl, en):
            log(tr("ERROR: XFEM-scheur '{0}': " + nl,
                   "ERROR: XFEM crack '{0}': " + en).format(sel))
            return None
        faces, keys = [], set()
        for eid, fid in model_data["face_selection_faces"][sel]:
            if eid not in conn or _volume_base(conn[eid][0]) is None:
                return err("vlak {0} van element {1} is geen vlak van een "
                           "volume-element.".format(fid, eid),
                           "face {0} of element {1} is not a face of a "
                           "solid element.".format(fid, eid))
            atype, cn = conn[eid]
            nc = bridge_fracture._CORNERS[_volume_base(atype)]
            fn = (faces_of(eid, fid) if faces_of is not None else
                  bridge_mesh._face_from_table(atype, cn, fid)) or []
            corners = [n for n in fn if n in cn[:nc]]
            key = frozenset(corners)
            if len(corners) < 3 or key in keys:
                continue      # the same face selected from both sides
            keys.add(key)
            faces.append(corners)
        if not faces:
            return err("de selectie heeft geen vlakken.",
                       "the selection has no faces.")
        faces, problem = _orient(faces, nodes)
        if problem:
            return err("een rib hoort bij meer dan twee vlakken (vertakt "
                       "scheurvlak); XFEM kent per scheur een vlak zonder "
                       "vertakking. Maak er meer XFEM_-selecties van.",
                       "an edge belongs to more than two faces (branched "
                       "crack surface); XFEM knows one surface per crack "
                       "without branches. Make several XFEM_ selections.")
        count = {}
        for f in faces:
            for e in _ring(f):
                count[frozenset(e)] = count.get(frozenset(e), 0) + 1
        front = [e for f in faces for e in _ring(f)
                 if count[frozenset(e)] == 1 and frozenset(e) not in skin]
        crack_nodes = set(n for f in faces for n in f)
        front_keys = set(frozenset(e) for e in front)
        # Elements at the crack (message) and at the front (message,
        # element size); nodes of the elements that touch the crack plane
        # (oblique conditions, warn_oblique)
        cut, front_eids, h, cut_nodes = [], [], 0.0, set()
        for eid in sorted(conn):
            atype, cn = conn[eid]
            base = _volume_base(atype)
            if base is None:
                continue
            corners = cn[:bridge_fracture._CORNERS[base]]
            cs = set(corners)
            if not cs & crack_nodes:
                continue
            cut_nodes.update(cn)
            if any(key <= cs for key in keys):
                cut.append(eid)
            if any(key <= cs for key in front_keys):
                front_eids.append(eid)
                for p, q in bridge_fracture._EDGES[base]:
                    h = max(h, _norm(_sub(nodes[corners[p]],
                                          nodes[corners[q]])))
        pieces = _front_pieces(front)
        curved = any(bridge_fracture.front_shape(
            [nodes[n] for n in piece])[0] != "recht" for piece in pieces)
        name = re.sub(r"[^A-Za-z0-9_]", "_", sel[len(SEL_PREFIX):])[:16]
        group = "{0}{1}".format(SEL_GROUP, k + 1)
        spec = {"index": "'{0}'".format(sel), "text": "<<{0}>>".format(sel),
                "name": name, "kind": "SELECTIE", "form": "MAILLAGE",
                "selection": sel, "fiss_group": group + "S",
                "front_group": group + "F", "curved": curved,
                # Default as for the shapes (_complete): LAGRANGE for
                # a straight front, LEGENDRE for a curved front
                "smoothing": "LEGENDRE" if curved else "LAGRANGE",
                "cut": cut, "front_eids": front_eids, "h_front": h,
                "cut_nodes": cut_nodes}
        model_data["_xfem_sel_specs"].append(spec)
        out[spec["fiss_group"]] = [
            ("TRIA3" if len(f) == 3 else "QUAD4", f) for f in faces]
        if front:
            out[spec["front_group"]] = [("SEG2", list(e)) for e in front]
        log("INFO: XFEM, crack {0} from face selection '{1}': {2} faces, "
            "front {3} edges in {4} piece(s) ({5}), groups {6}/{7}."
            .format(name, sel, len(faces), len(front), len(pieces),
                    "gekromd" if curved else "recht", spec["fiss_group"],
                    spec["front_group"]))
    return out


# ==========================================
# .COMM: MODEL
# ==========================================
def _fmt(v):
    return "{0!r}".format(float(v))


def _tup(v):
    return "(" + ", ".join(_fmt(c) for c in v) + ")"


def _defi_fiss(spec):
    """Text of DEFI_FISS=_F(...) (catalogue defi_fiss_xfem.py)."""
    f = spec["form"]
    if f == "MAILLAGE":
        # Crack plane and front as cells in the mesh (mesh_cells)
        return "_F(GROUP_MA_FISS='{0}', GROUP_MA_FOND='{1}')".format(
            spec["fiss_group"], spec["front_group"])
    if f == "DEMI_PLAN":
        return ("_F(FORM_FISS='DEMI_PLAN', PFON={0}, NORMALE={1},\n"
                "                     DTAN={2})").format(
                    _tup(spec["point"]), _tup(spec["normal"]),
                    _tup(spec["dtan"]))
    extra = ""
    if f == "RECTANGLE" and spec.get("fillet"):
        extra = ", RAYON_CONGE={0}".format(_fmt(spec["fillet"]))
    return ("_F(FORM_FISS='{0}', DEMI_GRAND_AXE={1}, DEMI_PETIT_AXE={2}{3},\n"
            "                     CENTRE={4}, VECT_X={5},\n"
            "                     VECT_Y={6})").format(
                f, _fmt(spec["a"]), _fmt(spec["b"]), extra,
                _tup(spec["centre"]), _tup(spec["vect_x"]),
                _tup(spec["vect_y"]))


def _check_model(model_data):
    """Solid elements with MODELISATION='3D' only (XFEM in Code-Aster;
    the results go back via a 3D auxiliary model, result_block). ERROR and
    False otherwise."""
    import bridge_mesh
    shapes = model_data.get("elem_shapes", {})
    other = sorted(set(s for s in shapes.values()
                       if s not in bridge_mesh._SOLID_SHAPES))
    if other:
        log(tr("ERROR: #ASTER-XFEM werkt alleen in een model met alleen "
               "volume-elementen; dit model heeft ook {0}. Modelleer het "
               "deel met de scheur in volume-elementen, of gebruik een "
               "gemeshte scheur (SCHEUR_-selecties).",
               "ERROR: #ASTER-XFEM only works in a model with only solid "
               "elements; this model also has {0}. Model the part with the "
               "crack in solid elements, or use a meshed crack (CRACK_ "
               "selections).").format(", ".join(other)))
        return False
    mods = sorted(set(m for m in model_data.get(
        "elset_modelisations", {}).values() if m != "3D"))
    if mods or model_data.get("poi1_groups") or model_data.get("discretes"):
        log(tr("ERROR: #ASTER-XFEM: XFEM kent alleen MODELISATION '3D' "
               "(hier ook {0}). Zet elem_hex8 op '3D' of 'LINE_QUAD' "
               "(pagina Elementen) en gebruik geen losse knopen of veren.",
               "ERROR: #ASTER-XFEM: XFEM only knows MODELISATION '3D' "
               "(here also {0}). Set elem_hex8 to '3D' or 'LINE_QUAD' "
               "(Elements page) and use no loose nodes or springs.").format(
                   ", ".join(mods) or tr("losse knopen/veren",
                                         "loose nodes/springs")))
        return False
    return True


def model_block(model_data, analysis, block):
    """
    AFFE_MODELE of the bridge (block) with the XFEM cracks: the sound
    model is called model_sain, then DEFI_FISS_XFEM per crack and
    model = MODI_MODELE_XFEM. block unchanged without #ASTER-XFEM (or in
    another analysis); None on an error (ERROR in the log). Checks
    the model and the position of every crack in the mesh.
    """
    model_data["xfem"] = []
    if not is_requested(model_data):
        return block
    if not active_here():
        return block      # generate_AsterSolver_files reports it (WARNING)
    cracks = specs(model_data)
    if cracks is None:
        return None
    # Cracks from XFEM_ face selections (bridge_mesh.write_mesh ->
    # mesh_cells); the names must stay unique
    cracks = cracks + model_data.get("_xfem_sel_specs", [])
    seen = set()
    for c in cracks:
        if c["name"] in seen:
            log(tr("ERROR: XFEM: twee scheuren met naam '{0}' (#ASTER-XFEM "
                   "naam= of XFEM_<naam>).",
                   "ERROR: XFEM: two cracks named '{0}' (#ASTER-XFEM name= "
                   "or XFEM_<name>).").format(c["name"]))
            return None
        seen.add(c["name"])
    if not _check_model(model_data):
        return None
    if "model = AFFE_MODELE(" not in block:
        log("ERROR: XFEM: AFFE_MODELE van de bridge niet gevonden.")
        return None
    conn = model_data.get("_conn") or {}
    renames = model_data.get("selection_renames", {})
    elsel = model_data.get("element_selections", {})
    lines = ["", "# " + "=" * 53,
             "# XFEM CRACKS (bridge: #ASTER-XFEM, bridge_xfem.py,",
             "# docs/Breukmechanica.md par. 7): level sets in the sound",
             "# model, then the XFEM model 'model' for loads and solve",
             "# " + "=" * 53]
    names = []
    cut_nodes = set()
    for c in cracks:
        if c["form"] == "MAILLAGE":
            cut, front, h = c["cut"], c["front_eids"], c["h_front"]
            cut_nodes.update(c["cut_nodes"])
        else:
            cut, front, h = _cut_elements(model_data, c, conn)
        for eid in cut:
            cut_nodes.update(conn[eid][1])
        if not cut:
            log(tr("ERROR: #ASTER-XFEM (scheur {0}): de scheur snijdt geen "
                   "enkel volume-element. Ligt hij in het model? Coordinaten "
                   "en lengtes zijn in m (of geef een eenheid, bijv. "
                   "'r=20 mm').",
                   "ERROR: #ASTER-XFEM (crack {0}): the crack cuts no solid "
                   "element. Is it inside the model? Coordinates and "
                   "lengths are in m (or give a unit, e.g. 'r=20 mm')."
                   ).format(c["name"]))
            return None
        if not front and c["form"] == "MAILLAGE":
            log(tr("ERROR: XFEM-scheur '{0}': de vlakselectie heeft geen "
                   "rand binnen het volume (geen front): de scheur snijdt "
                   "het model helemaal door, of de vlakken liggen op de "
                   "buitenkant. Selecteer de vlakken in het scheurvlak "
                   "binnen het model (docs/Breukmechanica.md par. 7.8).",
                   "ERROR: XFEM crack '{0}': the face selection has no "
                   "edge inside the solid (no front): the crack cuts all "
                   "the way through the model, or the faces are on the "
                   "outside. Select the faces in the crack plane inside the "
                   "model (docs/en/Fracture_mechanics.md par. 7.8).").format(
                       c["selection"]))
            return None
        if not front:
            log(tr("ERROR: #ASTER-XFEM (scheur {0}): het front ligt buiten "
                   "het model (de scheur snijdt het model helemaal door); "
                   "dan zijn er geen K en G. Maak de scheur kleiner dan het "
                   "model; coordinaten en lengtes zijn in m (of geef een "
                   "eenheid).",
                   "ERROR: #ASTER-XFEM (crack {0}): the front lies outside "
                   "the model (the crack cuts all the way through the "
                   "model); there are then no K and G. Make the crack "
                   "smaller than the model; coordinates and lengths are in "
                   "m (or give a unit).").format(c["name"]))
            return None
        size = crack_size(c)
        c["h_front"] = h
        log("INFO: XFEM, crack {0} ({1}): {2} cut elements, of which "
            "{3} at the front (element size normal to the front {4:.4g} "
            "m{5}).".format(
                c["name"], c["kind"], len(cut), len(front), h,
                "" if size is None else ", scheurmaat {0:.4g} m".format(size)))
        if size is not None and h > size / _H_RATIO:
            log(tr("WARNING: #ASTER-XFEM (scheur {0}): de elementen aan het "
                   "front ({1:.3g} m) zijn groter dan 1/{2:g} van de "
                   "scheurmaat ({3:.3g} m); K en G worden dan onnauwkeurig "
                   "(docs/Breukmechanica.md par. 7.4). Verfijn het mesh rond "
                   "het front.",
                   "WARNING: #ASTER-XFEM (crack {0}): the elements at the "
                   "front ({1:.3g} m) are larger than 1/{2:g} of the crack "
                   "size ({3:.3g} m); K and G then become inaccurate "
                   "(docs/en/Fracture_mechanics.md par. 7.4). Refine the "
                   "mesh around the front.").format(
                       c["name"], h, _H_RATIO, size))
        enri = ""
        if c.get("group"):
            if c["group"] not in elsel:
                log(tr("ERROR: #ASTER-XFEM (scheur {0}): groep '{1}' is geen "
                       "elementselectie van het model.",
                       "ERROR: #ASTER-XFEM (crack {0}): group '{1}' is not "
                       "an element selection of the model.").format(
                           c["name"], c["group"]))
                return None
            enri = ",\n    GROUP_MA_ENRI='{0}'".format(
                renames.get(c["group"], c["group"]))
        i = len(names) + 1
        c["concept"] = "fiss_{0}".format(i)
        names.append(c["concept"])
        lines += [
            "# Crack {0}: {1}".format(c["name"], c["text"]),
            "{0} = DEFI_FISS_XFEM(".format(c["concept"]),
            "    MAILLAGE=mesh,",
            "    TYPE_DISCONTINUITE='FISSURE',",
            "    DEFI_FISS={0}{1},".format(_defi_fiss(c), enri),
            ")",
        ]
        model_data["xfem"].append(c)
    model_data["xfem_cut_nodes"] = cut_nodes
    lines += [
        "model = MODI_MODELE_XFEM(MODELE_IN=model_sain, FISSURE=({0},))"
        .format(", ".join(names)), ""]
    return (block.replace("model = AFFE_MODELE(", "model_sain = AFFE_MODELE(",
                          1) + "\n".join(lines))


def axis_ddl(angl, ddls, values):
    """
    Symmetry/oblique condition (LIAISON_OBLIQUE with local x = the
    normal, nautical angles angl) along a global axis: (component,
    value) for DDL_IMPO, else None. Only an entry with only 'DX'
    (solid nodes). Why: with an XFEM model DDL_IMPO also fixes the
    Heaviside degrees of freedom of the nodes of cut elements
    (both lips), LIAISON_OBLIQUE only the classic DX/DY/DZ; measured
    forma07b (BR-11): K1 at the symmetry plane with LIAISON_OBLIQUE +3.8 %,
    with DDL_IMPO equal to the test case.
    """
    if tuple(ddls) != ("DX",):
        return None
    a, b = math.radians(angl[0]), math.radians(angl[1])
    x = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), -math.sin(b))
    for i, comp in enumerate(("DX", "DY", "DZ")):
        if abs(abs(x[i]) - 1.0) < 1.0e-9:
            sign = 1.0 if x[i] > 0.0 else -1.0
            return comp, sign * float((values or {}).get("DX", 0.0))
    return None


def warn_oblique(model_data, selection, group):
    """WARNING (once per selection) if the node group of an oblique
    condition has nodes of cut elements: there it does not act on the
    XFEM degrees of freedom with XFEM."""
    nids = set((model_data.get("extra_node_groups") or {}).get(group, ()))
    if not nids & model_data.get("xfem_cut_nodes", set()):
        return
    warned = model_data.setdefault("_xfem_warned_oblique", set())
    if selection in warned:
        return
    warned.add(selection)
    log(tr("WARNING: #ASTER-XFEM: de voorwaarde op '{0}' staat schuin "
           "(LIAISON_OBLIQUE) en legt op knopen van elementen die de scheur "
           "snijdt de XFEM-vrijheidsgraden niet vast (gemeten aan een "
           "symmetrievlak: K +3,8 %). Laat de scheur dat vlak niet raken, "
           "of leg het vlak langs een globale as (dan DDL_IMPO).",
           "WARNING: #ASTER-XFEM: the constraint on '{0}' is oblique "
           "(LIAISON_OBLIQUE) and does not fix the XFEM degrees of freedom "
           "on nodes of elements cut by the crack (measured at a symmetry "
           "plane: K +3.8 %). Keep the crack away from that plane, or align "
           "the plane with a global axis (then DDL_IMPO).").format(selection))


# ==========================================
# .COMM: RESULTS TO THE ORIGINAL MESH
# ==========================================
_RESULT_BLOCK = """
# =====================================================
# XFEM: resultaten op het oorspronkelijke mesh (bridge_xfem.result_block)
# De verplaatsing van het XFEM-model heeft extra vrijheidsgraden (H1X..,
# K1..) en is op een knoop van een gesneden element niet de fysische
# verplaatsing. POST_MAIL_XFEM maakt een mesh dat de scheur volgt,
# POST_CHAM_XFEM zet DEPL en SIEF_ELGA daarop; elke knoop van het
# oorspronkelijke mesh is een knoop van dat mesh, dus PROJ_CHAMP
# COLLOCATION geeft de waarde aan de eigen kant van de scheur. Het
# hulpmodel krijgt alleen de volume-elsets (het mesh van POST_MAIL_XFEM houdt
# de groepen; zijn frontcellen en randen zonder volume gaven alarm
# MODELE1_63). REAC_NODA komt uit het XFEM-resultaat (DX, DY, DZ).
# =====================================================
res_xfem = res
res_xfem = CALC_CHAMP(reuse=res_xfem, RESULTAT=res_xfem, FORCE=('REAC_NODA',))
mesh_xvisu = POST_MAIL_XFEM(MODELE=model)
model_xvisu = AFFE_MODELE(
    MAILLAGE=mesh_xvisu,
    AFFE=_F(GROUP_MA={groups}, PHENOMENE='MECANIQUE', MODELISATION='3D'),
)
res_xvisu = POST_CHAM_XFEM(MODELE_VISU=model_xvisu, RESULTAT=res_xfem)
res_xvisu = CALC_CHAMP(reuse=res_xvisu, RESULTAT=res_xvisu,
                       CONTRAINTE=('SIGM_NOEU',), CRITERES=('SIEQ_NOEU',))
{med}res = PROJ_CHAMP(RESULTAT=res_xvisu, MODELE_1=model_xvisu,
                 MODELE_2=model_sain, METHODE='COLLOCATION',
                 NOM_CHAM=('DEPL', 'SIGM_NOEU', 'SIEQ_NOEU'))
reac_xfem = CREA_CHAMP(TYPE_CHAM='NOEU_DEPL_R', OPERATION='EXTR',
                       RESULTAT=res_xfem, NOM_CHAM='REAC_NODA', NUME_ORDRE=1)
reac_sain = CREA_CHAMP(TYPE_CHAM='NOEU_DEPL_R', OPERATION='ASSE',
                       MODELE=model_sain,
                       ASSE=_F(TOUT='OUI', CHAM_GD=reac_xfem,
                               NOM_CMP=('DX', 'DY', 'DZ')))
res = CREA_RESU(reuse=res, RESULTAT=res, OPERATION='AFFE',
                TYPE_RESU='EVOL_ELAS',
                AFFE=_F(NOM_CHAM='REAC_NODA', CHAM_GD=reac_sain, INST=0.0,
                        MODELE=model_sain))
model = model_sain
"""


def active(model_data):
    """True if model_block has set XFEM cracks."""
    return bool(model_data.get("xfem"))


def result_block(model_data):
    """CALC_CHAMP replacement after MECA_STATIQUE with XFEM (see _RESULT_BLOCK),
    or "" without XFEM."""
    if not active(model_data):
        return ""
    groups = [g for g, m in model_data.get("elset_modelisations", {}).items()
              if m == "3D"]
    med = ""
    if CONFIG_BRIDGE.get("med_export", False):
        # ParaView: the mesh that follows the crack (the lips have their own
        # nodes, so the opening can be seen) with the fields; IMPR_RESU
        # writes the mesh of the result along (measured, BR-14)
        med = ("# MED voor ParaView (med_export): mesh dat de scheur volgt\n"
               "IMPR_RESU(FORMAT='MED', UNITE={0}, RESU=_F(\n"
               "    RESULTAT=res_xvisu,\n"
               "    NOM_CHAM=('DEPL', 'SIGM_NOEU', 'SIEQ_NOEU')))\n"
               .format(MED_UNIT))
    return _RESULT_BLOCK.replace("{groups}", "(" + ", ".join(
        "'{0}'".format(g) for g in groups) + ",)").replace("{med}", med)


def med_path(work_dir=None):
    """Path of the MED file with the mesh that follows the crack
    (<model>_<run_id>_xfem.rmed)."""
    return os.path.join(work_dir or work_dir_path(),
                        run_name(MED_SUFFIX))


def export_lines(model_data, work_dir):
    """Line(s) for the .export: the MED file of result_block (only
    with XFEM and med_export), like the .rmed in
    bridge_to_aster._export_result_lines."""
    if not active(model_data) or not CONFIG_BRIDGE.get("med_export", False):
        return ""
    return "\nF rmed {0} R {1}".format(med_path(work_dir), MED_UNIT)


# ==========================================
# .COMM: K AND G (AFTER THE EXPORT)
# ==========================================
# CSV writer in the job (Python 3 of Code-Aster). Rows of CALC_G_XFEM
# and POST_K1_K2_K3 are matched on NUM_PT if the coordinates are equal
# (both use the front points of the crack, or NB_POINT_FOND
# points).
_CSV_COLUMNS = (
    ("crack", None), ("front", None), ("point", "NUM_PT"),
    ("x", "COOR_X"), ("y", "COOR_Y"), ("z", "COOR_Z"), ("s", "ABSC_CURV"),
    ("G", "G"), ("K1", "K1"), ("K2", "K2"), ("K3", "K3"),
    ("G_IRWIN", "G_IRWIN"), ("K1_POST_K", "K1"), ("K2_POST_K", "K2"),
    ("K3_POST_K", "K3"), ("G_POST_K", "G"),
)

_JOB_CODE = '''
def _bridge_xfem_fronts(fiss):
    return max(1, len(fiss.getCrackTipMultiplicity()) // 2)


def _bridge_xfem_csv(path, tables, columns):
    import io
    lines = [",".join(c[0] for c in columns)]
    for key, front, t_g, t_pk in tables:
        vg = t_g.EXTR_TABLE().values()
        vpk = {}
        if t_pk is not None:
            vp = t_pk.EXTR_TABLE().values()
            for i, num in enumerate(vp.get("NUM_PT", [])):
                vpk[int(num)] = dict((k, vp[k][i]) for k in vp
                                     if i < len(vp[k]))
        size = max([abs(v) for c in ("COOR_X", "COOR_Y", "COOR_Z")
                    for v in vg.get(c, []) if v is not None] + [1.0e-30])
        for i, num in enumerate(vg.get("NUM_PT", [])):
            pk = vpk.get(int(num), {})
            if pk and any(abs((pk.get(c) or 0.0) - (vg[c][i] or 0.0)) >
                          1.0e-6 * size for c in ("COOR_X", "COOR_Y",
                                                  "COOR_Z")):
                pk = {}
            row = []
            for n, (head, para) in enumerate(columns):
                if head == "crack":
                    v = key
                elif head == "front":
                    v = front
                elif head.endswith("_POST_K"):
                    v = pk.get(para)
                else:
                    v = vg.get(para, [None] * (i + 1))[i]
                if v is None:
                    row.append("")
                elif isinstance(v, float):
                    row.append("%.10g" % v)
                else:
                    row.append(str(v).strip())
            lines.append(",".join(row))
    with io.open(path, "w", encoding="utf-8") as f:
        f.write("\\n".join(lines) + "\\n")
    print("BRIDGE_XFEM_CSV " + path)
'''


def _py(text):
    return "'{0}'".format(text.replace("\\", "\\\\").replace("'", "\\'"))


def _r_bounds(analysis, spec):
    """(R_INF, R_SUP) or None (automatic: Code-Aster picks 2h / 4h,
    measured during development); per crack r_inf/r_sup, else the settings
    fracture_r_inf/_sup. Nonsensical combination: ERROR and False."""
    r_inf = spec.get("r_inf")
    r_sup = spec.get("r_sup")
    if r_inf is None and r_sup is None:
        r_inf = float(analysis.get("fracture_r_inf", 0.0) or 0.0)
        r_sup = float(analysis.get("fracture_r_sup", 0.0) or 0.0)
    r_inf = r_inf or 0.0
    r_sup = r_sup or 0.0
    if r_inf == 0.0 and r_sup == 0.0:
        return None
    if r_inf < 0.0 or r_sup <= r_inf:
        log(tr("ERROR: #ASTER-XFEM (scheur {0}): R_INF ({1} m) en R_SUP "
               "({2} m): nodig 0 <= R_INF < R_SUP, of beide 0 "
               "(automatisch).",
               "ERROR: #ASTER-XFEM (crack {0}): R_INF ({1} m) and R_SUP "
               "({2} m): need 0 <= R_INF < R_SUP, or both 0 "
               "(automatic).").format(spec["name"], r_inf, r_sup))
        return False
    return r_inf, r_sup


def _warn_curved(spec):
    if spec["kind"] in _CURVED or spec.get("curved"):
        log(tr("WARNING: #ASTER-XFEM (scheur {0}): gekromd front; K uit "
               "CALC_G_XFEM (interactie-integraal) heeft geen "
               "krommingscorrectie en ligt enkele procenten te hoog "
               "(gemeten +3 tot +5 %, docs/Breukmechanica.md par. 7.4). "
               "Gebruik K uit POST_K1_K2_K3 (kolom K1_POST_K) of G.",
               "WARNING: #ASTER-XFEM (crack {0}): curved front; K from "
               "CALC_G_XFEM (interaction integral) has no curvature "
               "correction and is a few percent too high (measured +3 to "
               "+5 %, docs/en/Fracture_mechanics.md par. 7.4). Use K from "
               "POST_K1_K2_K3 (column K1_POST_K) or G.").format(
                   spec["name"]))


def k_block(model_data, analysis, work_dir):
    """
    .comm code after the result export: per crack and per front CALC_G_XFEM
    and POST_K1_K2_K3 on res_xfem, tables in the .mess and the CSV
    (csv_path). "" without XFEM; None on an error.
    """
    cracks = model_data.get("xfem") or []
    if not cracks:
        return ""
    lines = ["", "# " + "=" * 53,
             "# FRACTURE MECHANICS XFEM (bridge_xfem.k_block): K and G",
             "# along the front of every #ASTER-XFEM crack, per front (NUME_FOND)",
             "# " + "=" * 53, _JOB_CODE, "_bridge_xfem_tabs = []"]
    for c in cracks:
        bounds = _r_bounds(analysis, c)
        if bounds is False:
            return None
        _warn_curved(c)
        theta = "FISSURE={0}, NUME_FOND=_k".format(c["concept"])
        pk = ""
        if bounds is not None:
            theta += ", R_INF={0}, R_SUP={1}".format(_fmt(bounds[0]),
                                                     _fmt(bounds[1]))
            # POST_K1_K2_K3 then uses the lip displacements up to R_SUP
            # (like forma07b: ABSC_CURV_MAXI = rsup)
            pk += ", ABSC_CURV_MAXI={0}".format(_fmt(bounds[1]))
        if c.get("points"):
            theta += ", NB_POINT_FOND={0}".format(c["points"])
            pk += ", NB_POINT_FOND={0}".format(c["points"])
        if c["smoothing"] == "LEGENDRE":
            degree = c.get("degree")
            if degree is None:
                degree = int(analysis.get("fracture_legendre_degree", 5))
            lissage = ("_F(LISSAGE_G='LEGENDRE', LISSAGE_THETA='LEGENDRE', "
                       "DEGRE={0})".format(degree))
        else:
            lissage = "_F(LISSAGE_G='LAGRANGE', LISSAGE_THETA='LAGRANGE')"
        lines += [
            "# Crack {0} ({1})".format(c["name"], c["kind"]),
            "for _k in range(1, _bridge_xfem_fronts({0}) + 1):".format(
                c["concept"]),
            "    _tg = CALC_G_XFEM(RESULTAT=res_xfem, OPTION='CALC_K_G',",
            "                      THETA=_F({0}),".format(theta),
            "                      LISSAGE={0})".format(lissage),
            "    IMPR_TABLE(TABLE=_tg, UNITE=6)",
            "    # POST_K1_K2_K3 (extrapolation of the jump in the",
            "    # displacement across the lips) as a check; an error here",
            "    # does not stop the table of CALC_G_XFEM",
            "    try:",
            "        _tp = POST_K1_K2_K3(RESULTAT=res_xfem, FISSURE={0}, "
            "NUME_FOND=_k{1})".format(c["concept"], pk),
            "        IMPR_TABLE(TABLE=_tp, UNITE=6)",
            "    except Exception as _e:",
            "        _tp = None",
            "        print('BRIDGE_XFEM_POSTK_FOUT {0}/' + str(_k) + ' ' + "
            "str(_e).replace(chr(10), ' ')[:300])".format(c["name"]),
            "    _bridge_xfem_tabs.append(({0}, _k, _tg, _tp))".format(
                _py(c["name"])),
        ]
    lines.append("_bridge_xfem_csv({0}, _bridge_xfem_tabs, {1!r})".format(
        _py(csv_path(work_dir)), [list(c) for c in _CSV_COLUMNS]))
    return "\n".join(lines) + "\n"


def csv_path(work_dir=None):
    """Path of the table of this run (<model>_<run_id>_xfem.csv)."""
    return os.path.join(work_dir or work_dir_path(),
                        run_name(CSV_SUFFIX))


# ==========================================
# AFTER THE RUN: READ THE TABLE AND REPORT
# ==========================================
_DIFF_WARN = 0.05


def report(work_dir=None, mess_path=None):
    """
    Summary of the XFEM table of this run for the log and the
    status box (list of texts; empty without XFEM). WARNINGs for negative
    K_I, missing POST_K1_K2_K3 and a large difference between K from
    CALC_G_XFEM and from POST_K1_K2_K3. In the text MPa.m^0,5 and J/m2.
    """
    import bridge_fracture as bf
    path = csv_path(work_dir)
    rows = bf.read_csv(path)
    if not rows:
        return []
    errors = {}
    if mess_path and os.path.isfile(mess_path):
        with io.open(mess_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("BRIDGE_XFEM_POSTK_FOUT"):
                    parts = line.split(None, 2)
                    errors[parts[1] if len(parts) > 1 else "?"] = (
                        parts[2].strip() if len(parts) > 2 else "")
    keys = []
    for r in rows:
        k = r.get("crack")
        k = "%g" % k if isinstance(k, float) else str(k or "")
        f = r.get("front")
        f = "%g" % f if isinstance(f, float) else str(f or "1")
        r["crack"], r["front"] = k, f
        if (k, f) not in keys:
            keys.append((k, f))
    out = []
    for key, front in keys:
        sub = [r for r in rows if r["crack"] == key and r["front"] == front]
        label = key if front == "1" and sum(
            1 for kk in keys if kk[0] == key) == 1 else key + "/" + front
        line = tr(u"Breukmechanica XFEM, scheur {0}: {1} punten langs het "
                  u"front. K_I {2} MPa.m^0,5 (CALC_G_XFEM), {3} MPa.m^0,5 "
                  u"(POST_K1_K2_K3); G {4} J/m2. K_II tot {5}, K_III tot {6} "
                  u"MPa.m^0,5. Tabel: {7}",
                  u"Fracture mechanics XFEM, crack {0}: {1} points along the "
                  u"front. K_I {2} MPa.m^0.5 (CALC_G_XFEM), {3} MPa.m^0.5 "
                  u"(POST_K1_K2_K3); G {4} J/m2. K_II up to {5}, K_III up "
                  u"to {6} MPa.m^0.5. Table: {7}").format(
                      label, len(sub), bf._fmt_range(bf._range(sub, "K1",
                                                               1.0e6)),
                      bf._fmt_range(bf._range(sub, "K1_POST_K", 1.0e6)),
                      bf._fmt_range(bf._range(sub, "G")),
                      bf._fmt_abs(sub, "K2"), bf._fmt_abs(sub, "K3"),
                      os.path.basename(path))
        log(u"INFO: " + line)
        out.append(line)
        for text in _warnings(sub, label, errors.get(key + "/" + front)):
            log(text)
            out.append(text[len("WARNING: "):])
    return out


def _warnings(rows, label, postk_error):
    out = []
    k1 = [r["K1"] for r in rows if isinstance(r.get("K1"), float)]
    if k1 and min(k1) < 0.0:
        out.append(tr(u"WARNING: Breukmechanica XFEM, scheur {0}: K_I is "
                      u"negatief op {1} van {2} punten: de lippen gaan daar "
                      u"over elkaar (druk op de scheur; zonder contact op "
                      u"de lippen is de waarde fysisch zinloos). Controleer "
                      u"de belasting.",
                      u"WARNING: Fracture mechanics XFEM, crack {0}: K_I is "
                      u"negative at {1} of {2} points: the lips overlap "
                      u"there (compression on the crack; without contact on "
                      u"the lips the value is physically meaningless). Check "
                      u"the load.").format(
                          label, sum(1 for v in k1 if v < 0.0), len(k1)))
    if postk_error is not None or all(r.get("K1_POST_K") is None
                                      for r in rows):
        out.append(tr(u"WARNING: Breukmechanica XFEM, scheur {0}: "
                      u"POST_K1_K2_K3 gaf geen waarden ({1}); alleen "
                      u"CALC_G_XFEM.",
                      u"WARNING: Fracture mechanics XFEM, crack {0}: "
                      u"POST_K1_K2_K3 gave no values ({1}); CALC_G_XFEM "
                      u"only.").format(label, postk_error or "-"))
    pairs = [(r["K1"], r["K1_POST_K"]) for r in rows
             if isinstance(r.get("K1"), float) and
             isinstance(r.get("K1_POST_K"), float)]
    ref = max([abs(b) for _a, b in pairs] + [0.0])
    if pairs and ref > 0.0:
        # Interior points only: at a free surface or a
        # symmetry plane the methods always differ
        inner = pairs[1:-1] if len(pairs) > 2 else pairs
        diff = max(abs(a - b) for a, b in inner) / ref
        if diff > _DIFF_WARN:
            out.append(tr(u"WARNING: Breukmechanica XFEM, scheur {0}: K_I uit "
                          u"CALC_G_XFEM en uit POST_K1_K2_K3 verschillen tot "
                          u"{1}% (binnen het front). Bij een gekromd front is "
                          u"dat de ontbrekende krommingscorrectie (gebruik "
                          u"POST_K1_K2_K3); anders: verfijn het mesh rond "
                          u"het front, controleer R_INF/R_SUP en glad/graad "
                          u"(docs/Breukmechanica.md par. 7).",
                          u"WARNING: Fracture mechanics XFEM, crack {0}: K_I "
                          u"from CALC_G_XFEM and from POST_K1_K2_K3 differ by "
                          u"up to {1}% (inside the front). For a curved "
                          u"front this is the missing curvature correction "
                          u"(use POST_K1_K2_K3); otherwise: refine the mesh "
                          u"around the front, check R_INF/R_SUP and "
                          u"smoothing/degree (docs/en/Fracture_mechanics.md "
                          u"par. 7).").format(label, "%.1f" % (100.0 * diff)))
    return out
