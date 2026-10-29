# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_acoustic.py
# Responsibility: Mecway Acoustic Resonance 3D (A30, cavity modes) to
# Code-Aster PHENOMENE='ACOUSTIQUE' + CALC_MODES, and the same model as a
# harmonic pressure field (source, absorbing boundaries, microphones) with
# DYNA_VIBRA HARM (Mecway has no analysis type for that).
#
#   note_tag(item, model_data)        - called by bridge_from_liml.py
#                                       for every load/constraint in an
#                                       acoustic run (report or keep).
#   parse_acoustic(root, model_data)  - after the loop in bridge_from_liml.py:
#                                       materials (speed of sound,
#                                       density) and pressure nodes.
#   build_acoustic_modes(...)         - builder; bridge_to_aster._build_modal
#                                       sends an acoustic analysis
#                                       here (CALC_MODES is the key in
#                                       SOLVER_BUILDERS_ASTER).
#   build_acoustic_harm(...)          - builder harmonic pressure field
#                                       (acoustic_harm_3d, DYNA_VIBRA HARM;
#                                       via bridge_to_aster._build_dyna_modal);
#                                       see the block HARMONIC PRESSURE FIELD.
#   resolve_auto(), report_harmonic() - MecwayAsterBridgeMain: 'auto' with
#                                       a source, microphones in the log.
#
# Mecway XML (Mecway 33, determined with headless 'mecway <model> solve',
# TestFiles/Tools/mw_solve.py; tag names also in mecway.exe):
#   <analysis type="A30" maxmode="5" />            (A20 = 2D: see below)
#   <mat><mechanical type="Isotropic" speedofsound="340 m/s" />
#        <density type="Simple" density="1.2 kg/m³" /></mat>
#     (density optional: Mecway solves without it; only an impedance
#     needs it. One material: with two materials Mecway gives no
#     solution, seen with headless solve.)
#   <fluidpressure selection="nodes or faces"><value>0 Pa</value>
#     (manual v33 par. 9.34: pressure node p = 0; Mecway refuses another
#     value, "Pressure must be zero.")
#   <impedance selection="faces"><specificimpedancer>408</...r>
#     <specificimpedancei>0</...i></impedance>    (manual par. 9.35; number
#     without unit = Pa.s/m; Z = r + i i; with impedance complex modes:
#     fields pressure + pressurei, <mode .. frequency=".." decayrate="..">;
#     translated in _complex_modes_comm + aster_acoustic_complex.py, S2b.)
#   Solution: per mode <mode id="k" frequency="f Hz"> with the node variable
#   "pressure"; Mecway normalises p^T M p = 1 with M = int N^T N / c^2 dV
#   (checked: constant mode of a tube with volume V: p = c / sqrt(V);
#   manual v33 par. 6.9.1: amplitudes are arbitrary).
#
# Translation (Code-Aster 17.4; syntax as test cases ahlv100a and adlv101f):
#   - AFFE_MODELE PHENOMENE='ACOUSTIQUE', MODELISATION='3D' on the volumes
#     (elements ACOU_HEXA8/20, ACOU_PENTA6/15, ACOU_TETRA4/10 in elem.1;
#     no pyramids).
#   - DEFI_MATERIAU FLUIDE=_F(RHO, CELE_R) (catalogue defi_materiau.py;
#     RHO is required). Without density RHO = 1. RIGI_ACOU and MASS_ACOU
#     do not contain rho (measured, NOT checked in the source code: RHO 1.2
#     gave the same frequencies and MASS_GENE as RHO 1, and a tube of two
#     media with rho 1.2 / 12 gave the frequencies of equal density,
#     248.98 Hz instead of analytically 306.47 Hz). Like Mecway (K = int
#     grad N^T grad N, manual v33 par. 6.9.1) the interface between two
#     media therefore has continuous dp/dn: only correct for equal
#     density. Media with different density: ERROR (_materials).
#   - Pressure node: AFFE_CHAR_ACOU PRES_IMPO PRES=0j (adlv101f).
#   - ASSEMBLAGE RIGI_ACOU / MASS_ACOU (complex matrices) and
#     COMB_MATR_ASSE PARTIE='REEL' (ahlv100a), then CALC_MODES (result
#     MODE_ACOU, field PRES, component PRES; seen in a run).
#   - Hard walls without a pressure node: the stiffness is singular (constant
#     pressure, 0 Hz). PLUS_PETITE then stops with <EXCEPTION> ALGELINE3_81
#     (seen); the bridge searches around a small negative frequency
#     (OPTION 'CENTRE', _free_shift), like free-free in modal.
#   - NORM_MODE does not work for MODE_ACOU (MASS_GENE as norm still gave
#     max |p| = 1 and a MASS_GENE of 8.65e-8, seen): aster_results_
#     export scales the shapes itself by 1/sqrt(MASS_GENE), so p^T M p = 1
#     like Mecway.
#
# Acoustic Resonance 2D (Mecway A20, STAPPENPLAN S16d; measured headless
# with Mecway 34, 28 Oct 2026, mw_solve.py): the same .liml tags as A30 on
# plane elements tri3/tri6/quad4/quad8 in the XY plane; fluid pressure and
# impedance on edges (faceid 1..4) or nodes. A Shell/membrane thickness
# changes nothing (frequencies and shapes identical with and without
# 10 mm); the normalisation is per unit thickness (constant mode p =
# c / sqrt(area)). Mecway has no axisymmetric acoustic type. Translated
# with MODELISATION 'PLAN' (impedance edges 'PLAN_ABSO'; test case
# ahlv100f) and otherwise the A30 route: MASS_ACOU of PLAN is per unit
# thickness, so the MASS_GENE normalisation gives Mecway's amplitudes
# (verification AK-10 .. AK-13). bridge_plane._apply_acoustic checks the
# mesh and sets model_data["acoustic_2d"]. The harmonic pressure field
# (acoustic_harm_3d) is not translated in 2D: Mecway has no 2D input for
# it (no frequency or source; an A20 model with fluid pressure != 0 gives
# no solution in Mecway 34, measured headless 29 Oct 2026; KNOWN_BUGS 126).
#
# Compatible with IronPython 2.7.9 (standard library only).

import math
import re
import os
from collections import OrderedDict

from bridge_utils import (log, parse_and_convert, CONFIG_BRIDGE, tr,
                          run_name, _normalize_unit_string)


# Mecway loads that only exist in Acoustic Resonance (manual v33
# par. 9.34, 9.35); in a mechanical or thermal analysis they play
# no role (INFO in bridge_from_liml).
ACOUSTIC_TAGS = frozenset(["fluidpressure", "impedance"])

# Constraints that Mecway also uses in acoustics (manual v33 par. 9.9:
# bonded contact couples the pressure; test models in mecway.exe: "A30
# node-surface coupling", "A30 Constraint Equations"), but that the bridge
# does not translate there: report and skip.
_NOT_IN_ACOUSTICS = frozenset(["contact2", "nodesurfacecoupling",
                               "constraintequation"])

# Mecway shapes with an acoustic Code-Aster element (elem.1 of 17.4:
# ACOU_HEXA8/20/27, ACOU_PENTA6/15, ACOU_TETRA4/10; no pyramid).
_ACOUSTIC_SHAPES = frozenset(["hex8", "hex20", "wedge6", "wedge15",
                              "tet4", "tet10"])
# Acoustic Resonance 2D (A20, S16d; bridge_plane._apply_acoustic sets
# model_data["acoustic_2d"]): plane elements with MODELISATION 'PLAN'
# (elem.1 of 17.4: ACOU_PLAN on TRIA3/6, QUAD4/8 - NOT verified in the
# catalogue, seen in the Code-Aster run of verification AK-10 .. AK-13) and
# edges 'PLAN_ABSO' for an impedance (test case ahlv100f, SEG3).
_ACOUSTIC_SHAPES_2D = frozenset(["tri3", "tri6", "quad4", "quad8"])


def _modelisations(model_data):
    """(area/volume, impedance boundary) modelisations of
    PHENOMENE='ACOUSTIQUE' (catalogue affe_modele.py v17.4: 3D, PLAN,
    3D_ABSO, PLAN_ABSO)."""
    if model_data.get("acoustic_2d"):
        return "PLAN", "PLAN_ABSO"
    return "3D", "3D_ABSO"
_LINEAR_SHAPES = frozenset(["hex8", "wedge6", "tet4"])

# Harmonic analysis (S3a): analysis name and the prefixes of special
# Mecway selections (case does not matter; NL and EN).
HARM_ANALYSIS = "acoustic_harm_3d"
_PREFIXES = (("source", ("BRON_", "SOURCE_")),
             ("absorbing", ("ABSORBEREND_", "ABSORBING_")),
             ("microphone", ("MICROFOON_", "MICROPHONE_")))

# #ASTER-BRON (source_value; also bridge_vibroacoustic_harm): number with
# unit, the whole text. Velocity units that parse_and_convert(..,
# "velocity") converts (empty = m/s) and pressure units that parse_and_convert(..,
# "pressure") converts (lower case; parse_and_convert decides mPa/MPa
# by the capital letter). Here a pressure gives a clear ERROR; in
# vibroacoustic_harm_3d a pressure is an incident wave.
_NUMBER_UNIT_RE = re.compile(
    r"^[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?\s*([A-Za-z0-9/]*)\s*$")
_VELOCITY_UNITS = ("", "m/s", "mm/s", "mm/ms", "in/s", "ft/s")
_PRESSURE_UNITS = ("pa", "n/m2", "kpa", "kn/m2", "mpa", "n/mm2", "gpa",
                   "bar", "mbar", "psi")

# Elements per wavelength at the highest frequency below which the bridge
# warns (linear / quadratic). Measured (verification AH-01/01b/02,
# docs/Akoestiek.md par. 5.4), plane wave over 2 wavelengths: hex8 10 per
# wavelength phase -1.6% (~ (kh)^2/24) and |p| +1.7%, 20 per wavelength
# -0.4%; hex20 10 per wavelength <= 0.02%, 5 per wavelength |p| -0.25% and
# phase -0.16%.
_MIN_PER_WAVELENGTH = {True: 10.0, False: 5.0}


def is_acoustic(analysis_cfg):
    """True if the analysis config is acoustic (key "phenomene")."""
    return str(analysis_cfg.get("phenomene", "")).upper() == "ACOUSTIQUE"


def _r(x):
    """Number for the .comm (15 digits, decimal point; bridge_mesh._real)."""
    import bridge_mesh
    return bridge_mesh._real(float(x))


def _skip(model_data, text):
    model_data["skipped_loads"].append(text)


# ==========================================
# PARSING
# ==========================================
def note_tag(item, model_data):
    """
    A load or constraint in an acoustic run (bridge_from_liml
    skips them there). Acoustic tags are read by parse_acoustic; what Mecway
    uses in acoustics but the bridge does not translate: ERROR and
    skipped_loads; mechanical and thermal loads: INFO (they do not take
    part in Acoustic Resonance, manual v33 chapter 9: analysis types per
    load).
    """
    tag = item.tag
    # contact2: selectionmaster/-slave, nodesurfacecoupling:
    # selectionsurface/-node (bridge_from_liml)
    sel = item.get("selection") or " / ".join(
        item.get(k) for k in ("selectionmaster", "selectionslave",
                              "selectionsurface", "selectionnode")
        if item.get(k)) or ""
    if tag in ACOUSTIC_TAGS or item.get("suppressed", "") == "true":
        return
    if tag in _NOT_IN_ACOUSTICS:
        _skip(model_data, tr("{0} op '{1}' (akoestiek)",
                             "{0} on '{1}' (acoustics)").format(tag, sel))
        log(tr("ERROR: '{0}' op '{1}' wordt in een akoestische analyse niet "
               "vertaald en is NIET meegenomen (gebruik een doorlopend mesh "
               "zonder contact of koppelingen).",
               "ERROR: '{0}' on '{1}' is not translated in an acoustic "
               "analysis and is NOT included (use a continuous mesh without "
               "contact or couplings).").format(tag, sel))
        return
    log("INFO: Load '{0}' on '{1}' does not count in an acoustic "
        "analysis.".format(tag, sel))


def _selection_kind(model_data, name):
    if name in model_data.get("node_groups", {}):
        return "node"
    if name in model_data.get("face_selection_faces", {}):
        return "face"
    if name in model_data.get("element_selections", {}):
        return "element"
    return None


def _prefix_role(name):
    """'source'/'absorbing'/'microphone' if the Mecway name starts with a
    prefix from _PREFIXES (case does not matter), else
    None."""
    upper = (name or "").upper()
    for role, prefixes in _PREFIXES:
        for p in prefixes:
            if upper.startswith(p):
                return role
    return None


def _named_groups(model_data):
    """{role: [(Mecway name, kind)]} of the selections with a special
    prefix (by the original Mecway name, STAPPENPLAN B.2)."""
    out = {"source": [], "absorbing": [], "microphone": []}
    seen = set()
    for kind, names in (("face", model_data.get("face_selection_faces", {})),
                        ("node", model_data.get("node_groups", {})),
                        ("element",
                         model_data.get("element_selections", {}))):
        for name in names:
            role = _prefix_role(name)
            if role and (name, kind) not in seen:
                seen.add((name, kind))
                out[role].append((name, kind))
    return out


def source_value(text):
    """
    Value of an #ASTER-BRON: 'number [unit]' as the whole text ->
    (kind, value SI, unit as typed). kind 'velocity' (unit from
    _VELOCITY_UNITS, without unit m/s; value in m/s), 'pressure'
    (_PRESSURE_UNITS; value in Pa, converted once by
    parse_and_convert) or None (no number, or another unit; value
    None). parse_and_convert would return an unknown unit unchanged and text
    without a number as 0.0, hence this check first.
    """
    text = _normalize_unit_string(u"{0}".format(text).strip())
    m = _NUMBER_UNIT_RE.match(text)
    if not m:
        return None, None, ""
    unit = m.group(1)
    if unit.lower() in _VELOCITY_UNITS:
        kind = "velocity"
    elif unit.lower() in _PRESSURE_UNITS:
        kind = "pressure"
    else:
        return None, None, unit
    return kind, float(parse_and_convert(text, kind)), unit


def _parse_aster_sources(model_data, ac):
    """#ASTER-BRON selection = velocity [unit] [, phase] (bridge_custom)
    -> ac["aster_sources"] = [(selection, v [m/s], phase [degrees])].
    Only a velocity: without unit m/s, otherwise the velocity units
    of parse_and_convert (_VELOCITY_UNITS). A pressure unit (in
    vibroacoustic_harm_3d an incident wave) or another unit and
    text without a number give an ERROR (parse_and_convert would return the
    value unchanged as m/s or as 0.0)."""
    for body in model_data.get("aster_custom", {}).get("sources", []):
        # 'Sel = 2 mm/s' or 'Sel = 2 mm/s, 90' or 'Sel = 2 mm/s, fase = 90'
        name, sep, rest = body.partition("=")
        parts = [p.strip() for p in rest.split(",")]
        v = None
        phase = 0.0
        if sep and name.strip() and parts[0] and len(parts) <= 2:
            kind, value, unit = source_value(parts[0])
            if kind == "pressure":
                ac["bad"].append(tr(
                    "'#ASTER-BRON {0}': een druk ({1}) kan hier niet als "
                    "bron; #ASTER-BRON is in deze analyse een "
                    "normaalsnelheid [m/s of mm/s]. Een opgelegde druk: "
                    "Mecway's fluid pressure != 0 op de selectie",
                    "'#ASTER-BRON {0}': a pressure ({1}) cannot be a "
                    "source here; in this analysis #ASTER-BRON is a "
                    "normal velocity [m/s or mm/s]. An imposed pressure: "
                    "Mecway's fluid pressure != 0 on the "
                    "selection").format(body.strip(), unit))
                continue
            if kind == "velocity":
                try:
                    v = value
                    if len(parts) == 2:
                        phase = float(parts[1].split("=")[-1].strip())
                except (TypeError, ValueError):
                    v = None
        if v is None:
            ac["bad"].append(tr(
                "'#ASTER-BRON {0}': verwacht 'selectie = snelheid [m/s of "
                "mm/s] [, fase in graden]', bijv. '#ASTER-BRON Luidspreker "
                "= 2 mm/s, 90'",
                "'#ASTER-BRON {0}': expected 'selection = velocity [m/s or "
                "mm/s] [, phase in degrees]', e.g. '#ASTER-BRON Speaker = "
                "2 mm/s, 90'").format(body.strip()))
            continue
        ac["aster_sources"].append((name.strip(), v, phase))


def parse_acoustic(root, model_data):
    """
    Materials (speed of sound, density) and acoustic conditions from
    the .liml to model_data["acoustic_data"]:
      "materials":  {mat: {"c": m/s or None, "rho": kg/m3 or None}}
      "pressure0":  [(selection, "node"/"face")]   pressure nodes p = 0
      "pressure_src": [(selection, kind, p [Pa], text)]  fluid pressure
                    != 0: in the harmonic analysis an imposed pressure, in
                    the cavity modes an error
      "impedances": [selection]
      "impedance_values": [(selection, Re Z, Im Z)]  (Pa.s/m)
      "named":      {role: [(selection, kind)]}  BRON_/ABSORBEREND_/
                    MICROFOON_ (harmonic, _named_groups)
      "aster_sources": [(selection, v, phase)]   #ASTER-BRON
      "bad":        [text]                        fatal input errors
    """
    ac = {"materials": OrderedDict(), "pressure0": [], "pressure_src": [],
          "impedances": [], "impedance_values": [],
          "named": _named_groups(model_data), "aster_sources": [],
          "bad": []}
    _parse_aster_sources(model_data, ac)
    for mat in root.findall("mat"):
        name = mat.get("name", "UnknownMat")
        mech = mat.find("mechanical")
        dens = mat.find("density")
        c = mech.get("speedofsound") if mech is not None else None
        rho = dens.get("density") if dens is not None else None
        ac["materials"][name] = {
            "c": parse_and_convert(c, "velocity") if c else None,
            "rho": parse_and_convert(rho, "density") if rho else None}
        log("INFO: Acoustic material '{0}': c = {1} m/s, rho = {2} "
            "kg/m3.".format(name, ac["materials"][name]["c"],
                            ac["materials"][name]["rho"]))
    for item in root:
        if item.tag not in ACOUSTIC_TAGS:
            continue
        sel = item.get("selection", "")
        if item.get("suppressed", "") == "true":
            log("INFO: {0} on '{1}' skipped (suppressed).".format(
                item.tag, sel))
            continue
        kind = _selection_kind(model_data, sel)
        if item.tag == "impedance":
            ac["impedances"].append(sel)
            ac["impedance_values"].append(
                (sel, _number(item.findtext("specificimpedancer")),
                 _number(item.findtext("specificimpedancei"))))
            continue
        text = item.findtext("value")
        value = parse_and_convert(text, "pressure") if text else 0.0
        try:
            value = float(value)
        except (TypeError, ValueError):
            ac["bad"].append(tr(
                "fluid pressure op '{0}': waarde '{1}' is geen druk",
                "fluid pressure on '{0}': value '{1}' is not a "
                "pressure").format(sel, text))
            continue
        if kind not in ("node", "face"):
            ac["bad"].append(tr(
                "fluid pressure op '{0}': kies een knoop- of vlakselectie",
                "fluid pressure on '{0}': choose a node or face "
                "selection").format(sel))
        elif abs(value) > 0.0:
            # Cavity modes: Mecway refuses this too ("Pressure must be
            # zero."), build_acoustic_modes gives an ERROR; harmonic:
            # an imposed pressure (source).
            ac["pressure_src"].append((sel, kind, value, text))
        else:
            ac["pressure0"].append((sel, kind))
    model_data["acoustic_data"] = ac


def _number(text):
    """Number from a Mecway field without unit (impedance), 0 if empty;
    None if it is not a number."""
    if text is None or not text.strip():
        return 0.0
    try:
        return float(parse_and_convert(text, "dimensionless"))
    except (TypeError, ValueError):
        return None


def has_source(model_data):
    """True if the model has a harmonic source (face selection BRON_/
    SOURCE_, #ASTER-BRON or fluid pressure != 0): active_analysis 'auto'
    then picks the harmonic analysis for A30 (MecwayAsterBridgeMain,
    resolve_auto)."""
    ac = model_data.get("acoustic_data") or {}
    return bool(ac.get("named", {}).get("source") or
                ac.get("aster_sources") or ac.get("pressure_src"))


def resolve_auto(resolved, model_data):
    """Analysis for 'auto': A30 with a source -> acoustic_harm_3d (if it
    exists), else unchanged. A20 (2D) always keeps the cavity modes: Mecway
    has no 2D harmonic acoustic input (bridge_plane._apply_acoustic)."""
    if model_data.get("analysis_type") == "A20":
        return resolved
    if (resolved == "acoustic_modes_3d" and has_source(model_data) and
            HARM_ANALYSIS in CONFIG_BRIDGE.get("analyses", {})):
        log("INFO: Acoustics: the model has a source (BRON_ selection, "
            "#ASTER-BRON or fluid pressure != 0); 'auto' picks the "
            "harmonic analysis '{0}'. For "
            "the cavity modes: choose 'acoustic_modes_3d' as active "
            "analyse.".format(HARM_ANALYSIS))
        return HARM_ANALYSIS
    return resolved


# ==========================================
# BUILDER
# ==========================================
def _fmt_groups(groups):
    return "({0},)".format(", ".join("'{0}'".format(g) for g in groups))


def _elsets(model_data):
    """[(Code-Aster elset, Mecway material)] of the volumes, or None on
    an error (ERROR logged). After write_mesh the keys of "elsets" are
    the Code-Aster names (bridge_mesh._apply_to_model_data)."""
    shapes_of = OrderedDict()
    elem_elset = model_data.get("_elem_elset", {})
    for eid, shape, _nodes, elset in model_data.get("mesh_elements", []):
        name = elem_elset.get(eid, elset)
        shapes_of.setdefault(name, set()).add(shape)
    out, bad = [], []
    plane = bool(model_data.get("acoustic_2d"))
    allowed = _ACOUSTIC_SHAPES_2D if plane else _ACOUSTIC_SHAPES
    for elset, shapes in shapes_of.items():
        wrong = sorted(shapes - allowed)
        if wrong:
            bad.append("'{0}' ({1})".format(elset, ", ".join(wrong)))
            continue
        mat = model_data.get("elsets", {}).get(elset)
        if not mat:
            bad.append(tr("'{0}' (geen materiaal)",
                          "'{0}' (no material)").format(elset))
            continue
        out.append((elset, mat))
    if bad and plane:
        log(tr("ERROR: Akoestiek 2D (A20): alleen vlakke elementen (tri3, "
               "tri6, quad4, quad8) met een materiaal: {0}. Mesh in Mecway "
               "alleen het lucht- of vloeistofvlak.",
               "ERROR: Acoustics 2D (A20): only plane elements (tri3, tri6, "
               "quad4, quad8) with a material: {0}. In Mecway, mesh only the "
               "air or fluid area.").format(", ".join(bad)))
        return None
    if bad:
        log(tr("ERROR: Akoestiek: alleen volume-elementen (hex, wedge, tet; "
               "geen piramides, schalen of balken) met een materiaal: {0}. "
               "Mesh in Mecway alleen het lucht- of vloeistofvolume.",
               "ERROR: Acoustics: only solid elements (hex, wedge, tet; no "
               "pyramids, shells or beams) with a material: {0}. In Mecway, "
               "mesh only the air or fluid volume.").format(", ".join(bad)))
        return None
    if not out:
        log(tr("ERROR: Akoestiek: geen volume-elementen gevonden.",
               "ERROR: Acoustics: no solid elements found."))
        return None
    return out


def _materials(elsets, ac):
    """{Mecway material: (c, rho)} or None (ERROR). Without density rho
    = 1. Several media: only with equal (or no) density, because the
    matrices do not contain rho (see the header)."""
    used = []
    for _es, mat in elsets:
        if mat not in used:
            used.append(mat)
    props = ac["materials"]
    no_c = [m for m in used if not (props.get(m, {}).get("c") or 0.0) > 0.0]
    if no_c:
        log(tr("ERROR: Akoestiek: materiaal {0} heeft geen geluidssnelheid. "
               "Vul in Mecway bij het materiaal (Isotropic) 'Speed of sound' "
               "in.",
               "ERROR: Acoustics: material {0} has no speed of sound. Fill "
               "in 'Speed of sound' for the material (Isotropic) in "
               "Mecway.").format(", ".join("'%s'" % m for m in no_c)))
        return None
    rhos = dict((m, props[m].get("rho") or 0.0) for m in used)
    given = sorted(set(v for v in rhos.values() if v > 0.0))
    if len(given) > 1 and given[-1] > given[0] * (1.0 + 1.0e-6):
        log(tr("ERROR: Akoestiek: de media hebben een verschillende "
               "dichtheid ({0}). Code-Aster's akoestische drukformulering "
               "(en Mecway) neemt een dichtheidssprong op het grensvlak niet "
               "mee; de frequenties zouden fout zijn. Geef alle materialen "
               "dezelfde dichtheid (of geen) als het verschil klein is, of "
               "reken de media apart.",
               "ERROR: Acoustics: the media have different densities ({0}). "
               "Code-Aster's acoustic pressure formulation (and Mecway) does "
               "not include a density jump at the interface; the "
               "frequencies would be wrong. Give all materials the same "
               "density (or none) if the difference is small, or compute "
               "the media separately.").format(", ".join(
                   "%s %s kg/m3" % (m, "%.6g" % rhos[m]) for m in used)))
        return None
    missing = [m for m in used if not rhos[m] > 0.0]
    if given and missing:
        # One medium with and one without density: the matrices do not
        # contain rho (see the header), so the interface (p and dp/dn
        # continuous) behaves as if the densities are equal. The medium
        # without density gets RHO = 1 in DEFI_MATERIAU; that only counts for
        # a source or impedance on that medium, and those require a density.
        # Computed (07-10-2026): AK-05 with 1.2 kg/m3 / none gives the
        # frequencies of AK-05 (equal density), RHO 1.2 and 1.0.
        log(tr("WARNING: Akoestiek: medium {0} heeft geen dichtheid, "
               "medium {1} wel ({2}). Op het grensvlak rekent de bridge "
               "alsof de dichtheden gelijk zijn (druk en dp/dn continu): "
               "dat klopt alleen als {0} dezelfde dichtheid heeft; bij een "
               "andere dichtheid zijn de resultaten fout (docs/Akoestiek.md "
               "par. 3.2). Code-Aster krijgt voor {0} RHO = 1 kg/m3. Vul bij "
               "elk medium de dichtheid in. De berekening gaat door.",
               "WARNING: Acoustics: medium {0} has no density, medium {1} "
               "has ({2}). At the interface the bridge computes as if the "
               "densities are equal (pressure and dp/dn continuous): that "
               "is only correct if {0} has the same density; with a "
               "different density the results are wrong (docs/en/"
               "Acoustics.md section 3.2). Code-Aster gets RHO = 1 kg/m3 "
               "for {0}. Fill in the density for every medium. The "
               "computation continues.").format(
                   ", ".join("'%s'" % m for m in missing),
                   ", ".join("'%s'" % m for m in used if m not in missing),
                   ", ".join("%s kg/m3" % ("%.6g" % v) for v in given)))
    out = OrderedDict()
    for m in used:
        out[m] = (props[m]["c"], rhos[m] if rhos[m] > 0.0 else 1.0)
    if len(used) > 1:
        log("INFO: Acoustics: {0} media ({1}) with equal (or no) "
            "density; at the "
            "interface the pressure and dp/dn are continuous. Mecway itself "
            "solves acoustics with only one material.".format(
                len(used), ", ".join(used)))
    return out


def _free_shift(model_data, elsets, mats):
    """
    Search frequency [Hz] < 0 for hard walls without a pressure node: -0.1 x
    c_min / (2 D), D = diagonal of the bounding box of the volumes.
    For a convex volume the first mode with pressure variation lies above
    c / (2 D) (Payne-Weinberger, eigenvalue >= pi^2 / D^2); the shift is
    therefore well below that mode and close to the 0 Hz mode. Measured: a tube
    of 1 m with CENTRE -10 Hz gave the same modes as Mecway (verification
    AK-01).
    """
    keep = set(es for es, _m in elsets)
    elem_elset = model_data.get("_elem_elset", {})
    nodes = model_data.get("mesh_nodes", {})
    lo, hi = [1.0e300] * 3, [-1.0e300] * 3
    for eid, _shape, enodes, elset in model_data.get("mesh_elements", []):
        if elem_elset.get(eid, elset) not in keep:
            continue
        for n in enodes:
            p = nodes.get(n)
            if p is None:
                continue
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
    diag = math.sqrt(sum((hi[k] - lo[k]) ** 2 for k in range(3)))
    c_min = min(c for c, _rho in mats.values())
    if diag <= 0.0:
        return -1.0
    return -0.1 * c_min / (2.0 * diag)


def _calc_modes_block(model_data, analysis, shift_free):
    """res = CALC_MODES(...) like bridge_to_aster._calc_modes_block
    (modal), without NORM_MODE (does not work for MODE_ACOU, see the header)."""
    import bridge_to_aster as bta
    n = bta._mode_count(model_data, analysis)
    shift = float(analysis.get("modal_shift_hz", 0.0) or 0.0)
    lines = ["res = CALC_MODES(",
             "    TYPE_RESU='DYNAMIQUE',",
             "    MATR_RIGI=rigidite,",
             "    MATR_MASS=masse,"]
    if shift == 0.0 and shift_free is not None:
        shift = shift_free
        log("INFO: Acoustics: hard walls without a pressure node; the first "
            "mode is the constant pressure (0 Hz). Search frequency {0} Hz "
            "(OPTION 'CENTRE').".format("%.6g" % shift))
    if shift != 0.0:
        lines += ["    OPTION='CENTRE',",
                  "    CALC_FREQ=_F(FREQ={0}, NMAX_FREQ={1}),".format(
                      _r(shift), n)]
    else:
        lines += ["    OPTION='PLUS_PETITE',",
                  "    CALC_FREQ=_F(NMAX_FREQ={0}),".format(n)]
    lines += ["    VERI_MODE=_F(SEUIL={0}, STOP_ERREUR='NON'),".format(
                  "%.10g" % float(analysis.get("modal_tolerance", 1.0e-6))),
              "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(
                  int(analysis.get("solver_nprec", 8))),
              ")"]
    log("INFO: CALC_MODES acoustic: {0} modes.".format(n))
    return "\n".join(lines) + "\n"


def build_acoustic_modes(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate study.comm and study.export for the cavity modes (Mecway A30).
    Returns the path to study.export, or None on an error.
    """
    import bridge_to_aster as bta
    log("--- Generating Aster Files (CALC_MODES akoestisch) ---")
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor modale "
               "analyses. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for modal "
               "analyses. Choose 'liml' (General page)."))
        return None
    ac = model_data.get("acoustic_data")
    if ac is None:
        log(tr("ERROR: Geen akoestische gegevens gelezen; is het Mecway-"
               "analysetype A30 (Acoustic Resonance 3D) of de actieve "
               "analyse 'acoustic_modes_3d'?",
               "ERROR: No acoustic data read; is the Mecway analysis type "
               "A30 (Acoustic Resonance 3D) or the active analysis "
               "'acoustic_modes_3d'?"))
        return None
    bad = list(ac["bad"])
    # Mecway itself refuses this too ("Pressure must be zero.").
    bad += [tr("fluid pressure op '{0}' is {1}; alleen 0 kan (drukknoop; "
               "als bron: de harmonische analyse '{2}')",
               "fluid pressure on '{0}' is {1}; only 0 is possible "
               "(pressure node; as a source: the harmonic analysis "
               "'{2}')").format(sel, text, HARM_ANALYSIS)
            for sel, _k, _v, text in ac.get("pressure_src", [])]
    if bad:
        log(tr("ERROR: Akoestiek: {0}.", "ERROR: Acoustics: {0}.").format(
            "; ".join(bad)))
        return None
    # (no list comprehensions with loose names: in Python 2.7 they leak
    # into the function, e.g. _r over the module function _r)
    named = list(item[0] for role in ("source", "absorbing")
                 for item in ac.get("named", {}).get(role, []))
    named += list(item[0] for item in ac.get("aster_sources", []))
    if named:
        log("INFO: Acoustics: source and absorbing selections ({0}) only count "
            "in the harmonic analysis '{1}'; for the cavity modes they are "
            "hard walls.".format(", ".join(named), HARM_ANALYSIS))
    if model_data.get("analysis_type") == "A20" and \
            not model_data.get("acoustic_2d"):
        # bridge_plane._apply_acoustic did not run (should not happen)
        log(tr("ERROR: Acoustic Resonance 2D (A20): de vlakke modelisatie "
               "ontbreekt (bridge_plane).",
               "ERROR: Acoustic Resonance 2D (A20): the plane modelisation "
               "is missing (bridge_plane)."))
        return None
    elsets = _elsets(model_data)
    if elsets is None:
        return None
    mats = _materials(elsets, ac)
    if mats is None:
        return None
    mod_area, _mod_abso = _modelisations(model_data)
    if ac["impedances"]:
        # Impedance: complex modes (S2b), own route (see
        # _complex_modes_comm and aster_acoustic_complex.py).
        return _complex_modes_comm(work_dir, model_data, msh_path, resu_name,
                                   analysis, ac, elsets, mats)

    # --- model, materials ---
    model_block = ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n    AFFE=_F(\n"
                   "        GROUP_MA={0},\n        PHENOMENE='ACOUSTIQUE',\n"
                   "        MODELISATION='{1}',\n    ),\n)\n").format(
                       _fmt_groups([es for es, _m in elsets]), mod_area)
    names = OrderedDict()
    mat_lines = []
    for k, (mat, (c, rho)) in enumerate(mats.items()):
        names[mat] = "MAC{0}".format(k + 1)
        mat_lines.append("{0}{1} = DEFI_MATERIAU(FLUIDE=_F(RHO={2}, "
                         "CELE_R={3}))".format(bta._mat_comment(mat),
                                               names[mat], _r(rho), _r(c)))
    fieldmat_block = ("fieldmat = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n"
                      "    MODELE=model,\n    AFFE=(\n{0}    ),\n)\n").format(
                          "".join("        _F(GROUP_MA='{0}', MATER={1}),\n"
                                  .format(es, names[m]) for es, m in elsets))

    # --- pressure nodes ---
    renames = model_data.get("selection_renames",
                             model_data.get("group_renames", {}))
    known = model_data.get("mesh_group_names", set())
    entries = []
    for sel, kind in ac["pressure0"]:
        name = renames.get(sel, sel)
        if name not in known:
            log(tr("WARNING: Akoestiek: selectie '{0}' van fluid pressure is "
                   "leeg; overgeslagen.",
                   "WARNING: Acoustics: selection '{0}' of fluid pressure is "
                   "empty; skipped.").format(sel))
            continue
        entries.append("_F({0}='{1}', PRES=0j)".format(
            "GROUP_NO" if kind == "node" else "GROUP_MA", name))
    charges = []
    loads_block = ""
    if entries:
        loads_block = ("# Pressure nodes (Mecway fluid pressure = 0)\n"
                       "bc_pres = AFFE_CHAR_ACOU(\n    MODELE=model,\n"
                       "    PRES_IMPO=(\n        {0},\n    ),\n)\n").format(
                           ",\n        ".join(entries))
        charges.append("bc_pres")
    extra = model_data.get("aster_custom", {}).get("excit", [])
    charges += [n for n in extra if n not in charges]
    loads_block += bta._custom_code(model_data, "code")
    if not loads_block:
        loads_block = "#-- no pressure nodes (hard walls) --\n"
    charge_ref = ("    CHARGE=({0},),\n".format(", ".join(charges))
                  if charges else "")
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{0}"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('rigi_c'), OPTION='RIGI_ACOU'),\n"
        "        _F(MATRICE=CO('mass_c'), OPTION='MASS_ACOU'),\n"
        "    ),\n"
        ")\n"
        "# Real parts (the acoustic matrices are complex; ahlv100a)\n"
        "rigidite = COMB_MATR_ASSE(COMB_R=_F(MATR_ASSE=rigi_c, "
        "PARTIE='REEL', COEF_R=1.0))\n"
        "masse = COMB_MATR_ASSE(COMB_R=_F(MATR_ASSE=mass_c, "
        "PARTIE='REEL', COEF_R=1.0))\n").format(charge_ref)
    shift_free = None
    if not charges:
        shift_free = _free_shift(model_data, elsets, mats)
    calc_modes_block = _calc_modes_block(model_data, analysis, shift_free)
    export_block = (bta._custom_code(model_data, "post") +
                    _export_block(work_dir, model_data))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('PRES',)))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = bta._read_template(analysis["template"])
        bta._write_comm(comm_path, template.format(
            model_block=model_block,
            materials_block="\n".join(mat_lines) + "\n",
            fieldmat_block=fieldmat_block,
            loads_block=loads_block,
            assemblage_block=assemblage_block,
            calc_modes_block=calc_modes_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        with open(export_path, "w") as f:
            f.write("\n".join([
                "P actions make_etude",
                "P time_limit {0}".format(analysis.get("time_limit", 900)),
                "P memory_limit {0}".format(analysis.get("memory_limit", 2048)),
                "P mpi_nbcpu 1",
                "P ncpus {0}".format(CONFIG_BRIDGE["ncpus"]),
                "P no-mpi true",
                "F comm {0} D 1".format(comm_path),
                "F mail {0} D 20".format(msh_path),
                "F mess {0} R 6".format(os.path.join(work_dir,
                                                     run_name(".mess"))),
            ]) + bta._export_result_lines(work_dir, resu_name))
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren akoestische solver-bestanden mislukt: {0}",
               "ERROR: Generating the acoustic solver files failed: {0}")
            .format(str(e)))
    return None


def _export_block(work_dir, model_data):
    """aster_results_export: modes as <mode> with the node variable
    'pressure' (Mecway's name), normalised p^T M p = 1 (export_results
    does that for MODE_ACOU with MASS_GENE), and the BRIDGE_MODE lines."""
    import bridge_to_aster as bta
    scripts = os.path.dirname(os.path.abspath(__file__))
    return ("# Results in Mecway's own format (result_route 'liml')\n"
            "import sys\n"
            "sys.path.insert(0, {0})\n"
            "import aster_results_export\n"
            "aster_results_export.print_modes(res)\n"
            "aster_results_export.export_results(\n"
            "    res, {1}, {2},\n"
            "    fields=['pressure'], precision='double'{3})\n").format(
                bta._py_str(scripts), bta._py_str(bta.results_file(work_dir)),
                bta._py_str(model_data.get("liml_path", "")),
                bta.formulas_arg(model_data))


# ==========================================
# COMPLEX CAVITY MODES WITH IMPEDANCE (S2b)
#
# Mecway A30 with <impedance>: quadratic eigenvalue problem (K + lambda C
# + lambda^2 M) P = 0 with C = int rho/Z N N^T dA (manual v33 par. 6.9.2).
# CALC_MODES cannot do that (MATR_AMOR only matr_asse_depl_r/gene_r,
# catalogue calc_modes.py v17.4; AFFE_CHAR_ACOU has no impedance;
# a complex Z gives a complex C). Route:
#   - AFFE_MODELE: volumes '3D' and the impedance faces '3D_ABSO';
#   - ASSEMBLAGE RIGI_ACOU / MASS_ACOU without CHARGE (the pressure nodes
#     are eliminated by aster_acoustic_complex itself);
#   - per impedance CALC_MATR_ELEM AMOR_ACOU with its own CHAM_MATER:
#     CELE_R = 1 on that face (the 3D_ABSO matrix is (1/c) int N N^T dA, without
#     rho, measured in S3a; with c = 1 the surface-mass-like int N N^T
#     dA, sum = area, measured), _CELE_OTHER on the other
#     impedance faces (contribution 1e-30: negligible);
#   - aster_acoustic_complex.solve_modes (scipy, in the job): C = sum
#     rho/Z_g A_g, linearisation + shift-invert, export as Mecway's
#     complex modes (frequency + decayrate, pressure + pressurei).
# Measured (tube hard / Z, hex20; verification AI): equal to Mecway 33
# headless up to 1e-9 and to the analytical roots.
# ==========================================
_CELE_OTHER = 1.0e30


def _impedance_inputs(model_data, ac, mats):
    """
    Impedance boundaries for the complex modes: [(Code-Aster group, rho / Z
    (complex), description, Mecway selection)], or None (ERROR logged).
    Mecway's Z = specificimpedancer + i specificimpedancei (Pa.s/m, number
    without unit); measured headless: Z = 2000 - 1000i gives the same
    eigenvalues as C = rho/Z int N N dA in a separate calculation.
    """
    renames = model_data.get("selection_renames",
                             model_data.get("group_renames", {}))
    known = model_data.get("mesh_group_names", set())
    faces = model_data.get("face_selection_faces", {})
    out, bad = [], []
    for sel, zr, zi in ac.get("impedance_values", []):
        if sel not in faces:
            bad.append(tr("impedantie op '{0}': kies een vlakselectie",
                          "impedance on '{0}': choose a face "
                          "selection").format(sel))
            continue
        if zr is None or zi is None:
            bad.append(tr("impedantie op '{0}': Re Z en Im Z moeten getallen "
                          "zijn (Pa.s/m, zonder eenheid)",
                          "impedance on '{0}': Re Z and Im Z must be numbers "
                          "(Pa.s/m, without unit)").format(sel))
            continue
        z = complex(zr, zi)
        if abs(z) == 0.0:
            bad.append(tr("impedantie op '{0}' is 0; gebruik fluid pressure "
                          "= 0 voor een drukknoop (open einde)",
                          "impedance on '{0}' is 0; use fluid pressure = 0 "
                          "for a pressure node (open end)").format(sel))
            continue
        media = _face_media(model_data, sel, mats)
        if len(media) != 1:
            bad.append(tr("impedantie '{0}' ligt aan {1} media ({2}); maak "
                          "per medium een eigen selectie",
                          "impedance '{0}' borders {1} media ({2}); make a "
                          "separate selection per medium").format(
                              sel, len(media), ", ".join(media) or "-"))
            continue
        mat = media[0]
        rho = ac["materials"].get(mat, {}).get("rho") or 0.0
        if rho <= 0.0:
            # Without density Mecway solves with rho = 0: the impedance
            # then has no effect (seen headless: Z = 2000 without density gave
            # the modes of a hard wall, decay rate ~1e-10).
            bad.append(tr("impedantie op '{0}': materiaal '{1}' heeft geen "
                          "dichtheid; de randterm is rho / Z (Mecway rekent "
                          "zonder dichtheid met rho = 0: een harde wand)",
                          "impedance on '{0}': material '{1}' has no "
                          "density; the boundary term is rho / Z (without a "
                          "density Mecway uses rho = 0: a hard wall)").format(
                              sel, mat))
            continue
        name = renames.get(sel, sel)
        if name not in known:
            log(tr("WARNING: Akoestiek: impedantieselectie '{0}' is leeg; "
                   "overgeslagen.",
                   "WARNING: Acoustics: impedance selection '{0}' is empty; "
                   "skipped.").format(sel))
            continue
        c = mats[mat][0]
        ratio = z / (rho * c)
        refl = (z - rho * c) / (z + rho * c)
        log("INFO: Acoustics: impedance Z = {0} {1} {2}i Pa.s/m on '{3}' "
            "(Z / (rho c) = {4} {5} {6}i; reflection factor at normal "
            "incidence |R| = {7}).".format(
                "%.6g" % z.real, "-" if z.imag < 0 else "+",
                "%.6g" % abs(z.imag), sel, "%.4g" % ratio.real,
                "-" if ratio.imag < 0 else "+", "%.4g" % abs(ratio.imag),
                "%.4g" % abs(refl)))
        if z.real < 0.0:
            log(tr("WARNING: Akoestiek: impedantie op '{0}' heeft Re Z < 0: "
                   "de rand voert energie toe; modes groeien aan (negatieve "
                   "decay rate).",
                   "WARNING: Acoustics: impedance on '{0}' has Re Z < 0: "
                   "the boundary adds energy; modes grow (negative decay "
                   "rate).").format(sel))
        out.append((name, rho / z, "{0}: Z = {1}".format(
            sel, ("%.6g" % z.real) + ("%+.6gi" % z.imag if z.imag else "")),
            sel, mat))
    if bad:
        log(tr("ERROR: Akoestiek: {0}.", "ERROR: Acoustics: {0}.").format(
            "; ".join(bad)))
        return None
    if not out:
        log(tr("ERROR: Akoestiek: alle impedantieselecties zijn leeg.",
               "ERROR: Acoustics: all impedance selections are empty."))
        return None
    return out


def _cplx(z):
    """complex(..) as a Python literal for the .comm."""
    return "complex({0}, {1})".format(_r(z.real), _r(z.imag))


def _complex_modes_comm(work_dir, model_data, msh_path, resu_name, analysis,
                        ac, elsets, mats):
    """
    .comm and .export for the complex cavity modes (impedance, see the block
    above). Same template as the real cavity modes
    (AsterTemplate_Akoestiek.comm); the 'CALC_MODES' section calls
    aster_acoustic_complex. Returns the path to the .export or None.
    """
    import bridge_to_aster as bta
    imps = _impedance_inputs(model_data, ac, mats)
    if imps is None:
        return None
    vol = [es for es, _m in elsets]
    faces = []
    for g, _coef, _label, _sel, _mat in imps:
        if g not in faces:
            faces.append(g)
    mod_area, mod_abso = _modelisations(model_data)
    model_block = ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n    AFFE=(\n"
                   "        _F(GROUP_MA={0}, PHENOMENE='ACOUSTIQUE', "
                   "MODELISATION='{2}'),\n"
                   "        _F(GROUP_MA={1}, PHENOMENE='ACOUSTIQUE', "
                   "MODELISATION='{3}'),\n    ),\n)\n").format(
                       _fmt_groups(vol), _fmt_groups(faces), mod_area,
                       mod_abso)
    names = OrderedDict()
    mat_lines = []
    for k, (mat, (c, rho)) in enumerate(mats.items()):
        names[mat] = "MAC{0}".format(k + 1)
        mat_lines.append("{0}{1} = DEFI_MATERIAU(FLUIDE=_F(RHO={2}, "
                         "CELE_R={3}))".format(bta._mat_comment(mat),
                                               names[mat], _r(rho), _r(c)))
    mat_lines.append(
        "# Impedance faces: CELE_R = 1 gives AMOR_ACOU = int N N dA "
        "(bridge_acoustic,\n# complex modes); the other impedance faces "
        "in the same matrix ~0.\n"
        "MAZ1 = DEFI_MATERIAU(FLUIDE=_F(RHO=1.0, CELE_R=1.0))\n"
        "MAZ0 = DEFI_MATERIAU(FLUIDE=_F(RHO=1.0, CELE_R={0}))".format(
            _r(_CELE_OTHER)))
    face_mat = dict((g, names[mat]) for g, _c, _l, _s, mat in imps)
    vol_assign = "".join("        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        es, names[m]) for es, m in elsets)
    fieldmat_block = ("fieldmat = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n"
                      "    MODELE=model,\n    AFFE=(\n{0}{1}    ),\n)\n").format(
                          vol_assign, "".join(
                              "        _F(GROUP_MA='{0}', MATER={1}),\n"
                              .format(g, face_mat[g]) for g in faces))

    # --- pressure nodes: eliminated in aster_acoustic_complex ---
    dirichlet = []
    renames = model_data.get("selection_renames",
                             model_data.get("group_renames", {}))
    known = model_data.get("mesh_group_names", set())
    for sel, kind in ac["pressure0"]:
        name = renames.get(sel, sel)
        if name not in known:
            log(tr("WARNING: Akoestiek: selectie '{0}' van fluid pressure is "
                   "leeg; overgeslagen.",
                   "WARNING: Acoustics: selection '{0}' of fluid pressure is "
                   "empty; skipped.").format(sel))
            continue
        dirichlet.append(("GROUP_NO" if kind == "node" else "GROUP_MA", name))
    extra = model_data.get("aster_custom", {}).get("excit", [])
    if extra:
        log(tr("WARNING: Akoestiek: #ASTER-EXCIT ({0}) wordt bij complexe "
               "modes (impedantie) niet gebruikt: de matrices worden zonder "
               "lasten geassembleerd.",
               "WARNING: Acoustics: #ASTER-EXCIT ({0}) is not used for "
               "complex modes (impedance): the matrices are assembled "
               "without loads.").format(", ".join(extra)))
    loads_block = ("#-- pressure nodes: eliminated in aster_acoustic_complex "
                   "({0}) --\n".format(", ".join(n for _k, n in dirichlet)
                                       or "none") +
                   bta._custom_code(model_data, "code"))

    lines = ["ASSEMBLAGE(",
             "    MODELE=model,",
             "    CHAM_MATER=fieldmat,",
             "    NUME_DDL=CO('numedd'),",
             "    MATR_ASSE=(",
             "        _F(MATRICE=CO('rigi_c'), OPTION='RIGI_ACOU'),",
             "        _F(MATRICE=CO('mass_c'), OPTION='MASS_ACOU'),",
             "    ),",
             ")"]
    damping = []
    for k, (g, coef, label, _sel, _mat) in enumerate(imps):
        idx = k + 1
        lines += ["# Impedance {0}".format(label),
                  "chz{0} = AFFE_MATERIAU(".format(idx),
                  "    MAILLAGE=mesh,",
                  "    MODELE=model,",
                  "    AFFE=(",
                  vol_assign.rstrip("\n")]
        lines += ["        _F(GROUP_MA='{0}', MATER={1}),".format(
            f, "MAZ1" if f == g else "MAZ0") for f in faces]
        lines += ["    ),",
                  ")",
                  "mez{0} = CALC_MATR_ELEM(OPTION='AMOR_ACOU', MODELE=model, "
                  "CHAM_MATER=chz{0})".format(idx),
                  "amz{0} = ASSE_MATRICE(MATR_ELEM=mez{0}, NUME_DDL=numedd)"
                  .format(idx)]
        damping.append("(amz{0}, {1}, {2})".format(idx, _cplx(coef),
                                                   bta._py_str(label)))
    assemblage_block = "\n".join(lines) + "\n"

    n = bta._mode_count(model_data, analysis)
    shift = float(analysis.get("modal_shift_hz", 0.0) or 0.0)
    free = _free_shift(model_data, elsets, mats)
    c_min = min(c for c, _rho in mats.values())
    size = -0.1 * c_min / (2.0 * free) if free < 0.0 else 1.0
    scripts = os.path.dirname(os.path.abspath(__file__))
    calc_modes_block = (
        "# Complex modes (impedance): quadratic eigenvalue problem\n"
        "# (K + l C + l^2 M) P = 0, C = sum rho/Z int N N dA (Mecway manual\n"
        "# par. 6.9.2), solved with scipy in aster_acoustic_complex\n"
        "# (CALC_MODES does not take MATR_AMOR for pressure matrices).\n"
        "import sys\n"
        "sys.path.insert(0, {0})\n"
        "import aster_acoustic_complex\n"
        "aster_acoustic_complex.solve_modes(\n"
        "    rigi_c, mass_c, [\n{1}    ],\n"
        "    numedd, mesh, {2}, {3},\n"
        "    n_modes={4}, dirichlet={5},\n"
        "    shift_hz={6}, free_shift_hz={7}, c_ref={8}, size_ref={9},\n"
        "    tolerance={10}, precision='double')\n").format(
            bta._py_str(scripts),
            "".join("        {0},\n".format(d) for d in damping),
            bta._py_str(bta.results_file(work_dir)),
            bta._py_str(model_data.get("liml_path", "")), n,
            repr(dirichlet), _r(shift), _r(free), _r(c_min), _r(size),
            "%.10g" % float(analysis.get("modal_tolerance", 1.0e-6)))
    log("INFO: Acoustics: {0} impedance boundary(ies): complex modes "
        "(frequency and decay rate), {1} modes{2}.".format(
            len(imps), n, (" around {0} Hz".format("%.6g" % shift)
                           if shift > 0.0 else " with the smallest |lambda| "
                           "(as in Mecway)")))
    if shift < 0.0:
        log(tr("WARNING: Akoestiek: een negatieve zoekfrequentie telt bij "
               "complexe modes niet; de modes met de kleinste |lambda| "
               "(zoals Mecway).",
               "WARNING: Acoustics: a negative search frequency does not "
               "apply to complex modes; the modes with the smallest "
               "|lambda| (like Mecway)."))
    export_block = bta._custom_code(model_data, "post")
    if CONFIG_BRIDGE.get("med_export", False):
        log(tr("WARNING: Akoestiek: geen MED-export bij complexe modes "
               "(impedantie): er is geen Code-Aster-resultaat; de modes "
               "staan alleen in Mecway.",
               "WARNING: Acoustics: no MED export for complex modes "
               "(impedance): there is no Code-Aster result; the modes are "
               "only in Mecway."))
    blocks = dict(model_block=model_block,
                  materials_block="\n".join(mat_lines) + "\n",
                  fieldmat_block=fieldmat_block, loads_block=loads_block,
                  assemblage_block=assemblage_block,
                  calc_modes_block=calc_modes_block,
                  export_block=export_block or "#-- no #ASTER-POST --\n",
                  impr_resu_block="#-- no MED export (complex modes: no "
                                  "Code-Aster result) --\n")
    return _write_modes_files(work_dir, analysis, msh_path, resu_name, blocks,
                              med=False)


def _write_modes_files(work_dir, analysis, msh_path, resu_name, blocks,
                       med=True):
    """The .comm (template analysis["template"], placeholders blocks) and the
    .export; returns the path to the .export or None (ERROR logged). med
    False: no .rmed in the .export (nothing is written to UNITE 80)."""
    import bridge_to_aster as bta
    result_lines = bta._export_result_lines(work_dir, resu_name)
    if not med:
        result_lines = "".join("\n" + line for line in
                               result_lines.split("\n")
                               if line and not line.startswith("F rmed"))
    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = bta._read_template(analysis["template"])
        bta._write_comm(comm_path, template.format(**blocks))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        with open(export_path, "w") as f:
            f.write("\n".join([
                "P actions make_etude",
                "P time_limit {0}".format(analysis.get("time_limit", 900)),
                "P memory_limit {0}".format(analysis.get("memory_limit", 2048)),
                "P mpi_nbcpu 1",
                "P ncpus {0}".format(CONFIG_BRIDGE["ncpus"]),
                "P no-mpi true",
                "F comm {0} D 1".format(comm_path),
                "F mail {0} D 20".format(msh_path),
                "F mess {0} R 6".format(os.path.join(work_dir,
                                                     run_name(".mess"))),
            ]) + result_lines)
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren akoestische solver-bestanden mislukt: {0}",
               "ERROR: Generating the acoustic solver files failed: {0}")
            .format(str(e)))
    return None


# ==========================================
# HARMONIC PRESSURE FIELD (S3a): DYNA_VIBRA TYPE_CALCUL='HARM'
#
# Mecway has no harmonic analysis (manual v33 chapter 6); the bridge
# solves the A30 model (materials, fluid pressure, impedance) with:
#   source      face selection BRON_... / SOURCE_... (normal velocity
#               source_velocity, into the fluid) or #ASTER-BRON selection =
#               v [, phase]  -> AFFE_CHAR_ACOU VITE_FACE VNOR
#               fluid pressure != 0  -> imposed pressure (PRES_IMPO)
#   absorbing   face selection ABSORBEREND_... / ABSORBING_... -> 3D_ABSO
#               (rho c of the medium); Mecway impedance with real Z
#               -> 3D_ABSO with its own material CELE_R = Z / rho
#   microphone  node selection MICROFOON_... / MICROPHONE_... -> CSV and
#               BRIDGE_MIC lines (aster_acoustic_export)
# Code-Aster route: test case ahlv100a (ASSEMBLAGE RIGI_ACOU, MASS_ACOU,
# AMOR_ACOU and VECT_ASSE CHAR_ACOU; DYNA_VIBRA HARM PHYS with EXCIT
# VECT_ASSE, PUIS_PULS=1, PHAS_DEG=90).
# Measured in runs (Code-Aster 17.4, tube 1 x 0.1 x 0.1 m, hex20):
#   - the matrices do not contain rho (see the header); the source does:
#     VITE_FACE VNOR = v with EXCIT COEF_MULT=+1, PUIS_PULS=1, PHAS_DEG=90
#     (= i w v) gave p = +rho c v on the source face with an absorbing end;
#     with COEF_MULT=-1 (ahlv100a) -rho c v. +1 therefore means: v into the
#     fluid (a piston that pushes), p(t) = Re(P e^(i w t)).
#   - VITE_FACE needs the faces in the model (MODELISATION '3D',
#     elements ACOUNA_FACE*) with a material (otherwise <EXCEPTION>
#     CALCUL_20, seen).
#   - 3D_ABSO: AMOR_ACOU = (1/c) int N N dA with c of the material of
#     the face, without rho (RHO 2.4 instead of 1.2 on the face: no difference;
#     CELE_R 680 instead of 340: reflection 1/3, max/min of |p| = 2.000, like
#     an impedance Z = 2 rho c). An impedance Z therefore becomes CELE_R =
#     Z / rho of the medium (Mecway: C = int rho/Z N N dA, manual v33
#     par. 6.9.2). CELE_I (complex c) did NOT give the expected reflection of
#     a complex Z (measured 2.19 instead of 2.62): complex Z -> ERROR.
#   - PRES_IMPO != 0 in VECT_ASSE CHAR_ACOU (with the matrices assembled
#     with CHARGE) gives the imposed pressure; as a separate EXCIT without
#     PUIS_PULS (p = 2 Pa: |p| = 2.000000 along the tube, seen).
# ==========================================
_EDGES = {
    "hex": ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)),
    "wedge": ((0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3), (0, 3),
              (1, 4), (2, 5)),
    "tet": ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)),
}


def _frequencies(analysis, label=None):
    """Ascending list of frequencies [Hz] from harm_freq_list (text, "0" =
    not used) or harm_freq_start/_end/_count/_spacing; None on an
    error (ERROR logged). label: (nl, en) for the message (default
    acoustics harmonic; also bridge_vibroacoustic_harm)."""
    nl, en = label or ("Akoestiek harmonisch", "Acoustics harmonic")
    text = "{0}".format(analysis.get("harm_freq_list", "0") or "0").strip()
    vals = []
    if text not in ("", "0", "0.0"):
        try:
            vals = [float(t) for t in re.split(r"[;,\s]+", text) if t]
        except ValueError:
            vals = None
        if not vals or min(vals) <= 0.0:
            log(tr("ERROR: {1}: frequentielijst "
                   "(harm_freq_list) '{0}' is ongeldig; verwacht getallen > 0 "
                   "in Hz gescheiden door komma's, bijv. '100, 250, 500' "
                   "(punt als decimaalteken), of 0 voor het bereik.",
                   "ERROR: {1}: frequency list "
                   "(harm_freq_list) '{0}' is invalid; expected numbers > 0 "
                   "in Hz separated by commas, e.g. '100, 250, 500' (point "
                   "as decimal separator), or 0 for the range.").format(
                       text, tr(nl, en)))
            return None
    else:
        try:
            f0 = float(analysis.get("harm_freq_start", 0.0))
            f1 = float(analysis.get("harm_freq_end", 0.0))
            n = int(analysis.get("harm_freq_count", 1))
        except (TypeError, ValueError):
            f0, f1, n = 0.0, 0.0, 0
        spacing = "{0}".format(analysis.get("harm_freq_spacing", "lin"))
        if f0 <= 0.0 or f1 < f0 or n < 1:
            log(tr("ERROR: {3}: frequentiebereik {0} .. {1} "
                   "Hz met {2} stappen is ongeldig (start > 0, eind >= "
                   "start, aantal >= 1).",
                   "ERROR: {3}: frequency range {0} .. {1} Hz "
                   "with {2} steps is invalid (start > 0, end >= start, "
                   "count >= 1).").format(f0, f1, n, tr(nl, en)))
            return None
        if n == 1 or f1 == f0:
            vals = [f0]
        elif spacing == "log":
            vals = [f0 * (f1 / f0) ** (k / float(n - 1)) for k in range(n)]
        else:
            vals = [f0 + (f1 - f0) * k / float(n - 1) for k in range(n)]
    out = []
    for v in sorted(vals):
        if not out or v > out[-1] * (1.0 + 1.0e-9):
            out.append(v)
    return out


def _face_media(model_data, sel, mats):
    """Mecway materials of the solid elements on which the faces of the
    selection (Mecway name) lie."""
    elem_elset = model_data.get("_elem_elset", {})
    elsets = model_data.get("elsets", {})
    out = []
    for eid, _fid in model_data.get("face_selection_faces", {}).get(sel, []):
        mat = elsets.get(elem_elset.get(eid))
        if mat in mats and mat not in out:
            out.append(mat)
    return out


def _wavelength_check(model_data, elsets, mats, f_max):
    """WARNING if the largest element edge is more than lambda / N at the
    highest frequency (N = _MIN_PER_WAVELENGTH, linear/quadratic);
    INFO with the smallest number of elements per wavelength."""
    keep = dict(elsets)
    nodes = model_data.get("mesh_nodes", {})
    elem_elset = model_data.get("_elem_elset", {})
    worst = None
    n_bad = 0
    for eid, shape, enodes, elset in model_data.get("mesh_elements", []):
        name = elem_elset.get(eid, elset)
        mat = keep.get(name)
        if mat is None:
            continue
        edges = _EDGES.get(shape.rstrip("0123456789"))
        if not edges:
            continue
        h = 0.0
        for a, b in edges:
            pa, pb = nodes.get(enodes[a]), nodes.get(enodes[b])
            if pa is None or pb is None:
                continue
            h = max(h, math.sqrt(sum((pa[k] - pb[k]) ** 2
                                     for k in range(3))))
        if h <= 0.0:
            continue
        per = mats[mat][0] / f_max / h
        linear = shape in _LINEAR_SHAPES
        if per < _MIN_PER_WAVELENGTH[linear]:
            n_bad += 1
        if worst is None or per < worst[0]:
            worst = (per, linear)
    if worst is None:
        return
    log("INFO: Acoustics harmonic: smallest number of elements per "
        "wavelength at {0} Hz: {1} (largest element edge).".format(
            "%.6g" % f_max, "%.3g" % worst[0]))
    if n_bad:
        log(tr("WARNING: Akoestiek harmonisch: {0} element(en) hebben bij de "
               "hoogste frequentie ({1} Hz) minder dan {2} (lineair) / {3} "
               "(kwadratisch) elementen per golflengte (kleinste: {4}). De "
               "druk en vooral de fase worden dan onnauwkeurig; verfijn het "
               "mesh of verlaag de hoogste frequentie (docs/Akoestiek.md).",
               "WARNING: Acoustics harmonic: {0} element(s) have fewer than "
               "{2} (linear) / {3} (quadratic) elements per wavelength at "
               "the highest frequency ({1} Hz) (smallest: {4}). The pressure "
               "and especially the phase become inaccurate; refine the mesh "
               "or lower the highest frequency (docs/en/Acoustics.md).")
            .format(n_bad, "%.6g" % f_max,
                    "%g" % _MIN_PER_WAVELENGTH[True],
                    "%g" % _MIN_PER_WAVELENGTH[False], "%.3g" % worst[0]))


def _ri(z):
    """Complex number as ('RI', re, im) for the .comm (ahlv100a)."""
    return "('RI', {0}, {1})".format(_r(z.real), _r(z.imag))


def _harm_inputs(model_data, analysis, ac, mats):
    """
    Sources, absorbing faces and microphones to Code-Aster names.
    Returns dict or None (ERROR logged):
      "vite":  [(group, complex v [m/s], description)]
      "pres":  [(GROUP_NO/GROUP_MA, group, complex p [Pa])]  (also p = 0)
      "abso":  [(group, c [m/s], rho, description)]
      "mics":  OrderedDict {Mecway name: [node numbers]}
      "source_media": {group: Mecway material} (material on the source face)
    """
    renames = model_data.get("selection_renames",
                             model_data.get("group_renames", {}))
    known = model_data.get("mesh_group_names", set())
    faces = model_data.get("face_selection_faces", {})
    named = ac.get("named", {})
    out = {"vite": [], "pres": [], "abso": [], "mics": OrderedDict(),
           "source_media": OrderedDict(), "abso_media": OrderedDict()}
    bad = []
    roles = {}

    def aster(sel):
        name = renames.get(sel, sel)
        return name if name in known else None

    def claim(sel, role):
        if sel in roles and roles[sel] != role:
            bad.append(tr("selectie '{0}' is zowel {1} als {2}",
                          "selection '{0}' is both {1} and {2}").format(
                              sel, roles[sel], role))
        roles[sel] = role

    def one_medium(sel, what):
        media = _face_media(model_data, sel, mats)
        if len(media) != 1:
            bad.append(tr(
                "{0} '{1}' ligt aan {2} media ({3}); maak per medium een "
                "eigen selectie",
                "{0} '{1}' borders {2} media ({3}); make a separate "
                "selection per medium").format(
                    what, sel, len(media), ", ".join(media) or "-"))
            return None
        return media[0]

    # --- sources: velocity ---
    v0 = float(analysis.get("source_velocity", 1.0e-3))
    how = tr("BRON_-selectie", "SOURCE_ selection")
    vel = [(sel, complex(v0, 0.0), how)
           for sel, kind in named.get("source", []) if kind == "face"]
    for sel, kind in named.get("source", []):
        if kind != "face":
            bad.append(tr("bron '{0}' is een {1}selectie; een bron moet "
                          "een vlakselectie zijn",
                          "source '{0}' is a {1} selection; a source must "
                          "be a face selection").format(sel, kind))
    for sel, v, phase in ac.get("aster_sources", []):
        if sel not in faces:
            bad.append(tr("#ASTER-BRON: '{0}' is geen vlakselectie",
                          "#ASTER-BRON: '{0}' is not a face "
                          "selection").format(sel))
            continue
        rad = math.radians(phase)
        # cos(90 degrees) = 6e-17: round, so that 90 degrees is purely imaginary
        re, im = [0.0 if abs(t) < 1.0e-12 else t
                  for t in (math.cos(rad), math.sin(rad))]
        vel = [x for x in vel if x[0] != sel]
        vel.append((sel, complex(v * re, v * im), "#ASTER-BRON"))
    for sel, z, how in vel:
        claim(sel, tr("bron", "source"))
        name = aster(sel)
        if name is None:
            log(tr("WARNING: Akoestiek: bronselectie '{0}' is leeg; "
                   "overgeslagen.",
                   "WARNING: Acoustics: source selection '{0}' is empty; "
                   "skipped.").format(sel))
            continue
        mat = one_medium(sel, tr("bron", "source"))
        if mat is None:
            continue
        out["vite"].append((name, z, "{0} {1}".format(how, sel)))
        out["source_media"][name] = mat
        log("INFO: Acoustics: source '{0}' ({1}): normal velocity {2} m/s, "
            "phase {3} degrees (into the fluid).".format(
                sel, how, "%.6g" % abs(z),
                "%.6g" % math.degrees(math.atan2(z.imag, z.real))))

    # --- imposed pressure (fluid pressure; 0 = pressure node) ---
    for sel, kind in ac.get("pressure0", []):
        name = aster(sel)
        if name is None:
            log(tr("WARNING: Akoestiek: selectie '{0}' van fluid pressure is "
                   "leeg; overgeslagen.",
                   "WARNING: Acoustics: selection '{0}' of fluid pressure is "
                   "empty; skipped.").format(sel))
            continue
        out["pres"].append(("GROUP_NO" if kind == "node" else "GROUP_MA",
                            name, 0j))
    for sel, kind, value, _text in ac.get("pressure_src", []):
        claim(sel, tr("opgelegde druk", "imposed pressure"))
        name = aster(sel)
        if name is None:
            continue
        out["pres"].append(("GROUP_NO" if kind == "node" else "GROUP_MA",
                            name, complex(value, 0.0)))
        log("INFO: Acoustics: imposed pressure {0} Pa on '{1}' (fluid "
            "pressure; source).".format("%.6g" % value, sel))

    # --- absorbing boundaries ---
    for sel, kind in named.get("absorbing", []):
        if kind != "face":
            bad.append(tr("absorberende rand '{0}' is een {1}selectie; "
                          "kies een vlakselectie",
                          "absorbing boundary '{0}' is a {1} selection; "
                          "choose a face selection").format(sel, kind))
            continue
        claim(sel, tr("absorberend", "absorbing"))
        name = aster(sel)
        mat = one_medium(sel, tr("absorberende rand", "absorbing boundary"))
        if name is None or mat is None:
            continue
        c, rho = mats[mat]
        out["abso"].append((name, c, rho, "rho c ({0})".format(mat)))
        out["abso_media"][name] = mat
    for sel, zr, zi in ac.get("impedance_values", []):
        claim(sel, tr("impedantie", "impedance"))
        name = aster(sel)
        if sel not in faces:
            bad.append(tr("impedantie op '{0}': kies een vlakselectie",
                          "impedance on '{0}': choose a face "
                          "selection").format(sel))
            continue
        if zr is None or zi is None or zr <= 0.0:
            bad.append(tr("impedantie op '{0}': Re Z moet een getal > 0 zijn "
                          "(Pa.s/m)",
                          "impedance on '{0}': Re Z must be a number > 0 "
                          "(Pa.s/m)").format(sel))
            continue
        if zi != 0.0:
            bad.append(tr(
                "impedantie op '{0}' is complex (Im Z = {1}); de bridge "
                "vertaalt in de harmonische analyse alleen een reele Z "
                "(KNOWN_BUGS 57)",
                "impedance on '{0}' is complex (Im Z = {1}); in the "
                "harmonic analysis the bridge only translates a real Z "
                "(KNOWN_BUGS 57)").format(sel, "%g" % zi))
            continue
        mat = one_medium(sel, tr("impedantie", "impedance"))
        if name is None or mat is None:
            continue
        rho_given = ac["materials"].get(mat, {}).get("rho") or 0.0
        if rho_given <= 0.0:
            bad.append(tr(
                "impedantie op '{0}': materiaal '{1}' heeft geen dichtheid "
                "(nodig voor Z / rho, zoals in Mecway)",
                "impedance on '{0}': material '{1}' has no density (needed "
                "for Z / rho, as in Mecway)").format(sel, mat))
            continue
        out["abso"].append((name, zr / rho_given, rho_given,
                            "Z = {0} Pa.s/m ({1})".format("%g" % zr, mat)))
        out["abso_media"][name] = mat
        log("INFO: Acoustics: impedance Z = {0} Pa.s/m on '{1}' "
            "(Z / (rho c) = {2}): absorbing boundary 3D_ABSO with c = Z / rho "
            "= {3} m/s.".format("%g" % zr, sel,
                                "%.4g" % (zr / (rho_given * mats[mat][0])),
                                "%.6g" % (zr / rho_given)))

    # --- microphones ---
    for sel, kind in named.get("microphone", []):
        if kind != "node":
            log(tr("WARNING: Akoestiek: microfoon '{0}' is een {1}selectie; "
                   "alleen knoopselecties tellen; overgeslagen.",
                   "WARNING: Acoustics: microphone '{0}' is a {1} "
                   "selection; only node selections count; "
                   "skipped.").format(sel, kind))
            continue
        nids = [int(str(n).lstrip("N")) for n in
                model_data.get("node_groups", {}).get(sel, [])]
        if nids:
            out["mics"][sel] = nids
    if bad:
        log(tr("ERROR: Akoestiek harmonisch: {0}.",
               "ERROR: Acoustics harmonic: {0}.").format("; ".join(bad)))
        return None
    if not out["vite"] and not any(abs(p) > 0.0 for _g, _n, p
                                   in out["pres"]):
        log(tr("ERROR: Akoestiek harmonisch: geen bron. Geef een "
               "vlakselectie de naam BRON_... (normaalsnelheid "
               "source_velocity), gebruik '#ASTER-BRON selectie = "
               "snelheid', of een fluid pressure != 0 (opgelegde druk).",
               "ERROR: Acoustics harmonic: no source. Name a face "
               "selection SOURCE_... (normal velocity source_velocity), "
               "use '#ASTER-BRON selection = velocity', or a fluid "
               "pressure != 0 (imposed pressure)."))
        return None
    if not out["abso"]:
        log(tr("WARNING: Akoestiek harmonisch: geen absorberende rand "
               "(ABSORBEREND_-selectie of impedance): zonder demping is "
               "de respons bij een holtemode oneindig groot. Kies "
               "frequenties tussen de resonanties of voeg een "
               "absorberende rand toe.",
               "WARNING: Acoustics harmonic: no absorbing boundary "
               "(ABSORBING_ selection or impedance): without damping the "
               "response at a cavity mode is infinite. Choose frequencies "
               "between the resonances or add an absorbing boundary."))
    return out


def build_acoustic_harm(work_dir, model_data, msh_path, resu_name, analysis):
    """
    Generate the .comm and .export for the harmonic pressure field
    (acoustic_harm_3d; bridge_to_aster._build_dyna_modal sends an
    acoustic DYNA_VIBRA analysis here). Returns the path to the
    .export, or None on an error.
    """
    import bridge_to_aster as bta
    log("--- Generating Aster Files (DYNA_VIBRA HARM akoestisch) ---")
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor de "
               "harmonische akoestiek. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for harmonic "
               "acoustics. Choose 'liml' (General page)."))
        return None
    ac = model_data.get("acoustic_data")
    if ac is None:
        log(tr("ERROR: Geen akoestische gegevens gelezen; is het Mecway-"
               "analysetype A30 (Acoustic Resonance 3D)?",
               "ERROR: No acoustic data read; is the Mecway analysis type "
               "A30 (Acoustic Resonance 3D)?"))
        return None
    if ac["bad"]:
        log(tr("ERROR: Akoestiek: {0}.", "ERROR: Acoustics: {0}.").format(
            "; ".join(ac["bad"])))
        return None
    if model_data.get("analysis_type") == "A20":
        # (bridge_plane._apply_acoustic already stops; defensive)
        log(tr("ERROR: Het harmonische drukveld wordt voor Acoustic "
               "Resonance 2D (A20) niet vertaald: Mecway heeft in 2D geen "
               "harmonische akoestiek (geen frequentie- of broninvoer). "
               "Kies de holtemodes (acoustic_modes_3d) of een 3D-model "
               "(A30).",
               "ERROR: The harmonic pressure field is not translated for "
               "Acoustic Resonance 2D (A20): Mecway has no harmonic "
               "acoustics in 2D (no frequency or source input). Choose the "
               "cavity modes (acoustic_modes_3d) or a 3D model (A30)."))
        return None
    elsets = _elsets(model_data)
    if elsets is None:
        return None
    mats = _materials(elsets, ac)
    if mats is None:
        return None
    freqs = _frequencies(analysis)
    if freqs is None:
        return None
    inp = _harm_inputs(model_data, analysis, ac, mats)
    if inp is None:
        return None
    no_rho = [m for m in mats if not ac["materials"].get(m, {}).get("rho")]
    if inp["vite"] and no_rho:
        # The source is i w rho v (VITE_FACE): without density p would be
        # c v instead of rho c v (RHO = 1).
        log(tr("ERROR: Akoestiek harmonisch: materiaal {0} heeft geen "
               "dichtheid; een snelheidsbron geeft p = rho c v. Vul in "
               "Mecway bij het materiaal een dichtheid in (bijv. 1.2 kg/m3 "
               "voor lucht).",
               "ERROR: Acoustics harmonic: material {0} has no density; a "
               "velocity source gives p = rho c v. Fill in a density for "
               "the material in Mecway (e.g. 1.2 kg/m3 for air).").format(
                   ", ".join("'%s'" % m for m in no_rho)))
        return None
    _wavelength_check(model_data, elsets, mats, freqs[-1])
    log("INFO: Acoustics harmonic: {0} frequency(ies) from {1} to {2} "
        "Hz.".format(len(freqs), "%.6g" % freqs[0], "%.6g" % freqs[-1]))

    # --- model: volumes and source faces 3D, absorbing faces 3D_ABSO ---
    vol = [es for es, _m in elsets]
    src = list(item[0] for item in inp["vite"] if item[0] not in vol)
    src = [g for k, g in enumerate(src) if g not in src[:k]]
    abso = [a[0] for a in inp["abso"]]
    model_block = ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n    AFFE=(\n"
                   "        _F(GROUP_MA={0}, PHENOMENE='ACOUSTIQUE', "
                   "MODELISATION='3D'),\n").format(_fmt_groups(vol + src))
    if abso:
        model_block += ("        _F(GROUP_MA={0}, PHENOMENE='ACOUSTIQUE', "
                        "MODELISATION='3D_ABSO'),\n").format(
                            _fmt_groups(abso))
    model_block += "    ),\n)\n"

    # --- materials ---
    names = OrderedDict()
    mat_lines = []
    for k, (mat, (c, rho)) in enumerate(mats.items()):
        names[mat] = "MAC{0}".format(k + 1)
        mat_lines.append("{0}{1} = DEFI_MATERIAU(FLUIDE=_F(RHO={2}, "
                         "CELE_R={3}))".format(bta._mat_comment(mat),
                                               names[mat], _r(rho), _r(c)))
    assign = ["        _F(GROUP_MA='{0}', MATER={1}),\n".format(es, names[m])
              for es, m in elsets]
    assign += ["        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        g, names[inp["source_media"][g]]) for g in src]
    for k, (g, c, rho, desc) in enumerate(inp["abso"]):
        mat = inp["abso_media"][g]
        if abs(c - mats[mat][0]) <= 1.0e-12 * mats[mat][0]:
            mname = names[mat]
        else:
            # impedance: own material with c = Z / rho (see above)
            mname = "MAZ{0}".format(k + 1)
            mat_lines.append("# absorbing boundary '{0}': {1}\n{2} = "
                             "DEFI_MATERIAU(FLUIDE=_F(RHO={3}, CELE_R={4}))"
                             .format(g, desc, mname, _r(rho), _r(c)))
        assign.append("        _F(GROUP_MA='{0}', MATER={1}),\n".format(
            g, mname))
    fieldmat_block = ("fieldmat = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n"
                      "    MODELE=model,\n    AFFE=(\n{0}    ),\n)\n").format(
                          "".join(assign))

    # --- loads ---
    loads = []
    if inp["vite"]:
        loads.append("# Source: normal velocity into the fluid (VITE_FACE VNOR)\n"
                     "ch_vite = AFFE_CHAR_ACOU(\n    MODELE=model,\n"
                     "    VITE_FACE=(\n{0}    ),\n)\n".format("".join(
                         "        _F(GROUP_MA='{0}', VNOR={1}),  # {2}\n"
                         .format(g, _ri(v), d) for g, v, d in inp["vite"])))
    if inp["pres"]:
        loads.append("# Imposed pressure (fluid pressure; 0 = pressure node)\n"
                     "bc_pres = AFFE_CHAR_ACOU(\n    MODELE=model,\n"
                     "    PRES_IMPO=(\n{0}    ),\n)\n".format("".join(
                         "        _F({0}='{1}', PRES={2}),\n".format(
                             kw, g, _ri(p)) for kw, g, p in inp["pres"])))
    loads_block = "\n".join(loads) + bta._custom_code(model_data, "code")
    if model_data.get("aster_custom", {}).get("excit"):
        # DYNA_VIBRA HARM only takes VECT_ASSE here (catalogue
        # dyna_vibra.py: CHARGE only char_meca); the bridge cannot put its
        # own acoustic loads in EXCIT.
        log(tr("WARNING: Akoestiek harmonisch: #ASTER-EXCIT wordt niet "
               "gebruikt ({0}); gebruik #ASTER-BRON of een eigen DYNA_VIBRA "
               "in #ASTER-POST.",
               "WARNING: Acoustics harmonic: #ASTER-EXCIT is not used "
               "({0}); use #ASTER-BRON or your own DYNA_VIBRA in "
               "#ASTER-POST.").format(", ".join(
                   model_data["aster_custom"]["excit"])))
    p_source = any(abs(p) > 0.0 for _kw, _g, p in inp["pres"])

    # --- matrices and vectors (ahlv100a) ---
    vect = []
    if inp["vite"]:
        vect.append("        _F(VECTEUR=CO('vec_v'), OPTION='CHAR_ACOU', "
                    "CHARGE=ch_vite),\n")
    if p_source:
        vect.append("        _F(VECTEUR=CO('vec_p'), OPTION='CHAR_ACOU', "
                    "CHARGE=bc_pres),\n")
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{0}"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('rigi_c'), OPTION='RIGI_ACOU'),\n"
        "        _F(MATRICE=CO('mass_c'), OPTION='MASS_ACOU'),\n"
        "{1}"
        "    ),\n"
        "    VECT_ASSE=(\n{2}    ),\n"
        ")\n").format(
            "    CHARGE=(bc_pres,),\n" if inp["pres"] else "",
            "        _F(MATRICE=CO('amor_c'), OPTION='AMOR_ACOU'),\n"
            if abso else "", "".join(vect))

    # --- harmonic calculation ---
    excit = []
    if inp["vite"]:
        # i w x vec_v (see the header of this block: v into the fluid)
        excit.append("        _F(VECT_ASSE=vec_v, COEF_MULT=1.0, "
                     "PUIS_PULS=1, PHAS_DEG=90.0),\n")
    if p_source:
        excit.append("        _F(VECT_ASSE=vec_p, COEF_MULT=1.0),\n")
    harm_block = (
        "freqs = DEFI_LIST_REEL(VALE=({0},))\n"
        "res = DYNA_VIBRA(\n"
        "    TYPE_CALCUL='HARM',\n"
        "    BASE_CALCUL='PHYS',\n"
        "    CHAM_MATER=fieldmat,\n"
        "    MATR_MASS=mass_c,\n"
        "    MATR_RIGI=rigi_c,\n"
        "{1}"
        "    LIST_FREQ=freqs,\n"
        "    EXCIT=(\n{2}    ),\n"
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={3}),\n"
        ")\n").format(", ".join(_r(f) for f in freqs),
                      "    MATR_AMOR=amor_c,\n" if abso else "",
                      "".join(excit), int(analysis.get("solver_nprec", 8)))

    export_block = (bta._custom_code(model_data, "post") +
                    _harm_export_block(work_dir, model_data, inp["mics"]))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = (
            "IMPR_RESU(FORMAT='MED', UNITE=80, RESU=(\n"
            "    _F(RESULTAT=res, NOM_CHAM='PRES', PARTIE='REEL', "
            "NOM_CHAM_MED='PRES_REEL'),\n"
            "    _F(RESULTAT=res, NOM_CHAM='PRES', PARTIE='IMAG', "
            "NOM_CHAM_MED='PRES_IMAG'),\n))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = bta._read_template(analysis["template"])
        bta._write_comm(comm_path, template.format(
            model_block=model_block,
            materials_block="\n".join(mat_lines) + "\n",
            fieldmat_block=fieldmat_block,
            loads_block=loads_block,
            assemblage_block=assemblage_block,
            harm_block=harm_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        with open(export_path, "w") as f:
            f.write("\n".join([
                "P actions make_etude",
                "P time_limit {0}".format(analysis.get("time_limit", 900)),
                "P memory_limit {0}".format(analysis.get("memory_limit", 2048)),
                "P mpi_nbcpu 1",
                "P ncpus {0}".format(CONFIG_BRIDGE["ncpus"]),
                "P no-mpi true",
                "F comm {0} D 1".format(comm_path),
                "F mail {0} D 20".format(msh_path),
                "F mess {0} R 6".format(os.path.join(work_dir,
                                                     run_name(".mess"))),
            ]) + bta._export_result_lines(work_dir, resu_name))
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren akoestische solver-bestanden mislukt: {0}",
               "ERROR: Generating the acoustic solver files failed: {0}")
            .format(str(e)))
    return None


MIC_SUFFIX = "_microfoons.csv"


def _harm_export_block(work_dir, model_data, mics):
    """aster_acoustic_export: one <mode> per frequency (pressure,
    pressurei, pressuremag, pressurephase, spl) and the microphones."""
    import bridge_to_aster as bta
    scripts = os.path.dirname(os.path.abspath(__file__))
    mic_text = "{" + ", ".join("{0}: [{1}]".format(
        bta._py_str(name), ", ".join(str(n) for n in nids))
        for name, nids in mics.items()) + "}"
    return ("# Results in Mecway's own format (result_route 'liml')\n"
            "import sys\n"
            "sys.path.insert(0, {0})\n"
            "import aster_acoustic_export\n"
            "aster_acoustic_export.export_harmonic(\n"
            "    res, {1}, {2},\n"
            "    microphones={3},\n"
            "    csv_path={4},\n"
            "    language={5})\n").format(
                bta._py_str(scripts), bta._py_str(bta.results_file(work_dir)),
                bta._py_str(model_data.get("liml_path", "")), mic_text,
                bta._py_str(os.path.join(work_dir, run_name(MIC_SUFFIX))),
                bta._py_str(CONFIG_BRIDGE.get("language", "en")))


# ==========================================
# AFTER THE RUN: MICROPHONES IN THE LOG (IronPython)
# ==========================================
def read_microphones(csv_path):
    """[(name, f, amplitude, phase, spl)] from the CSV of
    aster_acoustic_export; [] if it is missing."""
    import csv
    out = []
    if not csv_path or not os.path.isfile(csv_path):
        return out
    f = open(csv_path, "r")
    try:
        rows = list(csv.reader(f))
    finally:
        f.close()
    for row in rows[1:]:
        try:
            out.append((row[0], float(row[1]), float(row[4]),
                        float(row[5]), float(row[6])))
        except (IndexError, ValueError):
            continue
    return out


def report_harmonic(work_dir, frequencies):
    """
    After a harmonic run: number of frequencies and per microphone the
    highest sound pressure level in the log; the lines for the status box.
    frequencies: [(id, "frequency", f)] from read_modes().
    """
    path = os.path.join(work_dir, run_name(MIC_SUFFIX))
    lines = [tr(u"Akoestiek harmonisch: {0} frequentie(s), {1} .. {2} Hz. "
                u"Velden in Mecway per frequentie: pressure (Re), pressurei "
                u"(Im), pressuremag (|p|), pressurephase (graden), spl (dB "
                u"re 20 uPa).",
                u"Acoustics harmonic: {0} frequency(ies), {1} .. {2} Hz. "
                u"Fields in Mecway per frequency: pressure (Re), pressurei "
                u"(Im), pressuremag (|p|), pressurephase (degrees), spl (dB "
                u"re 20 uPa).").format(
                    len(frequencies),
                    "%.6g" % min(f for _i, _k, f in frequencies)
                    if frequencies else "-",
                    "%.6g" % max(f for _i, _k, f in frequencies)
                    if frequencies else "-")]
    mics = read_microphones(path)
    by_name = OrderedDict()
    for name, f, amp, phase, level in mics:
        by_name.setdefault(name, []).append((f, amp, phase, level))
    for name, rows in by_name.items():
        f, amp, _ph, level = max(rows, key=lambda r: r[3])
        lines.append(tr(u"Microfoon {0}: hoogste niveau {1} dB bij {2} Hz "
                        u"(|p| = {3} Pa).",
                        u"Microphone {0}: highest level {1} dB at {2} Hz "
                        u"(|p| = {3} Pa).").format(
                            name, "%.1f" % level, "%.6g" % f, "%.4g" % amp))
        for f, amp, phase, level in rows:
            log(u"INFO: Microphone {0}: f = {1} Hz, |p| = {2} Pa, phase = {3} "
                u"degrees, SPL = {4} dB.".format(
                    name, "%.6g" % f, "%.6g" % amp, "%.2f" % phase,
                    "%.2f" % level))
    if by_name:
        lines.append(tr(u"Frequentierespons per microfoon: {0}",
                        u"Frequency response per microphone: {0}").format(
                            path))
    for line in lines:
        log(u"INFO: " + line)
    return lines
