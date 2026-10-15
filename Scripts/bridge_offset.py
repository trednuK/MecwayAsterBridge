# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_offset.py
#
# Verantwoordelijkheid: Mecway's Element offset (Loads & Constraints) voor
# schalen en balken naar Code-Aster.
#
#   parse(item, model_data)        <offset> uit de .liml (bridge_from_liml)
#   prepare(model_data, nodes, conn, elements)
#                                  plan: extra knopen, nieuwe connectiviteit,
#                                  starre paren, EXCENTREMENT-groepen
#                                  (bridge_mesh.write_mesh, voor de POI1)
#   apply_to_mesh(plan, ...)       cellen omzetten, groepen in het mesh
#                                  (bridge_mesh.write_mesh, na de namen)
#   coque_groups(model_data, elset) COQUE-entries van AFFE_CARA_ELEM
#                                  (bridge_to_aster._build_cara_elem_block)
#   discretes(plan, model_data)    POI1 (DIS_TR) voor Mecway-knopen zonder
#                                  eigen rotaties (bridge_mesh.write_mesh)
#   link_entries(model_data)       LIAISON_DDL per starre arm
#                                  (bridge_to_aster._build_charges)
#
# MECWAY (manual v34 par. 7.4.3 en 7.5.1; headless gemeten met Mecway 34,
# TestFiles/Tools/mw_solve.py, oktober 2026):
#   <offset selection="elementselectie">
#       <u>0 m</u><v>0 m</v><w>0.105 m</w>      schalen (elementassen)
#   </offset>
#   <offset selection="..."><x>..</x><y>..</y><z>..</z></offset>
#                                                balken (globale assen)
#   In mecway.exe staan de keuzes "Element coordinates (shells)" en "Global
#   coordinates (beams, internal solver)". Gemeten:
#   - schaal: het middenvlak ligt op afstand w in de +W-richting (de
#     elementnormaal, rechtshandig over de knopen). Een strook met w = +10 mm
#     en een trekkracht in de knopen buigt naar +W (tip +7,09 mm, rotatie
#     -0,0713 rad om Y; analytisch P e L^2/(2EI) = 7,14 mm). u en v hebben
#     geen invloed (gelijk aan zonder offset), x/y/z op een schaal ook niet.
#   - balk: de as ligt op (x, y, z) globaal van de knopen; u/v/w op een
#     balk hebben geen invloed. RectBar 10 x 20 mm, 100 N trek, z = 10 mm:
#     tip 0,357 mm (= P e L^2/(2EI)), y = 10 mm: 1,429 mm.
#   - "An offset shell behaves the same as if there were rigid beams
#     connected between the nodes and the shell located at the midsurface"
#     (manual par. 7.4.3). Knoopwaarden (verplaatsing, rotatie, reactie)
#     horen bij de knopen, elementwaarden (spanning, snedekrachten) bij het
#     verschoven element (par. 7.5.1).
#   - Mecway zelf kent de offset alleen in statische analyses (interne
#     solver); de bridge vertaalt hem in elke mechanische analyse.
#
# CODE-ASTER (17.4):
#   1. Schalen DKT/DST: AFFE_CARA_ELEM COQUE EXCENTREMENT = w met
#      INER_ROTA='OUI' (catalogus affe_cara_elem.py: regel
#      PRESENT_PRESENT('EXCENTREMENT', 'INER_ROTA')). Het middenvlak ligt
#      op +EXCENTREMENT langs de normaal van de cel (U4.42.01 par. COQUE);
#      de cel heeft dezelfde knoopvolgorde als Mecway, dus dezelfde normaal
#      (gemeten: zelfde teken als Mecway, LS-60). Testcases met
#      EXCENTREMENT: ssls111a (DST), ssls111b (DKT), sdls124a.
#   2. COQUE_3D (tri6/quad8, of de keuze COQUE_3D) kent geen excentrement:
#      <EXCEPTION> CALCULEL2_31 "un excentrement non nul ... sur un element
#      qui ne sait pas traiter l'excentrement" (gezien op CompositeBeam).
#      POU_D_E/POU_D_T hebben geen offset (catalogus affe_cara_elem.py
#      POUTRE: geen excentriciteit; alleen multivezelbalken kunnen een
#      doorsnede uit het midden leggen). Daarom, zoals de manual het
#      beschrijft: het element komt op eigen knopen op de verschoven plek
#      (knoop + offset) en elk paar (knoop, verschoven knoop) wordt star
#      verbonden met LIAISON_DDL-relaties (link_entries; LIAISON_SOLIDE gaf
#      FACTOR_11 op de drilling-rotatie). Een Mecway-knoop zonder eigen
#      rotaties krijgt een POI1 met DIS_TR (discretes()). MECA_STATIQUE
#      krijgt dan MUMPS POSTTRAITEMENTS='FORCE' (bridge_to_aster
#      _build_lin_solveur_ref). Kleine rotaties (KNOWN_BUGS 108).
#   Knoopgroepen BROFL<k> (een per paar) gebruikt ook aster_results_export:
#   verplaatsingen blijven op de Mecway-knoop, de reactie van de
#   verschoven knoop gaat met het moment van de arm naar de Mecway-knoop en
#   spanningen van het verschoven element worden aan de Mecway-knoop
#   getoond.
#
# Compatibel met IronPython 2.7.9 (Mecway scripting engine).

import math
import re
from collections import OrderedDict

from bridge_utils import log, tr, parse_and_convert

TAG = "offset"
LINK_PREFIX = "BROFL"      # knoopgroep per star paar (ook aster_results_export)
EXC_PREFIX = "BROFE"       # cellen met EXCENTREMENT
REST_PREFIX = "BROFR"      # rest van een elset zonder offset

_SHELLS = frozenset(["tri3", "tri6", "quad4", "quad8"])
_BEAMS = frozenset(["line2"])
_EXC_MODELISATIONS = ("DKT", "DST")
_NUMBER = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*"
                     r"[^\s\d()*+/^-]*\s*$")

# Natuurlijke coordinaten van de knopen in Code-Aster-volgorde
# (bridge_mesh._ASTER_TYPES: hoeken, dan middens).
_NAT = {
    "TRIA3": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
    "TRIA6": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.5, 0.0), (0.5, 0.5),
              (0.0, 0.5)],
    "QUAD4": [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)],
    "QUAD8": [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0),
              (0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)],
}


# ==========================================
# INLEZEN
# ==========================================
def parse(item, model_data):
    """<offset> -> model_data["element_offsets"]."""
    sel = item.get("selection", "")
    comps = {}
    for key in ("u", "v", "w", "x", "y", "z"):
        text = item.findtext(key)
        if text is None:
            continue
        if not _NUMBER.match(text):
            model_data["skipped_loads"].append(
                tr("element offset op '{0}'", "element offset on '{0}'")
                .format(sel))
            log(tr("ERROR: Element offset op '{0}': '{1}' is geen getal "
                   "(formules worden niet vertaald). NIET meegenomen.",
                   "ERROR: Element offset on '{0}': '{1}' is not a number "
                   "(formulas are not translated). NOT included.").format(
                    sel, text))
            return
        comps[key] = parse_and_convert(text, "length")
    uvw = xyz = None
    if any(k in comps for k in "uvw"):
        uvw = tuple(comps.get(k, 0.0) for k in "uvw")
    if any(k in comps for k in "xyz"):
        xyz = tuple(comps.get(k, 0.0) for k in "xyz")
    model_data.setdefault("element_offsets", []).append(
        {"selection": sel, "uvw": uvw, "xyz": xyz})
    log("INFO: Element offset op '{0}': uvw={1}, xyz={2} (m).".format(
        sel, uvw, xyz))


# ==========================================
# MEETKUNDE
# ==========================================
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a):
    n = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    if n == 0.0:
        return None
    return (a[0] / n, a[1] / n, a[2] / n)


def _dshape(atype, xi, eta):
    """Afgeleiden (dN/dxi, dN/deta) per knoop in Code-Aster-volgorde."""
    if atype == "TRIA3":
        return [(-1.0, -1.0), (1.0, 0.0), (0.0, 1.0)]
    if atype == "TRIA6":
        l1, l2, l3 = 1.0 - xi - eta, xi, eta
        return [(-(4.0 * l1 - 1.0), -(4.0 * l1 - 1.0)),
                (4.0 * l2 - 1.0, 0.0), (0.0, 4.0 * l3 - 1.0),
                (4.0 * (l1 - l2), -4.0 * l2), (4.0 * l3, 4.0 * l2),
                (-4.0 * l3, 4.0 * (l1 - l3))]
    out = []
    for xi_i, eta_i in _NAT[atype]:
        if atype == "QUAD4":
            out.append((0.25 * xi_i * (1.0 + eta * eta_i),
                        0.25 * eta_i * (1.0 + xi * xi_i)))
        elif xi_i != 0.0 and eta_i != 0.0:          # hoek QUAD8
            out.append((0.25 * xi_i * (1.0 + eta * eta_i) *
                        (2.0 * xi * xi_i + eta * eta_i),
                        0.25 * eta_i * (1.0 + xi * xi_i) *
                        (xi * xi_i + 2.0 * eta * eta_i)))
        elif xi_i == 0.0:                            # midden, eta = +-1
            out.append((-xi * (1.0 + eta * eta_i),
                        0.5 * eta_i * (1.0 - xi * xi)))
        else:                                        # midden, xi = +-1
            out.append((0.5 * xi_i * (1.0 - eta * eta),
                        -eta * (1.0 + xi * xi_i)))
    return out


def _node_normals(atype, pts):
    """Eenheidsnormaal (W) van een schaalelement in elke knoop; Mecway: de
    W-as staat loodrecht op het oppervlak in elk punt (manual par. 7.4.2),
    rechtshandig over de knopen zoals de normaal van de Code-Aster-cel."""
    out = []
    for xi, eta in _NAT[atype]:
        a, b = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        for (dx, de), p in zip(_dshape(atype, xi, eta), pts):
            for k in range(3):
                a[k] += dx * p[k]
                b[k] += de * p[k]
        out.append(_unit(_cross(a, b)))
    return out


# ==========================================
# MESH: PLAN
# ==========================================
def prepare(model_data, nodes, conn, elements, joint_ends=frozenset()):
    """
    Plan voor bridge_mesh.write_mesh, of None zonder (bruikbare) offset.

    nodes    : {nid: (x, y, z)}
    conn     : {eid: (aster_type, [nid ...])} (Code-Aster-volgorde)
    elements : model_data["mesh_elements"]
    joint_ends: {(eid, nid)} balkuiteinden met een flexible joint
               (bridge_mesh._joint_ends); die zitten aan een eigen knoop en
               dragen de rotaties van de Mecway-knoop niet

    Returns dict:
      new_nodes : [(nid, (x, y, z))] extra knopen (na de Mecway-knopen)
      cells     : {eid: [nid ...]} nieuwe connectiviteit (starre route)
      pairs     : [(Mecway-knoop, extra knoop, arm (m), "shell"/"beam")]
      no_rot    : [nid] Mecway-knopen van een paar zonder rotaties uit een
                  ander element (POI1 DIS_TR, discretes())
      stiff     : {nid: E t^3} van de verschoven schalen in die knoop
      exc       : OrderedDict {(elset, w): [eid]} (EXCENTREMENT)
    """
    offsets = model_data.get("element_offsets") or []
    if not offsets:
        return None
    elem_elset = dict((e[0], e[3]) for e in elements)
    shapes = dict((e[0], e[1]) for e in elements)
    mods = model_data.get("elset_modelisations", {})
    selections = model_data.get("element_selections", {})
    assigned = {}            # eid -> ("exc", w) of ("rigid", [vector])
    ignored = OrderedDict()  # reden -> set(eid)

    def ignore(why, eid):
        ignored.setdefault(why, set()).add(eid)

    for off in offsets:
        sel = off["selection"]
        eids = selections.get(sel)
        if not eids:
            model_data["skipped_loads"].append(
                tr("element offset op '{0}'", "element offset on '{0}'")
                .format(sel))
            log(tr("ERROR: Element offset op '{0}': geen elementselectie "
                   "met die naam (of leeg). NIET meegenomen.",
                   "ERROR: Element offset on '{0}': no element selection "
                   "with that name (or empty). NOT included.").format(sel))
            continue
        for eid in eids:
            if eid not in conn:
                continue
            shape = shapes.get(eid)
            mod = mods.get(elem_elset.get(eid), "")
            if shape in _SHELLS:
                if off["uvw"] is None:
                    ignore("shell_xyz", eid)
                    continue
                u, v, w = off["uvw"]
                if u or v:
                    ignore("shell_uv", eid)
                if not w:
                    continue
                if eid in assigned:
                    ignore("double", eid)
                    continue
                if mod in _EXC_MODELISATIONS:
                    assigned[eid] = ("exc", w)
                else:
                    atype, cn = conn[eid]
                    normals = _node_normals(atype, [nodes[n] for n in cn])
                    if None in normals:
                        ignore("degenerate", eid)
                        continue
                    assigned[eid] = ("shell", (w, normals))
            elif shape in _BEAMS and not mod.startswith("DIS"):
                if off["xyz"] is None:
                    ignore("beam_uvw", eid)
                    continue
                if not any(off["xyz"]):
                    continue
                if eid in assigned:
                    ignore("double", eid)
                    continue
                assigned[eid] = ("beam", off["xyz"])
            else:
                ignore("other", eid)

    _report_ignored(model_data, ignored)
    if not assigned:
        return None
    _report_edge_loads(model_data, assigned)

    # Starre route. Schalen: een extra knoop per (Mecway-knoop, w) op w maal
    # de gemiddelde normaal van de verschoven elementen in die knoop (een
    # doorlopend verschoven vlak; Mecway verschuift per element, bij een
    # gekromde schaal een verschil van de tweede orde). Balken: een extra
    # knoop per (Mecway-knoop, offsetvector).
    normal_sum = {}
    for eid, (kind, data) in assigned.items():
        if kind == "shell":
            w, normals = data
            for nid, n in zip(conn[eid][1], normals):
                acc = normal_sum.setdefault((nid, w), [0.0, 0.0, 0.0])
                for k in range(3):
                    acc[k] += n[k]
    size = max([1.0] + [abs(c) for p in nodes.values() for c in p])
    tol = 1.0e-9 * size
    next_nid = max(nodes) + 1
    by_key = {}
    new_nodes, pairs, cells = [], [], {}
    exc = OrderedDict()
    for eid in sorted(assigned):
        kind, data = assigned[eid]
        if kind == "exc":
            exc.setdefault((elem_elset[eid], data), []).append(eid)
            continue
        atype, cn = conn[eid]
        new_cn = []
        for nid in cn:
            if kind == "shell":
                w = data[0]
                n = _unit(normal_sum[(nid, w)]) or (0.0, 0.0, 1.0)
                d = (w * n[0], w * n[1], w * n[2])
                key = (nid, "w", w)
            else:
                d = data
                key = (nid,) + tuple(int(round(c / tol)) for c in d)
            if key not in by_key:
                p = nodes[nid]
                by_key[key] = next_nid
                new_nodes.append((next_nid, (p[0] + d[0], p[1] + d[1],
                                             p[2] + d[2])))
                pairs.append((nid, next_nid, d, kind))
                next_nid += 1
            new_cn.append(by_key[key])
        cells[eid] = new_cn
    # Mecway-knopen van een paar zonder rotatievrijheidsgraden uit een
    # ander element (alleen nog via de arm, of alleen volumes/veren): POI1
    # met DIS_TR (discretes()).
    rot_nodes = set()
    for eid, (atype, cn) in conn.items():
        mod = mods.get(elem_elset.get(eid), "")
        if eid not in cells and (mod.startswith("POU") or mod in (
                "DKT", "DST", "COQUE_3D", "DIS_TR")):
            rot_nodes.update(n for n in cn if (eid, n) not in joint_ends)
    no_rot = sorted(set(p[0] for p in pairs) - rot_nodes)
    # Buigstijfheid E t^3 van de verschoven schalen per Mecway-knoop: maat
    # voor de veer op de vrije rotatie om de normaal (discretes()).
    stiff = {}
    mats = model_data.get("materials", {})
    for eid, (kind, data) in assigned.items():
        if kind != "shell":
            continue
        elset = elem_elset[eid]
        try:
            e_mod = float(mats[model_data["elsets"][elset]]["E"])
            thick = float(model_data["shell_sections"][elset]["thickness"])
            k = e_mod * thick ** 3
        except (KeyError, TypeError, ValueError):
            k = 0.0
        for nid in conn[eid][1]:
            stiff[nid] = max(stiff.get(nid, 0.0), k)
    for (elset, w), eids in exc.items():
        log("INFO: Element offset: {0} schaalelement(en) van '{1}' met "
            "EXCENTREMENT = {2} m.".format(len(eids), elset, w))
    if cells:
        log("INFO: Element offset: {0} element(en) op eigen knopen op de "
            "verschoven plek, {1} starre armen (LIAISON_DDL), {2} "
            "Mecway-knopen met een POI1 (DIS_TR) voor hun rotaties.".format(
                len(cells), len(pairs), len(no_rot)))
    model_data["offset_new_nids"] = [nid for nid, _xyz in new_nodes]
    return {"new_nodes": new_nodes, "cells": cells, "pairs": pairs,
            "no_rot": no_rot, "stiff": stiff, "exc": exc}


# Belastingen die op een vlakselectie (ook schaalranden) aangrijpen
_EDGE_LOADS = frozenset(["force", "surfacepressure", "traction",
                         "linepressure", "hydrostaticpressure"])


def _report_edge_loads(model_data, assigned):
    """
    WARNING voor een last op randen (faceid 1..4) van verschoven schalen.
    Mecway 34 (headless, oktober 2026, strook als LS-60 met de trekkracht
    als last op het randvlak in plaats van op de knopen): tip w = 4e-16 m,
    dus de last grijpt aan op de verschoven rand (geen moment). De bridge
    zet zo'n last op de randcel op de Mecway-knopen (FORCE_ARETE, ook bij
    EXCENTREMENT): 7,08e-3 m (DKT) en 7,10e-3 m (COQUE_3D), het moment
    w x F per lengte extra (KNOWN_BUGS 108). Een last op de knopen (knoop-
    selectie) grijpt in Mecway wel op de knopen aan (LS-60).
    """
    faces = model_data.get("face_selection_faces", {})
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _EDGE_LOADS or bc.get("skip"):
            continue
        hit = sorted(set(eid for eid, fid in faces.get(bc.get("selection"),
                                                       ())
                         if eid in assigned and assigned[eid][0] in (
                             "exc", "shell") and 1 <= fid <= 4))
        if hit:
            log(tr("WARNING: Last '{0}' op '{1}' grijpt aan op randen van "
                   "schalen met een element offset ({2}): de bridge zet "
                   "hem op de knopen, Mecway op de verschoven rand "
                   "(gemeten); verschil: een moment w x F per lengte "
                   "(KNOWN_BUGS 108). Een last op de knopen (knoopselectie) "
                   "werkt in beide op de knopen.",
                   "WARNING: Load '{0}' on '{1}' acts on edges of shells "
                   "with an element offset ({2}): the bridge applies it at "
                   "the nodes, Mecway at the offset edge (measured); "
                   "difference: a moment w x F per length (KNOWN_BUGS "
                   "108). A load on the nodes (node selection) acts at the "
                   "nodes in both.").format(
                       bc["type"], bc.get("selection"),
                       ", ".join(str(e) for e in hit[:10]) +
                       (" ..." if len(hit) > 10 else "")))


def _report_ignored(model_data, ignored):
    texts = {
        "shell_xyz": tr(
            "WARNING: Element offset in globale coordinaten (x/y/z) op "
            "schaalelementen {0}: Mecway gebruikt dat alleen voor balken "
            "(gemeten: geen effect op schalen). Niet toegepast.",
            "WARNING: Element offset in global coordinates (x/y/z) on "
            "shell elements {0}: Mecway only uses that for beams "
            "(measured: no effect on shells). Not applied."),
        "beam_uvw": tr(
            "WARNING: Element offset in elementcoordinaten (u/v/w) op "
            "balkelementen {0}: Mecway gebruikt voor balken globale "
            "coordinaten (gemeten: u/v/w hebben geen effect). Niet "
            "toegepast; kies in Mecway 'Global coordinates'.",
            "WARNING: Element offset in element coordinates (u/v/w) on "
            "beam elements {0}: Mecway uses global coordinates for beams "
            "(measured: u/v/w have no effect). Not applied; choose "
            "'Global coordinates' in Mecway."),
        "shell_uv": tr(
            "INFO: Element offset op schalen {0}: alleen W (normaal) telt; "
            "u en v hebben ook in Mecway geen effect (gemeten).",
            "INFO: Element offset on shells {0}: only W (normal) counts; "
            "u and v have no effect in Mecway either (measured)."),
        "double": tr(
            "WARNING: Elementen {0} hebben meer dan een element offset; "
            "de eerste geldt (Mecway meldt dit als fout).",
            "WARNING: Elements {0} have more than one element offset; "
            "the first applies (Mecway reports this as an error)."),
        "degenerate": tr(
            "WARNING: Element offset: schaalelementen {0} hebben geen "
            "normaal (ontaard). Niet toegepast.",
            "WARNING: Element offset: shell elements {0} have no normal "
            "(degenerate). Not applied."),
        "other": tr(
            "WARNING: Element offset op elementen {0} die geen schaal of "
            "balk zijn (Mecway: alleen schalen en balken). Niet toegepast.",
            "WARNING: Element offset on elements {0} that are neither "
            "shell nor beam (Mecway: shells and beams only). Not applied."),
    }
    for why, eids in ignored.items():
        ids = sorted(eids)
        shown = ", ".join(str(e) for e in ids[:10]) + (
            " ..." if len(ids) > 10 else "")
        log(texts[why].format(shown))


# ==========================================
# MESH: TOEPASSEN (na de namen)
# ==========================================
def _free_name(prefix, k, taken):
    """Vrije groepsnaam <prefix><k>; de naam gaat meteen in taken, zodat
    een volgende aanroep hem niet nog eens geeft."""
    name = "{0}{1}".format(prefix, k)
    while name in taken:
        k += 1000000
        name = "{0}{1}".format(prefix, k)
    taken.add(name)
    return name


def apply_to_mesh(plan, model_data, by_type, group_ma, group_no, rn_es):
    """Cellen van de starre route op hun nieuwe knopen, knoopgroep per paar,
    EXCENTREMENT- en restgroepen; model_data["offset_links"] en
    ["offset_shells"] voor bridge_to_aster."""
    model_data["offset_links"] = []
    model_data["offset_shells"] = OrderedDict()
    # {eid: "rigid" (eigen knopen) of "exc" (EXCENTREMENT)}, voor de
    # melding bij verlijmd contact (bridge_mesh._bonded)
    model_data["offset_elements"] = {}
    if not plan:
        return
    for eid in plan["cells"]:
        model_data["offset_elements"][eid] = "rigid"
    for eids in plan["exc"].values():
        for eid in eids:
            model_data["offset_elements"][eid] = "exc"
    # Een joint op een verschoven element vertaalt
    # bridge_mesh._flexible_joints niet (WARNING daar, KNOWN_BUGS 108d).
    cells = dict(("M{0}".format(e), cn) for e, cn in plan["cells"].items())
    if cells:
        for atype, items in by_type.items():
            by_type[atype] = [(name, cells.get(name, cn))
                              for name, cn in items]
    taken = set(group_ma) | set(group_no)
    no_rot = set(plan["no_rot"])
    for k, (orig, new, d, kind) in enumerate(plan["pairs"]):
        name = _free_name(LINK_PREFIX, k + 1, taken)
        group_no[name] = ["N{0}".format(orig), "N{0}".format(new)]
        model_data["offset_links"].append(
            {"group": name, "orig": orig, "new": new, "arm": d,
             "kind": kind, "own_rot": orig not in no_rot})
    for k, ((elset, w), eids) in enumerate(plan["exc"].items()):
        group = rn_es(elset)
        members = ["M{0}".format(e) for e in eids]
        name = _free_name(EXC_PREFIX, k + 1, taken)
        group_ma[name] = members
        info = model_data["offset_shells"].setdefault(
            group, {"rest": group, "parts": []})
        info["parts"].append((name, w))
    k_rest = 0      # een restgroep per elset (eigen nummer)
    for group, info in model_data["offset_shells"].items():
        offset_members = set()
        for name, _w in info["parts"]:
            offset_members.update(group_ma[name])
        rest = [m for m in group_ma.get(group, []) if m not in offset_members]
        if not rest:
            info["rest"] = None
        elif len(rest) < len(group_ma.get(group, [])):
            k_rest += 1
            name = _free_name(REST_PREFIX, k_rest, taken)
            group_ma[name] = rest
            info["rest"] = name


def discretes(plan, model_data):
    """
    POI1-discreten (bridge_mesh._build_discretes-formaat: {groep: {"nodes",
    "mod", "cara", "label"}}) voor de Mecway-knopen zonder eigen rotaties
    (plan["no_rot"]): DIS_TR, zodat de arm (u_f = u_o + theta_o x d) hun
    rotaties heeft. Hangt zo'n knoop alleen aan schaalarmen langs dezelfde
    normaal n, dan hangt zijn rotatie om n nergens aan (link_entries koppelt
    die drilling niet): een veer k n n^T op alleen die rotatie (K_TR_N, 21
    waarden, bovendriehoek per kolom zoals K_T_N, catalogus
    affe_cara_elem.py), met k = E t^3 van de schaal (orde van de
    buigstijfheid; de waarde doet er niet toe, de vrijheidsgraad is
    ontkoppeld). Een losse Lagrange-relatie theta . n = 0 botste met een
    inklemming op dezelfde knoop (<EXCEPTION> ASSEMBLA_26, "bloque
    plusieurs fois"). Andere knopen: stijfheid 0 (K_TR_D_N).
    """
    out = OrderedDict()
    if not plan or not plan.get("no_rot"):
        return out
    arms = {}
    for orig, new, d, kind in plan["pairs"]:
        arms.setdefault(orig, []).append((d, kind))
    groups = OrderedDict()
    for nid in plan["no_rot"]:
        own = arms[nid]
        n = _unit(own[0][0])
        k = plan["stiff"].get(nid, 0.0) or 1.0e3
        if n is not None and all(
                kind == "shell" and abs(_dot(_unit(d), n)) > 0.999
                for d, kind in own):
            key = tuple(round(c, 6) for c in n) + (float("%.3g" % k),)
            groups.setdefault(key, [n, k, []])[2].append(nid)
        else:
            groups.setdefault(None, [None, 0.0, []])[2].append(nid)
    zero_mass = ("M_TR_D_N", (0.0,) * 10)
    for key, (n, k, nids) in groups.items():
        name = "BROFP{0}".format(len(out) + 1)
        if n is None:
            cara = [("K_TR_D_N", (0.0,) * 6), zero_mass]
        else:
            full = [[0.0] * 6 for _ in range(6)]
            for a in range(3):
                for b in range(3):
                    full[3 + a][3 + b] = k * n[a] * n[b]
            vals = tuple(full[i][j] for j in range(6) for i in range(j + 1))
            cara = [("K_TR_N", vals), zero_mass]
        out[name] = {"nodes": nids, "mod": "DIS_TR", "cara": cara,
                     "label": "element offset"}
    return out


# ==========================================
# COMMANDOBESTAND
# ==========================================
def coque_groups(model_data, elset):
    """[(GROUP_MA, extra tekst)] voor de COQUE-entries van een schaalelset:
    zonder offset [(elset, "")], anders de rest en per offset een groep met
    EXCENTREMENT en INER_ROTA (verplicht samen, catalogus
    affe_cara_elem.py)."""
    info = model_data.get("offset_shells", {}).get(elset)
    if not info:
        return [(elset, "")]
    out = []
    if info["rest"]:
        out.append((info["rest"], ""))
    for name, w in info["parts"]:
        out.append((name, ", EXCENTREMENT={0!r}, INER_ROTA='OUI'".format(
            float(w))))
    return out


def _relation(terms):
    """LIAISON_DDL-entry sum(coef * ddl) = 0; termen met coef ~0 vallen weg."""
    terms = [(n, ddl, c) for n, ddl, c in terms if abs(c) > 1.0e-12]
    return ("_F(NOEUD=({0},), DDL=({1},), COEF_MULT=({2},), "
            "COEF_IMPO=0.0)").format(
        ", ".join("'N{0}'".format(n) for n, _d, _c in terms),
        ", ".join("'{0}'".format(ddl) for _n, ddl, _c in terms),
        ", ".join(repr(float(c)) for _n, _d, c in terms))


def _in_plane(n):
    """Twee eenheidsvectoren loodrecht op n (en op elkaar)."""
    ref = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
    t1 = _unit(_cross(n, ref))
    return t1, _cross(n, t1)


def link_entries(model_data):
    """
    LIAISON_DDL-relaties van de starre armen (U4.44.01 LIAISON_DDL: lineaire
    relatie sum(COEF_MULT_i u_i) = COEF_IMPO). Per paar (Mecway-knoop o,
    knoop f van het verschoven element, arm d = x_f - x_o), kleine rotaties:
      u_f = u_o + theta_o x d                    (3 relaties)
      balk:   theta_f = theta_o                  (3 relaties)
      schaal: theta_f = theta_o loodrecht op d   (2 relaties; d is de
              normaal)
    De rotatie om de normaal van een schaal (drilling) wordt niet gekoppeld:
    de schaal heeft daar alleen een fictieve stijfheid (Code-Aster
    COEF_RIGI_DRZ, Mecway "arbitrary small stiffness", manual par. 7.4.1).
    Met LIAISON_SOLIDE (die ook die rotatie koppelt) stopte Code-Aster met
    <EXCEPTION> FACTOR_11 op DRY/DRZ van de verschoven knopen (gezien met
    een strook en CompositeBeam, ook met een arm van lengte ~0). Hangt een
    Mecway-knoop alleen nog aan een schaalarm, dan houdt een veer op zijn
    rotatie om de normaal die vrijheidsgraad vast (discretes()).
    Starre-lichaamsbewegingen van het paar voldoen aan de koppelrelaties,
    dus de krachten van de koppeling zijn onderling in evenwicht (de reactie
    gaat in aster_results_export met het moment van de arm naar de
    Mecway-knoop).
    Returns [entry-tekst].
    """
    out = []
    for link in model_data.get("offset_links", []):
        o, f, d = link["orig"], link["new"], link["arm"]
        dx, dy, dz = d
        out.append(_relation([(f, "DX", 1.0), (o, "DX", -1.0),
                              (o, "DRY", -dz), (o, "DRZ", dy)]))
        out.append(_relation([(f, "DY", 1.0), (o, "DY", -1.0),
                              (o, "DRZ", -dx), (o, "DRX", dz)]))
        out.append(_relation([(f, "DZ", 1.0), (o, "DZ", -1.0),
                              (o, "DRX", -dy), (o, "DRY", dx)]))
        if link["kind"] == "beam" or link["own_rot"]:
            axes = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
        else:
            axes = list(_in_plane(_unit(d)))
        for t in axes:
            out.append(_relation(
                [(f, "DR" + c, t[k]) for k, c in enumerate("XYZ")] +
                [(o, "DR" + c, -t[k]) for k, c in enumerate("XYZ")]))
    return out
