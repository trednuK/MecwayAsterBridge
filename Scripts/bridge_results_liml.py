# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_results_liml.py
#
# Verantwoordelijkheid: zet een resultaatbestand (geschreven door
# aster_results_export.py binnen de Code-Aster-job) in de <solution> van de
# model-.liml, zodat Mecway de resultaten met mw.open() inleest; haalt
# resultaten uit de .liml (strip_results), controleert of een
# resultaatbestand bij het mesh past en somt ze op (knop Resultaten...); en
# leest als terugval een tijdstap uit het fragment voor de
# solution.set_variable()-route.
#
# ROUTE ("binair"):
#   Code-Aster-job: CALC_CHAMP -> aster_results_export.export_results()
#       -> <werkmap>/<model>_<run_id>_results.xml  (<results
#          precision="single|double">, alle tijdstappen, base64)
#   IronPython:     splice_results(model.liml, fragment, model.liml)
#       -> de .liml (vorige versie .bak) met <solution> = kopie van het
#          model (zonder <fieldvariable>) + het fragment; daarna
#          mw.open(model.liml).
#   Terugval:       read_step(fragment) -> {variabele: [waarde per knoop]}
#       -> solution.set_variable() (alleen knoopwaarden, een tijdstap).
#
# Wat Mecway in <solution> zet (nagelopen in door Mecway 33 opgeslagen
# .liml-bestanden, zie TestFiles/): een kopie van alle top-level elementen
# van het model op het moment van oplossen (analysis, timesteps, node,
# elset/elem, belastingen, mat, selecties, ...), behalve <fieldvariable>
# (weergave-instellingen), met dezelfde opmaak twee spaties dieper, en als
# laatste <results>. <solution> is het laatste kind van <liml>.
#
# BESTANDSGROOTTES (gemeten, Code-Aster 17.4, STAT_NON_LINE op een hex8-
# blok van 18.225 knopen, 51 gearchiveerde tijdstappen; DEPL, SIGM_NOEU,
# SIEQ_NOEU en REAC_NODA = 13 componenten, 15 Mecway-variabelen):
#   .resu (POST_RELEVE_T TOUT_ORDRE + IMPR_TABLE)  644 MB, ~53 bytes/waarde,
#                                       ~80 s CPU voor tabellen + schrijven
#   study.rmed (IMPR_RESU MED, double)  217 MB (incl. 17 SIEQ-componenten)
#   resu_mesh.msh (IMPR_RESU GMSH)      3,4 GB, 159 s CPU
#   fragment (export_results, single)   78 MB, ~5,6 bytes/waarde, 1,6 s
#   splice_results (IronPython)         0,9 s; read_step: 1,8 s
# Schatting ProfielBuigen (17.418 knopen, 101 stappen): fragment met 26
# variabelen ~0,26 GB; .resu-tekst met ~20 componenten ~1,9 GB.
#
# Compatibel met IronPython 2.7.9 (alleen de standaardbibliotheek).

import array
import base64
import io
import os
import re

from bridge_utils import tr, choose_configuration, configuration_warning


_CHUNK = 4 * 1024 * 1024


# ==========================================
# POSITIES IN DE .LIML (zonder het hele bestand te lezen)
# ==========================================
def _find_solution_start(path, begin=0):
    """
    Byte-positie van '<solution' (als element: gevolgd door '>', '/' of
    spatie) vanaf byte begin, of -1. Leest in blokken; het model voor
    <solution> is klein, een oude solution kan honderden MB zijn.
    """
    return _find_from(path, "<solution", begin, ">/ \t\r\n")


def _find_from(path, pat, begin=0, follow=None):
    """Byte-positie van pat vanaf byte begin, of -1. Met follow: alleen
    als het teken na pat daarin staat (een element, geen langere naam)."""
    offset = begin
    keep = ""
    f = open(path, "rb")
    try:
        f.seek(begin)
        while True:
            block = f.read(_CHUNK)
            if not block:
                return -1
            buf = keep + block
            start = 0
            while True:
                i = buf.find(pat, start)
                if i < 0 or i + len(pat) >= len(buf):
                    break
                if follow is None or buf[i + len(pat)] in follow:
                    return offset - len(keep) + i
                start = i + 1
            keep = buf[-(len(pat) + 1):]
            offset += len(block)
    finally:
        f.close()


def _find_last(path, pat):
    """Byte-positie van het laatste voorkomen van pat, of -1 (zoekt vanaf
    het eind in blokken)."""
    size = os.path.getsize(path)
    f = open(path, "rb")
    try:
        end = size
        tail = ""
        while end > 0:
            start = max(0, end - _CHUNK)
            f.seek(start)
            buf = f.read(end - start) + tail
            i = buf.rfind(pat)
            if i >= 0:
                return start + i
            tail = buf[:len(pat)]
            end = start
        return -1
    finally:
        f.close()


def _read_range(path, start, end):
    f = open(path, "rb")
    try:
        f.seek(start)
        return f.read(end - start)
    finally:
        f.close()


def _copy_range(src, dst_file, start, end):
    """Kopieer de bytes [start, end) van src naar het open dst_file."""
    f = open(src, "rb")
    try:
        f.seek(start)
        left = end - start
        while left > 0:
            block = f.read(min(_CHUNK, left))
            if not block:
                break
            dst_file.write(block)
            left -= len(block)
    finally:
        f.close()


def _copy_from(src, dst_file, start):
    """Kopieer src vanaf byte start tot het eind naar het open dst_file."""
    f = open(src, "rb")
    try:
        f.seek(start)
        while True:
            block = f.read(_CHUNK)
            if not block:
                break
            dst_file.write(block)
    finally:
        f.close()


# ==========================================
# MODELKOPIE VOOR <solution>
# ==========================================
_FIELDVAR_OPEN = re.compile(r"^\s*<fieldvariable[\s>/]")


def _model_copy(head, nl):
    """
    Regels van de modelkopie in <solution>: de top-level elementen uit head
    (de tekst tussen <liml ...> en <solution>/</liml>) twee spaties dieper,
    zonder <fieldvariable>.

    Inspringen alleen op regels die met een tag beginnen terwijl de vorige
    regel op '>' eindigt; vervolgregels van meerregelige tekst (comment,
    radiossmodeldefinition) blijven ongewijzigd, zoals Mecway's eigen kopie.
    """
    body = head[head.index(">", head.index("<liml")) + 1:]
    lines = body.split(nl)
    if lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines.pop()
    out = []
    prev_tag_end = True
    skipping = False
    for line in lines:
        starts_tag = prev_tag_end and line.lstrip().startswith("<")
        if starts_tag and not skipping and _FIELDVAR_OPEN.match(line):
            skipping = not line.rstrip().endswith("/>")
            prev_tag_end = line.rstrip().endswith(">")
            continue
        if skipping:
            if "</fieldvariable>" in line:
                skipping = False
            prev_tag_end = line.rstrip().endswith(">")
            continue
        out.append(("  " + line) if starts_tag else line)
        prev_tag_end = line.rstrip().endswith(">")
    return out


def _newline(text):
    return "\r\n" if "\r\n" in text else "\n"


# ==========================================
# CYCLISCHE SYMMETRIE: HET HELE WIEL IN DE MODELKOPIE (S10i)
#
# Mecway's eigen cyclische oplossing (headless gemeten met Mecway 33,
# details in aster_cyclic.py): de modelkopie in <solution> heeft N kopieen
# van de knopen en elementen. Knoop i van sector j (0 .. N-1) heet
# i + j x n, gedraaid over +j x 360/N graden om de as door de oorsprong;
# element e heet e + j x ne (ne = hoogste elementnummer), met de knopen van
# zijn sector; per elset staan de elementen per sector achter elkaar. De
# extra knopen staan direct na de laatste knoop van het model, de extra
# elementen aan het eind van hun elset; de rest van de kopie (selecties,
# belastingen, <cyclicsymmetry>) blijft die van de sector. Coordinaten met
# 15 significante cijfers ("0.428682574873297", "4.22074656910206E-21"),
# zoals Mecway.
# ==========================================
_CYCLIC = re.compile(r"<cyclicsymmetry\b([^>]*)>")
_NODE_LINE = re.compile(r'^(\s*)<node\s+nid="(\d+)"\s+x="([^"]*)"\s+'
                        r'y="([^"]*)"\s+z="([^"]*)"\s*/>\s*$')
_ELEM_LINE = re.compile(r'^(\s*<elem\s+eid=")(\d+)("[^>]*\bnodes=")'
                        r'([^"]*)(".*)$')


def cyclic_info(head):
    """(as 0/1/2, segmenten) van de eerste <cyclicsymmetry> die niet
    onderdrukt is in de modeltekst head, of None."""
    import bridge_cyclic
    for m in _CYCLIC.finditer(head):
        attrs = dict(_ATTR.findall(m.group(1)))
        if attrs.get("suppressed", "") == "true":
            continue
        axis = bridge_cyclic.axis_index(attrs.get("axis", "3"))
        try:
            segments = int(float(attrs.get("segments", "0")))
        except ValueError:
            segments = 0
        if axis is not None and segments >= 2:
            return axis, segments
    return None


def _coord(v):
    """Coordinaat zoals Mecway (15 significante cijfers, "0" voor 0)."""
    if v == 0.0:
        return "0"
    return "%.15G" % v


def _wheel_copy(lines, segments, axis):
    """
    De regels van de modelkopie (_model_copy) uitgebreid tot het hele wiel
    (zie de kop van dit blok). Returns (regels, n, ne).
    """
    import math
    nodes = {}
    last_node = -1
    max_eid = 0
    for k, line in enumerate(lines):
        m = _NODE_LINE.match(line)
        if m:
            nodes[int(m.group(2))] = (m.group(1), float(m.group(3)),
                                      float(m.group(4)), float(m.group(5)))
            last_node = k
            continue
        m = _ELEM_LINE.match(line)
        if m:
            max_eid = max(max_eid, int(m.group(2)))
    n = max(nodes) if nodes else 0
    i, k2 = (axis + 1) % 3, (axis + 2) % 3
    extra_nodes = []
    for j in range(1, segments):
        a = 2.0 * math.pi * j / segments
        c, s = math.cos(a), math.sin(a)
        for nid in sorted(nodes):
            indent, x, y, z = nodes[nid]
            p = [x, y, z]
            q = list(p)
            q[i] = c * p[i] - s * p[k2]
            q[k2] = s * p[i] + c * p[k2]
            extra_nodes.append('{0}<node nid="{1}" x="{2}" y="{3}" z="{4}" />'
                               .format(indent, nid + j * n, _coord(q[0]),
                                       _coord(q[1]), _coord(q[2])))
    out = []
    elems = None            # elem-regels van de lopende <elset>
    for k, line in enumerate(lines):
        stripped = line.strip()
        if elems is not None and stripped.startswith("</elset>"):
            for j in range(1, segments):
                for m in elems:
                    out.append("{0}{1}{2}{3}{4}".format(
                        m.group(1), int(m.group(2)) + j * max_eid,
                        m.group(3), " ".join(str(int(v) + j * n)
                                             for v in m.group(4).split()),
                        m.group(5)))
            elems = None
        elif stripped.startswith("<elset") and not stripped.endswith("/>"):
            elems = []
        elif elems is not None:
            m = _ELEM_LINE.match(line)
            if m:
                elems.append(m)
        out.append(line)
        if k == last_node:
            out.extend(extra_nodes)
    return out, n, max_eid


def _wheel_check(head, fragment_path):
    """
    (info, fout) voor modeltekst head en resultaatbestand fragment_path:
    info = (as, N) als het resultaat het hele wiel van een cyclisch model
    is (knoopnummers boven het aantal knopen n van het model, tot N x n;
    aster_results_export met cyclic=...), anders None; fout = melding als
    de knoopnummers niet bij het model passen.
    """
    nids, _eids = _fragment_ids(fragment_path)
    n = len(set(_NODE_TAG.findall(head)))
    if not nids or max(nids) <= n:
        return None, None
    info = cyclic_info(head)
    if info is None or max(nids) > info[1] * n:
        return None, tr(
            "Het resultaat hoort bij een mesh met (minstens) {0} knopen; het "
            "model heeft er {1}.",
            "The result belongs to a mesh with (at least) {0} nodes; the "
            "model has {1}.").format(max(nids), n)
    return info, None


def wheel_segments(model_liml, fragment_path):
    """Aantal segmenten N als resultaatbestand fragment_path het hele wiel
    van het cyclische model model_liml is (_wheel_check), anders None."""
    sol = _find_solution_start(model_liml)
    head = _read_range(model_liml, 0, sol if sol >= 0 else
                       os.path.getsize(model_liml))
    info, _err = _wheel_check(head, fragment_path)
    return info[1] if info else None


# ==========================================
# SPLICE
# ==========================================
_CONF_ATTR = re.compile(r'\bconfiguration="([^"]*)"')
_CONF_NAME = re.compile(r'<configuration\s+name="([^"]*)"')
_SUPPRESSED_IN = re.compile(r'<suppressed\s+configuration="([^"]*)"')


def _solutions(path, first):
    """
    [(begin, eind, configuratie of None)] van de top-level <solution>-
    elementen vanaf byte first (de eerste <solution>). Mecway zet ze
    achter elkaar als laatste kinderen van <liml>, een per configuratie
    (<solution configuration="naam">, Samples/CylinderLifting.liml en
    Tutorials/AssemblyWithContact.liml); zonder configuraties een
    <solution> zonder attribuut. Streaming: alleen starttags en
    sluittags worden gezocht.
    """
    out = []
    pos = first
    while pos >= 0:
        tag = _read_range(path, pos, pos + 1024)
        close = tag.find(">")
        if close < 0:
            break
        m = _CONF_ATTR.search(tag[:close])
        conf = m.group(1) if m else None
        if tag[close - 1] == "/":                # <solution ... />
            end = pos + close + 1
        else:
            end = _find_from(path, "</solution>", pos + close)
            if end < 0:
                break
            end += len("</solution>")
        out.append((pos, end, conf))
        pos = _find_solution_start(path, end)
    return out


def _model_head(model_liml):
    """Het model voor de eerste <solution> (klein; een oude solution kan
    honderden MB zijn)."""
    sol = _find_solution_start(model_liml)
    return _read_range(model_liml, 0, sol if sol >= 0 else
                       os.path.getsize(model_liml))


def configuration_names(model_liml):
    """Namen van de configuraties van het model (<configuration
    name="..">), in volgorde; [] zonder configuraties of als het bestand
    niet te lezen is. Voor de keuzelijst Configuratie op het startscherm."""
    try:
        return _CONF_NAME.findall(_model_head(model_liml))
    except (IOError, OSError):
        return []


def pick_configuration(model_liml):
    """
    (configuratie, melding) voor splice_results. Zonder <configuration> in
    het model (None, ""). De Mecway-API kan de actieve configuratie niet
    lezen (alleen mw.set_active_configuration); de keuze komt uit
    bridge_utils.choose_configuration (instelling "configuration" of de
    regel daar), dezelfde als bridge_from_liml._pick_configuration voor de
    lasten. melding: WARNING-tekst (zonder "WARNING: ") voor de log, of ""
    als de keuze eenduidig is. De solutions van andere configuraties
    blijven ongewijzigd (splice_results).
    """
    head = _model_head(model_liml)
    names = _CONF_NAME.findall(head)
    suppressed = set(_SUPPRESSED_IN.findall(head))
    configuration, how, missing = choose_configuration(names, suppressed)
    if configuration is None:
        return None, ""
    return configuration, configuration_warning(names, configuration, how,
                                                missing)


def splice_results(model_liml, fragment_path, out_path, configuration=None):
    """
    Schrijf out_path = model_liml met een nieuwe <solution> (modelkopie +
    fragment). Alles buiten die <solution> blijft byte-gelijk, ook de
    solutions van andere configuraties. configuration: naam (zie
    pick_configuration) of None (model zonder configuraties: de solution
    zonder attribuut). Een bestaand out_path wordt out_path + ".bak"; er
    wordt eerst naar out_path + ".tmp" geschreven. out_path mag gelijk zijn
    aan model_liml.

    Is het fragment het hele wiel van een cyclisch model (aster_results_
    export met cyclic=...), dan krijgt de modelkopie de knopen en
    elementen van alle sectoren, zoals Mecway (_wheel_copy).

    Returns
    -------
    (bool, str) - (True, "") of (False, reden).
    """
    if not os.path.exists(model_liml):
        return False, tr("Model niet gevonden: {0}",
                         "Model not found: {0}").format(model_liml)
    if not os.path.exists(fragment_path) or \
            os.path.getsize(fragment_path) == 0:
        return False, tr("Fragment ontbreekt of is leeg: {0}",
                         "Fragment is missing or empty: {0}").format(
            fragment_path)

    sol = _find_solution_start(model_liml)
    open_tag = ("<solution>" if configuration is None else
                '<solution configuration="{0}">'.format(configuration))
    if sol >= 0:
        head = _read_range(model_liml, 0, sol)
        sols = _solutions(model_liml, sol)
        if not sols:
            return False, tr("<solution> zonder einde in {0}",
                             "<solution> without end in {0}").format(
                model_liml)
        same = [s for s in sols if s[2] == configuration]
        if not same and configuration is not None:
            # Solution zonder configuratie (oudere bridge-versie) vervangen
            same = [s for s in sols if s[2] is None]
        if same:
            # Bestaande solution vervangen; de rest blijft staan.
            begin, tail_start = same[0][0], same[0][1]
            indent = ""      # de tekst ervoor eindigt op de inspringing
            lead = ""
        else:
            # Nieuwe solution achter de laatste.
            begin = tail_start = sols[-1][1]
            indent = "  "
            lead = None
    else:
        tail_start = _find_last(model_liml, "</liml>")
        if tail_start < 0:
            return False, tr("Geen </liml> in {0}",
                             "No </liml> in {0}").format(model_liml)
        head = _read_range(model_liml, 0, tail_start)
        begin = tail_start
        indent = "  "
        lead = ""
    nl = _newline(head)
    if lead is None:
        lead = nl
    copy_lines = _model_copy(head, nl)
    wheel, err = _wheel_check(head, fragment_path)
    if err:
        return False, err
    if wheel:
        # Cyclische symmetrie: het hele wiel, zoals Mecway's eigen oplossing
        copy_lines = _wheel_copy(copy_lines, wheel[1], wheel[0])[0]

    tmp = out_path + ".tmp"
    f = open(tmp, "wb")
    try:
        _copy_range(model_liml, f, 0, begin)
        f.write(lead + indent + open_tag + nl)
        f.write(nl.join(copy_lines) + nl)
        _copy_from(fragment_path, f, 0)
        f.write("  </solution>")
        if sol < 0:
            f.write(nl)
        _copy_from(model_liml, f, tail_start)
    finally:
        f.close()

    _replace_with_bak(tmp, out_path)
    return True, ""


def _replace_with_bak(tmp, out_path):
    """out_path -> out_path.bak (een oude .bak vervalt), tmp -> out_path."""
    if os.path.exists(out_path):
        bak = out_path + ".bak"
        if os.path.exists(bak):
            os.remove(bak)
        os.rename(out_path, bak)
    os.rename(tmp, out_path)


# ==========================================
# RESULTATEN UIT DE .LIML HALEN (kleine .liml)
# ==========================================
def strip_results(model_liml):
    """
    Verwijder alle <solution>-elementen (resultaten, ook die van andere
    configuraties) uit model_liml; het model zelf blijft byte-gelijk. Zo
    blijft de .liml klein; de resultaten van een bridge-run staan in
    <model>_<run_id>_results.xml en zijn met splice_results opnieuw in te
    laden. Vorige versie: model_liml.bak.

    Returns
    -------
    (bool, str) - (True, "") of (False, reden).
    """
    if not os.path.exists(model_liml):
        return False, tr("Model niet gevonden: {0}",
                         "Model not found: {0}").format(model_liml)
    sol = _find_solution_start(model_liml)
    if sol < 0:
        return False, tr("Het model bevat geen resultaten.",
                         "The model contains no results.")
    sols = _solutions(model_liml, sol)
    if not sols:
        return False, tr("<solution> zonder einde in {0}",
                         "<solution> without end in {0}").format(model_liml)
    tmp = model_liml + ".tmp"
    f = open(tmp, "wb")
    try:
        pos = 0
        for begin, end, _conf in sols:
            # De regel van <solution> helemaal weg: inspringing en de
            # regelovergang ervoor horen erbij.
            before = _read_range(model_liml, max(pos, begin - 256), begin)
            cut = begin - (len(before) - len(before.rstrip(" \t")))
            prev = _read_range(model_liml, max(pos, cut - 2), cut)
            if prev.endswith("\r\n"):
                cut -= 2
            elif prev.endswith("\n"):
                cut -= 1
            _copy_range(model_liml, f, pos, cut)
            pos = end
        _copy_from(model_liml, f, pos)
    finally:
        f.close()
    _replace_with_bak(tmp, model_liml)
    return True, ""


# ==========================================
# RESULTAATBESTANDEN IN DE WERKMAP
# ==========================================
RESULTS_SUFFIX = "_results.xml"     # <model>_<run_id>_results.xml
_RUN_STEM = re.compile(r"^(.*)_(\d{8}_\d{6})$")   # <model>_<run_id>
_COMM_LIML = re.compile(r"export_results\(\s*res,\s*r'[^']*',\s*r'([^']*)'")


def run_files(results_path):
    """
    Bestanden van dezelfde run als results_path
    (<model>_<run_id>_results.xml): {"run_id", "comm", "mail", "model"}.
    "mail" is het mesh van de run (<model>_<run_id>.mail, of een ander
    *_<run_id>.mail van een oudere versie; anders None), "model" de .liml
    waarvoor de run rekende, gelezen uit de .comm (of "").
    """
    folder = os.path.dirname(os.path.abspath(results_path))
    name = os.path.basename(results_path)
    stem = name[:-len(RESULTS_SUFFIX)] if name.endswith(RESULTS_SUFFIX)         else os.path.splitext(name)[0]
    m = _RUN_STEM.match(stem)
    run_id = m.group(2) if m else ""
    info = {"run_id": run_id, "comm": os.path.join(folder, stem + ".comm"),
            "mail": None, "model": ""}
    mail = os.path.join(folder, stem + ".mail")
    if os.path.exists(mail):
        info["mail"] = mail
    elif run_id:
        try:
            for n in os.listdir(folder):
                if n.endswith("_{0}.mail".format(run_id)):
                    info["mail"] = os.path.join(folder, n)
                    break
        except OSError:
            pass
    try:
        f = open(info["comm"], "r")
        try:
            m = _COMM_LIML.search(f.read())
        finally:
            f.close()
        if m:
            info["model"] = m.group(1)
    except (IOError, OSError):
        pass
    return info


def list_results(work_dir):
    """
    Resultaatbestanden in work_dir, nieuwste eerst: lijst van dicts
    {"path", "size", "mtime"} plus de sleutels van run_files().
    """
    out = []
    try:
        names = os.listdir(work_dir)
    except OSError:
        return out
    for n in names:
        if not n.endswith(RESULTS_SUFFIX):
            continue
        path = os.path.join(work_dir, n)
        item = run_files(path)
        item.update({"path": path, "size": os.path.getsize(path),
                     "mtime": os.path.getmtime(path)})
        out.append(item)
    out.sort(key=lambda d: d["mtime"], reverse=True)
    return out


# ==========================================
# PAST EEN RESULTAATBESTAND BIJ HET MODEL?
# ==========================================
_NODE_TAG = re.compile(r'<node\s+nid="(\d+)"\s+x="([^"]*)"\s+y="([^"]*)"'
                       r'\s+z="([^"]*)"')
_ELEM_ID = re.compile(r'<elem\s+eid="(\d+)"')
_MAIL_NODE = re.compile(r'^\s*N(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$')


def _model_mesh(model_liml):
    """({nid: (x, y, z)}, set van eid) van het model (vóór <solution>)."""
    sol = _find_solution_start(model_liml)
    head = _read_range(model_liml, 0, sol if sol >= 0 else
                       os.path.getsize(model_liml))
    nodes = {}
    for m in _NODE_TAG.finditer(head):
        nodes[int(m.group(1))] = (float(m.group(2)), float(m.group(3)),
                                  float(m.group(4)))
    return nodes, set(int(e) for e in _ELEM_ID.findall(head))


def _fragment_ids(fragment_path):
    """(set van knoopnummers, set van elementnummers) uit de <nodeids>/
    <elementnodeids> van een resultaatbestand. Die staan vooraan
    (aster_results_export._write_fragment); er wordt gelezen tot de eerste
    tijdstap of variabele."""
    nids = set()
    eids = set()
    chunks = None
    kind = None
    f = open(fragment_path, "rb")
    try:
        for line in f:
            if chunks is None:
                m = _OPEN_TAG.search(line)
                if m is None:
                    continue
                kind = m.group(1)
                if kind in ("timestep", "mode", "nodevariable",
                            "elementnodevariable"):
                    break
                if kind not in ("nodeids", "elementnodeids"):
                    continue
                chunks = []
                line = line[m.end():]
            _collect(line, chunks)
            if "<" in line:
                ids = _decode(chunks, "i")
                if kind == "nodeids":
                    nids.update(ids)
                else:
                    eids.update(ids)
                chunks = None
    finally:
        f.close()
    return nids, eids


def _mail_coords(mail_path):
    """{nid: (x, y, z)} uit het COOR_3D-blok van een .mail-bestand."""
    coords = {}
    inside = False
    f = open(mail_path, "r")
    try:
        for line in f:
            word = line.strip()
            if word == "COOR_3D":
                inside = True
                continue
            if inside:
                if word == "FINSF":
                    break
                m = _MAIL_NODE.match(line)
                if m:
                    coords[int(m.group(1))] = (float(m.group(2)),
                                               float(m.group(3)),
                                               float(m.group(4)))
    finally:
        f.close()
    return coords


def _worst_node(nodes, coords):
    """(grootste coordinaatverschil, knoop) tussen nodes en coords
    ({nid: (x, y, z)})."""
    worst, worst_nid = 0.0, None
    for nid, xyz in nodes.items():
        d = max(abs(a - b) for a, b in zip(xyz, coords[nid]))
        if d > worst:
            worst, worst_nid = d, nid
    return worst, worst_nid


def check_results_fit(model_liml, fragment_path, mail_path=None):
    """
    Past resultaatbestand fragment_path bij het mesh van model_liml?
    Resultaten op een ander mesh zouden stil op verkeerde knopen landen.
    Controle: knoop- en elementnummers van het resultaat bestaan in het
    model; met mail_path (het .mail-bestand van dezelfde run) ook de
    knoopcoördinaten.

    Returns
    -------
    (bool, str) - (past, melding). Bij True kan de melding een
    waarschuwing zijn (bijv. geen .mail om de coördinaten te vergelijken).
    """
    nodes, model_eids = _model_mesh(model_liml)
    nids, eids = _fragment_ids(fragment_path)
    if not nids and not eids:
        return False, tr("Geen resultaten gevonden in {0}.",
                         "No results found in {0}.").format(fragment_path)
    head = _model_head(model_liml)
    wheel, err = _wheel_check(head, fragment_path)
    if err:
        return False, err
    if wheel:
        # Hele wiel van een cyclisch model: de knopen van sector 0 zijn die
        # van het model (de coordinaten hieronder); de andere sectoren
        # volgen uit de draaiing (_wheel_copy).
        n = max(nodes) if nodes else 0
        nids = set(k for k in nids if k <= n)
    if not nids.issubset(nodes):
        return False, tr(
            "Het resultaat hoort bij een mesh met (minstens) {0} knopen; het "
            "model heeft er {1}.",
            "The result belongs to a mesh with (at least) {0} nodes; the "
            "model has {1}.").format(max(nids), len(nodes))
    missing = eids - model_eids
    if missing:
        return False, tr(
            "{0} elementen van het resultaat bestaan niet in het model "
            "(bijv. {1}).",
            "{0} elements of the result do not exist in the model "
            "(e.g. {1}).").format(len(missing), min(missing))
    if not (mail_path and os.path.exists(mail_path)):
        return True, tr(
            "Mesh-bestand van deze run niet gevonden; alleen knoop- en "
            "elementnummers gecontroleerd, niet de coördinaten.",
            "Mesh file of this run not found; only node and element "
            "numbers checked, not the coordinates.")
    coords = _mail_coords(mail_path)
    if set(coords) != set(nodes):
        return False, tr(
            "Het mesh van de run ({0} knopen) verschilt van het model "
            "({1} knopen).",
            "The mesh of the run ({0} nodes) differs from the model "
            "({1} nodes).").format(len(coords), len(nodes))
    span = max([abs(c) for xyz in nodes.values() for c in xyz] + [1e-30])
    worst, worst_nid = _worst_node(nodes, coords)
    cyc = cyclic_info(head)
    if worst > 1e-6 * span and cyc is not None and cyc[0] != 2:
        # Cyclische symmetrie om X of Y: het .mail van de run staat in het
        # rekenframe (as -> Z, bridge_cyclic._rewrite_mesh); terugdraaien.
        # Alleen een modale run draait (bridge_cyclic.build_cyclic_modes),
        # daarom beide frames proberen.
        import bridge_cyclic
        back = dict((nid, bridge_cyclic.to_model_frame(xyz, cyc[0]))
                    for nid, xyz in coords.items())
        worst_b, nid_b = _worst_node(nodes, back)
        if worst_b < worst:
            worst, worst_nid = worst_b, nid_b
    if worst > 1e-6 * span:
        return False, tr(
            "Knoop {0} ligt in het model anders dan in de run (verschil "
            "{1}); het mesh is gewijzigd.",
            "Node {0} is in a different position in the model than in the "
            "run (difference {1}); the mesh has changed.").format(
                worst_nid, "%.3g" % worst)
    return True, ""


# ==========================================
# TERUGVAL: EEN TIJDSTAP LEZEN
# ==========================================
_OPEN_TAG = re.compile(r'<(results|nodeids|elementnodeids|timestep|mode|'
                       r'nodevariable|elementnodevariable|valuessingle|'
                       r'valuesdouble)\b([^>]*)>')
_ATTR = re.compile(r'(\w+)="([^"]*)"')


def read_step(fragment_path, step=-1, n_nodes=None):
    """
    Lees de knoopvariabelen van een tijdstap uit een results-fragment (of
    een .liml met <results>). Regel voor regel: werkt ook voor fragmenten
    van honderden MB.

    Parameters
    ----------
    step    : tijdstap-id (of mode-id bij <mode>, vanaf 1); -1 = de
              laatste. Zonder <timestep>/<mode> (statisch) wordt step
              genegeerd.
    n_nodes : lengte van de lijsten (aantal knopen van de solution); None =
              hoogste knoopnummer in het fragment.

    Returns
    -------
    dict {Mecway-variabele: [waarde of None per knoop 1..n]} - het formaat
    van solution.set_variable(). Elementknoopvariabelen worden
    overgeslagen.
    """
    ids = {}            # naam -> base64-regels van <nodeids>
    values = {}         # naam -> base64-regels in de gekozen tijdstap
    typecode = "f"
    keep = True         # hoort de lopende tijdstap bij de gevraagde?
    var = None          # lopende <nodevariable>, None in elementvariabelen
    target = None       # lijst waarin base64-regels worden verzameld
    f = open(fragment_path, "rb")
    try:
        for line in f:
            if target is not None:
                _collect(line, target)
                if "<" in line:
                    target = None
                continue
            m = _OPEN_TAG.search(line)
            if m is None:
                continue
            kind, attrs = m.group(1), dict(_ATTR.findall(m.group(2)))
            sink = None
            if kind == "results":
                typecode = "d" if attrs.get("precision") == "double" else "f"
            elif kind in ("timestep", "mode"):
                keep = step == -1 or int(attrs.get("id", -2)) == step
                if keep:
                    values = {}
            elif kind == "nodevariable":
                var = attrs.get("name")
            elif kind == "elementnodevariable":
                var = None
            elif kind == "nodeids":
                sink = ids.setdefault(attrs.get("name"), [])
            elif kind == "elementnodeids":
                sink = []
            else:   # valuessingle / valuesdouble
                sink = values.setdefault(var, []) if (keep and var) else []
            if sink is not None:
                rest = line[m.end():]
                _collect(rest, sink)
                if "<" not in rest:
                    target = sink
    finally:
        f.close()
    return _to_node_lists(ids, values, typecode, n_nodes)


_MODE_TAG = re.compile(r'<mode\s+id="(\d+)"\s+(frequency|bucklingfactor)='
                       r'"([-+0-9.eEinfINFaA]+)')


def read_modes(fragment_path):
    """
    Modes in een resultaatbestand (modaal/knik, aster_results_export):
    lijst van (id, soort, waarde) met soort "frequency" (Hz) of
    "bucklingfactor"; leeg zonder <mode>. Regel voor regel (de <mode>-
    regels staan los van de base64-regels).
    """
    out = []
    f = open(fragment_path, "rb")
    try:
        for line in f:
            if "<mode" not in line:
                continue
            m = _MODE_TAG.search(line)
            if m:
                out.append((int(m.group(1)), m.group(2), float(m.group(3))))
    finally:
        f.close()
    return out


_MESS_MODE = re.compile(r"^BRIDGE_MODE\s+(\d+)\s+(.*)$")
_MESS_MASS = re.compile(r"^BRIDGE_MASSA\s+(.*)$")


def _key_values(text):
    """{sleutel: float of tekst} uit 'A=1 B=2 C=x,y,z'."""
    values = {}
    for part in text.split():
        if "=" in part:
            key, val = part.split("=", 1)
            try:
                values[key] = float(val)
            except ValueError:
                values[key] = val
    return values


def read_mode_summary(mess_path):
    """
    {mode: {parameter: waarde}} uit de BRIDGE_MODE-regels die
    aster_results_export.print_modes in de .mess zet (FREQ,
    MASS_EFFE_UN_DX/DY/DZ, MASS_EFFE_UN_DRX/DRY/DRZ of CHAR_CRIT); {} als
    ze ontbreken. Onder de sleutel "massa" de BRIDGE_MASSA-regel (M, JX,
    JY, JZ, ZWP als tekst "x,y,z", JZX, JZY, JZZ), als die er is.
    """
    out = {}
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = open(mess_path, "rb")
    try:
        for line in f:
            if not isinstance(line, str):     # CPython 3 (verificatie)
                line = line.decode("utf-8", "replace")
            m = _MESS_MODE.match(line.strip())
            if m:
                out[int(m.group(1))] = dict(
                    (k, v) for k, v in _key_values(m.group(2)).items()
                    if isinstance(v, float))
                continue
            m = _MESS_MASS.match(line.strip())
            if m:
                out["massa"] = _key_values(m.group(1))
    finally:
        f.close()
    return out


_MESS_CYCL = re.compile(r"^BRIDGE_CYCL\s+(.*)$")


def read_cyclic_summary(mess_path):
    """{N, NMAX_FREQ, MODES, WIEL} uit de regel BRIDGE_CYCL van
    aster_cyclic.collect (WIEL = 1: de modes staan op het hele wiel), of
    {} zonder die regel."""
    if not mess_path or not os.path.exists(mess_path):
        return {}
    out = {}
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            m = _MESS_CYCL.match(line.strip())
            if m:
                out = _key_values(m.group(1))
    finally:
        f.close()
    return out


# Globale fout van CALC_ERREUR ERME in de .mess (Code-Aster 17.4, gezien):
#    MECANIQUE : ESTIMATEUR D'ERREUR EN RESIDU EXPLICITE
#    ...
#  NUMERO D'ORDRE:     1
#  ERREUR            ABSOLUE         RELATIVE   NORME DE SIGMA
#  TOTALE            1.51459146D+06  61.083 %   1.96324245D+06
#  TERME VOLUMIQUE   7.37849403D+05  35.181 %
#  TERME SAUT        4.62616959D+05  22.936 %
#  TERME NORMAL      3.30403568D+05  16.596 %
# RELATIVE = 100 eta / sqrt(eta^2 + norm(sigma)^2) (nagerekend uit ERME_ELEM,
# zie bridge_to_aster._error_estimator_block).
_ERR_HEAD = "ESTIMATEUR D'ERREUR EN RESIDU"
_ERR_ORDER = re.compile(r"NUMERO D'ORDRE:\s*(\d+)")
_ERR_ROW = re.compile(r"^\s*(TOTALE|TERME VOLUMIQUE|TERME SAUT|TERME NORMAL)\s+"
                      r"([-+0-9.EeDd]+)\s+([-+0-9.EeDd]+)\s*%(?:\s+([-+0-9.EeDd]+))?")
_ERR_KEYS = {"TOTALE": "total", "TERME VOLUMIQUE": "volume",
             "TERME SAUT": "jump", "TERME NORMAL": "boundary"}


def _fortran_float(text):
    return float(text.replace("D", "E").replace("d", "e"))


def read_error_summary(mess_path):
    """
    Globale foutschatting per numero d'ordre uit de .mess: lijst van dicts
    {"order": n, "abs": eta, "rel": %, "sigma": norm van sigma, "volume":
    %, "jump": %, "boundary": %} in volgorde van de .mess; [] zonder
    foutschatter. Alleen het mechanische blok (MECANIQUE).
    """
    out = []
    if not mess_path or not os.path.exists(mess_path):
        return out
    # io.open met UTF-8: de .mess bevat Franse accenten; zo ook bruikbaar
    # in CPython (verificatie, TestFiles/Verificatie/verif_lib.py).
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        current = None
        for line in f:
            if _ERR_HEAD in line:
                current = {} if "MECANIQUE" in line else None
                continue
            if current is None:
                continue
            m = _ERR_ORDER.search(line)
            if m:
                current["order"] = int(m.group(1))
                continue
            m = _ERR_ROW.match(line)
            if not m:
                continue
            key = _ERR_KEYS[m.group(1)]
            try:
                if key == "total":
                    current["abs"] = _fortran_float(m.group(2))
                    current["rel"] = _fortran_float(m.group(3))
                    if m.group(4):
                        current["sigma"] = _fortran_float(m.group(4))
                else:
                    current[key] = _fortran_float(m.group(3))
            except ValueError:
                continue
            if key == "boundary":
                if "rel" in current:
                    out.append(current)
                current = None
    finally:
        f.close()
    return out


# Niet-lineaire knik (bridge_to_aster._crit_stab_report,
# _imperfection_blocks): regels die de Code-Aster-job in de .mess zet.
_CS_KIND = re.compile(r"^BRIDGE_CRIT_STAB_SOORT\s+(\w+)")
_CS_ROW = re.compile(r"^BRIDGE_CRIT_STAB\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)")
_IMP_MODE = re.compile(r"^BRIDGE_IMPERFECTIE_MODE\s+(\d+)\s+([-+0-9.eE]+)")
_IMP = re.compile(r"^BRIDGE_IMPERFECTIE\s+(\d+)\s+([-+0-9.eE]+)")


def read_crit_stab(mess_path):
    """
    Stabiliteitscriterium per stap (CRIT_STAB) uit de .mess:
    {"kind": "factor" | "eigen", "rows": [(t, lambda)], "missing": tekst
    of None}; None als CRIT_STAB niet aan stond. Betekenis van lambda:
    bridge_to_aster._crit_stab_kind.
    """
    if not mess_path or not os.path.exists(mess_path):
        return None
    out = None
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            line = line.strip()
            if not line.startswith("BRIDGE_CRIT_STAB"):
                continue
            m = _CS_KIND.match(line)
            if m:
                out = {"kind": m.group(1), "rows": [], "missing": None}
                continue
            if out is None:
                continue
            if line.startswith("BRIDGE_CRIT_STAB_GEEN"):
                out["missing"] = line[len("BRIDGE_CRIT_STAB_GEEN"):].strip()
                continue
            m = _CS_ROW.match(line)
            if m:
                out["rows"].append((float(m.group(1)), float(m.group(2))))
    finally:
        f.close()
    if out is not None:
        out["rows"].sort()
    return out


def crit_stab_estimate(rows):
    """
    Schatting van het knikpunt uit de 'eigen'-reeks (lambda -> 0):
    ("kruising", t) als lambda tussen twee stappen van < 0 naar >= 0 gaat
    (lineair geinterpoleerd); ("extrapolatie", t) als lambda nog < 0 is en
    in de laatste twee stappen stijgt (lineair doorgetrokken naar 0);
    anders None.
    """
    for (t0, l0), (t1, l1) in zip(rows, rows[1:]):
        if l0 < 0.0 <= l1:
            return ("kruising", t0 + (t1 - t0) * (-l0) / (l1 - l0))
    if len(rows) >= 2:
        (t0, l0), (t1, l1) = rows[-2], rows[-1]
        if l1 < 0.0 and l1 > l0 and t1 > t0:
            return ("extrapolatie", t1 + (t1 - t0) * (-l1) / (l1 - l0))
    return None


def read_imperfection(mess_path):
    """
    Imperfectie (knikvorm) uit de .mess: {"mode": k, "amplitude": e0 [m],
    "factors": {mode: kniklastfactor}}; None zonder imperfectie.
    """
    if not mess_path or not os.path.exists(mess_path):
        return None
    out = None
    factors = {}
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            line = line.strip()
            m = _IMP_MODE.match(line)
            if m:
                factors[int(m.group(1))] = float(m.group(2))
                continue
            m = _IMP.match(line)
            if m:
                out = {"mode": int(m.group(1)),
                       "amplitude": float(m.group(2))}
    finally:
        f.close()
    if out is not None:
        out["factors"] = factors
    return out


def _collect(text, buf):
    """Voeg het base64-deel van text (tot een eventuele sluittag) toe."""
    text = text.split("<", 1)[0].strip()
    if text:
        buf.append(text)


def _decode(chunks, typecode):
    a = array.array(typecode)
    a.fromstring(base64.b64decode("".join(chunks)))
    return a


def _to_node_lists(ids, values, typecode, n_nodes):
    """{naam: [waarde of None per knoop]} uit de base64-regels."""
    nids = dict((name, _decode(chunks, "i")) for name, chunks in ids.items())
    if n_nodes is None:
        n_nodes = max([max(a) for a in nids.values() if len(a)] + [0])
    out = {}
    for name, chunks in values.items():
        vals = _decode(chunks, typecode)
        ids_ = nids.get(name)
        if ids_ is None or len(ids_) != len(vals):
            continue
        lst = [None] * n_nodes
        for nid, v in zip(ids_, vals):
            if 1 <= nid <= n_nodes:
                # float(): IronPython geeft uit array('f') een System.Single.
                lst[nid - 1] = float(v)
        out[name] = lst
    return out
