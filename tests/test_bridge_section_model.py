# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 2.7 and 3, also IronPython via TestFiles/Tools/
# run_ipy.ps1) of bridge_section_model: temporary shells in the open model.
# The fake mw follows what was measured on Mecway 35.0.9802, so that an order
# that would hurt in Mecway hurts here: ids are always 1..n and shift after a
# delete, delete_nodes takes the elements along, delete_material of a material
# in use silently unassigns it, material_type raises on a missing material, a
# duplicate name gets (2).
#
#   python tests/test_bridge_section_model.py
#   powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1
#       -Script tests/test_bridge_section_model.py

from __future__ import print_function

import copy
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
TMP = tempfile.mkdtemp(prefix="section_model_")
bridge_utils.CONFIG_BRIDGE["work_dir"] = TMP      # in memory only
bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
import bridge_section_model as sm  # noqa: E402
import bridge_section_view as sv  # noqa: E402

LOG = []
sm.log = LOG.append
sv.log = LOG.append
NAME = "Doorsnede_tijdelijk"


def check(name, cond):
    print(("OK   " if cond else "FOUT ") + name)
    check.count += 1
    if not cond:
        check.failed = True


check.count = 0
check.failed = False


N_MODEL_NODES = 5
N_MODEL_ELEMS = 4


class Vector(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class Stop(Exception):
    pass


class FakeMw(object):
    """The mesh and material part of the API. fail: {method: n}, the n-th
    call of that method raises Stop."""

    def __init__(self):
        self.node_xyz = {}
        self.elems = {}             # eid: (shape, nodes, component)
        self.comps = {}             # name: material or None
        self.mats = {}              # name: {"types": {}, "props": {}}
        self.fail = {}
        self.counts = {}
        self.calls = []

    def _call(self, name):
        self.calls.append(name)
        self.counts[name] = self.counts.get(name, 0) + 1
        if self.fail.get(name) == self.counts[name]:
            raise Stop("failure in {0}".format(name))

    def state(self):
        return (self.node_xyz, self.elems, self.comps, self.mats)

    def snapshot(self):
        return copy.deepcopy(self.state())

    def reopened(self):
        """mw.open: the same model in a new object, no memory of anything."""
        other = FakeMw()
        other.node_xyz, other.elems, other.comps, other.mats = self.snapshot()
        return other

    def add_beam_model(self):
        """More nodes than the model of beam_view, so that the ids Mecway
        gives differ from the ids of the view."""
        for i in range(1, N_MODEL_NODES + 1):
            self.node_xyz[i] = (float(i), 0.0, 0.0)
        self.comps["Beam"] = "Sect"
        self.mats["Sect"] = {"types": {"geometric": "UniformGeneralSection"},
                             "props": {"area": 1e-3}}
        for i in range(1, N_MODEL_ELEMS + 1):
            self.elems[i] = ("line2", (i, i + 1), "Beam")

    def _compact(self):
        """Ids back to 1..n, in order, as Mecway does after a delete."""
        new = dict((old, i + 1) for i, old in enumerate(sorted(self.node_xyz)))
        self.node_xyz = dict((new[n], p) for n, p in self.node_xyz.items())
        self.elems = dict(
            (i + 1, (self.elems[e][0],
                     tuple(new[n] for n in self.elems[e][1]),
                     self.elems[e][2]))
            for i, e in enumerate(sorted(self.elems)))

    # Nodes and elements
    def all_nodes(self):
        return sorted(self.node_xyz)

    def all_elements(self):
        return sorted(self.elems)

    def nodes(self, eid):
        return list(self.elems[eid][1])

    def new_node(self, v):
        self._call("new_node")
        nid = len(self.node_xyz) + 1
        self.node_xyz[nid] = (v.x, v.y, v.z)
        return nid

    def new_element(self, shape, nodes, component):
        self._call("new_element")
        if component not in self.comps:
            raise Stop("no component")
        for n in nodes:
            if n not in self.node_xyz:
                raise Stop("no node {0}".format(n))
        eid = len(self.elems) + 1
        self.elems[eid] = (shape, tuple(nodes), component)
        return eid

    def delete_elements(self, eids):
        self._call("delete_elements")
        for e in eids:
            del self.elems[e]
        self._compact()

    def delete_nodes(self, nids):
        self._call("delete_nodes")
        for n in nids:
            del self.node_xyz[n]
        for e in list(self.elems):
            if set(self.elems[e][1]) & set(nids):
                del self.elems[e]
        self._compact()

    # Components
    def components(self):
        return list(self.comps)

    def new_component(self, name):
        self._call("new_component")
        out, k = name, 1
        while out in self.comps:
            k += 1
            out = "{0}({1})".format(name, k)
        self.comps[out] = None
        return out

    def component_elements(self, name):
        return [e for e in sorted(self.elems) if self.elems[e][2] == name]

    def delete_component(self, name):
        self._call("delete_component")
        if self.component_elements(name):
            raise Stop("component with elements")
        self.comps.pop(name, None)

    def material(self, component):
        if component not in self.comps:
            raise Exception("no such component")
        return self.comps[component]

    def set_material(self, component, material):
        self._call("set_material")
        self._mat(material)
        self.comps[component] = material

    # Materials
    def _mat(self, name):
        if name not in self.mats:
            raise Exception('Material "{0}" does not exist.'.format(name))
        return self.mats[name]

    def new_material(self, name):
        self._call("new_material")
        out, k = name, 1
        while out in self.mats:
            k += 1
            out = "{0}({1})".format(name, k)
        self.mats[out] = {"types": {}, "props": {}}
        return out

    def material_type(self, name, group):
        return self._mat(name)["types"].get(group, "None")

    def set_material_type(self, name, group, value):
        self._call("set_material_type")
        self._mat(name)["types"][group] = value

    def material_property(self, name, prop):
        props = self._mat(name)["props"]
        if prop not in props:
            raise Exception("not compatible")
        return props[prop]

    def set_material_property(self, name, prop, value):
        self._call("set_material_property")
        self._mat(name)["props"][prop] = value

    def delete_material(self, name):
        self._call("delete_material")
        self._mat(name)
        del self.mats[name]
        for comp in self.comps:
            if self.comps[comp] == name:
                self.comps[comp] = None     # silently, as Mecway

    # View
    def set_model_active(self):
        self._call("set_model_active")

    def display(self):
        self._call("display")


def soft_material():
    return {"types": {"geometric": "Plate", "mechanical": "Isotropic"},
            "props": {"thickness": 1e-4, "youngsmodulus": 1e3,
                      "poissonratio": 0.3}}


def model():
    mw = FakeMw()
    mw.add_beam_model()
    return mw


def beam_view():
    """A real view: two beams on one axis, a rectangle with a square hole
    and a diamond, so that side quads, cap quads and cap triangles occur."""
    data = {
        "mesh_nodes": {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0),
                       3: (2.0, 0.0, 0.0)},
        "mesh_elements": [(1, "line2", (1, 2), "A"),
                          (2, "line2", (2, 3), "B")],
        "elset_modelisations": {"A": "POU_D_E", "B": "POU_D_E"},
        "elsets": {"A": "M1", "B": "M2"}}
    shapes = {
        "M1": {"loops": [[(-0.02, -0.01), (0.02, -0.01), (0.02, 0.01),
                          (-0.02, 0.01)],
                         [(-0.01, -0.005), (0.01, -0.005), (0.01, 0.005),
                          (-0.01, 0.005)]], "area": 6e-4},
        "M2": {"loops": [[(0.0, -0.01), (0.01, 0.0), (0.0, 0.01),
                          (-0.01, 0.0)]], "area": 2e-4}}
    return sv.build_view(data, shapes)


VIEW = beam_view()
check("view: quads and triangles, from the real build_view",
      VIEW["quads"] > 0 and VIEW["tris"] > 0)
N_NODES = len(VIEW["nids"])
N_ELEMS = len(VIEW["elements"])


def raises(fn, kind=Stop):
    try:
        fn()
    except kind as e:
        return e
    return None


# ------------------------------------------
# Show, then remove
# ------------------------------------------
mw = model()
before = mw.snapshot()
check("shown: not on a clean model", not sm.shown(mw))
info = sm.show_shape(mw, VIEW, Vector)
check("show: counts", info["nodes"] == N_NODES and
      info["elements"] == N_ELEMS and
      len(mw.node_xyz) == N_MODEL_NODES + N_NODES and
      len(mw.elems) == N_MODEL_ELEMS + N_ELEMS)
check("show: component and material", info["component"] == NAME and
      info["material"] == NAME and mw.comps[NAME] == NAME)
check("show: all elements in the component",
      len(mw.component_elements(NAME)) == N_ELEMS)
check("show: soft Plate, no density",
      mw.mats[NAME]["types"] == {"geometric": "Plate",
                                 "mechanical": "Isotropic"} and
      mw.mats[NAME]["props"] == soft_material()["props"])
check("show: material assigned before the first element",
      mw.calls.index("set_material") < mw.calls.index("new_node"))
check("show: model view active, display last",
      mw.calls[-2:] == ["set_model_active", "display"])
xyz = dict(zip(VIEW["nids"], VIEW["xyz"]))
real = sorted(n for n in mw.node_xyz if n > N_MODEL_NODES)
check("show: the nodes lie where the view says",
      set(xyz.values()) == set(mw.node_xyz[n] for n in real))
ok = True
for (eid, shape, nodes), new in zip(VIEW["elements"],
                                    mw.component_elements(NAME)):
    ok = ok and mw.elems[new][0] == shape and [
        xyz[n] for n in nodes] == [mw.node_xyz[n] for n in mw.elems[new][1]]
check("show: ids of Mecway mapped, every element on the right points", ok)
check("show: Mecway ids differ from the ids of the view",
      real[0] != VIEW["nids"][0])
check("shown: after show", sm.shown(mw))
check("remove: True", sm.remove_shape(mw) is True)
check("remove: model equal to before", mw.snapshot() == before)
check("shown: not after remove", not sm.shown(mw))
n = mw.calls.index("delete_elements")
check("remove: order elements, nodes, component, material",
      [c for c in mw.calls[n:] if c.startswith("delete_")] ==
      ["delete_elements", "delete_nodes", "delete_component",
       "delete_material"])
check("remove: display after the deletes", mw.calls[-1] == "display")

# ------------------------------------------
# Shared nodes
# ------------------------------------------
mw = model()
before = mw.snapshot()
sm.show_shape(mw, VIEW, Vector)
shell_node = mw.nodes(mw.component_elements(NAME)[0])[0]
shell_xyz = mw.node_xyz[shell_node]
mw.comps["User"] = "Sect"
user_end = mw.new_node(Vector(9.0, 9.0, 9.0))
mw.new_element("line2", [3, shell_node], "User")
mw.new_element("line2", [user_end, shell_node], "User")
check("remove with a shared node: True", sm.remove_shape(mw) is True)
stay = mw.component_elements("User")
check("remove: both user elements on a shell node stay, ids renumbered",
      len(stay) == 2 and mw.node_xyz[mw.nodes(stay[0])[1]] == shell_xyz and
      mw.nodes(stay[1])[1] == mw.nodes(stay[0])[1])
check("remove: a user node after ours keeps its element, on the right point",
      mw.node_xyz[mw.nodes(stay[1])[0]] == (9.0, 9.0, 9.0))
check("remove: the other shell nodes and elements are gone",
      len(mw.node_xyz) == N_MODEL_NODES + 2 and
      len(mw.elems) == N_MODEL_ELEMS + 2 and NAME not in mw.comps)
check("remove: the beams keep their ids",
      all(mw.nodes(i + 1) == [i + 1, i + 2] for i in range(N_MODEL_ELEMS)))
mw.delete_elements(stay)
mw.delete_nodes([n for n in mw.all_nodes() if n > N_MODEL_NODES])
del mw.comps["User"]
check("remove: model equal to before the shared node", mw.snapshot() == before)

# ------------------------------------------
# Idempotent
# ------------------------------------------
mw = model()
before = mw.snapshot()
check("remove with nothing there: True", sm.remove_shape(mw) is True)
check("remove with nothing there: no delete and no redraw",
      not [c for c in mw.calls if c.startswith("delete_") or c == "display"])
sm.show_shape(mw, VIEW, Vector)
check("remove twice", sm.remove_shape(mw) and sm.remove_shape(mw) and
      mw.snapshot() == before)
sm.show_shape(mw, VIEW, Vector)
info = sm.show_shape(mw, VIEW, Vector)
check("show twice replaces, no stacking",
      info["component"] == NAME and
      len(mw.elems) == N_MODEL_ELEMS + N_ELEMS and
      len(mw.comps) == 2 and len(mw.mats) == 2)
check("remove after show twice", sm.remove_shape(mw) and
      mw.snapshot() == before)
mw = FakeMw()
check("remove on an empty model", sm.remove_shape(mw) is True and
      mw.snapshot() == FakeMw().snapshot())

# ------------------------------------------
# Failure halfway: everything goes back
# ------------------------------------------
points = [("new_material", 1), ("set_material_type", 1),
          ("set_material_property", 2), ("new_component", 1),
          ("set_material", 1), ("new_node", 1), ("new_node", 5),
          ("new_element", 1), ("new_element", 7),
          ("new_element", N_ELEMS)]
for method, nth in points:
    mw = model()
    before = mw.snapshot()
    mw.fail = {method: nth}
    del LOG[:]
    e = raises(lambda: sm.show_shape(mw, VIEW, Vector))
    label = "{0} #{1}".format(method, nth)
    check("failure at {0}: raises the failure itself".format(label),
          e is not None and "failure in {0}".format(method) in str(e))
    check("failure at {0}: model equal to before".format(label),
          mw.snapshot() == before)
    check("failure at {0}: one ERROR in the log".format(label),
          len([ln for ln in LOG if ln.startswith("ERROR:")]) == 1)
    check("failure at {0}: not shown".format(label), not sm.shown(mw))

mw = model()
mw.mats[NAME] = {"types": {"geometric": "Plate"}, "props": {"thickness": 5e-3}}
mw.comps["Plate1"] = NAME
before = mw.snapshot()
mw.fail = {"new_element": 3}
raises(lambda: sm.show_shape(mw, VIEW, Vector))
check("failure with a user material of that name: that one untouched",
      mw.snapshot() == before)

mw = model()
mw.fail = {"new_element": 3, "delete_elements": 1}
del LOG[:]
e = raises(lambda: sm.show_shape(mw, VIEW, Vector))
check("failing rollback: the original failure is raised",
      e is not None and "new_element" in str(e))
check("failing rollback: says so in the log",
      len([ln for ln in LOG if "rollback failed" in ln]) == 1)
check("failing rollback: a later remove cleans up what has a component",
      sm.shown(mw) and sm.remove_shape(mw) and not sm.shown(mw) and
      NAME not in mw.mats)

# ------------------------------------------
# remove_shape never raises
# ------------------------------------------
mw = model()
sm.show_shape(mw, VIEW, Vector)
mw.fail = {"delete_nodes": 1}
del LOG[:]
check("remove failing: False, no exception", sm.remove_shape(mw) is False)
check("remove failing: ERROR in the log",
      len([ln for ln in LOG if ln.startswith("ERROR:")]) == 1)
check("remove failing: still shown", sm.shown(mw))
mw.fail = {}
mw.counts = {}
check("remove failing: a second remove finishes the job",
      sm.remove_shape(mw) is True and not sm.shown(mw))

mw = model()
sm.show_shape(mw, VIEW, Vector)
mw.fail = {"delete_nodes": 1}
mw.counts = {}
e = raises(lambda: sm.show_shape(mw, VIEW, Vector), RuntimeError)
check("show over a shape that cannot be removed: refuses", e is not None)
check("show over a shape that cannot be removed: nothing stacked",
      "Doorsnede_tijdelijk(2)" not in mw.comps)

# ------------------------------------------
# Display is not fatal
# ------------------------------------------
mw = model()
mw.fail = {"display": 1}
del LOG[:]
info = sm.show_shape(mw, VIEW, Vector)
check("display failing on show: shape stays, WARNING",
      info is not None and sm.shown(mw) and
      len([ln for ln in LOG if ln.startswith("WARNING:")]) == 1)
mw.fail = {"display": 2}
del LOG[:]
check("display failing on remove: True, WARNING",
      sm.remove_shape(mw) is True and not sm.shown(mw) and
      len([ln for ln in LOG if ln.startswith("WARNING:")]) == 1)
mw = model()
mw.fail = {"set_model_active": 1}
del LOG[:]
info = sm.show_shape(mw, VIEW, Vector)
check("set_model_active failing: shape stays, still a redraw",
      info is not None and "display" in mw.calls and
      len([ln for ln in LOG if ln.startswith("WARNING:")]) == 1)

# ------------------------------------------
# No view
# ------------------------------------------
mw = model()
before = mw.snapshot()
check("show without a view: None, nothing added",
      sm.show_shape(mw, None, Vector) is None and mw.snapshot() == before)
check("show with an empty view: None",
      sm.show_shape(mw, {"parts": []}, Vector) is None and
      mw.snapshot() == before)
sm.show_shape(mw, VIEW, Vector)
check("show without a view removes the old shape",
      sm.show_shape(mw, None, Vector) is None and mw.snapshot() == before)

# ------------------------------------------
# Leftover from a crash
# ------------------------------------------
mw = model()
before = mw.snapshot()
sm.show_shape(mw, VIEW, Vector)
left = mw.reopened()
check("leftover: shown after a rebuild, without any memory", sm.shown(left))
check("leftover: removed", sm.remove_shape(left) is True and
      left.snapshot() == before)
check("shown: False after a rebuild of a clean model",
      not sm.shown(model().reopened()))
info = sm.show_shape(mw.reopened(), VIEW, Vector)
check("leftover: a show on a rebuilt model starts clean",
      info["component"] == NAME and info["material"] == NAME)

mw = model()
before = mw.snapshot()
mw.mats[NAME] = soft_material()
check("leftover: a material without a component is not shown",
      not sm.shown(mw))
check("leftover: such a material is removed",
      sm.remove_shape(mw) and mw.snapshot() == before)

mw = model()
before = mw.snapshot()
mw.new_component(NAME)
check("leftover: an empty component without material counts", sm.shown(mw))
check("leftover: such a component is removed",
      sm.remove_shape(mw) and mw.snapshot() == before)

mw = model()
before = mw.snapshot()
sm.show_shape(mw, VIEW, Vector)
mw.mats[NAME + "(2)"] = mw.mats.pop(NAME)
mw.mats[NAME] = soft_material()
del mw.comps[NAME]
mw.comps[NAME + "(2)"] = NAME + "(2)"
for e in list(mw.elems):
    if mw.elems[e][2] == NAME:
        mw.elems[e] = (mw.elems[e][0], mw.elems[e][1], NAME + "(2)")
check("leftover under a suffixed name, and an unused one before it",
      sm.shown(mw) and sm.remove_shape(mw) and mw.snapshot() == before)

# ------------------------------------------
# A user material of the same name
# ------------------------------------------
mw = model()
mw.mats[NAME] = {"types": {"geometric": "Plate", "mechanical": "Isotropic"},
                 "props": {"thickness": 5e-3, "youngsmodulus": 2e11,
                           "poissonratio": 0.3}}
before = mw.snapshot()
info = sm.show_shape(mw, VIEW, Vector)
check("user material: another name is taken", info["material"] != NAME and
      info["material"] == NAME + "(2)" and mw.comps[NAME] == NAME + "(2)")
check("user material: not changed while shown",
      mw.mats[NAME] == before[3][NAME])
check("user material: stays after remove, model equal to before",
      sm.remove_shape(mw) and mw.snapshot() == before)
check("user material, not assigned, alone in the model: left alone",
      sm.remove_shape(mw) and mw.snapshot() == before)

mw = model()
mw.mats[NAME] = soft_material()
mw.comps["Plate1"] = NAME
before = mw.snapshot()
info = sm.show_shape(mw, VIEW, Vector)
check("same values, in use by a user component: not taken over",
      info["material"] == NAME + "(2)")
check("same values, in use: still assigned after remove",
      sm.remove_shape(mw) and mw.snapshot() == before and
      mw.comps["Plate1"] == NAME)
check("same values, in use: nothing to do", sm.remove_shape(mw) and
      mw.snapshot() == before)

mw = model()
mw.mats[NAME] = soft_material()
mw.mats[NAME]["types"]["density"] = "Isotropic"
before = mw.snapshot()
check("user material differs only in density: left alone",
      sm.remove_shape(mw) and mw.snapshot() == before)
mw = model()
mw.mats[NAME] = soft_material()
mw.mats[NAME]["props"]["youngsmodulus"] = 1001.0
before = mw.snapshot()
check("user material differs only in Young's modulus: left alone",
      sm.remove_shape(mw) and mw.snapshot() == before)

# ------------------------------------------
# User components
# ------------------------------------------
for name in (NAME + "_oud", NAME + "2", "x" + NAME, NAME.lower(),
             NAME + "(a)", "Doorsnede"):
    mw = model()
    mw.comps[name] = "Sect"
    mw.new_element("line2", [1, mw.new_node(Vector(0.0, 1.0, 0.0))], name)
    before = mw.snapshot()
    check("similar component '{0}': not shown".format(name), not sm.shown(mw))
    sm.show_shape(mw, VIEW, Vector)
    check("similar component '{0}': stays".format(name),
          sm.remove_shape(mw) and mw.snapshot() == before)

for name in (NAME + "_oud", NAME.lower(), NAME + "(a)"):
    for material in (None, "Soft"):
        mw = model()
        mw.mats["Soft"] = soft_material()
        mw.comps[name] = material
        mw.new_element("line2", [1, mw.new_node(Vector(0.0, 1.0, 0.0))], name)
        before = mw.snapshot()
        label = "similar component '{0}', material {1}".format(name, material)
        check(label + ": stays", not sm.shown(mw) and sm.remove_shape(mw) and
              mw.snapshot() == before)

mw = model()
mw.mats["Zacht"] = soft_material()
sm.show_shape(mw, VIEW, Vector)
mw.mats["Other"] = soft_material()
mw.set_material(NAME, "Other")
before = mw.snapshot()
check("our component on a soft material of another name: no longer ours",
      not sm.shown(mw) and sm.remove_shape(mw) and "Zacht" in mw.mats and
      "Other" in mw.mats and len(mw.elems) == N_MODEL_ELEMS + N_ELEMS)

mw = model()
mw.comps[NAME] = "Sect"
mw.new_element("line2", [1, mw.new_node(Vector(0.0, 1.0, 0.0))], NAME)
before = mw.snapshot()
check("same name with a user material: not shown", not sm.shown(mw))
info = sm.show_shape(mw, VIEW, Vector)
check("same name with a user material: Mecway suffixes ours",
      info["component"] == NAME + "(2)")
check("same name with a user material: ours is removed, theirs stays",
      sm.remove_shape(mw) and mw.snapshot() == before)

shutil.rmtree(TMP, ignore_errors=True)

print("{0} checks".format(check.count))
if check.failed:
    print("FOUT: test_bridge_section_model")
    sys.exit(1)
print("Alle controles OK")
