# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_results_liml.py
#
# Responsibility: put a result file (written by aster_results_export.py
# inside the Code-Aster job) into the <solution> of the model .liml, so
# that Mecway reads the results with mw.open(); remove results from the
# .liml (strip_results), check whether a result file matches the mesh and
# list them (Results... button); and, as a fallback, read one time step
# from the fragment for the
# solution.set_variable() route.
#
# ROUTE ("binary"):
#   Code-Aster-job: CALC_CHAMP -> aster_results_export.export_results()
#       -> <work folder>/<model>_<run_id>_results.xml  (<results
#          precision="single|double">, all time steps, base64)
#   IronPython:     splice_results(model.liml, fragment, model.liml)
#       -> the .liml (previous version .bak) with <solution> = copy of the
#          model (without <fieldvariable>) + the fragment; then
#          mw.open(model.liml).
#   Fallback:       read_step(fragment) -> {variable: [value per node]}
#       -> solution.set_variable() (node values only, one time step).
#
# What Mecway puts in <solution> (checked in 33 .liml files saved by
# Mecway, see TestFiles/): a copy of all top-level elements
# of the model at the moment of solving (analysis, timesteps, node,
# elset/elem, loads, mat, selections, ...), except <fieldvariable>
# (display settings), with the same formatting two spaces deeper, and as
# the last one <results>. <solution> is the last child of <liml>.
# With configurations: one <solution configuration="X"> per configuration;
# the bridge replaces only that of the solved configuration, with the
# model copy as Mecway writes it for X (_configuration_copy).
#
# FILE SIZES (measured, Code-Aster 17.4, STAT_NON_LINE on a hex8
# block of 18,225 nodes, 51 archived time steps; DEPL, SIGM_NOEU,
# SIEQ_NOEU and REAC_NODA = 13 components, 15 Mecway variables):
#   .resu (POST_RELEVE_T TOUT_ORDRE + IMPR_TABLE)  644 MB, ~53 bytes/value,
#                                       ~80 s CPU for tables + writing
#   study.rmed (IMPR_RESU MED, double)  217 MB (incl. 17 SIEQ-componenten)
#   resu_mesh.msh (IMPR_RESU GMSH)      3.4 GB, 159 s CPU
#   fragment (export_results, single)   78 MB, ~5.6 bytes/value, 1.6 s
#   splice_results (IronPython)         0.9 s; read_step: 1.8 s
# Estimate ProfielBuigen (17,418 nodes, 101 steps): fragment with 26
# variables ~0.26 GB; .resu text with ~20 components ~1.9 GB.
#
# Compatible with IronPython 2.7.9 (standard library only).

import array
import base64
import io
import os
import re

from bridge_utils import tr, choose_configuration, configuration_warning


_CHUNK = 4 * 1024 * 1024


# ==========================================
# POSITIONS IN THE .LIML (without reading the whole file)
# ==========================================
def _find_solution_start(path, begin=0):
    """
    Byte position of '<solution' (as an element: followed by '>', '/' or
    a space) from byte begin, or -1. Reads in blocks; the model before
    <solution> is small, an old solution can be hundreds of MB.
    """
    return _find_from(path, "<solution", begin, ">/ \t\r\n")


def _find_from(path, pat, begin=0, follow=None):
    """Byte position of pat from byte begin, or -1. With follow: only
    if the character after pat is in it (an element, not a longer name)."""
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
    """Byte position of the last occurrence of pat, or -1 (searches from
    the end in blocks)."""
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
    """Copy the bytes [start, end) of src to the open dst_file."""
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
    """Copy src from byte start to the end to the open dst_file."""
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
# MODEL COPY FOR <solution>
# ==========================================
_FIELDVAR_OPEN = re.compile(r"^\s*<fieldvariable[\s>/]")


def _model_copy(head, nl):
    """
    Lines of the model copy in <solution>: the top-level elements of head
    (the text between <liml ...> and <solution>/</liml>) two spaces deeper,
    without <fieldvariable>.

    Indent only lines that start with a tag while the previous line ends
    with '>'; continuation lines of multi-line text (comment,
    radiossmodeldefinition) stay unchanged, like Mecway's own copy.
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
# CONFIGURATIONS IN THE MODEL COPY
#
# Mecway's own solution of a model with configurations (measured
# headless with Mecway 34, mecway.exe <model> solve on LS-20a with
# loads, a <fixed> and <group>s suppressed per configuration): the model
# copy in <solution configuration="X"> has
#   - no <configuration name=".."/> elements;
#   - no <suppressed configuration=".."/> children;
#   - suppressed="true" as the last attribute of every item suppressed in
#     X (<gravity suppressed="true">, <traction selection=".."
#     suppressed="true">);
#   - an item without children left is self-closing
#     (<fixed selection="SymX" suppressed="true" />, <group name="G" />).
# Items suppressed only through a suppressed group keep their tag as is.
# Mecway 34 refuses a copy with the <configuration> definitions and
# <suppressed> children ("Error opening file").
# ==========================================
_TAG = re.compile(r'<(/?)([A-Za-z_][\w.:-]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*?)'
                  r'(/?)>')
_SUPPRESSED_TRUE = re.compile(r'\bsuppressed\s*=\s*"true"')


class _Open(object):
    """An element that is open while scanning the model copy."""
    __slots__ = ("m", "kept", "removed", "suppress", "drop")

    def __init__(self, m, drop):
        self.m = m              # match of the start tag
        self.kept = 0           # child elements that stay
        self.removed = []       # (start, end) of removed <suppressed> children
        self.suppress = False   # suppressed in the solved configuration
        self.drop = drop        # the whole element goes (<configuration>)


def _start_tag(m, suppress, close):
    """Start tag of match m with suppressed="true" (if suppress and not yet
    there) as the last attribute; close is ">" or " />"."""
    attrs = m.group(3).rstrip()
    if suppress and not _SUPPRESSED_TRUE.search(attrs):
        attrs += ' suppressed="true"'
    return "<" + m.group(2) + attrs + close


def _blank_lines(text, edits, nl):
    """Removals ("" edits) that leave only whitespace on their line remove
    the whole line, line break included."""
    by_line = {}
    for k, (a, b, rep) in enumerate(edits):
        if rep:
            continue
        ls = text.rfind(nl, 0, a)
        ls = 0 if ls < 0 else ls + len(nl)
        le = text.find(nl, b)
        le = len(text) if le < 0 else le
        if text.find(nl, a, b) >= 0:
            continue                    # removal over more lines
        by_line.setdefault((ls, le), []).append(k)
    drop = set()
    extra = []
    for (ls, le), ks in by_line.items():
        line = text[ls:le]
        for k in sorted(ks, reverse=True):
            a, b = edits[k][0] - ls, edits[k][1] - ls
            line = line[:a] + line[b:]
        if line.strip():
            continue
        drop.update(ks)
        if le < len(text):
            extra.append((ls, le + len(nl), ""))
        elif ls > 0:
            extra.append((ls - len(nl), le, ""))
        else:
            extra.append((ls, le, ""))
    return [e for k, e in enumerate(edits) if k not in drop] + extra


def _configuration_copy(text, configuration, nl):
    """
    The model copy text (the lines of _model_copy joined with nl) as Mecway
    writes it in <solution configuration="configuration">; see the header
    of this block. Text without <configuration>/<suppressed> comes back
    unchanged.
    """
    edits = []       # (start, end, replacement); "" = remove
    stack = []
    for m in _TAG.finditer(text):
        closing, name, attrs, selfclose = m.groups()
        if closing:
            if not stack:
                continue
            node = stack.pop()
            if node.drop:
                edits = [e for e in edits if e[0] < node.m.start()]
                edits.append((node.m.start(), m.end(), ""))
                continue
            if not node.removed and not node.suppress:
                continue
            inner = text[node.m.end():m.start()]
            for a, b in reversed(node.removed):
                inner = (inner[:a - node.m.end()] + inner[b - node.m.end():])
            if node.kept == 0 and not inner.strip():
                # Nothing left inside: self-closing, like Mecway
                edits = [e for e in edits if e[0] < node.m.start()]
                edits.append((node.m.start(), m.end(),
                              _start_tag(node.m, node.suppress, " />")))
            elif node.suppress:
                tag = _start_tag(node.m, True, ">")
                if tag != node.m.group(0):
                    edits.append((node.m.start(), node.m.end(), tag))
            continue
        if name == "configuration" and not stack:
            # Configuration definition at the top of the model: drop it
            if selfclose:
                edits.append((m.start(), m.end(), ""))
            else:
                stack.append(_Open(m, True))
            continue
        conf = _CONF_ATTR.search(attrs)
        if name == "suppressed" and stack and selfclose and conf:
            parent = stack[-1]
            parent.removed.append((m.start(), m.end()))
            if conf.group(1) == configuration:
                parent.suppress = True
            edits.append((m.start(), m.end(), ""))
            continue
        if stack:
            stack[-1].kept += 1
        if not selfclose:
            stack.append(_Open(m, False))
    if not edits:
        return text
    edits = sorted(_blank_lines(text, edits, nl))
    out = []
    pos = 0
    for a, b, rep in edits:
        if a < pos:           # inside a part that was already replaced
            continue
        out.append(text[pos:a])
        out.append(rep)
        pos = b
    out.append(text[pos:])
    return "".join(out)


def _solution_copy(head, nl, configuration):
    """Lines of the model copy for <solution> (_model_copy); for a model
    with configurations as Mecway writes it (_configuration_copy)."""
    lines = _model_copy(head, nl)
    if configuration is None:
        return lines
    return _configuration_copy(nl.join(lines), configuration, nl).split(nl)


# ==========================================
# CYCLIC SYMMETRY: THE WHOLE WHEEL IN THE MODEL COPY (S10i)
#
# Mecway's own cyclic solution (measured headless with Mecway 33,
# details in aster_cyclic.py): the model copy in <solution> has N copies
# of the nodes and elements. Node i of sector j (0 .. N-1) is numbered
# i + j x n, rotated by +j x 360/N degrees about the axis through the
# origin; element e is numbered e + j x ne (ne = highest element number),
# with the nodes of its sector; per elset the elements are listed sector by
# sector. The extra nodes follow directly after the last node of the
# model, the extra elements are at the end of their elset; the rest of the
# copy (selections, loads, <cyclicsymmetry>) stays that of the sector.
# Coordinates with 15 significant digits ("0.428682574873297",
# "4.22074656910206E-21"), like Mecway.
# ==========================================
_CYCLIC = re.compile(r"<cyclicsymmetry\b([^>]*)>")
_NODE_LINE = re.compile(r'^(\s*)<node\s+nid="(\d+)"\s+x="([^"]*)"\s+'
                        r'y="([^"]*)"\s+z="([^"]*)"\s*/>\s*$')
_ELEM_LINE = re.compile(r'^(\s*<elem\s+eid=")(\d+)("[^>]*\bnodes=")'
                        r'([^"]*)(".*)$')


def cyclic_info(head):
    """(axis 0/1/2, segments) of the first <cyclicsymmetry> that is not
    suppressed in the model text head, or None."""
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
    """Coordinate like Mecway (15 significant digits, "0" for 0)."""
    if v == 0.0:
        return "0"
    return "%.15G" % v


def _wheel_copy(lines, segments, axis):
    """
    The lines of the model copy (_model_copy) extended to the whole wheel
    (see the header of this block). Returns (lines, n, ne).
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
    elems = None            # elem lines of the current <elset>
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
    (info, error) for model text head and result file fragment_path:
    info = (axis, N) if the result is the whole wheel of a cyclic model
    (node numbers above the number of nodes n of the model, up to N x n;
    aster_results_export with cyclic=...), otherwise None; error = message
    if the node numbers do not match the model.
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
    """Number of segments N if result file fragment_path is the whole wheel
    of the cyclic model model_liml (_wheel_check), otherwise None."""
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
    [(begin, end, configuration or None)] of the top-level <solution>
    elements from byte first (the first <solution>). Mecway writes them
    one after another as the last children of <liml>, one per
    configuration (<solution configuration="name">,
    Samples/CylinderLifting.liml and Tutorials/AssemblyWithContact.liml);
    without configurations one <solution> without attribute. Streaming:
    only start tags and end tags are searched.
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
    """The model before the first <solution> (small; an old solution can
    be hundreds of MB)."""
    sol = _find_solution_start(model_liml)
    return _read_range(model_liml, 0, sol if sol >= 0 else
                       os.path.getsize(model_liml))


def configuration_names(model_liml):
    """Names of the configurations of the model (<configuration
    name="..">), in order; [] without configurations or if the file
    cannot be read. For the Configuration list on the start screen."""
    try:
        return _CONF_NAME.findall(_model_head(model_liml))
    except (IOError, OSError):
        return []


def pick_configuration(model_liml):
    """
    (configuration, message) for splice_results. Without <configuration>
    in the model (None, ""). The Mecway API cannot read the active
    configuration (only mw.set_active_configuration); the choice comes from
    bridge_utils.choose_configuration (setting "configuration" or the
    rule there), the same as bridge_from_liml._pick_configuration for the
    loads. message: WARNING text (without "WARNING: ") for the log, or ""
    if the choice is unambiguous. The solutions of other configurations
    stay unchanged (splice_results).
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
    Write out_path = model_liml with a new <solution> (model copy +
    fragment). Everything outside that <solution> stays byte-identical,
    including the solutions of other configurations. configuration: name
    (see pick_configuration) or None (model without configurations: the
    solution without attribute). An existing out_path becomes
    out_path + ".bak"; writing goes to out_path + ".tmp" first. out_path
    may be equal to model_liml.

    If the fragment is the whole wheel of a cyclic model (aster_results_
    export with cyclic=...), the model copy gets the nodes and
    elements of all sectors, like Mecway (_wheel_copy).

    Returns
    -------
    (bool, str) - (True, "") or (False, reason).
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
            # Replace a solution without configuration (older bridge version)
            same = [s for s in sols if s[2] is None]
        if same:
            # Replace the existing solution; the rest stays.
            begin, tail_start = same[0][0], same[0][1]
            indent = ""      # the text before it ends with the indentation
            lead = ""
        else:
            # New solution after the last one.
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
    copy_lines = _solution_copy(head, nl, configuration)
    wheel, err = _wheel_check(head, fragment_path)
    if err:
        return False, err
    if wheel:
        # Cyclic symmetry: the whole wheel, like Mecway's own solution
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
    """out_path -> out_path.bak (an old .bak is dropped), tmp -> out_path."""
    if os.path.exists(out_path):
        bak = out_path + ".bak"
        if os.path.exists(bak):
            os.remove(bak)
        os.rename(out_path, bak)
    os.rename(tmp, out_path)


# ==========================================
# REMOVING RESULTS FROM THE .LIML (small .liml)
# ==========================================
def strip_results(model_liml):
    """
    Remove all <solution> elements (results, also those of other
    configurations) from model_liml; the model itself stays byte-identical.
    This keeps the .liml small; the results of a bridge run are in
    <model>_<run_id>_results.xml and can be loaded again with
    splice_results. Previous version: model_liml.bak.

    Returns
    -------
    (bool, str) - (True, "") or (False, reason).
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
            # Remove the line of <solution> completely: the indentation and
            # the line break before it belong to it.
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
# RESULT FILES IN THE WORK FOLDER
# ==========================================
RESULTS_SUFFIX = "_results.xml"     # <model>_<run_id>_results.xml
_RUN_STEM = re.compile(r"^(.*)_(\d{8}_\d{6})$")   # <model>_<run_id>
_COMM_LIML = re.compile(r"export_results\(\s*res,\s*r'[^']*',\s*r'([^']*)'")


def run_files(results_path):
    """
    Files of the same run as results_path
    (<model>_<run_id>_results.xml): {"run_id", "comm", "mail", "model"}.
    "mail" is the mesh of the run (<model>_<run_id>.mail, or another
    *_<run_id>.mail of an older version; otherwise None), "model" the .liml
    the run computed, read from the .comm (or "").
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
    Result files in work_dir, newest first: list of dicts
    {"path", "size", "mtime"} plus the keys of run_files().
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
# DOES A RESULT FILE MATCH THE MODEL?
# ==========================================
_NODE_TAG = re.compile(r'<node\s+nid="(\d+)"\s+x="([^"]*)"\s+y="([^"]*)"'
                       r'\s+z="([^"]*)"')
_ELEM_ID = re.compile(r'<elem\s+eid="(\d+)"')
_MAIL_NODE = re.compile(r'^\s*N(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$')


def _model_mesh(model_liml):
    """({nid: (x, y, z)}, set of eid) of the model (before <solution>)."""
    sol = _find_solution_start(model_liml)
    head = _read_range(model_liml, 0, sol if sol >= 0 else
                       os.path.getsize(model_liml))
    nodes = {}
    for m in _NODE_TAG.finditer(head):
        nodes[int(m.group(1))] = (float(m.group(2)), float(m.group(3)),
                                  float(m.group(4)))
    return nodes, set(int(e) for e in _ELEM_ID.findall(head))


def _fragment_ids(fragment_path):
    """(set of node numbers, set of element numbers) from the <nodeids>/
    <elementnodeids> of a result file. These come first
    (aster_results_export._write_fragment); reading stops at the first
    time step or variable."""
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
    """{nid: (x, y, z)} from the COOR_3D block of a .mail file."""
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
    """(largest coordinate difference, node) between nodes and coords
    ({nid: (x, y, z)})."""
    worst, worst_nid = 0.0, None
    for nid, xyz in nodes.items():
        d = max(abs(a - b) for a, b in zip(xyz, coords[nid]))
        if d > worst:
            worst, worst_nid = d, nid
    return worst, worst_nid


def check_results_fit(model_liml, fragment_path, mail_path=None):
    """
    Does result file fragment_path match the mesh of model_liml?
    Results on a different mesh would silently land on the wrong nodes.
    Check: node and element numbers of the result exist in the
    model; with mail_path (the .mail file of the same run) also the
    node coordinates.

    Returns
    -------
    (bool, str) - (matches, message). With True the message can be a
    warning (e.g. no .mail to compare the coordinates).
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
        # Whole wheel of a cyclic model: the nodes of sector 0 are those
        # of the model (the coordinates below); the other sectors
        # follow from the rotation (_wheel_copy).
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
        # Cyclic symmetry about X or Y: the .mail of the run is in the
        # computation frame (axis -> Z, bridge_cyclic._rewrite_mesh); rotate
        # back. Only a modal run rotates (bridge_cyclic.build_cyclic_modes),
        # so try both frames.
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
# FALLBACK: READING ONE TIME STEP
# ==========================================
_OPEN_TAG = re.compile(r'<(results|nodeids|elementnodeids|timestep|mode|'
                       r'nodevariable|elementnodevariable|valuessingle|'
                       r'valuesdouble)\b([^>]*)>')
_ATTR = re.compile(r'(\w+)="([^"]*)"')


def read_step(fragment_path, step=-1, n_nodes=None):
    """
    Read the node variables of one time step from a results fragment (or
    a .liml with <results>). Line by line: also works for fragments
    of hundreds of MB.

    Parameters
    ----------
    step    : time step id (or mode id with <mode>, from 1); -1 = the
              last one. Without <timestep>/<mode> (static) step is
              ignored.
    n_nodes : length of the lists (number of nodes of the solution); None =
              highest node number in the fragment.

    Returns
    -------
    dict {Mecway variable: [value or None per node 1..n]} - the format
    of solution.set_variable(). Element node variables are
    skipped.
    """
    ids = {}            # name -> base64 lines of <nodeids>
    values = {}         # name -> base64 lines in the chosen time step
    typecode = "f"
    keep = True         # does the current time step belong to the request?
    var = None          # current <nodevariable>, None in element variables
    target = None       # list in which base64 lines are collected
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
    Modes in a result file (modal/buckling, aster_results_export):
    list of (id, kind, value) with kind "frequency" (Hz) or
    "bucklingfactor"; empty without <mode>. Line by line (the <mode>
    lines are separate from the base64 lines).
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
    """{key: float or text} from 'A=1 B=2 C=x,y,z'."""
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
    {mode: {parameter: value}} from the BRIDGE_MODE lines that
    aster_results_export.print_modes writes to the .mess (FREQ,
    MASS_EFFE_UN_DX/DY/DZ, MASS_EFFE_UN_DRX/DRY/DRZ or CHAR_CRIT); {} if
    they are missing. Under the key "massa" the BRIDGE_MASSA line (M, JX,
    JY, JZ, ZWP as text "x,y,z", JZX, JZY, JZZ), if present.
    """
    out = {}
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = open(mess_path, "rb")
    try:
        for line in f:
            if not isinstance(line, str):     # CPython 3 (verification)
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


def read_tagged(mess_path, tag):
    """{key: float or text} of the last line '<tag> A=1 B=x,y' in the
    .mess, or {} without it. For BRIDGE_STATCHECK / BRIDGE_STATREAC
    (aster_results_export.print_static_check) and BRIDGE_EXCIT
    (print_excitation). The tag must be followed by a space (so
    BRIDGE_STATCHECK does not match BRIDGE_STATCHECK_FOUT)."""
    out = {}
    if not mess_path or not os.path.exists(mess_path):
        return out
    head = tag + " "
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            line = line.strip()
            if line.startswith(head):
                out = _key_values(line[len(head):])
    finally:
        f.close()
    return out


_MESS_CYCL = re.compile(r"^BRIDGE_CYCL\s+(.*)$")


def read_cyclic_summary(mess_path):
    """{N, NMAX_FREQ, MODES, WIEL} from the BRIDGE_CYCL line of
    aster_cyclic.collect (WIEL = 1: the modes are on the whole wheel), or
    {} without that line."""
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


# Global error of CALC_ERREUR ERME in the .mess (Code-Aster 17.4, seen):
#    MECANIQUE : ESTIMATEUR D'ERREUR EN RESIDU EXPLICITE
#    ...
#  NUMERO D'ORDRE:     1
#  ERREUR            ABSOLUE         RELATIVE   NORME DE SIGMA
#  TOTALE            1.51459146D+06  61.083 %   1.96324245D+06
#  TERME VOLUMIQUE   7.37849403D+05  35.181 %
#  TERME SAUT        4.62616959D+05  22.936 %
#  TERME NORMAL      3.30403568D+05  16.596 %
# RELATIVE = 100 eta / sqrt(eta^2 + norm(sigma)^2) (recomputed from ERME_ELEM,
# see bridge_to_aster._error_estimator_block).
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
    Global error estimate per numero d'ordre from the .mess: list of dicts
    {"order": n, "abs": eta, "rel": %, "sigma": norm of sigma, "volume":
    %, "jump": %, "boundary": %} in the order of the .mess; [] without
    error estimator. Only the mechanical block (MECANIQUE).
    """
    out = []
    if not mess_path or not os.path.exists(mess_path):
        return out
    # io.open with UTF-8: the .mess contains French accents; this way also
    # usable in CPython (verification, TestFiles/Verificatie/verif_lib.py).
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


# Nonlinear buckling (bridge_to_aster._crit_stab_report,
# _imperfection_blocks): lines that the Code-Aster job writes to the .mess.
_CS_KIND = re.compile(r"^BRIDGE_CRIT_STAB_SOORT\s+(\w+)")
_CS_ROW = re.compile(r"^BRIDGE_CRIT_STAB\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)")
_IMP_MODE = re.compile(r"^BRIDGE_IMPERFECTIE_MODE\s+(\d+)\s+([-+0-9.eE]+)")
_IMP = re.compile(r"^BRIDGE_IMPERFECTIE\s+(\d+)\s+([-+0-9.eE]+)")


def read_crit_stab(mess_path):
    """
    Stability criterion per step (CRIT_STAB) from the .mess:
    {"kind": "factor" | "eigen", "rows": [(t, lambda)], "missing": text
    or None}; None if CRIT_STAB was not on. Meaning of lambda:
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
    Estimate of the buckling point from the 'eigen' series (lambda -> 0):
    ("kruising", t) if lambda goes from < 0 to >= 0 between two steps
    (linearly interpolated); ("extrapolatie", t) if lambda is still < 0
    and rises in the last two steps (linearly extended to 0);
    otherwise None.
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
    Imperfection (buckling shape) from the .mess: {"mode": k,
    "amplitude": e0 [m], "factors": {mode: buckling load factor}}; None
    without imperfection.
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
    """Add the base64 part of text (up to a possible end tag)."""
    text = text.split("<", 1)[0].strip()
    if text:
        buf.append(text)


def _decode(chunks, typecode):
    a = array.array(typecode)
    a.fromstring(base64.b64decode("".join(chunks)))
    return a


def _to_node_lists(ids, values, typecode, n_nodes):
    """{name: [value or None per node]} from the base64 lines."""
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
                # float(): IronPython returns a System.Single from array('f').
                lst[nid - 1] = float(v)
        out[name] = lst
    return out
