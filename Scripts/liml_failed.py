# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Hide failed elements per time step in Mecway's own results (STAPPENPLAN E1, OV 57).

Every element that ever fails gets private copies of its nodes in the <solution> mesh of a
solved .liml (new node numbers above every existing one). The copies carry the values of their
originals in every step (others="follow", OPEN_VRAGEN 71), except the displacement: from the
failure step on it puts them on the element's frozen centroid (exact at deformation scale 1), so
the element shrinks to a point. At deformation scale s a collapsed node is drawn at
(1 - s) X + s c: the element reappears at |1 - s| times its size (full size at s = 0, mirrored at
s = 2). The model part of the file stays byte for byte (keep_original adds two <configuration>
lines after <liml>); element-node values never change.

Copy rule: a node that an intact element also uses stays with the intact elements. When all
owners of a node fail, the latest-failing owner keeps the original (it collapses with it), the
others get copies. Supports (1.0.3): an original whose largest |value| of a reaction variable
(REACTION_PREFIXES) over the steps exceeds REACTION_REL_TOL times the largest of its group
(reactionforce*, reactionmom*: _react_group) in the file, or that has a NaN/inf reaction, is
never collapsed: the latest-failing owner gets a copy too, and the original stays in place with
its real displacement and all its values, used by no element (also in mode "copies"); it then
counts in the maxandmin group name="" (recomputed, or added as the first component). Up to 1.0.2
its reaction stayed while its displacement collapsed, so Mecway drew the reaction at a moved
spot. That Mecway draws the reaction of a node in no element on its place is NOT verified
(ASSUMPTIONS 73). Pass 1 now also decodes the reaction blocks, so a broken one is refused there
(layout, bad_base64, value_count), also by scan() and when nothing failed. 1.0.4 (KNOWN_BUGS
87): when both reactionforce* and reactionmom* have values, a group whose peak is only round-off
next to the other (REACTION_NOISE_TOL with the model length, or REACTION_NOISE_RAW) marks no
supports (report key noise_reaction_groups); Code-Aster's REAC_NODA under a pure end moment
otherwise made every free node a support. One group alone keeps the 1.0.3 rule. 1.0.5
(KNOWN_BUGS 88): no change in behaviour; the number characters of _parse_time are written in
pieces (_NUM_CHARS), as a run of ten digits in the source trips a phone-number check.

Processed marker (OPEN_VRAGEN 72): the first line inside the target <results> becomes
<globalvariable name="failed_hidden">N</globalvariable>, N = number of hidden elements. Mecway
35.0.9802 keeps a numeric <globalvariable> on <results> level there through re-saves (it moves
one there itself) and turns a non-numeric text into 0 (research note 10 section 4.3, gate of
1.0.1: N = 3, 12345678 and 16777217 survived two re-saves, single and double precision).
Presence decides; N is information. The attribute limlfailed="1.0.0" of version 1.0.0 (dropped
by Mecway on re-save) is still read.

Self-contained on purpose: Python 2.7 (IronPython 2.7.9) and 3, stdlib only, no imports from
AdvancedToolsHub. MecwayAsterBridge keeps a byte-identical copy (drift test, STAPPENPLAN E4);
change this file only here and bump VERSION. Design and review:
docs/reviews/2026-11-10_E1_kern_plan.md; contract of the variable `failed`:
docs/design/CONTRACT_FAILED.md. Messages are (code, (en, nl)).

API: process(), scan(), processed_marker(), marker_count(), message(); refusals raise
LimlFailedError.

Flag providers, fixed order, the first available decides for the whole file:
  1 `failed`         element-node variable of the bridge (contract failed/1: exactly 0.0/1.0,
                     uniform per element, monotone; refused otherwise);
  2 `Element_status` OpenRadioss /ANIM/ELEM/OFF (dead = all values of the element 0.0);
  3 events           <run>_events.json of MWradiossHub (the DELETE ... ELEMENT and RUPTURE lines
                     of the .out, mwradiosshub/events.py; time_upper where present, else time;
                     element_type is ignored: the element ids are the deck ids, which equal the
                     Mecway ids in route 1+plak, unique over all types; the event times are taken
                     as seconds, like the <timestep time>: SI deck times NOT verified). A file
                     without a usable erosion event (none, or only without time or with unknown
                     elements) is no source: warning events_empty, next provider (KNOWN_BUGS 76);
  4 stress rule      only when the caller says the result is OpenRadioss: all element-node
                     stress components 0.0 (the prototype's geometric safety net is dropped on
                     purpose: it guessed, the providers above do not).
Failure step k = start of the final run of dead steps; centroid = mean of X + u over the
distinct nodes at step k - 1 (step 0 when k = 0, allowed for providers 1 and 3).

File layout handled without an XML parser (mecway skill liml-format 9; research note 10):
line based, one structural tag per line, base64 blocks in any layout (single line, data on the
opening line or the next, closing tag on its own line or after the data); a re-encoded block
keeps the layout of its input, so an identity run is byte-identical.
"""

import base64
import binascii
import io
import json
import math
import os
import re
import sys
import time
from array import array

VERSION = "1.0.5"
CONTRACT_FAILED = "failed/1"

# --- switches (module constants; tests change them) -------------------------------------
# Marker of a processed file (see the module docstring); False writes no marker (the input
# check stays).
WRITE_MARKER = True
MARKER_VAR = b"failed_hidden"      # <globalvariable name=...> on <results> level (1.0.1)
MARKER_ATTR = b"limlfailed"        # attribute on <results> of 1.0.0: read, removed on force
# Element_status 0 in the first output step carries no information when that step is t = 0;
# such elements stay visible. True hides them from step 0 on (decide after gate E0(b)).
STATUS_HIDE_DEAD_FROM_START = False

DISPL = (b"displx", b"disply", b"displz")
DISPLMAG = b"displmag"
# Extensive node variables: a copy would count them twice in sums over nodes, so they never
# get copies in their <nodeids> (review finding 1); their values mark the supports (1.0.3).
# Prefixes of Mecway's names.
REACTION_PREFIXES = (b"reaction",)
# 1.0.3: a node is a support when its largest |reaction| over the steps exceeds this fraction of
# the largest of its group (_react_group) in the file; below it a value counts as round-off
# (Code-Aster's REAC_NODA on free nodes: measured 1e-9..1e-5 of the peak, bridge 11 Nov 2026,
# ASSUMPTIONS 73)
REACTION_REL_TOL = 1e-3
# 1.0.4 (KNOWN_BUGS 87): of the groups reactionforce (N) and reactionmom (N m) one holds only
# round-off when its peak is small next to the other (_react_noise): P_F * L < NOISE_TOL * P_M
# or P_F < NOISE_RAW * P_M for the forces, P_M < NOISE_TOL * P_F * L or P_M < NOISE_RAW * P_F
# for the moments; L = diagonal of the bounding box of the element nodes (m; a .liml is SI).
# Such a group marks no supports. NOISE_RAW is the solver's own scale: RESI_GLOB_RELA of
# Code-Aster divides the largest residual over all DOFs, forces and moments unscaled, by the
# load plus reactions (bridge docs, U4.51.03) [I]; NL-81 gave P_F / P_M = 2.1e-6 (L = 1 m).
REACTION_NOISE_TOL = 1e-3
REACTION_NOISE_RAW = 1e-4
# Characters of the number in a time attribute (_parse_time). 1.0.5 (KNOWN_BUGS 88): written in
# pieces, so the source holds no run of ten digits (a privacy check reads that as a phone number).
_NUM_CHARS = b"01234" b"56789" b"+-.eE"
REACT_FORCE = b"reactionforce"
REACT_MOM = b"reactionmom"
FAILED_VAR = b"failed"
STATUS_VAR = b"Element_status"
STRESS_VARS = (b"stressxx", b"stressyy", b"stresszz", b"stressxy", b"stressyz", b"stresszx",
               b"vonmises")
EVENTS_SCHEMAS = ("mwhubpost-events/1", "mwrad-events/1")
TIME_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, u"µs": 1e-6, u"μs": 1e-6,
              "min": 60.0, "h": 3600.0}
MODES = ("collapse", "copies", "identity")
OTHERS = ("zero", "follow")
SOLVERS = (None, "radioss", "aster")
# keep_original: names of the two configurations (original first); no white space, Mecway
# refuses a configuration name with a space ("Configuration ... is not defined", gate 11 Nov
# 2026 [V Mecway 35])
KEEP_NAMES = (u"Origineel", u"Bezweken_verborgen")
B64_WIDTH = 64                 # Mecway's base64 line width (research note 10)
_TICK = 4096                   # lines between progress/cancel polls (a power of two)
_TICK_BYTES = 4 << 20          # ... and at least every 4 MB read (long lines)
_PLAN_TICK = 4096              # loop iterations between polls in _plan (a power of two)
_PASS1_SHARE = 0.30            # process(): pass 1 0-0.30, plan 0.30-0.35, pass 2 0.35-1
_PLAN_SHARE = 0.05
_SCAN_PASS1_SHARE = 0.90       # scan(): pass 1 0-0.90, plan 0.90-1

PY3 = sys.version_info[0] >= 3

_TEXT = {
    # refusals
    "bad_argument": (u"Invalid argument: {0}.", u"Ongeldig argument: {0}."),
    "not_found": (u"File not found: {0}", u"Bestand niet gevonden: {0}"),
    "same_path": (u"Input and output are the same file.", u"Invoer en uitvoer zijn hetzelfde bestand."),
    "read_error": (u"Cannot read {0}: {1}", u"Kan {0} niet lezen: {1}"),
    "write_error": (u"Cannot write {0}: {1}", u"Kan {0} niet schrijven: {1}"),
    "not_liml": (u"This is not a Mecway .liml file.", u"Dit is geen Mecway-.liml-bestand."),
    "no_solution": (u"The file has no solved results (<solution>).",
                    u"Het bestand heeft geen opgeloste resultaten (<solution>)."),
    "configurations": (u"The file holds {0} solutions (configurations {1}); choose one configuration.",
                       u"Het bestand bevat {0} oplossingen (configuraties {1}); kies een "
                       u"configuratie."),
    "keep_original_configurations": (u"The original results can only be kept next to the hidden ones "
                                     u"in a model without configurations.",
                                     u"De oorspronkelijke resultaten kunnen alleen naast de "
                                     u"verborgen worden bewaard in een model zonder configuraties."),
    "configuration_not_found": (u"Configuration {0} has no solution in this file.",
                                u"Configuratie {0} heeft geen oplossing in dit bestand."),
    "modal_result": (u"Modal or buckling results have no time steps; nothing to hide.",
                     u"Modale of knikresultaten hebben geen tijdstappen; er valt niets te verbergen."),
    "no_timesteps": (u"Static results without time steps; nothing to hide.",
                     u"Statische resultaten zonder tijdstappen; er valt niets te verbergen."),
    "already_processed": (u"This file was already processed ({0} failed elements hidden); start from "
                          u"the original result.",
                          u"Dit bestand is al bewerkt ({0} bezweken elementen verborgen); begin bij "
                          u"het oorspronkelijke resultaat."),
    # text of code already_processed for the attribute of version 1.0.0
    "already_processed_version": (u"This file was already processed (failed elements hidden, version "
                                  u"{0}); start from the original result.",
                                  u"Dit bestand is al bewerkt (bezweken elementen verborgen, versie "
                                  u"{0}); begin bij het oorspronkelijke resultaat."),
    "no_flag_source": (u"No failure information found: no variable 'failed' or 'Element_status'{0}.",
                       u"Geen gegevens over bezwijken gevonden: geen variabele 'failed' of "
                       u"'Element_status'{1}."),
    "failed_contract": (u"The variable 'failed' does not follow contract failed/1 (element {0}, "
                        u"step {1}: {2}).",
                        u"De variabele 'failed' volgt het contract failed/1 niet (element {0}, "
                        u"stap {1}: {2})."),
    "events_invalid": (u"The events file {0} cannot be used: {1}",
                       u"Het gebeurtenissenbestand {0} is onbruikbaar: {1}"),
    "time_unit": (u"Unknown or missing time in the results: '{0}'.",
                  u"Onbekende of ontbrekende tijd in de resultaten: '{0}'."),
    "time_order": (u"The time steps are not in ascending order (step {0}).",
                   u"De tijdstappen staan niet op volgorde (stap {0})."),
    "unknown_element": (u"Element {0} of variable {1} is not in the solution mesh.",
                        u"Element {0} van variabele {1} zit niet in het mesh van de oplossing."),
    "unknown_node": (u"Element {0} uses node {1}, which is not in the solution mesh.",
                     u"Element {0} gebruikt knoop {1}, die niet in het mesh van de oplossing zit."),
    "duplicate_id": (u"Number {0} occurs twice in the solution mesh ({1}).",
                     u"Nummer {0} komt twee keer voor in het mesh van de oplossing ({1})."),
    "value_count": (u"Variable {0} has {1} values where {2} are expected.",
                    u"Variabele {0} heeft {1} waarden waar er {2} verwacht worden."),
    "no_displacement": (u"Node {0} of failed element {1} has no displacement.",
                        u"Knoop {0} van bezweken element {1} heeft geen verplaatsing."),
    "bad_base64": (u"Damaged base64 data near line {0}.", u"Beschadigde base64-gegevens bij regel {0}."),
    "bad_number": (u"Unreadable number near line {0}.", u"Onleesbaar getal bij regel {0}."),
    "layout": (u"Unsupported file layout near line {0} ({1}).",
               u"Niet-ondersteunde opbouw van het bestand bij regel {0} ({1})."),
    "platform": (u"Unsupported platform (byte order or integer size).",
                 u"Niet-ondersteund platform (bytevolgorde of grootte van gehele getallen)."),
    "too_large": (u"Not enough memory for this file.", u"Onvoldoende geheugen voor dit bestand."),
    "cancelled": (u"Cancelled.", u"Geannuleerd."),
    # results
    "done": (u"{0} failed elements hidden (source {1}); written to {2}.",
             u"{0} bezweken elementen verborgen (bron {1}); geschreven naar {2}."),
    "done_two": (u"{0} failed elements hidden (source {1}); written to {2} with two "
                 u"configurations: {3} (unchanged results) and {4} (failed elements hidden).",
                 u"{0} bezweken elementen verborgen (bron {1}); geschreven naar {2} met twee "
                 u"configuraties: {3} (ongewijzigde resultaten) en {4} (bezweken elementen "
                 u"verborgen)."),
    "scanned": (u"{0} failed elements found (source {1}).",
                u"{0} bezweken elementen gevonden (bron {1})."),
    "copied": (u"Written without hiding (mode {0}) to {1}.",
               u"Geschreven zonder verbergen (modus {0}) naar {1}."),
    "nothing_failed": (u"No failed elements found (source {0}); nothing written.",
                       u"Geen bezweken elementen gevonden (bron {0}); niets geschreven."),
    # warnings (count first)
    "not_covered": (u"{0} elements have no failure information and stay visible.",
                    u"{0} elementen hebben geen gegevens over bezwijken en blijven zichtbaar."),
    "dead_from_start": (u"{0} elements are marked failed from the first step on (no information); "
                        u"they stay visible.",
                        u"{0} elementen staan vanaf de eerste stap als bezweken (geen informatie); "
                        u"ze blijven zichtbaar."),
    "dead_before_first_step": (u"{0} elements are already failed at the first output step (time > 0); "
                               u"they stay visible.",
                               u"{0} elementen zijn bij de eerste uitvoerstap (tijd > 0) al bezweken; "
                               u"ze blijven zichtbaar."),
    "revived": (u"{0} elements came back after failing; only their last failure counts.",
                u"{0} elementen kwamen terug na het bezwijken; alleen het laatste bezwijken telt."),
    "status_out_of_range": (u"{0} Element_status values lie outside [-1, 1].",
                            u"{0} waarden van Element_status liggen buiten [-1, 1]."),
    "bad_displacement": (u"{0} failed elements have no finite displacement before failing; "
                         u"they stay visible.",
                         u"{0} bezweken elementen hebben geen eindige verplaatsing vóór het "
                         u"bezwijken; ze blijven zichtbaar."),
    "events_missing": (u"Events file {0} not found; not used.",
                       u"Gebeurtenissenbestand {0} niet gevonden; niet gebruikt."),
    "events_empty": (u"Events file {0} lists no usable failed element; not used.",
                     u"Gebeurtenissenbestand {0} noemt geen bruikbaar bezweken element; niet "
                     u"gebruikt."),
    "events_no_time": (u"{0} events without a time are ignored.",
                       u"{0} gebeurtenissen zonder tijd worden genegeerd."),
    "events_coarse_time": (u"{0} events only have the time of the cycle row before the deletion; "
                           u"those elements may disappear up to one output step early.",
                           u"{0} gebeurtenissen hebben alleen de tijd van de cyclusregel vóór het "
                           u"verwijderen; die elementen kunnen tot een uitvoerstap te vroeg "
                           u"verdwijnen."),
    "events_unknown_elements": (u"{0} events refer to elements that are not in the mesh.",
                                u"{0} gebeurtenissen noemen elementen die niet in het mesh zitten."),
    "events_after_last_step": (u"{0} elements fail after the last output step and stay visible.",
                               u"{0} elementen bezwijken na de laatste uitvoerstap en blijven zichtbaar."),
    "events_incomplete": (u"{0} elements have all stresses 0 at the end but are not in the events file.",
                          u"{0} elementen hebben aan het einde alle spanningen 0 maar staan niet in "
                          u"het gebeurtenissenbestand."),
    "precision_mixed": (u"{0} value blocks do not match the precision of the results.",
                        u"{0} waardeblokken passen niet bij de precisie van de resultaten."),
    "mm_group_mismatch": (u"{0} maxandmin groups could not be recomputed; they keep their old range.",
                          u"{0} maxandmin-groepen konden niet opnieuw berekend worden; ze houden hun "
                          u"oude bereik."),
    "version_old": (u"The file has <liml version> {0} (< 31) with single precision; Mecway may show "
                    u"a dialog when opening it.",
                    u"Het bestand heeft <liml version> {0} (< 31) met enkele precisie; Mecway kan "
                    u"bij het openen een venster tonen."),
    "looks_processed": (u"{0} nodes of failed elements look like copies of an earlier run; the file "
                        u"may have been processed before.",
                        u"{0} knopen van bezweken elementen lijken kopieën van een eerdere run; het "
                        u"bestand is misschien al eerder bewerkt."),
}

WARNING_CODES = ("not_covered", "dead_from_start", "dead_before_first_step", "revived",
                 "status_out_of_range", "bad_displacement", "events_missing", "events_empty",
                 "events_no_time",
                 "events_coarse_time", "events_unknown_elements", "events_after_last_step",
                 "events_incomplete", "precision_mixed", "mm_group_mismatch", "version_old",
                 "looks_processed")


def message(code, *args, **kw):
    """(code, (en, nl)) with the {n} placeholders filled from args (unicode); text_key= takes
    the text of another _TEXT entry under the same code."""
    en, nl = _TEXT[kw.get("text_key") or code]
    a = [_u(x) for x in args]
    return code, (en.format(*a), nl.format(*a))


def _u(x):
    """Text for messages: bytes (file data) are UTF-8; IronPython's str holds file bytes as
    characters < 256, so it is decoded too when that works."""
    if PY3:
        if isinstance(x, bytes):
            return x.decode("utf-8", "replace")
        return x if isinstance(x, str) else u"{0}".format(x)
    if isinstance(x, (str, bytes)):
        try:
            return x.decode("utf-8")
        except Exception:
            try:
                return x.decode("latin-1")
            except Exception:
                return x
    if isinstance(x, unicode):  # noqa: F821 (py2 only)
        return x
    return u"{0}".format(x)


class LimlFailedError(Exception):
    """A refusal: .code, .text = (en, nl), .info (dict)."""

    def __init__(self, code, *args, **kw):
        self.code, self.text = message(code, *args, text_key=kw.get("text_key"))
        self.info = kw.get("info") or {}
        Exception.__init__(self, u"{0}: {1}".format(self.code, self.text[0]))


def _refuse(code, *args, **kw):
    raise LimlFailedError(code, *args, **kw)


# ----------------------------------------------------------------------------- helpers
def _attr(line, name):
    """Raw bytes of attribute `name` (double quotes), or None; single quotes -> layout."""
    key = b" " + name + b'="'
    i = line.find(key)
    if i < 0:
        if line.find(b" " + name + b"='") >= 0:
            raise _Layout("single-quoted attribute")
        return None
    i += len(key)
    j = line.find(b'"', i)
    if j < 0:
        raise _Layout("unterminated attribute")
    return line[i:j]


def _req(line, name):
    """A required attribute; missing -> layout (IronPython: int(None)/float(None) can raise a
    SystemError instead of a TypeError)."""
    v = _attr(line, name)
    if v is None:
        raise _Layout("missing attribute " + name.decode("ascii"))
    return v


class _Layout(Exception):
    """Internal: turned into a `layout` refusal with the line number."""


_ENT = re.compile(br"&(#x[0-9A-Fa-f]+|#[0-9]+|amp|lt|gt|quot|apos);")
_NAMED = {b"amp": b"&", b"lt": b"<", b"gt": b">", b"quot": b'"', b"apos": b"'"}


def _unescape(b):
    """XML character references in an attribute value (bytes, UTF-8)."""
    if b is None or b.find(b"&") < 0:
        return b
    # pieces by hand: IronPython 2.7.9's re.sub with a function dropped the named entities
    # (1.0.1: "A&amp;B" became "AB")
    out = []
    last = 0
    for m in _ENT.finditer(b):
        out.append(b[last:m.start()])
        g = m.group(1)
        if g in _NAMED:
            out.append(_NAMED[g])
        else:
            try:
                cp = int(g[2:], 16) if g[:2] == b"#x" else int(g[1:])
                ch = chr(cp) if PY3 else unichr(cp)  # noqa: F821 (py2 only)
                out.append(ch.encode("utf-8"))
            except (ValueError, OverflowError):     # not a character: keep the text
                out.append(m.group(0))
        last = m.end()
    out.append(b[last:])
    return b"".join(out)


def _frombytes(tc, raw):
    a = array(tc)
    if PY3:
        a.frombytes(raw)
    else:
        a.fromstring(raw)
    return a


def _tobytes(a):
    return a.tobytes() if PY3 else a.tostring()


def _eol(raw):
    if raw.endswith(b"\r\n"):
        return b"\r\n"
    return b"\n" if raw.endswith(b"\n") else b""


def _close(a, b):
    return a == b or abs(a - b) <= 1e-6 * max(abs(a), abs(b))


def _fmt15(x):
    return ("%.15G" % x).encode("ascii")


def _finite(x):
    return x == x and not math.isinf(x)


def _is_solution_tag(s):
    if not s.startswith(b"<solution"):
        return False
    nxt = s[9:10]
    return nxt in (b">", b" ", b"\t", b"\r", b"\n", b"/", b"")


# the <solution ...> start tag up to its '>' (quoted attribute values may hold '>')
_SOL_TAG = re.compile(b"<solution(?:[^>\"']|\"[^\"]*\"|'[^']*')*>")


def _sol_empty(s):
    """For a stripped <solution> line: True when the element also ends on this line
    (<solution ... /> or <solution ...></solution>, e.g. a configuration without results,
    KNOWN_BUGS 136 of the bridge): an empty solution of its own that never extends into the
    next one. False when it stays open; None when the start tag does not close on this line."""
    m = _SOL_TAG.match(s)
    if m is None:
        return None
    end = m.end()
    if s[end - 2:end] == b"/>":
        return True
    return s.find(b"</solution", end) >= 0


def _gv_marker(s):
    """For a stripped line: None when it is not <globalvariable name="failed_hidden">, else
    (text, complete): the text between the tags (u"" when empty) and whether the element closes
    on this line. The name is compared exactly; a single-quoted name raises _Layout."""
    if not s.startswith(b"<globalvariable"):
        return None
    if s[15:16] not in (b" ", b"\t", b">", b"/", b"\r", b"\n", b""):
        return None
    if _attr(s, b"name") != MARKER_VAR:
        return None
    gt = s.find(b">")
    if gt < 0:
        return u"", False
    if s[gt - 1:gt] == b"/":
        return u"", True
    end = s.find(b"</globalvariable", gt)
    if end < 0:
        return s[gt + 1:].strip().decode("utf-8", "replace"), False
    return s[gt + 1:end].strip().decode("utf-8", "replace"), True


def _conf_list(names):
    """Text of the configuration names of the solutions (for the refusal)."""
    return u", ".join(u"-" if n is None else n for n in names)


def _xml_attr(text):
    """Unicode -> escaped UTF-8 bytes for an attribute value in double quotes."""
    t = text.replace(u"&", u"&amp;").replace(u"<", u"&lt;").replace(u">", u"&gt;")
    return t.replace(u'"', u"&quot;").encode("utf-8")


def _with_conf(raw, name):
    """The <solution> line with configuration="name" added (it has none: checked in pass 1)."""
    i = raw.find(b"<solution") + len(b"<solution")
    return raw[:i] + b' configuration="' + _xml_attr(name) + b'"' + raw[i:]


def marker_count(text):
    """The hidden count of a marker text ('3', '3.0', '3E0'; a unit after a space is ignored),
    or None when it is not a whole number >= 0."""
    try:
        x = float(text.split()[0])
    except (IndexError, ValueError):
        return None
    if not _finite(x) or x < 0 or x != math.floor(x):
        return None
    return int(x)


def _parse_time(raw):
    """Seconds from a time attribute ('0.001 s'), or raise ValueError."""
    t = raw.strip()
    i = 0
    while i < len(t) and t[i:i + 1] in _NUM_CHARS:
        i += 1
    num = float(t[:i])
    unit = t[i:].strip().decode("utf-8")
    if unit == u"":
        return num
    if unit not in TIME_UNITS:
        raise ValueError(unit)
    return num * TIME_UNITS[unit]


def _index(ids, what):
    """Position lookup for ids (array('i')): a dense array when the ids are compact, else a
    dict (review finding 7). Returns get(id) -> position or -1."""
    n = len(ids)
    if n == 0:
        return lambda i: -1
    lo = min(ids)
    hi = max(ids)
    if lo >= 0 and hi <= 4 * n + 1024:
        a = array("i", [-1]) * (hi + 1)
        for p in range(n):
            i = ids[p]
            if a[i] >= 0:
                _refuse("duplicate_id", i, what)
            a[i] = p

        def get(i):
            return a[i] if 0 <= i <= hi else -1
        return get
    d = {}
    for p in range(n):
        i = ids[p]
        if i in d:
            _refuse("duplicate_id", i, what)
        d[i] = p
    return lambda i: d.get(i, -1)


def _replace(tmp, path):
    try:
        os.replace(tmp, path)          # Python 3
    except AttributeError:             # Python 2 / IronPython: not atomic, as anim_index
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)


def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# ----------------------------------------------------------------------------- base64 blocks
class _Block(object):
    """One base64 element (<nodeids>, <elementnodeids>, <valuessingle>, <valuesdouble>) and
    its layout, so it can be written back the same way."""

    __slots__ = ("tag", "name", "prefix", "eol", "chunks", "single", "selfclose", "tail",
                 "first_on_open", "open_rest", "indent", "ceol", "close_after", "close_raw",
                 "line", "raw_open")

    def __init__(self, raw, tag, name, line):
        self.tag = tag
        self.name = name
        self.line = line
        self.raw_open = raw
        self.eol = _eol(raw)
        self.single = self.selfclose = self.close_after = self.first_on_open = False
        self.indent = self.ceol = self.close_raw = self.tail = None
        self.open_rest = b""
        self.chunks = []
        i = raw.find(b"<" + tag)
        gt = raw.find(b">", i)
        if gt < 0:
            raise _Layout("tag not closed on its line")
        if raw[gt - 1:gt] == b"/":
            self.selfclose = True
            self.prefix = raw[:i]
            self.tail = raw[gt + 1:]
            return
        self.prefix = raw[:gt + 1]
        body = raw[gt + 1:len(raw) - len(self.eol)]
        j = body.find(b"</")
        if j >= 0:
            self.single = True
            self.chunks.append(body[:j].strip())
            self.tail = body[j:] + self.eol
            return
        first = body.strip()
        if first.find(b"<") >= 0:
            raise _Layout("markup inside base64 data")
        self.first_on_open = bool(first)
        self.open_rest = body
        if first:
            self.chunks.append(first)

    def done(self):
        return self.single or self.selfclose or self.close_raw is not None or self.close_after

    def feed(self, raw):
        """Add one line; True when the block is complete."""
        j = raw.find(b"</")
        lt = raw.find(b"<")
        if lt >= 0 and lt != j:
            raise _Layout("markup inside base64 data")
        if j < 0:
            if self.indent is None:
                self.indent = raw[:len(raw) - len(raw.lstrip())]
                self.ceol = _eol(raw)
            self.chunks.append(raw.strip())
            return False
        before = raw[:j]
        if before.strip():
            if self.indent is None:
                self.indent = before[:len(before) - len(before.lstrip())]
            self.chunks.append(before.strip())
            self.close_after = True
            self.tail = raw[j:]
        else:
            self.close_raw = raw
        return True

    def data(self):
        try:
            return base64.b64decode(b"".join(self.chunks))
        except (binascii.Error, TypeError, ValueError):
            _refuse("bad_base64", self.line)

    def emit(self, raw_bytes):
        """Lines of this block with new contents, in the input's layout."""
        text = base64.b64encode(raw_bytes)
        if self.selfclose:
            if not text:
                return [self.raw_open]
            return [self.prefix + b"<" + self.tag + b">" + text + b"</" + self.tag + b">" + self.tail]
        if self.single:
            return [self.prefix + text + self.tail]
        width = len(self.chunks[0]) if len(self.chunks) >= 2 and self.chunks[0] else B64_WIDTH
        chunks = [text[i:i + width] for i in range(0, len(text), width)]
        ind = self.indent if self.indent is not None else b""
        ceol = self.ceol if self.ceol is not None else self.eol
        out = []
        if self.first_on_open:
            out.append(self.prefix + (chunks[0] if chunks else b"") + self.eol)
            rest = chunks[1:]
        else:
            out.append(self.prefix + self.open_rest + self.eol)
            rest = chunks
        if self.close_after:
            for c in rest[:-1]:
                out.append(ind + c + ceol)
            out.append(ind + (rest[-1] if rest else b"") + self.tail)
        else:
            for c in rest:
                out.append(ind + c + ceol)
            out.append(self.close_raw)
        return out


def _new_block(raw, tag, name, line):
    return _Block(raw, tag, name, line)


def _values_tag(s):
    if s.startswith(b"<valuessingle"):
        return b"valuessingle"
    if s.startswith(b"<valuesdouble"):
        return b"valuesdouble"
    return None


# ----------------------------------------------------------------------------- state
class _State(object):
    pass


class _Ticker(object):
    """Progress by bytes read and cancel polling."""

    def __init__(self, path, progress, cancel, base, share, phase, extra=0):
        try:
            self.total = float(max(1, os.path.getsize(path) + extra))
        except OSError:
            self.total = 1.0
        self.progress, self.cancel = progress, cancel
        self.base, self.share, self.phase = base, share, phase
        self.last = -1.0
        self.read = 0
        self.mark = _TICK_BYTES

    def tick(self):
        self.mark = self.read + _TICK_BYTES
        if self.cancel is not None and self.cancel():
            _refuse("cancelled")
        if self.progress is not None:
            fr = self.base + self.share * min(1.0, self.read / self.total)
            if fr - self.last >= 0.01:
                self.last = fr
                self.progress(fr, self.phase)


# ----------------------------------------------------------------------------- flag tracking
class _Tracker(object):
    """Failure records per element, streamed step by step (final run of dead steps)."""

    def __init__(self, n_elems, allow_k0, strict=False):
        self.prev = bytearray(n_elems)
        self.rec = {}                  # pos -> (k, centroid or None)
        self.dfs = set()               # dead from the first step, not recorded
        self.revived = 0
        self.allow_k0 = allow_k0
        self.strict = strict

    def update(self, j, dead, centroid_at):
        """dead: bytearray per element; centroid_at(p, step) -> centroid or None."""
        prev = self.prev
        if dead == prev:
            return
        for p in range(len(dead)):
            d = dead[p]
            if d == prev[p]:
                continue
            if d:
                if j == 0 and not self.allow_k0:
                    self.dfs.add(p)
                else:
                    self.rec[p] = (j, centroid_at(p, j - 1 if j > 0 else 0)
                                   if centroid_at is not None else None)
            else:
                if self.strict:
                    return p                # caller refuses (contract)
                if p in self.rec:
                    del self.rec[p]
                    self.revived += 1
                self.dfs.discard(p)
        self.prev = dead
        return None


# ----------------------------------------------------------------------------- pass 1
_OUT, _SOL, _RES = 0, 1, 2


def _pass1(path, o, ticker):
    st = _State()
    st.model_max = 0
    st.liml_version = None
    st.seen_liml = False
    st.n_solutions = 0
    st.target = None                 # ordinal of the target solution
    # solutions with <results> (1.0.2): only those count for the choice of the target; an
    # empty <solution .../> or one that closes before <results> is ignored
    st.n_full = 0                    # all of them
    st.n_full_match = 0              # those of o.configuration
    st.precision = None
    _new_mesh(st)
    st.steps = 0
    st.times = []                    # raw time attribute per step
    st.warnings = {}
    st.info = {}
    st.provider = None
    st.marker = None                 # marker text of the input (variable, else 1.0.0 attribute)
    st.marker_old = None             # limlfailed attribute (1.0.0)
    st.marker_gv = None              # text of the failed_hidden variable (1.0.1)
    st.model_confs = []              # <configuration name> of the model part (unescaped)
    st.sol_confs = []                # configuration attribute per <solution> (None: none)
    st.sol_bytes = 0                 # bytes of the target <solution> block
    st.carry = None                  # 1.0.3: per node position 1 = a support (_react_finish)
    st.react_pos = {}                # reaction nodeids name -> array: index -> node position
    st.react_cache = {}              # nodeids bytes -> that array
    st.react_max = {}                # reaction group -> array: node position -> largest |value|
    st.react_peak = {}               # reaction group -> largest |value| over nodes and steps
    st.noise_groups = []             # 1.0.4: reaction groups of round-off only (_react_noise)
    npos = None
    shape_ix = {}
    elset = -1
    where = _OUT
    skip = None
    skip_sol = None                  # skipping a <solution>: True when of o.configuration
    skip_res = False                 # ... and it has <results>
    blk = None
    var = kind = None
    want = rwant = False
    step = -1
    ids_names = {}                   # elementnodeids name -> slots (pos, off)
    slot_cache = {}
    displ_ix = {}                    # displ name -> array: node pos -> index (-1)
    displ_len = {}
    cur = {}
    prev = {}
    stepvals = {}
    needed = ()                      # element-node variables decoded per step
    tracker = None
    sec = None                       # secondary stress tracker (events_incomplete)
    covered = None
    prov = {}
    line = 0
    mixed = 0
    f = open(path, "rb")             # builtin open: str lines in IronPython; io.open is 5x slower
    try:                             # and bytes-typed there (research note 10, 1.5.1)
        for raw in f:
            line += 1
            ticker.read += len(raw)
            if not (line & (_TICK - 1)) or ticker.read >= ticker.mark:
                ticker.tick()
            if where != _OUT:
                st.sol_bytes += len(raw)
            if skip is not None:
                if skip_sol is not None and not skip_res and raw.find(b"<results") >= 0:
                    skip_res = True
                if raw.find(skip) >= 0:
                    skip = None
                    if skip_sol is not None and skip_res:
                        st.n_full += 1
                        st.n_full_match += 1 if skip_sol else 0
                    skip_sol = None
                continue
            try:
                if blk is not None:
                    if blk.feed(raw):
                        _block_done1(st, o, blk, ids_names, slot_cache, displ_ix, displ_len,
                                     cur, stepvals, npos, kind)
                        blk = None
                    continue
                s = raw.lstrip()
                if not s:
                    continue
                if where == _OUT:
                    if _is_solution_tag(s):
                        st.n_solutions += 1
                        conf = _unescape(_attr(s, b"configuration"))
                        st.sol_confs.append(None if conf is None else conf.decode("utf-8", "replace"))
                        # 1.0.2 (bridge KNOWN_BUGS 136): an empty <solution .../> is its own
                        # solution without results: never the target and nothing to skip, so it
                        # never swallows the next <solution>. The target is the first solution
                        # (of o.configuration) that opens while none has been chosen; one that
                        # closes before <results> is dropped again (see </solution in _SOL).
                        empty = _sol_empty(s)
                        if empty is None:
                            raise _Layout("solution tag not closed on its line")
                        match = o.configuration is None or (
                            conf is not None and conf.decode("utf-8", "replace") == o.configuration)
                        if empty:
                            pass
                        elif match and st.target is None:
                            st.target = st.n_solutions - 1
                            if o.keep and (st.model_confs or conf is not None):
                                _refuse("keep_original_configurations",
                                        info={"configurations": list(st.model_confs) or
                                              [conf.decode("utf-8", "replace")]})
                            st.sol_bytes = len(raw)
                            _new_mesh(st)       # a target dropped before <results> leaves none
                            shape_ix = {}
                            elset = -1
                            where = _SOL
                        else:               # counted after the loop when it has <results>
                            skip = b"</solution"
                            skip_sol = match
                            skip_res = False
                    elif s.startswith(b"<configuration ") and st.n_solutions == 0:
                        nm = _unescape(_attr(s, b"name"))
                        st.model_confs.append(u"" if nm is None else nm.decode("utf-8", "replace"))
                    elif s.startswith(b"<node ") and s.find(b' x="') >= 0:
                        n = int(_req(s, b"nid"))
                        if n > st.model_max:
                            st.model_max = n
                    elif s.startswith(b"<liml"):
                        st.seen_liml = True
                        v = _attr(s, b"version")
                        if v is not None:
                            st.liml_version = int(v)
                    continue
                if where == _SOL:
                    if s.startswith(b"<node ") and s.find(b' x="') >= 0:
                        if s.rstrip()[-2:] != b"/>":
                            raise _Layout("node line not self-closing")
                        st.nids.append(int(_req(s, b"nid")))
                        st.xs.append(float(_req(s, b"x")))
                        st.ys.append(float(_req(s, b"y")))
                        st.zs.append(float(_req(s, b"z")))
                    elif s.startswith(b"<elem ") and elset >= 0:
                        st.eids.append(int(_req(s, b"eid")))
                        sh = _attr(s, b"shape") or b""
                        if sh not in shape_ix:
                            shape_ix[sh] = len(st.shapes)
                            st.shapes.append(sh)
                        st.eshape.append(shape_ix[sh])
                        for t in _req(s, b"nodes").split():
                            st.conn.append(int(t))
                        st.eoff.append(len(st.conn))
                        st.eset.append(elset)
                    elif s.startswith(b"<elset "):
                        st.elset_names.append(_unescape(_attr(s, b"name")))
                        elset = len(st.elset_names) - 1
                        if s.rstrip()[-2:] == b"/>":
                            elset = -1
                    elif s.startswith(b"</elset"):
                        elset = -1
                    elif s.startswith(b"<results"):
                        st.n_full += 1
                        st.n_full_match += 1
                        st.precision = _attr(s, b"precision")
                        mk = _attr(s, MARKER_ATTR)
                        if mk is not None:
                            st.marker_old = mk.decode("ascii", "replace")
                        npos = _index(st.nids, "node")
                        st.npos = npos
                        st.epos = _index(st.eids, "element")
                        st.carry = bytearray(len(st.nids))      # 1.0.3: see _react_done1
                        st.react_pos = {}
                        st.react_cache = {}
                        st.react_max = {}
                        st.react_peak = {}
                        for p in range(len(st.eids)):
                            for n in st.conn[st.eoff[p]:st.eoff[p + 1]]:
                                if npos(n) < 0:
                                    _refuse("unknown_node", st.eids[p], n)
                        where = _RES
                    elif s.startswith(b"</solution"):
                        # closed before <results>: a solution without results, as an empty
                        # <solution ... /> (1.0.2): not the target (refused after the loop)
                        _sol_end(o, s)
                        st.target = None
                        where = _OUT
                    continue
                # where == _RES
                if s.startswith(b"<nodeids "):
                    name = _attr(s, b"name")
                    if name in DISPL or _is_react(name):
                        blk = _new_block(raw, b"nodeids", name, line)
                        kind = "nodeids"
                        if blk.done():
                            _block_done1(st, o, blk, ids_names, slot_cache, displ_ix, displ_len,
                                         cur, stepvals, npos, kind)
                            blk = None
                    elif s.find(b"</nodeids") < 0 and s.rstrip()[-2:] != b"/>":
                        skip = b"</nodeids"
                elif s.startswith(b"<elementnodeids "):
                    name = _attr(s, b"name")
                    if name in (FAILED_VAR, STATUS_VAR) or name in STRESS_VARS:
                        blk = _new_block(raw, b"elementnodeids", name, line)
                        kind = "elementnodeids"
                        if blk.done():
                            _block_done1(st, o, blk, ids_names, slot_cache, displ_ix, displ_len,
                                         cur, stepvals, npos, kind)
                            blk = None
                    elif s.find(b"</elementnodeids") < 0 and s.rstrip()[-2:] != b"/>":
                        skip = b"</elementnodeids"
                elif step < 0 and s.startswith(b"<globalvariable"):
                    mk = _gv_marker(s)
                    if mk is not None and st.marker_gv is None:
                        st.marker_gv = mk[0] or u"?"
                elif s.startswith(b"<timestep "):
                    step += 1
                    st.times.append(_attr(s, b"time"))
                    if step == 0:
                        _check_marker(st, o)
                        needed, tracker, sec, covered = _choose(st, o, ids_names, prov)
                    prev = cur
                    cur = {}
                    stepvals = {}
                elif s.startswith(b"</timestep"):
                    _eval_step(st, o, step, prov, ids_names, stepvals, needed, tracker, sec,
                               prev, cur, displ_ix, line)
                elif s.startswith(b"<nodevariable ") or s.startswith(b"<elementnodevariable "):
                    if step < 0:
                        _refuse("no_timesteps")
                    var = _attr(s, b"name")
                    rwant = False
                    if s.startswith(b"<nodevariable "):
                        kind = "node"
                        want = var in DISPL
                        # 1.0.3: reaction values tell which nodes are supports (_plan)
                        rwant = not want and _is_react(var)
                        end = b"</nodevariable"
                    else:
                        kind = "elem"
                        want = var in needed
                        end = b"</elementnodevariable"
                    if not want and not rwant and s.find(end) < 0:
                        skip = end
                elif (want or rwant) and _values_tag(s) is not None:
                    tag = _values_tag(s)
                    if want and (tag == b"valuesdouble") != (st.precision == b"double"):
                        mixed += 1
                    blk = _new_block(raw, tag, var, line)
                    if blk.done():
                        _block_done1(st, o, blk, ids_names, slot_cache, displ_ix, displ_len,
                                     cur, stepvals, npos, kind)
                        blk = None
                elif s.startswith(b"</nodevariable") or s.startswith(b"</elementnodevariable"):
                    want = rwant = False
                    var = None
                elif s.startswith(b"<mode "):
                    _refuse("modal_result")
                elif s.startswith(b"</solution"):
                    _sol_end(o, s)
                    where = _OUT
            except _Layout as e:
                _refuse("layout", line, e.args[0] if e.args else "")
            except (ValueError, OverflowError):     # OverflowError: id above int32
                _refuse("bad_number", line)
            except TypeError:           # attribute missing where one is required
                _refuse("layout", line, "missing attribute")
    finally:
        f.close()
    if not st.seen_liml:
        _refuse("not_liml")
    # keep_original also never next to or on an empty solution of a configuration (1.0.2)
    if o.keep and (st.n_solutions > 1 or any(c is not None for c in st.sol_confs)):
        _refuse("keep_original_configurations", info={"configurations": list(st.sol_confs)})
    if st.n_full_match > 1:     # two with <results> (of o.configuration); empty ones do not count
        _refuse("configurations", st.n_solutions, _conf_list(st.sol_confs),
                info={"configurations": list(st.sol_confs)})
    if st.target is None:
        if o.configuration is not None and st.n_solutions:
            _refuse("configuration_not_found", o.configuration)
        _refuse("no_solution")
    if step < 0:
        _refuse("no_timesteps")
    st.steps = step + 1
    if mixed:
        st.warnings["precision_mixed"] = mixed
    _react_finish(st)
    st.react_max = st.react_peak = st.react_cache = st.react_pos = None     # memory
    _finish1(st, o, prov, tracker, sec, covered)
    return st


def _new_mesh(st):
    """Empty mesh arrays of the target <solution> (again when a target closed before <results>)."""
    st.nids = array("i")
    st.xs = array("d")
    st.ys = array("d")
    st.zs = array("d")
    st.eids = array("i")
    st.eoff = array("i", [0])
    st.conn = array("i")
    st.eset = array("i")
    st.eshape = array("i")
    st.shapes = []
    st.elset_names = []              # unescaped bytes


def _block_done1(st, o, blk, ids_names, slot_cache, displ_ix, displ_len, cur, stepvals, npos, kind):
    data = blk.data()
    if blk.name not in DISPL and kind in ("nodeids", "node"):
        _react_done1(st, blk, data, npos, kind)
        return
    if blk.tag == b"nodeids":
        ids = _frombytes("i", data)
        ix = array("i", [-1]) * len(st.nids)
        last = None
        for i in range(len(ids)):
            n = ids[i]
            if last is not None and n <= last:
                raise _Layout("nodeids not ascending")
            last = n
            q = npos(n)
            if q >= 0:
                ix[q] = i
        displ_ix[blk.name] = ix
        displ_len[blk.name] = len(ids)
    elif blk.tag == b"elementnodeids":
        sl = slot_cache.get(data)
        if sl is None:
            ids = _frombytes("i", data)
            pos = array("i")
            off = array("i", [0])
            o_ = 0
            epos = st.epos
            for e in ids:
                p = epos(e)
                if p < 0:
                    _refuse("unknown_element", e, blk.name)
                pos.append(p)
                o_ += st.eoff[p + 1] - st.eoff[p]
                off.append(o_)
            sl = (pos, off)
            slot_cache[data] = sl
        ids_names[blk.name] = sl
    else:
        vals = _frombytes("d" if blk.tag == b"valuesdouble" else "f", data)
        if kind == "node":
            n = displ_len.get(blk.name)
            if n is not None and len(vals) != n:
                _refuse("value_count", blk.name, len(vals), n)
            cur[blk.name] = vals
        else:
            sl = ids_names.get(blk.name)
            if sl is not None and len(vals) != sl[1][-1]:
                _refuse("value_count", blk.name, len(vals), sl[1][-1])
            stepvals[blk.name] = vals


def _is_react(name):
    """A reaction-type node variable (REACTION_PREFIXES; one prefix at a time: IronPython's
    str.startswith rejects a tuple of bytes)."""
    return name is not None and any(name.startswith(p) for p in REACTION_PREFIXES)


def _react_group(name):
    """Reaction variables that share one scale: the name without a trailing x, y, z or mag
    (reactionforcex/y/z/mag -> reactionforce, reactionmomx -> reactionmom)."""
    for t in (b"mag", b"x", b"y", b"z"):
        if name.endswith(t):
            return name[:len(name) - len(t)]
    return name


def _react_done1(st, blk, data, npos, kind):
    """1.0.3: <nodeids> and values of a reaction variable: per node position the largest |value|
    over the steps and per group (_react_group) the largest over all its nodes and steps;
    _react_finish turns that into st.carry. NaN and inf mark a support at once. Being listed is
    not enough: Mecway lists every node, with 0.0 away from the supports."""
    if kind == "nodeids":
        rp = st.react_cache.get(data)       # the variables of a group share one list
        if rp is None:
            ids = _frombytes("i", data)
            rp = array("i", [-1]) * len(ids)
            last = None
            for i in range(len(ids)):
                n = ids[i]
                if last is not None and n <= last:
                    raise _Layout("nodeids not ascending")
                last = n
                rp[i] = npos(n)
            st.react_cache[data] = rp
        st.react_pos[blk.name] = rp
        return
    rp = st.react_pos.get(blk.name)
    if rp is None:                  # values without <nodeids>: pass 2 leaves them alone too
        return
    vals = _frombytes("d" if blk.tag == b"valuesdouble" else "f", data)
    if len(vals) != len(rp):
        _refuse("value_count", blk.name, len(vals), len(rp))
    if vals.count(0.0) == len(vals):
        return
    g = _react_group(blk.name)
    mx = st.react_max.get(g)
    if mx is None:
        mx = array("d", [0.0]) * len(st.nids)
        st.react_max[g] = mx
    peak = st.react_peak.get(g, 0.0)
    carry = st.carry
    for i in range(len(vals)):
        v = vals[i]
        if v != 0.0:
            q = rp[i]
            if q < 0:
                continue
            a = abs(v)
            if a != a or math.isinf(a):
                carry[q] = 1
                continue
            if a > mx[q]:
                mx[q] = a
                if a > peak:
                    peak = a
    st.react_peak[g] = peak


def _react_finish(st):
    """1.0.3: st.carry[q] = 1 for a support: a node whose |reaction| exceeds REACTION_REL_TOL
    times the largest of its group over all nodes and steps (exact 0.0 away from the supports
    in Mecway's own results; round-off of the bridge's REAC_NODA on free nodes was 1e-9..1e-5
    of the peak in Code-Aster 17.4 results, measured by the bridge). 1.0.4: a group of round-off
    only (_react_noise) marks no supports; NaN/inf still do (_react_done1)."""
    carry = st.carry
    if carry is None:
        return
    noise = _react_noise(st)
    st.noise_groups = [g.decode("ascii", "replace") for g in noise]
    for g, mx in st.react_max.items():
        peak = st.react_peak.get(g, 0.0)
        if peak > 0.0 and g not in noise:
            thr = REACTION_REL_TOL * peak
            for q in range(len(mx)):
                if mx[q] > thr:
                    carry[q] = 1


def _react_noise(st):
    """1.0.4 (KNOWN_BUGS 87): [REACT_FORCE] or [REACT_MOM] when that group holds only round-off
    next to the other (REACTION_NOISE_TOL, REACTION_NOISE_RAW), else []. Only when both groups
    have a peak > 0 (NaN/inf never count in a peak); neither or both: []. The L criterion only
    with a usable L (_elem_diagonal) and finite products; the raw one always. Products, not
    quotients: the checker computes the same expressions."""
    pf = st.react_peak.get(REACT_FORCE, 0.0)
    pm = st.react_peak.get(REACT_MOM, 0.0)
    if not (pf > 0.0 and pm > 0.0):
        return []
    f_noise = pf < REACTION_NOISE_RAW * pm
    m_noise = pm < REACTION_NOISE_RAW * pf
    ln = _elem_diagonal(st)
    if ln is not None:
        a = pf * ln
        c = REACTION_NOISE_TOL * pf * ln
        if not (math.isinf(a) or math.isinf(c)):
            f_noise = f_noise or a < REACTION_NOISE_TOL * pm
            m_noise = m_noise or pm < c
    if f_noise == m_noise:
        return []
    return [REACT_FORCE] if f_noise else [REACT_MOM]


def _elem_diagonal(st):
    """1.0.4: diagonal of the axis-aligned bounding box of the nodes used by an element of the
    target mesh (undeformed; loose nodes such as reference points do not count); None without
    elements, with a NaN coordinate, or when it is not finite and > 0."""
    npos = st.npos
    xs, ys, zs = st.xs, st.ys, st.zs
    seen = bytearray(len(st.nids))
    x0 = y0 = z0 = x1 = y1 = z1 = None
    for n in st.conn:
        q = npos(n)
        if q < 0 or seen[q]:
            continue
        seen[q] = 1
        x, y, z = xs[q], ys[q], zs[q]
        if x != x or y != y or z != z:     # a NaN coordinate: no length (order-free)
            return None
        if x0 is None:
            x0 = x1 = x
            y0 = y1 = y
            z0 = z1 = z
            continue
        if x < x0:
            x0 = x
        elif x > x1:
            x1 = x
        if y < y0:
            y0 = y
        elif y > y1:
            y1 = y
        if z < z0:
            z0 = z
        elif z > z1:
            z1 = z
    if x0 is None:
        return None
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    if not (ln > 0.0) or math.isinf(ln):
        return None
    return ln


def _sol_end(o, s):
    """keep_original copies the target solution up to its closing line: that line must hold
    only </solution> (e.g. not </solution></liml>)."""
    if o.keep and s.strip() != b"</solution>":
        raise _Layout("</solution> not alone on its line")


def _check_marker(st, o):
    """At the first <timestep>: refuse a processed input unless force (the variable wins over
    the attribute of 1.0.0). info has the same keys either way."""
    st.marker = st.marker_gv if st.marker_gv is not None else st.marker_old
    if st.marker is None or (o.force and not o.keep):    # keep_original: never on a processed
        return                                            # input (the original would be one)
    count = marker_count(st.marker_gv) if st.marker_gv is not None else None
    info = {"marker": st.marker, "hidden_count": count, "marker_version": st.marker_old}
    if st.marker_gv is not None:
        _refuse("already_processed", st.marker_gv, info=info)
    _refuse("already_processed", st.marker_old, info=info, text_key="already_processed_version")


def _choose(st, o, ids_names, prov):
    """Provider at the first <timestep>: (needed element-node vars, tracker, secondary, covered)."""
    n_e = len(st.eids)
    stress = tuple(v for v in STRESS_VARS if v in ids_names)
    sec = None
    if FAILED_VAR in ids_names:
        st.provider = "failed"
        needed = (FAILED_VAR,)
        tracker = _Tracker(n_e, True, strict=True)
    elif STATUS_VAR in ids_names:
        st.provider = "Element_status"
        needed = (STATUS_VAR,)
        tracker = _Tracker(n_e, STATUS_HIDE_DEAD_FROM_START)
    else:
        evs = None
        empty = False
        if o.events_path is not None and os.path.isfile(o.events_path):
            evs = _load_events(st, o.events_path)
            if not evs:         # no usable erosion event: no source (KNOWN_BUGS 76)
                evs = None
                empty = True
                st.warnings["events_empty"] = 1
                st.info["events_empty_path"] = o.events_path
        elif o.events_path is not None:
            st.warnings["events_missing"] = 1
            st.info["events_missing_path"] = o.events_path
        if evs is not None:
            st.provider = "events"
            prov["events"] = evs
            tracker = _Tracker(n_e, True)
            needed = ()
            if o.solver == "radioss" and stress:
                needed = stress
                sec = _Tracker(n_e, False)
        elif o.solver == "radioss" and stress:
            st.provider = "stress"
            needed = stress
            tracker = _Tracker(n_e, False)
        else:
            if o.events_path is None:
                extra_en, extra_nl = u", no events file", u", geen gebeurtenissenbestand"
            elif empty:
                extra_en = u", events file without failures"
                extra_nl = u", gebeurtenissenbestand zonder bezwijken"
            else:
                extra_en, extra_nl = u", events file missing", u", gebeurtenissenbestand ontbreekt"
            if o.solver != "radioss":
                extra_en += u", stress rule only for OpenRadioss"
                extra_nl += u", spanningsregel alleen voor OpenRadioss"
            _refuse("no_flag_source", extra_en, extra_nl)
    covered = bytearray(n_e)
    if st.provider == "events":
        for p in prov["events"]:
            covered[p] = 1
    else:
        for v in needed:
            for p in ids_names[v][0]:
                covered[p] = 1
    prov["stress"] = stress
    return needed, tracker, sec, covered


def _load_events(st, path):
    """{element pos: effective time} from <run>_events.json (mwradiosshub/events.py)."""
    try:
        with io.open(path, "r", encoding="utf-8-sig") as f:
            data = json.loads(f.read())
    except (IOError, OSError) as e:
        _refuse("events_invalid", path, e)
    except ValueError as e:
        _refuse("events_invalid", path, e)
    if not isinstance(data, dict) or data.get("schema") not in EVENTS_SCHEMAS:
        _refuse("events_invalid", path, u"schema {0}".format(
            data.get("schema") if isinstance(data, dict) else None))
    evs = data.get("events")
    if not isinstance(evs, list):
        _refuse("events_invalid", path, u"no event list")
    out = {}
    no_time = coarse = unknown = 0
    for ev in evs:
        if not isinstance(ev, dict) or ev.get("kind") != "erosion":
            continue
        try:
            eid = int(ev.get("element_id"))
        except (TypeError, ValueError):
            unknown += 1
            continue
        t = ev.get("time_upper")
        if t is None:
            t = ev.get("time")
            if t is not None and ev.get("time_source") == "row":
                coarse += 1
        if t is None:
            no_time += 1
            continue
        try:
            t = float(t)
        except (TypeError, ValueError):
            no_time += 1
            continue
        p = st.epos(eid)
        if p < 0:
            unknown += 1
            continue
        if p not in out or t < out[p]:
            out[p] = t
    for code, n in (("events_no_time", no_time), ("events_coarse_time", coarse),
                    ("events_unknown_elements", unknown)):
        if n:
            st.warnings[code] = n
    return out


def _step_time(st, j):
    raw = st.times[j]
    if raw is None:
        _refuse("time_unit", u"")
    try:
        return _parse_time(raw)
    except ValueError:
        _refuse("time_unit", raw)


def _eval_step(st, o, j, prov, ids_names, stepvals, needed, tracker, sec, prev, cur, displ_ix, line):
    n_e = len(st.eids)
    for v in needed:
        if v not in stepvals:
            _refuse("layout", line, u"variable {0} missing in step {1}".format(_u(v), j))
    dead = bytearray(n_e)
    pv = st.provider
    if pv == "failed":
        vals = stepvals[FAILED_VAR]
        pos, off = ids_names[FAILED_VAR]
        if vals.count(0.0) + vals.count(1.0) != len(vals):
            for i in range(len(pos)):
                for q in range(off[i], off[i + 1]):
                    if vals[q] != 0.0 and vals[q] != 1.0:
                        _refuse("failed_contract", st.eids[pos[i]], j, u"value not 0 or 1")
        for i in range(len(pos)):
            a, b = off[i], off[i + 1]
            t = sum(vals[a:b])
            if t:
                if t != b - a:
                    _refuse("failed_contract", st.eids[pos[i]], j, u"mixed values")
                dead[pos[i]] = 1
    elif pv == "Element_status":
        vals = stepvals[STATUS_VAR]
        pos, off = ids_names[STATUS_VAR]
        for i in range(len(pos)):
            if not any(vals[off[i]:off[i + 1]]):
                dead[pos[i]] = 1
        if len(vals) and (min(vals) < -1.0 or max(vals) > 1.0):
            st.warnings["status_out_of_range"] = st.warnings.get("status_out_of_range", 0) + \
                sum(1 for v in vals if v < -1.0 or v > 1.0)
    elif pv == "events":
        tj = _step_time(st, j)
        if j > 0 and tj < st._t_last:
            _refuse("time_order", j)
        st._t_last = tj
        for p, t in prov["events"].items():
            if tj >= t:
                dead[p] = 1
    if pv == "stress" or sec is not None:
        sd = _stress_dead(n_e, prov["stress"], ids_names, stepvals)
        if pv == "stress":
            dead = sd
        else:
            sec.update(j, sd, None)

    def centroid_at(p, k):
        return _centroid(st, p, cur if k == j else prev, displ_ix)
    bad = tracker.update(j, dead, centroid_at)
    if bad is not None:
        _refuse("failed_contract", st.eids[bad], j, u"not monotone")
    if j == 0 and pv == "Element_status" and tracker.dfs:
        st._t0 = _maybe_time(st, 0)


def _maybe_time(st, j):
    try:
        return _parse_time(st.times[j]) if st.times[j] is not None else None
    except ValueError:
        return None


def _stress_dead(n_e, names, ids_names, stepvals):
    alive = bytearray(n_e)
    cov = bytearray(n_e)
    for v in names:
        vals = stepvals[v]
        pos, off = ids_names[v]
        for i in range(len(pos)):
            p = pos[i]
            cov[p] = 1
            if not alive[p] and any(vals[off[i]:off[i + 1]]):
                alive[p] = 1
    dead = bytearray(n_e)
    for p in range(n_e):
        if cov[p] and not alive[p]:
            dead[p] = 1
    return dead


def _centroid(st, p, displ, displ_ix):
    """Mean of X + u over the distinct nodes of element p, or None when not finite."""
    try:
        ux, uy, uz = displ[DISPL[0]], displ[DISPL[1]], displ[DISPL[2]]
        ix, iy, iz = displ_ix[DISPL[0]], displ_ix[DISPL[1]], displ_ix[DISPL[2]]
    except KeyError:
        _refuse("no_displacement", st.conn[st.eoff[p]], st.eids[p])
    seen = set()
    sx = sy = sz = 0.0
    m = 0
    for n in st.conn[st.eoff[p]:st.eoff[p + 1]]:
        if n in seen:
            continue
        seen.add(n)
        q = st.npos(n)
        a, b, c = ix[q], iy[q], iz[q]
        if a < 0 or b < 0 or c < 0:
            _refuse("no_displacement", n, st.eids[p])
        sx += st.xs[q] + ux[a]
        sy += st.ys[q] + uy[b]
        sz += st.zs[q] + uz[c]
        m += 1
    cen = (sx / m, sy / m, sz / m)
    if not (_finite(cen[0]) and _finite(cen[1]) and _finite(cen[2])):
        return None
    return cen


def _finish1(st, o, prov, tracker, sec, covered):
    failed = {}
    bad = 0
    for p, (k, c) in tracker.rec.items():
        if c is None:
            bad += 1
        else:
            failed[p] = (k, c)
    w = st.warnings
    if bad:
        w["bad_displacement"] = bad
    if tracker.revived:
        w["revived"] = tracker.revived
    n_cov = sum(1 for x in covered if x) if covered is not None else 0
    if st.provider in ("failed", "Element_status") and len(st.eids) - n_cov:
        w["not_covered"] = len(st.eids) - n_cov
    if st.provider == "stress":
        if len(st.eids) - n_cov:
            w["not_covered"] = len(st.eids) - n_cov
        if tracker.dfs:
            st.info["never_loaded"] = len(tracker.dfs)
    if st.provider == "Element_status" and tracker.dfs:
        t0 = getattr(st, "_t0", None)
        if t0 is not None and t0 > 0.0:
            w["dead_before_first_step"] = len(tracker.dfs)
        else:
            w["dead_from_start"] = len(tracker.dfs)
    if st.provider == "events":
        n_after = sum(1 for p in prov["events"] if p not in tracker.rec)
        if n_after:
            w["events_after_last_step"] = n_after
        if sec is not None:
            miss = sum(1 for p in sec.rec if p not in tracker.rec)
            if miss:
                w["events_incomplete"] = miss
    if st.precision == b"single" and st.liml_version is not None and st.liml_version < 31:
        w["version_old"] = st.liml_version
    st.failed = failed


# ----------------------------------------------------------------------------- plan
class _PlanTick(object):
    """Progress (phase "scan") and cancel polling inside _plan (KNOWN_BUGS 72): call with the
    fraction of the plan done."""

    def __init__(self, progress, cancel, base, share):
        self.progress, self.cancel = progress, cancel
        self.base, self.share = base, share
        self.last = -1.0

    def __call__(self, fr):
        if self.cancel is not None and self.cancel():
            _refuse("cancelled")
        if self.progress is not None:
            v = self.base + self.share * min(1.0, max(0.0, fr))
            if v - self.last >= 0.01 or self.last < 0.0:
                self.last = v
                self.progress(v, "scan")


def _no_tick(fr):
    return None


def _plan(st, o, tick=None):
    """Copies and the rest of what pass 2 needs (copy rule of collapse_eroded.py). tick(fr):
    progress and cancel, at the start of every stage and every _PLAN_TICK iterations."""
    tick = tick or _no_tick
    pl = _State()
    failed = st.failed if o.mode != "identity" else {}
    conn, eoff = st.conn, st.eoff
    n_e = len(st.eids)
    n_f = max(1, len(failed))
    m = _PLAN_TICK - 1
    tick(0.0)
    fnodes = set()
    for i, p in enumerate(failed):
        if not (i & m):
            tick(0.05 * i / n_f)
        for n in conn[eoff[p]:eoff[p + 1]]:
            fnodes.add(n)
    tick(0.05)
    owners = {}
    for p in range(n_e):
        if not (p & m):
            tick(0.05 + 0.3 * p / max(1, n_e))
        for n in conn[eoff[p]:eoff[p + 1]]:
            if n in fnodes:
                lst = owners.get(n)
                if lst is None:
                    owners[n] = [p]
                elif lst[-1] != p:
                    lst.append(p)
    top = max(st.model_max, max(st.nids) if len(st.nids) else 0)
    next_id = top + 1
    new_conn = {}
    copy_of = {}
    copy_elem = {}
    kept = {}
    freed = set()
    carry = st.carry
    tick(0.35)
    for i, p in enumerate(sorted(failed)):
        if not (i & m):
            tick(0.35 + 0.2 * i / n_f)
        mine = {}
        out = []
        for n in conn[eoff[p]:eoff[p + 1]]:
            if n in mine:
                out.append(mine[n])
                continue
            own = owners[n]
            keeper = None
            if all(q in failed for q in own):
                if carry is not None and carry[st.npos(n)]:
                    # 1.0.3: a support node (a reaction above round-off) is never
                    # collapsed: every owner gets a copy, the original keeps its place, its
                    # real displacement and all values, used by no element ("" group)
                    freed.add(n)
                else:
                    keeper = own[0]
                    for q in own[1:]:
                        if failed[q][0] > failed[keeper][0]:
                            keeper = q
            if keeper == p:
                kept[n] = p
                mine[n] = n
            else:
                c = next_id
                next_id += 1
                copy_of[c] = n
                copy_elem[c] = p
                mine[n] = c
            out.append(mine[n])
        if out != list(conn[eoff[p]:eoff[p + 1]]):
            new_conn[st.eids[p]] = out
    pl.new_conn = new_conn
    pl.copy_of = copy_of
    pl.copy_elem = copy_elem
    pl.copies = sorted(copy_of)
    pl.kept = kept
    pl.freed = freed
    pl.need = set(copy_of.values()) | set(kept)
    pl.affected = sorted(set(st.eset[p] for p in failed))
    # displacement offsets of the collapse per collapsed node: (k, (dx, dy, dz, mag))
    coll = {}
    for c, n in copy_of.items():
        coll[c] = _offset(st, failed[copy_elem[c]], n)
    for n, p in kept.items():
        coll[n] = _offset(st, failed[p], n)
    pl.coll = coll
    # membership per affected elset over node positions (copies: their element's elset)
    n_nodes = len(st.nids)
    members = {}
    for s in pl.affected:
        members[s] = bytearray(n_nodes)
    copy_set = {}
    aff = set(pl.affected)
    tick(0.55)
    for p in range(n_e):
        if not (p & m):
            tick(0.55 + 0.2 * p / max(1, n_e))
        s = st.eset[p]
        if s not in aff:
            continue
        nc = new_conn.get(st.eids[p])
        mb = members[s]
        for n in (nc if nc is not None else conn[eoff[p]:eoff[p + 1]]):
            if n in copy_of:
                copy_set[n] = s
            else:
                mb[st.npos(n)] = 1
    pl.members = members
    pl.copy_elset = copy_set
    # 1.0.3: nodes in no element after the change (maxandmin group name="", first, as the
    # mecway skill liml-format 9 describes): the free nodes of the input plus the freed
    # supports. Only with freed supports (otherwise the "" group cannot change) and when no
    # elset is called "" itself.
    pl.free = None
    pl.free_blocked = bool(freed) and b"" in st.elset_names    # counted as mm_group_mismatch
    if freed and not pl.free_blocked:
        used = bytearray(n_nodes)
        for p in range(n_e):
            if not (p & m):
                tick(0.75)
            for n in conn[eoff[p]:eoff[p + 1]]:
                used[st.npos(n)] = 1
        free = bytearray(n_nodes)
        for q in range(n_nodes):
            if not used[q]:
                free[q] = 1
        for n in freed:
            free[st.npos(n)] = 1
        pl.free = free
    # tightened structural fingerprint (review finding 4): a node of a failed element above
    # the model's highest id, used by that element only, on the spot of a model node
    cand = {}
    tick(0.75)
    for i, p in enumerate(failed):
        if not (i & m):
            tick(0.75 + 0.1 * i / n_f)
        for n in set(conn[eoff[p]:eoff[p + 1]]):
            if n > st.model_max and owners.get(n) == [p]:
                q = st.npos(n)
                cand[(st.xs[q], st.ys[q], st.zs[q])] = cand.get((st.xs[q], st.ys[q], st.zs[q]), 0) + 1
    hits = 0
    if cand:
        tick(0.85)
        for q in range(n_nodes):
            if not (q & m):
                tick(0.85 + 0.15 * q / max(1, n_nodes))
            if st.nids[q] <= st.model_max:
                key = (st.xs[q], st.ys[q], st.zs[q])
                if key in cand:
                    hits += cand.pop(key)
    if hits:
        st.warnings["looks_processed"] = hits
    tick(1.0)
    return pl


def _offset(st, rec, n):
    k, c = rec
    q = st.npos(n)
    dx = c[0] - st.xs[q]
    dy = c[1] - st.ys[q]
    dz = c[2] - st.zs[q]
    # x * x, not x ** 2: IronPython's ** (Math.Pow) can differ by one ulp (note 10, 1.5.2)
    return k, (dx, dy, dz, math.sqrt(dx * dx + dy * dy + dz * dz))


# ----------------------------------------------------------------------------- pass 2
def _pass2(st, pl, o, in_path, out_path, ticker):
    tmp = out_path + ".tmp"
    h = [None, None]
    ok = False
    try:
        try:
            h[0] = open(in_path, "rb")
            h[1] = open(tmp, "wb")
            _write(st, pl, o, h[0], h[1], ticker)
            h[0].close()
            h[0] = None
            h[1].close()
            h[1] = None
            _replace(tmp, out_path)
            ok = True
        except MemoryError:
            _refuse("too_large")
        except (IOError, OSError) as e:
            _refuse("write_error", out_path, e)
    finally:
        if not ok:              # also on cancel, refusal or a bug: no .tmp left behind
            _cleanup(h[0], h[1], tmp)


def _cleanup(f, g, tmp):
    for h in (f, g):
        if h is not None:
            try:
                h.close()
            except Exception:
                pass
    _remove(tmp)


def _write(st, pl, o, f, g, ticker):
    w = g.write
    mode = o.mode
    collapse = mode == "collapse"
    where = _OUT
    sol = -1
    skip_copy = None           # end marker while copying a block verbatim
    blk = None
    held = None                # nodevariable header and maxandmin lines
    var = None
    step = -1
    line = 0
    node_raw = {}
    in_nodes = False
    copies_done = not pl.copies
    drop_markers = False       # True after our marker: drop failed_hidden lines of the input
    confs_done = False         # keep_original: <configuration> lines written
    info_of = {}               # nodeids name -> info
    cache = {}
    st.mm_rewritten = 0
    st.mm_mismatch = 0
    for raw in f:
        line += 1
        ticker.read += len(raw)
        if not (line & (_TICK - 1)) or ticker.read >= ticker.mark:
            ticker.tick()
        if skip_copy is not None:
            w(raw)
            if raw.find(skip_copy) >= 0:
                skip_copy = None
            continue
        try:
            if blk is not None:
                if blk.feed(raw):
                    _block_done2(st, pl, o, blk, info_of, cache, held, step, g)
                    blk = None
                    held = None
                continue
            if held is not None:
                s = raw.lstrip()
                tag = _values_tag(s)
                if tag is not None:
                    blk = _new_block(raw, tag, var, line)
                    if blk.done():
                        _block_done2(st, pl, o, blk, info_of, cache, held, step, g)
                        blk = None
                        held = None
                elif s.startswith(b"</nodevariable"):
                    g.writelines(held)
                    w(raw)
                    held = None
                else:
                    if s.count(b"<component ") > 1:
                        raise _Layout("two components on one line")
                    held.append(raw)
                continue
            if where == _OUT:
                s = raw.lstrip()
                if _is_solution_tag(s):
                    sol += 1
                    if sol == st.target:
                        where = _SOL
                        if o.keep:
                            _copy_original(o, line, _with_conf(raw, o.names[0]), w, ticker)
                            raw = _with_conf(raw, o.names[1])
                    elif not _sol_empty(s):         # an empty <solution .../>: nothing to skip
                        skip_copy = b"</solution"
                w(raw)
                if o.keep and not confs_done and s.startswith(b"<liml"):
                    _write_confs(o, raw, w)
                    confs_done = True
                continue
            s = raw.lstrip()
            if where == _SOL:
                if s.startswith(b"<node ") and s.find(b' x="') >= 0:
                    in_nodes = True
                    n = int(_req(s, b"nid"))
                    if n in pl.need:
                        node_raw[n] = raw
                    w(raw)
                    continue
                if in_nodes:
                    in_nodes = False
                    if not copies_done and len(node_raw) == len(pl.need):
                        _write_copies(pl, node_raw, w)
                        copies_done = True
                if s.startswith(b"<elem "):
                    nc = pl.new_conn.get(int(_req(s, b"eid")))
                    if nc is not None:
                        old = _attr(raw, b"nodes")
                        raw = raw.replace(b' nodes="' + old + b'"',
                                          b' nodes="' + b" ".join(str(x).encode("ascii") for x in nc)
                                          + b'"', 1)
                    w(raw)
                elif s.startswith(b"<results"):
                    if not copies_done:
                        _write_copies(pl, node_raw, w)
                        copies_done = True
                    where = _RES
                    if collapse and WRITE_MARKER:
                        _write_marker(st, raw, w)
                        drop_markers = True
                    else:                   # copies / identity: any marker stays verbatim
                        w(raw)
                else:
                    w(raw)
                continue
            # _RES
            if s.startswith(b"<nodeids "):
                blk = _new_block(raw, b"nodeids", _attr(s, b"name"), line)
                if blk.done():
                    _block_done2(st, pl, o, blk, info_of, cache, held, step, g)
                    blk = None
            elif s.startswith(b"<nodevariable "):
                var = _attr(s, b"name")
                held = [raw]
                if s.find(b"</nodevariable") >= 0:
                    raise _Layout("nodevariable on one line")
            elif s.startswith(b"<elementnodevariable "):
                w(raw)
                if s.find(b"</elementnodevariable") < 0:
                    skip_copy = b"</elementnodevariable"
            elif s.startswith(b"<elementnodeids "):
                w(raw)
                if s.find(b"</elementnodeids") < 0 and s.rstrip()[-2:] != b"/>":
                    skip_copy = b"</elementnodeids"
            elif s.startswith(b"<timestep "):
                step += 1
                w(raw)
            elif s.startswith(b"</solution"):
                where = _OUT
                w(raw)
            elif drop_markers and step < 0 and _gv_marker(s) is not None:
                # force on a processed file: the old marker goes, ours is the only one
                if not _gv_marker(s)[1]:
                    raise _Layout("marker split over lines")
            else:
                w(raw)
        except _Layout as e:
            _refuse("layout", line, e.args[0] if e.args else "")
        except (ValueError, OverflowError):
            _refuse("bad_number", line)
        except TypeError:               # attribute missing (e.g. a component without max/min)
            _refuse("layout", line, "missing attribute")
    if blk is not None or held is not None:
        _refuse("layout", line, "file ends inside a block")


def _write_confs(o, raw, w):
    """keep_original: the two <configuration> definitions right after the <liml ...> line."""
    eol = _eol(raw)
    body = raw[:len(raw) - len(eol)].rstrip()
    if body.find(b">") != len(body) - 1 or body[-2:] == b"/>":
        raise _Layout("liml tag not alone on its line")
    ind = raw[:len(raw) - len(raw.lstrip())] + b"  "
    for n in o.names:
        w(ind + b'<configuration name="' + _xml_attr(n) + b'" />' + (eol or b"\n"))


def _copy_original(o, line, first, w, ticker):
    """keep_original: the target <solution> block verbatim from a second handle (its first line
    `first` with the configuration of the original), up to and including </solution>."""
    try:
        h = open(o.in_path, "rb")
    except (IOError, OSError) as e:
        _refuse("read_error", o.in_path, e)
    try:
        k = 0
        for raw in h:
            k += 1
            if k < line:
                if not (k & (_TICK - 1)):
                    ticker.tick()           # cancel while skipping the model part
                continue
            ticker.read += len(raw)
            if not (k & (_TICK - 1)) or ticker.read >= ticker.mark:
                ticker.tick()
            if k == line:
                w(first)
                continue
            w(raw)
            if raw.find(b"</solution") >= 0:
                return
    finally:
        h.close()
    raise _Layout("file ends inside the solution")


def _write_marker(st, raw, w):
    """The <results ...> line without the 1.0.0 attribute, then the marker line as its first
    child: indent of <results> + 2 spaces (Mecway: 4 and 6), the line end of <results>."""
    old = _attr(raw, MARKER_ATTR)
    if old is not None:
        raw = raw.replace(b" " + MARKER_ATTR + b'="' + old + b'"', b"", 1)
    eol = _eol(raw)
    body = raw[:len(raw) - len(eol)].rstrip()
    i = body.find(b"<results")
    if body.find(b">", i) != len(body) - 1 or body[-2:] == b"/>":
        raise _Layout("results tag not alone on its line")
    ind = raw[:len(raw) - len(raw.lstrip())]
    w(raw)
    w(ind + b"  <globalvariable name=\"" + MARKER_VAR + b"\">" +
      str(len(st.failed)).encode("ascii") + b"</globalvariable>" + (eol or b"\n"))


def _write_copies(pl, node_raw, w):
    for c in pl.copies:
        r = node_raw[pl.copy_of[c]]
        old = _attr(r, b"nid")
        w(r.replace(b' nid="' + old + b'"', b' nid="' + str(c).encode("ascii") + b'"', 1))


def _block_done2(st, pl, o, blk, info_of, cache, held, step, g):
    data = blk.data()
    if blk.tag == b"nodeids":
        # one prefix at a time: IronPython's str.startswith rejects a tuple of bytes
        react = any(blk.name.startswith(p) for p in REACTION_PREFIXES)
        key = (data, react)
        info = cache.get(key)
        if info is None:
            info = _nodeids_info(st, pl, o, _frombytes("i", data), react)
            cache[key] = info
        info_of[blk.name] = info
        g.writelines(blk.emit(info[0]))
        return
    info = info_of.get(blk.name)
    tc = "d" if blk.tag == b"valuesdouble" else "f"
    vals = _frombytes(tc, data)
    if info is None:                # values without <nodeids>: leave them alone
        g.writelines(held)
        g.writelines(blk.emit(data))
        return
    ext_bytes, copy_slots, kept_slots, mm_pos, n0, lost = info
    if len(vals) != n0:
        _refuse("value_count", blk.name, len(vals), n0)
    mm_new = None
    if o.mode != "identity":
        if copy_slots:
            vals.extend(array(tc, [vals[sl[1]] for sl in copy_slots]))
        if o.mode == "collapse":
            name = blk.name
            comp = None
            if name in DISPL:
                comp = DISPL.index(name)
            elif name == DISPLMAG:
                comp = 3
            if comp is not None or o.others == "zero":
                for sl in copy_slots:
                    if step >= sl[2]:
                        vals[sl[0]] = sl[3][comp] if comp is not None else 0.0
                for sl in kept_slots:
                    if step >= sl[2]:
                        vals[sl[0]] = sl[3][comp] if comp is not None else 0.0
        mm_new = {}
        if lost:
            st.mm_mismatch += 1
        for s, idx in mm_pos.items():
            mx = mn = None
            for i in idx:
                v = vals[i]
                if v != v:
                    continue
                if mx is None:
                    mx = mn = v
                elif v > mx:
                    mx = v
                elif v < mn:
                    mn = v
            mm_new[st.elset_names[s] if s >= 0 else b""] = (mx, mn)
    out = []
    seen = set()
    for r in held:
        t = r.lstrip()
        if mm_new is not None and t.startswith(b"<component "):
            nm = _unescape(_attr(t, b"name"))
            if nm in mm_new:
                seen.add(nm)
                mx, mn = mm_new[nm]
                if mx is None:
                    st.mm_mismatch += 1
                else:
                    omax = _attr(r, b"max")
                    omin = _attr(r, b"min")
                    if omax is None or omin is None:    # IronPython: float(None) is a SystemError
                        raise _Layout("component without max/min")
                    if not (_close(mx, float(omax)) and _close(mn, float(omin))):
                        r = r.replace(b' max="' + omax + b'"', b' max="' + _fmt15(mx) + b'"', 1)
                        r = r.replace(b' min="' + omin + b'"', b' min="' + _fmt15(mn) + b'"', 1)
                        st.mm_rewritten += 1
        out.append(r)
    if mm_new is not None:
        for nm, (mx, mn) in mm_new.items():
            if nm not in seen and mx is not None:
                if not (nm == b"" and -1 in mm_pos and _add_free_group(out, mx, mn)):
                    st.mm_mismatch += 1
    g.writelines(out)
    g.writelines(blk.emit(_tobytes(vals)))


def _add_free_group(out, mx, mn):
    """1.0.3: insert <component name="" .../> as the first line inside <maxandmin> (a freed
    support made a node free where the input had none); indent and line end of the first
    component line, else of <maxandmin> + 2 spaces. False when there is no <maxandmin> line
    of its own (the caller counts mm_group_mismatch)."""
    for i in range(len(out)):
        if out[i].strip() == b"<maxandmin>":
            nxt = out[i + 1] if i + 1 < len(out) else b""
            comp = nxt.lstrip().startswith(b"<component ")
            ref = nxt if comp else out[i]
            ind = ref[:len(ref) - len(ref.lstrip())] + (b"" if comp else b"  ")
            eol = _eol(ref) or _eol(out[i]) or b"\n"
            out.insert(i + 1, ind + b'<component name="" max="' + _fmt15(mx) + b'" min="' +
                       _fmt15(mn) + b'" />' + eol)
            return True
    return False


def _nodeids_info(st, pl, o, ids, react):
    """(extended ids bytes, copy slots, kept slots, mm positions per affected elset (-1: the ""
    group, 1.0.3), n0, lost: the "" group is blocked by an elset called "").
    A slot is (index in the extended list, source index, failure step, offsets)."""
    n0 = len(ids)
    where = {}
    need = pl.need
    mm_pos = {}
    items = []
    for s in pl.affected:
        mm_pos[s] = array("i")
        items.append((pl.members[s], mm_pos[s]))
    if pl.free is not None:         # 1.0.3: the "" group (key -1), kept below only when a
        mm_pos[-1] = array("i")     # freed support is in this list
        items.append((pl.free, mm_pos[-1]))
    npos = st.npos
    last = None
    for i in range(n0):
        n = ids[i]
        if last is not None and n <= last:
            raise _Layout("nodeids not ascending")
        last = n
        q = npos(n)
        if q >= 0:
            for mb, arr in items:
                if mb[q]:
                    arr.append(i)
        if n in need:
            where[n] = i
    if -1 in mm_pos and not any(n in where for n in pl.freed):
        del mm_pos[-1]
    # an elset called "" blocks the "" group: _block_done2 counts mm_group_mismatch per block
    lost = pl.free_blocked and any(n in where for n in pl.freed)
    ext = array("i", ids)
    copy_slots = []
    kept_slots = []
    # Reaction-type variables are extensive: no copies, and their values are never changed
    # (not even on kept originals), so sums over nodes stay right (diff review finding 1).
    if o.mode != "identity" and not react:
        for c in pl.copies:
            src = where.get(pl.copy_of[c])
            if src is None:
                continue
            ext.append(c)
            ei = len(ext) - 1
            k, d = pl.coll[c]
            copy_slots.append((ei, src, k, d))
            s = pl.copy_elset.get(c)
            if s in mm_pos:
                mm_pos[s].append(ei)
        for n in pl.kept:
            i = where.get(n)
            if i is not None:
                k, d = pl.coll[n]
                kept_slots.append((i, i, k, d))
    return _tobytes(ext), copy_slots, kept_slots, mm_pos, n0, lost


# ----------------------------------------------------------------------------- API
class _Opts(object):
    pass


def _opts(events_path, solver, mode, others, force, configuration, keep=False, names=KEEP_NAMES):
    if mode not in MODES:
        _refuse("bad_argument", u"mode={0}".format(mode))
    if others not in OTHERS:
        _refuse("bad_argument", u"others={0}".format(others))
    if solver not in SOLVERS:
        _refuse("bad_argument", u"solver={0}".format(solver))
    if sys.byteorder != "little" or array("i").itemsize != 4 or array("f").itemsize != 4:
        _refuse("platform")
    o = _Opts()
    o.events_path = events_path
    o.solver = solver
    o.mode = mode
    o.others = others
    o.force = force
    o.configuration = None if configuration is None else _u(configuration)
    o.keep = bool(keep)
    o.names = None
    o.in_path = None
    if o.keep:
        if mode != "collapse" or o.configuration is not None:
            _refuse("bad_argument", u"keep_original with mode={0}, configuration={1}".format(
                mode, o.configuration))
        try:
            nm = () if isinstance(names, (type(b""), type(u""))) else tuple(_u(x) for x in names)
        except TypeError:
            nm = ()
        if len(nm) != 2 or nm[0] == nm[1] or \
                any((not x) or any(c.isspace() or ord(c) < 32 for c in x) for x in nm):
            _refuse("bad_argument", u"names={0} (two different names without spaces)".format(
                u", ".join(nm) if nm else names))
        o.names = nm
    return o


def _run1(in_path, o, progress, cancel, share):
    if not os.path.isfile(in_path):
        _refuse("not_found", in_path)
    ticker = _Ticker(in_path, progress, cancel, 0.0, share, "scan")
    try:
        st = _pass1(in_path, o, ticker)
    except MemoryError:
        _refuse("too_large")
    except (IOError, OSError) as e:
        _refuse("read_error", in_path, e)
    return st, ticker


def _report(st, pl, o, t):
    rep = {"version": VERSION, "mode": o.mode, "others": o.others, "written": False,
           "out_path": None, "provider": st.provider,
           "precision": st.precision.decode("ascii", "replace") if st.precision else None,
           "liml_version": st.liml_version, "steps": st.steps, "elements": len(st.eids),
           "nodes": len(st.nids), "failed_count": len(st.failed),
           "failed": dict((st.eids[p], k) for p, (k, c) in st.failed.items()),
           "configuration": o.configuration, "marker": st.marker,
           "keep_original": o.keep, "configurations": list(o.names) if o.keep else None,
           "seconds": t, "info": dict(st.info)}
    by_shape = {}
    for p in st.failed:
        sh = st.shapes[st.eshape[p]].decode("ascii", "replace")
        by_shape[sh] = by_shape.get(sh, 0) + 1
    rep["failed_by_shape"] = by_shape
    rep["copies"] = len(pl.copy_of) if pl is not None else 0
    rep["kept_originals"] = len(pl.kept) if pl is not None else 0
    rep["kept_supports"] = len(pl.freed) if pl is not None else 0      # 1.0.3
    rep["noise_reaction_groups"] = list(st.noise_groups)                 # 1.0.4
    rep["affected_elsets"] = [st.elset_names[s].decode("utf-8", "replace")
                              for s in (pl.affected if pl is not None else [])]
    rep["warnings"] = dict(st.warnings)
    return rep


def _messages(rep):
    msgs = []
    for code in WARNING_CODES:
        n = rep["warnings"].get(code)
        if n:
            arg = n
            if code in ("events_missing", "events_empty"):
                arg = rep["info"].get(code + "_path", n)
            msgs.append(message(code, arg))
    return msgs


def scan(in_path, events_path=None, solver=None, progress=None, cancel=None, force=False,
         configuration=None):
    """Dry run (pass 1 and the copy plan): the report of process() with written=False."""
    try:
        return _scan(in_path, events_path, solver, progress, cancel, force, configuration)
    except MemoryError:
        _refuse("too_large")


def _scan(in_path, events_path, solver, progress, cancel, force, configuration):
    t0 = time.time()
    o = _opts(events_path, solver, "collapse", "follow", force, configuration)
    st, ticker = _run1(in_path, o, progress, cancel, _SCAN_PASS1_SHARE)
    t1 = time.time()
    pl = _plan(st, o, _PlanTick(progress, cancel, _SCAN_PASS1_SHARE, 1.0 - _SCAN_PASS1_SHARE))
    rep = _report(st, pl, o, {"pass1": t1 - t0, "plan": time.time() - t1, "pass2": 0.0})
    msgs = _messages(rep)
    if st.failed:
        rep["code"] = "scanned"
        msgs.insert(0, message("scanned", len(st.failed), st.provider))
    else:
        rep["code"] = "nothing_failed"
        msgs.insert(0, message("nothing_failed", st.provider))
    rep["messages"] = msgs
    if progress is not None:
        progress(1.0, "scan")
    return rep


def process(in_path, out_path, events_path=None, solver=None, progress=None, cancel=None,
            mode="collapse", force=False, others="follow", configuration=None,
            keep_original=False, names=KEEP_NAMES):
    """Write out_path with the failed elements hidden; returns the report (plan §1.2).

    mode   "collapse" (product), "copies" (copies only, no collapse, no marker; diagnostic),
           "identity" (decode and re-encode, change nothing; tests).
    others "follow" (default, OPEN_VRAGEN 71): every non-displacement node variable of a
           collapsed node keeps following the original node, so the legend ranges stay as
           they were except for the displacement; "zero": those variables are 0 from the
           failure step on (pulls the legend range of the affected elsets towards 0).
           Displacements always collapse; reaction-type variables (REACTION_PREFIXES) never
           get copies and are never changed. 1.0.3: a node whose owners all fail and that
           is a support (REACTION_REL_TOL) is never collapsed, also in mode "copies" (report key
           kept_supports; see the module docstring). 1.0.4: a reaction group of round-off only
           marks no supports (report key noise_reaction_groups, also in scan()).
    force  skip the processed-marker check (tests); the output then carries one new marker
           (an input marker and the 1.0.0 attribute are dropped) in mode collapse.
    configuration  name of the configuration whose <solution> to process; None = the file
           must hold exactly one <solution> with <results>. Other solutions are copied
           verbatim. 1.0.2: an empty solution (<solution ... />, <solution ...></solution>, or
           any <solution> that closes before <results>) is never the target and does not
           count: none left gives configuration_not_found (no_solution with configuration
           None); two with <results> (of that configuration) give configurations. A <solution
           start tag that does not close on its line gives layout.
    keep_original  True: one output file with two configurations, names[0] (the original
           <solution>, verbatim) and names[1] (the processed one, with the marker), defined
           right after <liml ...>; about twice the size. Only mode collapse, configuration
           None and an input without configurations and with one <solution>, empty ones
           included (else keep_original_configurations: the model part would need
           <suppressed configuration> copies, not tested in Mecway).
    names  the two configuration names: different, no white space (Mecway refuses a name
           with a space), XML-escaped on writing.
    Raises LimlFailedError on refusal; "nothing failed" returns written=False.
    """
    try:
        return _process(in_path, out_path, events_path, solver, progress, cancel, mode, force,
                        others, configuration, keep_original, names)
    except MemoryError:         # anywhere (pass 1, plan, pass 2); pass 2 removes its .tmp
        _refuse("too_large")


def _process(in_path, out_path, events_path, solver, progress, cancel, mode, force, others,
             configuration, keep_original, names):
    t0 = time.time()
    o = _opts(events_path, solver, mode, others, force, configuration, keep_original, names)
    o.in_path = in_path
    if _same(in_path, out_path):
        _refuse("same_path")
    st, ticker = _run1(in_path, o, progress, cancel, _PASS1_SHARE)
    t1 = time.time()
    pl = _plan(st, o, _PlanTick(progress, cancel, _PASS1_SHARE, _PLAN_SHARE))
    t2 = time.time()
    if not st.failed and mode != "identity":
        rep = _report(st, pl, o, {"pass1": t1 - t0, "plan": t2 - t1, "pass2": 0.0})
        rep["code"] = "nothing_failed"
        rep["messages"] = [message("nothing_failed", st.provider)] + _messages(rep)
        if progress is not None:
            progress(1.0, "write")
        return rep
    base2 = _PASS1_SHARE + _PLAN_SHARE
    ticker2 = _Ticker(in_path, progress, cancel, base2, 1.0 - base2, "write",
                      st.sol_bytes if o.keep else 0)
    _pass2(st, pl, o, in_path, out_path, ticker2)
    if st.mm_mismatch:
        st.warnings["mm_group_mismatch"] = st.mm_mismatch
    rep = _report(st, pl, o, {"pass1": t1 - t0, "plan": t2 - t1, "pass2": time.time() - t2})
    rep["written"] = True
    rep["out_path"] = out_path
    rep["mm_rewritten"] = st.mm_rewritten
    if mode == "collapse" and o.keep:
        rep["code"] = "done"
        head = message("done", len(st.failed), st.provider, out_path, o.names[0], o.names[1],
                       text_key="done_two")
    elif mode == "collapse":
        rep["code"] = "done"
        head = message("done", len(st.failed), st.provider, out_path)
    else:
        rep["code"] = "copied"
        head = message("copied", mode, out_path)
    rep["messages"] = [head] + _messages(rep)
    if progress is not None:
        progress(1.0, "write")
    return rep


def processed_marker(path, configuration=None):
    """The marker text of the target <solution>'s <results>, or None (never an empty text):
    the hidden count as written by 1.0.1 (u"3"; u"?" for an empty variable), else the version
    of the 1.0.0 attribute (u"1.0.0"); the variable wins when both are there. Presence is the
    signal; marker_count() of the text gives the count. configuration=None: the first
    <solution> with <results>, or, when the model part defines configurations (e.g. a
    keep_original output), the first marker of any <solution> (then the whole file may be
    read). An empty <solution ... /> (or <solution ...></solution>, a configuration without
    results) is a solution of its own without a marker; it never takes the marker of the next
    <solution> (1.0.2). Two solutions of the configuration: the first with <results> (process()
    refuses such a file). Raises no LimlFailedError; a split <solution tag counts as open.
    Reads up to the
    <results> line and the <globalvariable> lines right after it
    (where Mecway and the core put the marker), so it stays cheap (for a warning on an open
    processed model). process() itself also sees a marker further down, before the first
    <timestep>."""
    conf = None if configuration is None else _u(configuration)
    sol = False
    old = None
    in_res = False
    every = False               # configuration None in a model with configurations
    seen_sol = False
    with open(path, "rb") as f:
        for raw in f:
            s = raw.lstrip()
            try:
                if in_res:
                    if not s.strip():
                        continue
                    if not s.startswith(b"<globalvariable"):
                        if every and old is None:
                            in_res = sol = False
                            continue
                        return old
                    mk = _gv_marker(s)
                    if mk is not None:
                        return mk[0] or u"?"
                    continue
                if not sol:
                    if _is_solution_tag(s):
                        seen_sol = True
                        if _sol_empty(s):   # its own empty solution: no marker, and never the
                            continue        # next solution's (1.0.2, bridge KNOWN_BUGS 136)
                        c = _unescape(_attr(s, b"configuration"))
                        if conf is None or (c is not None and c.decode("utf-8", "replace") == conf):
                            sol = True
                    elif conf is None and not seen_sol and s.startswith(b"<configuration "):
                        every = True
                    continue
                if s.startswith(b"<results"):
                    mk = _attr(s, MARKER_ATTR)
                    old = None if mk is None else (mk.decode("ascii", "replace") or u"?")
                    if s.rstrip()[-2:] == b"/>":
                        return old
                    in_res = True
                elif s.startswith(b"</solution"):
                    sol = False
            except _Layout:         # single quotes: not our marker (process() refuses the file)
                continue
    return old


def _same(a, b):
    na = os.path.normcase(os.path.abspath(a))
    nb = os.path.normcase(os.path.abspath(b))
    if na == nb:
        return True
    try:
        return os.path.samefile(a, b)
    except (AttributeError, OSError):
        return False
