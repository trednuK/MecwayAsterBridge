# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_vibroacoustic_harm.py
# Responsibility: harmonic response of a coupled model of
# structure + air/liquid (analysis vibroacoustic_harm_3d, STAPPENPLAN
# S3c): per frequency the displacement of the structure and the pressure in
# the fluid, with absorbing boundaries, sources and microphones. Mecway has
# no harmonic and no coupled analysis (manual v33 chapter 6); the bridge
# computes the model of the coupled modes (S3b, bridge_vibroacoustic.py:
# a Frequency model V30 with a fluid part) as a harmonic load.
#
#   build_vibroacoustic_harm(...) - builder (bridge_to_aster.
#                         _build_dyna_modal sends a vibro-acoustic
#                         analysis with type_calcul 'HARM' here)
#   report_harmonic(...)  - after the run: frequencies, microphones and
#                         probes in the log and the status box
#
# Input (besides that of S3b: fluid part, coupling faces, OPEN_):
#   force/pressure/gravity on the structure  Mecway loads (amplitude;
#                       phase with #ASTER-FASE, table = amplitude against
#                       frequency), like harmonic_3d (bridge_harmonic)
#   velocity source     face selection BRON_/SOURCE_ on the fluid
#                       (normal velocity source_velocity, into the fluid) or
#                       '#ASTER-BRON selection = v [m/s or mm/s] [, phase]'
#                       -> AFFE_CHAR_MECA VITE_FACE
#   incident wave       face selection INVALLEND_/INCIDENT_ (amplitude of the
#                       wave travelling into the fluid: incident_pressure)
#                       or '#ASTER-BRON selection = p [Pa] [, phase]'
#                       -> AFFE_CHAR_MECA ONDE_FLUI + matrix ONDE_FLUI
#   absorbing boundary  face selection ABSORBEREND_/ABSORBING_ (rho c) or
#                       Mecway's impedance with a real Z
#                       -> MODELISATION '3D_FLUI_ABSO', matrix IMPE_MECA
#   microphone/probe    node selections MICROFOON_ (pressure, SPL; CSV like
#                       S3a) and MEETPUNT_ (displacement; CSV like S10h)
#
# Route (Code-Aster 17.4, test cases ahlv101a, ahlv100b and ahlv302a):
#   ASSEMBLAGE RIGI_MECA / MASS_MECA (+ ONDE_FLUI with the wave loads) and
#   IMPE_MECA -> DYNA_VIBRA TYPE_CALCUL='HARM' BASE_CALCUL='PHYS' with
#   MATR_IMPE_PHI (catalogue dyna_vibra.py: MATR_IMPE_PHI matr_asse_depl_r,
#   only PHYS or GENE) and EXCIT VECT_ASSE (sources with PUIS_PULS=1,
#   PHAS_DEG=90: i w x vector, like ahlv101a/ahlv100b).
# Why direct (PHYS) and not on a modal basis: (1) U_P_PHI gives a spurious
# mode at 0 Hz per PHI degree of freedom (bridge_vibroacoustic, header), so
# a modal basis needs the BANDE search of S3b and cannot miss the static
# contribution of those degrees of freedom; (2) the absorbing boundary is
# not proportional damping: the real modes do not decouple and the
# radiation damping is exactly the quantity you want to see; (3) ahlv101a
# and ahlv100b compute this way. The computing time grows linearly with
# the number of frequencies (one factorization per frequency).
#
# Measured (verification VH, docs/Akoestiek.md par. 7): see the header of
# TestFiles/Verificatie/tests_vibroakoestiek_harmonisch.py and the
# comment lines at the blocks below.
#
# Compatible with IronPython 2.7.9 (standard library only).

import os
from collections import OrderedDict

import bridge_to_aster as b2a
import bridge_dyna_modal as bdm
import bridge_harmonic as bh
import bridge_acoustic as bac
import bridge_vibroacoustic as bva
from bridge_utils import log, tr, CONFIG_BRIDGE, run_name

ANALYSIS = "vibroacoustic_harm_3d"
MIC_SUFFIX = bac.MIC_SUFFIX            # <run>_microfoons.csv (like S3a)
PROBE_SUFFIX = bh.PROBE_SUFFIX         # <run>_meetpunten.csv (like S10h)
_LABEL = ("Vibro-akoestiek harmonisch", "Vibroacoustics harmonic")
# Fields to Mecway besides the pressure (always included): like harmonic_3d.
_FIELD_GROUPS = ("displacements", "velocities", "accelerations",
                 "stresses", "vonmises")
_STRESS_GROUPS = ("stresses", "vonmises")


def is_vibro_harm(analysis_cfg):
    """True for harmonic vibro-acoustics (analysis config with
    "vibroacoustic" and type_calcul 'HARM')."""
    cfg = analysis_cfg or {}
    return (bva.is_vibroacoustic(cfg) and
            str(cfg.get("type_calcul", "")).upper() == "HARM")


def _r(x):
    import bridge_mesh
    return bridge_mesh._real(float(x))


def _err(text):
    log(tr("ERROR: Vibro-akoestiek harmonisch: {0}.",
           "ERROR: Vibroacoustics harmonic: {0}.").format(text))


# ==========================================
# INPUT: sources, boundaries, microphones
# ==========================================
def _aster_sources(model_data):
    """'#ASTER-BRON selection = value [unit] [, phase]' -> ([(selection,
    kind 'velocity'/'pressure', value SI, phase degrees)], errors). The
    value is read by bridge_acoustic.source_value (whole text number +
    unit): a pressure unit (Pa, N/m2, kPa, kN/m2, MPa, N/mm2, GPa, bar,
    mbar, psi; converted to Pa once) makes an incident wave, a velocity
    unit (m/s, mm/s, mm/ms, in/s, ft/s or no unit = m/s) a velocity
    source; another unit or text without a number is an error (fatal in
    _inputs)."""
    out, bad = [], []
    for body in model_data.get("aster_custom", {}).get("sources", []):
        name, sep, rest = body.partition("=")
        parts = [p.strip() for p in rest.split(",")]
        item = None
        unknown = ""
        if sep and name.strip() and parts[0] and len(parts) <= 2:
            kind, value, unit = bac.source_value(parts[0])
            if kind is None:
                unknown = unit
            else:
                try:
                    phase = (float(parts[1].split("=")[-1].strip())
                             if len(parts) == 2 else 0.0)
                    item = (name.strip(), kind, value, phase)
                except (TypeError, ValueError):
                    item = None
        if item is None:
            bad.append(tr(
                "'#ASTER-BRON {0}': verwacht 'selectie = snelheid [m/s, "
                "mm/s, mm/ms, in/s, ft/s] of druk [Pa, N/m2, kPa, kN/m2, "
                "MPa, N/mm2, GPa, bar, mbar, psi] [, fase in graden]', bijv. "
                "'#ASTER-BRON Inlaat = 2 mm/s, 90'{1}",
                "'#ASTER-BRON {0}': expected 'selection = velocity [m/s, "
                "mm/s, mm/ms, in/s, ft/s] or pressure [Pa, N/m2, kPa, kN/m2, "
                "MPa, N/mm2, GPa, bar, mbar, psi] [, phase in degrees]', "
                "e.g. '#ASTER-BRON Inlet = 2 mm/s, 90'{1}").format(
                    body.strip(),
                    tr(" (eenheid '{0}' niet herkend)",
                       " (unit '{0}' not recognised)").format(unknown)
                    if unknown else ""))
            continue
        out.append(item)
    return out, bad


def _face_fluid(model_data, vib, sel):
    """Mecway parts (fluid) of the elements to which the faces of the
    selection belong, and the number of faces that do not belong to a
    fluid."""
    elem_elset = dict((eid, es) for eid, _s, _n, es
                      in model_data.get("mesh_elements", []))
    media, other = [], 0
    for eid, _fid in model_data.get("face_selection_faces", {}).get(sel, []):
        if eid in vib["fluid_eids"]:
            es = elem_elset.get(eid)
            if es not in media:
                media.append(es)
        else:
            other += 1
    return media, other


def _inputs(model_data, analysis, vib, fluid_ca):
    """
    Sources, absorbing faces and microphones to Code-Aster names.
    Returns dict or None (ERROR logged):
      "vite":  [(group, v [m/s], phase, fluid part, description)]
      "onde":  [(group, p_in [Pa], phase, fluid part, description)]
      "abso":  [(group, Mecway part, Z or None (= rho c), descr.)]
      "mics":  OrderedDict {Mecway name: [node numbers]}
    """
    renames = model_data.get("selection_renames",
                             model_data.get("group_renames", {}))
    known = model_data.get("mesh_group_names", set())
    faces = model_data.get("face_selection_faces", {})
    named = vib.get("named", {})
    out = {"vite": [], "onde": [], "abso": [], "mics": OrderedDict()}
    bad = []
    roles = {}

    def claim(sel, role):
        if sel in roles and roles[sel] != role:
            bad.append(tr("selectie '{0}' is zowel {1} als {2}",
                          "selection '{0}' is both {1} and {2}").format(
                              sel, roles[sel], role))
        roles[sel] = role

    def fluid_of(sel, what):
        """The single fluid part of a face selection, or None."""
        if sel not in faces:
            bad.append(tr("{0} '{1}' is geen vlakselectie",
                          "{0} '{1}' is not a face selection").format(
                              what, sel))
            return None
        media, other = _face_fluid(model_data, vib, sel)
        if other or len(media) != 1:
            bad.append(tr(
                "{0} '{1}' ligt niet aan precies een fluidum ({2} "
                "fluidum-onderde(e)l(en), {3} vlak(ken) aan de constructie); "
                "kies vlakken van een fluidum-onderdeel",
                "{0} '{1}' does not border exactly one fluid ({2} fluid "
                "part(s), {3} face(s) on the structure); choose faces of one "
                "fluid part").format(what, sel, len(media), other))
            return None
        return media[0]

    def aster(sel):
        name = renames.get(sel, sel)
        if name not in known:
            log(tr("WARNING: Vibro-akoestiek harmonisch: selectie '{0}' is "
                   "leeg; overgeslagen.",
                   "WARNING: Vibroacoustics harmonic: selection '{0}' is "
                   "empty; skipped.").format(sel))
            return None
        return name

    # --- sources: BRON_ (velocity), INVALLEND_ (wave), #ASTER-BRON ---
    v0 = float(analysis.get("source_velocity", 1.0e-3))
    p0 = float(analysis.get("incident_pressure", 1.0))
    items = OrderedDict()
    for sel, kind in named.get("source", []):
        items[sel] = ("velocity", v0, 0.0, tr("BRON_-selectie",
                                               "SOURCE_ selection"))
    for sel, kind in named.get("incident", []):
        items[sel] = ("pressure", p0, 0.0, tr("INVALLEND_-selectie",
                                               "INCIDENT_ selection"))
    custom, bad_custom = _aster_sources(model_data)
    bad += bad_custom
    for sel, kind, value, phase in custom:
        items[sel] = (kind, value, phase, "#ASTER-BRON")
    for sel, (kind, value, phase, how) in items.items():
        what = (tr("bron", "source") if kind == "velocity"
                else tr("invallende golf", "incident wave"))
        claim(sel, what)
        es = fluid_of(sel, what)
        name = aster(sel) if es is not None else None
        if name is None:
            continue
        key = "vite" if kind == "velocity" else "onde"
        out[key].append((name, value, phase, es,
                         "{0} {1}".format(how, sel)))
        if kind == "velocity":
            log("INFO: Harmonic vibro-acoustics: source '{0}' ({1}): "
                "normal velocity {2} m/s into the fluid, phase {3} degrees."
                .format(sel, how, "%.6g" % value, "%g" % phase))
        else:
            log("INFO: Harmonic vibro-acoustics: incident wave on '{0}' "
                "({1}): amplitude {2} Pa (the wave travelling into the fluid), "
                "phase {3} degrees; the face lets returning waves through "
                "(ONDE_FLUI).".format(sel, how, "%.6g" % value, "%g" % phase))

    # --- absorbing boundaries: ABSORBEREND_ and Mecway's impedance ---
    for sel, kind in named.get("absorbing", []):
        what = tr("absorberende rand", "absorbing boundary")
        claim(sel, what)
        es = fluid_of(sel, what)
        name = aster(sel) if es is not None else None
        if name is not None:
            out["abso"].append((name, es, None, "rho c"))
    for sel, zr, zi in vib.get("impedance_values", []):
        what = tr("impedantie", "impedance")
        claim(sel, what)
        if zr is None or zi is None or zr <= 0.0:
            bad.append(tr("impedantie op '{0}': Re Z moet een getal > 0 zijn "
                          "(Pa.s/m)",
                          "impedance on '{0}': Re Z must be a number > 0 "
                          "(Pa.s/m)").format(sel))
            continue
        if zi != 0.0:
            bad.append(tr(
                "impedantie op '{0}' is complex (Im Z = {1}); alleen een "
                "reele Z (KNOWN_BUGS 59)",
                "impedance on '{0}' is complex (Im Z = {1}); only a real Z "
                "(KNOWN_BUGS 59)").format(sel, "%g" % zi))
            continue
        es = fluid_of(sel, what)
        name = aster(sel) if es is not None else None
        if name is not None:
            out["abso"].append((name, es, zr, "Z = {0} Pa.s/m".format(
                "%g" % zr)))

    # --- microphones (pressure) ---
    for sel, kind in named.get("microphone", []):
        if kind != "node":
            log(tr("WARNING: Vibro-akoestiek harmonisch: microfoon '{0}' is "
                   "een {1}selectie; alleen knoopselecties tellen; "
                   "overgeslagen.",
                   "WARNING: Vibroacoustics harmonic: microphone '{0}' is a "
                   "{1} selection; only node selections count; "
                   "skipped.").format(sel, kind))
            continue
        nids = [int(str(n).lstrip("N")) for n in
                model_data.get("node_groups", {}).get(sel, [])]
        if nids:
            out["mics"][sel] = nids
    for sel, kind in named.get("source", []) + named.get("incident", []) + \
            named.get("absorbing", []):
        if kind != "face":
            bad.append(tr("'{0}' is een {1}selectie; kies een vlakselectie",
                          "'{0}' is a {1} selection; choose a face "
                          "selection").format(sel, kind))
    if bad:
        _err("; ".join(bad))
        return None
    return out


# ==========================================
# BUILDER
# ==========================================
def _check(model_data, vib):
    """What this analysis cannot do: list of errors (text)."""
    bad = list(vib["bad"])
    bad += [tr("fluid pressure op '{0}' is {1}; een opgelegde druk != 0 "
               "vertaalt de bridge in de vibro-akoestiek niet (bron: BRON_, "
               "INVALLEND_ of #ASTER-BRON; p = 0: OPEN_)",
               "fluid pressure on '{0}' is {1}; an imposed pressure != 0 is "
               "not translated in vibroacoustics (source: SOURCE_, "
               "INCIDENT_ or #ASTER-BRON; p = 0: OPEN_)").format(s, t)
            for s, t in vib["pressure_src"]]
    if b2a._thermal_active(model_data):
        bad.append(tr("thermische rek (Thermal stress) wordt niet vertaald; "
                      "zet hem uit",
                      "thermal strain (Thermal stress) is not translated; "
                      "switch it off"))
    return bad


def _orient_block(groups, renames, fluid_of):
    """ORIE_PEAU of the boundary faces of the fluid (normal outwards,
    GROUP_MA_INTERNE = the fluid; like the coupling faces in S3b)."""
    if not groups:
        return ""
    return ("\n# Randvlakken van het fluidum (bronnen, invallende golf, "
            "absorberend):\n# normaal uit het fluidum (ORIE_PEAU met "
            "GROUP_MA_INTERNE)\n"
            "mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE=mesh,\n"
            "    ORIE_PEAU=(\n{0}    ),\n)\n").format("".join(
                "        _F(GROUP_MA_PEAU='{0}', GROUP_MA_INTERNE='{1}'),\n"
                .format(g, renames.get(fluid_of[g], fluid_of[g]))
                for g in groups))


def build_vibroacoustic_harm(work_dir, model_data, msh_path, resu_name,
                             analysis):
    """
    Generate the .comm and .export for harmonic vibro-acoustics
    (vibroacoustic_harm_3d). Returns the path to the .export, or None
    (ERROR logged).
    """
    log("--- Generating Aster Files (DYNA_VIBRA HARM vibro-akoestisch) ---")
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor de "
               "harmonische vibro-akoestiek. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for harmonic "
               "vibroacoustics. Choose 'liml' (General page)."))
        return None
    vib = model_data.get("vibro")
    if not vib:
        log(tr("ERROR: Vibro-akoestiek harmonisch: het model heeft geen "
               "fluidum. Geef het lucht- of vloeistofvolume een eigen "
               "onderdeel met een materiaal met 'Speed of sound' en een "
               "dichtheid (zonder Young's modulus), of een naam die begint "
               "met LUCHT_ of FLUID_. Zonder fluidum: harmonic_3d.",
               "ERROR: Vibroacoustics harmonic: the model has no fluid. Give "
               "the air or liquid volume its own part with a material with "
               "'Speed of sound' and a density (without Young's modulus), "
               "or a name starting with LUCHT_ or FLUID_. Without a fluid: "
               "harmonic_3d."))
        return None
    renames = model_data.get("group_renames", {})
    fluid_ca = OrderedDict((renames.get(es, es), mat)
                           for es, mat in vib["fluid_elsets"].items())
    bad = _check(model_data, vib) + bva._check_fluid(model_data, vib,
                                                     fluid_ca)
    if bad:
        _err("; ".join(bad))
        return None
    if not b2a._check_linear(model_data, tr("een harmonische analyse",
                                            "a harmonic analysis")):
        return None
    freqs = bac._frequencies(analysis, _LABEL)
    if freqs is None:
        return None
    inp = _inputs(model_data, analysis, vib, fluid_ca)
    if inp is None:
        return None
    nonzero = b2a._nonzero_imposed(model_data)
    if nonzero:
        _err(tr("opgelegde verplaatsing of rotatie <> 0 op {0}: een "
                "opgelegde (basis)beweging wordt niet vertaald; zet de "
                "waarde op 0 en breng de belasting als kracht, druk of bron "
                "aan",
                "imposed displacement or rotation <> 0 on {0}: an imposed "
                "(base) motion is not translated; set the value to 0 and "
                "apply the load as a force, pressure or source").format(
                    ", ".join("'{0}'".format(s) for s in nonzero)))
        return None
    if model_data.get("initial_velocities"):
        log("INFO: Harmonic vibro-acoustics: the initial velocity is not "
            "used (steady-state response).")

    fluid_mats = set(m for m, p in vib["materials"].items()
                     if p.get("c") and not p.get("E"))
    fluid_mats |= set(fluid_ca.values())
    md_s = bva._structure_view(model_data, fluid_ca, fluid_mats)
    structure = bool(b2a._model_groups(md_s))
    interfaces = vib.get("interfaces", OrderedDict())
    if structure and not interfaces:
        log(tr("WARNING: Vibro-akoestiek harmonisch: geen koppelvlak "
               "gevonden; fluidum en constructie delen geen vlakken. De "
               "constructie straalt dan geen geluid af. Mesh ze als een "
               "doorlopend mesh (gedeelde knopen op het grensvlak).",
               "WARNING: Vibroacoustics harmonic: no coupling face found; "
               "fluid and structure share no faces. The structure then "
               "radiates no sound. Mesh them as one continuous mesh "
               "(shared nodes on the interface)."))

    # --- loads on the structure (like harmonic_3d) ---
    load_funcs, charges = [], []
    constraints, excitations, extra, phases = [], [], [], []
    if structure:
        load_funcs = b2a._collect_load_funcs(model_data)
        func_names = b2a._load_func_names(model_data)
        timed = [name for name, _h in load_funcs]
        charges = b2a._build_charges(md_s, func_names)
        constraints, excitations, extra, errors = bdm._excitations(charges,
                                                                   timed)
        if errors:
            _err(tr("een opgelegde verplaatsing met een tabel kan niet; zet "
                    "de tabel uit of de waarde op 0",
                    "an imposed displacement with a table is not possible; "
                    "remove the table or set the value to 0"))
            return None
        phases = bh._excitation_phases(md_s, charges, extra, excitations)
        if phases is None:
            return None
    n_src = len(excitations) + len(inp["vite"]) + len(inp["onde"])
    if not n_src:
        _err(tr("geen bron: geen belasting op de constructie (kracht, druk, "
                "gravity), geen BRON_- of INVALLEND_-vlakselectie en geen "
                "#ASTER-BRON; de respons is overal 0",
                "no source: no load on the structure (force, pressure, "
                "gravity), no SOURCE_ or INCIDENT_ face selection and no "
                "#ASTER-BRON; the response is zero everywhere"))
        return None
    if load_funcs:
        log("INFO: Harmonic vibro-acoustics: {0} load(s) with a "
            "Mecway table: the column 'time' is the frequency in Hz, the value "
            "the amplitude at that frequency.".format(len(load_funcs)))

    # --- damping of the structure ---
    alpha, beta, _z = bdm._damping_text(model_data, analysis)
    dampers = bh._dampers(md_s)
    if not (inp["abso"] or alpha or beta or dampers):
        log(tr("WARNING: Vibro-akoestiek harmonisch: geen absorberende rand "
               "(ABSORBEREND_, impedance) en geen demping (Rayleigh, "
               "dempers): bij een gekoppelde eigenfrequentie is de respons "
               "oneindig. Voeg een absorberende rand of demping toe, of "
               "kies frequenties tussen de modes (vibroacoustic_modes_3d).",
               "WARNING: Vibroacoustics harmonic: no absorbing boundary "
               "(ABSORBING_, impedance) and no damping (Rayleigh, "
               "dampers): at a coupled natural frequency the response is "
               "infinite. Add an absorbing boundary or damping, or choose "
               "frequencies between the modes (vibroacoustic_modes_3d)."))
    if dampers:
        md_s["damping_matrix"] = True
    mats_c = OrderedDict((m, (vib["materials"][m]["c"],
                              vib["materials"][m]["rho"]))
                         for m in fluid_ca.values())
    bac._wavelength_check(model_data, list(fluid_ca.items()), mats_c,
                          freqs[-1])
    probes = bh._probes(model_data)

    # --- fields ---
    fields = [f for f in analysis.get("fields", ["displacements"])
              if f in _FIELD_GROUPS]
    if "displacements" not in fields:
        fields.insert(0, "displacements")
    g3d = b2a._result_groups(md_s)[0] if structure else []
    stresses = bool(g3d) and any(f in fields for f in _STRESS_GROUPS)
    if not stresses:
        if any(f in fields for f in _STRESS_GROUPS):
            log("INFO: Harmonic vibro-acoustics: stresses only on "
                "volume elements of the structure (the model has "
                "none).")
        fields = [f for f in fields if f not in _STRESS_GROUPS]

    # --- mesh: groups, orientation ---
    defigroup_block = b2a._build_defigroup_block(md_s)
    if interfaces:
        defigroup_block += (
            "\n# Koppelvlakken: normaal uit het fluidum (ORIE_PEAU met "
            "GROUP_MA_INTERNE,\n# zoals adlv100b/adls102a)\n"
            "mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE=mesh,\n"
            "    ORIE_PEAU=(\n{0}    ),\n)\n").format("".join(
                "        _F(GROUP_MA_PEAU='{0}', GROUP_MA_INTERNE='{1}'),\n"
                .format(g, renames.get(es, es))
                for g, es in interfaces.items()))
    fluid_of = OrderedDict()
    for g, _v, _p, es, _d in inp["vite"] + inp["onde"]:
        fluid_of[g] = es
    for g, es, _z, _d in inp["abso"]:
        fluid_of[g] = es
    defigroup_block += _orient_block(list(fluid_of), renames, fluid_of)

    # --- model ---
    load_faces = [g for g, _v, _p, _e, _d in inp["vite"] + inp["onde"]]
    load_faces = [g for k, g in enumerate(load_faces)
                  if g not in load_faces[:k]]
    abso = [g for g, _e, _z, _d in inp["abso"]]
    fluid_lines = "".join(
        "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
        "MODELISATION='3D_FLUIDE', FORMULATION='U_P_PHI'),\n".format(es)
        for es in list(fluid_ca) + load_faces)
    fluid_lines += "".join(
        "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
        "MODELISATION='FLUI_STRU', FORMULATION='U_P_PHI'),\n".format(g)
        for g in interfaces)
    fluid_lines += "".join(
        "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
        "MODELISATION='3D_FLUI_ABSO', FORMULATION='U_P_PHI'),\n".format(g)
        for g in abso)
    if structure:
        model_block = bva._insert_affe(b2a._build_model_block(md_s),
                                       "model = AFFE_MODELE(", fluid_lines)
    else:
        model_block = ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n"
                       "    AFFE=(\n{0}    ),\n)\n").format(fluid_lines)
    cara = structure and b2a._has_cara(md_s)
    cara_ref = "    CARA_ELEM=cara,\n" if cara else ""
    cara_elem_block = b2a._build_cara_elem_block(md_s) if structure else \
        "#-- no structure --\n"

    # --- materials ---
    names = OrderedDict()
    mat_lines = []
    for k, mat in enumerate(sorted(set(fluid_ca.values()),
                                   key=list(vib["materials"]).index)):
        props = vib["materials"][mat]
        names[mat] = "MAF{0}".format(k + 1)
        mat_lines.append("{0}{1} = DEFI_MATERIAU(FLUIDE=_F(RHO={2}, "
                         "CELE_R={3}))".format(b2a._mat_comment(mat),
                                               names[mat], _r(props["rho"]),
                                               _r(props["c"])))
    assign = ["        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        es, names[m]) for es, m in fluid_ca.items()]
    assign += ["        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        g, names[vib["fluid_elsets"][es]]) for g, es in interfaces.items()]
    assign += ["        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        g, names[vib["fluid_elsets"][fluid_of[g]]]) for g in load_faces]
    for k, (g, es, z, desc) in enumerate(inp["abso"]):
        mat = vib["fluid_elsets"][es]
        c, rho = mats_c[mat]
        if z is None:
            mname = names[mat]
        else:
            # Impedance Z: own material with CELE_R = Z / rho on the face
            # (IMPE_MECA of 3D_FLUI_ABSO belongs to Z = rho c of the
            # material of the face; measured: verification VH-03, Z = 2 rho c
            # to 1.2e-4).
            mname = "MAZ{0}".format(k + 1)
            mat_lines.append("# absorberende rand '{0}': {1} (Z / (rho c) = "
                             "{2})\n{3} = DEFI_MATERIAU(FLUIDE=_F(RHO={4}, "
                             "CELE_R={5}))".format(
                                 g, desc, "%.4g" % (z / (rho * c)), mname,
                                 _r(rho), _r(z / rho)))
            log("INFO: Harmonic vibro-acoustics: impedance {0} on '{1}' "
                "(Z / (rho c) = {2}): 3D_FLUI_ABSO with c = Z / rho = {3} "
                "m/s.".format(desc, g, "%.4g" % (z / (rho * c)),
                              "%.6g" % (z / rho)))
        assign.append("        _F(GROUP_MA='{0}', MATER={1}),\n".format(
            g, mname))
    materials_block = ((b2a._build_materials_block(md_s, analysis)
                        if structure else "") + "\n".join(mat_lines) + "\n")
    if structure:
        fieldmat_block = bva._insert_affe(b2a._build_fieldmat_block(md_s),
                                          "fieldmat = AFFE_MATERIAU(",
                                          "".join(assign))
    else:
        fieldmat_block = ("fieldmat = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n"
                          "    MODELE=model,\n    AFFE=(\n{0}    ),\n)\n"
                          ).format("".join(assign))
    if model_block is None or fieldmat_block is None:
        _err(tr("AFFE_MODELE/AFFE_MATERIAU niet herkend (interne fout)",
                "AFFE_MODELE/AFFE_MATERIAU not recognised (internal error)"))
        return None

    # --- loads ---
    if charges:
        loads_block, _excit = b2a._render_charges(charges, md_s)
    else:
        loads_block = ""
    loads_block = ("bridge_f0 = DEFI_CONSTANTE(VALE=0.0)\n"
                   "bridge_f1 = DEFI_CONSTANTE(VALE=1.0)\n" + loads_block +
                   "\n" + "".join(b2a._render_char_meca(n, c, k)
                                  for n, c, k in extra))
    if not charges:
        loads_block += b2a._custom_code(model_data, "code")
    known = model_data.get("mesh_group_names", set())
    sel_renames = model_data.get("selection_renames", renames)
    entries = []
    for sel, kind in vib["open"]:
        name = sel_renames.get(sel, sel)
        if name not in known:
            log(tr("WARNING: Vibro-akoestiek: drukknoop-selectie '{0}' is "
                   "leeg; overgeslagen.",
                   "WARNING: Vibroacoustics: pressure node selection '{0}' "
                   "is empty; skipped.").format(sel))
            continue
        entries.append("        _F({0}='{1}', PRES=0.0, PHI=0.0),\n".format(
            "GROUP_NO" if kind == "node" else "GROUP_MA", name))
        log("INFO: Vibro-acoustics: pressure node p = 0 on '{0}'.".format(sel))
    charge_names = list(constraints)
    if entries:
        loads_block += ("\n# Drukknopen p = 0 (OPEN_-selecties, fluid "
                        "pressure 0): PRES en PHI\n"
                        "bc_flu = AFFE_CHAR_MECA(\n    MODELE=model,\n"
                        "    DDL_IMPO=(\n{0}    ),\n)\n").format(
                            "".join(entries))
        charge_names.append("bc_flu")
    # Sources: one load per face (the phase is in EXCIT PHAS_DEG). VITE_FACE
    # and ONDE_FLUI only accept a real value (catalogue
    # affe_char_meca.py v17.4).
    for k, (g, v, _ph, _es, desc) in enumerate(inp["vite"]):
        loads_block += ("\n# Bron {0}: normaalsnelheid (VITE_FACE)\n"
                        "ch_vite_{1} = AFFE_CHAR_MECA(MODELE=model, "
                        "VITE_FACE=_F(GROUP_MA='{2}', VNOR={3}))\n").format(
                            desc, k + 1, g, _r(v))
    for k, (g, p, _ph, _es, desc) in enumerate(inp["onde"]):
        # ONDE_FLUI PRES = 2 p_in: Code-Aster's boundary is (dp/dn + i k p) =
        # i k PRES, so the wave travelling into the fluid has amplitude
        # PRES / 2 (ahlv101a: PRES 1 -> |p| = 0.5; verification VH-01/VH-04)
        loads_block += ("\n# Invallende golf {0}: amplitude {1} Pa het fluidum "
                        "in (ONDE_FLUI PRES = 2 x amplitude)\n"
                        "ch_onde_{2} = AFFE_CHAR_MECA(MODELE=model, "
                        "ONDE_FLUI=_F(GROUP_MA='{3}', PRES={4}))\n").format(
                            desc, "%.6g" % p, k + 1, g, _r(2.0 * p))
    custom_excit = model_data.get("aster_custom", {}).get("excit", [])
    charge_names += [n for n in custom_excit if n not in charge_names]
    onde_names = ["ch_onde_{0}".format(k + 1)
                  for k in range(len(inp["onde"]))]

    # --- matrices ---
    struct_groups = list(md_s.get("elset_modelisations", {}).keys())
    matr = ["        _F(MATRICE=CO('rigidite'), OPTION='RIGI_MECA'),\n",
            "        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n"]
    # ONDE_FLUI and IMPE_MECA in a separate ASSEMBLAGE without CARA_ELEM
    # (CALC_MATR_ELEM IMPE_MECA refuses CARA_ELEM: <EXCEPTION> SUPERVIS_4,
    # seen with a spring in the model; ahlv101a also assembles IMPE_MECA
    # separately) on the same NUME_DDL.
    impe_matr = []
    if onde_names:
        impe_matr.append("        _F(MATRICE=CO('impe_onde'), "
                         "OPTION='ONDE_FLUI'),\n")
    if abso:
        impe_matr.append("        _F(MATRICE=CO('impe_abso'), "
                         "OPTION='IMPE_MECA'),\n")
    if (alpha or beta) and struct_groups:
        # Rayleigh damping only on the structure (C = alpha M_s + beta
        # K_s): the matrices of the whole model also contain the fluid.
        matr += ["        _F(MATRICE=CO('rigi_s'), OPTION='RIGI_MECA', "
                 "GROUP_MA={0}),\n".format(b2a._fmt_groups(struct_groups)),
                 "        _F(MATRICE=CO('mass_s'), OPTION='MASS_MECA', "
                 "GROUP_MA={0}),\n".format(b2a._fmt_groups(struct_groups))]
    if dampers:
        # AMOR_MECA on the whole model: with GROUP_MA, ASSEMBLAGE gave
        # <EXCEPTION> DVP_1 (dismoi.F90; the elementary RIGI/MASS apply to
        # all elements). The other elements have no Rayleigh coefficients
        # (0); AMOR_FLUI='NON': the absorbing boundaries are in IMPE_MECA
        # (like DYNA_LINE, dyna_line_ops.py). Measured: VH-04c.
        matr.append("        _F(MATRICE=CO('amor_dis'), OPTION='AMOR_MECA', "
                    "AMOR_FLUI='NON'),\n")
    all_charges = charge_names + onde_names
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}{charge}"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n{matr}    ),\n"
        ")\n").format(cara=cara_ref, matr="".join(matr), charge=(
            "    CHARGE=({0},),\n".format(", ".join(all_charges))
            if all_charges else ""))
    if impe_matr:
        assemblage_block += (
            "# Randen van het fluidum: invallende golf (ONDE_FLUI, met de "
            "golflasten)\n# en absorberend (IMPE_MECA, 3D_FLUI_ABSO), zoals "
            "ahlv101a\n"
            "ASSEMBLAGE(\n"
            "    MODELE=model,\n"
            "    CHAM_MATER=fieldmat,\n"
            "{charge}"
            "    NUME_DDL=numedd,\n"
            "    MATR_ASSE=(\n{matr}    ),\n"
            ")\n").format(matr="".join(impe_matr), charge=(
                "    CHARGE=({0},),\n".format(", ".join(onde_names))
                if onde_names else ""))
    impe_terms = (["impe_onde"] if onde_names else []) + \
        (["impe_abso"] if abso else [])
    if len(impe_terms) == 2:
        assemblage_block += (
            "# Impedantie van de randen: invallende golf (ONDE_FLUI) + "
            "absorberend\n# (IMPE_MECA), zoals ahlv101a\n"
            "impe = COMB_MATR_ASSE(COMB_R=(\n"
            "    _F(MATR_ASSE=impe_onde, COEF_R=1.0),\n"
            "    _F(MATR_ASSE=impe_abso, COEF_R=1.0),\n))\n")
    elif impe_terms:
        assemblage_block += "impe = {0}\n".format(impe_terms[0])
    damp_terms = []
    if (alpha or beta) and struct_groups:
        if alpha:
            damp_terms.append(("mass_s", alpha))
        if beta:
            damp_terms.append(("rigi_s", beta))
    if dampers:
        damp_terms.append(("amor_dis", 1.0))
    if damp_terms:
        assemblage_block += (
            "# Demping van de constructie: C = alpha M_s + beta K_s (Mecway "
            "manual\n# par. 9.26) + dempers (AMOR_MECA)\n"
            "amor = COMB_MATR_ASSE(COMB_R=(\n{0}))\n").format("".join(
                "    _F(MATR_ASSE={0}, COEF_R={1!r}),\n".format(m, float(c))
                for m, c in damp_terms))

    # --- load vectors and EXCIT ---
    vec_lines, excit = [], []
    cara_kw = ", CARA_ELEM=cara" if cara else ""
    for k, (charge, fonc) in enumerate(excitations):
        vec_lines += [
            "vel_{0} = CALC_VECT_ELEM(OPTION='CHAR_MECA', CHARGE={1}, "
            "CHAM_MATER=fieldmat{2})".format(k + 1, charge, cara_kw),
            "vec_{0} = ASSE_VECTEUR(VECT_ELEM=vel_{0}, NUME_DDL=numedd)"
            .format(k + 1)]
        mult = "FONC_MULT={0}".format(fonc) if fonc else "COEF_MULT=1.0"
        excit.append("        _F(VECT_ASSE=vec_{0}, {1}, PHAS_DEG={2!r}),"
                     .format(k + 1, mult, float(phases[k])))
    for kind, items in (("vite", inp["vite"]), ("onde", inp["onde"])):
        for k, (_g, _v, phase, _es, desc) in enumerate(items):
            vec_lines += [
                "vel_{0}_{1} = CALC_VECT_ELEM(OPTION='CHAR_MECA', "
                "CHARGE=ch_{0}_{1}, CHAM_MATER=fieldmat)".format(kind, k + 1),
                "vec_{0}_{1} = ASSE_VECTEUR(VECT_ELEM=vel_{0}_{1}, "
                "NUME_DDL=numedd)".format(kind, k + 1)]
            # i w x vector (PUIS_PULS=1, PHAS_DEG=90; ahlv101a, ahlv100b).
            # VITE_FACE: with VNOR > 0 and COEF_MULT=+1 ahlv100b gives p =
            # -rho c v (VNOR outwards); the bridge imposes v into the fluid:
            # COEF_MULT=-1 (measured: VH-01b).
            coef = -1.0 if kind == "vite" else 1.0
            excit.append("        _F(VECT_ASSE=vec_{0}_{1}, COEF_MULT={2!r}, "
                         "PUIS_PULS=1, PHAS_DEG={3!r}),  # {4}".format(
                             kind, k + 1, coef, 90.0 + float(phase), desc))
    vectors_block = "\n".join(vec_lines) + "\n"

    harm_block = (
        "bridge_lf = DEFI_LIST_REEL(VALE=({0},))\n"
        "print('BRIDGE_HARM_LIJST N=%d FMIN=%.10g FMAX=%.10g VERFIJND=0 "
        "BASIS=PHYS' % ({1}, {2}, {3}))\n"
        "res = DYNA_VIBRA(\n"
        "    TYPE_CALCUL='HARM',\n"
        "    BASE_CALCUL='PHYS',\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}"
        "    MATR_MASS=masse,\n"
        "    MATR_RIGI=rigidite,\n"
        "{amor}{impe}{flui}"
        "    LIST_FREQ=bridge_lf,\n"
        "    NOM_CHAM=('DEPL',),\n"
        "    EXCIT=(\n{excit}\n    ),\n"
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={nprec}),\n"
        ")\n").format(
            ", ".join(_r(f) for f in freqs), len(freqs), _r(freqs[0]),
            _r(freqs[-1]), cara=cara_ref,
            amor="    MATR_AMOR=amor,\n" if damp_terms else "",
            impe="    MATR_IMPE_PHI=impe,\n" if impe_terms else "",
            # like DYNA_LINE (dyna_line_ops.py): with MATR_AMOR and
            # MATR_IMPE_PHI together AMOR_FLUI='NON'
            flui="    AMOR_FLUI='NON',\n" if damp_terms and impe_terms
            else "",
            excit="\n".join(excit),
            nprec=int(analysis.get("solver_nprec", 8)))

    if stresses:
        calc_champ_block = (
            "# Complexe spanningen in de volume-elementen van de constructie\n"
            "res = CALC_CHAMP(\n"
            "    reuse=res,\n"
            "    RESULTAT=res,\n"
            "    MODELE=model,\n"
            "    CHAM_MATER=fieldmat,\n"
            "{0}"
            "    GROUP_MA={1},\n"
            "    CONTRAINTE=('SIGM_NOEU',),\n"
            ")\n").format(cara_ref, b2a._fmt_groups(g3d))
    else:
        calc_champ_block = "#-- no stresses (fields or no volumes) --\n"

    scripts = os.path.dirname(os.path.abspath(__file__))

    def _ids(d):
        return "{" + ", ".join("{0}: [{1}]".format(
            b2a._py_str(name), ", ".join(str(n) for n in nids))
            for name, nids in d.items()) + "}"
    export_block = b2a._custom_code(model_data, "post") + (
        "# Resultaten in Mecway's eigen formaat (result_route 'liml'): een\n"
        "# <mode frequency> per frequentie met de verplaatsing van de\n"
        "# constructie en de druk in het fluidum (aster_harmonic_export)\n"
        "import sys\n"
        "sys.path.insert(0, {0})\n"
        "import aster_harmonic_export\n"
        "aster_harmonic_export.export_harmonic(\n"
        "    res, {1}, {2},\n"
        "    fields={3!r},\n"
        "    probes={4},\n"
        "    csv_path={5},\n"
        "    language={6},\n"
        "    basis='PHYS',\n"
        "    pressure=True,\n"
        "    microphones={7},\n"
        "    mic_csv_path={8})\n").format(
            b2a._py_str(scripts), b2a._py_str(b2a.results_file(work_dir)),
            b2a._py_str(model_data.get("liml_path", "")),
            [str(f) for f in fields], _ids(probes),
            b2a._py_str(os.path.join(work_dir, run_name(PROBE_SUFFIX))),
            b2a._py_str(CONFIG_BRIDGE.get("language", "en")),
            _ids(inp["mics"]),
            b2a._py_str(os.path.join(work_dir, run_name(MIC_SUFFIX))))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = (
            "IMPR_RESU(FORMAT='MED', UNITE=80, RESU=(\n"
            "    _F(RESULTAT=res, NOM_CHAM='DEPL', PARTIE='REEL', "
            "NOM_CHAM_MED='DEPL_REEL'),\n"
            "    _F(RESULTAT=res, NOM_CHAM='DEPL', PARTIE='IMAG', "
            "NOM_CHAM_MED='DEPL_IMAG'),\n))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    log("INFO: Harmonic vibro-acoustics (direct, DYNA_VIBRA PHYS): {0} "
        "frequency(ies) from {1} to {2} Hz; {3} load(s) on the "
        "structure, {4} velocity source(s), {5} incident wave(s), "
        "{6} absorbing boundary(ies), Rayleigh alpha {7} 1/s, beta {8} s{9}; "
        "{10} microphone(s), {11} probe(s).".format(
            len(freqs), "%.6g" % freqs[0], "%.6g" % freqs[-1],
            len(excitations), len(inp["vite"]), len(inp["onde"]), len(abso),
            alpha, beta, ", dempers " + ", ".join(dampers) if dampers else "",
            len(inp["mics"]), len(probes)))
    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = b2a._read_template(analysis["template"])
        b2a._write_comm(comm_path, template.format(
            defigroup_block=defigroup_block,
            model_block=model_block,
            cara_elem_block=cara_elem_block,
            materials_block=materials_block,
            fieldmat_block=fieldmat_block,
            load_funcs_block=bh._freq_funcs_block(load_funcs),
            loads_block=loads_block,
            assemblage_block=assemblage_block,
            vectors_block=vectors_block,
            harm_block=harm_block,
            calc_champ_block=calc_champ_block,
            export_block=export_block,
            impr_resu_block=impr_resu_block,
        ))
        log("SUCCESS: .comm written to '{0}'.".format(comm_path))
        export_path = os.path.join(work_dir, run_name(".export"))
        with open(export_path, "w") as f:
            f.write("\n".join([
                "P actions make_etude",
                "P time_limit {0}".format(analysis.get("time_limit", 1800)),
                "P memory_limit {0}".format(analysis.get("memory_limit",
                                                         2048)),
                "P mpi_nbcpu 1",
                "P ncpus {0}".format(CONFIG_BRIDGE["ncpus"]),
                "P no-mpi true",
                "F comm {0} D 1".format(comm_path),
                "F mail {0} D 20".format(msh_path),
                "F mess {0} R 6".format(os.path.join(work_dir,
                                                     run_name(".mess"))),
            ]) + b2a._export_result_lines(work_dir, resu_name))
        log("SUCCESS: .export written to '{0}'.".format(export_path))
        return export_path
    except KeyError as e:
        log(tr("ERROR: Template placeholder ontbreekt: {0}.",
               "ERROR: Template placeholder missing: {0}.").format(str(e)))
    except Exception as e:
        log(tr("ERROR: Genereren vibro-akoestische solver-bestanden mislukt: "
               "{0}",
               "ERROR: Generating the vibroacoustic solver files failed: "
               "{0}").format(str(e)))
    return None


# ==========================================
# AFTER THE RUN (IronPython): LOG AND STATUS BOX
# ==========================================
def report_harmonic(work_dir, frequencies):
    """
    After a harmonic vibro-acoustic run: number of frequencies, per
    microphone the highest level and per probe the largest amplitude.
    Returns the lines for the status box. frequencies: [(id, "frequency",
    f)] from read_modes().
    """
    fs = [f for _i, _k, f in frequencies]
    lines = [tr(u"Vibro-akoestiek harmonisch (direct): {0} frequentie(s), "
                u"{1} .. {2} Hz. Velden per frequentie: constructie displx/"
                u"y/z (Re), displix/y/z (Im), displamp*, displphase*, "
                u"displmag; fluidum pressure (Re), pressurei (Im), "
                u"pressuremag, pressurephase, spl (dB re 20 uPa).",
                u"Vibroacoustics harmonic (direct): {0} frequency(ies), {1} "
                u".. {2} Hz. Fields per frequency: structure displx/y/z "
                u"(Re), displix/y/z (Im), displamp*, displphase*, displmag; "
                u"fluid pressure (Re), pressurei (Im), pressuremag, "
                u"pressurephase, spl (dB re 20 uPa).").format(
                    len(fs), "%.6g" % min(fs) if fs else "-",
                    "%.6g" % max(fs) if fs else "-")]
    mic_path = os.path.join(work_dir, run_name(MIC_SUFFIX))
    by_name = OrderedDict()
    for name, f, amp, phase, level in bac.read_microphones(mic_path):
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
                            mic_path))
    probe_path = os.path.join(work_dir, run_name(PROBE_SUFFIX))
    probes = OrderedDict()
    for name, f, amp, acc in bh.read_probes(probe_path):
        probes.setdefault(name, []).append((f, amp, acc))
    for name, rows in probes.items():
        f, amp, acc = max(rows, key=lambda r: r[1])
        lines.append(tr(u"Meetpunt {0}: grootste amplitude |u| = {1} m bij "
                        u"{2} Hz (|a| = {3} m/s2).",
                        u"Probe {0}: largest amplitude |u| = {1} m at {2} Hz "
                        u"(|a| = {3} m/s2).").format(
                            name, "%.4g" % amp, "%.6g" % f, "%.4g" % acc))
    if probes:
        lines.append(tr(u"Frequentierespons per meetpunt: {0}",
                        u"Frequency response per probe: {0}").format(
                            probe_path))
    for line in lines:
        log(u"INFO: " + line)
    return lines
