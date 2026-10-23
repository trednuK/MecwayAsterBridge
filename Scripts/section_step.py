# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_step.py
# Small STEP (ISO 10303-21) reader for MecwaySectionProps: finds the planar
# CAD face(s) on a given plane and returns their exact boundary as 2D
# polylines, so the section properties are computed on the CAD geometry
# instead of on the mesh.
# Pure Python, standard library only; runs in CPython 3 and IronPython 2.7.9.
#
# API:
#   find_faces(path, normal, offset, points, tol)  -> [face_id, ...]
#   face_loops_2d(path, face_ids, u, v)            -> [[[x, y], ...], ...]
#   face_ids(path)                                 -> all face ids in order
# All coordinates in metres (the STEP length unit is converted, Mecway places
# STEP geometry 1:1 in its model in metres, checked with Mecway's PipeClip
# sample). Face ids are the STEP instance numbers (#id) of ADVANCED_FACE /
# FACE_SURFACE entities.

import io
import math
import os
import re

# ---------------------------------------------------------------------------
# Part 21 parser
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"/\*.*?\*/"                         # comment
    r"|'(?:[^']|'')*'"                   # string, '' is an escaped quote
    r'|"[^"]*"'                          # binary
    r"|#\d+"                             # instance reference / name
    r"|\.[A-Za-z_][A-Za-z0-9_]*\."       # enumeration / logical
    r"|[+-]?\d+\.?\d*(?:[Ee][+-]?\d+)?"  # number
    r"|!?[A-Za-z_][A-Za-z0-9_]*"         # keyword
    r"|[()=;,$*]",
    re.DOTALL)


class Ref(int):
    """Reference to an entity instance (#n)."""
    pass


class Enum(str):
    """Enumeration value without the dots (.T. -> 'T')."""
    pass


class Typed(object):
    """Typed parameter, e.g. LENGTH_MEASURE(25.4)."""
    def __init__(self, name, args):
        self.name = name
        self.args = args


DERIVED = "*"


class Entity(object):
    """One entity instance. parts: {TYPE_NAME: [args]} (one part for a simple
    entity, several for a complex entity ( A() B() ... ))."""
    def __init__(self, eid, parts, order):
        self.id = eid
        self.parts = parts
        self.order = order

    def name(self):
        return self.order[0] if len(self.order) == 1 else \
            "(" + " ".join(self.order) + ")"

    def has(self, t):
        return t in self.parts

    def args(self, t=None):
        if t is None:
            return self.parts[self.order[0]]
        return self.parts[t]


class StepError(ValueError):
    pass


def _parse_tokens(tokens):
    """Builds {id: Entity} from the token list of the whole file. Header
    entities (FILE_NAME(...);) are skipped: only '#n = ...;' is read."""
    ents = {}
    n = len(tokens)
    i = 0

    def value(i):
        t = tokens[i]
        c = t[0]
        if c == "#":
            return Ref(int(t[1:])), i + 1
        if c == "'":
            return t[1:-1].replace("''", "'"), i + 1
        if c == "(":
            lst = []
            i += 1
            if tokens[i] == ")":
                return lst, i + 1
            while True:
                v, i = value(i)
                lst.append(v)
                t = tokens[i]
                if t == ",":
                    i += 1
                elif t == ")":
                    return lst, i + 1
                else:
                    raise StepError("unexpected token '{0}'".format(t))
        if c == "$":
            return None, i + 1
        if c == "*":
            return DERIVED, i + 1
        if c == "." and t[-1] == "." and len(t) > 2 and not t[1].isdigit():
            return Enum(t[1:-1]), i + 1
        if c in "+-0123456789":
            if "." in t or "E" in t or "e" in t:
                return float(t), i + 1
            return int(t), i + 1
        if c == '"':
            return t[1:-1], i + 1
        if c.isalpha() or c in "_!":
            # typed parameter NAME(value)
            if i + 1 < n and tokens[i + 1] == "(":
                args, j = value(i + 1)
                return Typed(t, args), j
            return Enum(t), i + 1
        raise StepError("unexpected token '{0}'".format(t))

    while i < n:
        t = tokens[i]
        if t[0] == "#" and i + 1 < n and tokens[i + 1] == "=":
            eid = int(t[1:])
            i += 2
            parts = {}
            order = []
            try:
                if tokens[i] == "(":
                    # complex entity ( A(..) B(..) )
                    i += 1
                    while tokens[i] != ")":
                        name = tokens[i]
                        args, i = value(i + 1)
                        parts[name] = args
                        order.append(name)
                    i += 1
                else:
                    name = tokens[i]
                    args, i = value(i + 1)
                    parts[name] = args
                    order.append(name)
            except (IndexError, StepError) as e:
                raise StepError("STEP file: cannot parse entity #{0} ({1})"
                                .format(eid, e))
            ents[eid] = Entity(eid, parts, order)
            # skip to the end of the record
            while i < n and tokens[i] != ";":
                i += 1
        i += 1
    return ents


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _mul(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    L = _norm(a)
    if L == 0.0:
        raise StepError("zero-length direction")
    return [a[0] / L, a[1] / L, a[2] / L]


def _dist(a, b):
    return _norm(_sub(a, b))


# ---------------------------------------------------------------------------
# Curves (3D, coordinates already in metres)
# ---------------------------------------------------------------------------

class _Conic(object):
    """CIRCLE (a == b) or ELLIPSE: c + a cos t x + b sin t y, period 2 pi."""
    periodic = True

    def __init__(self, c, x, y, a, b):
        self.c, self.x, self.y, self.a, self.b = c, x, y, a, b

    def eval(self, t):
        return _add(self.c, _add(_mul(self.x, self.a * math.cos(t)),
                                 _mul(self.y, self.b * math.sin(t))))

    def param(self, p):
        d = _sub(p, self.c)
        return math.atan2(_dot(d, self.y) / self.b, _dot(d, self.x) / self.a)

    def range(self):
        return 0.0, 2.0 * math.pi

    def initial(self, ta, tb, tol, max_angle):
        # at most max_angle per segment and sagitta of the largest radius
        r = max(self.a, self.b)
        da = max_angle
        if tol < r:
            da = min(da, 2.0 * math.acos(1.0 - tol / r))
        nseg = max(1, int(math.ceil(abs(tb - ta) / da - 1e-9)))
        return [ta + (tb - ta) * k / float(nseg) for k in range(nseg + 1)]


class _Line(object):
    periodic = False

    def __init__(self, p, d):
        self.p, self.d = p, _unit(d)

    def eval(self, t):
        return _add(self.p, _mul(self.d, t))

    def param(self, p):
        return _dot(_sub(p, self.p), self.d)

    def range(self):
        return -1e300, 1e300

    def initial(self, ta, tb, tol, max_angle):
        return [ta, tb]


class _Polyline(object):
    periodic = False

    def __init__(self, pts):
        self.pts = pts

    def eval(self, t):
        n = len(self.pts) - 1
        k = min(max(int(math.floor(t)), 0), n - 1)
        s = t - k
        return _add(self.pts[k], _mul(_sub(self.pts[k + 1], self.pts[k]), s))

    def param(self, p):
        best, bt = None, 0.0
        for k in range(len(self.pts) - 1):
            a, b = self.pts[k], self.pts[k + 1]
            ab = _sub(b, a)
            L2 = _dot(ab, ab)
            s = 0.0 if L2 == 0.0 else min(max(_dot(_sub(p, a), ab) / L2,
                                              0.0), 1.0)
            d = _dist(p, _add(a, _mul(ab, s)))
            if best is None or d < best:
                best, bt = d, k + s
        return bt

    def range(self):
        return 0.0, float(len(self.pts) - 1)

    def initial(self, ta, tb, tol, max_angle):
        ks = [float(k) for k in range(len(self.pts)) if ta < k < tb]
        return [ta] + ks + [tb]


class _BSpline(object):
    """(Rational) B-spline curve, de Boor evaluation."""
    periodic = False

    def __init__(self, degree, cps, knots, weights=None):
        self.p = degree
        self.cps = cps
        self.U = knots
        self.w = weights
        if len(knots) != len(cps) + degree + 1:
            raise StepError("B-spline: {0} knots for {1} control points of "
                            "degree {2}".format(len(knots), len(cps), degree))

    def range(self):
        return self.U[self.p], self.U[len(self.cps)]

    def eval(self, t):
        p, U = self.p, self.U
        n = len(self.cps) - 1
        t0, t1 = self.range()
        t = min(max(t, t0), t1)
        k = p
        while k < n and U[k + 1] <= t:
            k += 1
        if self.w is None:
            d = [list(self.cps[j]) + [1.0] for j in range(k - p, k + 1)]
        else:
            d = []
            for j in range(k - p, k + 1):
                wj = self.w[j]
                c = self.cps[j]
                d.append([c[0] * wj, c[1] * wj, c[2] * wj, wj])
        for r in range(1, p + 1):
            for j in range(p, r - 1, -1):
                i = j + k - p
                den = U[i + p - r + 1] - U[i]
                a = 0.0 if den == 0.0 else (t - U[i]) / den
                d[j] = [(1.0 - a) * d[j - 1][m] + a * d[j][m]
                        for m in range(4)]
        q = d[p]
        return [q[0] / q[3], q[1] / q[3], q[2] / q[3]]

    def _spans(self):
        t0, t1 = self.range()
        ks = sorted(set(u for u in self.U if t0 <= u <= t1))
        return ks

    def param(self, p):
        # coarse search over the knot spans, then golden-section refinement
        ks = self._spans()
        cand = []
        for i in range(len(ks) - 1):
            for m in range(16):
                cand.append(ks[i] + (ks[i + 1] - ks[i]) * m / 16.0)
        cand.append(ks[-1])
        best = min(cand, key=lambda t: _dist(self.eval(t), p))
        i = cand.index(best)
        lo = cand[max(i - 1, 0)]
        hi = cand[min(i + 1, len(cand) - 1)]
        g = (math.sqrt(5.0) - 1.0) / 2.0
        for _ in range(80):
            if hi - lo < 1e-15 * max(1.0, abs(hi)):
                break
            a = hi - g * (hi - lo)
            b = lo + g * (hi - lo)
            if _dist(self.eval(a), p) < _dist(self.eval(b), p):
                hi = b
            else:
                lo = a
        t = 0.5 * (lo + hi)
        if _dist(self.eval(best), p) < _dist(self.eval(t), p):
            t = best
        return t

    def initial(self, ta, tb, tol, max_angle):
        # knots inside (ta, tb), each span divided in 4 (degree-dependent)
        ks = [u for u in self._spans() if ta < u < tb]
        brk = [ta] + ks + [tb]
        sub = max(2, 2 * self.p)
        out = []
        for i in range(len(brk) - 1):
            for m in range(sub):
                out.append(brk[i] + (brk[i + 1] - brk[i]) * m / float(sub))
        out.append(tb)
        return out


class _Reversed(object):
    """Basis curve with opposite sense (TRIMMED_CURVE sense_agreement .F.)."""

    def __init__(self, c):
        self.c = c
        self.periodic = c.periodic

    def eval(self, t):
        return self.c.eval(-t)

    def param(self, p):
        return -self.c.param(p)

    def range(self):
        a, b = self.c.range()
        return -b, -a

    def initial(self, ta, tb, tol, max_angle):
        return [-t for t in reversed(self.c.initial(-tb, -ta, tol,
                                                    max_angle))]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

_SI_PREFIX = {None: 1.0, "EXA": 1e18, "PETA": 1e15, "TERA": 1e12,
              "GIGA": 1e9, "MEGA": 1e6, "KILO": 1e3, "HECTO": 1e2,
              "DECA": 1e1, "DECI": 1e-1, "CENTI": 1e-2, "MILLI": 1e-3,
              "MICRO": 1e-6, "NANO": 1e-9, "PICO": 1e-12, "FEMTO": 1e-15,
              "ATTO": 1e-18}

# Names of conversion-based length units when the measure is missing.
_NAMED_LENGTH = {"INCH": 0.0254, "FOOT": 0.3048, "FEET": 0.3048,
                 "MILLIMETRE": 1e-3, "MILLIMETER": 1e-3, "METRE": 1.0,
                 "METER": 1.0, "CENTIMETRE": 1e-2, "YARD": 0.9144,
                 "MIL": 2.54e-5, "MILE": 1609.344}


class StepModel(object):
    def __init__(self, path):
        if not os.path.isfile(path):
            raise StepError("STEP file not found: {0}".format(path))
        f = io.open(path, "r", encoding="latin-1")
        try:
            text = f.read()
        finally:
            f.close()
        tokens = [t for t in _TOKEN_RE.findall(text) if not t.startswith("/*")]
        self.path = path
        self.ents = _parse_tokens(tokens)
        if not self.ents:
            raise StepError("no entities in STEP file {0}".format(path))
        self.scale = self._length_scale()
        self._pt = {}
        self._dir = {}
        self._curve = {}
        self._edge = {}

    # -- access ------------------------------------------------------------
    def ent(self, ref):
        try:
            return self.ents[int(ref)]
        except KeyError:
            raise StepError("STEP file: entity #{0} is missing".format(ref))

    def faces(self):
        return [e for k, e in sorted(self.ents.items())
                if e.has("ADVANCED_FACE") or e.has("FACE_SURFACE")]

    # -- units -------------------------------------------------------------
    def _unit_scale(self, ref, depth=0):
        e = self.ent(ref)
        if depth > 10:
            raise StepError("STEP: recursive unit definition #{0}"
                            .format(e.id))
        if e.has("SI_UNIT"):
            a = e.args("SI_UNIT")
            prefix = a[0] if len(a) > 1 else None
            if prefix is not None and str(prefix) not in _SI_PREFIX:
                raise StepError("STEP: unknown SI prefix .{0}. in #{1}"
                                .format(prefix, e.id))
            return _SI_PREFIX[None if prefix is None else str(prefix)]
        if e.has("CONVERSION_BASED_UNIT"):
            name, mref = e.args("CONVERSION_BASED_UNIT")[:2]
            try:
                m = self.ent(mref)
                key = [k for k in m.order if "MEASURE_WITH_UNIT" in k][0]
                vc, uref = m.args(key)[:2]
                val = vc.args[0] if isinstance(vc, Typed) else vc
                return float(val) * self._unit_scale(uref, depth + 1)
            except (StepError, IndexError, TypeError, ValueError):
                nm = str(name).upper()
                if nm in _NAMED_LENGTH:
                    return _NAMED_LENGTH[nm]
                raise StepError("STEP: cannot read length unit '{0}' (#{1})"
                                .format(name, e.id))
        raise StepError("STEP: unsupported length unit {0} (#{1})"
                        .format(e.name(), e.id))

    def _length_scale(self):
        scales = []
        for e in self.ents.values():
            if e.has("GLOBAL_UNIT_ASSIGNED_CONTEXT"):
                for r in e.args("GLOBAL_UNIT_ASSIGNED_CONTEXT")[0]:
                    if self.ent(r).has("LENGTH_UNIT"):
                        scales.append(self._unit_scale(r))
        if not scales:
            # Part 21 without unit context: assume millimetres (CAD default)
            return 1e-3
        s0 = scales[0]
        for s in scales[1:]:
            if abs(s - s0) > 1e-12 * s0:
                raise StepError("STEP file has several length units ({0}); "
                                "not supported".format(sorted(set(scales))))
        return s0

    # -- geometry ----------------------------------------------------------
    def point(self, ref):
        r = int(ref)
        p = self._pt.get(r)
        if p is None:
            e = self.ent(r)
            if e.has("CARTESIAN_POINT"):
                c = e.args("CARTESIAN_POINT")[1]
            elif e.has("VERTEX_POINT"):
                return self.point(e.args("VERTEX_POINT")[1])
            else:
                raise StepError("#{0} {1} is not a point".format(r, e.name()))
            c = [float(x) for x in c] + [0.0] * (3 - len(c))
            p = _mul(c, self.scale)
            self._pt[r] = p
        return p

    def direction(self, ref, default=None):
        if ref is None:
            return default
        r = int(ref)
        d = self._dir.get(r)
        if d is None:
            e = self.ent(r)
            if e.has("DIRECTION"):
                c = e.args("DIRECTION")[1]
            elif e.has("VECTOR"):
                return self.direction(e.args("VECTOR")[1])
            else:
                raise StepError("#{0} {1} is not a direction"
                                .format(r, e.name()))
            c = [float(x) for x in c] + [0.0] * (3 - len(c))
            d = _unit(c)
            self._dir[r] = d
        return d

    def placement(self, ref):
        """AXIS2_PLACEMENT_3D -> (origin, x, y, z)."""
        e = self.ent(ref)
        if not e.has("AXIS2_PLACEMENT_3D"):
            raise StepError("#{0} {1}: expected AXIS2_PLACEMENT_3D"
                            .format(e.id, e.name()))
        a = e.args("AXIS2_PLACEMENT_3D")
        o = self.point(a[1])
        z = self.direction(a[2] if len(a) > 2 else None, [0.0, 0.0, 1.0])
        x = self.direction(a[3] if len(a) > 3 else None, None)
        if x is None or abs(_dot(x, z)) > 1.0 - 1e-12:
            x = [1.0, 0.0, 0.0] if abs(z[0]) < 0.9 else [0.0, 1.0, 0.0]
        x = _unit(_sub(x, _mul(z, _dot(x, z))))
        y = _cross(z, x)
        return o, x, y, z

    def plane(self, face):
        """(origin, normal) of the face's PLANE, or raise with the surface
        type when it is not a plane."""
        t = "ADVANCED_FACE" if face.has("ADVANCED_FACE") else "FACE_SURFACE"
        a = face.args(t)
        s = self.ent(a[2])
        if not s.has("PLANE"):
            raise StepError("STEP face #{0} is not a plane ({1})"
                            .format(face.id, s.name()))
        o, x, y, z = self.placement(s.args("PLANE")[1])
        return o, z

    def curve(self, ref):
        r = int(ref)
        c = self._curve.get(r)
        if c is None:
            c = self._make_curve(self.ent(r))
            self._curve[r] = c
        return c

    def _make_curve(self, e):
        if e.has("SURFACE_CURVE") or e.has("SEAM_CURVE") or \
                e.has("INTERSECTION_CURVE"):
            k = [k for k in ("SURFACE_CURVE", "SEAM_CURVE",
                             "INTERSECTION_CURVE") if e.has(k)][0]
            return self.curve(e.args(k)[1])
        if e.has("LINE"):
            a = e.args("LINE")
            return _Line(self.point(a[1]), self.direction(a[2]))
        if e.has("CIRCLE"):
            a = e.args("CIRCLE")
            o, x, y, z = self.placement(a[1])
            r = float(a[2]) * self.scale
            return _Conic(o, x, y, r, r)
        if e.has("ELLIPSE"):
            a = e.args("ELLIPSE")
            o, x, y, z = self.placement(a[1])
            return _Conic(o, x, y, float(a[2]) * self.scale,
                          float(a[3]) * self.scale)
        if e.has("POLYLINE"):
            a = e.args("POLYLINE")
            return _Polyline([self.point(p) for p in a[1]])
        if e.has("TRIMMED_CURVE"):
            a = e.args("TRIMMED_CURVE")
            c = self.curve(a[1])
            # the edge vertices bound the curve; only the sense is used
            if str(a[4]) == "F":
                c = _Reversed(c)
            return c
        if e.has("B_SPLINE_CURVE_WITH_KNOTS") or e.has("B_SPLINE_CURVE"):
            return self._bspline(e)
        raise StepError("STEP: unsupported curve type {0} (#{1})"
                        .format(e.name(), e.id))

    def _bspline(self, e):
        if e.has("B_SPLINE_CURVE_WITH_KNOTS") and \
                not e.has("B_SPLINE_CURVE"):
            a = e.args("B_SPLINE_CURVE_WITH_KNOTS")
            deg, cps = int(a[1]), a[2]
            mults, kn = a[6], a[7]
        else:
            b = e.args("B_SPLINE_CURVE")
            off = 1 if len(b) >= 6 else 0      # with or without the name
            deg, cps = int(b[off]), b[off + 1]
            if e.has("B_SPLINE_CURVE_WITH_KNOTS"):
                mults, kn = e.args("B_SPLINE_CURVE_WITH_KNOTS")[:2]
            else:
                mults, kn = None, None
        pts = [self.point(p) for p in cps]
        if kn is not None:
            knots = []
            for m, u in zip(mults, kn):
                knots.extend([float(u)] * int(m))
        elif e.has("BEZIER_CURVE"):
            knots = [0.0] * (deg + 1) + [1.0] * (deg + 1)
        elif e.has("QUASI_UNIFORM_CURVE"):
            nin = len(pts) - deg - 1
            knots = [0.0] * (deg + 1) + \
                [float(k) for k in range(1, nin + 1)] + \
                [float(nin + 1)] * (deg + 1)
        elif e.has("UNIFORM_CURVE"):
            knots = [float(k - deg) for k in range(len(pts) + deg + 1)]
        else:
            raise StepError("STEP: B-spline #{0} without knots ({1})"
                            .format(e.id, e.name()))
        w = None
        if e.has("RATIONAL_B_SPLINE_CURVE"):
            w = [float(x) for x in e.args("RATIONAL_B_SPLINE_CURVE")[0]]
        return _BSpline(deg, pts, knots, w)

    # -- topology ----------------------------------------------------------
    def face_bounds(self, face):
        """[(edge_loop_entity or poly_loop, orientation_bool)] of the face;
        VERTEX_LOOPs (degenerate) are left out."""
        t = "ADVANCED_FACE" if face.has("ADVANCED_FACE") else "FACE_SURFACE"
        out = []
        for br in face.args(t)[1]:
            b = self.ent(br)
            k = "FACE_OUTER_BOUND" if b.has("FACE_OUTER_BOUND") else \
                "FACE_BOUND"
            if not b.has(k):
                raise StepError("STEP face #{0}: {1} is not a face bound"
                                .format(face.id, b.name()))
            a = b.args(k)
            loop = self.ent(a[1])
            if loop.has("VERTEX_LOOP"):
                continue
            out.append((loop, str(a[2]) != "F"))
        return out

    def loop_edges(self, loop):
        """[(edge_curve_id or None, start_key, end_key, oriented)] of an
        EDGE_LOOP in loop order; POLY_LOOP gives straight edges without id."""
        out = []
        if loop.has("POLY_LOOP"):
            pts = [int(p) for p in loop.args("POLY_LOOP")[1]]
            for i in range(len(pts)):
                out.append((None, pts[i], pts[(i + 1) % len(pts)], True))
            return out
        if not loop.has("EDGE_LOOP"):
            raise StepError("STEP: unsupported loop type {0} (#{1})"
                            .format(loop.name(), loop.id))
        for oref in loop.args("EDGE_LOOP")[1]:
            oe = self.ent(oref)
            if not oe.has("ORIENTED_EDGE"):
                raise StepError("STEP: #{0} {1} in edge loop #{2}"
                                .format(oe.id, oe.name(), loop.id))
            a = oe.args("ORIENTED_EDGE")
            ec = self.ent(a[3])
            if not ec.has("EDGE_CURVE"):
                raise StepError("STEP: unsupported edge type {0} (#{1})"
                                .format(ec.name(), ec.id))
            out.append((ec.id, None, None, str(a[4]) != "F"))
        return out

    def edge_points(self, eid, tol, max_angle):
        """Sampled points of EDGE_CURVE eid from its start vertex to its end
        vertex (edge direction), cached so that faces sharing the edge use
        exactly the same points."""
        key = (eid, tol, max_angle)
        pts = self._edge.get(key)
        if pts is not None:
            return pts
        e = self.ent(eid)
        a = e.args("EDGE_CURVE")
        v1, v2 = int(a[1]), int(a[2])
        p1, p2 = self.point(v1), self.point(v2)
        c = self.curve(a[3])
        same = str(a[4]) != "F"
        closed = (v1 == v2) or _dist(p1, p2) == 0.0
        # along the curve direction from pa to pb
        pa, pb = (p1, p2) if same else (p2, p1)
        if isinstance(c, _Line):
            pts = [p1, p2]
        else:
            pts = _sample(c, pa, pb, closed, tol, max_angle)
            if not same:
                pts.reverse()
            pts[0], pts[-1] = p1, p2
        self._edge[key] = pts
        return pts


def _sample(c, pa, pb, closed, tol, max_angle):
    """Points on curve c from pa to pb in the curve direction (pa == pb and
    closed: the full curve)."""
    t0, t1 = c.range()
    ta = c.param(pa)
    if closed:
        if c.periodic:
            tb = ta + 2.0 * math.pi
        else:
            ta, tb = t0, t1
    else:
        tb = c.param(pb)
        if c.periodic:
            while tb <= ta + 1e-12:
                tb += 2.0 * math.pi
            while tb > ta + 2.0 * math.pi + 1e-12:
                tb -= 2.0 * math.pi
    if not c.periodic and tb < ta:
        # closed non-periodic curve passing the seam: two parts
        return _sample_range(c, ta, t1, tol, max_angle)[:-1] + \
            _sample_range(c, t0, tb, tol, max_angle)
    return _sample_range(c, ta, tb, tol, max_angle)


def _sample_range(c, ta, tb, tol, max_angle):
    ts = c.initial(ta, tb, tol, max_angle)
    out = [c.eval(ts[0])]
    for i in range(len(ts) - 1):
        _refine(c, ts[i], ts[i + 1], out[-1], c.eval(ts[i + 1]), tol, out, 0)
    return out


def _refine(c, ta, tb, pa, pb, tol, out, depth):
    """Appends the points after pa up to pb, subdividing while the sagitta
    (curve midpoint to chord) is larger than tol."""
    if depth < 20 and not isinstance(c, (_Line, _Polyline)):
        tm = 0.5 * (ta + tb)
        pm = c.eval(tm)
        mid = _mul(_add(pa, pb), 0.5)
        if _dist(pm, mid) > tol:
            _refine(c, ta, tm, pa, pm, tol, out, depth + 1)
            _refine(c, tm, tb, pm, pb, tol, out, depth + 1)
            return
    out.append(pb)


# ---------------------------------------------------------------------------
# Face boundaries
# ---------------------------------------------------------------------------

# Default sampling of curved edges: sagitta at most CHORD_REL times the face
# size (bounding-box diagonal) and at most MAX_ANGLE_DEG per arc segment.
# The polygon area of a full circle is then about (dtheta^2 / 6) = 4.6e-4
# relative too small at 3 degrees; pass smaller values to face_loops_2d for
# more accurate areas (e.g. 0.5 degrees -> 1.3e-5).
CHORD_REL = 1e-4
MAX_ANGLE_DEG = 3.0


def _oriented_segments(model, faces, tol, max_angle):
    """[(edge_key, pts)] of all loops of the faces, each in the direction of
    the loop (edge orientation and bound orientation applied)."""
    segs = []
    for f in faces:
        for loop, bori in model.face_bounds(f):
            for eid, ka, kb, ori in model.loop_edges(loop):
                if eid is None:
                    pts = [model.point(ka), model.point(kb)]
                    key = ("P", min(ka, kb), max(ka, kb))
                else:
                    pts = list(model.edge_points(eid, tol, max_angle))
                    key = ("E", eid)
                if not ori:
                    pts.reverse()
                if not bori:
                    pts.reverse()
                segs.append((key, pts))
    return segs


def _face_size(model, faces):
    """Bounding-box diagonal of the faces (coarse sampling, 10 deg arcs)."""
    lo = [1e300] * 3
    hi = [-1e300] * 3
    for key, pts in _oriented_segments(model, faces, 1e300,
                                       math.radians(10.0)):
        for p in pts:
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
    if lo[0] > hi[0]:
        return 0.0
    return _dist(lo, hi)


def _chain(segs, eps, gap_tol):
    """Chains point lists (each from start to end) into closed loops. Ends
    are matched by coordinates (within eps); the direction of a segment is
    reversed if needed. Ends left without partner (defective CAD: curves
    that do not meet) are joined to the nearest free end within gap_tol by
    a straight segment. Returns ([[p, ...]] (last point not repeated),
    [(gap_length, midpoint_3d)]); raises _OpenBoundary when an end stays
    free."""
    def k(p):
        return (int(round(p[0] / eps)), int(round(p[1] / eps)),
                int(round(p[2] / eps)))

    def near_keys(p):
        a, b, c = k(p)
        for i in (a - 1, a, a + 1):
            for j in (b - 1, b, b + 1):
                for m in (c - 1, c, c + 1):
                    yield (i, j, m)

    used = [False] * len(segs)
    ends = {}
    for i, s in enumerate(segs):
        ends.setdefault(k(s[0]), []).append(i)
        ends.setdefault(k(s[-1]), []).append(i)

    def find(p, prefer_start):
        best = None
        for key in near_keys(p):
            for i in ends.get(key, ()):
                if used[i]:
                    continue
                s = segs[i]
                if _dist(s[0], p) <= eps:
                    return i, False
                if _dist(s[-1], p) <= eps and best is None:
                    best = (i, True)
        return best

    # 1. chains of exactly matching ends (closed loops or open chains)
    closed = []
    chains = []
    for i0 in range(len(segs)):
        if used[i0]:
            continue
        used[i0] = True
        loop = list(segs[i0])
        start = loop[0]
        is_closed = True
        while _dist(loop[-1], start) > eps or len(loop) < 3:
            nxt = find(loop[-1], True)
            if nxt is None:
                is_closed = False
                break
            i, rev = nxt
            used[i] = True
            s = segs[i]
            loop.extend(reversed(s[:-1]) if rev else s[1:])
        if is_closed:
            closed.append(loop[:-1])
        else:
            chains.append(loop)

    # 2. free ends: join the closest pair of ends (two chains, or the start
    # and end of one chain) while it is within gap_tol; a join longer than
    # eps is a closed gap (straight segment).
    gaps = []
    while chains:
        best = None
        nc = len(chains)
        for i in range(nc):
            ci = chains[i]
            if len(ci) >= 3:
                d = _dist(ci[-1], ci[0])
                if best is None or d < best[0]:
                    best = (d, i, i, False, False)
            for j in range(i + 1, nc):
                cj = chains[j]
                # (end of i to start of j), (end i, end j), (start i, start j),
                # (start i, end j)
                for ei in (True, False):
                    pi = ci[-1] if ei else ci[0]
                    for ej in (False, True):
                        pj = cj[-1] if ej else cj[0]
                        d = _dist(pi, pj)
                        if best is None or d < best[0]:
                            best = (d, i, j, ei, ej)
        d, i, j, ei, ej = best
        if d > gap_tol:
            break
        if i == j:
            c = chains.pop(i)
            if d > eps:
                gaps.append((d, _mul(_add(c[-1], c[0]), 0.5)))
            closed.append(c)
            continue
        ci, cj = chains[i], chains[j]
        a = ci if ei else ci[::-1]           # a ends at the joined end
        b = cj[::-1] if ej else cj           # b starts at the joined end
        if d > eps:
            gaps.append((d, _mul(_add(a[-1], b[0]), 0.5)))
            merged = a + b
        else:
            merged = a + b[1:]
        for k2 in sorted((i, j), reverse=True):
            chains.pop(k2)
        chains.append(merged)
    if chains:
        # largest of the smallest distances from a free end to another one
        worst = None
        ends_ = []
        for c in chains:
            ends_.append(c[0])
            ends_.append(c[-1])
        for m, p in enumerate(ends_):
            dmin = min([_dist(p, q) for n2, q in enumerate(ends_)
                        if n2 != m] or [0.0])
            if worst is None or dmin > worst[0]:
                worst = (dmin, p)
        raise _OpenBoundary(worst[0], worst[1])

    loops = []
    for loop in closed:
        # merge near-duplicate points
        clean = []
        for p in loop:
            if not clean or _dist(p, clean[-1]) > eps:
                clean.append(p)
        while len(clean) > 1 and _dist(clean[0], clean[-1]) <= eps:
            clean.pop()
        if len(clean) >= 3:
            loops.append(clean)
    return loops, gaps


class _OpenBoundary(Exception):
    def __init__(self, gap, point):
        Exception.__init__(self, gap)
        self.gap = gap
        self.point = point


def _g(x, digits):
    """'%g' formatting with a decimal point: IronPython's str.format uses the
    Windows locale for '{0:.4g}' (decimal comma), '%' does not."""
    return ("%." + str(digits) + "g") % x


def _area2d(loop):
    a = 0.0
    n = len(loop)
    for i in range(n):
        x1, y1 = loop[i]
        x2, y2 = loop[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return 0.5 * a


def _inside2d(pt, loop):
    x, y = pt
    c = False
    n = len(loop)
    j = n - 1
    for i in range(n):
        xi, yi = loop[i]
        xj, yj = loop[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                c = not c
        j = i
    return c


GAP_REL = 0.02         # default gap_tol relative to the face-set size


def _loops_3d(model, faces, chord_rel=None, max_angle_deg=None,
              gap_tol=None, u=None, v=None):
    """(loops_3d, size, gaps) of the union of faces; see _chain. u, v only
    serve the error message (2D position of the largest gap)."""
    if chord_rel is None:
        chord_rel = CHORD_REL
    if max_angle_deg is None:
        max_angle_deg = MAX_ANGLE_DEG
    size = _face_size(model, faces)
    if size <= 0.0:
        raise StepError("STEP: faces {0} have no boundary"
                        .format(", ".join("#{0}".format(f.id)
                                          for f in faces)))
    tol = float(chord_rel) * size
    segs = _oriented_segments(model, faces, tol,
                              math.radians(float(max_angle_deg)))
    count = {}
    for key, pts in segs:
        count[key] = count.get(key, 0) + 1
    keep = [pts for key, pts in segs if count[key] % 2 == 1]
    if gap_tol is None:
        gap_tol = GAP_REL * size
    try:
        loops, gaps = _chain(keep, 1e-9 * size + 1e-12, float(gap_tol))
    except _OpenBoundary as e:
        if u is None:
            u, v = _basis(model.plane(faces[0])[1])
        raise StepError(
            "STEP: boundary of face(s) {0} not closed, largest gap {1} mm "
            "at ({2}, {3}) mm (more than the gap tolerance "
            "{4} mm)".format(
                ", ".join("#{0}".format(f.id) for f in faces),
                _g(e.gap * 1e3, 4), _g(_dot(e.point, u) * 1e3, 6),
                _g(_dot(e.point, v) * 1e3, 6), _g(float(gap_tol) * 1e3, 4)))
    return loops, size, gaps


def _project(loops, u, v):
    return [[[_dot(p, u), _dot(p, v)] for p in lp] for lp in loops]


def _basis(n):
    n = _unit(n)
    a = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
    u = _unit(_sub(a, _mul(n, _dot(a, n))))
    return u, _cross(n, u)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

_MODELS = {}


def load(path):
    """Parsed STEP model (cached per path and modification time)."""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise StepError("STEP file not found: {0}".format(path))
    key = (path, os.path.getmtime(path))
    m = _MODELS.get(key)
    if m is None:
        m = StepModel(path)
        _MODELS.clear()
        _MODELS[key] = m
    return m


def face_ids(path):
    """STEP ids of all faces (ADVANCED_FACE / FACE_SURFACE) in file order.
    In Mecway the CAD face with surface id s (selection Surface<gg><sss>,
    preview triangle surfaceid) is face_ids(path)[s - 2] (checked with the
    PipeClip sample; NOT verified for multi-body or assembly files)."""
    return [f.id for f in load(path).faces()]


def find_faces(path, normal, offset, points, tol):
    """STEP ids of the planar faces whose PLANE is parallel to normal (either
    sign) at offset = P.normal (within tol, metres) and that contain at least
    one of points (3D, metres; exact boundary including holes)."""
    model = load(path)
    n = _unit([float(x) for x in normal])
    u, v = _basis(n)
    tol = float(tol)
    angle_tol = 1e-6
    found = []
    planes = []
    errors = []
    for f in model.faces():
        try:
            o, z = model.plane(f)
        except StepError:
            continue
        if _norm(_cross(z, n)) > angle_tol:
            continue
        d = _dot(o, n)
        planes.append((f.id, d))
        if abs(d - offset) > tol:
            continue
        try:
            loops = _project(_loops_3d(model, [f], u=u, v=v)[0], u, v)
        except StepError as e:
            # e.g. a gap beyond the tolerance: skip, report if nothing found
            errors.append(str(e))
            continue
        for p in points:
            if abs(_dot(p, n) - offset) > tol:
                continue
            q = [_dot(p, u), _dot(p, v)]
            c = 0
            for lp in loops:
                if _inside2d(q, lp):
                    c += 1
            if c % 2 == 1:
                found.append(f.id)
                break
    if not found:
        near = ", ".join("#{0} at {1} m".format(i, _g(d, 6))
                         for i, d in planes[:12])
        raise StepError(
            "no planar STEP face in {0} on the plane n=({1}, {2}, "
            "{3}), offset {4} m contains the selected points "
            "(parallel planar faces: {5})".format(
                os.path.basename(path), _g(n[0], 4), _g(n[1], 4),
                _g(n[2], 4), _g(offset, 6),
                near if near else "none") +
            ("; skipped: " + "; ".join(errors[:3]) if errors else ""))
    return found


def face_loops_2d(path, face_ids, u, v, chord_rel=None, max_angle_deg=None,
                  gap_tol=None, info=None):
    """Closed boundary loops [[x, y], ...] (metres, x = P.u, y = P.v, last
    point not repeated) of the union of the given planar faces. Edges shared
    by two of the faces cancel. Outer loops are counter-clockwise in (x, y),
    holes clockwise. chord_rel / max_angle_deg override the sampling of curved
    edges (defaults CHORD_REL, MAX_ANGLE_DEG).
    Gaps (edge ends that do not meet, defective CAD) up to gap_tol metres
    (default GAP_REL = 2 % of the face-set size) are closed with a straight
    segment; real slits are bounded by closed edge loops and are never
    touched. Larger gaps raise StepError. If info is a dict,
    info["gaps_closed"] = [[length_m, [x, y]], ...] (midpoint of each gap)."""
    model = load(path)
    u = [float(x) for x in u]
    v = [float(x) for x in v]
    faces = []
    for fid in face_ids:
        f = model.ent(fid)
        if not (f.has("ADVANCED_FACE") or f.has("FACE_SURFACE")):
            raise StepError("STEP: #{0} is not a face ({1})"
                            .format(fid, f.name()))
        model.plane(f)              # raises when not a plane
        faces.append(f)
    if not faces:
        raise StepError("STEP: no faces given")
    l3, size, gaps = _loops_3d(model, faces, chord_rel, max_angle_deg,
                               gap_tol, u, v)
    loops = _project(l3, u, v)
    if info is not None:
        info["gaps_closed"] = [[g, [_dot(p, u), _dot(p, v)]]
                               for g, p in gaps]
    out = []
    for i, lp in enumerate(loops):
        depth = 0
        for j, other in enumerate(loops):
            if i != j and _inside2d(_probe(lp), other):
                depth += 1
        a = _area2d(lp)
        if (depth % 2 == 0) != (a > 0):
            lp = lp[::-1]
        out.append(lp)
    return out


def _probe(loop):
    """A point just inside the loop near its first edge (for nesting)."""
    (x1, y1), (x2, y2) = loop[0], loop[1]
    mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
    dx, dy = x2 - x1, y2 - y1
    L = math.sqrt(dx * dx + dy * dy) or 1.0
    s = 1e-7 * L
    a = _area2d(loop)
    sgn = 1.0 if a > 0 else -1.0
    return [mx - sgn * dy / L * s, my + sgn * dx / L * s]


def loops_area(loops):
    """Signed area sum of 2D loops (outer CCW positive, holes negative)."""
    return sum(_area2d(lp) for lp in loops)
