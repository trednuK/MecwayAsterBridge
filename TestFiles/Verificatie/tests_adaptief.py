# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Adaptieve verfijning (stap S7; Scripts/bridge_adapt.py, docs/Foutschatter.md
par. 6). Toelichting: docs/Verificatie.md hoofdstuk Adaptieve verfijning
(AD).

Model: plaat met een rond gat onder trek, eindige breedte; kwart van de
plaat (symmetrie x = 0 en y = 0), hex20. Gat d = 2r = 20 mm, breedte W =
100 mm (d/W = 0,2), lengte 300 mm (3 W), trek 100 MPa op het eindvlak.
Dik: een plak van 10 mm met symmetrie op beide z-vlakken (vlakke rek, 3D;
de spanningen van een vlak probleem met randlasten hangen niet af van nu,
dus vlakke rek en vlakke spanning hebben dezelfde Kt; nagerekend: AD-01
n = 32 -0,14%, dunne plaat 1 mm in vlakke spanning n = 32 -0,08%). Kt_n =
sigma_xx in (0, r) / sigma_nom met sigma_nom = sigma W / (W - d) (netto
doorsnede).

Referentie: Peterson (Pilkey & Pilkey 2008, Peterson's Stress
Concentration Factors, 3e druk, chart 4.1, fit op Howland 1930): Kt_n = 2
+ 0,284 (1 - d/W) - 0,600 (1 - d/W)^2 + 1,32 (1 - d/W)^3 = 2,5190; ter
controle Heywood (1952) 2 + (1 - d/W)^3 = 2,512 en Roark (7e druk, tabel
17.1 geval 2a) 3,00 - 3,13 d/W + 3,66 (d/W)^2 - 1,53 (d/W)^3 = 2,508.
Formules overgenomen; de boeken zelf zijn niet lokaal ingezien.

AD-01-n1..n32  uniform in het vlak (1 laag in de dikte; in vlakke rek
               verandert het aantal lagen niets): het grove mesh (12 hex20)
               en de globale verfijningen. Mecway's Refine x2 op alles
               geeft dezelfde Kt met 8 x zoveel elementen per stap (ook in
               de dikte): 12 x 8^k elementen voor n = 2^k.
AD-02          de verfijningslus zoals in Mecway (bridge_adapt.after_run
               en bridge_adapt.refine_in_mecway): grof mesh -> run ->
               keuze -> mw.refine_x2 in headless Mecway (mecway.exe
               <model> script) -> run ... tot het doel. De tussenmodellen
               staan als modellen/AD-02-L<k>.liml (in Mecway te openen).
               Zonder Mecway (mecway.exe niet gevonden of fout) valt de lus
               terug op de opgeslagen tussenmodellen, maar dan faalt de
               controle "lus met Mecway gedraaid" (FOUT/NOK, nooit OK).
AD-03          voorwaarde op een knoopselectie: de lus stopt met een ERROR
               voor het verfijnen (Mecway verfijnt knoopselecties niet mee).
"""
import glob
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import verif_lib as V
from verif_lib import Case, Check, Model, hexmesh, box

if V.SCRIPTS not in sys.path:
    sys.path.insert(0, V.SCRIPTS)

GROUP = "Adaptieve verfijning"
MECWAY = r"C:\Program Files\Mecway\mecway.exe"

R = 0.010                   # m, straal van het gat
WH = 0.050                  # m, halve breedte (W = 0,1)
LH = 0.150                  # m, halve lengte (L = 3 W)
TZ = 0.0005                 # m, halve dikte (t = 1 mm)
TZ_STRAIN = 0.010           # m, dikte van de plak in vlakke rek
SIG = 100.0e6               # Pa, trek op het eindvlak
BETA = 2 * R / (2 * WH)     # d/W
SIG_NOM = SIG / (1.0 - BETA)
KT_PETERSON = (2.0 + 0.284 * (1 - BETA) - 0.600 * (1 - BETA) ** 2 +
               1.32 * (1 - BETA) ** 3)
KT_HEYWOOD = 2.0 + (1 - BETA) ** 3
KT_ROARK = 3.00 - 3.13 * BETA + 3.66 * BETA ** 2 - 1.53 * BETA ** 3
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')

# Instellingen van de lus in AD-02 (de standaard van de bridge behalve
# adapt_refine zelf)
ADAPT = {"adapt_refine": True}


# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------
def _blocks(tz):
    """Afbeeldingen van de ring rond het gat (u radiaal, v hoek, w dikte):
    blok A theta 0..45 graden -> rand x = WH, blok B 45..90 -> rand y =
    WH; tz = (halve) dikte."""
    def block_a(u, v, w):
        t = v * math.pi / 4
        p0 = (R * math.cos(t), R * math.sin(t))
        p1 = (WH, WH * v)
        return (p0[0] + u * (p1[0] - p0[0]), p0[1] + u * (p1[1] - p0[1]),
                w * tz)

    def block_b(u, v, w):
        t = math.pi / 4 + v * math.pi / 4
        p0 = (R * math.cos(t), R * math.sin(t))
        p1 = (WH * (1 - v), WH)
        return (p0[0] + u * (p1[0] - p0[0]), p0[1] + u * (p1[1] - p0[1]),
                w * tz)
    return block_a, block_b


# Kuhn-splitsing van een kubus in 6 tetraeders langs de diagonaal
# (0,0,0)-(1,1,1): per volgorde van de assen een pad van hoek naar hoek.
# Conform tussen buurcellen (Freudenthal) en tussen de blokken, omdat hun
# (u, v, w) op de gedeelde vlakken dezelfde richting hebben.
_KUHN = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
_TET_MID = [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]   # TETRA10
_TET_FACES = {1: (0, 2, 1), 2: (0, 1, 3), 3: (2, 3, 1), 4: (0, 3, 2)}


def tetmesh(m, elset, nu, nv, nw, mapping):
    """
    Gestructureerd blok van tet10 (6 per cel, Kuhn), middenknopen op de
    afgebeelde parametrische middens (gekromde randen gevolgd). Zelfde
    returnwaarde als verif_lib.hexmesh ("faces" {kant: [(eid, faceid)]},
    "nodes" {kant: set(nid)}).
    """
    faces = dict((s, []) for s in V.HEX_FACE)
    side_nodes = dict((s, set()) for s in V.HEX_FACE)
    for i in range(nu):
        for j in range(nv):
            for k in range(nw):
                for perm in _KUHN:
                    c = [0, 0, 0]
                    pars = [(i / float(nu), j / float(nv), k / float(nw))]
                    for ax in perm:
                        c[ax] += 1
                        pars.append(((i + c[0]) / float(nu),
                                     (j + c[1]) / float(nv),
                                     (k + c[2]) / float(nw)))
                    xyz = [mapping(*p) for p in pars]
                    d = [[xyz[q][r] - xyz[0][r] for r in range(3)]
                         for q in (1, 2, 3)]
                    det = (d[0][0] * (d[1][1] * d[2][2] - d[1][2] * d[2][1]) -
                           d[0][1] * (d[1][0] * d[2][2] - d[1][2] * d[2][0]) +
                           d[0][2] * (d[1][0] * d[2][1] - d[1][1] * d[2][0]))
                    if det < 0:
                        pars[1], pars[2] = pars[2], pars[1]
                    pars += [tuple(0.5 * (pars[a][r] + pars[b][r])
                                   for r in range(3)) for a, b in _TET_MID]
                    nids = [m.node(*mapping(*p)) for p in pars]
                    eid = m.elem(elset, "tet10", nids)
                    for fid, cs in _TET_FACES.items():
                        for side, idx, val in (("u0", 0, 0.0), ("u1", 0, 1.0),
                                               ("v0", 1, 0.0), ("v1", 1, 1.0),
                                               ("w0", 2, 0.0), ("w1", 2, 1.0)):
                            if all(abs(pars[q][idx] - val) < 1e-12
                                   for q in cs):
                                faces[side].append((eid, fid))
                                side_nodes[side].update(
                                    n for p, n in zip(pars, nids)
                                    if abs(p[idx] - val) < 1e-12)
    return {"faces": faces, "nodes": side_nodes}


def build_plate(n, nz=None, shape="hex20", strain=False):
    """Kwart plaat; n = 1 grof (12 hex20 of 72 tet10), n = 2, 4, 8 =
    uniform verfijnd (zoals refine_x2 op alle elementen); nz = aantal
    lagen in de dikte (standaard n). strain=False: dunne plaat (halve
    dikte TZ, symmetrie in z = 0, vlakke spanning); True: dikke plak
    (dikte TZ_STRAIN) met beide z-vlakken symmetrie (vlakke rek)."""
    nz = n if nz is None else nz
    tz = TZ_STRAIN if strain else TZ
    block_a, block_b = _blocks(tz)

    def build():
        m = Model("S30")
        m.elset("Plaat", "Staal")
        if shape == "tet10":
            def mesh(*a):
                return tetmesh(*a)
        else:
            def mesh(*a):
                return hexmesh(*a, order=2)
        a = mesh(m, "Plaat", 2 * n, 2 * n, nz, block_a)
        b = mesh(m, "Plaat", 2 * n, 2 * n, nz, block_b)
        c = mesh(m, "Plaat", 2 * n, 2 * n, nz, box(WH, LH, 0, WH, 0, tz))
        m.mat("Staal", STEEL)
        m.face_selection("SymX", b["faces"]["v1"])
        m.face_selection("SymY", a["faces"]["v0"] + c["faces"]["v0"])
        sides = ("w0", "w1") if strain else ("w0",)
        m.face_selection("SymZ", [f for blk in (a, b, c) for w in sides
                                  for f in blk["faces"][w]])
        m.face_selection("Trek", c["faces"]["u1"])
        m.node_selection("Gatrand", sorted(a["nodes"]["u0"] |
                                           b["nodes"]["u0"]))
        m.add('<symmetry selection="SymX"><x>1</x><y>0</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymY"><x>0</x><y>1</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymZ"><x>0</x><y>0</y><z>1</z>'
              '</symmetry>')
        m.add('<traction selection="Trek"><x>%g Pa</x><y>0 Pa</y>'
              '<z>0 Pa</z></traction>' % SIG)
        return m
    return build


class LimlModel(object):
    """Een bestaand .liml-model (van Mecway) met wat Results en
    run_verificatie van een Model gebruiken: nodes, n_elem, nodesel,
    write()."""

    def __init__(self, path):
        self.path = path
        root = ET.parse(path).getroot()
        nodes = {}
        for nd in root.findall("node"):
            nodes[int(nd.get("nid"))] = (float(nd.get("x")),
                                         float(nd.get("y")),
                                         float(nd.get("z")))
        far = (1e30, 1e30, 1e30)
        self.nodes = [nodes.get(i, far) for i in range(1, max(nodes) + 1)]
        self.elements = []
        for es in root.findall("elset"):
            for el in es.findall("elem"):
                self.elements.append((int(el.get("eid")), el.get("shape"),
                                      [int(x) for x in
                                       el.get("nodes").split()]))
        self.n_elem = len(self.elements)
        self.nodesel = {}
        for ns in root.findall("nodeselection"):
            self.nodesel[ns.get("name")] = [int(x.get("nid"))
                                            for x in ns.findall("node")]

    def write(self, path):
        if os.path.abspath(path) != os.path.abspath(self.path):
            shutil.copy(self.path, path)
        return path

    def centroid(self, eid_shape_nodes):
        _eid, shape, nids = eid_shape_nodes
        corners = {"hex": 8, "tet": 4, "pyr": 5, "wed": 6}[shape[:3]]
        pts = [self.nodes[n - 1] for n in nids[:corners]]
        return tuple(sum(p[d] for p in pts) / len(pts) for d in range(3))


# ------------------------------------------------------------------
# Lus: bridge-run (zoals run_verificatie), keuze, Mecway-verfijning
# ------------------------------------------------------------------
def _work_root():
    return os.environ.get("VERIF_WORK") or os.path.join(
        tempfile.gettempdir(), "mab_verificatie")


def _bridge_run(liml, work, settings):
    """Bridge + Code-Aster op liml in werkmap work (_run_one.py). Returns
    run.json als dict."""
    cfg = work + ".json"
    json.dump({"settings": settings, "general": {}, "timeout": 1800},
              open(cfg, "w"))
    subprocess.call([sys.executable, os.path.join(V.HERE, "_run_one.py"),
                     work, liml, "lin_static_3d", cfg])
    path = os.path.join(work, "run.json")
    return json.load(io.open(path, encoding="utf-8")) if \
        os.path.isfile(path) else {}


_REFINE_SCRIPT = u'''# Gegenereerd door tests_adaptief.py (headless Mecway)
import sys
sys.path.insert(0, r"{scripts}")
import bridge_utils
bridge_utils.CONFIG_BRIDGE["work_dir"] = r"{work}"
import bridge_adapt
f = open(r"{status}", "w")
try:
    n = bridge_adapt.refine_in_mecway(mw, {eids!r})
    mw.save_as(r"{out}")
    f.write("OK %s\\n" % n)
except Exception as e:
    f.write("FOUT %r\\n" % e)
f.close()
'''


def mecway_refine(liml_in, liml_out, eids, work):
    """bridge_adapt.refine_in_mecway(mw, eids) in headless Mecway op
    liml_in; resultaat liml_out. Returns True als het gelukt is."""
    if not os.path.isfile(MECWAY):
        return False
    if not os.path.isdir(work):
        os.makedirs(work)
    script = os.path.join(work, "verfijn.py")
    status = os.path.join(work, "verfijn_status.txt")
    for p in (status, liml_out):
        if os.path.exists(p):
            os.remove(p)
    io.open(script, "w", encoding="utf-8").write(_REFINE_SCRIPT.format(
        scripts=V.SCRIPTS, work=work, status=status, out=liml_out,
        eids=sorted(eids)))
    try:
        subprocess.call([MECWAY, liml_in, "script", script], timeout=600)
    except Exception:
        return False
    ok = (os.path.isfile(status) and
          io.open(status).read().startswith("OK") and
          os.path.isfile(liml_out))
    return ok


def _model_data(liml, work):
    import bridge_utils as u
    from bridge_from_liml import extract_aster_data_from_liml
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["language"] = "nl"
    u.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
    u.set_run_log(None)
    return extract_aster_data_from_liml(liml)


def kt(r):
    """Kt_n uit sigma_xx in de knoop op (0, r, 0)."""
    return r.at("stressxx", (0.0, R, 0.0)) / SIG_NOM


_LOOPS = {}         # case-id -> lijst van lussen (gevuld door adapt_loop)


def adapt_loop(case_id, build0, settings=None):
    """
    De lus van MecwayAsterBridgeMain (_adapt_step) offline: per lus k het
    model modellen/<case_id>-L<k>.liml door de bridge en Code-Aster,
    bridge_adapt.after_run beslist, headless Mecway verfijnt. Returns de
    build-functie van de case: het laatste model (dat run_verificatie nog
    een keer rekent en controleert). Per lus in _LOOPS[case_id]: n_elem,
    rel, Kt, verfijnde elementen (middelpunten).
    """
    import bridge_adapt
    import bridge_results_liml
    import bridge_utils as u

    def build():
        an = dict(u.CONFIG_BRIDGE["analyses"]["lin_static_3d"])
        an.update(ADAPT)
        an.update(settings or {})
        cfg = bridge_adapt.adapt_settings(an)
        root = os.path.join(_work_root(), case_id + "-lus")
        if not os.path.isdir(root):
            os.makedirs(root)
        history, loops = [], []
        _LOOPS[case_id] = loops
        liml = build0().write(os.path.join(V.MODELS, case_id + "-L0.liml"))
        k = 0
        while True:
            work = os.path.join(root, "L%d" % k)
            run = _bridge_run(liml, work, {})
            model = LimlModel(liml)
            rec = {"liml": liml, "n_elem": model.n_elem, "kt": None,
                   "rel": None, "refined": [],
                   "quality": min(bridge_adapt.scaled_jacobian(
                       s, [model.nodes[n - 1] for n in nids])
                       for _e, s, nids in model.elements)}
            loops.append(rec)
            if not run.get("results"):
                break
            res = V.Results(run["results"], model)
            rec["kt"] = kt(res)
            summ = bridge_results_liml.read_error_summary(run.get("mess"))
            md = _model_data(liml, work)
            step = bridge_adapt.after_run(history, cfg, md, run["results"],
                                          summ[-1] if summ else None)
            rec["rel"] = history[-1]["rel"]
            rec["notes"] = step["notes"]
            if not step["refine"]:
                break
            by_id = dict((e[0], e) for e in model.elements)
            rec["refined"] = [model.centroid(by_id[e])
                              for e in step["elements"]]
            nxt = os.path.join(V.MODELS, "%s-L%d.liml" % (case_id, k + 1))
            rec["mecway"] = mecway_refine(liml, nxt, step["elements"], work)
            if not rec["mecway"]:
                if not os.path.isfile(nxt):
                    raise RuntimeError("Mecway-verfijning mislukt en geen "
                                       "opgeslagen model %s" % nxt)
                rec["note"] = "opgeslagen model (Mecway niet beschikbaar)"
            liml = nxt
            k += 1
        # Laatste model: run_verificatie rekent het nog een keer
        loops[-1]["final"] = True
        return LimlModel(liml)
    return build


# ------------------------------------------------------------------
# Cases
# ------------------------------------------------------------------
# Uniforme reeks (AD-01): n -> tolerantie van Kt (gemeten fouten -27,2 /
# -14,3 / -6,3 / -2,5 / -0,75 / -0,14%; de reeks laat de convergentie naar
# Peterson zien, het klaar-criterium 2% geldt vanaf n = 16).
_UNIFORM = ((1, 0.30), (2, 0.16), (4, 0.08), (8, 0.03), (16, 0.02),
            (32, 0.005))
# Lus AD-02: doel 1,5% (een piekspanning vraagt een kleinere globale fout
# dan de standaard 2%: docs/Foutschatter.md par. 6.3), verder de
# standaardinstellingen van de bridge.
AD02 = {"adapt_target_error": 1.5, "adapt_max_loops": 6}


def _refine_x2_elements(n):
    """Elementen na globale Refine x2 van het grove mesh (12 hex20) tot
    in-plane n: 12 x 8^k, n = 2^k."""
    return 12 * 8 ** int(round(math.log(n, 2)))


def _uniform_needed(r, tol=0.02):
    """Elementen die uniform verfijnen (Refine x2 op alles) nodig heeft
    voor |Kt - Peterson| <= tol: de eerste AD-01-case binnen tol (uit
    dezelfde werkmap; die draaien eerder)."""
    root = os.path.dirname(os.path.dirname(r.mess))
    for n, _t in _UNIFORM:
        res = glob.glob(os.path.join(root, "AD-01-n%d" % n,
                                     "*_results.xml"))
        if not res:
            raise ValueError("AD-01-n%d niet gedraaid" % n)
        k = kt(V.Results(res[0], build_plate(n, 1, strain=True)()))
        if abs(k / KT_PETERSON - 1.0) <= tol:
            return _refine_x2_elements(n)
    raise ValueError("uniform binnen %g niet bereikt" % tol)


def _loops(case_id):
    loops = _LOOPS.get(case_id)
    if not loops:
        raise ValueError("lus van %s niet gedraaid" % case_id)
    return loops


def _mecway_fraction(case_id):
    """Fractie van de verfijningsstappen van de lus die echt door
    headless Mecway zijn gedaan (1 = alle). Een stap die terugviel op het
    opgeslagen tussenmodel (Mecway niet gevonden of mislukt) telt niet
    mee, zodat de test dan faalt en niet stil op oude modellen verder
    gaat."""
    steps = [l for l in _loops(case_id) if l["refined"]]
    if not steps:
        raise ValueError("geen verfijningsstap in de lus van %s" % case_id)
    return sum(1 for l in steps if l.get("mecway")) / float(len(steps))


def _max_ratio(case_id):
    """Grootste rel_k / rel_(k-1) over de lussen (< 1: daalt elke lus)."""
    rel = [l["rel"] for l in _loops(case_id)]
    return max(b / a for a, b in zip(rel, rel[1:]))


def _near_hole(case_id, radius=3 * R):
    """Fractie van alle verfijnde elementen (alle lussen) met het
    middelpunt binnen radius van het midden van het gat."""
    pts = [c for l in _loops(case_id) for c in l["refined"]]
    return sum(1 for c in pts if math.hypot(c[0], c[1]) < radius) / \
        float(len(pts))


def _eta_sum(r):
    """sqrt(som eta_e^2) uit het resultaatbestand / globale eta (.mess):
    de fout per element die de lus leest, telt op tot de globale."""
    import bridge_adapt
    res = glob.glob(os.path.join(os.path.dirname(r.mess), "*_results.xml"))
    elements = [(e[0], e[1], e[2], "") for e in r.model.elements]
    errors = bridge_adapt.read_element_errors(res[0], elements)
    return math.sqrt(sum(v * v for v in errors.values())) / \
        V.error_summary(r)["abs"]


TESTS = []
for _n, _tol in _UNIFORM:
    TESTS.append(Case(
        "AD-01-n%d" % _n, GROUP,
        "Plaat met gat (vlakke rek), uniform hex20 %dx%d per blok" % (
            2 * _n, 2 * _n),
        "lin_static_3d", build_plate(_n, 1, strain=True),
        [Check("Kt_n", kt, ref=KT_PETERSON, tol=_tol, unit="",
               source="Peterson (Pilkey & Pilkey 2008, chart 4.1): 2 + "
                      "0,284 (1-d/W) - 0,600 (1-d/W)^2 + 1,32 (1-d/W)^3")],
        series="AD-01 hex20", h=(WH - R) / (2.0 * _n),
        note="Kwart plaat d/W = 0,2, plak 10 mm met symmetrie op beide "
             "z-vlakken (vlakke rek), 1 laag; Refine x2 op alles zou %d "
             "elementen geven." % _refine_x2_elements(_n)))

TESTS.append(Case(
    "AD-02", GROUP,
    "Plaat met gat: adaptieve verfijningslus (Mecway refine_x2)",
    "lin_static_3d", adapt_loop("AD-02", build_plate(1, 1, strain=True),
                                AD02),
    [Check("lus met Mecway gedraaid (fractie verfijningsstappen)",
           lambda r: _mecway_fraction("AD-02"), ref=1.0, tol_abs=0.0,
           unit="", source="elke verfijning door headless Mecway (refine_x2), "
                           "niet door een opgeslagen tussenmodel; faalt "
                           "als Mecway niet beschikbaar is",
           in_series=False),
     Check("Kt_n na de lus", kt, ref=KT_PETERSON, tol=0.02, unit="",
           source="Peterson (Pilkey & Pilkey 2008, chart 4.1); klaar-"
                  "criterium S7: 2%"),
     Check("elementen / uniform (Refine x2) tot 2%",
           lambda r: r.model.n_elem / float(_uniform_needed(r)), ref=0.0,
           tol_abs=0.999, unit="",
           source="minder elementen dan uniform verfijnen tot dezelfde "
                  "nauwkeurigheid (< 1)", in_series=False),
     Check("globale fout daalt elke lus (max rel_k/rel_k-1)",
           lambda r: _max_ratio("AD-02"), ref=0.0, tol_abs=0.999, unit="",
           source="< 1: de schatting daalt per lus", in_series=False),
     Check("verfijnd binnen 3r van het gat (fractie)",
           lambda r: _near_hole("AD-02"), ref=1.0, tol_abs=0.1, unit="",
           source="de verfijning concentreert zich bij het gat",
           in_series=False),
     Check("sqrt(som eta_e^2) / eta globaal", _eta_sum, ref=1.0, tol=1e-3,
           unit="", source="ERME_ELNO per element = ERME_ELEM; .mess "
                           "TOTALE", in_series=False),
     Check("sigma_xx aan het eindvlak", lambda r: r.at(
         "stressxx", (LH, WH / 2, TZ_STRAIN / 2)), ref=SIG, tol=0.005,
           unit="Pa", source="traction op het eindvlak (de vlakselectie "
                             "verfijnt mee)", in_series=False)],
    note="Lus uit bridge_adapt (doel 1,5%, max. 6 lussen, Dorfler 0,5, "
         "geen buren) met headless Mecway (refine_x2); tussenmodellen "
         "modellen/AD-02-L<k>.liml."))


# ------------------------------------------------------------------
# AD-03 Voorwaarde op een knoopselectie: de lus stopt voor het verfijnen
# ------------------------------------------------------------------
def build_ad03():
    m = Model("S30")
    m.elset("Balk", "Staal")
    mesh = hexmesh(m, "Balk", 4, 1, 1, box(0, 0.2, 0, 0.02, 0, 0.02),
                   order=2)
    m.mat("Staal", STEEL)
    m.node_selection("InklemKnopen", sorted(mesh["nodes"]["u0"]))
    m.face_selection("Eindvlak", mesh["faces"]["u1"])
    m.add('<fixed selection="InklemKnopen" />')
    m.add('<traction selection="Eindvlak"><x>0 Pa</x><y>0 Pa</y>'
          '<z>-1e6 Pa</z></traction>')
    return m


def _ad03_stops(r):
    """1 als bridge_adapt.after_run op deze run niet verfijnt en de
    knoopselectie als oorzaak noemt, anders 0."""
    import bridge_adapt
    import bridge_utils as u
    work = os.path.dirname(r.mess)
    md = _model_data(os.path.join(V.MODELS, "AD-03.liml"), work)
    an = dict(u.CONFIG_BRIDGE["analyses"]["lin_static_3d"])
    an.update(ADAPT)
    an["adapt_target_error"] = 0.01
    res = glob.glob(os.path.join(work, "*_results.xml"))[0]
    step = bridge_adapt.after_run([], bridge_adapt.adapt_settings(an), md,
                                  res, V.error_summary(r))
    named = any("InklemKnopen" in n for n in step["notes"])
    return 1.0 if (not step["refine"] and named) else 0.0


TESTS.append(Case(
    "AD-03", GROUP,
    "Adaptieve verfijning: inklemming op een knoopselectie -> ERROR",
    "lin_static_3d", build_ad03,
    [Check("lus stopt voor verfijnen (1 = ja)", _ad03_stops, ref=1.0,
           tol_abs=0.0, unit="",
           source="Mecway verfijnt knoopselecties niet mee (headless "
                  "nagelopen); bridge_adapt.node_bc_conflicts",
           in_series=False)],
    note="Balk hex20 4x1x1, fixed op de knopen van x = 0 (knoopselectie), "
         "traction op het eindvlak; de grootste fout zit bij de "
         "inklemming."))


# ------------------------------------------------------------------
# AD-10 .. AD-12 Adaptive refinement with HOMARD inside the job (step S35b;
# Scripts/bridge_homard.py, aster_adapt.py; docs/Foutschatter.md par. 7)
# ------------------------------------------------------------------
# The same quarter plate with a hole (d/W = 0.2, slab 10 mm, hex20 coarse
# mesh of 12 elements, one layer), thermal and with plasticity. References:
# uniformly refined meshes through the bridge (S35a,
# TestFiles/Tools/homard_s35/run_s35.py references), the quantity in the
# node (0, R) at the hole edge:
#   thermal (T = 0 / 100 degrees C on x = 0 / x = L, k = 50 W/m/K, hole
#   insulated): qx = -67 465.3 W/m^2 with 32 x 32 hex20 per block (12 288
#   elements in the plane; n16: -67 326.6, so converged within 0.2%);
#   uniform in 3D (every layer refined too, as HOMARD does): n4 768
#   elements -2.66%, n8 6144 elements -0.87%.
#   plasticity (bilinear, yield 250 MPa, plastic modulus 2000 MPa, traction
#   ramp to 150 MPa, GDEF_LOG): sxx = 291.007 MPa, p = 0.00150735 with
#   n32 (n16: 291.665 MPa, 0.00151098); uniform 3D n8 6144 elements
#   +2.4% / +0.8%.
QX_REF = -67465.3
SXX_REF = 291.007e6
P_REF = 0.00150735
UNIFORM_N8 = 6144
SIG_NL = 150.0e6
HOMARD_TH = {"adapt_homard": True, "adapt_homard_target": 0.15,
             "adapt_homard_max_loops": 10}
HOMARD_NL = {"adapt_homard": True, "adapt_homard_target": 0.4,
             "adapt_homard_max_loops": 10}


def _plate_blocks(m, n=1):
    block_a, block_b = _blocks(TZ_STRAIN)
    a = hexmesh(m, "Plaat", 2 * n, 2 * n, 1, block_a, order=2)
    b = hexmesh(m, "Plaat", 2 * n, 2 * n, 1, block_b, order=2)
    c = hexmesh(m, "Plaat", 2 * n, 2 * n, 1, box(WH, LH, 0, WH, 0,
                                                  TZ_STRAIN), order=2)
    return a, b, c


def build_th_plate(override=False, node_temp=False):
    """Thermal plate; override: face selection 'Gat' with #ASTER-RAND
    CILINDER; node_temp: the cold side as a node selection (AD-12)."""
    def build():
        m = Model("T30")
        m.elset("Plaat", "Staal")
        a, b, c = _plate_blocks(m)
        m.mat("Staal", '<thermal type="Isotropic" '
              'thermalconductivity="50 W/m/K" />')
        if node_temp:
            m.node_selection("Koud", sorted(b["nodes"]["v1"]))
        else:
            m.face_selection("Koud", b["faces"]["v1"])
        m.face_selection("Warm", c["faces"]["u1"])
        for sel, t in (("Koud", 273.15), ("Warm", 373.15)):
            m.add('<temperature2 selection="%s"><value>%.12g K</value>'
                  '<starttime>0 s</starttime><endtime>0 s</endtime>'
                  '</temperature2>' % (sel, t))
        if override:
            m.face_selection("Gat", a["faces"]["u0"] + b["faces"]["u0"])
            m.add('<ccxmodeldefinition>** ASTER-RAND Gat = CILINDER 0, 0, '
                  '0, 0, 0, 1, 10 mm</ccxmodeldefinition>')
        return m
    return build


def build_nl_plate():
    m = Model("L30", timesteps={"timeperiod": "1 s", "stepsize": "0.25 s"})
    m.elset("Plaat", "Staal")
    a, b, c = _plate_blocks(m)
    m.mat("Staal", STEEL, '<plastic type="BilinearIsotropic" '
          'yieldstrength="250 MPa" tangentmodulus="2000 MPa" />')
    m.face_selection("SymX", b["faces"]["v1"])
    m.face_selection("SymY", a["faces"]["v0"] + c["faces"]["v0"])
    m.face_selection("SymZ", [f for blk in (a, b, c) for w in ("w0", "w1")
                              for f in blk["faces"][w]])
    m.face_selection("Trek", c["faces"]["u1"])
    for s, (x, y, z) in (("SymX", (1, 0, 0)), ("SymY", (0, 1, 0)),
                         ("SymZ", (0, 0, 1))):
        m.add('<symmetry selection="%s"><x>%d</x><y>%d</y><z>%d</z>'
              '</symmetry>' % (s, x, y, z))
    m.add('<traction selection="Trek"><x time="0 s">0 Pa</x><x time="1 s">'
          '%g Pa</x><y>0 Pa</y><z>0 Pa</z></traction>' % SIG_NL)
    return m


def _adapt_lines(r):
    """[(loop, cells, error)] and the stop reason from the .mess."""
    rows, stop = [], None
    for line in io.open(r.mess, encoding="utf-8", errors="replace"):
        if line.startswith("BRIDGE_ADAPT loop="):
            w = dict(x.split("=") for x in line.split()[1:])
            rows.append((int(w["loop"]), int(w["cells"]), float(w["error"])))
        elif line.startswith("BRIDGE_ADAPT stop="):
            stop = line.split("=", 1)[1].strip()
    return rows, stop


def _log_has(r, text):
    logs = glob.glob(os.path.join(os.path.dirname(r.mess),
                                  "*_bridge_log.txt"))
    return 1.0 if logs and text in io.open(
        logs[0], encoding="utf-8", errors="replace").read() else 0.0


def _last_t(r):
    t = r.times()
    return t[-1] if t else None


def _homard_checks(ref, var, unit, tol, source):
    return [
        Check(var + " at the hole edge (0, R)",
              lambda r: r.at(var, (0.0, R, 0.0), time=_last_t(r)), ref=ref,
              tol=tol, unit=unit, source=source),
        Check("cells after the loop / uniform n8 (same accuracy)",
              lambda r: _adapt_lines(r)[0][-1][1] / float(UNIFORM_N8),
              ref=0.0, tol_abs=0.999, unit="",
              source="fewer cells than uniform refinement (n8, 6144 "
                     "hex20) at the same accuracy (< 1)", in_series=False),
        Check("loop stopped on the target (1 = yes)",
              lambda r: 1.0 if _adapt_lines(r)[1] == "target" else 0.0,
              ref=1.0, tol_abs=0.0, unit="", source="BRIDGE_ADAPT stop=",
              in_series=False),
        Check("hole recognised as a cylinder (1 = yes)",
              lambda r: _log_has(r, "boundary recognised as CYLINDRE"),
              ref=1.0, tol_abs=0.0, unit="",
              source="bridge_homard.recognise, bridge log",
              in_series=False)]


TESTS.append(Case(
    "AD-10", GROUP,
    "Plaat met gat thermisch: adaptieve verfijning met HOMARD in de job",
    "ther_3d", build_th_plate(), _homard_checks(
        QX_REF, "heatfluxx", "W/m2", 0.015,
        "uniform n32 through the bridge (12 288 hex20 in the plane; n16 "
        "-0.2%), S35a"), settings=HOMARD_TH,
    note="adapt_homard, target 0.15% (ZZ), max. 10 loops; automatic "
         "boundary following of the hole (cylinder); result projected "
         "onto the 12 coarse elements."))

TESTS.append(Case(
    "AD-10b", GROUP,
    "Plaat met gat thermisch: rand gegeven met #ASTER-RAND",
    "ther_3d", build_th_plate(override=True), [
        Check("heatfluxx at the hole edge (0, R) equal to AD-10",
              lambda r: r.at("heatfluxx", (0.0, R, 0.0)), ref=-66877.98,
              tol=1.0e-4, unit="W/m2",
              source="AD-10 (automatic recognition, the same cylinder)",
              in_series=False),
        Check("#ASTER-RAND used (1 = yes)",
              lambda r: _log_has(r, "follows CYLINDRE"), ref=1.0,
              tol_abs=0.0, unit="", source="bridge log", in_series=False)],
    settings=HOMARD_TH,
    note="As AD-10 with face selection 'Gat' and '#ASTER-RAND Gat = "
         "CILINDER 0, 0, 0, 0, 0, 1, 10 mm'."))

TESTS.append(Case(
    "AD-11", GROUP,
    "Plaat met gat plastisch: adaptieve verfijning met HOMARD in de job",
    "nonlin_static_3d", build_nl_plate, _homard_checks(
        SXX_REF, "stressxx", "Pa", 0.03,
        "uniform n32 through the bridge (12 288 hex20 in the plane; n16 "
        "+0.2%), S35a") + [
        Check("equivalent plastic strain at (0, R)",
              lambda r: r.at("equivalentplasticstrain", (0.0, R, 0.0),
                             time=_last_t(r)), ref=P_REF, tol=0.03, unit="",
              source="uniform n32 through the bridge, S35a"),
        Check("all 5 time steps in Mecway",
              lambda r: float(len(r.times())), ref=5.0, tol_abs=0.0,
              unit="", source="PROJ_CHAMP of all instants",
              in_series=False)],
    settings=HOMARD_NL,
    note="adapt_homard, target 0.4% (ZZ), max. 10 loops; each loop the "
         "whole load history (0 .. 1 s in 4 steps) on the new mesh; "
         "symmetry as FACE_IMPO DNOR."))


def _ad12_error(r):
    """1 if the bridge refuses the model with adapt_homard (node
    selection 'Koud' with a temperature) with an ERROR that names it."""
    import bridge_utils as u
    from bridge_from_liml import extract_aster_data_from_liml
    from bridge_mesh import write_mesh
    from bridge_to_aster import generate_AsterSolver_files
    work = os.path.join(os.path.dirname(r.mess), "ad12_offline")
    if not os.path.isdir(work):
        os.makedirs(work)
    liml = os.path.join(work, "AD-12.liml")
    shutil.copy(os.path.join(V.MODELS, "AD-12.liml"), liml)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["language"] = "en"
    u.CONFIG_BRIDGE["active_analysis"] = "ther_3d"
    saved = dict(u.CONFIG_BRIDGE["analyses"]["ther_3d"])
    u.CONFIG_BRIDGE["analyses"]["ther_3d"].update(HOMARD_TH)
    u.set_run_log("ad12", liml)
    try:
        md = extract_aster_data_from_liml(liml)
        mail = os.path.join(work, "ad12.mail")
        exp = write_mesh(mail, md) and generate_AsterSolver_files(
            work, md, mail, "ad12.resu")
    finally:
        u.CONFIG_BRIDGE["analyses"]["ther_3d"] = saved
    logs = glob.glob(os.path.join(work, "*bridge_log.txt"))
    text = io.open(logs[0], encoding="utf-8").read() if logs else ""
    return 1.0 if (not exp and "adapt_homard" in text and "Koud" in text) \
        else 0.0


TESTS.append(Case(
    "AD-12", GROUP,
    "Adaptieve verfijning HOMARD: temperatuur op een knoopselectie -> ERROR",
    "ther_3d", build_th_plate(node_temp=True), [
        Check("bridge refuses with an ERROR that names 'Koud' (1 = yes)",
              _ad12_error, ref=1.0, tol_abs=0.0, unit="",
              source="HOMARD keeps node groups with their old nodes only "
                     "(S35a); bridge_homard.check_scope",
              in_series=False)],
    note="The run itself without adapt_homard; the check generates the "
         "same model with adapt_homard offline."))
