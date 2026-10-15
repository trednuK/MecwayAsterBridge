# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test van de koppeling cellen/knopen -> Mecway in
# Scripts/aster_results_export.py (Python 3 met numpy, zoals in de job):
# _coincident_extra, _node_alias en _element_points (joint, element offset,
# gesplitste line3, LINE_QUAD-middenknopen, cellen zonder Mecway-element).
#
#   python tests/test_results_koppeling.py

from __future__ import print_function

import io
import os
import sys
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import numpy as np  # noqa: E402
import aster_results_export as are  # noqa: E402


class _F(object):
    def __init__(self, n, alias):
        self.n = n
        self.alias = alias


def test_coincident_exclude():
    # knopen 0..2 Mecway; 3 = joint-knoop op knoop 1; 4 = verschoven knoop
    # die toevallig op knoop 2 ligt (hoort via de arm bij knoop 0)
    xyz = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [1, 0, 0], [2, 0, 0]],
                   dtype=float)
    assert are._coincident_extra(xyz, 3) == {3: 1, 4: 2}
    co = are._coincident_extra(xyz, 3, exclude=[4])
    assert co == {3: 1}, co
    pairs = (np.array([0]), np.array([4]), xyz[[4]] - xyz[[0]])
    alias = are._node_alias(5, 3, co, pairs)
    assert list(alias) == [0, 1, 2, 1, 0], alias


def test_element_points():
    # Mecway: 1 line2 [1, 2] met joint op knoop 2 (cel [1, J=5]); line3
    # [2, 3, 4] (eind, midden, eind) als twee cellen [2, 3] en [3, 4];
    # quad4-schaal [1, 2, 3, 4] verschoven (cel op knopen 6..9); een cel
    # [10, 11] zonder Mecway-element.
    n = 4
    alias = np.array([0, 1, 2, 3, 1, 0, 1, 2, 3, -1, -1])
    conn = [[0, 4], [1, 2], [2, 3], [5, 6, 7, 8], [9, 10]]
    elements = {1: ("line2", [1, 2]), 2: ("line3", [2, 3, 4]),
                3: ("quad4", [1, 2, 3, 4])}
    nbpt = np.array([2, 2, 2, 4, 2])
    nbsp = np.ones(5, dtype=int)
    fields = _F(n, alias)
    # de cel [9, 10] heeft knopen zonder Mecway-knoop: telt niet mee
    out = are._element_points(fields, conn, elements, nbpt, nbsp, "t1",
                              elements)
    assert out[1] == [(0, 0), (0, 1)], out[1]
    assert out[2] == [(1, 0), (1, 1), (2, 1)], out[2]
    assert out[3] == [(3, 0), (3, 1), (3, 2), (3, 3)], out[3]
    # een cel met waarden die bij geen element hoort: een melding
    alias2 = np.array([0, 1, 2, 3])
    buf = io.StringIO()
    with redirect_stdout(buf):
        are._element_points(_F(n, alias2), [[0, 2]], elements,
                            np.array([2]), np.array([1]), "t2", elements)
    assert "1 cel(len)" in buf.getvalue() or "1 cell(s)" in buf.getvalue(), \
        buf.getvalue()


if __name__ == "__main__":
    test_coincident_exclude()
    test_element_points()
    print("test_results_koppeling: OK")
