# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_welding.py
# Verantwoordelijkheid: bewegende lasbron (stap S4a) in een transiente
# thermische analyse (Mecway T31 -> ther_3d, bridge_thermal.py).
#
# Invoer: een regel '#ASTER-LASBRON' (ook '#ASTER-WELD') in een vrij
# tekstveld van Mecway (bridge_custom.py), bijv.
#   #ASTER-LASBRON Q=2000, eta=0.8, v=0.005, start=(0.01, 0, 0.02),
#   #ASTER-LASBRON     richting=(1, 0, 0), af=0.002, ar=0.004, b=0.002, c=0.002
# (opeenvolgende LASBRON-regels vormen een bron; een regel die met 'Q=' of
# 'nieuw' begint, start een nieuwe bron). Waarden in SI (zoals alle
# #ASTER-regels). Zie docs/Lassen.md voor alle sleutels.
#
#   parse_specs(bodies, ...)  - sleutels lezen en controleren
#   apply(tb, model_data, an) - FORMULE + AFFE_CHAR_THER_F per bron in de
#                               .comm van bridge_thermal.build_thermal (meer
#                               bronnen, ook Mecway-functiebronnen: een
#                               last, _merged_load)
#   report_lines(mess_path)   - energiecontrole uit de .mess (statusvak),
#                               plus de samenvatting van de keten
#                               thermisch -> mechanisch (bridge_thermomech)
#
# Toevoegmateriaal dat geboren wordt (stap S4c, sleutel geboorte=):
#   _births            - geboortetijd per element (BORN_FUNC), groepen per
#                        geboortestap; tb.birth / model_data["welding_birth"]
#   birth_materials    - thermisch stil materiaal (THER_FO van INST en
#                        NEUT1, of een stil THER_NL-materiaal + ther_loop)
#   bridge_thermomech._birth_solve - mechanisch (STAT_NON_LINE per
#                        geboortestap, spanningsvrij bij de geboorte)
#
# Bronvorm: Goldak dubbel-ellipsoide (Goldak, Chakravarti & Bibby, 1984):
#   q(xi, eta, zeta) = 6 sqrt(3) f Q_eff / (a b c pi sqrt(pi))
#                      * exp(-3 xi^2/a^2 - 3 eta^2/b^2 - 3 zeta^2/c^2)
# met xi langs de lasrichting (voor de bron: a = af, f = ff; erachter
# a = ar, f = fr), eta dwars, zeta de diepte (in het materiaal), Q_eff =
# eta * Q. Over de halve ruimte (zeta >= 0) is de integraal (ff + fr)/2 *
# Q_eff = Q_eff bij ff + fr = 2. Standaard ff = 2 af/(af + ar), fr = 2 ar/
# (af + ar): q is dan continu in xi = 0. Met r = .. zijn af = ar = b = c =
# r (halve Gauss-bol, ff = fr = 1).
#
# Code-Aster 17.4: AFFE_CHAR_THER_F SOURCE SOUR = FORMULE van X, Y, Z,
# INST (catalogus affe_char_ther_f.py; FORMULE rekent de uitdrukking in
# Python met de opgegeven argumenten, catalogus formule.py). De bron werkt
# alleen op de elementen van de brongroep (sneller dan het hele model; de
# Python-functie wordt per Gauss-punt en per stap aangeroepen).
# Energiecontrole in de job: CALC_VECT_ELEM CHAR_THER + ASSE_VECTEUR geeft
# de knooplasten zoals THER_LINEAIRE ze integreert; hun som is het
# vermogen dat het mesh echt opneemt (som van de vormfuncties = 1).
#
# Compatibel met IronPython 2.7.9 (alleen standaardbibliotheek).

import math
import re
from collections import OrderedDict

from bridge_utils import log, tr

# Voorvoegsel van Mecway-selecties/-componenten met de elementen van de
# lasrups (STAPPENPLAN B.2): standaard-brongroep als 'groep' ontbreekt.
GROUP_PREFIX = "LASNAAD_"

# Brongroep automatisch: elementen binnen CUTOFF x de grootste halve as van
# de baan (q < exp(-3 * CUTOFF^2) = 2e-12 van de piek daarbuiten).
CUTOFF = 3.0

# Tijdstap: de bron verspringt per stap v*dt; WARNING boven
# MAX_JUMP x de bronlengte (af + ar). Gemeten (Code-Aster 17.4, WE-01/
# WE-01b, Gauss-bron r = 0,75 mm, h = 0,5 mm, theta 0,57; 07-10-2026):
# afwijking van de TEMPERATUUR naast de bron (3 mm) / op de lasas 6 mm
# erachter t.o.v. dezelfde bron analytisch (tests_lassen.goldak_exact):
# v*dt = (af + ar)/6 -1,4% / -0,25%; (af + ar)/2 (deze grens) -2,2% /
# -2,9%; 1 x (af + ar) -4,9% / -26% (de bron slaat knopen over; meting
# S4a). T.o.v. de run met (af + ar)/6 is de grens -0,8% / -2,7%
# (docs/Lassen.md par. 4.1). Geen energieverlies: de energie op t = 6 s
# is bij beide stappen +0,06% (WE-01, WE-01b).
MAX_JUMP = 0.5

# Mesh: WARNING als de elementen langs de baan in een richting groter zijn
# dan MAX_H x de halve as in die richting. Integratiefout van de bron met
# 2 Gauss-punten per element (HEXA8) per richting, slechtste ligging,
# berekend: 0,03% bij h = 0,67 a, 0,28% bij 0,8 a, 1,8% bij 1,0 a, 7,6%
# bij 1,33 a (docs/Lassen.md par. 4). De energiecontrole in de job meet
# het werkelijke effect.
MAX_H = 0.8

# Energiecontrole: WARNING als het opgenomen vermogen meer dan dit
# (fractie) van Q_eff afwijkt.
POWER_TOL = 0.02

_KEYS = {
    # sleutel -> (soort, synoniemen)
    "q": ("num", ("q", "vermogen", "power")),
    "eta": ("num", ("eta", "rendement", "efficiency")),
    "v": ("num", ("v", "snelheid", "speed")),
    "start": ("vec", ("start", "begin")),
    "dir": ("vec", ("richting", "dir", "direction")),
    "length": ("num", ("lengte", "length")),
    "path": ("sel", ("pad", "path", "baan")),
    "depth": ("vec", ("diepte", "depth")),
    "af": ("num", ("af",)),
    "ar": ("num", ("ar",)),
    "b": ("num", ("b",)),
    "c": ("num", ("c",)),
    "r": ("num", ("r",)),
    "ff": ("num", ("ff",)),
    "fr": ("num", ("fr",)),
    "t0": ("num", ("t0", "tstart")),
    "t1": ("num", ("t1", "teind", "tend")),
    "group": ("sel", ("groep", "group")),
    "sym": ("num", ("symmetrie", "symmetry")),
    # Toevoegmateriaal (S4c): ja / nee / <<elementselectie of component>>
    "birth": ("birth", ("geboorte", "birth")),
    "lead": ("num", ("voorloop", "lead")),
}
_ALIAS = dict((a, k) for k, (_s, names) in _KEYS.items() for a in names)
_SEL_RE = re.compile(r"^<<([^<>]+)>>$")
_YES = ("ja", "yes", "j", "y", "1", "aan", "on", "true", "waar")
_NO = ("nee", "no", "n", "0", "uit", "off", "false", "onwaar")

# Toevoegmateriaal (geboorte, stap S4c): "quiet element"-methode. Een nog
# niet geboren element krijgt rho*cp x QUIET en lambda x QUIET^2 (thermisch:
# nagenoeg geen warmteopslag, en de temperatuurvereffening a = lambda /
# (rho cp) x QUIET, zodat er voor de geboorte ook geen warmte het
# ongeboren materiaal in kruipt) en mechanisch E x QUIET (bridge_thermomech).
# Gemeten (Code-Aster 17.4, prototype: rups van 2 elementen dik op een
# plaat, de bron alleen in de plaat, de rups in een keer geboren na 2 s):
# met lambda en rho*cp allebei x 1e-3 bracht de geboorte 21% van de
# ingebrachte energie extra in (de rups was door geleiding al opgewarmd),
# met lambda x 1e-6 nog 3,3% (alleen de knopen op het grensvlak met de plaat
# zijn warm); WE-11 met de standaard: +1,2..1,6%. Thermisch rekent het
# toevoegmateriaal met een diagonale warmtecapaciteit (bridge_thermal
# model_block, 3D_DIAG). Zie docs/Lassen.md par. 10.
QUIET = 1.0e-4

# Voorloop van de geboorte (standaard, x af): een element wordt geboren
# als de bron (het midden) op voorloop van zijn achterste knoop (langs de
# baan) is; de bron werkt alleen in een punt van het toevoegmateriaal dat
# al geboren is (s(t) > s_punt - voorloop). Voor de bron ligt deel
# erfc(sqrt(3) voorloop / af) van het voorste deel van de bron verder dan
# voorloop: 1,4% bij 1 x af, 2,4e-4 bij 1,5 x af, 4e-7 bij 2 x af.
LEAD_AF = 2.0


# ==========================================
# LEZEN
# ==========================================
def _split(body):
    """Stukken 'sleutel = waarde' gescheiden door komma's buiten haakjes."""
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _number(text):
    return float(text.strip().replace(" ", ""))


def group_lines(bodies):
    """Regels (#ASTER-LASBRON) samenvoegen tot bronnen: een regel die met
    'Q=' (of 'vermogen=', 'power=') of het woord 'nieuw'/'new' begint,
    start een nieuwe bron; de andere regels horen bij de vorige."""
    sources = []
    for body in bodies:
        text = body.strip()
        low = text.lower()
        new = False
        if low.split(" ")[0] in ("nieuw", "new"):
            new = True
            text = text.split(" ", 1)[1] if " " in text else ""
        else:
            key = low.split("=", 1)[0].strip()
            new = _ALIAS.get(key) == "q"
        if new or not sources:
            sources.append([])
        if text:
            sources[-1].append(text)
    return [", ".join(s) for s in sources]


def parse_specs(bodies):
    """
    [spec] uit de #ASTER-LASBRON-regels; spec = dict met de sleutels van
    _KEYS (getallen, vectoren als tuple, selecties als Mecway-naam). None
    (met ERROR in de log) bij een fout.
    """
    specs = []
    for k, text in enumerate(group_lines(bodies)):
        spec = {"index": k + 1, "text": text}
        for part in _split(text):
            key, sep, raw = part.partition("=")
            key = key.strip().lower()
            raw = raw.strip()
            name = _ALIAS.get(key)
            if not sep or name is None:
                log(tr("ERROR: #ASTER-LASBRON: onbekend of onvolledig "
                       "'{0}'. Bekend: {1}.",
                       "ERROR: #ASTER-LASBRON: unknown or incomplete "
                       "'{0}'. Known: {1}.").format(
                           part, ", ".join(sorted(_ALIAS))))
                return None
            kind = _KEYS[name][0]
            try:
                if kind == "num":
                    spec[name] = _number(raw)
                elif kind == "vec":
                    inner = raw.strip()
                    if not (inner.startswith("(") and inner.endswith(")")):
                        raise ValueError(raw)
                    vals = [_number(x) for x in inner[1:-1].split(",")]
                    if len(vals) != 3:
                        raise ValueError(raw)
                    spec[name] = tuple(vals)
                elif kind == "birth":
                    low = raw.strip("'\"").lower()
                    m = _SEL_RE.match(raw)
                    if m:
                        spec[name] = m.group(1).strip()
                    elif low in _YES:
                        spec[name] = True
                    elif low in _NO:
                        spec[name] = False
                    else:
                        raise ValueError(raw)
                else:
                    m = _SEL_RE.match(raw)
                    if not m:
                        raise ValueError(raw)
                    spec[name] = m.group(1).strip()
            except ValueError:
                log(tr("ERROR: #ASTER-LASBRON: '{0}' heeft geen geldige "
                       "waarde ({1}).",
                       "ERROR: #ASTER-LASBRON: '{0}' has no valid value "
                       "({1}).").format(key, {
                           "num": tr("getal in SI", "number in SI"),
                           "vec": "(x, y, z)",
                           "sel": "<<Mecway-selectie>>",
                           "birth": tr("ja, nee of <<Mecway-selectie>>",
                                       "yes, no or <<Mecway selection>>")
                       }[kind]))
                return None
        if not _complete(spec):
            return None
        specs.append(spec)
    return specs


def _complete(spec):
    """Standaardwaarden en controles van een bron; False (ERROR) bij een
    fout."""
    k = spec["index"]

    def err(nl, en):
        log(tr("ERROR: #ASTER-LASBRON (bron {0}): " + nl,
               "ERROR: #ASTER-LASBRON (source {0}): " + en).format(k))
        return False
    if "r" in spec:
        for key in ("af", "ar", "b", "c"):
            spec.setdefault(key, spec["r"])
    missing = [key for key in ("q", "v", "af", "ar", "b", "c")
               if key not in spec]
    if missing:
        return err("ontbreekt: {0} (Q, v en af, ar, b, c of r zijn "
                   "verplicht).".format(", ".join(missing)),
                   "missing: {0} (Q, v and af, ar, b, c or r are "
                   "required).".format(", ".join(missing)))
    if "path" not in spec and not ("start" in spec and "dir" in spec):
        return err("geef de baan: start=(x, y, z) en richting=(dx, dy, dz), "
                   "of pad=<<knoopselectie>>.",
                   "give the path: start=(x, y, z) and direction=(dx, dy, "
                   "dz), or path=<<node selection>>.")
    for key in ("q", "v", "af", "ar", "b", "c"):
        if spec[key] <= 0.0:
            return err("{0} moet > 0 zijn.".format(key),
                       "{0} must be > 0.".format(key))
    spec.setdefault("eta", 1.0)
    if not 0.0 < spec["eta"] <= 1.0:
        return err("eta (rendement) moet tussen 0 en 1 liggen.",
                   "eta (efficiency) must be between 0 and 1.")
    spec.setdefault("depth", (0.0, 0.0, -1.0))
    spec.setdefault("t0", 0.0)
    spec.setdefault("birth", False)
    if "lead" in spec and not spec["birth"]:
        log(tr("WARNING: #ASTER-LASBRON (bron {0}): voorloop zonder "
               "geboorte=...; genegeerd.",
               "WARNING: #ASTER-LASBRON (source {0}): lead without "
               "birth=...; ignored.").format(k))
    spec.setdefault("lead", LEAD_AF * spec["af"])
    if spec["lead"] < 0.0:
        return err("voorloop moet >= 0 zijn.", "lead must be >= 0.")
    s = spec["af"] + spec["ar"]
    spec.setdefault("ff", 2.0 * spec["af"] / s)
    spec.setdefault("fr", 2.0 * spec["ar"] / s)
    if abs(spec["ff"] + spec["fr"] - 2.0) > 1.0e-6:
        log(tr("WARNING: #ASTER-LASBRON (bron {0}): ff + fr = {1} <> 2; "
               "het ingebrachte vermogen is dan (ff + fr)/2 x eta x Q.",
               "WARNING: #ASTER-LASBRON (source {0}): ff + fr = {1} <> 2; "
               "the input power is then (ff + fr)/2 x eta x Q.").format(
                   k, "%.6g" % (spec["ff"] + spec["fr"])))
    return True


# ==========================================
# GEOMETRIE
# ==========================================
def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _unit(a):
    n = math.sqrt(_dot(a, a))
    if n == 0.0:
        raise ValueError("nulvector")
    return [c / n for c in a]


def _chain(points, first):
    """Knopen als keten (dichtstbijzijnde buur) vanaf het punt het dichtst
    bij first (of vanaf een uiteinde: het punt het verst van het eerste)."""
    pts = list(points)
    if first is None:
        far = max(pts, key=lambda p: _dot(_sub(p, pts[0]), _sub(p, pts[0])))
        first = far
    cur = min(pts, key=lambda p: _dot(_sub(p, first), _sub(p, first)))
    out = [cur]
    rest = [p for p in pts if p is not cur]
    while rest:
        nxt = min(rest, key=lambda p: _dot(_sub(p, cur), _sub(p, cur)))
        rest.remove(nxt)
        out.append(nxt)
        cur = nxt
    return out


def _path(spec, model_data, period, label):
    """(punten, cumulatieve lengtes) van de baan in SI; None (ERROR) bij een
    fout. Rechte baan zonder lengte: tot het einde van de analyse."""
    if "path" in spec:
        import bridge_custom
        name = bridge_custom.substitute(
            "<<{0}>>".format(spec["path"]), model_data.get("group_renames", {}),
            model_data.get("mesh_group_names", set()))
        ids = model_data.get("node_groups", {}).get(name)
        if not ids:
            log(tr("ERROR: {0}: pad '{1}' is geen knoopselectie met knopen.",
                   "ERROR: {0}: path '{1}' is not a node selection with "
                   "nodes.").format(label, spec["path"]))
            return None
        nodes = model_data["mesh_nodes"]
        pts = [tuple(nodes[int(str(i).lstrip("N"))]) for i in ids]
        pts = _chain(pts, spec.get("start"))
        if len(pts) < 2:
            log(tr("ERROR: {0}: pad '{1}' heeft minder dan 2 knopen.",
                   "ERROR: {0}: path '{1}' has fewer than 2 nodes.").format(
                       label, spec["path"]))
            return None
    else:
        try:
            d = _unit(spec["dir"])
        except ValueError:
            log(tr("ERROR: {0}: richting is (0, 0, 0).",
                   "ERROR: {0}: direction is (0, 0, 0).").format(label))
            return None
        if "length" in spec:
            length = spec["length"]
        else:
            t_end = spec.get("t1", period)
            length = max(spec["v"] * (t_end - spec["t0"]), 0.0)
        if length <= 0.0:
            log(tr("ERROR: {0}: baan met lengte 0 (lengte, t0/t1 of de "
                   "tijdsduur).",
                   "ERROR: {0}: path of length 0 (length, t0/t1 or the "
                   "duration).").format(label))
            return None
        p0 = spec["start"]
        pts = [tuple(p0), tuple(p0[i] + length * d[i] for i in range(3))]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.sqrt(_dot(_sub(b, a), _sub(b, a))))
    return pts, cum


def _segment_frames(pts, depth, label):
    """Per segment (e, w, n): lasrichting, dwars, diepte (orthonormaal; n
    = de diepterichting loodrecht op e gemaakt)."""
    frames = []
    for a, b in zip(pts, pts[1:]):
        e = _unit(_sub(b, a))
        n = _sub(depth, [_dot(depth, e) * c for c in e])
        try:
            n = _unit(n)
        except ValueError:
            log(tr("ERROR: {0}: diepterichting evenwijdig aan de lasbaan.",
                   "ERROR: {0}: depth direction parallel to the weld "
                   "path.").format(label))
            return None
        w = _cross(n, e)
        frames.append((e, w, n))
    return frames


def _dist_to_path(p, pts):
    best = None
    for a, b in zip(pts, pts[1:]):
        ab = _sub(b, a)
        ll = _dot(ab, ab)
        s = 0.0 if ll == 0.0 else max(0.0, min(1.0, _dot(_sub(p, a), ab) / ll))
        q = [a[i] + s * ab[i] for i in range(3)]
        d = math.sqrt(_dot(_sub(p, q), _sub(p, q)))
        if best is None or d < best:
            best = d
    return best


# ==========================================
# .COMM
# ==========================================
GOLDAK_FUNC = '''# Bewegende lasbron (bridge_welding.py): Goldak dubbel-ellipsoide langs
# een baan. P = (t0, v, L, punten, cum. lengtes, assenstelsels, qf, qr, af,
# ar, b, c, afkap); q in W/m3.
def _lb_goldak(X, Y, Z, INST, P):
    t0, v, L, pts, cum, frames, qf, qr, af, ar, b, c, cut = P
    s = v * (INST - t0)
    # aan op [t0, t_eind], ook op t_eind zelf (marge voor de afronding:
    # v (t_eind - t0) lag in een test net boven L, S4c)
    if s < 0.0 or s > L * (1.0 + 1.0e-9):
        return 0.0
    k = 0
    while k < len(cum) - 2 and s > cum[k + 1]:
        k += 1
    e, w, n = frames[k]
    p = pts[k]
    d = s - cum[k]
    dx = X - (p[0] + d * e[0])
    dy = Y - (p[1] + d * e[1])
    dz = Z - (p[2] + d * e[2])
    if dx * dx + dy * dy + dz * dz > cut:
        return 0.0
    xi = dx * e[0] + dy * e[1] + dz * e[2]
    et = dx * w[0] + dy * w[1] + dz * w[2]
    ze = dx * n[0] + dy * n[1] + dz * n[2]
    if xi >= 0.0:
        return qf * _lb_exp(-3.0 * ((xi / af) ** 2 + (et / b) ** 2 +
                                    (ze / c) ** 2))
    return qr * _lb_exp(-3.0 * ((xi / ar) ** 2 + (et / b) ** 2 +
                                (ze / c) ** 2))
import math as _lb_math
_lb_exp = _lb_math.exp
'''


def _tup(v):
    from bridge_mesh import _real
    return "(" + ", ".join(_real(float(c)) for c in v) + ")"


class _Source(object):
    def __init__(self, spec, pts, cum, frames):
        self.spec, self.pts, self.cum, self.frames = spec, pts, cum, frames
        self.k = spec["index"]
        self.q_eff = spec["eta"] * spec["q"]
        self.power = self.q_eff * 0.5 * (spec["ff"] + spec["fr"])
        # Symmetrievlakken door de baan: het mesh krijgt 1/2^n van de bron
        self.target = self.power / 2.0 ** int(round(spec.get("sym", 0.0)))
        c0 = 6.0 * math.sqrt(3.0) * self.q_eff / (
            spec["b"] * spec["c"] * math.pi * math.sqrt(math.pi))
        self.qf = c0 * spec["ff"] / spec["af"]
        self.qr = c0 * spec["fr"] / spec["ar"]
        self.amax = max(spec["af"], spec["ar"], spec["b"], spec["c"])
        self.length = cum[-1]
        self.t_end = spec["t0"] + self.length / spec["v"]
        if "t1" in spec:
            self.t_end = min(self.t_end, spec["t1"])
        self.group = None
        self.eids = []
        self.birth = None      # toevoegmateriaal: [eid] (geboorte, S4c)

    def born_line(self):
        """Parameters van _lb_born (BORN_FUNC) voor het toevoegmateriaal
        van deze bron: (t0, v, voorloop, t_eind, punten, cum. lengtes)."""
        from bridge_mesh import _real
        s = self.spec
        return "_GB{0} = ({1}, {2}, {3}, {4},\n    ({5},),\n    {6})".format(
            self.k, _real(s["t0"]), _real(s["v"]), _real(s["lead"]),
            _real(self.t_end), ", ".join(_tup(p) for p in self.pts),
            _tup(self.cum))

    def param_line(self):
        from bridge_mesh import _real
        s = self.spec
        frames = "(" + ", ".join(
            "(" + ", ".join(_tup(v) for v in f) + ")"
            for f in self.frames) + ",)"
        length = min(self.length, s["v"] * (self.t_end - s["t0"]))
        return ("_LB{0} = ({1}, {2}, {3},\n    ({4},),\n    {5},\n    {6},\n"
                "    {7}, {8}, {9}, {10}, {11}, {12}, {13})".format(
                    self.k, _real(s["t0"]), _real(s["v"]), _real(length),
                    ", ".join(_tup(p) for p in self.pts),
                    _tup(self.cum), frames, _real(self.qf), _real(self.qr),
                    _real(s["af"]), _real(s["ar"]), _real(s["b"]),
                    _real(s["c"]), _real((CUTOFF * self.amax) ** 2)))


def _source_group(tb, model_data, src, label):
    """(groep, [eid]) van de elementen waarop de bron werkt: 'groep', anders
    de selecties/componenten met GROUP_PREFIX, anders automatisch (binnen
    CUTOFF x de grootste halve as van de baan). None (ERROR) bij een
    fout."""
    import bridge_custom
    spec = src.spec
    renames = model_data.get("group_renames", {})
    if "group" in spec:
        name = bridge_custom.substitute(
            "<<{0}>>".format(spec["group"]), renames,
            model_data.get("mesh_group_names", set()))
        eids = _group_elements(tb, model_data, name)
        if eids is None:
            log(tr("ERROR: {0}: groep '{1}' is geen element-selectie of "
                   "component.",
                   "ERROR: {0}: group '{1}' is not an element selection or "
                   "component.").format(label, spec["group"]))
            return None
        return _check_group(tb, name, eids, label)
    # Met geboorte is LASNAAD_ het toevoegmateriaal; de bron werkt dan ook
    # in het basismateriaal eronder (automatische groep).
    named = [] if spec.get("birth") else _prefixed_groups(tb, model_data)
    if named:
        eids = []
        for name in named:
            eids += [e for e in (_group_elements(tb, model_data, name) or [])
                     if e not in eids]
        log("INFO: {0}: brongroep uit de selecties/componenten {1} "
            "(voorvoegsel {2}).".format(label, named, GROUP_PREFIX))
        grp = named[0] if len(named) == 1 else None
        return _check_group(tb, grp, eids, label)
    # Automatisch: elementen dicht bij de baan
    lim = CUTOFF * src.amax
    eids = []
    for eid, (_es, cls, _atype, cn) in tb.elem.items():
        if cls != "solid":
            continue
        pts = [tb.nodes[n] for n in cn]
        cen = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
        rad = max(math.sqrt(_dot(_sub(p, cen), _sub(p, cen))) for p in pts)
        if _dist_to_path(cen, src.pts) <= lim + rad:
            eids.append(eid)
    if not eids:
        log(tr("ERROR: {0}: geen volume-elementen binnen {1} m van de "
               "lasbaan; ligt de baan in het model (eenheden in m)?",
               "ERROR: {0}: no solid elements within {1} m of the weld "
               "path; is the path inside the model (units in m)?").format(
                   label, "%.4g" % lim))
        return None
    log("INFO: {0}: brongroep automatisch, {1} elementen binnen {2} m van "
        "de baan.".format(label, len(eids), "%.4g" % lim))
    return _check_group(tb, None, eids, label)


def _prefixed_groups(tb, model_data):
    """Code-Aster-namen van de selecties/componenten met GROUP_PREFIX (op
    de oorspronkelijke Mecway-naam)."""
    renames = model_data.get("group_renames", {})
    inverse = dict((v, k) for k, v in renames.items())
    named = []
    for name in model_data.get("element_selections", {}):
        if inverse.get(name, name).upper().startswith(GROUP_PREFIX):
            named.append(name)
    for es in OrderedDict.fromkeys(e[3] for e in
                                   model_data.get("mesh_elements", [])):
        if es.upper().startswith(GROUP_PREFIX) and tb.rn(es) not in named:
            named.append(tb.rn(es))
    return named


def _group_elements(tb, model_data, name):
    sel = model_data.get("element_selections", {}).get(name)
    if sel is not None:
        return list(sel)
    eids = [eid for eid, info in tb.elem.items() if info[0] == name]
    if eids:
        return eids
    if any(tb.rn(e[3]) == name for e in model_data.get("mesh_elements", [])):
        return []
    return None


def _check_group(tb, name, eids, label):
    solids = [e for e in eids if e in tb.elem and tb.elem[e][1] == "solid"]
    if len(solids) < len(eids):
        log(tr("WARNING: {0}: {1} element(en) in de brongroep zijn geen "
               "(gemodelleerde) volume-elementen en krijgen geen bron.",
               "WARNING: {0}: {1} element(s) in the source group are not "
               "(modelled) solid elements and get no source.").format(
                   label, len(eids) - len(solids)))
    if not solids:
        log(tr("ERROR: {0}: de brongroep heeft geen volume-elementen (de "
               "lasbron werkt alleen op volume-elementen).",
               "ERROR: {0}: the source group has no solid elements (the "
               "weld source only acts on solid elements).").format(label))
        return None
    if name is None or len(solids) < len(eids):
        try:
            name = tb._list_group(["M{0}".format(e) for e in solids])
        except ValueError as e:
            log(tr("ERROR: {0}: element {1} niet in het mesh gevonden.",
                   "ERROR: {0}: element {1} not found in the mesh.").format(
                       label, e))
            return None
    return name, solids


def _check_steps(src, step, label):
    """WARNING als de bron per stap meer dan MAX_JUMP x de bronlengte
    verspringt (met de stap die het wel haalt)."""
    s = src.spec
    lb = s["af"] + s["ar"]
    jump = s["v"] * step
    if jump > MAX_JUMP * lb * (1.0 + 1.0e-9):
        log(tr("WARNING: {0}: de bron verspringt {1} m per tijdstap, meer "
               "dan {2} x de bronlengte af + ar = {3} m. De temperatuur "
               "langs de rups gaat dan op en neer. Advies: stepsize <= {4} "
               "s (of een grotere bron).",
               "WARNING: {0}: the source jumps {1} m per time step, more "
               "than {2} x the source length af + ar = {3} m. The "
               "temperature along the bead then oscillates. Advice: "
               "stepsize <= {4} s (or a larger source).").format(
                   label, "%.4g" % jump, MAX_JUMP, "%.4g" % lb,
                   "%.4g" % (MAX_JUMP * lb / s["v"])))
        return False
    log("INFO: {0}: verspringing {1} m per stap ({2} x af + ar).".format(
        label, "%.4g" % jump, "%.3g" % (jump / lb)))
    return True


def _check_mesh(tb, src, eids, label):
    """WARNING als de elementen langs de baan (middelpunt binnen max(b, c)
    van de baan) in een richting van de bron groter zijn dan MAX_H x de
    halve as in die richting: afmeting langs de lasrichting t.o.v.
    min(af, ar), dwars t.o.v. b, in de diepte t.o.v. c. Returns de
    grootste verhouding (0 zonder elementen langs de baan)."""
    import bridge_mesh
    s = src.spec
    axes = (min(s["af"], s["ar"]), s["b"], s["c"])
    names = (tr("langs de lasrichting", "along the weld direction"),
             tr("dwars", "transverse"), tr("in de diepte", "in depth"))
    worst = (0.0, 0, 0.0)          # (verhouding, as, afmeting)
    for eid in eids:
        _es, _cls, atype, cn = tb.elem[eid]
        corners = [tb.nodes[n] for n in cn[:bridge_mesh._N_CORNERS[atype]]]
        cen = [sum(p[i] for p in corners) / len(corners) for i in range(3)]
        rad = max(math.sqrt(_dot(_sub(p, cen), _sub(p, cen)))
                  for p in corners)
        if _dist_to_path(cen, src.pts) > max(s["b"], s["c"]) + rad:
            continue
        # assenstelsel van het dichtstbijzijnde segment
        k = min(range(len(src.frames)), key=lambda j: _dist_to_path(
            cen, src.pts[j:j + 2]))
        for i, vec in enumerate(src.frames[k]):
            proj = [_dot(p, vec) for p in corners]
            ext = max(proj) - min(proj)
            if ext / axes[i] > worst[0]:
                worst = (ext / axes[i], i, ext)
    if worst[0] == 0.0:
        log(tr("WARNING: {0}: geen elementen direct langs de baan; ligt de "
               "baan op het model?",
               "WARNING: {0}: no elements right along the path; is the "
               "path on the model?").format(label))
        return 0.0
    ratio, i, ext = worst
    if ratio > MAX_H:
        log(tr("WARNING: {0}: elementen langs de lasbaan zijn {1} {2} m "
               "groot, {3} x de halve as {4} m (grens {5}). De bron wordt "
               "dan grof geintegreerd (zie de energiecontrole na de run). "
               "Advies: verfijn de mesh langs de rups tot <= {6} m in die "
               "richting, of vergroot de bron.",
               "WARNING: {0}: elements along the weld path are {2} m {1}, "
               "{3} x the semi-axis {4} m (limit {5}). The source is then "
               "integrated coarsely (see the energy check after the run). "
               "Advice: refine the mesh along the bead to <= {6} m in that "
               "direction, or enlarge the source.").format(
                   label, names[i], "%.3g" % ext, "%.2f" % ratio,
                   "%.3g" % axes[i], MAX_H, "%.3g" % (MAX_H * axes[i])))
    else:
        log("INFO: {0}: elementen langs de baan tot {1} x de halve as "
            "({2}).".format(label, "%.2f" % ratio, names[i]))
    return ratio


# ==========================================
# TOEVOEGMATERIAAL: GEBOORTE (stap S4c)
# ==========================================
# In de .comm en hier in de bridge dezelfde code (exec hieronder), zodat de
# geboorte van een punt (bron) en van een element (materiaal) op dezelfde
# manier gerekend worden.
BORN_FUNC = '''# Geboorte van toevoegmateriaal (bridge_welding.py, S4c): 1 als het punt
# (X, Y, Z) op tijd INST al geboren is: INST > tb = max(t0, t0 + (s -
# voorloop) / v), s = booglengte van het dichtstbijzijnde punt van de baan;
# nooit als tb na het einde van de bron ligt. B = (t0, v, voorloop, t_eind,
# punten, cum. lengtes).
def _lb_arc(X, Y, Z, pts, cum):
    # voorbij het einde van de baan doorgetrokken (s > L): daar komt de bron
    # niet, zodat dat materiaal nooit geboren wordt (verder dan de voorloop)
    best, s_best = None, 0.0
    last = len(pts) - 2
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ll = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2]
        u = ur = 0.0
        if ll > 0.0:
            ur = ((X - a[0]) * ab[0] + (Y - a[1]) * ab[1] +
                  (Z - a[2]) * ab[2]) / ll
            u = min(1.0, max(0.0, ur))
        d = ((X - a[0] - u * ab[0]) ** 2 + (Y - a[1] - u * ab[1]) ** 2 +
             (Z - a[2] - u * ab[2]) ** 2)
        if best is None or d < best:
            if k == last and ur > 1.0:
                u = ur
            best, s_best = d, cum[k] + u * (cum[k + 1] - cum[k])
    return s_best
def _lb_tborn(X, Y, Z, B):
    t0, v, lead, tstop, pts, cum = B
    return max(t0, t0 + (_lb_arc(X, Y, Z, pts, cum) - lead) / v)
def _lb_born(X, Y, Z, INST, B):
    tb = _lb_tborn(X, Y, Z, B)
    if tb > B[3]:
        return 0.0
    if INST > tb:
        return 1.0
    # geboren bij de start van de bron (tb = t0): vanaf t0 zelf
    return 1.0 if (tb <= B[0] and INST >= B[0] - 1.0e-9) else 0.0
'''
_BORN_NS = {}
exec(BORN_FUNC, _BORN_NS)


def _filler(tb, model_data, src, label, prefixed):
    """[eid] van het toevoegmateriaal van een bron (geboorte=<<selectie>>,
    of geboorte=ja: de selecties/componenten met GROUP_PREFIX). None
    (ERROR) bij een fout."""
    import bridge_custom
    birth = src.spec["birth"]
    if birth is True:
        if not prefixed:
            log(tr("ERROR: {0}: geboorte=ja vraagt een elementselectie of "
                   "component met voorvoegsel {1} (het toevoegmateriaal), "
                   "of geef geboorte=<<selectie>>.",
                   "ERROR: {0}: birth=yes needs an element selection or "
                   "component with prefix {1} (the filler material), or give "
                   "birth=<<selection>>.").format(label, GROUP_PREFIX))
            return None
        eids = []
        seen = set()
        for name in prefixed:
            for e in _group_elements(tb, model_data, name) or []:
                if e not in seen:
                    seen.add(e)
                    eids.append(e)
        what = ", ".join(prefixed)
    else:
        name = bridge_custom.substitute(
            "<<{0}>>".format(birth), model_data.get("group_renames", {}),
            model_data.get("mesh_group_names", set()))
        eids = _group_elements(tb, model_data, name)
        if eids is None:
            log(tr("ERROR: {0}: geboorte '{1}' is geen element-selectie of "
                   "component.",
                   "ERROR: {0}: birth '{1}' is not an element selection or "
                   "component.").format(label, birth))
            return None
        what = birth
    solids = [e for e in eids if e in tb.elem and tb.elem[e][1] == "solid"]
    if len(solids) < len(eids) or not solids:
        log(tr("ERROR: {0}: het toevoegmateriaal ({1}) heeft {2} element(en) "
               "die geen (gemodelleerde) volume-elementen zijn; geboorte kan "
               "alleen met volume-elementen.",
               "ERROR: {0}: the filler material ({1}) has {2} element(s) "
               "that are not (modelled) solid elements; birth only works "
               "with solid elements.").format(label, what,
                                              len(eids) - len(solids)))
        return None
    return solids


def _births(tb, model_data, sources, period, step):
    """
    Geboortetijden van het toevoegmateriaal van de bronnen met geboorte.
    Zet src.birth en tb.birth / model_data["welding_birth"] (dict, zie
    hieronder); returns de dict, {} zonder geboorte, False (ERROR).

    Element: tb = max(t0, t0 + (s_min - voorloop) / v), s_min = de kleinste
    booglengte van zijn hoekknopen (zo ligt elk punt van het element op of
    na de geboorte van het element: de bron komt nooit in een stil
    element). Nooit geboren als tb na het einde van de bron of op/na het
    einde van de analyse ligt (s voorbij het einde van de baan wordt
    doorgetrokken, _lb_arc). Per tijdstap: geboren in stap k (t_k-1 <= tb <
    t_k) = levend vanaf t_k; geboren bij de start (tb = t0): levend vanaf de
    eerste staptijd >= t0 (de bron op t0 telt dan in dat materiaal mee,
    _lb_born). NEUT1 = het midden van de stap, zodat 'INST > NEUT1' op de
    staptijden geen afrondingsgevoeligheid heeft.
    """
    import bridge_mesh
    born = [s for s in sources if s.spec.get("birth")]
    if not born:
        return {}
    if period <= 0.0 or step <= 0.0:
        log(tr("ERROR: Toevoegmateriaal (geboorte) vraagt tijdstappen "
               "(timeperiod en stepsize).",
               "ERROR: Filler material (birth) needs time steps (timeperiod "
               "and stepsize)."))
        return False
    n = max(1, int(round(period / step)))
    times = [period * k / float(n) for k in range(n + 1)]
    prefixed = _prefixed_groups(tb, model_data)
    owner = {}
    out = OrderedDict()            # eid -> stap k (1..n) of None
    for src in born:
        label = "#ASTER-LASBRON {0}".format(src.k)
        eids = _filler(tb, model_data, src, label, prefixed)
        if eids is None:
            return False
        twice = [e for e in eids if e in owner]
        if twice:
            log(tr("ERROR: {0}: {1} element(en) van het toevoegmateriaal "
                   "horen ook bij bron {2}; geef elke bron een eigen "
                   "geboorte=<<selectie>> (bijv. LASNAAD_1, LASNAAD_2).",
                   "ERROR: {0}: {1} filler element(s) also belong to source "
                   "{2}; give each source its own birth=<<selection>> (e.g. "
                   "LASNAAD_1, LASNAAD_2).").format(
                       label, len(twice), owner[twice[0]]))
            return False
        b = (src.spec["t0"], src.spec["v"], src.spec["lead"], src.t_end,
             src.pts, src.cum)
        never = 0
        first = last = None
        for eid in eids:
            owner[eid] = src.k
            _es, _cls, atype, cn = tb.elem[eid]
            corners = [tb.nodes[c] for c in
                       cn[:bridge_mesh._N_CORNERS[atype]]]
            t_b = min(_BORN_NS["_lb_tborn"](p[0], p[1], p[2], b)
                      for p in corners)
            k = None
            if t_b <= src.t_end and t_b < times[-1]:
                k = 1
                if t_b <= b[0]:
                    # geboren bij de start van de bron: levend vanaf de
                    # eerste staptijd >= t0 (zoals _lb_born: de bron op t0
                    # zelf telt dan mee)
                    while times[k] < b[0] - 1.0e-9:
                        k += 1
                else:
                    while times[k] <= t_b:
                        k += 1
                first = t_b if first is None else min(first, t_b)
                last = t_b if last is None else max(last, t_b)
            else:
                never += 1
            out[eid] = k
        src.birth = eids
        src.birth_info = (len(eids), first, last, never)
        if first is None:
            log(tr("ERROR: {0}: geen element van het toevoegmateriaal wordt "
                   "geboren (de bron komt er niet langs voor het einde van de "
                   "analyse); ligt het toevoegmateriaal langs de baan?",
                   "ERROR: {0}: no element of the filler material is born "
                   "(the source does not pass it before the end of the "
                   "analysis); does the filler lie along the path?").format(
                       label))
            return False
        log("INFO: {0}: toevoegmateriaal {1} elementen, geboren van t = {2} "
            "tot {3} s (voorloop {4} m).".format(
                label, len(eids), "%.6g" % first, "%.6g" % last,
                "%.4g" % src.spec["lead"]))
        if never:
            log(tr("WARNING: {0}: {1} element(en) van het toevoegmateriaal "
                   "worden nooit geboren (ze liggen verder dan de voorloop "
                   "voorbij het einde van de baan, of de bron of de analyse "
                   "stopt eerder); ze blijven 'stil' (geen warmteopslag, "
                   "geen stijfheid).",
                   "WARNING: {0}: {1} filler element(s) are never born (they "
                   "lie more than the lead beyond the end of the path, or "
                   "the source or the analysis stops earlier); they stay "
                   "'quiet' (no heat storage, no stiffness).").format(
                       label, never))
    # Groepen per (geboortestap, materiaal): NEUT1 in het thermische
    # materiaal, de materiaalwissel in de lussen (THER_NON_LINE,
    # STAT_NON_LINE); per materiaal (AFFE_MATERIAU) en alles samen.
    def mat_of(eid):
        return tb.elsets[tb.elem[eid][0]]["mat"]
    steps = OrderedDict()
    for eid, k in out.items():
        steps.setdefault((k, mat_of(eid)), []).append(eid)
    try:
        groups = OrderedDict()
        for key in sorted(steps, key=lambda x: (x[0] is None, x[0])):
            groups[key] = tb._list_group(["M{0}".format(e)
                                          for e in steps[key]])
        by_mat = OrderedDict()
        for eid in out:
            by_mat.setdefault(mat_of(eid), []).append(eid)
        mats = OrderedDict((m, tb._list_group(["M{0}".format(e) for e in ids]))
                           for m, ids in by_mat.items())
        every = tb._list_group(["M{0}".format(e) for e in out])
    except ValueError as e:
        log(tr("ERROR: Toevoegmateriaal: element {0} niet in het mesh "
               "gevonden.",
               "ERROR: Filler material: element {0} not found in the "
               "mesh.").format(e))
        return False
    info = {
        "times": times,
        # [(stap k (levend vanaf times[k]; None = nooit), materiaal, groep,
        #   NEUT1 = midden van de geboortestap)]
        "steps": [(k, m, g, (0.5 * (times[k - 1] + times[k])
                             if k is not None else 1.0e30))
                  for (k, m), g in groups.items()],
        "mats": mats,
        "all": every,
        "elements": out,
        "quiet": QUIET,
    }
    tb.birth = info
    model_data["welding_birth"] = info
    return info


def _source_parts(tb, src, sources, birth):
    """[(groep, bron met geboorte of None)]: de brongroep gesplitst in het
    deel buiten elk toevoegmateriaal (gewone bron) en per toevoegmateriaal
    het deel daarin (bron alleen waar dat al geboren is)."""
    owner = {}
    for other in sources:
        for e in other.birth or []:
            owner[e] = other
    plain = [e for e in src.eids if e not in owner]
    split = OrderedDict()
    for e in src.eids:
        if e in owner:
            split.setdefault(owner[e].k, (owner[e], []))[1].append(e)
    if not split:
        return [(src.group, None)]
    parts = []
    try:
        if plain:
            parts.append((tb._list_group(["M{0}".format(e) for e in plain]),
                          None))
        for _k, (other, eids) in split.items():
            parts.append((tb._list_group(["M{0}".format(e) for e in eids]),
                          other))
    except ValueError as e:
        log(tr("ERROR: Lasbron: element {0} niet in het mesh gevonden.",
               "ERROR: Weld source: element {0} not found in the mesh.")
            .format(e))
        return None
    return parts


def birth_materials(tb, names):
    """
    Thermische materialen van het toevoegmateriaal ("quiet element"): voor
    de geboorte lambda x QUIET^2 en rho*cp x QUIET, daarna de gewone
    waarden.

    THER_LINEAIRE (lineair materiaal): THER_FO met LAMBDA en RHO_CP als
    FORMULE van INST en NEUT1 (= het midden van de geboortestap) in een
    enkele solve. Code-Aster 17.4: THER_FO met functies van INST (testcase
    ttnp201a) en van een commandovariabele NEUT1 (testcase ssnp160a,
    AFFE_VARC CHAM_GD); het materiaal geldt op het einde van de stap (INST
    = t+): een element geboren in stap k (NEUT1 = midden) telt mee vanaf
    t_k (gezien in een prototype, WE-11).

    THER_NON_LINE (THER_NL: lambda(T), c(T), of straling): BETA en RHO_CP
    mogen in Code-Aster 17.4 geen formule of nappe zijn (MODELISA6_31,
    MODELISA6_58, gezien in een prototype), dus geen functie van NEUT1:
    een eigen 'stil' THER_NL-materiaal (functies x QUIET^2 / x QUIET) en een
    lus met THER_NON_LINE per geboortestap met een nieuw AFFE_MATERIAU
    (ther_loop).

    names: {(materiaal, f): concept} uit _Thermal._fieldmat.
    Returns (regels, [AFFE-entries], AFFE_VARC-tekst).
    """
    from bridge_mesh import _real
    birth = tb.birth
    mats = tb.th["materials"]
    lines, affe = [], []
    q = birth["quiet"]
    birth["concepts"] = {}
    if not tb.nonlinear:
        lines.append(
            "# Toevoegmateriaal (bridge_welding.birth_materials): het midden "
            "van de geboortestap\n# per element als NEUT1 (nooit geboren: "
            "1e30)\n"
            "gb_tb = CREA_CHAMP(TYPE_CHAM='CART_NEUT_R', OPERATION='AFFE', "
            "MAILLAGE=mesh, AFFE=(\n    {0},\n))".format(",\n    ".join(
                "_F(GROUP_MA='{0}', NOM_CMP='X1', VALE={1})".format(
                    g, _real(t)) for _k, _m, g, t in birth["steps"])))
    for mat, grp in birth["mats"].items():
        base = names.get((mat, 1.0))
        birth["concepts"][mat] = base
        p = mats[mat]
        lam = p["lambda"]
        rcp = p["rho"] * p["cp"]
        concept = "{0}_GB".format(base)
        if not tb.nonlinear:
            lines.append(
                "{0}_L = FORMULE(VALE='L if INST > NEUT1 else L * Q * Q', "
                "NOM_PARA=('INST', 'NEUT1'), L={1}, Q={3})\n"
                "{0}_C = FORMULE(VALE='C if INST > NEUT1 else C * Q', "
                "NOM_PARA=('INST', 'NEUT1'), C={2}, Q={3})\n"
                "{0} = DEFI_MATERIAU(THER_FO=_F(LAMBDA={0}_L, RHO_CP={0}_C))"
                .format(concept, _real(lam), _real(rcp), _real(q)))
        elif "lambda_T" in p or "cp_T" in p:
            lines.append("# stil (nog niet geboren): lambda x {0}, rho*cp x "
                         "{1}".format(_real(q * q), _real(q)))
            lines.append(tb._tempdep_funcs(concept, p, q, lam * q * q,
                                           rcp * q, f_lambda=q * q))
            lines.append("{0} = DEFI_MATERIAU(THER_NL=_F(LAMBDA={0}_L, "
                         "RHO_CP={0}_C))".format(concept))
        else:
            lines.append(
                "# stil (nog niet geboren)\n"
                "{0} = DEFI_MATERIAU(THER_NL=_F(LAMBDA=DEFI_CONSTANTE(VALE="
                "{1}), RHO_CP=DEFI_CONSTANTE(VALE={2})))".format(
                    concept, _real(lam * q * q), _real(rcp * q)))
        affe.append("_F(GROUP_MA='{0}', MATER={1})".format(grp, concept))
    if tb.nonlinear:
        return lines, affe, ""
    varc = ("    AFFE_VARC=_F(GROUP_MA='{0}', NOM_VARC='NEUT1', "
            "CHAM_GD=gb_tb),\n".format(birth["all"]))
    return lines, affe, varc


def birth_loop_data(birth, concepts, prefix="_gb"):
    """Python-regels voor een geboortelus in de .comm: {stap k: [(groep,
    materiaalconcept)]} van de elementen die vanaf times[k] leven
    ({prefix}_born). concepts: {materiaal: concept van het gewone
    materiaal}."""
    born = OrderedDict()
    for k, mat, grp, _t in birth["steps"]:
        if k is not None:
            born.setdefault(k, []).append((grp, concepts[mat]))
    return "{0}_born = {{\n{1}}}\n".format(prefix, "".join(
        "    {0}: [{1}],\n".format(k, ", ".join(
            "('{0}', {1})".format(g, c) for g, c in items))
        for k, items in born.items()))


def ther_loop(tb, affe, args):
    """
    THER_NON_LINE met toevoegmateriaal (THER_NL, zie birth_materials): per
    geboortestap een AFFE_MATERIAU met de geboren elementen op hun gewone
    materiaal (na de stille toewijzing: de laatste telt) en THER_NON_LINE
    van de vorige geboortestap tot hier (reuse, ETAT_INIT EVOL_THER: de
    temperatuur loopt door). affe: de AFFE-entries van fieldmat; args: de
    andere argumenten van THER_NON_LINE (zonder CHAM_MATER, ETAT_INIT,
    INCREMENT).
    """
    birth = tb.birth
    return (
        "# --- Toevoegmateriaal (bridge_welding.ther_loop): THER_NON_LINE "
        "per geboortestap ---\n"
        "_gb_affe = [\n    {affe},\n]\n"
        "{born}"
        "_gb_t = list(times.getValues())\n"
        "_gb_alive = []\n"
        "_gb_start = 0\n"
        "res = None\n"
        "for _gb_k in sorted(_gb_born) + [len(_gb_t)]:\n"
        "    _gb_stop = min(_gb_k - 1, len(_gb_t) - 1)\n"
        "    if _gb_stop > _gb_start:\n"
        "        _gb_cm = AFFE_MATERIAU(MAILLAGE=mesh, MODELE=model, AFFE=tuple(\n"
        "            _gb_affe + [_F(GROUP_MA=_g, MATER=_m) for _g, _m in "
        "_gb_alive]))\n"
        "        _gb_kw = dict(ETAT_INIT=_F(CHAM_NO=temp0)) if res is None else "
        "dict(\n"
        "            reuse=res, RESULTAT=res, ETAT_INIT=_F(EVOL_THER=res))\n"
        "        res = THER_NON_LINE(\n"
        "            CHAM_MATER=_gb_cm,\n"
        "            INCREMENT=_F(LIST_INST=times, INST_INIT=_gb_t[_gb_start], "
        "INST_FIN=_gb_t[_gb_stop]),\n"
        "{args}"
        "            **_gb_kw)\n"
        "        _gb_start = _gb_stop\n"
        "    if _gb_k < len(_gb_t):\n"
        "        _gb_alive += _gb_born[_gb_k]\n"
        "print('BRIDGE_GEBOORTE_THER %d' % len(_gb_alive))\n").format(
            affe=",\n    ".join(affe),
            born=birth_loop_data(birth, birth["concepts"]),
            args="".join("            " + a.strip() + "\n" for a in args))


def apply(tb, model_data, analysis):
    """
    Lasbronnen uit de #ASTER-LASBRON-regels in de thermische builder tb
    (bridge_thermal._Thermal). Returns (code, [last-namen voor EXCIT],
    nabewerking) of None bij een fout; ("", [], "") zonder lasbron.
    """
    bodies = model_data.get("aster_custom", {}).get("welding", [])
    if not bodies:
        return "", [], ""
    specs = parse_specs(bodies)
    if specs is None:
        return None
    if not tb.transient:
        log(tr("ERROR: #ASTER-LASBRON vraagt een transiente thermische "
               "analyse (Mecway Thermal transient, T31).",
               "ERROR: #ASTER-LASBRON needs a transient thermal analysis "
               "(Mecway Thermal transient, T31)."))
        return None
    ts = tb.th.get("timesteps", {})
    period, step = ts.get("period", 0.0), ts.get("step", 0.0)
    if period > 0.0 and step > 0.0:
        step = period / max(1, int(round(period / step)))
    sources = []
    code = [GOLDAK_FUNC]
    excit = []
    for spec in specs:
        label = "#ASTER-LASBRON {0}".format(spec["index"])
        found = _path(spec, model_data, period, label)
        if found is None:
            return None
        pts, cum = found
        frames = _segment_frames(pts, spec["depth"], label)
        if frames is None:
            return None
        src = _Source(spec, pts, cum, frames)
        grp = _source_group(tb, model_data, src, label)
        if grp is None:
            return None
        src.group, eids = grp
        if src.t_end <= spec["t0"]:
            log(tr("ERROR: {0}: de bron is nooit aan (t0 = {1} s, einde {2} "
                   "s).",
                   "ERROR: {0}: the source is never on (t0 = {1} s, end {2} "
                   "s).").format(label, spec["t0"], src.t_end))
            return None
        if ("length" in spec or "path" in spec) and \
                src.t_end > period * (1.0 + 1.0e-9):
            log(tr("WARNING: {0}: de bron is op het einde van de analyse "
                   "({1} s) nog niet aan het einde van de baan (t = {2} s).",
                   "WARNING: {0}: at the end of the analysis ({1} s) the "
                   "source has not yet reached the end of the path (t = {2} "
                   "s).").format(label, period, "%.6g" % src.t_end))
        if step > 0.0:
            _check_steps(src, step, label)
        _check_mesh(tb, src, eids, label)
        log("INFO: {0}: Goldak, Q_eff = {1} W (eta {2}), v = {3} m/s, baan "
            "{4} m van t = {5} tot {6} s, af/ar/b/c = {7}/{8}/{9}/{10} m, "
            "ff/fr = {11}/{12}, brongroep {13} ({14} elementen).".format(
                label, "%.6g" % src.q_eff, spec["eta"], spec["v"],
                "%.6g" % src.length, spec["t0"], "%.6g" % src.t_end,
                spec["af"], spec["ar"], spec["b"], spec["c"],
                "%.4g" % spec["ff"], "%.4g" % spec["fr"], src.group,
                len(eids)))
        src.eids = eids
        sources.append(src)
    # Toevoegmateriaal (geboorte, S4c): geboortetijden per element, in het
    # niet-gedraaide mesh (voor de rotatie hieronder)
    birth = _births(tb, model_data, sources, period, step)
    if birth is False:
        return None
    if birth:
        code.append(BORN_FUNC)
    for src in sources:
        if tb.rotation:
            # Gedraaid mesh (schalen als PLAN, bridge_thermal._shell_rotation):
            # X, Y, Z in de FORMULE zijn x_rot = Q x.
            q = tb.rotation[0]

            def rot(v):
                return tuple(sum(q[i][j] * v[j] for j in range(3))
                             for i in range(3))
            src.pts = [rot(p) for p in src.pts]
            src.frames = [tuple(rot(v) for v in f) for f in src.frames]
        if src.birth is not None:
            code.append(src.born_line())
    for src in sources:
        code.append(src.param_line())
        code.append(
            "LB{0} = FORMULE(VALE='_lb_goldak(X, Y, Z, INST, _LB{0})', "
            "NOM_PARA=('X', 'Y', 'Z', 'INST'),\n    _lb_goldak=_lb_goldak, "
            "_LB{0}=_LB{0})".format(src.k))
        parts = _source_parts(tb, src, sources, birth) if birth else \
            [(src.group, None)]
        if parts is None:
            return None
        entries = []
        for grp, other in parts:
            if other is None:
                entries.append("_F(GROUP_MA='{0}', SOUR=LB{1})".format(
                    grp, src.k))
                continue
            # Bron in het toevoegmateriaal van bron 'other': alleen waar dat
            # al geboren is (anders kwam de warmte in een stil element met
            # rho*cp x QUIET)
            name = "LB{0}_{1}".format(src.k, other.k)
            code.append(
                "{0} = FORMULE(VALE='_lb_goldak(X, Y, Z, INST, _LB{1}) if "
                "_lb_born(X, Y, Z, INST, _GB{2}) else 0.0',\n"
                "    NOM_PARA=('X', 'Y', 'Z', 'INST'), _lb_goldak=_lb_goldak, "
                "_lb_born=_lb_born,\n    _LB{1}=_LB{1}, _GB{2}=_GB{2})".format(
                    name, src.k, other.k))
            entries.append("_F(GROUP_MA='{0}', SOUR={1})".format(grp, name))
        code.append("lasbron_{0} = AFFE_CHAR_THER_F(MODELE=model, SOURCE=("
                    "\n    {1},\n))".format(src.k, ",\n    ".join(entries)))
    if len(sources) == 1 and not tb.func_sources:
        excit.append("lasbron_1")
    else:
        # Meer bronnen, of een lasbron naast Mecway-warmtebronnen als
        # formule of tijdstabel: een last met per deel van het mesh de som
        # van de bronnen. Code-Aster 17.4 rekent twee lasten
        # AFFE_CHAR_THER_F met SOURCE in een lijst (EXCIT, CALC_VECT_ELEM)
        # allebei met de functie van de eerste last (bridge_thermal.
        # add_func_source). lasbron_<k> blijven voor de energiecontrole per
        # bron.
        merged = _merged_load(tb, sources)
        if merged is None:
            return None
        code.append(merged)
        excit.append("lasbron")
    model_data["welding_sources"] = [
        {"index": s.k, "power": s.target, "t0": s.spec["t0"],
         "t_end": s.t_end, "group": s.group} for s in sources]
    return ("# --- Lasbronnen (#ASTER-LASBRON, bridge_welding.py) ---\n" +
            "\n".join(code) + "\n# --- einde lasbronnen ---\n", excit,
            _energy_block(sources, period, step))


def _merged_load(tb, sources):
    """
    Een AFFE_CHAR_THER_F 'lasbron' met alle bronnen samen: de lasbronnen en
    de Mecway-warmtebronnen als functie (tb.func_sources; die laat
    bridge_thermal dan weg, tb.sources_taken). Het mesh wordt verdeeld
    naar (de bronnen waarvan het element in de brongroep ligt, het
    toevoegmateriaal waartoe het hoort); per deel een FORMULE met de som
    van die bronnen, in toevoegmateriaal alleen waar het al geboren is
    (bridge_thermal._Thermal.merged_sources). Returns de .comm-tekst, of
    None (ERROR).
    """
    owner = {}
    for s in sources:
        for e in s.birth or []:
            owner[e] = s.k
    items = []
    for s in sources:
        items.append({
            "grp": s.group, "sour": None, "eids": s.eids,
            "term": "_lb_goldak(X, Y, Z, INST, _LB{0})".format(s.k),
            "ctx": OrderedDict([("_lb_goldak", "_lb_goldak"),
                                ("_LB{0}".format(s.k), "_LB{0}".format(s.k))]),
            "params": ["X", "Y", "Z", "INST"]})
    if tb.func_sources:
        log("INFO: Lasbron: {0} Mecway-warmtebron(nen) als formule of "
            "tijdstabel in dezelfde last 'lasbron'.".format(
                len(tb.func_sources)))
        items += tb.source_items()

    def born(j):
        return ("_lb_born(X, Y, Z, INST, _GB{0})".format(j),
                OrderedDict([("_lb_born", "_lb_born"),
                             ("_GB{0}".format(j), "_GB{0}".format(j))]))
    merged = tb.merged_sources(items, owner, born, prefix="LBS")
    if merged is None:
        return None
    tb.sources_taken = True
    lines = ["# Alle lasbronnen in een last (bridge_welding._merged_load)"]
    lines += merged[0]
    lines.append("lasbron = AFFE_CHAR_THER_F(MODELE=model, SOURCE=(\n    {0},"
                 "\n))".format(",\n    ".join(merged[1])))
    return "\n".join(lines)


def _energy_block(sources, period, step):
    """Energiecontrole in de job: per bron op enkele tijdstippen het
    vermogen dat het mesh opneemt (som van de knooplasten van de last, zoals
    THER_LINEAIRE/THER_NON_LINE ze integreren: CALC_VECT_ELEM CHAR_THER,
    catalogus calc_vect_elem.py) tegen het doel (ff + fr)/2 x eta x Q.
    Regels 'BRIDGE_LASBRON <bron> <t> <opgenomen W> <doel W>' in de .mess
    (report_lines)."""
    from bridge_mesh import _real
    lines = ["# Energiecontrole lasbron (bridge_welding._energy_block)",
             "nu_lb = NUME_DDL(MODELE=model)"]
    for src in sources:
        t0, t1 = src.spec["t0"], min(src.t_end, period)
        # 5 tijdstippen binnen de aan-periode (niet precies op t0/t1)
        times = [t0 + (t1 - t0) * (k + 0.5) / 5.0 for k in range(5)]
        lines.append(
            "for _t in ({0},):\n"
            "    _ve = CALC_VECT_ELEM(OPTION='CHAR_THER', CHARGE=lasbron_{1}, "
            "INST=_t)\n"
            "    _va = ASSE_VECTEUR(VECT_ELEM=_ve, NUME_DDL=nu_lb)\n"
            "    print('BRIDGE_LASBRON %d %r %r %r' % ({1}, _t, "
            "float(sum(_va.getValues())), {2}))".format(
                ", ".join(_real(t) for t in times), src.k,
                _real(src.target)))
        info = getattr(src, "birth_info", None)
        if info and info[1] is not None:
            # samenvatting toevoegmateriaal voor het statusvak (report_lines)
            lines.append("print('BRIDGE_GEBOORTE %d %d %r %r %d' % ({0}, {1}, "
                         "{2}, {3}, {4}))".format(src.k, info[0],
                                                  _real(info[1]),
                                                  _real(info[2]), info[3]))
    return "\n".join(lines) + "\n"


# ==========================================
# NA DE RUN
# ==========================================
_ROW = re.compile(r"^BRIDGE_LASBRON\s+(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)"
                  r"\s+([-+0-9.eE]+)")


def read_energy(mess_path):
    """{bron: [(t, opgenomen W, doel W)]} uit de .mess; {} zonder."""
    import io
    import os
    out = OrderedDict()
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            m = _ROW.match(line.strip())
            if m:
                out.setdefault(int(m.group(1)), []).append(
                    (float(m.group(2)), float(m.group(3)),
                     float(m.group(4))))
    finally:
        f.close()
    return out


def _symmetry_hint(lo, hi):
    """Extra tekst bij de vermogens-WARNING als het mesh (bijna precies) de
    helft of een kwart van de bron opneemt: dan ligt de baan meestal op een
    of twee symmetrievlakken zonder symmetrie= (docs-controle S11: WE-02
    zonder symmetrie=1 gaf 50,0%; test: tests/test_bridge_welding_energy.py)."""
    for n in (1, 2):
        if max(abs(lo * 2 ** n - 1.0), abs(hi * 2 ** n - 1.0)) <= POWER_TOL:
            return tr(u" Het mesh neemt 1/{0} van de bron op: ligt de baan op "
                      u"{1} symmetrievlak(ken)? Zet dan symmetrie={1} in de "
                      u"#ASTER-LASBRON-regel.",
                      u" The mesh takes up 1/{0} of the source: does the path "
                      u"lie on {1} symmetry plane(s)? Then set symmetry={1} "
                      u"in the #ASTER-LASBRON line.").format(2 ** n, n)
    return u""


def report_lines(mess_path):
    """Regels voor log en statusvak (energiecontrole per bron); WARNING
    in de log als het opgenomen vermogen meer dan POWER_TOL afwijkt."""
    lines = []
    for k, rows in read_energy(mess_path).items():
        target = rows[0][2]
        fr = [p / target for _t, p, _q in rows if target]
        if not fr:
            continue
        lo, hi = min(fr), max(fr)
        line = tr(u"Lasbron {0}: het mesh neemt {1}..{2}% van het vermogen "
                  u"{3} W op (energiecontrole op {4} tijdstippen).",
                  u"Weld source {0}: the mesh takes up {1}..{2}% of the "
                  u"power {3} W (energy check at {4} times).").format(
                      k, "%.1f" % (100.0 * lo), "%.1f" % (100.0 * hi),
                      "%.6g" % target, len(fr))
        log(u"INFO: " + line)
        if max(abs(lo - 1.0), abs(hi - 1.0)) > POWER_TOL:
            log(tr(u"WARNING: Lasbron {0}: opgenomen vermogen wijkt meer dan "
                   u"{1}% af van Q_eff: de mesh langs de rups is te grof "
                   u"voor de bron (of de bron ligt deels buiten het model). "
                   u"Verfijn de mesh langs de rups of vergroot af/ar/b/c.",
                   u"WARNING: Weld source {0}: the absorbed power deviates "
                   u"more than {1}% from Q_eff: the mesh along the bead is "
                   u"too coarse for the source (or the source lies partly "
                   u"outside the model). Refine the mesh along the bead or "
                   u"enlarge af/ar/b/c.").format(k, int(POWER_TOL * 100))
                + _symmetry_hint(lo, hi))
            line += tr(u" Afwijking > {0}%: mesh te grof voor de bron.",
                       u" Deviation > {0}%: mesh too coarse for the source.")\
                .format(int(POWER_TOL * 100))
        lines.append(line)
    lines += _birth_report(mess_path)
    # Keten thermisch -> mechanisch: restspanning en vervorming
    # (bridge_thermomech.report_lines, regels BRIDGE_THERMOMECA)
    import bridge_thermomech
    return lines + bridge_thermomech.report_lines(mess_path)


_BIRTH_ROW = re.compile(r"^BRIDGE_GEBOORTE\s+(\d+)\s+(\d+)\s+([-+0-9.eE]+)"
                        r"\s+([-+0-9.eE]+)\s+(\d+)")


def _birth_report(mess_path):
    """Regels voor het statusvak: het toevoegmateriaal per bron (regels
    BRIDGE_GEBOORTE in de .mess, _energy_block)."""
    import io
    import os
    out = []
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for row in f:
            m = _BIRTH_ROW.match(row.strip())
            if not m:
                continue
            k, n, never = int(m.group(1)), int(m.group(2)), int(m.group(5))
            line = tr(u"Lasbron {0}: toevoegmateriaal {1} elementen, geboren "
                      u"van t = {2} tot {3} s{4}.",
                      u"Weld source {0}: filler material {1} elements, born "
                      u"from t = {2} to {3} s{4}.").format(
                          k, n, "%.4g" % float(m.group(3)),
                          "%.4g" % float(m.group(4)),
                          tr(u" ({0} nooit)", u" ({0} never)").format(never)
                          if never else u"")
            log(u"INFO: " + line)
            out.append(line)
    finally:
        f.close()
    return out
