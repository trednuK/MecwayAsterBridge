# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_bcs.py
# Defines the BC classes (boundary conditions / loads) and the SUPPORTED_BCS registry.
#
# Every BC type inherits from BaseBC and implements two methods:
#   parse_xml()     - reads parameters from the Mecway .liml XML element
#   to_aster_dict() - translates the parameters to the Code-Aster keyword format
#
# Separating parse_xml() and to_aster_dict() makes it possible to do
# intermediate steps (e.g. distributing forces over nodes, injecting
# model-level flags) before the final Code-Aster syntax is generated.
#
# Internal metadata keys in params (prefix "_") are injected by bridge_from_liml.py
# (and possibly bridge_mesh.py) AFTER the parse_xml() call. This way the
# BC classes themselves need no knowledge of the whole model.
# Example: "_has_rot_dofs" decides in FixedBC.to_aster_dict() whether the
# clamping becomes DX=DY=DZ=0 or BLOCAGE=('DEPLACEMENT', 'ROTATION').
#
# Compatible with IronPython 2.7.9.

import math
import re
from collections import OrderedDict
from bridge_utils import log, parse_and_convert, tr


# ==========================================
# FORMULAS AS VALUE
# Mecway writes a formula without a unit in the text; the units are
# attributes (manual v33 par. 12.1: "in the case of formulas, appear as
# separate XML attributes"), e.g. Samples/PipeClip.liml:
#   <value unit="mm" timeunit="s" positionunit="mm">-12*t</value>
# unit = unit of the result, timeunit = unit of t, positionunit =
# unit of x, y, z. A formula in t is a time history (manual par. 9:
# "a Formula with the variable t ... evaluated at each time step").
#
# Language (Formula Help window of Mecway 33, texts in mecway.exe):
# + - * / ^ ( ), pi, e, sin, cos, tan, asin, acos, atan, atan2(y,x), log,
# abs, sqrt, heaviside(x), unittriangle(w,x), max(x,y), min(x,y).
# Verified with Mecway 33 (headless, force as formula on a bar of
# 2 hex8, nonlinear static with CCX and dynamic with the internal solver):
#   log = natural logarithm (log(10) = 2.3026); heaviside(0) = 0.5;
#   unittriangle(w,x) = triangle with base w around x = 0 and area 1
#   (peak 2/w); -2^2 = -4 (^ binds tighter than unary minus); 2^3^2 = 512
#   (^ right to left); sin in radians; timeunit "min" is
#   applied (t in minutes); t starts at 0 s.
# Linear static (measured): the internal solver ignores a load in t
# (also a table; displacement 0), CCX takes the formula at t = 0 and a
# table at t = 1. In MECA_STATIQUE the bridge takes, as with a table,
# the last value (bridge_to_aster, with WARNING).
#
# Mecway samples a formula for CCX and OpenRadioss at 10001 equal
# times and keeps the points with which the piecewise linear function
# deviates at most 0.01% of the range (manual par. 9). The bridge does
# the same over 0..timeperiod (<timesteps>; without: 1 s, as in
# bridge_from_liml). A formula without t is an ordinary value.
#
# Formulas in x, y, z (position dependent, possibly also with t): a
# PositionFormula (below), in the .comm a FORMULE of X, Y, Z (and INST)
# in AFFE_CHAR_MECA_F (bridge_to_aster._build_charges). Only for the
# loads with position_ok = True (pressure, traction, force, line pressure,
# imposed displacement and rotation); elsewhere it stays a FormulaError.
# Measured with Mecway 34 (headless, mw_solve.py, block 1 x 2 x 0.1 m of
# hex8 with the bottom fixed, internal solver and CCX):
#   - pressure 3*y^2 kPa (positionunit m) on the top: reaction 8000 N and
#     moment 12000 N.m, exact (integral); with positionunit mm and
#     3e-6*y^2 the same, so x, y, z in positionunit;
#   - traction x = 2*x+1, z = y^3 kPa: reactions -4000 N and -4000 N
#     (exact), moment -6399.96 N.m (exact -6400: Mecway samples per
#     face, manual par. 9.14: 1, 7 or 9 points);
#   - force (on faces and on nodes), imposed displacement/rotation and
#     line pressure with x, y or z in the formula (also 1000*(1+y)): Mecway
#     imposes NOTHING (reactions and displacements 0), with the internal
#     solver and with CCX (also nonlinear); gravity with x in the formula
#     and a direction vector as formula: Mecway does not solve (no solution);
#   - pressure 3*y^2*t with CCX (nonlinear): solves (displacement
#     proportional to t; the restriction "not ... both time and position"
#     in the manual is for the thermal loads, par. 9.23 ff.).
# The bridge still translates the position-dependent force, displacement
# and line pressure (the intent of the formula) and reports the difference
# with Mecway (WARNING, bridge_from_liml._check_position_formulas).
# ==========================================
_FORMULA_ATTRS = ("unit", "timeunit", "positionunit")
_FORMULA_SAMPLES = 10000          # intervals: 10001 times (Mecway)
_FORMULA_REL_TOL = 1.0e-4         # 0.01% of the range (Mecway)


class FormulaError(ValueError):
    """Formula that cannot be translated. The text (NL and EN, with
    the same placeholders) ends with ';' and fits in the message
    "ERROR: <load>: <text> NIET meegenomen." (as in
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
    # math.pow raises ValueError for a negative base with a
    # fractional exponent (CPython 3: ** would give a complex number).
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
    """[(kind, text)] with kind 'num', 'name' or 'op'."""
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
    Recursive descent; returns a function f(t) (closures, no eval) and the
    variables used. Grammar (see the measurements above):
      expr   := term (('+' | '-') term)*
      term   := unary (('*' | '/') unary)*
      unary  := ('-' | '+') unary | power
      power  := atom ('^' unary)?        (right-associative)
      atom   := number | name | name '(' expr (',' expr)* ')' | '(' expr ')'
    x, y and z are recognised as variables (for the message), but not
    evaluated.
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
    """True if the value of node is a Mecway formula (units as
    attributes)."""
    return any(node.get(a) is not None for a in _FORMULA_ATTRS)


def _unit_map(unit, quantity):
    """(a, b) with SI = a * value + b for the unit unit (via
    parse_and_convert; also an offset such as degC)."""
    unit = (unit or "").strip()
    b = parse_and_convert(u"0 " + unit, quantity)
    a = parse_and_convert(u"1 " + unit, quantity) - b
    return a, b


def _unit_si(unit, quantity):
    """SI value of 1 unit (positionunit/timeunit); 1 if empty or
    unknown."""
    unit = (unit or "").strip()
    if not unit:
        return 1.0
    v = parse_and_convert(u"1 " + unit, quantity)
    return v if isinstance(v, float) and v > 0.0 else 1.0


def _analysis_period(root):
    """End time of the analysis in s: <timesteps timeperiod> (as in
    bridge_from_liml), otherwise 1 s."""
    ts = root.find("timesteps") if root is not None else None
    if ts is None:
        return 1.0
    period = parse_and_convert(ts.get("timeperiod", "1 s"), "time")
    return period if period > 0.0 else 1.0


def _reduce_samples(values, tol):
    """
    Indices of the points to keep: per piece advance as far as possible
    (doubling, then halving) as long as all intermediate samples are
    at most tol away from the straight line. Every piece is fully
    checked, so the error is <= tol everywhere (at the samples).
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
    """Number for a FORMULE expression: 17 significant digits (exactly
    readable back) with a decimal point (%-formatting does not follow the
    locale, see bridge_mesh._real)."""
    txt = "%.17g" % value
    if "." in txt or "n" in txt:
        return txt
    mant, sep, exp = txt.partition("e")
    return mant + ".0" + sep + exp


class PositionFormula(object):
    """
    Mecway formula in x, y, z (and possibly t) as the value of a
    mechanical load or condition (limits: KNOWN_BUGS 104). In the .comm
    a FORMULE of X, Y, Z and INST (bridge_to_aster._build_charges,
    AFFE_CHAR_MECA_F; catalogue affe_char_meca_f.py v17.4: PRES_REP PRES,
    FORCE_FACE, FORCE_ARETE, FORCE_COQUE, FORCE_POUTRE, FORCE_NODALE,
    DDL_IMPO and LIAISON_OBLIQUE accept a formula), with X, Y, Z the
    initial position. Measured (Code-Aster 17.4, LS-40..44): volume faces,
    COQUE_3D and beams integrate the formula exactly (integration points),
    DKT takes it at the nodes; DDL_IMPO and FORCE_NODALE at the nodes.

    Value in SI = sum over the terms of
        factor * (a * f(x/pu, y/pu, z/pu, t/tu) + b)
    plus offset, with (a, b) the unit of the result (_unit_map), pu/tu
    the SI value of positionunit/timeunit (manual v33 par. 12.1) and
    factor/offset from the translation (e.g. 1/area, a sign, the sum
    with a constant). This way _scale, dividing by an area or
    a number of nodes and adding (bridge_to_aster._sum_values) work without
    rewriting the formula. Not a float: float(f) raises a TypeError, so that
    code expecting a number does not silently write something wrong.
    """

    def __init__(self, text, a, b, pu, tu, period, used):
        self.terms = [(text, a, b, pu, tu, 1.0)]
        self.offset = 0.0
        self.period = period          # end time of the analysis (s)
        self.t_fixed = None           # t filled in (static: end time)
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
        """True if the formula also depends on t (and t is not filled in)."""
        return "t" in self.used and self.t_fixed is None

    def at_end(self):
        """Copy with t = end time of the analysis (static analysis,
        as a time history in MECA_STATIQUE gets the last value)."""
        new = self._copy()
        if "t" in self.used:
            new.t_fixed = self.period
        return new

    def text(self):
        """Mecway text (for messages and the comment in the .comm)."""
        return " + ".join(t[0] for t in self.terms)

    def __repr__(self):
        return "PositionFormula({0!r})".format(self.text())

    def render(self):
        """(expression, NOM_PARA, {name: argument}) for FORMULE. INST
        only if t is not filled in."""
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
            # Only t filled in: FORMULE needs at least one parameter
            nom_para = ["X"]
        return " + ".join(parts), nom_para, args


def is_position(value):
    """True if value is a PositionFormula."""
    return isinstance(value, PositionFormula)


def _formula_value(node, quantity, root, allow_position=False):
    """
    SI value of a formula node: a float (formula without t), a
    list (t, value) over 0..end time of the analysis, or (with
    allow_position) a PositionFormula for a formula in x, y, z.
    FormulaError for x/y/z without allow_position, an unreadable formula or
    a calculation error.
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
        log(u"INFO: Formula '{0}' depends on the position ({1}): FORMULE "
            u"of X, Y, Z{2} (positionunit {3}).".format(
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
        log("INFO: Formula '{0}' is constant over 0..{1} s: {2}.".format(
            text, period, values[0]))
        return values[0]
    keep = _reduce_samples(values, _FORMULA_REL_TOL * (vmax - vmin))
    log("INFO: Formula '{0}' -> time history with {1} points over 0..{2} s "
        "(deviation <= 0.01% of the range).".format(text, len(keep),
                                                      period))
    return [(times[k], values[k]) for k in keep]


# Mecway function -> name in a Code-Aster FORMULE (Python 3 in the job).
# heaviside and unittriangle do not exist in Python: the .comm defines them
# (ASTER_FORMULA_PRELUDE), with the same behaviour as _heaviside and
# _unittriangle above (verified in Mecway 33).
_ASTER_FUNCS = {
    "sin": "sin", "cos": "cos", "tan": "tan", "asin": "asin",
    "acos": "acos", "atan": "atan", "atan2": "atan2", "log": "log",
    "abs": "abs", "sqrt": "sqrt", "max": "max", "min": "min",
    "heaviside": "_mw_heaviside", "unittriangle": "_mw_unittriangle",
}
# Arguments for FORMULE(...): name=object in the .comm. FORMULE evaluates the
# expression with only the given arguments and NOM_PARA (catalogue
# formule.py: "**args" as context), so abs/max/min explicitly as well.
_ASTER_FUNC_ARGS = {
    "sin": "_mw_math.sin", "cos": "_mw_math.cos", "tan": "_mw_math.tan",
    "asin": "_mw_math.asin", "acos": "_mw_math.acos",
    "atan": "_mw_math.atan", "atan2": "_mw_math.atan2",
    "log": "_mw_math.log", "sqrt": "_mw_math.sqrt", "abs": "abs",
    "max": "max", "min": "min", "heaviside": "_mw_heaviside",
    "unittriangle": "_mw_unittriangle",
}
ASTER_FORMULA_PRELUDE = (
    "# Mecway formulas (bridge_bcs.aster_expression): helper functions\n"
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
    Mecway formula as a Python expression for a Code-Aster FORMULE.

    variables : {"x"|"y"|"z"|"t": expression} (e.g. "(X/0.001)"); a
                variable that is not in the dict raises a ValueError.
    Returns (expression, variables used, {name: argument} for
    FORMULE). ValueError for an unreadable formula.
    The formula is first checked with _FormulaParser; then converted per
    token: '^' -> '**' (Python: right-associative and tighter than
    unary minus, as in Mecway: -2^2 = -4, 2^3^2 = 512), pi/e as a number,
    functions via _ASTER_FUNCS.
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
    """f(t) of a Mecway formula without x, y, z (ValueError otherwise)."""
    parser = _FormulaParser(text)
    fn = parser.parse()
    if parser.used - set(["t"]):
        raise ValueError(text)
    return fn


def _scalar(node, quantity):
    """Fixed SI value of node (text with unit or formula without t);
    FormulaError for a formula in t or x/y/z."""
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
    Decorator for parse_xml: on a FormulaError an ERROR and params =
    skipped_params of the class (gives no load; to_aster_dict -> {})
    plus "_skipped" = the description for model_data["skipped_loads"].
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
# BASE CLASS
# ==========================================
class BaseBC(object):
    aster_keyword = ""
    valid_targets = []
    # params of a load with an untranslatable formula
    # (_skip_on_formula_error): same form as parse_xml, without effect.
    skipped_params = {}

    def parse_xml(self, item, root):
        raise NotImplementedError("Moet worden overschreven door subklasse")

    def to_aster_dict(self, params):
        raise NotImplementedError("Moet worden overschreven door subklasse")

    def keyword(self, params):
        """Code-Aster keyword; can differ per BC (oblique
        direction -> LIAISON_OBLIQUE)."""
        return self.aster_keyword


# ==========================================
# HELPER FUNCTIONS: VALUE WITH TIME HISTORY, DIRECTION
# ==========================================
def _parse_value_strict(item, tag, quantity, default, root=None,
                        allow_position=False):
    """
    Value of <tag>: a float, or a list (t, value) if there are several
    <tag time="..."> (e.g. <value time="5 s">90 deg</value>) or if
    the value is a formula in t (see FORMULAS above; root gives the
    end time). The list becomes a DEFI_FONCTION in STAT_NON_LINE;
    MECA_STATIQUE takes the last value (bridge_to_aster.py). With
    allow_position a formula in x, y, z becomes a PositionFormula.
    FormulaError for a formula that cannot be translated.
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
    """Like _parse_value_strict, but without FormulaError (for
    bridge_from_liml, e.g. initial velocity): ERROR and default."""
    try:
        return _parse_value_strict(item, tag, quantity, default, root)
    except FormulaError as e:
        log(tr(u"ERROR: {0} op '{1}': {2} NIET meegenomen.",
               u"ERROR: {0} on '{1}': {2} NOT included.").format(
                   item.tag, item.get("selection", ""), e.text()))
        return default


def _scale(value, factor):
    """value (float or list (t, v)) times factor."""
    if isinstance(value, list):
        return [(t, v * factor) for t, v in value]
    return value * factor


def _value_at(value, t):
    """Value of value (float or list (t, v)) at time t: linear
    between the points, constant outside the range (like the DEFI_FONCTION
    of the bridge: PROL_GAUCHE/PROL_DROITE='CONSTANT')."""
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
    {"GRAVITE": [(t, g)], "DIRECTION": (dx, dy, dz)} for a gravity with
    time history (history: {axis: float or list (t, value)}), or {} if the
    vector is zero or changes direction in time (a PESANTEUR with
    FONC_MULT has a fixed DIRECTION). g has a sign (the vector is
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
    """Normalised direction from <x>/<y>/<z>, or None for a zero vector.
    FormulaError for a formula in t or x/y/z."""
    d = [_scalar(item.find(coord), "dimensionless")
         for coord in ("x", "y", "z")]
    n = math.sqrt(sum(c * c for c in d))
    if n < 1.0e-12:
        return None
    return tuple(c / n for c in d)


def _parse_direction(item):
    """Like _parse_direction_strict, but without FormulaError (for
    bridge_from_liml): ERROR and None (no direction)."""
    try:
        return _parse_direction_strict(item)
    except FormulaError as e:
        log(tr(u"ERROR: {0} op '{1}': {2} NIET meegenomen.",
               u"ERROR: {0} on '{1}': {2} NOT included.").format(
                   item.tag, item.get("selection", ""), e.text()))
        return None


def _angl_naut(direction):
    """
    ANGL_NAUT (degrees) whose local x axis lies along direction.
    Code-Aster: local x = (cos a cos b, sin a cos b, -sin b) (U4.44.01,
    LIAISON_OBLIQUE; nautical angles as in AFFE_CARA_ELEM ORIENTATION).
    """
    dx, dy, dz = direction
    a = math.degrees(math.atan2(dy, dx))
    b = math.degrees(math.atan2(-dz, math.sqrt(dx * dx + dy * dy)))
    return (a, b, 0.0)


def _directional_dict(params, prefix):
    """
    Mecway sets the component of the displacement (or rotation) along the
    direction to the value; perpendicular components stay free (manual v33
    par. 9.6/9.7). Along an axis: DDL_IMPO D<axis> (with sign). Oblique:
    LIAISON_OBLIQUE with the local x axis along the direction.
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
# FIXED SUPPORT  (tag: "fixed")
# Code-Aster: DDL_IMPO
#   - model without rotation DOFs (pure 3D): DX=DY=DZ=0
#   - model with rotation DOFs (beams/shells/DIS_TR):
#       BLOCAGE=('DEPLACEMENT', 'ROTATION')
#     BLOCAGE is the successor of LIAISON='ENCASTRE' (code_aster
#     Cata/Commands/affe_char_meca.py, compat_syntax, v17.4.0) and blocks
#     the degrees of freedom of the nodes per category, so that in a mixed
#     model no DRX/DRY/DRZ is imposed on 3D nodes that do not have them.
# Valid on: GROUP_NO and GROUP_MA
#
# Note: the "_has_rot_dofs" flag is NOT read in parse_xml(),
# but in to_aster_dict() via params.get("_has_rot_dofs", False).
# This flag is injected by bridge_from_liml.py (and bridge_mesh.py for
# added DIS_TR nodes) after the parse_xml() call.
# ==========================================
class FixedBC(BaseBC):
    aster_keyword = "DDL_IMPO"
    valid_targets = ["GROUP_NO", "GROUP_MA"]

    def parse_xml(self, item, root):
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    def to_aster_dict(self, params):
        # "_has_rot_dofs" is injected by bridge_from_liml.py / bridge_mesh.py;
        # NOT a global variable.
        if params.get("_has_rot_dofs", False):
            return {"BLOCAGE": ("DEPLACEMENT", "ROTATION")}
        return {"DX": 0.0, "DY": 0.0, "DZ": 0.0}


# ==========================================
# PINNED SUPPORT  (tag: "pinnedsupport")
# Code-Aster: DDL_IMPO with DX=DY=DZ=0 (no rotation blocking)
# Valid on: GROUP_NO and GROUP_MA
#
# A pinned support leaves rotations free: DRX/DRY/DRZ are deliberately
# NOT imposed, regardless of the element type.
# ==========================================
class PinnedBC(BaseBC):
    aster_keyword = "DDL_IMPO"
    valid_targets = ["GROUP_NO", "GROUP_MA"]

    def parse_xml(self, item, root):
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    def to_aster_dict(self, params):
        return {"DX": 0.0, "DY": 0.0, "DZ": 0.0}


# ==========================================
# IMPOSED DISPLACEMENT  (tag: "displacement")
# Code-Aster: DDL_IMPO (direction along an axis) or LIAISON_OBLIQUE (oblique)
# Valid on: GROUP_NO and GROUP_MA
#
# Mecway XML structure:
#   <value>      - value (with unit, e.g. "5 mm"); several
#                  <value time="..."> give a time history
#   <x>/<y>/<z>  - direction (gets normalised)
# The component along the direction gets the value, the others stay free
# (manual v33 par. 9.6).
# ==========================================
class DisplacementBC(BaseBC):
    aster_keyword = "DDL_IMPO"
    valid_targets = ["GROUP_NO", "GROUP_MA"]
    quantity = "length"
    prefix = "D"
    skipped_params = {"value": 0.0, "dir": None}
    # value as formula in x, y, z: DDL_IMPO/LIAISON_OBLIQUE with a
    # FORMULE (PositionFormula); the direction must be fixed
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
# IMPOSED ROTATION  (tag: "noderotation")
# Code-Aster: DDL_IMPO DRX/DRY/DRZ or LIAISON_OBLIQUE
# Valid on: GROUP_NO and GROUP_MA
#
# Only for nodes with rotation DOFs (beam, shell); on 3D nodes
# Code-Aster gives an error. Same XML as displacement, unit 'angle'
# (rad, or deg/° -> rad), direction = rotation axis (manual v33 par. 9.7).
# ==========================================
class NodeRotationBC(DisplacementBC):
    quantity = "angle"
    prefix = "DR"


# ==========================================
# FORCE  (tag: "force")
# Code-Aster: FORCE_NODALE with FX/FY/FZ on nodes; on faces FORCE_FACE,
# FORCE_COQUE or FORCE_ARETE (bridge_mesh._apply_to_model_data).
# Valid on: GROUP_NO and GROUP_MA
#
# IMPORTANT: the distribution happens OUTSIDE this class: over the nodes of
# a nodeselection in bridge_from_liml.py, over the nodes of
# beam ends and over the area/length of faces in
# bridge_mesh.py. parse_xml() returns the uncorrected TOTAL force
# per axis here (SI, Newton).
#
# Time history:
#   Mecway can give a force per time step via several <x>/<y>/<z>
#   elements with a time attribute, e.g.:
#     <x time="0 s">0 N</x>
#     <x time="1 s">1500 N</x>
#     <x time="2 s">2000 N</x>
#   parse_xml() then returns params[axis] as a list of (t, F) tuples
#   in SI units. Without a time attribute, params[axis] stays
#   a float (static force). If both static values and time steps are
#   present for the same axis, the time history takes precedence.
#
#   The MECA_STATIQUE builder collapses the list to the last value and
#   logs a warning. The STAT_NON_LINE builder generates a
#   DEFI_FONCTION and uses AFFE_CHAR_MECA_F.
# ==========================================
class ForceBC(BaseBC):
    # On nodes: FORCE_NODALE, distributed equally over the nodes. On faces:
    # FORCE_FACE; Mecway distributes the total force uniformly over the
    # area (manual v33 par. 9.13), so bridge_mesh.py divides by the
    # area of the face group and sets aster_keyword to FORCE_FACE.
    aster_keyword = "FORCE_NODALE"
    valid_targets = ["GROUP_NO", "GROUP_MA"]

    quantity = "force"
    prefix = "F"
    # components as formula in x, y, z (PositionFormula): force,
    # traction, line pressure; not for a moment (MomentBC)
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
        # Pass-through: values can be scalar (linear static) or
        # lists of (t, F) (nonlinear static). The rendering in
        # bridge_to_aster.py decides based on the type.
        return {"{0}{1}".format(self.prefix, ax.upper()): v
                for ax, v in params.items()
                if not ax.startswith("_")}


# ==========================================
# MOMENT  (tag: "moment")
# Mecway (manual v33 par. 9.18): on a single node with rotation DOFs
# (beam/shell) -> FORCE_NODALE MX/MY/MZ; on faces (shell or volume)
# as forces distributed over the faces, about the axis through the centroid.
# The distribution over faces is done by bridge_mesh.py (_moment_to_forces).
# XML: <moment selection="..."><x>2 N.m</x><y>..</y><z>..</z></moment>,
# per component possibly with time attributes (as for force).
# ==========================================
class MomentBC(ForceBC):
    quantity = "moment"
    prefix = "M"
    # distribution over the faces with fixed nodal forces
    # (bridge_mesh._moment_to_forces): no formula in x, y, z
    position_ok = False


# ==========================================
# GRAVITY  (tag: "gravity")
# Code-Aster: PESANTEUR with GRAVITE=|g| and DIRECTION=(dx,dy,dz)
# Valid on: global (no GROUP_MA in this implementation).
#
# Mecway XML structure:
#   <gravity>
#     <x>0 m/s2</x>
#     <y>0 m/s2</y>
#     <z>-9.81 m/s2</z>
#   </gravity>
#
# Code-Aster expects the gravity vector decomposed into:
#   GRAVITE   = magnitude |g| = sqrt(gx^2 + gy^2 + gz^2)   [m/s^2]
#   DIRECTION = normalised direction (gx/|g|, gy/|g|, gz/|g|)
#
# RHO comes from DEFI_MATERIAU (bridge_to_aster.py adds RHO in ELAS).
# Materials without density get RHO=0 and give no
# gravity contribution; Code-Aster gives no alarm in that case.
#
# IMPORTANT: <gravity> in the .liml has NO selection attribute.
# bridge_from_liml.py passes selection_name=""; bridge_to_aster.py
# detects this and omits the GROUP_MA prefix in the _F(...) entry.
#
# valid_targets stays ["GROUP_MA"] for consistency with the
# existing target validation in bridge_from_liml.py (an empty selection
# falls back to GROUP_MA automatically). The actual render writes
# no GROUP_MA when the selection is empty.
#
# Time history (Samples/SaggingCable.liml, Mecway manual v33 par. 9.19
# "constant or time-dependent"), per component as for force:
#   <y time="1 s">0 m/s²</y>
#   <y time="2 s">-9.8 m/s²</y>
# parse_xml() then puts in params["_history"] per component a float or a
# list (t, g) and in params x/y/z the value at the last time (for
# users that expect a fixed vector, e.g. hydrostatic pressure).
# to_aster_dict() turns it into GRAVITE = [(t, g(t))] (with sign) along a
# fixed DIRECTION; Code-Aster: PESANTEUR in AFFE_CHAR_MECA (not in
# AFFE_CHAR_MECA_F, catalogue affe_char_meca.py) with FONC_MULT in EXCIT,
# as in test case forma12b (PESANTEUR with EXCIT FONC_MULT). If the
# direction rotates in time, to_aster_dict() gives {} (cannot be translated
# with a function; bridge_from_liml reports that).
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
            # Fully zero vector: signal to the caller that this is
            # a no-op. bridge_from_liml.py already filters a zero vector
            # beforehand; bridge_to_aster.py skips an empty aster_dict.
            return {}

        return {
            "GRAVITE":   g,
            "DIRECTION": (gx / g, gy / g, gz / g),
        }


# ==========================================
# SURFACE PRESSURE  (tag: "surfacepressure")
# Code-Aster: PRES_REP with PRES=
# Valid on: GROUP_MA ONLY
#
# Convention: PRES > 0 = compressive (pushed towards the surface).
# Code-Aster computes the force vectors itself via the surface normal.
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
        # _sign: -1 for shell faces with faceid 6 (bridge_mesh.py)
        return {"PRES": _scale(params["PRES"], params.get("_sign", 1.0))}


# ==========================================
# IMPOSED VELOCITY  (tag: "velocity")
# Mecway (manual v33 par. 9.8): sets the component of the velocity along
# the direction; only in dynamic analyses. Code-Aster does not impose a
# velocity in DYNA_NON_LINE, but a displacement as a function of
# time: u(t) = integral of v (for constant v: v*t). The end time comes
# from <timesteps> (params["_t_end"], set by bridge_from_liml.py).
# ==========================================
class VelocityBC(DisplacementBC):
    quantity = "velocity"
    prefix = "D"
    # the velocity is integrated in time (_integrate): only
    # numbers and time histories
    position_ok = False

    def to_aster_dict(self, params):
        p = dict(params)
        p["value"] = _integrate(params.get("value", 0.0),
                                params.get("_t_end", 1.0))
        return _directional_dict(p, self.prefix)

    def keyword(self, params):
        return DisplacementBC.keyword(self, dict(params, value=0.0))


def _integrate(value, t_end):
    """Displacement history [(t, u)] for velocity value (float or
    [(t, v)], linear between the points, constant outside), from 0 to
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
# Mecway (manual v33 par. 9.2): normal displacement of the faces zero (or
# <displacement>, positive = into the face); at a node the average
# normal of the adjacent faces from the selection. On shells also the
# rotations about the in-plane axes.
# Code-Aster: FACE_IMPO DNOR on the boundary elements of volume elements
# (DNOR along the outward normal after ORIE_PEAU, so -value);
# flat shell faces via bridge_mesh.py as LIAISON_OBLIQUE.
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
            # flat shell faces (bridge_mesh._frictionless)
            return OrderedDict([("ANGL_NAUT", _angl_naut(params["_normal"])),
                                ("DX", value), ("DRY", 0.0), ("DRZ", 0.0)])
        return {"DNOR": value}

    def keyword(self, params):
        return "LIAISON_OBLIQUE" if "_normal" in params else "FACE_IMPO"


# ==========================================
# TRACTION  (tag: "traction")
# Mecway (manual v33 par. 9.15): force per area in global X/Y/Z, on
# faces or elements; per component possibly a time history.
#   <traction selection=".."><x>1 MPa</x><y>2 MPa</y><z>3 MPa</z></traction>
# Code-Aster: FORCE_FACE (faces of volume elements) or FORCE_COQUE
# (shells; PLAN follows the side, see bridge_mesh._traction). The choice is
# made by bridge_mesh.py; here only the components.
# ==========================================
class TractionBC(ForceBC):
    aster_keyword = "FORCE_FACE"
    valid_targets = ["GROUP_MA"]
    quantity = "pressure"


# ==========================================
# LINE PRESSURE  (tag: "linepressure")
# Mecway (manual v33 par. 9.16): force per length on line2/line3 elements
# or on locally 1D faces (shell edges), global X/Y/Z.
#   <linepressure selection=".."><x>0 N/m</x><y>10 N/m</y><z>-20 N/m</z>
# Code-Aster: FORCE_POUTRE FX/FY/FZ (beams) or FORCE_ARETE (shell edges),
# both force per length in the global coordinate system (U4.44.01).
# Element coordinates (beams only): <u>/<v>/<w> instead of <x>/<y>/<z>
# (XML seen in Mecway 33) -> FORCE_POUTRE N/VY/VZ in the local system;
# Code-Aster local y/z = Mecway V/W (see bridge_from_liml.py, profiles).
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
# HYDROSTATIC PRESSURE  (tag: "hydrostaticpressure")
# Mecway (manual v33 par. 9.17): pressure = rho * g * depth below the free
# surface (point <x>/<y>/<z>), zero above it; needs a separate gravity.
#   <hydrostaticpressure selection=".."><fluiddensity>1000 kg/m3
#   </fluiddensity><x>0 mm</x><y>0 mm</y><z>30 mm</z></hydrostaticpressure>
# Code-Aster: AFFE_CHAR_MECA_F PRES_REP with a FORMULE of X, Y, Z
# (U4.44.01 PRES_REP, "function" pressure). The formula is made by
# bridge_to_aster.py with the gravity vector (_hydrostatic_formula).
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
        # The PRES function only comes in bridge_to_aster.py (_build_charges).
        return {"PRES": params.get("_formula", "")}


# ==========================================
# ELASTIC SUPPORT  (tag: "elasticsupport")
# Mecway (manual v33 par. 9.4): stiffness per area, normal and
# tangential, on faces of volume elements and shell faces.
#   <elasticsupport selection=".."><modulus>1E12 Pa/m</modulus>
#   <tangential>2E11 Pa/m</tangential></elasticsupport>
# Code-Aster: a spring to ground per node (POI1, DIS_T, K_T_N), with
# stiffness = k * nodal weight of the area; bridge_mesh.py creates the
# elements (_build_discretes).
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
# Mecway (manual v33 par. 9.5): like frictionless where the support is
# loaded in compression, free where it would be in tension. The internal
# solver is hard; <stiffness> and <tensilestress> are only for CCX
# (springs) and are not read.
# Code-Aster: DEFI_CONTACT FORMULATION='LIAISON_UNIL' (U4.44.11 par. 3.8):
# per node n . u <= 0, with n the outward normal (towards the
# support). Only in STAT_NON_LINE/DYNA_NON_LINE. bridge_mesh.py
# groups the nodes per normal (_compression_only).
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
# Mecway (manual v33 par. 9.40): displacement perpendicular to the
# symmetry plane zero; rotations about in-plane axes zero (beam ends),
# on shell edges only the rotation about the edge. nodeplane="true": the
# plane follows from the nodes, otherwise normal <x>/<y>/<z>.
# Code-Aster: LIAISON_OBLIQUE with the local x axis along the normal
# (bridge_mesh._symmetry sets direction and groups).
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
# Mecway (manual v33 par. 9.20): rotation about the global X, Y or Z axis
# through the origin, F = m w^2 r on all mass (elements with density and
# nodal masses).
#   <centrifugal><x>0 rad/s</x><y>100000 r/min</y><z>0 rad/s</z>
# Code-Aster: AFFE_CHAR_MECA ROTATION=_F(VITESSE, AXE, CENTRE) (U4.44.01;
# catalogue affe_char_meca.py v17.4: VITESSE, AXE required). VITESSE in
# rad/s: NOT found in the documentation, verified with a run (see
# bridge_to_aster._build_charges). Nodal masses (DIS_T) get the force
# separately (bridge_to_aster._centrifugal_loads).
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
        """VITESSE and AXE, or {} if the axis is not X, Y or Z (or zero) or
        if there is a time history (bridge_from_liml.py reports that)."""
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
# BC REGISTRY
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
