# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_failure.py
# Responsibility: failure of elements in STAT_NON_LINE and
# DYNA_NON_LINE ("implicit element deletion"): an element whose
# plastic strain reaches a limit gets a very soft material and its
# stress becomes zero. Code-Aster itself has no element deletion (KNOWN_BUGS 9);
# this follows the approach from the literature in which failed elements in
# an implicit analysis get a negligible stiffness instead of
# disappearing (e.g. PMC9821832).
#
# Operation in the .comm (build_solve_block):
#   0. A line BRIDGE_TEND <end time> in the .mess (convergence monitor:
#      progress over the whole loop, bridge_convergence).
#   1. STAT_NON_LINE per time step of 'times' (INST_INIT/INST_FIN, with
#      reuse=res: one result with all steps).
#   2. After each step, per elset the equivalent plastic strain from
#      VARI_ELGA, averaged over the integration points of an element.
#      Average >= limit: the element fails.
#      - isotropic (VMIS_ISOT_LINE/_TRAC): V1 = EPSPEQ (catalogue
#        Behaviours/vmis_isot_*.py), the accumulated plastic strain;
#      - kinematic (VMIS_CINE_LINE): no EPSPEQ; V1..V6 = XCINXX..XCINYZ,
#        the back stress X (catalogue vmis_cine_line.py). X = c epsp with
#        c = 2/3 E Et / (E - Et) (Et = D_SIGM_EPSI): in a test run (hex8,
#        PETIT) X / EPSP_ELGA was 3,34128878e8 in all points, equal to
#        that c, for the normal and the shear components (so the same
#        tensor convention). The strain is sqrt(2/3 X:X) / c: the CURRENT
#        plastic strain, not accumulated (smaller than EPSPEQ under
#        alternating loading; WARNING). With GDEF_LOG (logarithmic strain)
#        the same variables V1..V6 (seen in the .mess); the values were
#        slightly below those with PETIT (0,076..0,078 versus 0,079..0,080
#        at t = 1 s in the tension bar), as ln(1 + e) < e.
#      Shells (DKT, COQUE_3D): VARI_ELGA has subpoints through the thickness
#      (COQUE_NCOU layers, per layer bottom/middle/top; getValuesWithDescription
#      gives cells, components, points and subpoints, seen in a
#      test run). The average runs over all (point, subpoint) pairs of
#      the element, just as for volume elements over all Gauss points
#      (also through the thickness): a measure of the strain in the whole
#      element. In bending the element therefore only fails when the strain
#      averaged over the thickness reaches the limit (surface then above the
#      limit), not at the first fibre (maximum) and not only when the
#      neutral axis yields (minimum, which never reaches the limit in pure
#      bending). With the default COQUE_NCOU = 1 there are 3 subpoints (seen
#      in a test run: 4 Gauss points x 3 subpoints per quad4 DKT).
#   3. For newly failed elements:
#      - group BZ<n>_<k> with all failed cells of elset k
#        (mesh.setGroupOfCells), in a new AFFE_MATERIAU the weak
#        material: E and slope after yielding x failure_stiffness_factor,
#        yield stress unchanged (so the element stays elastic; a soft
#        element that kept yielding had a tangent stiffness of ~1e-9 x E
#        and the matrix became singular, seen in a test run);
#      - stress (SIEF_ELGA) and internal variables to zero (CREA_CHAMP ASSE,
#        GROUP_MA; also sets all subpoints of shells to zero, seen in a
#        test run). With isotropic hardening V1 is kept (the
#        plastic strain in the results). With GDEF_LOG the stress is
#        also in the internal variables (TXX..TYZ: V3..V8 isotropic, V8..V13
#        kinematic, seen in the .mess); setting only SIEF_ELGA to zero gave
#        <IntegrationError> MECANONLINE9_3. With SIMO_MIEHE V3..V8 are
#        SM1..SM6 (catalogue simo_miehe.py; which tensor exactly is NOT
#        verified, in the Simo-Miehe theory the elastic
#        Cauchy-Green tensor): zero is the stress-free initial state (every
#        run without ETAT_INIT starts with VARI = 0, "On prend un état initial
#        nul" in the .mess; during yielding the values were ~1e-3, so
#        a deviation from the identity tensor and not the tensor itself,
#        test run). Setting to zero = back to stress-free, as intended;
#      - the next step starts from those fields (ETAT_INIT DEPL/SIGM/VARI)
#        with NEWTON PREDICTION='ELASTIQUE'. With the default 'TANGENTE'
#        the step after the failure did not converge (residual stayed
#        ~13 kN, at all subdivision levels); with 'ELASTIQUE' it did (test
#        runs, Code-Aster 17.4). Then 'TANGENTE' again ('ELASTIQUE' from the
#        start gave 148 substeps in the first step with GDEF_LOG).
#   4. Each event appears as a BRIDGE_BEZWIJKEN line in the .mess
#      (bridge_run_aster.failure_events reads them).
#
# Limit per material (_criterion), the first that exists:
#   #ASTER-BEZWIJKEN <material> = <strain> (bridge_custom; '*' = all
#                                           plastic materials)
#   OpenRadioss PLAS_TAB Eps_p_max         (bridge_radioss)
#   setting failure_plastic_strain > 0     (all plastic materials)
#
# Dynamics (DYNA_NON_LINE): the same loop, checked at the
# output times (outlist; these are also computation steps, bridge_to_aster.
# _build_dyna_listinst_block). After a failure moment also VITE and ACCE in
# ETAT_INIT. Explicit keeps PREDICTION 'TANGENTE' (MECANONLINE5_1). Implicit (HHT/NEWMARK)
# Code-Aster gives alarm MECANONLINE4_50 for SIGM in ETAT_INIT ("the
# initial acceleration is computed without this stress field"); the bridge
# passes ACCE. Whether that prevents the recomputation is NOT verified; the
# force history in the test run was physically plausible (drop to ~0, ringing).
#
# Limitations (with a message): only volume elements and shells
# (_SUPPORTED_DEFORMATIONS); not beams: Code-Aster has plasticity
# only in multifibre beams (POU_D_EM/POU_D_TGM; <EXCEPTION> POUTRE0_61
# with VMIS_ISOT_LINE on POU_D_E, test run), which the bridge does not make.
# Kinematic hardening without slope (Et = 0: X stays 0, no measure
# of the plastic strain). Only STAT_NON_LINE and DYNA_NON_LINE
# (MECA_STATIQUE: only the message, bridge_to_aster._build_lin_static).
#
# Messages show the Mecway name of an elset (mecway_name); the .comm and
# the BRIDGE_BEZWIJKEN lines use the Code-Aster name.
#
# Compatible with IronPython 2.7.9.

import io
import re
from collections import OrderedDict

from bridge_utils import log, tr, log_file_name

# except clause after STAT_NON_LINE/DYNA_NON_LINE (also the loops here and in
# bridge_thermomech). On every AsterError Code-Aster publishes the current
# result in the namespace of the .comm (ExecuteCommand.exec_: "except
# libaster.AsterError: self.publish_result(); raise", 17.4), so 'res' then
# holds the steps archived before the stop. Seen with 17.4: ConvergenceError
# MECANONLINE9_7, and <F> FONCT0_9 (function evaluation in step 12 of 20):
# INST 0..0.5 present and the post-processing ran. DVP_2 (floating point
# exception in FULL_MECA) is an <F> message from the element computation as
# well (same route as FONCT0_9; DVP_2 itself NIET geverifieerd in a run,
# KNOWN_BUGS 118).
# MECANONLINE*: always continue (as before). Other AsterErrors: only if 'res'
# has an archived step beyond the initial state; otherwise (error before the
# first step, or no 'res') the error is raised again. BRIDGE_FOUT_ID gives
# bridge_run_aster.py the id of the stopping error. No braces: the text is
# part of str.format templates.
PARTIAL_EXCEPT = (
    "except Exception as err:\n"
    "    _pe_id = str(getattr(err, 'id_message', '') or '')\n"
    "    try:\n"
    "        _pe_inst = list(res.getAccessParameters()['INST'])\n"
    "    except Exception:\n"
    "        _pe_inst = []\n"
    "    if not _pe_id or not _pe_inst or not (\n"
    "            _pe_id.startswith('MECANONLINE') or len(_pe_inst) > 1):\n"
    "        raise\n"
    "    print('BRIDGE_FOUT_ID', _pe_id)\n"
    "    print('BRIDGE_ONVOLLEDIG', _pe_inst[-1])\n")

# Per MODELISATION the DEFORMATION forms for which failure has been
# checked with a Code-Aster run (force drop after failure). DKT/COQUE_3D
# with VMIS_ISOT_LINE: 2 internal variables, also with GREEN_LAGRANGE/GROT_GDEP
# (seen in the .mess). DST becomes DKT in nonlinear analyses
# (bridge_from_liml).
_SUPPORTED_DEFORMATIONS = {
    "3D": ("PETIT", "PETIT_REAC", "GDEF_LOG", "SIMO_MIEHE"),
    "3D_SI": ("PETIT", "PETIT_REAC", "GDEF_LOG", "SIMO_MIEHE"),
    "DKT": ("PETIT", "GREEN_LAGRANGE"),
    "COQUE_3D": ("PETIT", "GROT_GDEP"),
}
_ISOTROPIC = ("VMIS_ISOT_LINE", "VMIS_ISOT_TRAC")
_KINEMATIC = "VMIS_CINE_LINE"


def _cine_coefficient(props):
    """c in X = c epsp for VMIS_CINE_LINE: 2/3 E Et / (E - Et) with Et the
    slope after yielding (ECRO_LINE D_SIGM_EPSI); see the header. None if
    there is no hardening (Et <= 0 or Et >= E)."""
    try:
        e_mod = float(props["E"])
        e_t = float(props["plastic_bilinear"]["et"])
    except (KeyError, TypeError, ValueError):
        return None
    if e_t <= 0.0 or e_t >= e_mod:
        return None
    return 2.0 / 3.0 * e_mod * e_t / (e_mod - e_t)


def _is_plastic(props):
    """Does the material have plasticity (and thus a plastic strain)?"""
    return bool(props.get("plastic_curve") or props.get("plastic_bilinear")
                or props.get("eps_p_max"))


def _criterion(mat_name, props, custom, default):
    """(limit, source) for a material, or (None, None). '*' and
    failure_plastic_strain only apply to plastic materials (an
    elastic material or a spring cannot fail; with '*' that gave
    an unjustified WARNING per elastic elset). A material named
    in #ASTER-BEZWIJKEN always passes (failure_plan reports
    it if it is not plastic)."""
    if mat_name in custom:
        return custom[mat_name], "#ASTER-BEZWIJKEN"
    if not _is_plastic(props):
        return None, None
    if "*" in custom:
        return custom["*"], "#ASTER-BEZWIJKEN *"
    if props.get("eps_p_max"):
        return props["eps_p_max"], "PLAS_TAB Eps_p_max"
    if default and default > 0.0:
        return default, "failure_plastic_strain"
    return None, None


def mecway_name(model_data, group):
    """Mecway name of a Code-Aster group (bridge_mesh renames:
    model_data["group_renames"] = {Mecway name: Code-Aster name});
    unknown: unchanged."""
    for src, dst in model_data.get("group_renames", {}).items():
        if dst == group:
            return src
    return group


def failure_candidates(model_data, analysis):
    """Elsets (solid or shell) with a failure limit while 'Element failure'
    is on: those for which failure_plan may build the failure loop. No
    messages (failure_plan gives them); for checks beforehand, e.g.
    bridge_to_aster._check_gd_beams (after a failure the loop restarts with
    PREDICTION='ELASTIQUE', which POU_D_T_GD cannot compute)."""
    if not analysis.get("element_failure", True):
        return []
    custom = model_data.get("aster_custom", {}).get("failure", {})
    default = float(analysis.get("failure_plastic_strain", 0.0) or 0.0)
    materials = model_data.get("materials", {})
    mods = model_data.get("elset_modelisations", {})
    return [elset for elset, mat_name in model_data.get("elsets", {}).items()
            if mods.get(elset, "") in _SUPPORTED_DEFORMATIONS and
            _criterion(mat_name, materials.get(mat_name, {}), custom,
                       default)[0] is not None]


def failure_plan(model_data, analysis, relation_for, deformation_for):
    """
    Which elsets can fail? List of dicts
    {"elset", "material", "limit", "relation", "deformation"}; empty if
    there is nothing to do. What is not possible is reported (WARNING) and
    goes into skipped_loads.

    relation_for(mat_name) and deformation_for(mod, relation, chosen,
    elset) come from bridge_to_aster (no circular import).
    """
    custom = model_data.get("aster_custom", {}).get("failure", {})
    default = float(analysis.get("failure_plastic_strain", 0.0) or 0.0)
    materials = model_data["materials"]
    for name in custom:
        if name != "*" and name not in materials:
            log(tr("ERROR: #ASTER-BEZWIJKEN: materiaal '{0}' bestaat niet "
                   "in het model; genegeerd. Bekend: {1}",
                   "ERROR: #ASTER-BEZWIJKEN: material '{0}' does not exist "
                   "in the model; ignored. Known: {1}").format(
                       name, ", ".join(materials)))
    wanted = OrderedDict()
    label = dict((g, mecway_name(model_data, g))
                 for g in model_data["elsets"])
    for elset, mat_name in model_data["elsets"].items():
        limit, source = _criterion(mat_name, materials.get(mat_name, {}),
                                   custom, default)
        if limit is not None:
            wanted[elset] = (mat_name, limit, source)
    if not wanted:
        return []
    skipped = model_data.setdefault("skipped_loads", [])
    if not analysis.get("element_failure", True):
        log(tr("WARNING: Bezwijkgrenzen in het model ({0}), maar "
               "'Bezwijken van elementen' staat uit: elementen bezwijken "
               "niet.",
               "WARNING: Failure limits in the model ({0}), but 'Element "
               "failure' is off: elements do not fail.").format(
                   ", ".join(label[g] for g in wanted)))
        skipped.append(tr("bezwijken van elementen (instelling uit)",
                          "element failure (setting off)"))
        return []
    if analysis.get("solver_command", "STAT_NON_LINE") not in (
            "STAT_NON_LINE", "DYNA_NON_LINE"):
        log(tr("WARNING: Bezwijken van elementen kan de bridge alleen in "
               "niet-lineaire analyses (STAT_NON_LINE, DYNA_NON_LINE); in "
               "deze analyse bezwijken {0} niet.",
               "WARNING: The bridge supports element failure only in "
               "nonlinear analyses (STAT_NON_LINE, DYNA_NON_LINE); in "
               "this analysis {0} do not fail.").format(
                   ", ".join(label[g] for g in wanted)))
        skipped.append(tr("bezwijken van {0} (alleen niet-lineair)",
                          "failure of {0} (nonlinear only)")
                       .format(", ".join(label[g] for g in wanted)))
        return []
    chosen = analysis.get("deformation", "PETIT")
    mods = model_data.get("elset_modelisations", {})
    plan = []
    for elset, (mat_name, limit, source) in wanted.items():
        relation = relation_for(mat_name)
        mod = mods.get(elset, "")
        reason = None
        coef = None
        if relation == _KINEMATIC:
            coef = _cine_coefficient(materials.get(mat_name, {}))
            if coef is None:
                reason = tr("kinematische versteviging zonder helling na "
                            "vloeien (tangent modulus 0): de terugspanning "
                            "blijft 0 en geeft geen maat voor de plastische "
                            "rek; geef een tangent modulus > 0 of kies "
                            "isotrope versteviging",
                            "kinematic hardening without a slope after "
                            "yield (tangent modulus 0): the back stress "
                            "stays 0 and gives no measure of the plastic "
                            "strain; give a tangent modulus > 0 or choose "
                            "isotropic hardening")
        elif relation not in _ISOTROPIC:
            reason = tr("het materiaal is niet plastisch (geen plastische "
                        "rek)",
                        "the material is not plastic (no plastic strain)")
        if reason is None and mod.startswith("POU_D"):
            # <EXCEPTION> POUTRE0_61 with VMIS_ISOT_LINE on POU_D_E (test run)
            reason = tr("balken ({0}) niet: Code-Aster kent plasticiteit "
                        "alleen in multivezelbalken, die de bridge niet "
                        "maakt",
                        "beams ({0}) not: Code-Aster supports plasticity "
                        "only in multifiber beams, which the bridge does "
                        "not create").format(mod)
        elif reason is None and mod not in _SUPPORTED_DEFORMATIONS:
            reason = tr("alleen volume-elementen en schalen ({0} niet)",
                        "solid and shell elements only ({0} not)").format(
                            mod or "?")
        deformation = None
        if reason is None:
            deformation = deformation_for(mod, relation, chosen, elset)
            if deformation not in _SUPPORTED_DEFORMATIONS[mod]:
                reason = tr("DEFORMATION={0} niet ondersteund bij {1} (wel "
                            "{2})",
                            "DEFORMATION={0} not supported with {1} ({2} "
                            "are)").format(
                                deformation, mod,
                                ", ".join(_SUPPORTED_DEFORMATIONS[mod]))
        if reason:
            log(tr("WARNING: Elset '{0}' ({1}, grens {2} uit {3}) kan niet "
                   "bezwijken: {4}.",
                   "WARNING: Elset '{0}' ({1}, limit {2} from {3}) cannot "
                   "fail: {4}.").format(label[elset], mat_name, limit,
                                        source, reason))
            skipped.append(tr("bezwijken van elset {0}",
                              "failure of elset {0}").format(label[elset]))
            continue
        log("INFO: Failure: elset '{0}' ({1}) at a plastic strain of "
            "{2} ({3}).".format(label[elset], mat_name, limit, source))
        if coef is not None:
            log(tr("WARNING: Elset '{0}' ({1}) heeft kinematische "
                   "versteviging: de bezwijkgrens geldt voor de huidige "
                   "plastische rek (uit de terugspanning), niet voor de "
                   "opgetelde. Bij wisselende belasting bezwijkt het "
                   "element later dan met isotrope versteviging.",
                   "WARNING: Elset '{0}' ({1}) has kinematic hardening: "
                   "the failure limit applies to the current plastic "
                   "strain (from the back stress), not the accumulated "
                   "one. Under alternating load the element fails later "
                   "than with isotropic hardening.").format(
                       label[elset], mat_name))
        plan.append({"elset": elset, "material": mat_name, "limit": limit,
                     "relation": relation, "deformation": deformation,
                     "cine_coef": coef})
    return plan


def weak_materials(model_data, plan, factor, concepts, elas_args, curves,
                   mat_comment):
    """
    DEFI_MATERIAU per material in plan: <MAT_n>_BZ. E and the slope after
    yielding x factor, yield stress unchanged: the soft element stays
    elastic. TRACTION: strain / factor and the same stress, so that the
    first point (sy / (E factor), sy) fits the new E and the slope
    stays smaller than E (U4.43.01 TRACTION).

    elas_args(props, factor) -> text for ELAS=_F(...); curves: {material:
    [(strain, stress)]} as in TRAC_<n>; mat_comment: comment line.
    Returns (text, {material: concept name}).
    """
    out = ""
    names = OrderedDict()
    for item in plan:
        mat_name = item["material"]
        if mat_name in names:
            continue
        props = model_data["materials"][mat_name]
        concept = concepts[mat_name] + "_BZ"
        names[mat_name] = concept
        extra = ""
        if mat_name in curves:
            func = concept.replace("MAT_", "TRAC_", 1)
            vale = ",\n          ".join(
                "{0!r}, {1!r}".format(e / factor, s)
                for e, s in curves[mat_name])
            out += ("{0} = DEFI_FONCTION(\n    NOM_PARA='EPSI',\n"
                    "    NOM_RESU='SIGM',\n    VALE=({1}),\n"
                    "    PROL_DROITE='LINEAIRE',\n"
                    "    PROL_GAUCHE='CONSTANT',\n)\n").format(func, vale)
            extra = "    TRACTION=_F(SIGM={0}),\n".format(func)
        else:
            bil = props["plastic_bilinear"]
            extra = "    ECRO_LINE=_F(D_SIGM_EPSI={0!r}, SY={1!r}),\n".format(
                bil["et"] * factor, bil["sy"])
        out += mat_comment(mat_name) + (
            "# failed: E x {0!r}, yield stress unchanged (stays "
            "elastic)\n".format(factor))
        out += "{0} = DEFI_MATERIAU(\n    ELAS=_F({1}),\n{2})\n".format(
            concept, elas_args(props, factor), extra)
    return out, names


def build_solve_block(plan, weak_names, affe_entries, varc, call_args):
    """
    Python code for the .comm: the failure loop instead of a single
    STAT_NON_LINE (see the header of this file).

    weak_names  : {material: concept} from weak_materials
    affe_entries: lines "        _F(GROUP_MA=..., MATER=...),\n" of the
                  normal AFFE_MATERIAU (bridge_to_aster._fieldmat_parts)
    varc        : AFFE_VARC lines of that AFFE_MATERIAU (or "")
    call_args   : dict with
                  "args"     : arguments of the solve without MODELE,
                               CHAM_MATER, INCREMENT, NEWTON and ETAT_INIT;
                  "newton"   : text inside NEWTON=_F(...);
                  "command"  : STAT_NON_LINE or DYNA_NON_LINE;
                  "segments" : Python expression with the times at which
                               failure is checked (start incl.);
                  "first"    : Python expression with extra arguments of
                               the first call (e.g. the initial velocity);
                  "dynamic"  : True: VITE and ACCE in the initial state
                               after a failure moment.
    """
    crit = "".join("    ({0!r}, {1!r}, {2}, {3}),\n".format(
        p["elset"], float(p["limit"]), weak_names[p["material"]],
        repr(float(p["cine_coef"])) if p.get("cine_coef") else "None")
        for p in plan)
    varc_args = "".join("        " + line.strip() + "\n"
                        for line in varc.splitlines() if line.strip())
    affe = "".join("    " + line.strip() + "\n"
                   for line in affe_entries)
    return (
        "# --- Element failure (bridge_failure.py) ---\n"
        "# Per time step: elements with a mean plastic strain (V1,\n"
        "# or from the back stress X with VMIS_CINE_LINE) above the limit\n"
        "# get the soft material and zero stress.\n"
        "import numpy as _bz_np\n"
        "# (elset, plastic strain limit, soft material, c): c = None:\n"
        "# isotropic, strain = V1 (EPSPEQ); otherwise VMIS_CINE_LINE with\n"
        "# X = c epsp (V1..V6), strain = sqrt(2/3 X:X) / c (current strain)\n"
        "_bz_crit = [\n"
        "{crit}]\n"
        "_bz_affe = [\n{affe}]\n"
        "_bz_inst = {segments}\n"
        "# end time for the progress in the convergence monitor\n"
        "print('BRIDGE_TEND %r' % float(_bz_inst[-1]))\n"
        "_bz_failed = {{}}   # elset -> set of cells (0-based)\n"
        "_bz_events = []   # (time, new cells): export_results(failures=)\n"
        "_bz_fm = fieldmat\n"
        "_bz_extra = {first}\n"
        "_bz_pred = 'TANGENTE'\n"
        "_bz_n = 0\n"
        "try:\n"
        "    for _bz_i in range(1, len(_bz_inst)):\n"
        "        res = {command}(\n"
        "            MODELE=model,\n"
        "            CHAM_MATER=_bz_fm,\n"
        "{args}"
        "            INCREMENT=_F(LIST_INST=listinst,\n"
        "                         INST_INIT=_bz_inst[_bz_i - 1],\n"
        "                         INST_FIN=_bz_inst[_bz_i]),\n"
        "            NEWTON=_F({newton}, PREDICTION=_bz_pred),\n"
        "            **_bz_extra)\n"
        "        _bz_last = res.getLastIndex()\n"
        "        _bz_vari = res.getField('VARI_ELGA', _bz_last)\n"
        "        _bz_new = {{}}\n"
        "        for _bz_g, _bz_lim, _bz_w, _bz_c in _bz_crit:\n"
        "            _v, _d = _bz_vari.getValuesWithDescription(['V1'], [_bz_g])\n"
        "            _v = _bz_np.asarray(_v)\n"
        "            if _bz_c is not None:\n"
        "                _x = [_v] + [_bz_np.asarray(_bz_vari.getValuesWithDescription(\n"
        "                    [_k], [_bz_g])[0]) for _k in ('V2', 'V3', 'V4', 'V5', 'V6')]\n"
        "                _v = _bz_np.sqrt(2.0 / 3.0 * (\n"
        "                    _x[0] ** 2 + _x[1] ** 2 + _x[2] ** 2 +\n"
        "                    2.0 * (_x[3] ** 2 + _x[4] ** 2 + _x[5] ** 2))) / _bz_c\n"
        "            _c = _bz_np.asarray(_d[0])\n"
        "            for _cell in _bz_np.unique(_c):\n"
        "                if (int(_cell) not in _bz_failed.get(_bz_g, ()) and\n"
        "                        _v[_c == _cell].mean() >= _bz_lim):\n"
        "                    _bz_new.setdefault(_bz_g, []).append(int(_cell))\n"
        "        if not _bz_new:\n"
        "            _bz_extra = dict(reuse=res, RESULTAT=res,\n"
        "                             ETAT_INIT=_F(EVOL_NOLI=res))\n"
        "            _bz_pred = 'TANGENTE'\n"
        "            continue\n"
        "        _bz_n += 1\n"
        "        _bz_groups = []\n"
        "        _bz_more = []\n"
        "        _bz_keep = []   # groups in which V1 (EPSPEQ) stays\n"
        "        for _k, (_bz_g, _bz_lim, _bz_w, _bz_c) in enumerate(_bz_crit):\n"
        "            _bz_failed.setdefault(_bz_g, set()).update(\n"
        "                _bz_new.get(_bz_g, []))\n"
        "            if _bz_g in _bz_new:\n"
        "                # cells: Code-Aster cell numbers (0-based); the bridge\n"
        "                # translates them to Mecway elements (failure_events)\n"
        "                print('BRIDGE_BEZWIJKEN t=%r elset=%s nieuw=%d totaal=%d "
        "cellen=%s' % (\n"
        "                    _bz_inst[_bz_i], _bz_g, len(_bz_new[_bz_g]),\n"
        "                    len(_bz_failed[_bz_g]),\n"
        "                    ','.join(str(c) for c in sorted(_bz_new[_bz_g]))))\n"
        "                _bz_events.append((float(_bz_inst[_bz_i]),\n"
        "                                   sorted(_bz_new[_bz_g])))\n"
        "            if _bz_failed[_bz_g]:\n"
        "                _nm = 'BZ%d_%d' % (_bz_n, _k + 1)\n"
        "                mesh.setGroupOfCells(_nm, sorted(_bz_failed[_bz_g]))\n"
        "                _bz_groups.append(_nm)\n"
        "                _bz_more.append(_F(GROUP_MA=_nm, MATER=_bz_w))\n"
        "                if _bz_c is None:\n"
        "                    _bz_keep.append(_nm)\n"
        "        _bz_fm = AFFE_MATERIAU(\n"
        "            MAILLAGE=mesh,\n"
        "            MODELE=model,\n"
        "            AFFE=tuple(_bz_affe + _bz_more),\n"
        "{varc})\n"
        "        _bz_sig = res.getField('SIEF_ELGA', _bz_last)\n"
        "        _bz_sig0 = CREA_CHAMP(\n"
        "            OPERATION='ASSE', TYPE_CHAM='ELGA_SIEF_R', MODELE=model,\n"
        "            PROL_ZERO='OUI',\n"
        "            ASSE=(_F(CHAM_GD=_bz_sig, TOUT='OUI'),\n"
        "                  _F(CHAM_GD=_bz_sig, GROUP_MA=tuple(_bz_groups),\n"
        "                     COEF_R=0.0)))\n"
        "        _bz_asse = [_F(CHAM_GD=_bz_vari, TOUT='OUI'),\n"
        "                    _F(CHAM_GD=_bz_vari, GROUP_MA=tuple(_bz_groups),\n"
        "                       COEF_R=0.0)]\n"
        "        if _bz_keep:\n"
        "            _bz_asse.append(_F(CHAM_GD=_bz_vari, GROUP_MA=tuple(_bz_keep),\n"
        "                               NOM_CMP=('V1',)))\n"
        "        _bz_vari0 = CREA_CHAMP(\n"
        "            OPERATION='ASSE', TYPE_CHAM='ELGA_VARI_R', MODELE=model,\n"
        "            PROL_ZERO='OUI', ASSE=tuple(_bz_asse))\n"
        "        _bz_extra = dict(reuse=res, RESULTAT=res, ETAT_INIT=_F(\n"
        "            DEPL=res.getField('DEPL', _bz_last), SIGM=_bz_sig0,\n"
        "{dyn_fields}"
        "            VARI=_bz_vari0))\n"
        "        _bz_pred = '{after_pred}'\n"
        + PARTIAL_EXCEPT +
        "print('BRIDGE_BEZWIJKEN_TOTAAL %d' % sum(len(c) for c in "
        "_bz_failed.values()))\n"
        "t_res = res.getAccessParameters()['INST'][-1]\n"
    ).format(crit=crit, affe=affe, args=call_args["args"],
             newton=call_args["newton"], varc=varc_args,
             command=call_args.get("command", "STAT_NON_LINE"),
             segments=call_args.get("segments",
                                    "list(times.getValues())"),
             first=call_args.get("first", "{}"),
             # Explicit (DIFF_CENT/TCHAMWA) only allows TANGENTE
             # (<EXCEPTION> MECANONLINE5_1, seen with 17.4).
             after_pred=("TANGENTE" if call_args.get("explicit")
                         else "ELASTIQUE"),
             dyn_fields=(
                 "            VITE=res.getField('VITE', _bz_last),\n"
                 "            ACCE=res.getField('ACCE', _bz_last),\n"
                 if call_args.get("dynamic") else ""))


# ==========================================
# AFTER THE RUN: WHICH ELEMENTS FAILED?
# ==========================================
_EVENT_RE = re.compile(r"^BRIDGE_BEZWIJKEN t=(\S+) elset=(\S+) nieuw=(\d+) "
                       r"totaal=(\d+) cellen=([\d,]*)\s*$", re.M)


def failure_events(mess_text, cell_names):
    """
    BRIDGE_BEZWIJKEN lines from the .mess: list of (time, elset,
    [Mecway element numbers]). cell_names: model_data["cell_names"]
    (bridge_mesh); an unknown cell number stays '#<nr>'.
    """
    events = []
    for m in _EVENT_RE.finditer(mess_text):
        eids = []
        for c in m.group(5).split(","):
            if not c:
                continue
            c = int(c)
            name = cell_names[c] if 0 <= c < len(cell_names) else None
            # H<eid>: second half of a split line3 beam (bridge_mesh)
            eid = (name[1:] if name and name[:1] in ("M", "H")
                   else "#{0}".format(c))
            if eid not in eids:
                eids.append(eid)
        events.append((float(m.group(1)), m.group(2), eids))
    return events


def report_failures(mess_path, model_data):
    """
    Log the failed elements of a run (WARNING per event) and return
    a short text for mw.message ("" without failure).
    """
    try:
        f = io.open(mess_path, encoding="utf-8", errors="replace")
        try:
            text = f.read()
        finally:
            f.close()
    except (IOError, OSError):
        return ""
    events = failure_events(text, model_data.get("cell_names", []))
    if not events:
        return ""
    total = 0
    for t, elset, eids in events:
        total += len(eids)
        shown = ", ".join(eids[:50]) + (" ..." if len(eids) > 50 else "")
        log(tr("WARNING: Bezwijken bij t={0}: {1} element(en) van elset "
               "'{2}': {3}",
               "WARNING: Failure at t={0}: {1} element(s) of elset '{2}': "
               "{3}").format("%g s" % t, len(eids),
                             mecway_name(model_data, elset), shown))
    # %g (no '{:g}': IronPython printed '{:.4g}' as 0, seen in an
    # IronPython test)
    when = ("t=%g s" % events[0][0] if events[0][0] == events[-1][0]
            else "t=%g .. %g s" % (events[0][0], events[-1][0]))
    return tr("Bezwijken: {0} element(en) bezweken ({1}); hun spanning is "
              "~0. De elementnummers staan in {2}.",
              "Failure: {0} element(s) failed ({1}); their stress is ~0. "
              "The element numbers are in {2}.").format(
                  total, when, log_file_name())
