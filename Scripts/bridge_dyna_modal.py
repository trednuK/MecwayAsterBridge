# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_dyna_modal.py
# Responsibility: response on a modal basis, Mecway Dynamic Response
# (D30) with the option Mode superposition (manual v33 sec. 6.4), to
# Code-Aster:
#   ASSEMBLAGE (RIGI_MECA, MASS_MECA)  -> CALC_MODES (the lowest maxmode
#   modes) -> load vectors (CALC_VECT_ELEM + ASSE_VECTEUR) ->
#   PROJ_BASE (generalised mass, stiffness and forces) ->
#   DYNA_VIBRA TYPE_CALCUL='TRAN', BASE_CALCUL='GENE' (modal damping,
#   NEWMARK) -> REST_GENE_PHYS (displacements and velocities at the nodes)
#   -> CALC_CHAMP (stresses) -> aster_results_export (time steps in the
#   .liml, like Mecway's own solution).
# Syntax: Code-Aster test case forma12d (17.4, share/aster/tests) and the
# catalogues dyna_vibra.py, proj_base.py, rest_gene_phys.py, calc_vect_elem.py
# of code_aster 17.4.
#
#   build_dyna_modal(...) - builder for SOLVER_BUILDERS_ASTER["DYNA_VIBRA"]
#                           (bridge_to_aster._build_dyna_modal).
#
# Behaviour of Mecway (measured headless with Mecway 33, mecway.exe <model>
# solve; verification MD in docs/Verificatie.md):
#   - The modal equations are integrated exactly: a step load on
#     a mass on a beam gave the same response with stepsize 0,02 s
#     (omega dt = 0,71) and 0,001 s, within 1e-4 of u_st (1 - cos omega t).
#     Code-Aster integrates with NEWMARK (average acceleration); the bridge
#     chooses the time step so small that the period error is negligible
#     (steps_per_period per period of the highest mode in the basis; the
#     period error of NEWMARK is (omega dt)^2 / 12, Hughes 2000, sec. 9.3).
#   - No static correction for the omitted modes: with 1 mode the
#     final displacement of a cantilever beam (point load at the tip,
#     damped) stayed 0,9707 x the static one (the contribution of mode 1),
#     with 6 modes 0,9986. The setting static_correction (default off) adds
#     that correction (MACRO_ELAS_MULT as MODE_CORR, CORR_STAT, test case
#     forma12d).
#   - Rayleigh damping (only on the whole model, manual sec. 9.26) as
#     modal damping ratio xi_i = (alpha / omega_i + beta omega_i) / 2
#     (manual sec. 9.26); xi_i < 1 for every mode (manual sec. 6.4).
#   - Output: t = 0 and every keepeverynthtimestep-th step of stepsize
#     (bridge_to_aster._output_times); displacement, rotation, velocity and
#     von Mises; no accelerations (manual sec. 6.4).
#
# Compatible with IronPython 2.7.9 (standard library only).

import math
import os
import re
from collections import OrderedDict

import bridge_to_aster as b2a
from bridge_utils import log, tr, CONFIG_BRIDGE, run_name


# Fields of the physical response (REST_GENE_PHYS NOM_CHAM) per group from
# "fields"; reactions and plastic strain do not belong to this analysis.
_STRESS_GROUPS = ("stresses", "vonmises")
_FIELD_GROUPS = ("displacements", "velocities") + _STRESS_GROUPS


def _value_names(text):
    """Names of concepts that appear as a value in a _F(...) (KW=name);
    a group name is in quotes and does not count."""
    return set(re.findall(r"=\s*([A-Za-z_]\w*)", text))


def _substitute(kws, mapping):
    """Copy of an excit dict (_build_charges) with the function names from
    mapping replaced (only as a value: after '=', not in a group name)."""
    out = OrderedDict()
    for kw, entries in kws.items():
        new = []
        for e in entries:
            for old, rep in mapping.items():
                e = re.sub(r"(=\s*){0}\b".format(re.escape(old)),
                           r"\g<1>{0}".format(rep), e)
            new.append(e)
        out[kw] = new
    return out


def _excitations(charges, timed):
    """
    Splits the loads of _build_charges into vectors, each with one
    time function: F(t) = sum_j V_j f_j(t) (linear in the function values).
    timed: names of the DEFI_FONCTIONs in time. Returns (supports,
    excitations, extra loads, errors):
      supports    : names of the loads without loading (load_k)
      excitations : [(load, function or None)] (None = constant from t = 0)
      extra       : [(name, command, excit dict)] new loads (gload_*):
                    an AFFE_CHAR_MECA_F with one function at 1 and the other
                    time functions at 0
      errors      : loads with a time-dependent support
    """
    constraints, excitations, extra, errors = [], [], [], []
    for k, (cmd, kws, fonc) in enumerate(charges):
        name = "load_{0}".format(k + 1)
        if not b2a._is_load_charge((cmd, kws, fonc)):
            if cmd == "AFFE_CHAR_MECA_F":
                errors.append(name)
            constraints.append(name)
            continue
        if cmd == "AFFE_CHAR_MECA":
            excitations.append((name, fonc))
            continue
        text = " ".join(e for es in kws.values() for e in es)
        names = _value_names(text)
        used = [f for f in timed if f in names]
        others = sorted(n for n in names if n not in timed)
        if others:
            # Constants (DEFI_CONSTANTE of beam loads) and space functions
            # (hydrostatic pressure): from t = 0, the time functions at 0.
            gname = "gload_{0}_0".format(k + 1)
            extra.append((gname, cmd, _substitute(
                kws, dict((f, "bridge_f0") for f in used))))
            excitations.append((gname, None))
        for i, f in enumerate(used):
            gname = "gload_{0}_{1}".format(k + 1, i + 1)
            mapping = dict((g, "bridge_f0") for g in used + others)
            mapping[f] = "bridge_f1"
            extra.append((gname, cmd, _substitute(kws, mapping)))
            excitations.append((gname, f))
    return constraints, excitations, extra, errors


def _check_model(model_data, analysis):
    """What the modal response cannot do: ERROR with the solution. Returns
    True if the model can be computed."""
    ok = True
    if not b2a._check_linear(model_data, tr("een respons op modale basis",
                                            "a mode superposition analysis")):
        ok = False
    dampers = [e for e, s in model_data.get("discrete_sections", {}).items()
               if s.get("kind") == "damper"]
    if dampers:
        # Mecway: "Damper elements cannot be used" (manual v33 par. 6.4).
        log(tr("ERROR: Dempers ({0}) kunnen niet in een respons op modale "
               "basis (ook niet in Mecway, manual par. 6.4). Gebruik "
               "Rayleigh-demping, of de directe analyse dyna_impl_3d "
               "(Mecway: Mode superposition uit).",
               "ERROR: Dampers ({0}) cannot be used in a mode superposition "
               "analysis (not in Mecway either, manual section 6.4). Use "
               "Rayleigh damping, or the direct analysis dyna_impl_3d "
               "(Mecway: Mode superposition off).").format(
                   ", ".join(dampers)))
        ok = False
    if model_data.get("initial_velocities"):
        log(tr("ERROR: Een beginsnelheid wordt in de respons op modale basis "
               "niet vertaald. Gebruik de directe analyse dyna_impl_3d.",
               "ERROR: An initial velocity is not translated in the mode "
               "superposition analysis. Use the direct analysis "
               "dyna_impl_3d."))
        ok = False
    if b2a._thermal_active(model_data):
        log(tr("ERROR: Thermische rek (Thermal stress) wordt in de respons "
               "op modale basis niet vertaald. Gebruik dyna_impl_3d.",
               "ERROR: Thermal strain (Thermal stress) is not translated in "
               "the mode superposition analysis. Use dyna_impl_3d."))
        ok = False
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor de respons "
               "op modale basis. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for the mode "
               "superposition analysis. Choose 'liml' (General page)."))
        ok = False
    if model_data.get("analysis_type") == "D30" and not model_data.get(
            "mode_superposition"):
        log(tr("WARNING: Het Mecway-model rekent Dynamic Response zonder Mode "
               "superposition (Newmark op het hele model); de bridge rekent "
               "op modale basis met {0} modes. Voor de directe berekening: "
               "dyna_impl_3d.",
               "WARNING: The Mecway model computes Dynamic Response without "
               "Mode superposition (Newmark on the whole model); the bridge "
               "computes on a modal basis with {0} modes. For the direct "
               "computation: dyna_impl_3d.").format(
                   b2a._mode_count(model_data, analysis)))
    return ok


def _regular_outputs(out):
    """(interval, count) if the output times are out = k * interval
    (k = 1..n), otherwise None. DYNA_VIBRA GENE uses a fixed step (PAS);
    the output times must fall on it."""
    if not out:
        return None
    inc = out[0]
    for k, t in enumerate(out):
        if abs(t - (k + 1) * inc) > 1.0e-6 * inc:
            return None
    return inc, len(out)


def _damping_text(model_data, analysis):
    """(alpha [1/s], beta [s], extra modal damping ratio)."""
    ray = model_data.get("rayleigh") or {}
    zeta = float(analysis.get("modal_damping", 0.0) or 0.0)
    return float(ray.get("alpha", 0.0) or 0.0), \
        float(ray.get("beta", 0.0) or 0.0), zeta


def _dyna_block(analysis, excitations, inc, n_out, alpha, beta, zeta,
                static_corr, fields, min_sub=1):
    """
    Damping, time step, DYNA_VIBRA and REST_GENE_PHYS (Python in the .comm:
    the frequencies are only known after CALC_MODES).
    """
    nsteps = max(4, int(analysis.get("steps_per_period", 50)))
    min_sub = max(1, int(min_sub))
    lines = [
        "# Modal damping: Mecway's Rayleigh damping C = alpha M + beta K is",
        "# per mode xi_i = (alpha / w_i + beta w_i) / 2 (Mecway manual sec.",
        "# 9.26), plus the setting modal_damping.",
        "import math as _math",
        "bridge_freqs = [float(_f) for _f in "
        "modes.getAccessParameters()['FREQ']]",
        "bridge_alpha, bridge_beta, bridge_zeta = {0!r}, {1!r}, {2!r}".format(
            alpha, beta, zeta),
        "bridge_xi = []",
        "for _f in bridge_freqs:",
        "    _w = 2.0 * _math.pi * _f",
        "    if _w <= 0.0:",
        "        # Rigid body motion or mechanism: Mecway does not allow it",
        "        # either (manual sec. 6.4); bridge_run_aster reports the cause.",
        "        print('BRIDGE_DYNA_MODAL_FOUT FREQ mode=%d f=%g' % "
        "(len(bridge_xi) + 1, _f))",
        "        raise ValueError('mode superposition: mode met f <= 0')",
        "    bridge_xi.append(0.5 * (bridge_alpha / _w + bridge_beta * _w) + "
        "bridge_zeta)",
        "for _i, (_f, _x) in enumerate(zip(bridge_freqs, bridge_xi)):",
        "    print('BRIDGE_DEMPING mode %d: %.6g Hz, xi = %.6g' % "
        "(_i + 1, _f, _x))",
        "if max(bridge_xi) >= 1.0:",
        "    # Mecway: xi < 1 for every mode (manual sec. 6.4, 9.26).",
        "    print('BRIDGE_DYNA_MODAL_FOUT DEMPING mode=%d xi=%g' % "
        "(bridge_xi.index(max(bridge_xi)) + 1, max(bridge_xi)))",
        "    raise ValueError('mode superposition: dempingsverhouding >= 1')",
        "",
        "# Time step: {0} steps per period of the highest mode (NEWMARK,".format(
            nsteps),
        "# period error (w dt)^2 / 12), a whole number per output interval,",
        "# at least {0}: never larger than Mecway's step (also with".format(
            min_sub),
        "# 'Generate solution every n time steps').",
        "bridge_inc, bridge_nout = {0!r}, {1}".format(inc, n_out),
        "bridge_nsub = max({1}, int(_math.ceil(bridge_inc * max(bridge_freqs) "
        "* {0})))".format(nsteps, min_sub),
        "bridge_pas = bridge_inc / bridge_nsub",
        "print('BRIDGE_DYNA_MODAL rekenstap %g s (%d per uitvoerinterval), "
        "%d stappen' % (bridge_pas, bridge_nsub, bridge_nsub * bridge_nout))",
        "",
    ]
    excit = []
    for k, (charge, fonc) in enumerate(excitations):
        f = fonc or "bridge_f1"
        entry = "_F(VECT_ASSE_GENE=fgen_{0}, FONC_MULT={1}".format(k + 1, f)
        if static_corr:
            entry += ", CORR_STAT='OUI', D_FONC_DT={0}, D_FONC_DT2={1}".format(
                "dfdt_{0}".format(k + 1) if fonc else "bridge_f0",
                "d2fdt_{0}".format(k + 1) if fonc else "bridge_f0")
        excit.append(entry + ")")
    if static_corr:
        # Static correction (test case forma12d): the static response to
        # each load vector (MACRO_ELAS_MULT) as MODE_CORR, with the
        # first and second derivative of the time function (CALC_FONCTION
        # DERIVE; 0 for a constant load).
        for k, (charge, fonc) in enumerate(excitations):
            if fonc:
                lines += [
                    "dfdt_{0} = CALC_FONCTION(DERIVE=_F(FONCTION={1}))".format(
                        k + 1, fonc),
                    "d2fdt_{0} = CALC_FONCTION(DERIVE=_F(FONCTION=dfdt_{0}))"
                    .format(k + 1),
                ]
    lines += [
        "tran = DYNA_VIBRA(",
        "    TYPE_CALCUL='TRAN',",
        "    BASE_CALCUL='GENE',",
        "    SCHEMA_TEMPS=_F(SCHEMA='NEWMARK'),",
        "    MATR_MASS=mgen,",
        "    MATR_RIGI=kgen,",
        "    AMOR_MODAL=_F(AMOR_REDUIT=bridge_xi),",
        "    INCREMENT=_F(PAS=bridge_pas, INST_FIN=bridge_inc * bridge_nout),",
        "    ARCHIVAGE=_F(PAS_ARCH=bridge_nsub),",
        "    EXCIT=(",
    ] + ["        {0},".format(e) for e in excit] + ["    ),"]
    if static_corr:
        lines.append("    MODE_CORR=corr,")
    lines += [")", ""]
    cham = ["DEPL"]
    if "velocities" in fields:
        cham.append("VITE")
    if any(f in fields for f in _STRESS_GROUPS):
        # SIPM_ELNO (beams) on a DYNA_TRANS without accelerations gave
        # alarm CALCULEL3_1 "Il manque les accélérations" (Code-Aster 17.4,
        # seen); the accelerations do not go to Mecway (like Mecway).
        cham.append("ACCE")
    lines += [
        "res = REST_GENE_PHYS(",
        "    RESU_GENE=tran,",
        "    TOUT_INST='OUI',",
        "    NOM_CHAM=({0},),".format(", ".join("'{0}'".format(c)
                                               for c in cham)),
    ]
    if static_corr:
        lines.append("    CORR_STAT='OUI',")
    lines += [")", ""]
    return "\n".join(lines)


def build_dyna_modal(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate the .comm and .export for the response on a modal basis
    (analysis dyna_modal_3d, solver_command DYNA_VIBRA). Returns the path of
    the .export, or None (ERROR logged).
    """
    log("--- Generating Aster Files (DYNA_VIBRA GENE) ---")
    if not _check_model(model_data, analysis):
        return None
    comm_path = os.path.join(work_dir, run_name(".comm"))

    load_funcs = b2a._collect_load_funcs(model_data)
    func_names = b2a._load_func_names(model_data)
    timed = [name for name, _h in load_funcs]
    charges = b2a._build_charges(model_data, func_names)
    constraints, excitations, extra, errors = _excitations(charges, timed)
    if errors:
        log(tr("ERROR: Een tijdsafhankelijke opgelegde verplaatsing kan niet "
               "in de respons op modale basis (de modes hebben die "
               "vrijheidsgraden vast). Gebruik dyna_impl_3d.",
               "ERROR: A time-dependent imposed displacement is not possible "
               "in the mode superposition analysis (the modes have those "
               "degrees of freedom fixed). Use dyna_impl_3d."))
        return None
    nonzero = b2a._nonzero_imposed(model_data)
    if nonzero:
        log(tr("ERROR: Opgelegde verplaatsing of rotatie <> 0 op {0}: dat "
               "kan niet in de respons op modale basis (de modes hebben die "
               "vrijheidsgraden vast). Zet de waarde op 0, of gebruik "
               "dyna_impl_3d.",
               "ERROR: Imposed displacement or rotation <> 0 on {0}: not "
               "possible in the mode superposition analysis (the modes have "
               "those degrees of freedom fixed). Set the value to 0, or use "
               "dyna_impl_3d.").format(
                   ", ".join("'{0}'".format(s) for s in nonzero)))
        return None
    custom_excit = model_data.get("aster_custom", {}).get("excit", [])
    if not constraints and not custom_excit:
        # Mecway: "Rigid body motion is not allowed so the model must be
        # fully constrained" (manual v33 sec. 6.4).
        log(tr("ERROR: Respons op modale basis zonder opleggingen: starre "
               "bewegingen kunnen niet (ook niet in Mecway, manual par. "
               "6.4). Leg het model in Mecway vast.",
               "ERROR: Mode superposition analysis without supports: rigid "
               "body motion is not possible (not in Mecway either, manual "
               "section 6.4). Add supports in Mecway."))
        return None
    if not excitations:
        log(tr("WARNING: Geen belastingen: de respons is overal 0.",
               "WARNING: No loads: the response is zero everywhere."))

    out = b2a._output_times(model_data, analysis)
    reg = _regular_outputs(out)
    if reg is None:
        log(tr("ERROR: De uitvoertijden ({0} ... {1} s) liggen niet op een "
               "regelmatig raster vanaf 0; DYNA_VIBRA rekent met een vaste "
               "stap. Kies in Mecway een eindtijd die een veelvoud is van "
               "de tijdstap.",
               "ERROR: The output times ({0} ... {1} s) are not on a regular "
               "grid from 0; DYNA_VIBRA uses a constant step. Choose an end "
               "time in Mecway that is a multiple of the time step.").format(
                   out[0] if out else "?", out[-1] if out else "?"))
        return None
    inc, n_out = reg
    log("INFO: Response on a modal basis: {0} output times, interval {1} s, "
        "end time {2} s.".format(n_out, inc, out[-1]))

    fields = [f for f in analysis.get("fields", ["displacements"])
              if f in _FIELD_GROUPS]
    ignored = [f for f in analysis.get("fields", []) if f not in
               _FIELD_GROUPS]
    if "displacements" not in fields:
        fields.insert(0, "displacements")
    if ignored:
        log("INFO: Response on a modal basis: fields {0} are not "
            "computed (no reactions or plastic strain).".format(
                ", ".join(ignored)))
    static_corr = bool(analysis.get("static_correction", False))
    alpha, beta, zeta = _damping_text(model_data, analysis)

    defigroup_block = b2a._build_defigroup_block(model_data)
    model_block = b2a._build_model_block(model_data)
    cara_elem_block = b2a._build_cara_elem_block(model_data)
    cara_ref = "    CARA_ELEM=cara,\n" if b2a._has_cara(model_data) else ""
    materials_block = b2a._build_materials_block(model_data, analysis)
    fieldmat_block = b2a._build_fieldmat_block(model_data)
    load_funcs_block = b2a._build_load_funcs_block(load_funcs)
    loads_block, _excit = b2a._render_charges(charges, model_data)
    consts = ("bridge_f0 = DEFI_CONSTANTE(VALE=0.0)\n"
              "bridge_f1 = DEFI_CONSTANTE(VALE=1.0)\n")
    loads_block = consts + loads_block + "\n" + "".join(
        b2a._render_char_meca(n, c, k) for n, c, k in extra)

    charge_names = list(constraints) + [n for n in custom_excit
                                        if n not in constraints]
    charge_ref = ""
    if charge_names:
        charge_ref = "    CHARGE=({0},),\n".format(", ".join(charge_names))
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}{charge}"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('rigidite'), OPTION='RIGI_MECA'),\n"
        "        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n"
        "    ),\n"
        ")\n").format(cara=cara_ref, charge=charge_ref)

    scripts = os.path.dirname(os.path.abspath(__file__))
    calc_modes_block = b2a._calc_modes_block(
        model_data, analysis, False, cara_ref).replace(
            "res = CALC_MODES(", "modes = CALC_MODES(", 1)
    calc_modes_block += (
        "# Mode overview (frequency, effective mass) in the .mess\n"
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
                k + 1, charge, ", CARA_ELEM=cara" if cara_ref else ""),
            "vec_{0} = ASSE_VECTEUR(VECT_ELEM=vel_{0}, NUME_DDL=numedd)"
            .format(k + 1),
        ]
    if excitations:
        # Load resultant for the warning on missing modal mass
        # (MecwayAsterBridgeMain._warn_modal_mass)
        proj.append("aster_results_export.print_excitation([{0}])".format(
            ", ".join("vec_{0}".format(k + 1)
                      for k in range(len(excitations)))))
    proj += [
        "PROJ_BASE(",
        "    BASE=modes,",
        "    STOCKAGE='DIAG',",
        "    MATR_ASSE_GENE=(",
        "        _F(MATRICE=CO('mgen'), MATR_ASSE=masse),",
        "        _F(MATRICE=CO('kgen'), MATR_ASSE=rigidite),",
        "    ),",
    ]
    if excitations:
        proj.append("    VECT_ASSE_GENE=(")
        proj += ["        _F(VECTEUR=CO('fgen_{0}'), VECT_ASSE=vec_{0}, "
                 "TYPE_VECT='FORC'),".format(k + 1)
                 for k in range(len(excitations))]
        proj.append("    ),")
    proj += [")", ""]
    if static_corr and excitations:
        # Static response per load vector (test case forma12d:
        # MACRO_ELAS_MULT with the supports as CHAR_MECA_GLOBAL).
        proj += [
            "corr = MACRO_ELAS_MULT(",
            "    MODELE=model,",
            "    CHAM_MATER=fieldmat,",
        ] + (["    CARA_ELEM=cara,"] if cara_ref else []) + [
            "    NUME_DDL=numedd,",
            "    CHAR_MECA_GLOBAL=({0},),".format(", ".join(charge_names)),
            "    CAS_CHARGE=(",
        ] + ["        _F(NOM_CAS='c{0}', CHAR_MECA={1}),".format(k + 1, c)
             for k, (c, _f) in enumerate(excitations)] + [
            "    ),",
            ")",
            "",
        ]
        log("INFO: Static correction for the omitted modes "
            "(MACRO_ELAS_MULT, CORR_STAT).")
    elif static_corr:
        static_corr = False
    projection_block = "\n".join(proj)
    if not excitations:
        # Without loading a zero vector, so that DYNA_VIBRA has an EXCIT.
        excitations = []
    # Mecway's step size bounds the solver step: with "Generate solution
    # every n time steps" the output interval is n steps.
    step = b2a._mecway_dyna_step(model_data)
    min_sub = max(1, int(math.ceil(inc / step - 1.0e-6))) if step else 1
    dyna_block = _dyna_block(analysis, excitations, inc, n_out, alpha, beta,
                             zeta, static_corr, fields, min_sub)
    if not excitations:
        dyna_block = dyna_block.replace("    EXCIT=(\n    ),\n", "")

    calc_champ_block = "#-- no stresses requested (fields) --\n"
    if any(f in fields for f in _STRESS_GROUPS):
        calc_champ_block = (
            "# Stresses on the physical response (linear in the "
            "displacements)\n" + _with_model(b2a._build_calc_champ_block(
                model_data, reactions=False), bool(cara_ref)))
    export_block = b2a._custom_code(model_data, "post") + (
        "# Results in Mecway's own format (bridge: "
        "result_route='liml')@N"
        "aster_results_export.export_results(@N"
        "    res, {fragment}, {liml},@N"
        "    extra_results=dict((k, globals()[k]) for k in@N"
        "                       ('res_sup', 'res_moy', 'res_inf')@N"
        "                       if k in globals()),@N"
        "    precision='single', static=False, fields={fields!r}"
        "{formulas})@N"
    ).replace("@N", chr(10)).format(
        fragment=b2a._py_str(b2a.results_file(work_dir)),
        liml=b2a._py_str(model_data.get("liml_path", "")),
        fields=[str(f) for f in fields],
        formulas=b2a.formulas_arg(model_data))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL',)))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    log("INFO: Response on a modal basis: {0} modes, {1} load vector(s), "
        "Rayleigh alpha {2} 1/s, beta {3} s, extra modal damping {4}{5}."
        .format(b2a._mode_count(model_data, analysis), len(excitations),
                alpha, beta, zeta, ", static correction" if static_corr
                else ""))
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
            dyna_block=dyna_block,
            calc_champ_block=calc_champ_block,
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


def _with_model(block, cara):
    """CALC_CHAMP on the result of REST_GENE_PHYS: MODELE, CHAM_MATER
    (and CARA_ELEM) explicitly, after each 'RESULTAT=res,'."""
    head = "res = CALC_CHAMP(\n    reuse=res,\n    RESULTAT=res,\n"
    add = "    MODELE=model,\n    CHAM_MATER=fieldmat,\n"
    if cara:
        add += "    CARA_ELEM=cara,\n"
    return block.replace(head, head + add)
