# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_glossary.py
# Explanations for the main window (bridge_gui): a tooltip per setting
# (SETTING_HELP) and a glossary with the codes and Code-Aster names that
# appear on screen (GLOSSARY, window "Uitleg..."). Text only, in
# both languages (nl, en); the content follows the docs (Handleiding.md,
# Instellingen_contact_en_nietlineair.md, Bezwijken.md, Modaal_en_knik.md).
#
# Extending: a new setting gets a line in SETTING_HELP; a
# new choice value or code a line in GLOSSARY. A choice list shows in
# its tooltip automatically the explanation of the options in GLOSSARY.
#
# Compatible with IronPython 2.7.9.

import textwrap
from collections import OrderedDict

# Width of a tooltip line (characters): a WinForms tooltip does not wrap
# by itself, so long lines become as wide as the screen.
_TIP_WIDTH = 80

# Categories of the glossary, shown in this order.
CATEGORIES = [
    ("mecway", (u"Mecway-analysetypen", u"Mecway analysis types")),
    ("analysis", (u"Analyses van de bridge", u"Bridge analyses")),
    ("command", (u"Code-Aster-commando's", u"Code-Aster commands")),
    ("element", (u"Elementtypen (MODELISATION)",
                 u"Element types (MODELISATION)")),
    ("deformation", (u"Vervorming (DEFORMATION)",
                     u"Deformation (DEFORMATION)")),
    ("material", (u"Materiaalwetten (RELATION)",
                  u"Material laws (RELATION)")),
    ("scheme", (u"Tijdschema's (dynamisch, thermisch)",
                u"Time schemes (dynamic, thermal)")),
    ("solver", (u"Oplosser en convergentie", u"Solver and convergence")),
    ("file", (u"Bestanden en resultaten", u"Files and results")),
    ("other", (u"Overig", u"Other")),
]

# term -> (category, explanation nl, explanation en)
GLOSSARY = OrderedDict([
    # --- Mecway analysis types (<analysis type="...">) ---
    ("S30", ("mecway", u"Mecway: statisch 3D (lineair). Bij 'auto' -> "
             u"lin_static_3d.",
             u"Mecway: static 3D (linear). With 'auto' -> lin_static_3d.")),
    ("L30", ("mecway", u"Mecway: niet-lineair statisch 3D (plasticiteit, "
             u"contact, grote verplaatsingen). Bij 'auto' -> "
             u"nonlin_static_3d.",
             u"Mecway: nonlinear static 3D (plasticity, contact, large "
             u"displacements). With 'auto' -> nonlin_static_3d.")),
    ("D31", ("mecway", u"Mecway: niet-lineaire dynamische respons 3D (in de "
             u"tijd, met massa). Bij 'auto' -> dyna_impl_3d; expliciet kies je "
             u"zelf (dyna_expl_3d).",
             u"Mecway: nonlinear dynamic response 3D (in time, with mass). "
             u"With 'auto' -> dyna_impl_3d; choose explicit yourself "
             u"(dyna_expl_3d).")),
    ("D30", ("mecway", u"Mecway: lineaire dynamische respons 3D (Dynamic "
             u"Response). Met de optie Mode superposition bij 'auto' -> "
             u"dyna_modal_3d (respons op modale basis); zonder (Newmark op "
             u"het hele model) -> dyna_impl_3d (zet daar schema NEWMARK en "
             u"deformation PETIT voor hetzelfde schema als Mecway).",
             u"Mecway: linear dynamic response 3D (Dynamic Response). With "
             u"the option Mode superposition, with 'auto' -> dyna_modal_3d "
             u"(mode superposition); without it (Newmark on the whole "
             u"model) -> dyna_impl_3d (set schema NEWMARK and deformation "
             u"PETIT there for the same scheme as Mecway).")),
    ("T30", ("mecway", u"Mecway: thermisch stationair 3D. Bij 'auto' -> "
             u"ther_3d.",
             u"Mecway: thermal steady state 3D. With 'auto' -> ther_3d.")),
    ("T31", ("mecway", u"Mecway: thermisch transient 3D (in de tijd). Bij "
             u"'auto' -> ther_3d.",
             u"Mecway: thermal transient 3D (in time). With 'auto' -> "
             u"ther_3d.")),
    ("V30", ("mecway", u"Mecway: frequentie (modaal) 3D, eigenfrequenties en "
             u"trillingsvormen. Bij 'auto' -> modal_3d; met een fluidum-"
             u"onderdeel (materiaal met Speed of sound zonder Young's "
             u"modulus) -> vibroacoustic_modes_3d.",
             u"Mecway: frequency (modal) 3D, natural frequencies and mode "
             u"shapes. With 'auto' -> modal_3d; with a fluid part (material "
             u"with Speed of sound without Young's modulus) -> "
             u"vibroacoustic_modes_3d.")),
    ("B30", ("mecway", u"Mecway: lineaire knik 3D, kniklastfactoren en "
             u"knikvormen. Bij 'auto' -> buckling_3d.",
             u"Mecway: linear buckling 3D, buckling factors and buckling "
             u"mode shapes. With 'auto' -> buckling_3d.")),
    ("A30", ("mecway", u"Mecway: Acoustic Resonance 3D, holtemodes van een "
             u"lucht- of vloeistofvolume (drukveld per mode). Bij 'auto' -> "
             u"acoustic_modes_3d, met een bron (BRON_-selectie of "
             u"#ASTER-BRON) acoustic_harm_3d. A20 (2D) wordt niet "
             u"vertaald.",
             u"Mecway: Acoustic Resonance 3D, cavity modes of an air or "
             u"fluid volume (pressure field per mode). With 'auto' -> "
             u"acoustic_modes_3d, with a source (SOURCE_ selection or "
             u"#ASTER-BRON) acoustic_harm_3d. A20 (2D) is not "
             u"translated.")),
    # --- analyses of the bridge ---
    ("auto", ("analysis", u"De analyse volgt het analysetype van het "
              u"Mecway-model (S30, L30, D30, D31, T30, T31, V30, B30, A30). Andere "
              u"typen stoppen de bridge met een melding.",
              u"The analysis follows the analysis type of the Mecway model "
              u"(S30, L30, D30, D31, T30, T31, V30, B30, A30). Other types stop the "
              u"bridge with a message.")),
    ("lin_static_3d", ("analysis", u"Statisch, lineair (MECA_STATIQUE). "
                       u"Geen contact, gap, tension/compression only.",
                       u"Static, linear (MECA_STATIQUE). No contact, gap, "
                       u"tension/compression only.")),
    ("nonlin_static_3d", ("analysis", u"Niet-lineair statisch "
                          u"(STAT_NON_LINE): plasticiteit, contact, grote "
                          u"verplaatsingen, bezwijken; in stappen tot de "
                          u"eindtijd.",
                          u"Nonlinear static (STAT_NON_LINE): plasticity, "
                          u"contact, large displacements, failure; in steps "
                          u"up to the end time.")),
    ("dyna_impl_3d", ("analysis", u"Dynamisch, impliciet (DYNA_NON_LINE met "
                      u"HHT of NEWMARK): grotere tijdstappen, met "
                      u"Newton-iteraties.",
                      u"Dynamic, implicit (DYNA_NON_LINE with HHT or "
                      u"NEWMARK): larger time steps, with Newton "
                      u"iterations.")),
    ("dyna_expl_3d", ("analysis", u"Dynamisch, expliciet (DYNA_NON_LINE met "
                      u"DIFF_CENT): zeer kleine tijdstappen, geen "
                      u"iteraties; voor snelle gebeurtenissen (impact).",
                      u"Dynamic, explicit (DYNA_NON_LINE with DIFF_CENT): "
                      u"very small time steps, no iterations; for fast "
                      u"events (impact).")),
    ("ther_3d", ("analysis", u"Thermisch (THER_LINEAIRE of THER_NON_LINE), "
                 u"stationair of transient.",
                 u"Thermal (THER_LINEAIRE or THER_NON_LINE), steady state or "
                 u"transient.")),
    ("modal_3d", ("analysis", u"Modaal (CALC_MODES): eigenfrequenties en "
                  u"trillingsvormen met de massa en de opleggingen; "
                  u"belastingen geven, zoals in Mecway, voorspanning "
                  u"(stress stiffening, docs/Modaal_en_knik.md).",
                  u"Modal (CALC_MODES): natural frequencies and mode shapes "
                  u"with the mass and the supports; loads give prestress, "
                  u"as in Mecway (stress stiffening, "
                  u"docs/en/Modal_and_buckling.md).")),
    ("dyna_modal_3d", ("analysis", u"Respons op modale basis (Mecway D30 "
                       u"met Mode superposition): eigenmodes (CALC_MODES), "
                       u"de modale vergelijkingen in de tijd (DYNA_VIBRA "
                       u"GENE) en terug naar de knopen; lineair, met "
                       u"Rayleigh- of modale demping "
                       u"(docs/Respons_op_modale_basis.md).",
                       u"Mode superposition (Mecway D30 with Mode "
                       u"superposition): eigenmodes (CALC_MODES), the modal "
                       u"equations in time (DYNA_VIBRA GENE) and back to the "
                       u"nodes; linear, with Rayleigh or modal damping "
                       u"(docs/en/Mode_superposition.md).")),
    ("harmonic_3d", ("analysis", u"Harmonische respons (frequentiedomein): "
                     u"stationaire respons op een sinusvormige last F "
                     u"e^(i w t) per frequentie, op modale basis (CALC_MODES, "
                     u"DYNA_VIBRA HARM GENE) of direct (PHYS); het Mecway-"
                     u"model is een Frequency- of Dynamic-Response-analyse. "
                     u"Velden per frequentie: amplitude, fase, Re/Im; "
                     u"meetpunten MEETPUNT_... (docs/Respons_op_modale_basis"
                     u".md). Kies deze analyse zelf (niet via 'auto').",
                     u"Harmonic response (frequency domain): steady-state "
                     u"response to a sinusoidal load F e^(i w t) per "
                     u"frequency, on a modal basis (CALC_MODES, DYNA_VIBRA "
                     u"HARM GENE) or direct (PHYS); the Mecway model is a "
                     u"Frequency or Dynamic Response analysis. Fields per "
                     u"frequency: amplitude, phase, Re/Im; probes PROBE_... "
                     u"(docs/en/Mode_superposition.md). Choose this analysis "
                     u"yourself (not via 'auto').")),
    ("spectrum_3d", ("analysis", u"Responsspectrum (aardbeving, schok): "
                     u"eigenmodes (CALC_MODES), per mode de respons op het "
                     u"spectrum en de combinatie over modes en richtingen "
                     u"(COMB_SISM_MODAL); het Mecway-model is een Frequency-"
                     u"analyse met een Gravity met tabel als spectrum. "
                     u"Resultaat: maxima zonder teken, een stap "
                     u"(docs/Spectrumanalyse.md). Kies deze analyse zelf "
                     u"(niet via 'auto').",
                     u"Response spectrum (earthquake, shock): eigenmodes "
                     u"(CALC_MODES), per mode the response to the spectrum "
                     u"and the combination over modes and directions "
                     u"(COMB_SISM_MODAL); the Mecway model is a Frequency "
                     u"analysis with a Gravity with a table as the spectrum. "
                     u"Result: maxima without sign, one step "
                     u"(docs/en/Response_spectrum.md). Choose this analysis "
                     u"yourself (not via 'auto').")),
    ("buckling_3d", ("analysis", u"Lineaire knik: statische berekening met "
                     u"de belastingen, dan CALC_MODES MODE_FLAMB: "
                     u"kniklastfactoren (veelvoud van de aangebrachte last) "
                     u"en knikvormen.",
                     u"Linear buckling: static analysis with the loads, then "
                     u"CALC_MODES MODE_FLAMB: buckling factors (multiple of "
                     u"the applied load) and buckling mode shapes.")),
    ("acoustic_modes_3d", ("analysis", u"Akoestische holtemodes "
                           u"(PHENOMENE ACOUSTIQUE, CALC_MODES): "
                           u"frequenties en drukveld per mode; harde "
                           u"wanden, fluid pressure = 0 is een drukknoop; "
                           u"met impedance complexe modes (frequentie, "
                           u"decay rate, pressure + pressurei, zoals Mecway) "
                           u"(docs/Akoestiek.md).",
                           u"Acoustic cavity modes (PHENOMENE ACOUSTIQUE, "
                           u"CALC_MODES): frequencies and pressure field "
                           u"per mode; hard walls, fluid pressure = 0 is a "
                           u"pressure node; with impedance complex modes "
                           u"(frequency, decay rate, pressure + pressurei, "
                           u"like Mecway) (docs/en/Acoustics.md).")),
    ("acoustic_harm_3d", ("analysis", u"Akoestiek harmonisch (PHENOMENE "
                          u"ACOUSTIQUE, DYNA_VIBRA HARM): drukveld per "
                          u"frequentie bij een bron (vlakselectie BRON_..., "
                          u"#ASTER-BRON of fluid pressure != 0), met "
                          u"absorberende randen (ABSORBEREND_... of een "
                          u"reele impedance) en microfoons (knoopselectie "
                          u"MICROFOON_...): velden pressure, pressurei, "
                          u"pressuremag, pressurephase, spl "
                          u"(docs/Akoestiek.md).",
                          u"Acoustics harmonic (PHENOMENE ACOUSTIQUE, "
                          u"DYNA_VIBRA HARM): pressure field per frequency "
                          u"from a source (face selection SOURCE_..., "
                          u"#ASTER-BRON or fluid pressure != 0), with "
                          u"absorbing boundaries (ABSORBING_... or a real "
                          u"impedance) and microphones (node selection "
                          u"MICROPHONE_...): fields pressure, pressurei, "
                          u"pressuremag, pressurephase, spl "
                          u"(docs/en/Acoustics.md).")),
    ("vibroacoustic_modes_3d", ("analysis", u"Vibro-akoestiek: gekoppelde "
                                u"modes van een constructie en een lucht- "
                                u"of vloeistofvolume (3D_FLUIDE, FLUI_STRU, "
                                u"U_P_PHI, CALC_MODES BANDE): verplaatsing in "
                                u"de constructie en druk (pressure) in het "
                                u"fluidum per mode. Fluidum = onderdeel met "
                                u"een materiaal met Speed of sound zonder "
                                u"Young's modulus (of naam LUCHT_/FLUID_); "
                                u"p = 0 met een selectie OPEN_... "
                                u"(docs/Akoestiek.md).",
                                u"Vibroacoustics: coupled modes of a "
                                u"structure and an air or liquid volume "
                                u"(3D_FLUIDE, FLUI_STRU, U_P_PHI, CALC_MODES "
                                u"BANDE): displacement in the structure and "
                                u"pressure in the fluid per mode. Fluid = "
                                u"part with a material with Speed of sound "
                                u"without Young's modulus (or name LUCHT_/"
                                u"FLUID_); p = 0 with a selection OPEN_... "
                                u"(docs/en/Acoustics.md).")),
    ("vibroacoustic_harm_3d", ("analysis", u"Vibro-akoestiek harmonisch: "
                               u"hetzelfde model als vibroacoustic_modes_3d "
                               u"per frequentie (DYNA_VIBRA HARM PHYS, "
                               u"3D_FLUI_ABSO): verplaatsing van de "
                               u"constructie en druk/SPL in het fluidum bij "
                               u"krachten op de constructie, een BRON_- of "
                               u"INVALLEND_-vlak of #ASTER-BRON, met "
                               u"absorberende randen (ABSORBEREND_, reele "
                               u"impedance) en microfoons (MICROFOON_). Zelf "
                               u"kiezen (docs/Akoestiek.md par. 7).",
                               u"Vibroacoustics harmonic: the same model as "
                               u"vibroacoustic_modes_3d per frequency "
                               u"(DYNA_VIBRA HARM PHYS, 3D_FLUI_ABSO): "
                               u"displacement of the structure and "
                               u"pressure/SPL in the fluid from forces on the "
                               u"structure, a SOURCE_ or INCIDENT_ face or "
                               u"#ASTER-BRON, with absorbing boundaries "
                               u"(ABSORBING_, real impedance) and "
                               u"microphones (MICROPHONE_). Choose it "
                               u"yourself (docs/en/Acoustics.md section "
                               u"7).")),
    # --- Code-Aster commands ---
    ("MECA_STATIQUE", ("command", u"Code-Aster: lineaire statische "
                       u"berekening (een stap).",
                       u"Code-Aster: linear static analysis (one step).")),
    ("STAT_NON_LINE", ("command", u"Code-Aster: niet-lineaire statische "
                       u"berekening in tijdstappen met Newton-iteraties.",
                       u"Code-Aster: nonlinear static analysis in time steps "
                       u"with Newton iterations.")),
    ("DYNA_NON_LINE", ("command", u"Code-Aster: niet-lineaire dynamische "
                       u"berekening (impliciet of expliciet).",
                       u"Code-Aster: nonlinear dynamic analysis (implicit or "
                       u"explicit).")),
    ("THER_LINEAIRE", ("command", u"Code-Aster: lineaire thermische "
                       u"berekening.",
                       u"Code-Aster: linear thermal analysis.")),
    ("THER_NON_LINE", ("command", u"Code-Aster: niet-lineaire thermische "
                       u"berekening (straling, convectie op schaalvlakken).",
                       u"Code-Aster: nonlinear thermal analysis (radiation, "
                       u"convection on shell faces).")),
    ("CALC_MODES", ("command", u"Code-Aster: eigenwaarden berekenen; "
                    u"trillingen (frequenties, met massamatrix) of knik "
                    u"(MODE_FLAMB, met geometrische stijfheid).",
                    u"Code-Aster: compute eigenvalues; vibration "
                    u"(frequencies, with mass matrix) or buckling "
                    u"(MODE_FLAMB, with geometric stiffness).")),
    ("COMB_SISM_MODAL", ("command", u"Code-Aster: responsspectrum op "
                         u"modale basis: per mode S_a(f, xi) x participatie "
                         u"/ omega^2 x vorm, gecombineerd over de modes "
                         u"(CQC, SRSS, ...) en de richtingen; met MODE_CORR "
                         u"de missing mass (pseudo-modes, MODE_STATIQUE).",
                         u"Code-Aster: response spectrum on a modal basis: "
                         u"per mode S_a(f, xi) x participation / omega^2 x "
                         u"shape, combined over the modes (CQC, SRSS, ...) "
                         u"and the directions; with MODE_CORR the missing "
                         u"mass (pseudo-modes, MODE_STATIQUE).")),
    ("dorfler", ("other", u"Dorfler-keuze (bulk criterion, Dorfler 1996) "
                 u"bij adaptieve verfijning: de elementen met de grootste "
                 u"fout tot ze samen een fractie van de totale fout (som "
                 u"eta_e^2) dragen.",
                 u"Dorfler marking (bulk criterion, Dorfler 1996) in "
                 u"adaptive refinement: the elements with the largest error "
                 u"until together they carry a fraction of the total error "
                 u"(sum eta_e^2).")),
    ("fraction", ("other", u"Adaptieve verfijning: een vaste fractie van de "
                  u"elementen met de grootste fout.",
                  u"Adaptive refinement: a fixed fraction of the elements "
                  u"with the largest error.")),
    ("factor", ("other", u"Adaptieve verfijning: elementen met een fout "
                u"groter dan een factor x de gemiddelde fout.",
                u"Adaptive refinement: elements with an error larger than "
                u"a factor x the mean error.")),
    ("CQC", ("other", u"Complete Quadratic Combination: modale combinatie "
             u"met de correlatie tussen modes met dicht bij elkaar liggende "
             u"frequenties (Der Kiureghian); gelijk aan SRSS als de "
             u"frequenties ver uit elkaar liggen. Standaard.",
             u"Complete Quadratic Combination: modal combination with the "
             u"correlation between modes with close frequencies (Der "
             u"Kiureghian); equal to SRSS when the frequencies are far "
             u"apart. Default.")),
    ("SRSS", ("other", u"Square Root of the Sum of Squares: wortel uit de "
              u"som van de kwadraten (modes of richtingen onafhankelijk). "
              u"Voor modes alleen goed als de frequenties ver uit elkaar "
              u"liggen.",
              u"Square Root of the Sum of Squares (modes or directions "
              u"independent). For modes only correct when the frequencies "
              u"are well separated.")),
    ("ABS", ("other", u"Som van de absolute waarden: bovengrens, zeer "
             u"conservatief.",
             u"Sum of the absolute values: upper bound, very "
             u"conservative.")),
    ("100-30-30", ("other", u"Richtingscombinatie E_a + 0,30 E_b + 0,30 E_c, "
                   u"de grootste over de richtingen (EN 1998-1 par. "
                   u"4.3.3.5.2).",
                   u"Direction combination E_a + 0.30 E_b + 0.30 E_c, the "
                   u"largest over the directions (EN 1998-1 section "
                   u"4.3.3.5.2).")),
    ("100-40-40", ("other", u"Richtingscombinatie met 0,40 (Newmark; "
                   u"Code-Aster COMB_DIRECTION='NEWMARK', de standaard van "
                   u"Code-Aster).",
                   u"Direction combination with 0.40 (Newmark; Code-Aster "
                   u"COMB_DIRECTION='NEWMARK', the Code-Aster default).")),
    ("period", ("other", u"Spectrumtabel in de gravity: de kolom 'time' is "
                u"de periode T [s] (zoals in normen, bijv. EN 1998-1).",
                u"Spectrum table in the gravity: the 'time' column is the "
                u"period T [s] (as in codes, e.g. EN 1998-1).")),
    ("frequency", ("other", u"Spectrumtabel in de gravity: de kolom 'time' "
                   u"is de frequentie f [Hz] (alleen het getal telt).",
                   u"Spectrum table in the gravity: the 'time' column is the "
                   u"frequency f [Hz] (only the number counts).")),
    ("DYNA_VIBRA", ("command", u"Code-Aster: lineaire dynamica; de bridge "
                    u"gebruikt BASE_CALCUL='GENE' (in de modale "
                    u"coordinaten, na PROJ_BASE) met TYPE_CALCUL='TRAN' (in "
                    u"de tijd) of 'HARM' (per frequentie: harmonic_3d, "
                    u"akoestiek); REST_GENE_PHYS zet de respons terug op de "
                    u"knopen.",
                    u"Code-Aster: linear dynamics; the bridge uses "
                    u"BASE_CALCUL='GENE' (in modal coordinates, after "
                    u"PROJ_BASE) with TYPE_CALCUL='TRAN' (in time) or "
                    u"'HARM' (per frequency: harmonic_3d, acoustics); "
                    u"REST_GENE_PHYS puts the response back on the "
                    u"nodes.")),
    ("GENE", ("other", u"Harmonisch: op modale basis (DYNA_VIBRA "
              u"BASE_CALCUL='GENE'): snel, met modale demping; alleen de "
              u"gerekende modes doen mee (modale truncatie).",
              u"Harmonic: on a modal basis (DYNA_VIBRA BASE_CALCUL='GENE'): "
              u"fast, with modal damping; only the computed modes take part "
              u"(modal truncation).")),
    ("PHYS", ("other", u"Harmonisch: direct op het hele model (DYNA_VIBRA "
              u"BASE_CALCUL='PHYS'): exact voor het mesh (geen modale "
              u"truncatie), een oplossing per frequentie; Rayleigh-demping "
              u"en dempers, geen modal_damping. Controle van GENE.",
              u"Harmonic: directly on the whole model (DYNA_VIBRA "
              u"BASE_CALCUL='PHYS'): exact for the mesh (no modal "
              u"truncation), one solution per frequency; Rayleigh damping "
              u"and dampers, no modal_damping. Check of GENE.")),
    ("MODE_ITER_CYCL", ("command", u"Code-Aster: modes van een cyclisch "
                        u"symmetrische constructie (wiel, schijf) uit een "
                        u"sector, per aantal nodal diameters (ND), met de "
                        u"modes van de sector met vaste snijvlakken als basis "
                        u"(Craig-Bampton; bridge_cyclic.py).",
                        u"Code-Aster: modes of a cyclically symmetric "
                        u"structure (wheel, disc) from one sector, per number "
                        u"of nodal diameters (ND), with the modes of the "
                        u"sector with fixed cut faces as the basis "
                        u"(Craig-Bampton; bridge_cyclic.py).")),
    ("DEFI_SQUELETTE", ("command", u"Code-Aster: skelet (mesh) van het hele "
                        u"wiel uit de sector bij cyclische symmetrie; "
                        u"REST_SOUS_STRUC SQUELETTE zet de modes daarop "
                        u"(instelling cyclic_full_wheel).",
                        u"Code-Aster: skeleton (mesh) of the whole wheel from "
                        u"the sector with cyclic symmetry; REST_SOUS_STRUC "
                        u"SQUELETTE puts the modes on it (setting "
                        u"cyclic_full_wheel).")),
    ("MODE_FLAMB", ("command", u"CALC_MODES voor knik: (K + lambda Kg) x = 0; "
                    u"lambda (CHAR_CRIT) is de kniklastfactor.",
                    u"CALC_MODES for buckling: (K + lambda Kg) x = 0; lambda "
                    u"(CHAR_CRIT) is the buckling factor.")),
    ("RIGI_GEOM", ("command", u"Geometrische stijfheid (spanningsstijfheid) "
                   u"uit het spanningsveld van de statische berekening; "
                   u"bepaalt de knik.",
                   u"Geometric (stress) stiffness from the stress field of "
                   u"the static analysis; determines buckling.")),
    ("CRIT_STAB", ("command", u"Stabiliteitscriterium in STAT_NON_LINE na "
                   u"elke stap: kleine verplaatsingen (K_T + lambda K_g) x "
                   u"= 0, lambda = kritische lastfactor; grote "
                   u"verplaatsingen (K_T + lambda I) x = 0, lambda naar 0 = "
                   u"knik (docs/Modaal_en_knik.md par. 5).",
                   u"Stability criterion in STAT_NON_LINE after each step: "
                   u"small displacements (K_T + lambda K_g) x = 0, lambda = "
                   u"critical load factor; large displacements (K_T + "
                   u"lambda I) x = 0, lambda to 0 = buckling "
                   u"(docs/en/Modal_and_buckling.md section 5).")),
    ("CALC_ERREUR", ("command", u"Foutschatter: ERME = residu-schatter per "
                     u"element (evenwicht in het element, sprongen van de "
                     u"spanning tussen elementen, last op de rand). In "
                     u"Mecway errorestimate (absoluut) en errorestimaterel "
                     u"(% per element); de globale relatieve fout in de log "
                     u"(docs/Foutschatter.md).",
                     u"Error estimator: ERME = residual estimator per "
                     u"element (equilibrium in the element, stress jumps "
                     u"between elements, load on the boundary). In Mecway "
                     u"errorestimate (absolute) and errorestimaterel (% per "
                     u"element); the global relative error in the log "
                     u"(docs/en/Error_estimator.md).")),
    ("DEFI_FOND_FISS", ("command", u"Breukmechanica: het scheurfront "
                        u"(SCHEUR_FRONT) en de lippen (SCHEUR_LIP_BOVEN/"
                        u"_ONDER) als scheur voor CALC_G en POST_K1_K2_K3 "
                        u"(docs/Breukmechanica.md).",
                        u"Fracture mechanics: the crack front (CRACK_FRONT) "
                        u"and the lips (CRACK_LIP_UPPER/_LOWER) as a crack "
                        u"for CALC_G and POST_K1_K2_K3 "
                        u"(docs/en/Fracture_mechanics.md).")),
    ("CALC_G", ("command", u"Energie-afgifte G (theta-methode) en "
                u"spanningsintensiteitsfactoren K_I, K_II, K_III "
                u"(interactie-integraal) per knoop langs het scheurfront; "
                u"in de log, het statusvak en <model>_<run>_scheur.csv.",
                u"Energy release rate G (theta method) and stress intensity "
                u"factors K_I, K_II, K_III (interaction integral) per node "
                u"along the crack front; in the log, the status box and "
                u"<model>_<run>_scheur.csv.")),
    ("POST_K1_K2_K3", ("command", u"K_I, K_II, K_III uit de sprong in de "
                       u"verplaatsing over de lippen (extrapolatie naar het "
                       u"front); in de bridge een controle op CALC_G, "
                       u"nauwkeurig met kwadratische elementen.",
                       u"K_I, K_II, K_III from the displacement jump across "
                       u"the lips (extrapolated to the front); in the bridge "
                       u"a check on CALC_G, accurate with quadratic "
                       u"elements.")),
    # --- element types ---
    ("3D", ("element", u"Volume-element, volledig geintegreerd. Hex8 is "
            u"stijver dan in Mecway (geen incompatibele modes).",
            u"Solid element, fully integrated. Hex8 is stiffer than in "
            u"Mecway (no incompatible modes).")),
    ("3D_SI", ("element", u"Volume-element met onderintegratie (alleen "
               u"hex8): minder stijf, maar bij 1 element over de dikte ~0 "
               u"buigspanning.",
               u"Solid element with reduced integration (hex8 only): less "
               u"stiff, but ~0 bending stress with 1 element through the "
               u"thickness.")),
    ("LINE_QUAD", ("element", u"Code-Aster maakt lineaire volume-elementen "
                   u"kwadratisch (hex8 -> hex20, tet4 -> tet10): buiging "
                   u"klopt, ~3x zoveel knopen. Alleen als verder niets "
                   u"lineair blijft (geen balken, veren, DKT-schalen), zonder "
                   u"kwadratische volume-elementen en niet expliciet; anders "
                   u"3D met een WARNING.",
                   u"Code-Aster makes linear solid elements quadratic (hex8 "
                   u"-> hex20, tet4 -> tet10): bending is correct, ~3x as many "
                   u"nodes. Only if nothing else stays linear (no beams, "
                   u"springs, DKT shells), without quadratic solid elements "
                   u"and not explicit; otherwise 3D with a WARNING.")),
    ("DKT", ("element", u"Dunne schaal (Kirchhoff), voor tri3/quad4.",
             u"Thin shell (Kirchhoff), for tri3/quad4.")),
    ("DST", ("element", u"Schaal met dwarskrachtvervorming (Mindlin); alleen "
             u"in de lineaire statische analyse, anders DKT (WARNING).",
             u"Shell with transverse shear deformation (Mindlin); only in "
             u"the linear static analysis, otherwise DKT (WARNING).")),
    ("COQUE_3D", ("element", u"Kwadratische schaal (quad9/tria7); nodig "
                  u"voor grote rotaties van schalen. Lineaire schalen worden "
                  u"eerst kwadratisch gemaakt; delen ze knopen met elementen "
                  u"die lineair blijven, dan DKT (WARNING).",
                  u"Quadratic shell (quad9/tria7); needed for large "
                  u"rotations of shells. Linear shells are made quadratic "
                  u"first; if they share nodes with elements that stay "
                  u"linear, DKT is used (WARNING).")),
    ("POU_D_E", ("element", u"Balk volgens Euler-Bernoulli (zonder "
                 u"afschuifvervorming), zoals Mecway.",
                 u"Euler-Bernoulli beam (no shear deformation), like "
                 u"Mecway.")),
    ("POU_D_T", ("element", u"Balk volgens Timoshenko (met "
                 u"afschuifvervorming).",
                 u"Timoshenko beam (with shear deformation).")),
    ("POU_D_T_GD", ("element", u"Balk volgens Timoshenko met grote "
                    u"verplaatsingen en rotaties (ELAS_POUTRE_GR, "
                    u"GROT_GDEP), elastisch. Alleen in niet-lineair "
                    u"statisch met grote verplaatsingen; elders POU_D_T. "
                    u"Geen balkspanningen, snedekrachten een waarde per "
                    u"element.",
                    u"Timoshenko beam with large displacements and "
                    u"rotations (ELAS_POUTRE_GR, GROT_GDEP), elastic. Only "
                    u"in nonlinear static with large displacements; "
                    u"elsewhere POU_D_T. No beam stresses, section forces "
                    u"one value per element.")),
    ("BARRE", ("element", u"Staaf (Mecway truss): alleen normaalkracht, "
               u"kleine verplaatsingen.",
               u"Bar (Mecway truss): axial force only, small "
               u"displacements.")),
    ("DIS_T", ("element", u"Discreet element (veer, demper, massa) met "
               u"alleen verplaatsingen; veren en dempers werken langs de "
               u"eigen as van het element.",
               u"Discrete element (spring, damper, mass) with translations "
               u"only; springs and dampers act along the element's own "
               u"axis.")),
    ("DIS_TR", ("element", u"Discreet element met verplaatsingen en "
                u"rotaties (bijv. een knoopmassa met rotatietraagheid).",
                u"Discrete element with translations and rotations (e.g. a "
                u"nodal mass with rotational inertia).")),
    # --- DEFORMATION ---
    ("PETIT", ("deformation", u"Kleine verplaatsingen, rotaties en rekken; "
               u"de vorm van het model verandert niet in de berekening.",
               u"Small displacements, rotations and strains; the shape of "
               u"the model does not change in the analysis.")),
    ("PETIT_REAC", ("deformation", u"Kleine rekken, maar de geometrie wordt "
                    u"per stap bijgewerkt; niet geschikt voor grote "
                    u"rotaties.",
                    u"Small strains, but the geometry is updated each step; "
                    u"not suitable for large rotations.")),
    ("GROT_GDEP", ("deformation", u"Grote verplaatsingen en rotaties. De "
                   u"bridge kiest per elementtype de vorm die Code-Aster "
                   u"toestaat (volume: GREEN_LAGRANGE of GDEF_LOG; "
                   u"COQUE_3D: GROT_GDEP). Balken en DKT/DST-schalen blijven "
                   u"geometrisch lineair (WARNING in de log); kies voor "
                   u"grote rotaties van schalen COQUE_3D.",
                   u"Large displacements and rotations. The bridge chooses "
                   u"the form Code-Aster allows per element type (solid: "
                   u"GREEN_LAGRANGE or GDEF_LOG; COQUE_3D: GROT_GDEP). Beams "
                   u"and DKT/DST shells stay geometrically linear (WARNING "
                   u"in the log); for large rotations of shells choose "
                   u"COQUE_3D.")),
    ("GDEF_LOG", ("deformation", u"Grote vervormingen met logaritmische "
                  u"rek; voor plastische volume-elementen.",
                  u"Large deformations with logarithmic strain; for plastic "
                  u"solid elements.")),
    ("GREEN_LAGRANGE", ("deformation", u"Grote verplaatsingen, kleine rekken "
                        u"(Green-Lagrange-rek); voor elastische volumes.",
                        u"Large displacements, small strains (Green-Lagrange "
                        u"strain); for elastic solids.")),
    ("SIMO_MIEHE", ("deformation", u"Grote plastische vervormingen "
                    u"(alternatief voor GDEF_LOG); niet met kinematische "
                    u"versteviging.",
                    u"Large plastic deformations (alternative to GDEF_LOG); "
                    u"not with kinematic hardening.")),
    # --- material laws ---
    ("ELAS", ("material", u"Lineair elastisch.", u"Linear elastic.")),
    ("VMIS_ISOT_TRAC", ("material", u"Von Mises-plasticiteit, isotrope "
                        u"versteviging volgens een spanning-rekcurve "
                        u"(hardingscurve, Ramberg-Osgood, PLAS_TAB).",
                        u"Von Mises plasticity, isotropic hardening from a "
                        u"stress-strain curve (hardening curve, "
                        u"Ramberg-Osgood, PLAS_TAB).")),
    ("VMIS_ISOT_LINE", ("material", u"Von Mises-plasticiteit, isotroop "
                        u"bilineair (vloeigrens + helling).",
                        u"Von Mises plasticity, isotropic bilinear (yield "
                        u"stress + slope).")),
    ("VMIS_CINE_LINE", ("material", u"Von Mises-plasticiteit, kinematisch "
                        u"bilineair (Bauschinger-effect); bezwijken met de "
                        u"huidige plastische rek (uit de terugspanning).",
                        u"Von Mises plasticity, kinematic bilinear "
                        u"(Bauschinger effect); failure uses the current "
                        u"plastic strain (from the back stress).")),
    ("EPSPEQ", ("material", u"Vergelijkingsplastische rek (interne variabele "
                u"V1); bepaalt het bezwijken.",
                u"Equivalent plastic strain (internal variable V1); decides "
                u"failure.")),
    ("PLAS_TAB", ("material", u"OpenRadioss-materiaalkaart (LAW36) met een "
                  u"spanning-rekcurve en Eps_p_max.",
                  u"OpenRadioss material card (LAW36) with a stress-strain "
                  u"curve and Eps_p_max.")),
    ("Eps_p_max", ("material", u"Bezwijkgrens (plastische rek) uit "
                   u"PLAS_TAB; de bridge maakt er bezwijken van elementen "
                   u"van.",
                   u"Failure limit (plastic strain) from PLAS_TAB; the bridge "
                   u"turns it into element failure.")),
    # A second 'auto' (strain definition) has its own key: an
    # OrderedDict keeps only one value per key.
    ("auto (curve)", ("other", u"Rekdefinitie hardingscurve: afgeleid uit het "
              u"eerste punt ((0,0) of rek > 0 -> totaal, zoals Mecway; "
              u"(0, spanning) -> plastisch, met een waarschuwing).",
              u"Strain definition of the hardening curve: derived from the "
              u"first point ((0,0) or strain > 0 -> total, like Mecway; "
              u"(0, stress) -> plastic, with a warning).")),
    ("auto (configuration)", ("other", u"Configuratie: de enige "
              u"configuratie van het model, anders de enige zonder "
              u"onderdrukte items, anders de eerste (met een waarschuwing).",
              u"Configuration: the only configuration of the model, else "
              u"the only one without suppressed items, else the first "
              u"(with a warning).")),
    ("plastic", ("other", u"Rekdefinitie hardingscurve: de rek is de "
                 u"plastische rek.",
                 u"Strain definition of the hardening curve: the strain is "
                 u"the plastic strain.")),
    ("total", ("other", u"Rekdefinitie hardingscurve: de rek is de totale "
               u"rek (elastisch + plastisch).",
               u"Strain definition of the hardening curve: the strain is "
               u"the total strain (elastic + plastic).")),
    # --- time schemes ---
    ("HHT", ("scheme", u"Impliciet schema met instelbare numerieke demping "
             u"(HHT ALPHA, -0.3 .. 0); dempt hoge frequenties.",
             u"Implicit scheme with adjustable numerical damping (HHT ALPHA, "
             u"-0.3 .. 0); damps high frequencies.")),
    ("NEWMARK", ("scheme", u"Impliciet schema (gemiddelde versnelling), "
                 u"zonder numerieke demping.",
                 u"Implicit scheme (average acceleration), without numerical "
                 u"damping.")),
    ("DIFF_CENT", ("scheme", u"Expliciet schema (centrale differenties); "
                   u"stap kleiner dan de kritieke tijdstap.",
                   u"Explicit scheme (central differences); step smaller "
                   u"than the critical time step.")),
    ("TCHAMWA", ("scheme", u"Expliciet schema met lichte numerieke demping.",
                 u"Explicit scheme with slight numerical damping.")),
    ("THETA", ("scheme", u"Thermisch tijdschema (theta-methode): 0 = "
               u"expliciet, 0.5 = Crank-Nicolson, 1 = impliciet Euler; "
               u"standaard 0.57 (Code-Aster).",
               u"Thermal time scheme (theta method): 0 = explicit, 0.5 = "
               u"Crank-Nicolson, 1 = implicit Euler; default 0.57 "
               u"(Code-Aster).")),
    # --- solver and convergence ---
    ("MUMPS", ("solver", u"Directe lineaire oplosser van Code-Aster "
               u"(factorisatie van de matrix; robuust, standaard).",
               u"Direct linear solver of Code-Aster (factorization of the "
               u"matrix; robust, default).")),
    ("GCPC", ("solver", u"Iteratieve lineaire oplosser (geconjugeerde "
              u"gradient met onvolledige factorisatie LDLT_INC); minder "
              u"geheugen, het convergentiescherm toont het residu per "
              u"iteratie. Alleen voor goed geconditioneerde modellen.",
              u"Iterative linear solver (conjugate gradient with incomplete "
              u"factorization LDLT_INC); less memory, the convergence "
              u"window shows the residual per iteration. Only for "
              u"well-conditioned models.")),
    ("RESI_RELA", ("solver", u"Nauwkeurigheid van de lineaire oplosser: "
                   u"bij MUMPS de grens voor de geschatte relatieve fout op "
                   u"de oplossing, bij GCPC het residu ||r||/||f|| waarop "
                   u"de iteraties stoppen.",
                   u"Accuracy of the linear solver: with MUMPS the limit for "
                   u"the estimated relative error of the solution, with GCPC "
                   u"the residual ||r||/||f|| at which the iterations "
                   u"stop.")),
    ("NPREC", ("solver", u"Controle van MUMPS op een (bijna) singuliere "
               u"matrix: aantal cijfers dat verloren mag gaan; -1 = controle "
               u"uit.",
               u"MUMPS check for a (nearly) singular matrix: number of digits "
               u"that may be lost; -1 = check off.")),
    ("RESI_GLOB_RELA", ("solver", u"Convergentiecriterium: grootste "
                        u"restkracht gedeeld door de grootste term van de "
                        u"belasting inclusief de reacties (standaard 1e-6).",
                        u"Convergence criterion: largest residual force "
                        u"divided by the largest term of the load including "
                        u"the reactions (default 1e-6).")),
    ("RESI_GLOB_MAXI", ("solver", u"Convergentiecriterium: grootste "
                        u"restkracht in N (absoluut); voor een beweging "
                        u"zonder weerstand.",
                        u"Convergence criterion: largest residual force in "
                        u"N (absolute); for a motion without resistance.")),
    ("RELA", ("solver", u"Convergentiecriterium RESI_GLOB_RELA (relatief); "
              u"standaard.",
              u"Convergence criterion RESI_GLOB_RELA (relative); "
              u"default.")),
    ("RELA_OF_MAXI", ("solver", u"RESI_GLOB_RELA of RESI_GLOB_MAXI "
                      u"(VERIF='AU_MOINS_UN'): een van beide volstaat.",
                      u"RESI_GLOB_RELA or RESI_GLOB_MAXI "
                      u"(VERIF='AU_MOINS_UN'): either one is enough.")),
    ("MAXI", ("solver", u"Convergentiecriterium RESI_GLOB_MAXI (absoluut, in "
              u"N); voor een beweging zonder weerstand.",
              u"Convergence criterion RESI_GLOB_MAXI (absolute, in N); for "
              u"a motion without resistance.")),
    ("STANDARD", ("solver", u"Contact (ALGO_CONT) met Lagrange-"
                  u"multiplicatoren: geen penetratie, geen stijfheid nodig. "
                  u"Standaard.",
                  u"Contact (ALGO_CONT) with Lagrange multipliers: no "
                  u"penetration, no stiffness needed. Default.")),
    ("PENALISATION", ("solver", u"Contact (ALGO_CONT) als veer met een "
                      u"stijfheid per oppervlak (Mecway's normal stiffness): "
                      u"kleine penetratie, zoals Mecway.",
                      u"Contact (ALGO_CONT) as a spring with a stiffness per "
                      u"area (Mecway's normal stiffness): small penetration, "
                      u"like Mecway.")),
    ("ITER_GLOB_MAXI", ("solver", u"Maximum aantal Newton-iteraties per "
                        u"stap; daarna wordt de stap opgedeeld.",
                        u"Maximum number of Newton iterations per step; then "
                        u"the step is subdivided.")),
    ("REAC_ITER", ("solver", u"Hoe vaak de stijfheidsmatrix binnen een stap "
                   u"opnieuw wordt berekend (1 = elke iteratie).",
                   u"How often the stiffness matrix is recomputed within a "
                   u"step (1 = every iteration).")),
    ("ENERGIE", ("solver", u"Energiebalans per stap (in het "
                 u"convergentiescherm); niet met contact.",
                 u"Energy balance per step (in the convergence window); not "
                 u"with contact.")),
    ("MASS_GENE", ("solver", u"Normering van de modes: "
                   u"gegeneraliseerde massa 1 (phi^T M phi = 1), zoals "
                   u"Mecway's trillingsvormen.",
                   u"Mode normalisation: generalised mass 1 (phi^T M phi = "
                   u"1), like Mecway's mode shapes.")),
    ("RIGI_GENE", ("solver", u"Normering van de modes: gegeneraliseerde "
                   u"stijfheid 1 (phi^T K phi = 1), zoals Mecway's "
                   u"knikvormen.",
                   u"Mode normalisation: generalised stiffness 1 (phi^T K "
                   u"phi = 1), like Mecway's buckling mode shapes.")),
    ("TRAN_ROTA", ("solver", u"Normering van de modes: grootste verplaatsing "
                   u"of rotatie = 1 (Code-Aster-standaard).",
                   u"Mode normalisation: largest displacement or rotation = "
                   u"1 (Code-Aster default).")),
    ("TRAN", ("solver", u"Normering van de modes: grootste verplaatsing = 1.",
              u"Mode normalisation: largest displacement = 1.")),
    ("EUCL", ("solver", u"Normering van de modes: euclidische norm van alle "
              u"vrijheidsgraden = 1.",
              u"Mode normalisation: Euclidean norm of all degrees of "
              u"freedom = 1.")),
    ("VERI_MODE", ("solver", u"Controle van de berekende modes: fout per mode "
                   u"(SEUIL) en Sturm-test (geen modes gemist). Een fout wordt "
                   u"een alarm (WARNING in de log).",
                   u"Check of the computed modes: error per mode (SEUIL) and "
                   u"Sturm test (no modes missed). A failure becomes an alarm "
                   u"(WARNING in the log).")),
    ("ncpus", ("solver", u"Aantal processorkernen (threads) dat Code-Aster "
               u"gebruikt.",
               u"Number of processor cores (threads) Code-Aster uses.")),
    # --- files and results ---
    ("auto (wait)", ("file", u"Wachten op Code-Aster: statusvenster met "
                     u"voortgang en Stoppen; het einde van de run wordt "
                     u"vanzelf herkend en de resultaten worden ingeladen. "
                     u"Standaard.",
                     u"Waiting for Code-Aster: status window with progress "
                     u"and Stop; the end of the run is recognised "
                     u"automatically and the results are loaded. "
                     u"Default.")),
    ("confirm", ("file", u"Wachten op Code-Aster: je klikt op OK in Mecway "
                 u"als het Code-Aster-venster 'DIAGNOSTIC JOB' toont.",
                 u"Waiting for Code-Aster: you click OK in Mecway when the "
                 u"Code-Aster window shows 'DIAGNOSTIC JOB'.")),
    ("liml", ("file", u"Resultaatroute: Code-Aster schrijft Mecway's eigen "
              u"resultaten; de bridge zet ze in de .liml (alle "
              u"tijdstappen of modes). Standaard.",
              u"Result route: Code-Aster writes Mecway's own results; the "
              u"bridge puts them into the .liml (all time steps or modes). "
              u"Default.")),
    ("tabel", ("file", u"Resultaatroute (oud): tabellen in een .resu, alleen "
               u"knoopwaarden van het laatste tijdstip, in de bestaande "
               u"Mecway-solution. Alleen statisch en niet-lineair statisch.",
               u"Result route (old): tables in a .resu, nodal values of the "
               u"last time only, into the existing Mecway solution. Static "
               u"and nonlinear static only.")),
    (".liml", ("file", u"Mecway-modelbestand (XML), ook met de resultaten.",
               u"Mecway model file (XML), also with the results.")),
    (".comm", ("file", u"Code-Aster-invoer (Python): wat er berekend wordt.",
               u"Code-Aster input (Python): what is computed.")),
    (".export", ("file", u"Code-Aster-runbestand: welke bestanden en "
                 u"limieten.",
                 u"Code-Aster run file: which files and limits.")),
    (".mess", ("file", u"Berichten van Code-Aster (fouten, alarmen, "
               u"convergentie); het convergentiescherm leest dit.",
               u"Code-Aster messages (errors, alarms, convergence); the "
               u"convergence window reads it.")),
    (".mail", ("file", u"Het mesh in Code-Aster-formaat.",
               u"The mesh in Code-Aster format.")),
    ("_results.xml", ("file", u"De resultaten van een run in Mecway-formaat; "
                      u"later opnieuw in te laden (knop Resultaten...).",
                      u"The results of a run in Mecway format; can be loaded "
                      u"again later (Results... button).")),
    ("MED / .rmed", ("file", u"Resultaatbestand voor ParaView/Salome "
                     u"(optioneel, kan groot zijn).",
                     u"Result file for ParaView/Salome (optional, can be "
                     u"large).")),
    # Result fields (setting 'fields'; bridge_from_aster.
    # RESULT_FIELD_SPECS): names in the choice list, with Mecway variables.
    ("displacements", ("file", u"Resultaatveld: verplaatsingen (displx/y/z) "
                       u"en bij balken, schalen en discreten rotaties "
                       u"(rotx/y/z). Modaal en knik: de vormen.",
                       u"Result field: displacements (displx/y/z) and for "
                       u"beams, shells and discretes rotations (rotx/y/z). "
                       u"Modal and buckling: the shapes.")),
    ("stresses", ("file", u"Resultaatveld: spanningstensor per knoop "
                  u"(SIGM_NOEU, globale assen; volume-elementen); balken: "
                  u"kleinste en grootste axiale spanning (beamsixxmin/max).",
                  u"Result field: stress tensor per node (SIGM_NOEU, global "
                  u"axes; solid elements); beams: smallest and largest axial "
                  u"stress (beamsixxmin/max).")),
    ("vonmises", ("file", u"Resultaatveld: von Mises per knoop (SIEQ_NOEU, "
                  u"volume-elementen); schalen: boven-, midden- en ondervlak "
                  u"(vonmisesu1/m/b).",
                  u"Result field: von Mises per node (SIEQ_NOEU, solid "
                  u"elements); shells: top, middle and bottom surface "
                  u"(vonmisesu1/m/b).")),
    ("velocities", ("file", u"Resultaatveld: snelheden (velx/y/z; "
                    u"dynamica, respons op modale basis; harmonisch "
                    u"omega x |U|).",
                    u"Result field: velocities (velx/y/z; dynamics, mode "
                    u"superposition; harmonic omega x |U|).")),
    ("accelerations", ("file", u"Resultaatveld: versnellingen (accelx/y/z; "
                       u"harmonisch omega^2 x |U|, responsspectrum de "
                       u"maximale absolute versnelling). Alleen route liml.",
                       u"Result field: accelerations (accelx/y/z; harmonic "
                       u"omega^2 x |U|, response spectrum the maximum "
                       u"absolute acceleration). Route liml only.")),
    ("reactions", ("file", u"Resultaatveld: reactiekrachten en -momenten "
                   u"per knoop (REAC_NODA; reactionforcex.., "
                   u"reactionmomx..).",
                   u"Result field: reaction forces and moments per node "
                   u"(REAC_NODA; reactionforcex.., reactionmomx..).")),
    ("plastic_strain", ("file", u"Resultaatveld: plastische rektensor "
                        u"(EPSP_NOEU; plasticstrainxx..).",
                        u"Result field: plastic strain tensor (EPSP_NOEU; "
                        u"plasticstrainxx..).")),
    ("plastic_strain_eq", ("file", u"Resultaatveld: equivalente plastische "
                           u"rek (interne variabele V1; "
                           u"equivalentplasticstrain, zoals Mecway).",
                           u"Result field: equivalent plastic strain "
                           u"(internal variable V1; equivalentplasticstrain, "
                           u"like Mecway).")),
    ("temperature", ("file", u"Resultaatveld: temperatuur (thermisch; in "
                     u"Kelvin naar Mecway).",
                     u"Result field: temperature (thermal; in Kelvin to "
                     u"Mecway).")),
    ("heat_flux", ("file", u"Resultaatveld: warmtestroom (heatfluxx/y/z; "
                   u"thermisch).",
                   u"Result field: heat flux (heatfluxx/y/z; thermal).")),
    ("metallurgy", ("file", u"Resultaatveld: fasen en hardheid "
                    u"(#ASTER-METALLURGIE; ferrite .. austenite, hardness); "
                    u"met #ASTER-METALLURGIE altijd mee.",
                    u"Result field: phases and hardness (#ASTER-METALLURGIE; "
                    u"ferrite .. austenite, hardness); always included with "
                    u"#ASTER-METALLURGIE.")),
    ("strain", ("file", u"Resultaatveld: totale rek. Volumes: lstrainxx.. "
                u"(niet-lineair met grote verplaatsingen "
                u"greenlagrangestrainxx..), schalen boven/midden/onder "
                u"lstrainxxu/m/b, globale assen; schuif als hoekverdraaiing "
                u"(zoals Mecway). Standaard uit.",
                u"Result field: total strain. Solids: lstrainxx.. "
                u"(nonlinear with large displacements "
                u"greenlagrangestrainxx..), shells top/middle/bottom "
                u"lstrainxxu/m/b, global axes; shear as engineering strain "
                u"(like Mecway). Off by default.")),
    ("beam_forces", ("file", u"Resultaatveld: snedekrachten van balken in "
                     u"de lokale assen (tensileforce, sheary, shearz, "
                     u"torsion, bendingmomv, bendingmomw; EFGE_ELNO), "
                     u"Mecway's namen en tekens.",
                     u"Result field: beam section forces in the local axes "
                     u"(tensileforce, sheary, shearz, torsion, bendingmomv, "
                     u"bendingmomw; EFGE_ELNO), Mecway's names and signs.")),
    ("shell_stresses", ("file", u"Resultaatveld: spanningstensor van "
                        u"schalen in globale assen op boven-, midden- en "
                        u"ondervlak (stressxxu1/m1/b1 ..). Standaard uit "
                        u"(18 variabelen).",
                        u"Result field: shell stress tensor in global axes "
                        u"on the top, middle and bottom surface "
                        u"(stressxxu1/m1/b1 ..). Off by default (18 "
                        u"variables).")),
    ("shell_forces", ("file", u"Resultaatveld: krachten en momenten per "
                      u"lengte van schalen in Mecway's U,V-assen "
                      u"(forceperlengthu/v/uv, momentu/v/uv, shearuw/vw; "
                      u"EFGE_ELNO), per knoop en per element-knoop. "
                      u"Resultaten ca. 2,5 keer zo groot (3500 "
                      u"quad4-schalen: .liml 1,6 -> 3,5 MB), Code-Aster-job "
                      u"+0,3 s; de andere resultaten veranderen niet.",
                      u"Result field: shell forces and moments per length "
                      u"in Mecway's U,V axes (forceperlengthu/v/uv, "
                      u"momentu/v/uv, shearuw/vw; EFGE_ELNO), per node and "
                      u"per element node. Results about 2.5 times larger "
                      u"(3500 quad4 shells: .liml 1.6 -> 3.5 MB), Code-Aster "
                      u"job +0.3 s; the other results do not change.")),
    ("safety_factor", ("file", u"Resultaatveld: factor of safety bij een "
                       u"materiaal met Mecway's von Mises-faalcriterium "
                       u"(tensile strength / von Mises; schalen de kleinste "
                       u"van boven en onder; factorofsafety).",
                       u"Result field: factor of safety for a material with "
                       u"Mecway's von Mises failure criterion (tensile "
                       u"strength / von Mises; shells the smallest of top and "
                       u"bottom; factorofsafety).")),
    ("contact", ("file", u"Resultaatveld: contactdruk (contactpressure, "
                 u"-LAGS_C) en contactstatus (contactstate: 0 open, 1 "
                 u"gesloten, 2 glijdend) op de slave-knopen; niet-lineair "
                 u"en dynamisch.",
                 u"Result field: contact pressure (contactpressure, "
                 u"-LAGS_C) and contact state (contactstate: 0 open, 1 "
                 u"closed, 2 sliding) on the slave nodes; nonlinear and "
                 u"dynamic.")),
    ("run_aster.bat", ("file", u"Het startprogramma van Code-Aster in de "
                       u"installatiemap (bin).",
                       u"Code-Aster's launcher in the installation folder "
                       u"(bin).")),
    # --- other ---
    ("#ASTER", ("other", u"Regels in Mecway's custom model definition met "
                u"eigen Code-Aster-invoer (docs/ASTER_regels_voorbeelden.md).",
                u"Lines in Mecway's custom model definition with your own "
                u"Code-Aster input (docs/en/ASTER_lines_examples.md).")),
    ("#ASTER-BEZWIJKEN", ("other", u"Bezwijkgrens per materiaal, bijv. "
                          u"'** ASTER-BEZWIJKEN Staal = 0.2' "
                          u"(docs/Bezwijken.md).",
                          u"Failure limit per material, e.g. "
                          u"'** ASTER-BEZWIJKEN Steel = 0.2' "
                          u"(docs/en/Failure.md).")),
    ("#ASTER-LASBRON", ("other", u"Bewegende lasbron (Goldak) in een "
                        u"transiente thermische analyse, bijv. "
                        u"'** ASTER-LASBRON Q=2000, eta=0.8, v=0.005, ...' "
                        u"(docs/Lassen.md).",
                        u"Moving weld heat source (Goldak) in a transient "
                        u"thermal analysis, e.g. "
                        u"'** ASTER-LASBRON Q=2000, eta=0.8, v=0.005, ...' "
                        u"(docs/en/Welding.md).")),
    ("Bezwijken", ("other", u"Elementen boven de bezwijkgrens krijgen een "
                   u"zeer lage stijfheid en spanning nul (niet-lineair en "
                   u"dynamisch).",
                   u"Elements above the failure limit get a very low "
                   u"stiffness and zero stress (nonlinear and dynamic).")),
    ("nl", ("other", u"Taal: Nederlands.", u"Language: Dutch.")),
    ("en", ("other", u"Taal: Engels (standaard).",
            u"Language: English (default).")),
    ("LINEAIRE", ("other", u"Breukmechanica (CALC_G DISCRETISATION): "
                  u"Lagrange, een waarde van G en K per knoop van het "
                  u"front; vraagt minstens 5 knopen langs het front (anders "
                  u"oscilleert het, WARNING). Code-Aster-standaard.",
                  u"Fracture mechanics (CALC_G DISCRETISATION): Lagrange, "
                  u"one value of G and K per node of the front; needs at "
                  u"least 5 nodes along the front (otherwise it oscillates, "
                  u"WARNING). Code-Aster default.")),
    ("LEGENDRE", ("other", u"Breukmechanica: G en K als Legendre-polynoom "
                  u"over het hele front (graad fracture_legendre_degree; "
                  u"graad 0 = een constante). Voor een front met weinig "
                  u"knopen.",
                  u"Fracture mechanics: G and K as a Legendre polynomial "
                  u"over the whole front (degree fracture_legendre_degree; "
                  u"degree 0 = a constant). For a front with few nodes.")),
    ("m (imperfection)", ("other", u"Imperfectie: amplitude in meter "
                          u"(standaard).",
                          u"Imperfection: amplitude in metres (default).")),
    ("L (imperfection)", ("other", u"Imperfectie: amplitude als fractie van "
                          u"de grootste afmeting van het model (0.001 = "
                          u"L/1000).",
                          u"Imperfection: amplitude as a fraction of the "
                          u"largest dimension of the model (0.001 = "
                          u"L/1000).")),
    ("lin", ("other", u"Frequenties: gelijke stappen in Hz (standaard).",
             u"Frequencies: equal steps in Hz (default).")),
    ("log", ("other", u"Frequenties: gelijke verhoudingen (zoals "
             u"octaafbanden), voor een groot bereik.",
             u"Frequencies: equal ratios (like octave bands), for a wide "
             u"range.")),
    ("CFL", ("other", u"Kritieke tijdstap van een expliciet schema "
             u"(Courant); de stap moet kleiner zijn.",
             u"Critical time step of an explicit scheme (Courant); the step "
             u"must be smaller.")),
])

# Setting -> explanation (tooltip). Keys as in CONFIG_BRIDGE.
SETTING_HELP = {
    "language": (u"Taal van het scherm, de meldingen, de WARNING/ERROR-"
                 u"regels in de log en de .mess en het convergentiescherm. "
                 u"Standaard en (Engels).",
                 u"Language of the window, the messages, the WARNING/ERROR "
                 u"lines in the log and the .mess and the convergence "
                 u"window. Default en (English)."),
    "exe_aster": (u"Pad naar run_aster.bat in de Code-Aster-installatie "
                  u"(map bin). Omgevingsvariabelen zoals %LOCALAPPDATA% "
                  u"mogen. Standaard %LOCALAPPDATA%\\code_aster\\v2025\\"
                  u"17.4\\bin\\run_aster.bat (plek van het Windows-pakket).",
                  u"Path to run_aster.bat in the Code-Aster installation "
                  u"(bin folder). Environment variables such as "
                  u"%LOCALAPPDATA% are allowed. Default %LOCALAPPDATA%\\"
                  u"code_aster\\v2025\\17.4\\bin\\run_aster.bat (location of "
                  u"the Windows package)."),
    "work_dir": (u"Map waar de bridge per run de bestanden zet "
                 u"(<model>_<tijd>.comm, .mess, resultaten, log). Houd het "
                 u"pad kort: werkmap plus bestandsnaam max. 259 tekens. "
                 u"Standaard (leeg) de map WorkDir naast de map Scripts; "
                 u"wordt aangemaakt.",
                 u"Folder where the bridge puts the files of each run "
                 u"(<model>_<time>.comm, .mess, results, log). Keep the path "
                 u"short: work folder plus file name max. 259 characters. "
                 u"Default (empty) the folder WorkDir next to the Scripts "
                 u"folder; created if needed. Not used with 'Work folder "
                 u"next to the model' (for a saved model)."),
    "work_dir_beside_model": (
        u"Aan: de bestanden van een run gaan naar de submap <model>_aster "
        u"naast het open .liml-bestand (bijv. C:\\Projecten\\Ligger.liml -> "
        u"C:\\Projecten\\Ligger_aster), ook Resultaten... en het "
        u"convergentiescherm. Een model dat nog niet is opgeslagen gebruikt "
        u"de Werkmap. Naast het vinkje staat de map die gebruikt wordt. "
        u"Standaard uit.",
        u"On: the files of a run go to the subfolder <model>_aster next to "
        u"the open .liml file (e.g. C:\\Projects\\Beam.liml -> "
        u"C:\\Projects\\Beam_aster), also Results... and the convergence "
        u"window. A model that has not been saved yet uses the Work folder. "
        u"The folder in use is shown next to the checkbox. Off by default."),
    "ncpus": (u"Aantal processorkernen (threads) voor Code-Aster (1 = geen "
              u"parallellisme; geen MPI). Standaard 1; het effect op de "
              u"rekentijd is niet gemeten.",
              u"Number of processor cores (threads) for Code-Aster (1 = no "
              u"parallelism; no MPI). Default 1; the effect on the run "
              u"time has not been measured."),
    "active_analysis": (u"Welke berekening Code-Aster doet. 'auto' volgt "
                        u"het analysetype van het Mecway-model (standaard). "
                        u"Expliciete dynamica, harmonische respons en "
                        u"vibro-akoestiek harmonisch kies je altijd zelf.",
                        u"Which analysis Code-Aster performs. 'auto' follows "
                        u"the analysis type of the Mecway model (default). "
                        u"Explicit dynamics, harmonic response and "
                        u"vibroacoustics harmonic are always chosen by "
                        u"you."),
    "configuration": (u"Welke configuratie (Mecway: Edit > New "
                      u"configuration) de bridge rekent: lasten die daarin "
                      u"onderdrukt zijn tellen niet mee, en de resultaten "
                      u"komen in de solution van die configuratie (de "
                      u"andere blijven staan). De lijst toont de "
                      u"configuraties van het open model (laatst "
                      u"opgeslagen versie). Mecway's API kan de actieve "
                      u"configuratie niet lezen. Een naam die niet in het "
                      u"model staat: waarschuwing en 'auto'.",
                      u"Which configuration (Mecway: Edit > New "
                      u"configuration) the bridge computes: loads suppressed "
                      u"in it are left out, and the results go into the "
                      u"solution of that configuration (the others stay). "
                      u"The list shows the configurations of the open model "
                      u"(last saved version). Mecway's API cannot read the "
                      u"active configuration. A name that is not in the "
                      u"model: warning and 'auto'."),
    "mecway_solve_first": (u"Eerst met Mecway's eigen solver rekenen als "
                           u"controle; de bridge vergelijkt daarna de "
                           u"resultaten (CSV in de werkmap). Standaard uit: "
                           u"Mecway's solve kan lang duren.",
                           u"Solve with Mecway's own solver first as a check; "
                           u"the bridge then compares the results (CSV in "
                           u"the work folder). Off by default: Mecway's solve can "
                           u"take long."),
    "result_route": (u"Hoe de resultaten in Mecway komen; 'tabel' alleen "
                     u"bij statisch en niet-lineair statisch. Standaard liml "
                     u"(alle tijdstappen of modes, klein bestand).",
                     u"How the results get into Mecway; 'tabel' only for "
                     u"static and nonlinear static. Default liml (all time "
                     u"steps or modes, small file)."),
    "convergence_monitor": (u"Bij elke run een apart venster met de "
                            u"voortgang, convergentie en meldingen van "
                            u"Code-Aster. Standaard aan.",
                            u"A separate window with the progress, "
                            u"convergence and messages of Code-Aster on "
                            u"every run. On by default."),
    "wait_for_aster": (u"Hoe de bridge wacht tot Code-Aster klaar is. 'auto' "
                       u"(standaard): een statusvenster met de voortgang en "
                       u"de knop Stoppen; Mecway is tijdens de run "
                       u"geblokkeerd en de resultaten worden daarna vanzelf "
                       u"ingeladen. 'confirm': je klikt zelf op OK als "
                       u"Code-Aster klaar is (zoals voorheen).",
                       u"How the bridge waits until Code-Aster has "
                       u"finished. 'auto' (default): a status window with "
                       u"the progress and the button Stop; Mecway is locked "
                       u"during the run and the results are loaded "
                       u"automatically afterwards. 'confirm': you click OK "
                       u"yourself when Code-Aster has finished (as "
                       u"before)."),
    "med_export": (u"Ook een MED-bestand (.rmed) schrijven voor ParaView of "
                   u"Salome. Mecway gebruikt het niet. Standaard uit: het "
                   u"bestand kan honderden MB worden. Met een XFEM-scheur ook "
                   u"_xfem.rmed: het mesh dat de scheur volgt, waarin de "
                   u"opening te zien is.",
                   u"Also write a MED file (.rmed) for ParaView or Salome. "
                   u"Mecway does not use it. Off by default: the file can be "
                   u"hundreds of MB. With an XFEM crack also _xfem.rmed: the "
                   u"mesh that follows the crack, in which the opening is "
                   u"visible."),
    "paraview_exe": (
        u"paraview.exe voor de knop ParaView in het convergentiescherm (opent "
        u"de .rmed van de run; zet daarvoor 'MED-bestand voor ParaView' "
        u"aan). Leeg (standaard) = automatisch zoeken: eerst de ParaView van "
        u"Salome-Meca (C:\\Salome_meca\\...\\ParaView\\bin, "
        u"%ProgramFiles%\\SALOME*), die een MED-lezer heeft, daarna "
        u"%ProgramFiles%\\ParaView*. Let op: ParaView 5.10 van paraview.org "
        u"heeft GEEN MED-lezer en kan een .rmed niet openen. De ParaView "
        u"van Salome-Meca start de bridge via run_paraview.bat (zet de "
        u"Salome-omgeving; los start hij niet: Qt5Widgets.dll ontbreekt). "
        u"Omgevingsvariabelen mogen in het pad.",
        u"paraview.exe for the ParaView button in the convergence window "
        u"(opens the .rmed of the run; turn on 'MED file for ParaView' for "
        u"that). Empty (default) = search automatically: first the ParaView "
        u"of Salome-Meca (C:\\Salome_meca\\...\\ParaView\\bin, "
        u"%ProgramFiles%\\SALOME*), which has a MED reader, then "
        u"%ProgramFiles%\\ParaView*. Note: ParaView 5.10 from paraview.org "
        u"has NO MED reader and cannot open a .rmed. The bridge starts "
        u"Salome-Meca's ParaView through run_paraview.bat (sets the Salome "
        u"environment; on its own it does not start: Qt5Widgets.dll "
        u"missing). Environment variables are allowed in the path."),
    "elem_hex8": (u"Hoe hex8-volume-elementen in Code-Aster gerekend "
                  u"worden. Standaard 3D (volledig geintegreerd; met weinig "
                  u"hex8 over de dikte te stijf bij buiging, KNOWN_BUGS 1).",
                  u"How hex8 solid elements are computed in Code-Aster. "
                  u"Default 3D (fully integrated; too stiff in bending with "
                  u"few hex8 through the thickness, KNOWN_BUGS 1)."),
    "cable_n_init_factor": (
        u"Kleine voorspanning voor tension-only-elementen (CABLE): "
        u"N_INIT = factor x E x A (in N) per kabelgroep. Zonder "
        u"voorspanning heeft een rechte kabel geen dwarsstijfheid en is "
        u"de matrix singulier. Standaard 1e-6: rek 1e-6, verandert de "
        u"resultaten niet merkbaar. 0 = geen voorspanning.",
        u"Small pretension for tension-only elements (CABLE): "
        u"N_INIT = factor x E x A (in N) per cable group. Without "
        u"pretension a straight cable has no transverse stiffness and "
        u"the matrix is singular. Default 1e-6: strain 1e-6, does not "
        u"change the results noticeably. 0 = no pretension."),
    "elem_shell": (u"Welk schaalelement voor tri3/quad4-schalen. Standaard "
                   u"DKT (dunne plaat, Kirchhoff).",
                   u"Which shell element for tri3/quad4 shells. Default DKT "
                   u"(thin plate, Kirchhoff)."),
    "elem_beam": (u"Welk balkelement voor line2- en line3-balken (line3 "
                  u"wordt in de middenknoop in twee SEG2-cellen gesplitst). "
                  u"Standaard POU_D_E (Euler-Bernoulli, zoals Mecway). "
                  u"POU_D_T_GD: grote rotaties in niet-lineair statisch "
                  u"(deformation GROT_GDEP); in andere analyses wordt dat "
                  u"POU_D_T (WARNING).",
                  u"Which beam element for line2 and line3 beams (line3 is "
                  u"split at its midside node into two SEG2 cells). Default "
                  u"POU_D_E (Euler-Bernoulli, like Mecway). POU_D_T_GD: "
                  u"large rotations in nonlinear static (deformation "
                  u"GROT_GDEP); in other analyses it becomes POU_D_T "
                  u"(WARNING)."),
    "fields": (u"Welke resultaten naar Mecway gaan (minder velden = kleiner "
               u"bestand). Modaal: stresses/vonmises (ook strain, "
               u"beam_forces, shell_stresses, shell_forces) geven waarden "
               u"per mode, alleen relatief betekenisvol (genormeerde "
               u"vormen). Standaard per analyse de velden die Mecway zelf "
               u"toont (docs/Standaardinstellingen_en_aannames.md par. 3); "
               u"strain en shell_stresses staan uit (grotere .liml). "
               u"shell_forces staat bij statisch en niet-lineair aan: bij "
               u"schalen ca. 2,5 keer zo grote resultaten (3500 "
               u"quad4-schalen: .liml 1,6 -> 3,5 MB, Code-Aster-job "
               u"+0,3 s); vink uit als je ze niet nodig hebt.",
               u"Which results go to Mecway (fewer fields = smaller file). "
               u"Modal: stresses/vonmises (also strain, beam_forces, "
               u"shell_stresses, shell_forces) give values per mode, only "
               u"meaningful relative to each other (normalised shapes). "
               u"Default per analysis: the fields Mecway itself shows "
               u"(docs/en/Default_settings_and_assumptions.md sec. 3); "
               u"strain and shell_stresses are off (larger .liml). "
               u"shell_forces is on for static and nonlinear: with shells "
               u"about 2.5 times larger results (3500 quad4 shells: .liml "
               u"1.6 -> 3.5 MB, Code-Aster job +0.3 s); untick it if you "
               u"do not need them."),
    "time_limit": (u"Maximale rekentijd van Code-Aster in seconden; daarna "
                   u"stopt de run; een afgebroken run levert geen volledige "
                   u"resultaten. Standaard 600 (statisch), 900 (modaal, "
                   u"knik, akoestiek, vibro-akoestiek modes), 7200 "
                   u"(dynamisch), anders 1800.",
                   u"Maximum run time of Code-Aster in seconds; then the run "
                   u"stops; an aborted run gives no complete results. Default "
                   u"600 (static), 900 (modal, buckling, acoustics, "
                   u"vibroacoustic modes), 7200 (dynamic), otherwise "
                   u"1800."),
    "memory_limit": (u"Maximaal geheugen voor Code-Aster in MB; te weinig: de "
                     u"run stopt (.mess, convergentiescherm). Standaard "
                     u"4096 (niet-lineair, dynamisch, thermisch), anders "
                     u"2048.",
                     u"Maximum memory for Code-Aster in MB; too little: the "
                     u"run stops (.mess, convergence window). Default 4096 "
                     u"(nonlinear, dynamic, thermal), otherwise 2048."),
    "solver_nprec": (u"MUMPS-controle op een singuliere matrix: aantal "
                     u"cijfers dat verloren mag gaan (8 = Code-Aster-"
                     u"standaard, standaard in alle analyses; -1 = uit).",
                     u"MUMPS check for a singular matrix: number of digits "
                     u"that may be lost (8 = Code-Aster default, default in "
                     u"all analyses; -1 = off)."),
    "lin_solver": (u"Oplosser voor Ku = F in de statische analyse: MUMPS "
                   u"(direct, standaard) of GCPC (iteratief, met "
                   u"residu-grafiek in het convergentiescherm).",
                   u"Solver for Ku = F in the static analysis: MUMPS "
                   u"(direct, default) or GCPC (iterative, with a residual "
                   u"plot in the convergence window)."),
    "lin_solver_resi": (u"RESI_RELA van de lineaire oplosser (standaard "
                        u"1e-6, als Code-Aster): bij MUMPS de maximale "
                        u"geschatte relatieve fout van de oplossing "
                        u"(groter = Code-Aster stopt met FACTOR_57), bij "
                        u"GCPC het convergentiecriterium. Statisch: de "
                        u"hele berekening; Modaal (voorspanning), Knik en "
                        u"Niet-lineair statisch (imperfectie): de "
                        u"statische stap vooraf. Een slank volumemodel op "
                        u"buiging kan zonder mechanisme 1e-5 tot 1e-4 "
                        u"halen; de foutmelding noemt dan de waarde om "
                        u"hier in te vullen. Een mechanisme geeft een fout "
                        u"van orde 1 of FACTOR_11.",
                        u"RESI_RELA of the linear solver (default 1e-6, "
                        u"as Code-Aster): with MUMPS the maximum estimated "
                        u"relative error of the solution (larger = "
                        u"Code-Aster stops with FACTOR_57), with GCPC the "
                        u"convergence criterion. Static: the whole "
                        u"analysis; Modal (prestress), Buckling and "
                        u"Nonlinear static (imperfection): the static step "
                        u"before it. A slender volume model in bending can "
                        u"reach 1e-5 to 1e-4 without a mechanism; the "
                        u"error message then gives the value to enter "
                        u"here. A mechanism gives an error of order 1 or "
                        u"FACTOR_11."),
    "substeps_per_interval": (u"Aantal rekenstappen per tijdsinterval van "
                              u"de lasttabel, alleen voor een model zonder "
                              u"Mecway's Time step size. Met een stapgrootte "
                              u"rekent de bridge per Mecway-stap (plus de "
                              u"knikken van de lasttabellen) en knipt "
                              u"Code-Aster een stap die niet convergeert. "
                              u"Meer = robuuster, langzamer. Standaard 10.",
                              u"Number of solver steps per time interval of "
                              u"the load table, only for a model without "
                              u"Mecway's Time step size. With a step size the "
                              u"bridge computes per Mecway step (plus the "
                              u"kinks of the load tables) and Code-Aster cuts "
                              u"a step that does not converge. More = more "
                              u"robust, slower. Default 10."),
    "newton_max_iter": (u"Maximum aantal Newton-iteraties per stap "
                        u"(ITER_GLOB_MAXI); daarna wordt de stap opgedeeld. "
                        u"Standaard 20 (Code-Aster 10; contact vraagt vaak "
                        u"meer).",
                        u"Maximum number of Newton iterations per step "
                        u"(ITER_GLOB_MAXI); then the step is subdivided. Default "
                        u"20 (Code-Aster 10; contact often needs more)."),
    "newton_reac_iter": (u"Hoe vaak de stijfheidsmatrix opnieuw wordt "
                         u"berekend (REAC_ITER; 1 = elke iteratie, standaard en "
                         u"Code-Aster-standaard; 0 stopte in de verificatie "
                         u"met DVP_2).",
                         u"How often the stiffness matrix is recomputed "
                         u"(REAC_ITER; 1 = every iteration, default and Code-Aster "
                         u"default; 0 stopped with DVP_2 in the "
                         u"verification)."),
    "convergence_resi_rela": (u"Convergentiecriterium (RESI_GLOB_RELA); "
                              u"kleiner = nauwkeuriger. Standaard 1e-5 (thermisch "
                              u"1e-6); de Code-Aster-standaard 1e-6 stagneert "
                              u"bij ontlasten van plastische volumes "
                              u"(GDEF_LOG), zie docs/"
                              u"Standaardinstellingen_en_aannames.md par. 3.3.",
                              u"Convergence criterion (RESI_GLOB_RELA); "
                              u"smaller = more accurate. Default 1e-5 (thermal 1e-6); "
                              u"the Code-Aster default 1e-6 stagnates when "
                              u"unloading plastic solids (GDEF_LOG), see "
                              u"docs/en/Default_settings_and_assumptions.md "
                              u"sec. 3.3."),
    "convergence_criterion": (
        u"RELA = restkracht gedeeld door de belasting inclusief reacties "
        u"(standaard). "
        u"MAXI = grootste restkracht in N (RESI_GLOB_MAXI): kies dit als het "
        u"model een opgelegde beweging heeft zonder weerstand (externe "
        u"krachten ~0, bijv. een deel dat eerst vrij beweegt tot het contact "
        u"maakt) en de run in de eerste stappen niet convergeert. "
        u"RELA_OF_MAXI = beide met VERIF='AU_MOINS_UN': geconvergeerd als een "
        u"van beide gehaald is (zoals CCX: relatief, met een absolute "
        u"ondergrens bij kleine krachten).",
        u"RELA = residual force divided by the load including reactions "
        u"(default). "
        u"MAXI = largest residual force in N (RESI_GLOB_MAXI): choose this "
        u"when the model has a prescribed motion without resistance "
        u"(external forces ~0, e.g. a part moving freely until it makes "
        u"contact) and the run does not converge in the first steps. "
        u"RELA_OF_MAXI = both with VERIF='AU_MOINS_UN': converged when "
        u"either criterion is met (like CCX: relative, with an absolute "
        u"floor for small forces)."),
    "convergence_resi_maxi": (
        u"Grens voor de grootste restkracht in N bij criterium MAXI; "
        u"klein ten opzichte van de verwachte krachten kiezen. "
        u"Standaard 1e-3 N.",
        u"Limit for the largest residual force in N with criterion MAXI; "
        u"choose it small compared with the expected forces. "
        u"Default 1e-3 N."),
    "contact_algo": (
        u"STANDARD (standaard) = Lagrange-contact van Code-Aster: geen "
        u"penetratie, "
        u"geen stijfheid nodig. PENALISATION = contact als veer met de "
        u"normaalstijfheid uit Mecway (en de tangentiele stijfheid bij "
        u"wrijving), zoals Mecway zelf rekent: kleine penetratie, vaak "
        u"robuuster bij lijncontact of een deel dat het contact kan "
        u"verliezen.",
        u"STANDARD (default) = Code-Aster Lagrange contact: no "
        u"penetration, no "
        u"stiffness needed. PENALISATION = contact as a spring with the "
        u"normal stiffness from Mecway (and the tangential stiffness with "
        u"friction), as Mecway itself computes: small penetration, often "
        u"more robust for line contact or a part that can lose contact."),
    "default_time_end": (u"Eindtijd als het model geen tijdsbelasting of "
                         u"tijdstappen heeft. Standaard 1 s (pseudotijd).",
                         u"End time when the model has no time load or time "
                         u"steps. Default 1 s (pseudo time)."),
    "plastic_strain_definition": (u"Of de rek in Mecway's hardingscurve de "
                                  u"plastische of de totale rek is. Mecway "
                                  u"zelf leest de curve als totale rek. "
                                  u"Standaard auto (afgeleid uit het eerste "
                                  u"punt van de curve).",
                                  u"Whether the strain in Mecway's hardening "
                                  u"curve is the plastic or the total "
                                  u"strain. Mecway itself reads the curve as "
                                  u"total strain. Default auto (derived from "
                                  u"the first point of the curve)."),
    "deformation": (u"Kleine of grote verplaatsingen/vervormingen "
                    u"(COMPORTEMENT DEFORMATION). Thermisch: alleen de "
                    u"mechanische keten (Thermal stress in een T31-model). "
                    u"Standaard GROT_GDEP (zoals Mecway's niet-lineaire "
                    u"analyse; per element vertaald, balken en DKT/DST "
                    u"blijven geometrisch lineair); thermisch PETIT.",
                    u"Small or large displacements/deformations "
                    u"(COMPORTEMENT DEFORMATION). Thermal: only the "
                    u"mechanical chain (Thermal stress in a T31 model). "
                    u"Default GROT_GDEP (like Mecway's nonlinear analysis; "
                    u"translated per element, beams and DKT/DST stay "
                    u"geometrically linear); thermal PETIT."),
    "schema": (u"Tijdintegratieschema van de dynamische analyse. Standaard "
               u"HHT (impliciet; dempt hoge frequenties) en DIFF_CENT "
               u"(expliciet).",
               u"Time integration scheme of the dynamic analysis. Default "
               u"HHT (implicit; damps high frequencies) and DIFF_CENT "
               u"(explicit)."),
    "hht_alpha": (u"Numerieke demping van HHT: 0 = geen, -0.3 = maximaal "
                  u"(periode langer, piek lager). Standaard -0.1 "
                  u"(Code-Aster-standaard).",
                  u"Numerical damping of HHT: 0 = none, -0.3 = maximum "
                  u"(longer period, lower peak). Default -0.1 (Code-Aster "
                  u"default)."),
    "substeps_per_output": (u"Rekenstappen per uitvoertijdstap van Mecway; meer = "
                            u"kleinere rekenstap. Standaard 1 (rekenstap = "
                            u"uitvoerinterval).",
                            u"Solver steps per Mecway output time step; more "
                            u"= smaller solver step. Default 1 (solver step "
                            u"= output interval)."),
    "energy_balance": (u"Energiebalans per stap uitrekenen en tonen; niet "
                       u"met contact. Standaard uit (alleen ter controle).",
                       u"Compute and show the energy balance per step; not "
                       u"with contact. Off by default (for checking only)."),
    "error_estimator": (u"Geschatte discretisatiefout per element en knoop "
                        u"(residu-schatter ERME van CALC_ERREUR, alleen "
                        u"volume-elementen) als veld errorestimate / "
                        u"errorestimaterel in Mecway, en de globale "
                        u"relatieve fout in de log en het statusvak. Grote "
                        u"waarden: daar de mesh verfijnen. Standaard aan "
                        u"(weinig rekentijd); zie docs/Foutschatter.md.",
                        u"Estimated discretisation error per element and "
                        u"node (residual estimator ERME of CALC_ERREUR, "
                        u"solid elements only) as field errorestimate / "
                        u"errorestimaterel in Mecway, and the global "
                        u"relative error in the log and the status box. "
                        u"Large values: refine the mesh there. On by default "
                        u"(little run time); see docs/en/Error_estimator.md."),
    "fracture_r_inf": (u"Breukmechanica (alleen met SCHEUR_-selecties): "
                       u"binnenstraal van het theta-veld van CALC_G rond het "
                       u"front, in m. 0 (standaard, met R_SUP 0) = automatisch: "
                       u"Code-Aster neemt 2 x de elementgrootte aan het "
                       u"front. Groter (bijv. 2 tot 3 elementen) als G of K "
                       u"van de keuze afhangen. Geldt ook voor #ASTER-XFEM "
                       u"(CALC_G_XFEM); zie docs/Breukmechanica.md.",
                       u"Fracture mechanics (only with CRACK_ selections): "
                       u"inner radius of the CALC_G theta field around the "
                       u"front, in m. 0 (default, with R_SUP 0) = automatic: "
                       u"Code-Aster takes 2 x the element size at the front. "
                       u"Larger (e.g. 2 to 3 elements) if G or K depend on "
                       u"the choice. Also applies to #ASTER-XFEM "
                       u"(CALC_G_XFEM); see docs/en/Fracture_mechanics.md."),
    "fracture_r_sup": (u"Breukmechanica: buitenstraal van het theta-veld in "
                       u"m (groter dan R_INF). 0 (standaard) = automatisch (4 x de "
                       u"elementgrootte aan het front). Binnen het model en "
                       u"niet tot over een andere scheur of een belaste rand.",
                       u"Fracture mechanics: outer radius of the theta field "
                       u"in m (larger than R_INF). 0 (default) = automatic (4 x the "
                       u"element size at the front). Inside the model and not "
                       u"reaching another crack or a loaded boundary."),
    "fracture_smoothing": (u"Breukmechanica: hoe CALC_G G en K langs het "
                           u"front gladmaakt. LINEAIRE (standaard): een "
                           u"waarde per knoop; vraagt minstens 5 knopen langs "
                           u"het front. LEGENDRE: een polynoom van de graad "
                           u"hieronder over het hele front (graad 0 = een "
                           u"constante). Niet voor #ASTER-XFEM (sleutel "
                           u"glad=).",
                           u"Fracture mechanics: how CALC_G smooths G and K "
                           u"along the front. LINEAIRE (default): one value "
                           u"per node; needs at least 5 nodes along the front. "
                           u"LEGENDRE: a polynomial of the degree below over "
                           u"the whole front (degree 0 = a constant). Not "
                           u"for #ASTER-XFEM (key glad=)."),
    "fracture_legendre_degree": (u"Breukmechanica: graad van het "
                                 u"Legendre-polynoom (0 .. 7, alleen bij "
                                 u"LEGENDRE); kleiner dan het aantal knopen "
                                 u"langs het front. Ook de standaard voor "
                                 u"#ASTER-XFEM met LEGENDRE. Standaard 5 "
                                 u"(Code-Aster).",
                                 u"Fracture mechanics: degree of the "
                                 u"Legendre polynomial (0 .. 7, LEGENDRE "
                                 u"only); below the number of nodes along "
                                 u"the front. Also the default for "
                                 u"#ASTER-XFEM with LEGENDRE. Default 5 "
                                 u"(Code-Aster)."),
    "adapt_refine": (u"Adaptieve verfijning: na de run de elementen met de "
                     u"grootste geschatte fout in Mecway verfijnen (Refine "
                     u"x2) en opnieuw rekenen, tot het doel of een grens. "
                     u"Elke lus vraagt weer om OK na Code-Aster. Werkt het "
                     u"best met hex20; vlakken met voorwaarden als "
                     u"vlakselectie. Standaard uit; zie docs/Foutschatter.md "
                     u"par. 6.",
                     u"Adaptive refinement: after the run, refine the "
                     u"elements with the largest estimated error in Mecway "
                     u"(Refine x2) and run again, until the target or a "
                     u"limit. Each loop asks for OK after Code-Aster again. "
                     u"Works best with hex20; faces with constraints as "
                     u"face selection. Off by default; see "
                     u"docs/en/Error_estimator.md sec. 6."),
    "adapt_target_error": (u"Doel van de lus: globale relatieve fout (%, "
                           u"energienorm). Voor verplaatsingen 2 tot 5; voor "
                           u"een piekspanning 1 tot 1,5 (plaat met gat: Kt "
                           u"binnen 2% bij 1,1%). Standaard 2.",
                           u"Target of the loop: global relative error (%, "
                           u"energy norm). For displacements 2 to 5; for a "
                           u"peak stress 1 to 1.5 (plate with hole: Kt "
                           u"within 2% at 1.1%). Default 2."),
    "adapt_max_loops": (u"Maximaal aantal verfijningen (elke verfijning is "
                        u"een extra run). Standaard 5.",
                        u"Maximum number of refinements (each refinement is "
                        u"an extra run). Default 5."),
    "adapt_select": (u"Welke elementen verfijnd worden: dorfler = de kleinste "
                     u"groep met de grootste fout die samen de fractie "
                     u"'Keuzewaarde' van de totale fout (in het kwadraat) "
                     u"dragen; fraction = die fractie van de elementen; "
                     u"factor = fout groter dan Keuzewaarde x het gemiddelde. "
                     u"Standaard dorfler.",
                     u"Which elements are refined: dorfler = the smallest "
                     u"group with the largest error that together carry "
                     u"the fraction 'Selection value' of the total (squared) "
                     u"error; fraction = that fraction of the elements; "
                     u"factor = error larger than Selection value x the "
                     u"mean. Default dorfler."),
    "adapt_fraction": (u"Waarde bij de keuze: dorfler 0,5 (standaard; kleiner "
                       u"= minder elementen per lus, meer lussen), fraction "
                       u"bijv. 0,1, factor bijv. 2.",
                       u"Value for the selection: dorfler 0.5 (default; "
                       u"smaller = fewer elements per loop, more loops), "
                       u"fraction e.g. 0.1, factor e.g. 2."),
    "adapt_neighbours": (u"Ook alle elementen verfijnen die een knoop met de "
                         u"gekozen elementen delen. Alleen voor dunne "
                         u"elementen (dikte << breedte), waar Mecway's "
                         u"overgangen anders na een paar lussen platte "
                         u"elementen geven; kost extra elementen. Standaard uit.",
                         u"Also refine all elements that share a node with "
                         u"the chosen elements. Only for thin elements "
                         u"(thickness << width), where Mecway's transitions "
                         u"otherwise give flat elements after a few loops; "
                         u"costs extra elements. Off by default."),
    "adapt_max_elements": (u"Grens: niet verfijnen als het model daarna meer "
                           u"elementen (alle, ook schalen en balken) zou "
                           u"hebben (schatting uit de "
                           u"groei van de vorige lus). Let ook op de "
                           u"geheugenlimiet van de run. Standaard 200000.",
                           u"Limit: do not refine if the model would then "
                           u"have more elements (all, also shells and "
                           u"beams) (estimate from the "
                           u"growth of the previous loop). Also mind the "
                           u"memory limit of the run. Default 200000."),
    "explicit_dt_factor": (u"Tijdstap als fractie van de geschatte "
                           u"kritieke tijdstap (0.5 .. 0.7 aanbevolen, "
                           u"U2.06.13); Code-Aster controleert de echte "
                           u"grens (STOP_CFL). Standaard 0.5; de schatting van de "
                           u"bridge kan 2 x de grens van Code-Aster zijn "
                           u"(DYNAMIQUE_2: verlagen).",
                           u"Time step as a fraction of the estimated "
                           u"critical time step (0.5 .. 0.7 recommended, "
                           u"U2.06.13); Code-Aster checks the real limit "
                           u"(STOP_CFL). Default 0.5; the bridge's estimate can be 2 x "
                           u"Code-Aster's limit (DYNAMIQUE_2: lower it)."),
    "theta": (u"Thermisch tijdschema (0 = expliciet, 0.5 = Crank-Nicolson, "
              u"1 = impliciet Euler; standaard 0.57 zoals Code-Aster).",
              u"Thermal time scheme (0 = explicit, 0.5 = Crank-Nicolson, "
              u"1 = implicit Euler; default 0.57 as in Code-Aster)."),
    "element_failure": (u"Elementen met een plastische rek boven de "
                        u"bezwijkgrens krijgen een zeer lage stijfheid en "
                        u"spanning nul (docs/Bezwijken.md). Standaard aan; werkt "
                        u"alleen waar een bezwijkgrens bestaat.",
                        u"Elements with a plastic strain above the failure "
                        u"limit get a very low stiffness and zero stress "
                        u"(docs/en/Failure.md). On by default; only acts where a "
                        u"failure limit exists."),
    "failure_plastic_strain": (u"Bezwijkgrens voor alle plastische "
                               u"materialen zonder eigen grens "
                               u"(#ASTER-BEZWIJKEN of Eps_p_max); 0 = uit "
                               u"(standaard).",
                               u"Failure limit for all plastic materials "
                               u"without their own limit (#ASTER-BEZWIJKEN or "
                               u"Eps_p_max); 0 = off (default)."),
    "modal_modes": (u"Aantal modes als het Mecway-model geen 'Number of "
                    u"modes' (maxmode) heeft; anders geldt dat van Mecway. "
                    u"Standaard 10 (spectrum 20, knik 4).",
                    u"Number of modes if the Mecway model has no 'Number of "
                    u"modes' (maxmode); otherwise Mecway's value is used. "
                    u"Default 10 (spectrum 20, buckling 4)."),
    "modal_shift_hz": (u"0 (standaard) = de laagste frequenties (zoals Mecway). "
                       u"Groter: "
                       u"de modes het dichtst bij deze frequentie (OPTION "
                       u"CENTRE), bijv. om een frequentiegebied te "
                       u"onderzoeken. Negatief (bijv. -10 x de verwachte "
                       u"eerste frequentie): ook de laagste modes, maar "
                       u"rekenbaar bij een mechanisme (melding ALGELINE3_81; "
                       u"het alarm ALGELINE3_82 is dan normaal).",
                       u"0 (default) = the lowest frequencies (like Mecway). "
                       u"Larger: "
                       u"the modes closest to this frequency (OPTION "
                       u"CENTRE), e.g. to examine a frequency range. "
                       u"Negative (e.g. -10 x the expected first frequency): "
                       u"also the lowest modes, but solvable with a "
                       u"mechanism (message ALGELINE3_81; the alarm "
                       u"ALGELINE3_82 is then normal)."),
    "modal_norm": (u"Schaal van de trillings-/knikvormen. Alleen de vorm "
                   u"heeft betekenis; standaard MASS_GENE (modaal) en RIGI_GENE "
                   u"(knik) "
                   u"geven dezelfde getallen als Mecway. MASS_GENE bij knik "
                   u"wordt RIGI_GENE (geen massamatrix).",
                   u"Scale of the mode shapes. Only the shape is meaningful; "
                   u"default MASS_GENE (modal) and RIGI_GENE (buckling) give the "
                   u"same "
                   u"numbers as Mecway. MASS_GENE for buckling becomes "
                   u"RIGI_GENE (no mass matrix)."),
    "modal_tolerance": (u"VERI_MODE SEUIL: toegestane relatieve fout per "
                        u"mode (standaard 1e-6). Wordt hij overschreden, "
                        u"dan meldt de log een WARNING.",
                        u"VERI_MODE SEUIL: allowed relative error per mode "
                        u"(default 1e-6). If exceeded, the log shows a "
                        u"WARNING."),
    "vibro_freq_min": (u"Vibro-akoestiek: de modes boven deze frequentie "
                       u"(standaard 0,1 Hz). Moet > 0 zijn: de formulering "
                       u"U_P_PHI geeft valse modes bij 0 Hz. Hoger zetten "
                       u"om de modes vanaf een frequentie te zoeken (bijv. "
                       u"rond een bromtoon).",
                       u"Vibroacoustics: the modes above this frequency "
                       u"(default 0.1 Hz). Must be > 0: the U_P_PHI "
                       u"formulation gives spurious modes at 0 Hz. Raise it "
                       u"to look for the modes from a frequency on (e.g. "
                       u"around a hum)."),
    "modal_prestress": (u"Aan (standaard, zoals Mecway): met belastingen of "
                        u"thermische rek rekent de bridge eerst statisch en "
                        u"dan de modes met de verstijfde matrix (trek "
                        u"verhoogt, druk verlaagt de frequenties). Uit: de "
                        u"belastingen worden genegeerd (WARNING).",
                        u"On (default, like Mecway): with loads or thermal "
                        u"strain the bridge first solves statically and then "
                        u"the modes with the stiffened matrix (tension "
                        u"raises, compression lowers the frequencies). Off: "
                        u"the loads are ignored (WARNING)."),
    "modal_complex": (u"Uit (standaard, zoals Mecway): reele modes, de "
                      u"demping telt niet mee. Aan: met Rayleigh-demping "
                      u"en/of dempers (Damper) complexe modes: per mode de "
                      u"gedempte frequentie f_d en de dempingsverhouding "
                      u"zeta (log en statusvak); de vorm (reeel deel) naar "
                      u"Mecway, met decay rate. Geen spanningen per mode.",
                      u"Off (default, like Mecway): real modes, damping is "
                      u"not included. On: with Rayleigh damping and/or "
                      u"dampers (Damper) complex modes: per mode the damped "
                      u"frequency f_d and the damping ratio zeta (log and "
                      u"status box); the shape (real part) to Mecway, with "
                      u"decay rate. No stresses per mode."),
    "cyclic_base_modes": (u"Alleen bij cyclische symmetrie (Mecway Cyclic "
                          u"symmetry): het aantal trillingsvormen van de "
                          u"sector met vaste snijvlakken in de basis van "
                          u"MODE_ITER_CYCL. 0 (standaard) = max(20, 4 x het "
                          u"aantal modes per nodal diameter). Meer = "
                          u"nauwkeuriger voor de hogere modes; reken ter "
                          u"controle met het dubbele: de frequenties moeten "
                          u"gelijk blijven.",
                          u"Only with cyclic symmetry (Mecway Cyclic "
                          u"symmetry): the number of vibration modes of the "
                          u"sector with fixed cut faces in the basis of "
                          u"MODE_ITER_CYCL. 0 (default) = max(20, 4 x the "
                          u"number of modes per nodal diameter). More = more "
                          u"accurate for the higher modes; as a check, run "
                          u"with twice as many: the frequencies should stay "
                          u"the same."),
    "cyclic_full_wheel": (u"Alleen bij cyclische symmetrie. Aan (standaard, "
                          u"zoals Mecway): elke trillingsvorm staat in Mecway "
                          u"op het hele wiel, alle N sectoren met hun fase "
                          u"(Code-Aster DEFI_SQUELETTE + REST_SOUS_STRUC); "
                          u"de knopen en elementen van de extra sectoren "
                          u"hebben dezelfde nummers als in Mecway's eigen "
                          u"oplossing. Uit: alleen de sector (kleiner "
                          u"bestand bij grote modellen).",
                          u"Only with cyclic symmetry. On (default, like "
                          u"Mecway): each mode shape is shown in Mecway on "
                          u"the whole wheel, all N sectors with their phase "
                          u"(Code-Aster DEFI_SQUELETTE + REST_SOUS_STRUC); "
                          u"the nodes and elements of the extra sectors have "
                          u"the same numbers as in Mecway's own solution. "
                          u"Off: only the sector (smaller file for large "
                          u"models)."),
    "crit_stab": (u"Na elke stap het stabiliteitscriterium van Code-Aster "
                  u"(CRIT_STAB) in de log en het statusvak, met een melding "
                  u"als knik bereikt is. Kleine verplaatsingen (PETIT, "
                  u"balken): kritische lastfactor van de huidige last (< 1 = "
                  u"knik). Grote verplaatsingen (standaard bij volumes en "
                  u"COQUE_3D): een eigenwaarde die naar 0 gaat (0 = knik), "
                  u"geen lastfactor. Kost per stap een eigenwaardeberekening. "
                  u"Breng de last met een tijdstabel aan (0 -> P). Standaard "
                  u"uit.",
                  u"After each step Code-Aster's stability criterion "
                  u"(CRIT_STAB) in the log and the status box, with a "
                  u"message when buckling is reached. Small displacements "
                  u"(PETIT, beams): critical load factor of the current load "
                  u"(< 1 = buckling). Large displacements (default for solids "
                  u"and COQUE_3D): an eigenvalue that goes to 0 (0 = "
                  u"buckling), not a load factor. Costs an eigenvalue "
                  u"solution per step. Apply the load with a time table "
                  u"(0 -> P). Off by default."),
    "imperfection_amplitude": (u"Knikvorm als imperfectie: eerst een "
                               u"lineaire knikberekening onder de lasten op "
                               u"de eindtijd, dan het mesh vervormen met "
                               u"deze knikvorm (grootste verplaatsing = "
                               u"amplitude) en daarop niet-lineair rekenen. "
                               u"0 = geen imperfectie (standaard). Vaak L/1000 tot "
                               u"L/300 (of de norm). Negatief keert de vorm "
                               u"om. Werkt alleen waar de elementen grote "
                               u"verplaatsingen rekenen (volumes, COQUE_3D).",
                               u"Buckling mode as imperfection: first a "
                               u"linear buckling analysis under the loads at "
                               u"the end time, then deform the mesh with "
                               u"this mode (largest displacement = "
                               u"amplitude) and solve nonlinearly on it. 0 = "
                               u"no imperfection (default). Often L/1000 to L/300 (or "
                               u"the code). Negative reverses the shape. "
                               u"Only effective where the elements use large "
                               u"displacements (solids, COQUE_3D)."),
    "imperfection_mode": (u"Nummer van de knikvorm (1 = kleinste "
                          u"kniklastfactor). Standaard 1.",
                          u"Number of the buckling mode (1 = smallest "
                          u"buckling factor). Default 1."),
    "imperfection_unit": (u"m: amplitude in meter. L: amplitude als fractie "
                          u"van de grootste afmeting van het model (bijv. "
                          u"0.001 = L/1000). Standaard m.",
                          u"m: amplitude in metres. L: amplitude as a "
                          u"fraction of the largest dimension of the model "
                          u"(e.g. 0.001 = L/1000). Default m."),
    "steps_per_period": (u"Respons op modale basis: rekenstappen (NEWMARK) "
                         u"per periode van de hoogste mode in de basis; "
                         u"standaard 50 (periodefout van die mode 0,13%, "
                         u"van lagere modes minder). Mecway rekent de "
                         u"modale vergelijkingen exact; lager alleen als de "
                         u"run te lang duurt.",
                         u"Mode superposition: solver steps (NEWMARK) per "
                         u"period of the highest mode in the basis; default "
                         u"50 (period error of that mode 0.13%, less for "
                         u"lower modes). Mecway solves the modal equations "
                         u"exactly; lower it only if the run takes too "
                         u"long."),
    "modal_damping": (u"Respons op modale basis en harmonisch (GENE): "
                      u"extra modale dempingsverhouding (fractie van "
                      u"kritisch, bijv. 0.02) voor alle modes, bovenop "
                      u"Mecway's Rayleigh-demping. Standaard 0 (alleen "
                      u"Mecway).",
                      u"Mode superposition and harmonic (GENE): extra modal "
                      u"damping ratio "
                      u"(fraction of critical, e.g. 0.02) for all modes, on "
                      u"top of Mecway's Rayleigh damping. Default 0 (Mecway "
                      u"only)."),
    "static_correction": (u"Respons op modale basis: statische correctie "
                          u"voor de weggelaten modes (MACRO_ELAS_MULT, "
                          u"CORR_STAT). Uit (standaard): zoals Mecway, alleen "
                          u"de gerekende modes. Aan: de quasi-statische "
                          u"bijdrage van de hogere modes telt mee (bijv. "
                          u"voor spanningen bij weinig modes). Harmonische "
                          u"respons (GENE): standaard aan; de statische "
                          u"respons op elke last wordt aan de modale basis "
                          u"toegevoegd (zoals DYNA_LINE ENRI_STAT).",
                          u"Mode superposition: static correction for the "
                          u"truncated modes (MACRO_ELAS_MULT, CORR_STAT). Off "
                          u"(default): like Mecway, only the computed modes. "
                          u"On: the quasi-static contribution of the higher "
                          u"modes is included (e.g. for stresses with few "
                          u"modes). Harmonic response (GENE): on by default; "
                          u"the static response to every load is added to "
                          u"the modal basis (like DYNA_LINE ENRI_STAT)."),
    "spectrum_abscissa": (u"Responsspectrum: wat de kolom 'time' van de "
                          u"gravity-tabel is: periode [s] (standaard) of "
                          u"frequentie [Hz].",
                          u"Response spectrum: what the 'time' column of the "
                          u"gravity table is: period [s] (default) or "
                          u"frequency [Hz]."),
    "spectrum_damping": (u"Responsspectrum: dempingsverhouding van elke "
                         u"mode (fractie van kritisch), standaard 0.05; het "
                         u"spectrum moet bij deze demping horen. Telt op "
                         u"bij Mecway's Rayleigh-demping (zet 0 als het "
                         u"model Rayleigh heeft). Bepaalt de CQC-correlatie "
                         u"en, bij een DEFI_NAPPE, de spectrumwaarde.",
                         u"Response spectrum: damping ratio of every mode "
                         u"(fraction of critical), default 0.05; the "
                         u"spectrum must belong to this damping. Adds to "
                         u"Mecway's Rayleigh damping (set 0 if the model has "
                         u"Rayleigh). Sets the CQC correlation and, with a "
                         u"DEFI_NAPPE, the spectrum value."),
    "modal_combination": (u"Responsspectrum: combinatie over de modes. CQC "
                          u"(standaard) is goed bij dicht bij elkaar "
                          u"liggende frequenties; SRSS alleen bij goed "
                          u"gescheiden frequenties.",
                          u"Response spectrum: combination over the modes. "
                          u"CQC (default) is correct for close frequencies; "
                          u"SRSS only for well separated frequencies."),
    "direction_combination": (u"Responsspectrum: combinatie van de "
                              u"richtingen X/Y/Z (alleen met meer dan een "
                              u"spectrumrichting). Standaard SRSS; de "
                              u"Code-Aster-standaard is NEWMARK (100-40-40).",
                              u"Response spectrum: combination of the "
                              u"directions X/Y/Z (only with more than one "
                              u"spectrum direction). Default SRSS; the "
                              u"Code-Aster default is NEWMARK (100-40-40)."),
    "missing_mass": (u"Responsspectrum: de massa die de gerekende modes niet "
                     u"dragen (hoge modes) quasi-statisch meenemen met het "
                     u"spectrum op de hoogste gerekende frequentie "
                     u"(pseudo-modes, MODE_CORR). Aan (standaard): reacties "
                     u"en spanningen compleet, ook met weinig modes. Uit: "
                     u"alleen de modes (vraagt ~90% effectieve massa).",
                     u"Response spectrum: include the mass the computed "
                     u"modes do not carry (high modes) quasi-statically with "
                     u"the spectrum at the highest computed frequency "
                     u"(pseudo-modes, MODE_CORR). On (default): reactions "
                     u"and stresses complete, also with few modes. Off: "
                     u"modes only (needs ~90% effective mass)."),
    "harm_freq_start": (u"Harmonisch (akoestiek, constructie): eerste "
                        u"frequentie van het bereik [Hz] (niet bij een "
                        u"frequentielijst). Standaard 1 Hz (harmonisch), 50 Hz "
                        u"(akoestiek), 20 Hz (vibro-akoestiek).",
                        u"Harmonic (acoustics, structure): first frequency "
                        u"of the range [Hz] (not with a frequency list). Default 1 "
                        u"Hz (harmonic), 50 Hz (acoustics), 20 Hz "
                        u"(vibroacoustics)."),
    "harm_freq_end": (u"Harmonisch: laatste frequentie [Hz]. Akoestiek: het "
                      u"mesh moet bij deze frequentie genoeg elementen per "
                      u"golflengte c/f hebben (lineair >= 10, kwadratisch "
                      u">= 5; anders een WARNING). Constructie (GENE): de "
                      u"hoogste gerekende mode hoort ruim boven deze "
                      u"frequentie te liggen (anders een WARNING). Standaard "
                      u"100 Hz (harmonisch), 1000 Hz (akoestiek), 500 Hz "
                      u"(vibro-akoestiek).",
                      u"Harmonic: last frequency [Hz]. Acoustics: the mesh "
                      u"needs enough elements per wavelength c/f at this "
                      u"frequency (linear >= 10, quadratic >= 5; otherwise "
                      u"a WARNING). Structure (GENE): the highest computed "
                      u"mode should be well above this frequency (otherwise "
                      u"a WARNING). Default 100 Hz (harmonic), 1000 Hz "
                      u"(acoustics), 500 Hz (vibroacoustics)."),
    "harm_freq_count": (u"Aantal frequenties van start tot eind (1 = alleen "
                        u"de start). Kies de stap kleiner dan de breedte van "
                        u"een resonantiepiek als je pieken zoekt. Standaard 100 "
                        u"(harmonisch), 20 (akoestiek), 50 "
                        u"(vibro-akoestiek).",
                        u"Number of frequencies from start to end (1 = only "
                        u"the start). Choose the step smaller than the width "
                        u"of a resonance peak when looking for peaks. Default 100 "
                        u"(harmonic), 20 (acoustics), 50 (vibroacoustics)."),
    "harm_freq_spacing": (u"lin: gelijke stappen in Hz; log: gelijke "
                          u"verhoudingen (zoals octaafbanden), handig over "
                          u"een groot bereik. Standaard lin.",
                          u"lin: equal steps in Hz; log: equal ratios (like "
                          u"octave bands), useful over a wide range. Default lin."),
    "harm_freq_list": (u"Eigen frequenties in Hz, gescheiden door komma's "
                       u"(punt als decimaalteken), bijv. '100, 250, 500'. 0 "
                       u"(standaard) = het bereik start/eind/aantal gebruiken.",
                       u"Own frequencies in Hz, separated by commas (point "
                       u"as decimal separator), e.g. '100, 250, 500'. 0 = "
                       u"use the range start/end/count (default)."),
    "harm_basis": (u"Harmonische respons: GENE (standaard) rekent op de "
                   u"modes (snel, modale demping, alleen de gerekende "
                   u"modes); PHYS rekent direct op het hele model (een "
                   u"oplossing per frequentie, Rayleigh en dempers, geen "
                   u"modal_damping): voor controle of een model met "
                   u"dempers.",
                   u"Harmonic response: GENE (default) computes on the "
                   u"modes (fast, modal damping, only the computed modes); "
                   u"PHYS computes directly on the whole model (one "
                   u"solution per frequency, Rayleigh and dampers, no "
                   u"modal_damping): for checking or a model with "
                   u"dampers."),
    "harm_refine_points": (u"Harmonische respons: extra frequenties per mode "
                           u"in het bereik, over de halfwaardebreedte 2 xi f "
                           u"rond de piek (DEFI_LIST_FREQ LARGEUR_3DB), "
                           u"zodat een resonantiepiek niet tussen twee "
                           u"punten valt. Standaard 5; 0 = alleen het "
                           u"bereik. Niet bij een frequentielijst of zonder "
                           u"demping.",
                           u"Harmonic response: extra frequencies per mode "
                           u"in the range, over the half-power bandwidth "
                           u"2 xi f around the peak (DEFI_LIST_FREQ "
                           u"LARGEUR_3DB), so that a resonance peak does not "
                           u"fall between two points. Default 5; 0 = the "
                           u"range only. Not with a frequency list or "
                           u"without damping."),
    "source_velocity": (u"Normaalsnelheid [m/s] van de vlakken met de naam "
                        u"BRON_... (de fluid in, fase 0). Een vlakke golf "
                        u"geeft p = rho c v (lucht: 408 Pa per m/s). Per "
                        u"selectie anders: #ASTER-BRON. Standaard 0.001 m/s (in "
                        u"lucht 0,41 Pa); alles is lineair in v.",
                        u"Normal velocity [m/s] of the faces named "
                        u"SOURCE_... (into the fluid, phase 0). A plane "
                        u"wave gives p = rho c v (air: 408 Pa per m/s). "
                        u"Different per selection: #ASTER-BRON. Default 0.001 m/s "
                        u"(0.41 Pa in air); everything is linear in v."),
    "incident_pressure": (u"Vibro-akoestiek harmonisch: amplitude [Pa] van "
                          u"de vlakke golf die op de vlakken INVALLEND_... "
                          u"het fluidum in loopt (fase 0). Het vlak laat "
                          u"teruggekaatste golven door (ONDE_FLUI). Per "
                          u"selectie anders: #ASTER-BRON met een druk "
                          u"(bijv. 2 Pa, 90). Standaard 1 Pa.",
                          u"Vibroacoustics harmonic: amplitude [Pa] of the "
                          u"plane wave that enters the fluid through the "
                          u"faces INCIDENT_... (phase 0). The face lets "
                          u"reflected waves pass (ONDE_FLUI). Different per "
                          u"selection: #ASTER-BRON with a pressure (e.g. 2 "
                          u"Pa, 90). Default 1 Pa."),
    "failure_stiffness_factor": (u"Stijfheid van een bezweken element als "
                                 u"fractie van E (standaard 1e-6; 1e-9 maakte de "
                                 u"matrix singulier).",
                                 u"Stiffness of a failed element as a "
                                 u"fraction of E (default 1e-6; 1e-9 made the "
                                 u"matrix singular)."),
}


# (setting, option) -> term in GLOSSARY, for options with a general
# name that mean something different per setting.
_OPTION_TERMS = {
    ("plastic_strain_definition", "auto"): "auto (curve)",
    ("wait_for_aster", "auto"): "auto (wait)",
    ("configuration", "auto"): "auto (configuration)",
    ("imperfection_unit", "m"): "m (imperfection)",
    ("imperfection_unit", "L"): "L (imperfection)",
}


def setting_tooltip(key, options, tr):
    """
    Tooltip text for a setting: the explanation from SETTING_HELP and, for
    a choice list, per option the explanation from GLOSSARY. tr(nl, en)
    chooses the language. Empty text if nothing is known.
    """
    lines = []
    if key in SETTING_HELP:
        lines.extend(textwrap.wrap(tr(*SETTING_HELP[key]), _TIP_WIDTH))
    opts = []
    for opt in options or []:
        opt = u"{0}".format(opt)
        # An option that means something different per setting (e.g.
        # 'auto' for strain definition and analysis choice) has its own term.
        entry = GLOSSARY.get(_OPTION_TERMS.get((key, opt), opt))
        if entry:
            # list with indentation under the option name
            opts.extend(textwrap.wrap(
                u"{0}: {1}".format(opt, tr(entry[1], entry[2])),
                _TIP_WIDTH, initial_indent=u"\u2022 ",
                subsequent_indent=u"   "))
    if opts:
        if lines:
            lines.append(u"")
        lines.append(tr(u"Opties:", u"Options:"))
        lines.extend(opts)
    return u"\n".join(lines)


def glossary_items(tr):
    """[(category title, [(term, explanation)])] in the order of
    CATEGORIES, in the language of tr."""
    out = []
    for cat, title in CATEGORIES:
        items = [(term, tr(nl, en)) for term, (c, nl, en)
                 in GLOSSARY.items() if c == cat]
        if items:
            out.append((tr(*title), items))
    return out
