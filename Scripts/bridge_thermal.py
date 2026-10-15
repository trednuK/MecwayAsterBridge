# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_thermal.py
# Verantwoordelijkheid: thermische analyses van Mecway (T30 stationair, T31
# transient) naar Code-Aster THER_LINEAIRE / THER_NON_LINE.
#
#   parse_thermal(root, model_data)  - aangeroepen door bridge_from_liml.py
#                                      (alleen als de analyse thermisch is):
#                                      materialen, belastingen,
#                                      beginvoorwaarden en tijdstappen.
#   build_thermal(...)               - builder voor SOLVER_BUILDERS_ASTER
#                                      (bridge_to_aster._build_thermal):
#                                      study.comm + study.export.
#
# Mecway-XML (Mecway 33; voorbeelden in C:\Program Files\Mecway\Samples:
# ConductionConvectionRadiation, FinConvection, OscillatingHeatFlow,
# CoolantChannel):
#   <analysis type="T30|T31" />  <timesteps timeperiod=".." stepsize=".." />
#   <mat><density density=".." /><thermal type="Isotropic"
#        thermalconductivity=".." specificheat=".." /></mat>
#   <temperature2 selection=".."><value>500 K</value><starttime>..
#   <temperature3><nodetemperature nid="1" value="300 K" /></temperature3>
#   <heatflow selection=".."><value>500 W</value> (of <value time="..">)
#   <heatflux selection="vlakken"><value>1000 W/m²</value>
#   <heatgeneration selection="elementen"><value>1e6 W/m³</value>
#   <convectionbc selection=".."><ambienttemp>..<coefficient>..
#   <radiationbc selection=".."><ambienttemp>..<emissivity>..
#   <initialconditions><temperature2 selection=".."><value>..
#
# Vertaling (Code-Aster 17.4; U4.44.02 AFFE_CHAR_THER, U4.54.01
# THER_LINEAIRE, U4.54.02 THER_NON_LINE, U4.43.01 DEFI_MATERIAU THER/THER_NL):
#   - Temperaturen in Code-Aster in graden CELSIUS: RAYONNEMENT rekent met
#     sigma*eps*((T+273,15)^4 - (T_ext+273,15)^4) (U4.44.02, "temperature
#     expressed in Celsius ... use only degrees Celsius for the whole
#     study"). Mecway-waarden (K) worden T - 273,15; aster_results_export
#     telt bij 'temperature' 273,15 op (VALUE_OFFSETS).
#   - Volume-elementen: MODELISATION '3D'; vlakken met een belasting zijn
#     randelementen ('3D' op de huidcellen, ORIE_PEAU).
#   - Schalen: Mecway rekent geleiding in het vlak van de schaal (manual
#     v33 par. 7.4, 6.7). Code-Aster's thermische 'COQUE' heeft drie
#     temperaturen door de dikte en randbelastingen alleen op TRIA
#     (U4.44.02 FLUX_REP/ECHANGE), dus de bridge gebruikt 'PLAN' (2D, diepte
#     1) voor schalen in een vlak Z = constant (anders "les résultats
#     seront faux", alarm MODELE1_53). Liggen alle schalen in evenwijdige
#     vlakken buiten Z = constant, dan draait de .comm het mesh eerst
#     (_Thermal._shell_rotation). Een schaal met dikte t wordt een
#     PLAN-laag met factor f = t / t_ref op LAMBDA en RHO_CP en op alle
#     belastingen per lengte (randen) en per oppervlak (bronnen); t_ref =
#     1 m als er volume-elementen zijn (dan klopt de koppeling met de
#     volumes), anders de meest gebruikte schaaldikte. Schalen van
#     verschillende dikte in één selectie krijgen elk een eigen deelgroep.
#     Een belasting op het schaalvlak (faceid 5/6) wordt een volumebron q/t
#     (SOURCE), convectie en straling op het schaalvlak een
#     temperatuurafhankelijke bron (SOUR_NL, THER_NON_LINE). De warmteflux
#     rekent CALC_CHAMP met de echte lambda (fieldmat_post, zie
#     _Thermal.calc_champ_block).
#     Verificatie (Code-Aster 17.4): ConductionConvectionRadiation geeft
#     380,278 K en 3591,65 W/m2 in schaal en volume, zoals Mecway-manual
#     v33 par. 11.13.
#   - Vergelijking met Mecway 33 (headless 'mecway <model> solve' met
#     <solutionfile filename=".."/>, interne solver): stationair gelijk tot
#     ~1e-11 K (zonder straling); transient rekent Mecway Crank-Nicolson
#     (THETA 0,5) met de belasting op het einde van de stap (zie
#     KNOWN_BUGS 14).
#   - Balken (Mecway fin-elementen): Code-Aster heeft geen thermisch
#     1D-element (catalogus affe_modele.py, PHENOMENE='THERMIQUE'); niet
#     vertaald.
#   - Formules als waarde (x, y, z, t) -> FORMULE in AFFE_CHAR_THER_F
#     (class Formula); temperatuurafhankelijk materiaal (TempDependent) ->
#     THER_NL met functies van TEMP (_Thermal._tempdep_funcs); bewegende
#     lasbron (#ASTER-LASBRON) -> bridge_welding.py.
#   - Straling en schaalvlak-convectie -> THER_NON_LINE met THER_NL
#     (ELEMENTS2_63 "On ne trouve pas le comportement THER_NL" met THER,
#     gezien in een run met Code-Aster 17.4); anders THER_LINEAIRE met THER.
#
# Compatibel met IronPython 2.7.9 (alleen standaardbibliotheek).

import math
import os
import re
from collections import OrderedDict

from bridge_utils import (log, parse_and_convert, CONFIG_BRIDGE, tr,
                          run_name)
import bridge_mesh


# Tags die parse_thermal() leest (bridge_from_liml.py slaat ze dan over).
THERMAL_TAGS = frozenset(["temperature2", "temperature3", "heatflow",
                          "heatflux", "heatgeneration", "convectionbc",
                          "radiationbc", "forcedconvection",
                          "massflowrate"])

# Kelvin -> Celsius (Code-Aster rekent thermisch in Celsius, zie kop).
KELVIN = 273.15
# Stefan-Boltzmann [W/m2/K4], CODATA 2018 (Mecway-manual v33 par. 11.13
# noemt 5,67037e-8).
STEFAN_BOLTZMANN = 5.670374419e-8
# Mecway: knopen zonder begintemperatuur beginnen op 0 K (manual v33
# par. 6.7.2).
MECWAY_DEFAULT_T0 = 0.0

# Getal gevolgd door alleen een eenheid (geen formule zoals 100*cos(t)).
_NUMBER_UNIT = re.compile(
    u"^\\s*[-+]?(\\d+\\.?\\d*|\\.\\d+)([eE][-+]?\\d+)?"
    u"[\\sA-Za-z0-9/\\.\u00b0\u00b2\u00b3\u2074\u00b5\u03bc\u00b7]*$")


def is_thermal(analysis_cfg):
    """True als de analyse-config thermisch is (THER_LINEAIRE/_NON_LINE)."""
    return str(analysis_cfg.get("solver_command", "")).startswith("THER")


def _r(x):
    """Getal voor de .comm: 15 significante cijfers met een decimale punt
    (bridge_mesh._real, %-opmaak volgt de landinstelling niet). Zo wordt
    300 - 273.15 '26.85' en niet 26.850000000000023 (CPython-repr) of
    26.850000000000001 (IronPython-repr, 17 cijfers; gezien in de
    IronPython-harness)."""
    return bridge_mesh._real(float(x))


# ==========================================
# PARSEN
# ==========================================
class Formula(object):
    """
    Mecway-formule als belastingwaarde (mechanisch:
    bridge_bcs.PositionFormula): in de .comm een FORMULE van X, Y, Z en INST
    (AFFE_CHAR_THER_F, catalogus affe_char_ther_f.py: SOURCE, FLUX_REP,
    ECHANGE, RAYONNEMENT, TEMP_IMPO accepteren een formule).

    Waarde in SI = factor * (a * f(x/pu, y/pu, z/pu, t/tu) + b) + offset,
    met (a, b) de eenheid van de uitkomst (bridge_bcs._unit_map), pu/tu de
    SI-waarde van positionunit/timeunit (Mecway schrijft de eenheden als
    attributen, manual v33 par. 12.1). factor/offset komen van de
    vertaling (bijv. 1/oppervlak, K -> Celsius).
    """

    def __init__(self, text, qtype, unit, posunit, timeunit):
        import bridge_bcs
        self.text = (text or "").strip()
        # Controle van de syntax; ValueError (gemeld) bij een fout.
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
        """Waarde op tijdstip t (s); alleen zonder x, y, z."""
        import bridge_bcs
        fn = bridge_bcs.time_function(self.text)
        return self.factor * (self.a * float(fn(t / self.tu)) + self.b) + \
            self.offset

    def render(self, coords, inst="INST"):
        """(uitdrukking, NOM_PARA, {naam: argument}) voor FORMULE.
        coords: {"x": uitdrukking in X, Y, Z} (gedraaid mesh); inst:
        uitdrukking voor de tijd (stationair: '1.0')."""
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
    """SI-waarde van 1 eenheid (positionunit/timeunit); 1 als leeg."""
    unit = (unit or "").strip()
    if not unit:
        return 1.0
    v = parse_and_convert(u"1 " + unit, qtype)
    return v if isinstance(v, float) and v > 0.0 else 1.0


def _is_timed(value):
    return isinstance(value, (list, Formula))


def _value(text, qtype):
    """Getal met eenheid naar SI; ValueError bij een formule of leeg."""
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
    Tekst van een waarde-knoop. Een formule schrijft Mecway als
    <x unit="°C" timeunit="s" positionunit="m">20</x>: zonder eenheid
    in de tekst; is de formule alleen een getal, dan hoort de eenheid uit
    het attribuut erbij (anders 20 -> 20 K). Een echte formule blijft
    tekst en wordt door _value geweigerd (gemeld).
    """
    text = node.text
    unit = node.get("unit")
    if unit and text is not None and _BARE_NUMBER.match(text):
        return u"{0} {1}".format(text.strip(), unit)
    return text


def _formula_node(node):
    """True als node een Mecway-formule is: eenheden als attributen en
    geen kaal getal (_with_unit)."""
    if not any(node.get(a) is not None for a in
               ("unit", "timeunit", "positionunit")):
        return False
    return not (node.text is not None and _BARE_NUMBER.match(node.text))


def _values(item, tag, qtype, formulas=True):
    """float, lijst (t, waarde) bij <tag time="..">, Formula (formule in
    x, y, z, t; alleen met formulas=True), of None."""
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
    Tabellen van een temperatuurafhankelijk thermisch materiaal (Mecway
    manual v33 par. 8.6; XML gezien in een met Mecway 33 opgeslagen model,
    mw.set_material_type(.., "thermal", "TempDependent")):
      <thermal type="TempDependent" thermalconductivity=".." ..>
        <specificheat temp="300 K" value="450 J/kg/K" />
        <thermalconductivity temp="300 K" value="50 W/m/K" />
      </thermal>
    (de attributen op <thermal> zijn resten van het type Isotropic en
    tellen niet als er een tabel is). Returns {"lambda_T": [(T in Celsius,
    W/m/K)], "cp_T": [(T, J/kg/K)]}, oplopend in T; ValueError bij een
    formule of een lege tabel.
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
    # Zonder XPath-predicaat ([@name='...']): een apostrof in de
    # selectienaam gaf daar een SyntaxError.
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
    Lees de thermische gegevens in model_data:
      "thermal"           : True
      "thermal_materials" : {mat: {"lambda", "rho", "cp"}}
      "thermal_data"      : {"materials", "loads", "node_temps",
                             "initial", "transient", "timesteps"}
    Niet-vertaalbare onderdelen gaan naar model_data["skipped_loads"].
    """
    th = {"materials": OrderedDict(), "loads": [], "node_temps": [],
          "initial": [], "transient": model_data.get("analysis_type") == "T31",
          "timesteps": {}}
    model_data["thermal"] = True
    model_data["thermal_materials"] = th["materials"]
    model_data["thermal_data"] = th

    # --- Materialen ---
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
            # Bijv. het water van een vloeistofnetwerk (alleen specificheat,
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
            # check_capacity: rho*cp > 0 over de hele tabel
            props["cp"] = min(v for _t, v in tables["cp_T"])
        th["materials"][name] = props
        if tables:
            log("INFO: Thermisch materiaal '{0}' temperatuurafhankelijk "
                "(Mecway TempDependent): lambda(T) {1} punten, cp(T) {2} "
                "punten, rho={3} kg/m3; THER_NON_LINE.".format(
                    name, len(tables.get("lambda_T", [])),
                    len(tables.get("cp_T", [])), props["rho"]))
        else:
            log("INFO: Thermisch materiaal '{0}': lambda={1} W/m/K, rho={2} "
                "kg/m3, cp={3} J/kg/K".format(name, props["lambda"],
                                              props["rho"], props["cp"]))

    # --- Belastingen en randvoorwaarden ---
    for item in root:
        tag = item.tag
        if tag not in THERMAL_TAGS or item.get("suppressed", "") == "true":
            continue
        sel = item.get("selection", "")
        if tag in ("forcedconvection", "massflowrate"):
            # Vloeistofnetwerk (manual v33 par. 7.12, 9.31, 9.33; alleen
            # CCX): geen equivalent in de bridge.
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
        log("INFO: Thermisch: {0} op '{1}' ({2}).".format(
            tag, sel, load["target"]))

    # --- Beginvoorwaarden ---
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

    # --- Tijdstappen (T31: stepsize; D31 schreef timepointsincrement) ---
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
    log("INFO: Thermisch: {0} materialen, {1} belastingen, {2} knoop"
        "temperaturen, {3} beginvoorwaarden, {4}.".format(
            len(th["materials"]), len(th["loads"]), len(th["node_temps"]),
            len(th["initial"]), "transient" if th["transient"]
            else "stationair"))


# ==========================================
# GEOMETRIE
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
    """Lengte van een SEG2 (2 punten) of SEG3 (hoek, hoek, midden; 3-punts
    Gauss op de kwadratische kromme)."""
    if len(pts) == 2:
        return _dist(pts[0], pts[1])
    total = 0.0
    for xi, w in ((-0.774596669241483, 5.0 / 9.0), (0.0, 8.0 / 9.0),
                  (0.774596669241483, 5.0 / 9.0)):
        # dN/dxi voor N0 = xi(xi-1)/2, N1 = xi(xi+1)/2, N2 = 1-xi^2
        d = (xi - 0.5, xi + 0.5, -2.0 * xi)
        t = [sum(d[k] * pts[k][c] for k in range(3)) for c in range(3)]
        total += w * math.sqrt(sum(c * c for c in t))
    return total


def _face_area(stype, pts):
    return sum(bridge_mesh._face_integrals(stype, pts)[0])


# Tetraeders (hoekindices, Code-Aster-volgorde) per volumetype; exact voor
# elementen met rechte ribben en vlakke zijvlakken (anders een benadering).
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
    """Verzamelt groepen, modelisaties, functies en lasten voor de .comm."""

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
        self.crea_ma = []         # DEFI_GROUP stap 1 (CREA_GROUP_MA)
        self.crea_ma2 = []        # DEFI_GROUP stap 2 (DIFFE/INTERSEC)
        self.crea_no = []         # CREA_GROUP_NO
        self.skin3d = []          # randgroepen van volumes ('3D', ORIE_PEAU)
        self.edges = []           # randgroepen van schalen ('PLAN')
        self.funcs = []           # DEFI_FONCTION / DEFI_CONSTANTE
        self.charges = []         # (commando, OrderedDict kw -> [_F])
        self.temp_const = []      # TEMP_IMPO constant
        self.temp_timed = []      # TEMP_IMPO met functie
        self.face_cache = {}
        self.inactive_faces = {}
        self.shells_union = None
        self.rotation = None      # classify: (Q, as, hoek) of None
        self.msh_path = None      # geschreven mesh (build_thermal)
        self.mesh_segs = None     # _edge_names: {naam: knopen} van SEG
        self.mesh_groups = None   # _edge_names: {groep: [elementnamen]}
        self.cell_index = None    # _list_group: {elementnaam: celnummer}
        self.node_flows = []      # (knoopgroep, waarde per knoop of tabel)
        self.birth = None         # toevoegmateriaal (bridge_welding._births)
        # Bronnen als functie (SOURCE in AFFE_CHAR_THER_F) samen in een last
        # (add_func_source, merged_sources): [{grp, sour, eids}]
        self.func_sources = []
        self.sources_taken = False  # bridge_welding zette ze in 'lasbron'
        self.group_cells = {}     # groep -> [eid] (element_targets, schaalvlak)
        self.func_params = {}     # functienaam -> NOM_PARA of constante

    # ---------- namen ----------
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

    # ---------- elementen ----------
    def classify(self):
        """Welke elsets worden gemodelleerd (volume '3D', vlakke schaal
        'PLAN'); balken, gekromde schalen en elsets zonder thermisch
        materiaal niet. Returns False als er niets te rekenen is."""
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
        # Alle schalen in evenwijdige vlakken buiten Z = constant: het mesh
        # wordt in de .comm gedraaid (zie _shell_rotation).
        self.rotation = self._shell_rotation(members, mats)
        zrow = self.rotation[0][2] if self.rotation else (0.0, 0.0, 1.0)
        # Volgorde van de .liml (de dicts in model_data hebben in IronPython
        # geen vaste volgorde).
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
            log("INFO: Schalen als PLAN met referentiedikte {0} m; factoren "
                "f = t / t_ref: {1}".format(self.t_ref, dict(
                    (k, v["f"]) for k, v in self.elsets.items()
                    if v["cls"] == "shell")))
        self.modelled = set(n for _s, _c, _a, cn in self.elem.values()
                            for n in cn)
        if any("lambda_T" in mats[i["mat"]] or "cp_T" in mats[i["mat"]]
               for i in self.elsets.values()):
            # THER_NL met functies van TEMP (_tempdep_funcs)
            self.nonlinear = True
        return True

    def _shell_rotation(self, members, mats):
        """(Q, as, hoek in graden) als alle schaalelementen evenwijdig zijn
        maar niet in een vlak Z = constant liggen, anders None. Q (rijen)
        draait de schaalnormaal n op Z (Rodrigues, rechtsom om as = n x Z).

        PLAN rekent in het XY-vlak (AFFE_MODELE: alarm MODELE1_53 "les
        résultats seront faux" voor een element buiten Z = constant). De
        .comm draait daarom het hele mesh (MODI_MAILLAGE ROTATION, star:
        volumes, temperaturen en oppervlakken veranderen niet) en draait de
        warmteflux na CALC_CHAMP terug (calc_champ_block). Getest met Code-
        Aster 17.4 tegen Mecway (vlak XZ en schuin vlak, KNOWN_BUGS 15)."""
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
        log("INFO: Schalen liggen in evenwijdige vlakken met normaal ({0}, "
            "{1}, {2}); het mesh wordt {3} graden om ({4}, {5}, 0) gedraaid "
            "zodat ze in een vlak Z = constant liggen (PLAN).".format(
                _r(n0[0]), _r(n0[1]), _r(n0[2]), _r(math.degrees(ang)),
                _r(k[0]), _r(k[1])))
        return q, k, math.degrees(ang)

    # ---------- doelgroepen ----------
    def face_parts(self, sel):
        """[(soort, oppervlak, knopen, f, t, (eid, faceid))] van een
        vlakselectie; soort solid / shelledge / shellface / inactive."""
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
        """Deelgroep van src met alleen de elementen van één dimensie
        (DEFI_GROUP TYPE_MAILLE)."""
        sub = self.new_group()
        self.crea_ma.append("_F(NOM='{0}', GROUP_MA='{1}', "
                            "TYPE_MAILLE='{2}')".format(sub, src, type_maille))
        return sub

    def _list_group(self, names):
        """Deelgroep met een MAILLE-lijst van elementen uit het mesh (namen
        zoals bridge_mesh ze schrijft: 'M<eid>', 'K<n>').

        Code-Aster 17.4 bewaart de elementnamen van het ASTER-mesh niet:
        MAILLE='M<n>' is de n-de cel in het bestand (char8_to_int.F90 leest
        het getal na de letter; 'K5' gaf "Fortran runtime error: Bad integer
        for item 1 in list input", 'M1001' in een mesh met 20 cellen
        MODELISA6_10 "ne fait pas partie du maillage"; gezien met Code-
        Aster 17.4). De bridge vertaalt de naam daarom naar het celnummer
        uit model_data["cell_names"] (bridge_mesh, volgorde in het
        bestand)."""
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
        """{frozenset(knopen): elementnaam} van de randelementen (SEG) in
        de mesh-groep van de selectie. bridge_mesh bewaart de namen van de
        randelementen niet in model_data, dus ze komen uit het geschreven
        mesh (self.msh_path; alleen nodig voor schaalranden van
        verschillende dikte in één selectie)."""
        if self.mesh_segs is None:
            self.mesh_segs, self.mesh_groups = _read_mesh_segments(
                self.msh_path)
        members = set(self.mesh_groups.get(self.rn(sel), []))
        return dict((nodes, name) for name, nodes in self.mesh_segs.items()
                    if name in members)

    def face_targets(self, sel, label):
        """([(soort, groep, f, t)], oppervlak) voor belastingen op
        vlakken; soort solid / shelledge / shellface, oppervlak = totaal
        van de vertaalde vlakken (randen: lengte x dikte). None als er
        niets overblijft.

        Schalen met verschillende dikte in één selectie (KNOWN_BUGS 15)
        en schaalelementen met beide zijden (faceid 5 en 6) geselecteerd
        krijgen eigen deelgroepen met een MAILLE-lijst per (f, t, aantal
        zijden), zodat elke dikte zijn eigen factor krijgt."""
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
        kinds = OrderedDict()     # soort -> OrderedDict((f, t) -> True)
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
        # Schaalvlakken: faceid 5 en 6 van hetzelfde element staan in de
        # mesh-groep twee keer als hetzelfde element (bridge_mesh); Code-
        # Aster haalt de dubbele weg (alarm MODELISA5_8), dus de last zou
        # maar op één zijde werken terwijl heatflow over beide zijden (2A)
        # verdeeld wordt. De bridge legt de last daarom op beide zijden: een
        # eigen groep met f x 2 (convectie, straling, flux, heatflow).
        # Mecway doet hetzelfde (Mecway 33, interne solver, headless
        # 'mecway <model> solve'): een plaat met heatflux of convectie op
        # faceid 5 en 6 geeft 2x de opwarming / de fin met 2h, en heatflow
        # wordt over beide zijden verdeeld; Code-Aster via de bridge wijkt
        # < 1e-11 K af (headless Mecway-run).
        sides = OrderedDict()
        for kind, _a, _n, _f, _t, key in parts:
            if kind == "shellface":
                sides.setdefault(key[0], set()).add(key[1])
        double = [e for e, fids in sides.items() if len(fids) > 1]
        if double:
            log("INFO: {0}: {1} schaalelement(en) in '{2}' hebben beide "
                "zijden (faceid 5 en 6) geselecteerd; de belasting werkt op "
                "beide zijden (factor 2), zoals in Mecway.".format(
                    label, len(double), sel))
        split_face = "shellface" in kinds and (
            bool(double) or len(kinds["shellface"]) > 1)
        split_edge = len(kinds.get("shelledge", ())) > 1
        out = []                  # (soort, groep, f, t)
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
            # Volumevlakken en schaalvlakken zijn allebei 2D: scheiden met
            # de groep van alle schalen.
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
                # schaalvlak-bron (SOURCE): de schaalelementen zelf
                self.group_cells[grp] = shell_eids
            if kind == "solid" and grp not in self.skin3d:
                self.skin3d.append(grp)
            if kind == "shelledge" and grp not in self.edges:
                self.edges.append(grp)
        return (out, area) if out and area > 0.0 else None

    def _face_lists(self, parts, sides, fts):
        """Schaalvlakken per (f, t, aantal zijden) in een eigen groep
        (elementnamen 'M<eid>', bridge_mesh); f maal het aantal zijden.
        Volgorde: per dikte eerst de enkelzijdige, dan de dubbelzijdige."""
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
        """Schaalranden per (f, t) in een eigen groep; None (gemeld) als
        een randelement niet in het mesh gevonden wordt."""
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
        """([(soort, groep, f, t)], volume) voor bronnen op elementen;
        soort solid / shell. Schalen van verschillende dikte krijgen elk
        een eigen groep (MAILLE-lijst per (f, t), KNOWN_BUGS 15)."""
        eids = self.md.get("element_selections", {}).get(self.rn(sel), [])
        kinds = OrderedDict()     # soort -> OrderedDict((f, t) -> [eid])
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
        # Vlakken van balken: knopen uit de Mecway-tabel van het lijnelement
        conn = dict((e, en) for e, s, en, _es in
                    self.md.get("mesh_elements", []) if s.startswith("line"))
        for eid, fid in self.md.get("face_selection_faces", {}).get(sel, []):
            if eid in conn:
                en = conn[eid]
                out.update({1: en, 2: en[:1], 3: en[-1:]}.get(fid, en))
        return out

    def node_target(self, sel, kind, label):
        """('GROUP_MA'|'GROUP_NO', groep) voor TEMP_IMPO / beginwaarden;
        alleen gemodelleerde knopen (anders een eigen knoopgroep)."""
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

    # ---------- waarden en functies ----------
    def formula_coords(self):
        """{"x"|"y"|"z": uitdrukking in X, Y, Z van Code-Aster}. Met een
        gedraaid mesh (_shell_rotation: x_rot = Q x) is x = Q^T x_rot."""
        if not self.rotation:
            return {"x": "X", "y": "Y", "z": "Z"}
        q = self.rotation[0]
        out = {}
        for j, v in enumerate(("x", "y", "z")):
            out[v] = "+".join("({0})*{1}".format(_r(q[i][j]), "XYZ"[i])
                              for i in range(3) if abs(q[i][j]) > 1.0e-15)
        return out

    def formula(self, fobj):
        """Naam van een FORMULE voor een Formula (Mecway-formule)."""
        import bridge_bcs
        expr, params, args = fobj.render(
            self.formula_coords(), "INST" if self.transient else "1.0")
        if not self.funcs or self.funcs[0] != bridge_bcs.ASTER_FORMULA_PRELUDE:
            self.funcs.insert(0, bridge_bcs.ASTER_FORMULA_PRELUDE)
        self.counter += 1
        name = "FF{0}".format(self.counter)
        if not params:
            # Alleen t in een stationaire analyse: t = 1 s ingevuld
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
        """Stationair: een tijdstabel wordt de waarde op t = 1 s, zoals
        Mecway met CCX. Gemeten met Mecway 33 (headless 'mecway <model>
        solve', T30):
          - CCX (solver="ccx"): lineair geïnterpoleerd op t = 1 s, het einde
            van de stap (temperature2 0 s/300 K, 2 s/500 K -> 400 K; 0,5 s/
            300 K, 0,8 s/600 K, 2 s/500 K -> 583,33 K; ook met <timesteps
            timeperiod="2 s">; convectie en heatgeneration idem);
          - interne solver: een grootheid met een tabel telt als 0
            (heatgeneration met elke tabel: geen bron; convectie met een
            tabel voor T_omg: rekent met 0 K, voor h: geen convectie;
            temperature2 met een tabel: niet opgelegd).
        De bridge volgt CCX en meldt het verschil met de interne solver.
        Een formule in t krijgt t = 1 s (NIET met Mecway vergeleken)."""
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
                log("INFO: {0}: tijdstabel in een stationaire analyse; "
                    "waarde op t = 1 s gebruikt ({1}), zoals Mecway met "
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
        """Naam van een DEFI_FONCTION (lijst), FORMULE (Formula) of
        DEFI_CONSTANTE (getal)."""
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
        """DEFI_FONCTION van TEMP (Celsius), lineair verlengd."""
        self.funcs.append(
            "{0} = DEFI_FONCTION(NOM_PARA='TEMP', VALE=(\n    {1},\n), "
            "PROL_GAUCHE='LINEAIRE', PROL_DROITE='LINEAIRE')".format(
                name, ",\n    ".join("{0}, {1}".format(_r(t), _r(v))
                                     for t, v in values_c)))

    def add_charge(self, kw_entries):
        """Een last: kw_entries = [(kw, {param: waarde of lijst}, groep)].
        Met een tijdstabel wordt alles AFFE_CHAR_THER_F met functies; een
        SOURCE met een functie gaat naar de gezamenlijke bronlast
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
        """SOURCE met functie 'name' op groep grp (de elementen staan in
        self.group_cells). Alle functiebronnen komen samen in een last
        (merged_sources): Code-Aster 17.4 rekent twee lasten
        AFFE_CHAR_THER_F met SOURCE in een EXCIT-lijst allebei met de
        functie van de eerste last (gemeten: twee helften met 2e6*t en een
        tijdstabel gaven 2x de eerste, in omgekeerde volgorde 2x de
        tweede). Een last met meer SOURCE-regels rekent goed, net als twee
        functielasten met FLUX_REP, ECHANGE of SOUR_NL en met
        AFFE_CHAR_MECA_F (FORCE_INTERNE, FORCE_FACE, PRES_REP) (gemeten met
        Code-Aster 17.4). De oorzaak zit in de gecompileerde code: NIET
        geverifieerd. De plaats van de eerste functiebron in self.charges
        wordt een merkteken (None), zodat de volgorde van EXCIT blijft."""
        if not self.func_sources:
            self.charges.append(None)
        self.func_sources.append({"grp": grp, "sour": name,
                                  "eids": self.group_cells.get(grp)})

    def source_items(self):
        """De functiebronnen als items voor merged_sources: term (aanroep
        in een FORMULE), ctx (argumenten van die FORMULE), params."""
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
        SOURCE-regels voor een AFFE_CHAR_THER_F met alle functiebronnen
        (items, zie source_items; bridge_welding voegt de lasbronnen toe).
        In een last overschrijft een latere SOURCE-regel op hetzelfde
        element de eerdere (gemeten met Code-Aster 17.4: de hele wand met
        f1 en daarna een helft met f2 gaf op die helft alleen f2). Daarom
        wordt het mesh
        verdeeld naar de bronnen die op het element liggen (en owner[eid],
        het toevoegmateriaal van een lasbron); per deel een FORMULE met de
        som (FORMULEs en DEFI_FONCTIONs als argument aangeroepen),
        met toevoegmateriaal alleen waar het al geboren is: born(j) =
        (voorwaarde, {naam: argument}). Een bron die met niets overlapt
        houdt zijn eigen groep en functie (de .comm met een bron blijft
        gelijk). Gekozen boven een FORMULE met indicatortermen per groep:
        die zou de groep uit X, Y, Z moeten afleiden, wat op de rand
        tussen twee groepen niet eenduidig is.
        Returns ([FORMULE-regels], [_F-regels]) of None (ERROR gemeld).
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
            log("INFO: {0} warmtebronnen als functie in een last (Code-Aster "
                "17.4 rekent meer functielasten met SOURCE als de eerste); "
                "{1} deel/delen van het mesh met de som van overlappende "
                "bronnen.".format(len(items), overlap))
        return lines, entries

    # ---------- belastingen ----------
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

    # ---------- verlijmd contact ----------
    def bonded_loads(self):
        """
        Verlijmd contact (contact2 bondedtie/bondedce/bondedelastic,
        model_data["bonded"] uit bridge_mesh._bonded) in een thermische
        analyse. Mecway: bij thermisch krijgt de slave-knoop de waarde in
        het geprojecteerde punt op het master-vlak; 'elastic' is thermisch
        een weerstandslaag met "Thermal conductance per unit area" (manual
        v33 par. 9.9.1).
          - tie / constraint equations (en elastic waar ECHANGE_PAROI niet
            kan): AFFE_CHAR_THER LIAISON_MAIL (catalogus affe_char_ther.py
            v17.4: GROUP_MA_MAIT, GROUP_NO_ESCL, DISTANCE_MAX; geen
            TYPE_RACCORD of DDL, alleen TEMP). Master: de moederelementen
            (volumes) of de schaalelementen, zoals mechanisch.
          - elastic: AFFE_CHAR_THER ECHANGE_PAROI (GROUP_MA_1/GROUP_MA_2,
            COEF_H = geleiding per oppervlak; U4.44.02, testcases ttlp101a
            en tplv101c) tussen de randvlakken van beide kanten. Alleen
            volumevlakken die knoop op knoop tegenover elkaar liggen
            (_conforming_faces); anders tie + WARNING + skipped_loads.
          - Volumes en schalen (PLAN) samen in het model: dan kan geen van
            beide (Code-Aster 17.4: LIAISON_MAIL <EXCEPTION> CHARGES7_6
            "mélange d'éléments 2D ... et 3D. Il n'est pas possible de
            réaliser une liaison", schaalrand op een blok; ECHANGE_PAROI
            <EXCEPTION> CHARGES6_2 "le modèle fourni doit être homogène en
            dimension", twee blokken met een losse schaal); ERROR +
            skipped_loads.
        Verificatie TH-04 (tests_thermisch.py).
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
            log("INFO: {0} -> AFFE_CHAR_THER LIAISON_MAIL (TEMP van de "
                "slave-knopen = TEMP op het master-vlak).".format(label))

    def _bonded_groups(self, b, label):
        """(master-elementgroep, slave-knoopgroep) in het thermische mesh.
        BRMAIT/BRESCL (bridge_mesh._bonded) maakt alleen de mechanische
        DEFI_GROUP aan (bridge_to_aster._build_defigroup_block); hier eigen
        groepen, zodat de keten thermisch -> mechanisch (zelfde mesh) ze
        niet twee keer aanmaakt."""
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
        """Elastic: ECHANGE_PAROI als dat kan (None), anders de reden
        (tekst; de aanroeper meldt en maakt er een tie van)."""
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
            "W/m2/K (weerstandslaag).".format(label, _r(h)))
        return None

    def _conforming_faces(self, parts_m, parts_s):
        """True als elk slave-vlak dezelfde knooppunten (coordinaten) heeft
        als een master-vlak en omgekeerd."""
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
            # Totaal over alle vlakken, gelijkmatig per oppervlak (manual
            # v33 par. 9.27); schaalranden: lengte x dikte.
            q = _scale(q, 1.0 / area)
            log("INFO: {0}: totaal oppervlak {1} m2.".format(label, area))
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
            else:   # schaalvlak: bron q/t per volume (maal f)
                entries.append(("SOURCE", {"SOUR": _scale(q, f / t)}, grp))
        self.add_charge(entries)

    def apply_node_flow(self, load, label):
        """heatflow op knopen: Mecway verdeelt de warmtestroom gelijk over
        de knopen (manual v33 par. 9.27, "divided equally between each
        node"). AFFE_CHAR_THER kent geen puntbron en THER_LINEAIRE/
        THER_NON_LINE geen EXCIT met een vector (catalogi
        affe_char_ther.py, ther_lineaire.py, ther_non_line.py), wel SOURCE
        SOUR_CALCULEE met een knoopveld s (W/m3). Dat geeft knooplasten
        M s met M = int(N_i N_j dV) (MASS_THER met RHO_CP = 1); met
        s = M^-1 F (RESOUDRE) zijn de knooplasten precies F (zie
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
        # Per knoop; met schalen als PLAN in modeleenheden (diepte t_ref).
        self.node_flows.append((tgt[1], _scale(
            load["value"], 1.0 / (len(nodes) * self.t_ref))))
        log("INFO: {0}: warmtestroom gelijk verdeeld over {1} knopen.".format(
            label, len(nodes)))

    def node_flow_block(self):
        """(.comm-blok, [EXCIT-entries]) voor heatflow op knopen: per last
        de knooplasten F (NOEU_TEMP_R), een bronveld s = M^-1 F
        (CALC_MATR_ELEM MASS_THER met RHO_CP = 1, RESOUDRE) en een last
        SOURCE SOUR_CALCULEE = s; met een tijdstabel s voor 1 W per knoop
        en FONC_MULT = de tabel."""
        if not self.node_flows:
            return "", []
        lines = [
            "# heatflow op knopen: bron s = M^-1 F (bridge_thermal."
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
                # SOUR_CALCULEE wil grandeur SOUR_R (CALCUL_5 met TEMP_R)
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
            log("INFO: {0}: totaal volume {1} m3.".format(label, vol))
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
        """Convectie/straling op een schaalvlak (PLAN): bron f/t * q(T)
        (SOUR_NL, functie van TEMP; U4.44.02 SOUR_NL)."""
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
        """Idem met een tijdstabel (h, T_omg of emissiviteit). SOUR_NL
        geeft de functie alleen TEMP (een FORMULE van TEMP en INST gaf in
        THER_NON_LINE "NameError: name 'INST' is not defined", Code-Aster
        17.4), dus gesplitst in een bron en een put:
          convectie: k*h*(Ta - T) = k*h(t)*Ta(t)  (SOURCE, FORMULE van INST)
                                  - k*h(t)*T      (SOUR_NL van TEMP)
          straling:  k*sigma*eps(t)*((Ta(t)+273,15)^4 - (T+273,15)^4) idem.
        Een tabel voor h of eps gaat in de put als EXCIT FONC_MULT (de
        SOUR_NL-functie dan met coëfficiënt 1). Tabellen: DEFI_FONCTION van
        INST, PROL CONSTANT (zoals Mecway, manual v33 par. 9)."""
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
        # Put: -c*coef*T (convectie) of -c*coef*(T+273,15)^4 (straling)
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

    # ---------- blokken ----------
    def defigroup_block(self):
        out = []
        if self.rotation:
            _q, k, ang = self.rotation
            # Alarm MODELE1_53 ("Le maillage est 3D ...") blijft: Code-Aster
            # bepaalt de dimensie van het mesh bij LIRE_MAILLAGE; de
            # schalen liggen na de draaiing wel in een vlak Z = constant
            # (resultaten gelijk aan Mecway, zie _shell_rotation).
            out.append("# Schalen naar een vlak Z = constant (PLAN), zie "
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
            # Vlakken van volumes met de normaal naar buiten (MODI_MAILLAGE
            # ORIE_PEAU, zoals de mechanische builders).
            out.append("mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE="
                       "mesh,\n    ORIE_PEAU=_F(GROUP_MA_PEAU={0}),\n)\n".format(
                           _fmt_groups(self.skin3d)))
        return "\n".join(out) if out else "#-- geen extra groepen --\n"

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
            # Toevoegmateriaal (bridge_welding): diagonale warmtecapaciteit
            # (3D_DIAG, testcase ttnp201a), na de volumes (de laatste
            # toewijzing telt). Met de consistente capaciteit volgde een
            # stil knooppunt via de massakoppeling de temperatuursnelheid
            # van zijn warme buren (WE-13: +138 K voor de geboorte, met een
            # dip eronder bij het opwarmen); diagonaal niet.
            affe.append("_F(GROUP_MA='{0}', PHENOMENE='THERMIQUE', "
                        "MODELISATION='3D_DIAG')".format(self.birth["all"]))
        return ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n    AFFE=(\n"
                "        {0},\n    ),\n)\n").format(",\n        ".join(affe))

    def materials_blocks(self):
        """(DEFI_MATERIAU-blok, AFFE_MATERIAU-blok). Met schalen f != 1 ook
        'fieldmat_post' zonder factor: CALC_CHAMP rekent de warmteflux
        daarmee (-lambda grad T met de echte lambda; CALC_CHAMP CHAM_MATER,
        catalogus calc_champ.py)."""
        lines = []
        fieldmat = self._fieldmat("fieldmat", "MTH", True, lines)
        if self.scaled():
            fieldmat += self._fieldmat("fieldmat_post", "MTP", False, lines)
        return "\n".join(lines) + "\n", fieldmat

    def scaled(self):
        return any(abs(i["f"] - 1.0) > 1.0e-12 for i in self.elsets.values())

    def _fieldmat(self, concept, prefix, with_f, lines):
        # Lokaal, zoals in build_thermal (bridge_to_aster importeert deze
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
                    # Temperatuurafhankelijk (Mecway TempDependent, manual
                    # v33 par. 8.6: lineair geïnterpoleerd, buiten de tabel
                    # het dichtstbijzijnde punt -> PROL CONSTANT). THER_NL
                    # met RHO_CP als functie van TEMP: Code-Aster bepaalt
                    # daaruit de enthalpie BETA (U4.43.01 THER_NL; R5.02.02).
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
                # Naam gefilterd zoals in de mechanische builders (alleen
                # ASCII, geen regeleinde; bridge_to_aster._mat_comment).
                lines.append("{0}{1}\n{2} = DEFI_MATERIAU({3})".format(
                    bta._mat_comment(info["mat"]).rstrip("\n"),
                    "" if f == 1.0 else " (schaal, f = {0})".format(_r(f)),
                    names[key], body))
            affe.append("_F(GROUP_MA='{0}', MATER={1})".format(
                elset, names[key]))
        varc = ""
        if self.birth and with_f:
            # Toevoegmateriaal dat geboren wordt (#ASTER-LASBRON geboorte=,
            # bridge_welding): eigen materiaal op de elementen, na de elsets
            # (de laatste toewijzing telt, U4.43.03 AFFE_MATERIAU).
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
        """DEFI_FONCTION van TEMP (Celsius) voor LAMBDA ({name}_L) en
        RHO_CP ({name}_C); zonder tabel een constante functie. f_lambda:
        eigen factor voor lambda (anders f; toevoegmateriaal, bridge_welding
        .birth_materials)."""
        def func(concept, table, scale, const):
            if not table:
                return "{0} = DEFI_CONSTANTE(VALE={1})".format(concept,
                                                             _r(const))
            # De tabel expliciet constant verlengen tot 0 K en tot 10 000 K
            # boven het laatste punt, en RHO_CP verfijnen (_refine_table).
            # Gemeten (Code-Aster 17.4, verificatie WE-04b, staaf met cp
            # 450..750 J/kg/K op 300/800/1300 K, start op 293,15 K): met de
            # Mecway-tabel zelf miste na de eerste stap 13% van de
            # ingebrachte energie (na 2 s 2,8%); verlengd 10%; verlengd en
            # verfijnd 0,01%. THER_NON_LINE leidt de enthalpie BETA af uit
            # de tabelpunten van RHO_CP (zie _refine_table); buiten het
            # bereik telde de verlenging van RHO_CP niet volledig mee.
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
        """Transient: elke elset heeft rho*cp > 0 nodig."""
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
            # Het merkteken van add_func_source: alle functiebronnen in een
            # last, of niets als bridge_welding ze in 'lasbron' zette
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
            # (commando, kw's) of (commando, kw's, FONC_MULT)
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
        """CREA_CHAMP met de begintemperatuur (Celsius) voor ETAT_INIT."""
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
        log("INFO: Transient thermisch: {0} stappen tot {1} s.".format(
            n, period))
        # Tijden expliciet (k * period / n, 15 cijfers): INTERVALLE/NOMBRE
        # telt de stap op en gaf tijden als 39.9999999999999 s in Mecway.
        vals = [_r(period * k / float(n)) for k in range(n + 1)]
        return ("times = DEFI_LIST_REEL(VALE=(\n    {0},\n))\n".format(
            ",\n    ".join(", ".join(vals[i:i + 8])
                           for i in range(0, len(vals), 8)))), n

    def calc_champ_block(self):
        """
        Warmteflux (-lambda grad T) in een eigen resultaat res_flux
        (aster_results_export leest 'heat_flux' daaruit). Met geschaalde
        schalen (f != 1) rekent CALC_CHAMP met fieldmat_post (echte
        lambda). Twee stappen, gezien met Code-Aster 17.4:
          - CALC_CHAMP reuse=res met een andere CHAM_MATER is verboden
            (CALCULEL_33);
          - in een nieuw resultaat in een aanroep FLUX_ELGA, FLUX_ELNO en
            FLUX_NOEU vragen gaf FLUX_NOEU op schaalknopen f x de flux
            (FLUX_ELNO kwam uit de FLUX_ELGA van res, die THER_NON_LINE met
            de geschaalde lambda opslaat); eerst FLUX_ELGA, dan in een
            tweede aanroep FLUX_ELNO/FLUX_NOEU gaf overal 3591,65 W/m2
            (ConductionConvectionRadiation).
        Alarm RESULT1_39 (ander materiaal dan in het resultaat) is dan
        bedoeld.
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
        """Gedraaid mesh (_shell_rotation): FLUX_NOEU per tijdstap terug naar
        de globale assen, v_glob = Q^T v (CREA_CHAMP ASSE met COEF_R per
        component, Result.setField; zelfde NUME_ORDRE als res, dat
        aster_results_export gebruikt). PLAN-knopen hebben geen FLUZ
        (MODI_REPERE VECT_3D weigert dat: ALGORITH2_12, Code-Aster 17.4);
        FLUZ telt alleen mee als er volume-elementen zijn."""
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
        return ("# Warmteflux terug naar de globale assen (mesh gedraaid, "
                "zie defigroup)\n"
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
                "# Mesh terug in de oorspronkelijke stand (aster_results_export "
                "vergelijkt de knoopcoördinaten met de .liml)\n"
                "mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE=mesh,\n"
                "    ROTATION=_F(POIN_1=(0.0, 0.0, 0.0), DIR=({1}, {2}, {3}), "
                "ANGLE={4}),\n)\n").format(
                    ",\n        ".join(terms), _r(self.rotation[1][0]),
                    _r(self.rotation[1][1]), _r(self.rotation[1][2]),
                    _r(-self.rotation[2]))


def _read_mesh_segments(path):
    """({naam: frozenset(knoop-id's)} van de SEG2/SEG3-elementen,
    {groep: [elementnamen]}) uit een mesh in ASTER-formaat
    (bridge_mesh.write_mesh: blokken 'SEG2' / 'GROUP_MA' tot 'FINSF',
    knopen 'N<id>')."""
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
    """Waarde van een tijdstabel [(t, v)] op tijdstip time: lineair
    tussen de punten, daarbuiten constant (manual v33 par. 9: "constant
    extrapolation")."""
    if time <= table[0][0]:
        return table[0][1]
    for (t0, v0), (t1, v1) in zip(table, table[1:]):
        if time <= t1:
            if t1 <= t0:
                return v1
            return v0 + (v1 - v0) * (time - t0) / (t1 - t0)
    return table[-1][1]


# Stap (graden) waarmee een RHO_CP-tabel verfijnd wordt (_refine_table).
_CP_TABLE_STEP = 10.0


def _refine_table(table, step):
    """Tabel [(T, v)] met tussenpunten (lineair geïnterpoleerd) zodat de
    afstand tussen twee punten met verschillende waarde <= step is.

    Gemeten (Code-Aster 17.4, verificatie WE-04b): THER_NON_LINE rekent met
    de enthalpie BETA uit RHO_CP, maar interpoleert BETA lineair tussen de
    tabelpunten van RHO_CP; tussen twee punten werkt dan de gemiddelde
    rho*cp van dat interval (energiebalans -2,8% met cp 450..750 J/kg/K op
    300/800/1300 K). Met punten om de 10 graden is BETA vrijwel exact.
    Een interval met gelijke waarden blijft één interval."""
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
    """Tekst voor een commentaarregel in de .comm: alleen ASCII, op een
    regel."""
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
    """IMPR_RESU MED (study.rmed) alleen met de instelling "med_export";
    Mecway krijgt de resultaten via de .liml."""
    if not CONFIG_BRIDGE.get("med_export", False):
        return "#-- geen MED-export (instelling med_export uit) --\n"
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
    Genereer study.comm en study.export voor een thermische analyse
    (THER_LINEAIRE, of THER_NON_LINE bij straling / schaalvlak-convectie).
    Returns het pad naar study.export, of None bij een fout.
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
    # Bewegende lasbron (#ASTER-LASBRON, bridge_welding.py)
    import bridge_welding
    welding = bridge_welding.apply(tb, model_data, analysis)
    if welding is None:
        return None
    weld_code, weld_excit, weld_post = welding
    # Metallurgie (#ASTER-METALLURGIE, bridge_metallurgy.py): META_ACIER in
    # de thermische materialen (tb.meta_kw), CALC_META na de solve
    import bridge_metallurgy
    meta = bridge_metallurgy.apply(tb, model_data, analysis)
    if meta is None:
        return None
    meta_pre, meta_post = meta
    if not (tb.transient or tb.temp_const or tb.temp_timed or tb.has_exchange):
        # Stationair zonder opgelegde temperatuur of warmte-uitwisseling:
        # de temperatuur is onbepaald (singuliere matrix).
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
        command, "transient" if tb.transient else "stationair",
        " - straling of convectie/straling op schaalvlakken" if tb.nonlinear
        else ""))

    # --- Oplossen ---
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
        # Toevoegmateriaal met THER_NL: THER_NON_LINE per geboortestap
        # (bridge_welding.ther_loop)
        skip = ("res = ", "    CHAM_MATER=", "    ETAT_INIT=", "    INCREMENT=",
                ")")
        solve_block = bridge_welding.ther_loop(
            tb, tb.fieldmat_affe,
            [line for line in solve if line and not line.startswith(skip)])

    # --- Keten thermisch -> mechanisch (Thermal stress in een T31-model,
    # bridge_thermomech.py): mechanische blokken en een eigen template ---
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

    # --- Nabewerking: warmteflux (FLUX_NOEU = -lambda grad T) ---
    # De energiecontrole van de lasbron vóór calc_champ_block: daar wordt een
    # gedraaid mesh (schalen) teruggedraaid. In de keten staat #ASTER-POST
    # na de mechanische solve (bridge_thermomech).
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
        # UTF-8 zoals de mechanische builders (bridge_to_aster._write_comm):
        # Code-Aster leest de .comm als UTF-8.
        template = bta._read_template(template_name)
        bta._write_comm(comm_path, template.format(
            defigroup_block=tb.defigroup_block(),
            model_block=tb.model_block(),
            materials_block=materials_block,
            fieldmat_block=fieldmat_block,
            funcs_block=("\n".join(tb.funcs) + "\n") if tb.funcs
            else "#-- geen functies --\n",
            listinst_block=listinst + initial,
            loads_block=loads_block or "#-- geen lasten --\n",
            solve_block=solve_block,
            calc_champ_block=calc,
            export_block=export_block,
            med_block=(bridge_thermomech.med_block() if mech
                       else _med_block()),
            **(mech or {})
        ))
        log("SUCCESS: .comm geschreven naar '{0}'.".format(comm_path))
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
        log("SUCCESS: .export geschreven naar '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren thermische solver-bestanden mislukt: {0}",
               "ERROR: Generating the thermal solver files failed: {0}")
            .format(str(e)))
    return None
