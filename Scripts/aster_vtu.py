# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_vtu.py
# VTU/PVD export of the result (setting vtu_export), for ParaView and
# MWHub Post (AdvancedToolsHub). Runs in the Code-Aster job (Python 3,
# numpy), called by aster_results_export._export with the same Mecway
# variables that go to the .liml, so ParaView and Mecway show the same
# numbers.
#
# Files (next to the results fragment <model>_<run_id>_results.xml):
#   <model>_<run_id>.pvd       collection, one <DataSet> per time step
#   <model>_<run_id>_<k>.vtu   step k (0-based), UnstructuredGrid
#   <model>_<run_id>_knopen.csv node series (NodeSeries): per named node
#                              selection of the .liml (<nodeselection>, at
#                              most MAX_SERIES_NODES nodes) every node
#                              variable over all steps; sidecar
#                              node_series of mwhubpost-job/1
#
# Contents of a .vtu:
#   - points and cells from the .liml (Mecway node and element numbers in
#     NODE_ID / ELEMENT_ID), Mecway's node order converted to VTK's
#     (_VTK_CELLS; Mecway order from the skill "mecway", liml-format §3);
#   - node variables as PointData under their Mecway name (displx, ...),
#     plus the vector DEPL (displx/y/z) for the deformation in ParaView;
#   - element-node variables (Mecway's elementnodevariable, e.g. stresses
#     per element) as CellData: the average over the nodes of the element
#     (choice B1: one value per cell is enough for colouring and the
#     erosion filter; the exact corner values stay in the .liml and MED);
#   - beam section forces (Mecway's tensileforce, sheary, ... per element
#     node) also per element end: EFGE_<N|VY|VZ|MT|MFY|MFZ>_1 at the first
#     and _2 at the last node of the element (Mecway order: line3 = c0 m
#     c1), for the beam sidecar of bridge_beams (mwhubpost-beams/1);
#   - the element variable "failed" as BEZWEKEN (_RENAME) and extra cell
#     arrays from aster_results_export (T_BEZWIJK), see add_cells.
#   Nodes or elements a variable has no value for get NaN.
#
# Format: VTK XML, appended raw data, header_type UInt64 (VTK file format
# documentation, "XML File Formats", AppendedData). Field values float32
# with precision "single", else float64; coordinates always float64.
#
# Do not use f-strings: same style as the rest of the bridge.

import os

import numpy as np


# Mecway shape -> (VTK cell type, VTK node order as positions in Mecway's
# node list). VTK types from vtkCellType.h. Mecway order: hex20 with the
# vertical edges (04 15 26 37) before the top edges, VTK the other way
# round (wedge15 likewise); quad8/tri6/line3 alternate corner and midside
# nodes in Mecway. Checked with CellSize on unit elements in Mecway order:
# ParaView 6.2 gives every volume/area/length exact and positive; Salome's
# ParaView 5.11 (older VTK) gives the wedges -0.5 with the same order
# (different wedge convention of that VTK; display is not affected).
_VTK_CELLS = {
    "line2": (3, (0, 1)),
    "line3": (21, (0, 2, 1)),
    "tri3": (5, (0, 1, 2)),
    "tri6": (22, (0, 2, 4, 1, 3, 5)),
    "quad4": (9, (0, 1, 2, 3)),
    "quad8": (23, (0, 2, 4, 6, 1, 3, 5, 7)),
    "tet4": (10, (0, 1, 2, 3)),
    "tet10": (24, tuple(range(10))),
    "pyr5": (14, (0, 1, 2, 3, 4)),
    "pyr13": (27, tuple(range(13))),
    "wedge6": (13, tuple(range(6))),
    "wedge15": (26, tuple(range(9)) + (12, 13, 14, 9, 10, 11)),
    "hex8": (12, tuple(range(8))),
    "hex20": (25, tuple(range(12)) + (16, 17, 18, 19, 12, 13, 14, 15)),
}

# Mecway variable -> array name in the VTU (MWHub Post contract,
# mwhubpost-job/1 example A: erosion field BEZWEKEN, intact = 0).
_RENAME = {"failed": "BEZWEKEN"}

# Mecway beam section forces -> Code-Aster component (aster_results_export
# FIELD_TABLE, beam_forces: local axes x along the beam, y = V, z = W).
_EFGE = {"tensileforce": "N", "sheary": "VY", "shearz": "VZ",
         "torsion": "MT", "bendingmomv": "MFY", "bendingmomw": "MFZ"}

# Larger node selections are left out of the node series (a column per
# node and variable; a face of a fine mesh would give thousands).
MAX_SERIES_NODES = 100

# Mecway node variables that together form a VTK vector.
_VECTORS = (("DEPL", ("displx", "disply", "displz")),)


def base_path(fragment_path):
    """<dir>/<model>_<run_id> from <dir>/<model>_<run_id>_results.xml
    (bridge_to_aster.results_file); otherwise the path without extension."""
    root = fragment_path
    if root.endswith("_results.xml"):
        return root[:-len("_results.xml")]
    return os.path.splitext(root)[0]


class VtuSeries(object):
    """One .vtu per time step plus the .pvd. Usage: s = VtuSeries(...);
    s.step(k, time, values) per step; s.close() writes the .pvd."""

    def __init__(self, base, model, variables, precision="single"):
        self.base = base
        self.dtype = np.float32 if precision == "single" else np.float64
        self.coords = np.asarray(model["coords"], dtype=np.float64)
        self.n = self.coords.shape[0]
        conn, offsets, types, eids = [], [], [], []
        self.skipped = set()
        for eid in sorted(model["elements"]):
            shape, nodes = model["elements"][eid]
            cell = _VTK_CELLS.get(shape)
            if cell is None or len(nodes) != len(cell[1]):
                self.skipped.add(shape)
                continue
            conn.extend(nodes[i] - 1 for i in cell[1])
            offsets.append(len(conn))
            types.append(cell[0])
            eids.append(eid)
        self.conn = np.asarray(conn, dtype=np.int64)
        self.offsets = np.asarray(offsets, dtype=np.int64)
        self.types = np.asarray(types, dtype=np.uint8)
        self.eids = np.asarray(eids, dtype=np.int32)
        self.cell_of = dict((e, i) for i, e in enumerate(eids))
        self.variables = variables
        self.layout = [self._layout(v, model) for v in variables]
        self.extra_cells = []
        self.steps = []
        self.failed = False
        sels = [(name, nids) for name, nids in
                (model.get("nodesel") or {}).items()
                if 0 < len(nids) <= MAX_SERIES_NODES]
        self.series = NodeSeries(base + "_knopen.csv", sels, self.n) \
            if sels else None

    def _layout(self, var, model):
        """Where the values of var go: ("p", rows) for a node variable,
        ("c", cells, starts) for an element-node variable."""
        ids = np.asarray(var.ids, dtype=np.int64)
        if not var.element:
            return ("p", ids - 1)
        counts = [len(model["elements"][int(e)][1]) for e in ids]
        starts = np.concatenate(([0], np.cumsum(counts)[:-1])).astype(
            np.int64) if len(counts) else np.zeros(0, dtype=np.int64)
        cells = np.asarray([self.cell_of.get(int(e), -1) for e in ids],
                           dtype=np.int64)
        return ("c", cells, starts, np.asarray(counts, dtype=np.float64))

    def add_cells(self, name, getter):
        """Extra cell array: getter(k) -> {Mecway element number: value}
        for step k (other cells NaN), or None (array left out)."""
        self.extra_cells.append((name, getter))

    def step(self, k, time_value, values):
        """Write step k; values[i] = values of variables[i] (or None)."""
        point, cell = [], []
        by_name = {}
        for var, lay, vals in zip(self.variables, self.layout, values):
            if vals is None:
                continue
            vals = np.asarray(vals, dtype=np.float64)
            if lay[0] == "p":
                out = np.full(self.n, np.nan)
                ok = (lay[1] >= 0) & (lay[1] < self.n)
                out[lay[1][ok]] = vals[ok]
                point.append((var.name, out))
                by_name.setdefault(var.name, out)
            else:
                out = np.full(len(self.eids), np.nan)
                if len(lay[1]):
                    mean = np.add.reduceat(vals, lay[2]) / lay[3]
                    ok = lay[1] >= 0
                    out[lay[1][ok]] = mean[ok]
                cell.append((_RENAME.get(var.name, var.name), out))
                if var.name in _EFGE and len(lay[1]):
                    ok = lay[1] >= 0
                    for end, pos in (("1", lay[2]),
                                     ("2", lay[2] + lay[3].astype(
                                         np.int64) - 1)):
                        out = np.full(len(self.eids), np.nan)
                        out[lay[1][ok]] = vals[pos[ok]]
                        cell.append(("EFGE_{0}_{1}".format(
                            _EFGE[var.name], end), out))
        for name, parts in _VECTORS:
            if all(p in by_name for p in parts):
                point.insert(0, (name, np.column_stack(
                    [by_name[p] for p in parts])))
        for name, getter in self.extra_cells:
            got = getter(k)
            if got is None:
                continue
            out = np.full(len(self.eids), np.nan)
            for eid, value in got.items():
                i = self.cell_of.get(int(eid))
                if i is not None:
                    out[i] = value
            cell.append((name, out))
        if self.series is not None:
            self.series.add(time_value, by_name)
        path = "{0}_{1}.vtu".format(self.base, k)
        _write_vtu(path, self, point, cell)
        self.steps.append((float(time_value), os.path.basename(path)))

    def close(self):
        """Write the .pvd; returns its path."""
        path = self.base + ".pvd"
        lines = ['<?xml version="1.0"?>',
                 '<VTKFile type="Collection" version="1.0" '
                 'byte_order="LittleEndian">',
                 '  <Collection>']
        for t, name in self.steps:
            lines.append('    <DataSet timestep="{0!r}" part="0" '
                         'file="{1}"/>'.format(t, name))
        lines += ['  </Collection>', '</VTKFile>', '']
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        os.replace(tmp, path)
        if self.series is not None:
            self.series.close()
        return path


class NodeSeries(object):
    """CSV with a column time and one column <selection>.N<nid>.<variable>
    per node of the selections and node variable (names of the first
    step); a missing value is empty. Separator ",", decimal point."""

    def __init__(self, path, selections, n):
        self.path = path
        self.cols = [(sel, nid) for sel, nids in selections
                     for nid in nids if 1 <= nid <= n]
        self.names = None
        self.rows = []

    def add(self, time_value, by_name):
        if self.names is None:
            self.names = list(by_name)
        row = [repr(float(time_value))]
        for sel, nid in self.cols:
            for name in self.names:
                vals = by_name.get(name)
                v = None if vals is None else float(vals[nid - 1])
                row.append("" if v is None or v != v else repr(v))
        self.rows.append(row)

    def close(self):
        head = ["time"] + ["{0}.N{1}.{2}".format(sel.replace(",", "_"),
                                                  nid, name)
                           for sel, nid in self.cols
                           for name in (self.names or [])]
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(",".join(head) + "\n")
            for row in self.rows:
                f.write(",".join(row) + "\n")
        os.replace(tmp, self.path)


def _vtk_type(a):
    return {"float32": "Float32", "float64": "Float64", "int32": "Int32",
            "int64": "Int64", "uint8": "UInt8"}[a.dtype.name]


def _write_vtu(path, series, point, cell):
    """One UnstructuredGrid with appended raw data."""
    blocks = []
    offset = [0]

    def array(a, name=None, ncomp=1):
        a = np.ascontiguousarray(a)
        head = '<DataArray type="{0}"'.format(_vtk_type(a))
        if name is not None:
            head += ' Name="{0}"'.format(name.replace('"', "'"))
        if ncomp != 1:
            head += ' NumberOfComponents="{0}"'.format(ncomp)
        head += ' format="appended" offset="{0}"/>'.format(offset[0])
        raw = a.tobytes()
        blocks.append(np.uint64(len(raw)).tobytes() + raw)
        offset[0] += 8 + len(raw)
        return head

    dt = series.dtype
    xml = ['<?xml version="1.0"?>',
           '<VTKFile type="UnstructuredGrid" version="1.0" '
           'byte_order="LittleEndian" header_type="UInt64">',
           '  <UnstructuredGrid>',
           '    <Piece NumberOfPoints="{0}" NumberOfCells="{1}">'.format(
               series.n, len(series.eids)),
           '      <PointData>']
    xml.append('        ' + array(np.arange(1, series.n + 1,
                                            dtype=np.int32), "NODE_ID"))
    for name, vals in point:
        ncomp = vals.shape[1] if vals.ndim == 2 else 1
        xml.append('        ' + array(vals.astype(dt), name, ncomp))
    xml += ['      </PointData>', '      <CellData>']
    xml.append('        ' + array(series.eids, "ELEMENT_ID"))
    for name, vals in cell:
        xml.append('        ' + array(vals.astype(dt), name))
    xml += ['      </CellData>', '      <Points>',
            '        ' + array(series.coords, None, 3),
            '      </Points>', '      <Cells>',
            '        ' + array(series.conn, "connectivity"),
            '        ' + array(series.offsets, "offsets"),
            '        ' + array(series.types, "types"),
            '      </Cells>', '    </Piece>', '  </UnstructuredGrid>',
            '  <AppendedData encoding="raw">']
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(("\n".join(xml) + "\n   _").encode("utf-8"))
        for b in blocks:
            f.write(b)
        f.write(b"\n  </AppendedData>\n</VTKFile>\n")
    os.replace(tmp, path)
