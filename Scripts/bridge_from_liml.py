# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_from_liml.py
# Leest het actieve Mecway .liml-bestand (XML-formaat) en extraheert alle
# benodigde data voor Code-Aster.
#
# Ondersteunde Mecway <geometric>-typen:
#   CircularBar           -> CERCLE (massief)
#   UniformCircularTube   -> CERCLE (hol: roundod, roundid)
#   RectBar               -> RECTANGLE (massief: recta, rectb)
#   RectTube              -> RECTANGLE (hol: recta, rectb, rectthickness)
#   UniformGeneralSection -> GENERALE (opgegeven A, iyy, izz, torsionconstant)
#   I, T, L, C            -> GENERALE (A, IY, IZ, JX berekend zoals Mecway,
#                            zie _profile_props)
#   Plate                 -> COQUE (thickness)
#
# Ondersteunde <mechanical>-typen:
#   Isotropic -> DEFI_MATERIAU ELAS (E, NU, RHO)
#   Spring    -> AFFE_CARA_ELEM DISCRET K_T_D_L (springconstant)
#   Damper    -> DIS_T met A_T_D_L (dampingcoefficient)
#   Gap       -> DIS_T met RELATION='DIS_CHOC' (closedstiffness)
#   TensionOnly -> MODELISATION='CABLE' (youngsmodulus + doorsnede)
# Truss-elementen (<elem ... truss="true">) -> MODELISATION='BARRE' met het
#   doorsnede-oppervlak (_split_trusses).
# Configuraties en groepen: onderdrukte items vallen weg
#   (_apply_suppression).
#
# Mechanische modelitems zonder selectie-BC (_parse_model_item):
#   thermalstress + temperature2 (+ temperature3 per knoop,
#   _parse_node_temperatures), rayleighdamping, constraintequation,
#   mass2, rotationalinertia; verlijmd contact2 -> model_data["bonded"].
#
# Ondersteunde <nodesurfacecoupling>-typen:
#   rbe3      -> LIAISON_RBE3 (gewogen gemiddelde, master volgt slaves)
#   rigidbody -> LIAISON_SOLIDE (master en slaves vormen samen 1 starre body)
#
# Compatibel met IronPython 2.7.9.

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

# ------------------------------------------------------------------
# CONSTANTEN: elementvormen per dimensie
# ------------------------------------------------------------------
_DIM_1D_SHAPES = frozenset({"line2", "line3"})
_DIM_2D_SHAPES = frozenset({"tri3", "tri6", "quad4", "quad8"})
_DIM_3D_SHAPES = frozenset({
    "hex8", "hex20", "tet4", "tet10",
    "pyr5", "pyr13", "wedge6", "wedge15",
})

# MODELISATION-waarden die rotatie-DOFs (DRX/DRY/DRZ) introduceren.
# DIS_T (veer) en BARRE hebben uitsluitend translatie-DOFs en staan hier
# NIET in.
_ROT_DOF_MODELISATIONS = frozenset({
    "POU_D_T", "POU_D_E",
    "COQUE_3D", "DKT", "DST", "Q4G",
    "DIS_TR",
})

# Keuzes voor de elementformulering (CONFIG_BRIDGE "elem_*"): toegestane
# waarden, de eerste is de standaard.
_ELEM_CHOICES = {
    "elem_hex8":  ("3D", "3D_SI", "LINE_QUAD"),
    "elem_shell": ("DKT", "DST", "COQUE_3D"),
    "elem_beam":  ("POU_D_E", "POU_D_T"),
}


def _parse_bilinear(plastic_node, mat_name, plastic_type, E=None):
    """
    Bilineaire versteviging -> {"sy", "et", "h", "kinematic"} (SI) of None.
    Code-Aster: ECRO_LINE SY / D_SIGM_EPSI (helling van de trekkromme na
    de vloeigrens in TOTALE rek; U4.43.01 ECRO_LINE) met VMIS_ISOT_LINE of
    VMIS_CINE_LINE. Mecway's "tangent modulus" is de plastische modulus H
    (spanning tegen plastische rek): headless gemeten met Mecway/CCX (de
    interne solver rekent geen plasticiteit), staaf 1% rek, H = 100 GPa:
    CCX 915,8 MPa, als H gelezen 914,5 MPa, als helling in totale rek
    1181 MPa (verificatie NL-01). Daarom D_SIGM_EPSI = E H / (E + H),
    zoals _kinematic_curve.
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
    log("INFO: Materiaal '{0}': bilineaire {1} versteviging, SY={2} Pa, "
        "H={3} Pa (Mecway tangent modulus) -> D_SIGM_EPSI={4} Pa "
        "({5}).".format(
            mat_name, "kinematische" if kinematic else "isotrope", sy, h, et,
            "VMIS_CINE_LINE" if kinematic else "VMIS_ISOT_LINE"))
    return {"sy": sy, "et": et, "h": h, "kinematic": kinematic}


def _kinematic_curve(curve, E, mat_name, definition):
    """
    Kinematische hardingscurve (Mecway "Plastic with kinematic hardening",
    manual v33 par. 8.8) -> {"sy", "et", "kinematic": True} of None.
    Code-Aster heeft voor von Mises geen kinematische versteviging met een
    willekeurige curve: VMIS_CINE_LINE (en VMIS_ECMI_*) is lineair
    kinematisch (Prager), VMIS_CIN1/2_CHAB is een andere (Chaboche-)wet.
    Is de versteviging na de vloeigrens lineair (een segment, of alle
    segmenten met dezelfde helling H in plastische rek), dan is de curve
    gelijk aan BilinearKinematic en wordt hij VMIS_CINE_LINE met
    D_SIGM_EPSI = E H / (E + H) (helling in totale rek, zoals
    _parse_bilinear). Anders None (gemeld; het materiaal blijft elastisch).
    definition: 'auto', 'plastic' of 'total' (CONFIG
    plastic_strain_definition, zoals _to_aster_traction_curve).
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
    log("INFO: Materiaal '{0}': kinematische curve is lineair (SY={1} Pa, "
        "H={2} Pa) -> VMIS_CINE_LINE, D_SIGM_EPSI={3} Pa.".format(
            mat_name, sy, h, et))
    return {"sy": sy, "et": et, "kinematic": True}


def _ramberg_osgood_curve(plastic_node, E, mat_name, n_points=25):
    """
    Ramberg-Osgood -> hardingscurve [(plastische rek, spanning)] of [].
    CCX (*DEFORMATION PLASTICITY): eps = sig/E + alpha*(sig/E)*(sig/sig0)^(n-1).
    Code-Aster heeft geen Ramberg-Osgood bij von Mises-plasticiteit; de
    curve gaat als TRACTION naar VMIS_ISOT_TRAC (incrementele plasticiteit:
    gelijk bij monotone belasting, anders bij ontlasten). Begin bij de
    spanning waar de plastische rek 1% van de elastische is, tot 3*sig0.
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
    """MODELISATION-keuze uit CONFIG_BRIDGE[key]; onbekend -> standaard."""
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


def _positive_int(text, default=1):
    """Geheel getal >= 1 uit een attribuut, anders default."""
    try:
        return max(1, int(text))
    except (TypeError, ValueError):
        return default


def _run_analysis_cfg(mecway_type, mode_superposition=False):
    """
    CONFIG_BRIDGE-dict van de analyse die deze run gebruikt; bij "auto" via
    het Mecway-analysetype (zoals main() hem omzet). {} als onbekend.
    """
    name = CONFIG_BRIDGE.get("active_analysis")
    if name == "auto":
        name = resolve_auto_analysis(mecway_type, mode_superposition)
    return CONFIG_BRIDGE["analyses"].get(name, {}) if name else {}


# ==========================================
# HULPFUNCTIE: GENERALE-SECTIE DICT
# ==========================================
def _parse_beam_orientation(elem):
    """
    Orientatie van een balkelement uit de <elem>-attributen, of None.

    Mecway (manual v33 par. 7.5 en de .liml van het testmodel):
    orientationvx/vy/vz = richting van de V-as (ontbrekend = 0), angle =
    extra rotatie van V om U. Zonder vector negeert Mecway angle (gezien
    in een vergelijking Mecway <-> Code-Aster), dus dan None.
    """
    keys = ("orientationvx", "orientationvy", "orientationvz")
    if not any(elem.get(k) is not None for k in keys):
        if elem.get("angle") is not None:
            log("INFO: Balkelement {0}: angle zonder orientatievector; "
                "Mecway negeert die, de bridge ook.".format(elem.get("eid")))
        return None
    vec = tuple(float(elem.get(k, "0")) for k in keys)
    angle = parse_and_convert(elem.get("angle", "0"), 'angle')
    return {"vec": vec, "angle": angle}


def _parse_failure(fail_node, mat_name, model_data):
    """
    Mecway's faalcriterium van een materiaal (Failure criteria, manual v34
    par. 8.7): <failure type="VonMises" tensilestrength="250 MPa" />
    (attribuutnaam gezien in een .liml die Mecway 34 zelf schreef met
    mw.set_material_property). Alleen von Mises wordt gebruikt: de factor
    of safety = tensilestrength / von Mises (resultaatveld safety_factor,
    aster_results_export._fos_vars). Andere criteria (Tsai-Wu, ...):
    WARNING. Resultaat in model_data["failure_strengths"] {mat: Pa}.
    """
    if fail_node is None:
        return
    kind = fail_node.get("type", "None")
    if kind in ("None", ""):
        return
    if kind == "VonMises":
        strength = parse_and_convert(fail_node.get("tensilestrength", "0"),
                                     'pressure')
        # parse_and_convert geeft een float (onbekende eenheid: het getal
        # ongewijzigd, met een WARNING); defensief, want een tekst in
        # failure_strengths zou de hele resultaatexport laten vallen
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
            log("INFO: Faalcriterium von Mises voor materiaal '{0}': "
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
    Retourneer een GENERALE-sectie dict voor Code-Aster POUTRE.

    Parameters (allen in SI-eenheden)
    ----------
    A   : float  doorsnede-oppervlak (m^2)
    IY  : float  traagheidsmoment om lokale y-as (m^4)
    IZ  : float  traagheidsmoment om lokale z-as (m^4)
    JX  : float  torsieconstante (m^4)
    """
    log("INFO: GENERALE sectie -> A={0} m2, IY={1} m4, "
        "IZ={2} m4, JX={3} m4".format(A, IY, IZ, JX))
    return {
        "aster_section": "GENERALE",
        "cara":          ("A", "IY", "IZ", "JX"),
        "vale":          (A, IY, IZ, JX),
    }


# ==========================================
# HULPFUNCTIES: PROFIELEIGENSCHAPPEN ZOALS MECWAY
# ==========================================
# Assen: V en W zijn de doorsnede-assen van Mecway (Mecway-manual v33,
# par. 7.5). In de tekening van het materiaalvenster loopt V verticaal
# (langs de hoogte van I/T/C en het been b van L), W horizontaal. Code-Aster
# lokale y = V, z = W (zelfde standaardorientatie, nagelopen met een
# vergelijking Mecway <-> Code-Aster), dus IY = I om V en IZ = I om W.
# Dat klopt ook met RECTANGLE (HY = recta langs V) en met de algemene
# doorsnede (iyy -> IY).
#
# Nagerekend tegen de waarden die Mecway 33 toont (a/b/c/d in mm):
#   I 100/50/10/8  : A 1640, I_V 211746.67, I_W 2374666.67, J 47132.76
#   T 50/5/9/30    : A 600, I_V 94062.5, I_W 57065.625, J 12692.74
#   C 80/150/6/5   : A 1650, I_V 1077982.95, I_W 6074550, J 16803.72
#   L 80/100/5     : A 875, I_V 260746.17, I_W 1159863.95, J 7177.22,
#                    theta 32.4554619917313 graden

def _roark_k1(a, b):
    """Torsieconstante van een rechthoek a x b, beide uiteinden vrij
    (Roark, Formulas for Stress and Strain, tabel 10.7)."""
    a, b = max(a, b), min(a, b)
    if a <= 0.0:
        return 0.0
    return a * b**3 * (1.0 / 3.0 - 0.21 * (b / a) *
                       (1.0 - b**4 / (12.0 * a**4)))


def _roark_k2(c, d):
    """Torsieconstante van een strook c (lengte) x d (dikte) met een vrij
    uiteinde; het andere zit vast aan de rest van het profiel (Roark)."""
    if c <= 0.0:
        return 0.0
    return c * d**3 * (1.0 / 3.0 - 0.105 * (d / c) *
                       (1.0 - d**4 / (192.0 * c**4)))


def _rects_inertia(rects):
    """
    A, I om de horizontale zwaartepuntsas (W), I om de verticale (V) en
    het productmoment, voor een doorsnede uit rechthoeken
    (x0, x1, y0, y1); x horizontaal, y verticaal.
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
    (A, IY, IZ, JX) van een I-, T-, C- of L-profiel, in de eenheid van de
    maten (SI als de maten in m zijn). IY = I om V, IZ = I om W.
    """
    if kind == "I":
        # a hoogte, b flensbreedte, c flensdikte, d lijfdikte
        A, i_w, i_v, _ = _rects_inertia([
            (0.0, b, 0.0, c), (0.0, b, a - c, a),
            ((b - d) / 2.0, (b + d) / 2.0, c, a - c)])
        D = (c * c + d * d / 4.0) / c
        alpha = 0.15 * min(c, d) / max(c, d)
        J = 2.0 * _roark_k1(b, c) + (a - 2.0 * c) * d**3 / 3.0 + \
            2.0 * alpha * D**4
        return A, i_v, i_w, J
    if kind == "T":
        # a flensbreedte, b lijfdikte, c flensdikte, d lijfhoogte
        A, i_w, i_v, _ = _rects_inertia([
            (0.0, a, d, d + c), ((a - b) / 2.0, (a + b) / 2.0, 0.0, d)])
        D = (c * c + b * b / 4.0) / c
        alpha = 0.15 * min(b, c) / max(b, c)
        J = _roark_k1(a, c) + _roark_k2(d, b) + alpha * D**4
        return A, i_v, i_w, J
    if kind == "C":
        # a flensbreedte (incl. lijf), b hoogte, c flensdikte, d lijfdikte
        A, i_w, i_v, _ = _rects_inertia([
            (0.0, a, 0.0, c), (0.0, a, b - c, b), (0.0, d, c, b - c)])
        D = 2.0 * ((c + d) - math.sqrt(2.0 * c * d))
        alpha = 0.07 * min(c, d) / max(c, d)
        J = 2.0 * _roark_k1(a, c) + _roark_k1(b - 2.0 * c, d) + \
            2.0 * alpha * D**4
        return A, i_v, i_w, J
    if kind == "L":
        # a horizontaal been, b verticaal been, c dikte. Mecway gebruikt de
        # hoofdassen: V staat onder theta met het been b, van been a af
        # gedraaid (theta zoals Mecway hem toont).
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
    (AY, AZ) voor POU_D_T: afschuifcoefficienten A / A_afschuif in de
    richting V (lokaal y) en W (lokaal z), de conventie van AFFE_CARA_ELEM
    (AY = 1.2 voor een rechthoek, testcase sdll10a).

    Benadering met dunwandige plaatdelen, NIET geverifieerd tegen Mecway of
    Code-Aster: het afschuifoppervlak in een richting is de som van de
    plaatdelen evenwijdig aan die richting; een lijf tussen twee flenzen
    (I, C) telt volledig mee (vrijwel gelijkmatige schuifspanning), andere
    plaatdelen (flenzen, lijf van T, benen van L) met 5/6 (parabolische
    verdeling, zoals een rechthoek). Mecway zelf rekent met Euler-balken
    (geen afschuifvervorming).
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
        # Benen naar de hoofdassen (V onder theta met been b, zie
        # _profile_props) geprojecteerd.
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


def _add_shear_coefs(elset_name, geom):
    """
    Sectie voor POU_D_T: bij SECTION='GENERALE' AY en AZ toevoegen.

    Zonder AY/AZ stopte Code-Aster met MODELISA_78 ("section GENERALE,
    element poutre : il manque la caracteristique ...") en DVP_2 (gezien in
    Mecway en opnieuw in een run met Code-Aster 17.4). De catalogus
    (affe_cara_elem.py) eist AY/AZ > 0 als ze gegeven zijn. Bij RECTANGLE
    en CERCLE rekent Code-Aster ze zelf uit: een korte POU_D_T-uitkraging
    (L 50 mm, 20x10 mm) gaf met RECTANGLE dezelfde doorbuiging als
    GENERALE met AY=AZ=1.2 en een andere dan met AY=AZ=1.0 (run met
    Code-Aster 17.4). Returns een nieuwe dict; geom zelf (gedeeld per
    materiaal) blijft ongewijzigd.
    """
    if geom.get("aster_section") != "GENERALE" or "AY" in geom["cara"]:
        return geom
    coefs = geom.get("shear_coefs")
    if coefs is None:
        coefs = (1.0, 1.0)
        log(tr("WARNING: Balk-elset '{0}' ({1}, POU_D_T): "
               "afschuifcoefficienten onbekend; AY=AZ=1.0 "
               "(afschuifoppervlak = A, geen correctie).",
               "WARNING: Beam elset '{0}' ({1}, POU_D_T): shear "
               "coefficients unknown; AY=AZ=1.0 (shear area = A, no "
               "correction).").format(elset_name,
                                      geom.get("geom_type", "?")))
    else:
        # %-opmaak: "{0:.4g}" volgt in IronPython de landinstelling (komma).
        log("INFO: Balk-elset '{0}' ({1}, POU_D_T): AY={2}, AZ={3} "
            "(benadering, zie _profile_shear_coefs).".format(
                elset_name, geom.get("geom_type", "?"),
                "%.4g" % coefs[0], "%.4g" % coefs[1]))
    new = dict(geom)
    new["cara"] = tuple(geom["cara"]) + ("AY", "AZ")
    new["vale"] = tuple(geom["vale"]) + tuple(coefs)
    return new


# ==========================================
# GEOMETRIE-PARSER
# ==========================================
def _parse_geometric_props(geom_node):
    """
    Parseer een Mecway <geometric>-element naar Code-Aster sectie-eigenschappen.

    pointy/pointz zijn het spanningsherstelpunt van Mecway ("Stress
    recovery point in principal coordinates") en worden niet gebruikt. De
    balkorientatie staat per element (_parse_beam_orientation).

    Returns
    -------
    dict or None
        Balk:  'geom_type', 'aster_section', 'cara', 'vale'
        Schaal: 'geom_type', 'thickness'
        None bij onbekend type.
    """
    geom_type = geom_node.get("type", "")
    result    = {"geom_type": geom_type}

    # ------------------------------------------------------------------
    # CIRKELVORMIGE DOORSNEDEN
    # ------------------------------------------------------------------
    if geom_type == "CircularBar":
        od = parse_and_convert(geom_node.get("roundod", "0"), 'length')
        result["aster_section"] = "CERCLE"
        result["cara"]          = ("R",)
        result["vale"]          = (od / 2.0,)
        log("INFO: CircularBar           -> CERCLE R={0} m".format(od / 2.0))

    elif geom_type == "UniformCircularTube":
        od  = parse_and_convert(geom_node.get("roundod", "0"), 'length')
        rid = parse_and_convert(geom_node.get("roundid", "0"), 'length')
        ep  = (od - rid) / 2.0
        result["aster_section"] = "CERCLE"
        result["cara"]          = ("R", "EP")
        result["vale"]          = (od / 2.0, ep)
        log("INFO: UniformCircularTube   -> CERCLE R={0} m, EP={1} m".format(
            od / 2.0, ep))

    # ------------------------------------------------------------------
    # RECHTHOEKIGE DOORSNEDEN
    # ------------------------------------------------------------------
    elif geom_type == "RectBar":
        a = parse_and_convert(geom_node.get("recta", "0"), 'length')
        b = parse_and_convert(geom_node.get("rectb", "0"), 'length')
        result["aster_section"] = "RECTANGLE"
        result["cara"]          = ("HY", "HZ")
        result["vale"]          = (a, b)
        log("INFO: RectBar               -> RECTANGLE HY={0} m, HZ={1} m".format(
            a, b))

    elif geom_type == "RectTube":
        a = parse_and_convert(geom_node.get("recta",         "0"), 'length')
        b = parse_and_convert(geom_node.get("rectb",         "0"), 'length')
        t = parse_and_convert(geom_node.get("rectthickness", "0"), 'length')
        result["aster_section"] = "RECTANGLE"
        result["cara"]          = ("HY", "HZ", "EPY", "EPZ")
        result["vale"]          = (a, b, t, t)
        log("INFO: RectTube              -> RECTANGLE HY={0}, HZ={1}, "
            "EPY=EPZ={2} m".format(a, b, t))

    # ------------------------------------------------------------------
    # ALGEMENE DOORSNEDE
    # ------------------------------------------------------------------
    elif geom_type == "UniformGeneralSection":
        A  = parse_and_convert(geom_node.get("area",            "0"), 'area')
        IY = parse_and_convert(geom_node.get("iyy",             "0"), 'inertia')
        IZ = parse_and_convert(geom_node.get("izz",             "0"), 'inertia')
        JX = parse_and_convert(geom_node.get("torsionconstant", "0"), 'inertia')
        log("INFO: UniformGeneralSection -> GENERALE (opgegeven waarden)")
        result.update(_make_generale_section(A, IY, IZ, JX))

    # ------------------------------------------------------------------
    # I-PROFIEL / T-PROFIEL / L-PROFIEL / C-PROFIEL
    # ------------------------------------------------------------------
    # Maten zoals in de tekening van het Mecway-materiaalvenster. De
    # waarden (A, I om V, I om W, torsieconstante) zijn nagerekend tegen
    # wat Mecway 33 zelf in dat venster toont; zie _profile_props().
    elif geom_type in ("I", "T", "L", "C"):
        p = geom_type.lower()
        dims = [parse_and_convert(geom_node.get(p + k, "0"), 'length')
                for k in ("a", "b", "c", "d")]
        A, IY, IZ, JX = _profile_props(geom_type, *dims)
        log("INFO: {0}-profiel             -> GENERALE (als Mecway)".format(
            geom_type))
        result.update(_make_generale_section(A, IY, IZ, JX))
        # Alleen gebruikt bij POU_D_T (STAP 3, _add_shear_coefs).
        result["shear_coefs"] = _profile_shear_coefs(geom_type, *dims)

    # ------------------------------------------------------------------
    # SCHAAL-ELEMENT
    # ------------------------------------------------------------------
    elif geom_type == "Plate":
        thickness = parse_and_convert(geom_node.get("thickness", "0"), 'length')
        result["thickness"] = thickness
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
    Truss-elementen (Mecway manual v33 par. 7.6: per element via Element
    properties -> Truss; in de .liml <elem ... truss="true">, gezien in
    Samples/VibratingTrussTower.liml en SaggingCable.liml) worden in
    Code-Aster staven: MODELISATION='BARRE' (alleen normaalkracht,
    scharnierend; catalogus phenomenons_modelisations.py, testcases
    ssll11c, sdnl138a). Een MODELISATION geldt per groep, dus:
      - alle 1D-elementen van een elset truss -> de elset wordt BARRE;
      - gemengd (balken en trusses in een component) -> de trusses gaan
        naar een eigen elset '<naam>_TRUSS' (in mesh_elements; zelfde
        materiaal, STAP 2b); de balken houden de naam van de component.
    Returns (truss_elsets, truss_parts): set van BARRE-elsets en
    {component: [truss-elset]}.
    """
    truss_elsets = set()
    truss_parts = {}
    used = set(elset_shapes_map)
    moved = {}
    for ename, teids in truss_eids.items():
        if teids == line_eids.get(ename, set()):
            truss_elsets.add(ename)
            log("INFO: Elset '{0}': {1} truss-elementen -> BARRE.".format(
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
    """Doorsnede-oppervlak (m2) van een balksectie-dict, of 0.0."""
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
# MECHANISCHE MODELITEMS ZONDER BC-KLASSE
# ==========================================
# Tags die geen belasting op een selectie zijn maar het model aanvullen
# (thermische rek, demping, MPC's, knoopmassa's); _parse_model_item zet ze
# in model_data, bridge_mesh.py / bridge_to_aster.py vertalen ze.
_MODEL_ITEM_TAGS = ("thermalstress", "temperature2", "rayleighdamping",
                    "constraintequation", "mass2", "rotationalinertia",
                    "flexiblejoint", bridge_offset.TAG)
# Daarvan in de keten thermisch -> mechanisch niet vertaald, met een
# WARNING (de andere doen er in de quasi-statische solve niet toe).
_CHAIN_DROPPED_TAGS = ("constraintequation", "flexiblejoint",
                       bridge_offset.TAG)

# DOF-namen van een constraint equation. ux/uy/uz staan in de .liml van
# het testmodel (Mecway 33). rx/ry/rz: in mecway.exe staan "rx", "ry",
# "rz" als losse strings direct voor de DOF-typenamen (DISPLX, DISPLY,
# ...), na "ux" "uy" "uz"; aannemelijk, maar NIET in een .liml gezien.
_CE_DOFS = {"ux": ("DX", "inverse_length"), "uy": ("DY", "inverse_length"),
            "uz": ("DZ", "inverse_length"), "rx": ("DRX", "inverse_angle"),
            "ry": ("DRY", "inverse_angle"), "rz": ("DRZ", "inverse_angle")}


def _not_translated(model_data, what, why):
    """Meld een niet-vertaald item (ERROR + skipped_loads)."""
    model_data["skipped_loads"].append(what)
    log(tr("ERROR: {0}: {1} NIET meegenomen.",
           "ERROR: {0}: {1} NOT included.").format(what, why))


_LIML_CHUNK = 4 * 1024 * 1024


def _model_bytes(file_path):
    """
    De bytes van de .liml tot de eerste '<solution' (als element: gevolgd
    door '>', '/' of witruimte) plus '</liml>', of None als er geen
    <solution> is. Leest in blokken, zoals bridge_results_liml.
    _find_solution_start (die werkt alleen met str, dus niet in CPython 3).
    '<' in tekst is in XML altijd '&lt;', dus de eerste '<solution' is het
    element. De bytes blijven ongewijzigd (ook een BOM en de
    XML-declaratie), de parser decodeert zoals bij ET.parse().
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
    Root-element van de .liml met alleen het model: alles vanaf <solution>
    (top-level, het laatste kind van <liml>) wordt niet gelezen. Na een run
    staan de resultaten in de .liml (bridge_results_liml.py); ET.parse()
    van het hele bestand kostte bij 99 MB 85 s in IronPython (ook
    ET.iterparse gaf pas na 81 s de eerste gebeurtenis: de parser van
    IronPython 2.7.9 verwerkt de invoer kennelijk pas in zijn geheel). Het
    model zelf (en dus alles wat hier gelezen wordt) staat vóór <solution>.
    """
    data = _model_bytes(file_path)
    if data is None:
        return ET.parse(file_path).getroot()
    return ET.fromstring(data)


def _suppressed_in(elem, configuration):
    """True als elem onderdrukt is: suppressed="true" (in alle
    configuraties) of een kind <suppressed configuration="naam"/> voor
    de gerekende configuratie."""
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
    (configuratie, hoe, ontbreekt) uit bridge_utils.choose_configuration,
    dezelfde keuze als bridge_results_liml.pick_configuration (die de
    resultaten in de solution van die configuratie zet). Hier op de
    geparste XML: pick_configuration leest bytes met str-bewerkingen en
    werkt niet in CPython 3 (rooktest).
    """
    names = [c.get("name") for c in root.findall("configuration")]
    suppressed = set()
    for elem in root.iter():
        for sup in elem.findall("suppressed"):
            suppressed.add(sup.get("configuration"))
    return choose_configuration(names, suppressed)


def _apply_suppression(root, model_data):
    """
    Zet suppressed="true" op items die in de gerekende configuratie of via
    een onderdrukte groep onderdrukt zijn; de rest van de bridge (ook
    bridge_thermal) kijkt alleen naar dat attribuut.

    Mecway (manual v33 par. 2.8): per configuratie een eigen set lasten en
    randvoorwaarden en een eigen solution. In de .liml: <configuration
    name=".."/> bovenaan en per item een kind <suppressed
    configuration=".."/> (Tutorials/AssemblyWithContact.liml,
    Samples/CylinderLifting.liml). De actieve configuratie staat niet in de
    .liml en de API kan haar niet lezen; de bridge rekent de configuratie
    uit de instelling "configuration" (startscherm) of volgens de regel van
    bridge_utils.choose_configuration, en zet de resultaten in de solution
    daarvan (_pick_configuration).
    Groepen (manual par. 9, "Groups can be suppressed"): <group name="G"
    suppressed="true"/> en items met group="G"
    (Samples/VibratingTrussTower.liml).
    """
    configuration, how, missing = _pick_configuration(root)
    model_data["configuration"] = configuration
    names = [c.get("name") for c in root.findall("configuration")]
    if configuration is not None:
        log("INFO: Configuratie '{0}' gerekend ({1}).".format(
            configuration, {"gekozen": "instelling Configuratie",
                            "enige": "de enige configuratie",
                            "vrij": "de enige zonder onderdrukte items",
                            "eerste": "de eerste"}[how]))
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
            why = "configuratie '{0}'".format(configuration)
        elif item.get("group") in groups:
            why = "groep '{0}'".format(item.get("group"))
        if why is None:
            continue
        item.set("suppressed", "true")
        log("INFO: {0} op '{1}' onderdrukt ({2}); niet vertaald.".format(
            item.tag, item.get("selection", item.get(
                "selectionslave", item.get("selectionsurface", ""))), why))


def _has_selection(root, tag, name):
    """True als root een <tag name="name"> heeft. Zonder XPath-predicaat:
    een apostrof in de naam gaf bij "[@name='...']" een SyntaxError
    ('invalid predicate') en het model viel half weg."""
    for e in root.findall(tag):
        if e.get("name") == name:
            return True
    return False


def _parse_node_temperatures(item, model_data):
    """
    Mecway Node temperature (<temperature3><nodetemperature nid=".."
    value="393 K" /></temperature3>, manual v34 par. 9.24; ook het resultaat
    van "Transfer temperatures from solution", manual par. 6.8 en 17.10) in
    een mechanische analyse: de temperatuur per knoop voor thermische rek,
    net als temperature2 (alleen met <thermalstress>).
    Gedrag van Mecway 34 (headless gezien, staaf van 4 hex8, vrije
    uitzetting en ingeklemd):
      - knopen zonder temperatuur staan op de referentietemperatuur
        (manual par. 9.25); temperature2 en temperature3 op verschillende
        knopen tellen samen;
      - S30, V30 (voorspanning) en B30: hetzelfde resultaat als
        temperature2 met dezelfde waarde op dezelfde knopen; L30 met CCX
        ook (zonder ramp, net als temperature2);
      - D30 (Dynamic Response): temperature2 en temperature3 tellen niet
        mee (gelijk resultaat met en zonder);
      - twee verschillende temperaturen op een knoop (temperature3 twee
        keer, of temperature3 en temperature2): Mecway rekent niet
        ("Conflicting temperatures on node"); dezelfde waarde mag.
    D31 staat niet bij de analysetypen van Node temperature (manual par.
    9.24); de internal solver rekent L30/D31 headless niet, dus niet
    gezien: gemeld en niet vertaald.
    Resultaat: model_data["node_temperatures"] {nid: K};
    bridge_to_aster._build_temperature_field zet ze in het knoopveld.
    """
    atype = model_data.get("analysis_type")
    if atype == "D30":
        log("INFO: Node temperature (temperature3) telt niet mee in Dynamic "
            "Response (D30), zoals in Mecway.")
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
    log("INFO: Node temperature op {0} knopen.".format(n))


def _selection_kind(root, sel):
    """'GROUP_NO' voor een nodeselection, anders 'GROUP_MA'."""
    if _has_selection(root, "nodeselection", sel):
        return "GROUP_NO"
    return "GROUP_MA"


def _parse_model_item(item, root, model_data):
    """Vul model_data aan voor een tag uit _MODEL_ITEM_TAGS."""
    tag = item.tag
    sel = item.get("selection", "")
    if tag == bridge_offset.TAG:
        # Element offset van schalen en balken (manual v34 par. 7.4.3,
        # 7.5.1); bridge_mesh/bridge_to_aster vertalen het (bridge_offset).
        bridge_offset.parse(item, model_data)
    elif tag == "thermalstress":
        # Mecway (manual v33 par. 9.25): een referentietemperatuur; knopen
        # zonder temperatuur staan op die temperatuur.
        if model_data.get("thermal_stress") is not None:
            _not_translated(model_data,
                            tr("tweede thermal stress",
                               "second thermal stress"),
                            tr("Mecway staat er een per model toe;",
                               "Mecway allows one per model;"))
            return
        model_data["thermal_stress"] = {"tref": parse_and_convert(
            item.findtext("referencetemperature"), "temperature")}
        log("INFO: Thermal stress, referentietemperatuur {0} K.".format(
            model_data["thermal_stress"]["tref"]))
    elif tag == "temperature2":
        # Mecway (manual v33 par. 9.23): in een mechanische analyse de
        # temperatuur voor thermische rek (met <thermalstress>).
        # <starttime>/<endtime> gelden alleen voor thermische analyses.
        # Een tijdstabel of formule in t wordt een lijst (t, K) (formule:
        # bemonsterd over de eindtijd van <timesteps>, daarom root);
        # bridge_to_aster._build_temperature_field gebruikt die in
        # STAT_NON_LINE en DYNA_NON_LINE (EVOL_THER) en laat hem elders weg,
        # zoals Mecway's eigen solver (KNOWN_BUGS 17).
        if model_data.get("analysis_type") == "D30":
            # Mecway 34 negeert Temperature in Dynamic Response (headless
            # gezien: gelijk resultaat met en zonder, ook met tijdstabel).
            log("INFO: Temperature (temperature2) op '{0}' telt niet mee in "
                "Dynamic Response (D30), zoals in Mecway.".format(sel))
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
            log("INFO: Temperatuur op '{0}' met tijdshistorie ({1} punten, "
                "{2} .. {3} s).".format(sel, len(value), value[0][0],
                                        value[-1][0]))
        else:
            log("INFO: Temperatuur {0} K op '{1}'.".format(value, sel))
    elif tag == "rayleighdamping":
        # Mecway (manual v33 par. 9.26): C = alpha M + beta K, op het hele
        # model of een selectie. Code-Aster: DEFI_MATERIAU ELAS AMOR_ALPHA
        # (x K) en AMOR_BETA (x M), U4.43.01 par. 4 -> per materiaal.
        # XML (Samples/DampedVibratingStrip.liml): <rayleighdamping
        # selection=""><alpha>1 rad/s</alpha><beta>0.005 s</beta>; een
        # lege selection is het hele model.
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
        log("INFO: Rayleigh-demping {0}.".format(model_data["rayleigh"]))
    elif tag == "constraintequation":
        # Mecway (manual v33 par. 9.42): A dof1 + B dof2 + ... = C.
        # <term coefficient="1 1/m" nid="49" dof="ux" />. In mecway.exe
        # staan "term" en "constant" samen bij de constraint-equation-
        # teksten ("The constant is ... but it must be zero with this
        # analysis type and solver"); of constant een kind-element of een
        # attribuut is, is NIET gezien in een .liml: beide gelezen. De
        # constante moet 0 zijn bij CCX en dynamica (manual par. 9.42).
        # Tutorials/ConstraintEquations.liml bevat zelf geen vergelijking
        # (die maak je in de tutorial, manual par. 17.14).
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
        # Mecway (manual v33 par. 9.12, "Flexible joint on beam"): laat het
        # uiteinde van een balkelement vrij roteren om een combinatie van
        # zijn lokale assen U (as), V en W, ook als het aan een ander
        # element vastzit of de rotatie is opgelegd; alleen op eindvlakken
        # van balkelementen. Geen stijfheid: alleen vrij of vast. XML
        # (Mecway 34 opgeslagen, tekst "Free rotation about U/V/W" in
        # mecway.exe): <flexiblejoint selection="FJ"><rotu /><rotw />
        # </flexiblejoint>; een aanwezig kind = vrij (inhoud genegeerd,
        # <rotu>false</rotu> slaat Mecway op als <rotu />). Vertaling:
        # bridge_mesh._flexible_joints (dubbele knoop + LIAISON_DDL).
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
            log("INFO: Flexible joint op '{0}' zonder vrije rotatie; geen "
                "effect.".format(sel))
            return
        model_data["flexible_joints"].append({"selection": sel,
                                              "free": free})
        log("INFO: Flexible joint op '{0}': vrije rotatie om {1}.".format(
            sel, "/".join(a.upper() for a in free)))
    elif tag in ("mass2", "rotationalinertia"):
        # Mecway (manual v33 par. 9.21/9.22): knoopmassa (gelijk verdeeld
        # over de knopen) of rotatietraagheid om de X/Y/Z-as (axis="3" = Z
        # gezien in Mecway 33; 1 = X, 2 = Y afgeleid; "axis" staat in
        # mecway.exe bij de rotational-inertia-teksten). Een
        # rotatietraagheid mag in Mecway maar op een knoop ("A rotational
        # inertia can only be applied to a single node", mecway.exe).
        # Code-Aster: POI1 met DIS_T M_T_D_N of DIS_TR M_TR_D_N
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
        log("INFO: {0} op '{1}': {2}.".format(tag, sel, entry))


def _check_gravity_history(params, model_data):
    """
    Gravity met tijdshistorie (bridge_bcs.GravityBC): False (gemeld) als de
    richting in de tijd verandert; een PESANTEUR met FONC_MULT heeft een
    vaste DIRECTION. True zonder historie of bij een vaste richting.
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
    log("INFO: Gravity met tijdshistorie: GRAVITE(t) {0} langs "
        "DIRECTION {1} (PESANTEUR met FONC_MULT).".format(
            d["GRAVITE"], d["DIRECTION"]))
    return True


# Analyses waarin een formule in x, y, z (bridge_bcs.PositionFormula) als
# FORMULE in AFFE_CHAR_MECA_F werkt (bridge_to_aster._build_charges):
# statisch, niet-lineair statisch, impliciete dynamica en modaal/knik
# (voorspanning). Niet: expliciete dynamica (een opgelegde verplaatsing
# wordt daar een versnelling, bridge_to_aster._explicit_kinematics),
# harmonisch, modale respons en spectrum (amplituden, NIET nagegaan).
_POSITION_SOLVERS = ("MECA_STATIQUE", "STAT_NON_LINE", "DYNA_NON_LINE",
                     "CALC_MODES")
_EXPLICIT_SCHEMAS = ("DIFF_CENT", "TCHAMWA")


def _check_position_formulas(tag, params, sel, run_cfg, model_data):
    """
    False (gemeld) als params een formule in x, y, z bevat
    (bridge_bcs.PositionFormula) die in deze analyse niet vertaald wordt.
    Anders True; bij een kracht, verplaatsing, rotatie of line pressure
    een WARNING: Mecway 34 legt die met een formule in x, y, z niet op
    (gemeten, zie de kop van bridge_bcs.py), de bridge wel.
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
    """False als de belasting niet vertaald kan worden (gemeld)."""
    if params.get("_skipped"):
        # formule die niet vertaald kan worden (bridge_bcs, ERROR gelogd)
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
        log("INFO: Elastic support op '{0}' met stijfheid 0; "
            "overgeslagen.".format(sel))
        return False
    return True


# ==========================================
# HOOFDFUNCTIE
# ==========================================
def extract_aster_data_from_liml(file_path):
    """
    Parst het .liml-bestand en retourneert model_data.

    Parameters
    ----------
    file_path : str  Absoluut pad naar het actieve .liml-bestand.

    Returns
    -------
    dict  model_data voor Code-Aster bestandgeneratie, of None bij een
          onverwachte fout tijdens het parsen (ERROR in de log).
    """
    log("START: Analyseren van .liml")
    hex8_mod  = _elem_choice("elem_hex8")
    shell_mod = _elem_choice("elem_shell")
    beam_mod  = _elem_choice("elem_beam")
    log("INFO: Elementformulering: hex8 -> {0}, lineaire schaal -> {1}, "
        "balk -> {2}".format(hex8_mod, shell_mod, beam_mod))
    model_data = {
        "bcs":                  [],
        "couplings":            [],   # nodesurfacecoupling -> LIAISON_RBE3 / LIAISON_SOLIDE
        "materials":            {},   # {mat_naam: {"E": float, "NU": float, "rho": float, ...}}
        "spring_materials":     {},   # {mat_naam: spring_constant_N_per_m}
        "mat_geometrics":       {},   # {mat_naam: geom_props_dict}
        "elsets":               {},   # {elset_naam: mat_naam}
        "elset_dims":           {},   # {elset_naam: "1D"/"2D"/"3D"}
        "elset_modelisations":  {},   # {elset_naam: MODELISATION-string}
        "node_groups":          {},
        "beam_sections":        {},   # 1D balk-elsets
        "shell_sections":       {},   # 2D schaal-elsets
        "spring_sections":      {},   # {elset_naam: {"spring_constant": float}}
        "has_rot_dofs":         False,
        "has_1d":               False,
        "has_2d":               False,
        "has_3d":               False,
        "elem_shapes":          {},   # {eid (int): Mecway-vorm}
        # {eid: {"vec": (vx, vy, vz) of None, "angle": rad}} voor balk-
        # elementen met een eigen orientatie (bridge_mesh maakt er groepen
        # met VECT_Y van).
        "beam_orientations":    {},
        # Belastingen/randvoorwaarden die niet vertaald konden worden; main()
        # meldt ze aan het eind aan de gebruiker.
        "skipped_loads":        [],
        "face_selections":      {},   # {faceselection-naam: [eid, ...]}
        # Mesh uit de .liml (bridge_mesh.write_mesh):
        "mesh_nodes":           {},   # {nid: (x, y, z)} in m
        "mesh_elements":        [],   # [(eid, vorm, [nid, ...], elset)]
        "face_selection_faces": {},   # {naam: [(eid, faceid), ...]}
        "element_selections":   {},   # {naam: [eid, ...]}
        "shell_upgrades":       {},   # {elset: [MODI_MAILLE-OPTION, ...]} (COQUE_3D)
        # Analyse uit de .liml: <analysis type="S30|L30|D31|..." solver=...>
        # en <timesteps> (eindtijd, start, interval van de uitvoer).
        "analysis_type":        "",
        "analysis_solver":      "",
        # Modaal (V30): <analysis maxmode="..">, aantal modes; None = niet
        # opgegeven (bridge_to_aster._build_modal: instelling modal_modes).
        "maxmode":              None,
        # D30 met <analysis modesuperposition="true">
        "mode_superposition":   False,
        "timesteps":            {},
        # contact2 -> DEFI_CONTACT: [{"master", "slave", "friction",
        # "selfcontact", "type"}]
        "contacts":             [],
        # <initialconditions><velocity>: [(selectie, target, (vx, vy, vz))]
        "initial_velocities":   [],
        # Materialen met OpenRadioss law VOID (geen stijfheid)
        "void_materials":       [],
        # De .liml zelf (aster_results_export leest er elsets en elementen uit)
        "liml_path":            file_path,
        # #ASTER-regels uit de vrije tekstvelden (bridge_custom.py)
        "aster_custom":         bridge_custom.empty(),
        # Mechanische modelitems (_parse_model_item):
        "thermal_stress":       None,  # {"tref": K}
        "temperatures":         [],    # [{"selection", "target", "value"}]
        # Node temperature (temperature3) in een mechanische analyse:
        # {nid: K} (_parse_node_temperatures)
        "node_temperatures":    {},
        "rayleigh":             None,  # {"alpha": 1/s, "beta": s}
        "constraint_equations": [],    # [{"terms": [(nid, DDL, coef)], ...}]
        "point_masses":         [],    # [{"selection", "kind", "value", ..}]
        # contact2 bonded* -> LIAISON_MAIL: [{"master", "slave", "type",
        # "tolerance", "kn", "kt"}]
        "bonded":               [],
        # line2-elementen met materiaal Gap/Damper (DIS_T) en TensionOnly
        # (CABLE): {mat_naam: {...}} en per elset de sectie
        "line_discretes":       {},
        "discrete_sections":    {},    # {elset: {"kind": "gap"/"damper",..}}
        "cable_sections":       {},    # {elset: {"area": m2}}
        # Flexible joint on beam: [{"selection": vlakselectie,
        # "free": ("u", "v", "w")}] (bridge_mesh._flexible_joints)
        "flexible_joints":      [],
    }

    try:
        root = _parse_model_root(file_path)
        # Per configuratie of via een groep onderdrukte items krijgen
        # suppressed="true".
        _apply_suppression(root, model_data)

        # ==========================================
        # STAP 0: ELEMENTVORMEN PER ELSET VERZAMELEN
        # ==========================================
        # Knopen en elementen van het model (niet die van <solution>):
        # bridge_mesh.py schrijft hiermee het Code-Aster-mesh.
        for node in root.findall("node"):
            model_data["mesh_nodes"][int(node.get("nid"))] = (
                float(node.get("x", "0")), float(node.get("y", "0")),
                float(node.get("z", "0")))
        elset_shapes_map = {}
        truss_eids = {}             # {elset: set(eid)} met truss="true"
        line_eids = {}              # {elset: set(eid)} alle 1D-elementen
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
                        # U-as (gap-richting, manual v33 par. 7.9)
                        model_data.setdefault("elem_u_axes", {})[int(eid)] = \
                            tuple(float(e.get(k, "0")) for k in (
                                "orientationux", "orientationuy",
                                "orientationuz"))
                    if (eid and s in _DIM_1D_SHAPES and
                            e.get("truss") != "true"):
                        # Een truss heeft geen orientatie nodig (manual
                        # v33 par. 7.6); BARRE kent geen VECT_Y.
                        orient = _parse_beam_orientation(e)
                        if orient is not None:
                            model_data["beam_orientations"][int(eid)] = \
                                orient
            elset_shapes_map[ename] = shapes
        truss_elsets, truss_parts = _split_trusses(
            model_data, elset_shapes_map, truss_eids, line_eids)

        # Faceselections: welke elementen dragen de geselecteerde vlakken.
        # Nodig om te bepalen of een vlak bij een volume-element hoort
        # (randelement in AFFE_MODELE) of bij een schaal.
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
        # STAP 0b: ANALYSE, TIJDSTAPPEN, OPENRADIOSS-FUNCTIES
        # ==========================================
        ana = root.find("analysis")
        if ana is not None:
            model_data["analysis_type"] = ana.get("type", "")
            model_data["analysis_solver"] = ana.get("solver", "")
            # Dynamic Response (D30) met de optie Mode superposition
            # (manual v33 par. 6.4): <analysis type="D30"
            # modesuperposition="true" maxmode="10" /> (Mecway-voorbeeld
            # DampedVibratingStrip.liml).
            model_data["mode_superposition"] = (
                ana.get("modesuperposition", "") == "true")
            try:
                model_data["maxmode"] = int(ana.get("maxmode"))
            except (TypeError, ValueError):
                model_data["maxmode"] = None
            # Knik (B30): shift = instelling van Mecway's eigen oplosser
            # (manual v33 par. 6.6); alleen gemeld (bridge_to_aster).
            model_data["analysis_shift"] = ana.get("shift")
        # DST is in Code-Aster 17.4 niet geprogrammeerd voor niet-lineaire
        # berekeningen: STAT_NON_LINE gaf alarm CALCULEL_54 ("PCOMPOR de
        # l'option FULL_MECA n'est pas connu des TYPE_ELEM") en daarna
        # <EXCEPTION> MECANONLINE_3 (gezien in een run, vlakke quad4-plaat).
        # Alleen MECA_STATIQUE krijgt dus DST.
        run_cfg = _run_analysis_cfg(model_data["analysis_type"],
                                    model_data.get("mode_superposition"))
        solver_cmd = run_cfg.get("solver_command")
        # Thermische analyse: thermische belastingen, materialen en
        # beginvoorwaarden leest bridge_thermal.parse_thermal() (STAP 2b).
        thermal_run = bridge_thermal.is_thermal(run_cfg)
        # Keten thermisch -> mechanisch (bridge_thermomech.py, stap S4b): een
        # transient thermisch model (T31) met een Thermal stress. Mecway
        # gebruikt Thermal stress alleen in mechanische analyses (manual v33
        # par. 9.25) maar bewaart het, met de mechanische randvoorwaarden,
        # ook in een thermisch model; de bridge leest ze dan wel.
        thermo_mech = (thermal_run and
                       model_data["analysis_type"] == "T31" and
                       any(it.tag == "thermalstress" and
                           it.get("suppressed", "") != "true"
                           for it in root))
        model_data["thermo_mech"] = thermo_mech
        if thermo_mech:
            log("INFO: Thermal stress in een transient thermisch model: "
                "keten thermisch -> mechanisch (restspanning en vervorming, "
                "bridge_thermomech.py); mechanische randvoorwaarden en "
                "lasten tellen mee.")
        # Akoestiek (A30): materialen en voorwaarden leest
        # bridge_acoustic.parse_acoustic() (STAP 2c).
        acoustic_run = bridge_acoustic.is_acoustic(run_cfg)
        # Vibro-akoestiek (constructie + fluidum): fluidum-onderdelen en
        # drukknopen leest bridge_vibroacoustic.parse_vibro() (STAP 2c).
        vibro_run = bridge_vibroacoustic.is_vibroacoustic(run_cfg)
        # Alleen melden als het model zulke elementen heeft (anders is de
        # keuze niet van toepassing).
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
        # 3D_SI kan de stabiele tijdstap niet berekenen: DYNA_NON_LINE met
        # DIFF_CENT gaf <EXCEPTION> CALCUL_37 ("Le TYPE_ELEMENT MECA_HEXS8
        # ne sait pas encore calculer l'option: PAS_COURANT"), gezien in een
        # run met Code-Aster 17.4. Expliciet dus altijd 3D.
        if hex8_mod == "3D_SI" and solver_cmd == "DYNA_NON_LINE" and \
                run_cfg.get("schema", "HHT") in ("DIFF_CENT", "TCHAMWA") \
                and "hex8" in all_shapes:
            log(tr("WARNING: 3D_SI werkt niet met een expliciet schema "
                   "({0}); hex8 worden 3D.",
                   "WARNING: 3D_SI does not work with an explicit scheme "
                   "({0}); hex8 become 3D.").format(run_cfg.get("schema")))
            hex8_mod = "3D"
        # LINE_QUAD (kwadratisch) expliciet: diagonale massa van HEXA20 bij
        # DIFF_CENT NIET geverifieerd, dus daar lineair.
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
                # schrijft een oplossing op t = 0 en elke n-de stap
                # (headless gezien met Mecway 33, D30 met mode
                # superposition: stepsize 0,001 s, n = 10 gaf 201 stappen
                # over 2 s). bridge_to_aster._output_times.
                "stepsize": parse_and_convert(ts.get("stepsize", "0 s"),
                                              "time"),
                "keep_every": _positive_int(ts.get("keepeverynthtimestep")),
            }
            log("INFO: Tijdstappen: {0}".format(model_data["timesteps"]))
        if (model_data["analysis_type"] == "D30" and solver_cmd ==
                "DYNA_NON_LINE" and (run_cfg.get("schema") != "NEWMARK" or
                                     run_cfg.get("deformation") != "PETIT")):
            # Mecway D30 zonder Mode superposition: lineair, Newmark met de
            # gemiddelde versnelling (manual v33 par. 6.4). Met NEWMARK en
            # PETIT rekent dyna_impl_3d hetzelfde schema (verificatie MD-07).
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
        model_data["aster_custom"] = bridge_custom.parse(
            [root.findtext(tag) for tag in bridge_custom.CUSTOM_TAGS])
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
        # STAP 1: KNOOPGROEPEN INLEZEN
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
                log("INFO: NodeGroup '{0}' -> {1} knopen".format(
                    name, len(node_ids)))

        # ==========================================
        # STAP 2: OVERIGE ELEMENTEN VERWERKEN
        # ==========================================
        for item in root:
            tag = item.tag
            log("DEBUG tag: '{0}' selection='{1}'".format(
                tag, item.get("selection", "")))

            # --------------------------------------------------
            # 2a. MATERIALEN
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
                        log("INFO: Veer-materiaal '{0}' -> k={1} N/m".format(
                            mat_name, k))

                    elif mech_type == "Isotropic":
                        mat_props = {
                            "E":    parse_and_convert(
                                        mech_node.get("youngsmodulus",
                                                      "210000000000"),
                                        'pressure'),
                            # Zonder poissonratio rekent Mecway met nu = 0
                            # (headless gemeten: VibratingCantileverSolid
                            # gaf in Mecway de frequenties van nu = 0;
                            # met 0,3 week de bridge +1,7% af).
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

                        # --- Plastische hardingscurve (optioneel) ---
                        # Mecway:
                        #   <plastic type="Isotropic">
                        #     <hardeningcurve strain="0"    stress="0 MPa" />
                        #     <hardeningcurve strain="0.01" stress="235 MPa" />
                        #     ...
                        #   </plastic>
                        #
                        # De curve wordt hier alleen op rek gesorteerd en
                        # verder ONGEWIJZIGD opgeslagen als
                        # (strain, stress)-tuples in SI-eenheden.
                        #
                        # De omzetting naar de Code-Aster TRACTION-definitie
                        # (totale rek EPSI, eerste punt = elastische grens,
                        # GEEN punt met abscis nul; U4.43.01 par. 5.1.1)
                        # en alle validatie gebeurt in bridge_to_aster.py
                        # (_to_aster_traction_curve), gestuurd door
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
                            # Typen (manual v33 par. 8.8; mecway.exe noemt
                            # BilinearIsotropic, BilinearKinematic,
                            # Kinematic, RambergOsgood naast Isotropic;
                            # 'Simple' in die lijst is het type van
                            # <density>, geen plasticiteit). XML van
                            # Isotropic, BilinearIsotropic en RambergOsgood
                            # gezien in Forum_models/TensileBlockTest.liml:
                            # BilinearIsotropic / BilinearKinematic
                            # (yieldstrength, tangentmodulus), RambergOsgood
                            # (yieldstrength, rambergosgoodexponent,
                            # rambergossgoodalpha), Kinematic: een
                            # hardingscurve zoals Isotropic
                            # (_kinematic_curve). Ideaal plastisch:
                            # Bilinear met tangentmodulus 0 (ECRO_LINE
                            # D_SIGM_EPSI=0.0 kan, testcase forma20c).
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
                                log("INFO: Plastische curve '{0}' voor "
                                    "materiaal '{1}': {2} punten, eerste "
                                    "punt ({3}, {4}).".format(
                                        plastic_type, mat_name, len(curve),
                                        curve[0][0], curve[0][1]))

                        model_data["materials"][mat_name] = mat_props
                        log("INFO: Materiaal '{0}' -> E={1} Pa, NU={2}, "
                            "Texp={3} 1/K, rho={4} kg/m3, plastic={5}".format(
                                mat_name,
                                mat_props["E"],  mat_props["NU"],
                                mat_props["Texp"], mat_props["rho"],
                                "plastic_curve" in mat_props))

                    elif mech_type in ("Gap", "Damper"):
                        # Mecway (manual v33 par. 7.8/7.9) op line2:
                        #   <mechanical type="Gap" closedstiffness="1E9 N/m"
                        #     [initialclearance=".." openforce=".."] />
                        #   <mechanical type="Damper"
                        #     dampingcoefficient="50 N.s/m" />
                        # initialclearance/openforce: attribuutnamen uit
                        # mecway.exe (in de lijst materiaalattributen,
                        # tussen springconstant/dampingcoefficient en
                        # closedstiffness), NIET in een .liml gezien.
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
                                    "(alleen CCX, gladde overgang) wordt "
                                    "niet gebruikt; Code-Aster DIS_CHOC is "
                                    "een harde schakeling.".format(mat_name))
                        else:
                            ld = {"kind": "damper",
                                  "c": parse_and_convert(mech_node.get(
                                      "dampingcoefficient", "0"), "damping")}
                        model_data["line_discretes"][mat_name] = ld
                        log("INFO: {0}-materiaal '{1}': {2}".format(
                            mech_type, mat_name, ld))

                    elif mech_type == "TensionOnly":
                        # Mecway (manual v33 par. 7.10): truss die alleen
                        # trek opneemt, stijfheid E A / L. Code-Aster: kabel
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
                        log("INFO: TensionOnly-materiaal '{0}': E={1} Pa "
                            "(kabel).".format(mat_name, model_data[
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
                    if geom_props is not None:
                        model_data["mat_geometrics"][mat_name] = geom_props
                        log("INFO: Geometrie-type '{0}' opgeslagen voor "
                            "materiaal '{1}'.".format(
                                geom_props.get("geom_type", "?"), mat_name))

            # --------------------------------------------------
            # 2b. ELEMENT-SETS
            # --------------------------------------------------
            elif tag == "elset":
                elset_name   = item.get("name", "Default")
                mat_assigned = item.get("material", None)
                if mat_assigned:
                    model_data["elsets"][elset_name] = mat_assigned
                    # Met de Mecway-naam (bridge_mesh hernoemt "elsets"):
                    # factor of safety per elset (aster_results_export).
                    model_data.setdefault("mecway_elset_materials", {})[
                        elset_name] = mat_assigned

                shapes = elset_shapes_map.get(elset_name, set())
                # Een elset krijgt één MODELISATION (1D boven 2D boven 3D);
                # elementen van een andere dimensie modelleert Code-Aster
                # dan niet (AFFE_MODELE kent ze dat type niet toe). Melden.
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
                    # Standaard POU_D_E: Euler-Bernoulli, zoals Mecway zelf
                    # ("Mecway's beam elements use Euler beam theory",
                    # Mecway-manual v33 par. 7.5). POU_D_T (Timoshenko) via
                    # CONFIG_BRIDGE["elem_beam"]; die heeft bij
                    # SECTION='GENERALE' AY/AZ nodig (STAP 3,
                    # _add_shear_coefs). POU_D_E bestaat alleen op SEG2
                    # (code_aster catalogus phenomenons_modelisations.py).
                    modelisation = beam_mod
                    model_data["has_1d"] = True
                    if "line3" in shapes and not thermal_run:
                        # Kwadratische balk (Mecway: alleen met CCX, manual
                        # v33 par. 7.5): bridge_mesh.write_mesh splitst elk
                        # line3-element in de middenknoop in twee SEG2-cellen
                        # (KNOWN_BUGS-keuze C4); de controle op niet-balken
                        # (truss, veer, ...) staat na STAP 3.
                        log("INFO: Elset '{0}' bevat line3-balken; elk "
                            "element wordt in de middenknoop gesplitst in "
                            "twee SEG2-cellen ({1}).".format(
                                elset_name, beam_mod))
                elif shapes & _DIM_2D_SHAPES:
                    dim          = "2D"
                    model_data["has_2d"] = True
                    # Code-Aster v17.4.0 catalogus:
                    #   DKT      : TRIA3, QUAD4
                    #   COQUE_3D : TRIA7, QUAD9 (TRIA6/QUAD8 eerst omzetten
                    #              met CREA_MAILLAGE MODI_MAILLE TRIA6_7/QUAD8_9)
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
                        # Keuze COQUE_3D voor lineaire schalen: Code-Aster
                        # maakt ze eerst kwadratisch (LINE_QUAD, dan
                        # QUAD8_9/TRIA6_7); bridge_to_aster._resolve_line_quad
                        # controleert of dat conform kan.
                        modelisation = "COQUE_3D"
                        upgrades = ["LINE_QUAD"]
                        if "quad4" in shapes:
                            upgrades.append("QUAD8_9")
                        if "tri3" in shapes:
                            upgrades.append("TRIA6_7")
                        model_data["shell_upgrades"][elset_name] = upgrades
                    else:
                        # DKT (standaard) of DST via CONFIG_BRIDGE
                        # ["elem_shell"]; beide op TRIA3/QUAD4.
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
                    # 3D_SI (onderintegratie) alleen voor elsets met
                    # uitsluitend hex8; anders blijft het 3D.
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
                # Truss-deel van een component met balken (_split_trusses)
                for part in truss_parts.get(elset_name, []):
                    if mat_assigned:
                        model_data["elsets"][part] = mat_assigned
                    model_data["elset_dims"][part] = "1D"
                    model_data["elset_modelisations"][part] = "BARRE"
                    model_data["has_1d"] = True
                    log("INFO: Elset '{0}' (truss-deel van '{1}') -> dim=1D, "
                        "MODELISATION='BARRE'".format(part, elset_name))

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
            #   selectionnode    -> master (1 knoop, GROUP_NO_MAIT bij RBE3)
            #   selectionsurface -> slaves (n knopen, GROUP_NO_ESCL bij RBE3)
            #   type="rbe3"      -> LIAISON_RBE3
            #   type="rigidbody" -> LIAISON_SOLIDE  (master + slaves =
            #                                       1 starre body)
            #   surfacerot=true  -> DDL_MAIT bevat ook DRX/DRY/DRZ (alleen rbe3)
            #
            # Slaves (selectionsurface):
            #   - nodeselection -> GROUP_NO met dezelfde naam;
            #   - faceselection -> de vlakken staan als GROUP_MA in het mesh
            #     (bridge_mesh.py, randelementen); bridge_to_aster.py maakt
            #     er een knoopgroep van met DEFI_GROUP
            #     CREA_GROUP_NO=_F(NOM=..., GROUP_MA=...).
            # Master (selectionnode): een losse knoop (zonder element) krijgt
            #   in bridge_mesh.py een POI1-element (DIS_T, of DIS_TR bij rbe3
            #   met surfacerot=true), anders heeft hij geen vrijheidsgraden
            #   in het model.
            # --------------------------------------------------
            elif acoustic_run and (
                    tag in bridge_acoustic.ACOUSTIC_TAGS or
                    tag in SUPPORTED_BCS or tag in _MODEL_ITEM_TAGS or
                    tag in bridge_thermal.THERMAL_TAGS or tag in (
                        "nodesurfacecoupling", "contact2",
                        "initialconditions")):
                # Akoestische analyse: alleen fluid pressure (en impedantie)
                # doen mee; bridge_acoustic meldt de rest.
                bridge_acoustic.note_tag(item, model_data)
                continue
            elif tag in bridge_acoustic.ACOUSTIC_TAGS:
                # Alleen in Acoustic Resonance (manual v33 par. 9.34, 9.35);
                # in de vibro-akoestiek leest parse_vibro ze (STAP 2c).
                if item.get("suppressed", "") != "true" and not vibro_run:
                    log("INFO: Akoestische voorwaarde '{0}' op '{1}' telt "
                        "niet mee in deze analyse.".format(
                            tag, item.get("selection", "")))
                continue
            elif tag == "nodesurfacecoupling":
                if item.get("suppressed", "") == "true":
                    log("INFO: nodesurfacecoupling overgeslagen (suppressed).")
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

                # selectionsurface: nodeselection (knopen) of faceselection
                # (vlakken; de slave-knopen worden in de .comm met
                # DEFI_GROUP CREA_GROUP_NO=_F(GROUP_MA=...) afgeleid).
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
                    "slave_kind":   slave_kind,  # GROUP_NO of GROUP_MA
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
                # Mecway kent unilateralelastic (contact) en bondedelastic/
                # bondedtie/bondedce (verlijmd; type-namen uit mecway.exe).
                # Verlijmd is geen DEFI_CONTACT (dat zou kunnen loslaten),
                # maar LIAISON_MAIL (bridge_mesh._bonded).
                # Stijfheid per oppervlak (Pa/m): Mecway's penalty-contact;
                # de bridge gebruikt ze bij contact_algo = PENALISATION
                # (bridge_to_aster._build_contact_block) en bij verlijmd
                # 'elastic' (alleen gemeld). Mecway eist kn > 0 ("Normal
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
                    # Thermisch 'elastic': warmteweerstandslaag met
                    # "Thermal conductance per unit area" (manual v33 par.
                    # 9.9.1), W/m²/K; bridge_thermal.bonded_loads ->
                    # ECHANGE_PAROI. Tagnaam: Mecway 34 (CCX-solver,
                    # headless) rekent met <conductanceperarea> de
                    # weerstandslaag (TH-04c: 340/360 K), met
                    # <thermalcontactconductance> niet.
                    text = item.findtext("conductanceperarea")
                    if text:
                        contact["conductance"] = parse_and_convert(
                            text, "heat_transfer")
                    model_data["bonded"].append(contact)
                    log("INFO: Verlijmd contact {0}".format(contact))
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
            # 2c-ter. BEGINVOORWAARDEN
            # <initialconditions><velocity selection=".."><value>..</value>
            #   <x>..</x><y>..</y><z>..</z></velocity></initialconditions>
            # --------------------------------------------------
            elif tag == "initialconditions":
                for ic in item:
                    sel = ic.get("selection", "")
                    if ic.tag == "temperature2":
                        # Begintemperatuur: bridge_thermal; in een
                        # mechanische analyse niet van toepassing.
                        if not thermal_run and ic.get("suppressed") != "true":
                            log("INFO: Begintemperatuur op '{0}' telt niet "
                                "mee in een mechanische analyse.".format(sel))
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
                    log("INFO: Beginsnelheid op '{0}': {1}".format(
                        sel, model_data["initial_velocities"][-1][2]))

            elif thermal_run and (tag in bridge_thermal.THERMAL_TAGS or
                                  tag in SUPPORTED_BCS or
                                  tag in _MODEL_ITEM_TAGS) and not (
                    thermo_mech and (tag in SUPPORTED_BCS or
                                     tag == "thermalstress")):
                # Thermische belastingen: bridge_thermal.parse_thermal()
                # hieronder. Mechanische belastingen spelen in een
                # thermische analyse geen rol (Mecway-manual v33 hoofdstuk
                # 9: per belasting de analysetypen), behalve in de keten
                # thermisch -> mechanisch (thermo_mech, hierboven): dan
                # gaan ze door naar 2d / _parse_model_item.
                if (tag in bridge_thermal.THERMAL_TAGS or
                        item.get("suppressed", "") == "true"):
                    continue
                if thermo_mech and tag in _CHAIN_DROPPED_TAGS:
                    # In de keten loopt de mechanische solve op het mesh
                    # en de modelisaties van het thermische deel (schalen
                    # als PLAN, geen balken; bridge_thermal): element
                    # offset (eigen knopen/EXCENTREMENT), flexible joints
                    # (eigen knoop) en constraint equations worden daar
                    # niet vertaald.
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
                    log("INFO: '{0}' op '{1}' telt niet mee in de keten "
                        "thermisch -> mechanisch (quasi-statisch, "
                        "temperatuur uit het thermische deel).".format(
                            tag, item.get("selection", "")))
                else:
                    log("INFO: Mechanische belasting '{0}' op '{1}' telt "
                        "niet mee in de thermische analyse (alleen met een "
                        "Thermal stress in een T31-model: keten thermisch "
                        "-> mechanisch, docs/Lassen.md par. 9).".format(
                            tag, item.get("selection", "")))
                continue
            elif not thermal_run and tag == "temperature3":
                # Node temperature in een mechanische analyse: thermische
                # rek per knoop.
                if item.get("suppressed", "") == "true":
                    log("INFO: temperature3 overgeslagen (suppressed).")
                    continue
                _parse_node_temperatures(item, model_data)
            elif (not thermal_run and tag in bridge_thermal.THERMAL_TAGS
                  and tag not in _MODEL_ITEM_TAGS):
                # Thermische belastingen (convectie, warmtestroom, ...)
                # spelen in een mechanische analyse geen rol (Mecway-manual
                # v33 hoofdstuk 9: per belasting de analysetypen); geen
                # fout, zoals mechanische belastingen in een thermische
                # analyse hierboven. temperature2 is ook mechanisch
                # (thermische rek, _parse_model_item).
                if item.get("suppressed", "") != "true":
                    log("INFO: Thermische belasting '{0}' op '{1}' telt niet "
                        "mee in een mechanische analyse.".format(
                            tag, item.get("selection", "")))
                continue
            elif tag in _MODEL_ITEM_TAGS:
                if item.get("suppressed", "") == "true":
                    log("INFO: {0} overgeslagen (suppressed).".format(tag))
                    continue
                _parse_model_item(item, root, model_data)

            # --------------------------------------------------
            # 2d. RANDVOORWAARDEN
            # _has_rot_dofs wordt VOORLOPIG False; de waarde voor het hele
            # model wordt in STAP 4 teruggeschreven in alle BC-params
            # (bridge_mesh.py kan hem later nog op True zetten bij
            # DIS_TR-knopen).
            # --------------------------------------------------
            elif tag in SUPPORTED_BCS:
                if item.get("suppressed", "") == "true":
                    log("INFO: {0} op '{1}' overgeslagen (suppressed).".format(
                        tag, item.get("selection", "")))
                    continue

                selection_name = item.get("selection", "")
                bc_handler     = SUPPORTED_BCS[tag]

                # Voor BCs zonder selection-attribuut (gravity is globaal),
                # blijft selection_name leeg; aster_target valt op GROUP_MA
                # en wordt door bridge_to_aster.py niet als GROUP_MA="..." gerendered.
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
                    # Responsspectrum (bridge_spectrum.py): de gravity is
                    # geen last maar de spectrale versnelling per richting
                    # (tabel: periode of frequentie -> versnelling).
                    model_data.setdefault("spectrum_gravity", []).append(
                        params)
                    continue

                # Gravity met magnitude 0: geen zin om PESANTEUR te emitten.
                # Met een tijdshistorie: nul over de hele historie.
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
                        log("INFO: Gravity met magnitude 0 -> overgeslagen.")
                        continue
                    if not _check_gravity_history(params, model_data):
                        continue

                params["_has_rot_dofs"] = False   # voorlopig; zie STAP 4

                if tag == "force" and aster_target == "GROUP_NO":
                    nodes_in_group = model_data["node_groups"].get(
                        selection_name, [])
                    num_nodes = len(nodes_in_group)
                    if num_nodes > 1:
                        # Verdeel kracht over knopen. Voor tijdshistorie
                        # (lijst van (t, F)-tuples) wordt elke F gedeeld.
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
                        log("INFO: Kracht op '{0}' verdeeld over {1} "
                            "knopen.".format(selection_name, num_nodes))
                    elif num_nodes == 1:
                        log("INFO: Kracht op '{0}' op 1 knoop.".format(
                            selection_name))
                    else:
                        log(tr("WARNING: Groep '{0}' heeft 0 knopen.",
                               "WARNING: Group '{0}' has 0 nodes.").format(
                            selection_name))

                aster_dict = bc_handler.to_aster_dict(params)
                if tag == "force" and aster_target == "GROUP_MA":
                    # Totale kracht; bridge_mesh.py deelt door het
                    # oppervlak (FORCE_FACE is kracht per oppervlak).
                    log("INFO: Kracht op vlakken '{0}': wordt FORCE_FACE "
                        "(totaal / oppervlak).".format(selection_name))
                model_data["bcs"].append({
                    "type":          tag,
                    "selection":     selection_name,
                    "params":        params,
                    "aster_target":  aster_target,
                    "aster_keyword": bc_handler.keyword(params),
                    "aster_dict":    aster_dict,
                })

            # --------------------------------------------------
            # 2d-bis. CYCLISCHE SYMMETRIE (modaal: bridge_cyclic.py)
            # --------------------------------------------------
            elif tag == bridge_cyclic.TAG:
                bridge_cyclic.parse(item, model_data, run_cfg)

            # --------------------------------------------------
            # 2e. ONBEKENDE BELASTINGEN / RANDVOORWAARDEN
            # Mecway kent veel meer typen (manual v33 hoofdstuk 9: moment,
            # traction, frictionless, symmetry, contact, ...). Alles met een
            # selectie dat hierboven niet is afgehandeld, wordt niet
            # vertaald; dat mag niet stil gebeuren.
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
        # STAP 2b: THERMISCH (materialen, belastingen, beginvoorwaarden)
        # ==========================================
        if thermal_run:
            bridge_thermal.parse_thermal(root, model_data)

        # ==========================================
        # STAP 2c: AKOESTIEK (geluidssnelheid, drukknopen)
        # ==========================================
        if acoustic_run:
            bridge_acoustic.parse_acoustic(root, model_data)
        elif not thermal_run:
            # Vibro-akoestiek: fluidum-onderdelen (materiaal met
            # geluidssnelheid zonder E, of LUCHT_/FLUID_), OPEN_, KOPPEL_.
            bridge_vibroacoustic.parse_vibro(root, model_data, run_cfg)

        # ==========================================
        # STAP 3: SECTIE-EIGENSCHAPPEN PER ELSET BEPALEN
        # ==========================================
        spring_mat_names = set(model_data["spring_materials"].keys())

        for elset_name, mat_name in model_data["elsets"].items():
            dim = model_data["elset_dims"].get(elset_name, "3D")

            # --- Veer-elementen -> DIS_T ---
            if mat_name in spring_mat_names:
                if dim == "1D":
                    k = model_data["spring_materials"][mat_name]
                    model_data["spring_sections"][elset_name] = {
                        "spring_constant": k}
                    model_data["elset_modelisations"][elset_name] = "DIS_T"
                    log("INFO: Veer '{0}': k={1} N/m -> DIS_T".format(
                        elset_name, k))
                else:
                    log(tr("WARNING: Veer-materiaal op niet-1D elset '{0}' "
                           "(dim={1}). Overgeslagen.",
                           "WARNING: Spring material on non-1D elset '{0}' "
                           "(dim={1}). Skipped.").format(elset_name, dim))
                continue

            # --- Gap / damper -> DIS_T op SEG2 ---
            if mat_name in model_data["line_discretes"]:
                if dim == "1D":
                    model_data["discrete_sections"][elset_name] = dict(
                        model_data["line_discretes"][mat_name])
                    model_data["elset_modelisations"][elset_name] = "DIS_T"
                else:
                    _not_translated(model_data, "elset '{0}'".format(
                        elset_name), tr("Gap/Damper alleen op line2;",
                                        "Gap/Damper only on line2;"))
                continue

            # --- Tension only -> CABLE ---
            props = model_data["materials"].get(mat_name, {})
            if props.get("tension_only"):
                geom = model_data["mat_geometrics"].get(mat_name, {})
                area = _section_area(geom)
                if dim != "1D" or not area:
                    _not_translated(model_data, "tension-only elset '{0}'"
                                    .format(elset_name),
                                    tr("alleen line2 met een doorsnede;",
                                       "only line2 with a cross-section;"))
                    model_data["elset_modelisations"].pop(elset_name, None)
                    continue
                model_data["cable_sections"][elset_name] = {"area": area}
                model_data["elset_modelisations"][elset_name] = "CABLE"
                log("INFO: Tension-only elset '{0}' -> CABLE, A={1} m2."
                    .format(elset_name, area))
                continue

            # --- Truss -> BARRE (_split_trusses) ---
            # Alleen het doorsnede-oppervlak telt (normaalkracht E A en
            # massa rho A); Code-Aster: AFFE_CARA_ELEM BARRE=_F(GROUP_MA,
            # SECTION='GENERALE', CARA='A', VALE=A) (catalogus
            # affe_cara_elem.py; testcases ssnl105a, sdnl138a). In
            # beam_sections met "truss": True, zodat bridge_mesh de naam
            # meeneemt bij het hernoemen.
            if model_data["elset_modelisations"].get(elset_name) == "BARRE":
                geom = model_data["mat_geometrics"].get(mat_name, {})
                area = _section_area(geom)
                if dim != "1D" or not area:
                    _not_translated(model_data, "truss elset '{0}'"
                                    .format(elset_name),
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
                log("INFO: Truss-elset '{0}' -> BARRE, A={1} m2.".format(
                    elset_name, area))
                continue

            # --- Reguliere balk / schaal / 3D ---
            geom = model_data["mat_geometrics"].get(mat_name)
            if geom is None:
                continue

            if dim == "1D":
                if "aster_section" in geom:
                    if model_data["elset_modelisations"].get(
                            elset_name) == "POU_D_T":
                        geom = _add_shear_coefs(elset_name, geom)
                    geom = dict(geom, area=_section_area(geom))
                    model_data["beam_sections"][elset_name] = geom
                    log("INFO: Balksectie '{0}': {1}".format(
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
                    log("INFO: Plaatdikte '{0}': {1} m".format(
                        elset_name, geom["thickness"]))
                else:
                    log(tr("WARNING: Elset '{0}' is 2D maar '{1}' heeft geen "
                           "dikte.",
                           "WARNING: Elset '{0}' is 2D but '{1}' has no "
                           "thickness.").format(
                               elset_name, geom.get("geom_type", "?")))

        # line3 alleen als balk: bridge_mesh splitst line3-balken in twee
        # SEG2-cellen (POU_D_E/POU_D_T bestaan alleen op SEG2). Truss, veer,
        # gap, demper en tension-only staan in Mecway alleen op line2
        # (manual v33 par. 7.6-7.10); twee staven of veren in serie zouden
        # een mechanisme of de halve stijfheid geven, dus melden.
        if not thermal_run:
            for elset_name, mod in sorted(
                    model_data["elset_modelisations"].items()):
                if ("line3" in elset_shapes_map.get(elset_name, ()) and
                        model_data["elset_dims"].get(elset_name) == "1D" and
                        mod not in ("POU_D_E", "POU_D_T")):
                    _not_translated(
                        model_data,
                        tr("elset '{0}': line3-elementen ({1})",
                           "elset '{0}': line3 elements ({1})").format(
                               elset_name, mod),
                        tr("alleen line3-balken worden vertaald; truss, "
                           "veer, gap, demper en tension-only alleen op "
                           "line2 (zoals Mecway);",
                           "only line3 beams are translated; truss, spring, "
                           "gap, damper and tension-only only on line2 "
                           "(as in Mecway);"))

        # BARRE is in Code-Aster 17.4 geometrisch lineair: een staaf die
        # star 30 graden draait gaf met DEFORMATION='GROT_GDEP' dezelfde
        # normaalkracht als met 'PETIT' (-2,68e6 N, run), zonder melding,
        # en een gespannen staaf heeft geen dwarsstijfheid (singuliere
        # matrix bij Samples/SaggingCable.liml). Zoals balken (POU_D_E)
        # dus kleine verplaatsingen; melden bij grote.
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

        # Elsets met een VOID-materiaal (OpenRadioss) niet in het model
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

        # ==========================================
        # STAP 4: has_rot_dofs VOOR HET MODEL + BC-HERBEREKENING
        # ==========================================
        model_data["has_rot_dofs"] = any(
            mod in _ROT_DOF_MODELISATIONS
            for mod in model_data["elset_modelisations"].values()
        )
        log("INFO: Definitieve has_rot_dofs = {0}".format(
            model_data["has_rot_dofs"]))

        # Velocity: verplaatsing tot de eindtijd van de analyse
        t_end = model_data["timesteps"].get("period", 1.0)
        for bc in model_data["bcs"]:
            if bc["type"] == "velocity":
                bc["params"]["_t_end"] = t_end

        # Herbereken aster_dict voor alle BCs met de definitieve vlag
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
        # Niet doorgaan met een half model: alles na de fout (materialen,
        # BC's, ...) zou stil ontbreken.
        log(tr("ERROR: Fout bij parsen XML van '{0}': {1}: {2}. De .liml "
               "kan niet worden vertaald.",
               "ERROR: Error while parsing XML of '{0}': {1}: {2}. The "
               ".liml cannot be translated.").format(
            file_path, type(e).__name__, str(e)))
        return None

    return model_data
