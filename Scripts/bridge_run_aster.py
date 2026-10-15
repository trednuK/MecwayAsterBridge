# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_run_aster.py
# Responsibility: starts Code-Aster as an external process via the
# run_aster.bat launcher, and after the run looks for errors in study.mess
# (aster_mess_errors). Isolated from file generation (bridge_to_aster.py)
# and result parsing (bridge_from_aster.py) because failure here has a
# different cause (launcher not found, permission problem) than failure
# in those other modules.
#
# Synchronisation: Code-Aster runs in a separate cmd window. This module
# does NOT wait until the solver has finished; instead mw.message() shows
# a dialog that the user must confirm manually. That is a
# deliberate choice because run_aster.bat gives no reliable exit signal
# and the solver output (.mess) is written asynchronously.
#
# Console output: the output of run_aster (including stderr) goes via "tee"
# from the Code-Aster installation (tools\tee.exe) to the window AND to
# study_console.txt. A Python error in study.comm only appears there (not
# in study.mess; KNOWN_BUGS 13 resolved).
#
# Convergence monitor: on every run (setting convergence_monitor)
# start_convergence_monitor() starts aster_convergence_monitor.py as a separate
# process (Code-Aster's CPython), see the header of that file; afterwards via
# the button Convergentiescherm in the main window (bridge_gui).
#
# Compatible with IronPython 2.7.9.

import os
import re
import subprocess
import time

from bridge_utils import (log, CONFIG_BRIDGE, tr, run_name, run_names,
                          exe_aster_path)
from bridge_convergence import python_errors


# Messages in study.mess appear as "<F> <CODE>" in a box; <A> is an
# alarm. An <EXCEPTION> stops the commands after it, but the launcher then
# sometimes only reports "DIAGNOSTIC JOB : <A>_ALARM" (seen with Code-Aster
# 17.4 on Windows). That is why the .mess file itself is searched.
# Also <ConvergenceError> and other <...Error>: STAT_NON_LINE stopped with
# <ConvergenceError> <MECANONLINE9_7> while the DIAGNOSTIC line gave "OK"
# (seen in Mecway).
_MESS_ERROR_RE = re.compile(
    r"<(EXCEPTION|F|S|E|[A-Za-z]+Error)>\s*<([A-Za-z0-9_]+)>")
# Without a message box, after a Python exception in a command.
_MESS_UNCAUGHT = "after an uncaught exception"
_MESS_ALARM_RE = re.compile(r"<A>\s*<([A-Za-z0-9_]+)>")
# Explanation of CALC_MODES alarms (bridge_to_aster._calc_modes_block:
# VERI_MODE STOP_ERREUR='NON', so alarms instead of errors). Text of the
# messages from Code-Aster 17.4 (seen with Mecway's BucklingBeam).
_ALARM_HINTS = {
    "ALGELINE5_23": (
        u"de Sturm-controle telt in het interval van de berekende modes "
        u"meer eigenwaarden dan berekend. Meestal valt een meervoudige mode "
        u"(symmetrie) op de grens van het aantal modes; anders is er een "
        u"mode gemist. Vraag een of twee modes meer en vergelijk.",
        u"the Sturm check counts more eigenvalues in the interval of the "
        u"computed modes than were computed. Usually a multiple mode "
        u"(symmetry) falls on the limit of the number of modes; otherwise a "
        u"mode was missed. Ask for one or two more modes and compare."),
    # Seen with a free-free model and a negative search frequency
    # (docs review): the lower bound of the Sturm band falls on a rigid mode.
    "ALGELINE3_82": (
        u"de ondergrens van het zoekinterval valt (bijna) op een eigenwaarde, "
        u"meestal een starre-lichaamsmode bij ~0 Hz (akoestiek: de constante "
        u"druk bij harde wanden). Meestal onschuldig: de "
        u"Sturm-telling kan daardoor afwijken. Controleer het aantal modes "
        u"of verschuif de zoekfrequentie iets.",
        u"the lower bound of the search interval (nearly) coincides with an "
        u"eigenvalue, usually a rigid body mode at ~0 Hz (acoustics: the "
        u"constant pressure with hard walls). Usually harmless: "
        u"the Sturm count may be off because of it. Check the number of "
        u"modes or shift the search frequency slightly."),
    # Duplicate cells (same nodes). Vibro-acoustics: a shell on a
    # fluid face has its own interface cell (FLUI_STRU) with the same
    # nodes (bridge_vibroacoustic.interface_faces); seen in verification
    # VA-03/VA-05, frequencies exact.
    "MODELISA4_8": (
        u"dubbele cellen (zelfde knopen). Bij vibro-akoestiek normaal voor "
        u"een schaal op een lucht- of vloeistofvlak (schaal en koppelvlak "
        u"zijn aparte cellen); anders: controleer het mesh op dubbele "
        u"elementen.",
        u"duplicate cells (same nodes). Normal in vibroacoustics for a shell "
        u"on an air or fluid face (shell and coupling face are separate "
        u"cells); otherwise: check the mesh for duplicate elements."),
    "MODELISA8_13": (
        u"zie MODELISA4_8 (dubbele cellen).",
        u"see MODELISA4_8 (duplicate cells)."),
    "ALGELINE2_74": (
        u"de controle van de modes (VERI_MODE: fout per mode en Sturm) is "
        u"niet gehaald; zie de tabel in study.mess.",
        u"the check of the modes (VERI_MODE: error per mode and Sturm) "
        u"failed; see the table in study.mess."),
    # Complex modes (bridge_modal_damping): Code-Aster only gives the
    # oscillating modes (seen: beta = 1e-3 s on a hex20 cantilever gave 3
    # of the 6 modes; free-free with alpha: the 6 rigid modes dropped out).
    "ALGELINE5_79": (
        u"complexe modes: minder modes dan gevraagd. Overkritisch gedempte "
        u"modes (zeta >= 1, vaak hoge modes met Rayleigh-beta of lage met "
        u"alpha) en starre modes trillen niet en worden niet gegeven. "
        u"Verlaag de demping als je die modes wilt zien; zeta per mode staat "
        u"in de log.",
        u"complex modes: fewer modes than requested. Overdamped modes (zeta "
        u">= 1, often high modes with Rayleigh beta or low ones with alpha) "
        u"and rigid body modes do not oscillate and are not given. Lower the "
        u"damping to see those modes; zeta per mode is in the log."),
    # Seen with complex modes in a free-free model (the stiffness is
    # singular); the elastic modes were equal to Mecway (MC-05).
    "FACTOR_11": (
        u"een (bijna) singuliere matrix bij het ontbinden. Bij complexe "
        u"modes in een model zonder opleggingen normaal (starre "
        u"bewegingen); anders: controleer de opleggingen.",
        u"a (nearly) singular matrix in the factorisation. Normal for "
        u"complex modes in a model without supports (rigid body motion); "
        u"otherwise: check the supports."),
}
_MESS_BOX_END = u"╚"        # bottom edge of the message box
_MESS_BOX_SIDE = u"║ "      # side of the box and a space
# Last line that run_aster writes to study.mess, also after an <EXCEPTION>.
_MESS_DONE = "--- DIAGNOSTIC JOB :"
# Explanation of messages that usually point to the model (text from
# Messages/factor.py of Code-Aster 17.4). A free mechanism with
# NPREC=-1 (no singularity detection) gives FACTOR_57 instead of FACTOR_10/11/42.
# Texts as a pair (nl, en); tr(*pair) picks the language when used.
_SINGULAR_HINT = (u"De stijfheidsmatrix is (bijna) singulier: waarschijnlijk "
                  u"kan een deel van het model vrij bewegen (te weinig "
                  u"opleggingen; een pinned support houdt alleen de "
                  u"gemiddelde verplaatsing vast) of zijn opleggingen dubbel. "
                  u"Zie docs/Foutmeldingen_CodeAster.md.",
                  u"The stiffness matrix is (nearly) singular: probably a "
                  u"part of the model can move freely (too few supports; a "
                  u"pinned support only fixes the average displacement) or "
                  u"supports are duplicated. See "
                  u"docs/en/CodeAster_error_messages.md.")
# Newton does not converge (STAT_NON_LINE/DYNA_NON_LINE). The bridge lets the
# job continue with the steps up to the last converged time
# (BRIDGE_ONVOLLEDIG); advice according to U2.04.04 sec. 4.1 and 4.5.
_NEWTON_HINT = (u"Newton convergeert niet; de resultaten tot het laatst "
                u"bereikte tijdstip worden ingeladen. Controleer eerst het "
                u"model: "
                u"contactvlakken (master = het stijve gereedschap, slave = "
                u"het fijnere of vervormende vlak), beginspleten en "
                u"-penetraties, en of delen alleen via contact op hun plaats "
                u"blijven. Reken stap voor stap: eerst contact met lineair "
                u"materiaal, dan plasticiteit. Doorsnijden of bezwijken: geef "
                u"het materiaal een bezwijkgrens (docs/Bezwijken.md); na een "
                u"bezwijkmoment helpen kleinere stappen. Blijft RESI_GLOB_RELA "
                u"in de eerste stappen hoog terwijl RESI_GLOB_MAXI heel klein "
                u"is (een beweging zonder weerstand), kies dan "
                u"Convergentiecriterium = MAXI. Stagneert RESI_GLOB_RELA net "
                u"boven het criterium (bijv. 2e-6 bij 1e-6, gezien bij "
                u"ontlasten met GDEF_LOG), gebruik dan de standaard 1e-5, of "
                u"Convergentiecriterium = RELA_OF_MAXI met RESI_GLOB_MAXI "
                u"boven de absolute rest waarop het stagneert (kolom "
                u"RESI_GLOB_MAXI in de .mess). Bij contact kan "
                u"Contactmethode = PENALISATION (Mecway's stijfheid) helpen. "
                u"Zie "
                u"docs/Instellingen_contact_en_nietlineair.md en "
                u"docs/Foutmeldingen_CodeAster.md.",
                u"Newton does not converge; the results up to the last "
                u"time reached are loaded. Check the model first: "
                u"contact surfaces (master = the stiff tool, slave = the "
                u"finer or deforming surface), initial gaps and "
                u"penetrations, and whether parts are held in place only by "
                u"contact. Work step by step: first contact with linear "
                u"material, then plasticity. Cutting through or collapse: "
                u"give the material a failure limit (docs/en/Failure.md); "
                u"after a failure event smaller steps help. If "
                u"RESI_GLOB_RELA stays high in the first steps while "
                u"RESI_GLOB_MAXI is very small (a motion without "
                u"resistance), choose Convergence criterion = MAXI. If "
                u"RESI_GLOB_RELA stalls just above the criterion (e.g. 2e-6 "
                u"at 1e-6, seen when unloading with GDEF_LOG), use the "
                u"default 1e-5, or Convergence criterion = RELA_OF_MAXI with "
                u"RESI_GLOB_MAXI above the absolute residual where it stalls "
                u"(column RESI_GLOB_MAXI in the .mess). With "
                u"contact, Contact method = PENALISATION (Mecway's "
                u"stiffness) can help. See "
                u"docs/en/Settings_contact_and_nonlinear.md and "
                u"docs/en/CodeAster_error_messages.md.")
# MECANONLINE9_4 with contact: pivot on LAGS_C (contact Lagrange) for
# line contact (Tutorials/AssemblyWithContact Fixed_support, compared
# headless); with PENALISATION it computes. NPREC -1 also computes
# but is inaccurate (docs review: -1,6% / +2,8% on a stiffness contrast),
# so no advice.
_NEWTON_SINGULAR_HINT = (
    _SINGULAR_HINT[0] + u" Met contact en 'LAGS_C' in de melding: een "
    u"contactvrijheidsgraad zonder steun (bijv. lijncontact); kies "
    u"Contactmethode = PENALISATION (Mecway's stijfheid).",
    _SINGULAR_HINT[1] + u" With contact and 'LAGS_C' in the message: a "
    u"contact degree of freedom without support (e.g. line contact); "
    u"choose Contact method = PENALISATION (Mecway's stiffness).")
# CALC_MODES (bridge_to_aster._calc_modes_block): the stiffness is singular
# at the search frequency (ALGELINE3_81, seen with a beam that was only
# supported by hinges), or Sorensen found too few modes
# (ALGELINE5_49 / ALGELINE3_78, seen with a search frequency far from the
# modes).
_MODES_SINGULAR_HINT = (
    u"De stijfheidsmatrix is singulier: het model heeft een mechanisme of "
    u"starre-lichaamsbeweging (te weinig opleggingen, een los onderdeel, "
    u"een scharnier). Leg het model beter vast, of kies op de pagina "
    u"Modaal een negatieve zoekfrequentie (bijv. -10 x de verwachte eerste "
    u"frequentie); de starre modes komen dan met ~0 Hz mee. Dat helpt alleen "
    u"als het losse deel massa heeft (dichtheid of puntmassa). Een "
    u"verbinding uit #ASTER-code telt alleen mee via #ASTER-EXCIT.",
    u"The stiffness matrix is singular: the model has a mechanism or rigid "
    u"body motion (too few supports, a loose part, a hinge). Support the "
    u"model better, or choose a negative search frequency on the Modal page "
    u"(e.g. -10 x the expected first frequency); the rigid modes then "
    u"appear with ~0 Hz. That only helps if the loose part has mass "
    u"(density or point mass). A connection from #ASTER code only counts "
    u"via #ASTER-EXCIT.")
_MODES_FEW_HINT = (
    u"Code-Aster vond (te) weinig modes rond de zoekfrequentie. Kies een "
    u"zoekfrequentie dichter bij de verwachte frequenties (0 = de "
    u"laagste), of minder modes. Met zoekfrequentie 0 kunnen veel valse "
    u"modes bij ~0 Hz de oorzaak zijn (bijv. een membraan met een zeer "
    u"kleine E en voorspanning, KNOWN_BUGS 49): kies dan een zoekfrequentie "
    u"rond de verwachte frequentie.",
    u"Code-Aster found (too) few modes around the search frequency. Choose "
    u"a search frequency closer to the expected frequencies (0 = the "
    u"lowest), or fewer modes. With search frequency 0, many spurious "
    u"modes at ~0 Hz can be the cause (e.g. a membrane with a very small E "
    u"and prestress, KNOWN_BUGS 49): then choose a search frequency around "
    u"the expected frequency.")
# MODE_ITER_CYCL (bridge_cyclic.py): the check of the cyclic geometry
# (seen with Code-Aster 17.4: ALGORITH16_52 for noise around 0 in the axial
# coordinate, ALGORITH16_58 for swapped cut faces, ALGORITH14_95 for 8
# sectors with nodes on the axis).
_CYCLIC_HINT = (
    u"Cyclische symmetrie (MODE_ITER_CYCL): de snijvlakken passen niet als "
    u"herhaling om de as. Controleer in Mecway de as, het aantal segmenten "
    u"en dat de knopen van master en slave op elkaar passen; bij 8 "
    u"segmenten met knopen op de as: maak een klein gat op de as "
    u"(KNOWN_BUGS 61).",
    u"Cyclic symmetry (MODE_ITER_CYCL): the cut faces do not repeat about "
    u"the axis. Check in Mecway the axis, the number of segments and that "
    u"the master and slave nodes match; with 8 segments and nodes on the "
    u"axis: make a small hole on the axis (KNOWN_BUGS 61).")
# FACTOR_57 (Messages/factor.py of Code-Aster 17.4): MUMPS' estimate of the
# relative error of the solution ("Erreur calculee", condition number x
# backward error) is above RESI_RELA ("Erreur acceptable"; U4.50.01 par.
# 3.5.3). Measured (docs/Foutmeldingen_CodeAster.md, verification BU-37):
# slender hex20 models in bending without a mechanism 1.1e-6 ... 5.0e-5;
# a real mechanism stops with FACTOR_11 (NPREC 8) or, with NPREC -1, gives
# 13 and 64. Below _RESI_ILL_LIMIT the advice is the setting
# lin_solver_resi (_resi_advice), above it the singular hint.
_RESI_ILL_LIMIT = 1.0e-3
_RESI_HINT = (
    u"MUMPS schat de fout van de oplossing groter dan RESI_RELA (Erreur "
    u"calculée > Erreur acceptable). Is die fout klein (kleiner dan "
    u"1e-3), dan is er geen mechanisme maar een slecht geconditioneerde "
    u"matrix (bijv. een slank volumemodel op buiging): zet 'Nauwkeurigheid "
    u"oplosser (RESI_RELA)' (lin_solver_resi) van de analyse ruim boven die "
    u"fout. Is ze groot (orde 1 of meer): " + _SINGULAR_HINT[0],
    u"MUMPS estimates the error of the solution above RESI_RELA (Erreur "
    u"calculée > Erreur acceptable). If that error is small (below "
    u"1e-3), there is no mechanism but a poorly conditioned matrix (e.g. "
    u"a slender volume model in bending): set 'Solver accuracy "
    u"(RESI_RELA)' (lin_solver_resi) of the analysis well above that "
    u"error. If it is large (order 1 or more): " + _SINGULAR_HINT[1])
_NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?")


def _resi_advice(box_text, analysis_name=None):
    """
    Advice for FACTOR_57 from the text of its message box: the computed
    and the acceptable error are the first two numbers in it (Code-Aster
    17.4: "Erreur calculee : 7.04369e-06 Erreur acceptable : 1e-06
    (RESI_RELA)"). analysis_name: the active analysis (default
    CONFIG_BRIDGE["active_analysis"], resolved by main()). Returns the text
    in the chosen language.
    """
    nums = []
    for tok in _NUMBER_RE.findall(box_text.split(u"MUMPS", 1)[-1]):
        try:
            nums.append(float(tok))
        except ValueError:
            pass
    if len(nums) < 2 or nums[0] <= 0.0:
        return tr(*_RESI_HINT)
    err, limit = nums[0], nums[1]
    if err >= _RESI_ILL_LIMIT:
        return tr(u"geschatte fout {0:.3g} (RESI_RELA {1:g}). ",
                  u"estimated error {0:.3g} (RESI_RELA {1:g}). ").format(
                      err, limit) + tr(*_SINGULAR_HINT)
    # Suggestion: the power of ten at least 10 x the computed error.
    exp = 0
    while 10.0 ** exp < 10.0 * err * (1.0 - 1e-9):
        exp += 1
    while 10.0 ** (exp - 1) >= 10.0 * err * (1.0 - 1e-9):
        exp -= 1
    suggest = u"1e{0}".format(exp)
    name = analysis_name or CONFIG_BRIDGE.get("active_analysis", u"")
    cfg = CONFIG_BRIDGE.get("analyses", {}).get(name, {})
    head = tr(u"MUMPS schat de fout van de oplossing op {0:.3g}, boven "
              u"RESI_RELA {1:g}. Zo'n kleine fout is geen mechanisme maar "
              u"een slecht geconditioneerde stijfheidsmatrix (bijv. een "
              u"slank volumemodel op buiging, of grote "
              u"stijfheidsverschillen). ",
              u"MUMPS estimates the error of the solution at {0:.3g}, above "
              u"RESI_RELA {1:g}. Such a small error is not a mechanism but a "
              u"poorly conditioned stiffness matrix (e.g. a slender volume "
              u"model in bending, or large differences in "
              u"stiffness). ").format(err, limit)
    if "lin_solver_resi" not in cfg:
        return head + tr(u"Deze analyse ({0}) heeft geen instelling voor "
                         u"RESI_RELA; zie docs/Foutmeldingen_CodeAster.md.",
                         u"This analysis ({0}) has no setting for "
                         u"RESI_RELA; see "
                         u"docs/en/CodeAster_error_messages.md.").format(name)
    title = name
    try:
        import bridge_gui
        pair = dict(bridge_gui.ANALYSIS_TITLES).get(name)
        if pair:
            title = tr(*pair)
    except Exception:
        pass
    return head + tr(u"Zet op de pagina {0} van het startscherm "
                     u"'Nauwkeurigheid oplosser (RESI_RELA)' "
                     u"(lin_solver_resi) op {1} en reken opnieuw. Zie "
                     u"docs/Foutmeldingen_CodeAster.md.",
                     u"On the page {0} of the start screen set 'Solver "
                     u"accuracy (RESI_RELA)' (lin_solver_resi) to {1} and "
                     u"run again. See "
                     u"docs/en/CodeAster_error_messages.md.").format(
                         title, suggest)


_MESS_HINTS = {"FACTOR_10": _SINGULAR_HINT, "FACTOR_11": _SINGULAR_HINT,
               "ALGORITH16_52": _CYCLIC_HINT, "ALGORITH16_58": _CYCLIC_HINT,
               "ALGORITH14_94": _CYCLIC_HINT,
               "ALGELINE3_81": _MODES_SINGULAR_HINT,
               "ALGELINE5_49": _MODES_FEW_HINT,
               "ALGELINE3_78": _MODES_FEW_HINT,
               "FACTOR_42": _SINGULAR_HINT, "FACTOR_57": _RESI_HINT,
               "MECANONLINE9_7": _NEWTON_HINT,
               # "Arret pour cause de matrice non inversible" (STAT_NON_LINE
               # with contact, seen in study.mess); causes as FACTOR_*,
               # or a pivot on a contact Lagrange degree of freedom.
               "MECANONLINE9_4": _NEWTON_SINGULAR_HINT}


def mess_hints():
    """Explanation per Code-Aster message code, chosen language (dict)."""
    return dict((code, tr(*pair)) for code, pair in _MESS_HINTS.items())
# Line that the .comm prints after a caught ConvergenceError
# (bridge_to_aster._build_nonlin_static).
_MESS_PARTIAL_RE = re.compile(r"BRIDGE_ONVOLLEDIG\s+(\S+)")
# The FIN command writes "<I> <FIN> ARRET NORMAL DANS "FIN" ..." (in every
# completed study.mess of the test models, also after a caught
# ConvergenceError). If it is missing, study.comm was not executed to the end
# (e.g. SyntaxError: study.mess then only has
# "DIAGNOSTIC JOB : OK"; seen with Code-Aster 17.4).
_MESS_FIN = "<FIN>"
# Line that the .comm of the response on a modal basis prints before it stops
# (bridge_dyna_modal._dyna_block): a mode without frequency or a
# damping ratio >= 1.
_MESS_MODAL_RE = re.compile(r"BRIDGE_DYNA_MODAL_FOUT\s+(\w+)\s*(.*)")
_MODAL_HINTS = {
    "FREQ": (u"Respons op modale basis: een mode met frequentie <= 0 ({0}): "
             u"een starre beweging of mechanisme. Mecway staat dat ook niet "
             u"toe (manual par. 6.4). Leg het model volledig vast.",
             u"Mode superposition: a mode with frequency <= 0 ({0}): a rigid "
             u"body motion or mechanism. Mecway does not allow it either "
             u"(manual section 6.4). Constrain the model fully."),
    "DEMPING": (u"Respons op modale basis: dempingsverhouding >= 1 ({0}), "
                u"overkritisch. Mecway vraagt xi < 1 voor elke mode (manual "
                u"par. 6.4). Verlaag de Rayleigh-demping (alpha dempt de "
                u"laagste, beta de hoogste modes; xi per mode staat in "
                u"study.mess, BRIDGE_DEMPING), de instelling modal_damping, "
                u"of het aantal modes.",
                u"Mode superposition: damping ratio >= 1 ({0}), overdamped. "
                u"Mecway requires xi < 1 for every mode (manual section "
                u"6.4). Lower the Rayleigh damping (alpha damps the lowest, "
                u"beta the highest modes; xi per mode is in study.mess, "
                u"BRIDGE_DEMPING), the setting modal_damping, or the number "
                u"of modes."),
}
# Same for the response spectrum analysis (bridge_spectrum._spectrum_block).
_MESS_SPECTRUM_RE = re.compile(r"BRIDGE_SPECTRUM_FOUT\s+(\w+)\s*(.*)")
_SPECTRUM_HINTS = {
    "FREQ": (u"Spectrumanalyse: een mode met frequentie <= 0 ({0}): een "
             u"starre beweging of mechanisme. Leg het model volledig vast.",
             u"Response spectrum analysis: a mode with frequency <= 0 ({0}): "
             u"a rigid body motion or mechanism. Constrain the model "
             u"fully."),
    "DEMPING": (u"Spectrumanalyse: dempingsverhouding >= 1 ({0}). Verlaag "
                u"spectrum_damping of Mecway's Rayleigh-demping (beta dempt "
                u"de hoogste modes), of het aantal modes.",
                u"Response spectrum analysis: damping ratio >= 1 ({0}). "
                u"Lower spectrum_damping or Mecway's Rayleigh damping (beta "
                u"damps the highest modes), or the number of modes."),
}
# Console output of run_aster (stdout + stderr), written by tee.
# Console output of the run: <model>_<run_id>_console.txt (run_name).
CONSOLE_SUFFIX = "_console.txt"
# An error in aster_results_export.py (in the job) is an error of the bridge,
# not of the model; that module then prints "aster_results_export: FOUT"
# (language nl) or "aster_results_export: ERROR" (en; the language of the job
# scripts follows CONFIG_BRIDGE["language"] via study.comm, bridge_to_aster).
_EXPORT_FAIL = (u"aster_results_export: FOUT", u"aster_results_export: ERROR")
_EXPORT_HINT = (u"Het wegschrijven van de resultaten naar Mecway "
                u"(aster_results_export.py) mislukte: een fout in de bridge, "
                u"niet in het model. Zie study_console.txt in de werkmap.",
                u"Writing the results to Mecway (aster_results_export.py) "
                u"failed: an error in the bridge, not in the model. See "
                u"study_console.txt in the work folder.")
_PYTHON_HINT = (u"study.comm is niet (volledig) uitgevoerd. Een fout in "
                u"#ASTER-regels? Zie het Code-Aster-venster of "
                u"study_console.txt in de werkmap.",
                u"study.comm was not (fully) executed. An error in "
                u"#ASTER lines? See the Code-Aster window or "
                u"study_console.txt in the work folder.")


def _read_mess(mess_path):
    """Text of study.mess (UTF-8, unreadable characters replaced)."""
    f = open(mess_path, "rb")
    try:
        return f.read().decode("utf-8", "replace")
    finally:
        f.close()


def _mess_diagnostic(text):
    """Text after 'DIAGNOSTIC JOB :' (e.g. '<A>_ALARM'), or ''."""
    if _MESS_DONE not in text:
        return u""
    rest = text[text.rindex(_MESS_DONE) + len(_MESS_DONE):].strip()
    return rest.splitlines()[0].strip() if rest else u""


def _diag_failed(diag):
    """True if the DIAGNOSTIC line indicates an error (<F>, <S> or <E>)."""
    return diag[:3] in (u"<F>", u"<S>", u"<E>")


def _mess_finished(work_dir, since):
    """True if study.mess is from this run and ends with DIAGNOSTIC JOB."""
    mess_path = os.path.join(work_dir, run_name(".mess"))
    try:
        # run_aster only copies fort.6 to study.mess at the end
        # ("Copying results" in the window); 1 s margin for the clock.
        if os.path.getmtime(mess_path) < since - 1.0:
            return False
        return _MESS_DONE in _read_mess(mess_path)
    except Exception:
        return False


def _mess_box_text(lines, start, max_chars=300):
    """Content of the message box after line 'start', on one line."""
    body = []
    for line in lines[start + 1:start + 40]:
        if _MESS_BOX_END in line:
            break
        part = line.strip().strip(_MESS_BOX_SIDE).strip()
        if part:
            body.append(part)
    text = u" ".join(body)
    if len(text) > max_chars:
        text = text[:max_chars] + u" ..."
    return text


# ==========================================
# CONSOLE OUTPUT AND CONVERGENCE MONITOR
# ==========================================
def aster_root():
    """Code-Aster install folder (exe_aster = <dir>\\bin\\run_aster.bat)."""
    return os.path.dirname(os.path.dirname(
        os.path.abspath(exe_aster_path())))


def _launch_command(export_path, console_path):
    """
    cmd line for run_aster in its own window. 'cmd /k' keeps the
    window open so the user can read errors; nested quotes are
    needed because the paths may contain spaces (cmd removes the outer
    pair). With tools\\tee.exe from the installation the output
    (stdout and stderr, 2>&1) also goes to console_path.

    Returns (command, True if the output is captured).
    """
    run = '"{0}" "{1}"'.format(exe_aster_path(), export_path)
    tee = os.path.join(aster_root(), "tools", "tee.exe")
    if console_path and os.path.isfile(tee):
        return ('cmd /k "{0} 2>&1 | "{1}" "{2}""'.format(
            run, tee, console_path), True)
    return 'cmd /k "{0}"'.format(run), False


def _console_text(work_dir, since=None):
    """Text of the console output of this run, or ""."""
    path = os.path.join(work_dir, run_name(CONSOLE_SUFFIX))
    try:
        if not os.path.exists(path) or (
                since is not None and os.path.getmtime(path) < since - 1.0):
            return u""
        return _read_mess(path)
    except Exception:
        return u""


def console_errors(work_dir, since=None):
    """
    Python errors in study_console.txt of this run (e.g. a SyntaxError
    in study.comm), via bridge_convergence.python_errors().

    Returns
    -------
    list of unicode - empty if there are no errors or the file is missing
                      or from an earlier run.
    """
    path = os.path.join(work_dir, run_name(CONSOLE_SUFFIX))
    try:
        if not os.path.exists(path):
            return []
        if since is not None and os.path.getmtime(path) < since - 1.0:
            return []
        return python_errors(_read_mess(path))
    except Exception as e:
        log(tr("WARNING: {0} niet leesbaar: {1}",
               "WARNING: {0} not readable: {1}").format(
                   os.path.basename(path), str(e)))
        return []


def _monitor_python():
    """pythonw.exe (without console window) of the Code-Aster installation,
    otherwise python.exe; None if neither exists."""
    root = aster_root()
    try:
        subdirs = sorted(d for d in os.listdir(root)
                         if d.lower().startswith("python"))
    except OSError:
        return None
    for exe in ("pythonw.exe", "python.exe"):
        for d in subdirs:
            path = os.path.join(root, d, exe)
            if os.path.isfile(path):
                return path
    return None


def latest_mess(work_dir, model=None):
    """Path of the newest .mess file in work_dir (the last run), or
    None. model: name of the Mecway file (bridge_utils.model_stem); then
    preferably the last run of that model."""
    def mtime(p):
        try:
            return os.path.getmtime(p)
        except OSError:
            return 0.0
    try:
        found = [os.path.join(work_dir, n) for n in os.listdir(work_dir)
                 if n.lower().endswith(".mess")]
    except OSError:
        return None
    if model:
        own = [p for p in found
               if os.path.basename(p).startswith(model + "_")]
        found = own or found
    if not found:
        return None
    return max(found, key=mtime)


def _monitor_log(mess_path):
    """Log file of the convergence monitor next to the .mess file:
    <model>_<run_id>.mess -> <model>_<run_id>_monitor_log.txt."""
    stem = os.path.splitext(os.path.abspath(mess_path))[0]
    return stem + "_monitor_log.txt"


def start_convergence_monitor(mess_path, since=0.0, console_path=None):
    """
    Start the convergence monitor (aster_convergence_monitor.py) as a separate
    process with Code-Aster's CPython. The process is independent of Mecway:
    it keeps working when the Mecway script has finished, and closing it
    has no effect on the run.

    Parameters
    ----------
    mess_path    : str   - .mess file from the .export (live: the fort.6
                           of the run that writes there).
    since        : float - time.time() at the start of the run; 0 = afterwards
                           (show the existing .mess file).
    console_path : str   - study_console.txt (Python errors), or None.

    Returns
    -------
    bool - True if the process was started (errors are logged, never
           passed on: the run always continues).
    """
    try:
        python = _monitor_python()
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "aster_convergence_monitor.py")
        if python is None or not os.path.isfile(script):
            log(tr("WARNING: Convergentiescherm niet gestart: Python van "
                   "Code-Aster ({0}) of {1} niet gevonden.",
                   "WARNING: Convergence window not started: Python of "
                   "Code-Aster ({0}) or {1} not found.").format(
                       aster_root(), script))
            return False
        work_dir = os.path.dirname(os.path.abspath(mess_path))
        args = [python, script, "--mess", mess_path,
                # %-formatting: always a point (locale, see bridge_gui)
                "--since", "%.3f" % since,
                "--log", _monitor_log(mess_path),
                "--lang", tr("nl", "en")]
        if console_path:
            args += ["--console", console_path]
        # PYTHONHOME/PYTHONPATH of another Python must not confuse
        # Code-Aster's Python.
        env = dict((k, v) for k, v in os.environ.items()
                   if k.upper() not in ("PYTHONHOME", "PYTHONPATH"))
        proc = subprocess.Popen(args, cwd=work_dir, env=env,
                                creationflags=0x08000000)  # CREATE_NO_WINDOW
        log("INFO: Convergence monitor started (pid {0}).".format(proc.pid))
        return True
    except Exception as e:
        log(tr("WARNING: Convergentiescherm niet gestart: {0}",
               "WARNING: Convergence window not started: {0}").format(
                   str(e)))
        return False


# ==========================================
# START CODE-ASTER
# ==========================================
def run_AsterSolver(export_path, work_dir, resu_name, mw):
    """
    Start Code-Aster via the run_aster.bat launcher in a separate cmd window.

    Parameters
    ----------
    export_path : str  - Path to the study.export file written by
                         bridge_to_aster.py.
    work_dir    : str  - Work folder (cwd for the subprocess).
    resu_name   : str  - File name of the .resu file (unique per run
                         through the timestamp; only used for the log).
    mw          : obj  - Mecway API object for mw.message() (synchronous
                         dialog while Code-Aster runs).

    Returns
    -------
    bool - True if the subprocess was started successfully, False on error.
           Note: this return value says NOTHING about whether the solver
           computed successfully.
    """
    log("--- Running Code_Aster ---")
    exe = exe_aster_path()
    if not os.path.isfile(exe):
        # 'cmd /k' always starts; without this check the window would appear
        # with "not recognised" and then be closed.
        log(tr("ERROR: Code-Aster-launcher niet gevonden: {0} (instelling "
               "op de pagina Algemeen).",
               "ERROR: Code-Aster launcher not found: {0} (setting on the "
               "General page).").format(exe))
        return False

    # The .resu file is NOT created beforehand: if it is missing after the
    # run, AsterToMecway_results() reports that Code-Aster wrote nothing.
    # Only the table route writes a .resu (bridge_to_aster.
    # _export_result_lines); the liml route a result fragment.
    if CONFIG_BRIDGE.get("result_route", "liml") == "tabel":
        log("INFO: Expected result file: {0}".format(resu_name))

    try:
        console_path = os.path.join(work_dir, run_name(CONSOLE_SUFFIX))
        try:
            if os.path.exists(console_path):
                os.remove(console_path)   # not to be confused with an old run
        except OSError:
            pass
        cmd_command, captured = _launch_command(export_path, console_path)
        if not captured:
            log(tr("WARNING: tee.exe niet gevonden in de "
                   "Code-Aster-installatie; de console-uitvoer "
                   "(Python-fouten) wordt niet vastgelegd.",
                   "WARNING: tee.exe not found in the Code-Aster "
                   "installation; the console output (Python errors) is "
                   "not captured."))

        start_time = time.time()
        process = subprocess.Popen(
            cmd_command,
            cwd=work_dir,
            creationflags=0x00000010,  # CREATE_NEW_CONSOLE
        )

        monitor = False
        # Also for linear analyses: then the statistics of the linear
        # solver (MECA_STATIQUE with INFO=2), the messages and the diagnosis.
        if CONFIG_BRIDGE.get("convergence_monitor", True):
            monitor = start_convergence_monitor(
                os.path.join(work_dir, run_name(".mess")), start_time,
                console_path if captured else None)

        mw.message(
            tr("Code_Aster is gestart in een apart venster.\n",
               "Code_Aster has been started in a separate window.\n") +
            (tr("Het convergentiescherm toont de voortgang.\n",
                "The convergence window shows the progress.\n") if monitor
             else "") +
            tr("Klik op OK zodra de berekening klaar is.",
               "Click OK once the calculation has finished.")
        )
        # Clicked OK too early? Then ask once more, because
        # process.terminate() below closes the window (seen in Mecway).
        if not _mess_finished(work_dir, start_time):
            log(tr("WARNING: study.mess is na de eerste OK nog niet "
                   "afgesloten.",
                   "WARNING: study.mess was not yet closed after the first "
                   "OK."))
            mw.message(run_names(tr(
                "Code-Aster is nog niet klaar (study.mess is niet "
                "afgesloten).\nKlik op OK zodra in het venster "
                "'DIAGNOSTIC JOB' staat.",
                "Code-Aster has not finished yet (study.mess is not "
                "closed).\nClick OK once the window shows "
                "'DIAGNOSTIC JOB'."
            )))

        # On an abort or a Python error (no <FIN>) the window stays
        # open: the traceback is there (and in study_console.txt).
        mess_path = os.path.join(work_dir, run_name(".mess"))
        try:
            if (not os.path.exists(mess_path) or
                    os.path.getmtime(mess_path) < start_time - 1.0):
                # No .mess from this run: Code-Aster did not start
                # (properly); the cause is only in the window.
                aborted = True
            else:
                text = _read_mess(mess_path)
                aborted = (_diag_failed(_mess_diagnostic(text)) or
                           (_MESS_DONE in text and _MESS_FIN not in text))
        except Exception:
            aborted = False
        if not aborted and console_errors(work_dir, start_time):
            aborted = True
        if aborted:
            log(tr("WARNING: Code-Aster afgebroken; het venster blijft open.",
                   "WARNING: Code-Aster aborted; the window stays open."))
            return True

        # process.terminate() closes the cmd window. That is fine: errors from
        # study.mess are reported by main() via aster_mess_errors(). The Popen
        # handle only points to the cmd process of the separate window, not to
        # the Code-Aster processes started from it. An error (e.g.
        # window already closed) is ignored.
        try:
            process.terminate()
        except Exception:
            pass
        return True

    except Exception as e:
        log(tr("ERROR: Kon Code-Aster niet starten: {0}",
               "ERROR: Could not start Code-Aster: {0}").format(str(e)))
        return False


# ==========================================
# ERRORS IN study.mess
# ==========================================
def aster_mess_errors(work_dir, since=None):
    """
    Search for errors (<EXCEPTION>, <F>, <S>, <E>) in study.mess.

    Parameters
    ----------
    work_dir : str          - Work folder with study.mess.
    since    : float or None - Start time of the run (time.time()). If
                               study.mess is older, it belongs to an earlier
                               run and is not assessed.

    Returns
    -------
    list of str - Unique messages in order of occurrence, e.g.
                  "<EXCEPTION> <CALCULEL_58>"; empty if there are no errors
                  or the file is missing/outdated (this is logged).
    """
    mess_path = os.path.join(work_dir, run_name(".mess"))
    if not os.path.exists(mess_path) or (
            since is not None and os.path.getmtime(mess_path) < since):
        # No .mess from this run: Code-Aster did not start or stopped
        # immediately; the cause is in the Code-Aster window (which stays
        # open, run_AsterSolver).
        msg = run_names(tr(u"Code-Aster schreef geen study.mess voor deze "
                           u"run; de oorzaak staat in het Code-Aster-venster "
                           u"(bijv. een fout in de installatie of de "
                           u"werkmap).",
                           u"Code-Aster wrote no study.mess for this run; "
                           u"the cause is shown in the Code-Aster window "
                           u"(e.g. an error in the installation or the work "
                           u"folder)."))
        log(u"ERROR: " + msg)
        return [msg]
    hints = mess_hints()
    python_hint = tr(*_PYTHON_HINT)
    errors = []
    seen = set()
    alarms = []
    try:
        text = _read_mess(mess_path)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = _MESS_ERROR_RE.search(line)
            if m:
                code = u"<{0}> <{1}>".format(m.group(1), m.group(2))
                if code not in seen:
                    seen.add(code)
                    msg = u"{0}: {1}".format(code, _mess_box_text(lines, i))
                    if m.group(2) == "FACTOR_57":
                        msg += u" -> " + _resi_advice(
                            _mess_box_text(lines, i, max_chars=2000))
                    elif m.group(2) in hints:
                        msg += u" -> " + hints[m.group(2)]
                    partial = _MESS_PARTIAL_RE.search(text)
                    if partial and m.group(2).startswith("MECANONLINE"):
                        msg += tr(u" Laatste tijdstip met resultaten: {0} s.",
                                  u" Last time with results: {0} s.").format(
                            partial.group(1))
                    errors.append(msg)
                continue
            m = _MESS_ALARM_RE.search(line)
            if m and m.group(1) not in alarms:
                alarms.append(m.group(1))
        modal = _MESS_MODAL_RE.search(text)
        hints = _MODAL_HINTS
        if not modal:
            modal = _MESS_SPECTRUM_RE.search(text)
            hints = _SPECTRUM_HINTS
        if modal:
            pair = hints.get(modal.group(1))
            if pair:
                errors.append(tr(*pair).format(modal.group(2).strip()))
        # Python error in study.comm: only appears in the console output.
        console = _console_text(work_dir, since)
        export_failed = any(key in console for key in _EXPORT_FAIL)
        for err in ([] if modal else console_errors(work_dir, since)):
            if export_failed:
                errors.append(u"{0} -> {1}".format(err, tr(*_EXPORT_HINT)))
            else:
                errors.append(tr(u"Python-fout in study.comm: {0} -> {1}",
                                 u"Python error in study.comm: {0} -> "
                                 u"{1}").format(err, python_hint))
        if not errors and _MESS_UNCAUGHT in text:
            errors.append(tr(u"Code-Aster stopte op een exceptie (\"Trying "
                             u"to close the database after an uncaught "
                             u"exception\"); zie study.mess.",
                             u"Code-Aster stopped on an exception (\"Trying "
                             u"to close the database after an uncaught "
                             u"exception\"); see study.mess."))
        if _MESS_DONE not in text:
            errors.append(tr(u"study.mess is niet afgesloten: Code-Aster is "
                             u"niet klaar of afgebroken.",
                             u"study.mess is not closed: Code-Aster has not "
                             u"finished or was aborted."))
        elif not errors and _diag_failed(_mess_diagnostic(text)):
            # A crash in Python or C (e.g. "Windows fatal exception:
            # access violation", seen in Mecway) gives no message box,
            # only "DIAGNOSTIC JOB : <F>_ABNORMAL_ABORT". The traceback
            # then only appears in the Code-Aster window.
            errors.append(tr(u"DIAGNOSTIC JOB : {0}. Er staat geen melding "
                             u"in study.mess; de oorzaak staat in het "
                             u"Code-Aster-venster.",
                             u"DIAGNOSTIC JOB : {0}. There is no message in "
                             u"study.mess; the cause is shown in the "
                             u"Code-Aster window.").format(
                                 _mess_diagnostic(text)))
        elif not errors and _MESS_FIN not in text:
            # Without captured console output (no tee.exe) this is the
            # only sign of a Python error (SyntaxError: DIAGNOSTIC OK).
            errors.append(tr(u"Code-Aster kwam niet tot FIN (geen '<FIN>' "
                             u"in study.mess, DIAGNOSTIC JOB : {0}): {1}",
                             u"Code-Aster did not reach FIN (no '<FIN>' in "
                             u"study.mess, DIAGNOSTIC JOB : {0}): {1}").format(
                                 _mess_diagnostic(text), python_hint))
    except Exception as e:
        log(tr("WARNING: study.mess niet leesbaar: {0}",
               "WARNING: study.mess not readable: {0}").format(str(e)))
        return []
    for alarm in alarms:
        if alarm in _ALARM_HINTS:
            log(tr(u"WARNING: Code-Aster-alarm {0} in study.mess: {1}",
                   u"WARNING: Code-Aster alarm {0} in study.mess: {1}").format(
                       alarm, tr(*_ALARM_HINTS[alarm])))
            continue
        log(tr(u"WARNING: Code-Aster-alarm {0} in study.mess.",
               u"WARNING: Code-Aster alarm {0} in study.mess.").format(alarm))
    # Messages with the file names of this run (shown in mw.message)
    errors = [run_names(msg) for msg in errors]
    for msg in errors:
        log(tr(u"ERROR: Code-Aster meldt {0}",
               u"ERROR: Code-Aster reports {0}").format(msg))
    return errors
