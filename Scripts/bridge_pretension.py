# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_pretension.py
# Responsibility: Mecway's *Pre-tension section* (bolt pretension, manual
# v34 par. 9.11; XML in bridge_bcs.PretensionSectionBC) as a cut through
# the mesh with LIAISON_DDL, called by bridge_mesh.write_mesh.
#
# What Mecway does (manual v34 par. 9.11, and the CCX deck of
# Samples/BoltedJoint.liml read during a headless Mecway 34 solve, 28 Oct
# 2026):
#   - the selected exterior faces define the prism: the axis is the median
#     of the cross products of the face normals (pairs of faces, at most
#     1000 faces), the axial extent is that of the selected faces, the
#     prism holds the volume elements within that extent that are
#     connected to the selected faces or to each other;
#   - Mecway finds a section through the prism, inserts a thin layer of
#     elements there and writes *PRE-TENSION SECTION (surface, reference
#     node, axis); the force is *CLOAD on DOF 1 of the reference node, the
#     length adjustment *BOUNDARY on it (BoltedJoint: the section is the
#     element boundary between the two selected elements, in the middle of
#     the extent);
#   - CCX (pretensionsections.f, ccx 2.23 source shipped with Mecway)
#     duplicates every node of the surface and writes per node pair two
#     MPCs u_new . t = u_old . t (t perpendicular to the axis) and one
#     u_new . n - u_old . n + d = 0 with d the DOF 1 of the reference node.
#
# Translation (equivalent, without the thin layer):
#   - side of every prism element = its centroid below or above the middle
#     of the axial extent (s_cut); the cut nodes are the nodes shared by an
#     element below and an element above. Every element below gets a copy
#     of those nodes (new node numbers after the Mecway nodes, as for
#     flexible joints), also its boundary cells (faces of selections); the
#     results in Mecway are those of the side above (the Mecway node);
#   - per node pair: DX, DY and DZ of the original minus those of the copy
#     plus n_i * DX(ref) = 0 (LIAISON_DDL, U4.44.01), i.e. u_above -
#     u_below = -delta * n, delta = shortening = DX of the reference node;
#     that holds the tangential components equal (the two CCX MPCs) and
#     gives the normal gap delta (the third);
#   - reference node at the centroid of the cut nodes, POI1 DIS_T with
#     stiffness 0 (group PRET_GROUP), DY = DZ = 0;
#   - load: FORCE_NODALE FX = F (force; the work conjugate of the
#     shortening is the axial force, tension positive like Mecway) or
#     DDL_IMPO DX = delta (adjustment) on the reference node; the BC of the
#     .liml is pointed at that node (group BRPT<k>), so time histories and
#     ramps follow the same path as an ordinary force or displacement.
# Sources: LIAISON_DDL with NOEUD/DDL/COEF_MULT/COEF_IMPO (catalogue
# Cata/Commands/affe_char_meca.py, v17.4; U4.44.01); the same relative
# displacement across doubled nodes of a bolt is the tightening of the
# official test case ssnv106a (LIAISON_GROUP DY with COEF_IMPO = FSER(t),
# DX and DZ tied); the reference node with a force is the CCX formulation
# above. Verification PT-01 .. PT-05 (hand calculation and Mecway 34 with
# CCX, headless).
#
# Compatible with IronPython 2.7.9.

import math
from collections import OrderedDict

from bridge_utils import log, tr, get_active_analysis

# POI1 cells (DIS_T, stiffness 0) on the reference nodes
PRET_GROUP = "BRPRET"
# Analyses in which the section is translated (Mecway also allows dynamic
# response; NOT translated by the bridge, KNOWN_BUGS 122)
_SOLVERS = ("MECA_STATIQUE", "STAT_NON_LINE")
# Mecway uses at most 1000 faces for the axis (manual v34 par. 9.11)
_MAX_FACES = 1000
# Pairs of faces closer to parallel than this (|n1 x n2|) give no axis
_MIN_SIN = 0.05


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    if n <= 0.0:
        return None
    return (a[0] / n, a[1] / n, a[2] / n)


def _newell(points):
    """Area vector (normal x area) of a polygon (Newell)."""
    nx = ny = nz = 0.0
    for i in range(len(points)):
        p, q = points[i], points[(i + 1) % len(points)]
        nx += (p[1] - q[1]) * (p[2] + q[2])
        ny += (p[2] - q[2]) * (p[0] + q[0])
        nz += (p[0] - q[0]) * (p[1] + q[1])
    return (0.5 * nx, 0.5 * ny, 0.5 * nz)


def _median(values):
    v = sorted(values)
    n = len(v)
    if n % 2:
        return v[n // 2]
    return 0.5 * (v[n // 2 - 1] + v[n // 2])


def prism_axis(normals):
    """
    Axis of the prism from the normals of the selected faces, like Mecway
    (manual v34 par. 9.11): the cross product of every pair of faces
    (at most _MAX_FACES faces), oriented alike, and their median per
    component. The orientation reference is the dominant direction of all
    cross products (power iteration on sum c c^T), so that a few pairs
    with an end face do not decide the sign. None if all faces are parallel.
    """
    normals = normals[:_MAX_FACES]
    crosses = []
    for i in range(len(normals)):
        for j in range(i + 1, len(normals)):
            c = _cross(normals[i], normals[j])
            s = math.sqrt(_dot(c, c))
            if s >= _MIN_SIN:
                crosses.append((c[0] / s, c[1] / s, c[2] / s))
    if not crosses:
        return None
    m = [[sum(c[a] * c[b] for c in crosses) for b in range(3)]
         for a in range(3)]
    ref = max(crosses, key=lambda c: abs(c[0]) + abs(c[1]) + abs(c[2]))
    for _ in range(50):
        v = tuple(sum(m[a][b] * ref[b] for b in range(3)) for a in range(3))
        v = _unit(v)
        if v is None:
            break
        ref = v
    oriented = [c if _dot(c, ref) >= 0.0 else (-c[0], -c[1], -c[2])
                for c in crosses]
    axis = _unit(tuple(_median([c[k] for c in oriented]) for k in range(3)))
    if axis is None:
        return None
    # a canonical sign: the largest component positive (the side that
    # keeps the Mecway nodes then does not depend on the face order)
    big = max(range(3), key=lambda k: abs(axis[k]))
    if axis[big] < 0.0:
        axis = (-axis[0], -axis[1], -axis[2])
    return tuple(c + 0.0 for c in axis)     # no -0.0 in the log


def analysis_supported():
    """True in linear and nonlinear static (_SOLVERS)."""
    try:
        cmd = get_active_analysis().get("solver_command")
    except (KeyError, TypeError, AttributeError):
        return False
    return cmd in _SOLVERS


def _reject(model_data, bc, why):
    bc["skip"] = True
    model_data.setdefault("skipped_loads", []).append(
        tr("pre-tension section op '{0}'",
           "pre-tension section on '{0}'").format(bc["selection"]))
    log(tr("ERROR: Pre-tension section op '{0}': {1}. NIET meegenomen.",
           "ERROR: Pre-tension section on '{0}': {1}. NOT included.").format(
        bc["selection"], why))


_SUPPORT_BCS = frozenset(["fixed", "pinnedsupport", "displacement",
                          "frictionless", "symmetry", "compressiononly"])


def _support_cells(model_data, conn, skin_by_key, faces_of):
    """Names of the boundary cells that belong only to face selections
    with supports (_SUPPORT_BCS), not to a load, contact or bonded
    contact."""
    import bridge_mesh
    uses = {}
    for bc in model_data.get("bcs", []):
        if bc.get("selection") and bc.get("type") != "pretensionsection":
            uses.setdefault(bc["selection"], set()).add(
                "support" if bc.get("type") in _SUPPORT_BCS else "other")
    for c in (model_data.get("contacts", []) +
              model_data.get("bonded", [])):
        for key in ("master", "slave"):
            if c.get(key):
                uses.setdefault(c[key], set()).add("other")
    cells = {}
    for sel, faces in model_data.get("face_selection_faces", {}).items():
        kind = "support" if uses.get(sel) == set(["support"]) else "other"
        for eid, fid in faces:
            if eid not in conn:
                continue
            atype, cn = conn[eid]
            fn = faces_of(eid, fid)
            if not fn:
                continue
            try:
                stype, snodes = bridge_mesh._skin_element(atype, cn, fn)
            except (KeyError, IndexError):
                continue
            name = skin_by_key.get(frozenset(snodes))
            if name is not None:
                cells.setdefault(name, set()).add(kind)
    return set(n for n, kinds in cells.items() if kinds == set(["support"]))


def apply(model_data, nodes, conn, by_type, cell_refs, skin_by_key,
          faces_of, next_nid):
    """
    Cut the mesh for every pre-tension section in model_data["bcs"].

    nodes      : {nid: (x, y, z)} Mecway nodes
    conn       : {eid: (aster_type, [nid ...])} (Mecway nodes; unchanged)
    by_type    : {aster_type: [(cell name, [nid ...])]}; the cells of the
                 elements below the cut and their boundary cells get the
                 copies of the cut nodes
    cell_refs  : {eid: [(aster_type, index in by_type)]}
    skin_by_key: {frozenset(nodes): boundary cell name}
    faces_of   : function (eid, faceid) -> face nodes
    next_nid   : first free node number

    Returns (new nodes {nid: xyz}, reference nodes [nid], node groups
    {name: ["N<nid>"]}); empty without a translatable section. Sets
    model_data["pretension_sections"] (one dict per section, for the log,
    LINE_QUAD and the documentation) and adds the relations to
    model_data["constraint_equations"].
    """
    import bridge_mesh
    new_nodes = OrderedDict()
    refs = []
    groups = OrderedDict()
    bcs = [bc for bc in model_data.get("bcs", [])
           if bc.get("type") == "pretensionsection" and not bc.get("skip")]
    if not bcs:
        return new_nodes, refs, groups
    supported = analysis_supported()
    shapes = model_data.get("elem_shapes", {})
    faces_by_sel = model_data.get("face_selection_faces", {})
    eqs = model_data.setdefault("constraint_equations", [])
    info_all = model_data.setdefault("pretension_sections", [])
    # elements per node (all cells, for the checks around the cut)
    at_node = {}
    for eid, (atype, cn) in conn.items():
        for n in cn:
            at_node.setdefault(n, set()).add(eid)
    solid = set(eid for eid in conn
                if shapes.get(eid) in bridge_mesh._SOLID_SHAPES)
    # boundary cell name -> (type, index in by_type)
    cell_index = {}
    for atype, items in by_type.items():
        for idx, (name, _cn) in enumerate(items):
            cell_index[name] = (atype, idx)
    support_cells = _support_cells(model_data, conn, skin_by_key, faces_of)
    # nodes already copied by an earlier section: a second cut through
    # the same nodes is not supported
    used = set()
    for bc in bcs:
        sel = bc["selection"]
        if not supported:
            _reject(model_data, bc, tr(
                "alleen in lineair en niet-lineair statisch (Mecway staat "
                "ook dynamica toe; KNOWN_BUGS 122)",
                "only in linear and nonlinear static analyses (Mecway also "
                "allows dynamic response; KNOWN_BUGS 122)"))
            continue
        faces = faces_by_sel.get(sel) or []
        if not faces:
            _reject(model_data, bc, tr("lege of onbekende vlakselectie",
                                       "empty or unknown face selection"))
            continue
        bad = sorted(set(eid for eid, fid in faces if eid not in solid))
        if bad:
            _reject(model_data, bc, tr(
                "alleen vlakken van volume-elementen (CCX-variant); de "
                "variant met een veerelement (interne solver) wordt niet "
                "vertaald (elementen {0})",
                "only faces of solid elements (CCX variant); the spring "
                "element variant (internal solver) is not translated "
                "(elements {0})").format(
                    ", ".join(str(e) for e in bad[:10])))
            continue
        # --- axis and axial extent ---
        normals = []
        face_nodes = set()
        for eid, fid in faces:
            atype, cn = conn[eid]
            fn = faces_of(eid, fid)
            if not fn:
                continue
            stype, snodes = bridge_mesh._skin_element(atype, cn, fn)
            nc = 3 if stype.startswith("TRIA") else 4
            nrm = _unit(_newell([nodes[n] for n in snodes[:nc]]))
            if nrm is not None:
                normals.append(nrm)
            face_nodes.update(snodes)
        axis = prism_axis(normals)
        if axis is None:
            _reject(model_data, bc, tr(
                "geen as: kies minstens twee vlakken onder verschillende "
                "hoeken op de buitenkant van het prisma (manual par. 9.11)",
                "no axis: select at least two faces at different angles "
                "on the outside of the prism (manual par. 9.11)"))
            continue
        s_of = dict((n, _dot(nodes[n], axis)) for n in face_nodes)
        s_min, s_max = min(s_of.values()), max(s_of.values())
        length = s_max - s_min
        if length <= 0.0:
            _reject(model_data, bc, tr(
                "de vlakken hebben geen lengte langs de as",
                "the faces have no length along the axis"))
            continue
        tol = 1.0e-6 * length

        def inside(eid):
            return all(s_min - tol <= _dot(nodes[n], axis) <= s_max + tol
                       for n in conn[eid][1])

        # --- prism: connected solid elements within the extent ---
        prism = set()
        todo = [eid for eid, fid in faces if inside(eid)]
        while todo:
            eid = todo.pop()
            if eid in prism:
                continue
            prism.add(eid)
            for n in conn[eid][1]:
                for other in at_node.get(n, ()):
                    if (other not in prism and other in solid and
                            inside(other)):
                        todo.append(other)
        if not prism:
            _reject(model_data, bc, tr(
                "geen volume-elementen binnen de axiale lengte van de "
                "vlakken",
                "no solid elements within the axial extent of the faces"))
            continue
        # --- section: centroid below / above the middle ---
        s_cut = 0.5 * (s_min + s_max)
        below, above = set(), set()
        for eid in prism:
            atype, cn = conn[eid]
            corners = cn[:bridge_mesh._N_CORNERS[atype]]
            s_c = sum(_dot(nodes[n], axis) for n in corners) / len(corners)
            (below if s_c < s_cut - tol else above).add(eid)
        below_nodes = set(n for e in below for n in conn[e][1])
        above_nodes = set(n for e in above for n in conn[e][1])
        cut = below_nodes & above_nodes
        if not below or not above or not cut:
            _reject(model_data, bc, tr(
                "geen doorsnede door het prisma gevonden (de elementen liggen "
                "niet aan weerszijden van het midden van de axiale lengte)",
                "no section through the prism found (the elements do not "
                "lie on both sides of the middle of the axial extent)"))
            continue
        outside = sorted(set(e for n in cut for e in at_node.get(n, ())
                             if e not in prism))
        bypass = sorted(e for e in conn if e not in prism and
                        set(conn[e][1]) & (below_nodes - cut) and
                        set(conn[e][1]) & (above_nodes - cut))
        if outside or bypass:
            ids = outside or bypass
            _reject(model_data, bc, tr(
                "de doorsnede raakt elementen buiten het prisma ({0}); alle "
                "elementen rond de doorsnede moeten binnen de axiale lengte "
                "van de geselecteerde vlakken liggen",
                "the section touches elements outside the prism ({0}); all "
                "elements around the section must lie within the axial "
                "extent of the selected faces").format(
                    ", ".join(str(e) for e in ids[:10]) +
                    (" ..." if len(ids) > 10 else "")))
            continue
        if cut & used:
            _reject(model_data, bc, tr(
                "de doorsnede gaat door knopen van een andere pre-tension "
                "section",
                "the section passes through nodes of another pre-tension "
                "section"))
            continue
        used |= cut
        # --- copies of the cut nodes for the elements below; the
        # elements above keep the Mecway nodes (as in the CCX deck of
        # BoltedJoint: the upper element keeps them, axis +Y) ---
        moved = below
        dup = OrderedDict()
        for n in sorted(cut):
            dup[n] = next_nid
            new_nodes[next_nid] = nodes[n]
            next_nid += 1
        for eid in moved:
            for atype, idx in cell_refs.get(eid, []):
                name, cell = by_type[atype][idx]
                by_type[atype][idx] = (name, [dup.get(n, n) for n in cell])
        # boundary cells (faces of selections) of the moved elements, except
        # those only used by supports: a support on both the node and its
        # copy repeats the tie (FACTOR_11, PT-01: frictionless on a plane
        # through the axis); on the Mecway node alone it holds the copy too
        n_skin = 0
        for eid in moved:
            atype, cn = conn[eid]
            if not set(cn) & cut:
                continue
            for fid in range(1, 7):
                fn = bridge_mesh._face_from_table(atype, cn, fid)
                if not fn or not set(fn) & cut:
                    continue
                stype, snodes = bridge_mesh._skin_element(atype, cn, fn)
                name = skin_by_key.get(frozenset(snodes))
                if name is None or name not in cell_index or \
                        name in support_cells:
                    continue
                st, idx = cell_index[name]
                old = by_type[st][idx][1]
                if any(n in dup for n in old):
                    by_type[st][idx] = (name, [dup.get(n, n) for n in old])
                    n_skin += 1
        # --- section area (faces shared by both sides), for the log ---
        below_faces = set()
        for eid in below:
            atype, cn = conn[eid]
            for fid in range(1, 7):
                fn = bridge_mesh._face_from_table(atype, cn, fid)
                if fn and set(fn) <= cut:
                    below_faces.add(frozenset(fn))
        area = 0.0
        for eid in above:
            atype, cn = conn[eid]
            for fid in range(1, 7):
                fn = bridge_mesh._face_from_table(atype, cn, fid)
                if not fn or frozenset(fn) not in below_faces:
                    continue
                # quadratic faces with their mid-side nodes (curved),
                # projected on the section plane (zig-zag cut in tets)
                stype, snodes = bridge_mesh._skin_element(atype, cn, fn)
                nrm = _unit(_newell([nodes[n] for n in fn]))
                if nrm is not None:
                    area += abs(_dot(nrm, axis)) * sum(
                        bridge_mesh._face_integrals(
                            stype, [nodes[n] for n in snodes])[0])
        # --- reference node and relations ---
        ref = next_nid
        next_nid += 1
        pts = [nodes[n] for n in cut]
        new_nodes[ref] = tuple(sum(p[k] for p in pts) / len(pts)
                               for k in range(3))
        refs.append(ref)
        for n, d in dup.items():
            for k, comp in enumerate(("DX", "DY", "DZ")):
                # u_above - u_below + delta * n = 0 (the original node n is
                # above, its copy d below)
                terms = [(n, comp, 1.0), (d, comp, -1.0)]
                if abs(axis[k]) > 1.0e-14:
                    terms.append((ref, "DX", axis[k]))
                eqs.append({"terms": terms, "constant": 0.0,
                            "source": "pretension"})
        for comp in ("DY", "DZ"):
            eqs.append({"terms": [(ref, comp, 1.0)], "constant": 0.0,
                        "source": "pretension"})
        group = "BRPT{0}".format(len(info_all) + 1)
        groups[group] = ["N{0}".format(ref)]
        mecway_sel = sel
        bc["selection"] = group
        bc["aster_target"] = "GROUP_NO"
        mode = bc["params"].get("mode", "force")
        info = {"selection": mecway_sel, "group": group, "ref": ref,
                "axis": axis, "s_cut": s_cut, "area": area,
                "below": len(below), "above": len(above),
                "pairs": len(dup), "mode": mode}
        info_all.append(info)
        value = bc["params"].get("value", 0.0)
        last = value[-1][1] if isinstance(value, list) else value
        extra = ""
        if mode == "force" and area > 0.0:
            # %-formatting: '{0:.6g}' gave a decimal comma in IronPython
            # (bridge_mesh, curved line3 warning)
            extra = ", nominal stress F/A = %.6g Pa" % (last / area)
        log("INFO: Pre-tension section '{0}': axis ({1}), extent {2} .. "
            "{3} m, section at {4} m, area {5} m2{6}; prism {7} "
            "element(s) ({8} below, {9} above), {10} node pair(s), {11} "
            "boundary cell(s) moved; reference node N{12} (DX = shortening), "
            "{13} {14}.".format(
                mecway_sel, ", ".join("%.6g" % c for c in axis),
                "%.6g" % s_min, "%.6g" % s_max, "%.6g" % s_cut, "%.6g" % area,
                extra, len(prism), len(below), len(above), len(dup), n_skin,
                ref, "force FX =" if mode == "force" else
                "length adjustment DX =", value))
    return new_nodes, refs, groups
