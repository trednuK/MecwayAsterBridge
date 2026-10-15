# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Verificatiekader van de MecwayAsterBridge (CPython 3, ontwikkelgereedschap;
draait niet in Mecway).

Een testcase bouwt een Mecway-model (.liml) met Model en de mesh-generatoren
hieronder, laat de bridge het vertalen en Code-Aster het rekenen (_run_one.py,
zoals een run vanuit Mecway, maar zonder Mecway) en vergelijkt grootheden uit
de resultaten (Results) met een analytische of referentiewaarde (Check).

Gebruik: run_verificatie.py (alle tests_*.py in deze map).

Indeling van een testmodule tests_<groep>.py:
    from verif_lib import Case, Check, Model, hexmesh, ...
    def build_xxx():            # -> Model
        ...
    TESTS = [Case("LS-01", "Statisch", "titel", "lin_static_3d", build_xxx,
                  checks=[Check("tip-DZ", lambda r: r.at("displz", (L, 0, 0)),
                                ref=..., tol=0.01, unit="m", source="Roark ...")],
                  series=None, settings={}, general={})]

Eenheden: SI. Mecway-waarden in de .liml krijgen een eenheid ("210000 MPa").
"""
import os
import io
import re
import math
import base64
import struct
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(REPO, "Scripts")
MODELS = os.path.join(HERE, "modellen")
RESULTS = os.path.join(HERE, "resultaten")


# ==========================================
# MODEL (.liml)
# ==========================================
def _fmt(v):
    return "%.12g" % v


class Model(object):
    """
    Minimale .liml-schrijver. Knopen worden op coordinaat samengevoegd
    (node()), zodat aangrenzende elementen en middenknopen gedeeld worden.

    analysis : Mecway-analysetype (S30, L30, D31, T30, T31, V30, B30)
    timesteps: dict met attributen van <timesteps> (bijv. timeperiod="1 s",
               stepsize="0.1 s") of None
    attrs    : extra attributen van <analysis> (bijv. {"maxmode": 5}) of
               None
    """

    def __init__(self, analysis="S30", timesteps=None, solver=None,
                 attrs=None):
        self.analysis = analysis
        self.solver = solver
        self.attrs = attrs or {}
        self.timesteps = timesteps
        self.nodes = []             # [(x, y, z)], nid = index + 1
        self._index = {}
        self.elsets = []            # [(name, material, [(eid, shape, nids)])]
        self._elset = {}
        self.n_elem = 0
        self.mats = []              # xml-teksten
        self.items = []             # belastingen/voorwaarden (xml)
        self.selections = []        # xml-teksten
        self.nodesel = {}           # naam -> [nid] (voor Results)

    # --- knopen en elementen ---
    def node(self, x, y, z, tol=1e-9):
        key = (round(x / tol), round(y / tol), round(z / tol))
        nid = self._index.get(key)
        if nid is None:
            self.nodes.append((float(x), float(y), float(z)))
            nid = len(self.nodes)
            self._index[key] = nid
        return nid

    def elset(self, name, material):
        if name not in self._elset:
            self._elset[name] = (name, material, [])
            self.elsets.append(self._elset[name])
        return name

    def elem(self, elset, shape, nids, attrs=""):
        self.n_elem += 1
        self._elset[elset][2].append((self.n_elem, shape, list(nids), attrs))
        return self.n_elem

    # --- materialen, selecties, belastingen ---
    def mat(self, name, *lines):
        self.mats.append(u'  <mat name="{0}">\n{1}\n  </mat>'.format(
            name, "\n".join("    " + l for l in lines)))

    def node_selection(self, name, nids):
        nids = list(dict.fromkeys(nids))
        self.nodesel[name] = nids
        self.selections.append(
            u'  <nodeselection name="{0}">\n{1}\n  </nodeselection>'.format(
                name, "\n".join('    <node nid="%d" />' % n for n in nids)))

    def face_selection(self, name, faces):
        self.selections.append(
            u'  <faceselection name="{0}">\n{1}\n  </faceselection>'.format(
                name, "\n".join('    <face eid="%d" faceid="%d" />' % f
                                for f in faces)))

    def element_selection(self, name, eids):
        self.selections.append(
            u'  <elementselection name="{0}">\n{1}\n  </elementselection>'
            .format(name, "\n".join('    <element eid="%d" />' % e
                                    for e in eids)))

    def add(self, xml):
        """Ruwe XML van een belasting of voorwaarde (Mecway-formaat)."""
        self.items.append(u"  " + xml.strip())

    # --- schrijven ---
    def xml(self):
        a = u'  <analysis type="{0}"{1}{2} />'.format(
            self.analysis, ' solver="%s"' % self.solver if self.solver else "",
            "".join(' %s="%s"' % kv for kv in sorted(self.attrs.items())))
        out = [u'<liml version="33">', a]
        if self.timesteps:
            out.append(u"  <timesteps " + " ".join(
                u'{0}="{1}"'.format(k, v) for k, v in self.timesteps.items())
                + u" />")
        for i, (x, y, z) in enumerate(self.nodes):
            out.append(u'  <node nid="%d" x="%s" y="%s" z="%s" />'
                       % (i + 1, _fmt(x), _fmt(y), _fmt(z)))
        for name, mat, elems in self.elsets:
            out.append(u'  <elset name="{0}" material="{1}">'.format(name, mat))
            for eid, shape, nids, attrs in elems:
                out.append(u'    <elem eid="%d" shape="%s" nodes="%s"%s />' % (
                    eid, shape, " ".join(str(n) for n in nids),
                    (" " + attrs) if attrs else ""))
            out.append(u"  </elset>")
        out += self.items + self.mats + self.selections
        out.append(u"</liml>")
        return u"\n".join(out) + u"\n"

    def write(self, path):
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        io.open(path, "w", encoding="utf-8", newline="\n").write(self.xml())
        return path


# ==========================================
# MESH-GENERATOREN (parametrisch: geometrie via een afbeelding)
# ==========================================
# Hex: hoeken in (u, v, w) zoals Mecway/Code-Aster HEXA8; middenknopen
# HEXA20 in de volgorde van bridge_mesh._MID_EDGES (Mecway = Code-Aster).
_HEX_CORNERS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
_HEX_MID = [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 5), (2, 6), (3, 7),
            (4, 5), (5, 6), (6, 7), (4, 7)]
# faceid per kant van het parametrische blok (bridge_mesh._FACE_CORNERS)
HEX_FACE = {"w0": 1, "w1": 2, "v0": 3, "u1": 4, "v1": 5, "u0": 6}


def hexmesh(m, elset, nu, nv, nw, mapping, order=1):
    """
    Gestructureerd blok van hex8 (order 1) of hex20 (order 2). mapping(u,
    v, w) -> (x, y, z) met u, v, w in [0, 1]; middenknopen liggen op de
    afgebeelde parametrische middens (gekromde randen worden gevolgd).
    Let op: een niet-lineaire verdichting in de afbeelding (bijv. u**2)
    zet middenknopen buiten het midden (kwartpuntelementen, singulier);
    verdicht dan stuksgewijs lineair.
    Returns dict: "elems" {(i, j, k): eid}, "faces" {kant: [(eid, faceid)]}
    met kant u0/u1/v0/v1/w0/w1, "nodes" {kant: set(nid)}.
    """
    shape = "hex8" if order == 1 else "hex20"
    elems = {}
    faces = dict((s, []) for s in HEX_FACE)
    side_nodes = dict((s, set()) for s in HEX_FACE)
    for i in range(nu):
        for j in range(nv):
            for k in range(nw):
                def pt(a, b, c):
                    return ((i + a) / float(nu), (j + b) / float(nv),
                            (k + c) / float(nw))
                params = [pt(*c) for c in _HEX_CORNERS]
                if order == 2:
                    params += [tuple(0.5 * (params[p][d] + params[q][d])
                                     for d in range(3)) for p, q in _HEX_MID]
                nids = [m.node(*mapping(*p)) for p in params]
                eid = m.elem(elset, shape, nids)
                elems[(i, j, k)] = eid
                for side, cond, idx in (("u0", i == 0, 0), ("u1", i == nu - 1, 0),
                                        ("v0", j == 0, 1), ("v1", j == nv - 1, 1),
                                        ("w0", k == 0, 2), ("w1", k == nw - 1, 2)):
                    if cond:
                        faces[side].append((eid, HEX_FACE[side]))
                        val = 0.0 if side.endswith("0") else 1.0
                        for p, n in zip(params, nids):
                            if abs(p[idx] - val) < 1e-12:
                                side_nodes[side].add(n)
    return {"elems": elems, "faces": faces, "nodes": side_nodes}


def box(x0, x1, y0, y1, z0, z1):
    """Afbeelding voor een rechthoekig blok."""
    def f(u, v, w):
        return (x0 + u * (x1 - x0), y0 + v * (y1 - y0), z0 + w * (z1 - z0))
    return f


# Quad: hoeken (u, v) = (0,0),(1,0),(1,1),(0,1); quad8 in Mecway-volgorde
# hoek, midden, hoek, midden, ... (bridge_mesh: quad8 -> [0,2,4,6,1,3,5,7]).
QUAD_EDGE = {"v0": 1, "u1": 2, "v1": 3, "u0": 4}
QUAD_FACE_TOP = 5          # schaalvlak in de richting van de elementnormaal


def quadmesh(m, elset, nu, nv, mapping, order=1):
    """
    Gestructureerd schaalvlak van quad4 (order 1) of quad8 (order 2).
    mapping(u, v) -> (x, y, z). Returns dict: "elems" {(i, j): eid},
    "edges" {kant: [(eid, faceid)]} (u0/u1/v0/v1), "faces" [(eid, 5)],
    "nodes" {kant: set(nid)}.
    """
    shape = "quad4" if order == 1 else "quad8"
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]
    elems = {}
    edges = dict((s, []) for s in QUAD_EDGE)
    side_nodes = dict((s, set()) for s in QUAD_EDGE)
    for i in range(nu):
        for j in range(nv):
            def pt(a, b):
                return ((i + a) / float(nu), (j + b) / float(nv))
            c = [pt(*p) for p in corners]
            if order == 1:
                params = c
            else:
                params = []
                for k in range(4):
                    a, b = c[k], c[(k + 1) % 4]
                    params += [a, (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))]
            nids = [m.node(*mapping(*p)) for p in params]
            eid = m.elem(elset, shape, nids)
            elems[(i, j)] = eid
            for side, cond, idx in (("u0", i == 0, 0), ("u1", i == nu - 1, 0),
                                    ("v0", j == 0, 1), ("v1", j == nv - 1, 1)):
                if cond:
                    edges[side].append((eid, QUAD_EDGE[side]))
                    val = 0.0 if side.endswith("0") else 1.0
                    for p, n in zip(params, nids):
                        if abs(p[idx] - val) < 1e-12:
                            side_nodes[side].add(n)
    return {"elems": elems, "edges": edges,
            "faces": [(e, QUAD_FACE_TOP) for e in elems.values()],
            "nodes": side_nodes}


def rect(x0, x1, y0, y1, z=0.0):
    """Afbeelding voor een rechthoekige plaat in het vlak z = constant."""
    def f(u, v):
        return (x0 + u * (x1 - x0), y0 + v * (y1 - y0), z)
    return f


def linemesh(m, elset, n, p0, p1):
    """n line2-elementen van p0 naar p1. Returns (eids, nids)."""
    nids = [m.node(*[p0[d] + (p1[d] - p0[d]) * i / float(n) for d in range(3)])
            for i in range(n + 1)]
    eids = [m.elem(elset, "line2", [nids[i], nids[i + 1]]) for i in range(n)]
    return eids, nids


# ==========================================
# RESULTATEN (<model>_<run_id>_results.xml, Mecway-formaat)
# ==========================================
def _values(nv):
    vd = nv.find("valuesdouble")
    vs = nv.find("valuessingle")
    if vd is not None and vd.text:
        b = base64.b64decode(vd.text)
        return struct.unpack("<%dd" % (len(b) // 8), b)
    b = base64.b64decode(vs.text)
    return struct.unpack("<%df" % (len(b) // 4), b)


def _time(text):
    if text is None:
        return 0.0
    m_ = re.match(r"\s*([-+0-9.eE]+)\s*(\w*)", text)
    v = float(m_.group(1))
    unit = m_.group(2)
    return v * {"ms": 1e-3, "min": 60.0}.get(unit, 1.0)


class Results(object):
    """
    Knoopresultaten per tijdstap uit een resultaatbestand van de bridge,
    met de knoopcoordinaten en knoopselecties uit het model.
      steps : [(t, {variabele: {nid: waarde}})], oplopend in t
      modes : {mode-id: frequentie [Hz] of kniklastfactor} bij een modale
              of knikanalyse (<mode id=".." frequency="f Hz"> of
              bucklingfactor=".."); de stappen hebben dan t = mode-id.
      elems : {t: {variabele: {eid: [waarde per knoop van het element]}}}
              (<elementnodevariable>; elem())
    """

    def __init__(self, results_path, model):
        txt = io.open(results_path, encoding="utf-8").read()
        root = ET.fromstring("<r>" + txt + "</r>")
        steps = {}
        self.elems = {}
        sizes = dict((e[0], len(e[2])) for es in getattr(model, "elsets", [])
                     for e in es[2])
        self.modes = {}
        self.globals = {}       # {mode-id: {naam: waarde}} (<globalvariable>)
        for res in root.iter("results"):
            ids, eids = {}, {}
            for tag, out in (("nodeids", ids), ("elementnodeids", eids)):
                for e in res.findall(tag):
                    b = base64.b64decode(e.text)
                    out[e.get("name")] = struct.unpack("<%di" % (len(b) // 4),
                                                       b)
            for st in (res.findall("timestep") or res.findall("mode")
                       or [res]):
                if st.tag == "mode":
                    t = float(st.get("id"))
                    val = st.get("frequency") or st.get("bucklingfactor")
                    self.modes[int(st.get("id"))] = float(val.split()[0])
                    self.globals[int(st.get("id"))] = dict(
                        (g.get("name"), float(g.text))
                        for g in st.findall("globalvariable"))
                else:
                    t = _time(st.get("time"))
                d = steps.setdefault(t, {})
                for nv in st.findall("nodevariable"):
                    n = nv.get("name")
                    nid = ids.get(n) or ids[list(ids)[0]]
                    d[n] = dict(zip(nid, _values(nv)))
                de = self.elems.setdefault(t, {})
                for ev in (st.findall("elementnodevariable")
                           if sizes else ()):
                    vals, k, out = _values(ev), 0, {}
                    for eid in eids.get(ev.get("name"), ()):
                        out[eid] = list(vals[k:k + sizes[eid]])
                        k += sizes[eid]
                    de[ev.get("name")] = out
        self.steps = sorted(steps.items())
        self.model = model
        self.mess = None            # pad van de .mess (run_verificatie)
        self._summary = None

    # --- opzoeken ---
    def mode(self, k):
        """Frequentie [Hz] of kniklastfactor van mode k (vanaf 1)."""
        return self.modes[k]

    def summary(self):
        """{mode: {parameter: waarde}} en "massa" uit de BRIDGE_MODE- en
        BRIDGE_MASSA-regels van de .mess (aster_results_export.print_modes;
        zelfde parser als de bridge, bridge_results_liml)."""
        if self._summary is None:
            import sys
            if SCRIPTS not in sys.path:
                sys.path.insert(0, SCRIPTS)
            from bridge_results_liml import read_mode_summary
            self._summary = read_mode_summary(self.mess) if self.mess else {}
        return self._summary

    def mode_global(self, k, name):
        """Mecway-<globalvariable> van mode k in het resultaatbestand, bijv.
        modaleffectivemassfractionty (aster_results_export, S12)."""
        return self.globals[k][name]

    def mode_param(self, k, key):
        """Parameter van mode k uit de .mess, bijv. MASS_EFFE_UN_DRZ."""
        return self.summary()[k][key]

    def mode_sum(self, key, modes=None):
        """Som van een parameter over de modes (None = alle)."""
        s = self.summary()
        return sum(s[k][key] for k in s if k != "massa" and
                   (modes is None or k in modes))

    def mass_param(self, key):
        """Uit BRIDGE_MASSA: M, JX, JY, JZ, JZX, JZY, JZZ (SI)."""
        return self.summary()["massa"][key]

    def times(self):
        return [t for t, _d in self.steps]

    def step(self, time=None):
        """Variabelen van de tijdstap het dichtst bij time (None = laatste)."""
        if time is None:
            return self.steps[-1][1]
        return min(self.steps, key=lambda s: abs(s[0] - time))[1]

    def nearest(self, point):
        """nid van de knoop het dichtst bij point."""
        best, nid = None, None
        for i, p in enumerate(self.model.nodes):
            d = sum((p[k] - point[k]) ** 2 for k in range(3))
            if best is None or d < best:
                best, nid = d, i + 1
        return nid

    def at(self, var, point, time=None):
        """Waarde van var in de knoop het dichtst bij point."""
        return self.step(time)[var][self.nearest(point)]

    def node(self, var, nid, time=None):
        return self.step(time)[var][nid]

    def elem(self, var, time=None):
        """{eid: [waarde per knoop, in de volgorde van het element]} van
        een elementnodevariable (leeg als die ontbreekt)."""
        ts = sorted(self.elems)
        if not ts:
            return {}
        t = ts[-1] if time is None else min(ts, key=lambda s: abs(s - time))
        return self.elems[t].get(var, {})

    def total(self, var, selection, time=None):
        """Som van var over een knoopselectie (bijv. reactiekrachten)."""
        d = self.step(time)[var]
        return sum(d.get(n, 0.0) for n in self.model.nodesel[selection])

    def mean(self, var, selection, time=None):
        """Gemiddelde van var over een knoopselectie."""
        d = self.step(time)[var]
        nids = self.model.nodesel[selection]
        return sum(d[n] for n in nids) / float(len(nids))

    def extreme(self, var, time=None, fn=max):
        return fn(self.step(time)[var].values())

    def history(self, var, point):
        """[(t, waarde)] in de knoop het dichtst bij point."""
        nid = self.nearest(point)
        return [(t, d[var][nid]) for t, d in self.steps if var in d]

    def argmax(self, var, time=None):
        """Coordinaten van de knoop met de grootste waarde van var."""
        d = self.step(time)[var]
        nid = max(d, key=lambda n: d[n])
        return self.model.nodes[nid - 1]


def error_summary(r):
    """
    Globale foutschatting (CALC_ERREUR ERME) van de run van Results r: de
    laatste dict van bridge_results_liml.read_error_summary ("rel" in %,
    "abs", "sigma", ...). r.mess zet run_verificatie.run_case. ValueError
    als de .mess geen foutschatting heeft.
    """
    import sys
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    import bridge_results_liml
    found = bridge_results_liml.read_error_summary(getattr(r, "mess", None))
    if not found:
        raise ValueError("geen foutschatting in de .mess")
    return found[-1]


# ==========================================
# TESTDEFINITIE
# ==========================================
class Check(object):
    """
    Een vergeleken grootheid. value(r) haalt de FEM-waarde uit Results r.
    tol: toegestane relatieve afwijking |fem - ref| / |ref|; of tol_abs
    (absoluut, bijv. bij ref = 0). source: bron van de referentiewaarde.
    """

    def __init__(self, name, value, ref, tol=None, tol_abs=None, unit="",
                 source="", in_series=True, known=None):
        self.name, self.value, self.ref = name, value, ref
        self.tol, self.tol_abs, self.unit, self.source = tol, tol_abs, unit, source
        # False: niet in de mesh-convergentietabel (geen discretisatiefout,
        # bijv. een vergelijking met een replica van hetzelfde schema)
        self.in_series = in_series
        # bekende beperking (bijv. "KNOWN_BUGS 43"): een afwijking telt
        # dan als BEKEND, niet als NOK
        self.known = known

    def evaluate(self, r):
        fem = float(self.value(r))
        dev = fem - self.ref
        rel = dev / abs(self.ref) if self.ref else None
        if self.tol_abs is not None:
            ok = abs(dev) <= self.tol_abs
        else:
            ok = rel is not None and abs(rel) <= self.tol
        return {"name": self.name, "fem": fem, "ref": self.ref, "rel": rel,
                "dev": dev, "ok": ok, "unit": self.unit,
                "tol": self.tol, "tol_abs": self.tol_abs, "source": self.source,
                "in_series": self.in_series, "known": self.known}


class Case(object):
    """
    Een testcase.
      id, group, title : bijv. "LS-01", "Lineair statisch", "Ingeklemde balk"
      analysis         : bridge-analyse (lin_static_3d, nonlin_static_3d,
                         dyna_impl_3d, dyna_expl_3d, ther_3d)
      build            : functie -> Model (wordt modellen/<id>.liml)
      checks           : [Check]
      settings         : analyse-instellingen (CONFIG_BRIDGE["analyses"][..])
      general          : algemene instellingen (bijv. elem_hex8)
      series, h        : naam van een mesh-convergentiereeks en de
                         elementgrootte (voor de convergentietabel)
      timeout          : seconden voor de Code-Aster-run
      note             : korte toelichting voor het rapport
    """

    def __init__(self, id, group, title, analysis, build, checks,
                 settings=None, general=None, series=None, h=None,
                 timeout=1800, note=""):
        self.id, self.group, self.title = id, group, title
        self.analysis, self.build, self.checks = analysis, build, checks
        self.settings = settings or {}
        self.general = general or {}
        self.series, self.h, self.timeout, self.note = series, h, timeout, note

    def liml_path(self):
        return os.path.join(MODELS, self.id + ".liml")
