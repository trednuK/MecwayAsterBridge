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
# prepare_base() adds the base to the .export before the run. finish_run()
# writes the manifest after the run, and only for a run that ended well: a
# manifest means the base is usable. After a failed run the base folder goes.
# Only then the newest "keep_base_runs" usable bases per model stay; older
# ones are removed, so a failed run never costs the last good base.
#
# Manifest (schema 1, UTF-8 JSON, no paths):
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
#   not_shared   parts where shared nodes do not describe the whole cut
#                (bonded contact, couplings, ...); a reader refuses or warns
#   extra_nodes  True if the base has nodes Mecway does not know (LINE_QUAD,
#                QUAD8_9, TRIA6_7 by CREA_MAILLAGE)
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

SCHEMA = 1
_TRUSS_PART = "_TRUSS"
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


def _not_shared(model_data):
    """What makes "shared nodes" an incomplete description of a cut."""
    return [name for name, key in (
        ("offset", "offset_links"), ("discrete", "discrete_sections"),
        ("contact", "contacts"), ("bonded", "bonded"),
        ("coupling", "couplings"), ("constraint", "constraint_equations"),
        ("pretension", "pretension_sections"),
        ("flexible_joint", "flexible_joints"))
        if model_data.get(key)]


def _deformation_by_component(model_data):
    """model_data["deformation_by_elset"] with the names Mecway shows."""
    import bridge_failure
    found = {}
    for elset, form in model_data.get("deformation_by_elset", {}).items():
        name = bridge_failure.mecway_name(model_data, elset)
        # The truss part of a component with beams (_split_trusses)
        if name.endswith(_TRUSS_PART):
            name = name[:-len(_TRUSS_PART)]
        found[name] = form if found.get(name, form) == form else "MIXED"
    return found


def build_manifest(model_data, kept, run_id, aster_version, memory_limit):
    """The manifest as a dict; see the header of this file."""
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
        "not_shared": _not_shared(model_data),
        "extra_nodes": bool(model_data.get("line_quad") or
                            model_data.get("shell_upgrades")),
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
