# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_thermomech.py
# Responsibility: the chain thermal -> mechanical (step S4b,
# welding: residual stress and distortion) in one job: first the transient
# thermal analysis of bridge_thermal.build_thermal (THER_LINEAIRE /
# THER_NON_LINE, with #ASTER-LASBRON), then STAT_NON_LINE with the
# temperature field as command variable.
#
# When: a Mecway model Thermal transient (T31, analysis ther_3d) with
# a Thermal stress (Mecway manual v33 par. 9.25; Mecway does not use it in
# a thermal analysis). The reference temperature of the
# Thermal stress is VALE_REF; the mechanical boundary conditions and loads
# (Fixed support, Displacement, ...) are in the same model (Mecway
# keeps them in a thermal analysis too; manual par. 17.10 computes a model
# this way, first thermal and then static). bridge_from_liml then reads them
# (model_data["thermo_mech"]).
#
# Material: E, nu, alpha and the plasticity of the Mecway material
# (BilinearIsotropic/-Kinematic, hardening curve). Mecway supports
# temperature dependence only for lambda and c (manual par. 8.6);
# E(T), nu(T), alpha(T), SY(T) and ET(T) via a line
#   #ASTER-MATERIAAL <Mecway-materiaal>: TC=(20, 600, 1200),
#   #ASTER-MATERIAAL     E=(210e9, 120e9, 20e9), SY=(355e6, 150e6, 10e6)
# (parse_materials; all values SI, temperatures T in K or TC in degrees
# C). See docs/Lassen.md par. 9.
#
# Code-Aster 17.4 (syntax source: test case hsnv100e, THER_LINEAIRE ->
# AFFE_MATERIAU AFFE_VARC EVOL -> STAT_NON_LINE with ECRO_LINE_FO;
# catalogues defi_materiau.py, affe_materiau.py, proj_champ.py):
#   - AFFE_VARC NOM_VARC='TEMP', EVOL=<thermal result>,
#     NOM_CHAM='TEMP', VALE_REF = reference temperature (degrees C: the
#     thermal computation is in Celsius, bridge_thermal);
#   - ELAS (constant) or ELAS_FO (functions of TEMP; ALPHA is then the
#     mean (secant) expansion coefficient relative to TEMP_DEF_ALPHA,
#     U4.43.01 ELAS_FO; recomputed in WE-09), ECRO_LINE / ECRO_LINE_FO (SY,
#     D_SIGM_EPSI = ET), TRACTION (hardening curve, constant in T);
#   - the mechanical time steps are the thermal ones (DEFI_LIST_INST on
#     'times', cutting on divergence; ARCHIVAGE on 'times', so that the
#     NUME_ORDRE of both results run in step for
#     aster_results_export).
#
#   enabled(model_data)            - chain active?
#   parse_materials(bodies)        - #ASTER-MATERIAAL lines
#   build_blocks(tb, md, analysis) - the mechanical .comm blocks
#   report_lines(mess_path)        - summary after the run (status box)
#
# Filler material that is born (#ASTER-LASBRON geboorte=, step S4c;
# model_data["welding_birth"] from bridge_welding._births): a quiet copy
# of the material (_materials, quiet: E and the hardening x QUIET) and
# STAT_NON_LINE per birth step (_birth_solve). docs/Lassen.md par. 10.
#
# Compatible with IronPython 2.7.9 (standard library only).

import re
from collections import OrderedDict

from bridge_utils import log, tr, CONFIG_BRIDGE

# Own template with the thermal and the mechanical solve.
TEMPLATE = "AsterTemplate_ThermoMeca.comm"

# Fields to Mecway if the user has not chosen a mechanical field on the
# Thermal page.
MECH_FIELDS = ["displacements", "stresses", "vonmises", "reactions",
               "plastic_strain", "plastic_strain_eq"]
_MECH_FIELD_SET = frozenset(MECH_FIELDS + ["velocities", "accelerations"])

KELVIN = 273.15

# Keys of #ASTER-MATERIAAL: name -> (synonyms)
_MAT_KEYS = OrderedDict([
    ("T", ("t", "temp")),
    ("TC", ("tc", "temp_c")),
    ("E", ("e",)),
    ("NU", ("nu",)),
    ("ALPHA", ("alpha",)),
    ("SY", ("sy",)),
    ("ET", ("et", "d_sigm_epsi")),
    ("H", ("h", "tangentmodulus")),
    ("T_ALPHA", ("t_alpha", "temp_def_alpha")),
    ("TC_ALPHA", ("tc_alpha",)),
    ("T_CUT", ("t_cut", "t_afkap")),
    ("TC_CUT", ("tc_cut", "tc_afkap")),
    ("HARDENING", ("versteviging", "hardening", "ecrouissage")),
])
_MAT_ALIAS = dict((a, k) for k, names in _MAT_KEYS.items() for a in names)
_TABLE_KEYS = ("E", "NU", "ALPHA", "SY", "ET", "H")


def enabled(model_data):
    """True if the chain thermal -> mechanical is active (T31 with a
    Thermal stress, bridge_from_liml)."""
    return bool(model_data.get("thermo_mech"))


def mech_fields(fields):
    """Fields for export_results: the chosen fields plus, without a
    mechanical field, MECH_FIELDS."""
    out = list(fields or [])
    if not any(f in _MECH_FIELD_SET for f in out):
        out += MECH_FIELDS
        log("INFO: Thermomechanical: no mechanical result field chosen; "
            "default {0}.".format(", ".join(MECH_FIELDS)))
    return out


# ==========================================
# #ASTER-MATERIAAL
# ==========================================
def _split(body):
    """Pieces separated by commas outside brackets."""
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _numbers(raw):
    """Number or list '(a, b, c)' / '[a, b, c]' -> [floats]."""
    text = raw.strip()
    if text[:1] in "([" and text[-1:] in ")]":
        text = text[1:-1]
    vals = [v.strip() for v in text.split(",") if v.strip()]
    if not vals:
        raise ValueError(raw)
    return [float(v.replace(" ", "")) for v in vals]


def _group(bodies):
    """Merge lines: a line '<name>: ...' starts a material; a line
    without a name (first ':' after a '=' or no ':') belongs to the
    previous one. Returns [(name, text)] or None (ERROR)."""
    out = []
    for body in bodies:
        text = body.strip()
        head, sep, rest = text.partition(":")
        if sep and "=" not in head:
            out.append([head.strip(), rest.strip()])
            continue
        if not out:
            log(tr("ERROR: #ASTER-MATERIAAL '{0}': verwacht '<Mecway-"
                   "materiaal>: sleutel=waarde, ...' (bijv. '#ASTER-"
                   "MATERIAAL Staal: TC=(20, 600), SY=(355e6, 150e6)').",
                   "ERROR: #ASTER-MATERIAL '{0}': expected '<Mecway "
                   "material>: key=value, ...' (e.g. '#ASTER-MATERIAL "
                   "Steel: TC=(20, 600), SY=(355e6, 150e6)').").format(text))
            return None
        prev = out[-1][1]
        # A list spanning two lines: join with a space.
        glue = " " if prev.count("(") + prev.count("[") > \
            prev.count(")") + prev.count("]") else ", "
        out[-1][1] = prev + glue + text if prev else text
    return [tuple(x) for x in out]


def parse_materials(bodies):
    """
    {Mecway material: spec} from the #ASTER-MATERIAAL lines; spec =
    {"T": [K, ...] (ascending) or None, "E"/"NU"/"ALPHA"/"SY"/"ET": [values]
    (1 value = constant, otherwise as many as T), "T_ALPHA": K or None,
    "kinematic": True/False/None}. None (ERROR in the log) on an error.
    """
    specs = OrderedDict()
    grouped = _group(bodies)
    if grouped is None:
        return None
    for name, text in grouped:
        label = "#ASTER-MATERIAAL {0}".format(name)
        spec = {"T": None, "T_ALPHA": None, "T_CUT": None,
                "kinematic": None}
        for part in _split(text):
            key, sep, raw = part.partition("=")
            k = _MAT_ALIAS.get(key.strip().lower())
            if not sep or k is None:
                log(tr("ERROR: {0}: onbekend of onvolledig '{1}'. Bekend: "
                       "{2}.",
                       "ERROR: {0}: unknown or incomplete '{1}'. Known: "
                       "{2}.").format(label, part, ", ".join(_MAT_KEYS)))
                return None
            raw = raw.strip()
            try:
                if k == "HARDENING":
                    low = raw.strip("'\"").lower()
                    if low in ("iso", "isotroop", "isotropic", "isotrope"):
                        spec["kinematic"] = False
                    elif low in ("kin", "kinematisch", "kinematic",
                                 "cinematique"):
                        spec["kinematic"] = True
                    else:
                        raise ValueError(raw)
                elif k in ("T", "TC"):
                    vals = _numbers(raw)
                    if k == "TC":
                        vals = [v + KELVIN for v in vals]
                    spec["T"] = vals
                elif k in ("T_ALPHA", "TC_ALPHA", "T_CUT", "TC_CUT"):
                    vals = _numbers(raw)
                    if len(vals) != 1:
                        raise ValueError(raw)
                    spec[k.replace("TC_", "T_")] = vals[0] + (
                        KELVIN if k.startswith("TC_") else 0.0)
                else:
                    spec[k] = _numbers(raw)
            except ValueError:
                log(tr("ERROR: {0}: '{1}' heeft geen geldige waarde (getal "
                       "in SI, of een lijst (a, b, ...); versteviging = iso "
                       "of kin).",
                       "ERROR: {0}: '{1}' has no valid value (number in "
                       "SI, or a list (a, b, ...); hardening = iso or "
                       "kin).").format(label, key.strip()))
                return None
        if not _check_spec(spec, label):
            return None
        specs[name] = spec
    return specs


def _check_spec(spec, label):
    def err(nl, en, *args):
        log(tr("ERROR: {0}: " + nl, "ERROR: {0}: " + en).format(label, *args))
        return False
    temps = spec["T"]
    lists = [k for k in _TABLE_KEYS if k in spec and len(spec[k]) > 1]
    if lists and temps is None:
        return err("lijsten voor {1} vragen de temperaturen T=(..) [K] of "
                   "TC=(..) [graden C].",
                   "lists for {1} need the temperatures T=(..) [K] or "
                   "TC=(..) [degrees C].", ", ".join(lists))
    if temps is not None:
        if any(b <= a for a, b in zip(temps, temps[1:])):
            return err("de temperaturen moeten oplopen.",
                       "the temperatures must increase.")
        if min(temps) <= 0.0:
            return err("temperatuur <= 0 K (T in kelvin, of TC in graden C).",
                       "temperature <= 0 K (T in kelvin, or TC in degrees "
                       "C).")
        for k in lists:
            if len(spec[k]) != len(temps):
                return err("{1} heeft {2} waarden, T heeft er {3}.",
                           "{1} has {2} values, T has {3}.", k,
                           len(spec[k]), len(temps))
    for k in ("E", "SY"):
        if k in spec and min(spec[k]) <= 0.0:
            return err("{1} moet > 0 zijn.", "{1} must be > 0.", k)
    for k in ("ET", "H"):
        if k in spec and min(spec[k]) < 0.0:
            return err("{1} moet >= 0 zijn.", "{1} must be >= 0.", k)
    if "ET" in spec and "H" in spec:
        return err("geef H (plastische modulus, Mecway 'Tangent modulus') "
                   "of ET (helling in totale rek, Code-Aster D_SIGM_EPSI), "
                   "niet allebei.",
                   "give H (plastic modulus, Mecway 'Tangent modulus') or "
                   "ET (slope in total strain, Code-Aster D_SIGM_EPSI), not "
                   "both.")
    if "NU" in spec and not all(-1.0 < v < 0.5 for v in spec["NU"]):
        return err("NU moet tussen -1 en 0,5 liggen.",
                   "NU must be between -1 and 0.5.")
    return True


def _table(spec, key, const):
    """[(T_K, value)] of a property: the list from spec, a
    constant (1 value in spec, or the Mecway value const) as [(None,
    v)]."""
    vals = spec.get(key) if spec else None
    if vals is None:
        return [(None, const)]
    if len(vals) == 1:
        return [(None, vals[0])]
    return list(zip(spec["T"], vals))


def _slope_table(spec, e_tab, bil):
    """D_SIGM_EPSI(T) (slope after the yield point in total strain): ET
    from spec, or from the plastic modulus H (spec, otherwise the Mecway
    material: Mecway's 'Tangent modulus' is H, bridge_from_liml.
    _parse_bilinear) as ET = E H / (E + H), per temperature point of E and
    H (linear in between, like every table)."""
    if spec and "ET" in spec:
        return _table(spec, "ET", 0.0)
    if spec and "H" in spec:
        h_tab = _table(spec, "H", 0.0)
    else:
        bil = bil or {}
        h = bil.get("h")
        if h is None:
            # _kinematic_curve returns only et (at the Mecway E)
            et = bil.get("et", 0.0)
            e0 = _value_at(e_tab, e_tab[0][0] or 0.0)
            h = e0 * et / (e0 - et) if e0 > et else 0.0
        h_tab = [(None, h)]
    temps = sorted(set(t for t, _v in e_tab + h_tab if t is not None))

    def et_at(t):
        e_t, h_t = _value_at(e_tab, t), _value_at(h_tab, t)
        return e_t * h_t / (e_t + h_t) if h_t > 0.0 else 0.0
    if not temps:
        return [(None, et_at(0.0))]
    return [(t, et_at(t)) for t in temps]


def _cut_alpha(a_tab, t_def, t_cut):
    """Secant alpha with thermal strain constant above t_cut (melting:
    liquid has no stiffness; without the cut-off the strain keeps growing
    linearly above the melting temperature, e.g. 4.6% at 3400 K, and
    STAT_NON_LINE converges poorly, WE-10b). eps_th(T) = alpha(T) (T -
    t_def) up to t_cut, above it eps_cut: alpha(T) = eps_cut / (T - t_def),
    in points with 2% growth of T - t_def up to t_cut + 10 000 K (linear
    interpolation: relative error on eps_th < 1e-4)."""
    pts = [(t, v) for t, v in a_tab if t is not None and t < t_cut]
    a_cut = _value_at(a_tab, t_cut)
    eps_cut = a_cut * (t_cut - t_def)
    out = pts + [(t_cut, a_cut)]
    d = t_cut - t_def
    while out[-1][0] < t_cut + 1.0e4:
        d *= 1.02
        out.append((t_def + d, eps_cut / d))
    return out


def _is_const(table):
    return table[0][0] is None


def _value_at(table, t_k):
    """Linearly interpolated, constant outside the table."""
    if _is_const(table):
        return table[0][1]
    if t_k <= table[0][0]:
        return table[0][1]
    for (t0, v0), (t1, v1) in zip(table, table[1:]):
        if t_k <= t1:
            return v0 + (v1 - v0) * (t_k - t0) / (t1 - t0)
    return table[-1][1]


# ==========================================
# .COMM BLOCKS
# ==========================================
def _r(x):
    import bridge_mesh
    return bridge_mesh._real(float(x))


def _func(concept, table):
    """DEFI_FONCTION of TEMP (degrees C, PROL constant like Mecway's own
    tables, manual par. 8.6) or DEFI_CONSTANTE."""
    if _is_const(table):
        return "{0} = DEFI_CONSTANTE(VALE={1})".format(concept,
                                                       _r(table[0][1]))
    return ("{0} = DEFI_FONCTION(NOM_PARA='TEMP', VALE=(\n    {1},\n), "
            "PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')").format(
                concept, ",\n    ".join("{0}, {1}".format(
                    _r(t - KELVIN), _r(v)) for t, v in table))


def _tref(model_data):
    """Reference temperature [K] (Thermal stress)."""
    return (model_data.get("thermal_stress") or {}).get("tref", 0.0)


def _check_reference(tb, model_data, tref):
    """WARNING if the initial temperature is not uniformly equal to the
    reference temperature (then there is already thermal strain at t = 0)."""
    th = tb.th
    values = set(round(v, 9) for _s, _k, v in th.get("initial", []))
    if not values:
        values = set([0.0])
    if values != set([round(tref, 9)]):
        log(tr("WARNING: Thermomechanisch: de referentietemperatuur van "
               "Thermal stress ({0} K) is niet de begintemperatuur ({1} K): "
               "op t = 0 is er dan al thermische rek, die Code-Aster in de "
               "eerste stap als last opbrengt (alarm MECANONLINE2_97 "
               "mogelijk). Maak ze gelijk.",
               "WARNING: Thermomechanical: the reference temperature of "
               "Thermal stress ({0} K) is not the initial temperature ({1} "
               "K): at t = 0 there is already thermal strain, which "
               "Code-Aster applies as a load in the first step (alarm "
               "MECANONLINE2_97 possible). Make them equal.").format(
                   "%.6g" % tref, ", ".join("%.6g" % v
                                            for v in sorted(values))))


def _check_elements(tb, model_data):
    """Volume elements only, and every mechanical elset also thermal.
    False (ERROR) otherwise."""
    mods = model_data.get("elset_modelisations", {})
    other = sorted(e for e, m in mods.items() if m not in ("3D", "3D_SI"))
    if other or model_data.get("poi1_groups") or model_data.get("discretes"):
        log(tr("ERROR: Thermomechanisch (Thermal stress in een thermisch "
               "model): alleen volume-elementen; elsets {0} (schalen, "
               "balken, veren) kan de keten niet rekenen. Zie "
               "docs/Lassen.md par. 9.",
               "ERROR: Thermomechanical (Thermal stress in a thermal "
               "model): solid elements only; elsets {0} (shells, beams, "
               "springs) cannot be computed by the chain. See "
               "docs/en/Welding.md sec. 9.").format(
                   ", ".join(other) or "POI1"))
        return False
    missing = sorted(e for e in mods if e not in tb.elsets)
    if missing:
        log(tr("ERROR: Thermomechanisch: elset(s) {0} hebben geen thermisch "
               "materiaal en dus geen temperatuur; geef ze in Mecway een "
               "warmtegeleiding.",
               "ERROR: Thermomechanical: elset(s) {0} have no thermal "
               "material and hence no temperature; give them a thermal "
               "conductivity in Mecway.").format(", ".join(missing)))
        return False
    return True


def _materials(md, specs, tref, analysis, quiet=None):
    """
    (DEFI_MATERIAU block, {mat: concept}, with_plastic) or None (ERROR).
    Sets "plastic_bilinear" in md["materials"][mat] for an
    #ASTER-MATERIAAL with SY, so that _relation_for (bridge_to_aster)
    chooses VMIS_ISOT_LINE / VMIS_CINE_LINE.
    quiet (filler material, build_blocks): {"mats": {material: group},
    "quiet": factor, "blocks": {}, "concepts": {}}; for those materials
    _materials fills "blocks" (DEFI_MATERIAU of the quiet copy <MAT_n>_Q,
    without the TRACTION curve: _quiet_block) and "concepts".
    """
    import bridge_to_aster as bta
    import bridge_metallurgy
    meta_mech = bridge_metallurgy.mech_specs(md)
    used = OrderedDict()
    for elset, mat in md.get("elsets", {}).items():
        if elset in md.get("elset_modelisations", {}):
            used[mat] = True
    for name in specs:
        if name not in md["materials"]:
            log(tr("ERROR: #ASTER-MATERIAAL '{0}': geen (mechanisch) "
                   "materiaal met die naam in het model. Materialen: {1}.",
                   "ERROR: #ASTER-MATERIAL '{0}': no (mechanical) material "
                   "with that name in the model. Materials: {1}.").format(
                       name, ", ".join(md["materials"])))
            return None
        if name not in used:
            log(tr("WARNING: #ASTER-MATERIAAL '{0}': materiaal niet "
                   "gebruikt door een volume-elset; genegeerd.",
                   "WARNING: #ASTER-MATERIAL '{0}': material not used by "
                   "a solid elset; ignored.").format(name))
    concepts = bta._material_concepts(md)
    out = []
    for mat in used:
        if mat not in md["materials"]:
            continue
        props = md["materials"][mat]
        spec = specs.get(mat)
        concept = concepts[mat]
        label = "materiaal '{0}'".format(mat)
        tab = {
            "E": _table(spec, "E", props["E"]),
            "NU": _table(spec, "NU", props["NU"]),
            "ALPHA": _table(spec, "ALPHA", props.get("Texp", 0.0)),
        }
        bil = props.get("plastic_bilinear")
        has_slope = spec and ("ET" in spec or "H" in spec)
        if (spec and "SY" in spec) or (has_slope and bil):
            if props.get("plastic_curve") and "SY" in spec:
                log(tr("WARNING: #ASTER-MATERIAAL '{0}': SY vervangt de "
                       "hardingscurve van het Mecway-materiaal.",
                       "WARNING: #ASTER-MATERIAL '{0}': SY replaces the "
                       "hardening curve of the Mecway material.").format(mat))
                props.pop("plastic_curve", None)
            kin = spec["kinematic"]
            if kin is None:
                kin = bool(bil and bil.get("kinematic"))
            tab["SY"] = _table(spec, "SY", (bil or {}).get("sy", 0.0))
            tab["ET"] = _slope_table(spec, tab["E"], bil)
            bil = {"sy": _value_at(tab["SY"], tref),
                   "et": _value_at(tab["ET"], tref), "kinematic": kin}
            props["plastic_bilinear"] = bil
        elif has_slope:
            log(tr("ERROR: #ASTER-MATERIAAL '{0}': H/ET zonder SY, en het "
                   "Mecway-materiaal is niet bilineair plastisch.",
                   "ERROR: #ASTER-MATERIAL '{0}': H/ET without SY, and the "
                   "Mecway material is not bilinear plastic.").format(mat))
            return None
        elif bil:
            if not _is_const(tab["E"]):
                tab["SY"] = [(None, bil["sy"])]
                tab["ET"] = _slope_table({}, tab["E"], bil)
            else:
                tab["SY"] = [(None, bil["sy"])]
                tab["ET"] = [(None, bil["et"])]
            if spec and spec["kinematic"] is not None:
                bil = dict(bil, kinematic=spec["kinematic"])
                props["plastic_bilinear"] = bil
        # Checks over the temperature range of the tables
        temps = sorted(set(t for v in tab.values() for t, _x in v
                           if t is not None)) or [tref]
        for t_k in temps:
            e_t = _value_at(tab["E"], t_k)
            if "ET" in tab and _value_at(tab["ET"], t_k) >= e_t:
                log(tr("ERROR: {0}: ET >= E bij {1} K; de tangentmodulus "
                       "moet kleiner zijn dan E.",
                       "ERROR: {0}: ET >= E at {1} K; the tangent modulus "
                       "must be smaller than E.").format(label, "%.6g" % t_k))
                return None
        if all(abs(v) == 0.0 for _t, v in tab["ALPHA"]):
            log(tr("WARNING: Thermomechanisch: materiaal '{0}' heeft geen "
                   "thermische uitzettingscoefficient (Mecway: Mechanical, "
                   "Thermal expansion coefficient; of ALPHA in "
                   "#ASTER-MATERIAAL): geen thermische rek, dus geen "
                   "spanningen uit de temperatuur.",
                   "WARNING: Thermomechanical: material '{0}' has no "
                   "thermal expansion coefficient (Mecway: Mechanical, "
                   "Thermal expansion coefficient; or ALPHA in "
                   "#ASTER-MATERIAL): no thermal strain, hence no stresses "
                   "from the temperature.").format(mat))
        t_alpha = (spec or {}).get("T_ALPHA")
        if t_alpha is None:
            t_alpha = tref
        t_cut = (spec or {}).get("T_CUT")
        if t_cut is not None:
            if t_cut <= t_alpha:
                log(tr("ERROR: {0}: T_CUT ({1} K) moet boven de "
                       "referentietemperatuur van alpha ({2} K) liggen.",
                       "ERROR: {0}: T_CUT ({1} K) must be above the "
                       "reference temperature of alpha ({2} K).").format(
                           label, "%.6g" % t_cut, "%.6g" % t_alpha))
                return None
            tab["ALPHA"] = _cut_alpha(tab["ALPHA"], t_alpha, t_cut)
        if mat in meta_mech:
            # Metallurgical law (#ASTER-METALLURGIE mechanica=ja,
            # bridge_metallurgy.py): ELAS_META_FO + META_ECRO_LINE
            block = bridge_metallurgy.mech_material(
                concept, mat, meta_mech[mat], tab, tref, t_alpha, t_cut,
                label)
            if block is None:
                return None
            out.append(bta._mat_comment(mat).rstrip("\n") + "\n" + block)
            continue
        fo = any(not _is_const(v) for v in (tab["E"], tab["NU"],
                                            tab["ALPHA"]))

        def render(name, scale, trac):
            """DEFI_MATERIAU lines of this material as concept name; E
            and the hardening x scale (quiet filler material, S4c: E x
            QUIET and ET x QUIET, yield stress equal, so that the quiet
            element stays elastic; TRACTION: trac = the curve with strain
            / QUIET, like bridge_failure.weak_materials)."""
            e_tab = [(t, v * scale) for t, v in tab["E"]]
            out_lines = [bta._mat_comment(mat).rstrip("\n")]
            if scale != 1.0:
                out_lines.append("# quiet filler material (not born yet): "
                                 "E x {0}".format(_r(scale)))
            if fo:
                t_alpha_c = t_alpha - KELVIN
                for k, t in (("E", e_tab), ("NU", tab["NU"]),
                             ("ALPHA", tab["ALPHA"])):
                    out_lines.append(_func("{0}_{1}".format(name, k), t))
                out_lines.append(_func("{0}_RHO".format(name),
                                       [(None, props.get("rho", 0.0))]))
                # ALPHA in ELAS_FO: mean (secant) coefficient relative to
                # TEMP_DEF_ALPHA; Code-Aster computes eps_th = alpha(T) (T -
                # T_def) - alpha(T_ref) (T_ref - T_def) (U4.43.01 ELAS_FO; the
                # second term NOT verified); with T_def = T_ref
                # (default) alpha(T) (T - T_ref), recomputed in WE-09
                # (4e-8).
                elas = ("    ELAS_FO=_F(E={0}_E, NU={0}_NU, RHO={0}_RHO, "
                        "ALPHA={0}_ALPHA, TEMP_DEF_ALPHA={1}),\n").format(
                            name, _r(t_alpha_c))
            else:
                elas = ("    ELAS=_F(E={0}, NU={1}, RHO={2}, ALPHA={3}),\n"
                        .format(_r(e_tab[0][1]), _r(tab["NU"][0][1]),
                                _r(props.get("rho", 0.0)),
                                _r(tab["ALPHA"][0][1])))
            ext = ""
            if "SY" in tab:
                et_tab = [(t, v * scale) for t, v in tab["ET"]]
                if _is_const(tab["SY"]) and _is_const(et_tab):
                    ext = ("    ECRO_LINE=_F(D_SIGM_EPSI={0}, SY={1}),\n"
                           .format(_r(et_tab[0][1]), _r(tab["SY"][0][1])))
                else:
                    out_lines.append(_func("{0}_SY".format(name), tab["SY"]))
                    out_lines.append(_func("{0}_ET".format(name), et_tab))
                    ext = ("    ECRO_LINE_FO=_F(D_SIGM_EPSI={0}_ET, "
                           "SY={0}_SY),\n").format(name)
            elif props.get("plastic_curve"):
                # Hardening curve (TRACTION, _build_plastic_curves_block):
                # constant in T.
                ext = "    TRACTION=_F(SIGM={0}),\n".format(trac)
            out_lines.append("{0} = DEFI_MATERIAU(\n{1}{2})".format(
                name, elas, ext))
            return out_lines, ext
        lines, extra = render(concept, 1.0,
                              concept.replace("MAT_", "TRAC_", 1))
        out.append("\n".join(lines))
        if quiet is not None and mat in quiet["mats"]:
            q_lines, _ext = render(concept + "_Q", quiet["quiet"],
                                   concept.replace("MAT_", "TRAC_", 1) + "_Q")
            quiet["blocks"][mat] = "\n".join(q_lines)
            quiet["concepts"][mat] = concept + "_Q"
        if "ECRO_LINE_FO" in extra:
            plast = ", ECRO_LINE_FO (SY, ET as a function of T)"
        elif "ECRO_LINE" in extra:
            plast = ", ECRO_LINE"
        elif extra:
            plast = ", TRACTION (hardening curve)"
        else:
            plast = ", elastic"
        log("INFO: Thermomechanical: {0}: {1}{2}{3}.".format(
            label, "ELAS_FO (E, nu, alpha as a function of T)" if fo
            else "ELAS", plast,
            "" if not spec else " (#ASTER-MATERIAAL, T_ref = {0} K)".format(
                "%.6g" % tref)))
    return "\n\n".join(out) + "\n", concepts, list(used)


def _fieldmat(md, concepts, tref, projected, quiet=None):
    """AFFE_MATERIAU (fieldmat) with the temperature as command variable.
    With filler material (quiet): the quiet material on the elements that
    are still to be born (after the elsets: the last assignment counts,
    U4.43.03). Returns (text, [AFFE entries], AFFE_VARC text)."""
    entries = []
    for elset, mat in md.get("elsets", {}).items():
        if elset in md.get("elset_modelisations", {}) and mat in concepts:
            entries.append("_F(GROUP_MA='{0}', MATER={1})".format(
                elset, concepts[mat]))
    if quiet:
        for mat, grp in quiet["mats"].items():
            if mat in quiet["concepts"]:
                entries.append("_F(GROUP_MA='{0}', MATER={1})".format(
                    grp, quiet["concepts"][mat]))
    evol = "res_tm" if projected else "res_ther"
    # Phases (META_ELNO) as command variable M_ACIER (#ASTER-METALLURGIE
    # mechanica=ja, bridge_metallurgy.varc_entries); AFFE_VARC as a tuple.
    import bridge_metallurgy
    varc_list = ["_F(TOUT='OUI', NOM_VARC='TEMP', EVOL={0}, NOM_CHAM='TEMP', "
                 "VALE_REF={1})".format(evol, _r(tref - KELVIN))] + \
        bridge_metallurgy.varc_entries(md, "res_ther")
    varc = "(\n        {0},\n    )".format(",\n        ".join(varc_list))
    text = ("fieldmat = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n    MODELE=model,"
            "\n    AFFE=(\n{0}\n    ),\n    AFFE_VARC={1},\n)\n").format(
                "\n".join("        " + e + "," for e in entries), varc)
    return text, entries, varc


def _quiet_block(md, quiet):
    """Quiet materials of the filler material (after the hardening curves:
    a TRACTION curve gets a quiet copy with strain / QUIET, like
    bridge_failure.weak_materials)."""
    out = []
    q = quiet["quiet"]
    curves = md.get("_traction_curves", {})
    for mat, text in quiet["blocks"].items():
        if "TRACTION=" in text and mat in curves:
            name = quiet["concepts"][mat].replace("MAT_", "TRAC_", 1)
            out.append(
                "{0} = DEFI_FONCTION(\n    NOM_PARA='EPSI',\n    "
                "NOM_RESU='SIGM',\n    VALE=({1}),\n    PROL_DROITE="
                "'LINEAIRE',\n    PROL_GAUCHE='CONSTANT',\n)".format(
                    name, ",\n          ".join(
                        "{0}, {1}".format(_r(e / q), _r(sg))
                        for e, sg in curves[mat])))
        out.append(text)
    return "\n".join(out) + "\n" if out else ""


# Summary in the job (after CALC_CHAMP): lines 'BRIDGE_THERMOMECA
# <key> <value>' in the .mess (report_lines). An error here must not stop
# the job.
_REPORT = '''# Thermomechanical summary (bridge_thermomech): residual stress and
# deformation at the last time, lines BRIDGE_THERMOMECA in the .mess.
def _bridge_tm_report(res, res_ther, n_nodes):
    import numpy as np
    out = []
    try:
        acc = res.getAccessParameters()
        idx, t = acc['NUME_ORDRE'][-1], acc['INST'][-1]
        out.append(('t', t))
        acc_t = res_ther.getAccessParameters()
        ok = list(acc_t['INST'][:len(acc['INST'])]) == list(acc['INST'])
        if not ok:
            print('BRIDGE_THERMOMECA_TIJDEN', len(acc['INST']),
                  len(acc_t['INST']))
        idx_t = acc_t['NUME_ORDRE'][acc_t['INST'].index(t)] \\
            if t in acc_t['INST'] else acc_t['NUME_ORDRE'][-1]

        def vals(r, name, i):
            sf = r.getField(name, i).toSimpleFieldOnNodes()
            v, m = sf.getValues()
            return list(sf.getComponents()), v[:n_nodes], m[:n_nodes]
        c, v, m = vals(res_ther, 'TEMP', idx_t)
        k = c.index('TEMP')
        out += [('T_min', float(v[m[:, k], k].min()) + 273.15),
                ('T_max', float(v[m[:, k], k].max()) + 273.15)]
        c, v, m = vals(res, 'DEPL', idx)
        uu = np.zeros(v.shape[0])
        for name in ('DX', 'DY', 'DZ'):
            k = c.index(name)
            out += [(name + '_min', float(v[m[:, k], k].min())),
                    (name + '_max', float(v[m[:, k], k].max()))]
            uu += np.where(m[:, k], v[:, k], 0.0) ** 2
        out.append(('U_max', float(np.sqrt(uu.max()))))
        c, v, m = vals(res, 'SIGM_NOEU', idx)
        for name in ('SIXX', 'SIYY', 'SIZZ'):
            k = c.index(name)
            out += [(name + '_min', float(v[m[:, k], k].min())),
                    (name + '_max', float(v[m[:, k], k].max()))]
        c, v, m = vals(res, 'SIEQ_NOEU', idx)
        k = c.index('VMIS')
        out.append(('VMIS_max', float(v[m[:, k], k].max())))
        if '{p_cmp}' and 'VARI_NOEU' in res.getFieldsNames():
            c, v, m = vals(res, 'VARI_NOEU', idx)
            k = c.index('{p_cmp}')
            out.append(('P_max', float(v[m[:, k], k].max())))
            vmax = 0.0
            for i in acc['NUME_ORDRE']:
                c, v, m = vals(res, 'VARI_NOEU', i)
                vmax = max(vmax, float(v[m[:, k], k].max()))
            out.append(('P_max_all', vmax))
    except Exception as exc:
        print('BRIDGE_THERMOMECA_FOUT', repr(exc))
    for key, value in out:
        print('BRIDGE_THERMOMECA %s %r' % (key, value))
_bridge_tm_report(res, res_ther, {n_nodes})
'''


def _birth_solve(birth, concepts, entries, varc, call, with_plastic):
    """
    STAT_NON_LINE with filler material that is born (#ASTER-LASBRON
    geboorte=, bridge_welding._births; step S4c). Per birth step k
    (elements alive from times[k]):
      1. STAT_NON_LINE up to times[k-1] with the current material (quiet
         elements: E x QUIET, _materials);
      2. a new AFFE_MATERIAU with the born elements on their normal
         material (after the quiet assignment: the last one counts);
      3. the next STAT_NON_LINE starts from the state at times[k-1] with
         stress and internal variables of the new elements at zero
         (ETAT_INIT DEPL/SIGM/VARI, CREA_CHAMP ASSE like bridge_failure)
         and NEWTON PREDICTION='ELASTIQUE' (as after failure).
    The element is thus stress-free in its deformed position at the
    temperature of times[k-1]: after that only the strain and the thermal
    strain from there count (the relations are incremental; with the new
    AFFE_MATERIAU E- = E+ in the first step). Seen in a prototype
    (Code-Aster 17.4, bar WE-12): shrinkage stress after birth at T0 +
    100 K and cooling E alpha 100 K to 1e-4, also with VMIS_ISOT_LINE.
    call: dict with excit, comp, solveur, reac, rech, conv (text as in
    build_blocks).
    """
    import bridge_welding
    return (
        "# --- Filler material (bridge_thermomech._birth_solve): "
        "STAT_NON_LINE per birth step ---\n"
        "_gm_affe = [\n    {affe},\n]\n"
        "{born}"
        "_gm_t = list(times.getValues())\n"
        "_gm_alive = []\n"
        "_gm_new = []\n"
        "_gm_start = 0\n"
        "res = None\n"
        "try:\n"
        "    for _gm_k in sorted(_gm_born) + [len(_gm_t)]:\n"
        "        _gm_stop = min(_gm_k - 1, len(_gm_t) - 1)\n"
        "        if _gm_stop > _gm_start:\n"
        "            _gm_fm = AFFE_MATERIAU(MAILLAGE=mesh, MODELE=model, AFFE=tuple(\n"
        "                _gm_affe + [_F(GROUP_MA=_g, MATER=_m) for _g, _m in "
        "_gm_alive]),\n"
        "                AFFE_VARC={varc})\n"
        "            _gm_pred = 'TANGENTE'\n"
        "            _gm_kw = {{}}\n"
        "            if res is not None and _gm_new:\n"
        "                # newly born: stress and internal variables to zero\n"
        "                _gm_last = res.getLastIndex()\n"
        "                _gm_s = res.getField('SIEF_ELGA', _gm_last)\n"
        "                _gm_ei = dict(DEPL=res.getField('DEPL', _gm_last), "
        "SIGM=CREA_CHAMP(\n"
        "                    OPERATION='ASSE', TYPE_CHAM='ELGA_SIEF_R', "
        "MODELE=model, PROL_ZERO='OUI',\n"
        "                    ASSE=(_F(CHAM_GD=_gm_s, TOUT='OUI'),\n"
        "                          _F(CHAM_GD=_gm_s, GROUP_MA=tuple(_gm_new), "
        "COEF_R=0.0))))\n"
        "{vari}"
        "                _gm_kw = dict(reuse=res, RESULTAT=res, "
        "ETAT_INIT=_F(**_gm_ei))\n"
        "                _gm_pred = 'ELASTIQUE'\n"
        "            elif res is not None:\n"
        "                _gm_kw = dict(reuse=res, RESULTAT=res, "
        "ETAT_INIT=_F(EVOL_NOLI=res))\n"
        "            res = STAT_NON_LINE(\n"
        "                MODELE=model,\n"
        "                CHAM_MATER=_gm_fm,\n"
        "{excit}\n"
        "{comp}"
        "                INCREMENT=_F(LIST_INST=listinst, "
        "INST_INIT=_gm_t[_gm_start],\n"
        "                             INST_FIN=_gm_t[_gm_stop]),\n"
        "                ARCHIVAGE=_F(LIST_INST=times),\n"
        "{solveur}"
        "                NEWTON=_F(REAC_ITER={reac}, PREDICTION=_gm_pred),\n"
        "{rech}"
        "                CONVERGENCE=_F({conv}),\n"
        "                **_gm_kw)\n"
        "            _gm_start = _gm_stop\n"
        "            _gm_new = []\n"
        "        if _gm_k < len(_gm_t):\n"
        "            _gm_alive += _gm_born[_gm_k]\n"
        "            _gm_new += [_g for _g, _m in _gm_born[_gm_k]]\n"
        "except Exception as err:\n"
        "    if not str(getattr(err, 'id_message', '')).startswith("
        "'MECANONLINE'):\n"
        "        raise\n"
        "    print('BRIDGE_ONVOLLEDIG', res.getAccessParameters()['INST'][-1])\n"
        "print('BRIDGE_GEBOORTE_MECA %d' % len(_gm_alive))\n"
        "t_res = res.getAccessParameters()['INST'][-1]\n").format(
            affe=",\n    ".join(entries),
            born=bridge_welding.birth_loop_data(birth, concepts, "_gm"),
            varc=varc,
            vari=(
                "                _gm_v = res.getField('VARI_ELGA', _gm_last)\n"
                "                _gm_ei['VARI'] = CREA_CHAMP(\n"
                "                    OPERATION='ASSE', TYPE_CHAM='ELGA_VARI_R', "
                "MODELE=model, PROL_ZERO='OUI',\n"
                "                    ASSE=(_F(CHAM_GD=_gm_v, TOUT='OUI'),\n"
                "                          _F(CHAM_GD=_gm_v, GROUP_MA=tuple("
                "_gm_new), COEF_R=0.0)))\n" if with_plastic else ""),
            **call)


def build_blocks(tb, model_data, analysis):
    """
    The mechanical blocks for TEMPLATE (dict placeholder -> text), or
    None (ERROR in the log). tb: the thermal builder
    (bridge_thermal._Thermal), na apply_loads.
    """
    import bridge_to_aster as bta
    if not tb.transient:
        log(tr("ERROR: Thermomechanisch vraagt een transiente thermische "
               "analyse (Mecway Thermal transient, T31).",
               "ERROR: Thermomechanical needs a transient thermal analysis "
               "(Mecway Thermal transient, T31)."))
        return None
    if not _check_elements(tb, model_data):
        return None
    tref = _tref(model_data)
    _check_reference(tb, model_data, tref)
    specs = parse_materials(model_data.get("aster_custom", {}).get(
        "materials", []))
    if specs is None:
        return None
    # Own copy: the mechanical helper functions of bridge_to_aster set
    # keys in model_data; the thermal parts stay untouched.
    # #ASTER code and #ASTER-EXCIT belong to the thermal part
    # (bridge_thermal); the chain does not compute contact and couplings.
    md = dict(model_data)
    md["materials"] = OrderedDict((k, dict(v)) for k, v in
                                  model_data["materials"].items())
    custom = dict(model_data.get("aster_custom", {}))
    custom["code"], custom["excit"] = [], []
    md["aster_custom"] = custom
    md["couplings"], md["contacts"] = [], []
    if not bta._check_materials(md, analysis):
        return None
    # bonded contact with a skewed/curved shell: NPREC = -1
    analysis = bta.bonded_nprec(md, analysis)
    # LINE_QUAD (Elements page): the mechanical mesh becomes quadratic;
    # the temperature field then goes to the new mesh with PROJ_CHAMP.
    bta._resolve_line_quad(md)
    projected = bool(md.get("line_quad"))
    import bridge_metallurgy
    meta_mech = bridge_metallurgy.mech_specs(md)
    if not bridge_metallurgy.check_chain(md, projected):
        return None
    # Filler material that is born (#ASTER-LASBRON geboorte=,
    # bridge_welding._births): a quiet copy of the material
    birth = model_data.get("welding_birth")
    quiet = None
    if birth:
        quiet = {"mats": birth["mats"], "quiet": birth["quiet"],
                 "blocks": OrderedDict(), "concepts": {}}
    mats = _materials(md, specs, tref, analysis, quiet)
    if mats is None:
        return None
    materials_block, concepts, used = mats
    try:
        curves_block, _func_map = bta._build_plastic_curves_block(md,
                                                                  analysis)
    except ValueError as e:
        log(tr("ERROR: Hardingscurve ongeldig voor Code-Aster TRACTION: "
               "{0}",
               "ERROR: Hardening curve invalid for Code-Aster TRACTION: "
               "{0}").format(str(e)))
        return None
    with_plastic = any(bta._relation_for(md, m) != "ELAS" or m in meta_mech
                       for m in used)
    if with_plastic:
        # Linear hex8 'locks' in plastic flow (WE-10: with '3D' up to
        # 1.3-2.6 x SY in the weld; LINE_QUAD advice).
        bta._warn_plastic_hex8(md, [])

    # Loads and boundary conditions (as _build_nonlin_static)
    md["_follower_groups"] = bta._follower_pressure_groups(md, analysis)
    md["_follower_rotation"] = bta._follower_rotation(md, analysis,
                                                      "STAT_NON_LINE")
    load_funcs = bta._collect_load_funcs(md)
    charges = bta._build_charges(md, bta._load_func_names(md))
    loads_block, excit_clause = bta._render_charges(charges, md)
    if not excit_clause:
        log(tr("ERROR: Thermomechanisch zonder mechanische randvoorwaarden: "
               "het model ligt niet vast. Zet in Mecway Fixed support of "
               "Displacement op het model (minstens de zes starre "
               "bewegingen; bij een vrij uitzettend deel statisch bepaald, "
               "docs/Lassen.md par. 9).",
               "ERROR: Thermomechanical without mechanical constraints: the "
               "model is not held. Put Fixed support or Displacement on the "
               "model in Mecway (at least the six rigid-body motions; for "
               "a part that expands freely, statically determinate, "
               "docs/en/Welding.md sec. 9)."))
        return None
    comportement = bridge_metallurgy.patch_comportement(
        bta._build_comportement_block(md, analysis), md)

    pre = "res_ther = res\ndel res\n"
    defigroup = pre + "mesh_th = mesh\n" + bta._build_defigroup_block(md)
    if projected:
        defigroup += (
            "\n# Temperature field to the quadratic mesh (LINE_QUAD): "
            "midside nodes linear\n# between the corner nodes, as in the "
            "linear element (PROJ_CHAMP COLLOCATION)\n"
            "res_tm = PROJ_CHAMP(RESULTAT=res_ther, MAILLAGE_1=mesh_th, "
            "MAILLAGE_2=mesh, METHODE='COLLOCATION', NOM_CHAM='TEMP', "
            "TOUT_ORDRE='OUI')\n")
    listinst = (
        "# Mechanical steps = the thermal times; on divergence "
        "cut the step (ECHEC DECOUPE)\n"
        "listinst = DEFI_LIST_INST(\n"
        "    DEFI_LIST=_F(LIST_INST=times),\n"
        "    ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE',\n"
        "             SUBD_METHODE='MANUEL', SUBD_PAS=4, SUBD_NIVEAU=6),\n"
        ")\n")
    solve = (
        "try:\n"
        "    res = STAT_NON_LINE(\n"
        "        MODELE=model,\n"
        "        CHAM_MATER=fieldmat,\n"
        "{excit}\n"
        "{comp}"
        "        INCREMENT=_F(LIST_INST=listinst),\n"
        "        ARCHIVAGE=_F(LIST_INST=times),\n"
        "{solveur}"
        "        NEWTON=_F(REAC_ITER={reac}),\n"
        "{rech}"
        "        CONVERGENCE=_F({conv}),\n"
        "    )\n"
        "except Exception as err:\n"
        "    if not str(getattr(err, 'id_message', '')).startswith("
        "'MECANONLINE'):\n"
        "        raise\n"
        "    print('BRIDGE_ONVOLLEDIG', res.getAccessParameters()['INST'][-1])\n"
        "t_res = res.getAccessParameters()['INST'][-1]\n").format(
            excit=bta._indent(excit_clause), comp=bta._indent(comportement),
            solveur=bta._indent(bta._build_solveur_ref(analysis)),
            reac=int(analysis.get("newton_reac_iter", 1)),
            # Line search (U4.51.03 RECH_LINEAIRE): with plasticity and a
            # steep, rapidly changing temperature field Newton diverged on
            # hex20 (WE-10b, LINE_QUAD: second step after 20 iterations
            # still residual 0.5, also after cutting 3x); with
            # ITER_LINE_MAXI=5 9-10 iterations per step. Not needed
            # without plasticity.
            rech=("        RECH_LINEAIRE=_F(ITER_LINE_MAXI=5),\n"
                  if with_plastic else ""),
            conv=bta._convergence_args(analysis))
    fm_text, fm_entries, fm_varc = _fieldmat(md, concepts, tref, projected,
                                             quiet)
    if birth:
        # Filler material: STAT_NON_LINE per birth step (_birth_solve)
        deep = " " * 12
        solve = _birth_solve(birth, concepts, fm_entries, fm_varc, {
            "excit": bta._indent(excit_clause, deep),
            "comp": bta._indent(comportement, deep),
            "solveur": bta._indent(bta._build_solveur_ref(analysis), deep),
            "reac": int(analysis.get("newton_reac_iter", 1)),
            "rech": ("                RECH_LINEAIRE=_F(ITER_LINE_MAXI=5),\n"
                     if with_plastic else ""),
            "conv": bta._convergence_args(analysis)}, with_plastic)
        log("INFO: Thermomechanical: filler material {0} elements, quiet "
            "(E x {1}) until birth, then stress-free in the "
            "state at the start of the birth step; STAT_NON_LINE per "
            "birth step.".format(len(birth["elements"]),
                                   "%.3g" % birth["quiet"]))
    calc = bta._build_calc_champ_block(md, with_plastic=with_plastic)
    # Cumulative plastic strain: V1 with VMIS_*; with META_P_IL V1..V5 are
    # hardenings per phase and V7 a stress (hsnv101a, MT-07), so
    # no P_max (bridge_metallurgy.mech_fields).
    report = _REPORT.format(n_nodes=len(model_data.get("mesh_nodes", {})),
                            p_cmp="" if meta_mech else "V1")
    log("INFO: Thermomechanical: STAT_NON_LINE on the thermal times, "
        "AFFE_VARC TEMP (EVOL = thermal result{0}), VALE_REF = {1} K, "
        "DEFORMATION {2}, {3}.".format(
            ", via PROJ_CHAMP to LINE_QUAD" if projected else "",
            "%.6g" % tref, analysis.get("deformation", "PETIT"),
            "plastic" if with_plastic else "elastic"))
    return {
        "mech_defigroup_block": defigroup,
        "mech_model_block": bta._build_model_block(md),
        "mech_materials_block": curves_block + materials_block + (
            _quiet_block(md, quiet) if quiet else ""),
        "mech_fieldmat_block": fm_text,
        "mech_loads_block": (bta._build_load_funcs_block(load_funcs) +
                             loads_block + "\n" + listinst),
        "mech_solve_block": solve,
        "mech_calc_champ_block": calc + report +
        bta._custom_code(model_data, "post"),
    }


def export_block(work_dir, model_data, fields):
    """aster_results_export with the mechanical result as 'res' and the
    thermal one as extra result 'res_ther' (temperature) and 'res_flux'
    (heat flux); same NUME_ORDRE (ARCHIVAGE on the thermal times)."""
    import bridge_to_aster as bta
    import os
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        return "#-- no export (result_route is not 'liml') --\n"
    scripts = os.path.dirname(os.path.abspath(__file__))
    return (
        "# Results in Mecway's own format (mechanical + thermal)\n"
        "import sys\n"
        "sys.path.insert(0, {scripts})\n"
        "import aster_results_export\n"
        "aster_results_export.export_results(\n"
        "    res, {fragment}, {liml},\n"
        "    extra_results=dict((k, globals()[k]) for k in\n"
        "                       ('res_ther', 'res_flux') if k in globals()),\n"
        "    precision='single', static=False, fields={fields!r})\n").format(
            scripts=bta._py_str(scripts),
            fragment=bta._py_str(bta.results_file(work_dir)),
            liml=bta._py_str(model_data.get("liml_path", "")),
            fields=[str(f) for f in fields])


def med_block():
    """IMPR_RESU MED only with the setting med_export."""
    if not CONFIG_BRIDGE.get("med_export", False):
        return "#-- no MED export (setting med_export off) --\n"
    return ("IMPR_RESU(\n    FORMAT='MED',\n    UNITE=80,\n    RESU=(\n"
            "        _F(RESULTAT=res_ther, NOM_CHAM=('TEMP',)),\n"
            "        _F(RESULTAT=res, NOM_CHAM=('DEPL', 'SIGM_NOEU', "
            "'SIEQ_NOEU')),\n    ),\n)\n")


# ==========================================
# AFTER THE RUN
# ==========================================
_ROW = re.compile(r"^BRIDGE_THERMOMECA\s+(\w+)\s+([-+0-9.eEinfa]+)\s*$")


def read_summary(mess_path):
    """{key: value} from the BRIDGE_THERMOMECA lines of the .mess."""
    import io
    import os
    out = OrderedDict()
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            m = _ROW.match(line.strip())
            if m:
                try:
                    out[m.group(1)] = float(m.group(2))
                except ValueError:
                    pass
            elif line.startswith("BRIDGE_THERMOMECA_TIJDEN"):
                out["_tijden"] = line.strip()
            elif line.startswith("BRIDGE_THERMOMECA_FOUT"):
                out["_fout"] = line.strip()
    finally:
        f.close()
    return out


def report_lines(mess_path):
    """Lines for log and status box: residual stress and distortion at the
    last time."""
    s = read_summary(mess_path)
    if not s:
        return []
    lines = []
    if "_tijden" in s:
        log(tr("WARNING: Thermomechanisch: de tijdstappen van het "
               "mechanische en het thermische resultaat lopen niet gelijk "
               "({0}); de temperatuur in Mecway kan bij een andere stap "
               "horen.",
               "WARNING: Thermomechanical: the time steps of the mechanical "
               "and the thermal result differ ({0}); the temperature in "
               "Mecway may belong to another step.").format(s["_tijden"]))
    if "_fout" in s:
        log("INFO: Thermomechanical summary incomplete: {0}".format(
            s["_fout"]))
    if "t" not in s or "VMIS_max" not in s:
        return lines
    mpa = 1.0e-6

    def rng(key):
        return "{0}..{1}".format("%.4g" % (s.get(key + "_min", 0.0) * mpa),
                                 "%.4g" % (s.get(key + "_max", 0.0) * mpa))
    line = tr(
        u"Thermomechanisch, t = {0} s (T {1}..{2} K): verplaatsing max {3} "
        u"mm (dx {4}..{5}, dy {6}..{7}, dz {8}..{9} mm); restspanning von "
        u"Mises max {10} MPa, sxx {11}, syy {12}, szz {13} MPa{14}.",
        u"Thermomechanical, t = {0} s (T {1}..{2} K): displacement max {3} "
        u"mm (dx {4}..{5}, dy {6}..{7}, dz {8}..{9} mm); residual stress von "
        u"Mises max {10} MPa, sxx {11}, syy {12}, szz {13} MPa{14}.").format(
            "%.6g" % s["t"], "%.5g" % s.get("T_min", 0.0),
            "%.5g" % s.get("T_max", 0.0), "%.4g" % (s.get("U_max", 0.0) * 1e3),
            *(["%.4g" % (s.get(k, 0.0) * 1e3) for k in (
                "DX_min", "DX_max", "DY_min", "DY_max", "DZ_min", "DZ_max")] +
              ["%.4g" % (s["VMIS_max"] * mpa), rng("SIXX"), rng("SIYY"),
               rng("SIZZ"),
               (tr(u"; cumulatieve plastische rek max {0} (tijdens de run "
                   u"max {1})", u"; cumulative plastic strain max {0} "
                   u"(during the run max {1})").format(
                       "%.4g" % s["P_max"], "%.4g" % s.get("P_max_all",
                                                           s["P_max"]))
                if "P_max" in s else u"")]))
    log(u"INFO: " + line)
    lines.append(line)
    return lines
