# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_cyclic.py
#
# Responsibility: modal analysis with cyclic symmetry (Mecway
# Frequency (V30) with a Cyclic symmetry constraint, manual v33 par. 9.41)
# to Code-Aster's cyclic substructuring (R4.06.03, U4.52.05):
#   sector modes with fixed cut faces (CALC_MODES, Craig-Bampton) ->
#   DEFI_INTERF_DYNA (DROITE/GAUCHE/AXE, TYPE 'CRAIGB') -> DEFI_BASE_MODALE
#   CLASSIQUE (+ static modes of the cut faces) -> MODE_ITER_CYCL
#   (modes per number of nodal diameters) -> REST_SOUS_STRUC SECTEUR=1 (and,
#   setting cyclic_full_wheel, DEFI_SQUELETTE CYCLIQUE + REST_SOUS_STRUC
#   SQUELETTE: the whole wheel) -> aster_cyclic.collect (Mecway's order,
#   back to the coordinate system of the model) -> aster_results_export (the
#   modes on the whole wheel in Mecway's numbering, or on the sector) ->
#   bridge_results_liml.splice_results (the nodes and elements of the N
#   sectors in the model copy of <solution>, like Mecway).
# Syntax: Code-Aster test cases sdlv134a, sdls04a, sdlv301a (17.4,
# share/aster/tests) and the catalogue mode_iter_cycl.py of code_aster 17.4.
#
#   parse(item, model_data, run_cfg)  <cyclicsymmetry> from the .liml
#                                     (bridge_from_liml)
#   is_cyclic(model_data)             cyclic symmetry in the model
#   build_cyclic_modes(...)           builder (bridge_to_aster._build_modal)
#
# Mecway input (measured headless with Mecway 33, TestFiles/Tools/
# mw_solve.py; Samples/Impeller.liml):
#   <cyclicsymmetry axis="3" segments="12" selectionmaster="A"
#                   selectionslave="B" />
#   axis: 1 = X, 2 = Y, 3 = Z (ring sector about Z: axis 3 gave the
#   frequencies of the full ring, 1 and 2 did not; about Y: axis 2; "0"
#   gave the same as 1). The axis passes through the origin (there is no
#   attribute for a point).
#   Master and slave are node or face selections; the slave lies at +360/N
#   or -360/N degrees from the master (Mecway determines the direction).
#   Mecway computes maxmode modes per number of nodal diameters ND = 0 ..
#   N/2 (rounded down), and sorts them by ND and frequency
#   (manual par. 9.41: "5 modes ... 7 segments ... 20 modes"); the
#   solution shows the full wheel. A pair of standing waves (ND > 0)
#   counts as one mode.
#
# Code-Aster:
#   - The symmetry axis must be the Z axis (U4.52.05 par. 1); DROITE and
#     GAUCHE follow the trigonometric direction in the XY plane: GAUCHE
#     lies at +360/N degrees from DROITE. The other way round gave
#     <EXCEPTION> ALGORITH16_58 "INVERSION INTERFACE DROITE/GAUCHE" (seen,
#     Code-Aster 17.4). With an X or Y axis the bridge writes the
#     coordinates in the mesh file with a cyclic permutation of the axes
#     (_rewrite_mesh; = ROTATION below) and converts the directions in the
#     loads (_permute_charges); aster_cyclic rotates mesh and shapes back.
#   - REST_SOUS_STRUC has NOM_CHAM 'ACCE' by default (seen): the bridge
#     asks for 'DEPL'.
#   - The nodes of DROITE and GAUCHE are in the same order (pairs);
#     MODE_ITER_CYCL checks their positions (VERI_CYCL).
#   - Nodes on the axis: interface AXE ("points communs a tous les secteurs",
#     U4.52.05 par. 3.4.1; test case sdlv134a).
#   - The accuracy depends on the number of sector modes in the basis
#     (cyclic_base_modes; measured in docs/Verificatie.md, CY).
#
# Compatible with IronPython 2.7.9 (standard library only).

import math
import os
import re
from collections import OrderedDict

from bridge_utils import log, tr, CONFIG_BRIDGE, run_name

TAG = "cyclicsymmetry"

# Mecway axis -> index (0 = X, 1 = Y, 2 = Z); see the header.
_AXES = {"0": 0, "1": 0, "2": 1, "3": 2}
_AXIS_NAMES = "XYZ"

# Rotate the mesh to the Z axis (MODE_ITER_CYCL): rotation about (1, 1, 1)
# by ANGLE degrees. +120: e_x -> e_y -> e_z -> e_x, so axis Y -> Z and a
# point (x, y, z) -> (z, x, y); -120: axis X -> Z, (x, y, z) -> (y, z, x).
# Component names in the loads follow (_RENAME), vectors as a tuple
# (_TUPLE: new order of the old components).
ROTATION = {"X": -120.0, "Y": 120.0}
_RENAME = {"Y": {"X": "Y", "Y": "Z", "Z": "X"},
           "X": {"X": "Z", "Y": "X", "Z": "Y"}}
_TUPLE = {"Y": (1, 2, 0), "X": (2, 0, 1)}

# Groups in the mesh (bridge_mesh names are Mecway names; Mecway does not
# use these prefixes).
GROUP_RIGHT = "BRCYC_D"     # DROITE (lower angle)
GROUP_LEFT = "BRCYC_G"      # GAUCHE (+360/N)
GROUP_AXIS = "BRCYC_A"      # nodes on the axis
GROUP_FIX = "BRCYC_F"       # free node of a pair with a fixed node

TEMPLATE = "AsterTemplate_ModeIterCycl.comm"

# Coordinates smaller than _SNAP x the model size become 0 (_rewrite_mesh).
_SNAP = 1.0e-12

# BCs that fix degrees of freedom (per direction): on a cut face only
# fully fixed (all three displacements) is allowed.
_DOF_BCS = ("fixed", "displacement")
# BCs with relations between directions or nodes: not on a cut face.
_RELATION_BCS = ("pinnedsupport", "symmetry", "frictionless",
                 "compressiononly", "velocity")


# ==========================================
# INPUT FROM THE .LIML
# ==========================================
def accepts(run_cfg):
    """True if the analysis can translate cyclic symmetry: modal
    (CALC_MODES DYNAMIQUE), not acoustic."""
    return (run_cfg.get("solver_command") == "CALC_MODES" and
            run_cfg.get("type_resu", "DYNAMIQUE") == "DYNAMIQUE" and
            run_cfg.get("phenomene", "MECANIQUE") != "ACOUSTIQUE")


def parse(item, model_data, run_cfg):
    """
    <cyclicsymmetry axis segments selectionmaster selectionslave> to
    model_data["cyclic"]. Not in a modal analysis, or a second
    cyclic symmetry: ERROR and skipped_loads (not translated).
    """
    if item.get("suppressed", "") == "true":
        log("INFO: Cyclic symmetry skipped (suppressed).")
        return
    master = item.get("selectionmaster", "")
    slave = item.get("selectionslave", "")
    what = tr("cyclische symmetrie '{0}' / '{1}'",
              "cyclic symmetry '{0}' / '{1}'").format(master, slave)
    if not accepts(run_cfg):
        model_data["skipped_loads"].append(what)
        log(tr("ERROR: Cyclische symmetrie wordt alleen in een modale "
               "analyse vertaald (Mecway Frequency, bridge-analyse "
               "modal_3d), niet in {0}. NIET meegenomen: het model rekent "
               "als losse sector.",
               "ERROR: Cyclic symmetry is only translated in a modal "
               "analysis (Mecway Frequency, bridge analysis modal_3d), not "
               "in {0}. NOT included: the model is computed as a single "
               "sector.").format(run_cfg.get("solver_command", "?")))
        return
    if model_data.get("cyclic"):
        model_data["skipped_loads"].append(what)
        log(tr("ERROR: Meer dan een cyclische symmetrie; alleen de eerste "
               "wordt vertaald.",
               "ERROR: More than one cyclic symmetry; only the first is "
               "translated."))
        return
    try:
        segments = int(float(item.get("segments", "0")))
    except ValueError:
        segments = 0
    axis = _AXES.get(item.get("axis", "3").strip(), None)
    if axis is None:
        model_data["skipped_loads"].append(what)
        log(tr("ERROR: Cyclische symmetrie: onbekende as '{0}'. NIET "
               "meegenomen.",
               "ERROR: Cyclic symmetry: unknown axis '{0}'. NOT "
               "included.").format(item.get("axis")))
        return
    model_data["cyclic"] = {"axis": axis, "segments": segments,
                            "master": master, "slave": slave}
    log("INFO: Cyclic symmetry: {0} segments about the {1} axis, master "
        "'{2}', slave '{3}'.".format(segments, _AXIS_NAMES[axis], master,
                                     slave))


def is_cyclic(model_data):
    return bool(model_data.get("cyclic"))


def axis_index(text):
    """Mecway's axis attribute ("1"/"2"/"3", "0" = X) to 0/1/2, or
    None."""
    return _AXES.get((text or "3").strip(), None)


# ==========================================
# NODES OF SELECTIONS
# ==========================================
def _elem_nodes(model_data):
    """{eid: (aster_type, [nid in Code-Aster order])} (bridge_mesh)."""
    conn = model_data.get("_conn")
    if conn:
        return conn
    import bridge_mesh
    out = {}
    for eid, shape, enodes, _elset in model_data.get("mesh_elements", []):
        spec = bridge_mesh._ASTER_TYPES.get(shape)
        if spec:
            out[eid] = (spec[0], [enodes[i] for i in spec[1]])
    return out


def _face_nodes(conn, eid, fid):
    """Corner and mid-side nodes of face fid of element eid (table of
    bridge_mesh, as without the Mecway API; in Mecway equal to
    mw.face_nodes, checked by bridge_mesh)."""
    import bridge_mesh
    if eid not in conn:
        return []
    atype, cn = conn[eid]
    corners = bridge_mesh._face_from_table(atype, cn, fid)
    if not corners:
        return []
    return list(bridge_mesh._skin_element(atype, cn, corners)[1])


def _selection_nodes(model_data, name, conn):
    """
    Node numbers of a selection (Mecway or Code-Aster name): node,
    face or element selection; None if it does not exist.
    """
    renames = model_data.get("selection_renames", {})
    reverse = dict((v, k) for k, v in renames.items())
    aster = renames.get(name, name)
    mecway = reverse.get(name, name)
    groups = model_data.get("node_groups", {})
    for key in (aster, name, mecway):
        if key in groups:
            return set(int(str(n).lstrip("N")) for n in groups[key])
    faces = model_data.get("face_selection_faces", {})
    for key in (mecway, name, aster):
        if key in faces:
            out = set()
            for eid, fid in faces[key]:
                out.update(_face_nodes(conn, eid, fid))
            return out
    elems = model_data.get("element_selections", {})
    for key in (aster, name, mecway):
        if key in elems:
            out = set()
            for eid in elems[key]:
                out.update(conn.get(int(eid), (None, []))[1])
            return out
    return None


# ==========================================
# MASTER-SLAVE PAIRS
# ==========================================
def _rotate(p, axis, angle):
    """Point p rotated about the axis (index) through the origin."""
    c, s = math.cos(angle), math.sin(angle)
    i, j = (axis + 1) % 3, (axis + 2) % 3
    q = list(p)
    q[i] = c * p[i] - s * p[j]
    q[j] = s * p[i] + c * p[j]
    return tuple(q)


class _Grid(object):
    """Spatial grid to find nodes by coordinate."""

    def __init__(self, coords, nids, h):
        self.h = h
        self.cells = {}
        self.coords = coords
        for n in nids:
            self.cells.setdefault(self._key(coords[n]), []).append(n)

    def _key(self, p):
        return tuple(int(math.floor(v / self.h)) for v in p)

    def nearest(self, p):
        k = self._key(p)
        best, dist = None, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for n in self.cells.get((k[0] + dx, k[1] + dy,
                                             k[2] + dz), ()):
                        q = self.coords[n]
                        d = math.sqrt(sum((q[a] - p[a]) ** 2
                                          for a in range(3)))
                        if dist is None or d < dist:
                            best, dist = n, d
        return best, dist


def _pairs(coords, master, slave, axis, n_seg, tol):
    """
    (pairs [(droite, gauche)], axis nodes, error) with gauche at +360/N
    degrees from droite; error = message or None.
    """
    def radius(p):
        return math.sqrt(sum(p[a] ** 2 for a in range(3) if a != axis))
    on_axis = set(n for n in master | slave if radius(coords[n]) <= tol)
    m = sorted(master - on_axis)
    s = sorted(slave - on_axis)
    if len(m) != len(s):
        return None, on_axis, tr(
            "master en slave hebben een verschillend aantal knopen buiten "
            "de as ({0} en {1})", "master and slave have a different number "
            "of nodes off the axis ({0} and {1})").format(len(m), len(s))
    if not m:
        return None, on_axis, tr("geen knopen buiten de as",
                                 "no nodes off the axis")
    grid = _Grid(coords, s, max(10.0 * tol, 1e-12))
    alpha = 2.0 * math.pi / n_seg
    worst = {}
    for sign in (1.0, -1.0):
        pairs = []
        used = set()
        worst[sign] = 0.0
        for n in m:
            q, d = grid.nearest(_rotate(coords[n], axis, sign * alpha))
            if q is None or d > tol or q in used:
                worst[sign] = max(worst[sign], d if d is not None else
                                  float("inf"))
                pairs = None
                break
            used.add(q)
            pairs.append((n, q) if sign > 0 else (q, n))
        if pairs is not None:
            pairs.sort()
            return pairs, on_axis, None
    return None, on_axis, tr(
        "de slave-knopen liggen niet op +/-360/{0} graden van de "
        "master-knopen om de {1}-as door de oorsprong (binnen {2:.3g} m)",
        "the slave nodes do not lie at +/-360/{0} degrees from the master "
        "nodes about the {1} axis through the origin (within {2:.3g} "
        "m)").format(n_seg, _AXIS_NAMES[axis], tol)


# ==========================================
# SUPPORTS ON THE CUT FACES
# ==========================================
def _constrained(model_data, conn):
    """
    ({node: set(DX/DY/DZ) fixed}, set(nodes with a relation)) from
    the BCs, constraint equations and couplings.
    """
    dofs = {}
    related = set()
    for bc in model_data.get("bcs", []):
        if bc.get("skip") or not bc.get("selection"):
            continue
        if bc["type"] in _DOF_BCS:
            if bc["type"] == "fixed":
                comps = ("DX", "DY", "DZ")
            else:
                comps = [k for k in bc.get("aster_dict", {})
                         if k in ("DX", "DY", "DZ")]
            nodes = _selection_nodes(model_data, bc["selection"], conn)
            for n in nodes or ():
                dofs.setdefault(n, set()).update(comps)
        elif bc["type"] in _RELATION_BCS:
            nodes = _selection_nodes(model_data, bc["selection"], conn)
            related.update(nodes or ())
    for ce in model_data.get("constraint_equations", []):
        related.update(int(n) for n, _d, _c in ce["terms"])
    for c in model_data.get("couplings", []):
        for key in ("slave_group", "master_group"):
            nodes = _selection_nodes(model_data, c.get(key, ""), conn)
            related.update(nodes or ())
    return dofs, related


# ==========================================
# LOADS IN THE COMPUTATION FRAME (axis -> Z)
# ==========================================
def _permute_entry(text, axis_name):
    """An _F(...) text with the directions in the rotated frame."""
    ren = _RENAME[axis_name]
    order = _TUPLE[axis_name]
    text = re.sub(r"\b([DF])([XYZ])(\s*=)",
                  lambda m: m.group(1) + ren[m.group(2)] + m.group(3), text)
    text = re.sub(r"'D([XYZ])'", lambda m: "'D" + ren[m.group(1)] + "'",
                  text)

    def vec(m):
        vals = [v.strip() for v in m.group(3).split(",")]
        if len(vals) != 3:
            return m.group(0)
        new = [None] * 3
        for k in range(3):
            new[order[k]] = vals[k]
        return "{0}{1}{2}{3}".format(m.group(1), m.group(2), ", ".join(new),
                                     m.group(4))
    return re.sub(r"\b((?:DIRECTION|AXE|CENTRE)\s*=\s*)([\(\[])([^\)\]]*)"
                  r"([\)\]])", lambda m: vec(m), text)


_NOT_PERMUTED = re.compile(r"\bANGL_NAUT\s*=|\bDR[XYZ]\b|\bM[XYZ]\s*=")


def _permute_charges(charges, axis_name):
    """
    Copy of the loads (_build_charges) in the rotated frame, or
    (None, reason) if a load cannot be converted.
    """
    out = []
    for command, kws, fonc in charges:
        if command != "AFFE_CHAR_MECA":
            return None, tr("een last met een functie ({0})",
                            "a load with a function ({0})").format(
                                ", ".join(kws))
        new = OrderedDict()
        for kw, entries in kws.items():
            # The bridge does not convert skewed coordinate systems and
            # rotations/moments (with volume elements they normally do not
            # occur).
            if kw in ("LIAISON_OBLIQUE",) or any(
                    _NOT_PERMUTED.search(e) for e in entries):
                return None, kw
            new[kw] = [_permute_entry(e, axis_name) for e in entries]
        out.append((command, new, fonc))
    return out, None


# ==========================================
# MODEL CHECK
# ==========================================
def _check_model(model_data, analysis):
    """What the cyclic route cannot do: ERROR with the solution."""
    import bridge_to_aster as b2a
    ok = True
    cyc = model_data["cyclic"]
    if cyc["segments"] < 2:
        log(tr("ERROR: Cyclische symmetrie met {0} segment(en); geef in "
               "Mecway het aantal segmenten van het hele wiel (minstens 2).",
               "ERROR: Cyclic symmetry with {0} segment(s); enter in Mecway "
               "the number of segments of the whole wheel (at least "
               "2).").format(cyc["segments"]))
        ok = False
    dims = model_data.get("elset_dims", {})
    other = [e for e, d in dims.items() if d != "3D"]
    if other:
        # Mecway: "Shells and beams are not allowed in frequency analysis"
        # with the internal solver (manual v33 par. 9.41).
        log(tr("ERROR: Cyclische symmetrie alleen met volume-elementen (ook "
               "in Mecway, manual par. 9.41); niet met {0}.",
               "ERROR: Cyclic symmetry only with solid elements (also in "
               "Mecway, manual section 9.41); not with {0}.").format(
                   ", ".join("'{0}'".format(e) for e in other)))
        ok = False
    if model_data.get("line_quad"):
        log(tr("ERROR: Cyclische symmetrie met elem_hex8 = LINE_QUAD kan "
               "niet: de nieuwe middenknopen op de snijvlakken hebben geen "
               "paar. Gebruik kwadratische elementen in Mecway (hex20), of "
               "elem_hex8 = 3D (pagina Elementen).",
               "ERROR: Cyclic symmetry with elem_hex8 = LINE_QUAD is not "
               "possible: the new midside nodes on the cut faces have no "
               "pair. Use quadratic elements in Mecway (hex20), or "
               "elem_hex8 = 3D (Elements page)."))
        ok = False
    if model_data.get("bonded"):
        log(tr("ERROR: Verlijmd contact met cyclische symmetrie wordt niet "
               "vertaald.",
               "ERROR: Bonded contact with cyclic symmetry is not "
               "translated."))
        ok = False
    return ok


def _base_count(analysis, n):
    """Number of sector modes (fixed cut faces) in the basis: setting
    cyclic_base_modes, 0 = automatic max(20, 4 n)."""
    nb = int(analysis.get("cyclic_base_modes", 0) or 0)
    if nb <= 0:
        nb = max(20, 4 * n)
    return max(nb, n)


def _fmt_names(nids, per_line=10):
    names = ["N{0}".format(n) for n in nids]
    return "\n".join(" " + " ".join(names[i:i + per_line])
                     for i in range(0, len(names), per_line))


def to_model_frame(xyz, axis):
    """
    Coordinates from the .mail of a cyclic run back to the frame of
    the model: the inverse of the permutation in _rewrite_mesh (there
    new[_TUPLE[a]] = old[a], so model[a] = mesh[_TUPLE[a]]). axis: index
    0/1/2 (X/Y/Z, bridge_results_liml.cyclic_info); unchanged for Z.
    For bridge_results_liml.check_results_fit (Results... button).
    """
    order = _TUPLE.get(_AXIS_NAMES[axis]) if axis in (0, 1, 2) else None
    if order is None:
        return tuple(xyz)
    return tuple(xyz[order[a]] for a in range(3))


def _rewrite_mesh(msh_path, groups, axis_name, size):
    """
    Node groups (in this order) at the end of the ASTER mesh, and the
    coordinates in the computation frame (_TUPLE with an X or Y axis:
    axis -> Z). An exact permutation in the file, no MODI_MAILLAGE
    ROTATION beforehand, and coordinates smaller than _SNAP x the model
    size become 0:
    MODE_ITER_CYCL compares the axial coordinate of the pairs relatively,
    and noise around 0 (1e-17 after a rotation; 1.9e-20 against 6.0e-20 m
    in Mecway's own Impeller.liml) gave <EXCEPTION> ALGORITH16_52 "axe de
    symetrie cyclique different de Oz" (seen with Code-Aster 17.4). The
    shift (< 1e-12 x the model size) is within the check of the
    node order in aster_results_export (1e-9).
    """
    with open(msh_path, "r") as f:
        text = f.read()
    order = _TUPLE.get(axis_name, (0, 1, 2))
    snap = _SNAP * size
    lines = text.split("\n")
    inside = False
    for k, line in enumerate(lines):
        word = line.strip()
        if word == "COOR_3D":
            inside = True
            continue
        if inside and word == "FINSF":
            inside = False
            continue
        if inside and word:
            parts = word.split()
            new = [None] * 3
            for a in range(3):
                v = parts[1 + a]
                if abs(float(v)) < snap:
                    v = "0.0"
                new[order[a]] = v
            lines[k] = " " + " ".join([parts[0]] + new + parts[4:])
    text = "\n".join(lines)
    body = text.rstrip()
    if not body.endswith("FIN"):
        raise IOError("mesh zonder FIN: {0}".format(msh_path))
    body = body[:-3]
    for name, nids in groups:
        if nids:
            body += "GROUP_NO\n {0}\n{1}\nFINSF\n".format(
                name, _fmt_names(nids))
    with open(msh_path, "w") as f:
        f.write(body + "FIN\n")


def _relations(pairs, n_seg):
    """LIAISON_DDL for ND 0 in the Z frame: u_G = R_z(360/N) u_D."""
    a = 2.0 * math.pi / n_seg
    c, s = math.cos(a), math.sin(a)
    out = []
    for d, g in pairs:
        nd, ng = "'N{0}'".format(d), "'N{0}'".format(g)
        out.append("_F(NOEUD=({0}, {1}, {1}), DDL=('DX', 'DX', 'DY'), "
                   "COEF_MULT=(1.0, {2!r}, {3!r}), COEF_IMPO=0.0)".format(
                       ng, nd, -c, s))
        out.append("_F(NOEUD=({0}, {1}, {1}), DDL=('DY', 'DX', 'DY'), "
                   "COEF_MULT=(1.0, {2!r}, {3!r}), COEF_IMPO=0.0)".format(
                       ng, nd, -s, -c))
        out.append("_F(NOEUD=({0}, {1}), DDL=('DZ', 'DZ'), "
                   "COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0)".format(ng, nd))
    return out


# ==========================================
# BUILDER
# ==========================================
def build_cyclic_modes(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate the .comm and .export for modes with cyclic symmetry
    (MODE_ITER_CYCL). Returns the path of the .export, or None (ERROR
    logged). Called from bridge_to_aster._build_modal (V30 with
    <cyclicsymmetry>), na _collapse_histories.
    """
    import bridge_to_aster as b2a
    log("--- Generating Aster Files (MODE_ITER_CYCL) ---")
    if not _check_model(model_data, analysis):
        return None
    cyc = model_data["cyclic"]
    n_seg = cyc["segments"]
    axis = cyc["axis"]
    axis_name = _AXIS_NAMES[axis]
    conn = _elem_nodes(model_data)
    coords = model_data.get("mesh_nodes", {})

    # --- cut faces ---
    master = _selection_nodes(model_data, cyc["master"], conn)
    slave = _selection_nodes(model_data, cyc["slave"], conn)
    for name, nodes in ((cyc["master"], master), (cyc["slave"], slave)):
        if not nodes:
            log(tr("ERROR: Cyclische symmetrie: selectie '{0}' bestaat niet "
                   "of is leeg.",
                   "ERROR: Cyclic symmetry: selection '{0}' does not exist "
                   "or is empty.").format(name))
            return None
    size = max([abs(v) for p in coords.values() for v in p] + [1e-12])
    tol = 1.0e-5 * size
    pairs, on_axis, err = _pairs(coords, master, slave, axis, n_seg, tol)
    if err:
        log(tr("ERROR: Cyclische symmetrie: {0}. Controleer het aantal "
               "segmenten, de as en dat de knopen van de twee snijvlakken "
               "op elkaar passen (Mecway eist dat ook met de interne "
               "solver, manual par. 9.41).",
               "ERROR: Cyclic symmetry: {0}. Check the number of segments, "
               "the axis and that the nodes of both cut faces match (Mecway "
               "requires that too with the internal solver, manual section "
               "9.41).").format(err))
        return None

    # --- supports on the cut faces ---
    dofs, related = _constrained(model_data, conn)
    full = set(n for n, d in dofs.items() if len(d) == 3)
    cut = set(n for p in pairs for n in p) | on_axis
    partial = sorted(n for n in cut if (n in dofs and n not in full) or
                     (n in related and n not in full))
    if partial:
        log(tr("ERROR: Cyclische symmetrie: {0} knoop/knopen op de "
               "snijvlakken hebben een gedeeltelijke oplegging of een "
               "relatie (bijv. N{1}). De bridge kan op een snijvlak alleen "
               "volledig vaste knopen (fixed, of displacement 0 in X, Y en "
               "Z). Haal de oplegging van het snijvlak, of leg die knopen "
               "volledig vast.",
               "ERROR: Cyclic symmetry: {0} node(s) on the cut faces have "
               "a partial support or a relation (e.g. N{1}). On a cut face "
               "the bridge only supports fully fixed nodes (fixed, or "
               "displacement 0 in X, Y and Z). Remove the support from the "
               "cut face, or fix those nodes completely.").format(
                   len(partial), partial[0]))
        return None
    free_pairs = [(d, g) for d, g in pairs if d not in full and g not in full]
    extra_fix = sorted(set(d if g in full else g for d, g in pairs
                           if (d in full) != (g in full)))
    axis_nodes = sorted(n for n in on_axis if n not in full)
    if not free_pairs:
        log(tr("ERROR: Cyclische symmetrie: alle knopen op de snijvlakken "
               "liggen vast; de sectoren zijn dan niet gekoppeld. Reken "
               "zonder cyclische symmetrie.",
               "ERROR: Cyclic symmetry: all nodes on the cut faces are "
               "fixed; the sectors are then not coupled. Compute without "
               "cyclic symmetry."))
        return None
    if axis_nodes and n_seg == 8:
        # Code-Aster 17.4, bibfor/algorith/ctetax.F90: the check of the
        # axis nodes rotates the vector (1, 1, 1) of active degrees of
        # freedom by 360/N degrees; at 45 degrees cos - sin = 0, so DX is
        # "missing": <EXCEPTION> ALGORITH14_95 "il manque un ddl sur un noeud
        # axe" (seen with a circular plate, N = 8; not with N = 6 and 12).
        log(tr("ERROR: Cyclische symmetrie met 8 segmenten en knopen op de "
               "as ({0}) kan Code-Aster 17.4 niet rekenen (MODE_ITER_CYCL "
               "stopt met ALGORITH14_95, een fout in Code-Aster bij 45 "
               "graden). Maak in Mecway een klein gat op de as (geen knopen "
               "op de as), of reken het volledige model.",
               "ERROR: Cyclic symmetry with 8 segments and nodes on the "
               "axis ({0}) cannot be computed by Code-Aster 17.4 "
               "(MODE_ITER_CYCL stops with ALGORITH14_95, a Code-Aster bug "
               "at 45 degrees). Make a small hole on the axis in Mecway (no "
               "nodes on the axis), or compute the full model.").format(
                   len(axis_nodes)))
        return None
    if extra_fix:
        log("INFO: Cyclic symmetry: {0} node(s) on a cut face "
            "fixed because the corresponding node on the other cut face "
            "is fixed.".format(len(extra_fix)))
    log("INFO: Cyclic symmetry: {0} node pairs{1}{2}, axis {3}, {4} "
        "segments ({5:.6g} degrees).".format(
            len(free_pairs), ", {0} nodes on the axis".format(len(axis_nodes))
            if axis_nodes else "", ", {0} pairs with a fixed node".format(
                len(pairs) - len(free_pairs)) if len(pairs) != len(
                    free_pairs) else "", axis_name, n_seg, 360.0 / n_seg))

    # --- settings ---
    n = b2a._mode_count(model_data, analysis)
    nb = _base_count(analysis, n)
    shift = float(analysis.get("modal_shift_hz", 0.0) or 0.0)
    if analysis.get("modal_complex", False):
        log(tr("WARNING: Complexe modes (modal_complex) met cyclische "
               "symmetrie worden niet gebouwd; de bridge rekent reele modes "
               "zonder demping (zoals Mecway).",
               "WARNING: Complex modes (modal_complex) with cyclic symmetry "
               "are not built; the bridge computes real modes without "
               "damping (like Mecway)."))
    wanted = [f for f in analysis.get("fields", ["displacements"])
              if f != "displacements"]
    if wanted:
        log("INFO: Cyclic symmetry: only the mode shapes go to "
            "Mecway; ignored: {0}.".format(", ".join(wanted)))
    norm = str(analysis.get("modal_norm", "MASS_GENE")).upper()
    if norm != "MASS_GENE":
        log("INFO: Cyclic symmetry: the normalization ({0}) applies only to "
            "the sector basis; the scale of the cyclic modes is that of "
            "REST_SOUS_STRUC.".format(norm))

    # --- loads ---
    prestress_on = bool(analysis.get("modal_prestress", True))
    charges, names_bc, names_load = b2a._modal_charges(model_data, False,
                                                       prestress_on)
    prestress = None
    if prestress_on and (names_load or b2a._thermal_active(model_data)):
        prestress = b2a._prestress_plan(model_data, charges, names_bc,
                                        names_load)
        if prestress is None:
            return None
    rotate_block = "#-- symmetry axis is Z: no rotation --\n"
    if axis_name != "Z":
        perm, why = _permute_charges(charges, axis_name)
        if perm is None or model_data.get("_charge_prelude"):
            log(tr("ERROR: Cyclische symmetrie om de {0}-as: de bridge draait "
                   "het model naar de Z-as (MODE_ITER_CYCL eist Z), maar kan "
                   "{1} niet meedraaien. Draai het model in Mecway zo dat de "
                   "symmetrieas de Z-as is.",
                   "ERROR: Cyclic symmetry about the {0} axis: the bridge "
                   "rotates the model to the Z axis (MODE_ITER_CYCL requires "
                   "Z), but cannot rotate {1}. Rotate the model in Mecway so "
                   "that the symmetry axis is the Z axis.").format(
                       axis_name, why or tr("een formule-last",
                                            "a formula load")))
            return None
        charges = perm
        if model_data.get("aster_custom", {}).get("code"):
            log(tr("WARNING: Cyclische symmetrie om de {0}-as: #ASTER-code "
                   "rekent in het gedraaide frame (as {0} -> Z); richtingen "
                   "daarin gelden in dat frame.",
                   "WARNING: Cyclic symmetry about the {0} axis: #ASTER code "
                   "is computed in the rotated frame (axis {0} -> Z); "
                   "directions in it apply in that frame.").format(axis_name))
        rotate_block = (
            "# Symmetry axis {0} -> Z: MODE_ITER_CYCL needs the Z axis (U4.52.05\n"
            "# par. 1). The mesh file is already in the computation frame (cyclic\n"
            "# permutation of the axes = rotation {1!r} degrees about (1, 1, 1),\n"
            "# bridge_cyclic._rewrite_mesh), and so are the loads\n"
            "# (_permute_charges); aster_cyclic rotates mesh and shapes back.\n"
            ).format(axis_name, ROTATION[axis_name])
    try:
        _rewrite_mesh(msh_path, [
            (GROUP_RIGHT, [d for d, g in free_pairs]),
            (GROUP_LEFT, [g for d, g in free_pairs]),
            (GROUP_AXIS, axis_nodes), (GROUP_FIX, extra_fix)], axis_name,
            size)
    except Exception as e:
        log(tr("ERROR: Snijvlakgroepen niet in het mesh gezet: {0}",
               "ERROR: Cut face groups not written to the mesh: {0}")
            .format(e))
        return None
    loads_block, excit_clause = b2a._render_charges(charges, model_data)
    cyc_names = ["cycl_if"]
    cyc_lines = [
        "# Cyclic symmetry (bridge_cyclic): cut faces fixed for the",
        "# sector basis (Craig-Bampton, U4.52.05; test case sdlv134a).",
        "cycl_if = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(",
        "    GROUP_NO=({0}), DX=0.0, DY=0.0, DZ=0.0))".format(", ".join(
            "'{0}'".format(g) for g in [GROUP_RIGHT, GROUP_LEFT] +
            ([GROUP_AXIS] if axis_nodes else [])) + ","),
    ]
    fix_names = []
    if extra_fix:
        fix_names = ["cycl_fix"]
        cyc_lines += [
            "# Free node of a pair whose other node is fixed.",
            "cycl_fix = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(",
            "    GROUP_NO='{0}', DX=0.0, DY=0.0, DZ=0.0))".format(GROUP_FIX)]
    static_block = "#-- not applicable (no prestress) --\n"
    if prestress:
        rel = _relations(free_pairs, n_seg)
        ddl = ""
        if axis_nodes:
            ddl = ("    DDL_IMPO=_F(GROUP_NO='{0}', DX=0.0, DY=0.0),\n"
                   .format(GROUP_AXIS))
        cyc_lines += [
            "# Prestress: the static state is cyclically symmetric",
            "# (ND 0): u_gauche = R_z(360/N) u_droite; nodes on the axis only",
            "# axially.",
            "cycl_rel = AFFE_CHAR_MECA(MODELE=model,",
            ddl + "    LIAISON_DDL=(",
        ] + ["        {0},".format(r) for r in rel] + ["    ),", ")"]
        # All loads are constant here (_collapse_histories); the EXCIT
        # of _render_charges plus the cyclic relations.
        names = (["load_{0}".format(k + 1) for k in range(len(charges))] +
                 list(model_data.get("aster_custom", {}).get("excit", [])) +
                 ["cycl_rel"] + fix_names)
        excit = "    EXCIT=(\n{0}    ),".format("".join(
            "        _F(CHARGE={0}),\n".format(x) for x in names))
        static_block = (
            "# Prestress: stress state under the applied loads\n"
            "# (Mecway manual v33 par. 6.3, stress stiffening).\n"
            "stat = MECA_STATIQUE(\n"
            "    MODELE=model,\n"
            "    CHAM_MATER=fieldmat,\n"
            "{cara}{excit}\n"
            "    SOLVEUR=_F(METHODE='MUMPS', NPREC={nprec}),\n"
            ")\n"
            "sig = CREA_CHAMP(OPERATION='EXTR', TYPE_CHAM='ELGA_SIEF_R',\n"
            "                 RESULTAT=stat, NUME_ORDRE=1, "
            "NOM_CHAM='SIEF_ELGA')\n").format(
                cara="    CARA_ELEM=cara,\n" if b2a._has_cara(model_data)
                else "", excit=excit,
                nprec=int(analysis.get("solver_nprec", 8)))
    cyclic_loads_block = "\n".join(cyc_lines) + "\n"

    cara_ref = "    CARA_ELEM=cara,\n" if b2a._has_cara(model_data) else ""
    extra = model_data.get("aster_custom", {}).get("excit", [])
    rotation = prestress["rotation"] if prestress else []
    charge_names = (list(names_bc) + [x for x in extra if x not in names_bc]
                    + [x for x in rotation] + cyc_names + fix_names)
    second = "        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n"
    if prestress:
        second += ("        _F(MATRICE=CO('rigi_geo'), OPTION='RIGI_GEOM', "
                   "SIEF_ELGA=sig),\n")
    if rotation:
        second += "        _F(MATRICE=CO('rigi_rot'), OPTION='RIGI_ROTA'),\n"
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}    CHARGE=({charge},),\n"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('{rigi}'), OPTION='RIGI_MECA'),\n"
        "{second}"
        "    ),\n"
        ")\n").format(cara=cara_ref, charge=", ".join(charge_names),
                      second=second,
                      rigi="rigi_ela" if prestress else "rigidite")
    if prestress:
        terms = ["rigi_ela", "rigi_geo"] + (["rigi_rot"] if rotation else [])
        assemblage_block += (
            "# Prestressed stiffness (stress stiffening)\n"
            "rigidite = COMB_MATR_ASSE(COMB_R=(\n{0}))\n").format("".join(
                "    _F(MATR_ASSE={0}, COEF_R=1.0),\n".format(m)
                for m in terms))

    interfaces = ["        _F(NOM='DROITE', TYPE='CRAIGB', "
                  "GROUP_NO='{0}'),".format(GROUP_RIGHT),
                  "        _F(NOM='GAUCHE', TYPE='CRAIGB', "
                  "GROUP_NO='{0}'),".format(GROUP_LEFT)]
    if axis_nodes:
        interfaces.append("        _F(NOM='AXE', TYPE='CRAIGB', "
                          "GROUP_NO='{0}'),".format(GROUP_AXIS))
    base_block = "\n".join([
        "# Sector modes with fixed cut faces (basis for the cyclic",
        "# substructuring)",
        "modes = CALC_MODES(",
        "    TYPE_RESU='DYNAMIQUE',",
        "    MATR_RIGI=rigidite,",
        "    MATR_MASS=masse,",
        "    OPTION='PLUS_PETITE',",
        "    CALC_FREQ=_F(NMAX_FREQ={0}),".format(nb),
        "    CHAM_MATER=fieldmat,",
    ] + (["    CARA_ELEM=cara,"] if cara_ref else []) + [
        "    VERI_MODE=_F(SEUIL={0}, STOP_ERREUR='NON'),".format(
            "%.10g" % float(analysis.get("modal_tolerance", 1.0e-6))),
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(
            int(analysis.get("solver_nprec", 8))),
        ")",
        "lint = DEFI_INTERF_DYNA(",
        "    NUME_DDL=numedd,",
        "    INTERFACE=(",
    ] + interfaces + [
        "    ),",
        ")",
        "# Basis: the sector modes plus the static modes of the cut faces",
        "bamo = DEFI_BASE_MODALE(CLASSIQUE=_F(INTERF_DYNA=lint, "
        "MODE_MECA=modes, NMAX_MODE={0}))".format(nb),
    ]) + "\n"
    diameters = list(range(n_seg // 2 + 1))
    # NB_DIAM 0 .. N/2 (rounded down), like Mecway. With an odd N,
    # TOUT_DIAM also computes (N + 1)/2, equal to (N - 1)/2 (seen:
    # Impeller, N = 17, ND 9 = ND 8).
    calcul = ["NB_DIAM={0}".format(tuple(diameters) if len(diameters) > 1
                                   else "({0},)".format(diameters[0])),
              "NMAX_FREQ={0}".format(n)]
    if shift > 0.0:
        calcul += ["OPTION='CENTRE'", "FREQ={0!r}".format(shift)]
        log("INFO: Cyclic symmetry: per nodal diameter the {0} modes "
            "closest to {1} Hz (OPTION 'CENTRE').".format(n, shift))
    elif shift < 0.0:
        log("INFO: Cyclic symmetry: a negative shift frequency is not "
            "needed (the sector with fixed cut faces has no rigid body "
            "modes); the lowest modes.")
    scripts = os.path.dirname(os.path.abspath(__file__))
    full_wheel = bool(analysis.get("cyclic_full_wheel", True))
    liml = model_data.get("liml_path", "")
    wheel_lines = []
    wheel_args = ""
    if full_wheel:
        # The whole wheel like Mecway (S10i): skeleton with all N sectors
        # (DEFI_SQUELETTE CYCLIQUE, SECTEUR TOUT='OUI') and the modes on it
        # (REST_SOUS_STRUC SQUELETTE: sector j with the phase of the ND;
        # syntax test cases sdlv134a, sdls04a, sdls01c, 17.4). If it
        # fails, only the sector goes to Mecway (aster_cyclic).
        wheel_lines = [
            "# The whole wheel (setting cyclic_full_wheel): skeleton with the N",
            "# sectors and the modes on it; otherwise only the sector.",
            "try:",
            "    squel = DEFI_SQUELETTE(CYCLIQUE=_F(MODE_CYCL=modcyc),",
            "                           SECTEUR=_F(TOUT='OUI'))",
            "    modwiel = REST_SOUS_STRUC(RESU_GENE=modcyc, SQUELETTE=squel,",
            "                              NOM_CHAM='DEPL')",
            "except Exception as exc:",
            # Message in the language of the bridge (without an
            # apostrophe: it is between '...').
            "    print('{0}: %r' % (exc,))".format(tr(
                "aster_cyclic: WAARSCHUWING: skelet van het hele wiel niet "
                "gemaakt",
                "aster_cyclic: WARNING: skeleton of the whole wheel not "
                "built")),
            "    squel = modwiel = None",
        ]
        wheel_args = ", wheel=modwiel, skeleton=squel, liml={0}".format(
            b2a._py_str(liml))
        log("INFO: Cyclic symmetry: the modes go to Mecway on the whole "
            "wheel ({0} sectors, like Mecway; setting "
            "cyclic_full_wheel).".format(n_seg))
    cycl_block = "\n".join([
        "modcyc = MODE_ITER_CYCL(",
        "    BASE_MODALE=bamo,",
        "    NB_MODE={0},".format(nb),
        "    NB_SECTEUR={0},".format(n_seg),
        "    LIAISON=_F(DROITE='DROITE', GAUCHE='GAUCHE'{0}),".format(
            ", AXE='AXE'" if axis_nodes else ""),
        "    CALCUL=_F({0}),".format(", ".join(calcul)),
        ")",
        "# Modes on sector 1 (field DEPL per mode)",
        "modsec = REST_SOUS_STRUC(RESU_GENE=modcyc, SECTEUR=1, NOM_CHAM='DEPL')",
    ] + wheel_lines + [
        "import sys",
        "sys.path.insert(0, {0})".format(b2a._py_str(scripts)),
        "import aster_cyclic",
        "res = aster_cyclic.collect(modsec, mesh, numedd, {0}, {1}, {2!r}, "
        "axis='{3}', "
        "angle={4!r}{5})".format(n_seg, n, diameters, axis_name,
                                 ROTATION.get(axis_name, 0.0), wheel_args),
    ]) + "\n"
    export_block = b2a._custom_code(model_data, "post") + (
        "# Results in Mecway's own format (bridge: result_route='liml')@N"
        "import aster_results_export@N"
        "aster_results_export.export_results(@N"
        "    res, {fragment}, {liml},@N"
        "    fields=['displacements'], precision='double',@N"
        "    cyclic={cyclic})@N"
    ).replace("@N", chr(10)).format(
        fragment=b2a._py_str(b2a.results_file(work_dir)),
        liml=b2a._py_str(liml),
        cyclic="{{'axis': {0}, 'segments': {1}}}".format(axis, n_seg))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL',)))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"
    log("INFO: MODE_ITER_CYCL: {0} modes per nodal diameter (ND 0 .. {1}), "
        "{2} sector modes in the basis (cyclic_base_modes){3}.".format(
            n, diameters[-1], nb, ", prestressed" if prestress else ""))

    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = b2a._read_template(TEMPLATE)
        b2a._write_comm(comm_path, template.format(
            defigroup_block=b2a._build_defigroup_block(model_data),
            rotate_block=rotate_block,
            model_block=b2a._build_model_block(model_data),
            cara_elem_block=b2a._build_cara_elem_block(model_data),
            materials_block=b2a._build_materials_block(model_data, analysis),
            fieldmat_block=b2a._build_fieldmat_block(model_data),
            loads_block=loads_block,
            cyclic_loads_block=cyclic_loads_block,
            static_block=static_block,
            assemblage_block=assemblage_block,
            base_block=base_block,
            cycl_block=cycl_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        export_content = (
            "P actions make_etude\n"
            "P time_limit {time_limit}\n"
            "P memory_limit {memory_limit}\n"
            "P mpi_nbcpu 1\n"
            "P ncpus {ncpus}\n"
            "P no-mpi true\n"
            "F comm {comm} D 1\n"
            "F mail {msh} D 20\n"
            "F mess {mess} R 6"
        ).format(
            time_limit=analysis.get("time_limit", 900),
            memory_limit=analysis.get("memory_limit", 2048),
            ncpus=CONFIG_BRIDGE["ncpus"],
            comm=comm_path, msh=msh_path,
            mess=os.path.join(work_dir, run_name(".mess")),
        ) + b2a._export_result_lines(work_dir, resu_name)
        with open(export_path, "w") as f:
            f.write(export_content)
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren solver-bestanden mislukt: {0}",
               "ERROR: Generating solver files failed: {0}").format(str(e)))
    return None
