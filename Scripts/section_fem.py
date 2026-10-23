# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_fem.py
# Cross-section properties on a tri6 mesh (from section_mesh.py).
# Runs in the Python that ships with Code-Aster (CPython 3, numpy + scipy);
# NOT in IronPython.
#
# Formulation: W.D. Pilkey, "Analysis and Design of Elastic Beams:
# Computational Methods", Wiley 2002 (ch. 6: warping function, shear
# functions, shear centre, shear deformation coefficients), the same
# formulation as the Python package sectionproperties (R. van Leeuwen), which
# was used as the reference during development (not needed at run time).
#
#   - geometric properties: exact triangle integrals (exact for polygons);
#   - plastic moduli: plastic neutral axis by root finding on the exactly
#     clipped triangles;
#   - warping function omega: K omega = f_torsion with the constraint
#     int(omega) = 0 (Lagrange multiplier); J = Ixx + Iyy - omega . f_torsion;
#   - shear functions psi, phi (Poisson ratio nu), elastic shear centre,
#     Trefftz shear centre, warping constant about the shear centre, shear
#     areas; 6-point Gauss rule (exact for the polynomial degrees involved
#     on straight-edged tri6).

import math

import numpy as np
from scipy.sparse import coo_matrix, bmat, csc_matrix
from scipy.sparse.linalg import splu
from scipy.optimize import brentq

# Dunavant degree-4 rule, 6 points: (zeta1, zeta2, zeta3, weight), sum w = 1
_A1, _W1 = 0.445948490915965, 0.223381589678011
_A2, _W2 = 0.091576213509771, 0.109951743655322
GAUSS6 = np.array([
    [_A1, _A1, 1 - 2 * _A1, _W1],
    [_A1, 1 - 2 * _A1, _A1, _W1],
    [1 - 2 * _A1, _A1, _A1, _W1],
    [_A2, _A2, 1 - 2 * _A2, _W2],
    [_A2, 1 - 2 * _A2, _A2, _W2],
    [1 - 2 * _A2, _A2, _A2, _W2],
])


def _shape(z):
    """tri6 shape functions and derivatives w.r.t. the area coordinates."""
    z1, z2, z3 = z
    N = np.array([z1 * (2 * z1 - 1), z2 * (2 * z2 - 1), z3 * (2 * z3 - 1),
                  4 * z1 * z2, 4 * z2 * z3, 4 * z3 * z1])
    dN = np.array([[4 * z1 - 1, 0, 0],
                   [0, 4 * z2 - 1, 0],
                   [0, 0, 4 * z3 - 1],
                   [4 * z2, 4 * z1, 0],
                   [0, 4 * z3, 4 * z2],
                   [4 * z3, 0, 4 * z1]])
    return N, dN


def principal_coordinate(phi_deg, x, y):
    """Coordinates along principal axes 1 and 2 (axis 1 at phi from +x)."""
    p = math.radians(phi_deg)
    c, s = math.cos(p), math.sin(p)
    return c * x + s * y, -s * x + c * y


# --------------------------------------------------------------------------
# Geometric properties
# --------------------------------------------------------------------------

def _tri_moments(X):
    """Exact area, first and second moments of linear triangles X (E,3,2)
    about the origin of X."""
    x, y = X[:, :, 0], X[:, :, 1]
    A = 0.5 * ((x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0]) -
               (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0]))
    sx = x.sum(axis=1)
    sy = y.sum(axis=1)
    qx = A * sy / 3.0                              # int y
    qy = A * sx / 3.0                              # int x
    ixx = A / 6.0 * (np.sum(y * y, axis=1) + y[:, 0] * y[:, 1] + y[:, 1] * y[:, 2] +
                     y[:, 2] * y[:, 0])
    iyy = A / 6.0 * (np.sum(x * x, axis=1) + x[:, 0] * x[:, 1] + x[:, 1] * x[:, 2] +
                     x[:, 2] * x[:, 0])
    ixy = A / 12.0 * (2 * np.sum(x * y, axis=1) + x[:, 0] * y[:, 1] + x[:, 1] * y[:, 0] +
                      x[:, 0] * y[:, 2] + x[:, 2] * y[:, 0] +
                      x[:, 1] * y[:, 2] + x[:, 2] * y[:, 1])
    return A, qx, qy, ixx, iyy, ixy


def geometric_properties(nodes, elements, boundary=None, loops=None):
    """Area, centroid, second moments, principal axes, elastic moduli,
    radii of gyration. Exact for a polygonal section."""
    t3 = elements[:, :3]
    ref = nodes[t3].reshape(-1, 2).mean(axis=0)
    X = nodes[t3] - ref
    A, qx, qy, _, _, _ = _tri_moments(X)
    area = float(A.sum())
    cx = float(qy.sum() / area) + ref[0]
    cy = float(qx.sum() / area) + ref[1]
    Xc = nodes[t3] - np.array([cx, cy])
    _, _, _, ixx, iyy, ixy = _tri_moments(Xc)
    ixx_c, iyy_c, ixy_c = float(ixx.sum()), float(iyy.sum()), float(ixy.sum())

    # principal axes, as sectionproperties (post.py): I11 >= I22,
    # phi = angle from +x to axis 1 (degrees, CCW)
    delta = math.sqrt(((ixx_c - iyy_c) / 2.0) ** 2 + ixy_c ** 2)
    i11 = (ixx_c + iyy_c) / 2.0 + delta
    i22 = (ixx_c + iyy_c) / 2.0 - delta
    if abs(ixx_c - i11) < 1e-9 * i11:
        phi = 0.0
    else:
        phi = math.degrees(math.atan2(ixx_c - i11, ixy_c))
    # An axis has two directions: take the one with phi in (-90, 90], so
    # axis 1 (Mecway's V) points to the +x side (round-off of Ixy on a mesh
    # boundary gave phi = -180 for a symmetric half tube). Everything below
    # (principal moduli, plastic moduli, the aster block) uses this phi.
    if phi > 90.0:
        phi -= 180.0
    elif phi <= -90.0:
        phi += 180.0

    xs = nodes[:, 0] - cx
    ys = nodes[:, 1] - cy
    x1, y2 = principal_coordinate(phi, xs, ys)
    r = {
        "area": area,
        "centroid": [cx, cy],
        "ixx_c": ixx_c, "iyy_c": iyy_c, "ixy_c": ixy_c,
        "i11_c": i11, "i22_c": i22, "phi_deg": phi,
        "rx": math.sqrt(ixx_c / area), "ry": math.sqrt(iyy_c / area),
        "r11": math.sqrt(i11 / area), "r22": math.sqrt(max(i22, 0.0) / area),
        "zxx_plus": ixx_c / abs(ys.max()), "zxx_minus": ixx_c / abs(ys.min()),
        "zyy_plus": iyy_c / abs(xs.max()), "zyy_minus": iyy_c / abs(xs.min()),
        "z11_plus": i11 / abs(y2.max()), "z11_minus": i11 / abs(y2.min()),
        "z22_plus": i22 / abs(x1.max()), "z22_minus": i22 / abs(x1.min()),
    }
    return r


def outer_perimeter(loops):
    """Total length of the loops that are outer boundaries (even nesting
    depth under the even-odd rule); hole boundaries are not counted."""
    from section_mesh import points_inside
    loops = [np.asarray(l, dtype=float) for l in loops]
    total = 0.0
    for k, lp in enumerate(loops):
        L = float(np.sum(np.hypot(*(np.roll(lp, -1, axis=0) - lp).T)))
        others = [l for j, l in enumerate(loops) if j != k]
        if others:
            pa = np.vstack(others)
            pb = np.vstack([np.roll(l, -1, axis=0) for l in others])
            # test point: midpoint of the first edge of this loop
            q = 0.5 * (lp[0] + lp[1])
            depth_odd = bool(points_inside(q[None, :], pa, pb)[0])
        else:
            depth_odd = False
        if not depth_odd:
            total += L
    return total


# --------------------------------------------------------------------------
# Plastic properties
# --------------------------------------------------------------------------

def _clip_above(dv, A):
    """Area and int(d) of the part d > 0 of linear triangles with vertex
    values dv (E,3) and areas A."""
    d = np.sort(dv, axis=1)
    da, db, dc = d[:, 0], d[:, 1], d[:, 2]
    area = np.zeros(len(d))
    mom = np.zeros(len(d))
    allin = da >= 0
    area[allin] = A[allin]
    mom[allin] = A[allin] * (da[allin] + db[allin] + dc[allin]) / 3.0
    one = (dc > 0) & (db <= 0)
    if one.any():
        f = A[one] * dc[one] / (dc[one] - da[one]) * dc[one] / (dc[one] - db[one])
        area[one] = f
        mom[one] = f * dc[one] / 3.0
    two = (da < 0) & (db > 0)
    if two.any():
        f = A[two] * da[two] / (da[two] - db[two]) * da[two] / (da[two] - dc[two])
        area[two] = A[two] - f
        mom[two] = A[two] * (da[two] + db[two] + dc[two]) / 3.0 - f * da[two] / 3.0
    return area, mom


def plastic_modulus(nodes, elements, n):
    """Plastic section modulus for bending with the plastic neutral axis
    perpendicular to the unit vector n: S = int |n.x - c| dA with c such that
    the area is split in halves. Returns (S, c)."""
    t3 = elements[:, :3]
    X = nodes[t3]
    A, _, _, _, _, _ = _tri_moments(X - X.reshape(-1, 2).mean(axis=0))
    d0 = X[:, :, 0] * n[0] + X[:, :, 1] * n[1]
    half = 0.5 * A.sum()

    def f(c):
        return _clip_above(d0 - c, A)[0].sum() - half

    lo, hi = d0.min(), d0.max()
    span = hi - lo
    c = brentq(f, lo, hi, xtol=1e-14 * span, rtol=1e-15, maxiter=200)
    area_up, mom_up = _clip_above(d0 - c, A)
    m_tot = float(np.sum(A * (d0.mean(axis=1) - c)))
    return 2.0 * float(mom_up.sum()) - m_tot, c


def plastic_properties(nodes, elements, phi_deg):
    p = math.radians(phi_deg)
    e1 = np.array([math.cos(p), math.sin(p)])
    e2 = np.array([-math.sin(p), math.cos(p)])
    sxx, _ = plastic_modulus(nodes, elements, np.array([0.0, 1.0]))
    syy, _ = plastic_modulus(nodes, elements, np.array([1.0, 0.0]))
    s11, _ = plastic_modulus(nodes, elements, e2)
    s22, _ = plastic_modulus(nodes, elements, e1)
    return {"sxx": sxx, "syy": syy, "s11": s11, "s22": s22}


# --------------------------------------------------------------------------
# Warping and shear
# --------------------------------------------------------------------------

def _element_data(nodes, elements, centroid):
    """Per element and Gauss point: weights w (E,G), shape N (G,6),
    B (E,G,2,6) and coordinates x, y (E,G) relative to the centroid."""
    X = nodes[elements[:, :3]] - np.asarray(centroid)
    x, y = X[:, :, 0], X[:, :, 1]
    A2 = ((x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0]) -
          (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0]))          # 2 * area
    # d zeta_k / dx = b_k / 2A, d zeta_k / dy = c_k / 2A
    b = np.stack([y[:, 1] - y[:, 2], y[:, 2] - y[:, 0], y[:, 0] - y[:, 1]], axis=1) / A2[:, None]
    c = np.stack([x[:, 2] - x[:, 1], x[:, 0] - x[:, 2], x[:, 1] - x[:, 0]], axis=1) / A2[:, None]
    G = len(GAUSS6)
    E = len(elements)
    Ns = np.zeros((G, 6))
    B = np.zeros((E, G, 2, 6))
    gx = np.zeros((E, G))
    gy = np.zeros((E, G))
    w = np.zeros((E, G))
    for g, (z1, z2, z3, wg) in enumerate(GAUSS6):
        N, dN = _shape((z1, z2, z3))
        Ns[g] = N
        B[:, g, 0, :] = b @ dN.T
        B[:, g, 1, :] = c @ dN.T
        gx[:, g] = x[:, 0] * z1 + x[:, 1] * z2 + x[:, 2] * z3
        gy[:, g] = y[:, 0] * z1 + y[:, 1] * z2 + y[:, 2] * z3
        w[:, g] = wg * 0.5 * A2
    return w, Ns, B, gx, gy


def _assemble_matrix(elements, ke, n):
    E = len(elements)
    rows = np.repeat(elements, 6, axis=1).ravel()
    cols = np.tile(elements, (1, 6)).ravel()
    return coo_matrix((ke.reshape(E, 36).ravel(), (rows, cols)), shape=(n, n)).tocsc()


def _assemble_vector(elements, fe, n):
    return np.bincount(elements.ravel(), weights=fe.ravel(), minlength=n)


def warping_properties(nodes, elements, geo, nu=0.0, boundary=None):
    """Torsion constant, warping constant, shear centres and shear areas
    (Pilkey ch. 6 / sectionproperties). geo: result of geometric_properties."""
    n = len(nodes)
    cx, cy = geo["centroid"]
    ixx, iyy, ixy = geo["ixx_c"], geo["iyy_c"], geo["ixy_c"]
    area = geo["area"]
    w, Ns, B, x, y = _element_data(nodes, elements, (cx, cy))

    ke = np.einsum("eg,egki,egkj->eij", w, B, B)
    f_tor = np.einsum("eg,egki,egk->ei", w, B, np.stack([y, -x], axis=2))
    ce = np.einsum("eg,gi->ei", w, Ns)
    K = _assemble_matrix(elements, ke, n)
    c = _assemble_vector(elements, ce, n)

    r = x ** 2 - y ** 2
    q = 2 * x * y
    d1 = ixx * r - ixy * q
    d2 = ixy * r + ixx * q
    h1 = -ixy * r + iyy * q
    h2 = -iyy * r - ixy * q
    f_psi = (np.einsum("eg,egki,egk->ei", w, B, np.stack([d1, d2], axis=2)) * (nu / 2.0) +
             2 * (1 + nu) * np.einsum("eg,gi,eg->ei", w, Ns, ixx * x - ixy * y))
    f_phi = (np.einsum("eg,egki,egk->ei", w, B, np.stack([h1, h2], axis=2)) * (nu / 2.0) +
             2 * (1 + nu) * np.einsum("eg,gi,eg->ei", w, Ns, iyy * y - ixy * x))

    F = np.column_stack([_assemble_vector(elements, f_tor, n),
                         _assemble_vector(elements, f_psi, n),
                         _assemble_vector(elements, f_phi, n)])
    # Lagrange multiplier for int(u) = 0 (bordered matrix)
    cc = csc_matrix(c.reshape(-1, 1))
    Klg = bmat([[K, cc], [cc.T, None]], format="csc")
    lu = splu(Klg)
    U = lu.solve(np.vstack([F, np.zeros((1, 3))]))
    # K has zero row sums and sum(F) = 0 (centroidal coordinates), so the
    # multiplier must vanish: lambda * sum(c) = -sum(F). Check it against the
    # element loads before assembly (relative to max|u| or the assembled load
    # it fails for a circle, where omega is zero up to round-off).
    lam = np.abs(U[-1]) * c.sum()
    scale = np.array([np.abs(f_tor).sum(), np.abs(f_psi).sum(), np.abs(f_phi).sum()])
    scale = np.maximum(scale, 1e-300)
    if np.any(lam / scale > 1e-8):
        raise ValueError("Lagrange multiplier check failed (%s)" % (lam / scale))
    omega, psi, phi = U[:-1, 0], U[:-1, 1], U[:-1, 2]
    ft = F[:, 0]
    J = ixx + iyy - float(omega.dot(ft))

    E = len(elements)
    om_g = Ns @ omega[elements].T      # (G,E)
    om_g = om_g.T                      # (E,G)
    rr = x ** 2 + y ** 2
    sc_xint = float(np.sum(w * (iyy * x + ixy * y) * rr))
    sc_yint = float(np.sum(w * (ixx * y + ixy * x) * rr))
    q_omega = float(np.sum(w * om_g))
    i_omega = float(np.sum(w * om_g ** 2))
    i_xomega = float(np.sum(w * x * om_g))
    i_yomega = float(np.sum(w * y * om_g))

    delta_s = 2 * (1 + nu) * (ixx * iyy - ixy ** 2)
    x_se = (nu / 2 * sc_xint - float(ft.dot(phi))) / delta_s
    y_se = (nu / 2 * sc_yint + float(ft.dot(psi))) / delta_s
    det = ixx * iyy - ixy ** 2
    x_st = (ixy * i_xomega - iyy * i_yomega) / det
    y_st = (ixx * i_xomega - ixy * i_yomega) / det
    gamma = i_omega - q_omega ** 2 / area - y_se * i_xomega + x_se * i_yomega

    # shear deformation coefficients
    bpsi = np.einsum("egki,ei->egk", B, psi[elements]) - nu / 2 * np.stack([d1, d2], axis=2)
    bphi = np.einsum("egki,ei->egk", B, phi[elements]) - nu / 2 * np.stack([h1, h2], axis=2)
    kx = float(np.einsum("eg,egk,egk->", w, bpsi, bpsi))
    ky = float(np.einsum("eg,egk,egk->", w, bphi, bphi))
    kxy = float(np.einsum("eg,egk,egk->", w, bpsi, bphi))
    a_sx = delta_s ** 2 / kx
    a_sy = delta_s ** 2 / ky
    axx = kx * area / delta_s ** 2
    ayy = ky * area / delta_s ** 2
    axy = kxy * area / delta_s ** 2
    p = math.radians(geo["phi_deg"])
    R = np.array([[math.cos(p), math.sin(p)], [-math.sin(p), math.cos(p)]])
    ra = R.dot(np.array([[axx, axy], [axy, ayy]])).dot(R.T)
    a_s11 = area / ra[0, 0]
    a_s22 = area / ra[1, 1]

    # torsion radius: J * max|tau| / T on the boundary, tau*J/T = grad(omega) - (y, -x)
    rt = None
    if boundary is not None and len(boundary):
        rt = _torsion_radius(nodes, elements, omega, (cx, cy), boundary)

    return {
        "j": J, "gamma": gamma,
        "shear_centre": [x_se + cx, y_se + cy],
        "shear_centre_trefftz": [x_st + cx, y_st + cy],
        "a_sx": a_sx, "a_sy": a_sy, "a_s11": a_s11, "a_s22": a_s22,
        "delta_s": delta_s, "rt": rt,
        "_omega": omega,
    }


def _torsion_radius(nodes, elements, omega, centroid, boundary):
    """max over the boundary of the shear stress for a unit torque times J
    (|(grad(omega) - (y, -x)) . tangent| = J tau_max / T).

    The shear stress is evaluated at the element nodes and averaged per node
    over the elements that share it (area weighted), then the maximum over the
    nodes of the boundary edges is taken. At a re-entrant corner the exact
    stress is singular, so there the value depends on the mesh."""
    X = nodes[elements[:, :3]] - np.asarray(centroid)
    x, y = X[:, :, 0], X[:, :, 1]
    A2 = ((x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0]) -
          (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0]))
    b = np.stack([y[:, 1] - y[:, 2], y[:, 2] - y[:, 0], y[:, 0] - y[:, 1]], axis=1) / A2[:, None]
    c = np.stack([x[:, 2] - x[:, 1], x[:, 0] - x[:, 2], x[:, 1] - x[:, 0]], axis=1) / A2[:, None]
    om = omega[elements]
    zn = [np.eye(3)[0], np.eye(3)[1], np.eye(3)[2],
          np.array([.5, .5, 0.]), np.array([0., .5, .5]), np.array([.5, 0., .5])]
    tx = np.zeros(elements.shape)
    ty = np.zeros(elements.shape)
    for k, z in enumerate(zn):
        _, dN = _shape(z)
        gx = np.einsum("ek,ik,ei->e", b, dN, om)
        gy = np.einsum("ek,ik,ei->e", c, dN, om)
        tx[:, k] = gx - y @ z
        ty[:, k] = gy + x @ z
    wgt = np.repeat(np.abs(A2)[:, None], 6, axis=1)
    n = len(nodes)
    sw = np.bincount(elements.ravel(), weights=wgt.ravel(), minlength=n)
    sw = np.where(sw > 0, sw, 1.0)
    ax = np.bincount(elements.ravel(), weights=(wgt * tx).ravel(), minlength=n) / sw
    ay = np.bincount(elements.ravel(), weights=(wgt * ty).ravel(), minlength=n) / sw
    # component along each boundary edge (on a free edge tau is tangential;
    # the magnitude would also pick up the discretisation error at corners)
    t = nodes[boundary[:, 1]] - nodes[boundary[:, 0]]
    t = t / np.hypot(t[:, 0], t[:, 1])[:, None]
    tan = np.abs(ax[boundary] * t[:, 0:1] + ay[boundary] * t[:, 1:2])
    return float(tan.max())
