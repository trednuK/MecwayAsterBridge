# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 3 with numpy, as in the job) of the total stress of a
# harmonic analysis with hysteretic damping (KNOWN_BUGS 120,
# aster_harmonic_export header):
#   - one loss factor: SIGM_NOEU times (1 + i eta);
#   - several: per node sum n_k (1 + i eta_k) sigma_k / sum n_k with the
#     cell counts per class (class_counts, 0-based cells and nodes), equal
#     to the mean over the cells of (1 + i eta_e) sigma_e at the node;
#   - a stress node without a class cell is counted (ERROR in the job).
# Verification in Code-Aster: HR-06e .. HR-06g (TestFiles/Verificatie/
# tests_harmonisch.py).
#
#   python tests/test_harm_hyst_stress.py

from __future__ import print_function

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import numpy as np  # noqa: E402
import aster_harmonic_export as ahe  # noqa: E402

_FAILED = []


def check(cond, text):
    if not cond:
        _FAILED.append(text)
        print("FAIL: " + text)


class _SF(object):
    def __init__(self, cmps, vals, mask):
        self.cmps, self.vals, self.mask = cmps, vals, mask

    def getComponents(self):
        return self.cmps

    def getValues(self):
        return self.vals, self.mask


class _Fld(object):
    def __init__(self, sf):
        self.sf = sf

    def toSimpleFieldOnNodes(self):
        return self.sf


class _Res(object):
    """SIGM_NOEU only (index ignored)."""

    def __init__(self, vals, mask):
        self.sf = _SF(["SIXX", "SIYY"], vals, mask)

    def getField(self, name, index):
        if name != "SIGM_NOEU":
            raise KeyError(name)
        return _Fld(self.sf)


class _Mesh(object):
    """Two quad cells in a row: cell 0 nodes 0 1 4 3, cell 1 nodes 1 2 5 4
    (0-based); groups A = cell 0, B = cell 1. With three=True a third cell
    2 (nodes 1 6 7 4) in group A2: nodes 1 and 4 then have two cells of
    class A (groups A and A2) and one of class B."""

    def __init__(self, three=False):
        self.three = three

    def getConnectivity(self):
        out = [[0, 1, 4, 3], [1, 2, 5, 4]]
        return out + ([[1, 6, 7, 4]] if self.three else [])

    def getCells(self, g):
        return {"A": [0], "B": [1], "A2": [2]}[g]


def main():
    n = 6
    mesh = _Mesh()
    ca = ahe.class_counts(mesh, ["A"], n)
    cb = ahe.class_counts(mesh, ["B"], n)
    check(list(ca) == [1, 1, 0, 1, 1, 0], "counts A {0}".format(list(ca)))
    check(list(cb) == [0, 1, 1, 0, 1, 1], "counts B {0}".format(list(cb)))
    check(list(ahe.class_counts(mesh, ["A", "A"], n)) == list(ca),
          "a cell counts once")

    # element stresses (computed, real E) per cell: A = 3 + 1j, B = 5 - 2j
    sa, sb = 3.0 + 1.0j, 5.0 - 2.0j
    ea, eb = 0.5, 0.1
    in_a = np.array([1, 1, 0, 1, 1, 0], dtype=bool)
    in_b = np.array([0, 1, 1, 0, 1, 1], dtype=bool)
    # SIGM_NOEU of each class: the mean of its cells at the node
    va = np.where(in_a, sa, 0.0)[:, None] * np.ones((1, 2))
    vb = np.where(in_b, sb, 0.0)[:, None] * np.ones((1, 2))
    base = ((va * in_a[:, None] + vb * in_b[:, None]) /
            (in_a.astype(float) + in_b)[:, None])
    mask = np.ones((n, 2), dtype=bool)
    res = _Res(base.copy(), mask)
    res_a = _Res(va, np.repeat(in_a[:, None], 2, axis=1))
    res_b = _Res(vb, np.repeat(in_b[:, None], 2, axis=1))

    # one loss factor
    data = ahe._HarmFields(res, n, {1: 1.0}, stress_eta=0.3)
    data.set_index(1)
    got = data.field("SIGM_NOEU")[1]
    check(np.allclose(got, base * (1 + 0.3j)), "single eta")

    # two classes
    data = ahe._HarmFields(res, n, {1: 1.0}, classes=[
        (ea, res_a, ca), (eb, res_b, cb)])
    data.set_index(1)
    got = data.field("SIGM_NOEU")[1][:, 0]
    want = []
    for k in range(n):
        terms = []
        if in_a[k]:
            terms.append((1 + 1j * ea) * sa)
        if in_b[k]:
            terms.append((1 + 1j * eb) * sb)
        want.append(sum(terms) / len(terms))
    check(np.allclose(got, want), "two classes {0} (want {1})".format(
        got, want))
    check(data.unmatched == 0, "no unmatched nodes")
    # a stress node outside every class keeps its value and is counted
    data = ahe._HarmFields(res, n, {1: 1.0}, classes=[(ea, res_a, ca)])
    data.set_index(1)
    got = data.field("SIGM_NOEU")[1][:, 0]
    check(data.unmatched == 2, "unmatched {0}".format(data.unmatched))
    check(np.isclose(got[2], base[2, 0]), "unmatched node unchanged")
    # unequal counts: class A has 2 cells at nodes 1 and 4 (values sa and
    # sa2, its SIGM_NOEU there their mean), class B one (sb)
    n3, sa2 = 8, 1.0 - 4.0j
    mesh3 = _Mesh(three=True)
    ca3 = ahe.class_counts(mesh3, ["A", "A2"], n3)
    cb3 = ahe.class_counts(mesh3, ["B"], n3)
    check(list(ca3) == [1, 2, 0, 1, 2, 0, 1, 1], "counts A+A2 {0}".format(
        list(ca3)))
    cell_a = {0: [sa], 1: [sa, sa2], 3: [sa], 4: [sa, sa2], 6: [sa2],
              7: [sa2]}
    cell_b = {1: [sb], 2: [sb], 4: [sb], 5: [sb]}
    va3 = np.array([np.mean(cell_a[k]) if k in cell_a else 0.0
                    for k in range(n3)])[:, None] * np.ones((1, 2))
    vb3 = np.array([np.mean(cell_b[k]) if k in cell_b else 0.0
                    for k in range(n3)])[:, None] * np.ones((1, 2))
    ma3 = np.repeat(np.array([k in cell_a for k in range(n3)])[:, None], 2,
                    axis=1)
    mb3 = np.repeat(np.array([k in cell_b for k in range(n3)])[:, None], 2,
                    axis=1)
    res3 = _Res(np.zeros((n3, 2), dtype=complex), np.ones((n3, 2), bool))
    data = ahe._HarmFields(res3, n3, {1: 1.0}, classes=[
        (ea, _Res(va3, ma3), ca3), (eb, _Res(vb3, mb3), cb3)])
    data.set_index(1)
    got = data.field("SIGM_NOEU")[1][:, 0]
    for k in range(n3):
        terms = [(1 + 1j * ea) * v for v in cell_a.get(k, [])] + \
            [(1 + 1j * eb) * v for v in cell_b.get(k, [])]
        want = sum(terms) / len(terms)
        check(np.isclose(got[k], want), "unequal counts node {0}: {1} "
              "(want {2})".format(k, got[k], want))
    # other fields are not touched
    data = ahe._HarmFields(res, n, {1: 1.0}, stress_eta=0.3)
    data.set_index(1)
    check(data.field("DEPL") is None, "no DEPL in the fake")

    if _FAILED:
        print("{0} failure(s)".format(len(_FAILED)))
        sys.exit(1)
    print("OK: total harmonic stress with hysteretic damping (one loss "
          "factor, classes per node, unmatched nodes)")


if __name__ == "__main__":
    main()
