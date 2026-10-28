# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_formula.py
# Responsibility: Mecway's result formulas (Solution > Formula, <formula>
# in the .liml; STAPPENPLAN S33, GitHub issue #8). Parses the formula text,
# knows Mecway's symbols and the units of a formula, and evaluates a
# formula on numpy arrays. bridge_from_liml (IronPython, Mecway) checks
# and plans the formulas; aster_results_export (Python 3 in the
# Code-Aster job) evaluates them per time step.
#
# Pure Python, standard library only (numpy is passed in by the caller);
# runs in Python 2.7 (IronPython 2.7.9) and Python 3.
#
# Mecway (measured headless with Mecway 34, mw_solve.py, and in the GUI):
#   - a formula is evaluated during Mecway's own solve and stored as
#     nodevariable <fieldscalar> ("formula", "formula(2)", ...), only on
#     the nodes where all its symbols have a value (FR.x: reaction nodes);
#     a formula created after solving is computed from the stored results;
#   - each symbol is first converted from SI to the unit of the <unit> line
#     with its dimension (exponents = powers of length, mass, time, current,
#     temperature, Mecway's order: "+1" = m, "-1+1-2" = Pa, "+0+1-3" =
#     W/m2, "+0+0+1" = s, "+0+0+0+0+1" = K, "" = dimensionless), then the
#     formula is evaluated and the number stored as it is (x in mm: 50 for
#     x = 0.05 m; T in degF: 100.018 for 310.938 K, affine);
#   - a unit Mecway does not know (e.g. "W/mm2") counts as SI;
#   - the symbols read Mecway's node values (s.xx = stressxx, e.xx =
#     lstrainxx, g.xy = lstrainxy (engineering shear strain), u.x*s.xx =
#     displx*stressxx per node);
#   - a formula with t is not computed in a static/steady solution;
#   - s1..s3, tr and e1..e3 read Mecway's principal fields principal1..3,
#     tresca and lprincipalstrain1..3; the bridge writes them with the
#     result fields principal_stresses / principal_strains (S34). GLe1..3:
#     not supported (Mecway's own L30 solution with CCX had no separate
#     Green-Lagrange principal field; e1 is the principal strain there).
# Language as for formulas in loads (bridge_bcs, measured in Mecway 33):
# + - * / ^ ( ), pi, e, sin, cos, tan, asin, acos, atan, atan2(y,x), log
# (natural), abs, sqrt, heaviside(x) (0.5 at 0), unittriangle(w,x),
# max(x,y), min(x,y); ^ binds tighter than unary minus and is right
# associative. Symbols are case sensitive (T = temperature, t = time).

import math
import re

# Dimensions as Mecway's exponents tuple (length, mass, time, current,
# temperature), trailing zeros removed.
LENGTH = (1,)
PRESSURE = (-1, 1, -2)
FORCE = (1, 1, -2)
MOMENT = (2, 1, -2)
HEAT_FLUX = (0, 1, -3)
TIME = (0, 0, 1)
VELOCITY = (1, 0, -1)
ACCELERATION = (1, 0, -2)
ANGULAR_VELOCITY = (0, 0, -1)
TEMPERATURE = (0, 0, 0, 0, 1)
NONE = ()

# Symbol -> (source, dimension). source: ("coord", i) initial node
# position, ("time",) the time of the step, or the name of the bridge's
# node variable (aster_results_export.FIELD_TABLE). Symbols of fields the
# bridge does not write (principal values, shell/element coordinates,
# electric, ...) are not in this table.
SYMBOLS = {
    "x": (("coord", 0), LENGTH), "y": (("coord", 1), LENGTH),
    "z": (("coord", 2), LENGTH), "t": (("time",), TIME),
    "T": ("temperature", TEMPERATURE),
    "vm": ("vonmises", PRESSURE),
    "peeq": ("equivalentplasticstrain", NONE),
    "P": ("pressure", PRESSURE),
    "cstr.P": ("contactpressure", PRESSURE),
    "fos": ("factorofsafety", NONE),
    # Principal values (S34; field principal_stresses / principal_strains)
    "s1": ("principal1", PRESSURE), "s2": ("principal2", PRESSURE),
    "s3": ("principal3", PRESSURE), "tr": ("tresca", PRESSURE),
    "e1": ("lprincipalstrain1", NONE), "e2": ("lprincipalstrain2", NONE),
    "e3": ("lprincipalstrain3", NONE),
}
for _c in "xyz":
    SYMBOLS["u." + _c] = ("displ" + _c, LENGTH)
    SYMBOLS["r." + _c] = ("rot" + _c, NONE)
    SYMBOLS["v." + _c] = ("vel" + _c, VELOCITY)
    SYMBOLS["a." + _c] = ("acc" + _c, ACCELERATION)
    SYMBOLS["av." + _c] = ("angularvel" + _c, ANGULAR_VELOCITY)
    SYMBOLS["FR." + _c] = ("reactionforce" + _c, FORCE)
    SYMBOLS["MR." + _c] = ("reactionmom" + _c, MOMENT)
    SYMBOLS["qf." + _c] = ("heatflux" + _c, HEAT_FLUX)
for _s in ("xx", "yy", "zz", "xy", "yz", "zx"):
    SYMBOLS["s." + _s] = ("stress" + _s, PRESSURE)
    _e = "e." if _s[0] == _s[1] else "g."
    SYMBOLS[_e + _s] = ("lstrain" + _s, NONE)
    _e = "GLe." if _s[0] == _s[1] else "GLg."
    SYMBOLS[_e + _s] = ("greenlagrangestrain" + _s, NONE)
# Beam forces (node values, bridge EFGE_NOEU / SIEF_NOEU)
for _sym, _var, _dim in (("FI.u", "tensileforce", FORCE),
                         ("FI.v", "sheary", FORCE),
                         ("FI.w", "shearz", FORCE),
                         ("MI.u", "torsion", MOMENT),
                         ("MI.v", "bendingmomv", MOMENT),
                         ("MI.w", "bendingmomw", MOMENT)):
    SYMBOLS[_sym] = (_var, _dim)

# Symbols Mecway knows (formula window, Mecway 34) that the bridge cannot
# evaluate: a clear message instead of "unknown name".
UNSUPPORTED = frozenset(
    ["b", "cdis.c", "cdis.1", "cdis.2", "r.u", "GLe1", "GLe2", "GLe3",
     "Ue", "UE", "V", "I", "qd",
     "dPd.x", "dPd.y", "cstr.1", "cstr.2", "iyy", "izz", "area", "density",
     "perimeter", "poissonratio", "specificheat", "torsionconstant",
     "youngsmodulus"] +
    ["ML.uu", "ML.vv", "ML.uv", "FL.uu", "FL.vv", "FL.uv", "FL.vw",
     "FL.wu"] +
    ["J." + c for c in "xyz"] + ["E." + c for c in "xyz"] +
    ["D." + c for c in "xyz"] + ["FE." + c for c in "xyz"] +
    ["s." + s for s in ("uu", "vv", "ww", "uv", "vw", "wu", "uu.1", "uu.2",
                        "uu.3", "uu.4", "uu.u")] +
    ["ZZs." + s for s in ("xx", "yy", "zz", "xy", "yz", "zx")] +
    ["ZZs1", "ZZs2", "ZZs3", "ZZvm"])

FUNCTIONS = {"sin": 1, "cos": 1, "tan": 1, "asin": 1, "acos": 1, "atan": 1,
             "atan2": 2, "log": 1, "abs": 1, "sqrt": 1, "heaviside": 1,
             "unittriangle": 2, "max": 2, "min": 2}
CONSTANTS = {"pi": math.pi, "e": math.e}

_TOKEN = re.compile(
    r"\s*(?:((?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)"
    r"|([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_0-9]+)*)|(\S))")


class FormulaError(ValueError):
    """Formula text that cannot be parsed or evaluated (message in
    English; the caller adds the formula name)."""


def _tokens(text):
    out = []
    pos = 0
    text = (text or "").rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None or m.end() == pos:
            break
        pos = m.end()
        if m.group(1) is not None:
            out.append(("num", m.group(1)))
        elif m.group(2) is not None:
            out.append(("name", m.group(2)))
        else:
            out.append(("op", m.group(3)))
    return out


class _Parser(object):
    """Recursive descent into a tree of tuples:
      ("num", v) ("sym", name) ("neg", a) ("bin", op, a, b)
      ("pow", a, b) ("call", function, [args])
    Grammar as bridge_bcs._FormulaParser (measured in Mecway 33):
      expr  := term (('+' | '-') term)*
      term  := unary (('*' | '/') unary)*
      unary := ('-' | '+') unary | power
      power := atom ('^' unary)?
      atom  := number | name | name '(' expr (',' expr)* ')' | '(' expr ')'
    """

    def __init__(self, text):
        self.tokens = _tokens(text)
        self.pos = 0

    def parse(self):
        if not self.tokens:
            raise FormulaError("empty formula")
        node = self._expr()
        if self.pos != len(self.tokens):
            raise FormulaError("unexpected '{0}'".format(
                self.tokens[self.pos][1]))
        return node

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
        node = self._term()
        while True:
            if self._take("+"):
                node = ("bin", "+", node, self._term())
            elif self._take("-"):
                node = ("bin", "-", node, self._term())
            else:
                return node

    def _term(self):
        node = self._unary()
        while True:
            if self._take("*"):
                node = ("bin", "*", node, self._unary())
            elif self._take("/"):
                node = ("bin", "/", node, self._unary())
            else:
                return node

    def _unary(self):
        if self._take("-"):
            return ("neg", self._unary())
        if self._take("+"):
            return self._unary()
        return self._power()

    def _power(self):
        node = self._atom()
        if self._take("^"):
            node = ("pow", node, self._unary())
        return node

    def _atom(self):
        kind, text = self._peek()
        if kind is None:
            raise FormulaError("formula incomplete")
        self.pos += 1
        if kind == "num":
            return ("num", float(text))
        if kind == "op":
            if text == "(":
                node = self._expr()
                if not self._take(")"):
                    raise FormulaError("')' missing")
                return node
            raise FormulaError("unexpected '{0}'".format(text))
        if self._take("("):
            fname = text.lower()
            if fname not in FUNCTIONS:
                raise FormulaError("unknown function '{0}'".format(text))
            args = [self._expr()]
            while self._take(","):
                args.append(self._expr())
            if not self._take(")"):
                raise FormulaError("')' missing")
            if len(args) != FUNCTIONS[fname]:
                raise FormulaError("{0} expects {1} argument(s)".format(
                    fname, FUNCTIONS[fname]))
            return ("call", fname, args)
        if text in SYMBOLS:
            return ("sym", text)
        if text.lower() in CONSTANTS:
            return ("num", CONSTANTS[text.lower()])
        if text in UNSUPPORTED:
            raise FormulaError("symbol '{0}' is not supported by the bridge"
                               .format(text))
        raise FormulaError("unknown name '{0}'".format(text))


def parse(text):
    """Tree of the formula text; FormulaError if it cannot be parsed or
    uses a symbol the bridge cannot evaluate."""
    return _Parser(text).parse()


def symbols(tree):
    """Set of the symbols used in tree."""
    out = set()
    stack = [tree]
    while stack:
        node = stack.pop()
        if node[0] == "sym":
            out.add(node[1])
        elif node[0] in ("neg",):
            stack.append(node[1])
        elif node[0] == "pow":
            stack.extend(node[1:3])
        elif node[0] == "bin":
            stack.extend(node[2:4])
        elif node[0] == "call":
            stack.extend(node[2])
    return out


def evaluate(tree, env, np):
    """Value of tree with env {symbol: array or number}; numpy as np.
    Division by zero and invalid operations give inf/nan (no error)."""
    kind = tree[0]
    if kind == "num":
        return tree[1]
    if kind == "sym":
        return env[tree[1]]
    if kind == "neg":
        return -evaluate(tree[1], env, np)
    if kind == "pow":
        return np.power(np.asarray(evaluate(tree[1], env, np), dtype=float),
                        evaluate(tree[2], env, np))
    if kind == "bin":
        a = evaluate(tree[2], env, np)
        b = evaluate(tree[3], env, np)
        op = tree[1]
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        return np.true_divide(a, b)
    args = [evaluate(a, env, np) for a in tree[2]]
    f = tree[1]
    if f == "heaviside":
        return np.heaviside(args[0], 0.5)
    if f == "unittriangle":
        w, x = args
        half = 0.5 * np.asarray(w, dtype=float)
        return np.where(np.abs(x) < half,
                        (2.0 / np.asarray(w, dtype=float)) *
                        (1.0 - np.abs(x) / half), 0.0)
    if f == "max":
        return np.maximum(args[0], args[1])
    if f == "min":
        return np.minimum(args[0], args[1])
    if f == "atan2":
        return np.arctan2(args[0], args[1])
    name = {"asin": "arcsin", "acos": "arccos", "atan": "arctan"}.get(f, f)
    return getattr(np, name)(args[0])


# ==========================================
# UNITS
# ==========================================
def exponents(text):
    """Mecway's exponents attribute ("+0+1-3") as a tuple without trailing
    zeros; None if it cannot be read."""
    text = (text or "").strip()
    if not text:
        return ()
    parts = re.findall(r"[-+]?\d+", text)
    if "".join(parts) != text.replace(" ", ""):
        return None
    out = [int(p) for p in parts]
    while out and out[-1] == 0:
        out.pop()
    return tuple(out)


def _dim(**kw):
    order = ("L", "M", "T", "I", "K")
    out = [kw.get(k, 0) for k in order]
    while out and out[-1] == 0:
        out.pop()
    return tuple(out)


# Unit atoms: name -> (SI factor, dimension). Spelling as Mecway writes it
# in the .liml (normalised: superscripts to digits, '·' to '.'). Composite
# units (W/m2, Btu/h/ft2, N.mm, kg/m3) are made of these with '/', '.',
# '*' and powers. Values: NIST SP 811 (2008), Btu = Btu_IT.
_IN = 0.0254
_FT = 0.3048
_LBM = 0.45359237
_LBF = 4.4482216152605
_BTU = 1055.05585262
_ATOMS = {
    "m": (1.0, _dim(L=1)), "mm": (1.0e-3, _dim(L=1)),
    "cm": (1.0e-2, _dim(L=1)), "km": (1.0e3, _dim(L=1)),
    "um": (1.0e-6, _dim(L=1)), "in": (_IN, _dim(L=1)),
    "ft": (_FT, _dim(L=1)), "yd": (0.9144, _dim(L=1)),
    "mi": (1609.344, _dim(L=1)), "mil": (_IN * 1.0e-3, _dim(L=1)),
    "kg": (1.0, _dim(M=1)), "g": (1.0e-3, _dim(M=1)),
    "t": (1.0e3, _dim(M=1)), "tonne": (1.0e3, _dim(M=1)),
    "lb": (_LBM, _dim(M=1)), "lbm": (_LBM, _dim(M=1)),
    "slug": (14.593902937, _dim(M=1)),
    "s": (1.0, _dim(T=1)), "ms": (1.0e-3, _dim(T=1)),
    "us": (1.0e-6, _dim(T=1)), "min": (60.0, _dim(T=1)),
    "h": (3600.0, _dim(T=1)), "hr": (3600.0, _dim(T=1)),
    "day": (86400.0, _dim(T=1)),
    "n": (1.0, _dim(L=1, M=1, T=-2)), "kn": (1.0e3, _dim(L=1, M=1, T=-2)),
    "mn_mega": (1.0e6, _dim(L=1, M=1, T=-2)),
    "lbf": (_LBF, _dim(L=1, M=1, T=-2)),
    "kip": (_LBF * 1.0e3, _dim(L=1, M=1, T=-2)),
    "kgf": (9.80665, _dim(L=1, M=1, T=-2)),
    "pa": (1.0, _dim(L=-1, M=1, T=-2)), "kpa": (1.0e3, _dim(L=-1, M=1, T=-2)),
    "mpa_mega": (1.0e6, _dim(L=-1, M=1, T=-2)),
    "gpa": (1.0e9, _dim(L=-1, M=1, T=-2)),
    "bar": (1.0e5, _dim(L=-1, M=1, T=-2)),
    "psi": (_LBF / _IN ** 2, _dim(L=-1, M=1, T=-2)),
    "ksi": (_LBF * 1.0e3 / _IN ** 2, _dim(L=-1, M=1, T=-2)),
    "psf": (_LBF / _FT ** 2, _dim(L=-1, M=1, T=-2)),
    "j": (1.0, _dim(L=2, M=1, T=-2)), "kj": (1.0e3, _dim(L=2, M=1, T=-2)),
    "btu": (_BTU, _dim(L=2, M=1, T=-2)),
    "cal": (4.184, _dim(L=2, M=1, T=-2)),
    "kcal": (4184.0, _dim(L=2, M=1, T=-2)),
    "w": (1.0, _dim(L=2, M=1, T=-3)), "kw": (1.0e3, _dim(L=2, M=1, T=-3)),
    "hp": (745.69987158227, _dim(L=2, M=1, T=-3)),
    "a": (1.0, _dim(I=1)),
    "rad": (1.0, ()), "deg": (math.pi / 180.0, ()),
    "k": (1.0, _dim(K=1)),
    "hz": (1.0, _dim(T=-1)),
}
# Temperatures: SI (K) = factor * value + offset; only as the whole unit
_TEMPERATURES = {"k": (1.0, 0.0), "degc": (1.0, 273.15), "c": (1.0, 273.15),
                 "degf": (5.0 / 9.0, 459.67 * 5.0 / 9.0),
                 "f": (5.0 / 9.0, 459.67 * 5.0 / 9.0),
                 "degr": (5.0 / 9.0, 0.0), "r": (5.0 / 9.0, 0.0)}


def _normalise_unit(text):
    t = (text or "").strip()
    for a, b in ((u"²", "2"), (u"³", "3"), (u"⁴", "4"),
                 (u"·", "."), (u"⋅", "."), (u"µ", "u"),
                 (u"μ", "u"), (u"°", "deg"), (u"−", "-")):
        t = t.replace(a, b)
    return t.replace(" ", "")


def _atom(name):
    if name in ("mN",):
        return (1.0e-3, _dim(L=1, M=1, T=-2))
    if name == "MN":
        return _ATOMS["mn_mega"]
    if name in ("MPa", "Mpa"):
        return _ATOMS["mpa_mega"]
    if name == "mPa":
        return (1.0e-3, _dim(L=-1, M=1, T=-2))
    return _ATOMS.get(name.lower())


def unit_map(text, dims):
    """(a, b) with SI = a * value + b for the unit text of a <unit> line
    with dimension dims (tuple from exponents()); None if the unit is not
    known or does not have that dimension (Mecway then computes in SI)."""
    t = _normalise_unit(text)
    if not t:
        return (1.0, 0.0) if dims == () else None
    if dims == TEMPERATURE:
        return _TEMPERATURES.get(t.lower())
    factor = 1.0
    dim = [0, 0, 0, 0, 0]
    # '/' divides everything after it until the next '/' (Mecway writes
    # Btu/h/ft2 = Btu / h / ft2). Parentheses: Mecway 34 treated
    # "BTU/(h.ft2)" as unknown (SI, measured), so here too.
    if "(" in t or ")" in t:
        return None
    for i, group in enumerate(t.split("/")):
        sign = 1 if i == 0 else -1
        for part in re.split(r"[.*]", group):
            if not part:
                return None
            m = re.match(r"^([A-Za-z]+)\^?(-?\d+)?$", part)
            if m is None:
                return None
            atom = _atom(m.group(1))
            if atom is None:
                return None
            power = int(m.group(2)) if m.group(2) else 1
            factor *= atom[0] ** (sign * power)
            for k, e in enumerate(atom[1]):
                dim[k] += sign * power * e
    while dim and dim[-1] == 0:
        dim.pop()
    if tuple(dim) != tuple(dims):
        return None
    return (factor, 0.0)


# ==========================================
# PLAN (bridge_from_liml) AND EVALUATION (aster_results_export)
# ==========================================
def plan(name, fieldscalar, text, units):
    """Check a Mecway formula and return its plan, a dict with only
    plain types (it is written into study.comm):
      {"name", "fieldscalar", "text", "symbols": {symbol: [source, a, b]},
       "notes": [English texts for an INFO/WARNING]}
    with value_in_formula_unit = (SI - b) / a per symbol. units: list of
    (exponents text, unit text) of the <unit> lines. FormulaError if the
    formula cannot be evaluated by the bridge."""
    tree = parse(text)
    lines = {}
    for ex, un in units:
        dims = exponents(ex)
        if dims is not None:
            lines[dims] = un
    notes = []
    syms = {}
    for sym in sorted(symbols(tree)):
        source, dims = SYMBOLS[sym]
        unit = lines.get(dims)
        ab = None
        if unit is None:
            if dims != ():
                notes.append("no unit line for the dimension of '{0}': "
                             "SI used".format(sym))
            ab = (1.0, 0.0)
        else:
            ab = unit_map(unit, dims)
            if ab is None:
                notes.append("unit '{0}' of '{1}' not known: SI used (as "
                             "Mecway does)".format(unit, sym))
                ab = (1.0, 0.0)
        if isinstance(source, tuple):
            source = list(source)
        syms[sym] = [source, ab[0], ab[1]]
    return {"name": name, "fieldscalar": fieldscalar, "text": text,
            "symbols": syms, "notes": notes}


def uses_time(p):
    """True if the formula plan p uses t."""
    return "t" in p["symbols"]


# Bridge node variable (prefix) -> result field group (bridge_from_aster.
# RESULT_FIELD_SPECS, the analysis setting "fields"); a formula only gets
# values if its groups are exported.
_GROUPS = (("displ", "displacements"), ("rot", "displacements"),
           ("vel", "velocities"), ("angularvel", "velocities"),
           ("acc", "accelerations"), ("reactionforce", "reactions"),
           ("reactionmom", "reactions"), ("stress", "stresses"),
           ("vonmises", "vonmises"), ("lstrain", "strain"),
           ("greenlagrangestrain", "strain"),
           ("equivalentplasticstrain", "plastic_strain_eq"),
           ("temperature", "temperature"), ("heatflux", "heat_flux"),
           ("contactpressure", "contact"),
           ("factorofsafety", "safety_factor"),
           ("principal", "principal_stresses"),
           ("tresca", "principal_stresses"),
           ("lprincipalstrain", "principal_strains"),
           ("tensileforce", "beam_forces"), ("shear", "beam_forces"),
           ("torsion", "beam_forces"), ("bendingmom", "beam_forces"))


def groups(p):
    """Result field groups the formula plan p needs (sorted list)."""
    out = set()
    for source, _a, _b in p["symbols"].values():
        if isinstance(source, list):
            continue
        for prefix, group in _GROUPS:
            if source.startswith(prefix):
                out.add(group)
                break
    return sorted(out)
