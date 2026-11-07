# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_profiles.py
# Mecway's beam sections as closed loops, plus what the solver uses as section
# properties, and the unit strings of a .liml. CPython 3; NOT in IronPython.
#
#   parse_value(text, quantity)         "10000 mm⁴" -> SI float
#   solver_props(geometric)             {"A", "ivv", "iww", "ivw"}
#   loops_for(geometric, shape=None)    {"loops", "props"}
#
# geometric is the dict of attributes of a <geometric> element, values as
# strings with units. shape is the parsed SECTIE-VORM of the material
# (beam_model reads it): {"loops", "area"}.
#
# AXES, measured on Mecway 35 (tests/test_section_profiles.py, tests/mecway):
# section loops are in V, W about the centroid, W = U x V. RectBar: recta along
# V, rectb along W. I, T, C, L: the drawing of the material window has x
# horizontal, y vertical; V = (-sin t, cos t) in the drawing, W = -(cos t, sin t),
# so the drawing x runs along -W: the web of a C is at +W, its flanges point to
# -W. t = 0 for I, T and C. An L is in its principal axes, with t wrapped into
# (-45, 45] degrees. Dimensions:
#   I  a height, b flange width, c flange thickness, d web thickness
#   T  a flange width, b web thickness, c flange thickness, d web height
#   C  a flange width incl. web, b height, c flange thickness, d web thickness
#   L  a horizontal leg, b vertical leg, c thickness
# Measured against stressptu and stresspt1..4 and against tip displacements:
# the solver uses the exact A, Iyy and Izz of these outlines. For a general
# section it uses area, iyy, izz as given. ivv = Mecway's iyy = int(w^2), iww =
# Mecway's izz = int(v^2), ivw = 0 in these axes. These hold for Mecway's own
# solver; other solvers NOT verified.

import math
import re

from section_stress import SectionError

BEAM_TYPES = ("RectBar", "RectTube", "CircularBar", "UniformCircularTube", "I", "T", "L", "C",
              "UniformGeneralSection")
# Sides of the polygon of a circle: area 0.02 % short
CIRCLE_SIDES = 180
# Largest relative difference of A between a SECTIE-VORM and its material, as
# MecwayAsterBridge: Mecway stores 15 digits, the line 10
SHAPE_AREA_TOL = 1.0e-6

# name: (SI factor, (length, mass, time))
_LB = 0.45359237
_IN = 0.0254
_FT = 0.3048
_LBF = _LB * 9.80665
_KIP = 1000.0 * _LBF
_FORCE = (1, 1, -2)
_PRESSURE = (-1, 1, -2)
_UNITS = {
    "m": (1.0, (1, 0, 0)), "mm": (1e-3, (1, 0, 0)), "cm": (1e-2, (1, 0, 0)),
    "km": (1e3, (1, 0, 0)), "um": (1e-6, (1, 0, 0)), "in": (_IN, (1, 0, 0)),
    "inch": (_IN, (1, 0, 0)), "ft": (_FT, (1, 0, 0)),
    "kg": (1.0, (0, 1, 0)), "g": (1e-3, (0, 1, 0)), "t": (1e3, (0, 1, 0)),
    "tonne": (1e3, (0, 1, 0)), "lb": (_LB, (0, 1, 0)), "lbm": (_LB, (0, 1, 0)),
    "slug": (_LBF / _FT, (0, 1, 0)),
    "s": (1.0, (0, 0, 1)), "sec": (1.0, (0, 0, 1)), "ms": (1e-3, (0, 0, 1)),
    "min": (60.0, (0, 0, 1)), "h": (3600.0, (0, 0, 1)),
    "N": (1.0, _FORCE), "mN": (1e-3, _FORCE), "kN": (1e3, _FORCE), "MN": (1e6, _FORCE),
    "lbf": (_LBF, _FORCE), "kip": (_KIP, _FORCE), "kips": (_KIP, _FORCE),
    "Pa": (1.0, _PRESSURE), "kPa": (1e3, _PRESSURE), "MPa": (1e6, _PRESSURE),
    "GPa": (1e9, _PRESSURE), "bar": (1e5, _PRESSURE), "mbar": (1e2, _PRESSURE),
    "psi": (_LBF / _IN ** 2, _PRESSURE), "ksi": (_KIP / _IN ** 2, _PRESSURE),
    "psf": (_LBF / _FT ** 2, _PRESSURE),
    "rad": (1.0, (0, 0, 0)), "deg": (math.pi / 180.0, (0, 0, 0)),
}
_QUANTITIES = {"length": (1, 0, 0), "area": (2, 0, 0), "inertia": (4, 0, 0),
               "pressure": _PRESSURE, "force": _FORCE, "moment": (2, 1, -2),
               "line_load": (0, 1, -2), "acceleration": (1, 0, -2), "density": (-3, 1, 0),
               "angle": (0, 0, 0)}
_SUPERSCRIPT = {u"⁰": u"0", u"¹": u"1", u"²": u"2", u"³": u"3",
                u"⁴": u"4", u"⁵": u"5", u"⁶": u"6", u"⁻": u"-"}
_NUMBER = re.compile(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$", re.S)
_TOKEN = re.compile(r"([A-Za-z]+)\^?(-?\d+)?")


class UnitError(ValueError):
    """A value or unit that cannot be read; never guessed."""


def _unit_factor(unit):
    """(SI factor, dimensions) of a unit such as "kg/m³" or "N.m"."""
    for old, new in _SUPERSCRIPT.items():
        unit = unit.replace(old, new)
    unit = unit.replace(u"°", "deg").replace(u"µ", "u").replace(u"μ", "u")
    unit = unit.replace(u"·", ".").replace("*", ".")
    factor, dims, sign, pos = 1.0, [0, 0, 0], 1, 0
    while pos < len(unit):
        if unit[pos] in ". ":
            pos += 1
            continue
        if unit[pos] == "/":
            sign, pos = -1, pos + 1
            continue
        match = _TOKEN.match(unit, pos)
        if not match or match.group(1) not in _UNITS:
            raise UnitError(unit)
        size, base = _UNITS[match.group(1)]
        power = sign * int(match.group(2) or 1)
        factor *= size ** power
        dims = [d + b * power for d, b in zip(dims, base)]
        pos = match.end()
        # after a "/" only the next factor is below the line, as Mecway's "W/m/K"
        # has two divisions and "N.m/s" one
        sign = 1
    return factor, tuple(dims)


def parse_value(text, quantity):
    """SI value of a string with a number and an optional unit. A bare number
    is SI. An unknown unit, or one of another quantity, raises UnitError."""
    match = _NUMBER.match(text or "")
    if not match:
        raise UnitError(text)
    value = float(match.group(1))
    unit = match.group(2)
    if not unit:
        return value
    factor, dims = _unit_factor(unit)
    if dims != _QUANTITIES[quantity]:
        raise UnitError(text)
    return value * factor


def starts_with_number(text):
    """True for a number followed by something: a unit, not a formula."""
    return bool(_NUMBER.match(text or ""))


def _value(geometric, key, quantity):
    try:
        return parse_value(geometric[key], quantity)
    except KeyError:
        raise SectionError("missing_dimension", key)
    except UnitError as exc:
        raise SectionError("bad_value", "{0}: {1}".format(key, exc))


def _lengths(geometric, keys):
    values = [_value(geometric, k, "length") for k in keys]
    if min(values) <= 0.0:
        raise SectionError("bad_dimensions", str(dict(zip(keys, values))))
    return values


def _check(ok, geometric):
    if not ok:
        raise SectionError("bad_dimensions", str(geometric))


def _rectangle(a, b):
    return [(-a / 2.0, -b / 2.0), (a / 2.0, -b / 2.0), (a / 2.0, b / 2.0), (-a / 2.0, b / 2.0)]


def _circle(radius):
    step = 2.0 * math.pi / CIRCLE_SIDES
    return [(radius * math.cos(k * step), radius * math.sin(k * step))
            for k in range(CIRCLE_SIDES)]


def _moments(loop):
    """A, Sx, Sy, int x^2, int y^2, int xy of a polygon, signed."""
    t = [0.0] * 6
    n = len(loop)
    for i in range(n):
        x0, y0 = loop[i]
        x1, y1 = loop[(i + 1) % n]
        cr = x0 * y1 - x1 * y0
        t[0] += cr / 2.0
        t[1] += cr * (x0 + x1) / 6.0
        t[2] += cr * (y0 + y1) / 6.0
        t[3] += cr * (x0 * x0 + x0 * x1 + x1 * x1) / 12.0
        t[4] += cr * (y0 * y0 + y0 * y1 + y1 * y1) / 12.0
        t[5] += cr * (x0 * y1 + 2.0 * x0 * y0 + 2.0 * x1 * y1 + x1 * y0) / 24.0
    return t


def principal_angle(i_w, i_v, i_vw):
    """Mecway's principal angle of an L from the inertias of the drawing:
    i_w about the horizontal axis, i_v about the vertical axis, i_vw the
    product, wrapped into (-45, 45] degrees. Measured on stressptu, see the
    file header; without the wrap V and W change places."""
    theta = 0.5 * math.atan2(-2.0 * i_vw, i_w - i_v)
    while theta > math.pi / 4.0 + 1e-12:
        theta -= math.pi / 2.0
    while theta <= -math.pi / 4.0 + 1e-12:
        theta += math.pi / 2.0
    return theta


def _drawing(kind, geometric):
    """Outline of an I, T, C or L in the drawing (x horizontal, y vertical)."""
    p = kind.lower()
    if kind == "L":
        a, b, c = _lengths(geometric, [p + "a", p + "b", p + "c"])
        _check(c < a and c < b, geometric)
        return [(0.0, 0.0), (a, 0.0), (a, c), (c, c), (c, b), (0.0, b)]
    a, b, c, d = _lengths(geometric, [p + k for k in "abcd"])
    if kind == "I":
        _check(2.0 * c < a and d < b, geometric)
        x0, x1 = (b - d) / 2.0, (b + d) / 2.0
        return [(0.0, 0.0), (b, 0.0), (b, c), (x1, c), (x1, a - c), (b, a - c), (b, a), (0.0, a),
                (0.0, a - c), (x0, a - c), (x0, c), (0.0, c)]
    if kind == "T":
        _check(b < a, geometric)
        x0, x1 = (a - b) / 2.0, (a + b) / 2.0
        return [(x0, 0.0), (x1, 0.0), (x1, d), (a, d), (a, d + c), (0.0, d + c), (0.0, d),
                (x0, d)]
    _check(d < a and 2.0 * c < b, geometric)        # C
    return [(0.0, 0.0), (a, 0.0), (a, c), (d, c), (d, b - c), (a, b - c), (a, b), (0.0, b)]


def _profile_loop(kind, geometric):
    """The outline of an I, T, C or L in V, W about the centroid."""
    loop = _drawing(kind, geometric)
    area, sx, sy, xx, yy, xy = _moments(loop)
    cx, cy = sx / area, sy / area
    theta = 0.0
    if kind == "L":
        theta = principal_angle(yy - area * cy * cy, xx - area * cx * cx, xy - area * cx * cy)
    sn, cs = math.sin(theta), math.cos(theta)
    return [(-sn * (x - cx) + cs * (y - cy), -(cs * (x - cx) + sn * (y - cy))) for x, y in loop]


def _standard_loops(geometric):
    kind = geometric.get("type")
    if kind == "RectBar":
        return [_rectangle(*_lengths(geometric, ["recta", "rectb"]))]
    if kind == "RectTube":
        a, b, t = _lengths(geometric, ["recta", "rectb", "rectthickness"])
        _check(2.0 * t < a and 2.0 * t < b, geometric)
        return [_rectangle(a, b), _rectangle(a - 2.0 * t, b - 2.0 * t)]
    if kind == "CircularBar":
        return [_circle(_lengths(geometric, ["roundod"])[0] / 2.0)]
    if kind == "UniformCircularTube":
        od = _lengths(geometric, ["roundod"])[0]
        rid = _value(geometric, "roundid", "length")
        _check(0.0 <= rid < od, geometric)
        return [_circle(od / 2.0)] + ([_circle(rid / 2.0)] if rid > 0.0 else [])
    if kind in ("I", "T", "L", "C"):
        return [_profile_loop(kind, geometric)]
    raise SectionError("unknown_section", str(kind))


def solver_props(geometric):
    """{"A", "ivv", "iww", "ivw"} as the solver uses them, see the file header.
    The first three of a general section are its attributes, so this also works
    without a shape."""
    kind = geometric.get("type")
    if kind == "UniformGeneralSection":
        props = {"A": _value(geometric, "area", "area"),
                 "ivv": _value(geometric, "iyy", "inertia"),
                 "iww": _value(geometric, "izz", "inertia"), "ivw": 0.0}
        if min(props["A"], props["ivv"], props["iww"]) <= 0.0:
            raise SectionError("bad_properties", str(props))
        return props
    if kind in ("CircularBar", "UniformCircularTube"):
        od = _lengths(geometric, ["roundod"])[0]
        rid = 0.0
        if kind != "CircularBar":
            rid = _value(geometric, "roundid", "length")
            _check(0.0 <= rid < od, geometric)
        inertia = math.pi * (od ** 4 - rid ** 4) / 64.0
        return {"A": math.pi * (od ** 2 - rid ** 2) / 4.0, "ivv": inertia, "iww": inertia,
                "ivw": 0.0}
    loops = _standard_loops(geometric)
    area, ivv, iww = 0.0, 0.0, 0.0
    for sign, loop in zip((1.0, -1.0), loops):
        m = _moments(loop)
        area += sign * abs(m[0])
        ivv += sign * abs(m[4])
        iww += sign * abs(m[3])
    # about the centroid: the outlines of a profile are at their centroid, the
    # rectangles and circles at their centre
    return {"A": area, "ivv": ivv, "iww": iww, "ivw": 0.0}


def loops_for(geometric, shape=None):
    """{"loops", "props"}: closed loops in V, W about the centroid, even-odd
    interior, and the properties of the solver. shape: the parsed SECTIE-VORM of
    the material, needed for a general section. Raises SectionError: no_shape,
    stale_shape (its A does not match the material, so it belongs to something
    else), unknown_section, missing_dimension, bad_value, bad_dimensions,
    bad_properties."""
    props = solver_props(geometric)
    if geometric.get("type") != "UniformGeneralSection":
        return {"loops": _standard_loops(geometric), "props": props}
    if not shape or not shape.get("loops"):
        raise SectionError("no_shape", "general section without SECTIE-VORM")
    area = shape.get("area")
    if area is not None and abs(area - props["A"]) > SHAPE_AREA_TOL * props["A"]:
        raise SectionError("stale_shape", "A {0} in the line, {1} in the material".format(
            area, props["A"]))
    return {"loops": [list(loop) for loop in shape["loops"]], "props": props}
