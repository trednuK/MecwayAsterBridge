# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_convergence_monitor.py
# Convergence window: shows the convergence of STAT_NON_LINE/DYNA_NON_LINE
# (Newton residuals, progress, step splits, contact, messages) live during
# a Code-Aster run, or afterwards from a .mess file. For MECA_STATIQUE
# (linear static) it shows the linear solver: system, time per phase
# (live), error bound/condition number (MUMPS) or residual per iteration
# (GCPC) and an assessment.
#
# Does NOT run in Mecway but as a separate process in the CPython 3 of the
# Code-Aster installation (<installation>\Python311\pythonw.exe), with tkinter
# from that same installation (tested with Code-Aster 17.4 / Python 3.11.9 /
# Tk 8.6.12). Why a separate process:
#   - Mecway's script runs on Mecway's UI thread and, after starting
#     Code-Aster, waits in its modal status window (or mw.message()); a window
#     of its own in that process would depend on that wait loop and stop or
#     hang along with the script.
#   - A separate process keeps working when the Mecway script has finished,
#     and closing this window has no effect on the run or on Mecway.
#   - The parser (bridge_convergence.py) is shared with the bridge.
# Started by bridge_run_aster.start_convergence_monitor() (automatically on
# every run, setting convergence_monitor) or by the button
# Convergence window in the main window (afterwards).
#
# Usage:
#   pythonw aster_convergence_monitor.py --mess <workdir>\study.mess
#           [--since <time.time() of the start>] [--resi 1e-6]
#           [--iter-max 20] [--log <log file>] [--exit-after-finish <s>]
#           [--lang nl|en] [--paraview <paraview.exe>]
#
# Buttons in the top bar for the run shown: .comm and .mail in Notepad (no
# file association for these extensions), Folder (Explorer on the work
# folder with the .mess selected), ParaView (<model>_<run_id>.rmed, only
# with the setting med_export), Reload and Open .mess ... .
#
# Data source: see bridge_convergence.find_live_fort6(). During the run the
# window reads the fort.6 in the temporary run_aster folder (Code-Aster writes
# the .mess file only at the end); after that the .mess file itself. If a
# new run to the same .mess file starts, the window follows it.

import argparse
import codecs
import math
import os
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bridge_convergence as bc  # noqa: E402
import bridge_utils              # noqa: E402
from bridge_utils import tr      # noqa: E402

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError:      # pragma: no cover - only without tkinter
    tk = None

_LOG_PATH = None
_CHUNK = 4 * 1024 * 1024          # max. bytes per read
_POLL_MS = 1000                   # read interval during a run
_FONT = ("Segoe UI", 9)
_FONT_B = ("Segoe UI", 10, "bold")
_STATUS_COLORS = {"geconvergeerd": "#2e7d32", "mislukt": "#c62828",
                  "bezig": "#1565c0"}
# Display of Step.status (internal keys stay Dutch).
_STATUS_TEXT = {"geconvergeerd": ("geconvergeerd", "converged"),
                "mislukt": ("mislukt", "failed"),
                "bezig": ("bezig", "running")}


def _status_text(status):
    pair = _STATUS_TEXT.get(status)
    return tr(*pair) if pair else status


def log(text):
    """Line in the log file of the window (if --log is given)."""
    if not _LOG_PATH:
        return
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[{0}] {1}\n".format(
                time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except Exception:
        pass


def _hints():
    """Explanation per Code-Aster message code (bridge, chosen language)."""
    try:
        from bridge_run_aster import mess_hints
        return mess_hints()
    except Exception as e:
        log(tr("WARNING: uitleg bij meldingen niet geladen: {0}",
               "WARNING: explanations for messages not loaded: {0}").format(
                   e))
        return {}


def _tmp_dirs():
    """Folders in which run_aster creates its run_aster_* folder
    (bridge_convergence.aster_tmp_dirs for this installation)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    return bc.aster_tmp_dirs(root)


# ==========================================
# DATA SOURCE: live fort.6 or the .mess file
# ==========================================
class Source(object):
    """Delivers new text from the right source; poll() -> (reset, text)."""

    def __init__(self, mess_path, since):
        self.mess = mess_path
        self.since = since or 0.0
        self.tmp_dirs = _tmp_dirs()
        self.path = None
        self.kind = None             # "fort6" or "mess"
        self.offset = 0
        self.decoder = None
        self.run_created = None      # creation time of the run_aster folder
        self.mess_mtime = None
        self.last_growth = None      # last time the source grew
        self.backlog = False         # there is still unread text
        self._last_scan = 0.0
        log("INFO: source {0}, since {1}, temporary folders {2}".format(
            mess_path, self.since, self.tmp_dirs))

    def _start(self, path, kind, created=None):
        self.path, self.kind, self.offset = path, kind, 0
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        if kind == "fort6":
            self.run_created = created
        else:
            try:
                self.mess_mtime = os.path.getmtime(path)
            except OSError:
                self.mess_mtime = None
        self.last_growth = time.time()
        log("INFO: reading {0} ({1})".format(path, kind))

    def _mess_mtime(self):
        try:
            return os.path.getmtime(self.mess)
        except OSError:
            return None

    def poll(self):
        now = time.time()
        reset = False
        live = self.kind == "fort6" and os.path.exists(self.path)
        # Look for a new (or the first) live run; not while reading one.
        if not live and now - self._last_scan > 1.0:
            self._last_scan = now
            since = self.since
            if self.run_created is not None:
                since = max(since, self.run_created + 1.0)
            if self.kind == "mess" and self.mess_mtime:
                since = max(since, self.mess_mtime)
            fort6, created = bc.find_live_fort6(self.tmp_dirs, self.mess,
                                                since)
            mtime = self._mess_mtime()
            if fort6 and (mtime is None or mtime < created):
                self._start(fort6, "fort6", created)
                return True, self._read()
        if self.kind == "fort6" and not os.path.exists(self.path):
            # run_aster has cleaned up the folder: the .mess file is complete.
            mtime = self._mess_mtime()
            if mtime is not None and mtime >= (self.run_created or 0) - 1.0:
                self._start(self.mess, "mess")
                return True, self._read()
            return False, u""
        if self.kind is None or (self.kind == "mess" and
                                 self.path != self.mess):
            mtime = self._mess_mtime()
            if mtime is not None and (self.since <= 0 or
                                      mtime >= self.since - 1.0):
                self._start(self.mess, "mess")
                reset = True
            else:
                return False, u""
        elif self.kind == "mess":
            mtime = self._mess_mtime()
            try:
                size = os.path.getsize(self.path)
            except OSError:
                size = 0
            if mtime is not None and (size < self.offset or
                                      (self.mess_mtime is not None and
                                       mtime > self.mess_mtime + 0.5 and
                                       not self.backlog)):
                self._start(self.mess, "mess")   # rewritten
                reset = True
        return reset, self._read()

    def _read(self):
        try:
            with open(self.path, "rb") as f:     # open briefly: run_aster
                f.seek(self.offset)               # can delete the folder
                raw = f.read(_CHUNK)
        except (IOError, OSError):
            return u""
        self.offset += len(raw)
        self.backlog = len(raw) == _CHUNK
        if raw:
            self.last_growth = time.time()
        return self.decoder.decode(raw, final=False)

    def describe(self):
        if self.kind == "fort6":
            return u"live: {0}".format(self.path)
        if self.kind == "mess":
            return tr(u"bestand: {0}", u"file: {0}").format(self.path)
        return tr(u"wachten op Code-Aster ({0})",
                  u"waiting for Code-Aster ({0})").format(self.mess)


class ConsoleWatcher(object):
    """
    Reads study_console.txt (stdout + stderr of run_aster, captured by
    bridge_run_aster) and looks for Python errors in study.comm; those are
    not in fort.6/study.mess (bridge_convergence.python_errors).
    """

    def __init__(self, path, since):
        self.path = path
        self.since = since or 0.0
        self.offset = 0
        self.tail = u""
        self.errors = []
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.mtime = None

    def poll(self):
        """True if there are new errors."""
        if not self.path:
            return False
        try:
            mtime = os.path.getmtime(self.path)
            size = os.path.getsize(self.path)
        except OSError:
            return False
        if mtime < self.since - 1.0:
            return False
        if size < self.offset:          # new run: start over
            self.offset, self.tail, self.errors = 0, u"", []
            self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.mtime = mtime
        if size == self.offset:
            return False
        try:
            with open(self.path, "rb") as f:
                f.seek(self.offset)
                raw = f.read(_CHUNK)
        except (IOError, OSError):
            return False
        self.offset += len(raw)
        # The last 80 lines are included: a traceback can be split over two
        # reads.
        text = self.tail + self.decoder.decode(raw, final=False)
        self.tail = u"\n".join(text.split(u"\n")[-80:])
        new = [e for e in bc.python_errors(text) if e not in self.errors]
        if new:
            self.errors.extend(new)
            log(tr(u"ERROR: Python-fout in de console-uitvoer: {0}",
                   u"ERROR: Python error in the console output: {0}").format(
                u"; ".join(new)))
        return bool(new)


# ==========================================
# PLOT ON A tk.Canvas
# ==========================================
def _nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / float(n)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    start = math.floor(lo / step) * step
    ticks = []
    v = start
    while v <= hi + step * 1e-9:
        ticks.append(v)
        v += step
    return ticks[0], ticks[-1], ticks


def _fmt(v):
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1e4 or a < 1e-3:
        return "%.0e" % v
    if a >= 100 or float(v).is_integer():
        return "%.0f" % v
    return "%.3g" % v


class Plot(object):
    PL, PR, PT, PB = 70, 64, 40, 34

    def __init__(self, master, title, on_click=None):
        self.c = tk.Canvas(master, background="white", highlightthickness=1,
                           highlightbackground="#bbbbbb")
        self.title = title
        self.cfg = {}
        self.on_click = on_click
        self._map = None
        self.c.bind("<Configure>", lambda e: self.draw())
        self.c.bind("<Button-1>", self._click)

    def set(self, **cfg):
        self.cfg = cfg
        self.draw()

    def _click(self, event):
        if self.on_click and self._map:
            x0, x1, px0, px1 = self._map
            if px1 > px0:
                self.on_click(x0 + (event.x - px0) * (x1 - x0) /
                              float(px1 - px0))

    @staticmethod
    def _range(values, log_axis, extra=()):
        vals = [v for v in list(values) + list(extra) if v is not None]
        if log_axis:
            vals = [v for v in vals if v > 0]
            if not vals:
                return None
            lo = math.floor(math.log10(min(vals)))
            hi = math.ceil(math.log10(max(vals)))
            if hi <= lo:
                hi = lo + 1
            return (lo, hi, None)
        if not vals:
            return None
        lo, hi = min(vals + [0.0]), max(vals)
        if hi == lo:
            hi = lo + 1.0
        lo, hi, ticks = _nice_ticks(lo, hi)
        return (lo, hi, ticks)

    def draw(self):
        c = self.c
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 50 or h < 50:
            return
        cfg = self.cfg
        c.create_text(8, 4, anchor="nw", text=self.title, font=_FONT_B)
        series = cfg.get("series", [])
        pts_all = [p for s in series for p in s["points"]
                   if p is not None and p[1] is not None]
        if not pts_all:
            c.create_text(w / 2, h / 2, text=cfg.get(
                "empty", tr(u"Nog geen gegevens", u"No data yet")),
                fill="#777777", font=_FONT)
            self._map = None
            return
        px0, px1 = self.PL, w - self.PR
        py0, py1 = self.PT, h - self.PB
        xs = [p[0] for p in pts_all]
        x0 = cfg.get("xmin", min(xs))
        x1 = cfg.get("xmax", max(xs))
        if x1 <= x0:
            x0, x1 = x0 - 0.5, x0 + 0.5
        pad = (x1 - x0) * 0.02 if cfg.get("pad_x", True) else 0.0
        x0, x1 = x0 - pad, x1 + pad
        self._map = (x0, x1, px0, px1)

        def X(x):
            return px0 + (x - x0) * (px1 - px0) / (x1 - x0)

        axes = {}
        for side in ("left", "right"):
            vals = [p[1] for s in series if s.get("axis", "left") == side
                    for p in s["points"] if p is not None]
            extra = [hl[0] for hl in cfg.get("hlines", [])] \
                if side == "left" else []
            rng = self._range(vals, cfg.get("ylog_" + side, False), extra)
            if rng is not None:
                axes[side] = rng

        def make_Y(side):
            lo, hi, _t = axes[side]
            logax = cfg.get("ylog_" + side, False)

            def Y(y):
                if y is None or (logax and y <= 0):
                    return None
                v = math.log10(y) if logax else y
                v = min(max(v, lo), hi)
                return py1 - (v - lo) * (py1 - py0) / float(hi - lo)
            return Y
        Ys = dict((side, make_Y(side)) for side in axes)

        # Grid and axes
        c.create_rectangle(px0, py0, px1, py1, outline="#888888")
        for side in axes:
            lo, hi, ticks = axes[side]
            logax = cfg.get("ylog_" + side, False)
            if logax:
                step = max(1, int(math.ceil((hi - lo) / 8.0)))
                ticks = [10.0 ** e for e in range(int(lo), int(hi) + 1, step)]
            Y = Ys[side]
            for t in ticks:
                y = Y(t)
                if y is None:
                    continue
                if side == "left":
                    c.create_line(px0, y, px1, y, fill="#eeeeee")
                    c.create_text(px0 - 4, y, anchor="e", font=_FONT,
                                  text=("1e%d" % round(math.log10(t)))
                                  if logax else _fmt(t))
                else:
                    c.create_text(px1 + 4, y, anchor="w", font=_FONT,
                                  fill="#555555",
                                  text=("1e%d" % round(math.log10(t)))
                                  if logax else _fmt(t))
        xl, xh, xt = _nice_ticks(x0, x1, max(2, int((px1 - px0) / 90)))
        for t in xt:
            if x0 <= t <= x1:
                x = X(t)
                c.create_line(x, py1, x, py1 + 4, fill="#888888")
                c.create_text(x, py1 + 6, anchor="n", text=_fmt(t),
                              font=_FONT)
        if cfg.get("xlabel"):
            c.create_text((px0 + px1) / 2, h - 2, anchor="s",
                          text=cfg["xlabel"], font=_FONT, fill="#444444")
        if cfg.get("ylabel") and "left" in axes:
            c.create_text(6, (py0 + py1) / 2, anchor="n", angle=90,
                          text=cfg["ylabel"], font=_FONT, fill="#444444")
        if cfg.get("ylabel_right") and "right" in axes:
            c.create_text(w - 6, (py0 + py1) / 2, anchor="n", angle=-90,
                          text=cfg["ylabel_right"], font=_FONT,
                          fill="#555555")

        # Vertical and horizontal guide lines
        for vx, color, label, dash in cfg.get("vlines", []):
            if x0 <= vx <= x1:
                x = X(vx)
                c.create_line(x, py0, x, py1, fill=color, dash=dash)
                if label:
                    c.create_text(x + 2, py0 + 2, anchor="nw", text=label,
                                  font=("Segoe UI", 7), fill=color)
        if "left" in Ys:
            for hy, color, label in cfg.get("hlines", []):
                y = Ys["left"](hy)
                if y is not None:
                    c.create_line(px0, y, px1, y, fill=color, dash=(6, 3),
                                  width=2)
                    c.create_text(px1 - 4, y - 2, anchor="se", text=label,
                                  font=_FONT, fill=color)

        # Series
        nx = max(1.0, x1 - x0)
        for s in series:
            side = s.get("axis", "left")
            if side not in Ys:
                continue
            Y = Ys[side]
            kind = s.get("kind", "line")
            color = s.get("color", "#1565c0")
            colors = s.get("colors")
            if kind == "bars":
                bw = max(1.0, 0.7 * (px1 - px0) / nx)
                ybase = Y(axes[side][0]) if not cfg.get(
                    "ylog_" + side) else py1
                if not cfg.get("ylog_" + side) and Y(0.0) is not None:
                    ybase = Y(0.0)
                for i, p in enumerate(s["points"]):
                    if p is None or p[1] is None:
                        continue
                    y = Y(p[1])
                    if y is None:
                        continue
                    x = X(p[0])
                    col = colors[i] if colors else color
                    c.create_rectangle(x - bw / 2, y, x + bw / 2, ybase,
                                       fill=col, outline=col)
                continue
            if kind in ("line", "step", "linemarkers"):
                seg = []
                prev = None
                for p in s["points"] + [None]:
                    y = Y(p[1]) if p is not None else None
                    if y is None:
                        if len(seg) >= 4:
                            c.create_line(*seg, fill=color,
                                          width=s.get("width", 1.5))
                        seg, prev = [], None
                        continue
                    x = X(p[0])
                    if kind == "step" and prev is not None:
                        seg += [x, prev]
                    seg += [x, y]
                    prev = y
            if kind in ("markers", "linemarkers"):
                r = s.get("size", 3)
                for i, p in enumerate(s["points"]):
                    if p is None:
                        continue
                    y = Y(p[1])
                    if y is None:
                        continue
                    x = X(p[0])
                    col = colors[i] if colors else color
                    c.create_oval(x - r, y - r, x + r, y + r, fill=col,
                                  outline=col)

        # Legend
        # Legend: one line between title and plot.
        lx = px0
        ly = py0 - 12
        for s in series:
            if not s.get("name"):
                continue
            c.create_rectangle(lx, ly - 4, lx + 10, ly + 4,
                               fill=s.get("color", "#1565c0"), outline="")
            t = c.create_text(lx + 14, ly, anchor="w", text=s["name"],
                              font=_FONT)
            bbox = c.bbox(t)
            lx = (bbox[2] if bbox else lx + 80) + 12


# ==========================================
# LINEAR ANALYSIS (MECA_STATIQUE): cards on a tk.Canvas
#
# As usual in pre/post software (solver monitor): an overview
# of the system and the solver, the time course per phase (live), the
# quality of the solution (residual, error bound, condition number; with
# GCPC the residual per iteration) and an assessment with explanation.
# ==========================================
_C_TEXT = "#222222"
_C_LABEL = "#555555"
_C_MUTED = "#9e9e9e"
_C_GRID = "#e0e0e0"
_C_BLUE = "#1565c0"
_C_GREEN = "#2e7d32"
_C_RED = "#c62828"
_C_ORANGE = "#ef6c00"
_C_INFO = "#607d8b"
_LEVEL_COLORS = {"ok": _C_GREEN, "info": _C_INFO, "let_op": _C_ORANGE,
                 "fout": _C_RED}
_FONT_SMALL = ("Segoe UI", 8)
_FONT_VALUE = ("Segoe UI", 9, "bold")


def _int(n):
    """Integer with a space as thousands separator: 268 569."""
    if n is None:
        return u"-"
    return u"{0:,}".format(int(n)).replace(u",", u" ")


def _sci(v, digits=2):
    if v is None:
        return u"-"
    return (u"{0:.%de}" % digits).format(v)


def _secs(s):
    if s is None:
        return u"-"
    if s < 0.01:
        return u"< 0.01 s"
    if s < 60:
        return u"{0:.2f} s".format(s) if s < 10 else u"{0:.1f} s".format(s)
    return _duration(s)


class Card(object):
    """Canvas with a title in the style of Plot; draw(fn) draws the content
    with fn(canvas, width, height, y_below_title)."""

    def __init__(self, master, title):
        self.c = tk.Canvas(master, background="white", highlightthickness=1,
                           highlightbackground="#bbbbbb")
        self.title = title
        self.fn = None
        self.c.bind("<Configure>", lambda e: self.redraw())

    def draw(self, fn):
        self.fn = fn
        self.redraw()

    def redraw(self):
        c = self.c
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 50 or h < 50:
            return
        c.create_text(8, 4, anchor="nw", text=self.title, font=_FONT_B)
        if self.fn is not None:
            try:
                self.fn(c, w, h, 30)
            except Exception:
                log("ERROR: " + traceback.format_exc())


def _rows(c, x, y, w, rows, label_w=170, dy=19):
    """Label/value table; rows = [(label, value, colour or None)]."""
    for label, value, color in rows:
        c.create_text(x, y, anchor="nw", text=label, font=_FONT,
                      fill=_C_LABEL)
        c.create_text(x + label_w, y, anchor="nw", text=value,
                      font=_FONT_VALUE, fill=color or _C_TEXT,
                      width=max(60, w - x - label_w - 8))
        y += dy
    return y


def _log_x(v, lo, hi, x0, x1):
    e = math.log10(v) if v and v > 0 else lo
    e = min(max(e, lo), hi)
    return x0 + (e - lo) * (x1 - x0) / float(hi - lo)


def _log_strip(c, x0, x1, y, title, items, lo, hi, zones=(), lines=(),
               step=3):
    """
    Dot plot on a log axis (one row per value), like a
    solver report: items = [(label, value, colour)], zones = [(from, to,
    colour)] as background (exponents), lines = [(value, colour,
    label)], step = distance between the axis ticks (decades). Returns y
    below the strip.
    """
    c.create_text(x0, y, anchor="nw", text=title, font=_FONT_VALUE,
                  fill=_C_TEXT)
    y += 30
    lab_w = 150
    ax0, ax1 = x0 + lab_w, x1 - 10
    if ax1 - ax0 < 80:
        return y
    top = y - 10
    bottom = y + 18 * len(items) - 6
    for z0, z1, color in zones:
        c.create_rectangle(_log_x(10.0 ** z0, lo, hi, ax0, ax1), top,
                           _log_x(10.0 ** z1, lo, hi, ax0, ax1), bottom,
                           fill=color, outline="")
    for e in range(int(lo), int(hi) + 1, step):
        x = _log_x(10.0 ** e, lo, hi, ax0, ax1)
        c.create_line(x, top, x, bottom, fill=_C_GRID)
        c.create_text(x, bottom + 2, anchor="n", text=u"1e{0}".format(e),
                      font=_FONT_SMALL, fill=_C_LABEL)
    for value, color, label in lines:
        if value and value > 0:
            x = _log_x(value, lo, hi, ax0, ax1)
            c.create_line(x, top - 2, x, bottom, fill=color, dash=(5, 3),
                          width=2)
            c.create_text(x + 3, top - 3, anchor="sw", text=label,
                          font=_FONT_SMALL, fill=color)
    for label, value, color in items:
        c.create_text(x0, y, anchor="w", text=label, font=_FONT,
                      fill=_C_LABEL)
        if value is None:
            c.create_text(ax0 + 4, y, anchor="w", text=u"-", font=_FONT,
                          fill=_C_MUTED)
        else:
            x = _log_x(value, lo, hi, ax0, ax1)
            c.create_line(ax0, y, x, y, fill=_C_GRID, width=1)
            c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color,
                          outline=color)
            anchor = "e" if x > ax1 - 60 else "w"
            t = c.create_text(x + (-8 if anchor == "e" else 8), y,
                              anchor=anchor, text=_sci(value), font=_FONT,
                              fill=_C_TEXT)
            bbox = c.bbox(t)
            if bbox:     # readable on top of guide lines
                c.tag_lower(c.create_rectangle(
                    bbox[0] - 1, bbox[1], bbox[2] + 1, bbox[3],
                    fill="white", outline=""), t)
        y += 18
    return bottom + 22


# ==========================================
# MAIN WINDOW
# ==========================================
class Monitor(object):

    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.hints = _hints()
        self.source = Source(args.mess, args.since)
        self.console = ConsoleWatcher(args.console, args.since)
        self.parser = None
        self._new_parser()
        self.sel = None              # selected attempt (None = latest)
        self._last_draw = 0.0
        self.started = time.time()

        root.title(tr(u"Convergentie Code-Aster - {0}",
                      u"Code-Aster convergence - {0}").format(
            os.path.basename(args.mess)))
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry("{0}x{1}+20+20".format(min(1250, sw - 40),
                                             min(920, sh - 80)))
        root.configure(background="#f4f4f4")

        top = tk.Frame(root, background="#f4f4f4")
        top.pack(side="top", fill="x", padx=6, pady=(6, 0))
        tk.Button(top, text=u"Open .mess ...", command=self.open_file,
                  font=_FONT).pack(side="right", padx=2)
        tk.Button(top, text=tr(u"Opnieuw lezen", u"Reload"),
                  command=self.reload,
                  font=_FONT).pack(side="right", padx=2)
        # Files of the run shown (packed right to left: ParaView, Folder,
        # .mail, .comm); state per file in _update_buttons().
        self.btn_files = {}
        for key, text, command in (
                ("rmed", u"ParaView", self.open_paraview),
                ("folder", tr(u"Map", u"Folder"), self.open_folder),
                ("mail", u".mail", lambda: self.open_notepad(".mail")),
                ("comm", u".comm", lambda: self.open_notepad(".comm"))):
            btn = tk.Button(top, text=text, command=command, font=_FONT)
            btn.pack(side="right", padx=2)
            self.btn_files[key] = btn
        self._update_buttons()
        self.lbl_source = tk.Label(top, text=u"", anchor="w", font=_FONT,
                                   foreground="#555555", background="#f4f4f4")
        self.lbl_source.pack(side="left", fill="x", expand=True)
        self.lbl_status = tk.Label(root, text=u"",
                                   font=("Segoe UI", 11, "bold"), anchor="w",
                                   justify="left", background="#f4f4f4")
        self.lbl_status.pack(side="top", fill="x", padx=6)
        self.lbl_status.bind("<Configure>", lambda e: self.lbl_status.configure(
            wraplength=max(200, e.width - 10)))

        grid = tk.Frame(root, background="#f4f4f4")
        grid.pack(side="top", fill="both", expand=True, padx=6, pady=4)
        for i in range(2):
            grid.columnconfigure(i, weight=1, uniform="col")
            grid.rowconfigure(i, weight=1, uniform="row")
        self.p_resi = Plot(grid, tr(u"(a) Residu per Newton-iteratie",
                                    u"(a) Residual per Newton iteration"))
        self.p_prog = Plot(grid, tr(u"(b) Voortgang: berekend tijdstip per "
                                    u"rekenpoging",
                                    u"(b) Progress: computed time per "
                                    u"solver attempt"),
                           on_click=self._click_step)
        self.p_newt = Plot(grid, tr(u"(c) Newton-iteraties per rekenpoging",
                                    u"(c) Newton iterations per solver "
                                    u"attempt"),
                           on_click=self._click_step)
        self.p_cont = Plot(grid, tr(u"(d) Contact per Newton-iteratie",
                                    u"(d) Contact per Newton iteration"))
        self.p_resi.c.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.p_prog.c.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.p_cont.c.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.p_newt.c.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        self._build_linear(grid)

        ctl = tk.Frame(root, background="#f4f4f4")
        ctl.pack(side="top", fill="x", padx=6)
        self.ctl = ctl
        tk.Label(ctl, text=tr(u"Rekenpogingen in (a) en (d):",
                              u"Solver attempts in (a) and (d):"),
                 font=_FONT,
                 background="#f4f4f4").pack(side="left")
        self.var_n = tk.IntVar(value=3)
        tk.Spinbox(ctl, from_=1, to=50, width=4, textvariable=self.var_n,
                   command=self._changed, font=_FONT).pack(side="left",
                                                          padx=(2, 12))
        self.var_follow = tk.BooleanVar(value=True)
        tk.Checkbutton(ctl, text=tr(u"Volg laatste poging",
                                    u"Follow last attempt"),
                       variable=self.var_follow, command=self._changed,
                       font=_FONT, background="#f4f4f4").pack(side="left")
        tk.Label(ctl, text=tr(u"   Poging:", u"   Attempt:"), font=_FONT,
                 background="#f4f4f4").pack(side="left")
        self.scale = tk.Scale(ctl, from_=1, to=1, orient="horizontal",
                              showvalue=True, command=self._scale_moved,
                              length=420, font=_FONT, background="#f4f4f4",
                              highlightthickness=0)
        self.scale.pack(side="left", fill="x", expand=True)

        self.lbl_step = tk.Label(root, text=u"", anchor="w", justify="left",
                                 font=("Consolas", 9), background="#f4f4f4")
        self.lbl_step.pack(side="top", fill="x", padx=6, pady=(2, 2))

        frm = tk.Frame(root)
        frm.pack(side="top", fill="x", padx=6, pady=(0, 6))
        self.frm_msgs = frm
        tk.Label(frm, text=tr(u"(e) Meldingen (laatste onderaan; FOUT = "
                              u"rood, ALARM = oranje, actie = grijs)",
                              u"(e) Messages (latest at the bottom; ERROR "
                              u"= red, ALARM = orange, action = grey)"),
                 anchor="w",
                 font=_FONT_B).pack(side="top", fill="x")
        self.txt = tk.Text(frm, height=9, wrap="word", font=("Segoe UI", 9))
        sb = tk.Scrollbar(frm, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.tag_configure("fout", foreground="#c62828")
        self.txt.tag_configure("alarm", foreground="#e65100")
        self.txt.tag_configure("actie", foreground="#777777")
        self.txt.tag_configure("hint", foreground="#1b5e20",
                               lmargin1=24, lmargin2=24)

        root.after(50, self.tick)

    # ---------- controls ----------
    def _new_parser(self):
        clock = time.time if self.source.kind == "fort6" else None
        self.parser = bc.ConvergenceParser(hints=self.hints, clock=clock)
        self.dirty = True
        self.finished_at = None
        self._msg_state = None

    def _changed(self, *args):
        self.dirty = True
        self.redraw(force=True)

    def _scale_moved(self, value):
        steps = self.parser.data.steps
        idx = int(float(value)) - 1   # scale counts from 1
        if steps and idx < len(steps) - 1:
            self.var_follow.set(False)
        self.sel = idx
        self.redraw(force=True)

    def _click_step(self, x):
        steps = self.parser.data.steps
        if not steps:
            return
        idx = int(round(x)) - 1
        idx = max(0, min(len(steps) - 1, idx))
        self.var_follow.set(idx == len(steps) - 1)
        self.sel = idx
        self.scale.set(idx + 1)
        self.redraw(force=True)

    def open_file(self):
        path = filedialog.askopenfilename(
            title=tr(u"Code-Aster .mess openen", u"Open Code-Aster .mess"),
            initialdir=os.path.dirname(self.source.mess),
            filetypes=[(tr(u"Code-Aster berichten", u"Code-Aster messages"),
                        "*.mess"),
                       (tr(u"Code-Aster uitvoer", u"Code-Aster output"),
                        "fort.6"),
                       (tr(u"Alle bestanden", u"All files"), "*.*")])
        if not path:
            return
        log("INFO: user opens {0}".format(path))
        self.args.mess = path
        self.source = Source(path, 0.0)
        # Console output of the same run: <model>_<run_id>_console.txt
        # next to <model>_<run_id>.mess (older runs: study_console.txt).
        console = _run_file(path, "_console.txt")
        self.console = ConsoleWatcher(
            console if path.lower().endswith(".mess") and
            os.path.exists(console) else None, 0.0)
        self._new_parser()
        self.sel = None
        self.var_follow.set(True)
        self._update_buttons()
        self.root.title(tr(u"Convergentie Code-Aster - {0}",
                           u"Code-Aster convergence - {0}").format(
            os.path.basename(path)))

    # ---------- files of the run ----------
    def _update_buttons(self):
        """.comm/.mail disabled if the file of the run shown is missing;
        ParaView and Folder stay enabled (they explain what is missing)."""
        mess = self.args.mess
        for key in ("comm", "mail"):
            state = ("normal" if os.path.isfile(_run_file(mess, "." + key))
                     else "disabled")
            btn = self.btn_files.get(key)
            if btn is not None and str(btn.cget("state")) != state:
                btn.configure(state=state)

    def _popen(self, args, creationflags=0):
        try:
            subprocess.Popen(args, creationflags=creationflags)
            log(u"INFO: started {0}".format(args))
            return True
        except Exception as e:
            log(u"WARNING: {0} not started: {1}".format(args, e))
            messagebox.showerror(u"Code-Aster", tr(
                u"Starten mislukt: {0}\n{1}",
                u"Starting failed: {0}\n{1}").format(
                    args if isinstance(args, str) else args[0], e),
                parent=self.root)
            return False

    def open_notepad(self, suffix):
        """.comm or .mail of the run in Notepad (no file association)."""
        path = _run_file(self.args.mess, suffix)
        if not os.path.isfile(path):
            messagebox.showinfo(u"Code-Aster", tr(
                u"Bestand niet gevonden: {0}", u"File not found: {0}").format(
                    path), parent=self.root)
            return
        self._popen(["notepad.exe", path])

    def open_folder(self):
        """Explorer on the work folder, with the .mess of the run selected
        (or the folder itself if the .mess is missing)."""
        mess = os.path.abspath(self.args.mess)
        folder = os.path.dirname(mess)
        if os.path.isfile(mess):
            # one command string: explorer wants /select,"<path>" (a
            # quoted list argument "/select,<path>" is NOT verified)
            self._popen(u'explorer.exe /select,"{0}"'.format(mess))
        elif os.path.isdir(folder):
            self._popen(["explorer.exe", folder])
        else:
            messagebox.showinfo(u"Code-Aster", tr(
                u"Map niet gevonden: {0}", u"Folder not found: {0}").format(
                    folder), parent=self.root)

    def open_paraview(self):
        """<model>_<run_id>.rmed of the run in ParaView (--paraview)."""
        rmed = _run_file(self.args.mess, ".rmed")
        if not os.path.isfile(rmed):
            messagebox.showinfo(u"ParaView", tr(
                u"Geen MED-bestand voor deze run:\n{0}\n\nZet in het "
                u"startscherm 'MED-bestand voor ParaView' (med_export) aan "
                u"en start de run opnieuw.",
                u"No MED file for this run:\n{0}\n\nTurn on 'MED file for "
                u"ParaView' (med_export) on the start screen and run "
                u"again.").format(rmed), parent=self.root)
            return
        exe = self.args.paraview
        if exe is None:
            exe = bridge_utils.paraview_exe_path()
        if not exe or not os.path.isfile(exe):
            messagebox.showinfo(u"ParaView", tr(
                u"ParaView niet gevonden{0}. Vul in het startscherm "
                u"'ParaView' (paraview_exe) in; neem ParaView 6.x van "
                u"paraview.org (leest een .rmed) of die van Salome-Meca: "
                u"ParaView 5.10 kan geen .rmed openen.",
                u"ParaView not found{0}. Fill in 'ParaView' (paraview_exe) "
                u"on the start screen; use ParaView 6.x from paraview.org "
                u"(reads a .rmed) or the one of Salome-Meca: ParaView 5.10 "
                u"cannot open a .rmed.").format(
                    u" ({0})".format(exe) if exe else u""),
                parent=self.root)
            return
        # Salome-Meca: run_paraview.bat (bridge_utils._salome_launcher)
        # opens a console only to set the environment; without a window.
        flags = 0x08000000 if exe.lower().endswith(".bat") else 0
        self._popen([exe, rmed], flags)

    def _names(self, text):
        """study.comm / study_console.txt in a message -> the files
        of the shown run (<model>_<run_id>.comm, ...)."""
        mess = self.args.mess
        return (text.replace(u"study.comm", os.path.basename(
                    _run_file(mess, ".comm")))
                .replace(u"study_console.txt", os.path.basename(
                    _run_file(mess, "_console.txt"))))

    def reload(self):
        self.source = Source(self.args.mess, self.source.since)
        self.console = ConsoleWatcher(self.console.path, self.console.since)
        self._new_parser()

    # ---------- loop ----------
    def tick(self):
        try:
            reset, text = self.source.poll()
            if reset:
                self._new_parser()
            if text:
                self.parser.feed(text)
                self.dirty = True
            if self.console.poll():
                self.dirty = True
            if (self.source.kind == "mess" and not self.source.backlog
                    and self.parser._partial):
                self.parser.close()
            data = self.parser.data
            lin = data.last_linear()
            if (lin is not None and not lin.finished() and
                    self.source.kind == "fort6"):
                self.dirty = True     # running phase: time keeps counting
            if data.finished() and self.finished_at is None:
                self.finished_at = time.time()
                log(u"INFO: run finished ({0}); summary:\n{1}".format(
                    data.diagnostic, bc.summarize(data)))
            self.redraw()
            self._update_buttons()
            if (self.args.exit_after_finish is not None and
                    self.finished_at is not None and
                    self.source.kind == "mess" and not self.source.backlog
                    and time.time() - self.finished_at >
                    self.args.exit_after_finish):
                log(u"INFO: --exit-after-finish: window closed; "
                    u"source {0}\n{1}".format(self.source.describe(),
                                            bc.summarize(data)))
                self.root.destroy()
                return
        except Exception:
            log("ERROR: " + traceback.format_exc())
        self.root.after(50 if self.source.backlog else _POLL_MS, self.tick)

    # ---------- drawing ----------
    def redraw(self, force=False):
        now = time.time()
        if not force and (not self.dirty or now - self._last_draw < 0.9):
            self._update_status()
            return
        self._last_draw = now
        self.dirty = False
        data = self.parser.data
        lin = data.last_linear() if not data.steps else None
        if lin is not None:
            self._update_status()
            self._draw_linear(lin)
            self._draw_messages(data)
            return
        self._set_mode("nonlinear")
        steps = data.steps
        n = len(steps)
        self.scale.configure(to=max(1, n))
        if self.var_follow.get() or self.sel is None or self.sel >= n:
            self.sel = n - 1 if n else None
            if n:
                self.scale.set(self.sel + 1)
        self._update_status()
        self._draw_resi(data)
        self._draw_progress(data)
        self._draw_newton(data)
        self._draw_contact(data)
        self._draw_step(data)
        self._draw_messages(data)

    def _window(self, data):
        if self.sel is None:
            return []
        try:
            k = max(1, int(self.var_n.get()))
        except (ValueError, tk.TclError):
            k = 3
        return data.steps[max(0, self.sel - k + 1):self.sel + 1]

    def _criterion(self, data):
        return data.resi_crit or self.args.resi

    def _update_status(self):
        data = self.parser.data
        src = self.source
        steps = data.steps
        parts = []
        if src.kind is None:
            state = tr(u"Wachten op Code-Aster", u"Waiting for Code-Aster")
        elif data.stopped:
            state = bc.stopped_text(data.stopped)
        elif data.finished():
            state = tr(u"Klaar ({0})", u"Finished ({0})").format(
                data.diagnostic)
        elif src.kind == "fort6" and not os.path.exists(src.path):
            state = tr(u"Run gestopt; wachten op het .mess-bestand",
                       u"Run stopped; waiting for the .mess file")
        elif src.kind == "fort6":
            state = tr(u"Bezig", u"Running")
        else:
            state = tr(u"Niet afgesloten (afgebroken of nog bezig?)",
                       u"Not closed (aborted or still running?)")
        if self.console.errors:
            state = self._names(tr(
                u"Python-fout in study.comm (zie meldingen)",
                u"Python error in study.comm (see messages)"))
        elif data.finished() and not data.fin:
            state = self._names(tr(
                u"Gestopt voor FIN ({0}; Python-fout in study.comm?)",
                u"Stopped before FIN ({0}; Python error in "
                u"study.comm?)")).format(data.diagnostic)
        parts.append(state)
        if data.command:
            parts.append(data.command)
        lin = data.last_linear() if not steps else None
        if lin is not None:
            parts.append(lin.method())
            if lin.current is not None and not lin.finished():
                sec = lin.phase_seconds(lin.current, time.time())
                parts.append(tr(u"fase: {0}", u"phase: {0}").format(
                    bc.lin_phase_title(lin.current, lin.method())) +
                    (u" ({0})".format(_secs(sec)) if sec is not None
                     else u""))
            elif lin.status == "klaar":
                parts.append(tr(u"opgelost", u"solved"))
            elif lin.status == "mislukt":
                parts.append(tr(u"MISLUKT", u"FAILED"))
        last = data.last_converged()
        if last is not None:
            parts.append(tr(u"bereikt t = {0:.6g} s",
                            u"reached t = {0:.6g} s").format(last.instant))
        if steps:
            cur = steps[-1]
            parts.append(tr(u"poging {0}: t = {1:.6g} s, niveau {2}",
                            u"attempt {0}: t = {1:.6g} s, level {2}").format(
                cur.index + 1, cur.instant, cur.level))
        overall = data.overall_progress()
        if overall:
            parts.append(u"{0}%".format(overall[0]))
        if src.kind == "fort6" and src.run_created:
            el = time.time() - src.run_created
            parts.append(u"{0}".format(_duration(el)))
            if overall and 0 < overall[0] < 100:
                p = overall[0]
                parts.append(tr(u"nog ~{0}", u"~{0} to go").format(
                    _duration(el * (100 - p) / float(p))))
            if src.last_growth and time.time() - src.last_growth > 30:
                parts.append(tr(u"laatste uitvoer {0} geleden",
                                u"last output {0} ago").format(
                    _duration(time.time() - src.last_growth)))
        if data.modes:
            parts.append(tr(u"modes {0}", u"modes {0}").format(
                bc.modes_text(data)))
        if data.partial_until is not None:
            parts.append(tr(u"ONVOLLEDIG: resultaten tot t = {0} s",
                            u"INCOMPLETE: results up to t = {0} s").format(
                data.partial_until))
        self.lbl_status.configure(text=u"   |   ".join(parts))
        self.lbl_source.configure(text=src.describe())

    # ---------- linear analysis (MECA_STATIQUE) ----------
    def _build_linear(self, grid):
        """Cards for MECA_STATIQUE; they sit in the same 2x2 grid
        as the plots and are only shown in linear mode."""
        self.k_system = Card(grid, tr(u"(a) Stelsel en oplosser",
                                      u"(a) System and solver"))
        self.k_time = Card(grid, tr(u"(b) Tijdverloop per fase",
                                    u"(b) Time per phase"))
        self.k_quality = Card(grid, tr(u"(c) Kwaliteit van de oplossing",
                                       u"(c) Quality of the solution"))
        self.p_gcpc = Plot(grid, tr(u"(c) Residu per GCPC-iteratie",
                                    u"(c) Residual per GCPC iteration"))
        self.k_assess = Card(grid, tr(u"(d) Beoordeling",
                                      u"(d) Assessment"))
        self._nl_widgets = [(self.p_resi.c, 0, 0), (self.p_prog.c, 0, 1),
                            (self.p_cont.c, 1, 0), (self.p_newt.c, 1, 1)]
        self._mode_key = None

    def _set_mode(self, mode, gcpc=False):
        """Switch between the nonlinear plots and the linear cards
        (and between the quality card and the GCPC plot)."""
        key = (mode, gcpc)
        if self._mode_key == key:
            return
        self._mode_key = key
        for w in (self.k_system.c, self.k_time.c, self.k_quality.c,
                  self.p_gcpc.c, self.k_assess.c):
            w.grid_remove()
        for w, _r, _c in self._nl_widgets:
            w.grid_remove()
        if mode == "linear":
            shown = [(self.k_system.c, 0, 0), (self.k_time.c, 0, 1),
                     ((self.p_gcpc.c if gcpc else self.k_quality.c), 1, 0),
                     (self.k_assess.c, 1, 1)]
        else:
            shown = self._nl_widgets
        for w, r, col in shown:
            w.grid(row=r, column=col, sticky="nsew", padx=2, pady=2)
        if mode == "linear":
            # No solve attempts: slider and attempt details hidden.
            self.ctl.pack_forget()
            self.lbl_step.pack_forget()
        else:
            self.ctl.pack(side="top", fill="x", padx=6, before=self.frm_msgs)
            self.lbl_step.pack(side="top", fill="x", padx=6, pady=(2, 2),
                               before=self.frm_msgs)

    def _draw_linear(self, lin):
        gcpc = lin.method() == "GCPC"
        self._set_mode("linear", gcpc)
        self.k_system.draw(
            lambda c, w, h, y: self._lin_system(c, w, h, y, lin))
        self.k_time.draw(
            lambda c, w, h, y: self._lin_time(c, w, h, y, lin))
        if gcpc:
            self._lin_gcpc_plot(lin)
        else:
            self.k_quality.draw(
                lambda c, w, h, y: self._lin_quality(c, w, h, y, lin))
        self.k_assess.draw(
            lambda c, w, h, y: self._lin_assess(c, w, h, y, lin))

    def _lin_system(self, c, w, h, y, lin):
        s = lin.solver
        mu = lin.mumps
        method = lin.method()
        if method == "MUMPS":
            desc = u"MUMPS {0}".format(mu.get("version", u"")).strip()
            desc += tr(u" (direct, LDLᵀ)", u" (direct, LDLᵀ)")
            if mu.get("ordering"):
                desc += tr(u", ordening {0}", u", ordering {0}").format(
                    mu["ordering"])
        elif method == "GCPC":
            desc = tr(u"GCPC (iteratief, voorconditionering {0})",
                      u"GCPC (iterative, preconditioner {0})").format(
                s.get("PRE_COND", u"LDLT_INC"))
        else:
            desc = method
        rows = [(tr(u"Oplosser", u"Solver"), desc, None)]
        eq = _int(lin.equations or lin.dofs)
        if lin.dofs_phys is not None:
            eq += tr(u"  ({0} fysiek", u"  ({0} physical").format(
                _int(lin.dofs_phys))
            if lin.lagr_pairs:
                eq += tr(u", {0} Lagrange voor {1} relaties",
                         u", {0} Lagrange for {1} relations").format(
                    _int(lin.lagr_pairs), _int(lin.relations))
            eq += u")"
        rows.append((tr(u"Vergelijkingen", u"Equations"), eq, None))
        if lin.nodes is not None:
            rows.append((tr(u"Knopen", u"Nodes"), _int(lin.nodes), None))
        if lin.nnz is not None:
            rows.append((tr(u"Niet-nul-termen matrix",
                            u"Non-zero terms matrix"),
                         tr(u"{0}  (vulling {1:.3g} %)",
                            u"{0}  (fill {1:.3g} %)").format(
                             _int(lin.nnz), lin.fill_pct or 0.0), None))
        if mu.get("entries") is not None:
            rows.append((tr(u"Termen in de factoren",
                            u"Entries in the factors"),
                         tr(u"{0}  (grootste front {1})",
                            u"{0}  (largest front {1})").format(
                             _int(mu["entries"]), _int(mu.get("front"))),
                         None))
        elif mu.get("entries_est") is not None:
            rows.append((tr(u"Termen in de factoren",
                            u"Entries in the factors"),
                         tr(u"{0}  (schatting)", u"{0}  (estimate)").format(
                             _int(mu["entries_est"])), _C_LABEL))
        if mu.get("flops") is not None:
            rows.append((tr(u"Werk factorisatie", u"Factorization work"),
                         u"{0} flop".format(_sci(mu["flops"])), None))
        if mu.get("mem_alloc") is not None:
            rows.append((tr(u"Geheugen MUMPS", u"MUMPS memory"),
                         tr(u"{0} MB gereserveerd, {1} MB gebruikt",
                            u"{0} MB allocated, {1} MB used").format(
                             _int(mu["mem_alloc"]), _int(mu.get("mem_used"))),
                         None))
        elif mu.get("mem_est") is not None:
            rows.append((tr(u"Geheugen MUMPS", u"MUMPS memory"),
                         tr(u"{0} MB (schatting)", u"{0} MB (estimate)"
                            ).format(_int(mu["mem_est"])), _C_LABEL))
        if mu.get("neg_pivots") is not None:
            neg = mu["neg_pivots"]
            extra = lin.lagr_pairs is not None and neg > lin.lagr_pairs
            rows.append((tr(u"Pivots", u"Pivots"),
                         tr(u"{0} negatief (verwacht {1}: Lagrange), {2} "
                            u"uitgesteld",
                            u"{0} negative (expected {1}: Lagrange), {2} "
                            u"delayed").format(
                             _int(neg), _int(lin.lagr_pairs or 0),
                             _int(mu.get("delayed", 0))),
                         _C_ORANGE if (mu.get("delayed") or extra)
                         else None))
        crit = []
        if s.get("RESI_RELA") is not None:
            crit.append(u"RESI_RELA {0:g}".format(s["RESI_RELA"]))
        if method == "MUMPS" and s.get("NPREC") is not None:
            crit.append(u"NPREC {0}".format(s["NPREC"]))
        if method == "GCPC":
            nmax = s.get("NMAX_ITER")
            if nmax == 0 and lin.equations:
                crit.append(tr(u"max. {0} iteraties (vergelijkingen / 2)",
                               u"max. {0} iterations (equations / 2)").format(
                    _int(lin.equations // 2)))
            elif nmax:
                crit.append(u"NMAX_ITER {0}".format(nmax))
        if crit:
            rows.append((tr(u"Criteria", u"Criteria"), u", ".join(crit),
                         None))
        if method == "GCPC" and lin.gcpc_init is not None:
            rows.append((tr(u"Beginresidu ||f||", u"Initial residual ||f||"),
                         _sci(lin.gcpc_init), None))
        if method == "GCPC" and lin.gcpc_converged is not None:
            rows.append((tr(u"Iteraties", u"Iterations"),
                         tr(u"{0}  (eindresidu {1})",
                            u"{0}  (final residual {1})").format(
                             _int(lin.gcpc_converged),
                             _sci(lin.gcpc_final[2] if lin.gcpc_final
                                  else None)), _C_GREEN))
        y = _rows(c, 10, y + 4, w, rows, label_w=min(175, int(w * 0.36)))
        if not lin.detailed:
            c.create_text(10, y + 6, anchor="nw", width=w - 20,
                          font=_FONT, fill=_C_MUTED, text=tr(
                              u"Geen statistiek van de oplosser in deze "
                              u".mess (INFO=1, oudere run). Een nieuwe run "
                              u"via de bridge schrijft die wel (INFO=2).",
                              u"No solver statistics in this .mess (INFO=1, "
                              u"older run). A new run via the bridge writes "
                              u"them (INFO=2)."))

    def _lin_time(self, c, w, h, y, lin):
        now = time.time() if self.source.kind == "fort6" else None
        keys = lin.phase_keys()
        secs = dict((k, lin.phase_seconds(k, now)) for k in keys)
        known = [v for v in secs.values() if v is not None]
        vmax = max(known + [1e-3])
        label_w = min(250, int(w * 0.42))
        x0, x1 = 10 + label_w, w - 84
        y += 12
        dy = max(22, min(34, int((h - y - 60) / max(1, len(keys)))))
        for k in keys:
            ph = lin.phases.get(k)
            running = (k == lin.current and not lin.finished())
            failed = (lin.status == "mislukt" and ph is not None and
                      ph.get("end") is None and ph.get("seconds") is None)
            color = (_C_BLUE if running else _C_RED if failed else
                     _C_GREEN if ph is not None else _C_MUTED)
            c.create_text(10, y, anchor="w", font=_FONT,
                          text=bc.lin_phase_title(k, lin.method()),
                          fill=_C_TEXT if ph is not None else _C_MUTED)
            c.create_rectangle(x0, y - 7, x1, y + 7, fill="#f2f2f2",
                               outline="")
            v = secs[k]
            if v is not None and x1 > x0:
                xe = x0 + max(2.0, (x1 - x0) * v / vmax)
                c.create_rectangle(x0, y - 7, xe, y + 7, fill=color,
                                   outline="")
            if running:
                txt = tr(u"bezig {0}", u"running {0}").format(_secs(v))
            elif ph is None:
                txt = tr(u"wacht", u"waiting") if not lin.finished() \
                    else u"-"
            else:
                txt = _secs(v)
            c.create_text(x1 + 6, y, anchor="w", text=txt, font=_FONT,
                          fill=color if (running or failed) else _C_TEXT)
            y += dy
        foot = tr(u"Som van de fasen: {0}", u"Sum of the phases: {0}").format(
            _secs(sum(known)))
        if lin.cpu_total is not None:
            foot += tr(u"   |   CPU-tijd MECA_STATIQUE: {0}",
                       u"   |   CPU time MECA_STATIQUE: {0}").format(
                _secs(lin.cpu_total))
        if not lin.finished() and lin.started_at is not None:
            foot += tr(u"   |   sinds de start: {0}",
                       u"   |   since the start: {0}").format(
                _secs(time.time() - lin.started_at))
        c.create_text(10, y, anchor="nw", text=foot, font=_FONT,
                      fill=_C_LABEL, width=w - 20)
        if (lin.method() == "MUMPS" and lin.current == "factor" and
                not lin.finished() and lin.mumps.get("flops")):
            c.create_text(10, y + 20, anchor="nw", font=_FONT_SMALL,
                          fill=_C_MUTED, width=w - 20, text=tr(
                              u"MUMPS meldt de factorisatie pas als die klaar "
                              u"is; geschat werk {0} flop.",
                              u"MUMPS reports the factorization only when it "
                              u"is done; estimated work {0} flop.").format(
                              _sci(lin.mumps["flops"])))

    def _lin_quality(self, c, w, h, y, lin):
        after = lin.refine_after or lin.refine_before
        if not after:
            text = (tr(u"Nog geen foutanalyse; MUMPS schrijft die na het "
                       u"oplossen.",
                       u"No error analysis yet; MUMPS writes it after the "
                       u"solve.") if not lin.finished() else
                    tr(u"Geen foutanalyse in de uitvoer (RESI_RELA < 0, "
                       u"POSTTRAITEMENTS='SANS' of INFO=1).",
                       u"No error analysis in the output (RESI_RELA < 0, "
                       u"POSTTRAITEMENTS='SANS' or INFO=1)."))
            c.create_text(10, y + 6, anchor="nw", width=w - 20, text=text,
                          font=_FONT, fill=_C_MUTED)
            return
        resi = lin.solver.get("RESI_RELA")
        err = after.get(9)
        err_col = _C_RED if (err is not None and resi and resi > 0 and
                             err > resi) else _C_GREEN
        y = _log_strip(
            c, 10, w, y + 4,
            tr(u"Fout en residu (relatief)", u"Error and residual (relative)"),
            [(tr(u"Geschaald residu", u"Scaled residual"), after.get(6),
              _C_INFO),
             (u"Backward error ω₁", after.get(7), _C_INFO),
             (u"Backward error ω₂", after.get(8), _C_INFO),
             (tr(u"Foutgrens oplossing", u"Solution error bound"), err,
              err_col)],
            -18, 0,
            lines=[(resi, _C_RED, u"RESI_RELA {0:g}".format(resi))]
            if resi and resi > 0 else [])
        cond1 = after.get(10)
        y = _log_strip(
            c, 10, w, y + 6,
            tr(u"Conditiegetal", u"Condition number"),
            [(tr(u"Conditie (1)", u"Condition (1)"), cond1,
              _C_ORANGE if (cond1 or 0) > 1e12 else _C_BLUE),
             (tr(u"Conditie (2)", u"Condition (2)"), after.get(11), _C_BLUE)],
            0, 20, zones=[(0, 4, "#e8f5e9"), (12, 20, "#fff3e0")], step=4)
        steps = lin.refine_steps
        foot = tr(u"Residu (max-norm) {0} voor en {1} na iteratieve "
                  u"verfijning ({2} stap(pen)). Foutgrens = conditie x "
                  u"backward error (MUMPS RINFOG 6-11).",
                  u"Residual (max norm) {0} before and {1} after iterative "
                  u"refinement ({2} step(s)). Error bound = condition x "
                  u"backward error (MUMPS RINFOG 6-11).").format(
            _sci(lin.refine_before.get("resid")),
            _sci(lin.refine_after.get("resid")),
            steps if steps is not None else u"-")
        c.create_text(10, y, anchor="nw", width=w - 20, text=foot,
                      font=_FONT_SMALL, fill=_C_LABEL)

    def _lin_gcpc_plot(self, lin):
        pts = []
        if lin.gcpc_init is not None:
            pts.append((0, 1.0))
        pts += [(n, rel) for n, _a, rel in lin.gcpc_iters]
        if lin.gcpc_converged is not None and lin.gcpc_final:
            pts.append((lin.gcpc_converged, lin.gcpc_final[2]))
        resi = lin.solver.get("RESI_RELA")
        if lin.gcpc_target:
            resi = lin.gcpc_target[1]
        # Staircase: Code-Aster only writes the first iteration at which the
        # residual drops below 1/10 of the previously written value
        # (gcpc.F90); in between the residual was above it.
        self.p_gcpc.set(
            series=[{"points": pts, "color": _C_BLUE, "kind": "step"},
                    {"name": tr(u"relatief residu ||r|| / ||f||",
                                u"relative residual ||r|| / ||f||"),
                     "points": pts, "color": _C_BLUE, "kind": "markers"}],
            ylog_left=True,
            hlines=[(resi, _C_RED, u"RESI_RELA {0:g}".format(resi))]
            if resi else [],
            xlabel=tr(u"GCPC-iteratie (Code-Aster schrijft een iteratie "
                      u"zodra het residu 10x gedaald is)",
                      u"GCPC iteration (Code-Aster writes an iteration once "
                      u"the residual has dropped 10x)"),
            ylabel=tr(u"relatief residu", u"relative residual"),
            empty=tr(u"Nog geen GCPC-iteraties", u"No GCPC iterations yet"))

    def _lin_assess(self, c, w, h, y, lin):
        items = bc.assess_linear(lin)
        if not lin.finished():
            items.insert(0, ("info", tr(
                u"Code-Aster rekent nog; de beoordeling volgt na het "
                u"oplossen.",
                u"Code-Aster is still computing; the assessment follows "
                u"after the solve.")))
        if not items:
            items = [("info", tr(u"Geen gegevens", u"No data"))]
        y += 8
        for level, text in items:
            color = _LEVEL_COLORS.get(level, _C_INFO)
            c.create_oval(12, y + 3, 22, y + 13, fill=color, outline=color)
            t = c.create_text(32, y, anchor="nw", width=w - 44, text=text,
                              font=_FONT, fill=_C_TEXT)
            bbox = c.bbox(t)
            y = (bbox[3] if bbox else y + 16) + 8
        if lin.method() == "GCPC":
            notes = [tr(u"Residu ||r|| / ||f||: hoeveel van de belasting "
                        u"nog niet in evenwicht is; GCPC stopt onder "
                        u"RESI_RELA.",
                        u"Residual ||r|| / ||f||: how much of the load is "
                        u"not yet in equilibrium; GCPC stops below "
                        u"RESI_RELA."),
                     tr(u"Een vlak stuk in de grafiek = trage convergentie "
                        u"(slank of slecht geconditioneerd model).",
                        u"A flat part in the plot = slow convergence "
                        u"(slender or poorly conditioned model).")]
        else:
            notes = [tr(u"Foutgrens: geschatte relatieve fout in de "
                        u"verplaatsingen = conditie x backward error; moet "
                        u"onder RESI_RELA blijven.",
                        u"Error bound: estimated relative error in the "
                        u"displacements = condition x backward error; must "
                        u"stay below RESI_RELA."),
                     tr(u"Conditiegetal: gevoeligheid voor afrondfouten; "
                        u"groot bij een slecht vastgehouden deel of grote "
                        u"stijfheidsverschillen.",
                        u"Condition number: sensitivity to rounding errors; "
                        u"large for a poorly held part or large stiffness "
                        u"differences."),
                     tr(u"Backward error: hoe goed de factorisatie het "
                        u"stelsel oplost; normaal ~1e-15.",
                        u"Backward error: how well the factorization solves "
                        u"the system; normally ~1e-15.")]
        y += 6
        c.create_text(10, y, anchor="nw", font=_FONT_VALUE, fill=_C_LABEL,
                      text=tr(u"Wat betekenen de getallen?",
                              u"What do the numbers mean?"))
        y += 20
        for note in notes:
            t = c.create_text(14, y, anchor="nw", width=w - 30, text=note,
                              font=_FONT_SMALL, fill=_C_LABEL)
            bbox = c.bbox(t)
            y = (bbox[3] if bbox else y + 14) + 4
        c.create_text(10, h - 6, anchor="sw", width=w - 20, font=_FONT_SMALL,
                      fill=_C_MUTED, text=tr(
                          u"Bron: Code-Aster U2.08.03 (lineaire oplossers) "
                          u"en U4.50.01 (SOLVEUR); uitleg in de "
                          u"documentatie (Instellingen contact en "
                          u"niet-lineair).",
                          u"Source: Code-Aster U2.08.03 (linear solvers) and "
                          u"U4.50.01 (SOLVEUR); explained in the "
                          u"documentation (Settings contact and "
                          u"nonlinear)."))

    def _iter_points(self, window):
        """x position per iteration (continuous) and separator lines."""
        out = []
        vlines = []
        x = 0
        for step in window:
            color = _STATUS_COLORS.get(step.status, "#555555")
            # Keep the label short: attempt and level (the time is in the
            # details below the plots).
            vlines.append((x + 0.5, color, u"#{0} n{1}".format(
                step.index + 1, step.level), (2, 2)))
            prev_geom = None
            for it in step.iterations:
                x += 1
                g = it.get("geom")
                if prev_geom is not None and g is not None and g != prev_geom:
                    vlines.append((x - 0.5, "#9e9e9e", u"G{0:.0f}".format(g),
                                   (1, 3)))
                prev_geom = g
                out.append((x, step, it))
            out.append(None)      # break between attempts
        return out, vlines

    def _draw_resi(self, data):
        window = self._window(data)
        pts, vlines = self._iter_points(window)

        def series(key):
            return [None if p is None else (p[0], p[2].get(key))
                    for p in pts]
        crit = self._criterion(data)
        self.p_resi.set(
            series=[
                {"name": tr(u"RESI_GLOB_RELA (links)",
                            u"RESI_GLOB_RELA (left)"), "points":
                 series("resi_rela"), "color": "#1565c0",
                 "kind": "linemarkers"},
                {"name": tr(u"RESI_GLOB_MAXI [N] (rechts)",
                            u"RESI_GLOB_MAXI [N] (right)"), "points":
                 series("resi_maxi"), "color": "#ef6c00", "kind": "line",
                 "axis": "right", "width": 1},
            ],
            ylog_left=True, ylog_right=True,
            hlines=[(crit, "#c62828", tr(u"criterium {0:g}",
                                         u"criterion {0:g}").format(crit))]
            if crit else [],
            vlines=vlines, xlabel=tr(u"Newton-iteratie (doorlopend over de "
                                     u"getoonde pogingen)",
                                     u"Newton iteration (continuous over "
                                     u"the attempts shown)"),
            ylabel=tr(u"relatief residu", u"relative residual"),
            ylabel_right=tr(u"max. residu", u"max. residual"),
            empty=tr(u"Nog geen Newton-iteraties",
                     u"No Newton iterations yet") if (data.command or
                                                      data.steps) and not
            data.explicit else tr(u"Geen convergentietabel: lineaire of "
                               u"expliciete analyse (meldingen staan "
                               u"hieronder)",
                               u"No convergence table: linear or explicit "
                               u"analysis (messages are shown below)"))

    def _draw_progress(self, data):
        steps = data.steps
        if steps:
            pts = [(s.index + 1, s.instant) for s in steps]
            cols = [_STATUS_COLORS.get(s.status, "#555555") for s in steps]
            conv = [(s.index + 1, s.instant) for s in steps
                    if s.status == "geconvergeerd"]
            lvl = [(s.index + 1, s.level) for s in steps]
            sel = [(self.sel + 1, "#000000", u"", (3, 2))] \
                if self.sel is not None else []
            self.p_prog.set(
                series=[
                    {"name": tr(u"geconvergeerd", u"converged"),
                     "points": conv,
                     "color": "#2e7d32", "kind": "line", "width": 1},
                    {"name": tr(u"poging (groen ok, rood mislukt)",
                                u"attempt (green ok, red failed)"),
                     "points": pts, "colors": cols, "color": "#c62828",
                     "kind": "markers"},
                    {"name": tr(u"niveau van opdeling (rechts)",
                                u"subdivision level (right)"),
                     "points": lvl,
                     "color": "#9e9e9e", "kind": "step", "axis": "right",
                     "width": 1},
                ],
                vlines=sel, xlabel=tr(u"rekenpoging (klik = selecteren)",
                                      u"solver attempt (click = select)"),
                ylabel=tr(u"tijdstip [s]", u"time [s]"),
                ylabel_right=tr(u"niveau", u"level"))
        else:
            pts = [(i + 1, p[1]) for i, p in enumerate(data.progress)]
            self.p_prog.set(
                series=[{"name": tr(u"berekend tijdstip", u"computed time"),
                         "points": pts,
                         "color": "#1565c0", "kind": "line"}],
                xlabel=tr(u"uitvoerregel", u"output line"),
                ylabel=tr(u"tijdstip [s]", u"time [s]"),
                empty=tr(u"Nog geen tijdstappen", u"No time steps yet"))

    def _draw_newton(self, data):
        steps = data.steps
        pts = [(s.index + 1, s.newton_count()) for s in steps]
        cols = [_STATUS_COLORS.get(s.status, "#555555") for s in steps]
        geom = [(s.index + 1, s.geom_loops()) for s in steps
                if s.geom_loops() is not None]
        series = [{"name": tr(u"Newton-iteraties", u"Newton iterations"),
                   "points": pts,
                   "colors": cols, "color": "#2e7d32", "kind": "bars"}]
        if geom:
            series.append({"name": tr(u"geom. contactlussen (rechts)",
                                      u"geom. contact loops (right)"),
                           "points": geom, "color": "#000000",
                           "kind": "markers", "axis": "right", "size": 2})
        iter_max = data.iter_max or self.args.iter_max
        sel = [(self.sel + 1, "#000000", u"", (3, 2))] \
            if self.sel is not None else []
        self.p_newt.set(
            series=series,
            hlines=[(iter_max, "#c62828", u"ITER_GLOB_MAXI {0}".format(
                iter_max))] if iter_max else [],
            vlines=sel, xlabel=tr(u"rekenpoging (klik = selecteren)",
                                  u"solver attempt (click = select)"),
            ylabel=tr(u"iteraties", u"iterations"),
            ylabel_right=tr(u"lussen", u"loops"),
            empty=tr(u"Nog geen tijdstappen", u"No time steps yet"))

    def _draw_contact(self, data):
        window = self._window(data)
        pts, vlines = self._iter_points(window)
        has_contact = any(p is not None and (
            p[2].get("cont_press") is not None or
            p[2].get("cont_vari") is not None or
            p[2].get("cont_crit") is not None) for p in pts)
        if has_contact:
            def series(key):
                return [None if p is None else (p[0], p[2].get(key))
                        for p in pts]
            crit = [p for p in series("cont_crit") if p is not None and
                    p[1] is not None]
            vari = [p for p in series("cont_vari") if p is not None]
            self.p_cont.title = tr(u"(d) Contact per Newton-iteratie",
                                   u"(d) Contact per Newton iteration")
            self.p_cont.set(
                series=[
                    {"name": tr(u"statuswisselingen (rechts)",
                                u"status changes (right)"), "points": vari,
                     "color": "#b0bec5", "kind": "bars", "axis": "right"},
                    {"name": u"PRESSURE ERROR", "points":
                     series("cont_press"), "color": "#6a1b9a",
                     "kind": "linemarkers"},
                    {"name": tr(u"CRITERE VALEUR (einde geom. lus)",
                                u"CRITERE VALEUR (end of geom. loop)"),
                     "points": crit, "color": "#2e7d32", "kind": "markers",
                     "size": 5},
                ],
                ylog_left=True, vlines=vlines,
                xlabel=tr(u"Newton-iteratie (G2, G3 = nieuwe geometrische "
                          u"lus)",
                          u"Newton iteration (G2, G3 = new geometric "
                          u"loop)"),
                ylabel=tr(u"fout / criterium", u"error / criterion"),
                ylabel_right=tr(u"wisselingen", u"changes"))
            return
        energy = [s for s in data.steps if s.energy]
        if energy:
            names = []
            for s in energy:
                for k in s.energy:
                    if k not in names:
                        names.append(k)
            colors = ["#1565c0", "#c62828", "#2e7d32", "#ef6c00", "#6a1b9a",
                      "#455a64"]
            self.p_cont.title = tr(u"(d) Energiebalans (TOTAL, ENERGIE)",
                                   u"(d) Energy balance (TOTAL, ENERGIE)")
            self.p_cont.set(
                series=[{"name": k, "points": [(s.index + 1, s.energy.get(k))
                                               for s in energy],
                         "color": colors[i % len(colors)], "kind": "line"}
                        for i, k in enumerate(names)],
                xlabel=tr(u"rekenpoging", u"solver attempt"),
                ylabel=tr(u"energie [J]", u"energy [J]"))
            return
        self.p_cont.title = tr(u"(d) Contact per Newton-iteratie",
                               u"(d) Contact per Newton iteration")
        self.p_cont.set(series=[], empty=tr(
            u"Geen contactkolommen in de convergentietabel (geen contact in "
            u"dit model)",
            u"No contact columns in the convergence table (no contact in "
            u"this model)"))

    def _draw_step(self, data):
        if self.sel is None or not data.steps:
            self.lbl_step.configure(text=u"")
            return
        s = data.steps[self.sel]
        rows = [tr(u"Poging {0}: t = {1:.6g} s, niveau {2}, {3}{4}",
                   u"Attempt {0}: t = {1:.6g} s, level {2}, {3}{4}").format(
            s.index + 1, s.instant, s.level, _status_text(s.status),
            u" ({0})".format(s.error) if s.error else u"")]
        info = [u"Newton {0}".format(s.newton_count())]
        if s.geom_loops() is not None:
            info.append(tr(u"geom. lussen {0}", u"geom. loops {0}").format(
                s.geom_loops()))
        if s.summary.get("contact_links") is not None:
            info.append(tr(u"contactliaisons {0:.0f}",
                           u"contact links {0:.0f}").format(
                s.summary["contact_links"]))
        if s.status_changes() is not None:
            info.append(tr(u"statuswisselingen {0}",
                           u"status changes {0}").format(s.status_changes()))
        cyc = [(k, v) for k, v in s.summary.items()
               if k.startswith("cycles_") and v]
        if cyc:
            info.append(tr(u"cycli ", u"cycles ") + u", ".join(
                u"{0}={1:.0f}".format(k[7:], v) for k, v in cyc))
        if s.contact_initial:
            info.append(tr(u"begin: {0} in contact, {1} uitgesloten",
                           u"start: {0} in contact, {1} excluded").format(
                *s.contact_initial))
        if s.resi_location:
            info.append(tr(u"grootste residu: {0}",
                           u"largest residual: {0}").format(s.resi_location))
        if s.cpu is not None:
            info.append(u"CPU {0:g} s".format(s.cpu))
        if s.iterations:
            last = s.iterations[-1]
            if last.get("resi_rela") is not None:
                info.append(tr(u"laatste RESI_GLOB_RELA {0:.3e}",
                               u"last RESI_GLOB_RELA {0:.3e}").format(
                    last["resi_rela"]))
        rows.append(u"  " + u" | ".join(info))
        if s.energy:
            rows.append(tr(u"  energie: ", u"  energy: ") + u", ".join(
                u"{0}={1:.4g}".format(k, v) for k, v in s.energy.items()
                if v is not None))
        self.lbl_step.configure(text=u"\n".join(rows))

    def _draw_messages(self, data):
        state = (tuple((m.get("seq"), m["count"]) for m in data.messages),
                 len(self.console.errors))
        if state == self._msg_state:
            return
        self._msg_state = state
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        for m in sorted(data.messages, key=lambda m: m.get("seq", 0)):
            where = u""
            if m.get("step") is not None:
                where = tr(u"[poging {0}, t = {1:.6g} s] ",
                           u"[attempt {0}, t = {1:.6g} s] ").format(
                    m["step"] + 1, m["instant"])
            label = {"fout": tr(u"FOUT", u"ERROR"), "alarm": u"ALARM",
                     "actie": tr(u"actie", u"action")}.get(m["kind"],
                                                           m["kind"])
            code = m["code"] if m["code"] not in (u"PIVOT", u"") else u""
            text = m["text"]
            if len(text) > 300:
                text = text[:300] + u" ..."
            line = u"{0}{1}{2}{3}: {4}\n".format(
                where, label, u" " + code if code else u"",
                u" ({0}x)".format(m["count"]) if m["count"] > 1 else u"",
                text)
            self.txt.insert("end", line, m["kind"])
            if m.get("hint"):
                self.txt.insert("end", u"-> " + m["hint"] + u"\n", "hint")
        for err in self.console.errors:
            self.txt.insert("end", self._names(tr(
                u"FOUT Python in study.comm: {0}\n",
                u"ERROR Python in study.comm: {0}\n")).format(err), "fout")
            self.txt.insert("end", self._names(tr(
                u"-> study.comm is niet (volledig) uitgevoerd; een fout in "
                u"#ASTER-regels? Zie het Code-Aster-venster of "
                u"study_console.txt.\n",
                u"-> study.comm was not (fully) executed; an error in "
                u"#ASTER lines? See the Code-Aster window or "
                u"study_console.txt.\n")), "hint")
        self.txt.see("end")
        self.txt.configure(state="disabled")


def _run_file(mess_path, suffix):
    """File of the same run as mess_path: <model>_<run_id>.mess ->
    <model>_<run_id><suffix> (e.g. ".comm", "_console.txt")."""
    return os.path.splitext(mess_path)[0] + suffix


def _duration(sec):
    sec = int(max(0, sec))
    if sec < 60:
        return u"{0} s".format(sec)
    if sec < 3600:
        return u"{0} min {1:02d} s".format(sec // 60, sec % 60)
    return u"{0} h {1:02d} min".format(sec // 3600, (sec % 3600) // 60)


def main(argv=None):
    global _LOG_PATH
    ap = argparse.ArgumentParser(description=u"Convergentiescherm Code-Aster")
    ap.add_argument("--mess", required=True,
                    help=u".mess-bestand van de run (uit de .export)")
    ap.add_argument("--since", type=float, default=0.0,
                    help=u"starttijd van de run (time.time()); 0 = achteraf")
    ap.add_argument("--resi", type=float, default=None,
                    help=u"RESI_GLOB_RELA als het niet in de uitvoer staat")
    ap.add_argument("--iter-max", dest="iter_max", type=int, default=None)
    ap.add_argument("--log", default=None, help=u"logbestand")
    ap.add_argument("--console", default=None,
                    help=u"<model>_<run>_console.txt (Python-fouten in "
                         u"<model>_<run>.comm)")
    ap.add_argument("--exit-after-finish", dest="exit_after_finish",
                    type=float, default=None,
                    help=u"sluit N s nadat de run klaar is (voor tests)")
    ap.add_argument("--lang", choices=("nl", "en"), default=None,
                    help=u"taal van het scherm; standaard die uit "
                         u"bridge_utils.CONFIG_BRIDGE")
    ap.add_argument("--paraview", default=None,
                    help=u"paraview.exe voor de knop ParaView; standaard "
                         u"bridge_utils.paraview_exe_path()")
    args = ap.parse_args(argv)
    if args.lang:
        bridge_utils.CONFIG_BRIDGE["language"] = args.lang
    _LOG_PATH = args.log
    if args.log:
        try:     # pythonw has no console: errors to the log file
            sys.stderr = open(args.log, "a", encoding="utf-8")
        except Exception:
            pass
    log(u"INFO: convergence window started (pid {0}, Python {1})".format(
        os.getpid(), sys.version.split()[0]))
    if tk is None:
        log(tr("ERROR: tkinter ontbreekt in deze Python.",
               "ERROR: tkinter is missing in this Python."))
        return 1
    try:   # sharp text on screens with a scale factor
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        root = tk.Tk()
        Monitor(root, args)
        root.mainloop()
    except Exception:
        log("ERROR: " + traceback.format_exc())
        return 1
    log("INFO: convergence window closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
