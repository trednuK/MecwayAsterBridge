# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Read a Code-Aster MED result (.rmed) on the host and write the same
# <results> fragment aster_results_export writes inside the job.
# Used when the job runs in a container (CAVE): the container cannot
# import Scripts or see the Windows path of the .liml. No NumPy, no
# medcoupling: bridge_hdf5 reads the HDF5 file.
#
# Covered: nodal DEPL, SIGM_NOEU, SIEQ_NOEU (VMIS), REAC_NODA, TEMP,
# FLUX_NOEU, and the element-node fields SIGM_ELNO and SIEQ_ELNO.
# One step is static (no <timestep>); several steps are <timestep>.
# Eigenmodes are not rewritten as <mode> (the frequency is not in the
# MED field). Do not use f-strings (IronPython 2.7).

from __future__ import division

import base64
import os
import struct

import bridge_hdf5

_NL = b"\r\n"
_B64 = 64
_NO_PROFILE = "MED_NO_PROFILE_INTERNAL"

# (med field, component, mecway name, element-node?)
_MAP = (
    ("DEPL", "DX", "displx", False),
    ("DEPL", "DY", "disply", False),
    ("DEPL", "DZ", "displz", False),
    ("DEPL", "DRX", "rotx", False),
    ("DEPL", "DRY", "roty", False),
    ("DEPL", "DRZ", "rotz", False),
    ("SIGM_NOEU", "SIXX", "stressxx", False),
    ("SIGM_NOEU", "SIYY", "stressyy", False),
    ("SIGM_NOEU", "SIZZ", "stresszz", False),
    ("SIGM_NOEU", "SIXY", "stressxy", False),
    ("SIGM_NOEU", "SIYZ", "stressyz", False),
    ("SIGM_NOEU", "SIXZ", "stresszx", False),
    ("SIEQ_NOEU", "VMIS", "vonmises", False),
    ("res_sup", "VMIS", "vonmisesu1", False),
    ("res_moy", "VMIS", "vonmisesm", False),
    ("res_inf", "VMIS", "vonmisesb", False),
    ("REAC_NODA", "DX", "reactionforcex", False),
    ("REAC_NODA", "DY", "reactionforcey", False),
    ("REAC_NODA", "DZ", "reactionforcez", False),
    ("REAC_NODA", "DRX", "reactionmomx", False),
    ("REAC_NODA", "DRY", "reactionmomy", False),
    ("REAC_NODA", "DRZ", "reactionmomz", False),
    ("TEMP", "TEMP", "temperature", False),
    ("FLUX_NOEU", "FLUX", "heatfluxx", False),
    ("FLUX_NOEU", "FLUY", "heatfluxy", False),
    ("FLUX_NOEU", "FLUZ", "heatfluxz", False),
    ("SIGM_ELNO", "SIXX", "stressxx", True),
    ("SIGM_ELNO", "SIYY", "stressyy", True),
    ("SIGM_ELNO", "SIZZ", "stresszz", True),
    ("SIGM_ELNO", "SIXY", "stressxy", True),
    ("SIGM_ELNO", "SIYZ", "stressyz", True),
    ("SIGM_ELNO", "SIXZ", "stresszx", True),
    ("SIEQ_ELNO", "VMIS", "vonmises", True),
)


def read_med(path):
    """Mesh nodes, cells and fields. fields[name] = list of steps
    (time, nodal {nid: [comps]}, elno {etype: {eid: [[comps per node]]}})."""
    fh = bridge_hdf5.File(path)
    try:
        mesh_name, body = _mesh_body(fh)
        nodes = _nodes(body)
        cells = _cells(body, nodes)
        fields = {}
        if _has(fh, "CHA"):
            for name in list(fh["CHA"].keys()):
                comps, steps = _field(fh["CHA"][name], nodes, cells)
                fields[name] = {"comps": comps, "steps": steps}
        return {"mesh": mesh_name, "nodes": nodes, "cells": cells,
                "fields": fields}
    finally:
        fh.close()


def _has(group, key):
    try:
        group[key]
    except KeyError:
        return False
    return True


def _text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("ascii", "replace").replace("\x00", "").strip()
    return str(value).replace("\x00", "").strip()


def _num_attr(attrs, key, default=0):
    if key not in attrs or attrs[key] is None:
        return default
    return int(attrs[key])


def _components(attrs):
    raw = _text(attrs.get("NOM"))
    if not raw:
        return []
    # Fixed width 16, as the MED library writes component names.
    if len(raw) >= 16 and len(raw) % 16 == 0:
        return [raw[i:i + 16].strip() for i in range(0, len(raw), 16)]
    return raw.split()


def _flat(dataset):
    values = dataset[:]
    if isinstance(values, list):
        return values
    return list(values)


def _fortran(flat, nrow, ncol):
    """Column-major (nrow, ncol) as a list of rows."""
    rows = []
    for i in range(nrow):
        rows.append([flat[i + k * nrow] for k in range(ncol)])
    return rows


def _mesh_body(fh):
    meshes = fh["ENS_MAA"]
    name = list(meshes.keys())[0]
    mesh = meshes[name]
    if _has(mesh, "NOE"):
        return name, mesh
    for key in list(mesh.keys()):
        if _has(mesh[key], "NOE"):
            return name, mesh[key]
    raise ValueError("MED mesh has no nodes")


def _nodes(body):
    coo = body["NOE"]["COO"]
    flat = _flat(coo)
    nbr = _num_attr(coo.attrs, "NBR", 0)
    if nbr <= 0:
        raise ValueError("MED mesh has no nodes")
    dim = len(flat) // nbr
    coords = _fortran(flat, nbr, dim)
    nums = None
    if _has(body["NOE"], "NUM"):
        nums = [int(v) for v in _flat(body["NOE"]["NUM"])]
    out = []
    for i in range(nbr):
        nid = nums[i] if nums else i + 1
        xyz = coords[i] + [0.0] * (3 - len(coords[i]))
        out.append((nid, xyz))
    return out


def _cells(body, nodes):
    """{med type: [(element number, [mecway node ids])]}."""
    if not _has(body, "MAI"):
        return {}
    index_to_nid = {}
    for i, (nid, _xyz) in enumerate(nodes):
        index_to_nid[i + 1] = nid
    cells = {}
    mai = body["MAI"]
    for typ in list(mai.keys()):
        grp = mai[typ]
        if not _has(grp, "NOD"):
            continue
        nod = grp["NOD"]
        ncell = _num_attr(nod.attrs, "NBR", 0)
        flat = [int(v) for v in _flat(nod)]
        if ncell <= 0:
            continue
        npe = len(flat) // ncell
        conn = _fortran(flat, ncell, npe)
        nums = None
        if _has(grp, "NUM"):
            nums = [int(v) for v in _flat(grp["NUM"])]
        block = []
        for i in range(ncell):
            eid = nums[i] if nums else i + 1
            block.append((eid, [index_to_nid.get(k, k) for k in conn[i]]))
        cells[typ] = block
    return cells


def _profile_values(support):
    """(n_entities, rows of components) from a NOE or NOE.TYPE group."""
    profile = _text(support.attrs.get("PFL")) or _NO_PROFILE
    if not _has(support, profile):
        # Some files store CO directly on the support.
        if _has(support, "CO"):
            data = support
        else:
            return 0, []
    else:
        data = support[profile]
    co = data["CO"]
    nbr = _num_attr(co.attrs, "NBR", _num_attr(data.attrs, "NBR", 0))
    nga = _num_attr(co.attrs, "NGA", _num_attr(data.attrs, "NGA", 1))
    flat = _flat(co)
    if nbr <= 0 or not flat:
        return 0, []
    ncomp = len(flat) // (nbr * max(nga, 1))
    if nga <= 1:
        return nbr, _fortran(flat, nbr, ncomp)
    # (cell, gauss, component), Fortran order.
    rows = []
    span = nbr * nga
    for i in range(nbr):
        points = []
        for g in range(nga):
            points.append([flat[i + g * nbr + c * span] for c in range(ncomp)])
        rows.append(points)
    return nbr, rows


def _field(group, nodes, cells):
    steps = []
    comps = _components(group.attrs)
    for key in sorted(group.keys()):
        step = group[key]
        time = step.attrs.get("PDT", 0.0)
        try:
            time = float(time)
        except (TypeError, ValueError):
            time = 0.0
        nodal = {}
        elno = {}
        if _has(step, "NOE"):
            _n, rows = _profile_values(step["NOE"])
            for i, row in enumerate(rows):
                if i < len(nodes) and row and not isinstance(row[0], list):
                    nodal[nodes[i][0]] = row
        for sub in list(step.keys()):
            if not str(sub).startswith("NOE."):
                continue
            typ = str(sub).split(".", 1)[1]
            _n, rows = _profile_values(step[sub])
            block = cells.get(typ) or []
            stored = {}
            for i, points in enumerate(rows):
                if i < len(block) and points and isinstance(points[0], list):
                    eid, conn = block[i]
                    stored[eid] = (conn, points)
            if stored:
                elno[typ] = stored
        steps.append((time, nodal, elno))
    return comps, steps


def _steps(med):
    times = []
    for info in med["fields"].values():
        for time, _n, _e in info["steps"]:
            if time not in times:
                times.append(time)
    return times


def _comp_index(info, comp, width):
    names = info["comps"]
    if comp in names:
        return names.index(comp)
    if comp == "MAG":
        return None
    if not names and comp in ("DX", "DY", "DZ", "TEMP", "VMIS"):
        fallback = {"DX": 0, "DY": 1, "DZ": 2, "TEMP": 0, "VMIS": 0}
        idx = fallback[comp]
        return idx if idx < width else None
    return None


def _present(med):
    found = []
    for field, comp, name, elno in _MAP:
        info = med["fields"].get(field)
        if not info or not info["steps"]:
            continue
        _time, nodal, blocks = info["steps"][0]
        if elno:
            if not blocks:
                continue
            sample = next(iter(next(iter(blocks.values())).values()))[1]
            width = len(sample[0]) if sample else 0
        else:
            if not nodal:
                continue
            width = len(next(iter(nodal.values())))
        if _comp_index(info, comp, width) is None and comp != "MAG":
            continue
        if comp == "MAG":
            continue
        found.append((field, comp, name, elno))
    names = [row[2] for row in found]
    if "displx" in names and "disply" in names and "displz" in names:
        found.append(("DEPL", "MAG", "displmag", False))
    if "heatfluxx" in names and "heatfluxy" in names:
        found.append(("FLUX_NOEU", "MAG", "heatfluxmag", False))
    return found


def _nodal_value(info, step_i, comp):
    steps = info["steps"]
    if step_i >= len(steps):
        if len(steps) != 1:
            return {}
        step_i = 0
    _time, nodal, _elno = steps[step_i]
    if not nodal:
        return {}
    width = len(next(iter(nodal.values())))
    if comp == "MAG":
        out = {}
        for nid, row in nodal.items():
            out[nid] = (row[0] ** 2 + row[1] ** 2 +
                        (row[2] ** 2 if len(row) > 2 else 0.0)) ** 0.5
        return out
    idx = _comp_index(info, comp, width)
    if idx is None:
        return {}
    return dict((nid, row[idx]) for nid, row in nodal.items())


def _elno_value(info, step_i, comp, model_data):
    """{element id: [value per Mecway node]}."""
    steps = info["steps"]
    if step_i >= len(steps):
        if len(steps) != 1:
            return {}
        step_i = 0
    _time, _nodal, blocks = steps[step_i]
    elements = (model_data or {}).get("elements") or {}
    out = {}
    for _typ, stored in blocks.items():
        for eid, (conn, points) in stored.items():
            width = len(points[0]) if points else 0
            idx = _comp_index(info, comp, width)
            if idx is None:
                continue
            by_node = {}
            for k, nid in enumerate(conn):
                if k < len(points):
                    by_node[nid] = points[k][idx]
            order = conn
            elem = elements.get(eid)
            if (isinstance(elem, (list, tuple)) and len(elem) >= 2 and
                    isinstance(elem[1], (list, tuple))):
                order = elem[1]
            out[eid] = [by_node.get(nid, 0.0) for nid in order]
    return out


def _groups_for_nodes(ids, model_data):
    """[(elset or '', [positions into ids])]."""
    elsets = (model_data or {}).get("elsets") or {}
    elements = (model_data or {}).get("elements") or {}
    if not elsets or not elements:
        return [("", list(range(len(ids))))]
    pos = dict((nid, i) for i, nid in enumerate(ids))
    used = set()
    groups = []
    for name in elsets:
        nids = []
        for eid in elsets[name]:
            elem = elements.get(eid)
            if not elem:
                continue
            nodes = elem[1] if isinstance(elem, (list, tuple)) else elem
            for nid in nodes:
                if nid in pos and nid not in nids:
                    nids.append(nid)
                    used.add(nid)
        if nids:
            groups.append((str(name), [pos[n] for n in nids]))
    free = [pos[n] for n in ids if n not in used]
    if free:
        groups.insert(0, ("", free))
    return groups or [("", list(range(len(ids))))]


def _num(x):
    x = float(x)
    if x == 0.0:
        x = 0.0
    return "{0:.15G}".format(x)


def _xml(text):
    amp = "&" + "amp;"
    lt = "&" + "lt;"
    gt = "&" + "gt;"
    quot = "&" + "quot;"
    return (text.replace("&", amp).replace("<", lt)
            .replace(">", gt).replace('"', quot))


def _b64(data):
    enc = base64.b64encode(data)
    if not isinstance(enc, bytes):
        enc = enc.encode("ascii")
    lines = [enc[i:i + _B64] for i in range(0, len(enc), _B64)]
    return _NL.join(lines) + _NL


def _pack_ids(ids):
    return b"".join(struct.pack("<i", int(i)) for i in ids)


def _pack_f64(values):
    return b"".join(struct.pack("<d", float(v)) for v in values)


def _ids_xml(name, ids, element):
    tag = "elementnodeids" if element else "nodeids"
    body = ('      <{0} name="{1}">'.format(tag, _xml(name))).encode("utf-8")
    body += _b64(_pack_ids(ids))
    body += "</{0}>".format(tag).encode("ascii") + _NL
    return body


def _var_xml(name, values, groups, element, indent):
    tag = "elementnodevariable" if element else "nodevariable"
    empty = "elements" if element else "nodes"
    i1, i2 = indent + "  ", indent + "    "
    parts = [indent + '<{0} name="{1}">'.format(tag, _xml(name)),
             i1 + "<maxandmin>"]
    for gname, pos in groups:
        if not pos:
            continue
        sub = [values[i] for i in pos]
        parts.append(i2 + '<component name="{0}" max="{1}" min="{2}" />'
                     .format(_xml(gname), _num(max(sub)), _num(min(sub))))
    parts.append(i1 + "</maxandmin>")
    head = "\r\n".join(parts) + "\r\n" + i1 + "<valuesdouble>"
    tail = ("</valuesdouble>\r\n{0}<{1} />\r\n{0}<values />\r\n"
            "{2}</{3}>\r\n").format(i1, empty, indent, tag)
    return head.encode("utf-8") + _b64(_pack_f64(values)) + tail.encode("ascii")


def _write(out_path, rows, times, model_data, med):
    static = len(times) <= 1
    indent = "      " if static else "        "
    parts = [b'    <results precision="double">\r\n']
    # ids from the first step; a later step uses the same nodes
    prepared = []
    for field, comp, name, elno in rows:
        info = med["fields"][field]
        if elno:
            values = _elno_value(info, 0, comp, model_data)
            ids = sorted(values)
            prepared.append((field, comp, name, True, ids))
            parts.append(_ids_xml(name, ids, True))
        else:
            values = _nodal_value(info, 0, comp)
            ids = sorted(values)
            prepared.append((field, comp, name, False, ids))
            parts.append(_ids_xml(name, ids, False))
    for k, _time in enumerate(times):
        if not static:
            parts.append('      <timestep id="{0}" time="{1} s">\r\n'.format(
                k, _num(times[k])).encode("ascii"))
        for field, comp, name, elno, ids in prepared:
            info = med["fields"][field]
            if elno:
                by_elem = _elno_value(info, k, comp, model_data)
                flat = []
                for eid in ids:
                    flat.extend(by_elem.get(eid) or [])
                groups = [("", list(range(len(flat))))]
            else:
                by_node = _nodal_value(info, k, comp)
                flat = [by_node.get(nid, 0.0) for nid in ids]
                groups = _groups_for_nodes(ids, model_data)
            parts.append(_var_xml(name, flat, groups, elno, indent))
        if not static:
            parts.append(b"      </timestep>\r\n")
    parts.append(b"    </results>\r\n")
    f = open(out_path, "wb")
    try:
        f.write(b"".join(parts))
    finally:
        f.close()


def write_fragment(rmed_path, out_path, model_data=None):
    """Write <results> from a .rmed. Returns the number of variables."""
    med = read_med(rmed_path)
    times = _steps(med)
    rows = _present(med)
    if not rows:
        raise ValueError("no Mecway field in {0}".format(rmed_path))
    _write(out_path, rows, times or [0.0], model_data, med)
    return len(rows)
