# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_monitor.py
#
# Responsibility: the text of the Code-Aster run that the bridge stores in
# the .liml as Mecway's "Saved monitor" item (GitHub issue #7, setting
# save_monitor), so that the output of the run can be read in Mecway after
# the Code-Aster windows have been closed. Builds the text from the .mess
# (and the console output); bridge_results_liml.splice_results writes it.
#
# HOW MECWAY STORES A SAVED MONITOR (Mecway 34.0.9772, measured headless
# 2026-10-28: a model with a top-level <savedmonitor /> solved with
# "mecway.exe model.liml solve", then reopened and saved with mw.save_as;
# Mecway manual par. 10.3 "Saved Monitor"):
#   <liml>
#     ...
#     <savedmonitor />                    top level: the tree item (Solution)
#     <solution>
#       ...model copy (without <savedmonitor />)...
#       <results precision="double">
#         <savedmonitor>
#           <output>00:00	Start 19:39:15 .
#   00:00	Allocating matrix
#   ...</output>                         plain text, CRLF lines
#         </savedmonitor>
#         <nodeids ...> ...
#       </results>
#     </solution>
# Measured with hand-written files (same Mecway, open + save_as): the text
# survives byte-identical, also 1.4 million characters (1.9 MB .liml) with
# escaped < > &, accents and tabs; a <results> with only <savedmonitor>
# (no variables) opens without a dialog (solution without values); without
# the top-level <savedmonitor /> Mecway keeps the text in <results> as
# well. The tree item itself could not be checked headless (the tree of
# the hidden main window is empty): NOT verified in the GUI.
#
# CONTENT (CONFIG_BRIDGE["save_monitor"]):
#   "summary" (default): header (model, run, path and size of the full
#       .mess, Code-Aster version, DIAGNOSTIC JOB), every error/alarm
#       message box (<EXCEPTION>, <F>, <S>, <E>, <A>, Python errors) once
#       with its number of occurrences, the alarm list of FIN
#       (CATAMESS_89), Python errors from the console output, the steps of
#       a nonlinear solve (bridge_convergence) or the progress lines, the
#       bridge's own lines (BRIDGE_..., aster_...:), timing and memory, and
#       the last lines of the .mess. At most SUMMARY_MAX_CHARS characters.
#   "full": the whole .mess; above FULL_MAX_CHARS the start and the end
#       with a note in between (a .mess of a long nonlinear run can be tens
#       of MB; the .liml should stay quick to open).
#   "off": nothing is stored.
# A run without results gets a solution with only the monitor only when the
# model has no results yet (bridge_results_liml.has_results,
# MecwayAsterBridgeMain._monitor_only): existing results are never replaced.
#
# Pure Python, standard library only; runs in Python 2.7 (IronPython
# 2.7.9, Mecway) and Python 3 (tests).

import io
import os
import re

try:
    from bridge_utils import tr
except ImportError:      # pragma: no cover - bridge_utils next to this file
    def tr(nl, en):
        return en

try:
    unicode
except NameError:        # Python 3
    unicode = str

MONITOR_MODES = ("summary", "full", "off")
SUMMARY_MAX_CHARS = 400000
FULL_MAX_CHARS = 4000000
_MAX_CODES = 100          # distinct message codes shown in full
_BOX_LINES = 80           # lines per message box
_STEPS_HEAD = 25          # first and last nonlinear steps
_BRIDGE_LINES = 200       # bridge lines (head + tail)
_TAIL_LINES = 40          # last lines of the .mess

# Message boxes of Code-Aster 17.4 (seen in .mess files): a frame of
# box-drawing characters, the first text line '<A> <CODE>' etc.
_MSG_RE = re.compile(
    u"^\\s*║?\\s*<(EXCEPTION|F|S|E|A|[A-Za-z]+Error)>\\s*<([A-Za-z0-9_]+)>")
_BOX_TOP = u"╔"
_BOX_BOTTOM = u"╚"
_BOX_SIDE = u"║"
_CATAMESS = u"<CATAMESS_89>"
_DIAG = u"DIAGNOSTIC JOB"
_VERSION_RE = re.compile(u"^\\s*Version (\\d+\\.\\d+\\.\\d+)")
_PROGRESS_RE = re.compile(u"^\\[\\s*\\d+%\\]")
_BRIDGE_RE = re.compile(u"^(BRIDGE_[A-Z0-9_]+\\b|aster_[a-z_]+:)")
_FIN_RE = re.compile(u"^\\s*<I>\\s*<FIN>")
_TIMING_HEAD = u"* COMMAND"
_TIMING_END = u"* TOTAL_JOB"
# Characters that XML 1.0 does not allow (control characters except tab,
# LF and CR; e.g. ANSI escape codes in console output).
_XML_BAD = re.compile(u"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def read_text(path):
    """Text of a .mess or console file (UTF-8, unreadable characters
    replaced), or None if it is missing."""
    if not path or not os.path.isfile(path):
        return None
    f = io.open(path, "rb")
    try:
        return f.read().decode("utf-8", "replace")
    finally:
        f.close()


def _head_tail(items, n):
    """The first n and the last n items with a note in between."""
    if len(items) <= 2 * n:
        return list(items)
    skipped = len(items) - 2 * n
    return (list(items[:n]) +
            [tr(u"   ... {0} regels overgeslagen ...",
                u"   ... {0} lines skipped ...").format(skipped)] +
            list(items[-n:]))


def _box(lines, i):
    """Lines of the message box whose first text line is lines[i]: up to and
    including the bottom of the frame (at most _BOX_LINES), with the top
    of the frame if it is the line before. A message without a frame: only
    that line."""
    out = []
    if i > 0 and lines[i - 1].strip().startswith(_BOX_TOP):
        out.append(lines[i - 1].rstrip())
    if not lines[i].strip().startswith(_BOX_SIDE):
        return out + [lines[i].rstrip()]
    for line in lines[i:i + _BOX_LINES]:
        out.append(line.rstrip())
        if line.strip().startswith(_BOX_BOTTOM):
            break
    else:
        out.append(u"   ...")
    return out


def _messages(lines):
    """[(kind, code, box lines, count)] of the error/alarm boxes in order of
    the first occurrence; each code only once."""
    order = []
    found = {}
    for i, line in enumerate(lines):
        m = _MSG_RE.match(line)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        if key in found:
            found[key][3] += 1
            continue
        entry = [m.group(1), m.group(2), _box(lines, i), 1]
        found[key] = entry
        order.append(entry)
    return order


def _catamess(lines):
    """Box of the alarm list of FIN (<I> <CATAMESS_89>), or []."""
    for i in range(len(lines) - 1, -1, -1):
        if _CATAMESS in lines[i]:
            return _box(lines, i)
    return []


def _timing(lines):
    """(memory lines of FIN and the timing table per command, index of the
    line after the table or None) at the end of the .mess."""
    out = [l.rstrip() for l in lines if _FIN_RE.match(l)]
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(_TIMING_HEAD):
            start = i - 1 if i > 0 else i
    if start is None:
        return out, None
    for j in range(start, min(len(lines), start + 400)):
        out.append(lines[j].rstrip())
        if lines[j].strip().startswith(_TIMING_END):
            if j + 1 < len(lines):
                out.append(lines[j + 1].rstrip())
            return out, j + 2
    return out, None


def _steps(text):
    """Lines with the steps of STAT_NON_LINE / DYNA_NON_LINE
    (bridge_convergence), or [] without a nonlinear solve or on a read
    error."""
    try:
        import bridge_convergence
        parser = bridge_convergence.ConvergenceParser()
        parser.feed(text)
        parser.close()
        data = parser.data
    except Exception:
        return []
    steps = data.steps
    if not steps:
        return []
    conv = len([s for s in steps if s.status == "geconvergeerd"])
    fail = [s for s in steps if s.status == "mislukt"]
    out = [tr(u"{0} pogingen, {1} geconvergeerd, {2} mislukt, {3} "
              u"Newton-iteraties in totaal.",
              u"{0} attempts, {1} converged, {2} failed, {3} Newton "
              u"iterations in total.").format(
                  len(steps), conv, len(fail),
                  sum(s.newton_count() for s in steps))]
    status = {"geconvergeerd": tr(u"geconvergeerd", u"converged"),
              "mislukt": tr(u"MISLUKT", u"FAILED"),
              "bezig": tr(u"niet afgerond", u"not finished")}

    def row(s):
        line = tr(u"  t = {0}  niveau {1}  {2} iteraties  {3}",
                  u"  t = {0}  level {1}  {2} iterations  {3}").format(
                      "%.6g" % s.instant if s.instant is not None else "?",
                      s.level, s.newton_count(),
                      status.get(s.status, s.status))
        if s.error:
            line += u"  " + s.error.strip()[:200]
        return line
    out.extend(_head_tail([row(s) for s in steps], _STEPS_HEAD))
    shown = set(steps[:_STEPS_HEAD] + steps[-_STEPS_HEAD:]) \
        if len(steps) > 2 * _STEPS_HEAD else set(steps)
    extra = [s for s in fail if s not in shown]
    if extra:
        out.append(tr(u"  Overige mislukte pogingen:",
                      u"  Other failed attempts:"))
        out.extend([row(s) for s in extra[:50]])
    return out


def summarize(text, mess_path=u"", console_text=None, header=None):
    """
    Summary of a .mess text (see the header of this file). header: lines
    put at the top (model, run). Returns unicode with LF line ends.
    """
    # Some lines of the .mess end in CR CR LF (seen in the timing table of
    # 17.4); splitlines() would give an empty line in between.
    lines = text.replace(u"\r", u"").split(u"\n")
    out = list(header or [])
    size = u""
    if mess_path and os.path.isfile(mess_path):
        # %-formatting: format() follows the locale in IronPython
        size = u" (%.2f MB)" % (os.path.getsize(mess_path) / 1.0e6)
    out.append(tr(u"Volledige Code-Aster-uitvoer: {0}{1}",
                  u"Full Code-Aster output: {0}{1}").format(
                      mess_path or u"?", size))
    version = u""
    for line in lines[:80]:
        m = _VERSION_RE.match(line)
        if m:
            version = m.group(1)
            break
    if version:
        out.append(u"Code-Aster {0}".format(version))
    diag = [l.strip() for l in lines if _DIAG in l]
    out.append(diag[-1] if diag else
               tr(u"Geen DIAGNOSTIC JOB in de .mess: de run is niet "
                  u"normaal beeindigd (gestopt of afgebroken).",
                  u"No DIAGNOSTIC JOB in the .mess: the run did not end "
                  u"normally (stopped or aborted)."))

    def section(title, body):
        if body:
            out.append(u"")
            out.append(u"== {0} ==".format(title))
            out.extend(body)

    msgs = _messages(lines)
    body = []
    for kind, code, box, count in msgs[:_MAX_CODES]:
        times = u"" if count == 1 else tr(u"  ({0} keer)",
                                          u"  ({0} times)").format(count)
        if len(box) == 1:
            # A message without a frame: the line itself
            body.append(box[0] + times)
            continue
        body.append(u"<{0}> <{1}>{2}".format(kind, code, times))
        body.extend(box)
    if len(msgs) > _MAX_CODES:
        body.append(tr(u"... en nog {0} andere meldingen (zie de .mess).",
                       u"... and {0} other messages (see the .mess).").format(
                           len(msgs) - _MAX_CODES))
    section(tr(u"Fouten en alarmen", u"Errors and alarms"), body or [
        tr(u"Geen fouten of alarmen.", u"No errors or alarms.")])
    section(tr(u"Alarmen volgens Code-Aster (FIN)",
               u"Alarms according to Code-Aster (FIN)"), _catamess(lines))
    if console_text:
        try:
            import bridge_convergence
            py = bridge_convergence.python_errors(console_text)
        except Exception:
            py = []
        section(tr(u"Python-fouten (console)", u"Python errors (console)"),
                py)
    steps = _steps(text)
    if steps:
        section(tr(u"Stappen (niet-lineair)", u"Steps (nonlinear)"), steps)
    else:
        section(tr(u"Voortgang", u"Progress"), _head_tail(
            [l.rstrip() for l in lines if _PROGRESS_RE.match(l)],
            _STEPS_HEAD))
    section(tr(u"Uitvoer van de bridge", u"Output of the bridge"),
            _head_tail([l.rstrip() for l in lines if _BRIDGE_RE.match(l)],
                       _BRIDGE_LINES // 2))
    timing, after = _timing(lines)
    section(tr(u"Tijd en geheugen", u"Time and memory"), timing)
    # The end of the .mess: after the timing table (a normal end), else the
    # last lines (a crash: traceback, last command).
    tail = [l.rstrip() for l in lines[after or 0:] if l.strip()]
    tail = tail[-_TAIL_LINES:]
    section(tr(u"Einde van de .mess", u"End of the .mess"), tail)
    result = u"\n".join(out)
    if len(result) > SUMMARY_MAX_CHARS:
        result = (result[:SUMMARY_MAX_CHARS] + u"\n" +
                  tr(u"... ingekort; zie de volledige .mess.",
                     u"... truncated; see the full .mess."))
    return result


def full_text(text, mess_path=u"", header=None):
    """The whole .mess with the header; above FULL_MAX_CHARS the first
    quarter and the last three quarters of that limit with a note."""
    if len(text) > FULL_MAX_CHARS:
        head = FULL_MAX_CHARS // 4
        text = (text[:head] + u"\n\n" +
                tr(u"... {0} tekens overgeslagen; zie de volledige .mess "
                   u"...",
                   u"... {0} characters skipped; see the full .mess "
                   u"...").format(len(text) - FULL_MAX_CHARS) + u"\n\n" +
                text[-(FULL_MAX_CHARS - head):])
    lines = list(header or [])
    lines.append(tr(u"Volledige Code-Aster-uitvoer: {0}",
                    u"Full Code-Aster output: {0}").format(mess_path or u"?"))
    lines.append(u"")
    return u"\n".join(lines) + u"\n" + text


def monitor_text(mess_path, mode="summary", console_path=None, header=None):
    """
    Text for the Saved monitor of a run, or None (mode "off", unknown mode
    or no .mess).
    """
    if mode not in ("summary", "full"):
        return None
    text = read_text(mess_path)
    if text is None:
        return None
    if mode == "full":
        return full_text(text, mess_path, header)
    return summarize(text, mess_path, read_text(console_path), header)


def xml_escape(text):
    """Text as XML element content: ASCII with character references,
    without characters XML does not allow, CRLF line ends (as Mecway)."""
    if not isinstance(text, unicode):
        text = text.decode("utf-8", "replace")
    text = _XML_BAD.sub(u"", text)
    text = text.replace(u"\r\n", u"\n").replace(u"\r", u"\n")
    text = (text.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;"))
    text = text.replace(u"\n", u"\r\n")
    return text.encode("ascii", "xmlcharrefreplace").decode("ascii")


def savedmonitor_block(text, nl="\r\n", indent="      "):
    """<savedmonitor><output>text</output></savedmonitor> as Mecway writes
    it inside <results> (str, ASCII), starting with nl."""
    return (nl + indent + "<savedmonitor>" + nl + indent + "  <output>" +
            str(xml_escape(text)) + "</output>" + nl + indent +
            "</savedmonitor>")
