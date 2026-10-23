# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_gui.py
# Responsibility: the non-modal window of MecwaySectionProps.
#   run_window(mw)        show the window until the user closes it
#   claim_instance() / release_instance() / activate_existing()
#                         one window per Mecway process
#
# The window runs on its own STA thread (Application.Run); the script thread
# (Mecway's) keeps Mecway's messages going and executes every mw call the
# window asks for (_MwCaller), so the user can select faces in Mecway while
# the window is open. Same pattern as the panel of MecwayHexMesh (there:
# after a box selection in the viewport, buttons of a window on Mecway's own
# thread no longer clicked).
#
# Flow: "Calculate" reads the selected faces (section_mecway.read_selection),
# builds the boundary (mesh faces) or the STEP request (CAD face), starts
# section_analysis.py in Code-Aster's Python and shows the table and the
# plot. "Create general section" makes a Mecway material from the result
# and, if ticked, stores the extra Code-Aster data as an #ASTER-SECTIE line
# (section_mecway.store_aster_line: save, edit the .liml, reopen).
#
# Texts: every user text in Dutch and English; the NL/EN switch in the
# header redraws the window. Compatible with IronPython 2.7.9.

import math
import threading
import time
import traceback

import bridge_utils
from bridge_utils import log
import section_mecway as smw

PANEL_TITLE = u"MecwaySectionProps"
_INSTANCE_NAME = u"MecwaySectionProps_{0}"
# Seconds after which a hanging analysis process is stopped.
ANALYSIS_TIMEOUT = 600

T = {
    "title": (u"Doorsnede-eigenschappen", u"Section properties"),
    "sub_none": (u"Selecteer in Mecway de vlakken van een vlakke doorsnede "
                 u"en klik op Berekenen.",
                 u"Select the faces of a flat cross-section in Mecway and "
                 u"click Calculate."),
    "input": (u"Invoer:", u"Input:"),
    "mode_mesh": (u"Mesh-vlakken (selectie)", u"Mesh faces (selection)"),
    "mode_cad": (u"CAD-vlak (exacte STEP-rand)",
                 u"CAD face (exact STEP boundary)"),
    "calc": (u"Berekenen", u"Calculate"),
    "busy": (u"Bezig met berekenen... {0} s", u"Calculating... {0} s"),
    "unit": (u"Eenheid:", u"Unit:"),
    "copy": (u"Kopiëren", u"Copy"),
    "close": (u"Sluiten", u"Close"),
    "copied": (u"Gegevens gekopieerd (plakbaar in Excel)",
               u"Data copied (pastes into Excel)"),
    "copy_fail": (u"Kopiëren mislukt: {0}", u"Copy failed: {0}"),
    "gs_group": (u"General section in Mecway", u"General section in Mecway"),
    "gs_name": (u"Materiaalnaam:", u"Material name:"),
    "gs_comp": (u"Toewijzen aan:", u"Assign to:"),
    "gs_none": (u"(geen component)", u"(no component)"),
    "gs_copy": (u"E, ν, ρ overnemen van het huidige materiaal",
                u"Copy E, ν, ρ from the current material"),
    "gs_store": (u"Extra Code-Aster-eigenschappen opslaan (model wordt "
                 u"opgeslagen en heropend)",
                 u"Store extra Code-Aster properties (the model is saved "
                 u"and reopened)"),
    "gs_make": (u"General section maken", u"Create general section"),
    "gs_need": (u"Bereken eerst een doorsnede.",
                u"Calculate a section first."),
    "gs_no_j": (u"Geen torsieconstante (losse delen?): een General section "
                u"kan niet worden gemaakt.",
                u"No torsion constant (separate parts?): a general section "
                u"cannot be created."),
    "gs_confirm": (u"Het model wordt opgeslagen, de extra Code-Aster-"
                   u"eigenschappen worden in de custom model definition "
                   u"gezet en het model wordt opnieuw geopend (de undo-"
                   u"geschiedenis van Mecway vervalt).\n\nDoorgaan?",
                   u"The model is saved, the extra Code-Aster properties "
                   u"are put in the custom model definition and the model "
                   u"is reopened (Mecway's undo history is lost).\n\n"
                   u"Continue?"),
    "gs_done": (u"Materiaal '{0}' gemaakt{1}.", u"Material '{0}' created{1}."),
    "gs_assigned": (u" en toegewezen aan '{0}'", u" and assigned to '{0}'"),
    "gs_stored": (u"; extra eigenschappen opgeslagen in het model",
                  u"; extra properties stored in the model"),
    "gs_failed": (u"General section maken mislukt:\n{0}",
                  u"Creating the general section failed:\n{0}"),
    "error": (u"Fout", u"Error"),
    "faces": (u"{0} vlak(ken)", u"{0} face(s)"),
    "cad_faces": (u"CAD-vlak(ken) {0}", u"CAD face(s) {0}"),
    "units": (u"eenheden: {0}", u"units: {0}"),
    # table
    "s_geom": (u"Geometrie", u"Geometry"),
    "area": (u"Oppervlakte A", u"Area A"),
    "perim": (u"Omtrek (buitenrand)", u"Perimeter (outer)"),
    "cent": (u"Zwaartepunt (x; y)", u"Centroid (x; y)"),
    "cent3": (u"Zwaartepunt globaal (X; Y; Z)", u"Centroid global (X; Y; Z)"),
    "s_inertia": (u"Traagheid t.o.v. zwaartepunt",
                  u"Second moments about centroid"),
    "i11": (u"I11 (hoofdas 1)", u"I11 (principal axis 1)"),
    "i22": (u"I22 (hoofdas 2)", u"I22 (principal axis 2)"),
    "phi": (u"Hoek hoofdas φ (van +x)", u"Principal angle φ (from +x)"),
    "rx": (u"Traagheidsstraal rx", u"Radius of gyration rx"),
    "ry": (u"Traagheidsstraal ry", u"Radius of gyration ry"),
    "s_mod": (u"Weerstandsmomenten", u"Section moduli"),
    "wxp": (u"Wx boven (+y)", u"Wx top (+y)"),
    "wxm": (u"Wx onder (−y)", u"Wx bottom (−y)"),
    "wyp": (u"Wy rechts (+x)", u"Wy right (+x)"),
    "wym": (u"Wy links (−x)", u"Wy left (−x)"),
    "w11": (u"W1 (hoofdas 1, min.)", u"W1 (principal axis 1, min.)"),
    "w22": (u"W2 (hoofdas 2, min.)", u"W2 (principal axis 2, min.)"),
    "wplx": (u"Wpl,x (plastisch)", u"Wpl,x (plastic)"),
    "wply": (u"Wpl,y (plastisch)", u"Wpl,y (plastic)"),
    "wpl1": (u"Wpl,1 (plastisch, hoofdas 1)", u"Wpl,1 (plastic, axis 1)"),
    "wpl2": (u"Wpl,2 (plastisch, hoofdas 2)", u"Wpl,2 (plastic, axis 2)"),
    "s_tors": (u"Torsie, welving en afschuiving",
               u"Torsion, warping and shear"),
    "j": (u"Torsieconstante J", u"Torsion constant J"),
    "iw": (u"Welvingsconstante Iw", u"Warping constant Iw"),
    "sc": (u"Dwarskrachtcentrum (x; y)", u"Shear centre (x; y)"),
    "as1": (u"Afschuifoppervlak As,1 (langs as 1)",
            u"Shear area As,1 (along axis 1)"),
    "as2": (u"Afschuifoppervlak As,2 (langs as 2)",
            u"Shear area As,2 (along axis 2)"),
    "s_mecway": (u"Mecway General section (V = as 1, W = as 2)",
                 u"Mecway general section (V = axis 1, W = axis 2)"),
    "m_iyy": (u"Iyy (om V)", u"Iyy (about V)"),
    "m_izz": (u"Izz (om W)", u"Izz (about W)"),
    "m_pt": (u"Spanningspunt (V; W)", u"Stress recovery point (V; W)"),
    "m_u": (u"Balkas U = normaal n", u"Beam axis U = normal n"),
    "m_v": (u"V-vector (as 1) voor Element orientation",
            u"V vector (axis 1) for Element orientation"),
    "m_w": (u"W = U × V (as 2)", u"W = U × V (axis 2)"),
    "s_aster": (u"Code-Aster GENERALE (#ASTER-SECTIE, y = V, z = W)",
                u"Code-Aster GENERALE (#ASTER-SECTIE, y = V, z = W)"),
    "n_parts": (u"Torsie/welving/afschuiving niet berekend: {0}",
                u"Torsion/warping/shear not computed: {0}"),
    "n_axes": (u"Assen: x = globaal {0}, y = globaal {1} (vlak gezien van "
               u"buiten).",
               u"Axes: x = global {0}, y = global {1} (face seen from "
               u"outside)."),
    "n_beam": (u"EY/EZ gelden voor balken van knoop 1 naar 2 in de richting "
               u"n; loopt de balk andersom, dan is de doorsnede gespiegeld.",
               u"EY/EZ apply to beams running from node 1 to 2 along n; a "
               u"beam running the other way sees the section mirrored."),
    "n_mesh": (u"Mesh: {0} elementen (tri6), {1} knopen.",
               u"Mesh: {0} elements (tri6), {1} nodes."),
    "n_cad": (u"Rand uit STEP: {0}", u"Boundary from STEP: {0}"),
    "n_welded": (u"{0} dubbele knopen samengevoegd.",
                 u"{0} duplicate nodes merged."),
    "n_split": (u"{0} rand(en) gesplitst bij een T-aansluiting.",
                u"{0} edge(s) split at a T-joint."),
    "n_gaps": (u"{0} kleine opening(en) in de rand gesloten met een rechte "
               u"lijn (grootste {1} mm bij ({2}; {3}) mm).",
               u"{0} small gap(s) in the boundary closed with a straight "
               u"line (largest {1} mm at ({2}; {3}) mm)."),
    # plot
    "p_cent": (u"zwaartepunt", u"centroid"),
    "p_axes": (u"x, y: assen door zwaartepunt", u"x, y: centroidal axes"),
    "p_ax1": (u"1 = V: hoofdas, I11 = {0}", u"1 = V: principal axis, "
              u"I11 = {0}"),
    "p_ax2": (u"2 = W: hoofdas, I22 = {0}", u"2 = W: principal axis, "
              u"I22 = {0}"),
    "p_phi": (u"φ = {0}° (van +x naar as 1)",
              u"φ = {0}° (from +x to axis 1)"),
    "p_sc": (u"dwarskrachtcentrum ({0}; {1})", u"shear centre ({0}; {1})"),
    "busy_text": (u"Het venster van MecwaySectionProps is al open.",
                  u"The MecwaySectionProps window is already open."),
}
LANGS = ("nl", "en")
UNITS = ("mm", "m")
SUP = {"-": u"⁻", "0": u"⁰", "1": u"¹", "2": u"²",
       "3": u"³", "4": u"⁴", "5": u"⁵", "6": u"⁶",
       "7": u"⁷", "8": u"⁸", "9": u"⁹"}


def tx(key, lang):
    nl, en = T[key]
    return nl if lang == "nl" else en


def _lang():
    return "nl" if bridge_utils.CONFIG_BRIDGE.get("language") == "nl" \
        else "en"


def instance_busy_text():
    return tx("busy_text", _lang())


# ==========================================
# NUMBERS
# ==========================================
def fmt(v, dec):
    """Readable number: grouped digits, x10^n for very large/small values
    (as AreaPropsForAlibre)."""
    if v is None:
        return u"–"
    if v == 0:
        return u"0"
    a = abs(v)
    if 1e-3 <= a < 1e6:
        s = "%.6g" % v
        if "e" in s:
            s = "%.6f" % v
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        sign = u""
        if s.startswith("-"):
            sign, s = u"−", s[1:]
        ip, _, fp = s.partition(".")
        if len(ip) > 4:
            groups = []
            while len(ip) > 3:
                groups.insert(0, ip[-3:])
                ip = ip[:-3]
            groups.insert(0, ip)
            ip = u" ".join(groups)
        return sign + ip + (dec + fp if fp else u"")
    e = int(math.floor(math.log10(a)))
    m = v / 10.0 ** e
    ms = ("%.4f" % m).rstrip("0").rstrip(".").replace(".", dec)
    if ms.startswith("-"):
        ms = u"−" + ms[1:]
    return u"{0} × 10{1}".format(ms, u"".join(SUP[c] for c in str(e)))


def raw(v, dec):
    return u"" if v is None else ("%.10g" % v).replace(".", dec)


def scale_of(unit, power):
    """Factor from SI (m^power) to the display unit."""
    return (1e3 ** power) if unit == "mm" else 1.0


def unit_text(unit, power):
    sup = {1: u"", 2: u"²", 3: u"³", 4: u"⁴", 6: u"⁶",
           5: u"⁵"}
    return unit + sup[power]


# ==========================================
# TABLE CONTENT
# ==========================================
def _dir3(plane, a, b):
    """3D direction a*u + b*v."""
    u, v = plane["u"], plane["v"]
    return tuple(a * u[i] + b * v[i] for i in range(3))


def heal_notes(heal, lang):
    """Notes on the repairs of the boundary (section_mecway.boundary_loops,
    section_step gap closing)."""
    notes = []
    if not heal:
        return notes
    if heal.get("welded"):
        notes.append(tx("n_welded", lang).format(heal["welded"]))
    if heal.get("split"):
        notes.append(tx("n_split", lang).format(heal["split"]))
    gaps = heal.get("gaps_closed") or []
    if gaps:
        dec = u"," if lang == "nl" else u"."
        big = max(gaps, key=lambda g: g[0])
        notes.append(tx("n_gaps", lang).format(
            len(gaps), fmt(big[0] * 1e3, dec), fmt(big[1][0] * 1e3, dec),
            fmt(big[1][1] * 1e3, dec)))
    return notes


def table_sections(res, plane, lang, unit, heal=None):
    """[(title, [(label, value or tuple or text, unit text)])] of the
    results in the display unit, and the notes."""
    def L(p):
        return scale_of(unit, p)

    def U(p):
        return unit_text(unit, p)

    def val(key, p):
        v = res.get(key)
        return None if v is None else v * L(p)
    cx, cy = res["centroid"]
    n = plane["normal"]
    c3 = tuple(cx * plane["u"][i] + cy * plane["v"][i] + plane["offset"] *
               n[i] for i in range(3))
    phi = math.radians(res["phi_deg"])
    ax1 = _dir3(plane, math.cos(phi), math.sin(phi))
    ax2 = _dir3(plane, -math.sin(phi), math.cos(phi))
    sections = [
        (tx("s_geom", lang), [
            (tx("area", lang), val("area", 2), U(2)),
            (tx("perim", lang), val("perimeter", 1), U(1)),
            (tx("cent", lang), (cx * L(1), cy * L(1)), U(1)),
            (tx("cent3", lang), tuple(c * L(1) for c in c3), U(1)),
        ]),
        (tx("s_inertia", lang), [
            (u"Ixx", val("ixx_c", 4), U(4)),
            (u"Iyy", val("iyy_c", 4), U(4)),
            # Ixy below 1e-9 of the largest moment is round-off of the mesh
            (u"Ixy", 0.0 if abs(res["ixy_c"]) < 1e-9 * max(
                abs(res["ixx_c"]), abs(res["iyy_c"])) else val("ixy_c", 4),
             U(4)),
            (tx("i11", lang), val("i11_c", 4), U(4)),
            (tx("i22", lang), val("i22_c", 4), U(4)),
            (tx("phi", lang), res["phi_deg"], u"°"),
            (tx("rx", lang), val("rx", 1), U(1)),
            (tx("ry", lang), val("ry", 1), U(1)),
        ]),
    ]
    mods = [
        (tx("wxp", lang), val("zxx_plus", 3), U(3)),
        (tx("wxm", lang), val("zxx_minus", 3), U(3)),
        (tx("wyp", lang), val("zyy_plus", 3), U(3)),
        (tx("wym", lang), val("zyy_minus", 3), U(3)),
    ]
    if res.get("z11_plus") is not None:
        mods.append((tx("w11", lang), min(res["z11_plus"], res["z11_minus"])
                     * L(3), U(3)))
        mods.append((tx("w22", lang), min(res["z22_plus"], res["z22_minus"])
                     * L(3), U(3)))
    if res.get("plastic_computed"):
        mods += [(tx("wplx", lang), val("sxx", 3), U(3)),
                 (tx("wply", lang), val("syy", 3), U(3)),
                 (tx("wpl1", lang), val("s11", 3), U(3)),
                 (tx("wpl2", lang), val("s22", 3), U(3))]
    sections.append((tx("s_mod", lang), mods))
    notes = []
    if res.get("warping_computed"):
        sc = res["shear_centre"]
        sections.append((tx("s_tors", lang), [
            (tx("j", lang), val("j", 4), U(4)),
            (tx("iw", lang), val("gamma", 6), U(6)),
            (tx("sc", lang), (sc[0] * L(1), sc[1] * L(1)), U(1)),
            (tx("as1", lang), val("a_s11", 2), U(2)),
            (tx("as2", lang), val("a_s22", 2), U(2)),
        ]))
        py, pz = smw.recovery_point(res)
        sections.append((tx("s_mecway", lang), [
            (u"Area", val("area", 2), U(2)),
            (tx("m_iyy", lang), val("i11_c", 4), U(4)),
            (tx("m_izz", lang), val("i22_c", 4), U(4)),
            (u"Torsion constant", val("j", 4), U(4)),
            (u"Perimeter", val("perimeter", 1), U(1)),
            (tx("m_pt", lang), (py * L(1), pz * L(1)), U(1)),
            (tx("m_u", lang), smw.axis_name(n), u""),
            (tx("m_v", lang), smw.axis_name(ax1), u""),
            (tx("m_w", lang), smw.axis_name(ax2), u""),
        ]))
        a = res.get("aster", {})
        rows = []
        for key, p in (("AY", 0), ("AZ", 0), ("EY", 1), ("EZ", 1),
                       ("RY", 1), ("RZ", 1), ("RT", 1), ("JG", 6),
                       ("IYR2", 5), ("IZR2", 5)):
            if a.get(key) is not None:
                rows.append((key, a[key] * (L(p) if p else 1.0),
                             U(p) if p else u"–"))
        sections.append((tx("s_aster", lang), rows))
        notes.append(tx("n_beam", lang))
    else:
        notes.append(tx("n_parts", lang).format(
            res.get("warping_note") or u"?"))
    notes.append(tx("n_axes", lang).format(smw.axis_name(plane["u"]),
                                           smw.axis_name(plane["v"])))
    notes.append(tx("n_mesh", lang).format(res.get("n_elements", "?"),
                                           res.get("n_nodes", "?")))
    return sections, heal_notes(heal, lang) + notes


# ==========================================
# ONE WINDOW PER MECWAY PROCESS (as MecwayHexMesh)
# ==========================================
def claim_instance():
    """Token for release_instance(), True without .NET, or None when the
    window is already open in this Mecway process."""
    try:
        from System.Threading import Semaphore
        from System.Diagnostics import Process
        name = _INSTANCE_NAME.format(Process.GetCurrentProcess().Id)
    except Exception:
        return True
    semaphore = Semaphore(1, 1, name)
    if not semaphore.WaitOne(0):
        semaphore.Dispose()
        return None
    return semaphore


def release_instance(token):
    if token is None or token is True:
        return
    try:
        token.Release()
    finally:
        token.Dispose()


def activate_existing():
    """Bring the open window to the front (second start of the script;
    Win32 by title, because a second start may run in a fresh script
    engine). Returns True when it was found."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.FindWindowExW.restype = ctypes.c_void_p
        user32.FindWindowExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_wchar_p, ctypes.c_wchar_p]
        user32.GetWindowThreadProcessId.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        pid = ctypes.windll.kernel32.GetCurrentProcessId()
        hwnd = None
        while True:
            hwnd = user32.FindWindowExW(None, hwnd, None, PANEL_TITLE)
            if not hwnd:
                return False
            owner = ctypes.c_ulong(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid:
                user32.ShowWindow(hwnd, 9)          # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return True
    except Exception:
        return False


# ==========================================
# MW CALLS FROM THE WINDOW THREAD (as MecwayHexMesh)
# ==========================================
class _MwCaller(object):
    """The window thread hands a function that uses mw to the script
    thread and waits; the wait (WaitOne on an STA thread) still answers
    sent messages, so Mecway never blocks on us. direct=True: call at once
    (offline tests)."""

    def __init__(self, direct=False):
        self.direct = direct
        self._lock = threading.Lock()
        self._queue = []

    def call(self, fn):
        if self.direct:
            return fn()
        from System.Threading import ManualResetEvent
        box = {"fn": fn, "done": ManualResetEvent(False)}
        self._lock.acquire()
        try:
            self._queue.append(box)
        finally:
            self._lock.release()
        while not box["done"].WaitOne(50):
            pass
        if "error" in box:
            raise RuntimeError(box["error"])
        return box.get("result")

    def serve_once(self):
        self._lock.acquire()
        try:
            box = self._queue.pop(0) if self._queue else None
        finally:
            self._lock.release()
        if box is None:
            return
        try:
            box["result"] = box["fn"]()
        except Exception as e:
            box["error"] = u"{0}".format(e)
            log("ERROR: MecwaySectionProps: {0}".format(
                traceback.format_exc()))
        box["done"].Set()

    def serve(self, thread, pump=None):
        while thread.IsAlive:
            self.serve_once()
            if pump is not None:
                pump()
            thread.Join(10)
        self.serve_once()


def run_window(mw):
    """Show the window until the user closes it. ImportError when Windows
    Forms cannot be loaded."""
    try:
        import clr
        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
        from System.Threading import Thread, ThreadStart, ApartmentState
        from System.Windows.Forms import Application
    except Exception as e:
        raise ImportError(u"Windows Forms: {0}".format(e))
    result = {"error": None}
    caller = _MwCaller(False)

    def build_and_run():
        try:
            from System.Windows.Forms import Application as App
            App.Run(_Window(mw, caller).form)
        except Exception:
            result["error"] = traceback.format_exc()

    thread = Thread(ThreadStart(build_and_run))
    thread.SetApartmentState(ApartmentState.STA)
    thread.IsBackground = True
    thread.Start()
    on_ui_thread = (Thread.CurrentThread.GetApartmentState() ==
                    ApartmentState.STA)
    caller.serve(thread, Application.DoEvents if on_ui_thread else None)
    if result["error"]:
        raise RuntimeError(result["error"])


# ==========================================
# THE WINDOW
# ==========================================
def _forms():
    import clr
    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    import System.Drawing as D
    import System.Windows.Forms as F
    return D, F


_CLICK_SAFE = {}


def click_safe(kind):
    """A Button/CheckBox/RadioButton class whose click does not depend on
    WindowFromPoint (a window of Mecway's thread over the spot swallowed
    clicks in MecwayHexMesh, its known bug 60): it clicks on a release
    inside its own area after a press on it."""
    cls = _CLICK_SAFE.get(kind)
    if cls is not None:
        return cls
    D, F = _forms()
    base = getattr(F, kind)
    left = F.MouseButtons.Left
    native = F.FlatStyle.System

    class ClickSafe(base):
        def OnMouseDown(self, e):
            self._sp_down = e.Button == left
            base.OnMouseDown(self, e)

        def OnClick(self, e):
            self._sp_clicked = True
            base.OnClick(self, e)

        def OnMouseUp(self, e):
            down = getattr(self, "_sp_down", False)
            self._sp_down = False
            self._sp_clicked = False
            base.OnMouseUp(self, e)
            if down and not self._sp_clicked and e.Button == left and \
                    self.FlatStyle != native and self.Enabled and \
                    self.ClientRectangle.Contains(e.Location):
                self.OnClick(e)

    _CLICK_SAFE[kind] = ClickSafe
    return ClickSafe


C = {}


def _colors():
    D, F = _forms()
    if not C:
        C.update({
            "header": D.Color.FromArgb(32, 41, 54),
            "header_sub": D.Color.FromArgb(170, 182, 196),
            "accent": D.Color.FromArgb(0, 120, 212),
            "text": D.Color.FromArgb(30, 30, 30),
            "muted": D.Color.FromArgb(105, 112, 120),
            "line": D.Color.FromArgb(225, 229, 234),
            "band": D.Color.FromArgb(247, 249, 251),
            "bg": D.Color.White,
            "fill": D.Color.FromArgb(207, 227, 247),
            "edge": D.Color.FromArgb(31, 59, 87),
            "ax1": D.Color.FromArgb(209, 52, 47),
            "ax2": D.Color.FromArgb(46, 139, 87),
            "grey": D.Color.FromArgb(85, 85, 85),
            "sc": D.Color.FromArgb(242, 163, 58),
            "error": D.Color.FromArgb(180, 30, 30),
        })
    return C


WIDTH = 1180
TABLE_W = 600
HEADER_H = 64
BAR_H = 46
GS_H = 104
FOOTER_H = 52
ROW_H = 21
PAD = 18


class _Window(object):
    def __init__(self, mw, caller):
        self.mw = mw
        self.caller = caller
        self.lang = _lang()
        self.unit = "mm"
        self.mode = "mesh"
        self.res = None
        self.plane = None
        self.source = u""
        self.heal = None            # repairs of the boundary (notes)
        self.status = u""
        self.status_error = False
        self.busy = None            # (process, result path, start time)
        self.name = u"Section"
        self.component = None
        self.copy_mat = True
        self.store = True
        self.components = []
        D, F = _forms()
        self.D, self.F = D, F
        form = F.Form()
        form.AutoScaleDimensions = D.SizeF(96.0, 96.0)
        form.AutoScaleMode = F.AutoScaleMode.Dpi
        form.Text = PANEL_TITLE
        form.BackColor = _colors()["bg"]
        form.FormBorderStyle = F.FormBorderStyle.Sizable
        form.MinimizeBox = True
        form.MaximizeBox = False
        form.ShowInTaskbar = True
        form.StartPosition = F.FormStartPosition.CenterScreen
        form.Font = D.Font("Segoe UI", 9.0)
        form.ClientSize = D.Size(WIDTH, 820)
        form.MinimumSize = D.Size(900, 600)
        self.form = form
        self.timer = F.Timer()
        self.timer.Interval = 250
        self.timer.Tick += self._on_tick
        form.Shown += lambda s, e: self._on_shown()
        form.Resize += lambda s, e: self._layout_body()
        form.FormClosing += self._on_closing
        self.render()

    # ---------------- helpers ----------------
    def t(self, key):
        return tx(key, self.lang)

    def _label(self, parent, text, x, y, w, h, size=9.0, bold=False,
               color=None, align=None, back=None):
        D, F = self.D, self.F
        lb = F.Label()
        lb.Text = text
        lb.Location = D.Point(x, y)
        lb.Size = D.Size(w, h)
        lb.Font = D.Font("Segoe UI", size,
                         D.FontStyle.Bold if bold else D.FontStyle.Regular)
        lb.ForeColor = color if color is not None else _colors()["text"]
        lb.TextAlign = align if align is not None else \
            D.ContentAlignment.MiddleLeft
        lb.BackColor = back if back is not None else D.Color.Transparent
        lb.AutoEllipsis = True
        parent.Controls.Add(lb)
        return lb

    def _button(self, parent, text, x, y, w, fn, primary=False):
        D, F = self.D, self.F
        b = click_safe("Button")()
        b.Text = text
        b.Location = D.Point(x, y)
        b.Size = D.Size(w, 30)
        b.FlatStyle = F.FlatStyle.Flat
        b.Font = D.Font("Segoe UI", 9.0)
        b.Cursor = F.Cursors.Hand
        if primary:
            b.BackColor = _colors()["accent"]
            b.ForeColor = D.Color.White
            b.FlatAppearance.BorderSize = 0
        else:
            b.BackColor = _colors()["bg"]
            b.ForeColor = _colors()["text"]
            b.FlatAppearance.BorderColor = D.Color.FromArgb(200, 205, 212)
        b.Click += self._guard(fn)
        parent.Controls.Add(b)
        return b

    def _guard(self, fn):
        def handler(sender, args):
            try:
                fn()
            except Exception as e:
                log("ERROR: MecwaySectionProps: {0}".format(
                    traceback.format_exc()))
                self._set_status(u"{0}".format(e), True)
        return handler

    def _set_status(self, text, error=False):
        self.status, self.status_error = text, error
        lb = getattr(self, "status_label", None)
        if lb is not None and not lb.IsDisposed:
            lb.Text = text
            lb.ForeColor = _colors()["error" if error else "muted"]

    # ---------------- building ----------------
    def render(self):
        D, F = self.D, self.F
        col = _colors()
        form = self.form
        form.SuspendLayout()
        for c in list(form.Controls):
            c.Dispose()
        form.Controls.Clear()
        W = form.ClientSize.Width

        header = F.Panel()
        header.BackColor = col["header"]
        header.Dock = F.DockStyle.Top
        # Full width before adding children: a new panel is 200 px wide and
        # controls anchored to its right edge would move off-screen when
        # docking widens it.
        header.Size = D.Size(W, HEADER_H)
        self._label(header, self.t("title") + u"  ·  " + PANEL_TITLE,
                    PAD, 6, 700, 30, 14, True, D.Color.White)
        self._label(header, self._subtitle(), PAD, 36, W - 260, 20, 8.5,
                    False, col["header_sub"])
        langs = F.FlowLayoutPanel()
        langs.Dock = F.DockStyle.Right
        langs.Width = 130
        langs.Padding = F.Padding(0, 22, 0, 0)
        langs.BackColor = col["header"]
        for code in LANGS:
            rb = click_safe("RadioButton")()
            rb.Text = code.upper()
            rb.Font = D.Font("Segoe UI", 9.0, D.FontStyle.Bold)
            rb.ForeColor = D.Color.White
            rb.BackColor = col["header"]
            rb.AutoSize = True
            rb.Checked = (code == self.lang)
            rb.Tag = code
            rb.CheckedChanged += self._on_lang
            langs.Controls.Add(rb)
        header.Controls.Add(langs)

        bar = F.Panel()
        bar.BackColor = col["band"]
        bar.Dock = F.DockStyle.Top
        bar.Size = D.Size(W, BAR_H)
        self._label(bar, self.t("input"), PAD, 12, 60, 22, 9, True)
        x = PAD + 62
        for code, key, w in (("mesh", "mode_mesh", 190),
                             ("cad", "mode_cad", 230)):
            rb = click_safe("RadioButton")()
            rb.Text = self.t(key)
            rb.AutoSize = True
            rb.Location = D.Point(x, 13)
            rb.Checked = (self.mode == code)
            rb.Tag = code
            rb.BackColor = col["band"]
            rb.CheckedChanged += self._on_mode
            bar.Controls.Add(rb)
            x += w
        self.calc_button = self._button(bar, self.t("calc"), x + 10, 8, 120,
                                        self.on_calculate, True)
        self._label(bar, self.t("unit"), x + 150, 12, 60, 22)
        cb = F.ComboBox()
        cb.DropDownStyle = F.ComboBoxStyle.DropDownList
        for u in UNITS:
            cb.Items.Add(u)
        cb.SelectedIndex = UNITS.index(self.unit)
        cb.Location = D.Point(x + 212, 10)
        cb.Size = D.Size(60, 24)
        cb.SelectedIndexChanged += self._on_unit
        bar.Controls.Add(cb)

        footer = F.Panel()
        footer.BackColor = col["band"]
        footer.Dock = F.DockStyle.Bottom
        footer.Size = D.Size(W, FOOTER_H)
        self.status_label = self._label(footer, self.status, PAD, 10,
                                        W - 300, 32, 9)
        self.status_label.Anchor = F.AnchorStyles.Left | \
            F.AnchorStyles.Right | F.AnchorStyles.Top
        self._set_status(self.status, self.status_error)
        b = self._button(footer, self.t("close"), W - PAD - 110, 11, 110,
                         self.form.Close)
        b.Anchor = F.AnchorStyles.Right | F.AnchorStyles.Top
        b = self._button(footer, self.t("copy"), W - PAD - 230, 11, 110,
                         self.on_copy)
        b.Anchor = F.AnchorStyles.Right | F.AnchorStyles.Top

        gs = F.Panel()
        gs.Dock = F.DockStyle.Bottom
        gs.Size = D.Size(W, GS_H)
        gs.BackColor = col["bg"]
        line = F.Panel()
        line.BackColor = col["line"]
        line.Dock = F.DockStyle.Top
        line.Height = 1
        gs.Controls.Add(line)
        self._build_gs(gs)

        body = F.Panel()
        body.Dock = F.DockStyle.Fill
        body.BackColor = col["bg"]
        self.table = F.Panel()
        self.table.AutoScroll = True
        self.table.BackColor = col["bg"]
        body.Controls.Add(self.table)
        self.plot = F.PictureBox()
        self.plot.SizeMode = F.PictureBoxSizeMode.Zoom
        self.plot.BackColor = col["bg"]
        body.Controls.Add(self.plot)
        self.body = body
        # Dock order: Fill last
        form.Controls.Add(body)
        form.Controls.Add(gs)
        form.Controls.Add(footer)
        form.Controls.Add(bar)
        form.Controls.Add(header)
        form.ResumeLayout()
        self._fill_table()
        self._layout_body()
        self._update_buttons()

    def _subtitle(self):
        if self.res is None:
            return self.t("sub_none")
        return u"{0}  ·  {1}".format(self.source,
                                         self.t("units").format(self.unit))

    def _build_gs(self, gs):
        D, F = self.D, self.F
        col = _colors()
        self._label(gs, self.t("gs_group").upper(), PAD, 8, 400, 18, 8.5,
                    True, col["accent"])
        self._label(gs, self.t("gs_name"), PAD, 34, 110, 22)
        tb = F.TextBox()
        tb.Text = self.name
        tb.Location = D.Point(PAD + 112, 33)
        tb.Size = D.Size(170, 24)

        def on_name(s, e):
            self.name = s.Text
        tb.TextChanged += on_name
        gs.Controls.Add(tb)
        self._label(gs, self.t("gs_comp"), PAD + 300, 34, 100, 22)
        cb = F.ComboBox()
        cb.DropDownStyle = F.ComboBoxStyle.DropDownList
        cb.Location = D.Point(PAD + 402, 33)
        cb.Size = D.Size(200, 24)
        cb.Items.Add(self.t("gs_none"))
        names = [c for c, _, is_line in self.components if is_line]
        for c in names:
            cb.Items.Add(c)
        cb.SelectedIndex = (names.index(self.component) + 1
                            if self.component in names else 0)

        def on_comp(s, e):
            i = s.SelectedIndex
            self.component = names[i - 1] if i > 0 else None
        cb.SelectedIndexChanged += on_comp
        gs.Controls.Add(cb)
        chk = click_safe("CheckBox")()
        chk.Text = self.t("gs_copy")
        chk.AutoSize = True
        chk.Checked = self.copy_mat
        chk.Location = D.Point(PAD + 620, 35)

        def on_copy_mat(s, e):
            self.copy_mat = s.Checked
        chk.CheckedChanged += on_copy_mat
        gs.Controls.Add(chk)
        chk = click_safe("CheckBox")()
        chk.Text = self.t("gs_store")
        chk.AutoSize = True
        chk.Checked = self.store
        chk.Location = D.Point(PAD, 68)

        def on_store(s, e):
            self.store = s.Checked
        chk.CheckedChanged += on_store
        gs.Controls.Add(chk)
        self.gs_button = self._button(gs, self.t("gs_make"),
                                      self.form.ClientSize.Width - PAD - 200,
                                      62, 200, self.on_create, True)
        self.gs_button.Anchor = self.F.AnchorStyles.Right | \
            self.F.AnchorStyles.Top

    def _layout_body(self):
        body = getattr(self, "body", None)
        if body is None or body.IsDisposed:
            return
        D = self.D
        w, h = body.ClientSize.Width, body.ClientSize.Height
        tw = min(TABLE_W, max(420, w // 2))
        self.table.Location = D.Point(0, 0)
        self.table.Size = D.Size(tw, h)
        self.plot.Location = D.Point(tw, 0)
        self.plot.Size = D.Size(max(10, w - tw), h)
        self._draw_plot()

    def _fill_table(self):
        D, F = self.D, self.F
        col = _colors()
        panel = self.table
        panel.Controls.Clear()
        self.copy_lines = []
        if self.res is None:
            return
        dec = u"," if self.lang == "nl" else u"."
        sections, notes = table_sections(self.res, self.plane, self.lang,
                                         self.unit, self.heal)
        width = TABLE_W - 2 * PAD - 20
        y = 8
        self.copy_lines = [self.t("title"), self._subtitle(), u""]
        for title, rows in sections:
            y += 6
            self._label(panel, title.upper(), PAD, y, width, 20, 8.0, True,
                        col["accent"])
            y += 22
            self.copy_lines.append(title)
            for i, (label, value, unit) in enumerate(rows):
                band = col["band"] if i % 2 else col["bg"]
                row = F.Panel()
                row.BackColor = band
                row.Location = D.Point(PAD, y)
                row.Size = D.Size(width, ROW_H)
                panel.Controls.Add(row)
                self._label(row, label, 6, 0, 250, ROW_H, 9, False,
                            col["muted"], back=band)
                if isinstance(value, tuple):
                    text = u"(" + u";  ".join(fmt(v, dec) for v in value) + \
                        u")"
                    copy = u"\t".join(raw(v, dec) for v in value)
                elif isinstance(value, basestring):
                    text = copy = value
                else:
                    text, copy = fmt(value, dec), raw(value, dec)
                self._label(row, text, 250, 0, width - 250 - 62, ROW_H, 9.5,
                            True, col["text"], D.ContentAlignment.MiddleRight,
                            band)
                self._label(row, unit, width - 58, 0, 58, ROW_H, 9, False,
                            col["muted"], back=band)
                self.copy_lines.append(u"{0}\t{1}\t{2}".format(label, copy,
                                                               unit))
                y += ROW_H
            self.copy_lines.append(u"")
            y += 2
        y += 6
        for n in notes:
            lb = self._label(panel, n, PAD, y, width, 34, 8.0, False,
                             col["muted"])
            lb.AutoEllipsis = False
            y += 34
            self.copy_lines.append(n)
        spacer = F.Panel()
        spacer.Location = D.Point(0, y + 8)
        spacer.Size = D.Size(1, 1)
        panel.Controls.Add(spacer)

    def _update_buttons(self):
        busy = self.busy is not None
        for b in (getattr(self, "calc_button", None),
                  getattr(self, "gs_button", None)):
            if b is not None and not b.IsDisposed:
                b.Enabled = not busy
        b = getattr(self, "gs_button", None)
        if b is not None and not b.IsDisposed and self.res is None:
            b.Enabled = False

    # ---------------- plot ----------------
    def _draw_plot(self):
        pic = getattr(self, "plot", None)
        if pic is None or pic.IsDisposed:
            return
        w, h = pic.ClientSize.Width, pic.ClientSize.Height
        if self.res is None or w < 50 or h < 50:
            pic.Image = None
            return
        old = pic.Image
        pic.Image = draw_plot(self.res, self.plane, self.lang, self.unit,
                              w, h)
        if old is not None:
            old.Dispose()

    # ---------------- events ----------------
    def _on_shown(self):
        try:
            self.components = self.caller.call(
                lambda: smw.components_info(self.mw))
            lines = [c for c, _, is_line in self.components if is_line]
            if self.component is None and len(lines) == 1:
                self.component = lines[0]
        except Exception as e:
            self._set_status(u"{0}".format(e), True)
        self.render()
        self.form.Activate()

    def _on_lang(self, sender, e):
        if not sender.Checked or sender.Tag == self.lang:
            return
        self.lang = sender.Tag
        self.form.BeginInvoke(self.F.MethodInvoker(self.render))

    def _on_mode(self, sender, e):
        if sender.Checked:
            self.mode = sender.Tag

    def _on_unit(self, sender, e):
        self.unit = UNITS[sender.SelectedIndex]
        self.form.BeginInvoke(self.F.MethodInvoker(self.render))

    def _on_closing(self, sender, e):
        if self.busy is not None:
            try:
                self.busy[0].Kill()
            except Exception:
                pass
            self.busy = None
        self.timer.Stop()

    def on_calculate(self):
        if self.busy is not None:
            return
        mode = self.mode

        def gather():
            faces = smw.read_selection(self.mw)
            job, plane = smw.section_input(self.mw, faces, mode)
            return faces, job, plane
        faces, job, plane = self.caller.call(gather)
        proc, dst = smw.start_analysis(job)
        self.busy = (proc, dst, time.time(), faces, job, plane)
        self._set_status(self.t("busy").format(0))
        self._update_buttons()
        self.timer.Start()

    def _on_tick(self, sender, e):
        if self.busy is None:
            self.timer.Stop()
            return
        proc, dst, start, faces, job, plane = self.busy
        elapsed = time.time() - start
        if not proc.HasExited:
            if elapsed > ANALYSIS_TIMEOUT:
                try:
                    proc.Kill()
                except Exception:
                    pass
            self._set_status(self.t("busy").format(int(elapsed)))
            return
        self.timer.Stop()
        self.busy = None
        try:
            res = smw.read_results(proc, dst)
        except Exception as ex:
            self._set_status(u"{0}".format(ex), True)
            self._update_buttons()
            return
        self.res, self.plane = res, plane
        # mesh faces: repairs from section_mecway; CAD face: from section_step
        # (copied into the result by section_analysis)
        self.heal = job.get("heal") or {"gaps_closed":
                                        res.get("gaps_closed") or []}
        if "step" in job:
            self.source = self.t("cad_faces").format(
                u", ".join(u"#{0}".format(i) for i in res.get("face_ids",
                                                             [])))
        else:
            self.source = self.t("faces").format(len(faces))
        self._set_status(u"")
        log("INFO: MecwaySectionProps: A = {0} m2, I11 = {1} m4, I22 = {2} "
            "m4, J = {3} m4 ({4} s).".format(
                res.get("area"), res.get("i11_c"), res.get("i22_c"),
                res.get("j"), "%.1f" % elapsed))
        self.render()

    def on_copy(self):
        lines = getattr(self, "copy_lines", None)
        if not lines:
            return
        try:
            self.F.Clipboard.SetText(u"\r\n".join(lines))
            self._set_status(self.t("copied"))
        except Exception as e:
            self._set_status(self.t("copy_fail").format(e), True)

    def on_create(self):
        F = self.F
        if self.res is None:
            self._set_status(self.t("gs_need"), True)
            return
        if not self.res.get("warping_computed"):
            self._set_status(self.t("gs_no_j"), True)
            return
        if self.store:
            answer = F.MessageBox.Show(self.form, self.t("gs_confirm"),
                                       PANEL_TITLE, F.MessageBoxButtons.YesNo,
                                       F.MessageBoxIcon.Question)
            if answer != F.DialogResult.Yes:
                return
        res, comp, store = self.res, self.component, self.store
        name = (self.name or u"Section").strip() or u"Section"
        copy_from = None
        if self.copy_mat and comp:
            copy_from = dict((c, m) for c, m, _ in self.components).get(comp)

        def work():
            mat = smw.create_general_section(self.mw, name, res, comp,
                                             copy_from)
            if store:
                smw.store_aster_line(self.mw, mat, res)
            return mat, smw.components_info(self.mw)
        try:
            mat, self.components = self.caller.call(work)
        except Exception as e:
            F.MessageBox.Show(self.form, self.t("gs_failed").format(e),
                              PANEL_TITLE, F.MessageBoxButtons.OK,
                              F.MessageBoxIcon.Error)
            self._set_status(self.t("gs_failed").format(e), True)
            return
        self._set_status(self.t("gs_done").format(
            mat, (self.t("gs_assigned").format(comp) if comp else u"") +
            (self.t("gs_stored") if store else u"")))


# ==========================================
# THE PLOT (System.Drawing, no matplotlib in Code-Aster's Python)
# ==========================================
def draw_plot(res, plane, lang, unit, w, h):
    """Bitmap w x h of the section: filled loops (even-odd), centroid,
    centroidal x/y axes, principal axes 1 (V) and 2 (W) with phi, shear
    centre, and a legend under it."""
    D, F = _forms()
    from System import Array
    from System.Drawing.Drawing2D import (AdjustableArrowCap, DashStyle,
                                          FillMode, GraphicsPath,
                                          SmoothingMode)
    col = _colors()
    dec = u"," if lang == "nl" else u"."
    L = scale_of(unit, 1)
    bmp = D.Bitmap(w, h)
    g = D.Graphics.FromImage(bmp)
    g.SmoothingMode = SmoothingMode.AntiAlias
    g.Clear(col["bg"])
    loops = res.get("loops") or []
    xs = [p[0] for lp in loops for p in lp]
    ys = [p[1] for lp in loops for p in lp]
    if not xs:
        g.Dispose()
        return bmp
    cx, cy = res["centroid"]
    size = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    legend_h = 6 * 18 + 16
    ph = max(60, h - legend_h)
    margin = 40
    half = 0.72 * size
    s = min((w - 2 * margin) / (2 * half), (ph - 2 * margin) / (2 * half))
    ox, oy = w / 2.0, ph / 2.0

    def P(x, y):
        return D.PointF(float(ox + (x - cx) * s), float(oy - (y - cy) * s))
    # grid
    grid = D.Pen(D.Color.FromArgb(235, 235, 235), 1.0)
    step = 10 ** math.floor(math.log10(size / 2.0))
    gx = math.floor((cx - half) / step) * step
    while gx < cx + half:
        a, b = P(gx, cy - half), P(gx, cy + half)
        g.DrawLine(grid, a, b)
        gx += step
    gy = math.floor((cy - half) / step) * step
    while gy < cy + half:
        a, b = P(cx - half, gy), P(cx + half, gy)
        g.DrawLine(grid, a, b)
        gy += step
    # section
    path = GraphicsPath(FillMode.Alternate)
    for lp in loops:
        if len(lp) >= 3:
            path.AddPolygon(Array[D.PointF]([P(x, y) for x, y in lp]))
    g.FillPath(D.SolidBrush(col["fill"]), path)
    g.DrawPath(D.Pen(col["edge"], 1.3), path)

    font = D.Font("Segoe UI", 9.0)
    bold = D.Font("Segoe UI", 10.0, D.FontStyle.Bold)
    arm = 0.62 * size

    def arrow(angle, color, label, dash, width, side=0.0):
        """side: label shifted this many pixels to the left of the arrow
        (keeps "1 (V)" and "y" apart when phi is 90 degrees)."""
        a = math.radians(angle)
        dx, dy = arm * math.cos(a), arm * math.sin(a)
        pen = D.Pen(color, width)
        if dash:
            pen.DashStyle = DashStyle.Dash
        g.DrawLine(pen, P(cx - dx, cy - dy), P(cx, cy))
        pen2 = D.Pen(color, width)
        if dash:
            pen2.DashStyle = DashStyle.Dash
        pen2.CustomEndCap = AdjustableArrowCap(4.0, 5.0)
        g.DrawLine(pen2, P(cx, cy), P(cx + dx, cy + dy))
        t = P(cx + 1.1 * dx, cy + 1.1 * dy)
        sz = g.MeasureString(label, bold)
        lx = t.X - sz.Width / 2 - side * math.sin(a)
        ly = t.Y - sz.Height / 2 - side * math.cos(a)
        g.DrawString(label, bold, D.SolidBrush(color), lx, ly)
    phi = res["phi_deg"]
    arrow(0.0, col["grey"], u"x", True, 1.0)
    arrow(90.0, col["grey"], u"y", True, 1.0)
    arrow(phi, col["ax1"], u"1 (V)", False, 1.6, 26.0)
    arrow(phi + 90.0, col["ax2"], u"2 (W)", False, 1.6, 26.0)
    r = 0.22 * size * s
    start, sweep = (0.0, phi) if phi >= 0 else (phi, -phi)
    # GDI+ angles run clockwise on screen (y down): negate
    g.DrawArc(D.Pen(col["ax1"], 1.0), float(ox - r), float(oy - r),
              float(2 * r), float(2 * r), float(-start - sweep), float(sweep))
    c = P(cx, cy)
    g.FillEllipse(D.Brushes.White, c.X - 6, c.Y - 6, 12, 12)
    g.DrawEllipse(D.Pen(D.Color.Black, 1.5), c.X - 6, c.Y - 6, 12, 12)
    g.DrawLine(D.Pen(D.Color.Black, 1.2), c.X - 6, c.Y, c.X + 6, c.Y)
    g.DrawLine(D.Pen(D.Color.Black, 1.2), c.X, c.Y - 6, c.X, c.Y + 6)
    sc = res.get("shear_centre") if res.get("warping_computed") else None
    if sc and math.hypot(sc[0] - cx, sc[1] - cy) > 1e-3 * size:
        q = P(sc[0], sc[1])
        pts = Array[D.PointF]([D.PointF(q.X, q.Y - 6), D.PointF(q.X + 6, q.Y),
                               D.PointF(q.X, q.Y + 6), D.PointF(q.X - 6, q.Y)])
        g.FillPolygon(D.SolidBrush(col["sc"]), pts)
        g.DrawPolygon(D.Pen(D.Color.Black, 1.0), pts)
    # legend
    U4 = unit_text(unit, 4)
    lines = [
        (D.Color.Black, u"○  {0} ({1}; {2}) {3}".format(
            tx("p_cent", lang), fmt(cx * L, dec), fmt(cy * L, dec), unit)),
        (col["grey"], u"- -  " + tx("p_axes", lang) + u"  (x = {0}, y = {1})"
         .format(smw.axis_name(plane["u"]), smw.axis_name(plane["v"]))),
        (col["ax1"], u"—  " + tx("p_ax1", lang).format(
            fmt(res["i11_c"] * scale_of(unit, 4), dec) + u" " + U4)),
        (col["ax2"], u"—  " + tx("p_ax2", lang).format(
            fmt(res["i22_c"] * scale_of(unit, 4), dec) + u" " + U4)),
        (col["ax1"], u"◠  " + tx("p_phi", lang).format(
            ("%.2f" % phi).replace(".", dec))),
    ]
    if sc:
        lines.append((col["sc"], u"◆  " + tx("p_sc", lang).format(
            fmt(sc[0] * L, dec), fmt(sc[1] * L, dec)) + u" " + unit))
    y = ph + 4
    for color, text in lines:
        g.DrawString(text, font, D.SolidBrush(color), 24.0, float(y))
        y += 18
    g.Dispose()
    return bmp
