# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
S35 prototype library (Python 3, runs INSIDE the Code-Aster 17.4 job): a
ZZ-type error indicator from a discontinuous *_ELNO field against its nodal
average *_NOEU, a Doerfler selection and the cell volumes it needs.

Why an own indicator (S35 research, STAPPENPLAN.md §S35, measured with
Code-Aster 17.4): the native indicators fail on the meshes HOMARD makes from
the bridge's hex meshes (transition PYRAM13/TETRA10):
  - ERTH_ELEM: <EXCEPTION> CALCUL_37 "THER_PYRAM13 ne sait pas encore
    calculer l'option ERTH_ELEM"; after THER_NON_LINE (stationary) DVP_1 in
    rsadpa.F90 already on a pure HEXA20 mesh;
  - ERZ1_ELEM: DVP_2 (floating point exception, option CALC_ESTI_ERRE) on a
    HOMARD TETRA10 of a mixed mesh;
  - ERZ2_ELEM: CALCUL_38 (CALC_NOEU_BORD) as soon as the model has face
    cells (pressure/traction faces);
  - ERME_ELEM: needs SIGM_ELNO on the whole model (INDICATEUR_2 with face
    cells) and the loads in EXCIT (no reuse, CALCULEL_39); it is the
    residual estimator of the linear problem (KNOWN_BUGS 51).
The ZZ indicator only needs SIGM_ELNO/SIGM_NOEU (or FLUX_ELNO/FLUX_NOEU),
which exist for every 3D cell type, also with plasticity.

Not part of the bridge: a prototype for S35b (see run_s35.py).
"""
import numpy as np

# Corner count -> sub-tetrahedra (corner indices) for the cell volume. The
# corner order is Code-Aster's (HEXA8/PENTA6/PYRAM5/TETRA4, the first
# nodes of the quadratic cells). The volume of curved quadratic cells is
# taken from the corners (weights only).
_TETS = {
    4: [(0, 1, 2, 3)],
    5: [(0, 1, 2, 4), (0, 2, 3, 4)],
    6: [(0, 1, 2, 5), (0, 1, 5, 4), (0, 4, 5, 3)],
    8: [(0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6),
        (0, 4, 5, 6), (0, 5, 1, 6)],
}
# number of nodes of a 3D cell -> number of corners
_CORNERS = {4: 4, 10: 4, 5: 5, 13: 5, 6: 6, 15: 6, 18: 6, 8: 8, 20: 8,
            27: 8}


def cell_volumes(xyz, conn, cells):
    """Volume per cell in cells (0 for a cell that is not 3D)."""
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
    """Shear components of a stress tensor count twice in s:s."""
    return np.array([2.0 if (c[:2] == "SI" and len(c) == 4 and
                             c[2] != c[3]) else 1.0 for c in cmps])


def zz_indicator(res, index, elno, noeu, cells):
    """
    ZZ-type indicator (Zienkiewicz & Zhu 1987, nodal averaging as the
    recovered field): per cell e

        eta_e^2 = V_e * mean over the cell nodes of |s_elno - s_noeu|^2

    and the global relative error 100 sqrt(sum eta^2 / (sum eta^2 +
    sum V_e mean |s_noeu|^2)) [%], an L2 norm of the stress (or heat flux),
    not the energy norm of ERME (docs/Foutschatter.md §1.5).

    res: result with elno and noeu at index; cells: 0-based cell numbers
    (the solid group). Returns (eta per cell, relative error [%]).
    The ELNO rows follow the cell order with one row per cell node
    (aster_results_export._cell_layout, same storage).
    """
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
    ncell = len(conn)
    nbpt = np.array([sfe.getNumberOfPointsOfCell(c)
                     if sfe.getNumberOfComponentsForSubpointsOfCell(c) > 0
                     else 0 for c in range(ncell)])
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
    return np.sqrt(eta2), rel


def dorfler(eta, theta):
    """Indices of the fewest cells that carry the fraction theta of
    sum eta^2 (Doerfler 1996, as bridge_adapt 'dorfler')."""
    order = np.argsort(-eta)
    cum = np.cumsum(eta[order] ** 2)
    if len(cum) == 0 or cum[-1] <= 0:
        return np.array([], dtype=int)
    n = int(np.searchsorted(cum, theta * cum[-1]) + 1)
    return order[:n]
