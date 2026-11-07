# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_custom.py
# Responsibility: read #ASTER lines that the user puts in a free text field
# in Mecway, and prepare them for bridge_to_aster.py. This way a model can
# use Code-Aster functions for which Mecway has no input
# (e.g. LIAISON_ELEM for beam-volume connections) without changing the
# bridge.
#
# Where: Mecway's free text fields (XML tags):
#   <ccxmodeldefinition>      CCX > Custom model definition
#   <ccxstep>                 CCX > Custom step contents
#   <radiossmodeldefinition>  OpenRadioss > Custom model definition
#   <radiossengineinput>      OpenRadioss > Custom engine input
#   <nastranbulkdata>         Mystran > Custom bulk data
# A line starts with '#' (comment for OpenRadioss), '**' (CCX) or '$'
# (Mystran/Nastran), then ASTER; so the Mecway solver ignores the line.
# In practice: dynamics/contact in an OpenRadioss analysis, statics in a
# Mystran analysis; the bridge reads the fields regardless of the solver.
#
# Lines (prefix '#', '**' or '$', leading spaces allowed):
#   #ASTER <code>            Code-Aster code, literally before the solve
#                            (after the loads of the bridge). Consecutive
#                            lines form a block; the indentation after
#                            '#ASTER ' is preserved.
#   #ASTER-EXCIT name, ...   add load(s) from #ASTER code to EXCIT
#   #ASTER-CONTACT K=V, ...  extra keywords for DEFI_CONTACT (global)
#   #ASTER-ZONE K=V, ...     extra keywords for each contact zone
#   #ASTER-OPTIE key = value
#                            setting of the active analysis for this
#                            model (e.g. newton_max_iter = 50)
#   #ASTER-POST <code>       Code-Aster code after the solve (before IMPR_RESU)
#   #ASTER-BEZWIJKEN material = strain
#                            elements of this Mecway material fail
#                            at this equivalent plastic strain ('*' =
#                            all plastic materials); also
#                            #ASTER-FAILURE. See bridge_failure.py.
#   #ASTER-SPECTRE X, Y = name [, K=V, ...]
#                            response spectrum (analysis spectrum_3d) for
#                            these directions: a DEFI_NAPPE/DEFI_FONCTION/
#                            FORMULE from #ASTER code (SPEC_OSCI), with
#                            optionally extra keywords for SPECTRE
#                            (ECHELLE, NATURE, CORR_FREQ); also
#                            #ASTER-SPECTRUM. See bridge_spectrum.py.
#   #ASTER-BRON selection = velocity [, phase]
#                            harmonic acoustics (acoustic_harm_3d): a
#                            face selection as source with normal velocity
#                            into the fluid (m/s or mm/s) and phase in
#                            degrees; also #ASTER-SOURCE. See
#                            bridge_acoustic.py. In harmonic vibro-acoustics
#                            (vibroacoustic_harm_3d) also with a pressure
#                            (Pa): an incident wave. See
#                            bridge_vibroacoustic_harm.py.
#   #ASTER-LASBRON K=V, ...  moving weld source (transient thermal; also
#                            #ASTER-WELD). See bridge_welding.py.
#   #ASTER-FASE selection = degrees
#                            harmonic response (harmonic_3d): the
#                            load on this selection gets this phase
#                            (EXCIT PHAS_DEG); also #ASTER-PHASE. See
#                            bridge_harmonic.py.
#   #ASTER-HYST material = eta
#                            harmonic response (harmonic_3d): loss factor
#                            eta of this Mecway material ('*' = all;
#                            AMOR_HYST, complex stiffness K (1 + i eta)).
#                            See bridge_harmonic.py.
#   #ASTER-MATERIAAL name: K=V, ...
#                            temperature-dependent E, nu, alpha, SY, ET
#                            of a Mecway material (chain thermal ->
#                            mechanical; also #ASTER-MATERIAL). See
#                            bridge_thermomech.py.
#   #ASTER-WOHLER material: K=V, ...
#                            Wohler curve for fatigue; also
#                            #ASTER-VERMOEIING/-FATIGUE K=V (options),
#                            #ASTER-BLOK/-BLOCK a, m, n and #ASTER-SIGNAAL/
#                            -SIGNAL f1, f2, ... See bridge_fatigue.py.
#   #ASTER-METALLURGIE name: K=V, ...
#                            phase transformations in steel (TRC, CALC_META)
#                            for a Mecway material (transient thermal; also
#                            #ASTER-METALLURGY). See bridge_metallurgy.py.
#   #ASTER-XFEM K=V, ...     XFEM crack without meshing it (linear
#                            static: K and G along the front). See
#                            bridge_xfem.py.
#   #ASTER-SECTIE material: K=V, ...
#                            extra Code-Aster characteristics of a Mecway
#                            general beam section (AY, AZ, EY, EZ, RY, RZ,
#                            RT, JG, IYR2, IZR2; SI), written by
#                            MecwaySectionProps (own repository); also
#                            #ASTER-SECTION. See
#                            bridge_from_liml._section_extras.
#   #ASTER-RAND selection = CILINDER x, y, z, ax, ay, az, r
#                            adaptive refinement with HOMARD
#                            (adapt_homard): the boundary shape of a face
#                            selection for FRONTIERE_ANALYTIQUE (also BOL x,
#                            y, z, r and GEEN; English #ASTER-BOUNDARY,
#                            CYLINDER/SPHERE/NONE). See bridge_homard.py.
#   <<Mecway-selectie>>      in all lines: the Code-Aster group name of
#                            that selection (bridge_mesh renames names)
#
# Not an #ASTER line, but read here as well (prefix '**' only):
#   ** SECTIE-VORM material: N=17 6, A=1.5e-3
#   ** SECTIE-VORM material: P=v w v w ...
#                            outline of a general section, written by
#                            MecwaySectionProps; collected in file order in
#                            "section_shapes" and worked out in
#                            bridge_section_view.parse_shapes. A run ignores
#                            these lines.
#   ** SECTIE-RICHTING material: V=vx vy vz, U=ux uy uz
#                            directions a general section was made for, global
#                            unit vectors in %.6g, written by
#                            MecwaySectionProps: V = principal axis 1, the V
#                            axis a beam must have, U = the beam direction of
#                            the stored data. Collected in file order in
#                            "section_directions"; see report_directions. Only
#                            a check: mesh, .comm and results do not use them.
#                            The newest good line of a material counts. Must
#                            not start with '** ASTER-SECTIE '.
#
# Example (beam node on a volume face, LIAISON_ELEM OPTION='3D_POU'):
#   #ASTER verb = AFFE_CHAR_MECA(MODELE=model,
#   #ASTER     LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='<<Vlak>>',
#   #ASTER                     GROUP_NO_2='<<Knoop>>'))
#   #ASTER-EXCIT verb
#
# The bridge does not check the Code-Aster syntax of #ASTER code; errors
# come from Code-Aster (study.mess).
#
# Compatible with IronPython 2.7.9.

import math
import re
from collections import OrderedDict

from bridge_utils import log, tr, parse_yes_no

CUSTOM_TAGS = ("ccxmodeldefinition", "ccxstep", "radiossmodeldefinition",
               "radiossengineinput", "nastranbulkdata")

# Also recognise the kind in lower case, so that '#ASTER-Excit' is not
# silently dropped but reported as a kind (or as an unknown kind).
_LINE_RE = re.compile(r"^\s*(?:#|\*\*|\$)\s*ASTER(-[A-Za-z]+)?(?:\s(.*))?$")
# Looks like an #ASTER line (prefix directly followed by ASTER) but
# does not match _LINE_RE, e.g. '#ASTER_EXCIT' or '#ASTER:': report
# instead of silently skipping. Without a space after the prefix, so that
# ordinary CCX comment lines ('** ...') are not affected.
_NEAR_RE = re.compile(r"^\s*(?:#|\*\*|\$)ASTER")
# Outline of a general section (bridge_section_view.py). Must not look like
# an #ASTER line: _LINE_RE and _NEAR_RE only match right after the prefix.
_SHAPE_RE = re.compile(r"^\s*\*\*\s*SECTIE-VORM(?:\s+(.*))?$")
# Directions of a general section (report_directions); the same remark.
_DIRECTION_RE = re.compile(r"^\s*\*\*\s*SECTIE-RICHTING(?:\s+(.*))?$")
_PLACEHOLDER_RE = re.compile(r"<<([^<>]+)>>")
_KINDS = ("", "-EXCIT", "-CONTACT", "-ZONE", "-OPTIE", "-POST",
          "-BEZWIJKEN", "-FAILURE", "-SPECTRE", "-SPECTRUM",
          "-BRON", "-SOURCE", "-LASBRON", "-WELD",
          "-FASE", "-PHASE", "-HYST", "-MATERIAAL", "-MATERIAL",
          "-WOHLER", "-VERMOEIING", "-FATIGUE", "-BLOK", "-BLOCK",
          "-SIGNAAL", "-SIGNAL", "-METALLURGIE", "-METALLURGY",
          "-XFEM", "-CONSTANT", "-SECTIE", "-SECTION",
          "-RAND", "-BOUNDARY")
# Fatigue (bridge_fatigue.py): kind -> key in out["fatigue"]
_FATIGUE_KINDS = {"-WOHLER": "wohler", "-VERMOEIING": "options",
                  "-FATIGUE": "options", "-BLOK": "block", "-BLOCK": "block",
                  "-SIGNAAL": "signal", "-SIGNAL": "signal"}
# Not #ASTER lines: they do not count in the summary of parse()
_SECTION_LINE_KEYS = ("section_shapes", "section_directions")
# Largest angle between a beam and a SECTIE-RICHTING line that passes, degrees
DIRECTION_TOL = 1.0


def empty():
    """Empty structure as parse() returns it."""
    return {"code": [], "excit": [], "contact": [], "zone": [],
            "options": {}, "post": [], "failure": {}, "spectrum": {},
            "sources": [], "welding": [],
            "phases": [], "hyst": [], "materials": [],
            "fatigue": [], "metallurgy": [],
            "xfem": [], "constant": [], "sections": [], "boundaries": [],
            "section_shapes": [], "section_directions": []}


def parse(texts):
    """
    #ASTER lines from the free text fields.

    texts : list of strings (contents of the CUSTOM_TAGS)
    Returns dict with "code"/"post" (lines), "excit" (names),
    "contact"/"zone" (pieces 'K=V'), "options" ({key: text}),
    "section_shapes" (bodies of the ** SECTIE-VORM lines, in order),
    "section_directions" (the same of the ** SECTIE-RICHTING lines).
    """
    out = empty()
    for text in texts:
        for raw in (text or "").splitlines():
            shape = _SHAPE_RE.match(raw.rstrip("\r"))
            if shape:
                out["section_shapes"].append((shape.group(1) or "").strip())
                continue
            direction = _DIRECTION_RE.match(raw.rstrip("\r"))
            if direction:
                out["section_directions"].append(
                    (direction.group(1) or "").strip())
                continue
            m = _LINE_RE.match(raw.rstrip("\r"))
            if not m:
                if _NEAR_RE.match(raw):
                    log(tr("ERROR: Regel lijkt op een #ASTER-regel maar wordt "
                           "niet herkend en wordt overgeslagen (verwacht "
                           "'#ASTER <code>' of '#ASTER-SOORT ...'): {0}",
                           "ERROR: Line looks like an #ASTER line but is "
                           "not recognised and is skipped (expected "
                           "'#ASTER <code>' or '#ASTER-KIND ...'): {0}")
                        .format(raw.strip()))
                continue
            kind = (m.group(1) or "").upper()
            body = m.group(2) or ""
            if kind not in _KINDS:
                log(tr("ERROR: Onbekende regel '#ASTER{0}' wordt "
                       "overgeslagen: {1}",
                       "ERROR: Unknown line '#ASTER{0}' is skipped: "
                       "{1}").format(kind, raw.strip()))
                continue
            if kind == "":
                out["code"].append(body)
            elif kind == "-POST":
                out["post"].append(body)
            elif kind == "-EXCIT":
                out["excit"] += [n.strip() for n in body.split(",")
                                 if n.strip()]
            elif kind == "-CONTACT":
                if body.strip():
                    out["contact"].append(body.strip().rstrip(","))
            elif kind == "-ZONE":
                if body.strip():
                    out["zone"].append(body.strip().rstrip(","))
            elif kind in ("-BEZWIJKEN", "-FAILURE"):
                _parse_failure(body, out["failure"])
            elif kind in ("-SPECTRE", "-SPECTRUM"):
                _parse_spectrum(body, out["spectrum"])
            elif kind in ("-BRON", "-SOURCE"):
                # worked out in bridge_acoustic._parse_aster_sources and
                # bridge_vibroacoustic_harm._aster_sources
                if body.strip():
                    out["sources"].append(body.strip())
            elif kind in ("-LASBRON", "-WELD"):
                if body.strip():
                    out["welding"].append(body.strip())
            elif kind in _FATIGUE_KINDS:
                # worked out in bridge_fatigue.parse
                if body.strip():
                    out["fatigue"].append((_FATIGUE_KINDS[kind],
                                           body.strip()))
            elif kind in ("-FASE", "-PHASE"):
                # worked out in bridge_harmonic._phase_bodies
                if body.strip():
                    out["phases"].append(body.strip())
            elif kind == "-HYST":
                # worked out in bridge_harmonic._loss_factors
                if body.strip():
                    out["hyst"].append(body.strip())
            elif kind == "-XFEM":
                # worked out in bridge_xfem.parse_specs
                if body.strip():
                    out["xfem"].append(body.strip())
            elif kind == "-CONSTANT":
                # Constant (dead) loads in linear buckling, by selection
                # name or load type; worked out in
                # bridge_to_aster._dead_live_split
                out["constant"] += [n.strip() for n in body.split(",")
                                    if n.strip()]
            elif kind in ("-MATERIAAL", "-MATERIAL"):
                # worked out in bridge_thermomech.parse_materials
                if body.strip():
                    out["materials"].append(body.strip())
            elif kind in ("-SECTIE", "-SECTION"):
                # worked out in bridge_from_liml._section_extras
                if body.strip():
                    out["sections"].append(body.strip())
            elif kind in ("-RAND", "-BOUNDARY"):
                # worked out in bridge_homard.parse_boundaries
                if body.strip():
                    out["boundaries"].append(body.strip())
            elif kind in ("-METALLURGIE", "-METALLURGY"):
                # worked out in bridge_metallurgy.parse_specs
                if body.strip():
                    out["metallurgy"].append(body.strip())
            else:
                key, sep, value = body.partition("=")
                if not sep or not key.strip():
                    log(tr("ERROR: '#ASTER-OPTIE {0}': verwacht 'sleutel = "
                           "waarde'.",
                           "ERROR: '#ASTER-OPTIE {0}': expected 'key = "
                           "value'.").format(body.strip()))
                    continue
                out["options"][key.strip()] = value.strip()
    n = sum(len(v) for k, v in out.items() if k not in _SECTION_LINE_KEYS)
    if out["section_shapes"]:
        log("INFO: {0} SECTIE-VORM lines (outline of a general section; a "
            "run does not use them).".format(len(out["section_shapes"])))
    if n:
        log("INFO: #ASTER lines: {0} code, {1} EXCIT, {2} CONTACT, {3} ZONE, "
            "{4} OPTIE, {5} POST, {6} BEZWIJKEN, {7} SPECTRE, {8} BRON, "
            "{9} LASBRON, {10} FASE, {11} MATERIAAL, {12} VERMOEIING, "
            "{13} METALLURGIE, {14} XFEM, {15} CONSTANT, {16} HYST, {17} SECTIE.".format(
                len(out["code"]), len(out["excit"]), len(out["contact"]),
                len(out["zone"]), len(out["options"]), len(out["post"]),
                len(out["failure"]), len(out["spectrum"]),
                len(out["sources"]), len(out["welding"]),
                len(out["phases"]), len(out["materials"]),
                len(out["fatigue"]), len(out["metallurgy"]),
                len(out["xfem"]), len(out["constant"]),
                len(out["hyst"]),
                len(out["sections"])))
    return out


def _unit_vector(values):
    """Unit vector of three numbers (text or float), or None: anything else,
    nan, inf and a length of 0 are no direction."""
    if len(values) != 3:
        return None
    try:
        v = [float(x) for x in values]
    except (TypeError, ValueError):
        return None
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if math.isnan(n) or math.isinf(n) or n == 0.0:
        return None
    return (v[0] / n, v[1] / n, v[2] / n)


def _read_direction(rest):
    """'V=0 1 0, U=1 0 0' -> {"V": unit, "U": unit}, or None when it is
    anything else."""
    out = {}
    for part in rest.split(","):
        key, eq, raw = part.partition("=")
        key = key.strip()
        vector = _unit_vector(raw.split())
        if not eq or key not in ("V", "U") or key in out or vector is None:
            return None
        out[key] = vector
    return out if len(out) == 2 else None


def parse_directions(bodies):
    """
    {material: {"V": unit vector, "U": unit vector}} from the bodies of the
    SECTIE-RICHTING lines, in file order, split on the last colon. A bad line
    is skipped with a log line, so that an earlier good line of its material
    stays; of the good lines the newest counts. Never raises.
    """
    out = OrderedDict()
    for body in bodies:
        name, sep, rest = body.rpartition(":")
        name = name.strip()
        found = _read_direction(rest) if sep and name else None
        if found is None:
            log(tr(u"WARNING: SECTIE-RICHTING '{0}' wordt overgeslagen: "
                   u"verwacht '<materiaal>: V=vx vy vz, U=ux uy uz'.",
                   u"WARNING: SECTIE-RICHTING '{0}' is skipped: expected "
                   u"'<material>: V=vx vy vz, U=ux uy uz'.").format(body))
            continue
        out[name] = found
    return out


def _angle(a, b, either_sign=False):
    """Angle between unit vectors in degrees; atan2 stays exact near 0 and
    180. either_sign: between the lines, so at most 90."""
    cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
             a[0] * b[1] - a[1] * b[0])
    dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    size = math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
    return math.degrees(math.atan2(size, abs(dot) if either_sign else dot))


def direction_warnings(beams, directions):
    """
    The check of the SECTIE-RICHTING lines: pure, Python 2.7 and 3, no mw and
    no logging. beams: [(material, U, V)], U and V of any length (a beam
    without a direction is passed over). directions: from parse_directions.
    Returns the WARNING texts, per material in the order of directions:
    turned (V), mirrored (U against U), not parallel (U). Beams of a material
    without a line do not count. The three are independent: a reversed beam
    with the default V (Z x U) also has its V reversed, so it gives both
    turned and mirrored.
    """
    found = {}
    for material, u, v in beams:
        wanted = directions.get(material)
        u = _unit_vector(u)
        v = _unit_vector(v)
        if wanted is None or u is None or v is None:
            continue
        state = found.setdefault(material, {
            "turned": [], "mirrored": 0, "skew": []})
        angle = _angle(v, wanted["V"])
        if angle > DIRECTION_TOL:
            state["turned"].append(angle)
        if sum(u[i] * wanted["U"][i] for i in range(3)) < 0.0:
            state["mirrored"] += 1
        angle = _angle(u, wanted["U"], True)
        if angle > DIRECTION_TOL:
            state["skew"].append(angle)
    out = []
    for material in directions:
        state = found.get(material)
        if state is None:
            continue
        if state["turned"]:
            out.append(tr(
                u"WARNING: Materiaal '{0}': bij {1} balk(en) staat de "
                u"doorsnede gedraaid: hun V-as wijkt tot {2} graden af van de "
                u"as waarvoor de doorsnede is gemaakt. De resultaten van deze "
                u"balken kloppen niet. Zet de V-as goed (Element orientation "
                u"of V vector), of wijs de doorsnede opnieuw toe met "
                u"MecwaySectionProps.",
                u"WARNING: Material '{0}': on {1} beam(s) the section is "
                u"turned: their V axis is up to {2} degrees from the axis the "
                u"section was made for. The results of these beams are wrong. "
                u"Correct the V axis (Element orientation or V vector), or "
                u"reassign the section with MecwaySectionProps.").format(
                    material, len(state["turned"]),
                    "%.1f" % max(state["turned"])))
        if state["mirrored"]:
            out.append(tr(
                u"WARNING: Materiaal '{0}': {1} balk(en) lopen tegen de "
                u"richting in waarvoor de doorsnede is gemaakt: de balk ziet "
                u"de doorsnede gespiegeld. Keer deze balken om, of wijs de "
                u"doorsnede opnieuw toe met MecwaySectionProps.",
                u"WARNING: Material '{0}': {1} beam(s) run against the "
                u"direction the section was made for: the beam sees the "
                u"section mirrored. Reverse these beams, or reassign the "
                u"section with MecwaySectionProps.").format(
                    material, state["mirrored"]))
        if state["skew"]:
            out.append(tr(
                u"WARNING: Materiaal '{0}': {1} balk(en) lopen niet evenwijdig "
                u"aan de richting waarvoor de doorsnede is gemaakt, tot {2} "
                u"graden. Controleer deze balken, of geef ze een eigen "
                u"materiaal en wijs de doorsnede daarop toe met "
                u"MecwaySectionProps.",
                u"WARNING: Material '{0}': {1} beam(s) are not parallel to "
                u"the direction the section was made for, up to {2} degrees. "
                u"Check these beams, or give them their own material and "
                u"assign the section to it with MecwaySectionProps.").format(
                    material, len(state["skew"]), "%.1f" % max(state["skew"])))
    return out


def report_directions(bodies, beams):
    """The check on the lines of a model (out["section_directions"]): every
    text of direction_warnings in the log. Returns those texts. Once per run:
    bridge_mesh.write_mesh on a run, bridge_section_view.build_view for the
    section view outside a run."""
    if not bodies:
        return []
    texts = direction_warnings(beams, parse_directions(bodies))
    for text in texts:
        log(text)
    return texts


# Shear centre this far from the centroid, relative to the square root of the
# area, counts as an open section that twists (an angle or a channel is well
# above it, a section with two axes of symmetry is at 0).
SHEAR_OFFSET_LIMIT = 0.1


def shear_centre_warning(material, geom, modelisation):
    """
    The WARNING for a general section with a shear centre away from the
    centroid on a beam without warping, or None. Measured with Code-Aster
    17.4 on an open section against a solid model, own weight, built in:
    POU_D_TG within 1.2% in bending and twist; POU_D_E, which gets EY and EZ
    but no JG, 5.6 times too much twist. POU_D_T, POU_D_T_GD: the same lack
    of JG, the twist NOT verified.
    geom: bridge_from_liml section with "section_extras".
    """
    extras = (geom or {}).get("section_extras") or {}
    if modelisation == "POU_D_TG" or not extras.get("JG"):
        return None
    area = extras.get("A") or 0.0
    offset = math.sqrt((extras.get("EY") or 0.0) ** 2 +
                       (extras.get("EZ") or 0.0) ** 2)
    if area <= 0.0 or offset <= SHEAR_OFFSET_LIMIT * math.sqrt(area):
        return None
    return tr(u"WARNING: Materiaal '{0}': het dwarskrachtcentrum ligt {1} mm "
              u"van het zwaartepunt. {2} heeft geen welving en overschat dan "
              u"de wringing (POU_D_E: 5,6 keer gemeten op een open profiel). "
              u"Kies bij Elementen 'Balken' = POU_D_TG.",
              u"WARNING: Material '{0}': the shear centre lies {1} mm from "
              u"the centroid. {2} has no warping and then overestimates the "
              u"twist (POU_D_E: 5.6 times, measured on an open section). "
              u"Choose Beams = POU_D_TG on the Elements page.").format(
                  material, "%.0f" % (offset * 1e3), modelisation)


_SPECTRUM_RE = re.compile(r"^\s*([XYZxyz](?:\s*,\s*[XYZxyz])*)\s*=\s*"
                          r"([A-Za-z_]\w*)\s*(?:,(.*))?$")


def _parse_spectrum(body, spectrum):
    """'#ASTER-SPECTRE X, Y = name, ECHELLE=9.81' -> spectrum[direction] =
    (name, ['ECHELLE=9.81']) (bridge_spectrum.py: SPECTRE of
    COMB_SISM_MODAL)."""
    m = _SPECTRUM_RE.match(body)
    extra = []
    if m and m.group(3):
        extra = [p.strip() for p in m.group(3).split(",") if p.strip()]
    if not m or any("=" not in p for p in extra):
        log(tr("ERROR: '#ASTER-SPECTRE {0}': verwacht 'X, Y = naam' met "
               "eventueel ', K=V' (bijv. '#ASTER-SPECTRE X = spec, "
               "ECHELLE=9.81'); genegeerd.",
               "ERROR: '#ASTER-SPECTRE {0}': expected 'X, Y = name' with "
               "optionally ', K=V' (e.g. '#ASTER-SPECTRE X = spec, "
               "ECHELLE=9.81'); ignored.").format(body.strip()))
        return
    for axis in re.findall(r"[XYZxyz]", m.group(1)):
        spectrum[axis.upper()] = (m.group(2), extra)


def _parse_failure(body, failure):
    """'#ASTER-BEZWIJKEN material = strain' -> failure[material] = strain."""
    name, sep, value = body.rpartition("=")
    try:
        limit = float(value.strip().replace(",", "."))
    except ValueError:
        limit = None
    if not sep or not name.strip() or limit is None or limit <= 0.0:
        log(tr("ERROR: '#ASTER-BEZWIJKEN {0}': verwacht 'materiaal = rek' "
               "met een rek > 0 (bijv. '#ASTER-BEZWIJKEN Staal = 0.2'); "
               "genegeerd.",
               "ERROR: '#ASTER-BEZWIJKEN {0}': expected 'material = "
               "strain' with a strain > 0 (e.g. '#ASTER-BEZWIJKEN Steel = "
               "0.2'); ignored.").format(body.strip()))
        return
    failure[name.strip()] = limit


def substitute(text, renames, known):
    """
    Replace <<Mecway-selectie>> with the Code-Aster group name.

    renames : {Mecway name: Code-Aster name} (bridge_mesh)
    known   : set of Code-Aster group names in the mesh
    An unknown selection is logged as ERROR and stays in place, so that
    Code-Aster gives a clear error on it.
    """
    def repl(m):
        name = m.group(1).strip()
        aster = renames.get(name, name)
        if aster not in known:
            log(tr("ERROR: #ASTER: selectie '{0}' bestaat niet in het "
                   "mesh.",
                   "ERROR: #ASTER: selection '{0}' does not exist in the "
                   "mesh.").format(name))
        return aster
    return _PLACEHOLDER_RE.sub(repl, text)


def apply_options(analysis, options):
    """
    Copy of the analysis settings with the #ASTER-OPTIE values. Only
    keys the analysis already has; the type follows the existing value.
    A yes/no setting accepts the words of bridge_utils.parse_yes_no
    (ja/nee, aan/uit, yes/no, on/off, true/false, 1/0, oui/non); any other
    text gives a WARNING and the existing value stays.
    """
    result = dict(analysis)
    for key, raw in options.items():
        if key not in analysis:
            log(tr("ERROR: #ASTER-OPTIE '{0}' bestaat niet voor deze "
                   "analyse; genegeerd. Bekend: {1}",
                   "ERROR: #ASTER-OPTIE '{0}' does not exist for this "
                   "analysis; ignored. Known: {1}").format(
                    key, ", ".join(sorted(analysis))))
            continue
        old = analysis[key]
        try:
            if isinstance(old, bool):
                value = parse_yes_no(raw)
                if value is None:
                    log(tr("WARNING: #ASTER-OPTIE {0} = {1}: geen ja/nee-"
                           "waarde (ja/nee, aan/uit, yes/no, on/off, "
                           "true/false, 1/0, oui/non); de instelling blijft "
                           "{2}.",
                           "WARNING: #ASTER-OPTIE {0} = {1}: not a yes/no "
                           "value (yes/no, on/off, true/false, 1/0, ja/nee, "
                           "aan/uit, oui/non); the setting stays "
                           "{2}.").format(key, raw, old))
                    continue
            elif isinstance(old, int):
                value = int(raw)
            elif isinstance(old, float):
                value = float(raw)
            else:
                value = raw.strip("'\"")
        except ValueError:
            log(tr("ERROR: #ASTER-OPTIE {0} = {1}: geen geldige waarde; "
                   "genegeerd.",
                   "ERROR: #ASTER-OPTIE {0} = {1}: not a valid value; "
                   "ignored.").format(key, raw))
            continue
        result[key] = value
        log("INFO: #ASTER-OPTIE {0} = {1} (was {2}).".format(key, value, old))
    return result
