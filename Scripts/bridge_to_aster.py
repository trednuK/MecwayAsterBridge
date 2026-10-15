# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_to_aster.py
# Verantwoordelijkheid: genereert study.comm en study.export op basis van
# model_data (output van bridge_from_liml.extract_aster_data_from_liml(),
# daarna afgestemd op de mesh door bridge_mesh.write_mesh()).
#
# Architectuur:
#   - SOLVER_BUILDERS_ASTER koppelt elk solver-keyword aan een builder-functie.
#     Nieuw analysetype = nieuwe builder + entry in SOLVER_BUILDERS_ASTER +
#     nieuwe template (pad in CONFIG_BRIDGE["analyses"][...]["template"]).
#   - generate_AsterSolver_files() is de publieke dispatcher; selecteert de
#     builder op basis van "solver_command" van de actieve analyse
#     (get_active_analysis()).
#
# Template-placeholders gegenereerd door _build_lin_static():
#   {defigroup_block}      DEFI_GROUP (+ CREA_MAILLAGE / MODI_MAILLAGE)
#   {model_block}          AFFE_MODELE (per elset, gemengde dimensies)
#   {cara_elem_block}      AFFE_CARA_ELEM (balk- / schaal- / veer-secties)
#   {materials_block}      DEFI_MATERIAU per materiaal (incl. RHO)
#   {fieldmat_block}       AFFE_MATERIAU toewijzing
#   {loads_block}          AFFE_CHAR_MECA met BC's, belastingen en couplings
#   {cara_elem_ref}        "    CARA_ELEM=cara,\n" of "" in MECA_STATIQUE
#   {solveur_ref}          "    SOLVEUR=_F(METHODE=.., ..),\n    INFO=2,\n"
#                          (_build_lin_solveur_ref, instelling lin_solver)
#   {calc_champ_block}     CALC_CHAMP (element-type-afhankelijk)
#   {postreleve_block}     POST_RELEVE_T tabellen
#   {impr_table_block}     IMPR_TABLE aanroepen
#   {impr_resu_block}      IMPR_RESU MED (alleen met "med_export")
#
# Compatibel met IronPython 2.7.9.

import io
import math
import os
import re

import bridge_custom
import bridge_failure
import bridge_fracture
import bridge_xfem
import bridge_fatigue
import bridge_mesh
import bridge_modal_damping
from collections import OrderedDict
from bridge_results_liml import RESULTS_SUFFIX
from bridge_utils import (log, tr, CONFIG_BRIDGE, get_active_analysis,
                          run_name, template_path)


# ==========================================
# HULPFUNCTIES: TEMPLATE-BLOKKEN BOUWEN
# Elke functie neemt model_data en retourneert een kant-en-klare string
# die als placeholder in de .comm-template wordt ingevuld.
# ==========================================

def _has_cara(model_data):
    """True als AFFE_CARA_ELEM nodig is (balken, schalen, veren, POI1,
    discreten, kabels)."""
    return any(bool(model_data.get(k)) for k in (
        "beam_sections", "shell_sections", "spring_sections", "poi1_groups",
        "discretes", "discrete_sections", "cable_sections"))


def _build_solveur_ref(analysis):
    """
    SOLVEUR-regel voor MECA_STATIQUE / STAT_NON_LINE.

    NPREC (catalogus c_solveur.py v17.4.0: integer, default 8) is het
    aantal decimalen dat bij de factorisatie verloren mag gaan voordat
    Code-Aster de matrix singulier verklaart; -1 schakelt die controle uit.
    RESI_RELA (default 1e-6) controleert daarna nog steeds het residu van
    de oplossing.
    """
    nprec = analysis.get("solver_nprec", 8)
    return "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),\n".format(int(nprec))


# Lineaire oplossers voor MECA_STATIQUE (instelling "lin_solver").
#   MUMPS : direct (catalogus c_solveur.py v17.4.0: default voor 'LIN').
#   GCPC  : geconjugeerde gradient met onvolledige LDLT als
#           voorconditionering (PRE_COND='LDLT_INC', default van GCPC);
#           RESI_RELA = ||r|| / ||f|| (U4.50.01 par. 3.6, default 1e-6),
#           NMAX_ITER 0 = neq / 2.
# PETSC staat in de catalogus, maar de Windows-versie van Code-Aster 17.4
# is sequentieel: <EXCEPTION> <FERMETUR_10> "Le solveur PETSc n'est pas
# installé" (gezien in een testrun; U4.50.01 par. 3.7: PETSC alleen in de
# parallelle versie). Daarom niet aangeboden.
LIN_SOLVERS = ("MUMPS", "GCPC")


def _build_lin_solveur_ref(analysis):
    """
    SOLVEUR- en INFO-regels voor MECA_STATIQUE (alleen lin_static_3d; de
    andere analyses gebruiken _build_solveur_ref ongewijzigd).

    INFO=2 (catalogus meca_statique.py: into (1, 2)) zet de statistiek van
    de lineaire oplosser in de .mess: matrixgrootte, MUMPS-fasen
    (analyse/factorisatie/oplossen) met tijden, geheugen, pivots, het
    residu voor/na iteratieve verfijning, de foutgrens en het
    conditiegetal (MUMPS ICNTL(4)=2), of bij GCPC het residu per
    iteratie (gcpc.F90: alleen als het met een factor 10 gedaald is,
    paraaf=0.1). Het convergentiescherm leest dat
    (bridge_convergence.LinearSolve). De hoeveelheid tekst hangt niet af
    van de modelgrootte (gezien: ~15 kB extra, ook bij 270 000
    vergelijkingen).

    RESI_RELA (instelling "lin_solver_resi", catalogus-default 1e-6 bij
    MECA_STATIQUE):
      MUMPS : grens voor de geschatte relatieve fout op de oplossing
              (conditiegetal x 'backward error', RINFOG(9)); is die groter,
              dan stopt Code-Aster (U4.50.01 par. 3.5.3, U2.08.03 par.
              7.2.1).
      GCPC  : convergentiecriterium ||r|| / ||f|| (U4.50.01 par. 3.6).
    """
    solver = "{0}".format(analysis.get("lin_solver", "MUMPS")).upper()
    # %-opmaak: altijd een punt; repr() gaf in IronPython
    # 9.9999999999999995e-07 voor 1e-6.
    resi = "%.10g" % float(analysis.get("lin_solver_resi", 1.0e-6))
    if solver == "GCPC":
        line = ("    SOLVEUR=_F(METHODE='GCPC', PRE_COND='LDLT_INC', "
                "RESI_RELA={0}),\n".format(resi))
    else:
        if solver != "MUMPS":
            log(tr("WARNING: Onbekende lineaire oplosser '{0}' (lin_solver); "
                   "MUMPS gebruikt.",
                   "WARNING: Unknown linear solver '{0}' (lin_solver); "
                   "MUMPS used.").format(solver))
        line = ("    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}, "
                "RESI_RELA={1}),\n".format(
                    int(analysis.get("solver_nprec", 8)), resi))
    return line + "    INFO=2,\n"


def _read_template(path):
    """
    Template-tekst als unicode (de templates zijn ASCII/UTF-8). path: de
    waarde uit CONFIG_BRIDGE (bestandsnaam in de Scripts-map of absoluut
    pad, bridge_utils.template_path).
    """
    full = template_path(path)
    if not full or not os.path.isfile(full):
        raise IOError(tr("template '{0}' niet gevonden (gezocht: {1})",
                         "template '{0}' not found (looked for: {1})").format(
            path, full))
    f = io.open(full, encoding="utf-8")
    try:
        return f.read()
    finally:
        f.close()


# De jobscripts (aster_*.py, Python 3 in de job) kennen CONFIG_BRIDGE niet;
# ze lezen de taal van hun WAARSCHUWING/FOUT-regels uit deze
# omgevingsvariabele (aster_results_export.tr; zelfde naam als
# aster_results_export.LANGUAGE_ENV).
JOB_LANGUAGE_ENV = "BRIDGE_LANGUAGE"
_DEBUT_RE = re.compile(r"^DEBUT\s*\(", re.M)


def _language_lines():
    """Regels voor study.comm die de taal van de run aan de jobscripts
    doorgeven (os.environ in het Code-Aster-proces)."""
    lang = "nl" if CONFIG_BRIDGE.get("language", "en") == "nl" else "en"
    return (u"# Taal van de meldingen van de jobscripts (aster_*.py)\n"
            u"import os as _bridge_os\n"
            u"_bridge_os.environ['{0}'] = '{1}'\n".format(
                JOB_LANGUAGE_ENV, lang))


def _with_language(text):
    """text met _language_lines voor de eerste DEBUT-regel (alle templates
    hebben er een op een eigen regel), of bovenaan zonder DEBUT."""
    m = _DEBUT_RE.search(text)
    pos = m.start() if m else 0
    return text[:pos] + _language_lines() + text[pos:]


def _write_comm(path, text):
    """
    Schrijf de .comm als UTF-8. Code-Aster leest de .comm als UTF-8; een
    niet-UTF-8-byte geeft ook in commentaar een SyntaxError (gezien: 'Ålu'
    in cp1252). open(path, 'w') schreef in IronPython de systeemcodering
    ('ü' als de byte 0xFC), bijv. uit #ASTER-regels of een pad met een
    umlaut. io.open vraagt unicode: in IronPython is str al unicode.
    Voor DEBUT komt de taal van de meldingen van de jobscripts erbij
    (_language_lines).
    """
    text = _with_language(text)
    f = io.open(path, "w", encoding="utf-8")
    try:
        f.write(text)
    finally:
        f.close()


def _py_str(text):
    """
    Python-stringliteral voor een pad in de .comm: backslash en apostrof
    ge-escaped (een r'...'-literal brak op een pad met een apostrof, bijv.
    "D:\\Jan's modellen"). Niet-ASCII-tekens blijven staan; de .comm is
    UTF-8 (_write_comm).
    """
    return "'{0}'".format(text.replace("\\", "\\\\").replace("'", "\\'"))


# Mecway-voorwaarden die verplaatsingen vastleggen (DDL_IMPO / LIAISON_*).
_KINEMATIC_BCS = frozenset(["fixed", "displacement", "noderotation",
                            "pinnedsupport", "frictionless", "velocity",
                            "symmetry", "compressiononly"])
_LINEAR_SOLIDS = frozenset(["hex8", "tet4", "wedge6", "pyr5"])
_QUADRATIC_SOLIDS = frozenset(["hex20", "tet10", "wedge15", "pyr13"])


def _resolve_line_quad(model_data):
    """
    Beslis eenmalig (vóór de builder) welke lineaire cellen Code-Aster
    kwadratisch maakt (CREA_MAILLAGE LINE_QUAD, catalogus crea_maillage.py
    v17.4.0). Zet model_data["line_quad"] op None, "TOUT" of een lijst
    groepen; _line_quad_block schrijft het.

    - elem_hex8 = "LINE_QUAD" (KNOWN_BUGS 1): hex8 rekent in Code-Aster
      zonder incompatibele modes en buigt te stijf (uitkragende balk, 1
      element dik: 0,123 mm tegen 0,189 mm in Mecway). TOUT: alle cellen,
      ook huidvlakken. Alleen als er verder niets lineair blijft dat knopen
      deelt (geen balken, veren, POI1, DKT-schalen): anders sluiten die
      niet aan op de middenknopen.
    - elem_shell = "COQUE_3D" (KNOWN_BUGS 2): lineaire schalen worden
      QUAD8/TRIA6 en daarna QUAD9/TRIA7 (shell_upgrades met "LINE_QUAD").
      Alleen de schaalgroepen, tenzij TOUT al geldt; delen ze knopen met
      elementen die lineair blijven, dan DKT (niet-conform mesh).
    De extra middenknopen komen na de Mecway-knopen; aster_results_export
    laat ze weg (hun reacties gaan naar de hoekknopen, _reaction_lumping)
    en koppelt elementwaarden via de hoekknopen.
    """
    model_data["line_quad"] = None
    elements = model_data.get("mesh_elements", [])
    renames = model_data.get("group_renames", {})
    shapes = set(e[1] for e in elements)
    dims = model_data.get("elset_dims", {})
    upgrades = model_data.get("shell_upgrades", {})
    shell_lq = [g for g, opts in upgrades.items() if "LINE_QUAD" in opts]
    choice = model_data.get("hex8_choice", "3D")

    # Verlijmd contact (LIAISON_MAIL) met de master op COQUE_3D: Code-Aster
    # interpoleert met de QUAD9/TRIA7-vormfuncties en legt dan ook DX op de
    # middenknoop, die bij COQUE_3D alleen rotaties heeft: <EXCEPTION>
    # CHARGES2_31 (Code-Aster 17.4, QA-model M15b_bonded_coque). Die
    # schalen blijven DKT (vóór de keuze TOUT, zodat ze daar als lineair
    # blijvend meetellen).
    elem_elset = model_data.get("_elem_elset", {})
    faces = model_data.get("group_face_list", {})
    bonded = set()
    for b in model_data.get("bonded", []):
        for f in faces.get(b.get("master"), []):
            if f.get("kind") == "shellface":
                bonded.add(elem_elset.get(f["eid"]))
    bonded &= set(shell_lq)
    if bonded:
        log(tr("WARNING: COQUE_3D niet toegepast op schalen {0}: ze zijn "
               "master van verlijmd contact, en LIAISON_MAIL kan niet op "
               "COQUE_3D (CHARGES2_31: de middenknoop heeft geen DX). DKT "
               "gebruikt.",
               "WARNING: COQUE_3D not applied to shells {0}: they are the "
               "master of bonded contact, and LIAISON_MAIL cannot work on "
               "COQUE_3D (CHARGES2_31: the centre node has no DX). DKT "
               "used.").format(
                   ", ".join(sorted(bonded))))
        for g in bonded:
            model_data["elset_modelisations"][g] = "DKT"
            upgrades.pop(g, None)
        shell_lq = [g for g in shell_lq if g not in bonded]
        edges = model_data.get("edge_groups", {})
        for sel in list(edges):
            parent = bridge_mesh._shell_edge_parent(model_data, sel)
            if parent:
                edges[sel] = parent

    tout = False
    if choice == "LINE_QUAD":
        problems = []
        others = sorted(e for e, d in dims.items()
                        if d != "3D" and e not in shell_lq)
        if others:
            problems.append(tr("elsets die lineair blijven ({0})",
                               "elsets that stay linear ({0})").format(
                ", ".join(others)))
        if shapes & _QUADRATIC_SOLIDS:
            problems.append(tr("al kwadratische volume-elementen",
                               "already quadratic solid elements"))
        if not shapes & _LINEAR_SOLIDS:
            problems.append(tr("geen lineaire volume-elementen",
                               "no linear solid elements"))
        if problems:
            log(tr("WARNING: Keuze LINE_QUAD (kwadratische volume-elementen) "
                   "niet toegepast: {0}. De elementen blijven lineair; maak "
                   "in Mecway kwadratische elementen als buiging belangrijk "
                   "is.",
                   "WARNING: Choice LINE_QUAD (quadratic solid elements) "
                   "not applied: {0}. The elements stay linear; create "
                   "quadratic elements in Mecway if bending matters.")
                .format("; ".join(problems)))
        else:
            tout = True
    elif "hex8" in shapes and choice == "3D":
        log(tr("WARNING: Hex8 rekent in Code-Aster stijver dan in Mecway "
               "(geen incompatibele modes): bij buiging met weinig "
               "elementen over de dikte zijn verplaatsingen tot ~35% te "
               "klein (KNOWN_BUGS 1). Kies op de pagina Elementen "
               "'LINE_QUAD' of gebruik kwadratische elementen in Mecway.",
               "WARNING: Hex8 is stiffer in Code-Aster than in Mecway "
               "(no incompatible modes): in bending with few elements "
               "through the thickness, displacements are up to ~35% too "
               "small (KNOWN_BUGS 1). Choose 'LINE_QUAD' on the Elements "
               "tab or use quadratic elements in Mecway."))

    if shell_lq and not tout:
        lq = set(shell_lq)
        shell_nodes, other_nodes = set(), set()
        for elem in elements:
            group = renames.get(elem[3], elem[3])
            if group in lq:
                shell_nodes.update(elem[2])
            elif group in dims:
                other_nodes.update(elem[2])
        if shell_nodes & other_nodes:
            log(tr("WARNING: COQUE_3D voor lineaire schalen niet toegepast: "
                   "{0} delen knopen met elementen die lineair blijven "
                   "(niet-conform mesh). DKT gebruikt; kies ook LINE_QUAD "
                   "voor de volume-elementen of maak de schalen in Mecway "
                   "kwadratisch.",
                   "WARNING: COQUE_3D for linear shells not applied: "
                   "{0} share nodes with elements that stay linear "
                   "(non-conforming mesh). DKT used; also choose LINE_QUAD "
                   "for the solid elements or make the shells quadratic "
                   "in Mecway.").format(", ".join(sorted(lq))))
            for g in shell_lq:
                model_data["elset_modelisations"][g] = "DKT"
                upgrades.pop(g, None)
            shell_lq = []
            # Schaalranden in het model (FORCE_ARETE, bridge_mesh) kregen de
            # modelisatie van de schaal al mee: bijwerken, anders COQUE_3D
            # op SEG2 -> <EXCEPTION> MODELISA6_96 (Code-Aster 17.4).
            edges = model_data.get("edge_groups", {})
            for sel in list(edges):
                parent = bridge_mesh._shell_edge_parent(model_data, sel)
                if parent:
                    edges[sel] = parent

    # Alleen schalen en die worden allemaal kwadratisch: TOUT, dan gaan ook
    # rand- en vlakgroepen (bv. een ingeklemde rand als SEG2) mee.
    if shell_lq and not tout and set(dims) <= set(shell_lq):
        tout = True
    # Knoopgroepen van kinematische voorwaarden krijgen de middenknopen erbij
    # (anders blijven die vrij); groepen met lasten niet: FORCE_NODALE werkt
    # per knoop, met middenknopen zou de totale last groter worden.
    kin = set(bc["selection"] for bc in model_data.get("bcs", [])
              if bc.get("type") in _KINEMATIC_BCS and bc.get("selection")
              and bc.get("aster_target") == "GROUP_NO")
    loaded = set(bc["selection"] for bc in model_data.get("bcs", [])
                 if bc.get("type") not in _KINEMATIC_BCS
                 and bc.get("selection"))
    # Koppelingen (RBE2/RBE3) en knoopgroepen in #ASTER-regels (bv.
    # LIAISON_MAIL GROUP_NO_ESCL) ook; behalve regels met FORCE_NODALE.
    for c in model_data.get("couplings", []):
        kin.update(g for g in (c.get("master_group"), c.get("slave_group"))
                   if g)
    custom = model_data.get("aster_custom", {})
    for line in (custom.get("code", []) + custom.get("zone", []) +
                 custom.get("contact", [])):
        if "FORCE_NODALE" not in line:
            for name in re.findall(r"<<([^<>]+)>>", line):
                kin.add(renames.get(name.strip(), name.strip()))
    # Een groep met een knooplast niet aanvullen: de last moet op de
    # Mecway-knopen blijven. Alleen melden als LINE_QUAD echt gebeurt.
    if (tout or shell_lq) and kin & loaded:
        log(tr("WARNING: LINE_QUAD: knoopselectie(s) {0} hebben zowel een "
               "voorwaarde als een last; de last blijft op de Mecway-knopen, "
               "maar de nieuwe middenknopen worden dan niet vastgehouden. "
               "Maak in Mecway aparte selecties voor last en voorwaarde.",
               "WARNING: LINE_QUAD: node selection(s) {0} have both a "
               "constraint and a load; the load stays on the Mecway nodes, "
               "but the new midside nodes are then not held. Create "
               "separate selections for load and constraint in Mecway.")
            .format(", ".join(sorted(kin & loaded))))
    # Knoopgroepen die de bridge zelf maakt (symmetry BRSY, compression only
    # BRCO, verlijmd contact BRESCL) en de knoopselecties van temperatuur
    # en beginsnelheid (veldwaarden per knoop, geen knooplast).
    kin.update(model_data.get("extra_node_groups", {}).keys())
    for t in model_data.get("temperatures", []):
        if t.get("selection"):
            kin.add(t["selection"])
    for sel, target, _v in model_data.get("initial_velocities", []):
        if target == "GROUP_NO":
            kin.add(sel)
    model_data["line_quad_nodegroups"] = sorted(kin - loaded)
    if tout:
        model_data["line_quad"] = "TOUT"
    elif shell_lq:
        model_data["line_quad"] = shell_lq
    if model_data["line_quad"] and any(
            bc.get("type") == "pinnedsupport"
            for bc in model_data.get("bcs", [])):
        log(tr("WARNING: LINE_QUAD: pinned support (gemiddelde verplaatsing "
               "nul) weegt alleen de Mecway-knopen (hoekknopen); de nieuwe "
               "middenknopen op die vlakken tellen niet mee.",
               "WARNING: LINE_QUAD: pinned support (zero mean "
               "displacement) only weighs the Mecway nodes (corner nodes); "
               "the new midside nodes on those faces do not count."))
    if model_data["line_quad"]:
        log("INFO: LINE_QUAD ({0}): lineaire cellen worden kwadratisch; "
            "resultaten in Mecway op de hoekknopen.".format(
                "alle cellen" if tout else ", ".join(shell_lq)))
        if CONFIG_BRIDGE.get("result_route", "liml") == "tabel":
            # De route "liml" verdeelt de reacties van de middenknopen over
            # de hoekknopen (aster_results_export._reaction_lumping); de
            # tabellen (GROUP_NO='all_nodes') bevatten alleen hoekknopen.
            log(tr("WARNING: LINE_QUAD met result_route 'tabel': de reacties "
                   "van de nieuwe middenknopen ontbreken in Mecway (som van "
                   "de reacties klopt niet). Kies 'liml' bij Resultaten naar "
                   "Mecway.",
                   "WARNING: LINE_QUAD with result_route 'tabel': the "
                   "reactions of the new midside nodes are missing in "
                   "Mecway (the sum of the reactions is wrong). Choose "
                   "'liml' under Results to Mecway."))


def _line_quad_block(model_data):
    """CREA_MAILLAGE LINE_QUAD volgens _resolve_line_quad, of ""."""
    lq = model_data.get("line_quad")
    if not lq:
        return ""
    # Deel van het mesh: rand-/vlakgroepen die geheel op de om te zetten
    # cellen liggen gaan mee (anders houdt bv. een ingeklemde schaalrand
    # alleen zijn hoekknopen vast); bepaald in de job uit het mesh.
    pre = ""
    where = "TOUT='OUI'"
    if lq != "TOUT":
        pre = _LQ_GROUPS + "_lq_groups = _bridge_lq_groups(mesh, {0})\n".format(
            _fmt_groups(lq))
        where = "GROUP_MA=_lq_groups"
    return ("# Lineaire cellen kwadratisch (bridge: LINE_QUAD, zie "
            "_resolve_line_quad)\n"
            + pre +
            "_n_lin = mesh.getNumberOfNodes()\n"
            "mesh = CREA_MAILLAGE(\n"
            "    MAILLAGE=mesh,\n"
            "    LINE_QUAD=_F({0}),\n"
            ")\n"
            + _LQ_NODEGROUPS + "\n").format(where)


def _line_quad_nodes_call(model_data):
    """
    Aanroep van _bridge_lq_nodegroups, na de DEFI_GROUP van de bridge:
    groepen die de bridge zelf met NOEUD=(...) aanmaakt (symmetry,
    compression only, verlijmd contact) bestaan pas dan.
    """
    if not model_data.get("line_quad"):
        return ""
    wanted = model_data.get("line_quad_nodegroups") or []
    return ("\n# Middenknopen (LINE_QUAD) toevoegen aan knoopgroepen van "
            "voorwaarden\n_bridge_lq_nodegroups(mesh, _n_lin, {0})\n".format(
                _fmt_groups(wanted) if wanted else "()"))


# Knoopgroepen (Mecway-knoopselecties, bv. een ingeklemde rand) kent
# CREA_MAILLAGE LINE_QUAD de nieuwe middenknopen niet toe; die zouden vrij
# blijven (plaat ingeklemd op knopen werd ~28% te slap). Een middenknoop
# hoort bij een groep als beide eindknopen van zijn rand erin zitten. De
# rand volgt uit de geometrie (middenknoop = midden van twee hoekknopen van
# dezelfde cel), dus onafhankelijk van de knoopvolgorde per celtype. De
# middenknoop van QUAD9/TRIA7 (laatste knoop, COQUE_3D) valt op het midden
# van een diagonaal maar draagt alleen rotaties: niet toevoegen (DX op die
# knoop -> CHARGES2_31).
# Mesh-API: getNodes(..., localNumbering=True) en setGroupOfNodes met
# 0-gebaseerde nummers, zoals in MacroCommands/Mac3Coeur (v17.4).
_LQ_GROUPS = (
    "def _bridge_lq_groups(mesh, groups):\n"
    "    conn = mesh.getConnectivity()\n"
    "    nodes = set()\n"
    "    for g in groups:\n"
    "        for c in mesh.getCells(g):\n"
    "            nodes.update(conn[c])\n"
    "    out = list(groups)\n"
    "    for g in mesh.getGroupsOfCells():\n"
    "        cells = mesh.getCells(g)\n"
    "        if g not in out and len(cells) and all(\n"
    "                set(conn[c]) <= nodes for c in cells):\n"
    "            out.append(g)\n"
    "    print('BRIDGE LINE_QUAD: groepen', out)\n"
    "    return tuple(out)\n"
)

_LQ_NODEGROUPS = (
    "def _bridge_lq_nodegroups(mesh, n_lin, wanted):\n"
    "    import numpy as np\n"
    "    xyz = np.asarray(mesh.getCoordinates().getValues(),\n"
    "                     dtype=float).reshape(-1, 3)\n"
    "    scale = 1.0e9 / max(1.0e-30, float(np.abs(xyz).max()))\n"
    "    key = lambda p: tuple(int(round(c * scale)) for c in p)\n"
    "    groups = [g for g in mesh.getGroupsOfNodes() if g in wanted]\n"
    "    if not groups:\n"
    "        return\n"
    "    members = dict((g, set(mesh.getNodes(g, localNumbering=True)))\n"
    "                   for g in groups)\n"
    "    union = set()\n"
    "    for s in members.values():\n"
    "        union |= s\n"
    "    mids = {{}}\n"
    "    centres = set()\n"
    "    for cell in mesh.getConnectivity():\n"
    "        if len(cell) in (7, 9):\n"
    "            centres.add(cell[-1])\n"
    "        corners = [n for n in cell if n < n_lin and n in union]\n"
    "        for i in range(len(corners)):\n"
    "            for j in range(i + 1, len(corners)):\n"
    "                a, b = corners[i], corners[j]\n"
    "                mids[key(0.5 * (xyz[a] + xyz[b]))] = (a, b)\n"
    "    pairs = {{}}\n"
    "    for m in range(n_lin, xyz.shape[0]):\n"
    "        if m in centres:\n"
    "            continue\n"
    "        ab = mids.get(key(xyz[m]))\n"
    "        if ab is not None:\n"
    "            pairs[m] = ab\n"
    "    for g in groups:\n"
    "        s = members[g]\n"
    "        extra = [m for m, (a, b) in pairs.items() if a in s and b in s]\n"
    "        if extra:\n"
    "            # Bestaande groep eerst weg (anders SOUSTRUC_37).\n"
    "            DEFI_GROUP(reuse=mesh, MAILLAGE=mesh,\n"
    "                       DETR_GROUP_NO=_F(NOM=g))\n"
    "            mesh.setGroupOfNodes(g, sorted(s | set(extra)))\n"
    "            print('BRIDGE LINE_QUAD: knoopgroep', g, '+', len(extra),\n"
    "                  'middenknopen')\n"
)


def _build_defigroup_block(model_data):
    """
    Genereer DEFI_GROUP voor Mecway nodeselections en voor slave-knopen
    van couplings op een faceselection, plus (indien nodig) CREA_MAILLAGE
    MODI_MAILLE voor kwadratische schalen (COQUE_3D) en MODI_MAILLAGE
    ORIE_PEAU voor drukvlakken (skin_groups).

    NOEUD-syntax: Code-Aster verwacht een tuple.
      Een knoop   -> NOEUD=('N7',)    (komma verplicht voor tuple)
      Meerdere    -> NOEUD=('N1', 'N2', ...)
    Knoopgroep uit vlakken: _F(NOM='naam', GROUP_MA='vlakgroep').
    """
    crea_entries = []
    # Knoopgroepen staan sinds bridge_mesh.write_mesh() al in het mesh.
    node_groups = ({} if model_data.get("node_groups_in_mesh")
                   else model_data["node_groups"])
    for name, ids in node_groups.items():
        id_str = ", ".join("'{0}'".format(i) for i in ids)
        crea_entries.append(
            "        _F(NOM='{0}', NOEUD=({1},)),".format(name, id_str))
    # Knoopgroepen voor SANS_GROUP_NO in DEFI_CONTACT (bridge_mesh.
    # _exclude_fixed_slaves); een GROUP_NO mag dezelfde naam hebben als de
    # GROUP_MA waar hij van komt.
    for name, group_ma in sorted(
            model_data.get("contact_sans_from_ma", {}).items()):
        crea_entries.append(
            "        _F(NOM='{0}', GROUP_MA='{1}'),".format(name, group_ma))
    for c in model_data.get("couplings", []):
        if c.get("slave_group_ma"):
            crea_entries.append(
                "        _F(NOM='{0}', GROUP_MA='{1}'),".format(
                    c["slave_group"], c["slave_group_ma"]))
    # Knoopgroepen per richting (symmetry, compression only;
    # bridge_mesh._extra_node_group). NOEUD in CREA_GROUP_NO: catalogus
    # defi_group.py v17.4 (statut 'c', toegestaan).
    for name, nids in model_data.get("extra_node_groups", {}).items():
        crea_entries.append("        _F(NOM='{0}', NOEUD={1}),".format(
            name, _fmt_seq(["'N{0}'".format(n) for n in nids],
                           indent="            ")))
    # Knopengroepen voor resultaattabellen met GROUP_MA (zie _postreleve).
    # Hier, vóór de solve: DEFI_GROUP reuse=mesh ná MECA_STATIQUE gaf in
    # Code-Aster 17.4 (Windows) "Windows fatal exception: access violation"
    # (gezien in Mecway, model met 6 balkgroepen). Alleen voor de route
    # 'tabel': met 'liml' zijn er geen tabellen (_results_route).
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        for table in _result_tables(model_data):
            if table[5]:
                for name, group in zip(
                        _table_node_groups(table[0], table[5]), table[5]):
                    crea_entries.append(
                        "        _F(NOM='{0}', GROUP_MA='{1}'),".format(
                            name, group))

    # model_data["group_ma_unions"] = {naam: [groepen]}: samengevoegde
    # contactvlakken (bridge_mesh._merge_contact_zones); hier een groep
    # (DEFI_GROUP CREA_GROUP_MA UNION, catalogus defi_group.py v17.4.0).
    copy_entries = []
    for name, parts in model_data.get("group_ma_unions", {}).items():
        copy_entries.append(
            "        _F(NOM='{0}', UNION={1}),".format(name, _fmt_groups(parts)))
    # Groepen van gap-elementen met dezelfde DIS_CONTACT (_prepare_gaps);
    # MAILLE in CREA_GROUP_MA: catalogus defi_group.py v17.4 (statut 'c').
    # Ook BRMAIT (verlijmd contact) en BRLP (_prepare_beam_loads). MAILLE=
    # 'M<n>' is in Code-Aster 17.4 de n-de cel in het meshbestand, niet de
    # naam (zie bridge_thermal._list_group): Mecway-elementnummer -> positie
    # via model_data["cell_names"] (bridge_mesh, bestandsvolgorde). Met
    # element-ID's +1000 gaf 'M<eid>' <EXCEPTION> MODELISA6_10.
    cell_pos = dict((n, i + 1) for i, n in
                    enumerate(model_data.get("cell_names", [])))
    for name, eids in model_data.get("extra_ma_groups", {}).items():
        refs = []
        for e in eids:
            pos = cell_pos.get("M{0}".format(e)) if cell_pos else e
            if pos is None:
                log(tr("ERROR: Element {0} van groep '{1}' staat niet in het "
                       "mesh; de groep is onvolledig.",
                       "ERROR: Element {0} of group '{1}' is not in the "
                       "mesh; the group is incomplete.").format(e, name))
                continue
            refs.append("'M{0}'".format(pos))
        copy_entries.append("        _F(NOM='{0}', MAILLE={1}),".format(
            name, _fmt_seq(refs, indent="            ")))

    def _factor(keyword, entries):
        if len(entries) == 1:
            # rstrip(","): de entry eindigt al op een komma; de
            # format-string voegt er zelf een toe (anders ",,").
            return "    {0}={1},".format(
                keyword, entries[0].strip().rstrip(","))
        return "    {0}=(\n{1}\n    ),".format(keyword, "\n".join(entries))

    block = "#-- not used in this analysis --\n"
    if crea_entries or copy_entries:
        parts = []
        if copy_entries:
            parts.append(_factor("CREA_GROUP_MA", copy_entries))
        if crea_entries:
            parts.append(_factor("CREA_GROUP_NO", crea_entries))
        block = (
            "mesh = DEFI_GROUP(\n"
            "    reuse=mesh,\n"
            "    MAILLAGE=mesh,\n"
            "{crea}\n"
            ")\n"
        ).format(crea="\n".join(parts))

    # Kwadratische volume-elementen (keuze "LINE_QUAD"): vóór de
    # knoopgroepen uit cellen, zodat die de middenknopen bevatten.
    block = _line_quad_block(model_data) + block

    # COQUE_3D bestaat alleen op QUAD9/TRIA7 (code_aster catalogus v17.4.0):
    # QUAD8/TRIA6 van Mecway eerst omzetten. CREA_MAILLAGE levert een nieuw
    # mesh-object; de groepen worden meegenomen.
    modi = []
    for elset, options in model_data.get("shell_upgrades", {}).items():
        for opt in options:
            if opt == "LINE_QUAD":      # al gedaan in _line_quad_block
                continue
            modi.append("        _F(GROUP_MA='{0}', OPTION='{1}'),".format(
                elset, opt))
    if modi:
        block += (
            "\nmesh = CREA_MAILLAGE(\n"
            "    MAILLAGE=mesh,\n"
            "    MODI_MAILLE=(\n"
            "{0}\n"
            "    ),\n"
            ")\n"
        ).format("\n".join(modi))

    # Drukvlakken op volume-elementen: normaal naar buiten richten, zodat
    # PRES_REP onafhankelijk is van de knoopvolgorde van Mecway's export
    # (MODI_MAILLAGE ORIE_PEAU, catalogus v17.4.0).
    skin_groups = model_data.get("skin_groups", [])
    if skin_groups:
        block += (
            "\nmesh = MODI_MAILLAGE(\n"
            "    reuse=mesh,\n"
            "    MAILLAGE=mesh,\n"
            "    ORIE_PEAU=_F(GROUP_MA_PEAU=({0},)),\n"
            ")\n"
        ).format(", ".join("'{0}'".format(g) for g in skin_groups))
    # Middenknopen van QUAD9/TRIA7 per LIAISON_OBLIQUE-selectie (na
    # MODI_MAILLE/LINE_QUAD: pas dan bestaan ze; _centre_node_groups).
    centre = _centre_node_groups(model_data)
    if centre:
        block += (
            "\n# Middenknopen QUAD9/TRIA7 (alleen rotaties) buiten "
            "LIAISON_OBLIQUE DX/DY/DZ\nmesh = DEFI_GROUP(\n"
            "    reuse=mesh,\n    MAILLAGE=mesh,\n    CREA_GROUP_NO=(\n{0}\n"
            "    ),\n)\n").format("\n".join(
                "        _F(GROUP_MA='{0}', CRIT_NOEUD='CENTRE', "
                "NOM='{1}'),".format(sel, name)
                for sel, name in centre.items()))
    return block + _line_quad_nodes_call(model_data)


def _build_model_block(model_data):
    """
    Genereer de AFFE_MODELE-aanroep voor gemengde 1D/2D/3D analyses.

    Elke elset krijgt zijn eigen _F()-entry met de bijbehorende
    MODELISATION uit model_data["elset_modelisations"]:
        1D (line2)            -> POU_D_E   (Euler-balk met torsie, als Mecway)
                                 of POU_D_T (Timoshenko; CONFIG "elem_beam")
        1D met veer-materiaal -> DIS_T
        2D lineair (tri3/quad4)   -> DKT of DST (CONFIG "elem_shell")
        2D kwadratisch (tri6/quad8) -> COQUE_3D (na MODI_MAILLE)
        3D (hex/tet/...)      -> 3D, of 3D_SI voor elsets met alleen hex8
                                 (CONFIG "elem_hex8")
    Daarnaast:
        skin_groups  (vlakken met druk op volume-elementen) -> 3D
                     (AFFE_MODELE kent dan randelementen toe)
        poi1_groups  (losse knopen, zie bridge_mesh.py)     -> DIS_T/DIS_TR

    Als er niets te modelleren is, wordt een globale TOUT='OUI',
    MODELISATION='3D' fallback gegenereerd.
    """
    elset_mods = model_data.get("elset_modelisations", {})
    skin_groups = model_data.get("skin_groups", [])
    poi1_groups = model_data.get("poi1_groups", {})

    if not elset_mods and not skin_groups and not poi1_groups and \
            not model_data.get("discretes"):
        log("INFO: Geen elset-modelisaties; gebruik TOUT='OUI', MODELISATION='3D'.")
        return (
            "model = AFFE_MODELE(\n"
            "    MAILLAGE=mesh,\n"
            "    AFFE=_F(TOUT='OUI', PHENOMENE='MECANIQUE', MODELISATION='3D'),\n"
            ")\n"
        )

    lines = [
        "model = AFFE_MODELE(",
        "    MAILLAGE=mesh,",
        "    AFFE=(",
    ]
    for elset_name, modelisation in elset_mods.items():
        lines.append(
            "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE',"
            " MODELISATION='{1}'),".format(elset_name, modelisation)
        )
    for group in skin_groups:
        lines.append(
            "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE',"
            " MODELISATION='3D'),".format(group)
        )
    for group, modelisation in poi1_groups.items():
        lines.append(
            "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE',"
            " MODELISATION='{1}'),".format(group, modelisation)
        )
    for group, d in model_data.get("discretes", {}).items():
        lines.append(
            "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE',"
            " MODELISATION='{1}'),".format(group, d["mod"]))
    # Schaalranden met FORCE_ARETE (bridge_mesh._line_pressure)
    for group, modelisation in model_data.get("edge_groups", {}).items():
        lines.append(
            "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE',"
            " MODELISATION='{1}'),".format(group, modelisation))
    lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


def _model_groups(model_data):
    """Alle GROUP_MA's die _build_model_block in AFFE_MODELE zet."""
    groups = list(model_data.get("elset_modelisations", {}))
    groups += list(model_data.get("skin_groups", []))
    groups += list(model_data.get("poi1_groups", {}))
    groups += list(model_data.get("discretes", {}))
    groups += list(model_data.get("edge_groups", {}))
    out = []
    for g in groups:
        if g not in out:
            out.append(g)
    return out


def _shell_ref_vector(model_data, group):
    """
    Referentievector voor het lokale assenstelsel van een schaalgroep.

    Code-Aster projecteert zonder VECTEUR/ANGL_REP de globale X-as op het
    element (U4.42.01 COQUE, VECTEUR); staat de schaalnormaal langs X, dan
    stopt de berekening met PLATE1_40. Returns None als X bruikbaar is
    (uitvoer ongewijzigd), anders de globale as die het verst van alle
    normalen af ligt. Ligt elke as bijna langs een normaal (bv. een gesloten
    doos in een selectie), dan een WARNING: splits de selectie in Mecway.
    """
    nodes = model_data.get("mesh_nodes", {})
    renames = model_data.get("group_renames", {})
    normals = []
    for elem in model_data.get("mesh_elements", []):
        if renames.get(elem[3], elem[3]) != group:
            continue
        pts = [nodes[n] for n in elem[2][:4] if n in nodes]
        if len(pts) < 3:
            continue
        if elem[1].startswith("quad") and len(pts) == 4:
            a = [pts[2][i] - pts[0][i] for i in range(3)]
            b = [pts[3][i] - pts[1][i] for i in range(3)]
        else:
            a = [pts[1][i] - pts[0][i] for i in range(3)]
            b = [pts[2][i] - pts[0][i] for i in range(3)]
        n = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
             a[0] * b[1] - a[1] * b[0])
        length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if length > 0.0:
            normals.append([c / length for c in n])
    if not normals:
        return None
    # Grootste |cos| tussen as en normaal; 0.9 = as minstens ~25 graden uit
    # het vlak, ruim genoeg voor een goed bepaald lokaal assenstelsel.
    worst = [max(abs(n[axis]) for n in normals) for axis in range(3)]
    if worst[0] < 0.9:
        return None
    axis = min(range(3), key=lambda k: worst[k])
    if worst[axis] >= 0.9:
        log(tr("WARNING: Schaalgroep '{0}' heeft normalen langs alle "
               "globale assen; geen referentievector (VECTEUR) die voor elk "
               "element werkt. Splits de selectie in Mecway per vlak als "
               "Code-Aster stopt met PLATE1_40.",
               "WARNING: Shell group '{0}' has normals along all global "
               "axes; no reference vector (VECTEUR) works for every "
               "element. Split the selection per face in Mecway if "
               "Code-Aster stops with PLATE1_40.").format(group))
    vect = [0.0, 0.0, 0.0]
    vect[axis] = 1.0
    log("INFO: Schaalgroep '{0}' ligt (deels) loodrecht op X; lokaal "
        "assenstelsel via VECTEUR=({1}, {2}, {3}).".format(group, *vect))
    return vect


def _build_cara_elem_block(model_data):
    """
    Genereer de AFFE_CARA_ELEM-aanroep voor schaal-, staaf- en veer-elementen.

    COQUE-entries: 2D-elsets met Plate-geometrie.
    POUTRE-entries: 1D-elsets met balk-doorsnede-geometrie.
    DISCRET-entries: 1D-elsets met veer-materiaal (DIS_T, K_T_D_L) en
    POI1-groepen (K_T_D_N / K_TR_D_N), elk met een massa-entry (M_*).

    Zonder balken, schalen, veren en POI1-groepen (zie _has_cara) wordt
    een commentaarregel teruggegeven zodat de placeholder geldig blijft.

    ORIENTATION-entries: balken met een eigen V-as (Mecway
    orientationvx/vy/vz + angle). bridge_mesh.py zet die in subgroepen met
    een V per groep (model_data["beam_vect_y"]); CARA='VECT_Y' legt de
    lokale y-as van Code-Aster langs V. Zonder eigen orientatie zijn de
    standaarden van Mecway en Code-Aster gelijk (nagelopen met een
    vergelijking Mecway <-> Code-Aster voor balken langs X, langs Z en
    schuin).
    """
    shell_secs  = model_data.get("shell_sections",  {})
    beam_secs   = model_data.get("beam_sections",   {})
    spring_secs = model_data.get("spring_sections", {})
    poi1_groups = model_data.get("poi1_groups",     {})

    if not _has_cara(model_data):
        return "#-- not used in this analysis --\n"

    lines = ["cara = AFFE_CARA_ELEM(", "    MODELE=model,"]

    # --- COQUE (schaal-elementen) ---
    if shell_secs:
        shell_entries = []
        for elset_name, sec in shell_secs.items():
            vect = _shell_ref_vector(model_data, elset_name)
            shell_entries.append(
                "        _F(GROUP_MA='{0}', EPAIS={1}{2}),".format(
                    elset_name, sec["thickness"],
                    "" if vect is None else
                    ", VECTEUR=({0}, {1}, {2})".format(*vect))
            )
        if len(shell_entries) == 1:
            lines.append("    COQUE={0},".format(
                shell_entries[0].strip().rstrip(",")))
        else:
            lines.append("    COQUE=(")
            lines.extend(shell_entries)
            lines.append("    ),")

    # --- BARRE (truss-elementen, MODELISATION 'BARRE', bridge_from_liml):
    # alleen de oppervlakte (catalogus affe_cara_elem.py BARRE, SECTION
    # 'GENERALE' met CARA 'A'; testcases ssnl105a/sdnl138a) ---
    truss_entries = [
        "        _F(GROUP_MA='{0}', SECTION='GENERALE', CARA='A', "
        "VALE={1!r}),".format(elset_name, float(sec["area"]))
        for elset_name, sec in beam_secs.items() if sec.get("truss")]
    if truss_entries:
        lines.append("    BARRE=(")
        lines.extend(truss_entries)
        lines.append("    ),")
    beam_secs = OrderedDict((k, v) for k, v in beam_secs.items()
                            if not v.get("truss"))

    # --- POUTRE (staaf-/balk-elementen) ---
    if beam_secs:
        beam_entries = []
        for elset_name, sec in beam_secs.items():
            cara_str = ", ".join("'{0}'".format(c) for c in sec["cara"])
            vale_str = ", ".join("{0}".format(v)   for v in sec["vale"])
            beam_entries.append(
                "        _F(GROUP_MA='{0}',\n"
                "           SECTION='{1}',\n"
                "           CARA=({2},),\n"
                "           VALE=({3},)),".format(
                    elset_name, sec["aster_section"], cara_str, vale_str)
            )
        if len(beam_entries) == 1:
            lines.append("    POUTRE={0},".format(
                beam_entries[0].strip().rstrip(",")))
        else:
            lines.append("    POUTRE=(")
            lines.extend(beam_entries)
            lines.append("    ),")

    # --- ORIENTATION (balken met een eigen V-as) ---
    orient_entries = []
    for group, v in model_data.get("beam_vect_y", {}).items():
        orient_entries.append(
            "        _F(GROUP_MA='{0}', CARA='VECT_Y', VALE=({1}, {2}, "
            "{3})),".format(group, v[0], v[1], v[2]))
    if len(orient_entries) == 1:
        lines.append("    ORIENTATION={0},".format(
            orient_entries[0].strip().rstrip(",")))
    elif orient_entries:
        lines.append("    ORIENTATION=(")
        lines.extend(orient_entries)
        lines.append("    ),")

    # --- DISCRET (veer-elementen, DIS_T) ---
    # K_T_D_L: diagonale translatie-stijfheidsmatrix (KX, KY, KZ).
    # De veer werkt in de lokale x-richting (balk-as); KY=KZ=0.
    # Voor een volledige 3D-veer: gebruik K_TR_D_L met 6 waarden.
    # POI1 (losse knopen): stijfheid 0; de knoop krijgt alleen
    # vrijheidsgraden voor LIAISON_RBE3 / LIAISON_SOLIDE.
    #   DIS_T  -> K_T_D_N  (3 waarden)
    #   DIS_TR -> K_TR_D_N (6 waarden)
    # Massa: elk discreet element krijgt ook een massa-matrix met waarde 0
    # (M_T_D_L / M_T_D_N: 1 waarde; M_TR_D_N: 10 waarden). Zonder
    # M_*-toewijzing geeft Code-Aster alarm DISCRETS_26 ("matrice de MASSE
    # ... pas affecte"); afdi3d.F90 (v17.4.0) zet de vlag DISM bij elke
    # M_*-toewijzing, ook met waarde 0. CARA mag per _F maar 1 waarde
    # hebben (catalogus affe_cara_elem.py), dus aparte _F-entries.
    if spring_secs or poi1_groups:
        discret_entries = []
        for elset_name, sec in spring_secs.items():
            k = sec["spring_constant"]
            # REPERE='LOCAL': k langs de eigen as van de veer (lokale x
            # van een SEG2 = knoop 1 -> knoop 2). Standaard is REPERE
            # 'GLOBAL' (catalogus affe_cara_elem.py v17.4): dan werkte k in
            # globaal X, ook voor een veer langs Y (verificatie LS-06).
            discret_entries.append(
                "        _F(GROUP_MA='{0}',\n"
                "           CARA='K_T_D_L', REPERE='LOCAL',\n"
                "           VALE=({1}, 0.0, 0.0)),".format(elset_name, k)
            )
            discret_entries.append(
                "        _F(GROUP_MA='{0}',\n"
                "           CARA='M_T_D_L',\n"
                "           VALE=(0.0,)),".format(elset_name)
            )
        for group, modelisation in poi1_groups.items():
            if modelisation == "DIS_TR":
                cara, vale = "K_TR_D_N", "0.0, 0.0, 0.0, 0.0, 0.0, 0.0"
                mcara, mvale = "M_TR_D_N", ", ".join(["0.0"] * 10)
            else:
                cara, vale = "K_T_D_N", "0.0, 0.0, 0.0"
                mcara, mvale = "M_T_D_N", "0.0"
            discret_entries.append(
                "        _F(GROUP_MA='{0}',\n"
                "           CARA='{1}',\n"
                "           VALE=({2})),".format(group, cara, vale)
            )
            discret_entries.append(
                "        _F(GROUP_MA='{0}',\n"
                "           CARA='{1}',\n"
                "           VALE=({2},)),".format(group, mcara, mvale)
            )
    else:
        discret_entries = []
    discret_entries += _discrete_cara_entries(model_data)
    if model_data.get("damping_matrix"):
        # Complexe modes (AMOR_MECA): demping 0 op de andere discreten
        discret_entries += bridge_modal_damping.zero_damping_entries(
            discret_entries)
    if discret_entries:
        if len(discret_entries) == 1:
            lines.append("    DISCRET={0},".format(
                discret_entries[0].strip().rstrip(",")))
        else:
            lines.append("    DISCRET=(")
            lines.extend(discret_entries)
            lines.append("    ),")

    # --- CABLE (tension only, U4.42.01 AFFE_CARA_ELEM CABLE: AIRE en
    # N_INIT verplicht; N_INIT = 0: geen voorspanning) ---
    cable_entries = [
        "        _F(GROUP_MA='{0}', AIRE={1!r}, N_INIT=0.0),".format(
            elset, sec["area"])
        for elset, sec in model_data.get("cable_sections", {}).items()]
    if cable_entries:
        lines.append("    CABLE=(")
        lines.extend(cable_entries)
        lines.append("    ),")

    lines.append(")")
    return "\n".join(lines) + "\n"


def _discrete_cara_entries(model_data):
    """
    DISCRET-entries voor de POI1-discreten van bridge_mesh._build_discretes
    (elastic support, knoopmassa's) en de line2-discreten (gap, damper).
    Elk discreet element krijgt stijfheid, massa (en demping) zodat
    Code-Aster geen alarm DISCRETS_26 geeft (zie hierboven).
    Damper (manual v33 par. 7.8): A_T_D_L = (c, 0, 0), demping langs de
    elementas. Gap: K_T_D_L = (k, 0, 0) als startmatrix; het gedrag komt
    van DIS_CHOC (DEFI_MATERIAU DIS_CONTACT, _prepare_gaps).
    """
    out = []

    def entry(group, cara, vals, local=False):
        out.append("        _F(GROUP_MA='{0}', CARA='{1}', {3}VALE=({2},)),"
                   .format(group, cara, ", ".join(repr(float(v))
                                                  for v in vals),
                           "REPERE='LOCAL', " if local else ""))
    for group, d in model_data.get("discretes", {}).items():
        for cara, vals in d["cara"]:
            entry(group, cara, vals)
    for elset, sec in model_data.get("discrete_sections", {}).items():
        # Gap: stijfheid 0 op de elset, k op de vertaalde gap-groepen
        # (latere occurrence overschrijft; niet-vertaalde gaps houden 0).
        entry(elset, "K_T_D_L", (0.0, 0.0, 0.0))
        entry(elset, "M_T_D_L", (0.0,))
        if sec["kind"] == "damper":
            # langs de eigen as van de demper (zie de veer hierboven)
            entry(elset, "A_T_D_L", (sec["c"], 0.0, 0.0), local=True)
    for group, gap in model_data.get("gap_groups", {}).items():
        entry(group, "K_T_D_L", (gap["k"], 0.0, 0.0))
    return out


# Modelisaties waarvan de spanningen sub-punten (lagen) hebben.
_SHELL_MODELISATIONS = ("DKT", "DST", "COQUE_3D")

# Volume- en balkmodelisaties die voor de post-processing gelijk zijn aan
# '3D' resp. 'POU_D_E'.
_VOLUME_MODELISATIONS = ("3D", "3D_SI")
_BEAM_MODELISATIONS = ("POU_D_E", "POU_D_T")

# Doorsneden waarvoor SIPM_ELNO zinvol is: posigr.F90 (v17.4.0) rekent
# alleen voor TSEC=1 (RECTANGLE) en TSEC=2 (CERCLE); voor GENERALE (TSEC=0)
# geeft Code-Aster alarm ELEMENTS4_4 en geen waarden.
_SIPM_SECTIONS = ("RECTANGLE", "CERCLE")

# POST_RELEVE_T leest INTITULE in een character(len=16) (rvtecn.F90 e.a.,
# v17.4.0); langere namen worden afgekapt.
ASTER_INTITULE_MAX = 16


def _intitule(name):
    """INTITULE zoals Code-Aster hem in de tabel schrijft (max. 16 tekens)."""
    return name[:ASTER_INTITULE_MAX]


def _fmt_groups(groups):
    """('A', 'B',) - tuple-notatie, ook geldig voor een enkele groep."""
    return "({0},)".format(", ".join("'{0}'".format(g) for g in groups))


def _result_groups(model_data, verbose=False):
    """
    Groepen per soort post-processing.

    Returns
    -------
    (groups_3d, groups_shell, groups_beam_sipm)
        groups_3d        : elsets met MODELISATION '3D' / '3D_SI'
        groups_shell     : elsets met DKT / DST / COQUE_3D
        groups_beam_sipm : POU_D_E/POU_D_T-elsets met RECTANGLE- of
                           CERCLE-doorsnede
    """
    mods      = model_data.get("elset_modelisations", {})
    beam_secs = model_data.get("beam_sections", {})
    g3d, gsh, gbm = [], [], []
    for group, mod in mods.items():
        if mod in _VOLUME_MODELISATIONS:
            g3d.append(group)
        elif mod in _SHELL_MODELISATIONS:
            gsh.append(group)
        elif mod in _BEAM_MODELISATIONS:
            section = beam_secs.get(group, {}).get("aster_section")
            mat = model_data.get("elsets", {}).get(group)
            if (mat in model_data.get("materials", {}) and
                    _relation_for(model_data, mat) != "ELAS"):
                # Plastisch materiaal (ECRO_LINE/TRACTION in DEFI_MATERIAU)
                # op een balk: de balk rekent elastisch
                # (_build_comportement_block), maar SIPM_ELNO weigert het
                # materiaal: <EXCEPTION> ELEMENTS4_64 "votre matériau doit
                # avoir un seul comportement : ELAS" (Code-Aster 17.4).
                if verbose:
                    log("INFO: Balk-elset '{0}': geen SIPM_ELNO (plastisch "
                        "materiaal, ELEMENTS4_64).".format(group))
                continue
            if section in _SIPM_SECTIONS:
                gbm.append(group)
            elif verbose:
                log("INFO: Balk-elset '{0}' (doorsnede {1}): geen "
                    "SIPM_ELNO-spanningen; Code-Aster berekent die alleen "
                    "voor RECTANGLE en CERCLE.".format(group, section))
    return g3d, gsh, gbm


def _build_calc_champ_block(model_data, with_plastic=False, reactions=True):
    """
    Genereer de CALC_CHAMP-aanroepen (en POST_CHAMP voor schalen).
    reactions False: zonder REAC_NODA (spanningen per mode, _build_modal).

    Code-Aster v17.4.0, geverifieerd in catalogus en testcases:

    REAC_NODA
        Eigen aanroep; zonder GROUP_MA (alle knopen), behalve bij elastic
        support: dan zonder de veren (BRES*), zie hieronder.

    SIGM_NOEU / SIEQ_NOEU (+ EPSP_NOEU / VARI_NOEU bij plasticiteit)
        Alleen op de 3D-elsets (GROUP_MA). Op schalen (DKT/COQUE_3D) heeft
        het spanningsveld sub-punten (lagen); een NOEU-veld kan die niet
        bevatten, dus Code-Aster slaat die elementen anders over met alarm
        UTILITAI_3. Balken (POU_D_E) leveren geen SIGM_NOEU.

    Schalen: SIGM_ELNO -> POST_CHAMP EXTR_COQUE (NUME_COUCHE=1, NIVE_COUCHE
        'SUP', 'MOY' en 'INF') -> SIEQ_ELNO -> SIEQ_NOEU. Zelfde volgorde
        als testcase ssls131a (DKT). COQUE_NCOU is standaard 1 (catalogus
        AFFE_CARA_ELEM). In Mecway: vonmisesu1 / vonmisesm / vonmisesb
        (zie STRUCT_FIELD_SPECS in bridge_from_aster.py). Alleen de von
        Mises-spanning gaat naar Mecway: de tensorcomponenten van schalen
        staan in het lokale schaal-assenstelsel van Code-Aster.

    Balken: SIPM_ELNO (SIXXMIN/SIXXMAX: extreme axiale spanning in de
        doorsnede uit N, MFY, MFZ; option sipm_elno.py / posigr.F90).
        Alleen voor RECTANGLE en CERCLE, zie _SIPM_SECTIONS.
    """
    g3d, gsh, gbm = _result_groups(model_data, verbose=True)

    out = [] if not reactions else [
        "res = CALC_CHAMP(",
        "    reuse=res,",
        "    RESULTAT=res,",
    ]
    # Elastic support is in Code-Aster een veer-element (POI1, BRES*): de
    # knoop is in evenwicht en REAC_NODA is daar 0, terwijl Mecway de
    # veerkracht als reactie toont. REAC_NODA dan zonder die veren
    # berekenen, zodat de kracht van de constructie op de veer de reactie
    # is (GROUP_MA in CALC_CHAMP, catalogus calc_champ.py v17.4).
    springs = [g for g in model_data.get("discretes", {})
               if g.startswith("BRES")]
    if springs and reactions:
        groups = [g for g in _model_groups(model_data) if g not in springs]
        out.append("    GROUP_MA={0},".format(_fmt_groups(groups)))
    if reactions:
        out += [
            "    FORCE=('REAC_NODA', ),",
            ")",
            "",
        ]

    # result_route "liml": ook spanningen per element-knoop (Mecway's
    # contour "per element"). aster_results_export schrijft SIGM_ELNO en
    # SIEQ_ELNO van volume-elementen als elementnodevariable. SIGM_ELNO EEN
    # keer over volume + schalen aanvragen, anders faalt POST_CHAMP
    # EXTR_COQUE later (CALCULEL2_15; zie de kop van aster_results_export).
    elno = bool(g3d) and CONFIG_BRIDGE.get("result_route", "liml") == "liml"
    if elno:
        out += [
            "# Spanningen per element-knoop voor Mecway (result_route 'liml').",
            "res = CALC_CHAMP(",
            "    reuse=res,",
            "    RESULTAT=res,",
            "    GROUP_MA={0},".format(_fmt_groups(list(g3d) + list(gsh))),
            "    CONTRAINTE=('SIGM_ELNO', ),",
            ")",
            "res = CALC_CHAMP(",
            "    reuse=res,",
            "    RESULTAT=res,",
            "    GROUP_MA={0},".format(_fmt_groups(g3d)),
            "    CRITERES=('SIEQ_ELNO', ),",
            ")",
            "",
        ]

    if g3d:
        out += [
            "res = CALC_CHAMP(",
            "    reuse=res,",
            "    RESULTAT=res,",
            "    GROUP_MA={0},".format(_fmt_groups(g3d)),
            "    CONTRAINTE=('SIGM_NOEU', ),",
            "    CRITERES=('SIEQ_NOEU', ),",
        ]
        if with_plastic:
            out.append("    DEFORMATION=('EPSP_NOEU', ),")
            # V1 is de cumulatieve plastische rek bij VMIS_ISOT_*; bij
            # VMIS_CINE_LINE zijn V1..V6 de terugspanning (NIET
            # geverifieerd in R5.03.02), dus dan geen VARI_NOEU (anders
            # zou "equivalentplasticstrain" in Mecway iets anders tonen).
            if any((p.get("plastic_bilinear") or {}).get("kinematic")
                   for p in model_data["materials"].values()):
                log("INFO: Kinematische versteviging: geen equivalente "
                    "plastische rek (VARI_NOEU) naar Mecway, wel de "
                    "plastische rektensor (EPSP_NOEU).")
            else:
                out.append("    VARI_INTERNE=('VARI_NOEU', ),")
        out += [")", ""]
    elif with_plastic:
        log(tr("WARNING: Plastisch materiaal maar geen 3D-elsets; "
               "EPSP_NOEU/VARI_NOEU worden niet berekend.",
               "WARNING: Plastic material but no 3D elsets; "
               "EPSP_NOEU/VARI_NOEU are not computed."))

    if gsh:
        groups = _fmt_groups(gsh)
        out += [
            "# Schalen: spanningen per laag (sub-punten) -> boven-, midden-",
            "# en ondervlak apart extraheren (POST_CHAMP EXTR_COQUE).",
        ]
        if not elno:
            out += [
                "res = CALC_CHAMP(",
                "    reuse=res,",
                "    RESULTAT=res,",
                "    GROUP_MA={0},".format(groups),
                "    CONTRAINTE=('SIGM_ELNO', ),",
                ")",
                "",
            ]
        for concept, level in (("res_sup", "SUP"), ("res_moy", "MOY"),
                               ("res_inf", "INF")):
            out += [
                "{0} = POST_CHAMP(".format(concept),
                "    RESULTAT=res,",
                "    GROUP_MA={0},".format(groups),
                "    EXTR_COQUE=_F(",
                "        NOM_CHAM=('SIGM_ELNO', ),",
                "        NUME_COUCHE=1,",
                "        NIVE_COUCHE='{0}',".format(level),
                "    ),",
                ")",
                # GROUP_MA is nodig: POST_CHAMP vult SIGM_ELNO alleen op de
                # schalen, en zonder GROUP_MA rekent CALC_CHAMP op alle
                # elementen van het model. Dat geeft <EXCEPTION> CALCULEL_58
                # ("Il manque la composante : SIXX") op het eerste 3D- of
                # balkelement (gezien in een run met Code-Aster 17.4).
                "{0} = CALC_CHAMP(reuse={0}, RESULTAT={0}, GROUP_MA={1}, "
                "CRITERES=('SIEQ_ELNO', ))".format(concept, groups),
                "{0} = CALC_CHAMP(reuse={0}, RESULTAT={0}, GROUP_MA={1}, "
                "CRITERES=('SIEQ_NOEU', ))".format(concept, groups),
                "",
            ]

    if gbm:
        out += [
            "# Balken: extreme axiale spanning in de doorsnede.",
            "res = CALC_CHAMP(",
            "    reuse=res,",
            "    RESULTAT=res,",
            "    GROUP_MA={0},".format(_fmt_groups(gbm)),
            "    CONTRAINTE=('SIPM_ELNO', ),",
            ")",
            "",
        ]

    return "\n".join(out) + "\n"


# ==========================================
# FOUTSCHATTER (CALC_ERREUR, residu-schatter ERME)
# ==========================================
# Lasten die CALC_ERREUR ERME_ELEM meeneemt. Gezien met Code-Aster 17.4:
# PRES_REP (carte PRESS), FORCE_FACE en PESANTEUR werken; FORCE_NODALE
# geeft alarm INDICATEUR_6 ("ne sait pas traiter les charges du type de
# ...") en daarna <EXCEPTION> INDICATEUR_8; twee lasten met PRES_REP geven
# INDICATEUR_7 ("Le choix PRESS apparaît au moins dans 2 charges") en
# INDICATEUR_8. ROTATION: geen alarm, en de volumeterm verandert als hij
# ontbreekt (gezien, balk met centrifugaal); FORCE_INTERNE: testcase
# sslv153a (dual probleem).
_ERME_LOAD_KEYWORDS = ("PRES_REP", "FORCE_FACE", "PESANTEUR", "ROTATION",
                       "FORCE_INTERNE")
# Lasten op vlakken: alleen op randelementen van volume-elementen.
_ERME_FACE_KEYWORDS = ("PRES_REP", "FORCE_FACE")
# Druk op de vrije vlakken [Pa]: verwaarloosbaar, maar niet 0 (zie
# _error_estimator_block).
_ERR_FREE_PRES = 1.0e-14


def _erme_force_face(entry):
    """
    FORCE_FACE-entry voor de last van de schatter met omgekeerd teken van
    FX/FY/FZ. Gemeten (Code-Aster 17.4, stap S7): ERME rekent de randterm
    van FORCE_FACE als sigma.n + g in plaats van sigma.n - g. Blok onder
    uniforme trek 100 MPa (hex20, exacte oplossing): met FX = +1e8 in
    load_err een geschatte fout van 15% (alleen TERME NORMAL), met FX =
    -1e8 0,000%, met FX = +2e8 22% (de randterm 3/2 x die van +1e8); met
    PRES_REP (druk -1e8) 0,000%. Ook in z-richting (FZ). Alleen de
    normaalcomponent telt ("TERME NORMAL"): een tangentiele FZ op een vlak
    met normaal x (FS-01 n = 4) gaf met FZ = +1e6 / -1e6 / 0 / +3e6 een
    randterm van 6,65 / 6,66 / 6,66 / 6,67%, dus FS-01 verandert niet. Een
    U-doc of de bron (te0003/ermebo) is NIET ingezien; de oplossing zelf
    (MECA_STATIQUE) gebruikt deze last niet.
    """
    def neg(m):
        try:
            return "{0}={1!r}".format(m.group(1), -float(m.group(2)))
        except ValueError:
            return m.group(0)
    return re.sub(r"\b(F[XYZ])=([-+0-9.eE]+)", neg, entry)


def _error_estimator_groups(model_data, analysis):
    """
    Volumegroepen voor de foutschatter, of [] als die niet draait (uit, of
    geen volume-elementen: WARNING). Alleen MECA_STATIQUE (zie
    bridge_utils.error_estimator_requested).
    """
    if not analysis.get("error_estimator", False):
        return []
    g3d = _result_groups(model_data)[0]
    if not g3d:
        log(tr("WARNING: Foutschatter: het model heeft geen volume-elementen; "
               "CALC_ERREUR (ERME) bestaat in de bridge alleen voor volumes. "
               "Geen foutschatting.",
               "WARNING: Error estimator: the model has no solid elements; "
               "CALC_ERREUR (ERME) is only used for solids in the bridge. "
               "No error estimate."))
        return []
    return g3d


def _entry_groups(entry):
    """GROUP_MA-namen in een _F-tekst (een naam of een tuple)."""
    found = re.search(r"GROUP_MA=\(?([^)=]*?)\)?(?:,\s*[A-Z_]+=|\)$)", entry)
    if not found:
        return []
    return re.findall(r"'([^']+)'", found.group(1))


def _error_estimator_block(model_data, charges, g3d):
    """
    CALC_ERREUR voor de foutschatter, als regels voor na CALC_CHAMP.
    Alles nagelopen met Code-Aster 17.4 (runs bij de bouw, zie
    docs/Foutschatter.md):

    - Eigen last load_err: de constante lasten die ERME kent
      (_ERME_LOAD_KEYWORDS) samen in een AFFE_CHAR_MECA, plus PRES_REP op de
      vrije vlakken (bridge_mesh._free_faces). Zo telt elke soort maar een
      keer (INDICATEUR_7/8) en vallen puntlasten (FORCE_NODALE,
      INDICATEUR_6/8) weg; een puntlast is voor de schatter een
      spanningsvrije rand, de fout is daar groot (terecht: singulier). De
      oplossing zelf (MECA_STATIQUE) gebruikt load_err niet.
    - Vrije vlakken met PRES = _ERR_FREE_PRES (1e-14 Pa, zoals _pres0 in
      sslv153a), niet 0: met PRES = 0.0 bleef de randterm ("TERME NORMAL")
      gelijk aan die zonder die vlakken, met 1e-14 niet.
    - Eigen resultaat res_err (CREA_RESU met DEPL van res, dan SIGM_ELNO op
      het hele model en CALC_ERREUR met EXCIT=load_err en reuse): CALC_ERREUR
      reuse=res met een andere EXCIT geeft <EXCEPTION> CALCULEL_39; zonder
      reuse komt ERME_ELEM in het nieuwe resultaat, maar ERME_ELNO/NOEU
      zoeken hun bronvelden in RESULTAT (UTILITAI8_13, CALCUL_29/17). En
      SIGM_ELNO moet op het hele model staan, anders INDICATEUR_2 en
      CALCUL_29. Zo geen alarmen RESULT1_40/65 (andere lasten dan in res).
    - Velden ERME_ELEM, ERME_ELNO (per element constant) en ERME_NOEU
      (gemiddeld per knoop), zoals testcase sslv153a. Componenten o.a.
      ERREST (absolute schatting eta_e), NUEST = 100 eta_e / sqrt(eta_e^2 +
      SIGCAL^2) (lokaal relatief, %) en SIGCAL (norm van sigma per element);
      nagerekend in een run. De globale fout (100 sqrt(som eta^2 / (som
      eta^2 + som SIGCAL^2))) drukt CALC_ERREUR zelf af in de .mess
      ("ESTIMATEUR D'ERREUR EN RESIDU EXPLICITE", gelezen door
      bridge_results_liml.read_error_summary).

    Returns tekst, of "" als er geen last voor de schatter is (WARNING).
    """
    skin = set(model_data.get("skin_groups", []))
    merged = OrderedDict()
    left_out = []
    for command, kws, fonc in charges:
        for kw, entries in kws.items():
            if kw not in _ERME_LOAD_KEYWORDS:
                if kw in _LOAD_KEYWORDS:
                    left_out.append(kw)
                continue
            for entry in entries:
                groups = _entry_groups(entry)
                allowed = skin if kw in _ERME_FACE_KEYWORDS else set(g3d)
                if command != "AFFE_CHAR_MECA" or fonc is not None or (
                        (groups or kw in _ERME_FACE_KEYWORDS) and
                        not (groups and set(groups) <= allowed)):
                    left_out.append(kw)
                    continue
                if kw == "FORCE_FACE":
                    entry = _erme_force_face(entry)
                merged.setdefault(kw, []).append(entry)
    free = model_data.get("error_free_group")
    if free:
        merged.setdefault("PRES_REP", []).append(
            "_F(GROUP_MA='{0}', PRES={1!r})".format(free, _ERR_FREE_PRES))
    if left_out:
        log(tr("INFO: Foutschatter: niet meegenomen lasten ({0}); voor de "
               "schatter is daar een spanningsvrije rand (een puntlast geeft "
               "daar een grote lokale fout).",
               "INFO: Error estimator: loads not included ({0}); for the "
               "estimator that is a traction-free boundary (a point load "
               "gives a large local error there).").format(
                   ", ".join(sorted(set(left_out)))))
    if not merged:
        log(tr("WARNING: Foutschatter: geen last of vrij vlak voor CALC_ERREUR; "
               "geen foutschatting.",
               "WARNING: Error estimator: no load or free face for "
               "CALC_ERREUR; no error estimate."))
        return ""
    _warn_overlapping_faces(model_data, merged)
    mods = model_data.get("elset_modelisations", {})
    affe = ["        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
            "MODELISATION='{1}'),".format(g, mods.get(g, "3D")) for g in g3d]
    affe += ["        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
             "MODELISATION='3D'),".format(g) for g in sorted(skin)]
    entries, varc = model_data.get("_fieldmat_parts", ([], ""))
    # Alleen de volumegroepen (een materiaal op een groep buiten model_err
    # is zinloos); TOUT='OUI' blijft.
    entries = [e for e in entries if "TOUT=" in e or
               (set(_entry_groups(e.strip().rstrip(","))) & set(g3d))]
    lines = [
        "# Foutschatter (CALC_ERREUR, residu ERME; bridge 'error_estimator').",
        "# Eigen model (alleen volume-elementen en hun randvlakken), eigen",
        "# last (alle vlak- en volumelasten in een AFFE_CHAR_MECA, PRES_REP ~0",
        "# op de vrije vlakken) en eigen resultaat res_err met de",
        "# verplaatsingen van res.",
        "model_err = AFFE_MODELE(",
        "    MAILLAGE=mesh,",
        "    AFFE=(",
    ] + affe + [
        "    ),",
        ")",
        "fieldmat_err = AFFE_MATERIAU(",
        "    MAILLAGE=mesh,",
        "    MODELE=model_err,",
        "    AFFE=(",
        "".join(entries).rstrip(chr(10)),
        "    ),",
        varc.rstrip(chr(10)),
        ")",
        _render_char_meca("load_err", "AFFE_CHAR_MECA", merged).replace(
            "MODELE=model,", "MODELE=model_err,").rstrip(chr(10)),
        "u_all = CREA_CHAMP(TYPE_CHAM='NOEU_DEPL_R', OPERATION='EXTR',",
        "                   RESULTAT=res, NOM_CHAM='DEPL', NUME_ORDRE=1)",
        "u_err = CREA_CHAMP(TYPE_CHAM='NOEU_DEPL_R', OPERATION='ASSE',",
        "                   MODELE=model_err,",
        "                   ASSE=_F(TOUT='OUI', CHAM_GD=u_all,",
        "                           NOM_CMP=('DX', 'DY', 'DZ')))",
        "res_err = CREA_RESU(",
        "    OPERATION='AFFE',",
        "    TYPE_RESU='EVOL_ELAS',",
        "    AFFE=_F(NOM_CHAM='DEPL', CHAM_GD=u_err, MODELE=model_err,",
        "            CHAM_MATER=fieldmat_err, INST=0.0),",
        ")",
        "res_err = CALC_CHAMP(reuse=res_err, RESULTAT=res_err,",
        "                     CONTRAINTE=('SIGM_ELNO', ))",
        "res_err = CALC_ERREUR(",
        "    reuse=res_err,",
        "    RESULTAT=res_err,",
        "    OPTION=('ERME_ELEM', 'ERME_ELNO', 'ERME_NOEU'),",
        "    EXCIT=_F(CHARGE=load_err),",
        ")",
        "",
    ]
    lines = [l for l in lines if l != ""] + [""]
    log("INFO: Foutschatter aan: CALC_ERREUR ERME op {0} (lasten: {1}).".format(
        ", ".join(g3d), ", ".join(merged)))
    return "\n".join(lines) + "\n"


def _warn_overlapping_faces(model_data, merged):
    """WARNING als twee vlaklasten van dezelfde soort een vlak delen: in een
    AFFE_CHAR_MECA overschrijft de laatste de eerste (carte), dus de
    schatter ziet daar maar een van beide (de oplossing telt ze wel op)."""
    face_list = model_data.get("group_face_list", {})
    for kw in _ERME_FACE_KEYWORDS:
        seen = {}
        clash = set()
        for k, entry in enumerate(merged.get(kw, [])):
            for g in _entry_groups(entry):
                for face in face_list.get(g, []):
                    key = frozenset(face["nodes"])
                    if key in seen and seen[key][0] != k:
                        clash.update((seen[key][1], g))
                    seen.setdefault(key, (k, g))
        if clash:
            log(tr("WARNING: Foutschatter: {0} op overlappende vlakken ({1}); "
                   "de schatter neemt daar maar een van de lasten mee, de fout "
                   "op die vlakken is minder betrouwbaar.",
                   "WARNING: Error estimator: {0} on overlapping faces ({1}); "
                   "the estimator only takes one of the loads there, the "
                   "error on those faces is less reliable.").format(
                       kw, ", ".join(sorted(clash))))


def _table_node_groups(concept, group_ma):
    """
    Knopengroepen voor een tabel met GROUP_MA: een per mailles-groep,
    bijv. ['tab_sipm_n1', 'tab_sipm_n2']. Een groep per _F, want
    CREA_GROUP_NO met GROUP_MA=(meerdere groepen) gaf in Code-Aster 17.4
    <EXCEPTION> JEVEUX_10 ("Le nom demande existe deja dans la base
    &&SSCGNO.LITMP2"), gezien in Mecway met 6 balkgroepen.
    """
    return ["{0}_n{1}".format(concept, i + 1) for i in range(len(group_ma))]


def _postreleve(concept, intitule, resultat, nom_cham, cmp_line,
                result_selector, group_ma=None):
    """Een POST_RELEVE_T-aanroep (OPERATION='EXTRACTION') als regels."""
    lines = [
        "{0} = POST_RELEVE_T(".format(concept),
        "    ACTION=_F(",
        "        INTITULE='{0}',".format(_intitule(intitule)),
        "        OPERATION='EXTRACTION',",
        "        RESULTAT={0},".format(resultat),
        "        NOM_CHAM='{0}',".format(nom_cham),
        "        {0},".format(cmp_line),
        "        {0},".format(result_selector),
    ]
    if group_ma:
        # Met GROUP_MA moet elke knoop uit GROUP_NO aan een maille van die
        # groep vastzitten. Met 'all_nodes' gaf Code-Aster 17.4
        # <EXCEPTION> POSTRELE_40 ("Le noeud numero 1 n'est pas connecte a
        # la maille ..."). De knopengroep maakt _build_defigroup_block aan.
        lines += [
            "        GROUP_NO={0},".format(_fmt_groups(
                _table_node_groups(concept, group_ma))),
            "        GROUP_MA={0},".format(_fmt_groups(group_ma)),
        ]
    else:
        lines.append("        GROUP_NO='all_nodes',")
    lines += ["    ),", ")", ""]
    return lines


def _result_tables(model_data, with_plastic=False, with_velocity=False):
    """
    Lijst van (concept, intitule, resultaat, nom_cham, cmp_line, group_ma)
    voor alle POST_RELEVE_T-tabellen. Gedeeld door _build_postreleve_block
    en _build_impr_table_block zodat beide altijd overeenkomen.

    De INTITULE moet overeenkomen met een sleutel in RESULT_FIELD_SPECS
    of STRUCT_FIELD_SPECS in bridge_from_aster.py.
    """
    g3d, gsh, gbm = _result_groups(model_data)
    tables = [("tab_depl", "displacements", "res", "DEPL",
               "TOUT_CMP='OUI'", None)]
    if with_velocity:
        # DYNA_NON_LINE archiveert VITE en ACCE naast DEPL (U4.53.01).
        tables.append(("tab_vite", "velocities", "res", "VITE",
                       "NOM_CMP=('DX', 'DY', 'DZ')", None))
    if g3d:
        tables += [
            ("tab_sigm", "stresses", "res", "SIGM_NOEU",
             "TOUT_CMP='OUI'", None),
            ("tab_vmis", "vonmises", "res", "SIEQ_NOEU",
             "NOM_CMP=('VMIS', )", None),
        ]
    if gsh:
        tables += [
            ("tab_vmss", "vmis_shell_sup", "res_sup", "SIEQ_NOEU",
             "NOM_CMP=('VMIS', )", None),
            ("tab_vmsm", "vmis_shell_moy", "res_moy", "SIEQ_NOEU",
             "NOM_CMP=('VMIS', )", None),
            ("tab_vmsi", "vmis_shell_inf", "res_inf", "SIEQ_NOEU",
             "NOM_CMP=('VMIS', )", None),
        ]
    if gbm:
        tables.append(("tab_sipm", "beam_sixx", "res", "SIPM_ELNO",
                       "TOUT_CMP='OUI'", gbm))
    tables.append(("tab_reac", "reactions", "res", "REAC_NODA",
                   "TOUT_CMP='OUI'", None))
    if with_plastic and g3d:
        tables.append(("tab_epsp", "plastic_strain", "res", "EPSP_NOEU",
                       "TOUT_CMP='OUI'", None))
        # Geen VARI_NOEU bij kinematische versteviging (zie
        # _build_calc_champ_block).
        if not any((p.get("plastic_bilinear") or {}).get("kinematic")
                   for p in model_data["materials"].values()):
            tables.append(("tab_vari", "plastic_strain_eq", "res",
                           "VARI_NOEU", "NOM_CMP=('V1', )", None))
    return tables


def _build_postreleve_block(model_data, result_selector="NUME_ORDRE=1",
                            with_plastic=False, with_velocity=False):
    """
    Genereer POST_RELEVE_T-aanroepen (zie _result_tables).

    Parameters
    ----------
    result_selector : str
        Code-Aster selector voor de te extracten stap, bijv.
        "NUME_ORDRE=1" voor MECA_STATIQUE of "INST=3.0" voor het laatste
        tijdstip van een STAT_NON_LINE. POST_CHAMP behoudt de nummering
        (testcase ssls131a gebruikt NUME_ORDRE=1 op het POST_CHAMP-resultaat).
    with_plastic : bool
        Voeg tab_epsp (plastische strain tensor) en tab_vari (V1 =
        equivalente plastische strain) toe (alleen bij 3D-elsets).

    Alarm POSTRELE_70 bij 'stresses' in een model met balken/schalen:
        op0051.F90 (v17.4.0) geeft dit alarm voor SIGM_NOEU zodra het model
        structuurelementen bevat en REPERE niet 'LOCAL' is. De waarden
        worden ongewijzigd uit het veld gehaald; SIGM_NOEU bestaat hier
        alleen op 3D-elementen en staat daar in het globale assenstelsel.
        REPERE='LOCAL' wordt bewust NIET gebruikt: voor een knopenlijst is
        dat het raak-/normaalvlak van het pad (U4.81.21 par. 5.2.4).
    """
    tables = _result_tables(model_data, with_plastic, with_velocity)
    lines = []
    # De knopengroepen voor tabellen met GROUP_MA maakt
    # _build_defigroup_block() aan, vóór de solve.
    for concept, intitule, resultat, nom_cham, cmp_line, group_ma in tables:
        lines += _postreleve(concept, intitule, resultat, nom_cham,
                             cmp_line, result_selector, group_ma)
    return "\n".join(lines) + "\n"


def results_file(work_dir):
    """
    Pad van het resultaatbestand van de lopende run (result_route "liml"):
    <model>_<run_id>_results.xml. Het blijft na het inladen staan, zodat de
    resultaten later opnieuw in te laden zijn (knop Resultaten...).
    """
    return os.path.join(work_dir, run_name(RESULTS_SUFFIX))


def _results_route(work_dir, model_data, postreleve_block, impr_table_block,
                   precision, static=None, fields=None, extra=""):
    """
    result_route "liml": geen POST_RELEVE_T-tabellen, maar
    aster_results_export.py (draait in de Code-Aster-job, numpy) schrijft
    Mecway's eigen <results> naar results_file(); MecwayAsterBridgeMain
    plakt het in de .liml en opent die. "tabel": ongewijzigd.
    static: True/False geeft export_results(static=...) door (bijv.
    stationair thermisch: EVOL_THER, dat _is_static niet herkent); None =
    automatisch. fields: lijst groepen voor export_results(fields=...);
    None = alles wat in het resultaat staat. extra: tekst achter de
    argumenten (bijv. ", node_fields=..." van bridge_fatigue).
    Returns (postreleve_block, impr_table_block).
    """
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        return postreleve_block, impr_table_block
    scripts = os.path.dirname(os.path.abspath(__file__))
    fragment = results_file(work_dir)
    block = (
        "# Resultaten in Mecway's eigen formaat (bridge: result_route='liml')@N"
        "import sys@N"
        "sys.path.insert(0, {scripts})@N"
        "import aster_results_export@N"
        "aster_results_export.export_results(@N"
        "    res, {fragment}, {liml},@N"
        "    extra_results=dict((k, globals()[k]) for k in@N"
        "                       ('res_sup', 'res_moy', 'res_inf',@N"
        "                        'res_flux', 'res_err')@N"
        "                       if k in globals()),@N"
        "    precision='{precision}'{static}{fields}{extra})@N"
    ).replace("@N", chr(10)).format(
        scripts=_py_str(scripts), fragment=_py_str(fragment),
        liml=_py_str(model_data.get("liml_path", "")), precision=precision,
        static="" if static is None else ", static={0}".format(bool(static)),
        fields="" if fields is None else ", fields={0!r}".format(
            [str(f) for f in fields]), extra=extra)
    return "#-- tabellen niet nodig (result_route='liml') --" + chr(10), block


def _build_impr_table_block(model_data, with_plastic=False,
                            with_velocity=False):
    """
    IMPR_TABLE voor precies de tabellen uit _build_postreleve_block()
    naar UNITE=8 (.resu-bestand).
    """
    lines = []
    for table in _result_tables(model_data, with_plastic, with_velocity):
        lines += [
            "IMPR_TABLE(TABLE={0}, UNITE=8, FORMAT='TABLEAU',".format(
                table[0]),
            "           SEPARATEUR=' ', COMMENTAIRE='#')",
        ]
    return "\n".join(lines) + "\n"


def _build_impr_resu_block(model_data, with_plastic=False):
    """
    IMPR_RESU naar MED (study.rmed, ParaView/Salome), alleen met de
    instelling "med_export": Mecway krijgt de resultaten via de .liml (of
    de tabellen), een MED-bestand van honderden MB is anders overbodig.
    Een GMSH-export bestaat niet meer (las niemand; 5,6 GB bij
    ProfielBuigen).
    """
    if not CONFIG_BRIDGE.get("med_export", False):
        return "#-- geen MED-export (instelling med_export uit) --\n"
    return "\n".join([
        "IMPR_RESU(",
        "    FORMAT='MED',",
        "    UNITE=80,",
        "    RESU=_F(",
        "        RESULTAT=res,",
        "        NOM_CHAM={0},".format(
            _build_impr_resu_cham(model_data, with_plastic)),
        "    ),",
        ")",
        ""])


def _export_result_lines(work_dir, resu_name):
    """
    Uitvoerbestanden in study.export: de .resu (UNITE 8) alleen voor de
    tabelroute, study.rmed (UNITE 80) alleen met "med_export". Zo blijven
    er geen lege of overbodige bestanden in de werkmap achter.
    """
    lines = []
    if CONFIG_BRIDGE.get("result_route", "liml") == "tabel":
        lines.append("F resu {0} R 8".format(os.path.join(work_dir, resu_name)))
    if CONFIG_BRIDGE.get("med_export", False):
        lines.append("F rmed {0} R 80".format(
            os.path.join(work_dir, run_name(".rmed"))))
    return "".join("\n" + line for line in lines)


def _build_impr_resu_cham(model_data, with_plastic=False):
    """
    NOM_CHAM-tuple voor IMPR_RESU MED: alleen velden die in 'res'
    daadwerkelijk berekend zijn.
    """
    g3d, _gsh, _gbm = _result_groups(model_data)
    champs = ["DEPL", "REAC_NODA"]
    if g3d:
        champs += ["SIGM_NOEU", "SIEQ_NOEU"]
        if with_plastic:
            champs.append("EPSP_NOEU")
            # Geen VARI_NOEU bij kinematische versteviging (zie
            # _build_calc_champ_block).
            if not any((p.get("plastic_bilinear") or {}).get("kinematic")
                       for p in model_data["materials"].values()):
                champs.append("VARI_NOEU")
    return "({0},)".format(", ".join("'{0}'".format(c) for c in champs))


# ==========================================
# HULPFUNCTIE: DEFI_MATERIAU
# ==========================================
def _thermal_active(model_data):
    """True als thermische rek meedoet: Mecway <thermalstress> (manual v33
    par. 9.25: zonder thermal stress geen thermische belasting)."""
    return model_data.get("thermal_stress") is not None


def _material_concepts(model_data):
    """
    Unieke Code-Aster-conceptnaam per Mecway-materiaal: MAT_1, MAT_2, ...
    (volgorde van model_data["materials"]), zoals MTH1.. in bridge_thermal.
    Afgeleid uit de naam (re.sub + [:16]) gaf botsingen
    ("Constructiestaal_S235" en "..._S355_buis" -> hetzelfde concept, stil
    het verkeerde materiaal) en een SyntaxError bij niet-ASCII-namen. De
    Mecway-naam staat als commentaar erboven. Gecached in model_data, zodat
    DEFI_MATERIAU, AFFE_MATERIAU en TRACTION (TRAC_<n>) dezelfde nummers
    gebruiken.
    """
    names = model_data.get("_mat_concepts")
    if names is None or list(names) != list(model_data["materials"]):
        names = OrderedDict()
        for i, mat_name in enumerate(model_data["materials"]):
            names[mat_name] = "MAT_{0}".format(i + 1)
        model_data["_mat_concepts"] = names
    return names


def _mat_comment(mat_name):
    """Commentaarregel met de Mecway-naam. Alleen ASCII (overige tekens ->
    '?'): ingevoerd toen de .comm nog in de systeemcodering werd geschreven
    (een niet-UTF-8-byte gaf ook in commentaar een SyntaxError, gezien:
    'Ålu' in cp1252). Sinds _write_comm is de .comm UTF-8; ASCII blijft als
    extra zekerheid. Witruimte samengevoegd: een regeleinde in de naam zou
    de .comm breken."""
    name = "".join(c if 32 <= ord(c) < 127 else "?"
                   for c in " ".join(mat_name.split()))
    return "# materiaal '{0}'\n".format(name)


def _build_materials_block(model_data, analysis, plastic_func_map=None):
    """
    DEFI_MATERIAU per materiaal (U4.43.01):
      ELAS E, NU, RHO (altijd, ook 0: PESANTEUR);
      ALPHA alleen met thermal stress (anders alarmen zonder AFFE_VARC);
      AMOR_ALPHA/AMOR_BETA bij Rayleigh-demping in DYNA_NON_LINE: Code-Aster
        C = AMOR_ALPHA K + AMOR_BETA M (U4.43.01 par. 4 "ELAS"), Mecway
        C = alpha M + beta K (manual v33 par. 9.26), dus AMOR_ALPHA =
        Mecway beta en AMOR_BETA = Mecway alpha;
      TRACTION bij een hardingscurve (plastic_func_map);
      CABLE bij tension only (EC_SUR_E: Code-Aster-standaard 1e-4, de
        drukstijfheid is dan 1e-4 E; 0 kan de matrix singulier maken,
        U4.43.01 CABLE). Mecway heeft geen drukstijfheid.
    Plus DIS_CONTACT per gap-groep (_prepare_gaps).
    """
    plastic_func_map = plastic_func_map or {}
    thermal = _thermal_active(model_data)
    rayleigh = model_data.get("rayleigh")
    if rayleigh and analysis.get("solver_command") != "DYNA_NON_LINE":
        if analysis.get("solver_command") != "DYNA_VIBRA":
            # DYNA_VIBRA (modale basis, harmonisch): de Rayleigh-demping
            # gaat als modale demping of dempingsmatrix mee, niet via het
            # materiaal.
            # Complexe modes en het responsspectrum nemen de demping elders
            # mee (dempingsmatrix, xi per mode); hier gaat het alleen om
            # AMOR_ALPHA/AMOR_BETA in DEFI_MATERIAU.
            log("INFO: Rayleigh-demping niet als materiaaldemping "
                "(AMOR_ALPHA/AMOR_BETA) in DEFI_MATERIAU; die gebruikt alleen "
                "DYNA_NON_LINE. Complexe modes en het responsspectrum nemen de "
                "demping zelf mee; in de andere analyses telt ze niet.")
        rayleigh = None
    # Expliciet: Rayleigh-demping verkleint de stabiele stap; dat neemt
    # _critical_time_step mee (_damped_step_factor).
    out = ""
    concepts = _material_concepts(model_data)
    for mat_name, props in model_data["materials"].items():
        concept = concepts[mat_name]
        elas = _elas_args(props, thermal, rayleigh)
        extra = []
        if mat_name in plastic_func_map:
            extra.append("    TRACTION=_F(SIGM={0}),\n".format(
                plastic_func_map[mat_name]))
        bil = props.get("plastic_bilinear")
        if bil:
            # U4.43.01 ECRO_LINE: SY en D_SIGM_EPSI (helling na de
            # vloeigrens), voor VMIS_ISOT_LINE en VMIS_CINE_LINE.
            extra.append("    ECRO_LINE=_F(D_SIGM_EPSI={0!r}, SY={1!r}),\n"
                         .format(bil["et"], bil["sy"]))
        if props.get("tension_only"):
            extra.append("    CABLE=_F(EC_SUR_E=1.0e-4),\n")
        out += _mat_comment(mat_name)
        if extra:
            out += "{0} = DEFI_MATERIAU(\n    ELAS=_F({1}),\n{2})\n".format(
                concept, elas, "".join(extra))
        else:
            out += "{0} = DEFI_MATERIAU(ELAS=_F({1}),)\n".format(
                concept, elas)
    for group, gap in model_data.get("gap_groups", {}).items():
        # DIS_CHOC op SEG2: contact zodra de knoopafstand langs de
        # elementas <= DIST_1 + DIST_2 (nagelopen met een run, Code-Aster
        # 17.4: SEG2 van 0,1 m met DIST_1 = DIST_2 = 0 sloot pas na
        # 0,1 m). _prepare_gaps kiest DIST_1 + DIST_2 = L - speling.
        out += ("MAT_{0} = DEFI_MATERIAU(DIS_CONTACT=_F(RIGI_NOR={1!r}, "
                "DIST_1={2!r}, DIST_2={2!r}),)\n").format(
                    group, gap["k"], gap["dist"] / 2.0)
    return out


def _elas_args(props, thermal, rayleigh, factor=1.0):
    """Tekst binnen ELAS=_F(...): E (x factor, voor het slappe materiaal
    van bridge_failure), NU, RHO en zo nodig ALPHA en Rayleigh-demping."""
    e_mod = props["E"] if factor == 1.0 else repr(props["E"] * factor)
    elas = "E={0}, NU={1}, RHO={2}".format(e_mod, props["NU"],
                                           props.get("rho", 0.0))
    if thermal:
        elas += ", ALPHA={0!r}".format(props.get("Texp", 0.0))
    if rayleigh:
        elas += ", AMOR_ALPHA={0!r}, AMOR_BETA={1!r}".format(
            rayleigh["beta"], rayleigh["alpha"])
    return elas


def _prepare_gaps(model_data):
    """
    Gap-elementen (Mecway manual v33 par. 7.9): unilateraal contact tussen
    twee knopen langs U (standaard knoop 1 -> 2), gesloten bij een
    naderingsverplaatsing >= initial clearance c (standaard 0, ook als de
    knopen uit elkaar liggen). Code-Aster DIS_CHOC sluit bij afstand <=
    DIST_1 + DIST_2, dus DIST_1 + DIST_2 = L - c per element; elementen met
    dezelfde waarde delen een groep en een DEFI_MATERIAU.
    Niet vertaald (gemeld): U tegen de richting knoop 1 -> 2 in (trek-
    gap), U schuin op het element, samenvallende knopen, c > L.
    """
    nodes = model_data.get("mesh_nodes", {})
    u_axes = model_data.get("elem_u_axes", {})
    gaps = OrderedDict()
    extra = model_data.setdefault("extra_ma_groups", OrderedDict())
    for eid, shape, enodes, elset in model_data.get("mesh_elements", []):
        sec = model_data.get("discrete_sections", {}).get(
            model_data.get("_elem_elset", {}).get(eid, elset))
        if not sec or sec["kind"] != "gap":
            continue
        p1, p2 = nodes[enodes[0]], nodes[enodes[1]]
        d = [p2[k] - p1[k] for k in range(3)]
        length = math.sqrt(sum(c * c for c in d))
        reason = None
        if length <= 0.0:
            reason = tr("samenvallende knopen", "coincident nodes")
        elif eid in u_axes:
            u = u_axes[eid]
            nu = math.sqrt(sum(c * c for c in u))
            cos = sum(a * b for a, b in zip(u, d)) / (nu * length) \
                if nu > 0.0 else 0.0
            if cos < 1.0 - 1.0e-6:
                reason = tr("U-as niet langs knoop 1 -> 2 (trek-gap of "
                            "schuine gap)",
                            "U axis not along node 1 -> 2 (tension gap or "
                            "oblique gap)")
        dist = length - sec["clearance"]
        if reason is None and dist < 0.0:
            reason = tr("speling groter dan de elementlengte",
                        "clearance larger than the element length")
        if reason:
            model_data.setdefault("skipped_loads", []).append(
                tr("gap-element {0}", "gap element {0}").format(eid))
            log(tr("ERROR: Gap-element {0}: {1}; DIS_CHOC kan dat niet. "
                   "NIET meegenomen (element zonder stijfheid).",
                   "ERROR: Gap element {0}: {1}; DIS_CHOC cannot do that. "
                   "NOT included (element without stiffness).").format(
                    eid, reason))
            continue
        key = (round(dist, 12), sec["k"])
        if key not in gaps:
            gaps[key] = "BRGAP{0}".format(len(gaps) + 1)
            model_data.setdefault("gap_groups", OrderedDict())[gaps[key]] = {
                "k": sec["k"], "dist": dist}
            extra[gaps[key]] = []
        extra[gaps[key]].append(eid)


# ==========================================
# HULPFUNCTIE: AFFE_MATERIAU
# ==========================================
def _build_fieldmat_block(model_data, t_ramp=None):
    """
    AFFE_MATERIAU-aanroep: per elset het materiaal (MAT_<n>,
    _material_concepts).

    Overgeslagen elsets:
      - veer-elsets (DIS_T): de stijfheid zit in AFFE_CARA_ELEM DISCRET;
        Code-Aster geeft een ALARM bij ELAS op een DISCRET-element.
      - elsets waarvan het materiaal niet in model_data["materials"] staat
        (bijv. een niet-ondersteund mechanisch type): er is dan geen
        DEFI_MATERIAU voor, dus MAT_<n> zou ongedefinieerd zijn.

    Zonder elsets, of als er geen toewijzing overblijft, krijgt het hele
    model het eerste materiaal (TOUT='OUI'), zodat AFFE nooit leeg is.
    """
    materials        = model_data["materials"]
    concepts         = _material_concepts(model_data)
    spring_mat_names = set(model_data.get("spring_materials", {}).keys())
    entries = []
    discrete_mat_names = set(model_data.get("line_discretes", {}).keys())
    for elset_name, mat_name in model_data["elsets"].items():
        if mat_name in spring_mat_names or mat_name in discrete_mat_names:
            log("INFO: Elset '{0}' (veer/gap/demper, DIS_T) overgeslagen "
                "in AFFE_MATERIAU.".format(elset_name))
            continue
        if mat_name not in materials:
            log(tr("WARNING: Elset '{0}': materiaal '{1}' is niet "
                   "gedefinieerd (geen DEFI_MATERIAU); elset krijgt geen "
                   "materiaal.",
                   "WARNING: Elset '{0}': material '{1}' is not defined "
                   "(no DEFI_MATERIAU); elset gets no material.").format(
                    elset_name, mat_name))
            continue
        entries.append("        _F(GROUP_MA='{0}', MATER={1}),\n".format(
            elset_name, concepts[mat_name]))

    if not entries and materials:
        first_mat  = list(materials.keys())[0]
        entries.append("        _F(TOUT='OUI', MATER={0}),\n".format(
            concepts[first_mat]))
        log("INFO: Geen elset-materiaaltoewijzing; materiaal '{0}' globaal "
            "toegewezen (TOUT='OUI').".format(first_mat))
    for group in model_data.get("gap_groups", {}):
        entries.append("        _F(GROUP_MA='{0}', MATER=MAT_{0}),\n".format(
            group))

    temp_block, varc = _build_temperature_field(model_data, t_ramp)
    if not entries:
        # Alleen discrete elementen (veren, dempers): AFFE_MATERIAU vraagt
        # AFFE of CHAM_MATER (<EXCEPTION> SUPERVIS_4 met een lege AFFE,
        # Code-Aster 17.4) en STAT_NON_LINE/DYNA_NON_LINE vragen CHAM_MATER
        # (catalogus). Een leeg materiaal zonder invloed op de discreten.
        temp_block += "MAT_BRLEEG = DEFI_MATERIAU(ELAS=_F(E=1.0, NU=0.0),)\n"
        entries.append("        _F(TOUT='OUI', MATER=MAT_BRLEEG),\n")
    # Bewaard voor de AFFE_MATERIAU's van de bezwijklus (bridge_failure)
    model_data["_fieldmat_parts"] = (list(entries), varc)
    return temp_block + (
        "fieldmat = AFFE_MATERIAU(\n"
        "    MAILLAGE=mesh,\n"
        "    MODELE=model,\n"
        "    AFFE=(\n"
        + "".join(entries) +
        "    ),\n" + varc + ")\n"
    )


# Waarden per knoop in het temperatuurveld (Node temperature) en de
# temperatuur van knopen die de bridge in de job toevoegt. Indeling van het
# veld: getValuesWithDescription(cmp) geeft (waarden, (knopen, cmps)), zoals
# in MacroCommands/Contrib/diffusion_H2.py (v17.4); setValues(array) zet
# alle waarden in de volgorde van getValues() (idem). Met alleen TEMP op
# elke knoop is dat een waarde per knoop; dat controleert de functie.
# Nieuwe knopen (index >= aantal Mecway-knopen): een middenknoop van een
# rand (LINE_QUAD) krijgt het gemiddelde van de eindknopen, de middenknoop
# van QUAD9/TRIA7 (laatste knoop van de cel) de waarde van QUAD8/TRIA6 in
# het midden (vormfuncties: hoeken -1/4 en randmiddens 1/2, resp. -1/9 en
# 4/9). Knoopnummers van getConnectivity() zijn 0-gebaseerd, zoals in
# _LQ_NODEGROUPS.
_NODE_TEMPS_FUNC = (
    "def _bridge_node_temps(fld, mesh, temps, n_mw):\n"
    "    import numpy as np\n"
    "    vals = np.array(fld.getValues(), dtype=float)\n"
    "    tv, desc = fld.getValuesWithDescription('TEMP')\n"
    "    nodes = list(desc[0])\n"
    "    nn = mesh.getNumberOfNodes()\n"
    "    if (len(tv) != len(vals) or len(nodes) != nn or\n"
    "            not np.allclose(np.asarray(tv), vals)):\n"
    "        raise ValueError('BRIDGE: onverwachte indeling van het '\n"
    "                         'temperatuurveld (Node temperature)')\n"
    "    base = min(nodes)\n"
    "    pos = np.zeros(nn, dtype=int)\n"
    "    for i, n in enumerate(nodes):\n"
    "        pos[n - base] = i\n"
    "    for value, nids in temps.items():\n"
    "        vals[pos[np.asarray(nids, dtype=int) - 1]] = value\n"
    "    if nn > n_mw:\n"
    "        xyz = np.asarray(mesh.getCoordinates().getValues(),\n"
    "                         dtype=float).reshape(-1, 3)\n"
    "        scale = 1.0e9 / max(1.0e-30, float(np.abs(xyz).max()))\n"
    "        key = lambda p: tuple(int(round(c * scale)) for c in p)\n"
    "        conn = mesh.getConnectivity()\n"
    "        mids = {}\n"
    "        centres = {}\n"
    "        for cell in conn:\n"
    "            if len(cell) in (7, 9) and cell[-1] >= n_mw:\n"
    "                centres[cell[-1]] = cell\n"
    "            old = [n for n in cell if n < n_mw]\n"
    "            for i in range(len(old)):\n"
    "                for j in range(i + 1, len(old)):\n"
    "                    a, b = old[i], old[j]\n"
    "                    mids[key(0.5 * (xyz[a] + xyz[b]))] = (a, b)\n"
    "        n_mid = 0\n"
    "        for m in range(n_mw, nn):\n"
    "            ab = None if m in centres else mids.get(key(xyz[m]))\n"
    "            if ab is not None:\n"
    "                vals[pos[m]] = 0.5 * (vals[pos[ab[0]]] + vals[pos[ab[1]]])\n"
    "                n_mid += 1\n"
    "        for m, cell in centres.items():\n"
    "            nc = 4 if len(cell) == 9 else 3\n"
    "            wc, wm = (-0.25, 0.5) if nc == 4 else (-1.0 / 9, 4.0 / 9)\n"
    "            vals[pos[m]] = (wc * sum(vals[pos[n]] for n in cell[:nc]) +\n"
    "                            wm * sum(vals[pos[n]] for n in cell[nc:-1]))\n"
    "        print('BRIDGE TEMP: {0} middenknopen, {1} celmiddens '\n"
    "              'geinterpoleerd'.format(n_mid, len(centres)))\n"
    "    fld.setValues(vals)\n"
    "\n"
)


def _check_temperature_conflicts(model_data, node_temps):
    """
    WARNING als een knoop met een Node temperature ook in een selectie met
    een andere temperature2-waarde ligt: Mecway rekent dan niet
    ("Conflicting temperatures on node", headless gezien met Mecway 34);
    de bridge gebruikt de Node temperature (_bridge_node_temps na de
    AFFE's).
    """
    node_groups = model_data.get("node_groups", {})
    faces = model_data.get("group_face_list", {})
    elem_sel = model_data.get("element_selections", {})
    conn = model_data.get("_conn", {})
    clash = set()
    for t in model_data.get("temperatures", []):
        sel = t.get("selection")
        if sel in node_groups:
            nids = set(int(str(n).lstrip("N")) for n in node_groups[sel])
        elif sel in faces:
            nids = set(n for f in faces[sel] for n in f.get("nodes", []))
        elif sel in elem_sel:
            nids = set(n for e in elem_sel[sel] if e in conn
                       for n in conn[e][1])
        else:
            continue
        for n in nids:
            v = node_temps.get(n)
            if v is not None and abs(v - t["value"]) > 1e-9 * max(
                    1.0, abs(v)):
                clash.add(n)
    if clash:
        log(tr("WARNING: Knoop/knopen {0} hebben een Node temperature en een "
               "andere Temperature; Mecway rekent dan niet (\"Conflicting "
               "temperatures on node\"). De bridge gebruikt de Node "
               "temperature.",
               "WARNING: Node(s) {0} have a Node temperature and a "
               "different Temperature; Mecway does not solve then "
               "(\"Conflicting temperatures on node\"). The bridge uses the "
               "Node temperature.").format(
                   ", ".join(str(n) for n in sorted(clash)[:10])))


def _build_temperature_field(model_data, t_ramp=None):
    """
    Thermische rek (Mecway thermal stress + temperature, manual v33 par.
    9.23/9.25): knopen zonder temperatuur staan op de referentie-
    temperatuur. Code-Aster: knoopveld TEMP (CREA_CHAMP NOEU_TEMP_R AFFE,
    later AFFE wint) als commandovariabele (AFFE_MATERIAU AFFE_VARC
    NOM_VARC='TEMP', VALE_REF = referentie; U4.43.03), en ALPHA in ELAS.
    Code-Aster interpoleert het knoopveld in het element; Mecway 34 ook
    (headless gezien, LS-08b; de manual spreekt van het elementgemiddelde,
    KNOWN_BUGS 17).
    Node temperature (temperature3, model_data["node_temperatures"]):
    de waarden per knoop zet _bridge_node_temps
    in het veld (na de AFFE's; Mecway staat geen twee verschillende
    temperaturen op een knoop toe, de volgorde doet er dus niet toe).
    Knopen die de bridge in de job toevoegt (LINE_QUAD-middenknopen,
    middenknoop van QUAD9/TRIA7 bij COQUE_3D) krijgen dan de
    geinterpoleerde temperatuur van de Mecway-knopen, zoals het veld op
    het oorspronkelijke mesh.
    Returns (blok met CREA_CHAMP, "    AFFE_VARC=...,\\n") of ("", "").
    """
    ts = model_data.get("thermal_stress")
    temps = model_data.get("temperatures", [])
    node_temps = model_data.get("node_temperatures") or {}
    if ts is None:
        if temps or node_temps:
            log("INFO: Temperaturen zonder thermal stress: geen thermische "
                "rek (zoals Mecway, manual v33 par. 9.25).")
        return "", ""
    tref = ts["tref"]
    affe = ["_F(TOUT='OUI', NOM_CMP='TEMP', VALE={0!r})".format(tref)]
    for t in temps:
        affe.append("_F({0}='{1}', NOM_CMP='TEMP', VALE={2!r})".format(
            t["target"], t["selection"], t["value"]))
    block = (
        "temp_fld = CREA_CHAMP(\n"
        "    TYPE_CHAM='NOEU_TEMP_R',\n"
        "    OPERATION='AFFE',\n"
        "    MAILLAGE=mesh,\n"
        "    AFFE=(\n        {0},\n    ),\n"
        ")\n").format(",\n        ".join(affe))
    if node_temps:
        _check_temperature_conflicts(model_data, node_temps)
    new_nodes = bool(model_data.get("line_quad") or
                     model_data.get("shell_upgrades"))
    if node_temps or (new_nodes and temps):
        by_value = OrderedDict()
        for nid in sorted(node_temps):
            by_value.setdefault(node_temps[nid], []).append(
                "{0}".format(nid))
        data = "".join("    {0!r}: {1},\n".format(
            v, _fmt_seq(nids, per_line=12, indent="        "))
            for v, nids in by_value.items())
        block += _NODE_TEMPS_FUNC + (
            "# Node temperature (Mecway temperature3) per knoop: "
            "{{K: (Mecway-knoopnummers)}}\n"
            "_bridge_node_temps(temp_fld, mesh, {{\n{0}}}, {1})\n"
        ).format(data, len(model_data.get("mesh_nodes", {})))
    block += "\n"
    if t_ramp is None:
        varc = ("    AFFE_VARC=_F(TOUT='OUI', NOM_VARC='TEMP', "
                "CHAM_GD=temp_fld, VALE_REF={0!r}),\n").format(tref)
        return block, varc
    # STAT_NON_LINE: een constant veld vanaf t = 0 gaf alarm
    # MECANONLINE2_97 ("à l'état initial ... déformation anélastique non
    # nulle ... on ne prend pas en compte les éventuelles contraintes
    # incompatibles", Code-Aster 17.4). Daarom een EVOL_THER (CREA_RESU
    # AFFE, U4.44.12) van de referentie op t = 0 lineair naar het veld op
    # t_ramp (eindtijd), zoals een belasting die oploopt.
    block += (
        "temp_ref = CREA_CHAMP(\n"
        "    TYPE_CHAM='NOEU_TEMP_R',\n"
        "    OPERATION='AFFE',\n"
        "    MAILLAGE=mesh,\n"
        "    AFFE=_F(TOUT='OUI', NOM_CMP='TEMP', VALE={0!r}),\n"
        ")\n"
        "temp_evo = CREA_RESU(\n"
        "    OPERATION='AFFE',\n"
        "    TYPE_RESU='EVOL_THER',\n"
        "    AFFE=(\n"
        "        _F(NOM_CHAM='TEMP', CHAM_GD=temp_ref, INST=0.0),\n"
        "        _F(NOM_CHAM='TEMP', CHAM_GD=temp_fld, INST={1!r}),\n"
        "    ),\n"
        ")\n\n").format(tref, t_ramp)
    varc = ("    AFFE_VARC=_F(TOUT='OUI', NOM_VARC='TEMP', EVOL=temp_evo, "
            "VALE_REF={0!r}),\n").format(tref)
    return block, varc


# ==========================================
# HULPFUNCTIE: BC'S RENDEREN (gedeeld door alle builders)
# ==========================================
def _fmt_seq(items, per_line=8, indent="        "):
    """Tuple-notatie, na per_line items een nieuwe regel."""
    lines = []
    for i in range(0, len(items), per_line):
        lines.append(", ".join(items[i:i + per_line]))
    return "(" + (",\n" + indent).join(lines) + ",)"


def _render_bc(bc, aster_dict=None):
    """
    [_F-strings] voor een BC onder bc["aster_keyword"].

    - pin_weights (pinned support, bridge_mesh._pinned_to_mean): per
      richting LIAISON_DDL sum(w_i * u_i) = 0 over de knopen. NOEUD i.p.v.
      GROUP_NO: de volgorde van de knopen moet bij COEF_MULT passen.
    - Anders: _F(<target>='<groep>', sleutel=waarde, ...); zonder selectie
      (gravity) alleen de sleutels. aster_dict vervangt bc["aster_dict"]
      (constante of tijdsafhankelijke deel, zie _build_charges).
    """
    if bc.get("pin_weights"):
        pw = bc["pin_weights"]
        names = _fmt_seq(["'N{0}'".format(n) for n, w in pw])
        coefs = _fmt_seq(["{0!r}".format(w) for n, w in pw], per_line=4)
        return ["_F(NOEUD={0},\n        DDL=('{1}',)*{2},\n"
                "        COEF_MULT={3},\n        COEF_IMPO=0.0)".format(
                    names, ddl, len(pw), coefs)
                for ddl in ("DX", "DY", "DZ")]
    if aster_dict is None:
        aster_dict = bc["aster_dict"]
    parts = ", ".join("{0}={1}".format(k, v) for k, v in aster_dict.items())
    if bc["selection"]:
        return ["_F({0}='{1}', {2})".format(
            bc["aster_target"], bc["selection"], parts)]
    return ["_F({0})".format(parts)]


def _centre_node_groups(model_data):
    """
    {selectie: knoopgroep} voor LIAISON_OBLIQUE op een GROUP_MA met
    COQUE_3D-schalen (frictionless op schaalvlakken, schuine verplaatsing).
    Die cellen zijn in de job QUAD9/TRIA7 (MODI_MAILLE of LINE_QUAD); de
    middenknoop draagt alleen DRX/DRY/DRZ (catalogus: COQUE_3D, Code-Aster
    17.4: LIAISON_OBLIQUE DX daarop -> <EXCEPTION> CHARGES2_31). De groep
    met die middenknopen (DEFI_GROUP CRIT_NOEUD='CENTRE', catalogus
    defi_group.py v17.4) gaat in SANS_GROUP_NO (_build_charges).
    Gecached; het nummer volgt de volgorde van de bcs.
    """
    cached = model_data.get("_centre_groups")
    if cached is not None:
        return cached
    mods = model_data.get("elset_modelisations", {})
    elem_elset = model_data.get("_elem_elset", {})
    faces = model_data.get("group_face_list", {})
    taken = model_data.get("mesh_group_names", set())
    out = OrderedDict()
    for bc in model_data.get("bcs", []):
        sel = bc.get("selection")
        if (bc.get("skip") or not sel or sel in out
                or bc.get("oblique") is not None
                or bc.get("unil_zones") is not None
                or bc.get("aster_keyword") != "LIAISON_OBLIQUE"
                or bc.get("aster_target") != "GROUP_MA"):
            continue
        # Alleen schaalvlakken (de cellen zelf); een schaalrand (SEG3)
        # heeft geen middenknoop (lege groep: SOUSTRUC_38).
        eids = set(f["eid"] for f in faces.get(sel, [])
                   if f.get("kind") == "shellface")
        eids.update(model_data.get("element_selections", {}).get(sel, []))
        if any(mods.get(elem_elset.get(e)) == "COQUE_3D" for e in eids):
            n = len(out) + 1
            while "BRCT{0}".format(n) in taken:
                n += 1
            out[sel] = "BRCT{0}".format(n)
    model_data["_centre_groups"] = out
    return out


def _centre_rotation_entry(centre, values, sans):
    """LIAISON_OBLIQUE-entry voor de middenknopen (alleen DR*-componenten
    uit values, met dezelfde ANGL_NAUT), of [] zonder rotaties."""
    parts = ["GROUP_NO='{0}'".format(centre)]
    rot = [(k, v) for k, v in values.items() if k.startswith("DR")]
    if not rot:
        return []
    parts += ["{0}={1}".format(k, v) for k, v in rot]
    if "ANGL_NAUT" in values:
        parts.append("ANGL_NAUT={0}".format(values["ANGL_NAUT"]))
    parts += ["{0}={1}".format(k, v) for k, v in sans.items()]
    return ["_F({0})".format(", ".join(parts))]


# Sleutels die geen waarde zijn maar bij de waarden horen; ze gaan mee met
# het constante en het tijdsafhankelijke deel.
_BC_ATTRIBUTE_KEYS = ("ANGL_NAUT", "PLAN")


def _render_node_loads(node_loads, factors):
    """
    FORCE_NODALE-entries, een per knoop: sum_k factors[k] * f_ik.
    node_loads : {component: [(nid, (fx, fy, fz))]} (alle componenten met
    dezelfde knopen in dezelfde volgorde, bridge_mesh._moment_to_forces).
    """
    out = []
    comps = [c for c in node_loads if factors.get(c, 0.0) != 0.0]
    if not comps:
        return out
    for i, (n, _) in enumerate(node_loads[comps[0]]):
        f = [sum(factors[c] * node_loads[c][i][1][j] for c in comps)
             for j in range(3)]
        out.append("_F(NOEUD='N{0}', FX={1!r}, FY={2!r}, FZ={3!r})".format(
            n, f[0], f[1], f[2]))
    return out


# Belastingen (geen randvoorwaarden). Binnen een AFFE_CHAR_MECA overschrijft
# een latere occurrence op dezelfde knoop/maille een eerdere i.p.v. op te
# tellen (gezien met Code-Aster 17.4: van een moment met MX en MY in twee
# FORCE_NODALE-occurrences bleef alleen MY over). Mecway telt belastingen
# op; daarom krijgt elke belasting een eigen AFFE_CHAR_MECA en telt EXCIT
# ze op.
_LOAD_KEYWORDS = frozenset(("FORCE_NODALE", "FORCE_FACE", "FORCE_ARETE",
                            "FORCE_COQUE", "FORCE_POUTRE", "PRES_REP",
                            "PESANTEUR", "ROTATION"))


def _build_charges(model_data, func_names=None):
    """
    Verdeel alle BC's en koppelingen over Code-Aster-lasten.

    Returns
    -------
    list of (command, excit, fonc_mult)
        command   : 'AFFE_CHAR_MECA' of 'AFFE_CHAR_MECA_F'
        excit     : OrderedDict {aster_keyword: [_F-strings]}
        fonc_mult : naam van een DEFI_FONCTION voor EXCIT/FONC_MULT, of None
    De eerste last bevat alle constante randvoorwaarden en koppelingen;
    elke belasting (_LOAD_KEYWORDS) krijgt een eigen last. Tijdshistories
    worden DEFI_FONCTION's uit func_names ({(bc-index, sleutel): naam},
    _load_func_names). Zonder func_names mogen er geen tijdshistories meer
    zijn (MECA_STATIQUE neemt de laatste waarde, zie _build_lin_static).
    Een kracht- of momentcomponent 0 wordt weggelaten (geen effect); een
    opgelegde verplaatsing 0 niet.
    """
    constraints = OrderedDict()
    timed_constraints = OrderedDict()
    loads = []
    # Knopen met een fixed support niet nog eens schuin vastleggen: een
    # dubbele (lineair afhankelijke) voorwaarde maakt het stelsel met
    # Lagrange-multiplicatoren singulier (FACTOR_42 met een frictionless
    # schaalvlak naast een inklemming, gezien met Code-Aster 17.4). Mecway
    # reduceert dubbele voorwaarden zelf (manual v33 par. 9.6).
    sans = OrderedDict()
    for bc in model_data["bcs"]:
        if bc["type"] == "fixed" and bc["selection"]:
            key = "SANS_" + bc["aster_target"]
            sans.setdefault(key, [])
            if bc["selection"] not in sans[key]:
                sans[key].append(bc["selection"])
    sans = OrderedDict((k, tuple(v)) for k, v in sans.items())
    prelude = []
    beam_merged = []
    _sum_line_pressures(model_data)
    for idx, bc in enumerate(model_data["bcs"]):
        kw = bc["aster_keyword"]
        if bc.get("unil_zones") is not None:
            continue        # compression only: DEFI_CONTACT (contact-blok)
        if bc.get("oblique") is not None:
            # symmetry (bridge_mesh._symmetry): per groep LIAISON_OBLIQUE
            # (groep, angl, ddls[, waarden]): het optionele 4e element
            # {ddl: waarde} (frictionless per knoopnormaal met een
            # normaalverplaatsing, bridge_mesh); zonder: 0.
            for item in bc["oblique"]:
                group, angl, ddls = item[:3]
                values = item[3] if len(item) > 3 and item[3] else {}
                if model_data.get("xfem"):
                    ddl = bridge_xfem.axis_ddl(angl, ddls, values)
                    if ddl is not None:
                        # XFEM: DDL_IMPO legt ook de XFEM-vrijheidsgraden
                        # van gesneden elementen vast, LIAISON_OBLIQUE
                        # niet (forma07b, BR-11: K1 +3,8 % aan het
                        # symmetrievlak; met DDL_IMPO exact)
                        constraints.setdefault("DDL_IMPO", []).append(
                            "_F(GROUP_NO='{0}', {1}={2!r}{3})".format(
                                group, ddl[0], ddl[1], "".join(
                                    ", {0}={1}".format(k, v)
                                    for k, v in sans.items())))
                        continue
                    bridge_xfem.warn_oblique(model_data, bc["selection"],
                                             group)
                parts = ["GROUP_NO='{0}'".format(group),
                         "ANGL_NAUT=({0!r}, {1!r}, {2!r})".format(*angl)]
                parts += ["{0}={1!r}".format(d, float(values.get(d, 0.0)))
                          for d in ddls]
                parts += ["{0}={1}".format(k, v) for k, v in sans.items()]
                constraints.setdefault("LIAISON_OBLIQUE", []).append(
                    "_F({0})".format(", ".join(parts)))
            continue
        if bc["type"] == "centrifugal" and bc["aster_dict"]:
            loads.extend(_centrifugal_loads(model_data, bc))
            continue
        if bc.get("hydro") is not None:
            name = "FHYD{0}".format(len(prelude) + 1)
            prelude.append(_hydrostatic_formula(name, bc["hydro"]))
            loads.append(("AFFE_CHAR_MECA_F", OrderedDict([(kw, [
                "_F(GROUP_MA='{0}', PRES={1})".format(bc["selection"],
                                                      name)])]), None))
            continue
        if bc.get("pin_weights"):
            constraints.setdefault(kw, []).extend(_render_bc(bc))
            continue
        if bc.get("node_loads"):
            # Moment op vlakken (bridge_mesh._moment_to_forces): constante
            # componenten opgeteld per knoop, elke tijdsafhankelijke
            # component een last met FONC_MULT.
            const_f = {}
            for comp in bc["node_loads"]:
                v = bc["aster_dict"][comp]
                if isinstance(v, list):
                    loads.append(("AFFE_CHAR_MECA", OrderedDict(
                        [(kw, _render_node_loads(bc["node_loads"],
                                                 {comp: 1.0}))]),
                        func_names[(idx, comp)]))
                else:
                    const_f[comp] = v
            entries = _render_node_loads(bc["node_loads"], const_f)
            if entries:
                loads.append(("AFFE_CHAR_MECA",
                              OrderedDict([(kw, entries)]), None))
            continue
        if not bc["aster_dict"]:
            log("INFO: BC '{0}' op '{1}' heeft lege aster_dict. "
                "Overgeslagen.".format(bc["type"], bc["selection"]))
            continue
        if bc["type"] == "gravity" and isinstance(
                bc["aster_dict"].get("GRAVITE"), list):
            # Gravity met een tijdshistorie (bridge_bcs.GravityBC):
            # AFFE_CHAR_MECA_F kent geen PESANTEUR (catalogus
            # affe_char_meca_f.py v17.4), dus PESANTEUR met GRAVITE 1 en
            # de historie als FONC_MULT in EXCIT (zoals testcase forma12b).
            # Een eigen last met fonc: _merge_beam_loads telt hem niet op
            # bij de constante gravity.
            d = bc["aster_dict"]["DIRECTION"]
            loads.append(("AFFE_CHAR_MECA", OrderedDict([(
                "PESANTEUR", ["_F(GRAVITE=1.0, DIRECTION=({0!r}, {1!r}, "
                              "{2!r}))".format(*d)])]),
                func_names[(idx, "GRAVITE")]))
            continue
        cdict = OrderedDict()
        tdict = OrderedDict()
        for k, v in bc["aster_dict"].items():
            if isinstance(v, list):
                tdict[k] = func_names[(idx, k)]
            elif bc["type"] in ("force", "moment", "traction",
                                "linepressure") and v == 0.0:
                continue
            else:
                cdict[k] = v
        attrs = OrderedDict((k, cdict.pop(k)) for k in _BC_ATTRIBUTE_KEYS
                            if k in cdict)
        centre = None
        if kw in ("LIAISON_OBLIQUE", "FACE_IMPO"):
            attrs.update(sans)
            if kw == "LIAISON_OBLIQUE" and bc.get("aster_target") == "GROUP_MA":
                centre = _centre_node_groups(model_data).get(bc["selection"])
            if centre:
                # Middenknoop van QUAD9/TRIA7 (COQUE_3D) heeft alleen
                # DRX/DRY/DRZ: LIAISON_OBLIQUE met DX erop gaf <EXCEPTION>
                # CHARGES2_31 (Code-Aster 17.4). Uitsluiten; de rotaties
                # krijgt die knoop hieronder apart.
                attrs["SANS_GROUP_NO"] = tuple(
                    attrs.get("SANS_GROUP_NO", ())) + (centre,)
        elif kw == "DDL_IMPO" and bc["type"] in ("displacement",
                                                 "noderotation", "velocity"):
            # Ook een opgelegde verplaatsing/rotatie niet op fixed-knopen:
            # een tijdsafhankelijke gaf ASSEMBLA_26 ("bloqué plusieurs
            # fois"), een constante won stil van de inklemming (crit-review).
            # DDL_IMPO kent SANS_GROUP_NO/SANS_GROUP_MA (catalogus
            # affe_char_meca.py v17.4).
            attrs.update(sans)
        if bc.get("_beam_merged"):
            # Alle verdeelde balklasten in een AFFE_CHAR_MECA_F
            # (_prepare_beam_loads): constanten als DEFI_CONSTANTE.
            for k in list(cdict):
                name = "FCST{0}_{1}".format(idx + 1, k)
                prelude.append("{0} = DEFI_CONSTANTE(VALE={1!r})\n".format(
                    name, cdict.pop(k)))
                tdict[k] = name
            beam_merged.extend(_render_bc(bc, tdict))
            continue
        if tdict and cdict and kw == "FORCE_POUTRE":
            # Balken: een verdeelde last per balk (<EXCEPTION> CALCULEL2_92
            # "plus d'une charge répartie ... pas possible pour les modèles
            # de poutre", Code-Aster 17.4): constante componenten als
            # DEFI_CONSTANTE in dezelfde AFFE_CHAR_MECA_F.
            for k in list(cdict):
                name = "FCST{0}_{1}".format(idx + 1, k)
                prelude.append("{0} = DEFI_CONSTANTE(VALE={1!r})\n".format(
                    name, cdict.pop(k)))
                tdict[k] = name
        if (tdict and kw == "PRES_REP" and list(tdict) == ["PRES"]
                and not attrs and _on_shell_faces(model_data,
                                                  bc["selection"])):
            # Druk met een historie op schalen: PRES_REP met een functie
            # (AFFE_CHAR_MECA_F) gaf op COQUE_3D <EXCEPTION> ELEMENTS4_92
            # "chargement de pression fonction (et non nul) sur un element
            # de coque" (Code-Aster 17.4, testrun). Daarom PRES = 1 met de
            # historie als FONC_MULT in EXCIT (zelfde last, het teken van
            # faceid 6 zit in de historie).
            loads.append(("AFFE_CHAR_MECA", OrderedDict([(kw, [
                "_F(GROUP_MA='{0}', PRES=1.0)".format(bc["selection"])])]),
                tdict["PRES"]))
            tdict = OrderedDict()
        if tdict:
            tdict.update(attrs)
            entries = _render_bc(bc, tdict)
            if centre:
                entries += _centre_rotation_entry(centre, tdict, sans)
            if kw in _LOAD_KEYWORDS:
                loads.append(("AFFE_CHAR_MECA_F",
                              OrderedDict([(kw, entries)]), None))
            else:
                timed_constraints.setdefault(kw, []).extend(entries)
        if cdict:
            cdict.update(attrs)
            entries = _render_bc(bc, cdict)
            if centre:
                entries += _centre_rotation_entry(centre, cdict, sans)
            if kw in _LOAD_KEYWORDS:
                loads.append(("AFFE_CHAR_MECA",
                              OrderedDict([(kw, entries)]), None))
            else:
                constraints.setdefault(kw, []).extend(entries)

    if beam_merged:
        loads.append(("AFFE_CHAR_MECA_F",
                      OrderedDict([("FORCE_POUTRE", beam_merged)]), None))
    # Gravity buiten de balken als krachten (_prepare_beam_loads)
    loads.extend(model_data.get("_extra_loads", []))
    for kw, entries in _render_couplings(
            model_data.get("couplings", [])).items():
        constraints.setdefault(kw, []).extend(entries)
    for kw, entries in _render_mpcs(model_data).items():
        constraints.setdefault(kw, []).extend(entries)
    model_data["_charge_prelude"] = "".join(
        prelude + model_data.pop("_extra_prelude", []))

    charges = []
    if constraints:
        charges.append(("AFFE_CHAR_MECA", constraints, None))
    if timed_constraints:
        charges.append(("AFFE_CHAR_MECA_F", timed_constraints, None))
    return charges + _merge_beam_loads(model_data, loads)


def _on_shell_faces(model_data, selection):
    """True als de vlakselectie schaalvlakken bevat (bridge_mesh
    group_face_list, kind 'shellface')."""
    return any(f.get("kind") == "shellface" for f in
               model_data.get("group_face_list", {}).get(selection, []))


def _follower_pressure_groups(model_data, analysis):
    """
    Selecties waarop druk (surfacepressure, PRES_REP) een meebewegende last
    wordt: EXCIT TYPE_CHARGE='SUIV' (_render_charges). Mecway: "In
    nonlinear analysis, uniform pressure is a follower load" (manual v33
    par. 9.14; CCX rekent de druk dan op de vervormde vlakken, e_c3d.f).
    Alleen bij grote verplaatsingen (deformation GROT_GDEP e.d.) en alleen
    op volumevlakken en COQUE_3D-schalen; DKT/DST kunnen het niet
    (<EXCEPTION> CALCUL_42 "MEDKQU4 devrait calculer l'option
    RIGI_MECA_PRSU_F", Code-Aster 17.4, testrun) en zijn hier geometrisch
    lineair. Hydrostatische druk (FORMULE) en druk met een formule blijven
    vast (Mecway zegt dit alleen van uniforme druk).
    """
    if analysis.get("deformation", "PETIT") not in _LARGE_DEFORMATIONS:
        return set()
    mods = model_data.get("elset_modelisations", {})
    elem_elset = model_data.get("_elem_elset", {})
    faces = model_data.get("group_face_list", {})
    out, fixed = set(), []
    for bc in model_data.get("bcs", []):
        if (bc["type"] != "surfacepressure" or bc.get("hydro") is not None
                or bc.get("aster_keyword") != "PRES_REP"
                or not bc.get("selection")):
            continue
        ok = True
        for f in faces.get(bc["selection"], []):
            if f.get("kind") == "shellface" and mods.get(
                    elem_elset.get(f["eid"])) != "COQUE_3D":
                ok = False
        if ok:
            out.add(bc["selection"])
        else:
            fixed.append(bc["selection"])
    if fixed:
        log(tr("WARNING: Druk op DKT/DST-schalen ({0}) blijft een vaste last "
               "(Mecway: meebewegend in een niet-lineaire analyse); Code-Aster "
               "kan dat alleen op COQUE_3D (elem_shell, pagina Elementen).",
               "WARNING: Pressure on DKT/DST shells ({0}) stays a fixed load "
               "(Mecway: follower load in a nonlinear analysis); Code-Aster "
               "can do that only on COQUE_3D (elem_shell, Elements page).")
            .format(", ".join(sorted(set(fixed)))))
    if out:
        log("INFO: Druk als meebewegende last (TYPE_CHARGE='SUIV') op "
            "{0}.".format(", ".join(sorted(out))))
    return out


def _follower_rotation(model_data, analysis, command):
    """
    Centrifugaalkracht (ROTATION) als meebewegende last in STAT_NON_LINE
    bij grote verplaatsingen: Mecway neemt spin softening "automatically
    ... into account with the ... Nonlinear Static analysis types" (manual
    v33 par. 9.20; CCX gebruikt dan de vervormde positie, e_c3d.f). Code-
    Aster: EXCIT TYPE_CHARGE='SUIV' met ROTATION rekent op de vervormde
    straal (testrun 17.4, staaf 0,1 m, w = 7000 rad/s, 3D GREEN_LAGRANGE:
    reactie 19379 N i.p.v. 19232 N = rho A w^2 L^2 / 2, tip 0,6083 mm
    i.p.v. 0,6040 mm). Alleen als ROTATION alleen op volume-elementen
    staat (balken blijven PETIT; met schalen wordt het FORMULE's van de
    beginpositie, _centrifugal_loads, die blijven vast). Dynamica: Mecway
    kent geen centrifugaalkracht in Nonlinear Dynamic; daar vast gelaten.
    """
    if (command != "STAT_NON_LINE" or
            analysis.get("deformation", "PETIT") not in _LARGE_DEFORMATIONS):
        return False
    if not any(bc["type"] == "centrifugal" and bc.get("aster_dict")
               for bc in model_data.get("bcs", [])):
        return False
    mods = model_data.get("elset_modelisations", {})
    groups = [g for g, m in mods.items()
              if m not in ("DIS_T", "DIS_TR", "CABLE")]
    if not groups or any(mods[g] not in _VOLUME_MODELISATIONS
                         for g in groups):
        log("INFO: Centrifugaalkracht blijft een vaste last (niet alleen "
            "volume-elementen; spin softening alleen voor volumes).")
        return False
    log("INFO: Centrifugaalkracht op de vervormde straal (ROTATION, "
        "TYPE_CHARGE='SUIV', spin softening zoals Mecway Nonlinear "
        "Static).")
    return True


# Verdeelde lasten die op balken werken (CALCULEL2_92, _merge_beam_loads)
_BEAM_DIST_KEYWORDS = ("FORCE_POUTRE", "PESANTEUR", "ROTATION")


def _sum_line_pressures(model_data):
    """Constante line pressures op dezelfde balkselectie (zelfde stelsel)
    optellen tot een belasting (zie _merge_beam_loads)."""
    first = {}
    for bc in model_data["bcs"]:
        if bc["type"] != "linepressure" or \
                bc["aster_keyword"] != "FORCE_POUTRE" or \
                any(isinstance(v, list) for v in bc["aster_dict"].values()):
            continue
        key = (bc["selection"], bool(bc["params"].get("_local")))
        if key not in first:
            first[key] = bc
            continue
        target = first[key]["aster_dict"]
        for k, v in bc["aster_dict"].items():
            target[k] = target.get(k, 0.0) + v
        bc["aster_dict"] = {}
        log("INFO: Line pressures op '{0}' opgeteld (een verdeelde last per "
            "balk in Code-Aster).".format(bc["selection"]))


def _merge_beam_loads(model_data, loads):
    """
    Code-Aster staat per balk een verdeelde last toe: <EXCEPTION>
    CALCULEL2_92 "votre chargement contient plus d'une charge répartie, le
    calcul n'est pas possible pour les modèles de poutre" (Code-Aster 17.4,
    MECA_STATIQUE/STAT_NON_LINE met FORCE_POUTRE en PESANTEUR in aparte
    lasten). In een AFFE_CHAR_MECA samen (andere sleutelwoorden, dus geen
    overschrijving) rekende het wel goed (balk met line pressure en
    gravity: reactie 2,60097 N = hand). Daarom de constante FORCE_POUTRE,
    PESANTEUR en ROTATION samen in een last. Overlappende line pressures en
    een tijdsafhankelijke line pressure naast andere verdeelde balklasten
    regelt _prepare_beam_loads vooraf (BRLP-groepen, een AFFE_CHAR_MECA_F);
    de controle hieronder blijft als vangnet.
    """
    mods = set(model_data.get("elset_modelisations", {}).values())
    if not mods & set(_BEAM_MODELISATIONS):
        return loads
    idx = [i for i, (cmd, kws, fonc) in enumerate(loads)
           if cmd == "AFFE_CHAR_MECA" and fonc is None and kws and
           set(kws) <= set(_BEAM_DIST_KEYWORDS)]
    if len(idx) < 2:
        return loads
    # Binnen een AFFE_CHAR_MECA overschrijft een latere _F een eerdere op
    # dezelfde cel (nagelopen: FORCE_POUTRE ALLB FZ=1 en B FZ=10 gaf
    # reactie -11 i.p.v. -12). Overlappende FORCE_POUTRE-groepen dus niet
    # samenvoegen: dan liever de luide CALCULEL2_92 dan een stil fout
    # antwoord.
    groups = []
    for i in idx:
        for entry in loads[i][1].get("FORCE_POUTRE", []):
            m = re.search(r"GROUP_MA='([^']+)'", entry)
            groups.append(m.group(1) if m else None)
    cells = [_group_cells(model_data, g) for g in groups]
    for a in range(len(cells)):
        for b in range(a + 1, len(cells)):
            if cells[a] is None or cells[b] is None or cells[a] & cells[b]:
                log(tr("ERROR: Meerdere verdeelde lasten (line pressure) op "
                       "dezelfde balken ('{0}', '{1}'): Code-Aster telt die "
                       "in een last niet op en weigert ze in aparte lasten "
                       "(CALCULEL2_92). Voeg ze in Mecway samen tot een line "
                       "pressure per balkselectie.",
                       "ERROR: Several distributed loads (line pressure) on "
                       "the same beams ('{0}', '{1}'): Code-Aster does not "
                       "add them up within one load and rejects them in "
                       "separate loads (CALCULEL2_92). Combine them in "
                       "Mecway into one line pressure per beam selection.")
                    .format(groups[a], groups[b]))
                return loads
    merged = OrderedDict()
    for i in idx:
        for kw, entries in loads[i][1].items():
            merged.setdefault(kw, []).extend(entries)
    # PESANTEUR mag maar een keer (catalogus affe_char_meca.py, max=1):
    # meerdere gravity-items optellen tot een vector.
    if len(merged.get("PESANTEUR", [])) > 1:
        merged["PESANTEUR"] = [_sum_gravity(merged["PESANTEUR"])]
    out = [l for i, l in enumerate(loads) if i not in idx]
    out.insert(idx[0], ("AFFE_CHAR_MECA", merged, None))
    log("INFO: Verdeelde balklasten ({0}) in een AFFE_CHAR_MECA "
        "(CALCULEL2_92).".format(", ".join(merged)))
    return out


def _sum_values(values):
    """Som van getallen en tijdshistories [(t, v)] (lineair tussen de
    punten, constant erbuiten, _interp_history): een getal, of een
    historie op de unie van de tijden."""
    hists = [v for v in values if isinstance(v, list)]
    if not hists:
        return sum(values)
    times = sorted(set(t for h in hists for t, _v in h))
    return [(t, sum(_interp_history(v, t) for v in values)) for t in times]


def _prepare_beam_loads(model_data, solver_cmd):
    """
    Een verdeelde last per balkelement (<EXCEPTION> CALCULEL2_92, zie
    _merge_beam_loads), ook bij
      (a) line pressures op overlappende, verschillende selecties: de
          balkelementen worden verdeeld in disjuncte groepen (BRLPn, een
          per combinatie van lasten) met per groep de som; binnen een
          AFFE_CHAR_MECA overschrijft een latere FORCE_POUTRE-_F een
          eerdere op dezelfde cel (nagelopen, _merge_beam_loads), dus
          optellen moet hier;
      (b) een tijdsafhankelijke line pressure samen met een andere
          verdeelde last op dezelfde balk (niet in MECA_STATIQUE: die neemt
          de laatste waarde). AFFE_CHAR_MECA_F kent geen PESANTEUR
          (catalogus affe_char_meca_f.py v17.4), dus gravity op de balken
          wordt FORCE_POUTRE rho A g (globaal) in dezelfde som, en
          PESANTEUR blijft voor de andere groepen (GROUP_MA, catalogus
          affe_char_meca.py). De som van tijdshistories en constanten is
          weer een historie (_sum_values) -> een DEFI_FONCTION per
          component.
    Vervangt de betrokken line pressures door nieuwe (synthetische) BC's
    op de BRLP-groepen (model_data["extra_ma_groups"], DEFI_GROUP MAILLE);
    vóór de builder aanroepen (_build_defigroup_block). Niet: lokale (N,
    VY, VZ) en globale (FX, FY, FZ) componenten op dezelfde balk (één
    FORCE_POUTRE-_F kent ze niet samen, PRESENT_ABSENT in de catalogus)
    en centrifugaalkracht met een tijdsafhankelijke line pressure: ERROR,
    dan blijft CALCULEL2_92.
    """
    mods = model_data.get("elset_modelisations", {})
    beam_sets = [g for g, m in mods.items() if m in _BEAM_MODELISATIONS]
    if not beam_sets:
        return
    renames = model_data.get("group_renames", {})
    cell_set = {}
    for e in model_data.get("mesh_elements", []):
        g = renames.get(e[3], e[3])
        if g in beam_sets:
            cell_set[e[0]] = g
    bcs = model_data["bcs"]
    timed_ok = solver_cmd != "MECA_STATIQUE"
    lps = []
    for idx, bc in enumerate(bcs):
        if (bc["type"] == "linepressure"
                and bc.get("aster_keyword") == "FORCE_POUTRE"
                and bc.get("aster_dict")):
            cells = _group_cells(model_data, bc["selection"]) or set()
            cells = set(c for c in cells if c in cell_set)
            timed = timed_ok and any(isinstance(v, list)
                                     for v in bc["aster_dict"].values())
            lps.append((idx, cells, timed))
    if not lps:
        return
    gravity = [bc for bc in bcs if bc["type"] == "gravity"
               and bc.get("aster_dict")]
    timed_gravity = [bc for bc in gravity
                     if isinstance(bc["aster_dict"].get("GRAVITE"), list)]
    gravity = [bc for bc in gravity if bc not in timed_gravity]
    centri = [bc for bc in bcs if bc["type"] == "centrifugal"
              and bc.get("aster_dict")]
    mats = model_data.get("materials", {})
    elsets = model_data.get("elsets", {})
    secs = model_data.get("beam_sections", {})

    def rho_a(g):
        return (mats.get(elsets.get(g), {}).get("rho", 0.0) *
                secs.get(g, {}).get("area", 0.0))
    if timed_gravity and timed_ok and any(rho_a(g) for g in beam_sets):
        # Gravity met historie is een eigen last (PESANTEUR met FONC_MULT,
        # _build_charges); samen met een line pressure telt CALCULEL2_92
        # twee verdeelde lasten. NIET opgelost (geen run).
        log(tr("WARNING: Gravity met een tijdshistorie en line pressures "
               "op balken: Code-Aster staat een verdeelde last per balk "
               "toe en kan stoppen met CALCULEL2_92. Geef gravity of de "
               "line pressure in Mecway zonder tijdshistorie.",
               "WARNING: Gravity with a time history and line pressures "
               "on beams: Code-Aster allows one distributed load per beam "
               "and may stop with CALCULEL2_92. Give gravity or the line "
               "pressure no time history in Mecway."))
    # Probleem (a) of (b)?
    by_cell = {}
    for idx, cells, timed in lps:
        for c in cells:
            by_cell.setdefault(c, []).append(idx)
    sels = dict((idx, bcs[idx]["selection"]) for idx, _c, _t in lps)
    overlap = any(len(set(sels[i] for i in ids)) > 1
                  for ids in by_cell.values())
    timed_ids = set(idx for idx, _c, t in lps if t)
    # CALCULEL2_92 telt de lasten (charges) met een verdeelde balklast,
    # niet per balk: een constante FORCE_POUTRE op BRLP1 (AFFE_CHAR_MECA)
    # naast een tijdsafhankelijke op het disjuncte BRLP3 (AFFE_CHAR_MECA_F)
    # stopte CALC_CHAMP (SIPM_ELNO) nog met CALCULEL2_92 (Code-Aster 17.4,
    # testrun; STAT_NON_LINE zelf rekende wel). Dus met een
    # tijdsafhankelijke line pressure alle verdeelde balklasten in een
    # AFFE_CHAR_MECA_F (_build_charges, "_beam_merged").
    mixed = bool(timed_ids) and (
        len(lps) > 1 or bool((gravity or centri) and
                             any(rho_a(g) for g in beam_sets)))
    if not overlap and not mixed:
        return
    if mixed and centri and any(rho_a(g) for g in beam_sets):
        log(tr("ERROR: Centrifugaalkracht en een tijdsafhankelijke line "
               "pressure op dezelfde balken: Code-Aster staat per balk een "
               "verdeelde last toe (CALCULEL2_92); niet samengevoegd.",
               "ERROR: Centrifugal force and a time-dependent line pressure "
               "on the same beams: Code-Aster allows one distributed load "
               "per beam (CALCULEL2_92); not combined."))
        return
    # Bijdragen per cel: (sleutel, systeem 'G'/'L', {component: waarde})
    grav_vec = [0.0, 0.0, 0.0]
    if mixed:
        for bc in gravity:
            d = bc["aster_dict"]
            n = math.sqrt(sum(x * x for x in d["DIRECTION"])) or 1.0
            for k in range(3):
                grav_vec[k] += d["GRAVITE"] * d["DIRECTION"][k] / n
    sig = {}
    cells_all = set(by_cell)
    if mixed and any(grav_vec):
        cells_all |= set(c for c in cell_set if rho_a(cell_set[c]))
    for c in cells_all:
        key = tuple(sorted(by_cell.get(c, [])))
        if mixed and any(grav_vec) and rho_a(cell_set[c]):
            key += (("G", cell_set[c]),)
        sig.setdefault(key, []).append(c)
    # Lokaal en globaal op dezelfde cel kan niet in een _F
    for key in sig:
        local = set(bool(bcs[i]["params"].get("_local"))
                    for i in key if not isinstance(i, tuple))
        if any(isinstance(i, tuple) for i in key):
            local.add(False)
        if len(local) > 1:
            log(tr("ERROR: Line pressures in elementcoordinaten (u/v/w) en "
                   "globaal (x/y/z of gravity) op dezelfde balken ({0}): "
                   "Code-Aster kent ze niet samen in een FORCE_POUTRE en "
                   "staat per balk een verdeelde last toe (CALCULEL2_92). "
                   "Gebruik in Mecway een assenstelsel per balkselectie.",
                   "ERROR: Line pressures in element coordinates (u/v/w) "
                   "and global (x/y/z or gravity) on the same beams ({0}): "
                   "Code-Aster does not accept them together in one "
                   "FORCE_POUTRE and allows one distributed load per beam "
                   "(CALCULEL2_92). Use one coordinate system per beam "
                   "selection in Mecway.").format(", ".join(
                       sorted(set(sels[i] for i in key
                                  if not isinstance(i, tuple))))))
            return
    taken = set(model_data.get("mesh_group_names", set()))
    groups = model_data.setdefault("extra_ma_groups", OrderedDict())
    taken |= set(groups)
    new_bcs = []
    n = 0
    for key in sorted(sig, key=lambda k: min(sig[k])):
        comps = OrderedDict()
        local = False
        for i in key:
            if isinstance(i, tuple):
                q = rho_a(i[1])
                for k, ax in enumerate(("FX", "FY", "FZ")):
                    comps.setdefault(ax, []).append(q * grav_vec[k])
                continue
            local = bool(bcs[i]["params"].get("_local"))
            for k, v in bcs[i]["aster_dict"].items():
                comps.setdefault(k, []).append(v)
        n += 1
        while "BRLP{0}".format(n) in taken:
            n += 1
        name = "BRLP{0}".format(n)
        taken.add(name)
        groups[name] = sorted(sig[key])
        new_bcs.append({
            "type": "linepressure", "selection": name,
            "aster_keyword": "FORCE_POUTRE", "aster_target": "GROUP_MA",
            "params": {"_local": local}, "_beam_merged": mixed,
            "aster_dict": OrderedDict((k, _sum_values(v))
                                      for k, v in comps.items())})
    for idx, _c, _t in lps:
        bcs[idx]["aster_dict"] = {}
    if mixed and any(grav_vec):
        # Gravity op de balken zit nu in FORCE_POUTRE. Ook een PESANTEUR
        # met GROUP_MA zonder balken in een aparte last gaf nog CALCULEL2_92
        # (Code-Aster 17.4, testrun balk + knoopmassa): de controle telt
        # lasten, niet elementen. De rest daarom als gewone krachten:
        # volumes FORCE_INTERNE rho g, schalen FORCE_COQUE rho t g,
        # knoopmassa's FORCE_NODALE m g (zoals _centrifugal_loads).
        for bc in gravity:
            bc["aster_dict"] = {}
        extra = []
        shells = model_data.get("shell_sections", {})
        for g, mod in mods.items():
            if g in beam_sets:
                continue
            rho = mats.get(elsets.get(g), {}).get("rho", 0.0)
            if not rho:
                continue
            if mod in _VOLUME_MODELISATIONS:
                kw, q = "FORCE_INTERNE", rho
            elif mod in _SHELL_MODELISATIONS:
                kw, q = "FORCE_COQUE", rho * shells.get(g, {}).get(
                    "thickness", 0.0)
            else:
                model_data.setdefault("skipped_loads", []).append(
                    tr("gravity op elset '{0}' ({1})",
                       "gravity on elset '{0}' ({1})").format(g, mod))
                log(tr("ERROR: Gravity op '{0}' ({1}) in een model met een "
                       "tijdsafhankelijke line pressure op balken: niet "
                       "vertaald.",
                       "ERROR: Gravity on '{0}' ({1}) in a model with a "
                       "time-dependent line pressure on beams: not "
                       "translated.").format(g, mod))
                continue
            extra.append(("AFFE_CHAR_MECA", OrderedDict([(kw, [
                "_F(GROUP_MA='{0}', FX={1!r}, FY={2!r}, FZ={3!r})".format(
                    g, q * grav_vec[0], q * grav_vec[1], q * grav_vec[2])])]),
                None))
        node_mass = OrderedDict()
        for d in model_data.get("discretes", {}).values():
            m = dict(d.get("cara", [])).get("M_T_D_N") or \
                dict(d.get("cara", [])).get("M_TR_D_N")
            if m and m[0]:
                for n in d.get("nodes", []):
                    node_mass[n] = node_mass.get(n, 0.0) + m[0]
        if node_mass:
            extra.append(("AFFE_CHAR_MECA", OrderedDict([("FORCE_NODALE", [
                "_F(NOEUD='N{0}', FX={1!r}, FY={2!r}, FZ={3!r})".format(
                    n, m * grav_vec[0], m * grav_vec[1], m * grav_vec[2])
                for n, m in node_mass.items()])]), None))
        model_data["_extra_loads"] = extra
    bcs.extend(new_bcs)
    log("INFO: Verdeelde balklasten per balkelement opgeteld in {0} "
        "disjuncte groep(en) ({1}){2} (CALCULEL2_92).".format(
            len(new_bcs), ", ".join(b["selection"] for b in new_bcs),
            "; gravity op de balken als FORCE_POUTRE rho A g"
            if mixed and any(grav_vec) else ""))


def _group_cells(model_data, group):
    """Mecway-elementnummers van een elset of elementselectie (hernoemde
    naam), of None als onbekend."""
    if group is None:
        return None
    extra = model_data.get("extra_ma_groups", {}).get(group)
    if extra is not None:
        return set(extra)
    sel = model_data.get("element_selections", {}).get(group)
    if sel is not None:
        return set(sel)
    renames = model_data.get("group_renames", {})
    cells = set(e[0] for e in model_data.get("mesh_elements", [])
                if renames.get(e[3], e[3]) == group)
    return cells or None


def _sum_gravity(entries):
    """Meerdere PESANTEUR-_F's (GRAVITE g, DIRECTION d) -> een _F met de
    vectorsom."""
    total = [0.0, 0.0, 0.0]
    for entry in entries:
        g = float(re.search(r"GRAVITE=([^,\)]+)", entry).group(1))
        d = [float(v) for v in re.search(
            r"DIRECTION=\(([^)]*)\)", entry).group(1).split(",") if v.strip()]
        n = math.sqrt(sum(c * c for c in d)) or 1.0
        for k in range(3):
            total[k] += g * d[k] / n
    mag = math.sqrt(sum(c * c for c in total))
    if mag == 0.0:
        return "_F(GRAVITE=0.0, DIRECTION=(0.0, 0.0, -1.0))"
    log("INFO: {0} gravity-belastingen opgeteld tot een PESANTEUR (catalogus: "
        "maximaal een).".format(len(entries)))
    return "_F(GRAVITE={0!r}, DIRECTION=({1!r}, {2!r}, {3!r}))".format(
        mag, total[0] / mag, total[1] / mag, total[2] / mag)


def _render_charges(charges, model_data=None):
    """
    (blok met de AFFE_CHAR_MECA(_F)-aanroepen, EXCIT-regel). De lasten
    heten load_1, load_2, ...; daarna volgen de #ASTER-code van de
    gebruiker en de lasten uit #ASTER-EXCIT (bridge_custom.py).
    """
    code = _custom_code(model_data, "code")
    extra = []
    if model_data is not None:
        extra = model_data.get("aster_custom", {}).get("excit", [])
    if not charges and not extra:
        log(tr("WARNING: Geen randvoorwaarden of belastingen in het model.",
               "WARNING: No constraints or loads in the model."))
        return "#-- geen randvoorwaarden of belastingen --\n" + code, ""
    blocks = []
    if model_data is not None and model_data.get("_charge_prelude"):
        blocks.append(model_data["_charge_prelude"])
    excit = []
    follower = (model_data or {}).get("_follower_groups") or set()
    for k, (command, kws, fonc) in enumerate(charges):
        name = "load_{0}".format(k + 1)
        blocks.append(_render_char_meca(name, command, kws))
        # Druk als meebewegende last (_follower_pressure_groups): een last
        # met alleen PRES_REP op die selecties; elke druk heeft een eigen
        # last (_build_charges), TYPE_CHARGE geldt per last (U4.51.03
        # EXCIT).
        groups = [m for e in kws.get("PRES_REP", [])
                  for m in re.findall(r"GROUP_MA='([^']+)'", e)]
        suiv = (follower and list(kws) == ["PRES_REP"] and groups
                and all(g in follower for g in groups))
        # Centrifugaalkracht op de vervormde straal (spin softening):
        # ROTATION met TYPE_CHARGE='SUIV' (_follower_rotation).
        if (list(kws) == ["ROTATION"] and fonc is None and
                (model_data or {}).get("_follower_rotation")):
            suiv = True
        excit.append("_F(CHARGE={0}{1}{2})".format(
            name, ", FONC_MULT={0}".format(fonc) if fonc else "",
            ", TYPE_CHARGE='SUIV'" if suiv else ""))
    if code:
        blocks.append(code)
    excit += ["_F(CHARGE={0})".format(n) for n in extra]
    if len(excit) == 1:
        clause = "    EXCIT={0},".format(excit[0])
    else:
        clause = "    EXCIT=(\n{0}    ),".format(
            "".join("        {0},\n".format(e) for e in excit))
    return "\n".join(blocks), clause


def _custom_code(model_data, kind):
    """#ASTER-code ("code" of "post") met de Code-Aster-groepsnamen, of ""."""
    if model_data is None:
        return ""
    lines = model_data.get("aster_custom", {}).get(kind, [])
    if not lines:
        return ""
    text = "\n".join(lines)
    text = bridge_custom.substitute(
        text, model_data.get("group_renames", {}),
        model_data.get("mesh_group_names", set()))
    title = ("#ASTER-code van de gebruiker" if kind == "code"
             else "#ASTER-POST-code van de gebruiker")
    return "# --- {0} (Mecway custom input) ---\n{1}\n# --- einde ---\n".format(
        title, text)


def _render_char_meca(concept, command, excit):
    """'<concept> = <command>(MODELE=model, KW=..., ...)'."""
    out = "{0} = {1}(\n    MODELE=model,\n".format(concept, command)
    for kw, entries in excit.items():
        if len(entries) == 1:
            out += "    {0}={1},\n".format(kw, entries[0])
        else:
            out += "    {0}=(\n        {1},\n    ),\n".format(
                kw, ",\n        ".join(entries))
    return out + ")\n"


def _hydrostatic_formula(name, hydro):
    """
    FORMULE voor PRES_REP (Mecway hydrostatic pressure, manual v33 par.
    9.17): p = rho * g . (x - x0) onder het vrije oppervlak, 0 erboven;
    X, Y, Z = beginpositie (U4.44.01 PRES_REP "function" pressure).
    hydro["sign"] = -1 voor schaalvlakken met faceid 6 (zoals
    surfacepressure). Mecway integreert stuksgewijs exact; Code-Aster neemt
    de formule in de integratiepunten (kleine fout in een vlak dat het
    vrije oppervlak snijdt).
    """
    g, p0 = hydro["g"], hydro["point"]
    expr = ("{s!r}*max(0.0, {rho!r}*({gx!r}*(X-({x0!r}))+{gy!r}*(Y-({y0!r}))"
            "+{gz!r}*(Z-({z0!r}))))").format(
                s=hydro["sign"], rho=hydro["rho"], gx=g[0], gy=g[1], gz=g[2],
                x0=p0[0], y0=p0[1], z0=p0[2])
    return ("{0} = FORMULE(NOM_PARA=('X', 'Y', 'Z'),\n"
            "    VALE='{1}')\n").format(name, expr)


def _centrifugal_loads(model_data, bc):
    """
    Centrifugaalkracht (Mecway manual v33 par. 9.20, F = m w^2 r op alle
    massa, as door de oorsprong, beginpositie).
      - Zonder schalen: Code-Aster ROTATION (U4.44.01) op de elsets.
      - Met schalen: ROTATION kan niet: <EXCEPTION> CALCUL_37 "MEDKQU4 ne
        sait pas encore calculer l'option CHAR_MECA_ROTA_R" (Code-Aster
        17.4), ook niet met GROUP_MA zonder schalen. Dan per elset
        dezelfde kracht als FORMULE van X, Y, Z (AFFE_CHAR_MECA_F):
        volumes FORCE_INTERNE rho w^2 r, schalen FORCE_COQUE rho t w^2 r,
        balken FORCE_POUTRE rho A w^2 r.
      - Discrete elementen kunnen ROTATION ook niet ("MECA_DIS_T_N ne sait
        pas ..."): knoopmassa's (bridge_mesh._build_discretes) als
        FORCE_NODALE m w^2 r.
    """
    d = bc["aster_dict"]
    w, axis = d["VITESSE"], d["AXE"]
    out = []
    mods = model_data.get("elset_modelisations", {})
    # Kabels (tension only, MODELISATION CABLE) kunnen ROTATION niet:
    # <EXCEPTION> CALCUL_37 "MECABL2 ne sait pas encore calculer l'option"
    # (Code-Aster 17.4, crit-review); FORCE_POUTRE bestaat er ook niet voor.
    for g, mod in mods.items():
        if mod == "CABLE":
            model_data.setdefault("skipped_loads", []).append(
                tr("centrifugaalkracht op kabel-elset '{0}'",
                   "centrifugal force on cable elset '{0}'").format(g))
            log(tr("ERROR: Centrifugaalkracht op de kabels (tension only) "
                   "'{0}' wordt niet vertaald; de rest van het model krijgt "
                   "hem wel.",
                   "ERROR: Centrifugal force on the cables (tension only) "
                   "'{0}' is not translated; the rest of the model does "
                   "get it.").format(g))
    groups = [g for g, mod in mods.items()
              if mod not in ("DIS_T", "DIS_TR", "CABLE")]
    if not any(mods.get(g) in _SHELL_MODELISATIONS for g in groups):
        if groups:
            parts = ["GROUP_MA={0}".format(_fmt_groups(groups))]
            parts += ["{0}={1}".format(k, v) for k, v in d.items()]
            out.append(("AFFE_CHAR_MECA", OrderedDict(
                [("ROTATION", ["_F({0})".format(", ".join(parts))])]), None))
        groups = []
    for gi, g in enumerate(groups):
        rho = model_data["materials"].get(
            model_data.get("elsets", {}).get(g), {}).get("rho", 0.0)
        mod = mods[g]
        if mod in _SHELL_MODELISATIONS:
            kw, q = "FORCE_COQUE", rho * model_data.get(
                "shell_sections", {}).get(g, {}).get("thickness", 0.0)
        elif mod in _BEAM_MODELISATIONS:
            kw, q = "FORCE_POUTRE", rho * model_data.get(
                "beam_sections", {}).get(g, {}).get("area", 0.0)
        elif mod in _VOLUME_MODELISATIONS:
            kw, q = "FORCE_INTERNE", rho
        else:
            if rho:
                model_data.setdefault("skipped_loads", []).append(
                    tr("centrifugaalkracht op elset '{0}' ({1})",
                       "centrifugal force on elset '{0}' ({1})").format(
                        g, mod))
                log(tr("ERROR: Centrifugaalkracht op '{0}' ({1}) in een "
                       "model met schalen: niet vertaald.",
                       "ERROR: Centrifugal force on '{0}' ({1}) in a model "
                       "with shells: not translated.").format(g, mod))
            continue
        if not q:
            continue
        comps = []
        dot = "+".join("{0!r}*{1}".format(axis[j], "XYZ"[j]) for j in range(3))
        for k, ax in enumerate("XYZ"):
            # r_loodrecht_k = x_k - (x . a) a_k
            # Volgnummer in de naam: groepen met dezelfde eerste tekens
            # mogen elkaars FORMULE niet overschrijven (crit-review).
            name = "FCEN{0}_{1}_{2}".format(
                gi + 1, re.sub(r"\W+", "_", g)[:10], ax)
            model_data.setdefault("_extra_prelude", []).append(
                "{0} = FORMULE(NOM_PARA=('X', 'Y', 'Z'), "
                "VALE='{1!r}*({2}-({3})*{4!r})')\n".format(
                    name, q * w * w, ax, dot, axis[k]))
            comps.append("F{0}={1}".format(ax, name))
        out.append(("AFFE_CHAR_MECA_F", OrderedDict([(kw, [
            "_F(GROUP_MA='{0}', {1})".format(g, ", ".join(comps))])]), None))
    nodes = model_data.get("mesh_nodes", {})
    forces = []
    for group, disc in model_data.get("discretes", {}).items():
        mass = dict(disc["cara"]).get("M_T_D_N")
        if not mass or not mass[0]:
            continue
        for n in disc["nodes"]:
            x = nodes[n]
            along = sum(x[k] * axis[k] for k in range(3))
            r = [x[k] - along * axis[k] for k in range(3)]
            f = [mass[0] * w * w * c for c in r]
            forces.append("_F(NOEUD='N{0}', FX={1!r}, FY={2!r}, FZ={3!r})"
                          .format(n, f[0], f[1], f[2]))
    if forces:
        log("INFO: Centrifugaalkracht op {0} knoopmassa('s) als "
            "FORCE_NODALE m w^2 r.".format(len(forces)))
        out.append(("AFFE_CHAR_MECA", OrderedDict(
            [("FORCE_NODALE", forces)]), None))
    return out


def _render_mpcs(model_data):
    """
    Lineaire relaties die geen BC op een selectie zijn:
      - constraint equations (Mecway manual v33 par. 9.42,
        A dof1 + B dof2 + ... = C) -> LIAISON_DDL sum(COEF_MULT_i u_i) =
        COEF_IMPO (U4.44.01 LIAISON_DDL), coefficienten in SI;
      - verlijmd contact (bridge_mesh._bonded) -> LIAISON_MAIL (U4.44.01).
    """
    out = OrderedDict()
    for ce in model_data.get("constraint_equations", []):
        terms = ce["terms"]
        out.setdefault("LIAISON_DDL", []).append(
            "_F(NOEUD={0}, DDL={1}, COEF_MULT={2}, COEF_IMPO={3!r})".format(
                _fmt_seq(["'N{0}'".format(n) for n, d, c in terms]),
                _fmt_seq(["'{0}'".format(d) for n, d, c in terms]),
                _fmt_seq(["{0!r}".format(c) for n, d, c in terms]),
                ce["constant"]))
    normals = OrderedDict()
    for b in model_data.get("bonded", []):
        parts = ["GROUP_MA_MAIT='{0}'".format(b["master"]),
                 "GROUP_NO_ESCL='{0}'".format(b["slave"]),
                 "TYPE_RACCORD='{0}'".format(b["raccord"])]
        if b["raccord"] == "COQUE_MASSIF":
            # Schaalrand (slave) in een volume (master): LIAISON_MAIL
            # COQUE_MASSIF vraagt EPAIS en CHAM_NORMALE (catalogus
            # affe_char_meca.py v17.4; U4.44.01). Normaalveld van de schaal
            # met CREA_CHAMP OPERATION='NORMALE' (docs/
            # ASTER_regels_voorbeelden.md voorbeeld 2, doorgerekend: plaatrand
            # in een blok 0,00897 mm tegen ingeklemde strook 0,00867 mm), een
            # per schaalgroep, vóór de last (_extra_prelude).
            group = b["shell_group"]
            if group not in normals:
                normals[group] = "BRNORM{0}".format(len(normals) + 1)
                model_data.setdefault("_extra_prelude", []).append(
                    "{0} = CREA_CHAMP(TYPE_CHAM='NOEU_GEOM_R', "
                    "OPERATION='NORMALE', MODELE=model, GROUP_MA='{1}')"
                    "\n".format(normals[group], group))
            parts += ["EPAIS={0!r}".format(float(b["epais"])),
                      "CHAM_NORMALE={0}".format(normals[group])]
        if b.get("ddl"):
            # COQUE: zonder de drilling-rotatie (bridge_mesh._coque_ddl)
            parts.append("DDL=({0})".format(", ".join(
                "'{0}'".format(d) for d in b["ddl"])))
        if b.get("distance", 0.0) > 0.0:
            parts.append("DISTANCE_MAX={0!r}".format(b["distance"]))
        out.setdefault("LIAISON_MAIL", []).append(
            "_F({0})".format(", ".join(parts)))
    return out


# ==========================================
# HULPFUNCTIE: COUPLINGS RENDEREN
# ==========================================
def _render_couplings(couplings):
    """
    Render LIAISON_RBE3- en LIAISON_SOLIDE-blokken uit model_data["couplings"].

    Returns
    -------
    OrderedDict  {aster_keyword: [rendered_F_strings, ...]}

    LIAISON_SOLIDE (RBE2 / rigidbody)
        _F(GROUP_NO=('master_grp', 'slave_grp'))

    LIAISON_RBE3 (rbe3)
        _F(
            GROUP_NO_MAIT='master_grp',
            DDL_MAIT=('DX','DY','DZ' [,'DRX','DRY','DRZ']),
            GROUP_NO_ESCL=('slave_grp',),
            DDL_ESCL=('DX-DY-DZ',),
            COEF_ESCL=(1.0,),
        )

    surface_rot=True voegt DRX/DRY/DRZ toe aan DDL_MAIT.
    DDL_ESCL blijft 'DX-DY-DZ': solid-knopen hebben enkel translaties;
    een eventuele rotatie-bijdrage vanaf shell/beam-slaves zou via een
    aparte slave-groep moeten worden gemodelleerd. Niet ondersteund.
    """
    result = OrderedDict()
    for c in couplings:
        master = c["master_group"]
        slave  = c["slave_group"]

        if c["type"] == "rbe2":
            rendered = "_F(GROUP_NO=('{0}', '{1}'))".format(master, slave)
            result.setdefault("LIAISON_SOLIDE", []).append(rendered)

        elif c["type"] == "rbe3":
            ddl_mait = ("('DX', 'DY', 'DZ', 'DRX', 'DRY', 'DRZ')"
                        if c.get("surface_rot", False)
                        else "('DX', 'DY', 'DZ')")
            rendered = (
                "_F(GROUP_NO_MAIT='{master}', "
                "DDL_MAIT={ddl_mait}, "
                "GROUP_NO_ESCL=('{slave}',), "
                "DDL_ESCL=('DX-DY-DZ',), "
                "COEF_ESCL=(1.0,))"
            ).format(master=master, ddl_mait=ddl_mait, slave=slave)
            result.setdefault("LIAISON_RBE3", []).append(rendered)

        else:
            log(tr("WARNING: Onbekend coupling-type '{0}'. Genegeerd.",
                   "WARNING: Unknown coupling type '{0}'. Ignored.").format(
                c["type"]))
    return result


# ==========================================
# BUILDER VOOR LINEAIR-STATISCHE ANALYSE  (MECA_STATIQUE)
# ==========================================
def _build_lin_static(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Genereer study.comm en study.export voor een MECA_STATIQUE-analyse.

    Ondersteunt gemengde modellen met 1D (balk), 2D (schaal) en 3D elementen.

    Parameters
    ----------
    work_dir   : str  - Werkmap voor alle gegenereerde bestanden.
    model_data : dict - Uitvoer van extract_aster_data_from_liml().
    msh_path   : str  - Pad naar het mesh (ASTER-formaat, bridge_mesh.py).
    resu_name  : str  - Bestandsnaam voor het .resu-resultaatbestand.
    analysis   : dict - Actieve analyse-config (uit CONFIG_BRIDGE["analyses"]).

    Returns
    -------
    str of None - Pad naar study.export bij succes, anders None.
    """
    log("--- Generating Aster Files (MECA_STATIQUE) ---")
    comm_path = os.path.join(work_dir, run_name(".comm"))
    if not _check_linear(model_data):
        return None
    # Bezwijkgrenzen (#ASTER-BEZWIJKEN, Eps_p_max) werken alleen
    # niet-lineair: failure_plan meldt dat (WARNING + skipped_loads) en
    # geeft hier altijd een leeg plan.
    bridge_failure.failure_plan(
        model_data, analysis,
        lambda mat: _relation_for(model_data, mat), _deformation_for)

    # --------------------------------------------------
    # PRE-PROCESSING: collapse tijdshistorie naar laatste waarde.
    # MECA_STATIQUE is statisch; tijdshistorie wordt alleen ondersteund
    # in STAT_NON_LINE. Voor elke BC met lijst-waarden in aster_dict
    # (gegenereerd door ForceBC met <x time="...">) nemen we de laatste
    # tijdsstap-waarde en loggen we een waarschuwing.
    #
    # Plastic curves (model_data["materials"][...]["plastic_curve"]) worden
    # genegeerd: DEFI_MATERIAU krijgt alleen ELAS, COMPORTEMENT is impliciet
    # elastisch in MECA_STATIQUE.
    # --------------------------------------------------
    for bc in model_data["bcs"]:
        new_dict = {}
        for k, v in bc["aster_dict"].items():
            if isinstance(v, list):
                last_val = v[-1][1] if v else 0.0
                log(tr("WARNING: Tijdsstap-belasting {0} op '{1}' is "
                       "gecollapsed naar laatste waarde {2} voor "
                       "MECA_STATIQUE. Gebruik nonlin_static_3d voor "
                       "volledige tijdshistorie.",
                       "WARNING: Time-step load {0} on '{1}' is "
                       "collapsed to its last value {2} for "
                       "MECA_STATIQUE. Use nonlin_static_3d for the "
                       "full time history.").format(
                        k, bc["selection"], last_val))
                new_dict[k] = last_val
            else:
                new_dict[k] = v
        bc["aster_dict"] = new_dict

    # --------------------------------------------------
    # BLOK A: DEFI_GROUP (nodeselections, slave-knopen uit vlakken)
    #         + eventueel CREA_MAILLAGE MODI_MAILLE (COQUE_3D) en
    #         MODI_MAILLAGE ORIE_PEAU (drukvlakken)
    # --------------------------------------------------
    defigroup_block = _build_defigroup_block(model_data)

    # --------------------------------------------------
    # BLOK B + C: AFFE_MODELE + AFFE_CARA_ELEM
    # --------------------------------------------------
    model_block     = _build_model_block(model_data)
    # XFEM (#ASTER-XFEM, bridge_xfem): het gezonde model heet model_sain,
    # daarna DEFI_FISS_XFEM + MODI_MODELE_XFEM; lasten en solve op 'model'
    model_block = bridge_xfem.model_block(model_data, analysis, model_block)
    if model_block is None:
        return None
    xfem = bridge_xfem.active(model_data)
    cara_elem_block = _build_cara_elem_block(model_data)

    cara_elem_ref = "    CARA_ELEM=cara,\n" if _has_cara(model_data) else ""

    # --------------------------------------------------
    # BLOK D: DEFI_MATERIAU per materiaal
    #
    # RHO wordt ALTIJD opgenomen (default 0.0). Dit voorkomt een
    # Code-Aster ALARM bij gebruik van PESANTEUR op materialen
    # zonder dichtheid, en zorgt dat zelfgewicht-loads correct
    # worden uitgerekend voor materialen waar wel RHO is opgegeven.
    #
    # ALPHA (thermische uitzetting) alleen met thermal stress
    # (_build_materials_block; AFFE_VARC in _build_fieldmat_block).
    # --------------------------------------------------
    materials_block = _build_materials_block(model_data, analysis)

    # --------------------------------------------------
    # BLOK E: AFFE_MATERIAU (materiaaltoewijzing per GROUP_MA)
    # --------------------------------------------------
    fieldmat_block = _build_fieldmat_block(model_data)

    # --------------------------------------------------
    # BLOK F: AFFE_CHAR_MECA (BC's, belastingen, couplings)
    #
    # Pre-render alle _F(...)-strings per Code-Aster keyword in een
    # OrderedDict. Standaard BCs eerst, dan couplings (LIAISON_*).
    #
    # Empty-selection support: gravity (<gravity>) heeft GEEN
    # selection-attribuut. Voor zulke BCs wordt geen GROUP_NO/GROUP_MA
    # prefix toegevoegd; de _F(...) bevat uitsluitend de Code-Aster
    # keywords (GRAVITE=..., DIRECTION=(...)).
    # --------------------------------------------------
    charges = _build_charges(model_data)
    loads_block, excit_clause = _render_charges(charges, model_data)
    if not excit_clause:
        # MECA_STATIQUE zonder EXCIT: <EXCEPTION> SUPERVIS_4 (Code-Aster
        # 17.4, QA-run); zonder belasting is er ook niets te rekenen.
        log(tr("ERROR: Geen randvoorwaarden of belastingen in het model (of "
               "alle overgeslagen, zie de meldingen hierboven). Voeg in "
               "Mecway voorwaarden en belastingen toe.",
               "ERROR: No constraints or loads in the model (or all "
               "skipped, see the messages above). Add constraints and "
               "loads in Mecway."))
        return None

    # --------------------------------------------------
    # BLOK G: CALC_CHAMP, POST_RELEVE_T, IMPR_TABLE
    # (element-type-afhankelijk)
    # --------------------------------------------------
    # Foutschatter (instelling error_estimator): CALC_ERREUR in een eigen
    # resultaat res_err (_error_estimator_block).
    err_groups = _error_estimator_groups(model_data, analysis)
    if err_groups and xfem:
        # CALC_ERREUR op het XFEM-model: niet gebouwd (bridge_xfem); de
        # foutschatter staat standaard aan, dus geen WARNING
        log("INFO: Foutschatter (error_estimator) werkt niet samen met "
            "#ASTER-XFEM; geen foutschatting.")
        err_groups = []
    err_block = (_error_estimator_block(model_data, charges, err_groups)
                 if err_groups else "")
    if err_block and CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("INFO: Foutschatter: het veld gaat alleen via result_route "
               "'liml' naar Mecway; met 'tabel' alleen de globale fout in "
               "de log.",
               "INFO: Error estimator: the field only goes to Mecway with "
               "result_route 'liml'; with 'tabel' only the global error in "
               "the log."))
    # Vermoeiing (#ASTER-WOHLER + #ASTER-BLOK/-SIGNAAL, bridge_fatigue):
    # na CALC_CHAMP, de velden damage/life gaan mee in de export
    fatigue = bridge_fatigue.fatigue_block(model_data, analysis, work_dir)
    if fatigue is None:
        return None
    if xfem and fatigue[0]:
        # Vermoeiing op het XFEM-resultaat: NIET gebouwd/geverifieerd
        log(tr("WARNING: Vermoeiing werkt niet samen met #ASTER-XFEM; geen "
               "vermoeiingsberekening.",
               "WARNING: Fatigue does not work together with #ASTER-XFEM; "
               "no fatigue analysis."))
        fatigue = ("", "")
    if xfem:
        # XFEM: velden via POST_CHAM_XFEM + PROJ_CHAMP op het oorspronkelijke
        # mesh, i.p.v. CALC_CHAMP op het XFEM-model (bridge_xfem)
        calc_champ_block = (bridge_xfem.result_block(model_data) +
                            _custom_code(model_data, 'post'))
    else:
        calc_champ_block = (_build_calc_champ_block(model_data) + err_block +
                            _custom_code(model_data, 'post') + fatigue[0])
    postreleve_block  = _build_postreleve_block(model_data)
    impr_table_block  = _build_impr_table_block(model_data)
    postreleve_block, impr_table_block = _results_route(
        work_dir, model_data, postreleve_block, impr_table_block, "double",
        extra=fatigue[1])
    # Breukmechanica (SCHEUR_-selecties): na de resultaatexport, zodat een
    # fout daar de resultaten in Mecway niet tegenhoudt (bridge_fracture)
    fracture_block = bridge_fracture.fracture_block(
        model_data, analysis, work_dir, _material_concepts(model_data),
        excit_clause, cara_elem_ref)
    if fracture_block is None:
        return None
    # XFEM: K en G per scheur, ook na de export (bridge_xfem.k_block)
    xfem_block = bridge_xfem.k_block(model_data, analysis, work_dir)
    if xfem_block is None:
        return None

    # --------------------------------------------------
    # BESTANDEN SCHRIJVEN
    # --------------------------------------------------
    try:
        template_content = _read_template(analysis["template"])
        _write_comm(comm_path, template_content.format(
            defigroup_block  = defigroup_block,
            model_block      = model_block,
            cara_elem_block  = cara_elem_block,
            materials_block  = materials_block,
            fieldmat_block   = fieldmat_block,
            loads_block      = loads_block,
            excit_clause     = excit_clause,
            cara_elem_ref    = cara_elem_ref,
            solveur_ref      = _build_lin_solveur_ref(analysis),
            calc_champ_block = calc_champ_block,
            postreleve_block = postreleve_block,
            impr_table_block = impr_table_block,
            impr_resu_block  = (_build_impr_resu_block(model_data) +
                                fracture_block + xfem_block),
        ))
        log("SUCCESS: .comm geschreven naar '{0}'.".format(comm_path))

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
            time_limit   = analysis.get("time_limit",   600),
            memory_limit = analysis.get("memory_limit", 2048),
            ncpus    = CONFIG_BRIDGE["ncpus"],
            comm     = comm_path,
            msh      = msh_path,
            mess     = os.path.join(work_dir, run_name(".mess")),
        ) + (_export_result_lines(work_dir, resu_name) +
             bridge_xfem.export_lines(model_data, work_dir))
        with open(export_path, 'w') as f:
            f.write(export_content)
        log("SUCCESS: .export geschreven naar '{0}'.".format(export_path))

        return export_path

    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}. "
               "Controleer de .comm-template op {{placeholder}}-namen.",
               "ERROR: Template placeholder missing: {0}. "
               "Check the .comm template for {{placeholder}} names.")
            .format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren solver-bestanden mislukt: {0}",
               "ERROR: Generating solver files failed: {0}").format(str(e)))

    return None


def _nonlinear_parts(model_data):
    """Namen van de onderdelen die MECA_STATIQUE niet kan (contact,
    compression only, gaps, tension only); [] als er geen zijn."""
    found = []
    if any(bc["type"] == "compressiononly" for bc in model_data["bcs"]):
        found.append("compression only support")
    if model_data.get("contacts"):
        found.append("contact (contact2)")
    kinds = set(s["kind"] for s in model_data.get(
        "discrete_sections", {}).values())
    if "gap" in kinds:
        found.append(tr("gap-elementen", "gap elements"))
    if model_data.get("cable_sections"):
        found.append(tr("tension-only-elementen", "tension only elements"))
    return found


def _check_linear(model_data, what=None):
    """
    MECA_STATIQUE kan geen niet-lineaire randvoorwaarden of elementen.
    Mecway rekent compression only en gaps in Static 3D met de interne
    solver iteratief (manual v33 par. 9.5, 7.9); Code-Aster vraagt
    STAT_NON_LINE (LIAISON_UNIL, DIS_CHOC, CABLE). Niet stil lineariseren:
    ERROR en stoppen.
    """
    found = _nonlinear_parts(model_data)
    if model_data.get("contacts"):
        # Contact (DEFI_CONTACT) kan alleen in STAT_NON_LINE/DYNA_NON_LINE;
        # _build_lin_static schreef het niet en meldde niets. Verlijmd
        # contact (LIAISON_MAIL, model_data["bonded"]) werkt wel lineair.
        for c in model_data["contacts"]:
            model_data.setdefault("skipped_loads", []).append(
                tr("contact '{0}' / '{1}' (lineaire analyse)",
                   "contact '{0}' / '{1}' (linear analysis)").format(
                    c.get("master", ""), c.get("slave", "")))
    if found and what:
        # Modaal/knik (_build_modal): niet-lineaire onderdelen kunnen niet.
        log(tr("ERROR: {0} kan niet in {1} (lineair). Verwijder het uit "
               "het model of onderdruk het in een configuratie.",
               "ERROR: {0} is not possible in {1} (linear). Remove it "
               "from the model or suppress it in a configuration.").format(
                   ", ".join(found), what))
        return False
    if found:
        log(tr("ERROR: {0} vraagt een niet-lineaire berekening (Code-Aster "
               "STAT_NON_LINE). Kies in het startscherm de analyse "
               "'nonlin_static_3d'.",
               "ERROR: {0} requires a nonlinear analysis (Code-Aster "
               "STAT_NON_LINE). Choose the analysis 'nonlin_static_3d' "
               "on the start screen.").format(", ".join(found)))
        return False
    return True


# ==========================================
# HULPFUNCTIES VOOR STAT_NON_LINE
# ==========================================

def _safe_func_name(prefix, selection, axis):
    """
    Genereer een geldige Code-Aster Python-variabelenaam voor een
    DEFI_FONCTION. Selection-namen kunnen niet-alfanumerieke karakters
    bevatten; die vervangen we door underscore.
    """
    safe_sel = re.sub(r'\W+', '_', selection)[:24]
    return "{0}_{1}_{2}".format(prefix, safe_sel, axis)


def _load_func_names(model_data):
    """
    Unieke DEFI_FONCTION-naam per tijdsafhankelijke BC-component
    (kracht, opgelegde verplaatsing of rotatie).

    Twee krachten op dezelfde selectie, of selecties die pas na het afkappen
    in _safe_func_name verschillen, zouden dezelfde naam krijgen; een
    volgnummer (_2, _3, ...) maakt de naam uniek. _collect_load_funcs() en
    _build_charges() gebruiken allebei deze mapping, zodat definitie en
    gebruik van de functie dezelfde naam hebben.

    Returns
    -------
    OrderedDict  {(bc-index in model_data["bcs"], kw_axis): func_name}
    """
    names = OrderedDict()
    used  = set()
    for idx, bc in enumerate(model_data["bcs"]):
        for kw_axis, value in bc["aster_dict"].items():
            if not isinstance(value, list):
                continue
            base = _safe_func_name("FN", bc["selection"], kw_axis)
            name = base
            n = 2
            while name in used:
                name = "{0}_{1}".format(base, n)
                n += 1
            used.add(name)
            names[(idx, kw_axis)] = name
    return names


def _collect_load_funcs(model_data):
    """
    Verzamel alle tijdsafhankelijke krachtcomponenten uit model_data["bcs"].

    Returns
    -------
    list of (func_name, history) tuples
        func_name : str  Code-Aster Python-variabelenaam voor de DEFI_FONCTION
        history   : list of (t, value) tuples in SI-eenheden
    """
    bcs = model_data["bcs"]
    return [(func_name, bcs[idx]["aster_dict"][kw_axis])
            for (idx, kw_axis), func_name
            in _load_func_names(model_data).items()]


def _to_aster_traction_curve(mat_name, curve, e_mod, definition):
    """
    Zet een Mecway-hardingscurve om naar een Code-Aster TRACTION-curve.

    Code-Aster-definitie (U4.43.01 DEFI_MATERIAU, par. 5.1.1, operand SIGM;
    gecontroleerd in de v18-documentatie op codeaster.gitlab.io):
      - SIGM is de spanning als functie van de TOTALE rek (parameter EPSI).
      - De ordinaat van het eerste punt is de elastische grens; een punt
        met abscis nul is uitdrukkelijk NIET toegestaan.

    Mecway leest <hardeningcurve strain="..."> als TOTALE rek (headless
    gecontroleerd met Mecway/CCX bij de docs-review: curve (0,0), (sy/E, sy),
    ... gaf dezelfde spanning als de bridge met 'total'). Daarom:
      definition = 'plastic' : strain = plastische rek.
                               EPSI = strain + stress / E
                               (eerste punt (0, sy) -> (sy/E, sy)).
      definition = 'total'   : strain = totale rek.
                               Een beginpunt (0, 0) wordt verwijderd
                               (de elastische tak volgt uit ELAS/E).
      definition = 'auto'    : afgeleid uit het eerste punt:
                               (0, 0) of eps > 0 -> 'total' (zoals Mecway;
                                 de hellingcontrole hieronder waarschuwt
                                 als het punt niet op de elastische lijn
                                 ligt)
                               (0, sigma>0)      -> 'plastic' + WARNING
                                 (Mecway zelf leest dit als totale rek).

    Parameters
    ----------
    mat_name   : str    Materiaalnaam (alleen voor logging).
    curve      : list   (strain, stress)-tuples in SI, oplopend gesorteerd.
    e_mod      : float  Elasticiteitsmodulus E [Pa] uit ELAS.
    definition : str    'auto', 'plastic' of 'total'.

    Returns
    -------
    list of (eps_tot, sigma) tuples

    Raises
    ------
    ValueError  bij een curve die niet aan de Code-Aster-definitie kan
                voldoen of een dubbelzinnige rekdefinitie.
    """
    if not curve:
        raise ValueError(tr("Materiaal '{0}': lege hardingscurve.",
                            "Material '{0}': empty hardening curve.")
                         .format(mat_name))
    if e_mod <= 0.0:
        raise ValueError(tr("Materiaal '{0}': E={1} is ongeldig voor de "
                            "omrekening van de hardingscurve.",
                            "Material '{0}': E={1} is invalid for "
                            "converting the hardening curve.").format(
                             mat_name, e_mod))

    first_strain, first_stress = curve[0]

    if definition == "auto":
        if first_strain == 0.0 and first_stress > 0.0:
            definition = "plastic"
            log(tr("WARNING: Materiaal '{0}': de hardingscurve begint bij "
                   "(0, {1}); de bridge leest de rek als plastische rek. "
                   "Mecway leest dezelfde curve als totale rek, dus de "
                   "Mecway-oplossing kan afwijken. Zet "
                   "'plastic_strain_definition' op 'plastic' of 'total' om "
                   "deze melding te vermijden.",
                   "WARNING: Material '{0}': the hardening curve starts at "
                   "(0, {1}); the bridge reads the strain as plastic strain. "
                   "Mecway reads the same curve as total strain, so the "
                   "Mecway solution may differ. Set "
                   "'plastic_strain_definition' to 'plastic' or 'total' to "
                   "avoid this message.").format(mat_name, first_stress))
        else:
            # (0, 0) of een eerste punt met rek > 0: totale rek, zoals Mecway
            definition = "total"
        log("INFO: Materiaal '{0}': rekdefinitie hardingscurve afgeleid "
            "als '{1}' (eerste punt ({2}, {3})).".format(
                mat_name, definition, first_strain, first_stress))

    if definition == "plastic":
        aster_curve = [(eps_p + sig / e_mod, sig) for eps_p, sig in curve]
        if first_strain != 0.0:
            log(tr("WARNING: Materiaal '{0}': eerste plastische rek is {1} "
                   "i.p.v. 0; het eerste punt ligt dan niet op de "
                   "elastische lijn (helling E).",
                   "WARNING: Material '{0}': first plastic strain is {1} "
                   "instead of 0; the first point then does not lie on the "
                   "elastic line (slope E).").format(mat_name, first_strain))

    elif definition == "total":
        aster_curve = [(eps, sig) for eps, sig in curve if eps != 0.0]
        dropped = [(eps, sig) for eps, sig in curve if eps == 0.0]
        for eps, sig in dropped:
            if sig != 0.0:
                raise ValueError(tr(
                    "Materiaal '{0}': punt ({1}, {2}) is bij totale rek "
                    "fysisch onmogelijk (spanning zonder rek).",
                    "Material '{0}': point ({1}, {2}) is physically "
                    "impossible for total strain (stress without strain).")
                    .format(mat_name, eps, sig))
        if dropped:
            log("INFO: Materiaal '{0}': beginpunt (0, 0) verwijderd; "
                "Code-Aster staat geen abscis nul toe.".format(mat_name))
        if aster_curve:
            eps1, sig1 = aster_curve[0]
            slope    = sig1 / eps1
            rel_diff = abs(slope - e_mod) / e_mod
            if rel_diff > 0.05:
                # Doorgeven zoals aangeleverd, met waarschuwing (niet
                # stilzwijgend corrigeren).
                log(tr("WARNING: Materiaal '{0}': helling tot het eerste "
                       "punt = {1} Pa, maar E = {2} Pa (verschil "
                       "{3}). Het eerste punt hoort de elastische grens "
                       "op de elastische lijn te zijn.",
                       "WARNING: Material '{0}': slope up to the first "
                       "point = {1} Pa, but E = {2} Pa (difference "
                       "{3}). The first point should be the yield point "
                       "on the elastic line.").format(
                        # %-opmaak (zie _warn_large_rotations)
                        mat_name, "%.3e" % slope, "%.3e" % e_mod,
                        "%.0f%%" % (100.0 * rel_diff)))

    else:
        raise ValueError(tr(
            "Ongeldige 'plastic_strain_definition' = '{0}'. Toegestaan: "
            "'auto', 'plastic', 'total'.",
            "Invalid 'plastic_strain_definition' = '{0}'. Allowed: "
            "'auto', 'plastic', 'total'.").format(definition))

    # --- Controles op het Code-Aster-resultaat ---
    if not aster_curve:
        raise ValueError(tr("Materiaal '{0}': na omrekening blijft geen "
                            "punt over.",
                            "Material '{0}': no point remains after "
                            "conversion.").format(mat_name))
    for eps, sig in aster_curve:
        if eps <= 0.0:
            raise ValueError(tr(
                "Materiaal '{0}': punt met abscis EPSI={1} <= 0 is niet "
                "toegestaan in TRACTION.",
                "Material '{0}': point with abscissa EPSI={1} <= 0 is not "
                "allowed in TRACTION.").format(mat_name, eps))
    for i in range(1, len(aster_curve)):
        if aster_curve[i][0] <= aster_curve[i - 1][0]:
            raise ValueError(tr(
                "Materiaal '{0}': EPSI niet strikt oplopend tussen punt "
                "{1} ({2}) en punt {3} ({4}).",
                "Material '{0}': EPSI not strictly increasing between "
                "point {1} ({2}) and point {3} ({4}).").format(
                    mat_name, i, aster_curve[i - 1][0],
                    i + 1, aster_curve[i][0]))
    if len(aster_curve) == 1:
        log(tr("WARNING: Materiaal '{0}': TRACTION-curve heeft maar 1 punt "
               "(alleen de elastische grens).",
               "WARNING: Material '{0}': TRACTION curve has only 1 point "
               "(only the yield point).").format(mat_name))

    return aster_curve


def _build_plastic_curves_block(model_data, analysis):
    """
    Genereer DEFI_FONCTION-aanroepen voor elke plastische hardingscurve.

    De Mecway-curve wordt eerst via _to_aster_traction_curve() omgezet
    naar de Code-Aster TRACTION-definitie (totale rek, geen abscis nul).
    De rekdefinitie komt uit analysis["plastic_strain_definition"]
    ('auto' als de sleutel ontbreekt).

    Returns
    -------
    (str, dict)
        - String met alle DEFI_FONCTION-blokken (kant-en-klaar voor de
          template).
        - Mapping {mat_name: func_var_name} voor gebruik in DEFI_MATERIAU
          TRACTION-clausule.

    Raises
    ------
    ValueError  doorgegeven uit _to_aster_traction_curve().
    """
    blocks = []
    func_map = {}
    definition = analysis.get("plastic_strain_definition", "auto")

    for mat_name, props in model_data["materials"].items():
        raw_curve = props.get("plastic_curve")
        if not raw_curve:
            continue

        # OpenRadioss PLAS_TAB levert zelf de definitie (bridge_radioss)
        curve = _to_aster_traction_curve(
            mat_name, raw_curve, props["E"],
            props.get("curve_definition", definition))

        # Zelfde nummer als het materiaal (MAT_<n> -> TRAC_<n>)
        func_var = _material_concepts(model_data)[mat_name].replace(
            "MAT_", "TRAC_", 1)
        func_map[mat_name] = func_var
        # Ook voor het slappe materiaal bij bezwijken (bridge_failure)
        model_data.setdefault("_traction_curves", {})[mat_name] = curve

        # VALE-tuple: alternerend EPSI (totale rek), SIGM, EPSI, SIGM, ...
        vale_parts = []
        for strain, stress in curve:
            vale_parts.append("{0}, {1}".format(strain, stress))
        vale_str = ",\n          ".join(vale_parts)

        blocks.append(
            _mat_comment(mat_name) +
            "{func_var} = DEFI_FONCTION(\n"
            "    NOM_PARA='EPSI',\n"
            "    NOM_RESU='SIGM',\n"
            "    VALE=({vale}),\n"
            "    PROL_DROITE='LINEAIRE',\n"
            "    PROL_GAUCHE='CONSTANT',\n"
            ")".format(func_var=func_var, vale=vale_str)
        )

    if not blocks:
        return "#-- geen plastische curves in dit model --\n", func_map

    return "\n\n".join(blocks) + "\n", func_map


def _build_load_funcs_block(load_funcs):
    """
    Genereer DEFI_FONCTION-aanroepen voor elke tijdsafhankelijke kracht.

    Parameters
    ----------
    load_funcs : list of (func_name, history) tuples

    Returns
    -------
    str  Kant-en-klaar blok voor de template.
    """
    if not load_funcs:
        return "#-- geen tijdsafhankelijke belastingen in dit model --\n"

    blocks = []
    for func_name, history in load_funcs:
        vale_parts = []
        for t, val in history:
            # !r: IronPython 2.7 str() geeft 12 cijfers; de versnellings-
            # stoten van _explicit_accelerations willen volle precisie
            # (CPython 3: gelijk aan str()).
            vale_parts.append("{0!r}, {1!r}".format(t, val))
        vale_str = ",\n          ".join(vale_parts)

        blocks.append(
            "{name} = DEFI_FONCTION(\n"
            "    NOM_PARA='INST',\n"
            "    VALE=({vale}),\n"
            "    PROL_DROITE='CONSTANT',\n"
            "    PROL_GAUCHE='CONSTANT',\n"
            ")".format(name=func_name, vale=vale_str)
        )

    return "\n\n".join(blocks) + "\n"


_LISTINST_ECHEC = (
    # DEFI_LIST_INST: bij divergentie wordt de stap in 4 gedeeld (tot 6
    # niveaus). Met alleen een DEFI_LIST_REEL knipt STAT_NON_LINE de stap
    # niet automatisch (U4.51.03 INCREMENT; melding SUBDIVISE_3).
    "listinst = DEFI_LIST_INST(\n"
    "    DEFI_LIST=_F(LIST_INST=times),\n"
    "    ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE',\n"
    "             SUBD_METHODE='MANUEL', SUBD_PAS=4,\n"
    "             SUBD_NIVEAU=6),\n"
    ")\n")


def _mecway_static_times(load_funcs, model_data):
    """
    Rekentijden van niet-lineair statisch met Mecway's stapgrootte
    (<timesteps timeperiod stepsize>), of None
    zonder stapgrootte (dan substeps_per_interval, _build_listinst_block).

    Mecway rekent met een vaste stap van 0 tot de periode en schrijft elke
    stap als uitvoertijd (L30 "Time step size"; bijv. Samples/PipeClip
    0,05 s). De bridge rekent dezelfde stappen dt, 2 dt, ..., periode, plus
    de knikken van de lasttabellen die tussen twee stappen vallen (zodat het
    lastpad exact gevolgd wordt: plasticiteit, ontlasten, vermoeiing).
    substeps_per_interval geldt hier niet: een fijner lastpad = een kleinere
    Time step size in Mecway. Lasttijden na de periode vallen weg (Mecway
    rekent tot de periode). Een periode die geen veelvoud is van de stap
    eindigt hier met een kortere stap, en automatictimestepping (Mecway past
    de stap aan) wordt niet nagebootst; beide NIET in Mecway geverifieerd.
    Elke rekenstap wordt gearchiveerd (statisch, geen ARCHIVAGE).
    """
    ts = (model_data or {}).get("timesteps") or {}
    dt = ts.get("stepsize") or 0.0
    t_end = ts.get("period") or 0.0
    if dt <= 0.0 or t_end <= 0.0:
        return None
    n = int(math.ceil(t_end / dt - 1.0e-9))
    grid = [_round_time(k * dt) for k in range(1, n)] + [t_end]
    later = sorted(set(t for _, h in load_funcs for t, _ in h
                       if t > t_end * (1.0 + 1.0e-9)))
    if later:
        log("INFO: Lasttabel loopt tot t = {0} s; gerekend tot Mecway's "
            "periode {1} s (zoals Mecway).".format(later[-1], t_end))
    kinks = [t for _, h in load_funcs for t, _ in h if 0.0 < t < t_end]
    times = _merge_times([0.0] + grid + kinks, t_end, prefer=grid)
    extra = len(times) - 1 - len(grid)
    log("INFO: Tijdstappen uit Mecway: stap {0} s tot {1} s, {2} "
        "rekenstappen{3}; substeps_per_interval niet gebruikt.".format(
            dt, t_end, len(times) - 1,
            " (waarvan {0} op knikken van de lasttabel)".format(extra)
            if extra > 0 else ""))
    return times


def _build_listinst_block(load_funcs, analysis, model_data=None):
    """
    Genereer DEFI_LIST_REEL + DEFI_LIST_INST voor de tijdsdiscretisatie
    van niet-lineair statisch.

    Met Mecway's <timesteps stepsize> (_mecway_static_times): Mecway's
    stappen tot de periode plus de knikken van de lasttabellen; elke
    rekenstap is een uitvoertijd. Zonder stapgrootte:
    alle unieke tijdspunten van de lastfuncties met substeps_per_interval
    stappen per interval. In beide gevallen knipt DEFI_LIST_INST een stap
    die niet convergeert.

    Returns
    -------
    (block_str, t_end)
        block_str : DEFI_LIST_REEL aanroep
        t_end     : float  laatste tijdspunt; nodig voor POST_RELEVE_T INST=...
    """
    mecway_times = _mecway_static_times(load_funcs, model_data)
    if mecway_times:
        block_str = (
            "times = DEFI_LIST_REEL(\n"
            "    VALE=({0}),\n"
            ")\n".format(", ".join("{0!r}".format(t) for t in mecway_times))
            + _LISTINST_ECHEC)
        return block_str, mecway_times[-1]

    nb_substeps = analysis.get("substeps_per_interval", 10)
    t_default   = analysis.get("default_time_end", 1.0)

    # Verzamel unieke tijdspunten
    all_times = set()
    for _, history in load_funcs:
        for t, _ in history:
            all_times.add(t)

    if not all_times:
        # Geen tijdsafhankelijke belastingen: 0 -> default_time_end
        all_times = {0.0, t_default}

    # Bijna-dubbele tijden (verschillende lasthistories) samenvoegen:
    # DISCRETISATION_87 (zie _merge_times).
    sorted_times = sorted(all_times)
    sorted_times = _merge_times(sorted_times,
                                max(abs(sorted_times[0]),
                                    abs(sorted_times[-1])))

    # DEBUT = eerste tijdspunt
    debut = sorted_times[0]

    # INTERVALLE = lijst van _F(JUSQU_A=..., NOMBRE=...) per segment
    intervalles = []
    for i in range(1, len(sorted_times)):
        intervalles.append(
            "        _F(JUSQU_A={0}, NOMBRE={1}),".format(
                sorted_times[i], nb_substeps)
        )

    if not intervalles:
        # Slechts een tijdspunt: kunstmatige t_end nodig
        intervalles.append(
            "        _F(JUSQU_A={0}, NOMBRE={1}),".format(
                debut + t_default, nb_substeps))
        t_end = debut + t_default
    else:
        t_end = sorted_times[-1]

    block_str = (
        "times = DEFI_LIST_REEL(\n"
        "    DEBUT={debut},\n"
        "    INTERVALLE=(\n"
        "{intervalles}\n"
        "    ),\n"
        ")\n"
    ).format(debut=debut, intervalles="\n".join(intervalles)) + \
        _LISTINST_ECHEC

    return block_str, t_end


_LARGE_DEFORMATIONS = ("GROT_GDEP", "GREEN_LAGRANGE", "GDEF_LOG",
                       "SIMO_MIEHE")


def _deformation_for(modelisation, relation, chosen, elset_name):
    """
    DEFORMATION per elset bij de keuze "deformation" van de analyse. Grote
    verplaatsingen gaan in Code-Aster 17.4 niet met een vorm voor alles
    (nagelopen met runs op een gemengd model):
      volume ELAS          : GREEN_LAGRANGE (GROT_GDEP mag niet op 3D,
                             COMPOR5_22) of GDEF_LOG als dat gekozen is;
      volume plastisch     : GDEF_LOG (GREEN_LAGRANGE geweigerd,
                             COMPOR1_44) of SIMO_MIEHE als gekozen, behalve
                             bij VMIS_CINE_LINE (SIMO_MIEHE geweigerd,
                             COMPOR1_44 in een QA-run): dan GDEF_LOG;
      DKT/DST              : GREEN_LAGRANGE (GROT_GDEP convergeerde niet,
                             GDEF_LOG geweigerd COMPOR1_99). Met een
                             WARNING: in 17.4 gaf GREEN_LAGRANGE op DKT
                             dezelfde resultaten als PETIT (QA-run, geen
                             effect van grote rotaties);
      COQUE_3D             : GROT_GDEP (alarm COMPOR1_47: rotaties < 2 pi);
      balken POU_D_E/_T    : PETIT met een WARNING (grote rotaties vragen
                             POU_D_T_GD met ELAS_POUTRE_GR; GROT_GDEP op
                             POU_D_E convergeerde niet).
    PETIT en PETIT_REAC gaan ongewijzigd door.
    """
    if chosen not in _LARGE_DEFORMATIONS:
        return chosen
    plastic = relation.startswith("VMIS")
    if modelisation in ("3D", "3D_SI"):
        if plastic:
            if chosen == "SIMO_MIEHE" and relation == "VMIS_CINE_LINE":
                log("INFO: Elset '{0}': VMIS_CINE_LINE kan niet met "
                    "SIMO_MIEHE (COMPOR1_44); DEFORMATION='GDEF_LOG'."
                    .format(elset_name))
                return "GDEF_LOG"
            return "SIMO_MIEHE" if chosen == "SIMO_MIEHE" else "GDEF_LOG"
        return "GDEF_LOG" if chosen == "GDEF_LOG" else "GREEN_LAGRANGE"
    if modelisation in ("DKT", "DST"):
        if relation == "VMIS_CINE_LINE":
            # GREEN_LAGRANGE met VMIS_CINE_LINE: <EXCEPTION> COMPOR1_44
            # (catalogus van VMIS_CINE_LINE: PETIT, PETIT_REAC, GROT_GDEP,
            # GDEF_LOG; testrun Code-Aster 17.4). PETIT geeft op DKT
            # hetzelfde als GREEN_LAGRANGE (zie hierboven).
            log("INFO: Elset '{0}' ({1}): VMIS_CINE_LINE kan niet met "
                "GREEN_LAGRANGE (COMPOR1_44); DEFORMATION='PETIT'."
                .format(elset_name, modelisation))
            return "PETIT"
        log("INFO: Elset '{0}' ({1}): grote rotaties werken niet op "
            "DKT/DST-schalen in Code-Aster 17.4 (GREEN_LAGRANGE gaf dezelfde "
            "resultaten als kleine verplaatsingen, GROT_GDEP convergeerde "
            "niet); de schaal blijft geometrisch lineair. Kies op de "
            "pagina Elementen elem_shell = COQUE_3D voor grote rotaties."
            .format(elset_name, modelisation))
        return "GREEN_LAGRANGE"
    if modelisation == "COQUE_3D":
        return "GROT_GDEP"
    if modelisation.startswith("POU_D"):
        log("INFO: Elset '{0}' ({1}): grote verplaatsingen niet voor "
            "balken in de bridge (vraagt POU_D_T_GD met ELAS_POUTRE_GR); "
            "DEFORMATION='PETIT'.".format(elset_name, modelisation))
        return "PETIT"
    return "PETIT"


def _relation_for(model_data, mat_name):
    """RELATION van een (niet-veer-)materiaal: VMIS_ISOT_TRAC bij een
    hardingscurve, VMIS_ISOT_LINE/VMIS_CINE_LINE bij bilineaire
    plasticiteit, anders ELAS."""
    props = model_data["materials"].get(mat_name, {})
    if "plastic_curve" in props:
        return "VMIS_ISOT_TRAC"
    if props.get("plastic_bilinear"):
        return ("VMIS_CINE_LINE" if props["plastic_bilinear"]["kinematic"]
                else "VMIS_ISOT_LINE")
    return "ELAS"


def _build_comportement_block(model_data, analysis):
    """
    Genereer COMPORTEMENT-clausule voor STAT_NON_LINE en DYNA_NON_LINE.

    Per elset wordt de bijbehorende RELATION gekozen:
      - Veer-elsets (DIS_T)         : 'ELAS' (compatibel met DIS_T)
      - Kabels                      : 'CABLE' (met GROT_GDEP)
      - Overige elsets              : _relation_for: 'VMIS_ISOT_TRAC'
                                      (hardingscurve), 'VMIS_ISOT_LINE' /
                                      'VMIS_CINE_LINE' (bilineair) of 'ELAS'
      - POI1-discreten              : 'ELAS'
      - Gaps                        : 'DIS_CHOC'

    DEFORMATION komt uit analysis["deformation"] (in CONFIG_BRIDGE
    'GROT_GDEP'; zonder sleutel 'PETIT'); bij een
    keuze voor grote verplaatsingen kiest _deformation_for per elset de vorm
    die Code-Aster bij die MODELISATION/RELATION accepteert (U4.51.11 par.
    4.6; nagelopen met runs).
    """
    deformation = analysis.get("deformation", "PETIT")
    # Een WARNING per run (de details per elset staan als INFO in de log):
    # sinds GROT_GDEP de standaard is, zou anders elk niet-lineair model met
    # balken of DKT-schalen per elset waarschuwen.
    if deformation in _LARGE_DEFORMATIONS:
        small = sorted(e for e, m in model_data.get(
            "elset_modelisations", {}).items()
            if m in ("DKT", "DST") or str(m).startswith("POU_D"))
        if small:
            log(tr("WARNING: Grote verplaatsingen (DEFORMATION={0}) niet "
                   "voor balken en DKT/DST-schalen: {1} blijven geometrisch "
                   "lineair. Voor grote rotaties van schalen: elem_shell = "
                   "COQUE_3D (pagina Elementen).",
                   "WARNING: Large displacements (DEFORMATION={0}) not for "
                   "beams and DKT/DST shells: these elsets stay "
                   "geometrically linear: {1}. For large rotations of "
                   "shells: elem_shell = "
                   "COQUE_3D (Elements page).").format(
                deformation, ", ".join(small)))
    spring_mat_names = set(model_data.get("spring_materials", {}).keys())
    entries = []

    cables = model_data.get("cable_sections", {})
    for elset_name, mat_name in model_data["elsets"].items():
        if elset_name in cables:
            # Kabel: RELATION='CABLE' met grote verplaatsingen (U4.51.11:
            # CABLE alleen met GROT_GDEP; nagelopen met een run)
            entries.append(
                "        _F(GROUP_MA='{0}', RELATION='CABLE', "
                "DEFORMATION='GROT_GDEP'),".format(elset_name))
            continue
        if mat_name in spring_mat_names:
            relation = "ELAS"
        else:
            relation = _relation_for(model_data, mat_name)

        mod = model_data.get("elset_modelisations", {}).get(elset_name, "")
        if relation != "ELAS" and str(mod).startswith("POU_D"):
            # POU_D_E/POU_D_T met VMIS_* gaf <EXCEPTION> POUTRE0_61 "La loi
            # de comportement VMIS_ISOT_LINE n'est pas disponible pour les
            # poutres classiques. Utilisez les poutres multifibres." en
            # daarna FATAL (Code-Aster 17.4, testrun).
            name = bridge_failure.mecway_name(model_data, elset_name)
            log(tr("WARNING: Elset '{0}' ({1}): plasticiteit niet voor "
                   "balken (Code-Aster kent die alleen in multivezelbalken, "
                   "POUTRE0_61); de balk rekent elastisch.",
                   "WARNING: Elset '{0}' ({1}): plasticity not for beams "
                   "(Code-Aster supports it only in multifiber beams, "
                   "POUTRE0_61); the beam is computed elastically.").format(
                       name, mod))
            model_data.setdefault("skipped_loads", []).append(
                tr("plasticiteit van balk-elset '{0}' (elastisch gerekend)",
                   "plasticity of beam elset '{0}' (computed elastically)")
                .format(name))
            relation = "ELAS"
        entries.append(
            "        _F(GROUP_MA='{0}', RELATION='{1}', "
            "DEFORMATION='{2}'),".format(
                elset_name, relation,
                _deformation_for(mod, relation, deformation, elset_name))
        )

    # POI1-discreten (losse knopen, elastic support, knoopmassa's): ELAS
    # (ondersteund voor DISCRET, U4.51.11 par. 4.4.1.1); kleine
    # verplaatsingen (grote voor discreten NIET geverifieerd).
    for group in (list(model_data.get("poi1_groups", {})) +
                  list(model_data.get("discretes", {}))):
        entries.append(
            "        _F(GROUP_MA='{0}', RELATION='ELAS', "
            "DEFORMATION='{1}'),".format(
                group, "PETIT_REAC" if deformation == "PETIT_REAC"
                else "PETIT")
        )
    # Gaps: DIS_CHOC (U4.51.11; DEFI_MATERIAU DIS_CONTACT), na de elset
    # zodat deze occurrence de ELAS van de elset overschrijft.
    for group in model_data.get("gap_groups", {}):
        entries.append(
            "        _F(GROUP_MA='{0}', RELATION='DIS_CHOC'),".format(group))

    if not entries:
        # Geen elsets: fallback
        return ("    COMPORTEMENT=_F(TOUT='OUI', RELATION='ELAS', "
                "DEFORMATION='{0}'),\n".format(
                    _deformation_for("3D", "ELAS", deformation, "TOUT")))

    if len(entries) == 1:
        # Komma na de _F(...) is verplicht: hierna volgt INCREMENT=...
        return "    COMPORTEMENT={0},\n".format(
            entries[0].strip().rstrip(","))

    return "    COMPORTEMENT=(\n{0}\n    ),\n".format("\n".join(entries))


def _indent(block, prefix="    "):
    """Elke niet-lege regel van block extra inspringen (voor try:)."""
    return "".join(prefix + line if line.strip() else line
                   for line in block.splitlines(True))


# Grens waarboven een opgelegde rotatie als "groot" geldt (~6 graden).
_LARGE_ROTATION = 0.1


def _warn_large_rotations(model_data, analysis):
    """
    Waarschuw als een opgelegde rotatie groot is terwijl de kinematica klein
    is. POU_D_E, LIAISON_SOLIDE en DDL_IMPO DR* gaan dan uit van kleine
    rotaties; LIAISON_SOLIDE vraagt bij grote transformaties een volgende
    last (EXCIT TYPE_CHARGE='SUIV', U4.44.01 par. 5.16) en de balk
    POU_D_T_GD met DEFORMATION='GROT_GDEP'. De bridge past niets aan; de
    gebruiker kiest zelf (KNOWN_BUGS 11).
    """
    largest = 0.0
    for bc in model_data["bcs"]:
        if bc["type"] != "noderotation":
            continue
        for v in bc["aster_dict"].values():
            if isinstance(v, list):
                largest = max([largest] + [abs(x) for _, x in v])
            elif isinstance(v, float):
                largest = max(largest, abs(v))
    if largest > _LARGE_ROTATION:
        deformation = analysis.get("deformation", "PETIT")
        large = deformation in _LARGE_DEFORMATIONS
        log(tr("WARNING: Opgelegde rotatie tot {0} rad ({1} graden) "
               "met DEFORMATION='{2}'. {3}Balken, de opgelegde rotatie zelf "
               "(DDL_IMPO DR*) en starre koppelingen (LIAISON_SOLIDE) "
               "blijven kleine rotaties: drijf een star deel dan aan met "
               "een opgelegde verplaatsing via #ASTER (FORMULE, "
               "docs/ASTER_regels_voorbeelden.md voorbeeld 9). "
               "KNOWN_BUGS 11.",
               "WARNING: Imposed rotation up to {0} rad ({1} "
               "degrees) with DEFORMATION='{2}'. {3}Beams, the imposed "
               "rotation itself (DDL_IMPO DR*) and rigid couplings "
               "(LIAISON_SOLIDE) remain small rotations: drive a rigid part "
               "with an imposed displacement via #ASTER instead (FORMULE, "
               "docs/en/ASTER_lines_examples.md example 9). "
               "KNOWN_BUGS 11.").format(
                # %-opmaak: '{0:.3g}' gaf in IronPython een komma
                "%.3g" % largest, "%.0f" % math.degrees(largest),
                deformation,
                "" if large else tr(
                    "Zet in het startscherm DEFORMATION op GROT_GDEP (de "
                    "bridge kiest per elementtype de juiste vorm). ",
                    "Set DEFORMATION to GROT_GDEP on the start screen (the "
                    "bridge picks the right form per element type). ")))
        # Niet in skipped_loads: de rotatie wordt wel opgelegd (de melding
        # aan het eind zegt "NIET vertaald"; crit-review).


# ==========================================
# HULPFUNCTIES VOOR CONTACT EN DYNAMICA
# ==========================================
def _convergence_args(analysis):
    """
    Argumenten van CONVERGENCE (STAT_NON_LINE/DYNA_NON_LINE, catalogus
    c_convergence.py v17.4: RESI_GLOB_RELA en RESI_GLOB_MAXI mogen samen;
    VERIF='TOUT' (standaard) eist beide, VERIF='AU_MOINS_UN' een van beide;
    U4.51.03). convergence_criterion:
      - "RELA" (standaard): RESI_GLOB_RELA = convergence_resi_rela
        (restkracht / externe krachten);
      - "MAXI": RESI_GLOB_MAXI = convergence_resi_maxi (grootste
        restkracht in N). Voor een opgelegde beweging zonder weerstand:
        Samples/PipeClip bleef met RELA hangen op RESI_GLOB_RELA 1..13 bij
        een restkracht van ~1e-12 N (MECANONLINE9_7, stap 1); met MAXI
        1e-3 N rekent hij door (headless vergeleken met Mecway).
      - "RELA_OF_MAXI": beide met VERIF='AU_MOINS_UN': geconvergeerd als
        het relatieve OF het absolute criterium gehaald is (zoals CCX: een
        relatief criterium met een absolute ondergrens bij kleine
        krachten).
    """
    crit = "{0}".format(analysis.get("convergence_criterion", "RELA")).upper()
    iters = analysis.get("newton_max_iter", 20)
    maxi = "%.10g" % float(analysis.get("convergence_resi_maxi", 1.0e-3))
    if crit == "MAXI":
        return "RESI_GLOB_MAXI={0}, ITER_GLOB_MAXI={1}".format(maxi, iters)
    if crit == "RELA_OF_MAXI":
        return ("RESI_GLOB_RELA={0}, RESI_GLOB_MAXI={1}, "
                "VERIF='AU_MOINS_UN', ITER_GLOB_MAXI={2}").format(
                    analysis.get("convergence_resi_rela", 1.0e-6), maxi,
                    iters)
    if crit != "RELA":
        log(tr("WARNING: convergence_criterion '{0}' onbekend; RELA "
               "gebruikt.",
               "WARNING: convergence_criterion '{0}' unknown; RELA "
               "used.").format(crit))
    return "RESI_GLOB_RELA={0}, ITER_GLOB_MAXI={1}".format(
        analysis.get("convergence_resi_rela", 1.0e-6), iters)


def _quadratic_slave(model_data, group):
    """True als het slave-vlak kwadratische randelementen heeft."""
    faces = model_data.get("group_face_list", {}).get(group, [])
    return any(f.get("stype") in ("TRIA6", "QUAD8", "QUAD9", "TRIA7")
               for f in faces)


def _penalty_args(c, algo, friction):
    """Extra zone-argumenten voor ALGO_CONT='PENALISATION' (of "")."""
    if algo != "PENALISATION":
        return ""
    label = "'{0}' / '{1}'".format(c.get("master"), c.get("slave"))
    kn = c.get("kn", 0.0) or 0.0
    if kn <= 0.0:
        log(tr("WARNING: Contact {0}: geen normaalstijfheid in de .liml; "
               "Lagrange-contact (STANDARD) voor deze zone.",
               "WARNING: Contact {0}: no normal stiffness in the .liml; "
               "Lagrange contact (STANDARD) for this zone.").format(label))
        return ""
    out = ", ALGO_CONT='PENALISATION', COEF_PENA_CONT={0!r}".format(kn)
    if friction and c.get("friction", 0.0) > 0.0:
        kt = c.get("kt", 0.0) or 0.0
        if kt > 0.0:
            out += ", ALGO_FROT='PENALISATION', COEF_PENA_FROT={0!r}".format(
                kt)
        else:
            log("INFO: Contact {0}: tangentiele stijfheid 0; wrijving "
                "volgens Lagrange (ALGO_FROT STANDARD).".format(label))
    log("INFO: Contact {0}: PENALISATION, COEF_PENA_CONT={1} Pa/m.".format(
        label, "%.6g" % kn))
    return out


def _build_contact_block(model_data, analysis=None):
    """
    DEFI_CONTACT voor de contact2-paren (bridge_mesh.py heeft de namen
    afgestemd en de vlakken in skin_groups gezet).

    Mecway "unilateral elastic" is een penalty-contact met een stijfheid
    per oppervlak (manual v33 par. 9.9; normalstiffness > 0 verplicht).
    Code-Aster: continue formulering (U4.44.11), per zone ALGO_CONT
    (catalogus defi_contact.py v17.4):
      - contact_algo "STANDARD" (standaard): augmented Lagrangian, geen
        stijfheid nodig, geen penetratie;
      - "PENALISATION": COEF_PENA_CONT = Mecway's normalstiffness (Pa/m;
        contactdruk = coef x penetratie, zoals Mecway); met wrijving
        ALGO_FROT='PENALISATION' met COEF_PENA_FROT = tangentialstiffness,
        of Lagrange-wrijving als die 0 is. Getest (headless tegen Mecway):
        Samples/PipeClip volgt Mecway binnen ~3% (STANDARD verloor het
        contact), AssemblyWithContact Fixed_support rekent door (STANDARD:
        pivot op LAGS_C, MECANONLINE9_4).
    Wrijving: COULOMB met de wrijvingscoefficient. Returns (blok,
    "    CONTACT=..") of ("", "").
    """
    if analysis is None:
        analysis = CONFIG_BRIDGE["analyses"].get(get_active_analysis(), {})
    algo = "{0}".format(analysis.get("contact_algo", "STANDARD")).upper()
    if algo not in ("STANDARD", "PENALISATION"):
        log(tr("WARNING: contact_algo '{0}' onbekend; STANDARD gebruikt.",
               "WARNING: contact_algo '{0}' unknown; STANDARD used.").format(
            algo))
        algo = "STANDARD"
    pairs = model_data.get("contacts", [])
    unil = [bc for bc in model_data["bcs"] if bc.get("unil_zones")]
    if unil and pairs:
        for bc in unil:
            model_data.setdefault("skipped_loads", []).append(
                tr("compression only op '{0}'",
                   "compression only on '{0}'").format(bc["selection"]))
        log(tr("ERROR: Compression only en contact in een model: "
               "STAT_NON_LINE neemt een DEFI_CONTACT (CONTACT, catalogus "
               "v17.4) en LIAISON_UNIL is een eigen FORMULATION. "
               "Compression only NIET meegenomen.",
               "ERROR: Compression only and contact in one model: "
               "STAT_NON_LINE takes one DEFI_CONTACT (CONTACT, catalogue "
               "v17.4) and LIAISON_UNIL is a separate FORMULATION. "
               "Compression only NOT included."))
    elif unil:
        return _build_unil_block(unil)
    if not pairs:
        return "", ""
    friction = any(c.get("friction", 0.0) > 0.0 for c in pairs)
    custom = model_data.get("aster_custom", {})
    zone_extra = "".join(", " + bridge_custom.substitute(
        z, model_data.get("group_renames", {}),
        model_data.get("mesh_group_names", set()))
        for z in custom.get("zone", []))
    glob_extra = "".join("    {0},\n".format(bridge_custom.substitute(
        c, model_data.get("group_renames", {}),
        model_data.get("mesh_group_names", set())))
        for c in custom.get("contact", []))
    zones = []
    for c in pairs:
        z = "_F(GROUP_MA_MAIT='{0}', GROUP_MA_ESCL='{1}'".format(
            c["master"], c["slave"])
        if friction:
            z += ", COULOMB={0!r}".format(c.get("friction", 0.0))
        z += _penalty_args(c, algo, friction)
        if "INTEGRATION" not in zone_extra and _quadratic_slave(
                model_data, c["slave"]):
            # Kwadratisch slave-vlak: INTEGRATION 'AUTO' (= SIMPSON hier)
            # haalde de contact-patchtest niet (hex20, niet-passende
            # meshes: 1,5..4,6% fout, ook met penalty); 'NCOTES' (catalogus
            # defi_contact.py, ORDRE_INT 3) is exact (<= 0,01%, verificatie
            # NL-03), PipeClip (tet10) en AssemblyWithContact rekenen
            # gelijk door. Lineaire vlakken houden AUTO (knoopintegratie).
            z += ", INTEGRATION='NCOTES'"
        # Slaveknopen met een vaste voorwaarde (bridge_mesh.
        # _exclude_fixed_slaves); een eigen #ASTER-ZONE SANS_GROUP_NO gaat
        # voor (twee keer hetzelfde sleutelwoord is een Python-fout).
        if c.get("sans_groups") and "SANS_GROUP_NO" not in zone_extra:
            z += ", SANS_GROUP_NO={0}".format(_fmt_groups(c["sans_groups"]))
        zones.append(z + zone_extra + ")")
    block = (
        "contact = DEFI_CONTACT(\n"
        "    MODELE=model,\n"
        "    FORMULATION='CONTINUE',\n"
        "    FROTTEMENT='{0}',\n"
        "{2}"
        "    ZONE=(\n        {1},\n    ),\n"
        ")\n"
    ).format("COULOMB" if friction else "SANS",
             ",\n        ".join(zones), glob_extra)
    return block, "    CONTACT=contact,\n"


def _build_unil_block(unil_bcs):
    """
    Compression only (bridge_mesh._compression_only) als DEFI_CONTACT
    FORMULATION='LIAISON_UNIL' (U4.44.11 par. 3.8): per zone
    sum COEF_MULT_i * u_i < COEF_IMPO met COEF_MULT = (nx, ny, nz) op DX,
    DY, DZ en COEF_IMPO = 0: de knoop mag niet de steun in bewegen.
    COEF_MULT/COEF_IMPO zijn functies (catalogus defi_contact.py v17.4):
    DEFI_CONSTANTE. ALGO_CONT standaard 'CONTRAINTE' (actieve-
    voorwaardenmethode, hard zoals Mecway's interne solver).
    """
    consts = OrderedDict()

    def const(v):
        key = repr(float(v))
        if key not in consts:
            consts[key] = "CUNIL{0}".format(len(consts) + 1)
        return consts[key]
    zero = const(0.0)
    zones = []
    for bc in unil_bcs:
        for group, n in bc["unil_zones"]:
            zones.append(
                "_F(GROUP_NO='{0}', NOM_CMP=('DX', 'DY', 'DZ'), "
                "COEF_MULT=({1}, {2}, {3}), COEF_IMPO={4})".format(
                    group, const(n[0]), const(n[1]), const(n[2]), zero))
    block = "".join("{0} = DEFI_CONSTANTE(VALE={1})\n".format(name, key)
                    for key, name in consts.items())
    block += (
        "contact = DEFI_CONTACT(\n"
        "    MODELE=model,\n"
        "    FORMULATION='LIAISON_UNIL',\n"
        "    ZONE=(\n        {0},\n    ),\n"
        ")\n").format(",\n        ".join(zones))
    return block, "    CONTACT=contact,\n"


def _build_etat_init_block(model_data):
    """
    Beginsnelheid (Mecway <initialconditions><velocity>) als veld VITE
    voor ETAT_INIT van DYNA_NON_LINE (CREA_CHAMP AFFE, U4.72.04). Mecway:
    loodrechte componenten zijn nul (manual v33 par. 9.8). Returns
    (blok, "    ETAT_INIT=..") of ("", "").
    """
    vels = model_data.get("initial_velocities", [])
    if not vels:
        return "", ""
    affe = ["_F(TOUT='OUI', NOM_CMP=('DX', 'DY', 'DZ'), "
            "VALE=(0.0, 0.0, 0.0))"]
    for sel, target, v in vels:
        affe.append("_F({0}='{1}', NOM_CMP=('DX', 'DY', 'DZ'), "
                    "VALE=({2!r}, {3!r}, {4!r}))".format(
                        target, sel, v[0], v[1], v[2]))
    block = (
        "vite0 = CREA_CHAMP(\n"
        "    TYPE_CHAM='NOEU_DEPL_R',\n"
        "    OPERATION='AFFE',\n"
        "    MODELE=model,\n"
        "    AFFE=(\n        {0},\n    ),\n"
        ")\n"
    ).format(",\n        ".join(affe))
    return block, "    ETAT_INIT=_F(VITE=vite0),\n"


def _round_time(t):
    """Tijd op 12 significante cijfers: start + k * inc gaf bijv.
    3 * 5e-05 = 0.00015000000000000001 naast de lasttijd 0.00015."""
    return float("%.12g" % t)


def _merge_times(times, t_end, prefer=()):
    """
    Gesorteerde tijden zonder bijna-dubbele (verschil <= 1e-9 * t_end).
    Twee punten 1e-20 s uit elkaar gaven in DEFI_LIST_INST <EXCEPTION>
    DISCRETISATION_87 en geen resultaten (Code-Aster 17.4, testrun). Van
    een bijna-dubbel paar blijft een tijd uit prefer staan (bijv. de
    uitvoertijden, die ARCHIVAGE en de bezwijklus als rekenstap zoeken).
    """
    tol = 1.0e-9 * abs(t_end) if t_end else 1.0e-15
    prefer = set(prefer)
    out = []
    for t in sorted(set(times)):
        if out and t - out[-1] <= tol:
            if t in prefer and out[-1] not in prefer:
                out[-1] = t
            continue
        out.append(t)
    return out


def _output_times(model_data, analysis):
    """Uitvoertijden uit <timesteps> (regelmatig: start, start+inc, ...,
    periode), of [default_time_end] zonder tijdstappen. Afgerond
    (_round_time); de laatste is precies de periode."""
    ts = model_data.get("timesteps") or {}
    t_end = ts.get("period") or analysis.get("default_time_end", 1.0)
    inc = ts.get("increment")
    if not inc and model_data.get("analysis_type") == "D30" and \
            ts.get("stepsize"):
        # Dynamic Response (D30): Mecway schrijft elke n-de rekenstap
        # (stepsize x keepeverynthtimestep, bridge_from_liml).
        inc = ts["stepsize"] * ts.get("keep_every", 1)
    inc = inc or t_end
    start = ts.get("start") or 0.0
    times = []
    k = 1
    while True:
        t = _round_time(start + k * inc)
        if t > t_end * (1.0 + 1.0e-9):
            break
        times.append(t)
        k += 1
    if times and abs(times[-1] - t_end) <= 1.0e-9 * t_end:
        times[-1] = t_end
    else:
        times.append(t_end)
    return _merge_times(times, t_end)


def _damped_step_factor(xi):
    """
    Stabiele stap van centrale differenties met demping, als fractie van
    de ongedempte 2/w: dt <= (2/w) (sqrt(1 + xi^2) - xi) (Belytschko, Liu,
    Moran, "Nonlinear Finite Elements for Continua and Structures", par.
    6.4.3; ook de Abaqus/Explicit-handleiding, "stability limit"). Code-
    Aster neemt demping niet mee in de eigen CFL-controle (STOP_CFL): een
    balk met Rayleigh-beta 5,5e-4 s en stap 0,5 x de ongedempte schatting
    gaf <EXCEPTION> DVP_2 (Code-Aster 17.4).
    """
    xi = max(0.0, xi)
    return math.sqrt(1.0 + xi * xi) - xi


def _discrete_time_step(model_data):
    """
    Stabiele stap van de discrete elementen (bridge_mesh._build_discretes:
    knoopmassa's M_T_D_N/M_TR_D_N, elastic support K_T_D_N; veren
    spring_sections, dempers discrete_sections). Per knoop met een massa:
    w^2 = sum k (1/m_i + 1/m_j) + k_steun / m_i, demping eta = sum c (1/m_i
    + 1/m_j) (= 2 xi w); dt = (2/w) (sqrt(1 + xi^2) - xi), of 2/eta zonder
    stijfheid (_damped_step_factor). Een knoop aan het andere eind zonder
    knoopmassa telt als vast (1/m_j = 0): voor een massa aan een veer naar
    een vaste knoop exact (w^2 = k/m); voor een keten een bovengrens van w
    (Gershgorin). Veren/dempers tussen knopen zonder knoopmassa (bv. aan
    volume-elementen) tellen niet mee. NIET de exacte waarde. Returns dt of
    None.
    """
    mass = {}
    k_sup = {}
    for d in model_data.get("discretes", {}).values():
        cara = dict(d.get("cara", []))
        m = (cara.get("M_T_D_N") or cara.get("M_TR_D_N") or (0.0,))[0]
        k = cara.get("K_T_D_N") or cara.get("K_TR_D_N") or (0.0,)
        for n in d.get("nodes", []):
            if m:
                mass[n] = mass.get(n, 0.0) + m
            if max(k[:3]) > 0.0:
                k_sup[n] = k_sup.get(n, 0.0) + max(k[:3])
    if not mass:
        return None
    renames = model_data.get("group_renames", {})
    springs = model_data.get("spring_sections", {})
    dampers = dict((g, s["c"]) for g, s in
                   model_data.get("discrete_sections", {}).items()
                   if s.get("kind") == "damper")
    w2 = dict((n, k_sup.get(n, 0.0) / m) for n, m in mass.items())
    eta = dict((n, 0.0) for n in mass)
    for eid, shape, enodes, elset in model_data.get("mesh_elements", []):
        group = renames.get(elset, elset)
        if len(enodes) != 2 or (group not in springs and group not in dampers):
            continue
        inv = sum(1.0 / mass[n] for n in enodes if n in mass)
        for n in enodes:
            if n not in mass:
                continue
            if group in springs:
                w2[n] += springs[group]["spring_constant"] * inv
            else:
                eta[n] += dampers[group] * inv
    dt = None
    for n in mass:
        if w2[n] > 0.0:
            w = math.sqrt(w2[n])
            d = 2.0 / w * _damped_step_factor(eta[n] / (2.0 * w))
        elif eta[n] > 0.0:
            d = 2.0 / eta[n]
        else:
            continue
        dt = d if dt is None else min(dt, d)
    return dt


def _critical_time_step(model_data):
    """
    Schatting van de stabiele tijdstap voor DIFF_CENT: kleinste ribbe /
    drukgolfsnelheid c = sqrt(E (1-nu) / (rho (1+nu) (1-2nu))) per
    elset (= 2 / w_max van een staafelement). NIET de exacte CFL-waarde
    die Code-Aster berekent (STOP_CFL controleert die zelf).
    Rayleigh-demping (Mecway C = alpha M + beta K, op de elementen met
    materiaal): xi = alpha / (2 w) + beta w / 2 bij w = 2 / dt, en de stap
    maal _damped_step_factor(xi). Discrete elementen: _discrete_time_step;
    de kleinste van beide.
    """
    nodes = model_data.get("mesh_nodes", {})
    mats = model_data.get("materials", {})
    elsets = model_data.get("elsets", {})
    renames = model_data.get("group_renames", {})
    rayleigh = model_data.get("rayleigh") or {}
    alpha = rayleigh.get("alpha") or 0.0
    beta = rayleigh.get("beta") or 0.0
    dt = None
    for eid, shape, enodes, elset in model_data.get("mesh_elements", []):
        # mesh_elements heeft de Mecway-naam, elsets de hernoemde
        # (bridge_mesh); zonder omzetting viel een elset met een
        # spatie stil weg uit de schatting (crit-review).
        props = mats.get(elsets.get(renames.get(elset, elset)))
        if not props or not props.get("rho"):
            continue
        e, nu, rho = props["E"], props["NU"], props["rho"]
        c = math.sqrt(e * (1.0 - nu) / (rho * (1.0 + nu) * (1.0 - 2.0 * nu)))
        pts = [nodes[n] for n in enodes]
        lmin = min(math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
                   for k, a in enumerate(pts) for b in pts[k + 1:])
        if lmin > 0.0:
            d = lmin / c
            dt = d if dt is None else min(dt, d)
    if dt and (alpha or beta):
        w = 2.0 / dt
        xi = alpha / (2.0 * w) + beta * w / 2.0
        factor = _damped_step_factor(xi)
        vals = ("%.4g" % alpha, "%.4g" % beta, "%.4g" % w, "%.4g" % xi,
                "%.3g" % factor)
        if factor < 0.1:
            log(tr("WARNING: Rayleigh-demping (alpha {0} 1/s, beta {1} s) "
                   "geeft bij de hoogste eigenfrequentie (~{2} rad/s) een "
                   "dempingsverhouding {3}: de stabiele stap van het "
                   "expliciete schema wordt {4} x zo groot, dus veel meer "
                   "stappen. Overweeg dyna_impl_3d.",
                   "WARNING: Rayleigh damping (alpha {0} 1/s, beta {1} s) "
                   "gives a damping ratio of {3} at the highest natural "
                   "frequency (~{2} rad/s): the stable step of the explicit "
                   "scheme becomes {4} times as large, so many more steps. "
                   "Consider dyna_impl_3d.").format(*vals))
        else:
            log("INFO: Rayleigh-demping (alpha {0} 1/s, beta {1} s): "
                "dempingsverhouding {3} bij ~{2} rad/s, stabiele stap x {4} "
                "(centrale differenties met demping).".format(*vals))
        dt *= factor
    # Zonder elementen met materiaal kan Code-Aster zelf geen CFL-grens
    # bepalen: STOP_CFL='OUI' (default) stopt dan met <EXCEPTION>
    # DYNAMIQUE_4 "La condition de stabilite n'a pu etre calculee pour aucun
    # element" (Code-Aster 17.4, veer + demper + knoopmassa). Dan
    # STOP_CFL='NON' (catalogus dyna_non_line.py, b_explicit) met de
    # schatting hieronder.
    model_data["_explicit_no_cfl"] = dt is None
    d = _discrete_time_step(model_data)
    if d:
        log("INFO: Expliciet: geschatte stabiele stap van de discrete "
            "elementen (knoopmassa's, veren, dempers) {0} s.".format(d))
        dt = d if dt is None else min(dt, d)
    return dt


# ==========================================
# OPGELEGDE VERPLAATSING IN EXPLICIETE DYNAMICA
# ==========================================
# DIFF_CENT/TCHAMWA kennen alleen FORMULATION='ACCELERATION' (catalogus
# dyna_non_line.py v17.4, b_explicit); DDL_IMPO (en LIAISON_OBLIQUE,
# FACE_IMPO) leggen dan de versnelling op: een opgelegde u(t) = 0 -> 6 mm
# bewoog 5,5e-10 m (testrun; daarom zet _explicit_kinematics u(t) om naar
# een versnelling, verificatie DY-03b). Een verplaatsing nul blijft
# goed (versnelling nul, beginsnelheid nul).
_EXPLICIT_KINEMATIC_TYPES = ("displacement", "noderotation", "velocity",
                             "frictionless")

# PHI van TCHAMWA: de bridge zet hem niet, dus de catalogus-default
# (dyna_non_line.py v17.4, b_tchamwa: PHI defaut=1.05).
_TCHAMWA_PHI = 1.05


def _explicit_kinematic_values(model_data):
    """
    [(bc-index, sleutel, waarde)] van opgelegde verplaatsingen, rotaties en
    snelheden (als verplaatsingshistorie, bridge_bcs.VelocityBC) die niet
    overal nul zijn: waarde is een getal of [(t, u)].
    """
    out = []
    for idx, bc in enumerate(model_data.get("bcs", [])):
        if (bc["type"] not in _EXPLICIT_KINEMATIC_TYPES or bc.get("skip")
                or bc.get("oblique") is not None
                or bc.get("unil_zones") is not None
                or bc.get("pin_weights")):
            continue
        for k, v in bc["aster_dict"].items():
            if k in _BC_ATTRIBUTE_KEYS:
                continue
            if isinstance(v, list):
                if any(u != 0.0 for _t, u in v):
                    out.append((idx, k, v))
            elif isinstance(v, (int, float)) and not isinstance(v, bool) \
                    and v != 0.0:
                out.append((idx, k, v))
    return out


def _interp_history(hist, t):
    """Lineair tussen de punten, constant erbuiten (zoals DEFI_FONCTION
    met PROL_GAUCHE/PROL_DROITE='CONSTANT', _build_load_funcs_block)."""
    if not isinstance(hist, list):
        return hist
    pts = sorted(hist)
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, u0), (t1, u1) in zip(pts[:-1], pts[1:]):
        if t <= t1:
            return u1 if t1 <= t0 else u0 + (u1 - u0) * (t - t0) / (t1 - t0)
    return pts[-1][1]


def _explicit_steps(intervals):
    """[(begin, eind, stap)] per INTERVALLE van listinst (vanaf 0)."""
    segs = []
    prev = 0.0
    for t, n in intervals:
        segs.append((prev, t, (t - prev) / n))
        prev = t
    return segs


def _explicit_step_around(segs, t):
    """(stap ervoor, stap erna) rond rekentijd t; ervoor 0 op t = 0."""
    tol = 1.0e-9 * segs[-1][1]
    before = after = 0.0
    for a, b, h in segs:
        if a - tol <= t < b - tol and not after:
            after = h
        if a + tol < t <= b + tol:
            before = h
    return before, after or segs[-1][2]


def _explicit_accelerations(hist, segs, boundaries, schema):
    """
    Versnellingshistorie [(t, a)] die met het expliciete schema op de
    rekentijden precies de verplaatsing hist (getal of [(t, u)]) geeft.

    Doel: u op de knikpunten (begin 0; bij u(0) != 0 de eerste rekentijd;
    de knikken van hist, die rekentijden zijn, _build_dyna_listinst_block;
    de eindtijd), lineair ertussen. w_n = (u_n+1 - u_n) / h_n is dan per
    stuk constant. Beginsnelheid 0 (geen ETAT_INIT op deze knopen).
    - DIFF_CENT (Newmark beta = 0, gamma = 1/2): u_n+1 = u_n + h_n v_n +
      h_n^2/2 a_n, v_n+1 = v_n + h_n/2 (a_n + a_n+1), dus
      a_n = 2 (w_n - w_n-1) / (h_n-1 + h_n), met w_-1 = 0, h_-1 = 0: alleen
      op de knikken een versnelling, elders 0. Nagelopen met een testrun
      (Code-Aster 17.4, trekstaaf 0 -> 6 mm in 1 ms: u = 6,000e-3 m op
      t = 1 ms, v = 6 m/s op alle uitvoertijden).
    - TCHAMWA: u_n+1 = u_n + h_n v_n + PHI h_n^2 a_n, v_n+1 = v_n + h_n a_n
      (afgeleid uit een testrun met Code-Aster 17.4: de DIFF_CENT-stoot gaf
      v = 2 * 6 m/s en u_1 = PHI h^2 a_0); a_n = (w_n - v_n) / (PHI h_n),
      na een knik een snel uitdovende reeks (factor 1 - 1/PHI per stap).
    """
    t_end = boundaries[-1]
    tol = 1.0e-9 * t_end
    h0 = segs[0][2]
    schema = schema or "DIFF_CENT"
    u0 = _interp_history(hist, 0.0)
    pts = [(0.0, 0.0)]
    start = 0.0
    if u0 != 0.0:
        # Begint de verplaatsing niet op nul: zoals impliciet in de eerste
        # stap opleggen (beginverplaatsing is 0, geen ETAT_INIT DEPL).
        start = h0
        pts.append((h0, _interp_history(hist, h0)))
    knots = set()
    if isinstance(hist, list):
        for t, _u in hist:
            if start + tol < t < t_end - tol:
                # De knik ligt op een INTERVALLE-grens (bijna-dubbele tijden
                # zijn in _merge_times samengevoegd): die grens nemen.
                knots.add(min(boundaries, key=lambda b: abs(b - t)))
    for t in sorted(knots):
        if t > pts[-1][0] + tol:
            pts.append((t, _interp_history(hist, t)))
    if t_end > pts[-1][0] + tol:
        pts.append((t_end, _interp_history(hist, t_end)))
    # Gemiddelde snelheid per stuk; knikken = begin van elk stuk
    kinks = []
    w_prev = 0.0
    for (ta, ua), (tb, ub) in zip(pts[:-1], pts[1:]):
        w = (ub - ua) / (tb - ta)
        kinks.append((ta, w_prev, w))
        w_prev = w
    acc = {}
    if schema == "TCHAMWA":
        t_cur, v_cur = 0.0, 0.0
        for j, (ta, w_old, w) in enumerate(kinks):
            # Snelheid vlak voor de knik: de vorige reeks is uitgedoofd
            # (v = w_old), of liep tot deze knik door (v_cur).
            v = v_cur if abs(t_cur - ta) <= tol else w_old
            t = ta
            t_next = kinks[j + 1][0] if j + 1 < len(kinks) else t_end
            for _k in range(60):
                h = _explicit_step_around(segs, t)[1]
                a = (w - v) / (_TCHAMWA_PHI * h)
                if abs(a) * h <= 1.0e-14 * max(abs(w), abs(w_old), 1.0e-30):
                    break
                acc[t] = a
                v += h * a
                t = t + h
                if t >= t_next - tol:
                    break
            t_cur, v_cur = t, v
    else:
        for ta, w_old, w in kinks:
            if w == w_old:
                continue
            before, after = _explicit_step_around(segs, ta)
            acc[ta] = 2.0 * (w - w_old) / (before + after)
    # Functiepunten: de versnelling op de knikken, nul op de rekentijden
    # ernaast (DDL_IMPO neemt de functie alleen op de rekentijden).
    eps = 1.0e-6 * min(h for _a, _b, h in segs)
    out = dict(acc)
    for t in list(acc):
        before, after = _explicit_step_around(segs, t)
        for n in ((t - before) if before else None, t + after):
            if n is None or n > t_end + tol:
                continue
            if not any(abs(n - k) <= eps for k in out):
                out[n] = 0.0
    if not out:
        return [(0.0, 0.0), (t_end, 0.0)]
    return [(_round_time(t) if t else 0.0, a) for t, a in sorted(out.items())]


def _explicit_kinematics(model_data, intervals, schema):
    """
    Opgelegde verplaatsingen (_explicit_kinematic_values) omzetten naar de
    versnelling die DIFF_CENT/TCHAMWA oplegt (_explicit_accelerations).
    Vervangt de waarden in bc["aster_dict"] door een tijdshistorie; die
    wordt een DEFI_FONCTION in AFFE_CHAR_MECA_F (_build_charges).
    """
    kin = _explicit_kinematic_values(model_data)
    if not kin:
        return
    segs = _explicit_steps(intervals)
    boundaries = [t for t, _n in intervals]
    bcs = model_data["bcs"]
    for idx, key, value in kin:
        bc = bcs[idx]
        if not isinstance(value, list):
            log(tr("WARNING: Opgelegde {0} {1} = {2} op '{3}' zonder "
                   "tijdshistorie in expliciete dynamica: de waarde wordt in "
                   "de eerste rekenstap ({4} s) bereikt (een stoot, zoals "
                   "impliciet). Geef in Mecway een tijdshistorie voor een "
                   "geleidelijke beweging.",
                   "WARNING: Prescribed {0} {1} = {2} on '{3}' without a "
                   "time history in explicit dynamics: the value is reached "
                   "in the first time step ({4} s) (a shock, as in implicit). "
                   "Give a time history in Mecway for a gradual motion.")
                .format(bc["type"], key, value, bc["selection"],
                        "%.4g" % segs[0][2]))
        bc["aster_dict"][key] = _explicit_accelerations(
            value, segs, boundaries, schema)
        log("INFO: Expliciet: opgelegde {0} {1} op '{2}' omgezet naar een "
            "versnelling ({3} legt DDL_IMPO op de versnelling op; "
            "stoten op de knikken van u(t)).".format(
                bc["type"], key, bc["selection"], schema))
    if model_data.get("initial_velocities"):
        log(tr("WARNING: Beginsnelheid en opgelegde verplaatsing in "
               "expliciete dynamica: op knopen met beide klopt de "
               "verplaatsing niet (de omzetting naar een versnelling gaat "
               "uit van beginsnelheid nul). Geef die knopen geen "
               "beginsnelheid.",
               "WARNING: Initial velocity and prescribed displacement in "
               "explicit dynamics: on nodes with both, the displacement is "
               "wrong (the conversion to an acceleration assumes zero "
               "initial velocity). Give those nodes no initial velocity."))


def _build_dyna_listinst_block(model_data, load_funcs, analysis):
    """
    Tijdsdiscretisatie voor DYNA_NON_LINE.

    Impliciet: substeps_per_output stappen per uitvoerinterval, met
    automatische halvering bij divergentie (DEFI_LIST_INST ECHEC, U4.34.03).
    Expliciet (DIFF_CENT): per uitvoerinterval een gelijke stap van ten
    hoogste explicit_dt_factor * geschatte kritieke tijdstap
    (_critical_time_step). Zo is elke uitvoertijd een rekenstap: met een
    vaste stap over de hele periode vielen de uitvoertijden tussen de
    stappen en archiveerde ARCHIVAGE LIST_INST alleen t=0 en t_end
    (testrun, Code-Aster 17.4).
    Returns (blok, t_end).
    """
    out = _output_times(model_data, analysis)
    t_end = out[-1]
    lines = ["outlist = DEFI_LIST_REEL(\n    VALE=({0}),\n)\n".format(
        ", ".join("{0!r}".format(t) for t in out))]
    if analysis.get("schema", "HHT") in ("DIFF_CENT", "TCHAMWA"):
        dt_crit = _critical_time_step(model_data)
        if not dt_crit:
            raise ValueError(tr("geen kritieke tijdstap: materiaal zonder "
                                "dichtheid?",
                                "no critical time step: material without "
                                "density?"))
        dt = analysis.get("explicit_dt_factor", 0.5) * dt_crit
        # De knikken van opgelegde verplaatsingen worden rekentijden
        # (INTERVALLE-grenzen): daar komt de versnellingsstoot
        # (_explicit_kinematics).
        kin = _explicit_kinematic_values(model_data)
        bounds = _merge_times(out + [t for _i, _k, v in kin
                                     if isinstance(v, list)
                                     for t, _u in v if 0.0 < t < t_end],
                              t_end, prefer=out)
        intervals = []
        prev = 0.0
        for t in bounds:
            # -1e-9: een interval dat na _round_time net boven een geheel
            # aantal stappen uitkomt (5,0000000000027 dt) gaf een stap extra
            # en een ongelijke stapgrootte (verificatie DY-03)
            intervals.append((t, max(1, int(math.ceil(
                (t - prev) / dt - 1e-9)))))
            prev = t
        nsteps = sum(n for _, n in intervals)
        log("INFO: Expliciet: geschatte kritieke tijdstap {0} s, stap <= {1} "
            "s, {2} stappen.".format(dt_crit, dt, nsteps))
        if nsteps > 2000000:
            log(tr("WARNING: {0} expliciete stappen; Code-Aster kent geen "
                   "mass scaling (zoals /DT/NODA/CST in OpenRadioss). "
                   "Overweeg de impliciete analyse.",
                   "WARNING: {0} explicit steps; Code-Aster has no mass "
                   "scaling (like /DT/NODA/CST in OpenRadioss). Consider "
                   "the implicit analysis.").format(nsteps))
        lines.append(
            "listinst = DEFI_LIST_REEL(\n    DEBUT=0.0,\n    INTERVALLE=(\n"
            "{0}    ),\n)\n".format("".join(
                "        _F(JUSQU_A={0!r}, NOMBRE={1}),\n".format(t, n)
                for t, n in intervals)))
        _explicit_kinematics(model_data, intervals, analysis.get("schema"))
    else:
        n = analysis.get("substeps_per_output", 1)
        times = _merge_times([0.0] + out + [t for _, h in load_funcs
                                            for t, _ in h if 0.0 < t < t_end],
                             t_end, prefer=out)
        lines.append(
            "times = DEFI_LIST_REEL(\n    DEBUT=0.0,\n    INTERVALLE=(\n"
            "{0}    ),\n)\n".format("".join(
                "        _F(JUSQU_A={0!r}, NOMBRE={1}),\n".format(t, n)
                for t in times[1:])))
        lines.append(
            "listinst = DEFI_LIST_INST(\n"
            "    DEFI_LIST=_F(LIST_INST=times),\n"
            "    ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE',\n"
            "             SUBD_METHODE='MANUEL', SUBD_PAS=4,\n"
            "             SUBD_NIVEAU=6),\n)\n")
    return "\n".join(lines), t_end


# Grenzen van failure_stiffness_factor, gelijk aan het startscherm
# (bridge_gui ANALYSIS_SPECS, "float_range").
# Ondergrens 1e-7: met 1e-9 stopte de statische trekstaaf na het bezwijken
# met MECANONLINE9_4 (matrix singulier; testrun Code-Aster 17.4).
_FAILURE_FACTOR_RANGE = (1.0e-7, 0.1)


def _failure_stiffness_factor(analysis):
    """
    failure_stiffness_factor, begrensd op _FAILURE_FACTOR_RANGE. Via
    #ASTER-OPTIE kon elke waarde binnenkomen; 0 gaf een ZeroDivisionError
    (bridge_failure.weak_materials deelt de TRACTION-rek door de factor).
    """
    lo, hi = _FAILURE_FACTOR_RANGE
    default = 1.0e-6
    raw = analysis.get("failure_stiffness_factor", default)
    try:
        factor = float(raw)
    except (TypeError, ValueError):
        factor = None
    if factor is None or factor != factor:   # geen getal of NaN
        used = default
    else:
        used = min(max(factor, lo), hi)
    if factor is None or used != factor:
        log(tr("WARNING: failure_stiffness_factor = {0} ligt niet tussen "
               "{1} en {2} (zoals op het startscherm); {3} gebruikt.",
               "WARNING: failure_stiffness_factor = {0} is not between {1} "
               "and {2} (as on the start screen); {3} used.").format(
                   raw, lo, hi, used))
    return used


def _warn_plastic_hex8(model_data, plan):
    """
    WARNING voor plastische hex8-elementen die lineair blijven (elem_hex8
    '3D', of LINE_QUAD niet toegepast). Volledig geintegreerde hex8 'lockt'
    bij plastisch vloeien (de plastische rek is volumebehoudend): in een
    testrun (trekstaaf met kerf, Code-Aster 17.4) bezweek het eerste element
    met '3D' pas bij t=0,6, met LINE_QUAD bij t=0,2. Of 3D_SI dit ook
    oplost is NIET geverifieerd; het advies is LINE_QUAD.
    """
    if model_data.get("line_quad") == "TOUT":
        return
    renames = model_data.get("group_renames", {})
    mods = model_data.get("elset_modelisations", {})
    hex_elsets = set(renames.get(e[3], e[3])
                     for e in model_data.get("mesh_elements", [])
                     if e[1] == "hex8")
    names = []
    for elset, mat_name in model_data.get("elsets", {}).items():
        if elset not in hex_elsets or mods.get(elset) != "3D":
            continue
        if _relation_for(model_data, mat_name) != "ELAS":
            names.append(elset)
    if not names:
        return
    failing = set(p["elset"] for p in plan) & set(names)
    log(tr("WARNING: Plastische hex8-elementen (elset {0}) blijven "
           "lineair: lineaire hex8 'lockt' bij plastisch vloeien "
           "(volumebehoudend), de plastische rek groeit te langzaam{1}. "
           "Kies op de pagina Elementen 'LINE_QUAD' of gebruik "
           "kwadratische elementen in Mecway.",
           "WARNING: Plastic hex8 elements (elset {0}) stay linear: "
           "linear hex8 locks in plastic flow (volume-preserving), "
           "the plastic strain grows too slowly{1}. Choose 'LINE_QUAD' on "
           "the Elements page or use quadratic elements in Mecway.").format(
               ", ".join(bridge_failure.mecway_name(model_data, n)
                         for n in names),
               tr(" en elementen bezwijken te laat (testrun: t=0,6 in plaats "
                  "van t=0,2 met LINE_QUAD)",
                  " and elements fail too late (test run: t=0.6 instead of "
                  "t=0.2 with LINE_QUAD)") if failing else ""))


# ==========================================
# NIET-LINEAIRE KNIK: CRIT_STAB EN KNIKVORM ALS IMPERFECTIE
# (instellingen crit_stab, imperfection_*; docs/Modaal_en_knik.md par. 5)
# ==========================================
def _crit_stab_args():
    """CRIT_STAB in STAT_NON_LINE (catalogus stat_non_line.py v17.4): de
    kleinste |CHAR_CRIT| (OPTION 'PLUS_PETITE', NMAX_CHAR_CRIT 1) na elke
    stap. Geen ECHEC INSTABILITE in DEFI_LIST_INST: de berekening gaat na
    een instabiliteit door (standaard, U4.51.03 par. 3.18.9), zodat ook het
    gedrag erna (met een imperfectie) zichtbaar blijft."""
    return "    CRIT_STAB=_F(OPTION='PLUS_PETITE', NMAX_CHAR_CRIT=1),\n"


def _model_size(model_data):
    """Grootste afmeting [m] van de omhullende doos van de Mecway-knopen."""
    nodes = list(model_data.get("mesh_nodes", {}).values())
    if not nodes:
        return 0.0
    return max(max(p[k] for p in nodes) - min(p[k] for p in nodes)
               for k in range(3))


def _imperfection_plan(model_data, analysis):
    """
    Knikvorm als imperfectie (instellingen imperfection_amplitude, _mode,
    _unit; ook #ASTER-OPTIE). None = uit; False = fout (ERROR gelogd);
    anders {"mode": k, "amplitude": e0 in m}.
    """
    try:
        amp = float(analysis.get("imperfection_amplitude", 0.0) or 0.0)
        mode = int(analysis.get("imperfection_mode", 1))
    except (TypeError, ValueError):
        amp, mode = None, 0
    if amp == 0.0:
        return None
    if amp is None or mode < 1:
        log(tr("ERROR: Imperfectie: ongeldige amplitude of modenummer "
               "(imperfection_amplitude, imperfection_mode >= 1).",
               "ERROR: Imperfection: invalid amplitude or mode number "
               "(imperfection_amplitude, imperfection_mode >= 1)."))
        return False
    unit = "{0}".format(analysis.get("imperfection_unit", "m"))
    if unit == "L":
        size = _model_size(model_data)
        log("INFO: Imperfectie: amplitude {0} x L, L = {1:.6g} m (grootste "
            "afmeting van het model) = {2:.6g} m.".format(amp, size,
                                                          amp * size))
        amp = amp * size
    elif unit != "m":
        log(tr("ERROR: Imperfectie: eenheid '{0}' onbekend (imperfection_"
               "unit: m of L).",
               "ERROR: Imperfection: unit '{0}' unknown (imperfection_"
               "unit: m or L).").format(unit))
        return False
    found = _nonlinear_parts(model_data)
    if found:
        # De knikvorm komt uit een lineaire knikberekening (MECA_STATIQUE
        # + CALC_MODES); contact en dergelijke kan die niet.
        log(tr("ERROR: Imperfectie (knikvorm) niet mogelijk met {0}: de "
               "knikvorm komt uit een lineaire knikberekening. Zet de "
               "amplitude op 0, of onderdruk deze onderdelen in een "
               "configuratie.",
               "ERROR: Imperfection (buckling mode) not possible with {0}: "
               "the mode comes from a linear buckling analysis. Set the "
               "amplitude to 0, or suppress these parts in a "
               "configuration.").format(", ".join(found)))
        return False
    # De uitbuiging groeit alleen waar de elementen grote verplaatsingen
    # rekenen (evenwicht op de vervormde vorm); balken en DKT/DST blijven
    # geometrisch lineair (_deformation_for).
    if analysis.get("deformation", "PETIT") not in _LARGE_DEFORMATIONS:
        log(tr("WARNING: Imperfectie met kleine verplaatsingen (DEFORMATION="
               "{0}): het evenwicht staat op de onvervormde vorm, dus de "
               "uitbuiging groeit niet met de last (geen tweede-orde-"
               "effect). Kies een DEFORMATION voor grote verplaatsingen "
               "(standaard GROT_GDEP).",
               "WARNING: Imperfection with small displacements (DEFORMATION="
               "{0}): equilibrium is on the undeformed shape, so the "
               "deflection does not grow with the load (no second-order "
               "effect). Choose a DEFORMATION for large displacements "
               "(default GROT_GDEP).").format(analysis.get("deformation")))
    small = sorted(e for e, m in model_data.get(
        "elset_modelisations", {}).items()
        if m in ("DKT", "DST") or str(m).startswith("POU_D"))
    if small:
        log(tr("WARNING: Imperfectie: balken en DKT/DST-schalen ({0}) "
               "rekenen geometrisch lineair; daar versterkt de imperfectie "
               "niet. Gebruik volume-elementen of elem_shell = COQUE_3D.",
               "WARNING: Imperfection: beams and DKT/DST shells ({0}) are "
               "geometrically linear; there the imperfection is not "
               "amplified. Use solid elements or elem_shell = "
               "COQUE_3D.").format(", ".join(
                   bridge_failure.mecway_name(model_data, e) for e in small)))
    return {"mode": mode, "amplitude": amp}


def _imperfection_blocks(model_data, analysis, plan, charges, excit_clause,
                         cara_ref, t_end):
    """
    (blok vóór STAT_NON_LINE, blok vóór de resultaatexport) voor de
    knikvorm als imperfectie (U2.08.04 par. 2.2: de constructie licht
    voorvervormen volgens de knikvorm):
      1. lineaire knik onder de lasten op t_end, zoals buckling_3d
         (_build_modal; testcase ssll105a): MECA_STATIQUE (INST=t_end,
         zodat FONC_MULT/AFFE_CHAR_MECA_F de eindwaarde hebben), SIEF_ELGA,
         ASSEMBLAGE RIGI_MECA + RIGI_GEOM, CALC_MODES MODE_FLAMB met
         NORM_MODE 'TRAN' (grootste verplaatsingscomponent = 1);
      2. MODI_MAILLAGE DEFORME 'TRAN' met amplitude x mode k (CREA_CHAMP
         COMB; zoals testcase ssnl502d, voordeformatie volgens de
         knikvorm), daarna AFFE_CARA_ELEM opnieuw (balk-/schaalassen op de
         vervormde geometrie);
      3. na CALC_CHAMP het mesh terug (DEFORME met -amplitude x mode, zoals
         testcase hsna105a), zodat aster_results_export de knopen tegen de
         .liml kan controleren (_check_node_order). De verplaatsingen
         blijven die t.o.v. de imperfecte vorm.
    Een meebewegende last (TYPE_CHARGE='SUIV') is in MECA_STATIQUE een
    vaste last (catalogus meca_statique.py: alleen 'FIXE_CSTE').
    """
    k = plan["mode"]
    amp = plan["amplitude"]
    names_bc = ["load_{0}".format(i + 1) for i, c in enumerate(charges)
                if not _is_load_charge(c)]
    extra = model_data.get("aster_custom", {}).get("excit", [])
    names = names_bc + [n for n in extra if n not in names_bc]
    charge_ref = ("    CHARGE=({0},),\n".format(", ".join(names))
                  if names else "")
    excit = excit_clause.replace(", TYPE_CHARGE='SUIV'", "")
    nprec = int(analysis.get("solver_nprec", 8))
    pre = (
        "# --- Imperfectie: knikvorm {k} van de lineaire knik onder de\n"
        "# lasten op t = {t_end!r} (bridge_to_aster._imperfection_blocks) ---\n"
        "imp_stat = MECA_STATIQUE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}{excit}\n"
        "    INST={t_end!r},\n"
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={nprec}),\n"
        ")\n"
        "imp_sig = CREA_CHAMP(OPERATION='EXTR', TYPE_CHAM='ELGA_SIEF_R',\n"
        "                     RESULTAT=imp_stat, NUME_ORDRE=1, "
        "NOM_CHAM='SIEF_ELGA')\n"
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}{charge}"
        "    NUME_DDL=CO('imp_nume'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('imp_rigi'), OPTION='RIGI_MECA'),\n"
        "        _F(MATRICE=CO('imp_geo'), OPTION='RIGI_GEOM', "
        "SIEF_ELGA=imp_sig),\n"
        "    ),\n"
        ")\n"
        "imp_modes = CALC_MODES(\n"
        "    TYPE_RESU='MODE_FLAMB',\n"
        "    MATR_RIGI=imp_rigi,\n"
        "    MATR_RIGI_GEOM=imp_geo,\n"
        "    OPTION='PLUS_PETITE',\n"
        "    CALC_CHAR_CRIT=_F(NMAX_CHAR_CRIT={k}),\n"
        "    NORM_MODE=_F(NORME='TRAN'),\n"
        "    VERI_MODE=_F(STOP_ERREUR='NON'),\n"
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={nprec}),\n"
        ")\n"
        "imp_phi = CREA_CHAMP(OPERATION='EXTR', TYPE_CHAM='NOEU_DEPL_R',\n"
        "                     RESULTAT=imp_modes, NOM_CHAM='DEPL', "
        "NUME_ORDRE={k})\n"
        "# Kniklastfactoren (CHAR_CRIT staat niet in getAccessParameters;\n"
        "# RECU_TABLE NOM_PARA zoals aster_results_export._table_values)\n"
        "imp_tab = RECU_TABLE(CO=imp_modes, NOM_PARA=('CHAR_CRIT',))"
        ".EXTR_TABLE().values()\n"
        "for imp_i, imp_nr in enumerate(imp_tab['NUME_ORDRE']):\n"
        "    print('BRIDGE_IMPERFECTIE_MODE %d %r' % (imp_nr, "
        "imp_tab['CHAR_CRIT'][imp_i]))\n"
        "print('BRIDGE_IMPERFECTIE %d %r' % ({k}, {amp!r}))\n"
        "imp_def = CREA_CHAMP(OPERATION='COMB', TYPE_CHAM='NOEU_DEPL_R',\n"
        "                     COMB=_F(CHAM_GD=imp_phi, COEF_R={amp!r}))\n"
        "mesh = MODI_MAILLAGE(reuse=mesh, MAILLAGE=mesh,\n"
        "                     DEFORME=_F(OPTION='TRAN', DEPL=imp_def))\n"
    ).format(k=k, t_end=float(t_end), cara=cara_ref, excit=excit,
             nprec=nprec, charge=charge_ref, amp=float(amp))
    restore = (
        "# --- Imperfectie: mesh terug naar de Mecway-geometrie voor de\n"
        "# export (verplaatsingen blijven t.o.v. de imperfecte vorm) ---\n"
        "imp_terug = CREA_CHAMP(OPERATION='COMB', TYPE_CHAM='NOEU_DEPL_R',\n"
        "                       COMB=_F(CHAM_GD=imp_phi, COEF_R={0!r}))\n"
        "mesh = MODI_MAILLAGE(reuse=mesh, MAILLAGE=mesh,\n"
        "                     DEFORME=_F(OPTION='TRAN', DEPL=imp_terug))\n"
    ).format(-float(amp))
    log("INFO: Imperfectie: knikvorm {0} van de lineaire knik onder de "
        "lasten op t = {1:g}, amplitude {2:.6g} m (grootste "
        "verplaatsingscomponent).".format(k, float(t_end), float(amp)))
    return pre, restore


_LARGE_RE = re.compile(r"DEFORMATION='(GROT_GDEP|GREEN_LAGRANGE|GDEF_LOG|"
                       r"SIMO_MIEHE)'")


def _crit_stab_kind(comportement_block):
    """
    Wat CRIT_STAB uitrekent (U4.51.03 par. 3.18, U2.08.04 par. 2.1):
      'factor': kleine verplaatsingen (PETIT, PETIT_REAC; balken blijven
        altijd PETIT): det(K_T + lambda K_g) = 0 met K_g uit de spanning van
        de stap; lambda = kritische lastfactor van de huidige last
        (gemeten: lambda(t) P(t) = Pcr constant en gelijk aan buckling_3d;
        verificatie NK-01, NK-02b; PETIT_REAC gaf dezelfde factoren);
      'eigen': grote verplaatsingen: K_T bevat K_g al, Code-Aster lost
        det(K_T + lambda I) = 0 op (gezien: "Nombre de produits B*X = 0"
        in de .mess, tegen ~35 bij 'factor'). lambda = kleinste eigenwaarde
        van K_T met omgekeerd teken: < 0 stabiel, 0 = knik of grenspunt
        (NK-02a, NK-04). Zodra een elset groot rekent, geldt dit voor het
        hele model (gemeten: hex20 GREEN_LAGRANGE + balk PETIT, in beide
        volgorden); GDEF_LOG ook (NK-04); SIMO_MIEHE NIET geverifieerd
        (aangenomen zoals GDEF_LOG).
    """
    return "eigen" if _LARGE_RE.search(comportement_block) else "factor"


def _crit_stab_report(kind):
    """Na de solve: de tabel ANALYSE_MODALE (CRIT_STAB; kolommen o.a. INST,
    CHAR_CRIT, TYPE_MODE 'MODE_FLAMB', gezien met 17.4) als
    BRIDGE_CRIT_STAB-regels in de .mess
    (bridge_results_liml.read_crit_stab)."""
    return (
        "# Stabiliteitscriterium per stap (CRIT_STAB) naar de .mess\n"
        "print('BRIDGE_CRIT_STAB_SOORT {0}')\n"
        "try:\n"
        "    _cs = RECU_TABLE(CO=res, NOM_TABLE='ANALYSE_MODALE')"
        ".EXTR_TABLE().values()\n"
        "    for _k in range(len(_cs['INST'])):\n"
        "        if str(_cs['TYPE_MODE'][_k]).strip() == 'MODE_FLAMB':\n"
        "            print('BRIDGE_CRIT_STAB %r %r' % (float(_cs['INST'][_k]),\n"
        "                  float(_cs['CHAR_CRIT'][_k])))\n"
        "except Exception as _cs_err:\n"
        "    print('BRIDGE_CRIT_STAB_GEEN', _cs_err)\n").format(kind)


# ==========================================
# BUILDER VOOR NIET-LINEAIR-STATISCHE ANALYSE  (STAT_NON_LINE)
# ==========================================
def _build_nonlin_static(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Genereer study.comm en study.export voor een STAT_NON_LINE- of
    DYNA_NON_LINE-analyse.

    Ondersteunt:
      - Plastische materialen (Mecway <plastic>): VMIS_ISOT_TRAC,
        VMIS_ISOT_LINE of VMIS_CINE_LINE (_relation_for); bezwijken van
        elementen via bridge_failure.
      - Tijdsafhankelijke krachten via DEFI_FONCTION en AFFE_CHAR_MECA_F.
      - Gemengde modellen (1D / 2D / 3D / veren) zoals MECA_STATIQUE.
      - Constante BCs (constraints, gravity, pressure, couplings) via
        AFFE_CHAR_MECA.

    Tijdsdiscretisatie:
      - statisch: Mecway's stappen (<timesteps stepsize>) plus de knikken
        van de lasttabellen, zonder stapgrootte substeps_per_interval
        stappen per segment tussen de lasttijden; in DEFI_LIST_INST met
        automatisch knippen (_build_listinst_block);
      - dynamisch: _build_dyna_listinst_block (uitvoertijden van Mecway's
        <timesteps>).

    Resultaten:
      - route 'liml' (standaard): aster_results_export schrijft alle
        gearchiveerde tijdstippen (statisch: elke rekenstap; dynamisch: de
        uitvoertijden);
      - route 'tabel': statisch alleen het laatst bereikte tijdstip
        (INST=t_res), dynamisch alle gearchiveerde (TOUT_ORDRE).

    DEFORMATION is een keuze per analyse (CONFIG "deformation"); per elset
    vertaald door _deformation_for.
    """
    command = analysis.get("solver_command", "STAT_NON_LINE")
    dynamic = command == "DYNA_NON_LINE"
    log("--- Generating Aster Files ({0}) ---".format(command))
    comm_path = os.path.join(work_dir, run_name(".comm"))

    # --------------------------------------------------
    # BLOK A: DEFI_GROUP (identiek aan MECA_STATIQUE)
    # --------------------------------------------------
    defigroup_block = _build_defigroup_block(model_data)

    # --------------------------------------------------
    # BLOK B + C: AFFE_MODELE + AFFE_CARA_ELEM (gedeeld)
    # --------------------------------------------------
    model_block     = _build_model_block(model_data)
    cara_elem_block = _build_cara_elem_block(model_data)

    cara_elem_ref = "    CARA_ELEM=cara,\n" if _has_cara(model_data) else ""

    # --------------------------------------------------
    # BLOK D-pre: DEFI_FONCTION voor plastische hardingscurves
    # Moet VOOR DEFI_MATERIAU staan zodat TRACTION=_F(SIGM=traction_func)
    # geldig is.
    # --------------------------------------------------
    try:
        plastic_curves_block, plastic_func_map = _build_plastic_curves_block(
            model_data, analysis)
    except ValueError as e:
        log(tr("ERROR: Hardingscurve ongeldig voor Code-Aster TRACTION: "
               "{0}",
               "ERROR: Hardening curve invalid for Code-Aster TRACTION: "
               "{0}").format(str(e)))
        return None
    with_plastic = bool(plastic_func_map) or any(
        p.get("plastic_bilinear") for p in model_data["materials"].values())

    # --------------------------------------------------
    # BLOK D: DEFI_MATERIAU per materiaal met optionele TRACTION
    # --------------------------------------------------
    materials_block = _build_materials_block(model_data, analysis,
                                             plastic_func_map)


    # --------------------------------------------------
    # BLOK F-pre: DEFI_FONCTION voor tijdsafhankelijke krachten
    # --------------------------------------------------
    load_funcs       = _collect_load_funcs(model_data)

    # --------------------------------------------------
    # BLOK F-pre2: DEFI_LIST_REEL
    # --------------------------------------------------
    if dynamic:
        try:
            listinst_block, t_end = _build_dyna_listinst_block(
                model_data, load_funcs, analysis)
        except ValueError as e:
            log(tr("ERROR: Tijdsdiscretisatie DYNA_NON_LINE: {0}",
                   "ERROR: Time discretisation DYNA_NON_LINE: {0}").format(e))
            return None
        # Expliciet: opgelegde verplaatsingen zijn nu versnellingshistories
        # (_explicit_kinematics); opnieuw verzamelen.
        load_funcs = _collect_load_funcs(model_data)
    else:
        listinst_block, t_end = _build_listinst_block(load_funcs, analysis,
                                                      model_data)
    load_funcs_block = _build_load_funcs_block(load_funcs)
    log("INFO: {0} tijdspad eindigt op t_end={1}".format(command, t_end))

    # --------------------------------------------------
    # BLOK E: AFFE_MATERIAU (als MECA_STATIQUE; statisch loopt een
    # temperatuurveld op van 0 tot t_end, _build_temperature_field)
    # --------------------------------------------------
    fieldmat_block = _build_fieldmat_block(
        model_data, None if dynamic else t_end)

    # --------------------------------------------------
    # BLOK F: AFFE_CHAR_MECA (constanten) + AFFE_CHAR_MECA_F (tijdsafh.)
    #
    # const_excit: alle constante BCs (DDL_IMPO, PRES_REP, PESANTEUR,
    #              LIAISON_*, constante krachten).
    # time_excit:  BC-componenten met een tijdshistorie (krachten,
    #              opgelegde verplaatsingen/rotaties) als DEFI_FONCTION.
    # --------------------------------------------------
    model_data["_follower_groups"] = _follower_pressure_groups(
        model_data, analysis)
    model_data["_follower_rotation"] = _follower_rotation(
        model_data, analysis, command)
    charges = _build_charges(model_data, _load_func_names(model_data))
    loads_const_block, excit_clause = _render_charges(charges, model_data)
    # Knikvorm als imperfectie (alleen niet-lineair statisch)
    imperfection = None
    if not dynamic:
        imperfection = _imperfection_plan(model_data, analysis)
        if imperfection is False:
            return None
    if not excit_clause and not (dynamic and
                                 model_data.get("initial_velocities")):
        # Zonder last (en zonder beginsnelheid) niets te rekenen; zie
        # _build_lin_static.
        log(tr("ERROR: Geen randvoorwaarden of belastingen in het model (of "
               "alle overgeslagen, zie de meldingen hierboven). Voeg in "
               "Mecway voorwaarden en belastingen toe.",
               "ERROR: No constraints or loads in the model (or all "
               "skipped, see the messages above). Add constraints and "
               "loads in Mecway."))
        return None

    # --------------------------------------------------
    # BLOK G: COMPORTEMENT (relatie per elset)
    # --------------------------------------------------
    comportement_block = _build_comportement_block(model_data, analysis)
    _warn_large_rotations(model_data, analysis)

    # --------------------------------------------------
    # BLOK H: CALC_CHAMP, POST_RELEVE_T, IMPR_TABLE
    # Plastic strain alleen toevoegen als minstens 1 materiaal een
    # plastische curve heeft.
    # --------------------------------------------------
    # Tabellen (route 'tabel'): dynamisch alle gearchiveerde tijdstippen
    # (uitvoertijden); statisch het laatst bereikte tijdstip (t_res, na de
    # solve; bij niet-convergentie eerder dan t_end). Route 'liml': alle
    # gearchiveerde tijdstippen (aster_results_export).
    result_selector  = ("TOUT_ORDRE='OUI'" if dynamic else "INST=t_res")
    # Vermoeiing (#ASTER-WOHLER, bridge_fatigue): de tijdstappen van de run
    # zijn het signaal per knoop
    fatigue = bridge_fatigue.fatigue_block(model_data, analysis, work_dir)
    if fatigue is None:
        return None
    calc_champ_block = (_build_calc_champ_block(
        model_data, with_plastic=with_plastic) +
        _custom_code(model_data, 'post') + fatigue[0])
    postreleve_block = _build_postreleve_block(
        model_data, result_selector=result_selector,
        with_plastic=with_plastic, with_velocity=dynamic)
    impr_table_block = _build_impr_table_block(
        model_data, with_plastic=with_plastic, with_velocity=dynamic)
    # Statisch double (zoals Mecway's eigen statische resultaten), dynamisch
    # single (zoals Mecway's OpenRadioss-resultaten).
    postreleve_block, impr_table_block = _results_route(
        work_dir, model_data, postreleve_block, impr_table_block,
        "single" if dynamic else "double", extra=fatigue[1])

    # --------------------------------------------------
    # STAT_NON_LINE-aanroep: volledig hier opgebouwd en als
    # {statnonline_block} in de template ingevuld.
    #
    # NEWTON / CONVERGENCE / SOLVEUR waarden uit CONFIG_BRIDGE["analyses"][...].
    # --------------------------------------------------
    reac_iter      = analysis.get("newton_reac_iter",      1)
    contact_block, contact_ref = _build_contact_block(model_data, analysis)
    extra = ""
    if dynamic:
        etat_block, etat_ref = _build_etat_init_block(model_data)
        schema = analysis.get("schema", "HHT")
        if schema in ("DIFF_CENT", "TCHAMWA"):
            schema_clause = (
                "    MASS_DIAG='OUI',\n"
                "    SCHEMA_TEMPS=_F(SCHEMA='{0}', FORMULATION='ACCELERATION'"
                "{1}),\n"
            ).format(schema, ", STOP_CFL='NON'"
                     if model_data.get("_explicit_no_cfl") else "")
        elif schema == "HHT":
            schema_clause = (
                "    SCHEMA_TEMPS=_F(SCHEMA='HHT', ALPHA={0!r}, "
                "FORMULATION='DEPLACEMENT'),\n"
            ).format(analysis.get("hht_alpha", -0.1))
        else:
            schema_clause = (
                "    SCHEMA_TEMPS=_F(SCHEMA='NEWMARK', "
                "FORMULATION='DEPLACEMENT'),\n")
        extra = (schema_clause + etat_ref +
                 "    ARCHIVAGE=_F(LIST_INST=outlist),\n")
        listinst_block = listinst_block + "\n" + etat_block
    # ENERGIE=_F() (U4.53.01 par. 3.22; catalogus dyna_non_line.py):
    # energiebalans per stap in study.mess, getoond in het
    # convergentiescherm. Met contact CONTINUE stopt Code-Aster met
    # <EXCEPTION> MECANONLINE5_15 (gezien met 17.4); dan weglaten.
    if analysis.get("energy_balance", False):
        if contact_ref:
            log(tr("WARNING: Energiebalans (ENERGIE) weggelaten: Code-Aster "
                   "kent die niet met contact (DEFI_CONTACT; MECANONLINE5_15 "
                   "gezien met CONTINUE).",
                   "WARNING: Energy balance (ENERGIE) omitted: Code-Aster "
                   "does not support it with contact (DEFI_CONTACT; "
                   "MECANONLINE5_15 seen with CONTINUE)."))
        else:
            extra += "    ENERGIE=_F(),\n"
    # Stabiliteitscriterium per stap (niet-lineaire knik; alleen statisch)
    crit_stab = (not dynamic) and bool(analysis.get("crit_stab", False))
    if crit_stab:
        extra += _crit_stab_args()
        crit_kind = _crit_stab_kind(comportement_block)
        log("INFO: CRIT_STAB per stap ({0}).".format(
            "kritische lastfactor van de huidige last" if crit_kind ==
            "factor" else "kleinste eigenwaarde van de tangentstijfheid, "
            "grote verplaatsingen"))
    # Bij niet-convergentie gooit Code-Aster een ConvergenceError (id
    # MECANONLINE*), maar 'res' bevat dan alle gearchiveerde stappen tot het
    # laatste geconvergeerde tijdstip (gezien met Code-Aster 17.4). De job
    # gaat daarom door met de nabewerking; BRIDGE_ONVOLLEDIG in study.mess
    # vertelt bridge_run_aster.py tot welk tijdstip er resultaten zijn.
    statnonline_block = contact_block + (
        "try:\n"
        "    res = {command}(\n"
        "        MODELE=model,\n"
        "        CHAM_MATER=fieldmat,\n"
        "{cara_ref}"
        "{excit_clause}\n"
        "{contact_ref}"
        "{comp}"
        "        INCREMENT=_F(LIST_INST=listinst),\n"
        "{extra}"
        "{solveur}"
        "        NEWTON=_F(REAC_ITER={reac}),\n"
        "        CONVERGENCE=_F({conv}),\n"
        "    )\n"
        "except Exception as err:\n"
        "    if not str(getattr(err, 'id_message', '')).startswith("
        "'MECANONLINE'):\n"
        "        raise\n"
        "    print('BRIDGE_ONVOLLEDIG', res.getAccessParameters()['INST'][-1])\n"
        "t_res = res.getAccessParameters()['INST'][-1]\n"
    ).format(
        command      = command,
        cara_ref     = _indent(cara_elem_ref),
        excit_clause = _indent(excit_clause),
        contact_ref  = _indent(contact_ref),
        comp         = _indent(comportement_block),
        extra        = _indent(extra),
        conv         = _convergence_args(analysis),
        reac         = reac_iter,
        solveur      = _indent(_build_solveur_ref(analysis)),
    )

    # --------------------------------------------------
    # BEZWIJKEN VAN ELEMENTEN (bridge_failure.py): een lus over de
    # tijdstappen in plaats van een enkele STAT_NON_LINE.
    # --------------------------------------------------
    plan = bridge_failure.failure_plan(
        model_data, analysis,
        lambda mat: _relation_for(model_data, mat), _deformation_for)
    _warn_plastic_hex8(model_data, plan)
    if plan:
        factor = _failure_stiffness_factor(analysis)
        rayleigh = model_data.get("rayleigh") if dynamic else None
        weak_block, weak_names = bridge_failure.weak_materials(
            model_data, plan, factor, _material_concepts(model_data),
            lambda props, f: _elas_args(props, _thermal_active(model_data),
                                        rayleigh, f),
            model_data.get("_traction_curves", {}), _mat_comment)
        materials_block += weak_block
        affe_entries, varc = model_data["_fieldmat_parts"]
        # Controlemomenten: statisch elke rekenstap ('times'); dynamisch de
        # uitvoertijden ('outlist'). Die zijn ook rekenstappen (INCREMENT
        # INST_FIN moet in de lijst staan): impliciet en expliciet loopt
        # listinst per uitvoerinterval (_build_dyna_listinst_block).
        if not dynamic:
            segments = "list(times.getValues())"
        else:
            segments = "[0.0] + list(outlist.getValues())"
        loop_extra = extra
        first = "{}"
        if dynamic and etat_ref:
            # De beginsnelheid alleen in de eerste aanroep; daarna komt
            # ETAT_INIT uit de lus.
            loop_extra = extra.replace(etat_ref, "")
            first = "dict({0})".format(etat_ref.strip().rstrip(","))
        statnonline_block = contact_block + bridge_failure.build_solve_block(
            plan, weak_names, affe_entries, varc, {
                "args": (_indent(cara_elem_ref) + _indent(excit_clause) +
                         "\n" + _indent(contact_ref) +
                         _indent(comportement_block) + _indent(loop_extra) +
                         _indent(_build_solveur_ref(analysis)) +
                         "        CONVERGENCE=_F({0}),\n".format(
                             _convergence_args(analysis))),
                "newton": "REAC_ITER={0}".format(reac_iter),
                "command": command, "segments": segments, "first": first,
                "dynamic": dynamic,
                "explicit": dynamic and analysis.get("schema", "HHT") in (
                    "DIFF_CENT", "TCHAMWA")})
    if crit_stab:
        statnonline_block += _crit_stab_report(crit_kind)
    if imperfection:
        pre, restore = _imperfection_blocks(
            model_data, analysis, imperfection, charges, excit_clause,
            cara_elem_ref, t_end)
        if _has_cara(model_data):
            # Balk- en schaalassen opnieuw op de vervormde geometrie
            pre += cara_elem_block
        statnonline_block = pre + "\n" + statnonline_block
        postreleve_block = restore + postreleve_block

    # --------------------------------------------------
    # BESTANDEN SCHRIJVEN
    # --------------------------------------------------
    try:
        template_content = _read_template(analysis["template"])
        _write_comm(comm_path, template_content.format(
            defigroup_block      = defigroup_block,
            model_block          = model_block,
            cara_elem_block      = cara_elem_block,
            plastic_curves_block = plastic_curves_block,
            materials_block      = materials_block,
            fieldmat_block       = fieldmat_block,
            load_funcs_block     = load_funcs_block,
            listinst_block       = listinst_block,
            loads_const_block    = loads_const_block,
            statnonline_block    = statnonline_block,
            calc_champ_block     = calc_champ_block,
            postreleve_block     = postreleve_block,
            impr_table_block     = impr_table_block,
            impr_resu_block      = _build_impr_resu_block(
                model_data, with_plastic=with_plastic),
        ))
        log("SUCCESS: .comm geschreven naar '{0}'.".format(comm_path))

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
            time_limit   = analysis.get("time_limit",   1800),
            memory_limit = analysis.get("memory_limit", 4096),
            ncpus    = CONFIG_BRIDGE["ncpus"],
            comm     = comm_path,
            msh      = msh_path,
            mess     = os.path.join(work_dir, run_name(".mess")),
        ) + _export_result_lines(work_dir, resu_name)
        with open(export_path, 'w') as f:
            f.write(export_content)
        log("SUCCESS: .export geschreven naar '{0}'.".format(export_path))

        return export_path

    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}. "
               "Controleer de .comm-template op {{placeholder}}-namen.",
               "ERROR: Template placeholder missing: {0}. "
               "Check the .comm template for {{placeholder}} names.")
            .format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren solver-bestanden mislukt: {0}",
               "ERROR: Generating solver files failed: {0}").format(str(e)))

    return None


# ==========================================
# BUILDER VOOR MODAAL EN LINEAIRE KNIK  (CALC_MODES)
#
# Mecway V30 (frequentie) en B30 (lineaire knik) slaan elke mode op als
# <mode id="k" frequency="f Hz"> resp. <mode id="k" bucklingfactor="x">
# binnen <results> (nagelopen met Mecway 33 headless op de voorbeelden
# VibratingCantileverBeam/-Solid/-FreePlate en BucklingBeam/-Plate); dat
# schrijft aster_results_export.py. Normering van de vormen in Mecway
# (nagerekend op dezelfde voorbeelden): trillingsvormen met
# gegeneraliseerde massa 1 (tip van de ingeklemde balk 2/sqrt(m) =
# 0,2059), knikvormen met gegeneraliseerde stijfheid phi^T K phi = 1 (tip
# van de ingeklemde kolom 0,001404 = 1/sqrt(EI (pi/2L)^4 L/2)).
# ==========================================
# NORM_MODE NORME (catalogus calc_modes.py v17.4).
_MODE_NORMS = ("MASS_GENE", "RIGI_GENE", "EUCL", "EUCL_TRAN", "TRAN",
               "TRAN_ROTA")


def _collapse_histories(model_data, command):
    """
    Lasten en voorwaarden met een tijdshistorie krijgen hun laatste waarde
    (zoals MECA_STATIQUE in _build_lin_static): een modale of knik-
    berekening is niet in de tijd.
    """
    for bc in model_data["bcs"]:
        new_dict = {}
        for k, v in bc["aster_dict"].items():
            if isinstance(v, list):
                last_val = v[-1][1] if v else 0.0
                log(tr("WARNING: Tijdsstap-belasting {0} op '{1}' is "
                       "gecollapsed naar laatste waarde {2} voor {3}.",
                       "WARNING: Time-step load {0} on '{1}' is "
                       "collapsed to its last value {2} for {3}.").format(
                        k, bc["selection"], last_val, command))
                new_dict[k] = last_val
            else:
                new_dict[k] = v
        bc["aster_dict"] = new_dict


def _is_load_charge(charge):
    """True als een last uit _build_charges een belasting is (geen
    oplegging of koppeling)."""
    return any(kw in _LOAD_KEYWORDS for kw in charge[1])


def _modal_charges(model_data, buckling, prestress=False):
    """
    Lasten voor CALC_MODES (_build_charges): (charges, namen van de
    opleggingslasten, namen van de belastingen). Knik en modaal met
    voorspanning (prestress, instelling modal_prestress): alles (de
    belastingen bepalen het spanningsveld). Modaal zonder voorspanning:
    alleen de opleggingen en koppelingen; de belastingen vervallen met een
    WARNING en een regel in skipped_loads (Mecway rekent met belastingen
    altijd voorgespannen, manual v33 par. 6.3 "Stress stiffening").
    """
    charges = _build_charges(model_data)
    if not buckling and not prestress:
        dropped = [c for c in charges if _is_load_charge(c)]
        kws = []
        for c in dropped:
            for kw in c[1]:
                if kw not in kws:
                    kws.append(kw)
        if _thermal_active(model_data):
            # De thermische rek doet alleen mee via MECA_STATIQUE.
            kws.append(tr("thermische rek", "thermal strain"))
        if kws:
            log(tr("WARNING: Modale analyse: belastingen ({0}) worden "
                   "genegeerd (instelling 'Voorspanning door belastingen' "
                   "uit). Mecway rekent dan met spanningsverstijving "
                   "(stress stiffening); de frequenties kunnen dus "
                   "afwijken.",
                   "WARNING: Modal analysis: loads ({0}) are ignored "
                   "(setting 'Prestress from loads' off). Mecway then "
                   "includes stress stiffening, so the frequencies may "
                   "differ.").format(", ".join(kws)))
            model_data.setdefault("skipped_loads", []).append(
                tr("belastingen in de modale analyse ({0}; voorspanning "
                   "uit)",
                   "loads in the modal analysis ({0}; prestress "
                   "off)").format(", ".join(kws)))
        charges = [c for c in charges if not _is_load_charge(c)]
    names_bc, names_load = [], []
    for k, c in enumerate(charges):
        (names_load if _is_load_charge(c) else names_bc).append(
            "load_{0}".format(k + 1))
    return charges, names_bc, names_load


_IMPOSED_DOFS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ", "DNOR")


def _nonzero_imposed(model_data):
    """Selecties met een opgelegde verplaatsing of rotatie <> 0
    (displacement, noderotation, frictionless). Na _collapse_histories
    zijn de waarden getallen."""
    out = []
    for bc in model_data["bcs"]:
        if bc["type"] not in ("displacement", "noderotation",
                              "frictionless"):
            continue
        for k, v in bc.get("aster_dict", {}).items():
            if (k in _IMPOSED_DOFS and isinstance(v, (int, float))
                    and v != 0.0):
                if bc["selection"] not in out:
                    out.append(bc["selection"])
    return out


def _prestress_plan(model_data, charges, names_bc, names_load):
    """
    Modaal met voorspanning (Mecway V30 met belastingen, manual v33 par.
    6.3 "Stress stiffening": eerst lineair statisch, dan de modes met de
    aangepaste stijfheid). Returns None bij een fout (ERROR gelogd), anders
    een dict:
      rotation : namen van de ROTATION-lasten; die gaan ook in ASSEMBLAGE
                 CHARGE voor RIGI_ROTA (spin softening, zoals Mecway:
                 Impeller-voorbeeld par. 11.21 "stress stiffening and spin
                 softening"; route als testcase sdll133a: RIGI_MECA +
                 RIGI_GEOM + RIGI_ROTA, alle COEF_R 1).
    Mecway rekent geen voorspanning met opgelegde verplaatsingen of
    rotaties <> 0 (par. 6.3: "not allowed"; headless gezien: geen
    oplossing). De bridge geeft dan een ERROR met de oplossing.
    """
    nonzero = _nonzero_imposed(model_data)
    if nonzero:
        log(tr("ERROR: Modaal met voorspanning: opgelegde verplaatsing of "
               "rotatie <> 0 op {0}. Mecway rekent dat ook niet (manual "
               "par. 6.3). Zet de waarde op 0, of zet 'Voorspanning door "
               "belastingen' uit (pagina Modaal; dan telt alleen dat de "
               "vrijheidsgraad vastligt en vervallen de belastingen).",
               "ERROR: Modal with prestress: imposed displacement or "
               "rotation <> 0 on {0}. Mecway does not solve this either "
               "(manual section 6.3). Set the value to 0, or switch off "
               "'Prestress from loads' (Modal page; then only the fixed "
               "degree of freedom counts and the loads are dropped).")
            .format(", ".join("'{0}'".format(s) for s in nonzero)))
        return None
    if not names_bc:
        log(tr("ERROR: Modaal met voorspanning zonder opleggingen: de "
               "statische berekening onder de belastingen is singulier. "
               "Leg het model in Mecway vast, of zet 'Voorspanning door "
               "belastingen' uit (pagina Modaal).",
               "ERROR: Modal with prestress without supports: the static "
               "analysis under the loads is singular. Add supports in "
               "Mecway, or switch off 'Prestress from loads' (Modal "
               "page)."))
        return None
    rotation = [n for n, c in zip(["load_{0}".format(k + 1) for k in
                                   range(len(charges))], charges)
                if c[0] == "AFFE_CHAR_MECA" and list(c[1]) == ["ROTATION"]]
    if any(bc["type"] == "centrifugal" for bc in model_data["bcs"]):
        if not rotation:
            # Met schalen wordt de centrifugaalkracht een FORMULE-last
            # (_centrifugal_loads); RIGI_ROTA vraagt een ROTATION-last.
            log(tr("WARNING: Centrifugaalkracht in een model met schalen: "
                   "alleen de spanningsverstijving telt mee, niet de "
                   "spin softening (RIGI_ROTA kan niet zonder Code-Aster "
                   "ROTATION). Frequenties kunnen hoger zijn dan in "
                   "Mecway.",
                   "WARNING: Centrifugal force in a model with shells: "
                   "only stress stiffening is included, not spin softening "
                   "(RIGI_ROTA is not possible without Code-Aster "
                   "ROTATION). Frequencies may be higher than in Mecway."))
        elif any(dict(d["cara"]).get("M_T_D_N") for d in
                 model_data.get("discretes", {}).values()):
            log(tr("WARNING: Centrifugaalkracht: de spin softening van "
                   "knoopmassa's (mass) telt niet mee (RIGI_ROTA alleen op "
                   "elementen); hun centrifugaalkracht wel.",
                   "WARNING: Centrifugal force: the spin softening of "
                   "point masses (mass) is not included (RIGI_ROTA only on "
                   "elements); their centrifugal force is."))
    log("INFO: Modaal met voorspanning: MECA_STATIQUE met de belastingen, "
        "dan K + Kg (RIGI_GEOM){0} in CALC_MODES.".format(
            " + RIGI_ROTA" if rotation else ""))
    return {"rotation": rotation}


def _mode_count(model_data, analysis):
    """Aantal modes: Mecway's maxmode, anders de instelling modal_modes."""
    n = model_data.get("maxmode")
    if n is None or n < 1:
        n = int(analysis.get("modal_modes", 10))
        log("INFO: Geen maxmode in het Mecway-model; {0} modes "
            "(instelling modal_modes).".format(n))
    return max(1, int(n))


def _mode_norm(analysis, buckling, quiet=False):
    """NORM_MODE NORME uit de instelling modal_norm. Knik heeft geen
    massamatrix: MASS_GENE wordt dan RIGI_GENE (zoals Mecway). quiet: geen
    meldingen (tweede aanroep voor dezelfde run)."""
    norm = "{0}".format(analysis.get(
        "modal_norm", "RIGI_GENE" if buckling else "MASS_GENE")).upper()
    if norm not in _MODE_NORMS:
        if not quiet:
            log(tr("WARNING: Onbekende normering '{0}' (modal_norm); {1} "
                   "gebruikt.",
                   "WARNING: Unknown normalisation '{0}' (modal_norm); {1} "
                   "used.").format(norm, "RIGI_GENE" if buckling
                                   else "MASS_GENE"))
        norm = "RIGI_GENE" if buckling else "MASS_GENE"
    if buckling and norm == "MASS_GENE":
        if not quiet:
            log(tr("WARNING: Knik heeft geen massamatrix; normering "
                   "RIGI_GENE i.p.v. MASS_GENE.",
                   "WARNING: Buckling has no mass matrix; normalisation "
                   "RIGI_GENE instead of MASS_GENE."))
        norm = "RIGI_GENE"
    return norm


# Vrij-vrij (modaal zonder opleggingen): zoekfrequentie -f_s met
# (2 pi f_s)^2 = 1e-8 x de grootste diag(K)/diag(M). Dan is |sigma| M van
# de orde 1e-8 van de stijfste vrijheidsgraad: net boven de
# singulariteitsgrens van MUMPS (NPREC 8: 8 cijfers verlies), en zo dicht
# mogelijk bij 0, want hoe verder de shift van de gezochte eigenwaarden,
# hoe slechter Sorensen ze scheidt. Gezien met Code-Aster 17.4:
#   - VibratingFreePlate (dunne plaat, COQUE_3D): -0,83 Hz faalde
#     (ALGELINE3_81, de membraanstijfheid E t is veel groter dan de
#     buigstijfheid); -100 Hz en -138 Hz (deze regel) gaven de 6 starre
#     modes (~0 Hz) en 331,73 / 480,57 / 562,86 Hz (Mecway 332,65 /
#     480,60 / 562,87 Hz met quad8);
#   - een ingeklemde hex20-balk met de factor 1e-6 (-636 Hz, eerste mode
#     16,7 Hz): Sorensen vond geen enkele mode (ALGELINE5_49 en
#     ALGELINE3_78). Daarom alleen vrij-vrij; een mechanisme in een
#     opgelegd model geeft ALGELINE3_81 (uitleg in bridge_run_aster; de
#     gebruiker kan dan een negatieve zoekfrequentie kiezen).
_FREE_SHIFT_BLOCK = (
    "# Vrij-vrij: zoekfrequentie onder 0 (bridge_to_aster._FREE_SHIFT_BLOCK)\n"
    "import numpy as _np\n"
    "def _bridge_diag(_m):\n"
    "    _v, _r, _c, _n = _m.getValuesWithDescription()\n"
    "    _r, _c, _v = _np.asarray(_r), _np.asarray(_c), _np.asarray(_v)\n"
    "    _d = _np.zeros(_n)\n"
    "    _d[_r[_r == _c]] = _v[_r == _c]\n"
    "    return _d\n"
    "_kd, _md = _bridge_diag(rigidite), _bridge_diag(masse)\n"
    "_ok = (_md > 0.0) & (_kd > 0.0)\n"
    "bridge_fshift = 1.0\n"
    "if _ok.any():\n"
    "    bridge_fshift = max(1.0e-3, float(_np.sqrt(1.0e-8 * (_kd[_ok] / "
    "_md[_ok]).max())) / (2.0 * _np.pi))\n"
    "print('BRIDGE_FREE_SHIFT', bridge_fshift)\n")


def _calc_modes_block(model_data, analysis, buckling, cara_ref, free=False,
                      damped=False):
    """
    res = CALC_MODES(...) (catalogus calc_modes.py v17.4, U4.52.02):
      modaal: TYPE_RESU 'DYNAMIQUE', OPTION 'PLUS_PETITE' (de laagste
        frequenties, zoals Mecway) met CALC_FREQ NMAX_FREQ, of 'CENTRE'
        rond modal_shift_hz (CALC_FREQ FREQ; negatief: de laagste modes
        met een verschoven, regelmatige K - sigma M, voor mechanismen);
      knik: TYPE_RESU 'MODE_FLAMB' met MATR_RIGI_GEOM, OPTION
        'PLUS_PETITE' (kleinste |CHAR_CRIT|) met CALC_CHAR_CRIT
        NMAX_CHAR_CRIT. OPTION 'CENTRE' rond een kniklastfactor wordt in
        Code-Aster 17.4 genegeerd ("valeur de décalage en charge critique
        : 0", gemeten met 90/200/-200 op BU-01); 'BANDE' werkt wel. Mecway
        rekent ook altijd de kleinste factoren (zijn 'shift' is een
        oplosserinstelling: BucklingPlate shift 1000, factoren 7..12).
        CHAR_CRIT is Mecway's kniklastfactor (BucklingBeam: Mecway
        41124,699, Code-Aster CHAR_CRIT +41124,699, gezien); negatief =
        knik bij de omgekeerde belasting (aster_results_export).
    VERI_MODE SEUIL (default 1e-6) = grens voor de relatieve fout per mode,
    plus de Sturm-test (STURM 'OUI', standaard): telt de eigenwaarden in
    [lambda_1, lambda_n] (marge PREC_SHIFT). Die faalt ook als een
    meervoudige mode op de grens n valt (<EXCEPTION> ALGELINE5_23
    "théoriquement 4 ... calculé 3", dan ALGELINE2_74; gezien met Mecway's
    BucklingBeam, vierkante doorsnede, 3 modes). Mecway geeft dan gewoon de
    gevraagde modes. Opnieuw rekenen in een try/except kan niet: na een
    <E>-melding stopt Code-Aster bij het volgende commando (CATAMESS_6,
    gezien). Daarom STOP_ERREUR='NON': beide controles worden alarmen
    (<A>), die bridge_run_aster met uitleg als WARNING logt.
    damped: complexe modes met de dempingsmatrix 'amor'
    (bridge_modal_damping.calc_modes_lines).
    """
    n = _mode_count(model_data, analysis)
    norm = _mode_norm(analysis, buckling)
    prelude = ""
    lines = ["res = CALC_MODES(",
             "    TYPE_RESU='{0}',".format("MODE_FLAMB" if buckling
                                           else "DYNAMIQUE"),
             "    MATR_RIGI=rigidite,"]
    if buckling:
        lines.append("    MATR_RIGI_GEOM=rigi_geo,")
        lines += ["    OPTION='PLUS_PETITE',",
                  "    CALC_CHAR_CRIT=_F(NMAX_CHAR_CRIT={0}),".format(n)]
    else:
        lines.append("    MATR_MASS=masse,")
        shift = float(analysis.get("modal_shift_hz", 0.0) or 0.0)
        if damped:
            if free and shift == 0.0:
                prelude = _FREE_SHIFT_BLOCK
            lines += bridge_modal_damping.calc_modes_lines(n, shift, free)
        elif shift != 0.0:
            lines += ["    OPTION='CENTRE',",
                      "    CALC_FREQ=_F(FREQ={0!r}, NMAX_FREQ={1}),".format(
                          shift, n)]
        elif free:
            # Vrij-vrij: K is singulier, dus de standaard-shift 0 van
            # PLUS_PETITE (en Code-Aster's eigen verschuiving naar
            # -SEUIL_FREQ = -0,01 Hz) faalt: <EXCEPTION> ALGELINE3_81
            # (gezien met Mecway's VibratingFreePlate; ook METHODE
            # 'TRI_DIAG' met MODE_RIGIDE='OUI' gaf ALGELINE3_81). CENTRE
            # rond een negatieve frequentie geeft dezelfde laagste modes
            # (alle omega^2 >= 0) met een regelmatige K + |sigma| M, zie
            # _FREE_SHIFT_BLOCK.
            prelude = _FREE_SHIFT_BLOCK
            lines += ["    OPTION='CENTRE',",
                      "    CALC_FREQ=_F(FREQ=-bridge_fshift, NMAX_FREQ={0}),"
                      .format(n)]
        else:
            lines += ["    OPTION='PLUS_PETITE',",
                      "    CALC_FREQ=_F(NMAX_FREQ={0}),".format(n)]
    lines += ["    CHAM_MATER=fieldmat,"]
    if cara_ref:
        lines.append("    CARA_ELEM=cara,")
    # Knik met RIGI_GENE: Code-Aster kent dat niet voor MODE_FLAMB
    # (<EXCEPTION> ALGELINE4_77, gezien); aster_results_export normeert dan
    # zelf (_stiffness_scales, rigi_geo in _modes_export_block).
    aster_norm = "TRAN_ROTA" if (buckling and norm == "RIGI_GENE") else norm
    lines += ["    NORM_MODE=_F(NORME='{0}'),".format(aster_norm),
              "    VERI_MODE=_F(SEUIL={0}, STOP_ERREUR='NON'),".format(
                  "%.10g" % float(analysis.get("modal_tolerance", 1.0e-6))),
              "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(
                  int(analysis.get("solver_nprec", 8))),
              ")"]
    log("INFO: CALC_MODES {0}: {1} modes, normering {2}.".format(
        "MODE_FLAMB" if buckling else "DYNAMIQUE", n, norm))
    return prelude + "\n".join(lines) + "\n"


def _modes_export_block(work_dir, model_data, stiffness_norm=False,
                        fields=("displacements",), mass=False,
                        complex_modes=False):
    """aster_results_export: modes naar Mecway's <mode>-formaat (double,
    zoals Mecway's eigen modale/knik-oplossing) en een overzicht per mode
    in de .mess (BRIDGE_MODE-regels). stiffness_norm: knikvormen normeren
    op phi^T K phi = 1 met de geassembleerde rigi_geo. fields: groepen
    voor export_results (spanningen per mode: _modal_stress_fields). mass:
    de massamatrix 'masse' meegeven (effectieve massa voor de rotaties).
    complex_modes: complexe modes (bridge_modal_damping); export_results
    krijgt dan ook 'masse' (normering van het reele deel)."""
    scripts = os.path.dirname(os.path.abspath(__file__))
    extra = ""
    if len(fields) > 1:
        extra = ("    extra_results=dict((k, globals()[k]) for k in@N"
                 "                       ('res_sup', 'res_moy', 'res_inf')@N"
                 "                       if k in globals()),@N")
    return (
        "# Resultaten in Mecway's eigen formaat (bridge: result_route='liml')@N"
        "import sys@N"
        "sys.path.insert(0, {scripts})@N"
        "import aster_results_export@N"
        "aster_results_export.print_modes(res{mass})@N"
        "aster_results_export.export_results(@N"
        "    res, {fragment}, {liml},@N"
        "{extra}"
        "    fields={fields!r}, precision='double'{norm}{cmass})@N"
    ).replace("@N", chr(10)).format(
        scripts=_py_str(scripts), fragment=_py_str(results_file(work_dir)),
        liml=_py_str(model_data.get("liml_path", "")),
        mass=", mass=masse" if mass else "", extra=extra.replace(
            "@N", chr(10)), fields=[str(f) for f in fields],
        norm=", rigi_geo=rigi_geo" if stiffness_norm else "",
        cmass=", mass=masse" if complex_modes else "")


# Velden die bij een modale analyse per mode naar Mecway kunnen (instelling
# "fields" op de pagina Modaal; Mecway rekent ze ook per mode als je ze
# vóór het oplossen onder Solution aanvraagt, nagelopen headless met
# Mecway 33: stressxx.. en vonmises als node- en elementnodevariable).
_MODAL_STRESS_GROUPS = ("stresses", "vonmises")


def _modal_stress_fields(analysis, buckling):
    """(groepen voor export_results, genegeerde groepen). Spanningen per
    mode alleen bij modaal (niet bij knik: de knikvormen worden pas in
    aster_results_export genormeerd, de spanningen niet)."""
    wanted = [f for f in analysis.get("fields", ["displacements"])
              if f != "displacements"]
    use = [] if buckling else [f for f in wanted
                               if f in _MODAL_STRESS_GROUPS]
    return ["displacements"] + use, [f for f in wanted if f not in use]


def _build_modal(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Genereer study.comm en study.export voor CALC_MODES:
      modaal (analysis "type_resu" 'DYNAMIQUE', Mecway V30): stijfheid en
        massa met ASSEMBLAGE (U4.61.21; RIGI_MECA, MASS_MECA, met de
        opleggingen als CHARGE), daarna CALC_MODES;
      modaal met voorspanning (belastingen of thermische rek aanwezig en
        instelling modal_prestress aan, zoals Mecway): eerst MECA_STATIQUE
        en SIEF_ELGA zoals bij knik, dan K = RIGI_MECA + RIGI_GEOM (+
        RIGI_ROTA bij centrifugaalkracht) met COMB_MATR_ASSE
        (_prestress_plan);
      knik ('MODE_FLAMB', Mecway B30): MECA_STATIQUE met alle lasten, het
        spanningsveld SIEF_ELGA (CREA_CHAMP EXTR), ASSEMBLAGE RIGI_MECA en
        RIGI_GEOM met dat veld, daarna CALC_MODES MODE_FLAMB (route van
        testcase ssll105a: CALC_MATR_ELEM RIGI_GEOM + ASSE_MATRICE, hier in
        een ASSEMBLAGE; catalogus assemblage.py v17.4: RIGI_GEOM met
        SIEF_ELGA).
    Elementen, secties, materialen en randvoorwaarden als MECA_STATIQUE;
    knoopmassa's (POI1 M_T_D_N / M_TR_D_N) tellen mee in MASS_MECA.
    Alleen route 'liml' (de modes zijn geen tijdstappen).
    Akoestische holtemodes (Mecway A30, analysis "phenomene"
    'ACOUSTIQUE'): eigen builder in bridge_acoustic.py.
    """
    import bridge_acoustic
    if bridge_acoustic.is_acoustic(analysis):
        return bridge_acoustic.build_acoustic_modes(
            work_dir, model_data, msh_path, resu_name, analysis)
    # Vibro-akoestiek (analysis "vibroacoustic"): constructie + fluidum,
    # gekoppelde modes in bridge_vibroacoustic.py.
    import bridge_vibroacoustic
    if bridge_vibroacoustic.is_vibroacoustic(analysis):
        return bridge_vibroacoustic.build_vibroacoustic_modes(
            work_dir, model_data, msh_path, resu_name, analysis)
    buckling = analysis.get("type_resu", "DYNAMIQUE") == "MODE_FLAMB"
    what = "MODE_FLAMB" if buckling else "DYNAMIQUE"
    log("--- Generating Aster Files (CALC_MODES {0}) ---".format(what))
    comm_path = os.path.join(work_dir, run_name(".comm"))
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor modale "
               "en knikanalyses. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for modal "
               "and buckling analyses. Choose 'liml' (General page)."))
        return None
    if not _check_linear(model_data, tr("een modale of knikanalyse",
                                        "a modal or buckling analysis")):
        return None
    bridge_failure.failure_plan(
        model_data, analysis,
        lambda mat: _relation_for(model_data, mat), _deformation_for)
    _collapse_histories(model_data, "CALC_MODES")
    # Cyclische symmetrie (Mecway Cyclic symmetry, alleen modaal):
    # MODE_ITER_CYCL in bridge_cyclic.py.
    import bridge_cyclic
    if not buckling and bridge_cyclic.is_cyclic(model_data):
        return bridge_cyclic.build_cyclic_modes(
            work_dir, model_data, msh_path, resu_name, analysis)
    if model_data.get("analysis_type") == "B30" and model_data.get(
            "analysis_shift") is not None:
        log("INFO: Mecway's shift ({0}) is een instelling van Mecway's "
            "eigen oplosser; de bridge zoekt, zoals Mecway, de laagste "
            "kniklastfactoren.".format(
                model_data["analysis_shift"]))
    # Complexe modes met demping (instelling modal_complex; standaard uit =
    # reele modes zoals Mecway): bridge_modal_damping.
    damping = bridge_modal_damping.plan(model_data, analysis, buckling)
    fields, ignored = _modal_stress_fields(analysis, buckling)
    if damping and len(fields) > 1:
        log(tr("INFO: Complexe modes: alleen de trillingsvormen gaan naar "
               "Mecway, geen spanningen per mode ({0}).",
               "INFO: Complex modes: only the mode shapes go to Mecway, no "
               "stresses per mode ({0}).").format(", ".join(fields[1:])))
        fields = ["displacements"]
    if ignored:
        log("INFO: Modes: naar Mecway gaan de trillings-/knikvormen "
            "(displacements){0}; genegeerd: {1}.".format(
                " en spanningen per mode" if len(fields) > 1 else "",
                ", ".join(ignored)))
    if len(fields) > 1:
        log("INFO: Spanningen per mode ({0}): de vormen zijn genormeerd "
            "({1}), dus de spanningen zijn alleen ten opzichte van elkaar "
            "betekenisvol (verdeling, plaats van het maximum), niet als "
            "waarde in Pa.".format(", ".join(fields[1:]),
                                   _mode_norm(analysis, buckling,
                                              quiet=True)))

    defigroup_block = _build_defigroup_block(model_data)
    model_block = _build_model_block(model_data)
    cara_elem_block = _build_cara_elem_block(model_data)
    cara_elem_ref = "    CARA_ELEM=cara,\n" if _has_cara(model_data) else ""
    materials_block = _build_materials_block(model_data, analysis)
    fieldmat_block = _build_fieldmat_block(model_data)

    # Modaal met voorspanning (stress stiffening, zoals Mecway): alleen als
    # er belastingen zijn (Mecway: "When any loads are present", manual
    # v33 par. 6.3); thermische rek telt mee (Mecway-voorbeeld
    # VibratingMembrane, par. 11.20: spanning via thermische rek).
    prestress_on = (not buckling) and bool(
        analysis.get("modal_prestress", True))
    charges, names_bc, names_load = _modal_charges(model_data, buckling,
                                                   prestress_on)
    prestress = None
    if prestress_on and (names_load or _thermal_active(model_data)):
        prestress = _prestress_plan(model_data, charges, names_bc,
                                    names_load)
        if prestress is None:
            return None
    loads_block, excit_clause = _render_charges(charges, model_data)
    extra = model_data.get("aster_custom", {}).get("excit", [])
    if extra:
        # Ook in ASSEMBLAGE CHARGE: zo tellen verbindingen uit #ASTER-code
        # (LIAISON_ELEM, LIAISON_MAIL, DDL_IMPO, ...) mee in de matrices.
        # Krachten in zo'n last dragen niet bij aan RIGI_MECA/MASS_MECA/
        # RIGI_GEOM (U4.61.21: CHARGE levert de kinematische condities);
        # doorgerekend met voorbeeld 1 van docs/ASTER_regels_voorbeelden.md.
        log("INFO: #ASTER-EXCIT-lasten {0}: in de matrices (ASSEMBLAGE "
            "CHARGE){1}.".format(", ".join(extra), " en in MECA_STATIQUE"
                                 if (buckling or prestress) else ""))
    if not names_bc:
        if buckling:
            log(tr("ERROR: Knik zonder opleggingen: de statische "
                   "berekening is singulier. Leg het model in Mecway vast.",
                   "ERROR: Buckling without supports: the static analysis "
                   "is singular. Add supports in Mecway."))
            return None
        log(tr("WARNING: Geen opleggingen (vrij-vrij): de eerste modes "
               "(tot 6) zijn starre-lichaamsbewegingen met een frequentie "
               "van ~0 Hz; tel ze mee bij het aantal modes.",
               "WARNING: No supports (free-free): the first modes (up to "
               "6) are rigid body motions with a frequency of ~0 Hz; count "
               "them in the number of modes."))
    if buckling and not (names_load or extra):
        log(tr("ERROR: Knik zonder belasting: de kniklastfactor is een "
               "veelvoud van de aangebrachte last. Breng in Mecway de "
               "(referentie)belasting aan.",
               "ERROR: Buckling without a load: the buckling factor is a "
               "multiple of the applied load. Apply the (reference) load "
               "in Mecway."))
        return None

    if buckling or prestress:
        static_block = (
            ("# Spanningstoestand onder de aangebrachte lasten (de\n"
             "# kniklastfactor is een veelvoud van deze lasten).\n"
             if buckling else
             "# Voorspanning: spanningstoestand onder de aangebrachte\n"
             "# lasten (Mecway manual v33 par. 6.3, stress stiffening).\n") +
            "stat = MECA_STATIQUE(\n"
            "    MODELE=model,\n"
            "    CHAM_MATER=fieldmat,\n"
            "{cara}{excit}\n"
            "    SOLVEUR=_F(METHODE='MUMPS', NPREC={nprec}),\n"
            ")\n"
            "sig = CREA_CHAMP(OPERATION='EXTR', TYPE_CHAM='ELGA_SIEF_R',\n"
            "                 RESULTAT=stat, NUME_ORDRE=1, "
            "NOM_CHAM='SIEF_ELGA')\n").format(
                cara=cara_elem_ref, excit=excit_clause,
                nprec=int(analysis.get("solver_nprec", 8)))
        second = ("        _F(MATRICE=CO('rigi_geo'), OPTION='RIGI_GEOM', "
                  "SIEF_ELGA=sig),\n")
    else:
        static_block = ("#-- niet van toepassing (modaal zonder "
                        "voorspanning) --\n")
        second = ""
    if not buckling:
        second = ("        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n" +
                  second)
    rotation = prestress["rotation"] if prestress else []
    if rotation:
        # Spin softening: centrifugale stijfheid (RIGI_ROTA; vraagt de
        # ROTATION-last in CHARGE, catalogus calc_matr_elem.py v17.4).
        second += "        _F(MATRICE=CO('rigi_rot'), OPTION='RIGI_ROTA'),\n"
    second += bridge_modal_damping.assemblage_entry(damping)
    charge_names = list(names_bc) + [n for n in extra if n not in names_bc]
    charge_names += [n for n in rotation if n not in charge_names]
    charge_ref = ""
    if charge_names:
        charge_ref = "    CHARGE=({0},),\n".format(", ".join(charge_names))
    # Met voorspanning: K = RIGI_MECA + RIGI_GEOM (+ RIGI_ROTA), alle met
    # COEF_R 1 (testcases sdll101a "corde a piano": trek verhoogt de
    # frequenties; sdll133a met RIGI_ROTA). Trek geeft een positieve,
    # druk een negatieve RIGI_GEOM (verificatie MP-01, MP-02).
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}{charge}"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('{rigi}'), OPTION='RIGI_MECA'),\n"
        "{second}"
        "    ),\n"
        ")\n").format(cara=cara_elem_ref, charge=charge_ref, second=second,
                      rigi="rigi_ela" if prestress else "rigidite")
    if prestress:
        terms = ["rigi_ela", "rigi_geo"] + (["rigi_rot"] if rotation else [])
        assemblage_block += (
            "# Voorgespannen stijfheid (stress stiffening)\n"
            "rigidite = COMB_MATR_ASSE(COMB_R=(\n{0}))\n").format("".join(
                "    _F(MATR_ASSE={0}, COEF_R=1.0),\n".format(m)
                for m in terms))
    assemblage_block += bridge_modal_damping.damping_block(damping)
    calc_modes_block = _calc_modes_block(model_data, analysis, buckling,
                                         cara_elem_ref, free=not names_bc,
                                         damped=bool(damping))
    stress_block = ""
    if len(fields) > 1:
        # Spanningen per mode: CALC_CHAMP op het modale resultaat, zoals
        # statisch (SIGM_ELNO/SIGM_NOEU/SIEQ_*, schalen via POST_CHAMP
        # EXTR_COQUE, balken SIPM_ELNO), zonder REAC_NODA (geen evenwicht
        # bij een mode). Ook voor modes zijn de spanningen lineair in de
        # vorm (sigma = D B phi).
        stress_block = ("# Spanningen per trillingsvorm (instelling fields "
                        "van modal_3d)\n" + _build_calc_champ_block(
                            model_data, reactions=False) + "\n")
    export_block = (stress_block + _custom_code(model_data, 'post') +
                    _modes_export_block(
                        work_dir, model_data, buckling and _mode_norm(
                            analysis, buckling, quiet=True) == "RIGI_GENE",
                        fields=fields, mass=not buckling,
                        complex_modes=bool(damping)))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL',)))\n")
    else:
        impr_resu_block = "#-- geen MED-export (instelling med_export uit) --\n"

    try:
        template_content = _read_template(analysis["template"])
        _write_comm(comm_path, template_content.format(
            defigroup_block  = defigroup_block,
            model_block      = model_block,
            cara_elem_block  = cara_elem_block,
            materials_block  = materials_block,
            fieldmat_block   = fieldmat_block,
            loads_block      = loads_block,
            static_block     = static_block,
            assemblage_block = assemblage_block,
            calc_modes_block = calc_modes_block,
            export_block     = export_block,
            impr_resu_block  = impr_resu_block,
        ))
        log("SUCCESS: .comm geschreven naar '{0}'.".format(comm_path))

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
            time_limit   = analysis.get("time_limit",   900),
            memory_limit = analysis.get("memory_limit", 2048),
            ncpus    = CONFIG_BRIDGE["ncpus"],
            comm     = comm_path,
            msh      = msh_path,
            mess     = os.path.join(work_dir, run_name(".mess")),
        ) + _export_result_lines(work_dir, resu_name)
        with open(export_path, 'w') as f:
            f.write(export_content)
        log("SUCCESS: .export geschreven naar '{0}'.".format(export_path))
        return export_path

    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}. "
               "Controleer de .comm-template op {{placeholder}}-namen.",
               "ERROR: Template placeholder missing: {0}. "
               "Check the .comm template for {{placeholder}} names.")
            .format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren solver-bestanden mislukt: {0}",
               "ERROR: Generating solver files failed: {0}").format(str(e)))
    return None


# ==========================================
# SOLVER-BUILDERS REGISTRY
#
# Nieuw analysetype toevoegen:
#   1. Schrijf _build_<analyse>() in dit bestand (zelfde signatuur als
#      _build_lin_static).
#   2. Voeg entry toe aan SOLVER_BUILDERS_ASTER hieronder.
#   3. Plaats de template AsterTemplate_<naam>.comm in Scripts/.
#   4. Voeg analyse-config toe aan CONFIG_BRIDGE["analyses"] in bridge_utils.py
#      (met "solver_command" en de bestandsnaam in "template").
# ==========================================
def _build_thermal(work_dir, model_data, msh_path, resu_name, analysis):
    """Thermisch (THER_LINEAIRE / THER_NON_LINE): zie bridge_thermal.py.
    Import hier, want bridge_thermal gebruikt hulpfuncties uit deze module."""
    import bridge_thermal
    return bridge_thermal.build_thermal(work_dir, model_data, msh_path,
                                        resu_name, analysis)


def _build_dyna_modal(work_dir, model_data, msh_path, resu_name, analysis):
    """Respons op modale basis (DYNA_VIBRA GENE): zie bridge_dyna_modal.py.
    Import hier, want die module gebruikt hulpfuncties uit deze module.
    Akoestisch (analysis "phenomene" 'ACOUSTIQUE', acoustic_harm_3d):
    harmonisch drukveld in bridge_acoustic.build_acoustic_harm."""
    import bridge_acoustic
    if bridge_acoustic.is_acoustic(analysis):
        return bridge_acoustic.build_acoustic_harm(
            work_dir, model_data, msh_path, resu_name, analysis)
    import bridge_vibroacoustic_harm
    if bridge_vibroacoustic_harm.is_vibro_harm(analysis):
        # Vibro-akoestiek harmonisch (vibroacoustic_harm_3d)
        return bridge_vibroacoustic_harm.build_vibroacoustic_harm(
            work_dir, model_data, msh_path, resu_name, analysis)
    if str(analysis.get("type_calcul", "")).upper() == "HARM":
        # Harmonische respons van de constructie (harmonic_3d)
        import bridge_harmonic
        return bridge_harmonic.build_harmonic(work_dir, model_data, msh_path,
                                              resu_name, analysis)
    import bridge_dyna_modal
    return bridge_dyna_modal.build_dyna_modal(work_dir, model_data, msh_path,
                                              resu_name, analysis)


def _build_spectrum(work_dir, model_data, msh_path, resu_name, analysis):
    """Responsspectrum (COMB_SISM_MODAL): zie bridge_spectrum.py. Import
    hier, want die module gebruikt hulpfuncties uit deze module."""
    import bridge_spectrum
    return bridge_spectrum.build_spectrum(work_dir, model_data, msh_path,
                                          resu_name, analysis)


SOLVER_BUILDERS_ASTER = {
    "MECA_STATIQUE": _build_lin_static,
    "STAT_NON_LINE": _build_nonlin_static,
    # Zelfde builder: materialen, lasten en postprocessing zijn gelijk;
    # tijdsdiscretisatie, SCHEMA_TEMPS en ETAT_INIT verschillen.
    "DYNA_NON_LINE": _build_nonlin_static,
    # Thermisch: de builder kiest zelf THER_LINEAIRE of THER_NON_LINE.
    "THER_LINEAIRE": _build_thermal,
    "THER_NON_LINE": _build_thermal,
    # Modaal (V30) en lineaire knik (B30): de builder kiest met
    # analysis["type_resu"] ('DYNAMIQUE' of 'MODE_FLAMB'); akoestische
    # holtemodes (analysis["phenomene"] 'ACOUSTIQUE', A30) gaan door naar
    # bridge_acoustic.build_acoustic_modes.
    "CALC_MODES":    _build_modal,
    # Respons op modale basis (Mecway D30 met mode superposition):
    # CALC_MODES -> PROJ_BASE -> DYNA_VIBRA GENE -> REST_GENE_PHYS.
    # Akoestisch harmonisch (acoustic_harm_3d): bridge_acoustic.
    # Harmonische respons (harmonic_3d, type_calcul 'HARM'):
    # bridge_harmonic.
    "DYNA_VIBRA":    _build_dyna_modal,
    # Responsspectrum: CALC_MODES -> COMB_SISM_MODAL (bridge_spectrum.py).
    "COMB_SISM_MODAL": _build_spectrum,
}


# ==========================================
# PUBLIEKE DISPATCHER
# ==========================================
def generate_AsterSolver_files(work_dir, model_data, msh_path, resu_name):
    """
    Dispatcher: kies de builder voor study.comm/study.export op basis van
    "solver_command" van de actieve analyse (get_active_analysis():
    CONFIG_BRIDGE["analyses"][CONFIG_BRIDGE["active_analysis"]]).

    Returns
    -------
    str of None - Pad naar study.export bij succes, anders None.
    """
    try:
        analysis = get_active_analysis()
    except KeyError as e:
        log("ERROR: {0}".format(str(e)))
        return None

    # #ASTER-OPTIE: instellingen voor dit model (alleen in het geheugen)
    analysis = bridge_custom.apply_options(
        analysis, model_data.get("aster_custom", {}).get("options", {}))

    solver_cmd = analysis.get("solver_command")
    builder    = SOLVER_BUILDERS_ASTER.get(solver_cmd)
    # Thermisch en akoestisch: geen mechanische voorbereiding (LINE_QUAD,
    # materiaalcontrole E/rho, balklasten); eigen materialen in
    # bridge_thermal / bridge_acoustic.
    import bridge_acoustic
    mechanical = not (str(solver_cmd or "").startswith("THER") or
                      bridge_acoustic.is_acoustic(analysis))
    if analysis.get("error_estimator") and solver_cmd != "MECA_STATIQUE":
        # Foutschatter alleen lineair statisch (docs/Foutschatter.md: bij
        # STAT_NON_LINE grote vervormingen/plasticiteit en lasten in de tijd,
        # thermisch ERTH niet gebouwd).
        log(tr("WARNING: Foutschatter (error_estimator) werkt alleen bij "
               "lineair statisch (MECA_STATIQUE), niet bij {0}; geen "
               "foutschatting.",
               "WARNING: Error estimator (error_estimator) only works for "
               "linear static (MECA_STATIQUE), not for {0}; no error "
               "estimate.").format(solver_cmd))
    if bridge_fracture.is_requested(model_data) and             solver_cmd != "MECA_STATIQUE":
        # Breukmechanica alleen lineair statisch (docs/Breukmechanica.md)
        log(tr("WARNING: Breukmechanica (SCHEUR_-selecties) werkt alleen "
               "bij lineair statisch (MECA_STATIQUE), niet bij {0}; geen K "
               "en G.",
               "WARNING: Fracture mechanics (CRACK_ selections) only works "
               "for linear static (MECA_STATIQUE), not for {0}; no K and "
               "G.").format(solver_cmd))
    if bridge_xfem.is_requested(model_data) and             solver_cmd != "MECA_STATIQUE":
        # XFEM alleen lineair statisch (docs/Breukmechanica.md par. 7)
        log(tr("WARNING: XFEM (#ASTER-XFEM, XFEM_-selecties) werkt alleen "
               "bij lineair statisch (MECA_STATIQUE), niet bij {0}; de "
               "scheur wordt genegeerd.",
               "WARNING: XFEM (#ASTER-XFEM, XFEM_ selections) only works "
               "for linear static (MECA_STATIQUE), not for {0}; the crack "
               "is ignored.").format(
                   solver_cmd))
    # Vermoeiing alleen statisch en DYNA_NON_LINE (bridge_fatigue)
    bridge_fatigue.unsupported_warning(model_data, solver_cmd)
    if mechanical:
        _resolve_line_quad(model_data)
        if model_data.get("aster_custom", {}).get("welding"):
            # bridge_welding.py: alleen in ther_3d (bridge_thermal)
            log(tr("WARNING: #ASTER-LASBRON werkt alleen in een transiente "
                   "thermische analyse (Mecway T31, ther_3d); hier genegeerd.",
                   "WARNING: #ASTER-LASBRON only works in a transient "
                   "thermal analysis (Mecway T31, ther_3d); ignored here."))
        if model_data.get("aster_custom", {}).get("metallurgy"):
            # bridge_metallurgy.py: alleen in ther_3d (bridge_thermal)
            log(tr("WARNING: #ASTER-METALLURGIE werkt alleen in een "
                   "transiente thermische analyse (Mecway T31, ther_3d); "
                   "hier genegeerd.",
                   "WARNING: #ASTER-METALLURGY only works in a transient "
                   "thermal analysis (Mecway T31, ther_3d); ignored here."))
        if model_data.get("aster_custom", {}).get("materials"):
            # bridge_thermomech.py: alleen in de keten thermisch -> mechanisch
            log(tr("WARNING: #ASTER-MATERIAAL werkt alleen in de keten "
                   "thermisch -> mechanisch (Mecway T31 met Thermal stress); "
                   "hier genegeerd.",
                   "WARNING: #ASTER-MATERIAL only works in the thermal -> "
                   "mechanical chain (Mecway T31 with Thermal stress); "
                   "ignored here."))
    if builder is None:
        log(tr("ERROR: Geen builder geregistreerd voor "
               "solver_command='{0}'. Beschikbaar: {1}.",
               "ERROR: No builder registered for solver_command='{0}'. "
               "Available: {1}.").format(
                solver_cmd, list(SOLVER_BUILDERS_ASTER.keys())))
        return None

    if mechanical:
        if not _check_materials(model_data, analysis):
            return None
        # Een verdeelde last per balk (BRLP-groepen vóór DEFI_GROUP)
        _prepare_beam_loads(model_data, solver_cmd)

    # Gap-groepen (DEFI_GROUP, DEFI_MATERIAU) vóór de blokken
    _prepare_gaps(model_data)
    return builder(work_dir, model_data, msh_path, resu_name, analysis)


def _check_materials(model_data, analysis):
    """
    Elke elset in AFFE_MODELE (behalve veren/gaps/dempers, DIS_*) moet een
    vertaald materiaal hebben. Zonder materiaal stopt Code-Aster met
    <EXCEPTION> CALCUL_20 zonder aanwijzing welke elset (QA-run); zonder
    enig materiaal zou _build_fieldmat_block een leeg materiaal (E = 1)
    toewijzen. ERROR en stoppen.
    Impliciete dynamica: een elset zonder dichtheid geeft een singuliere
    massamatrix (MECANONLINE_78 mogelijk): WARNING.
    """
    materials = model_data.get("materials", {})
    elsets = model_data.get("elsets", {})
    bad, no_rho = [], []
    for elset, mod in model_data.get("elset_modelisations", {}).items():
        if mod.startswith("DIS_"):
            continue
        mat = elsets.get(elset)
        if not mat:
            bad.append(tr("'{0}' (geen materiaal toegewezen)",
                          "'{0}' (no material assigned)").format(elset))
        elif mat not in materials:
            bad.append(tr("'{0}' (materiaal '{1}' ontbreekt of is niet "
                          "vertaald)",
                          "'{0}' (material '{1}' is missing or not "
                          "translated)").format(elset, mat))
        elif not materials[mat].get("rho"):
            no_rho.append(elset)
    if bad:
        log(tr("ERROR: Elset(s) zonder bruikbaar materiaal: {0}. Wijs in "
               "Mecway een (isotroop) materiaal toe.",
               "ERROR: Elset(s) without a usable material: {0}. Assign an "
               "(isotropic) material in Mecway.").format(", ".join(bad)))
        return False
    if no_rho and ((analysis.get("solver_command") == "CALC_MODES"
                    and analysis.get("type_resu", "DYNAMIQUE") == "DYNAMIQUE")
                   or analysis.get("solver_command") in (
                       "DYNA_VIBRA", "COMB_SISM_MODAL")):
        # Zonder dichtheid geen massa: de massamatrix is (deels) nul en
        # die vrijheidsgraden geven geen (of oneindige) frequenties.
        log(tr("WARNING: Modaal: elset(s) {0} hebben geen dichtheid en dus "
               "geen massa; geef het materiaal in Mecway een dichtheid.",
               "WARNING: Modal: elset(s) {0} have no density and hence no "
               "mass; give the material a density in Mecway.").format(
                   ", ".join(no_rho)))
    if (no_rho and analysis.get("solver_command") == "DYNA_NON_LINE"
            and analysis.get("schema") not in ("DIFF_CENT", "TCHAMWA")):
        log(tr("WARNING: Dynamica: elset(s) {0} hebben geen dichtheid; de "
               "massamatrix is dan (deels) singulier: Code-Aster meldt "
               "MECANONLINE_78 (beginversnelling onbetrouwbaar) of stopt. "
               "Geef het materiaal in Mecway een dichtheid.",
               "WARNING: Dynamics: elset(s) {0} have no density; the mass "
               "matrix is then (partly) singular: Code-Aster reports "
               "MECANONLINE_78 (initial acceleration unreliable) or stops. "
               "Give the material a density in Mecway.").format(
                   ", ".join(no_rho)))
    return True
