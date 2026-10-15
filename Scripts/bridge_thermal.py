# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_thermal.py
# Responsibility: thermal analyses from Mecway (T30 steady state, T31
# transient) to Code-Aster THER_LINEAIRE / THER_NON_LINE.
#
#   parse_thermal(root, model_data)  - called by bridge_from_liml.py
#                                      (only if the analysis is thermal):
#                                      materials, loads,
#                                      initial conditions and time steps.
#   build_thermal(...)               - builder for SOLVER_BUILDERS_ASTER
#                                      (bridge_to_aster._build_thermal):
#                                      study.comm + study.export.
#
# Mecway XML (Mecway 33; examples in C:\Program Files\Mecway\Samples:
# ConductionConvectionRadiation, FinConvection, OscillatingHeatFlow,
# CoolantChannel):
#   <analysis type="T30|T31" />  <timesteps timeperiod=".." stepsize=".." />
#   <mat><density density=".." /><thermal type="Isotropic"
#        thermalconductivity=".." specificheat=".." /></mat>
#   <temperature2 selection=".."><value>500 K</value><starttime>..
#   <temperature3><nodetemperature nid="1" value="300 K" /></temperature3>
#   <heatflow selection=".."><value>500 W</value> (or <value time="..">)
#   <heatflux selection="faces"><value>1000 W/m²</value>
#   <heatgeneration selection="elements"><value>1e6 W/m³</value>
#   <convectionbc selection=".."><ambienttemp>..<coefficient>..
#   <radiationbc selection=".."><ambienttemp>..<emissivity>..
#   <initialconditions><temperature2 selection=".."><value>..
#
# Translation (Code-Aster 17.4; U4.44.02 AFFE_CHAR_THER, U4.54.01
# THER_LINEAIRE, U4.54.02 THER_NON_LINE, U4.43.01 DEFI_MATERIAU THER/THER_NL):
#   - Temperatures in Code-Aster are in degrees CELSIUS: RAYONNEMENT uses
#     sigma*eps*((T+273.15)^4 - (T_ext+273.15)^4) (U4.44.02, "temperature
#     expressed in Celsius ... use only degrees Celsius for the whole
#     study"). Mecway values (K) become T - 273.15; aster_results_export
#     adds 273.15 to 'temperature' (VALUE_OFFSETS).
#   - Volume elements: MODELISATION '3D'; faces with a load become
#     boundary elements ('3D' on the skin cells, ORIE_PEAU).
#   - Shells: Mecway computes conduction in the plane of the shell (manual
#     v33 sec. 7.4, 6.7). Code-Aster's thermal 'COQUE' has three
#     temperatures through the thickness and edge loads only on TRIA
#     (U4.44.02 FLUX_REP/ECHANGE), so the bridge uses 'PLAN' (2D, depth
#     1) for shells in a plane Z = constant (otherwise "les résultats
#     seront faux", alarm MODELE1_53). If all shells lie in parallel
#     planes other than Z = constant, the .comm first rotates the mesh
#     (_Thermal._shell_rotation). A shell with thickness t becomes a
#     PLAN layer with factor f = t / t_ref on LAMBDA and RHO_CP and on all
#     loads per length (edges) and per area (sources); t_ref =
#     1 m if there are volume elements (then the coupling with the
#     volumes is correct), otherwise the most used shell thickness. Shells
#     of different thickness in one selection each get their own subgroup.
#     A load on the shell face (faceid 5/6) becomes a volume source q/t
#     (SOURCE), convection and radiation on the shell face a
#     temperature-dependent source (SOUR_NL, THER_NON_LINE). The heat flux
#     is computed by CALC_CHAMP with the real lambda (fieldmat_post, see
#     _Thermal.calc_champ_block).
#     Verification (Code-Aster 17.4): ConductionConvectionRadiation gives
#     380.278 K and 3591.65 W/m2 in shell and volume, as in Mecway manual
#     v33 sec. 11.13.
#   - Comparison with Mecway 33 (headless 'mecway <model> solve' with
#     <solutionfile filename=".."/>, internal solver): steady state equal
#     to ~1e-11 K (without radiation); in transient Mecway uses
#     Crank-Nicolson (THETA 0.5) with the load at the end of the step (see
#     KNOWN_BUGS 14).
#   - Beams (Mecway fin elements): Code-Aster has no thermal
#     1D element (catalog affe_modele.py, PHENOMENE='THERMIQUE'); not
#     translated.
#   - Formulas as value (x, y, z, t) -> FORMULE in AFFE_CHAR_THER_F
#     (class Formula); temperature-dependent material (TempDependent) ->
#     THER_NL with functions of TEMP (_Thermal._tempdep_funcs); moving
#     welding source (#ASTER-LASBRON) -> bridge_welding.py.
#   - Radiation and shell-face convection -> THER_NON_LINE with THER_NL
#     (ELEMENTS2_63 "On ne trouve pas le comportement THER_NL" with THER,
#     seen in a run with Code-Aster 17.4); otherwise THER_LINEAIRE with THER.
#
# Compatible with IronPython 2.7.9 (standard library only).

import math
import os
import re
from collections import OrderedDict

from bridge_utils import (log, parse_and_convert, CONFIG_BRIDGE, tr,
                          run_name)
import bridge_mesh


# Tags read by parse_thermal() (bridge_from_liml.py then skips them).
THERMAL_TAGS = frozenset(["temperature2", "temperature3", "heatflow",
                          "heatflux", "heatgeneration", "convectionbc",
                          "radiationbc", "forcedconvection",
                          "massflowrate"])

# Kelvin -> Celsius (Code-Aster computes thermal in Celsius, see header).
KELVIN = 273.15
# Stefan-Boltzmann [W/m2/K4], CODATA 2018 (Mecway manual v33 sec. 11.13
# gives 5.67037e-8).
STEFAN_BOLTZMANN = 5.670374419e-8
# Mecway: nodes without an initial temperature start at 0 K (manual v33
# sec. 6.7.2).
MECWAY_DEFAULT_T0 = 0.0

# Number followed by only a unit (no formula such as 100*cos(t)).
_NUMBER_UNIT = re.compile(
    u"^\\s*[-+]?(\\d+\\.?\\d*|\\.\\d+)([eE][-+]?\\d+)?"
    u"[\\sA-Za-z0-9/\\.\u00b0\u00b2\u00b3\u2074\u00b5\u03bc\u00b7]*$")


def is_thermal(analysis_cfg):
    """True if the analysis config is thermal (THER_LINEAIRE/_NON_LINE)."""
    return str(analysis_cfg.get("solver_command", "")).startswith("THER")


def _r(x):
    """Number for the .comm: 15 significant digits with a decimal point
    (bridge_mesh._real, %-formatting does not follow the locale). So
    300 - 273.15 becomes '26.85' and not 26.850000000000023 (CPython repr)
    or 26.850000000000001 (IronPython repr, 17 digits; seen in the
    IronPython harness)."""
    return bridge_mesh._real(float(x))


# ==========================================
# PARSEN
# ==========================================
class Formula(object):
    """
    Mecway formula as load value (mechanical:
    bridge_bcs.PositionFormula): in the .comm a FORMULE of X, Y, Z and INST
    (AFFE_CHAR_THER_F, catalog affe_char_ther_f.py: SOURCE, FLUX_REP,
    ECHANGE, RAYONNEMENT, TEMP_IMPO accept a formula).

    Value in SI = factor * (a * f(x/pu, y/pu, z/pu, t/tu) + b) + offset,
    with (a, b) the unit of the result (bridge_bcs._unit_map), pu/tu the
    SI value of positionunit/timeunit (Mecway writes the units as
    attributes, manual v33 sec. 12.1). factor/offset come from the
    translation (e.g. 1/area, K -> Celsius).
    """

    def __init__(self, text, qtype, unit, posunit, timeunit):
        import bridge_bcs
        self.text = (text or "").strip()
        # Syntax check; ValueError (reported) on an error.
        _expr, self.used, _args = bridge_bcs.aster_expression(
            self.text, dict((v, v) for v in ("x", "y", "z", "t")))
        self.a, self.b = bridge_bcs._unit_map(unit, qtype)
        self.pu = _unit_si(posunit, "length")
        self.tu = _unit_si(timeunit, "time")
        self.factor = 1.0
        self.offset = 0.0

    def _copy(self):
        new = Formula.__new__(Formula)
        new.__dict__.update(self.__dict__)
        return new

    def scaled(self, k):
        new = self._copy()
        new.factor *= k
        new.offset *= k
        return new

    def shifted(self, o):
        new = self._copy()
        new.offset += o
        return new

    def positional(self):
        return bool(self.used & set(["x", "y", "z"]))

    def at_time(self, t):
        """Value at time t (s); only without x, y, z."""
        import bridge_bcs
        fn = bridge_bcs.time_function(self.text)
        return self.factor * (self.a * float(fn(t / self.tu)) + self.b) + \
            self.offset

    def render(self, coords, inst="INST"):
        """(expression, NOM_PARA, {name: argument}) for FORMULE.
        coords: {"x": expression in X, Y, Z} (rotated mesh); inst:
        expression for the time (steady state: '1.0')."""
        import bridge_bcs
        var = {}
        for v in ("x", "y", "z"):
            var[v] = "(({0})/{1})".format(coords[v], _r(self.pu))
        var["t"] = "(({0})/{1})".format(inst, _r(self.tu))
        expr, used, args = bridge_bcs.aster_expression(self.text, var)
        expr = "{0}*({1}*({2})+{3})+{4}".format(
            _r(self.factor), _r(self.a), expr, _r(self.b), _r(self.offset))
        params = []
        for v, names in (("x", "XYZ"), ("y", "XYZ"), ("z", "XYZ")):
            if v in used:
                for n in names:
                    if n in coords[v] and n not in params:
                        params.append(n)
        if "t" in used and inst == "INST":
            params.append("INST")
        return expr, [p for p in ("X", "Y", "Z", "INST") if p in params], args


def _unit_si(unit, qtype):
    """SI value of 1 unit (positionunit/timeunit); 1 if empty."""
    unit = (unit or "").strip()
    if not unit:
        return 1.0
    v = parse_and_convert(u"1 " + unit, qtype)
    return v if isinstance(v, float) and v > 0.0 else 1.0


def _is_timed(value):
    return isinstance(value, (list, Formula))


def _value(text, qtype):
    """Number with unit to SI; ValueError for a formula or empty."""
    if text is None or not _NUMBER_UNIT.match(text):
        raise ValueError(tr(
            "waarde '{0}' is geen getal met eenheid (formules "
            "worden niet vertaald)",
            "value '{0}' is not a number with a unit (formulas "
            "are not translated)").format(text))
    return parse_and_convert(text, qtype)


_BARE_NUMBER = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$")


def _with_unit(node):
    """
    Text of a value node. Mecway writes a formula as
    <x unit="°C" timeunit="s" positionunit="m">20</x>: without a unit
    in the text; if the formula is just a number, the unit from the
    attribute belongs to it (otherwise 20 -> 20 K). A real formula stays
    text and is rejected by _value (reported).
    """
    text = node.text
    unit = node.get("unit")
    if unit and text is not None and _BARE_NUMBER.match(text):
        return u"{0} {1}".format(text.strip(), unit)
    return text


def _formula_node(node):
    """True if node is a Mecway formula: units as attributes and
    not a bare number (_with_unit)."""
    if not any(node.get(a) is not None for a in
               ("unit", "timeunit", "positionunit")):
        return False
    return not (node.text is not None and _BARE_NUMBER.match(node.text))


def _values(item, tag, qtype, formulas=True):
    """float, list (t, value) for <tag time="..">, Formula (formula in
    x, y, z, t; only with formulas=True), or None."""
    nodes = item.findall(tag)
    if not nodes:
        return None
    hist = []
    const = None
    for node in nodes:
        if _formula_node(node):
            if not formulas or node.get("time") is not None or len(nodes) > 1:
                raise ValueError(tr(
                    "formule '{0}' kan hier niet (alleen als enige waarde "
                    "van een belasting)",
                    "formula '{0}' is not allowed here (only as the single "
                    "value of a load)").format(node.text))
            try:
                return Formula(node.text, qtype, node.get("unit"),
                               node.get("positionunit"), node.get("timeunit"))
            except ValueError as e:
                raise ValueError(tr("formule '{0}' niet te lezen ({1})",
                                    "formula '{0}' cannot be read ({1})")
                                 .format(node.text, e))
        v = _value(_with_unit(node), qtype)
        if node.get("time") is not None:
            hist.append((_value(node.get("time"), "time"), v))
        else:
            const = v
    if hist:
        hist.sort(key=lambda tv: tv[0])
        return hist
    return const


def _tempdep_tables(node, name):
    """
    Tables of a temperature-dependent thermal material (Mecway
    manual v33 sec. 8.6; XML seen in a model saved with Mecway 33,
    mw.set_material_type(.., "thermal", "TempDependent")):
      <thermal type="TempDependent" thermalconductivity=".." ..>
        <specificheat temp="300 K" value="450 J/kg/K" />
        <thermalconductivity temp="300 K" value="50 W/m/K" />
      </thermal>
    (the attributes on <thermal> are leftovers of the type Isotropic and
    do not count if there is a table). Returns {"lambda_T": [(T in Celsius,
    W/m/K)], "cp_T": [(T, J/kg/K)]}, ascending in T; ValueError for a
    formula or an empty table.
    """
    out = {}
    for tag, key, qtype in (("thermalconductivity", "lambda_T",
                             "conductivity"),
                            ("specificheat", "cp_T", "specific_heat")):
        rows = []
        for row in node.findall(tag):
            rows.append((_value(row.get("temp"), "temperature") - KELVIN,
                         _value(row.get("value"), qtype)))
        if rows:
            rows.sort(key=lambda r: r[0])
            out[key] = rows
    if not out:
        raise ValueError(tr("TempDependent zonder tabel",
                            "TempDependent without a table"))
    for key, attr in (("lambda_T", "thermalconductivity"),
                      ("cp_T", "specificheat")):
        if key not in out:
            log(tr("WARNING: Thermisch materiaal '{0}' (TempDependent) heeft "
                   "geen tabel voor {1}; de vaste waarde wordt gebruikt.",
                   "WARNING: Thermal material '{0}' (TempDependent) has no "
                   "table for {1}; the constant value is used.").format(
                       name, attr))
    return out


def _selection_kind(root, name):
    # Without an XPath predicate ([@name='...']): an apostrophe in the
    # selection name gave a SyntaxError there.
    for tag, kind in (("nodeselection", "node"), ("faceselection", "face"),
                      ("elementselection", "element")):
        for node in root.findall(tag):
            if node.get("name") == name:
                return kind
    return None


def _skip(model_data, text):
    model_data.setdefault("skipped_loads", []).append(text)
    log(tr("ERROR: Niet vertaald: {0}.",
           "ERROR: Not translated: {0}.").format(text))


def parse_thermal(root, model_data):
    """
    Read the thermal data into model_data:
      "thermal"           : True
      "thermal_materials" : {mat: {"lambda", "rho", "cp"}}
      "thermal_data"      : {"materials", "loads", "node_temps",
                             "initial", "transient", "timesteps"}
    Untranslatable parts go to model_data["skipped_loads"].
    """
    th = {"materials": OrderedDict(), "loads": [], "node_temps": [],
          "initial": [], "transient": model_data.get("analysis_type") == "T31",
          "timesteps": {}}
    model_data["thermal"] = True
    model_data["thermal_materials"] = th["materials"]
    model_data["thermal_data"] = th

    # --- Materials ---
    for mat in root.findall("mat"):
        name = mat.get("name", "UnknownMat")
        node = mat.find("thermal")
        if node is None:
            continue
        ttype = node.get("type", "Isotropic")
        tables = {}
        if ttype == "TempDependent":
            try:
                tables = _tempdep_tables(node, name)
            except ValueError as e:
                _skip(model_data, tr("thermisch materiaal '{0}': {1}",
                                     "thermal material '{0}': {1}").format(
                    name, e))
                continue
        elif ttype != "Isotropic" or len(list(node)):
            _skip(model_data, tr("thermisch materiaal '{0}' van type '{1}'",
                                 "thermal material '{0}' of type '{1}'")
                  .format(name, ttype))
            continue
        if "lambda_T" in tables and not node.get("thermalconductivity"):
            node.set("thermalconductivity", "{0} W/m/K".format(
                _r(tables["lambda_T"][0][1])))
        if not node.get("thermalconductivity"):
            # E.g. the water of a fluid network (only specificheat,
            # CoolantChannel.liml).
            log(tr("WARNING: Materiaal '{0}' heeft geen thermalconductivity; "
                   "elementen ermee worden niet thermisch gerekend.",
                   "WARNING: Material '{0}' has no thermalconductivity; "
                   "elements using it are left out of the thermal "
                   "calculation.").format(name))
            continue
        try:
            props = {
                "lambda": _value(node.get("thermalconductivity"),
                                 "conductivity"),
                "cp": (_value(node.get("specificheat"), "specific_heat")
                       if node.get("specificheat") else 0.0),
                "rho": 0.0,
            }
            dens = mat.find("density")
            if dens is not None and dens.get("density"):
                props["rho"] = _value(dens.get("density"), "density")
        except ValueError as e:
            _skip(model_data, tr("thermisch materiaal '{0}': {1}",
                                 "thermal material '{0}': {1}").format(
                name, e))
            continue
        props.update(tables)
        if "cp_T" in tables:
            # check_capacity: rho*cp > 0 over the whole table
            props["cp"] = min(v for _t, v in tables["cp_T"])
        th["materials"][name] = props
        if tables:
            log("INFO: Thermal material '{0}' temperature-dependent "
                "(Mecway TempDependent): lambda(T) {1} points, cp(T) {2} "
                "points, rho={3} kg/m3; THER_NON_LINE.".format(
                    name, len(tables.get("lambda_T", [])),
                    len(tables.get("cp_T", [])), props["rho"]))
        else:
            log("INFO: Thermal material '{0}': lambda={1} W/m/K, rho={2} "
                "kg/m3, cp={3} J/kg/K".format(name, props["lambda"],
                                              props["rho"], props["cp"]))

    # --- Loads and boundary conditions ---
    for item in root:
        tag = item.tag
        if tag not in THERMAL_TAGS or item.get("suppressed", "") == "true":
            continue
        sel = item.get("selection", "")
        if tag in ("forcedconvection", "massflowrate"):
            # Fluid network (manual v33 sec. 7.12, 9.31, 9.33; only
            # CCX): no equivalent in the bridge.
            _skip(model_data, tr("{0} op '{1}' (vloeistofnetwerk)",
                                 "{0} on '{1}' (fluid network)").format(
                tag, sel or item.get("selectionfaces", "")))
            continue
        if tag == "temperature3":
            for nt in item.findall("nodetemperature"):
                try:
                    th["node_temps"].append((int(nt.get("nid")), _value(
                        nt.get("value"), "temperature")))
                except (TypeError, ValueError) as e:
                    _skip(model_data, tr(
                        "nodetemperature knoop {0}: {1}",
                        "nodetemperature node {0}: {1}").format(
                            nt.get("nid"), e))
            continue
        load = {"tag": tag, "sel": sel, "target": _selection_kind(root, sel)}
        try:
            if tag == "temperature2":
                load["value"] = _values(item, "value", "temperature")
                start = _value(item.findtext("starttime") or "0 s", "time")
                end = _value(item.findtext("endtime") or "0 s", "time")
                load["interval"] = (start, end)
            elif tag == "heatflow":
                load["value"] = _values(item, "value", "power")
            elif tag == "heatflux":
                load["value"] = _values(item, "value", "heat_flux")
            elif tag == "heatgeneration":
                load["value"] = _values(item, "value", "power_density")
            elif tag == "convectionbc":
                load["ambient"] = _values(item, "ambienttemp", "temperature")
                load["coef"] = _values(item, "coefficient", "heat_transfer")
            elif tag == "radiationbc":
                load["ambient"] = _values(item, "ambienttemp", "temperature")
                load["emissivity"] = _values(item, "emissivity",
                                             "dimensionless")
                if item.find("cavity") is not None or item.get("cavity"):
                    raise ValueError(tr(
                        "holteradiatie (cavity, alleen CCX)",
                        "cavity radiation (cavity, CCX only)"))
        except ValueError as e:
            _skip(model_data, tr("{0} op '{1}': {2}",
                                 "{0} on '{1}': {2}").format(tag, sel, e))
            continue
        missing = [k for k in ("value", "ambient", "coef", "emissivity")
                   if k in load and load[k] is None]
        if missing or load["target"] is None:
            _skip(model_data, tr("{0} op '{1}': {2}",
                                 "{0} on '{1}': {2}").format(
                tag, sel, tr("geen waarde", "no value") if missing
                else tr("selectie onbekend", "unknown selection")))
            continue
        th["loads"].append(load)
        log("INFO: Thermal: {0} on '{1}' ({2}).".format(
            tag, sel, load["target"]))

    # --- Initial conditions ---
    ic_root = root.find("initialconditions")
    for ic in (list(ic_root) if ic_root is not None else []):
        if ic.tag != "temperature2" or ic.get("suppressed", "") == "true":
            continue
        sel = ic.get("selection", "")
        try:
            v = _values(ic, "value", "temperature", formulas=False)
        except ValueError as e:
            _skip(model_data, tr("begintemperatuur op '{0}': {1}",
                                 "initial temperature on '{0}': {1}").format(
                sel, e))
            continue
        if isinstance(v, list):
            log(tr("WARNING: Begintemperatuur op '{0}' heeft een tijdstabel; "
                   "de eerste waarde wordt gebruikt.",
                   "WARNING: Initial temperature on '{0}' has a time table; "
                   "the first value is used.").format(sel))
            v = v[0][1]
        kind = _selection_kind(root, sel)
        if v is None or kind is None:
            _skip(model_data, tr("begintemperatuur op '{0}'",
                                 "initial temperature on '{0}'").format(sel))
            continue
        th["initial"].append((sel, kind, v))

    # --- Time steps (T31: stepsize; D31 wrote timepointsincrement) ---
    ts = root.find("timesteps")
    if ts is not None:
        step = ts.get("stepsize") or ts.get("timepointsincrement")
        th["timesteps"] = {
            "period": parse_and_convert(ts.get("timeperiod", "1 s"), "time"),
            "step": parse_and_convert(step, "time") if step else 0.0,
        }
        other = [k for k in ts.keys() if k not in (
            "timeperiod", "stepsize", "timepointsincrement")]
        if other:
            log(tr("WARNING: <timesteps>-attributen {0} worden niet gebruikt "
                   "(alleen timeperiod en stepsize).",
                   "WARNING: <timesteps> attributes {0} are not used "
                   "(only timeperiod and stepsize).").format(other))
    log("INFO: Thermal: {0} materials, {1} loads, {2} node"
        "temperatures, {3} initial conditions, {4}.".format(
            len(th["materials"]), len(th["loads"]), len(th["node_temps"]),
            len(th["initial"]), "transient" if th["transient"]
            else "steady-state"))


# ==========================================
# GEOMETRY
# ==========================================
def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _seg_length(pts):
    """Length of a SEG2 (2 points) or SEG3 (corner, corner, middle; 3-point
    Gauss on the quadratic curve)."""
    if len(pts) == 2:
        return _dist(pts[0], pts[1])
    total = 0.0
    for xi, w in ((-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
                  (0.774596669241483, 5.0 / 9.0)):
        # dN/dxi for N0 = xi(xi-1)/2, N1 = xi(xi+1)/2, N2 = 1-xi^2
        d = (xi - 0.5, xi + 0.5, -2.0 * xi)
        t = [sum(d[k] * pts[k][c] for k in range(3)) for c in range(3)]
        total += w * math.sqrt(sum(c * c for c in t))
    return total


def _face_area(stype, pts):
    return sum(bridge_mesh._face_integrals(stype, pts)[0])


# Tetrahedra (corner indices, Code-Aster order) per volume type; exact for
# elements with straight edges and flat faces (otherwise an approximation).
_TETS = {
    "TETRA": [(0, 1, 2, 3)],
    "PYRAM": [(0, 1, 2, 4), (0, 2, 3, 4)],
    "PENTA": [(0, 1, 2, 3), (1, 2, 3, 4), (2, 3, 4, 5)],
    "HEXA": [(0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6),
             (0, 4, 5, 6), (0, 5, 1, 6)],
}


def _solid_volume(atype, pts):
    for prefix, tets in _TETS.items():
        if atype.startswith(prefix):
            vol = 0.0
            for a, b, c, d in tets:
                u = [pts[b][k] - pts[a][k] for k in range(3)]
                v = [pts[c][k] - pts[a][k] for k in range(3)]
                w = [pts[d][k] - pts[a][k] for k in range(3)]
                vol += abs(u[0] * (v[1] * w[2] - v[2] * w[1]) -
                           u[1] * (v[0] * w[2] - v[2] * w[0]) +
                           u[2] * (v[0] * w[1] - v[1] * w[0])) / 6.0
            return vol
    return 0.0


# ==========================================
# BUILDER
# ==========================================
class _Thermal(object):
    """Collects groups, modelisations, functions and loads for the .comm."""

    def __init__(self, model_data, th, analysis):
        self.md = model_data
        self.th = th
        self.analysis = analysis
        self.renames = model_data.get("group_renames", {})
        self.used_names = set(model_data.get("mesh_group_names", set()))
        self.nodes = model_data["mesh_nodes"]
        self.transient = th["transient"]
        self.nonlinear = False
        self.has_exchange = False  # ECHANGE / RAYONNEMENT / SOUR_NL
        self.counter = 0
        self.crea_ma = []         # DEFI_GROUP step 1 (CREA_GROUP_MA)
        self.crea_ma2 = []        # DEFI_GROUP step 2 (DIFFE/INTERSEC)
        self.crea_no = []         # CREA_GROUP_NO
        self.skin3d = []          # skin groups of volumes ('3D', ORIE_PEAU)
        self.edges = []           # boundary groups of shells ('PLAN')
        self.funcs = []           # DEFI_FONCTION / DEFI_CONSTANTE
        self.charges = []         # (command, OrderedDict kw -> [_F])
        self.temp_const = []      # TEMP_IMPO constant
        self.temp_timed = []      # TEMP_IMPO with function
        self.face_cache = {}
        self.inactive_faces = {}
        self.shells_union = None
        self.rotation = None      # classify: (Q, axis, angle) or None
        self.msh_path = None      # written mesh (build_thermal)
        self.mesh_segs = None     # _edge_names: {name: nodes} of SEG
        self.mesh_groups = None   # _edge_names: {group: [element names]}
        self.cell_index = None    # _list_group: {element name: cell number}
        self.node_flows = []      # (node group, value per node or table)
        self.birth = None         # filler material (bridge_welding._births)
        # Sources as functions (SOURCE in AFFE_CHAR_THER_F) together in one
        # load (add_func_source, merged_sources): [{grp, sour, eids}]
        self.func_sources = []
        self.sources_taken = False  # bridge_welding put them in 'lasbron'
        self.group_cells = {}     # grp -> [eid] (element_targets, shell face)
        self.func_params = {}     # function name -> NOM_PARA or constant

    # ---------- names ----------
    def rn(self, name):
        return self.renames.get(name, name)

    def new_group(self, prefix="TH"):
        while True:
            self.counter += 1
            name = "{0}{1}".format(prefix, self.counter)
            if name not in self.used_names:
                self.used_names.add(name)
                return name

    def skip(self, text):
        _skip(self.md, text)

    # ---------- elements ----------
    def classify(self):
        """Which elsets are modelled (volume '3D', flat shell
        'PLAN'); not beams, curved shells and elsets without thermal
        material. Returns False if there is nothing to compute."""
        md = self.md
        mats = self.th["materials"]
        self.elsets = OrderedDict()   # elset -> dict(cls, mat, t, f)
        self.elem = {}                # eid -> (elset, cls, atype, cn)
        members = OrderedDict()
        for eid, shape, enodes, elset in md.get("mesh_elements", []):
            atype, order = bridge_mesh._ASTER_TYPES[shape]
            cn = [enodes[i] for i in order]
            members.setdefault(self.rn(elset), []).append((eid, atype, cn))
        size = 0.0
        if self.nodes:
            for c in range(3):
                vals = [p[c] for p in self.nodes.values()]
                size = max(size, max(vals) - min(vals))
        tol = 1.0e-9 * max(size, 1.0e-3)
        # All shells in parallel planes other than Z = constant: the mesh
        # is rotated in the .comm (see _shell_rotation).
        self.rotation = self._shell_rotation(members, mats)
        zrow = self.rotation[0][2] if self.rotation else (0.0, 0.0, 1.0)
        # Order of the .liml (the dicts in model_data have no fixed order
        # in IronPython).
        for elset, elems in members.items():
            dim = md.get("elset_dims", {}).get(elset)
            mat = md["elsets"].get(elset)
            if dim is None:
                continue
            if dim == "1D":
                self.skip(tr("elset '{0}': balken/fin-elementen (Code-Aster "
                             "heeft geen thermisch 1D-element)",
                             "elset '{0}': beams/fin elements (Code-Aster "
                             "has no thermal 1D element)").format(elset))
                continue
            if mat not in mats:
                self.skip(tr("elset '{0}': materiaal '{1}' zonder "
                             "(ondersteunde) thermische eigenschappen",
                             "elset '{0}': material '{1}' without "
                             "(supported) thermal properties").format(
                                 elset, mat))
                continue
            info = {"cls": "solid" if dim == "3D" else "shell", "mat": mat,
                    "t": 1.0, "f": 1.0, "n": len(elems)}
            if dim == "2D":
                t = md.get("shell_sections", {}).get(elset, {}).get(
                    "thickness")
                zs = [_dot(zrow, self.nodes[n])
                      for _e, _a, cn in elems for n in cn]
                if not t:
                    self.skip(tr("elset '{0}': schaal zonder dikte",
                                 "elset '{0}': shell without thickness")
                              .format(elset))
                    continue
                if max(zs) - min(zs) > tol:
                    self.skip(tr("elset '{0}': schaal niet vlak of niet "
                                 "evenwijdig aan de andere schalen (thermisch "
                                 "alleen als PLAN-model: alle schalen in "
                                 "evenwijdige vlakken)",
                                 "elset '{0}': shell not flat or not parallel "
                                 "to the other shells (thermal only as a PLAN "
                                 "model: all shells in parallel planes)")
                              .format(elset))
                    continue
                info["t"] = t
            self.elsets[elset] = info
            for eid, atype, cn in elems:
                self.elem[eid] = (elset, info["cls"], atype, cn)
        if not self.elsets:
            log(tr("ERROR: Geen elset die thermisch gerekend kan worden.",
                   "ERROR: No elset that can be included in the thermal "
                   "calculation."))
            return False
        shells = [i for i in self.elsets.values() if i["cls"] == "shell"]
        if any(i["cls"] == "solid" for i in self.elsets.values()):
            self.t_ref = 1.0
        elif shells:
            count = {}
            for i in shells:
                count[i["t"]] = count.get(i["t"], 0) + i["n"]
            self.t_ref = max(count.items(), key=lambda kv: kv[1])[0]
        else:
            self.t_ref = 1.0
        for i in shells:
            i["f"] = i["t"] / self.t_ref
        if shells:
            log("INFO: Shells as PLAN with reference thickness {0} m; factors "
                "f = t / t_ref: {1}".format(self.t_ref, dict(
                    (k, v["f"]) for k, v in self.elsets.items()
                    if v["cls"] == "shell")))
        self.modelled = set(n for _s, _c, _a, cn in self.elem.values()
                            for n in cn)
        if any("lambda_T" in mats[i["mat"]] or "cp_T" in mats[i["mat"]]
               for i in self.elsets.values()):
            # THER_NL with functions of TEMP (_tempdep_funcs)
            self.nonlinear = True
        return True

    def _shell_rotation(self, members, mats):
        """(Q, axis, angle in degrees) if all shell elements are parallel
        but do not lie in a plane Z = constant, otherwise None. Q (rows)
        rotates the shell normal n onto Z (Rodrigues, clockwise about
        axis = n x Z).

        PLAN computes in the XY plane (AFFE_MODELE: alarm MODELE1_53 "les
        résultats seront faux" for an element outside Z = constant). The
        .comm therefore rotates the whole mesh (MODI_MAILLAGE ROTATION,
        rigid: volumes, temperatures and areas do not change) and rotates
        the heat flux back after CALC_CHAMP (calc_champ_block). Tested with
        Code-Aster 17.4 against Mecway (plane XZ and inclined plane,
        KNOWN_BUGS 15)."""
        n0 = None
        md = self.md
        for elset, elems in members.items():
            if (md.get("elset_dims", {}).get(elset) != "2D" or
                    md["elsets"].get(elset) not in mats or
                    not md.get("shell_sections", {}).get(elset, {}).get(
                        "thickness")):
                continue
            for _eid, atype, cn in elems:
                p = [self.nodes[n] for n in
                     cn[:bridge_mesh._N_CORNERS[atype]]]
                nrm = _cross(_sub(p[1], p[0]), _sub(p[-1], p[0]))
                length = math.sqrt(_dot(nrm, nrm))
                if length == 0.0:
                    return None
                nrm = [c / length for c in nrm]
                if n0 is None:
                    n0 = nrm
                else:
                    c = _cross(nrm, n0)
                    if _dot(c, c) > 1.0e-12:
                        return None
        if n0 is None or abs(n0[2]) > 1.0 - 1.0e-12:
            return None
        if n0[2] < 0.0:
            n0 = [-c for c in n0]
        axis = (n0[1], -n0[0], 0.0)       # n0 x (0, 0, 1)
        s = math.sqrt(_dot(axis, axis))
        k = [c / s for c in axis]
        ang = math.atan2(s, n0[2])
        cs, sn = math.cos(ang), math.sin(ang)
        kx = ((0.0, -k[2], k[1]), (k[2], 0.0, -k[0]), (-k[1], k[0], 0.0))
        q = tuple(tuple((cs if i == j else 0.0) + (1.0 - cs) * k[i] * k[j] +
                        sn * kx[i][j] for j in range(3)) for i in range(3))
        log("INFO: Shells lie in parallel planes with normal ({0}, "
            "{1}, {2}); the mesh is rotated {3} degrees about ({4}, {5}, 0) "
            "so that they lie in a plane Z = constant (PLAN).".format(
                _r(n0[0]), _r(n0[1]), _r(n0[2]), _r(math.degrees(ang)),
                _r(k[0]), _r(k[1])))
        return q, k, math.degrees(ang)

    # ---------- target groups ----------
    def face_parts(self, sel):
        """[(kind, area, nodes, f, t, (eid, faceid))] of a
        face selection; kind solid / shelledge / shellface / inactive."""
        parts = []
        for eid, fid in self.md.get("face_selection_faces", {}).get(sel, []):
            key = (eid, fid)
            info = self.elem.get(eid)
            if info is None:
                parts.append(("inactive", 0.0, [], 1.0, 1.0, key))
                continue
            elset, cls, atype, cn = info
            e = self.elsets[elset]
            pts = lambda ns: [self.nodes[n] for n in ns]
            if cls == "shell" and fid in (5, 6):
                parts.append(("shellface", _face_area(atype, pts(cn)), cn,
                              e["f"], e["t"], key))
                continue
            corners = bridge_mesh._face_from_table(atype, cn, fid)
            if not corners:
                parts.append(("inactive", 0.0, [], 1.0, 1.0, key))
                continue
            stype, snodes = bridge_mesh._skin_element(atype, cn, corners)
            if cls == "solid":
                parts.append(("solid", _face_area(stype, pts(snodes)),
                              snodes, 1.0, 1.0, key))
            else:
                parts.append(("shelledge",
                              _seg_length(pts(snodes)) * e["t"], snodes,
                              e["f"], e["t"], key))
        return parts

    def _shells_group(self):
        if self.shells_union is None:
            self.shells_union = self.new_group("THS")
            groups = [g for g, i in self.elsets.items() if i["cls"] == "shell"]
            self.crea_ma.append("_F(NOM='{0}', UNION={1})".format(
                self.shells_union, _fmt_groups(groups)))
        return self.shells_union

    def _sub_group(self, src, type_maille):
        """Subgroup of src with only the elements of one dimension
        (DEFI_GROUP TYPE_MAILLE)."""
        sub = self.new_group()
        self.crea_ma.append("_F(NOM='{0}', GROUP_MA='{1}', "
                            "TYPE_MAILLE='{2}')".format(sub, src, type_maille))
        return sub

    def _list_group(self, names):
        """Subgroup with a MAILLE list of elements from the mesh (names
        as bridge_mesh writes them: 'M<eid>', 'K<n>').

        Code-Aster 17.4 does not keep the element names of the ASTER mesh:
        MAILLE='M<n>' is the n-th cell in the file (char8_to_int.F90 reads
        the number after the letter; 'K5' gave "Fortran runtime error: Bad
        integer for item 1 in list input", 'M1001' in a mesh with 20 cells
        MODELISA6_10 "ne fait pas partie du maillage"; seen with Code-
        Aster 17.4). So the bridge translates the name to the cell number
        from model_data["cell_names"] (bridge_mesh, order in the
        file)."""
        if self.cell_index is None:
            self.cell_index = dict(
                (n, i + 1) for i, n in enumerate(self.md.get("cell_names", [])))
        refs = []
        for name in names:
            pos = self.cell_index.get(name)
            if pos is None:
                raise ValueError(name)
            refs.append("'M{0}'".format(pos))
        sub = self.new_group()
        self.crea_ma.append("_F(NOM='{0}', MAILLE={1})".format(
            sub, _fmt_seq(refs)))
        return sub

    def _edge_names(self, sel):
        """{frozenset(nodes): element name} of the boundary elements (SEG)
        in the mesh group of the selection. bridge_mesh does not keep the
        names of the boundary elements in model_data, so they come from the
        written mesh (self.msh_path; only needed for shell edges of
        different thickness in one selection)."""
        if self.mesh_segs is None:
            self.mesh_segs, self.mesh_groups = _read_mesh_segments(
                self.msh_path)
        members = set(self.mesh_groups.get(self.rn(sel), []))
        return dict((nodes, name) for name, nodes in self.mesh_segs.items()
                    if name in members)

    def face_targets(self, sel, label):
        """([(kind, group, f, t)], area) for loads on
        faces; kind solid / shelledge / shellface, area = total
        of the translated faces (edges: length x thickness). None if
        nothing is left.

        Shells with different thickness in one selection (KNOWN_BUGS 15)
        and shell elements with both sides (faceid 5 and 6) selected
        get their own subgroups with a MAILLE list per (f, t, number of
        sides), so that each thickness gets its own factor."""
        if sel in self.face_cache:
            return self.face_cache[sel]
        try:
            value = self._face_targets(sel, label)
        except ValueError as e:
            self.skip(tr("{0}: element {1} niet in het mesh gevonden",
                         "{0}: element {1} not found in the mesh").format(
                             label, e))
            value = None
        self.face_cache[sel] = value
        return value

    def _face_targets(self, sel, label):
        parts = self.face_parts(sel)
        kinds = OrderedDict()     # kind -> OrderedDict((f, t) -> True)
        for kind, _a, _n, f, t, _key in parts:
            if kind != "inactive":
                kinds.setdefault(kind, OrderedDict())[(f, t)] = True
        self.inactive_faces[sel] = sum(1 for p in parts if p[0] == "inactive")
        if self.inactive_faces[sel]:
            log(tr("WARNING: {0}: {1} vlak(ken) van balken of niet-"
                   "gemodelleerde elementen in '{2}' vallen weg.",
                   "WARNING: {0}: {1} face(s) of beams or non-modelled "
                   "elements in '{2}' are dropped.").format(
                       label, self.inactive_faces[sel], sel))
        # Shell faces: faceid 5 and 6 of the same element appear in the
        # mesh group twice as the same element (bridge_mesh); Code-
        # Aster removes the duplicate (alarm MODELISA5_8), so the load would
        # act on only one side while heatflow is distributed over both
        # sides (2A). So the bridge puts the load on both sides: a
        # separate group with f x 2 (convection, radiation, flux, heatflow).
        # Mecway does the same (Mecway 33, internal solver, headless
        # 'mecway <model> solve'): a plate with heatflux or convection on
        # faceid 5 and 6 gives 2x the heating / the fin with 2h, and heatflow
        # is distributed over both sides; Code-Aster via the bridge deviates
        # < 1e-11 K (headless Mecway run).
        sides = OrderedDict()
        for kind, _a, _n, _f, _t, key in parts:
            if kind == "shellface":
                sides.setdefault(key[0], set()).add(key[1])
        double = [e for e, fids in sides.items() if len(fids) > 1]
        if double:
            log("INFO: {0}: {1} shell element(s) in '{2}' have both "
                "sides (faceid 5 and 6) selected; the load acts on "
                "both sides (factor 2), as in Mecway.".format(
                    label, len(double), sel))
        split_face = "shellface" in kinds and (
            bool(double) or len(kinds["shellface"]) > 1)
        split_edge = len(kinds.get("shelledge", ())) > 1
        out = []                  # (kind, group, f, t)
        g = self.rn(sel)
        if len(kinds) == 1 and not (split_face or split_edge):
            kind = list(kinds)[0]
            f, t = list(kinds[kind])[0]
            out.append((kind, g, f, t))
        elif kinds:
            if "shelledge" in kinds:
                if split_edge:
                    edges = self._edge_lists(sel, parts, label)
                    if edges is None:
                        del kinds["shelledge"]
                    else:
                        out += edges
                else:
                    f, t = list(kinds["shelledge"])[0]
                    out.append(("shelledge", self._sub_group(g, "1D"), f, t))
            # Volume faces and shell faces are both 2D: separate them with
            # the group of all shells.
            both = "solid" in kinds and "shellface" in kinds
            tmp = self._sub_group(g, "2D") if both else None
            if "solid" in kinds:
                if both:
                    shells = self._shells_group()
                    grp = self.new_group()
                    self.crea_ma2.append("_F(NOM='{0}', DIFFE=('{1}', '{2}'))"
                                         .format(grp, tmp, shells))
                else:
                    grp = self._sub_group(g, "2D")
                out.append(("solid", grp, 1.0, 1.0))
            if "shellface" in kinds:
                if split_face:
                    out += self._face_lists(parts, sides, kinds["shellface"])
                else:
                    f, t = list(kinds["shellface"])[0]
                    if both:
                        shells = self._shells_group()
                        grp = self.new_group()
                        self.crea_ma2.append(
                            "_F(NOM='{0}', INTERSEC=('{1}', '{2}'))".format(
                                grp, tmp, shells))
                    else:
                        grp = self._sub_group(g, "2D")
                    out.append(("shellface", grp, f, t))
        area = sum(p[1] for p in parts if p[0] in kinds)
        shell_eids = list(OrderedDict.fromkeys(
            p[5][0] for p in parts if p[0] == "shellface"))
        for kind, grp, _f, _t in out:
            if kind == "shellface" and grp not in self.group_cells:
                # shell-face source (SOURCE): the shell elements themselves
                self.group_cells[grp] = shell_eids
            if kind == "solid" and grp not in self.skin3d:
                self.skin3d.append(grp)
            if kind == "shelledge" and grp not in self.edges:
                self.edges.append(grp)
        return (out, area) if out and area > 0.0 else None

    def _face_lists(self, parts, sides, fts):
        """Shell faces per (f, t, number of sides) in their own group
        (element names 'M<eid>', bridge_mesh); f times the number of sides.
        Order: per thickness first the single-sided, then the double-sided."""
        order = list(fts)
        by_key = OrderedDict()
        done = set()
        for kind, _a, _n, f, t, key in parts:
            if kind != "shellface" or key[0] in done:
                continue
            done.add(key[0])
            nsides = len(sides[key[0]])
            by_key.setdefault((order.index((f, t)), nsides, f, t),
                              []).append(key[0])
        out = []
        for k in sorted(by_key):
            _i, nsides, f, t = k
            grp = self._list_group(["M{0}".format(e) for e in by_key[k]])
            self.group_cells[grp] = by_key[k]
            out.append(("shellface", grp, f * nsides, t))
        return out

    def _edge_lists(self, sel, parts, label):
        """Shell edges per (f, t) in their own group; None (reported) if
        a boundary element is not found in the mesh."""
        try:
            names = self._edge_names(sel)
        except (IOError, OSError, ValueError, IndexError) as e:
            log(tr("ERROR: Mesh '{0}' niet te lezen: {1}",
                   "ERROR: Mesh '{0}' cannot be read: {1}").format(
                       self.msh_path, e))
            names = {}
        by_ft = OrderedDict()
        missing = 0
        for kind, _a, snodes, f, t, _key in parts:
            if kind != "shelledge":
                continue
            name = names.get(frozenset(snodes))
            if name is None:
                missing += 1
                continue
            lst = by_ft.setdefault((f, t), [])
            if name not in lst:
                lst.append(name)
        if missing:
            self.skip(tr("{0}: schaalranden van verschillende dikte in '{1}' "
                         "({2} randelement(en) niet in het mesh gevonden)",
                         "{0}: shell edges of different thicknesses in '{1}' "
                         "({2} edge element(s) not found in the mesh)").format(
                             label, sel, missing))
            return None
        return [("shelledge", self._list_group(lst), f, t)
                for (f, t), lst in by_ft.items()]

    def element_targets(self, sel, label):
        """([(kind, group, f, t)], volume) for sources on elements;
        kind solid / shell. Shells of different thickness each get
        their own group (MAILLE list per (f, t), KNOWN_BUGS 15)."""
        eids = self.md.get("element_selections", {}).get(self.rn(sel), [])
        kinds = OrderedDict()     # kind -> OrderedDict((f, t) -> [eid])
        vol = 0.0
        dropped = 0
        for eid in eids:
            info = self.elem.get(eid)
            if info is None:
                dropped += 1
                continue
            elset, cls, atype, cn = info
            e = self.elsets[elset]
            pts = [self.nodes[n] for n in cn]
            if cls == "solid":
                vol += _solid_volume(atype, pts)
            else:
                vol += _face_area(atype, pts) * e["t"]
            kinds.setdefault(cls, OrderedDict()).setdefault(
                (e["f"], e["t"]), []).append(eid)
        if dropped:
            self.skip(tr("{0}: {1} element(en) van '{2}' worden niet "
                         "gemodelleerd (balken of overgeslagen elsets)",
                         "{0}: {1} element(s) of '{2}' are not modelled "
                         "(beams or skipped elsets)").format(
                             label, dropped, sel))
        g = self.rn(sel)
        out = []
        multi = len(kinds.get("shell", ())) > 1
        def flat(kind):
            return [e for lst in kinds[kind].values() for e in lst]
        if len(kinds) == 1 and not multi:
            kind = list(kinds)[0]
            f, t = list(kinds[kind])[0]
            out.append((kind, g, f, t))
            self.group_cells[g] = flat(kind)
        elif kinds:
            if "solid" in kinds:
                grp = self._sub_group(g, "3D")
                self.group_cells[grp] = flat("solid")
                out.append(("solid", grp, 1.0, 1.0))
            if "shell" in kinds:
                if multi:
                    for (f, t), lst in kinds["shell"].items():
                        try:
                            grp = self._list_group(
                                ["M{0}".format(e) for e in lst])
                        except ValueError as e:
                            self.skip(tr(
                                "{0}: element {1} niet in het mesh gevonden",
                                "{0}: element {1} not found in the mesh")
                                .format(label, e))
                            return None
                        self.group_cells[grp] = list(lst)
                        out.append(("shell", grp, f, t))
                else:
                    f, t = list(kinds["shell"])[0]
                    grp = self._sub_group(g, "2D")
                    self.group_cells[grp] = flat("shell")
                    out.append(("shell", grp, f, t))
        return (out, vol) if out and vol > 0.0 else None

    def selection_nodes(self, sel, kind):
        if kind == "node":
            return set(int(str(n).lstrip("N")) for n in
                       self.md.get("node_groups", {}).get(self.rn(sel), []))
        if kind == "element":
            out = set()
            shapes = dict((e, en) for e, _s, en, _es in
                          self.md.get("mesh_elements", []))
            for eid in self.md.get("element_selections", {}).get(
                    self.rn(sel), []):
                out.update(shapes.get(eid, []))
            return out
        out = set()
        for part in self.face_parts(sel):
            out.update(part[2])
        # Faces of beams: nodes from the Mecway table of the line element
        conn = dict((e, en) for e, s, en, _es in
                    self.md.get("mesh_elements", []) if s.startswith("line"))
        for eid, fid in self.md.get("face_selection_faces", {}).get(sel, []):
            if eid in conn:
                en = conn[eid]
                out.update({1: en, 2: en[:1], 3: en[-1:]}.get(fid, en))
        return out

    def node_target(self, sel, kind, label):
        """('GROUP_MA'|'GROUP_NO', group) for TEMP_IMPO / initial values;
        only modelled nodes (otherwise a separate node group)."""
        nodes = self.selection_nodes(sel, kind)
        keep = sorted(nodes & self.modelled)
        if not keep:
            self.skip(tr("{0} op '{1}': geen knopen van gemodelleerde "
                         "elementen",
                         "{0} on '{1}': no nodes of modelled elements")
                      .format(label, sel))
            return None
        g = self.rn(sel)
        if len(keep) == len(nodes):
            if kind == "node" or g in self.md.get("face_node_groups", set()):
                return ("GROUP_NO", g)
            return ("GROUP_MA", g)
        log(tr("WARNING: {0} op '{1}': {2} van {3} knopen liggen niet op "
               "gemodelleerde elementen en vallen weg.",
               "WARNING: {0} on '{1}': {2} of {3} nodes do not lie on "
               "modelled elements and are dropped.").format(
                   label, sel, len(nodes) - len(keep), len(nodes)))
        sub = self.new_group("THN")
        self.crea_no.append("_F(NOM='{0}', NOEUD={1})".format(
            sub, _fmt_seq(["'N{0}'".format(n) for n in keep])))
        return ("GROUP_NO", sub)

    # ---------- values and functions ----------
    def formula_coords(self):
        """{"x"|"y"|"z": expression in X, Y, Z of Code-Aster}. With a
        rotated mesh (_shell_rotation: x_rot = Q x), x = Q^T x_rot."""
        if not self.rotation:
            return {"x": "X", "y": "Y", "z": "Z"}
        q = self.rotation[0]
        out = {}
        for j, v in enumerate(("x", "y", "z")):
            out[v] = "+".join("({0})*{1}".format(_r(q[i][j]), "XYZ"[i])
                              for i in range(3) if abs(q[i][j]) > 1.0e-15)
        return out

    def formula(self, fobj):
        """Name of a FORMULE for a Formula (Mecway formula)."""
        import bridge_bcs
        expr, params, args = fobj.render(
            self.formula_coords(), "INST" if self.transient else "1.0")
        if not self.funcs or self.funcs[0] != bridge_bcs.ASTER_FORMULA_PRELUDE:
            self.funcs.insert(0, bridge_bcs.ASTER_FORMULA_PRELUDE)
        self.counter += 1
        name = "FF{0}".format(self.counter)
        if not params:
            # Only t in a steady-state analysis: t = 1 s filled in
            params = ["INST"]
        self.func_params[name] = list(params)
        self.funcs.append("{0} = FORMULE(\n    VALE='{1}',\n    NOM_PARA={2},"
                          "{3}\n)  # Mecway: {4}".format(
                              name, expr, _fmt_seq(
                                  ["'{0}'".format(p) for p in params]),
                              "".join("\n    {0}={1},".format(k, v)
                                      for k, v in sorted(args.items())),
                              _ascii(fobj.text)))
        return name

    def steady(self, value, label):
        """Steady state: a time table becomes the value at t = 1 s, as
        Mecway with CCX. Measured with Mecway 33 (headless 'mecway <model>
        solve', T30):
          - CCX (solver="ccx"): linearly interpolated at t = 1 s, the end
            of the step (temperature2 0 s/300 K, 2 s/500 K -> 400 K; 0.5 s/
            300 K, 0.8 s/600 K, 2 s/500 K -> 583.33 K; also with <timesteps
            timeperiod="2 s">; convection and heatgeneration likewise);
          - internal solver: a quantity with a table counts as 0
            (heatgeneration with any table: no source; convection with a
            table for T_amb: computes with 0 K, for h: no convection;
            temperature2 with a table: not imposed).
        The bridge follows CCX and reports how the internal solver differs.
        A formula in t gets t = 1 s (NOT compared with Mecway)."""
        if isinstance(value, Formula):
            if "t" not in value.used:
                return value
            log(tr("WARNING: {0}: formule in t in een stationaire analyse; "
                   "de bridge vult t = 1 s in (zoals een tijdstabel).",
                   "WARNING: {0}: formula in t in a steady-state analysis; "
                   "the bridge uses t = 1 s (like a time table).").format(
                       label))
            if value.positional():
                return value
            return value.at_time(1.0)
        if isinstance(value, list):
            v = _interpolate(value, 1.0)
            if str(self.md.get("analysis_solver", "")).lower() == "ccx":
                log("INFO: {0}: time table in a steady-state analysis; "
                    "value at t = 1 s used ({1}), as Mecway does with "
                    "CCX.".format(label, _r(v)))
            else:
                log(tr("WARNING: {0}: tijdstabel in een stationaire analyse; "
                       "de bridge gebruikt de waarde op t = 1 s ({1}), zoals "
                       "Mecway met CCX. Mecway's interne solver telt een "
                       "tabel in een stationaire analyse als 0 (een "
                       "temperatuur wordt dan niet opgelegd); de resultaten "
                       "verschillen daarom van die solver.",
                       "WARNING: {0}: time table in a steady-state "
                       "analysis; the bridge uses the value at t = 1 s ({1}), "
                       "like Mecway with CCX. Mecway's internal solver "
                       "counts a table in a steady-state analysis as 0 (a "
                       "temperature is then not imposed); the results "
                       "therefore differ from that solver.").format(
                           label, _r(v)))
            return v
        return value

    def func(self, value):
        """Name of a DEFI_FONCTION (list), FORMULE (Formula) or
        DEFI_CONSTANTE (number)."""
        if isinstance(value, Formula):
            return self.formula(value)
        self.counter += 1
        name = "FT{0}".format(self.counter)
        if isinstance(value, list):
            self.func_params[name] = ["INST"]
            self.funcs.append(
                "{0} = DEFI_FONCTION(NOM_PARA='INST', VALE=(\n    {1},\n), "
                "PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')".format(
                    name, ",\n    ".join("{0}, {1}".format(_r(t), _r(v))
                                         for t, v in value)))
        else:
            self.func_params[name] = float(value)
            self.funcs.append("{0} = DEFI_CONSTANTE(VALE={1})".format(
                name, _r(value)))
        return name

    def temp_func(self, name, values_c):
        """DEFI_FONCTION of TEMP (Celsius), extended linearly."""
        self.funcs.append(
            "{0} = DEFI_FONCTION(NOM_PARA='TEMP', VALE=(\n    {1},\n), "
            "PROL_GAUCHE='LINEAIRE', PROL_DROITE='LINEAIRE')".format(
                name, ",\n    ".join("{0}, {1}".format(_r(t), _r(v))
                                     for t, v in values_c)))

    def add_charge(self, kw_entries):
        """One load: kw_entries = [(kw, {param: value or list}, group)].
        With a time table it all becomes AFFE_CHAR_THER_F with functions;
        a SOURCE with a function goes to the combined source load
        (add_func_source)."""
        timed = any(_is_timed(v) for _k, p, _g in kw_entries
                    for v in p.values())
        excit = OrderedDict()
        for kw, params, grp in kw_entries:
            if timed and kw == "SOURCE":
                self.add_func_source(grp, self.func(params["SOUR"]))
                continue
            parts = ["GROUP_MA='{0}'".format(grp)]
            for key, v in params.items():
                parts.append("{0}={1}".format(
                    key, self.func(v) if timed else _r(v)))
            excit.setdefault(kw, []).append("_F({0})".format(", ".join(parts)))
        if excit:
            self.charges.append(("AFFE_CHAR_THER_F" if timed else
                                 "AFFE_CHAR_THER", excit))

    def add_func_source(self, grp, name):
        """SOURCE with function 'name' on group grp (the elements are in
        self.group_cells). All function sources go together into one load
        (merged_sources): Code-Aster 17.4 computes two loads
        AFFE_CHAR_THER_F with SOURCE in one EXCIT list both with the
        function of the first load (measured: two halves with 2e6*t and a
        time table gave 2x the first, in reverse order 2x the
        second). One load with several SOURCE lines is correct, as are two
        function loads with FLUX_REP, ECHANGE or SOUR_NL and with
        AFFE_CHAR_MECA_F (FORCE_INTERNE, FORCE_FACE, PRES_REP) (measured with
        Code-Aster 17.4). The cause is in the compiled code: NOT
        verified. The place of the first function source in self.charges
        becomes a marker (None), so that the order of EXCIT is kept."""
        if not self.func_sources:
            self.charges.append(None)
        self.func_sources.append({"grp": grp, "sour": name,
                                  "eids": self.group_cells.get(grp)})

    def source_items(self):
        """The function sources as items for merged_sources: term (call
        in a FORMULE), ctx (arguments of that FORMULE), params."""
        items = []
        for s in self.func_sources:
            p = self.func_params.get(s["sour"], ["INST"])
            if isinstance(p, float):
                term, ctx, params = "({0})".format(_r(p)), OrderedDict(), []
            else:
                term = "{0}({1})".format(s["sour"], ", ".join(p))
                ctx = OrderedDict([(s["sour"], s["sour"])])
                params = list(p)
            items.append({"grp": s["grp"], "sour": s["sour"],
                          "eids": s["eids"], "term": term, "ctx": ctx,
                          "params": params})
        return items

    def merged_sources(self, items, owner=None, born=None, prefix="FQ"):
        """
        SOURCE lines for an AFFE_CHAR_THER_F with all function sources
        (items, see source_items; bridge_welding adds the welding sources).
        Within one load a later SOURCE line on the same element overrides
        the earlier one (measured with Code-Aster 17.4: the whole wall with
        f1 and then one half with f2 gave only f2 on that half). Therefore
        the mesh is
        split by the sources that lie on the element (and owner[eid],
        the filler material of a welding source); per part a FORMULE with
        the sum (FORMULEs and DEFI_FONCTIONs called as argument),
        with filler material only where it is already born: born(j) =
        (condition, {name: argument}). A source that overlaps nothing
        keeps its own group and function (the .comm with one source stays
        the same). Chosen over a FORMULE with indicator terms per group:
        that would have to derive the group from X, Y, Z, which is not
        unambiguous on the boundary between two groups.
        Returns ([FORMULE lines], [_F lines]) or None (ERROR reported).
        """
        owner = owner or {}
        member = OrderedDict()
        for i, it in enumerate(items):
            if it["eids"] is None:
                log(tr("ERROR: Warmtebron op groep '{0}': de elementen zijn "
                       "niet bekend, dus de bronnen kunnen niet in een last.",
                       "ERROR: Heat source on group '{0}': the elements "
                       "are not known, so the sources cannot be put in one "
                       "load.").format(it["grp"]))
                return None
            for e in it["eids"]:
                lst = member.setdefault(e, [])
                if i not in lst:
                    lst.append(i)
        parts = OrderedDict()
        for e, idx in member.items():
            parts.setdefault((tuple(idx), owner.get(e)), []).append(e)
        lines, entries = [], []
        try:
            for (idx, j), eids in parts.items():
                it = items[idx[0]]
                whole = len(idx) == 1 and j is None and \
                    len(eids) == len(set(it["eids"]))
                grp = it["grp"] if whole else self._list_group(
                    ["M{0}".format(e) for e in eids])
                if whole and it.get("sour"):
                    entries.append("_F(GROUP_MA='{0}', SOUR={1})".format(
                        grp, it["sour"]))
                    continue
                ctx = OrderedDict()
                params = []
                for i in idx:
                    ctx.update(items[i]["ctx"])
                    params += items[i]["params"]
                vale = " + ".join(items[i]["term"] for i in idx)
                if j is not None:
                    cond, cctx = born(j)
                    vale = "({0}) if {1} else 0.0".format(vale, cond)
                    ctx.update(cctx)
                    params += ["X", "Y", "Z", "INST"]
                params = [p for p in ("X", "Y", "Z", "INST")
                          if p in params] or ["INST"]
                self.counter += 1
                name = "{0}{1}".format(prefix, self.counter)
                lines.append(
                    "{0} = FORMULE(VALE='{1}',\n    NOM_PARA={2}{3})".format(
                        name, vale, _fmt_seq(["'{0}'".format(p)
                                              for p in params]),
                        "".join(",\n    {0}={1}".format(k, v)
                                for k, v in ctx.items())))
                entries.append("_F(GROUP_MA='{0}', SOUR={1})".format(
                    grp, name))
        except ValueError as e:
            log(tr("ERROR: Warmtebron: element {0} niet in het mesh "
                   "gevonden.",
                   "ERROR: Heat source: element {0} not found in the mesh.")
                .format(e))
            return None
        overlap = sum(1 for k in parts if len(k[0]) > 1)
        if len(items) > 1:
            log("INFO: {0} heat sources as functions in one load (Code-Aster "
                "17.4 computes multiple SOURCE function loads as the first); "
                "{1} part(s) of the mesh with the sum of overlapping "
                "sources.".format(len(items), overlap))
        return lines, entries

    # ---------- loads ----------
    def apply_loads(self):
        for load in self.th["loads"]:
            tag, sel, target = load["tag"], load["sel"], load["target"]
            label = tr("{0} op '{1}'", "{0} on '{1}'").format(tag, sel)
            if not self.transient:
                for key in ("value", "ambient", "coef", "emissivity"):
                    if key in load:
                        load[key] = self.steady(load[key], label)
            if tag == "temperature2":
                self.apply_temperature(load, label)
            elif tag in ("heatflow", "heatflux"):
                if target == "node" and tag == "heatflow":
                    self.apply_node_flow(load, label)
                elif target == "node":
                    self.skip(tr("{0} (heat flux alleen op vlakken)",
                                 "{0} (heat flux only on faces)").format(
                        label))
                elif target == "element":
                    if tag == "heatflux":
                        self.skip(tr("{0} (heat flux alleen op vlakken)",
                                     "{0} (heat flux only on faces)").format(
                            label))
                    else:
                        self.apply_source(load, label, per_volume=False)
                else:
                    self.apply_face_flux(load, label)
            elif tag == "heatgeneration":
                if target != "element":
                    self.skip(tr("{0} (alleen op elementen)",
                                 "{0} (only on elements)").format(label))
                else:
                    self.apply_source(load, label, per_volume=True)
            elif tag in ("convectionbc", "radiationbc"):
                if target != "face":
                    self.skip(tr("{0} (alleen op vlakken)",
                                 "{0} (only on faces)").format(label))
                else:
                    self.apply_exchange(load, label)
        self.apply_node_temperatures()

    # ---------- bonded contact ----------
    def bonded_loads(self):
        """
        Bonded contact (contact2 bondedtie/bondedce/bondedelastic,
        model_data["bonded"] from bridge_mesh._bonded) in a thermal
        analysis. Mecway: in thermal analysis the slave node gets the value
        at the projected point on the master face; 'elastic' is thermally
        a resistance layer with "Thermal conductance per unit area" (manual
        v33 sec. 9.9.1).
          - tie / constraint equations (and elastic where ECHANGE_PAROI is
            not possible): AFFE_CHAR_THER LIAISON_MAIL (catalog
            affe_char_ther.py v17.4: GROUP_MA_MAIT, GROUP_NO_ESCL,
            DISTANCE_MAX; no TYPE_RACCORD or DDL, only TEMP). Master: the
            parent elements (volumes) or the shell elements, as mechanical.
          - elastic: AFFE_CHAR_THER ECHANGE_PAROI (GROUP_MA_1/GROUP_MA_2,
            COEF_H = conductance per area; U4.44.02, test cases ttlp101a
            and tplv101c) between the boundary faces of both sides. Only
            volume faces that face each other node for node
            (_conforming_faces); otherwise tie + WARNING + skipped_loads.
          - Volumes and shells (PLAN) together in the model: then neither
            works (Code-Aster 17.4: LIAISON_MAIL <EXCEPTION> CHARGES7_6
            "mélange d'éléments 2D ... et 3D. Il n'est pas possible de
            réaliser une liaison", shell edge on a block; ECHANGE_PAROI
            <EXCEPTION> CHARGES6_2 "le modèle fourni doit être homogène en
            dimension", two blocks with a loose shell); ERROR +
            skipped_loads.
        Verification TH-04 (tests_thermisch.py).
        """
        mixed = len(set(i["cls"] for i in self.elsets.values())) > 1
        for b in self.md.get("bonded", []):
            sel_m, sel_s = b.get("selections", (b["master"], b["slave"]))
            label = tr("verlijmd contact '{0}' / '{1}'",
                       "bonded contact '{0}' / '{1}'").format(sel_m, sel_s)
            parts_m = self.face_parts(sel_m)
            parts_s = self.face_parts(sel_s)
            dropped = [sel for sel, parts in ((sel_m, parts_m),
                                              (sel_s, parts_s))
                       if not parts or any(p[0] == "inactive"
                                           for p in parts)]
            if dropped:
                self.skip(tr("{0}: vlakken van niet-gemodelleerde elementen "
                             "in {1} (balken, schalen buiten het PLAN-vlak "
                             "of elsets zonder thermisch materiaal)",
                             "{0}: faces of non-modelled elements in {1} "
                             "(beams, shells outside the PLAN plane or "
                             "elsets without thermal material)").format(
                                 label, ", ".join("'{0}'".format(s)
                                                  for s in dropped)))
                continue
            if mixed:
                self.skip(tr("{0}: Code-Aster kan thermisch geen verlijmd "
                             "contact (LIAISON_MAIL, ECHANGE_PAROI) leggen "
                             "in een model met volumes en schalen samen "
                             "(CHARGES7_6, CHARGES6_2); gebruik gedeelde "
                             "knopen (Merge nearby nodes)",
                             "{0}: Code-Aster cannot apply thermal bonded "
                             "contact (LIAISON_MAIL, ECHANGE_PAROI) in a "
                             "model with solids and shells together "
                             "(CHARGES7_6, CHARGES6_2); use shared nodes "
                             "(Merge nearby nodes)").format(label))
                continue
            why = None
            if b.get("type") == "bondedelastic":
                why = self._bonded_exchange(b, label, parts_m, parts_s)
                if why is None:
                    continue
            if why:
                self.md.setdefault("skipped_loads", []).append(tr(
                    "{0}: thermische weerstand (elastic) niet vertaald, "
                    "ideaal verlijmd", "{0}: thermal resistance (elastic) "
                    "not translated, ideally bonded").format(label))
                log(tr("WARNING: {0} is 'elastic' (weerstandslaag): {1}. "
                       "Vertaald als ideaal verlijmd (LIAISON_MAIL, geen "
                       "temperatuursprong over de naad).",
                       "WARNING: {0} is 'elastic' (resistive layer): {1}. "
                       "Translated as ideally bonded (LIAISON_MAIL, no "
                       "temperature jump across the bond).").format(
                           label, why))
            groups = self._bonded_groups(b, label)
            if groups is None:
                continue
            parts = ["GROUP_MA_MAIT='{0}'".format(groups[0]),
                     "GROUP_NO_ESCL='{0}'".format(groups[1])]
            if b.get("distance", 0.0) > 0.0:
                parts.append("DISTANCE_MAX={0}".format(_r(b["distance"])))
            self.charges.append(("AFFE_CHAR_THER", OrderedDict(
                [("LIAISON_MAIL", ["_F({0})".format(", ".join(parts))])])))
            log("INFO: {0} -> AFFE_CHAR_THER LIAISON_MAIL (TEMP of the "
                "slave nodes = TEMP on the master face).".format(label))

    def _bonded_groups(self, b, label):
        """(master element group, slave node group) in the thermal mesh.
        BRMAIT/BRESCL (bridge_mesh._bonded) only creates the mechanical
        DEFI_GROUP (bridge_to_aster._build_defigroup_block); here separate
        groups, so that the chain thermal -> mechanical (same mesh) does
        not create them twice."""
        master = b["master"]
        eids = self.md.get("extra_ma_groups", {}).get(master)
        if eids is not None:
            try:
                master = self._list_group(["M{0}".format(e) for e in eids])
            except ValueError as e:
                self.skip(tr("{0}: element {1} niet in het mesh gevonden",
                             "{0}: element {1} not found in the mesh")
                          .format(label, e))
                return None
        nids = self.md.get("extra_node_groups", {}).get(b["slave"])
        if not nids:
            self.skip(tr("{0}: geen slave-knopen",
                         "{0}: no slave nodes").format(label))
            return None
        slave = self.new_group("THN")
        self.crea_no.append("_F(NOM='{0}', NOEUD={1})".format(
            slave, _fmt_seq(["'N{0}'".format(n) for n in nids])))
        return master, slave

    def _bonded_exchange(self, b, label, parts_m, parts_s):
        """Elastic: ECHANGE_PAROI if possible (None), otherwise the reason
        (text; the caller reports it and makes it a tie)."""
        h = b.get("conductance")
        if not h or h <= 0.0:
            return tr("geen 'Thermal conductance per unit area' in de .liml",
                      "no 'Thermal conductance per unit area' in the .liml")
        if any(p[0] != "solid" for p in parts_m + parts_s):
            return tr("weerstandslaag alleen tussen volumevlakken",
                      "resistive layer only between solid faces")
        if not self._conforming_faces(parts_m, parts_s):
            return tr("de vlakken liggen niet knoop op knoop tegenover "
                      "elkaar (niet-conform mesh); ECHANGE_PAROI vraagt "
                      "gelijke vlakken aan beide kanten",
                      "the faces are not node-to-node opposite each other "
                      "(non-conforming mesh); ECHANGE_PAROI needs equal "
                      "faces on both sides")
        found_m = self.face_targets(b["selections"][0], label)
        found_s = self.face_targets(b["selections"][1], label)
        if found_m is None or found_s is None:
            return tr("vlakken niet gevonden", "faces not found")
        self.charges.append(("AFFE_CHAR_THER", OrderedDict([(
            "ECHANGE_PAROI", ["_F(GROUP_MA_1={0}, GROUP_MA_2={1}, "
                              "COEF_H={2})".format(
                                  _fmt_groups([t[1] for t in found_m[0]]),
                                  _fmt_groups([t[1] for t in found_s[0]]),
                                  _r(h))])])))
        log("INFO: {0} -> AFFE_CHAR_THER ECHANGE_PAROI COEF_H = {1} "
            "W/m2/K (resistance layer).".format(label, _r(h)))
        return None

    def _conforming_faces(self, parts_m, parts_s):
        """True if every slave face has the same nodes (coordinates)
        as a master face and vice versa."""
        size = 0.0
        if self.nodes:
            for c in range(3):
                vals = [p[c] for p in self.nodes.values()]
                size = max(size, max(vals) - min(vals))
        tol = 1.0e-6 * max(size, 1.0e-3)

        def key(nodes):
            return frozenset(tuple(int(round(self.nodes[n][c] / tol))
                                   for c in range(3)) for n in nodes)
        km = [key(p[2]) for p in parts_m]
        ks = [key(p[2]) for p in parts_s]
        return len(km) == len(ks) and set(km) == set(ks)

    def apply_temperature(self, load, label):
        start, end = load["interval"]
        if self.transient and (start != 0.0 or end != 0.0):
            self.skip(tr("{0}: tijdsinterval {1}..{2} s (de temperatuur "
                         "wordt de hele analyse opgelegd)",
                         "{0}: time interval {1}..{2} s (the temperature is "
                         "imposed for the whole analysis)").format(
                             label, start, end))
        tgt = self.node_target(load["sel"], load["target"], load["tag"])
        if tgt is None:
            return
        v = load["value"]
        if isinstance(v, Formula):
            self.temp_timed.append("_F({0}='{1}', TEMP={2})".format(
                tgt[0], tgt[1], self.formula(v.shifted(-KELVIN))))
        elif isinstance(v, list):
            fn = self.func([(t, x - KELVIN) for t, x in v])
            self.temp_timed.append("_F({0}='{1}', TEMP={2})".format(
                tgt[0], tgt[1], fn))
        else:
            self.temp_const.append("_F({0}='{1}', TEMP={2})".format(
                tgt[0], tgt[1], _r(v - KELVIN)))

    def apply_node_temperatures(self):
        by_value = OrderedDict()
        dropped = 0
        for nid, v in self.th["node_temps"]:
            if nid in self.modelled:
                by_value.setdefault(v, []).append(nid)
            else:
                dropped += 1
        if dropped:
            self.skip(tr("nodetemperature op {0} knopen zonder gemodelleerd "
                         "element",
                         "nodetemperature on {0} nodes without a modelled "
                         "element").format(dropped))
        for v, nids in by_value.items():
            grp = self.new_group("THN")
            self.crea_no.append("_F(NOM='{0}', NOEUD={1})".format(
                grp, _fmt_seq(["'N{0}'".format(n) for n in nids])))
            self.temp_const.append("_F(GROUP_NO='{0}', TEMP={1})".format(
                grp, _r(v - KELVIN)))

    def apply_face_flux(self, load, label):
        found = self.face_targets(load["sel"], label)
        if found is None:
            self.skip(tr("{0}: geen vlakken van gemodelleerde elementen",
                         "{0}: no faces of modelled elements").format(
                label))
            return
        targets, area = found
        q = load["value"]
        if (load["tag"] == "heatflow" and isinstance(q, Formula) and
                q.positional()):
            self.skip(tr("{0}: formule in x, y, z voor een totale "
                         "warmtestroom (gebruik heat flux of internal heat "
                         "generation)",
                         "{0}: formula in x, y, z for a total heat flow "
                         "(use heat flux or internal heat generation)")
                      .format(label))
            return
        if load["tag"] == "heatflow":
            # Total over all faces, uniform per area (manual
            # v33 sec. 9.27); shell edges: length x thickness.
            q = _scale(q, 1.0 / area)
            log("INFO: {0}: total area {1} m2.".format(label, area))
            if self.inactive_faces.get(load["sel"]):
                self.skip(tr("{0}: deel op vlakken van balken; het totaal "
                             "is over de overige vlakken verdeeld",
                             "{0}: part on faces of beams; the total is "
                             "distributed over the other faces").format(
                                 label))
        entries = []
        for kind, grp, f, t in targets:
            if kind == "solid":
                entries.append(("FLUX_REP", {"FLUN": q}, grp))
            elif kind == "shelledge":
                entries.append(("FLUX_REP", {"FLUN": _scale(q, f)}, grp))
            else:   # shell face: source q/t per volume (times f)
                entries.append(("SOURCE", {"SOUR": _scale(q, f / t)}, grp))
        self.add_charge(entries)

    def apply_node_flow(self, load, label):
        """heatflow on nodes: Mecway distributes the heat flow equally over
        the nodes (manual v33 sec. 9.27, "divided equally between each
        node"). AFFE_CHAR_THER has no point source and THER_LINEAIRE/
        THER_NON_LINE no EXCIT with a vector (catalogs
        affe_char_ther.py, ther_lineaire.py, ther_non_line.py), but SOURCE
        SOUR_CALCULEE with a nodal field s (W/m3) works. That gives nodal
        loads M s with M = int(N_i N_j dV) (MASS_THER with RHO_CP = 1); with
        s = M^-1 F (RESOUDRE) the nodal loads are exactly F (see
        node_flow_block)."""
        if isinstance(load["value"], Formula) and load["value"].positional():
            self.skip(tr("{0}: formule in x, y, z op knopen",
                         "{0}: formula in x, y, z on nodes").format(label))
            return
        nodes = self.selection_nodes(load["sel"], "node")
        tgt = self.node_target(load["sel"], "node", load["tag"])
        if tgt is None or not nodes:
            return
        keep = len(nodes & self.modelled)
        if keep < len(nodes):
            self.skip(tr("{0}: {1} van {2} knopen zonder gemodelleerd "
                         "element; hun deel van de warmtestroom vervalt",
                         "{0}: {1} of {2} nodes without a modelled element; "
                         "their share of the heat flow is dropped").format(
                             label, len(nodes) - keep, len(nodes)))
        # Per node; with shells as PLAN in model units (depth t_ref).
        self.node_flows.append((tgt[1], _scale(
            load["value"], 1.0 / (len(nodes) * self.t_ref))))
        log("INFO: {0}: heat flow split equally over {1} nodes.".format(
            label, len(nodes)))

    def node_flow_block(self):
        """(.comm block, [EXCIT entries]) for heatflow on nodes: per load
        the nodal loads F (NOEU_TEMP_R), a source field s = M^-1 F
        (CALC_MATR_ELEM MASS_THER with RHO_CP = 1, RESOUDRE) and a load
        SOURCE SOUR_CALCULEE = s; with a time table s for 1 W per node
        and FONC_MULT = the table."""
        if not self.node_flows:
            return "", []
        lines = [
            "# heatflow on nodes: source s = M^-1 F (bridge_thermal."
            "apply_node_flow)",
            "MTHUNIT = DEFI_MATERIAU(THER=_F(LAMBDA=1.0, RHO_CP=1.0))",
            "fm_unit = AFFE_MATERIAU(MAILLAGE=mesh, MODELE=model, "
            "AFFE=_F(TOUT='OUI', MATER=MTHUNIT))",
            "me_unit = CALC_MATR_ELEM(OPTION='MASS_THER', MODELE=model, "
            "CHAM_MATER=fm_unit)",
            "nu_unit = NUME_DDL(MATR_RIGI=me_unit)",
            "ma_unit = ASSE_MATRICE(MATR_ELEM=me_unit, NUME_DDL=nu_unit)",
            "ma_unit = FACTORISER(reuse=ma_unit, MATR_ASSE=ma_unit, "
            "METHODE='MUMPS')",
        ]
        excit = []
        for k, (grp, value) in enumerate(self.node_flows):
            timed = _is_timed(value)
            lines += [
                "qn_{0} = CREA_CHAMP(TYPE_CHAM='NOEU_TEMP_R', "
                "OPERATION='AFFE', MODELE=model, NUME_DDL=nu_unit, "
                "AFFE=(_F(TOUT='OUI', "
                "NOM_CMP='TEMP', VALE=0.0), _F(GROUP_NO='{1}', "
                "NOM_CMP='TEMP', VALE={2})))".format(
                    k + 1, grp, "1.0" if timed else _r(value)),
                "tn_{0} = RESOUDRE(MATR=ma_unit, CHAM_NO=qn_{0})".format(k + 1),
                # SOUR_CALCULEE wants grandeur SOUR_R (CALCUL_5 with TEMP_R)
                "sn_{0} = CREA_CHAMP(TYPE_CHAM='NOEU_SOUR_R', "
                "OPERATION='ASSE', MODELE=model, ASSE=_F(TOUT='OUI', "
                "CHAM_GD=tn_{0}, NOM_CMP='TEMP', NOM_CMP_RESU='SOUR'))"
                .format(k + 1),
                "loadqn_{0} = AFFE_CHAR_THER(MODELE=model, SOURCE=_F("
                "SOUR_CALCULEE=sn_{0}))".format(k + 1)]
            if timed:
                excit.append("_F(CHARGE=loadqn_{0}, FONC_MULT={1})".format(
                    k + 1, self.func(value)))
            else:
                excit.append("_F(CHARGE=loadqn_{0})".format(k + 1))
        return "\n".join(lines) + "\n", excit

    def apply_source(self, load, label, per_volume):
        found = self.element_targets(load["sel"], label)
        if found is None:
            self.skip(tr("{0}: geen gemodelleerde elementen",
                         "{0}: no modelled elements").format(label))
            return
        targets, vol = found
        s = load["value"]
        if not per_volume and isinstance(s, Formula) and s.positional():
            self.skip(tr("{0}: formule in x, y, z voor een totale "
                         "warmtestroom (gebruik internal heat generation)",
                         "{0}: formula in x, y, z for a total heat flow "
                         "(use internal heat generation)").format(label))
            return
        if not per_volume:
            s = _scale(s, 1.0 / vol)
            log("INFO: {0}: total volume {1} m3.".format(label, vol))
        entries = []
        for _kind, grp, f, _t in targets:
            entries.append(("SOURCE", {"SOUR": _scale(s, f)}, grp))
        self.add_charge(entries)

    def apply_exchange(self, load, label):
        found = self.face_targets(load["sel"], label)
        if found is None:
            self.skip(tr("{0}: geen vlakken van gemodelleerde elementen",
                         "{0}: no faces of modelled elements").format(
                label))
            return
        targets, _area = found
        conv = load["tag"] == "convectionbc"
        amb = _shift(load["ambient"], -KELVIN)
        entries = []
        for kind, grp, f, t in targets:
            if kind == "shellface":
                self.shell_face_exchange(load, label, grp, f, t, amb, conv)
                continue
            if conv:
                entries.append(("ECHANGE", OrderedDict([
                    ("COEF_H", _scale(load["coef"], f)),
                    ("TEMP_EXT", amb)]), grp))
            else:
                self.nonlinear = True
                entries.append(("RAYONNEMENT", OrderedDict([
                    ("SIGMA", STEFAN_BOLTZMANN * f),
                    ("EPSILON", load["emissivity"]),
                    ("TEMP_EXT", amb)]), grp))
        if entries:
            self.has_exchange = True
            self.add_charge(entries)

    def shell_face_exchange(self, load, label, grp, f, t, amb, conv):
        """Convection/radiation on a shell face (PLAN): source f/t * q(T)
        (SOUR_NL, function of TEMP; U4.44.02 SOUR_NL)."""
        vals = [load.get("coef"), load.get("emissivity"), amb]
        if any(isinstance(v, Formula) for v in vals):
            self.skip(tr("{0}: formule voor convectie/straling op een "
                         "schaalvlak (alleen getallen en tijdstabellen)",
                         "{0}: formula for convection/radiation on a shell "
                         "face (only numbers and time tables)").format(label))
            return
        self.nonlinear = True
        k = f / t
        if any(isinstance(v, list) for v in vals):
            self.shell_face_exchange_timed(grp, k, amb, load, conv)
            return
        self.counter += 1
        name = "FS{0}".format(self.counter)
        if conv:
            h = load["coef"] * k
            pts = [(amb - 1000.0, h * 1000.0), (amb + 1000.0, -h * 1000.0)]
        else:
            c = STEFAN_BOLTZMANN * load["emissivity"] * k
            ta4 = (amb + KELVIN) ** 4
            top = max(3000.0, amb + 1000.0)
            pts = []
            temp = -KELVIN
            while temp <= top:
                pts.append((temp, c * (ta4 - (temp + KELVIN) ** 4)))
                temp += 5.0
        self.temp_func(name, pts)
        self.has_exchange = True
        self.charges.append(("AFFE_CHAR_THER_F", OrderedDict([
            ("SOUR_NL", ["_F(GROUP_MA='{0}', SOUR={1})".format(grp, name)])])))

    def shell_face_exchange_timed(self, grp, k, amb, load, conv):
        """Same with a time table (h, T_amb or emissivity). SOUR_NL
        gives the function only TEMP (a FORMULE of TEMP and INST gave in
        THER_NON_LINE "NameError: name 'INST' is not defined", Code-Aster
        17.4), so split into a source and a sink:
          convection: k*h*(Ta - T) = k*h(t)*Ta(t)  (SOURCE, FORMULE of INST)
                                   - k*h(t)*T      (SOUR_NL of TEMP)
          radiation:  k*sigma*eps(t)*((Ta(t)+273.15)^4 - (T+273.15)^4) idem.
        A table for h or eps goes into the sink as EXCIT FONC_MULT (the
        SOUR_NL function then with coefficient 1). Tables: DEFI_FONCTION of
        INST, PROL CONSTANT (as Mecway, manual v33 sec. 9)."""
        coef = load["coef"] if conv else load["emissivity"]
        args = OrderedDict()
        names = {}

        def term(key, value):
            if isinstance(value, list):
                names[key] = self.func(value)
                args[names[key]] = names[key]
                return "{0}(INST)".format(names[key])
            return "({0})".format(_r(value))
        c = k if conv else STEFAN_BOLTZMANN * k
        if conv:
            expr = "{0}*{1}*{2}".format(_r(c), term("c", coef),
                                        term("a", amb))
        else:
            expr = "{0}*{1}*({2}+{3})**4".format(
                _r(c), term("c", coef), term("a", amb), _r(KELVIN))
        self.counter += 1
        src = "FS{0}".format(self.counter)
        self.func_params[src] = ["INST"]
        self.funcs.append("{0} = FORMULE(VALE='{1}', NOM_PARA='INST'{2})"
                          .format(src, expr, "".join(
                              ", {0}={1}".format(a, b)
                              for a, b in args.items())))
        # Sink: -c*coef*T (convection) or -c*coef*(T+273.15)^4 (radiation)
        timed_coef = isinstance(coef, list)
        c0 = c * (1.0 if timed_coef else coef)
        self.counter += 1
        sink = "FS{0}".format(self.counter)
        if conv:
            pts = [(-1000.0, c0 * 1000.0), (1000.0, -c0 * 1000.0)]
        else:
            ambs = [v for _t, v in amb] if isinstance(amb, list) else [amb]
            top = max(3000.0, max(ambs) + 1000.0)
            pts = []
            temp = -KELVIN
            while temp <= top:
                pts.append((temp, -c0 * (temp + KELVIN) ** 4))
                temp += 5.0
        self.temp_func(sink, pts)
        self.has_exchange = True
        self.add_func_source(grp, src)
        self.charges.append(("AFFE_CHAR_THER_F", OrderedDict([
            ("SOUR_NL", ["_F(GROUP_MA='{0}', SOUR={1})".format(grp, sink)])]),
            names.get("c")))

    # ---------- blocks ----------
    def defigroup_block(self):
        out = []
        if self.rotation:
            _q, k, ang = self.rotation
            # Alarm MODELE1_53 ("Le maillage est 3D ...") remains: Code-Aster
            # determines the dimension of the mesh at LIRE_MAILLAGE; after
            # the rotation the shells do lie in a plane Z = constant
            # (results equal to Mecway, see _shell_rotation).
            out.append("# Shells to a plane Z = constant (PLAN), see "
                       "bridge_thermal._shell_rotation\nmesh = MODI_MAILLAGE("
                       "\n    reuse=mesh,\n    MAILLAGE=mesh,\n    ROTATION="
                       "_F(POIN_1=(0.0, 0.0, 0.0), DIR=({0}, {1}, {2}), "
                       "ANGLE={3}),\n)\n".format(_r(k[0]), _r(k[1]),
                                                 _r(k[2]), _r(ang)))
        if self.crea_ma or self.crea_no:
            parts = []
            if self.crea_ma:
                parts.append("    CREA_GROUP_MA=(\n        {0},\n    ),".format(
                    ",\n        ".join(self.crea_ma)))
            if self.crea_no:
                parts.append("    CREA_GROUP_NO=(\n        {0},\n    ),".format(
                    ",\n        ".join(self.crea_no)))
            out.append("mesh = DEFI_GROUP(\n    reuse=mesh,\n    MAILLAGE=mesh,"
                       "\n{0}\n)\n".format("\n".join(parts)))
        if self.crea_ma2:
            out.append("mesh = DEFI_GROUP(\n    reuse=mesh,\n    MAILLAGE=mesh,"
                       "\n    CREA_GROUP_MA=(\n        {0},\n    ),\n)\n".format(
                           ",\n        ".join(self.crea_ma2)))
        if self.skin3d:
            # Faces of volumes with the normal pointing outward (MODI_MAILLAGE
            # ORIE_PEAU, as in the mechanical builders).
            out.append("mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE="
                       "mesh,\n    ORIE_PEAU=_F(GROUP_MA_PEAU={0}),\n)\n".format(
                           _fmt_groups(self.skin3d)))
        return "\n".join(out) if out else "#-- no extra groups --\n"

    def model_block(self):
        solids = [g for g, i in self.elsets.items() if i["cls"] == "solid"]
        shells = [g for g, i in self.elsets.items() if i["cls"] == "shell"]
        affe = []
        for groups, mod in ((solids, "3D"), (shells + self.edges, "PLAN"),
                            (self.skin3d, "3D")):
            if groups:
                affe.append("_F(GROUP_MA={0}, PHENOMENE='THERMIQUE', "
                            "MODELISATION='{1}')".format(_fmt_groups(groups),
                                                         mod))
        if self.birth:
            # Filler material (bridge_welding): diagonal heat capacity
            # (3D_DIAG, test case ttnp201a), after the volumes (the last
            # assignment counts). With the consistent capacity a node at rest
            # followed the temperature rate of its hot neighbours via the mass
            # coupling (WE-13: +138 K before birth, with a dip below it during
            # heating); not with the diagonal one.
            affe.append("_F(GROUP_MA='{0}', PHENOMENE='THERMIQUE', "
                        "MODELISATION='3D_DIAG')".format(self.birth["all"]))
        return ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n    AFFE=(\n"
                "        {0},\n    ),\n)\n").format(",\n        ".join(affe))

    def materials_blocks(self):
        """(DEFI_MATERIAU block, AFFE_MATERIAU block). With shells f != 1
        also 'fieldmat_post' without factor: CALC_CHAMP computes the heat
        flux with it (-lambda grad T with the real lambda; CALC_CHAMP
        CHAM_MATER, catalog calc_champ.py)."""
        lines = []
        fieldmat = self._fieldmat("fieldmat", "MTH", True, lines)
        if self.scaled():
            fieldmat += self._fieldmat("fieldmat_post", "MTP", False, lines)
        return "\n".join(lines) + "\n", fieldmat

    def scaled(self):
        return any(abs(i["f"] - 1.0) > 1.0e-12 for i in self.elsets.values())

    def _fieldmat(self, concept, prefix, with_f, lines):
        # Local, as in build_thermal (bridge_to_aster imports this
        # module).
        import bridge_to_aster as bta
        mats = self.th["materials"]
        names = OrderedDict()
        affe = []
        for elset, info in self.elsets.items():
            f = info["f"] if with_f else 1.0
            key = (info["mat"], f)
            if key not in names:
                names[key] = "{0}{1}".format(prefix, len(names) + 1)
                p = mats[info["mat"]]
                lam = p["lambda"] * f
                rcp = p["rho"] * p["cp"] * f
                if "lambda_T" in p or "cp_T" in p:
                    # Temperature-dependent (Mecway TempDependent, manual
                    # v33 sec. 8.6: linearly interpolated, outside the table
                    # the nearest point -> PROL CONSTANT). THER_NL
                    # with RHO_CP as a function of TEMP: Code-Aster derives
                    # the enthalpy BETA from it (U4.43.01 THER_NL; R5.02.02).
                    lines.append(self._tempdep_funcs(
                        names[key], p, f, lam, rcp))
                    body = ("THER_NL=_F(LAMBDA={0}_L, RHO_CP={0}_C)"
                            .format(names[key]))
                elif self.nonlinear:
                    body = ("THER_NL=_F(LAMBDA=DEFI_CONSTANTE(VALE={0}), "
                            "RHO_CP=DEFI_CONSTANTE(VALE={1}))").format(
                                _r(lam), _r(rcp))
                else:
                    body = "THER=_F(LAMBDA={0}, RHO_CP={1})".format(
                        _r(lam), _r(rcp))
                if with_f:
                    # META_ACIER / DURT_META (bridge_metallurgy.apply)
                    body += getattr(self, "meta_kw", {}).get(info["mat"], "")
                # Name filtered as in the mechanical builders (only
                # ASCII, no line break; bridge_to_aster._mat_comment).
                lines.append("{0}{1}\n{2} = DEFI_MATERIAU({3})".format(
                    bta._mat_comment(info["mat"]).rstrip("\n"),
                    "" if f == 1.0 else " (schaal, f = {0})".format(_r(f)),
                    names[key], body))
            affe.append("_F(GROUP_MA='{0}', MATER={1})".format(
                elset, names[key]))
        varc = ""
        if self.birth and with_f:
            # Filler material that is born (#ASTER-LASBRON geboorte=,
            # bridge_welding): own material on the elements, after the elsets
            # (the last assignment counts, U4.43.03 AFFE_MATERIAU).
            import bridge_welding
            b_lines, b_affe, varc = bridge_welding.birth_materials(self, names)
            lines += b_lines
            affe += b_affe
        if with_f:
            self.fieldmat_affe = list(affe)
        return ("{0} = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n    MODELE=model,\n"
                "    AFFE=(\n        {1},\n    ),\n{2})\n").format(
                    concept, ",\n        ".join(affe), varc)

    @staticmethod
    def _tempdep_funcs(name, p, f, lam, rcp, f_lambda=None):
        """DEFI_FONCTION of TEMP (Celsius) for LAMBDA ({name}_L) and
        RHO_CP ({name}_C); without a table a constant function. f_lambda:
        own factor for lambda (else f; filler material, bridge_welding
        .birth_materials)."""
        def func(concept, table, scale, const):
            if not table:
                return "{0} = DEFI_CONSTANTE(VALE={1})".format(concept,
                                                             _r(const))
            # Extend the table explicitly (constant) to 0 K and to 10 000 K
            # above the last point, and refine RHO_CP (_refine_table).
            # Measured (Code-Aster 17.4, verification WE-04b, bar with cp
            # 450..750 J/kg/K at 300/800/1300 K, start at 293.15 K): with the
            # Mecway table itself 13% of the input energy was missing after
            # the first step (2.8% after 2 s); extended 10%; extended and
            # refined 0.01%. THER_NON_LINE derives the enthalpy BETA from
            # the table points of RHO_CP (see _refine_table); outside the
            # range the extension of RHO_CP did not fully count.
            table = [(-KELVIN, table[0][1])] + \
                [r for r in table if r[0] > -KELVIN] + \
                [(table[-1][0] + 1.0e4, table[-1][1])]
            if concept.endswith("_C"):
                table = _refine_table(table, _CP_TABLE_STEP)
            return ("{0} = DEFI_FONCTION(NOM_PARA='TEMP', VALE=(\n    {1},\n"
                    "), PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')"
                    .format(concept, ",\n    ".join(
                        "{0}, {1}".format(_r(t), _r(v * scale))
                        for t, v in table)))
        return "\n".join([
            func(name + "_L", p.get("lambda_T"),
                 f if f_lambda is None else f_lambda, lam),
            func(name + "_C", p.get("cp_T"), p["rho"] * f, rcp)])

    def check_capacity(self):
        """Transient: every elset needs rho*cp > 0."""
        bad = [g for g, i in self.elsets.items()
               if self.th["materials"][i["mat"]]["rho"] *
               self.th["materials"][i["mat"]]["cp"] <= 0.0]
        if bad and self.transient:
            log(tr("ERROR: Transient thermisch: dichtheid en soortelijke "
                   "warmte ontbreken voor elset(s) {0}.",
                   "ERROR: Transient thermal: density and specific heat are "
                   "missing for elset(s) {0}.").format(", ".join(bad)))
            return False
        return True

    def loads_block(self, extra_excit):
        charges = list(self.charges)
        if self.temp_const:
            charges.insert(0, ("AFFE_CHAR_THER", OrderedDict(
                [("TEMP_IMPO", self.temp_const)])))
        if self.temp_timed:
            charges.insert(1 if self.temp_const else 0, (
                "AFFE_CHAR_THER_F", OrderedDict(
                    [("TEMP_IMPO", self.temp_timed)])))
        if None in charges:
            # The marker of add_func_source: all function sources in one
            # load, or nothing if bridge_welding put them in 'lasbron'
            pos = charges.index(None)
            if self.sources_taken:
                del charges[pos]
            else:
                merged = self.merged_sources(self.source_items())
                if merged is None:
                    return None, None
                self.funcs += merged[0]
                charges[pos] = ("AFFE_CHAR_THER_F", OrderedDict(
                    [("SOURCE", merged[1])]))
        blocks = []
        excit = []
        for k, charge in enumerate(charges):
            # (command, kws) or (command, kws, FONC_MULT)
            command, kws = charge[0], charge[1]
            mult = charge[2] if len(charge) > 2 else None
            name = "load_{0}".format(k + 1)
            body = "".join("    {0}=(\n        {1},\n    ),\n".format(
                kw, ",\n        ".join(entries)) for kw, entries in kws.items())
            blocks.append("{0} = {1}(\n    MODELE=model,\n{2})\n".format(
                name, command, body))
            excit.append("_F(CHARGE={0}{1})".format(
                name, ", FONC_MULT={0}".format(mult) if mult else ""))
        flow_block, flow_excit = self.node_flow_block()
        if flow_block:
            blocks.append(flow_block)
            excit += flow_excit
        excit += ["_F(CHARGE={0})".format(n) for n in extra_excit]
        return "\n".join(blocks), excit

    def initial_block(self):
        """CREA_CHAMP with the initial temperature (Celsius) for ETAT_INIT."""
        affe = ["_F(TOUT='OUI', NOM_CMP='TEMP', VALE={0})".format(
            _r(MECWAY_DEFAULT_T0 - KELVIN))]
        if not self.th["initial"]:
            log(tr("WARNING: Transient zonder begintemperatuur: Mecway "
                   "begint dan op 0 K (manual v33 par. 6.7.2); de bridge ook.",
                   "WARNING: Transient without initial temperature: Mecway "
                   "then starts at 0 K (manual v33 sec. 6.7.2); so does the "
                   "bridge."))
        for sel, kind, v in self.th["initial"]:
            tgt = self.node_target(sel, kind, tr("begintemperatuur",
                                                 "initial temperature"))
            if tgt is not None:
                affe.append("_F({0}='{1}', NOM_CMP='TEMP', VALE={2})".format(
                    tgt[0], tgt[1], _r(v - KELVIN)))
        return ("temp0 = CREA_CHAMP(\n    TYPE_CHAM='NOEU_TEMP_R',\n"
                "    OPERATION='AFFE',\n    MODELE=model,\n    AFFE=(\n"
                "        {0},\n    ),\n)\n").format(",\n        ".join(affe))

    def listinst_block(self):
        if not self.transient:
            return "times = DEFI_LIST_REEL(VALE=(0.0,))\n", None
        ts = self.th["timesteps"]
        period, step = ts.get("period", 0.0), ts.get("step", 0.0)
        if period <= 0.0 or step <= 0.0:
            log(tr("ERROR: Transient thermisch zonder <timesteps> "
                   "(timeperiod en stepsize).",
                   "ERROR: Transient thermal analysis without <timesteps> "
                   "(timeperiod and stepsize)."))
            return None, None
        n = max(1, int(round(period / step)))
        if abs(n * step - period) > 1.0e-6 * period:
            log(tr("WARNING: Tijdsduur {0} s is geen veelvoud van de stap "
                   "{1} s; {2} gelijke stappen.",
                   "WARNING: Duration {0} s is not a multiple of the step "
                   "{1} s; {2} equal steps.").format(period, step, n))
        log("INFO: Transient thermal: {0} steps up to {1} s.".format(
            n, period))
        # Explicit times (k * period / n, 15 digits): INTERVALLE/NOMBRE
        # adds up the step and gave times like 39.9999999999999 s in Mecway.
        vals = [_r(period * k / float(n)) for k in range(n + 1)]
        return ("times = DEFI_LIST_REEL(VALE=(\n    {0},\n))\n".format(
            ",\n    ".join(", ".join(vals[i:i + 8])
                           for i in range(0, len(vals), 8)))), n

    def calc_champ_block(self):
        """
        Heat flux (-lambda grad T) in a separate result res_flux
        (aster_results_export reads 'heat_flux' from it). With scaled
        shells (f != 1) CALC_CHAMP computes with fieldmat_post (real
        lambda). Two steps, seen with Code-Aster 17.4:
          - CALC_CHAMP reuse=res with a different CHAM_MATER is forbidden
            (CALCULEL_33);
          - asking for FLUX_ELGA, FLUX_ELNO and FLUX_NOEU in one call in a
            new result gave FLUX_NOEU on shell nodes f x the flux
            (FLUX_ELNO came from the FLUX_ELGA of res, which THER_NON_LINE
            stores with the scaled lambda); first FLUX_ELGA, then in a
            second call FLUX_ELNO/FLUX_NOEU gave 3591.65 W/m2 everywhere
            (ConductionConvectionRadiation).
        Alarm RESULT1_39 (different material than in the result) is then
        intended.
        """
        groups = _fmt_groups(list(self.elsets))
        return ("res_flux = CALC_CHAMP(\n    RESULTAT=res,\n{0}"
                "    GROUP_MA={1},\n    THERMIQUE=('FLUX_ELGA',),\n)\n"
                "res_flux = CALC_CHAMP(\n    reuse=res_flux,\n"
                "    RESULTAT=res_flux,\n    GROUP_MA={1},\n"
                "    THERMIQUE=('FLUX_ELNO', 'FLUX_NOEU'),\n)\n").format(
                    "    CHAM_MATER=fieldmat_post,\n" if self.scaled() else "",
                    groups) + self.flux_rotation_block()

    def flux_rotation_block(self):
        """Rotated mesh (_shell_rotation): FLUX_NOEU per time step back to
        the global axes, v_glob = Q^T v (CREA_CHAMP ASSE with COEF_R per
        component, Result.setField; same NUME_ORDRE as res, which
        aster_results_export uses). PLAN nodes have no FLUZ
        (MODI_REPERE VECT_3D refuses that: ALGORITH2_12, Code-Aster 17.4);
        FLUZ only counts if there are volume elements."""
        if not self.rotation:
            return ""
        q = self.rotation[0]
        cmps = ("FLUX", "FLUY", "FLUZ")
        has_solid = any(i["cls"] == "solid" for i in self.elsets.values())
        terms = []
        for i in range(3):
            for j in range(3 if has_solid else 2):
                if abs(q[j][i]) > 1.0e-14:
                    terms.append("_F(TOUT='OUI', CHAM_GD=fl_r, NOM_CMP='{0}', "
                                 "NOM_CMP_RESU='{1}', COEF_R={2}, "
                                 "CUMUL='OUI')".format(cmps[j], cmps[i],
                                                       _r(q[j][i])))
        return ("# Heat flux back to the global axes (mesh rotated, "
                "see defigroup)\n"
                "fl_zero = CREA_CHAMP(TYPE_CHAM='NOEU_FLUX_R', "
                "OPERATION='AFFE', MODELE=model, AFFE=_F(TOUT='OUI', "
                "NOM_CMP=('FLUX', 'FLUY', 'FLUZ'), VALE=(0.0, 0.0, 0.0)))\n"
                "for nume_r in res_flux.getAccessParameters()['NUME_ORDRE']:\n"
                "    fl_r = CREA_CHAMP(TYPE_CHAM='NOEU_FLUX_R', "
                "OPERATION='EXTR', RESULTAT=res_flux, NOM_CHAM='FLUX_NOEU', "
                "NUME_ORDRE=nume_r)\n"
                "    fl_g = CREA_CHAMP(TYPE_CHAM='NOEU_FLUX_R', "
                "OPERATION='ASSE', MODELE=model, ASSE=(\n"
                "        _F(TOUT='OUI', CHAM_GD=fl_zero),\n"
                "        {0},\n    ))\n"
                "    res_flux.setField(fl_g, 'FLUX_NOEU', nume_r)\n"
                "# Mesh back to its original position (aster_results_export "
                "compares the node coordinates with the .liml)\n"
                "mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE=mesh,\n"
                "    ROTATION=_F(POIN_1=(0.0, 0.0, 0.0), DIR=({1}, {2}, {3}), "
                "ANGLE={4}),\n)\n").format(
                    ",\n        ".join(terms), _r(self.rotation[1][0]),
                    _r(self.rotation[1][1]), _r(self.rotation[1][2]),
                    _r(-self.rotation[2]))


def _read_mesh_segments(path):
    """({name: frozenset(node ids)} of the SEG2/SEG3 elements,
    {group: [element names]}) from a mesh in ASTER format
    (bridge_mesh.write_mesh: blocks 'SEG2' / 'GROUP_MA' to 'FINSF',
    nodes 'N<id>')."""
    segs = {}
    groups = {}
    block = None
    group = None
    f = open(path)
    try:
        for line in f:
            words = line.split()
            if not words:
                continue
            if block is None:
                if words[0] in ("SEG2", "SEG3", "GROUP_MA"):
                    block = words[0]
                    group = None
                continue
            if words[0] == "FINSF":
                block = None
                continue
            if block == "GROUP_MA":
                if group is None:
                    group = words[0]
                    groups[group] = words[1:]
                else:
                    groups[group].extend(words)
            else:
                segs[words[0]] = frozenset(int(w[1:]) for w in words[1:])
    finally:
        f.close()
    return segs, groups


def _interpolate(table, time):
    """Value of a time table [(t, v)] at time time: linear
    between the points, constant outside them (manual v33 sec. 9:
    "constant extrapolation")."""
    if time <= table[0][0]:
        return table[0][1]
    for (t0, v0), (t1, v1) in zip(table, table[1:]):
        if time <= t1:
            if t1 <= t0:
                return v1
            return v0 + (v1 - v0) * (time - t0) / (t1 - t0)
    return table[-1][1]


# Step (degrees) by which a RHO_CP table is refined (_refine_table).
_CP_TABLE_STEP = 10.0


def _refine_table(table, step):
    """Table [(T, v)] with extra points (linearly interpolated) so that
    the distance between two points with different values is <= step.

    Measured (Code-Aster 17.4, verification WE-04b): THER_NON_LINE computes
    with the enthalpy BETA from RHO_CP, but interpolates BETA linearly
    between the table points of RHO_CP; between two points the mean
    rho*cp of that interval then applies (energy balance -2.8% with cp
    450..750 J/kg/K at 300/800/1300 K). With points every 10 degrees BETA
    is nearly exact. An interval with equal values stays one interval."""
    out = [table[0]]
    for (t0, v0), (t1, v1) in zip(table, table[1:]):
        n = 1
        if v1 != v0:
            n = max(1, min(500, int(math.ceil((t1 - t0) / step))))
        for k in range(1, n + 1):
            out.append((t0 + (t1 - t0) * k / float(n),
                        v0 + (v1 - v0) * k / float(n)))
    return out


def _ascii(text):
    """Text for a comment line in the .comm: ASCII only, on one
    line."""
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in (text or ""))


def _fmt_groups(groups):
    return "({0},)".format(", ".join("'{0}'".format(g) for g in groups))


def _fmt_seq(items, per_line=8):
    lines = [", ".join(items[i:i + per_line])
             for i in range(0, len(items), per_line)]
    return "(" + ",\n            ".join(lines) + ",)"


def _scale(value, factor):
    if isinstance(value, Formula):
        return value.scaled(factor)
    if isinstance(value, list):
        return [(t, v * factor) for t, v in value]
    return value * factor


def _shift(value, offset):
    if isinstance(value, Formula):
        return value.shifted(offset)
    if isinstance(value, list):
        return [(t, v + offset) for t, v in value]
    return value + offset


def _med_block():
    """IMPR_RESU MED (study.rmed) only with the setting "med_export";
    Mecway gets the results via the .liml."""
    if not CONFIG_BRIDGE.get("med_export", False):
        return "#-- no MED export (setting med_export off) --\n"
    return ("IMPR_RESU(\n"
            "    FORMAT='MED',\n"
            "    UNITE=80,\n"
            "    RESU=(\n"
            "        _F(RESULTAT=res, NOM_CHAM=('TEMP',)),\n"
            "        _F(RESULTAT=res_flux, NOM_CHAM=('FLUX_NOEU',)),\n"
            "    ),\n"
            ")\n")


def build_thermal(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate study.comm and study.export for a thermal analysis
    (THER_LINEAIRE, or THER_NON_LINE with radiation / shell-face convection).
    Returns the path to study.export, or None on an error.
    """
    import bridge_to_aster as bta
    log("--- Generating Aster Files (thermisch) ---")
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: Thermische analyses werken alleen met result_route "
               "'liml' (resultaten in Mecway's eigen formaat).",
               "ERROR: Thermal analyses only work with result_route "
               "'liml' (results in Mecway's own format)."))
        return None
    th = model_data.get("thermal_data")
    if th is None:
        log(tr("ERROR: Geen thermische gegevens gelezen; is het Mecway-"
               "analysetype T30/T31 of de actieve analyse 'ther_3d'?",
               "ERROR: No thermal data read; is the Mecway analysis "
               "type T30/T31 or the active analysis 'ther_3d'?"))
        return None
    for key, what in (("couplings", tr("koppelingen (nodesurfacecoupling)",
                                       "couplings (nodesurfacecoupling)")),
                      ("contacts", "contact")):
        for c in model_data.get(key, []):
            _skip(model_data, tr("{0} in een thermische analyse",
                                 "{0} in a thermal analysis").format(what))
    tb = _Thermal(model_data, th, analysis)
    tb.msh_path = msh_path
    if not tb.classify():
        return None
    if not tb.check_capacity():
        return None
    tb.apply_loads()
    tb.bonded_loads()
    # Moving welding source (#ASTER-LASBRON, bridge_welding.py)
    import bridge_welding
    welding = bridge_welding.apply(tb, model_data, analysis)
    if welding is None:
        return None
    weld_code, weld_excit, weld_post = welding
    # Metallurgy (#ASTER-METALLURGIE, bridge_metallurgy.py): META_ACIER in
    # the thermal materials (tb.meta_kw), CALC_META after the solve
    import bridge_metallurgy
    meta = bridge_metallurgy.apply(tb, model_data, analysis)
    if meta is None:
        return None
    meta_pre, meta_post = meta
    if not (tb.transient or tb.temp_const or tb.temp_timed or tb.has_exchange):
        # Steady state without imposed temperature or heat exchange:
        # the temperature is undetermined (singular matrix).
        if model_data.get("aster_custom", {}).get("code"):
            log(tr("WARNING: Stationair zonder temperatuur, convectie of "
                   "straling; aangenomen dat de #ASTER-code dat regelt.",
                   "WARNING: Steady state without temperature, convection or "
                   "radiation; assuming the #ASTER code takes care of "
                   "that."))
        else:
            log(tr("ERROR: Stationair thermisch model zonder opgelegde "
                   "temperatuur, convectie of straling (na het weglaten van "
                   "niet-vertaalde onderdelen): de temperatuur is onbepaald.",
                   "ERROR: Steady-state thermal model without imposed "
                   "temperature, convection or radiation (after leaving out "
                   "untranslated items): the temperature is undetermined."))
            return None
    listinst, nsteps = tb.listinst_block()
    if listinst is None:
        return None
    initial = tb.initial_block() if tb.transient else ""
    loads_block, excit = tb.loads_block(
        weld_excit + model_data.get("aster_custom", {}).get("excit", []))
    if loads_block is None:
        return None
    if not excit:
        log(tr("WARNING: Geen thermische randvoorwaarden of belastingen.",
               "WARNING: No thermal boundary conditions or loads."))
    loads_block += weld_code + bta._custom_code(model_data, "code")
    materials_block, fieldmat_block = tb.materials_blocks()
    materials_block = meta_pre + materials_block
    command = "THER_NON_LINE" if tb.nonlinear else "THER_LINEAIRE"
    log("INFO: {0} ({1}){2}.".format(
        command, "transient" if tb.transient else "steady-state",
        " - radiation or convection/radiation on shell faces" if tb.nonlinear
        else ""))

    # --- Solve ---
    solve = ["res = {0}(".format(command),
             "    MODELE=model,",
             "    CHAM_MATER=fieldmat,",
             "    EXCIT=(\n        {0},\n    ),".format(
                 ",\n        ".join(excit)) if excit else "",
             "    TYPE_CALCUL='{0}',".format("TRAN" if tb.transient
                                             else "STAT")]
    if tb.transient:
        solve += ["    ETAT_INIT=_F(CHAM_NO=temp0),",
                  "    SCHEMA_TEMPS=_F(SCHEMA='THETA', THETA={0}),".format(
                      _r(analysis.get("theta", 0.57)))]
    solve += ["    INCREMENT=_F(LIST_INST=times),",
              "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(
                  int(analysis.get("solver_nprec", 8)))]
    if tb.nonlinear:
        solve += ["    NEWTON=_F(REAC_ITER={0}),".format(
                      int(analysis.get("newton_reac_iter", 1))),
                  "    CONVERGENCE=_F(RESI_GLOB_RELA={0}, ITER_GLOB_MAXI={1}),"
                  .format(_r(analysis.get("convergence_resi_rela", 1.0e-6)),
                          int(analysis.get("newton_max_iter", 20)))]
    solve.append(")")
    solve_block = "\n".join(line for line in solve if line) + "\n"
    if tb.birth and tb.nonlinear:
        # Filler material with THER_NL: THER_NON_LINE per birth step
        # (bridge_welding.ther_loop)
        skip = ("res = ", "    CHAM_MATER=", "    ETAT_INIT=", "    INCREMENT=",
                ")")
        solve_block = bridge_welding.ther_loop(
            tb, tb.fieldmat_affe,
            [line for line in solve if line and not line.startswith(skip)])

    # --- Chain thermal -> mechanical (Thermal stress in a T31 model,
    # bridge_thermomech.py): mechanical blocks and a separate template ---
    import bridge_thermomech
    mech = None
    template_name = analysis["template"]
    if bridge_thermomech.enabled(model_data):
        mech = bridge_thermomech.build_blocks(tb, model_data, analysis)
        if mech is None:
            return None
        template_name = bridge_thermomech.TEMPLATE
    elif model_data.get("aster_custom", {}).get("materials"):
        log(tr("WARNING: #ASTER-MATERIAAL werkt alleen met een Thermal stress "
               "in een transient thermisch model (keten thermisch -> "
               "mechanisch); hier genegeerd.",
               "WARNING: #ASTER-MATERIAL only works with a Thermal stress in "
               "a transient thermal model (thermal -> mechanical chain); "
               "ignored here."))

    # --- Post-processing: heat flux (FLUX_NOEU = -lambda grad T) ---
    # The energy check of the welding source before calc_champ_block: there
    # a rotated mesh (shells) is rotated back. In the chain #ASTER-POST is
    # after the mechanical solve (bridge_thermomech).
    calc = weld_post + meta_post + tb.calc_champ_block() + (
        "" if mech else bta._custom_code(model_data, "post"))
    fields = bridge_metallurgy.fields(
        analysis.get("fields", ["temperature", "heat_flux"]), model_data)
    if mech:
        export_block = bridge_thermomech.export_block(
            work_dir, model_data, bridge_metallurgy.mech_fields(
                bridge_thermomech.mech_fields(fields), model_data))
    else:
        export_block = bta._results_route(
            work_dir, model_data, "", "",
            "single" if tb.transient else "double",
            static=not tb.transient, fields=fields)[1]

    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        # UTF-8 as in the mechanical builders (bridge_to_aster._write_comm):
        # Code-Aster reads the .comm as UTF-8.
        template = bta._read_template(template_name)
        bta._write_comm(comm_path, template.format(
            defigroup_block=tb.defigroup_block(),
            model_block=tb.model_block(),
            materials_block=materials_block,
            fieldmat_block=fieldmat_block,
            funcs_block=("\n".join(tb.funcs) + "\n") if tb.funcs
            else "#-- no functions --\n",
            listinst_block=listinst + initial,
            loads_block=loads_block or "#-- no loads --\n",
            solve_block=solve_block,
            calc_champ_block=calc,
            export_block=export_block,
            med_block=(bridge_thermomech.med_block() if mech
                       else _med_block()),
            **(mech or {})
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        with open(export_path, "w") as f:
            f.write("\n".join([
                "P actions make_etude",
                "P time_limit {0}".format(analysis.get("time_limit", 1800)),
                "P memory_limit {0}".format(analysis.get("memory_limit", 4096)),
                "P mpi_nbcpu 1",
                "P ncpus {0}".format(CONFIG_BRIDGE["ncpus"]),
                "P no-mpi true",
                "F comm {0} D 1".format(comm_path),
                "F mail {0} D 20".format(msh_path),
                "F mess {0} R 6".format(os.path.join(work_dir,
                                                     run_name(".mess"))),
            ] + (["F rmed {0} R 80".format(os.path.join(work_dir,
                                                       run_name(".rmed")))]
                 if CONFIG_BRIDGE.get("med_export", False) else [])))
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren thermische solver-bestanden mislukt: {0}",
               "ERROR: Generating the thermal solver files failed: {0}")
            .format(str(e)))
    return None
