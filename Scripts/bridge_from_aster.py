# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_from_aster.py
# Verantwoordelijkheid: leest het Code-Aster .resu-bestand (POST_RELEVE_T
# tabel-formaat) en injecteert de resultaten in de actieve Mecway-solution
# via solution.set_variable().
#
# Architectuur:
#   - RESULT_FIELD_SPECS is de centrale registry van alle ondersteunde
#     resultaatvelden. Per analyse selecteert CONFIG_BRIDGE["analyses"][...]
#     ["fields"] een subset hiervan (ook de keuzelijst in het startscherm).
#   - STRUCT_FIELD_SPECS bevat de extra tabellen voor schalen en balken.
#     Die worden automatisch meegeladen als hun 'ouder'-veld actief is
#     (bijv. 'vonmises') en hebben dus geen eigen entry in "fields" nodig.
#   - Nieuw veld toevoegen: entry in RESULT_FIELD_SPECS + zorg dat de
#     bijbehorende POST_RELEVE_T-tabel door bridge_to_aster.py wordt
#     gegenereerd met dezelfde INTITULE (_result_tables).
#
# Belangrijk (Mecway API, solution.set_variable): de lijst met waarden moet
# precies zo lang zijn als het aantal knopen in de SOLUTION. De solution is
# de mesh van de laatste Mecway-solve. Is het model daarna veranderd, dan
# past niet elke Code-Aster-knoop in de solution. main() roept daarom
# check_solution_mesh() aan vóór de Code-Aster-run; AsterToMecway_results()
# meldt daarnaast rijen voor knopen buiten de solution.
#
# Compatibel met IronPython 2.7.9.

import os
from collections import OrderedDict

from bridge_utils import (log, get_active_analysis, CONFIG_BRIDGE, tr,
                          run_name)


# POST_RELEVE_T leest INTITULE in een character(len=16) (rvtecn.F90 e.a.,
# code_aster v17.4.0): langere namen staan afgekapt in de .resu.
ASTER_INTITULE_MAX = 16


# ==========================================
# RESULTAATVELDEN-REGISTRY
#
# Mapping per INTITULE (eerste kolom in de .resu-tabel) naar:
#   {Code-Aster componentnaam: Mecway solution-variable naam}
#
# INTITULE moet overeenkomen met de INTITULE-waarde in de bijbehorende
# POST_RELEVE_T-aanroep in de gegenereerde .comm (zie bridge_to_aster.py
# _result_tables).
# ==========================================
RESULT_FIELD_SPECS = OrderedDict([
    # Rotaties (DRX/DRY/DRZ, radialen) bestaan alleen op knopen van balken,
    # schalen en DIS_TR-elementen; op volumeknopen staat '-' in de .resu en
    # blijft de waarde None (zoals in Mecway's eigen solution).
    ('displacements', OrderedDict([
        ('DX', 'displx'),
        ('DY', 'disply'),
        ('DZ', 'displz'),
        ('DRX', 'rotx'),
        ('DRY', 'roty'),
        ('DRZ', 'rotz'),
    ])),
    # stresses / vonmises: alleen 3D-elementen (SIGM_NOEU / SIEQ_NOEU,
    # globaal assenstelsel). Schalen en balken: zie STRUCT_FIELD_SPECS.
    ('stresses', OrderedDict([
        ('SIXX', 'stressxx'),
        ('SIYY', 'stressyy'),
        ('SIZZ', 'stresszz'),
        ('SIXY', 'stressxy'),
        ('SIYZ', 'stressyz'),
        ('SIXZ', 'stresszx'),
    ])),
    ('vonmises', OrderedDict([
        ('VMIS', 'vonmises'),
    ])),
    # velocities: alleen DYNA_NON_LINE (VITE); namen zoals Mecway ze voor
    # OpenRadioss-resultaten opslaat (velx/vely/velz, velmag).
    ('velocities', OrderedDict([
        ('DX', 'velx'),
        ('DY', 'vely'),
        ('DZ', 'velz'),
    ])),
    # accelerations: ACCE (dynamica; responsspectrum: maximale absolute
    # versnelling, bridge_spectrum.py). Alleen route 'liml'
    # (aster_results_export); Mecway kent geen eigen naam.
    ('accelerations', OrderedDict([
        ('DX', 'accelx'),
        ('DY', 'accely'),
        ('DZ', 'accelz'),
    ])),
    # REAC_NODA: DRX/DRY/DRZ zijn reactiemomenten (alleen op knopen met
    # rotatie-vrijheidsgraden). Mecway-namen zoals in Mecway's eigen
    # solution (reactionmomx/y/z, reactionmommag).
    ('reactions', OrderedDict([
        ('DX', 'reactionforcex'),
        ('DY', 'reactionforcey'),
        ('DZ', 'reactionforcez'),
        ('DRX', 'reactionmomx'),
        ('DRY', 'reactionmomy'),
        ('DRZ', 'reactionmomz'),
    ])),
    # ----------------------------------------------------------
    # PLASTIC STRAIN  (STAT_NON_LINE met VMIS_ISOT_TRAC)
    #
    # plastic_strain  (EPSP_NOEU) levert de plastische strain TENSOR
    # in dezelfde componenten als de spanningstensor:
    #   EPXX, EPYY, EPZZ, EPXY, EPYZ, EPXZ.
    #
    # plastic_strain_eq (VARI_NOEU)  levert de geaccumuleerde
    # equivalente plastische strain als interne variabele V1
    # (voor isotrope hardening). INTITULE in de .resu: 'plastic_strain_e'
    # (16 tekens); de parser koppelt die terug via _intitule_lookup().
    #
    # Mecway-namen: na een CCX-solve met *EL FILE PEEQ maakt Mecway 33
    # zelf 'equivalentplasticstrain' aan (veld "equivalent plastic
    # strain"); V1 gebruikt dezelfde naam. Een plastische-rektensor maakt
    # Mecway niet aan (ook niet met PE); 'plasticstrainxx' enz. zijn eigen
    # namen van de bridge. set_variable() maakt een niet-bestaande
    # variabele aan (API).
    #
    # BEPERKING: de tabelroute zet een tijdstip in de solution (statisch:
    # INST=t_res, het laatst bereikte). Voor dynamica schrijft
    # bridge_to_aster TOUT_ORDRE; die combinatie blokkeert
    # MecwayAsterBridgeMain (melding: kies route 'liml').
    # ----------------------------------------------------------
    ('plastic_strain', OrderedDict([
        ('EPXX', 'plasticstrainxx'),
        ('EPYY', 'plasticstrainyy'),
        ('EPZZ', 'plasticstrainzz'),
        ('EPXY', 'plasticstrainxy'),
        ('EPYZ', 'plasticstrainyz'),
        ('EPXZ', 'plasticstrainzx'),
    ])),
    ('plastic_strain_eq', OrderedDict([
        ('V1', 'equivalentplasticstrain'),
    ])),
    # Thermisch (analyse ther_3d, bridge_thermal.py): alleen via
    # result_route 'liml' (aster_results_export.py FIELD_TABLE; TEMP in
    # Celsius wordt daar Kelvin). Hier voor de veldkeuze in het startscherm.
    ('temperature', OrderedDict([
        ('TEMP', 'temperature'),
    ])),
    ('heat_flux', OrderedDict([
        ('FLUX', 'heatfluxx'),
        ('FLUY', 'heatfluxy'),
        ('FLUZ', 'heatfluxz'),
    ])),
    # Metallurgie (#ASTER-METALLURGIE, bridge_metallurgy.py; CALC_META):
    # alleen via result_route 'liml' (FIELD_TABLE groep "metallurgy"); met
    # #ASTER-METALLURGIE altijd mee (bridge_metallurgy.fields).
    ('metallurgy', OrderedDict([
        ('V1', 'ferrite'),
        ('V2', 'pearlite'),
        ('V3', 'bainite'),
        ('V4', 'martensite'),
        ('V5', 'austenite'),
        ('HV', 'hardness'),
    ])),
    # Foutschatter (errorestimate, errorestimaterel): geen entry hier; het
    # veld gaat alleen via result_route 'liml' (aster_results_export
    # FIELD_TABLE groep "error_estimate") en hangt aan de instelling
    # error_estimator, niet aan "fields" (docs/Foutschatter.md).
    # ----------------------------------------------------------
    # EXTRA VELDEN (alleen als ze gekozen zijn; aster_results_export
    # OPT_IN_GROUPS, bridge_to_aster._optional_fields). Mecway-namen
    # headless nagelopen in Mecway 34 (zie aster_results_export FIELD_TABLE
    # en _plan_derived).
    # strain: totale rek van volume-elementen (EPSI_NOEU; lineair, Mecway
    # lstrain*). Niet-lineair met grote verplaatsingen: Green-Lagrange
    # (EPSG_NOEU, STRUCT_FIELD_SPECS strain_gl). Schuif x 2 (_VALUE_SCALES).
    # Schalen (lstrain<ij>u/m/b) alleen via route 'liml'.
    ('strain', OrderedDict([
        ('EPXX', 'lstrainxx'),
        ('EPYY', 'lstrainyy'),
        ('EPZZ', 'lstrainzz'),
        ('EPXY', 'lstrainxy'),
        ('EPYZ', 'lstrainyz'),
        ('EPXZ', 'lstrainzx'),
    ])),
    # beam_forces: snedekrachten van balken (EFGE_NOEU, lokale assen).
    ('beam_forces', OrderedDict([
        ('N', 'tensileforce'),
        ('VY', 'sheary'),
        ('VZ', 'shearz'),
        ('MT', 'torsion'),
        ('MFY', 'bendingmomv'),
        ('MFZ', 'bendingmomw'),
    ])),
    # Alleen via route 'liml' (in de job berekend, geen tabel):
    #   shell_stresses: stress<ij>u1/m1/b1 (globale tensor boven/midden/
    #                   onder);
    #   shell_forces:   forceperlengthu/v/uv, momentu/v/uv, shearuw/vw;
    #   safety_factor:  factorofsafety (von Mises-faalcriterium);
    #   contact:        contactpressure (-LAGS_C) en contactstate.
    ('shell_stresses', OrderedDict()),
    ('shell_forces', OrderedDict()),
    ('safety_factor', OrderedDict()),
    ('contact', OrderedDict([
        ('LAGS_C', 'contactpressure'),
    ])),
])


# ==========================================
# EXTRA VELDEN VOOR SCHALEN EN BALKEN
#
# INTITULE -> (ouder-veld, {Code-Aster component: Mecway-variabele}).
# Geladen als het ouder-veld in analysis["fields"] staat.
#
#   vmis_shell_sup / vmis_shell_moy / vmis_shell_inf
#       Von Mises op boven-, midden- en ondervlak van DKT/COQUE_3D-schalen
#       (POST_CHAMP EXTR_COQUE, NIVE_COUCHE 'SUP'/'MOY'/'INF'). Mecway-namen
#       zoals Mecway ze zelf voor schalen schrijft (gezien in een door
#       Mecway opgeloste .liml): vonmisesu1 (boven), vonmisesm (midden),
#       vonmisesb (onder). Zoals bij Mecway staan schaalknopen NIET in
#       'vonmises' (dat veld is voor volume-elementen).
#       LET OP (niet geverifieerd): Code-Aster's 'SUP' ligt aan de kant
#       van de positieve elementnormaal (couche 1 = onderste laag in de
#       richting van de normaal). Dat Mecway's 'u' dezelfde kant is, is
#       aangenomen; de knoopvolgorde in .msh en .liml is wel gelijk.
#       Tensorcomponenten van schalen staan in Code-Aster's lokale schaal-
#       assenstelsel en worden niet geladen; Mecway's eigen schaal-
#       componenten (stressxxb1 enz.) worden leeggemaakt, zie
#       _MECWAY_SHELL_TENSOR_VARS.
#   beam_sixx
#       SIPM_ELNO van balken (RECTANGLE/CERCLE): kleinste en grootste
#       axiale spanning in de doorsnede (uit N, MFY, MFZ; zonder afschuiving
#       en torsie, dus geen von Mises). Per knoop over de aansluitende
#       elementen: minimum van SIXXMIN, maximum van SIXXMAX.
# ==========================================
STRUCT_FIELD_SPECS = OrderedDict([
    ('vmis_shell_sup', ('vonmises', OrderedDict([
        ('VMIS', 'vonmisesu1'),
    ]))),
    ('vmis_shell_moy', ('vonmises', OrderedDict([
        ('VMIS', 'vonmisesm'),
    ]))),
    ('vmis_shell_inf', ('vonmises', OrderedDict([
        ('VMIS', 'vonmisesb'),
    ]))),
    ('beam_sixx', ('stresses', OrderedDict([
        ('SIXXMIN', 'beamsixxmin'),
        ('SIXXMAX', 'beamsixxmax'),
    ]))),
    # Totale rek bij grote verplaatsingen (EPSG_NOEU, Green-Lagrange;
    # bridge_to_aster._strain_kind): Mecway's namen voor L30/D31.
    ('strain_gl', ('strain', OrderedDict([
        ('EPXX', 'greenlagrangestrainxx'),
        ('EPYY', 'greenlagrangestrainyy'),
        ('EPZZ', 'greenlagrangestrainzz'),
        ('EPXY', 'greenlagrangestrainxy'),
        ('EPYZ', 'greenlagrangestrainyz'),
        ('EPXZ', 'greenlagrangestrainzx'),
    ]))),
])

# Vaste factor per Mecway-variabele: Mecway's schuifrek is de technische
# hoekverdraaiing gamma = 2 eps (headless gemeten, Mecway 34), Code-Aster's
# EPXY/EPXZ/EPYZ zijn tensorcomponenten (zelfde tabel als
# aster_results_export.VALUE_SCALES).
_VALUE_SCALES = dict(
    (p + s, 2.0) for p in ("lstrain", "greenlagrangestrain")
    for s in ("xy", "yz", "zx"))

# Samenvoegen als een knoop meerdere rijen heeft (ELNO-velden: een rij per
# aansluitend element). Niet genoemd = laatste waarde.
_MERGE_MIN = frozenset(['beamsixxmin'])
_MERGE_MAX = frozenset(['beamsixxmax'])

# Schaal-spanningscomponenten uit Mecway's eigen solve (namen gezien in een
# door Mecway opgeloste .liml). In deze tabelroute levert de bridge ze niet
# (de route 'liml' wel: resultaatveld shell_stresses, in de job naar
# globale assen gedraaid); als ze bestaan worden ze leeggemaakt zodat er
# geen Mecway-waarden naast Code-Aster-waarden blijven staan.
_MECWAY_SHELL_TENSOR_VARS = tuple(
    "stress{0}{1}".format(c, lvl)
    for lvl in ("b1", "m1", "u1")
    for c in ("xx", "yy", "zz", "xy", "yz", "zx"))


def _intitule_lookup(names):
    """{INTITULE zoals in de .resu (max. 16 tekens): veldnaam}."""
    return dict((name[:ASTER_INTITULE_MAX], name) for name in names)


def _table_in_comm(work_dir, intitule):
    """True als study.comm een POST_RELEVE_T met deze INTITULE heeft (of
    de .comm niet te lezen is: dan liever de WARNING)."""
    try:
        with open(os.path.join(work_dir, run_name(".comm")), "r") as f:
            text = f.read()
    except (IOError, OSError):
        return True
    return "INTITULE='{0}'".format(intitule[:ASTER_INTITULE_MAX]) in text


# ==========================================
# CONTROLE: PAST DE MECWAY-SOLUTION BIJ HET MODEL?
# ==========================================
def check_solution_mesh(mw, solution, max_checked=2000):
    """
    Controleer of de knopen van de Mecway-solution overeenkomen met die van
    het huidige model.

    Waarom: solution.set_variable() schrijft alleen naar knopen die in de
    solution bestaan (lijstlengte = aantal knopen van de solution). Een
    solution van voor een modelwijziging heeft andere/minder knopen.

    Parameters
    ----------
    mw          : Mecway API-object (mw.all_nodes, mw.node).
    solution    : Mecway solution-object of None.
    max_checked : int - maximaal aantal knopen waarvan de positie wordt
                  vergeleken (gelijkmatig verdeeld; snelheid bij grote
                  modellen).

    Returns
    -------
    (bool, str) - (True, "") als het past; anders (False, reden).
    """
    if solution is None:
        return False, tr("Er is nog geen Mecway-solution.",
                         "There is no Mecway solution yet.")
    try:
        model_nodes = list(mw.all_nodes())
    except Exception as e:
        return False, tr("Knopen van het model niet leesbaar: {0}",
                         "Cannot read the nodes of the model: {0}").format(
            str(e))
    try:
        sol_nodes = list(solution.all_nodes())
    except Exception as e:
        return False, tr("Knopen van de solution niet leesbaar: {0}",
                         "Cannot read the nodes of the solution: {0}").format(
            str(e))

    if len(sol_nodes) != len(model_nodes) or \
            set(sol_nodes) != set(model_nodes):
        return False, tr(
            "De solution heeft {0} knopen, het model {1}. De "
            "solution is van voor de laatste modelwijziging.",
            "The solution has {0} nodes, the model {1}. The solution "
            "predates the last change to the model.").format(
                len(sol_nodes), len(model_nodes))

    step = max(1, len(model_nodes) // max_checked)
    for nid in model_nodes[::step]:
        try:
            a = mw.node(nid)
            b = solution.node(nid)
        except Exception as e:
            return False, tr(
                "Positie van knoop {0} niet leesbaar: {1}",
                "Cannot read the position of node {0}: {1}").format(
                    nid, str(e))
        size = abs(a.x) + abs(a.y) + abs(a.z)
        diff = abs(a.x - b.x) + abs(a.y - b.y) + abs(a.z - b.z)
        if diff > 1.0e-9 * (1.0 + size):
            return False, tr(
                "Knoop {0} ligt in de solution op een andere "
                "plek dan in het model. De solution is van voor "
                "de laatste modelwijziging.",
                "Node {0} is at a different position in the solution "
                "than in the model. The solution predates the last "
                "change to the model.").format(nid)
    return True, ""


# ==========================================
# VERGELIJKING MECWAY <-> CODE-ASTER
# ==========================================
def _compare_modes_with_mecway(solution, modes, nearest=False):
    """
    Vergelijk de frequenties/kniklastfactoren van Code-Aster (modes:
    bridge_results_liml.read_modes) met die van de Mecway-solve
    (solution.modes(), solution.frequency(m) / buckling_factor(m),
    API_reference Mecway). Alleen de waarden: de vormen hebben een
    willekeurig teken en zijn bij meervoudige modes niet uniek. Logt per
    mode beide waarden en het verschil.
    nearest: per Code-Aster-mode de Mecway-mode met de dichtstbijzijnde
    frequentie i.p.v. hetzelfde nummer (complexe akoestische modes: Mecway
    laat 0-Hz-modes willekeurig weg, manual v33 par. 6.9.2, dus de nummers
    lopen niet gelijk; modes met ~0 Hz worden dan niet vergeleken).
    """
    if nearest:
        _compare_nearest(solution, modes)
        return
    try:
        mw_modes = list(solution.modes() or [])
    except Exception as e:
        log(tr("WARNING: Mecway-modes niet leesbaar: {0}",
               "WARNING: Mecway modes not readable: {0}").format(e))
        return
    if not mw_modes:
        log(tr("WARNING: De Mecway-solution heeft geen modes; geen "
               "vergelijking.",
               "WARNING: The Mecway solution has no modes; no "
               "comparison."))
        return
    for mid, kind, value in modes:
        if mid not in mw_modes:
            continue
        try:
            mw_value = (solution.buckling_factor(mid)
                        if kind == "bucklingfactor"
                        else solution.frequency(mid))
        except Exception:
            mw_value = None
        if mw_value is None:
            continue
        rel = (value - mw_value) / abs(mw_value) if mw_value else 0.0
        # %-opmaak: format() geeft in IronPython een komma (landinstelling)
        log("INFO: Vergelijking mode {0}: Mecway {1}, Code-Aster {2} "
            "({3}%).".format(mid, "%.6g" % mw_value, "%.6g" % value,
                             "%+.2f" % (100.0 * rel)))


def _compare_nearest(solution, modes):
    """Zie _compare_modes_with_mecway (nearest=True)."""
    try:
        mw = [(m, solution.frequency(m)) for m in (solution.modes() or [])]
    except Exception as e:
        log(tr("WARNING: Mecway-modes niet leesbaar: {0}",
               "WARNING: Mecway modes not readable: {0}").format(e))
        return
    mw = [(m, f) for m, f in mw if f is not None and abs(f) > 1.0e-3]
    if not mw:
        log(tr("WARNING: De Mecway-solution heeft geen modes; geen "
               "vergelijking.",
               "WARNING: The Mecway solution has no modes; no "
               "comparison."))
        return
    for mid, _kind, value in modes:
        if abs(value) <= 1.0e-3:
            continue
        m, f = min(mw, key=lambda t: abs(t[1] - value))
        log("INFO: Vergelijking mode {0}: Mecway mode {1} {2}, Code-Aster "
            "{3} ({4}%).".format(mid, m, "%.6g" % f, "%.6g" % value,
                                 "%+.2f" % (100.0 * (value - f) / abs(f))))


def _compare_with_mecway(solution, arrays, names, work_dir):
    """
    Vergelijk Code-Aster-waarden met die van de Mecway-solve, vóór ze
    worden overschreven. Alleen zinvol direct na mw.solve() ("Eerst
    Mecway-solve ter controle"): dan bevat de solution Mecway's eigen
    resultaat op dezelfde mesh.

    Schrijft <model>_<run_id>_vergelijking.csv (knoop, variabele, mecway,
    aster) in de werkmap en logt per variabele het grootste verschil.
    """
    rows = []
    # Met tijdstappen (transient, dynamica) geeft node_value() zonder
    # time_step niets (API_reference: "Time step number if there are time
    # steps in the solution"); vergelijk dan de laatste tijdstap van Mecway
    # met de laatste van Code-Aster.
    step = None
    try:
        steps = list(solution.time_steps() or [])
        if steps:
            step = steps[-1]
            log("INFO: Vergelijking op de laatste tijdstap van Mecway (t = "
                "{0} s).".format(solution.time(step)))
    except Exception:
        step = None
    for name in names:
        aster = arrays.get(name)
        if aster is None:
            continue
        max_m = max_a = max_d = 0.0
        node_d = None
        for i, a in enumerate(aster):
            if a is None:
                continue
            try:
                m = solution.node_value(name, i + 1, step)
            except Exception:
                m = None
            if m is None:
                continue
            rows.append("{0},{1},{2!r},{3!r}".format(i + 1, name, m, a))
            max_m = max(max_m, abs(m))
            max_a = max(max_a, abs(a))
            if abs(m - a) > max_d:
                max_d, node_d = abs(m - a), i + 1
        if node_d is None and max_m == 0.0:
            continue
        rel = max_d / max_m if max_m > 0.0 else 0.0
        log("INFO: Vergelijking {0}: max|Mecway|={1}, max|Code-Aster|="
            "{2}, max verschil={3} ({4:.1%} van max|Mecway|) in knoop "
            "{5}.".format(name, max_m, max_a, max_d, rel, node_d))
    if rows:
        path = os.path.join(work_dir, run_name("_vergelijking.csv"))
        try:
            f = open(path, "w")
            try:
                f.write("knoop,variabele,mecway,aster\n")
                f.write("\n".join(rows) + "\n")
            finally:
                f.close()
        except Exception as e:
            log(tr("WARNING: {0} niet geschreven: {1}",
                   "WARNING: {0} not written: {1}").format(path, str(e)))


# ==========================================
# RESULTATEN INLADEN IN MECWAY
# ==========================================
def AsterToMecway_results(work_dir, resu_name, mw, solution):
    """
    Lees het Code-Aster .resu-bestand en laad de resultaten in Mecway.

    Parameters
    ----------
    work_dir  : str  - Werkmap waarin het .resu-bestand staat.
    resu_name : str  - Bestandsnaam van het .resu-bestand.
    mw        : obj  - Mecway API-object (mw.set_solution_active, mw.display).
    solution  : obj  - Mecway active-solution object (solution.set_variable,
                       solution.all_nodes, solution.node_value).

    Returns
    -------
    bool - True als minimaal een veld in Mecway is geladen.

    Bijwerkingen
    -----------
    - Roept solution.set_variable() voor elk veld in de actieve analyse
      (plus de bijbehorende velden uit STRUCT_FIELD_SPECS).
    - Berekent afgeleide velden 'displmag', 'reactionforcemag' en
      'reactionmommag' uit de x/y/z-componenten via Pythagoras.
    - Maakt Mecway's eigen schaal-spanningscomponenten leeg als er
      schaalresultaten zijn (zie _MECWAY_SHELL_TENSOR_VARS).
    - Activeert de solution-weergave als minimaal een veld geladen is.
    """
    log("--- Loading Results ---")
    resu_path = os.path.join(work_dir, resu_name)

    if not os.path.exists(resu_path):
        log(tr("ERROR: Resultaatbestand niet gevonden: '{0}'.",
               "ERROR: Result file not found: '{0}'.").format(resu_path))
        return False
    if os.path.getsize(resu_path) == 0:
        log(tr("ERROR: Resultaatbestand is leeg: '{0}'. Code-Aster is "
               "waarschijnlijk vastgelopen; zie study.mess.",
               "ERROR: Result file is empty: '{0}'. Code-Aster probably "
               "crashed; see study.mess.").format(resu_path))
        return False

    try:
        analysis = get_active_analysis()
    except KeyError as e:
        log("ERROR: {0}".format(str(e)))
        return False

    # Selecteer alleen de velden uit RESULT_FIELD_SPECS die in de actieve
    # analyse-config zijn opgenomen, plus de schaal-/balkvelden van die
    # ouders.
    active_specs = OrderedDict()
    for field_name in analysis.get("fields", []):
        if field_name in RESULT_FIELD_SPECS:
            active_specs[field_name] = RESULT_FIELD_SPECS[field_name]
        else:
            log(tr("WARNING: Veld '{0}' heeft geen entry in "
                   "RESULT_FIELD_SPECS; wordt overgeslagen.",
                   "WARNING: Field '{0}' has no entry in "
                   "RESULT_FIELD_SPECS; skipped.").format(field_name))
    struct_specs = OrderedDict()
    for intitule, (parent, comp_map) in STRUCT_FIELD_SPECS.items():
        if parent in active_specs:
            struct_specs[intitule] = comp_map

    if not active_specs:
        log(tr("ERROR: Geen geldige velden in active_specs. Niets te laden.",
               "ERROR: No valid fields in active_specs. Nothing to load."))
        return False

    all_specs = OrderedDict(active_specs)
    all_specs.update(struct_specs)
    lookup = _intitule_lookup(all_specs.keys())

    try:
        all_nodes = list(solution.all_nodes())
        n_nodes   = max(all_nodes)
    except Exception:
        log(tr("ERROR: Geen geldig solution-object.",
               "ERROR: No valid solution object."))
        return False
    if n_nodes != len(all_nodes):
        log(tr("WARNING: Knoopnummers van de solution zijn niet "
               "aaneengesloten ({0} knopen, hoogste nummer {1}).",
               "WARNING: The node numbers of the solution are not "
               "contiguous ({0} nodes, highest number {1}).").format(
                   len(all_nodes), n_nodes))

    # Initialiseer per veld een array van lengte n_nodes met None-waarden.
    # Knopen zonder waarde in het .resu blijven None; Mecway gaat hier
    # zelf correct mee om in set_variable().
    arrays = {}
    for comp_map in all_specs.values():
        for mecway_name in comp_map.values():
            arrays[mecway_name] = [None] * n_nodes

    if 'displacements' in active_specs:
        arrays['displmag'] = [None] * n_nodes
    if 'reactions' in active_specs:
        arrays['reactionforcemag'] = [None] * n_nodes
        arrays['reactionmommag'] = [None] * n_nodes

    # Unieke knopen per tabel (ELNO-tabellen hebben meerdere rijen per
    # knoop).
    seen = OrderedDict((intitule, set()) for intitule in all_specs)
    outside = OrderedDict()   # intitule -> aantal rijen buiten de solution
    column_index = {}

    # --------------------------------------------------
    # PARSE .resu-BESTAND
    #
    # POST_RELEVE_T schrijft tabellen met een kop-regel van de vorm:
    #   INTITULE  NOEUD  RESU  NOM_CHAM  NUME_ORDRE  ...  DX  DY  DZ ...
    # gevolgd door datarijen waar de eerste kolom de INTITULE-waarde is.
    # ELNO-velden (beam_sixx) hebben ook een kolom MAILLE en dus meerdere
    # rijen per knoop.
    #
    # Meerdere tabellen worden achter elkaar in hetzelfde bestand
    # geschreven; bij elke nieuwe kop-regel updaten we column_index.
    # Een '-' in een kolom (component bestaat niet op die knoop, bijv.
    # DRX op een volumeknoop) wordt overgeslagen.
    # --------------------------------------------------
    try:
        with open(resu_path, 'r') as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                parts = stripped.split()

                if parts[0] == 'INTITULE':
                    column_index = dict(
                        (name, i) for i, name in enumerate(parts))
                    continue

                intitule = lookup.get(parts[0])
                if intitule is None:
                    continue

                noeud_col = column_index.get('NOEUD')
                if noeud_col is None or noeud_col >= len(parts):
                    continue
                try:
                    node_id = int(parts[noeud_col])
                except ValueError:
                    continue

                idx = node_id - 1
                if not (0 <= idx < n_nodes):
                    outside[intitule] = outside.get(intitule, 0) + 1
                    continue

                comp_map = all_specs[intitule]
                row_ok   = False
                for aster_cmp, mecway_name in comp_map.items():
                    col = column_index.get(aster_cmp)
                    if col is None or col >= len(parts):
                        continue
                    try:
                        value = float(parts[col]) * _VALUE_SCALES.get(
                            mecway_name, 1.0)
                    except ValueError:
                        continue
                    old = arrays[mecway_name][idx]
                    if old is not None and mecway_name in _MERGE_MIN:
                        value = min(old, value)
                    elif old is not None and mecway_name in _MERGE_MAX:
                        value = max(old, value)
                    arrays[mecway_name][idx] = value
                    row_ok = True
                if row_ok:
                    seen[intitule].add(idx)

    except Exception as e:
        log(tr("ERROR: Fout bij lezen .resu-bestand: {0}",
               "ERROR: Error while reading the .resu file: {0}").format(
                   str(e)))
        return False

    counts = OrderedDict((k, len(v)) for k, v in seen.items())

    for intitule, n in outside.items():
        log(tr("WARNING: '{0}': {1} rij(en) voor knopen die niet in de "
               "Mecway-solution bestaan (solution heeft {2} knopen). De "
               "solution is waarschijnlijk van voor de laatste "
               "modelwijziging; los het model eerst op in Mecway "
               "(startscherm: 'Eerst Mecway-solve ter controle').",
               "WARNING: '{0}': {1} row(s) for nodes that do not exist in "
               "the Mecway solution (the solution has {2} nodes). The "
               "solution probably predates the last change to the model; "
               "solve the model in Mecway first (start screen: 'Mecway "
               "solve first as a check').").format(
                   intitule, n, n_nodes))

    # --------------------------------------------------
    # AFGELEIDE GROOTHEDEN (magnitudes)
    # --------------------------------------------------
    if 'displacements' in active_specs and counts['displacements'] > 0:
        dx, dy, dz = arrays['displx'], arrays['disply'], arrays['displz']
        for i in range(n_nodes):
            if dx[i] is not None and dy[i] is not None and dz[i] is not None:
                arrays['displmag'][i] = (
                    dx[i]**2 + dy[i]**2 + dz[i]**2) ** 0.5

    if 'reactions' in active_specs and counts['reactions'] > 0:
        fx, fy, fz = (arrays['reactionforcex'],
                      arrays['reactionforcey'],
                      arrays['reactionforcez'])
        for i in range(n_nodes):
            if fx[i] is not None and fy[i] is not None and fz[i] is not None:
                arrays['reactionforcemag'][i] = (
                    fx[i]**2 + fy[i]**2 + fz[i]**2) ** 0.5
        mx, my, mz = (arrays['reactionmomx'],
                      arrays['reactionmomy'],
                      arrays['reactionmomz'])
        for i in range(n_nodes):
            if mx[i] is not None and my[i] is not None and mz[i] is not None:
                arrays['reactionmommag'][i] = (
                    mx[i]**2 + my[i]**2 + mz[i]**2) ** 0.5

    # --------------------------------------------------
    # VERGELIJKING MET DE MECWAY-SOLVE (alleen na "Eerst Mecway-solve")
    # --------------------------------------------------
    if CONFIG_BRIDGE.get("mecway_solve_first", False):
        compare_names = []
        # Spanningen ook: met 3D_SI klopten de verplaatsingen maar was de
        # buigspanning nul. Knoopspanningen zijn bij Mecway en Code-Aster
        # anders geextrapoleerd, dus daar is een verschil normaal.
        for intitule in ('displacements', 'reactions', 'stresses',
                         'vonmises', 'plastic_strain_eq'):
            if intitule in active_specs and counts[intitule] > 0:
                compare_names += list(all_specs[intitule].values())
        _compare_with_mecway(solution, arrays, compare_names, work_dir)

    # --------------------------------------------------
    # INJECTEER IN MECWAY
    # --------------------------------------------------
    any_loaded = False
    for intitule, comp_map in all_specs.items():
        if counts[intitule] > 0:
            # Componenten zonder enige waarde (bijv. DRX in een model met
            # alleen volume-elementen) worden niet aangemaakt.
            names = [n for n in comp_map.values()
                     if any(v is not None for v in arrays[n])]
            for mecway_name in names:
                solution.set_variable(
                    mecway_name, arrays[mecway_name],
                    time_step=None, mode=None)
            log("SUCCESS: '{0}' geladen voor {1} knopen ({2}).".format(
                intitule, counts[intitule], ", ".join(names)))
            any_loaded = True
        elif intitule in active_specs and not _table_in_comm(
                work_dir, intitule):
            # De .comm vraagt deze tabel niet (bv. plastic_strain_eq bij
            # een elastisch model of kinematische versteviging, zie
            # bridge_to_aster._result_tables): geen fout.
            log("INFO: '{0}' niet berekend in deze analyse.".format(
                intitule))
        elif intitule in active_specs:
            log(tr("WARNING: Geen data gevonden voor '{0}' in '{1}'. "
                   "Controleer .comm-template en .mess-bestand.",
                   "WARNING: No data found for '{0}' in '{1}'. "
                   "Check the .comm template and the .mess file.").format(
                       intitule, resu_name))

    if 'displacements' in active_specs and counts['displacements'] > 0:
        solution.set_variable('displmag', arrays['displmag'])
        log("SUCCESS: 'displmag' berekend uit displx/y/z.")

    if 'reactions' in active_specs and counts['reactions'] > 0:
        solution.set_variable('reactionforcemag', arrays['reactionforcemag'])
        log("SUCCESS: 'reactionforcemag' berekend uit reactionforcex/y/z.")
        if any(v is not None for v in arrays['reactionmommag']):
            solution.set_variable('reactionmommag', arrays['reactionmommag'])
            log("SUCCESS: 'reactionmommag' berekend uit reactionmomx/y/z.")

    # --------------------------------------------------
    # VEROUDERDE MECWAY-SCHAALVELDEN LEEGMAKEN
    # Alleen als er schaalresultaten zijn geladen en de variabele op een
    # schaalknoop een waarde heeft (= bestaat nog uit Mecway's eigen solve).
    # Dat set_variable een lijst met alleen None accepteert, staat in de API
    # ("It can contain None for nodes with no value"); hoe Mecway een
    # volledig lege variabele toont, is niet gedocumenteerd.
    # --------------------------------------------------
    shell_idx = set()
    for intitule in ('vmis_shell_sup', 'vmis_shell_moy', 'vmis_shell_inf'):
        if intitule in seen:
            shell_idx.update(seen[intitule])
    if shell_idx:
        probe = min(shell_idx) + 1
        cleared = []
        for name in _MECWAY_SHELL_TENSOR_VARS:
            try:
                if solution.node_value(name, probe) is None:
                    continue
                solution.set_variable(name, [None] * n_nodes)
                cleared.append(name)
            except Exception as e:
                log(tr("WARNING: Mecway-variabele '{0}' niet leeg te "
                       "maken: {1}",
                       "WARNING: Cannot clear Mecway variable '{0}': "
                       "{1}").format(name, str(e)))
        if cleared:
            log("INFO: Mecway-schaalcomponenten leeggemaakt (geen Code-Aster-"
                "equivalent in globaal XYZ): {0}".format(", ".join(cleared)))

    if any_loaded:
        mw.set_solution_active()
        mw.display()
    else:
        log(tr("WARNING: Geen enkel veld kon geladen worden uit '{0}'. "
               "Controleer het .mess-bestand op Code-Aster-fouten.",
               "WARNING: No field could be loaded from '{0}'. "
               "Check the .mess file for Code-Aster errors.").format(
                   resu_name))
    return any_loaded
