# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_warping.py
# Beams with warping: elem_beam = POU_D_TG (STAPPENPLAN S19, KNOWN_BUGS 115).
#
# Code-Aster's POU_D_TG is a Timoshenko beam with a 7th degree of freedom
# GRX per node (the warping, the derivative of the twist: test case
# ssll102c "LE DDL GRX VAUT DRX/L"), the shear (torsion) centre outside the
# centroid (EY, EZ) and the warping constant JG; its RIGI_GEOM couples the
# axial force and the bending moments with the twist about the shear centre
# (Wagner terms IYR2, IZR2), so that flexural-torsional and lateral-torsional
# buckling of open sections appear (test case ssll103a: angle 120 x 120 x 8,
# flexural-torsional buckling with POU_D_TG). U4.42.01 par. 9.4.3 (v17.4
# catalogue affe_cara_elem.py): AY, AZ, EY, EZ, JG, IYR2, IZR2 for
# SECTION='GENERALE'; EY/EZ = the components of the vector shear centre ->
# centroid ("composante de CG") in the principal axes.
#
# This module has two parts:
#   1. section_props(): EY, EZ, JG, IYR2, IZR2 of Mecway's I, T, C and L
#      profiles (dimensions as bridge_from_liml._profile_props), in the
#      local axes of the bridge (y = Mecway's V, z = W; for L the principal
#      axes of _profile_props).
#   2. warping_nodes(): the nodes where GRX = 0 (setting beam_warping),
#      called by bridge_mesh.write_mesh, which writes them as node group
#      WARP_GROUP; bridge_to_aster._build_charges adds DDL_IMPO GRX = 0.
#
# Compatible with IronPython 2.7.9 (stdlib only).

import math

from bridge_utils import log, tr, CONFIG_BRIDGE

WARP_BEAM = "POU_D_TG"
# Node group with GRX = 0 (letters/digits, <= 24 characters)
WARP_GROUP = "BRGRX"
# Choices of the setting beam_warping (the first is the default)
WARP_CHOICES = ("auto", "free", "blocked")
_ROT = ("DRX", "DRY", "DRZ")
# Conditions that hold a node kinematically (bridge_bcs tag names)
_KINEMATIC = ("fixed", "pinnedsupport", "displacement", "noderotation",
              "velocity", "symmetry", "frictionless")
# A fixed rotation axis counts as the twist when it lies along the beam
# axis within this cosine (about 0.8 degrees)
_ALONG = 1.0 - 1.0e-4


# ==========================================
# 1. SECTION PROPERTIES OF THIN-WALLED PROFILES
# ==========================================
# Method (thin-walled open sections, Vlasov; Trahair, Flexural-Torsional
# Buckling of Structures, 1993, ch. 2 and app.; Timoshenko & Gere, Theory
# of Elastic Stability, 2nd ed., 1961, par. 5.1-5.3): the profile as
# straight centre-line segments (a tree), the sectorial coordinate
# omega(s) = int (r x dr) from the centroid, the shear centre S as the
# pole for which int omega y dA = int omega z dA = 0, the warping constant
# C_w = int (omega_S - mean)^2 dA plus the thickness (secondary) warping
# of each segment t^3/12 int ((p - S) . e_s)^2 ds. Checks (offline):
#   - I 100/50/10/8 mm: primary C_w = t_f b^3 h^2/24 = 4.219e-10 m^6
#     (+1.0 % secondary), S in the centroid;
#   - C 100 x 50 x 6 mm: primary C_w 4.0135e-10 m^6 = t b^3 h^2/12
#     (3b + 2h)/(6b + h) (Timoshenko & Gere 1961 par. 5.3 / Roark), shear
#     centre 29.33 mm from the centroid (closed form on the centre line
#     e + x_c = 29.375 mm);
#   - L 120 x 120 x 8 mm: C_w = 4.43988e-11 m^6 and IYR2 = 8.4848e-8 m^5,
#     shear centre 40.96 mm from the centroid: Code-Aster test case
#     ssll103a gives JG = 44398819 mm^6, IYR2 = 84948392 mm^5, EY = 41.012
#     mm (positive EY with positive IYR2, as here).
# A, IY, IZ, JX stay those of _profile_props (Mecway's values); the Wagner
# integrals IYR2 = int y (y^2 + z^2) dA and IZR2 = int z (y^2 + z^2) dA
# (U4.42.01 par. 9.4.3; about the centroid, principal axes) are exact over
# the rectangles of the profile.

_GAUSS = (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))


def _rects(kind, a, b, c, d):
    """Rectangles (x0, x1, y0, y1) of the drawing (x horizontal = W,
    y vertical = V), as bridge_from_liml._profile_props."""
    if kind == "I":
        return [(0.0, b, 0.0, c), (0.0, b, a - c, a),
                ((b - d) / 2.0, (b + d) / 2.0, c, a - c)]
    if kind == "T":
        return [(0.0, a, d, d + c), ((a - b) / 2.0, (a + b) / 2.0, 0.0, d)]
    if kind == "C":
        return [(0.0, a, 0.0, c), (0.0, a, b - c, b), (0.0, d, c, b - c)]
    return [(0.0, a, 0.0, c), (0.0, c, c, b)]          # L


def _segments(kind, a, b, c, d):
    """Centre-line segments ((x0, y0), (x1, y1), t) of the drawing."""
    if kind == "I":
        yb, yt, xm = c / 2.0, a - c / 2.0, b / 2.0
        return [((xm, yb), (0.0, yb), c), ((xm, yb), (b, yb), c),
                ((xm, yt), (0.0, yt), c), ((xm, yt), (b, yt), c),
                ((xm, yb), (xm, yt), d)]
    if kind == "T":
        yf, xm = d + c / 2.0, a / 2.0
        return [((xm, yf), (0.0, yf), c), ((xm, yf), (a, yf), c),
                ((xm, yf), (xm, 0.0), b)]
    if kind == "C":
        xw, yb, yt = d / 2.0, c / 2.0, b - c / 2.0
        return [((xw, yb), (xw, yt), d), ((xw, yb), (a, yb), c),
                ((xw, yt), (a, yt), c)]
    h = c / 2.0                                        # L
    return [((h, h), (a, h), c), ((h, h), (h, b), c)]


def _lin(f0, f1, g0, g1):
    """int f g ds / L for f, g linear on a segment."""
    return (2.0 * f0 * g0 + f0 * g1 + f1 * g0 + 2.0 * f1 * g1) / 6.0


def section_props(kind, a, b, c, d):
    """
    {"EY", "EZ", "JG", "IYR2", "IZR2"} of an I, T, C or L profile (unit of
    the dimensions, SI if they are in m), or None for another kind or
    impossible dimensions. Local y = V (vertical in Mecway's drawing), z = W
    (horizontal, +z = to the right in the drawing: as the beam sidecar
    bridge_beams; whether Mecway's W points that way is NOT verified, it
    only changes the sign of EZ and IZR2 of C and L profiles, not a
    buckling load under axial force); L in the principal axes of
    _profile_props (V at theta to leg b).
    """
    if kind not in ("I", "T", "C", "L") or min(a, b, c) <= 0.0 or (
            kind != "L" and d <= 0.0):
        return None
    rects = _rects(kind, a, b, c, d)
    area = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in rects)
    if area <= 0.0:
        return None
    cx = sum((x1 - x0) * (y1 - y0) * (x0 + x1) / 2.0
             for x0, x1, y0, y1 in rects) / area
    cy = sum((x1 - x0) * (y1 - y0) * (y0 + y1) / 2.0
             for x0, x1, y0, y1 in rects) / area
    theta = 0.0
    if kind == "L":
        i_w = i_v = i_vw = 0.0
        for x0, x1, y0, y1 in rects:
            w, h = x1 - x0, y1 - y0
            dx, dy = (x0 + x1) / 2.0 - cx, (y0 + y1) / 2.0 - cy
            i_w += w * h ** 3 / 12.0 + w * h * dy * dy
            i_v += h * w ** 3 / 12.0 + w * h * dx * dx
            i_vw += w * h * dx * dy
        theta = 0.5 * math.atan2(-2.0 * i_vw, i_w - i_v)
    sn, cs = math.sin(theta), math.cos(theta)

    def loc(x, y):
        """Drawing point -> local (y, z): V' = (-sin, cos), W' = (cos, sin)
        (the I about V' is i_pv of _profile_props)."""
        dx, dy = x - cx, y - cy
        return (-sn * dx + cs * dy, cs * dx + sn * dy)

    # Wagner integrals, exact (cubic) with 2 x 2 Gauss points per rectangle
    iyr2 = izr2 = 0.0
    for x0, x1, y0, y1 in rects:
        jac = (x1 - x0) * (y1 - y0) / 4.0
        for gx in _GAUSS:
            for gy in _GAUSS:
                yl, zl = loc((x0 + x1) / 2.0 + gx * (x1 - x0) / 2.0,
                             (y0 + y1) / 2.0 + gy * (y1 - y0) / 2.0)
                r2 = yl * yl + zl * zl
                iyr2 += jac * yl * r2
                izr2 += jac * zl * r2

    # Sectorial coordinate along the centre-line tree (pole = centroid)
    segs = [(loc(*p0), loc(*p1), t)
            for p0, p1, t in _segments(kind, a, b, c, d)]

    def key(p):
        return (round(p[0], 12), round(p[1], 12))

    omega = {key(segs[0][0]): 0.0}
    todo = list(segs)
    walked = []
    while todo:
        for seg in todo:
            p0, p1, t = seg
            swept = p0[0] * p1[1] - p0[1] * p1[0]
            if key(p0) in omega:
                w0 = omega[key(p0)]
                w1 = omega.setdefault(key(p1), w0 + swept)
            elif key(p1) in omega:
                w1 = omega[key(p1)]
                w0 = omega.setdefault(key(p0), w1 - swept)
            else:
                continue
            walked.append((p0, p1, t, w0, w1))
            todo.remove(seg)
            break
        else:
            return None
    s = dict.fromkeys(("A", "w", "y", "z", "wy", "wz", "yy", "zz", "yz"),
                      0.0)
    for p0, p1, t, w0, w1 in walked:
        tl = t * math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        s["A"] += tl
        s["w"] += tl * (w0 + w1) / 2.0
        s["y"] += tl * (p0[0] + p1[0]) / 2.0
        s["z"] += tl * (p0[1] + p1[1]) / 2.0
        s["wy"] += tl * _lin(w0, w1, p0[0], p1[0])
        s["wz"] += tl * _lin(w0, w1, p0[1], p1[1])
        s["yy"] += tl * _lin(p0[0], p1[0], p0[0], p1[0])
        s["zz"] += tl * _lin(p0[1], p1[1], p0[1], p1[1])
        s["yz"] += tl * _lin(p0[0], p1[0], p0[1], p1[1])

    def cov(u, v):
        return s[u + v] - s[u] * s[v] / s["A"]

    # Pole Q: omega_Q = omega - y_Q z + z_Q y + const; shear centre where
    # cov(omega_Q, y) = cov(omega_Q, z) = 0
    a11, a12, b1 = -cov("y", "z"), cov("y", "y"), -cov("w", "y")
    a21, a22, b2 = -cov("z", "z"), cov("y", "z"), -cov("w", "z")
    det = a11 * a22 - a12 * a21
    if abs(det) < 1e-300:
        return None
    y_s = (b1 * a22 - a12 * b2) / det
    z_s = (a11 * b2 - a21 * b1) / det
    tot = mean = sq = secondary = 0.0
    for p0, p1, t, w0, w1 in walked:
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        q0 = w0 - y_s * p0[1] + z_s * p0[0]
        q1 = w1 - y_s * p1[1] + z_s * p1[0]
        tot += t * length
        mean += t * length * (q0 + q1) / 2.0
        sq += t * length * _lin(q0, q1, q0, q1)
        e = ((p1[0] - p0[0]) / length, (p1[1] - p0[1]) / length)
        r0 = (p0[0] - y_s) * e[0] + (p0[1] - z_s) * e[1]
        r1 = (p1[0] - y_s) * e[0] + (p1[1] - z_s) * e[1]
        secondary += t ** 3 / 12.0 * length * _lin(r0, r1, r0, r1)
    c_w = max(sq - mean * mean / tot, 0.0) + secondary
    # round-off of a symmetric profile -> exactly 0
    def clean(v, scale):
        return 0.0 if abs(v) < 1e-9 * scale else v

    return {"EY": clean(-y_s, math.sqrt(area)),
            "EZ": clean(-z_s, math.sqrt(area)), "JG": c_w,
            "IYR2": clean(iyr2, area ** 2.5),
            "IZR2": clean(izr2, area ** 2.5)}


_WARP_KEYS = ("EY", "EZ", "JG", "IYR2", "IZR2")


def add_warping(elset_name, geom):
    """
    Section of a POU_D_TG elset: GENERALE gets EY, EZ, JG, IYR2, IZR2 (those
    that are not in it yet). Source: #ASTER-SECTIE (MecwaySectionProps,
    "section_extras"; EY/EZ are already in cara from
    bridge_from_liml._apply_section_extras), else section_props() of an
    I/T/C/L profile, else 0 with a WARNING (general section without
    #ASTER-SECTIE). RECTANGLE and CERCLE stay as they are (doubly symmetric,
    shear centre in the centroid; JG not given = 0, the warping of these
    compact or closed sections is negligible). Returns a new dict.
    """
    if geom.get("aster_section") != "GENERALE":
        log("INFO: Beam elset '{0}' ({1}, POU_D_TG): section {2}, shear "
            "centre in the centroid, no warping constant (JG = 0).".format(
                elset_name, geom.get("geom_type", "?"),
                geom.get("aster_section")))
        return geom
    have = set(geom["cara"])
    extras = geom.get("section_extras") or {}
    profile = geom.get("profile") or {}
    values, source = {}, None
    if extras:
        values = dict((k, extras[k]) for k in _WARP_KEYS if k in extras)
        source = "#ASTER-SECTIE (MecwaySectionProps)"
        missing = [k for k in ("JG",) if k not in extras]
        if missing:
            log(tr("WARNING: Balk-elset '{0}' (POU_D_TG): #ASTER-SECTIE "
                   "heeft geen JG; welvingsconstante 0 (geen "
                   "welvingsstijfheid). Maak de regel opnieuw met "
                   "MecwaySectionProps.",
                   "WARNING: Beam elset '{0}' (POU_D_TG): #ASTER-SECTIE "
                   "has no JG; warping constant 0 (no warping stiffness). "
                   "Create the line again with MecwaySectionProps.").format(
                       elset_name))
    elif profile.get("shape") in ("I", "T", "C", "L"):
        values = section_props(profile["shape"], profile["a"], profile["b"],
                               profile["c"], profile["d"]) or {}
        source = "thin-walled formulas, bridge_warping.section_props"
    if not values:
        log(tr("WARNING: Balk-elset '{0}' ({1}, POU_D_TG): geen "
               "welvingsconstante en geen dwarskrachtcentrum bekend; JG = "
               "0, EY = EZ = 0. Torsie dan om het zwaartepunt zonder "
               "welvingsstijfheid, zodat buig-torsieknik en kipknik van "
               "open profielen te hoog kunnen uitvallen. Geef de waarden "
               "met een #ASTER-SECTIE-regel (MecwaySectionProps) of kies "
               "een I-, T-, C- of L-profiel in Mecway.",
               "WARNING: Beam elset '{0}' ({1}, POU_D_TG): no warping "
               "constant and no shear centre known; JG = 0, EY = EZ = 0. "
               "Torsion is then about the centroid without warping "
               "stiffness, so flexural-torsional and lateral-torsional "
               "buckling of open sections can come out too high. Give the "
               "values with an #ASTER-SECTIE line (MecwaySectionProps) or "
               "choose an I, T, C or L profile in Mecway.").format(
                   elset_name, geom.get("geom_type", "?")))
        return geom
    keys = [k for k in _WARP_KEYS if k in values and k not in have]
    new = dict(geom)
    new["cara"] = tuple(geom["cara"]) + tuple(keys)
    new["vale"] = tuple(geom["vale"]) + tuple(values[k] for k in keys)
    cara = dict(zip(new["cara"], new["vale"]))
    # %-formatting: "{0:.4g}" follows the locale in IronPython (comma)
    log("INFO: Beam elset '{0}' ({1}, POU_D_TG): EY={2} m, EZ={3} m, "
        "JG={4} m6, IYR2={5} m5, IZR2={6} m5 ({7}).".format(
            elset_name, geom.get("geom_type", "?"),
            "%.5g" % cara.get("EY", 0.0), "%.5g" % cara.get("EZ", 0.0),
            "%.5g" % cara.get("JG", 0.0), "%.5g" % cara.get("IYR2", 0.0),
            "%.5g" % cara.get("IZR2", 0.0), source))
    return new


# ==========================================
# 2. WARPING AT SUPPORTS (GRX = 0)
# ==========================================
# Mecway has no warping degree of freedom, so the bridge decides where the
# warping is restrained (user's decision 16 Oct 2026, STAPPENPLAN S19;
# setting beam_warping):
#   auto    (default) GRX = 0 at a node of a POU_D_TG beam where a rotation
#           about an axis across that beam is fixed: Fixed support, Node
#           rotation or Displacement/symmetry that fixes a bending rotation,
#           a rigid (rigidbody/RBE2) coupling. Free where only translations
#           and/or the rotation about the beam axis are fixed (a fork
#           support, Pinned support) and at all other nodes. A clamped end
#           restrains the warping of the flanges, a fork support does not
#           (Timoshenko & Gere 1961 par. 6.2 and 5.4; Trahair 1993 ch. 3).
#   free    GRX free everywhere (also at a Fixed support).
#   blocked GRX = 0 at every node of a POU_D_TG beam that has a kinematic
#           condition (also pinned and fork supports).
# Fixed support = DDL_IMPO BLOCAGE=('DEPLACEMENT', 'ROTATION'), which does
# NOT fix GRX (run 28 Oct 2026, C column of BU-35 with POU_D_TG: 343.8
# with BLOCAGE alone, 385.0 with an extra GRX = 0), hence the own group.


def note_reactions(analysis):
    """
    WARNING for POU_D_TG beams when the analysis sends reactions to Mecway.
    Measured with Code-Aster 17.4 (28 Oct 2026, cantilever L = 1 m, 10
    elements, CERCLE R = 10 mm, 100 N at the tip): REAC_NODA of POU_D_TG has
    spurious nodal values, -3.0 N at the loaded tip and -0.30 N m at every
    node (support 103.0 N), proportional to the shear flexibility (AY):
    POU_D_T gives 100.0 exactly, POU_D_TG with AY = AZ = 1e-6 also. The
    displacements, the section forces (EFGE_ELNO, verification LS-30 with
    POU_D_TG) and the sum of all reactions (BRIDGE_STATREAC) are right. The
    cause inside Code-Aster (FORC_NODA of MECA_POU_D_TG) is NOT verified.
    """
    fields = (analysis or {}).get("fields") or []
    if "reactions" not in fields:
        return
    log(tr("WARNING: Balken POU_D_TG: Code-Aster 17.4 geeft bij dit element "
           "reactiekrachten per knoop met een fout die met de "
           "afschuifvervorming groeit (gemeten: 3% bij de inklemming van "
           "een ronde ligger van 10 elementen, en kleine reactiemomenten in "
           "vrije knopen). Verplaatsingen, snedekrachten (beam_forces) en de "
           "som van alle reacties kloppen. Lees reacties van POU_D_TG-"
           "balken met deze marge (KNOWN_BUGS 123).",
           "WARNING: POU_D_TG beams: Code-Aster 17.4 gives nodal reaction "
           "forces for this element with an error that grows with the shear "
           "deformation (measured: 3% at the clamp of a round beam of 10 "
           "elements, and small reaction moments at free nodes). "
           "Displacements, section forces (beam_forces) and the sum of all "
           "reactions are right. Read reactions of POU_D_TG beams with this "
           "margin (KNOWN_BUGS 123)."))


def warping_choice():
    """The setting beam_warping (auto/free/blocked); unknown -> auto."""
    value = "{0}".format(CONFIG_BRIDGE.get("beam_warping", "auto")).lower()
    if value not in WARP_CHOICES:
        log(tr("WARNING: CONFIG_BRIDGE['beam_warping'] = '{0}' is onbekend "
               "(kies uit {1}); 'auto' gebruikt.",
               "WARNING: CONFIG_BRIDGE['beam_warping'] = '{0}' is unknown "
               "(choose from {1}); 'auto' used.").format(
                   value, ", ".join(WARP_CHOICES)))
        return "auto"
    return value


def warping_nodes(model_data, cells, xyz, selection_nodes, bc_dofs):
    """
    Nodes where GRX = 0, for the POU_D_TG cells.

    cells           : [(node 1, node 2)] of all POU_D_TG cells (final mesh:
                      after offsets and flexible joints, whose own nodes
                      are not Mecway nodes and so get no condition: the
                      warping stays free there)
    xyz             : {node: (x, y, z)} for those nodes
    selection_nodes : function (Mecway selection name) -> set of nodes
    bc_dofs         : function (bc) -> set of global DOFs it fixes
                      (bridge_mesh._bc_dofs)
    Returns (sorted node list, {node: reason}).
    """
    mode = warping_choice()
    axes = {}
    for n1, n2 in cells:
        p, q = xyz[n1], xyz[n2]
        v = [q[i] - p[i] for i in range(3)]
        length = math.sqrt(sum(c * c for c in v))
        if length <= 0.0:
            continue
        v = [c / length for c in v]
        axes.setdefault(n1, []).append(v)
        axes.setdefault(n2, []).append(v)
    if mode == "free" or not axes:
        return [], {}
    held = {}            # node -> [(label, set of DOFs)]
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in _KINEMATIC or not bc.get("selection"):
            continue
        dofs = bc_dofs(bc)
        for n in selection_nodes(bc["selection"]) & set(axes):
            held.setdefault(n, []).append((bc["type"], dofs))
    for c in model_data.get("couplings", []):
        if c.get("type") != "rbe2":
            continue
        for group in (c.get("master_group"), c.get("slave_group")):
            for n in selection_nodes(group) & set(axes):
                held.setdefault(n, []).append(
                    ("rigidbody coupling", set(_ROT)))
    reasons = {}
    for n, items in held.items():
        for label, dofs in items:
            rot = [k for k in range(3) if _ROT[k] in dofs]
            if mode == "blocked":
                reasons[n] = "{0} (beam_warping = blocked)".format(label)
                break
            # a fixed rotation axis e_k across a beam axis = bending
            across = [k for k in rot
                      if any(abs(v[k]) < _ALONG for v in axes[n])]
            if across:
                reasons[n] = "{0}, rotation {1} fixed".format(
                    label, "/".join(_ROT[k] for k in across))
                break
    nodes = sorted(reasons)
    free = sorted(set(held) - set(reasons))
    if nodes or free:
        shown = ", ".join("N{0} ({1})".format(n, reasons[n])
                          for n in nodes[:20])
        log("INFO: Warping (POU_D_TG, beam_warping = {0}): GRX = 0 at {1} "
            "node(s){2}{3}; free at {4} supported node(s){5} and at all "
            "other nodes.".format(
                mode, len(nodes), ": " if nodes else "", shown +
                (" ..." if len(nodes) > 20 else ""), len(free),
                (" (" + ", ".join("N{0}".format(n) for n in free[:20]) +
                 (" ..." if len(free) > 20 else "") + ")") if free else ""))
    return nodes, reasons
