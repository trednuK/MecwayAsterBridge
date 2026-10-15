# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_bcs.py
# Definieert de BC-klassen (randvoorwaarden / belastingen) en het SUPPORTED_BCS-register.
#
# Elk BC-type erft van BaseBC en implementeert twee methoden:
#   parse_xml()     - leest parameters uit het Mecway .liml XML-element
#   to_aster_dict() - vertaalt de parameters naar het Code-Aster sleutelwoord-formaat
#
# De scheiding tussen parse_xml() en to_aster_dict() maakt het mogelijk om
# tussenstappen te doen (bijv. krachtverdeling over knopen, injectie van
# model-niveau flags) voordat de uiteindelijke Code-Aster syntax wordt gegenereerd.
#
# Interne metadata-sleutels in params (prefix "_") worden door bridge_from_liml.py
# (en eventueel bridge_mesh.py) geinjecteerd NA de parse_xml()-aanroep. Zo
# hoeven de BC-klassen zelf geen kennis te hebben van het totale model.
# Voorbeeld: "_has_rot_dofs" bepaalt in FixedBC.to_aster_dict() of de
# inklemming DX=DY=DZ=0 of BLOCAGE=('DEPLACEMENT', 'ROTATION') wordt.
#
# Compatibel met IronPython 2.7.9.

import math
import re
from collections import OrderedDict
from bridge_utils import log, parse_and_convert, tr


# ==========================================
# FORMULES ALS WAARDE
# Mecway schrijft een formule zonder eenheid in de tekst; de eenheden staan
# als attributen (manual v33 par. 12.1: "in the case of formulas, appear as
# separate XML attributes"), bijv. Samples/PipeClip.liml:
#   <value unit="mm" timeunit="s" positionunit="mm">-12*t</value>
# unit = eenheid van de uitkomst, timeunit = eenheid van t, positionunit =
# eenheid van x, y, z. Een formule in t is een tijdshistorie (manual par. 9:
# "a Formula with the variable t ... evaluated at each time step").
#
# Taal (Formula Help-venster van Mecway 33, teksten in mecway.exe):
# + - * / ^ ( ), pi, e, sin, cos, tan, asin, acos, atan, atan2(y,x), log,
# abs, sqrt, heaviside(x), unittriangle(w,x), max(x,y), min(x,y).
# Nagemeten met Mecway 33 (headless, kracht als formule op een staafje van
# 2 hex8, niet-lineair statisch met CCX en dynamisch met de interne solver):
#   log = natuurlijke logaritme (log(10) = 2,3026); heaviside(0) = 0,5;
#   unittriangle(w,x) = driehoek met basis w rond x = 0 en oppervlak 1
#   (top 2/w); -2^2 = -4 (^ bindt sterker dan het minteken); 2^3^2 = 512
#   (^ van rechts naar links); sin in radialen; timeunit "min" wordt
#   toegepast (t in minuten); t loopt vanaf 0 s.
# Lineair statisch (gemeten): de interne solver negeert een last in t
# (ook een tabel; verplaatsing 0), CCX neemt de formule bij t = 0 en een
# tabel bij t = 1. De bridge neemt in MECA_STATIQUE, zoals bij een tabel,
# de laatste waarde (bridge_to_aster, met WARNING).
#
# Mecway bemonstert een formule voor CCX en OpenRadioss op 10001 gelijke
# tijden en houdt de punten over waarmee de stuksgewijs lineaire functie
# hoogstens 0,01% van het bereik afwijkt (manual par. 9). De bridge doet
# hetzelfde over 0..timeperiod (<timesteps>; zonder: 1 s, zoals
# bridge_from_liml). Een formule zonder t is een gewone waarde.
#
# Formules in x, y, z (plaatsafhankelijk, eventueel ook met t): een
# PositionFormula (hieronder), in de .comm een FORMULE van X, Y, Z (en INST)
# in AFFE_CHAR_MECA_F (bridge_to_aster._build_charges). Alleen voor de
# lasten met position_ok = True (druk, traction, kracht, line pressure,
# opgelegde verplaatsing en rotatie); elders blijft het een FormulaError.
# Gemeten met Mecway 34 (headless, mw_solve.py, blok 1 x 2 x 0,1 m van
# hex8 met de onderkant vast, interne solver en CCX):
#   - druk 3*y^2 kPa (positionunit m) op de bovenkant: reactie 8000 N en
#     moment 12000 N.m, exact (integraal); met positionunit mm en
#     3e-6*y^2 hetzelfde, dus x, y, z in positionunit;
#   - traction x = 2*x+1, z = y^3 kPa: reacties -4000 N en -4000 N
#     (exact), moment -6399,96 N.m (exact -6400: Mecway bemonstert per
#     vlak, manual par. 9.14: 1, 7 of 9 punten);
#   - kracht (op vlakken en op knopen), opgelegde verplaatsing/rotatie en
#     line pressure met x, y of z in de formule (ook 1000*(1+y)): Mecway
#     legt NIETS op (reacties en verplaatsingen 0), met de interne solver
#     en met CCX (ook niet-lineair); gravity met x in de formule en een
#     richtingsvector als formule: Mecway rekent niet (geen oplossing);
#   - druk 3*y^2*t met CCX (niet-lineair): rekent (verplaatsing evenredig
#     met t; de beperking "not ... both time and position" in de handleiding
#     staat bij de thermische lasten, par. 9.23 e.v.).
# De bridge vertaalt de plaatsafhankelijke kracht, verplaatsing en line
# pressure toch (de bedoeling van de formule) en meldt het verschil met
# Mecway (WARNING, bridge_from_liml._check_position_formulas).
# ==========================================
_FORMULA_ATTRS = ("unit", "timeunit", "positionunit")
_FORMULA_SAMPLES = 10000          # intervallen: 10001 tijden (Mecway)
_FORMULA_REL_TOL = 1.0e-4         # 0,01% van het bereik (Mecway)


class FormulaError(ValueError):
    """Formule die niet vertaald kan worden. De tekst (NL en EN, met
    dezelfde placeholders) eindigt op ';' en past in de melding
    "ERROR: <last>: <tekst> NIET meegenomen." (zoals
    bridge_from_liml._not_translated)."""

    def __init__(self, nl, en, *args):
        ValueError.__init__(self, en.format(*args))
        self.nl = nl
        self.en = en
        self.fmt_args = args

    def text(self):
        return tr(self.nl, self.en).format(*self.fmt_args)


def _heaviside(x):
    if x > 0.0:
        return 1.0
    if x < 0.0:
        return 0.0
    return 0.5


def _unittriangle(w, x):
    if w <= 0.0:
        raise ValueError("unittriangle: w <= 0")
    half = 0.5 * w
    if abs(x) >= half:
        return 0.0
    return (2.0 / w) * (1.0 - abs(x) / half)


def _power(a, b):
    # math.pow geeft ValueError bij een negatief grondtal met een
    # gebroken exponent (CPython 3: ** zou een complex getal geven).
    return math.pow(a, b)


_FORMULA_FUNCS = {
    "sin": (1, math.sin), "cos": (1, math.cos), "tan": (1, math.tan),
    "asin": (1, math.asin), "acos": (1, math.acos), "atan": (1, math.atan),
    "atan2": (2, math.atan2), "log": (1, math.log), "abs": (1, abs),
    "sqrt": (1, math.sqrt), "heaviside": (1, _heaviside),
    "unittriangle": (2, _unittriangle), "max": (2, max), "min": (2, min),
}
_FORMULA_CONSTS = {"pi": math.pi, "e": math.e}
_FORMULA_VARS = ("t", "x", "y", "z")
_FORMULA_TOKEN = re.compile(
    r"\s*(?:((?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)"
    r"|([A-Za-z_][A-Za-z_0-9]*)|(\S))")


def _formula_tokens(text):
    """[(soort, tekst)] met soort 'num', 'name' of 'op'."""
    tokens = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = _FORMULA_TOKEN.match(text, pos)
        if m is None or m.end() == pos:
            break
        pos = m.end()
        if m.group(1) is not None:
            tokens.append(("num", m.group(1)))
        elif m.group(2) is not None:
            tokens.append(("name", m.group(2).lower()))
        else:
            tokens.append(("op", m.group(3)))
    return tokens


class _FormulaParser(object):
    """
    Recursive descent; levert een functie f(t) (closures, geen eval) en de
    gebruikte variabelen. Grammatica (zie de metingen hierboven):
      expr   := term (('+' | '-') term)*
      term   := unary (('*' | '/') unary)*
      unary  := ('-' | '+') unary | power
      power  := atom ('^' unary)?        (rechts-associatief)
      atom   := getal | naam | naam '(' expr (',' expr)* ')' | '(' expr ')'
    x, y en z worden als variabele herkend (voor de melding), maar niet
    berekend.
    """

    def __init__(self, text):
        self.text = text
        self.tokens = _formula_tokens(text)
        self.pos = 0
        self.used = set()

    def parse(self):
        if not self.tokens:
            raise ValueError(tr(u"lege formule", u"empty formula"))
        fn = self._expr()
        if self.pos != len(self.tokens):
            raise ValueError(tr(u"onverwacht '{0}'", u"unexpected '{0}'")
                             .format(self.tokens[self.pos][1]))
        return fn

    def _peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (None, None)

    def _take(self, op):
        if self._peek() == ("op", op):
            self.pos += 1
            return True
        return False

    def _expr(self):
        fn = self._term()
        while True:
            if self._take("+"):
                fn = (lambda a, b: lambda t: a(t) + b(t))(fn, self._term())
            elif self._take("-"):
                fn = (lambda a, b: lambda t: a(t) - b(t))(fn, self._term())
            else:
                return fn

    def _term(self):
        fn = self._unary()
        while True:
            if self._take("*"):
                fn = (lambda a, b: lambda t: a(t) * b(t))(fn, self._unary())
            elif self._take("/"):
                fn = (lambda a, b: lambda t: a(t) / b(t))(fn, self._unary())
            else:
                return fn

    def _unary(self):
        if self._take("-"):
            return (lambda a: lambda t: -a(t))(self._unary())
        if self._take("+"):
            return self._unary()
        return self._power()

    def _power(self):
        fn = self._atom()
        if self._take("^"):
            fn = (lambda a, b: lambda t: _power(a(t), b(t)))(
                fn, self._unary())
        return fn

    def _atom(self):
        kind, text = self._peek()
        if kind is None:
            raise ValueError(tr(u"formule onvolledig",
                                u"formula incomplete"))
        self.pos += 1
        if kind == "num":
            value = float(text)
            return lambda t: value
        if kind == "op":
            if text == "(":
                fn = self._expr()
                if not self._take(")"):
                    raise ValueError(tr(u"')' ontbreekt", u"')' missing"))
                return fn
            raise ValueError(tr(u"onverwacht '{0}'",
                                u"unexpected '{0}'").format(text))
        if self._take("("):
            if text not in _FORMULA_FUNCS:
                raise ValueError(tr(u"onbekende functie '{0}'",
                                    u"unknown function '{0}'").format(text))
            nargs, func = _FORMULA_FUNCS[text]
            args = [self._expr()]
            while self._take(","):
                args.append(self._expr())
            if not self._take(")"):
                raise ValueError(tr(u"')' ontbreekt", u"')' missing"))
            if len(args) != nargs:
                raise ValueError(tr(u"{0} verwacht {1} argument(en)",
                                    u"{0} expects {1} argument(s)").format(
                                        text, nargs))
            if nargs == 1:
                return (lambda f, a: lambda t: f(a(t)))(func, args[0])
            return (lambda f, a, b: lambda t: f(a(t), b(t)))(
                func, args[0], args[1])
        if text in _FORMULA_CONSTS:
            value = _FORMULA_CONSTS[text]
            return lambda t: value
        if text in _FORMULA_VARS:
            self.used.add(text)
            return lambda t: t
        raise ValueError(tr(u"onbekende naam '{0}'",
                            u"unknown name '{0}'").format(text))


def _is_formula(node):
    """True als de waarde van node een Mecway-formule is (eenheden als
    attributen)."""
    return any(node.get(a) is not None for a in _FORMULA_ATTRS)


def _unit_map(unit, quantity):
    """(a, b) met SI = a * waarde + b voor de eenheid unit (via
    parse_and_convert; ook een verschuiving zoals degC)."""
    unit = (unit or "").strip()
    b = parse_and_convert(u"0 " + unit, quantity)
    a = parse_and_convert(u"1 " + unit, quantity) - b
    return a, b


def _unit_si(unit, quantity):
    """SI-waarde van 1 eenheid (positionunit/timeunit); 1 als leeg of
    onbekend."""
    unit = (unit or "").strip()
    if not unit:
        return 1.0
    v = parse_and_convert(u"1 " + unit, quantity)
    return v if isinstance(v, float) and v > 0.0 else 1.0


def _analysis_period(root):
    """Eindtijd van de analyse in s: <timesteps timeperiod> (zoals
    bridge_from_liml), anders 1 s."""
    ts = root.find("timesteps") if root is not None else None
    if ts is None:
        return 1.0
    period = parse_and_convert(ts.get("timeperiod", "1 s"), "time")
    return period if period > 0.0 else 1.0


def _reduce_samples(values, tol):
    """
    Indices van de punten die over: per stuk zo ver mogelijk vooruit
    (verdubbelen, dan halveren) zolang alle tussenliggende monsters
    hoogstens tol van de rechte lijn afliggen. Elk stuk wordt volledig
    gecontroleerd, dus de fout is overal <= tol (op de monsters).
    """
    n = len(values)

    def ok(i, j):
        vi, vj = values[i], values[j]
        span = float(j - i)
        for k in range(i + 1, j):
            if abs(values[k] - (vi + (vj - vi) * (k - i) / span)) > tol:
                return False
        return True

    keep = [0]
    i = 0
    while i < n - 1:
        good = i + 1
        step = 2
        bad = None
        while True:
            j = min(i + step, n - 1)
            if ok(i, j):
                good = j
                if j == n - 1:
                    break
                step *= 2
            else:
                bad = j
                break
        if bad is not None:
            lo, hi = good, bad
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if ok(i, mid):
                    lo = mid
                else:
                    hi = mid
            good = lo
        keep.append(good)
        i = good
    return keep


def _num(value):
    """Getal voor een FORMULE-uitdrukking: 17 significante cijfers (exact
    terug te lezen) met een decimale punt (%-opmaak volgt de landinstelling
    niet, zie bridge_mesh._real)."""
    txt = "%.17g" % value
    if "." in txt or "n" in txt:
        return txt
    mant, sep, exp = txt.partition("e")
    return mant + ".0" + sep + exp


class PositionFormula(object):
    """
    Mecway-formule in x, y, z (en eventueel t) als waarde van een
    mechanische last of voorwaarde (grenzen: KNOWN_BUGS 104). In de .comm
    een FORMULE van X, Y, Z en INST (bridge_to_aster._build_charges,
    AFFE_CHAR_MECA_F; catalogus affe_char_meca_f.py v17.4: PRES_REP PRES,
    FORCE_FACE, FORCE_ARETE, FORCE_COQUE, FORCE_POUTRE, FORCE_NODALE,
    DDL_IMPO en LIAISON_OBLIQUE nemen een formule), met X, Y, Z de
    beginpositie. Gemeten (Code-Aster 17.4, LS-40..44): volumevlakken,
    COQUE_3D en balken integreren de formule exact (integratiepunten),
    DKT neemt ze in de knopen; DDL_IMPO en FORCE_NODALE in de knopen.

    Waarde in SI = som over de termen van
        factor * (a * f(x/pu, y/pu, z/pu, t/tu) + b)
    plus offset, met (a, b) de eenheid van de uitkomst (_unit_map), pu/tu
    de SI-waarde van positionunit/timeunit (manual v33 par. 12.1) en
    factor/offset van de vertaling (bijv. 1/oppervlak, een teken, de som
    met een constante). Zo werken _scale, het delen door een oppervlak of
    een aantal knopen en optellen (bridge_to_aster._sum_values) zonder de
    formule te herschrijven. Geen float: float(f) geeft een TypeError, zodat
    code die een getal verwacht niet stil iets verkeerds schrijft.
    """

    def __init__(self, text, a, b, pu, tu, period, used):
        self.terms = [(text, a, b, pu, tu, 1.0)]
        self.offset = 0.0
        self.period = period          # eindtijd van de analyse (s)
        self.t_fixed = None           # t ingevuld (statisch: eindtijd)
        self.used = set(used)

    def _copy(self):
        new = PositionFormula.__new__(PositionFormula)
        new.__dict__.update(self.__dict__)
        new.terms = list(self.terms)
        new.used = set(self.used)
        return new

    def scaled(self, k):
        k = float(k)
        new = self._copy()
        new.terms = [(s, a, b, pu, tu, f * k)
                     for s, a, b, pu, tu, f in self.terms]
        new.offset = self.offset * k
        return new

    def __mul__(self, k):
        if isinstance(k, (int, float)) and not isinstance(k, bool):
            return self.scaled(k)
        return NotImplemented

    __rmul__ = __mul__

    def __div__(self, k):
        if isinstance(k, (int, float)) and not isinstance(k, bool):
            return self.scaled(1.0 / k)
        return NotImplemented

    __truediv__ = __div__

    def __neg__(self):
        return self.scaled(-1.0)

    def __add__(self, other):
        if isinstance(other, PositionFormula):
            new = self._copy()
            new.terms = self.terms + other.terms
            new.offset = self.offset + other.offset
            new.used = self.used | other.used
            new.period = max(self.period, other.period)
            return new
        if isinstance(other, (int, float)) and not isinstance(other, bool):
            new = self._copy()
            new.offset = self.offset + float(other)
            return new
        return NotImplemented

    __radd__ = __add__

    def timed(self):
        """True als de formule ook van t afhangt (en t niet is ingevuld)."""
        return "t" in self.used and self.t_fixed is None

    def at_end(self):
        """Kopie met t = eindtijd van de analyse (statische berekening,
        zoals een tijdshistorie in MECA_STATIQUE de laatste waarde krijgt)."""
        new = self._copy()
        if "t" in self.used:
            new.t_fixed = self.period
        return new

    def text(self):
        """Mecway-tekst (voor meldingen en het commentaar in de .comm)."""
        return " + ".join(t[0] for t in self.terms)

    def __repr__(self):
        return "PositionFormula({0!r})".format(self.text())

    def render(self):
        """(uitdrukking, NOM_PARA, {naam: argument}) voor FORMULE. INST
        alleen als t niet is ingevuld."""
        parts = []
        args = {}
        params = set()
        for text, a, b, pu, tu, f in self.terms:
            var = {}
            for v in ("x", "y", "z"):
                var[v] = "({0}/{1})".format(v.upper(), _num(pu))
            if self.t_fixed is None:
                var["t"] = "(INST/{0})".format(_num(tu))
            else:
                var["t"] = "({0})".format(_num(self.t_fixed / tu))
            expr, used, fargs = aster_expression(text, var)
            args.update(fargs)
            for v in used:
                if v in ("x", "y", "z"):
                    params.add(v.upper())
                elif self.t_fixed is None:
                    params.add("INST")
            parts.append("{0}*({1}*({2})+{3})".format(
                _num(f), _num(a), expr, _num(b)))
        if self.offset:
            parts.append(_num(self.offset))
        nom_para = [p for p in ("X", "Y", "Z", "INST") if p in params]
        if not nom_para:
            # Alleen t ingevuld: FORMULE vraagt minstens een parameter
            nom_para = ["X"]
        return " + ".join(parts), nom_para, args


def is_position(value):
    """True als value een PositionFormula is."""
    return isinstance(value, PositionFormula)


def _formula_value(node, quantity, root, allow_position=False):
    """
    SI-waarde van een formule-knoop: een float (formule zonder t), een
    lijst (t, waarde) over 0..eindtijd van de analyse, of (met
    allow_position) een PositionFormula voor een formule in x, y, z.
    FormulaError bij x/y/z zonder allow_position, een onleesbare formule of
    een rekenfout.
    """
    text = (node.text or "").strip()
    parser = _FormulaParser(text)
    try:
        fn = parser.parse()
    except ValueError as e:
        raise FormulaError(u"formule '{0}' niet te lezen ({1});",
                           u"formula '{0}' cannot be read ({1});", text, e)
    places = sorted(parser.used - set(["t"]))
    if places and not allow_position:
        raise FormulaError(
            u"formule '{0}' hangt af van de plaats ({1}); de bridge vertaalt "
            u"hier alleen formules in de tijd t;",
            u"formula '{0}' depends on position ({1}); the bridge only "
            u"translates formulas in time t here;", text, ", ".join(places))
    a, b = _unit_map(node.get("unit"), quantity)
    if places:
        if node.get("time") is not None:
            raise FormulaError(
                u"formule '{0}' in x, y, z als tabelwaarde (time-attribuut);",
                u"formula '{0}' in x, y, z as a table value (time "
                u"attribute);", text)
        pu = _unit_si(node.get("positionunit"), "length")
        tu = _unit_si(node.get("timeunit"), "time")
        log(u"INFO: Formule '{0}' hangt af van de plaats ({1}): FORMULE "
            u"van X, Y, Z{2} (positionunit {3}).".format(
                text, ", ".join(places),
                ", INST" if "t" in parser.used else "",
                node.get("positionunit") or "m"))
        return PositionFormula(text, a, b, pu, tu, _analysis_period(root),
                               parser.used)

    def value_at(t_formula, t_si):
        try:
            v = float(fn(t_formula))
        except (ValueError, ZeroDivisionError, OverflowError,
                TypeError) as e:
            raise FormulaError(
                u"formule '{0}' niet te berekenen bij t = {1} s ({2});",
                u"formula '{0}' cannot be evaluated at t = {1} s ({2});",
                text, t_si, e)
        if v != v or v in (float("inf"), float("-inf")):
            raise FormulaError(
                u"formule '{0}' geeft geen getal bij t = {1} s;",
                u"formula '{0}' gives no number at t = {1} s;", text, t_si)
        return a * v + b

    if "t" not in parser.used:
        return value_at(0.0, 0.0)
    if node.get("time") is not None:
        raise FormulaError(
            u"formule '{0}' in t als tabelwaarde (time-attribuut);",
            u"formula '{0}' in t as a table value (time attribute);", text)
    t_unit = parse_and_convert(u"1 " + (node.get("timeunit") or "s").strip(),
                               "time")
    if t_unit <= 0.0:
        t_unit = 1.0
    period = _analysis_period(root)
    times = [i * period / _FORMULA_SAMPLES
             for i in range(_FORMULA_SAMPLES + 1)]
    values = [value_at(t / t_unit, t) for t in times]
    vmin, vmax = min(values), max(values)
    if vmax - vmin <= 1.0e-12 * max(abs(vmin), abs(vmax)):
        log("INFO: Formule '{0}' is constant over 0..{1} s: {2}.".format(
            text, period, values[0]))
        return values[0]
    keep = _reduce_samples(values, _FORMULA_REL_TOL * (vmax - vmin))
    log("INFO: Formule '{0}' -> tijdshistorie met {1} punten over 0..{2} s "
        "(afwijking <= 0,01% van het bereik).".format(text, len(keep),
                                                      period))
    return [(times[k], values[k]) for k in keep]


# Mecway-functie -> naam in een Code-Aster-FORMULE (Python 3 in de job).
# heaviside en unittriangle bestaan niet in Python: de .comm definieert ze
# (ASTER_FORMULA_PRELUDE), met hetzelfde gedrag als _heaviside en
# _unittriangle hierboven (nagemeten in Mecway 33).
_ASTER_FUNCS = {
    "sin": "sin", "cos": "cos", "tan": "tan", "asin": "asin",
    "acos": "acos", "atan": "atan", "atan2": "atan2", "log": "log",
    "abs": "abs", "sqrt": "sqrt", "max": "max", "min": "min",
    "heaviside": "_mw_heaviside", "unittriangle": "_mw_unittriangle",
}
# Argumenten voor FORMULE(...): naam=object in de .comm. FORMULE rekent de
# uitdrukking met alleen de opgegeven argumenten en NOM_PARA (catalogus
# formule.py: "**args" als context), dus ook abs/max/min expliciet.
_ASTER_FUNC_ARGS = {
    "sin": "_mw_math.sin", "cos": "_mw_math.cos", "tan": "_mw_math.tan",
    "asin": "_mw_math.asin", "acos": "_mw_math.acos",
    "atan": "_mw_math.atan", "atan2": "_mw_math.atan2",
    "log": "_mw_math.log", "sqrt": "_mw_math.sqrt", "abs": "abs",
    "max": "max", "min": "min", "heaviside": "_mw_heaviside",
    "unittriangle": "_mw_unittriangle",
}
ASTER_FORMULA_PRELUDE = (
    "# Mecway-formules (bridge_bcs.aster_expression): hulpfuncties\n"
    "import math as _mw_math\n"
    "def _mw_heaviside(x):\n"
    "    return 1.0 if x > 0.0 else (0.0 if x < 0.0 else 0.5)\n"
    "def _mw_unittriangle(w, x):\n"
    "    if w <= 0.0:\n"
    "        raise ValueError('unittriangle: w <= 0')\n"
    "    return 0.0 if abs(x) >= 0.5 * w else (2.0 / w) * (1.0 - "
    "abs(x) / (0.5 * w))\n")


def aster_expression(text, variables):
    """
    Mecway-formule als Python-uitdrukking voor een Code-Aster-FORMULE.

    variables : {"x"|"y"|"z"|"t": uitdrukking} (bijv. "(X/0.001)"); een
                variabele die niet in de dict staat, geeft een ValueError.
    Returns (uitdrukking, gebruikte variabelen, {naam: argument} voor
    FORMULE). ValueError bij een onleesbare formule.
    De formule wordt eerst met _FormulaParser gecontroleerd; daarna per
    token omgezet: '^' -> '**' (Python: rechts-associatief en sterker dan
    het minteken, zoals Mecway: -2^2 = -4, 2^3^2 = 512), pi/e als getal,
    functies via _ASTER_FUNCS.
    """
    parser = _FormulaParser(text)
    parser.parse()
    out = []
    args = {}
    for kind, tok in _formula_tokens(text):
        if kind == "num":
            out.append(tok)
        elif kind == "op":
            out.append("**" if tok == "^" else tok)
        elif tok in _FORMULA_FUNCS:
            out.append(_ASTER_FUNCS[tok])
            args[_ASTER_FUNCS[tok]] = _ASTER_FUNC_ARGS[tok]
        elif tok in _FORMULA_CONSTS:
            out.append("%.17g" % _FORMULA_CONSTS[tok])
        elif tok in variables:
            out.append(variables[tok])
        else:
            raise ValueError(tr(u"variabele '{0}' kan hier niet",
                                u"variable '{0}' is not allowed here")
                             .format(tok))
    return " ".join(out), set(parser.used), args


def time_function(text):
    """f(t) van een Mecway-formule zonder x, y, z (ValueError anders)."""
    parser = _FormulaParser(text)
    fn = parser.parse()
    if parser.used - set(["t"]):
        raise ValueError(text)
    return fn


def _scalar(node, quantity):
    """Vaste SI-waarde van node (tekst met eenheid of formule zonder t);
    FormulaError bij een formule in t of x/y/z."""
    if node is None:
        return 0.0
    if not _is_formula(node):
        return parse_and_convert(node.text, quantity)
    value = _formula_value(node, quantity, None)
    if isinstance(value, list):
        raise FormulaError(
            u"formule '{0}' hangt af van de tijd; hier kan alleen een vaste "
            u"waarde;",
            u"formula '{0}' depends on time; only a fixed value is possible "
            u"here;", (node.text or "").strip())
    return value


def _skip_on_formula_error(parse_xml):
    """
    Decorator voor parse_xml: bij een FormulaError een ERROR en params =
    skipped_params van de klasse (geeft geen last; to_aster_dict -> {})
    plus "_skipped" = de omschrijving voor model_data["skipped_loads"].
    """
    def wrapper(self, item, root):
        try:
            return parse_xml(self, item, root)
        except FormulaError as e:
            sel = item.get("selection", "")
            what = tr(u"{0} op '{1}'", u"{0} on '{1}'").format(
                item.tag, sel) if sel else item.tag
            log(tr(u"ERROR: {0}: {1} NIET meegenomen.",
                   u"ERROR: {0}: {1} NOT included.").format(what, e.text()))
            params = dict(self.skipped_params)
            params["_skipped"] = what
            return params
    wrapper.__name__ = parse_xml.__name__
    wrapper.__doc__ = parse_xml.__doc__
    return wrapper


# ==========================================
# BASIS-KLASSE
# ==========================================
class BaseBC(object):
    aster_keyword = ""
    valid_targets = []
    # params van een last met een niet-vertaalbare formule
    # (_skip_on_formula_error): vorm zoals parse_xml, zonder werking.
    skipped_params = {}

    def parse_xml(self, item, root):
        raise NotImplementedError("Moet worden overschreven door subklasse")

    def to_aster_dict(self, params):
        raise NotImplementedError("Moet worden overschreven door subklasse")

    def keyword(self, params):
        """Code-Aster-sleutelwoord; kan per BC verschillen (schuine
        richting -> LIAISON_OBLIQUE)."""
        return self.aster_keyword


# ==========================================
# HULPFUNCTIES: WAARDE MET TIJDSHISTORIE, RICHTING
# ==========================================
def _parse_value_strict(item, tag, quantity, default, root=None,
                        allow_position=False):
    """
    Waarde van <tag>: een float, of een lijst (t, waarde) als er meerdere
    <tag time="..."> staan (bijv. <value time="5 s">90 deg</value>) of als
    de waarde een formule in t is (zie FORMULES hierboven; root geeft de
    eindtijd). De lijst wordt een DEFI_FONCTION in STAT_NON_LINE;
    MECA_STATIQUE neemt de laatste waarde (bridge_to_aster.py). Met
    allow_position wordt een formule in x, y, z een PositionFormula.
    FormulaError bij een formule die niet vertaald kan worden.
    """
    nodes = item.findall(tag)
    if not nodes:
        return default
    history = []
    static = default
    for node in nodes:
        if _is_formula(node):
            value = _formula_value(node, quantity, root, allow_position)
        else:
            value = parse_and_convert(node.text, quantity)
        if node.get("time") is not None:
            history.append((parse_and_convert(node.get("time"), "time"), value))
        else:
            static = value
    if history:
        history.sort(key=lambda tv: tv[0])
        return history
    return static


def _parse_value(item, tag, quantity, default, root=None):
    """Als _parse_value_strict, maar zonder FormulaError (voor
    bridge_from_liml, bijv. beginsnelheid): ERROR en default."""
    try:
        return _parse_value_strict(item, tag, quantity, default, root)
    except FormulaError as e:
        log(tr(u"ERROR: {0} op '{1}': {2} NIET meegenomen.",
               u"ERROR: {0} on '{1}': {2} NOT included.").format(
                   item.tag, item.get("selection", ""), e.text()))
        return default


def _scale(value, factor):
    """value (float of lijst (t, v)) maal factor."""
    if isinstance(value, list):
        return [(t, v * factor) for t, v in value]
    return value * factor


def _value_at(value, t):
    """Waarde van value (float of lijst (t, v)) op tijd t: lineair
    tussen de punten, constant buiten het bereik (zoals de DEFI_FONCTION
    van de bridge: PROL_GAUCHE/PROL_DROITE='CONSTANT')."""
    if not isinstance(value, list):
        return value
    if t <= value[0][0]:
        return value[0][1]
    for (t0, v0), (t1, v1) in zip(value, value[1:]):
        if t <= t1:
            if t1 == t0:
                return v1
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return value[-1][1]


def _gravity_history(history):
    """
    {"GRAVITE": [(t, g)], "DIRECTION": (dx, dy, dz)} voor een gravity met
    tijdshistorie (history: {as: float of lijst (t, waarde)}), of {} als de
    vector nul is of in de tijd van richting verandert (een PESANTEUR met
    FONC_MULT heeft een vaste DIRECTION). g heeft een teken (de vector is
    g * DIRECTION).
    """
    times = sorted(set(tv[0] for v in history.values()
                       if isinstance(v, list) for tv in v))
    vecs = [(t, [_value_at(history.get(ax, 0.0), t) for ax in "xyz"])
            for t in times]
    norms = [math.sqrt(sum(c * c for c in v)) for t, v in vecs]
    big = max(norms) if norms else 0.0
    if big < 1.0e-12:
        return {}
    ref = vecs[norms.index(big)][1]
    d = tuple(c / big for c in ref)
    out = []
    for t, v in vecs:
        s = sum(v[k] * d[k] for k in range(3))
        off = math.sqrt(sum((v[k] - s * d[k]) ** 2 for k in range(3)))
        if off > 1.0e-9 * big:
            return {}
        out.append((t, s))
    return {"GRAVITE": out, "DIRECTION": d}


def _parse_direction_strict(item):
    """Genormaliseerde richting uit <x>/<y>/<z>, of None bij nulvector.
    FormulaError bij een formule in t of x/y/z."""
    d = [_scalar(item.find(coord), "dimensionless")
         for coord in ("x", "y", "z")]
    n = math.sqrt(sum(c * c for c in d))
    if n < 1.0e-12:
        return None
    return tuple(c / n for c in d)


def _parse_direction(item):
    """Als _parse_direction_strict, maar zonder FormulaError (voor
    bridge_from_liml): ERROR en None (geen richting)."""
    try:
        return _parse_direction_strict(item)
    except FormulaError as e:
        log(tr(u"ERROR: {0} op '{1}': {2} NIET meegenomen.",
               u"ERROR: {0} on '{1}': {2} NOT included.").format(
                   item.tag, item.get("selection", ""), e.text()))
        return None


def _angl_naut(direction):
    """
    ANGL_NAUT (graden) waarvan de lokale x-as langs direction ligt.
    Code-Aster: lokale x = (cos a cos b, sin a cos b, -sin b) (U4.44.01,
    LIAISON_OBLIQUE; nautische hoeken zoals in AFFE_CARA_ELEM ORIENTATION).
    """
    dx, dy, dz = direction
    a = math.degrees(math.atan2(dy, dx))
    b = math.degrees(math.atan2(-dz, math.sqrt(dx * dx + dy * dy)))
    return (a, b, 0.0)


def _directional_dict(params, prefix):
    """
    Mecway zet de component van de verplaatsing (of rotatie) langs de
    richting op de waarde; loodrechte componenten blijven vrij (manual v33
    par. 9.6/9.7). Langs een as: DDL_IMPO D<as> (met teken). Schuin:
    LIAISON_OBLIQUE met de lokale x-as langs de richting.
    """
    d = params.get("dir")
    if d is None:
        return {}
    value = params.get("value", 0.0)
    for i, ax in enumerate("XYZ"):
        if abs(abs(d[i]) - 1.0) < 1.0e-12:
            return {"{0}{1}".format(prefix, ax): _scale(value, d[i])}
    return {"ANGL_NAUT": _angl_naut(d), "{0}X".format(prefix): value}


# ==========================================
# VASTE INKLEMMING  (tag: "fixed")
# Code-Aster: DDL_IMPO
#   - model zonder rotatie-DOFs (puur 3D): DX=DY=DZ=0
#   - model met rotatie-DOFs (balken/schalen/DIS_TR):
#       BLOCAGE=('DEPLACEMENT', 'ROTATION')
#     BLOCAGE is de opvolger van LIAISON='ENCASTRE' (code_aster
#     Cata/Commands/affe_char_meca.py, compat_syntax, v17.4.0) en blokkeert
#     per categorie de vrijheidsgraden van de knopen, zodat in een gemengd
#     model geen DRX/DRY/DRZ wordt opgelegd op 3D-knopen die deze niet hebben.
# Geldig op: GROUP_NO en GROUP_MA
#
# Opmerking: de "_has_rot_dofs"-vlag wordt NIET gelezen in parse_xml(),
# maar in to_aster_dict() via params.get("_has_rot_dofs", False).
# Deze vlag wordt door bridge_from_liml.py (en bridge_mesh.py bij
# toegevoegde DIS_TR-knopen) geinjecteerd na de parse_xml()-aanroep.
# ==========================================
class FixedBC(BaseBC):
    aster_keyword = "DDL_IMPO"
    valid_targets = ["GROUP_NO", "GROUP_MA"]

    def parse_xml(self, item, root):
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    def to_aster_dict(self, params):
        # "_has_rot_dofs" is geinjecteerd door bridge_from_liml.py / bridge_mesh.py;
        # GEEN globale variabele.
        if params.get("_has_rot_dofs", False):
            return {"BLOCAGE": ("DEPLACEMENT", "ROTATION")}
        return {"DX": 0.0, "DY": 0.0, "DZ": 0.0}


# ==========================================
# PINNED SUPPORT  (tag: "pinnedsupport")
# Code-Aster: DDL_IMPO met DX=DY=DZ=0 (geen rotatie-blokkering)
# Geldig op: GROUP_NO en GROUP_MA
#
# Een pinned support laat rotaties vrij: DRX/DRY/DRZ worden bewust
# NIET opgelegd, ongeacht het element-type.
# ==========================================
class PinnedBC(BaseBC):
    aster_keyword = "DDL_IMPO"
    valid_targets = ["GROUP_NO", "GROUP_MA"]

    def parse_xml(self, item, root):
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    def to_aster_dict(self, params):
        return {"DX": 0.0, "DY": 0.0, "DZ": 0.0}


# ==========================================
# OPGELEGDE VERPLAATSING  (tag: "displacement")
# Code-Aster: DDL_IMPO (richting langs een as) of LIAISON_OBLIQUE (schuin)
# Geldig op: GROUP_NO en GROUP_MA
#
# Mecway XML-structuur:
#   <value>      - waarde (met eenheid, bijv. "5 mm"); meerdere
#                  <value time="..."> geven een tijdshistorie
#   <x>/<y>/<z>  - richting (wordt genormaliseerd)
# De component langs de richting krijgt de waarde, de andere blijven vrij
# (manual v33 par. 9.6).
# ==========================================
class DisplacementBC(BaseBC):
    aster_keyword = "DDL_IMPO"
    valid_targets = ["GROUP_NO", "GROUP_MA"]
    quantity = "length"
    prefix = "D"
    skipped_params = {"value": 0.0, "dir": None}
    # waarde als formule in x, y, z: DDL_IMPO/LIAISON_OBLIQUE met een
    # FORMULE (PositionFormula); de richting moet vast zijn
    position_ok = True

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        return {"value": _parse_value_strict(item, "value", self.quantity,
                                             0.0, root, self.position_ok),
                "dir": _parse_direction_strict(item)}

    def to_aster_dict(self, params):
        return _directional_dict(params, self.prefix)

    def keyword(self, params):
        if "ANGL_NAUT" in self.to_aster_dict(params):
            return "LIAISON_OBLIQUE"
        return "DDL_IMPO"


# ==========================================
# OPGELEGDE ROTATIE  (tag: "noderotation")
# Code-Aster: DDL_IMPO DRX/DRY/DRZ of LIAISON_OBLIQUE
# Geldig op: GROUP_NO en GROUP_MA
#
# Alleen voor knopen met rotatie-DOFs (balk, schaal); op 3D-knopen geeft
# Code-Aster een fout. Zelfde XML als displacement, eenheid 'angle'
# (rad, of deg/° -> rad), richting = rotatie-as (manual v33 par. 9.7).
# ==========================================
class NodeRotationBC(DisplacementBC):
    quantity = "angle"
    prefix = "DR"


# ==========================================
# KRACHT  (tag: "force")
# Code-Aster: FORCE_NODALE met FX/FY/FZ op knopen; op vlakken FORCE_FACE,
# FORCE_COQUE of FORCE_ARETE (bridge_mesh._apply_to_model_data).
# Geldig op: GROUP_NO en GROUP_MA
#
# BELANGRIJK: de verdeling gebeurt BUITEN deze klasse: over de knopen van
# een nodeselection in bridge_from_liml.py, over de knopen van
# balkuiteinden en over het oppervlak/de lengte van vlakken in
# bridge_mesh.py. parse_xml() geeft hier de ongecorrigeerde TOTALE kracht
# per as terug (SI, Newton).
#
# Tijdshistorie:
#   Mecway kan een kracht per tijdsstap geven via meerdere <x>/<y>/<z>
#   elementen met een time-attribuut, bijv.:
#     <x time="0 s">0 N</x>
#     <x time="1 s">1500 N</x>
#     <x time="2 s">2000 N</x>
#   parse_xml() geeft dan params[axis] terug als lijst van (t, F)-tuples
#   in SI-eenheden. Als er geen time-attribuut staat, blijft params[axis]
#   een float (statische kracht). Als zowel statische als tijdsstappen
#   aanwezig zijn voor dezelfde as, krijgt de tijdshistorie voorrang.
#
#   MECA_STATIQUE-builder collapsed de lijst naar de laatste waarde en
#   logt een waarschuwing. STAT_NON_LINE-builder genereert een
#   DEFI_FONCTION en gebruikt AFFE_CHAR_MECA_F.
# ==========================================
class ForceBC(BaseBC):
    # Op knopen: FORCE_NODALE, gelijk verdeeld over de knopen. Op vlakken:
    # FORCE_FACE; Mecway verdeelt de totale kracht gelijkmatig over het
    # oppervlak (manual v33 par. 9.13), dus bridge_mesh.py deelt door het
    # oppervlak van de vlakgroep en zet aster_keyword op FORCE_FACE.
    aster_keyword = "FORCE_NODALE"
    valid_targets = ["GROUP_NO", "GROUP_MA"]

    quantity = "force"
    prefix = "F"
    # componenten als formule in x, y, z (PositionFormula): kracht,
    # traction, line pressure; niet bij een moment (MomentBC)
    position_ok = True

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        params = {}
        for coord in ['x', 'y', 'z']:
            value = _parse_value_strict(item, coord, self.quantity, None,
                                        root, self.position_ok)
            if value is not None:
                params[coord] = value
        return params

    def to_aster_dict(self, params):
        # Pass-through: waarden kunnen scalar zijn (lineair-statisch) of
        # lijsten van (t, F) (niet-lineair-statisch). De rendering in
        # bridge_to_aster.py beslist op basis van het type.
        return {"{0}{1}".format(self.prefix, ax.upper()): v
                for ax, v in params.items()
                if not ax.startswith("_")}


# ==========================================
# MOMENT  (tag: "moment")
# Mecway (manual v33 par. 9.18): op een enkele knoop met rotatie-DOFs
# (balk/schaal) -> FORCE_NODALE MX/MY/MZ; op vlakken (schaal of volume)
# als krachten verdeeld over de vlakken, om de as door het zwaartepunt.
# De verdeling over vlakken doet bridge_mesh.py (_moment_to_forces).
# XML: <moment selection="..."><x>2 N.m</x><y>..</y><z>..</z></moment>,
# per component eventueel met time-attributen (zoals force).
# ==========================================
class MomentBC(ForceBC):
    quantity = "moment"
    prefix = "M"
    # verdeling over de vlakken met vaste knoopkrachten
    # (bridge_mesh._moment_to_forces): geen formule in x, y, z
    position_ok = False


# ==========================================
# GRAVITY  (tag: "gravity")
# Code-Aster: PESANTEUR met GRAVITE=|g| en DIRECTION=(dx,dy,dz)
# Geldig op: globaal (geen GROUP_MA in deze implementatie).
#
# Mecway XML-structuur:
#   <gravity>
#     <x>0 m/s2</x>
#     <y>0 m/s2</y>
#     <z>-9.81 m/s2</z>
#   </gravity>
#
# Code-Aster verwacht de zwaartekrachtvector ontbonden in:
#   GRAVITE   = magnitude |g| = sqrt(gx^2 + gy^2 + gz^2)   [m/s^2]
#   DIRECTION = genormaliseerde richting (gx/|g|, gy/|g|, gz/|g|)
#
# RHO komt uit DEFI_MATERIAU (bridge_to_aster.py voegt RHO toe in ELAS).
# Materialen zonder dichtheid krijgen RHO=0 en leveren geen
# zwaartekrachtbijdrage; Code-Aster geeft geen alarm in dat geval.
#
# BELANGRIJK: <gravity> in de .liml heeft GEEN selection-attribuut.
# bridge_from_liml.py geeft selection_name="" door; bridge_to_aster.py
# detecteert dit en laat de GROUP_MA-prefix weg in de _F(...) entry.
#
# valid_targets blijft ["GROUP_MA"] voor consistentie met de
# bestaande target-validatie in bridge_from_liml.py (lege selection
# valt automatisch op GROUP_MA). De daadwerkelijke render schrijft
# geen GROUP_MA wanneer de selection leeg is.
#
# Tijdshistorie (Samples/SaggingCable.liml, Mecway manual v33 par. 9.19
# "constant or time-dependent"), per component zoals bij force:
#   <y time="1 s">0 m/s²</y>
#   <y time="2 s">-9.8 m/s²</y>
# parse_xml() zet dan in params["_history"] per component een float of een
# lijst (t, g) en in params x/y/z de waarde op de laatste tijd (voor
# gebruikers die een vaste vector verwachten, bijv. hydrostatische druk).
# to_aster_dict() maakt er GRAVITE = [(t, g(t))] (met teken) langs een vaste
# DIRECTION van; Code-Aster: PESANTEUR in AFFE_CHAR_MECA (niet in
# AFFE_CHAR_MECA_F, catalogus affe_char_meca.py) met FONC_MULT in EXCIT,
# zoals testcase forma12b (PESANTEUR met EXCIT FONC_MULT). Draait de
# richting in de tijd, dan geeft to_aster_dict() {} (niet te vertalen met
# een functie; bridge_from_liml meldt dat).
# ==========================================
class GravityBC(BaseBC):
    aster_keyword = "PESANTEUR"
    valid_targets = ["GROUP_MA"]

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        params = {}
        history = {}
        for coord in ['x', 'y', 'z']:
            value = _parse_value_strict(item, coord, 'acceleration', None,
                                        root)
            if value is not None:
                history[coord] = value
        if not any(isinstance(v, list) for v in history.values()):
            return history
        t_last = max(tv[0] for v in history.values()
                     if isinstance(v, list) for tv in v)
        for coord, value in history.items():
            params[coord] = _value_at(value, t_last)
        params["_history"] = history
        return params

    def to_aster_dict(self, params):
        if params.get("_history"):
            return _gravity_history(params["_history"])
        gx = params.get('x', 0.0)
        gy = params.get('y', 0.0)
        gz = params.get('z', 0.0)
        g  = math.sqrt(gx * gx + gy * gy + gz * gz)

        if g < 1.0e-12:
            # Volledig nul-vector: signaleer voor de aanroeper dat dit
            # een no-op is. bridge_from_liml.py filtert een nul-vector al
            # vooraf; bridge_to_aster.py slaat een lege aster_dict over.
            return {}

        return {
            "GRAVITE":   g,
            "DIRECTION": (gx / g, gy / g, gz / g),
        }


# ==========================================
# OPPERVLAKTEDRUK  (tag: "surfacepressure")
# Code-Aster: PRES_REP met PRES=
# Geldig op: GROUP_MA UITSLUITEND
#
# Conventie: PRES > 0 = compressief (naar het oppervlak toe gedrukt).
# Code-Aster berekent zelf de krachtvectoren via de oppervlaktenormaal.
# ==========================================
class SurfacePressureBC(BaseBC):
    aster_keyword = "PRES_REP"
    valid_targets = ["GROUP_MA"]
    skipped_params = {"PRES": 0.0}

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        if item.find("normal") is not None:
            pres_val = _parse_value_strict(item, "normal", "pressure", 0.0,
                                           root, allow_position=True)
        else:
            pres_val = parse_and_convert(item.get("normal", "0"), 'pressure')
        return {"PRES": pres_val}

    def to_aster_dict(self, params):
        if params.get("_skipped"):
            return {}
        # _sign: -1 voor schaalvlakken met faceid 6 (bridge_mesh.py)
        return {"PRES": _scale(params["PRES"], params.get("_sign", 1.0))}


# ==========================================
# OPGELEGDE SNELHEID  (tag: "velocity")
# Mecway (manual v33 par. 9.8): zet de component van de snelheid langs de
# richting; alleen bij dynamische analyses. Code-Aster legt in
# DYNA_NON_LINE geen snelheid op, wel een verplaatsing als functie van de
# tijd: u(t) = integraal van v (bij constante v: v*t). De eindtijd komt
# uit <timesteps> (params["_t_end"], gezet door bridge_from_liml.py).
# ==========================================
class VelocityBC(DisplacementBC):
    quantity = "velocity"
    prefix = "D"
    # de snelheid wordt in de tijd geintegreerd (_integrate): alleen
    # getallen en tijdshistories
    position_ok = False

    def to_aster_dict(self, params):
        p = dict(params)
        p["value"] = _integrate(params.get("value", 0.0),
                                params.get("_t_end", 1.0))
        return _directional_dict(p, self.prefix)

    def keyword(self, params):
        return DisplacementBC.keyword(self, dict(params, value=0.0))


def _integrate(value, t_end):
    """Verplaatsingshistorie [(t, u)] bij snelheid value (float of
    [(t, v)], lineair tussen de punten, constant erbuiten), van 0 tot
    t_end."""
    if not isinstance(value, list):
        return [(0.0, 0.0), (t_end, value * t_end)]
    pts = sorted(value)
    times = sorted(set([0.0, t_end] + [t for t, v in pts
                                       if 0.0 < t < t_end]))

    def v_at(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, v0), (t1, v1) in zip(pts[:-1], pts[1:]):
            if t <= t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0) if t1 > t0 \
                    else v1
        return pts[-1][1]

    out = [(0.0, 0.0)]
    u = 0.0
    for t0, t1 in zip(times[:-1], times[1:]):
        u += 0.5 * (v_at(t0) + v_at(t1)) * (t1 - t0)
        out.append((t1, u))
    return out


# ==========================================
# FRICTIONLESS SUPPORT  (tag: "frictionless")
# Mecway (manual v33 par. 9.2): normaalverplaatsing van de vlakken nul (of
# <displacement>, positief = het vlak in); in een knoop de gemiddelde
# normaal van de aangrenzende vlakken uit de selectie. Op schalen ook de
# rotaties om de assen in het vlak.
# Code-Aster: FACE_IMPO DNOR op de randelementen van volume-elementen
# (DNOR langs de naar buiten gerichte normaal na ORIE_PEAU, dus -waarde);
# vlakke schaalvlakken via bridge_mesh.py als LIAISON_OBLIQUE.
# ==========================================
class FrictionlessBC(BaseBC):
    aster_keyword = "FACE_IMPO"
    valid_targets = ["GROUP_MA"]

    skipped_params = {"value": 0.0}

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        return {"value": _parse_value_strict(item, "displacement", "length",
                                             0.0, root)}

    def to_aster_dict(self, params):
        if params.get("_skipped"):
            return {}
        value = _scale(params.get("value", 0.0), -1.0)
        if "_normal" in params:
            # vlakke schaalvlakken (bridge_mesh._frictionless)
            return OrderedDict([("ANGL_NAUT", _angl_naut(params["_normal"])),
                                ("DX", value), ("DRY", 0.0), ("DRZ", 0.0)])
        return {"DNOR": value}

    def keyword(self, params):
        return "LIAISON_OBLIQUE" if "_normal" in params else "FACE_IMPO"


# ==========================================
# TRACTION  (tag: "traction")
# Mecway (manual v33 par. 9.15): kracht per oppervlak in globale X/Y/Z, op
# vlakken of elementen; per component eventueel een tijdshistorie.
#   <traction selection=".."><x>1 MPa</x><y>2 MPa</y><z>3 MPa</z></traction>
# Code-Aster: FORCE_FACE (vlakken van volume-elementen) of FORCE_COQUE
# (schalen; PLAN volgt de kant, zie bridge_mesh._traction). De keuze maakt
# bridge_mesh.py; hier alleen de componenten.
# ==========================================
class TractionBC(ForceBC):
    aster_keyword = "FORCE_FACE"
    valid_targets = ["GROUP_MA"]
    quantity = "pressure"


# ==========================================
# LINE PRESSURE  (tag: "linepressure")
# Mecway (manual v33 par. 9.16): kracht per lengte op line2/line3-elementen
# of op lokaal 1D-vlakken (schaalranden), globaal X/Y/Z.
#   <linepressure selection=".."><x>0 N/m</x><y>10 N/m</y><z>-20 N/m</z>
# Code-Aster: FORCE_POUTRE FX/FY/FZ (balken) of FORCE_ARETE (schaalranden),
# beide kracht per lengte in het globale assenstelsel (U4.44.01).
# Elementcoordinaten (alleen balken): <u>/<v>/<w> i.p.v. <x>/<y>/<z>
# (XML gezien in Mecway 33) -> FORCE_POUTRE N/VY/VZ in het lokale stelsel;
# Code-Aster lokaal y/z = Mecway V/W (zie bridge_from_liml.py, profielen).
# ==========================================
class LinePressureBC(ForceBC):
    aster_keyword = "FORCE_POUTRE"
    valid_targets = ["GROUP_MA"]
    quantity = "line_load"
    _LOCAL = OrderedDict([("u", "N"), ("v", "VY"), ("w", "VZ")])

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        local = OrderedDict()
        for coord in self._LOCAL:
            value = _parse_value_strict(item, coord, self.quantity, None,
                                        root, self.position_ok)
            if value is not None:
                local[coord] = value
        if local:
            local["_local"] = True
            return local
        return ForceBC.parse_xml(self, item, root)

    def to_aster_dict(self, params):
        if params.get("_local"):
            return OrderedDict((self._LOCAL[ax], v)
                               for ax, v in params.items()
                               if ax in self._LOCAL)
        return ForceBC.to_aster_dict(self, params)


# ==========================================
# HYDROSTATISCHE DRUK  (tag: "hydrostaticpressure")
# Mecway (manual v33 par. 9.17): druk = rho * g * diepte onder het vrije
# oppervlak (punt <x>/<y>/<z>), nul erboven; vraagt een aparte gravity.
#   <hydrostaticpressure selection=".."><fluiddensity>1000 kg/m3
#   </fluiddensity><x>0 mm</x><y>0 mm</y><z>30 mm</z></hydrostaticpressure>
# Code-Aster: AFFE_CHAR_MECA_F PRES_REP met een FORMULE van X, Y, Z
# (U4.44.01 PRES_REP, "function" pressure). De formule maakt
# bridge_to_aster.py met de zwaartekrachtvector (_hydrostatic_formula).
# ==========================================
class HydrostaticPressureBC(BaseBC):
    aster_keyword = "PRES_REP"
    valid_targets = ["GROUP_MA"]

    skipped_params = {"rho": 0.0, "point": (0.0, 0.0, 0.0)}

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        point = [_scalar(item.find(coord), "length")
                 for coord in ("x", "y", "z")]
        return {"rho": _scalar(item.find("fluiddensity"), "density"),
                "point": tuple(point)}

    def to_aster_dict(self, params):
        if params.get("_skipped"):
            return {}
        # De PRES-functie komt pas in bridge_to_aster.py (_build_charges).
        return {"PRES": params.get("_formula", "")}


# ==========================================
# ELASTIC SUPPORT  (tag: "elasticsupport")
# Mecway (manual v33 par. 9.4): stijfheid per oppervlak, normaal en
# tangentieel, op vlakken van volume-elementen en schaalvlakken.
#   <elasticsupport selection=".."><modulus>1E12 Pa/m</modulus>
#   <tangential>2E11 Pa/m</tangential></elasticsupport>
# Code-Aster: een veer naar de grond per knoop (POI1, DIS_T, K_T_N), met
# stijfheid = k * knoopgewicht van het oppervlak; bridge_mesh.py maakt de
# elementen (_build_discretes).
# ==========================================
class ElasticSupportBC(BaseBC):
    aster_keyword = "DISCRET"
    valid_targets = ["GROUP_MA"]

    skipped_params = {"kn": 0.0, "kt": 0.0}

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        return {"kn": _scalar(item.find("modulus"), "stiffness_per_area"),
                "kt": _scalar(item.find("tangential"), "stiffness_per_area")}

    def to_aster_dict(self, params):
        return {}


# ==========================================
# COMPRESSION ONLY SUPPORT  (tag: "compressiononly")
# Mecway (manual v33 par. 9.5): als frictionless waar de steun op druk
# belast wordt, vrij waar hij op trek zou komen. De interne solver rekent
# hard; <stiffness> en <tensilestress> zijn alleen voor CCX (veren) en
# worden niet gelezen.
# Code-Aster: DEFI_CONTACT FORMULATION='LIAISON_UNIL' (U4.44.11 par. 3.8):
# per knoop n . u <= 0, met n de naar buiten gerichte normaal (naar de
# steun). Alleen in STAT_NON_LINE/DYNA_NON_LINE. bridge_mesh.py
# groepeert de knopen per normaal (_compression_only).
# ==========================================
class CompressionOnlyBC(BaseBC):
    aster_keyword = "LIAISON_UNIL"
    valid_targets = ["GROUP_MA"]

    def parse_xml(self, item, root):
        return {}

    def to_aster_dict(self, params):
        return {}


# ==========================================
# SYMMETRY  (tag: "symmetry")
# Mecway (manual v33 par. 9.40): verplaatsing loodrecht op het
# symmetrievlak nul; rotaties om assen in het vlak nul (balkuiteinden),
# op schaalranden alleen de rotatie om de rand. nodeplane="true": het vlak
# volgt uit de knopen, anders normaal <x>/<y>/<z>.
# Code-Aster: LIAISON_OBLIQUE met de lokale x-as langs de normaal
# (bridge_mesh._symmetry zet richting en groepen).
# ==========================================
class SymmetryBC(BaseBC):
    aster_keyword = "LIAISON_OBLIQUE"
    valid_targets = ["GROUP_MA", "GROUP_NO"]

    skipped_params = {"nodeplane": False, "dir": None}

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        return {"nodeplane": item.get("nodeplane", "") == "true",
                "dir": _parse_direction_strict(item)}

    def to_aster_dict(self, params):
        return {}


# ==========================================
# CENTRIFUGAL FORCE  (tag: "centrifugal")
# Mecway (manual v33 par. 9.20): rotatie om de globale X-, Y- of Z-as door
# de oorsprong, F = m w^2 r op alle massa (elementen met dichtheid en
# knoopmassa's).
#   <centrifugal><x>0 rad/s</x><y>100000 r/min</y><z>0 rad/s</z>
# Code-Aster: AFFE_CHAR_MECA ROTATION=_F(VITESSE, AXE, CENTRE) (U4.44.01;
# catalogus affe_char_meca.py v17.4: VITESSE, AXE verplicht). VITESSE in
# rad/s: NIET in de documentatie gevonden, nagerekend met een run (zie
# bridge_to_aster._build_charges). Knoopmassa's (DIS_T) krijgen de kracht
# apart (bridge_to_aster._centrifugal_loads).
# ==========================================
class CentrifugalBC(BaseBC):
    aster_keyword = "ROTATION"
    valid_targets = ["GROUP_MA"]

    @_skip_on_formula_error
    def parse_xml(self, item, root):
        params = {}
        for coord in ("x", "y", "z"):
            value = _parse_value_strict(item, coord, "angular_velocity",
                                        None, root)
            if value is not None:
                params[coord] = value
        return params

    def to_aster_dict(self, params):
        """VITESSE en AXE, of {} als de as geen X, Y of Z is (of nul) of
        als er een tijdshistorie is (bridge_from_liml.py meldt dat)."""
        comps = [(i, params.get(c, 0.0)) for i, c in enumerate("xyz")]
        if any(isinstance(v, list) for _, v in comps):
            return {}
        nonzero = [(i, v) for i, v in comps if v != 0.0]
        if len(nonzero) != 1:
            return {}
        i, w = nonzero[0]
        axis = [0.0, 0.0, 0.0]
        axis[i] = 1.0
        return OrderedDict([("VITESSE", abs(w)), ("AXE", tuple(axis)),
                            ("CENTRE", (0.0, 0.0, 0.0))])


# ==========================================
# BC-REGISTER
# ==========================================
SUPPORTED_BCS = {
    "fixed":           FixedBC(),
    "displacement":    DisplacementBC(),
    "force":           ForceBC(),
    "surfacepressure": SurfacePressureBC(),
    "pinnedsupport":   PinnedBC(),
    "noderotation":    NodeRotationBC(),
    "gravity":         GravityBC(),
    "moment":          MomentBC(),
    "frictionless":    FrictionlessBC(),
    "velocity":        VelocityBC(),
    "traction":        TractionBC(),
    "linepressure":    LinePressureBC(),
    "hydrostaticpressure": HydrostaticPressureBC(),
    "elasticsupport":  ElasticSupportBC(),
    "compressiononly": CompressionOnlyBC(),
    "symmetry":        SymmetryBC(),
    "centrifugal":     CentrifugalBC(),
}
