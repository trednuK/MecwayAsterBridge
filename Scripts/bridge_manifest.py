# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_manifest.py
# Keep the Code-Aster base of a run, for a short POURSUITE afterwards. Used
# by MecwayFreebody: it computes the forces on the cuts of a selection that
# is made after the run.
#
# With the setting "keep_base" a linear or nonlinear static run gets:
#   <model>_<run_id>_base/           the base (R base ... R 0 in the .export)
#   <model>_<run_id>_manifest.json   what a follow-up run needs to know
# note_mesh() keeps, while bridge_mesh.write_mesh runs, what only the mesh
# writer knows (beam axes, offsets, connected nodes; only with the setting).
# prepare_base() adds the base to the .export before the run. finish_run()
# writes the manifest after the run, and only for a run that ended well: a
# manifest means the base is usable. After a failed run the base folder goes.
# Only then the newest "keep_base_runs" usable bases per model stay; older
# ones are removed, so a failed run never costs the last good base.
#
# Manifest (schema 2, UTF-8 JSON, no paths). Schema 2 keeps every key of
# schema 1 with its meaning, except not_shared (a list of kinds in schema 1,
# a dict now); the schema 2 keys are marked (2).
#   schema, run_id, model (file name), configuration, analysis, solver,
#   aster_version, memory_limit, base (folder name),
#   fingerprint  mesh_fingerprint() of the Mecway model
#   deformation  the choice of the run; "PETIT" for MECA_STATIQUE
#   deformation_by_component  {Mecway component: what it really computed
#                with}: the bridge chooses per element set. With PETIT the
#                moments of a cut are summed on the undeformed shape, else on
#                x + u (measured, MecwayFreebody E9). DKT/DST count as PETIT.
#                "MIXED": parts of the component differ (a truss part of a
#                component with beams).
#   concepts     names in the base: result, mesh, model, material, cara
#   cells        the cell names in the order of the mesh file. In the base a
#                cell has no name but a position, also after CREA_MAILLAGE:
#                position i (from 1) is cells[i-1]. Cells of Mecway element
#                eid: M<eid>, a split line3 also H<eid>.
#   skin         {"K12": [[eid, faceid], ...]}: which Mecway faces a skin cell
#                belongs to. The mesh itself has no such link.
#   not_shared   (2) {kind: {"nodes": [nid], "origin": "user"|"bridge",
#                "groups": [[nid], ...]}}: parts where shared nodes do not
#                describe the whole cut; a reader refuses or warns. nodes:
#                the Mecway nodes the kind acts on, sorted (nodes the bridge
#                adds, such as the own node of a flexible joint or the copies
#                of a pre-tension section, are left out). groups: the same
#                nodes per connection (a contact, bonded contact or coupling
#                item, a constraint equation, an offset arm, a discrete
#                element), so that a reader can test one connection at a
#                time (an addition to the contract of MecwayFreebody; nodes
#                is their union). Kinds and origin:
#                  user   (the Mecway item itself connects): contact, bonded,
#                         coupling (RBE2/RBE3: master and slave nodes),
#                         constraint (the user's constraint equations),
#                         discrete (gap and damper elements)
#                  bridge (relations the bridge makes itself to translate a
#                         Mecway feature): line3truss (midside node of a
#                         split line3 truss), flexible_joint, offset (rigid
#                         arms of an element offset), pretension; a
#                         constraint equation of the bridge with another
#                         "source" gets that source as its kind, also bridge
#                A kind is there only if the model has it; none: {}.
#                "contact" (unilateral) is left out of a MECA_STATIQUE run:
#                the bridge skips it there (bridge_to_aster._check_linear).
#   extra_nodes  True if the base has nodes Mecway does not know (LINE_QUAD,
#                QUAD8_9, TRIA6_7 by CREA_MAILLAGE)
#   components   (2) {Mecway component: {"model": MODELISATION as Code-Aster
#                got it (DKT, DST, COQUE_3D, POU_D_E, POU_D_T, POU_D_TG,
#                POU_D_T_GD, BARRE, CABLE, 3D, 3D_SI, DIS_T, ...),
#                "has_warping": True for POU_D_TG, and for beams and trusses
#                "section": {"cara": [...], "vale": [...], "shape": SECTION
#                of AFFE_CARA_ELEM ("GENERALE", "RECTANGLE", "CERCLE"; None
#                for CABLE, which gets AIRE), "mecway_shape": Mecway's section
#                type ("RectBar", "I", "UniformGeneralSection", ...)}}}.
#                A component that mixes beams and trusses has its trusses in
#                "truss_part" ({"model", "has_warping", "section",
#                "elements": [eid]}; an addition to the contract of
#                MecwayFreebody); those cells have no beam_axes entry. CABLE:
#                only AIRE, N_INIT is left out.
#   coef_rigi_drz (2) COEF_RIGI_DRZ of the shells; null: the bridge does not
#                set it, so Code-Aster's default holds
#   beam_axes    (2) {cell name: [[x], [y], [z]]}: the local axes of every
#                beam cell (MODELISATION POU_*) as given to Code-Aster: x
#                from node 1 to node 2 of the (half) cell, y its VECT_Y
#                (bridge_mesh._mecway_v_axis) made perpendicular to x as
#                Code-Aster does, z = x cross y. A split line3 has M<eid> (node
#                1 to the midside node) and H<eid> (midside node to node 2).
#                Trusses and cables have none.
#   excentrement (2) {eid: e}: EXCENTREMENT of DKT/DST elements with an
#                element offset (bridge_offset; the midsurface at +e along
#                the cell normal). An offset that the bridge makes with own
#                nodes and rigid arms is not here but in not_shared "offset".
#
# Compatible with IronPython 2.7.9 and Python 3 (offline test:
# python tests/test_bridge_manifest.py).

import hashlib
import io
import json
import math
import os
import re
import time

import bridge_version
from bridge_utils import CONFIG_BRIDGE, exe_aster_path, log, run_name, tr

SCHEMA = 2
# The truss part of a component with beams: bridge_from_liml._split_trusses
_TRUSS_PART = re.compile(r"^(.+)_TRUSS\d*$")
# A base without manifest may belong to a run of another Mecway; this old it
# does not (seconds)
ORPHAN_AGE = 6 * 3600
BASE_SUFFIX = "_base"
MANIFEST_SUFFIX = "_manifest.json"
# The results MecwayFreebody can use: a static result per step
BASE_SOLVERS = ("MECA_STATIQUE", "STAT_NON_LINE")


def _nano(value):
    """Coordinate in nm as an integer. Not through a format: "g" follows the
    Windows locale in IronPython, and round() differs between 2.7 and 3."""
    return int(math.floor(float(value) * 1e9 + 0.5))


def mesh_fingerprint(nodes, element_ids):
    """
    Hash of the Mecway model: node numbers, coordinates (to 1 nm) and element
    numbers. nodes: {nid: (x, y, z)} in metres. A follow-up run compares it
    with the open model, so that results of another mesh are never mixed.
    A reader uses this same function; here the input is the .liml of the run
    in the solved configuration.
    """
    h = hashlib.sha256()
    for nid in sorted(nodes):
        xyz = nodes[nid]
        h.update("{0} {1} {2} {3}\n".format(
            int(nid), _nano(xyz[0]), _nano(xyz[1]), _nano(xyz[2])).encode("ascii"))
    for eid in sorted(element_ids):
        h.update("E{0}\n".format(int(eid)).encode("ascii"))
    return h.hexdigest()


# not_shared: (kind, model_data key, origin); see the header
_KINDS = (("offset", "offset_links", "bridge"),
          ("discrete", "discrete_sections", "user"),
          ("contact", "contacts", "user"),
          ("bonded", "bonded", "user"),
          ("coupling", "couplings", "user"),
          ("constraint", "constraint_equations", "user"),
          ("pretension", "pretension_sections", "bridge"),
          ("flexible_joint", "flexible_joints", "bridge"))
# Kind of the constraint equations the bridge makes itself, by their
# "source" (bridge_mesh, bridge_pretension); the user's have no source
_CE_KINDS = {"line3truss": "line3truss", "flexiblejoint": "flexible_joint",
             "pretension": "pretension"}


def _nid(value):
    s = str(value)
    return int(s[1:]) if s.startswith("N") else int(s)


def _unit(a):
    n = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return [a[0] / n, a[1] / n, a[2] / n]


def _beam_axes(nodes, conn, beam_groups, beam_vect_y, split_line3):
    """{cell name: [x, y, z]} of the beam cells; see the header. beam_groups
    {group: [cell name]} with the VECT_Y beam_vect_y[group]
    (bridge_mesh.write_mesh, step 4)."""
    out = {}
    for group, members in beam_groups.items():
        v = beam_vect_y[group]
        for name in members:
            eid = int(name[1:])
            cn = conn[eid][1]
            if eid in split_line3:
                a, b = (cn[0], cn[2]) if name[0] == "M" else (cn[2], cn[1])
            else:
                a, b = cn[0], cn[1]
            chord = [nodes[b][i] - nodes[a][i] for i in range(3)]
            if not any(chord):
                # A cell of length 0 has no axes (Code-Aster would stop on
                # it); the rest of the manifest stays usable
                log(tr("WARNING: Balkcel {0} heeft lengte 0: geen assen in "
                       "het manifest.",
                       "WARNING: Beam cell {0} has length 0: no axes in the "
                       "manifest.").format(name))
                continue
            x = _unit(chord)
            # Code-Aster keeps the part of VECT_Y perpendicular to x
            # (U4.42.01 AFFE_CARA_ELEM ORIENTATION VECT_Y); V of
            # _mecway_v_axis already is, up to rounding
            d = v[0] * x[0] + v[1] * x[1] + v[2] * x[2]
            y = _unit([v[i] - d * x[i] for i in range(3)])
            z = [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2],
                 x[0] * y[1] - x[1] * y[0]]
            out[name] = [x, y, z]
    return out


def _excentrement(offset_plan):
    """{eid as text: e} of the DKT/DST cells with EXCENTREMENT
    (bridge_offset.prepare: plan["exc"] = {(elset, e): [eid]})."""
    out = {}
    for (_elset, e), eids in ((offset_plan or {}).get("exc") or {}).items():
        for eid in eids:
            out[str(eid)] = float(e)
    return out


def _not_shared(model_data, nodes, conn, elements, group_face_list):
    """{kind: {"nodes", "origin", "groups"}}; see the header. Before the
    renames of bridge_mesh.write_mesh (step 5): selections by their Mecway
    names. group_face_list: {face selection: [{"nodes", ...}]}
    (write_mesh)."""
    node_groups = model_data.get("node_groups", {})
    elem_sel = model_data.get("element_selections", {})

    def sel_nodes(name):
        if name in group_face_list:
            return set(n for f in group_face_list[name] for n in f["nodes"])
        if name in node_groups:
            return set(_nid(i) for i in node_groups[name])
        if name in elem_sel:
            return set(n for e in elem_sel[name] if e in conn
                       for n in conn[e][1])
        return set()

    found = {}

    def add(kind, origin, ids=None):
        """One connection of a kind (ids None: only note the kind)."""
        entry = found.setdefault(kind, {"nodes": set(), "origin": origin,
                                        "groups": [], "seen": set()})
        if ids is None:
            return
        group = sorted(set(n for n in ids if n in nodes))
        entry["nodes"].update(group)
        if group and tuple(group) not in entry["seen"]:
            entry["seen"].add(tuple(group))
            entry["groups"].append(group)

    for kind, key, origin in _KINDS:
        # the user's constraint equations only (below)
        if kind != "constraint" and model_data.get(key):
            add(kind, origin)
    for link in model_data.get("offset_links") or []:
        add("offset", "bridge", [link["orig"]])
    discrete = model_data.get("discrete_sections") or {}
    for eid, _shape, enodes, elset in elements:
        if elset in discrete:
            add("discrete", "user", enodes)
    for key, kind in (("contacts", "contact"), ("bonded", "bonded")):
        for c in model_data.get(key) or []:
            add(kind, "user", sel_nodes(c.get("master")) |
                sel_nodes(c.get("slave")))
    for c in model_data.get("couplings") or []:
        add("coupling", "user", sel_nodes(c.get("master_group")) |
            sel_nodes(c.get("slave_group")))
    # Flexible joints: the Mecway nodes of their relations
    # (bridge_mesh._flexible_joints), so a joint end that is not
    # translated adds no node
    for ce in model_data.get("constraint_equations") or []:
        source = ce.get("source")
        if source is None:
            kind, origin = "constraint", "user"
        else:
            kind, origin = _CE_KINDS.get(source, source), "bridge"
        add(kind, origin, [t[0] for t in ce.get("terms", [])])
    empty = sorted(k for k, e in found.items()
                   if e["origin"] == "user" and not e["nodes"])
    if empty:
        log(tr("WARNING: Manifest: {0} zonder knopen (lege selectie?); een "
               "vervolgrun kan die verbinding niet aan een snede toetsen.",
               "WARNING: Manifest: {0} without nodes (empty selection?); a "
               "follow-up run cannot test that connection against a cut.")
            .format(", ".join(empty)))
    return dict((kind, {"nodes": sorted(e["nodes"]), "origin": e["origin"],
                        "groups": e["groups"]})
                for kind, e in found.items())


def note_mesh(model_data, nodes, conn, elements, group_face_list,
              offset_plan, beam_groups, beam_vect_y, split_line3):
    """
    Called by bridge_mesh.write_mesh after the element offset is in the mesh
    and before the renames: model_data["manifest_mesh"] with beam_axes,
    excentrement and not_shared (see the header). Nothing without the
    setting keep_base. A problem here gives a WARNING and no manifest after
    the run (finish_run), never a stopped mesh.
    nodes: the Mecway nodes; conn: {eid: (aster type, [nid])}; elements:
    model_data["mesh_elements"].
    """
    if not CONFIG_BRIDGE.get("keep_base", False):
        return
    try:
        model_data["manifest_mesh"] = {
            "beam_axes": _beam_axes(nodes, conn, beam_groups, beam_vect_y,
                                    split_line3),
            "excentrement": _excentrement(offset_plan),
            "not_shared": _not_shared(model_data, nodes, conn, elements,
                                      group_face_list)}
    except Exception as e:
        model_data["manifest_mesh"] = None
        log(tr("WARNING: Gegevens voor het manifest niet verzameld: {0}",
               "WARNING: Data for the manifest not collected: {0}").format(e))


def _component_names(model_data, elsets):
    """{elset: (Mecway name, Mecway component)}: the truss part of a
    component with beams belongs to that component
    (model_data["truss_parts"] of bridge_from_liml._split_trusses; without
    it, a model_data of before: the name '<name>_TRUSS' if <name> is in
    elsets too)."""
    import bridge_failure
    names = dict((es, bridge_failure.mecway_name(model_data, es))
                 for es in elsets)
    parts = model_data.get("truss_parts")
    out = {}
    if parts is not None:
        owner = dict((part, comp) for comp, ps in parts.items() for part in ps)
        for es, name in names.items():
            out[es] = (name, owner.get(name, name))
        return out
    own = set(names.values())
    for es, name in names.items():
        m = _TRUSS_PART.match(name)
        out[es] = (name, m.group(1) if m and m.group(1) in own else name)
    return out


def _deformation_by_component(model_data):
    """model_data["deformation_by_elset"] with the names Mecway shows."""
    by_elset = model_data.get("deformation_by_elset", {})
    names = _component_names(model_data, list(by_elset))
    found = {}
    for elset, form in by_elset.items():
        name = names[elset][1]
        found[name] = form if found.get(name, form) == form else "MIXED"
    return found


def _section(beam, cable):
    """section of a component as AFFE_CARA_ELEM got it, or None.
    beam: model_data["beam_sections"][elset] (POUTRE, or BARRE with
    "truss"); cable: model_data["cable_sections"][elset] (CABLE, AIRE)."""
    if beam and beam.get("cara") is not None:
        return {"cara": list(beam["cara"]),
                "vale": [float(v) for v in beam["vale"]],
                "shape": beam.get("aster_section"),
                "mecway_shape": beam.get("geom_type")}
    if cable:
        return {"cara": ["AIRE"], "vale": [float(cable["area"])],
                "shape": None, "mecway_shape": cable.get("geom_type")}
    return None


def _components(model_data):
    """{Mecway component: {"model", "has_warping", "section"}}; see the
    header."""
    mods = model_data.get("elset_modelisations", {})
    beams = model_data.get("beam_sections", {})
    cables = model_data.get("cable_sections", {})
    names = _component_names(model_data, list(mods))
    out = {}
    for elset, mod in mods.items():
        entry = {"model": mod, "has_warping": mod == "POU_D_TG"}
        section = _section(beams.get(elset), cables.get(elset))
        if section is not None:
            entry["section"] = section
        name, component = names[elset]
        if name == component:
            out.setdefault(component, {}).update(entry)
        else:
            # mesh_elements keep the Mecway elset name (bridge_mesh renames
            # in group_renames only)
            entry["elements"] = sorted(
                e[0] for e in model_data.get("mesh_elements", [])
                if e[3] == name)
            out.setdefault(component, {})["truss_part"] = entry
    return out


def build_manifest(model_data, kept, run_id, aster_version, memory_limit):
    """The manifest as a dict; see the header of this file. Without the
    data of note_mesh there is no manifest (ValueError)."""
    mesh = model_data.get("manifest_mesh")
    if not mesh:
        raise ValueError("no data of the mesh (bridge_manifest.note_mesh)")
    not_shared = dict(mesh["not_shared"])
    if kept["solver"] == "MECA_STATIQUE":
        # Unilateral contact is not in a linear run
        # (bridge_to_aster._check_linear)
        not_shared.pop("contact", None)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "model": split_run_name(run_name(""))[0],
        "configuration": model_data.get("configuration"),
        "analysis": CONFIG_BRIDGE.get("active_analysis"),
        "solver": kept["solver"],
        "aster_version": aster_version,
        "memory_limit": memory_limit,
        "deformation": kept["deformation"],
        "deformation_by_component": _deformation_by_component(model_data),
        "base": os.path.basename(run_name(BASE_SUFFIX)),
        "fingerprint": mesh_fingerprint(
            model_data.get("mesh_nodes", {}),
            [e[0] for e in model_data.get("mesh_elements", [])]),
        "concepts": {
            "result": "res", "mesh": "mesh", "model": "model",
            "material": "fieldmat",
            "cara": "cara" if kept["has_cara"] else None},
        "cells": list(model_data.get("cell_names", [])),
        "skin": dict((k, [list(p) for p in v])
                     for k, v in model_data.get("skin_parents", {}).items()),
        "not_shared": not_shared,
        "extra_nodes": bool(model_data.get("line_quad") or
                            model_data.get("shell_upgrades")),
        "components": _components(model_data),
        # The bridge never writes COEF_RIGI_DRZ (AFFE_CARA_ELEM COQUE,
        # bridge_to_aster._build_cara_elem_block); a key for when it does
        "coef_rigi_drz": model_data.get("coef_rigi_drz"),
        "beam_axes": mesh["beam_axes"],
        "excentrement": mesh["excentrement"],
    }


def write_manifest(path, manifest):
    """Written through a .tmp file: a follow-up run never reads half a file."""
    tmp = path + ".tmp"
    # Compact: a manifest of 200 000 cells is read in IronPython
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)


def read_memory_limit(export_path):
    """P memory_limit of the .export, in MB; None if it is not there."""
    with io.open(export_path, encoding="utf-8", errors="replace") as f:
        m = re.search(r"^P memory_limit (\d+)", f.read(), re.M)
    return int(m.group(1)) if m else None


def bases_to_remove(names, model_stem, keep):
    """
    Usable base folders of this model beyond the newest keep, oldest first.
    names: the folder listing. Only exact <model_stem>_<yyyymmdd>_<hhmmss>_base
    names with a manifest; run ids sort by time.
    """
    pattern = re.compile("^" + re.escape(model_stem) +
                         r"_\d{8}_\d{6}" + re.escape(BASE_SUFFIX) + "$")
    found = sorted(n for n in names if pattern.match(n) and
                   n[:-len(BASE_SUFFIX)] + MANIFEST_SUFFIX in names)
    keep = max(int(keep), 1)
    return found[:-keep] if len(found) > keep else []


def orphan_bases(names, model_stem, current):
    """Base folders of this model without a manifest, except that of the
    current run. prune_bases also looks at their age."""
    pattern = re.compile("^" + re.escape(model_stem) +
                         r"_\d{8}_\d{6}" + re.escape(BASE_SUFFIX) + "$")
    return [n for n in names if pattern.match(n) and n != current and
            n[:-len(BASE_SUFFIX)] + MANIFEST_SUFFIX not in names]


def _has_subfolder(path):
    return any(os.path.isdir(os.path.join(path, n)) for n in os.listdir(path))


def _remove_folder(path):
    """Remove the files of a base folder and the folder; not recursive, a
    base has no subfolders."""
    for n in os.listdir(path):
        os.remove(os.path.join(path, n))
    os.rmdir(path)


def prune_bases(work_dir, model_stem, keep, current=None):
    """Remove the oldest bases of this model and those left without a
    manifest. Never stops a run."""
    names = os.listdir(work_dir)
    now = time.time()
    orphans = [n for n in orphan_bases(names, model_stem, current)
               if now - os.path.getmtime(os.path.join(work_dir, n)) >
               ORPHAN_AGE]
    for name in bases_to_remove(names, model_stem, keep) + orphans:
        path = os.path.join(work_dir, name)
        try:
            if _has_subfolder(path):
                log(tr("WARNING: {0} bevat een submap en blijft staan.",
                       "WARNING: {0} has a subfolder and stays.").format(path))
                continue
            # The manifest first: a base that is half removed (a file in use)
            # must not look usable
            manifest = path[:-len(BASE_SUFFIX)] + MANIFEST_SUFFIX
            if os.path.exists(manifest):
                os.remove(manifest)
            _remove_folder(path)
            log("INFO: Old Code-Aster base removed: {0}".format(name))
        except (IOError, OSError) as e:
            log(tr("WARNING: Kon {0} niet verwijderen: {1}",
                   "WARNING: Could not delete {0}: {1}").format(path, e))


def split_run_name(name):
    """(<model>, <run_id>) from run_name(""); (name, None) outside a run."""
    m = re.match(r"^(.*)_(\d{8}_\d{6})$", name)
    return (m.group(1), m.group(2)) if m else (name, None)


def prepare_base(export_path, work_dir, model_data, analysis, adaptive,
                 has_cara):
    """
    After the builder: with the setting "keep_base" add the base to the
    .export. Returns True if the run keeps its base. A problem here gives a
    WARNING: the run itself is worth more than the base.
    """
    if not CONFIG_BRIDGE.get("keep_base", False):
        return False
    import bridge_xfem
    solver_cmd = analysis.get("solver_command")
    if (solver_cmd not in BASE_SOLVERS or adaptive or
            bridge_xfem.selection_names(model_data)):
        log(tr("INFO: Base wordt niet bewaard: alleen voor statische runs "
               "zonder adaptieve verfijning of XFEM.",
               "INFO: Base not kept: only for static runs without adaptive "
               "refinement or XFEM."))
        return False
    try:
        base_dir = os.path.join(work_dir, run_name(BASE_SUFFIX))
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        # As the builders write the .export: one encoding in the file
        with open(export_path, "a") as f:
            f.write("\nR base {0} R 0".format(base_dir))
        linear = solver_cmd == "MECA_STATIQUE"
        model_data["kept_base"] = {
            "solver": solver_cmd, "has_cara": has_cara,
            "deformation": ("PETIT" if linear
                            else analysis.get("deformation", "PETIT"))}
        return True
    except Exception as e:
        log(tr("WARNING: Base bewaren voorbereiden mislukt: {0}",
               "WARNING: Preparing to keep the base failed: {0}").format(e))
        return False


def finish_run(work_dir, model_data, export_path, success, aster_version=None):
    """
    After the run. success: the run ended normally without errors. Then the
    manifest and the clean-up of old bases; else the base folder goes and
    the older bases stay. Never stops the bridge.
    """
    kept = model_data.get("kept_base")
    if not kept:
        return False
    base_dir = os.path.join(work_dir, run_name(BASE_SUFFIX))
    try:
        if not success:
            if os.path.isdir(base_dir) and not _has_subfolder(base_dir):
                _remove_folder(base_dir)
            log(tr("WARNING: Run niet goed afgesloten: base niet bewaard.",
                   "WARNING: Run did not end well: base not kept."))
            return False
        stem, run_id = split_run_name(run_name(""))
        version = (aster_version or
                   bridge_version.aster_version_from_launcher(exe_aster_path()))
        write_manifest(
            os.path.join(work_dir, run_name(MANIFEST_SUFFIX)),
            build_manifest(model_data, kept, run_id, version,
                           read_memory_limit(export_path)))
        if run_id is not None:
            prune_bases(work_dir, stem, CONFIG_BRIDGE.get("keep_base_runs", 3),
                        os.path.basename(base_dir))
        return True
    except Exception as e:
        log(tr("WARNING: Manifest schrijven mislukt: {0}",
               "WARNING: Writing the manifest failed: {0}").format(e))
        return False
