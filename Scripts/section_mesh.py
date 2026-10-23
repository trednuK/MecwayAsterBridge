# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_mesh.py
# 2D triangle mesher for a beam cross-section given as closed loops.
# Runs in the Python that ships with Code-Aster (CPython 3, numpy + scipy);
# NOT in IronPython. Standard library + numpy + scipy only.
#
# Domain: even-odd rule over all loops (outer boundaries, holes, islands in
# holes, several separate parts). Loops are cleaned first (merge near-equal
# points, drop collinear points, split at T-junctions and crossings, cancel
# segments that occur twice, e.g. the shared edge of two adjacent faces).
#
# Method: conforming Delaunay refinement (Ruppert / Shewchuk), batch version:
#   1. size field h(x): global size from the target element count, limited by
#      the local wall thickness (ray from each boundary point along the inward
#      normal to the opposite boundary), graded with a Lipschitz factor;
#   2. boundary segments split to h(x) (concentric-shell splitting next to
#      input vertices, so small input angles do not make refinement loop);
#   3. triangular lattice of interior points where h(x) is the global size;
#   4. loop: scipy.spatial.Delaunay of all points, split segments that are
#      encroached (point inside the diametral circle) or missing, flood-fill
#      inside/outside across the segments, insert circumcentres of triangles
#      that are too large or of poor quality (if a circumcentre encroaches a
#      segment, split the segment instead), until nothing is left or the
#      iteration cap is reached;
#   5. tri6 elements (midside nodes on the straight edges).
#
# Reference: J.R. Shewchuk, "Delaunay refinement algorithms for triangular
# mesh generation", Comput. Geom. 22 (2002) 21-74 (encroachment, circumcentre
# insertion, concentric shells).

import math

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import Delaunay, cKDTree


class MeshError(Exception):
    pass


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------

def points_inside(q, pa, pb, chunk=4000000):
    """Even-odd test of points q (n,2) against segments pa-pb (m,2 each).

    Ray in +x direction; half-open rule on y so a vertex is counted once."""
    q = np.asarray(q, dtype=float)
    n = len(q)
    out = np.zeros(n, dtype=bool)
    m = len(pa)
    if n == 0 or m == 0:
        return out
    ya, yb = pa[:, 1], pb[:, 1]
    xa, xb = pa[:, 0], pb[:, 0]
    dy = yb - ya
    dy_safe = np.where(dy == 0.0, 1.0, dy)
    step = max(1, chunk // m)
    for s in range(0, n, step):
        qq = q[s:s + step]
        px = qq[:, 0:1]
        py = qq[:, 1:2]
        straddle = (ya > py) != (yb > py)
        xint = xa + (py - ya) * (xb - xa) / dy_safe
        cross = straddle & (xint > px)
        out[s:s + step] = (np.count_nonzero(cross, axis=1) % 2) == 1
    return out


def _seg_point_distance(p, a, b):
    """Distance of points p (n,2) to all segments a-b (m,2): (n,m) array and
    the projection parameter t."""
    ab = b - a
    l2 = np.einsum("ij,ij->i", ab, ab)
    l2 = np.where(l2 == 0.0, 1.0, l2)
    ap = p[:, None, :] - a[None, :, :]
    t = np.einsum("nmk,mk->nm", ap, ab) / l2[None, :]
    tc = np.clip(t, 0.0, 1.0)
    d = ap - tc[:, :, None] * ab[None, :, :]
    return np.sqrt(np.einsum("nmk,nmk->nm", d, d)), t


class _UnionFind(object):
    def __init__(self, n):
        self.p = np.arange(n)

    def find(self, i):
        p = self.p
        while p[i] != i:
            p[i] = p[p[i]]
            i = p[i]
        return i

    def union(self, i, j):
        ri, rj = self.find(i), self.find(j)
        if ri != rj:
            self.p[max(ri, rj)] = min(ri, rj)


# --------------------------------------------------------------------------
# 1. Cleaning the input loops into a planar straight-line graph
# --------------------------------------------------------------------------

def clean_loops(loops, rel_tol=1e-7):
    """Clean the loops; return (points (n,2), segments (m,2) int, tol).

    The result is a planar graph whose segments bound the even-odd domain of
    the input: every segment has material on exactly one side."""
    arrs = []
    for lp in loops:
        a = np.asarray(lp, dtype=float).reshape(-1, 2)
        if len(a) >= 2 and np.allclose(a[0], a[-1], rtol=0.0, atol=0.0):
            a = a[:-1]                      # closing point repeated
        if len(a) >= 3:
            arrs.append(a)
    if not arrs:
        raise MeshError("no loop with at least 3 points")
    allp = np.vstack(arrs)
    if not np.all(np.isfinite(allp)):
        raise MeshError("loop coordinates are not finite")
    diag = float(np.hypot(*(allp.max(axis=0) - allp.min(axis=0))))
    if diag <= 0.0:
        raise MeshError("loops have zero size")
    tol = rel_tol * diag

    # merge points closer than tol (noise of a 3D mesh, shared vertices)
    uf = _UnionFind(len(allp))
    for i, j in cKDTree(allp).query_pairs(tol):
        uf.union(i, j)
    rep = np.array([uf.find(i) for i in range(len(allp))])
    uniq, inv = np.unique(rep, return_inverse=True)
    pts = allp[uniq]
    segs = []
    off = 0
    for a in arrs:
        ids = list(inv[off:off + len(a)])
        off += len(a)
        ids = _simplify_loop(ids, pts, tol)
        if len(ids) >= 3:
            segs.extend((ids[k], ids[(k + 1) % len(ids)]) for k in range(len(ids)))
    if not segs:
        raise MeshError("all loops degenerate")
    segs = np.array(segs, dtype=int)

    pts, segs = _split_crossings(pts, segs, tol)
    pts, segs = _split_t_junctions(pts, segs, tol)
    segs = _xor_segments(segs)
    if len(segs) < 3:
        raise MeshError("loops cancel out (no area left)")
    used = np.unique(segs)
    remap = -np.ones(len(pts), dtype=int)
    remap[used] = np.arange(len(used))
    return pts[used], remap[segs], tol


def _simplify_loop(ids, pts, tol):
    """Drop repeated ids and vertices that lie within tol of the chord of
    their neighbours (collinear points, back-tracking spikes)."""
    changed = True
    while changed and len(ids) >= 3:
        changed = False
        out = []
        for k in range(len(ids)):
            if not out or ids[k] != out[-1]:
                out.append(ids[k])
        while len(out) > 1 and out[0] == out[-1]:
            out.pop()
        ids = out
        if len(ids) < 3:
            break
        keep = []
        n = len(ids)
        k = 0
        removed = set()
        for k in range(n):
            a = pts[ids[k - 1]]
            b = pts[ids[k]]
            c = pts[ids[(k + 1) % n]]
            ac = c - a
            lac = math.hypot(ac[0], ac[1])
            ab = b - a
            if lac <= tol:
                dev = math.hypot(ab[0], ab[1])
                inside_chord = False
            else:
                dev = abs(ac[0] * ab[1] - ac[1] * ab[0]) / lac
                t = (ab[0] * ac[0] + ab[1] * ac[1]) / (lac * lac)
                inside_chord = -1e-9 <= t <= 1.0 + 1e-9
            if dev <= tol and (inside_chord or lac <= tol) and (k - 1) % n not in removed:
                removed.add(k)
                changed = True
            else:
                keep.append(ids[k])
        ids = keep
    return ids


def _split_crossings(pts, segs, tol):
    """Add a vertex at every proper crossing of two segments (even-odd stays
    well defined)."""
    for _ in range(5):
        a, b = pts[segs[:, 0]], pts[segs[:, 1]]
        mn = np.minimum(a, b) - tol
        mx = np.maximum(a, b) + tol
        new_pts = []
        m = len(segs)
        step = max(1, 2000000 // m)
        for s in range(0, m, step):
            i = np.arange(s, min(m, s + step))
            ov = ((mn[i, None, 0] <= mx[None, :, 0]) & (mx[i, None, 0] >= mn[None, :, 0]) &
                  (mn[i, None, 1] <= mx[None, :, 1]) & (mx[i, None, 1] >= mn[None, :, 1]))
            ov &= i[:, None] < np.arange(m)[None, :]
            ii, jj = np.nonzero(ov)
            if len(ii) == 0:
                continue
            ii = i[ii]
            # skip pairs that share a vertex
            sh = ((segs[ii, 0] == segs[jj, 0]) | (segs[ii, 0] == segs[jj, 1]) |
                  (segs[ii, 1] == segs[jj, 0]) | (segs[ii, 1] == segs[jj, 1]))
            ii, jj = ii[~sh], jj[~sh]
            p, r = a[ii], b[ii] - a[ii]
            q, sv = a[jj], b[jj] - a[jj]
            den = r[:, 0] * sv[:, 1] - r[:, 1] * sv[:, 0]
            ok = np.abs(den) > 1e-300
            qp = q - p
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (qp[:, 0] * sv[:, 1] - qp[:, 1] * sv[:, 0]) / den
                u = (qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]) / den
            lr = np.hypot(r[:, 0], r[:, 1])
            ls = np.hypot(sv[:, 0], sv[:, 1])
            et = tol / np.maximum(lr, 1e-300)
            eu = tol / np.maximum(ls, 1e-300)
            ok &= (t > et) & (t < 1 - et) & (u > eu) & (u < 1 - eu)
            if ok.any():
                new_pts.append(p[ok] + t[ok, None] * r[ok])
        if not new_pts:
            break
        newp = np.vstack(new_pts)
        pts = np.vstack([pts, newp])
        pts, segs = _split_t_junctions(pts, segs, tol)
    return pts, segs


def _split_t_junctions(pts, segs, tol):
    """Split every segment at the vertices that lie on it (within tol)."""
    for _ in range(20):
        a, b = pts[segs[:, 0]], pts[segs[:, 1]]
        hits = {}
        n = len(pts)
        step = max(1, 2000000 // max(1, len(segs)))
        for s in range(0, n, step):
            p = pts[s:s + step]
            d, t = _seg_point_distance(p, a, b)
            L = np.hypot(*(b - a).T)
            e = tol / np.maximum(L, 1e-300)
            on = (d <= tol) & (t > e[None, :]) & (t < 1 - e[None, :])
            vi, sj = np.nonzero(on)
            vi = vi + s
            ok = (segs[sj, 0] != vi) & (segs[sj, 1] != vi)
            for v, sg, tt in zip(vi[ok], sj[ok], t[vi[ok] - s, sj[ok]]):
                hits.setdefault(int(sg), []).append((float(tt), int(v)))
        if not hits:
            break
        out = []
        for k in range(len(segs)):
            if k in hits:
                chain = [segs[k, 0]] + [v for _, v in sorted(hits[k])] + [segs[k, 1]]
                out.extend((chain[i], chain[i + 1]) for i in range(len(chain) - 1)
                           if chain[i] != chain[i + 1])
            else:
                out.append((segs[k, 0], segs[k, 1]))
        segs = np.array(out, dtype=int)
    return pts, segs


def _xor_segments(segs):
    """Segments that occur an even number of times cancel (even-odd rule)."""
    segs = segs[segs[:, 0] != segs[:, 1]]
    key = np.sort(segs, axis=1)
    uniq, cnt = np.unique(key, axis=0, return_counts=True)
    return uniq[cnt % 2 == 1]


def chain_loops(pts, segs):
    """Chain segments into closed loops (list of (k,2) arrays)."""
    adj = {}
    for k, (i, j) in enumerate(segs):
        adj.setdefault(int(i), []).append(k)
        adj.setdefault(int(j), []).append(k)
    used = np.zeros(len(segs), dtype=bool)
    loops = []
    for k0 in range(len(segs)):
        if used[k0]:
            continue
        used[k0] = True
        start, cur = int(segs[k0, 0]), int(segs[k0, 1])
        ids = [start]
        while cur != start:
            ids.append(cur)
            nxt = None
            for k in adj[cur]:
                if not used[k]:
                    nxt = k
                    break
            if nxt is None:
                break
            used[nxt] = True
            i, j = segs[nxt]
            cur = int(j) if int(i) == cur else int(i)
        loops.append(pts[ids])
    return loops


def orient_segments(pts, segs, tol):
    """Orient every segment so the material is on its left; returns the
    oriented segments. Raises if a segment has material on neither side."""
    a, b = pts[segs[:, 0]], pts[segs[:, 1]]
    mid = 0.5 * (a + b)
    d = b - a
    L = np.hypot(d[:, 0], d[:, 1])
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1) / L[:, None]
    eps = np.minimum(10.0 * tol, 0.01 * L)
    left = points_inside(mid + eps[:, None] * nrm, a, b)
    right = points_inside(mid - eps[:, None] * nrm, a, b)
    out = segs.copy()
    flip = right & ~left
    out[flip] = out[flip][:, ::-1]
    bad = left == right
    if bad.any():
        # can only happen for degenerate input (e.g. a dangling edge)
        out = out[~bad]
    return out


# --------------------------------------------------------------------------
# 2. Size field
# --------------------------------------------------------------------------

class SizeField(object):
    """h(x) = min(h0, min_i(h_i + g |x - p_i|)), evaluated over the k nearest
    sample points p_i (good enough for a mesh size function)."""

    def __init__(self, h0, samples, hs, grading, k=16):
        self.h0 = h0
        self.g = grading
        small = hs < h0
        self.p = samples[small]
        self.h = hs[small]
        self.tree = cKDTree(self.p) if len(self.p) else None
        self.k = min(k, len(self.p))
        if self.tree is not None:
            # make the samples consistent with the grading among themselves
            for _ in range(3):
                self.h = np.minimum(self.h, self._eval(self.p))

    def _eval(self, q):
        d, i = self.tree.query(q, k=self.k)
        if self.k == 1:
            d, i = d[:, None], i[:, None]
        return np.min(self.h[i] + self.g * d, axis=1)

    def __call__(self, q):
        q = np.asarray(q, dtype=float).reshape(-1, 2)
        if self.tree is None or len(q) == 0:
            return np.full(len(q), self.h0)
        return np.minimum(self.h0, self._eval(q))


def _thickness_samples(pts, osegs, spacing, tol):
    """Ray casting: for sample points on every oriented segment, the distance
    along the inward normal to the nearest other (non-adjacent) segment."""
    a, b = pts[osegs[:, 0]], pts[osegs[:, 1]]
    d = b - a
    L = np.hypot(d[:, 0], d[:, 1])
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1) / L[:, None]   # inward (left)
    ns = np.maximum(1, np.ceil(L / spacing).astype(int))
    sid = np.repeat(np.arange(len(osegs)), ns)
    start = np.cumsum(ns) - ns
    k = np.arange(len(sid)) - np.repeat(start, ns)
    t = (k + 0.5) / ns[sid]
    P = a[sid] + t[:, None] * d[sid]
    N = nrm[sid]
    m = len(osegs)
    dist = np.full(len(P), np.inf)
    step = max(1, 3000000 // m)
    e0, e1 = osegs[:, 0], osegs[:, 1]
    for s in range(0, len(P), step):
        p = P[s:s + step]
        nv = N[s:s + step]
        si = sid[s:s + step]
        # ray p + u*nv, segment a + w*d
        den = nv[:, 0:1] * d[None, :, 1] - nv[:, 1:2] * d[None, :, 0]
        ap = a[None, :, :] - p[:, None, :]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = (ap[:, :, 0] * d[None, :, 1] - ap[:, :, 1] * d[None, :, 0]) / den
            w = (ap[:, :, 0] * nv[:, 1:2] - ap[:, :, 1] * nv[:, 0:1]) / den
        hit = (np.abs(den) > 1e-300) & (u > tol) & (w >= 0.0) & (w <= 1.0)
        # exclude the own segment and segments sharing a vertex with it
        own0, own1 = e0[si][:, None], e1[si][:, None]
        adj = ((e0[None, :] == own0) | (e0[None, :] == own1) |
               (e1[None, :] == own0) | (e1[None, :] == own1))
        hit &= ~adj
        u = np.where(hit, u, np.inf)
        dist[s:s + step] = u.min(axis=1)
    return P, dist


# --------------------------------------------------------------------------
# 3. Refinement
# --------------------------------------------------------------------------

def _split_points(pts, segs, is_input):
    """Split point of each segment: midpoint, or concentric shell (power of 2
    distance) from an input vertex when only one end is an input vertex."""
    a, b = pts[segs[:, 0]], pts[segs[:, 1]]
    d = b - a
    L = np.hypot(d[:, 0], d[:, 1])
    t = np.full(len(segs), 0.5)
    ia, ib = is_input[segs[:, 0]], is_input[segs[:, 1]]
    one = ia ^ ib
    if one.any():
        shell = 2.0 ** np.round(np.log2(0.5 * L[one]))
        tt = np.clip(shell / L[one], 0.3, 0.7)
        t[one] = np.where(ia[one], tt, 1.0 - tt)
    return a + t[:, None] * d


def _do_split(pts, segs, is_input, mask):
    if not mask.any():
        return pts, segs, is_input
    sp = segs[mask]
    newp = _split_points(pts, sp, is_input)
    n0 = len(pts)
    nid = np.arange(n0, n0 + len(sp))
    pts = np.vstack([pts, newp])
    is_input = np.concatenate([is_input, np.zeros(len(sp), dtype=bool)])
    segs = np.vstack([segs[~mask],
                      np.stack([sp[:, 0], nid], axis=1),
                      np.stack([nid, sp[:, 1]], axis=1)])
    return pts, segs, is_input


def _encroached(pts, segs, tree=None):
    """Segments with a point strictly inside their diametral circle."""
    a, b = pts[segs[:, 0]], pts[segs[:, 1]]
    mid = 0.5 * (a + b)
    r = 0.5 * np.hypot(*(b - a).T) * (1.0 - 1e-9)
    if tree is None:
        tree = cKDTree(pts)
    cnt = tree.query_ball_point(mid, r, return_length=True)
    return np.asarray(cnt) > 0


def _points_encroach(c, pts, segs):
    """For candidate points c: index of a segment whose diametral circle
    contains it (or -1), and the boolean mask per segment."""
    a, b = pts[segs[:, 0]], pts[segs[:, 1]]
    mid = 0.5 * (a + b)
    r = 0.5 * np.hypot(*(b - a).T)
    tree = cKDTree(mid)
    lists = tree.query_ball_point(c, r.max())
    hit_seg = np.zeros(len(segs), dtype=bool)
    enc = np.zeros(len(c), dtype=bool)
    for i, lst in enumerate(lists):
        if not lst:
            continue
        lst = np.asarray(lst)
        dd = np.hypot(*(mid[lst] - c[i]).T)
        h = lst[dd < r[lst]]
        if len(h):
            enc[i] = True
            hit_seg[h] = True
    return enc, hit_seg


def _classify(tri, segs, n_pts, pa, pb):
    """Inside/outside per Delaunay triangle: flood fill across non-segment
    edges, one even-odd test per connected region."""
    simp = tri.simplices
    nb = tri.neighbors
    ne = len(simp)
    seg_keys = set((np.minimum(segs[:, 0], segs[:, 1]).astype(np.int64) * n_pts +
                    np.maximum(segs[:, 0], segs[:, 1])).tolist())
    rows, cols = [], []
    for k in range(3):
        i = simp[:, (k + 1) % 3]
        j = simp[:, (k + 2) % 3]
        key = np.minimum(i, j).astype(np.int64) * n_pts + np.maximum(i, j)
        is_seg = np.fromiter((kk in seg_keys for kk in key.tolist()), dtype=bool, count=ne)
        ok = (nb[:, k] >= 0) & ~is_seg
        rows.append(np.nonzero(ok)[0])
        cols.append(nb[ok, k])
    rows = np.concatenate(rows)
    cols = np.concatenate(cols)
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(ne, ne))
    ncomp, lab = connected_components(g, directed=False)
    first = np.full(ncomp, -1)
    first[lab[::-1]] = np.arange(ne)[::-1]
    cen = tri.points[simp[first]].mean(axis=1)
    comp_in = points_inside(cen, pa, pb)
    return comp_in[lab]


def _delaunay(pts):
    """Delaunay triangulation without degenerate simplices. Qhull's default
    triangulated output ('Qt') can contain zero-area triangles for cocircular
    points (e.g. a polygonal circle); joggled input ('QJ') does not. The
    joggle only affects the choice of diagonals, the returned coordinates are
    the original ones (Qhull documentation, option QJ)."""
    tri = Delaunay(pts, qhull_options="QJ Qbb Qc")
    # Flat triangles of exactly collinear points (e.g. a split segment on the
    # convex hull) are valid for the joggled points but have zero area: drop
    # them. Their edges then count as missing, so a segment that only exists
    # in a flat triangle is split again.
    X = pts[tri.simplices]
    e1 = X[:, 1] - X[:, 0]
    e2 = X[:, 2] - X[:, 0]
    a2 = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    l2 = np.maximum(np.einsum("ij,ij->i", e1, e1), np.einsum("ij,ij->i", e2, e2))
    ok = a2 > 1e-10 * l2
    return _Tri(pts, tri.simplices, tri.neighbors, ok)


class _Tri(object):
    """Delaunay result restricted to the non-degenerate simplices."""

    def __init__(self, pts, simp, nb, ok):
        new = -np.ones(len(simp), dtype=int)
        new[ok] = np.arange(int(ok.sum()))
        nb = nb[ok]
        self.points = pts
        self.simplices = simp[ok]
        self.neighbors = np.where(nb >= 0, new[np.maximum(nb, 0)], -1)


def _edges_of(simp):
    e = np.vstack([simp[:, [0, 1]], simp[:, [1, 2]], simp[:, [2, 0]]])
    return np.sort(e, axis=1)


def _input_vertex_angles(pts, osegs):
    """Smallest angle between segments at each vertex (radians; pi when the
    vertex has fewer than two segments)."""
    ang = np.full(len(pts), np.pi)
    inc = {}
    for i, j in osegs:
        inc.setdefault(int(i), []).append(int(j))
        inc.setdefault(int(j), []).append(int(i))
    for v, nbs in inc.items():
        if len(nbs) < 2:
            continue
        dirs = [math.atan2(pts[w, 1] - pts[v, 1], pts[w, 0] - pts[v, 0]) for w in nbs]
        best = np.pi
        for x in range(len(dirs)):
            for y in range(x + 1, len(dirs)):
                dd = abs(dirs[x] - dirs[y]) % (2 * np.pi)
                best = min(best, dd, 2 * np.pi - dd)
        ang[v] = best
    return ang


def mesh_section(loops, max_area=None, n_target=3000, n_across=3.0,
                 min_angle=25.0, grading=0.3, max_iter=60, max_nodes=400000,
                 log=None):
    """Mesh the even-odd domain of `loops` with tri6 elements.

    loops     : list of closed loops [[x, y], ...] (last point not repeated)
    max_area  : maximum element area (None = automatic, about n_target elements
                on a section without thin walls)
    n_across  : wall thickness / element size (about n_across+1 element rows
                across the thinnest wall)
    Returns a dict: nodes (N,2), elements (E,6) tri6 (corners CCW, then the
    midside nodes of edges 1-2, 2-3, 3-1), boundary (B,3) boundary edges as
    (corner, corner, midside), loops (cleaned loops), and counts."""
    pts0, segs0, tol = clean_loops(loops)
    osegs = orient_segments(pts0, segs0, tol)
    if len(osegs) < 3:
        raise MeshError("no closed area found in the loops")
    pa, pb = pts0[osegs[:, 0]], pts0[osegs[:, 1]]
    area = 0.5 * float(np.sum(pa[:, 0] * pb[:, 1] - pb[:, 0] * pa[:, 1]))
    if area <= 0.0:
        raise MeshError("section area is zero")
    clean = chain_loops(pts0, osegs)

    # global size: equilateral-ish triangles, mean area ~0.4 h^2 after refinement
    h0 = math.sqrt(area / (0.42 * n_target))
    if max_area:
        h0 = min(h0, math.sqrt(4.0 * max_area / math.sqrt(3.0)))
    diag = float(np.hypot(*(pts0.max(axis=0) - pts0.min(axis=0))))
    h_min = max(h0 * 1e-3, 50.0 * tol)

    P, thick = _thickness_samples(pts0, osegs, 0.5 * h0, tol)
    hs = np.clip(thick / n_across, h_min, h0)
    size = SizeField(h0, P, hs, grading)

    # boundary discretisation
    pts = pts0.copy()
    is_input = np.ones(len(pts), dtype=bool)
    segs = osegs.copy()
    for _ in range(80):
        a, b = pts[segs[:, 0]], pts[segs[:, 1]]
        L = np.hypot(*(b - a).T)
        need = L > 1.05 * size(0.5 * (a + b))
        need &= L > 2.0 * h_min
        if not need.any():
            break
        pts, segs, is_input = _do_split(pts, segs, is_input, need)
    # interior lattice where the size field is the global size
    lo = pts0.min(axis=0)
    hi = pts0.max(axis=0)
    dy = h0 * math.sqrt(3.0) / 2.0
    ny = int((hi[1] - lo[1]) / dy) + 1
    nx = int((hi[0] - lo[0]) / h0) + 2
    if nx * ny < 4 * max_nodes:
        jj, ii = np.mgrid[0:ny, 0:nx]
        lat = np.stack([lo[0] + (ii + 0.5 * (jj % 2)) * h0,
                        lo[1] + (jj + 0.5) * dy], axis=-1).reshape(-1, 2)
        lat = lat[size(lat) >= 0.9 * h0]
        if len(lat):
            lat = lat[points_inside(lat, pa, pb)]
        if len(lat):
            dist, _ = cKDTree(pts).query(lat)
            lat = lat[dist > 0.6 * h0]
        pts = np.vstack([pts, lat])
        is_input = np.concatenate([is_input, np.zeros(len(lat), dtype=bool)])

    ang = _input_vertex_angles(pts0, osegs)
    small_angle = np.zeros(len(pts), dtype=bool)
    small_angle[:len(pts0)] = ang < math.radians(60.0)
    B = 1.0 / (2.0 * math.sin(math.radians(min_angle)))

    it = 0
    converged = False
    tri = None
    for it in range(1, max_iter + 1):
        tree = cKDTree(pts)
        enc = _encroached(pts, segs, tree)
        tri = _delaunay(pts)
        simp = tri.simplices
        n = len(pts)
        ek = _edges_of(simp)
        ekey = np.unique(ek[:, 0].astype(np.int64) * n + ek[:, 1])
        sk = np.sort(segs, axis=1)
        skey = sk[:, 0].astype(np.int64) * n + sk[:, 1]
        missing = ~np.isin(skey, ekey)
        if (enc | missing).any():
            pts, segs, is_input = _do_split(pts, segs, is_input, enc | missing)
            small_angle = np.concatenate([small_angle,
                                          np.zeros(len(pts) - len(small_angle), dtype=bool)])
            continue
        inside = _classify(tri, segs, n, pa, pb)
        both = is_input[segs[:, 0]] & is_input[segs[:, 1]]
        fine_in = skey[both] if both.any() else None
        X = pts[simp]
        e0 = X[:, 1] - X[:, 0]
        e1 = X[:, 2] - X[:, 1]
        e2 = X[:, 0] - X[:, 2]
        la = np.hypot(*e0.T)
        lb = np.hypot(*e1.T)
        lc = np.hypot(*e2.T)
        ar = 0.5 * np.abs(e0[:, 0] * (-e2[:, 1]) - e0[:, 1] * (-e2[:, 0]))
        ar = np.maximum(ar, 1e-300)
        R = la * lb * lc / (4.0 * ar)
        lmin = np.minimum(np.minimum(la, lb), lc)
        cen = X.mean(axis=1)
        hloc = size(cen)
        bad_size = R > 0.62 * hloc
        if max_area:
            bad_size |= ar > max_area
        bad_q = R / lmin > B
        # do not chase quality next to small input angles (would not end)
        bad_q &= ~small_angle[simp].any(axis=1)
        # A densely sampled input boundary (e.g. arcs from a STEP file at 1
        # degree per chord) would otherwise grade the whole interior down to
        # the vertex spacing. Accept a fan of narrow triangles on such an
        # edge: quality is not required when the shortest edge of the
        # triangle is an unsplit input segment much shorter than h(x). The
        # small angles are then at the apex; the largest angle stays below
        # 90 + small, which is what matters for the Laplace problems.
        if fine_in is not None and bad_q.any():
            sh = np.argmin(np.stack([la, lb, lc], axis=1), axis=1)
            i0 = simp[np.arange(len(simp)), sh]
            i1 = simp[np.arange(len(simp)), (sh + 1) % 3]
            k = np.minimum(i0, i1).astype(np.int64) * n + np.maximum(i0, i1)
            on_input = np.isin(k, fine_in)
            bad_q &= ~(on_input & (lmin < 0.5 * hloc))
        bad = inside & (bad_size | bad_q) & (lmin > h_min)
        if not bad.any() or len(pts) > max_nodes:
            converged = not bad.any()
            break
        bi = np.nonzero(bad)[0]
        # circumcentres
        A0, B0, C0 = X[bi, 0], X[bi, 1], X[bi, 2]
        bx, by = B0[:, 0] - A0[:, 0], B0[:, 1] - A0[:, 1]
        cx, cy = C0[:, 0] - A0[:, 0], C0[:, 1] - A0[:, 1]
        dd = 2.0 * (bx * cy - by * cx)
        ux = (cy * (bx * bx + by * by) - by * (cx * cx + cy * cy)) / dd
        uy = (bx * (cx * cx + cy * cy) - cx * (bx * bx + by * by)) / dd
        cc = np.stack([A0[:, 0] + ux, A0[:, 1] + uy], axis=1)
        Rb = R[bi]
        # priority: largest relative badness first
        prio = Rb / np.minimum(hloc[bi], lmin[bi] * B)
        order = np.argsort(-prio)
        cc, Rb = cc[order], Rb[order]
        encp, hit_seg = _points_encroach(cc, pts, segs)
        keep = ~encp
        if keep.any():
            ins = points_inside(cc[keep], pa, pb)
            kk = np.nonzero(keep)[0]
            keep[kk[~ins]] = False
        cand = cc[keep]
        rc = Rb[keep]
        accepted = []
        if len(cand):
            ctree = cKDTree(cand)
            lists = ctree.query_ball_point(cand, 0.5 * rc)
            taken = np.zeros(len(cand), dtype=bool)
            for i, lst in enumerate(lists):
                ok = True
                for j in lst:
                    if j < i and taken[j]:
                        ok = False
                        break
                if ok:
                    taken[i] = True
            accepted = cand[taken]
        if len(accepted) == 0 and not hit_seg.any():
            break
        if len(accepted):
            pts = np.vstack([pts, accepted])
            is_input = np.concatenate([is_input, np.zeros(len(accepted), dtype=bool)])
        pts, segs, is_input = _do_split(pts, segs, is_input, hit_seg)
        small_angle = np.concatenate([small_angle,
                                      np.zeros(len(pts) - len(small_angle), dtype=bool)])

    # final triangulation with all segments present
    for _ in range(40):
        tree = cKDTree(pts)
        tri = _delaunay(pts)
        simp = tri.simplices
        n = len(pts)
        ek = _edges_of(simp)
        ekey = np.unique(ek[:, 0].astype(np.int64) * n + ek[:, 1])
        sk = np.sort(segs, axis=1)
        missing = ~np.isin(sk[:, 0].astype(np.int64) * n + sk[:, 1], ekey)
        if not missing.any():
            break
        enc = _encroached(pts, segs, tree)
        pts, segs, is_input = _do_split(pts, segs, is_input, missing | enc)
    else:
        raise MeshError("could not recover all boundary segments")
    inside = _classify(tri, segs, len(pts), pa, pb)
    t3 = tri.simplices[inside]
    if len(t3) == 0:
        raise MeshError("no triangles inside the section")
    # drop unused points, orient CCW
    used = np.unique(t3)
    remap = -np.ones(len(pts), dtype=int)
    remap[used] = np.arange(len(used))
    nodes = pts[used]
    t3 = remap[t3]
    segs = remap[segs]
    X = nodes[t3]
    sgn = ((X[:, 1, 0] - X[:, 0, 0]) * (X[:, 2, 1] - X[:, 0, 1]) -
           (X[:, 1, 1] - X[:, 0, 1]) * (X[:, 2, 0] - X[:, 0, 0]))
    t3[sgn < 0] = t3[sgn < 0][:, [0, 2, 1]]

    # midside nodes
    nc = len(nodes)
    e = np.vstack([t3[:, [0, 1]], t3[:, [1, 2]], t3[:, [2, 0]]])
    ek = np.sort(e, axis=1)
    key = ek[:, 0].astype(np.int64) * nc + ek[:, 1]
    ukey, inv = np.unique(key, return_inverse=True)
    ue = np.stack([ukey // nc, ukey % nc], axis=1)
    mids = 0.5 * (nodes[ue[:, 0]] + nodes[ue[:, 1]])
    ne = len(t3)
    mid_id = nc + inv
    tri6 = np.column_stack([t3, mid_id[:ne], mid_id[ne:2 * ne], mid_id[2 * ne:]])
    nodes6 = np.vstack([nodes, mids])
    sk = np.sort(segs, axis=1)
    skey = sk[:, 0].astype(np.int64) * nc + sk[:, 1]
    pos = np.searchsorted(ukey, skey)
    if np.any(pos >= len(ukey)) or np.any(ukey[np.minimum(pos, len(ukey) - 1)] != skey):
        raise MeshError("boundary segment missing in the final mesh")
    boundary = np.column_stack([segs, nc + pos])

    # quality report
    X = nodes[t3]
    la = np.hypot(*(X[:, 1] - X[:, 0]).T)
    lb = np.hypot(*(X[:, 2] - X[:, 1]).T)
    lc = np.hypot(*(X[:, 0] - X[:, 2]).T)
    cosA = np.clip((la ** 2 + lc ** 2 - lb ** 2) / (2 * la * lc), -1, 1)
    cosB = np.clip((la ** 2 + lb ** 2 - lc ** 2) / (2 * la * lb), -1, 1)
    angA = np.degrees(np.arccos(cosA))
    angB = np.degrees(np.arccos(cosB))
    angC = 180.0 - angA - angB
    amin = np.minimum(np.minimum(angA, angB), angC)
    info = {
        "n_elements": int(ne),
        "n_nodes": int(len(nodes6)),
        "n_corner_nodes": int(nc),
        "n_boundary_edges": int(len(boundary)),
        "iterations": int(it),
        "converged": bool(converged),
        "min_angle_deg": float(amin.min()),
        "n_angle_below_20": int(np.count_nonzero(amin < 20.0)),
        "h_global": float(h0),
        "h_min_field": float(size.h.min()) if len(size.h) else float(h0),
        "area_input": float(area),
        "diag": diag,
    }
    if log is not None:
        log("INFO: mesh {0} tri6, {1} nodes, {2} iterations, min angle {3:.1f} deg".format(
            ne, len(nodes6), it, info["min_angle_deg"]))
    return {"nodes": nodes6, "elements": tri6, "boundary": boundary,
            "loops": clean, "info": info}


def element_parts(elements):
    """Connected parts of the mesh (elements sharing an edge); returns
    (n_parts, label per element)."""
    t3 = elements[:, :3]
    ne = len(t3)
    e = np.vstack([t3[:, [0, 1]], t3[:, [1, 2]], t3[:, [2, 0]]])
    ek = np.sort(e, axis=1)
    owner = np.tile(np.arange(ne), 3)
    order = np.lexsort((ek[:, 1], ek[:, 0]))
    eks = ek[order]
    same = np.all(eks[1:] == eks[:-1], axis=1)
    r = owner[order][:-1][same]
    c = owner[order][1:][same]
    g = coo_matrix((np.ones(len(r)), (r, c)), shape=(ne, ne))
    return connected_components(g, directed=False)
