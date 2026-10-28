# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_homard.py
# Responsibility: adaptive refinement with HOMARD inside the Code-Aster job
# for thermal (ther_3d) and nonlinear static (nonlin_static_3d) analyses
# (step S35b, STAPPENPLAN.md; research S35a). Linear static keeps the
# Mecway route of bridge_adapt.py (refine_x2).
#
# What happens (docs/Foutschatter.md par. 7):
#   - bridge_mesh.write_mesh asks boundary_groups() for the curved
#     boundaries: free faces of the solids in patches (crease angle
#     CREASE_DEG), each patch fitted as a cylinder or a sphere
#     (FIT_TOL relative to the radius); the faces of a recognised patch go
#     into the mesh as a group BRRAND<n> of boundary elements, for
#     MACR_ADAP_MAIL FRONTIERE_ANALYTIQUE. #ASTER-RAND (#ASTER-BOUNDARY)
#     per face selection overrides the recognition (shape or GEEN/NONE).
#   - check_scope() gives an ERROR for what the first version cannot
#     refine (shells, beams, contact, couplings, compression only, node
#     selections with more than one node, ...): HOMARD refines only cell
#     groups; node groups keep their old nodes (S35a, measured).
#   - wrap() turns the region between the markers BRIDGE_ADAPT_BEGIN and
#     BRIDGE_ADAPT_END of the thermal / nonlinear template into a Python
#     loop: solve -> indicator (aster_adapt.py, inside the job) -> HOMARD
#     -> solve ... and after the loop PROJ_CHAMP of the result onto the
#     original mesh, so that aster_results_export writes it for Mecway.
#   - report() reads the BRIDGE_ADAPT lines of the .mess for the status
#     box.
#
# Compatible with IronPython 2.7.9 (no numpy; small linear algebra here).

import math
import re

from bridge_utils import log, tr, parse_and_convert, get_active_analysis

# Analyses with the HOMARD loop (solver_command of CONFIG_BRIDGE)
SOLVERS = ("THER_LINEAIRE", "THER_NON_LINE", "STAT_NON_LINE")
# Markers in AsterTemplate_Thermique.comm / AsterTemplate_StatNonLine.comm
BEGIN = "BRIDGE_ADAPT_BEGIN"
END = "BRIDGE_ADAPT_END"
# Group names: boundary following (in the mesh) and the selection per loop
# (in the job); also in bridge_mesh._GENERATED_NAME_RE.
BOUNDARY_PREFIX = "BRRAND"
SELECT_PREFIX = "BRADAP"
# Neighbouring boundary faces belong to one patch if their normals differ
# by less than this angle (a hole edge against a flat face: 90 degrees; a
# coarse hole with 8 faces around: 45 degrees).
CREASE_DEG = 50.0
# A patch is a cylinder/sphere if every node lies within FIT_TOL x radius
# of the fitted surface. Nodes of a Mecway mesh lie on the CAD surface;
# 1e-3 also accepts a faceted (STL-like) mesh of fine facets.
FIT_TOL = 1.0e-3
# A radius above MAX_RADIUS x the patch size counts as flat (no boundary
# following needed).
MAX_RADIUS = 50.0
# Fixed Doerfler fraction of the selection per loop (as bridge_adapt
# 'dorfler' 0.5; S35a prototype).
DORFLER = 0.5


# ==========================================
# REQUEST AND SETTINGS
# ==========================================
def settings(model_data=None):
    """
    The adaptive settings of the active analysis with the #ASTER-OPTIE
    values, or None if the HOMARD loop is not requested (setting
    adapt_homard off, or another analysis).
    """
    import bridge_custom
    try:
        analysis = get_active_analysis()
    except KeyError:
        return None
    if "adapt_homard" not in analysis:
        return None
    options = {}
    if model_data:
        options = model_data.get("aster_custom", {}).get("options", {})
    keys = ("adapt_homard", "adapt_homard_target",
            "adapt_homard_max_loops", "adapt_homard_max_elements")
    sub = dict((k, v) for k, v in analysis.items() if k in keys)
    opts = dict((k, v) for k, v in options.items() if k in keys)
    if opts:
        sub = bridge_custom.apply_options(sub, opts)
    if not sub.get("adapt_homard"):
        return None
    if analysis.get("solver_command") not in SOLVERS:
        return None
    return {"target": float(sub.get("adapt_homard_target", 1.0)),
            "max_loops": int(sub.get("adapt_homard_max_loops", 5)),
            "max_elements": int(sub.get("adapt_homard_max_elements",
                                        200000))}


# ==========================================
# #ASTER-RAND: boundary shape per face selection
# ==========================================
_SHAPES = {"CILINDER": "CYLINDRE", "CYLINDER": "CYLINDRE",
           "BOL": "SPHERE", "SPHERE": "SPHERE",
           "GEEN": "NONE", "NONE": "NONE"}
_NUMBERS = {"CYLINDRE": 7, "SPHERE": 4, "NONE": 0}


def parse_boundaries(bodies):
    """
    #ASTER-RAND lines: 'selection = CILINDER x, y, z, ax, ay, az, r',
    'selection = BOL x, y, z, r' or 'selection = GEEN' (English
    CYLINDER / SPHERE / NONE). Lengths with an optional unit (default m).
    Returns {selection: (shape, [values])} with shape CYLINDRE, SPHERE
    or NONE; a wrong line gives an ERROR and is skipped.
    """
    out = {}
    for body in bodies:
        sel, sep, rest = body.partition("=")
        head = rest.strip().split(None, 1)
        shape = _SHAPES.get(head[0].upper()) if head else None
        # values separated by commas; a value may have a unit ("10 mm")
        words = [head[0] if head else ""] + [
            w.strip() for w in (head[1] if len(head) > 1 else "").split(",")
            if w.strip()]
        if not sep or not sel.strip() or shape is None or \
                len(words) - 1 != _NUMBERS[shape]:
            log(tr("ERROR: '#ASTER-RAND {0}': verwacht 'selectie = CILINDER "
                   "x, y, z, ax, ay, az, r', 'selectie = BOL x, y, z, r' of "
                   "'selectie = GEEN'; overgeslagen.",
                   "ERROR: '#ASTER-RAND {0}': expected 'selection = "
                   "CYLINDER x, y, z, ax, ay, az, r', 'selection = SPHERE "
                   "x, y, z, r' or 'selection = NONE'; skipped.").format(
                body.strip()))
            continue
        values = []
        for i, w in enumerate(words[1:]):
            # direction components (ax, ay, az) have no unit
            unitless = shape == "CYLINDRE" and i in (3, 4, 5)
            try:
                values.append(float(w) if unitless or
                              re.match(r"^[-+.\d][\d.eE+-]*$", w) else
                              parse_and_convert(w, "length"))
            except ValueError:
                values = None
                break
        if values is None:
            log(tr("ERROR: '#ASTER-RAND {0}': geen getal; overgeslagen.",
                   "ERROR: '#ASTER-RAND {0}': not a number; skipped.")
                .format(body.strip()))
            continue
        if shape == "CYLINDRE" and _norm(values[3:6]) == 0.0:
            log(tr("ERROR: '#ASTER-RAND {0}': as nul; overgeslagen.",
                   "ERROR: '#ASTER-RAND {0}': zero axis; skipped.")
                .format(body.strip()))
            continue
        out[sel.strip()] = (shape, values)
    return out


# ==========================================
# SMALL LINEAR ALGEBRA (IronPython: no numpy)
# ==========================================
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    return math.sqrt(sum(x * x for x in a))


def _unit(a):
    n = _norm(a)
    return tuple(x / n for x in a) if n > 0.0 else None


def _solve(a, b):
    """Solve a x = b (Gauss with partial pivoting); None if singular."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < 1.0e-300:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    return [m[i][n] / m[i][i] for i in range(n)]


def _eig_sym3(a):
    """Eigenvalues and eigenvectors of a symmetric 3x3 (Jacobi), sorted
    ascending: [(value, vector), ...]."""
    a = [list(r) for r in a]
    v = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    for _sweep in range(50):
        off = abs(a[0][1]) + abs(a[0][2]) + abs(a[1][2])
        if off < 1.0e-15:
            break
        for p, q in ((0, 1), (0, 2), (1, 2)):
            if abs(a[p][q]) < 1.0e-300:
                continue
            theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
            t = (1.0 if theta >= 0 else -1.0) / (
                abs(theta) + math.sqrt(theta * theta + 1.0))
            c = 1.0 / math.sqrt(t * t + 1.0)
            s = t * c
            for k in range(3):
                akp, akq = a[k][p], a[k][q]
                a[k][p] = c * akp - s * akq
                a[k][q] = s * akp + c * akq
            for k in range(3):
                apk, aqk = a[p][k], a[q][k]
                a[p][k] = c * apk - s * aqk
                a[q][k] = s * apk + c * aqk
            for k in range(3):
                vkp, vkq = v[k][p], v[k][q]
                v[k][p] = c * vkp - s * vkq
                v[k][q] = s * vkp + c * vkq
    pairs = [(a[i][i], (v[0][i], v[1][i], v[2][i])) for i in range(3)]
    return sorted(pairs, key=lambda x: x[0])


# ==========================================
# SURFACE FIT
# ==========================================
def face_normal(points):
    """Unit normal of a (possibly curved) face from its boundary ring
    (Newell), or None."""
    n = [0.0, 0.0, 0.0]
    k = len(points)
    for i in range(k):
        p, q = points[i], points[(i + 1) % k]
        n[0] += (p[1] - q[1]) * (p[2] + q[2])
        n[1] += (p[2] - q[2]) * (p[0] + q[0])
        n[2] += (p[0] - q[0]) * (p[1] + q[1])
    return _unit(n)


def _fit_sphere(points):
    """Least squares x^2+y^2+z^2 + D x + E y + F z + G = 0 -> (centre,
    radius) or None."""
    ata = [[0.0] * 4 for _ in range(4)]
    atb = [0.0] * 4
    for p in points:
        row = (p[0], p[1], p[2], 1.0)
        rhs = -(p[0] * p[0] + p[1] * p[1] + p[2] * p[2])
        for i in range(4):
            atb[i] += row[i] * rhs
            for j in range(4):
                ata[i][j] += row[i] * row[j]
    s = _solve(ata, atb)
    if s is None:
        return None
    c = (-s[0] / 2.0, -s[1] / 2.0, -s[2] / 2.0)
    r2 = _dot(c, c) - s[3]
    if r2 <= 0.0:
        return None
    return c, math.sqrt(r2)


def _fit_circle(points2):
    """Least squares circle (Kasa) in 2D -> (centre, radius) or None."""
    ata = [[0.0] * 3 for _ in range(3)]
    atb = [0.0] * 3
    for x, y in points2:
        row = (x, y, 1.0)
        rhs = -(x * x + y * y)
        for i in range(3):
            atb[i] += row[i] * rhs
            for j in range(3):
                ata[i][j] += row[i] * row[j]
    s = _solve(ata, atb)
    if s is None:
        return None
    c = (-s[0] / 2.0, -s[1] / 2.0)
    r2 = c[0] * c[0] + c[1] * c[1] - s[2]
    if r2 <= 0.0:
        return None
    return c, math.sqrt(r2)


def fit_surface(points, normals, tol=FIT_TOL):
    """
    Recognise a patch: points (all nodes) and normals (one per face).
    Returns {"shape": "PLAN"/"SPHERE"/"CYLINDRE"/None, "params": [...],
    "dev": max. relative deviation}. params: SPHERE (x, y, z, r),
    CYLINDRE (x, y, z, ax, ay, az, r) with (x, y, z) on the axis.
    """
    pts = list(points)
    if len(pts) < 4 or not normals:
        return {"shape": None, "params": None, "dev": None}
    size = max(_norm(_sub(p, pts[0])) for p in pts) or 1.0
    m = [[0.0] * 3 for _ in range(3)]
    for n in normals:
        for i in range(3):
            for j in range(3):
                m[i][j] += n[i] * n[j] / len(normals)
    eig = _eig_sym3(m)
    # flat: all normals parallel and all points in one plane
    nrm = eig[2][1]
    off = max(abs(_dot(_sub(p, pts[0]), nrm)) for p in pts)
    if off <= tol * size:
        return {"shape": "PLAN", "params": None, "dev": off / size}
    best = {"shape": None, "params": None, "dev": None}
    # An exact cylinder has normals exactly perpendicular to its axis
    # (smallest eigenvalue ~0); two parallel circles of a cylinder with one
    # element layer also lie on a sphere, so then the sphere is not tried.
    sph = _fit_sphere(pts) if eig[0][0] > 1.0e-8 else None
    if sph is not None:
        c, r = sph
        dev = max(abs(_norm(_sub(p, c)) - r) for p in pts) / r
        if dev <= tol and r <= MAX_RADIUS * size:
            return {"shape": "SPHERE", "params": [c[0], c[1], c[2], r],
                    "dev": dev}
        best["dev"] = dev
    # cylinder: the normals are perpendicular to the axis (smallest
    # eigenvalue of sum n n^T is ~0)
    axis = _unit(eig[0][1])
    if axis is not None and eig[0][0] <= 1.0e-2:
        u = _unit(_cross(axis, (1.0, 0.0, 0.0)))
        if u is None or _norm(_cross(axis, (1.0, 0.0, 0.0))) < 0.3:
            u = _unit(_cross(axis, (0.0, 1.0, 0.0)))
        v = _cross(axis, u)
        circ = _fit_circle([(_dot(p, u), _dot(p, v)) for p in pts])
        if circ is not None:
            (cu, cv), r = circ
            w = sum(_dot(p, axis) for p in pts) / len(pts)
            c = tuple(cu * u[i] + cv * v[i] + w * axis[i] for i in range(3))
            dev = max(abs(_norm(_cross(_sub(p, c), axis)) - r)
                      for p in pts) / r
            if dev <= tol and r <= MAX_RADIUS * size:
                return {"shape": "CYLINDRE",
                        "params": [c[0], c[1], c[2], axis[0], axis[1],
                                   axis[2], r], "dev": dev}
            if best["dev"] is None or dev < best["dev"]:
                best["dev"] = dev
    return best


# ==========================================
# PATCHES OF BOUNDARY FACES
# ==========================================
def patches(faces, coords, crease_deg=CREASE_DEG):
    """
    faces: [(key, ring)] with ring the boundary nodes of the face in order
    (corners and mid nodes); coords {nid: (x, y, z)}. Faces sharing an
    edge (two consecutive corner/mid nodes) with normals within
    crease_deg form a patch. Returns [[index into faces, ...], ...].
    """
    cos_lim = math.cos(math.radians(crease_deg))
    normals = [face_normal([coords[n] for n in ring]) for _k, ring in faces]
    edges = {}
    for i, (_k, ring) in enumerate(faces):
        for a, b in zip(ring, ring[1:] + ring[:1]):
            edges.setdefault(frozenset((a, b)), []).append(i)
    parent = list(range(len(faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for members in edges.values():
        for i in members:
            for j in members:
                if i < j and normals[i] and normals[j] and \
                        _dot(normals[i], normals[j]) >= cos_lim:
                    parent[find(i)] = find(j)
    groups = {}
    for i in range(len(faces)):
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values()], normals


def recognise(faces, coords, overrides=None):
    """
    The curved boundaries for MACR_ADAP_MAIL FRONTIERE_ANALYTIQUE.

    faces    : [(key, ring)] free faces of the solids (ring: boundary nodes
               in order)
    overrides: [(selection, (shape, values), [face keys])] from #ASTER-RAND
    Returns [(shape, params, [face keys], description)]: one entry per
    recognised or prescribed surface. Logs INFO per surface and a WARNING
    per curved patch that is not recognised.
    """
    out = []
    taken = set()
    for sel, (shape, values), keys in overrides or ():
        taken.update(keys)
        if shape == "NONE":
            log("INFO: Adaptive refinement: boundary following off for "
                "face selection '{0}' (#ASTER-RAND).".format(sel))
            continue
        params = list(values)
        if shape == "CYLINDRE":
            ax = _unit(params[3:6])
            params[3:6] = list(ax)
        out.append((shape, params, list(keys), sel))
        log("INFO: Adaptive refinement: face selection '{0}' follows {1} "
            "{2} (#ASTER-RAND).".format(sel, shape, _fmt(params)))
    free = [(k, ring) for k, ring in faces if k not in taken]
    groups, normals = patches(free, coords)
    for g in groups:
        pts = {}
        for i in g:
            for n in free[i][1]:
                pts[n] = coords[n]
        fit = fit_surface(list(pts.values()), [normals[i] for i in g
                                               if normals[i]])
        where = _centroid(list(pts.values()))
        if fit["shape"] == "PLAN":
            continue
        if fit["shape"] is None:
            log(tr("WARNING: Adaptieve verfijning: gekromd randvlak ({0} "
                   "vlakken, rond ({1})) niet herkend als cilinder of bol "
                   "(afwijking {2}); HOMARD volgt deze rand niet (nieuwe "
                   "knopen op de rechte elementranden). Geef de vorm met "
                   "#ASTER-RAND als het een cilinder of bol is.",
                   "WARNING: Adaptive refinement: curved boundary ({0} "
                   "faces, around ({1})) not recognised as a cylinder or "
                   "sphere (deviation {2}); HOMARD does not follow this "
                   "boundary (new nodes on the straight element edges). "
                   "Give the shape with #ASTER-RAND if it is a cylinder or "
                   "sphere.").format(
                len(g), _fmt(where),
                "?" if fit["dev"] is None else "%.2g" % fit["dev"]))
            continue
        desc = tr("{0} vlakken rond ({1})", "{0} faces around ({1})").format(
            len(g), _fmt(where))
        out.append((fit["shape"], fit["params"], [free[i][0] for i in g],
                    desc))
        log("INFO: Adaptive refinement: boundary recognised as {0} {1} "
            "({2} faces, deviation {3:.2g} x radius).".format(
                fit["shape"], _fmt(fit["params"]), len(g), fit["dev"]))
    return out


def _centroid(pts):
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


def _fmt(values):
    return ", ".join("%.5g" % v for v in values)


# ==========================================
# SCOPE OF THE FIRST VERSION
# ==========================================
_SOLIDS = frozenset(["hex8", "hex20", "tet4", "tet10", "pyr5", "pyr13",
                     "wedge6", "wedge15"])
# model_data keys of features that hang on node lists or node normals
# (HOMARD keeps node groups with their old nodes only)
_UNSUPPORTED_KEYS = (
    ("couplings", "koppelingen", "couplings"),
    ("contacts", "contact", "contact"),
    ("bonded", "verlijmd contact", "bonded contact"),
    ("constraint_equations", "vergelijkingen tussen knopen",
     "constraint equations"),
    ("point_masses", "puntmassa's", "point masses"),
    ("pretension_sections", "voorspansecties", "pre-tension sections"),
    ("flexible_joints", "flexibele verbindingen", "flexible joints"),
    ("line_discretes", "veren/dempers", "springs/dampers"),
)


def check_scope(model_data, analysis, comm_region=None):
    """
    ERRORs for what the first version of the HOMARD loop cannot handle.
    Returns True if the model can be refined. comm_region: the text of the
    loop (wrap), checked for node groups with more than one node.
    """
    errors = []
    shapes = set(model_data.get("elem_shapes", {}).values())
    other = sorted(s for s in shapes if s not in _SOLIDS)
    if other:
        errors.append(tr("alleen volume-elementen (hier ook {0}: schalen, "
                         "balken, veren of massa's)",
                         "solid elements only (here also {0}: shells, "
                         "beams, springs or masses)").format(
            ", ".join(other)))
    for key, nl, en in _UNSUPPORTED_KEYS:
        if model_data.get(key):
            errors.append(tr("{0} niet ondersteund", "{0} not supported")
                          .format(tr(nl, en)))
    for bc in model_data.get("bcs", []):
        if bc.get("skip"):
            continue
        if bc.get("type") == "compressiononly":
            errors.append(tr("Compression only ('{0}') niet ondersteund",
                             "Compression only ('{0}') not supported")
                          .format(bc.get("selection")))
    custom = model_data.get("aster_custom", {})
    if custom.get("failure") or (analysis or {}).get(
            "failure_plastic_strain", 0.0) > 0.0:
        errors.append(tr("bezwijken van elementen niet ondersteund",
                         "element failure not supported"))
    if model_data.get("line_quad"):
        errors.append(tr("LINE_QUAD (elem_hex8) niet ondersteund",
                         "LINE_QUAD (elem_hex8) not supported"))
    import bridge_utils
    if bridge_utils.CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        errors.append(tr("alleen resultaatroute 'liml'",
                         "result route 'liml' only"))
    if model_data.get("analysis_2d") or model_data.get("plane"):
        errors.append(tr("alleen 3D", "3D only"))
    if comm_region is not None:
        multi = multi_node_groups(model_data, comm_region)
        if multi:
            errors.append(tr(
                "knoopgroep(en) met meer dan een knoop in een last of "
                "voorwaarde: {0} (HOMARD vult knoopgroepen niet aan; zet de "
                "last of voorwaarde op een vlakselectie)",
                "node group(s) with more than one node in a load or "
                "constraint: {0} (HOMARD does not extend node groups; put "
                "the load or constraint on a face selection)").format(
                ", ".join(multi)))
    for e in errors:
        log(tr("ERROR: Adaptieve verfijning (adapt_homard): {0}. Zet "
               "adapt_homard uit of pas het model aan.",
               "ERROR: Adaptive refinement (adapt_homard): {0}. Switch "
               "adapt_homard off or change the model.").format(e))
    return not errors


_GROUP_NO_RE = re.compile(r"GROUP_NO(?:_[A-Z0-9]+)?\s*=\s*(\([^)]*\)|'[^']*')")


def multi_node_groups(model_data, text):
    """Names of node groups with more than one node that the text uses."""
    sizes = {}
    for name, ids in model_data.get("node_groups", {}).items():
        sizes[name] = len(ids)
    for name, ids in model_data.get("extra_node_groups", {}).items():
        sizes[name] = len(ids)
    used = set()
    for m in _GROUP_NO_RE.finditer(text):
        used.update(re.findall(r"'([^']+)'", m.group(1)))
    return sorted(n for n in used
                  if n == "all_nodes" or sizes.get(n, 2) > 1)


# ==========================================
# THE LOOP IN THE .comm
# ==========================================
def _indent(text):
    return "\n".join(("    " + line) if line.strip() else ""
                     for line in text.split("\n"))


def wrap(text, plan, model_data):
    """
    Put the region between the markers in a loop (see the module header).
    plan: settings() plus "kind" ("thermal"/"mechanical"), "solids"
    (Code-Aster group names), "skin" (groups for ORIE_PEAU), "boundaries"
    ([(group, shape, params)]), "ignore_pyra", "refined_med" (path or None).
    Returns the new text, or None (ERROR) if the region is not found or
    cannot be indented safely.
    """
    lines = text.split("\n")
    begin = [i for i, l in enumerate(lines) if BEGIN in l]
    end = [i for i, l in enumerate(lines) if END in l]
    if len(begin) != 1 or len(end) != 1 or end[0] <= begin[0]:
        log(tr("ERROR: Adaptieve verfijning: markeringen {0}/{1} niet in "
               "het sjabloon.",
               "ERROR: Adaptive refinement: markers {0}/{1} not in the "
               "template.").format(BEGIN, END))
        return None
    region = "\n".join(lines[begin[0] + 1:end[0]])
    if '"""' in region or "'''" in region:
        log(tr("ERROR: Adaptieve verfijning: het rekenblok bevat een "
               "tekst over meerdere regels en kan niet in de lus.",
               "ERROR: Adaptive refinement: the solve block contains a "
               "multi-line string and cannot go into the loop."))
        return None
    if not check_scope(model_data, None, region):
        return None
    loop = _loop_code(plan, _indent(region))
    return "\n".join(lines[:begin[0] + 1] + [loop] + lines[end[0]:])


def _py_str(text):
    """Python string literal for a path (as bridge_to_aster._py_str)."""
    return "'{0}'".format(text.replace("\\", "\\\\").replace("'", "\\'"))


def apply(export_path, model_data, plan, solver):
    """
    After the builder: put the loop into the .comm of export_path.
    Returns export_path, or None (ERROR) if the model cannot be refined.
    """
    import io
    import os
    import bridge_utils
    comm = None
    for line in io.open(export_path, encoding="utf-8").read().splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "F" and parts[1] == "comm":
            comm = " ".join(parts[2:-2])
    if not comm or not os.path.isfile(comm):
        log(tr("ERROR: Adaptieve verfijning: .comm niet gevonden in {0}.",
               "ERROR: Adaptive refinement: .comm not found in {0}.")
            .format(export_path))
        return None
    mods = model_data.get("elset_modelisations", {})
    solids = [g for g, m in mods.items() if str(m).startswith("3D")]
    if not solids:
        solids = ["all_elems"]
    full = dict(plan)
    full.update({
        "kind": "thermal" if str(solver).startswith("THER") else
                "mechanical",
        "solids": sorted(solids),
        "skin": list(model_data.get("skin_groups", [])),
        "boundaries": list(model_data.get("adapt_boundaries", [])),
        "ignore_pyra": bool(model_data.get("adapt_pyramids")),
        "scripts": os.path.dirname(os.path.abspath(__file__)),
        "refined_med": None})
    cfg = bridge_utils.CONFIG_BRIDGE
    if cfg.get("med_export") or cfg.get("vtu_export"):
        full["refined_med"] = _py_str(os.path.join(
            bridge_utils.work_dir_path(),
            bridge_utils.run_name("_verfijnd.rmed")))
    if full["kind"] == "mechanical":
        log(tr("WARNING: Adaptieve verfijning: de reactiekrachten gaan niet "
               "naar Mecway (knoopkrachten van het verfijnde mesh zijn "
               "niet te interpoleren naar de oorspronkelijke knopen).",
               "WARNING: Adaptive refinement: the reaction forces do not "
               "go to Mecway (nodal forces of the refined mesh cannot be "
               "interpolated to the original nodes)."))
    text = io.open(comm, encoding="utf-8").read()
    new = wrap(text, full, model_data)
    if new is None:
        return None
    f = io.open(comm, "w", encoding="utf-8")
    try:
        f.write(new)
    finally:
        f.close()
    log("INFO: Adaptive refinement (HOMARD): loop in {0} (target {1} %, "
        "max. {2} loops, max. {3} elements, {4} curved boundary group(s)"
        "{5}).".format(os.path.basename(comm), full["target"],
                       full["max_loops"], full["max_elements"],
                       len(full["boundaries"]),
                       ", pyramids ignored" if full["ignore_pyra"] else ""))
    return export_path


def _loop_code(plan, body):
    thermal = plan["kind"] == "thermal"
    solids = tuple(plan["solids"])
    front = []
    for i, (group, shape, params) in enumerate(plan["boundaries"]):
        if shape == "SPHERE":
            front.append("_F(NOM='R{0}', TYPE='SPHERE', GROUP_MA='{1}', "
                         "X_CENTRE={2!r}, Y_CENTRE={3!r}, Z_CENTRE={4!r}, "
                         "RAYON={5!r})".format(i + 1, group, *params))
        else:
            front.append("_F(NOM='R{0}', TYPE='CYLINDRE', GROUP_MA='{1}', "
                         "X_CENTRE={2!r}, Y_CENTRE={3!r}, Z_CENTRE={4!r}, "
                         "X_AXE={5!r}, Y_AXE={6!r}, Z_AXE={7!r}, "
                         "RAYON={8!r})".format(i + 1, group, *params))
    extra = []
    if front:
        extra.append("FRONTIERE_ANALYTIQUE=(\n            " +
                     ",\n            ".join(front) + ",\n        )")
    if plan.get("ignore_pyra"):
        # Pyramids in the input mesh: HOMARD stops without (S35a,
        # research_mixed.comm; catalogue macr_adap_mail.py v17.4:
        # ELEMENTS_ACCEPTES 'IGNORE_PYRA' = they are ignored)
        extra.append("ELEMENTS_ACCEPTES='IGNORE_PYRA'")
    extra_kw = "".join(",\n        " + e for e in extra)
    skin = ""
    if plan.get("skin"):
        skin = ("        mesh = MODI_MAILLAGE(reuse=mesh, MAILLAGE=mesh, "
                "ORIE_PEAU=_F(GROUP_MA_PEAU={0!r}))\n".format(
                    tuple(plan["skin"])))
    if thermal:
        ind = ("    _adapt_f = CALC_CHAMP(RESULTAT=res, GROUP_MA={0!r}, "
               "THERMIQUE=('FLUX_ELNO', 'FLUX_NOEU'))\n"
               "    _adapt_sel = _adapt_run.after_solve(_adapt_k, _adapt_f, "
               "'FLUX_ELNO', 'FLUX_NOEU', mesh)\n").format(solids)
        projected = ("res", "res_flux")
    else:
        ind = ("    _adapt_f = CALC_CHAMP(RESULTAT=res, GROUP_MA={0!r}, "
               "INST=res.getAccessParameters()['INST'][-1], "
               "CONTRAINTE=('SIGM_ELNO', 'SIGM_NOEU'))\n"
               "    _adapt_sel = _adapt_run.after_solve(_adapt_k, _adapt_f, "
               "'SIGM_ELNO', 'SIGM_NOEU', mesh)\n").format(solids)
        projected = ("res",)
    med = ""
    if plan.get("refined_med"):
        med = (
            "DEFI_FICHIER(ACTION='ASSOCIER', UNITE=79, TYPE='BINARY', "
            "FICHIER={0})\n"
            "IMPR_RESU(FORMAT='MED', UNITE=79, RESU=_F(RESULTAT=_adapt_fine['res']))\n"
            "DEFI_FICHIER(ACTION='LIBERER', UNITE=79)\n").format(
                plan["refined_med"])
    return (
        "# ===== Adaptive refinement with HOMARD (bridge_homard.py, step "
        "S35b) =====\n"
        "# Each loop: the whole solve below on the current mesh, a ZZ "
        "indicator\n"
        "# (aster_adapt.py; the native ERTH/ERZ1/ERZ2/ERME stop on HOMARD's\n"
        "# transition cells, S35a), Doerfler selection 0.5 -> group "
        "BRADAP<k>\n"
        "# -> 0/1 field CART_NEUT_R -> MACR_ADAP_MAIL RAFFINEMENT\n"
        "# CRIT_RAFF_ABS=0.5 (pattern of test case forma07b). After the "
        "loop the\n"
        "# result is projected onto the original mesh (PROJ_CHAMP with "
        "MODELE_1/2,\n"
        "# U4.72.05; node fields exact at the original nodes, element-node "
        "fields\n"
        "# from one neighbouring element: S35a) for aster_results_export.\n"
        "import sys as _adapt_sys\n"
        "_adapt_sys.path.insert(0, {scripts})\n"
        "import aster_adapt as _adapt_mod\n"
        "_adapt_run = _adapt_mod.Loop(target={target!r}, max_loops={loops!r}, "
        "max_elements={maxel!r}, fraction={frac!r}, solids={solids!r})\n"
        "_adapt_mesh0 = mesh\n"
        "for _adapt_k in range({loops} + 1):\n"
        "    if _adapt_k > 0:\n"
        "{skin}"
        "        pass\n"
        "{body}\n"
        "    if _adapt_k == 0:\n"
        "        _adapt_model0 = model\n"
        "{ind}"
        "    if _adapt_sel is None:\n"
        "        break\n"
        "    _adapt_grp = '{sel}%d' % _adapt_k\n"
        "    mesh.setGroupOfCells(_adapt_grp, _adapt_sel)\n"
        "    _adapt_ind = CREA_CHAMP(TYPE_CHAM='CART_NEUT_R', "
        "OPERATION='AFFE', MAILLAGE=mesh, AFFE=(\n"
        "        _F(TOUT='OUI', NOM_CMP='X1', VALE=0.0),\n"
        "        _F(GROUP_MA=_adapt_grp, NOM_CMP='X1', VALE=1.0)))\n"
        "    _adapt_name = 'bradap%d' % (_adapt_k + 1)\n"
        "    MACR_ADAP_MAIL(\n"
        "        ADAPTATION='RAFFINEMENT', CHAM_GD=_adapt_ind, "
        "CRIT_RAFF_ABS=0.5,\n"
        "        MAILLAGE_N=mesh, MAILLAGE_NP1=CO(_adapt_name){extra})\n"
        "    # HOMARD can fail without an exception (no new mesh; S35a)\n"
        "    if _adapt_name not in globals():\n"
        "        _adapt_run.homard_failed(_adapt_k)\n"
        "        break\n"
        "    mesh = globals()[_adapt_name]\n"
        "_adapt_run.summary()\n"
        "_adapt_fine = dict((k, globals()[k]) for k in {proj!r} "
        "if k in globals())\n"
        "for _adapt_key, _adapt_res in _adapt_fine.items():\n"
        "    globals()[_adapt_key] = PROJ_CHAMP(\n"
        "        RESULTAT=_adapt_res, MODELE_1=model, MODELE_2=_adapt_model0,\n"
        "        NOM_CHAM=_adapt_mod.projected_fields(_adapt_res))\n"
        "model = _adapt_model0\n"
        "mesh = _adapt_mesh0\n"
        "{med}"
        "# ===== end of the adaptive refinement =====").format(
            target=plan["target"], loops=plan["max_loops"],
            maxel=plan["max_elements"], frac=DORFLER, solids=solids,
            skin=skin, body=body, ind=ind, sel=SELECT_PREFIX,
            extra=extra_kw, proj=projected, med=med,
            scripts=_py_str(plan["scripts"]))


# ==========================================
# AFTER THE RUN
# ==========================================
_REPORT_RE = re.compile(r"^BRIDGE_ADAPT (.*)$")


def report(mess_path):
    """Status lines from the BRIDGE_ADAPT lines of the .mess (one per
    loop and the reason for stopping), translated."""
    out = []
    try:
        import io
        text = io.open(mess_path, encoding="utf-8", errors="replace").read()
    except Exception:
        return out
    for line in text.splitlines():
        m = _REPORT_RE.match(line.strip())
        if not m:
            continue
        words = dict(w.split("=", 1) for w in m.group(1).split()
                     if "=" in w)
        if "loop" in words and "error" in words:
            out.append(tr("Adaptieve verfijning lus {0}: {1} elementen, "
                          "globale fout (ZZ) {2} %",
                          "Adaptive refinement loop {0}: {1} elements, "
                          "global error (ZZ) {2} %").format(
                words["loop"], words.get("cells", "?"), words["error"]))
        elif "stop" in words:
            reason = words["stop"]
            texts = {
                "target": tr("doel bereikt", "target reached"),
                "loops": tr("maximum aantal lussen bereikt",
                            "maximum number of loops reached"),
                "elements": tr("het maximum aantal elementen zou "
                               "overschreden worden",
                               "the maximum number of elements would be "
                               "exceeded"),
                "rising": tr("de fout stijgt twee lussen achter elkaar",
                             "the error rose in two loops in a row"),
                "homard": tr("HOMARD maakte geen nieuw mesh (zie .mess)",
                             "HOMARD made no new mesh (see .mess)"),
                "none": tr("geen elementen te verfijnen",
                           "no elements to refine"),
            }
            out.append(tr("Adaptieve verfijning gestopt: {0}.",
                          "Adaptive refinement stopped: {0}.").format(
                texts.get(reason, reason)))
    for line in out:
        log("INFO: " + line)
    return out
