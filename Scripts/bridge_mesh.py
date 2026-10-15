# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_mesh.py
# Verantwoordelijkheid: het mesh rechtstreeks uit de .liml (model_data van
# bridge_from_liml.py) schrijven in het ASTER-meshformaat (LIRE_MAILLAGE
# FORMAT='ASTER') en model_data daarop afstemmen. Er is geen Gmsh-export
# meer nodig.
#
# Waarom niet meer via Gmsh (nagelopen met Code-Aster 17.4):
#   - LIRE_MAILLAGE FORMAT='GMSH' zet het bestand eerst om met PRE_GMSH; die
#     kapt groepsnamen af op 8 tekens ('Sixteen_chars_16' -> 'Sixteen_').
#     Het ASTER-formaat leest namen tot 24 tekens (25 gaf MODELISA7_82).
#   - In Gmsh hoort een element bij een groep; hier mag een element in
#     meerdere groepen (een vlak in twee selecties, balkorientatie).
#   - Knoopgroepen kunnen direct in het mesh.
#
# Groepen: elke component (elset) wordt GROUP_MA, elke nodeselection
# GROUP_NO, elke faceselection GROUP_MA van randelementen (of van de
# schaalelementen zelf), elke elementselection GROUP_MA. De namen blijven
# die van Mecway; alleen namen die Code-Aster niet accepteert worden
# aangepast (zie _aster_name).
#
# Knoopvolgorde per elementtype (_ASTER_TYPES): voor 3D gelijk aan Mecway
# (hoekknopen, dan middenknopen); afgeleid uit de geometrie van Mecway-
# voorbeeldmodellen (middenknoop = midden van welke ribbe) en vergeleken
# met de volgorde die PRE_GMSH schrijft. 1D/2D-elementen staan in de .liml
# om en om (hoek, midden, hoek, ...); Code-Aster wil eerst de hoeken.
#
# Compatibel met IronPython 2.7.9.

import math
import re
from collections import OrderedDict

from bridge_utils import log, tr, error_estimator_requested
from bridge_bcs import SUPPORTED_BCS, _angl_naut, is_position


# Maximale groepsnaamlengte in Code-Aster (ASTER-formaat, nagelopen).
ASTER_NAME_MAX = 24

# Namen van de groepen voor losse knopen.
POI1_GROUP_T = "BRPOI1T"    # DIS_T  (alleen translaties)
POI1_GROUP_R = "BRPOI1R"    # DIS_TR (translaties + rotaties)
# Randelementen op de vrije (onbelaste, niet opgelegde) vlakken van
# volume-elementen, voor de foutschatter (_free_faces, bridge_to_aster
# _error_estimator_block).
ERR_FREE_GROUP = "BRERRVRIJ"

_SOLID_SHAPES = frozenset({"hex8", "hex20", "tet4", "tet10", "pyr5",
                           "pyr13", "wedge6", "wedge15"})
_SHELL_SHAPES = frozenset({"tri3", "tri6", "quad4", "quad8"})
_BEAM_SHAPES = frozenset({"line2", "line3"})

# Mecway-vorm -> (Code-Aster-type, Mecway-index per Code-Aster-positie).
# pyr13 komt in geen enkel Mecway-voorbeeld voor, wel in de overgangen van
# Mecway's refine_x2 op hex20 (stap S7): daar liggen de middenknopen in deze
# volgorde (hoeken + middens zoals Code-Aster; nagelopen op de positie van
# elke middenknoop, tests_adaptief AD-02). Code-Aster rekent die meshes
# zonder alarm.
_ASTER_TYPES = {
    "line2":   ("SEG2",    [0, 1]),
    "line3":   ("SEG3",    [0, 2, 1]),
    "tri3":    ("TRIA3",   [0, 1, 2]),
    "tri6":    ("TRIA6",   [0, 2, 4, 1, 3, 5]),
    "quad4":   ("QUAD4",   [0, 1, 2, 3]),
    "quad8":   ("QUAD8",   [0, 2, 4, 6, 1, 3, 5, 7]),
    "tet4":    ("TETRA4",  list(range(4))),
    "tet10":   ("TETRA10", list(range(10))),
    "pyr5":    ("PYRAM5",  list(range(5))),
    "pyr13":   ("PYRAM13", list(range(13))),
    "wedge6":  ("PENTA6",  list(range(6))),
    "wedge15": ("PENTA15", list(range(15))),
    "hex8":    ("HEXA8",   list(range(8))),
    "hex20":   ("HEXA20",  list(range(20))),
}
# Modelisaties waarvoor een line3-element in twee SEG2-cellen wordt
# gesplitst. POU_D_E bestaat alleen op SEG2 (catalogus
# phenomenons_modelisations.py, zie bridge_from_liml STAP 2b); voor POU_D_T
# aangenomen (NIET geverifieerd), een kwadratisch balkelement kent de bridge
# in Code-Aster niet. Twee Euler-cellen interpoleren elk kubisch, dus
# minstens zo goed als een kwadratische balk (Mecway's line3-balk rekent
# alleen met CCX, B32R; verificatie LS-50). Met POU_D_T gerekend: LS-51e
# +0,09 % (afschuiving), Code-Aster 17.4.
# De middenknoop wordt een gewone knoop met 6 vrijheidsgraden.
_LINE3_SPLIT_MODS = ("POU_D_E", "POU_D_T")
# Groep van de POI1-cellen (DIS_TR, stijfheid 0) op knopen van een flexible
# joint zonder ander element met rotaties (_flexible_joints)
JOINT_GROUP = "BRJOINT"

_N_CORNERS = {"SEG2": 2, "SEG3": 2, "TRIA3": 3, "TRIA6": 3, "QUAD4": 4,
              "QUAD8": 4, "TETRA4": 4, "TETRA10": 4, "PYRAM5": 5,
              "PYRAM13": 5, "PENTA6": 6, "PENTA15": 6, "HEXA8": 8,
              "HEXA20": 8}
# Ribben van de middenknopen in Code-Aster-volgorde (hoekindices).
_MID_EDGES = {
    "SEG3":    [(0, 1)],
    "TRIA6":   [(0, 1), (1, 2), (2, 0)],
    "QUAD8":   [(0, 1), (1, 2), (2, 3), (3, 0)],
    "TETRA10": [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)],
    "PYRAM13": [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 4), (2, 4),
                (3, 4)],
    "PENTA15": [(0, 1), (1, 2), (0, 2), (0, 3), (1, 4), (2, 5), (3, 4),
                (4, 5), (3, 5)],
    "HEXA20":  [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4), (1, 5), (2, 6),
                (3, 7), (4, 5), (5, 6), (6, 7), (4, 7)],
}
# Hoekknopen per faceid, in de volgorde van mw.face_nodes() in Mecway 33
# (uitgelezen met een element van elke vorm). Alleen gebruikt zonder
# Mecway-API (offline tests); in Mecway gebruikt de bridge mw.face_nodes()
# en logt een verschil met deze tabel. Schalen: 1..3/4 zijn de randen,
# 5 het vlak en 6 hetzelfde vlak met de omgekeerde normaal.
_FACE_CORNERS = {
    "HEXA":  {1: [0, 3, 2, 1], 2: [4, 5, 6, 7], 3: [0, 1, 5, 4],
              4: [1, 2, 6, 5], 5: [2, 3, 7, 6], 6: [3, 0, 4, 7]},
    "TETRA": {1: [0, 2, 1], 2: [0, 1, 3], 3: [2, 3, 1], 4: [0, 3, 2]},
    "PENTA": {1: [0, 2, 1], 2: [3, 4, 5], 3: [0, 1, 4, 3],
              4: [1, 2, 5, 4], 5: [2, 0, 3, 5]},
    "PYRAM": {1: [0, 1, 4], 2: [1, 2, 4], 3: [2, 3, 4], 4: [3, 0, 4],
              5: [0, 3, 2, 1]},
    "TRIA":  {1: [0, 1], 2: [1, 2], 3: [2, 0], 5: [0, 1, 2], 6: [2, 1, 0]},
    "QUAD":  {1: [0, 1], 2: [1, 2], 3: [2, 3], 4: [3, 0], 5: [0, 1, 2, 3],
              6: [3, 2, 1, 0]},
    "SEG":   {1: [0, 1], 2: [0], 3: [1]},
}


# ==========================================
# VECTOREN
# ==========================================
def _vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _vunit(a):
    n = math.sqrt(_vdot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


# Integratiepunten (xi, eta, gewicht). Driehoek: 6-puntsregel, exact tot
# graad 4 (Dunavant); vierhoek: 3x3 Gauss.
_TRI_GAUSS = []
for _a, _w in ((0.445948490915965, 0.111690794839005),
               (0.091576213509771, 0.054975871827661)):
    _TRI_GAUSS += [(_a, _a, _w), (1.0 - 2.0 * _a, _a, _w),
                   (_a, 1.0 - 2.0 * _a, _w)]
_QUAD_GAUSS = [(x, y, wx * wy)
               for x, wx in ((-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
                             (0.774596669241483, 5.0 / 9.0))
               for y, wy in ((-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
                             (0.774596669241483, 5.0 / 9.0))]
_QUAD_CORNERS = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]


def _face_shape(stype, xi, eta):
    """Vormfuncties van een randelement in Code-Aster-volgorde (hoeken, dan
    middenknoop k tussen hoek k en k+1)."""
    if stype.startswith("TRIA"):
        l = (1.0 - xi - eta, xi, eta)
        if stype == "TRIA3":
            return list(l)
        return ([li * (2.0 * li - 1.0) for li in l] +
                [4.0 * l[0] * l[1], 4.0 * l[1] * l[2], 4.0 * l[2] * l[0]])
    if stype == "QUAD4":
        return [0.25 * (1 + xi * a) * (1 + eta * b) for a, b in _QUAD_CORNERS]
    n = [0.25 * (1 + xi * a) * (1 + eta * b) * (xi * a + eta * b - 1)
         for a, b in _QUAD_CORNERS]
    return n + [0.5 * (1 - xi * xi) * (1 - eta), 0.5 * (1 + xi) * (1 - eta * eta),
                0.5 * (1 - xi * xi) * (1 + eta), 0.5 * (1 - xi) * (1 - eta * eta)]


def _face_integrals(stype, pts):
    """
    Integralen over het vlak (Gauss):
      w[i] = int(N_i dA)      - som = oppervlak (ook gekromd kwadratisch);
                                 knoopgewichten van een gemiddelde
      m[i] = int(N_i x dA)    - eerste momenten per knoop (vector)
      S    = int(x x^T dA)    - tweede moment (3x3), voor momentverdeling
    """
    rule = _TRI_GAUSS if stype.startswith("TRIA") else _QUAD_GAUSS
    h = 1.0e-3   # centrale differentie: exact voor kwadratische N
    w = [0.0] * len(pts)
    m = [[0.0, 0.0, 0.0] for _ in pts]
    S = [[0.0] * 3 for _ in range(3)]
    for xi, eta, gw in rule:
        n = _face_shape(stype, xi, eta)
        np_ = _face_shape(stype, xi + h, eta)
        nm = _face_shape(stype, xi - h, eta)
        ep = _face_shape(stype, xi, eta + h)
        em = _face_shape(stype, xi, eta - h)
        dx = [sum((np_[i] - nm[i]) / (2 * h) * pts[i][c]
                  for i in range(len(pts))) for c in range(3)]
        de = [sum((ep[i] - em[i]) / (2 * h) * pts[i][c]
                  for i in range(len(pts))) for c in range(3)]
        cr = _vcross(dx, de)
        jac = math.sqrt(_vdot(cr, cr))
        x = [sum(n[i] * pts[i][c] for i in range(len(pts))) for c in range(3)]
        for i in range(len(pts)):
            w[i] += gw * jac * n[i]
            for c in range(3):
                m[i][c] += gw * jac * n[i] * x[c]
        for a in range(3):
            for b in range(3):
                S[a][b] += gw * jac * x[a] * x[b]
    return w, m, S


def _inv3(a):
    """Inverse van een 3x3-matrix (lijst van rijen)."""
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) -
           a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) +
           a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    cof = [[a[(r + 1) % 3][(c + 1) % 3] * a[(r + 2) % 3][(c + 2) % 3] -
            a[(r + 1) % 3][(c + 2) % 3] * a[(r + 2) % 3][(c + 1) % 3]
            for r in range(3)] for c in range(3)]
    return [[cof[r][c] / det for c in range(3)] for r in range(3)]


def _cell_names(eid, split):
    """Namen van de mesh-cellen van Mecway-element eid: M<eid>, en voor een
    gesplitste line3-balk ook H<eid> (tweede helft). Celnamen in het
    ASTER-formaat hebben max. 8 tekens: eid tot 9999999."""
    if split:
        return ["M{0}".format(eid), "H{0}".format(eid)]
    return ["M{0}".format(eid)]


def cell_names_of(model_data, eid):
    """Celnamen van Mecway-element eid na write_mesh (zie _cell_names);
    voor andere modules (bridge_to_aster, DEFI_GROUP MAILLE)."""
    return _cell_names(eid, eid in model_data.get("line3_split", ()))


def _mecway_v_axis(p1, p2, orient):
    """
    V-as van een balkelement van p1 naar p2, zoals Mecway hem bepaalt
    (Mecway-manual v33 par. 7.5):
      - met vector: projectie van de vector op het vlak loodrecht op U,
        daarna rotatie om U met 'angle' (rechtshandig; nagelopen met een
        CCX-export van Mecway: U=+X, vector Z, angle -90 graden -> V=+Y);
      - zonder vector: V loodrecht op Z, in het XY-vlak (V = Z x U); is
        het element (bijna) evenwijdig aan Z (gradient < 0,01 %), dan V = Y.
    orient: {"vec": (vx, vy, vz), "angle": rad} of None.
    """
    u = _vunit(_vsub(p2, p1))
    vec = orient["vec"] if orient else None
    if vec is not None and _vdot(vec, vec) > 0.0:
        d = _vdot(vec, u)
        v = (vec[0] - d * u[0], vec[1] - d * u[1], vec[2] - d * u[2])
        if _vdot(v, v) > 1.0e-18 * _vdot(vec, vec):
            v = _vunit(v)
            a = orient.get("angle", 0.0)
            if a:
                w = _vcross(u, v)
                v = tuple(v[i] * math.cos(a) + w[i] * math.sin(a)
                          for i in range(3))
            return v
        log(tr("WARNING: Orientatievector {0} is evenwijdig aan de balk; "
               "standaardorientatie gebruikt.",
               "WARNING: Orientation vector {0} is parallel to the beam; "
               "default orientation used.").format(vec))
    if math.sqrt(u[0] ** 2 + u[1] ** 2) < 1.0e-4 * abs(u[2]):
        return (0.0, 1.0, 0.0)
    return _vunit(_vcross((0.0, 0.0, 1.0), u))


# ==========================================
# NAMEN
# ==========================================
def _aster_names(names, reserved=()):
    """
    {Mecway-naam: Code-Aster-naam}. Code-Aster accepteert in het mesh alleen
    namen die met een letter beginnen, met letters, cijfers en '_', tot 24
    tekens (nagelopen met Code-Aster 17.4: '02Contact', 'Linear(2)', 'Fix-Z'
    en 'a.b' gaven een fout bij LIRE_MAILLAGE). Ongeldige tekens worden '_',
    een naam die niet met een letter begint krijgt 'G' ervoor; daarna
    uniek gemaakt, ook tegen de namen die de bridge zelf maakt
    (_GENERATED_NAME_RE).
    """
    used = set(reserved)
    mapping = OrderedDict()
    for name in names:
        if name in mapping:
            continue
        cand = re.sub(r"[^A-Za-z0-9_]", "_", name)
        if not cand or not cand[0].isalpha():
            cand = "G" + cand
        cand = cand[:ASTER_NAME_MAX]
        cand = _unique_name(cand, used)
        used.add(cand)
        mapping[name] = cand
        if cand != name:
            log("INFO: Groepsnaam '{0}' -> '{1}' (Code-Aster: letter eerst, "
                "alleen letters/cijfers/_, max. {2} tekens, uniek).".format(
                    name, cand, ASTER_NAME_MAX))
    return mapping


# Groepsnamen die de bridge zelf maakt (na het hernoemen, met een teller):
# bridge_mesh BRSY/BRCO/BRESCL/BROV/BRFR (_extra_node_group), BRMAIT
# (_bonded), CMAIT/CESCL (_merge_contact_zones), BRES/BRMA/BRRI
# (_build_discretes), BOR (balkorientatie), BRPOI1T/R; bridge_to_aster
# BRGAP (gaps), BRCT (middenknopen) en tab_<concept>_n<i>
# (resultaattabellen); bridge_thermal TH/THS/THN; bridge_xfem BRXF<n>S/F
# (scheur uit een XFEM_-vlakselectie). Een gebruikersnaam van
# die vorm wordt hernoemd, zodat hij niet met een gemaakte groep kan botsen.
_GENERATED_NAME_RE = re.compile(
    r"^(?:(?:BRSY|BRCO|BRESCL|BROV|BRFR|BRMAIT|CMAIT|CESCL|BRES|BRMA|BRRI|BOR|"
    r"BRGAP|BRCT|THS|THN|TH)\d+|BRXF\d+[SF]|BRPOI1[TR]|all_elems|all_nodes|"
    r"tab_\w+_n\d+)$")


def _unique_name(cand, used):
    """cand, of cand met '_1', '_2', ... (max. ASTER_NAME_MAX tekens) als
    hij al gebruikt is of de vorm van een gemaakte groep heeft."""
    base, i = cand, 1
    while cand in used or _GENERATED_NAME_RE.match(cand):
        suffix = "_{0}".format(i)
        cand = base[:ASTER_NAME_MAX - len(suffix)] + suffix
        i += 1
    return cand


def _selection_names(model_data, renames, reserved, elset_members):
    """
    {Mecway-naam: Code-Aster-naam} voor selecties. Een face- of
    elementselectie met dezelfde naam als een elset (component) zou als
    GROUP_MA de elset-groep overschrijven (de elementen vielen dan stil uit
    het model); zo'n selectie krijgt een eigen naam met '_1', '_2', ...
    Alle verwijzingen naar de selectie (BC's, contact, koppelingen) gaan
    via deze naam. Knoopselecties niet: een GROUP_NO mag dezelfde naam
    hebben als een GROUP_MA.
    """
    out = OrderedDict(renames)
    elsets = set(elset_members)
    for key in ("elsets", "elset_dims", "elset_modelisations"):
        elsets.update(model_data.get(key, {}).keys())
    used = set(reserved) | set(renames.values())
    for name in (list(model_data.get("face_selection_faces", {}).keys()) +
                 list(model_data.get("element_selections", {}).keys())):
        if name not in elsets or out.get(name) != renames.get(name, name):
            continue
        new = _unique_name(renames.get(name, name), used)
        used.add(new)
        out[name] = new
        log(tr("WARNING: Selectie '{0}' heeft dezelfde naam als een "
               "component (elset); in Code-Aster heet de selectie '{1}'. "
               "<<{0}>> in #ASTER-regels is de component. Geef de selectie "
               "in Mecway liever een eigen naam.",
               "WARNING: Selection '{0}' has the same name as a component "
               "(elset); in Code-Aster the selection is called '{1}'. "
               "<<{0}>> in #ASTER lines is the component. Preferably give "
               "the selection its own name in Mecway.").format(name, new))
    return out


def _real(value):
    """Getal voor het ASTER-meshformaat: 15 significante cijfers en altijd
    een decimale punt. '-1e-05' gaf <EXCEPTION> <MODELISA7_85> 'un nombre
    est attendu' (Code-Aster 17.4); '-1.0e-05' en '0.0' worden gelezen."""
    # %-opmaak: "{0:.15g}".format() volgt in Mecway's IronPython de
    # landinstelling en gaf onder een Nederlandse locale '0,25' (gezien in
    # de IronPython-harness); Code-Aster stopte dan met MODELISA7_66.
    txt = "%.15g" % value
    if "." in txt or "n" in txt:          # al een punt, of inf/nan
        return txt
    mant, sep, exp = txt.partition("e")
    return mant + ".0" + sep + exp


def _wrap(items, width=79):
    """Regels ' item item ...' van hoogstens width tekens. LIRE_MAILLAGE
    FORMAT='ASTER' leest maximaal 80 tekens per regel: een langere HEXA20-
    regel gaf <EXCEPTION> <MODELISA7_66> 'item attendu en debut de ligne'
    (Code-Aster 17.4); een element mag over meerdere regels doorlopen."""
    lines = []
    cur = ""
    for it in items:
        if cur and len(cur) + 1 + len(it) > width:
            lines.append(cur)
            cur = ""
        cur += " " + it
    if cur:
        lines.append(cur)
    return lines


# ==========================================
# VLAKKEN
# ==========================================
def _face_from_table(aster_type, conn, faceid):
    """Hoekknopen van een vlak uit _FACE_CORNERS, of None."""
    for prefix, table in _FACE_CORNERS.items():
        if aster_type.startswith(prefix):
            corners = table.get(faceid)
            return [conn[i] for i in corners] if corners else None
    return None


def _skin_element(aster_type, conn, face_nids):
    """
    (type, knopen) van een randelement in Code-Aster-volgorde: hoekknopen in
    de volgorde van face_nids, middenknopen per ribbe uit het moederelement.
    """
    nc = _N_CORNERS[aster_type]
    corner_set = set(conn[:nc])
    corners = [n for n in face_nids if n in corner_set]
    mids = []
    if aster_type in _MID_EDGES:
        midmap = {}
        for k, (a, b) in enumerate(_MID_EDGES[aster_type]):
            midmap[frozenset((conn[a], conn[b]))] = conn[nc + k]
        ring = corners + corners[:1] if len(corners) > 2 else corners
        for a, b in zip(ring[:-1], ring[1:]):
            mids.append(midmap[frozenset((a, b))])
    if len(corners) == 2:
        return ("SEG3" if mids else "SEG2"), corners + mids
    if len(corners) == 3:
        return ("TRIA6" if mids else "TRIA3"), corners + mids
    return ("QUAD8" if mids else "QUAD4"), corners + mids


# Voorwaarden die verplaatsingen opleggen: een vlak waarvan alle hoekknopen
# zo vastliggen, telt voor de foutschatter als Dirichlet-rand (_free_faces).
_DIRICHLET_BCS = frozenset(["fixed", "pinnedsupport", "displacement",
                            "noderotation", "frictionless", "symmetry",
                            "compressiononly", "elasticsupport"])


# Modelisaties met rotatievrijheidsgraden in de knopen (_flexible_joints)
_ROT_MODS = frozenset(["POU_D_E", "POU_D_T", "POU_D_TG", "DKT", "DST",
                       "COQUE_3D", "DIS_TR"])
_ROT_DOFS = ("DRX", "DRY", "DRZ")


def _selection_nodes(model_data, sel, conn, face_group_nodes):
    """Knopen van een Mecway-selectie (knopen, balkvlakken, elementen)."""
    ids = model_data.get("node_groups", {}).get(sel)
    if ids is not None:
        return set(int(str(i).lstrip("N")) for i in ids)
    if sel in face_group_nodes:
        return set(face_group_nodes[sel])
    eids = model_data.get("element_selections", {}).get(sel)
    if eids is not None:
        return set(n for e in eids if e in conn for n in conn[e][1])
    return set()


def _complement(axes):
    """Orthonormale basis van het complement van de span van axes (3D)."""
    basis = []
    for a in list(axes) + [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                           (0.0, 0.0, 1.0)]:
        v = list(a)
        for b in basis:
            d = _vdot(v, b)
            v = [v[i] - d * b[i] for i in range(3)]
        if _vdot(v, v) > 1.0e-12:
            basis.append(_vunit(v))
    return basis[len(_span(axes)):]


def _span(axes):
    """Orthonormale basis van de span van axes."""
    basis = []
    for a in axes:
        v = list(a)
        for b in basis:
            d = _vdot(v, b)
            v = [v[i] - d * b[i] for i in range(3)]
        if _vdot(v, v) > 1.0e-12:
            basis.append(_vunit(v))
    return basis


def _rot_terms(nid, axis, sign):
    """Termen (knoop, DDL, coef) van sign * (rotatie van nid langs axis)."""
    return [(nid, d, sign * c) for d, c in zip(_ROT_DOFS, axis)
            if abs(c) > 1.0e-12]


def _flexible_joints(model_data, nodes, conn, elements, faces_of, by_type,
                     cell_refs, split_line3, face_group_nodes, poi_rot,
                     poi_any):
    """
    Flexible joint on beam (Mecway manual v33 par. 9.12; XML in
    bridge_from_liml._parse_model_item): het uiteinde van een balkelement
    roteert vrij om de gekozen lokale assen U (balkas), V en W.

    Vertaling: het element krijgt aan dat uiteinde een eigen knoop op
    dezelfde plaats (nummer na de Mecway-knopen; in het mesh alleen voor die
    cel, dus by_type krijgt een kopie van de knooplijst, conn blijft de
    Mecway-knopen houden). Die knoop is met LIAISON_DDL (U4.44.01; via
    model_data["constraint_equations"], bridge_to_aster._render_mpcs) aan de
    Mecway-knoop gekoppeld: DX, DY, DZ gelijk en de rotatie langs elke
    niet-vrije lokale as e gelijk (e . theta_nieuw = e . theta_oud). Lokale
    assen zoals Mecway (_mecway_v_axis): U langs de (halve) cel, V uit de
    orientatie, W = U x V (nagelopen met Mecway 34: beam langs X, <rotw />
    = scharnier om Z).

    Heeft de Mecway-knoop geen ander element met rotaties (alle balken daar
    hebben een joint, of alleen volume-elementen), dan krijgt hij een POI1
    DIS_TR met stijfheid 0 (groep JOINT_GROUP) en worden de rotaties langs
    het complement van de gekoppelde assen op 0 gezet (Mecway toont daar
    rotatie 0, gezien bij een scharnier met joints aan beide kanten), tenzij
    een voorwaarde op die knoop al rotaties vastlegt.

    Returns (extra knopen {nid: xyz}, POI1-knopen) of (None, None) zonder
    joints. Resultaten: de extra knopen vallen weg (aster_results_export
    leest alleen de Mecway-knopen; hun reactie telt op bij de Mecway-knoop
    op dezelfde plaats).
    """
    joints = model_data.get("flexible_joints") or []
    if not joints:
        return None, None
    mods = model_data.get("elset_modelisations", {})
    elem_info = dict((eid, (shape, es)) for eid, shape, en, es in elements)
    faces_by_sel = model_data.get("face_selection_faces", {})
    free_at = OrderedDict()     # (eid, nid) -> set van vrije assen
    for j in joints:
        faces = faces_by_sel.get(j["selection"])
        if not faces:
            _not_translated(model_data, {"selection": j["selection"]},
                            "Flexible joint",
                            tr("lege of onbekende vlakselectie",
                               "empty or unknown face selection"))
            continue
        for eid, fid in faces:
            shape, es = elem_info.get(eid, (None, None))
            fn = list(faces_of(eid, fid)) if eid in conn else []
            if shape not in _BEAM_SHAPES or len(fn) != 1:
                _not_translated(
                    model_data, {"selection": j["selection"]},
                    "Flexible joint",
                    tr("vlak {0} van element {1} is geen eindvlak van een "
                       "balkelement (Mecway: alleen eindvlakken van balken)",
                       "face {0} of element {1} is not an end face of a beam "
                       "element (Mecway: beam end faces only)").format(
                           fid, eid))
                continue
            mod = mods.get(es)
            if mod == "BARRE":
                log("INFO: Flexible joint op truss-element {0}: een staaf "
                    "scharniert al.".format(eid))
                continue
            if mod not in _LINE3_SPLIT_MODS:
                _not_translated(
                    model_data, {"selection": j["selection"]},
                    "Flexible joint",
                    tr("element {0} is geen balk (MODELISATION {1})",
                       "element {0} is not a beam (MODELISATION {1})")
                    .format(eid, mod))
                continue
            free_at.setdefault((eid, fn[0]), set()).update(j["free"])
    if not free_at:
        return None, None

    # Elementen per knoop (alle cellen, ook zonder joint)
    at_node = {}
    for eid, (atype, cn) in conn.items():
        for n in cn:
            at_node.setdefault(n, set()).add(eid)
    # Rotaties die voorwaarden per knoop vastleggen
    bc_rot = {}
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _DIRICHLET_BCS or bc.get("skip"):
            continue
        rot = _bc_dofs(bc) & set(_ROT_DOFS)
        if not rot:
            continue
        for n in _selection_nodes(model_data, bc.get("selection"), conn,
                                  face_group_nodes):
            bc_rot.setdefault(n, set()).update(rot)

    by_node = OrderedDict()
    for (eid, nid), free in free_at.items():
        by_node.setdefault(nid, []).append((eid, free))
    next_nid = max(nodes) + 1
    new_nodes = OrderedDict()
    poi_nodes = []
    eqs = model_data.setdefault("constraint_equations", [])
    for nid, items in by_node.items():
        jointed = set(e for e, _f in items)
        others = at_node.get(nid, set()) - jointed
        rot_carrier = nid in poi_rot or any(
            mods.get(elem_info[e][1]) in _ROT_MODS for e in others)
        tied_axes = []
        for eid, free in items:
            dup = next_nid
            next_nid += 1
            new_nodes[dup] = nodes[nid]
            model_data.setdefault("joint_nodes", {})[dup] = nid
            # Cel met dit uiteinde (bij een gesplitste line3 een helft) en
            # de lokale assen van die cel
            cn = conn[eid][1]
            if eid in split_line3:
                halves = ((cn[0], cn[2]), (cn[2], cn[1]))
                k = 0 if nid == cn[0] else 1
                a, b = halves[k]
                atype, idx = cell_refs[eid][k]
            else:
                a, b = cn[0], cn[1]
                atype, idx = cell_refs[eid][0]
            name, cell = by_type[atype][idx]
            by_type[atype][idx] = (name, [dup if n == nid else n
                                          for n in cell])
            u = _vunit(_vsub(nodes[b], nodes[a]))
            v = _mecway_v_axis(nodes[a], nodes[b],
                               model_data.get("beam_orientations",
                                              {}).get(eid))
            w = _vcross(u, v)
            for d in ("DX", "DY", "DZ"):
                eqs.append({"terms": [(dup, d, 1.0), (nid, d, -1.0)],
                            "constant": 0.0, "source": "flexiblejoint"})
            fixed = [ax for key, ax in (("u", u), ("v", v), ("w", w))
                     if key not in free]
            for ax in fixed:
                eqs.append({"terms": _rot_terms(dup, ax, 1.0) +
                            _rot_terms(nid, ax, -1.0),
                            "constant": 0.0, "source": "flexiblejoint"})
            tied_axes.extend(fixed)
            log("INFO: Flexible joint element {0}, knoop N{1}: eigen knoop "
                "N{2}, vrij om {3} (U={4}, V={5}).".format(
                    eid, nid, dup, "/".join(sorted(f.upper() for f in free)),
                    tuple(round(c, 6) for c in u),
                    tuple(round(c, 6) for c in v)))
        if rot_carrier:
            continue
        # Geen ander element met rotaties: knoop N<nid> krijgt een POI1
        # DIS_TR (anders heeft hij geen rotaties, of zelfs geen
        # vrijheidsgraden als alleen balken met een joint er zitten)
        if not tied_axes and (others or nid in poi_any):
            continue        # geen rotaties nodig, wel vrijheidsgraden
        poi_nodes.append(nid)
        if bc_rot.get(nid):
            continue
        for ax in _complement(tied_axes):
            eqs.append({"terms": _rot_terms(nid, ax, 1.0), "constant": 0.0,
                        "source": "flexiblejoint"})
    log("INFO: Flexible joint: {0} balkuiteinde(n) met een eigen knoop "
        "(LIAISON_DDL), {1} knoop/knopen met een POI1 DIS_TR.".format(
            len(new_nodes), len(poi_nodes)))
    return new_nodes, poi_nodes


def _referenced_names(model_data):
    """Namen van selecties die een voorwaarde, belasting, contact of
    koppeling gebruikt (alle tekstwaarden van die dicts, een niveau diep)."""
    names = set()
    for key in ("bcs", "contacts", "bonded", "couplings"):
        for item in model_data.get(key, []) or []:
            if isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, (type(u""), type(""))):
                        names.add(v)
    return names


def _free_faces(model_data, conn):
    """
    Vrije vlakken van volume-elementen voor de foutschatter: [(type,
    knopen)] als randelementen (Code-Aster-volgorde, _skin_element).

    Waarom: CALC_ERREUR ERME_ELEM rekent een randterm (sigma.n - g) alleen
    op vlakken waar een last op staat; een vlak zonder last behandelt het
    als opgelegde verplaatsing, dus zonder randterm. Bron: testcase
    sslv153a (Code-Aster 17.4), commentaar: zonder de groepen LIBRE/LIBRE2
    met druk ~0 "ces bords sont consideres comme a deplacement impose par
    le calcul des indicateurs d'erreur"; sslv07a: "STRICTO SENSU, LE CALCUL
    DE ERME_ELEM EST FAUX CAR DES BORDS A CONTRAINTE NULLE N'ONT PAS ETE
    DEFINIS". De bridge zet daarom PRES_REP ~0 op de vrije vlakken (1e-14
    Pa, niet 0: zie bridge_to_aster._error_estimator_block).

    Vrij = rand van het volume (vlak van precies een volume-element), niet
    gedeeld met een schaalelement, niet in een vlakselectie die een
    voorwaarde, last, contact of koppeling gebruikt (_referenced_names: die
    vlakken hebben een eigen last of zijn Dirichlet), en niet met alle
    hoekknopen in een knoopselectie van een opgelegde verplaatsing
    (_DIRICHLET_BCS). Vlakken uit _FACE_CORNERS (hoekknopen; de volgorde is
    voor PRES_REP ~0 niet van belang, ORIE_PEAU richt ze naar buiten).
    """
    shapes = model_data.get("elem_shapes", {})
    counts = OrderedDict()
    for eid in sorted(conn):
        if shapes.get(eid) not in _SOLID_SHAPES:
            continue
        atype, cn = conn[eid]
        for prefix, table in _FACE_CORNERS.items():
            if atype.startswith(prefix):
                for fid in sorted(table):
                    corners = [cn[i] for i in table[fid]]
                    key = frozenset(corners)
                    if key in counts:
                        counts[key][0] += 1
                    else:
                        counts[key] = [1, eid, corners]
                break
    taken = set()
    for eid, (atype, cn) in conn.items():
        if shapes.get(eid) in _SHELL_SHAPES:
            taken.add(frozenset(cn[:_N_CORNERS[atype]]))
    used = _referenced_names(model_data)
    for fname, faces in model_data.get("face_selection_faces", {}).items():
        if fname not in used:
            continue
        for eid, fid in faces:
            if eid in conn:
                taken.add(frozenset(_face_from_table(
                    conn[eid][0], conn[eid][1], fid) or []))
    fixed = set()
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _DIRICHLET_BCS or not bc.get("selection"):
            continue
        sel = bc["selection"]
        # Alleen knoopselecties: een vlakselectie met een voorwaarde valt al
        # onder "taken" (zijn eigen vlakken). Met de knopen van een
        # vlakselectie zou bijv. een buitenwand tussen twee opgelegde
        # eindvlakken (een element dik) ten onrechte Dirichlet worden
        # (gezien bij verificatie LS-04).
        for i in model_data.get("node_groups", {}).get(sel, []):
            fixed.add(int(str(i).lstrip("N")))
    out = []
    for key, (n, eid, corners) in counts.items():
        if n != 1 or key in taken or key <= fixed:
            continue
        atype, cn = conn[eid]
        out.append(_skin_element(atype, cn, corners))
    return out


# ==========================================
# HOOFDFUNCTIE
# ==========================================
def write_mesh(mail_path, model_data, face_nodes=None):
    """
    Schrijf het mesh van model_data naar mail_path (ASTER-formaat) en stem
    model_data erop af (groepsnamen, POI1-groepen, balkorientatie,
    oppervlakken voor krachten op vlakken).

    face_nodes : functie (eid, faceid) -> [knoopnummers] of None. In Mecway
                 mw.face_nodes(FaceId(eid, faceid)); zonder (offline tests)
                 de tabel _FACE_CORNERS.

    Returns
    -------
    bool  True bij succes; False bij een fout (melding in bridge_log.txt).
    """
    log("--- Mesh schrijven (ASTER-formaat): {0} ---".format(mail_path))
    nodes = model_data.get("mesh_nodes", {})
    elements = model_data.get("mesh_elements", [])
    if not nodes or not elements:
        log(tr("ERROR: Geen knopen of elementen in de .liml gevonden.",
               "ERROR: No nodes or elements found in the .liml."))
        return False
    nids = sorted(nodes.keys())
    if nids != list(range(1, len(nids) + 1)):
        # De resultaten worden op knoopindex teruggelezen; Mecway nummert
        # na verfijnen en verwijderen 1..N door (gezien in Mecway).
        log(tr("ERROR: Knoopnummers zijn niet 1..N aaneengesloten ({0} "
               "knopen, hoogste {1}).",
               "ERROR: Node numbers are not contiguous 1..N ({0} "
               "nodes, highest {1}).").format(len(nids), nids[-1]))
        return False

    # --------------------------------------------------
    # 1. Elementen in Code-Aster-volgorde
    # --------------------------------------------------
    conn = {}          # eid -> (aster_type, [nid ...])
    by_type = OrderedDict()
    elset_members = OrderedDict()
    # Cellen per element: {eid: [(aster_type, index in by_type[type])]};
    # een line3-balk heeft er twee (_LINE3_SPLIT_MODS)
    cell_refs = {}
    elset_mods = model_data.get("elset_modelisations", {})
    n_split = 0
    for eid, shape, enodes, elset in elements:
        spec = _ASTER_TYPES.get(shape)
        if spec is None:
            log(tr("ERROR: Elementvorm '{0}' (element {1}) wordt niet "
                   "ondersteund.",
                   "ERROR: Element shape '{0}' (element {1}) is not "
                   "supported.").format(shape, eid))
            return False
        atype, order = spec
        if len(enodes) != len(order):
            log(tr("ERROR: Element {0} ({1}) heeft {2} knopen, verwacht {3}.",
                   "ERROR: Element {0} ({1}) has {2} nodes, expected {3}.")
                .format(eid, shape, len(enodes), len(order)))
            return False
        cn = [enodes[i] for i in order]
        conn[eid] = (atype, cn)
        if shape == "line3" and elset_mods.get(elset) in _LINE3_SPLIT_MODS:
            # Kwadratische balk -> twee SEG2-cellen M<eid> (eerste knoop -
            # middenknoop) en H<eid> (middenknoop - tweede knoop): de
            # balkelementen van Code-Aster bestaan alleen op SEG2 (zie
            # _LINE3_SPLIT_MODS). conn houdt de Mecway-vorm (SEG3) voor de
            # geometrie (vlakken, lengtes); de resultaten gaan per knoop
            # terug, dus ook op de middenknoop.
            n_split += 1
            for name, part in zip(_cell_names(eid, True),
                                  ([cn[0], cn[2]], [cn[2], cn[1]])):
                items = by_type.setdefault("SEG2", [])
                cell_refs.setdefault(eid, []).append(("SEG2", len(items)))
                items.append((name, part))
                elset_members.setdefault(elset, []).append(name)
            continue
        items = by_type.setdefault(atype, [])
        cell_refs[eid] = [(atype, len(items))]
        items.append(("M{0}".format(eid), cn))
        elset_members.setdefault(elset, []).append("M{0}".format(eid))
    if n_split:
        log("INFO: {0} line3-balkelement(en) gesplitst in twee SEG2-cellen "
            "(M<eid> en H<eid>).".format(n_split))
    split_line3 = set(e for e, refs in cell_refs.items() if len(refs) == 2)

    # --------------------------------------------------
    # 2. Vlakselecties -> randelementen / schaalelementen / knopen
    # --------------------------------------------------
    shapes = model_data.get("elem_shapes", {})
    skin_by_key = {}
    skin_count = [0]
    face_groups = OrderedDict()       # naam -> [elementnamen]
    face_group_nodes = OrderedDict()  # naam -> set(nid), alleen balkvlakken
    group_areas = {}
    group_weights = {}                # naam -> {nid: int(N dA)}, volumevlakken
    group_integrals = {}              # naam -> [w, m, S] per knoop, alle vlakken
    group_faces = {}                  # naam -> {"kinds": set, "normals": [..]}
    # naam -> [{"kind", "stype", "nodes", "eid", "fid", "side"}] per vlak,
    # voor belastingen die per knoop een normaal of gewicht nodig hebben
    # (elastic support, compression only, symmetry)
    group_face_list = OrderedDict()

    def note_list(fname, kind, stype, snodes, eid, fid, side=None):
        group_face_list.setdefault(fname, []).append({
            "kind": kind, "stype": stype, "nodes": list(snodes), "eid": eid,
            "fid": fid, "side": side})

    def note_face(fname, kind, corner_pts, side=None):
        info = group_faces.setdefault(
            fname, {"kinds": set(), "normals": [], "sides": set()})
        info["kinds"].add(kind)
        if side is not None:
            info["sides"].add(side)
        if len(corner_pts) >= 3:
            nrm = _vcross(_vsub(corner_pts[1], corner_pts[0]),
                          _vsub(corner_pts[-1], corner_pts[0]))
            if _vdot(nrm, nrm) > 0.0:
                info["normals"].append(_vunit(nrm))

    def add_integrals(fname, stype, snodes):
        fw, fm, fs = _face_integrals(stype, [nodes[n] for n in snodes])
        gi = group_integrals.setdefault(
            fname, [OrderedDict(), OrderedDict(), [[0.0] * 3 for _ in range(3)]])
        for n, w, m in zip(snodes, fw, fm):
            gi[0][n] = gi[0].get(n, 0.0) + w
            old = gi[1].get(n, (0.0, 0.0, 0.0))
            gi[1][n] = tuple(old[c] + m[c] for c in range(3))
        for a in range(3):
            for b in range(3):
                gi[2][a][b] += fs[a][b]
        return fw
    checked = set()

    def faces_of(eid, fid):
        atype, cn = conn[eid]
        table = _face_from_table(atype, cn, fid)
        if face_nodes is None:
            return table
        api = list(face_nodes(eid, fid))
        key = (atype, fid)
        if table is not None and key not in checked:
            checked.add(key)
            if set(table) != set(api) - set(cn[_N_CORNERS[atype]:]):
                log(tr("WARNING: Vlak {0} van {1}: Mecway geeft {2}, de "
                       "tabel {3}. De Mecway-waarde wordt gebruikt.",
                       "WARNING: Face {0} of {1}: Mecway gives {2}, the "
                       "table {3}. The Mecway value is used.").format(
                        fid, atype, api, table))
        return api

    # XFEM_-vlakselecties zijn een scheur (stap 2e, bridge_xfem.mesh_cells),
    # geen randelementen
    import bridge_xfem
    xfem_sel = (set(bridge_xfem.selection_names(model_data))
                if bridge_xfem.active_here() else set())
    for fname, faces in model_data.get("face_selection_faces", {}).items():
        if fname in xfem_sel:
            continue
        members = []
        for eid, fid in faces:
            if eid not in conn:
                log(tr("ERROR: Vlakselectie '{0}': element {1} bestaat niet.",
                       "ERROR: Face selection '{0}': element {1} does not "
                       "exist.").format(fname, eid))
                continue
            shape = shapes.get(eid, "?")
            atype, cn = conn[eid]
            fn = faces_of(eid, fid)
            if not fn:
                log(tr("ERROR: Vlakselectie '{0}': vlak {1} van element {2} "
                       "({3}) onbekend.",
                       "ERROR: Face selection '{0}': face {1} of element {2} "
                       "({3}) unknown.").format(fname, fid, eid, shape))
                continue
            if shape in _BEAM_SHAPES:
                face_group_nodes.setdefault(fname, set()).update(fn)
                note_face(fname, "beam", [])
                note_list(fname, "beam", atype, fn, eid, fid)
                continue
            if shape in _SHELL_SHAPES and set(fn) >= set(cn[:_N_CORNERS[atype]]):
                members.append("M{0}".format(eid))   # schaalvlak = element
                add_integrals(fname, atype, cn)
                corner_set = set(cn[:_N_CORNERS[atype]])
                # volgorde van het vlak: faceid 5 en 6 hebben tegengestelde
                # normalen; side = +1 als de vlaknormaal gelijk is aan de
                # elementnormaal (Code-Aster), anders -1
                fpts = [nodes[n] for n in fn if n in corner_set]
                epts = [nodes[n] for n in cn[:_N_CORNERS[atype]]]
                fn_ = _vcross(_vsub(fpts[1], fpts[0]), _vsub(fpts[-1], fpts[0]))
                en_ = _vcross(_vsub(epts[1], epts[0]), _vsub(epts[-1], epts[0]))
                note_face(fname, "shellface", fpts,
                          1 if _vdot(fn_, en_) > 0.0 else -1)
                note_list(fname, "shellface", atype, cn, eid, fid,
                          1 if _vdot(fn_, en_) > 0.0 else -1)
                continue
            stype, snodes = _skin_element(atype, cn, fn)
            key = frozenset(snodes)
            if key not in skin_by_key:
                skin_count[0] += 1
                name = "K{0}".format(skin_count[0])
                skin_by_key[key] = name
                by_type.setdefault(stype, []).append((name, snodes))
            note_face(fname, "solid" if shape in _SOLID_SHAPES else "shelledge",
                      [nodes[n] for n in
                       snodes[:3 if stype.startswith("TRIA") else 4]])
            note_list(fname, "solid" if shape in _SOLID_SHAPES
                      else "shelledge", stype, snodes, eid, fid)
            if shape in _SOLID_SHAPES:
                fw = add_integrals(fname, stype, snodes)
                gw = group_weights.setdefault(fname, OrderedDict())
                for n, w in zip(snodes, fw):
                    gw[n] = gw.get(n, 0.0) + w
                group_areas[fname] = group_areas.get(fname, 0.0) + sum(fw)
            members.append(skin_by_key[key])
        if members:
            # Een cel één keer per groep: vlak 5 en 6 van hetzelfde
            # schaalelement gaven alarm MODELISA5_8 bij LIRE_MAILLAGE (de
            # integralen en vlaklijsten hierboven tellen beide zijden wel)
            face_groups[fname] = list(OrderedDict.fromkeys(members))

    # --------------------------------------------------
    # 2b. Foutschatter: randelementen op de vrije vlakken (_free_faces)
    # --------------------------------------------------
    free_members = []
    if error_estimator_requested(
            model_data.get("aster_custom", {}).get("options")):
        for stype, snodes in _free_faces(model_data, conn):
            key = frozenset(snodes)
            if key not in skin_by_key:
                skin_count[0] += 1
                name = "K{0}".format(skin_count[0])
                skin_by_key[key] = name
                by_type.setdefault(stype, []).append((name, snodes))
            free_members.append(skin_by_key[key])
        if free_members:
            log("INFO: Foutschatter: {0} vrije vlakken van volume-elementen "
                "als groep '{1}' (spanningsvrije rand, PRES_REP ~0 in "
                "CALC_ERREUR).".format(len(free_members), ERR_FREE_GROUP))

    # --------------------------------------------------
    # 2c. Vibro-akoestiek: koppelvlakken fluidum-constructie als
    #     randelementen (bridge_vibroacoustic.interface_faces)
    # --------------------------------------------------
    vibro_members = OrderedDict()
    if model_data.get("vibro"):
        import bridge_vibroacoustic
        if bridge_vibroacoustic.wanted():
            found = bridge_vibroacoustic.interface_faces(model_data, conn)
            if found is None:
                return False
            for group, items in found.items():
                for stype, snodes in items:
                    key = frozenset(snodes)
                    if key not in skin_by_key:
                        skin_count[0] += 1
                        name = "K{0}".format(skin_count[0])
                        skin_by_key[key] = name
                        by_type.setdefault(stype, []).append((name, snodes))
                    vibro_members.setdefault(group, []).append(
                        skin_by_key[key])

    # --------------------------------------------------
    # 2d. Breukmechanica: ribben langs het scheurfront als SEG-cellen
    #     (bridge_fracture.front_cells; groepen BRSCHEUR<n>)
    # --------------------------------------------------
    import bridge_fracture
    crack_cells = bridge_fracture.front_cells(model_data, conn)
    if crack_cells is None:
        return False
    crack_members = OrderedDict()
    for group, items in crack_cells.items():
        for stype, snodes in items:
            skin_count[0] += 1
            name = "K{0}".format(skin_count[0])
            by_type.setdefault(stype, []).append((name, snodes))
            crack_members.setdefault(group, []).append(name)

    # --------------------------------------------------
    # 2e. XFEM: scheurvlak en front uit XFEM_-vlakselecties als cellen
    #     buiten het model (bridge_xfem.mesh_cells; groepen BRXF<n>S/F)
    # --------------------------------------------------
    xfem_cells = bridge_xfem.mesh_cells(
        model_data, conn, faces_of if face_nodes is not None else None)
    if xfem_cells is None:
        return False
    for group, items in xfem_cells.items():
        for stype, snodes in items:
            skin_count[0] += 1
            name = "K{0}".format(skin_count[0])
            by_type.setdefault(stype, []).append((name, snodes))
            crack_members.setdefault(group, []).append(name)

    # --------------------------------------------------
    # 3. Losse knopen uit nodeselections -> POI1
    # --------------------------------------------------
    used_nodes = set()
    for atype, cn in conn.values():
        used_nodes.update(cn)
    rot_masters = set()
    master_groups = set()
    for c in model_data.get("couplings", []):
        master_groups.add(c["master_group"])
        if c["type"] == "rbe3" and c.get("surface_rot", False):
            rot_masters.add(c["master_group"])
    poi1_nodes = OrderedDict([(POI1_GROUP_T, []), (POI1_GROUP_R, [])])
    for gname, ids in model_data.get("node_groups", {}).items():
        for nid_str in ids:
            nid = int(nid_str[1:]) if nid_str.startswith("N") else int(nid_str)
            if nid in used_nodes:
                continue
            if nid not in nodes:
                log(tr("ERROR: Knoop {0} uit nodeselection '{1}' bestaat "
                       "niet.",
                       "ERROR: Node {0} from nodeselection '{1}' does not "
                       "exist.").format(nid, gname))
                continue
            target = POI1_GROUP_R if gname in rot_masters else POI1_GROUP_T
            if nid in poi1_nodes[POI1_GROUP_R]:
                continue
            if target == POI1_GROUP_R and nid in poi1_nodes[POI1_GROUP_T]:
                poi1_nodes[POI1_GROUP_T].remove(nid)
            if nid not in poi1_nodes[target]:
                poi1_nodes[target].append(nid)
            if gname not in master_groups:
                log(tr("WARNING: Losse knoop {0} (nodeselection '{1}') is "
                       "geen master van een koppeling. Het DIS-element heeft "
                       "stijfheid 0; zonder koppeling of opgelegde "
                       "verplaatsing wordt de stijfheidsmatrix singulier.",
                       "WARNING: Free node {0} (nodeselection '{1}') is "
                       "not the master of a coupling. The DIS element has "
                       "stiffness 0; without a coupling or prescribed "
                       "displacement the stiffness matrix becomes singular.")
                    .format(nid, gname))
    poi1_groups = OrderedDict()
    poi1_members = OrderedDict()
    for gname, pnids in poi1_nodes.items():
        if not pnids:
            continue
        names = []
        for nid in pnids:
            name = "P{0}".format(nid)
            by_type.setdefault("POI1", []).append((name, [nid]))
            names.append(name)
        poi1_members[gname] = names
        poi1_groups[gname] = "DIS_TR" if gname == POI1_GROUP_R else "DIS_T"
        log("INFO: {0} losse knoop/knopen als POI1 in groep '{1}' ({2}): "
            "{3}".format(len(pnids), gname, poi1_groups[gname],
                         ", ".join("N{0}".format(n) for n in pnids)))

    # --------------------------------------------------
    # 4. Balkorientatie -> extra groepen met een eigen VECT_Y
    # --------------------------------------------------
    # Een element mag in het ASTER-formaat in meerdere groepen, dus de
    # elset blijft heel; elke V-richting krijgt een extra groep BORnnnnn
    # met ORIENTATION VECT_Y (model_data["beam_vect_y"]).
    beam_groups = OrderedDict()
    beam_vect_y = OrderedDict()
    orient = model_data.get("beam_orientations", {})
    if orient:
        # Gesorteerd: een set gaf per Python-proces (hash-seed) een andere
        # volgorde van de BOR-groepen in de .comm.
        oriented_elsets = sorted(set(es for eid, shape, en, es in elements
                                     if eid in orient))
        for elset in oriented_elsets:
            subgroups = OrderedDict()
            for eid, shape, enodes, es in elements:
                if es != elset or shape not in _BEAM_SHAPES:
                    continue
                cn = conn[eid][1]
                if eid in split_line3:
                    # per helft (rechte SEG2): V loodrecht op die helft
                    parts = zip(_cell_names(eid, True),
                                ((cn[0], cn[2]), (cn[2], cn[1])))
                else:
                    parts = [("M{0}".format(eid), (cn[0], cn[1]))]
                for name, (a, b) in parts:
                    v = _mecway_v_axis(nodes[a], nodes[b], orient.get(eid))
                    key = tuple(round(c, 9) for c in v)
                    subgroups.setdefault(key, [v, []])[1].append(name)
            for v, members in subgroups.values():
                sub = "BOR{0:05d}".format(len(beam_groups) + 1)
                beam_groups[sub] = members
                beam_vect_y[sub] = v
            log("INFO: Balkorientatie '{0}': {1} richting(en) van V."
                .format(elset, len(subgroups)))

    # --------------------------------------------------
    # 4b. Discrete elementen op knopen (elastic support, knoopmassa's)
    # --------------------------------------------------
    discretes = _build_discretes(model_data, nodes, conn, group_face_list)
    k_poi = 0
    for dname, d in discretes.items():
        names = []
        for nid in d["nodes"]:
            k_poi += 1
            names.append("S{0}".format(k_poi))
            by_type.setdefault("POI1", []).append((names[-1], [nid]))
        d["members"] = names

    # --------------------------------------------------
    # 4c. Flexible joints: eigen knoop per balkuiteinde + LIAISON_DDL
    # --------------------------------------------------
    poi_rot = set(poi1_nodes[POI1_GROUP_R])
    poi_any = set(poi1_nodes[POI1_GROUP_T]) | poi_rot
    for d in discretes.values():
        poi_any.update(d["nodes"])
        if d.get("mod") == "DIS_TR":
            poi_rot.update(d["nodes"])
    joint_nodes, joint_poi = _flexible_joints(
        model_data, nodes, conn, elements, faces_of, by_type, cell_refs,
        split_line3, face_group_nodes, poi_rot, poi_any)
    joint_nodes = joint_nodes or OrderedDict()
    if joint_poi:
        names = []
        for nid in joint_poi:
            names.append("J{0}".format(nid))
            by_type.setdefault("POI1", []).append((names[-1], [nid]))
        poi1_members[JOINT_GROUP] = names
        poi1_groups[JOINT_GROUP] = "DIS_TR"

    # --------------------------------------------------
    # 5. Namen
    # --------------------------------------------------
    reserved = (["all_elems", "all_nodes", POI1_GROUP_T, POI1_GROUP_R,
                 ERR_FREE_GROUP, JOINT_GROUP] +
                list(beam_groups.keys()) + list(discretes.keys()) +
                list(vibro_members.keys()) + list(crack_members.keys()))
    renames = _aster_names(
        list(elset_members.keys()) +
        list(model_data.get("node_groups", {}).keys()) +
        list(model_data.get("face_selection_faces", {}).keys()) +
        list(model_data.get("element_selections", {}).keys()) +
        [c["master_group"] for c in model_data.get("couplings", [])] +
        [c["slave_group"] for c in model_data.get("couplings", [])],
        reserved)
    sel_renames = _selection_names(model_data, renames, reserved,
                                   elset_members)

    def rn(name):
        """Code-Aster-naam van een selectie (node/face/element)."""
        return sel_renames.get(name, name)

    def rn_es(name):
        """Code-Aster-naam van een elset (component)."""
        return renames.get(name, name)

    group_ma = OrderedDict()
    for name, members in elset_members.items():
        group_ma[rn_es(name)] = members
    for name, members in face_groups.items():
        group_ma[rn(name)] = members
    for name, eids in model_data.get("element_selections", {}).items():
        members = [c for e in eids if e in conn
                   for c in _cell_names(e, e in split_line3)]
        if members:
            group_ma[rn(name)] = members
    for name, members in poi1_members.items():
        group_ma[name] = members
    for name, members in beam_groups.items():
        group_ma[name] = members
    for name, d in discretes.items():
        group_ma[name] = d.pop("members")
    if free_members:
        group_ma[ERR_FREE_GROUP] = free_members
    for name, members in vibro_members.items():
        group_ma[name] = members
    for name, members in crack_members.items():
        group_ma[name] = members

    group_no = OrderedDict()
    for name, ids in model_data.get("node_groups", {}).items():
        group_no[rn(name)] = ["N{0}".format(int(str(i).lstrip("N")))
                              for i in ids]
    for name, nset in face_group_nodes.items():
        if rn(name) not in group_ma:
            group_no[rn(name)] = ["N{0}".format(n) for n in sorted(nset)]
    # Lege groepen (lege Mecway-selectie) niet schrijven: een voorwaarde of
    # last erop wordt in _apply_to_model_data overgeslagen en gemeld.
    for groups in (group_ma, group_no):
        for name in [n for n, m in groups.items() if not m]:
            del groups[name]

    # --------------------------------------------------
    # 6. Schrijven
    # --------------------------------------------------
    try:
        out = ["TITRE", " Mecway-model via MecwayAsterBridge", "FINSF",
               "COOR_3D"]
        for nid in nids:
            # 15 significante cijfers: de regel blijft onder 80 tekens.
            out.append(" N{0} {1}".format(nid, " ".join(
                _real(c) for c in nodes[nid])))
        # Extra knopen van flexible joints na de Mecway-knopen (de
        # resultaten worden op knoopindex teruggelezen)
        for nid, xyz in joint_nodes.items():
            out.append(" N{0} {1}".format(nid, " ".join(
                _real(c) for c in xyz)))
        out.append("FINSF")
        # Celnaam per Code-Aster-celnummer (0-based, volgorde in het
        # bestand); bridge_failure vertaalt er bezweken cellen mee naar
        # Mecway-elementen (Code-Aster 17.4 heeft geen getCellName).
        model_data["cell_names"] = [name for items in by_type.values()
                                    for name, _cn in items]
        for atype, items in by_type.items():
            out.append(atype)
            for name, cn in items:
                out.extend(_wrap([name] + ["N{0}".format(n) for n in cn]))
            out.append("FINSF")
        for kind, groups in (("GROUP_MA", group_ma), ("GROUP_NO", group_no)):
            for name, members in groups.items():
                out.append(kind)
                out.append(" {0}".format(name))
                out.extend(_wrap(members))
                out.append("FINSF")
        out.append("FIN")
        f = open(mail_path, "w")
        try:
            f.write("\n".join(out) + "\n")
        finally:
            f.close()
    except Exception as e:
        log(tr("ERROR: Schrijven van '{0}' mislukt: {1}",
               "ERROR: Writing '{0}' failed: {1}").format(mail_path, str(e)))
        return False

    nonempty = set(group_ma.keys())
    model_data["group_ma_unions"] = OrderedDict()
    model_data["beam_vect_y"] = beam_vect_y
    model_data["node_groups_in_mesh"] = True
    # Voor #ASTER-regels (<<Mecway-naam>> -> Code-Aster-naam) en voor de
    # elsets van mesh_elements (bridge_to_aster, bridge_thermal): bij een
    # selectie met dezelfde naam als een elset wint de elset
    # (_selection_names meldt dat).
    model_data["group_renames"] = dict(renames)
    # Selecties apart (een vlakselectie met de naam van een elset krijgt
    # een eigen naam, _selection_names); gebruikt door bridge_acoustic.
    model_data["selection_renames"] = dict(sel_renames)
    model_data["mesh_group_names"] = set(group_ma) | set(group_no)
    model_data["face_node_groups"] = set(
        rn(n) for n in face_group_nodes if rn(n) not in group_ma)
    model_data["discretes"] = discretes
    model_data["_conn"] = conn
    # Gesplitste line3-balken (cellen M<eid> en H<eid>, cell_names_of);
    # extra knopen van flexible joints: model_data["joint_nodes"]
    model_data["line3_split"] = split_line3
    model_data["_elem_elset"] = dict((eid, rn_es(es))
                                     for eid, shape, en, es in elements)
    model_data["group_face_list"] = OrderedDict(
        (rn(k), v) for k, v in group_face_list.items())
    for name, nset in face_group_nodes.items():
        group_weights.setdefault(name, OrderedDict(
            (n, 1.0) for n in sorted(nset)))
    _apply_to_model_data(model_data, rn, rn_es, nonempty, poi1_groups,
                         dict((rn(k), v) for k, v in group_areas.items()),
                         dict((rn(k), v) for k, v in group_weights.items()),
                         dict((rn(k), v) for k, v in group_integrals.items()),
                         dict((rn(k), v) for k, v in group_faces.items()))
    # De vrije vlakken in het model (randelementen, ORIE_PEAU), zodat de
    # foutschatter er een last op ziet (bridge_to_aster._error_estimator_block).
    model_data["error_free_group"] = ERR_FREE_GROUP if free_members else None
    if free_members:
        model_data["skin_groups"].append(ERR_FREE_GROUP)
    log("SUCCESS: Mesh geschreven: {0} knopen, {1} elementen, {2} randelementen, "
        "{3} GROUP_MA, {4} GROUP_NO.".format(
            len(nids), len(conn), skin_count[0], len(group_ma), len(group_no)))
    return True


def _per_area(params, area):
    """Krachtparameters (float of tijdshistorie) gedeeld door area."""
    out = {}
    for ax, v in params.items():
        if ax.startswith("_"):
            out[ax] = v
        elif isinstance(v, list):
            out[ax] = [(t, f / area) for t, f in v]
        else:
            out[ax] = v / area
    return out


# ==========================================
# VLAKKEN PER KNOOP: GEWICHTEN EN NORMALEN
# ==========================================
def _lumped_weights(stype, pts):
    """
    Knoopgewichten van een vlak (som = oppervlak): int(N_i dA), of bij een
    niet-positief gewicht (hoeken van QUAD8/TRIA6) de HRZ-verdeling
    w_i = A * int(N_i^2 dA) / sum_j int(N_j^2 dA) (Hinton-Rock-Zienkiewicz,
    zoals voor een gelumpte massamatrix). Hoe Mecway een elastic support over
    de knopen verdeelt, is NIET geverifieerd.
    """
    w = _face_integrals(stype, pts)[0]
    if min(w) > 0.0:
        return w
    rule = _TRI_GAUSS if stype.startswith("TRIA") else _QUAD_GAUSS
    h = 1.0e-3
    sq = [0.0] * len(pts)
    for xi, eta, gw in rule:
        n = _face_shape(stype, xi, eta)
        dx = [sum((a - b) / (2 * h) * pts[i][c] for i, (a, b) in enumerate(
            zip(_face_shape(stype, xi + h, eta),
                _face_shape(stype, xi - h, eta)))) for c in range(3)]
        de = [sum((a - b) / (2 * h) * pts[i][c] for i, (a, b) in enumerate(
            zip(_face_shape(stype, xi, eta + h),
                _face_shape(stype, xi, eta - h)))) for c in range(3)]
        cr = _vcross(dx, de)
        jac = math.sqrt(_vdot(cr, cr))
        for i in range(len(pts)):
            sq[i] += gw * jac * n[i] * n[i]
    area = sum(w)
    total = sum(sq)
    return [area * s / total for s in sq]


def _face_normal(face, nodes, conn):
    """
    Eenheidsnormaal van een vlak uit group_face_list, naar buiten gericht:
    volumevlak van het moederelement af (via het zwaartepunt), schaalvlak
    langs de vlaknormaal (side * elementnormaal; faceid 5 = elementnormaal).
    """
    nc = 3 if face["stype"].startswith("TRIA") else 4
    p = [nodes[n] for n in face["nodes"][:nc]]
    if nc == 3:
        nrm = _vcross(_vsub(p[1], p[0]), _vsub(p[2], p[0]))
    else:
        nrm = _vcross(_vsub(p[2], p[0]), _vsub(p[3], p[1]))
    nrm = _vunit(nrm)
    if face["kind"] == "solid":
        cn = conn[face["eid"]][1]
        c = [sum(nodes[n][k] for n in cn) / len(cn) for k in range(3)]
        f = [sum(q[k] for q in p) / nc for k in range(3)]
        if _vdot(nrm, _vsub(f, c)) < 0.0:
            nrm = (-nrm[0], -nrm[1], -nrm[2])
    elif face["kind"] == "shellface" and face.get("side", 1) < 0:
        nrm = (-nrm[0], -nrm[1], -nrm[2])
    return nrm


def _node_weights_normals(faces, nodes, conn):
    """
    {nid: gewicht} en {nid: gemiddelde normaal} over de vlakken (2D-vlakken
    van volumes en schalen). Normaal in een knoop: gewogen gemiddelde van de
    normalen van de aangrenzende vlakken (zoals Mecway's frictionless,
    manual v33 par. 9.2).
    """
    weights = OrderedDict()
    sums = OrderedDict()
    for face in faces:
        nrm = _face_normal(face, nodes, conn)
        w = _lumped_weights(face["stype"], [nodes[n] for n in face["nodes"]])
        for n, wi in zip(face["nodes"], w):
            weights[n] = weights.get(n, 0.0) + wi
            old = sums.get(n, (0.0, 0.0, 0.0))
            sums[n] = tuple(old[k] + wi * nrm[k] for k in range(3))
    return weights, OrderedDict((n, _vunit(v)) for n, v in sums.items())


def _round_key(values, scale):
    """Sleutel om knopen met (vrijwel) gelijke waarden te groeperen."""
    return tuple(int(round(v / scale * 1.0e9)) for v in values)


# ==========================================
# DISCRETE ELEMENTEN OP KNOPEN (vóór het schrijven van het mesh)
# ==========================================
def _build_discretes(model_data, nodes, conn, face_list):
    """
    POI1-discreten voor elastic support en knoopmassa's. Returns
    OrderedDict {groep: {"nodes": [nid], "mod": "DIS_T"/"DIS_TR",
    "cara": [(CARA, (waarden))]}}; knopen met gelijke waarden delen een
    groep (AFFE_CARA_ELEM DISCRET kent alleen GROUP_MA, catalogus v17.4).

    Elastic support (manual v33 par. 9.4): per knoop een veer naar de grond
    K = w_i * (kt I + (kn - kt) n n^T), w_i = knoopgewicht van het oppervlak
    (_lumped_weights), n = gemiddelde normaal. K_T_N: volle symmetrische
    3x3 in het globale stelsel, 6 waarden "triangulaire superieure par
    colonne" (catalogus affe_cara_elem.py): K11, K12, K22, K13, K23, K33.
    """
    out = OrderedDict()

    def add(prefix, items, mod, make_cara, label):
        groups = OrderedDict()
        scale = max([abs(v) for _, vals in items for v in vals] + [1.0e-30])
        for nid, vals in items:
            groups.setdefault(_round_key(vals, scale), [vals, []])[1].append(
                nid)
        for vals, nids in groups.values():
            name = "{0}{1}".format(prefix, len(out) + 1)
            out[name] = {"nodes": nids, "mod": mod, "cara": make_cara(vals),
                         "label": label}

    for bc in model_data.get("bcs", []):
        if bc["type"] != "elasticsupport":
            continue
        bc["skip"] = True      # vertaald als discrete elementen
        sel = bc["selection"]
        faces = face_list.get(sel, [])
        kinds = set(f["kind"] for f in faces)
        if not faces:
            # Mecway 33 slaat het op een elementselectie op, maar rekent er
            # niet mee: headless gemeten (interne solver en CCX), blok met
            # elastic support op 4 elementen = zelfde doorbuiging als zonder
            model_data.setdefault("skipped_loads", []).append(
                tr("elastic support op '{0}'",
                   "elastic support on '{0}'").format(sel))
            log(tr("WARNING: Elastic support op '{0}': geen vlakken "
                   "(elementselectie?). Mecway rekent een elastic support "
                   "op elementen ook niet mee; kies vlakken (manual v33 "
                   "par. 9.4). NIET meegenomen.",
                   "WARNING: Elastic support on '{0}': no faces (element "
                   "selection?). Mecway does not apply an elastic support "
                   "on elements either; select faces (manual v33 par. "
                   "9.4). NOT included.").format(sel))
            continue
        if not kinds <= set(["solid", "shellface"]):
            model_data.setdefault("skipped_loads", []).append(
                tr("elastic support op '{0}'",
                   "elastic support on '{0}'").format(sel))
            log(tr("ERROR: Elastic support op '{0}': alleen vlakken van "
                   "volume-elementen en schaalvlakken (manual v33 par. 9.4), "
                   "hier {1}. NIET meegenomen.",
                   "ERROR: Elastic support on '{0}': only faces of solid "
                   "elements and shell faces (manual v33 par. 9.4), "
                   "here {1}. NOT included.").format(sel, sorted(kinds)))
            continue
        kn, kt = bc["params"]["kn"], bc["params"]["kt"]
        weights, normals = _node_weights_normals(faces, nodes, conn)
        items = []
        for n, w in weights.items():
            v = normals[n]
            k = [[w * ((kt if a == b else 0.0) + (kn - kt) * v[a] * v[b])
                  for b in range(3)] for a in range(3)]
            items.append((n, (k[0][0], k[0][1], k[1][1], k[0][2], k[1][2],
                              k[2][2])))
        add("BRES", items, "DIS_T",
            lambda vals: [("K_T_N", vals), ("M_T_D_N", (0.0,))],
            "elastic support '{0}'".format(sel))
        log("INFO: Elastic support '{0}': {1} knopen, oppervlak {2} m2, "
            "kn={3} Pa/m, kt={4} Pa/m -> veren DIS_T K_T_N.".format(
                sel, len(weights), "%.6g" % sum(weights.values()), kn, kt))

    groups = model_data.get("node_groups", {})
    for pm in model_data.get("point_masses", []):
        ids = [int(str(i).lstrip("N")) for i in groups.get(pm["selection"],
                                                            [])]
        if not ids:
            continue
        share = pm["value"] / float(len(ids))
        if pm["kind"] == "mass":
            # Mecway (manual v33 par. 9.21): massa gelijk verdeeld over de
            # knopen. M_T_D_N: 1 waarde (catalogus affe_cara_elem.py).
            add("BRMA", [(n, (share,)) for n in ids], "DIS_T",
                lambda vals: [("K_T_D_N", (0.0, 0.0, 0.0)),
                              ("M_T_D_N", vals)],
                "massa '{0}'".format(pm["selection"]))
        else:
            # M_TR_D_N: (M, IX, IY, IZ, IXY, IYZ, IXZ, EX, EY, EZ), U4.42.01
            # par. DISCRET. Gelijk verdeeld over de knopen zoals de massa:
            # NIET geverifieerd (manual zegt het alleen voor massa).
            if len(ids) > 1:
                log(tr("WARNING: Rotatietraagheid op '{0}' ({1} knopen): "
                       "gelijk verdeeld (NIET geverifieerd tegen Mecway).",
                       "WARNING: Rotational inertia on '{0}' ({1} nodes): "
                       "distributed equally (NOT verified against Mecway).")
                    .format(pm["selection"], len(ids)))
            inertia = [0.0, 0.0, 0.0]
            inertia[pm["axis"] - 1] = share
            add("BRRI", [(n, tuple(inertia)) for n in ids], "DIS_TR",
                lambda vals: [("K_TR_D_N", (0.0,) * 6),
                              ("M_TR_D_N", (0.0,) + tuple(vals) +
                               (0.0,) * 6)],
                "rotatietraagheid '{0}'".format(pm["selection"]))
        log("INFO: {0} op '{1}': {2} per knoop over {3} knopen.".format(
            pm["kind"], pm["selection"], share, len(ids)))
    return out


# ==========================================
# TRACTION, LINE PRESSURE, HYDROSTATISCHE DRUK
# ==========================================
def _not_translated(model_data, bc, what, why):
    bc["skip"] = True
    model_data.setdefault("skipped_loads", []).append(
        tr("{0} op '{1}'", "{0} on '{1}'").format(what, bc["selection"]))
    log(tr("ERROR: {0} op '{1}': {2}. NIET meegenomen.",
           "ERROR: {0} on '{1}': {2}. NOT included.").format(
        what, bc["selection"], why))


def _element_kinds(model_data, sel):
    """Modelisaties van de elementen van een elementselectie, of None."""
    eids = model_data.get("element_selections", {}).get(sel)
    if eids is None:
        return None
    mods = model_data.get("elset_modelisations", {})
    elem_elset = model_data.get("_elem_elset", {})
    return set(mods.get(elem_elset.get(e), "?") for e in eids)


def _traction(model_data, bc, faces, skin_groups):
    """
    Mecway (manual v33 par. 9.15): kracht per oppervlak, globaal.
      - volumevlakken: FORCE_FACE (U4.44.01), randelementen in het model;
      - schaalvlakken: FORCE_COQUE FX/FY/FZ met PLAN='SUP' (faceid 5, kant
        van de elementnormaal) of 'INF' (faceid 6): Mecway legt de kracht
        op het vlak op halve dikte, dus met een moment; PLAN SUP/INF doet
        dat in Code-Aster (U4.44.01 FORCE_COQUE: "force applied to upper/
        lower skin");
      - schaalelementen (elementselectie): FORCE_COQUE PLAN='MOY'
        (middenvlak, zoals Mecway);
      - schaalranden en balkuiteinden: knoopkrachten (_edge_loads).
    """
    sel = bc["selection"]
    kinds = faces.get("kinds", set()) if faces else set()
    elem_mods = _element_kinds(model_data, sel)
    handler = SUPPORTED_BCS["traction"]
    if kinds == set(["solid"]):
        bc["aster_keyword"] = "FORCE_FACE"
        if sel not in skin_groups:
            skin_groups.append(sel)
        return
    if kinds and kinds <= set(["shelledge", "beam"]):
        _edge_loads(model_data, bc, "Traction")
        return
    if kinds == set(["shellface"]) and len(faces.get("sides", ())) == 1:
        plan = "SUP" if list(faces["sides"])[0] > 0 else "INF"
    elif not kinds and elem_mods and elem_mods <= set(["DKT", "DST",
                                                         "COQUE_3D"]):
        plan = "MOY"
    else:
        _not_translated(model_data, bc, "Traction",
                        tr("alleen volumevlakken, schaalvlakken aan een kant, "
                           "schaalelementen, schaalranden of balkuiteinden "
                           "(hier {0})",
                           "only solid faces, shell faces on one side, "
                           "shell elements, shell edges or beam ends "
                           "(here {0})").format(
                            sorted(kinds) or sorted(elem_mods or ["?"])))
        return
    bc["aster_keyword"] = "FORCE_COQUE"
    d = OrderedDict(handler.to_aster_dict(bc["params"]))
    d["PLAN"] = "'{0}'".format(plan)     # tekst in de .comm
    bc["aster_dict"] = d
    log("INFO: Traction op schalen '{0}': FORCE_COQUE PLAN='{1}'.".format(
        sel, plan))


def _shell_edge_parent(model_data, sel):
    """MODELISATION van de schalen achter randgroep sel (DKT/DST/COQUE_3D),
    of None als die niet eenduidig een schaaltype is."""
    mods = model_data.get("elset_modelisations", {})
    elem_elset = model_data.get("_elem_elset", {})
    parents = set(mods.get(elem_elset.get(f["eid"]), "?") for f in
                  model_data.get("group_face_list", {}).get(sel, []))
    if len(parents) == 1 and parents <= set(["DKT", "DST", "COQUE_3D"]):
        return list(parents)[0]
    return None


def _edge_length(model_data, sel):
    """Totale lengte van de schaalranden in sel (SEG2; SEG3 via de
    middenknoop als twee rechte stukken)."""
    nodes = model_data["mesh_nodes"]
    total = 0.0
    for f in model_data.get("group_face_list", {}).get(sel, []):
        ns = f["nodes"]
        path = [ns[0], ns[2], ns[1]] if len(ns) == 3 else ns[:2]
        for a, b in zip(path[:-1], path[1:]):
            d = _vsub(nodes[b], nodes[a])
            total += math.sqrt(_vdot(d, d))
    return total


def _line_pressure(model_data, bc, faces):
    """
    Mecway (manual v33 par. 9.16): kracht per lengte op balkelementen
    (FORCE_POUTRE, globaal FX/FY/FZ of lokaal N/VY/VZ) of op schaalranden
    (FORCE_ARETE, globaal; U4.44.01: "line forces to an edge of a volume
    element or shell"). FORCE_POUTRE werkt ook op BARRE (trusses): run
    17.4, staaf 2 m met FX=1000 N/m, EA=2,1e7 N -> u(2)=9,52381e-5 m exact.
    """
    sel = bc["selection"]
    kinds = faces.get("kinds", set()) if faces else set()
    local = bc["params"].get("_local")
    elem_mods = _element_kinds(model_data, sel)
    if not kinds and elem_mods and elem_mods <= set(["POU_D_E", "POU_D_T", "BARRE"]):
        bc["aster_keyword"] = "FORCE_POUTRE"
        return
    if kinds == set(["shelledge"]) and not local:
        # De randen moeten in het model, met de modelisatie van de schaal
        # (<EXCEPTION> MODELISA6_96 zonder, Code-Aster 17.4).
        mods = model_data.get("elset_modelisations", {})
        elem_elset = model_data.get("_elem_elset", {})
        parents = set(mods.get(elem_elset.get(f["eid"]), "?") for f in
                      model_data.get("group_face_list", {}).get(sel, []))
        if len(parents) != 1 or not parents <= set(["DKT", "DST",
                                                      "COQUE_3D"]):
            _not_translated(model_data, bc, "Line pressure",
                            tr("schaalranden van een schaaltype (hier {0})",
                               "shell edges of one shell type (here {0})")
                            .format(sorted(parents)))
            return
        model_data.setdefault("edge_groups", OrderedDict())[sel] = \
            list(parents)[0]
        bc["aster_keyword"] = "FORCE_ARETE"
        return
    _not_translated(model_data, bc, "Line pressure",
                    tr("alleen balkelementen (elementselectie) of "
                       "schaalranden (globaal X/Y/Z); hier {0}{1}",
                       "only beam elements (element selection) or "
                       "shell edges (global X/Y/Z); here {0}{1}").format(
                        sorted(kinds) or sorted(elem_mods or ["?"]),
                        tr(", elementcoordinaten", ", element coordinates")
                        if local else ""))


# ==========================================
# DRUK EN TRACTION OP SCHAALRANDEN EN BALKUITEINDEN
# ==========================================
_SEG_GAUSS = [(-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
              (0.774596669241483, 5.0 / 9.0)]


def _seg_shape(nn, xi):
    """Vormfuncties en afgeleiden van SEG2/SEG3 (Code-Aster-volgorde:
    hoeken, dan middenknoop)."""
    if nn == 2:
        return [0.5 * (1.0 - xi), 0.5 * (1.0 + xi)], [-0.5, 0.5]
    return ([0.5 * xi * (xi - 1.0), 0.5 * xi * (xi + 1.0), 1.0 - xi * xi],
            [xi - 0.5, xi + 0.5, -2.0 * xi])


def _shell_normal(nodes, cn, atype):
    """Eenheidsnormaal van een schaalelement uit de hoekknopen."""
    p = [nodes[n] for n in cn[:_N_CORNERS[atype]]]
    if len(p) == 3:
        return _vunit(_vcross(_vsub(p[1], p[0]), _vsub(p[2], p[0])))
    return _vunit(_vcross(_vsub(p[2], p[0]), _vsub(p[3], p[1])))


def _edge_frames(model_data, faces_list):
    """
    Per schaalrand (kind 'shelledge') de integraal over de randlengte:
    {nid: [int N_i t dl, int N_i t n dl, int N_i dl, int N_i e dl,
    schaalnormaal]} met t de dikte, n de naar buiten gerichte normaal in
    het schaalvlak (loodrecht op de rand, van het element af) en e de
    raaklijn. Returns (dict, reden) met reden != None als een dikte
    ontbreekt.
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    sections = model_data.get("shell_sections", {})
    elem_elset = model_data.get("_elem_elset", {})
    out = OrderedDict()
    for f in faces_list:
        sec = sections.get(elem_elset.get(f["eid"])) or {}
        t = sec.get("thickness")
        if not t:
            return out, tr("schaal zonder dikte (element {0})",
                           "shell without thickness (element {0})").format(
                f["eid"])
        atype, cn = conn[f["eid"]]
        ns = _shell_normal(nodes, cn, atype)
        c = [sum(nodes[n][k] for n in cn) / len(cn) for k in range(3)]
        en = f["nodes"]
        pts = [nodes[n] for n in en]
        for xi, gw in _SEG_GAUSS:
            shp, dshp = _seg_shape(len(en), xi)
            x = [sum(shp[i] * pts[i][k] for i in range(len(en)))
                 for k in range(3)]
            dx = [sum(dshp[i] * pts[i][k] for i in range(len(en)))
                  for k in range(3)]
            jac = math.sqrt(_vdot(dx, dx))
            e = _vunit(dx)
            n = _vunit(_vcross(e, ns))
            if _vdot(n, _vsub(x, c)) < 0.0:
                n = (-n[0], -n[1], -n[2])
            for i, nid in enumerate(en):
                a = out.setdefault(nid, [0.0, [0.0] * 3, 0.0, [0.0] * 3,
                                         ns])
                w = gw * jac * shp[i]
                a[0] += w * t
                a[2] += w
                # raaklijn met een vaste zin (de zin van een rand is vrij)
                s = 1.0 if _vdot(e, a[3]) >= 0.0 else -1.0
                for k in range(3):
                    a[1][k] += w * t * n[k]
                    a[3][k] += s * w * e[k]
    return out, None


def _edge_loads(model_data, bc, what):
    """
    Druk of traction op schaalranden en balkuiteinden als knoopkrachten
    (FORCE_NODALE via bc["node_loads"], zoals een moment op vlakken;
    bridge_to_aster._build_charges schaalt ze, ook met een tijdsfunctie).

    Mecway (manual v33 par. 9.14/9.15): druk = normaalkracht evenredig met
    het oppervlak van het vlak, positief naar het element toe; traction =
    kracht per oppervlak in X/Y/Z. Het oppervlak van een schaalrand is
    lengte x dikte (het randvlak ligt symmetrisch om het middenvlak, dus
    geen moment), dat van een balkuiteinde de doorsnede A. Zo vertaald:
    schaalrand f_i = -p int(N_i t n dl) (n in het schaalvlak, van het
    element af) of T int(N_i t dl); balkuiteinde -p A u (u = de as naar
    buiten) of T A. Dat Mecway het randvlak zo rekent, is NIET
    geverifieerd tegen een Mecway-oplossing (geen voorbeeld met druk op
    een schaalrand of balkuiteinde). Code-Aster heeft geen druk op een
    schaalrand (PRES_REP: "domaine de milieu continu 2D ou 3D, ou ...
    coques", catalogus affe_char_meca.py v17.4); FORCE_ARETE zou een groep
    per richting vragen. Statisch gelijkwaardig met de consistente
    knoopkrachten van de rand; na LINE_QUAD blijven de krachten op de
    Mecway-knopen.
    """
    sel = bc["selection"]
    if any(is_position(v) for v in bc["aster_dict"].values()):
        # De knoopkrachten zijn vaste vectoren maal de waarde
        # (_render_node_loads); een formule in x, y, z zou per knoop
        # anders moeten wegen. KNOWN_BUGS 104.
        _not_translated(model_data, bc, what, tr(
            "formule in x, y, z op schaalranden of balkuiteinden "
            "(KNOWN_BUGS 104)",
            "formula in x, y, z on shell edges or beam ends "
            "(KNOWN_BUGS 104)"))
        return
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    faces_list = model_data.get("group_face_list", {}).get(sel, [])
    edges = [f for f in faces_list if f["kind"] == "shelledge"]
    ends = [f for f in faces_list if f["kind"] == "beam"]
    frames, why = _edge_frames(model_data, edges)
    elem_elset = model_data.get("_elem_elset", {})
    per_node = OrderedDict()     # nid -> [gewicht, vector]  (druk: -vector)
    for nid, a in frames.items():
        per_node[nid] = [a[0], list(a[1])]
    for f in ends:
        if why:
            break
        if f["fid"] not in (2, 3) or len(set(f["nodes"])) != 1:
            why = tr("zijvlak van een balk (alleen balkuiteinden, faceid "
                     "2/3; gebruik voor een verdeelde last line pressure op "
                     "een elementselectie)",
                     "side face of a beam (only beam ends, faceid 2/3; for a "
                     "distributed load use line pressure on an element "
                     "selection)")
            break
        area = None
        for key in ("beam_sections", "cable_sections"):
            sec = model_data.get(key, {}).get(elem_elset.get(f["eid"]))
            if sec and sec.get("area"):
                area = sec["area"]
        if not area:
            why = tr("balk zonder doorsnede-oppervlak (element {0})",
                     "beam without cross-section area (element {0})").format(
                f["eid"])
            break
        nid = f["nodes"][0]
        cn = conn[f["eid"]][1]
        other = cn[1] if nid == cn[0] else cn[0]
        u = _vunit(_vsub(nodes[nid], nodes[other]))
        a = per_node.setdefault(nid, [0.0, [0.0] * 3])
        a[0] += area
        for k in range(3):
            a[1][k] += area * u[k]
    if why or not per_node:
        _not_translated(model_data, bc, what, why or tr(
            "geen schaalranden of balkuiteinden", "no shell edges or "
            "beam ends"))
        return
    if bc["type"] == "surfacepressure":
        node_loads = OrderedDict([("PRES", [
            (n, tuple(-c for c in a[1])) for n, a in per_node.items()])])
    else:
        node_loads = OrderedDict()
        for k, comp in enumerate(("FX", "FY", "FZ")):
            if comp in bc["aster_dict"]:
                node_loads[comp] = [
                    (n, tuple(a[0] if j == k else 0.0 for j in range(3)))
                    for n, a in per_node.items()]
    bc["aster_keyword"] = "FORCE_NODALE"
    bc["node_loads"] = node_loads
    log("INFO: {0} op '{1}': {2} schaalrand(en), {3} balkuiteinde(n) -> "
        "knoopkrachten over {4} knopen (oppervlak {5} m2).".format(
            what, sel, len(edges), len(ends), len(per_node),
            "%.6g" % sum(a[0] for a in per_node.values())))


def _gravity_sum(grav, sel):
    """
    Vectorsom (gx, gy, gz) van de gravity-items. Een tijdshistorie (lijst
    (t, g); nu leest bridge_bcs.GravityBC alleen een vaste waarde, KNOWN_BUGS
    32) telt met de laatste waarde mee: de druk-formule is constant (WARNING).
    """
    total = [0.0, 0.0, 0.0]
    history = False
    for b in grav:
        for k, c in enumerate(("x", "y", "z")):
            v = b["params"].get(c, 0.0)
            if isinstance(v, list):
                history = True
                v = v[-1][1] if v else 0.0
            total[k] += v
    if history:
        log(tr("WARNING: Hydrostatische druk op '{0}': gravity met een "
               "tijdshistorie; de laatste waarde wordt gebruikt.",
               "WARNING: Hydrostatic pressure on '{0}': gravity with a "
               "time history; the last value is used.").format(sel))
    if len(grav) > 1:
        log("INFO: Hydrostatische druk op '{0}': {1} gravity-items opgeteld "
            "tot ({2}) m/s2.".format(sel, len(grav),
                                     ", ".join("%.6g" % c for c in total)))
    return tuple(total)


def _hydrostatic(model_data, bc, faces, skin_groups):
    """
    Mecway (manual v33 par. 9.17): p = rho * g . (x - x0) onder het vrije
    oppervlak (punt x0), 0 erboven; g = de gravity-belasting van het model.
    Code-Aster: consistente knoopkrachten (FORCE_NODALE via node_loads,
    _hydrostatic_forces), op volumevlakken of schaalvlakken aan een kant
    (teken zoals surfacepressure); headless tegen Mecway: resultante exact,
    hex20-blok DX 0,12%. Terugval voor andere vlaktypen: PRES_REP /
    FORCE_COQUE met een FORMULE (bridge_to_aster._hydrostatic_formula).
    Meerdere gravity-items: de vectorsom, zoals de
    gravity-lasten zelf in Code-Aster opgeteld worden (elk een eigen last in
    EXCIT, of een PESANTEUR in bridge_to_aster._sum_gravity).
    """
    grav = [b for b in model_data["bcs"]
            if b["type"] == "gravity" and not b.get("skip")]
    if not grav:
        _not_translated(model_data, bc,
                        tr("Hydrostatische druk", "Hydrostatic pressure"),
                        tr("het model heeft geen gravity (manual par. 9.17: "
                           "verplicht)",
                           "the model has no gravity (manual par. 9.17: "
                           "required)"))
        return
    g = _gravity_sum(grav, bc["selection"])
    kinds = faces.get("kinds", set()) if faces else set()
    sign = 1.0
    if kinds == set(["solid"]):
        if bc["selection"] not in skin_groups:
            skin_groups.append(bc["selection"])
    elif kinds == set(["shellface"]) and len(faces.get("sides", ())) == 1:
        # Een druk als functie op schalen moet via FORCE_COQUE PRES
        # (<EXCEPTION> ELEMENTS4_92 met PRES_REP, Code-Aster 17.4).
        sign = float(list(faces["sides"])[0])
        bc["aster_keyword"] = "FORCE_COQUE"
    else:
        _not_translated(model_data, bc,
                        tr("Hydrostatische druk", "Hydrostatic pressure"),
                        tr("alleen volumevlakken of schaalvlakken aan een "
                           "kant (hier {0})",
                           "only solid faces or shell faces on one side "
                           "(here {0})").format(sorted(kinds) or "?"))
        return
    hydro = {"rho": bc["params"]["rho"], "point": bc["params"]["point"],
             "g": g, "sign": sign}
    forces = _hydrostatic_forces(model_data, bc["selection"], hydro)
    if forces is None:
        # vlaktype zonder vormfuncties hier: PRES_REP/FORCE_COQUE met de
        # formule (bridge_to_aster._hydrostatic_formula, Gausspunten)
        bc["hydro"] = hydro
        bc["aster_dict"] = {"PRES": "hydro"}
        return
    if bc["selection"] in skin_groups and kinds == set(["solid"]):
        skin_groups.remove(bc["selection"])
    bc["aster_keyword"] = "FORCE_NODALE"
    bc["node_loads"] = OrderedDict([("HYD", forces)])
    bc["aster_dict"] = {"HYD": 1.0}
    tot = [sum(f[1][k] for f in forces) for k in range(3)]
    log("INFO: Hydrostatische druk op '{0}': knoopkrachten over {1} knopen, "
        "resultante ({2}) N.".format(bc["selection"], len(forces),
                                     ", ".join("%.6g" % c for c in tot)))


def _sub_rule(stype, k):
    """
    Integratieregel over k x k deelcellen (vierhoek) of k^2 deeldriehoeken,
    met de regel van _face_integrals per deelcel. Voor een vlak dat het
    vrije oppervlak snijdt: de knik in p = max(0, ...) valt dan in een
    kleine cel (fout ~1/k^2).
    """
    out = []
    if stype.startswith("TRIA"):
        for i in range(k):
            for j in range(k - i):
                tris = [((i, j), (i + 1, j), (i, j + 1))]
                if i + j < k - 1:
                    tris.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
                for a, b, c in tris:
                    for u, v, w in _TRI_GAUSS:
                        out.append(((a[0] + u * (b[0] - a[0]) +
                                     v * (c[0] - a[0])) / float(k),
                                    (a[1] + u * (b[1] - a[1]) +
                                     v * (c[1] - a[1])) / float(k),
                                    w / float(k * k)))
        return out
    h = 2.0 / k
    for i in range(k):
        for j in range(k):
            for u, v, w in _QUAD_GAUSS:
                out.append((-1.0 + h * (i + 0.5 * (u + 1.0)),
                            -1.0 + h * (j + 0.5 * (v + 1.0)),
                            w / float(k * k)))
    return out


def _hydrostatic_forces(model_data, sel, hydro):
    """
    Consistente knoopkrachten f_i = -int(N_i p n dA) van de hydrostatische
    druk (n = normaal van het vlak naar buiten, druk > 0 = het vlak in).
    Mecway integreert stuksgewijs exact (manual v33 par. 9.17: "< 1%");
    PRES_REP met een FORMULE neemt Gausspunten: blok 1x1x1 m, 2 hex8 over
    de hoogte, waterlijn op 0,75 m: resultante 1,7% te groot, Mecway
    (headless) 0,03%. Hier: vlakken die het vrije oppervlak snijden over
    8 x 8 deelcellen. Returns [(nid, (fx, fy, fz))] of None als een vlak
    geen bekend type heeft.
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    rho, g, x0 = hydro["rho"], hydro["g"], hydro["point"]

    def pres(x):
        return max(0.0, rho * sum(g[c] * (x[c] - x0[c]) for c in range(3)))

    rules = {}
    acc = OrderedDict()
    hd = 1.0e-3
    for f in model_data.get("group_face_list", {}).get(sel, []):
        stype = f["stype"]
        if stype not in ("TRIA3", "TRIA6", "QUAD4", "QUAD8"):
            return None
        nids = f["nodes"][:{"TRIA3": 3, "TRIA6": 6, "QUAD4": 4,
                            "QUAD8": 8}[stype]]
        pts = [nodes[n] for n in nids]
        if f["kind"] == "shellface":
            orient = float(f.get("side") or 1)
        else:
            # buitennormaal: weg van het zwaartepunt van het element
            cn = conn[f["eid"]][1]
            ce = [sum(nodes[n][c] for n in cn) / len(cn) for c in range(3)]
            cf = [sum(p[c] for p in pts) / len(pts) for c in range(3)]
            n0 = _vcross(_vsub(pts[1], pts[0]), _vsub(pts[-1], pts[0]))
            if stype.startswith("QUAD"):
                n0 = _vcross(_vsub(pts[2], pts[0]), _vsub(pts[3], pts[1]))
            orient = 1.0 if _vdot(n0, _vsub(cf, ce)) >= 0.0 else -1.0
        ps = [pres(p) for p in pts]
        if max(ps) <= 0.0:
            continue
        k = 1 if min(ps) > 0.0 else 8
        if (stype, k) not in rules:
            rules[(stype, k)] = (_sub_rule(stype, k) if k > 1 else
                                 (_TRI_GAUSS if stype.startswith("TRIA")
                                  else _QUAD_GAUSS))
        for xi, eta, w in rules[(stype, k)]:
            n = _face_shape(stype, xi, eta)
            x = [sum(n[i] * pts[i][c] for i in range(len(pts)))
                 for c in range(3)]
            p = pres(x)
            if p <= 0.0:
                continue
            np_ = _face_shape(stype, xi + hd, eta)
            nm = _face_shape(stype, xi - hd, eta)
            ep = _face_shape(stype, xi, eta + hd)
            em = _face_shape(stype, xi, eta - hd)
            dx = [sum((np_[i] - nm[i]) / (2 * hd) * pts[i][c]
                      for i in range(len(pts))) for c in range(3)]
            de = [sum((ep[i] - em[i]) / (2 * hd) * pts[i][c]
                      for i in range(len(pts))) for c in range(3)]
            cr = _vcross(dx, de)        # n dA per d(xi) d(eta)
            for i, nid in enumerate(nids):
                a = acc.setdefault(nid, [0.0, 0.0, 0.0])
                for c in range(3):
                    a[c] -= orient * w * n[i] * p * cr[c]
    return [(nid, tuple(v)) for nid, v in acc.items()]


# ==========================================
# COMPRESSION ONLY EN SYMMETRY: KNOOPGROEPEN PER RICHTING
# ==========================================
def _extra_node_group(model_data, prefix, nids):
    """Nieuwe knoopgroep (DEFI_GROUP NOEUD in de .comm); returns naam."""
    groups = model_data.setdefault("extra_node_groups", OrderedDict())
    name = "{0}{1}".format(prefix, len(groups) + 1)
    groups[name] = sorted(nids)
    return name


def _compression_only(model_data, bc, faces_list):
    """
    Mecway (manual v33 par. 9.5): als frictionless waar de steun op druk
    komt, vrij bij trek. Code-Aster: LIAISON_UNIL (U4.44.11 par. 3.8),
    sum COEF_MULT_i * u_i < COEF_IMPO, per knoop n . u <= 0 met n de naar
    buiten gerichte normaal (de steun ligt aan die kant). Knopen met
    dezelfde normaal vormen een zone. Rotaties van schaalknopen worden niet
    vastgehouden (Mecway's frictionless doet dat wel; NIET vertaald).
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    kinds = set(f["kind"] for f in faces_list)
    if not faces_list or not kinds <= set(["solid", "shellface"]):
        _not_translated(model_data, bc, "Compression only",
                        tr("alleen vlakken van volume-elementen en "
                           "schaalvlakken (hier {0})",
                           "only faces of solid elements and shell faces "
                           "(here {0})").format(sorted(kinds) or "?"))
        return
    if "shellface" in kinds:
        log(tr("WARNING: Compression only op schaalvlakken '{0}': alleen "
               "de normaalverplaatsing, de rotaties blijven vrij.",
               "WARNING: Compression only on shell faces '{0}': only "
               "the normal displacement, the rotations remain free.").format(
                bc["selection"]))
    _, normals = _node_weights_normals(faces_list, nodes, conn)
    zones = OrderedDict()
    for n, v in normals.items():
        zones.setdefault(_round_key(v, 1.0e-3), [v, []])[1].append(n)
    bc["unil_zones"] = [(_extra_node_group(model_data, "BRCO", nids), v)
                        for v, nids in zones.values()]
    bc["aster_dict"] = {}
    log("INFO: Compression only '{0}': {1} knopen in {2} zone(s) "
        "LIAISON_UNIL.".format(bc["selection"], len(normals), len(zones)))


def _plane_normal(points):
    """Normaal van het vlak door de punten (drie ver uit elkaar), of None."""
    if len(points) < 3:
        return None
    p0 = points[0]
    p1 = max(points, key=lambda p: _vdot(_vsub(p, p0), _vsub(p, p0)))
    d = _vsub(p1, p0)

    def off_line(p):
        c = _vcross(d, _vsub(p, p0))
        return _vdot(c, c)
    p2 = max(points, key=off_line)
    nrm = _vcross(d, _vsub(p2, p0))
    if _vdot(nrm, nrm) <= 1.0e-24 * _vdot(d, d) ** 2:
        return None
    return _vunit(nrm)


def _angl_naut3(x, y):
    """
    ANGL_NAUT (graden) met lokale x langs x en lokale y langs (de projectie
    van) y. Nautische hoeken van Code-Aster: alpha om Z, beta om y1, gamma
    om x2 (U4.42.01 ORIENTATION); na alpha en beta is y1 = (-sin a, cos a,
    0), gamma draait y1 naar y.
    """
    a, b, _ = _angl_naut(x)
    ar = math.radians(a)
    y1 = (-math.sin(ar), math.cos(ar), 0.0)
    z1 = _vcross(x, y1)
    return (a, b, math.degrees(math.atan2(_vdot(y, z1), _vdot(y, y1))))


def _symmetry(model_data, bc, faces_list):
    """
    Mecway (manual v33 par. 9.40): verplaatsing loodrecht op het
    symmetrievlak nul; balkuiteinden ook de rotaties om de assen in het
    vlak, schaalranden alleen de rotatie om de rand. LIAISON_OBLIQUE met
    lokaal x = normaal: volumeknopen DX=0, balkknopen DX=DRY=DRZ=0,
    schaalranden (lokaal y = rand) DX=DRY=0.
    """
    nodes = model_data["mesh_nodes"]
    sel = bc["selection"]
    kinds = set(f["kind"] for f in faces_list)
    if not faces_list or not kinds <= set(["solid", "shelledge", "beam"]):
        _not_translated(model_data, bc, "Symmetry",
                        tr("alleen vlakken van volume-elementen, schaalranden "
                           "en balkuiteinden (hier {0})",
                           "only faces of solid elements, shell edges "
                           "and beam ends (here {0})").format(
                            sorted(kinds) or "?"))
        return
    all_nodes = set(n for f in faces_list for n in f["nodes"])
    if bc["params"].get("nodeplane"):
        pts = [nodes[n] for n in sorted(all_nodes)]
        nrm = _plane_normal(pts)
        if nrm is not None:
            size = max(math.sqrt(_vdot(_vsub(p, pts[0]), _vsub(p, pts[0])))
                       for p in pts)
            off = max(abs(_vdot(_vsub(p, pts[0]), nrm)) for p in pts)
            if off > 1.0e-6 * size:
                _not_translated(model_data, bc, "Symmetry",
                                tr("'plane defined by nodes', maar de knopen "
                                   "liggen niet in een vlak (afwijking {0} m; "
                                   "manual par. 9.40: 'all nodes should be "
                                   "coplanar')",
                                   "'plane defined by nodes', but the nodes "
                                   "do not lie in one plane (deviation {0} m; "
                                   "manual par. 9.40: 'all nodes should be "
                                   "coplanar')").format("%.3g" % off))
                return
    else:
        nrm = bc["params"].get("dir")
    if nrm is None:
        _not_translated(model_data, bc, "Symmetry",
                        tr("geen symmetrievlak (normaal nul of knopen op een "
                           "lijn)",
                           "no symmetry plane (zero normal or nodes on a "
                           "line)"))
        return
    beam = set(n for f in faces_list if f["kind"] == "beam"
               for n in f["nodes"])
    edges = OrderedDict()
    for f in faces_list:
        if f["kind"] != "shelledge":
            continue
        p0, p1 = nodes[f["nodes"][0]], nodes[f["nodes"][1]]
        t = _vsub(p1, p0)
        t = _vunit(_vsub(t, tuple(_vdot(t, nrm) * c for c in nrm)))
        if t[0] < -1.0e-9 or (abs(t[0]) <= 1.0e-9 and (
                t[1] < -1.0e-9 or (abs(t[1]) <= 1.0e-9 and t[2] < 0.0))):
            t = (-t[0], -t[1], -t[2])     # richting van de rand is vrij
        edges.setdefault(_round_key(t, 1.0), [t, set()])[1].update(
            n for n in f["nodes"] if n not in beam)
    edge_nodes = set(n for _, ns in edges.values() for n in ns)
    solid = all_nodes - beam - edge_nodes
    angl = _angl_naut(nrm)
    entries = []
    if solid:
        entries.append((_extra_node_group(model_data, "BRSY", solid), angl,
                        ("DX",)))
    if beam:
        entries.append((_extra_node_group(model_data, "BRSY", beam), angl,
                        ("DX", "DRY", "DRZ")))
    for t, ns in edges.values():
        entries.append((_extra_node_group(model_data, "BRSY", ns),
                        _angl_naut3(nrm, t), ("DX", "DRY")))
    bc["oblique"] = entries
    bc["aster_dict"] = {}
    log("INFO: Symmetry '{0}': normaal ({1}), {2} groep(en) "
        "LIAISON_OBLIQUE.".format(sel, ", ".join("%.4g" % c for c in nrm),
                                  len(entries)))


# ==========================================
# VERLIJMD CONTACT -> LIAISON_MAIL
# ==========================================
def _bonded(model_data, c, group_faces, rn):
    """
    Mecway bonded contact (manual v33 par. 9.9.1): de slave-knopen volgen
    het geprojecteerde punt op het master-vlak. Code-Aster: AFFE_CHAR_MECA
    LIAISON_MAIL (U4.44.01): "slave node movements are linked to the
    movements of their projections on the master face". TYPE_RACCORD naar
    de soort knopen (U4.44.01 LIAISON_MAIL): MASSIF (volume-volume), COQUE
    (schaal-schaal), MASSIF_COQUE ("slave nodes ... massive type ... master
    nodes ... shell type"). Schaal (slave) op volume (master): MASSIF met
    de schaalknopen als slave; dat koppelt alleen DX/DY/DZ, de rotaties van
    de schaal blijven vrij. Run 17.4 (balk 1x0,1x0,1 m hex8 + DKT-plaat
    0,01 m op het bovenvlak, eindlast 100 N): DZ -1,11361e-5 m, gelijk aan
    gedeelde knopen (-1,11362e-5); plaat met eigen mesh 7x3 -1,11430e-5
    (zonder plaat -1,32381e-5). COQUE_MASSIF (EPAIS, CHAM_NORMALE,
    catalogus affe_char_meca.py) is daar niet nodig. Schaalranden van één
    component op een volume: COQUE_MASSIF, een stijve verbinding
    (_shell_edge_joint); anders MASSIF, dan werkt de rand als scharnier
    (WARNING).
    Returns een dict voor bridge_to_aster, of None.
    """
    master, slave = rn(c["master"]), rn(c["slave"])
    label = tr("verlijmd contact '{0}' / '{1}'",
               "bonded contact '{0}' / '{1}'").format(c["master"], c["slave"])
    mk = group_faces.get(master, {}).get("kinds", set(["?"]))
    sk = group_faces.get(slave, {}).get("kinds", set(["?"]))

    def skip(why):
        model_data.setdefault("skipped_loads", []).append(label)
        log(tr("ERROR: {0}: {1}. NIET meegenomen.",
               "ERROR: {0}: {1}. NOT included.").format(label, why))
    if master == slave:
        return skip(tr("master en slave zijn dezelfde selectie",
                       "master and slave are the same selection"))
    if mk == set(["solid"]):
        m_type = "MASSIF"
    elif mk == set(["shellface"]):
        m_type = "COQUE"
    else:
        return skip(tr("master moet volumevlakken of schaalvlakken bevatten "
                       "(hier {0})",
                       "master must contain solid faces or shell faces "
                       "(here {0})").format(sorted(mk)))
    if sk == set(["solid"]):
        s_type = "MASSIF"
    elif sk <= set(["shellface", "shelledge"]):
        s_type = "COQUE"
    else:
        return skip(tr("slave: alleen volumevlakken, schaalvlakken of "
                       "schaalranden (hier {0}; balkuiteinden niet)",
                       "slave: only solid faces, shell faces or "
                       "shell edges (here {0}; not beam ends)").format(
                        sorted(sk)))
    raccord = {("MASSIF", "MASSIF"): "MASSIF", ("COQUE", "COQUE"): "COQUE",
               ("COQUE", "MASSIF"): "MASSIF_COQUE",
               ("MASSIF", "COQUE"): "MASSIF"}[(m_type, s_type)]
    # Thermisch (T30/T31): bridge_thermal.bonded_loads vertaalt het contact
    # (LIAISON_MAIL op TEMP of ECHANGE_PAROI) en meldt zelf wat niet lukt;
    # de mechanische meldingen hieronder gelden dan alleen voor het
    # mechanische deel van de keten thermisch -> mechanisch.
    thermal = model_data.get("thermal_data") is not None
    mech = not thermal or model_data.get("thermo_mech")
    edge = None
    if (m_type, s_type) == ("MASSIF", "COQUE") and "shelledge" in sk:
        edge = _shell_edge_joint(model_data, slave)
        if edge is not None:
            raccord = "COQUE_MASSIF"
        elif mech:
            log(tr("WARNING: {0}: schaalrand op een volume koppelt hier "
                   "alleen de verplaatsingen (randen van meerdere "
                   "componenten of ook schaalvlakken); de rand werkt als "
                   "scharnier (geen moment). Stijf: één component per "
                   "verlijmd contact.",
                   "WARNING: {0}: shell edge on a solid only ties the "
                   "displacements here (edges of several components or "
                   "also shell faces); the edge acts as a hinge (no "
                   "moment). Rigid: one component per bonded "
                   "contact.").format(label))
    if c["type"] == "bondedelastic" and mech:
        model_data.setdefault("skipped_loads", []).append(
            tr("{0}: verende laag (kn={1}, kt={2} Pa/m) niet vertaald, star "
               "verlijmd",
               "{0}: elastic layer (kn={1}, kt={2} Pa/m) not translated, "
               "rigidly bonded").format(label, c.get("kn"), c.get("kt")))
        log(tr("WARNING: {0} is 'elastic': Code-Aster LIAISON_MAIL is star; "
               "de stijfheid wordt niet vertaald.",
               "WARNING: {0} is 'elastic': Code-Aster LIAISON_MAIL is "
               "rigid; the stiffness is not translated.").format(label))
    if c.get("tolerance", 0.0) <= 0.0:
        log("INFO: {0}: automatische tolerantie van Mecway; Code-Aster "
            "koppelt alle slave-knopen (geen DISTANCE_MAX).".format(label))
    # Master: bij volumes de moederelementen van de vlakken (<EXCEPTION>
    # PROJECTION4_55 met de randvlakken: "les mailles maîtres doivent avoir
    # la même dimension que l'espace de modélisation", Code-Aster 17.4);
    # bij schalen de schaalelementen zelf (= de vlakgroep). Slave: de
    # knopen van de vlakken (GROUP_NO_ESCL), dan hoeven de randvlakken niet
    # in het model (MODELISA6_96).
    faces = model_data.get("group_face_list", {})
    slave_set = set(n for f in faces.get(slave, []) for n in f["nodes"])
    relations, ddl, rot_ddl = None, None, None
    if raccord == "COQUE" and mech:
        # Schaal op schaal. LIAISON_MAIL kan niet op een kwadratische master
        # (tri6/quad8 -> COQUE_3D: het vraagt DX van de middenknoop van de
        # QUAD9/TRIA7, die alleen rotaties heeft, CHARGES2_31) en laat de
        # drilling-rotatie alleen weg als de master loodrecht op een
        # globale as staat (_coque_ddl). Dan schrijft de bridge de
        # relaties zelf (_bonded_relations, LIAISON_DDL).
        # Volume als slave (MASSIF_COQUE) op een kwadratische schaal rekent
        # LIAISON_MAIL wel goed: quad8-plaat met een hex20-blok eronder,
        # knopen op en midden in de plaatelementen, gelijk aan de relaties
        # van _bonded_relations tot 7 cijfers (Code-Aster 17.4).
        conn = model_data.get("_conn", {})
        m_eids = sorted(set(f["eid"] for f in faces.get(master, [])))
        quadratic = any(conn[e][0] in ("QUAD8", "TRIA6") for e in m_eids
                        if e in conn)
        ddl = _coque_ddl(group_faces.get(master, {}))
        if quadratic:
            # De rotaties kan LIAISON_MAIL wel (de middenknoop heeft
            # DRX/DRY/DRZ en telt dan exact mee); de bridge schrijft alleen
            # de translaties. Loodrecht op een globale as zonder de
            # drilling-rotatie, anders alle drie (DDL kent geen lokaal
            # assenstelsel) met NPREC = -1 (_bonded_relations). Gemeten
            # (Code-Aster 17.4, quad8-plaat 10 x 4 met een rib midden in de
            # elementen, LS-07i/k): in het XY-vlak 1,13419e-5 m, 30 graden
            # gedraaid met alle drie de rotaties 1,13358e-5 m (-0,05 %); de
            # rotaties met LIAISON_DDL zonder de middenknoop gaven
            # 1,2330e-5 (+8,7 %, te slap).
            if ddl is not None:
                rot_ddl = tuple(d for d in ddl if d.startswith("DR"))
            else:
                rot_ddl = ("DRX", "DRY", "DRZ")
                model_data["_bonded_nprec_off"] = True
        if quadratic or ddl is None:
            relations = _bonded_relations(
                model_data, m_eids, slave_set, rot_ddl is None,
                c.get("tolerance", 0.0), label)
            if relations is None:
                log(tr("WARNING: {0}: geen slave-knoop te koppelen (alle "
                       "slave-knopen zijn ook knoop van de master of liggen "
                       "verder dan de tolerantie).",
                       "WARNING: {0}: no slave node to tie (all slave nodes "
                       "are also master nodes or lie beyond the "
                       "tolerance).").format(label))
                relations = []
    if m_type == "MASSIF":
        groups = model_data.setdefault("extra_ma_groups", OrderedDict())
        name = "BRMAIT{0}".format(len(groups) + 1)
        groups[name] = sorted(set(f["eid"] for f in faces.get(master, [])))
        master = name
    out = {"master": master, "raccord": raccord,
           "slave": _extra_node_group(model_data, "BRESCL", slave_set),
           "distance": c.get("tolerance", 0.0), "type": c["type"],
           "kinds": (m_type, s_type), "selections": (c["master"],
                                                     c["slave"]),
           "conductance": c.get("conductance")}
    if thermal:
        log("INFO: {0}: thermische koppeling in bridge_thermal "
            "(LIAISON_MAIL op TEMP of ECHANGE_PAROI).".format(label))
    if relations is not None:
        # mechanisch: LIAISON_DDL i.p.v. LIAISON_MAIL (_render_mpcs); bij
        # rot_ddl daarnaast LIAISON_MAIL voor alleen de rotaties
        out["relations"] = relations
        if rot_ddl:
            out["ddl"] = rot_ddl
            log("INFO: {0}: rotaties via LIAISON_MAIL TYPE_RACCORD='COQUE' "
                "DDL={1}.".format(label, rot_ddl))
        return out
    if mech:
        log("INFO: {0} -> LIAISON_MAIL TYPE_RACCORD='{1}'{2}.".format(
            label, raccord, " (mechanisch deel)" if thermal else ""))
    if raccord == "COQUE":
        out["ddl"] = ddl
    if edge is not None:
        # bridge_to_aster: CHAM_NORMALE = CREA_CHAMP NOEU_GEOM_R NORMALE op
        # de schaalcomponent (docs/ASTER_regels_voorbeelden.md voorbeeld 2)
        out["shell_group"], out["epais"] = edge
    return out


def _coque_ddl(info):
    """
    DDL van LIAISON_MAIL TYPE_RACCORD='COQUE' (schaal op schaal). Zonder DDL
    koppelt Code-Aster alle DDL van de schalen ("par défaut tous les DDL
    des coques", catalogus affe_char_meca.py v17.4), ook de rotatie om de
    normaal van de master (drilling). Die heeft bij DKT alleen een
    fictieve stijfheid (AFFE_CARA_ELEM COQUE COEF_RIGI_DRZ, standaard
    1e-5) en MUMPS vindt dan nulpivots: <EXCEPTION> <FACTOR_11> op DRZ
    (Code-Aster 17.4, NPREC=8; plaatstrook met een lijmnaad in het vlak en
    een rib met de rand op een plaat, TestFiles/Verificatie/
    tests_lineair_statisch.py LS-07; met NPREC=-1 dezelfde oplossing als zonder de
    drilling-koppeling, ook met COEF_RIGI_DRZ=1e-3 nog FACTOR_11; de
    strook van LS-07a 30 graden gedraaid (LS-07f) met alle DDL: idem).
    Buiging en dwarskracht gaan via de verplaatsingen en de twee rotaties
    in het mastervlak. Ligt de master in een vlak loodrecht op een globale
    as, dan blijft die rotatie (DRX/DRY/DRZ) hier weg.
    Returns een tuple met DDL-namen, of None als DDL (globale componenten)
    dat niet kan uitdrukken (scheve of gekromde master): dan schrijft
    _bonded de relaties zelf (_bonded_relations).
    """
    normals = info.get("normals") or []
    if normals:
        n0 = normals[0]
        if all(abs(_vdot(n, n0)) > 1.0 - 1.0e-6 for n in normals):
            for k, comp in enumerate(("DRX", "DRY", "DRZ")):
                if abs(n0[k]) > 1.0 - 1.0e-6:
                    return tuple(d for d in ("DX", "DY", "DZ", "DRX", "DRY",
                                             "DRZ") if d != comp)
    return None


def _face_point(atype, pts, xi, eta):
    """Punt en raakvectoren (d/dxi, d/deta) van een schaalelement in
    (xi, eta); vormfuncties van _face_shape (centrale differentie, exact
    voor kwadratische N)."""
    h = 1.0e-3
    n = _face_shape(atype, xi, eta)
    dxi = [(a - b) / (2 * h) for a, b in zip(_face_shape(atype, xi + h, eta),
                                             _face_shape(atype, xi - h, eta))]
    deta = [(a - b) / (2 * h) for a, b in zip(_face_shape(atype, xi, eta + h),
                                              _face_shape(atype, xi, eta - h))]
    x = tuple(sum(n[i] * pts[i][c] for i in range(len(pts)))
              for c in range(3))
    tx = tuple(sum(dxi[i] * pts[i][c] for i in range(len(pts)))
               for c in range(3))
    te = tuple(sum(deta[i] * pts[i][c] for i in range(len(pts)))
               for c in range(3))
    return n, x, tx, te


def _clamp_face(atype, xi, eta):
    """(xi, eta) terug in het referentie-element (driehoek: xi, eta >= 0,
    xi + eta <= 1; vierhoek: [-1, 1]^2)."""
    if atype.startswith("TRIA"):
        xi, eta = max(xi, 0.0), max(eta, 0.0)
        if xi + eta > 1.0:
            s = min(max(0.5 * (xi - eta + 1.0), 0.0), 1.0)
            xi, eta = s, 1.0 - s
        return xi, eta
    return min(max(xi, -1.0), 1.0), min(max(eta, -1.0), 1.0)


def _project_on_face(atype, pts, p):
    """
    Dichtstbijzijnde punt van p op een schaalelement (Gauss-Newton op
    |x(xi, eta) - p|^2, begrensd tot het element). Returns (afstand, N,
    x, tx, te).
    """
    xi, eta = (1.0 / 3.0, 1.0 / 3.0) if atype.startswith("TRIA") else \
        (0.0, 0.0)
    for _ in range(30):
        n, x, tx, te = _face_point(atype, pts, xi, eta)
        r = _vsub(p, x)
        a11, a12, a22 = _vdot(tx, tx), _vdot(tx, te), _vdot(te, te)
        b1, b2 = _vdot(tx, r), _vdot(te, r)
        det = a11 * a22 - a12 * a12
        if det <= 0.0:
            break
        dxi = (a22 * b1 - a12 * b2) / det
        deta = (a11 * b2 - a12 * b1) / det
        nxi, neta = _clamp_face(atype, xi + dxi, eta + deta)
        moved = abs(nxi - xi) + abs(neta - eta)
        xi, eta = nxi, neta
        if moved < 1.0e-12:
            break
    n, x, tx, te = _face_point(atype, pts, xi, eta)
    d = _vsub(p, x)
    return math.sqrt(_vdot(d, d)), n, x, tx, te


def _bonded_relations(model_data, m_eids, slave_nids, rotations, distance,
                      label):
    """
    Verlijmd contact met een schaal als master, door de bridge zelf
    geschreven als lineaire relaties (LIAISON_DDL, U4.44.01), voor de
    gevallen die LIAISON_MAIL niet aankan:
    - kwadratische master (tri6/quad8 -> COQUE_3D, TRIA7/QUAD9): LIAISON_MAIL
      interpoleert met de 9 (7) knopen en vraagt dan DX van de
      middenknoop, die bij COQUE_3D alleen rotaties heeft
      (<EXCEPTION> <CHARGES2_31>, Code-Aster 17.4, LS-07i). De translaties
      van COQUE_3D horen bij de 8 (6) knopen van de Mecway-cel (R3.07.05,
      NIET in de bron nagelopen; de middenknoop heeft volgens CHARGES2_31
      geen DX). Hier alleen de translaties met de QUAD8/TRIA6-
      vormfuncties (_face_shape, rotations False); de rotaties blijven bij
      LIAISON_MAIL (_bonded: rot_ddl), waar de middenknoop meetelt.
    - scheve of gekromde lineaire master: de rotatie om de
      normaal van de master (drilling) mag niet meedoen (_coque_ddl:
      FACTOR_11), en DDL van LIAISON_MAIL kent alleen globale componenten.
      Hier per slave-knoop twee relaties voor de rotatie in het raakvlak
      van de master in het projectiepunt (t1, t2):
      t_k . theta_slave = sum N_i t_k . theta_i.
      Staat t_k scheef (meer dan één globale component), dan zit de
      drilling-rotatie van de slave (alleen de fictieve stijfheid
      COEF_RIGI_DRZ) in dezelfde DDL als een relatie, en meldt MUMPS een
      bijna-nulpivot (FACTOR_11) terwijl het stelsel regulier is (LS-07f,
      Code-Aster 17.4: NPREC 8 en 10 FACTOR_11, NPREC 12 en -1 rekenen,
      met dezelfde oplossing als LS-07a; COEF_RIGI_DRZ 1e-2 nog
      FACTOR_11, 1e-1 rekent). De marge schaalt met COEF_RIGI_DRZ en de
      dikte, dus geen vaste NPREC: model_data["_bonded_nprec_off"] zet
      NPREC = -1 (bridge_to_aster.generate_AsterSolver_files; RESI_RELA
      blijft het residu controleren: dezelfde strook zonder inklemming
      stopt met FACTOR_57).
    Zoals LIAISON_MAIL (U4.44.01): elke slave-knoop volgt het
    geprojecteerde punt op het dichtstbijzijnde master-element (ook buiten
    het element: dan de rand); met een tolerantie > 0 alleen knopen binnen
    die afstand (DISTANCE_MAX). Slave-knopen die ook knoop van de master
    zijn, blijven buiten de relaties (anders een lege relatie).
    rotations: False bij een kwadratische master (zie boven): alleen de
    translaties.
    Returns [(knopen, ddl, coefficienten)] of None (niets te koppelen).
    """
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    elems = []
    m_nodes = set()
    for eid in m_eids:
        atype, cn = conn[eid]
        pts = [nodes[n] for n in cn]
        lo = [min(q[c] for q in pts) for c in range(3)]
        hi = [max(q[c] for q in pts) for c in range(3)]
        elems.append((atype, cn, pts, lo, hi))
        m_nodes.update(cn)
    rel = []
    shared, far, dmax = 0, 0, 0.0
    mixed = False
    for s in sorted(slave_nids):
        if s in m_nodes:
            shared += 1
            continue
        p = nodes[s]
        boxes = []
        for k, (atype, cn, pts, lo, hi) in enumerate(elems):
            gap = [max(lo[c] - p[c], 0.0, p[c] - hi[c]) for c in range(3)]
            boxes.append((math.sqrt(_vdot(gap, gap)), k))
        boxes.sort()
        best = None
        for bd, k in boxes:
            if best is not None and bd > best[0] * (1.0 + 1.0e-9) + 1.0e-15:
                break
            atype, cn, pts = elems[k][:3]
            res = _project_on_face(atype, pts, p)
            if best is None or res[0] < best[0] - 1.0e-15:
                best = (res[0], k) + res[1:]
        if best is None:
            continue
        d, k, n, x, tx, te = best
        if distance > 0.0 and d > distance:
            far += 1
            continue
        dmax = max(dmax, d)
        cn = elems[k][1]
        terms = [(m, w) for m, w in zip(cn, n) if abs(w) > 1.0e-10]
        for comp in ("DX", "DY", "DZ"):
            rel.append(([s] + [m for m, w in terms], [comp] * (len(terms) + 1),
                        [1.0] + [-w for m, w in terms]))
        if rotations:
            nrm = _vunit(_vcross(tx, te))
            t1 = _vunit(tx)
            t2 = _vcross(nrm, t1)
            for t in (t1, t2):
                comps = [(c, t[i]) for i, c in enumerate(("DRX", "DRY", "DRZ"))
                         if abs(t[i]) > 1.0e-12]
                if len(comps) > 1:
                    mixed = True
                nids, ddl, coef = [], [], []
                for nid, w in [(s, 1.0)] + [(m, -w) for m, w in terms]:
                    for c, tc in comps:
                        nids.append(nid)
                        ddl.append(c)
                        coef.append(w * tc)
                rel.append((nids, ddl, coef))
    if shared:
        log("INFO: {0}: {1} slave-knopen zijn ook knoop van de master en "
            "worden niet gekoppeld.".format(label, shared))
    if far:
        log("INFO: {0}: {1} slave-knopen liggen verder dan de tolerantie "
            "van het mastervlak en worden niet gekoppeld.".format(label, far))
    if not rel:
        return None
    if mixed:
        # bridge_to_aster.generate_AsterSolver_files: NPREC = -1
        model_data["_bonded_nprec_off"] = True
    log("INFO: {0} -> LIAISON_DDL door de bridge ({1} relaties, {2} "
        "slave-knopen, grootste afstand tot de master {3:.3g} m; {4}).".format(
            label, len(rel), len(rel) // (5 if rotations else 3), dmax,
            "translaties en rotaties in het mastervlak" if rotations
            else "alleen translaties"))
    return rel


def _shell_edge_joint(model_data, slave):
    """
    (schaalcomponent, dikte) voor LIAISON_MAIL COQUE_MASSIF als de slave
    alleen schaalranden van één component met een dikte bevat, anders None.
    COQUE_MASSIF (U4.44.01, catalogus affe_char_meca.py: EPAIS en
    CHAM_NORMALE verplicht) verbindt de rand stijf, ook de rotaties: de
    rotatie van een schaalknoop volgt uit de verplaatsingen van het volume
    over de dikte. Doorgerekend in docs/ASTER_regels_voorbeelden.md
    voorbeeld 2 (model S, plaatrand in een blok: 0,00897 mm, ingeklemde
    strook 0,00867 mm). Mecway/CCX zet schalen om in volume-elementen, dan
    is de rand ook stijf (NIET in Mecway geverifieerd).
    """
    faces = model_data.get("group_face_list", {}).get(slave, [])
    if not faces or any(f.get("kind") != "shelledge" for f in faces):
        return None
    elem_elset = model_data.get("_elem_elset", {})
    elsets = set(elem_elset.get(f["eid"]) for f in faces)
    if len(elsets) != 1:
        return None
    es = elsets.pop()
    sec = model_data.get("shell_sections", {}).get(es)
    if not sec or not sec.get("thickness"):
        return None
    return es, sec["thickness"]


# ==========================================
# PINNED SUPPORT: GEMIDDELDE VERPLAATSING NUL
# ==========================================
def _pinned_to_mean(model_data, bc, group_weights):
    """
    Mecway: "A pinned support constrains mean displacement to zero in all
    three directions" (manual v33 par. 9.3); in Mecway gezien: twee knopen
    krijgen tegengestelde verplaatsingen en gelijke reacties. Code-Aster:
    per richting een LIAISON_DDL sum(w_i * u_i) = 0 (U4.44.01). Gewichten:
    gelijk per knoop voor knopen, int(N_i dA)/A voor vlakken van volume-
    elementen. Eén knoop: gewoon DDL_IMPO.
    """
    sel = bc["selection"]
    if sel in model_data.get("node_groups", {}):
        ids = [int(str(i).lstrip("N")) for i in model_data["node_groups"][sel]]
        weights = OrderedDict((n, 1.0) for n in ids)
    elif sel in group_weights:
        weights = group_weights[sel]
    else:
        bc["skip"] = True
        model_data.setdefault("skipped_loads", []).append(
            tr("pinned support op '{0}'",
               "pinned support on '{0}'").format(sel))
        log(tr("ERROR: Pinned support op '{0}': alleen knopen en vlakken van "
               "volume-elementen (Mecway manual par. 9.3). NIET meegenomen.",
               "ERROR: Pinned support on '{0}': only nodes and faces of "
               "solid elements (Mecway manual par. 9.3). NOT included.")
            .format(sel))
        return
    if len(weights) < 2:
        return
    total = sum(weights.values())
    bc["aster_keyword"] = "LIAISON_DDL"
    bc["pin_weights"] = [(n, w / total) for n, w in weights.items()]
    log("INFO: Pinned support '{0}': gemiddelde verplaatsing nul over {1} "
        "knopen (LIAISON_DDL).".format(sel, len(weights)))


# ==========================================
# MOMENT: OP EEN KNOOP OF ALS KRACHTEN OVER VLAKKEN
# ==========================================
def _moment_to_forces(model_data, bc, group_integrals, group_weights=None):
    """
    Mecway (manual v33 par. 9.18): een moment werkt op een enkele knoop met
    rotatie-DOFs, of als krachten verdeeld over vlakken (schaal of volume)
    om de as door hun zwaartepunt.

    Knopen: een nodeselection, of een faceselection van balkuiteinden
    (faceid 2/3 = knoop 1/2, _FACE_CORNERS 'SEG'); die staat in het mesh als
    GROUP_NO (zoals een kracht op balkuiteinden) en telt via group_weights.
    Een uiteinde = een knoop: FORCE_NODALE MX/MY/MZ op die knoop.

    Vlakken: lineair verdeelde oppervlaktekracht t(x) = omega x (x - c),
    met omega = Theta^-1 M en Theta = int(|r|^2 I - r r^T) dA (r = x - c),
    zodat int(r x t) dA = M en de resulterende kracht nul is. Consistente
    knoopkrachten: f_i = omega x int(N_i (x - c) dA). Per momentcomponent
    staan de knoopkrachten voor een eenheidsmoment in bc["node_loads"]
    (bridge_to_aster._build_charges schaalt ze, ook met een tijdsfunctie).
    """
    sel = bc["selection"]
    if bc["aster_target"] == "GROUP_NO":
        if sel in model_data.get("node_groups", {}):
            n = len(model_data["node_groups"][sel])
        else:
            # balkvlakken (face_node_groups): de knopen van de vlakken
            n = len((group_weights or {}).get(sel, ()))
        if n != 1:
            bc["skip"] = True
            model_data.setdefault("skipped_loads", []).append(
                tr("moment op '{0}' ({1} knopen)",
                   "moment on '{0}' ({1} nodes)").format(sel, n))
            log(tr("ERROR: Moment op '{0}': Mecway staat een moment op "
                   "knopen (of balkuiteinden) alleen toe op een enkele knoop "
                   "met rotatie-DOFs, hier {1} knopen. NIET meegenomen.",
                   "ERROR: Moment on '{0}': Mecway only allows a moment on "
                   "nodes (or beam ends) on a single node with rotational "
                   "DOFs, here {1} nodes. NOT included.").format(sel, n))
        return
    if sel not in group_integrals:
        bc["skip"] = True
        model_data.setdefault("skipped_loads", []).append(
            tr("moment op '{0}'", "moment on '{0}'").format(sel))
        log(tr("ERROR: Moment op '{0}': alleen op een knoop of op vlakken "
               "van schaal- of volume-elementen. NIET meegenomen.",
               "ERROR: Moment on '{0}': only on a node or on faces "
               "of shell or solid elements. NOT included.").format(sel))
        return
    w, m, S = group_integrals[sel]
    area = sum(w.values())
    c = [sum(mi[k] for mi in m.values()) / area for k in range(3)]
    rr = [[S[a][b] - area * c[a] * c[b] for b in range(3)] for a in range(3)]
    # spoor van rr (niet 'tr' noemen: dat is de vertaalfunctie)
    trace = rr[0][0] + rr[1][1] + rr[2][2]
    theta_inv = _inv3([[(trace if a == b else 0.0) - rr[a][b]
                        for b in range(3)] for a in range(3)])
    node_loads = OrderedDict()
    for k, key in enumerate(("MX", "MY", "MZ")):
        if key not in bc["aster_dict"]:
            continue
        omega = [theta_inv[a][k] for a in range(3)]
        node_loads[key] = [
            (n, _vcross(omega, tuple(m[n][j] - w[n] * c[j] for j in range(3))))
            for n in w]
    bc["aster_keyword"] = "FORCE_NODALE"
    bc["node_loads"] = node_loads
    log("INFO: Moment op vlakken '{0}': krachten over {1} knopen om het "
        "zwaartepunt ({2}).".format(
            sel, len(w), ", ".join("%.6g" % v for v in c)))


# ==========================================
# CONTACT: ZONES MET GEDEELDE SLAVE-KNOPEN SAMENVOEGEN
# ==========================================
# Voorwaarden die alle verplaatsingen van een knoop vastleggen; zit een
# contact-slaveknoop daar ook in, dan is de matrix singulier (pivot op
# LAGS_C, MECANONLINE9_4; gezien bij een buigmodel: profiel ingeklemd en
# slave).
# Gedeeltelijke voorwaarden (displacement met enkele componenten,
# frictionless, symmetry) niet: die botsen alleen in de normaalrichting
# (een symmetrievlak loodrecht op het contact is gewoon toegestaan).
_SLAVE_CONFLICT_BCS = ("fixed",)


def _exclude_fixed_slaves(model_data, group_integrals):
    """
    Slaveknopen die ook een kinematische voorwaarde hebben uit het contact
    halen met SANS_GROUP_NO, zoals Code-Aster aanraadt (U4.44.11 par. 3.1.3:
    "recommended when the latter are subjected to boundary conditions in
    the expected direction of the contact (embedding for example)").
    Zet per zone c["sans_groups"] (knoopgroepen) en vult
    model_data["contact_sans_from_ma"] = {knoopgroep: vlakgroep} voor
    DEFI_GROUP; logt per zone hoeveel knopen.
    """
    node_groups = model_data.get("node_groups", {})
    unions = model_data.get("group_ma_unions", {})
    from_ma = model_data.setdefault("contact_sans_from_ma", {})

    def to_int(n):
        return int(str(n).lstrip("N"))

    bc_nodes = []           # [(knoopgroepnaam, set knopen, bron)]
    for bc in model_data.get("bcs", []):
        sel = bc.get("selection")
        if bc.get("type") not in _SLAVE_CONFLICT_BCS or not sel:
            continue
        if sel in node_groups:
            nodes = set(to_int(n) for n in node_groups[sel])
            bc_nodes.append((sel, nodes, sel))
        elif sel in group_integrals:
            nodes = set(to_int(n) for n in group_integrals[sel][0])
            bc_nodes.append((sel, nodes, sel))
    for c in model_data.get("contacts", []):
        slave_groups = unions.get(c["slave"], [c["slave"]])
        slave = set()
        for g in slave_groups:
            slave |= set(to_int(n) for n in group_integrals.get(g, [{}])[0])
        sans, count = [], set()
        for name, nodes, source in bc_nodes:
            common = slave & nodes
            if not common:
                continue
            if name not in node_groups:
                from_ma[name] = source
            if name not in sans:
                sans.append(name)
            count |= common
        if sans:
            c["sans_groups"] = sans
            log("INFO: Contact (slave '{0}'): {1} slave-knopen hebben ook een "
                "vaste voorwaarde ({2}) en worden uitgesloten met "
                "SANS_GROUP_NO (U4.44.11 par. 3.1.3).".format(
                    c["slave"], len(count), ", ".join(sans)))


# Voorwaarden die als relatie (LIAISON_*) of gedeeltelijke DDL_IMPO worden
# geschreven; overlap daartussen (of met fixed) kan een dubbele Lagrange-
# voorwaarde geven (FACTOR_42/57). Fixed met fixed is gewoon dubbel DDL_IMPO.
_RELATION_BCS = ("pinnedsupport", "frictionless", "symmetry", "displacement",
                 "noderotation", "velocity")

# Naast fixed sluit bridge_to_aster._build_charges de fixed-knopen al uit
# (SANS_GROUP_* bij LIAISON_OBLIQUE, FACE_IMPO en de DDL_IMPO van deze
# soorten); die overlap hoeft niet gemeld te worden.
_SANS_FIXED_BCS = ("frictionless", "symmetry", "displacement",
                   "noderotation", "velocity")


_ALL_DOFS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")


def _global_dofs(ddls, angl):
    """Globale vrijheidsgraden die ddls in het lokale stelsel van ANGL_NAUT
    angl raken (None: ddls zijn al globaal). Lokaal x = (cos a cos b,
    sin a cos b, -sin b) (U4.44.01 LIAISON_OBLIQUE, nautische hoeken); een
    lokale y/z-component ligt in het vlak loodrecht op x: ruim genomen alle
    globale assen die niet langs x liggen."""
    if angl is None:
        return set(ddls)
    a, b = math.radians(angl[0]), math.radians(angl[1])
    x = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), -math.sin(b))
    out = set()
    for d in ddls:
        prefix = "DR" if d.startswith("DR") else "D"
        if d.endswith("X"):
            axes = [i for i in range(3) if abs(x[i]) > 1.0e-9]
        else:
            axes = [i for i in range(3) if abs(x[i]) < 1.0 - 1.0e-9]
        out.update(prefix + "XYZ"[i] for i in axes)
    return out


def _local_axes(angl):
    """Lokale x, y, z (globaal) bij ANGL_NAUT (alpha, beta, gamma) in graden:
    R = Rz(alpha) Ry(beta) Rx(gamma), lokaal x = (cos a cos b, sin a cos b,
    -sin b) (U4.44.01 LIAISON_OBLIQUE; U4.42.01 ORIENTATION). Gamma draait
    y1 = (-sin a, cos a, 0) om x (zoals _angl_naut3)."""
    a, b, g = [math.radians(v) for v in angl]
    x = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), -math.sin(b))
    y = (math.cos(a) * math.sin(b) * math.sin(g) - math.sin(a) * math.cos(g),
         math.sin(a) * math.sin(b) * math.sin(g) + math.cos(a) * math.cos(g),
         math.cos(b) * math.sin(g))
    return x, y, _vcross(x, y)


def _aligned_dofs(ddls, angl):
    """Globale vrijheidsgraden die ddls in het lokale stelsel van angl
    precies vastleggen, als elke gebruikte lokale as langs een globale as
    ligt; anders None (de relatie mengt globale vrijheidsgraden)."""
    if angl is None:
        return set(ddls)
    axes = dict(zip("XYZ", _local_axes(angl)))
    out = set()
    for d in ddls:
        v = axes[d[-1]]
        i = max(range(3), key=lambda k: abs(v[k]))
        if abs(v[i]) < 1.0 - 1.0e-9:
            return None
        out.add(("DR" if d.startswith("DR") else "D") + "XYZ"[i])
    return out


def _bc_dofs(bc, faces=None):
    """Globale vrijheidsgraden die een kinematische voorwaarde vastlegt
    (ruim: bij twijfel meer). faces: group_faces-entry van de selectie
    (normalen, voor frictionless op een vlak volumevlak)."""
    t = bc["type"]
    d = bc.get("aster_dict") or {}
    if t == "fixed":
        return set(_ALL_DOFS) if "BLOCAGE" in d else set(
            k for k in d if k in _ALL_DOFS)
    if t == "pinnedsupport":
        return set(("DX", "DY", "DZ"))
    if bc.get("oblique") is not None:   # symmetry, frictionless per knoop
        out = set()
        for _group, angl, ddls in bc["oblique"]:
            out |= _global_dofs(ddls, angl)
        return out
    if "DNOR" in d:                      # frictionless op volumevlakken
        normals = (faces or {}).get("normals") or []
        if normals and all(abs(_vdot(normals[0], n)) > 1.0 - 1.0e-6
                           for n in normals):
            return set("D" + "XYZ"[i] for i in range(3)
                       if abs(normals[0][i]) > 1.0e-9)
        return set(("DX", "DY", "DZ"))
    keys = [k for k in d if k in _ALL_DOFS]
    return _global_dofs(keys, d.get("ANGL_NAUT")) if keys else set(_ALL_DOFS)


def _ddl_kind(bc):
    """'const' of 'timed' voor een gewone DDL_IMPO (displacement, node
    rotation, velocity langs een globale as; pinned support op een knoop),
    anders None. Alle constante DDL_IMPO staan in een AFFE_CHAR_MECA, alle
    tijdsafhankelijke in een AFFE_CHAR_MECA_F (bridge_to_aster.
    _build_charges)."""
    if bc.get("aster_keyword") != "DDL_IMPO" or bc["type"] not in (
            "displacement", "noderotation", "velocity", "pinnedsupport"):
        return None
    if bc.get("pin_weights") or bc.get("oblique") is not None:
        return None
    values = [v for k, v in (bc.get("aster_dict") or {}).items()
              if k in _ALL_DOFS]
    if not values:
        return None
    # een formule in x, y, z (PositionFormula) is ook een functie
    # (AFFE_CHAR_MECA_F)
    return "timed" if any(isinstance(v, list) or is_position(v)
                          for v in values) else "const"


def _ddl_values(bcs):
    """{DOF: waarde} van de DDL_IMPO-voorwaarden bcs (de laatste wint, zoals
    in Code-Aster)."""
    out = {}
    for bc in bcs:
        for k, v in (bc.get("aster_dict") or {}).items():
            if k in _ALL_DOFS:
                out[k] = v
    return out


def _exact_relation_dofs(model_data, bc, nodes_of, faces):
    """
    {knoop: set(globale DOF)} die een relatie (symmetry, frictionless)
    met waarde 0 precies vastlegt, alleen waar de lokale assen langs de
    globale assen liggen; None als dat niet eenduidig is.
    """
    extra = model_data.get("extra_node_groups", {})
    d = bc.get("aster_dict") or {}
    out = {}
    if bc.get("oblique") is not None:
        for group, angl, ddls in bc["oblique"]:
            dofs = _aligned_dofs(ddls, angl)
            if dofs is None:
                return None
            for n in extra.get(group, ()):
                out.setdefault(n, set()).update(dofs)
        return out
    if bc["type"] != "frictionless":
        return None
    if "DNOR" in d:
        normals = (faces or {}).get("normals") or []
        if (isinstance(d["DNOR"], list) or d["DNOR"] != 0.0 or not normals
                or not all(abs(_vdot(normals[0], n)) > 1.0 - 1.0e-9
                           for n in normals)):
            return None
        dofs = _aligned_dofs(["DX"], _angl_naut(normals[0]))
    elif "ANGL_NAUT" in d:
        keys = [k for k in d if k in _ALL_DOFS]
        if any(isinstance(d[k], list) or d[k] != 0.0 for k in keys):
            return None
        dofs = _aligned_dofs(keys, d["ANGL_NAUT"])
    else:
        return None
    if dofs is None:
        return None
    return dict((n, set(dofs)) for n in nodes_of(bc["selection"]))


def _drop_covered_ddl(model_data, nodes_of, group_faces):
    """
    Een opgelegde verplaatsing/rotatie 0 langs een globale as (DDL_IMPO) op
    knopen die een symmetry of frictionless (waarde 0) al in precies die
    richting vastlegt, is dezelfde voorwaarde. Mecway reduceert dat zelf
    (manual v33 par. 9.6: "reduce them to a minimum equivalent set");
    Code-Aster stopt met <EXCEPTION> FACTOR_42 (matrice singulière;
    gezien met Code-Aster 17.4: displacement X=0 en symmetry/frictionless
    met normaal X op hetzelfde vlak). De relatie blijft (die legt soms ook
    rotaties vast); de DDL_IMPO krijgt een knoopgroep zonder die knopen
    (KNOWN_BUGS 8). Alleen voor selecties waarvan de knopen vastliggen
    (knopen, vlakken van volumes, schaalranden, balkuiteinden); niet voor
    schaalvlakken en elementselecties (COQUE_3D: middenknoop in de job).
    """
    rels = []
    for bc in model_data.get("bcs", []):
        if bc.get("skip") or bc["type"] not in ("symmetry", "frictionless"):
            continue
        ex = _exact_relation_dofs(model_data, bc, nodes_of,
                                  group_faces.get(bc["selection"]))
        if ex:
            rels.append((bc, ex))
    if not rels:
        return
    face_list = model_data.get("group_face_list", {})
    node_groups = model_data.get("node_groups", {})
    for bc in model_data.get("bcs", []):
        if (bc.get("skip") or _ddl_kind(bc) != "const"
                or bc["type"] not in ("displacement", "noderotation")):
            continue
        values = _ddl_values([bc])
        if any(v != 0.0 for v in values.values()):
            continue
        sel = bc["selection"]
        kinds = set(f["kind"] for f in face_list.get(sel, []))
        if sel not in node_groups and not (
                kinds and kinds <= set(["solid", "shelledge", "beam"])):
            continue
        dofs = set(values)
        nodes = nodes_of(sel)
        covered = set()
        by = []
        for rbc, ex in rels:
            hit = set(n for n in nodes if dofs <= ex.get(n, set()))
            if hit:
                covered |= hit
                by.append("{0} '{1}'".format(rbc["type"], rbc["selection"]))
        if not covered:
            continue
        rest = nodes - covered
        log("INFO: {0} '{1}' ({2}=0): {3} knoop/knopen vallen al onder {4} "
            "en worden uit de DDL_IMPO gehaald (dubbele voorwaarde, "
            "FACTOR_42).".format(bc["type"], sel, "/".join(sorted(dofs)),
                                 len(covered), ", ".join(by)))
        if not rest:
            bc["skip"] = True
            continue
        bc["selection"] = _extra_node_group(model_data, "BROV", rest)
        bc["aster_target"] = "GROUP_NO"


def _unit_rows(ddls, angl=None):
    """[(soort, vector)] voor vrijheidsgraden ddls ('DX', 'DRY', ...) in het
    lokale stelsel van ANGL_NAUT angl (None: globaal); soort 'D' of 'DR'."""
    axes = _local_axes(angl) if angl is not None else (
        (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    return [("DR" if d.startswith("DR") else "D", axes["XYZ".index(d[-1])])
            for d in ddls]


def _rank3(vectors):
    """Rang van een stel 3D-vectoren (Gram-Schmidt, relatieve tolerantie)."""
    basis = []
    for v in vectors:
        w = list(v)
        for b in basis:
            d = _vdot(w, b)
            w = [w[k] - d * b[k] for k in range(3)]
        n = math.sqrt(_vdot(w, w))
        if n > 1.0e-6:
            basis.append([c / n for c in w])
    return len(basis)


def _dependent_dofs(rows_a, rows_b):
    """Globale vrijheidsgraden waarin de voorwaarden rows_a en rows_b in een
    knoop lineair afhankelijk zijn (samen een dubbele voorwaarde: rang van
    de unie kleiner dan de som), of een lege set."""
    out = set()
    for kind in ("D", "DR"):
        a = [v for k, v in rows_a if k == kind]
        b = [v for k, v in rows_b if k == kind]
        if not a or not b or _rank3(a + b) == _rank3(a) + _rank3(b):
            continue
        for i in range(3):
            if (any(abs(v[i]) > 1.0e-9 for v in a)
                    and any(abs(v[i]) > 1.0e-9 for v in b)):
                out.add(kind + "XYZ"[i])
    return out


def _constraint_rows(model_data, bc):
    """
    Functie knoop -> [(soort, vector)]: de richtingen die voorwaarde bc in
    die knoop vastlegt (globaal; per knoop bij symmetry/frictionless met
    knoopnormalen, FACE_IMPO DNOR met de gemiddelde vlaknormaal zoals
    Code-Aster die per knoop neemt).
    """
    t = bc["type"]
    d = bc.get("aster_dict") or {}
    if t == "fixed":
        rows = _unit_rows(_ALL_DOFS if "BLOCAGE" in d else
                          [k for k in d if k in _ALL_DOFS])
        return lambda n: rows
    if t == "pinnedsupport":
        rows = _unit_rows(("DX", "DY", "DZ"))
        return lambda n: rows
    if bc.get("oblique") is not None:
        extra = model_data.get("extra_node_groups", {})
        per = {}
        for group, angl, ddls in bc["oblique"]:
            rows = _unit_rows(ddls, angl)
            for n in extra.get(group, ()):
                per.setdefault(n, []).extend(rows)
        return lambda n: per.get(n, [])
    if "DNOR" in d:
        faces = [f for f in model_data.get("group_face_list", {}).get(
            bc["selection"], []) if f["kind"] == "solid"]
        try:
            _w, normals = _node_weights_normals(
                faces, model_data["mesh_nodes"], model_data["_conn"])
        except ZeroDivisionError:
            rows = _unit_rows(("DX", "DY", "DZ"))
            return lambda n: rows
        return lambda n: [("D", normals[n])] if n in normals else []
    rows = _unit_rows([k for k in d if k in _ALL_DOFS], d.get("ANGL_NAUT"))
    return lambda n: rows


def _report_constraint_overlaps(model_data, group_integrals, group_faces=None):
    """
    Overlap van kinematische voorwaarden (en RBE-slaves) per paar dat in
    gedeelde knopen een afhankelijke richting vastlegt (_dependent_dofs; een
    normaal naast een raaklijn telt niet). Mecway lost overlap zelf op
    (manual v33 par. 9.6), Code-Aster niet altijd:
      - fixed naast frictionless/symmetry/displacement/noderotation/
        velocity: al opgelost (SANS_GROUP_* in bridge_to_aster);
      - DDL_IMPO 0 die al onder een symmetry/frictionless 0 in dezelfde
        globale richting valt: opgelost (_drop_covered_ddl);
      - twee DDL_IMPO in dezelfde last (beide constant of beide
        tijdsafhankelijk): Code-Aster neemt de laatste (gezien met Code-
        Aster 17.4, ook in AFFE_CHAR_MECA_F); alleen bij verschillende
        waarden een WARNING;
      - constant naast tijdsafhankelijk op dezelfde DOF: <EXCEPTION>
        ASSEMBLA_26 (gezien met Code-Aster 17.4): WARNING;
      - twee symmetry's met dezelfde relaties per knoop: Code-Aster laat de
        dubbele relatie vallen (gezien met Code-Aster 17.4): geen melding;
      - verder: WARNING met de selecties en de gedeelde vrijheidsgraden
        (FACTOR_42/57 of een nulpivot, KNOWN_BUGS 8).
    """
    node_groups = model_data.get("node_groups", {})
    extra = model_data.get("extra_node_groups", {})
    face_list = model_data.get("group_face_list", {})
    elem_sel = model_data.get("element_selections", {})
    conn = model_data.get("_conn", {})
    group_faces = group_faces or {}

    def nodes_of(sel):
        if sel in node_groups:
            return set(int(str(n).lstrip("N")) for n in node_groups[sel])
        if sel in extra:
            return set(extra[sel])
        if sel in face_list:
            return set(n for f in face_list[sel] for n in f["nodes"])
        if sel in elem_sel:
            return set(n for e in elem_sel[sel] if e in conn
                       for n in conn[e][1])
        if sel in group_integrals:
            return set(int(str(n).lstrip("N")) for n in group_integrals[sel][0])
        return set()

    _drop_covered_ddl(model_data, nodes_of, group_faces)

    # Per (soort, selectie) de vastgelegde vrijheidsgraden (globaal); een
    # selectie met meerdere items van dezelfde soort (bv. displacement x en
    # y) wordt een item, zodat elk paar een keer gemeld wordt.
    items = OrderedDict()
    for bc in model_data.get("bcs", []):
        if (bc.get("type") in _RELATION_BCS + ("fixed",)
                and bc.get("selection") and not bc.get("skip")):
            it = items.setdefault((bc["type"], bc["selection"]),
                                  [set(), [], []])
            it[0].update(_bc_dofs(bc, group_faces.get(bc["selection"])))
            it[1].append(bc)
            it[2].append(_constraint_rows(model_data, bc))
    all_rows = _unit_rows(_ALL_DOFS)
    for c in model_data.get("couplings", []):
        it = items.setdefault(("koppeling", c.get("slave_group_ma") or
                               c.get("slave_group")), [set(), [], []])
        it[0].update(_ALL_DOFS)
        it[2].append(lambda n: all_rows)
    sets = [(t, s, nodes_of(s), dofs, bcs, rows)
            for (t, s), (dofs, bcs, rows) in items.items()]

    def kind(bcs):
        kinds = set(_ddl_kind(b) for b in bcs)
        return list(kinds)[0] if bcs and len(kinds) == 1 else None

    def oblique_spec(bcs, n):
        spec = set()
        for b in bcs:
            for group, angl, ddls in b.get("oblique") or ():
                if n in extra.get(group, ()):
                    spec.add((tuple(round(a, 9) for a in angl),
                              tuple(ddls)))
        return frozenset(spec)

    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            (ta, sa, na, da, ba, ra), (tb, sb, nb, db, bb, rb) = (
                sets[i], sets[j])
            if not da & db:
                continue        # andere vrijheidsgraden: geen conflict
            if ta == "fixed" and tb == "fixed":
                continue
            if "fixed" in (ta, tb) and set((ta, tb)) - set(
                    ("fixed",) + _SANS_FIXED_BCS) == set():
                continue
            # Alleen knopen waar de richtingen echt afhankelijk zijn (een
            # normaal naast een raaklijn is geen dubbele voorwaarde).
            common = set()
            dofs = set()
            for n in na & nb:
                dep = _dependent_dofs([r for f in ra for r in f(n)],
                                      [r for f in rb for r in f(n)])
                if dep:
                    common.add(n)
                    dofs |= dep
            if not common:
                continue
            dof_txt = "/".join(d for d in _ALL_DOFS if d in dofs)
            ka, kb = kind(ba), kind(bb)
            if ka and kb:
                va, vb = _ddl_values(ba), _ddl_values(bb)
                shared = [d for d in _ALL_DOFS if d in va and d in vb]
                if ka != kb:
                    log(tr("WARNING: Voorwaarden {0} '{1}' en {2} '{3}' "
                           "leggen {4} op in {5} knoop/knopen (o.a. N{6}), de "
                           "ene constant en de andere tijdsafhankelijk: Code-"
                           "Aster stopt dan met ASSEMBLA_26 (dubbel "
                           "opgelegd). Pas de selecties in Mecway aan.",
                           "WARNING: Constraints {0} '{1}' and {2} '{3}' "
                           "prescribe {4} on {5} node(s) (e.g. N{6}), one "
                           "constant and the other time dependent: Code-Aster "
                           "then stops with ASSEMBLA_26 (prescribed twice). "
                           "Adjust the selections in Mecway.").format(
                            ta, sa, tb, sb, dof_txt, len(common), min(common)))
                elif any(va[d] != vb[d] for d in shared):
                    log(tr("WARNING: Voorwaarden {0} '{1}' en {2} '{3}' "
                           "leggen "
                           "{4} op in {5} knoop/knopen (o.a. N{6}) met "
                           "verschillende waarden; Code-Aster neemt de "
                           "laatste ('{3}'). Pas zo nodig de selecties in "
                           "Mecway aan.",
                           "WARNING: Constraints {0} '{1}' and {2} '{3}' "
                           "prescribe {4} on {5} node(s) (e.g. N{6}) with "
                           "different values; Code-Aster takes the last one "
                           "('{3}'). Adjust the selections in Mecway if "
                           "necessary.").format(
                            ta, sa, tb, sb, dof_txt, len(common), min(common)))
                continue
            if ta == tb == "symmetry" and all(
                    oblique_spec(ba, n) == oblique_spec(bb, n)
                    for n in common):
                continue    # dezelfde relaties: Code-Aster laat er een vallen
            log(tr("WARNING: Voorwaarden {0} '{1}' en {2} '{3}' delen "
                   "{4} knoop/knopen (o.a. N{5}) op {6}. Code-Aster kan dan "
                   "stoppen met FACTOR_42/57 of een nulpivot (dubbele "
                   "voorwaarde); Mecway lost dat zelf op. Pas zo nodig "
                   "de selecties in Mecway aan.",
                   "WARNING: Constraints {0} '{1}' and {2} '{3}' share "
                   "{4} node(s) (e.g. N{5}) on {6}. Code-Aster may then "
                   "stop with FACTOR_42/57 or a zero pivot (duplicate "
                   "constraint); Mecway resolves this itself. Adjust "
                   "the selections in Mecway if necessary.").format(
                    ta, sa, tb, sb, len(common), min(common), dof_txt))


def _check_contact_sides(label, master, slave, group_integrals):
    """
    WARNING als de slave-kant duidelijk grover is dan de master. Code-Aster
    controleert alleen de slave-punten tegen de master-vlakken (U2.04.04
    par. 2.2: slave = de fijnste mesh, master = de stijfste/grofste kant);
    een fijne master dringt dan tussen de grove slave-punten door zonder
    contactkracht. Gezien bij een buigmodel: rol (60 vlakken) slave
    op het profiel (4482 vlakken), de rol ging door het profiel heen; met
    master/slave omgewisseld ontstond wel contact. De bridge wisselt niet
    zelf: in Mecway is de keuze aan de gebruiker.
    """
    def size(group):
        # Karakteristieke elementmaat: sqrt(oppervlak / aantal knopen); het
        # oppervlak is de som van de knoopgewichten (integraal N dA).
        w = group_integrals.get(group, [{}])[0]
        area = sum(w.values())
        return (area / len(w)) ** 0.5 if w and area > 0 else None
    hm, hs = size(master), size(slave)
    if hm and hs and hs > 2.0 * hm:
        # %-opmaak: "{0:.3g}".format() volgt in IronPython de landinstelling
        # (zie bridge_mesh._real)
        log(tr("WARNING: {0}: de slave-vlakken zijn {1}x zo grof als "
               "de master (elementmaat {2} tegen {3} m). Code-Aster "
               "controleert alleen slave-punten tegen master-vlakken; de "
               "fijne master kan dan zonder contactkracht door de slave "
               "dringen. Maak in Mecway de fijnste kant de slave (U2.04.04 "
               "par. 2.2).",
               "WARNING: {0}: the slave faces are {1}x as coarse as "
               "the master (element size {2} vs {3} m). Code-Aster "
               "only checks slave points against master faces; the "
               "fine master can then penetrate the slave without contact "
               "force. In Mecway, make the finest side the slave (U2.04.04 "
               "par. 2.2).").format(label, "%.1f" % (hs / hm), "%.3g" % hs,
                                    "%.3g" % hm))


def _merge_contact_zones(pairs, group_integrals, unions):
    """
    Code-Aster verbiedt knopen die in de slave-vlakken van twee zones zitten
    (<EXCEPTION> <CONTACT2_16>, Code-Aster 17.4; SANS_GROUP_NO helpt niet,
    de controle gaat over de vlakken). Mecway kent die beperking niet: een
    profiel kan slave zijn tegen een mes en tegen een contour. Master en
    slave wisselen (de hint van CONTACT2_16) maakt het gereedschap slave,
    terwijl de master het stijfste vlak hoort te zijn (U2.04.04 par. 2.2);
    bij een knipmodel (dynamisch, contact) divergeerde dat al in de eerste
    stap.

    Daarom worden paren waarvan de slave-vlakken knopen delen samengevoegd
    tot een zone: master = unie van de masters, slave = unie van de slaves
    (DEFI_GROUP CREA_GROUP_MA UNION via `unions`). Bij het koppelen zoekt
    Code-Aster per slave-punt het dichtstbijzijnde master-element.
    Wrijving van een samengevoegde zone: de grootste coefficient.
    """
    def nodes_of(group):
        return set(group_integrals.get(group, [{}])[0].keys())

    zones = []          # [{"pairs": [...], "nodes": set()}]
    for pair in pairs:
        s_nodes = nodes_of(pair["slave"])
        hits = [z for z in zones if z["nodes"] & s_nodes]
        merged = {"pairs": [pair], "nodes": set(s_nodes)}
        for z in hits:
            merged["pairs"] = z["pairs"] + merged["pairs"]
            merged["nodes"] |= z["nodes"]
            zones.remove(z)
        zones.append(merged)

    def union(prefix, groups, k):
        uniq = []
        for g in groups:
            if g not in uniq:
                uniq.append(g)
        if len(uniq) == 1:
            return uniq[0]
        name = "{0}{1}".format(prefix, k)
        unions[name] = uniq
        return name

    result = []
    for k, z in enumerate(zones):
        ps = z["pairs"]
        if len(ps) == 1:
            result.append(ps[0])
            continue
        zone = dict(ps[0])
        zone["master"] = union("CMAIT", [p["master"] for p in ps], k + 1)
        zone["slave"] = union("CESCL", [p["slave"] for p in ps], k + 1)
        zone["friction"] = max(p.get("friction", 0.0) for p in ps)
        # penalty-stijfheden (contact_algo PENALISATION): de grootste
        zone["kn"] = max(p.get("kn", 0.0) for p in ps)
        zone["kt"] = max(p.get("kt", 0.0) for p in ps)
        if len(set(p.get("friction", 0.0) for p in ps)) > 1:
            log(tr("WARNING: Samengevoegde contactzone met verschillende "
                   "wrijvingscoefficienten; de grootste ({0}) wordt gebruikt.",
                   "WARNING: Merged contact zone with different friction "
                   "coefficients; the largest ({0}) is used.")
                .format(zone["friction"]))
        log(tr("WARNING: Contactparen {0} delen slave-knopen en zijn "
               "samengevoegd tot een zone (master '{1}', slave '{2}'; "
               "Code-Aster CONTACT2_16).",
               "WARNING: Contact pairs {0} share slave nodes and have been "
               "merged into one zone (master '{1}', slave '{2}'; "
               "Code-Aster CONTACT2_16).")
            .format(", ".join("{0}/{1}".format(p["master"], p["slave"])
                              for p in ps), zone["master"], zone["slave"]))
        result.append(zone)
    return result


# ==========================================
# FRICTIONLESS SUPPORT
# ==========================================
def _frictionless(model_data, bc, faces, faces_list=None):
    """
    Volumevlakken: FACE_IMPO DNOR (bridge_bcs.FrictionlessBC); geeft True,
    dan moeten de randelementen in het model (skin_groups, ORIE_PEAU).
    Vlakke schaalvlakken: LIAISON_OBLIQUE met de lokale x-as langs de
    normaal: DX = -waarde en DRY = DRZ = 0 (rotaties om de assen in het
    vlak, manual v33 par. 9.2). Gekromde schaalvlakken en schaalranden:
    LIAISON_OBLIQUE per knoopnormaal (_frictionless_per_node). Balken
    worden gemeld en overgeslagen.
    """
    sel = bc["selection"]
    kinds = faces["kinds"] if faces else set()
    if kinds == set(["solid"]):
        return True
    reason = tr("alleen vlakken van volume-elementen, schaalvlakken of "
                "schaalranden",
                "only faces of solid elements, shell faces or shell edges")
    if kinds == set(["shellface"]) and faces["normals"]:
        n0 = faces["normals"][0]
        if all(abs(_vdot(n0, n)) > 1.0 - 1.0e-6 for n in faces["normals"]):
            value = bc["params"].get("value", 0.0)
            if (isinstance(value, list) or value != 0.0):
                log(tr("WARNING: Frictionless op schaalvlakken '{0}' met een "
                       "normaalverplaatsing: de richting (welke kant 'in' "
                       "is) is NIET geverifieerd tegen Mecway.",
                       "WARNING: Frictionless on shell faces '{0}' with a "
                       "normal displacement: the direction (which side is "
                       "'in') is NOT verified against Mecway.").format(sel))
            dx, dy, dz = n0
            handler = SUPPORTED_BCS["frictionless"]
            bc["params"]["_normal"] = n0
            bc["aster_keyword"] = handler.keyword(bc["params"])
            bc["aster_dict"] = handler.to_aster_dict(bc["params"])
            log("INFO: Frictionless op vlakke schaalvlakken '{0}': "
                "LIAISON_OBLIQUE, normaal ({1})."
                .format(sel, ", ".join("%.4g" % v for v in (dx, dy, dz))))
            return False
    if kinds in (set(["shellface"]), set(["shelledge"])):
        reason = _frictionless_per_node(model_data, bc, faces_list or [],
                                        list(kinds)[0])
        if reason is None:
            return False
    bc["skip"] = True
    model_data.setdefault("skipped_loads", []).append(
        tr("frictionless op '{0}'", "frictionless on '{0}'").format(sel))
    log(tr("ERROR: Frictionless op '{0}' ({1}): {2}. NIET meegenomen.",
           "ERROR: Frictionless on '{0}' ({1}): {2}. NOT included.").format(
        sel, ", ".join(sorted(kinds)) or tr("geen vlakken", "no faces"),
        reason))
    return False


def _frictionless_per_node(model_data, bc, faces_list, kind):
    """
    Frictionless op gekromde schaalvlakken of op schaalranden (KNOWN_BUGS 5).
    Mecway (manual v33 par. 9.2): normaalverplaatsing nul, in een knoop
    langs de gemiddelde normaal van de aangrenzende vlakken uit de
    selectie; op schalen ook de rotaties om de assen in het vlak.
    Code-Aster: LIAISON_OBLIQUE per groep knopen met dezelfde normaal
    (bc["oblique"], zoals symmetry; U4.44.01 LIAISON_OBLIQUE, ANGL_NAUT
    met lokaal x = de normaal):
      - schaalvlakken: DX = DRY = DRZ = 0 (zoals de vlakke schaalvlakken);
      - schaalranden: normaal in het schaalvlak (loodrecht op de rand), lokaal
        y = de rand: DX = DRY = 0. Alleen de rotatie om de rand, zoals Mecway
        bij symmetry op schaalranden (manual par. 9.40); of Mecway's
        frictionless op een schaalrand ook de rotatie om de schaalnormaal
        vastlegt, is NIET geverifieerd.
    Alleen normaalverplaatsing 0 (bc["oblique"] schrijft 0.0). Na LINE_QUAD
    (COQUE_3D) krijgen de nieuwe middenknopen geen voorwaarde (een groep per
    normaal; bridge_to_aster vult alleen groepen aan waar beide eindknopen
    in zitten). Returns None als vertaald, anders de reden.
    """
    value = bc["params"].get("value", 0.0)
    if isinstance(value, list) and all(v == 0.0 for _t, v in value):
        value = 0.0
    if isinstance(value, list) or value != 0.0:
        return tr("normaalverplaatsing ongelijk aan 0 op gekromde "
                  "schaalvlakken of schaalranden wordt niet vertaald",
                  "a non-zero normal displacement on curved shell faces "
                  "or shell edges is not translated")
    nodes = model_data["mesh_nodes"]
    conn = model_data["_conn"]
    groups = OrderedDict()           # sleutel -> [angl, ddls, [nid]]
    if kind == "shellface":
        sums = OrderedDict()
        for f in faces_list:
            nrm = _face_normal(f, nodes, conn)
            w = _lumped_weights(f["stype"], [nodes[n] for n in f["nodes"]])
            for n, wi in zip(f["nodes"], w):
                old = sums.get(n, (0.0, 0.0, 0.0))
                sums[n] = tuple(old[k] + wi * nrm[k] for k in range(3))
        for n, v in sums.items():
            if _vdot(v, v) <= 1.0e-24:
                return tr("knoop N{0} heeft geen eenduidige normaal (vlakken "
                          "aan beide kanten?)",
                          "node N{0} has no unique normal (faces on both "
                          "sides?)").format(n)
            x = _vunit(v)
            groups.setdefault(_round_key(x, 1.0e-3),
                              [_angl_naut(x), ("DX", "DRY", "DRZ"), []]
                              )[2].append(n)
    else:
        frames, why = _edge_frames(model_data, faces_list)
        if why:
            return why
        for n, a in frames.items():
            v, ns = a[1], a[4]
            if _vdot(v, v) <= 1.0e-24:
                return tr("knoop N{0} heeft geen eenduidige normaal",
                          "node N{0} has no unique normal").format(n)
            x = _vunit(v)
            y = _vcross(ns, x)
            if _vdot(y, y) <= 1.0e-24:
                return tr("knoop N{0}: normaal langs de schaalnormaal",
                          "node N{0}: normal along the shell normal").format(n)
            y = _vunit(y)
            groups.setdefault(_round_key(x + y, 1.0e-3),
                              [_angl_naut3(x, y), ("DX", "DRY"), []]
                              )[2].append(n)
    bc["oblique"] = [(_extra_node_group(model_data, "BRFR", nids), angl,
                      ddls) for angl, ddls, nids in groups.values()]
    bc["aster_dict"] = {}
    log("INFO: Frictionless op {0} '{1}': {2} knopen, {3} normaal/normalen, "
        "LIAISON_OBLIQUE per groep.".format(
            "gekromde schaalvlakken" if kind == "shellface" else
            "schaalranden", bc["selection"],
            sum(len(g[2]) for g in groups.values()), len(groups)))
    return None


# ==========================================
# KOPPELINGEN (RBE2/RBE3): NAMEN EN SLAVE-KNOOPGROEPEN
# ==========================================
def _couplings_to_mesh(model_data, rn, nonempty_names, node_face_groups,
                       known):
    """
    Groepsnamen van de koppelingen naar Code-Aster; een slave-vlakgroep
    krijgt een knoopgroep '<vlakgroep>_N' (DEFI_GROUP in bridge_to_aster).
    Een koppeling met een lege of ontbrekende master- of slave-selectie
    wordt overgeslagen en gemeld, zoals een BC (anders stopt Code-Aster op
    de onbekende groep, MODELISA7_77).
    """
    node_group_names = set(model_data.get("node_groups", {}).keys())
    kept = []
    for c in model_data.get("couplings", []):
        master_mw, slave_mw = c["master_group"], c["slave_group"]
        c["master_group"] = rn(master_mw)
        face_group = rn(slave_mw)
        if c.get("slave_kind") == "GROUP_MA" and \
                face_group in node_face_groups:
            # Vlakken van balkuiteinden: alleen knopen in het mesh.
            c["slave_kind"] = "GROUP_NO"
        if c.get("slave_kind") == "GROUP_MA":
            slave_ok = face_group in nonempty_names
        else:
            slave_ok = face_group in known
        missing = [n for n, ok in ((master_mw, c["master_group"] in known),
                                   (slave_mw, slave_ok)) if not ok]
        if missing:
            model_data.setdefault("skipped_loads", []).append(
                tr("koppeling {0} '{1}' / '{2}' (lege of ontbrekende "
                   "selectie)",
                   "coupling {0} '{1}' / '{2}' (empty or missing "
                   "selection)").format(c["type"], master_mw, slave_mw))
            log(tr("ERROR: Koppeling {0} '{1}' / '{2}' verwijst naar "
                   "selectie(s) {3}, die leeg zijn of niet bestaan. NIET "
                   "meegenomen.",
                   "ERROR: Coupling {0} '{1}' / '{2}' refers to "
                   "selection(s) {3}, which are empty or do not exist. NOT "
                   "included.").format(
                c["type"], master_mw, slave_mw,
                ", ".join("'{0}'".format(n) for n in missing)))
            continue
        kept.append(c)
        if c.get("slave_kind") != "GROUP_MA":
            c["slave_group"] = face_group
            continue
        # Max. 24 tekens (Code-Aster-groepsnaam): inkorten voor "_N".
        no_name, k = face_group, 0
        while (no_name in node_group_names or no_name in nonempty_names
               or no_name in known):
            k += 1
            suffix = "_N" if k == 1 else "_N{0}".format(k)
            no_name = face_group[:ASTER_NAME_MAX - len(suffix)] + suffix
        node_group_names.add(no_name)
        c["slave_group_ma"] = face_group
        c["slave_group"] = no_name
        log("INFO: Koppeling: slave-knopen '{0}' worden afgeleid van "
            "vlakgroep '{1}'.".format(no_name, face_group))
    model_data["couplings"] = kept


# ==========================================
# model_data AFSTEMMEN OP HET MESH
# ==========================================
# Dicts met een elset als sleutel (hernoemen, lege elsets weglaten).
_ELSET_KEYS = ("elsets", "elset_dims", "elset_modelisations", "beam_sections",
               "shell_sections", "spring_sections", "shell_upgrades",
               "cable_sections", "discrete_sections")


def _apply_to_model_data(model_data, rn, rn_es, nonempty_names, poi1_groups,
                         group_areas, group_weights, group_integrals,
                         group_faces):
    """rn: Code-Aster-naam van een selectie, rn_es: van een elset."""
    # --- Elset-gebonden dicts hernoemen ---
    for key in _ELSET_KEYS:
        old = model_data.get(key, {})
        model_data[key] = OrderedDict((rn_es(k), v) for k, v in old.items())
    for key in ("node_groups", "face_selections", "element_selections"):
        old = model_data.get(key, {})
        model_data[key] = OrderedDict((rn(k), v) for k, v in old.items())

    # --- Elsets zonder elementen weglaten ---
    for elset in list(model_data["elset_modelisations"].keys()):
        if elset not in nonempty_names:
            log(tr("WARNING: Elset '{0}' heeft geen elementen en wordt "
                   "weggelaten uit AFFE_MODELE/AFFE_MATERIAU.",
                   "WARNING: Elset '{0}' has no elements and is "
                   "omitted from AFFE_MODELE/AFFE_MATERIAU.").format(elset))
            for key in _ELSET_KEYS:
                model_data[key].pop(elset, None)

    # --- BC's: namen en randelementen ---
    skin_groups = []
    face_list = model_data.get("group_face_list", {})
    face_sel = model_data.get("face_selections", {})
    shapes = model_data.get("elem_shapes", {})
    node_face_groups = model_data.get("face_node_groups", set())
    known = model_data.get("mesh_group_names", nonempty_names)
    for bc in model_data["bcs"]:
        if not bc["selection"]:
            continue
        bc["selection"] = rn(bc["selection"])
        sel = bc["selection"]
        if sel not in known:
            # Lege of ontbrekende selectie: overslaan (anders stopt Code-
            # Aster met <EXCEPTION> MODELISA7_77 op de onbekende groep).
            bc["skip"] = True
            model_data.setdefault("skipped_loads", []).append(
                tr("{0} op '{1}' (lege of ontbrekende selectie)",
                   "{0} on '{1}' (empty or missing selection)").format(
                    bc["type"], sel))
            log(tr("ERROR: {0} verwijst naar selectie '{1}', die leeg is of "
                   "niet bestaat. NIET meegenomen.",
                   "ERROR: {0} refers to selection '{1}', which is empty or "
                   "does not exist. NOT included.").format(bc["type"], sel))
            continue
        if bc["aster_target"] == "GROUP_MA" and sel in node_face_groups:
            # Vlakken van balken: alleen knopen.
            bc["aster_target"] = "GROUP_NO"
            if bc["type"] == "force":
                # Totale kracht, net als op een nodeselection gelijk
                # verdeeld over de knopen (bridge_from_liml, STAP 2);
                # FORCE_NODALE legt de waarde per knoop op.
                n = len(group_weights.get(sel, ()))
                if n > 1:
                    bc["params"] = _per_area(bc["params"], float(n))
                    bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                        bc["params"])
                log("INFO: Kracht op balkuiteinden '{0}': verdeeld over {1} "
                    "knopen (FORCE_NODALE).".format(sel, n))
        if bc["type"] == "pinnedsupport":
            _pinned_to_mean(model_data, bc, group_weights)
            continue
        if bc["type"] == "moment":
            _moment_to_forces(model_data, bc, group_integrals, group_weights)
            continue
        if bc["type"] == "frictionless":
            if _frictionless(model_data, bc, group_faces.get(sel),
                             face_list.get(sel, [])):
                if sel not in skin_groups:
                    skin_groups.append(sel)
            continue
        if bc["type"] == "traction":
            _traction(model_data, bc, group_faces.get(sel), skin_groups)
            continue
        if bc["type"] == "linepressure":
            _line_pressure(model_data, bc, group_faces.get(sel))
            continue
        if bc["type"] == "hydrostaticpressure":
            _hydrostatic(model_data, bc, group_faces.get(sel), skin_groups)
            continue
        if bc["type"] == "compressiononly":
            _compression_only(model_data, bc, face_list.get(sel, []))
            continue
        if bc["type"] == "symmetry":
            _symmetry(model_data, bc, face_list.get(sel, []))
            continue
        if bc["type"] == "surfacepressure" and (
                group_faces.get(sel, {}).get("kinds") or set(["?"])) <= set(
                    ["shelledge", "beam"]):
            # Schaalranden en balkuiteinden (vóór de GROUP_NO-sprong
            # hieronder: balkvlakken staan alleen als knopen in het mesh)
            _edge_loads(model_data, bc, tr("Druk", "Pressure"))
            continue
        if bc["aster_target"] != "GROUP_MA":
            continue
        # Kracht op vlakken: totale kracht / oppervlak -> FORCE_FACE op
        # randelementen van volume-elementen (FORCE_FACE, U4.44.01).
        if bc["type"] == "force":
            parent = set(shapes.get(eid, "?") for eid in face_sel.get(sel, []))
            area = group_areas.get(sel, 0.0)
            if (sel in face_sel and parent and parent <= _SOLID_SHAPES
                    and area > 0.0):
                bc["params"] = _per_area(bc["params"], area)
                bc["aster_keyword"] = "FORCE_FACE"
                bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                    bc["params"])
                if sel not in skin_groups:
                    skin_groups.append(sel)
                log("INFO: Kracht op vlakken '{0}': oppervlak {1} m2 -> "
                    "FORCE_FACE.".format(sel, area))
            elif (group_faces.get(sel, {}).get("kinds") == set(["shellface"])
                    and sel in group_integrals):
                # Schaalvlakken: kracht per oppervlak op het middenvlak
                # (FORCE_COQUE FX/FY/FZ, globaal assenstelsel, U4.44.01).
                area = sum(group_integrals[sel][0].values())
                bc["params"] = _per_area(bc["params"], area)
                bc["aster_keyword"] = "FORCE_COQUE"
                bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                    bc["params"])
                log("INFO: Kracht op schaalvlakken '{0}': oppervlak {1} m2 "
                    "-> FORCE_COQUE.".format(sel, area))
            elif (group_faces.get(sel, {}).get("kinds") == set(["shelledge"])
                    and _shell_edge_parent(model_data, sel)):
                # Schaalranden: totale kracht / randlengte -> FORCE_ARETE
                # (kracht per lengte, globaal; U4.44.01 "line forces to an
                # edge of a volume element or shell"). De randen komen met
                # de modelisatie van de schaal in het model (edge_groups).
                length = _edge_length(model_data, sel)
                if length > 0.0:
                    model_data.setdefault("edge_groups", OrderedDict())[sel] = \
                        _shell_edge_parent(model_data, sel)
                    bc["params"] = _per_area(bc["params"], length)
                    bc["aster_keyword"] = "FORCE_ARETE"
                    bc["aster_dict"] = SUPPORTED_BCS["force"].to_aster_dict(
                        bc["params"])
                    log("INFO: Kracht op schaalranden '{0}': lengte {1} m "
                        "-> FORCE_ARETE.".format(sel, length))
                else:
                    _not_translated(model_data, bc, tr("Kracht", "Force"),
                                    tr("schaalranden zonder lengte",
                                       "shell edges without length"))
            else:
                bc["skip"] = True
                model_data.setdefault("skipped_loads", []).append(
                    tr("kracht op '{0}' (vlakken van {1})",
                       "force on '{0}' (faces of {1})").format(
                        sel, ", ".join(sorted(parent)) or "?"))
                log(tr("ERROR: Kracht op '{0}': alleen vlakken van volume- "
                       "of schaalelementen worden ondersteund (hier: {1}). "
                       "Belasting NIET meegenomen.",
                       "ERROR: Force on '{0}': only faces of solid "
                       "or shell elements are supported (here: {1}). "
                       "Load NOT included.").format(sel, sorted(parent)))
            continue
        # Druk op vlakken van volume-elementen: de vlakken moeten in
        # AFFE_MODELE (MODELISATION='3D' -> randelementen).
        if bc["type"] == "surfacepressure" and sel in face_sel:
            parent = set(shapes.get(eid, "?") for eid in face_sel[sel])
            faces = group_faces.get(sel, {})
            if parent and parent <= _SOLID_SHAPES:
                if sel not in skin_groups:
                    skin_groups.append(sel)
            elif faces.get("kinds") == set(["shellface"]) and \
                    len(faces.get("sides", ())) == 1:
                # Schaalvlakken: PRES_REP op de schaalelementen werkt tegen
                # de elementnormaal in; Mecway-druk werkt het vlak in, dus
                # tegen de vlaknormaal in (faceid 5 = elementnormaal,
                # 6 = omgekeerd): teken = side.
                side = list(faces["sides"])[0]
                if side < 0:
                    bc["params"]["_sign"] = -1.0
                    bc["aster_dict"] = SUPPORTED_BCS[
                        "surfacepressure"].to_aster_dict(bc["params"])
                log("INFO: Druk op schaalvlakken '{0}' (teken {1:+d})."
                    .format(sel, side))
            else:
                bc["skip"] = True
                model_data.setdefault("skipped_loads", []).append(
                    tr("druk op '{0}' (vlakken van {1})",
                       "pressure on '{0}' (faces of {1})").format(
                        sel, ", ".join(sorted(parent)) or "?"))
                log(tr("ERROR: Druk op '{0}': alleen vlakken van "
                       "volume-elementen, schaalvlakken aan een kant (alle "
                       "faceid 5 of alle 6), schaalranden of balkuiteinden "
                       "(elk apart); hier {1}. NIET meegenomen.",
                       "ERROR: Pressure on '{0}': only faces of "
                       "solid elements, shell faces on one side (all "
                       "faceid 5 or all 6), shell edges or beam ends "
                       "(separately); here {1}. NOT included.").format(
                        sel, ", ".join(sorted(faces.get("kinds", ())))
                        or sorted(parent)))
        elif bc["type"] == "surfacepressure":
            # Elementselectie: PRES_REP werkt alleen op schaalelementen
            # (en randelementen); op volume-elementen negeert Code-Aster
            # hem met alarm CHARGES2_89 (gemeld in een review; de run zelf
            # NIET nagelopen).
            mods = _element_kinds(model_data, sel)
            if mods is not None and not mods <= set(["DKT", "DST",
                                                     "COQUE_3D"]):
                _not_translated(model_data, bc, tr("Druk", "Pressure"),
                                tr("op een elementselectie alleen "
                                   "schaalelementen (hier {0}); kies voor "
                                   "volume-elementen een vlakselectie",
                                   "on an element selection only shell "
                                   "elements (here {0}); for solid "
                                   "elements use a face selection").format(
                                    ", ".join(sorted(mods))))
    # --- Contact (contact2 -> DEFI_CONTACT) ---
    # De vlakken moeten in het model (randelementen, ORIE_PEAU voor een
    # naar buiten gerichte normaal; DEFI_CONTACT U4.44.11). Schaalvlakken
    # zijn de schaalelementen zelf.
    pairs = []
    for c in model_data.get("contacts", []):
        master, slave = rn(c["master"]), rn(c["slave"])
        label = "contact '{0}' / '{1}'".format(c["master"], c["slave"])
        if c.get("selfcontact") or not slave or master == slave:
            model_data.setdefault("skipped_loads", []).append(
                "self-{0}".format(label))
            log(tr("ERROR: Self-contact op '{0}' wordt niet vertaald (Code-"
                   "Aster CONTINUE/DISCRETE vraagt twee verschillende "
                   "vlakgroepen).",
                   "ERROR: Self-contact on '{0}' is not translated (Code-"
                   "Aster CONTINUE/DISCRETE requires two different "
                   "face groups).").format(c["master"]))
            continue
        kinds = set()
        for g in (master, slave):
            kinds |= group_faces.get(g, {}).get("kinds", set(["?"]))
        if not kinds <= set(["solid", "shellface"]):
            model_data.setdefault("skipped_loads", []).append(label)
            log(tr("ERROR: {0}: alleen vlakken van volume-elementen en "
                   "schaalvlakken (hier {1}). NIET meegenomen.",
                   "ERROR: {0}: only faces of solid elements and "
                   "shell faces (here {1}). NOT included.").format(
                    label, sorted(kinds)))
            continue
        for g in (master, slave):
            solid = "solid" in group_faces.get(g, {}).get("kinds", ())
            if solid and g not in skin_groups:
                skin_groups.append(g)
        _check_contact_sides(label, master, slave, group_integrals)
        pairs.append(dict(c, master=master, slave=slave))
    model_data["contacts"] = _merge_contact_zones(
        pairs, group_integrals, model_data["group_ma_unions"])
    # --- Couplings (vóór de overlapcontrole: die kijkt met de Code-Aster-
    # namen) ---
    _couplings_to_mesh(model_data, rn, nonempty_names, node_face_groups,
                       known)
    _exclude_fixed_slaves(model_data, group_integrals)
    _report_constraint_overlaps(model_data, group_integrals, group_faces)
    bonded = []
    for c in model_data.get("bonded", []):
        b = _bonded(model_data, c, group_faces, rn)
        if b is not None:
            bonded.append(b)
    model_data["bonded"] = bonded
    model_data["temperatures"] = [
        dict(t, selection=rn(t["selection"]))
        for t in model_data.get("temperatures", [])]

    # Volumevlakken die #ASTER-code noemt (<<naam>>): randelementen in het
    # model, anders kan bijv. LIAISON_ELEM ze niet gebruiken (MODELISA4_50/
    # 4_51, Code-Aster 17.4).
    custom = model_data.get("aster_custom", {})
    text = " ".join(custom.get("code", []) + custom.get("post", []) +
                    custom.get("zone", []) + custom.get("contact", []))
    for name in re.findall(r"<<([^<>]+)>>", text):
        # zoals bridge_custom.substitute (group_renames: elset wint)
        g = rn_es(name.strip())
        solid = "solid" in group_faces.get(g, {}).get("kinds", ())
        if solid and g not in skin_groups:
            skin_groups.append(g)
    model_data["skin_groups"] = skin_groups
    model_data["initial_velocities"] = [
        (rn(sel), target, v)
        for sel, target, v in model_data.get("initial_velocities", [])]
    model_data["bcs"] = [bc for bc in model_data["bcs"]
                         if not bc.get("skip")]

    # --- POI1-groepen en rotatie-DOFs ---
    model_data["poi1_groups"] = poi1_groups
    dis_tr = ("DIS_TR" in poi1_groups.values() or any(
        d["mod"] == "DIS_TR" for d in model_data.get("discretes", {}).values()))
    if dis_tr and not model_data["has_rot_dofs"]:
        model_data["has_rot_dofs"] = True
        for bc in model_data["bcs"]:
            bc["params"]["_has_rot_dofs"] = True
            # Alleen fixed hangt van de vlag af; de aster_dict van andere
            # BC's is hierboven al aangepast (traction PLAN, druk-teken).
            if bc["type"] == "fixed":
                bc["aster_dict"] = SUPPORTED_BCS[bc["type"]].to_aster_dict(
                    bc["params"])
        log("INFO: has_rot_dofs = True door DIS_TR-knopen; BC's herberekend.")
