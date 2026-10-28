# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_from_liml.py
# Reads the active Mecway .liml file (XML format) and extracts all
# data needed for Code-Aster.
#
# Supported Mecway <geometric> types:
#   CircularBar           -> CERCLE (solid)
#   UniformCircularTube   -> CERCLE (hollow: roundod, roundid)
#   RectBar               -> RECTANGLE (solid: recta, rectb)
#   RectTube              -> RECTANGLE (hollow: recta, rectb, rectthickness)
#   UniformGeneralSection -> GENERALE (given A, iyy, izz, torsionconstant)
#   I, T, L, C            -> GENERALE (A, IY, IZ, JX computed as Mecway does,
#                            see _profile_props)
#   Plate                 -> COQUE (thickness)
#
# Supported <mechanical> types:
#   Isotropic -> DEFI_MATERIAU ELAS (E, NU, RHO)
#   Spring    -> AFFE_CARA_ELEM DISCRET K_T_D_L (springconstant)
#   Damper    -> DIS_T with A_T_D_L (dampingcoefficient)
#   Gap       -> DIS_T with RELATION='DIS_CHOC' (closedstiffness)
#   TensionOnly -> MODELISATION='CABLE' (youngsmodulus + cross-section)
# Truss elements (<elem ... truss="true">) -> MODELISATION='BARRE' with the
#   cross-section area (_split_trusses).
# Configurations and groups: suppressed items are dropped
#   (_apply_suppression).
#
# Mechanical model items without a selection BC (_parse_model_item):
#   thermalstress + temperature2 (+ temperature3 per node,
#   _parse_node_temperatures), rayleighdamping, constraintequation,
#   mass2, rotationalinertia; bonded contact2 -> model_data["bonded"].
# Element orientation cards (<orientation>): bridge_orientation.
#
# Supported <nodesurfacecoupling> types:
#   rbe3      -> LIAISON_RBE3 (weighted average, master follows slaves)
#   rigidbody -> LIAISON_SOLIDE (master and slaves together form 1 rigid body)
#
# Compatible with IronPython 2.7.9.

import math
import xml.etree.ElementTree as ET
from bridge_utils import (log, parse_and_convert, CONFIG_BRIDGE,
                          resolve_auto_analysis, tr,
                          choose_configuration, configuration_warning)
from bridge_bcs import (SUPPORTED_BCS, _parse_direction, _parse_value,
                        is_position)
import bridge_radioss
import bridge_custom
import bridge_thermal
import bridge_acoustic
import bridge_vibroacoustic
import bridge_cyclic
import bridge_offset
import bridge_orientation
import bridge_plane

# ------------------------------------------------------------------
# CONSTANTS: element shapes per dimension
# ------------------------------------------------------------------
_DIM_1D_SHAPES = frozenset({"line2", "line3"})
_DIM_2D_SHAPES = frozenset({"tri3", "tri6", "quad4", "quad8"})
_DIM_3D_SHAPES = frozenset({
    "hex8", "hex20", "tet4", "tet10",
    "pyr5", "pyr13", "wedge6", "wedge15",
})

# MODELISATION values that introduce rotation DOFs (DRX/DRY/DRZ).
# DIS_T (spring) and BARRE have translation DOFs only and are
# NOT listed here.
_ROT_DOF_MODELISATIONS = frozenset({
    "POU_D_T", "POU_D_E", "POU_D_T_GD",
    "COQUE_3D", "DKT", "DST", "Q4G",
    "DIS_TR",
})

# Choices for the element formulation (CONFIG_BRIDGE "elem_*"): allowed
# values, the first one is the default.
_ELEM_CHOICES = {
    "elem_hex8":  ("3D", "3D_SI", "LINE_QUAD"),
    "elem_shell": ("DKT", "DST", "COQUE_3D"),
    "elem_beam":  ("POU_D_E", "POU_D_T", "POU_D_T_GD"),
}

# Beam with large displacements and rotations (elem_beam choice, STAPPENPLAN
# S20; route from the fork by MishalTPC,
# github.com/mishal0488/MecwayAsterBridge): only in nonlinear static, see
# _gd_beam_choice.
GD_BEAM = "POU_D_T_GD"
# Beam modelisations with AY/AZ for SECTION='GENERALE' (shear deformation)
_SHEAR_BEAMS = ("POU_D_T", GD_BEAM)


def _parse_bilinear(plastic_node, mat_name, plastic_type, E=None):
    """
    Bilinear hardening -> {"sy", "et", "h", "kinematic"} (SI) or None.
    Code-Aster: ECRO_LINE SY / D_SIGM_EPSI (slope of the tensile curve after
    the yield point in TOTAL strain; U4.43.01 ECRO_LINE) with VMIS_ISOT_LINE or
    VMIS_CINE_LINE. Mecway's "tangent modulus" is the plastic modulus H
    (stress versus plastic strain): measured headless with Mecway/CCX (the
    internal solver does not compute plasticity), bar 1% strain, H = 100 GPa:
    CCX 915.8 MPa, read as H 914.5 MPa, as slope in total strain
    1181 MPa (verification NL-01). Hence D_SIGM_EPSI = E H / (E + H),
    as in _kinematic_curve.
    """
    sy = parse_and_convert(plastic_node.get("yieldstrength", "0"), "pressure")
    h = parse_and_convert(plastic_node.get("tangentmodulus", "0"),
                          "pressure")
    try:
        sy, h = float(sy), float(h)
    except (TypeError, ValueError):
        sy = h = 0.0
    try:
        e_mod = float(E)
    except (TypeError, ValueError):
        e_mod = 0.0
    if h > 0.0 and e_mod > 0.0:
        et = e_mod * h / (e_mod + h)
    else:
        et = max(h, 0.0) if e_mod <= 0.0 else 0.0
    if sy <= 0.0:
        log(tr("ERROR: Plasticiteit van materiaal '{0}' ({1}): geen geldige "
               "yieldstrength ({2}); materiaal elastisch gerekend.",
               "ERROR: Plasticity of material '{0}' ({1}): no valid "
               "yieldstrength ({2}); material computed as elastic.").format(
                mat_name, plastic_type, plastic_node.get("yieldstrength")))
        return None
    kinematic = plastic_type == "BilinearKinematic"
    log("INFO: Material '{0}': bilinear {1} hardening, SY={2} Pa, "
        "H={3} Pa (Mecway tangent modulus) -> D_SIGM_EPSI={4} Pa "
        "({5}).".format(
            mat_name, "kinematic" if kinematic else "isotropic", sy, h, et,
            "VMIS_CINE_LINE" if kinematic else "VMIS_ISOT_LINE"))
    return {"sy": sy, "et": et, "h": h, "kinematic": kinematic}


def _parse_hyperelastic(mech_node, dens_node, mech_type, mat_name):
    """
    Mecway Neo Hooke / Mooney-Rivlin (manual par. 8.8; Mecway 34 only in
    Nonlinear static 3D and Nonlinear dynamic response 3D) -> material
    dict with "hyper": {"C10", "C01", "K"} (SI), or None after an ERROR.
    XML (attribute names from a save_as round trip in Mecway 34 headless,
    22 Oct 2026: other names were dropped):
      <mechanical type="NeoHooke" hyperelasticc10="1 MPa" d1="1E-09 m2/N"
                  thermalexpansion=".." />
      <mechanical type="MooneyRivlin" hyperelasticc10=".." hyperelasticc01=".."
                  d1=".." thermalexpansion=".." />
    Code-Aster: DEFI_MATERIAU ELAS_HYPER (C10, C01, K, RHO) with
    RELATION='ELAS_HYPER', DEFORMATION='GREEN_LAGRANGE' (catalogue
    defi_materiau.py; test case ssnv187a). Volumetric term: Mecway/CCX
    (Abaqus form) U = (J - 1)^2 / D1, Code-Aster K/2 (J - 1)^2, so
    K = 2 / D1 (NOT verified in the Fortran; checked with runs: cube in
    uniaxial tension/compression against 2 (lambda - lambda^-2)
    (C10 + C01/lambda), verification NL-50).
    E and NU are the small-strain equivalents (G = 2 (C10 + C01),
    E = 9 K G / (3 K + G) = 2 G (1 + NU)): only for the explicit time
    step and other estimates, ELAS is not written (ELAS and ELAS_HYPER
    exclude each other in DEFI_MATERIAU).
    """
    c10 = parse_and_convert(mech_node.get("hyperelasticc10", "0"),
                            "pressure")
    c01 = 0.0
    if mech_type == "MooneyRivlin":
        c01 = parse_and_convert(mech_node.get("hyperelasticc01", "0"),
                                "pressure")
    d1 = parse_and_convert(mech_node.get("d1", "0"), "inverse_pressure")
    texp = parse_and_convert(mech_node.get("thermalexpansion", "0"),
                             "inversetemp")
    g = 2.0 * (c10 + c01)
    if g <= 0.0:
        log(tr("ERROR: Materiaal '{0}' ({1}): C10 + C01 = {2} Pa; de "
               "beginschuifmodulus 2 (C10 + C01) moet positief zijn.",
               "ERROR: Material '{0}' ({1}): C10 + C01 = {2} Pa; the "
               "initial shear modulus 2 (C10 + C01) must be positive.")
            .format(mat_name, mech_type, c10 + c01))
        return None
    if d1 <= 0.0:
        log(tr("ERROR: Materiaal '{0}' ({1}): D1 = {2}. D1 = 0 betekent "
               "volledig onsamendrukbaar; Code-Aster ELAS_HYPER heeft een "
               "eindige compressiemodulus K = 2/D1 nodig. Geef in Mecway "
               "D1 > 0, bijv. D1 = 2/K met K ongeveer 1000 x de "
               "schuifmodulus 2 (C10 + C01), hier D1 = {3} m2/N "
               "(nagenoeg onsamendrukbaar).",
               "ERROR: Material '{0}' ({1}): D1 = {2}. D1 = 0 means fully "
               "incompressible; Code-Aster ELAS_HYPER needs a finite bulk "
               "modulus K = 2/D1. Give D1 > 0 in Mecway, e.g. D1 = 2/K "
               "with K about 1000 x the shear modulus 2 (C10 + C01), here "
               "D1 = {3} m2/N (nearly incompressible).").format(
                   mat_name, mech_type, d1, "%.3g" % (2.0 / (1000.0 * g))))
        return None
    k = 2.0 / d1
    e_eq = 9.0 * k * g / (3.0 * k + g)
    nu_eq = (3.0 * k - 2.0 * g) / (2.0 * (3.0 * k + g))
    if texp:
        log(tr("WARNING: Materiaal '{0}' ({1}): de thermische uitzetting "
               "wordt genegeerd; ELAS_HYPER van Code-Aster heeft geen "
               "ALPHA.",
               "WARNING: Material '{0}' ({1}): the thermal expansion is "
               "ignored; Code-Aster's ELAS_HYPER has no ALPHA.").format(
                   mat_name, mech_type))
    rho = 0.0
    if dens_node is not None:
        rho = parse_and_convert(dens_node.get("density", "0"), "density")
    log("INFO: Material '{0}' -> ELAS_HYPER ({1}): C10={2} Pa, C01={3} Pa, "
        "K=2/D1={4} Pa, rho={5} kg/m3 (small strain: E={6} Pa, "
        "NU={7}).".format(mat_name, mech_type, c10, c01, k, rho,
                          "%.6g" % e_eq, "%.6f" % nu_eq))
    return {"E": e_eq, "NU": nu_eq, "Texp": 0.0, "rho": rho,
            "hyper": {"type": mech_type, "C10": c10, "C01": c01, "K": k}}


def _curve_young(curve, E, mat_name, definition):
    """
    E of a material with a hardening curve read as TOTAL strain: the slope
    of the first segment (origin -> first point with strain > 0), as
    Mecway does. Mecway's Plastic tab: the first two points define the
    linear elastic region. Measured headless (Mecway 34 + CCX, bar in
    uniaxial tension, 22 Oct 2026): youngsmodulus 200 GPa with curve
    (0, 0), (0.001, 210 MPa), (0.011, 310 MPa) gave at strain 5e-4 a
    stress of 104.97 MPa in Nonlinear static and 105.00 MPa in Linear
    static (CCX), so E = 210 GPa (the curve), not 200 GPa (Elastic tab).
    A curve with a first point at strain > 0 (no (0, 0)) also gets the
    slope origin -> first point, as Mecway: measured the same way with
    curve (0.001, 210 MPa), (0.011, 310 MPa): 104.98 MPa (nonlinear, CCX)
    and 105.00 MPa (linear, CCX), so 210 GPa (verification NL-04c).
    Code-Aster stops with MATERIAL1_5 when the slope up to the first
    TRACTION point differs by more than 1% from ELAS E
    (MacroCommands/defi_materiau_ops.py, check_young_consistency).
    definition 'auto' as in _to_aster_traction_curve: (0, 0) or a first
    strain > 0 -> total; (0, sigma > 0) -> plastic (E unchanged).
    Returns E [Pa] (unchanged for the plastic definition or an unusable
    curve).
    """
    if not curve or definition not in ("auto", "total"):
        return E
    first = curve[0]
    if definition == "auto" and first[0] == 0.0 and first[1] > 0.0:
        return E
    pts = [(eps, sig) for eps, sig in curve if eps > 0.0]
    if not pts or pts[0][1] <= 0.0:
        return E
    slope = pts[0][1] / pts[0][0]
    try:
        e_tab = float(E)
    except (TypeError, ValueError):
        e_tab = 0.0
    if e_tab > 0.0 and abs(slope - e_tab) <= 1.0e-6 * e_tab:
        return E
    log(tr("WARNING: Materiaal '{0}': E = {1} Pa (helling van het eerste "
           "stuk van de hardingscurve, zoals Mecway) i.p.v. "
           "youngsmodulus {2} Pa van het tabblad Elastic. Mecway gebruikt "
           "voor dit materiaal de helling van de curve; Code-Aster eist "
           "dat E en de curve op 1% overeenkomen (MATERIAL1_5).",
           "WARNING: Material '{0}': E = {1} Pa (slope of the first segment "
           "of the hardening curve, as Mecway does) instead of "
           "youngsmodulus {2} Pa from the Elastic tab. Mecway uses the "
           "slope of the curve for this material; Code-Aster requires E "
           "and the curve to agree within 1% (MATERIAL1_5).").format(
               mat_name, "%.6g" % slope, "%.6g" % e_tab))
    return slope


def _kinematic_curve(curve, E, mat_name, definition):
    """
    Kinematic hardening curve (Mecway "Plastic with kinematic hardening",
    manual v33 par. 8.8) -> {"sy", "et", "kinematic": True} or None.
    For von Mises, Code-Aster has no kinematic hardening with an
    arbitrary curve: VMIS_CINE_LINE (and VMIS_ECMI_*) is linear
    kinematic (Prager), VMIS_CIN1/2_CHAB is a different (Chaboche) law.
    If the hardening after the yield point is linear (one segment, or all
    segments with the same slope H in plastic strain), the curve
    equals BilinearKinematic and it becomes VMIS_CINE_LINE with
    D_SIGM_EPSI = E H / (E + H) (slope in total strain, as in
    _parse_bilinear). Otherwise None (reported; the material stays elastic).
    definition: 'auto', 'plastic' or 'total' (CONFIG
    plastic_strain_definition, as in _to_aster_traction_curve).
    """
    first = curve[0]
    if definition == "auto":
        if first[0] == 0.0 and first[1] == 0.0:
            definition = "total"
        elif first[0] == 0.0 and first[1] > 0.0:
            definition = "plastic"
    if definition == "plastic" and first[0] == 0.0:
        pts = list(curve)
    elif definition == "total" and E > 0.0:
        pts = [(eps - sig / E, sig) for eps, sig in curve if eps != 0.0]
    else:
        pts = []
    why = None
    if not pts or pts[0][1] <= 0.0:
        why = tr("eerste punt {0} niet als vloeigrens te lezen",
                 "first point {0} cannot be read as the yield point"
                 ).format(first)
    else:
        sy = pts[0][1]
        h = 0.0
        if len(pts) > 1 and pts[-1][0] > pts[0][0]:
            h = (pts[-1][1] - sy) / (pts[-1][0] - pts[0][0])
        tol = 1.0e-3 * max(abs(h), 1.0e-6 * E)
        for (e0, s0), (e1, s1) in zip(pts, pts[1:]):
            if e1 <= e0 or abs((s1 - s0) / (e1 - e0) - h) > tol:
                why = tr("versteviging niet lineair",
                         "hardening not linear")
                break
    if why is not None:
        log(tr("WARNING: Materiaal '{0}': kinematische hardingscurve niet "
               "vertaald ({1}). Code-Aster heeft alleen lineaire "
               "kinematische versteviging (VMIS_CINE_LINE); kies in Mecway "
               "BilinearKinematic, of Isotropic als de belasting niet "
               "omkeert.",
               "WARNING: Material '{0}': kinematic hardening curve not "
               "translated ({1}). Code-Aster only has linear kinematic "
               "hardening (VMIS_CINE_LINE); choose BilinearKinematic in "
               "Mecway, or Isotropic if the load does not reverse.").format(
                   mat_name, why))
        return None
    et = E * h / (E + h) if E + h != 0.0 else 0.0
    log("INFO: Material '{0}': kinematic curve is linear (SY={1} Pa, "
        "H={2} Pa) -> VMIS_CINE_LINE, D_SIGM_EPSI={3} Pa.".format(
            mat_name, sy, h, et))
    return {"sy": sy, "et": et, "kinematic": True}


def _ramberg_osgood_curve(plastic_node, E, mat_name, n_points=25):
    """
    Ramberg-Osgood -> hardening curve [(plastic strain, stress)] or [].
    CCX (*DEFORMATION PLASTICITY): eps = sig/E + alpha*(sig/E)*(sig/sig0)^(n-1).
    Code-Aster has no Ramberg-Osgood with von Mises plasticity; the
    curve goes as TRACTION to VMIS_ISOT_TRAC (incremental plasticity:
    equal under monotonic loading, different when unloading). Starts at the
    stress where the plastic strain is 1% of the elastic strain, up to 3*sig0.
    """
    sig0 = parse_and_convert(plastic_node.get("yieldstrength", "0"),
                             "pressure")
    n = plastic_node.get("rambergosgoodexponent", "")
    alpha = plastic_node.get("rambergossgoodalpha",
                             plastic_node.get("rambergosgoodalpha", ""))
    try:
        sig0, n, alpha = float(sig0), float(n), float(alpha)
    except (TypeError, ValueError):
        sig0 = n = alpha = 0.0
    if sig0 <= 0.0 or n <= 1.0 or alpha <= 0.0:
        log(tr("ERROR: Ramberg-Osgood van materiaal '{0}': ongeldige "
               "parameters (yieldstrength={1}, exponent={2}, alpha={3}); "
               "materiaal elastisch gerekend.",
               "ERROR: Ramberg-Osgood of material '{0}': invalid "
               "parameters (yieldstrength={1}, exponent={2}, alpha={3}); "
               "material computed as elastic.").format(
                mat_name, plastic_node.get("yieldstrength"),
                plastic_node.get("rambergosgoodexponent"),
                plastic_node.get("rambergossgoodalpha")))
        return []
    s1 = sig0 * (0.01 / alpha) ** (1.0 / (n - 1.0))
    s2 = 3.0 * sig0
    curve = [(0.0, s1)]
    for i in range(1, n_points):
        sig = s1 * (s2 / s1) ** (float(i) / (n_points - 1))
        eps_p = alpha * (sig / E) * (sig / sig0) ** (n - 1.0)
        curve.append((eps_p, sig))
    log(tr("WARNING: Materiaal '{0}': Ramberg-Osgood (sig0={1} Pa, n={2}, "
           "alpha={3}) als hardingscurve met {4} punten (VMIS_ISOT_TRAC, "
           "incrementele plasticiteit; bij ontlasten anders dan CCX' "
           "deformatieplasticiteit).",
           "WARNING: Material '{0}': Ramberg-Osgood (sig0={1} Pa, n={2}, "
           "alpha={3}) as hardening curve with {4} points (VMIS_ISOT_TRAC, "
           "incremental plasticity; differs from CCX' deformation "
           "plasticity on unloading).").format(mat_name, sig0, n, alpha,
                                               len(curve)))
    return curve


def _elem_choice(key):
    """MODELISATION choice from CONFIG_BRIDGE[key]; unknown -> default."""
    allowed = _ELEM_CHOICES[key]
    value = CONFIG_BRIDGE.get(key, allowed[0])
    if value not in allowed:
        log(tr("WARNING: CONFIG_BRIDGE['{0}'] = '{1}' is onbekend (kies uit "
               "{2}); '{3}' gebruikt.",
               "WARNING: CONFIG_BRIDGE['{0}'] = '{1}' is unknown (choose "
               "from {2}); '{3}' used.").format(
                   key, value, ", ".join(allowed), allowed[0]))
        return allowed[0]
    return value


def _gd_beam_choice(beam_mod, run_cfg, shapes, thermal_run):
    """
    elem_beam = POU_D_T_GD only where Code-Aster 17.4 and the bridge can
    compute it: STAT_NON_LINE with large displacements (DEFORMATION
    GROT_GDEP; ELAS_POUTRE_GR only exists with GROT_GDEP, U4.51.11 par.
    4.6 and test case ssnl103a). The element has no RIGI_MECA: MECA_STATIQUE
    with POU_D_T_GD stopped with CALCUL_37 "MECA_POU_D_T_GD ne sait pas
    encore calculer l'option: RIGI_MECA" (Code-Aster 17.4 run), so the
    linear solvers cannot use it. Elsewhere (linear static, modal,
    buckling, harmonic, dynamics, or nonlinear static with PETIT/
    PETIT_REAC) the beam becomes POU_D_T with a WARNING: the same
    Timoshenko beam at small displacements (verification NL-80 and NL-80b:
    the small-load cantilever gives Timoshenko with both). Implicit
    dynamics with POU_D_T_GD (Code-Aster test case sdnl103a) is NOT
    verified in the bridge, so it falls back as well.
    """
    if beam_mod != GD_BEAM or thermal_run or not shapes & _DIM_1D_SHAPES:
        return beam_mod
    solver = run_cfg.get("solver_command")
    deformation = "{0}".format(run_cfg.get("deformation", "PETIT")).upper()
    if solver == "STAT_NON_LINE" and deformation in (
            "GROT_GDEP", "GREEN_LAGRANGE", "GDEF_LOG", "SIMO_MIEHE"):
        return beam_mod
    what = (solver if solver != "STAT_NON_LINE"
            else "STAT_NON_LINE, deformation {0}".format(deformation))
    log(tr("WARNING: elem_beam = POU_D_T_GD (grote rotaties) werkt alleen in "
           "niet-lineair statisch met grote verplaatsingen (deformation "
           "GROT_GDEP); in deze analyse ({0}) worden balken POU_D_T "
           "(Timoshenko, dezelfde balk bij kleine verplaatsingen).",
           "WARNING: elem_beam = POU_D_T_GD (large rotations) only works "
           "in nonlinear static with large displacements (deformation "
           "GROT_GDEP); in this analysis ({0}) beams become POU_D_T "
           "(Timoshenko, the same beam at small displacements).").format(
               what))
    return "POU_D_T"


def _positive_int(text, default=1):
    """Integer >= 1 from an attribute, otherwise default."""
    try:
        return max(1, int(text))
    except (TypeError, ValueError):
        return default


def _run_analysis_cfg(mecway_type, mode_superposition=False):
    """
    CONFIG_BRIDGE dict of the analysis this run uses; with "auto" via
    the Mecway analysis type (as main() converts it). {} if unknown.
    """
    name = CONFIG_BRIDGE.get("active_analysis")
    if name == "auto":
        name = resolve_auto_analysis(mecway_type, mode_superposition)
    return CONFIG_BRIDGE["analyses"].get(name, {}) if name else {}


# ==========================================
# HELPER FUNCTION: GENERALE SECTION DICT
# ==========================================
def _parse_beam_orientation(elem):
    """
    Orientation of a beam element from the <elem> attributes, or None.

    Mecway (manual v33 par. 7.5 and the .liml of the test model):
    orientationvx/vy/vz = direction of the V axis (missing = 0), angle =
    extra rotation of V about U. Without a vector Mecway ignores angle (seen
    in a comparison Mecway <-> Code-Aster), so then None.
    """
    keys = ("orientationvx", "orientationvy", "orientationvz")
    if not any(elem.get(k) is not None for k in keys):
        if elem.get("angle") is not None:
            log("INFO: Beam element {0}: angle without orientation vector; "
                "Mecway ignores it, the bridge too.".format(elem.get("eid")))
        return None
    vec = tuple(float(elem.get(k, "0")) for k in keys)
    angle = parse_and_convert(elem.get("angle", "0"), 'angle')
    return {"vec": vec, "angle": angle}


def _parse_failure(fail_node, mat_name, model_data):
    """
    Mecway's failure criterion of a material (Failure criteria, manual v34
    par. 8.7): <failure type="VonMises" tensilestrength="250 MPa" />
    (attribute name seen in a .liml that Mecway 34 wrote itself with
    mw.set_material_property). Only von Mises is used: the factor
    of safety = tensilestrength / von Mises (result field safety_factor,
    aster_results_export._fos_vars). Other criteria (Tsai-Wu, ...):
    WARNING. Result in model_data["failure_strengths"] {mat: Pa}.
    """
    if fail_node is None:
        return
    kind = fail_node.get("type", "None")
    if kind in ("None", ""):
        return
    if kind == "VonMises":
        strength = parse_and_convert(fail_node.get("tensilestrength", "0"),
                                     'pressure')
        # parse_and_convert returns a float (unknown unit: the number
        # unchanged, with a WARNING); defensive, because a text in
        # failure_strengths would make the whole result export fail
        # (aster_results_export._fos_vars)
        if not isinstance(strength, (int, float)):
            log(tr("WARNING: Faalcriterium von Mises van materiaal '{0}': "
                   "tensile strength '{1}' niet te lezen; geen factor of "
                   "safety.",
                   "WARNING: Von Mises failure criterion of material '{0}': "
                   "tensile strength '{1}' cannot be read; no factor of "
                   "safety.").format(
                       mat_name, fail_node.get("tensilestrength", "")))
            return
        if strength > 0.0:
            model_data.setdefault("failure_strengths", {})[mat_name] = \
                strength
            log("INFO: Failure criterion von Mises for material '{0}': "
                "S = {1} Pa (factor of safety).".format(mat_name, strength))
            return
        log(tr("WARNING: Faalcriterium von Mises van materiaal '{0}' zonder "
               "tensile strength; geen factor of safety.",
               "WARNING: Von Mises failure criterion of material '{0}' "
               "without a tensile strength; no factor of safety.").format(
                   mat_name))
        return
    log(tr("WARNING: Faalcriterium '{1}' van materiaal '{0}' wordt niet "
           "vertaald (alleen von Mises); geen factor of safety.",
           "WARNING: Failure criterion '{1}' of material '{0}' is not "
           "translated (von Mises only); no factor of safety.").format(
               mat_name, kind))


def _make_generale_section(A, IY, IZ, JX):
    """
    Return a GENERALE section dict for Code-Aster POUTRE.

    Parameters (all in SI units)
    ----------
    A   : float  cross-section area (m^2)
    IY  : float  moment of inertia about local y axis (m^4)
    IZ  : float  moment of inertia about local z axis (m^4)
    JX  : float  torsion constant (m^4)
    """
    log("INFO: GENERALE section -> A={0} m2, IY={1} m4, "
        "IZ={2} m4, JX={3} m4".format(A, IY, IZ, JX))
    return {
        "aster_section": "GENERALE",
        "cara":          ("A", "IY", "IZ", "JX"),
        "vale":          (A, IY, IZ, JX),
    }


# ==========================================
# HELPER FUNCTIONS: PROFILE PROPERTIES AS IN MECWAY
# ==========================================
# Axes: V and W are Mecway's cross-section axes (Mecway manual v33,
# par. 7.5). In the drawing of the material window V runs vertically
# (along the height of I/T/C and leg b of L), W horizontally. Code-Aster
# local y = V, z = W (same default orientation, checked with a
# comparison Mecway <-> Code-Aster), so IY = I about V and IZ = I about W.
# This also matches RECTANGLE (HY = recta along V) and the general
# section (iyy -> IY).
#
# Checked against the values Mecway 33 shows (a/b/c/d in mm):
#   I 100/50/10/8  : A 1640, I_V 211746.67, I_W 2374666.67, J 47132.76
#   T 50/5/9/30    : A 600, I_V 94062.5, I_W 57065.625, J 12692.74
#   C 80/150/6/5   : A 1650, I_V 1077982.95, I_W 6074550, J 16803.72
#   L 80/100/5     : A 875, I_V 260746.17, I_W 1159863.95, J 7177.22,
#                    theta 32.4554619917313 degrees

def _roark_k1(a, b):
    """Torsion constant of a rectangle a x b, both ends free
    (Roark, Formulas for Stress and Strain, table 10.7)."""
    a, b = max(a, b), min(a, b)
    if a <= 0.0:
        return 0.0
    return a * b**3 * (1.0 / 3.0 - 0.21 * (b / a) *
                       (1.0 - b**4 / (12.0 * a**4)))


def _roark_k2(c, d):
    """Torsion constant of a strip c (length) x d (thickness) with one free
    end; the other is attached to the rest of the profile (Roark)."""
    if c <= 0.0:
        return 0.0
    return c * d**3 * (1.0 / 3.0 - 0.105 * (d / c) *
                       (1.0 - d**4 / (192.0 * c**4)))


def _rects_inertia(rects):
    """
    A, I about the horizontal centroidal axis (W), I about the vertical (V) and
    the product moment, for a cross-section made of rectangles
    (x0, x1, y0, y1); x horizontal, y vertical.
    """
    A = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in rects)
    cx = sum((x1 - x0) * (y1 - y0) * (x0 + x1) / 2.0
             for x0, x1, y0, y1 in rects) / A
    cy = sum((x1 - x0) * (y1 - y0) * (y0 + y1) / 2.0
             for x0, x1, y0, y1 in rects) / A
    i_w = i_v = i_vw = 0.0
    for x0, x1, y0, y1 in rects:
        w, h = x1 - x0, y1 - y0
        dx, dy = (x0 + x1) / 2.0 - cx, (y0 + y1) / 2.0 - cy
        i_w += w * h**3 / 12.0 + w * h * dy * dy
        i_v += h * w**3 / 12.0 + w * h * dx * dx
        i_vw += w * h * dx * dy
    return A, i_w, i_v, i_vw


def _profile_props(kind, a, b, c, d):
    """
    (A, IY, IZ, JX) of an I, T, C or L profile, in the unit of the
    dimensions (SI if the dimensions are in m). IY = I about V, IZ = I about W.
    """
    if kind == "I":
        # a height, b flange width, c flange thickness, d web thickness
        A, i_w, i_v, _ = _rects_inertia([
            (0.0, b, 0.0, c), (0.0, b, a - c, a),
            ((b - d) / 2.0, (b + d) / 2.0, c, a - c)])
        D = (c * c + d * d / 4.0) / c
        alpha = 0.15 * min(c, d) / max(c, d)
        J = 2.0 * _roark_k1(b, c) + (a - 2.0 * c) * d**3 / 3.0 + \
            2.0 * alpha * D**4
        return A, i_v, i_w, J
    if kind == "T":
        # a flange width, b web thickness, c flange thickness, d web height
        A, i_w, i_v, _ = _rects_inertia([
            (0.0, a, d, d + c), ((a - b) / 2.0, (a + b) / 2.0, 0.0, d)])
        D = (c * c + b * b / 4.0) / c
        alpha = 0.15 * min(b, c) / max(b, c)
        J = _roark_k1(a, c) + _roark_k2(d, b) + alpha * D**4
        return A, i_v, i_w, J
    if kind == "C":
        # a flange width (incl. web), b height, c flange thick., d web thick.
        A, i_w, i_v, _ = _rects_inertia([
            (0.0, a, 0.0, c), (0.0, a, b - c, b), (0.0, d, c, b - c)])
        D = 2.0 * ((c + d) - math.sqrt(2.0 * c * d))
        alpha = 0.07 * min(c, d) / max(c, d)
        J = 2.0 * _roark_k1(a, c) + _roark_k1(b - 2.0 * c, d) + \
            2.0 * alpha * D**4
        return A, i_v, i_w, J
    if kind == "L":
        # a horizontal leg, b vertical leg, c thickness. Mecway uses the
        # principal axes: V is at theta to leg b, rotated away from leg a
        # (theta as Mecway shows it).
        A, i_w, i_v, i_vw = _rects_inertia([
            (0.0, a, 0.0, c), (0.0, c, c, b)])
        theta = 0.5 * math.atan2(-2.0 * i_vw, i_w - i_v)
        s, co = math.sin(theta), math.cos(theta)
        i_pv = i_v * co * co + i_w * s * s + 2.0 * i_vw * s * co
        i_pw = i_v + i_w - i_pv
        D = 2.0 * ((c + c) - math.sqrt(2.0 * c * c))
        J = _roark_k1(a, c) + _roark_k2(b - c, c) + 0.07 * D**4
        return A, i_pv, i_pw, J
    raise ValueError(tr("Onbekend profiel '{0}'",
                        "Unknown profile '{0}'").format(kind))


def _profile_shear_coefs(kind, a, b, c, d):
    """
    (AY, AZ) for POU_D_T: shear coefficients A / A_shear in the
    direction V (local y) and W (local z), the convention of AFFE_CARA_ELEM
    (AY = 1.2 for a rectangle, test case sdll10a).

    Approximation with thin-walled plate parts, NOT verified against Mecway or
    Code-Aster: the shear area in a direction is the sum of the
    plate parts parallel to that direction; a web between two flanges
    (I, C) counts fully (nearly uniform shear stress), other
    plate parts (flanges, web of T, legs of L) with 5/6 (parabolic
    distribution, like a rectangle). Mecway itself uses Euler beams
    (no shear deformation).
    """
    k = 5.0 / 6.0
    if kind == "I":
        A = _profile_props(kind, a, b, c, d)[0]
        a_v = d * (a - c)
        a_w = k * 2.0 * b * c
    elif kind == "T":
        A = _profile_props(kind, a, b, c, d)[0]
        a_v = k * b * d
        a_w = k * a * c
    elif kind == "C":
        A = _profile_props(kind, a, b, c, d)[0]
        a_v = d * (b - c)
        a_w = k * 2.0 * a * c
    elif kind == "L":
        # Legs projected onto the principal axes (V at theta to leg b, see
        # _profile_props).
        A, i_w, i_v, i_vw = _rects_inertia([
            (0.0, a, 0.0, c), (0.0, c, c, b)])
        theta = 0.5 * math.atan2(-2.0 * i_vw, i_w - i_v)
        cs2, sn2 = math.cos(theta) ** 2, math.sin(theta) ** 2
        leg_a, leg_b = a * c, (b - c) * c
        a_v = k * (leg_b * cs2 + leg_a * sn2)
        a_w = k * (leg_b * sn2 + leg_a * cs2)
    else:
        raise ValueError(tr("Onbekend profiel '{0}'",
                            "Unknown profile '{0}'").format(kind))
    if a_v <= 0.0 or a_w <= 0.0:
        return None
    return A / a_v, A / a_w


def _add_shear_coefs(elset_name, geom, mod="POU_D_T"):
    """
    Section for POU_D_T and POU_D_T_GD (both Timoshenko, mod is only for the
    log): with SECTION='GENERALE' add AY and AZ.

    Without AY/AZ Code-Aster stopped with MODELISA_78 ("section GENERALE,
    element poutre : il manque la caracteristique ...") and DVP_2 (seen in
    Mecway and again in a run with Code-Aster 17.4). The catalogue
    (affe_cara_elem.py) requires AY/AZ > 0 if they are given. For RECTANGLE
    and CERCLE Code-Aster computes them itself: a short POU_D_T cantilever
    (L 50 mm, 20x10 mm) gave with RECTANGLE the same deflection as
    GENERALE with AY=AZ=1.2 and a different one than with AY=AZ=1.0 (run with
    Code-Aster 17.4). Returns a new dict; geom itself (shared per
    material) stays unchanged.
    """
    if geom.get("aster_section") != "GENERALE" or "AY" in geom["cara"]:
        return geom
    coefs = geom.get("shear_coefs")
    if coefs is None:
        coefs = (1.0, 1.0)
        log(tr("WARNING: Balk-elset '{0}' ({1}, {2}): "
               "afschuifcoefficienten onbekend; AY=AZ=1.0 "
               "(afschuifoppervlak = A, geen correctie).",
               "WARNING: Beam elset '{0}' ({1}, {2}): shear "
               "coefficients unknown; AY=AZ=1.0 (shear area = A, no "
               "correction).").format(elset_name,
                                      geom.get("geom_type", "?"), mod))
    else:
        # %-formatting: "{0:.4g}" follows the locale in IronPython (comma).
        source = ("from #ASTER-SECTIE (MecwaySectionProps)"
                  if geom.get("section_extras") else
                  "approximation, see _profile_shear_coefs")
        log("INFO: Beam elset '{0}' ({1}, {2}): AY={3}, AZ={4} "
            "({5}).".format(
                elset_name, geom.get("geom_type", "?"), mod,
                "%.4g" % coefs[0], "%.4g" % coefs[1], source))
    new = dict(geom)
    new["cara"] = tuple(geom["cara"]) + ("AY", "AZ")
    new["vale"] = tuple(geom["vale"]) + tuple(coefs)
    return new


# ==========================================
# EXTRA SECTION DATA: #ASTER-SECTIE (MecwaySectionProps)
# ==========================================
# MecwaySectionProps (own repository, github.com/trednuK/MecwaySectionProps;
# until 24 Oct 2026 in this one) creates a Mecway general
# section (area, iyy, izz, torsionconstant) and writes the characteristics
# Mecway has no field for in one line per material in the custom model
# definition:
#   ** ASTER-SECTIE <material>: A=.., IY=.., IZ=.., JX=.., AY=.., AZ=..,
#      EY=.., EZ=.., RY=.., RZ=.., RT=.., JG=.., IYR2=.., IZR2=..   (SI)
# Local y = principal axis 1 (Mecway V), z = principal axis 2 (Mecway W).
# A, IY, IZ, JX repeat the Mecway section: they show whether the line still
# belongs to the material (the user may have changed it in Mecway).
_SECTION_CHECK_KEYS = ("A", "IY", "IZ", "JX")
_SECTION_EXTRA_KEYS = ("AY", "AZ", "EY", "EZ", "RY", "RZ", "RT", "JG",
                       "IYR2", "IZR2")
# Passed to AFFE_CARA_ELEM for every beam: EY/EZ, the eccentricity of the
# shear (torsion) centre in the principal axes (R3.08.01 par. 5.1, "exact"
# beams POU_D_E/POU_D_T; U4.42.01 par. 9.4.3, default 0) as MACR_CARA_POUTRE
# gives it: the vector shear centre -> centroid (MecwaySectionProps
# section_fem.py, checked against MACR_CARA_POUTRE of Code-Aster 17.4 on a
# channel and an unequal angle, its tests/section_aster_check.py; accepted
# by POU_D_E, POU_D_T, POU_D_T_GD: runs of 23 Oct 2026),
# and RY/RZ/RT, used only for the stresses (U4.42.01 par. 9.3). AY/AZ go
# through shear_coefs to the Timoshenko beams only (_add_shear_coefs). JG,
# IYR2 and IZR2 are only used by POU_D_TG/POU_D_TGM (U4.42.01 par. 9.4.3),
# which the bridge does not offer: kept in "section_extras" only.
_SECTION_PASSED_KEYS = ("EY", "EZ", "RY", "RZ", "RT")
# Relative difference above which A/IY/IZ/JX of the line no longer match
# the material (Mecway stores 15 significant digits).
_SECTION_MATCH_TOL = 1e-6


def _section_extras(bodies):
    """
    {Mecway material: {KEY: value}} from the #ASTER-SECTIE lines
    ('<material>: A=1.5e-3, IY=..., AY=1.2, ...', SI values). A line with an
    error is skipped with an ERROR in the log.
    """
    out = {}
    known = _SECTION_CHECK_KEYS + _SECTION_EXTRA_KEYS
    for body in bodies:
        # rpartition: the values contain no ':', a material name might
        name, sep, rest = body.rpartition(":")
        values = {}
        error = None
        if not sep or not name.strip():
            error = tr("verwacht '<materiaal>: A=..., IY=..., ...'",
                       "expected '<material>: A=..., IY=..., ...'")
        else:
            for part in [p.strip() for p in rest.split(",") if p.strip()]:
                key, eq, raw = part.partition("=")
                key = key.strip().upper()
                try:
                    value = float(raw.strip())
                except ValueError:
                    value = None
                if not eq or key not in known or value is None:
                    error = tr("onbekend of ongeldig '{0}' (bekend: {1})",
                               "unknown or invalid '{0}' (known: {1})"
                               ).format(part, ", ".join(known))
                    break
                values[key] = value
            missing = [k for k in _SECTION_CHECK_KEYS if k not in values]
            if error is None and missing:
                error = tr("ontbreekt: {0}", "missing: {0}").format(
                    ", ".join(missing))
        if error is not None:
            log(tr("ERROR: #ASTER-SECTIE '{0}' wordt overgeslagen: {1}.",
                   "ERROR: #ASTER-SECTIE '{0}' is skipped: {1}.").format(
                       body, error))
            continue
        out[name.strip()] = values
    return out


def _apply_section_extras(mat_name, geom, extra):
    """
    The section dict of a general section with the #ASTER-SECTIE data:
    EY, EZ, RY, RZ, RT added to cara/vale, AY/AZ as shear_coefs (Timoshenko
    beams only), everything in "section_extras". Returns geom unchanged
    (WARNING) when the line does not belong to this section any more.
    """
    if geom.get("geom_type") != "UniformGeneralSection":
        log(tr("WARNING: #ASTER-SECTIE '{0}': het materiaal heeft geen "
               "General section ({1}); de regel wordt genegeerd.",
               "WARNING: #ASTER-SECTIE '{0}': the material has no general "
               "section ({1}); the line is ignored.").format(
                   mat_name, geom.get("geom_type", "?")))
        return geom
    cara = dict(zip(geom["cara"], geom["vale"]))
    for key in _SECTION_CHECK_KEYS:
        ref = cara.get(key, 0.0)
        if abs(extra[key] - ref) > _SECTION_MATCH_TOL * max(abs(ref),
                                                             1e-30):
            log(tr("WARNING: #ASTER-SECTIE '{0}': {1} = {2} in de regel, "
                   "maar {3} in het materiaal; de doorsnede is na "
                   "MecwaySectionProps gewijzigd. De extra eigenschappen "
                   "(AY, AZ, EY, EZ, RY, RZ, RT) worden genegeerd; maak de "
                   "General section opnieuw met MecwaySectionProps.",
                   "WARNING: #ASTER-SECTIE '{0}': {1} = {2} in the line, "
                   "but {3} in the material; the section was changed after "
                   "MecwaySectionProps. The extra properties (AY, AZ, EY, "
                   "EZ, RY, RZ, RT) are ignored; create the general section "
                   "again with MecwaySectionProps.").format(
                       mat_name, key, "%.6g" % extra[key], "%.6g" % ref))
            return geom
    new = dict(geom)
    keys = [k for k in _SECTION_PASSED_KEYS if k in extra]
    new["cara"] = tuple(geom["cara"]) + tuple(keys)
    new["vale"] = tuple(geom["vale"]) + tuple(extra[k] for k in keys)
    if extra.get("AY", 0.0) > 0.0 and extra.get("AZ", 0.0) > 0.0:
        new["shear_coefs"] = (extra["AY"], extra["AZ"])
    new["section_extras"] = dict(extra)
    log("INFO: Material '{0}': #ASTER-SECTIE adds {1} to the general "
        "section{2}.".format(
            mat_name, ", ".join("{0}={1}".format(k, "%.6g" % extra[k])
                                for k in keys),
            "" if "shear_coefs" not in new else
            " (AY={0}, AZ={1} for Timoshenko beams)".format(
                "%.4g" % extra["AY"], "%.4g" % extra["AZ"])))
    return new


# ==========================================
# GEOMETRY PARSER
# ==========================================
def _parse_geometric_props(geom_node):
    """
    Parse a Mecway <geometric> element into Code-Aster section properties.

    pointy/pointz are Mecway's stress recovery point ("Stress
    recovery point in principal coordinates") and are not used. The
    beam orientation is stored per element (_parse_beam_orientation).

    Returns
    -------
    dict or None
        Beam:  'geom_type', 'aster_section', 'cara', 'vale'
        Shell: 'geom_type', 'thickness'
        None for an unknown type.
    """
    geom_type = geom_node.get("type", "")
    result    = {"geom_type": geom_type}

    # ------------------------------------------------------------------
    # CIRCULAR CROSS-SECTIONS
    # ------------------------------------------------------------------
    if geom_type == "CircularBar":
        od = parse_and_convert(geom_node.get("roundod", "0"), 'length')
        result["aster_section"] = "CERCLE"
        result["cara"]          = ("R",)
        result["vale"]          = (od / 2.0,)
        result["profile"]       = {"shape": "CircularBar", "od": od}
        log("INFO: CircularBar           -> CERCLE R={0} m".format(od / 2.0))

    elif geom_type == "UniformCircularTube":
        od  = parse_and_convert(geom_node.get("roundod", "0"), 'length')
        rid = parse_and_convert(geom_node.get("roundid", "0"), 'length')
        ep  = (od - rid) / 2.0
        result["aster_section"] = "CERCLE"
        result["cara"]          = ("R", "EP")
        result["vale"]          = (od / 2.0, ep)
        result["profile"]       = {"shape": "UniformCircularTube", "od": od,
                                   "id": rid}
        log("INFO: UniformCircularTube   -> CERCLE R={0} m, EP={1} m".format(
            od / 2.0, ep))

    # ------------------------------------------------------------------
    # RECTANGULAR CROSS-SECTIONS
    # ------------------------------------------------------------------
    elif geom_type == "RectBar":
        a = parse_and_convert(geom_node.get("recta", "0"), 'length')
        b = parse_and_convert(geom_node.get("rectb", "0"), 'length')
        result["aster_section"] = "RECTANGLE"
        result["cara"]          = ("HY", "HZ")
        result["vale"]          = (a, b)
        result["profile"]       = {"shape": "RectBar", "a": a, "b": b}
        log("INFO: RectBar               -> RECTANGLE HY={0} m, HZ={1} m".format(
            a, b))

    elif geom_type == "RectTube":
        a = parse_and_convert(geom_node.get("recta",         "0"), 'length')
        b = parse_and_convert(geom_node.get("rectb",         "0"), 'length')
        t = parse_and_convert(geom_node.get("rectthickness", "0"), 'length')
        result["aster_section"] = "RECTANGLE"
        result["cara"]          = ("HY", "HZ", "EPY", "EPZ")
        result["vale"]          = (a, b, t, t)
        result["profile"]       = {"shape": "RectTube", "a": a, "b": b,
                                   "t": t}
        log("INFO: RectTube              -> RECTANGLE HY={0}, HZ={1}, "
            "EPY=EPZ={2} m".format(a, b, t))

    # ------------------------------------------------------------------
    # GENERAL CROSS-SECTION
    # ------------------------------------------------------------------
    elif geom_type == "UniformGeneralSection":
        A  = parse_and_convert(geom_node.get("area",            "0"), 'area')
        IY = parse_and_convert(geom_node.get("iyy",             "0"), 'inertia')
        IZ = parse_and_convert(geom_node.get("izz",             "0"), 'inertia')
        JX = parse_and_convert(geom_node.get("torsionconstant", "0"), 'inertia')
        log("INFO: UniformGeneralSection -> GENERALE (given values)")
        result.update(_make_generale_section(A, IY, IZ, JX))

    # ------------------------------------------------------------------
    # I PROFILE / T PROFILE / L PROFILE / C PROFILE
    # ------------------------------------------------------------------
    # Dimensions as in the drawing of the Mecway material window. The
    # values (A, I about V, I about W, torsion constant) are checked against
    # what Mecway 33 itself shows in that window; see _profile_props().
    elif geom_type in ("I", "T", "L", "C"):
        p = geom_type.lower()
        dims = [parse_and_convert(geom_node.get(p + k, "0"), 'length')
                for k in ("a", "b", "c", "d")]
        A, IY, IZ, JX = _profile_props(geom_type, *dims)
        log("INFO: {0}-profile             -> GENERALE (as Mecway)".format(
            geom_type))
        result.update(_make_generale_section(A, IY, IZ, JX))
        # Only used with POU_D_T (STEP 3, _add_shear_coefs).
        result["shear_coefs"] = _profile_shear_coefs(geom_type, *dims)
        # Mecway's dimensions (meaning per shape: _profile_props), for
        # the beam sidecar (bridge_beams)
        result["profile"] = {"shape": geom_type, "a": dims[0], "b": dims[1],
                             "c": dims[2], "d": dims[3]}

    # ------------------------------------------------------------------
    # SHELL ELEMENT
    # ------------------------------------------------------------------
    elif geom_type == "Plate":
        thickness = parse_and_convert(geom_node.get("thickness", "0"), 'length')
        result["thickness"] = thickness
        # Plane strain in a Static 2D analysis (S20): planestrain="1"
        # (Mecway 34, seen after importing a CPE4 element; bridge_plane)
        result["planestrain"] = geom_node.get("planestrain", "") in (
            "1", "true")
        log("INFO: Plate                 -> COQUE EPAIS={0} m".format(thickness))

    else:
        log(tr("WARNING: Onbekend geometrie-type '{0}'. Voeg dit type toe "
               "aan _parse_geometric_props() in bridge_from_liml.py.",
               "WARNING: Unknown geometry type '{0}'. Add this type to "
               "_parse_geometric_props() in bridge_from_liml.py.").format(
                   geom_type))
        return None

    return result


def _split_trusses(model_data, elset_shapes_map, truss_eids, line_eids):
    """
    Truss elements (Mecway manual v33 par. 7.6: per element via Element
    properties -> Truss; in the .liml <elem ... truss="true">, seen in
    Samples/VibratingTrussTower.liml and SaggingCable.liml) become bars in
    Code-Aster: MODELISATION='BARRE' (axial force only,
    pinned; catalogue phenomenons_modelisations.py, test cases
    ssll11c, sdnl138a). A MODELISATION applies per group, so:
      - all 1D elements of an elset are truss -> the elset becomes BARRE;
      - mixed (beams and trusses in one component) -> the trusses go
        to their own elset '<name>_TRUSS' (in mesh_elements; same
        material, STEP 2b); the beams keep the name of the component.
    Returns (truss_elsets, truss_parts): set of BARRE elsets and
    {component: [truss elset]}.
    """
    truss_elsets = set()
    truss_parts = {}
    used = set(elset_shapes_map)
    moved = {}
    for ename, teids in truss_eids.items():
        if teids == line_eids.get(ename, set()):
            truss_elsets.add(ename)
            log("INFO: Elset '{0}': {1} truss elements -> BARRE.".format(
                ename, len(teids)))
            continue
        new = "{0}_TRUSS".format(ename)
        n = 2
        while new in used:
            new = "{0}_TRUSS{1}".format(ename, n)
            n += 1
        used.add(new)
        truss_elsets.add(new)
        truss_parts[ename] = [new]
        for eid in teids:
            moved[eid] = new
        elset_shapes_map[new] = set(
            model_data["elem_shapes"][eid] for eid in teids)
        log(tr("WARNING: Component '{0}' mengt balken en trusses; de {1} "
               "truss-elementen worden in Code-Aster de groep '{2}' (BARRE). "
               "<<{0}>> in #ASTER-regels is alleen het balkdeel.",
               "WARNING: Component '{0}' mixes beams and trusses; the {1} "
               "truss elements become group '{2}' in Code-Aster (BARRE). "
               "<<{0}>> in #ASTER lines is only the beam part.").format(
                   ename, len(teids), new))
    if moved:
        model_data["mesh_elements"] = [
            (eid, shape, nodes, moved.get(eid, elset))
            for eid, shape, nodes, elset in model_data["mesh_elements"]]
    return truss_elsets, truss_parts


def _section_area(geom):
    """Cross-section area (m2) of a beam section dict, or 0.0."""
    cara = dict(zip(geom.get("cara", ()), geom.get("vale", ())))
    section = geom.get("aster_section")
    if section == "CERCLE":
        r = cara.get("R", 0.0)
        ri = r - cara["EP"] if "EP" in cara else 0.0
        return math.pi * (r * r - ri * ri)
    if section == "RECTANGLE":
        hy, hz = cara.get("HY", 0.0), cara.get("HZ", 0.0)
        if "EPY" in cara:
            return hy * hz - (hy - 2.0 * cara["EPY"]) * (hz - 2.0 * cara["EPZ"])
        return hy * hz
    if section == "GENERALE":
        return cara.get("A", 0.0)
    return 0.0


# ==========================================
# MECHANICAL MODEL ITEMS WITHOUT A BC CLASS
# ==========================================
# Tags that are not a load on a selection but complement the model
# (thermal strain, damping, MPCs, nodal masses); _parse_model_item puts them
# in model_data, bridge_mesh.py / bridge_to_aster.py translate them.
_MODEL_ITEM_TAGS = ("thermalstress", "temperature2", "rayleighdamping",
                    "constraintequation", "mass2", "rotationalinertia",
                    "flexiblejoint", bridge_offset.TAG)
# Of these, not translated in the thermal -> mechanical chain, with a
# WARNING (the others do not matter in the quasi-static solve).
_CHAIN_DROPPED_TAGS = ("constraintequation", "flexiblejoint",
                       bridge_offset.TAG)

# DOF names of a constraint equation. ux/uy/uz are in the .liml of
# the test model (Mecway 33). rx/ry/rz: in mecway.exe "rx", "ry",
# "rz" are separate strings directly before the DOF type names (DISPLX, DISPLY,
# ...), after "ux" "uy" "uz"; plausible, but NOT seen in a .liml.
_CE_DOFS = {"ux": ("DX", "inverse_length"), "uy": ("DY", "inverse_length"),
            "uz": ("DZ", "inverse_length"), "rx": ("DRX", "inverse_angle"),
            "ry": ("DRY", "inverse_angle"), "rz": ("DRZ", "inverse_angle")}


def _not_translated(model_data, what, why):
    """Report an untranslated item (ERROR + skipped_loads)."""
    model_data["skipped_loads"].append(what)
    log(tr("ERROR: {0}: {1} NIET meegenomen.",
           "ERROR: {0}: {1} NOT included.").format(what, why))


def _drop_elset(model_data, elset_name, what, why):
    """Report an elset that cannot be translated (_not_translated). The
    whole elset is missing then, so extract_aster_data_from_liml stops
    before Code-Aster (otherwise only MODELE1_6 or an empty model)."""
    _not_translated(model_data, what, why)
    dropped = model_data.setdefault("_dropped_elsets", [])
    if elset_name not in dropped:
        dropped.append(elset_name)


_LIML_CHUNK = 4 * 1024 * 1024


def _model_bytes(file_path):
    """
    The bytes of the .liml up to the first '<solution' (as an element: followed
    by '>', '/' or whitespace) plus '</liml>', or None if there is no
    <solution>. Reads in blocks, like bridge_results_liml.
    _find_solution_start (which only works with str, so not in CPython 3).
    '<' in text is always '&lt;' in XML, so the first '<solution' is the
    element. The bytes stay unchanged (also a BOM and the
    XML declaration), the parser decodes as with ET.parse().
    """
    f = open(file_path, "rb")
    try:
        chunks = []
        size = 0                  # bytes in chunks
        keep = None
        while True:
            block = f.read(_LIML_CHUNK)
            if not block:
                return None
            if keep is None:
                # str in IronPython/Python 2, bytes in Python 3
                if isinstance(block, str):
                    pat, follow, close = "<solution", ">/ \t\r\n", "</liml>"
                else:
                    pat, follow, close = (b"<solution", b">/ \t\r\n",
                                          b"</liml>")
                keep = block[:0]
            buf = keep + block
            start = 0
            while True:
                i = buf.find(pat, start)
                if i < 0 or i + len(pat) >= len(buf):
                    break
                if buf[i + len(pat):i + len(pat) + 1] in follow:
                    pos = size - len(keep) + i
                    data = block[:0].join(chunks + [block])
                    return data[:pos] + close
                start = i + 1
            chunks.append(block)
            size += len(block)
            keep = buf[-len(pat):]
    finally:
        f.close()


def _parse_model_root(file_path):
    """
    Root element of the .liml with only the model: everything from <solution>
    (top level, the last child of <liml>) is not read. After a run
    the results are in the .liml (bridge_results_liml.py); ET.parse()
    of the whole file took 85 s for 99 MB in IronPython (also
    ET.iterparse gave the first event only after 81 s: the parser of
    IronPython 2.7.9 apparently processes the input only as a whole). The
    model itself (and so everything read here) comes before <solution>.
    """
    data = _model_bytes(file_path)
    if data is None:
        return ET.parse(file_path).getroot()
    return ET.fromstring(data)


def _suppressed_in(elem, configuration):
    """True if elem is suppressed: suppressed="true" (in all
    configurations) or a child <suppressed configuration="name"/> for
    the configuration being solved."""
    if elem.get("suppressed", "") == "true":
        return True
    if configuration is None:
        return False
    for sup in elem.findall("suppressed"):
        if sup.get("configuration") == configuration:
            return True
    return False


def _pick_configuration(root):
    """
    (configuration, how, missing) from bridge_utils.choose_configuration,
    the same choice as bridge_results_liml.pick_configuration (which puts the
    results in the solution of that configuration). Here on the
    parsed XML: pick_configuration reads bytes with str operations and
    does not work in CPython 3 (smoke test).
    """
    names = [c.get("name") for c in root.findall("configuration")]
    suppressed = set()
    for elem in root.iter():
        for sup in elem.findall("suppressed"):
            suppressed.add(sup.get("configuration"))
    return choose_configuration(names, suppressed)


def _apply_suppression(root, model_data):
    """
    Set suppressed="true" on items that are suppressed in the configuration
    being solved or via a suppressed group; the rest of the bridge (also
    bridge_thermal) only looks at that attribute.

    Mecway (manual v33 par. 2.8): per configuration its own set of loads and
    boundary conditions and its own solution. In the .liml: <configuration
    name=".."/> at the top and per item a child <suppressed
    configuration=".."/> (Tutorials/AssemblyWithContact.liml,
    Samples/CylinderLifting.liml). The active configuration is not in the
    .liml and the API cannot read it; the bridge solves the configuration
    from the setting "configuration" (start screen) or according to the rule of
    bridge_utils.choose_configuration, and puts the results in its
    solution (_pick_configuration).
    Groups (manual par. 9, "Groups can be suppressed"): <group name="G"
    suppressed="true"/> and items with group="G"
    (Samples/VibratingTrussTower.liml).
    """
    configuration, how, missing = _pick_configuration(root)
    model_data["configuration"] = configuration
    names = [c.get("name") for c in root.findall("configuration")]
    if configuration is not None:
        log("INFO: Configuration '{0}' solved ({1}).".format(
            configuration, {"gekozen": "setting Configuration",
                            "enige": "the only configuration",
                            "vrij": "the only one without suppressed items",
                            "eerste": "the first"}[how]))
        warning = configuration_warning(names, configuration, how, missing)
        if warning:
            log(u"WARNING: " + warning)
    groups = set(g.get("name") for g in root.findall("group")
                 if _suppressed_in(g, configuration))
    items = list(root)
    for ic in root.findall("initialconditions"):
        items.extend(list(ic))
    for item in items:
        if item.tag in ("configuration", "group") or \
                item.get("suppressed", "") == "true":
            continue
        why = None
        if _suppressed_in(item, configuration):
            why = "configuration '{0}'".format(configuration)
        elif item.get("group") in groups:
            why = "group '{0}'".format(item.get("group"))
        if why is None:
            continue
        item.set("suppressed", "true")
        log("INFO: {0} on '{1}' suppressed ({2}); not translated.".format(
            item.tag, item.get("selection", item.get(
                "selectionslave", item.get("selectionsurface", ""))), why))


def _has_selection(root, tag, name):
    """True if root has a <tag name="name">. Without XPath predicate:
    an apostrophe in the name gave a SyntaxError with "[@name='...']"
    ('invalid predicate') and the model was left half read."""
    for e in root.findall(tag):
        if e.get("name") == name:
            return True
    return False


def _parse_node_temperatures(item, model_data):
    """
    Mecway Node temperature (<temperature3><nodetemperature nid=".."
    value="393 K" /></temperature3>, manual v34 par. 9.24; also the result
    of "Transfer temperatures from solution", manual par. 6.8 and 17.10) in
    a mechanical analysis: the temperature per node for thermal strain,
    just like temperature2 (only with <thermalstress>).
    Behaviour of Mecway 34 (seen headless, bar of 4 hex8, free
    expansion and clamped):
      - nodes without temperature are at the reference temperature
        (manual par. 9.25); temperature2 and temperature3 on different
        nodes add up;
      - S30, V30 (prestress) and B30: the same result as
        temperature2 with the same value on the same nodes; L30 with CCX
        too (without ramp, just like temperature2);
      - D30 (Dynamic Response): temperature2 and temperature3 do not
        count (same result with and without);
      - two different temperatures on one node (temperature3 twice,
        or temperature3 and temperature2): Mecway does not solve
        ("Conflicting temperatures on node"); the same value is allowed.
    D31 is not among the analysis types of Node temperature (manual par.
    9.24); the internal solver does not solve L30/D31 headless, so not
    seen: reported and not translated.
    Result: model_data["node_temperatures"] {nid: K};
    bridge_to_aster._build_temperature_field puts them in the nodal field.
    """
    atype = model_data.get("analysis_type")
    if atype == "D30":
        log("INFO: Node temperature (temperature3) is ignored in Dynamic "
            "Response (D30), as in Mecway.")
        return
    if atype == "D31":
        _not_translated(model_data,
                        tr("Node temperature (temperature3)",
                           "Node temperature (temperature3)"),
                        tr("Mecway gebruikt Node temperature niet in "
                           "Nonlinear Dynamic Response (manual par. 9.24); "
                           "gebruik Temperature (temperature2);",
                           "Mecway does not use Node temperature in "
                           "Nonlinear Dynamic Response (manual par. 9.24); "
                           "use Temperature (temperature2);"))
        return
    temps = model_data["node_temperatures"]
    nodes = model_data.get("mesh_nodes", {})
    conflicts, bad = [], []
    n = 0
    for nt in item.findall("nodetemperature"):
        try:
            nid = int(nt.get("nid"))
            value = bridge_thermal._value(nt.get("value"), "temperature")
        except (TypeError, ValueError):
            bad.append(nt.get("nid"))
            continue
        if nodes and nid not in nodes:
            bad.append(nt.get("nid"))
            continue
        if nid in temps and abs(temps[nid] - value) > 1e-9 * max(
                1.0, abs(value)):
            conflicts.append(nid)
        temps[nid] = value
        n += 1
    if bad:
        _not_translated(model_data,
                        tr("Node temperature op {0} knoop/knopen",
                           "Node temperature on {0} node(s)").format(
                               len(bad)),
                        tr("onbekende knoop of geen getal met eenheid "
                           "(knopen {0});",
                           "unknown node or not a number with a unit "
                           "(nodes {0});").format(
                               ", ".join(str(b) for b in bad[:10])))
    if conflicts:
        log(tr("WARNING: Node temperature: knoop/knopen {0} hebben twee "
               "verschillende temperaturen; Mecway rekent dan niet "
               "(\"Conflicting temperatures on node\"). De bridge gebruikt "
               "de laatste waarde.",
               "WARNING: Node temperature: node(s) {0} have two different "
               "temperatures; Mecway does not solve then (\"Conflicting "
               "temperatures on node\"). The bridge uses the last value.")
            .format(", ".join(str(c) for c in conflicts[:10])))
    log("INFO: Node temperature on {0} nodes.".format(n))


def _selection_kind(root, sel):
    """'GROUP_NO' for a nodeselection, otherwise 'GROUP_MA'."""
    if _has_selection(root, "nodeselection", sel):
        return "GROUP_NO"
    return "GROUP_MA"


def _parse_model_item(item, root, model_data):
    """Complete model_data for a tag from _MODEL_ITEM_TAGS."""
    tag = item.tag
    sel = item.get("selection", "")
    if tag == bridge_offset.TAG:
        # Element offset of shells and beams (manual v34 par. 7.4.3,
        # 7.5.1); bridge_mesh/bridge_to_aster translate it (bridge_offset).
        bridge_offset.parse(item, model_data)
    elif tag == "thermalstress":
        # Mecway (manual v33 par. 9.25): a reference temperature; nodes
        # without temperature are at that temperature.
        if model_data.get("thermal_stress") is not None:
            _not_translated(model_data,
                            tr("tweede thermal stress",
                               "second thermal stress"),
                            tr("Mecway staat er een per model toe;",
                               "Mecway allows one per model;"))
            return
        model_data["thermal_stress"] = {"tref": parse_and_convert(
            item.findtext("referencetemperature"), "temperature")}
        log("INFO: Thermal stress, reference temperature {0} K.".format(
            model_data["thermal_stress"]["tref"]))
    elif tag == "temperature2":
        # Mecway (manual v33 par. 9.23): in a mechanical analysis the
        # temperature for thermal strain (with <thermalstress>).
        # <starttime>/<endtime> apply only to thermal analyses.
        # A time table or formula in t becomes a list (t, K) (formula:
        # sampled over the end time of <timesteps>, hence root);
        # bridge_to_aster._build_temperature_field uses it in
        # STAT_NON_LINE and DYNA_NON_LINE (EVOL_THER) and omits it elsewhere,
        # like Mecway's own solver (KNOWN_BUGS 17).
        if model_data.get("analysis_type") == "D30":
            # Mecway 34 ignores Temperature in Dynamic Response (seen
            # headless: same result with and without, also with a time table).
            log("INFO: Temperature (temperature2) on '{0}' is ignored in "
                "Dynamic Response (D30), as in Mecway.".format(sel))
            return
        value = _parse_value(item, "value", "temperature", None, root)
        if value is None:
            _not_translated(model_data,
                            tr("temperatuur op '{0}'",
                               "temperature on '{0}'").format(sel),
                            tr("geen bruikbare waarde;",
                               "no usable value;"))
            return
        model_data["temperatures"].append({
            "selection": sel, "target": _selection_kind(root, sel),
            "value": value})
        if isinstance(value, list):
            log("INFO: Temperature on '{0}' with time history ({1} points, "
                "{2} .. {3} s).".format(sel, len(value), value[0][0],
                                        value[-1][0]))
        else:
            log("INFO: Temperature {0} K on '{1}'.".format(value, sel))
    elif tag == "rayleighdamping":
        # Mecway (manual v33 par. 9.26): C = alpha M + beta K, on the whole
        # model or a selection. Code-Aster: DEFI_MATERIAU ELAS AMOR_ALPHA
        # (x K) and AMOR_BETA (x M), U4.43.01 par. 4 -> per material.
        # XML (Samples/DampedVibratingStrip.liml): <rayleighdamping
        # selection=""><alpha>1 rad/s</alpha><beta>0.005 s</beta>; an
        # empty selection is the whole model.
        if sel:
            _not_translated(model_data,
                            tr("Rayleigh-demping op selectie '{0}'",
                               "Rayleigh damping on selection '{0}'"
                               ).format(sel),
                            tr("alleen op het hele model (zoals bij CCX);",
                               "only on the whole model (as with CCX);"))
            return
        if model_data.get("rayleigh") is not None:
            _not_translated(model_data,
                            tr("tweede Rayleigh-demping",
                               "second Rayleigh damping"),
                            tr("Mecway/CCX staan er een toe;",
                               "Mecway/CCX allow one;"))
            return
        model_data["rayleigh"] = {
            "alpha": parse_and_convert(item.findtext("alpha"),
                                       "inverse_time"),
            "beta": parse_and_convert(item.findtext("beta"), "time")}
        log("INFO: Rayleigh damping {0}.".format(model_data["rayleigh"]))
    elif tag == "constraintequation":
        # Mecway (manual v33 par. 9.42): A dof1 + B dof2 + ... = C.
        # <term coefficient="1 1/m" nid="49" dof="ux" />. In mecway.exe
        # "term" and "constant" appear together with the constraint equation
        # texts ("The constant is ... but it must be zero with this
        # analysis type and solver"); whether constant is a child element or an
        # attribute is NOT seen in a .liml: both are read. The
        # constant must be 0 with CCX and dynamics (manual par. 9.42).
        # Tutorials/ConstraintEquations.liml itself contains no equation
        # (you create it in the tutorial, manual par. 17.14).
        terms = []
        for term in item.findall("term"):
            dof = _CE_DOFS.get(term.get("dof", ""))
            if dof is None:
                _not_translated(model_data, "constraint equation",
                                tr("onbekende DOF '{0}';",
                                   "unknown DOF '{0}';").format(
                                       term.get("dof")))
                return
            terms.append((int(term.get("nid")), dof[0], parse_and_convert(
                term.get("coefficient"), dof[1])))
        if not terms:
            return
        constant = parse_and_convert(
            item.findtext("constant") or item.get("constant") or "0",
            "dimensionless")
        model_data["constraint_equations"].append(
            {"terms": terms, "constant": constant})
        log("INFO: Constraint equation {0} = {1}.".format(terms, constant))
    elif tag == "flexiblejoint":
        # Mecway (manual v33 par. 9.12, "Flexible joint on beam"): lets the
        # end of a beam element rotate freely about a combination of
        # its local axes U (axis), V and W, also if it is attached to another
        # element or the rotation is imposed; only on end faces
        # of beam elements. No stiffness: only free or fixed. XML
        # (saved by Mecway 34, text "Free rotation about U/V/W" in
        # mecway.exe): <flexiblejoint selection="FJ"><rotu /><rotw />
        # </flexiblejoint>; a child present = free (content ignored,
        # Mecway saves <rotu>false</rotu> as <rotu />). Translation:
        # bridge_mesh._flexible_joints (duplicate node + LIAISON_DDL).
        free = tuple(a for a in ("u", "v", "w")
                     if item.find("rot" + a) is not None)
        if (_selection_kind(root, sel) != "GROUP_MA" or
                not _has_selection(root, "faceselection", sel)):
            _not_translated(model_data,
                            tr("flexible joint op '{0}'",
                               "flexible joint on '{0}'").format(sel),
                            tr("alleen op eindvlakken van balkelementen "
                               "(vlakselectie);",
                               "only on end faces of beam elements (face "
                               "selection);"))
            return
        if not free:
            log("INFO: Flexible joint on '{0}' without free rotation; no "
                "effect.".format(sel))
            return
        model_data["flexible_joints"].append({"selection": sel,
                                              "free": free})
        log("INFO: Flexible joint on '{0}': free rotation about {1}.".format(
            sel, "/".join(a.upper() for a in free)))
    elif tag in ("mass2", "rotationalinertia"):
        # Mecway (manual v33 par. 9.21/9.22): nodal mass (spread equally over
        # the nodes) or rotational inertia about the X/Y/Z axis (axis="3" = Z
        # seen in Mecway 33; 1 = X, 2 = Y derived; "axis" appears in
        # mecway.exe with the rotational inertia texts). In Mecway a
        # rotational inertia is allowed on one node only ("A rotational
        # inertia can only be applied to a single node", mecway.exe).
        # Code-Aster: POI1 with DIS_T M_T_D_N or DIS_TR M_TR_D_N
        # (bridge_mesh._build_discretes).
        if tag == "mass2":
            entry = {"selection": sel, "kind": "mass",
                     "value": parse_and_convert(item.findtext("value"),
                                                "mass")}
        else:
            entry = {"selection": sel, "kind": "inertia",
                     "axis": int(item.get("axis", "0") or 0),
                     "value": parse_and_convert(item.findtext("value"),
                                                "rotational_inertia")}
            if entry["axis"] not in (1, 2, 3):
                _not_translated(model_data,
                                tr("rotatietraagheid op '{0}'",
                                   "rotational inertia on '{0}'"
                                   ).format(sel),
                                tr("onbekende as '{0}';",
                                   "unknown axis '{0}';").format(
                                    item.get("axis")))
                return
        if _selection_kind(root, sel) != "GROUP_NO":
            _not_translated(model_data,
                            tr("{0} op '{1}'", "{0} on '{1}'").format(
                                tag, sel),
                            tr("alleen op knopen (nodeselection);",
                               "only on nodes (nodeselection);"))
            return
        n_nodes = len(model_data["node_groups"].get(sel, []))
        if tag == "rotationalinertia" and n_nodes > 1:
            _not_translated(model_data,
                            tr("rotatietraagheid op '{0}'",
                               "rotational inertia on '{0}'").format(sel),
                            tr("Mecway staat een rotatietraagheid maar op "
                               "een knoop toe (hier {0});",
                               "Mecway allows a rotational inertia on a "
                               "single node only (here {0});").format(
                                   n_nodes))
            return
        model_data["point_masses"].append(entry)
        log("INFO: {0} on '{1}': {2}.".format(tag, sel, entry))


def _check_gravity_history(params, model_data):
    """
    Gravity with time history (bridge_bcs.GravityBC): False (reported) if the
    direction changes in time; a PESANTEUR with FONC_MULT has a
    fixed DIRECTION. True without history or with a fixed direction.
    """
    if not params.get("_history"):
        return True
    d = SUPPORTED_BCS["gravity"].to_aster_dict(params)
    if not d:
        _not_translated(model_data,
                        tr("gravity met tijdshistorie",
                           "gravity with a time history"),
                        tr("de richting verandert in de tijd (Code-Aster "
                           "PESANTEUR met FONC_MULT heeft een vaste "
                           "richting);",
                           "the direction changes in time (Code-Aster "
                           "PESANTEUR with FONC_MULT has a fixed "
                           "direction);"))
        return False
    log("INFO: Gravity with time history: GRAVITE(t) {0} along "
        "DIRECTION {1} (PESANTEUR with FONC_MULT).".format(
            d["GRAVITE"], d["DIRECTION"]))
    return True


# Analyses in which a formula in x, y, z (bridge_bcs.PositionFormula) works as
# FORMULE in AFFE_CHAR_MECA_F (bridge_to_aster._build_charges):
# static, nonlinear static, implicit dynamics and modal/buckling
# (prestress). Not: explicit dynamics (an imposed displacement
# becomes an acceleration there, bridge_to_aster._explicit_kinematics),
# harmonic, modal response and spectrum (amplitudes, NOT checked).
_POSITION_SOLVERS = ("MECA_STATIQUE", "STAT_NON_LINE", "DYNA_NON_LINE",
                     "CALC_MODES")
_EXPLICIT_SCHEMAS = ("DIFF_CENT", "TCHAMWA")


def _check_position_formulas(tag, params, sel, run_cfg, model_data):
    """
    False (reported) if params contains a formula in x, y, z
    (bridge_bcs.PositionFormula) that is not translated in this analysis.
    Otherwise True; for a force, displacement, rotation or line pressure
    a WARNING: Mecway 34 does not impose those with a formula in x, y, z
    (measured, see the header of bridge_bcs.py), the bridge does.
    """
    found = [(k, v) for k, v in params.items()
             if not k.startswith("_") and is_position(v)]
    if not found:
        return True
    what = tr("{0} op '{1}'", "{0} on '{1}'").format(tag, sel)
    solver = run_cfg.get("solver_command")
    if solver not in _POSITION_SOLVERS or (
            solver == "DYNA_NON_LINE" and
            run_cfg.get("schema", "HHT") in _EXPLICIT_SCHEMAS):
        _not_translated(model_data, what, tr(
            "formule in x, y, z ({0}) wordt alleen vertaald in statisch, "
            "niet-lineair statisch, impliciete dynamica, modaal en knik;",
            "formula in x, y, z ({0}) is only translated in static, "
            "nonlinear static, implicit dynamics, modal and buckling;")
            .format(", ".join(v.text() for _k, v in found)))
        return False
    if tag in ("force", "displacement", "noderotation", "linepressure"):
        log(tr("WARNING: {0}: formule in x, y, z ({1}). Mecway 34 legt "
               "zo'n {2} niet op (gemeten: reacties en verplaatsingen 0, "
               "interne solver en CCX); de bridge wel, met de waarde van "
               "de formule op elke plaats. De resultaten verschillen dan "
               "van Mecway.",
               "WARNING: {0}: formula in x, y, z ({1}). Mecway 34 does not "
               "apply such a {2} (measured: reactions and displacements 0, "
               "internal solver and CCX); the bridge does, with the value "
               "of the formula at each location. The results then differ "
               "from Mecway.").format(
                   what, ", ".join(v.text() for _k, v in found), tag))
    return True


def _check_bc_params(tag, item, params, sel, model_data):
    """False if the load cannot be translated (reported)."""
    if params.get("_skipped"):
        # formula that cannot be translated (bridge_bcs, ERROR logged)
        model_data["skipped_loads"].append(params["_skipped"])
        return False
    if tag == "centrifugal":
        if any(isinstance(v, list) for v in params.values()):
            _not_translated(model_data,
                            tr("tijdsafhankelijke centrifugaalkracht",
                               "time-dependent centrifugal force"),
                            tr("Code-Aster ROTATION heeft een vaste VITESSE "
                               "(de kracht schaalt met w^2);",
                               "Code-Aster ROTATION has a fixed VITESSE "
                               "(the force scales with w^2);"))
            return False
        nonzero = [ax for ax, v in params.items() if v != 0.0]
        if len(nonzero) != 1:
            _not_translated(model_data,
                            tr("centrifugaalkracht", "centrifugal force"),
                            tr("de as moet precies een van X, Y, Z zijn "
                               "(manual par. 9.20), hier {0};",
                               "the axis must be exactly one of X, Y, Z "
                               "(manual par. 9.20), here {0};").format(
                                   params))
            return False
        if any(bc["type"] == "centrifugal" for bc in model_data["bcs"]):
            _not_translated(model_data,
                            tr("tweede centrifugaalkracht",
                               "second centrifugal force"),
                            tr("Code-Aster ROTATION mag een keer per last en "
                               "het gyroscopisch effect van twee rotaties "
                               "wordt niet vertaald;",
                               "Code-Aster ROTATION is allowed once per load "
                               "and the gyroscopic effect of two rotations "
                               "is not translated;"))
            return False
    if tag == "linepressure" and params.get("_local") and \
            params.get("u", 0.0) not in (0.0, None):
        log(tr("WARNING: Line pressure op '{0}': U-component (axiaal) staat "
               "in Mecway als 'internal solver only'; vertaald als "
               "FORCE_POUTRE N.",
               "WARNING: Line pressure on '{0}': U component (axial) is "
               "marked 'internal solver only' in Mecway; translated as "
               "FORCE_POUTRE N.").format(sel))
    if tag == "elasticsupport" and params["kn"] == 0.0 and \
            params["kt"] == 0.0:
        log("INFO: Elastic support on '{0}' with stiffness 0; "
            "skipped.".format(sel))
        return False
    return True


# ==========================================
# MAIN FUNCTION
# ==========================================
def _plan_result_formula(item, model_data):
    """A Mecway result formula (<formula>, Solution > Formula) for the
    job: plan of bridge_formula.plan in model_data["result_formulas"]
    (bridge_to_aster.formulas_arg), or a WARNING plus skipped_loads if the
    bridge cannot evaluate it (KNOWN_BUGS 121, S33)."""
    import bridge_formula
    name = item.get("name", "")
    expr = (item.find("formula").text or "").strip()
    units = [(u.get("exponents", ""), u.text or "")
             for u in item.findall("unit")]
    try:
        p = bridge_formula.plan(name, item.get("fieldscalar") or "formula",
                                expr, units)
    except bridge_formula.FormulaError as e:
        model_data["skipped_loads"].append(tr(
            u"formule '{0}' ({1}): {2}; door Mecway opnieuw maken na het "
            u"laden",
            u"formula '{0}' ({1}): {2}; create it again in Mecway after "
            u"loading").format(name, expr, e))
        log(tr(u"WARNING: Formule '{0}' ({1}) kan de bridge niet uitrekenen "
               u"({2}); na het laden is hij ongeldig (rood). Verwijder de "
               u"formule en maak hem opnieuw via Solution > Formula: Mecway "
               u"rekent hem dan uit de resultaten van de bridge.",
               u"WARNING: Formula '{0}' ({1}) cannot be computed by the "
               u"bridge ({2}); after loading it is invalid (red). Delete the "
               u"formula and create it again via Solution > Formula: Mecway "
               u"then computes it from the bridge results.").format(
                   name, expr, e))
        return
    for note in p["notes"]:
        log(tr(u"WARNING: Formule '{0}' ({1}): {2}.",
               u"WARNING: Formula '{0}' ({1}): {2}.").format(name, expr,
                                                            note))
    model_data.setdefault("result_formulas", []).append(p)
    log("INFO: Formula '{0}' ({1}) -> computed by the bridge as '{2}' "
        "(symbols {3}).".format(name, expr, p["fieldscalar"],
                                ", ".join(sorted(p["symbols"])) or "-"))


def extract_aster_data_from_liml(file_path):
    """
    Parses the .liml file and returns model_data.

    Parameters
    ----------
    file_path : str  Absolute path to the active .liml file.

    Returns
    -------
    dict  model_data for Code-Aster file generation, or None on an
          unexpected error during parsing (ERROR in the log).
    """
    log("START: Analyseren van .liml")
    hex8_mod  = _elem_choice("elem_hex8")
    shell_mod = _elem_choice("elem_shell")
    beam_mod  = _elem_choice("elem_beam")
    log("INFO: Element formulation: hex8 -> {0}, linear shell -> {1}, "
        "beam -> {2}".format(hex8_mod, shell_mod, beam_mod))
    model_data = {
        "bcs":                  [],
        "couplings":            [],   # nodesurfacecoupling -> LIAISON_RBE3 / LIAISON_SOLIDE
        "materials":            {},   # {mat_name: {"E": float, "NU": float, "rho": float, ...}}
        "spring_materials":     {},   # {mat_name: spring_constant_N_per_m}
        "mat_geometrics":       {},   # {mat_name: geom_props_dict}
        "elsets":               {},   # {elset_name: mat_name}
        "elset_dims":           {},   # {elset_name: "1D"/"2D"/"3D"}
        "elset_modelisations":  {},   # {elset_name: MODELISATION string}
        "node_groups":          {},
        "beam_sections":        {},   # 1D beam elsets
        "shell_sections":       {},   # 2D shell elsets
        "spring_sections":      {},   # {elset_name: {"spring_constant": float}}
        "has_rot_dofs":         False,
        "has_1d":               False,
        "has_2d":               False,
        "has_3d":               False,
        "elem_shapes":          {},   # {eid (int): Mecway shape}
        # {eid: {"vec": (vx, vy, vz) or None, "angle": rad}} for beam
        # elements with their own orientation (bridge_mesh makes groups
        # with VECT_Y from them).
        "beam_orientations":    {},
        # Loads/boundary conditions that could not be translated; main()
        # reports them to the user at the end.
        "skipped_loads":        [],
        "face_selections":      {},   # {faceselection_name: [eid, ...]}
        # Mesh from the .liml (bridge_mesh.write_mesh):
        "mesh_nodes":           {},   # {nid: (x, y, z)} in m
        "mesh_elements":        [],   # [(eid, shape, [nid, ...], elset)]
        "face_selection_faces": {},   # {name: [(eid, faceid), ...]}
        "element_selections":   {},   # {name: [eid, ...]}
        "shell_upgrades":       {},   # {elset: [MODI_MAILLE-OPTION, ...]} (COQUE_3D)
        # Analysis from the .liml: <analysis type="S30|L30|D31|..." solver=...>
        # and <timesteps> (end time, start, output interval).
        "analysis_type":        "",
        "analysis_solver":      "",
        # Modal (V30): <analysis maxmode="..">, number of modes; None = not
        # given (bridge_to_aster._build_modal: setting modal_modes).
        "maxmode":              None,
        # D30 with <analysis modesuperposition="true">
        "mode_superposition":   False,
        "timesteps":            {},
        # contact2 -> DEFI_CONTACT: [{"master", "slave", "friction",
        # "selfcontact", "type"}]
        "contacts":             [],
        # <initialconditions><velocity>: [(selection, target, (vx, vy, vz))]
        "initial_velocities":   [],
        # Materials with OpenRadioss law VOID (no stiffness)
        "void_materials":       [],
        # The .liml itself (aster_results_export reads elsets/elements from it)
        "liml_path":            file_path,
        # #ASTER lines from the free text fields (bridge_custom.py)
        "aster_custom":         bridge_custom.empty(),
        # Mechanical model items (_parse_model_item):
        "thermal_stress":       None,  # {"tref": K}
        "temperatures":         [],    # [{"selection", "target", "value"}]
        # Node temperature (temperature3) in a mechanical analysis:
        # {nid: K} (_parse_node_temperatures)
        "node_temperatures":    {},
        "rayleigh":             None,  # {"alpha": 1/s, "beta": s}
        "constraint_equations": [],    # [{"terms": [(nid, DDL, coef)], ...}]
        "point_masses":         [],    # [{"selection", "kind", "value", ..}]
        # contact2 bonded* -> LIAISON_MAIL: [{"master", "slave", "type",
        # "tolerance", "kn", "kt"}]
        "bonded":               [],
        # line2 elements with material Gap/Damper (DIS_T) and TensionOnly
        # (CABLE): {mat_name: {...}} and per elset the section
        "line_discretes":       {},
        "discrete_sections":    {},    # {elset: {"kind": "gap"/"damper",..}}
        "cable_sections":       {},    # {elset: {"area": m2}}
        # Flexible joint on beam: [{"selection": face selection,
        # "free": ("u", "v", "w")}] (bridge_mesh._flexible_joints)
        "flexible_joints":      [],
    }

    try:
        root = _parse_model_root(file_path)
        # Items suppressed per configuration or via a group get
        # suppressed="true".
        _apply_suppression(root, model_data)

        # ==========================================
        # STEP 0: COLLECT ELEMENT SHAPES PER ELSET
        # ==========================================
        # Nodes and elements of the model (not those of <solution>):
        # bridge_mesh.py writes the Code-Aster mesh with these.
        for node in root.findall("node"):
            model_data["mesh_nodes"][int(node.get("nid"))] = (
                float(node.get("x", "0")), float(node.get("y", "0")),
                float(node.get("z", "0")))
        elset_shapes_map = {}
        truss_eids = {}             # {elset: set(eid)} with truss="true"
        line_eids = {}              # {elset: set(eid)} all 1D elements
        for elset_elem in root.findall("elset"):
            ename  = elset_elem.get("name", "Default")
            shapes = set()
            for e in elset_elem.findall("elem"):
                s = e.get("shape")
                if s:
                    shapes.add(s)
                    eid = e.get("eid")
                    if eid and s in _DIM_1D_SHAPES:
                        line_eids.setdefault(ename, set()).add(int(eid))
                        if e.get("truss") == "true":
                            truss_eids.setdefault(ename, set()).add(
                                int(eid))
                    if eid:
                        model_data["elem_shapes"][int(eid)] = s
                        model_data["mesh_elements"].append((
                            int(eid), s,
                            [int(n) for n in e.get("nodes", "").split()],
                            ename))
                    if eid and any(e.get(k) is not None for k in (
                            "orientationux", "orientationuy",
                            "orientationuz")):
                        # U axis (gap direction, manual v33 par. 7.9)
                        model_data.setdefault("elem_u_axes", {})[int(eid)] = \
                            tuple(float(e.get(k, "0")) for k in (
                                "orientationux", "orientationuy",
                                "orientationuz"))
                    if (eid and s in _DIM_1D_SHAPES and
                            e.get("truss") != "true"):
                        # A truss needs no orientation (manual
                        # v33 par. 7.6); BARRE has no VECT_Y.
                        orient = _parse_beam_orientation(e)
                        if orient is not None:
                            model_data["beam_orientations"][int(eid)] = \
                                orient
            elset_shapes_map[ename] = shapes
        truss_elsets, truss_parts = _split_trusses(
            model_data, elset_shapes_map, truss_eids, line_eids)

        # Faceselections: which elements carry the selected faces.
        # Needed to decide whether a face belongs to a volume element
        # (boundary element in AFFE_MODELE) or to a shell.
        for fs in root.findall("faceselection"):
            fname = fs.get("name")
            eids = []
            faces = []
            for face in fs.findall("face"):
                eid = face.get("eid")
                if eid:
                    eids.append(int(eid))
                    faces.append((int(eid), int(face.get("faceid", "0"))))
            if fname:
                model_data["face_selections"][fname] = eids
                model_data["face_selection_faces"][fname] = faces
        for es in root.findall("elementselection"):
            ename = es.get("name")
            eids = [int(e.get("eid")) for e in es.findall("element")
                    if e.get("eid")]
            if ename:
                model_data["element_selections"][ename] = eids

        # ==========================================
        # STEP 0b: ANALYSIS, TIME STEPS, OPENRADIOSS FUNCTIONS
        # ==========================================
        ana = root.find("analysis")
        if ana is not None:
            model_data["analysis_type"] = ana.get("type", "")
            model_data["analysis_solver"] = ana.get("solver", "")
            # Dynamic Response (D30) with the option Mode superposition
            # (manual v33 par. 6.4): <analysis type="D30"
            # modesuperposition="true" maxmode="10" /> (Mecway example
            # DampedVibratingStrip.liml).
            model_data["mode_superposition"] = (
                ana.get("modesuperposition", "") == "true")
            try:
                model_data["maxmode"] = int(ana.get("maxmode"))
            except (TypeError, ValueError):
                model_data["maxmode"] = None
            # Buckling (B30): shift = setting of Mecway's own solver
            # (manual v33 par. 6.6); only reported (bridge_to_aster).
            model_data["analysis_shift"] = ana.get("shift")
        # DST is not programmed in Code-Aster 17.4 for nonlinear
        # analyses: STAT_NON_LINE gave alarm CALCULEL_54 ("PCOMPOR de
        # l'option FULL_MECA n'est pas connu des TYPE_ELEM") and then
        # <EXCEPTION> MECANONLINE_3 (seen in a run, flat quad4 plate).
        # So only MECA_STATIQUE gets DST.
        run_cfg = _run_analysis_cfg(model_data["analysis_type"],
                                    model_data.get("mode_superposition"))
        solver_cmd = run_cfg.get("solver_command")
        # Thermal analysis: thermal loads, materials and initial
        # conditions are read by bridge_thermal.parse_thermal() (STEP 2b).
        thermal_run = bridge_thermal.is_thermal(run_cfg)
        # Thermal -> mechanical chain (bridge_thermomech.py, step S4b): a
        # transient thermal model (T31) with a Thermal stress. Mecway
        # uses Thermal stress only in mechanical analyses (manual v33
        # par. 9.25) but keeps it, with the mechanical boundary conditions,
        # also in a thermal model; the bridge does read them then.
        thermo_mech = (thermal_run and
                       model_data["analysis_type"] == "T31" and
                       any(it.tag == "thermalstress" and
                           it.get("suppressed", "") != "true"
                           for it in root))
        model_data["thermo_mech"] = thermo_mech
        if thermo_mech:
            log("INFO: Thermal stress in a transient thermal model: "
                "thermal -> mechanical chain (residual stress and distortion, "
                "bridge_thermomech.py); mechanical boundary conditions and "
                "loads are included.")
        # Acoustics (A30): materials and conditions are read by
        # bridge_acoustic.parse_acoustic() (STEP 2c).
        acoustic_run = bridge_acoustic.is_acoustic(run_cfg)
        # Vibro-acoustics (structure + fluid): fluid parts and pressure
        # nodes are read by bridge_vibroacoustic.parse_vibro() (STEP 2c).
        vibro_run = bridge_vibroacoustic.is_vibroacoustic(run_cfg)
        # Only report if the model has such elements (otherwise the
        # choice does not apply).
        all_shapes = set()
        for _shapes in elset_shapes_map.values():
            all_shapes |= _shapes
        has_lin_shells = bool(all_shapes & set(["tri3", "quad4"]))
        if shell_mod == "DST" and solver_cmd != "MECA_STATIQUE" and \
                has_lin_shells and not thermal_run:
            log(tr("WARNING: DST werkt in Code-Aster alleen lineair "
                   "(MECA_STATIQUE); voor {0} worden lineaire schalen "
                   "DKT.",
                   "WARNING: DST only works linearly in Code-Aster "
                   "(MECA_STATIQUE); for {0} linear shells become "
                   "DKT.").format(solver_cmd))
            shell_mod = "DKT"
        beam_mod = _gd_beam_choice(beam_mod, run_cfg, all_shapes,
                                   thermal_run)
        # 3D_SI cannot compute the stable time step: DYNA_NON_LINE with
        # DIFF_CENT gave <EXCEPTION> CALCUL_37 ("Le TYPE_ELEMENT MECA_HEXS8
        # ne sait pas encore calculer l'option: PAS_COURANT"), seen in a
        # run with Code-Aster 17.4. So explicit is always 3D.
        if hex8_mod == "3D_SI" and solver_cmd == "DYNA_NON_LINE" and \
                run_cfg.get("schema", "HHT") in ("DIFF_CENT", "TCHAMWA") \
                and "hex8" in all_shapes:
            log(tr("WARNING: 3D_SI werkt niet met een expliciet schema "
                   "({0}); hex8 worden 3D.",
                   "WARNING: 3D_SI does not work with an explicit scheme "
                   "({0}); hex8 become 3D.").format(run_cfg.get("schema")))
            hex8_mod = "3D"
        # LINE_QUAD (quadratic) explicit: lumped mass of HEXA20 with
        # DIFF_CENT NOT verified, so linear there.
        if hex8_mod == "LINE_QUAD" and solver_cmd == "DYNA_NON_LINE" and \
                run_cfg.get("schema", "HHT") in ("DIFF_CENT", "TCHAMWA") \
                and all_shapes & set(["hex8", "tet4", "wedge6", "pyr5"]):
            log(tr("WARNING: LINE_QUAD niet bij een expliciet schema "
                   "({0}); volume-elementen blijven lineair.",
                   "WARNING: LINE_QUAD not with an explicit scheme "
                   "({0}); volume elements stay linear.").format(
                    run_cfg.get("schema")))
            hex8_mod = "3D"
        model_data["hex8_choice"] = hex8_mod
        ts = root.find("timesteps")
        if ts is not None:
            model_data["timesteps"] = {
                "period": parse_and_convert(ts.get("timeperiod", "1 s"),
                                            "time"),
                "start": parse_and_convert(ts.get("timepointsstart", "0 s"),
                                           "time"),
                "increment": parse_and_convert(
                    ts.get("timepointsincrement", "0 s"), "time"),
                "outputtimes": ts.get("outputtimes", "regular"),
                "automatic": ts.get("automatictimestepping", "") == "true",
                # D30 (Dynamic Response): <timesteps timeperiod=".."
                # stepsize=".." [keepeverynthtimestep="n"] />; Mecway
                # writes a solution at t = 0 and every n-th step
                # (seen headless with Mecway 33, D30 with mode
                # superposition: stepsize 0.001 s, n = 10 gave 201 steps
                # over 2 s). bridge_to_aster._output_times.
                "stepsize": parse_and_convert(ts.get("stepsize", "0 s"),
                                              "time"),
                "keep_every": _positive_int(ts.get("keepeverynthtimestep")),
            }
            log("INFO: Time steps: {0}".format(model_data["timesteps"]))
        if (model_data["analysis_type"] == "D30" and solver_cmd ==
                "DYNA_NON_LINE" and (run_cfg.get("schema") != "NEWMARK" or
                                     run_cfg.get("deformation") != "PETIT")):
            # Mecway D30 without Mode superposition: linear, Newmark with the
            # average acceleration (manual v33 par. 6.4). With NEWMARK and
            # PETIT dyna_impl_3d computes the same scheme (verification MD-07).
            log(tr("WARNING: Mecway Dynamic Response (D30) rekent lineair met "
                   "Newmark; de bridge rekent met schema {0} en deformation "
                   "{1}. Gelijk aan Mecway: schema NEWMARK en deformation "
                   "PETIT (pagina Dynamisch (impliciet)), of in Mecway Mode "
                   "superposition (dyna_modal_3d).",
                   "WARNING: Mecway Dynamic Response (D30) computes linearly "
                   "with Newmark; the bridge uses schema {0} and deformation "
                   "{1}. Same as Mecway: schema NEWMARK and deformation PETIT "
                   "(page Dynamic (implicit)), or Mode superposition in "
                   "Mecway (dyna_modal_3d).").format(
                       run_cfg.get("schema"), run_cfg.get("deformation")))
        # Every occurrence of a field, in file order: Mecway keeps a second
        # <ccxmodeldefinition> when one is imported into a model that has
        # one already (MecwaySectionProps adds its lines that way; Mecway 34,
        # headless, 23 Oct 2026).
        model_data["aster_custom"] = bridge_custom.parse(
            [el.text for tag in bridge_custom.CUSTOM_TAGS
             for el in root.findall(tag)])
        section_extras = _section_extras(
            model_data["aster_custom"].get("sections", []))
        mat_names = set(m.get("name") for m in root.findall("mat"))
        for name in sorted(set(section_extras) - mat_names):
            log(tr("WARNING: #ASTER-SECTIE '{0}': geen materiaal met deze "
                   "naam (hernoemd?); de regel wordt genegeerd.",
                   "WARNING: #ASTER-SECTIE '{0}': no material with this "
                   "name (renamed?); the line is ignored.").format(name))
        radioss_text = root.findtext("radiossmodeldefinition") or ""
        radioss_functions = bridge_radioss.parse_functions(radioss_text)
        radioss_units = bridge_radioss.begin_units(radioss_text)
        cards = bridge_radioss.other_cards(radioss_text)
        if cards:
            model_data["skipped_loads"].append(
                tr("OpenRadioss-kaarten in de model definition: {0}",
                   "OpenRadioss cards in the model definition: {0}"
                   ).format(", ".join(cards)))
            log(tr("ERROR: OpenRadioss-kaarten worden niet vertaald: {0}. "
                   "Alleen /FUNCT (voor PLAS_TAB) wordt gelezen.",
                   "ERROR: OpenRadioss cards are not translated: {0}. "
                   "Only /FUNCT (for PLAS_TAB) is read.").format(
                    ", ".join(cards)))

        # ==========================================
        # STEP 1: READ NODE GROUPS
        # ==========================================
        for ns in root.findall("nodeselection"):
            name     = ns.get("name")
            node_ids = []
            for node in ns.findall("node"):
                nid = node.get("nid")
                if nid:
                    node_ids.append("N{0}".format(nid))
            if name and node_ids:
                model_data["node_groups"][name] = node_ids
                log("INFO: NodeGroup '{0}' -> {1} nodes".format(
                    name, len(node_ids)))

        # ==========================================
        # STEP 2: PROCESS REMAINING ELEMENTS
        # ==========================================
        for item in root:
            tag = item.tag
            log("DEBUG tag: '{0}' selection='{1}'".format(
                tag, item.get("selection", "")))

            # --------------------------------------------------
            # 2a. MATERIALS
            # --------------------------------------------------
            if tag == "mat":
                mat_name  = item.get("name", "UnknownMat")
                mech_node = item.find("mechanical")
                geom_node = item.find("geometric")
                dens_node = item.find("density")
                _parse_failure(item.find("failure"), mat_name, model_data)

                if mech_node is not None:
                    mech_type = mech_node.get("type", "Isotropic")

                    if mech_type == "Spring":
                        k = parse_and_convert(
                            mech_node.get("springconstant", "0"),
                            'spring_stiffness')
                        model_data["spring_materials"][mat_name] = k
                        log("INFO: Spring material '{0}' -> k={1} N/m".format(
                            mat_name, k))

                    elif mech_type == "Isotropic":
                        mat_props = {
                            "E":    parse_and_convert(
                                        mech_node.get("youngsmodulus",
                                                      "210000000000"),
                                        'pressure'),
                            # Without poissonratio Mecway uses nu = 0
                            # (measured headless: VibratingCantileverSolid
                            # gave the frequencies of nu = 0 in Mecway;
                            # with 0.3 the bridge deviated +1.7%).
                            "NU":   parse_and_convert(
                                        mech_node.get("poissonratio", "0"),
                                        'dimensionless'),
                            "Texp": parse_and_convert(
                                        mech_node.get("thermalexpansion", "0"),
                                        'inversetemp'),
                            "rho":  0.0,
                        }
                        if dens_node is not None:
                            mat_props["rho"] = parse_and_convert(
                                dens_node.get("density", "0"), 'density')

                        # --- Plastic hardening curve (optional) ---
                        # Mecway:
                        #   <plastic type="Isotropic">
                        #     <hardeningcurve strain="0"    stress="0 MPa" />
                        #     <hardeningcurve strain="0.01" stress="235 MPa" />
                        #     ...
                        #   </plastic>
                        #
                        # The curve is only sorted by strain here and
                        # otherwise stored UNCHANGED as
                        # (strain, stress) tuples in SI units.
                        #
                        # The conversion to the Code-Aster TRACTION definition
                        # (total strain EPSI, first point = elastic limit,
                        # NO point with abscissa zero; U4.43.01 par. 5.1.1)
                        # and all validation happen in bridge_to_aster.py
                        # (_to_aster_traction_curve), controlled by
                        # CONFIG_BRIDGE ... "plastic_strain_definition".
                        plastic_node = item.find("plastic")
                        if plastic_node is not None:
                            plastic_type = plastic_node.get("type", "Isotropic")
                            curve = []
                            for hc in plastic_node.findall("hardeningcurve"):
                                strain = parse_and_convert(
                                    hc.get("strain", "0"), 'dimensionless')
                                stress = parse_and_convert(
                                    hc.get("stress", "0"), 'pressure')
                                curve.append((strain, stress))
                            curve.sort(key=lambda sc: sc[0])
                            # Types (manual v33 par. 8.8; mecway.exe lists
                            # BilinearIsotropic, BilinearKinematic,
                            # Kinematic, RambergOsgood next to Isotropic;
                            # 'Simple' in that list is the type of
                            # <density>, not plasticity). XML of
                            # Isotropic, BilinearIsotropic en RambergOsgood
                            # seen in Forum_models/TensileBlockTest.liml:
                            # BilinearIsotropic / BilinearKinematic
                            # (yieldstrength, tangentmodulus), RambergOsgood
                            # (yieldstrength, rambergosgoodexponent,
                            # rambergossgoodalpha), Kinematic: a
                            # hardening curve like Isotropic
                            # (_kinematic_curve). Perfectly plastic:
                            # Bilinear with tangentmodulus 0 (ECRO_LINE
                            # D_SIGM_EPSI=0.0 is allowed, test case forma20c).
                            # Curve as total strain: E = slope of the first
                            # segment, like Mecway (_curve_young); also in
                            # linear/modal analyses of this model (CCX
                            # linear static measured the same).
                            if plastic_type in ("Isotropic", "Kinematic") \
                                    and curve:
                                e_new = _curve_young(
                                    curve, mat_props["E"], mat_name,
                                    run_cfg.get("plastic_strain_definition",
                                                "auto"))
                                if e_new != mat_props["E"]:
                                    mat_props["E_elastic_tab"] = \
                                        mat_props["E"]
                                    mat_props["E"] = e_new
                            if plastic_type == "Kinematic" and curve:
                                bil = _kinematic_curve(
                                    curve, mat_props["E"], mat_name,
                                    run_cfg.get("plastic_strain_definition",
                                                "auto"))
                                if bil is not None:
                                    mat_props["plastic_type"] = \
                                        "BilinearKinematic"
                                    mat_props["plastic_bilinear"] = bil
                                    curve = []
                                    plastic_type = "done"
                            elif plastic_type in ("BilinearIsotropic",
                                                  "BilinearKinematic"):
                                bil = _parse_bilinear(plastic_node, mat_name,
                                                      plastic_type,
                                                      mat_props.get("E"))
                                if bil is not None:
                                    mat_props["plastic_type"] = plastic_type
                                    mat_props["plastic_bilinear"] = bil
                                    curve = []
                                    plastic_type = "done"
                            elif plastic_type == "RambergOsgood":
                                ro = _ramberg_osgood_curve(
                                    plastic_node, mat_props["E"], mat_name)
                                if ro:
                                    curve = ro
                                    plastic_type = "Isotropic"
                                    mat_props["curve_definition"] = "plastic"
                            if plastic_type != "done" and (
                                    plastic_type != "Isotropic" or not curve):
                                model_data["skipped_loads"].append(tr(
                                    "plasticiteit van materiaal '{0}' (type "
                                    "'{1}'): elastisch gerekend",
                                    "plasticity of material '{0}' (type "
                                    "'{1}'): computed as elastic").format(
                                        mat_name, plastic_type))
                                log(tr(
                                    "ERROR: Plasticiteit van materiaal '{0}' "
                                    "(type '{1}', {2} curvepunten) wordt niet "
                                    "ondersteund; materiaal elastisch "
                                    "gerekend.",
                                    "ERROR: Plasticity of material '{0}' "
                                    "(type '{1}', {2} curve points) is not "
                                    "supported; material computed as "
                                    "elastic.").format(
                                        mat_name, plastic_type, len(curve)))
                                curve = []
                            if curve:
                                mat_props["plastic_type"]  = plastic_type
                                mat_props["plastic_curve"] = curve
                                log("INFO: Plastic curve '{0}' for "
                                    "material '{1}': {2} points, first "
                                    "point ({3}, {4}).".format(
                                        plastic_type, mat_name, len(curve),
                                        curve[0][0], curve[0][1]))

                        model_data["materials"][mat_name] = mat_props
                        log("INFO: Material '{0}' -> E={1} Pa, NU={2}, "
                            "Texp={3} 1/K, rho={4} kg/m3, plastic={5}".format(
                                mat_name,
                                mat_props["E"],  mat_props["NU"],
                                mat_props["Texp"], mat_props["rho"],
                                "plastic_curve" in mat_props))

                    elif mech_type in ("NeoHooke", "MooneyRivlin"):
                        hyp = _parse_hyperelastic(mech_node, dens_node,
                                                  mech_type, mat_name)
                        if hyp is not None:
                            model_data["materials"][mat_name] = hyp

                    elif "foam" in mech_type.lower():
                        log(tr("ERROR: Materiaal '{0}': type '{1}' "
                               "(hyperfoam) wordt niet vertaald. Code-Aster "
                               "heeft geen hyperfoam-wet in "
                               "DEFI_MATERIAU; die kan alleen via MFront, en "
                               "dat zit niet in de Windows-versie van "
                               "Code-Aster. Kies Neo Hooke of "
                               "Mooney-Rivlin.",
                               "ERROR: Material '{0}': type '{1}' "
                               "(hyperfoam) is not translated. Code-Aster "
                               "has no hyperfoam law in DEFI_MATERIAU; it "
                               "is only possible via MFront, which is not "
                               "in the Windows version of Code-Aster. "
                               "Choose Neo Hooke or Mooney-Rivlin.").format(
                                   mat_name, mech_type))

                    elif mech_type in ("Gap", "Damper"):
                        # Mecway (manual v33 par. 7.8/7.9) on line2:
                        #   <mechanical type="Gap" closedstiffness="1E9 N/m"
                        #     [initialclearance=".." openforce=".."] />
                        #   <mechanical type="Damper"
                        #     dampingcoefficient="50 N.s/m" />
                        # initialclearance/openforce: attribute names from
                        # mecway.exe (in the list of material attributes,
                        # between springconstant/dampingcoefficient and
                        # closedstiffness), NOT seen in a .liml.
                        if mech_type == "Gap":
                            ld = {"kind": "gap",
                                  "k": parse_and_convert(mech_node.get(
                                      "closedstiffness", "0"),
                                      "spring_stiffness"),
                                  "clearance": parse_and_convert(
                                      mech_node.get("initialclearance", "0"),
                                      "length")}
                            if mech_node.get("openforce") is not None:
                                log("INFO: Gap '{0}': 'force of open gap' "
                                    "(CCX only, smooth transition) is "
                                    "not used; Code-Aster DIS_CHOC is "
                                    "a hard switch.".format(mat_name))
                        else:
                            ld = {"kind": "damper",
                                  "c": parse_and_convert(mech_node.get(
                                      "dampingcoefficient", "0"), "damping")}
                        model_data["line_discretes"][mat_name] = ld
                        log("INFO: {0} material '{1}': {2}".format(
                            mech_type, mat_name, ld))

                    elif mech_type == "TensionOnly":
                        # Mecway (manual v33 par. 7.10): truss that only
                        # carries tension, stiffness E A / L. Code-Aster: cable
                        # (MODELISATION='CABLE', RELATION='CABLE', U4.42.01
                        # AFFE_CARA_ELEM CABLE; DEFI_MATERIAU CABLE).
                        model_data["materials"][mat_name] = {
                            "E": parse_and_convert(mech_node.get(
                                "youngsmodulus", "0"), "pressure"),
                            "NU": 0.0, "Texp": 0.0, "rho": (
                                parse_and_convert(dens_node.get(
                                    "density", "0"), "density")
                                if dens_node is not None else 0.0),
                            "tension_only": True}
                        log("INFO: TensionOnly material '{0}': E={1} Pa "
                            "(cable).".format(mat_name, model_data[
                                "materials"][mat_name]["E"]))

                    else:
                        log(tr("WARNING: Onbekend mechanisch type '{0}' voor "
                               "materiaal '{1}'. Overgeslagen.",
                               "WARNING: Unknown mechanical type '{0}' for "
                               "material '{1}'. Skipped.").format(
                                mech_type, mat_name))

                radioss_node = item.find("openradioss")
                if mech_node is None and radioss_node is not None:
                    law = radioss_node.get("law", "")
                    if law == "PLAS_TAB":
                        props, notes = bridge_radioss.parse_plas_tab(
                            radioss_node.findtext("fieldcontents"),
                            radioss_functions, mat_name, radioss_units)
                        if props is not None:
                            if dens_node is not None:
                                props["rho"] = parse_and_convert(
                                    dens_node.get("density", "0"), 'density')
                            model_data["materials"][mat_name] = props
                        model_data["skipped_loads"].extend(notes)
                    elif law == "VOID":
                        model_data["void_materials"].append(mat_name)
                        log(tr("WARNING: Materiaal '{0}' heeft OpenRadioss "
                               "law VOID (geen stijfheid); de elementen "
                               "komen niet in het Code-Aster-model.",
                               "WARNING: Material '{0}' has OpenRadioss "
                               "law VOID (no stiffness); its elements are "
                               "left out of the Code-Aster model.").format(
                                   mat_name))
                    else:
                        model_data["skipped_loads"].append(
                            tr("materiaal '{0}' (OpenRadioss law {1})",
                               "material '{0}' (OpenRadioss law {1})"
                               ).format(mat_name, law))
                        log(tr("ERROR: OpenRadioss law '{0}' van materiaal "
                               "'{1}' wordt niet vertaald.",
                               "ERROR: OpenRadioss law '{0}' of material "
                               "'{1}' is not translated.").format(
                                   law, mat_name))

                if geom_node is not None:
                    geom_props = _parse_geometric_props(geom_node)
                    if geom_props is not None and \
                            mat_name in section_extras:
                        geom_props = _apply_section_extras(
                            mat_name, geom_props, section_extras[mat_name])
                    if geom_props is not None:
                        model_data["mat_geometrics"][mat_name] = geom_props
                        log("INFO: Geometry type '{0}' stored for "
                            "material '{1}'.".format(
                                geom_props.get("geom_type", "?"), mat_name))

            # --------------------------------------------------
            # 2b. ELEMENT SETS
            # --------------------------------------------------
            elif tag == "elset":
                elset_name   = item.get("name", "Default")
                mat_assigned = item.get("material", None)
                if mat_assigned:
                    model_data["elsets"][elset_name] = mat_assigned
                    # With the Mecway name (bridge_mesh renames "elsets"):
                    # factor of safety per elset (aster_results_export).
                    model_data.setdefault("mecway_elset_materials", {})[
                        elset_name] = mat_assigned

                shapes = elset_shapes_map.get(elset_name, set())
                # An elset gets one MODELISATION (1D over 2D over 3D);
                # Code-Aster then does not model elements of another
                # dimension (AFFE_MODELE does not assign that type). Report.
                for dim_shapes in (_DIM_1D_SHAPES, _DIM_2D_SHAPES,
                                   _DIM_3D_SHAPES):
                    if shapes & dim_shapes:
                        lost = sorted(shapes - dim_shapes)
                        if lost:
                            model_data["skipped_loads"].append(tr(
                                "elset '{0}': {1}-elementen niet "
                                "gemodelleerd (gemengde dimensies)",
                                "elset '{0}': {1} elements not modelled "
                                "(mixed dimensions)").format(
                                    elset_name, ", ".join(lost)))
                            log(tr("ERROR: Elset '{0}' mengt elementen van "
                                   "verschillende dimensie ({1}); alleen "
                                   "{2} wordt gemodelleerd, {3} NIET. "
                                   "Splits de component in Mecway.",
                                   "ERROR: Elset '{0}' mixes elements of "
                                   "different dimensions ({1}); only {2} "
                                   "is modelled, {3} is NOT. Split the "
                                   "component in Mecway.").format(
                                    elset_name, ", ".join(sorted(shapes)),
                                    ", ".join(sorted(shapes & dim_shapes)),
                                    ", ".join(lost)))
                        break

                if shapes & _DIM_1D_SHAPES:
                    dim          = "1D"
                    # Default POU_D_E: Euler-Bernoulli, as Mecway itself
                    # ("Mecway's beam elements use Euler beam theory",
                    # Mecway-manual v33 par. 7.5). POU_D_T (Timoshenko) via
                    # CONFIG_BRIDGE["elem_beam"]; it needs AY/AZ with
                    # SECTION='GENERALE' (STEP 3,
                    # _add_shear_coefs). POU_D_E exists only on SEG2
                    # (code_aster catalogue phenomenons_modelisations.py).
                    modelisation = beam_mod
                    model_data["has_1d"] = True
                    if "line3" in shapes and not thermal_run:
                        # Quadratic beam (Mecway: only with CCX, manual
                        # v33 par. 7.5): bridge_mesh.write_mesh splits each
                        # line3 element at the mid node into two SEG2 cells
                        # (KNOWN_BUGS choice C4); the check for non-beams
                        # (truss, spring, ...) comes after STEP 3.
                        log("INFO: Elset '{0}' contains line3 beams; each "
                            "element is split at the mid node into "
                            "two SEG2 cells ({1}).".format(
                                elset_name, beam_mod))
                elif shapes & _DIM_2D_SHAPES:
                    dim          = "2D"
                    model_data["has_2d"] = True
                    # Code-Aster v17.4.0 catalogue:
                    #   DKT      : TRIA3, QUAD4
                    #   COQUE_3D : TRIA7, QUAD9 (convert TRIA6/QUAD8 first
                    #              with CREA_MAILLAGE MODI_MAILLE TRIA6_7/QUAD8_9)
                    linear    = shapes & {"tri3", "quad4"}
                    quadratic = shapes & {"tri6", "quad8"}
                    if quadratic and not linear:
                        modelisation = "COQUE_3D"
                        upgrades = []
                        if "quad8" in shapes:
                            upgrades.append("QUAD8_9")
                        if "tri6" in shapes:
                            upgrades.append("TRIA6_7")
                        model_data["shell_upgrades"][elset_name] = upgrades
                    elif shell_mod == "COQUE_3D" and not quadratic:
                        # Choice COQUE_3D for linear shells: Code-Aster
                        # first makes them quadratic (LINE_QUAD, then
                        # QUAD8_9/TRIA6_7); bridge_to_aster._resolve_line_quad
                        # checks whether that can be done conformally.
                        modelisation = "COQUE_3D"
                        upgrades = ["LINE_QUAD"]
                        if "quad4" in shapes:
                            upgrades.append("QUAD8_9")
                        if "tri3" in shapes:
                            upgrades.append("TRIA6_7")
                        model_data["shell_upgrades"][elset_name] = upgrades
                    else:
                        # DKT (default) or DST via CONFIG_BRIDGE
                        # ["elem_shell"]; both on TRIA3/QUAD4.
                        modelisation = (shell_mod if shell_mod != "COQUE_3D"
                                        else "DKT")
                        if quadratic:
                            model_data["skipped_loads"].append(tr(
                                "elset '{0}': kwadratische schaalelementen "
                                "niet gemodelleerd (gemengd met lineaire)",
                                "elset '{0}': quadratic shell elements not "
                                "modelled (mixed with linear ones)").format(
                                    elset_name))
                            log(tr("ERROR: Elset '{0}' mengt lineaire en "
                                   "kwadratische schaal-elementen. {1} wordt "
                                   "gebruikt; de kwadratische elementen "
                                   "worden door Code-Aster niet "
                                   "gemodelleerd.",
                                   "ERROR: Elset '{0}' mixes linear and "
                                   "quadratic shell elements. {1} is used; "
                                   "the quadratic elements are not modelled "
                                   "by Code-Aster.").format(
                                    elset_name, modelisation))
                else:
                    dim          = "3D"
                    modelisation = "3D"
                    if shapes:
                        model_data["has_3d"] = True
                    # 3D_SI (reduced integration) only for elsets with
                    # hex8 only; otherwise it stays 3D.
                    if hex8_mod == "3D_SI" and shapes:
                        if shapes == set(["hex8"]):
                            modelisation = "3D_SI"
                            log(tr("WARNING: Elset '{0}' -> 3D_SI "
                                   "(onderintegratie). Met 1 element over de "
                                   "dikte is de buigspanning ~0 en kloppen "
                                   "de reacties niet (KNOWN_BUGS 1). Alarm "
                                   "MODELE1_7 van Code-Aster: alleen correct "
                                   "voor hex8 die parallellepipedums "
                                   "zijn.",
                                   "WARNING: Elset '{0}' -> 3D_SI "
                                   "(under-integration). With 1 element "
                                   "through the thickness the bending stress "
                                   "is ~0 and the reactions are wrong "
                                   "(KNOWN_BUGS 1). Code-Aster alarm "
                                   "MODELE1_7: only correct for hex8 that "
                                   "are parallelepipeds.").format(elset_name))
                        else:
                            log(tr("WARNING: Elset '{0}' bevat naast hex8 ook "
                                   "{1}; 3D_SI alleen bij uitsluitend hex8, "
                                   "dus MODELISATION='3D'.",
                                   "WARNING: Elset '{0}' contains {1} "
                                   "besides hex8; 3D_SI only with hex8 "
                                   "alone, so MODELISATION='3D'.").format(
                                    elset_name, ", ".join(sorted(
                                        shapes - set(["hex8"])))))

                if elset_name in truss_elsets and dim == "1D":
                    modelisation = "BARRE"      # _split_trusses
                model_data["elset_dims"][elset_name]          = dim
                model_data["elset_modelisations"][elset_name] = modelisation
                log("INFO: Elset '{0}' -> dim={1}, MODELISATION='{2}'".format(
                    elset_name, dim, modelisation))
                # Truss part of a component with beams (_split_trusses)
                for part in truss_parts.get(elset_name, []):
                    if mat_assigned:
                        model_data["elsets"][part] = mat_assigned
                    model_data["elset_dims"][part] = "1D"
                    model_data["elset_modelisations"][part] = "BARRE"
                    model_data["has_1d"] = True
                    log("INFO: Elset '{0}' (truss part of '{1}') -> dim=1D, "
                        "MODELISATION='BARRE'".format(part, elset_name))

            # --------------------------------------------------
            # 2b'. ELEMENT ORIENTATION as a Loads & Constraints item
            # (bridge_orientation; applied in STEP 4 like the per-element
            # attributes). In every analysis: without beams, shells or
            # gaps it only gives an INFO line.
            # --------------------------------------------------
            elif tag == bridge_orientation.TAG:
                if item.get("suppressed", "") == "true":
                    log("INFO: {0} on '{1}' skipped (suppressed).".format(
                        tag, item.get("selection", "")))
                    continue
                bridge_orientation.parse(item, model_data)

            # --------------------------------------------------
            # 2c. NODESURFACECOUPLING  (RBE2 / RBE3)
            #
            # Mecway XML:
            #   <nodesurfacecoupling selectionsurface="RBESlave"
            #                        selectionnode="RBEMaster"
            #                        type="rbe3" surfacerot="false" />
            #   <nodesurfacecoupling selectionsurface="RBESL2"
            #                        selectionnode="RBEMA1"
            #                        type="rigidbody" surfacerot="false" />
            #
            # Mapping:
            #   selectionnode    -> master (1 node, GROUP_NO_MAIT for RBE3)
            #   selectionsurface -> slaves (n nodes, GROUP_NO_ESCL for RBE3)
            #   type="rbe3"      -> LIAISON_RBE3
            #   type="rigidbody" -> LIAISON_SOLIDE  (master + slaves =
            #                                       1 rigid body)
            #   surfacerot=true  -> DDL_MAIT also contains DRX/DRY/DRZ (rbe3 only)
            #
            # Slaves (selectionsurface):
            #   - nodeselection -> GROUP_NO with the same name;
            #   - faceselection -> the faces are GROUP_MA in the mesh
            #     (bridge_mesh.py, boundary elements); bridge_to_aster.py makes
            #     a node group from them with DEFI_GROUP
            #     CREA_GROUP_NO=_F(NOM=..., GROUP_MA=...).
            # Master (selectionnode): a free node (without element) gets
            #   a POI1 element in bridge_mesh.py (DIS_T, or DIS_TR for rbe3
            #   with surfacerot=true), otherwise it has no degrees of freedom
            #   in the model.
            # --------------------------------------------------
            elif acoustic_run and (
                    tag in bridge_acoustic.ACOUSTIC_TAGS or
                    tag in SUPPORTED_BCS or tag in _MODEL_ITEM_TAGS or
                    tag in bridge_thermal.THERMAL_TAGS or tag in (
                        "nodesurfacecoupling", "contact2",
                        "initialconditions")):
                # Acoustic analysis: only fluid pressure (and impedance)
                # take part; bridge_acoustic reports the rest.
                bridge_acoustic.note_tag(item, model_data)
                continue
            elif tag in bridge_acoustic.ACOUSTIC_TAGS:
                # Only in Acoustic Resonance (manual v33 par. 9.34, 9.35);
                # in vibro-acoustics parse_vibro reads them (STEP 2c).
                if item.get("suppressed", "") != "true" and not vibro_run:
                    log("INFO: Acoustic condition '{0}' on '{1}' is "
                        "ignored in this analysis.".format(
                            tag, item.get("selection", "")))
                continue
            elif tag == "nodesurfacecoupling":
                if item.get("suppressed", "") == "true":
                    log("INFO: nodesurfacecoupling skipped (suppressed).")
                    continue

                coupling_type = item.get("type", "")
                surfacesel    = item.get("selectionsurface", "")
                nodesel       = item.get("selectionnode", "")
                surface_rot   = item.get("surfacerot", "false").lower() == "true"

                if not surfacesel or not nodesel:
                    log(tr("WARNING: nodesurfacecoupling mist "
                           "selectionsurface of selectionnode. Overgeslagen.",
                           "WARNING: nodesurfacecoupling lacks "
                           "selectionsurface or selectionnode. Skipped."))
                    continue

                # selectionsurface: nodeselection (nodes) or faceselection
                # (faces; the slave nodes are derived in the .comm with
                # DEFI_GROUP CREA_GROUP_NO=_F(GROUP_MA=...)).
                if _has_selection(root, "nodeselection", surfacesel):
                    slave_kind = "GROUP_NO"
                elif _has_selection(root, "faceselection", surfacesel):
                    slave_kind = "GROUP_MA"
                else:
                    log(tr("WARNING: nodesurfacecoupling: selectionsurface "
                           "'{0}' is geen node- of faceselection. "
                           "Overgeslagen.",
                           "WARNING: nodesurfacecoupling: selectionsurface "
                           "'{0}' is not a node or face selection. "
                           "Skipped.").format(surfacesel))
                    continue
                if not _has_selection(root, "nodeselection", nodesel):
                    log(tr("WARNING: nodesurfacecoupling: selectionnode "
                           "'{0}' is geen nodeselection. Overgeslagen.",
                           "WARNING: nodesurfacecoupling: selectionnode "
                           "'{0}' is not a node selection. Skipped."
                           ).format(nodesel))
                    continue

                if coupling_type == "rbe3":
                    kind = "rbe3"
                elif coupling_type == "rigidbody":
                    kind = "rbe2"
                else:
                    log(tr("WARNING: Onbekend coupling type '{0}'. "
                           "Ondersteund: 'rbe3', 'rigidbody'. Overgeslagen.",
                           "WARNING: Unknown coupling type '{0}'. "
                           "Supported: 'rbe3', 'rigidbody'. Skipped."
                           ).format(coupling_type))
                    continue

                model_data["couplings"].append({
                    "type":         kind,
                    "master_group": nodesel,     # selectionnode = master
                    "slave_group":  surfacesel,  # selectionsurface = slaves
                    "slave_kind":   slave_kind,  # GROUP_NO or GROUP_MA
                    "surface_rot":  surface_rot,
                })
                log("INFO: Coupling '{0}': master='{1}', slaves='{2}', "
                    "surfacerot={3}".format(
                        kind, nodesel, surfacesel, surface_rot))

            # --------------------------------------------------
            # 2c-bis. CONTACT (contact2) -> DEFI_CONTACT
            # <contact2 selectionmaster=".." selectionslave=".."
            #           type="unilateralelastic" selfcontact="false">
            #   <frictioncoefficient>0</frictioncoefficient> ...
            # --------------------------------------------------
            elif tag == "contact2":
                if item.get("suppressed", "") == "true":
                    continue
                contact = {
                    "master": item.get("selectionmaster", ""),
                    "slave": item.get("selectionslave", ""),
                    "type": item.get("type", ""),
                    "selfcontact": item.get("selfcontact", "") == "true",
                    "friction": parse_and_convert(
                        item.findtext("frictioncoefficient") or "0",
                        "dimensionless"),
                }
                # A contact whose selections are empty lost its reference in
                # Mecway: Mecway 34 replaces spaces in selection names by
                # underscores when it opens an older .liml and then writes
                # selectionmaster="" (seen 22 Oct 2026 with
                # Voorbeeld_C.liml from Mecway 33). Without the contact the
                # parts are not connected and Code-Aster stops without
                # convergence. Kept aside here; bridge_to_aster.
                # _check_lost_contacts decides per analysis (fatal where the
                # contact would be translated, else a WARNING: Mecway
                # ignores unilateral contact in linear and thermal
                # analyses).
                if not contact["master"] or (not contact["selfcontact"]
                                             and not contact["slave"]):
                    model_data.setdefault("lost_contacts", []).append(
                        contact)
                    continue
                # Mecway knows unilateralelastic (contact) and bondedelastic/
                # bondedtie/bondedce (bonded; type names from mecway.exe).
                # Bonded is not DEFI_CONTACT (that could separate),
                # but LIAISON_MAIL (bridge_mesh._bonded).
                # Stiffness per area (Pa/m): Mecway's penalty contact;
                # the bridge uses it with contact_algo = PENALISATION
                # (bridge_to_aster._build_contact_block) and with bonded
                # 'elastic' (only reported). Mecway requires kn > 0 ("Normal
                # stiffness per unit area ... must be strictly positive",
                # mecway.exe).
                contact["kn"] = parse_and_convert(
                    item.findtext("normalstiffness") or "0",
                    "stiffness_per_area")
                contact["kt"] = parse_and_convert(
                    item.findtext("tangentialstiffness") or "0",
                    "stiffness_per_area")
                if contact["type"] in ("bondedtie", "bondedce",
                                       "bondedelastic"):
                    contact["tolerance"] = parse_and_convert(
                        item.findtext("tolerance") or "0", "length")
                    # Thermal 'elastic': thermal resistance layer with
                    # "Thermal conductance per unit area" (manual v33 par.
                    # 9.9.1), W/m²/K; bridge_thermal.bonded_loads ->
                    # ECHANGE_PAROI. Tag name: Mecway 34 (CCX solver,
                    # headless) computes the resistance layer with
                    # <conductanceperarea> (TH-04c: 340/360 K), not with
                    # <thermalcontactconductance>.
                    text = item.findtext("conductanceperarea")
                    if text:
                        contact["conductance"] = parse_and_convert(
                            text, "heat_transfer")
                    model_data["bonded"].append(contact)
                    log("INFO: Bonded contact {0}".format(contact))
                    continue
                if contact["type"] not in ("unilateralelastic", ""):
                    model_data["skipped_loads"].append(
                        tr("contact '{0}' / '{1}' van type '{2}'",
                           "contact '{0}' / '{1}' of type '{2}'").format(
                            contact["master"], contact["slave"],
                            contact["type"]))
                    log(tr("ERROR: Contact van onbekend type '{0}'. NIET "
                           "meegenomen.",
                           "ERROR: Contact of unknown type '{0}'. NOT "
                           "included.").format(contact["type"]))
                    continue
                model_data["contacts"].append(contact)
                log("INFO: Contact {0}".format(contact))

            # --------------------------------------------------
            # 2c-ter. INITIAL CONDITIONS
            # <initialconditions><velocity selection=".."><value>..</value>
            #   <x>..</x><y>..</y><z>..</z></velocity></initialconditions>
            # --------------------------------------------------
            elif tag == "initialconditions":
                for ic in item:
                    sel = ic.get("selection", "")
                    if ic.tag == "temperature2":
                        # Initial temperature: bridge_thermal; does not
                        # apply in a mechanical analysis.
                        if not thermal_run and ic.get("suppressed") != "true":
                            log("INFO: Initial temperature on '{0}' does not "
                                "apply in a mechanical analysis.".format(sel))
                        continue
                    if ic.tag != "velocity" or ic.get("suppressed") == "true":
                        if ic.get("suppressed") != "true":
                            model_data["skipped_loads"].append(
                                tr("beginvoorwaarde {0} op '{1}'",
                                   "initial condition {0} on '{1}'").format(
                                    ic.tag, sel))
                            log(tr("ERROR: Beginvoorwaarde '{0}' wordt niet "
                                   "vertaald.",
                                   "ERROR: Initial condition '{0}' is not "
                                   "translated.").format(ic.tag))
                        continue
                    d = _parse_direction(ic)
                    v = _parse_value(ic, "value", "velocity", 0.0)
                    if d is None or isinstance(v, list):
                        log(tr("ERROR: Beginsnelheid op '{0}' zonder "
                               "richting of met tijdshistorie; "
                               "overgeslagen.",
                               "ERROR: Initial velocity on '{0}' without "
                               "direction or with a time history; "
                               "skipped.").format(sel))
                        continue
                    target = _selection_kind(root, sel)
                    model_data["initial_velocities"].append(
                        (sel, target, tuple(v * c for c in d)))
                    log("INFO: Initial velocity on '{0}': {1}".format(
                        sel, model_data["initial_velocities"][-1][2]))

            elif thermal_run and (tag in bridge_thermal.THERMAL_TAGS or
                                  tag in SUPPORTED_BCS or
                                  tag in _MODEL_ITEM_TAGS) and not (
                    thermo_mech and (tag in SUPPORTED_BCS or
                                     tag == "thermalstress")):
                # Thermal loads: bridge_thermal.parse_thermal()
                # below. Mechanical loads play no role in a
                # thermal analysis (Mecway manual v33 chapter
                # 9: analysis types per load), except in the
                # thermal -> mechanical chain (thermo_mech, above): then
                # they go on to 2d / _parse_model_item.
                if (tag in bridge_thermal.THERMAL_TAGS or
                        item.get("suppressed", "") == "true"):
                    continue
                if thermo_mech and tag in _CHAIN_DROPPED_TAGS:
                    # In the chain the mechanical solve runs on the mesh
                    # and modelisations of the thermal part (shells
                    # as PLAN, no beams; bridge_thermal): element
                    # offset (own nodes/EXCENTREMENT), flexible joints
                    # (own node) and constraint equations are not
                    # translated there.
                    model_data["skipped_loads"].append(
                        tr("{0} op '{1}' (keten thermisch -> mechanisch)",
                           "{0} on '{1}' (thermal -> mechanical chain)")
                        .format(tag, item.get("selection", "")))
                    log(tr("WARNING: {0} op '{1}' wordt in de keten "
                           "thermisch -> mechanisch (Thermal stress in een "
                           "T31-model) niet vertaald; de mechanische "
                           "berekening rekent zonder.",
                           "WARNING: {0} on '{1}' is not translated in the "
                           "thermal -> mechanical chain (Thermal stress in "
                           "a T31 model); the mechanical solve runs "
                           "without it.").format(
                               tag, item.get("selection", "")))
                elif thermo_mech:
                    log("INFO: '{0}' on '{1}' is ignored in the "
                        "thermal -> mechanical chain (quasi-static, "
                        "temperature from the thermal part).".format(
                            tag, item.get("selection", "")))
                else:
                    log("INFO: Mechanical load '{0}' on '{1}' is "
                        "ignored in the thermal analysis (only with a "
                        "Thermal stress in a T31 model: thermal -> "
                        "mechanical chain, docs/Lassen.md par. 9).".format(
                            tag, item.get("selection", "")))
                continue
            elif not thermal_run and tag == "temperature3":
                # Node temperature in a mechanical analysis: thermal
                # strain per node.
                if item.get("suppressed", "") == "true":
                    log("INFO: temperature3 skipped (suppressed).")
                    continue
                _parse_node_temperatures(item, model_data)
            elif (not thermal_run and tag in bridge_thermal.THERMAL_TAGS
                  and tag not in _MODEL_ITEM_TAGS):
                # Thermal loads (convection, heat flux, ...)
                # play no role in a mechanical analysis (Mecway manual
                # v33 chapter 9: analysis types per load); not an
                # error, like mechanical loads in a thermal
                # analysis above. temperature2 is also mechanical
                # (thermal strain, _parse_model_item).
                if item.get("suppressed", "") != "true":
                    log("INFO: Thermal load '{0}' on '{1}' is ignored "
                        "in a mechanical analysis.".format(
                            tag, item.get("selection", "")))
                continue
            elif tag in _MODEL_ITEM_TAGS:
                if item.get("suppressed", "") == "true":
                    log("INFO: {0} skipped (suppressed).".format(tag))
                    continue
                _parse_model_item(item, root, model_data)

            # --------------------------------------------------
            # 2d. BOUNDARY CONDITIONS
            # _has_rot_dofs is TEMPORARILY False; the value for the whole
            # model is written back into all BC params in STEP 4
            # (bridge_mesh.py can still set it to True later for
            # DIS_TR nodes).
            # --------------------------------------------------
            elif tag in SUPPORTED_BCS:
                if item.get("suppressed", "") == "true":
                    log("INFO: {0} on '{1}' skipped (suppressed).".format(
                        tag, item.get("selection", "")))
                    continue

                selection_name = item.get("selection", "")
                bc_handler     = SUPPORTED_BCS[tag]

                # For BCs without a selection attribute (gravity is global),
                # selection_name stays empty; aster_target becomes GROUP_MA
                # and is not rendered as GROUP_MA="..." by bridge_to_aster.py.
                aster_target = _selection_kind(root, selection_name)

                if aster_target not in bc_handler.valid_targets:
                    log(tr("ERROR: BC '{0}' op '{1}' ({2}) is ONGELDIG. "
                           "Toegestaan: {3}. BC wordt overgeslagen.",
                           "ERROR: BC '{0}' on '{1}' ({2}) is INVALID. "
                           "Allowed: {3}. BC is skipped.").format(
                            tag, selection_name, aster_target,
                            bc_handler.valid_targets))
                    model_data["skipped_loads"].append(
                        tr("{0} op '{1}'", "{0} on '{1}'").format(
                            tag, selection_name))
                    continue

                params = bc_handler.parse_xml(item, root)
                if not _check_bc_params(tag, item, params, selection_name,
                                        model_data):
                    continue
                if not _check_position_formulas(tag, params, selection_name,
                                                run_cfg, model_data):
                    continue
                if tag == "gravity" and solver_cmd == "COMB_SISM_MODAL":
                    # Response spectrum (bridge_spectrum.py): the gravity is
                    # not a load but the spectral acceleration per direction
                    # (table: period or frequency -> acceleration).
                    model_data.setdefault("spectrum_gravity", []).append(
                        params)
                    continue

                # Gravity with magnitude 0: no point in emitting PESANTEUR.
                # With a time history: zero over the whole history.
                if tag == "gravity":
                    if params.get("_history"):
                        zero = all(abs(tv[1]) < 1e-12 for v in
                                   params["_history"].values()
                                   for tv in (v if isinstance(v, list)
                                              else [(0.0, v)]))
                    else:
                        zero = all(abs(params.get(c, 0.0)) < 1e-12
                                   for c in ('x', 'y', 'z'))
                    if zero:
                        log("INFO: Gravity with magnitude 0 -> skipped.")
                        continue
                    if not _check_gravity_history(params, model_data):
                        continue

                params["_has_rot_dofs"] = False   # temporary; see STEP 4

                if tag == "force" and aster_target == "GROUP_NO":
                    nodes_in_group = model_data["node_groups"].get(
                        selection_name, [])
                    num_nodes = len(nodes_in_group)
                    if num_nodes > 1:
                        # Distribute force over nodes. For a time history
                        # (list of (t, F) tuples) each F is divided.
                        new_params = {}
                        for ax, v in params.items():
                            if ax.startswith("_"):
                                new_params[ax] = v
                            elif isinstance(v, list):
                                new_params[ax] = [
                                    (t, val / float(num_nodes))
                                    for t, val in v
                                ]
                            else:
                                new_params[ax] = v / float(num_nodes)
                        params = new_params
                        log("INFO: Force on '{0}' distributed over {1} "
                            "nodes.".format(selection_name, num_nodes))
                    elif num_nodes == 1:
                        log("INFO: Force on '{0}' on 1 node.".format(
                            selection_name))
                    else:
                        log(tr("WARNING: Groep '{0}' heeft 0 knopen.",
                               "WARNING: Group '{0}' has 0 nodes.").format(
                            selection_name))

                aster_dict = bc_handler.to_aster_dict(params)
                if tag == "force" and aster_target == "GROUP_MA":
                    # Total force; bridge_mesh.py divides by the
                    # area (FORCE_FACE is force per area).
                    log("INFO: Force on faces '{0}': becomes FORCE_FACE "
                        "(total / area).".format(selection_name))
                model_data["bcs"].append({
                    "type":          tag,
                    "selection":     selection_name,
                    "params":        params,
                    "aster_target":  aster_target,
                    "aster_keyword": bc_handler.keyword(params),
                    "aster_dict":    aster_dict,
                })

            # --------------------------------------------------
            # 2d-bis. CYCLIC SYMMETRY (modal: bridge_cyclic.py)
            # --------------------------------------------------
            elif tag == bridge_cyclic.TAG:
                bridge_cyclic.parse(item, model_data, run_cfg)

            # --------------------------------------------------
            # 2d-ter. CCX CUSTOM ELEMENT TYPE
            # Mecway's CCX > custom element type, e.g.
            #   <elementtype selection="" shape="hex8" type="C3D8R" />
            # (selection "" = all elements of that shape; GitHub issue #5).
            # A CalculiX setting, not a load: Code-Aster takes the element
            # formulation from the Elements page. Measured on a bonded rubber
            # block (issue #5, Code-Aster 17.4 vs CCX 2.23): '3D' gives the
            # same force as C3D8 and 'LINE_QUAD' the same as C3D20, within
            # 0.1 N; C3D8R and C3D8I have no equal in Code-Aster.
            # --------------------------------------------------
            elif tag == "elementtype":
                if item.get("suppressed", "") == "true":
                    continue
                shape = item.get("shape", "")
                where = (u"'{0}'".format(item.get("selection"))
                         if item.get("selection") else
                         tr("alle elementen", "all elements"))
                log(tr(u"WARNING: Aangepast CCX-elementtype {0} voor {1} "
                       u"({2}) geldt alleen voor CalculiX en wordt niet "
                       u"vertaald. Code-Aster rekent met de pagina Elementen "
                       u"(hex8: {3}). Vergelijkbaar met CCX: hex8 '3D' = "
                       u"C3D8, 'LINE_QUAD' = C3D20; C3D8R en C3D8I hebben "
                       u"geen gelijke in Code-Aster.",
                       u"WARNING: Custom CCX element type {0} for {1} ({2}) "
                       u"only applies to CalculiX and is not translated. "
                       u"Code-Aster uses the Elements page (hex8: {3}). "
                       u"Comparable with CCX: hex8 '3D' = C3D8, 'LINE_QUAD' "
                       u"= C3D20; C3D8R and C3D8I have no equal in "
                       u"Code-Aster.").format(
                           item.get("type", "?"), shape, where, hex8_mod))

            # --------------------------------------------------
            # 2d-quater. RESULT FORMULAS (Solution > Formula, S33)
            #   <formula name="Fq" displayunit="" fieldscalar="formula">
            #     <unit exponents="+0+1-3">W/m²</unit>
            #     <formula>qf.x</formula></formula>
            # Mecway evaluates a formula during its own solve and stores
            # the values as nodevariable <fieldscalar> ("formula",
            # "formula(2)", ...; seen headless in Mecway 34). The bridge
            # does the same in the job (aster_results_export._formula_vars)
            # with the plan of bridge_formula.plan; a formula it cannot
            # evaluate (a symbol of a field the bridge does not write, a
            # syntax error) keeps no values and is invalid (red) in Mecway:
            # WARNING with the workaround (create it again after loading,
            # Mecway then computes it from the results; checked in the
            # Mecway 34 GUI, GitHub issue #8).
            # --------------------------------------------------
            elif tag == "formula" and item.find("formula") is not None:
                _plan_result_formula(item, model_data)

            # --------------------------------------------------
            # 2e. UNKNOWN LOADS / BOUNDARY CONDITIONS
            # Mecway knows many more types (manual v33 chapter 9: moment,
            # traction, frictionless, symmetry, contact, ...). Anything with a
            # selection that is not handled above is not
            # translated; that must not happen silently.
            # --------------------------------------------------
            elif (item.get("selection") is not None or
                  item.get("selectionsurface") is not None or
                  item.get("selectionmaster") is not None):
                if item.get("suppressed", "") == "true":
                    continue
                model_data["skipped_loads"].append(
                    tr("{0} op '{1}'", "{0} on '{1}'").format(
                        tag, item.get("selection",
                                      item.get("selectionsurface", ""))))
                log(tr("ERROR: Belasting/randvoorwaarde '{0}' op '{1}' wordt "
                       "niet ondersteund en is NIET meegenomen.",
                       "ERROR: Load/boundary condition '{0}' on '{1}' is "
                       "not supported and is NOT included.").format(
                        tag, item.get("selection", "")))

        # ==========================================
        # STEP 2b: THERMAL (materials, loads, initial conditions)
        # ==========================================
        if thermal_run:
            bridge_thermal.parse_thermal(root, model_data)

        # ==========================================
        # STEP 2c: ACOUSTICS (speed of sound, pressure nodes)
        # ==========================================
        if acoustic_run:
            bridge_acoustic.parse_acoustic(root, model_data)
        elif not thermal_run:
            # Vibro-acoustics: fluid parts (material with
            # speed of sound without E, or LUCHT_/FLUID_), OPEN_, KOPPEL_.
            bridge_vibroacoustic.parse_vibro(root, model_data, run_cfg)

        # ==========================================
        # STEP 3: DETERMINE SECTION PROPERTIES PER ELSET
        # ==========================================
        spring_mat_names = set(model_data["spring_materials"].keys())

        for elset_name, mat_name in model_data["elsets"].items():
            dim = model_data["elset_dims"].get(elset_name, "3D")

            # --- Spring elements -> DIS_T ---
            if mat_name in spring_mat_names:
                if dim == "1D":
                    k = model_data["spring_materials"][mat_name]
                    model_data["spring_sections"][elset_name] = {
                        "spring_constant": k}
                    model_data["elset_modelisations"][elset_name] = "DIS_T"
                    log("INFO: Spring '{0}': k={1} N/m -> DIS_T".format(
                        elset_name, k))
                else:
                    _drop_elset(
                        model_data, elset_name,
                        tr("veer-materiaal op elset '{0}' (dim={1})",
                           "spring material on elset '{0}' (dim={1})")
                        .format(elset_name, dim),
                        tr("een veer alleen op 1D-elementen;",
                           "a spring only on 1D elements;"))
                continue

            # --- Gap / damper -> DIS_T op SEG2 ---
            if mat_name in model_data["line_discretes"]:
                if dim == "1D":
                    model_data["discrete_sections"][elset_name] = dict(
                        model_data["line_discretes"][mat_name])
                    model_data["elset_modelisations"][elset_name] = "DIS_T"
                else:
                    _drop_elset(model_data, elset_name,
                                "elset '{0}'".format(elset_name),
                                tr("Gap/Damper alleen op line2;",
                                   "Gap/Damper only on line2;"))
                continue

            # --- Tension only -> CABLE ---
            props = model_data["materials"].get(mat_name, {})
            if props.get("tension_only"):
                geom = model_data["mat_geometrics"].get(mat_name, {})
                area = _section_area(geom)
                if dim != "1D" or not area:
                    _drop_elset(model_data, elset_name,
                                "tension-only elset '{0}'".format(elset_name),
                                tr("alleen line2 met een doorsnede;",
                                   "only line2 with a cross-section;"))
                    model_data["elset_modelisations"].pop(elset_name, None)
                    continue
                model_data["cable_sections"][elset_name] = {
                    "area": area, "E": props.get("E")}
                model_data["elset_modelisations"][elset_name] = "CABLE"
                log("INFO: Tension-only elset '{0}' -> CABLE, A={1} m2."
                    .format(elset_name, area))
                continue

            # --- Truss -> BARRE (_split_trusses) ---
            # Only the cross-section area counts (axial force E A and
            # mass rho A); Code-Aster: AFFE_CARA_ELEM BARRE=_F(GROUP_MA,
            # SECTION='GENERALE', CARA='A', VALE=A) (catalogue
            # affe_cara_elem.py; test cases ssnl105a, sdnl138a). In
            # beam_sections with "truss": True, so that bridge_mesh takes the
            # name along when renaming.
            if model_data["elset_modelisations"].get(elset_name) == "BARRE":
                geom = model_data["mat_geometrics"].get(mat_name, {})
                area = _section_area(geom)
                if dim != "1D" or not area:
                    _drop_elset(model_data, elset_name,
                                "truss elset '{0}'".format(elset_name),
                                tr("een truss heeft een materiaal met "
                                   "een doorsnede nodig;",
                                   "a truss needs a material with a "
                                   "cross-section;"))
                    model_data["elset_modelisations"].pop(elset_name, None)
                    continue
                model_data["beam_sections"][elset_name] = {
                    "geom_type": geom.get("geom_type"),
                    "aster_section": "GENERALE", "cara": ("A",),
                    "vale": (area,), "area": area, "truss": True}
                log("INFO: Truss elset '{0}' -> BARRE, A={1} m2.".format(
                    elset_name, area))
                continue

            # --- Regular beam / shell / 3D ---
            geom = model_data["mat_geometrics"].get(mat_name)
            if geom is None:
                continue

            if dim == "1D":
                if "aster_section" in geom:
                    mod = model_data["elset_modelisations"].get(elset_name)
                    if mod in _SHEAR_BEAMS:
                        geom = _add_shear_coefs(elset_name, geom, mod)
                    geom = dict(geom, area=_section_area(geom))
                    model_data["beam_sections"][elset_name] = geom
                    log("INFO: Beam section '{0}': {1}".format(
                        elset_name, geom["aster_section"]))
                else:
                    log(tr("WARNING: Elset '{0}' is 1D maar '{1}' heeft geen "
                           "balk-sectie.",
                           "WARNING: Elset '{0}' is 1D but '{1}' has no "
                           "beam section.").format(
                               elset_name, geom.get("geom_type", "?")))
            elif dim == "2D":
                if "thickness" in geom:
                    model_data["shell_sections"][elset_name] = geom
                    log("INFO: Plate thickness '{0}': {1} m".format(
                        elset_name, geom["thickness"]))
                else:
                    log(tr("WARNING: Elset '{0}' is 2D maar '{1}' heeft geen "
                           "dikte.",
                           "WARNING: Elset '{0}' is 2D but '{1}' has no "
                           "thickness.").format(
                               elset_name, geom.get("geom_type", "?")))

        # line3 only as beam, truss or cable: bridge_mesh splits them into
        # two SEG2 cells (POU_D_E/POU_D_T and BARRE exist only on SEG2;
        # MODELISATION='BARRE' on SEG3 gave MODELE1_6, Code-Aster 17.4,
        # GitHub issue #6) and couples the midside node of a bar
        # (bridge_mesh._line3_truss_links). Spring, gap and damper are only
        # on line2 in Mecway (manual v33 par. 7.6-7.10); two springs in
        # series would give half the stiffness, so report.
        if not thermal_run:
            for elset_name, mod in sorted(
                    model_data["elset_modelisations"].items()):
                if ("line3" in elset_shapes_map.get(elset_name, ()) and
                        model_data["elset_dims"].get(elset_name) == "1D" and
                        mod not in ("POU_D_E", "POU_D_T", GD_BEAM,
                                    "BARRE", "CABLE")):
                    _drop_elset(
                        model_data, elset_name,
                        tr("elset '{0}': line3-elementen ({1})",
                           "elset '{0}': line3 elements ({1})").format(
                               elset_name, mod),
                        tr("alleen line3-balken en -truss worden vertaald; "
                           "veer, gap en demper alleen op line2 (zoals "
                           "Mecway);",
                           "only line3 beams and trusses are translated; "
                           "spring, gap and damper only on line2 (as in "
                           "Mecway);"))

        # BARRE is geometrically linear in Code-Aster 17.4: a bar that
        # rotates rigidly by 30 degrees gave with DEFORMATION='GROT_GDEP'
        # the same axial force as with 'PETIT' (-2.68e6 N, run), no message,
        # and a tensioned bar has no transverse stiffness (singular
        # matrix for Samples/SaggingCable.liml). Like beams (POU_D_E)
        # therefore small displacements; report for large ones.
        bars = sorted(e for e, m in model_data["elset_modelisations"].items()
                      if m == "BARRE")
        if bars and solver_cmd in ("STAT_NON_LINE", "DYNA_NON_LINE") and \
                run_cfg.get("deformation", "PETIT") not in (
                    "PETIT", "PETIT_REAC"):
            log(tr("WARNING: Truss-elementen ({0}) worden staven (BARRE); "
                   "die zijn in Code-Aster geometrisch lineair (geen grote "
                   "verplaatsingen, geen stijfheid uit trekkracht). Een "
                   "kabel die alleen door voorspanning dwarsstijfheid "
                   "krijgt (zoals Samples/SaggingCable.liml) rekent zo "
                   "niet.",
                   "WARNING: Truss elements ({0}) become bars (BARRE); "
                   "these are geometrically linear in Code-Aster (no large "
                   "displacements, no stiffness from tension). A cable "
                   "that only gets lateral stiffness from pretension (like "
                   "Samples/SaggingCable.liml) cannot be computed this "
                   "way.").format(", ".join(bars)))

        # Elsets with a VOID material (OpenRadioss) not in the model
        for elset_name, mat_name in list(model_data["elsets"].items()):
            if mat_name in model_data["void_materials"]:
                for key in ("elset_dims", "elset_modelisations",
                            "beam_sections", "shell_sections"):
                    model_data[key].pop(elset_name, None)
                model_data["skipped_loads"].append(
                    tr("elset '{0}' (materiaal '{1}' met law VOID)",
                       "elset '{0}' (material '{1}' with law VOID)").format(
                        elset_name, mat_name))
                log(tr("ERROR: Elset '{0}' heeft VOID-materiaal '{1}' en "
                       "wordt weggelaten uit het model.",
                       "ERROR: Elset '{0}' has VOID material '{1}' and is "
                       "left out of the model.").format(elset_name, mat_name))

        # 2D analysis (S20/SA0): plane modelisations (bridge_plane, S16a)
        if not bridge_plane.apply(model_data, run_cfg, elset_shapes_map):
            return None

        # ==========================================
        # STEP 4: has_rot_dofs FOR THE MODEL + BC RECALCULATION
        # ==========================================
        # Element orientation cards (Loads & Constraints) on the
        # elements of their selection, like the per-element attributes
        bridge_orientation.apply(model_data)
        model_data["has_rot_dofs"] = any(
            mod in _ROT_DOF_MODELISATIONS
            for mod in model_data["elset_modelisations"].values()
        )
        log("INFO: Final has_rot_dofs = {0}".format(
            model_data["has_rot_dofs"]))

        # Velocity: displacement up to the end time of the analysis
        t_end = model_data["timesteps"].get("period", 1.0)
        for bc in model_data["bcs"]:
            if bc["type"] == "velocity":
                bc["params"]["_t_end"] = t_end

        # Recompute aster_dict for all BCs with the final flag
        for bc in model_data["bcs"]:
            bc["params"]["_has_rot_dofs"] = model_data["has_rot_dofs"]
            bc["aster_dict"] = SUPPORTED_BCS[bc["type"]].to_aster_dict(
                bc["params"])
            if not bc["aster_dict"] and bc["type"] not in (
                    "elasticsupport", "compressiononly", "symmetry"):
                log(tr("WARNING: {0} op '{1}' heeft geen richting of "
                       "waarde; overgeslagen.",
                       "WARNING: {0} on '{1}' has no direction or value; "
                       "skipped.").format(bc["type"], bc["selection"]))

    except Exception as e:
        # Do not continue with half a model: everything after the error
        # (materials, BCs, ...) would be silently missing.
        log(tr("ERROR: Fout bij parsen XML van '{0}': {1}: {2}. De .liml "
               "kan niet worden vertaald.",
               "ERROR: Error while parsing XML of '{0}': {1}: {2}. The "
               ".liml cannot be translated.").format(
            file_path, type(e).__name__, str(e)))
        return None

    dropped = model_data.get("_dropped_elsets")
    if dropped:
        log(tr("ERROR: Elset(s) {0} kunnen niet naar Code-Aster vertaald "
               "worden (zie de ERROR-regels hierboven); zonder deze "
               "elementen zou de berekening fout of onvolledig zijn. De "
               "bridge stopt voor Code-Aster. Pas het model aan.",
               "ERROR: Elset(s) {0} cannot be translated to Code-Aster "
               "(see the ERROR lines above); without these elements the "
               "analysis would be wrong or incomplete. The bridge stops "
               "before Code-Aster. Adapt the model.").format(
                   ", ".join("'{0}'".format(e) for e in dropped)))
        return None

    return model_data
