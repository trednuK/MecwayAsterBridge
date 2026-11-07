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
# list them (Results... button); as a fallback, read one time step from
# the fragment for the solution.set_variable() route; and add the shells of
# general-section beams to a solution (add_section_view).
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
import bisect
import io
import json
import os
import re
from collections import OrderedDict

from bridge_utils import (tr, choose_configuration, configuration_warning, log,
                          model_stem, run_name, work_dir_path)
import bridge_monitor


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
# Top-level elements Mecway leaves out of the model copy: <fieldvariable>
# (display settings) and <savedmonitor /> (the Saved monitor item; its text
# is in <results>, bridge_monitor.py; measured with Mecway 34).
_FIELDVAR_OPEN = re.compile(r"^\s*<(fieldvariable|savedmonitor)[\s>/]")


def _model_copy(head, nl):
    """
    Lines of the model copy in <solution>: the top-level elements of head
    (the text between <liml ...> and <solution>/</liml>) two spaces deeper,
    without <fieldvariable> and <savedmonitor>.

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
    skipping = None          # closing tag of the element being left out
    for line in lines:
        starts_tag = prev_tag_end and line.lstrip().startswith("<")
        m = _FIELDVAR_OPEN.match(line) if starts_tag and not skipping \
            else None
        if m:
            close = "</{0}>".format(m.group(1))
            skipping = (None if line.rstrip().endswith("/>") or
                        close in line else close)
            prev_tag_end = line.rstrip().endswith(">")
            continue
        if skipping:
            if skipping in line:
                skipping = None
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


def has_results(model_liml, configuration=None):
    """
    True if model_liml has a solution with <results> for configuration
    (the solution splice_results would replace: the one with that
    configuration, else one without attribute; configuration None: the
    solution without attribute, else any). Mecway's stub solutions of a
    model with configurations have no <results> and do not count, nor does
    a <results> with only a Saved monitor (an earlier run without results,
    MecwayAsterBridgeMain._monitor_only). Streaming, as _solutions.
    """
    if not os.path.exists(model_liml):
        return False
    sol = _find_solution_start(model_liml)
    if sol < 0:
        return False
    sols = _solutions(model_liml, sol)
    same = [s for s in sols if s[2] == configuration]
    if not same:
        same = [s for s in sols if s[2] is None] if configuration else sols
    for begin, end, _conf in same:
        pos = _find_from(model_liml, "<results", begin, ">/ \t\r\n")
        if not 0 <= pos < end:
            continue
        head = _read_range(model_liml, pos, min(end, pos + 512))
        after = head.find(">") + 1
        if after <= 0 or head[after - 2] == "/":      # <results ... />
            continue
        rest = head[after:].lstrip()
        if rest.startswith("<savedmonitor"):
            mon = _find_from(model_liml, "</savedmonitor>", pos + after)
            if not 0 <= mon < end:
                return True
            rest = _read_range(model_liml, mon + len("</savedmonitor>"),
                               min(end, mon + 512)).lstrip()
        if not rest.startswith("</results>"):
            return True
    return False


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


_RESULTS_OPEN = re.compile(r"<results[\s>]")
_LIML_OPEN = re.compile(r"<liml[\s>]")
_MONITOR_TAG = re.compile(r"<savedmonitor[\s>/]")


def _results_tag_end(fragment_path):
    """Byte position just after the start tag <results ...> of the
    fragment (at its beginning, aster_results_export._write_fragment), or
    -1 if it is not in the first 4 kB."""
    text = _read_range(fragment_path, 0, min(4096,
                                             os.path.getsize(fragment_path)))
    m = _RESULTS_OPEN.search(text)
    if not m:
        return -1
    end = text.find(">", m.start())
    return end + 1 if end >= 0 else -1


def splice_results(model_liml, fragment_path, out_path, configuration=None,
                   monitor=None):
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

    monitor: text for Mecway's Saved monitor (bridge_monitor.monitor_text)
    or None. It goes as <savedmonitor><output> first into <results>, and
    the model gets a top-level <savedmonitor /> (the tree item) if it has
    none; the format is described in bridge_monitor.py. With monitor and
    fragment_path None the solution has only the monitor (a run without
    results; Mecway opens it as a solution without values).

    Returns
    -------
    (bool, str) - (True, "") or (False, reason).
    """
    if not os.path.exists(model_liml):
        return False, tr("Model niet gevonden: {0}",
                         "Model not found: {0}").format(model_liml)
    if fragment_path is None and monitor is None:
        return False, tr("Geen fragment en geen monitortekst.",
                         "No fragment and no monitor text.")
    if fragment_path is not None and (
            not os.path.exists(fragment_path) or
            os.path.getsize(fragment_path) == 0):
        return False, tr("Fragment ontbreekt of is leeg: {0}",
                         "Fragment is missing or empty: {0}").format(
            fragment_path)
    results_end = 0
    if fragment_path is not None and monitor is not None:
        results_end = _results_tag_end(fragment_path)
        if results_end < 0:
            return False, tr("Geen <results> aan het begin van {0}",
                             "No <results> at the start of {0}").format(
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
    wheel, err = (_wheel_check(head, fragment_path)
                  if fragment_path is not None else (None, None))
    if err:
        return False, err
    if wheel:
        # Cyclic symmetry: the whole wheel, like Mecway's own solution
        copy_lines = _wheel_copy(copy_lines, wheel[1], wheel[0])[0]
    # Saved monitor: the tree item at the top of the model (Mecway moves it
    # on save; the order of top-level items is free), unless it is there.
    marker = -1
    if monitor is not None and not _MONITOR_TAG.search(head):
        m = _LIML_OPEN.search(head)
        if m:
            marker = head.find(">", m.start()) + 1

    tmp = out_path + ".tmp"
    f = open(tmp, "wb")
    try:
        if marker > 0:
            _copy_range(model_liml, f, 0, marker)
            f.write(nl + "  <savedmonitor />")
            _copy_range(model_liml, f, marker, begin)
        else:
            _copy_range(model_liml, f, 0, begin)
        f.write(lead + indent + open_tag + nl)
        f.write(nl.join(copy_lines) + nl)
        if monitor is None:
            _copy_from(fragment_path, f, 0)
        else:
            block = bridge_monitor.savedmonitor_block(monitor)
            if fragment_path is None:
                f.write('    <results precision="double">' + block +
                        "\r\n    </results>\r\n")
            else:
                _copy_range(fragment_path, f, 0, results_end)
                f.write(block)
                _copy_from(fragment_path, f, results_end)
        f.write("  </solution>")
        if sol < 0:
            f.write(nl)
        _copy_from(model_liml, f, tail_start)
    finally:
        f.close()

    _replace_with_bak(tmp, out_path)
    _log_section_notes(fragment_path)
    return True, ""


def _replace_with_bak(tmp, out_path):
    """out_path -> out_path.bak (an old .bak is dropped), tmp -> out_path.
    When the second step fails, out_path is put back."""
    if not os.path.exists(out_path):
        os.rename(tmp, out_path)
        return
    bak = out_path + ".bak"
    if os.path.exists(bak):
        os.remove(bak)
    os.rename(out_path, bak)
    try:
        os.rename(tmp, out_path)
    except OSError:
        os.rename(bak, out_path)
        raise


def restore_bak(path):
    """path.bak back in place of path. True when that worked."""
    bak = path + ".bak"
    if not os.path.exists(bak):
        return False
    try:
        if os.path.exists(path):
            os.remove(path)
        os.rename(bak, path)
    except OSError:
        return False
    return True


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
# SECTION VIEW: SHELLS IN THE SOLUTION
#
# add_section_view writes the shells of bridge_section_view into the model
# copy of one <solution>, with values in its <results>; the model part and
# the other solutions stay byte-identical. An item of Mecway's Solution tree
# without values on the shells shows them black (seen by the user in Mecway
# 35), so every variable the beams have gets values on the shells:
#   displx/y/z, displmag    computed (bridge_section_view.shell_values)
#   stressptu, node values  the section stress, when it can be computed
#   other node variables    a shell node copies the beam node at its end;
#                           rotations are of this kind
#   element-node variables  a shell element copies its beam element, each
#                           node the value of its own end (also stressptu)
#   SECTION_STRESS          new, the section stress, as node values and as
#                           element-node values
#   SECTION_SHEAR, _VON_MISES   the same two ways, from the table of the job
#                           (<run>_section.json, bridge_section_stress) and the
#                           section forces; shells of a beam without either
#                           stay out of their ids. No table (a Mecway solve,
#                           an older run): these two do not exist, the rest
#                           does. The maxima of the job, beamvonmisesmax,
#                           beamsixxabsmax and beamtaumax, are element-node
#                           variables of the beams like any other.
# A node or element without a value is not in the <nodeids> or
# <elementnodeids> of that variable, so a shell of a beam without a value
# stays out of it too.
#
# Two passes. _index_results finds the tags without decoding anything; then
# _write_results rewrites one variable of one step at a time. Time: all
# base64 of the results is decoded and encoded once. Memory: the ids per
# distinct <nodeids>, the values of one variable of one step. Shell ids lie
# above the ids of the solved mesh, so that <nodeids> stay ascending.
# Measured in IronPython 2.7.9, double precision, 20 variables: linear, about
# 15 MB of file per second (2.65 GB in 174 s, 98 shell nodes), plus about
# 1.4 microseconds per shell node, variable and step (12,014 shell nodes, 100
# steps: 28 s, and the file grows from 45 to 351 MB).
#
# Reloads (splice_results) build the model copy from the head of the file,
# so the shells are gone afterwards: the caller adds them again.
# ==========================================
SECTION_STRESS = ("langsspanning", "longitudinalstress")
SECTION_SHEAR = ("doorsnedeschuif", "sectionshear")
SECTION_VON_MISES = ("doorsnedevonmises", "sectionvonmises")
_SECTION_NAMES = SECTION_STRESS + SECTION_SHEAR + SECTION_VON_MISES
# bridge_section_stress.SECTION_SUFFIX, without its numpy
SECTION_SUFFIX = "_section.json"
_MAX_SECTION_FILES = 30         # newest first, each a small file
_SHELL_DISPL = ("displx", "disply", "displz")
_SHELL_ROT = ("rotx", "roty", "rotz")
_SHELL_FORCES = ("tensileforce", "bendingmomv", "bendingmomw")
_SHELL_SHEARS = ("sheary", "shearz", "torsion")
_WIDTH = {"f": 4, "d": 8}
_B64_LINE = 64
_RESULT_TAG = re.compile(r'<(/?)(results|nodeids|elementnodeids|timestep|'
                         r'mode|nodevariable|elementnodevariable|'
                         r'savedmonitor)\b([^<>]*)>')
_VALUES_OPEN = re.compile(r"<(valuessingle|valuesdouble)>")
_ELSET_LINE = re.compile(r'^\s*<elset\s+name="([^"]*)"([^>]*?)(/?)>')
_COMPONENT = re.compile(r'[ \t]*<component name="([^"]*)"[^>]*/>\r?\n')
_EMPTY_COMPONENT = re.compile(r'[ \t]*<component name=""[^>]*/>\r?\n')
_MAXMIN = re.compile(r'([ \t]*)<maxandmin>\r?\n')
_MAXMIN_EMPTY = re.compile(r'([ \t]*)<maxandmin\s*/>')


class _Refused(Exception):
    """An ordinary refusal; text is the bilingual reason."""

    def __init__(self, text):
        Exception.__init__(self, text)
        self.text = text


def _bytes_of(values):
    """The contents of an array as a binary string."""
    if hasattr(values, "tobytes"):
        return values.tobytes()
    return values.tostring()


def _array_of(typecode, data):
    values = array.array(typecode)
    if hasattr(values, "frombytes"):
        values.frombytes(data)
    else:
        values.fromstring(data)
    return values


def _b64_text(data):
    """base64 of data in lines of 64 characters with CRLF, plus a CRLF at
    the end (as Mecway, see the header of aster_results_export.py)."""
    enc = base64.b64encode(data)
    if not isinstance(enc, str):
        enc = enc.decode("ascii")
    return "\r\n".join([enc[i:i + _B64_LINE]
                        for i in range(0, len(enc), _B64_LINE)]) + "\r\n"


def _b64_data(text):
    return base64.b64decode(text.replace("\r", "").replace("\n", "")
                            .replace(" ", ""))


def _result_tags(path, start, end):
    """The tags of _RESULT_TAG in the bytes [start, end): tuples (position,
    closing, name, attributes, position after the tag). In blocks; base64
    holds no '<'. The file closes when the generator ends, so read to the
    end."""
    f = open(path, "rb")
    try:
        f.seek(start)
        offset = start
        keep = ""
        left = end - start
        while left > 0:
            block = f.read(min(_CHUNK, left))
            if not block:
                break
            left -= len(block)
            buf = keep + block
            for m in _RESULT_TAG.finditer(buf):
                yield (offset + m.start(), m.group(1) == "/", m.group(2),
                       m.group(3), offset + m.end())
            cut = buf.rfind("<")
            if cut < 0 or buf.find(">", cut) >= 0:
                cut = len(buf)
            keep = buf[cut:]
            offset += cut
    finally:
        f.close()


def _new_step(kind):
    return {"kind": kind, "vars": OrderedDict(), "elvars": OrderedDict()}


def _index_results(path, start, end):
    """
    Positions of the blocks of <results>, nothing decoded: {"start", "end"
    (of </results>), "precision", "ids", "elids": {variable: (begin, end)},
    "steps": [{"kind": "timestep"/"mode"/None, "vars", "elvars": {variable:
    (begin, end)}}]}. A static solution is one step of kind None.
    """
    index = {"start": start, "end": None, "precision": None,
             "ids": OrderedDict(), "elids": OrderedDict(), "steps": []}
    static = _new_step(None)
    step = static
    inside = {}             # tag -> (position, variable)
    monitor = False
    for pos, closing, tag, attrs, stop in _result_tags(path, start, end):
        if monitor:
            monitor = not (closing and tag == "savedmonitor")
            continue
        alone = attrs.rstrip().endswith("/")
        if tag == "savedmonitor":
            monitor = not closing and not alone
        elif tag == "results":
            if closing:
                index["end"] = pos
            else:
                index["precision"] = dict(_ATTR.findall(attrs)).get(
                    "precision")
        elif tag in ("timestep", "mode"):
            if closing:
                step = static
            else:
                step = _new_step(tag)
                index["steps"].append(step)
        else:
            table = {"nodeids": index["ids"], "elementnodeids": index["elids"],
                     "nodevariable": step["vars"],
                     "elementnodevariable": step["elvars"]}[tag]
            if closing:
                begin, name = inside.pop(tag, (None, None))
                if name is not None:
                    table[name] = (begin, stop)
            elif alone:
                table[dict(_ATTR.findall(attrs)).get("name")] = (pos, stop)
            else:
                inside[tag] = (pos, dict(_ATTR.findall(attrs)).get("name"))
    if static["vars"] or static["elvars"]:
        if index["steps"]:
            raise _Refused(tr(
                "De resultaten hebben variabelen naast tijdstappen; dat "
                "formaat is onbekend.",
                "The results have variables next to time steps; that "
                "format is unknown."))
        index["steps"].append(static)
    return index


def _stale_text():
    return tr("De solution hoort niet bij dit model; het model is na de "
              "berekening gewijzigd. Reken opnieuw.",
              "The solution does not belong to this model; the model was "
              "changed after the calculation. Calculate again.")


def _misfit_text():
    return tr("Het aantal waarden in de resultaten past niet bij hun "
              "nummers.",
              "The number of values in the results does not fit their ids.")


def _no_result_text():
    return tr("Deze solution heeft geen resultaten. Reken eerst.",
              "This solution has no results. Calculate first.")


def _no_rotation_text():
    return tr("Het resultaat mist verplaatsing of rotatie op de balkknopen. "
              "Vraag beide aan als resultaatveld en reken opnieuw.",
              "The result lacks displacement or rotation on the beam "
              "nodes. Request both as result fields and calculate again.")


def _split_old_block(lines, base, taken, indent):
    """(lines without earlier shell elsets, their names, {eid: node count}
    of their elements, their nodes). Such an elset has the name of
    bridge_section_view (with a suffix when the model has a component of that
    name), no material and is not a component of the model."""
    old, old_nodes, counts, keep = [], set(), {}, []
    inside = False
    for line in lines:
        if inside:
            m = _ELEM_LINE.match(line)
            if m:
                nodes = m.group(4).split()
                counts[int(m.group(2))] = len(nodes)
                old_nodes.update([int(n) for n in nodes])
            elif line.strip().startswith("</elset>"):
                inside = False
            continue
        m = (_ELSET_LINE.match(line)
             if line.startswith(indent + "<elset ") else None)
        if m and m.group(1) not in taken and "material=" not in m.group(2) \
                and (m.group(1) == base or
                     re.match(re.escape(base) + r"_\d+$", m.group(1))):
            old.append(m.group(1))
            inside = not m.group(3)
            continue
        keep.append(line)
    return keep, old, counts, old_nodes


def _check_beams(view, nodes, elements):
    """Refuse when the drawn beams are not those of the solved mesh: the
    model copy can be older than the model."""
    if max(nodes or [0]) >= view["nids"][0] or \
            max(elements or [0]) >= view["elements"][0][0]:
        raise _Refused(_stale_text() + u" " + tr(
            "De solution heeft knopen die niet in het model staan, "
            "bijvoorbeeld door oplossen terwijl de doorsnede getoond werd.",
            "The solution has nodes that are not in the model, for example "
            "from solving while the section was shown."))
    for beam in view["beams"]:
        ids = elements.get(beam["eid"])
        if ids is None or len(ids) < max(beam["element_nodes"]):
            raise _Refused(_stale_text())
        for end in (0, 1):
            nid = beam["nodes"][end]
            xyz = nodes.get(nid)
            if xyz is None or \
                    int(ids[beam["element_nodes"][end] - 1]) != nid or \
                    max([abs(a - b) for a, b in zip(xyz, beam["ends"][end])]
                        ) > 1.0e-9 * (1.0 + max([abs(c) for c in xyz])):
                raise _Refused(_stale_text())


def _read_copy(lines, view, model_data, section_view):
    """
    What add_section_view needs of the model copy (its lines, from
    <solution> to the indentation of <results>): {"lines": without the
    block and the nodes of an earlier call, "old": names of such blocks,
    "counts": {eid: number of nodes}, old elements included, "node_limit",
    "element_limit": highest id of the solved mesh}.
    """
    indent = section_view.COPY_INDENT
    taken = set(e[3] for e in model_data.get("mesh_elements", []))
    keep, old, counts, old_nodes = _split_old_block(
        lines, section_view.ELSET, taken, indent)
    old_elements = list(counts)
    nodes, elements, out = {}, {}, []
    tag = indent + "<node "
    for line in keep:
        m = _NODE_LINE.match(line) if line.startswith(tag) else None
        if m:
            nid = int(m.group(2))
            if nid in old_nodes:
                continue
            nodes[nid] = (float(m.group(3)), float(m.group(4)),
                          float(m.group(5)))
        else:
            m = _ELEM_LINE.match(line)
            if m:
                elements[int(m.group(2))] = m.group(4).split()
        out.append(line)
    for eid, ids in elements.items():
        counts[eid] = len(ids)
    _check_beams(view, nodes, elements)
    return {"lines": out, "old": old, "counts": counts,
            "node_limit": min([view["nids"][0]] + list(old_nodes)) - 1,
            "element_limit": min([view["elements"][0][0]] + old_elements) - 1}


def _ids_of(text):
    """(array of ids, their binary string) of an ids block."""
    data = _b64_data(text[text.index(">") + 1:text.rindex("<")])
    return _array_of("i", data), data


def _node_layout(text, sources, limit, had_block):
    """
    Where the values of a variable are, from its <nodeids> block. sources:
    [(shell node, beam node)]. Keys: "where": {beam node: position}, "slots"
    values per step, "kept" those that stay (not of an earlier call), "raw"
    the ids that stay, "ids": shell nodes that get a value, "pick": for each
    the position of its beam node.
    """
    ids, raw = _ids_of(text)
    kept = bisect.bisect_right(ids, limit)
    if kept != len(ids) and not had_block:
        raise _Refused(_stale_text())
    wanted = set([beam for _shell, beam in sources])
    where = {}
    for i in range(kept):
        if ids[i] in wanted:
            where[int(ids[i])] = i
    pick = [(shell, where[beam]) for shell, beam in sources if beam in where]
    return {"where": where, "slots": len(ids), "kept": kept,
            "raw": raw[:4 * kept], "ids": [p[0] for p in pick],
            "pick": [p[1] for p in pick]}


def _element_layout(text, shells, counts, limit, had_block):
    """As _node_layout for an <elementnodeids> block, with a value per node
    of an element. shells: [(shell element, beam, [end per node])]; "where":
    {beam element: position of its first value}."""
    ids, raw = _ids_of(text)
    kept_ids = bisect.bisect_right(ids, limit)
    if kept_ids != len(ids) and not had_block:
        raise _Refused(_stale_text())
    beams = set([s[1]["eid"] for s in shells])
    where = {}
    slots = kept = 0
    for i in range(len(ids)):
        eid = ids[i]
        if eid not in counts:
            raise _Refused(_stale_text())
        if i == kept_ids:
            kept = slots
        elif i < kept_ids and eid in beams:
            where[int(eid)] = slots
        slots += counts[eid]
    if kept_ids == len(ids):
        kept = slots
    added, pick = [], []
    for eid, beam, ends in shells:
        first = where.get(beam["eid"])
        if first is not None:
            added.append(eid)
            pick.extend([first + beam["element_nodes"][e] - 1 for e in ends])
    return {"where": where, "slots": slots, "kept": kept,
            "raw": raw[:4 * kept_ids], "ids": added, "pick": pick}


def _layouts(src, index, view, copy):
    """({variable: layout} of node values, of element values), without the
    section stress. Variables with the same ids share a layout."""
    origin = dict(zip(view["nids"], view["origin"]))
    sources = [(nid, view["beams"][o[0]]["nodes"][o[1]])
               for nid, o in zip(view["nids"], view["origin"])]
    owner = {}
    for number, part in enumerate(view["parts"]):
        for element in part["elements"]:
            owner[element[0]] = view["beams"][number]
    shells = [(e[0], owner[e[0]], [origin[n][1] for n in e[2]])
              for e in view["elements"]]
    seen = {}

    def layout_of(span, element):
        src.seek(span[0])
        text = src.read(span[1] - span[0])
        key = (element, text[text.find(">") + 1:])
        if key not in seen:
            if element:
                seen[key] = _element_layout(
                    text, shells, copy["counts"], copy["element_limit"],
                    bool(copy["old"]))
            else:
                seen[key] = _node_layout(text, sources, copy["node_limit"],
                                         bool(copy["old"]))
        return seen[key]

    nodes = dict((name, layout_of(span, False))
                 for name, span in index["ids"].items()
                 if name not in _SECTION_NAMES)
    elements = dict((name, layout_of(span, True))
                    for name, span in index["elids"].items()
                    if name not in _SECTION_NAMES)
    return nodes, elements


def _all_shells(layout, view):
    """layout of a computed variable: a value on every shell node."""
    out = dict(layout)
    out["ids"] = list(view["nids"])
    out["pick"] = []
    return out


def _read_block(src, span):
    """The block at span around its values: {"head" up to and with the start
    tag of the values, "tail" from their end tag on, "code" array type,
    "raw" the values}."""
    src.seek(span[0])
    text = src.read(span[1] - span[0])
    m = _VALUES_OPEN.search(text)
    close = text.find("</" + m.group(1) + ">", m.end()) if m else -1
    if close < 0:
        raise _Refused(_misfit_text())
    return {"head": text[:m.end()], "tail": text[close:],
            "code": "d" if m.group(1) == "valuesdouble" else "f",
            "raw": _b64_data(text[m.end():close])}


def _checked(block, layout):
    if len(block["raw"]) != _WIDTH[block["code"]] * layout["slots"]:
        raise _Refused(_misfit_text())
    return block


def _pick_values(block, positions):
    """The values at positions, as an array of the block's type; the bytes
    stay as they are in the file."""
    raw, width = block["raw"], _WIDTH[block["code"]]
    return _array_of(block["code"], raw[:0].join(
        [raw[p * width:(p + 1) * width] for p in positions]))


def _bounds(values):
    """(max, min) of the finite numbers in values, or None."""
    finite = [v for v in values if v - v == 0.0]
    if not finite:
        return None
    return float(max(finite)), float(min(finite))


def _component(elset, bounds, indent, nl):
    return '{0}<component name="{1}" max="{2}" min="{3}" />{4}'.format(
        indent, elset, _coord(bounds[0]), _coord(bounds[1]), nl)


def _with_component(head, elset, bounds, drop):
    """head of a block without the components of drop, plus one for the
    shells: after the one for nodes without an element, because the shells
    are the first elset of the model copy."""
    head = _COMPONENT.sub(lambda m: "" if m.group(1) in drop else m.group(0),
                          head)
    if bounds is None:
        return head
    nl = "\r\n" if "\r\n" in head else "\n"
    m = _MAXMIN.search(head)
    if m is None:
        m = _MAXMIN_EMPTY.search(head)
        if m is None:
            return head
        return (head[:m.start()] + m.group(1) + "<maxandmin>" + nl +
                _component(elset, bounds, m.group(1) + "  ", nl) +
                m.group(1) + "</maxandmin>" + head[m.end():])
    at = m.end()
    first = _EMPTY_COMPONENT.match(head, at)
    if first:
        at = first.end()
    return (head[:at] + _component(elset, bounds, m.group(1) + "  ", nl) +
            head[at:])


def _rewrite_block(block, layout, computed, plan):
    """The new text of a variable. computed: shell values, or None to copy
    the beam values at layout["pick"]."""
    _checked(block, layout)
    code = block["code"]
    if computed is None:
        added = _pick_values(block, layout["pick"])
    else:
        added = array.array(code, computed)
    kept = block["raw"][:_WIDTH[code] * layout["kept"]]
    return (_with_component(block["head"], plan["elset"], _bounds(added),
                            plan["drop"]) +
            _b64_text(kept + _bytes_of(added)) + block["tail"])


def _new_variable(kind, name, indent, values, plan):
    """A whole new <nodevariable>/<elementnodevariable>, starting with a
    line break and without one at the end."""
    code = "d" if plan["index"]["precision"] == "double" else "f"
    tag = "valuesdouble" if code == "d" else "valuessingle"
    data = array.array(code, values)
    nl = plan["nl"]
    bounds = _bounds(data)
    return (nl + indent + '<{0} name="{1}">'.format(kind, name) + nl +
            indent + "  <maxandmin>" + nl +
            (_component(plan["elset"], bounds, indent + "    ", nl)
             if bounds else "") +
            indent + "  </maxandmin>" + nl +
            indent + "  <" + tag + ">" + _b64_text(_bytes_of(data)) +
            "</" + tag + ">" + nl +
            indent + "</" + kind + ">")


def _indent_before(src, pos):
    start = max(0, pos - 64)
    src.seek(start)
    text = src.read(pos - start)
    return text[len(text.rstrip(" \t")):]


def _whole_lines(src, span):
    """span with the indentation before it and the line break after it."""
    begin = span[0] - len(_indent_before(src, span[0]))
    src.seek(span[1])
    after = src.read(2)
    end = span[1]
    if after.startswith("\r\n"):
        end += 2
    elif after.startswith("\n"):
        end += 1
    return begin, end


def _kept_spans(table, drop):
    return [span for name, span in table.items() if name not in drop]


def _step_values(plan, step, src):
    """
    Shell values of one step: {"cache": decoded blocks by span, "values":
    {variable: [value per shell node]}, "routes": as shell_values}. Refuses
    when a beam end has no displacement or rotation.
    """
    cache = {}

    def block_of(name, table, layouts):
        span = step[table].get(name)
        if span is None or name not in layouts:
            raise _Refused(_no_rotation_text())
        if span not in cache:
            cache[span] = _checked(_read_block(src, span), layouts[name])
        return cache[span]

    def beam_values(name):
        where = plan["nodes"][name]["where"]
        order = sorted(where)
        got = _pick_values(block_of(name, "vars", plan["nodes"]),
                           [where[n] for n in order])
        return dict(zip(order, [float(v) for v in got]))

    dx, dy, dz = [beam_values(n) for n in _SHELL_DISPL]
    rx, ry, rz = [beam_values(n) for n in _SHELL_ROT]
    ends = plan["beam_nodes"]
    displ = dict((n, (dx.get(n), dy.get(n), dz.get(n))) for n in ends)
    rot = dict((n, (rx.get(n), ry.get(n), rz.get(n))) for n in ends)
    forces = _step_forces(plan, step, block_of, _SHELL_FORCES) \
        if plan["forces"] else None
    out = plan["section_view"].shell_values(plan["view"], displ, rot,
                                            plan["model"], forces)
    if out is None:
        raise _Refused(_no_rotation_text())
    values = dict((n, out[n]) for n in _SHELL_DISPL + ("displmag",))
    sigma = out.get("sectionsigma")
    if sigma is not None:
        values[plan["stress"]] = sigma
        if plan["has_stress"]:
            values["stressptu"] = sigma
        if plan["tables"]:
            shear = _step_forces(plan, step, block_of, _SHELL_SHEARS) or {}
            if "wanted" not in plan:
                _choose_shear_shells(plan, shear)
            if plan["wanted"]:
                _add_shear(plan, values, shear, sigma)
    return {"cache": cache, "values": values,
            "routes": out.get("stress_routes")}


def _choose_shear_shells(plan, shear):
    """Which shells get shear stress: those with a table row and with the
    forces of their beam, decided on the first step: the ids of a variable are
    the same in every step, so that only a step without the variable can
    differ, and then no shell gets them. A shell element needs all its nodes.
    Sets plan["wanted"] (positions in the shell nodes), "wanted_ids" and
    "wanted_elements", "wanted_slots" (position in wanted per node of those
    elements)."""
    view = plan["view"]
    points = plan["section_view"].shear_points(view, plan["tables"])
    every_step = not [s for s in plan["index"]["steps"]
                      for name in _SHELL_SHEARS if name not in s["elvars"]]
    wanted = [i for i, o in enumerate(view["origin"]) if points[i] is not None
              and view["beams"][o[0]]["eid"] in shear and every_step]
    plan["shear_points"] = points
    plan["wanted"] = wanted
    plan["wanted_ids"] = [view["nids"][i] for i in wanted]
    slot = dict((view["nids"][i], k) for k, i in enumerate(wanted))
    chosen = [e for e in view["elements"] if all([n in slot for n in e[2]])]
    plan["wanted_elements"] = [e[0] for e in chosen]
    plan["wanted_slots"] = [slot[n] for e in chosen for n in e[2]]


def _add_shear(plan, values, shear, sigma):
    """The two shear variables of a step in values."""
    missing = [o for o in plan["wanted"] if plan["view"]["beams"][
        plan["view"]["origin"][o][0]]["eid"] not in shear]
    if missing:
        raise _Refused(tr("De snedekrachten ontbreken in een van de stappen.",
                          "The section forces are missing in one of the "
                          "steps."))
    tau, von_mises = plan["section_view"].shell_shear(
        plan["view"], plan["shear_points"], plan["tables"], shear, sigma,
        plan["wanted"])
    values[plan["shear"]] = tau
    values[plan["von_mises"]] = von_mises


def _step_forces(plan, step, block_of, names):
    """{beam: ((three values of names) at end 0, at end 1)} from the element
    values of a step, for bridge_section_view; None without them."""
    layouts = plan["elements"]
    per_var = []
    beams = plan["view"]["beams"]
    for name in names:
        if name not in step["elvars"] or name not in layouts:
            return None
        where = layouts[name]["where"]
        spots = [where[b["eid"]] + k - 1 for b in beams if b["eid"] in where
                 for k in b["element_nodes"]]
        got = _pick_values(block_of(name, "elvars", layouts), spots)
        per_var.append(dict(zip(spots, [float(v) for v in got])))
    out = {}
    for beam in beams:
        eid = beam["eid"]
        if all([eid in layouts[name]["where"] for name in names]):
            out[eid] = tuple([
                tuple([values[layouts[name]["where"][eid] + k - 1]
                       for name, values in zip(names, per_var)])
                for k in beam["element_nodes"]])
    return out


def _touches(layout):
    return bool(layout["ids"]) or layout["kept"] != layout["slots"]


def _ids_block(tag, name, ids):
    return '<{0} name="{1}">{2}</{0}>'.format(
        tag, name, _b64_text(_bytes_of(array.array("i", ids))))


def _edits(src, plan):
    """
    The changes of <results>, in file order: (begin, serial, end, action,
    step or None, argument). Insertions have begin == end and come right
    after the last block that stays.
    """
    index = plan["index"]
    names = plan["names"]
    out = []

    def add(span, action, step=None, argument=None):
        out.append((span[0], len(out), span[1], action, step, argument))

    for table, layouts in ((index["ids"], plan["nodes"]),
                           (index["elids"], plan["elements"])):
        for name, span in table.items():
            if name in names:
                add(_whole_lines(src, span), "drop")
            elif name in layouts and _touches(layouts[name]):
                add(span, "ids", None, layouts[name])
    if plan["has_stress"]:
        spans = _kept_spans(index["ids"], names)
        pad = plan["nl"] + _indent_before(src, spans[0][0])
        at = spans[-1][1]
        for name, nids, _eids, _slots in plan["computed"]:
            add((at, at), "text", None, pad + _ids_block("nodeids", name, nids))
        spans = _kept_spans(index["elids"], names)
        at = spans[-1][1] if spans else at
        for name, _nids, eids, _slots in plan["computed"]:
            add((at, at), "text", None, pad + _ids_block(
                "elementnodeids", name, eids))
    for step in index["steps"]:
        for table, layouts, action in (("vars", plan["nodes"], "node"),
                                       ("elvars", plan["elements"],
                                        "element")):
            for name, span in step[table].items():
                if name in names:
                    add(_whole_lines(src, span), "drop")
                elif name in layouts and _touches(layouts[name]):
                    add(span, action, step, name)
        if plan["has_stress"]:
            spans = _kept_spans(step["vars"], names)
            pad = _indent_before(src, spans[0][0])
            at = spans[-1][1]
            for item in plan["computed"]:
                add((at, at), "new_node", step, (pad, item))
            spans = _kept_spans(step["elvars"], names)
            at = spans[-1][1] if spans else at
            for item in plan["computed"]:
                add((at, at), "new_element", step, (pad, item))
    return sorted(out, key=lambda e: e[:2])


def _pump(src, dst, start, end):
    """Copy [start, end) of the open src to the open dst."""
    src.seek(start)
    left = end - start
    while left > 0:
        block = src.read(min(_CHUNK, left))
        if not block:
            break
        dst.write(block)
        left -= len(block)


def _write_ids(src, dst, begin, end, layout):
    src.seek(begin)
    head = src.read(min(end - begin, 1024))
    src.seek(end - 32)
    tail = src.read(32)
    dst.write(head[:head.index(">") + 1])
    dst.write(_b64_text(layout["raw"] +
                        _bytes_of(array.array("i", layout["ids"]))))
    dst.write(tail[tail.rindex("<"):])


def _write_variable(src, dst, step, data, action, name, plan):
    table = "vars" if action == "node" else "elvars"
    layouts = plan["nodes" if action == "node" else "elements"]
    span = step[table][name]
    block = data["cache"].pop(span, None) or _read_block(src, span)
    computed = data["values"].get(name) if action == "node" else None
    dst.write(_rewrite_block(block, layouts[name], computed, plan))


def _write_results(src, dst, plan):
    """Write <results> up to its end tag, with the shells. Returns the
    stress routes of the last step."""
    index = plan["index"]
    pos = index["start"]
    current = data = routes = None
    for begin, _serial, end, action, step, argument in _edits(src, plan):
        _pump(src, dst, pos, begin)
        pos = end
        if step is not None and step is not current:
            current = step
            data = plan.pop("first", None) or _step_values(plan, step, src)
            routes = data["routes"]
            if plan["has_stress"] and [
                    c for c in plan["computed"] if c[0] not in data["values"]]:
                raise _Refused(tr(
                    "De spanning ontbreekt in een van de stappen.",
                    "The stress is missing in one of the steps."))
        if action == "text":
            dst.write(argument)
        elif action == "ids":
            _write_ids(src, dst, begin, end, argument)
        elif action in ("node", "element"):
            _write_variable(src, dst, step, data, action, argument, plan)
        elif action == "new_node":
            pad, item = argument
            dst.write(_new_variable("nodevariable", item[0], pad,
                                    data["values"][item[0]], plan))
        elif action == "new_element":
            pad, item = argument
            values = data["values"][item[0]]
            dst.write(_new_variable("elementnodevariable", item[0], pad,
                                    [values[i] for i in item[3]], plan))
    _pump(src, dst, pos, index["end"])
    return routes


def _nonlinear_material(view, model_data):
    """True when a drawn beam has a material that is not linear elastic."""
    materials = model_data.get("materials", {})
    for beam in view["beams"]:
        for key in materials.get(beam["material"]) or ():
            if key == "hyper" or key.startswith("plastic"):
                return True
    return False


def _without_stress(model_data, view):
    """model_data for shell_values when its stress is not used: without an
    E it would warn for every step."""
    out = dict(model_data)
    out["materials"] = dict((b["material"], {"E": 1.0})
                            for b in view["beams"])
    return out


def _view_result(ok, text, steps=0, routes=None, not_on_shells=None):
    return {"ok": ok, "text": text, "steps": steps,
            "routes": routes or {"forces": 0, "kinematics": 0},
            "not_on_shells": not_on_shells or []}


def _target_solution(path, first, configuration):
    """(begin, end) of the solution of configuration, as splice_results."""
    sols = _solutions(path, first)
    same = [s for s in sols if s[2] == configuration]
    if not same and configuration is not None:
        same = [s for s in sols if s[2] is None]
    if not same:
        raise _Refused(tr("Geen solution voor configuratie {0}.",
                          "No solution for configuration {0}.").format(
                              configuration))
    return same[0][0], same[0][1]


def _view_plan(src, path, begin, results, end, view, model_data):
    """Everything that holds for all steps of add_section_view, and the
    values of the first step (they decide whether there is a stress)."""
    import bridge_section_view as section_view
    index = _index_results(path, results, end)
    if not index["steps"] or index["end"] is None:
        raise _Refused(_no_result_text())
    for step in index["steps"]:
        for name in _SHELL_DISPL + _SHELL_ROT:
            if name not in step["vars"] or name not in index["ids"]:
                raise _Refused(_no_rotation_text())
    src.seek(begin)
    text = src.read(results - begin)
    nl = _newline(text)
    copy = _read_copy(text.split(nl), view, model_data, section_view)
    nodes, elements = _layouts(src, index, view, copy)
    for name in _SHELL_DISPL + ("displmag",):
        if name in nodes:
            nodes[name] = _all_shells(nodes[name], view)
    modes = len([s for s in index["steps"] if s["kind"] == "mode"]) > 0
    nonlinear = _nonlinear_material(view, model_data)
    first = view["nids"][0]
    plan = {"index": index, "view": view, "nl": nl,
            "section_view": section_view,
            "lines": section_view.thin_beam_lines(
                section_view.insert_into_copy(copy["lines"], view), view),
            "old": copy["old"], "elset": view["elset"],
            "drop": set(copy["old"]) | set([view["elset"]]),
            "names": set(_SECTION_NAMES),
            "stress": tr(SECTION_STRESS[0], SECTION_STRESS[1]),
            "shear": tr(SECTION_SHEAR[0], SECTION_SHEAR[1]),
            "von_mises": tr(SECTION_VON_MISES[0], SECTION_VON_MISES[1]),
            "tables": ({} if modes or nonlinear else
                       section_tables(path, view, model_data)),
            "computed": [],
            "nodes": nodes, "elements": elements,
            "model": (_without_stress(model_data, view)
                      if modes or nonlinear else model_data),
            "forces": not modes, "modes": modes, "nonlinear": nonlinear,
            "has_stress": False,
            "element_ids": [e[0] for e in view["elements"]],
            "element_slots": [n - first for e in view["elements"]
                              for n in e[2]],
            "beam_nodes": sorted(set([n for b in view["beams"]
                                      for n in b["nodes"]]))}
    data = _step_values(plan, index["steps"][0], src)
    if plan["stress"] in data["values"] and not modes and not nonlinear:
        plan["has_stress"] = True
        data["values"]["stressptu"] = data["values"][plan["stress"]]
        if "stressptu" in nodes:
            nodes["stressptu"] = _all_shells(nodes["stressptu"], view)
        plan["computed"] = [(plan["stress"], view["nids"], plan["element_ids"],
                             plan["element_slots"])]
        if plan.get("wanted"):
            plan["computed"] += [
                (name, plan["wanted_ids"], plan["wanted_elements"],
                 plan["wanted_slots"])
                for name in (plan["shear"], plan["von_mises"])]
    else:
        plan["model"] = _without_stress(model_data, view)
        plan["wanted"] = []
    plan["first"] = data
    return plan


def _view_text(plan, steps, routes, note, not_on_shells, liml_path):
    view = plan["view"]
    parts = [tr("Doorsnede in de solution: {0} knopen, {1} elementen, {2} "
                "stap(pen).",
                "Section view in the solution: {0} nodes, {1} elements, {2} "
                "step(s).").format(len(view["nids"]), len(view["elements"]),
                                   steps)]
    if plan["has_stress"]:
        parts.append(tr("Spanning: {0}, uit de snedekrachten voor {1} balken "
                        "en uit de kinematica voor {2}.",
                        "Stress: {0}, from the section forces for {1} beams "
                        "and from the kinematics for {2}.").format(
                            plan["stress"], routes["forces"],
                            routes["kinematics"]))
    elif plan["modes"]:
        parts.append(tr("Modes: geen spanning op de vorm.",
                        "Modes: no stress on the shape."))
    elif plan["nonlinear"]:
        parts.append(tr("Niet-lineair materiaal: geen spanning op de vorm.",
                        "Nonlinear material: no stress on the shape."))
    else:
        parts.append(tr("Geen spanning op de vorm: E of doorsnede ontbreekt.",
                        "No stress on the shape: E or section is missing."))
    if plan["has_stress"]:
        parts.append(_shear_text(plan))
    if not_on_shells:
        parts.append(tr("Zonder waarde op de balken, dus ook niet op de "
                        "vorm: {0}.",
                        "No value on the beams, so none on the shape "
                        "either: {0}.").format(", ".join(not_on_shells)))
    if plan["old"]:
        parts.append(tr("{0}.bak is de vorige versie, ook met vormen.",
                        "{0}.bak is the previous version, also with shells."
                        ).format(os.path.basename(liml_path)))
    if note:
        parts.append(note)
    return " ".join(parts)


def _shear_text(plan):
    view = plan["view"]
    if not plan["tables"]:
        return tr("Geen schuifspanning en von Mises op de vorm: die vragen de "
                  "tabel van een Code-Aster-run ({0}).",
                  "No shear stress and von Mises on the shape: those need the "
                  "table of a Code-Aster run ({0}).").format(SECTION_SUFFIX)
    if not plan.get("wanted"):
        return tr("Geen schuifspanning en von Mises op de vorm: de "
                  "snedekrachten ontbreken (resultaatveld beam_forces).",
                  "No shear stress and von Mises on the shape: the section "
                  "forces are missing (result field beam_forces).")
    left = len(view["nids"]) - len(plan["wanted"])
    text = tr("Schuifspanning en von Mises: {0}, {1}.",
              "Shear stress and von Mises: {0}, {1}.").format(
                  plan["shear"], plan["von_mises"])
    if left:
        text += u" " + tr("{0} knopen van de vorm hebben ze niet.",
                          "{0} nodes of the shape do not have them.").format(
                              left)
    return text


def _section_files(liml_path):
    """The _section.json files that may belong to this model: that of the
    current run first, then the newest first. A run shortens a long model
    name, hence the current run on its own. The prefix also fits a model
    called <model>_x: no harm, match_table looks at the section itself, and a
    table depends on nothing else."""
    folder = work_dir_path()
    stem = model_stem(liml_path) + "_"
    found = []
    try:
        for name in os.listdir(folder):
            if name.startswith(stem) and name.endswith(SECTION_SUFFIX):
                path = os.path.join(folder, name)
                found.append((os.path.getmtime(path), path))
    except OSError:
        pass
    found.sort(reverse=True)
    paths = [p[1] for p in found]
    current = os.path.join(folder, run_name(SECTION_SUFFIX))
    if os.path.exists(current):
        paths.insert(0, current)
    return paths[:_MAX_SECTION_FILES]


def _read_section_file(path):
    """The contents of a _section.json, or None when it cannot be used."""
    try:
        with io.open(path, encoding="utf-8") as f:
            data = json.loads(f.read())
    except (IOError, OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != 1:
        return None
    return data


def _usable_entry(entry, shape, model_data, name, section_view):
    """True for a section of a _section.json that fits this section and is
    whole. A damaged entry counts as absent: it must not cost the shells."""
    try:
        for key in ("EY", "EZ"):
            float(entry[key])
        for row in entry["points"]:
            if len(row) not in (8, 14):
                return False
            [float(x) for x in row]
        return bool(section_view.match_table(entry, shape, model_data, name))
    except Exception:       # IronPython: float(None) is a .NET null reference
        return False


def section_tables(liml_path, view, model_data):
    """
    {material: entry of a _section.json} for the drawn materials. A table
    depends on the section only, so that also a reload of an older result
    finds it; bridge_section_view.match_table decides that it belongs.
    """
    import bridge_section_view as section_view
    wanted = set(b["material"] for b in view["beams"])
    shapes = view["shapes"]
    out = {}
    for path in _section_files(liml_path):
        data = _read_section_file(path)
        for entry in (data or {}).get("sections") or []:
            name = entry.get("material") if isinstance(entry, dict) else None
            if name in wanted and name not in out and _usable_entry(
                    entry, shapes[name], model_data, name, section_view):
                out[name] = entry
        if len(out) == len(wanted):
            break
    return out


def _log_section_notes(fragment_path):
    """The warnings of the stress over the section (bridge_section_stress) in
    the log of the run: the job can only print them in its .mess."""
    if not fragment_path or not fragment_path.endswith(RESULTS_SUFFIX):
        return
    path = fragment_path[:-len(RESULTS_SUFFIX)] + SECTION_SUFFIX
    if os.path.exists(path):
        for text in (_read_section_file(path) or {}).get("warnings", []):
            log(text)


def _add_section_view(liml_path, tmp, view, model_data, configuration):
    if not os.path.exists(liml_path):
        raise _Refused(tr("Model niet gevonden: {0}",
                          "Model not found: {0}").format(liml_path))
    if not view or not view.get("nids") or not view.get("elements"):
        raise _Refused(tr("Geen balken om te tekenen.",
                          "No beams to draw."))
    sol = _find_solution_start(liml_path)
    if sol < 0:
        raise _Refused(tr("Het model heeft geen solution. Reken eerst.",
                          "The model has no solution. Calculate first."))
    note = ""
    if configuration is None:
        configuration, note = pick_configuration(liml_path)
    if cyclic_info(_read_range(liml_path, 0, sol)) is not None:
        raise _Refused(tr(
            "Cyclische symmetrie: de doorsnede kan niet in de solution, de "
            "knoopnummers kunnen botsen.",
            "Cyclic symmetry: the section view cannot go into the solution, "
            "the node numbers can clash."))
    begin, end = _target_solution(liml_path, sol, configuration)
    results = _find_from(liml_path, "<results", begin, ">/ \t\r\n")
    if not begin <= results < end:
        raise _Refused(_no_result_text())
    src = open(liml_path, "rb")
    dst = None
    try:
        plan = _view_plan(src, liml_path, begin, results, end, view,
                          model_data)
        dst = open(tmp, "wb")
        _copy_range(liml_path, dst, 0, begin)
        dst.write(plan["nl"].join(plan["lines"]))
        routes = _write_results(src, dst, plan)
        _copy_from(liml_path, dst, plan["index"]["end"])
    finally:
        src.close()
        if dst is not None:
            dst.close()
    _replace_with_bak(tmp, liml_path)
    steps = len(plan["index"]["steps"])
    names = [name for table in (plan["nodes"], plan["elements"])
             for name in table if not table[name]["ids"]]
    routes = (routes if plan["has_stress"] and routes else
              {"forces": 0, "kinematics": 0})
    return _view_result(True, _view_text(plan, steps, routes, note, names,
                                         liml_path), steps, routes, names)


def add_section_view(liml_path, view, model_data, configuration=None):
    """
    Put the shells of view (bridge_section_view.build_view) with their
    values in the solution of configuration in liml_path; see the header of
    this block. Everything outside that solution stays byte-identical, an
    earlier section view in it is replaced. configuration None:
    pick_configuration. Written through a .tmp file; the previous version
    becomes .bak.

    Returns {"ok": bool, "text": bilingual status, "steps": number of steps
    or modes, "routes": {"forces": beams, "kinematics": beams} of the stress
    in the last step, "not_on_shells": variables without a value on any
    drawn beam}. An ordinary refusal is ok False, not an exception.
    """
    tmp = liml_path + ".tmp"
    try:
        return _add_section_view(liml_path, tmp, view, model_data,
                                 configuration)
    except _Refused as e:
        return _view_result(False, e.text)
    except Exception as e:      # a display extra must not stop the caller
        return _view_result(False, tr(
            "De doorsnede is niet toegevoegd: {0}",
            "The section view was not added: {0}").format(e))
    finally:
        # without the .liml, the .tmp may be the only complete file
        if os.path.exists(tmp) and os.path.exists(liml_path):
            try:
                os.remove(tmp)
            except OSError:
                pass


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


_JUMP = re.compile(r"^BRIDGE_SPRONG\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")
_GUARD_END = re.compile(r"^BRIDGE_VANGNET\s+(\S+)")


def read_step_guard(mess_path):
    """
    Step guard and jump check of POU_D_T_GD beams from the .mess
    (bridge_to_aster._guarded_solve, aster_results_export.print_jump_check):
    {"ended": t the guard stopped or None, "jumps": [(t0, t1, u0, u1)]}.
    """
    out = {"ended": None, "jumps": []}
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            line = line.strip()
            m = _GUARD_END.match(line)
            if m:
                out["ended"] = float(m.group(1))
                continue
            m = _JUMP.match(line)
            if m:
                out["jumps"].append(tuple(float(m.group(i))
                                          for i in range(1, 5)))
    finally:
        f.close()
    return out


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
    return _array_of(typecode, base64.b64decode("".join(chunks)))


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
