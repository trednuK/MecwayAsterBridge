# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_manifest.py (Python 2.7 and 3, without Mecway and
# Code-Aster): the setting keep_base, the base line in the .export, the
# manifest, the fingerprint and the clean-up of old bases. Schema 2 on small
# self-made models through the real translation (.liml -> write_mesh ->
# generate_AsterSolver_files): shell plates, a beam frame with orientations
# and a flexible joint, a line3 beam, trusses, element offsets, a tie with an
# RBE3 and a constraint equation; compared with the .comm and the mesh file
# where Code-Aster gets the same data.
#
#   python tests/test_bridge_manifest.py

from __future__ import print_function

import copy
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_REPO = os.path.join(_HERE, "..")
sys.path.insert(0, os.path.join(_REPO, "Scripts"))
sys.path.insert(0, os.path.join(_REPO, "TestFiles", "Verificatie"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_manifest as bm  # noqa: E402

LOG = []
bm.log = LOG.append
_FAILED = []
_CONFIG = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _model():
    return {
        "mesh_nodes": {1: (0.0, 0.0, 0.0), 2: (0.1, 0.0, 0.0),
                       3: (0.1, 0.2, 0.0), 4: (0.0, 0.2, 0.3)},
        "mesh_elements": [(7, "tet4", [1, 2, 3, 4], "P")],
        "configuration": None,
        "skin_parents": {"K1": [[7, 1]], "K2": [[7, 2]]},
        "cell_names": ["M2", "M1", "K1"],
        "deformation_by_elset": {"P": "GDEF_LOG"},
        "elset_modelisations": {"P": "3D"},
        # as note_mesh leaves it for a plain solid
        "manifest_mesh": {"beam_axes": {}, "excentrement": {},
                          "not_shared": {}},
    }


def test_fingerprint():
    n = {1: (0.0, 0.0, 0.0), 2: (0.1, -0.2, 0.3)}
    a = bm.mesh_fingerprint(n, [5, 6])
    check(a == bm.mesh_fingerprint(dict(reversed(list(n.items()))), [6, 5]),
          "fingerprint does not depend on the order")
    check(a != bm.mesh_fingerprint({1: n[1], 2: (0.1, -0.2, 0.300000002)},
                                   [5, 6]),
          "a shift of 2 nm changes the fingerprint")
    check(a == bm.mesh_fingerprint({1: n[1], 2: (0.1, -0.2, 0.3000000001)},
                                   [5, 6]),
          "a shift of 0.1 nm does not")
    check(a != bm.mesh_fingerprint(n, [5, 7]), "element ids count")
    check(a != bm.mesh_fingerprint({1: n[1], 3: n[2]}, [5, 6]),
          "node ids count")
    check(len(a) == 64, "sha256 hex")


def test_run_name_split():
    check(bm.split_run_name("Beam_A_20261107_101500") ==
          ("Beam_A", "20261107_101500"), "model and run id")
    check(bm.split_run_name("study") == ("study", None), "outside a run")


def test_bases_to_remove():
    runs = ["20261101_100000", "20261102_100000", "20261103_100000",
            "20261104_100000"]
    names = ["M_{0}_base".format(r) for r in runs]
    names += ["M_{0}_manifest.json".format(r) for r in runs]
    names += ["M_B_20261101_100000_base", "M_B_20261101_100000_manifest.json",
              "M_x_base", "other", "M_20261105_100000_base"]
    check(bm.bases_to_remove(names, "M", 2) ==
          ["M_20261101_100000_base", "M_20261102_100000_base"],
          "oldest usable of this model only; a base without manifest "
          "does not count")
    check(bm.bases_to_remove(names, "M", 10) == [], "fewer than keep")
    check(bm.orphan_bases(names, "M", None) == ["M_20261105_100000_base"],
          "a base without manifest is an orphan")
    check(bm.orphan_bases(names, "M", "M_20261105_100000_base") == [],
          "but not that of the current run")
    check(bm.bases_to_remove(names, "M", 0) == names[:3],
          "at least the newest one stays")


def test_prune(tmp):
    for run in ("20261101_100000", "20261102_100000", "20261103_100000"):
        base = os.path.join(tmp, "M_{0}_base".format(run))
        os.mkdir(base)
        with open(os.path.join(base, "glob.1"), "w") as f:
            f.write("x")
        with open(os.path.join(tmp, "M_{0}_manifest.json".format(run)),
                  "w") as f:
            f.write("{}")
    os.mkdir(os.path.join(tmp, "M_20261102_100000_base", "sub"))
    bm.prune_bases(tmp, "M", 1)
    left = sorted(os.listdir(tmp))
    check("M_20261101_100000_base" not in left and
          "M_20261101_100000_manifest.json" not in left,
          "old base removed with its manifest")
    check("M_20261102_100000_base" in left and
          "M_20261102_100000_manifest.json" in left,
          "a folder with a subfolder stays, with its manifest")
    check("M_20261103_100000_base" in left, "newest stays")


def _read(path):
    # Closed at once: IronPython has no reference counting
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _export(tmp):
    path = os.path.join(tmp, "M_20261107_101500.export")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"P memory_limit 2048\nF comm x.comm D 1")
    return path


def test_finish_export(tmp):
    cfg = bridge_utils.CONFIG_BRIDGE
    bridge_utils.set_run_log("20261107_101500", "M.liml")
    bm.run_name = bridge_utils.run_name
    path = _export(tmp)
    cfg["keep_base"] = False
    static = {"solver_command": "MECA_STATIQUE"}
    nonlin = {"solver_command": "STAT_NON_LINE", "deformation": "GROT_GDEP"}
    check(not bm.prepare_base(path, tmp, _model(), static, False, False),
          "setting off: nothing")
    check(_read(path).count("R base") == 0,
          "setting off: .export unchanged")

    cfg["keep_base"] = True
    for analysis, adaptive in (({"solver_command": "CALC_MODES"}, False),
                               (static, True)):
        check(not bm.prepare_base(path, tmp, _model(), analysis, adaptive,
                                  False),
              "no base for {0}, adaptive {1}".format(analysis, adaptive))
    check(_read(path).count("R base") == 0,
          "still no base line")

    # A good older run of this model stays when a new run fails
    old = os.path.join(tmp, "M_20261101_100000")
    os.mkdir(old + "_base")
    with open(old + "_manifest.json", "w") as f:
        f.write("{}")
    cfg["keep_base_runs"] = 1
    model = _model()
    check(bm.prepare_base(path, tmp, model, nonlin, False, True),
          "static: base kept")
    check(os.listdir(tmp).count("M_20261107_101500_manifest.json") == 0,
          "no manifest before the run")
    with open(os.path.join(tmp, "M_20261107_101500_base", "glob.1"), "w") as f:
        f.write("x")
    check(not bm.finish_run(tmp, model, path, False), "failed run: no manifest")
    check(not os.path.exists(os.path.join(tmp, "M_20261107_101500_base")),
          "failed run: its base folder is gone")
    check(os.path.isdir(old + "_base") and
          os.path.exists(old + "_manifest.json"),
          "failed run: the older good base stays")
    os.mkdir(os.path.join(tmp, "M_20261107_101500_base"))
    check(bm.finish_run(tmp, model, path, True, "17.4"), "good run")
    check(not os.path.exists(old + "_base") and
          not os.path.exists(old + "_manifest.json"),
          "good run: the older base goes, keep_base_runs 1")
    cfg["keep_base_runs"] = 3
    text = _read(path)
    base = os.path.join(tmp, "M_20261107_101500_base")
    check("\nR base {0} R 0".format(base) in text, "base line in the .export")
    check(os.path.isdir(base), "base folder exists")
    man = json.loads(_read(os.path.join(
        tmp, "M_20261107_101500_manifest.json")))
    check(man["schema"] == 2 and man["run_id"] == "20261107_101500" and
          man["model"] == "M", "run and model")
    check(man["aster_version"] == "17.4", "version that really ran")
    check(man["extra_nodes"] is False, "no extra nodes")
    check(man["deformation"] == "GROT_GDEP", "choice of the run")
    check(man["deformation_by_component"] == {"P": "GDEF_LOG"},
          "what the component computed with")
    check(man["memory_limit"] == 2048, "memory limit from the .export")
    check(man["solver"] == "STAT_NON_LINE", "solver")
    check(man["base"] == "M_20261107_101500_base", "base without a path")
    check(man["concepts"]["result"] == "res" and
          man["concepts"]["cara"] == "cara", "concept names")
    check(man["cells"] == ["M2", "M1", "K1"], "cells in file order")
    check(man["skin"] == {"K1": [[7, 1]], "K2": [[7, 2]]}, "skin parents")
    check(man["not_shared"] == {}, "nothing special")
    check(man["components"] == {"P": {"model": "3D", "has_warping": False}},
          "a solid component: model only")
    check(man["coef_rigi_drz"] is None and man["beam_axes"] == {} and
          man["excentrement"] == {}, "schema 2 keys of a solid")
    check(set(man) == set(_SCHEMA1_KEYS) | set(_SCHEMA2_KEYS),
          "every key of schema 1 stays, plus those of schema 2: {0}".format(
              sorted(man)))
    check(tmp not in json.dumps(man), "no paths in the manifest")

    # Without the data of note_mesh: no manifest, the run goes on
    del LOG[:]
    model = _model()
    del model["manifest_mesh"]
    os.remove(os.path.join(tmp, "M_20261107_101500_manifest.json"))
    check(bm.prepare_base(path, tmp, model, nonlin, False, True),
          "base kept again")
    check(not bm.finish_run(tmp, model, path, True, "17.4") and
          not os.path.exists(os.path.join(
              tmp, "M_20261107_101500_manifest.json")) and
          any("Writing the manifest failed" in l for l in LOG),
          "no mesh data: no manifest, a WARNING")
    cfg["keep_base"] = False
    bridge_utils.set_run_log(None)


_SCHEMA1_KEYS = ("schema", "run_id", "model", "configuration", "analysis",
                 "solver", "aster_version", "memory_limit", "deformation",
                 "deformation_by_component", "base", "fingerprint",
                 "concepts", "cells", "skin", "not_shared", "extra_nodes")
_SCHEMA2_KEYS = ("components", "coef_rigi_drz", "beam_axes", "excentrement")


def test_deformation_by_component():
    md = {"deformation_by_elset": {"F": "GROT_GDEP", "F_TRUSS": "PETIT",
                                   "G": "PETIT", "G_TRUSS": "PETIT"},
          "group_renames": {"Part one": "P1"}}
    md["deformation_by_elset"]["P1"] = "GDEF_LOG"
    check(bm._deformation_by_component(md) ==
          {"F": "MIXED", "G": "PETIT", "Part one": "GDEF_LOG"},
          "truss part joins its component; a difference shows as MIXED")


def test_orphan_age(tmp):
    young = os.path.join(tmp, "M_20261106_100000_base")
    old = os.path.join(tmp, "M_20261105_100000_base")
    os.mkdir(young)
    os.mkdir(old)
    past = bm.time.time() - 2 * bm.ORPHAN_AGE
    os.utime(old, (past, past))
    bm.prune_bases(tmp, "M", 3)
    check(os.path.isdir(young), "a young base without manifest stays")
    check(not os.path.exists(old), "an old one goes")


def test_not_shared():
    nodes = dict((n, (0.0, 0.0, float(n))) for n in range(1, 13))
    conn = {1: ("SEG2", [1, 2]), 2: ("QUAD4", [3, 4, 5, 6]),
            3: ("SEG2", [7, 8])}
    elements = [(1, "line2", [1, 2], "Gap"), (2, "quad4", [3, 4, 5, 6], "P"),
                (3, "line2", [7, 8], "B")]
    faces = {"Face": [{"nodes": [3, 4]}, {"nodes": [4, 5]}]}
    md = {"node_groups": {"Master": ["N9"], "Two": [10, "11"]},
          "element_selections": {"Plate": [2, 99]},
          "offset_links": [{"orig": 7, "new": 101}, {"orig": 8, "new": 102}],
          "discrete_sections": {"Gap": {"kind": "gap"}},
          "contacts": [{"master": "Face", "slave": "Two"}],
          "bonded": [{"master": "Plate", "slave": "Master"}],
          "couplings": [{"master_group": "Master", "slave_group": "Face"}],
          "constraint_equations": [
              {"terms": [(12, "DX", 1.0), (1, "DX", -1.0)], "constant": 0.0},
              {"terms": [(5, "DY", 1.0), (3, "DY", -0.5), (4, "DY", -0.5)],
               "source": "line3truss"},
              {"terms": [(103, "DX", 1.0), (7, "DX", -1.0)],
               "source": "flexiblejoint"},
              {"terms": [(6, "DX", 1.0), (104, "DX", -1.0)],
               "source": "pretension"},
              {"terms": [(2, "DZ", 1.0)], "source": "future"}],
          "pretension_sections": [1],
          "flexible_joints": [{"selection": "Two"}]}
    md["constraint_equations"].append(
        {"terms": [(4, "DZ", 1.0), (5, "DZ", -0.5), (3, "DZ", -0.5)],
         "source": "line3truss"})         # same nodes: one group
    md["constraint_equations"].append(
        {"terms": [(10, "DY", 1.0), (11, "DY", -1.0)],
         "source": "line3truss"})         # another element
    del LOG[:]
    got = bm._not_shared(md, nodes, conn, elements, faces)
    want = {"offset": {"nodes": [7, 8], "origin": "bridge",
                       "groups": [[7], [8]]},
            "discrete": {"nodes": [1, 2], "origin": "user",
                         "groups": [[1, 2]]},
            "contact": {"nodes": [3, 4, 5, 10, 11], "origin": "user",
                        "groups": [[3, 4, 5, 10, 11]]},
            "bonded": {"nodes": [3, 4, 5, 6, 9], "origin": "user",
                       "groups": [[3, 4, 5, 6, 9]]},
            "coupling": {"nodes": [3, 4, 5, 9], "origin": "user",
                         "groups": [[3, 4, 5, 9]]},
            "constraint": {"nodes": [1, 12], "origin": "user",
                           "groups": [[1, 12]]},
            "line3truss": {"nodes": [3, 4, 5, 10, 11], "origin": "bridge",
                           "groups": [[3, 4, 5], [10, 11]]},
            # the Mecway node of its relations only, not the selection
            "flexible_joint": {"nodes": [7], "origin": "bridge",
                               "groups": [[7]]},
            "pretension": {"nodes": [6], "origin": "bridge",
                           "groups": [[6]]},
            "future": {"nodes": [2], "origin": "bridge", "groups": [[2]]}}
    for kind in sorted(set(want) | set(got)):
        check(got.get(kind) == want.get(kind),
              "not_shared {0}: {1}".format(kind, got.get(kind)))
    check(not any("without nodes" in l for l in LOG),
          "no WARNING when every user kind has nodes")
    check(bm._not_shared({}, nodes, conn, elements, faces) == {},
          "nothing: an empty dict")
    only_bridge = {"constraint_equations": [
        {"terms": [(5, "DY", 1.0)], "source": "line3truss"}]}
    check(sorted(bm._not_shared(only_bridge, nodes, conn, elements, faces))
          == ["line3truss"],
          "bridge relations only: no 'constraint' kind")
    lost = {"couplings": [{"master_group": "Gone", "slave_group": "Gone"}]}
    got = bm._not_shared(lost, nodes, conn, elements, faces)
    check(got == {"coupling": {"nodes": [], "origin": "user", "groups": []}}
          and any("coupling without nodes" in l for l in LOG),
          "a coupling on an unknown selection: there, empty, a WARNING")


def test_note_mesh_failure():
    """A problem in note_mesh: a WARNING, manifest_mesh None, so no
    manifest after the run; never an exception into write_mesh."""
    cfg = bridge_utils.CONFIG_BRIDGE
    md = {}
    cfg["keep_base"] = False
    bm.note_mesh(md, {}, {}, [], {}, None, {"BOR1": ["M1"]}, {}, set())
    check("manifest_mesh" not in md, "setting off: note_mesh does nothing")
    cfg["keep_base"] = True
    del LOG[:]
    bm.note_mesh(md, {}, {}, [], {}, None, {"BOR1": ["M1"]}, {}, set())
    check(md.get("manifest_mesh", 1) is None and
          any("Data for the manifest not collected" in l for l in LOG),
          "broken input: None and a WARNING")
    nodes = {1: (0.0, 0.0, 0.0), 2: (0.0, 0.0, 0.0), 3: (1.0, 0.0, 0.0)}
    conn = {1: ("SEG2", [1, 2]), 2: ("SEG2", [2, 3])}
    bm.note_mesh(md, nodes, conn, [], {}, None, {"BOR1": ["M1", "M2"]},
                 {"BOR1": (0.0, 1.0, 0.0)}, set())
    check(sorted(md["manifest_mesh"]["beam_axes"]) == ["M2"] and
          any("M1 has length 0" in l for l in LOG),
          "a beam cell of length 0: left out with a WARNING, the rest stays")
    cfg["keep_base"] = False


def test_linear_contact():
    """Unilateral contact is not in a MECA_STATIQUE run: not in not_shared."""
    md = _model()
    md["manifest_mesh"]["not_shared"] = {
        "contact": {"nodes": [1], "origin": "user", "groups": [[1]]},
        "bonded": {"nodes": [2], "origin": "user", "groups": [[2]]}}
    for solver, kinds in (("MECA_STATIQUE", ["bonded"]),
                          ("STAT_NON_LINE", ["bonded", "contact"])):
        man = bm.build_manifest(md, {"solver": solver, "has_cara": False,
                                     "deformation": "PETIT"}, None, "17.4",
                                None)
        check(sorted(man["not_shared"]) == kinds,
              "{0}: not_shared {1}".format(solver, sorted(man["not_shared"])))
    check(sorted(md["manifest_mesh"]["not_shared"]) == ["bonded", "contact"],
          "the data of note_mesh stay as they are")


# ==========================================
# Schema 2 through the real translation
# ==========================================
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
RECT = '<geometric type="RectBar" recta="10 mm" rectb="20 mm" />'
PLATE = '<geometric type="Plate" thickness="2 mm" />'
_RUN = "20261109_100000"


def _close(a, b, tol=1e-12):
    """a and b equal to tol: numbers, or (nested) lists of numbers."""
    if isinstance(a, (list, tuple)):
        return (isinstance(b, (list, tuple)) and len(a) == len(b) and
                all(_close(x, y, tol) for x, y in zip(a, b)))
    return abs(float(a) - float(b)) <= tol


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def _translate(model, keep=True, general=None, analysis="lin_static_3d"):
    """One translation as from Mecway, without Code-Aster: (manifest read
    back from its JSON file, model_data, .comm text, mesh text, log). keep:
    the setting keep_base."""
    import bridge_from_liml
    import bridge_mesh
    import bridge_to_aster
    cfg = bridge_utils.CONFIG_BRIDGE
    cfg.clear()
    cfg.update(copy.deepcopy(_CONFIG))
    cfg.update(general or {})
    cfg["keep_base"] = keep
    cfg["active_analysis"] = analysis
    tmp = tempfile.mkdtemp(prefix="mab_manifest_")
    try:
        cfg["work_dir"] = tmp
        path = model.write(os.path.join(tmp, "M.liml"))
        bridge_utils.set_run_log(_RUN, path)
        bm.run_name = bridge_utils.run_name
        md = bridge_from_liml.extract_aster_data_from_liml(path)
        mail = os.path.join(tmp, bridge_utils.run_name(".mail"))
        ok = md is not None and bridge_mesh.write_mesh(mail, md)
        exp = ok and bridge_to_aster.generate_AsterSolver_files(
            tmp, md, mail, bridge_utils.run_name(".resu"))
        comm = (_read(os.path.join(tmp, bridge_utils.run_name(".comm")))
                .replace(tmp.replace("\\", "\\\\"), "<T>")
                .replace(tmp, "<T>") if exp else None)
        mesh = _read(mail) if ok else None
        man = None
        if exp and keep and bm.finish_run(tmp, md, exp, True, "17.4"):
            man = json.loads(_read(os.path.join(
                tmp, bridge_utils.run_name(bm.MANIFEST_SUFFIX))))
        log = _read(bridge_utils.log_path())
        return man, md, comm, mesh, log
    finally:
        bridge_utils.set_run_log(None)
        cfg.clear()
        cfg.update(copy.deepcopy(_CONFIG))
        shutil.rmtree(tmp, ignore_errors=True)


def _vect_y(comm, mesh):
    """{cell: VECT_Y} as the .comm gives it to Code-Aster, through the
    ORIENTATION groups of the mesh file."""
    groups = {}
    for name, body in re.findall(r"GROUP_MA\n (\w+)\n(.*?)FINSF", mesh, re.S):
        groups[name] = body.split()
    out = {}
    for group, vals in re.findall(
            r"_F\(GROUP_MA='(\w+)', CARA='VECT_Y', VALE=\(([^)]*)\)\)", comm):
        v = [float(x) for x in vals.split(",")]
        for cell in groups.get(group, []):
            out[cell] = v
    return out


def _seg2_x(mesh):
    """{cell: unit vector node 1 -> node 2} of the SEG2 cells of the mesh
    file, with the coordinates of that file."""
    xyz = {}
    coor = re.search(r"COOR_3D\n(.*?)FINSF", mesh, re.S).group(1)
    for line in coor.splitlines():
        parts = line.split()
        if len(parts) == 4:
            xyz[parts[0]] = [float(c) for c in parts[1:]]
    out = {}
    for body in re.findall(r"\nSEG2\n(.*?)FINSF", mesh, re.S):
        cell = None
        cells = {}
        for tok in body.split():
            if tok.startswith("N") and cell is not None:
                cells[cell].append(tok)
            else:
                cell = tok
                cells[cell] = []
        for cell, (a, b) in cells.items():
            out[cell] = _unit([xyz[b][i] - xyz[a][i] for i in range(3)])
    return out


def _check_axes(man, comm, mesh, label):
    """beam_axes: right handed and orthonormal, y = the VECT_Y of the .comm
    (made perpendicular to x), x along the cell of the mesh file."""
    vy = _vect_y(comm, mesh)
    seg = _seg2_x(mesh)
    for cell, axes in man["beam_axes"].items():
        check(cell in seg and _close(axes[0], seg[cell], 1e-12),
              "{0}: {1} x from node 1 to node 2 of the mesh cell".format(
                  label, cell))
    check(set(man["beam_axes"]) == set(vy),
          "{0}: beam_axes for exactly the cells with VECT_Y: {1} / {2}"
          .format(label, sorted(man["beam_axes"]), sorted(vy)))
    for cell, (x, y, z) in man["beam_axes"].items():
        cross = [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2],
                 x[0] * y[1] - x[1] * y[0]]
        check(_close(cross, z, 1e-12) and
              _close([sum(a * b for a, b in zip(p, q))
                      for p, q in ((x, x), (y, y), (x, y))],
                     [1.0, 1.0, 0.0], 1e-12),
              "{0}: {1} orthonormal, z = x cross y".format(label, cell))
        if cell in vy:
            check(_close(y, _unit(vy[cell]), 1e-9),
                  "{0}: {1} y is VECT_Y {2}".format(label, cell, vy[cell]))


def _frame():
    """Column along Z (Mecway's default V), beam along X with orientation
    vectors (one with an angle), a flexible joint at the corner."""
    from verif_lib import Model
    m = Model("S30")
    m.elset("Frame", "Steel")
    m.mat("Steel", STEEL, RECT)
    p = [m.node(*xyz) for xyz in ((0, 0, 0), (0, 0, 0.5), (0, 0, 1),
                                 (0.5, 0, 1), (1, 0, 1), (1.5, 0, 1))]
    vz = 'orientationvx="0" orientationvy="0" orientationvz="1"'
    e = [m.elem("Frame", "line2", [p[0], p[1]]),
         m.elem("Frame", "line2", [p[1], p[2]]),
         m.elem("Frame", "line2", [p[2], p[3]], vz),
         m.elem("Frame", "line2", [p[3], p[4]], vz + ' angle="90 deg"'),
         m.elem("Frame", "line2", [p[4], p[5]])]
    m.node_selection("Base", [p[0]])
    m.node_selection("Tip", [p[5]])
    m.face_selection("FJ", [(e[2], 2)])         # node 1 of element 3
    m.add('<fixed selection="Base" />')
    m.add('<force selection="Tip"><x>0 N</x><y>5 N</y><z>-10 N</z></force>')
    m.add('<flexiblejoint selection="FJ"><rotw /></flexiblejoint>')
    return m, p, e


def test_frame():
    m, p, e = _frame()
    man, md, comm, mesh, log = _translate(m)
    check(man is not None, "frame: manifest\n" + log[-2000:])
    if man is None:
        return
    check(man["schema"] == 2, "frame: schema 2")
    check(man["components"] == {"Frame": {
        "model": "POU_D_E", "has_warping": False,
        "section": {"cara": ["HY", "HZ"], "vale": [0.01, 0.02],
                    "shape": "RECTANGLE", "mecway_shape": "RectBar"}}},
        "frame: component {0}".format(man["components"]))
    check("SECTION='RECTANGLE',\n           CARA=('HY', 'HZ',),\n"
          "           VALE=(0.01, 0.02,)" in comm,
          "frame: the .comm has the same section")
    check(man["coef_rigi_drz"] is None, "frame: coef_rigi_drz null")
    X, Y, Z = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]

    def neg(v):
        return [-c for c in v]
    want = {"M%d" % e[0]: [Z, Y, neg(X)],    # along Z: V = Y (Mecway)
            "M%d" % e[1]: [Z, Y, neg(X)],
            "M%d" % e[2]: [X, Z, neg(Y)],    # vector Z
            "M%d" % e[3]: [X, neg(Y), neg(Z)],   # vector Z, 90 degrees
            "M%d" % e[4]: [X, Y, Z]}         # default V = Z x U
    check(sorted(man["beam_axes"]) == sorted(want),
          "frame: one entry per cell")
    for cell, axes in want.items():
        check(_close(man["beam_axes"].get(cell), axes, 1e-12),
              "frame: axes of {0}: {1}".format(cell,
                                              man["beam_axes"].get(cell)))
    _check_axes(man, comm, mesh, "frame")
    check(man["not_shared"] == {"flexible_joint": {
        "nodes": [p[2]], "origin": "bridge", "groups": [[p[2]]]}},
          "frame: the joint at its Mecway node only: {0}".format(
              man["not_shared"]))
    check(man["excentrement"] == {}, "frame: no excentrement")
    check(man["deformation"] == "PETIT" and
          man["deformation_by_component"] == {},
          "frame: deformation as schema 1 (linear: PETIT, none per "
          "component)")


def test_setting_off_untouched():
    """keep_base off: the same mesh and .comm as with keep_base on, and no
    manifest data in model_data."""
    m = _frame()[0]
    _man, md_on, comm_on, mesh_on, _log = _translate(m, keep=True)
    man_off, md_off, comm_off, mesh_off, _log = _translate(m, keep=False)
    check(man_off is None and "manifest_mesh" not in md_off and
          "kept_base" not in md_off, "setting off: no manifest data")
    check(mesh_on == mesh_off and mesh_on is not None,
          "setting off: the same mesh file")
    check(comm_on == comm_off and comm_on is not None,
          "setting off: the same .comm")


def test_line3_beam():
    from verif_lib import Model
    m = Model("S30")
    m.elset("Arc", "Steel")
    m.mat("Steel", STEEL, RECT)
    a, mid, b = m.node(0, 0, 0), m.node(0.5, 0.1, 0), m.node(1, 0, 0)
    eid = m.elem("Arc", "line3", [a, mid, b])
    m.node_selection("Base", [a])
    m.node_selection("Tip", [b])
    m.add('<fixed selection="Base" />')
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-10 N</z></force>')
    man, md, comm, mesh, log = _translate(m, general={"elem_beam": "POU_D_T"})
    check(man is not None, "line3: manifest\n" + log[-2000:])
    if man is None:
        return
    check(man["components"]["Arc"]["model"] == "POU_D_T" and
          man["components"]["Arc"]["has_warping"] is False,
          "line3: POU_D_T")
    sec = man["components"]["Arc"]["section"]
    beam = md["beam_sections"]["Arc"]
    check(sec["cara"] == list(beam["cara"]) and
          _close(sec["vale"], beam["vale"], 0.0) and
          sec["shape"] == beam["aster_section"],
          "line3: section as written to AFFE_CARA_ELEM {0}".format(sec))
    s = math.sqrt(0.26)
    want = {"M%d" % eid: [[0.5 / s, 0.1 / s, 0.0], [-0.1 / s, 0.5 / s, 0.0],
                          [0.0, 0.0, 1.0]],
            "H%d" % eid: [[0.5 / s, -0.1 / s, 0.0], [0.1 / s, 0.5 / s, 0.0],
                          [0.0, 0.0, 1.0]]}
    check(sorted(man["beam_axes"]) == sorted(want),
          "line3: both halves {0}".format(sorted(man["beam_axes"])))
    for cell, axes in want.items():
        check(_close(man["beam_axes"].get(cell), axes, 1e-12),
              "line3: axes of {0}: {1}".format(cell,
                                              man["beam_axes"].get(cell)))
    _check_axes(man, comm, mesh, "line3")
    check(man["not_shared"] == {}, "line3 beam: no relations")


def test_trusses():
    """A line3 truss (BARRE, midside relations by the bridge) and a
    component that mixes a beam and a truss."""
    from verif_lib import Model
    m = Model("S30")
    m.elset("Truss", "Steel")
    m.elset("Mix", "Steel")
    # a user component with the name the bridge would give the truss part
    m.elset("Mix_TRUSS", "Steel")
    m.mat("Steel", STEEL, RECT)
    a, b, c = m.node(0, 0, 0), m.node(0.5, 0, 0), m.node(1, 0, 0)
    d, e = m.node(1, 1, 0), m.node(2, 1, 0)
    f, g = m.node(1, 0.5, 0), m.node(1, 1, 0)
    t3 = m.elem("Truss", "line3", [a, b, c], 'truss="true"')
    t3b = m.elem("Truss", "line3", [c, f, g], 'truss="true"')
    beam = m.elem("Mix", "line2", [c, d])
    t2 = m.elem("Mix", "line2", [d, e], 'truss="true"')
    own = m.elem("Mix_TRUSS", "line2", [e, m.node(2, 2, 0)])
    m.node_selection("Fix", [a, e])
    m.node_selection("Load", [c])
    m.add('<fixed selection="Fix" />')
    m.add('<force selection="Load"><x>10 N</x><y>0 N</y><z>0 N</z></force>')
    man, md, comm, mesh, log = _translate(m)
    check(man is not None, "trusses: manifest\n" + log[-2000:])
    if man is None:
        return
    area = md["beam_sections"]["Truss"]["area"]
    check(_close(area, 2.0e-4, 1e-18), "trusses: area of the RectBar")
    bar = {"cara": ["A"], "vale": [area], "shape": "GENERALE",
           "mecway_shape": "RectBar"}
    check(man["components"].get("Truss") == {
        "model": "BARRE", "has_warping": False, "section": bar},
        "trusses: BARRE {0}".format(man["components"].get("Truss")))
    mix = man["components"].get("Mix", {})
    check(mix.get("model") == "POU_D_E" and
          mix.get("section", {}).get("cara") == ["HY", "HZ"] and
          mix.get("truss_part") == {"model": "BARRE", "has_warping": False,
                                    "section": bar, "elements": [t2]},
          "trusses: the truss part of a mixed component {0}".format(mix))
    check(md.get("truss_parts") == {"Mix": ["Mix_TRUSS2"]},
          "trusses: the bridge names the part Mix_TRUSS2 {0}".format(
              md.get("truss_parts")))
    check(man["components"].get("Mix_TRUSS", {}).get("model") == "POU_D_E"
          and "truss_part" not in man["components"].get("Mix_TRUSS", {}),
          "trusses: the user's component Mix_TRUSS stays its own")
    check(sorted(man["components"]) == ["Mix", "Mix_TRUSS", "Truss"],
          "trusses: no component of its own for the truss part")
    check(sorted(man["beam_axes"]) == sorted(["M%d" % beam, "M%d" % own]),
          "trusses: beam_axes only for the beam cells {0}".format(
              sorted(man["beam_axes"])))
    _check_axes(man, comm, mesh, "trusses")
    check(man["not_shared"] == {"line3truss": {
        "nodes": sorted([a, b, c, f, g]), "origin": "bridge",
        "groups": [sorted([a, b, c]), sorted([c, f, g])]}},
        "trusses: midside relations of the bridge, one group per element "
        "{0}".format(man["not_shared"]))
    check("CARA='A', VALE={0!r}".format(area) in comm,
          "trusses: the .comm has the same area")
    del t3, t3b


def _poutre(comm):
    """{group: (SECTION, [CARA], [VALE])} of AFFE_CARA_ELEM POUTRE."""
    out = {}
    for group, sec, cara, vale in re.findall(
            r"_F\(GROUP_MA='(\w+)',\s*SECTION='(\w+)',\s*CARA=\(([^)]*)\),"
            r"\s*VALE=\(([^)]*)\)\)", comm):
        out[group] = (sec, [c.strip().strip("'") for c in cara.split(",")
                            if c.strip()],
                      [float(v) for v in vale.split(",") if v.strip()])
    return out


def test_sections():
    """An I profile (GENERALE) with POU_D_T (AY, AZ) and POU_D_TG (warping
    extras): the section is what AFFE_CARA_ELEM got."""
    from verif_lib import Model
    iprof = ('<geometric type="I" ia="100 mm" ib="50 mm" ic="8 mm" '
             'id="5 mm" />')
    for beam, warping in (("POU_D_T", False), ("POU_D_TG", True)):
        m = Model("S30")
        m.elset("Girder", "Steel")
        m.mat("Steel", STEEL, iprof)
        p = [m.node(0.25 * i, 0, 0) for i in range(3)]
        for a, b in zip(p[:-1], p[1:]):
            m.elem("Girder", "line2", [a, b])
        m.node_selection("Base", [p[0]])
        m.node_selection("Tip", [p[-1]])
        m.add('<fixed selection="Base" />')
        m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-10 N</z>'
              '</force>')
        man, md, comm, mesh, log = _translate(m, general={"elem_beam": beam})
        check(man is not None, "sections {0}: manifest\n{1}".format(
            beam, log[-2000:]))
        if man is None:
            continue
        comp = man["components"].get("Girder", {})
        sec = comp.get("section", {})
        got = _poutre(comm).get("Girder")
        check(comp.get("model") == beam and
              comp.get("has_warping") is warping,
              "sections {0}: model and warping {1}".format(beam, comp))
        check(got is not None and sec.get("shape") == got[0] == "GENERALE"
              and sec.get("cara") == got[1] and
              _close(sec.get("vale"), got[2], 0.0) and
              sec.get("mecway_shape") == "I",
              "sections {0}: as in the .comm {1} / {2}".format(beam, sec, got))
        need = ["A", "IY", "IZ", "JX", "AY", "AZ"]
        if warping:
            need += ["JG", "EY", "EZ"]
        check(all(k in sec.get("cara", []) for k in need),
              "sections {0}: has {1}".format(beam, need))
        _check_axes(man, comm, mesh, "sections " + beam)


def test_cable():
    """A tension-only member (CABLE, nonlinear static): AIRE, no axes."""
    from verif_lib import Model
    m = Model("L30", timesteps={"timeperiod": "1 s", "stepsize": "1 s"})
    m.elset("Rope", "Cable")
    m.mat("Cable", '<mechanical type="TensionOnly" youngsmodulus='
          '"210000 MPa" />', RECT)
    a, b, c = m.node(0, 0, 0), m.node(1, 0, 0), m.node(2, 0, 0)
    m.elem("Rope", "line2", [a, b])
    m.elem("Rope", "line2", [b, c])
    m.node_selection("Fix", [a])
    m.node_selection("Tip", [c])
    m.node_selection("Mid", [b])
    m.add('<fixed selection="Fix" />')
    m.add('<displacement selection="Mid"><y>0 m</y><z>0 m</z>'
          '</displacement>')
    m.add('<displacement selection="Tip"><y>0 m</y><z>0 m</z>'
          '</displacement>')
    m.add('<force selection="Tip"><x time="0 s">0 N</x><x time="1 s">10 N'
          '</x><y>0 N</y><z>0 N</z></force>')
    man, md, comm, mesh, log = _translate(m, analysis="nonlin_static_3d")
    check(man is not None, "cable: manifest\n" + log[-2000:])
    if man is None:
        return
    area = md["cable_sections"]["Rope"]["area"]
    check(man["components"] == {"Rope": {
        "model": "CABLE", "has_warping": False,
        "section": {"cara": ["AIRE"], "vale": [area], "shape": None,
                    "mecway_shape": "RectBar"}}},
        "cable: component {0}".format(man["components"]))
    check("AIRE={0!r}".format(area) in comm, "cable: the .comm has AIRE")
    check(man["beam_axes"] == {} and man["solver"] == "STAT_NON_LINE",
          "cable: no beam_axes")


def test_pretension():
    """Pre-tension section (verification PT-01): relations of the bridge,
    Mecway nodes only."""
    import tests_boutvoorspanning
    m = tests_boutvoorspanning.build_pt01()
    man, md, comm, mesh, log = _translate(m)
    check(man is not None, "pretension: manifest\n" + log[-2000:])
    if man is None:
        return
    mecway = set(md["mesh_nodes"])
    want = set(t[0] for ce in md["constraint_equations"]
               if ce.get("source") == "pretension"
               for t in ce["terms"]) & mecway
    got = man["not_shared"].get("pretension", {})
    check(got.get("origin") == "bridge" and got.get("nodes") ==
          sorted(want) and want and set(got["nodes"]) <= mecway,
          "pretension: the Mecway nodes of its relations {0}".format(got))
    check(all(set(g) <= set(got.get("nodes", [])) and len(g) == 1
              for g in got.get("groups", [])),
          "pretension: one Mecway node per relation (its copy is left out)")


def test_shells():
    from verif_lib import Model, quadmesh, rect
    for elem_shell in ("DKT", "DST"):
        m = Model("S30")
        m.elset("P4", "Steel")
        m.elset("P8", "Steel")
        m.mat("Steel", STEEL, PLATE)
        q4 = quadmesh(m, "P4", 2, 2, rect(0, 0.2, 0, 0.2))
        q8 = quadmesh(m, "P8", 2, 1, rect(0.5, 0.7, 0, 0.1), order=2)
        m.face_selection("Fix", q4["edges"]["u0"] + q8["edges"]["u0"])
        m.node_selection("Load", sorted(q4["nodes"]["u1"]) +
                         sorted(q8["nodes"]["u1"]))
        m.add('<fixed selection="Fix" />')
        m.add('<force selection="Load"><x>0 N</x><y>0 N</y><z>-1 N</z>'
              '</force>')
        man, md, comm, mesh, log = _translate(
            m, general={"elem_shell": elem_shell})
        check(man is not None, "shells: manifest\n" + log[-2000:])
        if man is None:
            return
        check(man["components"] == {
            "P4": {"model": elem_shell, "has_warping": False},
            "P8": {"model": "COQUE_3D", "has_warping": False}},
            "shells {0}: components {1}".format(elem_shell,
                                                man["components"]))
        check("MODELISATION='{0}'".format(elem_shell) in comm and
              "MODELISATION='COQUE_3D'" in comm,
              "shells {0}: as in AFFE_MODELE".format(elem_shell))
        check(man["coef_rigi_drz"] is None and "COEF_RIGI_DRZ" not in comm,
              "shells: the bridge does not set COEF_RIGI_DRZ")
        check(man["beam_axes"] == {} and man["excentrement"] == {} and
              man["not_shared"] == {}, "shells: nothing else")
        check(man["extra_nodes"] is True, "shells: QUAD8 -> QUAD9")


def test_offsets():
    """DKT with EXCENTREMENT on one element, a beam with a rigid offset."""
    from verif_lib import Model, quadmesh, rect
    m = Model("S30")
    m.elset("Plate", "Steel")
    m.elset("Rib", "Bar")
    m.mat("Steel", STEEL, PLATE)
    m.mat("Bar", STEEL, RECT)
    q = quadmesh(m, "Plate", 2, 1, rect(0, 0.2, 0, 0.1))
    off = q["elems"][(1, 0)]
    r0, r1 = m.node(0, 0, 0), m.node(0.1, 0, 0)
    rib = m.elem("Rib", "line2", [r0, r1])
    m.element_selection("Off", [off])
    m.element_selection("RibSel", [rib])
    m.face_selection("Fix", q["edges"]["u0"])
    m.node_selection("Load", sorted(q["nodes"]["u1"]))
    m.add('<fixed selection="Fix" />')
    m.add('<force selection="Load"><x>0 N</x><y>0 N</y><z>-1 N</z></force>')
    m.add('<offset selection="Off"><u>0 m</u><v>0 m</v><w>5 mm</w>'
          '</offset>')
    m.add('<offset selection="RibSel"><x>0 m</x><y>0 m</y><z>10 mm</z>'
          '</offset>')
    man, md, comm, mesh, log = _translate(m)
    check(man is not None, "offsets: manifest\n" + log[-2000:])
    if man is None:
        return
    check(sorted(man["excentrement"]) == [str(off)] and
          _close(man["excentrement"][str(off)], 0.005, 1e-15),
          "offsets: EXCENTREMENT of the one element {0}".format(
              man["excentrement"]))
    check("EXCENTREMENT=0.005, INER_ROTA='OUI'" in comm,
          "offsets: the .comm has the same EXCENTREMENT")
    check(man["not_shared"] == {"offset": {
        "nodes": [r0, r1], "origin": "bridge", "groups": [[r0], [r1]]}},
          "offsets: the rigid arms of the beam {0}".format(
              man["not_shared"]))
    check(man["components"]["Plate"] == {"model": "DKT",
                                         "has_warping": False},
          "offsets: DKT")
    check(sorted(man["beam_axes"]) == ["M%d" % rib],
          "offsets: the offset beam keeps its cell name")
    _check_axes(man, comm, mesh, "offsets")


def test_tie_rbe3():
    """Block B tied to block A, an RBE3 from a free node to the top of B,
    a constraint equation of the user."""
    from verif_lib import Model, hexmesh, box
    m = Model("S30")
    m.elset("A", "Steel")
    m.elset("B", "Steel")
    m.mat("Steel", STEEL)
    a = hexmesh(m, "A", 2, 1, 2, box(0, 0.02, 0, 0.01, 0, 0.02))
    b = hexmesh(m, "B", 2, 1, 2, box(0, 0.02, 0.0100001, 0.02, 0, 0.02))
    master = m.node(0.01, 0.03, 0.01)
    m.face_selection("Fix", a["faces"]["v0"])
    m.face_selection("Top", a["faces"]["v1"])
    m.face_selection("Bottom", b["faces"]["v0"])
    m.face_selection("Load", b["faces"]["v1"])
    m.node_selection("Master", [master])
    m.add('<fixed selection="Fix" />')
    m.add('<contact2 selectionmaster="Top" selectionslave="Bottom" '
          'type="bondedtie"><tolerance>0 m</tolerance></contact2>')
    m.add('<nodesurfacecoupling type="rbe3" selectionsurface="Load" '
          'selectionnode="Master" />')
    m.add('<force selection="Master"><x>0 N</x><y>-100 N</y><z>0 N</z>'
          '</force>')
    n1, n2 = sorted(a["nodes"]["u1"])[:2]
    m.add('<constraintequation><term coefficient="1 1/m" nid="%d" '
          'dof="ux" /><term coefficient="-1 1/m" nid="%d" dof="ux" />'
          '</constraintequation>' % (n1, n2))
    man, md, comm, mesh, log = _translate(m)
    check(man is not None, "tie: manifest\n" + log[-2000:])
    if man is None:
        return
    tie = sorted(a["nodes"]["v1"] | b["nodes"]["v0"])
    rbe3 = sorted(b["nodes"]["v1"] | set([master]))
    want = {"bonded": {"nodes": tie, "origin": "user", "groups": [tie]},
            "coupling": {"nodes": rbe3, "origin": "user", "groups": [rbe3]},
            "constraint": {"nodes": sorted([n1, n2]), "origin": "user",
                           "groups": [sorted([n1, n2])]}}
    for kind in sorted(set(want) | set(man["not_shared"])):
        check(man["not_shared"].get(kind) == want.get(kind),
              "tie: not_shared {0}: {1}".format(
                  kind, man["not_shared"].get(kind)))
    check(man["components"] == {"A": {"model": "3D", "has_warping": False},
                                "B": {"model": "3D", "has_warping": False}},
          "tie: solid components {0}".format(man["components"]))
    check(man["beam_axes"] == {} and man["excentrement"] == {},
          "tie: no beams, no offsets")


def main():
    test_fingerprint()
    test_run_name_split()
    test_bases_to_remove()
    test_deformation_by_component()
    for fn in (test_prune, test_finish_export, test_orphan_age):
        tmp = tempfile.mkdtemp()
        try:
            fn(tmp)
        finally:
            shutil.rmtree(tmp)
    test_not_shared()
    test_note_mesh_failure()
    test_linear_contact()
    for fn in (test_frame, test_setting_off_untouched, test_line3_beam,
               test_trusses, test_sections, test_cable, test_pretension,
               test_shells, test_offsets, test_tie_rbe3):
        fn()
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
