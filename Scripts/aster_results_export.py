# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_results_export.py
#
# Responsibility: writes the results of a Code-Aster run directly
# in Mecway's own result format (the <results> element inside
# <solution> of a .liml). Runs INSIDE the Code-Aster job (CPython 3.11
# with numpy 1.26, shipped with Code-Aster 17.4), NOT in IronPython.
#
# ROUTE ("binary", replaces the POST_RELEVE_T tables for large models):
#   1. After CALC_CHAMP the .comm calls export_results():
#          import sys
#          sys.path.insert(0, r"<repo>\Scripts")
#          import aster_results_export
#          aster_results_export.export_results(
#              res, r"<workdir>\<model>_<run_id>_results.xml",
#              r"<model>.liml",
#              fields=["displacements", "stresses", "vonmises", "reactions"],
#              extra_results={"res_sup": res_sup, "res_moy": res_moy,
#                             "res_inf": res_inf})
#      That writes a fragment <results precision="single">...</results>
#      with all archived time steps (res.getIndexes()).
#   2. IronPython (bridge_results_liml.splice_results) puts the fragment in
#      the <solution> of the .liml itself (previous version .bak); Mecway
#      reopens it with mw.open(). The file is kept (button Results...).
#      As a fallback bridge_results_liml.read_step() reads one time step for
#      the existing solution.set_variable() route.
#
# MECWAY FORMAT (derived from .liml files saved by Mecway 33 itself:
# an OpenRadioss model with 61 time steps (single) and a
# static CCX model (double); all rules below were checked there with a
# script):
#   <results precision="single">            ("double": float64, valuesdouble)
#     <nodeids name="var">   base64 int32 LE: node numbers with a value,
#                            ascending; per variable (e.g. stressxx only
#                            on volume nodes, rotx only on beam/shell).
#     <elementnodeids name="var">  base64 int32: element numbers, ascending.
#     <timestep id="k" time="t s">          (missing in a static
#                                            analysis: variables then
#                                            directly under <results>)
#       <nodevariable name="var">
#         <maxandmin><component name="elset" max=".." min=".." />...
#           Per elset (model order) max/min over the nodes of
#           that elset that are in nodeids; component name="" (first) for
#           nodes that are in no element at all. Elsets without values
#           are left out.
#         <valuessingle> base64 float32 LE, in the order of nodeids.
#         <nodes /><values />
#       <elementnodevariable name="var">
#         maxandmin per elset over the values of its elements;
#         values per element (order elementnodeids) for each node in the
#         order of the nodes attribute of <elem> (static CCX
#         results: only that order gives the same value per node in
#         adjacent elements); then <elements /><values />.
#   Base64 is in lines of 64 characters (CRLF), with a CRLF before the
#   closing tag. Numbers in max/min: 15 significant digits, as Mecway.
#
# MODES (CALC_MODES; checked in examples solved headless by Mecway 33
# VibratingCantileverBeam/-Solid/-FreePlate (V30) and
# BucklingBeam/-Plate (B30)): instead of <timestep> one block per mode,
#     <mode id="1" frequency="7.07368492123229 Hz">   (V30, id from 1)
#     <mode id="1" bucklingfactor="41124.6991224029">  (B30, without unit)
# with the same <nodevariable> blocks, precision="double". For V30 Mecway
# writes only displx/y/z (+ rotx/y/z for beams/shells), without
# displmag; for B30 with displmag. Mecway's API reads them with
# solution.modes(), solution.frequency(m) / buckling_factor(m) and
# node_value(var, nid, mode=m) (checked with a headless Mecway script).
# For real and complex MODE_MECA the effective mass per mode is a
# <globalvariable> directly after <mode> (as Mecway, see _MW_DIRS).
#
# FILE SIZES (measured; details in bridge_results_liml.py): a
# fragment costs ~5.6 bytes per value, the .resu tables ~53 bytes. Hex8
# block 18,225 nodes x 51 steps: fragment 78 MB in 1.6 s, .resu 644 MB
# (POST_RELEVE_T + IMPR_TABLE ~80 s), study.rmed 217 MB.
#
# CYCLIC SYMMETRY, THE WHOLE WHEEL (S10i): export_results(cyclic=...) with
# a result on the skeleton (aster_cyclic.collect) writes nodal fields
# for the N x n nodes of Mecway's own cyclic solution (node i of
# sector j = i + j x n, aster_cyclic.wheel_model); the maxandmin per elset
# cover all sectors. The nodes and elements themselves are put into the
# model copy of <solution> by bridge_results_liml.splice_results.
#
# Node order: bridge_mesh.write_mesh writes N1..NN in order of the
# node number and Code-Aster numbers the nodes in reading order; row i of a
# field is thus Mecway node i+1. export_results checks that with the
# coordinates (mesh.getCoordinates() against the .liml). Elements: after
# LIRE_MAILLAGE Code-Aster no longer knows names via the Python API
# (getCellName does not exist in v17.4, sdj.NOMMAI.get() gives None;
# checked), so a cell is linked to the Mecway element via its node set and
# the node of each ELNO point follows from mesh.getConnectivity(). Tested:
# the nodal average of the SIGM_ELNO ordered this way equals SIGM_NOEU
# (hex8, hex20); with reversed order it does not.
#
# ELEMENT NODE STRESSES require SIGM_ELNO (and SIEQ_ELNO) in res. Note,
# with volume + shells: request SIGM_ELNO ONCE over both groups
# (CALC_CHAMP GROUP_MA=(volume, shells), CONTRAINTE=('SIGM_ELNO',)) before
# the call with SIGM_NOEU. Requesting it on the volume only means the later
# CALC_CHAMP on the shells does not extend the existing field and then
# POST_CHAMP EXTR_COQUE fails (CALCULEL2_15); tested on the mixed model ME.
#
# Do not use f-strings: same style as the rest of the bridge.

import base64
import os
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict

import numpy as np


# ==========================================
# LANGUAGE OF THE MESSAGES
#
# The job scripts do not know CONFIG_BRIDGE. bridge_to_aster._write_comm
# sets os.environ[LANGUAGE_ENV] to CONFIG_BRIDGE["language"] in study.comm
# (before DEBUT); tr() reads it on every call. Without the
# variable (an old .comm, a test) "en" applies, the default of the
# bridge. Also used by aster_cyclic, aster_acoustic_*, aster_harmonic_
# export, aster_spectrum and aster_fatigue.
# ==========================================
LANGUAGE_ENV = "BRIDGE_LANGUAGE"


def tr(nl, en):
    """Text in the language of the run: nl if BRIDGE_LANGUAGE is "nl", else
    en (same placeholders; WAARSCHUWING/FOUT in nl, WARNING/ERROR in en)."""
    return nl if os.environ.get(LANGUAGE_ENV, "en") == "nl" else en


# ==========================================
# FIELD TABLE
#
# Mirror of RESULT_FIELD_SPECS / STRUCT_FIELD_SPECS in
# bridge_from_aster.py: (group, result, Code-Aster field, component,
# Mecway name, kind).
#   group     : key from RESULT_FIELD_SPECS (= CONFIG_BRIDGE
#               analyses[...]["fields"]); shell/beam fields under their
#               parent field as in STRUCT_FIELD_SPECS.
#   result    : "res" or a key from extra_results (res_sup, ...).
#   kind      : KNOOP      nodal field (..._NOEU, DEPL, VITE, REAC_NODA)
#               ELNO_MIN / ELNO_MAX  ELNO field, per node min/max over the
#                          adjacent elements (as beam_sixx)
#               ELEMKNOOP  ELNO field as Mecway elementnodevariable
#                          (volume elements only). Only if the field
#                          is in res: CALC_CHAMP CONTRAINTE=('SIGM_ELNO',)
#                          / CRITERES=('SIEQ_ELNO',) must compute it.
#               ELEMKNOOP_LIJN  same for line2/line3 (beams: EFGE_ELNO)
# Derived fields (shell tensor, shell strain and forces, factor of safety,
# contact status) are not in this table: _plan_derived.
# The Code-Aster order of the stress components is SIXX SIYY SIZZ SIXY
# SIXZ SIYZ (checked with getComponents()); the mapping is by name.
# ==========================================
KNOOP = "knoop"
ELNO_MIN = "elno_min"
ELNO_MAX = "elno_max"
ELEMKNOOP = "elementknoop"
ELEMKNOOP_LIJN = "elementknoop_lijn"

_STRESS_CMPS = (("SIXX", "xx"), ("SIYY", "yy"), ("SIZZ", "zz"),
                ("SIXY", "xy"), ("SIYZ", "yz"), ("SIXZ", "zx"))
_XYZ = (("DX", "x"), ("DY", "y"), ("DZ", "z"))
_RXYZ = (("DRX", "x"), ("DRY", "y"), ("DRZ", "z"))
_EPS_CMPS = (("EPXX", "xx"), ("EPYY", "yy"), ("EPZZ", "zz"),
             ("EPXY", "xy"), ("EPYZ", "yz"), ("EPXZ", "zx"))

FIELD_TABLE = (
    [("displacements", "res", "DEPL", c, "displ" + s, KNOOP)
     for c, s in _XYZ] +
    [("displacements", "res", "DEPL", c, "rot" + s, KNOOP)
     for c, s in _RXYZ] +
    [("velocities", "res", "VITE", c, "vel" + s, KNOOP) for c, s in _XYZ] +
    # Angular velocity of beam and shell nodes: Mecway's D30 writes
    # angularvelx/y/z (seen headless, Mecway 33; DampedVibratingStrip also
    # angularvelmag).
    [("velocities", "res", "VITE", c, "angularvel" + s, KNOOP)
     for c, s in _RXYZ] +
    # Acceleration (ACCE): Mecway has no acceleration field (no name in
    # mecway.exe); own names accelx/y/z of the bridge. Response spectrum
    # (bridge_spectrum.py): the maximum absolute acceleration.
    [("accelerations", "res", "ACCE", c, "accel" + s, KNOOP)
     for c, s in _XYZ] +
    [("stresses", "res", "SIGM_NOEU", c, "stress" + s, KNOOP)
     for c, s in _STRESS_CMPS] +
    [("vonmises", "res", "SIEQ_NOEU", "VMIS", "vonmises", KNOOP),
     ("vonmises", "res_sup", "SIEQ_NOEU", "VMIS", "vonmisesu1", KNOOP),
     ("vonmises", "res_moy", "SIEQ_NOEU", "VMIS", "vonmisesm", KNOOP),
     ("vonmises", "res_inf", "SIEQ_NOEU", "VMIS", "vonmisesb", KNOOP),
     ("stresses", "res", "SIPM_ELNO", "SIXXMIN", "beamsixxmin", ELNO_MIN),
     ("stresses", "res", "SIPM_ELNO", "SIXXMAX", "beamsixxmax", ELNO_MAX)] +
    [("reactions", "res", "REAC_NODA", c, "reactionforce" + s, KNOOP)
     for c, s in _XYZ] +
    [("reactions", "res", "REAC_NODA", c, "reactionmom" + s, KNOOP)
     for c, s in _RXYZ] +
    [("plastic_strain", "res", "EPSP_NOEU", c, "plasticstrain" + s, KNOOP)
     for c, s in _EPS_CMPS] +
    [("plastic_strain_eq", "res", "VARI_NOEU", "V1",
      "equivalentplasticstrain", KNOOP)] +
    [("stresses", "res", "SIGM_ELNO", c, "stress" + s, ELEMKNOOP)
     for c, s in _STRESS_CMPS] +
    [("vonmises", "res", "SIEQ_ELNO", "VMIS", "vonmises", ELEMKNOOP)] +
    # Thermal (bridge_thermal.py): TEMP in degrees Celsius (the bridge
    # computes in Celsius in Code-Aster, see VALUE_OFFSETS) and FLUX_NOEU =
    # -lambda grad T (components FLUX, FLUY, FLUZ; PLAN elements have
    # no FLUZ). Mecway names heatfluxx/y/z/mag checked in Mecway 33
    # (OscillatingHeatFlow: Mecway shows them under "heat flux").
    [("temperature", "res", "TEMP", "TEMP", "temperature", KNOOP),
     # Chain thermal -> mechanical (bridge_thermomech.py): res is the
     # mechanical result, the temperature is in res_ther.
     ("temperature", "res_ther", "TEMP", "TEMP", "temperature", KNOOP)] +
    [("heat_flux", "res_flux", "FLUX_NOEU", c, "heatflux" + s, KNOOP)
     for c, s in (("FLUX", "x"), ("FLUY", "y"), ("FLUZ", "z"))] +
    # Metallurgy (bridge_metallurgy.py, CALC_META): META_NOEU V1..V5 =
    # phase fractions ferrite, pearlite, bainite, martensite, austenite
    # (Behaviours/acier.py; seen in a run), DURT_NOEU HV = hardness.
    # In the thermal result res, in the chain in res_ther. Own names
    # of the bridge (Mecway has no phases).
    [("metallurgy", r, "META_NOEU", "V%d" % (i + 1), name, KNOOP)
     for r in ("res", "res_ther")
     for i, name in enumerate(("ferrite", "pearlite", "bainite",
                               "martensite", "austenite"))] +
    [("metallurgy", r, "DURT_NOEU", "HV", "hardness", KNOOP)
     for r in ("res", "res_ther")] +
    # Error estimator (bridge_to_aster._error_estimator_block, result
    # res_err): ERREST = absolute estimate eta_e, NUEST = local relative
    # (%). ERME_NOEU = nodal average; ERME_ELNO is constant per element,
    # so as elementnodevariable the real element value (volume
    # elements only). Own names of the bridge (Mecway has no error field).
    [("error_estimate", "res_err", "ERME_NOEU", "ERREST", "errorestimate",
      KNOOP),
     ("error_estimate", "res_err", "ERME_NOEU", "NUEST", "errorestimaterel",
      KNOOP),
     ("error_estimate", "res_err", "ERME_ELNO", "ERREST", "errorestimate",
      ELEMKNOOP),
     ("error_estimate", "res_err", "ERME_ELNO", "NUEST", "errorestimaterel",
      ELEMKNOOP)] +
    # Acoustic cavity modes (bridge_acoustic.py, MODE_ACOU): field PRES,
    # component PRES (seen in a run). Mecway's name "pressure" (headless
    # A30 solution). No entry in RESULT_FIELD_SPECS: there is nothing to
    # choose (bridge_acoustic always asks for ["pressure"]).
    [("pressure", "res", "PRES", "PRES", "pressure", KNOOP)] +
    # Vibro-acoustics (bridge_vibroacoustic.py, 3D_FLUIDE U_P_PHI): the
    # pressure is component PRES of DEPL (only on the fluid nodes).
    [("pressure", "res", "DEPL", "PRES", "pressure", KNOOP)] +
    # Total strain of volume elements (bridge_to_aster._strain_blocks).
    # Mecway names (seen headless, Mecway 34): linear (S30, D30, V30)
    # lstrainxx..lstrainzx, nonlinear (L30, D31, CCX) greenlagrange-
    # strainxx..; shear components are the engineering shear angle
    # gamma = 2 eps (measured: simple shear, lstrainzx =
    # tau/G), Code-Aster's EPXY/EPXZ/EPYZ are tensor components
    # (VALUE_SCALES). EPSI = small strains, EPSG = Green-Lagrange
    # (catalog calc_champ.py, DEFORMATION).
    [("strain", "res", f, c, n + s, k)
     for f, n, k in (("EPSI_NOEU", "lstrain", KNOOP),
                     ("EPSI_ELNO", "lstrain", ELEMKNOOP),
                     ("EPSG_NOEU", "greenlagrangestrain", KNOOP),
                     ("EPSG_ELNO", "greenlagrangestrain", ELEMKNOOP))
     for c, s in _EPS_CMPS] +
    # Section forces of beams (EFGE_ELNO/EFGE_NOEU, POU_D_E/POU_D_T,
    # local axes: x along the beam, y = Mecway's V, z = W; see
    # bridge_to_aster._build_cara_elem_block). Mecway names and signs
    # checked headless (Mecway 34, clamped beam with force and
    # moment at the tip, also inclined): tensileforce = N, sheary = VY,
    # shearz = VZ, torsion = MT, bendingmomv = MFY, bendingmomw = MFZ.
    # Large-rotation beams (POU_D_T_GD): the same components in
    # SIEF_NOEU/SIEF_ELNO (EFGE_ELNO stops with DVP_1 there, Code-Aster
    # 17.4; bridge_to_aster._optional_field_blocks). Only used where EFGE_* is
    # missing (one beam formulation per model, elem_beam).
    [("beam_forces", "res", f, c, name, k)
     for f, k in (("EFGE_NOEU", KNOOP), ("EFGE_ELNO", ELEMKNOOP_LIJN),
                  ("SIEF_NOEU", KNOOP), ("SIEF_ELNO", ELEMKNOOP_LIJN))
     for c, name in (("N", "tensileforce"), ("VY", "sheary"),
                     ("VZ", "shearz"), ("MT", "torsion"),
                     ("MFY", "bendingmomv"), ("MFZ", "bendingmomw"))] +
    # Contact pressure (DEFI_CONTACT CONTINUE): the Lagrange multiplier
    # LAGS_C of DEPL on the slave nodes is the contact pressure, negative in
    # compression (test case forma04b: "Pression de contact"; measured in the
    # patch test NL-03: LAGS_C = -p). Mecway: contactpressure, positive in
    # compression (CCX solution seen headless). Contact status: _plan_derived.
    [("contact", "res", "DEPL", "LAGS_C", "contactpressure", KNOOP)]
)

# Groups that are only included if chosen: their fields are sometimes
# always in the result (LAGS_C in DEPL, SIGM_ELNO of shells in res_sup),
# and without "fields" (static, nonlinear) export_results writes everything
# there is. bridge_to_aster._results_route passes the chosen groups
# (opt_in).
OPT_IN_GROUPS = frozenset(["strain", "beam_forces", "shell_stresses",
                           "shell_forces", "safety_factor", "contact"])

# Fixed factor per Mecway variable (value = Code-Aster x factor), not
# needed after VALUE_OFFSETS (no overlap): contact pressure positive in
# compression, shear strain as engineering shear angle (see FIELD_TABLE).
VALUE_SCALES = dict(
    [("contactpressure", -1.0)] +
    [(p + s, 2.0) for p in ("lstrain", "greenlagrangestrain")
     for s in ("xy", "yz", "zx")])

# Lower bound per Mecway variable (after VALUE_SCALES): contact pressure is
# never negative. With PENALISATION LAGS_C is positive on open slave nodes
# (seen in NL-03b: up to +3e4 Pa next to closed nodes), so -LAGS_C < 0;
# Mecway (CCX) shows 0 there.
VALUE_MIN = {"contactpressure": 0.0}

# Contact status without CONT_NOEU: closed above this fraction of the
# largest contact pressure (_contact_state_var).
CONTACT_CLOSED = 0.01

# Factor of safety at von Mises = 0 (unloaded): a large finite value
# (Mecway shows up to 15 by default, manual v34 sec. 8.7).
FOS_MAX = 1.0e6

# Fixed offset per Mecway variable (value = Code-Aster + offset).
# Code-Aster's RAYONNEMENT computes with T + 273.15 (U4.44.02: temperatures
# in degrees Celsius), so the thermal computation is in Celsius and Mecway
# gets Kelvin.
VALUE_OFFSETS = {"temperature": 273.15}

# Magnitude of a vector; Mecway puts the magnitude before the components.
MAGNITUDES = OrderedDict([
    ("displmag", ("displx", "disply", "displz")),
    ("velmag", ("velx", "vely", "velz")),
    ("accelmag", ("accelx", "accely", "accelz")),
    ("angularvelmag", ("angularvelx", "angularvely", "angularvelz")),
    ("reactionforcemag",
     ("reactionforcex", "reactionforcey", "reactionforcez")),
    ("reactionmommag", ("reactionmomx", "reactionmomy", "reactionmomz")),
    ("heatfluxmag", ("heatfluxx", "heatfluxy", "heatfluxz")),
])

# Components that may be missing in a magnitude (then 0): FLUZ does not
# exist on PLAN elements (shells in a plane Z = constant, bridge_thermal.py).
OPTIONAL_PARTS = frozenset(["heatfluxz"])

SOLID_SHAPES = frozenset(["hex8", "hex20", "tet4", "tet10", "pyr5", "pyr13",
                          "wedge6", "wedge15"])
SHELL_SHAPES = frozenset(["tri3", "quad4", "tri6", "quad8"])
LINE_SHAPES = frozenset(["line2", "line3"])

_NL = b"\r\n"            # Mecway writes CRLF
_B64_LINE = 64           # base64 line length in Mecway's .liml


# ==========================================
# MODEL FROM THE .LIML
# ==========================================
def read_liml_model(liml_path):
    """
    Read nodes, elsets and elements of the model (top level, not the
    copy in <solution>; reading stops at <solution>).

    Returns
    -------
    dict with
      "coords"   : np.ndarray (N, 3), row i = node i+1
      "elsets"   : OrderedDict {elset name: [eid, ...]} in model order
      "elements" : dict {eid: (shape, [nid, ...])}
      "uaxes"    : dict {eid: (ux, uy, uz)}: Mecway's U direction per
                   element (attributes orientationux/uy/uz, Element
                   properties), only where given
    """
    nodes = {}
    elsets = OrderedDict()
    elements = {}
    uaxes = {}
    depth = 0
    with open(liml_path, "rb") as f:
        for event, el in ET.iterparse(f, events=("start", "end")):
            if event == "start":
                depth += 1
                if depth == 2 and el.tag == "solution":
                    break
                continue
            depth -= 1
            if depth != 1:
                continue
            if el.tag == "node":
                nodes[int(el.get("nid"))] = (float(el.get("x")),
                                             float(el.get("y")),
                                             float(el.get("z")))
            elif el.tag == "elset":
                eids = elsets.setdefault(el.get("name", ""), [])
                for e in el.findall("elem"):
                    eid = int(e.get("eid"))
                    elements[eid] = (e.get("shape"),
                                     [int(n) for n in e.get("nodes").split()])
                    eids.append(eid)
                    keys = ("orientationux", "orientationuy",
                            "orientationuz")
                    if any(e.get(k) is not None for k in keys):
                        uaxes[eid] = tuple(float(e.get(k, "0"))
                                           for k in keys)
            el.clear()
    n = max(nodes) if nodes else 0
    if sorted(nodes) != list(range(1, n + 1)):
        raise ValueError(tr("Knoopnummers in {0} zijn niet 1..N "
                            "aaneengesloten.",
                            "Node numbers in {0} are not contiguous "
                            "1..N.").format(liml_path))
    coords = np.array([nodes[i] for i in range(1, n + 1)], dtype=float)
    return {"coords": coords, "elsets": elsets, "elements": elements,
            "uaxes": uaxes}


def _check_node_order(mesh, coords):
    """
    Check that row i of the Code-Aster mesh is node i+1 of the .liml
    (same coordinates). Returns an error message (str) or None.
    """
    xyz = np.asarray(mesh.getCoordinates().getValues(), dtype=float)
    xyz = xyz.reshape(-1, 3)
    if xyz.shape[0] < coords.shape[0]:
        return tr("Mesh heeft {0} knopen, de .liml {1}.",
                  "Mesh has {0} nodes, the .liml {1}.").format(
            xyz.shape[0], coords.shape[0])
    size = max(1.0, float(np.abs(coords).max()))
    diff = float(np.abs(xyz[:coords.shape[0]] - coords).max())
    if diff > 1.0e-9 * size:
        return tr("Knoopvolgorde van het mesh wijkt af van de .liml (max. "
                  "coordinaatverschil {0}).",
                  "Node order of the mesh differs from the .liml (max. "
                  "coordinate difference {0}).").format(diff)
    return None


# ==========================================
# FIELDS PER TIME STEP (cache: convert each field once)
# ==========================================
class _Fields(object):
    """Converts each requested field once per time step to numpy."""

    def __init__(self, results, n_nodes, lump=None, rows=None, pairs=None):
        self.results = results
        self.n = n_nodes
        self.lump = lump      # _reaction_lumping(): REAC_NODA extra nodes
        # _offset_pairs(): (Mecway node, node of the offset element,
        # arm) of an element offset, or None
        self.pairs = pairs
        # rows: mesh row per Mecway node (whole wheel for cyclic
        # symmetry, aster_cyclic.node_rows); None = row i is node i+1.
        self.rows = rows
        self.index = None
        self.data = {}
        self.layouts = {}     # (result, field) -> _cell_layout()
        self.scales = {}      # {index: factor} for DEPL (buckling modes)
        # Mecway node index per mesh node (_node_alias), or None (whole
        # wheel, cyclic: nodal fields only)
        self.alias = None

    def set_index(self, index):
        self.index = index
        self.data = {}

    def get(self, rkey, field, on_cells):
        """(components, values, mask, simple field) or None if the field
        is missing in this time step. Nodal fields: only the first n rows
        (= Mecway nodes 1..n; extra mesh nodes are dropped)."""
        key = (rkey, field)
        if key not in self.data:
            self.data[key] = None
            try:
                fld = self.results[rkey].getField(field, self.index)
                if on_cells:
                    sf = fld.toSimpleFieldOnCells()
                    vals, mask = sf.getValues()
                else:
                    sf = fld.toSimpleFieldOnNodes()
                    vals, mask = sf.getValues()
                    if field == "REAC_NODA" and self.lump is not None:
                        vals, mask = _lump_nodes(vals, mask, self.lump)
                    if self.pairs is not None:
                        vals, mask = _offset_values(
                            field, list(sf.getComponents()), vals, mask,
                            self.pairs)
                    if self.rows is not None:
                        vals, mask = vals[self.rows], mask[self.rows]
                    else:
                        vals, mask = vals[:self.n], mask[:self.n]
                    if (field in ("DEPL", "PRES") and
                            self.index in self.scales):
                        vals = vals * self.scales[self.index]
                    if np.iscomplexobj(vals):
                        # Complex modes (MODE_MECA_C): the real part after
                        # the phase rotation of _complex_modes (scales).
                        vals = vals.real
                self.data[key] = (list(sf.getComponents()), vals, mask, sf)
            except Exception:
                pass
        return self.data[key]


# ==========================================
# REACTIONS OF EXTRA NODES (LINE_QUAD, QUAD9/TRIA7)
# ==========================================
def _reaction_lumping(mesh, conn, n, offset_nodes=None):
    """
    Distribution of the nodal reactions of mesh nodes unknown to Mecway
    (index >= n: middle nodes of CREA_MAILLAGE LINE_QUAD, centre node of
    QUAD9/TRIA7 for COQUE_3D) over Mecway nodes, so that the sum of the
    reactions stays the same (otherwise they were lost: HexCantilever with
    LINE_QUAD gave sum Fz 752.6 N for a 100 N load).
      - centre node QUAD9/TRIA7 (last node of the cell; corner nodes
        first, Code-Aster order): 1/4 resp. 1/3 to each corner node;
      - middle node of an edge: 1/2 to each of the two end nodes. The
        edge follows from the geometry (middle of two Mecway nodes of
        the same cell), as _bridge_lq_nodegroups in bridge_to_aster.
    A force in the middle of an edge or of a parallelogram thus also has
    the same moment about every point. Only for REAC_NODA (averaging a
    displacement would be something else).
    offset_nodes: nodes of offset elements (bridge_offset, >= n);
    they count as corner nodes and then go via _offset_values to their
    Mecway node.
    Returns (src, dst, weight) as numpy arrays, or None without extra
    nodes.
    """
    xyz = np.asarray(mesh.getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    if xyz.shape[0] <= n:
        return None
    known = set() if offset_nodes is None else set(int(i)
                                                   for i in offset_nodes)
    src, dst, wgt = [], [], []
    done = set(known)
    for cn in conn:
        if len(cn) in (7, 9) and cn[-1] >= n and cn[-1] not in done:
            corners = list(cn[:4] if len(cn) == 9 else cn[:3])
            done.add(cn[-1])
            for c in corners:
                src.append(cn[-1])
                dst.append(c)
                wgt.append(1.0 / len(corners))
    # Extra node at the location of a Mecway node (flexible joint,
    # bridge_mesh._flexible_joints): the whole reaction goes to that node
    for m, c in sorted(_coincident_extra(xyz, n).items()):
        if m not in done:
            done.add(m)
            src.append(m)
            dst.append(c)
            wgt.append(1.0)
    rest = set(range(n, xyz.shape[0])) - done
    if rest:
        scale = 1.0e9 / max(1.0e-30, float(np.abs(xyz).max()))

        def key(p):
            return tuple(int(round(c * scale)) for c in p)
        mids = {}
        for cn in conn:
            corners = [c for c in cn if c < n or c in known]
            for i in range(len(corners)):
                for j in range(i + 1, len(corners)):
                    a, b = corners[i], corners[j]
                    mids.setdefault(key(0.5 * (xyz[a] + xyz[b])), (a, b))
        for m in sorted(rest):
            ab = mids.get(key(xyz[m]))
            if ab is None:
                continue
            done.add(m)
            for c in ab:
                src.append(m)
                dst.append(c)
                wgt.append(0.5)
    missing = xyz.shape[0] - n - len(done)
    if missing:
        print(tr("aster_results_export: WAARSCHUWING: {0} extra knopen "
                 "zonder Mecway-hoekknopen; hun reacties vallen weg.",
                 "aster_results_export: WARNING: {0} extra nodes without "
                 "Mecway corner nodes; their reactions are dropped.").format(
            missing))
    if not src:
        return None
    return (np.array(src, dtype=int), np.array(dst, dtype=int),
            np.array(wgt, dtype=float))


def _coincident_extra(xyz, n, exclude=()):
    """
    {index extra node: index Mecway node} for mesh nodes after the
    Mecway nodes (index >= n) that lie at the same location as a
    Mecway node: the own node of a beam end with a flexible
    joint (bridge_mesh._flexible_joints, coupled to that node with
    LIAISON_DDL). If several Mecway nodes lie there, the lowest.
    exclude: extra nodes that do not take part here (nodes of offset
    elements, _offset_pairs: they belong via the arm to their own
    Mecway node, even if they happen to lie on another Mecway node).
    """
    if xyz.shape[0] <= n:
        return {}
    scale = 1.0e9 / max(1.0e-30, float(np.abs(xyz).max()))

    def key(p):
        return tuple(int(round(c * scale)) for c in p)
    skip = set(int(i) for i in exclude)
    extra = dict((key(xyz[m]), m) for m in range(n, xyz.shape[0])
                 if m not in skip)
    out = {}
    for c in range(n):
        m = extra.get(key(xyz[c]))
        if m is not None and m not in out:
            out[m] = c
    # several extra nodes at the same location (joints on both sides)
    for m in range(n, xyz.shape[0]):
        c = out.get(extra.get(key(xyz[m])))
        if m not in out and m not in skip and c is not None:
            out[m] = c
    return out


def _node_alias(n_mesh, n, coincident, pairs):
    """
    Mecway node index (0-based) per mesh node, -1 for nodes without a
    Mecway node (middle nodes of LINE_QUAD, QUAD9/TRIA7):
      index < n                        : itself;
      own node of a joint              : the Mecway node at that location
                                         (_coincident_extra);
      node of an offset element        : its Mecway node (_offset_pairs;
                                         Mecway: element values of the
                                         offset element at the node).
    """
    alias = np.full(max(n_mesh, n), -1, dtype=int)
    alias[:n] = np.arange(n)
    for m, c in coincident.items():
        alias[m] = c
    if pairs is not None:
        alias[pairs[1]] = pairs[0]
    return alias


def _lump_nodes(vals, mask, lump):
    """Add the values of the extra nodes proportionally to the target
    nodes (_reaction_lumping); components without a value count as 0."""
    src, dst, wgt = lump
    out = np.where(mask, vals, 0.0)
    np.add.at(out, dst, out[src] * wgt[:, None])
    new_mask = mask.copy()
    np.logical_or.at(new_mask, dst, mask[src])
    return out, new_mask


# ==========================================
# ELEMENT OFFSET (bridge_offset): OFFSET NODES -> MECWAY NODES
# ==========================================
# Node groups with this prefix contain exactly one Mecway node and the
# node of the offset element (bridge_offset.LINK_PREFIX).
OFFSET_GROUP_PREFIX = "BROFL"
# Fields that already have the right value on the Mecway node itself (the
# node moves along with the rigid arm).
_KINEMATIC_FIELDS = ("DEPL", "VITE", "ACCE")


def _offset_pairs(mesh, n):
    """
    (o, f, arm) as numpy arrays (0-based node indices, arm = x_f - x_o)
    from the node groups BROFL<k> of bridge_offset, or None without offset.
    mesh.getGroupsOfNodes()/getNodes(group) (test case sdll157a, 17.4).
    """
    try:
        names = [g for g in mesh.getGroupsOfNodes()
                 if str(g).strip().startswith(OFFSET_GROUP_PREFIX)]
    except Exception:
        return None
    if not names:
        return None
    xyz = np.asarray(mesh.getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    orig, new = [], []
    for g in names:
        ids = sorted(int(i) for i in mesh.getNodes(str(g).strip()))
        if len(ids) != 2 or not (ids[0] < n <= ids[1] < xyz.shape[0]):
            continue
        orig.append(ids[0])
        new.append(ids[1])
    if not orig:
        return None
    orig, new = np.array(orig, dtype=int), np.array(new, dtype=int)
    return orig, new, xyz[new] - xyz[orig]


def _offset_values(field, comps, vals, mask, pairs):
    """
    Values of the nodes of offset elements to the Mecway node:
      REAC_NODA: the reaction of the offset node f goes with the moment
          of the arm to the Mecway node o (F_o += F_f, M_o += M_f +
          arm x F_f). The forces of the rigid arm itself (LIAISON_DDL) are
          in equilibrium with each other and so cancel out; what remains is
          the reaction of a support on o (Mecway: reactions on the nodes).
      DEPL/VITE/ACCE: unchanged (o has its own value).
      Other fields (stresses of shells per node): where o has no value,
          the average of its offset nodes (Mecway: the
          element values belong to the offset element).
    """
    orig, new, arm = pairs
    if field in _KINEMATIC_FIELDS:
        return vals, mask
    vals = np.array(vals, dtype=float, copy=True)
    mask = np.array(mask, copy=True)
    if field == "REAC_NODA":
        idx = dict((c, i) for i, c in enumerate(comps))
        out = np.where(mask, vals, 0.0)
        forces = [idx.get(c) for c in ("DX", "DY", "DZ")]
        moments = [idx.get(c) for c in ("DRX", "DRY", "DRZ")]
        f = np.zeros((len(new), 3))
        for k, i in enumerate(forces):
            if i is not None:
                f[:, k] = out[new, i]
                np.add.at(out[:, i], orig, out[new, i])
                out[new, i] = 0.0
        moment = np.cross(arm, f)
        for k, i in enumerate(moments):
            if i is not None:
                np.add.at(out[:, i], orig, out[new, i] + moment[:, k])
                out[new, i] = 0.0
        for i in [j for j in forces + moments if j is not None]:
            np.logical_or.at(mask[:, i], orig, mask[new, i])
        return out, mask
    total = np.zeros((vals.shape[0], vals.shape[1]))
    count = np.zeros((vals.shape[0], vals.shape[1]))
    have = mask[new]
    np.add.at(total, orig, np.where(have, vals[new], 0.0))
    np.add.at(count, orig, have.astype(float))
    fill = (~mask) & (count > 0)
    vals[fill] = total[fill] / count[fill]
    mask = mask | fill
    return vals, mask


# ==========================================
# CELLS -> MECWAY ELEMENTS
# ==========================================
def _cell_layout(sf, conn, nrows):
    """
    Rows of SimpleFieldOnCells.getValues(): only cells WITH components
    have rows, per cell nbpt*nbsp consecutively in cell order (storage
    .CESV, address per cell/point/subpoint as in cesexi.F90). NOTE:
    getNumberOfPointsOfCell() also gives the number of points for cells
    without values (checked: SIGM_ELNO only on shells gave nbpt=8 for
    HEXA8), and getValuesOnCell() in simplefieldoncells_ext.py (v17.4)
    counts those cells; hence getNumberOfComponentsForSubpointsOfCell().

    Returns (start, nbpt, nbsp) per cell (nbpt = 0 for cells without
    values), or None if the layout does not match nrows or a cell has only
    part of the components (then the (rows, ncmp) shape of getValues()
    does not fit; NOT verified how getValues() returns that case).
    """
    ncell = len(conn)
    ncmp = np.array([sf.getNumberOfComponentsForSubpointsOfCell(c)
                     for c in range(ncell)])
    nbpt = np.array([sf.getNumberOfPointsOfCell(c) for c in range(ncell)])
    nbsp = np.array([sf.getNumberOfSubPointsOfCell(c) for c in range(ncell)])
    nbpt = np.where(ncmp > 0, nbpt, 0)
    rows = nbpt * nbsp
    full = len(sf.getComponents())
    if int(rows.sum()) != nrows or np.any((ncmp > 0) & (ncmp != full)):
        return None
    start = np.concatenate([[0], np.cumsum(rows)[:-1]])
    return start, nbpt, nbsp


def _cell_nodes(fields, cn):
    """Mecway node indices (0-based, -1 = none) of the nodes of a
    cell (_node_alias)."""
    if fields.alias is None:
        return [c if c < fields.n else -1 for c in cn]
    return [int(fields.alias[c]) if c < len(fields.alias) else -1
            for c in cn]


_LOST_REPORTED = set()


def _element_points(fields, conn, elements, nbpt, nbsp, label,
                    all_elements=None):
    """
    {eid: [(cell, point) per node of the Mecway element, in the order
    of its nodes attribute]} for cells with an ELNO value per node
    (nbpt equal to the number of nodes, one subpoint). Matched on the
    node set after _cell_nodes:
      - after CREA_MAILLAGE LINE_QUAD a HEXA20 cell has 12 extra
        middle nodes (-1), the 8 corner nodes are those of the element;
      - the cell of an offset element (bridge_offset, rigid route)
        lies on its own nodes, the cell of a beam end with a flexible
        joint starts on its own node: via _node_alias back to the
        Mecway nodes;
      - a split line3 beam (bridge_mesh, two SEG2 cells M<eid> =
        [end 1, middle] and H<eid> = [middle, end 2]): end 1 and middle
        from the first cell, end 2 from the second.
    Boundary elements have no values and are dropped. all_elements (the
    whole model): cells with values that belong to no Mecway element
    are reported once per label (otherwise those values would be
    missing silently).
    """
    cells = {}
    for c, cn in enumerate(conn):
        if nbpt[c] != len(cn) or nbsp[c] != 1:
            continue
        mapped = _cell_nodes(fields, cn)
        key = tuple(sorted(m for m in mapped if m >= 0))
        if len(key) >= 2 and key not in cells:
            cells[key] = (c, mapped)

    def lookup(idx):
        hit = cells.get(tuple(sorted(idx)))
        if hit is None:
            return None
        c, mapped = hit
        return [(c, mapped.index(m)) for m in idx]

    out = {}
    for eid, (shape, nids) in elements.items():
        idx = [m - 1 for m in nids]
        pts = lookup(idx)
        if pts is None and shape == "line3" and len(idx) == 3:
            first, second = lookup(idx[:2]), lookup(idx[1:])
            if first is not None and second is not None:
                pts = first + second[1:]
        if pts is not None:
            out[eid] = pts
    if all_elements is not None and label not in _LOST_REPORTED:
        known = set()
        for shape, nids in all_elements.values():
            idx = [m - 1 for m in nids]
            known.add(tuple(sorted(idx)))
            if shape == "line3" and len(idx) == 3:
                known.add(tuple(sorted(idx[:2])))
                known.add(tuple(sorted(idx[1:])))
        lost = [c for key, (c, _m) in cells.items() if key not in known]
        if lost:
            _LOST_REPORTED.add(label)
            print(tr("aster_results_export: WAARSCHUWING: {0}: {1} cel(len) "
                     "met waarden horen bij geen Mecway-element; die "
                     "waarden ontbreken in Mecway.",
                     "aster_results_export: WARNING: {0}: {1} cell(s) with "
                     "values belong to no Mecway element; those values are "
                     "missing in Mecway.").format(label, len(lost)))
    return out


# ==========================================
# PLANNING VARIABLES (on the last time step)
# ==========================================
class _Var(object):
    """A Mecway variable: name, kind, ids and how to get the values."""

    def __init__(self, name, element, ids, getter):
        self.name = name
        self.element = element    # True: elementnodevariable
        self.ids = ids            # np.int32: node or element numbers
        self.getter = getter      # function(_Fields) -> np.ndarray float64
        self.groups = []          # [(component name, positions)]


def _node_var(rkey, field, cmp_, rows):
    def getter(fields):
        d = fields.get(rkey, field, False)
        if d is None or cmp_ not in d[0]:
            return None
        return d[1][rows, d[0].index(cmp_)]
    return getter


def _elno_node_var(rkey, field, cmp_, pt_node, rows, reduce_min):
    def getter(fields):
        d = fields.get(rkey, field, True)
        if d is None or cmp_ not in d[0]:
            return None
        col = d[1][:, d[0].index(cmp_)]
        ok = (pt_node >= 0) & d[2][:, d[0].index(cmp_)]
        out = np.full(fields.n, np.inf if reduce_min else -np.inf)
        ufunc = np.minimum if reduce_min else np.maximum
        ufunc.at(out, pt_node[ok], col[ok])
        return out[rows]
    return getter


def _elem_var(rkey, field, cmp_, gather):
    def getter(fields):
        d = fields.get(rkey, field, True)
        if d is None or cmp_ not in d[0]:
            return None
        return d[1][gather, d[0].index(cmp_)]
    return getter


def _plan_node(fields, rkey, field, cmp_, name):
    d = fields.get(rkey, field, False)
    if d is None or cmp_ not in d[0]:
        return None
    rows = np.nonzero(d[2][:, d[0].index(cmp_)])[0]
    if not len(rows):
        return None
    getter = _node_var(rkey, field, cmp_, rows)
    if name in VALUE_OFFSETS:
        getter = _offset(getter, VALUE_OFFSETS[name])
    if name in VALUE_SCALES:
        getter = _scaled(getter, VALUE_SCALES[name])
    if name in VALUE_MIN:
        getter = _at_least(getter, VALUE_MIN[name])
    return _Var(name, False, (rows + 1).astype("<i4"), getter)


def _offset(getter, offset):
    def shifted(fields):
        vals = getter(fields)
        return None if vals is None else vals + offset
    return shifted


def _scaled(getter, factor):
    def scaled(fields):
        vals = getter(fields)
        return None if vals is None else vals * factor
    return scaled


def _at_least(getter, lower):
    def clipped(fields):
        vals = getter(fields)
        return None if vals is None else np.maximum(vals, lower)
    return clipped


def _cells_field(fields, rkey, field, cmp_, conn):
    """(field, component index, (start, nbpt, nbsp)) of a cell field, or
    None. The layout is determined once per field (last time step) and
    applies to all time steps."""
    d = fields.get(rkey, field, True)
    if d is None or cmp_ not in d[0]:
        return None
    key = (rkey, field)
    if key not in fields.layouts:
        fields.layouts[key] = _cell_layout(d[3], conn, d[1].shape[0])
        if fields.layouts[key] is None:
            print(tr("aster_results_export: WAARSCHUWING: indeling van "
                     "{0}:{1} niet herkend; overgeslagen.",
                     "aster_results_export: WARNING: layout of {0}:{1} "
                     "not recognised; skipped.").format(rkey, field))
    if fields.layouts[key] is None:
        return None
    return d, d[0].index(cmp_), fields.layouts[key]


def _plan_elno_node(fields, rkey, field, cmp_, name, kind, conn):
    found = _cells_field(fields, rkey, field, cmp_, conn)
    if found is None:
        return None
    d, icmp, (start, nbpt, nbsp) = found
    # Mecway node per point (_cell_nodes: beam end with a flexible
    # joint and offset elements to their Mecway node)
    pt_node = np.full(d[1].shape[0], -1, dtype=int)
    for c, cn in enumerate(conn):
        if nbpt[c] == len(cn) and nbsp[c] == 1:
            pt_node[start[c]:start[c] + nbpt[c]] = _cell_nodes(fields, cn)
    ok = (pt_node >= 0) & d[2][:, icmp]
    rows = np.unique(pt_node[ok])
    if not len(rows):
        return None
    return _Var(name, False, (rows + 1).astype("<i4"),
                _elno_node_var(rkey, field, cmp_, pt_node, rows,
                               kind == ELNO_MIN))


def _plan_elem(fields, rkey, field, cmp_, name, conn, model,
               shapes=SOLID_SHAPES):
    found = _cells_field(fields, rkey, field, cmp_, conn)
    if found is None:
        return None
    d, icmp, (start, nbpt, nbsp) = found
    solids = dict((e, v) for e, v in model["elements"].items()
                  if v[0] in shapes)
    cells = _element_points(fields, conn, solids, nbpt, nbsp,
                            "{0}:{1}".format(rkey, field),
                            model["elements"])
    eids, gather = [], []
    for eid in sorted(cells):
        # ELNO point k of cell c; Mecway wants the order of the
        # nodes attribute of <elem> (_element_points)
        rows = [start[c] + k for c, k in cells[eid]]
        if not d[2][rows, icmp].all():
            continue
        gather.extend(rows)
        eids.append(eid)
    if not eids:
        return None
    getter = _elem_var(rkey, field, cmp_, np.array(gather))
    if name in VALUE_SCALES:
        getter = _scaled(getter, VALUE_SCALES[name])
    return _Var(name, True, np.array(eids, dtype="<i4"), getter)


def _wanted(group, groups_wanted, opt_in):
    """Does group belong to the export? With a list of groups (fields)
    exactly those; without a list everything except the OPT_IN_GROUPS
    that are not in opt_in."""
    if groups_wanted is not None:
        return group in groups_wanted
    return group not in OPT_IN_GROUPS or group in opt_in


def _plan_variables(fields, model, conn, groups_wanted, magnitudes=True,
                    opt_in=(), derived=None):
    """List of _Var in Mecway order (magnitude before the components;
    without magnitude if magnitudes is False, as Mecway's mode shapes).
    derived: arguments for _plan_derived (shell vectors, strengths)."""
    node_vars, elem_vars = OrderedDict(), OrderedDict()
    for group, rkey, field, cmp_, name, kind in FIELD_TABLE:
        if not _wanted(group, groups_wanted, opt_in):
            continue
        if rkey not in fields.results:
            continue
        if fields.rows is not None and kind != KNOOP:
            continue    # whole wheel (cyclic): nodal fields only
        if kind == KNOOP:
            var = _plan_node(fields, rkey, field, cmp_, name)
        elif kind in (ELNO_MIN, ELNO_MAX):
            var = _plan_elno_node(fields, rkey, field, cmp_, name, kind, conn)
        elif kind == ELEMKNOOP_LIJN:
            var = _plan_elem(fields, rkey, field, cmp_, name, conn, model,
                             LINE_SHAPES)
        else:
            var = _plan_elem(fields, rkey, field, cmp_, name, conn, model)
        if var is None:
            continue
        target = elem_vars if var.element else node_vars
        if name in target:
            print(tr("aster_results_export: WAARSCHUWING: '{0}' dubbel in "
                     "FIELD_TABLE, tweede bron genegeerd.",
                     "aster_results_export: WARNING: '{0}' twice in "
                     "FIELD_TABLE, second source ignored.").format(name))
            continue
        target[name] = var
    if fields.rows is None:
        wanted = [g for g in OPT_IN_GROUPS
                  if _wanted(g, groups_wanted, opt_in)]
        for var in _plan_derived(fields, model, conn, wanted,
                                 **(derived or {})):
            target = elem_vars if var.element else node_vars
            if var.name not in target:
                target[var.name] = var
    out = []
    for name, var in node_vars.items():
        for mag, parts in (MAGNITUDES.items() if magnitudes else ()):
            need = [p for p in parts if p not in OPTIONAL_PARTS]
            if parts[0] == name and all(p in node_vars for p in need):
                out.append(_magnitude_var(
                    mag, [node_vars[p] for p in need],
                    [node_vars[p] for p in parts
                     if p in OPTIONAL_PARTS and p in node_vars]))
        out.append(var)
    return out + list(elem_vars.values())


def _magnitude_var(name, parts, optional=()):
    """sqrt(x^2+y^2+z^2) on nodes where all required components
    exist; an optional component (OPTIONAL_PARTS) counts where it
    exists and is 0 elsewhere."""
    ids = parts[0].ids
    for p in parts[1:]:
        ids = np.intersect1d(ids, p.ids)
    pos = [np.searchsorted(p.ids, ids) for p in parts]
    opt = []
    for p in optional:
        here = np.isin(ids, p.ids)
        opt.append((p, here, np.searchsorted(p.ids, ids[here])))

    def getter(fields):
        vals = [p.getter(fields) for p in parts]
        if any(v is None for v in vals):
            return None
        sq = sum(v[k] ** 2 for v, k in zip(vals, pos))
        for p, here, k in opt:
            v = p.getter(fields)
            if v is not None:
                sq[here] += v[k] ** 2
        return np.sqrt(sq)
    return _Var(name, False, ids.astype("<i4"), getter)


# ==========================================
# DERIVED FIELDS: SHELLS, FACTOR OF SAFETY, CONTACT STATUS
# ==========================================
# Shells (DKT/DST/COQUE_3D): Code-Aster gives SIGM_ELNO, EPSI_ELNO and
# EFGE_ELNO in the local axis system of the element: x = projection of
# the reference vector (AFFE_CARA_ELEM COQUE VECTEUR, without: global X) on
# the element plane, n = normal from the node order, y = n x x (U4.42.01,
# COQUE/VECTEUR). Checked with a run: strip in the XY plane at 30
# degrees, SIGM_ELNO SIXX = sigma_xx global; SUP = side of +n.
# Mecway (seen headless, Mecway 34, strip at 30 degrees and straight):
#   - stress tensor in GLOBAL XYZ on top, middle and bottom surface:
#     stress<ij>u1 / m1 / b1 (layer 1); top = +W;
#   - total strain likewise: lstrain<ij>u / m / b, shear as shear angle
#     gamma, lstrainzz = 0 (plane stress; Code-Aster EPZZ = 0);
#   - forces and moments per length in Mecway's own U,V,W:
#     forceperlengthu/v/uv (N/m), momentu/v/uv (N.m/m; momentu > 0 gives
#     tension on top), shearuw/shearvw (transverse shear per length). U =
#     projection of the orientation vector or the edge from node 1 to 2
#     (quadratic: 1 to 3), V = W x U (manual v34 sec. 7.4.2).
# Nodal values are the average of the element values at the node
# (as Mecway and Code-Aster's _NOEU); in addition as elementnodevariable.
# Curved quadratic shells: the normal is that of the plane through the
# corner nodes (Code-Aster and Mecway vary it per point; NOT
# verified for strongly curved elements).
_TENSOR_ORDER = (("xx", 0, 0), ("yy", 1, 1), ("zz", 2, 2), ("xy", 0, 1),
                 ("yz", 1, 2), ("zx", 2, 0))
_SIGM_IJ = {"SIXX": (0, 0), "SIYY": (1, 1), "SIZZ": (2, 2), "SIXY": (0, 1),
            "SIXZ": (0, 2), "SIYZ": (1, 2)}
_EPSI_IJ = {"EPXX": (0, 0), "EPYY": (1, 1), "EPZZ": (2, 2), "EPXY": (0, 1),
            "EPXZ": (0, 2), "EPYZ": (1, 2)}
_SHELL_LEVELS = (("sup", "u"), ("moy", "m"), ("inf", "b"))
_SHELL_FORCE_NAMES = ("forceperlengthu", "forceperlengthv",
                      "forceperlengthuv", "momentu", "momentv", "momentuv",
                      "shearuw", "shearvw")


def _elset_of(model):
    out = {}
    for name, eids in model["elsets"].items():
        for e in eids:
            out.setdefault(e, name)
    return out


def _shell_frame(model, xyz, cell_nodes, eid, vectors, elset_of):
    """(R, cos, sin): R with columns x, y, n of Code-Aster's local
    shell axes (see the header above) and the angle of Mecway's U in that
    system, or None for a degenerate element."""
    shape, nids = model["elements"][eid]
    ncorner = 3 if shape.startswith("tri") else 4
    p = xyz[list(cell_nodes[:ncorner])]
    if ncorner == 4:
        n = np.cross(p[2] - p[0], p[3] - p[1])
    else:
        n = np.cross(p[1] - p[0], p[2] - p[0])
    if np.linalg.norm(n) == 0.0:
        return None
    n = n / np.linalg.norm(n)
    v = np.asarray(vectors.get(elset_of.get(eid), (1.0, 0.0, 0.0)),
                   dtype=float)
    x = v - v.dot(n) * n
    if np.linalg.norm(x) == 0.0:
        return None
    x = x / np.linalg.norm(x)
    y = np.cross(n, x)
    u = model.get("uaxes", {}).get(eid)
    if u is None:
        coords = model["coords"]
        j = 2 if shape in ("tri6", "quad8") else 1
        u = coords[nids[j] - 1] - coords[nids[0] - 1]
    u = np.asarray(u, dtype=float)
    u = u - u.dot(n) * n
    if np.linalg.norm(u) == 0.0:
        u = x
    u = u / np.linalg.norm(u)
    return np.column_stack((x, y, n)), float(u.dot(x)), float(u.dot(y))


def _shell_points(fields, rkey, field, cmp0, conn, model, xyz, vectors,
                  elset_of, frames):
    """Points of the shell cells of an ELNO field (one subpoint per
    node, so after POST_CHAMP EXTR_COQUE or EFGE_ELNO), with per point the
    node, the axis system and the collection order for Mecway's
    elementnodevariable; or None. frames: cache {eid: _shell_frame}."""
    found = _cells_field(fields, rkey, field, cmp0, conn)
    if found is None:
        return None
    d, _icmp, (start, nbpt, nbsp) = found
    shells = dict((e, v) for e, v in model["elements"].items()
                  if v[0] in SHELL_SHAPES)
    cells = _element_points(fields, conn, shells, nbpt, nbsp,
                            "{0}:{1}".format(rkey, field),
                            model["elements"])
    rows, node, rot, cs, gather, eids = [], [], [], [], [], []
    for eid in sorted(cells):
        c = cells[eid][0][0]
        cn = list(conn[c])
        if eid not in frames:
            frames[eid] = _shell_frame(model, xyz, cn, eid, vectors,
                                       elset_of)
        if frames[eid] is None:
            continue
        r, co, si = frames[eid]
        base = len(rows)
        rows.extend(range(start[c], start[c] + nbpt[c]))
        # nodal values at the Mecway nodes (also of offset cells)
        node.extend(_cell_nodes(fields, cn))
        rot.extend([r] * nbpt[c])
        cs.extend([(co, si)] * nbpt[c])
        gather.extend(base + k for _c, k in cells[eid])
        eids.append(eid)
    if not eids:
        return None
    node = np.array(node)
    ok = node >= 0
    uniq, inv = np.unique(node[ok], return_inverse=True)
    return {"rows": np.array(rows), "rot": np.array(rot),
            "cs": np.array(cs), "gather": np.array(gather),
            "eids": np.array(eids, dtype="<i4"), "ok": ok, "uniq": uniq,
            "inv": inv, "count": np.bincount(inv).astype(float)}


def _cached(fields, key, compute):
    """Compute the value once per time step (fields.data is cleared per
    index)."""
    k = ("afgeleid",) + key
    if k not in fields.data:
        fields.data[k] = compute()
    return fields.data[k]


def _shell_tensor(fields, plan, rkey, field, cmap):
    """(points, 6) global tensor xx, yy, zz, xy, yz, zx (R T R^T), or
    None."""
    d = fields.get(rkey, field, True)
    if d is None:
        return None
    vals = d[1][plan["rows"]]
    t = np.zeros((len(vals), 3, 3))
    for name, (i, j) in cmap.items():
        if name in d[0]:
            v = vals[:, d[0].index(name)]
            t[:, i, j] = v
            t[:, j, i] = v
    g = np.einsum("pik,pkl,pjl->pij", plan["rot"], t, plan["rot"])
    return np.column_stack([g[:, i, j] for _s, i, j in _TENSOR_ORDER])


def _shell_forces(fields, plan, rkey):
    """(points, 8) forces and moments per length in Mecway's U,V (see
    _SHELL_FORCE_NAMES), from EFGE_ELNO (NXX..MXY, QX, QY in Code-Aster's
    x,y), or None. U = cos x + sin y, V = -sin x + cos y."""
    d = fields.get(rkey, "EFGE_ELNO", True)
    if d is None:
        return None
    vals = d[1][plan["rows"]]

    def col(name):
        if name in d[0]:
            return vals[:, d[0].index(name)]
        return np.zeros(len(vals))
    c, s = plan["cs"][:, 0], plan["cs"][:, 1]
    out = []
    for p in ("N", "M"):
        xx, yy, xy = col(p + "XX"), col(p + "YY"), col(p + "XY")
        out += [c * c * xx + 2 * c * s * xy + s * s * yy,
                s * s * xx - 2 * c * s * xy + c * c * yy,
                c * s * (yy - xx) + (c * c - s * s) * xy]
    qx, qy = col("QX"), col("QY")
    out += [c * qx + s * qy, -s * qx + c * qy]
    return np.column_stack(out)


def _point_vars(plan, name_cols, compute, key):
    """Node and element node variables from a function that gives a
    (points, k) matrix per time step. name_cols: [(Mecway name, column,
    factor)]."""
    out = []
    for name, col, factor in name_cols:
        def node_get(fields, col=col, factor=factor):
            m = _cached(fields, key, compute(fields))
            if m is None:
                return None
            v = m[plan["ok"], col] * factor
            return np.bincount(plan["inv"], weights=v) / plan["count"]

        def elem_get(fields, col=col, factor=factor):
            m = _cached(fields, key, compute(fields))
            if m is None:
                return None
            return m[plan["gather"], col] * factor
        out.append(_Var(name, False, (plan["uniq"] + 1).astype("<i4"),
                        node_get))
        out.append(_Var(name, True, plan["eids"], elem_get))
    return out


def _fos_vars(fields, model, conn, strengths):
    """
    Factor of safety for Mecway's von Mises failure criterion (manual v34
    sec. 8.7: the factor by which all stress components reach the failure
    limit; for von Mises thus S / sigma_vM, with S = tensilestrength of the
    material; shells: the smaller of top and bottom side). Mecway
    computes it only when displaying (headless not in the solution, name
    factorofsafety checked with solution.node_value); variable
    factorofsafety, Mecway adds the item "failure" to it.
    Node: smallest S of the elsets with a criterion at that node
    divided by the largest von Mises (volume, shell top/bottom);
    element: per element node with its own S. Unloaded: FOS_MAX.
    """
    if not strengths:
        return []
    elset_of = _elset_of(model)
    n = fields.n
    s_node = np.full(n, np.inf)
    for name, eids in model["elsets"].items():
        if strengths.get(name, 0.0) > 0.0:
            nids = [nid - 1 for e in eids for nid in model["elements"][e][1]]
            np.minimum.at(s_node, np.array(nids, dtype=int),
                          float(strengths[name]))
    sources = [(r, f) for r, f in (("res", "SIEQ_NOEU"),
                                   ("res_sup", "SIEQ_NOEU"),
                                   ("res_inf", "SIEQ_NOEU"))
               if r in fields.results]
    have = np.zeros(n, dtype=bool)
    for r, f in sources:
        d = fields.get(r, f, False)
        if d is not None and "VMIS" in d[0]:
            have |= d[2][:, d[0].index("VMIS")]
    rows = np.nonzero(have & np.isfinite(s_node))[0]
    out = []
    if len(rows):
        def node_get(fields):
            sig = np.zeros(len(rows))
            found = False
            for r, f in sources:
                d = fields.get(r, f, False)
                if d is None or "VMIS" not in d[0]:
                    continue
                k = d[0].index("VMIS")
                v = np.where(d[2][rows, k], np.abs(d[1][rows, k]), 0.0)
                sig = np.maximum(sig, v)
                found = True
            if not found:
                return None
            return _fos(s_node[rows], sig)
        out.append(_Var("factorofsafety", False, (rows + 1).astype("<i4"),
                        node_get))
    # Per element: volumes from res, shells from res_sup and res_inf.
    parts = []      # (eids, [(rkey, gather)], S per value)
    found = _cells_field(fields, "res", "SIEQ_ELNO", "VMIS", conn)
    if found is not None:
        d, icmp, (start, nbpt, nbsp) = found
        solids = dict((e, v) for e, v in model["elements"].items()
                      if v[0] in SOLID_SHAPES and
                      strengths.get(elset_of.get(e), 0.0) > 0.0)
        cells = _element_points(fields, conn, solids, nbpt, nbsp,
                                "res:SIEQ_ELNO", model["elements"])
        eids, gather, svals = [], [], []
        for eid in sorted(cells):
            gather.extend(start[c] + k for c, k in cells[eid])
            svals += [strengths[elset_of[eid]]] * len(solids[eid][1])
            eids.append(eid)
        if eids:
            parts.append((eids, [("res", np.array(gather))], svals))
    shell_g = []
    for rkey in ("res_sup", "res_inf"):
        found = (_cells_field(fields, rkey, "SIEQ_ELNO", "VMIS", conn)
                 if rkey in fields.results else None)
        if found is None:
            continue
        d, icmp, (start, nbpt, nbsp) = found
        shells = dict((e, v) for e, v in model["elements"].items()
                      if v[0] in SHELL_SHAPES and
                      strengths.get(elset_of.get(e), 0.0) > 0.0)
        cells = _element_points(fields, conn, shells, nbpt, nbsp,
                                rkey + ":SIEQ_ELNO", model["elements"])
        eids, gather, svals = [], [], []
        for eid in sorted(cells):
            gather.extend(start[c] + k for c, k in cells[eid])
            svals += [strengths[elset_of[eid]]] * len(shells[eid][1])
            eids.append(eid)
        if eids:
            shell_g.append((eids, (rkey, np.array(gather)), svals))
    if shell_g and all(g[0] == shell_g[0][0] for g in shell_g):
        parts.append((shell_g[0][0], [g[1] for g in shell_g], shell_g[0][2]))
    if parts:
        # Mecway order: element numbers ascending, per element the
        # values (one per node) one after another.
        blocks = []
        for p, (eids, _src, _svals) in enumerate(parts):
            off = 0
            for eid in eids:
                size = len(model["elements"][eid][1])
                blocks.append((eid, p, off, size))
                off += size
        blocks.sort()
        order = [(p, off + i) for _e, p, off, size in blocks
                 for i in range(size)]
        all_eids = np.array([b[0] for b in blocks], dtype="<i4")

        def elem_get(fields):
            vals = []
            for eids, src, svals in parts:
                sig = None
                for rkey, gather in src:
                    d = fields.get(rkey, "SIEQ_ELNO", True)
                    if d is None or "VMIS" not in d[0]:
                        return None
                    v = np.abs(d[1][gather, d[0].index("VMIS")])
                    sig = v if sig is None else np.maximum(sig, v)
                vals.append(_fos(np.array(svals, dtype=float), sig))
            return np.array([vals[p][i] for p, i in order])
        out.append(_Var("factorofsafety", True, all_eids, elem_get))
    return out


def _fos(strength, sigma):
    """S / sigma, with FOS_MAX where sigma is (nearly) 0."""
    with np.errstate(divide="ignore", invalid="ignore"):
        f = np.where(sigma > 0.0, strength / np.where(sigma > 0.0, sigma, 1.0),
                     FOS_MAX)
    return np.minimum(f, FOS_MAX)


def _contact_state_var(fields):
    """
    contactstate on the slave nodes: 0 open, 1 closed, 2 closed and
    sliding (only with friction and CONT_NOEU). Mecway: 1 in contact, 0
    not (manual v34 sec. 9.9). Source:
      - CONT_NOEU, component CONT (0 no contact, 1 sticking, 2 sliding;
        U4.44.11, value 2 with friction NOT verified). Code-Aster
        17.4 only creates the field with integration at the nodes (linear
        faces), otherwise alarm CONTACT3_16 "le champ CONT_NOEU n'est pas
        créé" (seen). Without friction (no LAGS_F1 in DEPL) CONT gives
        2 for every closed point (seen in NL-30): then 1.
      - otherwise the contact pressure p = -LAGS_C: closed where p > 1% of
        the largest p in that step. Open nodes do not have an exact 0 (seen
        with PENALISATION and hex20: |p| up to ~0.1% of the peak next to the
        contact), hence the margin; sliding cannot be distinguished this way.
    """
    d = fields.get("res", "DEPL", False)
    if d is None or "LAGS_C" not in d[0]:
        return []
    k = d[0].index("LAGS_C")
    rows = np.nonzero(d[2][:, k])[0]
    if not len(rows):
        return []

    def getter(fields):
        dd = fields.get("res", "DEPL", False)
        if dd is None or "LAGS_C" not in dd[0]:
            return None
        cont = fields.get("res", "CONT_NOEU", False)
        if cont is not None and "CONT" in cont[0]:
            j = cont[0].index("CONT")
            state = np.where(cont[2][rows, j], cont[1][rows, j], 0.0)
            if "LAGS_F1" not in dd[0]:
                state = np.minimum(state, 1.0)
            return state
        p = -dd[1][rows, dd[0].index("LAGS_C")]
        tol = CONTACT_CLOSED * max(float(p.max()), 0.0)
        return np.where(p > tol, 1.0, 0.0)
    return [_Var("contactstate", False, (rows + 1).astype("<i4"), getter)]


def _plan_derived(fields, model, conn, wanted, shell_vectors=None,
                  strengths=None):
    """_Var's of the derived fields (see the header of this block) for the
    chosen groups (wanted). shell_vectors: {Mecway elset: VECTEUR} of
    AFFE_CARA_ELEM COQUE (without: global X); strengths: {Mecway elset:
    tensilestrength in Pa} of materials with a von Mises
    failure criterion."""
    out = []
    if "contact" in wanted:
        out += _contact_state_var(fields)
    if "safety_factor" in wanted:
        out += _fos_vars(fields, model, conn, strengths or {})
    shell_groups = [g for g in ("shell_stresses", "strain", "shell_forces")
                    if g in wanted]
    if not shell_groups:
        return out
    xyz = np.asarray(fields.results["res"].getMesh().getCoordinates()
                     .getValues(), dtype=float).reshape(-1, 3)
    vectors = shell_vectors or {}
    elset_of = _elset_of(model)
    frames = {}
    specs = []
    if "shell_stresses" in wanted:
        specs += [("res_" + lvl, "SIGM_ELNO", "SIXX", _SIGM_IJ, "stress",
                   suf + "1", 1.0) for lvl, suf in _SHELL_LEVELS]
    if "strain" in wanted:
        specs += [("eps_" + lvl, "EPSI_ELNO", "EPXX", _EPSI_IJ, "lstrain",
                   suf, 2.0) for lvl, suf in _SHELL_LEVELS]
    for rkey, field, cmp0, cmap, prefix, suffix, shear in specs:
        if rkey not in fields.results:
            continue
        plan = _shell_points(fields, rkey, field, cmp0, conn, model, xyz,
                             vectors, elset_of, frames)
        if plan is None:
            continue

        def compute(fields, plan=plan, rkey=rkey, field=field, cmap=cmap):
            return lambda: _shell_tensor(fields, plan, rkey, field, cmap)
        cols = [(prefix + s + suffix, k, shear if i != j else 1.0)
                for k, (s, i, j) in enumerate(_TENSOR_ORDER)]
        out += _point_vars(plan, cols, compute, (rkey, field))
    if "shell_forces" in wanted and "res_efs" in fields.results:
        plan = _shell_points(fields, "res_efs", "EFGE_ELNO", "NXX", conn,
                             model, xyz, vectors, elset_of, frames)
        if plan is not None:
            def compute(fields, plan=plan):
                return lambda: _shell_forces(fields, plan, "res_efs")
            out += _point_vars(plan, [(name, k, 1.0) for k, name in
                                      enumerate(_SHELL_FORCE_NAMES)],
                               compute, ("res_efs", "EFGE_ELNO"))
    return out


def _assign_groups(var, model, elset_nodes, free_nodes):
    """
    Positions within var.ids per maxandmin component (see header): first ""
    (nodes outside elements), then per elset. Empty components are dropped.
    """
    if var.element:
        block = np.array([len(model["elements"][e][1]) for e in var.ids])
        start = np.concatenate([[0], np.cumsum(block)[:-1]])
        where = dict((int(e), i) for i, e in enumerate(var.ids))
        for name, eids in model["elsets"].items():
            pos = [np.arange(start[where[e]], start[where[e]] + block[where[e]])
                   for e in eids if e in where]
            if pos:
                var.groups.append((name, np.concatenate(pos)))
        return
    candidates = [("", free_nodes)] + list(elset_nodes.items())
    for name, nids in candidates:
        # Positions in the ascending var.ids of the nodes of this group.
        pos = np.searchsorted(var.ids, nids[np.isin(nids, var.ids)])
        if len(pos):
            var.groups.append((name, pos))


# ==========================================
# WRITING
# ==========================================
def _xml_attr(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _num(x):
    """Number as Mecway writes it in max/min (15 significant
    digits)."""
    x = float(x)
    if x == 0.0:
        x = 0.0     # no "-0" (Mecway writes "0")
    return "{0:.15G}".format(x)


def _b64(data):
    """base64 in lines of 64 characters with CRLF, plus a CRLF at the end
    (as Mecway)."""
    enc = base64.b64encode(data)
    lines = [enc[i:i + _B64_LINE] for i in range(0, len(enc), _B64_LINE)]
    return _NL.join(lines) + _NL


def _ids_block(var, indent):
    tag = "elementnodeids" if var.element else "nodeids"
    return (indent + '<{0} name="{1}">'.format(tag, _xml_attr(var.name))
            ).encode("utf-8") + _b64(var.ids.tobytes()) + \
        "</{0}>".format(tag).encode("ascii") + _NL


def _var_block(var, values, indent, dtype, values_tag):
    """A <nodevariable>/<elementnodevariable> as bytes."""
    tag = "elementnodevariable" if var.element else "nodevariable"
    empty = "elements" if var.element else "nodes"
    i1, i2 = indent + "  ", indent + "    "
    vals = np.asarray(values, dtype=dtype)
    parts = [indent + '<{0} name="{1}">'.format(tag, _xml_attr(var.name)),
             i1 + "<maxandmin>"]
    for name, pos in var.groups:
        sub = vals[pos]
        parts.append(i2 + '<component name="{0}" max="{1}" min="{2}" />'
                     .format(_xml_attr(name), _num(sub.max()),
                             _num(sub.min())))
    parts.append(i1 + "</maxandmin>")
    head = "\r\n".join(parts) + "\r\n" + i1 + "<{0}>".format(values_tag)
    tail = "</{0}>\r\n{1}<{2} />\r\n{1}<values />\r\n{3}</{4}>\r\n".format(
        values_tag, i1, empty, indent, tag)
    return head.encode("utf-8") + _b64(vals.tobytes()) + tail.encode("ascii")


def _is_static(res, indexes):
    """Static (no <timestep>): one index and an EVOL_ELAS result
    (MECA_STATIQUE). If getType() fails, only by the count."""
    if len(indexes) != 1:
        return False
    try:
        return "ELAS" in str(res.getType()).upper()
    except Exception:
        return True


def _mode_kind(res):
    """'frequency' (MODE_MECA, MODE_ACOU), 'buckling' (MODE_FLAMB) or
    None."""
    try:
        kind = str(res.getType()).upper()
    except Exception:
        return None
    if "FLAMB" in kind:
        return "buckling"
    if kind.startswith("MODE_MECA") or kind.startswith("MODE_ACOU"):
        return "frequency"
    return None


def _is_acoustic(res):
    """True for acoustic modes (MODE_ACOU, bridge_acoustic.py)."""
    try:
        return str(res.getType()).upper().startswith("MODE_ACOU")
    except Exception:
        return False


def _mass_scales(res, indexes):
    """
    {index: 1/sqrt(MASS_GENE)}: acoustic shapes with p^T M p = 1, as
    Mecway (bridge_acoustic.py, header). NORM_MODE does not work in
    Code-Aster 17.4 for MODE_ACOU (MASS_GENE as norm gave max |p| = 1, seen);
    MASS_GENE in the table is p^T M p of the computed shape (recomputed:
    constant mode of a tube 1 x 0.1 x 0.1 m, c = 340 m/s, RHO = 1:
    MASS_GENE 8.6505e-8 = V / c^2, scale 3400 = Mecway's value).
    """
    out = {}
    for nr, (gen,) in _table_values(res, ("MASS_GENE",)).items():
        if nr in indexes and gen and float(gen) > 0.0:
            out[nr] = 1.0 / np.sqrt(float(gen))
    return out


def _table_values(res, names):
    """{NUME_ORDRE: [value per name]} from RECU_TABLE: parameters such as
    CHAR_CRIT and MASS_EFFE_UN_DX are not in getAccessParameters()
    (checked with Code-Aster 17.4; there only NUME_ORDRE, FREQ,
    NUME_MODE, NOEUD_CMP). An unknown parameter gives <EXCEPTION>
    UTILITAI3_5 (e.g. MASS_EFFE_UN_DRX)."""
    from code_aster.Commands import RECU_TABLE
    vals = RECU_TABLE(CO=res, NOM_PARA=tuple(names)).EXTR_TABLE().values()
    return dict((nr, [vals[k][i] for k in names])
                for i, nr in enumerate(vals["NUME_ORDRE"]))


def _mode_values(res, kind):
    """{index: frequency in Hz or buckling load factor}. The buckling load
    factor is CHAR_CRIT itself: Mecway's BucklingBeam (compressive force
    1 N on a clamped column) gave 41124.6991224029 in Mecway and in
    Code-Aster CHAR_CRIT = +41124.699122467 (seen). A negative CHAR_CRIT
    is buckling under the reversed load."""
    if kind == "buckling":
        return dict((nr, float(v[0])) for nr, v in
                    _table_values(res, ("CHAR_CRIT",)).items())
    acc = res.getAccessParameters()
    return dict((i, float(v)) for i, v in
                zip(acc["NUME_ORDRE"], acc["FREQ"]))


# Effective mass as a fraction of the total mass per direction (MODE_MECA).
# Code-Aster only knows the translations as parameter; the rotations are
# computed by _rotation_fractions itself (same definition, rigid rotation
# about the global axes through the origin, as Mecway).
_MASS_FRACTIONS = ("MASS_EFFE_UN_DX", "MASS_EFFE_UN_DY", "MASS_EFFE_UN_DZ")
_ROT_FRACTIONS = ("MASS_EFFE_UN_DRX", "MASS_EFFE_UN_DRY", "MASS_EFFE_UN_DRZ")
_DOF_INDEX = {"DX": 0, "DY": 1, "DZ": 2, "DRX": 3, "DRY": 4, "DRZ": 5}

# Effective mass in Mecway (S12): Mecway's own modal solution (internal
# solver, with "modal effective mass" and "modal effective mass fraction"
# under Solution) writes per <mode>, before the <nodevariable>s:
#   <globalvariable name="modaleffectivemassty">57.7394288067102</globalvariable>
#   <globalvariable name="modaleffectivemassfractionty">0.627861821259979</...>
# per direction tx, ty, tz, rx, ry, rz (mass and fraction alternately; seen
# headless with Mecway 33 on Samples/VibratingCantileverSolid.liml). A
# result with these globalvariables gives the items on opening
# "modal effective mass" (kg, kg.m2) and "modal effective mass fraction"
# (checked headless: Mecway adds the <fieldvariable>s on mw.save_as).
# The bridge writes the same names; the fraction is that of Code-Aster
# (denominator R^T M R including the constrained nodes, _effective_masses),
# NOT Mecway's denominator (free mass). Extra (own name of the bridge): the
# cumulative fraction over the modes up to and including this mode; Mecway
# keeps unknown globalvariables (checked headless), whether the GUI shows
# them is NOT verified.
_MW_DIRS = ("tx", "ty", "tz", "rx", "ry", "rz")
_MODE_GLOBALS = {}      # id(res) -> {index: [(name, value)]}


def _store_mode_globals(res, indexes, absolute, fractions):
    """
    Store the effective mass per mode for export_results (globalvariables
    in <mode>, see above). absolute: {index: [m_eff x 6]} (kg, kg.m2) or
    {}; fractions: {index: [fraction x 6]}, None where unknown. A direction
    without a fraction also gets no cumulative fraction.
    """
    out = {}
    cum = [0.0] * 6
    for idx in sorted(indexes):
        mass = list(absolute.get(idx) or [None] * 6)
        frac = list(fractions.get(idx) or [None] * 6)
        items = []
        for k, d in enumerate(_MW_DIRS):
            if k < len(mass) and mass[k] is not None:
                items.append(("modaleffectivemass" + d, float(mass[k])))
            if k < len(frac) and frac[k] is not None:
                items.append(("modaleffectivemassfraction" + d,
                              float(frac[k])))
        for k, d in enumerate(_MW_DIRS):
            if k < len(frac) and frac[k] is not None:
                cum[k] += float(frac[k])
                items.append(("cumulativeeffectivemassfraction" + d, cum[k]))
        if items:
            out[idx] = items
    _MODE_GLOBALS[id(res)] = out


def _matvec(matrix):
    """Function v -> M v for an assembled matrix (both triangles
    from getValuesWithDescription, see _stiffness_scales) and the size."""
    data, rows, cols, dim = matrix.getValuesWithDescription()
    data = np.asarray(data, dtype=float)
    rows = np.asarray(rows, dtype=np.int64)
    cols = np.asarray(cols, dtype=np.int64)

    def mul(v):
        return np.bincount(rows, weights=data * v[cols], minlength=dim)
    return mul, dim


def _rigid_vectors(matrix, xyz, point=(0.0, 0.0, 0.0)):
    """
    Rigid body motions as vectors in the numbering of matrix
    (6 x dim): translation X, Y, Z and rotation about the axes X, Y, Z
    through point: u = theta x (x - point), plus theta itself on the
    rotational degrees of freedom DRX/DRY/DRZ (beams, shells, discrete
    elements). Lagrange DOFs ('LAGR:DX', ...) and other components stay 0.
    getNodeAndComponentFromDOF: (node from 0, component) per
    degree of freedom (Code-Aster test cases sdll123b, fdlv101a, v17.4).
    """
    pairs = matrix.getDOFNumbering().getNodeAndComponentFromDOF()
    dim = len(pairs)
    vec = np.zeros((6, dim))
    nodes = np.array([p[0] for p in pairs], dtype=np.int64)
    comps = np.array([_DOF_INDEX.get(p[1], -1) for p in pairs])
    ok = (comps >= 0) & (nodes >= 0) & (nodes < xyz.shape[0])
    rel = np.zeros((dim, 3))
    rel[ok] = xyz[nodes[ok]] - np.asarray(point, dtype=float)
    x, y, z = rel[:, 0], rel[:, 1], rel[:, 2]
    for k in range(3):                  # translations
        vec[k, ok & (comps == k)] = 1.0
    # rotation about X: u = (0, -z, y); Y: (z, 0, -x); Z: (-y, x, 0)
    for k, terms in ((3, ((1, -z), (2, y))), (4, ((0, z), (2, -x))),
                     (5, ((0, -y), (1, x)))):
        for c, value in terms:
            sel = ok & (comps == c)
            vec[k, sel] = value[sel]
        vec[k, ok & (comps == k)] = 1.0
    return vec


def _effective_masses(res, mass, indexes, shapes=None):
    """
    Effective mass per mode for the 6 rigid motions R (translation
    X/Y/Z, rotation about the global axes X/Y/Z through the origin), as
    Mecway (manual v33 sec. 6.3: m_eff = Gamma^2, Gamma = phi^T M R, with
    mass-normalised phi; here divided by phi^T M phi, so that any
    normalisation works) and as a fraction of R^T M R. R^T M R includes,
    like Code-Aster's MASS_EFFE_UN_D* (measured: clamped block 0.609971 =
    23.94 / 39.25 kg total), the mass of the constrained nodes; Mecway
    divides by the free mass (same block 0.6225 = 23.94 / 38.47 kg).
    Returns ({index: [m_eff x 6]}, [R^T M R x 6], centre of mass, J_zwp).
    J_zwp: moments of inertia about axes through the centre of mass.
    shapes: {index: real shape} instead of DEPL (complex modes:
    _complex_modes).
    """
    mul, dim = _matvec(mass)
    xyz = np.asarray(res.getMesh().getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    rig = _rigid_vectors(mass, xyz)
    if rig.shape[1] != dim:
        raise ValueError(tr("nummering: {0} vrijheidsgraden, matrix {1}",
                            "numbering: {0} degrees of freedom, matrix "
                            "{1}").format(rig.shape[1], dim))
    m_rig = np.array([mul(r) for r in rig])          # M R (6 x dim)
    total = np.einsum("ij,ij->i", rig, m_rig)        # R^T M R
    out = {}
    for idx in indexes:
        if shapes is not None:
            phi = shapes[idx]
        else:
            phi = np.asarray(res.getField("DEPL", idx).getValues(),
                             dtype=float)
        if len(phi) != dim:
            raise ValueError(tr("mode {0}: {1} waarden, matrix {2}",
                                "mode {0}: {1} values, matrix {2}").format(
                idx, len(phi), dim))
        gen = float(phi.dot(mul(phi)))
        gamma = m_rig.dot(phi)
        out[idx] = list(gamma ** 2 / gen) if gen > 0.0 else [0.0] * 6
    # Centre of mass and inertia about it: R_rot(c) = R_rot(0) -
    # c x R_trans, so J(c) follows from the 6 x 6 mass matrix R^T M R.
    full = rig.dot(m_rig.T)
    mtot = np.mean(np.diag(full)[:3])
    cog = np.zeros(3)
    if mtot > 0.0:
        # R_trans,k^T M R_rot,j = m (e_j x c)_k (coupling term): e.g.
        # cpl[1, 2] = m c_x and cpl[2, 1] = -m c_x
        cpl = full[:3, 3:]
        cog = np.array([cpl[1, 2] - cpl[2, 1], cpl[2, 0] - cpl[0, 2],
                        cpl[0, 1] - cpl[1, 0]]) / (2.0 * mtot)
    j_cog = [total[3 + k] - mtot * (float(cog.dot(cog)) - cog[k] ** 2)
             for k in range(3)]
    return out, list(total), cog, j_cog


def _is_complex(res):
    """True for complex modes (MODE_MECA_C: CALC_MODES with MATR_AMOR,
    bridge_modal_damping)."""
    try:
        return str(res.getType()).upper().startswith("MODE_MECA_C")
    except Exception:
        return False


def _complex_modes(res, mass, indexes):
    """
    Per complex mode {index: dict}:
      fd    : damped frequency [Hz] = Im(s)/2pi (Code-Aster FREQ);
      zeta  : damping ratio -Re(s)/|s| (AMOR_REDUIT);
      fn    : |s|/2pi = fd / sqrt(1 - zeta^2) (with proportional damping
              the undamped natural frequency); None if zeta >= 1;
      decay : -Re(s) = zeta 2 pi fn [1/s] (Mecway's decay rate: amplitude
              ~ exp(-decay t)); None if zeta >= 1;
      scale : complex factor c: the shape to Mecway is Re(c phi);
      shape : Re(c phi), the whole vector (effective mass);
      imag  : |Im(c phi)|_M / |Re(c phi)|_M: 0 = classical (real) mode,
              e.g. with Rayleigh damping; larger with non-proportional
              damping (dampers).
    Phase rotation: theta = arg(phi^T M phi) / 2 (transpose, not
    conjugated) makes the real part as large as possible; then phi_r^T M
    phi_r = 1 (as the real modes, MASS_GENE) and the largest component
    positive. For a classical mode Re(c phi) is then exactly the real
    mass-normalised shape. Without mass matrix: phase of the largest
    component, scale of Code-Aster.
    """
    table = _table_values(res, ("FREQ", "AMOR_REDUIT"))
    mul = None
    if mass is not None:
        mul, dim = _matvec(mass)
    out = {}
    for idx in indexes:
        phi = np.asarray(res.getField("DEPL", idx).getValues(),
                         dtype=complex)
        if mul is not None and len(phi) == dim:
            mphi = mul(phi.real) + 1j * mul(phi.imag)
            rot = np.exp(-0.5j * np.angle(phi.dot(mphi)))
            psi = phi * rot
            gen = float(psi.real.dot(mul(psi.real)))
            gim = float(psi.imag.dot(mul(psi.imag)))
            scale = rot / np.sqrt(gen) if gen > 0.0 else rot
            imag = np.sqrt(gim / gen) if gen > 0.0 else 0.0
        else:
            k = int(np.argmax(np.abs(phi)))
            scale = np.exp(-1j * np.angle(phi[k])) if abs(phi[k]) else 1.0
            psi = phi * scale
            imag = (float(np.linalg.norm(psi.imag)) /
                    max(float(np.linalg.norm(psi.real)), 1.0e-300))
        shape = (phi * scale).real
        k = int(np.argmax(np.abs(shape)))
        if shape[k] < 0.0:
            scale, shape = -scale, -shape
        fd, zeta = table.get(idx, (None, None))
        fd = float(fd) if fd is not None else 0.0
        zeta = float(zeta) if zeta is not None else 0.0
        if abs(zeta) < 1.0e-10:
            zeta = 0.0      # numerically 0 (undamped mode, seen ~1e-13)
        fn = decay = None
        if zeta < 1.0:
            fn = fd / np.sqrt(1.0 - zeta ** 2)
            decay = zeta * 2.0 * np.pi * fn
        out[idx] = {"fd": fd, "zeta": zeta, "fn": fn, "decay": decay,
                    "scale": scale, "shape": shape, "imag": float(imag)}
    return out


def _print_complex_modes(res, mass):
    """
    BRIDGE_MODE lines for complex modes (MODE_MECA_C):
      BRIDGE_MODE <nr> FREQ=<damped, Hz> AMOR_REDUIT=<zeta>
                  FREQ_NAT=<|s|/2pi, Hz> DECAY=<1/s> IMAG=<..>
                  MASS_EFFE_UN_DX=.. .. MASS_EFFE_UN_DRZ=..
    The effective mass (fraction, translations and rotations about the
    origin) is computed by the bridge with the real part of the normalised
    shape (_complex_modes; for classical modes equal to the real modes,
    MC-04). Whether Code-Aster gives MASS_EFFE_UN_* for complex modes too
    is NOT checked; so RECU_TABLE is not requested here.
    """
    indexes = sorted(res.getIndexes())
    modes = _complex_modes(res, mass, indexes)
    meff = {}
    absolute = {}
    if mass is not None:
        try:
            meff, total, cog, j_cog = _effective_masses(
                res, mass, indexes,
                shapes=dict((i, m["shape"]) for i, m in modes.items()))
            print("BRIDGE_MASSA M={0} JX={1} JY={2} JZ={3} ZWP={4},{5},{6} "
                  "JZX={7} JZY={8} JZZ={9}".format(*[_num(v) for v in (
                      [total[0]] + total[3:] + list(cog) + j_cog)]))
            absolute = meff
            meff = dict((i, [v / t if t > 0.0 else 0.0
                             for v, t in zip(meff[i], total)])
                        for i in meff)
        except Exception as e:
            print(tr("aster_results_export: WAARSCHUWING: effectieve massa "
                     "complexe modes niet berekend: {0}",
                     "aster_results_export: WARNING: effective mass of the "
                     "complex modes not computed: {0}").format(e))
            meff = {}
            absolute = {}
    _store_mode_globals(res, indexes, absolute, meff)
    for idx in indexes:
        m = modes[idx]
        parts = ["BRIDGE_MODE {0} FREQ={1} AMOR_REDUIT={2}".format(
            idx, _num(m["fd"]), _num(m["zeta"]))]
        if m["fn"] is not None:
            parts.append("FREQ_NAT={0} DECAY={1}".format(
                _num(m["fn"]), _num(m["decay"])))
        parts.append("IMAG={0:.3g}".format(m["imag"]))
        for key, value in zip(_MASS_FRACTIONS + _ROT_FRACTIONS,
                              meff.get(idx, [])):
            parts.append("{0}={1:.6g}".format(key, float(value)))
        print(" ".join(parts))
        if m["fn"] is None:
            print("BRIDGE_COMPLEX_OVERKRITISCH mode={0} zeta={1:.6g}".format(
                idx, m["zeta"]))


def print_modes(res, mass=None):
    """
    Overview per mode in the .mess, read by the bridge
    (bridge_results_liml.read_mode_summary):
      BRIDGE_MODE <nr> FREQ=<Hz> MASS_EFFE_UN_DX=.. MASS_EFFE_UN_DY=.. ..
                  MASS_EFFE_UN_DRX=.. MASS_EFFE_UN_DRY=.. MASS_EFFE_UN_DRZ=..
      BRIDGE_MODE <nr> CHAR_CRIT=<buckling load factor>
      BRIDGE_MASSA M=.. JX=.. JY=.. JZ=.. ZWP=x,y,z JZX=.. JZY=.. JZZ=..
    mass: the assembled mass matrix (MASS_MECA) for the rotations;
    None = only the translations of Code-Aster. JX/JY/JZ: R^T M R of the
    rotations about the axes through the origin (denominator of the
    fractions); JZX/JZY/JZZ: about the axes through the centre of mass ZWP.
    """
    kind = _mode_kind(res)
    if kind is None:
        return
    try:
        if kind == "buckling":
            for nr, (cc,) in sorted(_table_values(
                    res, ("CHAR_CRIT",)).items()):
                print("BRIDGE_MODE {0} CHAR_CRIT={1}".format(
                    nr, _num(cc)))
            return
        if _is_complex(res):
            _print_complex_modes(res, mass)
            return
        if _is_acoustic(res):
            # Cavity modes: no effective mass (RECU_TABLE MASS_EFFE_UN_DX
            # would give an <EXCEPTION> in the .mess).
            for nr, freq in sorted(_mode_values(res, kind).items()):
                print("BRIDGE_MODE {0} FREQ={1}".format(nr, _num(freq)))
            return
        try:
            fractions = _table_values(res, _MASS_FRACTIONS)
        except Exception as e:
            print(tr("aster_results_export: effectieve massa niet "
                     "beschikbaar: {0}",
                     "aster_results_export: effective mass not available: "
                     "{0}").format(e))
            fractions = {}
        values = _mode_values(res, kind)
        rot, absolute = _rotation_fractions(res, mass, sorted(values),
                                            fractions)
        # For export_results: Mecway's globalvariables per mode
        # (translations: MASS_EFFE_UN_D* from Code-Aster itself)
        _store_mode_globals(res, values, absolute, dict(
            (nr, [None if v is None else float(v) for v in
                  (list(fractions.get(nr, [])) + [None] * 3)[:3]] +
             list(rot.get(nr, [None] * 3))) for nr in values))
        for nr, freq in sorted(values.items()):
            parts = ["BRIDGE_MODE {0} FREQ={1}".format(nr, _num(freq))]
            items = list(zip(_MASS_FRACTIONS, fractions.get(nr, [])))
            items += list(zip(_ROT_FRACTIONS, rot.get(nr, [])))
            for key, value in items:
                if value is not None:
                    parts.append("{0}={1:.6g}".format(key, float(value)))
            print(" ".join(parts))
    except Exception as e:
        print(tr("aster_results_export: WAARSCHUWING: modeoverzicht: {0}",
                 "aster_results_export: WARNING: mode summary: {0}").format(
            e))


def _rotation_fractions(res, mass, indexes, fractions):
    """
    ({index: [fraction rotation X, Y, Z]}, {index: [m_eff x 6]}) from
    _effective_masses, or ({}, {}) without mass matrix or on an error.
    Check: the translations computed here must equal
    Code-Aster's MASS_EFFE_UN_D* (otherwise the mapping of DOFs and
    nodes is wrong: no rotations and no absolute mass).
    """
    if mass is None:
        return {}, {}
    try:
        meff, total, cog, j_cog = _effective_masses(res, mass, indexes)
    except Exception as e:
        print(tr("aster_results_export: WAARSCHUWING: effectieve massa "
                 "rotaties niet berekend: {0}",
                 "aster_results_export: WARNING: effective mass of the "
                 "rotations not computed: {0}").format(e))
        return {}, {}
    worst = 0.0
    for idx in indexes:
        for k, ref in enumerate(fractions.get(idx, [])):
            if ref is not None and total[k] > 0.0:
                worst = max(worst, abs(meff[idx][k] / total[k] - float(ref)))
    if worst > 1.0e-4:
        print(tr("aster_results_export: WAARSCHUWING: effectieve massa "
                 "rotaties niet gegeven: de eigen berekening van de "
                 "translaties wijkt {0:.3g} af van MASS_EFFE_UN_D* van "
                 "Code-Aster.",
                 "aster_results_export: WARNING: effective mass of the "
                 "rotations not given: the own calculation of the "
                 "translations differs {0:.3g} from Code-Aster's "
                 "MASS_EFFE_UN_D*.").format(worst))
        return {}, {}
    print("BRIDGE_MASSA M={0} JX={1} JY={2} JZ={3} ZWP={4},{5},{6} JZX={7} "
          "JZY={8} JZZ={9}".format(*[_num(v) for v in (
              [total[0]] + total[3:] + list(cog) + j_cog)]))
    return (dict((idx, [meff[idx][3 + k] / total[3 + k]
                        if total[3 + k] > 0.0 else 0.0 for k in range(3)])
                 for idx in indexes),
            dict((idx, list(meff[idx])) for idx in indexes))


def _stiffness_scales(res, rigi_geo, values):
    """
    {index: factor} so that the buckling shape phi * factor has generalised
    stiffness 1 (phi^T K phi = 1), as Mecway (recomputed:
    BucklingBeam tip 0.0014040 = 1/sqrt(EI (pi/2L)^4 L/2)). NORM_MODE
    RIGI_GENE cannot do that for MODE_FLAMB (<EXCEPTION> ALGELINE4_77
    "l'option de normalisation RIGI_GENE n'est pas implantée", seen).
    From K phi = -CHAR_CRIT Kg phi follows |phi^T K phi| = |CHAR_CRIT
    phi^T Kg phi|; Kg has no terms on the Lagrange DOFs.
    rigi_geo: the assembled RIGI_GEOM (getValuesWithDescription gives
    both triangles, assemblymatrix_ext.py v17.4); the vector of DEPL
    has the same numbering (length checked).
    """
    data, rows, cols, dim = rigi_geo.getValuesWithDescription()
    data, rows, cols = np.asarray(data), np.asarray(rows), np.asarray(cols)
    out = {}
    for idx, factor in values.items():
        x = np.asarray(res.getField("DEPL", idx).getValues(), dtype=float)
        if len(x) != dim:
            print(tr("aster_results_export: WAARSCHUWING: normering "
                     "knikvorm {0}: {1} waarden, matrix {2}; niet "
                     "genormeerd.",
                     "aster_results_export: WARNING: normalising buckling "
                     "mode {0}: {1} values, matrix {2}; not "
                     "normalised.").format(idx, len(x), dim))
            continue
        k_gen = abs(factor * float(np.sum(data * x[rows] * x[cols])))
        if k_gen > 0.0:
            out[idx] = 1.0 / np.sqrt(k_gen)
    return out


def _times(res, indexes):
    """{index: time} from the access parameter INST (else the index)."""
    try:
        acc = res.getAccessParameters()
        return dict(zip(acc["NUME_ORDRE"], acc["INST"]))
    except Exception:
        return dict((i, float(i)) for i in indexes)


def export_results(res, out_path, liml_path, fields=None, extra_results=None,
                   precision="single", static=None, rigi_geo=None,
                   mass=None, node_fields=None, cyclic=None, opt_in=None,
                   shell_vectors=None, strengths=None, u_axes=None):
    """
    Write all archived time steps of res as a Mecway <results>
    fragment (bytes, CRLF, indented for placement in <solution>).

    Parameters
    ----------
    res           : Code-Aster result (after CALC_CHAMP).
    out_path      : target file of the fragment (first .tmp, then renamed).
    liml_path     : the .liml the mesh was written from (elsets,
                    elements and the check of the node order).
    fields        : list of groups from RESULT_FIELD_SPECS (e.g.
                    ["displacements", "stresses", "vonmises", "reactions"]);
                    None = everything that is in res.
    extra_results : {"res_sup": ..., "res_moy": ..., "res_inf": ...}
                    (POST_CHAMP EXTR_COQUE for shells), or None.
    precision     : "single" (float32, as Mecway for OpenRadioss) or
                    "double".
    static        : True/False, or None = automatic (_is_static).
    rigi_geo      : buckling: the assembled RIGI_GEOM; the buckling shapes
                    are then normalised to phi^T K phi = 1 (as
                    Mecway, _stiffness_scales). None = as computed.
    mass          : complex modes (MODE_MECA_C): the assembled
                    MASS_MECA; the real part of the shape is then
                    normalised to phi^T M phi = 1 (_complex_modes). Each
                    mode gets <mode frequency="f_d Hz" decayrate=".. 1/s">,
                    as Mecway's complex (acoustic) modes.
    node_fields   : {Mecway name: (node numbers, values)} that are equal in
                    every step (fatigue: damage, life; aster_fatigue),
                    or None. Node numbers from 1.
    cyclic        : {"axis": 0/1/2 (X/Y/Z), "segments": N} for cyclic
                    symmetry (bridge_cyclic), or None. If the mesh of
                    res has more nodes than the .liml (the skeleton of the
                    whole wheel, aster_cyclic.collect), the result goes to
                    Mecway's whole wheel (aster_cyclic.wheel_model: node i
                    + j x n, element e + j x ne), nodal fields only.
    opt_in        : without fields: the chosen groups from OPT_IN_GROUPS
                    (bridge_to_aster._results_route); None = none.
    shell_vectors : {Mecway elset: (vx, vy, vz)} reference vector of the
                    shells (AFFE_CARA_ELEM COQUE VECTEUR); without: X.
    strengths     : {Mecway elset: tensilestrength [Pa]} for the factor
                    of safety (von Mises failure criterion).
    u_axes        : [((ux, uy, uz), [(first eid, last eid), ...]), ...]:
                    Mecway's U direction of shells from an Element
                    orientation card (bridge_orientation; the attributes
                    orientationux/uy/uz are read from the .liml itself).

    Returns
    -------
    dict with statistics (steps, variables, bytes, seconds), or None on
    an error (message in the .mess; the .resu route then remains usable).
    """
    t0 = time.time()
    try:
        return _export(res, out_path, liml_path, fields, extra_results,
                       precision, static, t0, rigi_geo, mass, node_fields,
                       cyclic, opt_in, {"shell_vectors": shell_vectors,
                                        "strengths": strengths},
                       u_axes)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(tr("aster_results_export: FOUT: {0}",
                 "aster_results_export: ERROR: {0}").format(e))
        return None


def _export(res, out_path, liml_path, fields, extra_results, precision,
            static, t0, rigi_geo=None, mass=None, node_fields=None,
            cyclic=None, opt_in=None, derived=None, u_axes=None):
    """Work of export_results (without the error handling)."""
    model = read_liml_model(liml_path)
    for vec, ranges in u_axes or ():
        for first, last in ranges:
            for eid in range(first, last + 1):
                model["uaxes"][eid] = tuple(vec)
    n = model["coords"].shape[0]
    mesh = res.getMesh()
    rows = None
    xyz = np.asarray(mesh.getCoordinates().getValues(), dtype=float)
    if cyclic and xyz.size // 3 != n:
        # Whole wheel (aster_cyclic.collect): Mecway's numbering, nodes
        # matched by coordinate to the skeleton.
        import aster_cyclic
        model = aster_cyclic.wheel_model(model, int(cyclic["axis"]),
                                         int(cyclic["segments"]))
        rows, err = aster_cyclic.node_rows(xyz, model["coords"])
        n = model["coords"].shape[0]
    else:
        err = _check_node_order(mesh, model["coords"])
    if err:
        print(tr("aster_results_export: FOUT: {0}",
                 "aster_results_export: ERROR: {0}").format(err))
        return None

    results = {"res": res}
    results.update(extra_results or {})
    indexes = list(res.getIndexes())
    modes = _mode_kind(res)
    if modes:
        static = False
    if static is None:
        static = _is_static(res, indexes)
    if static:
        indexes = indexes[:1]
    groups = set(fields) if fields is not None else None
    conn = mesh.getConnectivity()
    lump = None
    pairs = _offset_pairs(mesh, n) if rows is None else None
    if rows is None and (groups is None or "reactions" in groups):
        lump = _reaction_lumping(mesh, conn, n,
                                 None if pairs is None else pairs[1])
    data = _Fields(results, n, lump, rows, pairs)
    if rows is None:
        data.alias = _node_alias(
            xyz.size // 3, n,
            _coincident_extra(xyz.reshape(-1, 3), n,
                              () if pairs is None else pairs[1]),
            pairs)
    mode_values = _mode_values(res, modes) if modes else None
    if modes == "buckling" and rigi_geo is not None:
        data.scales = _stiffness_scales(res, rigi_geo, mode_values)
    if modes and _is_acoustic(res):
        data.scales = _mass_scales(res, indexes)
    decays = None
    if modes and _is_complex(res):
        cplx = _complex_modes(res, mass, indexes)
        data.scales = dict((i, c["scale"]) for i, c in cplx.items())
        mode_values = dict((i, c["fd"]) for i, c in cplx.items())
        decays = dict((i, c["decay"]) for i, c in cplx.items())
    data.set_index(indexes[-1])
    opt_in = frozenset(opt_in or ())
    variables = _plan_variables(data, model, conn, groups,
                                magnitudes=modes != "frequency",
                                opt_in=opt_in, derived=derived)
    variables += _constant_vars(node_fields, n)
    if not variables:
        print(tr("aster_results_export: FOUT: geen enkel veld gevonden.",
                 "aster_results_export: ERROR: no field found at all."))
        return None
    _report_missing(results, groups, opt_in,
                    any(v[0] in SOLID_SHAPES
                        for v in model["elements"].values()))
    elset_nodes, free_nodes = _group_nodes(model, n)
    for var in variables:
        _assign_groups(var, model, elset_nodes, free_nodes)

    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        _write_fragment(f, variables, data, indexes,
                        None if (static or modes) else _times(res, indexes),
                        precision, model,
                        (modes, mode_values, decays) if modes else None,
                        _MODE_GLOBALS.get(id(res)) if modes else None)
        size = f.tell()
    os.replace(tmp, out_path)
    stats = {"stappen": len(indexes),
             "variabelen": [v.name for v in variables],
             "bytes": size, "seconden": time.time() - t0,
             "statisch": static, "modes": modes}
    print("aster_results_export: {0} geschreven: {1} stap(pen), {2} "
          "variabelen ({3}), {4:.1f} MB in {5:.2f} s.".format(
              out_path, stats["stappen"], len(variables),
              ", ".join(stats["variabelen"]), size / 1.0e6,
              stats["seconden"]))
    return stats


def _constant_vars(node_fields, n):
    """_Var's for fields that are equal in every step (node_fields of
    export_results), with ascending node numbers <= n."""
    out = []
    for name, (ids, vals) in (node_fields or {}).items():
        ids = np.asarray(ids, dtype="<i4")
        vals = np.asarray(vals, dtype=float)
        order = np.argsort(ids)
        ids, vals = ids[order], vals[order]
        keep = (ids >= 1) & (ids <= n)
        if not keep.any():
            continue
        ids, vals = ids[keep], vals[keep]
        out.append(_Var(name, False, ids, lambda fields, v=vals: v))
    return out


def _group_nodes(model, n):
    """({elset: ascending node numbers}, nodes in no element at all)."""
    elset_nodes = OrderedDict()
    used = np.zeros(n + 1, dtype=bool)
    for name, eids in model["elsets"].items():
        nids = sorted(set(nid for e in eids
                          for nid in model["elements"][e][1]))
        elset_nodes[name] = np.array(nids, dtype="<i4")
        used[nids] = True
    free_nodes = np.nonzero(~used[1:])[0].astype("<i4") + 1
    return elset_nodes, free_nodes


def _write_fragment(f, variables, data, indexes, times, precision, model,
                    modes=None, mode_globals=None):
    """
    Write <results> to the open file f. times = {index: time} gives
    one <timestep> per index; times = None is static (one index, the
    variables directly under <results>). modes = (kind, {index: value},
    {index: decay rate} or None) gives one <mode> per index (see header);
    with a decay rate (complex modes) also decayrate="<1/s>", as
    Mecway's complex acoustic modes (seen headless, Mecway 33:
    <mode id="2" frequency="170.000069959994 Hz" decayrate="70.347 1/s">).
    mode_globals: {index: [(name, value)]} (_store_mode_globals) as
    <globalvariable> directly after <mode>, as Mecway.
    """
    dtype = "<f4" if precision == "single" else "<f8"
    values_tag = "valuessingle" if precision == "single" else "valuesdouble"
    indent = ("      " if (times is None and modes is None)
              else "        ")
    f.write('    <results precision="{0}">\r\n'.format(precision)
            .encode("ascii"))
    for var in variables:
        f.write(_ids_block(var, "      "))
    for k, idx in enumerate(indexes):
        data.set_index(idx)
        if modes is not None:
            value = modes[1].get(idx, 0.0)
            attr = ('bucklingfactor="{0}"'.format(_num(value))
                    if modes[0] == "buckling"
                    else 'frequency="{0} Hz"'.format(_num(value)))
            decay = (modes[2] or {}).get(idx) if len(modes) > 2 else None
            if decay is not None:
                attr += ' decayrate="{0} 1/s"'.format(_num(decay))
            f.write('      <mode id="{0}" {1}>\r\n'.format(k + 1, attr)
                    .encode("ascii"))
            for name, value in (mode_globals or {}).get(idx, ()):
                f.write('        <globalvariable name="{0}">{1}'
                        '</globalvariable>\r\n'.format(name, _num(value))
                        .encode("ascii"))
        elif times is not None:
            f.write('      <timestep id="{0}" time="{1} s">\r\n'.format(
                k, _num(times.get(idx, idx))).encode("ascii"))
        for var in variables:
            vals = var.getter(data)
            if vals is None:
                print(tr("aster_results_export: WAARSCHUWING: '{0}' "
                         "ontbreekt in index {1}; nullen geschreven.",
                         "aster_results_export: WARNING: '{0}' missing in "
                         "index {1}; zeros written.").format(var.name, idx))
                vals = np.zeros(_value_count(var, model))
            f.write(_var_block(var, vals, indent, dtype, values_tag))
        if modes is not None:
            f.write(b"      </mode>\r\n")
        elif times is not None:
            f.write(b"      </timestep>\r\n")
    f.write(b"    </results>\r\n")


def _value_count(var, model):
    """Number of values of a variable per time step."""
    if not var.element:
        return len(var.ids)
    return sum(len(model["elements"][e][1]) for e in var.ids)


def _report_missing(results, groups_wanted, opt_in=frozenset(),
                    solids=True):
    """Report fields from FIELD_TABLE that are not in the result.
    solids False (no volume elements): the strain of res (EPSI/EPSG,
    volumes only) does not belong there; shells have their strain in eps_sup/
    eps_moy/eps_inf (_plan_derived)."""
    missing = set()
    names = {}
    for rkey, r in results.items():
        try:
            names[rkey] = list(r.getFieldsNames())
        except Exception:
            names[rkey] = []
    for group, rkey, field, _c, _n, _k in FIELD_TABLE:
        if not _wanted(group, groups_wanted, opt_in):
            continue
        if groups_wanted is None and group in ("temperature", "heat_flux"):
            continue    # thermal: only if they are requested
        if rkey not in results:
            continue
        if group == "strain" and not field.startswith(
                "EPSG" if "EPSG_NOEU" in names[rkey] else "EPSI"):
            continue    # small strains or Green-Lagrange, one of the two
        if group == "strain" and rkey == "res" and not solids:
            continue    # shells/beams only: no volume strain
        if field not in names[rkey]:
            missing.add("{0}:{1}".format(rkey, field))
    if missing:
        print(tr("aster_results_export: niet in het resultaat "
                 "(overgeslagen): {0}",
                 "aster_results_export: not in the result (skipped): "
                 "{0}").format(", ".join(sorted(missing))))
