# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_harmonic.py
# Responsibility: harmonic (steady-state) response of a
# structure in the frequency domain, analysis harmonic_3d. Mecway has
# no harmonic analysis (manual v33 chapter 6; D30 Dynamic Response is
# transient): the bridge computes a Mecway Frequency (V30) or Dynamic
# Response model (D30) with the same mesh, materials, supports and
# loads as a harmonic load F e^(i w t):
#   ASSEMBLAGE (RIGI_MECA, MASS_MECA) -> CALC_MODES (the lowest modes) ->
#   frequency list (range or list, with extra points around the resonances:
#   DEFI_LIST_FREQ RAFFINEMENT CRITERE='LARGEUR_3DB') ->
#   GENE (default): PROJ_BASE -> DYNA_VIBRA TYPE_CALCUL='HARM'
#                     BASE_CALCUL='GENE' (modal damping) -> REST_GENE_PHYS
#   PHYS (check):     DYNA_VIBRA HARM BASE_CALCUL='PHYS' on the whole model
#                     (C = alpha M + beta K + dampers)
#   -> CALC_CHAMP SIGM_NOEU (complex, volume elements) ->
#   aster_harmonic_export (in the job): per frequency a <mode
#   frequency=".. Hz"> with amplitude, phase, Re/Im and probes (CSV).
# Syntax: Code-Aster test cases sdld313d (DYNA_VIBRA HARM PHYS and GENE with
# VECT_ASSE(_GENE), COEF_MULT, PHAS_DEG; REST_GENE_PHYS) and sdld21b
# (DEFI_LIST_FREQ RAFFINEMENT LARGEUR_3DB, AMOR_REDUIT), catalogues
# dyna_vibra.py and defi_list_freq.py (and MacroCommands/
# defi_list_freq_ops.py: points over 2 zeta f around f sqrt(1 - 2 zeta^2)).
#
# Measured (Code-Aster 17.4, prototype on the hex20 console of MD-05,
# 7 Oct 2026):
#   - DYNA_VIBRA HARM GENE gives a HARM_GENE, REST_GENE_PHYS a
#     DYNA_HARMO with complex DEPL per frequency (access parameter FREQ)
#     (FieldOnNodesComplex); CALC_CHAMP CONTRAINTE='SIGM_NOEU' on that
#     DYNA_HARMO gives complex stresses.
#   - PHAS_DEG = 30 and a frequency far below the first mode: arg(U) =
#     29.4 degrees (in phase with the load); at the resonance arg(U) = 30 -
#     88.8 degrees: U = F e^(i phi) / (k - m w^2 + i w c), u(t) =
#     Re(U e^(i w t)) (lagging = negative phase).
#   - FONC_MULT with a DEFI_FONCTION(NOM_PARA='FREQ') works in GENE and
#     PHYS (GENE = PHYS without damping, 6 modes).
#   - A chain res.getField(..).toSimpleFieldOnNodes().getValues() gave
#     NaN (hold on to the intermediate objects, like aster_acoustic_export).
#
#   build_harmonic(...) - builder (bridge_to_aster._build_dyna_modal sends
#                         analyses with type_calcul 'HARM' here)
#   report_harmonic(...) - after the run: frequencies, modes in the range
#                         and probes in the log/the status box
#
# Compatible with IronPython 2.7.9 (standard library only).

import math
import os
import re
from collections import OrderedDict

import bridge_to_aster as b2a
import bridge_dyna_modal as bdm
from bridge_utils import log, tr, CONFIG_BRIDGE, run_name

HARM_ANALYSIS = "harmonic_3d"
# Node selections with the frequency response in the log and a CSV (by the
# original Mecway name, case-insensitive; NL and EN).
PROBE_PREFIXES = ("MEETPUNT_", "PROBE_")
PROBE_SUFFIX = "_meetpunten.csv"
# Fields to Mecway (groups from "fields"); reactions and plastic strain
# do not belong to this analysis.
_FIELD_GROUPS = ("displacements", "velocities", "accelerations",
                 "stresses", "vonmises")
_STRESS_GROUPS = ("stresses", "vonmises")
# Refinement around a resonance only for 0 < zeta < 0.5:
# defi_list_freq_ops.py centres on f sqrt(1 - 2 zeta^2) (exists up to
# zeta = 0.707) and with zeta = 0 the centre would fall exactly on the
# (infinite) resonance.
_REFINE_MAX_ZETA = 0.5


def is_harmonic(analysis_cfg):
    """True if the analysis config is the harmonic structural analysis
    (key "type_calcul" 'HARM', not acoustic)."""
    return (str(analysis_cfg.get("type_calcul", "")).upper() == "HARM" and
            str(analysis_cfg.get("phenomene", "")).upper() != "ACOUSTIQUE")


# ==========================================
# INPUT
# ==========================================
def _frequency_plan(analysis):
    """
    {"list": [f, ...]} (harm_freq_list, exactly these frequencies) or
    {"start", "end", "count", "spacing"} (range, with refinement around the
    resonances). None on an error (ERROR logged).
    """
    text = "{0}".format(analysis.get("harm_freq_list", "0") or "0").strip()
    if text not in ("", "0", "0.0"):
        try:
            vals = [float(t) for t in re.split(r"[;,\s]+", text) if t]
        except ValueError:
            vals = None
        if not vals or min(vals) < 0.0:
            log(tr("ERROR: Harmonisch: frequentielijst (harm_freq_list) "
                   "'{0}' is ongeldig; verwacht getallen >= 0 in Hz "
                   "gescheiden door komma's, bijv. '5, 10, 20' (punt als "
                   "decimaalteken), of 0 voor het bereik.",
                   "ERROR: Harmonic: frequency list (harm_freq_list) '{0}' "
                   "is invalid; expected numbers >= 0 in Hz separated by "
                   "commas, e.g. '5, 10, 20' (point as decimal separator), "
                   "or 0 for the range.").format(text))
            return None
        out = []
        for v in sorted(vals):
            if not out or v > out[-1] * (1.0 + 1.0e-9):
                out.append(v)
        return {"list": out}
    try:
        f0 = float(analysis.get("harm_freq_start", 0.0))
        f1 = float(analysis.get("harm_freq_end", 0.0))
        n = int(analysis.get("harm_freq_count", 1))
    except (TypeError, ValueError):
        f0, f1, n = 0.0, 0.0, 0
    spacing = "{0}".format(analysis.get("harm_freq_spacing", "lin"))
    if f0 <= 0.0 or f1 < f0 or n < 1 or spacing not in ("lin", "log"):
        log(tr("ERROR: Harmonisch: frequentiebereik {0} .. {1} Hz met {2} "
               "stappen ({3}) is ongeldig (start > 0, eind >= start, aantal "
               ">= 1, verdeling lin of log).",
               "ERROR: Harmonic: frequency range {0} .. {1} Hz with {2} "
               "steps ({3}) is invalid (start > 0, end >= start, count >= "
               "1, spacing lin or log).").format(f0, f1, n, spacing))
        return None
    return {"start": f0, "end": f1, "count": n, "spacing": spacing}


def _phase_bodies(model_data):
    """#ASTER-FASE selection = degrees -> ({Mecway selection: degrees},
    errors)."""
    out, bad = OrderedDict(), []
    for body in model_data.get("aster_custom", {}).get("phases", []):
        name, sep, rest = body.partition("=")
        name = name.strip()
        try:
            value = float(rest.strip().replace(" ", "")) if sep else None
        except ValueError:
            value = None
        if not name or value is None:
            bad.append(tr("'#ASTER-FASE {0}': verwacht 'selectie = fase in "
                          "graden', bijv. '#ASTER-FASE Kracht2 = 90'",
                          "'#ASTER-FASE {0}': expected 'selection = phase "
                          "in degrees', e.g. '#ASTER-FASE Force2 = "
                          "90'").format(body))
            continue
        out[name] = value
    return out, bad


def _charge_groups(kws):
    """Group names (GROUP_MA/GROUP_NO) in an excit dict, or [] (e.g.
    PESANTEUR on the whole model)."""
    text = " ".join(e for es in kws.values() for e in es)
    found = []
    for g in re.findall(r"GROUP_(?:MA|NO)\s*=\s*'([^']+)'", text):
        if g not in found:
            found.append(g)
    return found


def _excitation_phases(model_data, charges, extra, excitations):
    """
    Phase [degrees] per excitation (#ASTER-FASE on the selection of the
    load), or None on an error (ERROR logged). A load on several selections
    with different phases (merged beam loads, gravity) is not possible.
    """
    phases, bad = _phase_bodies(model_data)
    renames = model_data.get("selection_renames",
                             model_data.get("group_renames", {}))
    by_group = OrderedDict()
    for sel, deg in phases.items():
        by_group[renames.get(sel, sel)] = (sel, deg)
    kws_of = dict(("load_{0}".format(k + 1), kws)
                  for k, (_cmd, kws, _f) in enumerate(charges))
    kws_of.update(dict((name, kws) for name, _cmd, kws in extra))
    used = set()
    out = []
    for charge, _fonc in excitations:
        groups = _charge_groups(kws_of.get(charge, {}))
        found = [by_group[g] for g in groups if g in by_group]
        values = sorted(set(d for _s, d in found))
        if len(values) > 1 or (found and len(found) != len(groups)):
            bad.append(tr("een last op {0} heeft verschillende fasen ({1}); "
                          "geef elke selectie een eigen belasting in Mecway",
                          "a load on {0} has different phases ({1}); give "
                          "each selection its own load in Mecway").format(
                              ", ".join("'%s'" % g for g in groups),
                              ", ".join("%g" % v for v in values) or "0"))
            out.append(0.0)
            continue
        used.update(s for s, _d in found)
        out.append(values[0] if values else 0.0)
    for sel in phases:
        if sel not in used:
            bad.append(tr("#ASTER-FASE: '{0}' is geen selectie met een "
                          "belasting",
                          "#ASTER-FASE: '{0}' is not a selection with a "
                          "load").format(sel))
    if bad:
        log(tr("ERROR: Harmonisch: {0}.", "ERROR: Harmonic: {0}.").format(
            "; ".join(bad)))
        return None
    for sel in phases:
        log("INFO: Harmonic: load on '{0}' with phase {1} degrees "
            "(#ASTER-FASE).".format(sel, "%g" % phases[sel]))
    return out


def _probes(model_data):
    """OrderedDict {Mecway name: [node numbers]} of the node selections
    MEETPUNT_... / PROBE_...; face and element selections: WARNING."""
    out = OrderedDict()
    for kind, names in (("node", model_data.get("node_groups", {})),
                        ("face", model_data.get("face_selection_faces", {})),
                        ("element",
                         model_data.get("element_selections", {}))):
        for name in names:
            if not (name or "").upper().startswith(PROBE_PREFIXES):
                continue
            if kind != "node":
                log(tr("WARNING: Harmonisch: meetpunt '{0}' is een "
                       "{1}selectie; alleen knoopselecties tellen; "
                       "overgeslagen.",
                       "WARNING: Harmonic: probe '{0}' is a {1} selection; "
                       "only node selections count; skipped.").format(
                           name, kind))
                continue
            nids = [int(str(n).lstrip("N")) for n in names[name]]
            if nids:
                out[name] = nids
    return out


def _dampers(model_data):
    return sorted(e for e, s in model_data.get("discrete_sections",
                                                {}).items()
                  if s.get("kind") == "damper")


def _check_model(model_data, analysis, basis):
    """What the harmonic analysis cannot do: ERROR with the solution.
    Returns True if the model can be computed."""
    ok = True
    if not b2a._check_linear(model_data, tr("een harmonische analyse",
                                            "a harmonic analysis")):
        ok = False
    if b2a._thermal_active(model_data):
        log(tr("ERROR: Thermische rek (Thermal stress) wordt in de "
               "harmonische analyse niet vertaald. Zet hem uit in Mecway.",
               "ERROR: Thermal strain (Thermal stress) is not translated in "
               "the harmonic analysis. Switch it off in Mecway."))
        ok = False
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor de "
               "harmonische analyse. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for the "
               "harmonic analysis. Choose 'liml' (General page)."))
        ok = False
    dampers = _dampers(model_data)
    if dampers and basis == "GENE":
        # A damper makes the damping non-proportional: the modal
        # equations are then coupled (no AMOR_REDUIT per mode).
        log(tr("ERROR: Dempers ({0}) kunnen niet in de harmonische analyse "
               "op modale basis (Mecway's mode superposition ook niet, "
               "manual par. 6.4). Kies 'Basis' PHYS (direct, harm_basis) "
               "of gebruik Rayleigh-demping.",
               "ERROR: Dampers ({0}) cannot be used in the harmonic "
               "analysis on a modal basis (nor in Mecway's mode "
               "superposition, manual section 6.4). Choose 'Basis' PHYS "
               "(direct, harm_basis) or use Rayleigh damping.").format(
                   ", ".join(dampers)))
        ok = False
    zeta = float(analysis.get("modal_damping", 0.0) or 0.0)
    if zeta and basis == "PHYS":
        log(tr("ERROR: Extra modale demping (modal_damping = {0}) bestaat "
               "alleen op modale basis; de directe berekening (PHYS) kent "
               "alleen Rayleigh-demping en dempers. Kies 'Basis' GENE of "
               "zet modal_damping op 0.",
               "ERROR: Extra modal damping (modal_damping = {0}) only "
               "exists on a modal basis; the direct computation (PHYS) only "
               "knows Rayleigh damping and dampers. Choose 'Basis' GENE or "
               "set modal_damping to 0.").format("%g" % zeta))
        ok = False
    if zeta >= 1.0 and basis == "GENE":
        log(damping_warning(None, zeta))
    if model_data.get("initial_velocities"):
        log("INFO: Harmonic: the initial velocity is not used (steady-state "
            "response).")
    return ok


def damping_warning(mode, xi, count=1):
    """WARNING for a modal damping ratio xi >= 1 (overcritical).
    mode None: the setting modal_damping (before the run); otherwise the
    mode from the .mess (BRIDGE_HARM_WAARSCHUWING DEMPING, after the run).
    The computation goes on: the steady-state response of a mode,
    q = F / (k - w^2 m + 2 i xi w w_n m), also exists for xi >= 1; there is
    only no resonance peak (Clough & Penzien, 1993, chapter 3).
    Computed (Code-Aster 17.4, 07-10-2026): HR-01a with modal_damping
    1.5 (GENE) runs through, |U| within 4.4e-8 of the exact solution."""
    if mode is None:
        where = "modal_damping = {0}".format("%g" % xi)
    else:
        where = tr(u"mode {0}, xi = {1}; {2} mode(s) met xi >= 1",
                   u"mode {0}, xi = {1}; {2} mode(s) with xi >= 1").format(
                       mode, "%.4g" % xi, count)
    return tr(u"WARNING: Harmonisch: dempingsverhouding >= 1 ({0}), "
              u"overkritisch: zo'n mode geeft geen resonantiepiek. De "
              u"berekening gaat door. Mecway's mode superposition vraagt "
              u"xi < 1 voor elke mode (manual par. 6.4); controleer de "
              u"Rayleigh-demping (alpha dempt de laagste, beta de hoogste "
              u"modes; xi per mode staat in study.mess, BRIDGE_DEMPING) en "
              u"de instelling modal_damping.",
              u"WARNING: Harmonic: damping ratio >= 1 ({0}), overdamped: "
              u"such a mode gives no resonance peak. The computation "
              u"continues. Mecway's mode superposition requires xi < 1 for "
              u"every mode (manual section 6.4); check the Rayleigh damping "
              u"(alpha damps the lowest, beta the highest modes; xi per "
              u"mode is in study.mess, BRIDGE_DEMPING) and the setting "
              u"modal_damping.").format(where)


# ==========================================
# BUILDER
# ==========================================
def _freq_funcs_block(load_funcs):
    """DEFI_FONCTIONs of the Mecway tables as a function of the
    frequency (column 'time' = Hz): FONC_MULT in DYNA_VIBRA HARM is a
    function of FREQ (prototype, header)."""
    if not load_funcs:
        return "#-- no tables (amplitude constant over the frequency) --\n"
    blocks = []
    for name, history in load_funcs:
        vale = ",\n          ".join("{0!r}, {1!r}".format(float(t), float(v))
                                    for t, v in history)
        blocks.append(
            "# Mecway-tabel: kolom 'time' = frequentie [Hz]\n"
            "{0} = DEFI_FONCTION(\n"
            "    NOM_PARA='FREQ',\n"
            "    VALE=({1}),\n"
            "    PROL_DROITE='CONSTANT',\n"
            "    PROL_GAUCHE='CONSTANT',\n"
            ")".format(name, vale))
    return "\n\n".join(blocks) + "\n"


def _excit_entries(excitations, phases, basis):
    out = []
    for k, ((_charge, fonc), phase) in enumerate(zip(excitations, phases)):
        vec = ("VECT_ASSE_GENE=fgen_{0}" if basis == "GENE"
               else "VECT_ASSE=vec_{0}").format(k + 1)
        mult = "FONC_MULT={0}".format(fonc) if fonc else "COEF_MULT=1.0"
        out.append("        _F({0}, {1}, PHAS_DEG={2!r}),".format(
            vec, mult, float(phase)))
    return out


def _harm_block(analysis, plan, basis, excit, alpha, beta, zeta, damped_c,
                cara_ref):
    """Damping, frequency list, DYNA_VIBRA HARM (and REST_GENE_PHYS) ->
    res. Python in the .comm: the frequencies are only known after
    CALC_MODES."""
    npts = max(0, int(analysis.get("harm_refine_points", 5) or 0))
    lines = [
        "# Modal damping: Mecway's Rayleigh damping C = alpha M + beta K is",
        "# per mode xi_i = alpha / (2 w_i) + beta w_i / 2 (Mecway manual par.",
        "# 9.26), plus the setting modal_damping (GENE only).",
        "import math as _math",
        "bridge_freqs = [float(_f) for _f in "
        "modes.getAccessParameters()['FREQ']]",
        "bridge_alpha, bridge_beta, bridge_zeta = {0!r}, {1!r}, {2!r}".format(
            alpha, beta, zeta),
        "bridge_xi = []",
        "for _f in bridge_freqs:",
        "    _w = 2.0 * _math.pi * _f",
        "    if _w <= 0.0:",
        "        # Rigid motion or mechanism (bridge_run_aster reports the",
        "        # cause, as for the response on a modal basis).",
        "        print('BRIDGE_DYNA_MODAL_FOUT FREQ mode=%d f=%g' % "
        "(len(bridge_xi) + 1, _f))",
        "        raise ValueError('harmonisch: mode met f <= 0')",
        "    bridge_xi.append(0.5 * (bridge_alpha / _w + bridge_beta * _w) + "
        "bridge_zeta)",
        "for _i, (_f, _x) in enumerate(zip(bridge_freqs, bridge_xi)):",
        "    print('BRIDGE_DEMPING mode %d: %.6g Hz, xi = %.6g' % "
        "(_i + 1, _f, _x))",
        "if bridge_xi and max(bridge_xi) >= 1.0:",
        "    # Overcritically damped mode: no resonance peak. Unlike the",
        "    # response on a modal basis in time, the job does not stop;",
        "    # bridge_harmonic.report_harmonic reports it as a WARNING.",
        "    print('BRIDGE_HARM_WAARSCHUWING DEMPING MODE=%d XI=%.6g N=%d' % "
        "(bridge_xi.index(max(bridge_xi)) + 1, max(bridge_xi), "
        "len([_x for _x in bridge_xi if _x >= 1.0])))",
        "",
        "# Frequencies: the range (lin/log) with {0} points per mode over the"
        .format(npts),
        "# half-power bandwidth 2 xi f around the peak f sqrt(1 - 2 xi^2)",
        "# (DEFI_LIST_FREQ RAFFINEMENT CRITERE='LARGEUR_3DB', test case",
        "# sdld21b), or exactly the list harm_freq_list.",
    ]
    if "list" in plan:
        lines += [
            "bridge_base = {0!r}".format([float(f) for f in plan["list"]]),
            "bridge_refine = []",
        ]
    else:
        lines += [
            "bridge_f0, bridge_f1, bridge_n = {0!r}, {1!r}, {2}".format(
                plan["start"], plan["end"], plan["count"]),
        ]
        if plan["spacing"] == "log":
            lines.append(
                "bridge_base = [bridge_f0 * (bridge_f1 / bridge_f0) ** "
                "(_k / float(max(1, bridge_n - 1))) for _k in "
                "range(bridge_n)]")
        else:
            lines.append(
                "bridge_base = [bridge_f0 + (bridge_f1 - bridge_f0) * _k / "
                "float(max(1, bridge_n - 1)) for _k in range(bridge_n)]")
        if npts:
            lines += [
                "bridge_refine = [(_f, _x) for _f, _x in zip(bridge_freqs, "
                "bridge_xi)",
                "                 if bridge_f0 <= _f <= bridge_f1 and 0.0 < _x "
                "< {0!r}]".format(_REFINE_MAX_ZETA),
            ]
        else:
            lines.append("bridge_refine = []")
    lines += [
        "bridge_base = sorted(set(bridge_base))",
    ]
    if npts:
        lines += [
            "if bridge_refine:",
            "    bridge_lf = DEFI_LIST_FREQ(",
            "        VALE=bridge_base,",
            "        RAFFINEMENT=_F(LIST_RAFFINE=[_f for _f, _x in "
            "bridge_refine],",
            "                       CRITERE='LARGEUR_3DB', NB_POINTS={0},"
            .format(npts),
            "                       AMOR_REDUIT=[_x for _f, _x in "
            "bridge_refine]),",
            "    )",
            "else:",
            "    bridge_lf = DEFI_LIST_REEL(VALE=bridge_base)",
        ]
    else:
        lines.append("bridge_lf = DEFI_LIST_REEL(VALE=bridge_base)")
    lines += [
        "bridge_list = list(bridge_lf.getValues())",
        "print('BRIDGE_HARM_LIJST N=%d FMIN=%.10g FMAX=%.10g VERFIJND=%d "
        "BASIS={0}' % (len(bridge_list), min(bridge_list), max(bridge_list),"
        " len(bridge_refine)))".format(basis),
        "if max(bridge_list) > max(bridge_freqs):",
        "    # Modal truncation: above the top mode of the basis the response",
        "    # no longer follows the load (docs/Respons_op_modale_basis.md).",
        "    print('BRIDGE_HARM_WAARSCHUWING BASIS FMAX=%.10g FMODE=%.10g' % "
        "(max(bridge_list), max(bridge_freqs)))",
        "",
    ]
    if basis == "GENE":
        lines += [
            "# Damping per vector of the basis (with static enrichment also",
            "# the pseudo-modes above the real modes; the same formula).",
            "bridge_bfreqs = [float(_f) for _f in "
            "bridge_basis.getAccessParameters()['FREQ']]",
            "bridge_bxi = [0.5 * (bridge_alpha / (2.0 * _math.pi * _f) + "
            "bridge_beta * 2.0 * _math.pi * _f) + bridge_zeta",
            "              for _f in bridge_bfreqs]",
            "if len(bridge_bfreqs) > len(bridge_freqs):",
            "    print('BRIDGE_HARM_VERRIJKING N=%d FREQ=%s' % (len(bridge_bfreqs)"
            " - len(bridge_freqs), ','.join('%.6g' % _f for _f in "
            "bridge_bfreqs[len(bridge_freqs):])))",
            "harm = DYNA_VIBRA(",
            "    TYPE_CALCUL='HARM',",
            "    BASE_CALCUL='GENE',",
            "    MATR_MASS=mgen,",
            "    MATR_RIGI=kgen,",
            "    AMOR_MODAL=_F(AMOR_REDUIT=bridge_bxi),",
            "    LIST_FREQ=bridge_lf,",
            "    EXCIT=(",
        ] + excit + [
            "    ),",
            ")",
            "",
            "res = REST_GENE_PHYS(",
            "    RESU_GENE=harm,",
            "    TOUT_ORDRE='OUI',",
            "    NOM_CHAM=('DEPL',),",
            ")",
            "",
        ]
    else:
        lines += [
            "res = DYNA_VIBRA(",
            "    TYPE_CALCUL='HARM',",
            "    BASE_CALCUL='PHYS',",
            "    MODELE=model,",
            "    CHAM_MATER=fieldmat,",
        ] + (["    CARA_ELEM=cara,"] if cara_ref else []) + [
            "    MATR_MASS=masse,",
            "    MATR_RIGI=rigidite,",
        ] + (["    MATR_AMOR=amor,"] if damped_c else []) + [
            "    LIST_FREQ=bridge_lf,",
            "    NOM_CHAM=('DEPL',),",
            "    EXCIT=(",
        ] + excit + [
            "    ),",
            "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(
                int(analysis.get("solver_nprec", 8))),
            ")",
            "",
        ]
    return "\n".join(lines)


def _damping_matrix_block(alpha, beta, dampers):
    """PHYS: C = alpha M + beta K + C_dampers (COMB_MATR_ASSE, like
    bridge_modal_damping.damping_block), or '' without damping."""
    terms = []
    if alpha:
        terms.append(("masse", alpha))
    if beta:
        terms.append(("rigidite", beta))
    if dampers:
        terms.append(("amor_dis", 1.0))
    if not terms:
        return ""
    head = ("# Damping matrix of the direct computation: C = alpha M + beta "
            "K (Mecway\n# manual par. 9.26) + dampers (AMOR_MECA)\n")
    if terms == [("amor_dis", 1.0)]:
        return head + "amor = amor_dis\n"
    return head + "amor = COMB_MATR_ASSE(COMB_R=(\n{0}))\n".format("".join(
        "    _F(MATR_ASSE={0}, COEF_R={1!r}),\n".format(m, float(c))
        for m, c in terms))


def build_harmonic(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate the .comm and .export for the harmonic response (analysis
    harmonic_3d). Returns the path of the .export, or None (ERROR logged).
    """
    log("--- Generating Aster Files (DYNA_VIBRA HARM) ---")
    basis = "{0}".format(analysis.get("harm_basis", "GENE")).upper()
    if basis not in ("GENE", "PHYS"):
        log(tr("ERROR: Harmonisch: basis (harm_basis) '{0}' is onbekend; "
               "kies GENE (modale basis) of PHYS (direct).",
               "ERROR: Harmonic: basis (harm_basis) '{0}' is unknown; "
               "choose GENE (modal basis) or PHYS (direct).").format(basis))
        return None
    plan = _frequency_plan(analysis)
    if plan is None:
        return None
    if not _check_model(model_data, analysis, basis):
        return None

    load_funcs = b2a._collect_load_funcs(model_data)
    func_names = b2a._load_func_names(model_data)
    timed = [name for name, _h in load_funcs]
    charges = b2a._build_charges(model_data, func_names)
    constraints, excitations, extra, errors = bdm._excitations(charges, timed)
    if errors:
        log(tr("ERROR: Harmonisch: een opgelegde verplaatsing met een tabel "
               "kan niet (de modes hebben die vrijheidsgraden vast). Zet de "
               "tabel uit of de waarde op 0.",
               "ERROR: Harmonic: an imposed displacement with a table is not "
               "possible (the modes have those degrees of freedom fixed). "
               "Remove the table or set the value to 0."))
        return None
    nonzero = b2a._nonzero_imposed(model_data)
    if nonzero:
        log(tr("ERROR: Opgelegde verplaatsing of rotatie <> 0 op {0}: een "
               "opgelegde (basis)beweging wordt in de harmonische analyse "
               "niet vertaald. Zet de waarde op 0 en breng de belasting als "
               "kracht, druk of gravity aan.",
               "ERROR: Imposed displacement or rotation <> 0 on {0}: an "
               "imposed (base) motion is not translated in the harmonic "
               "analysis. Set the value to 0 and apply the load as a "
               "force, pressure or gravity.").format(
                   ", ".join("'{0}'".format(s) for s in nonzero)))
        return None
    custom_excit = model_data.get("aster_custom", {}).get("excit", [])
    if not constraints and not custom_excit:
        log(tr("ERROR: Harmonische analyse zonder opleggingen: starre "
               "bewegingen kunnen niet (de respons zou oneindig zijn). Leg "
               "het model in Mecway vast.",
               "ERROR: Harmonic analysis without supports: rigid body "
               "motion is not possible (the response would be infinite). "
               "Add supports in Mecway."))
        return None
    if not excitations:
        log(tr("ERROR: Harmonisch: geen belasting (kracht, druk, gravity, "
               "...): de respons is overal 0. Breng in Mecway de "
               "harmonische last aan (de amplitude is de waarde van de "
               "belasting).",
               "ERROR: Harmonic: no load (force, pressure, gravity, ...): "
               "the response is zero everywhere. Apply the harmonic load "
               "in Mecway (the amplitude is the value of the load)."))
        return None
    if load_funcs:
        log("INFO: Harmonic: {0} load(s) with a Mecway table: the "
            "column 'time' is the frequency in Hz, the value the amplitude "
            "at that frequency (linear in between, constant outside)."
            .format(len(load_funcs)))
    phases = _excitation_phases(model_data, charges, extra, excitations)
    if phases is None:
        return None
    probes = _probes(model_data)

    fields = [f for f in analysis.get("fields", ["displacements"])
              if f in _FIELD_GROUPS]
    ignored = [f for f in analysis.get("fields", []) if f not in
               _FIELD_GROUPS]
    if "displacements" not in fields:
        fields.insert(0, "displacements")
    if ignored:
        log("INFO: Harmonic: fields {0} are not computed (no "
            "reactions or plastic strain).".format(", ".join(ignored)))
    g3d, gsh, gbm = b2a._result_groups(model_data)
    stresses = any(f in fields for f in _STRESS_GROUPS)
    if stresses and (gsh or gbm or not g3d):
        log("INFO: Harmonic: stresses only on volume elements{0}."
            .format("" if g3d else " (het model heeft er geen)"))
    stresses = stresses and bool(g3d)

    alpha, beta, zeta = bdm._damping_text(model_data, analysis)
    dampers = _dampers(model_data) if basis == "PHYS" else []
    if not (alpha or beta or zeta or dampers):
        log(tr("WARNING: Harmonisch: het model heeft geen demping (Rayleigh, "
               "modal_damping of dempers): bij een eigenfrequentie is de "
               "respons oneindig. Geef demping op, of kies frequenties "
               "tussen de eigenfrequenties.",
               "WARNING: Harmonic: the model has no damping (Rayleigh, "
               "modal_damping or dampers): at a natural frequency the "
               "response is infinite. Specify damping, or choose "
               "frequencies between the natural frequencies."))
    if alpha < 0.0 or beta < 0.0 or zeta < 0.0:
        log(tr("WARNING: Negatieve demping (alpha {0}, beta {1}, "
               "modal_damping {2}): de respons kan niet fysisch zijn.",
               "WARNING: Negative damping (alpha {0}, beta {1}, "
               "modal_damping {2}): the response may be unphysical.").format(
                   "%g" % alpha, "%g" % beta, "%g" % zeta))
    if dampers:
        # AMOR_MECA of the dampers; damping 0 for the other discrete elements
        # (bridge_modal_damping.zero_damping_entries via
        # bridge_to_aster._build_cara_elem_block, otherwise DISCRETS_28).
        model_data["damping_matrix"] = True

    defigroup_block = b2a._build_defigroup_block(model_data)
    model_block = b2a._build_model_block(model_data)
    cara_elem_block = b2a._build_cara_elem_block(model_data)
    cara = b2a._has_cara(model_data)
    cara_ref = "    CARA_ELEM=cara,\n" if cara else ""
    materials_block = b2a._build_materials_block(model_data, analysis)
    fieldmat_block = b2a._build_fieldmat_block(model_data)
    load_funcs_block = _freq_funcs_block(load_funcs)
    loads_block, _excit = b2a._render_charges(charges, model_data)
    loads_block = ("bridge_f0 = DEFI_CONSTANTE(VALE=0.0)\n"
                   "bridge_f1 = DEFI_CONSTANTE(VALE=1.0)\n" + loads_block +
                   "\n" + "".join(b2a._render_char_meca(n, c, k)
                                  for n, c, k in extra))

    charge_names = list(constraints) + [n for n in custom_excit
                                        if n not in constraints]
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}"
        "    CHARGE=({charge},),\n"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('rigidite'), OPTION='RIGI_MECA'),\n"
        "        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n"
        "{amor}"
        "    ),\n"
        ")\n").format(
            cara=cara_ref, charge=", ".join(charge_names),
            amor="        _F(MATRICE=CO('amor_dis'), OPTION='AMOR_MECA'),\n"
            if dampers else "")

    scripts = os.path.dirname(os.path.abspath(__file__))
    calc_modes_block = b2a._calc_modes_block(
        model_data, analysis, False, cara_ref).replace(
            "res = CALC_MODES(", "modes = CALC_MODES(", 1)
    calc_modes_block += (
        "# Modeoverzicht (frequentie, effectieve massa) in de .mess\n"
        "import sys\n"
        "sys.path.insert(0, {0})\n"
        "import aster_results_export\n"
        "aster_results_export.print_modes(modes, mass=masse)\n").format(
            b2a._py_str(scripts))

    proj = []
    for k, (charge, _fonc) in enumerate(excitations):
        proj += [
            "vel_{0} = CALC_VECT_ELEM(OPTION='CHAR_MECA', CHARGE={1}, "
            "CHAM_MATER=fieldmat{2})".format(
                k + 1, charge, ", CARA_ELEM=cara" if cara else ""),
            "vec_{0} = ASSE_VECTEUR(VECT_ELEM=vel_{0}, NUME_DDL=numedd)"
            .format(k + 1),
        ]
    static_corr = basis == "GENE" and bool(analysis.get("static_correction",
                                                          True))
    if static_corr:
        # Static enrichment of the basis (like DYNA_LINE ENRI_STAT='OUI'
        # with ORTHO, MacroCommands/dyna_line_ops.py): the static response
        # to each load vector (MACRO_ELAS_MULT) added to the modes
        # (DEFI_BASE_MODALE RITZ, K-orthogonal), then the eigenproblem on
        # that basis (CALC_MODES QZ on the projected M and K) and back
        # (REST_GENE_PHYS): the extra vectors become "pseudo-modes" above
        # the real modes, the basis stays diagonal. This way the response at
        # low frequencies is exactly static and only the dynamics of the
        # omitted modes are missing.
        proj += [
            "# Static enrichment of the modal basis (DYNA_LINE "
            "ENRI_STAT)",
            "corr = MACRO_ELAS_MULT(",
            "    MODELE=model,",
            "    CHAM_MATER=fieldmat,",
        ] + (["    CARA_ELEM=cara,"] if cara else []) + [
            "    NUME_DDL=numedd,",
            "    CHAR_MECA_GLOBAL=({0},),".format(", ".join(charge_names)),
            "    CAS_CHARGE=(",
        ] + ["        _F(NOM_CAS='c{0}', CHAR_MECA={1}, OPTION='SANS'),"
             .format(k + 1, c) for k, (c, _f) in enumerate(excitations)] + [
            "    ),",
            ")",
            "bridge_ritz = DEFI_BASE_MODALE(",
            "    RITZ=(_F(MODE_MECA=modes), _F(MODE_INTF=corr)),",
            "    NUME_REF=numedd,",
            "    ORTHO='OUI',",
            "    MATRICE=rigidite,",
            ")",
            "bridge_nug = NUME_DDL_GENE(BASE=bridge_ritz, STOCKAGE='PLEIN')",
            "bridge_mr = PROJ_MATR_BASE(BASE=bridge_ritz, "
            "NUME_DDL_GENE=bridge_nug, MATR_ASSE=masse)",
            "bridge_kr = PROJ_MATR_BASE(BASE=bridge_ritz, "
            "NUME_DDL_GENE=bridge_nug, MATR_ASSE=rigidite)",
            "bridge_cm = CALC_MODES(",
            "    MATR_MASS=bridge_mr,",
            "    MATR_RIGI=bridge_kr,",
            "    OPTION='TOUT',",
            "    SOLVEUR_MODAL=_F(METHODE='QZ'),",
            "    VERI_MODE=_F(STOP_ERREUR='NON'),",
            ")",
            "bridge_basis = REST_GENE_PHYS(RESU_GENE=bridge_cm, "
            "MODE_MECA=bridge_ritz)",
            "",
        ]
        log("INFO: Harmonic: static enrichment of the modal basis "
            "({0} vector(s), MACRO_ELAS_MULT + DEFI_BASE_MODALE, like "
            "DYNA_LINE ENRI_STAT).".format(len(excitations)))
    elif basis == "GENE":
        proj.append("bridge_basis = modes")
    if basis == "GENE":
        proj += [
            "PROJ_BASE(",
            "    BASE=bridge_basis,",
            "    STOCKAGE='DIAG',",
            "    MATR_ASSE_GENE=(",
            "        _F(MATRICE=CO('mgen'), MATR_ASSE=masse),",
            "        _F(MATRICE=CO('kgen'), MATR_ASSE=rigidite),",
            "    ),",
            "    VECT_ASSE_GENE=(",
        ] + ["        _F(VECTEUR=CO('fgen_{0}'), VECT_ASSE=vec_{0}, "
             "TYPE_VECT='FORC'),".format(k + 1)
             for k in range(len(excitations))] + [
            "    ),",
            ")",
            "",
        ]
        damped_c = False
    else:
        block = _damping_matrix_block(alpha, beta, dampers)
        damped_c = bool(block)
        if block:
            proj.append(block)
    projection_block = "\n".join(proj)
    harm_block = _harm_block(analysis, plan, basis,
                             _excit_entries(excitations, phases, basis),
                             alpha, beta, zeta if basis == "GENE" else 0.0,
                             damped_c, cara)

    if stresses:
        calc_champ_block = (
            "# Complexe spanningen (lineair in de verplaatsingen; alleen\n"
            "# volume-elementen: een NOEU-veld van schalen/balken heeft\n"
            "# lagen/vezels, bridge_to_aster._build_calc_champ_block)\n"
            "res = CALC_CHAMP(\n"
            "    reuse=res,\n"
            "    RESULTAT=res,\n"
            "    MODELE=model,\n"
            "    CHAM_MATER=fieldmat,\n"
            "{0}"
            "    GROUP_MA={1},\n"
            "    CONTRAINTE=('SIGM_NOEU',),\n"
            ")\n").format(cara_ref, b2a._fmt_groups(g3d))
    else:
        calc_champ_block = "#-- no stresses requested (fields) --\n"
    probe_text = "{" + ", ".join("{0}: [{1}]".format(
        b2a._py_str(name), ", ".join(str(n) for n in nids))
        for name, nids in probes.items()) + "}"
    export_block = b2a._custom_code(model_data, "post") + (
        "# Resultaten in Mecway's eigen formaat (result_route 'liml'): een\n"
        "# <mode frequency> per frequentie (aster_harmonic_export)\n"
        "import aster_harmonic_export\n"
        "aster_harmonic_export.export_harmonic(\n"
        "    res, {0}, {1},\n"
        "    fields={2!r},\n"
        "    probes={3},\n"
        "    csv_path={4},\n"
        "    language={5},\n"
        "    basis={6!r})\n").format(
            b2a._py_str(b2a.results_file(work_dir)),
            b2a._py_str(model_data.get("liml_path", "")),
            [str(f) for f in fields], probe_text,
            b2a._py_str(os.path.join(work_dir, run_name(PROBE_SUFFIX))),
            b2a._py_str(CONFIG_BRIDGE.get("language", "en")), basis)
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = (
            "IMPR_RESU(FORMAT='MED', UNITE=80, RESU=(\n"
            "    _F(RESULTAT=res, NOM_CHAM='DEPL', PARTIE='REEL', "
            "NOM_CHAM_MED='DEPL_REEL'),\n"
            "    _F(RESULTAT=res, NOM_CHAM='DEPL', PARTIE='IMAG', "
            "NOM_CHAM_MED='DEPL_IMAG'),\n))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    if "list" in plan:
        what = tr("{0} frequenties uit de lijst",
                  "{0} frequencies from the list").format(len(plan["list"]))
    else:
        what = tr("{0} .. {1} Hz, {2} punten ({3}) + {4} per mode in het "
                  "bereik",
                  "{0} .. {1} Hz, {2} points ({3}) + {4} per mode in the "
                  "range").format(
                      "%g" % plan["start"], "%g" % plan["end"],
                      plan["count"], plan["spacing"],
                      int(analysis.get("harm_refine_points", 5) or 0))
    log("INFO: Harmonic ({0}): {1}; {2} modes, {3} load vector(s), "
        "Rayleigh alpha {4} 1/s, beta {5} s, extra modal damping {6}{7}; "
        "{8} probe(s).".format(
            "modale basis" if basis == "GENE" else "direct", what,
            b2a._mode_count(model_data, analysis), len(excitations),
            alpha, beta, zeta if basis == "GENE" else 0.0,
            ", dempers " + ", ".join(dampers) if dampers else "",
            len(probes)))
    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = b2a._read_template(analysis["template"])
        b2a._write_comm(comm_path, template.format(
            defigroup_block=defigroup_block,
            model_block=model_block,
            cara_elem_block=cara_elem_block,
            materials_block=materials_block,
            fieldmat_block=fieldmat_block,
            load_funcs_block=load_funcs_block,
            loads_block=loads_block,
            assemblage_block=assemblage_block,
            calc_modes_block=calc_modes_block,
            projection_block=projection_block,
            harm_block=harm_block,
            calc_champ_block=calc_champ_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        with open(export_path, "w") as f:
            f.write("\n".join([
                "P actions make_etude",
                "P time_limit {0}".format(analysis.get("time_limit", 1800)),
                "P memory_limit {0}".format(analysis.get("memory_limit",
                                                         2048)),
                "P mpi_nbcpu 1",
                "P ncpus {0}".format(CONFIG_BRIDGE["ncpus"]),
                "P no-mpi true",
                "F comm {0} D 1".format(comm_path),
                "F mail {0} D 20".format(msh_path),
                "F mess {0} R 6".format(os.path.join(work_dir,
                                                     run_name(".mess"))),
            ]) + b2a._export_result_lines(work_dir, resu_name))
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren solver-bestanden mislukt: {0}",
               "ERROR: Generating solver files failed: {0}").format(str(e)))
    return None


# ==========================================
# AFTER THE RUN (IronPython): LOG AND STATUS BOX
# ==========================================
_MESS_LIST = re.compile(r"BRIDGE_HARM_LIJST\s+(.*)")
_MESS_WARN = re.compile(r"BRIDGE_HARM_WAARSCHUWING\s+BASIS\s+(.*)")
_MESS_WARN_XI = re.compile(r"BRIDGE_HARM_WAARSCHUWING\s+DEMPING\s+(.*)")
_MESS_XI = re.compile(r"BRIDGE_DEMPING mode (\d+): ([-+0-9.eE]+) Hz, xi = "
                      r"([-+0-9.eE]+)")


def _key_values(text):
    out = {}
    for part in text.split():
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def read_mess_summary(mess_path):
    """{"list": {N, FMIN, FMAX, VERFIJND, BASIS}, "warn": {FMAX, FMODE} or
    None, "warn_xi": {MODE, XI, N} or None, "modes": [(nr, f, xi)]} from
    the .mess; empty if it is missing."""
    out = {"list": {}, "warn": None, "warn_xi": None, "modes": []}
    if not mess_path or not os.path.isfile(mess_path):
        return out
    f = open(mess_path, "rb")
    try:
        for line in f:
            if not isinstance(line, str):
                line = line.decode("utf-8", "replace")
            if not line.startswith("BRIDGE_"):
                continue
            m = _MESS_LIST.match(line.strip())
            if m:
                out["list"] = _key_values(m.group(1))
                continue
            m = _MESS_WARN.match(line.strip())
            if m:
                out["warn"] = _key_values(m.group(1))
                continue
            m = _MESS_WARN_XI.match(line.strip())
            if m:
                out["warn_xi"] = _key_values(m.group(1))
                continue
            m = _MESS_XI.match(line.strip())
            if m:
                out["modes"].append((int(m.group(1)), float(m.group(2)),
                                     float(m.group(3))))
    finally:
        f.close()
    return out


def read_probes(csv_path):
    """[(name, f, |u|, amplitude a)] from the CSV of aster_harmonic_export;
    [] if it is missing."""
    import csv
    out = []
    if not csv_path or not os.path.isfile(csv_path):
        return out
    f = open(csv_path, "r")
    try:
        rows = list(csv.reader(f))
    finally:
        f.close()
    for row in rows[1:]:
        try:
            out.append((row[0], float(row[1]), float(row[2]),
                        float(row[3])))
        except (IndexError, ValueError):
            continue
    return out


def report_harmonic(work_dir, frequencies):
    """
    After a harmonic run: frequencies, the modes in the range with their
    damping, per probe the largest amplitude; WARNING if the highest
    frequency is above the highest mode of the basis. Returns the lines
    for the status box. frequencies: [(id, "frequency", f)] from
    read_modes().
    """
    mess = read_mess_summary(os.path.join(work_dir, run_name(".mess")))
    fs = [f for _i, _k, f in frequencies]
    basis = mess["list"].get("BASIS", "GENE")
    lines = [tr(u"Harmonische respons ({0}): {1} frequentie(s), {2} .. {3} "
                u"Hz ({4} rond resonanties verfijnd). Velden per frequentie: "
                u"displx/y/z (Re, fase 0), displix/y/z (Im), displampx/y/z "
                u"en displmag (amplitude), displphasex/y/z (graden).",
                u"Harmonic response ({0}): {1} frequency(ies), {2} .. {3} Hz "
                u"({4} refined around resonances). Fields per frequency: "
                u"displx/y/z (Re, phase 0), displix/y/z (Im), displampx/y/z "
                u"and displmag (amplitude), displphasex/y/z (degrees).")
             .format(tr(u"modale basis", u"modal basis") if basis == "GENE"
                     else tr(u"direct", u"direct"), len(fs),
                     "%.6g" % min(fs) if fs else "-",
                     "%.6g" % max(fs) if fs else "-",
                     int(mess["list"].get("VERFIJND", 0) or 0))]
    if fs:
        inside = [(nr, f, xi) for nr, f, xi in mess["modes"]
                  if min(fs) <= f <= max(fs)]
        for nr, f, xi in inside:
            lines.append(tr(u"Mode {0} in het bereik: {1} Hz, xi = {2}.",
                            u"Mode {0} in the range: {1} Hz, xi = {2}.")
                         .format(nr, "%.6g" % f, "%.4g" % xi))
    if mess["warn"]:
        log(tr(u"WARNING: Harmonisch: de hoogste frequentie ({0} Hz) ligt "
               u"boven de hoogste mode van de modale basis ({1} Hz): daar "
               u"ontbreekt de bijdrage van hogere modes. Reken met meer "
               u"modes (Number of modes in Mecway) of met harm_basis PHYS.",
               u"WARNING: Harmonic: the highest frequency ({0} Hz) is above "
               u"the highest mode of the modal basis ({1} Hz): the "
               u"contribution of higher modes is missing there. Compute "
               u"with more modes (Number of modes in Mecway) or with "
               u"harm_basis PHYS.").format(
                   "%.6g" % mess["warn"].get("FMAX", 0.0),
                   "%.6g" % mess["warn"].get("FMODE", 0.0)))
    if mess["warn_xi"]:
        log(damping_warning(int(mess["warn_xi"].get("MODE", 0) or 0),
                            float(mess["warn_xi"].get("XI", 0.0) or 0.0),
                            int(mess["warn_xi"].get("N", 1) or 1)))
    path = os.path.join(work_dir, run_name(PROBE_SUFFIX))
    by_name = OrderedDict()
    for name, f, amp, acc in read_probes(path):
        by_name.setdefault(name, []).append((f, amp, acc))
    for name, rows in by_name.items():
        f, amp, acc = max(rows, key=lambda r: r[1])
        lines.append(tr(u"Meetpunt {0}: grootste amplitude |u| = {1} m bij "
                        u"{2} Hz (|a| = {3} m/s2).",
                        u"Probe {0}: largest amplitude |u| = {1} m at {2} Hz "
                        u"(|a| = {3} m/s2).").format(
                            name, "%.4g" % amp, "%.6g" % f, "%.4g" % acc))
    if by_name:
        lines.append(tr(u"Frequentierespons per meetpunt: {0}",
                        u"Frequency response per probe: {0}").format(path))
    for line in lines:
        log(u"INFO: " + line)
    return lines
