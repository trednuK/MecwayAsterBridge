# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# MecwayAsterBridgeMain.py
# Hoofdscript voor de Mecway-naar-Code-Aster-brug.
# Wordt uitgevoerd vanuit de Mecway scripting-engine (IronPython 2.7.9).
#
# De objecten 'mw' (Mecway API) en 'solution' (actieve solution) zijn
# impliciet beschikbaar vanuit de Mecway scripting-context; ze worden
# NIET hier gedefinieerd maar wel doorgegeven aan functies in
# bridge_gui.py, bridge_run_aster.py en bridge_from_aster.py die buiten de
# scripting-context draaien.
#
# Module-architectuur:
#   bridge_utils         : config, logging, eenheidsconversie  (gedeelde basis)
#   bridge_gui           : run_settings_dialog()                (startscherm)
#   bridge_bcs           : BC-klassen + SUPPORTED_BCS-registry
#   bridge_from_liml     : extract_aster_data_from_liml()       (Mecway -> dict)
#   bridge_mesh          : write_mesh()                         (.liml -> mesh)
#   bridge_to_aster      : generate_AsterSolver_files()         (dict -> .comm/.export)
#   bridge_run_aster     : run_AsterSolver()                    (start solver)
#   bridge_from_aster    : AsterToMecway_results()              (.resu -> Mecway)
#   bridge_thermal       : parse_thermal() / build_thermal()    (T30/T31 ->
#                          THER_LINEAIRE / THER_NON_LINE)
#   (modaal V30 / knik B30: bridge_to_aster._build_modal -> CALC_MODES;
#    de modes komen als <mode> in de .liml, zie _report_modes)
#   bridge_welding       : apply() / report_lines()             (#ASTER-LASBRON:
#                          bewegende lasbron in ther_3d)
#   bridge_thermomech    : build_blocks() / report_lines()      (T31 met
#                          Thermal stress: daarna STAT_NON_LINE, restspanning)
#   bridge_metallurgy    : apply() / report_lines()             (#ASTER-
#                          METALLURGIE: fasen en hardheid met CALC_META,
#                          optie metallurgische wet in de keten)
#   bridge_dyna_modal    : build_dyna_modal()                   (D30 met mode
#                          superposition -> DYNA_VIBRA GENE)
#   bridge_acoustic      : parse_acoustic() / build_acoustic_modes()
#                          (A30 holtemodes -> ACOUSTIQUE + CALC_MODES) /
#                          build_acoustic_harm() (A30 met bron ->
#                          DYNA_VIBRA HARM, drukveld per frequentie)
#   bridge_vibroacoustic : parse_vibro() / build_vibroacoustic_modes()
#                          (V30 met een fluidum -> 3D_FLUIDE + FLUI_STRU,
#                          gekoppelde modes)
#   bridge_vibroacoustic_harm : build_vibroacoustic_harm() / report_harmonic()
#                          (hetzelfde model per frequentie -> DYNA_VIBRA
#                          HARM PHYS, 3D_FLUI_ABSO, bronnen, microfoons)
#   bridge_spectrum     : build_spectrum()                     (responsspectrum
#                          -> CALC_MODES + COMB_SISM_MODAL)
#   bridge_harmonic      : build_harmonic()                     (harmonische
#                          respons -> DYNA_VIBRA HARM, per frequentie)
#   bridge_fracture      : front_cells() / fracture_block() / report()
#                          (SCHEUR_-selecties bij lineair statisch ->
#                          DEFI_FOND_FISS + CALC_G + POST_K1_K2_K3, K en G
#                          in <model>_<run_id>_scheur.csv en het statusvak)
#   bridge_xfem          : mesh_cells() / model_block() / result_block() /
#                          k_block() / report() (#ASTER-XFEM of XFEM_-
#                          vlakselectie: scheur zonder mesh ->
#                          DEFI_FISS_XFEM + CALC_G_XFEM + POST_K1_K2_K3;
#                          met med_export ook <model>_<run_id>_xfem.rmed)
#   bridge_fatigue       : fatigue_block() / report()          (#ASTER-WOHLER:
#                          vermoeiing, schade en levensduur per knoop via
#                          aster_fatigue.py in de job; velden damage/life)
#   AsterTemplate_*.comm : een .comm-template per analysetype (bestandsnaam
#                          per analyse in CONFIG_BRIDGE["analyses"], gezocht
#                          in de map van de scripts: template_path)
#
# Werkvolgorde:
#   0. Hoofdvenster (bridge_gui): instellingen (opgeslagen in
#      bridge_utils.py bij Starten), documentatie, convergentiescherm en
#      resultaten (Resultaten...). Na een run komt het venster terug, met de
#      uitkomst in het statusvak; Sluiten stopt de bridge.
#   1. Optioneel: solve het model in Mecway (controle: zijn er fouten?)
#   1b. Past de Mecway-solution bij het model? Anders stoppen (de resultaten
#      kunnen alleen op de knopen van de solution worden ingeladen)
#   2. Sla het model op (.liml)
#   3. Lees mesh, BC's, materialen en selecties uit het .liml-bestand
#      (stopt als er geen materialen zijn). Bij active_analysis = "auto"
#      volgt de analyse het Mecway-analysetype (alleen voor deze run).
#   3b. Schrijf het mesh in het ASTER-formaat (bridge_mesh)
#   4. Genereer <model>_<run_id>.comm en .export
#   5. Start Code-Aster; wacht op bevestiging van de gebruiker
#   6. Laad de resultaten terug in Mecway
#   7. Optioneel (adapt_refine, lineair statisch): verfijn de elementen met
#      de grootste geschatte fout in Mecway en begin weer bij 2
#      (bridge_adapt, _adapt_step)
#
# Configuratie (paden, CPU-aantallen, actieve analyse) staat in
# bridge_utils.py (CONFIG_BRIDGE) en is via het startscherm aan te passen.
#
# Bestanden in de werkmap: alles van een run heet <model>_<run_id>... met
# <model> de naam van het Mecway-bestand en run_id de tijdstempel
# (bridge_utils.run_name): _bridge_log.txt, .mail, .comm, .export, .mess,
# _console.txt, _results.xml (de resultaten, later opnieuw in te laden met
# de knop Resultaten... in het hoofdvenster) en, afhankelijk van de
# instellingen, .rmed, .resu en _vergelijking.csv.

import os
import shutil
import time
from datetime import datetime

# Module-imports volgen de dataflow: utils -> gui -> from_liml -> mesh ->
# to_aster -> run_aster -> from_aster. Alle modules importeren bridge_utils,
# dat zelf geen bridge_*-modules importeert. Daarnaast importeren
# bridge_from_liml en bridge_mesh bridge_bcs, en bridge_gui
# RESULT_FIELD_SPECS uit bridge_from_aster; geen daarvan importeert terug.
from bridge_utils       import (CONFIG_BRIDGE, log, resolve_auto_analysis,
                                set_run_log, log_file_name, tr, run_name,
                                run_names, path_too_long, work_dir_path,
                                exe_aster_path, BRIDGE_VERSION)
from bridge_gui         import run_settings_dialog, results_dialog
from bridge_from_liml   import extract_aster_data_from_liml
from bridge_mesh        import write_mesh
from bridge_to_aster    import generate_AsterSolver_files, results_file
from bridge_run_aster   import run_AsterSolver, aster_mess_errors
from bridge_from_aster  import (AsterToMecway_results, check_solution_mesh,
                                _compare_with_mecway,
                                _compare_modes_with_mecway)
from bridge_results_liml import (splice_results, read_step,
                                 pick_configuration, strip_results,
                                 list_results, run_files, check_results_fit,
                                 read_modes, read_mode_summary,
                                 read_cyclic_summary,
                                 read_error_summary, read_crit_stab,
                                 crit_stab_estimate, read_imperfection)
from bridge_failure     import report_failures
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
# VLAKKNOPEN UIT MECWAY
# ==========================================
def _face_nodes(eid, faceid):
    """Knopen van vlak faceid van element eid, zoals Mecway ze kent
    (mw.face_nodes; FaceId-nummers zijn die van <face> in de .liml)."""
    return list(mw.face_nodes(FaceId(eid, faceid)))


# ==========================================
# HOOFDFUNCTIE
# ==========================================
def _run(settings):
    """
    Een bridge-run met de instellingen van het hoofdvenster: model opslaan,
    vertalen, Code-Aster starten en de resultaten inladen. Meldingen gaan
    via _notify (statusvak van het hoofdvenster). Returns True als de
    resultaten in Mecway staan.
    """
    # Unieke run-ID (datum/tijd) voor alle bestanden van deze simulatie
    # (zie de kop van dit bestand). Eerst, zodat het statusvak ook bij een
    # fout hieronder de naam van deze run toont.
    # Bestandsnamen: <Mecway-bestand>_<run_id>... (mw.file_name(): het
    # open model; nog niet opgeslagen: "model").
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    set_run_log(run_id, mw.file_name())

    # Maak de werkmap aan als die nog niet bestaat
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
    log("INFO: Werkmap {0}; Code-Aster {1}.".format(work_dir_path(),
                                                    exe_aster_path()))
    # Versiecontrole (bridge_version.py): alleen een WARNING, de run gaat
    # door. De meldingen komen aan het eind in het statusvak (finally).
    # Code-Aster hier uit het launcherpad, na de run uit de .mess; Mecway
    # na het opslaan uit de .liml (stap 2).
    version_notes = {}
    version_notes["aster"] = bridge_version.check_aster(
        bridge_version.aster_version_from_launcher(exe_aster_path()),
        "launcher-pad")
    for analysis, key, _kind, old, new in settings["changes"]:
        log("INSTELLING: {0}{1}: {2} -> {3}".format(
            "" if analysis is None else "analyses['{0}'].".format(analysis),
            key, old, new))
    for err in settings["save_errors"]:
        log(tr("WARNING: Opslaan instelling mislukt: {0}",
               "WARNING: Saving setting failed: {0}").format(err))

    configured_analysis = CONFIG_BRIDGE["active_analysis"]
    try:
        # --- Stap 1: Solve in Mecway (optionele controle op fouten) ---
        # De Mecway-API documenteert geen returnwaarde voor mw.solve(); een
        # fout wordt daarom alleen herkend als mw.solve() een exceptie geeft.
        if CONFIG_BRIDGE.get("mecway_solve_first", False):
            log("INFO: Mecway-solve ter controle gestart.")
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
            log("INFO: Mecway-solve voltooid.")

        # --- Stap 1b: Past de solution bij het model? ---
        # solution.set_variable() kan alleen waarden kwijt op de knopen van
        # de laatste Mecway-solve. Na een modelwijziging (gezien in Mecway:
        # mesh verfijnd van 12 naar 45 knopen) werden de resultaten op 33
        # knopen stil weggelaten. Daarom vóór de Code-Aster-run controleren.
        # Alleen nodig voor de tabelroute (set_variable); de liml-route
        # schrijft de solution zelf.
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

        # --- Stap 2: Opslaan ---
        mw.save()
        active_liml = mw.file_name()  # Pad naar het actieve .liml-bestand
        version_notes["mecway"] = bridge_version.check_mecway(active_liml)[1]

        # --- Stap 3: Lees model_data uit het .liml-bestand ---
        model_data = extract_aster_data_from_liml(active_liml)
        _LAST["model_data"] = model_data      # adaptieve verfijning
        if model_data is None:
            _notify(tr("Het model kon niet gelezen worden. Controleer {0}.",
                       "The model could not be read. Check {0}.").format(
                           log_file_name()))
            return False

        # --- Stap 3a: "auto" -> analyse volgens het Mecway-analysetype ---
        # Alleen in het geheugen en alleen voor deze run (de finally
        # hieronder zet "auto" terug); get_active_analysis() in
        # bridge_to_aster/bridge_from_aster ziet zo de gekozen analyse.
        if CONFIG_BRIDGE["active_analysis"] == "auto":
            mecway_type = model_data.get("analysis_type", "")
            resolved = resolve_auto_analysis(
                mecway_type, model_data.get("mode_superposition"))
            # A30 met een bron (BRON_, #ASTER-BRON): harmonisch drukveld
            resolved = bridge_acoustic.resolve_auto(resolved, model_data)
            # V30 met een fluidum-onderdeel: vibro-akoestiek
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
                    "(ondersteund: statisch 3D, niet-lineair statisch 3D, "
                    "dynamisch 3D (lineair en niet-lineair, ook mode "
                    "superposition), thermisch stationair en "
                    "transient, frequentie (modaal), knik en akoestiek).\n\nKies in "
                    "het startscherm zelf een analyse. Code-Aster wordt "
                    "niet gestart.",
                    "Active analysis 'auto': the Mecway analysis type "
                    "'{0}' has no Code-Aster analysis in the bridge "
                    "(supported: static 3D, nonlinear static 3D, "
                    "dynamic 3D (linear and nonlinear, also mode "
                    "superposition), thermal steady-state and "
                    "transient, frequency (modal), buckling and acoustics).\n\n"
                    "Choose an analysis yourself in the start screen. "
                    "Code-Aster is not started.").format(
                        mecway_type))
                return False
            CONFIG_BRIDGE["active_analysis"] = resolved
            log("INFO: Actieve analyse 'auto': Mecway-analysetype '{0}' -> "
                "'{1}'.".format(mecway_type, resolved))

        # De tabelroute leest alleen een tijdstap uit tabellen met alle
        # stappen (bridge_from_aster): bij dynamica (TOUT_ORDRE) zou hij
        # stappen mengen en heeft de Mecway-solution tijdstappen. Modes
        # (CALC_MODES) zijn geen tijdstappen; set_variable() zou ze niet
        # als <mode> zetten.
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

        # Pre-flight check: er moeten materialen zijn voor een zinvolle analyse
        # (thermisch: materialen met <thermal>, bridge_thermal.py)
        if not (model_data.get("thermal_materials")
                if model_data.get("thermal") else model_data["materials"]):
            _notify(tr(
                "Geen materialen gevonden in het model.\n"
                "Code-Aster wordt niet gestart.",
                "No materials found in the model.\n"
                "Code-Aster is not started."
            ))
            return False

        # --- Stap 3b: Mesh rechtstreeks uit de .liml (ASTER-formaat) ---
        # Geen Gmsh-export: die kapte groepsnamen af op 8 tekens. Zie
        # bridge_mesh.py.
        mesh_file = os.path.join(work_dir_path(), run_name(".mail"))
        if not write_mesh(mesh_file, model_data, face_nodes=_face_nodes):
            _notify(tr("Schrijven van het mesh mislukt. Controleer "
                          "{0}.",
                          "Writing the mesh failed. Check {0}.").format(
                              log_file_name()))
            return False

        resu_name = run_name(".resu")
        _LAST["analysis"] = CONFIG_BRIDGE["active_analysis"]

        # --- Stap 4: Genereer .comm en .export ---
        export_file = generate_AsterSolver_files(
            work_dir_path(), model_data, mesh_file, resu_name
        )
        if export_file is None:
            _notify(tr("Genereren solver-bestanden mislukt. Controleer "
                          "{0}.",
                          "Generating the solver files failed. Check "
                          "{0}.").format(log_file_name()))
            return False

        # --- Stap 5 & 6: Start solver; laad resultaten terug ---
        # 'mw' en 'solution' worden doorgegeven zodat de externe modules
        # buiten de scripting-context pop-ups en resultaten kunnen beheren.
        run_start = time.time()
        if not run_AsterSolver(export_file, work_dir_path(), resu_name, mw):
            _notify(tr("Code-Aster kon niet gestart worden. Controleer "
                          "{0}.",
                          "Code-Aster could not be started. Check "
                          "{0}.").format(log_file_name()))
            return False
        mess_errors = aster_mess_errors(work_dir_path(), run_start)
        # Versie die echt draaide (kop van de .mess van deze run); gaat
        # voor de schatting uit het launcherpad.
        mess_path = os.path.join(work_dir_path(), run_name(".mess"))
        mess_version = (bridge_version.aster_version_from_mess(mess_path)
                        if os.path.exists(mess_path) and
                        os.path.getmtime(mess_path) >= run_start else None)
        if mess_version is not None:
            version_notes["aster"] = bridge_version.check_aster(
                mess_version, ".mess")
        # Bezweken elementen (bridge_failure.py) in de log en een melding
        failure_note = report_failures(
            os.path.join(work_dir_path(), run_name(".mess")),
            model_data)
        if route == "liml":
            loaded = _load_liml_results(active_liml, model_data, run_start)
        else:
            loaded = AsterToMecway_results(work_dir_path(),
                                           resu_name, mw, solution)
        if failure_note:
            _notify(failure_note)
        # Globale foutschatting (CALC_ERREUR, instelling error_estimator)
        _report_error_estimate()
        # Breukmechanica: K en G langs het scheurfront (bridge_fracture)
        for line in bridge_fracture.report(
                work_dir_path(),
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # XFEM-scheuren: K en G langs het front (bridge_xfem)
        for line in bridge_xfem.report(
                work_dir_path(),
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # Vermoeiing: schade en levensduur (bridge_fatigue)
        for line in bridge_fatigue.report(
                work_dir_path(),
                os.path.join(work_dir_path(), run_name(".mess"))):
            _notify(line)
        # Niet-lineaire knik: imperfectie en CRIT_STAB per stap
        _report_stability()
        # Lasbron: opgenomen vermogen (bridge_welding.report_lines)
        for line in report_welding(os.path.join(work_dir_path(),
                                                run_name(".mess"))):
            _notify(line)
        # Metallurgie: fasen, warmte-beinvloede zone, hardheid
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
        raise  # Geef de fout door zodat het except-blok hieronder hem logt
    finally:
        # Versiewaarschuwingen (bridge_version) altijd tonen, ook als de
        # run hierboven stopte: een andere versie kan de oorzaak zijn.
        for key in ("mecway", "aster"):
            if version_notes.get(key):
                _notify(version_notes[key])
        # Houdt Mecway de modules tussen twee runs in het geheugen (NIET
        # geverifieerd), dan zou de volgende run zonder terugzetten de
        # omgezette analyse i.p.v. "auto" tonen en opslaan.
        CONFIG_BRIDGE["active_analysis"] = configured_analysis


# Uitvoer van oudere bridge-versies zonder tijdstempel; elke run schrijft
# nu eigen bestanden (run_name), deze worden nergens meer gelezen.
_LEGACY_OUTPUTS = ("resu_mesh.msh", "study.comm", "study.export",
                   "study.mess", "study.resu", "study.rmed",
                   "study_console.txt", "study_results.xml",
                   "vergelijking_mecway_aster.csv",
                   "convergence_monitor_log.txt", "model_mesh.mail")


def _remove_stale_outputs():
    """
    Verwijder uitvoer van oudere bridge-versies zonder tijdstempel (zie
    _LEGACY_OUTPUTS), zodat er geen verouderde of overbodige bestanden in
    de werkmap blijven. Bestanden met een tijdstempel horen bij een run en
    blijven staan.
    """
    for name in _LEGACY_OUTPUTS:
        path = os.path.join(work_dir_path(), name)
        if os.path.exists(path):
            try:
                os.remove(path)
                log("INFO: Oud uitvoerbestand verwijderd: {0}".format(path))
            except OSError as e:
                log(tr("WARNING: Kon {0} niet verwijderen: {1}",
                       "WARNING: Could not delete {0}: {1}").format(path, e))


def _load_liml_results(active_liml, model_data, run_start):
    """
    result_route "liml": Code-Aster schreef Mecway's eigen <results>
    (aster_results_export.py). Vergelijk eventueel met de Mecway-solve,
    plak het fragment in de .liml (vorige versie: .bak) en open die
    opnieuw. Returns True als de resultaten in Mecway staan.
    """
    fragment = results_file(work_dir_path())
    if (not os.path.exists(fragment) or
            os.path.getmtime(fragment) < run_start - 1.0):
        log(tr("ERROR: Geen resultaatfragment van deze run ({0}); zie "
               "study.mess.",
               "ERROR: No result fragment from this run ({0}); see "
               "study.mess.").format(fragment))
        return False
    modes = read_modes(fragment)
    active = CONFIG_BRIDGE["analyses"].get(CONFIG_BRIDGE["active_analysis"],
                                           {})
    spectrum = active.get("solver_command") == "COMB_SISM_MODAL"
    # Akoestiek harmonisch: de <mode>-blokken zijn frequenties van de
    # respons, geen eigenmodes (bridge_acoustic.build_acoustic_harm).
    # Idem de harmonische respons van een constructie (bridge_harmonic).
    harmonic = (active.get("solver_command") == "DYNA_VIBRA" and
                (bridge_acoustic.is_acoustic(active) or
                 bridge_harmonic.is_harmonic(active)))
    vibro = bridge_vibroacoustic.is_vibroacoustic(active)
    if CONFIG_BRIDGE.get("mecway_solve_first", False) and spectrum:
        # Mecway rekent alleen de modes; de maxima van het spectrum zijn
        # niet met een Mecway-oplossing te vergelijken.
        log("INFO: Spectrumanalyse: geen vergelijking met de Mecway-solve "
            "(Mecway heeft geen spectrumanalyse).")
    elif CONFIG_BRIDGE.get("mecway_solve_first", False) and harmonic:
        log("INFO: Harmonische analyse: Mecway heeft geen harmonische "
            "analyse; geen vergelijking met de Mecway-solve.")
    elif CONFIG_BRIDGE.get("mecway_solve_first", False) and vibro:
        # Mecway rekent een fluidum zonder E als vaste stof met E = 0
        # (headless gezien: modes van 1e-7 Hz); niet vergelijkbaar.
        log("INFO: Vibro-akoestiek: Mecway heeft geen gekoppelde analyse; "
            "geen vergelijking met de Mecway-solve.")
    elif CONFIG_BRIDGE.get("mecway_solve_first", False):
        if modes:
            # Trillings-/knikvormen hebben een willekeurig teken en zijn bij
            # meervoudige modes niet uniek: alleen de waarden vergelijken.
            # Complexe modes: Mecway rekent zonder demping, dus met f_n =
            # |s| / 2 pi vergelijken (bridge_modal_damping).
            summary = read_mode_summary(os.path.join(
                work_dir_path(), run_name(".mess")))
            undamped = [(m, k, summary.get(m, {}).get("FREQ_NAT", v))
                        for m, k, v in modes]
            if undamped != modes:
                log(tr("INFO: Complexe modes: vergelijking met Mecway (zonder "
                       "demping) op f_n = f_d / sqrt(1 - zeta^2).",
                       "INFO: Complex modes: comparison with Mecway (without "
                       "damping) on f_n = f_d / sqrt(1 - zeta^2)."))
            # Complexe akoestische modes (impedantie): Mecway rekent hetzelfde
            # probleem, maar de nummers lopen door de 0-Hz-modes niet gelijk
            # (aster_acoustic_complex): op de dichtstbijzijnde frequentie.
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
                                configuration)
    if not ok:
        log(tr("ERROR: Resultaten niet in de .liml gezet: {0}",
               "ERROR: Results not written into the .liml: {0}").format(
                   reason))
        return False
    log("SUCCESS: Resultaten in '{0}' gezet (vorige versie: .bak); model "
        "opnieuw geopend.".format(active_liml))
    # Het resultaatbestand blijft staan: met de knop Resultaten... zijn de
    # resultaten later opnieuw in te laden, ook nadat ze uit de .liml zijn
    # verwijderd (kleine .liml).
    log("INFO: Resultaatbestand (opnieuw in te laden met "
        "de knop Resultaten...): {0}".format(fragment))
    if harmonic:
        report = (bridge_acoustic.report_harmonic
                  if bridge_acoustic.is_acoustic(active)
                  else bridge_vibroacoustic_harm.report_harmonic
                  if bridge_vibroacoustic_harm.is_vibro_harm(active)
                  else bridge_harmonic.report_harmonic)
        _notify(u"\n".join(report(work_dir_path(), modes)))
    elif modes:
        _report_modes(modes, extra=bridge_vibroacoustic.report_lines(
            work_dir_path()) if vibro else None, in_mecway=True)
    else:
        # Respons op modale basis (bridge_dyna_modal): de resultaten zijn
        # tijdstappen; de gebruikte modes staan als BRIDGE_MODE in de .mess.
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
        if spectrum:
            # Responsspectrum (bridge_spectrum): effectieve massa per
            # richting, missing mass en de totale reactie.
            import bridge_spectrum
            lines = bridge_spectrum.report_summary(
                os.path.join(work_dir_path(), run_name(".mess")),
                CONFIG_BRIDGE["analyses"].get(
                    CONFIG_BRIDGE["active_analysis"], {}))
            if lines:
                _notify(u"\n".join(lines))
    mw.open(active_liml)
    if configuration:
        # De configuratie met de nieuwe resultaten tonen (API:
        # mw.set_active_configuration).
        try:
            mw.set_active_configuration(configuration)
        except Exception as e:
            log(tr("WARNING: Configuratie '{0}' niet actief gemaakt: {1}",
                   "WARNING: Configuration '{0}' not made active: "
                   "{1}").format(configuration, e))
    return True


_MODES_SHOWN = 20     # zoveel modes in het statusvak; alle in de log


def _report_modes(modes, extra=None, in_mecway=False):
    """
    Frequenties (met effectieve massa) of kniklastfactoren in de log en
    het statusvak. modes: read_modes() van het resultaatbestand; de
    effectieve massa komt uit de BRIDGE_MODE-regels in de .mess
    (aster_results_export.print_modes). extra: regels die achteraan in het
    statusvak komen (vibro-akoestiek: bridge_vibroacoustic.report_lines,
    al gelogd). in_mecway: de modes zelf staan in Mecway (niet de modale
    basis van een respons); dan staat de effectieve massa ook als Mecway-
    variabele per mode in het resultaat (aster_results_export, S12).
    """
    # %-opmaak: "{0:.6g}".format() volgt in IronPython de Windows-
    # landinstelling (komma; gezien, zie bridge_gui._float_text).
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
                # Complexe modes (bridge_modal_damping): value = f_d
                line = tr(u"Mode {0}: {1} Hz gedempt (zeta {2}, f_n {3} Hz)",
                          u"Mode {0}: {1} Hz damped (zeta {2}, f_n {3} "
                          u"Hz)").format(
                              mid, "%.6g" % value, "%.4g" % zeta,
                              "%.6g" % summary[mid].get("FREQ_NAT", value))
            decay = summary.get(mid, {}).get("DECAY")
            if decay is not None and zeta is None:
                # Complexe akoestische modes (impedantie,
                # aster_acoustic_complex): decay rate, nagalmtijd, Q
                line += tr(u", decay rate {0} 1/s", u", decay rate {0} 1/s"
                           ).format("%.6g" % decay)
                if decay > 0.0:
                    line += tr(u" (T60 {0} s, Q {1})", u" (T60 {0} s, Q {1})"
                               ).format("%.4g" % summary[mid].get("T60", 0.0),
                                        "%.4g" % summary[mid].get("Q", 0.0))
            fractions = [summary.get(mid, {}).get(k) for k in (
                "MASS_EFFE_UN_DX", "MASS_EFFE_UN_DY", "MASS_EFFE_UN_DZ")]
            # Rotaties om de globale assen door de oorsprong (zoals Mecway;
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
            # Cyclische symmetrie (aster_cyclic): aantal nodal diameters
            nd = summary.get(mid, {}).get("ND")
            if nd is not None and nd >= 0:
                line += u" (ND {0})".format(int(nd))
        log(u"INFO: " + line)
        lines.append(line)
    if not buckling and any(summary.get(m, {}).get("ND") is not None
                            for m, _k, _v in modes):
        # Hele wiel of alleen de sector (aster_cyclic.collect, BRIDGE_CYCL)
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
        # aster_acoustic_complex (impedantie, docs/Akoestiek.md par. 3.3)
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
        # Noemers van de fracties (R^T M R) en het zwaartepunt: zo kan de
        # gebruiker de rotaties om de oorsprong duiden.
        cog = u"{0}".format(mass.get("ZWP", "?"))
        try:
            c = [float(v) for v in cog.split(",")]
            big = max([abs(v) for v in c] + [1.0e-30])
            cog = u", ".join("%.6g" % (v if abs(v) > 1.0e-9 * big else 0.0)
                             for v in c)
        except ValueError:
            pass
        log(u"INFO: Massa {0} kg, zwaartepunt ({1}) m; traagheidsmoment om "
            u"de assen door de oorsprong X/Y/Z {2}/{3}/{4} kg.m2, door het "
            u"zwaartepunt {5}/{6}/{7} kg.m2.".format(
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
        # Negatieve omega^2: K + Kg niet positief (modaal met voorspanning,
        # bridge_to_aster._prestress_plan). Starre modes van een vrij
        # model komen op ~ -1e-4 Hz (numeriek nul), vandaar de grens.
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
        # Holtemodes met harde wanden: mode 1 is de constante druk
        # (bridge_acoustic.py), geen fout.
        log(u"INFO: Mode 1 heeft ~0 Hz: constante druk (harde wanden "
            u"zonder drukknoop), zoals in Mecway.")
    elif not buckling and modes and modes[0][2] < 1.0e-2:
        log(tr(u"WARNING: Mode 1 heeft ~0 Hz: een starre-lichaamsbeweging "
               u"of mechanisme (te weinig opleggingen).",
               u"WARNING: Mode 1 has ~0 Hz: a rigid body motion or "
               u"mechanism (too few supports)."))
    _notify(u"\n".join(lines + list(extra or [])))


def _report_error_estimate():
    """
    Globale relatieve fout van de foutschatter (CALC_ERREUR ERME, zie
    bridge_to_aster._error_estimator_block) in de log en het statusvak,
    gelezen uit het blok dat Code-Aster in de .mess zet
    (read_error_summary). Niets als de schatter niet gedraaid heeft.
    Waarden: docs/Foutschatter.md (interpretatie).
    """
    summary = read_error_summary(os.path.join(work_dir_path(),
                                              run_name(".mess")))
    if not summary:
        return
    s = summary[-1]
    # %-opmaak: "{0:.3g}".format() volgt in IronPython de Windows-
    # landinstelling (zie _report_modes).
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


# Adaptieve verfijning (bridge_adapt): model_data en analyse van de laatste
# run, en de lussen van de lopende reeks (main() maakt history leeg).
_LAST = {}
_ADAPT = {"history": []}


def _adapt_step():
    """
    Na een geslaagde run: adaptieve verfijning (instelling adapt_refine,
    lineair statisch met foutschatter; docs/Foutschatter.md par. 6).
    bridge_adapt.after_run beslist op de globale fout (.mess) en de fout
    per element (resultaatbestand); bij verfijnen eerst een kopie van het
    oorspronkelijke model in de werkmap (eerste lus), dan mw.refine_x2 en
    mw.save(). Returns True als het model verfijnd is (nog een run).
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
        # Mecway's verfijning is via de API niet terug te draaien: het
        # oorspronkelijke model (met zijn resultaten) blijft als kopie.
        backup = os.path.join(work_dir, run_name("_voor_verfijning.liml"))
        try:
            shutil.copy(liml, backup)
            log(u"INFO: Adaptieve verfijning: oorspronkelijk model bewaard "
                u"als {0}.".format(backup))
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


# Grens voor de melding "mesh is grof" (globale relatieve fout in %); zie
# docs/Foutschatter.md (interpretatie).
_ERROR_COARSE_PCT = 20

# CRIT_STAB bij grote verplaatsingen: "dicht bij knik" als |lambda| onder
# deze fractie van de eerste |lambda| komt (keuze van de bridge; NK-04:
# 0,7% vlak voor het grenspunt).
_CRIT_NEAR = 0.05


def _report_stability():
    """
    Niet-lineaire knik (docs/Modaal_en_knik.md par. 5) in de log en het
    statusvak: de imperfectie (knikvorm, kniklastfactor, amplitude) en het
    stabiliteitscriterium CRIT_STAB per stap, met een melding als knik
    bereikt is. Betekenis van lambda: bridge_to_aster._crit_stab_kind.
    Niets als beide uit stonden.
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
            log(u"INFO: CRIT_STAB t = %.6g: kritische lastfactor %.6g" %
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
            log(u"INFO: CRIT_STAB t = %.6g: stabiliteitscriterium %.6g "
                u"(< 0 stabiel, 0 = knik)" % (t, lam))
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
# MELDINGEN EN HOOFDVENSTER
# ==========================================
# Meldingen van een run of een resultaatactie. Met het hoofdvenster
# (WinForms) komen ze in het statusvak; zonder (mw.input-terugval) als
# mw.message.
_NOTES = {"list": [], "popup": True}


def _notify(text):
    _NOTES["list"].append(u"{0}".format(text))
    if _NOTES["popup"]:
        mw.message(text)


def _status_text(ok, what):
    """Tekst voor het statusvak na een run of resultaatactie."""
    head = (tr(u"{0}: klaar.", u"{0}: done.") if ok else
            tr(u"{0}: gestopt (zie de meldingen hieronder en {1}).",
               u"{0}: stopped (see the messages below and {1}).")).format(
                   what, log_file_name())
    return u"\n\n".join([head] + _NOTES["list"])


def _results_action():
    """
    Knop Resultaten...: een eerdere run inladen of de resultaten uit het
    open model halen (kleine .liml). Zie bridge_results_liml en
    docs/Handleiding.md par. 5.1. Returns (ok, tekst voor het statusvak).
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
    mw.save()
    liml = mw.file_name()
    if choice["action"] == "strip":
        ok, reason = strip_results(liml)
        if not ok:
            return False, reason
        log("INFO: Resultaten uit '{0}' verwijderd.".format(liml))
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
    ok, reason = splice_results(liml, path, liml, configuration)
    if not ok:
        return False, tr("Resultaten niet ingeladen: {0}",
                         "Results not loaded: {0}").format(reason)
    log("SUCCESS: Resultaten '{0}' in '{1}' gezet.".format(path, liml))
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
    Het hoofdvenster blijft terugkomen tot de gebruiker op Sluiten klikt:
    Starten doet een run, Resultaten... laadt of verwijdert resultaten; het
    convergentiescherm en de documentatie werken in het venster zelf
    (bridge_gui). Zonder WinForms (mw.input-terugval): een run.
    """
    status = u""
    while True:
        # Buiten een run logt de bridge in bridge_log.txt (niet in het log
        # van de vorige run).
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
            # Adaptieve verfijning: verfijnen en opnieuw rekenen zolang
            # bridge_adapt dat zegt (elke run vraagt weer om OK na
            # Code-Aster, run_AsterSolver).
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
# Mecway voert dit script direct uit; main() wordt hier aangeroepen.
# ==========================================
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
