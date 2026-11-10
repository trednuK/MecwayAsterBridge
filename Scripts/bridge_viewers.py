# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_viewers.py
# Open the result files of a run outside Mecway: plain ParaView (the .pvd of
# vtu_export or a .rmed of med_export) and Salome-Meca's AsterStudy, tab
# Results (a .rmed). Used by the buttons "ParaView" and "AsterStudy" of the
# Results dialog (bridge_gui.results_dialog, IronPython 2.7.9 in Mecway) and
# of the convergence window (aster_convergence_monitor, Code-Aster's
# CPython 3). Works in both: standard library only, no mw.
#
# Pieces:
#   Salome search   salome_bases(), salome_dirs(), find_salome(): one search
#                   for both buttons. A root for AsterStudy has
#                   run_salome.bat, the launcher "salome" and W64\ASTERSTUDY;
#                   a root for ParaView has run_paraview.bat and
#                   W64\ParaView\bin\paraview.exe. Setting salome_meca_dir
#                   ("" = automatic).
#   ParaView        paraview_exe(): setting paraview_exe, else an official
#                   ParaView (%ProgramFiles%\ParaView*) or Salome's.
#   Files of a run  result_files(), choose_file().
#   Start           open_paraview(), open_asterstudy(): (ok, text).
#
# AsterStudy route (session script, launcher command line, environment):
# verified with Salome-Meca 2025 (SALOME 9.15, AsterStudy 0.11) started
# from CPython on 24 Oct 2026; started from IronPython (Mecway) NOT verified.
# showResultsFile is AsterStudy's call behind its menu "Post-process an
# external MED Results File" (asterstudy/gui/salomegui.py) and may change
# with the AsterStudy version.

import glob
import io
import os
import re
import subprocess
import time

import bridge_utils
from bridge_utils import tr, expand_path

CREATE_NO_WINDOW = 0x08000000

# cmd.exe parses the arguments of a .bat again; Python does not escape these
# characters for it, so a path with one of them is refused (no launch).
CMD_UNSAFE = u'%&^!"<>|'

# A second AsterStudy click within this many seconds of the last write of the
# session log only gives a message: Salome-Meca takes a while to start.
SALOME_BUSY_SECONDS = 60

# Result files of a run, in the order the buttons prefer them: the refined
# mesh of HOMARD and the mesh that follows an XFEM crack are what the user
# wants to see when they exist.
_SUFFIXES = (("verfijnd", "_verfijnd.rmed"), ("xfem", "_xfem.rmed"),
             ("pvd", ".pvd"), ("rmed", ".rmed"))


# ------------------------------------------------------------------ Salome

def salome_bases(environ=None):
    """Folders that hold Salome-Meca installations (or are one)."""
    env = os.environ if environ is None else environ
    drive = env.get("SystemDrive", "C:") + os.sep
    bases = [os.path.join(drive, "SALOME-MECA"),
             os.path.join(drive, "Salome_meca")]
    pf = env.get("ProgramFiles")
    if pf:
        bases.extend(sorted(glob.glob(os.path.join(pf, "SALOME*"))))
        bases.extend(sorted(glob.glob(os.path.join(pf, "Salome*"))))
    out = []
    for b in bases:
        if os.path.normcase(b) not in [os.path.normcase(x) for x in out]:
            out.append(b)
    return out


def is_salome_root(path):
    """True for a Salome-Meca root that can run AsterStudy."""
    return bool(path) and os.path.isfile(
        os.path.join(path, "run_salome.bat")) and os.path.isfile(
        os.path.join(path, "salome")) and os.path.isdir(
        os.path.join(path, "W64", "ASTERSTUDY"))


def salome_paraview(path):
    """<path>/run_paraview.bat when path is a Salome root with its own
    ParaView, else "". Salome's paraview.exe only starts in Salome's
    environment (on its own: "Qt5Widgets.dll not found", Salome-Meca
    v2025); run_paraview.bat sets it and passes the arguments on."""
    bat = os.path.join(path or "", "run_paraview.bat")
    exe = os.path.join(path or "", "W64", "ParaView", "bin", "paraview.exe")
    return bat if path and os.path.isfile(bat) and os.path.isfile(exe) \
        else ""


def salome_dirs(bases):
    """Every base and every folder directly in it (candidate roots)."""
    found = []
    for base in bases:
        if not os.path.isdir(base):
            continue
        try:
            names = sorted(os.listdir(base))
        except OSError:
            names = []
        for c in [base] + [os.path.join(base, n) for n in names]:
            if os.path.isdir(c) and os.path.normcase(c) not in \
                    [os.path.normcase(x) for x in found]:
                found.append(c)
    return found


def _grep(path, pattern):
    """First group of pattern in a text file, or None (never raises)."""
    try:
        f = io.open(path, "r", encoding="utf-8", errors="replace")
        try:
            m = re.search(pattern, f.read(), re.M)
        finally:
            f.close()
        return m.group(1) if m else None
    except (IOError, OSError):
        return None


def salome_version(root):
    """Version text of a Salome root: README "Application: SALOME-9.13.0"
    (Salome-Meca 2025 of EDF), else W64/SALOME/sat-product-SALOME.pyconf
    "version : 'V9_15_0'" (a build without README), else the folder
    name."""
    return (_grep(os.path.join(root, "README"), r"Application:\s*(\S+)") or
            _grep(os.path.join(root, "W64", "SALOME",
                               "sat-product-SALOME.pyconf"),
                  r"^\s*version\s*:\s*'([^']+)'") or
            os.path.basename(root.rstrip("\\/")))


def _version_tuple(text):
    return tuple(int(x) for x in re.findall(r"\d+", u"{0}".format(
        text or u""))[:4])


def _newest_first(roots):
    def key(root):
        try:
            mtime = os.path.getmtime(os.path.join(root, "run_salome.bat"))
        except OSError:
            mtime = 0.0
        return (_version_tuple(salome_version(root)), mtime)
    return sorted(roots, key=key, reverse=True)


def _salome_setting(setting):
    if setting is None:
        setting = bridge_utils.CONFIG_BRIDGE.get("salome_meca_dir", "")
    return expand_path(u"{0}".format(setting or u"").strip())


def _search_bases(setting, bases):
    """Folders to search: the setting (a root or a folder of roots), else
    bases (None = salome_bases())."""
    text = _salome_setting(setting)
    if text:
        return [text]
    return salome_bases() if bases is None else bases


def find_salome(setting=None, bases=None):
    """Salome-Meca root for AsterStudy, newest first, or "". setting: None
    = CONFIG_BRIDGE["salome_meca_dir"]; bases: folders to search when the
    setting is empty (tests pass their own)."""
    roots = [d for d in salome_dirs(_search_bases(setting, bases))
             if is_salome_root(d)]
    return _newest_first(roots)[0] if roots else ""


def salome_paraviews(setting=None, bases=None):
    """run_paraview.bat of every Salome root with a ParaView, newest
    first."""
    roots = [d for d in salome_dirs(_search_bases(setting, bases))
             if salome_paraview(d)]
    return [salome_paraview(d) for d in _newest_first(roots)]


# ---------------------------------------------------------------- ParaView

def paraview_version(path):
    """Version tuple of an official ParaView from its folder name
    (".../ParaView 6.2.0-Windows-Python3.12-msvc2017-AMD64/bin/paraview.exe"
    -> (6, 2, 0)); (0,) if the name has no version."""
    folder = os.path.basename(os.path.dirname(os.path.dirname(
        os.path.abspath(path))))
    m = re.match(r"(?i)paraview[ _-]*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?",
                 folder)
    if not m:
        return (0,)
    return tuple(int(g) for g in m.groups() if g is not None)


def official_paraviews(environ=None):
    """paraview.exe of official ParaViews (paraview.org) under the Program
    Files folders, newest first."""
    env = os.environ if environ is None else environ
    roots = []
    for v in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        p = env.get(v)
        if p and p not in roots:
            roots.append(p)
    found = []
    for root in roots:
        for path in glob.glob(os.path.join(root, "ParaView*", "bin",
                                           "paraview.exe")):
            if path not in found:
                found.append(path)
    found.sort(key=paraview_version, reverse=True)
    return found


def paraview_candidates(med=False, salome=None, bases=None, environ=None):
    """ParaViews to try, best first. For a .pvd (med False): official
    ParaView 6.x or newer, Salome's, then older official ones. For a .rmed
    (med True) Salome's first: it loads its MED reader itself, while an
    official ParaView 6.x without the MEDReader plugin loaded is NOT
    verified to open a .rmed; ParaView 5.10 has no MED reader at all (seen
    22 Oct 2026), so older official ones are left out."""
    official = official_paraviews(environ)
    modern = [p for p in official if paraview_version(p)[0] >= 6]
    older = [p for p in official if p not in modern]
    own = salome_paraviews(salome, bases)
    order = own + modern if med else modern + own + older
    out = []
    for p in order:
        if p not in out:
            out.append(p)
    return out


def _launcher(path):
    """Salome's paraview.exe (<root>/W64/ParaView/bin/paraview.exe) is
    started through <root>/run_paraview.bat, found up to four folders above
    it; other paths stay as they are."""
    if not path or os.path.basename(path).lower() != "paraview.exe":
        return path
    folder = os.path.dirname(os.path.abspath(path))
    for _level in range(4):
        folder = os.path.dirname(folder)
        bat = os.path.join(folder, "run_paraview.bat")
        if os.path.isfile(bat):
            return bat
    return path


def paraview_exe(setting=None, med=False, salome=None, bases=None,
                 environ=None):
    """ParaView to start: the setting paraview_exe (None = CONFIG_BRIDGE)
    always wins when filled in; else the first of paraview_candidates().
    "" when none is found."""
    if setting is None:
        setting = bridge_utils.CONFIG_BRIDGE.get("paraview_exe", "")
    path = expand_path(setting)
    if path:
        return _launcher(path)
    found = paraview_candidates(med, salome, bases, environ)
    return _launcher(found[0]) if found else ""


# ------------------------------------------------------------ files of a run

def run_base(path):
    """<dir>/<model>_<run_id> from a file of the run (_results.xml, .mess,
    or any other extension)."""
    for suffix in ("_results.xml",):
        if path.endswith(suffix):
            return path[:-len(suffix)]
    return os.path.splitext(path)[0]


def result_files(base):
    """{kind: path} of the result files of the run that exist; kinds
    "verfijnd", "xfem", "pvd", "rmed"."""
    out = {}
    for kind, suffix in _SUFFIXES:
        if os.path.isfile(base + suffix):
            out[kind] = base + suffix
    return out


def choose_file(files, med_only=False):
    """(path, [other files]) in the order of _SUFFIXES (only MED files when
    med_only), or (None, [])."""
    order = [k for k, _s in _SUFFIXES
             if not (med_only and k == "pvd") and k in files]
    if not order:
        return None, []
    return files[order[0]], [files[k] for k in order[1:]]


# ------------------------------------------------------------------- start

def _unsafe(paths):
    """The first path with a character cmd.exe would interpret, or None."""
    for p in paths:
        if any(c in p for c in CMD_UNSAFE):
            return p
    return None


def _clean_env(extra=None):
    """Environment for a started program: without PYTHONPATH/PYTHONHOME of
    the Python that starts it (IronPython in Mecway, Code-Aster's Python in
    the convergence window)."""
    env = dict((k, v) for k, v in os.environ.items()
               if k.upper() not in ("PYTHONPATH", "PYTHONHOME"))
    env.update(extra or {})
    return env


def _start(cmd, cwd, log_path, popen=None, env=None):
    """Start cmd without a console window, stdout/stderr to log_path (Mecway
    has no console handles to pass on). Returns None or the error text."""
    out = None
    try:
        out = open(log_path, "wb")
        (popen or subprocess.Popen)(cmd, cwd=cwd, env=env or _clean_env(),
                                    stdin=None, stdout=out, stderr=out,
                                    creationflags=CREATE_NO_WINDOW)
        return None
    except Exception as e:
        return u"{0}".format(e)
    finally:
        if out is not None:
            out.close()


def _others_note(others):
    if not others:
        return u""
    return tr(u"\nAndere resultaatbestanden van deze run: {0}",
              u"\nOther result files of this run: {0}").format(
                  u", ".join(os.path.basename(p) for p in others))


def _no_file_text(base, med_only):
    if med_only:
        return tr(u"Geen MED-bestand (.rmed) voor deze run:\n{0}.rmed\n\n"
                  u"AsterStudy opent alleen MED-bestanden. Zet in het "
                  u"startscherm 'MED-bestand voor ParaView' (med_export) aan "
                  u"en start de run opnieuw.",
                  u"No MED file (.rmed) for this run:\n{0}.rmed\n\n"
                  u"AsterStudy opens MED files only. Turn on 'MED file for "
                  u"ParaView' (med_export) on the start screen and run "
                  u"again.").format(base)
    return tr(u"Geen resultaatbestand voor ParaView bij deze run:\n"
              u"{0}.pvd / .rmed\n\nZet in het startscherm 'VTU/PVD-"
              u"bestanden voor ParaView' (vtu_export) of 'MED-bestand voor "
              u"ParaView' (med_export) aan en start de run opnieuw.",
              u"No result file for ParaView for this run:\n"
              u"{0}.pvd / .rmed\n\nTurn on 'VTU/PVD files for ParaView' "
              u"(vtu_export) or 'MED file for ParaView' (med_export) on the "
              u"start screen and run again.").format(base)


def _unsafe_text(path):
    return tr(u"Dit pad bevat een teken dat de Windows-opdrachtregel anders "
              u"leest (een van {0}), daarom start de bridge het programma "
              u"niet:\n{1}\n\nGebruik een werkmap of installatiemap zonder "
              u"die tekens.",
              u"This path holds a character the Windows command line reads "
              u"differently (one of {0}), so the bridge does not start the "
              u"program:\n{1}\n\nUse a work folder or installation folder "
              u"without those characters.").format(CMD_UNSAFE, path)


def open_paraview(base, paraview=None, salome=None, popen=None, bases=None,
                  environ=None):
    """
    Open the result of the run <base> (= <dir>/<model>_<run_id>) in
    ParaView: _verfijnd.rmed or _xfem.rmed when present, else the .pvd,
    else the .rmed. paraview / salome: the settings paraview_exe and
    salome_meca_dir (None = CONFIG_BRIDGE). Returns (ok, text); text names
    the other result files of the run.
    """
    path, others = choose_file(result_files(base))
    if path is None:
        return False, _no_file_text(base, False)
    med = path.lower().endswith(".rmed")
    exe = paraview_exe(paraview, med, salome, bases, environ)
    if not exe or not os.path.isfile(exe):
        return False, tr(
            u"ParaView niet gevonden{0}. Vul in het startscherm 'ParaView' "
            u"(paraview_exe) in, of installeer ParaView (paraview.org) of "
            u"Salome-Meca. Een .rmed opent in de ParaView van Salome-Meca; "
            u"ParaView 5.10 kan geen .rmed openen.",
            u"ParaView not found{0}. Fill in 'ParaView' (paraview_exe) on "
            u"the start screen, or install ParaView (paraview.org) or "
            u"Salome-Meca. A .rmed opens in Salome-Meca's ParaView; "
            u"ParaView 5.10 cannot open a .rmed.").format(
                u" ({0})".format(exe) if exe else u"")
    if exe.lower().endswith(".bat"):
        bad = _unsafe([exe, path])
        if bad:
            return False, _unsafe_text(bad)
    log_path = base + "_paraview_launch.log"
    error = _start([exe, path], os.path.dirname(os.path.abspath(path)),
                   log_path, popen)
    if error:
        return False, tr(u"ParaView starten mislukt: {0}\n{1}",
                         u"Starting ParaView failed: {0}\n{1}").format(
                             exe, error)
    bridge_utils.log(u"INFO: ParaView started: {0} {1}".format(exe, path))
    return True, tr(u"ParaView opent {0}.", u"ParaView opens {0}.").format(
        os.path.basename(path)) + _others_note(others)


# Runs in the Python of the Salome GUI (3.9 in Salome-Meca 2025) as a script
# of the launcher (salome start <script>). Public Salome calls
# (SalomePyQt.activateModule) plus AsterStudy's showResultsFile and Results
# tab, which can change per AsterStudy version.
SESSION_TEMPLATE = u'''# -*- coding: utf-8 -*-
# Written by MecwayAsterBridge (bridge_viewers.py): opens a MED result in
# AsterStudy, tab Results. Safe to delete.
import os
import sys
import time
import traceback

MED_PATH = @MED_PATH@
LOG_PATH = @LOG_PATH@


def _log(text):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("{0} {1}\\n".format(time.strftime("%H:%M:%S"), text))
    except Exception:
        pass


def _aster_gui():
    for name in ("ASTERSTUDYGUI", "salome.ASTERSTUDYGUI"):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "get_aster_gui"):
            return mod.get_aster_gui()
    import ASTERSTUDYGUI
    return ASTERSTUDYGUI.get_aster_gui()


def _results_tab(gui):
    try:
        from asterstudy.gui import Context
        gui.workSpace().view(Context.Results).set_as_working_tab()
        _log("results tab shown")
    except Exception:
        _log("results tab: " + traceback.format_exc())


def _open():
    try:
        import SalomePyQt
        sg = SalomePyQt.SalomePyQt()
        _log("activate ASTERSTUDY: {0}".format(sg.activateModule("ASTERSTUDY")))
        gui = _aster_gui()
        gui.showResultsFile(MED_PATH)
        _log("showResultsFile called: " + MED_PATH)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, lambda: _results_tab(gui))
    except Exception:
        _log("ERROR: " + traceback.format_exc())


_log("session script started, pid {0}".format(os.getpid()))
try:
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(500, _open)
except Exception:
    _open()
'''


def _literal(text):
    """Python 3 string literal of text in pure ASCII, the same from
    IronPython 2.7 and CPython 3: non-ASCII characters as \\uXXXX or
    \\UXXXXXXXX (a UTF-16 surrogate pair of IronPython joined into one code
    point). IronPython's json.dumps fails on non-ASCII text, and repr()
    differs between the two."""
    text = u"{0}".format(text)
    out = []
    i = 0
    while i < len(text):
        c = ord(text[i])
        if 0xD800 <= c < 0xDC00 and i + 1 < len(text) and \
                0xDC00 <= ord(text[i + 1]) < 0xE000:
            c = 0x10000 + ((c - 0xD800) << 10) + (ord(text[i + 1]) - 0xDC00)
            i += 1
        i += 1
        if c in (0x22, 0x5C):                     # " and backslash
            out.append(u"\\" + unichr_(c))
        elif 0x20 <= c < 0x7F:
            out.append(unichr_(c))
        elif c <= 0xFFFF:
            out.append(u"\\u%04x" % c)
        else:
            out.append(u"\\U%08x" % c)
    return u'"' + u"".join(out) + u'"'


def unichr_(c):
    """chr() of a code point below 0x80 in both Pythons."""
    try:
        return unichr(c)           # noqa: F821 (IronPython 2.7)
    except NameError:
        return chr(c)


def salome_files(med_path):
    """(session script, session log, launch log) next to a MED file:
    <stem>_salome.py, <stem>_salome_session.log, <stem>_salome_launch.log."""
    stem = os.path.splitext(os.path.abspath(med_path))[0] + "_salome"
    return stem + ".py", stem + "_session.log", stem + "_launch.log"


def session_script_text(med_path, log_path):
    return SESSION_TEMPLATE.replace(u"@MED_PATH@", _literal(med_path)) \
        .replace(u"@LOG_PATH@", _literal(log_path))


def salome_command(root, script):
    """What run_salome.bat runs, without its START: Salome's own Python with
    the launcher "salome" and the session script."""
    return [os.path.join(root, "W64", "Python", "python3.exe"),
            os.path.join(root, "salome"), "start", script]


def salome_env():
    """Environment as run_salome.bat of Salome-Meca 2025 sets it."""
    return _clean_env({"DEBUG": "-1", "ASTER_NO_EXCEPTHANDLER": "1"})


def open_asterstudy(base, salome=None, popen=None, bases=None, now=None):
    """
    Open the MED result of the run <base> in Salome-Meca, AsterStudy tab
    Results: _verfijnd.rmed or _xfem.rmed when present, else the .rmed.
    Writes <stem>_salome.py and starts Salome-Meca with it (a new Salome
    session per click; a second click within SALOME_BUSY_SECONDS of the
    session log only gives a message). Returns (ok, text).
    """
    path, others = choose_file(result_files(base), med_only=True)
    if path is None:
        return False, _no_file_text(base, True)
    root = find_salome(salome, bases)
    if not root:
        return False, tr(
            u"Salome-Meca niet gevonden (gezocht in {0}). Installeer "
            u"Salome-Meca 2025 of vul in het startscherm 'Salome-Meca-map' "
            u"(salome_meca_dir) in.",
            u"Salome-Meca not found (looked in {0}). Install Salome-Meca "
            u"2025 or fill in 'Salome-Meca folder' (salome_meca_dir) on the "
            u"start screen.").format(u"; ".join(_search_bases(salome,
                                                                bases)))
    script, session_log, launch_log = salome_files(path)
    now = time.time() if now is None else now
    try:
        busy = now - os.path.getmtime(session_log) < SALOME_BUSY_SECONDS
    except OSError:
        busy = False
    if busy:
        return False, tr(
            u"Salome-Meca start al voor {0} (minder dan {1} s geleden). "
            u"Wacht op het venster; klik daarna opnieuw voor een tweede "
            u"sessie.",
            u"Salome-Meca is already starting for {0} (less than {1} s "
            u"ago). Wait for its window; click again after that for a second "
            u"session.").format(os.path.basename(path), SALOME_BUSY_SECONDS)
    try:
        f = io.open(script, "w", encoding="utf-8")
        try:
            f.write(session_script_text(path, session_log))
        finally:
            f.close()
        f = io.open(session_log, "w", encoding="utf-8")
        f.close()
    except (IOError, OSError) as e:
        return False, tr(u"Sessiescript niet te schrijven: {0}",
                         u"Cannot write the session script: {0}").format(e)
    error = _start(salome_command(root, script), root, launch_log, popen,
                   salome_env())
    if error:
        return False, tr(u"Salome-Meca starten mislukt: {0}",
                         u"Starting Salome-Meca failed: {0}").format(error)
    bridge_utils.log(u"INFO: Salome-Meca started ({0}) for {1}".format(
        root, path))
    return True, tr(
        u"Salome-Meca start (dat duurt even) en opent {0} in AsterStudy, "
        u"tabblad Results.",
        u"Salome-Meca is starting (this takes a while) and opens {0} in "
        u"AsterStudy, tab Results.").format(os.path.basename(path)) + \
        _others_note(others)
