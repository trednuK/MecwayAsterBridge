# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# MecwayAsterBridgeMain.py
# Main script of the Mecway-to-Code-Aster bridge.
# Run from the Mecway scripting engine (IronPython 2.7.9).
#
# The objects 'mw' (Mecway API) and 'solution' (active solution) are
# implicitly available in the Mecway scripting context; they are NOT
# defined here but are passed on to functions in
# bridge_gui.py, bridge_run_aster.py and bridge_from_aster.py, which run
# outside the scripting context.
#
# Module architecture:
#   bridge_utils         : config, logging, unit conversion     (shared base)
#   bridge_gui           : run_settings_dialog()                (start screen)
#                          claim_instance()                     (one bridge
#                          per Mecway at a time)
#   bridge_bcs           : BC classes + SUPPORTED_BCS registry
#   bridge_from_liml     : extract_aster_data_from_liml()       (Mecway -> dict)
#   bridge_mesh          : write_mesh()                         (.liml -> mesh)
#   bridge_to_aster      : generate_AsterSolver_files()         (dict -> .comm/.export)
#   bridge_run_aster     : run_AsterSolver()                    (start solver)
#   bridge_from_aster    : AsterToMecway_results()              (.resu -> Mecway)
#   bridge_thermal       : parse_thermal() / build_thermal()    (T30/T31 ->
#                          THER_LINEAIRE / THER_NON_LINE)
#   (modal V30 / buckling B30: bridge_to_aster._build_modal -> CALC_MODES;
#    the modes go into the .liml as <mode>, see _report_modes)
#   bridge_welding       : apply() / report_lines()             (#ASTER-LASBRON:
#                          moving welding heat source in ther_3d)
#   bridge_thermomech    : build_blocks() / report_lines()      (T31 with
#                          Thermal stress: then STAT_NON_LINE, residual stress)
#   bridge_metallurgy    : apply() / report_lines()             (#ASTER-
#                          METALLURGIE: phases and hardness with CALC_META,
#                          optional metallurgical law in the chain)
#   bridge_dyna_modal    : build_dyna_modal()                   (D30 with mode
#                          superposition -> DYNA_VIBRA GENE)
#   bridge_acoustic      : parse_acoustic() / build_acoustic_modes()
#                          (A30/A20 cavity modes -> ACOUSTIQUE + CALC_MODES) /
#                          build_acoustic_harm() (A30 with a source ->
#                          DYNA_VIBRA HARM, pressure field per frequency)
#   bridge_vibroacoustic : parse_vibro() / build_vibroacoustic_modes()
#                          (V30 with a fluid -> 3D_FLUIDE + FLUI_STRU,
#                          coupled modes)
#   bridge_vibroacoustic_harm : build_vibroacoustic_harm() / report_harmonic()
#                          (the same model per frequency -> DYNA_VIBRA
#                          HARM PHYS, 3D_FLUI_ABSO, sources, microphones)
#   bridge_spectrum     : build_spectrum()                     (response spectrum
#                          -> CALC_MODES + COMB_SISM_MODAL)
#   bridge_harmonic      : build_harmonic()                     (harmonic
#                          response -> DYNA_VIBRA HARM, per frequency)
#   bridge_fracture      : front_cells() / fracture_block() / report()
#                          (SCHEUR_ selections in linear static ->
#                          DEFI_FOND_FISS + CALC_G + POST_K1_K2_K3, K and G
#                          in <model>_<run_id>_scheur.csv and the status box)
#   bridge_xfem          : mesh_cells() / model_block() / result_block() /
#                          k_block() / report() (#ASTER-XFEM or XFEM_
#                          face selection: crack without a mesh ->
#                          DEFI_FISS_XFEM + CALC_G_XFEM + POST_K1_K2_K3;
#                          with med_export also <model>_<run_id>_xfem.rmed)
#   bridge_fatigue       : fatigue_block() / report()          (#ASTER-WOHLER:
#                          fatigue, damage and life per node via
#                          aster_fatigue.py in the job; fields damage/life)
#   AsterTemplate_*.comm : one .comm template per analysis type (file name
#                          per analysis in CONFIG_BRIDGE["analyses"], looked
#                          up in the scripts folder: template_path)
#
# Work order:
#   0. Main window (bridge_gui): settings (saved in bridge_utils.py on
#      Start), documentation, convergence screen and results
#      (Results...). After a run the window comes back, with the outcome
#      in the status box; Close stops the bridge.
#   1. Optional: solve the model in Mecway (check: are there errors?)
#   1b. Does the Mecway solution match the model? Otherwise stop (the
#      results can only be loaded on the nodes of the solution)
#   2. Save the model (.liml)
#   3. Read mesh, BCs, materials and selections from the .liml file
#      (stops if there are no materials). With active_analysis = "auto"
#      the analysis follows the Mecway analysis type (for this run only).
#   3b. Write the mesh in ASTER format (bridge_mesh)
#   4. Generate <model>_<run_id>.comm and .export
#   5. Start Code-Aster; wait until it has finished (status window with
#      Stop, or confirmation by the user: setting wait_for_aster)
#   6. Load the results back into Mecway
#   7. Optional (adapt_refine, linear static): refine the elements with
#      the largest estimated error in Mecway and start again at 2
#      (bridge_adapt, _adapt_step)
#
# Configuration (paths, CPU counts, active analysis) is in
# bridge_utils.py (CONFIG_BRIDGE) and can be changed on the start screen.
#
# Files in the work folder: everything of a run is named <model>_<run_id>...
# with <model> the name of the Mecway file and run_id the timestamp
# (bridge_utils.run_name): _bridge_log.txt, .mail, .comm, .export, .mess,
# _console.txt, _results.xml (the results, which can be reloaded later with
# the Results... button in the main window) and, depending on the
# settings, .rmed, .resu and _vergelijking.csv.

import os
import shutil
import time
from datetime import datetime

# Module imports follow the data flow: utils -> gui -> from_liml -> mesh ->
# to_aster -> run_aster -> from_aster. All modules import bridge_utils,
# which itself imports no bridge_* modules. In addition,
# bridge_from_liml and bridge_mesh import bridge_bcs, and bridge_gui imports
# RESULT_FIELD_SPECS from bridge_from_aster; none of these imports back.
from bridge_utils       import (CONFIG_BRIDGE, log, resolve_auto_analysis,
                                set_run_log, log_file_name, tr, run_name,
                                run_names, path_too_long, work_dir_path,
                                exe_aster_path, set_model_path,
                                BRIDGE_VERSION, log_size, log_errors)
from bridge_gui         import (run_settings_dialog, results_dialog,
                                claim_instance, release_instance,
                                instance_busy_text)
from bridge_from_liml   import extract_aster_data_from_liml
from bridge_mesh        import write_mesh
from bridge_to_aster    import generate_AsterSolver_files, results_file
from bridge_run_aster   import (run_AsterSolver, aster_mess_errors,
                                penetration_report)
from bridge_convergence import stopped_text
from bridge_from_aster  import (AsterToMecway_results, check_solution_mesh,
                                _compare_with_mecway,
                                _compare_modes_with_mecway)
from bridge_results_liml import (splice_results, read_step,
                                 pick_configuration, strip_results,
                                 list_results, run_files, check_results_fit,
                                 read_modes, read_mode_summary,
                                 read_cyclic_summary, read_tagged,
                                 read_error_summary, read_crit_stab,
                                 crit_stab_estimate, read_imperfection,
                                 has_results)
from bridge_failure     import report_failures
from bridge_monitor     import monitor_text
from bridge_run_aster   import CONSOLE_SUFFIX
import bridge_version
import bridge_acoustic
import bridge_fracture
import bridge_xfem
import bridge_fatigue
import bridge_vibroacoustic
from bridge_welding     import report_lines as report_welding
import bridge_metallurgy
import bridge_harmonic
import bridge_vibroacoustic_harm
import bridge_adapt


# ==========================================
# FACE NODES FROM MECWAY
# ==========================================
def _face_nodes(eid, faceid):
    """Nodes of face faceid of element eid, as Mecway knows them
    (mw.face_nodes; FaceId numbers are those of <face> in the .liml)."""
    return list(mw.face_nodes(FaceId(eid, faceid)))


# ==========================================
# MAIN FUNCTION
# ==========================================
def _save_model():
    """
    mw.save() with a clear message. Mecway saves to the path the model was
    opened from; if that folder no longer exists (moved, deleted, drive
    removed), it only raises a bare IOError ("Could not find a part of the
    path", seen in Mecway 34). Returns None if saved, else the message for
    the status box (also logged as ERROR).
    """
    folder = os.path.dirname(mw.file_name() or "")
    if folder and not os.path.isdir(folder):
        log(tr("ERROR: De map van het open model bestaat niet meer: {0}",
               "ERROR: The folder of the open model no longer exists: "
               "{0}").format(folder))
        return tr("De map van het open model bestaat niet meer:\n{0}\n\nSla "
                  "het model op met File > Save As... in een bestaande map "
                  "en start opnieuw.",
                  "The folder of the open model no longer exists:\n{0}\n\n"
                  "Save the model with File > Save As... in an existing "
                  "folder and start again.").format(folder)
    try:
        mw.save()
    except Exception as e:
        log(tr("ERROR: Opslaan van het model mislukt: {0}",
               "ERROR: Saving the model failed: {0}").format(e))
        return tr("Opslaan van het model mislukt:\n{0}\n\nSla het model op "
                  "met File > Save As... en start opnieuw.",
                  "Saving the model failed:\n{0}\n\nSave the model with "
                  "File > Save As... and start again.").format(e)
    return None


def _run(settings):
    """
    One bridge run with the settings of the main window: save the model,
    translate it, start Code-Aster and load the results. Messages go
    through _notify (status box of the main window). Returns True if the
    results are in Mecway.
    """
    # Unique run ID (date/time) for all files of this simulation
    # (see the header of this file). First, so that the status box also
    # shows the name of this run on an error below.
    # File names: <Mecway file>_<run_id>... (mw.file_name(): the open
    # model; not saved yet: "model").
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Open model first: work_dir_beside_model puts the work folder next to
    # it (work_dir_path), also for the length check in set_run_log.
    set_model_path(mw.file_name())
    set_run_log(run_id, mw.file_name())

    # Create the work folder if it does not exist yet
    if not os.path.exists(work_dir_path()):
        os.makedirs(work_dir_path())
    if path_too_long():
        _notify(tr("De werkmap is te lang voor Windows-paden (max. 259 "
                   "tekens, ook met een ingekorte modelnaam): {0}\nKies een "
                   "kortere werkmap. Code-Aster wordt niet gestart.",
                   "The work folder is too long for Windows paths (max. 259 "
                   "characters, even with a shortened model name): {0}\n"
                   "Choose a shorter work folder. Code-Aster is not "
                   "started.").format(work_dir_path()))
        return False
    _remove_stale_outputs()

    log("START: MecwayAsterBridge {0} (startscherm via {1}), actieve "
        "analyse '{2}'.".format(BRIDGE_VERSION, settings["gui"],
                                CONFIG_BRIDGE["active_analysis"]))
    log("INFO: Work folder {0}; Code-Aster {1}.".format(work_dir_path(),
                                                    exe_aster_path()))
    # Version check (bridge_version.py): only a WARNING, the run goes
    # on. The messages appear in the status box at the end (finally).
    # Code-Aster here from the launcher path, after the run from the .mess;
    # Mecway after saving from the .liml (step 2).
    version_notes = {}
    version_notes["aster"] = bridge_version.check_aster(
        bridge_version.aster_version_from_launcher(exe_aster_path()),
        "launcher path")
    for analysis, key, _kind, old, new in settings["changes"]:
        log("SETTING: {0}{1}: {2} -> {3}".format(
            "" if analysis is None else "analyses['{0}'].".format(analysis),
            key, old, new))
    for err in settings["save_errors"]:
        log(tr("WARNING: Opslaan instelling mislukt: {0}",
               "WARNING: Saving setting failed: {0}").format(err))

    configured_analysis = CONFIG_BRIDGE["active_analysis"]
    try:
        # --- Step 1: Solve in Mecway (optional check for errors) ---
        # The Mecway API documents no return value for mw.solve(); an
        # error is therefore only detected if mw.solve() raises an exception.
        if CONFIG_BRIDGE.get("mecway_solve_first", False):
            log("INFO: Mecway solve started as a check.")
            try:
                mw.solve()
            except Exception as e:
                log(tr("ERROR: Mecway-solve mislukt: {0}",
                       "ERROR: Mecway solve failed: {0}").format(str(e)))
                _notify(tr("Mecway-solve mislukt:\n{0}\n\nCode-Aster "
                              "wordt niet gestart.",
                              "Mecway solve failed:\n{0}\n\nCode-Aster is "
                              "not started.").format(str(e)))
                return False
            log("INFO: Mecway solve completed.")

        # --- Step 1b: Does the solution match the model? ---
        # solution.set_variable() can only store values on the nodes of
        # the last Mecway solve. After a model change (seen in Mecway:
        # mesh refined from 12 to 45 nodes) the results on 33 nodes were
        # silently dropped. Hence the check before the Code-Aster run.
        # Only needed for the table route (set_variable); the liml route
        # writes the solution itself.
        route = CONFIG_BRIDGE.get("result_route", "liml")
        sol_ok, sol_reason = (check_solution_mesh(mw, solution)
                              if route == "tabel" else (True, ""))
        if not sol_ok:
            log("ERROR: {0}".format(sol_reason))
            _notify(tr("{0}\n\nLos het model eerst op in Mecway, of zet "
                          "in het startscherm 'Eerst Mecway-solve ter "
                          "controle' aan. Code-Aster wordt niet gestart.",
                          "{0}\n\nSolve the model in Mecway first, or turn "
                          "on 'Mecway solve first as a check' in the start "
                          "screen. Code-Aster is not started.").format(
                              sol_reason))
            return False

        # --- Step 2: Save ---
        save_error = _save_model()
        if save_error:
            _notify(save_error + tr(" Code-Aster wordt niet gestart.",
                                    " Code-Aster is not started."))
            return False
        active_liml = mw.file_name()  # Path to the active .liml file
        version_notes["mecway"] = bridge_version.check_mecway(active_liml)[1]

        # --- Step 3: Read model_data from the .liml file ---
        mark = log_size()
        model_data = extract_aster_data_from_liml(active_liml)
        _LAST["model_data"] = model_data      # adaptive refinement
        if model_data is None:
            _notify(_prep_failed(tr("Het model kon niet gelezen worden.",
                                    "The model could not be read."), mark))
            return False

        # --- Step 3a: "auto" -> analysis according to the Mecway type ---
        # Only in memory and only for this run (the finally below
        # resets "auto"); get_active_analysis() in
        # bridge_to_aster/bridge_from_aster thus sees the chosen analysis.
        if CONFIG_BRIDGE["active_analysis"] == "auto":
            mecway_type = model_data.get("analysis_type", "")
            resolved = resolve_auto_analysis(
                mecway_type, model_data.get("mode_superposition"))
            # A30 with a source (BRON_, #ASTER-BRON): harmonic pressure field
            resolved = bridge_acoustic.resolve_auto(resolved, model_data)
            # V30 with a fluid part: vibro-acoustics
            resolved = bridge_vibroacoustic.resolve_auto(resolved,
                                                         model_data)
            if resolved is None:
                log(tr("ERROR: Actieve analyse 'auto': Mecway-analysetype "
                       "'{0}' wordt niet ondersteund.",
                       "ERROR: Active analysis 'auto': Mecway analysis "
                       "type '{0}' is not supported.").format(mecway_type))
                _notify(tr(
                    "Actieve analyse 'auto': het Mecway-analysetype '{0}' "
                    "heeft geen Code-Aster-analyse in de bridge "
                    "(ondersteund: statisch 3D, statisch en dynamisch 2D "
                    "en axisymmetrisch, niet-lineair statisch 3D, "
                    "dynamisch 3D (lineair en niet-lineair, ook mode "
                    "superposition), thermisch stationair en "
                    "transient, frequentie (modaal), knik en akoestiek).\n\nKies in "
                    "het startscherm zelf een analyse. Code-Aster wordt "
                    "niet gestart.",
                    "Active analysis 'auto': the Mecway analysis type "
                    "'{0}' has no Code-Aster analysis in the bridge "
                    "(supported: static 3D, static and dynamic 2D and "
                    "axisymmetric, nonlinear static 3D, "
                    "dynamic 3D (linear and nonlinear, also mode "
                    "superposition), thermal steady-state and "
                    "transient, frequency (modal), buckling and acoustics).\n\n"
                    "Choose an analysis yourself in the start screen. "
                    "Code-Aster is not started.").format(
                        mecway_type))
                return False
            CONFIG_BRIDGE["active_analysis"] = resolved
            log("INFO: Active analysis 'auto': Mecway analysis type '{0}' -> "
                "'{1}'.".format(mecway_type, resolved))

        # The table route reads only one time step from tables with all
        # steps (bridge_from_aster): with dynamics (TOUT_ORDRE) it would
        # mix steps, and the Mecway solution has time steps. Modes
        # (CALC_MODES) are not time steps; set_variable() would not set
        # them as <mode>.
        if route == "tabel" and CONFIG_BRIDGE["analyses"].get(
                CONFIG_BRIDGE["active_analysis"], {}).get(
                    "solver_command") in ("DYNA_NON_LINE", "CALC_MODES",
                                          "DYNA_VIBRA", "COMB_SISM_MODAL"):
            _notify(tr("De resultaatroute 'tabel' werkt niet voor dynamische, "
                       "modale en knikanalyses. Kies 'liml' (pagina "
                       "Algemeen). Code-Aster wordt niet gestart.",
                       "The result route 'tabel' does not work for dynamic, "
                       "modal and buckling analyses. Choose 'liml' (General "
                       "page). Code-Aster is not started."))
            return False

        # Pre-flight check: materials are needed for a meaningful analysis
        # (thermal: materials with <thermal>, bridge_thermal.py)
        if not (model_data.get("thermal_materials")
                if model_data.get("thermal") else model_data["materials"]):
            _notify(tr(
                "Geen materialen gevonden in het model.\n"
                "Code-Aster wordt niet gestart.",
                "No materials found in the model.\n"
                "Code-Aster is not started."
            ))
            return False

        # --- Step 3b: Mesh directly from the .liml (ASTER format) ---
        # No Gmsh export: it truncated group names to 8 characters. See
        # bridge_mesh.py.
        mesh_file = os.path.join(work_dir_path(), run_name(".mail"))
        mark = log_size()
        if not write_mesh(mesh_file, model_data, face_nodes=_face_nodes):
            _notify(_prep_failed(tr("Schrijven van het mesh mislukt.",
                                    "Writing the mesh failed."), mark))
            return False

        resu_name = run_name(".resu")
        _LAST["analysis"] = CONFIG_BRIDGE["active_analysis"]

        # --- Step 4: Generate .comm and .export ---
        mark = log_size()
        export_file = generate_AsterSolver_files(
            work_dir_path(), model_data, mesh_file, resu_name
        )
        if export_file is None:
            _notify(_prep_failed(tr("Genereren solver-bestanden mislukt.",
                                    "Generating the solver files failed."),
                                 mark))
            return False

        # --- Step 5 & 6: Start solver; load results back ---
        # 'mw' and 'solution' are passed on so that the external modules
        # can handle pop-ups and results outside the scripting context.
        run_start = time.time()
        job = run_AsterSolver(export_file, work_dir_path(), resu_name, mw)
        if not job:
            _notify(tr("Code-Aster kon niet gestart worden. Controleer "
                          "{0}.",
                          "Code-Aster could not be started. Check "
                          "{0}.").format(log_file_name()))
            return False
        mess_path = os.path.join(work_dir_path(), run_name(".mess"))
        stopped = job.ended_early()
        if stopped:
            # Stop button or Code-Aster window closed (AsterJob): load
            # what is there, but never continue (adaptive loop). The job
            # is ended hard, so aster_results_export (end of study.comm)
            # did not run: normally there are no results.
            note = stopped_text("user" if job.state == "stopped"
                                else "window")
            log(u"WARNING: " + note)
            _notify(tr(
                u"{0} De uitvoer tot dat moment staat in {1}. Code-Aster "
                u"schrijft de resultaten pas aan het einde van de run; een "
                u"gestopte run heeft daarom meestal geen resultaten.",
                u"{0} The output up to that moment is in {1}. Code-Aster "
                u"writes the results only at the end of the run, so a "
                u"stopped run usually has no results.").format(
                    note, os.path.basename(mess_path)))
        elif job.exit_code:
            _notify(tr(u"run_aster eindigde met exitcode {0} (fout). Zie {1} "
                       u"en het Code-Aster-venster.",
                       u"run_aster ended with exit code {0} (error). See {1} "
                       u"and the Code-Aster window.").format(
                           job.exit_code, mess_path))
        mess_errors = ([] if stopped and not os.path.exists(mess_path)
                       else aster_mess_errors(work_dir_path(), run_start))
        # Version that actually ran (header of the .mess of this run);
        # takes precedence over the estimate from the launcher path.
        mess_version = (bridge_version.aster_version_from_mess(mess_path)
                        if os.path.exists(mess_path) and
                        os.path.getmtime(mess_path) >= run_start else None)
        if mess_version is not None:
            version_notes["aster"] = bridge_version.check_aster(
                mess_version, ".mess")
        # Failed elements (bridge_failure.py) in the log and a message
        failure_note = report_failures(
            os.path.join(work_dir_path(), run_name(".mess")),
            model_data)
        if route == "liml":
            loaded = _load_liml_results(active_liml, model_data, run_start,
                                        _run_monitor(active_liml, run_id,
                                                     run_start))
        else:
            if CONFIG_BRIDGE.get("save_monitor", "summary") != "off":
                log("INFO: Saved monitor not written: only with the result "
                    "route 'liml' (the route 'tabel' fills the existing "
                    "Mecway solution through the API).")
            loaded = AsterToMecway_results(work_dir_path(),
                                           resu_name, mw, solution)
        if failure_note:
            _notify(failure_note)
        # Penalty contact: penetration against contact_pene_maxi
        for line in penetration_report(
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # Global error estimate (CALC_ERREUR, setting error_estimator)
        _report_error_estimate()
        # Static: mass, centre of gravity and sum of the reactions
        _report_static_check()
        # Fracture mechanics: K and G along the crack front (bridge_fracture)
        for line in bridge_fracture.report(
                work_dir_path(),
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # XFEM cracks: K and G along the front (bridge_xfem)
        for line in bridge_xfem.report(
                work_dir_path(),
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # Fatigue: damage and life (bridge_fatigue)
        for line in bridge_fatigue.report(
                work_dir_path(),
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # Nonlinear buckling: imperfection and CRIT_STAB per step
        _report_stability()
        # Welding source: absorbed power (bridge_welding.report_lines)
        for line in report_welding(os.path.join(work_dir_path(),
                                                run_name(".mess"))):
            _notify(line)
        # Metallurgy: phases, heat-affected zone, hardness
        # (bridge_metallurgy.report_lines)
        for line in bridge_metallurgy.report_lines(
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        if mess_errors:
            _notify(run_names(tr(
                "Code-Aster meldt fouten in study.mess:\n{0}\n\n"
                "Resultaten zijn {1}.",
                "Code-Aster reports errors in study.mess:\n{0}"
                "\n\nResults are {1}.")).format(
                              "\n\n".join(mess_errors[:5]),
                              tr("deels geladen; controleer ze",
                                 "partly loaded; check them") if loaded
                              else tr("niet geladen", "not loaded")))
            return False
        if not loaded:
            _notify(run_names(tr(
                "Geen resultaten geladen. Controleer study.mess en {0}.",
                "No results loaded. Check study.mess and {0}.")).format(
                    log_file_name()))
            return False
        if stopped:
            return False
        skipped = model_data.get("skipped_loads", [])
        if skipped:
            _notify(tr("Let op: deze belastingen/randvoorwaarden zijn "
                          "NIET naar Code-Aster vertaald, de resultaten zijn "
                          "zonder berekend:\n- {0}",
                          "Note: these loads/constraints were NOT "
                          "translated to Code-Aster; the results were "
                          "computed without them:\n- {0}").format(
                              "\n- ".join(skipped)))
        return True

    except Exception as e:
        log(tr("ERROR: Onverwachte fout in main(): {0}",
               "ERROR: Unexpected error in main(): {0}").format(str(e)))
        raise  # Pass the error on so that the except block below logs it
    finally:
        # Always show version warnings (bridge_version), also if the
        # run above stopped: a different version may be the cause.
        for key in ("mecway", "aster"):
            if version_notes.get(key):
                _notify(version_notes[key])
        # If Mecway keeps the modules in memory between two runs (NOT
        # verified), the next run would, without resetting, show and save
        # the converted analysis instead of "auto".
        CONFIG_BRIDGE["active_analysis"] = configured_analysis


# Output of older bridge versions without a timestamp; every run now
# writes its own files (run_name), these are no longer read anywhere.
_LEGACY_OUTPUTS = ("resu_mesh.msh", "study.comm", "study.export",
                   "study.mess", "study.resu", "study.rmed",
                   "study_console.txt", "study_results.xml",
                   "vergelijking_mecway_aster.csv",
                   "convergence_monitor_log.txt", "model_mesh.mail")


def _remove_stale_outputs():
    """
    Remove output of older bridge versions without a timestamp (see
    _LEGACY_OUTPUTS), so that no outdated or superfluous files remain in
    the work folder. Files with a timestamp belong to a run and are
    kept.
    """
    for name in _LEGACY_OUTPUTS:
        path = os.path.join(work_dir_path(), name)
        if os.path.exists(path):
            try:
                os.remove(path)
                log("INFO: Old output file removed: {0}".format(path))
            except OSError as e:
                log(tr("WARNING: Kon {0} niet verwijderen: {1}",
                       "WARNING: Could not delete {0}: {1}").format(path, e))


def _monitor_header(liml, run_id, analysis):
    """First lines of the Saved monitor text (bridge_monitor)."""
    return [u"MecwayAsterBridge {0} - Code-Aster".format(BRIDGE_VERSION),
            tr(u"Model: {0}", u"Model: {0}").format(liml),
            tr(u"Run: {0}, analyse {1}", u"Run: {0}, analysis {1}").format(
                run_id, analysis)]


def _run_monitor(active_liml, run_id, run_start):
    """Text for Mecway's Saved monitor of this run (setting save_monitor,
    bridge_monitor.py), or None (off, or no .mess of this run)."""
    mode = CONFIG_BRIDGE.get("save_monitor", "summary")
    mess = os.path.join(work_dir_path(), run_name(".mess"))
    if mode == "off" or not os.path.exists(mess) or \
            os.path.getmtime(mess) < run_start:
        return None
    try:
        return monitor_text(
            mess, mode, os.path.join(work_dir_path(),
                                     run_name(CONSOLE_SUFFIX)),
            _monitor_header(active_liml, run_id,
                            CONFIG_BRIDGE["active_analysis"]))
    except Exception as e:
        log(tr(u"WARNING: Saved monitor niet gemaakt: {0}",
               u"WARNING: Saved monitor not made: {0}").format(e))
        return None


def _load_liml_results(active_liml, model_data, run_start, monitor=None):
    """
    result_route "liml": Code-Aster wrote Mecway's own <results>
    (aster_results_export.py). Optionally compare with the Mecway solve,
    paste the fragment into the .liml (previous version: .bak) and open it
    again. monitor: text for Mecway's Saved monitor (_run_monitor) or None;
    without results it is written as a solution with only the monitor if
    the model has no results yet (_monitor_only). Returns True if the
    results are in Mecway.
    """
    fragment = results_file(work_dir_path())
    if (not os.path.exists(fragment) or
            os.path.getmtime(fragment) < run_start - 1.0):
        log(tr("ERROR: Geen resultaatfragment van deze run ({0}); zie "
               "study.mess.",
               "ERROR: No result fragment from this run ({0}); see "
               "study.mess.").format(fragment))
        if monitor is not None:
            _monitor_only(active_liml, monitor)
        return False
    modes = read_modes(fragment)
    active = CONFIG_BRIDGE["analyses"].get(CONFIG_BRIDGE["active_analysis"],
                                           {})
    spectrum = active.get("solver_command") == "COMB_SISM_MODAL"
    # Harmonic acoustics: the <mode> blocks are frequencies of the
    # response, not eigenmodes (bridge_acoustic.build_acoustic_harm).
    # The same for the harmonic response of a structure (bridge_harmonic).
    harmonic = (active.get("solver_command") == "DYNA_VIBRA" and
                (bridge_acoustic.is_acoustic(active) or
                 bridge_harmonic.is_harmonic(active)))
    vibro = bridge_vibroacoustic.is_vibroacoustic(active)
    if CONFIG_BRIDGE.get("mecway_solve_first", False) and spectrum:
        # Mecway computes only the modes; the maxima of the spectrum cannot
        # be compared with a Mecway solution.
        log("INFO: Spectrum analysis: no comparison with the Mecway solve "
            "(Mecway has no spectrum analysis).")
    elif CONFIG_BRIDGE.get("mecway_solve_first", False) and harmonic:
        log("INFO: Harmonic analysis: Mecway has no harmonic "
            "analysis; no comparison with the Mecway solve.")
    elif CONFIG_BRIDGE.get("mecway_solve_first", False) and vibro:
        # Mecway computes a fluid without E as a solid with E = 0
        # (seen headless: modes of 1e-7 Hz); not comparable.
        log("INFO: Vibro-acoustics: Mecway has no coupled analysis; "
            "no comparison with the Mecway solve.")
    elif CONFIG_BRIDGE.get("mecway_solve_first", False):
        if modes:
            # Vibration/buckling shapes have an arbitrary sign and are not
            # unique for multiple modes: compare only the values.
            # Complex modes: Mecway computes without damping, so compare
            # with f_n = |s| / 2 pi (bridge_modal_damping).
            summary = read_mode_summary(os.path.join(
                work_dir_path(), run_name(".mess")))
            undamped = [(m, k, summary.get(m, {}).get("FREQ_NAT", v))
                        for m, k, v in modes]
            if undamped != modes:
                log(tr("INFO: Complexe modes: vergelijking met Mecway (zonder "
                       "demping) op f_n = f_d / sqrt(1 - zeta^2).",
                       "INFO: Complex modes: comparison with Mecway (without "
                       "damping) on f_n = f_d / sqrt(1 - zeta^2)."))
            # Complex acoustic modes (impedance): Mecway computes the same
            # problem, but the numbers do not match because of the 0 Hz
            # modes (aster_acoustic_complex): use the nearest frequency.
            nearest = any("DECAY" in summary.get(m, {}) and
                          "AMOR_REDUIT" not in summary.get(m, {})
                          for m, _k, _v in modes)
            _compare_modes_with_mecway(solution, undamped, nearest=nearest)
        else:
            arrays = read_step(fragment, -1, len(model_data["mesh_nodes"]))
            _compare_with_mecway(solution, arrays, sorted(arrays),
                                 work_dir_path())
    configuration, warning = pick_configuration(active_liml)
    if warning:
        log("WARNING: " + warning)
    ok, reason = splice_results(active_liml, fragment, active_liml,
                                configuration, monitor=monitor)
    if not ok and monitor is not None:
        log(tr(u"WARNING: Resultaten met Saved monitor niet in de .liml "
               u"gezet ({0}); opnieuw zonder monitor.",
               u"WARNING: Results with Saved monitor not written into the "
               u".liml ({0}); trying again without the monitor.").format(
                   reason))
        ok, reason = splice_results(active_liml, fragment, active_liml,
                                    configuration)
    if not ok:
        log(tr("ERROR: Resultaten niet in de .liml gezet: {0}",
               "ERROR: Results not written into the .liml: {0}").format(
                   reason))
        return False
    log("SUCCESS: Results written to '{0}' (previous version: .bak); model "
        "reopened.".format(active_liml))
    # The result file is kept: with the Results... button the results
    # can be reloaded later, also after they have been removed from the
    # .liml (small .liml).
    log("INFO: Result file (can be reloaded with "
        "the Results... button): {0}".format(fragment))
    if harmonic:
        report = (bridge_acoustic.report_harmonic
                  if bridge_acoustic.is_acoustic(active)
                  else bridge_vibroacoustic_harm.report_harmonic
                  if bridge_vibroacoustic_harm.is_vibro_harm(active)
                  else bridge_harmonic.report_harmonic)
        _notify(u"\n".join(report(work_dir_path(), modes)))
        _warn_modal_mass(harmonic=True)
    elif modes:
        _report_modes(modes, extra=bridge_vibroacoustic.report_lines(
            work_dir_path()) if vibro else None, in_mecway=True)
    else:
        # Response on a modal basis (bridge_dyna_modal): the results are
        # time steps; the modes used are in the .mess as BRIDGE_MODE.
        summary = read_mode_summary(os.path.join(work_dir_path(),
                                                 run_name(".mess")))
        basis = [(k, "frequency", v["FREQ"]) for k, v in sorted(
            (k, v) for k, v in summary.items() if k != "massa")
            if "FREQ" in v]
        if basis:
            log(tr(u"INFO: Modale basis van de respons ({0} modes):",
                   u"INFO: Modal basis of the response ({0} modes):").format(
                       len(basis)))
            _report_modes(basis)
            _warn_modal_mass()
        if spectrum:
            # Response spectrum (bridge_spectrum): effective mass per
            # direction, missing mass and the total reaction.
            import bridge_spectrum
            lines = bridge_spectrum.report_summary(
                os.path.join(work_dir_path(), run_name(".mess")),
                CONFIG_BRIDGE["analyses"].get(
                    CONFIG_BRIDGE["active_analysis"], {}))
            if lines:
                _notify(u"\n".join(lines))
    mw.open(active_liml)
    if configuration:
        # Show the configuration with the new results (API:
        # mw.set_active_configuration).
        try:
            mw.set_active_configuration(configuration)
        except Exception as e:
            log(tr("WARNING: Configuratie '{0}' niet actief gemaakt: {1}",
                   "WARNING: Configuration '{0}' not made active: "
                   "{1}").format(configuration, e))
    return True


def _monitor_only(active_liml, monitor):
    """A run without results (error, stopped): if the model has no
    results yet, put a solution with only the Saved monitor into the .liml
    (previous version: .bak) and reopen it, so that the output of the run
    stays readable in Mecway. A model that already has results is left
    untouched (its results are not replaced by an empty solution); the log
    then names the .mess."""
    configuration, _warning = pick_configuration(active_liml)
    if has_results(active_liml, configuration):
        log("INFO: Run without results: the model already has results, so "
            "it is left unchanged and gets no Saved monitor; the output of "
            "the run is in {0}.".format(
                os.path.join(work_dir_path(), run_name(".mess"))))
        return
    ok, reason = splice_results(active_liml, None, active_liml,
                                configuration, monitor=monitor)
    if not ok:
        log(tr(u"WARNING: Saved monitor niet in de .liml gezet: {0}",
               u"WARNING: Saved monitor not written into the .liml: "
               u"{0}").format(reason))
        return
    log("INFO: Run without results: a solution with only the Saved monitor "
        "written to '{0}' (previous version: .bak).".format(active_liml))
    mw.open(active_liml)
    if configuration:
        try:
            mw.set_active_configuration(configuration)
        except Exception as e:
            log(tr("WARNING: Configuratie '{0}' niet actief gemaakt: {1}",
                   "WARNING: Configuration '{0}' not made active: "
                   "{1}").format(configuration, e))


_MODES_SHOWN = 20     # this many modes in the status box; all in the log


def _report_modes(modes, extra=None, in_mecway=False):
    """
    Frequencies (with effective mass) or buckling load factors in the log
    and the status box. modes: read_modes() of the result file; the
    effective mass comes from the BRIDGE_MODE lines in the .mess
    (aster_results_export.print_modes). extra: lines added at the end of
    the status box (vibro-acoustics: bridge_vibroacoustic.report_lines,
    already logged). in_mecway: the modes themselves are in Mecway (not
    the modal basis of a response); then the effective mass is also a
    Mecway variable per mode in the result (aster_results_export, S12).
    """
    # %-formatting: in IronPython "{0:.6g}".format() follows the Windows
    # locale (comma; seen, see bridge_gui._float_text).
    summary = read_mode_summary(os.path.join(work_dir_path(),
                                             run_name(".mess")))
    buckling = modes[0][1] == "bucklingfactor"
    lines = []
    totals = [0.0, 0.0, 0.0]
    rot_totals = [0.0, 0.0, 0.0]
    has_rot = False
    for mid, _kind, value in modes:
        if buckling:
            line = tr(u"Mode {0}: kniklastfactor {1}",
                      u"Mode {0}: buckling factor {1}").format(
                          mid, "%.6g" % value)
        else:
            line = tr(u"Mode {0}: {1} Hz", u"Mode {0}: {1} Hz").format(
                mid, "%.6g" % value)
            zeta = summary.get(mid, {}).get("AMOR_REDUIT")
            if zeta is not None:
                # Complex modes (bridge_modal_damping): value = f_d
                line = tr(u"Mode {0}: {1} Hz gedempt (zeta {2}, f_n {3} Hz)",
                          u"Mode {0}: {1} Hz damped (zeta {2}, f_n {3} "
                          u"Hz)").format(
                              mid, "%.6g" % value, "%.4g" % zeta,
                              "%.6g" % summary[mid].get("FREQ_NAT", value))
            decay = summary.get(mid, {}).get("DECAY")
            if decay is not None and zeta is None:
                # Complex acoustic modes (impedance,
                # aster_acoustic_complex): decay rate, reverberation time, Q
                line += tr(u", decay rate {0} 1/s", u", decay rate {0} 1/s"
                           ).format("%.6g" % decay)
                if decay > 0.0:
                    line += tr(u" (T60 {0} s, Q {1})", u" (T60 {0} s, Q {1})"
                               ).format("%.4g" % summary[mid].get("T60", 0.0),
                                        "%.4g" % summary[mid].get("Q", 0.0))
            fractions = [summary.get(mid, {}).get(k) for k in (
                "MASS_EFFE_UN_DX", "MASS_EFFE_UN_DY", "MASS_EFFE_UN_DZ")]
            # Rotations about the global axes through the origin (as Mecway;
            # aster_results_export._effective_masses)
            rotations = [summary.get(mid, {}).get(k) for k in (
                "MASS_EFFE_UN_DRX", "MASS_EFFE_UN_DRY", "MASS_EFFE_UN_DRZ")]
            if None not in fractions:
                totals = [t + f for t, f in zip(totals, fractions)]
                text = u"X/Y/Z {0}/{1}/{2}%".format(
                    *["%.1f" % (100.0 * f) for f in fractions])
                if None not in rotations:
                    has_rot = True
                    rot_totals = [t + f for t, f in zip(rot_totals,
                                                        rotations)]
                    text += u", RX/RY/RZ {0}/{1}/{2}%".format(
                        *["%.1f" % (100.0 * f) for f in rotations])
                line += tr(u" (eff. massa {0})", u" (eff. mass {0})").format(
                    text)
            # Cyclic symmetry (aster_cyclic): number of nodal diameters
            nd = summary.get(mid, {}).get("ND")
            if nd is not None and nd >= 0:
                line += u" (ND {0})".format(int(nd))
        log(u"INFO: " + line)
        lines.append(line)
    if not buckling and any(summary.get(m, {}).get("ND") is not None
                            for m, _k, _v in modes):
        # Whole wheel or only the sector (aster_cyclic.collect, BRIDGE_CYCL)
        cyc = read_cyclic_summary(os.path.join(work_dir_path(),
                                               run_name(".mess")))
        if cyc.get("WIEL") == 1:
            where = tr(u"In Mecway het hele wiel ({0} sectoren), zoals "
                       u"Mecway.", u"In Mecway the whole wheel ({0} "
                       u"sectors), like Mecway.").format(int(cyc.get("N", 0)))
        else:
            where = tr(u"In Mecway alleen de sector.",
                       u"In Mecway only the sector.")
        note = tr(u"Cyclische symmetrie: modes per aantal nodal diameters "
                  u"(ND), zoals Mecway; voor 0 < ND < N/2 hoort bij elke "
                  u"mode een tweede met dezelfde frequentie (de vorm een "
                  u"kwart golf verschoven). {0}",
                  u"Cyclic symmetry: modes per number of nodal diameters "
                  u"(ND), like Mecway; for 0 < ND < N/2 each mode has a "
                  u"second one with the same frequency (the shape shifted by "
                  u"a quarter wave). {0}").format(where)
        log(u"INFO: " + note)
        lines.append(note)
    damped = [m for m, _k, _v in modes
              if summary.get(m, {}).get("AMOR_REDUIT") is not None]
    if damped and not buckling:
        note = tr(u"Complexe modes: in Mecway de gedempte frequentie f_d en "
                  u"het reele deel van de vorm; amplitude ~ exp(-zeta 2 pi "
                  u"f_n t), f_d = f_n sqrt(1 - zeta^2) (f_n: bij "
                  u"Rayleigh-demping de ongedempte frequentie).",
                  u"Complex modes: in Mecway the damped frequency f_d and "
                  u"the real part of the shape; amplitude ~ exp(-zeta 2 pi "
                  u"f_n t), f_d = f_n sqrt(1 - zeta^2) (f_n: with Rayleigh "
                  u"damping the undamped frequency).")
        log(u"INFO: " + note)
        lines.append(note)
        cplx = [m for m in damped if summary[m].get("IMAG", 0.0) > 0.01]
        if cplx:
            note = tr(u"Mode(s) {0}: niet-proportionele demping (dempers): "
                      u"de vorm is complex (imaginair deel tot {1}% van het "
                      u"reele) en de effectieve massa (uit het reele deel) "
                      u"een benadering.",
                      u"Mode(s) {0}: non-proportional damping (dampers): the "
                      u"shape is complex (imaginary part up to {1}% of the "
                      u"real part) and the effective mass (from the real "
                      u"part) an approximation.").format(
                          ", ".join(str(m) for m in cplx),
                          "%.0f" % (100.0 * max(summary[m]["IMAG"]
                                                for m in cplx)))
            log(u"INFO: " + note)
            lines.append(note)
    acoustic_cplx = [m for m, _k, _v in modes
                     if summary.get(m, {}).get("DECAY") is not None and
                     summary[m].get("AMOR_REDUIT") is None]
    if acoustic_cplx and not buckling:
        # aster_acoustic_complex (impedance, docs/Akoestiek.md par. 3.3)
        note = tr(u"Complexe modes (impedantie): p(t) = Re(P exp((i 2 pi f "
                  u"- decay) t)), velden pressure (Re P) en pressurei (Im P); "
                  u"T60 = 6,91 / decay is de nagalmtijd (60 dB), Q = |lambda| "
                  u"/ (2 decay).",
                  u"Complex modes (impedance): p(t) = Re(P exp((i 2 pi f - "
                  u"decay) t)), fields pressure (Re P) and pressurei (Im P); "
                  u"T60 = 6.91 / decay is the reverberation time (60 dB), Q "
                  u"= |lambda| / (2 decay).")
        log(u"INFO: " + note)
        lines.append(note)
        worst = max(summary[m].get("RESIDU", 0.0) for m in acoustic_cplx)
        limit = float(CONFIG_BRIDGE["analyses"].get(
            CONFIG_BRIDGE["active_analysis"], {}).get("modal_tolerance",
                                                      1.0e-6))
        if worst > limit:
            note = tr(u"WARNING: Complexe modes: residu {0} > {1} (Controle "
                      u"modes); de eigenwaarden zijn mogelijk onnauwkeurig. "
                      u"Verfijn het mesh of vraag minder modes.",
                      u"WARNING: Complex modes: residual {0} > {1} (Check "
                      u"modes); the eigenvalues may be inaccurate. Refine "
                      u"the mesh or request fewer modes.").format(
                          "%.3g" % worst, "%.3g" % limit)
            log(note)
            lines.append(note)
    if len(lines) > _MODES_SHOWN:
        lines = lines[:_MODES_SHOWN] + [tr(u"... ({0} modes, zie de log)",
                                           u"... ({0} modes, see the log)"
                                           ).format(len(modes))]
    if not buckling and any(totals):
        total = tr(u"Effectieve massa, som over de modes: X {0}%, Y "
                   u"{1}%, Z {2}%",
                   u"Effective mass, sum over the modes: X {0}%, Y "
                   u"{1}%, Z {2}%").format(
                       *["%.1f" % (100.0 * t) for t in totals])
        if has_rot:
            total += tr(u"; rotatie om de assen door de oorsprong: RX {0}%, "
                        u"RY {1}%, RZ {2}%",
                        u"; rotation about the axes through the origin: RX "
                        u"{0}%, RY {1}%, RZ {2}%").format(
                            *["%.1f" % (100.0 * t) for t in rot_totals])
        log(u"INFO: " + total)
        lines.append(total)
        if in_mecway:
            note = tr(u"In Mecway per mode onder Solution: modal effective "
                      u"mass (kg, kg.m2) en modal effective mass fraction. "
                      u"De fractie is die van Code-Aster: gedeeld door de "
                      u"totale massa inclusief de opgelegde knopen (Mecway's "
                      u"eigen solver deelt door de vrije massa).",
                      u"In Mecway per mode under Solution: modal effective "
                      u"mass (kg, kg.m2) and modal effective mass fraction. "
                      u"The fraction is Code-Aster's: divided by the total "
                      u"mass including the constrained nodes (Mecway's own "
                      u"solver divides by the free mass).")
            log(u"INFO: " + note)
            lines.append(note)
    mass = summary.get("massa")
    if not buckling and mass and "M" in mass:
        # Denominators of the fractions (R^T M R) and the centre of gravity:
        # this lets the user interpret the rotations about the origin.
        cog = u"{0}".format(mass.get("ZWP", "?"))
        try:
            c = [float(v) for v in cog.split(",")]
            big = max([abs(v) for v in c] + [1.0e-30])
            cog = u", ".join("%.6g" % (v if abs(v) > 1.0e-9 * big else 0.0)
                             for v in c)
        except ValueError:
            pass
        log(u"INFO: Mass {0} kg, centre of gravity ({1}) m; moment of inertia "
            u"about the axes through the origin X/Y/Z {2}/{3}/{4} kg.m2, through "
            u"the centre of gravity {5}/{6}/{7} kg.m2.".format(
                "%.6g" % mass["M"], cog,
                *["%.6g" % mass.get(k, 0.0) for k in (
                    "JX", "JY", "JZ", "JZX", "JZY", "JZZ")]))
    if buckling and any(v < 0.0 for _m, _k, v in modes):
        log(tr(u"WARNING: Negatieve kniklastfactor(en): knik bij de "
               u"omgekeerde belasting (bijv. trek i.p.v. druk). Alleen een "
               u"positieve factor hoort bij de aangebrachte richting.",
               u"WARNING: Negative buckling factor(s): buckling under the "
               u"reversed load (e.g. tension instead of compression). Only "
               u"a positive factor belongs to the applied direction."))
    if not buckling and any(v < -1.0e-2 for _m, _k, v in modes):
        # Negative omega^2: K + Kg not positive (modal with prestress,
        # bridge_to_aster._prestress_plan). Rigid body modes of a free
        # model come out at ~ -1e-4 Hz (numerically zero), hence the limit.
        log(tr(u"WARNING: Negatieve frequentie(s): de drukvoorspanning is "
               u"hoger dan de kniklast van die mode (instabiel; Mecway geeft "
               u"dan 0 Hz). Verlaag de drukbelasting of controleer met een "
               u"knikanalyse.",
               u"WARNING: Negative frequency (frequencies): the compressive "
               u"prestress exceeds the buckling load of that mode (unstable; "
               u"Mecway then gives 0 Hz). Reduce the compressive load or "
               u"check with a buckling analysis."))
    elif not buckling and modes and modes[0][2] < 1.0e-2 and CONFIG_BRIDGE[
            "analyses"].get(CONFIG_BRIDGE["active_analysis"], {}).get(
                "phenomene") == "ACOUSTIQUE":
        # Cavity modes with rigid walls: mode 1 is the constant pressure
        # (bridge_acoustic.py), not an error.
        log(u"INFO: Mode 1 is at ~0 Hz: constant pressure (rigid walls "
            u"without a pressure node), as in Mecway.")
    elif not buckling and modes and modes[0][2] < 1.0e-2:
        log(tr(u"WARNING: Mode 1 heeft ~0 Hz: een starre-lichaamsbeweging "
               u"of mechanisme (te weinig opleggingen).",
               u"WARNING: Mode 1 has ~0 Hz: a rigid body motion or "
               u"mechanism (too few supports)."))
    _notify(u"\n".join(lines + list(extra or [])))


def _report_static_check():
    """
    Mass, centre of gravity and sum of the reactions of a static run
    (MECA_STATIQUE, STAT_NON_LINE) in the log and the status box, from the
    BRIDGE_STATCHECK / BRIDGE_STATREAC lines in the .mess
    (aster_results_export.print_static_check). For the user's own hand
    check (J.-P. Aubry, Beginning with code_aster, 2019, par. 4.13-4.14):
    the mass against the drawing, the reactions against the applied
    loads. Deliberately no pass/fail comparison (pressures, formulas).
    Nothing without those lines (other analyses).
    """
    mess = os.path.join(work_dir_path(), run_name(".mess"))
    mass = read_tagged(mess, "BRIDGE_STATCHECK")
    reac = read_tagged(mess, "BRIDGE_STATREAC")
    if not mass and not reac:
        return
    # %-formatting: in IronPython "{0:.6g}".format() follows the Windows
    # locale (see _report_modes).
    parts = []
    if "M" in mass:
        cog = u"{0}".format(mass.get("ZWP", "?"))
        try:
            c = [float(v) for v in cog.split(",")]
            big = max([abs(v) for v in c] + [1.0e-30])
            cog = u", ".join("%.4g" % (v if abs(v) > 1.0e-9 * big else 0.0)
                             for v in c)
        except ValueError:
            pass
        parts.append(tr(u"massa {0} kg, zwaartepunt ({1}) m",
                        u"mass {0} kg, centre of gravity ({1}) m").format(
                            "%.6g" % mass["M"], cog))
    if "FX" in reac:
        f = [reac.get(k, 0.0) for k in ("FX", "FY", "FZ")]
        big = max([abs(v) for v in f] + [1.0e-30])
        f = [v if abs(v) > 1.0e-9 * big else 0.0 for v in f]
        parts.append(tr(u"som reactiekrachten FX {0}, FY {1}, FZ {2} N",
                        u"sum of reactions FX {0}, FY {1}, FZ {2} N").format(
                            *["%.6g" % v for v in f]))
    line = tr(u"Controle: {0} (vergelijk zelf met tekening en belastingen).",
              u"Check: {0} (compare with the drawing and the loads "
              u"yourself).").format(u"; ".join(parts))
    log(u"INFO: " + line)
    _notify(line)


_MODAL_MASS_MIN = 0.90   # cumulative effective mass (Aubry 2023, par. 3.3)


def _warn_modal_mass(harmonic=False):
    """
    WARNING when the cumulative effective mass fraction of the modal basis
    stays below 90% in an excited direction (response on a modal basis:
    bridge_dyna_modal, bridge_harmonic GENE; J.-P. Aubry, Beginning
    DYNAmics with code_aster, 2023, par. 3.3 and 11.3). Excited directions
    from the load resultant (BRIDGE_EXCIT, aster_results_export.
    print_excitation; gravity/acceleration is a load vector too): the
    directions with a resultant of at least 1% of the largest. Is the
    resultant (almost) zero (self-equilibrated load, e.g. a pressure on a
    closed surface), then every direction in which the load has
    components. Fractions: BRIDGE_MODE MASS_EFFE_UN_D* of the real modes
    (without the pseudo-modes of the static correction).
    """
    mess = os.path.join(work_dir_path(), run_name(".mess"))
    excit = read_tagged(mess, "BRIDGE_EXCIT")
    if not excit:
        return
    summary = read_mode_summary(mess)
    keys = ("MASS_EFFE_UN_DX", "MASS_EFFE_UN_DY", "MASS_EFFE_UN_DZ")
    rows = [v for k, v in summary.items() if k != "massa"]
    if not rows or any(key not in v for v in rows for key in keys):
        return
    totals = [sum(v[key] for v in rows) for key in keys]
    f = [abs(excit.get(k, 0.0)) for k in ("FX", "FY", "FZ")]
    a = [abs(excit.get(k, 0.0)) for k in ("AX", "AY", "AZ")]
    if max(a) <= 0.0:
        return
    if max(f) > 0.01 * max(a):
        dirs = [d for d in range(3) if f[d] >= 0.01 * max(f)]
    else:
        dirs = [d for d in range(3) if a[d] >= 0.01 * max(a)]
    low = [d for d in dirs if totals[d] < _MODAL_MASS_MIN]
    if not low:
        return
    which = u", ".join(u"{0} {1}%".format("XYZ"[d], "%.1f" % (
        100.0 * totals[d])) for d in low)
    other = (tr(u"harm_basis PHYS (fysische coordinaten)",
                u"harm_basis PHYS (physical coordinates)") if harmonic else
             tr(u"directe tijdsintegratie in Mecway (zonder Mode "
                u"superposition, fysische coordinaten)",
                u"direct time integration in Mecway (without Mode "
                u"superposition, physical coordinates)"))
    line = tr(u"WARNING: Modale basis: effectieve massa (som over {0} modes) "
              u"onder {1}% in de belaste richting(en): {2}. De respons mist "
              u"de bijdrage van hogere modes. Reken met meer modes (Number "
              u"of modes in Mecway, of modal_modes) of met {3}.",
              u"WARNING: Modal basis: effective mass (sum over {0} modes) "
              u"below {1}% in the loaded direction(s): {2}. The response "
              u"misses the contribution of higher modes. Compute with more "
              u"modes (Number of modes in Mecway, or modal_modes) or with "
              u"{3}.").format(len(rows), "%.0f" % (100.0 * _MODAL_MASS_MIN),
                              which, other)
    log(line)
    _notify(line)


def _report_error_estimate():
    """
    Global relative error of the error estimator (CALC_ERREUR ERME, see
    bridge_to_aster._error_estimator_block) in the log and the status box,
    read from the block that Code-Aster writes to the .mess
    (read_error_summary). Nothing if the estimator did not run.
    Values: docs/Foutschatter.md (interpretation).
    """
    summary = read_error_summary(os.path.join(work_dir_path(),
                                              run_name(".mess")))
    if not summary:
        return
    s = summary[-1]
    # %-formatting: in IronPython "{0:.3g}".format() follows the Windows
    # locale (see _report_modes).
    line = tr(u"Foutschatter: globale relatieve fout {0}% (residu-schatter "
              u"ERME; deel volume {1}%, sprongen {2}%, rand {3}%). Veld in "
              u"Mecway: errorestimate (absoluut) en errorestimaterel (%).",
              u"Error estimator: global relative error {0}% (residual "
              u"estimator ERME; volume part {1}%, jumps {2}%, boundary {3}%). "
              u"Field in Mecway: errorestimate (absolute) and "
              u"errorestimaterel (%).").format(
                  "%.3g" % s["rel"], "%.3g" % s.get("volume", 0.0),
                  "%.3g" % s.get("jump", 0.0), "%.3g" % s.get("boundary", 0.0))
    log(u"INFO: " + line)
    if s["rel"] > _ERROR_COARSE_PCT:
        line += tr(u" Boven {0}%: de mesh is grof; verfijn waar "
                   u"errorestimate groot is.",
                   u" Above {0}%: the mesh is coarse; refine where "
                   u"errorestimate is large.").format(_ERROR_COARSE_PCT)
    _notify(line)


# Adaptive refinement (bridge_adapt): model_data and analysis of the last
# run, and the loops of the current sequence (main() clears history).
_LAST = {}
_ADAPT = {"history": []}


def _adapt_step():
    """
    After a successful run: adaptive refinement (setting adapt_refine,
    linear static with error estimator; docs/Foutschatter.md par. 6).
    bridge_adapt.after_run decides on the global error (.mess) and the
    error per element (result file); when refining, first a copy of the
    original model in the work folder (first loop), then mw.refine_x2 and
    mw.save(). Returns True if the model was refined (another run).
    """
    analysis = CONFIG_BRIDGE["analyses"].get(_LAST.get("analysis"), {})
    model_data = _LAST.get("model_data") or {}
    settings = bridge_adapt.adapt_settings(
        analysis, model_data.get("aster_custom", {}).get("options"))
    if settings is None:
        return False
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        _notify(tr(u"Adaptieve verfijning: alleen met resultaatroute 'liml' "
                   u"(de fout per element komt uit het resultaatbestand); "
                   u"niet verfijnd.",
                   u"Adaptive refinement: only with result route 'liml' (the "
                   u"error per element comes from the result file); not "
                   u"refined."))
        return False
    work_dir = work_dir_path()
    summary = read_error_summary(os.path.join(work_dir, run_name(".mess")))
    step = bridge_adapt.after_run(_ADAPT["history"], settings, model_data,
                                  results_file(work_dir),
                                  summary[-1] if summary else None)
    if step["notes"]:
        _notify(u"\n".join(step["notes"]))
    if not step["refine"]:
        return False
    liml = mw.file_name()
    if len(_ADAPT["history"]) == 1:
        # Mecway's refinement cannot be undone through the API: the
        # original model (with its results) is kept as a copy.
        backup = os.path.join(work_dir, run_name("_voor_verfijning.liml"))
        try:
            shutil.copy(liml, backup)
            log(u"INFO: Adaptive refinement: original model saved "
                u"as {0}.".format(backup))
            _notify(tr(u"Het oorspronkelijke model staat als {0}.",
                       u"The original model is kept as {0}.").format(backup))
        except (IOError, OSError) as e:
            log(tr(u"WARNING: Kopie van het model niet gemaakt: {0}",
                   u"WARNING: Copy of the model not made: {0}").format(e))
    if bridge_adapt.refine_in_mecway(mw, step["elements"]) is None:
        _notify(tr(u"Adaptieve verfijning: Mecway kon niet verfijnen; zie "
                   u"de log.",
                   u"Adaptive refinement: Mecway could not refine; see the "
                   u"log."))
        return False
    mw.save()
    return True


# Limit for the message "mesh is coarse" (global relative error in %); see
# docs/Foutschatter.md (interpretation).
_ERROR_COARSE_PCT = 20

# CRIT_STAB with large displacements: "close to buckling" if |lambda| drops
# below this fraction of the first |lambda| (choice of the bridge; NK-04:
# 0.7% just before the limit point).
_CRIT_NEAR = 0.05


def _report_stability():
    """
    Nonlinear buckling (docs/Modaal_en_knik.md par. 5) in the log and the
    status box: the imperfection (buckling shape, buckling load factor,
    amplitude) and the stability criterion CRIT_STAB per step, with a
    message when buckling is reached. Meaning of lambda:
    bridge_to_aster._crit_stab_kind. Nothing if both were off.
    """
    mess = os.path.join(work_dir_path(), run_name(".mess"))
    imp = read_imperfection(mess)
    if imp:
        k = imp["mode"]
        factor = imp["factors"].get(k)
        line = tr(u"Imperfectie: knikvorm {0} (kniklastfactor {1} van de "
                  u"lasten op de eindtijd), amplitude {2} m. Verplaatsingen "
                  u"in Mecway zijn t.o.v. de imperfecte vorm.",
                  u"Imperfection: buckling mode {0} (buckling factor {1} of "
                  u"the loads at the end time), amplitude {2} m. "
                  u"Displacements in Mecway are relative to the imperfect "
                  u"shape.").format(
                      k, "?" if factor is None else "%.6g" % factor,
                      "%.6g" % imp["amplitude"])
        log(u"INFO: " + line)
        _notify(line)
        if factor is None:
            log(tr(u"WARNING: Imperfectie: knikvorm {0} niet gevonden in de "
                   u"lineaire knikberekening; controleer de .mess.",
                   u"WARNING: Imperfection: buckling mode {0} not found in "
                   u"the linear buckling analysis; check the .mess.")
                .format(k))
        elif factor < 0.0:
            log(tr(u"WARNING: Imperfectie: knikvorm {0} hoort bij de "
                   u"omgekeerde last (kniklastfactor {1} < 0). Kies een "
                   u"mode met een positieve factor (imperfection_mode).",
                   u"WARNING: Imperfection: buckling mode {0} belongs to the "
                   u"reversed load (buckling factor {1} < 0). Choose a mode "
                   u"with a positive factor (imperfection_mode).").format(
                       k, "%.6g" % factor))
    cs = read_crit_stab(mess)
    if cs is None:
        return
    rows = cs["rows"]
    if not rows:
        log(tr(u"WARNING: CRIT_STAB gaf geen waarden ({0}); zie de .mess.",
               u"WARNING: CRIT_STAB gave no values ({0}); see the .mess.")
            .format(cs.get("missing") or "-"))
        return
    t_last, lam_last = rows[-1]
    if cs["kind"] == "factor":
        for t, lam in rows:
            log(u"INFO: CRIT_STAB t = %.6g: critical load factor %.6g" %
                (t, lam))
        line = tr(u"Stabiliteit (CRIT_STAB): op t = {0} kritische "
                  u"lastfactor {1}: de last van dat moment x {1} geeft knik "
                  u"(lineaire schatting rond de huidige toestand).",
                  u"Stability (CRIT_STAB): at t = {0} critical load factor "
                  u"{1}: the load at that moment x {1} gives buckling "
                  u"(linear estimate about the current state).").format(
                      "%.6g" % t_last, "%.6g" % lam_last)
        reached = [(t, lam) for t, lam in rows if 0.0 < lam <= 1.0]
        if reached:
            warn = tr(u"WARNING: Knik bereikt: vanaf t = {0} is de kritische "
                      u"lastfactor <= 1 ({1}); de last is daar boven de "
                      u"kniklast. Zonder imperfectie blijft een perfecte "
                      u"constructie in de berekening recht: geef een "
                      u"imperfectie (imperfection_amplitude) voor het gedrag "
                      u"na knik.",
                      u"WARNING: Buckling reached: from t = {0} the critical "
                      u"load factor is <= 1 ({1}); the load there exceeds the "
                      u"buckling load. Without an imperfection a perfect "
                      u"structure stays straight in the analysis: add an "
                      u"imperfection (imperfection_amplitude) for the "
                      u"behaviour after buckling.").format(
                          "%.6g" % reached[0][0], "%.6g" % reached[0][1])
            log(warn)
            line += u" " + warn[len("WARNING: "):]
        elif lam_last < 0.0:
            line += tr(u" Negatief: knik bij de omgekeerde last.",
                       u" Negative: buckling under the reversed load.")
    else:
        for t, lam in rows:
            log(u"INFO: CRIT_STAB t = %.6g: stability criterion %.6g "
                u"(< 0 stable, 0 = buckling)" % (t, lam))
        line = tr(u"Stabiliteit (CRIT_STAB, grote verplaatsingen): op t = "
                  u"{0} criterium {1} (kleinste eigenwaarde van de "
                  u"tangentstijfheid met omgekeerd teken: < 0 stabiel, 0 = "
                  u"knik; geen lastfactor).",
                  u"Stability (CRIT_STAB, large displacements): at t = {0} "
                  u"criterion {1} (smallest eigenvalue of the tangent "
                  u"stiffness with reversed sign: < 0 stable, 0 = buckling; "
                  u"not a load factor).").format(
                      "%.6g" % t_last, "%.6g" % lam_last)
        est = crit_stab_estimate(rows)
        if est and est[0] == "kruising":
            warn = tr(u"WARNING: Knik of instabiliteit bereikt rond t = {0} "
                      u"(het criterium wordt 0).",
                      u"WARNING: Buckling or instability reached around t = "
                      u"{0} (the criterion becomes 0).").format(
                          "%.6g" % est[1])
            log(warn)
            line += u" " + warn[len("WARNING: "):]
        elif est:
            line += tr(u" Geschat knikpunt t ~ {0} (de laatste twee stappen "
                       u"lineair doorgetrokken naar 0; loopt de last vanaf 0 "
                       u"evenredig met de tijd op, dan is de kniklast ~ {1} "
                       u"x de last op t = {2}).",
                       u" Estimated buckling point t ~ {0} (last two steps "
                       u"extended linearly to 0; if the load rises from 0 in "
                       u"proportion to time, the buckling load is ~ {1} x "
                       u"the load at t = {2}).").format(
                           "%.6g" % est[1], "%.4g" % (est[1] / t_last),
                           "%.6g" % t_last)
        if (lam_last < 0.0 and
                abs(lam_last) < _CRIT_NEAR * abs(rows[0][1])):
            warn = tr(u"WARNING: Het stabiliteitscriterium is bijna 0: de "
                      u"constructie is dicht bij knik of een grenspunt "
                      u"(stopt de berekening hier, dan is dit de "
                      u"draagkracht).",
                      u"WARNING: The stability criterion is almost 0: the "
                      u"structure is close to buckling or a limit point (if "
                      u"the analysis stops here, this is the load "
                      u"capacity).")
            log(warn)
            line += u" " + warn[len("WARNING: "):]
    _notify(line)


# ==========================================
# MESSAGES AND MAIN WINDOW
# ==========================================
# Messages of a run or a result action. With the main window
# (WinForms) they go to the status box; without it (mw.input fallback)
# as mw.message.
_NOTES = {"list": [], "popup": True}


def _notify(text):
    _NOTES["list"].append(u"{0}".format(text))
    if _NOTES["popup"]:
        mw.message(text)


def _prep_failed(head, mark):
    """Message when the preparation stops before Code-Aster (model read,
    mesh, solver files): head, the first ERROR lines that this step wrote
    to the log after mark (bridge_utils.log_errors) and a reference to the
    log for the rest."""
    errors = log_errors(mark)
    if not errors:
        return tr(u"{0} Code-Aster is niet gestart. Controleer {1}.",
                  u"{0} Code-Aster was not started. Check {1}.").format(
                      head, log_file_name())
    return tr(u"{0} Code-Aster is niet gestart:\n\n{1}\n\nMeer in {2}.",
              u"{0} Code-Aster was not started:\n\n{1}\n\nMore in {2}."
              ).format(head, u"\n".join(errors), log_file_name())


def _status_text(ok, what):
    """Text for the status box after a run or result action."""
    head = (tr(u"{0}: klaar.", u"{0}: done.") if ok else
            tr(u"{0}: gestopt (zie de meldingen hieronder en {1}).",
               u"{0}: stopped (see the messages below and {1}).")).format(
                   what, log_file_name())
    return u"\n\n".join([head] + _NOTES["list"])


def _open_in_mwpost(results_path):
    """
    Results... button "In MWHub Post": the run of results_path
    (<model>_<run_id>_results.xml) in MWHub Post (AdvancedToolsHub,
    bridge_mwpost: job next to the .rmed/.pvd + the hub's launcher).
    Returns (ok, text for the status box).
    """
    import bridge_mwpost
    import bridge_version
    suffix = "_results.xml"
    base = (results_path[:-len(suffix)] if results_path.endswith(suffix)
            else os.path.splitext(results_path)[0])
    got = bridge_mwpost.open_run(
        base, mecway_version=bridge_version.mecway_version_from_liml(
            mw.file_name()))
    if got is None:
        return False, tr(
            "AdvancedToolsHub niet gevonden (instelling "
            "'advancedtoolshub_dir', %ADVANCEDTOOLSHUB_DIR% of de map "
            "naast deze repository).",
            "AdvancedToolsHub not found (setting 'advancedtoolshub_dir', "
            "%ADVANCEDTOOLSHUB_DIR% or the folder next to this "
            "repository).")
    ok, lines = got
    if lines:
        return ok, u"\n".join(lines)
    return ok, tr("Run geopend in MWHub Post: {0}",
                  "Run opened in MWHub Post: {0}").format(
                      os.path.basename(base))


def _results_action():
    """
    Results... button: load an earlier run or remove the results from the
    open model (small .liml). See bridge_results_liml and
    docs/Handleiding.md par. 5.1. Returns (ok, text for the status box).
    """
    set_run_log(None)
    work_dir = work_dir_path()
    items = list_results(work_dir)
    try:
        choice = results_dialog(items, work_dir)
    except ImportError:
        newest = items[0]["path"] if items else ""
        raw = mw.input(tr(
            "Pad van het resultaatbestand (leeg = nieuwste: {0}), of '-' om "
            "de resultaten uit het model te verwijderen:",
            "Path of the result file (empty = newest: {0}), or '-' to "
            "remove the results from the model:").format(newest or "-"))
        raw = "" if raw is None else "{0}".format(raw).strip().strip('"')
        choice = ({"action": "strip"} if raw == "-" else
                  {"action": "load", "path": raw or newest}
                  if (raw or newest) else None)
    if not choice:
        return True, u""
    if choice["action"] == "mwpost":
        return _open_in_mwpost(choice["path"])
    save_error = _save_model()
    if save_error:
        return False, save_error
    liml = mw.file_name()
    if choice["action"] == "strip":
        ok, reason = strip_results(liml)
        if not ok:
            return False, reason
        log("INFO: Results removed from '{0}'.".format(liml))
        mw.open(liml)
        return True, tr("Resultaten uit het model verwijderd; de .liml is nu "
                        "{0} kB (vorige versie: .bak).",
                        "Results removed from the model; the .liml is now "
                        "{0} kB (previous version: .bak).").format(
                            int(os.path.getsize(liml) / 1000))
    path = choice["path"]
    if not os.path.isfile(path):
        return False, tr("Bestand niet gevonden: {0}",
                         "File not found: {0}").format(path)
    info = run_files(path)
    ok, note = check_results_fit(liml, path, info["mail"])
    if not ok:
        log(tr("ERROR: Resultaten {0} passen niet bij {1}: {2}",
               "ERROR: Results {0} do not fit {1}: {2}").format(
                   path, liml, note))
        return False, tr("Deze resultaten passen niet bij het open model:\n"
                         "{0}\nNiet ingeladen.",
                         "These results do not fit the open model:\n{0}\n"
                         "Not loaded.").format(note)
    configuration, warning = pick_configuration(liml)
    # Saved monitor from the .mess of that run (if it is still there)
    monitor = None
    mode = CONFIG_BRIDGE.get("save_monitor", "summary")
    stem = info["comm"][:-len(".comm")]
    if mode != "off" and os.path.exists(stem + ".mess"):
        try:
            monitor = monitor_text(
                stem + ".mess", mode, stem + CONSOLE_SUFFIX,
                _monitor_header(info["model"] or liml, info["run_id"], "-"))
        except Exception as e:
            log(tr(u"WARNING: Saved monitor niet gemaakt: {0}",
                   u"WARNING: Saved monitor not made: {0}").format(e))
    ok, reason = splice_results(liml, path, liml, configuration,
                                monitor=monitor)
    if not ok and monitor is not None:
        ok, reason = splice_results(liml, path, liml, configuration)
    if not ok:
        return False, tr("Resultaten niet ingeladen: {0}",
                         "Results not loaded: {0}").format(reason)
    log("SUCCESS: Results '{0}' written to '{1}'.".format(path, liml))
    mw.open(liml)
    if configuration:
        try:
            mw.set_active_configuration(configuration)
        except Exception as e:
            log(tr("WARNING: Configuratie '{0}' niet actief gemaakt: {1}",
                   "WARNING: Configuration '{0}' not made active: "
                   "{1}").format(configuration, e))
    notes = [tr("Resultaten ingeladen: {0}", "Results loaded: {0}").format(
        os.path.basename(path))] + [n for n in (note, warning) if n]
    return True, u"\n".join(notes)


def main():
    """
    The main window keeps coming back until the user clicks Close:
    Start does a run, Results... loads or removes results; the
    convergence screen and the documentation work in the window itself
    (bridge_gui). Without WinForms (mw.input fallback): one run.
    """
    status = u""
    while True:
        # Outside a run the bridge logs to bridge_log.txt (not to the log
        # of the previous run). The open model determines the work folder
        # with work_dir_beside_model (start screen, Results...).
        set_model_path(mw.file_name())
        set_run_log(None)
        settings = run_settings_dialog(mw, status)
        action = settings.get("action", "run" if settings["ok"] else "close")
        if action == "results":
            try:
                ok, text = _results_action()
            except Exception as e:
                ok, text = False, u"{0}".format(e)
            if text or not ok:
                status = text if ok else tr(u"Resultaten: {0}",
                                            u"Results: {0}").format(text)
            continue
        if action != "run":
            return
        _NOTES["list"] = []
        _NOTES["popup"] = settings["gui"] != "winforms"
        try:
            _ADAPT["history"] = []
            ok = _run(settings)
            # Adaptive refinement: refine and compute again as long as
            # bridge_adapt says so (each run waits for Code-Aster in the
            # same way, run_AsterSolver; a stopped run ends the loop).
            while ok and _adapt_step():
                ok = _run(dict(settings, changes=[], save_errors=[]))
        except Exception as e:
            try:
                log("CRITICAL ERROR: {0}".format(str(e)))
            except Exception:
                pass
            _notify(tr("MecwayAsterBridge gestopt door een fout:\n{0}",
                       "MecwayAsterBridge stopped by an error:\n{0}").format(
                           str(e)))
            ok = False
        if settings["gui"] != "winforms":
            if ok:
                mw.message(tr("MecwayAsterBridge succesvol voltooid.",
                              "MecwayAsterBridge completed successfully."))
            return
        status = _status_text(ok, run_name(""))


# ==========================================
# ENTRY POINT
# Mecway runs this script directly; main() is called here.
# One bridge at a time per Mecway (bridge_gui.claim_instance): the main
# window is non-modal, so Tools > MecwayAsterBridgeMain stays available.
# ==========================================
_instance = claim_instance()
if _instance is None:
    mw.message(instance_busy_text())
else:
    try:
        main()
    except Exception as e:
        try:
            log("CRITICAL ERROR: {0}".format(str(e)))
        except Exception:
            pass
        mw.message(tr("MecwayAsterBridge gestopt door een fout:\n{0}",
                      "MecwayAsterBridge stopped by an error:\n{0}").format(
                          str(e)))
    finally:
        release_instance(_instance)
