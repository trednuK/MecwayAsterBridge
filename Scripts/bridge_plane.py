# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_plane.py
# Responsibility: Mecway's 2D analysis types (STAPPENPLAN S16a, S16b):
# Static 2D (S20, plane stress or plane strain), Static Axisymmetric (SA0),
# Dynamic Response 2D (D20) and Dynamic Response Axisymmetric (DA0) ->
# Code-Aster MODELISATION 'C_PLAN', 'D_PLAN' and 'AXIS' in MECA_STATIQUE
# (lin_static_3d) or DYNA_NON_LINE (dyna_impl_3d; with schema NEWMARK,
# deformation PETIT and one step per Mecway step equal to Mecway's linear
# Newmark: verification PL-10 .. PL-12, <= 4e-8).
# bridge_from_liml calls apply() (modelisations, checks), bridge_mesh calls
# convert_bc() per load and finish_bcs() after all loads, bridge_to_aster
# uses export_arg() / static_check_arg() for the results.
#
# Compatible with IronPython 2.7.9 (Mecway scripting engine).
#
# Mecway (measured headless with Mecway 34, mw_solve.py, 28 Oct 2026; manual
# v34 par. 6.1.1, 6.1.3, 7.1, 7.2):
#   - S20 = Static 2D, SA0 = Static Axisymmetric (the names in mecway.exe:
#     "Static 2D", "Static Axisymmetric"), D20 = Dynamic Response 2D, DA0 =
#     Dynamic Response Axisymmetric (Samples/PandSWaves.liml is D20; DA0
#     solved headless with time steps), A20 = Acoustic Resonance 2D (not
#     translated, NOT_TRANSLATED_2D). Plane elements tri3/tri6/quad4/
#     quad8 in the XY plane (Z ignored by Mecway), faceid 1..4 = the edges
#     (corner k to corner k+1), as for shells.
#   - S20: the material needs Mecway's "Shell/membrane" geometry
#     (<geometric type="Plate" thickness=".."/>); plane strain adds
#     planestrain="1" (seen after importing CPS4/CPE4 from a .inp). Without
#     a thickness Mecway's solve gives no solution. Forces, gravity and the
#     reaction forces are for the whole thickness t, also in plane strain
#     (pressure 1 MPa on a 20 mm edge, t = 10 mm: reaction 200 N; nodal
#     force 100 N: sigma = 100 / (20 mm x 10 mm)).
#   - SA0: Y is the axis of symmetry, X the radius (X >= 0). Forces, gravity
#     and reactions are for the full 360 degrees (force 1000 N on the top
#     edge of a ring r = 0.1..0.2 m: sigma_yy = 1000 / (pi (0.2^2 - 0.1^2))
#     uniform; gravity reaction = rho g V of the whole ring). A material
#     with a thickness gives no solution in Mecway's own SA0 solve.
#   - Results: displx, disply (+ displmag), reactionforcex/y (+ mag),
#     stressxx..stresszx (stressyz = stresszx = 0; stresszz = 0 in plane
#     stress, nu (sxx + syy) in plane strain, the hoop stress in SA0),
#     vonmises, principal1..3 and tresca from the 3D tensor; node and
#     element-node variables. No strain field in 2D (Mecway writes no
#     lstrain* in S20/SA0, also with the field "strain" requested).
#
# Code-Aster (U3.13.01 "Modélisations AXIS, D_PLAN, C_PLAN"; U4.44.01
# par. 3.5 and FORCE_NODALE; catalogue affe_char_meca.py v17.4):
#   - DX, DY per node; TRIA3/6, QUAD4/8 cells, SEG2/3 for edge loads;
#     loads FORCE_CONTOUR, FORCE_INTERNE, PESANTEUR (AXIS: only along Y),
#     PRES_REP, ROTATION.
#   - AXIS: forces are per radian ("brought back to a sector of 1 radian,
#     divide the real loading by 2 pi", U4.44.01 par. 3.5).
#   - C_PLAN / D_PLAN have no thickness: the model is per unit thickness.
#     Measured with Code-Aster 17.4 (C_PLAN, PRES_REP 1 MPa on a 20 mm
#     edge): sum REAC_NODA = 20000 N = 1 MPa x 0.02 m x 1 m.
#   - A mesh written with COOR_3D and all Z = 0 is read as 2D
#     (mesh.getDimension() = 2, no alarm; Code-Aster 17.4 run).
# So the bridge divides the concentrated forces (FORCE_NODALE) by the
# factor t (C_PLAN/D_PLAN) or 2 pi (AXIS) and multiplies the reactions by
# the same factor (aster_results_export, plane=...). Pressure, traction,
# edge forces (as force per area), gravity and centrifugal force need no
# factor: Code-Aster integrates them per unit thickness or per radian.

import math
from collections import OrderedDict

from bridge_utils import CONFIG_BRIDGE, log, tr

# Mecway analysis type -> kind of 2D analysis. D20/DA0 (Dynamic Response 2D /
# Axisymmetric, S16b): linear Newmark like D30, bridge analysis dyna_impl_3d.
PLANE_TYPES = {"S20": "plane", "SA0": "axis", "D20": "plane", "DA0": "axis"}
# 2D types that behave as Mecway's 3D type in the rest of the bridge (output
# times of D30, the Newmark warning)
EQUIVALENT_3D = {"S20": "S30", "SA0": "S30", "D20": "D30", "DA0": "D30"}
PLANE_MODELISATIONS = ("C_PLAN", "D_PLAN", "AXIS")
# Mecway 34's other 2D analysis type. V20 is not one: Mecway 34 converts
# it to V30 (the solution file says V30), unknown codes such as T20/B20/L20
# become S30.
NOT_TRANSLATED_2D = {"A20": "Acoustic Resonance 2D"}
PLANE_SHAPES = frozenset(["tri3", "tri6", "quad4", "quad8"])
# Solver command with a verified 2D route per Mecway type (S16a linear
# static, S16b implicit dynamics)
_VERIFIED_SOLVERS = {"S20": "MECA_STATIQUE", "SA0": "MECA_STATIQUE",
                     "D20": "DYNA_NON_LINE", "DA0": "DYNA_NON_LINE"}
_BRIDGE_ANALYSIS = {"MECA_STATIQUE": "lin_static_3d",
                    "DYNA_NON_LINE": "dyna_impl_3d"}
# Loads and constraints with a verified 2D route
_HANDLED = ("fixed", "pinnedsupport", "displacement", "force",
            "surfacepressure", "traction", "symmetry", "gravity",
            "centrifugal")
# model_data keys of model items without a verified 2D route
_NOT_VERIFIED = (("contacts", "Contact"), ("bonded", "Bonded contact"),
                 ("couplings", "Node-surface coupling"),
                 ("constraint_equations", "Constraint equation"),
                 ("point_masses", "Point mass"),
                 ("flexible_joints", "Flexible joint"),
                 ("thermal_stress", "Thermal stress"),
                 ("temperatures", "Temperature"),
                 ("node_temperatures", "Node temperature"),
                 ("initial_velocities", "Initial velocity"))
_DROP_DDL = ("DZ", "DRX", "DRY", "DRZ")
_DROP_FORCE = ("FZ", "MX", "MY", "MZ")
_SEG_GAUSS = [(-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
              (0.774596669241483, 5.0 / 9.0)]


def is_plane_type(mecway_type):
    """True for a Mecway 2D analysis type the bridge translates."""
    return mecway_type in PLANE_TYPES


def equivalent_3d(mecway_type):
    """Mecway's 3D analysis type with the same meaning outside the element
    formulation (S20/SA0 -> S30, D20/DA0 -> D30); other types unchanged."""
    return EQUIVALENT_3D.get(mecway_type, mecway_type)


def info(model_data):
    """The 2D settings of the run ({"type", "modelisation", "thickness",
    "factor"}) or None for a 3D analysis."""
    return model_data.get("plane") if model_data else None


def _fatal(text_nl, text_en, *args):
    log(tr("ERROR: " + text_nl, "ERROR: " + text_en).format(*args))
    return False


def apply(model_data, run_cfg, elset_shapes):
    """
    Modelisations of a 2D analysis (bridge_from_liml, before STEP 4).
    Returns True (nothing to do or done) or False after an ERROR (the
    bridge stops before Code-Aster).
    """
    atype = model_data.get("analysis_type", "")
    if atype in NOT_TRANSLATED_2D:
        # Otherwise a manually chosen 3D analysis would compute the plane
        # elements as shells
        return _fatal(
            "Mecway-analysetype {0} ({1}) wordt (nog) niet vertaald; de "
            "bridge vertaalt van de 2D-typen alleen Static 2D (S20) en "
            "Static Axisymmetric (SA0).",
            "Mecway analysis type {0} ({1}) is not translated (yet); of "
            "the 2D types the bridge only translates Static 2D (S20) and "
            "Static Axisymmetric (SA0).", atype, NOT_TRANSLATED_2D[atype])
    if atype not in PLANE_TYPES:
        return True
    solver = run_cfg.get("solver_command")
    need = _VERIFIED_SOLVERS[atype]
    if solver != need:
        return _fatal(
            "Mecway-analysetype {0} (2D) wordt alleen vertaald naar {1}, "
            "niet naar {2}. Kies op het startscherm 'auto' of {1}.",
            "Mecway analysis type {0} (2D) is only translated to {1}, not "
            "to {2}. Choose 'auto' or {1} on the start screen.", atype,
            _BRIDGE_ANALYSIS[need], solver or "?")
    if solver == "DYNA_NON_LINE" and (
            run_cfg.get("schema") in ("DIFF_CENT", "TCHAMWA") or
            model_data.get("mode_superposition")):
        return _fatal(
            "{0} (2D) wordt vertaald met het impliciete schema (NEWMARK of "
            "HHT, dyna_impl_3d); expliciet en Mode superposition zijn in 2D "
            "niet geverifieerd.",
            "{0} (2D) is translated with the implicit scheme (NEWMARK or "
            "HHT, dyna_impl_3d); explicit and Mode superposition are not "
            "verified in 2D.", atype)
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        return _fatal(
            "Een 2D-analyse ({0}) werkt alleen met de resultaatroute 'liml' "
            "(pagina Algemeen); de route 'tabel' schaalt de reactiekrachten "
            "niet naar de dikte of 360 graden.",
            "A 2D analysis ({0}) only works with the result route 'liml' "
            "(General page); the route 'tabel' does not scale the reaction "
            "forces to the thickness or 360 degrees.", atype)
    axis = PLANE_TYPES[atype] == "axis"
    # Model items without a verified 2D route (S16a)
    for key, what in _NOT_VERIFIED:
        if model_data.get(key):
            return _fatal(
                "{0} in een 2D-analyse ({1}) wordt (nog) niet vertaald; "
                "haal het weg of reken het model in 3D.",
                "{0} in a 2D analysis ({1}) is not translated (yet); remove "
                "it or compute the model in 3D.", what, atype)
    mods = model_data["elset_modelisations"]
    kinds = OrderedDict()           # (modelisation, thickness) -> [elsets]
    for elset in list(mods):
        shapes = set(elset_shapes.get(elset, ()))
        if not shapes:
            continue
        if not shapes <= PLANE_SHAPES:
            return _fatal(
                "Elset '{0}' bevat {1}; in een 2D-analyse ({2}) vertaalt de "
                "bridge alleen vlakke elementen (tri3, tri6, quad4, quad8), "
                "geen balken, truss, veren of volume-elementen.",
                "Elset '{0}' contains {1}; in a 2D analysis ({2}) the "
                "bridge only translates plane elements (tri3, tri6, quad4, "
                "quad8), no beams, trusses, springs or solid elements.",
                elset, ", ".join(sorted(shapes - PLANE_SHAPES)), atype)
        mat = model_data["elsets"].get(elset)
        geom = model_data["mat_geometrics"].get(mat) or {}
        thick = geom.get("thickness") if geom.get("geom_type") == "Plate" \
            else None
        if axis:
            mod, t = "AXIS", None
            if thick:
                log(tr("WARNING: Materiaal '{0}' heeft een dikte ({1} m); in "
                       "een axisymmetrische analyse (SA0) telt die niet (de "
                       "bridge negeert hem; Mecway's eigen solve geeft dan "
                       "geen oplossing).",
                       "WARNING: Material '{0}' has a thickness ({1} m); in "
                       "an axisymmetric analysis (SA0) it does not count "
                       "(the bridge ignores it; Mecway's own solve gives no "
                       "solution then).").format(mat, thick))
        else:
            if not thick or thick <= 0.0:
                return _fatal(
                    "Elset '{0}': Static 2D (S20) heeft een dikte nodig; geef "
                    "materiaal '{1}' in Mecway een geometrie Shell/membrane "
                    "met een dikte (ook voor plane strain; zonder dikte rekent "
                    "Mecway zelf ook niet).",
                    "Elset '{0}': Static 2D (S20) needs a thickness; give "
                    "material '{1}' a Shell/membrane geometry with a "
                    "thickness in Mecway (also for plane strain; Mecway "
                    "itself does not solve without one).", elset, mat)
            mod = "D_PLAN" if geom.get("planestrain") else "C_PLAN"
            t = float(thick)
        kinds.setdefault((mod, t), []).append(elset)
        mods[elset] = mod
        model_data["elset_dims"][elset] = "2D"
        for key in ("shell_sections", "shell_upgrades"):
            model_data.get(key, {}).pop(elset, None)
        log("INFO: Elset '{0}' -> MODELISATION='{1}'{2} (Mecway {3}).".format(
            elset, mod, "" if t is None else ", thickness {0} m".format(t),
            atype))
    if not kinds:
        return _fatal("Geen vlakke elementen in de 2D-analyse {0}.",
                      "No plane elements in the 2D analysis {0}.", atype)
    if len(kinds) > 1:
        return _fatal(
            "De 2D-analyse heeft elsets met verschillende modelisatie of "
            "dikte ({0}); de bridge vertaalt een model met een enkele "
            "dikte en een enkel type (plane stress of plane strain).",
            "The 2D analysis has elsets with different modelisation or "
            "thickness ({0}); the bridge translates a model with one "
            "thickness and one type (plane stress or plane strain).",
            "; ".join("{0} {1}: {2}".format(m, "" if t is None else t,
                                            ", ".join(e))
                      for (m, t), e in kinds.items()))
    (mod, t), _elsets = list(kinds.items())[0]
    # Nodes: XY plane (Mecway ignores Z, Code-Aster needs Z = 0 for a 2D
    # mesh) and X >= 0 for SA0 (Mecway manual v34 par. 6.1.3).
    used = set()
    for _eid, shape, nids, _es in model_data.get("mesh_elements", []):
        if shape in PLANE_SHAPES:
            used.update(nids)
    pts = [model_data["mesh_nodes"][n] for n in used
           if n in model_data["mesh_nodes"]]
    size = max([max(abs(p[0]), abs(p[1])) for p in pts] + [1.0e-30])
    zmax = max([abs(p[2]) for p in pts] + [0.0])
    if zmax > 1.0e-9 * size:
        return _fatal(
            "Een 2D-analyse ({0}) heeft alle knopen in het XY-vlak nodig "
            "(Z = 0); hier tot Z = {1} m. Code-Aster rekent een 2D-model "
            "alleen met Z = 0 (Mecway negeert Z).",
            "A 2D analysis ({0}) needs all nodes in the XY plane (Z = 0); "
            "here up to Z = {1} m. Code-Aster only computes a 2D model with "
            "Z = 0 (Mecway ignores Z).", atype, "%.4g" % zmax)
    if axis:
        xmin = min([p[0] for p in pts] + [0.0])
        if xmin < -1.0e-9 * size:
            return _fatal(
                "Axisymmetrisch (SA0): alle knopen moeten X >= 0 hebben (X = "
                "straal, Y = as); hier X tot {0} m.",
                "Axisymmetric (SA0): all nodes must have X >= 0 (X = radius, "
                "Y = axis); here X down to {0} m.", "%.4g" % xmin)
    factor = 2.0 * math.pi if axis else t
    model_data["plane"] = {"type": atype, "modelisation": mod,
                           "thickness": t, "factor": factor}
    log("INFO: 2D analysis {0}: MODELISATION='{1}'; concentrated forces / "
        "{2:.6g} and reactions x {2:.6g} ({3}).".format(
            atype, mod, factor,
            "per radian in Code-Aster, 360 degrees in Mecway" if axis else
            "per unit thickness in Code-Aster, thickness t in Mecway"))
    return True


def _div(value, k):
    """value (float, list (t, v) or PositionFormula) divided by k."""
    if isinstance(value, list):
        return [(tt, v / k) for tt, v in value]
    if hasattr(value, "scaled"):
        return value.scaled(1.0 / k)
    return value / k


def _skip(model_data, bc, why):
    bc["skip"] = True
    model_data.setdefault("skipped_loads", []).append(
        tr("{0} op '{1}' (2D)", "{0} on '{1}' (2D)").format(
            bc["type"], bc.get("selection") or "-"))
    log(tr("ERROR: {0} op '{1}' in een 2D-analyse: {2}. NIET meegenomen.",
           "ERROR: {0} on '{1}' in a 2D analysis: {2}. NOT included.").format(
               bc["type"], bc.get("selection") or "-", why))


def _edge_measure(model_data, sel, axis, thickness):
    """Area of the edges of sel: revolved area 2 pi int(r dl) (AXIS) or
    length x thickness (C_PLAN/D_PLAN); SEG3 isoparametric (3-point
    Gauss), SEG2 straight. Face list from bridge_mesh (nodes in Code-Aster
    order: end, end[, mid])."""
    nodes = model_data["mesh_nodes"]
    total = 0.0
    for f in model_data.get("group_face_list", {}).get(sel, []):
        ns = f["nodes"]
        pts = [nodes[n] for n in ns]
        for xi, w in _SEG_GAUSS:
            if len(pts) == 3:
                sh = [0.5 * xi * (xi - 1.0), 0.5 * xi * (xi + 1.0),
                      1.0 - xi * xi]
                dsh = [xi - 0.5, xi + 0.5, -2.0 * xi]
            else:
                sh = [0.5 * (1.0 - xi), 0.5 * (1.0 + xi)]
                dsh = [-0.5, 0.5]
            x = sum(s * p[0] for s, p in zip(sh, pts))
            dx = sum(d * p[0] for d, p in zip(dsh, pts))
            dy = sum(d * p[1] for d, p in zip(dsh, pts))
            jac = math.sqrt(dx * dx + dy * dy)
            total += w * jac * (2.0 * math.pi * x if axis else thickness)
    return total


def convert_bc(model_data, bc, faces, skin_groups):
    """
    2D translation of one load or constraint (bridge_mesh.
    _apply_to_model_data, after renaming the selection). Returns True if
    the load is done here (translated or skipped), False if the generic
    route may continue (constraints on nodes and edges, nodal forces;
    finish_bcs filters the components afterwards).
    """
    p = info(model_data)
    if p is None:
        return False
    sel = bc["selection"]
    kinds = (faces or {}).get("kinds") or set()
    edges = bool(kinds) and kinds <= set(["shelledge"])
    axis = p["modelisation"] == "AXIS"
    btype = bc["type"]
    if btype not in _HANDLED:
        _skip(model_data, bc, tr("niet vertaald in 2D (S16a: vast, "
                                 "verplaatsing, kracht, druk, traction, "
                                 "symmetrie, zwaartekracht, centrifugaal)",
                                 "not translated in 2D (S16a: fixed, "
                                 "displacement, force, pressure, traction, "
                                 "symmetry, gravity, centrifugal)"))
        return True
    if kinds and not edges:
        _skip(model_data, bc, tr("alleen randen van vlakke elementen "
                                 "(faceid 1..4), hier {0}",
                                 "only edges of plane elements (faceid "
                                 "1..4), here {0}").format(
                                     ", ".join(sorted(kinds))))
        return True
    if btype == "surfacepressure":
        if not edges:
            _skip(model_data, bc, tr("druk alleen op randen",
                                     "pressure only on edges"))
            return True
        # PRES_REP on the edge cells (U3.13.01: AXIS, C_PLAN, D_PLAN);
        # ORIE_PEAU orients them outwards like volume faces.
        if sel not in skin_groups:
            skin_groups.append(sel)
        bc["_plane"] = True
        log("INFO: Pressure on edges '{0}' -> PRES_REP (2D).".format(sel))
        return True
    if btype in ("traction", "force") and edges:
        params = dict(bc["params"])
        if btype == "force":
            area = _edge_measure(model_data, sel, axis, p["thickness"])
            if area <= 0.0:
                _skip(model_data, bc, tr("randen zonder lengte",
                                         "edges without length"))
                return True
            params = dict((k, v if k.startswith("_") else _div(v, area))
                          for k, v in params.items())
        z = params.get("z", 0.0)
        if z not in (0, 0.0, None):
            _skip(model_data, bc, tr("Z-component in een 2D-analyse",
                                     "Z component in a 2D analysis"))
            return True
        # Force per area on the edge (FORCE_CONTOUR, U3.13.01): Mecway's
        # traction directly; a force on edges uniform over the area, as
        # Mecway does (measured: uniform stress, see the header).
        bc["params"] = params
        bc["aster_keyword"] = "FORCE_CONTOUR"
        bc["aster_target"] = "GROUP_MA"
        bc["aster_dict"] = OrderedDict(
            ("F" + ax.upper(), params[ax]) for ax in ("x", "y")
            if params.get(ax) is not None)
        model_data.setdefault("edge_groups", OrderedDict())[sel] = \
            p["modelisation"]
        bc["_plane"] = True
        log("INFO: {0} on edges '{1}' -> FORCE_CONTOUR (2D){2}.".format(
            btype, sel, "" if btype == "traction" else
            ", area {0:.6g} m2".format(area)))
        return True
    if btype in ("traction", "force") and kinds:
        _skip(model_data, bc, tr("alleen op randen", "only on edges"))
        return True
    if btype == "traction":
        _skip(model_data, bc, tr("traction alleen op randen",
                                 "traction only on edges"))
        return True
    if btype == "symmetry":
        nrm = bc["params"].get("dir")
        if bc["params"].get("nodeplane") or nrm is None:
            _skip(model_data, bc, tr("alleen symmetrie met een normaal X of "
                                     "Y", "only symmetry with a normal X or "
                                     "Y"))
            return True
        comp = None
        for k, ax in enumerate("XY"):
            if abs(abs(nrm[k]) - 1.0) < 1.0e-9:
                comp = "D" + ax
        if comp is None:
            _skip(model_data, bc, tr("alleen symmetrie met een normaal X of "
                                     "Y", "only symmetry with a normal X or "
                                     "Y"))
            return True
        # Symmetry plane perpendicular to X or Y: that displacement zero
        # (Mecway manual v34: displacement normal to the plane = 0).
        bc["aster_keyword"] = "DDL_IMPO"
        bc["aster_dict"] = {comp: 0.0}
        bc["_plane"] = True
        log("INFO: Symmetry '{0}' -> DDL_IMPO {1}=0 (2D).".format(sel, comp))
        return True
    if btype == "displacement":
        d = bc["params"].get("dir")
        if d is not None and abs(d[2]) > 1.0e-12:
            _skip(model_data, bc, tr("richting met een Z-component",
                                     "direction with a Z component"))
            return True
        if d is not None and min(abs(d[0]), abs(d[1])) > 1.0e-12:
            _skip(model_data, bc, tr("schuine richting in het XY-vlak (niet "
                                     "geverifieerd in 2D); gebruik X of Y",
                                     "oblique direction in the XY plane "
                                     "(not verified in 2D); use X or Y"))
            return True
    return False


def finish_bcs(model_data):
    """
    After all loads (bridge_mesh._apply_to_model_data): drop the
    components a 2D model does not have (DZ, rotations, FZ, moments),
    divide the concentrated forces by the factor (t or 2 pi) and check
    gravity and centrifugal force against the plane.
    """
    p = info(model_data)
    if p is None:
        return
    axis = p["modelisation"] == "AXIS"
    factor = p["factor"]
    for bc in model_data.get("bcs", []):
        if bc.get("skip"):
            continue
        btype = bc["type"]
        if btype not in _HANDLED:
            _skip(model_data, bc, tr("niet vertaald in 2D",
                                     "not translated in 2D"))
            continue
        kw = bc.get("aster_keyword") or ""
        d = bc.get("aster_dict") or {}
        if bc.get("_plane"):
            continue
        if btype == "gravity" and d:
            dvec = d.get("DIRECTION", (0.0, 0.0, 0.0))
            bad = abs(dvec[2]) > 1.0e-12 or (axis and abs(dvec[0]) > 1.0e-12)
            if bad:
                _skip(model_data, bc, tr(
                    "zwaartekracht moet in het XY-vlak liggen (SA0: langs Y, "
                    "U3.13.01)", "gravity must lie in the XY plane (SA0: "
                    "along Y, U3.13.01)"))
            continue
        if btype == "centrifugal" and d:
            ax = d.get("AXE", (0.0, 0.0, 0.0))
            need = 1 if axis else 2
            if abs(abs(ax[need]) - 1.0) > 1.0e-12:
                _skip(model_data, bc, tr(
                    "rotatie-as moet {0} zijn",
                    "rotation axis must be {0}").format("Y" if axis else "Z"))
            continue
        if kw == "DDL_IMPO" and "BLOCAGE" not in d:
            new = OrderedDict((k, v) for k, v in d.items()
                              if k not in _DROP_DDL)
            if not new and d:
                _skip(model_data, bc, tr("alleen Z of rotaties",
                                         "only Z or rotations"))
                continue
            bc["aster_dict"] = new
        elif kw == "DDL_IMPO":
            bc["aster_dict"] = {"DX": 0.0, "DY": 0.0}
        elif kw == "FORCE_NODALE":
            new = OrderedDict()
            for k, v in sorted(d.items()):
                if k in _DROP_FORCE:
                    if v not in (0, 0.0):
                        log(tr("WARNING: {0} op '{1}': component {2} telt "
                               "niet in een 2D-analyse.",
                               "WARNING: {0} on '{1}': component {2} does "
                               "not count in a 2D analysis.").format(
                                   btype, bc.get("selection"), k))
                    continue
                new[k] = _div(v, factor)
            bc["aster_dict"] = new
        bc["_plane"] = True


def skin_modelisation(model_data, default="3D"):
    """MODELISATION of the boundary cells of pressure groups (AFFE_MODELE)."""
    p = info(model_data)
    return p["modelisation"] if p else default


def export_arg(model_data):
    """Extra argument for aster_results_export.export_results."""
    p = info(model_data)
    if p is None:
        return ""
    return ", plane={0!r}".format({"modelisation": str(p["modelisation"]),
                                   "factor": float(p["factor"])})


def static_check_arg(model_data):
    """Extra arguments for aster_results_export.print_static_check: the
    reactions and the mass of the whole body (thickness t or 360 degrees;
    MASS_INER of AXIS is already for 360 degrees, see there)."""
    p = info(model_data)
    if p is None:
        return ""
    mass = 1.0 if p["modelisation"] == "AXIS" else float(p["factor"])
    return ", scale={0!r}, mass_scale={1!r}".format(float(p["factor"]), mass)
