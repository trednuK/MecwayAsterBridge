# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of loads on face and element selections (IronPython 2.7 and
# Python 3,
# without Mecway and Code-Aster; liml -> mesh -> .comm in a temporary folder):
#   - force on shell faces with both sides (faceid 5 and 6) of the same
#     element: FORCE_COQUE over the area of the distinct elements, so the
#     resultant equals the Mecway force; a group with single- and
#     double-sided elements gives a WARNING (bridge_mesh._apply_to_model_data);
#   - elastic support and compression only on both sides of a shell: an
#     ERROR naming the selection, no exception (bridge_mesh._build_discretes,
#     _compression_only);
#   - #ASTER-XFEM groep=<<selection>> with a selection Code-Aster renames
#     (bridge_xfem.model_block);
#   - thermal face loads on a selection with faces of modelled and
#     non-modelled elements: only the active skin cells in AFFE_MODELE,
#     ORIE_PEAU, ECHANGE and FLUX_REP (bridge_thermal._face_targets).
#
#   python tests/test_bridge_face_selections.py

from __future__ import print_function

import io
import os
import re
import shutil
import sys
import tempfile
import traceback

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_from_liml as bfl  # noqa: E402
import bridge_mesh as bm  # noqa: E402
import bridge_plane  # noqa: E402
import bridge_thermal  # noqa: E402
import bridge_to_aster as bta  # noqa: E402
import bridge_xfem  # noqa: E402
for _mod in (bfl, bm, bridge_plane, bridge_thermal, bta, bridge_xfem):
    _mod.log = _log

FAILS = []
_SAVED = dict(bridge_utils.CONFIG_BRIDGE)


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        FAILS.append(text)


STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def _run(text, analysis):
    """(model_data, .comm text or None, exception text or None)."""
    tmp = tempfile.mkdtemp(prefix="mab_facesel_")
    try:
        path = os.path.join(tmp, "m.liml")
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
        bridge_utils.CONFIG_BRIDGE["active_analysis"] = analysis
        del LOG[:]
        md = bfl.extract_aster_data_from_liml(path)
        if md is None:
            return None, None, None
        mail = os.path.join(tmp, "m.mail")
        try:
            ok = (bm.write_mesh(mail, md) and
                  bta.generate_AsterSolver_files(tmp, md, mail, "t.resu"))
        except Exception:
            return md, None, traceback.format_exc().splitlines()[-1]
        comm = None
        if ok:
            with io.open(os.path.join(tmp, "study.comm"),
                         encoding="utf-8") as f:
                comm = f.read()
        return md, comm, None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _errors():
    return [m for m in LOG if m.startswith("ERROR")]


# ---------- shells ----------
def _shell_liml(loads, faces):
    """Three quad4 of 1 m2 in the XY plane (x 0 .. 3), fixed edge,
    face selection 'Sel'."""
    nodes = [(x, y) for y in (0, 1) for x in (0, 1, 2, 3)]
    lines = ['<liml version="34">', '  <analysis type="S30" />']
    for i, (x, y) in enumerate(nodes):
        lines.append('  <node nid="%d" x="%r" y="%r" z="0.0" />' % (
            i + 1, float(x), float(y)))
    lines += ['  <elset name="P" material="M">',
              '    <elem eid="1" shape="quad4" nodes="1 2 6 5" />',
              '    <elem eid="2" shape="quad4" nodes="2 3 7 6" />',
              '    <elem eid="3" shape="quad4" nodes="3 4 8 7" />',
              '  </elset>',
              '  <fixed selection="Links" />', loads,
              '  <mat name="M">',
              '    <geometric type="Plate" thickness="10 mm" />', STEEL,
              '  </mat>',
              '  <faceselection name="Links"><face eid="1" faceid="4" />'
              '</faceselection>',
              '  <faceselection name="Sel">%s</faceselection>' % faces,
              '</liml>']
    return "\n".join(lines)


def _faces(*pairs):
    return "".join('<face eid="%d" faceid="%d" />' % p for p in pairs)


FORCE = ('  <force selection="Sel"><x>0 N</x><y>0 N</y><z>10 N</z>'
         '</force>')


def _fz(comm):
    m = re.search(r"FORCE_COQUE=_F\(GROUP_MA='Sel', FZ=([-0-9.eE+]+)\)",
                  comm or "")
    return float(m.group(1)) if m else None


def test_shell_force():
    # both sides of element 1: area 1 m2 -> 10 N/m2 (was 5: 2 m2)
    md, comm, exc = _run(_shell_liml(FORCE, _faces((1, 5), (1, 6))),
                         "lin_static_3d")
    fz = _fz(comm)
    check(exc is None and fz is not None and abs(fz - 10.0) < 1e-9,
          "force on both sides of one shell: FZ = 10 N/m2 ({0}, {1})".format(
              fz, exc))
    # one side of two elements: 10 N / 2 m2, unchanged
    md, comm, exc = _run(_shell_liml(FORCE, _faces((1, 5), (2, 5))),
                         "lin_static_3d")
    fz = _fz(comm)
    check(fz is not None and abs(fz - 5.0) < 1e-9 and
          not [m for m in LOG if "both sides" in m],
          "force on one side of two shells: FZ = 5 N/m2 ({0})".format(fz))
    # element 1 both sides, element 2 one side: resultant over the
    # distinct area (2 m2), WARNING on the distribution
    md, comm, exc = _run(_shell_liml(FORCE, _faces((1, 5), (1, 6), (2, 6))),
                         "lin_static_3d")
    fz = _fz(comm)
    check(fz is not None and abs(fz - 5.0) < 1e-9 and
          [m for m in LOG if m.startswith("WARNING") and "'Sel'" in m and
           "both sides" in m],
          "force, mixed single/double-sided shells: FZ = 5 N/m2 and a "
          "WARNING ({0})".format(fz))


def test_shell_supports_both_sides():
    for tag, analysis in (
            ('  <elasticsupport selection="Sel"><modulus>1E9 Pa/m</modulus>'
             '<tangential>1E8 Pa/m</tangential></elasticsupport>',
             "lin_static_3d"),
            ('  <compressiononly selection="Sel" />', "nonlin_static_3d")):
        name = tag.split()[0].strip("< ")
        for faces, what in ((_faces((1, 5), (1, 6)), "both sides"),
                            (_faces((1, 5), (1, 6), (2, 5)),
                             "both sides of one of two")):
            md, comm, exc = _run(_shell_liml(tag, faces), analysis)
            errs = [m for m in _errors() if "'Sel'" in m]
            check(exc is None and comm is not None and errs and
                  [s for s in md.get("skipped_loads", []) if "Sel" in s],
                  "{0} on {1} of a shell: ERROR naming 'Sel', no exception "
                  "({2}, {3})".format(name, what, exc, errs[:1]))
        # one side: still translated
        md, comm, exc = _run(_shell_liml(tag, _faces((1, 5), (2, 5))),
                             analysis)
        check(exc is None and comm is not None and not _errors(),
              "{0} on one side of shells: translated ({1})".format(
                  name, _errors()[:1]))


# ---------- XFEM ----------
def _block(nx, ny, nz, lx, ly, lz, x0=0.0, y0=0.0, eid0=1, nid0=1):
    nodes, elems, idx = [], [], {}
    k = nid0
    for kz in range(nz + 1):
        for ky in range(ny + 1):
            for kx in range(nx + 1):
                idx[(kx, ky, kz)] = k
                nodes.append('  <node nid="%d" x="%r" y="%r" z="%r" />' % (
                    k, x0 + lx * kx / nx, y0 + ly * ky / ny, lz * kz / nz))
                k += 1
    e = eid0
    for kz in range(nz):
        for ky in range(ny):
            for kx in range(nx):
                c = [idx[(kx, ky, kz)], idx[(kx + 1, ky, kz)],
                     idx[(kx + 1, ky + 1, kz)], idx[(kx, ky + 1, kz)]]
                c += [idx[(a, b, kz + 1)] for a, b in
                      ((kx, ky), (kx + 1, ky), (kx + 1, ky + 1),
                       (kx, ky + 1))]
                elems.append('    <elem eid="%d" shape="hex8" nodes="%s" />'
                             % (e, " ".join(str(n) for n in c)))
                e += 1
    return nodes, elems


def _xfem_liml(group, selection):
    nodes, elems = _block(4, 3, 1, 0.1, 0.1, 0.02, y0=-0.05)
    lines = (['<liml version="34">', '  <analysis type="S30" />'] + nodes +
             ['  <elset name="Plaat" material="M">'] + elems +
             ['  </elset>', '  <fixed selection="Onder" />',
              '  <ccxmodeldefinition>** ASTER-XFEM vorm=HALFVLAK, '
              'front=(0.05, 0, 0), normaal=(0, 1, 0), richting=(1, 0, 0), '
              'groep=&lt;&lt;%s&gt;&gt;</ccxmodeldefinition>' % group,
              '  <mat name="M">', STEEL, '  </mat>',
              '  <faceselection name="Onder">' + _faces(
                  (1, 3), (2, 3), (3, 3), (4, 3)) + '</faceselection>',
              '  <elementselection name="%s">' % selection +
              "".join('<element eid="%d" />' % e for e in range(1, 13)) +
              '</elementselection>', '</liml>'])
    return "\n".join(lines)


def test_xfem_group():
    md, comm, exc = _run(_xfem_liml("Enri zone", "Enri zone"),
                         "lin_static_3d")
    check(comm is not None and "GROUP_MA_ENRI='Enri_zone'" in comm,
          "XFEM groep=<<Enri zone>>: GROUP_MA_ENRI with the renamed group "
          "({0})".format(_errors()[:1]))
    md, comm, exc = _run(_xfem_liml("Andere", "Enri zone"), "lin_static_3d")
    check(comm is None and [m for m in _errors() if "'Andere'" in m],
          "XFEM groep=<<Andere>> without that selection: ERROR")


# ---------- thermal ----------
_TH01C = os.path.join(_HERE, "..", "TestFiles", "Verificatie", "modellen",
                      "TH-01c.liml")


def _thermal_liml(extra):
    """TH-01c (hex8 wall, convection on 'Rechts') plus a heat flux on
    'Rechts' and, not modelled (no thermal properties), a separate hex8
    (elset 'Los'), a quad4 shell and a line2 beam. extra: which of them
    also has a face in 'Rechts' (None, "solid" face 4, "shell" face 5,
    "beam" end 2)."""
    with io.open(_TH01C, encoding="utf-8") as f:
        s = f.read()
    n = len(re.findall(r"<node nid=\"[0-9]+\" x=", s))
    nodes, elems = _block(1, 1, 1, 0.02, 0.02, 0.02, x0=0.5, eid0=6,
                          nid0=n + 1)
    n += 8
    for i, (x, y) in enumerate(((0.6, 0.0), (0.62, 0.0), (0.62, 0.02),
                                (0.6, 0.02), (0.7, 0.0), (0.72, 0.0))):
        nodes.append('  <node nid="%d" x="%r" y="%r" z="0.0" />' % (
            n + 1 + i, x, y))
    s = s.replace("  <elset ", "\n".join(nodes) + "\n  <elset ", 1)
    extra_elsets = "\n".join([
        '  <elset name="Los" material="Mech">'] + elems + [
        '  </elset>',
        '  <elset name="Schaal" material="MechS">',
        '    <elem eid="7" shape="quad4" nodes="%d %d %d %d" />' % (
            n + 1, n + 2, n + 3, n + 4),
        '  </elset>',
        '  <elset name="Balk" material="MechB">',
        '    <elem eid="8" shape="line2" nodes="%d %d" />' % (n + 5, n + 6),
        '  </elset>', ''])
    s = s.replace("  <temperature2", extra_elsets + "  <temperature2", 1)
    extra_mats = "\n".join([
        '  <mat name="Mech">', '    ' + STEEL, '  </mat>',
        '  <mat name="MechS">',
        '    <geometric type="Plate" thickness="2 mm" />', '    ' + STEEL,
        '  </mat>',
        '  <mat name="MechB">',
        '    <geometric type="CircularBar" roundod="20 mm" />',
        '    ' + STEEL, '  </mat>', ''])
    s = s.replace("  <mat ", extra_mats + "  <mat ", 1)
    s = s.replace("</convectionbc>", "</convectionbc>\n  <heatflux "
                  u'selection="Rechts"><value>1000 W/m²</value>'
                  "</heatflux>", 1)
    face = {"solid": (6, 4), "shell": (7, 5), "beam": (8, 2)}.get(extra)
    if face:
        s = s.replace('<face eid="5" faceid="4" />',
                      '<face eid="5" faceid="4" />\n    '
                      '<face eid="%d" faceid="%d" />' % face)
    return s


def _groups(comm, pattern):
    return re.findall(pattern, comm or "")


def test_thermal_inactive_faces():
    for extra in (None, "beam"):
        md, comm, exc = _run(_thermal_liml(extra), "ther_3d")
        check(comm is not None and
              "_F(GROUP_MA='Rechts', FLUN=1000.0)" in comm,
              "thermal, only modelled faces{0}: the selection group "
              "itself".format(" and a beam end" if extra else ""))
    for extra in ("solid", "shell"):
        md, comm, exc = _run(_thermal_liml(extra), "ther_3d")
        ok = comm is not None
        echange = _groups(comm, r"_F\(GROUP_MA='(\w+)', COEF_H=")
        flux = _groups(comm, r"_F\(GROUP_MA='(\w+)', FLUN=")
        peau = _groups(comm, r"ORIE_PEAU=_F\(GROUP_MA_PEAU=\(([^)]*)\)")
        lists = dict(_groups(comm, r"_F\(NOM='(\w+)', MAILLE=\(([^)]*)\)\)"))
        grp = flux[0] if flux else None
        check(ok and grp and grp != "Rechts" and echange == [grp] and
              peau and "'Rechts'" not in peau[0] and
              "'%s'" % grp in peau[0] and
              "_F(GROUP_MA=('Rechts',)" not in comm,
              "thermal, a non-modelled {0} face in 'Rechts': ECHANGE, "
              "FLUX_REP, ORIE_PEAU and AFFE_MODELE use a subgroup ({1}, {2}, "
              "{3})".format(extra, echange, flux, peau))
        # the subgroup is a MAILLE list with exactly the one active skin cell
        cells = [c.strip(" '") for c in lists.get(grp, "").split(",")
                 if c.strip(" '")]
        names = md.get("cell_names", []) if md else []
        inv = dict((tuple(p), k) for k, ps in (md or {}).get(
            "skin_parents", {}).items() for p in ps)
        want = names.index(inv.get((5, 4), "?")) + 1 if inv.get(
            (5, 4)) in names else None
        check(want is not None and cells == ["M{0}".format(want)],
              "thermal subgroup ({0}): only the skin cell of element 5 ({1}, "
              "want M{2})".format(extra, cells, want))


def main():
    try:
        test_shell_force()
        test_shell_supports_both_sides()
        test_xfem_group()
        test_thermal_inactive_faces()
    finally:
        bridge_utils.CONFIG_BRIDGE.clear()
        bridge_utils.CONFIG_BRIDGE.update(_SAVED)
    print("{0} failure(s)".format(len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
