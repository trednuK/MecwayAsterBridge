# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_section_model.py
#
# Responsibility: the swept shape of general-section beams in the open model,
# before a calculation. Mecway draws only a small rectangle for a general
# section, so the shells of bridge_section_view.build_view are added as
# temporary elements. The results route (shells in the model copy inside
# <solution>) does not use this module.
#
#   shown(mw)                       is the shape in the model?
#   show_shape(mw, view, Vector)    add it, all or nothing
#   remove_shape(mw)                remove it, idempotent
#
# Every answer comes from the model, never from remembered ids: mw.open
# rebuilds the model and a crash or a save can leave the shells in a file.
# So a leftover is removed in the same way as a shape shown a moment ago.
#
# WHAT IS OURS. There is no API to mark something or to list materials, so:
#   material : name in the series Doorsnede_tijdelijk, Doorsnede_tijdelijk(2),
#              ... (what new_material gives for a duplicate) and exactly the
#              soft Plate below.
#   component: a name in the same series, with one of those materials or none
#              (show_shape assigns it before the first element).
# A user material or component of the same name with other content, or a name
# that only looks like it, is left alone. A material any other component
# refers to is left alone as well: delete_material of a material in use does
# not fail, it silently takes it off that component (measured).
#
# ORDER. delete_nodes also deletes every element that uses the node, so first
# the elements, then only the nodes no remaining element uses, then the empty
# component, then the material. Mecway requires ids 1..n and renumbers after a
# delete, so that ids are only good until the next delete: each kind is
# deleted in one call, and the nodes in use are read after the elements went.
#
# THE MATERIAL. Without a material an internal solve is silently empty (0
# nodes), so it is required. No density, so that gravity and mass stay those
# of the beams.
#
# Measured on Mecway 35.0.9802, hidden scratch runs on a chain of 7 beams:
# - show, solve, remove: beam displacements, rotations, section forces and
#   stressptu equal to a solve without shells within 1e-10 of their largest
#   value; the unconnected closed shells solve without a message, displacement
#   0. Internal solver, Static 3D. Other analyses NOT verified.
# - show, remove, save_as: the file is byte for byte the file before.
# - show, save_as, mw.open, remove, save_as: no trace of the name left.
# - after show, solve, remove the <solution> of the file still holds the
#   shells until the next solve; the model part is clean.
# - material_type raises on a missing material and gives the string 'None'
#   for an unset group; material() gives None on a component without one and
#   raises on a missing component; delete_component of a missing component
#   does nothing; delete_material of a missing material raises; names are case
#   sensitive; set_material on a component without elements holds.
#
# Compatible with IronPython 2.7.9. mw and Vector exist only in the main
# script and are passed in.

import re

from bridge_utils import log, tr

PREFIX = "Doorsnede_tijdelijk"
_NAME_RE = re.compile("^" + re.escape(PREFIX) + r"(\(\d+\))?$")
# The soft Plate. Values in SI as the API wants them.
_SOFT_TYPES = (("geometric", "Plate"), ("mechanical", "Isotropic"),
               ("density", "None"))
_SOFT_VALUES = (("thickness", 1.0e-4), ("youngsmodulus", 1.0e3),
                ("poissonratio", 0.3))
_REL_TOL = 1.0e-9           # of a value above; it passes through a text file


# ==========================================
# WHAT IS OURS
# ==========================================
def _series_name(k):
    """PREFIX for k = 1, else the name Mecway gives the k-th duplicate."""
    return PREFIX if k == 1 else "{0}({1})".format(PREFIX, k)


def _material_exists(mw, name):
    """No API lists materials; material_type raises on a missing one. Any
    other failure also reads as missing, which is safe: new_material then
    still suffixes the name instead of taking over a material."""
    try:
        mw.material_type(name, "geometric")
    except Exception:
        return False
    return True


def _material_series(mw):
    """The existing names of the series, up to the first free one."""
    names = []
    while _material_exists(mw, _series_name(len(names) + 1)):
        names.append(_series_name(len(names) + 1))
    return names


def _is_our_material(mw, name):
    """True for a material of the series with exactly the soft Plate."""
    if not name or not _NAME_RE.match(name):
        return False
    try:
        for group, value in _SOFT_TYPES:
            if mw.material_type(name, group) != value:
                return False
        for prop, value in _SOFT_VALUES:
            actual = float(mw.material_property(name, prop))
            if abs(actual - value) > _REL_TOL * value:
                return False
    except Exception:
        # Missing, or a property that does not fit the type of the material.
        return False
    return True


def _our_components(mw):
    out = []
    for comp in mw.components():
        if _NAME_RE.match(comp):
            material = mw.material(comp)
            if material is None or _is_our_material(mw, material):
                out.append(comp)
    return out


def _our_materials(mw, comps):
    """Our materials no component outside comps refers to, also one that
    lost its component."""
    keep = set(mw.material(c) for c in mw.components() if c not in comps)
    names = set(_material_series(mw))
    names.update(mw.material(c) for c in comps)
    return sorted(n for n in names
                  if n not in keep and _is_our_material(mw, n))


def shown(mw):
    """True when the model holds a shape remove_shape would remove."""
    return bool(_our_components(mw))


# ==========================================
# REMOVE
# ==========================================
def _delete_added(mw, elements, nodes, components, materials):
    """Delete these elements, those of these nodes that are left without an
    element, these components when empty, then these materials."""
    alive = set(int(e) for e in mw.all_elements())
    gone = [e for e in elements if e in alive]
    if gone:
        mw.delete_elements(gone)
    used = set()
    for e in mw.all_elements():
        used.update(int(n) for n in mw.nodes(e))
    existing = set(int(n) for n in mw.all_nodes())
    free = sorted(n for n in set(nodes) if n in existing and n not in used)
    if free:
        mw.delete_nodes(free)
    present = list(mw.components())
    for comp in components:
        if comp in present and not list(mw.component_elements(comp)):
            mw.delete_component(comp)
    for material in materials:
        mw.delete_material(material)


def _refresh(mw):
    """Redraw; a failure here is no reason to undo anything."""
    try:
        mw.display()
    except Exception as e:
        log(tr(u"WARNING: Doorsnede: het scherm is niet ververst: {0}",
               u"WARNING: Section view: the display was not refreshed: {0}"
               ).format(e))


def remove_shape(mw):
    """
    Remove the shape, by what is in the model. Safe with nothing there, and
    never raises: this also runs in a finally. True when none of it is left,
    False (ERROR in the log) when that failed; a run must then not go on,
    or the shells enter the Code-Aster mesh.
    """
    try:
        comps = _our_components(mw)
        materials = _our_materials(mw, comps)
        if not comps and not materials:
            return True
        elements, nodes = [], set()
        for comp in comps:
            for e in mw.component_elements(comp):
                elements.append(int(e))
                nodes.update(int(n) for n in mw.nodes(e))
        _delete_added(mw, elements, nodes, comps, materials)
    except Exception as e:
        log(tr(u"ERROR: Doorsnede: de tijdelijke vorm is niet verwijderd: "
               u"{0}",
               u"ERROR: Section view: the temporary shape was not removed: "
               u"{0}").format(e))
        _refresh(mw)
        return False
    log("INFO: Section view: temporary shape removed ({0} elements).".format(
        len(elements)))
    _refresh(mw)
    return True


# ==========================================
# SHOW
# ==========================================
def _new_soft_material(mw, added):
    name = _series_name(len(_material_series(mw)) + 1)
    material = mw.new_material(name) or name
    added["materials"].append(material)
    for group, value in _SOFT_TYPES:
        if value != "None":
            mw.set_material_type(material, group, value)
    for prop, value in _SOFT_VALUES:
        mw.set_material_property(material, prop, value)
    return material


def _add_parts(mw, view, component, Vector, added):
    """Nodes and elements of view["parts"]; Mecway gives its own ids, so the
    ids of the view only tell which node is which."""
    for part in view["parts"]:
        ids = {}
        for nid, p in part["nodes"]:
            ids[nid] = int(mw.new_node(Vector(p[0], p[1], p[2])))
            added["nodes"].append(ids[nid])
        for _eid, shape, nodes in part["elements"]:
            added["elements"].append(int(mw.new_element(
                shape, [ids[n] for n in nodes], component)))


def _roll_back(mw, added):
    """Undo show_shape by what it added; never raises, so that the caller
    can raise the failure that brought it here."""
    try:
        _delete_added(mw, added["elements"], added["nodes"],
                      added["components"], added["materials"])
    except Exception as e:
        log(tr(u"ERROR: Doorsnede: terugdraaien mislukt: {0}. Bij de volgende "
               u"start wordt de vorm verwijderd; losse knopen blijven staan.",
               u"ERROR: Section view: rollback failed: {0}. The next start "
               u"removes the shape; loose nodes stay.").format(e))


def _activate_model(mw):
    try:
        mw.set_model_active()
    except Exception as e:
        log(tr(u"WARNING: Doorsnede: modelweergave niet actief gemaakt: {0}",
               u"WARNING: Section view: model view not made active: {0}"
               ).format(e))


def show_shape(mw, view, Vector):
    """
    Add view (bridge_section_view.build_view) to the model, in place of an
    earlier shape. Returns {"component", "material", "nodes", "elements"}, or
    None without a view (build_view has logged why). On a failure everything
    added is removed and the exception is raised.
    """
    if not remove_shape(mw):
        raise RuntimeError("the previous temporary shape is still there")
    if not view or not view.get("parts"):
        return None
    added = {"elements": [], "nodes": [], "components": [], "materials": []}
    try:
        material = _new_soft_material(mw, added)
        component = mw.new_component(PREFIX) or PREFIX
        added["components"].append(component)
        mw.set_material(component, material)
        _add_parts(mw, view, component, Vector, added)
    except Exception as e:
        log(tr(u"ERROR: Doorsnede: de tijdelijke vorm is niet gemaakt: {0}",
               u"ERROR: Section view: the temporary shape was not made: {0}"
               ).format(e))
        _roll_back(mw, added)
        raise
    _activate_model(mw)
    _refresh(mw)
    log("INFO: Section view: temporary shape shown ({0} nodes, {1} elements, "
        "component {2}, material {3}).".format(
            len(added["nodes"]), len(added["elements"]), component, material))
    return {"component": component, "material": material,
            "nodes": len(added["nodes"]), "elements": len(added["elements"])}
