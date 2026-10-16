# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_utils.py
# Shared helper file: configuration, logging and unit conversion.
# Compatible with IronPython 2.7.9 (Mecway scripting engine).
#
# Place in the module architecture:
#   - Imported by ALL other bridge_* modules.
#   - Has no import dependencies on other bridge_* modules,
#     to avoid circular imports.

import io
import os
import re
import math
from datetime import datetime


# Version of the bridge (start screen, log header, CHANGELOG.md). Kept
# outside CONFIG_BRIDGE on purpose: the start screen rewrites only that block.
BRIDGE_VERSION = "V2026.1"

# Tested versions (bridge_version.py): a different version only gives a
# WARNING, the run continues. Mecway: the version attribute of <liml>;
# Code-Aster: major.minor. Update after a successful regression, see
# docs/Na_een_update.md.
TESTED_MECWAY_VERSIONS = ("33", "34")
TESTED_ASTER_VERSIONS = ("17.4",)


# ==========================================
# CONFIGURATION
# ==========================================
CONFIG_BRIDGE = {
    # --- Installation / project (independent of the analysis) ---

    # Language of the start screen, messages, WARNING/ERROR log lines and the
    # convergence window: "nl" (Dutch) or "en" (English). See tr().
    "language":        "en",

    # Path to the run_aster.bat launcher of Code-Aster. Environment variables
    # (%LOCALAPPDATA%) and ~ are expanded on use (exe_aster_path()).
    # Default: the location where the Windows package (MSI) installs
    # Code-Aster 17.4.
    "exe_aster":       r"%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat",

    # Working directory: each run writes <model>_<run_id>.comm, .export,
    # .mess, the result file, the log etc. here (run_name). Empty ("") = the
    # folder WorkDir next to the folder Scripts (work_dir_path()); environment
    # variables and ~ are expanded.
    "work_dir":        "",

    # Number of CPU cores (threads) for Code-Aster (ncpus=1 = no parallelism)
    "ncpus":           1,
    # First run a Mecway solve as a check for model errors
    # (mw.solve(); the Mecway API documents no return value).
    "mecway_solve_first": False,
    # Results to Mecway: "liml" = Code-Aster writes Mecway's own
    # result format (all time steps, small file) and the bridge reopens
    # the .liml; "tabel" = POST_RELEVE_T tables + set_variable()
    # (node values only, existing Mecway time steps only).
    "result_route":    "liml",
    # Open the convergence and message window (aster_convergence_monitor.py,
    # separate window) as soon as Code-Aster starts; for a linear analysis
    # the statistics of the linear solver, the messages and the diagnosis.
    "convergence_monitor": True,
    # Waiting for Code-Aster (bridge_run_aster): "auto" = modal status
    # window with a Stop button, results loaded automatically when the run
    # has ended; "confirm" = click OK when Code-Aster has finished.
    "wait_for_aster":  "auto",
    # Also write a MED file (<model>_<run_id>.rmed) for
    # ParaView/Salome. Mecway does not use it; it can reach hundreds of MB.
    "med_export":      False,

    # --- Element formulation (applies to all analyses) ---
    # Hex8 solid elements: "3D" (fully integrated) or "3D_SI"
    # (reduced integration; only if an elset has hex8 only, not
    # with an explicit scheme). Note: 3D_SI with 1 element through the
    # thickness gives ~0 bending stress (KNOWN_BUGS 1). "LINE_QUAD": Code-Aster
    # makes all linear solid elements quadratic (only with solid elements
    # only, not explicit).
    "elem_hex8":       "3D",
    # Linear shells (tri3/quad4): "DKT" (Kirchhoff, thin) or "DST"
    # (Mindlin, with transverse shear). DST only with MECA_STATIQUE (nonlinear
    # not in Code-Aster, then DKT); quadratic shells stay COQUE_3D.
    # "COQUE_3D": linear shells first made quadratic (LINE_QUAD + QUAD8_9).
    "elem_shell":      "DKT",
    # Beams (line2/line3): "POU_D_E" (Euler, like Mecway) or "POU_D_T"
    # (Timoshenko; AY/AZ for general sections: bridge_from_liml.py).
    "elem_beam":       "POU_D_E",

    # NOTE: the values in this CONFIG_BRIDGE block are rewritten line by line
    # by the start screen (bridge_gui.py). Keep the pattern
    #  "key": value,  for every key (one key per line, comma after it;
    # only lists may span several lines).

    # --- Analysis selection ---
    # Which analysis from "analyses" below is used for this run.
    # "auto": follow the analysis type of the Mecway model (see
    # MECWAY_ANALYSIS_TYPES below this block); the choice applies to that run only.
    "active_analysis": "auto",
    # Configuration (Mecway: Edit > New configuration) that the bridge solves
    # and in which <solution configuration=".."> the results go. "auto":
    # the only configuration, else the only one without suppressed items,
    # else the first (choose_configuration); or the name of a
    # configuration. A name that is not in the model: WARNING and "auto".
    # The start screen shows the configurations of the open model.
    "configuration":   "auto",

    # --- Registry of supported analyses ---
    # Template per analysis ("template"): a file name is in the folder
    # of these scripts (Scripts/, template_path()); an absolute path is
    # also allowed (own template elsewhere).
    # One template per analysis type (MECA_STATIQUE, STAT_NON_LINE, ...)
    # because solver calls differ fundamentally in structure, not only
    # in parameters.
    "analyses": {
        "lin_static_3d": {
            # .comm template with placeholders for the generator in bridge_to_aster.py
            "template":       "AsterTemplate_MecaStatique.comm",
            "solver_command": "MECA_STATIQUE",
            # Result fields to be extracted.
            # Names refer to entries in RESULT_FIELD_SPECS in bridge_from_aster.py.
            # Unknown names are skipped with a log warning.
            # Extra fields (bridge_to_aster._optional_fields; only something if
            # the model has elements for them): beam_forces, shell_forces,
            # safety_factor on by default; strain and shell_stresses off
            # (larger .liml).
            "fields":         ["displacements", "stresses", "vonmises", "reactions",
                               "beam_forces", "shell_forces", "safety_factor"],
            # study.export: time limit [s] and memory limit [MB] for run_aster.
            "time_limit":     600,
            "memory_limit":   2048,
            # MUMPS NPREC: allowed number of lost digits (Code-Aster default 8,
            # here too; -1 = singularity check off, RESI_RELA then checks
            # the residual).
            "solver_nprec":   8,
            # Linear solver (bridge_to_aster._build_lin_solveur_ref):
            # "MUMPS" (direct, default) or "GCPC" (iterative, conjugate
            # gradient with PRE_COND='LDLT_INC'; residual per iteration in the
            # convergence window). PETSC is not in the Windows version.
            "lin_solver":     "MUMPS",
            # SOLVEUR RESI_RELA: MUMPS = limit for the estimated relative
            # error of the solution; GCPC = convergence criterion ||r||/||f||.
            "lin_solver_resi": 1.0e-6,
            # Error estimator (CALC_ERREUR ERME, residual estimator, solid
            # elements only): estimated discretisation error per element and
            # node to Mecway (errorestimate*) and the global relative
            # error in the log; see docs/Foutschatter.md.
            "error_estimator": True,
            # Fracture mechanics (SCHEUR_ selections, bridge_fracture.py,
            # docs/Breukmechanica.md): inner and outer radius [m] of the
            # theta field of CALC_G; both 0 = automatic (Code-Aster).
            # Smoothing along the front: "LINEAIRE" (Lagrange, per node)
            # or "LEGENDRE" (polynomial of fracture_legendre_degree).
            "fracture_r_inf": 0.0,
            "fracture_r_sup": 0.0,
            "fracture_smoothing": "LINEAIRE",
            "fracture_legendre_degree": 5,
            # Adaptive refinement (bridge_adapt.py, docs/Foutschatter.md
            # sec. 6): after the run refine the elements with the largest error
            # in Mecway (mw.refine_x2) and solve again, until the
            # global relative error [%] is below the target or a limit
            # (loops, elements) is reached. adapt_select: dorfler / fraction
            # / factor with adapt_fraction as value; adapt_neighbours:
            # also the elements that share a node with the selection.
            "adapt_refine":       False,
            "adapt_target_error": 2.0,
            "adapt_max_loops":    5,
            "adapt_select":       "dorfler",
            "adapt_fraction":     0.5,
            "adapt_neighbours":   False,
            "adapt_max_elements": 200000,
        },
        "nonlin_static_3d": {
            # .comm template for STAT_NON_LINE
            "template":       "AsterTemplate_StatNonLine.comm",
            "solver_command": "STAT_NON_LINE",
            "fields":         ["displacements", "stresses", "vonmises",
                               "reactions", "plastic_strain",
                               "plastic_strain_eq", "beam_forces",
                               "shell_forces", "safety_factor", "contact"],
            # Tunables for STAT_NON_LINE.
            # substeps_per_interval: solver steps per interval of the
            #   load table, only without Mecway's step size (<timesteps
            #   stepsize>; with it, one step per Mecway step).
            #   Higher = more robust convergence but longer runtime.
            # newton_max_iter:       maximum Newton iterations per substep.
            # convergence_resi_rela: relative residual for convergence.
            # default_time_end:      used if no time-dependent load exists
            #                        but STAT_NON_LINE is still wanted.
            "substeps_per_interval": 10,
            "newton_max_iter":       20,
            "convergence_resi_rela": 1.0e-5,
            # Convergence criterion (CONVERGENCE, U4.51.03): "RELA" =
            # RESI_GLOB_RELA (residual / external forces, Code-Aster default)
            # or "MAXI" = RESI_GLOB_MAXI (largest residual force in N,
            # convergence_resi_maxi). MAXI for an imposed displacement without
            # resistance (external forces ~0). "RELA_OF_MAXI"
            # = both with VERIF='AU_MOINS_UN': either one suffices.
            "convergence_criterion": "RELA",
            "convergence_resi_maxi": 1.0e-3,
            # Contact (DEFI_CONTACT CONTINUE, per zone): "STANDARD" =
            # Lagrange, no penetration; "PENALISATION" = spring with Mecway's
            # normalstiffness (COEF_PENA_CONT, Pa/m) and with friction
            # tangentialstiffness (COEF_PENA_FROT), like Mecway/CCX.
            "contact_algo":          "STANDARD",
            "default_time_end":      1.0,
            # Strain definition of Mecway's <hardeningcurve strain="...">.
            # Code-Aster TRACTION expects TOTAL strain and no point with
            # zero abscissa (U4.43.01 sec. 5.1.1); bridge_to_aster.py converts.
            #   "plastic" : strain = plastic strain  (EPSI = eps_p + sigma/E)
            #   "total"   : strain = total strain    (start point (0, 0) dropped)
            #   "auto"    : derived from the first point; (0, 0) or strain > 0
            #               -> total, (0, sigma>0) -> plastic + WARNING.
            # Mecway reads the curve as total strain (tested headless with
            # Mecway/CCX during the docs review; no official documentation).
            "plastic_strain_definition": "auto",
            # study.export: time limit [s] and memory limit [MB] for run_aster.
            "time_limit":            1800,
            "memory_limit":          4096,
            # COMPORTEMENT DEFORMATION (U4.51.11 sec. 4.6): "PETIT",
            # "GDEF_LOG", "GREEN_LAGRANGE", "GROT_GDEP", "PETIT_REAC",
            # "SIMO_MIEHE". Default "GROT_GDEP": Mecway's nonlinear
            # statics (L30) is always geometrically nonlinear; the
            # dynamic analyses follow that (choice, for dynamics NOT
            # verified). The bridge picks the allowed form per element type
            # (bridge_to_aster._deformation_for: solid GREEN_LAGRANGE/
            # GDEF_LOG, COQUE_3D GROT_GDEP; beams and DKT/DST stay
            # geometrically linear, with a WARNING).
            "deformation":           "GROT_GDEP",
            # NEWTON REAC_ITER (U4.51.03): how often the tangent matrix is
            # recomputed relative to the Newton iterations; 0 = not recomputed
            # within the time step. Code-Aster default is 1.
            "newton_reac_iter":      1,
            # MUMPS NPREC (see lin_static_3d).
            "solver_nprec":          8,
            # Element failure (bridge_failure.py): elements with a
            # plastic strain above the limit get E x stiffness_factor and
            # zero stress. Limit per material: #ASTER-BEZWIJKEN, PLAS_TAB
            # Eps_p_max or failure_plastic_strain (> 0: all plastic
            # materials without their own limit; 0 = off).
            "element_failure":       True,
            "failure_plastic_strain": 0.0,
            "failure_stiffness_factor": 1.0e-6,
            # Nonlinear buckling (bridge_to_aster._crit_stab_block,
            # _imperfection_block; docs/Modaal_en_knik.md sec. 5).
            # crit_stab: CRIT_STAB in STAT_NON_LINE, per step the critical
            # load factor of the current state (log and status box).
            # imperfection_amplitude: 0 = no imperfection; otherwise first
            # linear buckling and deform the mesh with buckling mode
            # imperfection_mode (largest displacement = amplitude), in m
            # or (imperfection_unit "L") as a fraction of the largest
            # dimension of the model.
            "crit_stab":             False,
            "imperfection_amplitude": 0.0,
            "imperfection_mode":     1,
            "imperfection_unit":     "m",
            # RESI_RELA of the MECA_STATIQUE of the imperfection (linear
            # buckling before STAT_NON_LINE; see lin_static_3d). STAT_NON_LINE
            # itself does not check it (Code-Aster default -1).
            "lin_solver_resi":       1.0e-6,
        },
        "dyna_impl_3d": {
            # Nonlinear dynamics, implicit (Mecway D31). Same
            # materials, loads and contact as nonlin_static_3d.
            "template":       "AsterTemplate_DynaNonLine.comm",
            "solver_command": "DYNA_NON_LINE",
            "fields":         ["displacements", "stresses", "vonmises",
                               "velocities", "reactions", "plastic_strain_eq",
                               "beam_forces", "safety_factor", "contact"],
            # SCHEMA_TEMPS (U4.53.01): "HHT" (numerical damping via
            # hht_alpha, -0.3..0) or "NEWMARK" (average acceleration).
            "schema":                "HHT",
            "hht_alpha":             -0.1,
            # Solver steps per output interval of Mecway's <timesteps>;
            # on divergence Code-Aster splits the step in 4 (up to 6 levels).
            "substeps_per_output":   1,
            "newton_max_iter":       20,
            "convergence_resi_rela": 1.0e-5,
            # See nonlin_static_3d.
            "convergence_criterion": "RELA",
            "convergence_resi_maxi": 1.0e-3,
            "contact_algo":          "STANDARD",
            "newton_reac_iter":      1,
            # ENERGIE=_F() (U4.53.01 sec. 3.22): energy balance per step in
            # study.mess (convergence window). Not with contact CONTINUE
            # (MECANONLINE5_15); then the bridge leaves it out.
            "energy_balance":        False,
            "default_time_end":      1.0,
            "plastic_strain_definition": "auto",
            # See nonlin_static_3d.
            "deformation":           "GROT_GDEP",
            "time_limit":            7200,
            "memory_limit":          4096,
            "solver_nprec":          8,
            # Element failure: see nonlin_static_3d (checked at the
            # output times).
            "element_failure":       True,
            "failure_plastic_strain": 0.0,
            "failure_stiffness_factor": 1.0e-6,
        },
        "dyna_expl_3d": {
            # Nonlinear dynamics, explicit (DIFF_CENT). Code-Aster has
            # no mass scaling: the step follows from the smallest element.
            "template":       "AsterTemplate_DynaNonLine.comm",
            "solver_command": "DYNA_NON_LINE",
            "fields":         ["displacements", "stresses", "vonmises",
                               "velocities", "reactions", "plastic_strain_eq",
                               "beam_forces", "safety_factor", "contact"],
            "schema":                "DIFF_CENT",
            # Time step = factor * estimated critical time step (STOP_CFL
            # checks the real limit).
            "explicit_dt_factor":    0.5,
            # See nonlin_static_3d.
            "contact_algo":          "STANDARD",
            "default_time_end":      1.0,
            "plastic_strain_definition": "auto",
            # See nonlin_static_3d.
            "deformation":           "GROT_GDEP",
            "time_limit":            7200,
            "memory_limit":          4096,
            "solver_nprec":          8,
            # Element failure: see nonlin_static_3d (checked at the
            # output times).
            "element_failure":       True,
            "failure_plastic_strain": 0.0,
            "failure_stiffness_factor": 1.0e-6,
        },
        "ther_3d": {
            # Thermal, steady state (Mecway T30) or transient (T31); the
            # bridge picks THER_LINEAIRE, or THER_NON_LINE with radiation or
            # convection/radiation on shell faces (bridge_thermal.py).
            "template":       "AsterTemplate_Thermique.comm",
            "solver_command": "THER_LINEAIRE",
            "fields":         ["temperature", "heat_flux"],
            # SCHEMA_TEMPS THETA (transient; 0 = explicit, 1 = implicit
            # Euler, Code-Aster default 0.57; catalogue ther_lineaire.py).
            "theta":                 0.57,
            # THER_NON_LINE only: Newton iterations, residual, REAC_ITER.
            "newton_max_iter":       20,
            "convergence_resi_rela": 1.0e-6,
            "newton_reac_iter":      1,
            # Only the chain thermal -> mechanical (T31 with Thermal
            # stress, bridge_thermomech.py): COMPORTEMENT DEFORMATION of
            # STAT_NON_LINE (welding: small strains, PETIT) and the strain
            # definition of a hardening curve (see nonlin_static_3d). Newton and
            # convergence: the settings above.
            "deformation":           "PETIT",
            "plastic_strain_definition": "auto",
            "time_limit":            1800,
            "memory_limit":          4096,
            "solver_nprec":          8,
        },
        "modal_3d": {
            # Modal analysis (Mecway V30): natural frequencies and
            # mode shapes with CALC_MODES (U4.52.02); see
            # bridge_to_aster._build_modal and docs/Modaal_en_knik.md.
            "template":       "AsterTemplate_CalcModes.comm",
            "solver_command": "CALC_MODES",
            # CALC_MODES TYPE_RESU: "DYNAMIQUE" (vibrations).
            "type_resu":      "DYNAMIQUE",
            # Mode shapes (DEPL), like Mecway's own modal
            # solution; with "stresses"/"vonmises" also stresses per mode
            # (bridge_to_aster._modal_stress_fields); other fields are
            # ignored.
            "fields":         ["displacements"],
            # Number of modes if the Mecway model has no maxmode
            # (<analysis type="V30" maxmode="..">).
            "modal_modes":    10,
            # Search frequency [Hz]: 0 = the lowest modes (OPTION
            # 'PLUS_PETITE'); > 0 = the modes closest to this
            # frequency (OPTION 'CENTRE'); < 0 = also the lowest modes,
            # for a model with a mechanism (rigid body modes).
            "modal_shift_hz": 0.0,
            # Normalisation of the mode shapes (NORM_MODE NORME):
            # "MASS_GENE" = generalised mass 1, like Mecway;
            # "TRAN_ROTA" = largest component 1 (Code-Aster default).
            "modal_norm":     "MASS_GENE",
            # VERI_MODE SEUIL: limit for the relative error
            # ||K x - w^2 M x|| / ||K x|| per mode (Code-Aster default 1e-6).
            "modal_tolerance": 1.0e-6,
            # Prestress from the loads (stress stiffening): True =
            # like Mecway (with loads first MECA_STATIQUE, then the
            # modes with K + Kg); False = ignore the loads (WARNING).
            "modal_prestress": True,
            # Complex modes with damping (Rayleigh, dampers): False = real
            # modes without damping, like Mecway; True = CALC_MODES with
            # MATR_AMOR (damped frequency and zeta per mode,
            # bridge_modal_damping.py).
            "modal_complex":  False,
            # Cyclic symmetry (bridge_cyclic.py, MODE_ITER_CYCL): number of
            # sector modes with fixed cut faces in the basis; 0 = automatic
            # max(20, 4 x the number of modes per nodal diameter).
            "cyclic_base_modes": 0,
            # Cyclic symmetry: True = the modes on the whole wheel to
            # Mecway (all N sectors, like Mecway's own solution;
            # DEFI_SQUELETTE + REST_SOUS_STRUC SQUELETTE); False = the
            # sector only.
            "cyclic_full_wheel": True,
            "time_limit":     900,
            "memory_limit":   2048,
            # MUMPS NPREC (see lin_static_3d).
            "solver_nprec":   8,
            # RESI_RELA of the static step for the prestress (see
            # lin_static_3d; bridge_to_aster._static_step_solveur).
            "lin_solver_resi": 1.0e-6,
        },
        "dyna_modal_3d": {
            # Response on a modal basis (Mecway D30 with Mode superposition):
            # CALC_MODES, PROJ_BASE, DYNA_VIBRA BASE_CALCUL='GENE' and
            # REST_GENE_PHYS; see bridge_dyna_modal.py and
            # docs/Modaal_en_knik.md.
            "template":       "AsterTemplate_DynaVibra.comm",
            "solver_command": "DYNA_VIBRA",
            # Like Mecway's mode superposition: displacements, rotations
            # and velocities (no accelerations, no reactions); stresses
            # with CALC_CHAMP on the physical response.
            "fields":         ["displacements", "velocities", "stresses",
                               "vonmises"],
            # Number of modes if the Mecway model has no maxmode.
            "modal_modes":    10,
            # Solver steps per period of the highest mode in the basis
            # (NEWMARK; Mecway solves the modal equations exactly).
            "steps_per_period": 50,
            # Extra modal damping ratio for all modes (on top of
            # Mecway's Rayleigh damping); 0 = Mecway only.
            "modal_damping":  0.0,
            # Static correction for the omitted modes (MACRO_ELAS_MULT,
            # CORR_STAT); Mecway does not do that.
            "static_correction": False,
            "modal_tolerance": 1.0e-6,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "harmonic_3d": {
            # Harmonic response in the frequency domain (Mecway has
            # no harmonic analysis; a V30 or D30 model): CALC_MODES,
            # DYNA_VIBRA TYPE_CALCUL='HARM' on a modal basis (GENE) or
            # direct (PHYS); see bridge_harmonic.py and
            # docs/Respons_op_modale_basis.md. Choose it yourself (not 'auto').
            "template":       "AsterTemplate_Harmonisch.comm",
            "solver_command": "DYNA_VIBRA",
            # bridge_to_aster._build_dyna_modal passes this analysis on
            # to bridge_harmonic.build_harmonic.
            "type_calcul":    "HARM",
            # Per frequency amplitude, phase, Re/Im (displacements); also
            # velocities/accelerations (amplitude) and stresses/vonmises
            # (solid elements).
            "fields":         ["displacements", "accelerations", "stresses",
                               "vonmises"],
            # Number of modes if the Mecway model has no maxmode.
            "modal_modes":    10,
            "modal_tolerance": 1.0e-6,
            # "GENE" = on a modal basis (default); "PHYS" = directly on the
            # whole model (check; Rayleigh and dampers, no modal_damping).
            "harm_basis":     "GENE",
            # Frequencies [Hz]: harm_freq_count steps from start to end
            # (spacing "lin" or "log"), or a list in harm_freq_list
            # (text, e.g. "5, 10, 20"; "0" = use the range).
            "harm_freq_start": 1.0,
            "harm_freq_end":  100.0,
            "harm_freq_count": 100,
            "harm_freq_spacing": "lin",
            "harm_freq_list": "0",
            # Extra frequencies per mode in the range, across the
            # half-power bandwidth (DEFI_LIST_FREQ LARGEUR_3DB); 0 = none.
            "harm_refine_points": 5,
            # Extra modal damping ratio for all modes (on top of
            # Mecway's Rayleigh damping, GENE only).
            "modal_damping":  0.0,
            # Static enrichment of the modal basis (GENE; like
            # DYNA_LINE ENRI_STAT='OUI'): the quasi-static contribution of the
            # omitted modes is included.
            "static_correction": True,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "spectrum_3d": {
            # Response spectrum (earthquake, shock): CALC_MODES and
            # COMB_SISM_MODAL; the spectrum is a Mecway gravity with a
            # table (or #ASTER-SPECTRE); see bridge_spectrum.py and
            # docs/Spectrumanalyse.md.
            "template":       "AsterTemplate_Spectre.comm",
            "solver_command": "COMB_SISM_MODAL",
            # Maxima (unsigned) to Mecway, as one step.
            "fields":         ["displacements", "accelerations", "stresses",
                               "vonmises", "reactions"],
            # Number of modes if the Mecway model has no maxmode.
            "modal_modes":    20,
            "modal_tolerance": 1.0e-6,
            # Table of the gravity: period [s] or frequency [Hz].
            "spectrum_abscissa": "period",
            # Damping ratio of every mode (on top of Mecway's Rayleigh).
            "spectrum_damping": 0.05,
            # Modal combination: CQC, SRSS or ABS.
            "modal_combination": "CQC",
            # Directional combination: SRSS, 100-30-30, 100-40-40 or ABS.
            "direction_combination": "SRSS",
            # Missing-mass correction (MODE_CORR with pseudo-modes).
            "missing_mass":   True,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "buckling_3d": {
            # Linear buckling (Mecway B30): MECA_STATIQUE with the loads,
            # geometric stiffness (RIGI_GEOM) and CALC_MODES
            # TYPE_RESU='MODE_FLAMB'; see bridge_to_aster._build_modal.
            "template":       "AsterTemplate_CalcModes.comm",
            "solver_command": "CALC_MODES",
            "type_resu":      "MODE_FLAMB",
            # Buckling mode shapes only (DEPL), like Mecway.
            "fields":         ["displacements"],
            # Number of modes if the Mecway model has no maxmode.
            "modal_modes":    4,
            # Always the smallest buckling load factors (OPTION 'PLUS_PETITE'),
            # like Mecway; Code-Aster 17.4 ignores 'CENTRE' around a factor
            # for buckling (bridge_to_aster._calc_modes_block).
            # Normalisation of the buckling modes (NORM_MODE NORME): "RIGI_GENE" =
            # generalised stiffness 1, like Mecway.
            "modal_norm":     "RIGI_GENE",
            # VERI_MODE SEUIL (see modal_3d).
            "modal_tolerance": 1.0e-6,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
            # RESI_RELA of the static step (stress state; see
            # lin_static_3d; bridge_to_aster._static_step_solveur).
            "lin_solver_resi": 1.0e-6,
        },
        "acoustic_modes_3d": {
            # Acoustic cavity modes (Mecway A30, Acoustic Resonance 3D):
            # PHENOMENE='ACOUSTIQUE' and CALC_MODES; see bridge_acoustic.py
            # and docs/Akoestiek.md. Result: the pressure field per mode.
            "template":       "AsterTemplate_Akoestiek.comm",
            "solver_command": "CALC_MODES",
            # bridge_to_aster._build_modal passes this analysis on to
            # bridge_acoustic.build_acoustic_modes.
            "phenomene":      "ACOUSTIQUE",
            # Number of modes if the Mecway model has no maxmode.
            "modal_modes":    10,
            # Search frequency [Hz]: 0 = the lowest modes (without a pressure
            # node the bridge picks a small negative search frequency itself).
            "modal_shift_hz": 0.0,
            # VERI_MODE SEUIL (see modal_3d).
            "modal_tolerance": 1.0e-6,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "acoustic_harm_3d": {
            # Harmonic pressure field (acoustics) on a Mecway A30 model:
            # PHENOMENE='ACOUSTIQUE' and DYNA_VIBRA HARM; source (BRON_ or
            # #ASTER-BRON), absorbing boundaries (ABSORBEREND_ or
            # impedance), microphones (MICROFOON_); see bridge_acoustic.py
            # and docs/Akoestiek.md. 'auto' picks this for A30 with a source.
            "template":       "AsterTemplate_AkoestiekHarm.comm",
            "solver_command": "DYNA_VIBRA",
            # bridge_to_aster._build_dyna_modal passes this analysis on
            # to bridge_acoustic.build_acoustic_harm.
            "phenomene":      "ACOUSTIQUE",
            # Frequencies [Hz]: harm_freq_count steps from start to end
            # (spacing "lin" or "log"), or a list in harm_freq_list
            # (text, e.g. "100, 250, 500"; "0" = use the range).
            "harm_freq_start": 50.0,
            "harm_freq_end":  1000.0,
            "harm_freq_count": 20,
            "harm_freq_spacing": "lin",
            "harm_freq_list": "0",
            # Normal velocity [m/s] of the BRON_ faces, into the fluid.
            "source_velocity": 0.001,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "vibroacoustic_modes_3d": {
            # Vibro-acoustics: structure + air/liquid coupled
            # (Mecway V30 with a fluid part): 3D_FLUIDE, FLUI_STRU,
            # U_P_PHI and CALC_MODES BANDE; see bridge_vibroacoustic.py and
            # docs/Akoestiek.md. 'auto' picks this for V30 with a fluid.
            "template":       "AsterTemplate_VibroAkoestiek.comm",
            "solver_command": "CALC_MODES",
            # bridge_to_aster._build_modal passes this analysis on to
            # bridge_vibroacoustic.build_vibroacoustic_modes.
            "vibroacoustic":  True,
            # Number of modes if the Mecway model has no maxmode.
            "modal_modes":    10,
            # Lower limit [Hz]: the modes above it (U_P_PHI gives spurious modes
            # at 0 Hz; rigid body modes and constant pressure fall below it).
            "vibro_freq_min": 0.1,
            # VERI_MODE SEUIL (see modal_3d).
            "modal_tolerance": 1.0e-6,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "vibroacoustic_harm_3d": {
            # Vibro-acoustics harmonic: structure + air/liquid per
            # frequency (the same model as vibroacoustic_modes_3d) with
            # sources, absorbing boundaries (3D_FLUI_ABSO) and microphones;
            # DYNA_VIBRA HARM PHYS; see bridge_vibroacoustic_harm.py and
            # docs/Akoestiek.md. Choose it yourself ('auto' stays with the modes).
            "template":       "AsterTemplate_VibroAkoestiekHarm.comm",
            "solver_command": "DYNA_VIBRA",
            # bridge_to_aster._build_dyna_modal passes this analysis on
            # to bridge_vibroacoustic_harm.build_vibroacoustic_harm.
            "vibroacoustic":  True,
            "type_calcul":    "HARM",
            # Structure per frequency (like harmonic_3d); the pressure in the
            # fluid is always included.
            "fields":         ["displacements", "accelerations", "stresses",
                               "vonmises"],
            # Frequencies [Hz]: harm_freq_count steps from start to end
            # (spacing "lin" or "log"), or a list in harm_freq_list
            # (text, e.g. "100, 250, 500"; "0" = use the range).
            "harm_freq_start": 20.0,
            "harm_freq_end":  500.0,
            "harm_freq_count": 50,
            "harm_freq_spacing": "lin",
            "harm_freq_list": "0",
            # Normal velocity [m/s] of the BRON_ faces, into the fluid.
            "source_velocity": 0.001,
            # Amplitude [Pa] of the incident wave on INVALLEND_ faces.
            "incident_pressure": 1.0,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
    },
}


# Mecway analysis type (<analysis type="..."> in the .liml) -> analysis in
# CONFIG_BRIDGE["analyses"], for active_analysis = "auto". Seen in the
# test models: S30 (static 3D), L30 (nonlinear static 3D), D31
# (nonlinear dynamic 3D), T30 (thermal steady state), T31 (thermal
# transient; Mecway examples FinConvection, OscillatingHeatFlow) and V30
# (frequency/modal 3D; Mecway examples VibratingCantileverBeam etc.)
# and B30 (linear buckling 3D; examples BucklingBeam, BucklingPlate).
# D30 (linear Dynamic Response 3D, examples DynamicResponse and
# DampedVibratingStrip): with Mode superposition the response on a modal
# basis, without it (Mecway: Newmark on the full model) implicit dynamics.
# Other types (2D, ...) have no analysis in the bridge.
# Key for D30 with Mode superposition (no Mecway type of its own; also the
# text on the start screen).
D30_MODE_SUPERPOSITION = "D30 + mode superposition"
MECWAY_ANALYSIS_TYPES = {
    "S30": "lin_static_3d",
    "L30": "nonlin_static_3d",
    "D30": "dyna_impl_3d",
    D30_MODE_SUPERPOSITION: "dyna_modal_3d",
    "D31": "dyna_impl_3d",
    "T30": "ther_3d",
    "T31": "ther_3d",
    "V30": "modal_3d",
    "B30": "buckling_3d",
    # Acoustic Resonance 3D (mecway.exe: "A30" / "Acoustic Resonance 3D";
    # A20 = 2D is not translated)
    "A30": "acoustic_modes_3d",
}


def resolve_auto_analysis(mecway_type, mode_superposition=False):
    """
    Analysis name for active_analysis = "auto". mode_superposition: D30
    with <analysis modesuperposition="true"> (model_data
    "mode_superposition").

    Returns
    -------
    str or None  None if the Mecway analysis type is not supported
                 or the matching analysis is not in CONFIG_BRIDGE.
    """
    if mecway_type == "D30" and mode_superposition:
        mecway_type = D30_MODE_SUPERPOSITION
    name = MECWAY_ANALYSIS_TYPES.get(mecway_type)
    if name is None or name not in CONFIG_BRIDGE["analyses"]:
        return None
    return name


# Folder of the bridge scripts (and the .comm templates).
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def expand_path(path):
    """Expand environment variables (%LOCALAPPDATA%, $HOME) and ~ in a path.
    An unknown variable is left as is (os.path.expandvars). Empty or None:
    ""."""
    if not path:
        return ""
    return os.path.expanduser(os.path.expandvars(u"{0}".format(path).strip()))


def default_work_dir():
    """Default working directory for work_dir "": WorkDir next to the folder
    Scripts (in the repo: <repo>/WorkDir, gitignored)."""
    return os.path.join(os.path.dirname(SCRIPTS_DIR), "WorkDir")


def work_dir_path():
    """
    Working directory of the bridge: CONFIG_BRIDGE["work_dir"] with expanded
    environment variables, or default_work_dir() if that setting is empty.
    Always read the working directory with this, never directly from
    CONFIG_BRIDGE.
    """
    return expand_path(CONFIG_BRIDGE.get("work_dir")) or default_work_dir()


def exe_aster_path():
    """Path to run_aster.bat: CONFIG_BRIDGE["exe_aster"] with expanded
    environment variables (default %LOCALAPPDATA%\\code_aster\\...)."""
    return expand_path(CONFIG_BRIDGE.get("exe_aster"))


def template_path(template):
    """
    Full path of a .comm template from CONFIG_BRIDGE["analyses"][..]
    ["template"]: a file name (or relative path) belongs in SCRIPTS_DIR;
    an absolute path is kept. If an absolute path does not exist (e.g. a
    setting from another PC or an old repo folder) but a template with the
    same name is in SCRIPTS_DIR, that one is used.
    """
    if not template:
        return template
    if not os.path.isabs(template):
        return os.path.join(SCRIPTS_DIR, template)
    if not os.path.isfile(template):
        local = os.path.join(SCRIPTS_DIR, os.path.basename(template))
        if os.path.isfile(local):
            return local
    return template


def get_active_analysis():
    """Returns the CONFIG_BRIDGE dict of the active analysis."""
    name = CONFIG_BRIDGE["active_analysis"]
    if name == "auto":
        raise KeyError(tr(
            "CONFIG_BRIDGE['active_analysis'] = 'auto' is nog niet "
            "omgezet naar een analyse (gebeurt in main() na het lezen van "
            "de .liml).",
            "CONFIG_BRIDGE['active_analysis'] = 'auto' has not been "
            "resolved to an analysis yet (done in main() after reading "
            "the .liml)."))
    if name not in CONFIG_BRIDGE["analyses"]:
        raise KeyError(tr(
            "CONFIG_BRIDGE['active_analysis'] = '{0}' staat niet in "
            "CONFIG_BRIDGE['analyses']. Beschikbaar: {1}",
            "CONFIG_BRIDGE['active_analysis'] = '{0}' is not in "
            "CONFIG_BRIDGE['analyses']. Available: {1}").format(
                name, list(CONFIG_BRIDGE["analyses"].keys()))
        )
    return CONFIG_BRIDGE["analyses"][name]


def error_estimator_requested(options=None):
    """
    True if the active analysis has the error estimator on
    ("error_estimator") and is MECA_STATIQUE: only there does the bridge
    build CALC_ERREUR (bridge_to_aster._error_estimator_block; other
    analyses: WARNING in generate_AsterSolver_files). Used by bridge_mesh for
    the free faces. options: the #ASTER-OPTIE values of the model
    (model_data["aster_custom"]["options"]); an "error_estimator" in it
    wins, with the same yes/no words as bridge_custom.apply_options.
    No valid active analysis: False.
    """
    try:
        analysis = get_active_analysis()
    except KeyError:
        return False
    if (analysis.get("solver_command") != "MECA_STATIQUE" or
            "error_estimator" not in analysis):
        return False
    value = parse_yes_no((options or {}).get("error_estimator"))
    if value is not None:
        return value
    # no value or an invalid value (WARNING in bridge_custom.apply_options)
    return bool(analysis["error_estimator"])


# Yes/no words for an #ASTER-OPTIE with a yes/no setting (NL, EN,
# FR; lower case).
YES_WORDS = ("1", "true", "yes", "on", "ja", "aan", "waar", "oui", "vrai")
NO_WORDS = ("0", "false", "no", "off", "nee", "uit", "onwaar", "non", "faux")


def parse_yes_no(raw):
    """
    True or False for a yes/no word (YES_WORDS / NO_WORDS; case,
    spaces and quotes do not matter), else None (also for None).
    Shared by bridge_custom.apply_options (which gives a WARNING for None
    and keeps the default value), bridge_adapt and error_estimator_requested.
    """
    if raw is None:
        return None
    low = u"{0}".format(raw).strip().strip("'\"").strip().lower()
    if low in YES_WORDS:
        return True
    if low in NO_WORDS:
        return False
    return None


# ==========================================
# LANGUAGE
# ==========================================
def tr(nl, en):
    """
    Text in the language of CONFIG_BRIDGE["language"] ("en" = English, the
    default; "nl" = Dutch). Both texts are given at the call, with the same
    placeholders and the same "INFO|WARNING|ERROR|SUCCESS:" prefix
    (bridge_run_aster and the convergence window recognise it):
        log(tr("WARNING: Groep '{0}' is leeg.",
               "WARNING: Group '{0}' is empty.").format(name))
    The language is read on every call; fixed texts at module level
    are therefore stored as a pair (nl, en) and translated on use: tr(*pair).
    """
    return en if CONFIG_BRIDGE.get("language", "en") == "en" else nl


def choose_configuration(names, suppressed):
    """
    Configuration of a model to be solved, shared by
    bridge_from_liml._pick_configuration (which loads count) and
    bridge_results_liml.pick_configuration (in which solution the results
    go), so that both always pick the same one. The Mecway API cannot read
    the active configuration (only mw.set_active_configuration),
    hence the setting CONFIG_BRIDGE["configuration"].

    names      : names of the <configuration name=".."> in order
    suppressed : names that appear somewhere in a
                 <suppressed configuration="..">
    Returns (name or None, how, missing):
      how = "geen" (model without configurations), "gekozen" (the setting),
            "enige" (the model has one), "vrij" (the only one without
            suppressed items) or "eerste" (none or several without
            suppressed items: the first; ambiguous);
      missing = the name from the setting if it is not in the model
            (then "auto" applies), else None.
    """
    if not names:
        return None, "geen", None
    wanted = (CONFIG_BRIDGE.get("configuration") or "auto").strip()
    missing = None
    if wanted != "auto":
        if wanted in names:
            return wanted, "gekozen", None
        missing = wanted
    if len(names) == 1:
        return names[0], "enige", missing
    free = [n for n in names if n not in suppressed]
    if len(free) == 1:
        return free[0], "vrij", missing
    return names[0], "eerste", missing


def configuration_warning(names, configuration, how, missing):
    """WARNING text (without "WARNING: ") for choose_configuration, or ""
    if the choice is unambiguous."""
    parts = []
    if missing:
        parts.append(tr(
            u"Configuratie '{0}' (instelling Configuratie) staat niet in het "
            u"model ({1}); de bridge kiest zelf.",
            u"Configuration '{0}' (setting Configuration) is not in the "
            u"model ({1}); the bridge chooses itself.").format(
                missing, u", ".join(names)))
    if how == "eerste":
        parts.append(tr(
            u"Model met configuraties ({0}): niet eenduidig welke bedoeld "
            u"is; de bridge rekent '{1}' (items die daarin onderdrukt zijn, "
            u"tellen niet mee) en zet de resultaten in de solution daarvan. "
            u"Kies de configuratie op het startscherm (Algemeen, "
            u"Configuratie).",
            u"Model with configurations ({0}): not clear which one is "
            u"meant; the bridge computes '{1}' (items suppressed in it are "
            u"left out) and writes the results into its solution. Choose the "
            u"configuration on the start screen (General, "
            u"Configuration).").format(u", ".join(names), configuration))
    return u" ".join(parts)


# ==========================================
# LOGGING
# ==========================================
# Log file of the current simulation (set_run_log); outside a run
# (start screen, offline tests) bridge_log.txt.
_RUN_LOG = {"name": "bridge_log.txt", "id": None, "model": "model"}

# Suffix of the log file of a run: <model>_<run_id>_bridge_log.txt
LOG_SUFFIX = "_bridge_log.txt"


def model_stem(liml_path):
    """
    Name of the Mecway file without folder and extension, usable in
    file names: characters outside A-Z, a-z, 0-9, '-' and '_' become '_'
    (safe in .export lines and in the .comm; a space in the working
    directory worked in a test, in the name NOT verified), without
    double or trailing '_'. "Mijn Model (v2).liml" -> "Mijn_Model_v2".
    Empty or None: "model".
    """
    stem = os.path.splitext(os.path.basename(liml_path or ""))[0]
    stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem or "model"


def set_run_log(run_id, model=None):
    """
    Start the file names of a simulation: run_id (time stamp) and model
    (name of the Mecway file, via model_stem). The log file becomes
    <model>_<run_id>_bridge_log.txt, like the other files of the run
    (run_name). run_id None: back to bridge_log.txt. Returns the
    file name of the log.
    """
    _RUN_LOG["id"] = run_id
    stem = model_stem(model)
    # Windows paths up to 259 characters (MAX_PATH): seen in a test with a
    # long working directory, where the result file (..._results.xml.tmp)
    # could not be written ([Errno 2]). Too long: shorten the model name.
    room = (259 - len(os.path.join(work_dir_path(), "")) -
            len("_{0}{1}.tmp".format(run_id or "", _LONGEST_SUFFIX)))
    short = stem[:max(8, room)] if len(stem) > room else stem
    _RUN_LOG["model"] = short
    # Still too long with the shortened name: path_too_long() (main stops).
    _RUN_LOG["too_long"] = run_id is not None and room < 8
    _RUN_LOG["name"] = ("bridge_log.txt" if run_id is None
                        else run_name(LOG_SUFFIX))
    if short != stem:
        log(tr("WARNING: Werkmap + modelnaam te lang voor Windows-paden "
               "(max. 259 tekens); bestandsnamen gebruiken '{0}' i.p.v. "
               "'{1}'. Kies een kortere werkmap.",
               "WARNING: Work folder + model name too long for Windows "
               "paths (max. 259 characters); file names use '{0}' instead "
               "of '{1}'. Choose a shorter work folder.").format(short, stem))
    return _RUN_LOG["name"]


# Longest suffix of a run file (bridge_to_aster.results_file,
# bridge_run_aster._monitor_log): determines the room for the model name.
_LONGEST_SUFFIX = "_monitor_log.txt"


def log_file_name():
    """Name of the current log file in the working directory."""
    return _RUN_LOG["name"]


def run_name(suffix):
    """
    File name (without folder) of an output file of the current run:
    <model>_<run_id><suffix>, e.g. for ProfielBuigen.liml run_name(".mess")
    -> ProfielBuigen_20261006_101500.mess. This way every file in the
    working directory visibly belongs to a model and a run. Outside a run
    (offline tests, set_run_log(None)): study<suffix>.
    """
    run_id = _RUN_LOG["id"]
    if run_id is None:
        return "study" + suffix
    return "{0}_{1}{2}".format(_RUN_LOG["model"], run_id, suffix)


# Generic names in messages and hints (e.g. "zie study.mess") ->
# the files of the current run (run_names).
_GENERIC_NAMES = (("study.mess", ".mess"), ("study.comm", ".comm"),
                  ("study_console.txt", "_console.txt"))


def path_too_long():
    """True if working directory + file name of the run would become longer
    than 259 characters even with a shortened model name (set_run_log)."""
    return bool(_RUN_LOG.get("too_long"))


def run_names(text):
    """Replace study.mess, study.comm and study_console.txt in a message
    by the names of the current run (unchanged outside a run). Only
    standalone names: a path like C:\\Werk\\study.comm (e.g. an old file
    being cleaned up) is kept."""
    if _RUN_LOG["id"] is None:
        return text
    for generic, suffix in _GENERIC_NAMES:
        text = re.sub(r"(?<![\\/\w.])" + re.escape(generic),
                      run_name(suffix).replace("\\", "\\\\"), text)
    return text


def log(text):
    """Write a time-stamped log line to the log file of the
    run. If the working directory is missing (e.g. a fresh installation),
    it is created; if writing fails, the message is lost instead of
    making the action fail."""
    work_dir = work_dir_path()
    log_path  = os.path.join(work_dir, _RUN_LOG["name"])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if not os.path.isdir(work_dir):
            os.makedirs(work_dir)
        # io.open with UTF-8: messages from study.mess contain French
        # accents (e.g. "numéro"), which plain open() cannot always
        # handle.
        with io.open(log_path, "a", encoding="utf-8") as f:
            f.write(u"[{0}] {1}\n".format(timestamp, run_names(text)))
    except (IOError, OSError):
        pass


# ==========================================
# UNIT CONVERSION
#
# Code-Aster works without units; the bridge supplies all values in
# SI units:
#   length           m      area             m²      inertia     m⁴
#   force            N      pressure / E     Pa      spring c.   N/m
#   angle            rad
#
# Mecway exports values with unit labels (e.g. "210 GPa",
# "10000 mm⁴", "4231 N/m"). Before the regex matching, Unicode
# superscripts (², ³, ⁴, ¹, ⁰) become ASCII digits, '°' becomes 'deg' and
# 'µ' becomes 'u'.
#
# Supported quantity types and conversions (unit case-insensitive,
# except the prefix m/M: mN, mPa and mN/m are milli, MN, MPa and MN/m mega):
#   'length'           mm→×1e-3,  cm→×1e-2
#   'force'            kN→×1e3,   MN→×1e6,   mN→×1e-3
#   'pressure'         kPa→×1e3,  MPa→×1e6,  GPa→×1e9,  mPa→×1e-3
#   'angle'            deg / °→×(π/180)
#   'area'             mm2→×1e-6, cm2→×1e-4,  in2→×6.4516e-4
#   'inertia'          mm4→×1e-12, cm4→×1e-8, in4→×4.16231e-7
#   'spring_stiffness' N/mm→×1e3,  kN/m→×1e3,  kN/mm→×1e6,  MN/m→×1e6,
#                      mN/m→×1e-3
#   'density'          t/mm3→×1e12, g/mm3→×1e6, g/cm3→×1e3
#   'inversetemp'      1/°F→×1.8  (1/K and 1/°C: no conversion)
#   'acceleration'     mm/s2→×1e-3
#   'time'             ms→×1e-3, us→×1e-6, min→×60, h→×3600
#   'temperature'      °C→+273.15, °F→(F-32)·5/9+273.15  (target unit K)
#   'conductivity'     W/m/K;  W/mm/K, kW/m/K→×1e3
#   'specific_heat'    J/kg/K; kJ/kg/K, J/g/K→×1e3
#   'heat_transfer'    W/m2/K; W/mm2/K→×1e6, kW/m2/K→×1e3  (/°C = /K)
#   'heat_flux'        W/m2;   W/mm2→×1e6, W/cm2→×1e4, kW/m2→×1e3
#   'power_density'    W/m3;   W/mm3→×1e9, W/cm3→×1e6, kW/m3→×1e3
#   'power'            W;      kW→×1e3, mW→×1e-3, MW→×1e6
#   imperial           in, ft, lbf, kip, psi, ksi, lbf.in, lb, slug, ...:
#                      see _OTHER_FACTORS (also N/mm2, bar, um, km)
#   unknown unit       value unchanged + WARNING in the log
#   'line_load', 'stiffness_per_area', 'mass', 'rotational_inertia',
#   'angular_velocity', 'inverse_time', 'inverse_length', 'inverse_angle',
#   'damping'          see _EXTRA_FACTORS
#   'dimensionless'    no conversion
# ==========================================

def _normalize_unit_string(s):
    """
    Replace Unicode characters in units by ASCII for unit recognition.

    Conversions (Unicode code points):
        ² U+00B2 → '2'
        ³ U+00B3 → '3'
        ⁴ U+2074 → '4'
        ¹ U+00B9 → '1'
        ⁰ U+2070 → '0'
        ° U+00B0 → 'deg'
        µ U+00B5 / μ U+03BC → 'u'

    Compatible with IronPython 2.7.9 (unicode strings from XML parsing).
    """
    try:
        # Python 2: basestring covers str and unicode
        if not isinstance(s, basestring):
            s = str(s)
    except NameError:
        # Python 3
        if not isinstance(s, str):
            s = str(s)

    if isinstance(s, bytes):
        s = s.decode('utf-8', 'replace')

    for old, new in [
        (u'\u2074', u'4'),   # ⁴
        (u'\u00b3', u'3'),   # ³
        (u'\u00b2', u'2'),   # ²
        (u'\u00b9', u'1'),   # ¹
        (u'\u2070', u'0'),   # ⁰
        (u'\u00b0', u'deg'), # °
        (u'\u00b5', u'u'),   # µ (micro sign)
        (u'\u03bc', u'u'),   # μ (Greek mu)
    ]:
        s = s.replace(old, new)

    return s


def parse_and_convert(val_str, quantity_type):
    """
    Parses a value string (number + optional unit) and converts to SI.

    Parameters
    ----------
    val_str       : str  Input string, e.g. "210 GPa", "10000 mm⁴", "4231 N/m"
    quantity_type : str  One of: 'length', 'force', 'pressure', 'angle',
                         'area', 'inertia', 'spring_stiffness', 'density',
                         'inversetemp', 'acceleration', 'time',
                         'velocity', 'moment', 'dimensionless'

    Returns
    -------
    float  Value in SI units, or 0.0 on a parse error.
    """
    if not val_str:
        return 0.0

    # Normalise Unicode characters BEFORE the regex
    val_str = _normalize_unit_string(str(val_str).strip())

    # Number (sign, decimal, exponent) followed by a unit string.
    # The unit may contain letters, digits and '/' (e.g. "mm4", "n/m").
    match = re.match(
        r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-zA-Z0-9/]*)",
        val_str
    )
    if not match:
        return 0.0

    val  = float(match.group(1))
    unit = match.group(2).lower()
    # m (milli) and M (mega) coincide after lower(); the original
    # prefix decides.
    milli = match.group(2).startswith('m')
    # Full unit as key: lower case, without spaces, dots,
    # '·' and '*' ("lbf·in" -> "lbfin", "N.m" -> "nm", "kg/m3").
    key = _unit_key(val_str[match.end(1):])

    # Imperial and other units (see _OTHER_FACTORS)
    other = _OTHER_FACTORS.get(quantity_type, {})
    if key in other:
        return val * other[key]

    # --------------------------------------------------
    # LENGTH   (target unit: m)
    # --------------------------------------------------
    if quantity_type == 'length':
        if unit == 'mm':    return val * 1.0e-3
        if unit == 'cm':    return val * 1.0e-2
        if unit == 'km':    return val * 1.0e3

    # --------------------------------------------------
    # FORCE   (target unit: N)
    # --------------------------------------------------
    elif quantity_type == 'force':
        if unit == 'kn':    return val * 1.0e3
        if unit == 'mn':    return val * (1.0e-3 if milli else 1.0e6)

    # --------------------------------------------------
    # PRESSURE / E-MODULUS   (target unit: Pa)
    # --------------------------------------------------
    elif quantity_type == 'pressure':
        if unit == 'kpa':   return val * 1.0e3
        if unit == 'mpa':   return val * (1.0e-3 if milli else 1.0e6)
        if unit == 'gpa':   return val * 1.0e9

    # --------------------------------------------------
    # ANGLE   (target unit: rad)
    # --------------------------------------------------
    elif quantity_type == 'angle':
        if unit == 'deg':
            return val * (math.pi / 180.0)

    # --------------------------------------------------
    # AREA   (target unit: m²)
    # Mecway exports e.g. "100 mm²" → after normalisation "100 mm2"
    # --------------------------------------------------
    elif quantity_type == 'area':
        if unit == 'mm2':   return val * 1.0e-6
        if unit == 'cm2':   return val * 1.0e-4
        if unit == 'in2':   return val * 6.4516e-4

    # --------------------------------------------------
    # MOMENT OF INERTIA   (target unit: m⁴)
    # Mecway exports e.g. "10000 mm⁴" → after normalisation "10000 mm4"
    # --------------------------------------------------
    elif quantity_type == 'inertia':
        if unit == 'mm4':   return val * 1.0e-12
        if unit == 'cm4':   return val * 1.0e-8
        if unit == 'in4':   return val * 4.16231e-7

    # --------------------------------------------------
    # SPRING CONSTANT   (target unit: N/m)
    # Mecway exports e.g. "4231 N/m" or "10 N/mm"
    # --------------------------------------------------
    elif quantity_type == 'spring_stiffness':
        if unit == 'n/mm':  return val * 1.0e3
        if unit == 'kn/m':  return val * 1.0e3
        if unit == 'kn/mm': return val * 1.0e6
        if unit == 'mn/m':  return val * (1.0e-3 if milli else 1.0e6)

    if quantity_type == 'density':
        if unit == 't/mm3':  return val * 1.0e12
        if unit == 'g/mm3':  return val * 1.0e6
        if unit == 'g/cm3':  return val * 1.0e3
        # kg/m³ or no unit -> no conversion needed

    if quantity_type == 'inversetemp':
        if unit == '1/degf':  return val * 1.8
        # 1/K, 1/°C or no unit -> no conversion needed

    if quantity_type == 'acceleration':
        if unit == 'mm/s2':  return val * 1.0e-3
        # m/s2 or no unit -> no conversion needed

    if quantity_type == 'velocity':
        if unit == 'mm/s':  return val * 1.0e-3
        if unit == 'mm/ms': return val
        # m/s or no unit -> no conversion needed

    if quantity_type == 'moment':
        # "2 N.m", "2 N·m", "5 kN.m", "300 N.mm": the unit contains a
        # dot, which the regex above does not capture.
        full = val_str[match.end(1):].strip().lower()
        full = full.replace(u'·', u'.').replace(u'*', u'.')
        full = full.replace(u' ', u'').replace(u'.', u'')
        if full == 'knm':   return val * 1.0e3
        if full == 'nmm':   return val * 1.0e-3
        if full == 'knmm':  return val
        # N.m or no unit -> no conversion needed

    if quantity_type == 'time':
        # SI is seconds.
        if unit == 'ms':  return val * 1.0e-3
        if unit == 'us':  return val * 1.0e-6
        if unit == 'min': return val * 60.0
        if unit == 'h':   return val * 3600.0
        # 's' or no unit -> no conversion needed

    # --------------------------------------------------
    # THERMAL (bridge_thermal.py). Mecway writes among others "500 K",
    # "20 °C" (CoolantChannel.liml), "380 W/m/K", "900 J/kg/K",
    # "37.5 W/m²/K", "1000 W/m²", "1000000 W/m³", "500 W". A dividing
    # '/°C' or '/°F' in a unit is the same as '/K' (resp. 5/9 K).
    # --------------------------------------------------
    if quantity_type == 'temperature':
        # Absolute temperature, target unit K.
        if unit == 'degc':  return val + 273.15
        if unit == 'degf':  return (val - 32.0) * 5.0 / 9.0 + 273.15
        # K or no unit -> no conversion needed

    if quantity_type in ('conductivity', 'specific_heat', 'heat_transfer'):
        per_f = unit.endswith('/degf')
        base = unit.replace('/degc', '/k').replace('/degf', '/k')
        factor = 1.8 if per_f else 1.0
        if quantity_type == 'conductivity':        # W/m/K
            if base == 'w/mm/k':  return val * 1.0e3 * factor
            if base == 'kw/m/k':  return val * 1.0e3 * factor
        elif quantity_type == 'specific_heat':     # J/kg/K
            if base == 'kj/kg/k': return val * 1.0e3 * factor
            if base == 'j/g/k':   return val * 1.0e3 * factor
        else:                                      # W/m2/K
            if base == 'w/mm2/k': return val * 1.0e6 * factor
            if base == 'kw/m2/k': return val * 1.0e3 * factor
        if base in ('', 'w/m/k', 'j/kg/k', 'w/m2/k'):
            return val * factor

    if quantity_type == 'heat_flux':               # W/m2
        if unit == 'w/mm2':   return val * 1.0e6
        if unit == 'w/cm2':   return val * 1.0e4
        if unit == 'kw/m2':   return val * 1.0e3

    if quantity_type == 'power_density':           # W/m3
        if unit == 'w/mm3':   return val * 1.0e9
        if unit == 'w/cm3':   return val * 1.0e6
        if unit == 'kw/m3':   return val * 1.0e3

    if quantity_type == 'power':                   # W
        if unit == 'kw':      return val * 1.0e3
        if unit == 'mw':      return val * (1.0e-3 if milli else 1.0e6)

    converted = _convert_extra(val, unit, val_str[match.end(1):],
                               quantity_type)
    if converted is not None:
        return converted

    # 'dimensionless', SI unit or no unit: value unchanged.
    # An unknown unit too, but with a WARNING: a silent
    # pass-through gave a 4.45x too small force for "-3500 lbf"
    # (Mecway Tutorials/Solution.liml).
    si_units = _SI_UNITS.get(quantity_type)
    if key and si_units is not None and key not in [
            _unit_key(x) for x in si_units]:
        tag = (_RUN_LOG["name"], quantity_type, key)
        if tag not in _WARNED_UNITS:
            _WARNED_UNITS.add(tag)
            log(tr(u"WARNING: Eenheid niet herkend in '{0}' (grootheid "
                   u"'{1}'): waarde ongewijzigd als SI ({2}) gebruikt. "
                   u"Controleer de eenheid of zet het model in SI-eenheden.",
                   u"WARNING: Unit not recognised in '{0}' (quantity "
                   u"'{1}'): value used unchanged as SI ({2}). Check the "
                   u"unit or put the model in SI units.").format(
                       val_str, quantity_type, si_units[0]))
    return val


def _unit_key(unit_text):
    """Unit as comparison key (see parse_and_convert)."""
    full = unit_text.strip().replace(u'\u00b7', u'.').replace(u'*', u'.')
    return full.replace(u' ', u'').replace(u'.', u'').lower()


# Imperial (and some metric) units -> SI. Exact definitions: 1 in = 0.0254 m,
# 1 ft = 0.3048 m, 1 lb = 0.45359237 kg, 1 lbf = 1 lb x 9.80665 m/s2 =
# 4.4482216152605 N, 1 kip = 1000 lbf, psi = lbf/in2, slug = lbf.s2/ft).
# Keys as in _unit_key ("lbf.in" and "in.lbf" -> "lbfin" / "inlbf").
_IN = 0.0254
_FT = 0.3048
_LB = 0.45359237
_LBF = 4.4482216152605
_KIP = 1000.0 * _LBF
_OTHER_FACTORS = {
    'length': {'in': _IN, 'inch': _IN, 'ft': _FT, 'um': 1.0e-6},
    'force': {'lbf': _LBF, 'kip': _KIP, 'kips': _KIP, 'kipf': _KIP},
    'pressure': {'psi': _LBF / _IN ** 2, 'ksi': _KIP / _IN ** 2,
                 'psf': _LBF / _FT ** 2, 'lbf/in2': _LBF / _IN ** 2,
                 'lbf/ft2': _LBF / _FT ** 2, 'kip/in2': _KIP / _IN ** 2,
                 'n/mm2': 1.0e6, 'kn/m2': 1.0e3, 'bar': 1.0e5,
                 'mbar': 1.0e2},
    'area': {'in2': _IN ** 2, 'ft2': _FT ** 2},
    'inertia': {'in4': _IN ** 4, 'ft4': _FT ** 4},
    'spring_stiffness': {'lbf/in': _LBF / _IN, 'kip/in': _KIP / _IN,
                         'lbf/ft': _LBF / _FT},
    'line_load': {'lbf/in': _LBF / _IN, 'kip/in': _KIP / _IN,
                  'lbf/ft': _LBF / _FT, 'kip/ft': _KIP / _FT},
    'stiffness_per_area': {'lbf/in3': _LBF / _IN ** 3,
                           'psi/in': _LBF / _IN ** 3,
                           'kip/in3': _KIP / _IN ** 3},
    'moment': {'lbfin': _LBF * _IN, 'inlbf': _LBF * _IN,
               'lbfft': _LBF * _FT, 'ftlbf': _LBF * _FT,
               'kipin': _KIP * _IN, 'inkip': _KIP * _IN,
               'kipft': _KIP * _FT, 'ftkip': _KIP * _FT},
    'density': {'lb/in3': _LB / _IN ** 3, 'lbm/in3': _LB / _IN ** 3,
                'lb/ft3': _LB / _FT ** 3, 'lbm/ft3': _LB / _FT ** 3,
                'slug/ft3': _LBF / _FT / _FT ** 3,
                'lbfs2/in4': _LBF / _IN ** 4},
    'mass': {'lb': _LB, 'lbm': _LB, 'slug': _LBF / _FT,
             'lbfs2/in': _LBF / _IN},
    'acceleration': {'in/s2': _IN, 'ft/s2': _FT},
    'velocity': {'in/s': _IN, 'ft/s': _FT},
    'rotational_inertia': {'lbin2': _LB * _IN ** 2, 'lbmin2': _LB * _IN ** 2,
                           'lbft2': _LB * _FT ** 2, 'lbmft2': _LB * _FT ** 2,
                           'lbfins2': _LBF * _IN, 'slugft2': _LBF * _FT},
    'damping': {'lbfs/in': _LBF / _IN, 'lbfs/ft': _LBF / _FT},
}

# Units in which the value is already SI (compared via _unit_key; the first
# is in the WARNING). Quantities without an entry (e.g. 'dimensionless')
# give no WARNING. Mecway writes '/degC' and '/K' interchangeably.
_SI_UNITS = {
    'length': ('m',), 'force': ('N',), 'pressure': ('Pa', 'N/m2'),
    'angle': ('rad',), 'area': ('m2',), 'inertia': ('m4',),
    'spring_stiffness': ('N/m',), 'density': ('kg/m3',),
    'inversetemp': ('1/K', '1/degC'), 'acceleration': ('m/s2',),
    'velocity': ('m/s',), 'moment': ('N.m',), 'time': ('s', 'sec'),
    'temperature': ('K',),
    'conductivity': ('W/m/K', 'W/m/degC'),
    'specific_heat': ('J/kg/K', 'J/kg/degC'),
    'heat_transfer': ('W/m2/K', 'W/m2/degC'),
    'heat_flux': ('W/m2',), 'power_density': ('W/m3',), 'power': ('W',),
    'line_load': ('N/m',), 'stiffness_per_area': ('Pa/m', 'N/m3'),
    'mass': ('kg',), 'rotational_inertia': ('kg.m2',),
    'angular_velocity': ('rad/s',), 'inverse_time': ('1/s', 'rad/s'),
    'inverse_length': ('1/m',), 'inverse_angle': ('1/rad',),
    'damping': ('N.s/m',),
}

# Already reported (log file, quantity, unit): one WARNING per run.
_WARNED_UNITS = set()


# Factors to SI for the quantities of the mechanical loads
# (traction, line pressure, elastic support, mass, ...). Key: unit
# in lower case without spaces and dots ("N.s/m" -> "ns/m").
_EXTRA_FACTORS = {
    # force per length (line pressure) -> N/m
    'line_load': {'n/m': 1.0, 'n/mm': 1.0e3, 'kn/m': 1.0e3, 'kn/mm': 1.0e6,
                  'mn/m': 1.0e6},
    # stiffness per area (elastic support, compression only) -> Pa/m
    'stiffness_per_area': {'pa/m': 1.0, 'kpa/m': 1.0e3, 'mpa/m': 1.0e6,
                           'gpa/m': 1.0e9, 'n/m3': 1.0, 'n/mm3': 1.0e9,
                           'mpa/mm': 1.0e9, 'gpa/mm': 1.0e12},
    # mass -> kg
    'mass': {'kg': 1.0, 'g': 1.0e-3, 't': 1.0e3, 'tonne': 1.0e3},
    # mass moment of inertia -> kg.m2 ("kg.m²" from Mecway)
    'rotational_inertia': {'kgm2': 1.0, 'kgmm2': 1.0e-6, 'tmm2': 1.0e-3,
                           'gmm2': 1.0e-9, 'kgcm2': 1.0e-4},
    # angular velocity -> rad/s ("r/min" from Mecway)
    'angular_velocity': {'rad/s': 1.0, 'r/min': 2.0 * math.pi / 60.0,
                         'rpm': 2.0 * math.pi / 60.0,
                         'deg/s': math.pi / 180.0, 'r/s': 2.0 * math.pi},
    # 1/time (Rayleigh alpha, Mecway shows "rad/s") -> 1/s
    'inverse_time': {'rad/s': 1.0, '1/s': 1.0, '1/ms': 1.0e3},
    # 1/length (coefficient of a constraint equation on ux/uy/uz) -> 1/m
    'inverse_length': {'1/m': 1.0, '1/mm': 1.0e3, '1/cm': 1.0e2},
    # 1/angle (coefficient on rx/ry/rz) -> 1/rad
    'inverse_angle': {'1/rad': 1.0, '1/deg': 180.0 / math.pi},
    # damping (damper) -> N.s/m
    'damping': {'ns/m': 1.0, 'ns/mm': 1.0e3, 'kns/m': 1.0e3},
}


def _convert_extra(val, unit, unit_text, quantity_type):
    """
    SI value for the quantities in _EXTRA_FACTORS and 'temperature', or
    None (unknown quantity or unit: parse_and_convert then returns the
    value unchanged).
    'temperature' -> K: "350 K", "20 degC" (after _normalize_unit_string),
    "68 degF".
    """
    if quantity_type == 'temperature':
        if unit in ('degc', 'c'):
            return val + 273.15
        if unit in ('degf', 'f'):
            return (val - 32.0) / 1.8 + 273.15
        return None
    table = _EXTRA_FACTORS.get(quantity_type)
    if table is None:
        return None
    full = unit_text.strip().replace(u'·', u'.').replace(u'*', u'.')
    full = full.replace(u' ', u'').replace(u'.', u'')
    key = full.lower()
    # m (milli) and M (mega) coincide after lower(): MPa/m, MN/m and mN/m
    if key in ('mpa/m', 'mn/m') and full[:1] == 'm':
        return val * {'mpa/m': 1.0e-3, 'mn/m': 1.0e-3}[key]
    if key in table:
        return val * table[key]
    return None
