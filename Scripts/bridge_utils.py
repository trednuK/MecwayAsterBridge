# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_utils.py
# Gedeeld hulpbestand: configuratie, logging en eenhedenconversie.
# Compatibel met IronPython 2.7.9 (Mecway scripting engine).
#
# Plaats in module-architectuur:
#   - Wordt geimporteerd door ALLE andere bridge_*-modules.
#   - Bevat geen import-afhankelijkheden naar andere bridge_*-modules,
#     om cirkelimporten te vermijden.

import io
import os
import re
import math
from datetime import datetime


# Versie van de bridge (startscherm, kop van het log, CHANGELOG.md). Staat
# bewust buiten CONFIG_BRIDGE: het startscherm herschrijft alleen dat blok.
BRIDGE_VERSION = "V2026.1"

# Geteste versies (bridge_version.py): een andere versie geeft alleen een
# WARNING, de run gaat door. Mecway: het attribuut version van <liml>;
# Code-Aster: major.minor. Bijwerken na een geslaagde regressie, zie
# docs/Na_een_update.md.
TESTED_MECWAY_VERSIONS = ("33", "34")
TESTED_ASTER_VERSIONS = ("17.4",)


# ==========================================
# CONFIGURATIE
# ==========================================
CONFIG_BRIDGE = {
    # --- Installatie / project (analyse-onafhankelijk) ---

    # Taal van startscherm, meldingen, WARNING/ERROR-logregels en het
    # convergentiescherm: "nl" (Nederlands) of "en" (Engels). Zie tr().
    "language":        "en",

    # Pad naar de run_aster.bat launcher van Code-Aster. Omgevingsvariabelen
    # (%LOCALAPPDATA%) en ~ worden bij gebruik ingevuld (exe_aster_path()).
    # Standaard: de plek waar het Windows-pakket (MSI) Code-Aster 17.4
    # installeert.
    "exe_aster":       r"%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat",

    # Werkmap: hier komen per run <model>_<run_id>.comm, .export, .mess,
    # het resultaatbestand, het log etc. (run_name). Leeg ("") = de map
    # WorkDir naast de map Scripts (work_dir_path()); omgevingsvariabelen
    # en ~ worden ingevuld.
    "work_dir":        "",

    # Aantal CPU-kernen (threads) voor Code-Aster (ncpus=1 = geen parallellisme)
    "ncpus":           1,
    # Eerst een Mecway-solve uitvoeren als controle op modelfouten
    # (mw.solve(); de Mecway-API documenteert geen returnwaarde).
    "mecway_solve_first": False,
    # Resultaten naar Mecway: "liml" = Code-Aster schrijft Mecway's eigen
    # resultaatformaat (alle tijdstappen, klein bestand) en de bridge opent
    # de .liml opnieuw; "tabel" = POST_RELEVE_T-tabellen + set_variable()
    # (alleen knoopwaarden, alleen bestaande Mecway-tijdstappen).
    "result_route":    "liml",
    # Convergentie- en meldingenscherm (aster_convergence_monitor.py, apart
    # venster) openen zodra Code-Aster start; bij een lineaire analyse de
    # statistiek van de lineaire oplosser, de meldingen en de diagnose.
    "convergence_monitor": True,
    # Ook een MED-bestand (<model>_<run_id>.rmed) schrijven voor
    # ParaView/Salome. Mecway gebruikt het niet; het kan honderden MB worden.
    "med_export":      False,

    # --- Elementformulering (geldt voor alle analyses) ---
    # Hex8-volume-elementen: "3D" (volledig geintegreerd) of "3D_SI"
    # (onderintegratie; alleen als een elset uitsluitend hex8 heeft, niet
    # bij een expliciet schema). Let op: 3D_SI geeft met 1 element over de
    # dikte ~0 buigspanning (KNOWN_BUGS 1). "LINE_QUAD": Code-Aster maakt
    # alle lineaire volume-elementen kwadratisch (alleen bij uitsluitend
    # volume-elementen, niet expliciet).
    "elem_hex8":       "3D",
    # Lineaire schalen (tri3/quad4): "DKT" (Kirchhoff, dun) of "DST"
    # (Mindlin, met dwarskracht). DST alleen bij MECA_STATIQUE (niet-lineair
    # niet in Code-Aster, dan DKT); kwadratische schalen blijven COQUE_3D.
    # "COQUE_3D": lineaire schalen eerst kwadratisch (LINE_QUAD + QUAD8_9).
    "elem_shell":      "DKT",
    # Balken (line2): "POU_D_E" (Euler, zoals Mecway) of "POU_D_T"
    # (Timoshenko; AY/AZ voor algemene doorsneden: bridge_from_liml.py).
    "elem_beam":       "POU_D_E",

    # LET OP: de waarden in dit CONFIG_BRIDGE-blok worden door het startscherm
    # (bridge_gui.py) regel-voor-regel herschreven. Houd per sleutel het
    # patroon  "sleutel": waarde,  aan (een sleutel per regel, komma erachter;
    # alleen lijsten mogen over meerdere regels lopen).

    # --- Analyse-selectie ---
    # Welke analyse uit "analyses" hieronder wordt gebruikt voor deze run.
    # "auto": volg het analysetype van het Mecway-model (zie
    # MECWAY_ANALYSIS_TYPES onder dit blok); de keuze geldt alleen voor die run.
    "active_analysis": "auto",

    # --- Registry van ondersteunde analyses ---
    # Template per analyse ("template"): een bestandsnaam staat in de map
    # van deze scripts (Scripts/, template_path()); een absoluut pad mag
    # ook (eigen template elders).
    # Eén template per analysetype (MECA_STATIQUE, STAT_NON_LINE, ...)
    # omdat solver-aanroepen fundamenteel verschillen in structuur, niet alleen
    # in parameters.
    "analyses": {
        "lin_static_3d": {
            # .comm-template met placeholders voor de generator in bridge_to_aster.py
            "template":       "AsterTemplate_MecaStatique.comm",
            "solver_command": "MECA_STATIQUE",
            # Resultaatvelden die geextraheerd moeten worden.
            # Namen verwijzen naar entries in RESULT_FIELD_SPECS in bridge_from_aster.py.
            # Onbekende namen worden overgeslagen met een log-waarschuwing.
            "fields":         ["displacements", "stresses", "vonmises", "reactions"],
            # study.export: tijdslimiet [s] en geheugenlimiet [MB] voor run_aster.
            "time_limit":     600,
            "memory_limit":   2048,
            # MUMPS NPREC: toegestane verloren decimalen (Code-Aster-default 8,
            # ook hier; -1 = singulariteitscontrole uit, RESI_RELA controleert
            # dan het residu).
            "solver_nprec":   8,
            # Lineaire oplosser (bridge_to_aster._build_lin_solveur_ref):
            # "MUMPS" (direct, standaard) of "GCPC" (iteratief, geconjugeerde
            # gradient met PRE_COND='LDLT_INC'; residu per iteratie in het
            # convergentiescherm). PETSC zit niet in de Windows-versie.
            "lin_solver":     "MUMPS",
            # SOLVEUR RESI_RELA: MUMPS = grens voor de geschatte relatieve
            # fout op de oplossing; GCPC = convergentiecriterium ||r||/||f||.
            "lin_solver_resi": 1.0e-6,
            # Foutschatter (CALC_ERREUR ERME, residu-schatter, alleen
            # volume-elementen): geschatte discretisatiefout per element en
            # knoop naar Mecway (errorestimate*) en de globale relatieve
            # fout in de log; zie docs/Foutschatter.md.
            "error_estimator": True,
            # Breukmechanica (SCHEUR_-selecties, bridge_fracture.py,
            # docs/Breukmechanica.md): binnen- en buitenstraal [m] van het
            # theta-veld van CALC_G; beide 0 = automatisch (Code-Aster).
            # Gladmaken langs het front: "LINEAIRE" (Lagrange, per knoop)
            # of "LEGENDRE" (polynoom van fracture_legendre_degree).
            "fracture_r_inf": 0.0,
            "fracture_r_sup": 0.0,
            "fracture_smoothing": "LINEAIRE",
            "fracture_legendre_degree": 5,
            # Adaptieve verfijning (bridge_adapt.py, docs/Foutschatter.md
            # par. 6): na de run de elementen met de grootste fout in
            # Mecway verfijnen (mw.refine_x2) en opnieuw rekenen, tot de
            # globale relatieve fout [%] onder het doel is of een grens
            # (lussen, elementen) bereikt is. adapt_select: dorfler / fraction
            # / factor met adapt_fraction als waarde; adapt_neighbours:
            # ook de elementen die een knoop met de keuze delen.
            "adapt_refine":       False,
            "adapt_target_error": 2.0,
            "adapt_max_loops":    5,
            "adapt_select":       "dorfler",
            "adapt_fraction":     0.5,
            "adapt_neighbours":   False,
            "adapt_max_elements": 200000,
        },
        "nonlin_static_3d": {
            # .comm-template voor STAT_NON_LINE
            "template":       "AsterTemplate_StatNonLine.comm",
            "solver_command": "STAT_NON_LINE",
            "fields":         ["displacements", "stresses", "vonmises",
                               "reactions", "plastic_strain",
                               "plastic_strain_eq"],
            # Tunables voor STAT_NON_LINE.
            # substeps_per_interval: aantal substeps per Mecway-tijdsstap.
            #   Hoger = robuustere convergentie maar langere runtime.
            # newton_max_iter:       maximum Newton-iteraties per substep.
            # convergence_resi_rela: relatieve residu voor convergentie.
            # default_time_end:      gebruikt als geen tijds-belasting bestaat
            #                        maar STAT_NON_LINE toch gewenst is.
            "substeps_per_interval": 10,
            "newton_max_iter":       20,
            "convergence_resi_rela": 1.0e-5,
            # Convergentiecriterium (CONVERGENCE, U4.51.03): "RELA" =
            # RESI_GLOB_RELA (residu / externe krachten, Code-Aster-standaard)
            # of "MAXI" = RESI_GLOB_MAXI (grootste restkracht in N,
            # convergence_resi_maxi). MAXI voor een opgelegde beweging zonder
            # weerstand (externe krachten ~0, KNOWN_BUGS 44). "RELA_OF_MAXI"
            # = beide met VERIF='AU_MOINS_UN': een van beide volstaat.
            "convergence_criterion": "RELA",
            "convergence_resi_maxi": 1.0e-3,
            # Contact (DEFI_CONTACT CONTINUE, per zone): "STANDARD" =
            # Lagrange, geen penetratie; "PENALISATION" = veer met Mecway's
            # normalstiffness (COEF_PENA_CONT, Pa/m) en bij wrijving
            # tangentialstiffness (COEF_PENA_FROT), zoals Mecway/CCX.
            "contact_algo":          "STANDARD",
            "default_time_end":      1.0,
            # Rekdefinitie van Mecway's <hardeningcurve strain="...">.
            # Code-Aster TRACTION verwacht TOTALE rek en geen punt met
            # abscis nul (U4.43.01 par. 5.1.1); bridge_to_aster.py rekent om.
            #   "plastic" : strain = plastische rek  (EPSI = eps_p + sigma/E)
            #   "total"   : strain = totale rek      (beginpunt (0, 0) vervalt)
            #   "auto"    : afgeleid uit het eerste punt; (0, 0) of rek > 0
            #               -> total, (0, sigma>0) -> plastic + WARNING.
            # Mecway leest de curve als totale rek (headless getest met
            # Mecway/CCX bij de docs-review; geen officiele documentatie).
            "plastic_strain_definition": "auto",
            # study.export: tijdslimiet [s] en geheugenlimiet [MB] voor run_aster.
            "time_limit":            1800,
            "memory_limit":          4096,
            # COMPORTEMENT DEFORMATION (U4.51.11 par. 4.6): "PETIT",
            # "GDEF_LOG", "GREEN_LAGRANGE", "GROT_GDEP", "PETIT_REAC",
            # "SIMO_MIEHE". Standaard "GROT_GDEP": Mecway's niet-lineaire
            # statica (L30) rekent altijd geometrisch niet-lineair; de
            # dynamische analyses volgen dat (keuze, voor dynamica NIET
            # geverifieerd). De bridge kiest per elementtype de toegestane vorm
            # (bridge_to_aster._deformation_for: volume GREEN_LAGRANGE/
            # GDEF_LOG, COQUE_3D GROT_GDEP; balken en DKT/DST blijven
            # geometrisch lineair, met een WARNING).
            "deformation":           "GROT_GDEP",
            # NEWTON REAC_ITER (U4.51.03): frequentie van herberekening van de
            # tangente matrix t.o.v. de Newton-iteraties; 0 = niet herberekend
            # binnen de tijdstap. Code-Aster-default is 1.
            "newton_reac_iter":      1,
            # MUMPS NPREC (zie lin_static_3d).
            "solver_nprec":          8,
            # Bezwijken van elementen (bridge_failure.py): elementen met een
            # plastische rek boven de grens krijgen E x stiffness_factor en
            # spanning nul. Grens per materiaal: #ASTER-BEZWIJKEN, PLAS_TAB
            # Eps_p_max of failure_plastic_strain (> 0: alle plastische
            # materialen zonder eigen grens; 0 = uit).
            "element_failure":       True,
            "failure_plastic_strain": 0.0,
            "failure_stiffness_factor": 1.0e-6,
            # Niet-lineaire knik (bridge_to_aster._crit_stab_block,
            # _imperfection_block; docs/Modaal_en_knik.md par. 5).
            # crit_stab: CRIT_STAB in STAT_NON_LINE, per stap de kritische
            # lastfactor van de huidige toestand (log en statusvak).
            # imperfection_amplitude: 0 = geen imperfectie; anders eerst
            # lineaire knik en het mesh vervormen met knikvorm
            # imperfection_mode (grootste verplaatsing = amplitude), in m
            # of (imperfection_unit "L") als fractie van de grootste
            # afmeting van het model.
            "crit_stab":             False,
            "imperfection_amplitude": 0.0,
            "imperfection_mode":     1,
            "imperfection_unit":     "m",
        },
        "dyna_impl_3d": {
            # Niet-lineaire dynamica, impliciet (Mecway D31). Zelfde
            # materialen, lasten en contact als nonlin_static_3d.
            "template":       "AsterTemplate_DynaNonLine.comm",
            "solver_command": "DYNA_NON_LINE",
            "fields":         ["displacements", "stresses", "vonmises",
                               "velocities", "reactions", "plastic_strain_eq"],
            # SCHEMA_TEMPS (U4.53.01): "HHT" (numerieke demping via
            # hht_alpha, -0.3..0) of "NEWMARK" (gemiddelde versnelling).
            "schema":                "HHT",
            "hht_alpha":             -0.1,
            # Rekenstappen per uitvoerinterval van Mecway's <timesteps>;
            # bij divergentie deelt Code-Aster de stap in 4 (tot 6 niveaus).
            "substeps_per_output":   1,
            "newton_max_iter":       20,
            "convergence_resi_rela": 1.0e-5,
            # Zie nonlin_static_3d.
            "convergence_criterion": "RELA",
            "convergence_resi_maxi": 1.0e-3,
            "contact_algo":          "STANDARD",
            "newton_reac_iter":      1,
            # ENERGIE=_F() (U4.53.01 par. 3.22): energiebalans per stap in
            # study.mess (convergentiescherm). Niet met contact CONTINUE
            # (MECANONLINE5_15); dan laat de bridge het weg.
            "energy_balance":        False,
            "default_time_end":      1.0,
            "plastic_strain_definition": "auto",
            # Zie nonlin_static_3d.
            "deformation":           "GROT_GDEP",
            "time_limit":            7200,
            "memory_limit":          4096,
            "solver_nprec":          8,
            # Bezwijken van elementen: zie nonlin_static_3d (controle op de
            # uitvoertijden).
            "element_failure":       True,
            "failure_plastic_strain": 0.0,
            "failure_stiffness_factor": 1.0e-6,
        },
        "dyna_expl_3d": {
            # Niet-lineaire dynamica, expliciet (DIFF_CENT). Code-Aster kent
            # geen mass scaling: de stap volgt uit het kleinste element.
            "template":       "AsterTemplate_DynaNonLine.comm",
            "solver_command": "DYNA_NON_LINE",
            "fields":         ["displacements", "stresses", "vonmises",
                               "velocities", "reactions", "plastic_strain_eq"],
            "schema":                "DIFF_CENT",
            # Tijdstap = factor * geschatte kritieke tijdstap (STOP_CFL
            # controleert de echte grens).
            "explicit_dt_factor":    0.5,
            # Zie nonlin_static_3d.
            "contact_algo":          "STANDARD",
            "default_time_end":      1.0,
            "plastic_strain_definition": "auto",
            # Zie nonlin_static_3d.
            "deformation":           "GROT_GDEP",
            "time_limit":            7200,
            "memory_limit":          4096,
            "solver_nprec":          8,
            # Bezwijken van elementen: zie nonlin_static_3d (controle op de
            # uitvoertijden).
            "element_failure":       True,
            "failure_plastic_strain": 0.0,
            "failure_stiffness_factor": 1.0e-6,
        },
        "ther_3d": {
            # Thermisch, stationair (Mecway T30) of transient (T31); de
            # bridge kiest THER_LINEAIRE, of THER_NON_LINE bij straling of
            # convectie/straling op schaalvlakken (bridge_thermal.py).
            "template":       "AsterTemplate_Thermique.comm",
            "solver_command": "THER_LINEAIRE",
            "fields":         ["temperature", "heat_flux"],
            # SCHEMA_TEMPS THETA (transient; 0 = expliciet, 1 = impliciet
            # Euler, Code-Aster-default 0.57; catalogus ther_lineaire.py).
            "theta":                 0.57,
            # Alleen THER_NON_LINE: Newton-iteraties, residu, REAC_ITER.
            "newton_max_iter":       20,
            "convergence_resi_rela": 1.0e-6,
            "newton_reac_iter":      1,
            # Alleen de keten thermisch -> mechanisch (T31 met Thermal
            # stress, bridge_thermomech.py): COMPORTEMENT DEFORMATION van
            # STAT_NON_LINE (lassen: kleine rekken, PETIT) en de rekdefinitie
            # van een hardingscurve (zie nonlin_static_3d). Newton en
            # convergentie: de instellingen hierboven.
            "deformation":           "PETIT",
            "plastic_strain_definition": "auto",
            "time_limit":            1800,
            "memory_limit":          4096,
            "solver_nprec":          8,
        },
        "modal_3d": {
            # Modale analyse (Mecway V30): eigenfrequenties en
            # trillingsvormen met CALC_MODES (U4.52.02); zie
            # bridge_to_aster._build_modal en docs/Modaal_en_knik.md.
            "template":       "AsterTemplate_CalcModes.comm",
            "solver_command": "CALC_MODES",
            # CALC_MODES TYPE_RESU: "DYNAMIQUE" (trillingen).
            "type_resu":      "DYNAMIQUE",
            # Trillingsvormen (DEPL), zoals Mecway's eigen modale
            # oplossing; met "stresses"/"vonmises" ook spanningen per mode
            # (bridge_to_aster._modal_stress_fields); andere velden worden
            # genegeerd.
            "fields":         ["displacements"],
            # Aantal modes als het Mecway-model geen maxmode heeft
            # (<analysis type="V30" maxmode="..">).
            "modal_modes":    10,
            # Zoekfrequentie [Hz]: 0 = de laagste modes (OPTION
            # 'PLUS_PETITE'); > 0 = de modes het dichtst bij deze
            # frequentie (OPTION 'CENTRE'); < 0 = ook de laagste modes,
            # voor een model met een mechanisme (starre modes).
            "modal_shift_hz": 0.0,
            # Normering van de trillingsvormen (NORM_MODE NORME):
            # "MASS_GENE" = gegeneraliseerde massa 1, zoals Mecway;
            # "TRAN_ROTA" = grootste component 1 (Code-Aster-standaard).
            "modal_norm":     "MASS_GENE",
            # VERI_MODE SEUIL: grens voor de relatieve fout
            # ||K x - w^2 M x|| / ||K x|| per mode (Code-Aster-default 1e-6).
            "modal_tolerance": 1.0e-6,
            # Voorspanning door de belastingen (stress stiffening): True =
            # zoals Mecway (met belastingen eerst MECA_STATIQUE, dan de
            # modes met K + Kg); False = belastingen negeren (WARNING).
            "modal_prestress": True,
            # Complexe modes met demping (Rayleigh, dempers): False = reele
            # modes zonder demping, zoals Mecway; True = CALC_MODES met
            # MATR_AMOR (gedempte frequentie en zeta per mode,
            # bridge_modal_damping.py).
            "modal_complex":  False,
            # Cyclische symmetrie (bridge_cyclic.py, MODE_ITER_CYCL): aantal
            # sectormodes met vaste snijvlakken in de basis; 0 = automatisch
            # max(20, 4 x het aantal modes per nodal diameter).
            "cyclic_base_modes": 0,
            # Cyclische symmetrie: True = de modes op het hele wiel naar
            # Mecway (alle N sectoren, zoals Mecway's eigen oplossing;
            # DEFI_SQUELETTE + REST_SOUS_STRUC SQUELETTE); False = alleen
            # de sector.
            "cyclic_full_wheel": True,
            "time_limit":     900,
            "memory_limit":   2048,
            # MUMPS NPREC (zie lin_static_3d).
            "solver_nprec":   8,
        },
        "dyna_modal_3d": {
            # Respons op modale basis (Mecway D30 met Mode superposition):
            # CALC_MODES, PROJ_BASE, DYNA_VIBRA BASE_CALCUL='GENE' en
            # REST_GENE_PHYS; zie bridge_dyna_modal.py en
            # docs/Modaal_en_knik.md.
            "template":       "AsterTemplate_DynaVibra.comm",
            "solver_command": "DYNA_VIBRA",
            # Zoals Mecway's mode superposition: verplaatsingen, rotaties
            # en snelheden (geen versnellingen, geen reacties); spanningen
            # met CALC_CHAMP op de fysieke respons.
            "fields":         ["displacements", "velocities", "stresses",
                               "vonmises"],
            # Aantal modes als het Mecway-model geen maxmode heeft.
            "modal_modes":    10,
            # Rekenstappen per periode van de hoogste mode in de basis
            # (NEWMARK; Mecway rekent de modale vergelijkingen exact).
            "steps_per_period": 50,
            # Extra modale dempingsverhouding voor alle modes (bovenop
            # Mecway's Rayleigh-demping); 0 = alleen Mecway.
            "modal_damping":  0.0,
            # Statische correctie voor de weggelaten modes (MACRO_ELAS_MULT,
            # CORR_STAT); Mecway doet dat niet.
            "static_correction": False,
            "modal_tolerance": 1.0e-6,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "harmonic_3d": {
            # Harmonische respons in het frequentiedomein (Mecway heeft
            # geen harmonische analyse; een V30- of D30-model): CALC_MODES,
            # DYNA_VIBRA TYPE_CALCUL='HARM' op modale basis (GENE) of
            # direct (PHYS); zie bridge_harmonic.py en
            # docs/Respons_op_modale_basis.md. Zelf kiezen (niet 'auto').
            "template":       "AsterTemplate_Harmonisch.comm",
            "solver_command": "DYNA_VIBRA",
            # bridge_to_aster._build_dyna_modal stuurt deze analyse door
            # naar bridge_harmonic.build_harmonic.
            "type_calcul":    "HARM",
            # Per frequentie amplitude, fase, Re/Im (displacements); ook
            # velocities/accelerations (amplitude) en stresses/vonmises
            # (volume-elementen).
            "fields":         ["displacements", "accelerations", "stresses",
                               "vonmises"],
            # Aantal modes als het Mecway-model geen maxmode heeft.
            "modal_modes":    10,
            "modal_tolerance": 1.0e-6,
            # "GENE" = op modale basis (standaard); "PHYS" = direct op het
            # hele model (controle; Rayleigh en dempers, geen modal_damping).
            "harm_basis":     "GENE",
            # Frequenties [Hz]: harm_freq_count stappen van start tot eind
            # (spacing "lin" of "log"), of een lijst in harm_freq_list
            # (tekst, bijv. "5, 10, 20"; "0" = het bereik gebruiken).
            "harm_freq_start": 1.0,
            "harm_freq_end":  100.0,
            "harm_freq_count": 100,
            "harm_freq_spacing": "lin",
            "harm_freq_list": "0",
            # Extra frequenties per mode in het bereik, over de
            # halfwaardebreedte (DEFI_LIST_FREQ LARGEUR_3DB); 0 = geen.
            "harm_refine_points": 5,
            # Extra modale dempingsverhouding voor alle modes (bovenop
            # Mecway's Rayleigh-demping, alleen GENE).
            "modal_damping":  0.0,
            # Statische verrijking van de modale basis (GENE; zoals
            # DYNA_LINE ENRI_STAT='OUI'): de quasi-statische bijdrage van de
            # weggelaten modes telt mee.
            "static_correction": True,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "spectrum_3d": {
            # Responsspectrum (aardbeving, schok): CALC_MODES en
            # COMB_SISM_MODAL; het spectrum is een Mecway-gravity met een
            # tabel (of #ASTER-SPECTRE); zie bridge_spectrum.py en
            # docs/Spectrumanalyse.md.
            "template":       "AsterTemplate_Spectre.comm",
            "solver_command": "COMB_SISM_MODAL",
            # Maxima (zonder teken) naar Mecway, als een stap.
            "fields":         ["displacements", "accelerations", "stresses",
                               "vonmises", "reactions"],
            # Aantal modes als het Mecway-model geen maxmode heeft.
            "modal_modes":    20,
            "modal_tolerance": 1.0e-6,
            # Tabel van de gravity: periode [s] of frequentie [Hz].
            "spectrum_abscissa": "period",
            # Dempingsverhouding van elke mode (bovenop Mecway's Rayleigh).
            "spectrum_damping": 0.05,
            # Modale combinatie: CQC, SRSS of ABS.
            "modal_combination": "CQC",
            # Richtingscombinatie: SRSS, 100-30-30, 100-40-40 of ABS.
            "direction_combination": "SRSS",
            # Missing-mass-correctie (MODE_CORR met pseudo-modes).
            "missing_mass":   True,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "buckling_3d": {
            # Lineaire knik (Mecway B30): MECA_STATIQUE met de lasten,
            # geometrische stijfheid (RIGI_GEOM) en CALC_MODES
            # TYPE_RESU='MODE_FLAMB'; zie bridge_to_aster._build_modal.
            "template":       "AsterTemplate_CalcModes.comm",
            "solver_command": "CALC_MODES",
            "type_resu":      "MODE_FLAMB",
            # Alleen knikvormen (DEPL), zoals Mecway.
            "fields":         ["displacements"],
            # Aantal modes als het Mecway-model geen maxmode heeft.
            "modal_modes":    4,
            # Altijd de kleinste kniklastfactoren (OPTION 'PLUS_PETITE'),
            # zoals Mecway; 'CENTRE' rond een factor negeert Code-Aster 17.4
            # bij knik (bridge_to_aster._calc_modes_block).
            # Normering van de knikvormen (NORM_MODE NORME): "RIGI_GENE" =
            # gegeneraliseerde stijfheid 1, zoals Mecway.
            "modal_norm":     "RIGI_GENE",
            # VERI_MODE SEUIL (zie modal_3d).
            "modal_tolerance": 1.0e-6,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "acoustic_modes_3d": {
            # Akoestische holtemodes (Mecway A30, Acoustic Resonance 3D):
            # PHENOMENE='ACOUSTIQUE' en CALC_MODES; zie bridge_acoustic.py
            # en docs/Akoestiek.md. Resultaat: per mode het drukveld.
            "template":       "AsterTemplate_Akoestiek.comm",
            "solver_command": "CALC_MODES",
            # bridge_to_aster._build_modal stuurt deze analyse door naar
            # bridge_acoustic.build_acoustic_modes.
            "phenomene":      "ACOUSTIQUE",
            # Aantal modes als het Mecway-model geen maxmode heeft.
            "modal_modes":    10,
            # Zoekfrequentie [Hz]: 0 = de laagste modes (zonder drukknoop
            # kiest de bridge zelf een kleine negatieve zoekfrequentie).
            "modal_shift_hz": 0.0,
            # VERI_MODE SEUIL (zie modal_3d).
            "modal_tolerance": 1.0e-6,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "acoustic_harm_3d": {
            # Harmonisch drukveld (akoestiek) op een Mecway A30-model:
            # PHENOMENE='ACOUSTIQUE' en DYNA_VIBRA HARM; bron (BRON_ of
            # #ASTER-BRON), absorberende randen (ABSORBEREND_ of
            # impedance), microfoons (MICROFOON_); zie bridge_acoustic.py
            # en docs/Akoestiek.md. 'auto' kiest deze bij A30 met een bron.
            "template":       "AsterTemplate_AkoestiekHarm.comm",
            "solver_command": "DYNA_VIBRA",
            # bridge_to_aster._build_dyna_modal stuurt deze analyse door
            # naar bridge_acoustic.build_acoustic_harm.
            "phenomene":      "ACOUSTIQUE",
            # Frequenties [Hz]: harm_freq_count stappen van start tot eind
            # (spacing "lin" of "log"), of een lijst in harm_freq_list
            # (tekst, bijv. "100, 250, 500"; "0" = het bereik gebruiken).
            "harm_freq_start": 50.0,
            "harm_freq_end":  1000.0,
            "harm_freq_count": 20,
            "harm_freq_spacing": "lin",
            "harm_freq_list": "0",
            # Normaalsnelheid [m/s] van de BRON_-vlakken, de fluid in.
            "source_velocity": 0.001,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "vibroacoustic_modes_3d": {
            # Vibro-akoestiek: constructie + lucht/vloeistof gekoppeld
            # (Mecway V30 met een fluidum-onderdeel): 3D_FLUIDE, FLUI_STRU,
            # U_P_PHI en CALC_MODES BANDE; zie bridge_vibroacoustic.py en
            # docs/Akoestiek.md. 'auto' kiest deze bij V30 met een fluidum.
            "template":       "AsterTemplate_VibroAkoestiek.comm",
            "solver_command": "CALC_MODES",
            # bridge_to_aster._build_modal stuurt deze analyse door naar
            # bridge_vibroacoustic.build_vibroacoustic_modes.
            "vibroacoustic":  True,
            # Aantal modes als het Mecway-model geen maxmode heeft.
            "modal_modes":    10,
            # Ondergrens [Hz]: de modes erboven (U_P_PHI geeft valse modes
            # bij 0 Hz; starre modes en constante druk vallen eronder).
            "vibro_freq_min": 0.1,
            # VERI_MODE SEUIL (zie modal_3d).
            "modal_tolerance": 1.0e-6,
            "time_limit":     900,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
        "vibroacoustic_harm_3d": {
            # Vibro-akoestiek harmonisch: constructie + lucht/vloeistof per
            # frequentie (hetzelfde model als vibroacoustic_modes_3d) met
            # bronnen, absorberende randen (3D_FLUI_ABSO) en microfoons;
            # DYNA_VIBRA HARM PHYS; zie bridge_vibroacoustic_harm.py en
            # docs/Akoestiek.md. Zelf kiezen ('auto' blijft de modes).
            "template":       "AsterTemplate_VibroAkoestiekHarm.comm",
            "solver_command": "DYNA_VIBRA",
            # bridge_to_aster._build_dyna_modal stuurt deze analyse door
            # naar bridge_vibroacoustic_harm.build_vibroacoustic_harm.
            "vibroacoustic":  True,
            "type_calcul":    "HARM",
            # Constructie per frequentie (zoals harmonic_3d); de druk in het
            # fluidum gaat altijd mee.
            "fields":         ["displacements", "accelerations", "stresses",
                               "vonmises"],
            # Frequenties [Hz]: harm_freq_count stappen van start tot eind
            # (spacing "lin" of "log"), of een lijst in harm_freq_list
            # (tekst, bijv. "100, 250, 500"; "0" = het bereik gebruiken).
            "harm_freq_start": 20.0,
            "harm_freq_end":  500.0,
            "harm_freq_count": 50,
            "harm_freq_spacing": "lin",
            "harm_freq_list": "0",
            # Normaalsnelheid [m/s] van de BRON_-vlakken, de fluid in.
            "source_velocity": 0.001,
            # Amplitude [Pa] van de invallende golf op INVALLEND_-vlakken.
            "incident_pressure": 1.0,
            "time_limit":     1800,
            "memory_limit":   2048,
            "solver_nprec":   8,
        },
    },
}


# Mecway-analysetype (<analysis type="..."> in de .liml) -> analyse in
# CONFIG_BRIDGE["analyses"], voor active_analysis = "auto". Gezien in de
# testmodellen: S30 (statisch 3D), L30 (niet-lineair statisch 3D), D31
# (niet-lineair dynamisch 3D), T30 (thermisch stationair), T31 (thermisch
# transient; Mecway-voorbeelden FinConvection, OscillatingHeatFlow) en V30
# (frequentie/modaal 3D; Mecway-voorbeelden VibratingCantileverBeam e.a.)
# en B30 (lineaire knik 3D; voorbeelden BucklingBeam, BucklingPlate).
# D30 (lineaire Dynamic Response 3D, voorbeelden DynamicResponse en
# DampedVibratingStrip): met Mode superposition de respons op modale basis,
# zonder (Mecway: Newmark op het volledige model) de impliciete dynamica.
# Andere typen (2D, ...) hebben geen analyse in de bridge.
# Sleutel voor D30 met Mode superposition (geen eigen Mecway-type; ook de
# tekst in het startscherm).
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
    # A20 = 2D wordt niet vertaald)
    "A30": "acoustic_modes_3d",
}


def resolve_auto_analysis(mecway_type, mode_superposition=False):
    """
    Analyse-naam voor active_analysis = "auto". mode_superposition: D30
    met <analysis modesuperposition="true"> (model_data
    "mode_superposition").

    Returns
    -------
    str of None  None als het Mecway-analysetype niet ondersteund wordt
                 of de bijbehorende analyse niet in CONFIG_BRIDGE staat.
    """
    if mecway_type == "D30" and mode_superposition:
        mecway_type = D30_MODE_SUPERPOSITION
    name = MECWAY_ANALYSIS_TYPES.get(mecway_type)
    if name is None or name not in CONFIG_BRIDGE["analyses"]:
        return None
    return name


# Map van de bridge-scripts (en de .comm-templates).
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def expand_path(path):
    """Vul omgevingsvariabelen (%LOCALAPPDATA%, $HOME) en ~ in een pad in.
    Een onbekende variabele blijft staan (os.path.expandvars). Leeg of None:
    ""."""
    if not path:
        return ""
    return os.path.expanduser(os.path.expandvars(u"{0}".format(path).strip()))


def default_work_dir():
    """Standaardwerkmap bij work_dir "": WorkDir naast de map Scripts
    (in de repo: <repo>/WorkDir, gitignored)."""
    return os.path.join(os.path.dirname(SCRIPTS_DIR), "WorkDir")


def work_dir_path():
    """
    Werkmap van de bridge: CONFIG_BRIDGE["work_dir"] met ingevulde
    omgevingsvariabelen, of default_work_dir() als die instelling leeg is.
    Lees de werkmap altijd hiermee, niet rechtstreeks uit CONFIG_BRIDGE.
    """
    return expand_path(CONFIG_BRIDGE.get("work_dir")) or default_work_dir()


def exe_aster_path():
    """Pad naar run_aster.bat: CONFIG_BRIDGE["exe_aster"] met ingevulde
    omgevingsvariabelen (standaard %LOCALAPPDATA%\\code_aster\\...)."""
    return expand_path(CONFIG_BRIDGE.get("exe_aster"))


def template_path(template):
    """
    Volledig pad van een .comm-template uit CONFIG_BRIDGE["analyses"][..]
    ["template"]: een bestandsnaam (of relatief pad) hoort in SCRIPTS_DIR;
    een absoluut pad blijft staan. Bestaat een absoluut pad niet (bijv. een
    instelling van een andere pc of een oude repo-map), maar staat een
    template met dezelfde naam in SCRIPTS_DIR, dan wordt die gebruikt.
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
    """Geeft de CONFIG_BRIDGE-dict van de actieve analyse terug."""
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
    True als de actieve analyse de foutschatter aan heeft
    ("error_estimator") en MECA_STATIQUE is: alleen daar bouwt de bridge
    CALC_ERREUR (bridge_to_aster._error_estimator_block; andere analyses:
    WARNING in generate_AsterSolver_files). Gebruikt door bridge_mesh voor
    de vrije vlakken. options: de #ASTER-OPTIE-waarden van het model
    (model_data["aster_custom"]["options"]); een "error_estimator" daarin
    wint, met dezelfde ja/nee-woorden als bridge_custom.apply_options.
    Geen geldige actieve analyse: False.
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
    # geen of een ongeldige waarde (WARNING in bridge_custom.apply_options)
    return bool(analysis["error_estimator"])


# Ja/nee-woorden voor een #ASTER-OPTIE met een ja/nee-instelling (NL, EN,
# FR; kleine letters).
YES_WORDS = ("1", "true", "yes", "on", "ja", "aan", "waar", "oui", "vrai")
NO_WORDS = ("0", "false", "no", "off", "nee", "uit", "onwaar", "non", "faux")


def parse_yes_no(raw):
    """
    True of False voor een ja/nee-woord (YES_WORDS / NO_WORDS; hoofdletters,
    spaties en aanhalingstekens maken niet uit), anders None (ook voor None).
    Gedeeld door bridge_custom.apply_options (die bij None een WARNING geeft
    en de standaardwaarde houdt), bridge_adapt en error_estimator_requested.
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
# TAAL
# ==========================================
def tr(nl, en):
    """
    Tekst in de taal van CONFIG_BRIDGE["language"] ("en" = Engels, de standaard;
    "nl" = Nederlands). Beide teksten staan bij de aanroep, met dezelfde
    placeholders en hetzelfde "INFO|WARNING|ERROR|SUCCESS:"-voorvoegsel
    (bridge_run_aster en het convergentiescherm herkennen dat):
        log(tr("WARNING: Groep '{0}' is leeg.",
               "WARNING: Group '{0}' is empty.").format(name))
    De taal wordt bij elke aanroep gelezen; vaste teksten op moduleniveau
    bewaar je daarom als paar (nl, en) en vertaal je bij gebruik: tr(*paar).
    """
    return en if CONFIG_BRIDGE.get("language", "en") == "en" else nl


# ==========================================
# LOG FUNCTIONALITEIT
# ==========================================
# Logbestand van de lopende simulatie (set_run_log); buiten een run
# (startscherm, offline tests) bridge_log.txt.
_RUN_LOG = {"name": "bridge_log.txt", "id": None, "model": "model"}

# Achtervoegsel van het logbestand van een run: <model>_<run_id>_bridge_log.txt
LOG_SUFFIX = "_bridge_log.txt"


def model_stem(liml_path):
    """
    Naam van het Mecway-bestand zonder map en extensie, bruikbaar in
    bestandsnamen: tekens buiten A-Z, a-z, 0-9, '-' en '_' worden '_'
    (veilig in .export-regels en in de .comm; een spatie in de werkmap
    werkte in een test wel, in de naam NIET geverifieerd), zonder
    dubbele of afsluitende '_'. "Mijn Model (v2).liml" -> "Mijn_Model_v2".
    Leeg of None: "model".
    """
    stem = os.path.splitext(os.path.basename(liml_path or ""))[0]
    stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem or "model"


def set_run_log(run_id, model=None):
    """
    Start de bestandsnamen van een simulatie: run_id (tijdstempel) en model
    (naam van het Mecway-bestand, via model_stem). Het logbestand wordt
    <model>_<run_id>_bridge_log.txt, net als de andere bestanden van de run
    (run_name). run_id None: terug naar bridge_log.txt. Returns de
    bestandsnaam van het log.
    """
    _RUN_LOG["id"] = run_id
    stem = model_stem(model)
    # Windows-paden tot 259 tekens (MAX_PATH): gezien in een test met een
    # lange werkmap, waar het resultaatbestand (..._results.xml.tmp) niet
    # geschreven kon worden ([Errno 2]). Te lang: de modelnaam inkorten.
    room = (259 - len(os.path.join(work_dir_path(), "")) -
            len("_{0}{1}.tmp".format(run_id or "", _LONGEST_SUFFIX)))
    short = stem[:max(8, room)] if len(stem) > room else stem
    _RUN_LOG["model"] = short
    # Past het ook met de ingekorte naam niet: path_too_long() (main stopt).
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


# Langste achtervoegsel van een runbestand (bridge_to_aster.results_file,
# bridge_run_aster._monitor_log): bepaalt de ruimte voor de modelnaam.
_LONGEST_SUFFIX = "_monitor_log.txt"


def log_file_name():
    """Naam van het huidige logbestand in de werkmap."""
    return _RUN_LOG["name"]


def run_name(suffix):
    """
    Bestandsnaam (zonder map) van een uitvoerbestand van de lopende run:
    <model>_<run_id><suffix>, bijv. voor ProfielBuigen.liml run_name(".mess")
    -> ProfielBuigen_20261006_101500.mess. Zo hoort elk bestand in de werkmap
    zichtbaar bij een model en een run. Buiten een run (offline tests,
    set_run_log(None)): study<suffix>.
    """
    run_id = _RUN_LOG["id"]
    if run_id is None:
        return "study" + suffix
    return "{0}_{1}{2}".format(_RUN_LOG["model"], run_id, suffix)


# Algemene namen in meldingen en hints (bijv. "zie study.mess") ->
# de bestanden van de lopende run (run_names).
_GENERIC_NAMES = (("study.mess", ".mess"), ("study.comm", ".comm"),
                  ("study_console.txt", "_console.txt"))


def path_too_long():
    """True als werkmap + bestandsnaam van de run ook met een ingekorte
    modelnaam langer dan 259 tekens zou worden (set_run_log)."""
    return bool(_RUN_LOG.get("too_long"))


def run_names(text):
    """Vervang in een melding study.mess, study.comm en study_console.txt
    door de namen van de lopende run (ongewijzigd buiten een run). Alleen
    losse namen: een pad als C:\\Werk\\study.comm (bijv. een oud bestand
    dat wordt opgeruimd) blijft staan."""
    if _RUN_LOG["id"] is None:
        return text
    for generic, suffix in _GENERIC_NAMES:
        text = re.sub(r"(?<![\\/\w.])" + re.escape(generic),
                      run_name(suffix).replace("\\", "\\\\"), text)
    return text


def log(text):
    """Schrijf een tijdgestempelde logregel naar het logbestand van de
    run. Ontbreekt de werkmap (bijv. een verse installatie), dan wordt die
    aangemaakt; lukt schrijven niet, dan gaat de melding verloren in plaats
    van de actie te laten mislukken."""
    work_dir = work_dir_path()
    log_path  = os.path.join(work_dir, _RUN_LOG["name"])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if not os.path.isdir(work_dir):
            os.makedirs(work_dir)
        # io.open met UTF-8: meldingen uit study.mess bevatten Franse
        # accenten (bijv. "numéro"), die het gewone open() niet altijd
        # aankan.
        with io.open(log_path, "a", encoding="utf-8") as f:
            f.write(u"[{0}] {1}\n".format(timestamp, run_names(text)))
    except (IOError, OSError):
        pass


# ==========================================
# EENHEIDSCONVERSIE
#
# Code-Aster rekent zonder eenheden; de bridge levert alle waarden aan in
# SI-eenheden:
#   lengte           m      oppervlakte      m²      traagheid   m⁴
#   kracht           N      druk / E-modul   Pa      veerconst.  N/m
#   hoek             rad
#
# Mecway exporteert waarden met eenheidslabels (bijv. "210 GPa",
# "10000 mm⁴", "4231 N/m"). Vóór de regex-matching worden Unicode-
# superscripts (², ³, ⁴, ¹, ⁰) ASCII-cijfers, '°' wordt 'deg' en 'µ' wordt 'u'.
#
# Ondersteunde hoeveelheidstypen en conversies (eenheid hoofdletterongevoelig,
# behalve het voorvoegsel m/M: mN, mPa en mN/m zijn milli, MN, MPa en MN/m mega):
#   'length'           mm→×1e-3,  cm→×1e-2
#   'force'            kN→×1e3,   MN→×1e6,   mN→×1e-3
#   'pressure'         kPa→×1e3,  MPa→×1e6,  GPa→×1e9,  mPa→×1e-3
#   'angle'            deg / °→×(π/180)
#   'area'             mm2→×1e-6, cm2→×1e-4,  in2→×6.4516e-4
#   'inertia'          mm4→×1e-12, cm4→×1e-8, in4→×4.16231e-7
#   'spring_stiffness' N/mm→×1e3,  kN/m→×1e3,  kN/mm→×1e6,  MN/m→×1e6,
#                      mN/m→×1e-3
#   'density'          t/mm3→×1e12, g/mm3→×1e6, g/cm3→×1e3
#   'inversetemp'      1/°F→×1.8  (1/K en 1/°C: geen conversie)
#   'acceleration'     mm/s2→×1e-3
#   'time'             ms→×1e-3, us→×1e-6, min→×60, h→×3600
#   'temperature'      °C→+273.15, °F→(F-32)·5/9+273.15  (doeleenheid K)
#   'conductivity'     W/m/K;  W/mm/K, kW/m/K→×1e3
#   'specific_heat'    J/kg/K; kJ/kg/K, J/g/K→×1e3
#   'heat_transfer'    W/m2/K; W/mm2/K→×1e6, kW/m2/K→×1e3  (/°C = /K)
#   'heat_flux'        W/m2;   W/mm2→×1e6, W/cm2→×1e4, kW/m2→×1e3
#   'power_density'    W/m3;   W/mm3→×1e9, W/cm3→×1e6, kW/m3→×1e3
#   'power'            W;      kW→×1e3, mW→×1e-3, MW→×1e6
#   imperiaal         in, ft, lbf, kip, psi, ksi, lbf.in, lb, slug, ...:
#                      zie _OTHER_FACTORS (ook N/mm2, bar, um, km)
#   onbekende eenheid  waarde ongewijzigd + WARNING in de log
#   'line_load', 'stiffness_per_area', 'mass', 'rotational_inertia',
#   'angular_velocity', 'inverse_time', 'inverse_length', 'inverse_angle',
#   'damping'          zie _EXTRA_FACTORS
#   'dimensionless'    geen conversie
# ==========================================

def _normalize_unit_string(s):
    """
    Vervang Unicode-tekens in eenheden door ASCII voor eenheidsherkenning.

    Conversies (Unicode-codepoints):
        ² U+00B2 → '2'
        ³ U+00B3 → '3'
        ⁴ U+2074 → '4'
        ¹ U+00B9 → '1'
        ⁰ U+2070 → '0'
        ° U+00B0 → 'deg'
        µ U+00B5 / μ U+03BC → 'u'

    Compatibel met IronPython 2.7.9 (unicode-strings uit XML-parsing).
    """
    try:
        # Python 2: basestring omvat str en unicode
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
        (u'\u00b5', u'u'),   # µ (micro-teken)
        (u'\u03bc', u'u'),   # μ (Griekse mu)
    ]:
        s = s.replace(old, new)

    return s


def parse_and_convert(val_str, quantity_type):
    """
    Parst een waarde-string (getal + optionele eenheid) en converteert naar SI.

    Parameters
    ----------
    val_str       : str  Invoerstring, bijv. "210 GPa", "10000 mm⁴", "4231 N/m"
    quantity_type : str  Een van: 'length', 'force', 'pressure', 'angle',
                         'area', 'inertia', 'spring_stiffness', 'density',
                         'inversetemp', 'acceleration', 'time',
                         'velocity', 'moment', 'dimensionless'

    Returns
    -------
    float  Waarde in SI-eenheid, of 0.0 bij een parse-fout.
    """
    if not val_str:
        return 0.0

    # Normaliseer Unicode-tekens VOOR de regex
    val_str = _normalize_unit_string(str(val_str).strip())

    # Getal (teken, decimaal, exponent) gevolgd door eenheidsstring.
    # Eenheid mag letters, cijfers én '/' bevatten (bijv. "mm4", "n/m").
    match = re.match(
        r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-zA-Z0-9/]*)",
        val_str
    )
    if not match:
        return 0.0

    val  = float(match.group(1))
    unit = match.group(2).lower()
    # m (milli) en M (mega) vallen na lower() samen; het originele
    # voorvoegsel beslist.
    milli = match.group(2).startswith('m')
    # Volledige eenheid als sleutel: kleine letters, zonder spaties, punten,
    # '·' en '*' ("lbf·in" -> "lbfin", "N.m" -> "nm", "kg/m3").
    key = _unit_key(val_str[match.end(1):])

    # Imperiale en overige eenheden (zie _OTHER_FACTORS)
    other = _OTHER_FACTORS.get(quantity_type, {})
    if key in other:
        return val * other[key]

    # --------------------------------------------------
    # LENGTE   (doeleenheid: m)
    # --------------------------------------------------
    if quantity_type == 'length':
        if unit == 'mm':    return val * 1.0e-3
        if unit == 'cm':    return val * 1.0e-2
        if unit == 'km':    return val * 1.0e3

    # --------------------------------------------------
    # KRACHT   (doeleenheid: N)
    # --------------------------------------------------
    elif quantity_type == 'force':
        if unit == 'kn':    return val * 1.0e3
        if unit == 'mn':    return val * (1.0e-3 if milli else 1.0e6)

    # --------------------------------------------------
    # DRUK / E-MODULUS   (doeleenheid: Pa)
    # --------------------------------------------------
    elif quantity_type == 'pressure':
        if unit == 'kpa':   return val * 1.0e3
        if unit == 'mpa':   return val * (1.0e-3 if milli else 1.0e6)
        if unit == 'gpa':   return val * 1.0e9

    # --------------------------------------------------
    # HOEK   (doeleenheid: rad)
    # --------------------------------------------------
    elif quantity_type == 'angle':
        if unit == 'deg':
            return val * (math.pi / 180.0)

    # --------------------------------------------------
    # OPPERVLAKTE   (doeleenheid: m²)
    # Mecway exporteert bijv. "100 mm²" → na normalisatie "100 mm2"
    # --------------------------------------------------
    elif quantity_type == 'area':
        if unit == 'mm2':   return val * 1.0e-6
        if unit == 'cm2':   return val * 1.0e-4
        if unit == 'in2':   return val * 6.4516e-4

    # --------------------------------------------------
    # TRAAGHEIDSMOMENT   (doeleenheid: m⁴)
    # Mecway exporteert bijv. "10000 mm⁴" → na normalisatie "10000 mm4"
    # --------------------------------------------------
    elif quantity_type == 'inertia':
        if unit == 'mm4':   return val * 1.0e-12
        if unit == 'cm4':   return val * 1.0e-8
        if unit == 'in4':   return val * 4.16231e-7

    # --------------------------------------------------
    # VEERCONSTANTE   (doeleenheid: N/m)
    # Mecway exporteert bijv. "4231 N/m" of "10 N/mm"
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
        # kg/m³ of geen eenheid -> geen conversie nodig

    if quantity_type == 'inversetemp':
        if unit == '1/degf':  return val * 1.8
        # 1/K, 1/°C of geen eenheid -> geen conversie nodig

    if quantity_type == 'acceleration':
        if unit == 'mm/s2':  return val * 1.0e-3
        # m/s2 of geen eenheid -> geen conversie nodig

    if quantity_type == 'velocity':
        if unit == 'mm/s':  return val * 1.0e-3
        if unit == 'mm/ms': return val
        # m/s of geen eenheid -> geen conversie nodig

    if quantity_type == 'moment':
        # "2 N.m", "2 N·m", "5 kN.m", "300 N.mm": de eenheid bevat een
        # punt, die de regex hierboven niet meeneemt.
        full = val_str[match.end(1):].strip().lower()
        full = full.replace(u'·', u'.').replace(u'*', u'.')
        full = full.replace(u' ', u'').replace(u'.', u'')
        if full == 'knm':   return val * 1.0e3
        if full == 'nmm':   return val * 1.0e-3
        if full == 'knmm':  return val
        # N.m of geen eenheid -> geen conversie nodig

    if quantity_type == 'time':
        # SI is seconden.
        if unit == 'ms':  return val * 1.0e-3
        if unit == 'us':  return val * 1.0e-6
        if unit == 'min': return val * 60.0
        if unit == 'h':   return val * 3600.0
        # 's' of geen eenheid -> geen conversie nodig

    # --------------------------------------------------
    # THERMISCH (bridge_thermal.py). Mecway schrijft o.a. "500 K",
    # "20 °C" (CoolantChannel.liml), "380 W/m/K", "900 J/kg/K",
    # "37.5 W/m²/K", "1000 W/m²", "1000000 W/m³", "500 W". Een delende
    # '/°C' of '/°F' in een eenheid is hetzelfde als '/K' (resp. 5/9 K).
    # --------------------------------------------------
    if quantity_type == 'temperature':
        # Absolute temperatuur, doeleenheid K.
        if unit == 'degc':  return val + 273.15
        if unit == 'degf':  return (val - 32.0) * 5.0 / 9.0 + 273.15
        # K of geen eenheid -> geen conversie nodig

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

    # 'dimensionless', SI-eenheid of geen eenheid: waarde ongewijzigd.
    # Een onbekende eenheid ook, maar met een WARNING: een stille
    # doorgifte gaf bij "-3500 lbf" (Mecway Tutorials/Solution.liml) een
    # 4,45x te kleine kracht.
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
    """Eenheid als vergelijkingssleutel (zie parse_and_convert)."""
    full = unit_text.strip().replace(u'\u00b7', u'.').replace(u'*', u'.')
    return full.replace(u' ', u'').replace(u'.', u'').lower()


# Imperiale (en enkele metrische) eenheden -> SI. Exacte definities: 1 in = 0,0254 m,
# 1 ft = 0,3048 m, 1 lb = 0,45359237 kg, 1 lbf = 1 lb x 9,80665 m/s2 =
# 4,4482216152605 N, 1 kip = 1000 lbf, psi = lbf/in2, slug = lbf.s2/ft).
# Sleutels zoals _unit_key ("lbf.in" en "in.lbf" -> "lbfin" / "inlbf").
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

# Eenheden waarin de waarde al SI is (vergeleken via _unit_key; de eerste
# staat in de WARNING). Hoeveelheden zonder entry (o.a. 'dimensionless')
# geven geen WARNING. Mecway schrijft '/degC' en '/K' door elkaar.
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

# Al gemelde (logbestand, grootheid, eenheid): een WARNING per run.
_WARNED_UNITS = set()


# Factoren naar SI voor de hoeveelheden van de mechanische belastingen
# (traction, line pressure, elastic support, mass, ...). Sleutel: eenheid
# in kleine letters zonder spaties en punten ("N.s/m" -> "ns/m").
_EXTRA_FACTORS = {
    # kracht per lengte (line pressure) -> N/m
    'line_load': {'n/m': 1.0, 'n/mm': 1.0e3, 'kn/m': 1.0e3, 'kn/mm': 1.0e6,
                  'mn/m': 1.0e6},
    # stijfheid per oppervlak (elastic support, compression only) -> Pa/m
    'stiffness_per_area': {'pa/m': 1.0, 'kpa/m': 1.0e3, 'mpa/m': 1.0e6,
                           'gpa/m': 1.0e9, 'n/m3': 1.0, 'n/mm3': 1.0e9,
                           'mpa/mm': 1.0e9, 'gpa/mm': 1.0e12},
    # massa -> kg
    'mass': {'kg': 1.0, 'g': 1.0e-3, 't': 1.0e3, 'tonne': 1.0e3},
    # massatraagheidsmoment -> kg.m2 ("kg.m²" van Mecway)
    'rotational_inertia': {'kgm2': 1.0, 'kgmm2': 1.0e-6, 'tmm2': 1.0e-3,
                           'gmm2': 1.0e-9, 'kgcm2': 1.0e-4},
    # hoeksnelheid -> rad/s ("r/min" van Mecway)
    'angular_velocity': {'rad/s': 1.0, 'r/min': 2.0 * math.pi / 60.0,
                         'rpm': 2.0 * math.pi / 60.0,
                         'deg/s': math.pi / 180.0, 'r/s': 2.0 * math.pi},
    # 1/tijd (Rayleigh alpha, Mecway toont "rad/s") -> 1/s
    'inverse_time': {'rad/s': 1.0, '1/s': 1.0, '1/ms': 1.0e3},
    # 1/lengte (coefficient van een constraint equation op ux/uy/uz) -> 1/m
    'inverse_length': {'1/m': 1.0, '1/mm': 1.0e3, '1/cm': 1.0e2},
    # 1/hoek (coefficient op rx/ry/rz) -> 1/rad
    'inverse_angle': {'1/rad': 1.0, '1/deg': 180.0 / math.pi},
    # demping (damper) -> N.s/m
    'damping': {'ns/m': 1.0, 'ns/mm': 1.0e3, 'kns/m': 1.0e3},
}


def _convert_extra(val, unit, unit_text, quantity_type):
    """
    SI-waarde voor de hoeveelheden in _EXTRA_FACTORS en 'temperature', of
    None (onbekende hoeveelheid of eenheid: parse_and_convert geeft dan de
    waarde ongewijzigd terug).
    'temperature' -> K: "350 K", "20 degC" (na _normalize_unit_string),
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
    # m (milli) en M (mega) vallen na lower() samen: MPa/m, MN/m en mN/m
    if key in ('mpa/m', 'mn/m') and full[:1] == 'm':
        return val * {'mpa/m': 1.0e-3, 'mn/m': 1.0e-3}[key]
    if key in table:
        return val * table[key]
    return None
