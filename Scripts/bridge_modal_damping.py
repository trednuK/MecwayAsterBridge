# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_modal_damping.py
# Responsibility: modal analysis with damping (complex modes), the
# setting modal_complex of modal_3d (Mecway V30). Helper functions for
# bridge_to_aster._build_modal:
#   plan(model_data, analysis, buckling) - None (real modes, like Mecway)
#                                 or {"alpha", "beta", "dampers"}
#   assemblage_entry(plan)       - AMOR_MECA of the dampers in ASSEMBLAGE
#   damping_block(plan)          - the damping matrix 'amor'
#   calc_modes_lines(...)        - MATR_AMOR and CALC_MODES search options
#   zero_damping_entries(...)    - A_* entries 0 for other discrete elements
#
# Behaviour of Mecway (measured headless with Mecway 33, mw_solve.py, 7 Oct
# 2026; docs/Modaal_en_knik.md sec. 6): a Frequency analysis (V30) ignores
# Rayleigh damping (mass on a beam with alpha = 3,55 1/s: the same
# frequencies 5,6494 / 8,4741 / 564,94 Hz as without, no decay rate) and
# computes no solution with a Damper element (line2); according to the
# manual, Rayleigh only belongs to Dynamic Response (manual v33 sec. 9.26
# "Analysis types"). Mecway only knows complex modes in acoustics with
# impedance (sec. 6.9.2): <mode frequency=".. Hz" decayrate=".. 1/s"> with
# the frequency = Im(s)/2pi and decay rate = -Re(s) of the eigenvalue s
# (seen headless: tube with Z = 2000 Pa.s/m, decayrate 70,35 1/s =
# (c/L) artanh(rho c/Z)). The bridge uses that format here as well.
#
# Code-Aster (catalogue calc_modes.py v17.4; test cases sdld21c, sdld23a,
# sdld27a): CALC_MODES TYPE_RESU='DYNAMIQUE' with MATR_AMOR (matr_asse_depl_r)
# solves the quadratic eigenvalue problem (K + s C + s^2 M) phi = 0;
# the result is a MODE_MECA_C with complex DEPL. Measured (mass 10 kg
# on a beam, k = 12 600 N/m, damper c = 213 N.s/m, zeta = 0,3):
#   FREQ = the DAMPED frequency Im(s)/2pi (5,38919 = 5,64944 sqrt(1 -
#   0,09) Hz) and AMOR_REDUIT = zeta = -Re(s)/|s| (0,29999), in the table
#   (RECU_TABLE NOM_PARA AMOR_REDUIT; not in getAccessParameters).
#   Only valid for underdamped modes; overdamped modes (real
#   eigenvalues) are not included: alarm ALGELINE5_79 (fewer modes
#   than requested; seen with beta = 0,017 s on the axial mode, zeta = 30).
#   SORENSEN with OPTION='PLUS_PETITE' fails (<EXCEPTION> ALGELINE2_71:
#   "la borne inferieure ... est nulle"); TRI_DIAG and QZ are (equal to
#   1e-9), SORENSEN with 'CENTRE' as well.
#
# Compatible with IronPython 2.7.9 (standard library only).

import re

from bridge_utils import log, tr


def _dampers(model_data):
    """Elsets with Mecway Damper material (line2, DIS_T A_T_D_L)."""
    return sorted(e for e, s in model_data.get("discrete_sections",
                                                {}).items()
                  if s.get("kind") == "damper")


def _rayleigh(model_data):
    """(alpha [1/s], beta [s]) of Mecway's Rayleigh damping (the whole
    model, bridge_from_liml), or (0, 0)."""
    ray = model_data.get("rayleigh") or {}
    return (float(ray.get("alpha", 0.0) or 0.0),
            float(ray.get("beta", 0.0) or 0.0))


def plan(model_data, analysis, buckling):
    """
    None: real modes without damping (like Mecway, default). Otherwise a
    dict {"alpha", "beta", "dampers"} for complex modes: setting
    modal_complex on and damping in the model (Rayleigh and/or dampers).
    Then sets model_data["damping_matrix"] (bridge_to_aster._build_cara_elem
    _block: damping characteristic 0 for the other discrete elements,
    otherwise alarm DISCRETS_28 per nodal mass).
    """
    if buckling:
        return None
    alpha, beta = _rayleigh(model_data)
    dampers = _dampers(model_data)
    what = []
    if alpha or beta:
        what.append(tr("Rayleigh-demping (alpha {0} 1/s, beta {1} s)",
                       "Rayleigh damping (alpha {0} 1/s, beta {1} s)").format(
                           "%.6g" % alpha, "%.6g" % beta))
    if dampers:
        what.append(tr("dempers ({0})", "dampers ({0})").format(
            ", ".join(dampers)))
    if not analysis.get("modal_complex", False):
        if what:
            log(tr("INFO: Modaal: {0} telt niet mee: reele modes zonder "
                   "demping, zoals Mecway's Frequency-analyse. Voor de "
                   "gedempte frequentie en de dempingsverhouding per mode: "
                   "zet 'Complexe modes met demping' aan (pagina Modaal).",
                   "INFO: Modal: {0} is not included: real modes without "
                   "damping, like Mecway's Frequency analysis. For the "
                   "damped frequency and the damping ratio per mode: switch "
                   "on 'Complex modes with damping' (Modal page).").format(
                       tr(" en ", " and ").join(what)))
        return None
    if not what:
        log(tr("INFO: Complexe modes gevraagd, maar het model heeft geen "
               "demping (Rayleigh of dempers): reele modes.",
               "INFO: Complex modes requested, but the model has no "
               "damping (Rayleigh or dampers): real modes."))
        return None
    if alpha < 0.0 or beta < 0.0:
        log(tr("WARNING: Negatieve Rayleigh-coefficient (alpha {0}, beta "
               "{1}): negatieve demping, modes kunnen aangroeien.",
               "WARNING: Negative Rayleigh coefficient (alpha {0}, beta "
               "{1}): negative damping, modes may grow.").format(
                   "%.6g" % alpha, "%.6g" % beta))
    model_data["damping_matrix"] = True
    log(tr("INFO: Complexe modes (kwadratisch eigenwaardeprobleem, "
           "CALC_MODES met MATR_AMOR) met {0}: C = {1}.",
           "INFO: Complex modes (quadratic eigenvalue problem, CALC_MODES "
           "with MATR_AMOR) with {0}: C = {1}.").format(
               tr(" en ", " and ").join(what), _c_text(alpha, beta, dampers)))
    return {"alpha": alpha, "beta": beta, "dampers": dampers}


def _c_text(alpha, beta, dampers):
    terms = []
    if alpha:
        terms.append("alpha M")
    if beta:
        terms.append("beta K")
    if dampers:
        terms.append("C_dempers")
    return " + ".join(terms)


def assemblage_entry(plan_):
    """ASSEMBLAGE entry for the dampers: AMOR_MECA gives the A_T_D_L of the
    DIS_T elements (test case sdld21c). Without Rayleigh in DEFI_MATERIAU
    (bridge_to_aster._build_materials_block only sets AMOR_ALPHA/BETA for
    DYNA_NON_LINE) the other elements contribute nothing (measured: beam +
    damper, zeta of the mode without damper 1e-12)."""
    if not plan_ or not plan_["dampers"]:
        return ""
    return "        _F(MATRICE=CO('amor_dis'), OPTION='AMOR_MECA'),\n"


def damping_block(plan_):
    """
    The damping matrix 'amor' after ASSEMBLAGE (and after the prestressed
    stiffness): C = alpha M + beta K (Mecway manual v33 sec. 9.26, the whole
    model, so also nodal masses and springs) + C_dampers. K is the stiffness
    of the eigenvalue problem ('rigidite'; with prestress K + Kg), so that
    for Rayleigh zeta_i = alpha / (2 w_i) + beta w_i / 2 with w_i the
    undamped natural frequency, as in the response on a modal basis
    (bridge_dyna_modal._dyna_block). COMB_MATR_ASSE with the
    Lagrange degrees of freedom of the supports works (measured: alpha M and
    beta K on a clamped beam, zeta 0,30000 / 0,20000 / 0,0030000 =
    alpha / 2w per mode).
    """
    if not plan_:
        return ""
    terms = []
    if plan_["alpha"]:
        terms.append(("masse", plan_["alpha"]))
    if plan_["beta"]:
        terms.append(("rigidite", plan_["beta"]))
    if plan_["dampers"]:
        terms.append(("amor_dis", 1.0))
    head = ("# Damping matrix for the complex modes (setting "
            "modal_complex):\n# C = {0} (bridge_modal_damping)\n".format(
                _c_text(plan_["alpha"], plan_["beta"], plan_["dampers"])))
    if terms == [("amor_dis", 1.0)]:
        return head + "amor = amor_dis\n"
    return head + "amor = COMB_MATR_ASSE(COMB_R=(\n{0}))\n".format("".join(
        "    _F(MATR_ASSE={0}, COEF_R={1!r}),\n".format(m, float(c))
        for m, c in terms))


def calc_modes_lines(n, shift, free):
    """
    Lines for CALC_MODES with damping (after MATR_MASS): MATR_AMOR, OPTION,
    CALC_FREQ and SOLVEUR_MODAL. shift: modal_shift_hz; free: no
    supports (the bridge then searches around -bridge_fshift,
    bridge_to_aster._FREE_SHIFT_BLOCK).
      shift 0 and supported: PLUS_PETITE with TRI_DIAG (Lanczos; SORENSEN
        cannot use PLUS_PETITE for a quadratic problem, ALGELINE2_71);
      otherwise: CENTRE with SORENSEN (test case sdld21c).
    """
    lines = ["    MATR_AMOR=amor,"]
    if shift != 0.0:
        lines += ["    OPTION='CENTRE',",
                  "    CALC_FREQ=_F(FREQ={0!r}, NMAX_FREQ={1}),".format(
                      shift, n)]
    elif free:
        lines += ["    OPTION='CENTRE',",
                  "    CALC_FREQ=_F(FREQ=-bridge_fshift, NMAX_FREQ={0}),"
                  .format(n)]
    else:
        lines += ["    OPTION='PLUS_PETITE',",
                  "    CALC_FREQ=_F(NMAX_FREQ={0}),".format(n),
                  "    SOLVEUR_MODAL=_F(METHODE='TRI_DIAG'),"]
    return lines


# DISCRET entry in bridge_to_aster._build_cara_elem_block (three forms,
# with or without REPERE).
_ENTRY_RE = re.compile(r"GROUP_MA='([^']+)',\s*CARA='([A-Z_]+)',\s*"
                       r"(?:REPERE='\w+',\s*)?VALE=\(([^)]*)\)")


def zero_damping_entries(entries):
    """
    Extra DISCRET entries with damping 0 (A_* next to each K_*) for groups
    without their own A_* entry. Without them, AMOR_MECA gives alarm
    DISCRETS_28 per discrete element ("vous n'avez pas affecte les
    caracteristiques d'amortissements. Par defaut l'amortissement est
    nul", seen with a nodal mass). Catalogue affe_cara_elem.py v17.4:
    every K_T_D_N, K_TR_D_N, K_T_N, K_T_D_L, ... has an A_ with as many values.
    """
    found = []
    damped = set()
    for text in entries:
        for group, cara, vals in _ENTRY_RE.findall(text):
            if cara.startswith("A_"):
                damped.add(group)
            elif cara.startswith("K_"):
                n = len([v for v in vals.split(",") if v.strip()])
                found.append((group, "A_" + cara[2:], n))
    out = []
    for group, cara, n in found:
        if group in damped:
            continue
        damped.add(group)
        out.append("        _F(GROUP_MA='{0}', CARA='{1}', VALE=({2},)),"
                   .format(group, cara, ", ".join(["0.0"] * n)))
    return out
