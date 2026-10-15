# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_spectrum.py
# Responsibility: response spectrum analysis (earthquake, shock) to
# Code-Aster; analysis spectrum_3d:
#   ASSEMBLAGE (RIGI_MECA, MASS_MECA) -> CALC_MODES (the lowest modes) ->
#   CALC_CHAMP on the modes (REAC_NODA, SIGM_ELNO/SIGM_NOEU) ->
#   [MODE_STATIQUE PSEUDO_MODE: missing mass] -> COMB_SISM_MODAL
#   (MONO_APPUI: spectral response per mode, combination over the modes and
#   the directions) -> aster_spectrum.maxima (one result with the maxima) ->
#   aster_results_export (one step in Mecway).
# Syntax: Code-Aster test cases sdld25a (8 masses and springs, DEFI_NAPPE
# in AMOR and FREQ, ACCE_ABSOLU) and sdlx02a (MODE_STATIQUE PSEUDO_MODE
# with MODE_CORR, REAC_NODA), catalogue comb_sism_modal.py and the macro
# code_aster/MacroCommands/comb_sism_modal_ops.py (17.4).
#
# Mecway has no spectrum analysis (manual v33 chapter 6; no text
# "spectrum" in mecway.exe). Input (docs/Spectrumanalyse.md):
#   - the Mecway model is a Frequency analysis (V30: Number of modes,
#     density, supports);
#   - the spectrum is a Gravity with a table per direction: the
#     "time" column is the period in s (setting spectrum_abscissa
#     'period') or the frequency in Hz ('frequency'), the value the spectral
#     acceleration; a fixed value without a table is a flat spectrum. The
#     gravity is not a load in this analysis (bridge_from_liml:
#     model_data["spectrum_gravity"]);
#   - or per direction a Code-Aster spectrum of its own (DEFI_NAPPE in AMOR
#     and FREQ, or FORMULE) from #ASTER code with '#ASTER-SPECTRE X = name'
#     (bridge_custom), e.g. spectra for several damping ratios.
#
#   build_spectrum(...)  - builder for SOLVER_BUILDERS_ASTER
#                          ["COMB_SISM_MODAL"] (bridge_to_aster)
#   report_summary(mess) - log/status box after the run (MecwayAsterBridgeMain)
#
# Compatible with IronPython 2.7.9 (standard library only).

import os
import re

import bridge_to_aster as b2a
from bridge_utils import log, tr, CONFIG_BRIDGE, run_name


_DIRS = ("X", "Y", "Z")
_MODAL_RULES = ("CQC", "SRSS", "ABS")
# Setting -> COMB_DIRECTION (aster_spectrum computes 100-30-30 itself from
# the directions; catalogue: ABS, QUAD, NEWMARK = 100-40-40).
_DIRECTION_RULES = {"SRSS": "QUAD", "100-30-30": "QUAD",
                    "100-40-40": "NEWMARK", "ABS": "ABS"}
_ABSCISSAE = ("period", "frequency")
_FIELD_GROUPS = ("displacements", "accelerations", "stresses", "vonmises",
                 "reactions")
# Load types that are only supports in a spectrum analysis.
_CONSTRAINT_TYPES = ("fixed", "displacement", "pinnedsupport",
                     "noderotation", "frictionless", "symmetry",
                     "elasticsupport")


# ==========================================
# SPECTRUM FROM THE GRAVITY
# ==========================================
def _value_at(value, x):
    """Value (number or table [(x, y)]) at x: linear, constant outside the
    table (Mecway manual v33 chapter 9)."""
    if not isinstance(value, list):
        return value
    if x <= value[0][0]:
        return value[0][1]
    if x >= value[-1][0]:
        return value[-1][1]
    for (x0, y0), (x1, y1) in zip(value, value[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return value[-1][1]


def gravity_spectra(model_data):
    """{direction: number or table [(x, acceleration)]} from the gravities
    (sum per component; a table and a number add up as in Mecway).
    Directions without a value are missing."""
    out = {}
    for d, ax in zip(_DIRS, "xyz"):
        parts = []
        for p in model_data.get("spectrum_gravity", []):
            v = (p.get("_history") or {}).get(ax, p.get(ax, 0.0))
            parts.append(v)
        tables = [v for v in parts if isinstance(v, list)]
        if tables:
            xs = sorted(set(x for t in tables for x, _y in t))
            out[d] = [(x, sum(_value_at(v, x) for v in parts)) for x in xs]
        else:
            total = sum(float(v) for v in parts)
            if abs(total) > 0.0:
                out[d] = total
    return dict((d, v) for d, v in out.items()
                if (isinstance(v, list) and any(abs(y) > 0 for _x, y in v))
                or (not isinstance(v, list) and v != 0.0))


def _points(value, abscissa, d):
    """(xs, ys) for aster_spectrum.table, or None (ERROR logged). Values
    without sign (the sign of a spectrum does not matter)."""
    if not isinstance(value, list):
        return [0.0], [abs(float(value))]
    xs = [float(x) for x, _y in value]
    ys = [abs(float(y)) for _x, y in value]
    if xs[0] < 0.0:
        log(tr("ERROR: Spectrum {0}: negatieve {1} ({2}) in de tabel van "
               "de gravity.",
               "ERROR: Spectrum {0}: negative {1} ({2}) in the table of the "
               "gravity.").format(
                   d, tr("periode", "period") if abscissa == "period"
                   else tr("frequentie", "frequency"), xs[0]))
        return None
    if any(float(y) < 0.0 for _x, y in value):
        log("INFO: Spectrum {0}: negative values in the table; the bridge "
            "takes the absolute value (the sign does not matter).".format(d))
    return xs, ys


def _setting(analysis, key, allowed, default):
    value = u"{0}".format(analysis.get(key, default)).strip()
    if value not in allowed:
        log(tr("ERROR: Instelling {0} = '{1}' is onbekend; kies {2}.",
               "ERROR: Setting {0} = '{1}' is unknown; choose {2}.").format(
                   key, value, ", ".join(allowed)))
        return None
    return value


# ==========================================
# CHECKS
# ==========================================
def _check_model(model_data, analysis):
    """What the spectrum analysis cannot do: ERROR with the solution. Returns
    True if the model can be computed."""
    ok = True
    if not b2a._check_linear(model_data, tr("een spectrumanalyse",
                                            "a response spectrum analysis")):
        ok = False
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor de "
               "spectrumanalyse. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for the "
               "response spectrum analysis. Choose 'liml' (General page)."))
        ok = False
    timed = [bc["selection"] for bc in model_data["bcs"]
             if bc["type"] in _CONSTRAINT_TYPES and any(
                 isinstance(v, list) for v in bc["aster_dict"].values())]
    if timed:
        log(tr("ERROR: Opgelegde verplaatsing met een tijdstabel op {0}: "
               "in een spectrumanalyse zijn de opleggingen vast (0). Haal "
               "de tabel weg.",
               "ERROR: Imposed displacement with a time table on {0}: in a "
               "response spectrum analysis the supports are fixed (0). "
               "Remove the table.").format(", ".join(timed)))
        ok = False
    else:
        nonzero = b2a._nonzero_imposed(model_data)
        if nonzero:
            log(tr("ERROR: Opgelegde verplaatsing of rotatie <> 0 op {0}: "
                   "de spectrumanalyse kent alleen vaste opleggingen (de "
                   "grond beweegt volgens het spectrum). Zet de waarde op 0.",
                   "ERROR: Imposed displacement or rotation <> 0 on {0}: the "
                   "response spectrum analysis only knows fixed supports "
                   "(the ground moves according to the spectrum). Set the "
                   "value to 0.").format(
                       ", ".join("'{0}'".format(s) for s in nonzero)))
            ok = False
    if b2a._thermal_active(model_data):
        log(tr("WARNING: Thermische rek (Thermal stress) telt niet mee in "
               "de spectrumanalyse.",
               "WARNING: Thermal strain (Thermal stress) is not included in "
               "the response spectrum analysis."))
    if model_data.get("analysis_type") not in ("V30", None, ""):
        log(tr("WARNING: Het Mecway-model is geen Frequency-analyse (V30) "
               "maar {0}. De spectrumanalyse gebruikt de modes; kies in "
               "Mecway Frequency, zodat Number of modes geldt en je de "
               "modes in Mecway kunt controleren.",
               "WARNING: The Mecway model is not a Frequency analysis (V30) "
               "but {0}. The response spectrum analysis uses the modes; "
               "choose Frequency in Mecway, so that Number of modes applies "
               "and you can check the modes in Mecway.").format(
                   model_data.get("analysis_type")))
    return ok


def _drop_loads(model_data):
    """Loads (not supports) do not take part: WARNING and
    skipped_loads. Time tables of loads are dropped silently (the load
    disappears anyway)."""
    names = []
    for bc in model_data["bcs"]:
        if bc["type"] in _CONSTRAINT_TYPES:
            continue
        if bc["type"] not in names:
            names.append(bc["type"])
        bc["aster_dict"] = dict(
            (k, (v[-1][1] if v else 0.0) if isinstance(v, list) else v)
            for k, v in bc["aster_dict"].items())
    if names:
        log(tr("WARNING: Spectrumanalyse: belastingen ({0}) doen niet mee; "
               "de belasting is het spectrum (Gravity met tabel).",
               "WARNING: Response spectrum analysis: loads ({0}) are not "
               "included; the load is the spectrum (Gravity with a "
               "table).").format(", ".join(names)))
        model_data.setdefault("skipped_loads", []).append(
            tr("belastingen in de spectrumanalyse ({0})",
               "loads in the response spectrum analysis ({0})").format(
                   ", ".join(names)))


# ==========================================
# BLOCKS OF THE .COMM
# ==========================================
def _spec_call(d, name, extra):
    """aster_spectrum dict for report()/von_mises() (same ECHELLE,
    NATURE, CORR_FREQ as in SPECTRE)."""
    kw = {"ECHELLE": "1.0", "NATURE": "'ACCE'", "CORR_FREQ": "'NON'"}
    for e in extra:
        k, _sep, v = e.partition("=")
        kw[k.strip().upper()] = v.strip()
    return ("dict(dir='{0}', spec={1}, scale={2}, nature={3}, "
            "corr_freq={4})".format(d, name, kw["ECHELLE"], kw["NATURE"],
                                    kw["CORR_FREQ"]))


def _spectrum_block(spectra, custom, abscissa, analysis, alpha, beta, zeta,
                    options, missing, cara_ref, dir_rule, dirs):
    """Spectra (FORMULE per direction), damping per mode, pseudo-modes and
    COMB_SISM_MODAL (Python in the .comm: the frequencies are only known
    after CALC_MODES)."""
    lines = []
    entries, specs = [], []
    for d in dirs:
        if d in custom:
            name, extra = custom[d]
            entries.append("_F(LIST_AXE=('{0}',), SPEC_OSCI={1}{2})".format(
                d, name, "".join(", " + e for e in extra)))
            specs.append(_spec_call(d, name, extra))
            continue
        xs, ys = spectra[d]
        arg = "1.0 / FREQ" if abscissa == "period" else "FREQ"
        lines += [
            "# Spectrum {0}: Mecway gravity, {1} -> acceleration [m/s2],".format(
                d, "period [s]" if abscissa == "period"
                else "frequency [Hz]"),
            "# linear between the points, constant outside the table.",
            "bridge_xs_{0} = {1!r}".format(d, xs),
            "bridge_ys_{0} = {1!r}".format(d, ys),
            "bridge_spec_{0} = FORMULE(".format(d),
            "    VALE='bridge_table({0}, bridge_xs_{1}, bridge_ys_{1})',"
            .format(arg, d),
            "    bridge_table=aster_spectrum.table, bridge_xs_{0}=bridge_xs_{0},"
            .format(d),
            "    bridge_ys_{0}=bridge_ys_{0}, NOM_PARA=('AMOR', 'FREQ'))".format(
                d),
            "",
        ]
        entries.append("_F(LIST_AXE=('{0}',), SPEC_OSCI=bridge_spec_{0})"
                       .format(d))
        specs.append(_spec_call(d, "bridge_spec_{0}".format(d), []))
    lines += [
        "# Modal damping: Mecway's Rayleigh damping C = alpha M + beta K is",
        "# per mode xi_i = (alpha / w_i + beta w_i) / 2 (Mecway manual par.",
        "# 9.26), plus the setting spectrum_damping.",
        "import math as _math",
        "bridge_freqs = [float(_f) for _f in "
        "modes.getAccessParameters()['FREQ']]",
        "bridge_alpha, bridge_beta, bridge_zeta = {0!r}, {1!r}, {2!r}".format(
            alpha, beta, zeta),
        "bridge_xi = []",
        "for _f in bridge_freqs:",
        "    _w = 2.0 * _math.pi * _f",
        "    if _w <= 0.0:",
        "        print('BRIDGE_SPECTRUM_FOUT FREQ mode=%d f=%g' % "
        "(len(bridge_xi) + 1, _f))",
        "        raise ValueError('spectrum: mode met f <= 0')",
        "    bridge_xi.append(0.5 * (bridge_alpha / _w + bridge_beta * _w) + "
        "bridge_zeta)",
        "if max(bridge_xi) >= 1.0:",
        "    print('BRIDGE_SPECTRUM_FOUT DEMPING mode=%d xi=%g' % "
        "(bridge_xi.index(max(bridge_xi)) + 1, max(bridge_xi)))",
        "    raise ValueError('spectrum: dempingsverhouding >= 1')",
        "bridge_specs = [",
    ] + ["    {0},".format(s) for s in specs] + ["]", ""]
    if missing:
        lines += [
            "# Missing mass: pseudo-modes = static response to a",
            "# unit acceleration per direction (MODE_STATIQUE PSEUDO_MODE,",
            "# test case sdlx02a); COMB_SISM_MODAL MODE_CORR adds the rest",
            "# (pseudo-mode minus the contribution of the modes) with the",
            "# spectrum at the cut-off frequency = the highest computed mode.",
            "bridge_fcut = max(bridge_freqs)",
            "psmod = MODE_STATIQUE(",
            "    MATR_RIGI=rigidite,",
            "    MATR_MASS=masse,",
            "    CHAM_MATER=fieldmat,",
        ] + (["    CARA_ELEM=cara,"] if cara_ref else []) + [
            "    PSEUDO_MODE=_F(AXE=({0},)),".format(
                ", ".join("'{0}'".format(d) for d in dirs)),
            ")",
            "{fields_ps}",
        ]
    type_resu = ["_F(TYPE='VALE_TOTA')"]
    if dir_rule == "100-30-30" and len(dirs) > 1:
        type_resu.append("_F(TYPE='VALE_DIRE', LIST_AXE=({0},))".format(
            ", ".join("'{0}'".format(d) for d in dirs)))
    lines += [
        "sism = COMB_SISM_MODAL(",
        "    MODE_MECA=modes,",
        "    AMOR_REDUIT=bridge_xi,",
        "    TYPE_ANALYSE='MONO_APPUI',",
    ]
    if missing:
        lines += ["    MODE_CORR='OUI',", "    PSEUDO_MODE=psmod,",
                  "    FREQ_COUP=bridge_fcut,"]
    lines += ["    SPECTRE=("] + ["        {0},".format(e) for e in entries] + [
        "    ),",
        "    COMB_MODE=_F(TYPE='{0}'),".format(analysis["_modal_rule"]),
        "    COMB_DIRECTION='{0}',".format(_DIRECTION_RULES[dir_rule]),
        "    OPTION=({0},),".format(", ".join("'{0}'".format(o)
                                             for o in options)),
        "    TYPE_RESU=({0},),".format(", ".join(type_resu)),
        "    INFO=2,",
        ")",
        "aster_spectrum.report(modes, bridge_specs, bridge_xi, '{0}', "
        "'{1}'{2})".format(
            analysis["_modal_rule"], _DIRECTION_RULES[dir_rule]
            if dir_rule != "100-30-30" else "100-30-30",
            ", psmod=psmod, f_cut=bridge_fcut" if missing else ""),
        "",
    ]
    return "\n".join(lines)


def _modal_fields_block(concept, g3d, stress, model_data):
    """CALC_CHAMP on the modes or the pseudo-modes: REAC_NODA (reactions and
    the total reaction) and, for stresses, SIGM_ELNO/SIGM_NOEU on the
    volume elements (test case sdlx02a: CALC_CHAMP on MODE_MECA and on
    MODE_STATIQUE for COMB_SISM_MODAL). REAC_NODA without the springs of
    elastic support (BRES*), as in static (bridge_to_aster.
    _build_calc_champ_block): then the spring force is the reaction."""
    springs = [g for g in model_data.get("discretes", {})
               if g.startswith("BRES")]
    where = ""
    if springs:
        where = " GROUP_MA={0},".format(b2a._fmt_groups(
            [g for g in b2a._model_groups(model_data) if g not in springs]))
    out = ["{0} = CALC_CHAMP(reuse={0}, RESULTAT={0},{1} FORCE=('REAC_NODA',))"
           .format(concept, where)]
    if stress and g3d:
        out.append("{0} = CALC_CHAMP(reuse={0}, RESULTAT={0}, GROUP_MA={1}, "
                   "CONTRAINTE=('SIGM_ELNO', 'SIGM_NOEU'))".format(
                       concept, b2a._fmt_groups(g3d)))
    return "\n".join(out) + "\n"


def build_spectrum(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate the .comm and .export for the response spectrum analysis
    (analysis spectrum_3d, solver_command COMB_SISM_MODAL). Returns the path
    of the .export, or None (ERROR logged).
    """
    log("--- Generating Aster Files (CALC_MODES + COMB_SISM_MODAL) ---")
    if not _check_model(model_data, analysis):
        return None
    abscissa = _setting(analysis, "spectrum_abscissa", _ABSCISSAE, "period")
    modal_rule = _setting(analysis, "modal_combination", _MODAL_RULES, "CQC")
    dir_rule = _setting(analysis, "direction_combination",
                        sorted(_DIRECTION_RULES), "SRSS")
    if None in (abscissa, modal_rule, dir_rule):
        return None
    analysis = dict(analysis)
    analysis["_modal_rule"] = modal_rule
    try:
        zeta = float(analysis.get("spectrum_damping", 0.05))
    except (TypeError, ValueError):
        zeta = -1.0
    if not 0.0 <= zeta < 1.0:
        log(tr("ERROR: Instelling spectrum_damping = {0}: kies een "
               "dempingsverhouding 0 <= xi < 1 (bijv. 0.05).",
               "ERROR: Setting spectrum_damping = {0}: choose a damping "
               "ratio 0 <= xi < 1 (e.g. 0.05).").format(
                   analysis.get("spectrum_damping")))
        return None
    missing = bool(analysis.get("missing_mass", True))

    # Spectra per direction
    custom = model_data.get("aster_custom", {}).get("spectrum", {})
    grav = gravity_spectra(model_data)
    spectra = {}
    for d, v in grav.items():
        if d in custom:
            log("INFO: Spectrum {0}: #ASTER-SPECTRE {1} instead of the "
                "gravity.".format(d, custom[d][0]))
            continue
        pts = _points(v, abscissa, d)
        if pts is None:
            return None
        spectra[d] = pts
    dirs = [d for d in _DIRS if d in spectra or d in custom]
    if not dirs:
        log(tr("ERROR: Spectrumanalyse zonder spectrum. Breng in Mecway een "
               "Gravity aan met per richting een tabel: in de kolom 'time' "
               "de periode [s] (of de frequentie, instelling "
               "spectrum_abscissa), als waarde de spectrale versnelling; of "
               "gebruik #ASTER-SPECTRE (docs/Spectrumanalyse.md).",
               "ERROR: Response spectrum analysis without a spectrum. Apply "
               "a Gravity in Mecway with a table per direction: in the "
               "'time' column the period [s] (or the frequency, setting "
               "spectrum_abscissa), as value the spectral acceleration; or "
               "use #ASTER-SPECTRE (docs/en/Response_spectrum.md)."))
        return None
    for d in dirs:
        if d in spectra:
            xs, ys = spectra[d]
            log("INFO: Spectrum {0}: {1} point(s), {2} {3} .. {4}, "
                "acceleration {5} .. {6} m/s2.".format(
                    d, len(xs), abscissa, min(xs), max(xs), min(ys),
                    max(ys)))

    # Supports; loads are dropped
    _drop_loads(model_data)
    charges = b2a._build_charges(model_data)
    charges = [c for c in charges if not b2a._is_load_charge(c)]
    custom_excit = model_data.get("aster_custom", {}).get("excit", [])
    if not charges and not custom_excit:
        log(tr("ERROR: Spectrumanalyse zonder opleggingen: de grond "
               "beweegt via de opleggingen. Leg het model in Mecway vast.",
               "ERROR: Response spectrum analysis without supports: the "
               "ground moves through the supports. Add supports in "
               "Mecway."))
        return None
    names = ["load_{0}".format(k + 1) for k in range(len(charges))]
    charge_names = names + [n for n in custom_excit if n not in names]

    fields = [f for f in analysis.get("fields", ["displacements"])
              if f in _FIELD_GROUPS]
    ignored = [f for f in analysis.get("fields", []) if f not in
               _FIELD_GROUPS]
    if "displacements" not in fields:
        fields.insert(0, "displacements")
    if ignored:
        log("INFO: Spectrum analysis: fields {0} are not computed."
            .format(", ".join(ignored)))
    g3d, gsh, gbm = b2a._result_groups(model_data)
    stress = any(f in fields for f in ("stresses", "vonmises"))
    if stress and not g3d:
        log("INFO: Spectrum analysis: stresses only on volume elements; "
            "the model has none.")
        stress = False
    elif stress and (gsh or gbm):
        log("INFO: Spectrum analysis: stresses only on the volume "
            "elements, not on shells and beams ({0}).".format(
                ", ".join(list(gsh) + list(gbm))))
    options = ["DEPL"]
    if "accelerations" in fields:
        options.append("ACCE_ABSOLU")
    if "reactions" in fields:
        options.append("REAC_NODA")
    if stress and "stresses" in fields:
        options.append("SIGM_ELNO")

    ray = model_data.get("rayleigh") or {}
    alpha = float(ray.get("alpha", 0.0) or 0.0)
    beta = float(ray.get("beta", 0.0) or 0.0)
    if alpha or beta:
        log("INFO: Spectrum analysis: Mecway's Rayleigh damping (alpha {0} "
            "1/s, beta {1} s) counts per mode, plus spectrum_damping "
            "{2}.".format(alpha, beta, zeta))
        if any(d in spectra for d in dirs):
            log(tr("WARNING: De demping verschilt per mode (Rayleigh), maar "
                   "een spectrum uit een gravity-tabel geldt voor een "
                   "demping; de bridge gebruikt het voor alle modes. Voor "
                   "spectra per demping: #ASTER-SPECTRE met een DEFI_NAPPE.",
                   "WARNING: The damping differs per mode (Rayleigh), but a "
                   "spectrum from a gravity table holds for one damping; "
                   "the bridge uses it for all modes. For spectra per "
                   "damping: #ASTER-SPECTRE with a DEFI_NAPPE."))

    defigroup_block = b2a._build_defigroup_block(model_data)
    model_block = b2a._build_model_block(model_data)
    cara_elem_block = b2a._build_cara_elem_block(model_data)
    cara_ref = "    CARA_ELEM=cara,\n" if b2a._has_cara(model_data) else ""
    materials_block = b2a._build_materials_block(model_data, analysis)
    fieldmat_block = b2a._build_fieldmat_block(model_data)
    loads_block, _excit = b2a._render_charges(charges, model_data)
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
        "    ),\n"
        ")\n").format(cara=cara_ref, charge=", ".join(charge_names))

    scripts = os.path.dirname(os.path.abspath(__file__))
    calc_modes_block = b2a._calc_modes_block(
        model_data, analysis, False, cara_ref).replace(
            "res = CALC_MODES(", "modes = CALC_MODES(", 1)
    calc_modes_block += (
        "# Mode overview (frequency, effective mass) in the .mess\n"
        "import sys\n"
        "sys.path.insert(0, {0})\n"
        "import aster_results_export\n"
        "import aster_spectrum\n"
        "aster_results_export.print_modes(modes, mass=masse)\n"
        "# Modal fields for COMB_SISM_MODAL\n").format(b2a._py_str(scripts))
    calc_modes_block += _modal_fields_block("modes", g3d, stress,
                                            model_data)
    spectrum_block = _spectrum_block(
        spectra, custom, abscissa, analysis, alpha, beta, zeta, options,
        missing, cara_ref, dir_rule, dirs).replace(
            "{fields_ps}",
            _modal_fields_block("psmod", g3d, stress, model_data))

    affe = "MODELE=model, CHAM_MATER=fieldmat" + (
        ", CARA_ELEM=cara" if cara_ref else "")
    result = [
        "# The maxima as one result (one index; ACCE_ABSOLU -> ACCE)",
        "res = aster_spectrum.maxima(sism, {0!r}, '{1}', {2!r}, {3})".format(
            options, dir_rule, dirs, affe),
    ]
    if stress and "stresses" in fields:
        result.append(
            "res = CALC_CHAMP(reuse=res, RESULTAT=res, {0}, GROUP_MA={1}, "
            "CONTRAINTE=('SIGM_NOEU',))".format(affe, b2a._fmt_groups(g3d)))
    extra = "{}"
    if stress and "vonmises" in fields:
        result += [
            "# von Mises computed per mode and combined (aster_spectrum)",
            "bridge_vm = aster_spectrum.von_mises(modes, bridge_specs, "
            "bridge_xi, '{0}', '{1}'{2})".format(
                modal_rule, _DIRECTION_RULES[dir_rule]
                if dir_rule != "100-30-30" else "100-30-30",
                ", psmod=psmod, f_cut=bridge_fcut" if missing else ""),
        ]
        extra = ("dict([('SIEQ_NOEU', bridge_vm)] if bridge_vm is not None "
                 "else [])")
    result += [
        "res_mecway = aster_spectrum.Result(res, {0})".format(extra), ""]
    result_block = "\n".join(result)

    export_block = b2a._custom_code(model_data, "post") + (
        "# Results in Mecway's own format (bridge: "
        "result_route='liml'), one step with the maxima@N"
        "aster_results_export.export_results(@N"
        "    res_mecway, {fragment}, {liml},@N"
        "    precision='single', static=True, fields={fields!r})@N"
    ).replace("@N", chr(10)).format(
        fragment=b2a._py_str(b2a.results_file(work_dir)),
        liml=b2a._py_str(model_data.get("liml_path", "")),
        fields=[str(f) for f in fields])
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL',)))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    log("INFO: Spectrum analysis: {0} modes, direction(s) {1}, modal "
        "combination {2}, directions {3}, damping {4}{5}.".format(
            b2a._mode_count(model_data, analysis), ", ".join(dirs),
            modal_rule, dir_rule, zeta,
            ", missing mass" if missing else ""))
    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = b2a._read_template(analysis["template"])
        b2a._write_comm(comm_path, template.format(
            defigroup_block=defigroup_block,
            model_block=model_block,
            cara_elem_block=cara_elem_block,
            materials_block=materials_block,
            fieldmat_block=fieldmat_block,
            loads_block=loads_block,
            assemblage_block=assemblage_block,
            calc_modes_block=calc_modes_block,
            spectrum_block=spectrum_block,
            result_block=result_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        export_content = (
            "P actions make_etude\n"
            "P time_limit {time_limit}\n"
            "P memory_limit {memory_limit}\n"
            "P mpi_nbcpu 1\n"
            "P ncpus {ncpus}\n"
            "P no-mpi true\n"
            "F comm {comm} D 1\n"
            "F mail {msh} D 20\n"
            "F mess {mess} R 6"
        ).format(
            time_limit=analysis.get("time_limit", 1800),
            memory_limit=analysis.get("memory_limit", 2048),
            ncpus=CONFIG_BRIDGE["ncpus"],
            comm=comm_path, msh=msh_path,
            mess=os.path.join(work_dir, run_name(".mess")),
        ) + b2a._export_result_lines(work_dir, resu_name)
        with open(export_path, "w") as f:
            f.write(export_content)
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
# AFTER THE RUN: LOG AND STATUS BOX
# ==========================================
_LINE_RE = re.compile(r"^BRIDGE_SPECTRUM_(MODE|MASSA|CUT|REACTIE)\s*(.*)$")
_KV_RE = re.compile(r"(\w+)=(\S+)")


def read_summary(mess_path):
    """{"modes": {nr: {..}}, "massa": {..}, "cut": {..}, "reactie": {..}}
    from the BRIDGE_SPECTRUM lines (aster_spectrum.report); {} without."""
    out = {}
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = open(mess_path, "rb")
    try:
        for line in f:
            if not isinstance(line, str):     # CPython 3 (verification)
                line = line.decode("utf-8", "replace")
            m = _LINE_RE.match(line.strip())
            if not m:
                continue
            kv = {}
            for k, v in _KV_RE.findall(m.group(2)):
                try:
                    kv[k] = float(v)
                except ValueError:
                    kv[k] = v
            kind = m.group(1)
            if kind == "MODE":
                nr = int(m.group(2).split()[0])
                out.setdefault("modes", {})[nr] = kv
            else:
                out[kind.lower()] = kv
    finally:
        f.close()
    return out


def report_summary(mess_path, analysis):
    """Lines for log and status box after the run: effective mass per
    direction (WARNING below 90% without missing mass), the spectrum at the
    cut-off frequency and the total reaction. Returns the list of lines."""
    s = read_summary(mess_path)
    lines = []
    if not s:
        return lines
    mass = s.get("massa", {})
    missing = bool(analysis.get("missing_mass", True))
    for d in _DIRS:
        if d not in mass:
            continue
        frac = mass[d]
        line = tr(u"Spectrum {0}: effectieve massa van de modes {1}%",
                  u"Spectrum {0}: effective mass of the modes {1}%").format(
                      d, "%.1f" % (100.0 * frac))
        if frac < 0.9 and not missing:
            log(tr(u"WARNING: Spectrum {0}: de modes dragen {1}% van de "
                   u"massa (< 90%): reacties en spanningen zijn te laag. "
                   u"Reken meer modes (Number of modes) of zet Missing mass "
                   u"aan.",
                   u"WARNING: Spectrum {0}: the modes carry {1}% of the "
                   u"mass (< 90%): reactions and stresses are too low. "
                   u"Compute more modes (Number of modes) or switch Missing "
                   u"mass on.").format(d, "%.1f" % (100.0 * frac)))
        elif frac < 0.9:
            line += tr(u" (rest via missing mass)", u" (rest via missing "
                       u"mass)")
        log(u"INFO: " + line)
        lines.append(line)
    cut = s.get("cut", {})
    if cut:
        line = tr(u"Missing mass: afsnijfrequentie {0} Hz, spectrum {1}",
                  u"Missing mass: cut-off frequency {0} Hz, spectrum {1}"
                  ).format("%.4g" % cut.get("FREQ", 0.0), u", ".join(
                      u"{0} {1} m/s2".format(k[3:], "%.4g" % v)
                      for k, v in sorted(cut.items())
                      if k.startswith("SA_")))
        log(u"INFO: " + line)
        lines.append(line)
    rea = s.get("reactie", {})
    if rea:
        line = tr(u"Totale reactiekracht (gecombineerd): X {0} N, Y {1} N, "
                  u"Z {2} N",
                  u"Total reaction force (combined): X {0} N, Y {1} N, Z "
                  u"{2} N").format(*["%.6g" % rea.get(k, 0.0)
                                     for k in ("FX", "FY", "FZ")])
        log(u"INFO: " + line)
        lines.append(line)
    return lines
