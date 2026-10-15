# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_gui.py
# Start screen of the MecwayAsterBridge.
#
# Responsibility:
#   1. Show the current values from CONFIG_BRIDGE (bridge_utils.py) in a
#      window with a navigation list on the left and the chosen page on the
#      right: "Algemeen", "Elementen", one page per analysis (titles in
#      ANALYSIS_TITLES) and "Documentatie".
#   2. Validate the input.
#   3. Update CONFIG_BRIDGE in memory (applies directly to this run).
#   4. Write changed values back into bridge_utils.py (only the
#      lines concerned; backup in bridge_utils.py.bak).
#
# Technique:
#   - The Mecway API only has mw.input() (a text field) and mw.message().
#     For a form with file/folder pickers .NET Windows Forms is used
#     via IronPython's 'clr'. Whether Mecway's scripting engine
#     allows that is not documented; if loading fails, the
#     dialog falls back to a series of mw.input() questions.
#   - FolderBrowserDialog/OpenFileDialog require an STA thread. If the
#     script does not run in an STA thread, the dialog is shown in its own
#     STA thread.
#
# Extending:
#   - New setting = entry in GENERAL_SPECS or ANALYSIS_SPECS plus the
#     key in CONFIG_BRIDGE (bridge_utils.py). Analysis settings
#     are only shown for analyses in which the key exists.
#     General keys in ELEMENT_KEYS are on the page "Elementen".
#   - New analysis: title in ANALYSIS_TITLES (otherwise the key is
#     shown); the page and the line in the navigation appear by themselves.
#   - New page of another kind: new_page(title, group) in
#     _show_winforms_dialog (the only registration point of the navigation).
#   - Labels and titles are a pair (nl, en) (or a text that is the same in
#     both languages); the language is CONFIG_BRIDGE["language"] at start.
#
# Compatible with IronPython 2.7.9.

import os
import re
import codecs
import shutil

import bridge_utils
import bridge_docs
import bridge_glossary
import bridge_results_liml
from bridge_utils import (CONFIG_BRIDGE, MECWAY_ANALYSIS_TYPES, tr,
                          work_dir_path, exe_aster_path, expand_path,
                          default_work_dir, BRIDGE_VERSION)
from bridge_from_aster import RESULT_FIELD_SPECS


def _t(text):
    """Label or filter in the chosen language: a pair (nl, en) or a text
    that is the same in both languages."""
    if isinstance(text, tuple):
        return tr(*text)
    return text


# ==========================================
# SCHEMA OF THE SETTINGS
# (key, label, kind, extra)
#   kind   : 'file', 'folder', 'text', 'int', 'float_pos', 'float_range',
#            'bool', 'choice', 'analysis_choice', 'configuration_choice',
#            'checklist'
#   extra  : file -> file filter; int -> minimum; choice -> options;
#            float_range -> (minimum, maximum), bounds included
# ==========================================
#   label and file filter: text, or a pair (nl, en) that _t() translates.
GENERAL_SPECS = [
    ("language", "Taal / Language", "choice", ("nl", "en")),
    ("exe_aster", "Code-Aster launcher (run_aster.bat)", "file",
     ("Batch-bestanden (*.bat)|*.bat|Alle bestanden (*.*)|*.*",
      "Batch files (*.bat)|*.bat|All files (*.*)|*.*")),
    ("work_dir", ("Werkmap", "Work folder"), "folder", None),
    ("ncpus", ("Aantal CPU-kernen (ncpus)", "Number of CPU cores (ncpus)"),
     "int", 1),
    ("active_analysis", ("Actieve analyse (auto = volgens Mecway)",
                         "Active analysis (auto = follow Mecway)"),
     "analysis_choice", None),
    # Choice list with the configurations of the open model (_MODEL_INFO)
    ("configuration", ("Configuratie (auto = volgens de regel)",
                       "Configuration (auto = by rule)"),
     "configuration_choice", None),
    ("mecway_solve_first", ("Eerst Mecway-solve ter controle",
                            "Mecway solve first as a check"), "bool", None),
    ("result_route", ("Resultaten naar Mecway", "Results to Mecway"),
     "choice", ("liml", "tabel")),
    ("convergence_monitor", ("Convergentie- en meldingenscherm",
                             "Convergence and messages window"),
     "bool", None),
    ("med_export", ("MED-bestand voor ParaView", "MED file for ParaView"),
     "bool", None),
    ("elem_hex8", ("Hex8-volume-elementen", "Hex8 solid elements"),
     "choice", ("3D", "3D_SI", "LINE_QUAD")),
    ("elem_shell", ("Lineaire schalen (tri3/quad4)",
                    "Linear shells (tri3/quad4)"), "choice",
     ("DKT", "DST", "COQUE_3D")),
    ("elem_beam", ("Balken (line2/line3)", "Beams (line2/line3)"),
     "choice",
     ("POU_D_E", "POU_D_T")),
]

# General keys that are on the page "Elementen".
ELEMENT_KEYS = ("elem_hex8", "elem_shell", "elem_beam")

_ELEMENT_HELP = (
    u"Hex8 (volume-elementen)\n"
    u"  \u2022 3D: volledig ge\u00efntegreerd; stijver dan de hex8 van Mecway "
    u"(incompatibele modes), zie KNOWN_BUGS 1.\n"
    u"  \u2022 3D_SI: onderintegratie; alleen elsets met uitsluitend hex8, niet "
    u"expliciet. Met 1 element over de dikte ~0 buigspanning.\n"
    u"  \u2022 LINE_QUAD: Code-Aster maakt lineaire volumes kwadratisch (hex8 -> "
    u"hex20, tet4 -> tet10); buiging klopt, ~3x zoveel knopen.\n"
    u"     Alleen bij een model met uitsluitend volume-elementen, niet "
    u"expliciet; resultaten op de hoekknopen.\n"
    u"\n"
    u"Lineaire schalen (tri3/quad4)\n"
    u"  \u2022 DKT: dunne plaat (Kirchhoff).\n"
    u"  \u2022 DST: met dwarskrachtvervorming (Mindlin); alleen bij Statisch, "
    u"anders DKT.\n"
    u"  \u2022 COQUE_3D: Code-Aster maakt de schalen kwadratisch (quad9/tria7, "
    u"met rotatie om de normaal);\n"
    u"     niet bij gedeelde knopen met elementen die lineair blijven (dan "
    u"DKT). Kwadratische schalen blijven COQUE_3D.\n"
    u"\n"
    u"Balken (line2/line3; line3 in twee SEG2-cellen gesplitst)\n"
    u"  \u2022 POU_D_E: Euler-Bernoulli, zoals Mecway.\n"
    u"  \u2022 POU_D_T: Timoshenko (met afschuifvervorming); I/T/C/L-profielen "
    u"met benaderde afschuifco\u00ebffici\u00ebnten,\n"
    u"     algemene doorsnede AY = AZ = 1.",
    u"Hex8 (solid elements)\n"
    u"  \u2022 3D: fully integrated; stiffer than Mecway's hex8 (incompatible "
    u"modes), see KNOWN_BUGS 1.\n"
    u"  \u2022 3D_SI: reduced integration; only elsets with hex8 elements only, "
    u"not explicit. With 1 element through the thickness ~0 bending stress.\n"
    u"  \u2022 LINE_QUAD: Code-Aster makes linear solids quadratic (hex8 -> "
    u"hex20, tet4 -> tet10); bending is correct, ~3x as many nodes.\n"
    u"     Only for a model with solid elements only, not explicit; results "
    u"on the corner nodes.\n"
    u"\n"
    u"Linear shells (tri3/quad4)\n"
    u"  \u2022 DKT: thin plate (Kirchhoff).\n"
    u"  \u2022 DST: with transverse shear deformation (Mindlin); only in "
    u"Static, otherwise DKT.\n"
    u"  \u2022 COQUE_3D: Code-Aster makes the shells quadratic (quad9/tria7, "
    u"with rotation about the normal);\n"
    u"     not when they share nodes with elements that stay linear (then "
    u"DKT). Quadratic shells stay COQUE_3D.\n"
    u"\n"
    u"Beams (line2/line3; line3 split into two SEG2 cells)\n"
    u"  \u2022 POU_D_E: Euler-Bernoulli, like Mecway.\n"
    u"  \u2022 POU_D_T: Timoshenko (with shear deformation); I/T/C/L profiles "
    u"with approximated shear coefficients,\n"
    u"     general section AY = AZ = 1.")

# Readable titles of the analyses (pages and messages), in the order
# of the navigation. Analyses not listed here get their key as
# title and come last.
ANALYSIS_TITLES = [
    ("lin_static_3d", ("Statisch", "Static")),
    ("nonlin_static_3d", ("Niet-lineair statisch", "Nonlinear static")),
    ("dyna_impl_3d", ("Dynamisch (impliciet)", "Dynamic (implicit)")),
    ("dyna_expl_3d", ("Dynamisch (expliciet)", "Dynamic (explicit)")),
    ("ther_3d", ("Thermisch", "Thermal")),
    ("modal_3d", ("Modaal", "Modal")),
    ("dyna_modal_3d", ("Respons op modale basis", "Mode superposition")),
    ("harmonic_3d", ("Harmonische respons", "Harmonic response")),
    ("spectrum_3d", ("Responsspectrum", "Response spectrum")),
    ("buckling_3d", ("Knik", "Buckling")),
    ("acoustic_modes_3d", ("Akoestiek (holtemodes)",
                           "Acoustics (cavity modes)")),
    ("acoustic_harm_3d", ("Akoestiek (harmonisch)",
                          "Acoustics (harmonic)")),
    ("vibroacoustic_modes_3d", ("Vibro-akoestiek (modes)",
                                "Vibroacoustics (modes)")),
    ("vibroacoustic_harm_3d", ("Vibro-akoestiek (harmonisch)",
                               "Vibroacoustics (harmonic)")),
]

# Deliberately not on the screen (belong to the analysis itself; docs/
# Standaardinstellingen_en_aannames.md sec. 3.1): "template" and
# "solver_command" (only shown, at the top of the page), "type_resu",
# "phenomene", "vibroacoustic" and "type_calcul" (route the analysis to
# its builder in bridge_to_aster).
ANALYSIS_SPECS = [
    ("fields", ("Resultaatvelden naar Mecway", "Result fields to Mecway"),
     "checklist", None),
    ("time_limit", ("Tijdslimiet run_aster [s]", "Time limit run_aster [s]"),
     "int", 1),
    ("memory_limit", ("Geheugenlimiet run_aster [MB]",
                      "Memory limit run_aster [MB]"), "int", 1),
    ("solver_nprec", ("MUMPS NPREC (-1 = controle uit)",
                      "MUMPS NPREC (-1 = check off)"), "int", -1),
    ("lin_solver", ("Lineaire oplosser (MUMPS / GCPC)",
                    "Linear solver (MUMPS / GCPC)"), "choice",
     ("MUMPS", "GCPC")),
    ("lin_solver_resi", ("Nauwkeurigheid oplosser (RESI_RELA)",
                         "Solver accuracy (RESI_RELA)"), "float_pos", None),
    ("substeps_per_interval", ("Substappen per tijdsinterval",
                               "Substeps per time interval"), "int", 1),
    ("newton_max_iter", ("Max. Newton-iteraties (ITER_GLOB_MAXI)",
                         "Max. Newton iterations (ITER_GLOB_MAXI)"),
     "int", 1),
    # REAC_ITER 0 (never reassemble) stopped with DVP_2 (verification
    # NL-02a, docs review); hence at least 1.
    ("newton_reac_iter", "NEWTON REAC_ITER", "int", 1),
    ("default_time_end", ("Eindtijd zonder tijdsbelasting [s]",
                          "End time without time load [s]"), "float_pos",
     None),
    ("convergence_criterion", ("Convergentiecriterium (RELA / MAXI / RELA "
                               "of MAXI)",
                               "Convergence criterion (RELA / MAXI / RELA "
                               "or MAXI)"),
     "choice", ("RELA", "MAXI", "RELA_OF_MAXI")),
    ("convergence_resi_rela", ("Convergentie RESI_GLOB_RELA",
                               "Convergence RESI_GLOB_RELA"), "float_pos",
     None),
    ("convergence_resi_maxi", ("Convergentie RESI_GLOB_MAXI [N]",
                               "Convergence RESI_GLOB_MAXI [N]"), "float_pos",
     None),
    ("contact_algo", ("Contactmethode (STANDARD / PENALISATION)",
                      "Contact method (STANDARD / PENALISATION)"), "choice",
     ("STANDARD", "PENALISATION")),
    ("plastic_strain_definition", ("Rekdefinitie hardingscurve",
                                   "Strain definition hardening curve"),
     "choice", ("auto", "plastic", "total")),
    ("deformation", "COMPORTEMENT DEFORMATION", "choice",
     ("PETIT", "PETIT_REAC", "GROT_GDEP", "GDEF_LOG", "GREEN_LAGRANGE",
      "SIMO_MIEHE")),
    # SCHEMA_TEMPS SCHEMA (catalog dyna_non_line.py also has NOHHT; the
    # bridge does not translate it). Implicit: HHT/NEWMARK; explicit:
    # DIFF_CENT/TCHAMWA.
    ("schema", ("Tijdschema (SCHEMA_TEMPS)", "Time scheme (SCHEMA_TEMPS)"),
     "choice", ("HHT", "NEWMARK", "DIFF_CENT", "TCHAMWA")),
    # HHT ALPHA: the catalog does not bound the value (dyna_non_line.py,
    # default -0.1); U2.06.13 gives -0.3 as lower bound of the usual
    # values (docs review); HHT is unconditionally stable for
    # -1/3 <= alpha <= 0.
    ("hht_alpha", "HHT ALPHA (-0.3 .. 0)", "float_range", (-0.3, 0.0)),
    ("substeps_per_output", ("Rekenstappen per uitvoerinterval",
                             "Solver steps per output interval"), "int", 1),
    ("explicit_dt_factor", ("Tijdstap / kritieke tijdstap",
                            "Time step / critical time step"), "float_pos",
     None),
    # Thermal transient: SCHEMA_TEMPS THETA, val_min 0 / val_max 1
    # (catalog ther_lineaire.py v17.4).
    ("theta", ("Tijdschema THETA (0 .. 1)", "Time scheme THETA (0 .. 1)"),
     "float_range", (0.0, 1.0)),
    # Failure of elements (bridge_failure.py; nonlinear and dynamic)
    ("element_failure", ("Bezwijken van elementen (plastische rek)",
                         "Element failure (plastic strain)"), "bool", None),
    ("failure_plastic_strain", ("Bezwijkgrens alle plastische mat. (0 = uit)",
                                "Failure limit all plastic mat. (0 = off)"),
     "float_range", (0.0, 100.0)),
    ("failure_stiffness_factor", ("Stijfheid bezweken element (x E)",
                                  "Stiffness of failed element (x E)"),
     "float_range", (1.0e-7, 0.1)),
    ("energy_balance", ("Energiebalans (ENERGIE; niet met contact)",
                        "Energy balance (ENERGIE; not with contact)"),
     "bool", None),
    ("error_estimator", ("Foutschatter (CALC_ERREUR, alleen volumes)",
                         "Error estimator (CALC_ERREUR, solids only)"),
     "bool", None),
    # Fracture mechanics (bridge_fracture.py; only with SCHEUR_ selections).
    # R_INF/R_SUP: val_min 0 in calc_g.py v17.4; 0 and 0 = automatic.
    # DEGRE: 0 .. 7 (calc_g.py).
    ("fracture_r_inf", ("Scheur: R_INF [m] (0 = automatisch)",
                        "Crack: R_INF [m] (0 = automatic)"), "float_range",
     (0.0, 1.0e3)),
    ("fracture_r_sup", ("Scheur: R_SUP [m] (0 = automatisch)",
                        "Crack: R_SUP [m] (0 = automatic)"), "float_range",
     (0.0, 1.0e3)),
    ("fracture_smoothing", ("Scheur: gladmaken langs het front",
                            "Crack: smoothing along the front"), "choice",
     ("LINEAIRE", "LEGENDRE")),
    ("fracture_legendre_degree", ("Scheur: Legendre-graad (0 .. 7)",
                                  "Crack: Legendre degree (0 .. 7)"),
     "int", 0),
    # Adaptive refinement (bridge_adapt.py; docs/Foutschatter.md sec. 6)
    ("adapt_refine", ("Adaptieve verfijning (Mecway refine_x2)",
                      "Adaptive refinement (Mecway refine_x2)"),
     "bool", None),
    ("adapt_target_error", ("Doel: globale relatieve fout [%]",
                            "Target: global relative error [%]"),
     "float_range", (0.01, 100.0)),
    ("adapt_max_loops", ("Max. aantal verfijningslussen",
                         "Max. number of refinement loops"), "int", 1),
    ("adapt_select", ("Keuze van de elementen", "Element selection"),
     "choice", ("dorfler", "fraction", "factor")),
    ("adapt_fraction", ("Keuzewaarde (Dorfler/fractie: 0..1; factor)",
                        "Selection value (Dorfler/fraction: 0..1; factor)"),
     "float_range", (0.0, 100.0)),
    ("adapt_neighbours", ("Ook de buren verfijnen (dunne elementen)",
                          "Also refine the neighbours (thin elements)"),
     "bool", None),
    ("adapt_max_elements", ("Max. aantal elementen na verfijnen",
                            "Max. number of elements after refining"),
     "int", 100),
    # Nonlinear buckling (bridge_to_aster._crit_stab_args,
    # _imperfection_plan; docs/Modaal_en_knik.md sec. 5). Amplitude 0 =
    # no imperfection; negative reverses the buckling shape.
    ("crit_stab", ("Stabiliteit per stap (CRIT_STAB)",
                   "Stability per step (CRIT_STAB)"), "bool", None),
    ("imperfection_amplitude", ("Imperfectie: amplitude (0 = geen)",
                                "Imperfection: amplitude (0 = none)"),
     "float_range", (-1.0e3, 1.0e3)),
    ("imperfection_mode", ("Imperfectie: knikvorm nr.",
                           "Imperfection: buckling mode no."), "int", 1),
    ("imperfection_unit", ("Imperfectie: amplitude in (m / x L)",
                           "Imperfection: amplitude in (m / x L)"),
     "choice", ("m", "L")),
    # Modal (CALC_MODES, bridge_to_aster._build_modal). NMAX_FREQ: val_min
    # 0 in the catalog calc_modes.py v17.4; 0 modes is pointless, so 1.
    ("modal_modes", ("Aantal modes (zonder maxmode in Mecway)",
                     "Number of modes (without maxmode in Mecway)"),
     "int", 1),
    ("modal_shift_hz", ("Zoekfrequentie [Hz] (0 = laagste modes)",
                        "Search frequency [Hz] (0 = lowest modes)"),
     "float_range", (-1.0e9, 1.0e9)),
    # NORM_MODE NORME (catalog calc_modes.py v17.4: MASS_GENE, RIGI_GENE,
    # EUCL, EUCL_TRAN, TRAN, TRAN_ROTA); the meaningful ones for Mecway.
    ("modal_norm", ("Normering trillings-/knikvormen (NORM_MODE)",
                    "Mode shape normalisation (NORM_MODE)"), "choice",
     ("MASS_GENE", "RIGI_GENE", "TRAN_ROTA", "TRAN", "EUCL")),
    ("modal_tolerance", ("Controle modes (VERI_MODE SEUIL)",
                         "Mode check (VERI_MODE SEUIL)"), "float_pos", None),
    # Vibro-acoustics (bridge_vibroacoustic._mode_search_block): > 0,
    # because U_P_PHI gives spurious modes at 0 Hz.
    ("vibro_freq_min", ("Ondergrens frequentie [Hz] (modes erboven)",
                        "Lower frequency bound [Hz] (modes above it)"),
     "float_pos", None),
    # Modal with prestress (bridge_to_aster._prestress_plan)
    ("modal_prestress", ("Voorspanning door belastingen (stress stiffening)",
                         "Prestress from loads (stress stiffening)"),
     "bool", None),
    # Complex modes with damping (bridge_modal_damping.py)
    ("modal_complex", ("Complexe modes met demping (Rayleigh, dempers)",
                       "Complex modes with damping (Rayleigh, dampers)"),
     "bool", None),
    # Cyclic symmetry (bridge_cyclic.py, MODE_ITER_CYCL)
    ("cyclic_base_modes", ("Cyclische symmetrie: sectormodes in de basis "
                           "(0 = automatisch)",
                           "Cyclic symmetry: sector modes in the basis "
                           "(0 = automatic)"), "int", 0),
    ("cyclic_full_wheel", ("Cyclische symmetrie: het hele wiel naar Mecway",
                           "Cyclic symmetry: the whole wheel to Mecway"),
     "bool", None),
    # Response on modal basis (bridge_dyna_modal.py)
    ("steps_per_period", ("Rekenstappen per periode van de hoogste mode",
                          "Solver steps per period of the highest mode"),
     "int", 4),
    ("modal_damping", ("Extra modale demping (fractie van kritisch)",
                       "Extra modal damping (fraction of critical)"),
     "float_range", (0.0, 0.99)),
    ("static_correction", ("Statische correctie weggelaten modes "
                           "(MACRO_ELAS_MULT)",
                           "Static correction truncated modes "
                           "(MACRO_ELAS_MULT)"), "bool", None),
    # Response spectrum (bridge_spectrum.py)
    ("spectrum_abscissa", ("Spectrumtabel: kolom 'time' is",
                           "Spectrum table: column 'time' is"), "choice",
     ("period", "frequency")),
    ("spectrum_damping", ("Modale demping (fractie van kritisch)",
                          "Modal damping (fraction of critical)"),
     "float_range", (0.0, 0.99)),
    ("modal_combination", ("Combinatie modes", "Combination of modes"),
     "choice", ("CQC", "SRSS", "ABS")),
    ("direction_combination", ("Combinatie richtingen",
                               "Combination of directions"), "choice",
     ("SRSS", "100-30-30", "100-40-40", "ABS")),
    ("missing_mass", ("Missing mass (pseudo-modes, MODE_CORR)",
                      "Missing mass (pseudo-modes, MODE_CORR)"), "bool",
     None),
    # Acoustics harmonic (bridge_acoustic.build_acoustic_harm); the list
    # is text ("0" = the range), so that it can also stay empty-like.
    ("harm_freq_start", ("Startfrequentie [Hz]", "Start frequency [Hz]"),
     "float_pos", None),
    ("harm_freq_end", ("Eindfrequentie [Hz]", "End frequency [Hz]"),
     "float_pos", None),
    ("harm_freq_count", ("Aantal frequenties", "Number of frequencies"),
     "int", 1),
    ("harm_freq_spacing", ("Verdeling (lin / log)", "Spacing (lin / log)"),
     "choice", ("lin", "log")),
    ("harm_freq_list", ("Frequentielijst [Hz] (0 = bereik hierboven)",
                        "Frequency list [Hz] (0 = range above)"), "text",
     None),
    # Harmonic response (bridge_harmonic.py)
    ("harm_basis", ("Basis (GENE modaal / PHYS direct)",
                    "Basis (GENE modal / PHYS direct)"), "choice",
     ("GENE", "PHYS")),
    ("harm_refine_points", ("Extra frequenties per resonantie (0 = geen)",
                            "Extra frequencies per resonance (0 = none)"),
     "int", 0),
    ("source_velocity", ("Snelheid BRON_-vlakken [m/s]",
                         "Velocity SOURCE_ faces [m/s]"), "float_pos",
     None),
    # Vibro-acoustics harmonic (bridge_vibroacoustic_harm.py)
    ("incident_pressure", ("Amplitude invallende golf INVALLEND_ [Pa]",
                           "Amplitude incident wave INCIDENT_ [Pa]"),
     "float_pos", None),
]

# Headings on the pages: the heading is above the first shown
# setting of its group (key -> (nl, en)).
SECTION_BEFORE = {
    "language": ("Taal en installatie", "Language and installation"),
    "active_analysis": ("Analyse", "Analysis"),
    "result_route": ("Resultaten en weergave", "Results and display"),
    "elem_hex8": ("Elementformulering", "Element formulation"),
    "fields": ("Resultaten", "Results"),
    "time_limit": ("Code-Aster-run", "Code-Aster run"),
    "solver_nprec": ("Oplosser", "Solver"),
    "substeps_per_interval": ("Stappen en convergentie",
                              "Steps and convergence"),
    "contact_algo": ("Contact", "Contact"),
    "plastic_strain_definition": ("Materiaal en kinematica",
                                  "Material and kinematics"),
    "schema": ("Tijdschema", "Time scheme"),
    "theta": ("Tijdschema", "Time scheme"),
    "element_failure": ("Bezwijken", "Failure"),
    "energy_balance": ("Controle", "Checks"),
    "error_estimator": ("Controle", "Checks"),
    "fracture_r_inf": ("Breukmechanica (SCHEUR_-selecties)",
                       "Fracture mechanics (CRACK_ selections)"),
    "adapt_refine": ("Adaptieve verfijning", "Adaptive refinement"),
    "crit_stab": ("Niet-lineaire knik", "Nonlinear buckling"),
    "modal_modes": ("Modes", "Modes"),
    "steps_per_period": ("Tijdintegratie en demping",
                         "Time integration and damping"),
    "spectrum_abscissa": ("Spectrum en combinatie",
                          "Spectrum and combination"),
    "harm_freq_start": ("Frequenties", "Frequencies"),
    "source_velocity": ("Bron", "Source"),
}

# Colours (R, G, B) and sizes of the windows: calm grey-white with a
# blue accent colour, font Segoe UI (Windows default).
_STYLE = {
    "font": ("Segoe UI", 9.0),
    "header_bg": (36, 54, 75),
    "header_fg": (255, 255, 255),
    "header_sub": (190, 202, 216),
    "accent": (31, 111, 178),
    "accent_hover": (24, 92, 150),
    "window_bg": (243, 245, 248),
    "page_bg": (255, 255, 255),
    "line": (218, 223, 230),
    "muted": (96, 106, 120),
    "status_bg": (236, 240, 245),
    "button_bg": (255, 255, 255),
    "label_w": 300,      # width of label column
    "row_h": 32,         # height of a row
    "nav_w": 220,        # width of navigation list on the left
    "nav_row_h": 32,     # height of a page in the navigation
    "nav_caption_h": 26,  # extra height for a group heading above it
}

# Default values for general keys that are still missing in an older
# bridge_utils.py (then the value is used, but not saved).
# Time schemes per dynamic analysis (choice list 'schema').
_SCHEMES = {"dyna_impl_3d": ("HHT", "NEWMARK"),
            "dyna_expl_3d": ("DIFF_CENT", "TCHAMWA")}

_GENERAL_DEFAULTS = {"language": "en", "configuration": "auto",
                     "mecway_solve_first": False, "result_route": "liml",
                     "convergence_monitor": True, "med_export": False,
                     "elem_hex8": "3D",
                     "elem_shell": "DKT", "elem_beam": "POU_D_E"}


# ==========================================
# HELPER FUNCTIONS: OPTIONS, DISPLAY, VALIDATION
# ==========================================
def _analysis_names():
    """Analyses in the order of ANALYSIS_TITLES, unknown ones after."""
    names = list(CONFIG_BRIDGE["analyses"].keys())
    known = [k for k, _t in ANALYSIS_TITLES if k in names]
    return known + sorted(k for k in names if k not in known)


def _analysis_title(name):
    """Readable title of an analysis (or the key)."""
    for key, title in ANALYSIS_TITLES:
        if key == name:
            return _t(title)
    return name


def _page_title(name, active):
    """Title of the page of an analysis; the active one gets a mark."""
    return _analysis_title(name) + (tr(" (actief)", " (active)")
                                    if name == active else "")


def _template_label(template):
    """Template name for the window; a custom template outside the
    Scripts folder with the full path, a missing one with a message."""
    full = bridge_utils.template_path(template)
    if not full:
        return "?"
    if not os.path.isfile(full):
        return tr(u"{0} (niet gevonden)", u"{0} (not found)").format(template)
    if os.path.normcase(os.path.dirname(full)) == os.path.normcase(
            bridge_utils.SCRIPTS_DIR):
        return os.path.basename(full)
    return full


def _mecway_types_for(name):
    """Mecway analysis types that lead to this analysis with 'auto'."""
    return sorted(k for k, v in MECWAY_ANALYSIS_TYPES.items() if v == name)


def _where(analysis, key):
    """Name of the page of a setting (for messages)."""
    if analysis is not None:
        return _analysis_title(analysis)
    return (tr("Elementen", "Elements") if key in ELEMENT_KEYS
            else tr("Algemeen", "General"))


def _field_options(current):
    opts = list(RESULT_FIELD_SPECS.keys())
    for v in current:
        if v not in opts:
            opts.append(v)
    return opts


# Choice lists (combobox): fixed options, analyses or configurations.
_CHOICE_KINDS = ("choice", "analysis_choice", "configuration_choice")

# Configurations of the model that is open in Mecway (run_settings_dialog,
# bridge_results_liml.configuration_names); empty without a model or
# without configurations.
_MODEL_INFO = {"configurations": []}


def _choice_options(kind, extra):
    if kind == "analysis_choice":
        return ["auto"] + _analysis_names()
    if kind == "configuration_choice":
        return ["auto"] + list(_MODEL_INFO["configurations"])
    return list(extra)


def _float_text(value):
    """Shortest text that gives back exactly the same float. repr() gives
    e.g. '-0.10000000000000001' in IronPython 2.7.9 and "{0:g}".format()
    follows the Windows locale ('-0,1'); %-formatting always gives a
    point (both seen in a test with Mecway's IronPython)."""
    value = float(value)
    for digits in (12, 15, 17):
        text = ("%." + str(digits) + "g") % value
        if float(text) == value:
            break
    if "." not in text and "e" not in text and "n" not in text:
        text += ".0"   # stays a float in bridge_utils.py
    return text


def exe_missing_text():
    """Message for the status box (with an empty line after it) if
    run_aster.bat does not exist, e.g. at a first start with a different
    installation folder; otherwise ""."""
    exe = exe_aster_path()
    if exe and os.path.isfile(exe):
        return u""
    return tr(u"Code-Aster niet gevonden: {0}\nKies op de pagina Algemeen "
              u"bij 'Code-Aster launcher (run_aster.bat)' met Bladeren... "
              u"het bestand run_aster.bat in de map bin van je "
              u"Code-Aster-installatie. Installatie: README.md en "
              u"Documentatie > Handleiding §1.\n\n",
              u"Code-Aster not found: {0}\nOn the General page, use "
              u"Browse... next to 'Code-Aster launcher (run_aster.bat)' to "
              u"choose run_aster.bat in the bin folder of your Code-Aster "
              u"installation. Installation: README.md and Documentation > "
              u"User guide §1.\n\n").format(exe or u"-")


def _format_value(value, kind):
    """Text display of a value in a text field or mw.input prompt."""
    if kind in ("float_pos", "float_range"):
        return _float_text(value)
    if kind == "bool":
        return tr("ja", "yes") if value else tr("nee", "no")
    if kind == "checklist":
        return ", ".join(value)
    return "{0}".format(value)


def _parse_and_validate(key, kind, extra, raw):
    """
    Convert input to a value and check it.

    raw : str for text kinds; bool for 'bool'; str for choices;
          list for 'checklist'.

    Returns
    -------
    (value, error)  error is None if the input is valid.
    """
    if kind in ("text", "file", "folder"):
        value = raw.strip()
        if key == "work_dir" and (not value or os.path.normcase(
                os.path.normpath(expand_path(value))) == os.path.normcase(
                    os.path.normpath(default_work_dir()))):
            # empty or the default folder: save "" (bridge_utils.work_dir_path)
            return "", None
        if not value:
            return None, tr("mag niet leeg zijn.", "must not be empty.")
        # environment variables (%LOCALAPPDATA%) stay in the setting
        if kind == "file" and not os.path.isfile(expand_path(value)):
            return None, tr("bestand bestaat niet: {0}",
                            "file does not exist: {0}").format(
                                expand_path(value))
        if kind == "folder" and not os.path.isabs(expand_path(value)):
            return None, tr("geef een volledig pad op: {0}",
                            "enter a full path: {0}").format(value)
        return value, None

    if kind == "int":
        try:
            value = int(raw.strip())
        except ValueError:
            return None, tr("geen geheel getal: '{0}'.",
                            "not a whole number: '{0}'.").format(raw)
        if extra is not None and value < extra:
            return None, tr("moet minimaal {0} zijn.",
                            "must be at least {0}.").format(extra)
        return value, None

    if kind == "float_pos":
        try:
            value = float(raw.strip().replace(",", "."))
        except ValueError:
            return None, tr("geen getal: '{0}'.",
                            "not a number: '{0}'.").format(raw)
        if value <= 0.0:
            return None, tr("moet groter dan 0 zijn.",
                            "must be greater than 0.")
        return value, None

    if kind == "float_range":
        try:
            value = float(raw.strip().replace(",", "."))
        except ValueError:
            return None, tr("geen getal: '{0}'.",
                            "not a number: '{0}'.").format(raw)
        lo, hi = extra
        if value < lo or value > hi:
            return None, tr("moet tussen {0} en {1} liggen.",
                            "must be between {0} and {1}.").format(lo, hi)
        return value, None

    if kind == "bool":
        return bool(raw), None

    if kind == "configuration_choice":
        # Any name is allowed: the setting also applies to other models; a
        # name that does not exist there gives a WARNING and "auto" in the run
        # (bridge_utils.choose_configuration).
        return u"{0}".format(raw).strip() or "auto", None

    if kind in _CHOICE_KINDS:
        options = _choice_options(kind, extra)
        value = "{0}".format(raw).strip()
        if value not in options:
            return None, tr("kies een van: {0}.",
                            "choose one of: {0}.").format(", ".join(options))
        return value, None

    if kind == "checklist":
        value = list(raw)
        if not value:
            return None, tr("kies minstens een veld.",
                            "choose at least one field.")
        return value, None

    return None, tr("onbekend soort instelling '{0}'.",
                    "unknown kind of setting '{0}'.").format(kind)


def _collect_current():
    """Current values from CONFIG_BRIDGE in the structure of the dialog."""
    general = {}
    for key, _label, _kind, _extra in GENERAL_SPECS:
        general[key] = CONFIG_BRIDGE.get(key, _GENERAL_DEFAULTS.get(key))
    analyses = {}
    for name in _analysis_names():
        cfg = CONFIG_BRIDGE["analyses"][name]
        analyses[name] = {}
        for key, _label, _kind, _extra in ANALYSIS_SPECS:
            if key in cfg:
                analyses[name][key] = cfg[key]
    return {"general": general, "analyses": analyses}


# ==========================================
# APPLYING IN MEMORY
# ==========================================
def _apply_values(new_values):
    """
    Write new values into CONFIG_BRIDGE (memory).

    Returns
    -------
    list of (analysis_or_None, key, kind, old, new)  changed ones only.
    """
    changes = []
    for key, _label, kind, _extra in GENERAL_SPECS:
        if key not in new_values["general"]:
            continue
        new = new_values["general"][key]
        old = CONFIG_BRIDGE.get(key, _GENERAL_DEFAULTS.get(key))
        if new != old or key not in CONFIG_BRIDGE:
            CONFIG_BRIDGE[key] = new
            changes.append((None, key, kind, old, new))
    for name, vals in new_values["analyses"].items():
        cfg = CONFIG_BRIDGE["analyses"][name]
        for key, _label, kind, _extra in ANALYSIS_SPECS:
            if key not in vals:
                continue
            new = vals[key]
            old = cfg.get(key)
            if new != old:
                cfg[key] = new
                changes.append((name, key, kind, old, new))
    return changes


# ==========================================
# SAVING IN bridge_utils.py
#
# Only the lines of changed keys are replaced. Comment
# lines stay untouched.
# Required form per key:   "key": value,   (one line), except
# lists ("fields"), which may span several lines.
# ==========================================
def bridge_utils_path():
    path = os.path.abspath(bridge_utils.__file__)
    if path.endswith(".pyc") or path.endswith(".pyo"):
        path = path[:-1]
    return path


def _render_str(s):
    if "\\" in s and not s.endswith("\\") and '"' not in s:
        return 'r"' + s + '"'
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _render_value(value, kind):
    if kind == "bool":
        return "True" if value else "False"
    if kind == "int":
        return "{0}".format(int(value))
    if kind in ("float_pos", "float_range"):
        return _float_text(value)
    if kind == "checklist":
        return "[" + ", ".join(_render_str(v) for v in value) + "]"
    return _render_str("{0}".format(value))


def _matching_brace(text, open_idx):
    """Index of the '}' that belongs to the '{' at open_idx (or -1)."""
    depth = 0
    quote = None
    i = open_idx
    n = len(text)
    while i < n:
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif c in ('"', "'"):
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _block_span(text, header_pattern, lo=0, hi=None):
    """(start, end) of the content of the dict block after header_pattern."""
    if hi is None:
        hi = len(text)
    m = re.compile(header_pattern, re.M).search(text, lo, hi)
    if m is None:
        return None
    close = _matching_brace(text, m.end() - 1)
    if close < 0 or close > hi:
        return None
    return m.end(), close


def _replace_in_span(text, span, key, rendered, is_list):
    lo, hi = span
    body = text[lo:hi]
    if is_list:
        pat = re.compile(r'^([ \t]*"%s"[ \t]*:[ \t]*)(\[[^\]]*\])'
                         % re.escape(key), re.M)
    else:
        pat = re.compile(r'^([ \t]*"%s"[ \t]*:[ \t]*)([^\r\n]*?)'
                         r'([ \t]*,[ \t]*(?:#[^\r\n]*)?)(\r?)$'
                         % re.escape(key), re.M)
    found = pat.findall(body)
    if len(found) != 1:
        return None, len(found)
    new_body = pat.sub(lambda m: m.group(1) + rendered + m.group(0)[
        len(m.group(1)) + len(m.group(2)):], body, count=1)
    return text[:lo] + new_body + text[hi:], 1


def save_to_bridge_utils(changes, path=None):
    """
    Write changed values back into bridge_utils.py.

    Returns
    -------
    list of str  error messages; empty = everything saved.
    """
    if not changes:
        return []
    if path is None:
        path = bridge_utils_path()
    errors = []
    try:
        f = codecs.open(path, "r", "utf-8")
        try:
            text = f.read()
        finally:
            f.close()
    except Exception as e:
        return [tr("Kan '{0}' niet lezen: {1}",
                   "Cannot read '{0}': {1}").format(path, e)]

    for analysis, key, kind, _old, new in changes:
        cfg_span = _block_span(text, r'^CONFIG_BRIDGE[ \t]*=[ \t]*\{')
        if cfg_span is None:
            errors.append(tr("CONFIG_BRIDGE-blok niet gevonden.",
                             "CONFIG_BRIDGE block not found."))
            break
        ana_span = _block_span(text, r'^[ \t]*"analyses"[ \t]*:[ \t]*\{',
                               cfg_span[0], cfg_span[1])
        rendered = _render_value(new, kind)
        is_list  = kind == "checklist"
        if analysis is None:
            # General key: only search outside the "analyses" block,
            # so that an analysis key with the same name does not count.
            where = "CONFIG_BRIDGE"
            if ana_span is None:
                new_text, count = _replace_in_span(
                    text, cfg_span, key, rendered, is_list)
            else:
                outside = [(cfg_span[0], ana_span[0]),
                           (ana_span[1], cfg_span[1])]
                results = [_replace_in_span(text, s, key, rendered, is_list)
                           for s in outside]
                count = sum(n for _t, n in results)
                hits  = [t for t, n in results if t is not None]
                new_text = hits[0] if count == 1 else None
        else:
            span = None
            if ana_span is not None:
                span = _block_span(
                    text, r'^[ \t]*"%s"[ \t]*:[ \t]*\{' % re.escape(analysis),
                    ana_span[0], ana_span[1])
            where = "analyses['{0}']".format(analysis)
            if span is None:
                errors.append(tr("Blok {0} niet gevonden.",
                                 "Block {0} not found.").format(where))
                continue
            new_text, count = _replace_in_span(
                text, span, key, rendered, is_list)
        if new_text is None:
            errors.append(tr(
                "Sleutel '{0}' in {1}: {2}x gevonden i.p.v. 1x; niet "
                "opgeslagen.",
                "Key '{0}' in {1}: found {2}x instead of 1x; not "
                "saved.").format(key, where, count))
            continue
        text = new_text

    # Syntax check before writing. The coding declaration is
    # made harmless for the check (compile() on unicode text
    # with a coding line gives a SyntaxError in Python 2).
    check = text.lstrip(u"﻿")
    check = re.sub(r"coding[:=]", "coding-", check, count=1)
    try:
        compile(check, path, "exec")
    except SyntaxError as e:
        errors.append(tr("Resultaat zou ongeldige Python zijn (regel {0}); "
                         "bridge_utils.py NIET gewijzigd.",
                         "Result would be invalid Python (line {0}); "
                         "bridge_utils.py NOT changed.").format(e.lineno))
        return errors

    try:
        shutil.copy2(path, path + ".bak")
        f = codecs.open(path, "w", "utf-8")
        try:
            f.write(text)
        finally:
            f.close()
    except Exception as e:
        errors.append(tr("Schrijven naar '{0}' mislukt: {1}",
                         "Writing to '{0}' failed: {1}").format(path, e))
    return errors


# ==========================================
# WINDOWS FORMS DIALOG
# ==========================================
class _Look(object):
    """
    Fonts, colours and styled buttons/headings for the windows
    (_STYLE). Can only be made after Windows Forms is loaded.
    """

    def __init__(self):
        from System.Drawing import Font, FontStyle, Color
        from System.Windows.Forms import FlatStyle, Cursors
        self._FlatStyle = FlatStyle
        self._Cursors = Cursors
        name, size = _STYLE["font"]
        self.font = Font(name, size)
        self.bold = Font(name, size, FontStyle.Bold)
        self.title = Font(name, 13.0, FontStyle.Bold)
        self.section = Font(name, 10.0, FontStyle.Bold)
        self.caption = Font(name, 8.0, FontStyle.Bold)

        def col(key):
            r, g, b = _STYLE[key]
            return Color.FromArgb(r, g, b)
        self.col = col
        self.white = Color.White

    def button(self, text, primary=False):
        """Flat button; primary = filled with the accent colour."""
        from System.Windows.Forms import Button
        btn = Button()
        btn.Text = text
        btn.FlatStyle = self._FlatStyle.Flat
        btn.Cursor = self._Cursors.Hand
        btn.Height = 32
        if primary:
            btn.BackColor = self.col("accent")
            btn.ForeColor = self.white
            btn.FlatAppearance.BorderColor = self.col("accent")
            btn.FlatAppearance.MouseOverBackColor = self.col("accent_hover")
            btn.Font = self.bold
        else:
            btn.BackColor = self.col("button_bg")
            btn.FlatAppearance.BorderColor = self.col("line")
            btn.FlatAppearance.MouseOverBackColor = self.col("status_bg")
        return btn

    def header(self, form, title, subtitle):
        """Dark header bar at the top of the window (Dock Top)."""
        from System.Windows.Forms import Panel, Label, DockStyle
        from System.Drawing import Point, Size
        bar = Panel()
        bar.Dock = DockStyle.Top
        bar.Height = 58
        bar.BackColor = self.col("header_bg")
        t = Label()
        t.Text = title
        t.Font = self.title
        t.ForeColor = self.col("header_fg")
        t.AutoSize = True
        t.Location = Point(16, 8)
        bar.Controls.Add(t)
        s = Label()
        s.Text = subtitle
        s.ForeColor = self.col("header_sub")
        s.AutoSize = True
        s.Location = Point(18, 34)
        bar.Controls.Add(s)
        form.Controls.Add(bar)
        return bar


def _show_winforms_dialog(current, status=u"", model=None):
    """
    Show the main window: navigation on the left with the settings pages
    (with tooltips, bridge_glossary) and the page Documentatie (bridge_docs),
    a status box (status: text about the previous run) and the buttons
    Starten, Resultaten..., Convergentiescherm, Uitleg... and Sluiten.

    Returns {"action": "run" | "results" | "close", "values": dict or None}
    ("values" only for "run": the validated new values). The
    convergence screen and the documentation work inside the window; for
    a run or the results the window closes and MecwayAsterBridgeMain
    opens it again afterwards. Errors when loading Windows Forms are
    passed on as ImportError; errors in the window itself as RuntimeError.
    """
    try:
        import clr
        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
        from System.Windows.Forms import (
            Form, Label, TextBox, Button, ComboBox,
            ComboBoxStyle, CheckBox, CheckedListBox, DialogResult,
            FormBorderStyle, FormStartPosition, OpenFileDialog,
            FolderBrowserDialog, MessageBox, MessageBoxButtons,
            MessageBoxIcon, ToolTip, ListBox, ScrollBars, Application,
            Panel, DockStyle, BorderStyle, Padding)
        from System.Drawing import Point, Size
        from System.Threading import Thread, ThreadStart, ApartmentState
    except Exception as e:
        raise ImportError(tr("Windows Forms niet beschikbaar: {0}",
                             "Windows Forms not available: {0}").format(e))

    result = {"action": "close", "values": None, "error": None}

    def build_and_run():
        try:
            look = _Look()
            form = Form()
            form.Text = "MecwayAsterBridge"
            form.Font = look.font
            form.BackColor = look.col("window_bg")
            # Fits with border and title bar on a screen 768 high; dragging
            # it larger is allowed (fields and buttons move along). Wider than
            # with tabs: the navigation list on the left takes _STYLE["nav_w"].
            form.ClientSize = Size(1120, 700)
            form.MinimumSize = Size(1000, 600)
            form.StartPosition = FormStartPosition.CenterScreen
            form.FormBorderStyle = FormBorderStyle.Sizable
            form.MinimizeBox = False
            # On top of Mecway when opening, after that a normal window.
            form.TopMost = True

            # Tooltips with an explanation per setting (bridge_glossary);
            # visible for long, because the texts are sometimes a few lines.
            tip = ToolTip()
            tip.AutoPopDelay = 30000
            tip.InitialDelay = 400
            tip.ReshowDelay = 200
            tip.ShowAlways = True

            active = current["general"]["active_analysis"]
            subtitle = tr("Mecway naar Code-Aster", "Mecway to Code-Aster")
            if model:
                subtitle += u"   •   " + tr(u"model: {0}",
                                                 u"model: {0}").format(
                    os.path.basename(model))
            subtitle += u"   •   " + tr(u"analyse: {0}",
                                             u"analysis: {0}").format(
                _analysis_title(active) if active != "auto" else "auto")
            header = look.header(form, u"MecwayAsterBridge " +
                                 BRIDGE_VERSION, subtitle)

            # Main part (navigation left, page right), status box and
            # button bar. Docking goes from back to front in the
            # z-order: button bar at the bottom, status box above it, header
            # at the top, the main part fills the rest.
            body = Panel()
            body.Dock = DockStyle.Fill
            body.Padding = Padding(12, 10, 12, 4)
            form.Controls.Add(body)
            status_panel = Panel()
            status_panel.Dock = DockStyle.Bottom
            status_panel.Height = 88
            status_panel.Padding = Padding(12, 2, 12, 4)
            form.Controls.Add(status_panel)
            footer = Panel()
            footer.Dock = DockStyle.Bottom
            footer.Height = 56
            footer.BackColor = look.col("page_bg")
            form.Controls.Add(footer)
            body.BringToFront()
            header.SendToBack()
            status_panel.SendToBack()
            footer.SendToBack()

            # --- Navigation on the left, chosen page on the right ---
            # Like Windows Settings: a self-drawn list with the
            # page names (group headings above them), on the right the title
            # and the content of the chosen page. new_page() is the only
            # registration point: every page appears in the list by itself.
            # Keyboard: arrows/Home/End in the list (which has the focus
            # when opening), Ctrl+Tab/Ctrl+Shift+Tab and Ctrl+PageDown/
            # PageUp from the whole window (as with tabs).
            from System.Windows.Forms import (DrawMode, TextRenderer,
                                              TextFormatFlags, DrawItemState,
                                              Keys)
            from System.Drawing import SolidBrush, Rectangle, ContentAlignment
            GROUP_SETTINGS = tr("Instellingen", "Settings")
            GROUP_ANALYSES = tr("Analyses", "Analyses")
            GROUP_HELP = tr("Hulp", "Help")

            page_frame = Panel()   # thin border around the page
            page_frame.Dock = DockStyle.Fill
            page_frame.BackColor = look.col("line")
            page_frame.Padding = Padding(1)
            page_frame.TabIndex = 1
            nav_gap = Panel()
            nav_gap.Dock = DockStyle.Left
            nav_gap.Width = 10
            nav = ListBox()
            nav.Name = "nav"
            nav.Dock = DockStyle.Left
            nav.Width = _STYLE["nav_w"]
            nav.BorderStyle = getattr(BorderStyle, "None")
            nav.BackColor = look.col("window_bg")
            nav.IntegralHeight = False
            nav.DrawMode = DrawMode.OwnerDrawVariable
            nav.TabIndex = 0
            # Docking from back to front: list on the left, spacing, the
            # page fills the rest.
            body.Controls.Add(page_frame)
            body.Controls.Add(nav_gap)
            body.Controls.Add(nav)

            page_area = Panel()
            page_area.Dock = DockStyle.Fill
            page_area.BackColor = look.col("page_bg")
            page_frame.Controls.Add(page_area)
            page_host = Panel()    # the pages (one visible at a time)
            page_host.Name = "pages"
            page_host.Dock = DockStyle.Fill
            page_area.Controls.Add(page_host)
            title_line = Panel()
            title_line.Dock = DockStyle.Top
            title_line.Height = 1
            title_line.BackColor = look.col("line")
            page_area.Controls.Add(title_line)
            page_title = Label()
            page_title.Dock = DockStyle.Top
            page_title.Height = 40
            page_title.Padding = Padding(10, 0, 0, 0)
            page_title.Font = look.title
            page_title.ForeColor = look.col("header_bg")
            page_title.AutoEllipsis = True
            page_title.TextAlign = ContentAlignment.MiddleLeft
            page_area.Controls.Add(page_title)

            pages = []   # per page {"page", "title", "group"}, in order
            nav_state = {"hover": -1}

            def new_page(title, group):
                """New page with a line in the navigation (under the
                group heading group); returns the Panel."""
                page = Panel()
                page.Dock = DockStyle.Fill
                page.AutoScroll = True
                page.BackColor = look.col("page_bg")
                page.Visible = False
                page_host.Controls.Add(page)
                pages.append({"page": page, "title": title, "group": group})
                nav.Items.Add(title)
                return page

            def page_index(page):
                for i, p in enumerate(pages):
                    if p["page"] is page:
                        return i
                return -1

            def set_page_title(page, title):
                k = page_index(page)
                if k >= 0:
                    pages[k]["title"] = title
                    if k == nav.SelectedIndex:
                        page_title.Text = title
                    nav.Invalidate()

            def select_page(page):
                k = page_index(page)
                if k >= 0:
                    nav.SelectedIndex = k

            def group_start(i):
                return i == 0 or pages[i]["group"] != pages[i - 1]["group"]

            def caption_h(i):
                # Space for the group heading above the first page of a
                # group (a bit less at the top).
                if not group_start(i):
                    return 0
                return _STYLE["nav_caption_h"] - (6 if i == 0 else 0)

            def on_nav_measure(sender, e):
                if 0 <= e.Index < len(pages):
                    e.ItemHeight = _STYLE["nav_row_h"] + caption_h(e.Index)

            def on_nav_draw(sender, e):
                i = e.Index
                if i < 0 or i >= len(pages):
                    return
                g = e.Graphics
                b = e.Bounds
                brush = SolidBrush(look.col("window_bg"))
                g.FillRectangle(brush, b)
                brush.Dispose()
                top = b.Y + caption_h(i)
                if top > b.Y:
                    TextRenderer.DrawText(
                        g, pages[i]["group"].upper(), look.caption,
                        Rectangle(b.X + 12, b.Y, b.Width - 16,
                                  top - b.Y - 4),
                        look.col("muted"),
                        TextFormatFlags.Bottom | TextFormatFlags.Left |
                        TextFormatFlags.SingleLine |
                        TextFormatFlags.EndEllipsis)
                r = Rectangle(b.X + 2, top + 1, b.Width - 4,
                              b.Bottom - top - 2)
                selected = (e.State & DrawItemState.Selected) == \
                    DrawItemState.Selected
                if selected or i == nav_state["hover"]:
                    brush = SolidBrush(look.col("page_bg") if selected
                                       else look.col("status_bg"))
                    g.FillRectangle(brush, r)
                    brush.Dispose()
                if selected:
                    # accent bar on the left, as in Windows Settings
                    brush = SolidBrush(look.col("accent"))
                    g.FillRectangle(brush, Rectangle(r.X, r.Y + 6, 3,
                                                     r.Height - 12))
                    brush.Dispose()
                TextRenderer.DrawText(
                    g, pages[i]["title"],
                    look.bold if selected else look.font,
                    Rectangle(r.X + 14, r.Y, r.Width - 18, r.Height),
                    look.col("accent") if selected else
                    look.col("header_bg"),
                    TextFormatFlags.VerticalCenter | TextFormatFlags.Left |
                    TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis)

            def set_hover(k):
                old = nav_state["hover"]
                if k == old:
                    return
                nav_state["hover"] = k
                for j in (old, k):
                    if 0 <= j < nav.Items.Count:
                        nav.Invalidate(nav.GetItemRectangle(j))

            def on_nav_move(sender, e):
                set_hover(nav.IndexFromPoint(e.Location))

            def on_nav_leave(sender, args):
                set_hover(-1)

            def on_nav_selected(sender, args):
                k = nav.SelectedIndex
                if not 0 <= k < len(pages):
                    return
                shown = pages[k]["page"]
                page_title.Text = pages[k]["title"]
                shown.Visible = True
                shown.BringToFront()
                for p in pages:
                    if p["page"] is not shown:
                        p["page"].Visible = False
                if shown in stretch:
                    fit_page(shown)

            def on_form_key(sender, e):
                # Ctrl+Tab / Ctrl+PageDown: next page; with Shift or
                # PageUp: previous (wrapping around).
                if not e.Control or not pages:
                    return
                if e.KeyCode == Keys.Tab:
                    step = -1 if e.Shift else 1
                elif e.KeyCode == Keys.Next:
                    step = 1
                elif e.KeyCode == Keys.Prior:
                    step = -1
                else:
                    return
                k = nav.SelectedIndex if nav.SelectedIndex >= 0 else 0
                nav.SelectedIndex = (k + step) % len(pages)
                e.Handled = True
                e.SuppressKeyPress = True

            nav.MeasureItem += on_nav_measure
            nav.DrawItem += on_nav_draw
            nav.MouseMove += on_nav_move
            nav.MouseLeave += on_nav_leave
            form.KeyPreview = True
            form.KeyDown += on_form_key

            page_gen = new_page(tr("Algemeen", "General"), GROUP_SETTINGS)
            page_elem = new_page(tr("Elementen", "Elements"), GROUP_SETTINGS)
            # One page per analysis; the active one gets "(actief)".
            analysis_pages = {}
            for name in _analysis_names():
                analysis_pages[name] = new_page(_page_title(name, active),
                                                GROUP_ANALYSES)

            controls = []   # (analysis_or_None, key, label, kind, extra, ctrl)
            # Per page the elements that follow the width:
            # (kind, element, button or None); see fit_page.
            stretch = {}
            sections = {}   # page -> shown headings
            x_ctrl = 16 + _STYLE["label_w"]

            def fit_page(page):
                w = page.ClientSize.Width
                for kind, ctrl, btn in stretch.get(page, []):
                    if kind == "path":
                        btn.Left = w - 16 - btn.Width
                        ctrl.Width = max(160, btn.Left - 8 - ctrl.Left)
                    else:
                        ctrl.Width = max(200, w - 16 - ctrl.Left)

            def make_fit(page):
                def handler(sender, args):
                    fit_page(page)
                return handler

            def make_browse(textbox, kind, flt):
                def handler(sender, args):
                    cur = expand_path(textbox.Text)
                    if kind == "folder":
                        dlg = FolderBrowserDialog()
                        dlg.Description = tr("Kies de werkmap",
                                             "Choose the work folder")
                        if os.path.isdir(cur):
                            dlg.SelectedPath = cur
                        if dlg.ShowDialog(form) == DialogResult.OK:
                            textbox.Text = dlg.SelectedPath
                    else:
                        dlg = OpenFileDialog()
                        dlg.Filter = _t(flt)
                        dlg.CheckFileExists = True
                        if cur:
                            d = os.path.dirname(cur)
                            if os.path.isdir(d):
                                dlg.InitialDirectory = d
                            dlg.FileName = os.path.basename(cur)
                        if dlg.ShowDialog(form) == DialogResult.OK:
                            textbox.Text = dlg.FileName
                return handler

            def add_section(parent, y, key):
                """Heading above the first setting of a group."""
                title = SECTION_BEFORE.get(key)
                shown = sections.setdefault(parent, set())
                if title is None or title in shown:
                    return y
                shown.add(title)
                if shown and y > 16:
                    y += 10
                lbl = Label()
                lbl.Text = _t(title)
                lbl.Font = look.section
                lbl.ForeColor = look.col("accent")
                lbl.AutoSize = True
                lbl.Location = Point(14, y)
                parent.Controls.Add(lbl)
                line = Panel()
                line.BackColor = look.col("line")
                line.Location = Point(16, y + 24)
                line.Size = Size(600, 1)
                parent.Controls.Add(line)
                stretch.setdefault(parent, []).append(("line", line, None))
                return y + 34

            def make_row(parent, y, analysis, key, label, kind, extra, value):
                y = add_section(parent, y, key)
                label = _t(label)
                lbl = Label()
                lbl.Text = label
                lbl.AutoEllipsis = True
                lbl.Location = Point(16, y + 3)
                lbl.Size = Size(_STYLE["label_w"] - 12, 20)
                parent.Controls.Add(lbl)
                x = x_ctrl
                height = _STYLE["row_h"]
                if kind in ("text", "int", "float_pos", "float_range",
                            "file", "folder"):
                    ctrl = TextBox()
                    ctrl.Location = Point(x, y)
                    ctrl.Width = 420 if kind in ("file", "folder") else 220
                    ctrl.Text = _format_value(value, kind)
                    if key == "work_dir" and not value:
                        # empty = default folder: show it (save as "")
                        ctrl.Text = default_work_dir()
                    if kind in ("file", "folder"):
                        btn = look.button(tr("Bladeren...", "Browse..."))
                        btn.Height = 25
                        btn.Width = 100
                        btn.Location = Point(x + 428, y - 1)
                        btn.Click += make_browse(ctrl, kind, extra)
                        parent.Controls.Add(btn)
                        stretch.setdefault(parent, []).append(
                            ("path", ctrl, btn))
                elif kind in _CHOICE_KINDS:
                    ctrl = ComboBox()
                    ctrl.DropDownStyle = ComboBoxStyle.DropDownList
                    ctrl.Location = Point(x, y)
                    ctrl.Width = 220
                    opts = _choice_options(kind, extra)
                    if key == "schema" and analysis in _SCHEMES:
                        # Implicit or explicit: only the matching
                        # schemes (the others would use hidden settings
                        # of the other kind).
                        opts = [o for o in opts if o in _SCHEMES[analysis]]
                    if value not in opts:
                        opts.append(value)   # unknown value visible
                    for o in opts:
                        ctrl.Items.Add(o)
                    ctrl.SelectedItem = value
                elif kind == "bool":
                    ctrl = CheckBox()
                    ctrl.Location = Point(x, y + 2)
                    ctrl.Size = Size(24, 22)
                    ctrl.Checked = bool(value)
                elif kind == "checklist":
                    ctrl = CheckedListBox()
                    ctrl.CheckOnClick = True
                    ctrl.BorderStyle = BorderStyle.FixedSingle
                    ctrl.IntegralHeight = False
                    ctrl.Location = Point(x, y)
                    ctrl.Size = Size(280, 132)
                    for o in _field_options(value):
                        ctrl.Items.Add(o, o in value)
                    height = 142
                else:
                    raise RuntimeError(tr("Onbekend soort '{0}'.",
                                          "Unknown kind '{0}'.").format(kind))
                parent.Controls.Add(ctrl)
                if kind in _CHOICE_KINDS:
                    options = _choice_options(kind, extra)
                elif kind == "checklist":
                    # explanation per result field (GLOSSARY) in the tooltip
                    options = _field_options(value)
                else:
                    options = []
                if key == "schema" and analysis in _SCHEMES:
                    options = [o for o in options if o in _SCHEMES[analysis]]
                help_text = bridge_glossary.setting_tooltip(key, options, tr)
                if help_text:
                    tip.SetToolTip(lbl, help_text)
                    tip.SetToolTip(ctrl, help_text)
                controls.append((analysis, key, label, kind, extra, ctrl))
                return y + height

            def add_text(parent, y, text, height=None):
                """Note in a muted colour over the full width;
                height None: follows from the number of lines."""
                if height is None:
                    height = 16 * (text.count("\n") + 1) + 8
                lbl = Label()
                lbl.Text = text
                lbl.ForeColor = look.col("muted")
                lbl.Location = Point(16, y)
                lbl.Size = Size(700, height)
                parent.Controls.Add(lbl)
                stretch.setdefault(parent, []).append(("text", lbl, None))
                return y + height

            # --- Pages Algemeen and Elementen ---
            y_gen = 12
            y_elem = 12
            for key, label, kind, extra in GENERAL_SPECS:
                if key in ELEMENT_KEYS:
                    y_elem = make_row(page_elem, y_elem, None, key, label,
                                      kind, extra, current["general"][key])
                else:
                    y_gen = make_row(page_gen, y_gen, None, key, label, kind,
                                     extra, current["general"][key])
            auto_lines = [u"  \u2022 {0}: {1}".format(t, _analysis_title(n))
                          for t, n in sorted(MECWAY_ANALYSIS_TYPES.items())]
            y_gen = add_text(
                page_gen, y_gen + 12,
                tr(u"Actieve analyse 'auto' volgt het analysetype van het "
                   u"Mecway-model:\n{0}\nAndere typen stoppen de bridge met "
                   u"een melding.",
                   u"Active analysis 'auto' follows the analysis type of "
                   u"the Mecway model:\n{0}\nOther types stop the bridge "
                   u"with a message.").format(u"\n".join(auto_lines)))
            y_gen = add_text(
                page_gen, y_gen + 6,
                tr(u"Taal / Language\n"
                   u"  \u2022 Geldt direct voor de run (meldingen, logbestand, "
                   u"convergentiescherm).\n"
                   u"  \u2022 Dit venster wisselt van taal als het na de run "
                   u"terugkomt.",
                   u"Taal / Language\n"
                   u"  \u2022 Applies to the run straight away (messages, log "
                   u"file, convergence window).\n"
                   u"  \u2022 This window switches language when it comes back "
                   u"after the run."))
            add_text(page_gen, y_gen + 6,
                     tr(u"Opslaan\n"
                        u"  \u2022 Wijzigingen worden bij Starten en "
                        u"Resultaten... opgeslagen in:\n     {0}\n"
                        u"  \u2022 Vorige versie: bridge_utils.py.bak",
                        u"Saving\n"
                        u"  \u2022 Changes are saved on Start and Results... "
                        u"in:\n     {0}\n"
                        u"  \u2022 Previous version: bridge_utils.py.bak").format(
                            bridge_utils_path()))
            add_text(page_elem, y_elem + 12, tr(*_ELEMENT_HELP))

            # --- One page per analysis ---
            for name in _analysis_names():
                page = analysis_pages[name]
                # The template follows from the analysis (bridge_utils.
                # template_path: name in the Scripts folder); display only.
                info = "Code-Aster: {0}   |   template: {1}".format(
                    CONFIG_BRIDGE["analyses"][name].get("solver_command",
                                                        "?"),
                    _template_label(CONFIG_BRIDGE["analyses"][name].get(
                        "template", "")))
                mtypes = _mecway_types_for(name)
                if mtypes:
                    info += tr("   |   gekozen bij 'auto' voor Mecway-"
                               "analysetype {0}",
                               "   |   chosen with 'auto' for Mecway "
                               "analysis type {0}").format(", ".join(mtypes))
                y = add_text(page, 10, info, 20) + 8
                for key, label, kind, extra in ANALYSIS_SPECS:
                    if key in current["analyses"][name]:
                        y = make_row(page, y, name, key, label, kind,
                                     extra, current["analyses"][name][key])

            # Page titles follow the choice of the active analysis.
            def make_active_handler(combo):
                def handler(sender, args):
                    chosen = "{0}".format(combo.SelectedItem)
                    for n, pg in analysis_pages.items():
                        set_page_title(pg, _page_title(n, chosen))
                return handler

            for analysis, key, _l, _k, _e, ctrl in controls:
                if analysis is None and key == "active_analysis":
                    ctrl.SelectedIndexChanged += make_active_handler(ctrl)

            # --- Page Documentatie (bridge_docs) ---
            page_docs = new_page(tr("Documentatie", "Documentation"), GROUP_HELP)
            page_docs.AutoScroll = False
            page_docs.Padding = Padding(8)
            doc_items = bridge_docs.doc_list(tr)
            doc_state = {"current": doc_items[0][1], "browser": None}
            doc_list = ListBox()
            doc_list.Dock = DockStyle.Left
            doc_list.Width = 230
            doc_list.BorderStyle = getattr(BorderStyle, "None")
            doc_list.BackColor = look.col("status_bg")
            doc_list.IntegralHeight = False
            # Self-drawn: wider lines, selection in the accent colour.
            doc_list.DrawMode = DrawMode.OwnerDrawFixed
            doc_list.ItemHeight = 28
            for title, _rel in doc_items:
                doc_list.Items.Add(title)
            page_docs.Controls.Add(doc_list)

            def on_draw_doc(sender, e):
                if e.Index < 0:
                    return
                selected = (e.State & DrawItemState.Selected) == \
                    DrawItemState.Selected
                back = look.col("accent") if selected else \
                    look.col("status_bg")
                fore = look.white if selected else look.col("header_bg")
                brush = SolidBrush(back)
                e.Graphics.FillRectangle(brush, e.Bounds)
                brush.Dispose()
                r = Rectangle(e.Bounds.X + 10, e.Bounds.Y,
                              e.Bounds.Width - 14, e.Bounds.Height)
                TextRenderer.DrawText(
                    e.Graphics, "{0}".format(doc_list.Items[e.Index]),
                    look.font, r, fore,
                    TextFormatFlags.VerticalCenter | TextFormatFlags.Left |
                    TextFormatFlags.EndEllipsis)
            doc_list.DrawItem += on_draw_doc
            try:
                from System.Windows.Forms import WebBrowser
                browser = WebBrowser()
                browser.ScriptErrorsSuppressed = True
                browser.AllowWebBrowserDrop = False
            except Exception:
                # Without a browser element: plain text (the Markdown itself).
                browser = None
            viewer = browser if browser is not None else TextBox()
            if browser is None:
                viewer.Multiline = True
                viewer.ReadOnly = True
                viewer.ScrollBars = ScrollBars.Vertical
            gap = Panel()
            gap.Dock = DockStyle.Left
            gap.Width = 8
            page_docs.Controls.Add(gap)
            viewer.Dock = DockStyle.Fill
            page_docs.Controls.Add(viewer)
            # Trademark notice at the bottom, over the full width
            notice = Label()
            notice.Text = tr(*bridge_docs.TRADEMARK_NOTICE)
            notice.ForeColor = look.col("muted")
            notice.Dock = DockStyle.Bottom
            # two lines of space: in a narrow window the text wraps
            notice.Height = 38
            notice.Padding = Padding(4, 6, 4, 0)
            page_docs.Controls.Add(notice)
            # docking from back to front: notice at the bottom, list
            # on the left, then the spacing, the viewer fills the rest
            viewer.BringToFront()
            doc_list.SendToBack()
            notice.SendToBack()
            doc_state["browser"] = browser

            def show_doc(rel):
                doc_state["current"] = rel
                html = bridge_docs.doc_html(rel, tr)
                if browser is not None:
                    browser.DocumentText = html
                else:
                    body = html[html.find("<body>"):]
                    text = re.sub(r"<[^>]+>", "", body)
                    viewer.Text = (text.replace("&lt;", "<")
                                   .replace("&gt;", ">")
                                   .replace("&amp;", "&")
                                   .replace("\n", "\r\n"))

            def on_doc_selected(sender, args):
                k = doc_list.SelectedIndex
                if 0 <= k < len(doc_items):
                    try:
                        show_doc(doc_items[k][1])
                    except Exception as e:
                        say(tr("Document niet getoond: {0}",
                               "Document not shown: {0}").format(e))
            doc_list.SelectedIndexChanged += on_doc_selected

            def scroll_to(anchor):
                try:
                    el = browser.Document.GetElementById(anchor)
                    if el is not None:
                        el.ScrollIntoView(True)
                except Exception:
                    pass

            def on_navigating(sender, args):
                # DocumentText loads as about:blank; a relative link
                # becomes about:<href> (an anchor about:blank#<id>). Links to
                # .md open here (with anchor), anchors scroll, web addresses
                # go to the default browser, the rest does not.
                url = "{0}".format(args.Url)
                if url in ("about:blank", ""):
                    return
                args.Cancel = True
                try:
                    href = url
                    if url.startswith("about:blank"):
                        href = url[len("about:blank"):]
                    elif url.startswith("about:"):
                        href = url[len("about:"):]
                    kind, target, anchor = bridge_docs.resolve_link(
                        doc_state["current"], href)
                    if kind == "anchor":
                        scroll_to(anchor)
                    elif kind == "doc":
                        doc_state["anchor"] = anchor
                        rels = [r for _t, r in doc_items]
                        if target in rels:
                            if doc_list.SelectedIndex == rels.index(target):
                                show_doc(target)
                            else:
                                doc_list.SelectedIndex = rels.index(target)
                        else:
                            # Outside the list: no selection, so that a click
                            # in the list goes to a document again.
                            doc_list.ClearSelected()
                            show_doc(target)
                    elif kind == "web":
                        from System.Diagnostics import Process
                        Process.Start(target)
                except Exception as e:
                    say(tr("Link niet geopend: {0}",
                           "Link not opened: {0}").format(e))

            def on_completed(sender, args):
                # After loading, jump to the anchor of the link.
                anchor = doc_state.pop("anchor", None)
                if anchor:
                    scroll_to(anchor)
            if browser is not None:
                browser.Navigating += on_navigating
                browser.DocumentCompleted += on_completed

            # --- Status box: outcome of the previous run and messages ---
            status_title = Label()
            status_title.Text = tr("Status", "Status")
            status_title.Font = look.bold
            status_title.ForeColor = look.col("muted")
            status_title.Dock = DockStyle.Top
            status_title.Height = 20
            status_card = Panel()
            status_card.Dock = DockStyle.Fill
            status_card.BackColor = look.col("status_bg")
            status_card.Padding = Padding(10, 6, 6, 6)
            status_panel.Controls.Add(status_card)
            status_panel.Controls.Add(status_title)
            status_box = TextBox()
            status_box.Multiline = True
            status_box.ReadOnly = True
            status_box.BorderStyle = getattr(BorderStyle, "None")
            status_box.BackColor = look.col("status_bg")
            status_box.ScrollBars = ScrollBars.Vertical
            status_box.Dock = DockStyle.Fill
            status_box.Text = (exe_missing_text() + (status or tr(
                "Kies de instellingen en klik Starten. Ga met de muis over "
                "een instelling voor uitleg; codes en namen staan onder "
                "Uitleg... en op de pagina Documentatie.",
                "Choose the settings and click Start. Hover over a setting "
                "for an explanation; codes and names are under "
                "Explanation... and on the Documentation page."))
            ).replace("\r\n", "\n").replace("\n", "\r\n")
            status_card.Controls.Add(status_box)

            def say(text):
                status_box.Text = text.replace("\r\n", "\n").replace(
                    "\n", "\r\n")

            # --- Buttons: helper buttons on the left, on the right Sluiten
            # and the primary button Starten (fit_footer places them) ---
            footer_line = Panel()
            footer_line.Dock = DockStyle.Top
            footer_line.Height = 1
            footer_line.BackColor = look.col("line")
            footer.Controls.Add(footer_line)
            left_buttons = []
            right_buttons = []

            def add_button(text, width, handler, help_text, right=False,
                           primary=False):
                btn = look.button(text, primary)
                btn.Width = width
                btn.Top = 13
                if handler is not None:
                    btn.Click += handler
                tip.SetToolTip(btn, help_text)
                footer.Controls.Add(btn)
                (right_buttons if right else left_buttons).append(btn)
                return btn

            def fit_footer(sender=None, args=None):
                x = 16
                for b in left_buttons:
                    b.Left = x
                    x += b.Width + 8
                x = footer.ClientSize.Width - 16
                for b in right_buttons:
                    x -= b.Width
                    b.Left = x
                    x -= 8
            footer.Resize += fit_footer

            def collect_values():
                """Validated values of all fields, or None (then a
                message has been shown)."""
                values = {"general": {}, "analyses": {}}
                errors = []
                for analysis, key, label, kind, extra, ctrl in controls:
                    if kind == "bool":
                        raw = bool(ctrl.Checked)
                    elif kind in _CHOICE_KINDS:
                        raw = "{0}".format(ctrl.SelectedItem)
                    elif kind == "checklist":
                        raw = [ "{0}".format(ctrl.Items[i])
                                for i in range(ctrl.Items.Count)
                                if ctrl.GetItemChecked(i) ]
                    else:
                        raw = ctrl.Text
                    value, err = _parse_and_validate(key, kind, extra, raw)
                    where = _where(analysis, key)
                    if err:
                        errors.append("[{0}] {1}: {2}".format(
                            where, label, err))
                    elif analysis is None:
                        values["general"][key] = value
                    else:
                        values["analyses"].setdefault(
                            analysis, {})[key] = value
                if errors:
                    MessageBox.Show(form, "\n".join(errors),
                                    tr("Controleer de invoer",
                                       "Check the input"),
                                    MessageBoxButtons.OK,
                                    MessageBoxIcon.Warning)
                    return None
                return values

            def guarded(fn):
                # An error in a button must not close the window (the
                # .NET error dialog offers 'Afsluiten'): report it in the
                # status box.
                def handler(sender, args):
                    try:
                        fn()
                    except Exception as e:
                        say(tr("Fout: {0}", "Error: {0}").format(e))
                return handler

            def leave(action):
                # Starten and Resultaten take the changed settings
                # along (also Resultaten, otherwise they are gone when the
                # window comes back).
                values = collect_values()
                if values is None:
                    return
                result["values"] = values
                result["action"] = action
                form.Close()

            def field_text(key):
                for analysis, k, _l, _kind, _e, ctrl in controls:
                    if analysis is None and k == key:
                        return ctrl.Text.strip()
                return CONFIG_BRIDGE.get(key, "")

            on_ok = guarded(lambda: leave("run"))
            on_results = guarded(lambda: leave("results"))
            on_monitor = guarded(lambda: say(open_convergence_monitor(
                expand_path(field_text("work_dir")), model)))

            def explain():
                select_page(page_docs)
                doc_list.SelectedIndex = 0
            on_explain = guarded(explain)

            add_button(tr("Resultaten...", "Results..."), 120, on_results, tr(
                "Resultaten van een eerdere run inladen, of de resultaten "
                "uit het model halen (kleine .liml).",
                "Load the results of an earlier run, or remove the results "
                "from the model (small .liml)."))
            add_button(tr("Convergentiescherm", "Convergence window"), 160,
                       on_monitor, tr(
                "Opent het convergentie- en meldingenscherm (apart venster) "
                "voor de laatste run van het open model in de werkmap (geen "
                "run van dit model: de nieuwste run daar); het blijft open "
                "naast Mecway.",
                "Opens the convergence and messages window (separate "
                "window) for the latest run of the open model in the work "
                "folder (no run of this model: the newest run there); it "
                "stays open next to Mecway."))
            add_button(tr("Uitleg...", "Explanation..."), 110, on_explain,
                       tr("Uitleg van codes en namen (woordenlijst) op de "
                          "pagina Documentatie.",
                          "Explanation of codes and names (glossary) on the "
                          "Documentation page."))
            ok_btn = add_button(tr("Starten", "Start"), 130, on_ok, tr(
                "Instellingen opslaan, het model opslaan en Code-Aster "
                "starten. Na de run komt dit venster terug.",
                "Save the settings, save the model and start Code-Aster. "
                "This window returns after the run."), right=True,
                primary=True)
            cancel_btn = add_button(tr("Sluiten", "Close"), 100,
                                    guarded(lambda: form.Close()),
                                    tr("Sluit de bridge. Gewijzigde "
                                       "instellingen worden alleen bij "
                                       "Starten of Resultaten... opgeslagen.",
                                       "Close the bridge. Changed settings "
                                       "are only saved on Start or "
                                       "Results..."), right=True)
            # No AcceptButton: Enter in a field or the document list
            # would otherwise start a run immediately.
            form.CancelButton = cancel_btn

            doc_list.SelectedIndex = 0
            for page in stretch:
                page.Resize += make_fit(page)

            nav.SelectedIndexChanged += on_nav_selected
            nav.SelectedIndex = 0

            def on_shown(sender, args):
                form.TopMost = False
                form.ActiveControl = nav
                fit_footer()
                for page in stretch:
                    fit_page(page)
            form.Shown += on_shown
            # Non-modal: Show() plus its own message loop. If the
            # script runs on Mecway's UI thread,
            # Application.DoEvents also processes Mecway's messages and Mecway
            # stays usable (viewing results) while this window is open;
            # ShowDialog() would block Mecway. In its own STA thread
            # (below) the same loop works too. NOT verified in Mecway
            # on which thread scripts run.
            state = {"open": True}

            def on_closed(sender, args):
                state["open"] = False
            form.FormClosed += on_closed
            try:
                form.Show()
                form.Activate()
                while state["open"]:
                    Application.DoEvents()
                    Thread.CurrentThread.Join(20)
            finally:
                # Release the window and browser element (ActiveX): the
                # window is rebuilt after every run.
                form.Dispose()
        except Exception as e:
            result["error"] = e

    if Thread.CurrentThread.GetApartmentState() == ApartmentState.STA:
        build_and_run()
    else:
        thread = Thread(ThreadStart(build_and_run))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    if result["error"] is not None:
        raise RuntimeError(tr("Fout in het hoofdvenster: {0}",
                              "Error in the main window: {0}").format(
            result["error"]))
    return {"action": result["action"], "values": result["values"]}


def open_convergence_monitor(work_dir=None, model=None):
    """
    Start the convergence screen (separate process, stays open) for the
    newest .mess file in work_dir (default the work folder from
    CONFIG_BRIDGE; the main window passes the value from the text field).
    Returns a status text.
    """
    import bridge_run_aster
    work_dir = work_dir or work_dir_path()
    mess = bridge_run_aster.latest_mess(work_dir, model)
    if mess is None:
        return tr("Nog geen run in de werkmap {0}; het convergentiescherm "
                  "heeft niets te tonen.",
                  "No run in the work folder {0} yet; the convergence "
                  "window has nothing to show.").format(work_dir)
    note = tr("Convergentiescherm geopend voor {0}.",
              "Convergence window opened for {0}.").format(
                  os.path.basename(mess))
    console = os.path.splitext(mess)[0] + bridge_run_aster.CONSOLE_SUFFIX
    if not bridge_run_aster.start_convergence_monitor(mess, 0.0, console):
        return tr("Het convergentiescherm kon niet gestart worden; zie {0} "
                  "in de werkmap.",
                  "The convergence window could not be started; see {0} in "
                  "the work folder.").format(bridge_utils.log_file_name())
    return note


# ==========================================
# RESULTS SELECTION SCREEN (button Resultaten... in the main window)
# ==========================================
def _results_line(item):
    """Line in the list: date/time, model, size."""
    rid = item.get("run_id", "")
    when = ("{0}-{1}-{2} {3}:{4}:{5}".format(rid[0:4], rid[4:6], rid[6:8],
                                              rid[9:11], rid[11:13],
                                              rid[13:15])
            if len(rid) == 15 else os.path.basename(item["path"]))
    model = os.path.basename(item.get("model", "")) or "?"
    # %-formatting: always a point (locale, see _float_text)
    return u"{0}    {1}    {2} MB".format(when, model,
                                          "%.1f" % (item["size"] / 1.0e6))


def results_dialog(items, work_dir):
    """
    Selection screen for the button Resultaten... (MecwayAsterBridgeMain.
    _results_action). items: list_results(work_dir).
    Returns {"action": "load", "path": result file},
    {"action": "strip"} or None (Annuleren). Without Windows Forms:
    ImportError (the script then falls back to mw.input()).
    """
    try:
        import clr
        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
        from System.Windows.Forms import (
            Form, Label, Button, ListBox, DialogResult, FormBorderStyle,
            FormStartPosition, OpenFileDialog, BorderStyle)
        from System.Drawing import Point, Size
        from System.Threading import Thread, ThreadStart, ApartmentState
    except Exception as e:
        raise ImportError(tr("Windows Forms niet beschikbaar: {0}",
                             "Windows Forms not available: {0}").format(e))

    result = {"value": None, "error": None}

    def build_and_run():
        try:
            look = _Look()
            form = Form()
            form.Text = tr("MecwayAsterBridge - resultaten",
                           "MecwayAsterBridge - results")
            form.Font = look.font
            form.BackColor = look.col("page_bg")
            form.ClientSize = Size(760, 470)
            form.StartPosition = FormStartPosition.CenterScreen
            form.FormBorderStyle = FormBorderStyle.FixedDialog
            form.MaximizeBox = False
            form.MinimizeBox = False
            form.TopMost = True
            look.header(form, tr("Resultaten", "Results"), work_dir)

            info = Label()
            info.Text = tr(
                "Resultaten van eerdere Code-Aster-runs (nieuwste eerst). "
                "'Inladen' zet de gekozen resultaten in het open model (na "
                "een controle of het mesh gelijk is). 'Uit model "
                "verwijderen' haalt alle resultaten uit de .liml, zodat die "
                "klein blijft; de resultaatbestanden blijven staan.",
                "Results of earlier Code-Aster runs (newest first). 'Load' "
                "puts the chosen results into the open model (after "
                "checking that the mesh is the same). 'Remove from model' "
                "takes all results out of the .liml so that it stays small; "
                "the result files are kept.")
            info.ForeColor = look.col("muted")
            info.Location = Point(16, 70)
            info.Size = Size(728, 52)
            form.Controls.Add(info)

            lst = ListBox()
            lst.Location = Point(16, 126)
            lst.Size = Size(728, 270)
            lst.IntegralHeight = False
            lst.BorderStyle = BorderStyle.FixedSingle
            for item in items:
                lst.Items.Add(_results_line(item))
            if items:
                lst.SelectedIndex = 0
            form.Controls.Add(lst)

            def finish(value):
                result["value"] = value
                form.DialogResult = DialogResult.OK

            def on_load(sender, args):
                if lst.SelectedIndex >= 0:
                    finish({"action": "load",
                            "path": items[lst.SelectedIndex]["path"]})

            def on_browse(sender, args):
                dlg = OpenFileDialog()
                dlg.Filter = tr("Resultaten (*_results.xml)|*_results.xml|"
                                "Alle bestanden (*.*)|*.*",
                                "Results (*_results.xml)|*_results.xml|"
                                "All files (*.*)|*.*")
                dlg.CheckFileExists = True
                if os.path.isdir(work_dir):
                    dlg.InitialDirectory = work_dir
                if dlg.ShowDialog(form) == DialogResult.OK:
                    finish({"action": "load", "path": dlg.FileName})

            def on_strip(sender, args):
                finish({"action": "strip"})

            buttons = [
                (tr("Inladen", "Load"), on_load, 110, True),
                (tr("Ander bestand...", "Other file..."), on_browse, 130,
                 False),
                (tr("Uit model verwijderen", "Remove from model"),
                 on_strip, 170, False),
            ]
            x = 16
            for text, handler, width, primary in buttons:
                btn = look.button(text, primary)
                btn.Location = Point(x, 416)
                btn.Width = width
                btn.Click += handler
                form.Controls.Add(btn)
                x += width + 8
            lst.DoubleClick += on_load
            cancel_btn = look.button(tr("Annuleren", "Cancel"))
            cancel_btn.Location = Point(644, 416)
            cancel_btn.Width = 100
            cancel_btn.DialogResult = DialogResult.Cancel
            form.Controls.Add(cancel_btn)
            form.CancelButton = cancel_btn

            if form.ShowDialog() != DialogResult.OK:
                result["value"] = None
        except Exception as e:
            result["error"] = e

    if Thread.CurrentThread.GetApartmentState() == ApartmentState.STA:
        build_and_run()
    else:
        thread = Thread(ThreadStart(build_and_run))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    if result["error"] is not None:
        raise RuntimeError(tr("Fout in het resultatenscherm: {0}",
                              "Error in the results window: {0}").format(
            result["error"]))
    return result["value"]


# ==========================================
# FALLBACK: mw.input() QUESTIONS
# ==========================================
def _ask(mw, prompt, key, kind, extra):
    """Ask for a value until the input is valid; empty = None (keep)."""
    while True:
        raw = mw.input(prompt)
        if raw is None or "{0}".format(raw).strip() == "":
            return None
        raw = "{0}".format(raw).strip()
        if kind == "bool":
            low = raw.lower()
            if low in ("j", "ja", "y", "yes", "1", "true"):
                raw = True
            elif low in ("n", "nee", "no", "0", "false"):
                raw = False
            else:
                mw.message(tr("Antwoord met j of n.", "Answer y or n."))
                continue
        elif kind == "checklist":
            raw = [p.strip() for p in raw.split(",") if p.strip()]
            unknown = [p for p in raw if p not in RESULT_FIELD_SPECS]
            if unknown:
                mw.message(tr("Onbekende velden: {0}",
                              "Unknown fields: {0}").format(", ".join(unknown)))
                continue
        value, err = _parse_and_validate(key, kind, extra, raw)
        if err:
            mw.message(err)
            continue
        return value


def _run_input_fallback(mw, current, reason):
    mw.message(tr(
        "Het grafische startscherm kon niet worden geladen:\n{0}\n\n"
        "De instellingen worden nu een voor een gevraagd.\n"
        "Laat een veld leeg om de huidige waarde te houden.",
        "The graphical start screen could not be loaded:\n{0}\n\n"
        "The settings will now be asked one by one.\n"
        "Leave a field empty to keep the current value.").format(reason))
    values = {"general": dict(current["general"]),
              "analyses": dict((k, dict(v))
                               for k, v in current["analyses"].items())}

    def prompt_for(where, label, kind, extra, value):
        lines = ["[{0}] {1}".format(where, _t(label)),
                 tr("Huidig: {0}", "Current: {0}").format(
                     _format_value(value, kind))]
        if kind in _CHOICE_KINDS:
            lines.append(tr("Opties: ", "Options: ")
                         + ", ".join(_choice_options(kind, extra)))
        elif kind == "bool":
            lines.append(tr("Antwoord j of n.", "Answer y or n."))
        elif kind == "float_range":
            lines.append(tr("Bereik: {0} .. {1}", "Range: {0} .. {1}").format(
                extra[0], extra[1]))
        elif kind == "checklist":
            lines.append(tr("Kommagescheiden, opties: ",
                            "Comma-separated, options: ")
                         + ", ".join(RESULT_FIELD_SPECS.keys()))
        return "\n".join(lines)

    for key, label, kind, extra in GENERAL_SPECS:
        new = _ask(mw, prompt_for(_where(None, key), label, kind, extra,
                                  values["general"][key]), key, kind, extra)
        if new is not None:
            values["general"][key] = new
    for name in _analysis_names():
        for key, label, kind, extra in ANALYSIS_SPECS:
            if key not in values["analyses"][name]:
                continue
            new = _ask(mw, prompt_for(_where(name, key), label, kind, extra,
                                      values["analyses"][name][key]),
                       key, kind, extra)
            if new is not None:
                values["analyses"][name][key] = new

    confirm = mw.input(tr("Typ J om te starten; iets anders annuleert.",
                          "Type Y to start; anything else cancels."))
    if "{0}".format(confirm).strip().lower() not in ("j", "ja", "y", "yes"):
        return None
    return values


# ==========================================
# PUBLIC FUNCTION
# ==========================================
# Is the main window already open (same Mecway session)? See
# run_settings_dialog.
_HUB = {"open": False}


def run_settings_dialog(mw, status=u""):
    """
    Show the main window, update CONFIG_BRIDGE and save changes
    (on Starten and Resultaten...). status: text about the previous run for
    the status box.

    Returns
    -------
    dict  {"ok": bool, "action": "run" | "results" | "close",
           "changes": [...], "save_errors": [...],
           "gui": "winforms" or "mw.input"}
          ok=True only for "run".
    """
    current = _collect_current()
    gui = "winforms"
    if _HUB["open"]:
        mw.message(tr("Het venster van MecwayAsterBridge is al open.",
                      "The MecwayAsterBridge window is already open."))
        return {"ok": False, "action": "close", "changes": [],
                "save_errors": [], "gui": gui}
    try:
        _HUB["open"] = True
        try:
            try:
                model = bridge_utils.model_stem(mw.file_name())
            except Exception:
                model = None
            # Configurations of the open model for the choice list (from
            # disk: the last saved version)
            try:
                _MODEL_INFO["configurations"] = \
                    bridge_results_liml.configuration_names(mw.file_name())
            except Exception:
                _MODEL_INFO["configurations"] = []
            answer = _show_winforms_dialog(current, status, model)
        finally:
            _HUB["open"] = False
        action, new_values = answer["action"], answer["values"]
    except (ImportError, RuntimeError) as e:
        gui = "mw.input"
        new_values = _run_input_fallback(mw, current, e)
        action = "run" if new_values is not None else "close"

    if action not in ("run", "results") or new_values is None:
        return {"ok": False, "action": action, "changes": [],
                "save_errors": [], "gui": gui}

    changes = _apply_values(new_values)
    save_errors = save_to_bridge_utils(changes)
    if save_errors:
        mw.message(tr("De instellingen gelden voor deze run, maar opslaan "
                      "in bridge_utils.py is (deels) mislukt:\n\n",
                      "The settings apply to this run, but saving them in "
                      "bridge_utils.py (partly) failed:\n\n")
                   + "\n".join(save_errors))
    return {"ok": action == "run", "action": action, "changes": changes,
            "save_errors": save_errors, "gui": gui}
