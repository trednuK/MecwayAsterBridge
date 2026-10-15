# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_results_export.py
#
# Verantwoordelijkheid: schrijft de resultaten van een Code-Aster-run direct
# in Mecway's eigen resultaatformaat (het <results>-element binnen
# <solution> van een .liml). Draait BINNEN de Code-Aster-job (CPython 3.11
# met numpy 1.26, meegeleverd met Code-Aster 17.4), NIET in IronPython.
#
# ROUTE ("binair", vervangt de POST_RELEVE_T-tabellen voor grote modellen):
#   1. De .comm roept na CALC_CHAMP export_results() aan:
#          import sys
#          sys.path.insert(0, r"<repo>\Scripts")
#          import aster_results_export
#          aster_results_export.export_results(
#              res, r"<werkmap>\<model>_<run_id>_results.xml",
#              r"<model>.liml",
#              fields=["displacements", "stresses", "vonmises", "reactions"],
#              extra_results={"res_sup": res_sup, "res_moy": res_moy,
#                             "res_inf": res_inf})
#      Dat schrijft een fragment <results precision="single">...</results>
#      met alle gearchiveerde tijdstappen (res.getIndexes()).
#   2. IronPython (bridge_results_liml.splice_results) zet het fragment in de
#      <solution> van de .liml zelf (vorige versie .bak); Mecway opent die
#      opnieuw met mw.open(). Het bestand blijft staan (knop Resultaten...).
#      Als terugval leest bridge_results_liml.read_step() een tijdstap voor
#      de bestaande solution.set_variable()-route.
#
# MECWAY-FORMAAT (afgeleid uit door Mecway 33 zelf opgeslagen .liml-
# bestanden: een OpenRadioss-model met 61 tijdstappen (single) en een
# statisch CCX-model (double); alle onderstaande regels zijn daar met een
# script op nagelopen):
#   <results precision="single">            ("double": float64, valuesdouble)
#     <nodeids name="var">   base64 int32 LE: knoopnummers met een waarde,
#                            oplopend; per variabele (bijv. stressxx alleen
#                            op volumeknopen, rotx alleen op balk/schaal).
#     <elementnodeids name="var">  base64 int32: elementnummers, oplopend.
#     <timestep id="k" time="t s">          (ontbreekt bij een statische
#                                            analyse: variabelen dan direct
#                                            onder <results>)
#       <nodevariable name="var">
#         <maxandmin><component name="elset" max=".." min=".." />...
#           Per elset (volgorde van het model) max/min over de knopen van
#           die elset die in nodeids staan; component name="" (eerst) voor
#           knopen die in geen enkel element zitten. Elsets zonder waarden
#           worden weggelaten.
#         <valuessingle> base64 float32 LE, in de volgorde van nodeids.
#         <nodes /><values />
#       <elementnodevariable name="var">
#         maxandmin per elset over de waarden van zijn elementen;
#         waarden per element (volgorde elementnodeids) voor elke knoop in de
#         volgorde van het nodes-attribuut van <elem> (statische CCX-
#         resultaten: alleen die volgorde geeft per knoop dezelfde waarde in
#         aangrenzende elementen); dan <elements /><values />.
#   Base64 staat in regels van 64 tekens (CRLF), met een CRLF voor de
#   sluittag. Getallen in max/min: 15 significante cijfers, zoals Mecway.
#
# MODES (CALC_MODES; nagelopen in door Mecway 33 headless opgeloste
# voorbeelden VibratingCantileverBeam/-Solid/-FreePlate (V30) en
# BucklingBeam/-Plate (B30)): in plaats van <timestep> een blok per mode,
#     <mode id="1" frequency="7.07368492123229 Hz">   (V30, id vanaf 1)
#     <mode id="1" bucklingfactor="41124.6991224029">  (B30, zonder eenheid)
# met dezelfde <nodevariable>-blokken, precision="double". Mecway schrijft
# bij V30 alleen displx/y/z (+ rotx/y/z bij balken/schalen), zonder
# displmag; bij B30 met displmag. Mecway's API leest ze met
# solution.modes(), solution.frequency(m) / buckling_factor(m) en
# node_value(var, nid, mode=m) (nagelopen met een headless Mecway-script).
# Bij reele en complexe MODE_MECA staat de effectieve massa per mode als
# <globalvariable> direct na <mode> (zoals Mecway, zie _MW_DIRS).
#
# BESTANDSGROOTTES (gemeten; details in bridge_results_liml.py): een
# fragment kost ~5,6 bytes per waarde, de .resu-tabellen ~53 bytes. Hex8-
# blok 18.225 knopen x 51 stappen: fragment 78 MB in 1,6 s, .resu 644 MB
# (POST_RELEVE_T + IMPR_TABLE ~80 s), study.rmed 217 MB.
#
# CYCLISCHE SYMMETRIE, HET HELE WIEL (S10i): export_results(cyclic=...) met
# een resultaat op het skelet (aster_cyclic.collect) schrijft knoopvelden
# voor de N x n knopen van Mecway's eigen cyclische oplossing (knoop i van
# sector j = i + j x n, aster_cyclic.wheel_model); de maxandmin per elset
# gaan over alle sectoren. De knopen en elementen zelf zet
# bridge_results_liml.splice_results in de modelkopie van <solution>.
#
# Knoopvolgorde: bridge_mesh.write_mesh schrijft N1..NN in volgorde van het
# knoopnummer en Code-Aster nummert de knopen in leesvolgorde; rij i van een
# veld is dus Mecway-knoop i+1. export_results controleert dat met de
# coordinaten (mesh.getCoordinates() tegen de .liml). Elementen: Code-Aster
# kent na LIRE_MAILLAGE geen namen meer via de Python-API (getCellName
# bestaat niet in v17.4, sdj.NOMMAI.get() geeft None; nagelopen), dus een
# cel wordt via zijn knopenverzameling aan het Mecway-element gekoppeld en
# de knoop van elk ELNO-punt volgt uit mesh.getConnectivity(). Getest: het
# knoopgemiddelde van de zo geordende SIGM_ELNO is gelijk aan SIGM_NOEU
# (hex8, hex20); met omgekeerde volgorde niet.
#
# ELEMENTKNOOPSPANNINGEN vereisen SIGM_ELNO (en SIEQ_ELNO) in res. Let op
# bij volume + schalen: vraag SIGM_ELNO EEN keer aan over beide groepen
# (CALC_CHAMP GROUP_MA=(volume, schalen), CONTRAINTE=('SIGM_ELNO',)) voor
# de aanroep met SIGM_NOEU. Alleen op het volume aanvragen laat de latere
# CALC_CHAMP op de schalen het bestaande veld niet aanvullen en dan faalt
# POST_CHAMP EXTR_COQUE (CALCULEL2_15); getest op het gemengde model ME.
#
# Gebruik geen f-strings: zelfde stijl als de rest van de bridge.

import base64
import os
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict

import numpy as np


# ==========================================
# TAAL VAN DE MELDINGEN
#
# De jobscripts kennen CONFIG_BRIDGE niet. bridge_to_aster._write_comm zet
# in study.comm (voor DEBUT) os.environ[LANGUAGE_ENV] op
# CONFIG_BRIDGE["language"]; tr() leest die bij elke aanroep. Zonder de
# variabele (een oude .comm, een test) geldt "en", de standaard van de
# bridge. Ook gebruikt door aster_cyclic, aster_acoustic_*, aster_harmonic_
# export, aster_spectrum en aster_fatigue.
# ==========================================
LANGUAGE_ENV = "BRIDGE_LANGUAGE"


def tr(nl, en):
    """Tekst in de taal van de run: nl als BRIDGE_LANGUAGE "nl" is, anders
    en (zelfde placeholders; WAARSCHUWING/FOUT in nl, WARNING/ERROR in en)."""
    return nl if os.environ.get(LANGUAGE_ENV, "en") == "nl" else en


# ==========================================
# VELDENTABEL
#
# Spiegel van RESULT_FIELD_SPECS / STRUCT_FIELD_SPECS in
# bridge_from_aster.py: (groep, resultaat, Code-Aster-veld, component,
# Mecway-naam, soort).
#   groep     : sleutel uit RESULT_FIELD_SPECS (= CONFIG_BRIDGE
#               analyses[...]["fields"]); schaal-/balkvelden onder hun
#               ouder-veld zoals in STRUCT_FIELD_SPECS.
#   resultaat : "res" of een sleutel uit extra_results (res_sup, ...).
#   soort     : KNOOP      knoopveld (..._NOEU, DEPL, VITE, REAC_NODA)
#               ELNO_MIN / ELNO_MAX  ELNO-veld, per knoop min/max over de
#                          aansluitende elementen (als beam_sixx)
#               ELEMKNOOP  ELNO-veld als Mecway-elementnodevariable
#                          (alleen volume-elementen). Alleen als het veld
#                          in res staat: CALC_CHAMP CONTRAINTE=('SIGM_ELNO',)
#                          / CRITERES=('SIEQ_ELNO',) moet het berekenen.
#               ELEMKNOOP_LIJN  idem voor line2-elementen (balken: EFGE_ELNO)
# Afgeleide velden (schaaltensor, -rek en -krachten, factor of safety,
# contactstatus) staan niet in deze tabel: _plan_derived.
# Code-Aster-volgorde van de spanningscomponenten is SIXX SIYY SIZZ SIXY
# SIXZ SIYZ (nagelopen met getComponents()); de koppeling gaat op naam.
# ==========================================
KNOOP = "knoop"
ELNO_MIN = "elno_min"
ELNO_MAX = "elno_max"
ELEMKNOOP = "elementknoop"
ELEMKNOOP_LIJN = "elementknoop_lijn"

_STRESS_CMPS = (("SIXX", "xx"), ("SIYY", "yy"), ("SIZZ", "zz"),
                ("SIXY", "xy"), ("SIYZ", "yz"), ("SIXZ", "zx"))
_XYZ = (("DX", "x"), ("DY", "y"), ("DZ", "z"))
_RXYZ = (("DRX", "x"), ("DRY", "y"), ("DRZ", "z"))
_EPS_CMPS = (("EPXX", "xx"), ("EPYY", "yy"), ("EPZZ", "zz"),
             ("EPXY", "xy"), ("EPYZ", "yz"), ("EPXZ", "zx"))

FIELD_TABLE = (
    [("displacements", "res", "DEPL", c, "displ" + s, KNOOP)
     for c, s in _XYZ] +
    [("displacements", "res", "DEPL", c, "rot" + s, KNOOP)
     for c, s in _RXYZ] +
    [("velocities", "res", "VITE", c, "vel" + s, KNOOP) for c, s in _XYZ] +
    # Hoeksnelheid van balk- en schaalknopen: Mecway's D30 schrijft
    # angularvelx/y/z (headless gezien, Mecway 33; DampedVibratingStrip ook
    # angularvelmag).
    [("velocities", "res", "VITE", c, "angularvel" + s, KNOOP)
     for c, s in _RXYZ] +
    # Versnelling (ACCE): Mecway kent geen versnellingsveld (geen naam in
    # mecway.exe); eigen namen accelx/y/z van de bridge. Responsspectrum
    # (bridge_spectrum.py): de maximale absolute versnelling.
    [("accelerations", "res", "ACCE", c, "accel" + s, KNOOP)
     for c, s in _XYZ] +
    [("stresses", "res", "SIGM_NOEU", c, "stress" + s, KNOOP)
     for c, s in _STRESS_CMPS] +
    [("vonmises", "res", "SIEQ_NOEU", "VMIS", "vonmises", KNOOP),
     ("vonmises", "res_sup", "SIEQ_NOEU", "VMIS", "vonmisesu1", KNOOP),
     ("vonmises", "res_moy", "SIEQ_NOEU", "VMIS", "vonmisesm", KNOOP),
     ("vonmises", "res_inf", "SIEQ_NOEU", "VMIS", "vonmisesb", KNOOP),
     ("stresses", "res", "SIPM_ELNO", "SIXXMIN", "beamsixxmin", ELNO_MIN),
     ("stresses", "res", "SIPM_ELNO", "SIXXMAX", "beamsixxmax", ELNO_MAX)] +
    [("reactions", "res", "REAC_NODA", c, "reactionforce" + s, KNOOP)
     for c, s in _XYZ] +
    [("reactions", "res", "REAC_NODA", c, "reactionmom" + s, KNOOP)
     for c, s in _RXYZ] +
    [("plastic_strain", "res", "EPSP_NOEU", c, "plasticstrain" + s, KNOOP)
     for c, s in _EPS_CMPS] +
    [("plastic_strain_eq", "res", "VARI_NOEU", "V1",
      "equivalentplasticstrain", KNOOP)] +
    [("stresses", "res", "SIGM_ELNO", c, "stress" + s, ELEMKNOOP)
     for c, s in _STRESS_CMPS] +
    [("vonmises", "res", "SIEQ_ELNO", "VMIS", "vonmises", ELEMKNOOP)] +
    # Thermisch (bridge_thermal.py): TEMP in graden Celsius (de bridge
    # rekent in Code-Aster in Celsius, zie VALUE_OFFSETS) en FLUX_NOEU =
    # -lambda grad T (componenten FLUX, FLUY, FLUZ; PLAN-elementen hebben
    # geen FLUZ). Mecway-namen heatfluxx/y/z/mag nagelopen in Mecway 33
    # (OscillatingHeatFlow: Mecway toont ze onder "heat flux").
    [("temperature", "res", "TEMP", "TEMP", "temperature", KNOOP),
     # Keten thermisch -> mechanisch (bridge_thermomech.py): res is het
     # mechanische resultaat, de temperatuur staat in res_ther.
     ("temperature", "res_ther", "TEMP", "TEMP", "temperature", KNOOP)] +
    [("heat_flux", "res_flux", "FLUX_NOEU", c, "heatflux" + s, KNOOP)
     for c, s in (("FLUX", "x"), ("FLUY", "y"), ("FLUZ", "z"))] +
    # Metallurgie (bridge_metallurgy.py, CALC_META): META_NOEU V1..V5 =
    # fasefracties ferriet, perliet, bainiet, martensiet, austeniet
    # (Behaviours/acier.py; gezien in een run), DURT_NOEU HV = hardheid.
    # In het thermische resultaat res, in de keten in res_ther. Eigen namen
    # van de bridge (Mecway kent geen fasen).
    [("metallurgy", r, "META_NOEU", "V%d" % (i + 1), name, KNOOP)
     for r in ("res", "res_ther")
     for i, name in enumerate(("ferrite", "pearlite", "bainite",
                               "martensite", "austenite"))] +
    [("metallurgy", r, "DURT_NOEU", "HV", "hardness", KNOOP)
     for r in ("res", "res_ther")] +
    # Foutschatter (bridge_to_aster._error_estimator_block, resultaat
    # res_err): ERREST = absolute schatting eta_e, NUEST = lokaal relatief
    # (%). ERME_NOEU = knoopgemiddelde; ERME_ELNO is per element constant,
    # dus als elementnodevariable de echte elementwaarde (alleen volume-
    # elementen). Eigen namen van de bridge (Mecway kent geen foutveld).
    [("error_estimate", "res_err", "ERME_NOEU", "ERREST", "errorestimate",
      KNOOP),
     ("error_estimate", "res_err", "ERME_NOEU", "NUEST", "errorestimaterel",
      KNOOP),
     ("error_estimate", "res_err", "ERME_ELNO", "ERREST", "errorestimate",
      ELEMKNOOP),
     ("error_estimate", "res_err", "ERME_ELNO", "NUEST", "errorestimaterel",
      ELEMKNOOP)] +
    # Akoestische holtemodes (bridge_acoustic.py, MODE_ACOU): veld PRES,
    # component PRES (gezien in een run). Mecway's naam "pressure" (headless
    # A30-oplossing). Geen entry in RESULT_FIELD_SPECS: er is niets te
    # kiezen (bridge_acoustic vraagt altijd ["pressure"]).
    [("pressure", "res", "PRES", "PRES", "pressure", KNOOP)] +
    # Vibro-akoestiek (bridge_vibroacoustic.py, 3D_FLUIDE U_P_PHI): de druk
    # is component PRES van DEPL (alleen op de knopen van het fluidum).
    [("pressure", "res", "DEPL", "PRES", "pressure", KNOOP)] +
    # Totale rek van volume-elementen (bridge_to_aster._strain_blocks).
    # Mecway-namen (headless gezien, Mecway 34): lineair (S30, D30, V30)
    # lstrainxx..lstrainzx, niet-lineair (L30, D31, CCX) greenlagrange-
    # strainxx..; schuifcomponenten zijn de technische hoekverdraaiing
    # gamma = 2 eps (gemeten: enkelvoudige afschuiving, lstrainzx =
    # tau/G), Code-Aster's EPXY/EPXZ/EPYZ zijn tensorcomponenten
    # (VALUE_SCALES). EPSI = kleine rekken, EPSG = Green-Lagrange
    # (catalogus calc_champ.py, DEFORMATION).
    [("strain", "res", f, c, n + s, k)
     for f, n, k in (("EPSI_NOEU", "lstrain", KNOOP),
                     ("EPSI_ELNO", "lstrain", ELEMKNOOP),
                     ("EPSG_NOEU", "greenlagrangestrain", KNOOP),
                     ("EPSG_ELNO", "greenlagrangestrain", ELEMKNOOP))
     for c, s in _EPS_CMPS] +
    # Snedekrachten van balken (EFGE_ELNO/EFGE_NOEU, POU_D_E/POU_D_T,
    # lokale assen: x langs de balk, y = Mecway's V, z = W; zie
    # bridge_to_aster._build_cara_elem_block). Mecway-namen en tekens
    # headless nagelopen (Mecway 34, ingeklemde balk met kracht en
    # moment op de tip, ook schuin): tensileforce = N, sheary = VY,
    # shearz = VZ, torsion = MT, bendingmomv = MFY, bendingmomw = MFZ.
    [("beam_forces", "res", f, c, name, k)
     for f, k in (("EFGE_NOEU", KNOOP), ("EFGE_ELNO", ELEMKNOOP_LIJN))
     for c, name in (("N", "tensileforce"), ("VY", "sheary"),
                     ("VZ", "shearz"), ("MT", "torsion"),
                     ("MFY", "bendingmomv"), ("MFZ", "bendingmomw"))] +
    # Contactdruk (DEFI_CONTACT CONTINUE): de Lagrange-multiplicator LAGS_C
    # van DEPL op de slave-knopen is de contactdruk, negatief bij druk
    # (testcase forma04b: "Pression de contact"; gemeten in de patchtest
    # NL-03: LAGS_C = -p). Mecway: contactpressure, positief bij druk
    # (CCX-oplossing headless gezien). Contactstatus: _plan_derived.
    [("contact", "res", "DEPL", "LAGS_C", "contactpressure", KNOOP)]
)

# Groepen die alleen meegaan als ze gekozen zijn: hun velden staan soms
# altijd in het resultaat (LAGS_C in DEPL, SIGM_ELNO van schalen in res_sup),
# en zonder "fields" (statisch, niet-lineair) schrijft export_results alles
# wat er is. bridge_to_aster._results_route geeft de gekozen groepen mee
# (opt_in).
OPT_IN_GROUPS = frozenset(["strain", "beam_forces", "shell_stresses",
                           "shell_forces", "safety_factor", "contact"])

# Vaste factor per Mecway-variabele (waarde = Code-Aster x factor), na
# VALUE_OFFSETS niet nodig (geen overlap): contactdruk positief bij druk,
# schuifrek als technische hoekverdraaiing (zie FIELD_TABLE).
VALUE_SCALES = dict(
    [("contactpressure", -1.0)] +
    [(p + s, 2.0) for p in ("lstrain", "greenlagrangestrain")
     for s in ("xy", "yz", "zx")])

# Ondergrens per Mecway-variabele (na VALUE_SCALES): contactdruk is nooit
# negatief. Met PENALISATION is LAGS_C op open slave-knopen positief
# (gezien in NL-03b: tot +3e4 Pa naast gesloten knopen), dus -LAGS_C < 0;
# Mecway (CCX) toont daar 0.
VALUE_MIN = {"contactpressure": 0.0}

# Contactstatus zonder CONT_NOEU: gesloten boven deze fractie van de
# grootste contactdruk (_contact_state_var).
CONTACT_CLOSED = 0.01

# Factor of safety bij von Mises = 0 (onbelast): een grote eindige waarde
# (Mecway toont standaard tot 15, manual v34 par. 8.7).
FOS_MAX = 1.0e6

# Vaste verschuiving per Mecway-variabele (waarde = Code-Aster + offset).
# Code-Aster's RAYONNEMENT rekent met T + 273,15 (U4.44.02: temperaturen in
# graden Celsius), dus de thermische berekening is in Celsius en Mecway
# krijgt Kelvin.
VALUE_OFFSETS = {"temperature": 273.15}

# Grootte van een vector; Mecway zet de grootte voor de componenten.
MAGNITUDES = OrderedDict([
    ("displmag", ("displx", "disply", "displz")),
    ("velmag", ("velx", "vely", "velz")),
    ("accelmag", ("accelx", "accely", "accelz")),
    ("angularvelmag", ("angularvelx", "angularvely", "angularvelz")),
    ("reactionforcemag",
     ("reactionforcex", "reactionforcey", "reactionforcez")),
    ("reactionmommag", ("reactionmomx", "reactionmomy", "reactionmomz")),
    ("heatfluxmag", ("heatfluxx", "heatfluxy", "heatfluxz")),
])

# Componenten die in een grootte mogen ontbreken (dan 0): FLUZ bestaat niet
# op PLAN-elementen (schalen in een vlak Z = constant, bridge_thermal.py).
OPTIONAL_PARTS = frozenset(["heatfluxz"])

SOLID_SHAPES = frozenset(["hex8", "hex20", "tet4", "tet10", "pyr5", "pyr13",
                          "wedge6", "wedge15"])
SHELL_SHAPES = frozenset(["tri3", "quad4", "tri6", "quad8"])
LINE_SHAPES = frozenset(["line2"])

_NL = b"\r\n"            # Mecway schrijft CRLF
_B64_LINE = 64           # base64-regellengte in Mecway's .liml


# ==========================================
# MODEL UIT DE .LIML
# ==========================================
def read_liml_model(liml_path):
    """
    Lees knopen, elsets en elementen van het model (top-level, niet de
    kopie in <solution>; het lezen stopt bij <solution>).

    Returns
    -------
    dict met
      "coords"   : np.ndarray (N, 3), rij i = knoop i+1
      "elsets"   : OrderedDict {elsetnaam: [eid, ...]} in modelvolgorde
      "elements" : dict {eid: (vorm, [nid, ...])}
      "uaxes"    : dict {eid: (ux, uy, uz)}: Mecway's U-richting per
                   element (attributen orientationux/uy/uz, Element
                   properties), alleen waar opgegeven
    """
    nodes = {}
    elsets = OrderedDict()
    elements = {}
    uaxes = {}
    depth = 0
    with open(liml_path, "rb") as f:
        for event, el in ET.iterparse(f, events=("start", "end")):
            if event == "start":
                depth += 1
                if depth == 2 and el.tag == "solution":
                    break
                continue
            depth -= 1
            if depth != 1:
                continue
            if el.tag == "node":
                nodes[int(el.get("nid"))] = (float(el.get("x")),
                                             float(el.get("y")),
                                             float(el.get("z")))
            elif el.tag == "elset":
                eids = elsets.setdefault(el.get("name", ""), [])
                for e in el.findall("elem"):
                    eid = int(e.get("eid"))
                    elements[eid] = (e.get("shape"),
                                     [int(n) for n in e.get("nodes").split()])
                    eids.append(eid)
                    keys = ("orientationux", "orientationuy",
                            "orientationuz")
                    if any(e.get(k) is not None for k in keys):
                        uaxes[eid] = tuple(float(e.get(k, "0"))
                                           for k in keys)
            el.clear()
    n = max(nodes) if nodes else 0
    if sorted(nodes) != list(range(1, n + 1)):
        raise ValueError(tr("Knoopnummers in {0} zijn niet 1..N "
                            "aaneengesloten.",
                            "Node numbers in {0} are not contiguous "
                            "1..N.").format(liml_path))
    coords = np.array([nodes[i] for i in range(1, n + 1)], dtype=float)
    return {"coords": coords, "elsets": elsets, "elements": elements,
            "uaxes": uaxes}


def _check_node_order(mesh, coords):
    """
    Controleer dat rij i van het Code-Aster-mesh knoop i+1 van de .liml is
    (zelfde coordinaten). Geeft een foutmelding (str) of None.
    """
    xyz = np.asarray(mesh.getCoordinates().getValues(), dtype=float)
    xyz = xyz.reshape(-1, 3)
    if xyz.shape[0] < coords.shape[0]:
        return tr("Mesh heeft {0} knopen, de .liml {1}.",
                  "Mesh has {0} nodes, the .liml {1}.").format(
            xyz.shape[0], coords.shape[0])
    size = max(1.0, float(np.abs(coords).max()))
    diff = float(np.abs(xyz[:coords.shape[0]] - coords).max())
    if diff > 1.0e-9 * size:
        return tr("Knoopvolgorde van het mesh wijkt af van de .liml (max. "
                  "coordinaatverschil {0}).",
                  "Node order of the mesh differs from the .liml (max. "
                  "coordinate difference {0}).").format(diff)
    return None


# ==========================================
# VELDEN PER TIJDSTAP (cache: elk veld een keer omzetten)
# ==========================================
class _Fields(object):
    """Zet per tijdstap elk gevraagd veld een keer om naar numpy."""

    def __init__(self, results, n_nodes, lump=None, rows=None, pairs=None):
        self.results = results
        self.n = n_nodes
        self.lump = lump      # _reaction_lumping(): REAC_NODA extra knopen
        # _offset_pairs(): (Mecway-knoop, knoop van het verschoven element,
        # arm) van een element offset, of None
        self.pairs = pairs
        # rows: rij van het mesh per Mecway-knoop (hele wiel bij cyclische
        # symmetrie, aster_cyclic.node_rows); None = rij i is knoop i+1.
        self.rows = rows
        self.index = None
        self.data = {}
        self.layouts = {}     # (resultaat, veld) -> _cell_layout()
        self.scales = {}      # {index: factor} voor DEPL (knikvormen)
        # {extra knoop: Mecway-knoop} op dezelfde plaats (_coincident_extra)
        self.coincident = {}

    def set_index(self, index):
        self.index = index
        self.data = {}

    def get(self, rkey, field, on_cells):
        """(componenten, waarden, masker, simple field) of None als het veld
        in deze tijdstap ontbreekt. Knoopvelden: alleen de eerste n rijen
        (= Mecway-knopen 1..n; extra mesh-knopen vallen af)."""
        key = (rkey, field)
        if key not in self.data:
            self.data[key] = None
            try:
                fld = self.results[rkey].getField(field, self.index)
                if on_cells:
                    sf = fld.toSimpleFieldOnCells()
                    vals, mask = sf.getValues()
                else:
                    sf = fld.toSimpleFieldOnNodes()
                    vals, mask = sf.getValues()
                    if field == "REAC_NODA" and self.lump is not None:
                        vals, mask = _lump_nodes(vals, mask, self.lump)
                    if self.pairs is not None:
                        vals, mask = _offset_values(
                            field, list(sf.getComponents()), vals, mask,
                            self.pairs)
                    if self.rows is not None:
                        vals, mask = vals[self.rows], mask[self.rows]
                    else:
                        vals, mask = vals[:self.n], mask[:self.n]
                    if (field in ("DEPL", "PRES") and
                            self.index in self.scales):
                        vals = vals * self.scales[self.index]
                    if np.iscomplexobj(vals):
                        # Complexe modes (MODE_MECA_C): het reele deel na
                        # de fasedraaiing van _complex_modes (scales).
                        vals = vals.real
                self.data[key] = (list(sf.getComponents()), vals, mask, sf)
            except Exception:
                pass
        return self.data[key]


# ==========================================
# REACTIES VAN EXTRA KNOPEN (LINE_QUAD, QUAD9/TRIA7)
# ==========================================
def _reaction_lumping(mesh, conn, n, offset_nodes=None):
    """
    Verdeling van de knoopreacties van mesh-knopen die Mecway niet kent
    (index >= n: middenknopen van CREA_MAILLAGE LINE_QUAD, middenknoop van
    QUAD9/TRIA7 voor COQUE_3D) over Mecway-knopen, zodat de som van de
    reacties gelijk blijft (anders vielen ze weg: HexCantilever met
    LINE_QUAD gaf som Fz 752,6 N bij 100 N last).
      - middenknoop QUAD9/TRIA7 (laatste knoop van de cel; hoekknopen
        eerst, Code-Aster-volgorde): 1/4 resp. 1/3 naar elke hoekknoop;
      - middenknoop van een rand: 1/2 naar elk van de twee eindknopen. De
        rand volgt uit de geometrie (midden van twee Mecway-knopen van
        dezelfde cel), zoals _bridge_lq_nodegroups in bridge_to_aster.
    Een kracht in het midden van een rand of van een parallellogram heeft
    zo ook hetzelfde moment om elk punt. Alleen voor REAC_NODA (een
    verplaatsing middelen zou iets anders zijn).
    offset_nodes: knopen van verschoven elementen (bridge_offset, >= n);
    die tellen als hoekknoop en gaan daarna via _offset_values naar hun
    Mecway-knoop.
    Returns (src, dst, gewicht) als numpy-arrays, of None zonder extra
    knopen.
    """
    xyz = np.asarray(mesh.getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    if xyz.shape[0] <= n:
        return None
    known = set() if offset_nodes is None else set(int(i)
                                                   for i in offset_nodes)
    src, dst, wgt = [], [], []
    done = set(known)
    for cn in conn:
        if len(cn) in (7, 9) and cn[-1] >= n and cn[-1] not in done:
            corners = list(cn[:4] if len(cn) == 9 else cn[:3])
            done.add(cn[-1])
            for c in corners:
                src.append(cn[-1])
                dst.append(c)
                wgt.append(1.0 / len(corners))
    # Extra knoop op de plaats van een Mecway-knoop (flexible joint,
    # bridge_mesh._flexible_joints): de hele reactie naar die knoop
    for m, c in sorted(_coincident_extra(xyz, n).items()):
        if m not in done:
            done.add(m)
            src.append(m)
            dst.append(c)
            wgt.append(1.0)
    rest = set(range(n, xyz.shape[0])) - done
    if rest:
        scale = 1.0e9 / max(1.0e-30, float(np.abs(xyz).max()))

        def key(p):
            return tuple(int(round(c * scale)) for c in p)
        mids = {}
        for cn in conn:
            corners = [c for c in cn if c < n or c in known]
            for i in range(len(corners)):
                for j in range(i + 1, len(corners)):
                    a, b = corners[i], corners[j]
                    mids.setdefault(key(0.5 * (xyz[a] + xyz[b])), (a, b))
        for m in sorted(rest):
            ab = mids.get(key(xyz[m]))
            if ab is None:
                continue
            done.add(m)
            for c in ab:
                src.append(m)
                dst.append(c)
                wgt.append(0.5)
    missing = xyz.shape[0] - n - len(done)
    if missing:
        print(tr("aster_results_export: WAARSCHUWING: {0} extra knopen "
                 "zonder Mecway-hoekknopen; hun reacties vallen weg.",
                 "aster_results_export: WARNING: {0} extra nodes without "
                 "Mecway corner nodes; their reactions are dropped.").format(
            missing))
    if not src:
        return None
    return (np.array(src, dtype=int), np.array(dst, dtype=int),
            np.array(wgt, dtype=float))


def _coincident_extra(xyz, n):
    """
    {index extra knoop: index Mecway-knoop} voor mesh-knopen na de
    Mecway-knopen (index >= n) die op dezelfde plaats liggen als een
    Mecway-knoop: de eigen knoop van een balkuiteinde met een flexible
    joint (bridge_mesh._flexible_joints, met LIAISON_DDL aan die knoop
    gekoppeld). Liggen er meer Mecway-knopen op die plaats, dan de laagste.
    """
    if xyz.shape[0] <= n:
        return {}
    scale = 1.0e9 / max(1.0e-30, float(np.abs(xyz).max()))

    def key(p):
        return tuple(int(round(c * scale)) for c in p)
    extra = dict((key(xyz[m]), m) for m in range(n, xyz.shape[0]))
    out = {}
    for c in range(n):
        m = extra.get(key(xyz[c]))
        if m is not None and m not in out:
            out[m] = c
    # meer extra knopen op dezelfde plaats (joints aan beide kanten)
    for m in range(n, xyz.shape[0]):
        c = out.get(extra.get(key(xyz[m])))
        if m not in out and c is not None:
            out[m] = c
    return out


def _lump_nodes(vals, mask, lump):
    """Tel de waarden van de extra knopen naar rato op bij de doelknopen
    (_reaction_lumping); componenten zonder waarde tellen als 0."""
    src, dst, wgt = lump
    out = np.where(mask, vals, 0.0)
    np.add.at(out, dst, out[src] * wgt[:, None])
    new_mask = mask.copy()
    np.logical_or.at(new_mask, dst, mask[src])
    return out, new_mask


# ==========================================
# ELEMENT OFFSET (bridge_offset): VERSCHOVEN KNOPEN -> MECWAY-KNOPEN
# ==========================================
# Knoopgroepen met dit voorvoegsel bevatten precies een Mecway-knoop en de
# knoop van het verschoven element (bridge_offset.LINK_PREFIX).
OFFSET_GROUP_PREFIX = "BROFL"
# Velden die op de Mecway-knoop zelf al de juiste waarde hebben (de knoop
# beweegt met de starre arm mee).
_KINEMATIC_FIELDS = ("DEPL", "VITE", "ACCE")


def _offset_pairs(mesh, n):
    """
    (o, f, arm) als numpy-arrays (0-based knoopindices, arm = x_f - x_o)
    uit de knoopgroepen BROFL<k> van bridge_offset, of None zonder offset.
    mesh.getGroupsOfNodes()/getNodes(groep) (testcase sdll157a, 17.4).
    """
    try:
        names = [g for g in mesh.getGroupsOfNodes()
                 if str(g).strip().startswith(OFFSET_GROUP_PREFIX)]
    except Exception:
        return None
    if not names:
        return None
    xyz = np.asarray(mesh.getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    orig, new = [], []
    for g in names:
        ids = sorted(int(i) for i in mesh.getNodes(str(g).strip()))
        if len(ids) != 2 or not (ids[0] < n <= ids[1] < xyz.shape[0]):
            continue
        orig.append(ids[0])
        new.append(ids[1])
    if not orig:
        return None
    orig, new = np.array(orig, dtype=int), np.array(new, dtype=int)
    return orig, new, xyz[new] - xyz[orig]


def _offset_values(field, comps, vals, mask, pairs):
    """
    Waarden van de knopen van verschoven elementen naar de Mecway-knoop:
      REAC_NODA: de reactie van de verschoven knoop f gaat met het moment
          van de arm naar de Mecway-knoop o (F_o += F_f, M_o += M_f +
          arm x F_f). De krachten van de starre arm zelf (LIAISON_DDL) zijn
          onderling in evenwicht en vallen zo weg; over blijft de reactie
          van een oplegging op o (Mecway: reacties op de knopen).
      DEPL/VITE/ACCE: ongewijzigd (o heeft zijn eigen waarde).
      Andere velden (spanningen van schalen per knoop): waar o geen waarde
          heeft, het gemiddelde van zijn verschoven knopen (Mecway: de
          elementwaarden horen bij het verschoven element).
    """
    orig, new, arm = pairs
    if field in _KINEMATIC_FIELDS:
        return vals, mask
    vals = np.array(vals, dtype=float, copy=True)
    mask = np.array(mask, copy=True)
    if field == "REAC_NODA":
        idx = dict((c, i) for i, c in enumerate(comps))
        out = np.where(mask, vals, 0.0)
        forces = [idx.get(c) for c in ("DX", "DY", "DZ")]
        moments = [idx.get(c) for c in ("DRX", "DRY", "DRZ")]
        f = np.zeros((len(new), 3))
        for k, i in enumerate(forces):
            if i is not None:
                f[:, k] = out[new, i]
                np.add.at(out[:, i], orig, out[new, i])
                out[new, i] = 0.0
        moment = np.cross(arm, f)
        for k, i in enumerate(moments):
            if i is not None:
                np.add.at(out[:, i], orig, out[new, i] + moment[:, k])
                out[new, i] = 0.0
        for i in [j for j in forces + moments if j is not None]:
            np.logical_or.at(mask[:, i], orig, mask[new, i])
        return out, mask
    total = np.zeros((vals.shape[0], vals.shape[1]))
    count = np.zeros((vals.shape[0], vals.shape[1]))
    have = mask[new]
    np.add.at(total, orig, np.where(have, vals[new], 0.0))
    np.add.at(count, orig, have.astype(float))
    fill = (~mask) & (count > 0)
    vals[fill] = total[fill] / count[fill]
    mask = mask | fill
    return vals, mask


# ==========================================
# CELLEN -> MECWAY-ELEMENTEN
# ==========================================
def _cell_layout(sf, conn, nrows):
    """
    Rijen van SimpleFieldOnCells.getValues(): alleen cellen MET componenten
    hebben rijen, per cel nbpt*nbsp achter elkaar in celvolgorde (opslag
    .CESV, adres per cel/punt/subpunt zoals in cesexi.F90). LET OP:
    getNumberOfPointsOfCell() geeft ook voor cellen zonder waarden het
    aantal punten (nagelopen: SIGM_ELNO alleen op schalen gaf nbpt=8 voor
    HEXA8), en getValuesOnCell() in simplefieldoncells_ext.py (v17.4) telt
    die cellen mee; daarom hier getNumberOfComponentsForSubpointsOfCell().

    Returns (start, nbpt, nbsp) per cel (nbpt = 0 voor cellen zonder
    waarden), of None als de indeling niet klopt met nrows of een cel maar
    een deel van de componenten heeft (dan past de (rijen, ncmp)-vorm van
    getValues() niet; NIET geverifieerd hoe getValues() dat dan geeft).
    """
    ncell = len(conn)
    ncmp = np.array([sf.getNumberOfComponentsForSubpointsOfCell(c)
                     for c in range(ncell)])
    nbpt = np.array([sf.getNumberOfPointsOfCell(c) for c in range(ncell)])
    nbsp = np.array([sf.getNumberOfSubPointsOfCell(c) for c in range(ncell)])
    nbpt = np.where(ncmp > 0, nbpt, 0)
    rows = nbpt * nbsp
    full = len(sf.getComponents())
    if int(rows.sum()) != nrows or np.any((ncmp > 0) & (ncmp != full)):
        return None
    start = np.concatenate([[0], np.cumsum(rows)[:-1]])
    return start, nbpt, nbsp


def _match_cells(conn, elements, nbpt, nbsp, n_nodes):
    """
    {eid: celindex} voor cellen met een ELNO-waarde per knoop (nbpt gelijk
    aan het aantal knopen, een subpunt). Koppeling op de knopenverzameling
    van de Mecway-knopen (index < n_nodes): na CREA_MAILLAGE LINE_QUAD heeft
    een HEXA20-cel 12 extra middenknopen, de 8 hoekknopen zijn die van het
    Mecway-element. Randelementen hebben geen waarden en vallen af.
    """
    by_nodes = {}
    for eid, (_shape, nids) in elements.items():
        by_nodes[tuple(sorted(nids))] = eid
    out = {}
    for c, cn in enumerate(conn):
        if nbpt[c] != len(cn) or nbsp[c] != 1:
            continue
        eid = by_nodes.get(tuple(sorted(n + 1 for n in cn
                                        if n < n_nodes)))
        if eid is not None and eid not in out:
            out[eid] = c
    return out


# ==========================================
# VARIABELEN PLANNEN (op de laatste tijdstap)
# ==========================================
class _Var(object):
    """Een Mecway-variabele: naam, soort, ids en hoe de waarden te halen."""

    def __init__(self, name, element, ids, getter):
        self.name = name
        self.element = element    # True: elementnodevariable
        self.ids = ids            # np.int32: knoop- of elementnummers
        self.getter = getter      # functie(_Fields) -> np.ndarray float64
        self.groups = []          # [(componentnaam, posities)]


def _node_var(rkey, field, cmp_, rows):
    def getter(fields):
        d = fields.get(rkey, field, False)
        if d is None or cmp_ not in d[0]:
            return None
        return d[1][rows, d[0].index(cmp_)]
    return getter


def _elno_node_var(rkey, field, cmp_, pt_node, rows, reduce_min):
    def getter(fields):
        d = fields.get(rkey, field, True)
        if d is None or cmp_ not in d[0]:
            return None
        col = d[1][:, d[0].index(cmp_)]
        ok = (pt_node >= 0) & d[2][:, d[0].index(cmp_)]
        out = np.full(fields.n, np.inf if reduce_min else -np.inf)
        ufunc = np.minimum if reduce_min else np.maximum
        ufunc.at(out, pt_node[ok], col[ok])
        return out[rows]
    return getter


def _elem_var(rkey, field, cmp_, gather):
    def getter(fields):
        d = fields.get(rkey, field, True)
        if d is None or cmp_ not in d[0]:
            return None
        return d[1][gather, d[0].index(cmp_)]
    return getter


def _plan_node(fields, rkey, field, cmp_, name):
    d = fields.get(rkey, field, False)
    if d is None or cmp_ not in d[0]:
        return None
    rows = np.nonzero(d[2][:, d[0].index(cmp_)])[0]
    if not len(rows):
        return None
    getter = _node_var(rkey, field, cmp_, rows)
    if name in VALUE_OFFSETS:
        getter = _offset(getter, VALUE_OFFSETS[name])
    if name in VALUE_SCALES:
        getter = _scaled(getter, VALUE_SCALES[name])
    if name in VALUE_MIN:
        getter = _at_least(getter, VALUE_MIN[name])
    return _Var(name, False, (rows + 1).astype("<i4"), getter)


def _offset(getter, offset):
    def shifted(fields):
        vals = getter(fields)
        return None if vals is None else vals + offset
    return shifted


def _scaled(getter, factor):
    def scaled(fields):
        vals = getter(fields)
        return None if vals is None else vals * factor
    return scaled


def _at_least(getter, lower):
    def clipped(fields):
        vals = getter(fields)
        return None if vals is None else np.maximum(vals, lower)
    return clipped


def _cells_field(fields, rkey, field, cmp_, conn):
    """(veld, componentindex, (start, nbpt, nbsp)) van een celveld, of None.
    De indeling wordt per veld een keer bepaald (laatste tijdstap) en geldt
    voor alle tijdstappen."""
    d = fields.get(rkey, field, True)
    if d is None or cmp_ not in d[0]:
        return None
    key = (rkey, field)
    if key not in fields.layouts:
        fields.layouts[key] = _cell_layout(d[3], conn, d[1].shape[0])
        if fields.layouts[key] is None:
            print(tr("aster_results_export: WAARSCHUWING: indeling van "
                     "{0}:{1} niet herkend; overgeslagen.",
                     "aster_results_export: WARNING: layout of {0}:{1} "
                     "not recognised; skipped.").format(rkey, field))
    if fields.layouts[key] is None:
        return None
    return d, d[0].index(cmp_), fields.layouts[key]


def _plan_elno_node(fields, rkey, field, cmp_, name, kind, conn):
    found = _cells_field(fields, rkey, field, cmp_, conn)
    if found is None:
        return None
    d, icmp, (start, nbpt, nbsp) = found
    pt_node = np.full(d[1].shape[0], -1, dtype=int)
    for c, cn in enumerate(conn):
        if nbpt[c] == len(cn) and nbsp[c] == 1:
            pt_node[start[c]:start[c] + nbpt[c]] = cn
    # balkuiteinde met een flexible joint: zijn waarde telt bij de
    # Mecway-knoop op dezelfde plaats (_coincident_extra)
    for m, c in fields.coincident.items():
        pt_node[pt_node == m] = c
    if fields.pairs is not None:
        # verschoven element (bridge_offset): waarde naar de Mecway-knoop
        alias = np.arange(max(int(pt_node.max()) + 1, fields.n,
                              int(fields.pairs[1].max()) + 1))
        alias[fields.pairs[1]] = fields.pairs[0]
        pt_node = np.where(pt_node >= 0, alias[np.maximum(pt_node, 0)], -1)
    pt_node[pt_node >= fields.n] = -1
    ok = (pt_node >= 0) & d[2][:, icmp]
    rows = np.unique(pt_node[ok])
    if not len(rows):
        return None
    return _Var(name, False, (rows + 1).astype("<i4"),
                _elno_node_var(rkey, field, cmp_, pt_node, rows,
                               kind == ELNO_MIN))


def _plan_elem(fields, rkey, field, cmp_, name, conn, model,
               shapes=SOLID_SHAPES):
    found = _cells_field(fields, rkey, field, cmp_, conn)
    if found is None:
        return None
    d, icmp, (start, nbpt, nbsp) = found
    solids = dict((e, v) for e, v in model["elements"].items()
                  if v[0] in shapes)
    cells = _match_cells(conn, solids, nbpt, nbsp, fields.n)
    eids, gather = [], []
    for eid in sorted(cells):
        c = cells[eid]
        if not d[2][start[c]:start[c] + nbpt[c], icmp].all():
            continue
        cn = list(conn[c])
        # ELNO-punt k hoort bij knoop conn[c][k]; Mecway wil de volgorde van
        # het nodes-attribuut van <elem>.
        gather.extend(start[c] + cn.index(nid - 1)
                      for nid in solids[eid][1])
        eids.append(eid)
    if not eids:
        return None
    getter = _elem_var(rkey, field, cmp_, np.array(gather))
    if name in VALUE_SCALES:
        getter = _scaled(getter, VALUE_SCALES[name])
    return _Var(name, True, np.array(eids, dtype="<i4"), getter)


def _wanted(group, groups_wanted, opt_in):
    """Hoort groep bij de export? Met een lijst groepen (fields) precies
    die; zonder lijst alles behalve de OPT_IN_GROUPS die niet in opt_in
    staan."""
    if groups_wanted is not None:
        return group in groups_wanted
    return group not in OPT_IN_GROUPS or group in opt_in


def _plan_variables(fields, model, conn, groups_wanted, magnitudes=True,
                    opt_in=(), derived=None):
    """Lijst _Var in Mecway-volgorde (grootte voor de componenten; zonder
    grootte als magnitudes False is, zoals Mecway's trillingsvormen).
    derived: argumenten voor _plan_derived (schaalvectoren, sterktes)."""
    node_vars, elem_vars = OrderedDict(), OrderedDict()
    for group, rkey, field, cmp_, name, kind in FIELD_TABLE:
        if not _wanted(group, groups_wanted, opt_in):
            continue
        if rkey not in fields.results:
            continue
        if fields.rows is not None and kind != KNOOP:
            continue    # hele wiel (cyclisch): alleen knoopvelden
        if kind == KNOOP:
            var = _plan_node(fields, rkey, field, cmp_, name)
        elif kind in (ELNO_MIN, ELNO_MAX):
            var = _plan_elno_node(fields, rkey, field, cmp_, name, kind, conn)
        elif kind == ELEMKNOOP_LIJN:
            var = _plan_elem(fields, rkey, field, cmp_, name, conn, model,
                             LINE_SHAPES)
        else:
            var = _plan_elem(fields, rkey, field, cmp_, name, conn, model)
        if var is None:
            continue
        target = elem_vars if var.element else node_vars
        if name in target:
            print(tr("aster_results_export: WAARSCHUWING: '{0}' dubbel in "
                     "FIELD_TABLE, tweede bron genegeerd.",
                     "aster_results_export: WARNING: '{0}' twice in "
                     "FIELD_TABLE, second source ignored.").format(name))
            continue
        target[name] = var
    if fields.rows is None:
        wanted = [g for g in OPT_IN_GROUPS
                  if _wanted(g, groups_wanted, opt_in)]
        for var in _plan_derived(fields, model, conn, wanted,
                                 **(derived or {})):
            target = elem_vars if var.element else node_vars
            if var.name not in target:
                target[var.name] = var
    out = []
    for name, var in node_vars.items():
        for mag, parts in (MAGNITUDES.items() if magnitudes else ()):
            need = [p for p in parts if p not in OPTIONAL_PARTS]
            if parts[0] == name and all(p in node_vars for p in need):
                out.append(_magnitude_var(
                    mag, [node_vars[p] for p in need],
                    [node_vars[p] for p in parts
                     if p in OPTIONAL_PARTS and p in node_vars]))
        out.append(var)
    return out + list(elem_vars.values())


def _magnitude_var(name, parts, optional=()):
    """sqrt(x^2+y^2+z^2) op knopen waar alle verplichte componenten
    bestaan; een optionele component (OPTIONAL_PARTS) telt mee waar hij
    bestaat en is elders 0."""
    ids = parts[0].ids
    for p in parts[1:]:
        ids = np.intersect1d(ids, p.ids)
    pos = [np.searchsorted(p.ids, ids) for p in parts]
    opt = []
    for p in optional:
        here = np.isin(ids, p.ids)
        opt.append((p, here, np.searchsorted(p.ids, ids[here])))

    def getter(fields):
        vals = [p.getter(fields) for p in parts]
        if any(v is None for v in vals):
            return None
        sq = sum(v[k] ** 2 for v, k in zip(vals, pos))
        for p, here, k in opt:
            v = p.getter(fields)
            if v is not None:
                sq[here] += v[k] ** 2
        return np.sqrt(sq)
    return _Var(name, False, ids.astype("<i4"), getter)


# ==========================================
# AFGELEIDE VELDEN: SCHALEN, FACTOR OF SAFETY, CONTACTSTATUS
# ==========================================
# Schalen (DKT/DST/COQUE_3D): Code-Aster geeft SIGM_ELNO, EPSI_ELNO en
# EFGE_ELNO in het lokale assenstelsel van het element: x = projectie van
# de referentievector (AFFE_CARA_ELEM COQUE VECTEUR, zonder: globaal X) op
# het elementvlak, n = normaal uit de knoopvolgorde, y = n x x (U4.42.01,
# COQUE/VECTEUR). Nagelopen met een run: strook in het XY-vlak onder 30
# graden, SIGM_ELNO SIXX = sigma_xx globaal; SUP = kant van +n.
# Mecway (headless gezien, Mecway 34, strook onder 30 graden en recht):
#   - spanningstensor in GLOBALE XYZ op boven-, midden- en ondervlak:
#     stress<ij>u1 / m1 / b1 (laag 1); boven = +W;
#   - totale rek idem: lstrain<ij>u / m / b, schuif als hoekverdraaiing
#     gamma, lstrainzz = 0 (vlakke spanning; Code-Aster EPZZ = 0);
#   - krachten en momenten per lengte in Mecway's eigen U,V,W:
#     forceperlengthu/v/uv (N/m), momentu/v/uv (N.m/m; momentu > 0 geeft
#     trek boven), shearuw/shearvw (dwarskracht per lengte). U = projectie
#     van de orientatievector of de rand van knoop 1 naar 2 (kwadratisch:
#     1 naar 3), V = W x U (manual v34 par. 7.4.2).
# Knoopwaarden zijn het gemiddelde van de elementwaarden in de knoop
# (zoals Mecway en Code-Aster's _NOEU); daarnaast als elementnodevariable.
# Gekromde kwadratische schalen: de normaal is die van het vlak door de
# hoekknopen (Code-Aster en Mecway variëren hem per punt; NIET
# geverifieerd voor sterk gekromde elementen).
_TENSOR_ORDER = (("xx", 0, 0), ("yy", 1, 1), ("zz", 2, 2), ("xy", 0, 1),
                 ("yz", 1, 2), ("zx", 2, 0))
_SIGM_IJ = {"SIXX": (0, 0), "SIYY": (1, 1), "SIZZ": (2, 2), "SIXY": (0, 1),
            "SIXZ": (0, 2), "SIYZ": (1, 2)}
_EPSI_IJ = {"EPXX": (0, 0), "EPYY": (1, 1), "EPZZ": (2, 2), "EPXY": (0, 1),
            "EPXZ": (0, 2), "EPYZ": (1, 2)}
_SHELL_LEVELS = (("sup", "u"), ("moy", "m"), ("inf", "b"))
_SHELL_FORCE_NAMES = ("forceperlengthu", "forceperlengthv",
                      "forceperlengthuv", "momentu", "momentv", "momentuv",
                      "shearuw", "shearvw")


def _elset_of(model):
    out = {}
    for name, eids in model["elsets"].items():
        for e in eids:
            out.setdefault(e, name)
    return out


def _shell_frame(model, xyz, cell_nodes, eid, vectors, elset_of):
    """(R, cos, sin): R met kolommen x, y, n van Code-Aster's lokale
    schaalassen (zie de kop hierboven) en de hoek van Mecway's U in dat
    stelsel, of None bij een ontaard element."""
    shape, nids = model["elements"][eid]
    ncorner = 3 if shape.startswith("tri") else 4
    p = xyz[list(cell_nodes[:ncorner])]
    if ncorner == 4:
        n = np.cross(p[2] - p[0], p[3] - p[1])
    else:
        n = np.cross(p[1] - p[0], p[2] - p[0])
    if np.linalg.norm(n) == 0.0:
        return None
    n = n / np.linalg.norm(n)
    v = np.asarray(vectors.get(elset_of.get(eid), (1.0, 0.0, 0.0)),
                   dtype=float)
    x = v - v.dot(n) * n
    if np.linalg.norm(x) == 0.0:
        return None
    x = x / np.linalg.norm(x)
    y = np.cross(n, x)
    u = model.get("uaxes", {}).get(eid)
    if u is None:
        coords = model["coords"]
        j = 2 if shape in ("tri6", "quad8") else 1
        u = coords[nids[j] - 1] - coords[nids[0] - 1]
    u = np.asarray(u, dtype=float)
    u = u - u.dot(n) * n
    if np.linalg.norm(u) == 0.0:
        u = x
    u = u / np.linalg.norm(u)
    return np.column_stack((x, y, n)), float(u.dot(x)), float(u.dot(y))


def _shell_points(fields, rkey, field, cmp0, conn, model, xyz, vectors,
                  elset_of, frames):
    """Punten van de schaalcellen van een ELNO-veld (een subpunt per
    knoop, dus na POST_CHAMP EXTR_COQUE of EFGE_ELNO), met per punt de
    knoop, het assenstelsel en de verzamelvolgorde voor Mecway's
    elementnodevariable; of None. frames: cache {eid: _shell_frame}."""
    found = _cells_field(fields, rkey, field, cmp0, conn)
    if found is None:
        return None
    d, _icmp, (start, nbpt, nbsp) = found
    shells = dict((e, v) for e, v in model["elements"].items()
                  if v[0] in SHELL_SHAPES)
    cells = _match_cells(conn, shells, nbpt, nbsp, fields.n)
    rows, node, rot, cs, gather, eids = [], [], [], [], [], []
    for eid in sorted(cells):
        c = cells[eid]
        cn = list(conn[c])
        if eid not in frames:
            frames[eid] = _shell_frame(model, xyz, cn, eid, vectors,
                                       elset_of)
        if frames[eid] is None:
            continue
        r, co, si = frames[eid]
        base = len(rows)
        rows.extend(range(start[c], start[c] + nbpt[c]))
        node.extend(cn)
        rot.extend([r] * nbpt[c])
        cs.extend([(co, si)] * nbpt[c])
        gather.extend(base + cn.index(nid - 1) for nid in shells[eid][1])
        eids.append(eid)
    if not eids:
        return None
    node = np.array(node)
    ok = node < fields.n
    uniq, inv = np.unique(node[ok], return_inverse=True)
    return {"rows": np.array(rows), "rot": np.array(rot),
            "cs": np.array(cs), "gather": np.array(gather),
            "eids": np.array(eids, dtype="<i4"), "ok": ok, "uniq": uniq,
            "inv": inv, "count": np.bincount(inv).astype(float)}


def _cached(fields, key, compute):
    """Waarde per tijdstap een keer berekenen (fields.data wordt per index
    geleegd)."""
    k = ("afgeleid",) + key
    if k not in fields.data:
        fields.data[k] = compute()
    return fields.data[k]


def _shell_tensor(fields, plan, rkey, field, cmap):
    """(punten, 6) globale tensor xx, yy, zz, xy, yz, zx (R T R^T), of
    None."""
    d = fields.get(rkey, field, True)
    if d is None:
        return None
    vals = d[1][plan["rows"]]
    t = np.zeros((len(vals), 3, 3))
    for name, (i, j) in cmap.items():
        if name in d[0]:
            v = vals[:, d[0].index(name)]
            t[:, i, j] = v
            t[:, j, i] = v
    g = np.einsum("pik,pkl,pjl->pij", plan["rot"], t, plan["rot"])
    return np.column_stack([g[:, i, j] for _s, i, j in _TENSOR_ORDER])


def _shell_forces(fields, plan, rkey):
    """(punten, 8) krachten en momenten per lengte in Mecway's U,V (zie
    _SHELL_FORCE_NAMES), uit EFGE_ELNO (NXX..MXY, QX, QY in Code-Aster's
    x,y), of None. U = cos x + sin y, V = -sin x + cos y."""
    d = fields.get(rkey, "EFGE_ELNO", True)
    if d is None:
        return None
    vals = d[1][plan["rows"]]

    def col(name):
        if name in d[0]:
            return vals[:, d[0].index(name)]
        return np.zeros(len(vals))
    c, s = plan["cs"][:, 0], plan["cs"][:, 1]
    out = []
    for p in ("N", "M"):
        xx, yy, xy = col(p + "XX"), col(p + "YY"), col(p + "XY")
        out += [c * c * xx + 2 * c * s * xy + s * s * yy,
                s * s * xx - 2 * c * s * xy + c * c * yy,
                c * s * (yy - xx) + (c * c - s * s) * xy]
    qx, qy = col("QX"), col("QY")
    out += [c * qx + s * qy, -s * qx + c * qy]
    return np.column_stack(out)


def _point_vars(plan, name_cols, compute, key):
    """Knoop- en elementnodevariabelen uit een functie die per tijdstap
    een (punten, k)-matrix geeft. name_cols: [(Mecway-naam, kolom,
    factor)]."""
    out = []
    for name, col, factor in name_cols:
        def node_get(fields, col=col, factor=factor):
            m = _cached(fields, key, compute(fields))
            if m is None:
                return None
            v = m[plan["ok"], col] * factor
            return np.bincount(plan["inv"], weights=v) / plan["count"]

        def elem_get(fields, col=col, factor=factor):
            m = _cached(fields, key, compute(fields))
            if m is None:
                return None
            return m[plan["gather"], col] * factor
        out.append(_Var(name, False, (plan["uniq"] + 1).astype("<i4"),
                        node_get))
        out.append(_Var(name, True, plan["eids"], elem_get))
    return out


def _fos_vars(fields, model, conn, strengths):
    """
    Factor of safety bij Mecway's von Mises-faalcriterium (manual v34 par.
    8.7: de factor waarmee alle spanningscomponenten de faalgrens bereiken;
    bij von Mises dus S / sigma_vM, met S = tensilestrength van het
    materiaal; schalen: de kleinste van boven- en onderkant). Mecway
    rekent hem pas bij het tonen (headless niet in de oplossing, naam
    factorofsafety nagelopen met solution.node_value); variabele
    factorofsafety, Mecway maakt er het item "failure" bij.
    Knoop: kleinste S van de elsets met een criterium in die knoop
    gedeeld door de grootste von Mises (volume, schaal boven/onder);
    element: per element-knoop met de eigen S. Onbelast: FOS_MAX.
    """
    if not strengths:
        return []
    elset_of = _elset_of(model)
    n = fields.n
    s_node = np.full(n, np.inf)
    for name, eids in model["elsets"].items():
        if strengths.get(name, 0.0) > 0.0:
            nids = [nid - 1 for e in eids for nid in model["elements"][e][1]]
            np.minimum.at(s_node, np.array(nids, dtype=int),
                          float(strengths[name]))
    sources = [(r, f) for r, f in (("res", "SIEQ_NOEU"),
                                   ("res_sup", "SIEQ_NOEU"),
                                   ("res_inf", "SIEQ_NOEU"))
               if r in fields.results]
    have = np.zeros(n, dtype=bool)
    for r, f in sources:
        d = fields.get(r, f, False)
        if d is not None and "VMIS" in d[0]:
            have |= d[2][:, d[0].index("VMIS")]
    rows = np.nonzero(have & np.isfinite(s_node))[0]
    out = []
    if len(rows):
        def node_get(fields):
            sig = np.zeros(len(rows))
            found = False
            for r, f in sources:
                d = fields.get(r, f, False)
                if d is None or "VMIS" not in d[0]:
                    continue
                k = d[0].index("VMIS")
                v = np.where(d[2][rows, k], np.abs(d[1][rows, k]), 0.0)
                sig = np.maximum(sig, v)
                found = True
            if not found:
                return None
            return _fos(s_node[rows], sig)
        out.append(_Var("factorofsafety", False, (rows + 1).astype("<i4"),
                        node_get))
    # Per element: volumes uit res, schalen uit res_sup en res_inf.
    parts = []      # (eids, [(rkey, gather)], S per waarde)
    found = _cells_field(fields, "res", "SIEQ_ELNO", "VMIS", conn)
    if found is not None:
        d, icmp, (start, nbpt, nbsp) = found
        solids = dict((e, v) for e, v in model["elements"].items()
                      if v[0] in SOLID_SHAPES and
                      strengths.get(elset_of.get(e), 0.0) > 0.0)
        cells = _match_cells(conn, solids, nbpt, nbsp, n)
        eids, gather, svals = [], [], []
        for eid in sorted(cells):
            c = cells[eid]
            cn = list(conn[c])
            gather.extend(start[c] + cn.index(nid - 1)
                          for nid in solids[eid][1])
            svals += [strengths[elset_of[eid]]] * len(solids[eid][1])
            eids.append(eid)
        if eids:
            parts.append((eids, [("res", np.array(gather))], svals))
    shell_g = []
    for rkey in ("res_sup", "res_inf"):
        found = (_cells_field(fields, rkey, "SIEQ_ELNO", "VMIS", conn)
                 if rkey in fields.results else None)
        if found is None:
            continue
        d, icmp, (start, nbpt, nbsp) = found
        shells = dict((e, v) for e, v in model["elements"].items()
                      if v[0] in SHELL_SHAPES and
                      strengths.get(elset_of.get(e), 0.0) > 0.0)
        cells = _match_cells(conn, shells, nbpt, nbsp, n)
        eids, gather, svals = [], [], []
        for eid in sorted(cells):
            c = cells[eid]
            cn = list(conn[c])
            gather.extend(start[c] + cn.index(nid - 1)
                          for nid in shells[eid][1])
            svals += [strengths[elset_of[eid]]] * len(shells[eid][1])
            eids.append(eid)
        if eids:
            shell_g.append((eids, (rkey, np.array(gather)), svals))
    if shell_g and all(g[0] == shell_g[0][0] for g in shell_g):
        parts.append((shell_g[0][0], [g[1] for g in shell_g], shell_g[0][2]))
    if parts:
        # Volgorde van Mecway: elementnummers oplopend, per element de
        # waarden (een per knoop) achter elkaar.
        blocks = []
        for p, (eids, _src, _svals) in enumerate(parts):
            off = 0
            for eid in eids:
                size = len(model["elements"][eid][1])
                blocks.append((eid, p, off, size))
                off += size
        blocks.sort()
        order = [(p, off + i) for _e, p, off, size in blocks
                 for i in range(size)]
        all_eids = np.array([b[0] for b in blocks], dtype="<i4")

        def elem_get(fields):
            vals = []
            for eids, src, svals in parts:
                sig = None
                for rkey, gather in src:
                    d = fields.get(rkey, "SIEQ_ELNO", True)
                    if d is None or "VMIS" not in d[0]:
                        return None
                    v = np.abs(d[1][gather, d[0].index("VMIS")])
                    sig = v if sig is None else np.maximum(sig, v)
                vals.append(_fos(np.array(svals, dtype=float), sig))
            return np.array([vals[p][i] for p, i in order])
        out.append(_Var("factorofsafety", True, all_eids, elem_get))
    return out


def _fos(strength, sigma):
    """S / sigma, met FOS_MAX waar sigma (bijna) 0 is."""
    with np.errstate(divide="ignore", invalid="ignore"):
        f = np.where(sigma > 0.0, strength / np.where(sigma > 0.0, sigma, 1.0),
                     FOS_MAX)
    return np.minimum(f, FOS_MAX)


def _contact_state_var(fields):
    """
    contactstate op de slave-knopen: 0 open, 1 gesloten, 2 gesloten en
    glijdend (alleen met wrijving en CONT_NOEU). Mecway: 1 in contact, 0
    niet (manual v34 par. 9.9). Bron:
      - CONT_NOEU, component CONT (0 geen contact, 1 kleven, 2 glijden;
        U4.44.11, waarde 2 met wrijving NIET geverifieerd). Code-Aster
        17.4 maakt het veld alleen bij integratie in de knopen (lineaire
        vlakken), anders alarm CONTACT3_16 "le champ CONT_NOEU n'est pas
        créé" (gezien). Zonder wrijving (geen LAGS_F1 in DEPL) geeft CONT
        2 voor elk gesloten punt (gezien in NL-30): dan 1.
      - anders de contactdruk p = -LAGS_C: gesloten waar p > 1% van de
        grootste p in die stap. Open knopen hebben geen exacte 0 (gezien
        met PENALISATION en hex20: |p| tot ~0,1% van de piek naast het
        contact), vandaar de marge; glijden is zo niet te onderscheiden.
    """
    d = fields.get("res", "DEPL", False)
    if d is None or "LAGS_C" not in d[0]:
        return []
    k = d[0].index("LAGS_C")
    rows = np.nonzero(d[2][:, k])[0]
    if not len(rows):
        return []

    def getter(fields):
        dd = fields.get("res", "DEPL", False)
        if dd is None or "LAGS_C" not in dd[0]:
            return None
        cont = fields.get("res", "CONT_NOEU", False)
        if cont is not None and "CONT" in cont[0]:
            j = cont[0].index("CONT")
            state = np.where(cont[2][rows, j], cont[1][rows, j], 0.0)
            if "LAGS_F1" not in dd[0]:
                state = np.minimum(state, 1.0)
            return state
        p = -dd[1][rows, dd[0].index("LAGS_C")]
        tol = CONTACT_CLOSED * max(float(p.max()), 0.0)
        return np.where(p > tol, 1.0, 0.0)
    return [_Var("contactstate", False, (rows + 1).astype("<i4"), getter)]


def _plan_derived(fields, model, conn, wanted, shell_vectors=None,
                  strengths=None):
    """_Var's van de afgeleide velden (zie de kop van dit blok) voor de
    gekozen groepen (wanted). shell_vectors: {Mecway-elset: VECTEUR} van
    AFFE_CARA_ELEM COQUE (zonder: globaal X); strengths: {Mecway-elset:
    tensilestrength in Pa} van materialen met een von Mises-
    faalcriterium."""
    out = []
    if "contact" in wanted:
        out += _contact_state_var(fields)
    if "safety_factor" in wanted:
        out += _fos_vars(fields, model, conn, strengths or {})
    shell_groups = [g for g in ("shell_stresses", "strain", "shell_forces")
                    if g in wanted]
    if not shell_groups:
        return out
    xyz = np.asarray(fields.results["res"].getMesh().getCoordinates()
                     .getValues(), dtype=float).reshape(-1, 3)
    vectors = shell_vectors or {}
    elset_of = _elset_of(model)
    frames = {}
    specs = []
    if "shell_stresses" in wanted:
        specs += [("res_" + lvl, "SIGM_ELNO", "SIXX", _SIGM_IJ, "stress",
                   suf + "1", 1.0) for lvl, suf in _SHELL_LEVELS]
    if "strain" in wanted:
        specs += [("eps_" + lvl, "EPSI_ELNO", "EPXX", _EPSI_IJ, "lstrain",
                   suf, 2.0) for lvl, suf in _SHELL_LEVELS]
    for rkey, field, cmp0, cmap, prefix, suffix, shear in specs:
        if rkey not in fields.results:
            continue
        plan = _shell_points(fields, rkey, field, cmp0, conn, model, xyz,
                             vectors, elset_of, frames)
        if plan is None:
            continue

        def compute(fields, plan=plan, rkey=rkey, field=field, cmap=cmap):
            return lambda: _shell_tensor(fields, plan, rkey, field, cmap)
        cols = [(prefix + s + suffix, k, shear if i != j else 1.0)
                for k, (s, i, j) in enumerate(_TENSOR_ORDER)]
        out += _point_vars(plan, cols, compute, (rkey, field))
    if "shell_forces" in wanted and "res_efs" in fields.results:
        plan = _shell_points(fields, "res_efs", "EFGE_ELNO", "NXX", conn,
                             model, xyz, vectors, elset_of, frames)
        if plan is not None:
            def compute(fields, plan=plan):
                return lambda: _shell_forces(fields, plan, "res_efs")
            out += _point_vars(plan, [(name, k, 1.0) for k, name in
                                      enumerate(_SHELL_FORCE_NAMES)],
                               compute, ("res_efs", "EFGE_ELNO"))
    return out


def _assign_groups(var, model, elset_nodes, free_nodes):
    """
    Posities binnen var.ids per maxandmin-component (zie kop): eerst ""
    (knopen buiten elementen), dan per elset. Lege componenten vallen af.
    """
    if var.element:
        block = np.array([len(model["elements"][e][1]) for e in var.ids])
        start = np.concatenate([[0], np.cumsum(block)[:-1]])
        where = dict((int(e), i) for i, e in enumerate(var.ids))
        for name, eids in model["elsets"].items():
            pos = [np.arange(start[where[e]], start[where[e]] + block[where[e]])
                   for e in eids if e in where]
            if pos:
                var.groups.append((name, np.concatenate(pos)))
        return
    candidates = [("", free_nodes)] + list(elset_nodes.items())
    for name, nids in candidates:
        # Posities in de oplopende var.ids van de knopen van deze groep.
        pos = np.searchsorted(var.ids, nids[np.isin(nids, var.ids)])
        if len(pos):
            var.groups.append((name, pos))


# ==========================================
# SCHRIJVEN
# ==========================================
def _xml_attr(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _num(x):
    """Getal zoals Mecway het in max/min schrijft (15 significante
    cijfers)."""
    x = float(x)
    if x == 0.0:
        x = 0.0     # geen "-0" (Mecway schrijft "0")
    return "{0:.15G}".format(x)


def _b64(data):
    """base64 in regels van 64 tekens met CRLF, plus een CRLF aan het eind
    (zoals Mecway)."""
    enc = base64.b64encode(data)
    lines = [enc[i:i + _B64_LINE] for i in range(0, len(enc), _B64_LINE)]
    return _NL.join(lines) + _NL


def _ids_block(var, indent):
    tag = "elementnodeids" if var.element else "nodeids"
    return (indent + '<{0} name="{1}">'.format(tag, _xml_attr(var.name))
            ).encode("utf-8") + _b64(var.ids.tobytes()) + \
        "</{0}>".format(tag).encode("ascii") + _NL


def _var_block(var, values, indent, dtype, values_tag):
    """Een <nodevariable>/<elementnodevariable> als bytes."""
    tag = "elementnodevariable" if var.element else "nodevariable"
    empty = "elements" if var.element else "nodes"
    i1, i2 = indent + "  ", indent + "    "
    vals = np.asarray(values, dtype=dtype)
    parts = [indent + '<{0} name="{1}">'.format(tag, _xml_attr(var.name)),
             i1 + "<maxandmin>"]
    for name, pos in var.groups:
        sub = vals[pos]
        parts.append(i2 + '<component name="{0}" max="{1}" min="{2}" />'
                     .format(_xml_attr(name), _num(sub.max()),
                             _num(sub.min())))
    parts.append(i1 + "</maxandmin>")
    head = "\r\n".join(parts) + "\r\n" + i1 + "<{0}>".format(values_tag)
    tail = "</{0}>\r\n{1}<{2} />\r\n{1}<values />\r\n{3}</{4}>\r\n".format(
        values_tag, i1, empty, indent, tag)
    return head.encode("utf-8") + _b64(vals.tobytes()) + tail.encode("ascii")


def _is_static(res, indexes):
    """Statisch (geen <timestep>): een index en een EVOL_ELAS-resultaat
    (MECA_STATIQUE). Lukt getType() niet, dan alleen op het aantal."""
    if len(indexes) != 1:
        return False
    try:
        return "ELAS" in str(res.getType()).upper()
    except Exception:
        return True


def _mode_kind(res):
    """'frequency' (MODE_MECA, MODE_ACOU), 'buckling' (MODE_FLAMB) of
    None."""
    try:
        kind = str(res.getType()).upper()
    except Exception:
        return None
    if "FLAMB" in kind:
        return "buckling"
    if kind.startswith("MODE_MECA") or kind.startswith("MODE_ACOU"):
        return "frequency"
    return None


def _is_acoustic(res):
    """True voor akoestische modes (MODE_ACOU, bridge_acoustic.py)."""
    try:
        return str(res.getType()).upper().startswith("MODE_ACOU")
    except Exception:
        return False


def _mass_scales(res, indexes):
    """
    {index: 1/sqrt(MASS_GENE)}: akoestische vormen met p^T M p = 1, zoals
    Mecway (bridge_acoustic.py, kop). NORM_MODE werkt in Code-Aster 17.4
    niet voor MODE_ACOU (MASS_GENE als norm gaf max |p| = 1, gezien);
    MASS_GENE in de tabel is p^T M p van de berekende vorm (nagerekend:
    constante mode van een buis 1 x 0,1 x 0,1 m, c = 340 m/s, RHO = 1:
    MASS_GENE 8,6505e-8 = V / c^2, schaal 3400 = Mecway's waarde).
    """
    out = {}
    for nr, (gen,) in _table_values(res, ("MASS_GENE",)).items():
        if nr in indexes and gen and float(gen) > 0.0:
            out[nr] = 1.0 / np.sqrt(float(gen))
    return out


def _table_values(res, names):
    """{NUME_ORDRE: [waarde per naam]} uit RECU_TABLE: parameters als
    CHAR_CRIT en MASS_EFFE_UN_DX staan niet in getAccessParameters()
    (nagelopen met Code-Aster 17.4; daar alleen NUME_ORDRE, FREQ,
    NUME_MODE, NOEUD_CMP). Een onbekende parameter geeft <EXCEPTION>
    UTILITAI3_5 (bijv. MASS_EFFE_UN_DRX)."""
    from code_aster.Commands import RECU_TABLE
    vals = RECU_TABLE(CO=res, NOM_PARA=tuple(names)).EXTR_TABLE().values()
    return dict((nr, [vals[k][i] for k in names])
                for i, nr in enumerate(vals["NUME_ORDRE"]))


def _mode_values(res, kind):
    """{index: frequentie in Hz of kniklastfactor}. De kniklastfactor is
    CHAR_CRIT zelf: Mecway's BucklingBeam (drukkracht 1 N op een
    ingeklemde kolom) gaf in Mecway 41124,6991224029 en in Code-Aster
    CHAR_CRIT = +41124,699122467 (gezien). Een negatieve CHAR_CRIT is knik
    bij de omgekeerde belasting."""
    if kind == "buckling":
        return dict((nr, float(v[0])) for nr, v in
                    _table_values(res, ("CHAR_CRIT",)).items())
    acc = res.getAccessParameters()
    return dict((i, float(v)) for i, v in
                zip(acc["NUME_ORDRE"], acc["FREQ"]))


# Effectieve massa als fractie van de totale massa per richting (MODE_MECA).
# Code-Aster kent alleen de translaties als parameter; de rotaties rekent
# _rotation_fractions zelf (zelfde definitie, starre rotatie om de
# globale assen door de oorsprong, zoals Mecway).
_MASS_FRACTIONS = ("MASS_EFFE_UN_DX", "MASS_EFFE_UN_DY", "MASS_EFFE_UN_DZ")
_ROT_FRACTIONS = ("MASS_EFFE_UN_DRX", "MASS_EFFE_UN_DRY", "MASS_EFFE_UN_DRZ")
_DOF_INDEX = {"DX": 0, "DY": 1, "DZ": 2, "DRX": 3, "DRY": 4, "DRZ": 5}

# Effectieve massa in Mecway (S12): Mecway's eigen modale oplossing (interne
# solver, met "modal effective mass" en "modal effective mass fraction"
# onder Solution) schrijft per <mode>, voor de <nodevariable>s:
#   <globalvariable name="modaleffectivemassty">57.7394288067102</globalvariable>
#   <globalvariable name="modaleffectivemassfractionty">0.627861821259979</...>
# per richting tx, ty, tz, rx, ry, rz (massa en fractie om en om; headless
# gezien met Mecway 33 op Samples/VibratingCantileverSolid.liml). Een
# resultaat met deze globalvariables geeft bij het openen zelf de items
# "modal effective mass" (kg, kg.m2) en "modal effective mass fraction"
# (headless nagelopen: Mecway voegt de <fieldvariable>s toe bij mw.save_as).
# De bridge schrijft dezelfde namen; de fractie is die van Code-Aster
# (noemer R^T M R inclusief de opgelegde knopen, _effective_masses), NIET
# Mecway's noemer (vrije massa). Extra (eigen naam van de bridge): de
# cumulatieve fractie over de modes tot en met deze mode; Mecway bewaart
# onbekende globalvariables (headless nagelopen), of de GUI ze toont is
# NIET geverifieerd.
_MW_DIRS = ("tx", "ty", "tz", "rx", "ry", "rz")
_MODE_GLOBALS = {}      # id(res) -> {index: [(naam, waarde)]}


def _store_mode_globals(res, indexes, absolute, fractions):
    """
    Bewaar de effectieve massa per mode voor export_results (globalvariables
    in <mode>, zie hierboven). absolute: {index: [m_eff x 6]} (kg, kg.m2) of
    {}; fractions: {index: [fractie x 6]}, None waar onbekend. Een richting
    zonder fractie krijgt ook geen cumulatieve fractie.
    """
    out = {}
    cum = [0.0] * 6
    for idx in sorted(indexes):
        mass = list(absolute.get(idx) or [None] * 6)
        frac = list(fractions.get(idx) or [None] * 6)
        items = []
        for k, d in enumerate(_MW_DIRS):
            if k < len(mass) and mass[k] is not None:
                items.append(("modaleffectivemass" + d, float(mass[k])))
            if k < len(frac) and frac[k] is not None:
                items.append(("modaleffectivemassfraction" + d,
                              float(frac[k])))
        for k, d in enumerate(_MW_DIRS):
            if k < len(frac) and frac[k] is not None:
                cum[k] += float(frac[k])
                items.append(("cumulativeeffectivemassfraction" + d, cum[k]))
        if items:
            out[idx] = items
    _MODE_GLOBALS[id(res)] = out


def _matvec(matrix):
    """Functie v -> M v voor een geassembleerde matrix (beide driehoeken
    uit getValuesWithDescription, zie _stiffness_scales) en de dimensie."""
    data, rows, cols, dim = matrix.getValuesWithDescription()
    data = np.asarray(data, dtype=float)
    rows = np.asarray(rows, dtype=np.int64)
    cols = np.asarray(cols, dtype=np.int64)

    def mul(v):
        return np.bincount(rows, weights=data * v[cols], minlength=dim)
    return mul, dim


def _rigid_vectors(matrix, xyz, point=(0.0, 0.0, 0.0)):
    """
    Starre-lichaamsbewegingen als vectoren in de nummering van matrix
    (6 x dim): translatie X, Y, Z en rotatie om de assen X, Y, Z door
    point: u = theta x (x - point), plus theta zelf op de rotatievrijheids-
    graden DRX/DRY/DRZ (balken, schalen, discrete elementen). Lagrange-
    vrijheidsgraden ('LAGR:DX', ...) en andere componenten blijven 0.
    getNodeAndComponentFromDOF: (knoop vanaf 0, component) per
    vrijheidsgraad (Code-Aster-testcases sdll123b, fdlv101a, v17.4).
    """
    pairs = matrix.getDOFNumbering().getNodeAndComponentFromDOF()
    dim = len(pairs)
    vec = np.zeros((6, dim))
    nodes = np.array([p[0] for p in pairs], dtype=np.int64)
    comps = np.array([_DOF_INDEX.get(p[1], -1) for p in pairs])
    ok = (comps >= 0) & (nodes >= 0) & (nodes < xyz.shape[0])
    rel = np.zeros((dim, 3))
    rel[ok] = xyz[nodes[ok]] - np.asarray(point, dtype=float)
    x, y, z = rel[:, 0], rel[:, 1], rel[:, 2]
    for k in range(3):                  # translaties
        vec[k, ok & (comps == k)] = 1.0
    # rotatie om X: u = (0, -z, y); om Y: (z, 0, -x); om Z: (-y, x, 0)
    for k, terms in ((3, ((1, -z), (2, y))), (4, ((0, z), (2, -x))),
                     (5, ((0, -y), (1, x)))):
        for c, value in terms:
            sel = ok & (comps == c)
            vec[k, sel] = value[sel]
        vec[k, ok & (comps == k)] = 1.0
    return vec


def _effective_masses(res, mass, indexes, shapes=None):
    """
    Effectieve massa per mode voor de 6 starre bewegingen R (translatie
    X/Y/Z, rotatie om de globale assen X/Y/Z door de oorsprong), zoals
    Mecway (manual v33 par. 6.3: m_eff = Gamma^2, Gamma = phi^T M R, met
    massagenormeerde phi; hier gedeeld door phi^T M phi, zodat elke
    normering werkt) en als fractie van R^T M R. R^T M R telt, zoals
    Code-Aster's MASS_EFFE_UN_D* (gemeten: ingeklemd blok 0,609971 =
    23,94 / 39,25 kg totaal), de massa van de opgelegde knopen mee; Mecway
    deelt door de vrije massa (zelfde blok 0,6225 = 23,94 / 38,47 kg).
    Returns ({index: [m_eff x 6]}, [R^T M R x 6], zwaartepunt, J_zwp).
    J_zwp: traagheidsmomenten om assen door het zwaartepunt.
    shapes: {index: reele vorm} i.p.v. DEPL (complexe modes:
    _complex_modes).
    """
    mul, dim = _matvec(mass)
    xyz = np.asarray(res.getMesh().getCoordinates().getValues(),
                     dtype=float).reshape(-1, 3)
    rig = _rigid_vectors(mass, xyz)
    if rig.shape[1] != dim:
        raise ValueError(tr("nummering: {0} vrijheidsgraden, matrix {1}",
                            "numbering: {0} degrees of freedom, matrix "
                            "{1}").format(rig.shape[1], dim))
    m_rig = np.array([mul(r) for r in rig])          # M R (6 x dim)
    total = np.einsum("ij,ij->i", rig, m_rig)        # R^T M R
    out = {}
    for idx in indexes:
        if shapes is not None:
            phi = shapes[idx]
        else:
            phi = np.asarray(res.getField("DEPL", idx).getValues(),
                             dtype=float)
        if len(phi) != dim:
            raise ValueError(tr("mode {0}: {1} waarden, matrix {2}",
                                "mode {0}: {1} values, matrix {2}").format(
                idx, len(phi), dim))
        gen = float(phi.dot(mul(phi)))
        gamma = m_rig.dot(phi)
        out[idx] = list(gamma ** 2 / gen) if gen > 0.0 else [0.0] * 6
    # Zwaartepunt en traagheid om het zwaartepunt: R_rot(c) = R_rot(0) -
    # c x R_trans, dus J(c) volgt uit de 6 x 6 massamatrix R^T M R.
    full = rig.dot(m_rig.T)
    mtot = np.mean(np.diag(full)[:3])
    cog = np.zeros(3)
    if mtot > 0.0:
        # R_trans,k^T M R_rot,j = m (e_j x c)_k (koppelterm): bijv.
        # cpl[1, 2] = m c_x en cpl[2, 1] = -m c_x
        cpl = full[:3, 3:]
        cog = np.array([cpl[1, 2] - cpl[2, 1], cpl[2, 0] - cpl[0, 2],
                        cpl[0, 1] - cpl[1, 0]]) / (2.0 * mtot)
    j_cog = [total[3 + k] - mtot * (float(cog.dot(cog)) - cog[k] ** 2)
             for k in range(3)]
    return out, list(total), cog, j_cog


def _is_complex(res):
    """True voor complexe modes (MODE_MECA_C: CALC_MODES met MATR_AMOR,
    bridge_modal_damping)."""
    try:
        return str(res.getType()).upper().startswith("MODE_MECA_C")
    except Exception:
        return False


def _complex_modes(res, mass, indexes):
    """
    Per complexe mode {index: dict}:
      fd    : gedempte frequentie [Hz] = Im(s)/2pi (Code-Aster FREQ);
      zeta  : dempingsverhouding -Re(s)/|s| (AMOR_REDUIT);
      fn    : |s|/2pi = fd / sqrt(1 - zeta^2) (bij proportionele demping de
              ongedempte eigenfrequentie); None als zeta >= 1;
      decay : -Re(s) = zeta 2 pi fn [1/s] (Mecway's decay rate: amplitude
              ~ exp(-decay t)); None als zeta >= 1;
      scale : complexe factor c: de vorm naar Mecway is Re(c phi);
      shape : Re(c phi), de hele vector (effectieve massa);
      imag  : |Im(c phi)|_M / |Re(c phi)|_M: 0 = klassieke (reele) mode,
              bijv. bij Rayleigh-demping; groter bij niet-proportionele
              demping (dempers).
    Fasedraaiing: theta = arg(phi^T M phi) / 2 (transpositie, niet
    geconjugeerd) maakt het reele deel zo groot mogelijk; daarna phi_r^T M
    phi_r = 1 (zoals de reele modes, MASS_GENE) en de grootste component
    positief. Bij een klassieke mode is Re(c phi) dan precies de reele
    massagenormeerde vorm. Zonder massamatrix: fase van de grootste
    component, schaal van Code-Aster.
    """
    table = _table_values(res, ("FREQ", "AMOR_REDUIT"))
    mul = None
    if mass is not None:
        mul, dim = _matvec(mass)
    out = {}
    for idx in indexes:
        phi = np.asarray(res.getField("DEPL", idx).getValues(),
                         dtype=complex)
        if mul is not None and len(phi) == dim:
            mphi = mul(phi.real) + 1j * mul(phi.imag)
            rot = np.exp(-0.5j * np.angle(phi.dot(mphi)))
            psi = phi * rot
            gen = float(psi.real.dot(mul(psi.real)))
            gim = float(psi.imag.dot(mul(psi.imag)))
            scale = rot / np.sqrt(gen) if gen > 0.0 else rot
            imag = np.sqrt(gim / gen) if gen > 0.0 else 0.0
        else:
            k = int(np.argmax(np.abs(phi)))
            scale = np.exp(-1j * np.angle(phi[k])) if abs(phi[k]) else 1.0
            psi = phi * scale
            imag = (float(np.linalg.norm(psi.imag)) /
                    max(float(np.linalg.norm(psi.real)), 1.0e-300))
        shape = (phi * scale).real
        k = int(np.argmax(np.abs(shape)))
        if shape[k] < 0.0:
            scale, shape = -scale, -shape
        fd, zeta = table.get(idx, (None, None))
        fd = float(fd) if fd is not None else 0.0
        zeta = float(zeta) if zeta is not None else 0.0
        if abs(zeta) < 1.0e-10:
            zeta = 0.0      # numeriek 0 (ongedempte mode, gezien ~1e-13)
        fn = decay = None
        if zeta < 1.0:
            fn = fd / np.sqrt(1.0 - zeta ** 2)
            decay = zeta * 2.0 * np.pi * fn
        out[idx] = {"fd": fd, "zeta": zeta, "fn": fn, "decay": decay,
                    "scale": scale, "shape": shape, "imag": float(imag)}
    return out


def _print_complex_modes(res, mass):
    """
    BRIDGE_MODE-regels voor complexe modes (MODE_MECA_C):
      BRIDGE_MODE <nr> FREQ=<gedempt, Hz> AMOR_REDUIT=<zeta>
                  FREQ_NAT=<|s|/2pi, Hz> DECAY=<1/s> IMAG=<..>
                  MASS_EFFE_UN_DX=.. .. MASS_EFFE_UN_DRZ=..
    De effectieve massa (fractie, translaties en rotaties om de oorsprong)
    rekent de bridge met het reele deel van de genormeerde vorm
    (_complex_modes; bij klassieke modes gelijk aan de reele modes, MC-04).
    Of Code-Aster MASS_EFFE_UN_* ook voor complexe modes geeft, is NIET
    nagelopen; RECU_TABLE wordt hier daarom niet gevraagd.
    """
    indexes = sorted(res.getIndexes())
    modes = _complex_modes(res, mass, indexes)
    meff = {}
    absolute = {}
    if mass is not None:
        try:
            meff, total, cog, j_cog = _effective_masses(
                res, mass, indexes,
                shapes=dict((i, m["shape"]) for i, m in modes.items()))
            print("BRIDGE_MASSA M={0} JX={1} JY={2} JZ={3} ZWP={4},{5},{6} "
                  "JZX={7} JZY={8} JZZ={9}".format(*[_num(v) for v in (
                      [total[0]] + total[3:] + list(cog) + j_cog)]))
            absolute = meff
            meff = dict((i, [v / t if t > 0.0 else 0.0
                             for v, t in zip(meff[i], total)])
                        for i in meff)
        except Exception as e:
            print(tr("aster_results_export: WAARSCHUWING: effectieve massa "
                     "complexe modes niet berekend: {0}",
                     "aster_results_export: WARNING: effective mass of the "
                     "complex modes not computed: {0}").format(e))
            meff = {}
            absolute = {}
    _store_mode_globals(res, indexes, absolute, meff)
    for idx in indexes:
        m = modes[idx]
        parts = ["BRIDGE_MODE {0} FREQ={1} AMOR_REDUIT={2}".format(
            idx, _num(m["fd"]), _num(m["zeta"]))]
        if m["fn"] is not None:
            parts.append("FREQ_NAT={0} DECAY={1}".format(
                _num(m["fn"]), _num(m["decay"])))
        parts.append("IMAG={0:.3g}".format(m["imag"]))
        for key, value in zip(_MASS_FRACTIONS + _ROT_FRACTIONS,
                              meff.get(idx, [])):
            parts.append("{0}={1:.6g}".format(key, float(value)))
        print(" ".join(parts))
        if m["fn"] is None:
            print("BRIDGE_COMPLEX_OVERKRITISCH mode={0} zeta={1:.6g}".format(
                idx, m["zeta"]))


def print_modes(res, mass=None):
    """
    Overzicht per mode in de .mess, gelezen door de bridge
    (bridge_results_liml.read_mode_summary):
      BRIDGE_MODE <nr> FREQ=<Hz> MASS_EFFE_UN_DX=.. MASS_EFFE_UN_DY=.. ..
                  MASS_EFFE_UN_DRX=.. MASS_EFFE_UN_DRY=.. MASS_EFFE_UN_DRZ=..
      BRIDGE_MODE <nr> CHAR_CRIT=<kniklastfactor>
      BRIDGE_MASSA M=.. JX=.. JY=.. JZ=.. ZWP=x,y,z JZX=.. JZY=.. JZZ=..
    mass: de geassembleerde massamatrix (MASS_MECA) voor de rotaties;
    None = alleen de translaties van Code-Aster. JX/JY/JZ: R^T M R van de
    rotaties om de assen door de oorsprong (noemer van de fracties);
    JZX/JZY/JZZ: om de assen door het zwaartepunt ZWP.
    """
    kind = _mode_kind(res)
    if kind is None:
        return
    try:
        if kind == "buckling":
            for nr, (cc,) in sorted(_table_values(
                    res, ("CHAR_CRIT",)).items()):
                print("BRIDGE_MODE {0} CHAR_CRIT={1}".format(
                    nr, _num(cc)))
            return
        if _is_complex(res):
            _print_complex_modes(res, mass)
            return
        if _is_acoustic(res):
            # Holtemodes: geen effectieve massa (RECU_TABLE MASS_EFFE_UN_DX
            # zou een <EXCEPTION> in de .mess geven).
            for nr, freq in sorted(_mode_values(res, kind).items()):
                print("BRIDGE_MODE {0} FREQ={1}".format(nr, _num(freq)))
            return
        try:
            fractions = _table_values(res, _MASS_FRACTIONS)
        except Exception as e:
            print(tr("aster_results_export: effectieve massa niet "
                     "beschikbaar: {0}",
                     "aster_results_export: effective mass not available: "
                     "{0}").format(e))
            fractions = {}
        values = _mode_values(res, kind)
        rot, absolute = _rotation_fractions(res, mass, sorted(values),
                                            fractions)
        # Voor export_results: Mecway's globalvariables per mode
        # (translaties: MASS_EFFE_UN_D* van Code-Aster zelf)
        _store_mode_globals(res, values, absolute, dict(
            (nr, [None if v is None else float(v) for v in
                  (list(fractions.get(nr, [])) + [None] * 3)[:3]] +
             list(rot.get(nr, [None] * 3))) for nr in values))
        for nr, freq in sorted(values.items()):
            parts = ["BRIDGE_MODE {0} FREQ={1}".format(nr, _num(freq))]
            items = list(zip(_MASS_FRACTIONS, fractions.get(nr, [])))
            items += list(zip(_ROT_FRACTIONS, rot.get(nr, [])))
            for key, value in items:
                if value is not None:
                    parts.append("{0}={1:.6g}".format(key, float(value)))
            print(" ".join(parts))
    except Exception as e:
        print(tr("aster_results_export: WAARSCHUWING: modeoverzicht: {0}",
                 "aster_results_export: WARNING: mode summary: {0}").format(
            e))


def _rotation_fractions(res, mass, indexes, fractions):
    """
    ({index: [fractie rotatie X, Y, Z]}, {index: [m_eff x 6]}) uit
    _effective_masses, of ({}, {}) zonder massamatrix of bij een fout.
    Controle: de zelf gerekende translaties moeten gelijk zijn aan
    Code-Aster's MASS_EFFE_UN_D* (anders klopt de koppeling van
    vrijheidsgraden en knopen niet: geen rotaties en geen absolute massa).
    """
    if mass is None:
        return {}, {}
    try:
        meff, total, cog, j_cog = _effective_masses(res, mass, indexes)
    except Exception as e:
        print(tr("aster_results_export: WAARSCHUWING: effectieve massa "
                 "rotaties niet berekend: {0}",
                 "aster_results_export: WARNING: effective mass of the "
                 "rotations not computed: {0}").format(e))
        return {}, {}
    worst = 0.0
    for idx in indexes:
        for k, ref in enumerate(fractions.get(idx, [])):
            if ref is not None and total[k] > 0.0:
                worst = max(worst, abs(meff[idx][k] / total[k] - float(ref)))
    if worst > 1.0e-4:
        print(tr("aster_results_export: WAARSCHUWING: effectieve massa "
                 "rotaties niet gegeven: de eigen berekening van de "
                 "translaties wijkt {0:.3g} af van MASS_EFFE_UN_D* van "
                 "Code-Aster.",
                 "aster_results_export: WARNING: effective mass of the "
                 "rotations not given: the own calculation of the "
                 "translations differs {0:.3g} from Code-Aster's "
                 "MASS_EFFE_UN_D*.").format(worst))
        return {}, {}
    print("BRIDGE_MASSA M={0} JX={1} JY={2} JZ={3} ZWP={4},{5},{6} JZX={7} "
          "JZY={8} JZZ={9}".format(*[_num(v) for v in (
              [total[0]] + total[3:] + list(cog) + j_cog)]))
    return (dict((idx, [meff[idx][3 + k] / total[3 + k]
                        if total[3 + k] > 0.0 else 0.0 for k in range(3)])
                 for idx in indexes),
            dict((idx, list(meff[idx])) for idx in indexes))


def _stiffness_scales(res, rigi_geo, values):
    """
    {index: factor} zodat de knikvorm phi * factor gegeneraliseerde
    stijfheid 1 heeft (phi^T K phi = 1), zoals Mecway (nagerekend:
    BucklingBeam tip 0,0014040 = 1/sqrt(EI (pi/2L)^4 L/2)). NORM_MODE
    RIGI_GENE kan dat niet voor MODE_FLAMB (<EXCEPTION> ALGELINE4_77
    "l'option de normalisation RIGI_GENE n'est pas implantée", gezien).
    Uit K phi = -CHAR_CRIT Kg phi volgt |phi^T K phi| = |CHAR_CRIT
    phi^T Kg phi|; Kg heeft geen termen op de Lagrange-vrijheidsgraden.
    rigi_geo: de geassembleerde RIGI_GEOM (getValuesWithDescription geeft
    beide driehoeken, assemblymatrix_ext.py v17.4); de vector van DEPL
    heeft dezelfde nummering (lengte gecontroleerd).
    """
    data, rows, cols, dim = rigi_geo.getValuesWithDescription()
    data, rows, cols = np.asarray(data), np.asarray(rows), np.asarray(cols)
    out = {}
    for idx, factor in values.items():
        x = np.asarray(res.getField("DEPL", idx).getValues(), dtype=float)
        if len(x) != dim:
            print(tr("aster_results_export: WAARSCHUWING: normering "
                     "knikvorm {0}: {1} waarden, matrix {2}; niet "
                     "genormeerd.",
                     "aster_results_export: WARNING: normalising buckling "
                     "mode {0}: {1} values, matrix {2}; not "
                     "normalised.").format(idx, len(x), dim))
            continue
        k_gen = abs(factor * float(np.sum(data * x[rows] * x[cols])))
        if k_gen > 0.0:
            out[idx] = 1.0 / np.sqrt(k_gen)
    return out


def _times(res, indexes):
    """{index: tijd} uit de toegangsparameter INST (anders de index)."""
    try:
        acc = res.getAccessParameters()
        return dict(zip(acc["NUME_ORDRE"], acc["INST"]))
    except Exception:
        return dict((i, float(i)) for i in indexes)


def export_results(res, out_path, liml_path, fields=None, extra_results=None,
                   precision="single", static=None, rigi_geo=None,
                   mass=None, node_fields=None, cyclic=None, opt_in=None,
                   shell_vectors=None, strengths=None):
    """
    Schrijf alle gearchiveerde tijdstappen van res als Mecway-<results>-
    fragment (bytes, CRLF, ingesprongen voor plaatsing in <solution>).

    Parameters
    ----------
    res           : Code-Aster-resultaat (na CALC_CHAMP).
    out_path      : doelbestand van het fragment (eerst .tmp, dan hernoemd).
    liml_path     : de .liml waaruit het mesh is geschreven (elsets,
                    elementen en de controle van de knoopvolgorde).
    fields        : lijst groepen uit RESULT_FIELD_SPECS (bijv.
                    ["displacements", "stresses", "vonmises", "reactions"]);
                    None = alles wat in res staat.
    extra_results : {"res_sup": ..., "res_moy": ..., "res_inf": ...}
                    (POST_CHAMP EXTR_COQUE voor schalen), of None.
    precision     : "single" (float32, als Mecway voor OpenRadioss) of
                    "double".
    static        : True/False, of None = automatisch (_is_static).
    rigi_geo      : knik: de geassembleerde RIGI_GEOM; de knikvormen
                    worden dan genormeerd op phi^T K phi = 1 (zoals
                    Mecway, _stiffness_scales). None = zoals berekend.
    mass          : complexe modes (MODE_MECA_C): de geassembleerde
                    MASS_MECA; het reele deel van de vorm wordt dan
                    genormeerd op phi^T M phi = 1 (_complex_modes). Elke
                    mode krijgt <mode frequency="f_d Hz" decayrate=".. 1/s">,
                    zoals Mecway's complexe (akoestische) modes.
    node_fields   : {Mecway-naam: (knoopnummers, waarden)} die in elke stap
                    gelijk zijn (vermoeiing: damage, life; aster_fatigue),
                    of None. Knoopnummers vanaf 1.
    cyclic        : {"axis": 0/1/2 (X/Y/Z), "segments": N} bij cyclische
                    symmetrie (bridge_cyclic), of None. Heeft het mesh van
                    res meer knopen dan de .liml (het skelet van het hele
                    wiel, aster_cyclic.collect), dan gaat het resultaat op
                    Mecway's hele wiel (aster_cyclic.wheel_model: knoop i
                    + j x n, element e + j x ne), alleen knoopvelden.
    opt_in        : zonder fields: de gekozen groepen uit OPT_IN_GROUPS
                    (bridge_to_aster._results_route); None = geen.
    shell_vectors : {Mecway-elset: (vx, vy, vz)} referentievector van de
                    schalen (AFFE_CARA_ELEM COQUE VECTEUR); zonder: X.
    strengths     : {Mecway-elset: tensilestrength [Pa]} voor de factor
                    of safety (von Mises-faalcriterium).

    Returns
    -------
    dict met statistiek (stappen, variabelen, bytes, seconden), of None bij
    een fout (melding in de .mess; de .resu-route blijft dan bruikbaar).
    """
    t0 = time.time()
    try:
        return _export(res, out_path, liml_path, fields, extra_results,
                       precision, static, t0, rigi_geo, mass, node_fields,
                       cyclic, opt_in, {"shell_vectors": shell_vectors,
                                        "strengths": strengths})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(tr("aster_results_export: FOUT: {0}",
                 "aster_results_export: ERROR: {0}").format(e))
        return None


def _export(res, out_path, liml_path, fields, extra_results, precision,
            static, t0, rigi_geo=None, mass=None, node_fields=None,
            cyclic=None, opt_in=None, derived=None):
    """Werk van export_results (zonder de foutafvang)."""
    model = read_liml_model(liml_path)
    n = model["coords"].shape[0]
    mesh = res.getMesh()
    rows = None
    xyz = np.asarray(mesh.getCoordinates().getValues(), dtype=float)
    if cyclic and xyz.size // 3 != n:
        # Hele wiel (aster_cyclic.collect): Mecway's nummering, knopen op
        # coordinaat gekoppeld aan het skelet.
        import aster_cyclic
        model = aster_cyclic.wheel_model(model, int(cyclic["axis"]),
                                         int(cyclic["segments"]))
        rows, err = aster_cyclic.node_rows(xyz, model["coords"])
        n = model["coords"].shape[0]
    else:
        err = _check_node_order(mesh, model["coords"])
    if err:
        print(tr("aster_results_export: FOUT: {0}",
                 "aster_results_export: ERROR: {0}").format(err))
        return None

    results = {"res": res}
    results.update(extra_results or {})
    indexes = list(res.getIndexes())
    modes = _mode_kind(res)
    if modes:
        static = False
    if static is None:
        static = _is_static(res, indexes)
    if static:
        indexes = indexes[:1]
    groups = set(fields) if fields is not None else None
    conn = mesh.getConnectivity()
    lump = None
    pairs = _offset_pairs(mesh, n) if rows is None else None
    if rows is None and (groups is None or "reactions" in groups):
        lump = _reaction_lumping(mesh, conn, n,
                                 None if pairs is None else pairs[1])
    data = _Fields(results, n, lump, rows, pairs)
    if rows is None:
        data.coincident = _coincident_extra(xyz.reshape(-1, 3), n)
    mode_values = _mode_values(res, modes) if modes else None
    if modes == "buckling" and rigi_geo is not None:
        data.scales = _stiffness_scales(res, rigi_geo, mode_values)
    if modes and _is_acoustic(res):
        data.scales = _mass_scales(res, indexes)
    decays = None
    if modes and _is_complex(res):
        cplx = _complex_modes(res, mass, indexes)
        data.scales = dict((i, c["scale"]) for i, c in cplx.items())
        mode_values = dict((i, c["fd"]) for i, c in cplx.items())
        decays = dict((i, c["decay"]) for i, c in cplx.items())
    data.set_index(indexes[-1])
    opt_in = frozenset(opt_in or ())
    variables = _plan_variables(data, model, conn, groups,
                                magnitudes=modes != "frequency",
                                opt_in=opt_in, derived=derived)
    variables += _constant_vars(node_fields, n)
    if not variables:
        print(tr("aster_results_export: FOUT: geen enkel veld gevonden.",
                 "aster_results_export: ERROR: no field found at all."))
        return None
    _report_missing(results, groups, opt_in)
    elset_nodes, free_nodes = _group_nodes(model, n)
    for var in variables:
        _assign_groups(var, model, elset_nodes, free_nodes)

    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        _write_fragment(f, variables, data, indexes,
                        None if (static or modes) else _times(res, indexes),
                        precision, model,
                        (modes, mode_values, decays) if modes else None,
                        _MODE_GLOBALS.get(id(res)) if modes else None)
        size = f.tell()
    os.replace(tmp, out_path)
    stats = {"stappen": len(indexes),
             "variabelen": [v.name for v in variables],
             "bytes": size, "seconden": time.time() - t0,
             "statisch": static, "modes": modes}
    print("aster_results_export: {0} geschreven: {1} stap(pen), {2} "
          "variabelen ({3}), {4:.1f} MB in {5:.2f} s.".format(
              out_path, stats["stappen"], len(variables),
              ", ".join(stats["variabelen"]), size / 1.0e6,
              stats["seconden"]))
    return stats


def _constant_vars(node_fields, n):
    """_Var's voor velden die in elke stap gelijk zijn (node_fields van
    export_results), met oplopende knoopnummers <= n."""
    out = []
    for name, (ids, vals) in (node_fields or {}).items():
        ids = np.asarray(ids, dtype="<i4")
        vals = np.asarray(vals, dtype=float)
        order = np.argsort(ids)
        ids, vals = ids[order], vals[order]
        keep = (ids >= 1) & (ids <= n)
        if not keep.any():
            continue
        ids, vals = ids[keep], vals[keep]
        out.append(_Var(name, False, ids, lambda fields, v=vals: v))
    return out


def _group_nodes(model, n):
    """({elset: oplopende knoopnummers}, knopen in geen enkel element)."""
    elset_nodes = OrderedDict()
    used = np.zeros(n + 1, dtype=bool)
    for name, eids in model["elsets"].items():
        nids = sorted(set(nid for e in eids
                          for nid in model["elements"][e][1]))
        elset_nodes[name] = np.array(nids, dtype="<i4")
        used[nids] = True
    free_nodes = np.nonzero(~used[1:])[0].astype("<i4") + 1
    return elset_nodes, free_nodes


def _write_fragment(f, variables, data, indexes, times, precision, model,
                    modes=None, mode_globals=None):
    """
    Schrijf <results> naar het open bestand f. times = {index: tijd} geeft
    een <timestep> per index; times = None is statisch (een index, de
    variabelen direct onder <results>). modes = (soort, {index: waarde},
    {index: decay rate} of None) geeft een <mode> per index (zie de kop);
    met een decay rate (complexe modes) ook decayrate="<1/s>", zoals
    Mecway's complexe akoestische modes (headless gezien, Mecway 33:
    <mode id="2" frequency="170.000069959994 Hz" decayrate="70.347 1/s">).
    mode_globals: {index: [(naam, waarde)]} (_store_mode_globals) als
    <globalvariable> direct na <mode>, zoals Mecway.
    """
    dtype = "<f4" if precision == "single" else "<f8"
    values_tag = "valuessingle" if precision == "single" else "valuesdouble"
    indent = ("      " if (times is None and modes is None)
              else "        ")
    f.write('    <results precision="{0}">\r\n'.format(precision)
            .encode("ascii"))
    for var in variables:
        f.write(_ids_block(var, "      "))
    for k, idx in enumerate(indexes):
        data.set_index(idx)
        if modes is not None:
            value = modes[1].get(idx, 0.0)
            attr = ('bucklingfactor="{0}"'.format(_num(value))
                    if modes[0] == "buckling"
                    else 'frequency="{0} Hz"'.format(_num(value)))
            decay = (modes[2] or {}).get(idx) if len(modes) > 2 else None
            if decay is not None:
                attr += ' decayrate="{0} 1/s"'.format(_num(decay))
            f.write('      <mode id="{0}" {1}>\r\n'.format(k + 1, attr)
                    .encode("ascii"))
            for name, value in (mode_globals or {}).get(idx, ()):
                f.write('        <globalvariable name="{0}">{1}'
                        '</globalvariable>\r\n'.format(name, _num(value))
                        .encode("ascii"))
        elif times is not None:
            f.write('      <timestep id="{0}" time="{1} s">\r\n'.format(
                k, _num(times.get(idx, idx))).encode("ascii"))
        for var in variables:
            vals = var.getter(data)
            if vals is None:
                print(tr("aster_results_export: WAARSCHUWING: '{0}' "
                         "ontbreekt in index {1}; nullen geschreven.",
                         "aster_results_export: WARNING: '{0}' missing in "
                         "index {1}; zeros written.").format(var.name, idx))
                vals = np.zeros(_value_count(var, model))
            f.write(_var_block(var, vals, indent, dtype, values_tag))
        if modes is not None:
            f.write(b"      </mode>\r\n")
        elif times is not None:
            f.write(b"      </timestep>\r\n")
    f.write(b"    </results>\r\n")


def _value_count(var, model):
    """Aantal waarden van een variabele per tijdstap."""
    if not var.element:
        return len(var.ids)
    return sum(len(model["elements"][e][1]) for e in var.ids)


def _report_missing(results, groups_wanted, opt_in=frozenset()):
    """Meld velden uit FIELD_TABLE die niet in het resultaat staan."""
    missing = set()
    names = {}
    for rkey, r in results.items():
        try:
            names[rkey] = list(r.getFieldsNames())
        except Exception:
            names[rkey] = []
    for group, rkey, field, _c, _n, _k in FIELD_TABLE:
        if not _wanted(group, groups_wanted, opt_in):
            continue
        if groups_wanted is None and group in ("temperature", "heat_flux"):
            continue    # thermisch: alleen als ze gevraagd zijn
        if rkey not in results:
            continue
        if group == "strain" and not field.startswith(
                "EPSG" if "EPSG_NOEU" in names[rkey] else "EPSI"):
            continue    # kleine rekken of Green-Lagrange, een van beide
        if field not in names[rkey]:
            missing.add("{0}:{1}".format(rkey, field))
    if missing:
        print(tr("aster_results_export: niet in het resultaat "
                 "(overgeslagen): {0}",
                 "aster_results_export: not in the result (skipped): "
                 "{0}").format(", ".join(sorted(missing))))
