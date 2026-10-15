# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_cyclic.py
#
# Verantwoordelijkheid: modale analyse met cyclische symmetrie (Mecway
# Frequency (V30) met een Cyclic symmetry-constraint, manual v33 par. 9.41)
# naar Code-Aster's cyclische substructurering (R4.06.03, U4.52.05):
#   sectormodes met vaste snijvlakken (CALC_MODES, Craig-Bampton) ->
#   DEFI_INTERF_DYNA (DROITE/GAUCHE/AXE, TYPE 'CRAIGB') -> DEFI_BASE_MODALE
#   CLASSIQUE (+ statische modes van de snijvlakken) -> MODE_ITER_CYCL
#   (modes per aantal nodal diameters) -> REST_SOUS_STRUC SECTEUR=1 (en,
#   instelling cyclic_full_wheel, DEFI_SQUELETTE CYCLIQUE + REST_SOUS_STRUC
#   SQUELETTE: het hele wiel) -> aster_cyclic.collect (Mecway's volgorde,
#   terug naar het assenstelsel van het model) -> aster_results_export (de
#   modes op het hele wiel in Mecway's nummering, of op de sector) ->
#   bridge_results_liml.splice_results (de knopen en elementen van de N
#   sectoren in de modelkopie van <solution>, zoals Mecway).
# Syntax: Code-Aster-testcases sdlv134a, sdls04a, sdlv301a (17.4,
# share/aster/tests) en de catalogus mode_iter_cycl.py van code_aster 17.4.
#
#   parse(item, model_data, run_cfg)  <cyclicsymmetry> uit de .liml
#                                     (bridge_from_liml)
#   is_cyclic(model_data)             cyclische symmetrie in het model
#   build_cyclic_modes(...)           builder (bridge_to_aster._build_modal)
#
# Mecway-invoer (headless gemeten met Mecway 33, TestFiles/Tools/
# mw_solve.py; Samples/Impeller.liml):
#   <cyclicsymmetry axis="3" segments="12" selectionmaster="A"
#                   selectionslave="B" />
#   axis: 1 = X, 2 = Y, 3 = Z (ringsector om Z: axis 3 gaf de frequenties
#   van de volledige ring, 1 en 2 niet; om Y: axis 2; "0" gaf hetzelfde als
#   1). De as gaat door de oorsprong (er is geen attribuut voor een punt).
#   Master en slave zijn knoop- of vlakselecties; de slave ligt op +360/N
#   of -360/N graden van de master (Mecway bepaalt zelf de richting).
#   Mecway rekent per aantal nodal diameters ND = 0 .. N/2 (afgerond naar
#   beneden) maxmode modes, en zet ze op volgorde van ND en frequentie
#   (manual par. 9.41: "5 modes ... 7 segments ... 20 modes"); de
#   oplossing toont het volledige wiel. Een paar staande golven (ND > 0)
#   telt als een mode.
#
# Code-Aster:
#   - De symmetrieas moet de Z-as zijn (U4.52.05 par. 1); DROITE en GAUCHE
#     volgen de trigonometrische richting in het XY-vlak: GAUCHE ligt op
#     +360/N graden van DROITE. Omgekeerd gaf <EXCEPTION> ALGORITH16_58
#     "INVERSION INTERFACE DROITE/GAUCHE" (gezien, Code-Aster 17.4). Bij een
#     X- of Y-as schrijft de bridge de coordinaten in het mesh-bestand met
#     een cyclische verwisseling van de assen (_rewrite_mesh; = ROTATION
#     hieronder) en zet hij de richtingen in de lasten om
#     (_permute_charges); aster_cyclic draait mesh en vormen terug.
#   - REST_SOUS_STRUC heeft NOM_CHAM standaard 'ACCE' (gezien): de bridge
#     vraagt 'DEPL'.
#   - De knopen van DROITE en GAUCHE staan in dezelfde volgorde (paren);
#     MODE_ITER_CYCL controleert de ligging (VERI_CYCL).
#   - Knopen op de as: interface AXE ("points communs a tous les secteurs",
#     U4.52.05 par. 3.4.1; testcase sdlv134a).
#   - De nauwkeurigheid hangt af van het aantal sectormodes in de basis
#     (cyclic_base_modes; gemeten in docs/Verificatie.md, CY).
#
# Compatibel met IronPython 2.7.9 (alleen standaardbibliotheek).

import math
import os
import re
from collections import OrderedDict

from bridge_utils import log, tr, CONFIG_BRIDGE, run_name

TAG = "cyclicsymmetry"

# Mecway axis -> index (0 = X, 1 = Y, 2 = Z); zie de kop.
_AXES = {"0": 0, "1": 0, "2": 1, "3": 2}
_AXIS_NAMES = "XYZ"

# Mesh draaien naar de Z-as (MODE_ITER_CYCL): rotatie om (1, 1, 1) over
# ANGLE graden. +120: e_x -> e_y -> e_z -> e_x, dus as Y -> Z en een punt
# (x, y, z) -> (z, x, y); -120: as X -> Z, (x, y, z) -> (y, z, x).
# Componentnamen in de lasten gaan mee (_RENAME), vectoren als tuple
# (_TUPLE: nieuwe volgorde van de oude componenten).
ROTATION = {"X": -120.0, "Y": 120.0}
_RENAME = {"Y": {"X": "Y", "Y": "Z", "Z": "X"},
           "X": {"X": "Z", "Y": "X", "Z": "Y"}}
_TUPLE = {"Y": (1, 2, 0), "X": (2, 0, 1)}

# Groepen in het mesh (bridge_mesh-namen zijn Mecway-namen; deze
# voorvoegsels gebruikt Mecway niet).
GROUP_RIGHT = "BRCYC_D"     # DROITE (lagere hoek)
GROUP_LEFT = "BRCYC_G"      # GAUCHE (+360/N)
GROUP_AXIS = "BRCYC_A"      # knopen op de as
GROUP_FIX = "BRCYC_F"       # vrije knoop van een paar met een vaste knoop

TEMPLATE = "AsterTemplate_ModeIterCycl.comm"

# Coordinaten kleiner dan _SNAP x de modelgrootte worden 0 (_rewrite_mesh).
_SNAP = 1.0e-12

# BC's die vrijheidsgraden vastleggen (per richting): op een snijvlak
# alleen volledig vast (alle drie de verplaatsingen) toegestaan.
_DOF_BCS = ("fixed", "displacement")
# BC's met relaties tussen richtingen of knopen: niet op een snijvlak.
_RELATION_BCS = ("pinnedsupport", "symmetry", "frictionless",
                 "compressiononly", "velocity")


# ==========================================
# INVOER UIT DE .LIML
# ==========================================
def accepts(run_cfg):
    """True als de analyse cyclische symmetrie kan vertalen: modaal
    (CALC_MODES DYNAMIQUE), niet akoestisch."""
    return (run_cfg.get("solver_command") == "CALC_MODES" and
            run_cfg.get("type_resu", "DYNAMIQUE") == "DYNAMIQUE" and
            run_cfg.get("phenomene", "MECANIQUE") != "ACOUSTIQUE")


def parse(item, model_data, run_cfg):
    """
    <cyclicsymmetry axis segments selectionmaster selectionslave> naar
    model_data["cyclic"]. Niet in een modale analyse, of een tweede
    cyclische symmetrie: ERROR en skipped_loads (niet vertaald).
    """
    if item.get("suppressed", "") == "true":
        log("INFO: Cyclische symmetrie overgeslagen (suppressed).")
        return
    master = item.get("selectionmaster", "")
    slave = item.get("selectionslave", "")
    what = tr("cyclische symmetrie '{0}' / '{1}'",
              "cyclic symmetry '{0}' / '{1}'").format(master, slave)
    if not accepts(run_cfg):
        model_data["skipped_loads"].append(what)
        log(tr("ERROR: Cyclische symmetrie wordt alleen in een modale "
               "analyse vertaald (Mecway Frequency, bridge-analyse "
               "modal_3d), niet in {0}. NIET meegenomen: het model rekent "
               "als losse sector.",
               "ERROR: Cyclic symmetry is only translated in a modal "
               "analysis (Mecway Frequency, bridge analysis modal_3d), not "
               "in {0}. NOT included: the model is computed as a single "
               "sector.").format(run_cfg.get("solver_command", "?")))
        return
    if model_data.get("cyclic"):
        model_data["skipped_loads"].append(what)
        log(tr("ERROR: Meer dan een cyclische symmetrie; alleen de eerste "
               "wordt vertaald.",
               "ERROR: More than one cyclic symmetry; only the first is "
               "translated."))
        return
    try:
        segments = int(float(item.get("segments", "0")))
    except ValueError:
        segments = 0
    axis = _AXES.get(item.get("axis", "3").strip(), None)
    if axis is None:
        model_data["skipped_loads"].append(what)
        log(tr("ERROR: Cyclische symmetrie: onbekende as '{0}'. NIET "
               "meegenomen.",
               "ERROR: Cyclic symmetry: unknown axis '{0}'. NOT "
               "included.").format(item.get("axis")))
        return
    model_data["cyclic"] = {"axis": axis, "segments": segments,
                            "master": master, "slave": slave}
    log("INFO: Cyclische symmetrie: {0} segmenten om de {1}-as, master "
        "'{2}', slave '{3}'.".format(segments, _AXIS_NAMES[axis], master,
                                     slave))


def is_cyclic(model_data):
    return bool(model_data.get("cyclic"))


def axis_index(text):
    """Mecway's axis-attribuut ("1"/"2"/"3", "0" = X) naar 0/1/2, of
    None."""
    return _AXES.get((text or "3").strip(), None)


# ==========================================
# KNOPEN VAN SELECTIES
# ==========================================
def _elem_nodes(model_data):
    """{eid: (aster_type, [nid in Code-Aster-volgorde])} (bridge_mesh)."""
    conn = model_data.get("_conn")
    if conn:
        return conn
    import bridge_mesh
    out = {}
    for eid, shape, enodes, _elset in model_data.get("mesh_elements", []):
        spec = bridge_mesh._ASTER_TYPES.get(shape)
        if spec:
            out[eid] = (spec[0], [enodes[i] for i in spec[1]])
    return out


def _face_nodes(conn, eid, fid):
    """Hoek- en middenknopen van vlak fid van element eid (tabel van
    bridge_mesh, zoals zonder Mecway-API; in Mecway gelijk aan
    mw.face_nodes, nagelopen door bridge_mesh)."""
    import bridge_mesh
    if eid not in conn:
        return []
    atype, cn = conn[eid]
    corners = bridge_mesh._face_from_table(atype, cn, fid)
    if not corners:
        return []
    return list(bridge_mesh._skin_element(atype, cn, corners)[1])


def _selection_nodes(model_data, name, conn):
    """
    Knoopnummers van een selectie (Mecway- of Code-Aster-naam): knoop-,
    vlak- of elementselectie; None als ze niet bestaat.
    """
    renames = model_data.get("selection_renames", {})
    reverse = dict((v, k) for k, v in renames.items())
    aster = renames.get(name, name)
    mecway = reverse.get(name, name)
    groups = model_data.get("node_groups", {})
    for key in (aster, name, mecway):
        if key in groups:
            return set(int(str(n).lstrip("N")) for n in groups[key])
    faces = model_data.get("face_selection_faces", {})
    for key in (mecway, name, aster):
        if key in faces:
            out = set()
            for eid, fid in faces[key]:
                out.update(_face_nodes(conn, eid, fid))
            return out
    elems = model_data.get("element_selections", {})
    for key in (aster, name, mecway):
        if key in elems:
            out = set()
            for eid in elems[key]:
                out.update(conn.get(int(eid), (None, []))[1])
            return out
    return None


# ==========================================
# PAREN MASTER-SLAVE
# ==========================================
def _rotate(p, axis, angle):
    """Punt p gedraaid om de as (index) door de oorsprong."""
    c, s = math.cos(angle), math.sin(angle)
    i, j = (axis + 1) % 3, (axis + 2) % 3
    q = list(p)
    q[i] = c * p[i] - s * p[j]
    q[j] = s * p[i] + c * p[j]
    return tuple(q)


class _Grid(object):
    """Ruimtelijk raster om knopen op coordinaat te vinden."""

    def __init__(self, coords, nids, h):
        self.h = h
        self.cells = {}
        self.coords = coords
        for n in nids:
            self.cells.setdefault(self._key(coords[n]), []).append(n)

    def _key(self, p):
        return tuple(int(math.floor(v / self.h)) for v in p)

    def nearest(self, p):
        k = self._key(p)
        best, dist = None, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for n in self.cells.get((k[0] + dx, k[1] + dy,
                                             k[2] + dz), ()):
                        q = self.coords[n]
                        d = math.sqrt(sum((q[a] - p[a]) ** 2
                                          for a in range(3)))
                        if dist is None or d < dist:
                            best, dist = n, d
        return best, dist


def _pairs(coords, master, slave, axis, n_seg, tol):
    """
    (paren [(droite, gauche)], asknopen, fout) met gauche op +360/N graden
    van droite; fout = melding of None.
    """
    def radius(p):
        return math.sqrt(sum(p[a] ** 2 for a in range(3) if a != axis))
    on_axis = set(n for n in master | slave if radius(coords[n]) <= tol)
    m = sorted(master - on_axis)
    s = sorted(slave - on_axis)
    if len(m) != len(s):
        return None, on_axis, tr(
            "master en slave hebben een verschillend aantal knopen buiten "
            "de as ({0} en {1})", "master and slave have a different number "
            "of nodes off the axis ({0} and {1})").format(len(m), len(s))
    if not m:
        return None, on_axis, tr("geen knopen buiten de as",
                                 "no nodes off the axis")
    grid = _Grid(coords, s, max(10.0 * tol, 1e-12))
    alpha = 2.0 * math.pi / n_seg
    worst = {}
    for sign in (1.0, -1.0):
        pairs = []
        used = set()
        worst[sign] = 0.0
        for n in m:
            q, d = grid.nearest(_rotate(coords[n], axis, sign * alpha))
            if q is None or d > tol or q in used:
                worst[sign] = max(worst[sign], d if d is not None else
                                  float("inf"))
                pairs = None
                break
            used.add(q)
            pairs.append((n, q) if sign > 0 else (q, n))
        if pairs is not None:
            pairs.sort()
            return pairs, on_axis, None
    return None, on_axis, tr(
        "de slave-knopen liggen niet op +/-360/{0} graden van de "
        "master-knopen om de {1}-as door de oorsprong (binnen {2:.3g} m)",
        "the slave nodes do not lie at +/-360/{0} degrees from the master "
        "nodes about the {1} axis through the origin (within {2:.3g} "
        "m)").format(n_seg, _AXIS_NAMES[axis], tol)


# ==========================================
# OPLEGGINGEN OP DE SNIJVLAKKEN
# ==========================================
def _constrained(model_data, conn):
    """
    ({knoop: set(DX/DY/DZ) vastgelegd}, set(knopen met een relatie)) uit
    de BC's, constraint equations en koppelingen.
    """
    dofs = {}
    related = set()
    for bc in model_data.get("bcs", []):
        if bc.get("skip") or not bc.get("selection"):
            continue
        if bc["type"] in _DOF_BCS:
            if bc["type"] == "fixed":
                comps = ("DX", "DY", "DZ")
            else:
                comps = [k for k in bc.get("aster_dict", {})
                         if k in ("DX", "DY", "DZ")]
            nodes = _selection_nodes(model_data, bc["selection"], conn)
            for n in nodes or ():
                dofs.setdefault(n, set()).update(comps)
        elif bc["type"] in _RELATION_BCS:
            nodes = _selection_nodes(model_data, bc["selection"], conn)
            related.update(nodes or ())
    for ce in model_data.get("constraint_equations", []):
        related.update(int(n) for n, _d, _c in ce["terms"])
    for c in model_data.get("couplings", []):
        for key in ("slave_group", "master_group"):
            nodes = _selection_nodes(model_data, c.get(key, ""), conn)
            related.update(nodes or ())
    return dofs, related


# ==========================================
# LASTEN IN HET REKENFRAME (as -> Z)
# ==========================================
def _permute_entry(text, axis_name):
    """Een _F(...)-tekst met de richtingen in het gedraaide frame."""
    ren = _RENAME[axis_name]
    order = _TUPLE[axis_name]
    text = re.sub(r"\b([DF])([XYZ])(\s*=)",
                  lambda m: m.group(1) + ren[m.group(2)] + m.group(3), text)
    text = re.sub(r"'D([XYZ])'", lambda m: "'D" + ren[m.group(1)] + "'",
                  text)

    def vec(m):
        vals = [v.strip() for v in m.group(3).split(",")]
        if len(vals) != 3:
            return m.group(0)
        new = [None] * 3
        for k in range(3):
            new[order[k]] = vals[k]
        return "{0}{1}{2}{3}".format(m.group(1), m.group(2), ", ".join(new),
                                     m.group(4))
    return re.sub(r"\b((?:DIRECTION|AXE|CENTRE)\s*=\s*)([\(\[])([^\)\]]*)"
                  r"([\)\]])", lambda m: vec(m), text)


_NOT_PERMUTED = re.compile(r"\bANGL_NAUT\s*=|\bDR[XYZ]\b|\bM[XYZ]\s*=")


def _permute_charges(charges, axis_name):
    """
    Kopie van de lasten (_build_charges) in het gedraaide frame, of
    (None, reden) als een last niet om te zetten is.
    """
    out = []
    for command, kws, fonc in charges:
        if command != "AFFE_CHAR_MECA":
            return None, tr("een last met een functie ({0})",
                            "a load with a function ({0})").format(
                                ", ".join(kws))
        new = OrderedDict()
        for kw, entries in kws.items():
            # Schuine assenstelsels en rotaties/momenten zet de bridge niet
            # om (bij volume-elementen komen ze normaal niet voor).
            if kw in ("LIAISON_OBLIQUE",) or any(
                    _NOT_PERMUTED.search(e) for e in entries):
                return None, kw
            new[kw] = [_permute_entry(e, axis_name) for e in entries]
        out.append((command, new, fonc))
    return out, None


# ==========================================
# CONTROLE VAN HET MODEL
# ==========================================
def _check_model(model_data, analysis):
    """Wat de cyclische route niet kan: ERROR met de oplossing."""
    import bridge_to_aster as b2a
    ok = True
    cyc = model_data["cyclic"]
    if cyc["segments"] < 2:
        log(tr("ERROR: Cyclische symmetrie met {0} segment(en); geef in "
               "Mecway het aantal segmenten van het hele wiel (minstens 2).",
               "ERROR: Cyclic symmetry with {0} segment(s); enter in Mecway "
               "the number of segments of the whole wheel (at least "
               "2).").format(cyc["segments"]))
        ok = False
    dims = model_data.get("elset_dims", {})
    other = [e for e, d in dims.items() if d != "3D"]
    if other:
        # Mecway: "Shells and beams are not allowed in frequency analysis"
        # met de interne solver (manual v33 par. 9.41).
        log(tr("ERROR: Cyclische symmetrie alleen met volume-elementen (ook "
               "in Mecway, manual par. 9.41); niet met {0}.",
               "ERROR: Cyclic symmetry only with solid elements (also in "
               "Mecway, manual section 9.41); not with {0}.").format(
                   ", ".join("'{0}'".format(e) for e in other)))
        ok = False
    if model_data.get("line_quad"):
        log(tr("ERROR: Cyclische symmetrie met elem_hex8 = LINE_QUAD kan "
               "niet: de nieuwe middenknopen op de snijvlakken hebben geen "
               "paar. Gebruik kwadratische elementen in Mecway (hex20), of "
               "elem_hex8 = 3D (pagina Elementen).",
               "ERROR: Cyclic symmetry with elem_hex8 = LINE_QUAD is not "
               "possible: the new midside nodes on the cut faces have no "
               "pair. Use quadratic elements in Mecway (hex20), or "
               "elem_hex8 = 3D (Elements page)."))
        ok = False
    if model_data.get("bonded"):
        log(tr("ERROR: Verlijmd contact met cyclische symmetrie wordt niet "
               "vertaald.",
               "ERROR: Bonded contact with cyclic symmetry is not "
               "translated."))
        ok = False
    return ok


def _base_count(analysis, n):
    """Aantal sectormodes (vaste snijvlakken) in de basis: instelling
    cyclic_base_modes, 0 = automatisch max(20, 4 n)."""
    nb = int(analysis.get("cyclic_base_modes", 0) or 0)
    if nb <= 0:
        nb = max(20, 4 * n)
    return max(nb, n)


def _fmt_names(nids, per_line=10):
    names = ["N{0}".format(n) for n in nids]
    return "\n".join(" " + " ".join(names[i:i + per_line])
                     for i in range(0, len(names), per_line))


def to_model_frame(xyz, axis):
    """
    Coordinaten uit het .mail van een cyclische run terug naar het frame
    van het model: de inverse van de verwisseling in _rewrite_mesh (daar
    nieuw[_TUPLE[a]] = oud[a], dus model[a] = mesh[_TUPLE[a]]). axis: index
    0/1/2 (X/Y/Z, bridge_results_liml.cyclic_info); bij Z ongewijzigd.
    Voor bridge_results_liml.check_results_fit (knop Resultaten...).
    """
    order = _TUPLE.get(_AXIS_NAMES[axis]) if axis in (0, 1, 2) else None
    if order is None:
        return tuple(xyz)
    return tuple(xyz[order[a]] for a in range(3))


def _rewrite_mesh(msh_path, groups, axis_name, size):
    """
    Knoopgroepen (in deze volgorde) achteraan het ASTER-mesh, en de
    coordinaten in het rekenframe (_TUPLE bij een X- of Y-as: as -> Z).
    Een exacte verwisseling in het bestand, geen MODI_MAILLAGE ROTATION
    vooraf, en coordinaten kleiner dan _SNAP x de modelgrootte worden 0:
    MODE_ITER_CYCL vergelijkt de axiale coordinaat van de paren relatief,
    en ruis rond 0 (1e-17 na een rotatie; 1,9e-20 tegen 6,0e-20 m in
    Mecway's eigen Impeller.liml) gaf <EXCEPTION> ALGORITH16_52 "axe de
    symetrie cyclique different de Oz" (gezien met Code-Aster 17.4). De
    verschuiving (< 1e-12 x de modelgrootte) valt binnen de controle van
    de knoopvolgorde in aster_results_export (1e-9).
    """
    with open(msh_path, "r") as f:
        text = f.read()
    order = _TUPLE.get(axis_name, (0, 1, 2))
    snap = _SNAP * size
    lines = text.split("\n")
    inside = False
    for k, line in enumerate(lines):
        word = line.strip()
        if word == "COOR_3D":
            inside = True
            continue
        if inside and word == "FINSF":
            inside = False
            continue
        if inside and word:
            parts = word.split()
            new = [None] * 3
            for a in range(3):
                v = parts[1 + a]
                if abs(float(v)) < snap:
                    v = "0.0"
                new[order[a]] = v
            lines[k] = " " + " ".join([parts[0]] + new + parts[4:])
    text = "\n".join(lines)
    body = text.rstrip()
    if not body.endswith("FIN"):
        raise IOError("mesh zonder FIN: {0}".format(msh_path))
    body = body[:-3]
    for name, nids in groups:
        if nids:
            body += "GROUP_NO\n {0}\n{1}\nFINSF\n".format(
                name, _fmt_names(nids))
    with open(msh_path, "w") as f:
        f.write(body + "FIN\n")


def _relations(pairs, n_seg):
    """LIAISON_DDL voor ND 0 in het Z-frame: u_G = R_z(360/N) u_D."""
    a = 2.0 * math.pi / n_seg
    c, s = math.cos(a), math.sin(a)
    out = []
    for d, g in pairs:
        nd, ng = "'N{0}'".format(d), "'N{0}'".format(g)
        out.append("_F(NOEUD=({0}, {1}, {1}), DDL=('DX', 'DX', 'DY'), "
                   "COEF_MULT=(1.0, {2!r}, {3!r}), COEF_IMPO=0.0)".format(
                       ng, nd, -c, s))
        out.append("_F(NOEUD=({0}, {1}, {1}), DDL=('DY', 'DX', 'DY'), "
                   "COEF_MULT=(1.0, {2!r}, {3!r}), COEF_IMPO=0.0)".format(
                       ng, nd, -s, -c))
        out.append("_F(NOEUD=({0}, {1}), DDL=('DZ', 'DZ'), "
                   "COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0)".format(ng, nd))
    return out


# ==========================================
# BUILDER
# ==========================================
def build_cyclic_modes(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Genereer de .comm en .export voor modes met cyclische symmetrie
    (MODE_ITER_CYCL). Returns het pad van de .export, of None (ERROR
    gelogd). Aanroep vanuit bridge_to_aster._build_modal (V30 met
    <cyclicsymmetry>), na _collapse_histories.
    """
    import bridge_to_aster as b2a
    log("--- Generating Aster Files (MODE_ITER_CYCL) ---")
    if not _check_model(model_data, analysis):
        return None
    cyc = model_data["cyclic"]
    n_seg = cyc["segments"]
    axis = cyc["axis"]
    axis_name = _AXIS_NAMES[axis]
    conn = _elem_nodes(model_data)
    coords = model_data.get("mesh_nodes", {})

    # --- snijvlakken ---
    master = _selection_nodes(model_data, cyc["master"], conn)
    slave = _selection_nodes(model_data, cyc["slave"], conn)
    for name, nodes in ((cyc["master"], master), (cyc["slave"], slave)):
        if not nodes:
            log(tr("ERROR: Cyclische symmetrie: selectie '{0}' bestaat niet "
                   "of is leeg.",
                   "ERROR: Cyclic symmetry: selection '{0}' does not exist "
                   "or is empty.").format(name))
            return None
    size = max([abs(v) for p in coords.values() for v in p] + [1e-12])
    tol = 1.0e-5 * size
    pairs, on_axis, err = _pairs(coords, master, slave, axis, n_seg, tol)
    if err:
        log(tr("ERROR: Cyclische symmetrie: {0}. Controleer het aantal "
               "segmenten, de as en dat de knopen van de twee snijvlakken "
               "op elkaar passen (Mecway eist dat ook met de interne "
               "solver, manual par. 9.41).",
               "ERROR: Cyclic symmetry: {0}. Check the number of segments, "
               "the axis and that the nodes of both cut faces match (Mecway "
               "requires that too with the internal solver, manual section "
               "9.41).").format(err))
        return None

    # --- opleggingen op de snijvlakken ---
    dofs, related = _constrained(model_data, conn)
    full = set(n for n, d in dofs.items() if len(d) == 3)
    cut = set(n for p in pairs for n in p) | on_axis
    partial = sorted(n for n in cut if (n in dofs and n not in full) or
                     (n in related and n not in full))
    if partial:
        log(tr("ERROR: Cyclische symmetrie: {0} knoop/knopen op de "
               "snijvlakken hebben een gedeeltelijke oplegging of een "
               "relatie (bijv. N{1}). De bridge kan op een snijvlak alleen "
               "volledig vaste knopen (fixed, of displacement 0 in X, Y en "
               "Z). Haal de oplegging van het snijvlak, of leg die knopen "
               "volledig vast.",
               "ERROR: Cyclic symmetry: {0} node(s) on the cut faces have "
               "a partial support or a relation (e.g. N{1}). On a cut face "
               "the bridge only supports fully fixed nodes (fixed, or "
               "displacement 0 in X, Y and Z). Remove the support from the "
               "cut face, or fix those nodes completely.").format(
                   len(partial), partial[0]))
        return None
    free_pairs = [(d, g) for d, g in pairs if d not in full and g not in full]
    extra_fix = sorted(set(d if g in full else g for d, g in pairs
                           if (d in full) != (g in full)))
    axis_nodes = sorted(n for n in on_axis if n not in full)
    if not free_pairs:
        log(tr("ERROR: Cyclische symmetrie: alle knopen op de snijvlakken "
               "liggen vast; de sectoren zijn dan niet gekoppeld. Reken "
               "zonder cyclische symmetrie.",
               "ERROR: Cyclic symmetry: all nodes on the cut faces are "
               "fixed; the sectors are then not coupled. Compute without "
               "cyclic symmetry."))
        return None
    if axis_nodes and n_seg == 8:
        # Code-Aster 17.4, bibfor/algorith/ctetax.F90: de controle van de
        # asknopen draait het vector (1, 1, 1) van actieve vrijheidsgraden
        # over 360/N graden; bij 45 graden is cos - sin = 0, dus "ontbreekt"
        # DX: <EXCEPTION> ALGORITH14_95 "il manque un ddl sur un noeud axe"
        # (gezien met een cirkelvormige plaat, N = 8; met N = 6 en 12 niet).
        log(tr("ERROR: Cyclische symmetrie met 8 segmenten en knopen op de "
               "as ({0}) kan Code-Aster 17.4 niet rekenen (MODE_ITER_CYCL "
               "stopt met ALGORITH14_95, een fout in Code-Aster bij 45 "
               "graden). Maak in Mecway een klein gat op de as (geen knopen "
               "op de as), of reken het volledige model.",
               "ERROR: Cyclic symmetry with 8 segments and nodes on the "
               "axis ({0}) cannot be computed by Code-Aster 17.4 "
               "(MODE_ITER_CYCL stops with ALGORITH14_95, a Code-Aster bug "
               "at 45 degrees). Make a small hole on the axis in Mecway (no "
               "nodes on the axis), or compute the full model.").format(
                   len(axis_nodes)))
        return None
    if extra_fix:
        log("INFO: Cyclische symmetrie: {0} knoop/knopen op een snijvlak "
            "vastgelegd omdat de bijbehorende knoop op het andere snijvlak "
            "vastligt.".format(len(extra_fix)))
    log("INFO: Cyclische symmetrie: {0} knopenparen{1}{2}, as {3}, {4} "
        "segmenten ({5:.6g} graden).".format(
            len(free_pairs), ", {0} knopen op de as".format(len(axis_nodes))
            if axis_nodes else "", ", {0} paren met een vaste knoop".format(
                len(pairs) - len(free_pairs)) if len(pairs) != len(
                    free_pairs) else "", axis_name, n_seg, 360.0 / n_seg))

    # --- instellingen ---
    n = b2a._mode_count(model_data, analysis)
    nb = _base_count(analysis, n)
    shift = float(analysis.get("modal_shift_hz", 0.0) or 0.0)
    if analysis.get("modal_complex", False):
        log(tr("WARNING: Complexe modes (modal_complex) met cyclische "
               "symmetrie worden niet gebouwd; de bridge rekent reele modes "
               "zonder demping (zoals Mecway).",
               "WARNING: Complex modes (modal_complex) with cyclic symmetry "
               "are not built; the bridge computes real modes without "
               "damping (like Mecway)."))
    wanted = [f for f in analysis.get("fields", ["displacements"])
              if f != "displacements"]
    if wanted:
        log("INFO: Cyclische symmetrie: naar Mecway gaan alleen de "
            "trillingsvormen; genegeerd: {0}.".format(", ".join(wanted)))
    norm = str(analysis.get("modal_norm", "MASS_GENE")).upper()
    if norm != "MASS_GENE":
        log("INFO: Cyclische symmetrie: de normering ({0}) geldt alleen voor "
            "de sectorbasis; de schaal van de cyclische modes is die van "
            "REST_SOUS_STRUC.".format(norm))

    # --- lasten ---
    prestress_on = bool(analysis.get("modal_prestress", True))
    charges, names_bc, names_load = b2a._modal_charges(model_data, False,
                                                       prestress_on)
    prestress = None
    if prestress_on and (names_load or b2a._thermal_active(model_data)):
        prestress = b2a._prestress_plan(model_data, charges, names_bc,
                                        names_load)
        if prestress is None:
            return None
    rotate_block = "#-- symmetrieas is Z: geen rotatie --\n"
    if axis_name != "Z":
        perm, why = _permute_charges(charges, axis_name)
        if perm is None or model_data.get("_charge_prelude"):
            log(tr("ERROR: Cyclische symmetrie om de {0}-as: de bridge draait "
                   "het model naar de Z-as (MODE_ITER_CYCL eist Z), maar kan "
                   "{1} niet meedraaien. Draai het model in Mecway zo dat de "
                   "symmetrieas de Z-as is.",
                   "ERROR: Cyclic symmetry about the {0} axis: the bridge "
                   "rotates the model to the Z axis (MODE_ITER_CYCL requires "
                   "Z), but cannot rotate {1}. Rotate the model in Mecway so "
                   "that the symmetry axis is the Z axis.").format(
                       axis_name, why or tr("een formule-last",
                                            "a formula load")))
            return None
        charges = perm
        if model_data.get("aster_custom", {}).get("code"):
            log(tr("WARNING: Cyclische symmetrie om de {0}-as: #ASTER-code "
                   "rekent in het gedraaide frame (as {0} -> Z); richtingen "
                   "daarin gelden in dat frame.",
                   "WARNING: Cyclic symmetry about the {0} axis: #ASTER code "
                   "is computed in the rotated frame (axis {0} -> Z); "
                   "directions in it apply in that frame.").format(axis_name))
        rotate_block = (
            "# Symmetrieas {0} -> Z: MODE_ITER_CYCL eist de Z-as (U4.52.05\n"
            "# par. 1). Het mesh-bestand staat al in het rekenframe (cyclische\n"
            "# verwisseling van de assen = rotatie {1!r} graden om (1, 1, 1),\n"
            "# bridge_cyclic._rewrite_mesh), de lasten ook\n"
            "# (_permute_charges); aster_cyclic draait mesh en vormen terug.\n"
            ).format(axis_name, ROTATION[axis_name])
    try:
        _rewrite_mesh(msh_path, [
            (GROUP_RIGHT, [d for d, g in free_pairs]),
            (GROUP_LEFT, [g for d, g in free_pairs]),
            (GROUP_AXIS, axis_nodes), (GROUP_FIX, extra_fix)], axis_name,
            size)
    except Exception as e:
        log(tr("ERROR: Snijvlakgroepen niet in het mesh gezet: {0}",
               "ERROR: Cut face groups not written to the mesh: {0}")
            .format(e))
        return None
    loads_block, excit_clause = b2a._render_charges(charges, model_data)
    cyc_names = ["cycl_if"]
    cyc_lines = [
        "# Cyclische symmetrie (bridge_cyclic): snijvlakken vast voor de",
        "# sectorbasis (Craig-Bampton, U4.52.05; testcase sdlv134a).",
        "cycl_if = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(",
        "    GROUP_NO=({0}), DX=0.0, DY=0.0, DZ=0.0))".format(", ".join(
            "'{0}'".format(g) for g in [GROUP_RIGHT, GROUP_LEFT] +
            ([GROUP_AXIS] if axis_nodes else [])) + ","),
    ]
    fix_names = []
    if extra_fix:
        fix_names = ["cycl_fix"]
        cyc_lines += [
            "# Vrije knoop van een paar waarvan de andere knoop vastligt.",
            "cycl_fix = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(",
            "    GROUP_NO='{0}', DX=0.0, DY=0.0, DZ=0.0))".format(GROUP_FIX)]
    static_block = "#-- niet van toepassing (geen voorspanning) --\n"
    if prestress:
        rel = _relations(free_pairs, n_seg)
        ddl = ""
        if axis_nodes:
            ddl = ("    DDL_IMPO=_F(GROUP_NO='{0}', DX=0.0, DY=0.0),\n"
                   .format(GROUP_AXIS))
        cyc_lines += [
            "# Voorspanning: de statische toestand is cyclisch symmetrisch",
            "# (ND 0): u_gauche = R_z(360/N) u_droite; knopen op de as alleen",
            "# axiaal.",
            "cycl_rel = AFFE_CHAR_MECA(MODELE=model,",
            ddl + "    LIAISON_DDL=(",
        ] + ["        {0},".format(r) for r in rel] + ["    ),", ")"]
        # Alle lasten zijn hier constant (_collapse_histories); de EXCIT
        # van _render_charges plus de cyclische relaties.
        names = (["load_{0}".format(k + 1) for k in range(len(charges))] +
                 list(model_data.get("aster_custom", {}).get("excit", [])) +
                 ["cycl_rel"] + fix_names)
        excit = "    EXCIT=(\n{0}    ),".format("".join(
            "        _F(CHARGE={0}),\n".format(x) for x in names))
        static_block = (
            "# Voorspanning: spanningstoestand onder de aangebrachte lasten\n"
            "# (Mecway manual v33 par. 6.3, stress stiffening).\n"
            "stat = MECA_STATIQUE(\n"
            "    MODELE=model,\n"
            "    CHAM_MATER=fieldmat,\n"
            "{cara}{excit}\n"
            "    SOLVEUR=_F(METHODE='MUMPS', NPREC={nprec}),\n"
            ")\n"
            "sig = CREA_CHAMP(OPERATION='EXTR', TYPE_CHAM='ELGA_SIEF_R',\n"
            "                 RESULTAT=stat, NUME_ORDRE=1, "
            "NOM_CHAM='SIEF_ELGA')\n").format(
                cara="    CARA_ELEM=cara,\n" if b2a._has_cara(model_data)
                else "", excit=excit,
                nprec=int(analysis.get("solver_nprec", 8)))
    cyclic_loads_block = "\n".join(cyc_lines) + "\n"

    cara_ref = "    CARA_ELEM=cara,\n" if b2a._has_cara(model_data) else ""
    extra = model_data.get("aster_custom", {}).get("excit", [])
    rotation = prestress["rotation"] if prestress else []
    charge_names = (list(names_bc) + [x for x in extra if x not in names_bc]
                    + [x for x in rotation] + cyc_names + fix_names)
    second = "        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n"
    if prestress:
        second += ("        _F(MATRICE=CO('rigi_geo'), OPTION='RIGI_GEOM', "
                   "SIEF_ELGA=sig),\n")
    if rotation:
        second += "        _F(MATRICE=CO('rigi_rot'), OPTION='RIGI_ROTA'),\n"
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}    CHARGE=({charge},),\n"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('{rigi}'), OPTION='RIGI_MECA'),\n"
        "{second}"
        "    ),\n"
        ")\n").format(cara=cara_ref, charge=", ".join(charge_names),
                      second=second,
                      rigi="rigi_ela" if prestress else "rigidite")
    if prestress:
        terms = ["rigi_ela", "rigi_geo"] + (["rigi_rot"] if rotation else [])
        assemblage_block += (
            "# Voorgespannen stijfheid (stress stiffening)\n"
            "rigidite = COMB_MATR_ASSE(COMB_R=(\n{0}))\n").format("".join(
                "    _F(MATR_ASSE={0}, COEF_R=1.0),\n".format(m)
                for m in terms))

    interfaces = ["        _F(NOM='DROITE', TYPE='CRAIGB', "
                  "GROUP_NO='{0}'),".format(GROUP_RIGHT),
                  "        _F(NOM='GAUCHE', TYPE='CRAIGB', "
                  "GROUP_NO='{0}'),".format(GROUP_LEFT)]
    if axis_nodes:
        interfaces.append("        _F(NOM='AXE', TYPE='CRAIGB', "
                          "GROUP_NO='{0}'),".format(GROUP_AXIS))
    base_block = "\n".join([
        "# Sectormodes met vaste snijvlakken (basis voor de cyclische",
        "# substructurering)",
        "modes = CALC_MODES(",
        "    TYPE_RESU='DYNAMIQUE',",
        "    MATR_RIGI=rigidite,",
        "    MATR_MASS=masse,",
        "    OPTION='PLUS_PETITE',",
        "    CALC_FREQ=_F(NMAX_FREQ={0}),".format(nb),
        "    CHAM_MATER=fieldmat,",
    ] + (["    CARA_ELEM=cara,"] if cara_ref else []) + [
        "    VERI_MODE=_F(SEUIL={0}, STOP_ERREUR='NON'),".format(
            "%.10g" % float(analysis.get("modal_tolerance", 1.0e-6))),
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(
            int(analysis.get("solver_nprec", 8))),
        ")",
        "lint = DEFI_INTERF_DYNA(",
        "    NUME_DDL=numedd,",
        "    INTERFACE=(",
    ] + interfaces + [
        "    ),",
        ")",
        "# Basis: de sectormodes plus de statische modes van de snijvlakken",
        "bamo = DEFI_BASE_MODALE(CLASSIQUE=_F(INTERF_DYNA=lint, "
        "MODE_MECA=modes, NMAX_MODE={0}))".format(nb),
    ]) + "\n"
    diameters = list(range(n_seg // 2 + 1))
    # NB_DIAM 0 .. N/2 (naar beneden afgerond), zoals Mecway. TOUT_DIAM
    # rekent bij een oneven N ook (N + 1)/2, gelijk aan (N - 1)/2 (gezien:
    # Impeller, N = 17, ND 9 = ND 8).
    calcul = ["NB_DIAM={0}".format(tuple(diameters) if len(diameters) > 1
                                   else "({0},)".format(diameters[0])),
              "NMAX_FREQ={0}".format(n)]
    if shift > 0.0:
        calcul += ["OPTION='CENTRE'", "FREQ={0!r}".format(shift)]
        log("INFO: Cyclische symmetrie: per nodal diameter de {0} modes "
            "het dichtst bij {1} Hz (OPTION 'CENTRE').".format(n, shift))
    elif shift < 0.0:
        log("INFO: Cyclische symmetrie: een negatieve zoekfrequentie is niet "
            "nodig (de sector met vaste snijvlakken heeft geen starre "
            "modes); de laagste modes.")
    scripts = os.path.dirname(os.path.abspath(__file__))
    full_wheel = bool(analysis.get("cyclic_full_wheel", True))
    liml = model_data.get("liml_path", "")
    wheel_lines = []
    wheel_args = ""
    if full_wheel:
        # Het hele wiel zoals Mecway (S10i): skelet met alle N sectoren
        # (DEFI_SQUELETTE CYCLIQUE, SECTEUR TOUT='OUI') en de modes daarop
        # (REST_SOUS_STRUC SQUELETTE: sector j met de fase van de ND;
        # syntax testcases sdlv134a, sdls04a, sdls01c, 17.4). Lukt het
        # niet, dan gaat alleen de sector naar Mecway (aster_cyclic).
        wheel_lines = [
            "# Het hele wiel (instelling cyclic_full_wheel): skelet met de N",
            "# sectoren en de modes daarop; anders alleen de sector.",
            "try:",
            "    squel = DEFI_SQUELETTE(CYCLIQUE=_F(MODE_CYCL=modcyc),",
            "                           SECTEUR=_F(TOUT='OUI'))",
            "    modwiel = REST_SOUS_STRUC(RESU_GENE=modcyc, SQUELETTE=squel,",
            "                              NOM_CHAM='DEPL')",
            "except Exception as exc:",
            # Melding in de taal van de bridge (zonder
            # apostrof: staat tussen '...').
            "    print('{0}: %r' % (exc,))".format(tr(
                "aster_cyclic: WAARSCHUWING: skelet van het hele wiel niet "
                "gemaakt",
                "aster_cyclic: WARNING: skeleton of the whole wheel not "
                "built")),
            "    squel = modwiel = None",
        ]
        wheel_args = ", wheel=modwiel, skeleton=squel, liml={0}".format(
            b2a._py_str(liml))
        log("INFO: Cyclische symmetrie: de modes gaan op het hele wiel "
            "naar Mecway ({0} sectoren, zoals Mecway; instelling "
            "cyclic_full_wheel).".format(n_seg))
    cycl_block = "\n".join([
        "modcyc = MODE_ITER_CYCL(",
        "    BASE_MODALE=bamo,",
        "    NB_MODE={0},".format(nb),
        "    NB_SECTEUR={0},".format(n_seg),
        "    LIAISON=_F(DROITE='DROITE', GAUCHE='GAUCHE'{0}),".format(
            ", AXE='AXE'" if axis_nodes else ""),
        "    CALCUL=_F({0}),".format(", ".join(calcul)),
        ")",
        "# Modes op sector 1 (per mode het veld DEPL)",
        "modsec = REST_SOUS_STRUC(RESU_GENE=modcyc, SECTEUR=1, NOM_CHAM='DEPL')",
    ] + wheel_lines + [
        "import sys",
        "sys.path.insert(0, {0})".format(b2a._py_str(scripts)),
        "import aster_cyclic",
        "res = aster_cyclic.collect(modsec, mesh, numedd, {0}, {1}, {2!r}, "
        "axis='{3}', "
        "angle={4!r}{5})".format(n_seg, n, diameters, axis_name,
                                 ROTATION.get(axis_name, 0.0), wheel_args),
    ]) + "\n"
    export_block = b2a._custom_code(model_data, "post") + (
        "# Resultaten in Mecway's eigen formaat (bridge: result_route='liml')@N"
        "import aster_results_export@N"
        "aster_results_export.export_results(@N"
        "    res, {fragment}, {liml},@N"
        "    fields=['displacements'], precision='double',@N"
        "    cyclic={cyclic})@N"
    ).replace("@N", chr(10)).format(
        fragment=b2a._py_str(b2a.results_file(work_dir)),
        liml=b2a._py_str(liml),
        cyclic="{{'axis': {0}, 'segments': {1}}}".format(axis, n_seg))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL',)))\n")
    else:
        impr_resu_block = "#-- geen MED-export (instelling med_export uit) --\n"
    log("INFO: MODE_ITER_CYCL: {0} modes per nodal diameter (ND 0 .. {1}), "
        "{2} sectormodes in de basis (cyclic_base_modes){3}.".format(
            n, diameters[-1], nb, ", voorgespannen" if prestress else ""))

    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = b2a._read_template(TEMPLATE)
        b2a._write_comm(comm_path, template.format(
            defigroup_block=b2a._build_defigroup_block(model_data),
            rotate_block=rotate_block,
            model_block=b2a._build_model_block(model_data),
            cara_elem_block=b2a._build_cara_elem_block(model_data),
            materials_block=b2a._build_materials_block(model_data, analysis),
            fieldmat_block=b2a._build_fieldmat_block(model_data),
            loads_block=loads_block,
            cyclic_loads_block=cyclic_loads_block,
            static_block=static_block,
            assemblage_block=assemblage_block,
            base_block=base_block,
            cycl_block=cycl_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
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
            time_limit=analysis.get("time_limit", 900),
            memory_limit=analysis.get("memory_limit", 2048),
            ncpus=CONFIG_BRIDGE["ncpus"],
            comm=comm_path, msh=msh_path,
            mess=os.path.join(work_dir, run_name(".mess")),
        ) + b2a._export_result_lines(work_dir, resu_name)
        with open(export_path, "w") as f:
            f.write(export_content)
        log("SUCCESS: .export geschreven naar '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren solver-bestanden mislukt: {0}",
               "ERROR: Generating solver files failed: {0}").format(str(e)))
    return None
