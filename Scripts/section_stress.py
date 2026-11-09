# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_stress.py
# Stress at every point of a beam section from the six section forces.
# CPython 3 with numpy and scipy only; NOT in IronPython.
#
# THEORY: Saint-Venant, prismatic beam, linear elastic: W.D. Pilkey, "Analysis
# and Design of Elastic Beams: Computational Methods", Wiley 2002. The fields
# come from section_fem.py (a copy of MecwaySectionProps, see AGENTS.md).
#
# AXES: V and W are the section axes of Mecway (principal axes when the shape
# comes from SECTIE-VORM), U = V x W along the beam, section forces on the +U
# face. section_fem works in x, y with torque about z = x cross y, so x = V,
# y = W, z = U.
#
# SECTION FORCES, measured on Mecway 35 and Code-Aster 17.4 (research note
# docs/research/01_vooronderzoek.md, par. 7):
#   N   int(sigma)              tensileforce  (N)
#   Vv  int(tau_uv)             sheary        (VY)
#   Vw  int(tau_uw)             shearz        (VZ)
#   T   torque about +U         torsion       (MT), about the beam line
#   Mv  int(w sigma)            bendingmomv   (MFY)
#   Mw  -int(v sigma)           bendingmomw   (MFZ)
#
#   sigma = N/A + (Mv Iww + Mw Ivw) w / D - (Mw Ivv + Mv Ivw) v / D
#   D = Ivv Iww - Ivw^2,  Ivv = int(w^2), Iww = int(v^2), Ivw = int(v w)
#   (Ivv is Mecway's iyy, Iww its izz)
#
#   tau = Vv tau_vv + Vw tau_vw + T_S tau_t
#   T_S = T + EY Vw - EZ Vv,  (EY, EZ) = vector shear centre -> centroid
#
# The shear fields act through the shear centre S and solvers report T about
# the beam line, which is the centroid: without T_S the stress in an open
# section does not balance the forces. Measured on POU_D_E, POU_D_T and
# POU_D_TG, 120 cases, 4.5e-8.
#
# PROPERTIES: sigma uses the section properties of the solver when they are
# given, so that it fits the equilibrium of the solver; a shape rounded by
# SECTIE-VORM has slightly other properties. The tau fields come from the mesh
# and are normalised on a unit resultant, so they balance V and T exactly.
#
# RE-ENTRANT CORNERS: the exact stress is infinite in a sharp re-entrant corner,
# so the peak there grows with the mesh and means nothing. Zones of radius
# 1 x the local thickness around such corners are left out of "maximum outside
# corners". A rule of thumb, measured on an I section (about 2 % mesh
# dependence), see mesh_sensitivity. Coordinates of the loops are about the
# centroid of the solver (section_profiles, SECTIE-VORM); the result uses the
# centroid of the mesh, which differs from it by rounding only.
#
#   SectionField(loops, nu, ...)    mesh, unit fields, corners
#   field.stress(forces, ...)       sigma, tau_v, tau_w per element node
#   measures(s)                     von Mises, Tresca, principal, tau
#   field.extremes(values)          maximum overall and outside the corners
#   field.resultants(s)             the six forces back, by integration
#   field.nodal(values)             averaged per node, for drawing
#   mesh_sensitivity(...)           the maximum on two meshes

import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import section_fem  # noqa: E402
import section_mesh  # noqa: E402

FORCES = ("N", "Vv", "Vw", "T", "Mv", "Mw")
# A corner counts as re-entrant when the interior angle exceeds this.
REENTRANT_MIN_DEG = 200.0
# A fillet has no singularity: a turn below this angle next to a facet shorter
# than FILLET_FACET x the local thickness is a facet of a rounded corner.
FILLET_TURN_DEG = 45.0
FILLET_FACET = 1.5
CORNER_ZONE_FACTOR = 1.0


class SectionError(Exception):
    """A section that cannot be calculated. code: for the window, which holds
    the text in both languages; detail: technical, for the log."""

    def __init__(self, code, detail=""):
        Exception.__init__(self, "{0}: {1}".format(code, detail))
        self.code = code
        self.detail = detail


def _tri6_shape(z):
    z1, z2, z3 = z
    return np.array([z1 * (2 * z1 - 1), z2 * (2 * z2 - 1), z3 * (2 * z3 - 1),
                     4 * z1 * z2, 4 * z2 * z3, 4 * z3 * z1])


def _distance_to_segments(p, a, b):
    """Distance of point p to the segments a[i]-b[i]."""
    d = b - a
    den = np.einsum("ij,ij->i", d, d)
    den = np.where(den == 0.0, 1.0, den)
    t = np.clip(np.einsum("ij,ij->i", p - a, d) / den, 0.0, 1.0)
    q = a + t[:, None] * d
    return np.hypot(p[0] - q[:, 0], p[1] - q[:, 1])


def reentrant_corners(loops):
    """[(point, local thickness)] of the sharp re-entrant corners of the
    material. loops: the cleaned loops of section_mesh.mesh_section, with the
    material on the left of the walking direction and no double points. The
    local thickness is the distance from the corner to the nearest boundary
    segment that does not touch the corner."""
    loops = [np.asarray(l, dtype=float) for l in loops]
    pa = np.vstack(loops)
    pb = np.vstack([np.roll(l, -1, axis=0) for l in loops])
    out = []
    start = 0
    for lp in loops:
        n = len(lp)
        for i in range(n):
            p, q, r = lp[i - 1], lp[i], lp[(i + 1) % n]
            a, b = q - p, r - q
            turn = math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], float(np.dot(a, b))))
            interior = 180.0 - turn         # material on the left
            if interior < REENTRANT_MIN_DEG:
                continue
            dist = _distance_to_segments(q, pa, pb)
            dist[start + i] = np.inf                    # segment leaving q
            dist[start + (i - 1) % n] = np.inf          # segment arriving at q
            thick = float(dist.min())
            facet = min(float(np.hypot(*a)), float(np.hypot(*b)))
            if interior - 180.0 < FILLET_TURN_DEG and facet < FILLET_FACET * thick:
                continue
            out.append((q.copy(), thick))
        start += n
    return out


class SectionField(object):
    """Mesh and unit fields of one section, for one Poisson ratio.

    loops   closed loops in V, W (metres), even-odd interior
    nu      Poisson ratio
    props   optional {"A", "ivv", "iww", "ivw"} of the solver, for sigma
    offset  optional (EY, EZ) of the solver, for T_S; default from the mesh
    The coordinates of the result are relative to the centroid of the mesh.
    """

    def __init__(self, loops, nu=0.3, props=None, offset=None, n_target=3000,
                 n_across=3.0):
        self.loops_in = [np.asarray(l, dtype=float) for l in loops]
        self.nu = float(nu)
        try:
            mesh = section_mesh.mesh_section([l.tolist() for l in self.loops_in],
                                             n_target=n_target, n_across=n_across)
        except section_mesh.MeshError as exc:
            raise SectionError("mesh_failed", str(exc))
        self.loops = mesh["loops"]
        self.nodes = np.asarray(mesh["nodes"], dtype=float)
        self.elements = np.asarray(mesh["elements"], dtype=int)
        self.geo = section_fem.geometric_properties(self.nodes, self.elements)
        self.centroid = np.array(self.geo["centroid"], dtype=float)
        self.xy = self.nodes - self.centroid
        self.mesh_props = {"A": self.geo["area"], "ivv": self.geo["ixx_c"],
                           "iww": self.geo["iyy_c"], "ivw": self.geo["ixy_c"]}
        self.props = dict(props) if props else dict(self.mesh_props)
        try:
            p = self.props
            ok = (p["A"] > 0.0 and p["ivv"] > 0.0 and p["iww"] > 0.0 and
                  p["ivv"] * p["iww"] - p["ivw"] ** 2 > 0.0)
        except KeyError as exc:
            raise SectionError("bad_properties", str(exc))
        if not ok:
            raise SectionError("bad_properties", str(p))
        self._node_vw = self.xy[self.elements]          # (E,6,2)
        self._weights()
        self.parts = int(section_mesh.element_parts(self.elements)[0])
        self.warnings = []
        self.fields = None
        self.j = None
        self.warping_length = None
        self.shear_centre = None
        self.offset = None
        if self.parts == 1:
            try:
                wp = section_fem.warping_properties(self.nodes, self.elements, self.geo,
                                                    nu=self.nu)
            except ValueError as exc:
                raise SectionError("warping_failed", str(exc))
            f = section_fem.shear_fields(self.nodes, self.elements, self.geo, wp,
                                         nu=self.nu)
            self.fields = {"t": f["torsion"], "vv": f["vx"], "vw": f["vy"]}
            self.j = wp["j"]
            # 1/k of restrained warping: sqrt(E Iw / (G J)). Measured on solid
            # models: a section closer than about 4 of these to a clamp or a
            # load introduction carries a bimoment that beam theory has not.
            self.warping_length = math.sqrt(2.0 * (1.0 + self.nu) * abs(wp["gamma"]) / self.j)
            self.shear_centre = np.array(wp["shear_centre"]) - self.centroid
            self.offset = (-self.shear_centre[0], -self.shear_centre[1])
            if offset is not None:
                self.offset = (float(offset[0]), float(offset[1]))
        else:
            self.warnings.append("separate_parts")
        self._corner_mask()

    def _weights(self):
        """Gauss weights (E,G) and interpolation matrix (G,6)."""
        X = self.xy[self.elements[:, :3]]
        x, y = X[:, :, 0], X[:, :, 1]
        a2 = ((x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0]) -
              (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0]))
        g = section_fem.GAUSS6
        self._gw = 0.5 * a2[:, None] * g[:, 3][None, :]
        self._gN = np.array([_tri6_shape(z) for z in g[:, :3]])
        self.element_area = 0.5 * a2

    def _corner_mask(self):
        """Mask (E,6): True for element nodes outside the corner zones."""
        self.corners = [(p - self.centroid, t) for p, t in reentrant_corners(self.loops)]
        keep = np.ones(self.elements.shape, dtype=bool)
        for p, t in self.corners:
            d = np.hypot(self._node_vw[:, :, 0] - p[0], self._node_vw[:, :, 1] - p[1])
            keep &= d > CORNER_ZONE_FACTOR * t
        self.outside = keep

    # ---------------------------------------------------------------- stress
    def torque_at_shear_centre(self, forces, about_shear_centre=False):
        """T_S from the torque T about the beam line. about_shear_centre: T is
        already about S (no conversion). Returns (T_S, the term added)."""
        t = float(forces.get("T", 0.0))
        if about_shear_centre or self.offset is None:
            return t, 0.0
        ey, ez = self.offset
        term = ey * float(forces.get("Vw", 0.0)) - ez * float(forces.get("Vv", 0.0))
        return t + term, term

    def stress(self, forces, about_shear_centre=False):
        """{"sigma", "tau_v", "tau_w"} arrays (E,6) at the element nodes for
        forces {N, Vv, Vw, T, Mv, Mw} (missing = 0). tau_* are None for a
        section of several parts, which has no shear fields."""
        n = float(forces.get("N", 0.0))
        mv = float(forces.get("Mv", 0.0))
        mw = float(forces.get("Mw", 0.0))
        p = self.props
        d = p["ivv"] * p["iww"] - p["ivw"] ** 2
        v, w = self._node_vw[:, :, 0], self._node_vw[:, :, 1]
        sigma = (n / p["A"] + (mv * p["iww"] + mw * p["ivw"]) * w / d -
                 (mw * p["ivv"] + mv * p["ivw"]) * v / d)
        if self.fields is None:
            return {"sigma": sigma, "tau_v": None, "tau_w": None}
        ts, _ = self.torque_at_shear_centre(forces, about_shear_centre)
        vv, vw = float(forces.get("Vv", 0.0)), float(forces.get("Vw", 0.0))
        f = self.fields
        tau = vv * f["vv"] + vw * f["vw"] + ts * f["t"]
        return {"sigma": sigma, "tau_v": tau[:, :, 0], "tau_w": tau[:, :, 1]}

    def resultants(self, s):
        """The section forces of a stress state by integration over the mesh:
        {N, Mv, Mw, Vv, Vw, Tc}, Tc = torque about the centroid."""
        gw, gN = self._gw, self._gN
        sig = np.einsum("gi,ei->eg", gN, s["sigma"])
        v = np.einsum("gi,ei->eg", gN, self._node_vw[:, :, 0])
        w = np.einsum("gi,ei->eg", gN, self._node_vw[:, :, 1])
        out = {"N": float(np.sum(gw * sig)), "Mv": float(np.sum(gw * sig * w)),
               "Mw": float(-np.sum(gw * sig * v))}
        if s.get("tau_v") is not None:
            tv = np.einsum("gi,ei->eg", gN, s["tau_v"])
            tw = np.einsum("gi,ei->eg", gN, s["tau_w"])
            out["Vv"] = float(np.sum(gw * tv))
            out["Vw"] = float(np.sum(gw * tw))
            out["Tc"] = float(np.sum(gw * (v * tw - w * tv)))
        return out

    def extremes(self, values):
        """Largest absolute value overall and outside the corner zones, each
        {"value", "point"} (signed value, V, W relative to the centroid).
        "outside_empty": no node lies outside the zones, then "outside" is the
        overall value."""
        def pick(mask):
            vals = np.where(mask & np.isfinite(values), np.abs(values), -1.0)
            i = int(np.argmax(vals))
            e, k = np.unravel_index(i, values.shape)
            return {"value": float(values[e, k]),
                    "point": self._node_vw[e, k].tolist()}
        all_ = pick(np.ones(values.shape, dtype=bool))
        empty = not self.outside.any()
        return {"overall": all_, "outside": all_ if empty else pick(self.outside),
                "outside_empty": empty}

    def nodal(self, values):
        """Element-node values averaged per node, weighted by element area."""
        n = len(self.nodes)
        wgt = np.repeat(np.abs(self.element_area)[:, None], 6, axis=1)
        sw = np.bincount(self.elements.ravel(), weights=wgt.ravel(), minlength=n)
        sv = np.bincount(self.elements.ravel(), weights=(wgt * values).ravel(), minlength=n)
        return sv / np.where(sw > 0.0, sw, 1.0)


def measures(s):
    """Derived values per element node, from {"sigma", "tau_v", "tau_w"}.
    Beam theory: the other stress components are zero. Without shear fields
    only the longitudinal stress exists."""
    sig = s["sigma"]
    out = {"sigma": sig}
    if s.get("tau_v") is None:
        return out
    tv, tw = s["tau_v"], s["tau_w"]
    tau = np.hypot(tv, tw)
    r = np.sqrt(0.25 * sig ** 2 + tau ** 2)
    out.update({"tau_v": tv, "tau_w": tw, "tau": tau,
                "vonmises": np.sqrt(sig ** 2 + 3.0 * tau ** 2),
                "tresca": 2.0 * r,
                "principal1": 0.5 * sig + r,
                "principal2": 0.5 * sig - r})
    return out


def mesh_sensitivity(field, forces, measure="vonmises", about_shear_centre=False):
    """Maximum outside the corners of field and of a mesh four times as fine:
    (this mesh, finer mesh, relative difference). A check for the tests; the window
    does not call it."""
    def largest(f):
        s_ = f.stress(forces, about_shear_centre)
        return abs(f.extremes(measures(s_)[measure])["outside"]["value"])
    fine = SectionField(field.loops_in, nu=field.nu, props=field.props, offset=field.offset,
                        n_target=4 * len(field.elements))
    a, b = largest(field), largest(fine)
    return a, b, (abs(a - b) / b if b else 0.0)
