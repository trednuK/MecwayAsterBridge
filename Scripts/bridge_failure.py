# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_failure.py
# Verantwoordelijkheid: bezwijken van elementen in STAT_NON_LINE en
# DYNA_NON_LINE ("impliciete elementverwijdering"): een element waarvan de
# plastische rek een grens haalt, krijgt een zeer slap materiaal en zijn
# spanning wordt nul. Code-Aster kent zelf geen elementverwijdering (KNOWN_BUGS 9);
# dit volgt de aanpak uit de literatuur waarin bezweken elementen in een
# impliciete berekening een verwaarloosbare stijfheid krijgen in plaats
# van te verdwijnen (bijv. PMC9821832).
#
# Werking in de .comm (build_solve_block):
#   0. Een regel BRIDGE_TEND <eindtijd> in de .mess (convergentiescherm:
#      voortgang over de hele lus, bridge_convergence).
#   1. STAT_NON_LINE per tijdstap van 'times' (INST_INIT/INST_FIN, met
#      reuse=res: een resultaat met alle stappen).
#   2. Na elke stap per elset de vergelijkingsplastische rek uit VARI_ELGA,
#      gemiddeld over de integratiepunten van een element. Gemiddelde >=
#      grens: element bezwijkt.
#      - isotroop (VMIS_ISOT_LINE/_TRAC): V1 = EPSPEQ (catalogus
#        Behaviours/vmis_isot_*.py), de opgetelde plastische rek;
#      - kinematisch (VMIS_CINE_LINE): geen EPSPEQ; V1..V6 = XCINXX..XCINYZ,
#        de terugspanning X (catalogus vmis_cine_line.py). X = c epsp met
#        c = 2/3 E Et / (E - Et) (Et = D_SIGM_EPSI): in een testrun (hex8,
#        PETIT) was X / EPSP_ELGA in alle punten 3,34128878e8, gelijk aan
#        die c, voor de normaal- en de schuifcomponenten (dus dezelfde
#        tensorconventie). De rek is sqrt(2/3 X:X) / c: de HUIDIGE
#        plastische rek, niet opgeteld (bij wisselende belasting kleiner
#        dan EPSPEQ; WARNING). Met GDEF_LOG (logaritmische rek) dezelfde
#        variabelen V1..V6 (gezien in de .mess); de waarden lagen iets
#        onder die met PETIT (0,076..0,078 tegen 0,079..0,080 bij t = 1 s
#        in de trekstaaf), zoals ln(1 + e) < e.
#      Schalen (DKT, COQUE_3D): VARI_ELGA heeft subpunten over de dikte
#      (COQUE_NCOU lagen, per laag onder/midden/boven; getValuesWithDescription
#      geeft cellen, componenten, punten en subpunten, gezien in een
#      testrun). Het gemiddelde loopt over alle (punt, subpunt)-paren van
#      het element, net als bij volume-elementen over alle Gauss-punten
#      (ook over de dikte): een maat voor de rek in het hele element. Bij
#      buiging bezwijkt het element dus pas als de rek gemiddeld over de
#      dikte de grens haalt (oppervlak dan boven de grens), niet bij de
#      eerste vezel (maximum) en niet pas als de neutrale lijn vloeit
#      (minimum, die haalt de grens bij zuivere buiging nooit). Met de
#      standaard COQUE_NCOU = 1 zijn er 3 subpunten (gezien in een
#      testrun: 4 Gauss-punten x 3 subpunten per quad4-DKT).
#   3. Bij nieuwe bezweken elementen:
#      - groep BZ<n>_<k> met alle bezweken cellen van elset k
#        (mesh.setGroupOfCells), in een nieuwe AFFE_MATERIAU het zwakke
#        materiaal: E en helling na vloeien x failure_stiffness_factor,
#        vloeigrens ongewijzigd (zo blijft het element elastisch; een slap
#        element dat verder vloeit had een raaklijnstijfheid van ~1e-9 x E
#        en de matrix werd singulier, gezien in een testrun);
#      - spanning (SIEF_ELGA) en interne variabelen op nul (CREA_CHAMP ASSE,
#        GROUP_MA; zet ook alle subpunten van schalen op nul, gezien in een
#        testrun). Bij isotrope versteviging blijft V1 staan (de
#        plastische rek in de resultaten). Bij GDEF_LOG staat de spanning
#        ook in de interne variabelen (TXX..TYZ: V3..V8 isotroop, V8..V13
#        kinematisch, gezien in de .mess); alleen SIEF_ELGA op nul gaf
#        <IntegrationError> MECANONLINE9_3. Bij SIMO_MIEHE zijn V3..V8
#        SM1..SM6 (catalogus simo_miehe.py; welke tensor precies is NIET
#        geverifieerd, in de theorie van Simo-Miehe de elastische
#        Cauchy-Green-tensor): nul is de spanningsloze begintoestand (elke
#        run zonder ETAT_INIT start met VARI = 0, "On prend un état initial
#        nul" in de .mess; tijdens het vloeien waren de waarden ~1e-3, dus
#        een afwijking van de eenheidstensor en niet de tensor zelf,
#        testrun). Op nul zetten = terug naar spanningsloos, zoals gewenst;
#      - de volgende stap start uit die velden (ETAT_INIT DEPL/SIGM/VARI)
#        met NEWTON PREDICTION='ELASTIQUE'. Met de standaard 'TANGENTE'
#        convergeerde de stap na het bezwijken niet (residu bleef ~13 kN,
#        op alle deelniveaus); met 'ELASTIQUE' wel (testruns, Code-Aster
#        17.4). Daarna weer 'TANGENTE' ('ELASTIQUE' vanaf het begin gaf bij
#        GDEF_LOG 148 deelstappen in de eerste stap).
#   4. Elke gebeurtenis komt als BRIDGE_BEZWIJKEN-regel in de .mess
#      (bridge_run_aster.failure_events leest ze).
#
# Grens per materiaal (_criterion), eerste die bestaat:
#   #ASTER-BEZWIJKEN <materiaal> = <rek>   (bridge_custom; '*' = alle
#                                           plastische materialen)
#   OpenRadioss PLAS_TAB Eps_p_max         (bridge_radioss)
#   instelling failure_plastic_strain > 0  (alle plastische materialen)
#
# Dynamica (DYNA_NON_LINE): dezelfde lus, gecontroleerd op de
# uitvoertijden (outlist; die zijn ook rekenstappen, bridge_to_aster.
# _build_dyna_listinst_block). Na een bezwijkmoment ook VITE en ACCE in
# ETAT_INIT. Expliciet blijft PREDICTION 'TANGENTE' (MECANONLINE5_1). Impliciet (HHT/NEWMARK)
# geeft Code-Aster bij SIGM in ETAT_INIT het alarm MECANONLINE4_50 ("de
# beginversnelling wordt zonder dit spanningsveld berekend"); de bridge geeft
# ACCE mee. Of dat de herberekening voorkomt is NIET geverifieerd; het
# krachtverloop in de testrun was fysisch plausibel (val naar ~0, naslingering).
#
# Beperkingen (met een melding): alleen volume-elementen en schalen
# (_SUPPORTED_DEFORMATIONS); balken niet: Code-Aster kent plasticiteit
# alleen in multivezelbalken (POU_D_EM/POU_D_TGM; <EXCEPTION> POUTRE0_61
# met VMIS_ISOT_LINE op POU_D_E, testrun), die de bridge niet maakt.
# Kinematische versteviging zonder helling (Et = 0: X blijft 0, geen maat
# voor de plastische rek). Alleen STAT_NON_LINE en DYNA_NON_LINE
# (MECA_STATIQUE: alleen de melding, bridge_to_aster._build_lin_static).
#
# Meldingen tonen de Mecway-naam van een elset (mecway_name); de .comm en
# de BRIDGE_BEZWIJKEN-regels gebruiken de Code-Aster-naam.
#
# Compatibel met IronPython 2.7.9.

import io
import re
from collections import OrderedDict

from bridge_utils import log, tr, log_file_name

# Per MODELISATION de DEFORMATION-vormen waarvoor het bezwijken met een
# Code-Aster-run gecontroleerd is (krachtval na het bezwijken). DKT/COQUE_3D
# met VMIS_ISOT_LINE: 2 interne variabelen, ook met GREEN_LAGRANGE/GROT_GDEP
# (gezien in de .mess). DST wordt in niet-lineaire analyses DKT
# (bridge_from_liml).
_SUPPORTED_DEFORMATIONS = {
    "3D": ("PETIT", "PETIT_REAC", "GDEF_LOG", "SIMO_MIEHE"),
    "3D_SI": ("PETIT", "PETIT_REAC", "GDEF_LOG", "SIMO_MIEHE"),
    "DKT": ("PETIT", "GREEN_LAGRANGE"),
    "COQUE_3D": ("PETIT", "GROT_GDEP"),
}
_ISOTROPIC = ("VMIS_ISOT_LINE", "VMIS_ISOT_TRAC")
_KINEMATIC = "VMIS_CINE_LINE"


def _cine_coefficient(props):
    """c in X = c epsp voor VMIS_CINE_LINE: 2/3 E Et / (E - Et) met Et de
    helling na vloeien (ECRO_LINE D_SIGM_EPSI); zie de kop. None als er
    geen versteviging is (Et <= 0 of Et >= E)."""
    try:
        e_mod = float(props["E"])
        e_t = float(props["plastic_bilinear"]["et"])
    except (KeyError, TypeError, ValueError):
        return None
    if e_t <= 0.0 or e_t >= e_mod:
        return None
    return 2.0 / 3.0 * e_mod * e_t / (e_mod - e_t)


def _is_plastic(props):
    """Heeft het materiaal plasticiteit (en dus een plastische rek)?"""
    return bool(props.get("plastic_curve") or props.get("plastic_bilinear")
                or props.get("eps_p_max"))


def _criterion(mat_name, props, custom, default):
    """(grens, bron) voor een materiaal, of (None, None). '*' en
    failure_plastic_strain gelden alleen voor plastische materialen (een
    elastisch materiaal of een veer kan niet bezwijken; met '*' gaf dat
    per elastische elset een onterechte WARNING). Een materiaal dat bij
    naam in #ASTER-BEZWIJKEN staat, gaat altijd door (failure_plan meldt
    het als het niet plastisch is)."""
    if mat_name in custom:
        return custom[mat_name], "#ASTER-BEZWIJKEN"
    if not _is_plastic(props):
        return None, None
    if "*" in custom:
        return custom["*"], "#ASTER-BEZWIJKEN *"
    if props.get("eps_p_max"):
        return props["eps_p_max"], "PLAS_TAB Eps_p_max"
    if default and default > 0.0:
        return default, "failure_plastic_strain"
    return None, None


def mecway_name(model_data, group):
    """Mecway-naam van een Code-Aster-groep (bridge_mesh hernoemt:
    model_data["group_renames"] = {Mecway-naam: Code-Aster-naam});
    onbekend: ongewijzigd."""
    for src, dst in model_data.get("group_renames", {}).items():
        if dst == group:
            return src
    return group


def failure_plan(model_data, analysis, relation_for, deformation_for):
    """
    Welke elsets kunnen bezwijken? Lijst van dicts
    {"elset", "material", "limit", "relation", "deformation"}; leeg als er
    niets te doen is. Wat niet kan, wordt gemeld (WARNING) en komt in
    skipped_loads.

    relation_for(mat_name) en deformation_for(mod, relation, chosen,
    elset) komen uit bridge_to_aster (geen kringimport).
    """
    custom = model_data.get("aster_custom", {}).get("failure", {})
    default = float(analysis.get("failure_plastic_strain", 0.0) or 0.0)
    materials = model_data["materials"]
    for name in custom:
        if name != "*" and name not in materials:
            log(tr("ERROR: #ASTER-BEZWIJKEN: materiaal '{0}' bestaat niet "
                   "in het model; genegeerd. Bekend: {1}",
                   "ERROR: #ASTER-BEZWIJKEN: material '{0}' does not exist "
                   "in the model; ignored. Known: {1}").format(
                       name, ", ".join(materials)))
    wanted = OrderedDict()
    label = dict((g, mecway_name(model_data, g))
                 for g in model_data["elsets"])
    for elset, mat_name in model_data["elsets"].items():
        limit, source = _criterion(mat_name, materials.get(mat_name, {}),
                                   custom, default)
        if limit is not None:
            wanted[elset] = (mat_name, limit, source)
    if not wanted:
        return []
    skipped = model_data.setdefault("skipped_loads", [])
    if not analysis.get("element_failure", True):
        log(tr("WARNING: Bezwijkgrenzen in het model ({0}), maar "
               "'Bezwijken van elementen' staat uit: elementen bezwijken "
               "niet.",
               "WARNING: Failure limits in the model ({0}), but 'Element "
               "failure' is off: elements do not fail.").format(
                   ", ".join(label[g] for g in wanted)))
        skipped.append(tr("bezwijken van elementen (instelling uit)",
                          "element failure (setting off)"))
        return []
    if analysis.get("solver_command", "STAT_NON_LINE") not in (
            "STAT_NON_LINE", "DYNA_NON_LINE"):
        log(tr("WARNING: Bezwijken van elementen kan de bridge alleen in "
               "niet-lineaire analyses (STAT_NON_LINE, DYNA_NON_LINE); in "
               "deze analyse bezwijken {0} niet.",
               "WARNING: The bridge supports element failure only in "
               "nonlinear analyses (STAT_NON_LINE, DYNA_NON_LINE); in "
               "this analysis {0} do not fail.").format(
                   ", ".join(label[g] for g in wanted)))
        skipped.append(tr("bezwijken van {0} (alleen niet-lineair)",
                          "failure of {0} (nonlinear only)")
                       .format(", ".join(label[g] for g in wanted)))
        return []
    chosen = analysis.get("deformation", "PETIT")
    mods = model_data.get("elset_modelisations", {})
    plan = []
    for elset, (mat_name, limit, source) in wanted.items():
        relation = relation_for(mat_name)
        mod = mods.get(elset, "")
        reason = None
        coef = None
        if relation == _KINEMATIC:
            coef = _cine_coefficient(materials.get(mat_name, {}))
            if coef is None:
                reason = tr("kinematische versteviging zonder helling na "
                            "vloeien (tangent modulus 0): de terugspanning "
                            "blijft 0 en geeft geen maat voor de plastische "
                            "rek; geef een tangent modulus > 0 of kies "
                            "isotrope versteviging",
                            "kinematic hardening without a slope after "
                            "yield (tangent modulus 0): the back stress "
                            "stays 0 and gives no measure of the plastic "
                            "strain; give a tangent modulus > 0 or choose "
                            "isotropic hardening")
        elif relation not in _ISOTROPIC:
            reason = tr("het materiaal is niet plastisch (geen plastische "
                        "rek)",
                        "the material is not plastic (no plastic strain)")
        if reason is None and mod.startswith("POU_D"):
            # <EXCEPTION> POUTRE0_61 met VMIS_ISOT_LINE op POU_D_E (testrun)
            reason = tr("balken ({0}) niet: Code-Aster kent plasticiteit "
                        "alleen in multivezelbalken, die de bridge niet "
                        "maakt",
                        "beams ({0}) not: Code-Aster supports plasticity "
                        "only in multifiber beams, which the bridge does "
                        "not create").format(mod)
        elif reason is None and mod not in _SUPPORTED_DEFORMATIONS:
            reason = tr("alleen volume-elementen en schalen ({0} niet)",
                        "solid and shell elements only ({0} not)").format(
                            mod or "?")
        deformation = None
        if reason is None:
            deformation = deformation_for(mod, relation, chosen, elset)
            if deformation not in _SUPPORTED_DEFORMATIONS[mod]:
                reason = tr("DEFORMATION={0} niet ondersteund bij {1} (wel "
                            "{2})",
                            "DEFORMATION={0} not supported with {1} ({2} "
                            "are)").format(
                                deformation, mod,
                                ", ".join(_SUPPORTED_DEFORMATIONS[mod]))
        if reason:
            log(tr("WARNING: Elset '{0}' ({1}, grens {2} uit {3}) kan niet "
                   "bezwijken: {4}.",
                   "WARNING: Elset '{0}' ({1}, limit {2} from {3}) cannot "
                   "fail: {4}.").format(label[elset], mat_name, limit,
                                        source, reason))
            skipped.append(tr("bezwijken van elset {0}",
                              "failure of elset {0}").format(label[elset]))
            continue
        log("INFO: Bezwijken: elset '{0}' ({1}) bij een plastische rek van "
            "{2} ({3}).".format(label[elset], mat_name, limit, source))
        if coef is not None:
            log(tr("WARNING: Elset '{0}' ({1}) heeft kinematische "
                   "versteviging: de bezwijkgrens geldt voor de huidige "
                   "plastische rek (uit de terugspanning), niet voor de "
                   "opgetelde. Bij wisselende belasting bezwijkt het "
                   "element later dan met isotrope versteviging.",
                   "WARNING: Elset '{0}' ({1}) has kinematic hardening: "
                   "the failure limit applies to the current plastic "
                   "strain (from the back stress), not the accumulated "
                   "one. Under alternating load the element fails later "
                   "than with isotropic hardening.").format(
                       label[elset], mat_name))
        plan.append({"elset": elset, "material": mat_name, "limit": limit,
                     "relation": relation, "deformation": deformation,
                     "cine_coef": coef})
    return plan


def weak_materials(model_data, plan, factor, concepts, elas_args, curves,
                   mat_comment):
    """
    DEFI_MATERIAU per materiaal in plan: <MAT_n>_BZ. E en de helling na
    vloeien x factor, vloeigrens ongewijzigd: het slappe element blijft
    elastisch. TRACTION: rek / factor en dezelfde spanning, zodat het
    eerste punt (sy / (E factor), sy) bij de nieuwe E past en de helling
    kleiner blijft dan E (U4.43.01 TRACTION).

    elas_args(props, factor) -> tekst voor ELAS=_F(...); curves: {materiaal:
    [(rek, spanning)]} zoals in TRAC_<n>; mat_comment: commentaarregel.
    Returns (tekst, {materiaal: conceptnaam}).
    """
    out = ""
    names = OrderedDict()
    for item in plan:
        mat_name = item["material"]
        if mat_name in names:
            continue
        props = model_data["materials"][mat_name]
        concept = concepts[mat_name] + "_BZ"
        names[mat_name] = concept
        extra = ""
        if mat_name in curves:
            func = concept.replace("MAT_", "TRAC_", 1)
            vale = ",\n          ".join(
                "{0!r}, {1!r}".format(e / factor, s)
                for e, s in curves[mat_name])
            out += ("{0} = DEFI_FONCTION(\n    NOM_PARA='EPSI',\n"
                    "    NOM_RESU='SIGM',\n    VALE=({1}),\n"
                    "    PROL_DROITE='LINEAIRE',\n"
                    "    PROL_GAUCHE='CONSTANT',\n)\n").format(func, vale)
            extra = "    TRACTION=_F(SIGM={0}),\n".format(func)
        else:
            bil = props["plastic_bilinear"]
            extra = "    ECRO_LINE=_F(D_SIGM_EPSI={0!r}, SY={1!r}),\n".format(
                bil["et"] * factor, bil["sy"])
        out += mat_comment(mat_name) + (
            "# bezweken: E x {0!r}, vloeigrens ongewijzigd (blijft "
            "elastisch)\n".format(factor))
        out += "{0} = DEFI_MATERIAU(\n    ELAS=_F({1}),\n{2})\n".format(
            concept, elas_args(props, factor), extra)
    return out, names


def build_solve_block(plan, weak_names, affe_entries, varc, call_args):
    """
    Python-code voor de .comm: de bezwijklus in plaats van een enkele
    STAT_NON_LINE (zie de kop van dit bestand).

    weak_names  : {materiaal: concept} uit weak_materials
    affe_entries: regels "        _F(GROUP_MA=..., MATER=...),\n" van de
                  gewone AFFE_MATERIAU (bridge_to_aster._fieldmat_parts)
    varc        : AFFE_VARC-regels van die AFFE_MATERIAU (of "")
    call_args   : dict met
                  "args"     : argumenten van de solve zonder MODELE,
                               CHAM_MATER, INCREMENT, NEWTON en ETAT_INIT;
                  "newton"   : tekst binnen NEWTON=_F(...);
                  "command"  : STAT_NON_LINE of DYNA_NON_LINE;
                  "segments" : Python-uitdrukking met de tijdstippen waarop
                               bezwijken wordt gecontroleerd (begin incl.);
                  "first"    : Python-uitdrukking met extra argumenten van
                               de eerste aanroep (bijv. de beginsnelheid);
                  "dynamic"  : True: VITE en ACCE in de beginstand na een
                               bezwijkmoment.
    """
    crit = "".join("    ({0!r}, {1!r}, {2}, {3}),\n".format(
        p["elset"], float(p["limit"]), weak_names[p["material"]],
        repr(float(p["cine_coef"])) if p.get("cine_coef") else "None")
        for p in plan)
    varc_args = "".join("        " + line.strip() + "\n"
                        for line in varc.splitlines() if line.strip())
    affe = "".join("    " + line.strip() + "\n"
                   for line in affe_entries)
    return (
        "# --- Bezwijken van elementen (bridge_failure.py) ---\n"
        "# Per tijdstap: elementen met een gemiddelde plastische rek (V1,\n"
        "# of uit de terugspanning X bij VMIS_CINE_LINE) boven de grens\n"
        "# krijgen het slappe materiaal en spanning nul.\n"
        "import numpy as _bz_np\n"
        "# (elset, grens plastische rek, slap materiaal, c): c = None:\n"
        "# isotroop, rek = V1 (EPSPEQ); anders VMIS_CINE_LINE met\n"
        "# X = c epsp (V1..V6), rek = sqrt(2/3 X:X) / c (huidige rek)\n"
        "_bz_crit = [\n"
        "{crit}]\n"
        "_bz_affe = [\n{affe}]\n"
        "_bz_inst = {segments}\n"
        "# eindtijd voor de voortgang in het convergentiescherm\n"
        "print('BRIDGE_TEND %r' % float(_bz_inst[-1]))\n"
        "_bz_failed = {{}}   # elset -> set van cellen (0-based)\n"
        "_bz_fm = fieldmat\n"
        "_bz_extra = {first}\n"
        "_bz_pred = 'TANGENTE'\n"
        "_bz_n = 0\n"
        "try:\n"
        "    for _bz_i in range(1, len(_bz_inst)):\n"
        "        res = {command}(\n"
        "            MODELE=model,\n"
        "            CHAM_MATER=_bz_fm,\n"
        "{args}"
        "            INCREMENT=_F(LIST_INST=listinst,\n"
        "                         INST_INIT=_bz_inst[_bz_i - 1],\n"
        "                         INST_FIN=_bz_inst[_bz_i]),\n"
        "            NEWTON=_F({newton}, PREDICTION=_bz_pred),\n"
        "            **_bz_extra)\n"
        "        _bz_last = res.getLastIndex()\n"
        "        _bz_vari = res.getField('VARI_ELGA', _bz_last)\n"
        "        _bz_new = {{}}\n"
        "        for _bz_g, _bz_lim, _bz_w, _bz_c in _bz_crit:\n"
        "            _v, _d = _bz_vari.getValuesWithDescription(['V1'], [_bz_g])\n"
        "            _v = _bz_np.asarray(_v)\n"
        "            if _bz_c is not None:\n"
        "                _x = [_v] + [_bz_np.asarray(_bz_vari.getValuesWithDescription(\n"
        "                    [_k], [_bz_g])[0]) for _k in ('V2', 'V3', 'V4', 'V5', 'V6')]\n"
        "                _v = _bz_np.sqrt(2.0 / 3.0 * (\n"
        "                    _x[0] ** 2 + _x[1] ** 2 + _x[2] ** 2 +\n"
        "                    2.0 * (_x[3] ** 2 + _x[4] ** 2 + _x[5] ** 2))) / _bz_c\n"
        "            _c = _bz_np.asarray(_d[0])\n"
        "            for _cell in _bz_np.unique(_c):\n"
        "                if (int(_cell) not in _bz_failed.get(_bz_g, ()) and\n"
        "                        _v[_c == _cell].mean() >= _bz_lim):\n"
        "                    _bz_new.setdefault(_bz_g, []).append(int(_cell))\n"
        "        if not _bz_new:\n"
        "            _bz_extra = dict(reuse=res, RESULTAT=res,\n"
        "                             ETAT_INIT=_F(EVOL_NOLI=res))\n"
        "            _bz_pred = 'TANGENTE'\n"
        "            continue\n"
        "        _bz_n += 1\n"
        "        _bz_groups = []\n"
        "        _bz_more = []\n"
        "        _bz_keep = []   # groepen waarin V1 (EPSPEQ) blijft staan\n"
        "        for _k, (_bz_g, _bz_lim, _bz_w, _bz_c) in enumerate(_bz_crit):\n"
        "            _bz_failed.setdefault(_bz_g, set()).update(\n"
        "                _bz_new.get(_bz_g, []))\n"
        "            if _bz_g in _bz_new:\n"
        "                # cellen: Code-Aster-celnummers (0-based); de bridge\n"
        "                # vertaalt ze naar Mecway-elementen (failure_events)\n"
        "                print('BRIDGE_BEZWIJKEN t=%r elset=%s nieuw=%d totaal=%d "
        "cellen=%s' % (\n"
        "                    _bz_inst[_bz_i], _bz_g, len(_bz_new[_bz_g]),\n"
        "                    len(_bz_failed[_bz_g]),\n"
        "                    ','.join(str(c) for c in sorted(_bz_new[_bz_g]))))\n"
        "            if _bz_failed[_bz_g]:\n"
        "                _nm = 'BZ%d_%d' % (_bz_n, _k + 1)\n"
        "                mesh.setGroupOfCells(_nm, sorted(_bz_failed[_bz_g]))\n"
        "                _bz_groups.append(_nm)\n"
        "                _bz_more.append(_F(GROUP_MA=_nm, MATER=_bz_w))\n"
        "                if _bz_c is None:\n"
        "                    _bz_keep.append(_nm)\n"
        "        _bz_fm = AFFE_MATERIAU(\n"
        "            MAILLAGE=mesh,\n"
        "            MODELE=model,\n"
        "            AFFE=tuple(_bz_affe + _bz_more),\n"
        "{varc})\n"
        "        _bz_sig = res.getField('SIEF_ELGA', _bz_last)\n"
        "        _bz_sig0 = CREA_CHAMP(\n"
        "            OPERATION='ASSE', TYPE_CHAM='ELGA_SIEF_R', MODELE=model,\n"
        "            PROL_ZERO='OUI',\n"
        "            ASSE=(_F(CHAM_GD=_bz_sig, TOUT='OUI'),\n"
        "                  _F(CHAM_GD=_bz_sig, GROUP_MA=tuple(_bz_groups),\n"
        "                     COEF_R=0.0)))\n"
        "        _bz_asse = [_F(CHAM_GD=_bz_vari, TOUT='OUI'),\n"
        "                    _F(CHAM_GD=_bz_vari, GROUP_MA=tuple(_bz_groups),\n"
        "                       COEF_R=0.0)]\n"
        "        if _bz_keep:\n"
        "            _bz_asse.append(_F(CHAM_GD=_bz_vari, GROUP_MA=tuple(_bz_keep),\n"
        "                               NOM_CMP=('V1',)))\n"
        "        _bz_vari0 = CREA_CHAMP(\n"
        "            OPERATION='ASSE', TYPE_CHAM='ELGA_VARI_R', MODELE=model,\n"
        "            PROL_ZERO='OUI', ASSE=tuple(_bz_asse))\n"
        "        _bz_extra = dict(reuse=res, RESULTAT=res, ETAT_INIT=_F(\n"
        "            DEPL=res.getField('DEPL', _bz_last), SIGM=_bz_sig0,\n"
        "{dyn_fields}"
        "            VARI=_bz_vari0))\n"
        "        _bz_pred = '{after_pred}'\n"
        "except Exception as err:\n"
        "    if not str(getattr(err, 'id_message', '')).startswith("
        "'MECANONLINE'):\n"
        "        raise\n"
        "    print('BRIDGE_ONVOLLEDIG', res.getAccessParameters()['INST'][-1])\n"
        "print('BRIDGE_BEZWIJKEN_TOTAAL %d' % sum(len(c) for c in "
        "_bz_failed.values()))\n"
        "t_res = res.getAccessParameters()['INST'][-1]\n"
    ).format(crit=crit, affe=affe, args=call_args["args"],
             newton=call_args["newton"], varc=varc_args,
             command=call_args.get("command", "STAT_NON_LINE"),
             segments=call_args.get("segments",
                                    "list(times.getValues())"),
             first=call_args.get("first", "{}"),
             # Expliciet (DIFF_CENT/TCHAMWA) staat alleen TANGENTE toe
             # (<EXCEPTION> MECANONLINE5_1, gezien met 17.4).
             after_pred=("TANGENTE" if call_args.get("explicit")
                         else "ELASTIQUE"),
             dyn_fields=(
                 "            VITE=res.getField('VITE', _bz_last),\n"
                 "            ACCE=res.getField('ACCE', _bz_last),\n"
                 if call_args.get("dynamic") else ""))


# ==========================================
# NA DE RUN: WELKE ELEMENTEN BEZWEKEN?
# ==========================================
_EVENT_RE = re.compile(r"^BRIDGE_BEZWIJKEN t=(\S+) elset=(\S+) nieuw=(\d+) "
                       r"totaal=(\d+) cellen=([\d,]*)\s*$", re.M)


def failure_events(mess_text, cell_names):
    """
    BRIDGE_BEZWIJKEN-regels uit de .mess: lijst van (tijd, elset,
    [Mecway-elementnummers]). cell_names: model_data["cell_names"]
    (bridge_mesh); een onbekend celnummer blijft '#<nr>'.
    """
    events = []
    for m in _EVENT_RE.finditer(mess_text):
        eids = []
        for c in m.group(5).split(","):
            if not c:
                continue
            c = int(c)
            name = cell_names[c] if 0 <= c < len(cell_names) else None
            # H<eid>: tweede helft van een gesplitste line3-balk (bridge_mesh)
            eid = (name[1:] if name and name[:1] in ("M", "H")
                   else "#{0}".format(c))
            if eid not in eids:
                eids.append(eid)
        events.append((float(m.group(1)), m.group(2), eids))
    return events


def report_failures(mess_path, model_data):
    """
    Log de bezweken elementen van een run (WARNING per gebeurtenis) en geef
    een korte tekst voor mw.message terug ("" zonder bezwijken).
    """
    try:
        f = io.open(mess_path, encoding="utf-8", errors="replace")
        try:
            text = f.read()
        finally:
            f.close()
    except (IOError, OSError):
        return ""
    events = failure_events(text, model_data.get("cell_names", []))
    if not events:
        return ""
    total = 0
    for t, elset, eids in events:
        total += len(eids)
        shown = ", ".join(eids[:50]) + (" ..." if len(eids) > 50 else "")
        log(tr("WARNING: Bezwijken bij t={0}: {1} element(en) van elset "
               "'{2}': {3}",
               "WARNING: Failure at t={0}: {1} element(s) of elset '{2}': "
               "{3}").format("%g s" % t, len(eids),
                             mecway_name(model_data, elset), shown))
    # %g (geen '{:g}': IronPython drukte '{:.4g}' als 0 af, gezien in een
    # IronPython-test)
    when = ("t=%g s" % events[0][0] if events[0][0] == events[-1][0]
            else "t=%g .. %g s" % (events[0][0], events[-1][0]))
    return tr("Bezwijken: {0} element(en) bezweken ({1}); hun spanning is "
              "~0. De elementnummers staan in {2}.",
              "Failure: {0} element(s) failed ({1}); their stress is ~0. "
              "The element numbers are in {2}.").format(
                  total, when, log_file_name())
