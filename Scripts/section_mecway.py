# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_mecway.py
# Responsibility: the Mecway side of MecwaySectionProps (all mw calls).
#   read_selection(mw)            selected faces -> nodes and coordinates
#   section_input(faces, mode)    plane, 2D frame, boundary loops (mesh) or
#                                 the STEP request (CAD) for the analysis
#   run_analysis(job)             section_analysis.py in the Python of the
#                                 Code-Aster installation (numpy/scipy)
#   create_general_section(...)   Mecway material with a general section
#   store_aster_line(...)         #ASTER-SECTIE line in the custom model
#                                 definition (save, edit the .liml, reopen)
#
# Coordinates: Mecway's API and the .liml use metres; everything here is SI.
# The 2D frame of the section is as AreaPropsForAlibre: the face seen from
# outside, y = global Y projected onto the plane (-Z or +Z when the face is
# normal to Y), x = y cross n, so x, y, n are right-handed. The 2D origin is
# the projection of the global origin: x = P.u, y = P.v, offset = P.n.
#
# Compatible with IronPython 2.7.9 (Mecway); the geometry functions also
# run in CPython (tests/test_section_mecway.py, with a fake mw).

import io
import json
import math
import os
import re

import bridge_utils
from bridge_utils import log, tr

# Material properties of a Mecway general section (the attribute names of
# <geometric type="UniformGeneralSection"> in the .liml; mw API reference:
# "the same as the property's attribute name").
GENERAL_SECTION = "UniformGeneralSection"
# Relative tolerance for "the faces lie in one plane".
PLANE_TOL = 1e-5
# Tag of the custom model definition the #ASTER-SECTIE lines go into (CCX >
# Custom model definition; CCX reads '**' lines as comments). The bridge
# reads every custom text field (bridge_custom.CUSTOM_TAGS).
CUSTOM_TAG = "ccxmodeldefinition"
LINE_PREFIX = u"** ASTER-SECTIE "
# Order of the keys in the #ASTER-SECTIE line (bridge_from_liml checks
# A, IY, IZ, JX against the material).
ASTER_KEYS = ("A", "IY", "IZ", "JX", "AY", "AZ", "EY", "EZ", "RY", "RZ",
              "RT", "JG", "IYR2", "IZR2")


# ==========================================
# SMALL VECTOR HELPERS
# ==========================================
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, f):
    return (a[0] * f, a[1] * f, a[2] * f)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    if n == 0.0:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def _dist(a, b):
    d = _sub(a, b)
    return math.sqrt(_dot(d, d))


def axis_name(vec):
    """'X', '-X', ... for a global axis direction, else '(x; y; z)'."""
    for i, name in enumerate("XYZ"):
        if abs(vec[i]) > 0.9999:
            return name if vec[i] > 0 else u"−" + name
    return u"({0}; {1}; {2})".format("%.3f" % vec[0], "%.3f" % vec[1],
                                     "%.3f" % vec[2])


# ==========================================
# READING THE SELECTION (mw)
# ==========================================
def read_selection(mw):
    """
    The selected faces as [{"eid", "face", "nodes", "coords", "centre"}]
    (coords per node in metres; centre = centroid of the element, for the
    outward normal). Faces only: in element or node selection mode
    mw.selected_faces() is empty.
    """
    faces = []
    centres = {}
    for fid in mw.selected_faces():
        eid = int(fid.element_id)
        nodes = [int(n) for n in mw.face_nodes(fid)]
        coords = []
        for n in nodes:
            p = mw.node(n)
            coords.append((float(p.x), float(p.y), float(p.z)))
        if eid not in centres:
            pts = [mw.node(n) for n in mw.nodes(eid)]
            centres[eid] = (sum(p.x for p in pts) / len(pts),
                            sum(p.y for p in pts) / len(pts),
                            sum(p.z for p in pts) / len(pts))
        faces.append({"eid": eid, "face": int(fid.face_number),
                      "nodes": nodes, "coords": coords,
                      "centre": centres[eid]})
    return faces


def components_info(mw):
    """[(component, material or None, is_line)] for the start of the
    window: is_line when its first element is a line2/line3 (a beam)."""
    out = []
    for comp in mw.components():
        mat = None
        try:
            mat = mw.material(comp)
        except Exception:
            pass
        is_line = False
        try:
            eids = list(mw.component_elements(comp))
            if eids:
                is_line = mw.element_shape(eids[0]) in ("line2", "line3")
        except Exception:
            pass
        out.append((comp, mat, is_line))
    return out


# ==========================================
# GEOMETRY OF THE SELECTION
# ==========================================
def _face_corners(nodes, coords):
    """
    (corner indices, {edge index: midside index}) of one face. 3/4 nodes:
    linear. 6/8 nodes: quadratic; the order of the midside nodes is found
    from the geometry (alternating corner/mid or corners first): the
    hypothesis whose midside nodes lie closest to the edge midpoints wins.
    """
    n = len(nodes)
    if n in (3, 4):
        return list(range(n)), {}
    if n not in (6, 8):
        raise ValueError(tr("Vlak met {0} knopen wordt niet ondersteund.",
                            "Face with {0} nodes is not supported.").format(n))
    k = n // 2

    def error(corners, mids):
        e = 0.0
        for i in range(k):
            a = coords[corners[i]]
            b = coords[corners[(i + 1) % k]]
            m = _mul(_add(a, b), 0.5)
            e += _dist(coords[mids[i]], m) / max(_dist(a, b), 1e-300)
        return e
    grouped = (list(range(k)), list(range(k, n)))
    alternating = (list(range(0, n, 2)), list(range(1, n, 2)))
    best = min((grouped, alternating), key=lambda h: error(*h))
    return best[0], dict(enumerate(best[1]))


def plane_axes(n_out):
    """(u, v) in-plane axes as AreaPropsForAlibre: the face seen from
    outside, v = global Y projected (or -Z/+Z for a face normal to Y),
    u = v x n."""
    if abs(n_out[1]) > 0.999:
        up = (0.0, 0.0, -1.0 if n_out[1] > 0 else 1.0)
    else:
        up = (0.0, 1.0, 0.0)
    d = _dot(up, n_out)
    v = _norm(_sub(up, _mul(n_out, d)))
    u = _norm(_cross(v, n_out))
    return u, v


def selection_plane(faces):
    """
    {"normal", "offset", "u", "v", "size"} of the selected faces; raises
    ValueError when they do not lie in one plane. The normal points out of
    the elements (from the element centroid to the face), or follows the
    node order for shell faces.
    """
    if not faces:
        raise ValueError(tr("Geen vlakken geselecteerd. Selecteer in Mecway "
                            "(vlakselectie) de vlakken van de doorsnede.",
                            "No faces selected. Select the faces of the "
                            "section in Mecway (face selection)."))
    total = (0.0, 0.0, 0.0)
    points = []
    for f in faces:
        corners, _ = _face_corners(f["nodes"], f["coords"])
        pts = [f["coords"][i] for i in corners]
        # Newell's method: area-weighted normal of the polygon
        nrm = (0.0, 0.0, 0.0)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            nrm = _add(nrm, ((a[1] - b[1]) * (a[2] + b[2]),
                             (a[2] - b[2]) * (a[0] + b[0]),
                             (a[0] - b[0]) * (a[1] + b[1])))
        centre = _mul(reduce(_add, pts), 1.0 / len(pts))
        outward = _sub(centre, f["centre"])
        if _dot(nrm, outward) < 0.0 and _dot(outward, outward) > 0.0:
            nrm = _mul(nrm, -1.0)
        total = _add(total, nrm)
        points.extend(f["coords"])
    normal = _norm(total)
    if normal == (0.0, 0.0, 0.0):
        raise ValueError(tr("De geselecteerde vlakken hebben geen "
                            "oppervlak.",
                            "The selected faces have no area."))
    size = max(_dist(points[0], p) for p in points) or 1.0
    offsets = [_dot(p, normal) for p in points]
    offset = sum(offsets) / len(offsets)
    worst = max(abs(o - offset) for o in offsets)
    if worst > PLANE_TOL * size:
        raise ValueError(tr("De geselecteerde vlakken liggen niet in één "
                            "vlak (afwijking {0} mm). Selecteer alleen "
                            "vlakken van één vlakke doorsnede.",
                            "The selected faces do not lie in one plane "
                            "(deviation {0} mm). Select only faces of one "
                            "flat cross-section.").format(
                                "%.4g" % (worst * 1e3)))
    u, v = plane_axes(normal)
    return {"normal": normal, "offset": offset, "u": u, "v": v,
            "size": size}


# Repair of a boundary whose faces do not quite fit together (an imported
# mesh with duplicate nodes, a non-conformal joint, a face left out),
# relative to the size of the selection. A real slit is bounded by closed
# edges, so only such defects leave free boundary ends; every repair is
# reported (heal in the job, notes in the window).
WELD_TOL = 1e-4       # nodes this close are one node (a mesh never has
                      # nodes this close: 10 000 elements across)
TJOINT_TOL = 1e-4     # a node this close to another face's edge splits it
GAP_TOL = 0.02        # free boundary ends this close are joined by a line


def _weld(coord, tol):
    """{node: canonical node}: nodes within tol of an earlier node map to
    it (grid hashing, cells of size tol)."""
    cells, canon = {}, {}
    for n in sorted(coord):
        x, y = coord[n]
        kx, ky = int(math.floor(x / tol)), int(math.floor(y / tol))
        found = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for m in cells.get((kx + dx, ky + dy), ()):
                    if math.hypot(coord[m][0] - x, coord[m][1] - y) <= tol:
                        found = m
                        break
                if found is not None:
                    break
            if found is not None:
                break
        if found is None:
            cells.setdefault((kx, ky), []).append(n)
            canon[n] = n
        else:
            canon[n] = found
    return canon


def _project_on_polyline(p, pts):
    """(distance, segment index, point) of p to the polyline pts."""
    best = (float("inf"), 0, pts[0])
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy
        t = 0.0 if ll == 0.0 else max(0.0, min(1.0, ((p[0] - ax) * dx +
                                                    (p[1] - ay) * dy) / ll))
        q = (ax + t * dx, ay + t * dy)
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < best[0]:
            best = (d, i + t, q)
    return best


def _split_edges(boundary, coord, tol):
    """Split boundary edges at nodes of other boundary edges that lie on
    them (T-joints of a non-conformal mesh). Returns (edges, count)."""
    nodes = set()
    for a, b, _ in boundary:
        nodes.add(a)
        nodes.add(b)
    out, count = [], 0
    for a, b, inner in boundary:
        pts = [coord[a]] + inner + [coord[b]]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        lo_x, hi_x = min(xs) - tol, max(xs) + tol
        lo_y, hi_y = min(ys) - tol, max(ys) + tol
        cuts = []
        for c in nodes:
            if c == a or c == b:
                continue
            x, y = coord[c]
            if not (lo_x <= x <= hi_x and lo_y <= y <= hi_y):
                continue
            d, s, _ = _project_on_polyline(coord[c], pts)
            if d <= tol and 0.0 < s < len(pts) - 1:
                cuts.append((s, c))
        if not cuts:
            out.append((a, b, inner))
            continue
        cuts.sort()
        count += len(cuts)
        start, piece = a, []
        k = 1               # next polyline point
        for s, c in cuts:
            while k < len(pts) - 1 and k <= s:
                piece.append(pts[k])
                k += 1
            out.append((start, c, piece))
            start, piece = c, []
        while k < len(pts) - 1:
            piece.append(pts[k])
            k += 1
        out.append((start, b, piece))
    return out, count


def _quadratic_2d(a, m, b):
    """Points between a and b on the parabola through a, m, b (t = 1/8 ...
    7/8): the curved edge of a quadratic face. A coarse 45 degree arc then
    loses 0.23% of the area of a quarter disc (the parabola itself 0.08%);
    t = 1/4, 1/2, 3/4 lost 0.7% (tests/test_section_mecway.py)."""
    out = []
    for t in [k / 8.0 for k in range(1, 8)]:
        n0 = (1.0 - t) * (1.0 - 2.0 * t)
        nm = 4.0 * t * (1.0 - t)
        n1 = t * (2.0 * t - 1.0)
        out.append((a[0] * n0 + m[0] * nm + b[0] * n1,
                    a[1] * n0 + m[1] * nm + b[1] * n1))
    return out


def boundary_loops(faces, plane):
    """
    Closed 2D loops [[x, y], ...] (metres, frame of plane) of the outer
    edges of the selected faces: an edge used by one selected face only.
    Quadratic edges are sampled on their parabola. The analysis takes the
    even-odd interior of all loops.

    Repairs (constants above): nodes at the same place are welded, an edge
    with another face's node on it is split there, and free ends of the
    boundary are joined to the nearest free end within GAP_TOL. Returns
    (loops, heal) with heal = {"welded": n, "split": n, "gaps_closed":
    [[length m, [x, y]], ...]}. ValueError when a gap is larger.
    """
    u, v = plane["u"], plane["v"]
    size = plane["size"]
    coord = {}
    raw = []
    for f in faces:
        corners, mids = _face_corners(f["nodes"], f["coords"])
        for i, n in enumerate(f["nodes"]):
            p = f["coords"][i]
            coord[n] = (_dot(p, u), _dot(p, v))
        k = len(corners)
        for i in range(k):
            raw.append((f["nodes"][corners[i]],
                        f["nodes"][corners[(i + 1) % k]],
                        f["nodes"][mids[i]] if i in mids else None))
    canon = _weld(coord, WELD_TOL * size)
    welded = sum(1 for n, c in canon.items() if n != c)
    count, edges = {}, {}
    for a, b, m in raw:
        a, b = canon[a], canon[b]
        if a == b:
            continue            # degenerate after welding
        inner = [] if m is None else _quadratic_2d(coord[a], coord[m],
                                                   coord[b])
        key = (min(a, b), max(a, b))
        count[key] = count.get(key, 0) + 1
        edges[key] = (a, b, inner)
    boundary = [edges[key] for key, c in count.items() if c == 1]
    if not boundary:
        raise ValueError(tr("De selectie heeft geen rand (gesloten "
                            "oppervlak?).",
                            "The selection has no boundary (closed "
                            "surface?)."))
    boundary, split = _split_edges(boundary, coord, TJOINT_TOL * size)
    if split:
        count, edges = {}, {}
        for a, b, inner in boundary:
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
            edges[key] = (a, b, inner)
        boundary = [edges[key] for key, c in count.items() if c == 1]

    # chains over the corner nodes; free ends (odd degree) first so that an
    # open chain is found from one end to the other
    at = {}
    for idx, (a, b, _) in enumerate(boundary):
        at.setdefault(a, []).append(idx)
        at.setdefault(b, []).append(idx)
    free = set(n for n, lst in at.items() if len(lst) % 2)
    order = [i for i, (a, b, _) in enumerate(boundary)
             if a in free or b in free] + list(range(len(boundary)))
    used = [False] * len(boundary)
    loops, open_chains = [], []
    for start in order:
        if used[start]:
            continue
        used[start] = True
        a, b, inner = boundary[start]
        if b in free and a not in free:
            a, b, inner = b, a, inner[::-1]
        first, pts, cur = a, [coord[a]] + list(inner), b
        while cur != first:
            nxt = [i for i in at[cur] if not used[i]]
            if not nxt:
                break
            i = nxt[0]
            used[i] = True
            a, b, inner = boundary[i]
            if a != cur:        # traverse the edge from cur
                a, b, inner = b, a, inner[::-1]
            pts += [coord[a]] + list(inner)
            cur = b
        if cur == first:
            loops.append(pts)
        else:
            open_chains.append(pts + [coord[cur]])

    gaps = []
    gap_tol = GAP_TOL * size
    while open_chains:
        chain = open_chains.pop(0)
        while True:
            end = chain[-1]
            # candidates: (distance, kind, index)
            cands = []
            if len(chain) >= 3:
                cands.append((math.hypot(end[0] - chain[0][0],
                                         end[1] - chain[0][1]), "self", -1))
            for j, other in enumerate(open_chains):
                cands.append((math.hypot(end[0] - other[0][0],
                                         end[1] - other[0][1]), "fwd", j))
                cands.append((math.hypot(end[0] - other[-1][0],
                                         end[1] - other[-1][1]), "rev", j))
            if not cands:
                cands.append((float("inf"), "none", -1))
            d, kind, j = min(cands)
            if d > gap_tol:
                if d == float("inf"):
                    d = 0.0
                raise ValueError(tr(
                    "De rand van de selectie is niet gesloten: een opening "
                    "bij ({0}; {1}) mm is groter dan {2} mm (of er is geen "
                    "ander rand-eind). Selecteer een gesloten gebied.",
                    "The boundary of the selection is not closed: an "
                    "opening at ({0}; {1}) mm is larger than {2} mm (or "
                    "there is no other free end). Select a closed region."
                ).format("%.4g" % (end[0] * 1e3), "%.4g" % (end[1] * 1e3),
                         "%.4g" % (gap_tol * 1e3)))
            if kind == "self":
                target = chain[0]
            else:
                other = open_chains.pop(j)
                if kind == "rev":
                    other = other[::-1]
                target = other[0]
            if d > WELD_TOL * size:
                gaps.append([d, [0.5 * (end[0] + target[0]),
                                 0.5 * (end[1] + target[1])]])
            if kind == "self":
                loops.append(chain if d > WELD_TOL * size else chain[:-1])
                break
            chain = chain + (other if d > WELD_TOL * size else other[1:])
    loops = [[[p[0], p[1]] for p in lp] for lp in loops if len(lp) >= 3]
    return loops, {"welded": welded, "split": split, "gaps_closed": gaps}


# ==========================================
# CAD (STEP) OF THE SELECTION
# ==========================================
_GEOMETRY_RE = re.compile(r'<geometry\b([^>]*)>')
_ELSET_RE = re.compile(r'<elset\b([^>]*)>')
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def _xml_unescape(text):
    return (text.replace("&quot;", '"').replace("&apos;", "'")
            .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))


def liml_geometries(liml_path):
    """({geometry id: STEP path}, {component: geometry id}) from the saved
    .liml (attributes only, read as text: fast also for a big model)."""
    geoms, comps = {}, {}
    folder = os.path.dirname(os.path.abspath(liml_path))
    with io.open(liml_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "<geometry" in line:
                for m in _GEOMETRY_RE.finditer(line):
                    attrs = dict(_ATTR_RE.findall(m.group(1)))
                    if "id" in attrs and "filename" in attrs:
                        path = _xml_unescape(attrs["filename"])
                        if not os.path.isabs(path):
                            path = os.path.join(folder, path)
                        geoms[attrs["id"]] = path
            if "<elset" in line:
                for m in _ELSET_RE.finditer(line):
                    attrs = dict(_ATTR_RE.findall(m.group(1)))
                    if "geomid" in attrs and "name" in attrs:
                        comps[_xml_unescape(attrs["name"])] = attrs["geomid"]
    return geoms, comps


def step_request(mw, faces, plane):
    """
    The "step" block for section_analysis (section_step.find_faces and
    face_loops_2d): the STEP file of the component of the selected faces
    and the centroids of those faces. ValueError with the reason when the
    CAD route is not possible.
    """
    liml = mw.file_name()
    if not liml or not os.path.isfile(liml):
        raise ValueError(tr("CAD-vlak: sla het model eerst op (de bridge "
                            "leest de STEP-koppeling uit de .liml).",
                            "CAD face: save the model first (the STEP link "
                            "is read from the .liml)."))
    geoms, comps = liml_geometries(liml)
    ids = set()
    for f in faces:
        comp = mw.element_component(f["eid"])
        if comp not in comps:
            raise ValueError(tr("CAD-vlak: component '{0}' is niet uit een "
                                "STEP-geometrie gemesht (of het model is "
                                "daarna niet opgeslagen). Gebruik 'Mesh-"
                                "vlakken'.",
                                "CAD face: component '{0}' was not meshed "
                                "from a STEP geometry (or the model was not "
                                "saved since). Use 'Mesh faces'.").format(
                                    comp))
        ids.add(comps[comp])
    if len(ids) > 1:
        raise ValueError(tr("CAD-vlak: de vlakken horen bij meer dan één "
                            "STEP-geometrie.",
                            "CAD face: the faces belong to more than one "
                            "STEP geometry."))
    gid = ids.pop()
    path = geoms.get(gid)
    if not path or not os.path.isfile(path):
        raise ValueError(tr("CAD-vlak: STEP-bestand van geometrie {0} niet "
                            "gevonden: {1}",
                            "CAD face: STEP file of geometry {0} not found: "
                            "{1}").format(gid, path))
    points = []
    for f in faces:
        corners, _ = _face_corners(f["nodes"], f["coords"])
        pts = [f["coords"][i] for i in corners]
        points.append(list(_mul(reduce(_add, pts), 1.0 / len(pts))))
    return {"file": path, "normal": list(plane["normal"]),
            "offset": plane["offset"], "u": list(plane["u"]),
            "v": list(plane["v"]), "points": points,
            "tol": max(1e-6, 1e-4 * plane["size"])}


def section_input(mw, faces, mode):
    """(job dict for section_analysis, plane) for mode "mesh" or "cad"."""
    plane = selection_plane(faces)
    job = {"nu": 0.0, "mesh_size": None}
    if mode == "cad":
        job["step"] = step_request(mw, faces, plane)
    else:
        job["loops"], job["heal"] = boundary_loops(faces, plane)
    return job, plane


# ==========================================
# THE ANALYSIS PROCESS
# ==========================================
def aster_python():
    """python.exe of the Code-Aster installation (numpy and scipy), or
    None. Same folders as bridge_run_aster._monitor_python."""
    from bridge_run_aster import aster_root
    root = aster_root()
    try:
        subdirs = sorted(d for d in os.listdir(root)
                         if d.lower().startswith("python"))
    except OSError:
        return None
    for d in subdirs:
        path = os.path.join(root, d, "python.exe")
        if os.path.isfile(path):
            return path
    return None


def work_folder():
    """<bridge work folder>/section_props (created)."""
    folder = os.path.join(bridge_utils.work_dir_path(), "section_props")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder


def start_analysis(job):
    """
    Write the job and start section_analysis.py without a console window.
    Returns (process, result path). Raises RuntimeError when Code-Aster's
    Python is missing.
    """
    python = aster_python()
    if not python:
        raise RuntimeError(tr("Python van Code-Aster niet gevonden (nodig "
                              "voor numpy/scipy). Controleer 'exe_aster' op "
                              "het startscherm van de bridge.",
                              "Code-Aster's Python not found (needed for "
                              "numpy/scipy). Check 'exe_aster' on the "
                              "bridge start screen."))
    folder = work_folder()
    src = os.path.join(folder, "section_input.json")
    dst = os.path.join(folder, "section_results.json")
    if os.path.isfile(dst):
        os.remove(dst)
    with io.open(src, "w", encoding="utf-8") as f:
        # ensure_ascii=False: IronPython's json fails on non-ASCII text
        # with ensure_ascii=True (e.g. a folder name with an accent).
        f.write(u"{0}".format(json.dumps(job, ensure_ascii=False)))
    script = os.path.join(bridge_utils.SCRIPTS_DIR, "section_analysis.py")
    import clr
    clr.AddReference("System")
    from System.Diagnostics import Process, ProcessStartInfo
    info = ProcessStartInfo(python)
    info.Arguments = u'-I "{0}" "{1}" "{2}"'.format(script, src, dst)
    info.UseShellExecute = False
    info.CreateNoWindow = True
    info.RedirectStandardError = True
    info.WorkingDirectory = folder
    log("INFO: MecwaySectionProps: {0} {1}".format(python, info.Arguments))
    return Process.Start(info), dst


def read_results(proc, dst):
    """Results dict of a finished process; RuntimeError on a failure."""
    stderr = u""
    try:
        stderr = proc.StandardError.ReadToEnd()
    except Exception:
        pass
    if not os.path.isfile(dst):
        raise RuntimeError(tr("De berekening gaf geen resultaat.\n{0}",
                              "The analysis produced no result.\n{0}")
                           .format(stderr[-1500:]))
    with io.open(dst, encoding="utf-8") as f:
        res = json.loads(f.read())
    if not res.get("success"):
        log("ERROR: MecwaySectionProps: {0}".format(
            res.get("traceback") or res.get("error")))
        raise RuntimeError(res.get("error") or u"?")
    return res


# ==========================================
# GENERAL SECTION IN MECWAY
# ==========================================
def recovery_point(res):
    """Mecway's stress recovery point (principal coordinates V, W): the
    boundary point farthest from the centroid (largest bending stress for
    a general direction of the moment)."""
    cx, cy = res["centroid"]
    phi = math.radians(res["phi_deg"])
    c, s = math.cos(phi), math.sin(phi)
    best, point = -1.0, (0.0, 0.0)
    for loop in res.get("loops", []):
        for x, y in loop:
            dx, dy = x - cx, y - cy
            r = dx * dx + dy * dy
            if r > best:
                best, point = r, (dx * c + dy * s, -dx * s + dy * c)
    return point


def general_section_values(res):
    """{Mecway property: SI value} of the general section: area, iyy = I
    about V = principal axis 1, izz = I about W = axis 2, torsion constant,
    perimeter and the stress recovery point."""
    py, pz = recovery_point(res)
    return [("area", res["area"]), ("iyy", res["i11_c"]),
            ("izz", res["i22_c"]), ("torsionconstant", res["j"]),
            ("perimeter", res["perimeter"]), ("pointy", py),
            ("pointz", pz)]


# Material groups copied from the component's current material.
_COPY = (("mechanical", "Isotropic", ("youngsmodulus", "poissonratio",
                                      "thermalexpansion")),
         ("density", None, ("density",)))


def create_general_section(mw, name, res, component=None, copy_from=None):
    """
    New Mecway material `name` (Mecway may change the name) with a general
    section from the results; with copy_from the isotropic elastic data
    and density of that material are copied; with component the material
    is assigned to it. Returns the material name.
    """
    mat = mw.new_material(name)
    mw.set_material_type(mat, "geometric", GENERAL_SECTION)
    for prop, value in general_section_values(res):
        mw.set_material_property(mat, prop, float(value))
    if copy_from:
        for group, only, props in _COPY:
            try:
                kind = mw.material_type(copy_from, group)
            except Exception:
                continue
            if not kind or kind == "None" or (only and kind != only):
                continue
            mw.set_material_type(mat, group, kind)
            for prop in props:
                try:
                    value = mw.material_property(copy_from, prop)
                except Exception:
                    continue
                if value is not None:
                    mw.set_material_property(mat, prop, value)
    if component:
        mw.set_material(component, mat)
    log("INFO: MecwaySectionProps: material '{0}' (general section){1}."
        .format(mat, " assigned to '{0}'".format(component)
                if component else ""))
    return mat


def aster_line(material, res):
    """The #ASTER-SECTIE line (without the '** ' prefix handling) for the
    material: SI values, 10 significant digits."""
    aster = dict(res["aster"])
    # The checked values exactly as written into the Mecway material.
    aster["A"], aster["IY"] = res["area"], res["i11_c"]
    aster["IZ"], aster["JX"] = res["i22_c"], res["j"]
    parts = []
    for key in ASTER_KEYS:
        if aster.get(key) is not None:
            parts.append(u"{0}={1}".format(key, "%.10g" % aster[key]))
    return LINE_PREFIX + u"{0}: {1}".format(material, u", ".join(parts))


def _xml_escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def insert_aster_line(xml, material, line):
    """
    The .liml text with `line` in the custom model definition; an earlier
    #ASTER-SECTIE line of the same material is replaced. Pure text edit
    (Mecway's formatting of the rest of the file stays as it is).
    """
    esc = _xml_escape(line)
    own = re.compile(r"^\s*(?:\*\*|#|\$)\s*ASTER-SECTI(?:E|ON)\s+" +
                     re.escape(_xml_escape(material)) + r"\s*:",
                     re.IGNORECASE)
    m = re.search(r"<{0}>(.*?)</{0}>".format(CUSTOM_TAG), xml, re.DOTALL)
    if m:
        lines = [ln for ln in re.split(r"\r?\n", m.group(1))
                 if not own.match(ln)]
        while lines and not lines[-1].strip():
            lines.pop()
        body = u"\n".join(lines + [esc])
        return xml[:m.start(1)] + body + xml[m.end(1):]
    m = re.search(r"<{0}\s*/>".format(CUSTOM_TAG), xml)
    block = u"<{0}>{1}</{0}>".format(CUSTOM_TAG, esc)
    if m:
        return xml[:m.start()] + block + xml[m.end():]
    end = xml.rfind(u"</liml>")
    if end < 0:
        raise ValueError(u"</liml> not found")
    newline = u"\r\n" if u"\r\n" in xml else u"\n"
    return xml[:end] + u"  " + block + newline + xml[end:]


def store_aster_line(mw, material, res):
    """
    Save the model, put the #ASTER-SECTIE line of `material` in the custom
    model definition of the .liml and reopen it in Mecway (there is no API
    for that text field). Returns the line.
    """
    liml = mw.file_name()
    if not liml or not os.path.dirname(liml):
        raise RuntimeError(tr("Sla het model eerst op (File > Save As...); "
                              "de extra eigenschappen komen in de .liml.",
                              "Save the model first (File > Save As...); "
                              "the extra properties go into the .liml."))
    mw.save()
    line = aster_line(material, res)
    with io.open(liml, encoding="utf-8", newline="") as f:
        xml = f.read()
    new = insert_aster_line(xml, material, line)
    tmp = liml + ".sectionprops.tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    # Replace the file; on Windows os.rename does not overwrite.
    bak = liml + ".sectionprops.bak"
    if os.path.isfile(bak):
        os.remove(bak)
    os.rename(liml, bak)
    try:
        os.rename(tmp, liml)
    except Exception:
        os.rename(bak, liml)
        raise
    os.remove(bak)
    mw.open(liml)
    log("INFO: MecwaySectionProps: '{0}' in <{1}> of {2}; model reopened."
        .format(line, CUSTOM_TAG, liml))
    return line


try:
    reduce
except NameError:           # Python 3 (offline tests)
    from functools import reduce
