# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_mesh.py
# Responsibility: write the mesh directly from the .liml (model_data of
# bridge_from_liml.py) in the ASTER mesh format (LIRE_MAILLAGE
# FORMAT='ASTER') and adjust model_data to it. A Gmsh export is no
# longer needed.
#
# Why no longer via Gmsh (checked with Code-Aster 17.4):
#   - LIRE_MAILLAGE FORMAT='GMSH' first converts the file with PRE_GMSH; that
#     truncates group names to 8 characters ('Sixteen_chars_16' -> 'Sixteen_').
#     The ASTER format reads names up to 24 characters (25 gave MODELISA7_82).
#   - In Gmsh an element belongs to one group; here an element may be in
#     several groups (a face in two selections, beam orientation).
#   - Node groups can go directly into the mesh.
#
# Groups: every component (elset) becomes GROUP_MA, every nodeselection
# GROUP_NO, every faceselection GROUP_MA of boundary elements (or of the
# shell elements themselves), every elementselection GROUP_MA. The names stay
# those of Mecway; only names that Code-Aster does not accept are
# adjusted (see _aster_name).
#
# Node order per element type (_ASTER_TYPES): for 3D equal to Mecway
# (corner nodes, then mid nodes); derived from the geometry of Mecway
# example models (mid node = middle of which edge) and compared
# with the order PRE_GMSH writes. 1D/2D elements are stored in the .liml
# alternately (corner, mid, corner, ...); Code-Aster wants the corners first.
#
# Compatible with IronPython 2.7.9.

import math
import re
from collections import OrderedDict

from bridge_utils import (log, tr, error_estimator_requested,
                          get_active_analysis)
from bridge_bcs import SUPPORTED_BCS, _angl_naut, is_position


# Maximum group name length in Code-Aster (ASTER format, checked).
ASTER_NAME_MAX = 24

# Names of the groups for free nodes.
POI1_GROUP_T = "BRPOI1T"    # DIS_T  (translations only)
POI1_GROUP_R = "BRPOI1R"    # DIS_TR (translations + rotations)
# Boundary elements on the free (unloaded, unconstrained) faces of
# volume elements, for the error estimator (_free_faces, bridge_to_aster
# _error_estimator_block).
ERR_FREE_GROUP = "BRERRVRIJ"

_SOLID_SHAPES = frozenset({"hex8", "hex20", "tet4", "tet10", "pyr5",
                           "pyr13", "wedge6", "wedge15"})
_SHELL_SHAPES = frozenset({"tri3", "tri6", "quad4", "quad8"})
_BEAM_SHAPES = frozenset({"line2", "line3"})

# Mecway shape -> (Code-Aster type, Mecway index per Code-Aster position).
# pyr13 occurs in no Mecway example, but it does in the transitions of
# Mecway's refine_x2 on hex20 (step S7): there the mid nodes are in this
# order (corners + mids as in Code-Aster; checked on the position of
# every mid node, tests_adaptief AD-02). Code-Aster solves those meshes
# without alarm.
_ASTER_TYPES = {
    "line2":   ("SEG2",    [0, 1]),
    "line3":   ("SEG3",    [0, 2, 1]),
    "tri3":    ("TRIA3",   [0, 1, 2]),
    "tri6":    ("TRIA6",   [0, 2, 4, 1, 3, 5]),
    "quad4":   ("QUAD4",   [0, 1, 2, 3]),
    "quad8":   ("QUAD8",   [0, 2, 4, 6, 1, 3, 5, 7]),
    "tet4":    ("TETRA4",  list(range(4))),
    "tet10":   ("TETRA10", list(range(10))),
    "pyr5":    ("PYRAM5",  list(range(5))),
    "pyr13":   ("PYRAM13", list(range(13))),
    "wedge6":  ("PENTA6",  list(range(6))),
    "wedge15": ("PENTA15", list(range(15))),
    "hex8":    ("HEXA8",   list(range(8))),
    "hex20":   ("HEXA20",  list(range(20))),
}
# Modelisations for which a line3 element is split into two SEG2
# cells. POU_D_E exists only on SEG2 (catalogue
# phenomenons_modelisations.py, see bridge_from_liml STEP 2b); for POU_D_T
# assumed (NOT verified), the bridge knows no quadratic beam element
# in Code-Aster. Two Euler cells each interpolate cubically, so
# at least as good as a quadratic beam (Mecway's line3 beam only solves
# with CCX, B32R; verification LS-50). Solved with POU_D_T: LS-51e
# +0.09 % (shear), Code-Aster 17.4. POU_D_T_GD (large rotations, SEG2
# only like POU_D_E) likewise: verification NL-84 (90-degree bend with line3).
# The mid node becomes an ordinary node with 6 degrees of freedom.
# BARRE and CABLE (line3 truss / tension-only) likewise: BARRE exists only
# on SEG2 (MODELISATION='BARRE' on SEG3 gave MODELE1_6, Code-Aster 17.4,
# GitHub issue #6); the midside node then gets Mecway's transverse
# condition (_line3_truss_links), otherwise it is a mechanism.
_LINE3_SPLIT_MODS = ("POU_D_E", "POU_D_T", "POU_D_T_GD", "BARRE", "CABLE")
# Bars: the midside node has no transverse stiffness of its own
_LINE3_BAR_MODS = ("BARRE", "CABLE")
# Group of the POI1 cells (DIS_TR, stiffness 0) on nodes of a flexible
# joint without another element with rotations (_flexible_joints)
JOINT_GROUP = "BRJOINT"

_N_CORNERS = {"SEG2": 2, "SEG3": 2, "TRIA3": 3, "TRIA6": 3, "QUAD4": 4,
              "QUAD8": 4, "TETRA4": 4, "TETRA10": 4, "PYRAM5": 5,
              "PYRAM13": 5, "PENTA6": 6, "PENTA15": 6, "HEXA8": 8,
              "HEXA20": 8}
# Edges of the mid nodes in Code-Aster order (corner indices).
_MID_EDGES = {
    "SEG3":    [(0, 1)],
    "TRIA6":   [(0, 1), (1, 2), (2, 0)],
    "QUAD8":   [(0, 1), (1, 2), (2, 3), (3, 0)],
    "TETRA10": [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)],
    "PYRAM13": [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 4), (2, 4),
                (3, 4)],
    "PENTA15": [(0, 1), (1, 2), (0, 2), (0, 3), (1, 4), (2, 5), (3, 4),
                (4, 5), (3, 5)],
    "HEXA20":  [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 5), (2, 6),
                (3, 7), (4, 5), (5, 6), (6, 7), (4, 7)],
}
# Corner nodes per faceid, in the order of mw.face_nodes() in Mecway 33
# (read out with an element of every shape). Only used without the
# Mecway API (offline tests); in Mecway the bridge uses mw.face_nodes()
# and logs a difference with this table. Shells: 1..3/4 are the edges,
# 5 the face and 6 the same face with the reversed normal.
_FACE_CORNERS = {
    "HEXA":  {1: [0, 3, 2, 1], 2: [4, 5, 6, 7], 3: [0, 1, 5, 4],
              4: [1, 2, 6, 5], 5: [2, 3, 7, 6], 6: [3, 0, 4, 7]},
    "TETRA": {1: [0, 2, 1], 2: [0, 1, 3], 3: [2, 3, 1], 4: [0, 3, 2]},
    "PENTA": {1: [0, 2, 1], 2: [3, 4, 5], 3: [0, 1, 4, 3],
              4: [1, 2, 5, 4], 5: [2, 0, 3, 5]},
    "PYRAM": {1: [0, 1, 4], 2: [1, 2, 4], 3: [2, 3, 4], 4: [3, 0, 4],
              5: [0, 3, 2, 1]},
    "TRIA":  {1: [0, 1], 2: [1, 2], 3: [2, 0], 5: [0, 1, 2], 6: [2, 1, 0]},
    "QUAD":  {1: [0, 1], 2: [1, 2], 3: [2, 3], 4: [3, 0], 5: [0, 1, 2, 3],
              6: [3, 2, 1, 0]},
    "SEG":   {1: [0, 1], 2: [0], 3: [1]},
}


# ==========================================
# VECTORS
# ==========================================
def _vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _vunit(a):
    n = math.sqrt(_vdot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


# Integration points (xi, eta, weight). Triangle: 6-point rule, exact up to
# degree 4 (Dunavant); quadrilateral: 3x3 Gauss.
_TRI_GAUSS = []
for _a, _w in ((0.445948490915965, 0.111690794839005),
               (0.091576213509771, 0.054975871827661)):
    _TRI_GAUSS += [(_a, _a, _w), (1.0 - 2.0 * _a, _a, _w),
                   (_a, 1.0 - 2.0 * _a, _w)]
_QUAD_GAUSS = [(x, y, wx * wy)
               for x, wx in ((-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
                             (0.774596669241483, 5.0 / 9.0))
               for y, wy in ((-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
                             (0.774596669241483, 5.0 / 9.0))]
_QUAD_CORNERS = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]


def _face_shape(stype, xi, eta):
    """Shape functions of a boundary element in Code-Aster order (corners, then
    mid node k between corner k and k+1)."""
    if stype.startswith("TRIA"):
        l = (1.0 - xi - eta, xi, eta)
        if stype == "TRIA3":
            return list(l)
        return ([li * (2.0 * li - 1.0) for li in l] +
                [4.0 * l[0] * l[1], 4.0 * l[1] * l[2], 4.0 * l[2] * l[0]])
    if stype == "QUAD4":
        return [0.25 * (1 + xi * a) * (1 + eta * b) for a, b in _QUAD_CORNERS]
    n = [0.25 * (1 + xi * a) * (1 + eta * b) * (xi * a + eta * b - 1)
         for a, b in _QUAD_CORNERS]
    return n + [0.5 * (1 - xi * xi) * (1 - eta), 0.5 * (1 + xi) * (1 - eta * eta),
                0.5 * (1 - xi * xi) * (1 + eta), 0.5 * (1 - xi) * (1 - eta * eta)]


def _face_integrals(stype, pts):
    """
    Integrals over the face (Gauss):
      w[i] = int(N_i dA)      - sum = area (also curved quadratic);
                                 nodal weights of an average
      m[i] = int(N_i x dA)    - first moments per node (vector)
      S    = int(x x^T dA)    - second moment (3x3), for moment distribution
    """
    rule = _TRI_GAUSS if stype.startswith("TRIA") else _QUAD_GAUSS
    h = 1.0e-3   # central difference: exact for quadratic N
    w = [0.0] * len(pts)
    m = [[0.0, 0.0, 0.0] for _ in pts]
    S = [[0.0] * 3 for _ in range(3)]
    for xi, eta, gw in rule:
        n = _face_shape(stype, xi, eta)
        np_ = _face_shape(stype, xi + h, eta)
        nm = _face_shape(stype, xi - h, eta)
        ep = _face_shape(stype, xi, eta + h)
        em = _face_shape(stype, xi, eta - h)
        dx = [sum((np_[i] - nm[i]) / (2 * h) * pts[i][c]
                  for i in range(len(pts))) for c in range(3)]
        de = [sum((ep[i] - em[i]) / (2 * h) * pts[i][c]
                  for i in range(len(pts))) for c in range(3)]
        cr = _vcross(dx, de)
        jac = math.sqrt(_vdot(cr, cr))
        x = [sum(n[i] * pts[i][c] for i in range(len(pts))) for c in range(3)]
        for i in range(len(pts)):
            w[i] += gw * jac * n[i]
            for c in range(3):
                m[i][c] += gw * jac * n[i] * x[c]
        for a in range(3):
            for b in range(3):
                S[a][b] += gw * jac * x[a] * x[b]
    return w, m, S


def _inv3(a):
    """Inverse of a 3x3 matrix (list of rows)."""
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) -
           a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) +
           a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    cof = [[a[(r + 1) % 3][(c + 1) % 3] * a[(r + 2) % 3][(c + 2) % 3] -
            a[(r + 1) % 3][(c + 2) % 3] * a[(r + 2) % 3][(c + 1) % 3]
            for r in range(3)] for c in range(3)]
    return [[cof[r][c] / det for c in range(3)] for r in range(3)]


def _cell_names(eid, split):
    """Names of the mesh cells of Mecway element eid: M<eid>, and for a
    split line3 beam also H<eid> (second half). Cell names in the
    ASTER format have max. 8 characters: eid up to 9999999."""
    if split:
        return ["M{0}".format(eid), "H{0}".format(eid)]
    return ["M{0}".format(eid)]


def cell_names_of(model_data, eid):
    """Cell names of Mecway element eid after write_mesh (see _cell_names);
    for other modules (bridge_to_aster, DEFI_GROUP MAILLE)."""
    return _cell_names(eid, eid in model_data.get("line3_split", ()))


def _mecway_v_axis(p1, p2, orient):
    """
    V axis of a beam element from p1 to p2, as Mecway determines it
    (Mecway manual v33 par. 7.5):
      - with vector: projection of the vector onto the plane normal to U,
        then rotation about U by 'angle' (right-handed; checked with a
        CCX export of Mecway: U=+X, vector Z, angle -90 degrees -> V=+Y);
      - without vector: V perpendicular to Z, in the XY plane (V = Z x U); if
        the element is (nearly) parallel to Z (gradient < 0.01 %), then V = Y.
    orient: {"vec": (vx, vy, vz), "angle": rad} or None.
    """
    u = _vunit(_vsub(p2, p1))
    vec = orient["vec"] if orient else None
    if vec is not None and _vdot(vec, vec) > 0.0:
        d = _vdot(vec, u)
        v = (vec[0] - d * u[0], vec[1] - d * u[1], vec[2] - d * u[2])
        if _vdot(v, v) > 1.0e-18 * _vdot(vec, vec):
            v = _vunit(v)
            a = orient.get("angle", 0.0)
            if a:
                w = _vcross(u, v)
                v = tuple(v[i] * math.cos(a) + w[i] * math.sin(a)
                          for i in range(3))
            return v
        log(tr("WARNING: Orientatievector {0} is evenwijdig aan de balk; "
               "standaardorientatie gebruikt.",
               "WARNING: Orientation vector {0} is parallel to the beam; "
               "default orientation used.").format(vec))
    if math.sqrt(u[0] ** 2 + u[1] ** 2) < 1.0e-4 * abs(u[2]):
        return (0.0, 1.0, 0.0)
    return _vunit(_vcross((0.0, 0.0, 1.0), u))


# ==========================================
# NAMES
# ==========================================
def _aster_names(names, reserved=()):
    """
    {Mecway name: Code-Aster name}. In the mesh Code-Aster only accepts
    names that start with a letter, with letters, digits and '_', up to 24
    characters (checked with Code-Aster 17.4: '02Contact', 'Linear(2)', 'Fix-Z'
    and 'a.b' gave an error in LIRE_MAILLAGE). Invalid characters become '_',
    a name that does not start with a letter gets 'G' in front; then
    made unique, also against the names the bridge creates itself
    (_GENERATED_NAME_RE).
    """
    used = set(reserved)
    mapping = OrderedDict()
    for name in names:
        if name in mapping:
            continue
        cand = re.sub(r"[^A-Za-z0-9_]", "_", name)
        if not cand or not cand[0].isalpha():
            cand = "G" + cand
        cand = cand[:ASTER_NAME_MAX]
        cand = _unique_name(cand, used)
        used.add(cand)
        mapping[name] = cand
        if cand != name:
            log("INFO: Group name '{0}' -> '{1}' (Code-Aster: letter first, "
                "only letters/digits/_, max. {2} characters, unique).".format(
                    name, cand, ASTER_NAME_MAX))
    return mapping


# Group names the bridge creates itself (after renaming, with a counter):
# bridge_mesh BRSY/BRCO/BRESCL/BROV/BRFR (_extra_node_group), BRMAIT
# (_bonded), CMAIT/CESCL (_merge_contact_zones), BRES/BRMA/BRRI
# (_build_discretes), BOR (beam orientation), BRPOI1T/R; bridge_to_aster
# BRGAP (gaps), BRCT (mid nodes) and tab_<concept>_n<i>
# (result tables); bridge_thermal TH/THS/THN; bridge_xfem BRXF<n>S/F
# (crack from an XFEM_ face selection). A user name of
# that form is renamed, so that it cannot clash with a generated group.
_GENERATED_NAME_RE = re.compile(
    r"^(?:(?:BRSY|BRCO|BRESCL|BROV|BRFR|BRMAIT|CMAIT|CESCL|BRES|BRMA|BRRI|BOR|"
    r"BRGAP|BRCT|THS|THN|TH)\d+|BRXF\d+[SF]|BRPOI1[TR]|all_elems|all_nodes|"
    r"tab_\w+_n\d+)$")


def _unique_name(cand, used):
    """cand, or cand with '_1', '_2', ... (max. ASTER_NAME_MAX characters) if
    it is already used or has the form of a generated group."""
    base, i = cand, 1
    while cand in used or _GENERATED_NAME_RE.match(cand):
        suffix = "_{0}".format(i)
        cand = base[:ASTER_NAME_MAX - len(suffix)] + suffix
        i += 1
    return cand


def _selection_names(model_data, renames, reserved, elset_members):
    """
    {Mecway name: Code-Aster name} for selections. A face or
    element selection with the same name as an elset (component) would
    overwrite the elset group as GROUP_MA (the elements then silently dropped
    out of the model); such a selection gets its own name with '_1', '_2', ...
    All references to the selection (BCs, contact, couplings) go
    via this name. Not node selections: a GROUP_NO may have the same name
    as a GROUP_MA.
    """
    out = OrderedDict(renames)
    elsets = set(elset_members)
    for key in ("elsets", "elset_dims", "elset_modelisations"):
        elsets.update(model_data.get(key, {}).keys())
    used = set(reserved) | set(renames.values())
    for name in (list(model_data.get("face_selection_faces", {}).keys()) +
                 list(model_data.get("element_selections", {}).keys())):
        if name not in elsets or out.get(name) != renames.get(name, name):
            continue
        new = _unique_name(renames.get(name, name), used)
        used.add(new)
        out[name] = new
        log(tr("WARNING: Selectie '{0}' heeft dezelfde naam als een "
               "component (elset); in Code-Aster heet de selectie '{1}'. "
               "<<{0}>> in #ASTER-regels is de component. Geef de selectie "
               "in Mecway liever een eigen naam.",
               "WARNING: Selection '{0}' has the same name as a component "
               "(elset); in Code-Aster the selection is called '{1}'. "
               "<<{0}>> in #ASTER lines is the component. Preferably give "
               "the selection its own name in Mecway.").format(name, new))
    return out


def _real(value):
    """Number for the ASTER mesh format: 15 significant digits and always
    a decimal point. '-1e-05' gave <EXCEPTION> <MODELISA7_85> 'un nombre
    est attendu' (Code-Aster 17.4); '-1.0e-05' and '0.0' are read."""
    # %-formatting: "{0:.15g}".format() follows the locale in Mecway's
    # IronPython and gave '0,25' under a Dutch locale (seen in
    # the IronPython harness); Code-Aster then stopped with MODELISA7_66.
    txt = "%.15g" % value
    if "." in txt or "n" in txt:          # already a point, or inf/nan
        return txt
    mant, sep, exp = txt.partition("e")
    return mant + ".0" + sep + exp


def _wrap(items, width=79):
    """Lines ' item item ...' of at most width characters. LIRE_MAILLAGE
    FORMAT='ASTER' reads at most 80 characters per line: a longer HEXA20
    line gave <EXCEPTION> <MODELISA7_66> 'item attendu en debut de ligne'
    (Code-Aster 17.4); an element may continue over several lines."""
    lines = []
    cur = ""
    for it in items:
        if cur and len(cur) + 1 + len(it) > width:
            lines.append(cur)
            cur = ""
        cur += " " + it
    if cur:
        lines.append(cur)
    return lines


# ==========================================
# FACES
# ==========================================
def _face_from_table(aster_type, conn, faceid):
    """Corner nodes of a face from _FACE_CORNERS, or None."""
    for prefix, table in _FACE_CORNERS.items():
        if aster_type.startswith(prefix):
            corners = table.get(faceid)
            return [conn[i] for i in corners] if corners else None
    return None


def _skin_element(aster_type, conn, face_nids):
    """
    (type, nodes) of a boundary element in Code-Aster order: corner nodes in
    the order of face_nids, mid nodes per edge from the parent element.
    """
    nc = _N_CORNERS[aster_type]
    corner_set = set(conn[:nc])
    corners = [n for n in face_nids if n in corner_set]
    mids = []
    if aster_type in _MID_EDGES:
        midmap = {}
        for k, (a, b) in enumerate(_MID_EDGES[aster_type]):
            midmap[frozenset((conn[a], conn[b]))] = conn[nc + k]
        ring = corners + corners[:1] if len(corners) > 2 else corners
        for a, b in zip(ring[:-1], ring[1:]):
            mids.append(midmap[frozenset((a, b))])
    if len(corners) == 2:
        return ("SEG3" if mids else "SEG2"), corners + mids
    if len(corners) == 3:
        return ("TRIA6" if mids else "TRIA3"), corners + mids
    return ("QUAD8" if mids else "QUAD4"), corners + mids


# Conditions that impose displacements: a face with all corner nodes fixed
# this way is a Dirichlet boundary for the error estimator (_free_faces).
_DIRICHLET_BCS = frozenset(["fixed", "pinnedsupport", "displacement",
                            "noderotation", "frictionless", "symmetry",
                            "compressiononly", "elasticsupport"])


# Modelisations with rotational degrees of freedom at nodes (_flexible_joints)
_ROT_MODS = frozenset(["POU_D_E", "POU_D_T", "POU_D_TG", "POU_D_T_GD",
                       "DKT", "DST",
                       "COQUE_3D", "DIS_TR"])
_ROT_DOFS = ("DRX", "DRY", "DRZ")


def _selection_nodes(model_data, sel, conn, face_group_nodes):
    """Nodes of a Mecway selection (nodes, beam faces, elements)."""
    ids = model_data.get("node_groups", {}).get(sel)
    if ids is not None:
        return set(int(str(i).lstrip("N")) for i in ids)
    if sel in face_group_nodes:
        return set(face_group_nodes[sel])
    eids = model_data.get("element_selections", {}).get(sel)
    if eids is not None:
        return set(n for e in eids if e in conn for n in conn[e][1])
    return set()


# Curved line3 beam (KNOWN_BUGS 107): distance of the midside node to the
# chord, relative to the chord length. 1e-3 = kink of about 0.23 degrees
# between the two straight halves (angle ~ 4 * bow rad); below that the
# split is practically exact (choice, NOT measured against Mecway).
_LINE3_CURVED = 1.0e-3


def _line3_bow(nodes, cn):
    """Distance of the midside node cn[2] of a line3 element (Code-Aster
    order: ends cn[0], cn[1]) to the chord, divided by the chord length;
    0 if a node is missing or the chord has length 0."""
    if any(n not in nodes for n in cn[:3]):
        return 0.0
    a, b, m = nodes[cn[0]], nodes[cn[1]], nodes[cn[2]]
    chord = _vsub(b, a)
    length = math.sqrt(_vdot(chord, chord))
    if length <= 0.0:
        return 0.0
    am = _vsub(m, a)
    t = _vdot(am, chord) / (length * length)
    off = [am[i] - t * chord[i] for i in range(3)]
    return math.sqrt(_vdot(off, off)) / length


def _line3_truss_links(model_data, nodes, conn, elements, split_line3,
                       elset_mods, face_group_nodes):
    """
    Midside node of a split line3 truss (BARRE/CABLE, _LINE3_SPLIT_MODS).
    Two bars in series have no stiffness across the chord at the midside
    node: without a condition Code-Aster stops with ALGELINE3_81 (zero
    pivot, run for GitHub issue #6). Mecway's quadratic truss interpolates
    only the axial displacement quadratically; across the chord the
    midside node follows the ends linearly (NIET geverifieerd in Mecway's
    broncode; NAFEMS CP5 with this condition 451.1/1049.9 Hz as the
    reference, verification MO-08). Per element and per direction p
    perpendicular to the chord a LIAISON_DDL (U4.44.01, via
    model_data["constraint_equations"], bridge_to_aster._render_mpcs):
    p . u_mid - 0.5 p . u_a - 0.5 p . u_b = 0.
    A global axis perpendicular to the chord that is fixed (DDL_IMPO) on
    all three nodes (for example uz = 0 for a plane truss) is skipped:
    that equation would be redundant and the matrix singular. Returns the
    number of equations.
    """
    fixed = {}       # nid -> set(DX/DY/DZ) fixed by a kinematic condition
    for bc in model_data.get("bcs", []):
        # Hard kinematic conditions only (a spring or compression-only
        # support does not fix the DOF). Symmetry and frictionless only
        # with explicit global DX/DY/DZ: their per-node directions
        # (bc["oblique"]) are made later, in _apply_to_model_data, and the
        # broad _bc_dofs fallback ("all fixed") would drop the midside
        # condition and leave a mechanism (KNOWN_BUGS 107).
        if bc.get("skip") or bc.get("type") not in (
                "fixed", "pinnedsupport", "displacement", "symmetry",
                "frictionless"):
            continue
        d = bc.get("aster_dict") or {}
        if "ANGL_NAUT" in d:
            continue
        if bc["type"] == "pinnedsupport" or (
                bc["type"] == "fixed" and "BLOCAGE" in d):
            dofs = set(("DX", "DY", "DZ"))
        else:
            dofs = set(k for k in d if k in ("DX", "DY", "DZ"))
        if not dofs:
            continue
        for n in _selection_nodes(model_data, bc.get("selection"), conn,
                                  face_group_nodes):
            fixed.setdefault(n, set()).update(dofs)
    eqs = model_data.setdefault("constraint_equations", [])
    n_eq = 0
    for eid, shape, _enodes, es in elements:
        if (eid not in split_line3 or
                elset_mods.get(es) not in _LINE3_BAR_MODS):
            continue
        a, b, mid = conn[eid][1][:3]
        chord = _vsub(nodes[b], nodes[a])
        if _vdot(chord, chord) <= 0.0:
            continue
        u = _vunit(chord)
        common = (fixed.get(a, set()) & fixed.get(b, set()) &
                  fixed.get(mid, set()))
        covered = [tuple(1.0 if j == i else 0.0 for j in range(3))
                   for i in range(3)
                   if "D" + "XYZ"[i] in common and abs(u[i]) < 1.0e-9]
        for p in _complement([u] + covered):
            terms = []
            for nid, w in ((mid, 1.0), (a, -0.5), (b, -0.5)):
                for i in range(3):
                    if abs(p[i]) > 1.0e-12:
                        terms.append((nid, "D" + "XYZ"[i], w * p[i]))
            if all(d in fixed.get(nid, ()) for nid, d, _c in terms):
                continue        # all degrees of freedom already fixed
            eqs.append({"terms": terms, "constant": 0.0,
                        "source": "line3truss"})
            n_eq += 1
    return n_eq


def _complement(axes):
    """Orthonormal basis of the complement of the span of axes (3D)."""
    basis = []
    for a in list(axes) + [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                           (0.0, 0.0, 1.0)]:
        v = list(a)
        for b in basis:
            d = _vdot(v, b)
            v = [v[i] - d * b[i] for i in range(3)]
        if _vdot(v, v) > 1.0e-12:
            basis.append(_vunit(v))
    return basis[len(_span(axes)):]


def _span(axes):
    """Orthonormal basis of the span of axes."""
    basis = []
    for a in axes:
        v = list(a)
        for b in basis:
            d = _vdot(v, b)
            v = [v[i] - d * b[i] for i in range(3)]
        if _vdot(v, v) > 1.0e-12:
            basis.append(_vunit(v))
    return basis


def _rot_terms(nid, axis, sign):
    """Terms (node, DDL, coef) of sign * (rotation of nid along axis)."""
    return [(nid, d, sign * c) for d, c in zip(_ROT_DOFS, axis)
            if abs(c) > 1.0e-12]


def _joint_ends(model_data, conn, elements, faces_of):
    """{(eid, node)}: beam ends in the face selections of flexible joints
    (without checks or messages; _flexible_joints does those). For
    bridge_offset.prepare: such an end is no longer attached to the Mecway node
    and so carries no rotations there."""
    out = set()
    shapes = dict((eid, shape) for eid, shape, en, es in elements)
    faces_by_sel = model_data.get("face_selection_faces", {})
    for j in model_data.get("flexible_joints") or []:
        for eid, fid in faces_by_sel.get(j["selection"]) or []:
            if eid not in conn or shapes.get(eid) not in _BEAM_SHAPES:
                continue
            fn = list(faces_of(eid, fid))
            if len(fn) == 1:
                out.add((eid, fn[0]))
    return out


def _warn_joint_element_constraints(model_data, jointed, elem_info):
    """
    WARNING for a constraint (_DIRICHLET_BCS) on an element selection or
    component that contains a beam element with a flexible joint: in
    Code-Aster it acts on the cells (GROUP_MA), so also on the joint's own
    node, which the coupling (LIAISON_DDL) ties to the Mecway node; the
    Mecway node itself is only constrained if another element of the
    selection contains it (Mecway constrains the nodes of the elements). If
    both are constrained, the relations are double: FACTOR_11 seen in a run
    (KNOWN_BUGS 106a), but two offline LS-51a variants ran without it.
    A selection of nodes or faces only acts on the Mecway node, like Mecway.
    """
    node_groups = model_data.get("node_groups", {})
    faces = model_data.get("face_selection_faces", {})
    elem_sel = model_data.get("element_selections", {})
    hits = []
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _DIRICHLET_BCS or bc.get("skip"):
            continue
        sel = bc.get("selection")
        if sel in node_groups or sel in faces:
            continue
        if sel in elem_sel:
            eids = set(elem_sel[sel])
        else:       # component (elset) name
            eids = set(e for e, (_s, es) in elem_info.items() if es == sel)
        if eids & jointed and sel not in hits:
            hits.append(sel)
    if hits:
        log(tr("WARNING: Voorwaarde op elementselectie/component {0} met "
               "een balkelement met een flexible joint: in Code-Aster werkt "
               "die op de eigen knoop van de joint (aan de Mecway-knoop "
               "gekoppeld), niet zoals in Mecway op de knopen van het "
               "element. Het resultaat kan daardoor afwijken en een dubbele "
               "voorwaarde kan Code-Aster laten stoppen met FACTOR_11. Zet "
               "de voorwaarde op knopen of vlakken (KNOWN_BUGS 106).",
               "WARNING: Constraint on element selection/component {0} "
               "containing a beam element with a flexible joint: in "
               "Code-Aster it acts on the joint's own node (coupled to the "
               "Mecway node), not on the nodes of the element as in Mecway. "
               "The result can therefore differ, and a double constraint "
               "can make Code-Aster stop with FACTOR_11. Put the constraint "
               "on nodes or faces (KNOWN_BUGS 106).").format(
                   ", ".join("'{0}'".format(s) for s in hits)))


def _flexible_joints(model_data, nodes, conn, elements, faces_of, by_type,
                     cell_refs, split_line3, face_group_nodes, poi_rot,
                     poi_any, offset_plan=None, offset_poi=frozenset()):
    """
    Flexible joint on beam (Mecway manual v33 par. 9.12; XML in
    bridge_from_liml._parse_model_item): the end of a beam element
    rotates freely about the chosen local axes U (beam axis), V and W.

    Translation: at that end the element gets its own node at the
    same place (number after the Mecway nodes; in the mesh only for that
    cell, so by_type gets a copy of the node list, conn keeps the
    Mecway nodes). That node is coupled with LIAISON_DDL (U4.44.01; via
    model_data["constraint_equations"], bridge_to_aster._render_mpcs) to the
    Mecway node: DX, DY, DZ equal and the rotation along every
    non-free local axis e equal (e . theta_new = e . theta_old). Local
    axes as in Mecway (_mecway_v_axis): U along the (half) cell, V from the
    orientation, W = U x V (checked with Mecway 34: beam along X, <rotw />
    = hinge about Z).

    If the Mecway node has no other element with rotations (all beams there
    have a joint, or only volume elements), it gets a POI1
    DIS_TR with stiffness 0 (group JOINT_GROUP) and the rotations along
    the complement of the coupled axes are set to 0 (Mecway shows
    rotation 0 there, seen with a hinge with joints on both sides), unless
    a condition on that node already fixes rotations.

    Element offset (bridge_offset.prepare, offset_plan["cells"]: elements
    on their own nodes, rigid arm Mecway node N -> offset node O): the
    joint sits at the end of the arm, between O and the element, as in
    Mecway 34 (LS-52c, headless: the torsion of the released half is 0,
    the deflection is the same either way). Order: N -> rigid arm (the
    offset link of bridge_offset) -> joint -> element. The own node lies
    at O, replaces O in the cell of the element and is coupled to O as
    above (axes of the element, parallel to N-N'). An O that is then in
    no cell gets a POI1 DIS_TR; the own node goes in a node group BROFL
    with N (offset_plan["joint_pairs"], bridge_offset.apply_to_mesh), so
    that aster_results_export maps its values to N. (The fork by
    MishalTPC, commit 773d59f, put the release at N, before the arm.)
    Only in linear static and modal (_joint_on_offset_supported) and not
    for a split line3 element (two cells): otherwise a WARNING and the
    element stays rigidly attached to the arm (KNOWN_BUGS 108d). An
    offset element without
    joint is no longer attached to the Mecway node but does carry its
    rotations via the arm; if the node is in no other cell, it gets a POI1
    DIS_TR (without extra relations), otherwise it has no degrees of
    freedom for the LIAISON_DDL. offset_poi: Mecway nodes whose only
    rotational POI1 is the zero-stiffness DIS_TR of the offset
    (bridge_offset.discretes): those do not count as a rotation carrier.

    Returns (extra nodes {nid: xyz}, POI1 nodes) or (None, None) without
    joints. Results: the extra nodes are dropped (aster_results_export
    only reads the Mecway nodes; their reaction adds to the Mecway node
    at the same place).
    """
    joints = model_data.get("flexible_joints") or []
    if not joints:
        return None, None
    mods = model_data.get("elset_modelisations", {})
    elem_info = dict((eid, (shape, es)) for eid, shape, en, es in elements)
    faces_by_sel = model_data.get("face_selection_faces", {})
    offset_cells = (offset_plan or {}).get("cells", {})
    offset_xyz = dict((offset_plan or {}).get("new_nodes", []))
    offset_ok = _joint_on_offset_supported()
    free_at = OrderedDict()     # (eid, nid) -> set of free axes
    on_offset = []
    for j in joints:
        faces = faces_by_sel.get(j["selection"])
        if not faces:
            _not_translated(model_data, {"selection": j["selection"]},
                            "Flexible joint",
                            tr("lege of onbekende vlakselectie",
                               "empty or unknown face selection"))
            continue
        for eid, fid in faces:
            shape, es = elem_info.get(eid, (None, None))
            fn = list(faces_of(eid, fid)) if eid in conn else []
            if shape not in _BEAM_SHAPES or len(fn) != 1:
                _not_translated(
                    model_data, {"selection": j["selection"]},
                    "Flexible joint",
                    tr("vlak {0} van element {1} is geen eindvlak van een "
                       "balkelement (Mecway: alleen eindvlakken van balken)",
                       "face {0} of element {1} is not an end face of a beam "
                       "element (Mecway: beam end faces only)").format(
                           fid, eid))
                continue
            mod = mods.get(es)
            if mod == "BARRE":
                log("INFO: Flexible joint on truss element {0}: a bar "
                    "is already pinned.".format(eid))
                continue
            # Beams only: _LINE3_SPLIT_MODS also holds the bars (BARRE,
            # CABLE), which have no rotations (DRX/DRY/DRZ) to release.
            if mod in _LINE3_BAR_MODS or mod not in _LINE3_SPLIT_MODS:
                _not_translated(
                    model_data, {"selection": j["selection"]},
                    "Flexible joint",
                    tr("element {0} is geen balk (MODELISATION {1})",
                       "element {0} is not a beam (MODELISATION {1})")
                    .format(eid, mod))
                continue
            if eid in offset_cells and (eid in split_line3 or
                                        not offset_ok):
                on_offset.append(eid)
                continue
            free_at.setdefault((eid, fn[0]), set()).update(j["free"])
    if on_offset:
        ids = sorted(set(on_offset))
        log(tr("WARNING: Balkelementen {0} hebben een element offset en een "
               "flexible joint; de joint wordt daar niet vertaald (het "
               "element zit star aan de arm). Een joint op een verschoven "
               "balk werkt alleen op line2-elementen in lineair statisch en "
               "modaal (KNOWN_BUGS 108).",
               "WARNING: Beam elements {0} have an element offset and a "
               "flexible joint; the joint is not translated there (the "
               "element is rigidly attached to the arm). A joint on an "
               "offset beam only works on line2 elements in linear static "
               "and modal analyses (KNOWN_BUGS 108).").format(
                   ", ".join(str(e) for e in ids[:10]) +
                   (" ..." if len(ids) > 10 else "")))
    if not free_at:
        return None, None
    _warn_joint_element_constraints(model_data, set(e for e, _n in free_at),
                                    elem_info)

    # Elements per node (all cells, also without joint)
    at_node = {}
    for eid, (atype, cn) in conn.items():
        for n in cn:
            at_node.setdefault(n, set()).add(eid)
    # Rotations that conditions fix per node
    bc_rot = {}
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _DIRICHLET_BCS or bc.get("skip"):
            continue
        rot = _bc_dofs(bc) & set(_ROT_DOFS)
        if not rot:
            continue
        for n in _selection_nodes(model_data, bc.get("selection"), conn,
                                  face_group_nodes):
            bc_rot.setdefault(n, set()).update(rot)

    by_node = OrderedDict()
    for (eid, nid), free in free_at.items():
        by_node.setdefault(nid, []).append((eid, free))
    # after the nodes of offset elements (bridge_offset.prepare)
    next_nid = max([max(nodes)] + list(model_data.get("offset_new_nids",
                                                      []))) + 1
    new_nodes = OrderedDict()
    poi_nodes = []
    own_poi = []        # offset nodes O without a cell (joint): POI1
    eqs = model_data.setdefault("constraint_equations", [])
    for nid, items in by_node.items():
        jointed = set(e for e, _f in items)
        others = at_node.get(nid, set()) - jointed
        rot_carrier = (nid in poi_rot and nid not in offset_poi) or any(
            mods.get(elem_info[e][1]) in _ROT_MODS for e in others)
        # offset elements carry the rotations via the arm, but their cell
        # is on its own nodes (bridge_offset)
        others = others - set(offset_cells)
        tied_axes = []
        for eid, free in items:
            dup = next_nid
            next_nid += 1
            new_nodes[dup] = nodes[nid]
            model_data.setdefault("joint_nodes", {})[dup] = nid
            # Cell with this end (for a split line3 one half) and
            # the local axes of that cell
            cn = conn[eid][1]
            if eid in split_line3:
                halves = ((cn[0], cn[2]), (cn[2], cn[1]))
                k = 0 if nid == cn[0] else 1
                a, b = halves[k]
                atype, idx = cell_refs[eid][k]
            else:
                a, b = cn[0], cn[1]
                atype, idx = cell_refs[eid][0]
            # Node the joint ties to: the Mecway node N, or for an offset
            # element its offset node O at the end of the rigid arm
            # (bridge_offset; the cell itself is set by
            # bridge_offset.apply_to_mesh from offset_plan)
            tie = nid
            if eid in offset_cells:
                # Offset element: Mecway node -> rigid arm (bridge_offset,
                # N -> O) -> joint -> element, as Mecway 34 (LS-52c: the
                # torsion of the released half is 0). The own node lies at
                # O and replaces O in the cell of this element; O itself
                # may then be in no cell: POI1 for its degrees of freedom.
                ocn = offset_cells[eid]
                o_node = ocn[cn.index(nid)]
                tie = o_node
                new_nodes[dup] = offset_xyz[o_node]
                offset_cells[eid] = [dup if n == o_node else n
                                     for n in ocn]
                if not any(o_node in c for e, c in offset_cells.items()
                           if e != eid) and o_node not in own_poi:
                    own_poi.append(o_node)
                # Results: the own node belongs via the arm to N
                # (node group BROFL, bridge_offset.apply_to_mesh)
                offset_plan.setdefault("joint_pairs", []).append(
                    (nid, dup, _vsub(offset_xyz[o_node], nodes[nid])))
            else:
                name, cell = by_type[atype][idx]
                by_type[atype][idx] = (name, [dup if n == nid else n
                                              for n in cell])
            u = _vunit(_vsub(nodes[b], nodes[a]))
            v = _mecway_v_axis(nodes[a], nodes[b],
                               model_data.get("beam_orientations",
                                              {}).get(eid))
            w = _vcross(u, v)
            for d in ("DX", "DY", "DZ"):
                eqs.append({"terms": [(dup, d, 1.0), (tie, d, -1.0)],
                            "constant": 0.0, "source": "flexiblejoint"})
            fixed = [ax for key, ax in (("u", u), ("v", v), ("w", w))
                     if key not in free]
            for ax in fixed:
                eqs.append({"terms": _rot_terms(dup, ax, 1.0) +
                            _rot_terms(tie, ax, -1.0),
                            "constant": 0.0, "source": "flexiblejoint"})
            tied_axes.extend(fixed)
            # Free axes per own node, for bridge_to_aster (POU_D_T_GD)
            model_data.setdefault("joint_free", {})[dup] = {
                "eid": eid, "node": nid, "free": sorted(free),
                "offset": tie != nid,
                "mod": mods.get(elem_info[eid][1])}
            log("INFO: Flexible joint element {0}, node N{1}: own node "
                "N{2}{6}, free about {3} (U={4}, V={5}).".format(
                    eid, nid, dup, "/".join(sorted(f.upper() for f in free)),
                    tuple(round(c, 6) for c in u),
                    tuple(round(c, 6) for c in v),
                    "" if tie == nid else
                    " at the end of the rigid arm (offset node N{0})".format(
                        tie)))
        if rot_carrier:
            if not others and nid not in poi_any:
                # only offset elements (and joints) at this node:
                # no cell any more, but the arm -> POI1 for the
                # degrees of freedom, rotations via the arm
                poi_nodes.append(nid)
            continue
        # No other element with rotations: node N<nid> gets a POI1
        # DIS_TR (otherwise it has no rotations, or even no
        # degrees of freedom if only beams with a joint are attached)
        if not tied_axes and (others or nid in poi_any) and \
                nid not in offset_poi:
            continue        # no rotations needed, but degrees of freedom
        poi_nodes.append(nid)
        if bc_rot.get(nid):
            continue
        for ax in _complement(tied_axes):
            eqs.append({"terms": _rot_terms(nid, ax, 1.0), "constant": 0.0,
                        "source": "flexiblejoint"})
    # An offset node O that is now only in the arm of the Mecway node and
    # the joint (offset element with a joint): degrees of freedom via a
    # POI1 DIS_TR (stiffness 0); its rotations follow from the relations.
    poi_nodes.extend(n for n in own_poi if n not in poi_nodes)
    log("INFO: Flexible joint: {0} beam end(s) with their own node "
        "(LIAISON_DDL), {1} node(s) with a POI1 DIS_TR.".format(
            len(new_nodes), len(poi_nodes)))
    return new_nodes, poi_nodes


def _joint_on_offset_supported():
    """True if a flexible joint on an offset beam is translated in the
    active analysis: linear static (MECA_STATIQUE) and modal (CALC_MODES
    with TYPE_RESU='DYNAMIQUE'), as in the fork by MishalTPC (commit
    773d59f: "linear static and ordinary real modal analyses only"). Other
    analyses keep the old behaviour (WARNING, element rigid to the arm);
    for nonlinear the arm itself is already a small-rotation relation
    (KNOWN_BUGS 108a)."""
    try:
        analysis = get_active_analysis()
    except (KeyError, TypeError):
        return False
    cmd = analysis.get("solver_command")
    return cmd == "MECA_STATIQUE" or (
        cmd == "CALC_MODES" and
        "{0}".format(analysis.get("type_resu", "DYNAMIQUE")).upper() ==
        "DYNAMIQUE")


def _referenced_names(model_data):
    """Names of selections used by a condition, load, contact or
    coupling (all text values of those dicts, one level deep)."""
    names = set()
    for key in ("bcs", "contacts", "bonded", "couplings"):
        for item in model_data.get(key, []) or []:
            if isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, (type(u""), type(""))):
                        names.add(v)
    return names


def _free_faces(model_data, conn):
    """
    Free faces of volume elements for the error estimator: [(type,
    nodes)] as boundary elements (Code-Aster order, _skin_element).

    Why: CALC_ERREUR ERME_ELEM computes a boundary term (sigma.n - g) only
    on faces carrying a load; a face without load is treated
    as imposed displacement, so without boundary term. Source: test case
    sslv153a (Code-Aster 17.4), comment: without the groups LIBRE/LIBRE2
    with pressure ~0 "ces bords sont consideres comme a deplacement impose par
    le calcul des indicateurs d'erreur"; sslv07a: "STRICTO SENSU, LE CALCUL
    DE ERME_ELEM EST FAUX CAR DES BORDS A CONTRAINTE NULLE N'ONT PAS ETE
    DEFINIS". The bridge therefore puts PRES_REP ~0 on the free faces (1e-14
    Pa, not 0: see bridge_to_aster._error_estimator_block).

    Free = boundary of the volume (face of exactly one volume element), not
    shared with a shell element, not in a face selection used by a
    condition, load, contact or coupling (_referenced_names: those
    faces have their own load or are Dirichlet), and not with all
    corner nodes in a node selection of an imposed displacement
    (_DIRICHLET_BCS). Faces from _FACE_CORNERS (corner nodes; the order
    does not matter for PRES_REP ~0, ORIE_PEAU orients them outwards).
    """
    shapes = model_data.get("elem_shapes", {})
    counts = OrderedDict()
    for eid in sorted(conn):
        if shapes.get(eid) not in _SOLID_SHAPES:
            continue
        atype, cn = conn[eid]
        for prefix, table in _FACE_CORNERS.items():
            if atype.startswith(prefix):
                for fid in sorted(table):
                    corners = [cn[i] for i in table[fid]]
                    key = frozenset(corners)
                    if key in counts:
                        counts[key][0] += 1
                    else:
                        counts[key] = [1, eid, corners]
                break
    taken = set()
    for eid, (atype, cn) in conn.items():
        if shapes.get(eid) in _SHELL_SHAPES:
            taken.add(frozenset(cn[:_N_CORNERS[atype]]))
    used = _referenced_names(model_data)
    for fname, faces in model_data.get("face_selection_faces", {}).items():
        if fname not in used:
            continue
        for eid, fid in faces:
            if eid in conn:
                taken.add(frozenset(_face_from_table(
                    conn[eid][0], conn[eid][1], fid) or []))
    fixed = set()
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _DIRICHLET_BCS or not bc.get("selection"):
            continue
        sel = bc["selection"]
        # Only node selections: a face selection with a condition is already
        # covered by "taken" (its own faces). With the nodes of a
        # face selection e.g. an outer wall between two constrained
        # end faces (one element thick) would wrongly become Dirichlet
        # (seen in verification LS-04).
        for i in model_data.get("node_groups", {}).get(sel, []):
            fixed.add(int(str(i).lstrip("N")))
    out = []
    for key, (n, eid, corners) in counts.items():
        if n != 1 or key in taken or key <= fixed:
            continue
        atype, cn = conn[eid]
        out.append(_skin_element(atype, cn, corners))
    return out


# ==========================================
# MAIN FUNCTION
# ==========================================
def write_mesh(mail_path, model_data, face_nodes=None):
    """
    Write the mesh of model_data to mail_path (ASTER format) and adjust
    model_data to it (group names, POI1 groups, beam orientation,
    areas for forces on faces).

    face_nodes : function (eid, faceid) -> [node numbers] or None. In Mecway
                 mw.face_nodes(FaceId(eid, faceid)); without it (offline tests)
                 the table _FACE_CORNERS.

    Returns
    -------
    bool  True on success; False on an error (message in bridge_log.txt).
    """
    log("--- Mesh schrijven (ASTER-formaat): {0} ---".format(mail_path))
    nodes = model_data.get("mesh_nodes", {})
    elements = model_data.get("mesh_elements", [])
    if not nodes or not elements:
        log(tr("ERROR: Geen knopen of elementen in de .liml gevonden.",
               "ERROR: No nodes or elements found in the .liml."))
        return False
    nids = sorted(nodes.keys())
    if nids != list(range(1, len(nids) + 1)):
        # The results are read back by node index; Mecway renumbers
        # 1..N after refining and deleting (seen in Mecway).
        log(tr("ERROR: Knoopnummers zijn niet 1..N aaneengesloten ({0} "
               "knopen, hoogste {1}).",
               "ERROR: Node numbers are not contiguous 1..N ({0} "
               "nodes, highest {1}).").format(len(nids), nids[-1]))
        return False

    # --------------------------------------------------
    # 1. Elements in Code-Aster order
    # --------------------------------------------------
    conn = {}          # eid -> (aster_type, [nid ...])
    by_type = OrderedDict()
    elset_members = OrderedDict()
    # Cells per element: {eid: [(aster_type, index in by_type[type])]};
    # a line3 beam has two (_LINE3_SPLIT_MODS)
    cell_refs = {}
    elset_mods = model_data.get("elset_modelisations", {})
    n_split = 0
    curved = []        # [(eid, bow)] curved line3 beams (KNOWN_BUGS 107)
    for eid, shape, enodes, elset in elements:
        spec = _ASTER_TYPES.get(shape)
        if spec is None:
            log(tr("ERROR: Elementvorm '{0}' (element {1}) wordt niet "
                   "ondersteund.",
                   "ERROR: Element shape '{0}' (element {1}) is not "
                   "supported.").format(shape, eid))
            return False
        atype, order = spec
        if len(enodes) != len(order):
            log(tr("ERROR: Element {0} ({1}) heeft {2} knopen, verwacht {3}.",
                   "ERROR: Element {0} ({1}) has {2} nodes, expected {3}.")
                .format(eid, shape, len(enodes), len(order)))
            return False
        cn = [enodes[i] for i in order]
        conn[eid] = (atype, cn)
        if shape == "line3" and elset_mods.get(elset) in _LINE3_SPLIT_MODS:
            # Quadratic beam -> two SEG2 cells M<eid> (first node -
            # mid node) and H<eid> (mid node - second node): the
            # beam elements of Code-Aster exist only on SEG2 (see
            # _LINE3_SPLIT_MODS). conn keeps the Mecway shape (SEG3) for the
            # geometry (faces, lengths); the results go back per node,
            # so also at the mid node.
            n_split += 1
            bow = _line3_bow(nodes, cn)
            if bow > _LINE3_CURVED:
                curved.append((eid, bow))
            for name, part in zip(_cell_names(eid, True),
                                  ([cn[0], cn[2]], [cn[2], cn[1]])):
                items = by_type.setdefault("SEG2", [])
                cell_refs.setdefault(eid, []).append(("SEG2", len(items)))
                items.append((name, part))
                elset_members.setdefault(elset, []).append(name)
            continue
        items = by_type.setdefault(atype, [])
        cell_refs[eid] = [(atype, len(items))]
        items.append(("M{0}".format(eid), cn))
        elset_members.setdefault(elset, []).append("M{0}".format(eid))
    if n_split:
        log("INFO: {0} line3 element(s) split into two SEG2 cells "
            "(M<eid> and H<eid>).".format(n_split))
    if curved:
        ids = [e for e, _b in curved]
        log(tr("WARNING: {0} gekromde line3-element(en) ({1}; "
               "middenknoop tot {2}% van de elementlengte naast de koorde). "
               "Code-Aster heeft geen gekromde balk of staaf: elk element "
               "wordt twee rechte stukken met een knik in de middenknoop. "
               "Mecway rekent de gekromde vorm; verfijn de kromming voor een "
               "betere benadering (KNOWN_BUGS 107).",
               "WARNING: {0} curved line3 element(s) ({1}; midside "
               "node up to {2}% of the element length off the chord). "
               "Code-Aster has no curved beam or bar: each element "
               "becomes two straight pieces with a kink at the midside "
               "node. Mecway computes the curved shape; refine the curve "
               "for a better approximation (KNOWN_BUGS 107).").format(
                   len(ids), ", ".join(str(e) for e in ids[:10]) +
                   (" ..." if len(ids) > 10 else ""),
                   # %-formatting: '{0:.2g}' gave a decimal comma in
                   # IronPython (bridge_to_aster._warn_large_rotations)
                   "%.2g" % (100.0 * max(b for _e, b in curved))))
    split_line3 = set(e for e, refs in cell_refs.items() if len(refs) == 2)

    # --------------------------------------------------
    # 2. Face selections -> boundary elements / shell elements / nodes
    # --------------------------------------------------
    shapes = model_data.get("elem_shapes", {})
    skin_by_key = {}
    skin_count = [0]
    face_groups = OrderedDict()       # name -> [element names]
    face_group_nodes = OrderedDict()  # name -> set(nid), beam faces only
    group_areas = {}
    group_weights = {}                # name -> {nid: int(N dA)}, volume faces
    group_integrals = {}              # name -> [w, m, S] per node, all faces
    group_faces = {}                  # name -> {"kinds": set, "normals": [..]}
    # name -> [{"kind", "stype", "nodes", "eid", "fid", "side"}] per face,
    # for loads that need a normal or weight per node
    # (elastic support, compression only, symmetry)
    group_face_list = OrderedDict()

    def note_list(fname, kind, stype, snodes, eid, fid, side=None):
        group_face_list.setdefault(fname, []).append({
            "kind": kind, "stype": stype, "nodes": list(snodes), "eid": eid,
            "fid": fid, "side": side})

    def note_face(fname, kind, corner_pts, side=None):
        info = group_faces.setdefault(
            fname, {"kinds": set(), "normals": [], "sides": set()})
        info["kinds"].add(kind)
        if side is not None:
            info["sides"].add(side)
        if len(corner_pts) >= 3:
            nrm = _vcross(_vsub(corner_pts[1], corner_pts[0]),
                          _vsub(corner_pts[-1], corner_pts[0]))
            if _vdot(nrm, nrm) > 0.0:
                info["normals"].append(_vunit(nrm))

    def add_integrals(fname, stype, snodes):
        fw, fm, fs = _face_integrals(stype, [nodes[n] for n in snodes])
        gi = group_integrals.setdefault(
            fname, [OrderedDict(), OrderedDict(), [[0.0] * 3 for _ in range(3)]])
        for n, w, m in zip(snodes, fw, fm):
            gi[0][n] = gi[0].get(n, 0.0) + w
            old = gi[1].get(n, (0.0, 0.0, 0.0))
            gi[1][n] = tuple(old[c] + m[c] for c in range(3))
        for a in range(3):
            for b in range(3):
                gi[2][a][b] += fs[a][b]
        return fw
    checked = set()

    def faces_of(eid, fid):
        atype, cn = conn[eid]
        table = _face_from_table(atype, cn, fid)
        if face_nodes is None:
            return table
        api = list(face_nodes(eid, fid))
        key = (atype, fid)
        if table is not None and key not in checked:
            checked.add(key)
            if set(table) != set(api) - set(cn[_N_CORNERS[atype]:]):
                log(tr("WARNING: Vlak {0} van {1}: Mecway geeft {2}, de "
                       "tabel {3}. De Mecway-waarde wordt gebruikt.",
                       "WARNING: Face {0} of {1}: Mecway gives {2}, the "
                       "table {3}. The Mecway value is used.").format(
                        fid, atype, api, table))
        return api

    # XFEM_ face selections are a crack (step 2e, bridge_xfem.mesh_cells),
    # not boundary elements
    import bridge_xfem
    xfem_sel = (set(bridge_xfem.selection_names(model_data))
                if bridge_xfem.active_here() else set())
    for fname, faces in model_data.get("face_selection_faces", {}).items():
        if fname in xfem_sel:
            continue
        members = []
        for eid, fid in faces:
            if eid not in conn:
                log(tr("ERROR: Vlakselectie '{0}': element {1} bestaat niet.",
                       "ERROR: Face selection '{0}': element {1} does not "
                       "exist.").format(fname, eid))
                continue
            shape = shapes.get(eid, "?")
            atype, cn = conn[eid]
            fn = faces_of(eid, fid)
            if not fn:
                log(tr("ERROR: Vlakselectie '{0}': vlak {1} van element {2} "
                       "({3}) onbekend.",
                       "ERROR: Face selection '{0}': face {1} of element {2} "
                       "({3}) unknown.").format(fname, fid, eid, shape))
                continue
            if shape in _BEAM_SHAPES:
                face_group_nodes.setdefault(fname, set()).update(fn)
                note_face(fname, "beam", [])
                note_list(fname, "beam", atype, fn, eid, fid)
                continue
            if shape in _SHELL_SHAPES and set(fn) >= set(cn[:_N_CORNERS[atype]]):
                members.append("M{0}".format(eid))   # shell face = element
                add_integrals(fname, atype, cn)
                corner_set = set(cn[:_N_CORNERS[atype]])
                # order of the face: faceid 5 and 6 have opposite
                # normals; side = +1 if the face normal equals the
                # element normal (Code-Aster), otherwise -1
                fpts = [nodes[n] for n in fn if n in corner_set]
                epts = [nodes[n] for n in cn[:_N_CORNERS[atype]]]
                fn_ = _vcross(_vsub(fpts[1], fpts[0]), _vsub(fpts[-1], fpts[0]))
                en_ = _vcross(_vsub(epts[1], epts[0]), _vsub(epts[-1], epts[0]))
                note_face(fname, "shellface", fpts,
                          1 if _vdot(fn_, en_) > 0.0 else -1)
                note_list(fname, "shellface", atype, cn, eid, fid,
                          1 if _vdot(fn_, en_) > 0.0 else -1)
                continue
            stype, snodes = _skin_element(atype, cn, fn)
            key = frozenset(snodes)
            if key not in skin_by_key:
                skin_count[0] += 1
                name = "K{0}".format(skin_count[0])
                skin_by_key[key] = name
                by_type.setdefault(stype, []).append((name, snodes))
            note_face(fname, "solid" if shape in _SOLID_SHAPES else "shelledge",
                      [nodes[n] for n in
                       snodes[:3 if stype.startswith("TRIA") else 4]])
            note_list(fname, "solid" if shape in _SOLID_SHAPES
                      else "shelledge", stype, snodes, eid, fid)
            if shape in _SOLID_SHAPES:
                fw = add_integrals(fname, stype, snodes)
                gw = group_weights.setdefault(fname, OrderedDict())
                for n, w in zip(snodes, fw):
                    gw[n] = gw.get(n, 0.0) + w
                group_areas[fname] = group_areas.get(fname, 0.0) + sum(fw)
            members.append(skin_by_key[key])
        if members:
            # A cell only once per group: face 5 and 6 of the same
            # shell element gave alarm MODELISA5_8 in LIRE_MAILLAGE (the
            # integrals and face lists above do count both sides)
            face_groups[fname] = list(OrderedDict.fromkeys(members))

    # --------------------------------------------------
    # 2b. Error estimator: boundary elements on the free faces (_free_faces)
    # --------------------------------------------------
    free_members = []
    if error_estimator_requested(
            model_data.get("aster_custom", {}).get("options")):
        for stype, snodes in _free_faces(model_data, conn):
            key = frozenset(snodes)
            if key not in skin_by_key:
                skin_count[0] += 1
                name = "K{0}".format(skin_count[0])
                skin_by_key[key] = name
                by_type.setdefault(stype, []).append((name, snodes))
            free_members.append(skin_by_key[key])
        if free_members:
            log("INFO: Error estimator: {0} free faces of volume elements "
                "as group '{1}' (stress-free boundary, PRES_REP ~0 in "
                "CALC_ERREUR).".format(len(free_members), ERR_FREE_GROUP))

    # --------------------------------------------------
    # 2c. Vibro-acoustics: fluid-structure coupling faces as
    #     boundary elements (bridge_vibroacoustic.interface_faces)
    # --------------------------------------------------
    vibro_members = OrderedDict()
    if model_data.get("vibro"):
        import bridge_vibroacoustic
        if bridge_vibroacoustic.wanted():
            found = bridge_vibroacoustic.interface_faces(model_data, conn)
            if found is None:
                return False
            for group, items in found.items():
                for stype, snodes in items:
                    key = frozenset(snodes)
                    if key not in skin_by_key:
                        skin_count[0] += 1
                        name = "K{0}".format(skin_count[0])
                        skin_by_key[key] = name
                        by_type.setdefault(stype, []).append((name, snodes))
                    vibro_members.setdefault(group, []).append(
                        skin_by_key[key])

    # --------------------------------------------------
    # 2d. Fracture mechanics: edges along the crack front as SEG cells
    #     (bridge_fracture.front_cells; groups BRSCHEUR<n>)
    # --------------------------------------------------
    import bridge_fracture
    crack_cells = bridge_fracture.front_cells(model_data, conn)
    if crack_cells is None:
        return False
    crack_members = OrderedDict()
    for group, items in crack_cells.items():
        for stype, snodes in items:
            skin_count[0] += 1
            name = "K{0}".format(skin_count[0])
            by_type.setdefault(stype, []).append((name, snodes))
            crack_members.setdefault(group, []).append(name)

    # --------------------------------------------------
    # 2e. XFEM: crack face and front from XFEM_ face selections as cells
    #     outside the model (bridge_xfem.mesh_cells; groups BRXF<n>S/F)
    # --------------------------------------------------
    xfem_cells = bridge_xfem.mesh_cells(
        model_data, conn, faces_of if face_nodes is not None else None)
    if xfem_cells is None:
        return False
    for group, items in xfem_cells.items():
        for stype, snodes in items:
            skin_count[0] += 1
            name = "K{0}".format(skin_count[0])
            by_type.setdefault(stype, []).append((name, snodes))
            crack_members.setdefault(group, []).append(name)

    # --------------------------------------------------
    # 2f. Element offset (bridge_offset): offset shells/beams on their own
    #     nodes (the faces and groups above stay on the
    #     Mecway nodes) or EXCENTREMENT
    # --------------------------------------------------
    import bridge_offset
    offset_plan = bridge_offset.prepare(
        model_data, nodes, conn, elements,
        _joint_ends(model_data, conn, elements, faces_of))

    # --------------------------------------------------
    # 3. Free nodes from nodeselections -> POI1
    # --------------------------------------------------
    used_nodes = set()
    for atype, cn in conn.values():
        used_nodes.update(cn)
    rot_masters = set()
    master_groups = set()
    for c in model_data.get("couplings", []):
        master_groups.add(c["master_group"])
        if c["type"] == "rbe3" and c.get("surface_rot", False):
            rot_masters.add(c["master_group"])
    poi1_nodes = OrderedDict([(POI1_GROUP_T, []), (POI1_GROUP_R, [])])
    for gname, ids in model_data.get("node_groups", {}).items():
        for nid_str in ids:
            nid = int(nid_str[1:]) if nid_str.startswith("N") else int(nid_str)
            if nid in used_nodes:
                continue
            if nid not in nodes:
                log(tr("ERROR: Knoop {0} uit nodeselection '{1}' bestaat "
                       "niet.",
                       "ERROR: Node {0} from nodeselection '{1}' does not "
                       "exist.").format(nid, gname))
                continue
            target = POI1_GROUP_R if gname in rot_masters else POI1_GROUP_T
            if nid in poi1_nodes[POI1_GROUP_R]:
                continue
            if target == POI1_GROUP_R and nid in poi1_nodes[POI1_GROUP_T]:
                poi1_nodes[POI1_GROUP_T].remove(nid)
            if nid not in poi1_nodes[target]:
                poi1_nodes[target].append(nid)
            if gname not in master_groups:
                log(tr("WARNING: Losse knoop {0} (nodeselection '{1}') is "
                       "geen master van een koppeling. Het DIS-element heeft "
                       "stijfheid 0; zonder koppeling of opgelegde "
                       "verplaatsing wordt de stijfheidsmatrix singulier.",
                       "WARNING: Free node {0} (nodeselection '{1}') is "
                       "not the master of a coupling. The DIS element has "
                       "stiffness 0; without a coupling or prescribed "
                       "displacement the stiffness matrix becomes singular.")
                    .format(nid, gname))
    poi1_groups = OrderedDict()
    poi1_members = OrderedDict()
    for gname, pnids in poi1_nodes.items():
        if not pnids:
            continue
        names = []
        for nid in pnids:
            name = "P{0}".format(nid)
            by_type.setdefault("POI1", []).append((name, [nid]))
            names.append(name)
        poi1_members[gname] = names
        poi1_groups[gname] = "DIS_TR" if gname == POI1_GROUP_R else "DIS_T"
        log("INFO: {0} free node(s) as POI1 in group '{1}' ({2}): "
            "{3}".format(len(pnids), gname, poi1_groups[gname],
                         ", ".join("N{0}".format(n) for n in pnids)))

    # --------------------------------------------------
    # 4. Beam orientation -> extra groups with their own VECT_Y
    # --------------------------------------------------
    # In the ASTER format an element may be in several groups, so the
    # elsets stay whole; every V direction gets an extra group BORnnnnn
    # with ORIENTATION VECT_Y (model_data["beam_vect_y"]), over all beam
    # elsets together (one group per direction, in element order). Every
    # beam cell (MODELISATION POU_*) gets Mecway's V axis explicitly, also
    # without orientation attributes or card (default rule of
    # _mecway_v_axis), so that the bridge does not rely on Code-Aster's
    # default (found in the fork by MishalTPC,
    # github.com/mishal0488/MecwayAsterBridge). Never for trusses (BARRE),
    # cables (CABLE) or springs/dampers/gaps (DIS_T), also line elements.
    # Offset and flexible-joint cells keep their name M<eid>/H<eid>; V
    # comes from the Mecway nodes (conn), as in Mecway.
    beam_groups = OrderedDict()
    beam_vect_y = OrderedDict()
    beam_axes = OrderedDict()        # eid -> (elset, node 1, node 2, V)
    orient = model_data.get("beam_orientations", {})
    by_dir = OrderedDict()           # rounded V -> [V, [cell names]]
    beam_elsets = set()
    for eid, shape, enodes, es in elements:
        if (shape not in _BEAM_SHAPES or eid not in conn or
                not elset_mods.get(es, "").startswith("POU_")):
            continue
        beam_elsets.add(es)
        cn = conn[eid][1]
        if eid in split_line3:
            # per half (straight SEG2): V perpendicular to that half
            parts = zip(_cell_names(eid, True),
                        ((cn[0], cn[2]), (cn[2], cn[1])))
        else:
            parts = [("M{0}".format(eid), (cn[0], cn[1]))]
        for name, (a, b) in parts:
            v = _mecway_v_axis(nodes[a], nodes[b], orient.get(eid))
            key = tuple(round(c, 9) for c in v)
            by_dir.setdefault(key, [v, []])[1].append(name)
        # beam sidecar (bridge_beams): end nodes and V of the whole element
        # (a split line3 as the straight line between its end nodes)
        beam_axes[eid] = (es, cn[0], cn[1],
                          _mecway_v_axis(nodes[cn[0]], nodes[cn[1]],
                                         orient.get(eid)))
    for v, members in by_dir.values():
        sub = "BOR{0:05d}".format(len(beam_groups) + 1)
        beam_groups[sub] = members
        beam_vect_y[sub] = v
    if by_dir:
        log("INFO: Beam orientation: VECT_Y for every beam cell, {0} "
            "direction(s) of V over {1} beam elset(s); {2} element(s) with "
            "their own orientation.".format(
                len(by_dir), len(beam_elsets),
                len([e for e in orient if e in conn])))

    # --------------------------------------------------
    # 4b. Discrete elements on nodes (elastic support, nodal masses)
    # --------------------------------------------------
    discretes = _build_discretes(model_data, nodes, conn, group_face_list)
    # Element offset: POI1 (DIS_TR) for Mecway nodes without own rotations
    offset_discretes = bridge_offset.discretes(offset_plan, model_data)
    discretes.update(offset_discretes)
    k_poi = 0
    for dname, d in discretes.items():
        names = []
        for nid in d["nodes"]:
            k_poi += 1
            names.append("S{0}".format(k_poi))
            by_type.setdefault("POI1", []).append((names[-1], [nid]))
        d["members"] = names

    # --------------------------------------------------
    # 4c. Flexible joints: own node per beam end + LIAISON_DDL
    # --------------------------------------------------
    poi_rot = set(poi1_nodes[POI1_GROUP_R])
    poi_any = set(poi1_nodes[POI1_GROUP_T]) | poi_rot
    for d in discretes.values():
        poi_any.update(d["nodes"])
        if d.get("mod") == "DIS_TR":
            poi_rot.update(d["nodes"])
    # Mecway nodes whose only rotational POI1 is the zero-stiffness DIS_TR
    # of an element offset: no rotation carrier for a flexible joint
    offset_poi = set()
    for d in offset_discretes.values():
        offset_poi.update(d["nodes"])
    for dname, d in discretes.items():
        if dname not in offset_discretes and d.get("mod") == "DIS_TR":
            offset_poi.difference_update(d["nodes"])
    offset_poi.difference_update(poi1_nodes[POI1_GROUP_R])
    joint_nodes, joint_poi = _flexible_joints(
        model_data, nodes, conn, elements, faces_of, by_type, cell_refs,
        split_line3, face_group_nodes, poi_rot, poi_any, offset_plan,
        frozenset(offset_poi))
    joint_nodes = joint_nodes or OrderedDict()
    if joint_poi:
        names = []
        for nid in joint_poi:
            names.append("J{0}".format(nid))
            by_type.setdefault("POI1", []).append((names[-1], [nid]))
        poi1_members[JOINT_GROUP] = names
        poi1_groups[JOINT_GROUP] = "DIS_TR"

    # --------------------------------------------------
    # 4d. Line3 truss: midside node across the chord (LIAISON_DDL)
    # --------------------------------------------------
    n_truss_eq = _line3_truss_links(model_data, nodes, conn, elements,
                                    split_line3, elset_mods,
                                    face_group_nodes)
    if n_truss_eq:
        log("INFO: Line3 truss: {0} LIAISON_DDL for the midside nodes "
            "(transverse displacement = mean of the end nodes).".format(
                n_truss_eq))

    # --------------------------------------------------
    # 4e. Pre-tension section: cut through the prism, copies of the cut
    #     nodes + reference node (bridge_pretension)
    # --------------------------------------------------
    import bridge_pretension
    pret_nodes, pret_refs, pret_groups = bridge_pretension.apply(
        model_data, nodes, conn, by_type, cell_refs, skin_by_key, faces_of,
        max([max(nodes)] + list(model_data.get("offset_new_nids", [])) +
            list(joint_nodes.keys())) + 1)
    if pret_refs:
        names = []
        for nid in pret_refs:
            names.append("PT{0}".format(nid))
            by_type.setdefault("POI1", []).append((names[-1], [nid]))
        poi1_members[bridge_pretension.PRET_GROUP] = names
        poi1_groups[bridge_pretension.PRET_GROUP] = "DIS_T"

    # --------------------------------------------------
    # 5. Names
    # --------------------------------------------------
    reserved = (["all_elems", "all_nodes", POI1_GROUP_T, POI1_GROUP_R,
                 ERR_FREE_GROUP, JOINT_GROUP, bridge_pretension.PRET_GROUP] +
                list(pret_groups.keys()) +
                list(beam_groups.keys()) + list(discretes.keys()) +
                list(vibro_members.keys()) + list(crack_members.keys()))
    renames = _aster_names(
        list(elset_members.keys()) +
        list(model_data.get("node_groups", {}).keys()) +
        list(model_data.get("face_selection_faces", {}).keys()) +
        list(model_data.get("element_selections", {}).keys()) +
        [c["master_group"] for c in model_data.get("couplings", [])] +
        [c["slave_group"] for c in model_data.get("couplings", [])],
        reserved)
    sel_renames = _selection_names(model_data, renames, reserved,
                                   elset_members)

    def rn(name):
        """Code-Aster name of a selection (node/face/element)."""
        return sel_renames.get(name, name)

    def rn_es(name):
        """Code-Aster name of an elset (component)."""
        return renames.get(name, name)

    group_ma = OrderedDict()
    for name, members in elset_members.items():
        group_ma[rn_es(name)] = members
    for name, members in face_groups.items():
        group_ma[rn(name)] = members
    for name, eids in model_data.get("element_selections", {}).items():
        members = [c for e in eids if e in conn
                   for c in _cell_names(e, e in split_line3)]
        if members:
            group_ma[rn(name)] = members
    for name, members in poi1_members.items():
        group_ma[name] = members
    for name, members in beam_groups.items():
        group_ma[name] = members
    for name, d in discretes.items():
        group_ma[name] = d.pop("members")
    if free_members:
        group_ma[ERR_FREE_GROUP] = free_members
    for name, members in vibro_members.items():
        group_ma[name] = members
    for name, members in crack_members.items():
        group_ma[name] = members

    group_no = OrderedDict()
    for name, ids in model_data.get("node_groups", {}).items():
        group_no[rn(name)] = ["N{0}".format(int(str(i).lstrip("N")))
                              for i in ids]
    for name, nset in face_group_nodes.items():
        if rn(name) not in group_ma:
            group_no[rn(name)] = ["N{0}".format(n) for n in sorted(nset)]
    group_no.update(pret_groups)
    bridge_offset.apply_to_mesh(offset_plan, model_data, by_type, group_ma,
                                group_no, rn_es)
    # Do not write empty groups (empty Mecway selection): a condition or
    # load on it is skipped and reported in _apply_to_model_data.
    for groups in (group_ma, group_no):
        for name in [n for n, m in groups.items() if not m]:
            del groups[name]

    # --------------------------------------------------
    # 6. Writing
    # --------------------------------------------------
    try:
        out = ["TITRE", " Mecway-model via MecwayAsterBridge", "FINSF",
               "COOR_3D"]
        for nid in nids:
            # 15 significant digits: the line stays under 80 characters.
            out.append(" N{0} {1}".format(nid, " ".join(
                _real(c) for c in nodes[nid])))
        # Nodes of offset elements (bridge_offset) and then those of
        # flexible joints after the Mecway nodes, numbered ascending (the
        # results are read back by node index: row i < N stays
        # Mecway node i+1)
        # and then the copies and reference nodes of pre-tension sections
        for nid, xyz in ((offset_plan or {}).get("new_nodes", []) +
                         list(joint_nodes.items()) +
                         list(pret_nodes.items())):
            out.append(" N{0} {1}".format(nid, " ".join(
                _real(c) for c in xyz)))
        out.append("FINSF")
        # Cell name per Code-Aster cell number (0-based, order in the
        # file); bridge_failure uses it to map failed cells to
        # Mecway elements (Code-Aster 17.4 has no getCellName).
        model_data["cell_names"] = [name for items in by_type.values()
                                    for name, _cn in items]
        for atype, items in by_type.items():
            out.append(atype)
            for name, cn in items:
                out.extend(_wrap([name] + ["N{0}".format(n) for n in cn]))
            out.append("FINSF")
        for kind, groups in (("GROUP_MA", group_ma), ("GROUP_NO", group_no)):
            for name, members in groups.items():
                out.append(kind)
                out.append(" {0}".format(name))
                out.extend(_wrap(members))
                out.append("FINSF")
        out.append("FIN")
        f = open(mail_path, "w")
        try:
            f.write("\n".join(out) + "\n")
        finally:
            f.close()
    except Exception as e:
        log(tr("ERROR: Schrijven van '{0}' mislukt: {1}",
               "ERROR: Writing '{0}' failed: {1}").format(mail_path, str(e)))
        return False

    nonempty = set(group_ma.keys())
    model_data["group_ma_unions"] = OrderedDict()
    model_data["beam_vect_y"] = beam_vect_y
    model_data["beam_axes"] = beam_axes
    model_data["beam_node_xyz"] = dict(
        (n, nodes[n]) for v in beam_axes.values() for n in v[1:3])
    model_data["node_groups_in_mesh"] = True
    # For #ASTER lines (<<Mecway name>> -> Code-Aster name) and for the
    # elsets of mesh_elements (bridge_to_aster, bridge_thermal): for a
    # selection with the same name as an elset the elset wins
    # (_selection_names reports that).
    model_data["group_renames"] = dict(renames)
    # Selections separately (a face selection with the name of an elset gets
    # its own name, _selection_names); used by bridge_acoustic.
    model_data["selection_renames"] = dict(sel_renames)
    model_data["mesh_group_names"] = set(group_ma) | set(group_no)
    model_data["face_node_groups"] = set(
        rn(n) for n in face_group_nodes if rn(n) not in group_ma)
    model_data["discretes"] = discretes
    model_data["_conn"] = conn
    # Split line3 beams (cells M<eid> and H<eid>, cell_names_of);
    # extra nodes of flexible joints: model_data["joint_nodes"]
    model_data["line3_split"] = split_line3
    # beam sidecar (bridge_beams): elset with its Code-Aster name, like
    # the keys of beam_sections (_ELSET_KEYS)
    model_data["beam_axes"] = OrderedDict(
        (eid, (rn_es(v[0]),) + tuple(v[1:]))
        for eid, v in model_data.get("beam_axes", {}).items())
    model_data["_elem_elset"] = dict((eid, rn_es(es))
                                     for eid, shape, en, es in elements)
    model_data["group_face_list"] = OrderedDict(
        (rn(k), v) for k, v in group_face_list.items())
    for name, nset in face_group_nodes.items():
        group_weights.setdefault(name, OrderedDict(
            (n, 1.0) for n in sorted(nset)))
    _apply_to_model_data(model_data, rn, rn_es, nonempty, poi1_groups,
                         dict((rn(k), v) for k, v in group_areas.items()),
                         dict((rn(k), v) for k, v in group_weights.items()),
                         dict((rn(k), v) for k, v in group_integrals.items()),
                         dict((rn(k), v) for k, v in group_faces.items()))
    # The free faces in the model (boundary elements, ORIE_PEAU), so that the
    # error estimator sees a load on them (bridge_to_aster._error_estimator_block).
    model_data["error_free_group"] = ERR_FREE_GROUP if free_members else None
    if free_members:
        model_data["skin_groups"].append(ERR_FREE_GROUP)
    log("SUCCESS: Mesh written: {0} nodes, {1} elements, {2} boundary elements, "
        "{3} GROUP_MA, {4} GROUP_NO.".format(
            len(nids), len(conn), skin_count[0], len(group_ma), len(group_no)))
    return True


def _per_area(params, area):
    """Force parameters (float or time history) divided by area."""
    out = {}
    for ax, v in params.items():
        if ax.startswith("_"):
            out[ax] = v
        elif isinstance(v, list):
            out[ax] = [(t, f / area) for t, f in v]
        else:
            out[ax] = v / area
    return out


# ==========================================
# FACES PER NODE: WEIGHTS AND NORMALS
# ==========================================
def _lumped_weights(stype, pts):
    """
    Nodal weights of a face (sum = area): int(N_i dA), or for a
    non-positive weight (corners of QUAD8/TRIA6) the HRZ distribution
    w_i = A * int(N_i^2 dA) / sum_j int(N_j^2 dA) (Hinton-Rock-Zienkiewicz,
    as for a lumped mass matrix). How Mecway distributes an elastic support
    over the nodes is NOT verified.
    """
    w = _face_integrals(stype, pts)[0]
    if min(w) > 0.0:
        return w
    rule = _TRI_GAUSS if stype.startswith("TRIA") else _QUAD_GAUSS
    h = 1.0e-3
    sq = [0.0] * len(pts)
    for xi, eta, gw in rule:
        n = _face_shape(stype, xi, eta)
        dx = [sum((a - b) / (2 * h) * pts[i][c] for i, (a, b) in enumerate(
            zip(_face_shape(stype, xi + h, eta),
                _face_shape(stype, xi - h, eta)))) for c in range(3)]
        de = [sum((a - b) / (2 * h) * pts[i][c] for i, (a, b) in enumerate(
            zip(_face_shape(stype, xi, eta + h),
                _face_shape(stype, xi, eta - h)))) for c in range(3)]
        cr = _vcross(dx, de)
        jac = math.sqrt(_vdot(cr, cr))
        for i in range(len(pts)):
            sq[i] += gw * jac * n[i] * n[i]
    area = sum(w)
    total = sum(sq)
    return [area * s / total for s in sq]


def _face_normal(face, nodes, conn):
    """
    Unit normal of a face from group_face_list, pointing outwards:
    volume face away from the parent element (via the centroid), shell face
    along the face normal (side * element normal; faceid 5 = element normal).
    """
    nc = 3 if face["stype"].startswith("TRIA") else 4
    p = [nodes[n] for n in face["nodes"][:nc]]
    if nc == 3:
        nrm = _vcross(_vsub(p[1], p[0]), _vsub(p[2], p[0]))
    else:
        nrm = _vcross(_vsub(p[2], p[0]), _vsub(p[3], p[1]))
    nrm = _vunit(nrm)
    if face["kind"] == "solid":
        cn = conn[face["eid"]][1]
        c = [sum(nodes[n][k] for n in cn) / len(cn) for k in range(3)]
        f = [sum(q[k] for q in p) / nc for k in range(3)]
        if _vdot(nrm, _vsub(f, c)) < 0.0:
            nrm = (-nrm[0], -nrm[1], -nrm[2])
    elif face["kind"] == "shellface" and face.get("side", 1) < 0:
        nrm = (-nrm[0], -nrm[1], -nrm[2])
    return nrm


def _node_weights_normals(faces, nodes, conn):
    """
    {nid: weight} and {nid: average normal} over the faces (2D faces
    of volumes and shells). Normal at a node: weighted average of the
    normals of the adjacent faces (like Mecway's frictionless,
    manual v33 par. 9.2).
    """
    weights = OrderedDict()
    sums = OrderedDict()
    for face in faces:
        nrm = _face_normal(face, nodes, conn)
        w = _lumped_weights(face["stype"], [nodes[n] for n in face["nodes"]])
        for n, wi in zip(face["nodes"], w):
            weights[n] = weights.get(n, 0.0) + wi
            old = sums.get(n, (0.0, 0.0, 0.0))
            sums[n] = tuple(old[k] + wi * nrm[k] for k in range(3))
    return weights, OrderedDict((n, _vunit(v)) for n, v in sums.items())


def _round_key(values, scale):
    """Key to group nodes with (nearly) equal values."""
    return tuple(int(round(v / scale * 1.0e9)) for v in values)


# ==========================================
# DISCRETE ELEMENTS ON NODES (before writing the mesh)
# ==========================================
def _build_discretes(model_data, nodes, conn, face_list):
    """
    POI1 discretes for elastic support and nodal masses. Returns
    OrderedDict {group: {"nodes": [nid], "mod": "DIS_T"/"DIS_TR",
    "cara": [(CARA, (values))]}}; nodes with equal values share a
    group (AFFE_CARA_ELEM DISCRET only knows GROUP_MA, catalogue v17.4).

    Elastic support (manual v33 par. 9.4): per node a spring to ground
    K = w_i * (kt I + (kn - kt) n n^T), w_i = nodal weight of the area
    (_lumped_weights), n = average normal. K_T_N: full symmetric
    3x3 in the global system, 6 values "triangulaire superieure par
    colonne" (catalogue affe_cara_elem.py): K11, K12, K22, K13, K23, K33.
    """
    out = OrderedDict()

    def add(prefix, items, mod, make_cara, label):
        groups = OrderedDict()
        scale = max([abs(v) for _, vals in items for v in vals] + [1.0e-30])
        for nid, vals in items:
            groups.setdefault(_round_key(vals, scale), [vals, []])[1].append(
                nid)
        for vals, nids in groups.values():
            name = "{0}{1}".format(prefix, len(out) + 1)
            out[name] = {"nodes": nids, "mod": mod, "cara": make_cara(vals),
                         "label": label}

    for bc in model_data.get("bcs", []):
        if bc["type"] != "elasticsupport":
            continue
        bc["skip"] = True      # translated as discrete elements
        sel = bc["selection"]
        faces = face_list.get(sel, [])
        kinds = set(f["kind"] for f in faces)
        if not faces:
            # Mecway 33 stores it on an element selection, but does not
            # use it: measured headless (internal solver and CCX), block with
            # elastic support on 4 elements = same deflection as without
            model_data.setdefault("skipped_loads", []).append(
                tr("elastic support op '{0}'",
                   "elastic support on '{0}'").format(sel))
            log(tr("WARNING: Elastic support op '{0}': geen vlakken "
                   "(elementselectie?). Mecway rekent een elastic support "
                   "op elementen ook niet mee; kies vlakken (manual v33 "
                   "par. 9.4). NIET meegenomen.",
                   "WARNING: Elastic support on '{0}': no faces (element "
                   "selection?). Mecway does not apply an elastic support "
                   "on elements either; select faces (manual v33 par. "
                   "9.4). NOT included.").format(sel))
            continue
        if not kinds <= set(["solid", "shellface"]):
            model_data.setdefault("skipped_loads", []).append(
                tr("elastic support op '{0}'",
                   "elastic support on '{0}'").format(sel))
            log(tr("ERROR: Elastic support op '{0}': alleen vlakken van "
                   "volume-elementen en schaalvlakken (manual v33 par. 9.4), "
                   "hier {1}. NIET meegenomen.",
                   "ERROR: Elastic support on '{0}': only faces of solid "
                   "elements and shell faces (manual v33 par. 9.4), "
                   "here {1}. NOT included.").format(sel, sorted(kinds)))
            continue
        kn, kt = bc["params"]["kn"], bc["params"]["kt"]
        weights, normals = _node_weights_normals(faces, nodes, conn)
        items = []
        for n, w in weights.items():
            v = normals[n]
            k = [[w * ((kt if a == b else 0.0) + (kn - kt) * v[a] * v[b])
                  for b in range(3)] for a in range(3)]
            items.append((n, (k[0][0], k[0][1], k[1][1], k[0][2], k[1][2],
                              k[2][2])))
        add("BRES", items, "DIS_T",
            lambda vals: [("K_T_N", vals), ("M_T_D_N", (0.0,))],
            "elastic support '{0}'".format(sel))
        log("INFO: Elastic support '{0}': {1} nodes, area {2} m2, "
            "kn={3} Pa/m, kt={4} Pa/m -> springs DIS_T K_T_N.".format(
                sel, len(weights), "%.6g" % sum(weights.values()), kn, kt))

    groups = model_data.get("node_groups", {})
    for pm in model_data.get("point_masses", []):
        ids = [int(str(i).lstrip("N")) for i in groups.get(pm["selection"],
                                                            [])]
        if not ids:
            continue
        share = pm["value"] / float(len(ids))
        if pm["kind"] == "mass":
            # Mecway (manual v33 par. 9.21): mass distributed equally over the
            # nodes. M_T_D_N: 1 value (catalogue affe_cara_elem.py).
            add("BRMA", [(n, (share,)) for n in ids], "DIS_T",
                lambda vals: [("K_T_D_N", (0.0, 0.0, 0.0)),
                              ("M_T_D_N", vals)],
                "massa '{0}'".format(pm["selection"]))
        else:
            # M_TR_D_N: (M, IX, IY, IZ, IXY, IYZ, IXZ, EX, EY, EZ), U4.42.01
            # par. DISCRET. Distributed equally over the nodes like the mass:
            # NOT verified (the manual only says so for mass).
            if len(ids) > 1:
                log(tr("WARNING: Rotatietraagheid op '{0}' ({1} knopen): "
                       "gelijk verdeeld (NIET geverifieerd tegen Mecway).",
                       "WARNING: Rotational inertia on '{0}' ({1} nodes): "
                       "distributed equally (NOT verified against Mecway).")
                    .format(pm["selection"], len(ids)))
            inertia = [0.0, 0.0, 0.0]
            inertia[pm["axis"] - 1] = share
            add("BRRI", [(n, tuple(inertia)) for n in ids], "DIS_TR",
                lambda vals: [("K_TR_D_N", (0.0,) * 6),
                              ("M_TR_D_N", (0.0,) + tuple(vals) +
                               (0.0,) * 6)],
                "rotatietraagheid '{0}'".format(pm["selection"]))
        log("INFO: {0} on '{1}': {2} per node over {3} nodes.".format(
            pm["kind"], pm["selection"], share, len(ids)))
    return out


# ==========================================
# TRACTION, LINE PRESSURE, HYDROSTATIC PRESSURE
# ==========================================
def _not_translated(model_data, bc, what, why):
    bc["skip"] = True
    model_data.setdefault("skipped_loads", []).append(
        tr("{0} op '{1}'", "{0} on '{1}'").format(what, bc["selection"]))
    log(tr("ERROR: {0} op '{1}': {2}. NIET meegenomen.",
           "ERROR: {0} on '{1}': {2}. NOT included.").format(
        what, bc["selection"], why))


def _element_kinds(model_data, sel):
    """Modelisations of the elements of an element selection, or None."""
    eids = model_data.get("element_selections", {}).get(sel)
    if eids is None:
        return None
    mods = model_data.get("elset_modelisations", {})
    elem_elset = model_data.get("_elem_elset", {})
    return set(mods.get(elem_elset.get(e), "?") for e in eids)


def _traction(model_data, bc, faces, skin_groups):
    """
    Mecway (manual v33 par. 9.15): force per area, global.
      - volume faces: FORCE_FACE (U4.44.01), boundary elements in the model;
      - shell faces: FORCE_COQUE FX/FY/FZ with PLAN='SUP' (faceid 5, side
        of the element normal) or 'INF' (faceid 6): Mecway applies the force
        on the face at half thickness, so with a moment; PLAN SUP/INF does
        that in Code-Aster (U4.44.01 FORCE_COQUE: "force applied to upper/
        lower skin");
      - shell elements (element selection): FORCE_COQUE PLAN='MOY'
        (mid-surface, as in Mecway);
      - shell edges and beam ends: nodal forces (_edge_loads).
    """
    sel = bc["selection"]
    kinds = faces.get("kinds", set()) if faces else set()
    elem_mods = _element_kinds(model_data, sel)
    handler = SUPPORTED_BCS["traction"]
    if kinds == set(["solid"]):
        bc["aster_keyword"] = "FORCE_FACE"
        if sel not in skin_groups:
            skin_groups.append(sel)
        return
    if kinds and kinds <= set(["shelledge", "beam"]):
        _edge_loads(model_data, bc, "Traction")
        return
    if kinds == set(["shellface"]) and len(faces.get("sides", ())) == 1:
        plan = "SUP" if list(faces["sides"])[0] > 0 else "INF"
    elif not kinds and elem_mods and elem_mods <= set(["DKT", "DST",
                                                         "COQUE_3D"]):
        plan = "MOY"
    else:
        _not_translated(model_data, bc, "Traction",
                        tr("alleen volumevlakken, schaalvlakken aan een kant, "
                           "schaalelementen, schaalranden of balkuiteinden "
                           "(hier {0})",
                           "only solid faces, shell faces on one side, "
                           "shell elements, shell edges or beam ends "
                           "(here {0})").format(
                            sorted(kinds) or sorted(elem_mods or ["?"])))
        return
    bc["aster_keyword"] = "FORCE_COQUE"
    d = OrderedDict(handler.to_aster_dict(bc["params"]))
    d["PLAN"] = "'{0}'".format(plan)     # text in the .comm
    bc["aster_dict"] = d
    log("INFO: Traction on shells '{0}': FORCE_COQUE PLAN='{1}'.".format(
        sel, plan))


def _shell_edge_parent(model_data, sel):
    """MODELISATION of the shells behind edge group sel (DKT/DST/COQUE_3D),
    or None if that is not unambiguously one shell type."""
    mods = model_data.get("elset_modelisations", {})
    elem_elset = model_data.get("_elem_elset", {})
    parents = set(mods.get(elem_elset.get(f["eid"]), "?") for f in
                  model_data.get("group_face_list", {}).get(sel, []))
    if len(parents) == 1 and parents <= set(["DKT", "DST", "COQUE_3D"]):
        return list(parents)[0]
    return None


def _edge_length(model_data, sel):
    """Total length of the shell edges in sel (SEG2; SEG3 via the
    mid node as two straight pieces)."""
    nodes = model_data["mesh_nodes"]
    total = 0.0
    for f in model_data.get("group_face_list", {}).get(sel, []):
        ns = f["nodes"]
        path = [ns[0], ns[2], ns[1]] if len(ns) == 3 else ns[:2]
        for a, b in zip(path[:-1], path[1:]):
            d = _vsub(nodes[b], nodes[a])
            total += math.sqrt(_vdot(d, d))
    return total


def _line_pressure(model_data, bc, faces):
    """
    Mecway (manual v33 par. 9.16): force per length on beam elements
    (FORCE_POUTRE, global FX/FY/FZ or local N/VY/VZ) or on shell edges
    (FORCE_ARETE, globaal; U4.44.01: "line forces to an edge of a volume
    element or shell"). FORCE_POUTRE also works on BARRE (trusses): run
    17.4, bar 2 m with FX=1000 N/m, EA=2.1e7 N -> u(2)=9.52381e-5 m exact.
    """
    sel = bc["selection"]
    kinds = faces.get("kinds", set()) if faces else set()
    local = bc["params"].get("_local")
    elem_mods = _element_kinds(model_data, sel)
    if not kinds and elem_mods and elem_mods <= set(
            ["POU_D_E", "POU_D_T", "POU_D_T_GD", "BARRE"]):
        bc["aster_keyword"] = "FORCE_POUTRE"
        return
    if kinds == set(["shelledge"]) and not local:
        # The edges must be in the model, with the modelisation of the shell
        # (<EXCEPTION> MODELISA6_96 without, Code-Aster 17.4).
        mods = model_data.get("elset_modelisations", {})
        elem_elset = model_data.get("_elem_elset", {})
        parents = set(mods.get(elem_elset.get(f["eid"]), "?") for f in
                      model_data.get("group_face_list", {}).get(sel, []))
        if len(parents) != 1 or not parents <= set(["DKT", "DST",
                                                      "COQUE_3D"]):
            _not_translated(model_data, bc, "Line pressure",
                            tr("schaalranden van een schaaltype (hier {0})",
                               "shell edges of one shell type (here {0})")
                            .format(sorted(parents)))
            return
        model_data.setdefault("edge_groups", OrderedDict())[sel] = \
            list(parents)[0]
        bc["aster_keyword"] = "FORCE_ARETE"
        return
    _not_translated(model_data, bc, "Line pressure",
                    tr("alleen balkelementen (elementselectie) of "
                       "schaalranden (globaal X/Y/Z); hier {0}{1}",
                       "only beam elements (element selection) or "
                       "shell edges (global X/Y/Z); here {0}{1}").format(
                        sorted(kinds) or sorted(elem_mods or ["?"]),
                        tr(", elementcoordinaten", ", element coordinates")
                        if local else ""))


# ==========================================
# PRESSURE AND TRACTION ON SHELL EDGES AND BEAM ENDS
# ==========================================
_SEG_GAUSS = [(-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
              (0.774596669241483, 5.0 / 9.0)]


def _seg_shape(nn, xi):
    """Shape functions and derivatives of SEG2/SEG3 (Code-Aster order:
    corners, then mid node)."""
    if nn == 2:
        return [0.5 * (1.0 - xi), 0.5 * (1.0 + xi)], [-0.5, 0.5]
    return ([0.5 * xi * (xi - 1.0), 0.5 * xi * (xi + 1.0), 1.0 - xi * xi],
            [xi - 0.5, xi + 0.5, -2.0 * xi])


def _shell_normal(nodes, cn, atype):
    """Unit normal of a shell element from the corner nodes."""
    p = [nodes[n] for n in cn[:_N_CORNERS[atype]]]
    if len(p) == 3:
        return _vunit(_vcross(_vsub(p[1], p[0]), _vsub(p[2], p[0])))
    return _vunit(_vcross(_vsub(p[2], p[0]), _vsub(p[3], p[1])))


def _edge_frames(model_data, faces_list):
    """
    Per shell edge (kind 'shelledge') the integral over the edge length:
    {nid: [int N_i t dl, int N_i t n dl, int N_i dl, int N_i e dl,
    shell normal]} with t the thickness, n the outward normal in
    the shell plane (perpendicular to the edge, away from the element) and e
    the tangent. Returns (dict, reason) with reason != None if a thickness
    is missing.
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    sections = model_data.get("shell_sections", {})
    elem_elset = model_data.get("_elem_elset", {})
    out = OrderedDict()
    for f in faces_list:
        sec = sections.get(elem_elset.get(f["eid"])) or {}
        t = sec.get("thickness")
        if not t:
            return out, tr("schaal zonder dikte (element {0})",
                           "shell without thickness (element {0})").format(
                f["eid"])
        atype, cn = conn[f["eid"]]
        ns = _shell_normal(nodes, cn, atype)
        c = [sum(nodes[n][k] for n in cn) / len(cn) for k in range(3)]
        en = f["nodes"]
        pts = [nodes[n] for n in en]
        for xi, gw in _SEG_GAUSS:
            shp, dshp = _seg_shape(len(en), xi)
            x = [sum(shp[i] * pts[i][k] for i in range(len(en)))
                 for k in range(3)]
            dx = [sum(dshp[i] * pts[i][k] for i in range(len(en)))
                  for k in range(3)]
            jac = math.sqrt(_vdot(dx, dx))
            e = _vunit(dx)
            n = _vunit(_vcross(e, ns))
            if _vdot(n, _vsub(x, c)) < 0.0:
                n = (-n[0], -n[1], -n[2])
            for i, nid in enumerate(en):
                a = out.setdefault(nid, [0.0, [0.0] * 3, 0.0, [0.0] * 3,
                                         ns])
                w = gw * jac * shp[i]
                a[0] += w * t
                a[2] += w
                # tangent with a fixed sense (the sense of an edge is free)
                s = 1.0 if _vdot(e, a[3]) >= 0.0 else -1.0
                for k in range(3):
                    a[1][k] += w * t * n[k]
                    a[3][k] += s * w * e[k]
    return out, None


def _edge_loads(model_data, bc, what):
    """
    Pressure or traction on shell edges and beam ends as nodal forces
    (FORCE_NODALE via bc["node_loads"], like a moment on faces;
    bridge_to_aster._build_charges scales them, also with a time function).

    Mecway (manual v33 par. 9.14/9.15): pressure = normal force proportional to
    the area of the face, positive towards the element; traction =
    force per area in X/Y/Z. The area of a shell edge is
    length x thickness (the edge face is symmetric about the mid-surface, so
    no moment), that of a beam end the cross-section A. Translated as:
    shell edge f_i = -p int(N_i t n dl) (n in the shell plane, away from the
    element) or T int(N_i t dl); beam end -p A u (u = the axis pointing
    outwards) or T A. That Mecway computes the edge face this way is NOT
    verified against a Mecway solution (no example with pressure on
    a shell edge or beam end). Code-Aster has no pressure on a
    shell edge (PRES_REP: "domaine de milieu continu 2D ou 3D, ou ...
    coques", catalogue affe_char_meca.py v17.4); FORCE_ARETE would need a group
    per direction. Statically equivalent to the consistent
    nodal forces of the edge; after LINE_QUAD the forces stay on the
    Mecway nodes.
    """
    sel = bc["selection"]
    if any(is_position(v) for v in bc["aster_dict"].values()):
        # The nodal forces are fixed vectors times the value
        # (_render_node_loads); a formula in x, y, z would have to be
        # weighted differently per node. KNOWN_BUGS 104.
        _not_translated(model_data, bc, what, tr(
            "formule in x, y, z op schaalranden of balkuiteinden "
            "(KNOWN_BUGS 104)",
            "formula in x, y, z on shell edges or beam ends "
            "(KNOWN_BUGS 104)"))
        return
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    faces_list = model_data.get("group_face_list", {}).get(sel, [])
    edges = [f for f in faces_list if f["kind"] == "shelledge"]
    ends = [f for f in faces_list if f["kind"] == "beam"]
    frames, why = _edge_frames(model_data, edges)
    elem_elset = model_data.get("_elem_elset", {})
    per_node = OrderedDict()     # nid -> [weight, vector]  (pressure: -vector)
    for nid, a in frames.items():
        per_node[nid] = [a[0], list(a[1])]
    for f in ends:
        if why:
            break
        if f["fid"] not in (2, 3) or len(set(f["nodes"])) != 1:
            why = tr("zijvlak van een balk (alleen balkuiteinden, faceid "
                     "2/3; gebruik voor een verdeelde last line pressure op "
                     "een elementselectie)",
                     "side face of a beam (only beam ends, faceid 2/3; for a "
                     "distributed load use line pressure on an element "
                     "selection)")
            break
        area = None
        for key in ("beam_sections", "cable_sections"):
            sec = model_data.get(key, {}).get(elem_elset.get(f["eid"]))
            if sec and sec.get("area"):
                area = sec["area"]
        if not area:
            why = tr("balk zonder doorsnede-oppervlak (element {0})",
                     "beam without cross-section area (element {0})").format(
                f["eid"])
            break
        nid = f["nodes"][0]
        cn = conn[f["eid"]][1]
        other = cn[1] if nid == cn[0] else cn[0]
        u = _vunit(_vsub(nodes[nid], nodes[other]))
        a = per_node.setdefault(nid, [0.0, [0.0] * 3])
        a[0] += area
        for k in range(3):
            a[1][k] += area * u[k]
    if why or not per_node:
        _not_translated(model_data, bc, what, why or tr(
            "geen schaalranden of balkuiteinden", "no shell edges or "
            "beam ends"))
        return
    if bc["type"] == "surfacepressure":
        node_loads = OrderedDict([("PRES", [
            (n, tuple(-c for c in a[1])) for n, a in per_node.items()])])
    else:
        node_loads = OrderedDict()
        for k, comp in enumerate(("FX", "FY", "FZ")):
            if comp in bc["aster_dict"]:
                node_loads[comp] = [
                    (n, tuple(a[0] if j == k else 0.0 for j in range(3)))
                    for n, a in per_node.items()]
    bc["aster_keyword"] = "FORCE_NODALE"
    bc["node_loads"] = node_loads
    log("INFO: {0} on '{1}': {2} shell edge(s), {3} beam end(s) -> "
        "nodal forces over {4} nodes (area {5} m2).".format(
            what, sel, len(edges), len(ends), len(per_node),
            "%.6g" % sum(a[0] for a in per_node.values())))


def _gravity_sum(grav, sel):
    """
    Vector sum (gx, gy, gz) of the gravity items. A time history (list
    (t, g); bridge_bcs.GravityBC now only reads a fixed value, KNOWN_BUGS
    32) counts with its last value: the pressure formula is constant (WARNING).
    """
    total = [0.0, 0.0, 0.0]
    history = False
    for b in grav:
        for k, c in enumerate(("x", "y", "z")):
            v = b["params"].get(c, 0.0)
            if isinstance(v, list):
                history = True
                v = v[-1][1] if v else 0.0
            total[k] += v
    if history:
        log(tr("WARNING: Hydrostatische druk op '{0}': gravity met een "
               "tijdshistorie; de laatste waarde wordt gebruikt.",
               "WARNING: Hydrostatic pressure on '{0}': gravity with a "
               "time history; the last value is used.").format(sel))
    if len(grav) > 1:
        log("INFO: Hydrostatic pressure on '{0}': {1} gravity items summed "
            "to ({2}) m/s2.".format(sel, len(grav),
                                     ", ".join("%.6g" % c for c in total)))
    return tuple(total)


def _hydrostatic(model_data, bc, faces, skin_groups):
    """
    Mecway (manual v33 par. 9.17): p = rho * g . (x - x0) below the free
    surface (point x0), 0 above it; g = the gravity load of the model.
    Code-Aster: consistent nodal forces (FORCE_NODALE via node_loads,
    _hydrostatic_forces), on volume faces or shell faces on one side
    (sign as for surfacepressure); headless against Mecway: resultant exact,
    hex20 block DX 0.12%. Fallback for other face types: PRES_REP /
    FORCE_COQUE with a FORMULE (bridge_to_aster._hydrostatic_formula).
    Several gravity items: the vector sum, as the
    gravity loads themselves are summed in Code-Aster (each its own load in
    EXCIT, or one PESANTEUR in bridge_to_aster._sum_gravity).
    """
    grav = [b for b in model_data["bcs"]
            if b["type"] == "gravity" and not b.get("skip")]
    if not grav:
        _not_translated(model_data, bc,
                        tr("Hydrostatische druk", "Hydrostatic pressure"),
                        tr("het model heeft geen gravity (manual par. 9.17: "
                           "verplicht)",
                           "the model has no gravity (manual par. 9.17: "
                           "required)"))
        return
    g = _gravity_sum(grav, bc["selection"])
    kinds = faces.get("kinds", set()) if faces else set()
    sign = 1.0
    if kinds == set(["solid"]):
        if bc["selection"] not in skin_groups:
            skin_groups.append(bc["selection"])
    elif kinds == set(["shellface"]) and len(faces.get("sides", ())) == 1:
        # A pressure as a function on shells must go via FORCE_COQUE PRES
        # (<EXCEPTION> ELEMENTS4_92 with PRES_REP, Code-Aster 17.4).
        sign = float(list(faces["sides"])[0])
        bc["aster_keyword"] = "FORCE_COQUE"
    else:
        _not_translated(model_data, bc,
                        tr("Hydrostatische druk", "Hydrostatic pressure"),
                        tr("alleen volumevlakken of schaalvlakken aan een "
                           "kant (hier {0})",
                           "only solid faces or shell faces on one side "
                           "(here {0})").format(sorted(kinds) or "?"))
        return
    hydro = {"rho": bc["params"]["rho"], "point": bc["params"]["point"],
             "g": g, "sign": sign}
    forces = _hydrostatic_forces(model_data, bc["selection"], hydro)
    if forces is None:
        # face type without shape functions here: PRES_REP/FORCE_COQUE with the
        # formula (bridge_to_aster._hydrostatic_formula, Gauss points)
        bc["hydro"] = hydro
        bc["aster_dict"] = {"PRES": "hydro"}
        return
    if bc["selection"] in skin_groups and kinds == set(["solid"]):
        skin_groups.remove(bc["selection"])
    bc["aster_keyword"] = "FORCE_NODALE"
    bc["node_loads"] = OrderedDict([("HYD", forces)])
    bc["aster_dict"] = {"HYD": 1.0}
    tot = [sum(f[1][k] for f in forces) for k in range(3)]
    log("INFO: Hydrostatic pressure on '{0}': nodal forces over {1} nodes, "
        "resultant ({2}) N.".format(bc["selection"], len(forces),
                                     ", ".join("%.6g" % c for c in tot)))


def _sub_rule(stype, k):
    """
    Integration rule over k x k sub-cells (quadrilateral) or k^2 sub-triangles,
    with the rule of _face_integrals per sub-cell. For a face that
    intersects the free surface: the kink in p = max(0, ...) then falls in a
    small cell (error ~1/k^2).
    """
    out = []
    if stype.startswith("TRIA"):
        for i in range(k):
            for j in range(k - i):
                tris = [((i, j), (i + 1, j), (i, j + 1))]
                if i + j < k - 1:
                    tris.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
                for a, b, c in tris:
                    for u, v, w in _TRI_GAUSS:
                        out.append(((a[0] + u * (b[0] - a[0]) +
                                     v * (c[0] - a[0])) / float(k),
                                    (a[1] + u * (b[1] - a[1]) +
                                     v * (c[1] - a[1])) / float(k),
                                    w / float(k * k)))
        return out
    h = 2.0 / k
    for i in range(k):
        for j in range(k):
            for u, v, w in _QUAD_GAUSS:
                out.append((-1.0 + h * (i + 0.5 * (u + 1.0)),
                            -1.0 + h * (j + 0.5 * (v + 1.0)),
                            w / float(k * k)))
    return out


def _hydrostatic_forces(model_data, sel, hydro):
    """
    Consistent nodal forces f_i = -int(N_i p n dA) of the hydrostatic
    pressure (n = outward normal of the face, pressure > 0 = into the face).
    Mecway integrates piecewise exactly (manual v33 par. 9.17: "< 1%");
    PRES_REP with a FORMULE uses Gauss points: block 1x1x1 m, 2 hex8 over
    the height, water line at 0.75 m: resultant 1.7% too large, Mecway
    (headless) 0.03%. Here: faces that intersect the free surface over
    8 x 8 sub-cells. Returns [(nid, (fx, fy, fz))] or None if a face
    has no known type.
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    rho, g, x0 = hydro["rho"], hydro["g"], hydro["point"]

    def pres(x):
        return max(0.0, rho * sum(g[c] * (x[c] - x0[c]) for c in range(3)))

    rules = {}
    acc = OrderedDict()
    hd = 1.0e-3
    for f in model_data.get("group_face_list", {}).get(sel, []):
        stype = f["stype"]
        if stype not in ("TRIA3", "TRIA6", "QUAD4", "QUAD8"):
            return None
        nids = f["nodes"][:{"TRIA3": 3, "TRIA6": 6, "QUAD4": 4,
                            "QUAD8": 8}[stype]]
        pts = [nodes[n] for n in nids]
        if f["kind"] == "shellface":
            orient = float(f.get("side") or 1)
        else:
            # outward normal: away from the centroid of the element
            cn = conn[f["eid"]][1]
            ce = [sum(nodes[n][c] for n in cn) / len(cn) for c in range(3)]
            cf = [sum(p[c] for p in pts) / len(pts) for c in range(3)]
            n0 = _vcross(_vsub(pts[1], pts[0]), _vsub(pts[-1], pts[0]))
            if stype.startswith("QUAD"):
                n0 = _vcross(_vsub(pts[2], pts[0]), _vsub(pts[3], pts[1]))
            orient = 1.0 if _vdot(n0, _vsub(cf, ce)) >= 0.0 else -1.0
        ps = [pres(p) for p in pts]
        if max(ps) <= 0.0:
            continue
        k = 1 if min(ps) > 0.0 else 8
        if (stype, k) not in rules:
            rules[(stype, k)] = (_sub_rule(stype, k) if k > 1 else
                                 (_TRI_GAUSS if stype.startswith("TRIA")
                                  else _QUAD_GAUSS))
        for xi, eta, w in rules[(stype, k)]:
            n = _face_shape(stype, xi, eta)
            x = [sum(n[i] * pts[i][c] for i in range(len(pts)))
                 for c in range(3)]
            p = pres(x)
            if p <= 0.0:
                continue
            np_ = _face_shape(stype, xi + hd, eta)
            nm = _face_shape(stype, xi - hd, eta)
            ep = _face_shape(stype, xi, eta + hd)
            em = _face_shape(stype, xi, eta - hd)
            dx = [sum((np_[i] - nm[i]) / (2 * hd) * pts[i][c]
                      for i in range(len(pts))) for c in range(3)]
            de = [sum((ep[i] - em[i]) / (2 * hd) * pts[i][c]
                      for i in range(len(pts))) for c in range(3)]
            cr = _vcross(dx, de)        # n dA per d(xi) d(eta)
            for i, nid in enumerate(nids):
                a = acc.setdefault(nid, [0.0, 0.0, 0.0])
                for c in range(3):
                    a[c] -= orient * w * n[i] * p * cr[c]
    return [(nid, tuple(v)) for nid, v in acc.items()]


# ==========================================
# COMPRESSION ONLY AND SYMMETRY: NODE GROUPS PER DIRECTION
# ==========================================
def _extra_node_group(model_data, prefix, nids):
    """New node group (DEFI_GROUP NOEUD in the .comm); returns name."""
    groups = model_data.setdefault("extra_node_groups", OrderedDict())
    name = "{0}{1}".format(prefix, len(groups) + 1)
    groups[name] = sorted(nids)
    return name


def _compression_only(model_data, bc, faces_list):
    """
    Mecway (manual v33 par. 9.5): like frictionless where the support is in
    compression, free in tension. Code-Aster: LIAISON_UNIL (U4.44.11 par. 3.8),
    sum COEF_MULT_i * u_i < COEF_IMPO, per node n . u <= 0 with n the
    outward normal (the support is on that side). Nodes with
    the same normal form a zone. Rotations of shell nodes are not
    held (Mecway's frictionless does; NOT translated).
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    kinds = set(f["kind"] for f in faces_list)
    if not faces_list or not kinds <= set(["solid", "shellface"]):
        _not_translated(model_data, bc, "Compression only",
                        tr("alleen vlakken van volume-elementen en "
                           "schaalvlakken (hier {0})",
                           "only faces of solid elements and shell faces "
                           "(here {0})").format(sorted(kinds) or "?"))
        return
    if "shellface" in kinds:
        log(tr("WARNING: Compression only op schaalvlakken '{0}': alleen "
               "de normaalverplaatsing, de rotaties blijven vrij.",
               "WARNING: Compression only on shell faces '{0}': only "
               "the normal displacement, the rotations remain free.").format(
                bc["selection"]))
    _, normals = _node_weights_normals(faces_list, nodes, conn)
    zones = OrderedDict()
    for n, v in normals.items():
        zones.setdefault(_round_key(v, 1.0e-3), [v, []])[1].append(n)
    bc["unil_zones"] = [(_extra_node_group(model_data, "BRCO", nids), v)
                        for v, nids in zones.values()]
    bc["aster_dict"] = {}
    log("INFO: Compression only '{0}': {1} nodes in {2} zone(s) "
        "LIAISON_UNIL.".format(bc["selection"], len(normals), len(zones)))


def _plane_normal(points):
    """Normal of the plane through the points (three far apart), or None."""
    if len(points) < 3:
        return None
    p0 = points[0]
    p1 = max(points, key=lambda p: _vdot(_vsub(p, p0), _vsub(p, p0)))
    d = _vsub(p1, p0)

    def off_line(p):
        c = _vcross(d, _vsub(p, p0))
        return _vdot(c, c)
    p2 = max(points, key=off_line)
    nrm = _vcross(d, _vsub(p2, p0))
    if _vdot(nrm, nrm) <= 1.0e-24 * _vdot(d, d) ** 2:
        return None
    return _vunit(nrm)


def _angl_naut3(x, y):
    """
    ANGL_NAUT (degrees) with local x along x and local y along (the projection
    of) y. Nautical angles of Code-Aster: alpha about Z, beta about y1, gamma
    about x2 (U4.42.01 ORIENTATION); after alpha and beta y1 = (-sin a, cos a,
    0), gamma rotates y1 to y.
    """
    a, b, _ = _angl_naut(x)
    ar = math.radians(a)
    y1 = (-math.sin(ar), math.cos(ar), 0.0)
    z1 = _vcross(x, y1)
    return (a, b, math.degrees(math.atan2(_vdot(y, z1), _vdot(y, y1))))


def _symmetry(model_data, bc, faces_list):
    """
    Mecway (manual v33 par. 9.40): displacement perpendicular to the
    symmetry plane zero; beam ends also the rotations about the in-plane
    axes, shell edges only the rotation about the edge. LIAISON_OBLIQUE with
    local x = normal: volume nodes DX=0, beam nodes DX=DRY=DRZ=0,
    shell edges (local y = edge) DX=DRY=0.
    """
    nodes = model_data["mesh_nodes"]
    sel = bc["selection"]
    kinds = set(f["kind"] for f in faces_list)
    if not faces_list or not kinds <= set(["solid", "shelledge", "beam"]):
        _not_translated(model_data, bc, "Symmetry",
                        tr("alleen vlakken van volume-elementen, schaalranden "
                           "en balkuiteinden (hier {0})",
                           "only faces of solid elements, shell edges "
                           "and beam ends (here {0})").format(
                            sorted(kinds) or "?"))
        return
    all_nodes = set(n for f in faces_list for n in f["nodes"])
    if bc["params"].get("nodeplane"):
        pts = [nodes[n] for n in sorted(all_nodes)]
        nrm = _plane_normal(pts)
        if nrm is not None:
            size = max(math.sqrt(_vdot(_vsub(p, pts[0]), _vsub(p, pts[0])))
                       for p in pts)
            off = max(abs(_vdot(_vsub(p, pts[0]), nrm)) for p in pts)
            if off > 1.0e-6 * size:
                _not_translated(model_data, bc, "Symmetry",
                                tr("'plane defined by nodes', maar de knopen "
                                   "liggen niet in een vlak (afwijking {0} m; "
                                   "manual par. 9.40: 'all nodes should be "
                                   "coplanar')",
                                   "'plane defined by nodes', but the nodes "
                                   "do not lie in one plane (deviation {0} m; "
                                   "manual par. 9.40: 'all nodes should be "
                                   "coplanar')").format("%.3g" % off))
                return
    else:
        nrm = bc["params"].get("dir")
    if nrm is None:
        _not_translated(model_data, bc, "Symmetry",
                        tr("geen symmetrievlak (normaal nul of knopen op een "
                           "lijn)",
                           "no symmetry plane (zero normal or nodes on a "
                           "line)"))
        return
    beam = set(n for f in faces_list if f["kind"] == "beam"
               for n in f["nodes"])
    edges = OrderedDict()
    for f in faces_list:
        if f["kind"] != "shelledge":
            continue
        p0, p1 = nodes[f["nodes"][0]], nodes[f["nodes"][1]]
        t = _vsub(p1, p0)
        t = _vunit(_vsub(t, tuple(_vdot(t, nrm) * c for c in nrm)))
        if t[0] < -1.0e-9 or (abs(t[0]) <= 1.0e-9 and (
                t[1] < -1.0e-9 or (abs(t[1]) <= 1.0e-9 and t[2] < 0.0))):
            t = (-t[0], -t[1], -t[2])     # direction of the edge is free
        edges.setdefault(_round_key(t, 1.0), [t, set()])[1].update(
            n for n in f["nodes"] if n not in beam)
    edge_nodes = set(n for _, ns in edges.values() for n in ns)
    solid = all_nodes - beam - edge_nodes
    angl = _angl_naut(nrm)
    entries = []
    if solid:
        entries.append((_extra_node_group(model_data, "BRSY", solid), angl,
                        ("DX",)))
    if beam:
        entries.append((_extra_node_group(model_data, "BRSY", beam), angl,
                        ("DX", "DRY", "DRZ")))
    for t, ns in edges.values():
        entries.append((_extra_node_group(model_data, "BRSY", ns),
                        _angl_naut3(nrm, t), ("DX", "DRY")))
    bc["oblique"] = entries
    bc["aster_dict"] = {}
    log("INFO: Symmetry '{0}': normal ({1}), {2} group(s) "
        "LIAISON_OBLIQUE.".format(sel, ", ".join("%.4g" % c for c in nrm),
                                  len(entries)))


# ==========================================
# BONDED CONTACT -> LIAISON_MAIL
# ==========================================
def _bonded(model_data, c, group_faces, rn):
    """
    Mecway bonded contact (manual v33 par. 9.9.1): the slave nodes follow
    the projected point on the master face. Code-Aster: AFFE_CHAR_MECA
    LIAISON_MAIL (U4.44.01): "slave node movements are linked to the
    movements of their projections on the master face". TYPE_RACCORD by
    the kind of nodes (U4.44.01 LIAISON_MAIL): MASSIF (volume-volume), COQUE
    (shell-shell), MASSIF_COQUE ("slave nodes ... massive type ... master
    nodes ... shell type"). Shell (slave) on volume (master): MASSIF with
    the shell nodes as slave; that only couples DX/DY/DZ, the rotations of
    the shell stay free. Run 17.4 (beam 1x0.1x0.1 m hex8 + DKT plate
    0.01 m on the top face, end load 100 N): DZ -1.11361e-5 m, equal to
    shared nodes (-1.11362e-5); plate with its own mesh 7x3 -1.11430e-5
    (without plate -1.32381e-5). COQUE_MASSIF (EPAIS, CHAM_NORMALE,
    catalogue affe_char_meca.py) is not needed there. Shell edges of one
    component on a volume: COQUE_MASSIF, a rigid connection
    (_shell_edge_joint); otherwise MASSIF, then the edge acts as a hinge
    (WARNING).
    Returns a dict for bridge_to_aster, or None.
    """
    master, slave = rn(c["master"]), rn(c["slave"])
    label = tr("verlijmd contact '{0}' / '{1}'",
               "bonded contact '{0}' / '{1}'").format(c["master"], c["slave"])
    mk = group_faces.get(master, {}).get("kinds", set(["?"]))
    sk = group_faces.get(slave, {}).get("kinds", set(["?"]))

    def skip(why):
        model_data.setdefault("skipped_loads", []).append(label)
        log(tr("ERROR: {0}: {1}. NIET meegenomen.",
               "ERROR: {0}: {1}. NOT included.").format(label, why))
    if master == slave:
        return skip(tr("master en slave zijn dezelfde selectie",
                       "master and slave are the same selection"))
    if mk == set(["solid"]):
        m_type = "MASSIF"
    elif mk == set(["shellface"]):
        m_type = "COQUE"
    else:
        return skip(tr("master moet volumevlakken of schaalvlakken bevatten "
                       "(hier {0})",
                       "master must contain solid faces or shell faces "
                       "(here {0})").format(sorted(mk)))
    if sk == set(["solid"]):
        s_type = "MASSIF"
    elif sk <= set(["shellface", "shelledge"]):
        s_type = "COQUE"
    else:
        return skip(tr("slave: alleen volumevlakken, schaalvlakken of "
                       "schaalranden (hier {0}; balkuiteinden niet)",
                       "slave: only solid faces, shell faces or "
                       "shell edges (here {0}; not beam ends)").format(
                        sorted(sk)))
    raccord = {("MASSIF", "MASSIF"): "MASSIF", ("COQUE", "COQUE"): "COQUE",
               ("COQUE", "MASSIF"): "MASSIF_COQUE",
               ("MASSIF", "COQUE"): "MASSIF"}[(m_type, s_type)]
    # Thermal (T30/T31): bridge_thermal.bonded_loads translates the contact
    # (LIAISON_MAIL on TEMP or ECHANGE_PAROI) and reports itself what fails;
    # the mechanical messages below then only apply to the
    # mechanical part of the thermal -> mechanical chain.
    thermal = model_data.get("thermal_data") is not None
    mech = not thermal or model_data.get("thermo_mech")
    edge = None
    if (m_type, s_type) == ("MASSIF", "COQUE") and "shelledge" in sk:
        edge = _shell_edge_joint(model_data, slave)
        if edge is not None:
            raccord = "COQUE_MASSIF"
        elif mech:
            log(tr("WARNING: {0}: schaalrand op een volume koppelt hier "
                   "alleen de verplaatsingen (randen van meerdere "
                   "componenten of ook schaalvlakken); de rand werkt als "
                   "scharnier (geen moment). Stijf: één component per "
                   "verlijmd contact.",
                   "WARNING: {0}: shell edge on a solid only ties the "
                   "displacements here (edges of several components or "
                   "also shell faces); the edge acts as a hinge (no "
                   "moment). Rigid: one component per bonded "
                   "contact.").format(label))
    if c["type"] == "bondedelastic" and mech:
        model_data.setdefault("skipped_loads", []).append(
            tr("{0}: verende laag (kn={1}, kt={2} Pa/m) niet vertaald, star "
               "verlijmd",
               "{0}: elastic layer (kn={1}, kt={2} Pa/m) not translated, "
               "rigidly bonded").format(label, c.get("kn"), c.get("kt")))
        log(tr("WARNING: {0} is 'elastic': Code-Aster LIAISON_MAIL is star; "
               "de stijfheid wordt niet vertaald.",
               "WARNING: {0} is 'elastic': Code-Aster LIAISON_MAIL is "
               "rigid; the stiffness is not translated.").format(label))
    if c.get("tolerance", 0.0) <= 0.0:
        log("INFO: {0}: automatic tolerance of Mecway; Code-Aster "
            "couples all slave nodes (no DISTANCE_MAX).".format(label))
    # Master: for volumes the parent elements of the faces (<EXCEPTION>
    # PROJECTION4_55 with boundary faces: "les mailles maîtres doivent avoir
    # la même dimension que l'espace de modélisation", Code-Aster 17.4);
    # for shells the shell elements themselves (= the face group). Slave: the
    # nodes of the faces (GROUP_NO_ESCL), then the boundary faces need not be
    # in the model (MODELISA6_96).
    faces = model_data.get("group_face_list", {})
    slave_set = set(n for f in faces.get(slave, []) for n in f["nodes"])
    relations, ddl, rot_ddl = None, None, None
    if raccord == "COQUE" and mech:
        # Shell on shell. LIAISON_MAIL cannot handle a quadratic master
        # (tri6/quad8 -> COQUE_3D: it asks for DX of the mid node of the
        # QUAD9/TRIA7, which only has rotations, CHARGES2_31) and omits the
        # drilling rotation only if the master is normal to a
        # global axis (_coque_ddl). Then the bridge writes the
        # relations itself (_bonded_relations, LIAISON_DDL).
        # A volume as slave (MASSIF_COQUE) on a quadratic shell is solved
        # correctly by LIAISON_MAIL: quad8 plate with a hex20 block below,
        # nodes on and in the middle of the plate elements, equal to the
        # relations of _bonded_relations to 7 digits (Code-Aster 17.4).
        conn = model_data.get("_conn", {})
        m_eids = sorted(set(f["eid"] for f in faces.get(master, [])))
        quadratic = any(conn[e][0] in ("QUAD8", "TRIA6") for e in m_eids
                        if e in conn)
        ddl = _coque_ddl(group_faces.get(master, {}))
        if quadratic:
            # LIAISON_MAIL can do the rotations (the mid node has
            # DRX/DRY/DRZ and then counts exactly); the bridge only writes
            # the translations. Perpendicular to a global axis without the
            # drilling rotation, otherwise all three (DDL knows no local
            # coordinate system) with NPREC = -1 (_bonded_relations). Measured
            # (Code-Aster 17.4, quad8 plate 10 x 4 with a rib mid-element,
            # LS-07i/k): in the XY plane 1.13419e-5 m, rotated 30 degrees
            # with all three rotations 1.13358e-5 m (-0.05 %); the
            # rotations with LIAISON_DDL without the mid node gave
            # 1.2330e-5 (+8.7 %, too flexible).
            if ddl is not None:
                rot_ddl = tuple(d for d in ddl if d.startswith("DR"))
            else:
                rot_ddl = ("DRX", "DRY", "DRZ")
                model_data["_bonded_nprec_off"] = True
        if quadratic or ddl is None:
            relations = _bonded_relations(
                model_data, m_eids, slave_set, rot_ddl is None,
                c.get("tolerance", 0.0), label)
            if relations is None:
                log(tr("WARNING: {0}: geen slave-knoop te koppelen (alle "
                       "slave-knopen zijn ook knoop van de master of liggen "
                       "verder dan de tolerantie).",
                       "WARNING: {0}: no slave node to tie (all slave nodes "
                       "are also master nodes or lie beyond the "
                       "tolerance).").format(label))
                relations = []
    off = model_data.get("offset_elements") or {}
    hit = sorted(set(f["eid"] for sel in (master, slave)
                     for f in faces.get(sel, []) if f["eid"] in off))
    if mech and hit:
        # Element offset (bridge_offset) on the shells of the contact:
        # LIAISON_MAIL projects onto the cells of the master; with the
        # rigid route they lie on the offset face (own nodes),
        # with EXCENTREMENT and with the own relations (_bonded_relations,
        # Mecway coordinates) on the nodes. Slave nodes are always the
        # Mecway nodes. What Mecway does: NOT checked (KNOWN_BUGS 108).
        shifted = relations is None and any(
            off.get(f["eid"]) == "rigid" for f in faces.get(master, []))
        if raccord == "COQUE" and any(off[e] == "rigid" for e in hit):
            # quad8 strip with offset (own nodes) bonded to a
            # second strip: MUMPS wrongly reported FACTOR_11 on DRX of
            # an offset node; with NPREC = -1 tip -9.4266e-4 m versus
            # -9.41484e-4 (Mecway, continuous strip LS-07b; Code-Aster
            # 17.4). As with an oblique master (bridge_to_aster
            # .bonded_nprec).
            model_data["_bonded_nprec_off"] = True
        where = (tr("het verschoven middenvlak van de master (LIAISON_MAIL "
                    "op de verschoven cellen)",
                    "the offset mid-surface of the master (LIAISON_MAIL on "
                    "the offset cells)") if shifted else
                 tr("de knopen van de master (referentievlak, niet het "
                    "verschoven middenvlak)",
                    "the master nodes (reference surface, not the offset "
                    "mid-surface)"))
        log(tr("WARNING: {0}: schaalelementen {1} hebben een element "
               "offset. De slave-knopen worden gekoppeld aan {2}; of Mecway "
               "dat ook zo doet, is niet nagelopen (KNOWN_BUGS 108).",
               "WARNING: {0}: shell elements {1} have an element offset. "
               "The slave nodes are tied to {2}; whether Mecway does the "
               "same has not been checked (KNOWN_BUGS 108).").format(
                   label, ", ".join(str(e) for e in hit[:10]) +
                   (" ..." if len(hit) > 10 else ""), where))
    if m_type == "MASSIF":
        groups = model_data.setdefault("extra_ma_groups", OrderedDict())
        name = "BRMAIT{0}".format(len(groups) + 1)
        groups[name] = sorted(set(f["eid"] for f in faces.get(master, [])))
        master = name
    out = {"master": master, "raccord": raccord,
           "slave": _extra_node_group(model_data, "BRESCL", slave_set),
           "distance": c.get("tolerance", 0.0), "type": c["type"],
           "kinds": (m_type, s_type), "selections": (c["master"],
                                                     c["slave"]),
           "conductance": c.get("conductance")}
    if thermal:
        log("INFO: {0}: thermal coupling in bridge_thermal "
            "(LIAISON_MAIL on TEMP or ECHANGE_PAROI).".format(label))
    if relations is not None:
        # mechanical: LIAISON_DDL instead of LIAISON_MAIL (_render_mpcs); with
        # rot_ddl also LIAISON_MAIL for the rotations only
        out["relations"] = relations
        if rot_ddl:
            out["ddl"] = rot_ddl
            log("INFO: {0}: rotations via LIAISON_MAIL TYPE_RACCORD='COQUE' "
                "DDL={1}.".format(label, rot_ddl))
        return out
    if mech:
        log("INFO: {0} -> LIAISON_MAIL TYPE_RACCORD='{1}'{2}.".format(
            label, raccord, " (mechanical part)" if thermal else ""))
    if raccord == "COQUE":
        out["ddl"] = ddl
    if edge is not None:
        # bridge_to_aster: CHAM_NORMALE = CREA_CHAMP NOEU_GEOM_R NORMALE on
        # the shell component (docs/ASTER_regels_voorbeelden.md example 2)
        out["shell_group"], out["epais"] = edge
    return out


def _coque_ddl(info):
    """
    DDL of LIAISON_MAIL TYPE_RACCORD='COQUE' (shell on shell). Without DDL
    Code-Aster couples all DDL of the shells ("par défaut tous les DDL
    des coques", catalogue affe_char_meca.py v17.4), also the rotation about
    the normal of the master (drilling). With DKT that only has a
    fictitious stiffness (AFFE_CARA_ELEM COQUE COEF_RIGI_DRZ, default
    1e-5) and MUMPS then finds zero pivots: <EXCEPTION> <FACTOR_11> on DRZ
    (Code-Aster 17.4, NPREC=8; plate strip with a glue seam in the plane and
    a rib with its edge on a plate, TestFiles/Verificatie/
    tests_lineair_statisch.py LS-07; with NPREC=-1 the same solution as without the
    drilling coupling, also with COEF_RIGI_DRZ=1e-3 still FACTOR_11; the
    strip of LS-07a rotated 30 degrees (LS-07f) with all DDL: same).
    Bending and shear go via the displacements and the two rotations
    in the master plane. If the master lies in a plane normal to a global
    axis, that rotation (DRX/DRY/DRZ) is left out here.
    Returns a tuple with DDL names, or None if DDL (global components)
    cannot express it (oblique or curved master): then
    _bonded writes the relations itself (_bonded_relations).
    """
    normals = info.get("normals") or []
    if normals:
        n0 = normals[0]
        if all(abs(_vdot(n, n0)) > 1.0 - 1.0e-6 for n in normals):
            for k, comp in enumerate(("DRX", "DRY", "DRZ")):
                if abs(n0[k]) > 1.0 - 1.0e-6:
                    return tuple(d for d in ("DX", "DY", "DZ", "DRX", "DRY",
                                             "DRZ") if d != comp)
    return None


def _face_point(atype, pts, xi, eta):
    """Point and tangent vectors (d/dxi, d/deta) of a shell element at
    (xi, eta); shape functions of _face_shape (central difference, exact
    for quadratic N)."""
    h = 1.0e-3
    n = _face_shape(atype, xi, eta)
    dxi = [(a - b) / (2 * h) for a, b in zip(_face_shape(atype, xi + h, eta),
                                             _face_shape(atype, xi - h, eta))]
    deta = [(a - b) / (2 * h) for a, b in zip(_face_shape(atype, xi, eta + h),
                                              _face_shape(atype, xi, eta - h))]
    x = tuple(sum(n[i] * pts[i][c] for i in range(len(pts)))
              for c in range(3))
    tx = tuple(sum(dxi[i] * pts[i][c] for i in range(len(pts)))
               for c in range(3))
    te = tuple(sum(deta[i] * pts[i][c] for i in range(len(pts)))
               for c in range(3))
    return n, x, tx, te


def _clamp_face(atype, xi, eta):
    """(xi, eta) back into the reference element (triangle: xi, eta >= 0,
    xi + eta <= 1; quadrilateral: [-1, 1]^2)."""
    if atype.startswith("TRIA"):
        xi, eta = max(xi, 0.0), max(eta, 0.0)
        if xi + eta > 1.0:
            s = min(max(0.5 * (xi - eta + 1.0), 0.0), 1.0)
            xi, eta = s, 1.0 - s
        return xi, eta
    return min(max(xi, -1.0), 1.0), min(max(eta, -1.0), 1.0)


def _project_on_face(atype, pts, p):
    """
    Closest point of p on a shell element (Gauss-Newton on
    |x(xi, eta) - p|^2, bounded to the element). Returns (distance, N,
    x, tx, te).
    """
    xi, eta = (1.0 / 3.0, 1.0 / 3.0) if atype.startswith("TRIA") else \
        (0.0, 0.0)
    for _ in range(30):
        n, x, tx, te = _face_point(atype, pts, xi, eta)
        r = _vsub(p, x)
        a11, a12, a22 = _vdot(tx, tx), _vdot(tx, te), _vdot(te, te)
        b1, b2 = _vdot(tx, r), _vdot(te, r)
        det = a11 * a22 - a12 * a12
        if det <= 0.0:
            break
        dxi = (a22 * b1 - a12 * b2) / det
        deta = (a11 * b2 - a12 * b1) / det
        nxi, neta = _clamp_face(atype, xi + dxi, eta + deta)
        moved = abs(nxi - xi) + abs(neta - eta)
        xi, eta = nxi, neta
        if moved < 1.0e-12:
            break
    n, x, tx, te = _face_point(atype, pts, xi, eta)
    d = _vsub(p, x)
    return math.sqrt(_vdot(d, d)), n, x, tx, te


def _bonded_relations(model_data, m_eids, slave_nids, rotations, distance,
                      label):
    """
    Bonded contact with a shell as master, written by the bridge itself
    as linear relations (LIAISON_DDL, U4.44.01), for the
    cases LIAISON_MAIL cannot handle:
    - quadratic master (tri6/quad8 -> COQUE_3D, TRIA7/QUAD9): LIAISON_MAIL
      interpolates with the 9 (7) nodes and then asks for DX of the
      mid node, which only has rotations with COQUE_3D
      (<EXCEPTION> <CHARGES2_31>, Code-Aster 17.4, LS-07i). The translations
      of COQUE_3D belong to the 8 (6) nodes of the Mecway cell (R3.07.05,
      NOT checked in the source; according to CHARGES2_31 the mid node has
      no DX). Here only the translations with the QUAD8/TRIA6
      shape functions (_face_shape, rotations False); the rotations stay with
      LIAISON_MAIL (_bonded: rot_ddl), where the mid node counts.
    - oblique or curved linear master: the rotation about the
      normal of the master (drilling) must not take part (_coque_ddl:
      FACTOR_11), and DDL of LIAISON_MAIL only knows global components.
      Here per slave node two relations for the rotation in the tangent plane
      of the master at the projection point (t1, t2):
      t_k . theta_slave = sum N_i t_k . theta_i.
      If t_k is oblique (more than one global component), the
      drilling rotation of the slave (only the fictitious stiffness
      COEF_RIGI_DRZ) is in the same DDL as a relation, and MUMPS reports a
      near-zero pivot (FACTOR_11) while the system is regular (LS-07f,
      Code-Aster 17.4: NPREC 8 and 10 FACTOR_11, NPREC 12 and -1 solve,
      with the same solution as LS-07a; COEF_RIGI_DRZ 1e-2 still
      FACTOR_11, 1e-1 solves). The margin scales with COEF_RIGI_DRZ and the
      thickness, so no fixed NPREC: model_data["_bonded_nprec_off"] sets
      NPREC = -1 (bridge_to_aster.generate_AsterSolver_files; RESI_RELA
      keeps checking the residual: the same strip without clamping
      stops with FACTOR_57).
    Like LIAISON_MAIL (U4.44.01): every slave node follows the
    projected point on the closest master element (also outside
    the element: then the edge); with a tolerance > 0 only nodes within
    that distance (DISTANCE_MAX). Slave nodes that are also nodes of the master
    stay out of the relations (otherwise an empty relation).
    rotations: False for a quadratic master (see above): only the
    translations.
    Returns [(nodes, ddl, coefficients)] or None (nothing to couple).
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    elems = []
    m_nodes = set()
    for eid in m_eids:
        atype, cn = conn[eid]
        pts = [nodes[n] for n in cn]
        lo = [min(q[c] for q in pts) for c in range(3)]
        hi = [max(q[c] for q in pts) for c in range(3)]
        elems.append((atype, cn, pts, lo, hi))
        m_nodes.update(cn)
    rel = []
    shared, far, dmax = 0, 0, 0.0
    mixed = False
    for s in sorted(slave_nids):
        if s in m_nodes:
            shared += 1
            continue
        p = nodes[s]
        boxes = []
        for k, (atype, cn, pts, lo, hi) in enumerate(elems):
            gap = [max(lo[c] - p[c], 0.0, p[c] - hi[c]) for c in range(3)]
            boxes.append((math.sqrt(_vdot(gap, gap)), k))
        boxes.sort()
        best = None
        for bd, k in boxes:
            if best is not None and bd > best[0] * (1.0 + 1.0e-9) + 1.0e-15:
                break
            atype, cn, pts = elems[k][:3]
            res = _project_on_face(atype, pts, p)
            if best is None or res[0] < best[0] - 1.0e-15:
                best = (res[0], k) + res[1:]
        if best is None:
            continue
        d, k, n, x, tx, te = best
        if distance > 0.0 and d > distance:
            far += 1
            continue
        dmax = max(dmax, d)
        cn = elems[k][1]
        terms = [(m, w) for m, w in zip(cn, n) if abs(w) > 1.0e-10]
        for comp in ("DX", "DY", "DZ"):
            rel.append(([s] + [m for m, w in terms], [comp] * (len(terms) + 1),
                        [1.0] + [-w for m, w in terms]))
        if rotations:
            nrm = _vunit(_vcross(tx, te))
            t1 = _vunit(tx)
            t2 = _vcross(nrm, t1)
            for t in (t1, t2):
                comps = [(c, t[i]) for i, c in enumerate(("DRX", "DRY", "DRZ"))
                         if abs(t[i]) > 1.0e-12]
                if len(comps) > 1:
                    mixed = True
                nids, ddl, coef = [], [], []
                for nid, w in [(s, 1.0)] + [(m, -w) for m, w in terms]:
                    for c, tc in comps:
                        nids.append(nid)
                        ddl.append(c)
                        coef.append(w * tc)
                rel.append((nids, ddl, coef))
    if shared:
        log("INFO: {0}: {1} slave nodes are also nodes of the master and "
            "are not coupled.".format(label, shared))
    if far:
        log("INFO: {0}: {1} slave nodes are farther than the tolerance "
            "from the master face and are not coupled.".format(label, far))
    if not rel:
        return None
    if mixed:
        # bridge_to_aster.generate_AsterSolver_files: NPREC = -1
        model_data["_bonded_nprec_off"] = True
    log("INFO: {0} -> LIAISON_DDL by the bridge ({1} relations, {2} "
        "slave nodes, largest distance to the master {3:.3g} m; {4}).".format(
            label, len(rel), len(rel) // (5 if rotations else 3), dmax,
            "translations and rotations in the master face" if rotations
            else "translations only"))
    return rel


def _shell_edge_joint(model_data, slave):
    """
    (shell component, thickness) for LIAISON_MAIL COQUE_MASSIF if the slave
    only contains shell edges of one component with a thickness, else None.
    COQUE_MASSIF (U4.44.01, catalogue affe_char_meca.py: EPAIS and
    CHAM_NORMALE required) connects the edge rigidly, also the rotations: the
    rotation of a shell node follows from the displacements of the volume
    over the thickness. Computed in docs/ASTER_regels_voorbeelden.md
    example 2 (model S, plate edge in a block: 0.00897 mm, clamped
    strip 0.00867 mm). Mecway/CCX converts shells into volume elements, then
    the edge is rigid too (NOT verified in Mecway).
    """
    faces = model_data.get("group_face_list", {}).get(slave, [])
    if not faces or any(f.get("kind") != "shelledge" for f in faces):
        return None
    elem_elset = model_data.get("_elem_elset", {})
    elsets = set(elem_elset.get(f["eid"]) for f in faces)
    if len(elsets) != 1:
        return None
    es = elsets.pop()
    sec = model_data.get("shell_sections", {}).get(es)
    if not sec or not sec.get("thickness"):
        return None
    return es, sec["thickness"]


# ==========================================
# PINNED SUPPORT: MEAN DISPLACEMENT ZERO
# ==========================================
def _pinned_to_mean(model_data, bc, group_weights):
    """
    Mecway: "A pinned support constrains mean displacement to zero in all
    three directions" (manual v33 par. 9.3); seen in Mecway: two nodes
    get opposite displacements and equal reactions. Code-Aster:
    per direction a LIAISON_DDL sum(w_i * u_i) = 0 (U4.44.01). Weights:
    equal per node for nodes, int(N_i dA)/A for faces of volume
    elements. One node: plain DDL_IMPO.
    """
    sel = bc["selection"]
    if sel in model_data.get("node_groups", {}):
        ids = [int(str(i).lstrip("N")) for i in model_data["node_groups"][sel]]
        weights = OrderedDict((n, 1.0) for n in ids)
    elif sel in group_weights:
        weights = group_weights[sel]
    else:
        bc["skip"] = True
        model_data.setdefault("skipped_loads", []).append(
            tr("pinned support op '{0}'",
               "pinned support on '{0}'").format(sel))
        log(tr("ERROR: Pinned support op '{0}': alleen knopen en vlakken van "
               "volume-elementen (Mecway manual par. 9.3). NIET meegenomen.",
               "ERROR: Pinned support on '{0}': only nodes and faces of "
               "solid elements (Mecway manual par. 9.3). NOT included.")
            .format(sel))
        return
    if len(weights) < 2:
        return
    total = sum(weights.values())
    bc["aster_keyword"] = "LIAISON_DDL"
    bc["pin_weights"] = [(n, w / total) for n, w in weights.items()]
    log("INFO: Pinned support '{0}': mean displacement zero over {1} "
        "nodes (LIAISON_DDL).".format(sel, len(weights)))


# ==========================================
# MOMENT: ON A NODE OR AS FORCES OVER FACES
# ==========================================
def _moment_to_forces(model_data, bc, group_integrals, group_weights=None):
    """
    Mecway (manual v33 par. 9.18): a moment acts on a single node with
    rotation DOFs, or as forces distributed over faces (shell or volume)
    about the axis through their centroid.

    Nodes: a nodeselection, or a faceselection of beam ends
    (faceid 2/3 = node 1/2, _FACE_CORNERS 'SEG'); that is in the mesh as
    GROUP_NO (like a force on beam ends) and counts via group_weights.
    One end = one node: FORCE_NODALE MX/MY/MZ on that node.

    Faces: linearly distributed surface traction t(x) = omega x (x - c),
    with omega = Theta^-1 M and Theta = int(|r|^2 I - r r^T) dA (r = x - c),
    so that int(r x t) dA = M and the resultant force is zero. Consistent
    nodal forces: f_i = omega x int(N_i (x - c) dA). Per moment component
    the nodal forces for a unit moment are stored in bc["node_loads"]
    (bridge_to_aster._build_charges scales them, also with a time function).
    """
    sel = bc["selection"]
    if bc["aster_target"] == "GROUP_NO":
        if sel in model_data.get("node_groups", {}):
            n = len(model_data["node_groups"][sel])
        else:
            # beam faces (face_node_groups): the nodes of the faces
            n = len((group_weights or {}).get(sel, ()))
        if n != 1:
            bc["skip"] = True
            model_data.setdefault("skipped_loads", []).append(
                tr("moment op '{0}' ({1} knopen)",
                   "moment on '{0}' ({1} nodes)").format(sel, n))
            log(tr("ERROR: Moment op '{0}': Mecway staat een moment op "
                   "knopen (of balkuiteinden) alleen toe op een enkele knoop "
                   "met rotatie-DOFs, hier {1} knopen. NIET meegenomen.",
                   "ERROR: Moment on '{0}': Mecway only allows a moment on "
                   "nodes (or beam ends) on a single node with rotational "
                   "DOFs, here {1} nodes. NOT included.").format(sel, n))
        return
    if sel not in group_integrals:
        bc["skip"] = True
        model_data.setdefault("skipped_loads", []).append(
            tr("moment op '{0}'", "moment on '{0}'").format(sel))
        log(tr("ERROR: Moment op '{0}': alleen op een knoop of op vlakken "
               "van schaal- of volume-elementen. NIET meegenomen.",
               "ERROR: Moment on '{0}': only on a node or on faces "
               "of shell or solid elements. NOT included.").format(sel))
        return
    w, m, S = group_integrals[sel]
    area = sum(w.values())
    c = [sum(mi[k] for mi in m.values()) / area for k in range(3)]
    rr = [[S[a][b] - area * c[a] * c[b] for b in range(3)] for a in range(3)]
    # trace of rr (do not call it 'tr': that is the translation function)
    trace = rr[0][0] + rr[1][1] + rr[2][2]
    theta_inv = _inv3([[(trace if a == b else 0.0) - rr[a][b]
                        for b in range(3)] for a in range(3)])
    node_loads = OrderedDict()
    for k, key in enumerate(("MX", "MY", "MZ")):
        if key not in bc["aster_dict"]:
            continue
        omega = [theta_inv[a][k] for a in range(3)]
        node_loads[key] = [
            (n, _vcross(omega, tuple(m[n][j] - w[n] * c[j] for j in range(3))))
            for n in w]
    bc["aster_keyword"] = "FORCE_NODALE"
    bc["node_loads"] = node_loads
    log("INFO: Moment on faces '{0}': forces over {1} nodes about the "
        "centroid ({2}).".format(
            sel, len(w), ", ".join("%.6g" % v for v in c)))


# ==========================================
# CONTACT: MERGE ZONES WITH SHARED SLAVE NODES
# ==========================================
# Conditions that fix all displacements of a node; if a
# contact slave node is also in them, the matrix is singular (pivot on
# LAGS_C, MECANONLINE9_4; seen in a bending model: profile clamped and
# slave).
# Partial conditions (displacement with some components,
# frictionless, symmetry) not: those only clash in the normal direction
# (a symmetry plane perpendicular to the contact is simply allowed).
_SLAVE_CONFLICT_BCS = ("fixed",)


def _exclude_fixed_slaves(model_data, group_integrals):
    """
    Remove slave nodes that also have a kinematic condition from the contact
    with SANS_GROUP_NO, as Code-Aster recommends (U4.44.11 par. 3.1.3:
    "recommended when the latter are subjected to boundary conditions in
    the expected direction of the contact (embedding for example)").
    Sets c["sans_groups"] (node groups) per zone and fills
    model_data["contact_sans_from_ma"] = {node group: face group} for
    DEFI_GROUP; logs the number of nodes per zone.
    """
    node_groups = model_data.get("node_groups", {})
    unions = model_data.get("group_ma_unions", {})
    from_ma = model_data.setdefault("contact_sans_from_ma", {})

    def to_int(n):
        return int(str(n).lstrip("N"))

    bc_nodes = []           # [(node group name, node set, source)]
    for bc in model_data.get("bcs", []):
        sel = bc.get("selection")
        if bc.get("type") not in _SLAVE_CONFLICT_BCS or not sel:
            continue
        if sel in node_groups:
            nodes = set(to_int(n) for n in node_groups[sel])
            bc_nodes.append((sel, nodes, sel))
        elif sel in group_integrals:
            nodes = set(to_int(n) for n in group_integrals[sel][0])
            bc_nodes.append((sel, nodes, sel))
    for c in model_data.get("contacts", []):
        slave_groups = unions.get(c["slave"], [c["slave"]])
        slave = set()
        for g in slave_groups:
            slave |= set(to_int(n) for n in group_integrals.get(g, [{}])[0])
        sans, count = [], set()
        for name, nodes, source in bc_nodes:
            common = slave & nodes
            if not common:
                continue
            if name not in node_groups:
                from_ma[name] = source
            if name not in sans:
                sans.append(name)
            count |= common
        if sans:
            c["sans_groups"] = sans
            log("INFO: Contact (slave '{0}'): {1} slave nodes also have a "
                "fixed condition ({2}) and are excluded with "
                "SANS_GROUP_NO (U4.44.11 par. 3.1.3).".format(
                    c["slave"], len(count), ", ".join(sans)))


# Conditions written as a relation (LIAISON_*) or partial DDL_IMPO;
# overlap between them (or with fixed) can give a double Lagrange
# condition (FACTOR_42/57). Fixed with fixed is simply a double DDL_IMPO.
_RELATION_BCS = ("pinnedsupport", "frictionless", "symmetry", "displacement",
                 "noderotation", "velocity")

# Besides fixed, bridge_to_aster._build_charges already excludes the fixed
# nodes (SANS_GROUP_* for LIAISON_OBLIQUE, FACE_IMPO and the DDL_IMPO of these
# kinds); that overlap need not be reported.
_SANS_FIXED_BCS = ("frictionless", "symmetry", "displacement",
                   "noderotation", "velocity")


_ALL_DOFS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")


def _global_dofs(ddls, angl):
    """Global degrees of freedom that ddls in the local system of ANGL_NAUT
    angl touch (None: ddls are already global). Local x = (cos a cos b,
    sin a cos b, -sin b) (U4.44.01 LIAISON_OBLIQUE, nautical angles); a
    local y/z component lies in the plane perpendicular to x: broadly all
    global axes that do not lie along x."""
    if angl is None:
        return set(ddls)
    a, b = math.radians(angl[0]), math.radians(angl[1])
    x = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), -math.sin(b))
    out = set()
    for d in ddls:
        prefix = "DR" if d.startswith("DR") else "D"
        if d.endswith("X"):
            axes = [i for i in range(3) if abs(x[i]) > 1.0e-9]
        else:
            axes = [i for i in range(3) if abs(x[i]) < 1.0 - 1.0e-9]
        out.update(prefix + "XYZ"[i] for i in axes)
    return out


def _local_axes(angl):
    """Local x, y, z (global) for ANGL_NAUT (alpha, beta, gamma) in degrees:
    R = Rz(alpha) Ry(beta) Rx(gamma), local x = (cos a cos b, sin a cos b,
    -sin b) (U4.44.01 LIAISON_OBLIQUE; U4.42.01 ORIENTATION). Gamma rotates
    y1 = (-sin a, cos a, 0) about x (as in _angl_naut3)."""
    a, b, g = [math.radians(v) for v in angl]
    x = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), -math.sin(b))
    y = (math.cos(a) * math.sin(b) * math.sin(g) - math.sin(a) * math.cos(g),
         math.sin(a) * math.sin(b) * math.sin(g) + math.cos(a) * math.cos(g),
         math.cos(b) * math.sin(g))
    return x, y, _vcross(x, y)


def _aligned_dofs(ddls, angl):
    """Global degrees of freedom that ddls in the local system of angl
    fix exactly, if every local axis used lies along a global axis;
    otherwise None (the relation mixes global degrees of freedom)."""
    if angl is None:
        return set(ddls)
    axes = dict(zip("XYZ", _local_axes(angl)))
    out = set()
    for d in ddls:
        v = axes[d[-1]]
        i = max(range(3), key=lambda k: abs(v[k]))
        if abs(v[i]) < 1.0 - 1.0e-9:
            return None
        out.add(("DR" if d.startswith("DR") else "D") + "XYZ"[i])
    return out


def _bc_dofs(bc, faces=None):
    """Global degrees of freedom that a kinematic condition fixes
    (broadly: more when in doubt). faces: group_faces entry of the selection
    (normals, for frictionless on a flat volume face)."""
    t = bc["type"]
    d = bc.get("aster_dict") or {}
    if t == "fixed":
        return set(_ALL_DOFS) if "BLOCAGE" in d else set(
            k for k in d if k in _ALL_DOFS)
    if t == "pinnedsupport":
        return set(("DX", "DY", "DZ"))
    if bc.get("oblique") is not None:   # symmetry, frictionless per node
        out = set()
        for _group, angl, ddls in bc["oblique"]:
            out |= _global_dofs(ddls, angl)
        return out
    if "DNOR" in d:                      # frictionless on volume faces
        normals = (faces or {}).get("normals") or []
        if normals and all(abs(_vdot(normals[0], n)) > 1.0 - 1.0e-6
                           for n in normals):
            return set("D" + "XYZ"[i] for i in range(3)
                       if abs(normals[0][i]) > 1.0e-9)
        return set(("DX", "DY", "DZ"))
    keys = [k for k in d if k in _ALL_DOFS]
    return _global_dofs(keys, d.get("ANGL_NAUT")) if keys else set(_ALL_DOFS)


def _ddl_kind(bc):
    """'const' or 'timed' for an ordinary DDL_IMPO (displacement, node
    rotation, velocity along a global axis; pinned support on a node),
    otherwise None. All constant DDL_IMPO are in one AFFE_CHAR_MECA, all
    time-dependent ones in one AFFE_CHAR_MECA_F (bridge_to_aster.
    _build_charges)."""
    if bc.get("aster_keyword") != "DDL_IMPO" or bc["type"] not in (
            "displacement", "noderotation", "velocity", "pinnedsupport"):
        return None
    if bc.get("pin_weights") or bc.get("oblique") is not None:
        return None
    values = [v for k, v in (bc.get("aster_dict") or {}).items()
              if k in _ALL_DOFS]
    if not values:
        return None
    # a formula in x, y, z (PositionFormula) is also a function
    # (AFFE_CHAR_MECA_F)
    return "timed" if any(isinstance(v, list) or is_position(v)
                          for v in values) else "const"


def _ddl_values(bcs):
    """{DOF: value} of the DDL_IMPO conditions bcs (the last one wins, as
    in Code-Aster)."""
    out = {}
    for bc in bcs:
        for k, v in (bc.get("aster_dict") or {}).items():
            if k in _ALL_DOFS:
                out[k] = v
    return out


def _exact_relation_dofs(model_data, bc, nodes_of, faces):
    """
    {node: set(global DOF)} that a relation (symmetry, frictionless)
    with value 0 fixes exactly, only where the local axes lie along the
    global axes; None if that is not unambiguous.
    """
    extra = model_data.get("extra_node_groups", {})
    d = bc.get("aster_dict") or {}
    out = {}
    if bc.get("oblique") is not None:
        for group, angl, ddls in bc["oblique"]:
            dofs = _aligned_dofs(ddls, angl)
            if dofs is None:
                return None
            for n in extra.get(group, ()):
                out.setdefault(n, set()).update(dofs)
        return out
    if bc["type"] != "frictionless":
        return None
    if "DNOR" in d:
        normals = (faces or {}).get("normals") or []
        if (isinstance(d["DNOR"], list) or d["DNOR"] != 0.0 or not normals
                or not all(abs(_vdot(normals[0], n)) > 1.0 - 1.0e-9
                           for n in normals)):
            return None
        dofs = _aligned_dofs(["DX"], _angl_naut(normals[0]))
    elif "ANGL_NAUT" in d:
        keys = [k for k in d if k in _ALL_DOFS]
        if any(isinstance(d[k], list) or d[k] != 0.0 for k in keys):
            return None
        dofs = _aligned_dofs(keys, d["ANGL_NAUT"])
    else:
        return None
    if dofs is None:
        return None
    return dict((n, set(dofs)) for n in nodes_of(bc["selection"]))


def _drop_covered_ddl(model_data, nodes_of, group_faces):
    """
    An imposed displacement/rotation 0 along a global axis (DDL_IMPO) on
    nodes that a symmetry or frictionless (value 0) already fixes in exactly
    that direction is the same condition. Mecway reduces that itself
    (manual v33 par. 9.6: "reduce them to a minimum equivalent set");
    Code-Aster stops with <EXCEPTION> FACTOR_42 (matrice singulière;
    seen with Code-Aster 17.4: displacement X=0 and symmetry/frictionless
    with normal X on the same face). The relation stays (it sometimes also
    fixes rotations); the DDL_IMPO gets a node group without those nodes
    (KNOWN_BUGS 8). Only for selections whose nodes are fixed
    (nodes, faces of volumes, shell edges, beam ends); not for
    shell faces and element selections (COQUE_3D: mid node in the job).
    """
    rels = []
    for bc in model_data.get("bcs", []):
        if bc.get("skip") or bc["type"] not in ("symmetry", "frictionless"):
            continue
        ex = _exact_relation_dofs(model_data, bc, nodes_of,
                                  group_faces.get(bc["selection"]))
        if ex:
            rels.append((bc, ex))
    if not rels:
        return
    face_list = model_data.get("group_face_list", {})
    node_groups = model_data.get("node_groups", {})
    for bc in model_data.get("bcs", []):
        if (bc.get("skip") or _ddl_kind(bc) != "const"
                or bc["type"] not in ("displacement", "noderotation")):
            continue
        values = _ddl_values([bc])
        if any(v != 0.0 for v in values.values()):
            continue
        sel = bc["selection"]
        kinds = set(f["kind"] for f in face_list.get(sel, []))
        if sel not in node_groups and not (
                kinds and kinds <= set(["solid", "shelledge", "beam"])):
            continue
        dofs = set(values)
        nodes = nodes_of(sel)
        covered = set()
        by = []
        for rbc, ex in rels:
            hit = set(n for n in nodes if dofs <= ex.get(n, set()))
            if hit:
                covered |= hit
                by.append("{0} '{1}'".format(rbc["type"], rbc["selection"]))
        if not covered:
            continue
        rest = nodes - covered
        log("INFO: {0} '{1}' ({2}=0): {3} node(s) already covered by {4} "
            "and are removed from the DDL_IMPO (double condition, "
            "FACTOR_42).".format(bc["type"], sel, "/".join(sorted(dofs)),
                                 len(covered), ", ".join(by)))
        if not rest:
            bc["skip"] = True
            continue
        bc["selection"] = _extra_node_group(model_data, "BROV", rest)
        bc["aster_target"] = "GROUP_NO"


def _unit_rows(ddls, angl=None):
    """[(kind, vector)] for degrees of freedom ddls ('DX', 'DRY', ...) in the
    local system of ANGL_NAUT angl (None: global); kind 'D' or 'DR'."""
    axes = _local_axes(angl) if angl is not None else (
        (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    return [("DR" if d.startswith("DR") else "D", axes["XYZ".index(d[-1])])
            for d in ddls]


def _rank3(vectors):
    """Rank of a set of 3D vectors (Gram-Schmidt, relative tolerance)."""
    basis = []
    for v in vectors:
        w = list(v)
        for b in basis:
            d = _vdot(w, b)
            w = [w[k] - d * b[k] for k in range(3)]
        n = math.sqrt(_vdot(w, w))
        if n > 1.0e-6:
            basis.append([c / n for c in w])
    return len(basis)


def _dependent_dofs(rows_a, rows_b):
    """Global degrees of freedom in which the conditions rows_a and rows_b at a
    node are linearly dependent (together a double condition: rank of
    the union smaller than the sum), or an empty set."""
    out = set()
    for kind in ("D", "DR"):
        a = [v for k, v in rows_a if k == kind]
        b = [v for k, v in rows_b if k == kind]
        if not a or not b or _rank3(a + b) == _rank3(a) + _rank3(b):
            continue
        for i in range(3):
            if (any(abs(v[i]) > 1.0e-9 for v in a)
                    and any(abs(v[i]) > 1.0e-9 for v in b)):
                out.add(kind + "XYZ"[i])
    return out


def _constraint_rows(model_data, bc):
    """
    Function node -> [(kind, vector)]: the directions that condition bc fixes
    at that node (global; per node for symmetry/frictionless with
    nodal normals, FACE_IMPO DNOR with the average face normal as
    Code-Aster takes it per node).
    """
    t = bc["type"]
    d = bc.get("aster_dict") or {}
    if t == "fixed":
        rows = _unit_rows(_ALL_DOFS if "BLOCAGE" in d else
                          [k for k in d if k in _ALL_DOFS])
        return lambda n: rows
    if t == "pinnedsupport":
        rows = _unit_rows(("DX", "DY", "DZ"))
        return lambda n: rows
    if bc.get("oblique") is not None:
        extra = model_data.get("extra_node_groups", {})
        per = {}
        for group, angl, ddls in bc["oblique"]:
            rows = _unit_rows(ddls, angl)
            for n in extra.get(group, ()):
                per.setdefault(n, []).extend(rows)
        return lambda n: per.get(n, [])
    if "DNOR" in d:
        faces = [f for f in model_data.get("group_face_list", {}).get(
            bc["selection"], []) if f["kind"] == "solid"]
        try:
            _w, normals = _node_weights_normals(
                faces, model_data["mesh_nodes"], model_data["_conn"])
        except ZeroDivisionError:
            rows = _unit_rows(("DX", "DY", "DZ"))
            return lambda n: rows
        return lambda n: [("D", normals[n])] if n in normals else []
    rows = _unit_rows([k for k in d if k in _ALL_DOFS], d.get("ANGL_NAUT"))
    return lambda n: rows


def _report_constraint_overlaps(model_data, group_integrals, group_faces=None):
    """
    Overlap of kinematic conditions (and RBE slaves) per pair that fixes a
    dependent direction in shared nodes (_dependent_dofs; a
    normal next to a tangent does not count). Mecway resolves overlap itself
    (manual v33 par. 9.6), Code-Aster not always:
      - fixed next to frictionless/symmetry/displacement/noderotation/
        velocity: already resolved (SANS_GROUP_* in bridge_to_aster);
      - DDL_IMPO 0 already covered by a symmetry/frictionless 0 in the same
        global direction: resolved (_drop_covered_ddl);
      - two DDL_IMPO in the same load (both constant or both
        time-dependent): Code-Aster takes the last one (seen with Code-
        Aster 17.4, also in AFFE_CHAR_MECA_F); a WARNING only for different
        values;
      - constant next to time-dependent on the same DOF: <EXCEPTION>
        ASSEMBLA_26 (seen with Code-Aster 17.4): WARNING;
      - two symmetries with the same relations per node: Code-Aster drops the
        double relation (seen with Code-Aster 17.4): no message;
      - otherwise: WARNING with the selections and the shared degrees of
        freedom (FACTOR_42/57 or a zero pivot, KNOWN_BUGS 8).
    """
    node_groups = model_data.get("node_groups", {})
    extra = model_data.get("extra_node_groups", {})
    face_list = model_data.get("group_face_list", {})
    elem_sel = model_data.get("element_selections", {})
    conn = model_data.get("_conn", {})
    group_faces = group_faces or {}

    def nodes_of(sel):
        if sel in node_groups:
            return set(int(str(n).lstrip("N")) for n in node_groups[sel])
        if sel in extra:
            return set(extra[sel])
        if sel in face_list:
            return set(n for f in face_list[sel] for n in f["nodes"])
        if sel in elem_sel:
            return set(n for e in elem_sel[sel] if e in conn
                       for n in conn[e][1])
        if sel in group_integrals:
            return set(int(str(n).lstrip("N")) for n in group_integrals[sel][0])
        return set()

    _drop_covered_ddl(model_data, nodes_of, group_faces)

    # Per (kind, selection) the fixed degrees of freedom (global); a
    # selection with several items of the same kind (e.g. displacement x and
    # y) becomes one item, so that each pair is reported once.
    items = OrderedDict()
    for bc in model_data.get("bcs", []):
        if (bc.get("type") in _RELATION_BCS + ("fixed",)
                and bc.get("selection") and not bc.get("skip")):
            it = items.setdefault((bc["type"], bc["selection"]),
                                  [set(), [], []])
            it[0].update(_bc_dofs(bc, group_faces.get(bc["selection"])))
            it[1].append(bc)
            it[2].append(_constraint_rows(model_data, bc))
    all_rows = _unit_rows(_ALL_DOFS)
    for c in model_data.get("couplings", []):
        it = items.setdefault(("koppeling", c.get("slave_group_ma") or
                               c.get("slave_group")), [set(), [], []])
        it[0].update(_ALL_DOFS)
        it[2].append(lambda n: all_rows)
    sets = [(t, s, nodes_of(s), dofs, bcs, rows)
            for (t, s), (dofs, bcs, rows) in items.items()]

    def kind(bcs):
        kinds = set(_ddl_kind(b) for b in bcs)
        return list(kinds)[0] if bcs and len(kinds) == 1 else None

    def oblique_spec(bcs, n):
        spec = set()
        for b in bcs:
            for group, angl, ddls in b.get("oblique") or ():
                if n in extra.get(group, ()):
                    spec.add((tuple(round(a, 9) for a in angl),
                              tuple(ddls)))
        return frozenset(spec)

    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            (ta, sa, na, da, ba, ra), (tb, sb, nb, db, bb, rb) = (
                sets[i], sets[j])
            if not da & db:
                continue        # other degrees of freedom: no conflict
            if ta == "fixed" and tb == "fixed":
                continue
            if "fixed" in (ta, tb) and set((ta, tb)) - set(
                    ("fixed",) + _SANS_FIXED_BCS) == set():
                continue
            # Only nodes where the directions are really dependent (a
            # normal next to a tangent is not a double condition).
            common = set()
            dofs = set()
            for n in na & nb:
                dep = _dependent_dofs([r for f in ra for r in f(n)],
                                      [r for f in rb for r in f(n)])
                if dep:
                    common.add(n)
                    dofs |= dep
            if not common:
                continue
            dof_txt = "/".join(d for d in _ALL_DOFS if d in dofs)
            ka, kb = kind(ba), kind(bb)
            if ka and kb:
                va, vb = _ddl_values(ba), _ddl_values(bb)
                shared = [d for d in _ALL_DOFS if d in va and d in vb]
                if ka != kb:
                    log(tr("WARNING: Voorwaarden {0} '{1}' en {2} '{3}' "
                           "leggen {4} op in {5} knoop/knopen (o.a. N{6}), de "
                           "ene constant en de andere tijdsafhankelijk: Code-"
                           "Aster stopt dan met ASSEMBLA_26 (dubbel "
                           "opgelegd). Pas de selecties in Mecway aan.",
                           "WARNING: Constraints {0} '{1}' and {2} '{3}' "
                           "prescribe {4} on {5} node(s) (e.g. N{6}), one "
                           "constant and the other time dependent: Code-Aster "
                           "then stops with ASSEMBLA_26 (prescribed twice). "
                           "Adjust the selections in Mecway.").format(
                            ta, sa, tb, sb, dof_txt, len(common), min(common)))
                elif any(va[d] != vb[d] for d in shared):
                    log(tr("WARNING: Voorwaarden {0} '{1}' en {2} '{3}' "
                           "leggen "
                           "{4} op in {5} knoop/knopen (o.a. N{6}) met "
                           "verschillende waarden; Code-Aster neemt de "
                           "laatste ('{3}'). Pas zo nodig de selecties in "
                           "Mecway aan.",
                           "WARNING: Constraints {0} '{1}' and {2} '{3}' "
                           "prescribe {4} on {5} node(s) (e.g. N{6}) with "
                           "different values; Code-Aster takes the last one "
                           "('{3}'). Adjust the selections in Mecway if "
                           "necessary.").format(
                            ta, sa, tb, sb, dof_txt, len(common), min(common)))
                continue
            if ta == tb == "symmetry" and all(
                    oblique_spec(ba, n) == oblique_spec(bb, n)
                    for n in common):
                continue    # same relations: Code-Aster drops one of them
            log(tr("WARNING: Voorwaarden {0} '{1}' en {2} '{3}' delen "
                   "{4} knoop/knopen (o.a. N{5}) op {6}. Code-Aster kan dan "
                   "stoppen met FACTOR_42/57 of een nulpivot (dubbele "
                   "voorwaarde); Mecway lost dat zelf op. Pas zo nodig "
                   "de selecties in Mecway aan.",
                   "WARNING: Constraints {0} '{1}' and {2} '{3}' share "
                   "{4} node(s) (e.g. N{5}) on {6}. Code-Aster may then "
                   "stop with FACTOR_42/57 or a zero pivot (duplicate "
                   "constraint); Mecway resolves this itself. Adjust "
                   "the selections in Mecway if necessary.").format(
                    ta, sa, tb, sb, len(common), min(common), dof_txt))


def _check_contact_sides(label, master, slave, group_integrals):
    """
    WARNING if the slave side is clearly coarser than the master. Code-Aster
    only checks the slave points against the master faces (U2.04.04
    par. 2.2: slave = the finest mesh, master = the stiffest/coarsest side);
    a fine master then penetrates between the coarse slave points without
    contact force. Seen in a bending model: roller (60 faces) slave
    on the profile (4482 faces), the roller went through the profile; with
    master/slave swapped contact did occur. The bridge does not swap
    by itself: in Mecway the choice is up to the user.
    """
    def size(group):
        # Characteristic element size: sqrt(area / number of nodes); the
        # area is the sum of the nodal weights (integral N dA).
        w = group_integrals.get(group, [{}])[0]
        area = sum(w.values())
        return (area / len(w)) ** 0.5 if w and area > 0 else None
    hm, hs = size(master), size(slave)
    if hm and hs and hs > 2.0 * hm:
        # %-formatting: "{0:.3g}".format() follows the locale in IronPython
        # (see bridge_mesh._real)
        log(tr("WARNING: {0}: de slave-vlakken zijn {1}x zo grof als "
               "de master (elementmaat {2} tegen {3} m). Code-Aster "
               "controleert alleen slave-punten tegen master-vlakken; de "
               "fijne master kan dan zonder contactkracht door de slave "
               "dringen. Maak in Mecway de fijnste kant de slave (U2.04.04 "
               "par. 2.2).",
               "WARNING: {0}: the slave faces are {1}x as coarse as "
               "the master (element size {2} vs {3} m). Code-Aster "
               "only checks slave points against master faces; the "
               "fine master can then penetrate the slave without contact "
               "force. In Mecway, make the finest side the slave (U2.04.04 "
               "par. 2.2).").format(label, "%.1f" % (hs / hm), "%.3g" % hs,
                                    "%.3g" % hm))


def _merge_contact_zones(pairs, group_integrals, unions):
    """
    Code-Aster forbids nodes that are in the slave faces of two zones
    (<EXCEPTION> <CONTACT2_16>, Code-Aster 17.4; SANS_GROUP_NO does not help,
    the check is about the faces). Mecway does not have that restriction: a
    profile can be slave against a blade and against a contour. Swapping master
    and slave (the hint of CONTACT2_16) makes the tool the slave,
    while the master should be the stiffest face (U2.04.04 par. 2.2);
    in a cutting model (dynamic, contact) that already diverged in the first
    step.

    Therefore pairs whose slave faces share nodes are merged
    into one zone: master = union of the masters, slave = union of the slaves
    (DEFI_GROUP CREA_GROUP_MA UNION via `unions`). When coupling,
    Code-Aster searches the closest master element per slave point.
    Friction of a merged zone: the largest coefficient.
    """
    def nodes_of(group):
        return set(group_integrals.get(group, [{}])[0].keys())

    zones = []          # [{"pairs": [...], "nodes": set()}]
    for pair in pairs:
        s_nodes = nodes_of(pair["slave"])
        hits = [z for z in zones if z["nodes"] & s_nodes]
        merged = {"pairs": [pair], "nodes": set(s_nodes)}
        for z in hits:
            merged["pairs"] = z["pairs"] + merged["pairs"]
            merged["nodes"] |= z["nodes"]
            zones.remove(z)
        zones.append(merged)

    def union(prefix, groups, k):
        uniq = []
        for g in groups:
            if g not in uniq:
                uniq.append(g)
        if len(uniq) == 1:
            return uniq[0]
        name = "{0}{1}".format(prefix, k)
        unions[name] = uniq
        return name

    result = []
    for k, z in enumerate(zones):
        ps = z["pairs"]
        if len(ps) == 1:
            result.append(ps[0])
            continue
        zone = dict(ps[0])
        zone["master"] = union("CMAIT", [p["master"] for p in ps], k + 1)
        zone["slave"] = union("CESCL", [p["slave"] for p in ps], k + 1)
        zone["friction"] = max(p.get("friction", 0.0) for p in ps)
        # penalty stiffnesses (contact_algo PENALISATION): the largest
        zone["kn"] = max(p.get("kn", 0.0) for p in ps)
        zone["kt"] = max(p.get("kt", 0.0) for p in ps)
        if len(set(p.get("friction", 0.0) for p in ps)) > 1:
            log(tr("WARNING: Samengevoegde contactzone met verschillende "
                   "wrijvingscoefficienten; de grootste ({0}) wordt gebruikt.",
                   "WARNING: Merged contact zone with different friction "
                   "coefficients; the largest ({0}) is used.")
                .format(zone["friction"]))
        log(tr("WARNING: Contactparen {0} delen slave-knopen en zijn "
               "samengevoegd tot een zone (master '{1}', slave '{2}'; "
               "Code-Aster CONTACT2_16).",
               "WARNING: Contact pairs {0} share slave nodes and have been "
               "merged into one zone (master '{1}', slave '{2}'; "
               "Code-Aster CONTACT2_16).")
            .format(", ".join("{0}/{1}".format(p["master"], p["slave"])
                              for p in ps), zone["master"], zone["slave"]))
        result.append(zone)
    return result


# ==========================================
# FRICTIONLESS SUPPORT
# ==========================================
def _frictionless(model_data, bc, faces, faces_list=None):
    """
    Volume faces: FACE_IMPO DNOR (bridge_bcs.FrictionlessBC); returns True,
    then the boundary elements must be in the model (skin_groups, ORIE_PEAU).
    Flat shell faces: LIAISON_OBLIQUE with the local x axis along the
    normal: DX = -value and DRY = DRZ = 0 (rotations about the in-plane
    axes, manual v33 par. 9.2). Curved shell faces and shell edges:
    LIAISON_OBLIQUE per nodal normal (_frictionless_per_node). Beams
    are reported and skipped.
    """
    sel = bc["selection"]
    kinds = faces["kinds"] if faces else set()
    if kinds == set(["solid"]):
        return True
    reason = tr("alleen vlakken van volume-elementen, schaalvlakken of "
                "schaalranden",
                "only faces of solid elements, shell faces or shell edges")
    if kinds == set(["shellface"]) and faces["normals"]:
        n0 = faces["normals"][0]
        if all(abs(_vdot(n0, n)) > 1.0 - 1.0e-6 for n in faces["normals"]):
            value = bc["params"].get("value", 0.0)
            if (isinstance(value, list) or value != 0.0):
                log(tr("WARNING: Frictionless op schaalvlakken '{0}' met een "
                       "normaalverplaatsing: de richting (welke kant 'in' "
                       "is) is NIET geverifieerd tegen Mecway.",
                       "WARNING: Frictionless on shell faces '{0}' with a "
                       "normal displacement: the direction (which side is "
                       "'in') is NOT verified against Mecway.").format(sel))
            dx, dy, dz = n0
            handler = SUPPORTED_BCS["frictionless"]
            bc["params"]["_normal"] = n0
            bc["aster_keyword"] = handler.keyword(bc["params"])
            bc["aster_dict"] = handler.to_aster_dict(bc["params"])
            log("INFO: Frictionless on flat shell faces '{0}': "
                "LIAISON_OBLIQUE, normal ({1})."
                .format(sel, ", ".join("%.4g" % v for v in (dx, dy, dz))))
            return False
    if kinds in (set(["shellface"]), set(["shelledge"])):
        reason = _frictionless_per_node(model_data, bc, faces_list or [],
                                        list(kinds)[0])
        if reason is None:
            return False
    bc["skip"] = True
    model_data.setdefault("skipped_loads", []).append(
        tr("frictionless op '{0}'", "frictionless on '{0}'").format(sel))
    log(tr("ERROR: Frictionless op '{0}' ({1}): {2}. NIET meegenomen.",
           "ERROR: Frictionless on '{0}' ({1}): {2}. NOT included.").format(
        sel, ", ".join(sorted(kinds)) or tr("geen vlakken", "no faces"),
        reason))
    return False


def _frictionless_per_node(model_data, bc, faces_list, kind):
    """
    Frictionless on curved shell faces or on shell edges (KNOWN_BUGS 5).
    Mecway (manual v33 par. 9.2): normal displacement zero, at a node
    along the average normal of the adjacent faces from the
    selection; on shells also the rotations about the in-plane axes.
    Code-Aster: LIAISON_OBLIQUE per group of nodes with the same normal
    (bc["oblique"], like symmetry; U4.44.01 LIAISON_OBLIQUE, ANGL_NAUT
    with local x = the normal):
      - shell faces: DX = DRY = DRZ = 0 (like the flat shell faces);
      - shell edges: normal in the shell plane (normal to the edge), local
        y = the edge: DX = DRY = 0. Only the rotation about the edge, as Mecway
        does for symmetry on shell edges (manual par. 9.40); whether Mecway's
        frictionless on a shell edge also fixes the rotation about the shell
        normal is NOT verified.
    Only normal displacement 0 (bc["oblique"] writes 0.0). After LINE_QUAD
    (COQUE_3D) the new mid nodes get no condition (one group per
    normal; bridge_to_aster only completes groups containing both end
    nodes). Returns None if translated, otherwise the reason.
    """
    value = bc["params"].get("value", 0.0)
    if isinstance(value, list) and all(v == 0.0 for _t, v in value):
        value = 0.0
    if isinstance(value, list) or value != 0.0:
        return tr("normaalverplaatsing ongelijk aan 0 op gekromde "
                  "schaalvlakken of schaalranden wordt niet vertaald",
                  "a non-zero normal displacement on curved shell faces "
                  "or shell edges is not translated")
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    groups = OrderedDict()           # key -> [angl, ddls, [nid]]
    if kind == "shellface":
        sums = OrderedDict()
        for f in faces_list:
            nrm = _face_normal(f, nodes, conn)
            w = _lumped_weights(f["stype"], [nodes[n] for n in f["nodes"]])
            for n, wi in zip(f["nodes"], w):
                old = sums.get(n, (0.0, 0.0, 0.0))
                sums[n] = tuple(old[k] + wi * nrm[k] for k in range(3))
        for n, v in sums.items():
            if _vdot(v, v) <= 1.0e-24:
                return tr("knoop N{0} heeft geen eenduidige normaal (vlakken "
                          "aan beide kanten?)",
                          "node N{0} has no unique normal (faces on both "
                          "sides?)").format(n)
            x = _vunit(v)
            groups.setdefault(_round_key(x, 1.0e-3),
                              [_angl_naut(x), ("DX", "DRY", "DRZ"), []]
                              )[2].append(n)
    else:
        frames, why = _edge_frames(model_data, faces_list)
        if why:
            return why
        for n, a in frames.items():
            v, ns = a[1], a[4]
            if _vdot(v, v) <= 1.0e-24:
                return tr("knoop N{0} heeft geen eenduidige normaal",
                          "node N{0} has no unique normal").format(n)
            x = _vunit(v)
            y = _vcross(ns, x)
            if _vdot(y, y) <= 1.0e-24:
                return tr("knoop N{0}: normaal langs de schaalnormaal",
                          "node N{0}: normal along the shell normal").format(n)
            y = _vunit(y)
            groups.setdefault(_round_key(x + y, 1.0e-3),
                              [_angl_naut3(x, y), ("DX", "DRY"), []]
                              )[2].append(n)
    bc["oblique"] = [(_extra_node_group(model_data, "BRFR", nids), angl,
                      ddls) for angl, ddls, nids in groups.values()]
    bc["aster_dict"] = {}
    log("INFO: Frictionless on {0} '{1}': {2} nodes, {3} normal(s), "
        "LIAISON_OBLIQUE per group.".format(
            "curved shell faces" if kind == "shellface" else
            "shell edges", bc["selection"],
            sum(len(g[2]) for g in groups.values()), len(groups)))
    return None


# ==========================================
# COUPLINGS (RBE2/RBE3): NAMES AND SLAVE NODE GROUPS
# ==========================================
def _couplings_to_mesh(model_data, rn, nonempty_names, node_face_groups,
                       known):
    """
    Group names of the couplings for Code-Aster; a slave face group
    gets a node group '<face group>_N' (DEFI_GROUP in bridge_to_aster).
    A coupling with an empty or missing master or slave selection
    is skipped and reported, like a BC (otherwise Code-Aster stops on
    the unknown group, MODELISA7_77).
    """
    node_group_names = set(model_data.get("node_groups", {}).keys())
    kept = []
    for c in model_data.get("couplings", []):
        master_mw, slave_mw = c["master_group"], c["slave_group"]
        c["master_group"] = rn(master_mw)
        face_group = rn(slave_mw)
        if c.get("slave_kind") == "GROUP_MA" and \
                face_group in node_face_groups:
            # Faces of beam ends: only nodes in the mesh.
            c["slave_kind"] = "GROUP_NO"
        if c.get("slave_kind") == "GROUP_MA":
            slave_ok = face_group in nonempty_names
        else:
            slave_ok = face_group in known
        missing = [n for n, ok in ((master_mw, c["master_group"] in known),
                                   (slave_mw, slave_ok)) if not ok]
        if missing:
            model_data.setdefault("skipped_loads", []).append(
                tr("koppeling {0} '{1}' / '{2}' (lege of ontbrekende "
                   "selectie)",
                   "coupling {0} '{1}' / '{2}' (empty or missing "
                   "selection)").format(c["type"], master_mw, slave_mw))
            log(tr("ERROR: Koppeling {0} '{1}' / '{2}' verwijst naar "
                   "selectie(s) {3}, die leeg zijn of niet bestaan. NIET "
                   "meegenomen.",
                   "ERROR: Coupling {0} '{1}' / '{2}' refers to "
                   "selection(s) {3}, which are empty or do not exist. NOT "
                   "included.").format(
                c["type"], master_mw, slave_mw,
                ", ".join("'{0}'".format(n) for n in missing)))
            continue
        kept.append(c)
        if c.get("slave_kind") != "GROUP_MA":
            c["slave_group"] = face_group
            continue
        # Max. 24 characters (Code-Aster group name): shorten for "_N".
        no_name, k = face_group, 0
        while (no_name in node_group_names or no_name in nonempty_names
               or no_name in known):
            k += 1
            suffix = "_N" if k == 1 else "_N{0}".format(k)
            no_name = face_group[:ASTER_NAME_MAX - len(suffix)] + suffix
        node_group_names.add(no_name)
        c["slave_group_ma"] = face_group
        c["slave_group"] = no_name
        log("INFO: Coupling: slave nodes '{0}' are derived from "
            "face group '{1}'.".format(no_name, face_group))
    model_data["couplings"] = kept


# ==========================================
# ADJUSTING model_data TO THE MESH
# ==========================================
# Dicts with an elset as key (renaming, dropping empty elsets).
_ELSET_KEYS = ("elsets", "elset_dims", "elset_modelisations", "beam_sections",
               "shell_sections", "spring_sections", "shell_upgrades",
               "cable_sections", "discrete_sections")


def _apply_to_model_data(model_data, rn, rn_es, nonempty_names, poi1_groups,
                         group_areas, group_weights, group_integrals,
                         group_faces):
    """rn: Code-Aster name of a selection, rn_es: of an elset."""
    # --- Rename elset-bound dicts ---
    for key in _ELSET_KEYS:
        old = model_data.get(key, {})
        model_data[key] = OrderedDict((rn_es(k), v) for k, v in old.items())
    for key in ("node_groups", "face_selections", "element_selections"):
        old = model_data.get(key, {})
        model_data[key] = OrderedDict((rn(k), v) for k, v in old.items())

    # --- Drop elsets without elements ---
    for elset in list(model_data["elset_modelisations"].keys()):
        if elset not in nonempty_names:
            log(tr("WARNING: Elset '{0}' heeft geen elementen en wordt "
                   "weggelaten uit AFFE_MODELE/AFFE_MATERIAU.",
                   "WARNING: Elset '{0}' has no elements and is "
                   "omitted from AFFE_MODELE/AFFE_MATERIAU.").format(elset))
            for key in _ELSET_KEYS:
                model_data[key].pop(elset, None)

    # --- BCs: names and boundary elements ---
    skin_groups = []
    face_list = model_data.get("group_face_list", {})
    face_sel = model_data.get("face_selections", {})
    shapes = model_data.get("elem_shapes", {})
    node_face_groups = model_data.get("face_node_groups", set())
    known = model_data.get("mesh_group_names", nonempty_names)
    for bc in model_data["bcs"]:
        if not bc["selection"]:
            continue
        bc["selection"] = rn(bc["selection"])
        sel = bc["selection"]
        if sel not in known:
            # Empty or missing selection: skip (otherwise Code-
            # Aster stops with <EXCEPTION> MODELISA7_77 on the unknown group).
            bc["skip"] = True
            model_data.setdefault("skipped_loads", []).append(
                tr("{0} op '{1}' (lege of ontbrekende selectie)",
                   "{0} on '{1}' (empty or missing selection)").format(
                    bc["type"], sel))
            log(tr("ERROR: {0} verwijst naar selectie '{1}', die leeg is of "
                   "niet bestaat. NIET meegenomen.",
                   "ERROR: {0} refers to selection '{1}', which is empty or "
                   "does not exist. NOT included.").format(bc["type"], sel))
            continue
        if bc["aster_target"] == "GROUP_MA" and sel in node_face_groups:
            # Faces of beams: only nodes.
            bc["aster_target"] = "GROUP_NO"
            if bc["type"] == "force":
                # Total force, distributed equally over the nodes just like on
                # a nodeselection (bridge_from_liml, STEP 2);
                # FORCE_NODALE applies the value per node.
                n = len(group_weights.get(sel, ()))
                if n > 1:
                    bc["params"] = _per_area(bc["params"], float(n))
                    bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                        bc["params"])
                log("INFO: Force on beam ends '{0}': distributed over {1} "
                    "nodes (FORCE_NODALE).".format(sel, n))
        if bc["type"] == "pinnedsupport":
            _pinned_to_mean(model_data, bc, group_weights)
            continue
        if bc["type"] == "moment":
            _moment_to_forces(model_data, bc, group_integrals, group_weights)
            continue
        if bc["type"] == "frictionless":
            if _frictionless(model_data, bc, group_faces.get(sel),
                             face_list.get(sel, [])):
                if sel not in skin_groups:
                    skin_groups.append(sel)
            continue
        if bc["type"] == "traction":
            _traction(model_data, bc, group_faces.get(sel), skin_groups)
            continue
        if bc["type"] == "linepressure":
            _line_pressure(model_data, bc, group_faces.get(sel))
            continue
        if bc["type"] == "hydrostaticpressure":
            _hydrostatic(model_data, bc, group_faces.get(sel), skin_groups)
            continue
        if bc["type"] == "compressiononly":
            _compression_only(model_data, bc, face_list.get(sel, []))
            continue
        if bc["type"] == "symmetry":
            _symmetry(model_data, bc, face_list.get(sel, []))
            continue
        if bc["type"] == "surfacepressure" and (
                group_faces.get(sel, {}).get("kinds") or set(["?"])) <= set(
                    ["shelledge", "beam"]):
            # Shell edges and beam ends (before the GROUP_NO jump
            # below: beam faces are only nodes in the mesh)
            _edge_loads(model_data, bc, tr("Druk", "Pressure"))
            continue
        if bc["aster_target"] != "GROUP_MA":
            continue
        # Force on faces: total force / area -> FORCE_FACE on
        # boundary elements of volume elements (FORCE_FACE, U4.44.01).
        if bc["type"] == "force":
            parent = set(shapes.get(eid, "?") for eid in face_sel.get(sel, []))
            area = group_areas.get(sel, 0.0)
            if (sel in face_sel and parent and parent <= _SOLID_SHAPES
                    and area > 0.0):
                bc["params"] = _per_area(bc["params"], area)
                bc["aster_keyword"] = "FORCE_FACE"
                bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                    bc["params"])
                if sel not in skin_groups:
                    skin_groups.append(sel)
                log("INFO: Force on faces '{0}': area {1} m2 -> "
                    "FORCE_FACE.".format(sel, area))
            elif (group_faces.get(sel, {}).get("kinds") == set(["shellface"])
                    and sel in group_integrals):
                # Shell faces: force per area on the mid-surface
                # (FORCE_COQUE FX/FY/FZ, global coordinate system, U4.44.01).
                area = sum(group_integrals[sel][0].values())
                bc["params"] = _per_area(bc["params"], area)
                bc["aster_keyword"] = "FORCE_COQUE"
                bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                    bc["params"])
                log("INFO: Force on shell faces '{0}': area {1} m2 "
                    "-> FORCE_COQUE.".format(sel, area))
            elif (group_faces.get(sel, {}).get("kinds") == set(["shelledge"])
                    and _shell_edge_parent(model_data, sel)):
                # Shell edges: total force / edge length -> FORCE_ARETE
                # (force per length, global; U4.44.01 "line forces to an
                # edge of a volume element or shell"). The edges enter the
                # model with the modelisation of the shell (edge_groups).
                length = _edge_length(model_data, sel)
                if length > 0.0:
                    model_data.setdefault("edge_groups", OrderedDict())[sel] = \
                        _shell_edge_parent(model_data, sel)
                    bc["params"] = _per_area(bc["params"], length)
                    bc["aster_keyword"] = "FORCE_ARETE"
                    bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                        bc["params"])
                    log("INFO: Force on shell edges '{0}': length {1} m "
                        "-> FORCE_ARETE.".format(sel, length))
                else:
                    _not_translated(model_data, bc, tr("Kracht", "Force"),
                                    tr("schaalranden zonder lengte",
                                       "shell edges without length"))
            else:
                bc["skip"] = True
                model_data.setdefault("skipped_loads", []).append(
                    tr("kracht op '{0}' (vlakken van {1})",
                       "force on '{0}' (faces of {1})").format(
                        sel, ", ".join(sorted(parent)) or "?"))
                log(tr("ERROR: Kracht op '{0}': alleen vlakken van volume- "
                       "of schaalelementen worden ondersteund (hier: {1}). "
                       "Belasting NIET meegenomen.",
                       "ERROR: Force on '{0}': only faces of solid "
                       "or shell elements are supported (here: {1}). "
                       "Load NOT included.").format(sel, sorted(parent)))
            continue
        # Pressure on faces of volume elements: the faces must be in
        # AFFE_MODELE (MODELISATION='3D' -> boundary elements).
        if bc["type"] == "surfacepressure" and sel in face_sel:
            parent = set(shapes.get(eid, "?") for eid in face_sel[sel])
            faces = group_faces.get(sel, {})
            if parent and parent <= _SOLID_SHAPES:
                if sel not in skin_groups:
                    skin_groups.append(sel)
            elif faces.get("kinds") == set(["shellface"]) and \
                    len(faces.get("sides", ())) == 1:
                # Shell faces: PRES_REP on the shell elements acts against
                # the element normal; Mecway pressure acts into the face, so
                # against the face normal (faceid 5 = element normal,
                # 6 = reversed): sign = side.
                side = list(faces["sides"])[0]
                if side < 0:
                    bc["params"]["_sign"] = -1.0
                    bc["aster_dict"] = SUPPORTED_BCS[
                        "surfacepressure"].to_aster_dict(bc["params"])
                log("INFO: Pressure on shell faces '{0}' (sign {1:+d})."
                    .format(sel, side))
            else:
                bc["skip"] = True
                model_data.setdefault("skipped_loads", []).append(
                    tr("druk op '{0}' (vlakken van {1})",
                       "pressure on '{0}' (faces of {1})").format(
                        sel, ", ".join(sorted(parent)) or "?"))
                log(tr("ERROR: Druk op '{0}': alleen vlakken van "
                       "volume-elementen, schaalvlakken aan een kant (alle "
                       "faceid 5 of alle 6), schaalranden of balkuiteinden "
                       "(elk apart); hier {1}. NIET meegenomen.",
                       "ERROR: Pressure on '{0}': only faces of "
                       "solid elements, shell faces on one side (all "
                       "faceid 5 or all 6), shell edges or beam ends "
                       "(separately); here {1}. NOT included.").format(
                        sel, ", ".join(sorted(faces.get("kinds", ())))
                        or sorted(parent)))
        elif bc["type"] == "surfacepressure":
            # Element selection: PRES_REP only acts on shell elements
            # (and boundary elements); on volume elements Code-Aster ignores
            # it with alarm CHARGES2_89 (reported in a review; the run itself
            # NOT checked).
            mods = _element_kinds(model_data, sel)
            if mods is not None and not mods <= set(["DKT", "DST",
                                                     "COQUE_3D"]):
                _not_translated(model_data, bc, tr("Druk", "Pressure"),
                                tr("op een elementselectie alleen "
                                   "schaalelementen (hier {0}); kies voor "
                                   "volume-elementen een vlakselectie",
                                   "on an element selection only shell "
                                   "elements (here {0}); for solid "
                                   "elements use a face selection").format(
                                    ", ".join(sorted(mods))))
    # --- Contact (contact2 -> DEFI_CONTACT) ---
    # The faces must be in the model (boundary elements, ORIE_PEAU for an
    # outward normal; DEFI_CONTACT U4.44.11). Shell faces
    # are the shell elements themselves.
    pairs = []
    for c in model_data.get("contacts", []):
        master, slave = rn(c["master"]), rn(c["slave"])
        label = "contact '{0}' / '{1}'".format(c["master"], c["slave"])
        if c.get("selfcontact") or not slave or master == slave:
            model_data.setdefault("skipped_loads", []).append(
                "self-{0}".format(label))
            log(tr("ERROR: Self-contact op '{0}' wordt niet vertaald (Code-"
                   "Aster CONTINUE/DISCRETE vraagt twee verschillende "
                   "vlakgroepen).",
                   "ERROR: Self-contact on '{0}' is not translated (Code-"
                   "Aster CONTINUE/DISCRETE requires two different "
                   "face groups).").format(c["master"]))
            continue
        kinds = set()
        for g in (master, slave):
            kinds |= group_faces.get(g, {}).get("kinds", set(["?"]))
        if not kinds <= set(["solid", "shellface"]):
            model_data.setdefault("skipped_loads", []).append(label)
            log(tr("ERROR: {0}: alleen vlakken van volume-elementen en "
                   "schaalvlakken (hier {1}). NIET meegenomen.",
                   "ERROR: {0}: only faces of solid elements and "
                   "shell faces (here {1}). NOT included.").format(
                    label, sorted(kinds)))
            continue
        for g in (master, slave):
            solid = "solid" in group_faces.get(g, {}).get("kinds", ())
            if solid and g not in skin_groups:
                skin_groups.append(g)
        _check_contact_sides(label, master, slave, group_integrals)
        pairs.append(dict(c, master=master, slave=slave))
    model_data["contacts"] = _merge_contact_zones(
        pairs, group_integrals, model_data["group_ma_unions"])
    # --- Couplings (before the overlap check: it uses the Code-Aster
    # names) ---
    _couplings_to_mesh(model_data, rn, nonempty_names, node_face_groups,
                       known)
    _exclude_fixed_slaves(model_data, group_integrals)
    _report_constraint_overlaps(model_data, group_integrals, group_faces)
    bonded = []
    for c in model_data.get("bonded", []):
        b = _bonded(model_data, c, group_faces, rn)
        if b is not None:
            bonded.append(b)
    model_data["bonded"] = bonded
    model_data["temperatures"] = [
        dict(t, selection=rn(t["selection"]))
        for t in model_data.get("temperatures", [])]

    # Volume faces named by #ASTER code (<<name>>): boundary elements in the
    # model, otherwise e.g. LIAISON_ELEM cannot use them (MODELISA4_50/
    # 4_51, Code-Aster 17.4).
    custom = model_data.get("aster_custom", {})
    text = " ".join(custom.get("code", []) + custom.get("post", []) +
                    custom.get("zone", []) + custom.get("contact", []))
    for name in re.findall(r"<<([^<>]+)>>", text):
        # as bridge_custom.substitute (group_renames: elset wins)
        g = rn_es(name.strip())
        solid = "solid" in group_faces.get(g, {}).get("kinds", ())
        if solid and g not in skin_groups:
            skin_groups.append(g)
    model_data["skin_groups"] = skin_groups
    model_data["initial_velocities"] = [
        (rn(sel), target, v)
        for sel, target, v in model_data.get("initial_velocities", [])]
    model_data["bcs"] = [bc for bc in model_data["bcs"]
                         if not bc.get("skip")]

    # --- POI1 groups and rotation DOFs ---
    model_data["poi1_groups"] = poi1_groups
    dis_tr = ("DIS_TR" in poi1_groups.values() or any(
        d["mod"] == "DIS_TR" for d in model_data.get("discretes", {}).values()))
    if dis_tr and not model_data["has_rot_dofs"]:
        model_data["has_rot_dofs"] = True
        for bc in model_data["bcs"]:
            bc["params"]["_has_rot_dofs"] = True
            # Only fixed depends on the flag; the aster_dict of other
            # BCs is already adjusted above (traction PLAN, pressure sign).
            if bc["type"] == "fixed":
                bc["aster_dict"] = SUPPORTED_BCS[bc["type"]].to_aster_dict(
                    bc["params"])
        log("INFO: has_rot_dofs = True due to DIS_TR nodes; BCs recomputed.")
