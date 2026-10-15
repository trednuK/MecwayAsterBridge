# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_cyclic.py
#
# Responsibility: the steps of the modal analysis with cyclic
# symmetry (bridge_cyclic.py) that run INSIDE the Code-Aster job
# (CPython 3.11, like aster_results_export.py; NOT in IronPython):
#   collect()  the modes of MODE_ITER_CYCL (via REST_SOUS_STRUC SECTEUR=1)
#              in Mecway's order as a MODE_MECA result on the
#              sector, or (setting cyclic_full_wheel) on the full wheel
#              (REST_SOUS_STRUC SQUELETTE), back in the global
#              coordinate system of the model, with a line BRIDGE_MODE <nr>
#              FREQ=.. ND=.. per mode.
#   wheel_model(), node_rows()  the full wheel in Mecway's numbering
#              (also used by aster_results_export).
#
# THE FULL WHEEL AS IN MECWAY (measured headless with Mecway 33 on
# TestFiles/Verificatie/modellen/CY-01, CY-04, CY-05, Samples/Impeller and
# variants with two elsets, a loose node and swapped master/slave):
# the <solution> contains N copies of the model. Sector j (0 .. N-1) is the
# sector rotated by +j x 360/N degrees (right-hand positive about the axis
# through the origin, regardless of which side is master); node i of
# sector j is called i + j x n (n = number of nodes of the model), element
# e is e + j x ne (ne = highest element number). Every node is
# copied, including those on the cut faces and on the axis (duplicated,
# not merged). Per elset the elements are listed sector by sector
# (sector 0, 1, ...). Code-Aster's skeleton (DEFI_SQUELETTE CYCLIQUE,
# SECTEUR TOUT='OUI') has (seen with CY-01) the same layout: N x n
# nodes, block j = the sector rotated by +j x 360/N about Z, and on block j
# the field of REST_SOUS_STRUC SECTEUR=j+1 rotated to that block;
# node_rows() still matches the nodes by coordinate.
#
# Order (measured with Code-Aster 17.4, test case sdls04a and the ring of
# docs/Verificatie.md, CY): REST_SOUS_STRUC SECTEUR=1 gives the modes per
# number of nodal diameters (ND) in the order of CALCUL NB_DIAM/TOUT_DIAM
# (0, 1, ..., N/2), NMAX_FREQ modes per ND; for 0 < ND < N/2 each
# mode appears twice (the pair of standing waves cos/sin, same FREQ), for
# ND 0 and ND N/2 once. Within an ND they are not always ascending
# (seen: 1420.8 before 1404.7 Hz). Mecway (manual v33 par. 9.41, checked
# headless) gives the requested number of modes per ND, each once,
# ascending in ND and within an ND in frequency: collect() does the same
# (the first member of a pair).
#
# Do not use f-strings: same style as the rest of the bridge.

# Computation frame: MODE_ITER_CYCL requires the Z axis as symmetry axis
# (U4.52.05 par. 1). For an X or Y axis the .comm first rotates the mesh
# with a cyclic permutation of the axes (MODI_MAILLAGE ROTATION 120
# degrees about (1, 1, 1); bridge_cyclic.ROTATION):
#   axis Y: p' = (z, x, y), so u = (u'_y, u'_z, u'_x);
#   axis X: p' = (y, z, x), so u = (u'_z, u'_x, u'_y).
# _BACK: the components of the computation frame that become DX, DY, DZ
# of the model.
from aster_results_export import tr   # language of the messages

_BACK = {"Z": ("DX", "DY", "DZ"), "Y": ("DY", "DZ", "DX"),
         "X": ("DZ", "DX", "DY")}
_AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}

# Matching of the nodes by coordinate (node_rows): within _MATCH x the
# model size (the bridge sets coordinates < 1e-12 x the model size to 0,
# bridge_cyclic._rewrite_mesh; rotating gives ~1e-16).
_MATCH = 1.0e-6


# ==========================================
# THE FULL WHEEL (Mecway's numbering, see the header)
# ==========================================
def wheel_coords(coords, axis, n_sectors):
    """(N x n, 3) array: row j x n + i = node i+1 of sector j, rotated
    by +j x 360/N degrees about the axis (index 0/1/2 = X/Y/Z) through the
    origin (like bridge_cyclic._rotate)."""
    import numpy as np
    coords = np.asarray(coords, dtype=float)
    i, k = (axis + 1) % 3, (axis + 2) % 3
    out = []
    for j in range(n_sectors):
        a = 2.0 * np.pi * j / n_sectors
        c, s = np.cos(a), np.sin(a)
        q = coords.copy()
        q[:, i] = c * coords[:, i] - s * coords[:, k]
        q[:, k] = s * coords[:, i] + c * coords[:, k]
        out.append(q)
    return np.concatenate(out)


def wheel_model(model, axis, n_sectors):
    """
    The model of aster_results_export.read_liml_model ("coords",
    "elsets", "elements") extended to the full wheel in Mecway's
    numbering: node i + j x n, element e + j x ne (ne = highest
    element number), per elset the sectors one after another.
    """
    from collections import OrderedDict
    n = model["coords"].shape[0]
    ne = max(model["elements"]) if model["elements"] else 0
    elements = {}
    elsets = OrderedDict()
    for name, eids in model["elsets"].items():
        out = elsets[name] = []
        for j in range(n_sectors):
            for e in eids:
                shape, nids = model["elements"][e]
                elements[e + j * ne] = (shape, [m + j * n for m in nids])
                out.append(e + j * ne)
    return {"coords": wheel_coords(model["coords"], axis, n_sectors),
            "elsets": elsets, "elements": elements}


def node_rows(mesh_xyz, coords):
    """
    (rows, error): rows[i] = the node (row) of the mesh at the location of
    node i+1 of coords (within _MATCH x the model size), or (None,
    message). First the identical order (that is how Code-Aster builds the
    skeleton), otherwise by coordinate (grid with the neighbouring cells).
    """
    import numpy as np
    mesh_xyz = np.asarray(mesh_xyz, dtype=float).reshape(-1, 3)
    coords = np.asarray(coords, dtype=float)
    size = max(1.0e-30, float(np.abs(coords).max()) if coords.size else 0.0)
    tol = _MATCH * size
    if mesh_xyz.shape == coords.shape and \
            float(np.abs(mesh_xyz - coords).max()) <= tol:
        return np.arange(coords.shape[0]), None
    cells = {}
    keys = np.floor(mesh_xyz / tol).astype(np.int64)
    for r, key in enumerate(map(tuple, keys)):
        cells.setdefault(key, []).append(r)
    rows = np.empty(coords.shape[0], dtype=np.int64)
    for i, p in enumerate(coords):
        k0 = np.floor(p / tol).astype(np.int64)
        best, dist = None, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for r in cells.get((k0[0] + dx, k0[1] + dy, k0[2] + dz),
                                       ()):
                        d = float(np.abs(mesh_xyz[r] - p).max())
                        if dist is None or d < dist:
                            best, dist = r, d
        if best is None or dist > tol:
            return None, tr("knoop {0} van het wiel ({1}) niet in het mesh "
                            "van het resultaat",
                            "node {0} of the wheel ({1}) not in the mesh of "
                            "the result").format(i + 1, tuple(p))
        rows[i] = best
    return rows, None


def _multiplicity(nd, n_sectors):
    """1 for ND 0 and ND N/2 (one standing wave), otherwise 2 (pair)."""
    return 1 if (nd == 0 or 2 * nd == n_sectors) else 2


def mode_table(freqs, n_sectors, nmax_freq, diameters):
    """
    [(frequency, position in REST_SOUS_STRUC (0-based), ND)] in Mecway's
    order, or None if the number of modes does not match the order
    above (then the ND cannot be determined).
    """
    expected = sum(nmax_freq * _multiplicity(d, n_sectors)
                   for d in diameters)
    if len(freqs) != expected:
        return None
    out = []
    k = 0
    for d in diameters:
        group = []
        mult = _multiplicity(d, n_sectors)
        for _j in range(nmax_freq):
            group.append((float(freqs[k]), k, d))
            k += mult
        group.sort()
        out.extend(group)
    return out


def _attach(modsec, mesh, numbering):
    """
    In the Python layer of Code-Aster 17.4 the result of REST_SOUS_STRUC
    SECTEUR=1 has no mesh and no fields: getFieldsNames() was empty,
    getField() gave KeyError and CREA_CHAMP EXTR <EXCEPTION> JEVEUX_26 (no
    mesh, seen). With setMesh, setDOFNumbering (the numbering of the
    sector basis, onto which REST_SOUS_STRUC writes the fields) and build()
    the DEPL fields are readable (seen; build() then reports "NUME_EQUA
    already exists", harmless).
    """
    modsec.setMesh(mesh)
    modsec.setDOFNumbering(numbering)
    try:
        modsec.build()
    except Exception as e:
        if "already exists" not in str(e):
            raise


def _rotate_back(target, axis, angle):
    """Mesh or skeleton back to the coordinate system of the model
    (MODI_MAILLAGE ROTATION about (1, 1, 1) by -angle degrees)."""
    from code_aster.Commands import MODI_MAILLAGE
    if axis != "Z":
        MODI_MAILLAGE(reuse=target, MAILLAGE=target,
                      ROTATION={"POIN_1": (0.0, 0.0, 0.0),
                                "DIR": (1.0, 1.0, 1.0),
                                "ANGLE": -float(angle)})


def _modes_on(source, target, table, axis):
    """MODE_MECA on mesh target with the DEPL fields of result source in
    the order of table (mode_table), components back (_BACK)."""
    from code_aster.Commands import CREA_CHAMP, CREA_RESU
    orders = list(source.getAccessParameters()["NUME_ORDRE"])
    affe = []
    for k, (f, pos, _nd) in enumerate(table):
        fld = source.getField("DEPL", orders[pos])
        # A separate field on the mesh (also for the Z axis), without the
        # Lagrange DOFs of the sector basis, with the components back in
        # the coordinate system of the model.
        new = CREA_CHAMP(OPERATION="ASSE", TYPE_CHAM="NOEU_DEPL_R",
                         MAILLAGE=target,
                         ASSE={"CHAM_GD": fld, "TOUT": "OUI",
                               "NOM_CMP": _BACK[axis],
                               "NOM_CMP_RESU": ("DX", "DY", "DZ")})
        affe.append({"NOM_CHAM": "DEPL", "CHAM_GD": new,
                     "NUME_MODE": k + 1, "FREQ": f})
    return CREA_RESU(OPERATION="AFFE", TYPE_RESU="MODE_MECA", AFFE=affe)


def _wheel(wheel, skeleton, table, axis, angle, n_sectors, liml):
    """
    The modes on the full wheel (REST_SOUS_STRUC SQUELETTE on the skeleton
    of DEFI_SQUELETTE CYCLIQUE), or (None, reason). Check beforehand: same
    frequencies as the sector, and every node of Mecway's wheel (wheel_model
    on the .liml) has a skeleton node at the same location.
    """
    import numpy as np
    import aster_results_export
    acc = wheel.getAccessParameters()
    freqs = [float(f) for f in acc["FREQ"]]
    if len(freqs) <= max(pos for _f, pos, _nd in table):
        return None, tr("{0} modes op het skelet",
                        "{0} modes on the skeleton").format(len(freqs))
    worst = max(abs(freqs[pos] - f) / max(abs(f), 1.0)
                for f, pos, _nd in table)
    if worst > 1.0e-9:
        return None, tr("andere frequenties op het skelet ({0:.3g})",
                        "different frequencies on the skeleton "
                        "({0:.3g})").format(worst)
    _rotate_back(skeleton, axis, angle)
    model = aster_results_export.read_liml_model(liml)
    coords = wheel_coords(model["coords"], _AXIS_INDEX[axis], n_sectors)
    xyz = np.asarray(skeleton.getCoordinates().getValues(), dtype=float)
    rows, err = node_rows(xyz, coords)
    if err:
        return None, err
    order = "zelfde volgorde" if (len(rows) == len(xyz) // 3 and np.all(
        rows == np.arange(len(rows)))) else "op coordinaat gekoppeld"
    print("aster_cyclic: hele wiel: {0} sectoren, {1} knopen ({2}).".format(
        n_sectors, len(rows), order))
    return _modes_on(wheel, skeleton, table, axis), None


def collect(modsec, mesh, numbering, n_sectors, nmax_freq, diameters,
            axis="Z", angle=0.0, wheel=None, skeleton=None, liml=None):
    """
    MODE_MECA with the modes in Mecway's order (mode_table), in the
    coordinate system of the model: on the full wheel if wheel
    (REST_SOUS_STRUC SQUELETTE), skeleton (the skeleton) and liml (the
    model's .liml) are given and the wheel checks out (_wheel), otherwise
    on the sector (mesh). numbering: the NUME_DDL of the sector basis
    (_attach). axis: "X", "Y" or "Z" (the symmetry axis in Mecway); for X/Y
    mesh and skeleton rotate back (MODI_MAILLAGE ROTATION about (1, 1, 1)
    by -angle degrees) and the DEPL components are restored (_BACK). Prints
    BRIDGE_MODE <nr> FREQ=<Hz> ND=<k> (bridge_results_liml.read_mode_summary)
    per mode and BRIDGE_CYCL N=.. NMAX_FREQ=.. MODES=.. WIEL=0|1.
    """
    _attach(modsec, mesh, numbering)
    acc = modsec.getAccessParameters()
    freqs = list(acc["FREQ"])
    table = mode_table(freqs, n_sectors, nmax_freq, diameters)
    if table is None:
        print(tr("aster_cyclic: WAARSCHUWING: {0} modes uit "
                 "MODE_ITER_CYCL, verwacht {1}; de nodal diameters zijn "
                 "onbekend en alle modes gaan op volgorde naar Mecway.",
                 "aster_cyclic: WARNING: {0} modes from MODE_ITER_CYCL, "
                 "expected {1}; the nodal diameters are unknown and all "
                 "modes go to Mecway in order.").format(
                  len(freqs), sum(nmax_freq * _multiplicity(d, n_sectors)
                                  for d in diameters)))
        table = [(float(f), k, -1) for k, f in enumerate(freqs)]
    res = None
    if wheel is not None and skeleton is not None and liml:
        try:
            res, why = _wheel(wheel, skeleton, table, axis, angle,
                              n_sectors, liml)
        except Exception as e:
            res, why = None, repr(e)
        if res is None:
            print(tr("aster_cyclic: WAARSCHUWING: het hele wiel is niet "
                     "opgebouwd ({0}); naar Mecway gaat alleen de sector.",
                     "aster_cyclic: WARNING: the whole wheel was not built "
                     "({0}); only the sector goes to Mecway.").format(why))
    full = res is not None
    if res is None:
        _rotate_back(mesh, axis, angle)
        res = _modes_on(modsec, mesh, table, axis)
    for k, (f, _pos, nd) in enumerate(table):
        print("BRIDGE_MODE {0} FREQ={1!r} ND={2}".format(k + 1, f, nd))
    print("BRIDGE_CYCL N={0} NMAX_FREQ={1} MODES={2} WIEL={3}".format(
        n_sectors, nmax_freq, len(table), 1 if full else 0))
    return res
