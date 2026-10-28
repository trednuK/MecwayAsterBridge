# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Adaptive refinement with HOMARD inside the Code-Aster job (step S35b):
the error indicator, the selection and the stop rules of the loop that
bridge_homard.wrap writes into study.comm. Runs in Code-Aster's Python 3
(numpy available), like aster_results_export.

Indicator (S35a, STAPPENPLAN.md): ZZ type (Zienkiewicz & Zhu 1987), the
element-node field (SIGM_ELNO or FLUX_ELNO) against its nodal average
(SIGM_NOEU or FLUX_NOEU):

    eta_e^2 = V_e * mean over the cell nodes of |s_elno - s_noeu|^2

global relative error 100 sqrt(sum eta^2 / (sum eta^2 + sum ||s||^2)) [%],
an L2 norm of the stress or heat flux (not the energy norm of ERME). The
native indicators stop on HOMARD's transition cells (measured, Code-Aster
17.4): ERTH_ELEM CALCUL_37 on THER_PYRAM13 and DVP_1 after a stationary
THER_NON_LINE; ERZ1_ELEM DVP_2 on a HOMARD TETRA10; ERZ2_ELEM CALCUL_38
with face cells; ERME_ELEM INDICATEUR_2 with face cells.

Messages: one line 'BRIDGE_ADAPT loop=<k> cells=<n> error=<e>' per loop
and 'BRIDGE_ADAPT stop=<reason>' (bridge_homard.report reads them).
"""
import numpy as np

# corner count -> sub-tetrahedra for the cell volume (Code-Aster corner
# order of HEXA8 / PENTA6 / PYRAM5 / TETRA4, first nodes of the quadratic
# cells); curved quadratic cells: volume from the corners (weights only)
_TETS = {
    4: [(0, 1, 2, 3)],
    5: [(0, 1, 2, 4), (0, 2, 3, 4)],
    6: [(0, 1, 2, 5), (0, 1, 5, 4), (0, 4, 5, 3)],
    8: [(0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6),
        (0, 4, 5, 6), (0, 5, 1, 6)],
}
_CORNERS = {4: 4, 10: 4, 5: 5, 13: 5, 6: 6, 15: 6, 18: 6, 8: 8, 20: 8,
            27: 8}
# Cells after refining one cell: 8 children plus HOMARD's transition cells
# around it (S35a: 3 selected hex20 -> 24 hex20 + 34 transitions); for the
# element limit (estimate before refining).
_GROWTH = 12
# Fields that are not projected onto the original mesh: nodal forces are
# integrals over the cells, not point values (reactions of the refined
# mesh cannot be interpolated).
_NOT_PROJECTED = ("REAC_NODA", "FORC_NODA", "FORC_NODA_NONL")


def cell_volumes(xyz, conn, cells):
    out = np.zeros(len(cells))
    for k, c in enumerate(cells):
        cn = conn[c]
        nc = _CORNERS.get(len(cn))
        if nc is None:
            continue
        p = xyz[np.asarray(cn[:nc])]
        v = 0.0
        for a, b, cc, d in _TETS[nc]:
            v += abs(np.dot(p[b] - p[a],
                            np.cross(p[cc] - p[a], p[d] - p[a]))) / 6.0
        out[k] = v
    return out


def _weights(cmps):
    return np.array([2.0 if (c[:2] == "SI" and len(c) == 4 and
                             c[2] != c[3]) else 1.0 for c in cmps])


def zz_indicator(res, index, elno, noeu, cells):
    """(eta per cell of cells, global relative error [%])."""
    mesh = res.getMesh()
    xyz = np.asarray(mesh.getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    conn = mesh.getConnectivity()
    sfe = res.getField(elno, index).toSimpleFieldOnCells()
    ve, _me = sfe.getValues()
    cmps = list(sfe.getComponents())
    sfn = res.getField(noeu, index).toSimpleFieldOnNodes()
    vn, _mn = sfn.getValues()
    ncmps = list(sfn.getComponents())
    keep_e = [i for i, c in enumerate(cmps) if c in ncmps]
    keep_n = [ncmps.index(cmps[i]) for i in keep_e]
    w = _weights([cmps[i] for i in keep_e])
    # rows of getValues(): only cells with values, nbpt rows each, in cell
    # order (aster_results_export._cell_layout)
    nbpt = np.array([sfe.getNumberOfPointsOfCell(c)
                     if sfe.getNumberOfComponentsForSubpointsOfCell(c) > 0
                     else 0 for c in range(len(conn))])
    start = np.concatenate([[0], np.cumsum(nbpt)[:-1]])
    vol = cell_volumes(xyz, conn, cells)
    eta2 = np.zeros(len(cells))
    nrm2 = np.zeros(len(cells))
    for k, c in enumerate(cells):
        nb = nbpt[c]
        if nb == 0:
            continue
        nodes = np.asarray(conn[c][:nb])
        se = ve[start[c]:start[c] + nb][:, keep_e]
        sn = vn[nodes][:, keep_n]
        eta2[k] = vol[k] * np.mean(np.sum(w * (se - sn) ** 2, axis=1))
        nrm2[k] = vol[k] * np.mean(np.sum(w * sn ** 2, axis=1))
    tot = eta2.sum() + nrm2.sum()
    rel = 100.0 * np.sqrt(eta2.sum() / tot) if tot > 0 else 0.0
    return np.sqrt(eta2), float(rel)


def dorfler(eta, theta):
    """Indices of the fewest cells carrying the fraction theta of
    sum eta^2 (Doerfler 1996)."""
    order = np.argsort(-eta)
    cum = np.cumsum(eta[order] ** 2)
    if len(cum) == 0 or cum[-1] <= 0:
        return np.array([], dtype=int)
    n = int(np.searchsorted(cum, theta * cum[-1]) + 1)
    return order[:n]


def projected_fields(res):
    """Node and element-node fields of res for PROJ_CHAMP (not the nodal
    forces, not Gauss-point or cell fields)."""
    out = []
    for name in res.getFieldsNames():
        if name in _NOT_PROJECTED:
            continue
        if name in ("DEPL", "TEMP") or name.endswith("_NOEU") or \
                name.endswith("_ELNO"):
            out.append(name)
    return tuple(sorted(out))


class Loop(object):
    """State of the adaptive loop (written into study.comm by
    bridge_homard.wrap)."""

    def __init__(self, target, max_loops, max_elements, fraction, solids):
        self.target = float(target)
        self.max_loops = int(max_loops)
        self.max_elements = int(max_elements)
        self.fraction = float(fraction)
        self.solids = list(solids)
        self.history = []          # (loop, cells, error)
        self.reason = None

    def _cells(self, mesh):
        cells = set()
        for g in self.solids:
            cells.update(int(c) for c in mesh.getCells(g))
        return np.array(sorted(cells), dtype=int)

    def _stop(self, reason):
        self.reason = reason
        print("BRIDGE_ADAPT stop={0}".format(reason))
        return None

    def after_solve(self, k, res, elno, noeu, mesh):
        """Indicator of loop k; returns the 0-based cells to refine
        (list) or None to stop."""
        cells = self._cells(mesh)
        index = res.getIndexes()[-1]
        eta, rel = zz_indicator(res, index, elno, noeu, cells)
        self.history.append((k, len(cells), rel))
        print("BRIDGE_ADAPT loop={0} cells={1} error={2:.4g}".format(
            k, len(cells), rel))
        if rel <= self.target:
            return self._stop("target")
        if k >= self.max_loops:
            return self._stop("loops")
        # Do not stop on one rising loop: HOMARD's transitions make the
        # global error rise now and then (S35a: 1.92 -> 1.71 -> 0.83 ->
        # 1.24 -> 0.62 %); stop when it is above the best value two loops
        # in a row.
        if len(self.history) >= 3:
            best = min(h[2] for h in self.history[:-2])
            if self.history[-1][2] > best and self.history[-2][2] > best:
                return self._stop("rising")
        sel = dorfler(eta, self.fraction)
        if len(sel) == 0:
            return self._stop("none")
        total = mesh.getNumberOfCells()
        if total + _GROWTH * len(sel) > self.max_elements:
            return self._stop("elements")
        return [int(cells[i]) for i in sel]

    def homard_failed(self, k):
        print("BRIDGE_ADAPT stop=homard")
        print("BRIDGE_ADAPT_ERROR HOMARD produced no mesh in loop {0}; "
              "the result of loop {0} is used.".format(k))
        self.reason = "homard"

    def summary(self):
        for k, n, e in self.history:
            print("BRIDGE_ADAPT_SUMMARY loop={0} cells={1} error={2:.4g}"
                  .format(k, n, e))
