# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_section_stress.py
#
# Responsibility: the stress of general and I, T, L, C beam sections from the
# section forces. Runs INSIDE the Code-Aster job (CPython with numpy and scipy,
# called by aster_results_export._section_stress_vars), NOT in IronPython.
# The numbers come from section_stress.py, section_fem.py, section_mesh.py and
# section_profiles.py: unchanged copies of MecwayAdvancedBeamAnalysis (same
# owner, MPL-2.0; tests/test_bridge_section_stress.py compares them with their
# source when that is present). Never edit those four here.
#
# WHAT IT MAKES
#   1. Element-node variables per beam end, largest value over the section
#      outside the corner zones:
#        beamvonmisesmax   sqrt(sigma^2 + 3 tau^2)
#        beamsixxabsmax    |sigma|
#        beamtaumax        |tau|, sum of shear force and torsion
#      Each is its own maximum, so the three can lie at different points. On a
#      section of several parts there are no shear fields: only beamsixxabsmax.
#   2. <model>_<run_id>_section.json next to the _results.xml: the warnings of
#      this step, and per general section with an outline a table for the shells
#      of bridge_section_view: per point of the outline and of the caps the unit
#      shear stress of Vv, Vw and T_S. Shear is linear in those three, so that
#      bridge_results_liml (IronPython, no numpy) can sum it per step. The table
#      depends on the section only, not on the run: it holds what it was made for
#      (loops, nu, A, IY, IZ, EY, EZ) and the reader compares those.
#
# THEORY, AXES, SIGNS: header of section_stress.py. Forces as Mecway and
# Code-Aster report them: V, W, U of the element, measured there.
#   T_S = T + EY Vw - EZ Vv
#   EY, EZ: those of the section the solver got from #ASTER-SECTIE, measured on
#   POU_D_E, POU_D_T and POU_D_TG (MecwayAdvancedBeamAnalysis tests/
#   test_beam_aster.py, G J dDRX/dx against T_S, 1e-7). Without that line: the
#   shear centre of the mesh of the section. That is also the rule for I, T, L, C
#   on POU_D_TG, where the solver has the thin-walled EY, EZ of bridge_warping:
#   the job does not know elem_beam. MT stays the total torque about the beam
#   line, so that only the small difference of the two shear centres counts,
#   NOT verified.
#
# POINTS: the mesh nodes outside the corner zones, shear averaged per node
# (SectionField.nodal). One third of the element nodes, which is what makes a
# chain of thousands of beams cheap; tests/test_bridge_section_stress.py compares
# with SectionField.extremes on element nodes. In a shell point inside a corner
# zone the sharp corner would give a number that grows with the mesh, so that
# point takes the two points where the outline leaves the zone, and the reader
# keeps the larger of the two; sigma stays that of the point itself.
#
# NOT HERE: no warping stress, no plasticity. A material that is not isotropic
# linear elastic is skipped with a WARNING. Forces are read as they are,
# Code-Aster's end values: exact under FORCE_POUTRE, q h^2 / 12 off under own
# weight on POU_D_TG (LS-97g, LS-97h; KNOWN_BUGS 133).
#
# Every problem is a WARNING and the job goes on: a failure here costs these
# results, never the results of the run (aster_results_export guards the call
# and switches off Code-Aster's floating point traps, _without_fpe).
#
# Do not use f-strings: same style as the rest of the bridge.

import io
import json
import math
import os
import xml.etree.ElementTree as ET
from collections import OrderedDict

import numpy as np

from aster_results_export import tr

SECTION_SUFFIX = "_section.json"
RESULTS_SUFFIX = "_results.xml"
# The six forces, in this order everywhere in this module
FORCE_NAMES = ("tensileforce", "sheary", "shearz", "torsion", "bendingmomv",
               "bendingmomw")
VON_MISES = "beamvonmisesmax"
SIGMA = "beamsixxabsmax"
TAU = "beamtaumax"
GENERAL = "UniformGeneralSection"
PROFILES = ("I", "T", "L", "C")
FORMAT_VERSION = 1
# Beam ends per block. Small on purpose: measured on 10,000 ends x 7000 points,
# 0.43 s with 8 ends per block and 1.9 s with 256 (Code-Aster's numpy).
_CHUNK_ENDS = 8


def read_head(liml_path):
    """The model part of the .liml, reading stops at <solution>: {"elsets":
    [(material, [eid, ...])], "mats": [<mat> elements], "texts": custom text
    fields in file order}."""
    from bridge_custom import CUSTOM_TAGS
    head = {"elsets": [], "mats": [], "texts": []}
    depth = 0
    with open(liml_path, "rb") as f:
        for event, el in ET.iterparse(f, events=("start", "end")):
            if event == "start":
                depth += 1
                if depth == 2 and el.tag == "solution":
                    break
                continue
            depth -= 1
            if depth != 1:
                continue
            if el.tag == "mat":
                head["mats"].append(el)
                continue
            if el.tag == "elset":
                head["elsets"].append((el.get("material"),
                                       [int(e.get("eid"))
                                        for e in el.findall("elem")]))
            elif el.tag in CUSTOM_TAGS:
                head["texts"].append(el.text)
            el.clear()
    return head


def _with_silent_logs(work):
    """work(), with the logging of the bridge modules off. Those would write
    to bridge_log.txt of the job; the lines were logged before the run."""
    import bridge_custom
    import bridge_from_liml
    import bridge_section_view
    import bridge_utils
    modules = (bridge_custom, bridge_from_liml, bridge_section_view,
               bridge_utils)
    saved = [m.log for m in modules]
    for m in modules:
        m.log = lambda text: None
    try:
        return work()
    finally:
        for m, old in zip(modules, saved):
            m.log = old


def _material(mat, shapes, extras):
    """One material as {"name", "kind", "cara": {...}, "shape", "attrs", "nu",
    "elastic"}; kind None for a section that is no business of this module."""
    from bridge_from_liml import (_apply_section_extras,
                                  _parse_geometric_props)
    from bridge_utils import parse_and_convert
    name = mat.get("name", "")
    node = mat.find("geometric")
    kind = node.get("type", "") if node is not None else ""
    if kind != GENERAL and kind not in PROFILES:
        return {"name": name, "kind": None}
    geom = _parse_geometric_props(node)
    if name in extras:
        geom = _apply_section_extras(name, geom, extras[name])
    mech = mat.find("mechanical")
    elastic = (mech is not None and mech.get("type", "Isotropic") == "Isotropic"
               and mat.find("plastic") is None and
               (mech.find("plastic") is None))
    # Without poissonratio the bridge gives Code-Aster nu = 0, as Mecway does
    # (bridge_from_liml, material block)
    nu = parse_and_convert(
        mech.get("poissonratio", "0") if mech is not None else "0",
        "dimensionless")
    return {"name": name, "kind": kind,
            "cara": dict(zip(geom.get("cara", ()), geom.get("vale", ()))),
            "attrs": dict(node.attrib), "nu": nu, "elastic": elastic,
            "shape": shapes.get(name)}


def read_materials(head):
    """{material: _material}. Uses the readers of the bridge, so that these
    are the numbers of the run."""
    import bridge_custom
    from bridge_from_liml import _parse_geometric_props, _section_extras
    from bridge_section_view import current_shapes, parse_shapes

    def work():
        custom = bridge_custom.parse(head["texts"])
        extras = _section_extras(custom.get("sections", []))
        geoms = {}
        for mat in head["mats"]:
            node = mat.find("geometric")
            if node is not None and node.get("type") == GENERAL:
                geoms[mat.get("name", "")] = _parse_geometric_props(node)
        shapes = current_shapes(parse_shapes(custom.get("section_shapes", [])),
                                {"mat_geometrics": geoms})
        out = OrderedDict()
        for mat in head["mats"]:
            item = _material(mat, shapes, extras)
            out[item["name"]] = item
        return out
    return _with_silent_logs(work)


def _loops_of(item):
    """Loops in V, W about the centroid, or raises section_stress.SectionError
    (no_shape, ...)."""
    import section_profiles
    from section_stress import SectionError
    if item["kind"] == GENERAL:
        if not item["shape"]:
            raise SectionError("no_shape", item["name"])
        return item["shape"]["loops"]
    return section_profiles.loops_for(item["attrs"])["loops"]


def section_key(loops, item):
    """Hashable: one SectionField per shape, nu and solver properties."""
    cara = item["cara"]
    return (tuple(tuple(tuple(p) for p in loop) for loop in loops), item["nu"],
            cara.get("A"), cara.get("IY"), cara.get("IZ"), cara.get("EY"),
            cara.get("EZ"))


class Section(object):
    """A SectionField prepared for many beam ends: nodal unit fields, the
    points outside the corner zones and their coefficients. Built once per
    section_key (SectionField is the expensive part)."""

    def __init__(self, loops, item):
        import section_stress
        cara = item["cara"]
        offset = None
        if cara.get("EY") is not None or cara.get("EZ") is not None:
            offset = (cara.get("EY", 0.0), cara.get("EZ", 0.0))
        self.loops = [[tuple(p) for p in loop] for loop in loops]
        self.item = item
        self.field = section_stress.SectionField(
            loops, nu=item["nu"], offset=offset,
            props={"A": cara["A"], "ivv": cara["IY"], "iww": cara["IZ"],
                   "ivw": 0.0})
        field = self.field
        self.has_shear = field.fields is not None
        keep = np.ones(len(field.xy), dtype=bool)
        for p, t in field.corners:
            keep &= (np.hypot(field.xy[:, 0] - p[0], field.xy[:, 1] - p[1]) >
                     section_stress.CORNER_ZONE_FACTOR * t)
        self.outside = keep
        use = keep if keep.any() else np.ones(len(keep), dtype=bool)
        v, w = field.xy[use, 0], field.xy[use, 1]
        p = field.props
        d = p["ivv"] * p["iww"] - p["ivw"] ** 2
        # sigma = S [N, Mv, Mw]
        self.sig = np.vstack([np.full(len(v), 1.0 / p["A"]),
                              (p["iww"] * w - p["ivw"] * v) / d,
                              (p["ivw"] * w - p["ivv"] * v) / d])
        self.unit = None
        if self.has_shear:
            # (6, nodes): Vv on v, w; Vw on v, w; T_S on v, w
            self.unit = np.array([
                field.nodal(field.fields[key][:, :, axis])
                for key in ("vv", "vw", "t") for axis in (0, 1)])
            self.tau_v = self.unit[0::2][:, use]
            self.tau_w = self.unit[1::2][:, use]

    def shear_forces(self, forces):
        """(ends, 3): Vv, Vw, T_S; forces (ends, 6) as FORCE_NAMES."""
        ey, ez = self.field.offset
        out = np.empty((len(forces), 3))
        out[:, 0] = forces[:, 1]
        out[:, 1] = forces[:, 2]
        out[:, 2] = forces[:, 3] + ey * forces[:, 2] - ez * forces[:, 1]
        return out

    def maxima(self, forces):
        """(von Mises, |sigma|, |tau|), each an array per beam end; forces
        (ends, 6). Without shear fields the first and last are None."""
        n = len(forces)
        vm, sig, tau = np.empty(n), np.empty(n), np.empty(n)
        for first in range(0, n, _CHUNK_ENDS):
            part = forces[first:first + _CHUNK_ENDS]
            last = first + len(part)
            s = part[:, (0, 4, 5)].dot(self.sig)
            sig[first:last] = np.abs(s).max(axis=1)
            if not self.has_shear:
                continue
            shear = self.shear_forces(part)
            tv = shear.dot(self.tau_v)
            tw = shear.dot(self.tau_w)
            t2 = tv * tv + tw * tw
            tau[first:last] = np.sqrt(t2.max(axis=1))
            vm[first:last] = np.sqrt((s * s + 3.0 * t2).max(axis=1))
        if not self.has_shear:
            return None, sig, None
        return vm, sig, tau

    def table(self):
        """Rows for the sidecar: [v, w, six unit values] or, inside a corner
        zone, [v, w, six values, six values] of the two exits of the zone."""
        from bridge_section_view import cap_pieces
        field = self.field
        points = [p for loop in self.loops for p in loop]
        points += [tuple(q) for piece in cap_pieces(self.loops) for q in piece]
        wanted = OrderedDict((p, True) for p in points)
        walk = _Boundary(field.elements)
        ids = walk.nodes
        rows = []
        for v, w in wanted:
            near = ids[int(np.argmin(np.hypot(field.nodes[ids, 0] - v,
                                              field.nodes[ids, 1] - w)))]
            row = [float(v), float(w)]
            for node in walk.exits(int(near), self.outside):
                row.extend(float(x) for x in self.unit[:, node])
            rows.append(row)
        return rows


class _Boundary(object):
    """The outline of a tri6 mesh as a graph of its nodes."""

    def __init__(self, elements):
        seen = {}
        for e in elements:
            for a, b, mid in ((e[0], e[1], e[3]), (e[1], e[2], e[4]),
                              (e[2], e[0], e[5])):
                key = (min(a, b), max(a, b))
                seen[key] = None if key in seen else (int(a), int(b), int(mid))
        self.next = {}
        for edge in seen.values():
            if edge is None:
                continue
            a, b, mid = edge
            self.next.setdefault(a, []).append(mid)
            self.next.setdefault(b, []).append(mid)
            self.next.setdefault(mid, []).extend([a, b])
        self.nodes = np.array(sorted(self.next))

    def exits(self, start, outside):
        """[start] when outside the zones, otherwise the first nodes outside
        them when walking both ways along the outline; [start] without one."""
        if outside[start]:
            return [start]
        found = []
        for first in self.next[start]:
            prev, node = start, first
            for _ in range(len(self.next)):
                if outside[node]:
                    if node not in found:
                        found.append(node)
                    break
                others = [n for n in self.next[node] if n != prev]
                if not others:
                    break
                prev, node = node, others[0]
        return found[:2] or [start]


class Plan(object):
    """The variables of a run: .variables [(name, ascending eids)]; .values
    turns the six forces of a step into their values."""

    def __init__(self, groups, variables, sizes):
        # [(Section, positions of its values per force, slots per variable)]
        self.groups = groups
        self.variables = variables
        self.sizes = sizes

    def values(self, arrays):
        """{variable: values of the step}. arrays: the six flat arrays of the
        element-node variables of FORCE_NAMES."""
        out = dict((name, np.zeros(size)) for name, size in self.sizes.items())
        for section, where, slots in self.groups:
            forces = np.column_stack([a[w] for a, w in zip(arrays, where)])
            vm, sig, tau = section.maxima(forces)
            for name, got in ((VON_MISES, vm), (SIGMA, sig), (TAU, tau)):
                if got is not None:
                    # the writer of the job must not get nan or inf
                    out[name][slots[name]] = np.where(np.isfinite(got), got,
                                                      0.0)
        return out


def _skip_text(item, code):
    name = item["name"]
    if code == "no_shape":
        return tr(u"WARNING: Materiaal '{0}': General section zonder bruikbare "
                  u"vorm (SECTIE-VORM uit MecwaySectionProps ontbreekt of hoort "
                  u"bij een andere doorsnede). Geen spanning over de doorsnede.",
                  u"WARNING: Material '{0}': general section without a usable "
                  u"shape (SECTIE-VORM of MecwaySectionProps is missing or "
                  u"belongs to another section). No stress over the "
                  u"section.").format(name)
    if code == "not_elastic":
        return tr(u"WARNING: Materiaal '{0}': niet isotroop lineair-elastisch; "
                  u"geen spanning over de doorsnede.",
                  u"WARNING: Material '{0}': not isotropic linear elastic; no "
                  u"stress over the section.").format(name)
    if code == "parts":
        return tr(u"WARNING: Materiaal '{0}': doorsnede uit meerdere delen; "
                  u"alleen de langsspanning, geen schuifspanning of von Mises.",
                  u"WARNING: Material '{0}': section of several parts; only "
                  u"the longitudinal stress, no shear stress or von "
                  u"Mises.").format(name)
    return tr(u"WARNING: Materiaal '{0}': doorsnede niet te berekenen ({1}); "
              u"geen spanning over de doorsnede.",
              u"WARNING: Material '{0}': section cannot be calculated ({1}); "
              u"no stress over the section.").format(name, code)


def no_forces_text():
    return tr(u"WARNING: Geen snedekrachten van de balken in het resultaat: "
              u"kies het resultaatveld beam_forces, anders geen spanning over "
              u"de doorsnede.",
              u"WARNING: No beam section forces in the result: choose the "
              u"result field beam_forces, otherwise no stress over the "
              u"section.")


def write_sidecar(out_path, warnings, tables):
    """<run>_section.json next to the fragment. Nothing when out_path is not a
    result file of a run."""
    if not out_path.endswith(RESULTS_SUFFIX):
        return None
    path = out_path[:-len(RESULTS_SUFFIX)] + SECTION_SUFFIX
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps({"version": FORMAT_VERSION, "warnings": warnings,
                            "sections": tables}))
    os.replace(tmp, path)
    return path


def _positions(ids, elements):
    """{eid: first position of its values} of a flat element-node array."""
    where, at = {}, 0
    for eid in ids:
        where[int(eid)] = at
        at += len(elements[int(eid)][1])
    return where


def _sections_of(head, materials, candidates, warnings):
    """({material: Section}, tables). Only materials of beams in candidates;
    identical sections share one Section."""
    from section_stress import SectionError
    used = set(material for material, eids in head["elsets"]
               if material in materials and candidates.intersection(eids))
    built, out, tables = {}, {}, []
    for name, item in materials.items():
        if name not in used or item["kind"] is None:
            continue
        if not item["elastic"]:
            warnings.append(_skip_text(item, "not_elastic"))
            continue
        try:
            loops = _loops_of(item)
            key = section_key(loops, item)
            if key not in built:
                built[key] = Section(loops, item)
        except SectionError as e:
            warnings.append(_skip_text(item, e.code))
            continue
        except Exception as e:      # one bad section must not cost the others
            warnings.append(_skip_text(item, str(e)))
            continue
        section = built[key]
        out[name] = section
        if not section.has_shear:
            warnings.append(_skip_text(item, "parts"))
        elif item["kind"] == GENERAL:
            cara = item["cara"]
            tables.append({"material": name, "loops": section.loops,
                           "nu": item["nu"], "A": cara["A"], "IY": cara["IY"],
                           "IZ": cara["IZ"],
                           "EY": float(section.field.offset[0]),
                           "EZ": float(section.field.offset[1]),
                           "points": section.table()})
    return out, tables


def _group(head, sections, elements, ids_of):
    """Plan out of {material: Section} and {force: ids of its variable}."""
    where = [_positions(ids_of[name], elements) for name in FORCE_NAMES]
    common = set(where[0])
    for one in where[1:]:
        common &= set(one)
    per_section = OrderedDict()
    for material, eids in head["elsets"]:
        section = sections.get(material)
        if section is not None:
            per_section.setdefault(id(section), (section, []))[1].extend(
                e for e in eids if e in common)
    names = (VON_MISES, SIGMA, TAU)
    chosen = dict((name, sorted(
        e for section, eids in per_section.values() for e in eids
        if name == SIGMA or section.has_shear)) for name in names)
    start = dict((name, _positions(chosen[name], elements)) for name in names)
    groups = []
    for section, eids in per_section.values():
        if not eids:
            continue
        eids = sorted(eids)
        spots = [[w[e] + k for e in eids
                  for k in range(len(elements[e][1]))] for w in where]
        slots = {}
        for name in names:
            if eids[0] in start[name]:
                slots[name] = np.array([start[name][e] + k for e in eids
                                        for k in range(len(elements[e][1]))])
        groups.append((section, [np.array(s) for s in spots], slots))
    variables = [(name, np.array(chosen[name], dtype="<i4")) for name in names
                 if chosen[name]]
    sizes = dict((name, sum(len(elements[e][1]) for e in eids))
                 for name, eids in chosen.items() if eids)
    return Plan(groups, variables, sizes)


def plan(liml_path, out_path, elements, ids_of):
    """
    What this run gets: (Plan or None, warnings). Writes the sidecar.

    liml_path, out_path: as export_results. elements: {eid: (shape, nodes)}
    of aster_results_export.read_liml_model. ids_of: {force: ids of its
    element-node variable}, for the forces of FORCE_NAMES that are in the
    result. Never raises for an ordinary reason: a WARNING instead.
    """
    head = read_head(liml_path)
    beams = set(e for e, v in elements.items() if v[0] in ("line2", "line3"))
    kinds = [m.find("geometric") for m in head["mats"]]
    if not any(k is not None and (k.get("type") == GENERAL or
                                  k.get("type") in PROFILES) for k in kinds):
        return None, []
    warnings = []
    if not all(name in ids_of for name in FORCE_NAMES):
        warnings.append(no_forces_text())
        write_sidecar(out_path, warnings, [])
        return None, warnings
    try:
        import section_stress  # noqa: F401
    except ImportError as e:    # also: a scipy that is missing
        warnings.append(tr(
            u"WARNING: numpy/scipy niet beschikbaar in Code-Aster ({0}); geen "
            u"spanning over de doorsnede.",
            u"WARNING: numpy/scipy not available in Code-Aster ({0}); no "
            u"stress over the section.").format(e))
        write_sidecar(out_path, warnings, [])
        return None, warnings
    materials = read_materials(head)
    candidates = beams.intersection(int(e) for e in ids_of[FORCE_NAMES[0]])
    sections, tables = _sections_of(head, materials, candidates, warnings)
    result = _group(head, sections, elements, ids_of) if sections else None
    write_sidecar(out_path, warnings, tables)
    return result, warnings
