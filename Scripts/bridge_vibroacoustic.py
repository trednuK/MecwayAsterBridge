# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_vibroacoustic.py
# Responsibility: vibro-acoustics, a structure and an air or liquid
# volume coupled in one model (coupled eigenmodes), from a Mecway
# Frequency model (V30). Mecway has no coupled analysis
# and computes acoustics (A30) with one material; the bridge computes the
# model with Code-Aster PHENOMENE='MECANIQUE':
#   fluid       MODELISATION='3D_FLUIDE'  (degrees of freedom PRES and PHI)
#   interface   MODELISATION='FLUI_STRU'  (DX, DY, DZ, PRES, PHI; there is
#               no '3D_FLUI_STRU')
#   structure   the normal mechanical elements (3D, DKT, COQUE_3D, ...)
# with FORMULATION='U_P_PHI' (catalogue affe_modele.py v17.4: U_P_PHI,
# U_P or U_PSI, default U_P_PHI; test cases adlv100a, adlv100p, ahlv101a).
#
#   parse_vibro(root, model_data, run_cfg) - bridge_from_liml STEP 2c:
#                         fluid parts, materials (c, rho), pressure nodes
#                         (OPEN_ selections, fluid pressure 0), KOPPEL_.
#   interface_faces(model_data, conn)      - bridge_mesh.write_mesh: the
#                         coupling faces as boundary elements (groups
#                         BRFSI<k>).
#   resolve_auto(resolved, model_data)     - MecwayAsterBridgeMain: 'auto'
#                         with V30 with a fluid -> vibroacoustic_modes_3d.
#   build_vibroacoustic_modes(...)         - builder; bridge_to_aster.
#                         _build_modal sends the analysis here
#                         (analysis "vibroacoustic": True).
#
# Input in Mecway (STAPPENPLAN S3b, approach B):
#   - A part (elset) is fluid if its material has a speed of sound
#     and no modulus of elasticity (Mecway's acoustic
#     material: <mechanical type="Isotropic" speedofsound="340 m/s" /> with
#     <density>), or if the name of the part starts with LUCHT_,
#     VLOEISTOF_ or FLUID_ (then a speed of sound is needed as well).
#   - Coupling faces: automatic, every face of a fluid element that
#     coincides with a face of a structural volume element or with a
#     shell element (shared nodes). Face selections KOPPEL_... /
#     COUPLING_...: then only those faces (manual choice).
#   - Pressure node p = 0 (free surface, open end): node or face selection
#     OPEN_..., or Mecway's fluid pressure = 0 (exists in Mecway only
#     in Acoustic Resonance, manual v33 par. 9.34; if it is in the .liml,
#     it is used).
#   - A face without a condition is a rigid wall (dp/dn = 0).
#
# Measured with Code-Aster 17.4 (scratch runs, verification VA):
#   - U_P_PHI: K has no term for PHI, so every PHI degree of freedom
#     gives an eigenvalue 0 (adlv100a mesh: 40 such modes at |f| <
#     1e-5 Hz with negative MASS_GENE). PLUS_PETITE stops with ALGELINE3_81
#     (K singular) and CENTRE around 1 Hz first gives those spurious modes.
#     OPTION 'BANDE' from f_min > 0 gives only the real modes: the Sturm
#     count (INFO_MODE) is correct (bar + water column: 6 of 6 analytical
#     modes, <= 1e-4). The bridge therefore searches with INFO_MODE for a
#     band [f_min, f_max] with at least the requested number of modes and
#     takes the first ones (_mode_search_block).
#   - U_P (non-symmetric) gave a wrong series with PLUS_PETITE (1147
#     Hz first instead of 13.83 Hz, adlv100a) and with CENTRE -10 Hz on the
#     bar <F> JEVEUX_26: not used. U_PSI: DDL_IMPO PRES does not exist
#     (<F> CHARGES2_45).
#   - The density is included in the matrices (unlike RIGI_ACOU/MASS_ACOU,
#     KNOWN_BUGS 55): bar + water column with rho 1000 and 1 each gave its
#     own analytical frequencies.
#   - The real modes have MASS_GENE > 0 and NORM_MODE MASS_GENE works.
#     BANDE can also return a spurious mode outside the band (seen with
#     a tilting shell: 3e-5 Hz with MASS_GENE < 0; NORM_MODE then gave
#     <EXCEPTION> DVP_2): the bridge filters first (f >= f_min, MASS_GENE >
#     0) and normalizes afterwards.
#   - Pressure node: DDL_IMPO PRES = 0 and PHI = 0 (adlv100p); the coupling
#     faces get the material of the fluid (adlv100a) and a normal out of
#     the fluid (MODI_MAILLAGE ORIE_PEAU with GROUP_MA_INTERNE = fluid,
#     adlv100b, adls102a, fdlv112h).
#
# Compatible with IronPython 2.7.9 (standard library only).

import os
from collections import OrderedDict

from bridge_utils import (log, parse_and_convert, CONFIG_BRIDGE, tr,
                          run_name)

ANALYSIS = "vibroacoustic_modes_3d"

# Prefixes (Mecway name, case-insensitive).
FLUID_PREFIXES = ("LUCHT_", "VLOEISTOF_", "FLUID_")
OPEN_PREFIXES = ("OPEN_",)
COUPLING_PREFIXES = ("KOPPEL_", "COUPLING_")
# Selections of harmonic (vibro-)acoustics (bridge_acoustic._PREFIXES,
# bridge_vibroacoustic_harm): meaningless in the modes (INFO), in the
# harmonic response (vibroacoustic_harm_3d) per role in "named".
HARM_ROLES = (("source", ("BRON_", "SOURCE_")),
              ("absorbing", ("ABSORBEREND_", "ABSORBING_")),
              ("microphone", ("MICROFOON_", "MICROPHONE_")),
              ("incident", ("INVALLEND_", "INCIDENT_")))
_HARM_PREFIXES = tuple(p for _role, ps in HARM_ROLES for p in ps)

# Mecway shapes with a 3D_FLUIDE element (elem.1 of 17.4: MEFL_HEXA8/20,
# MEFL_PENTA6/15, MEFL_TETRA4/10, MEFL_PYRAM5/13).
_FLUID_SHAPES = frozenset(["hex8", "hex20", "wedge6", "wedge15", "tet4",
                           "tet10", "pyr5", "pyr13"])

# Groups of the coupling faces (one per fluid part) in the mesh.
INTERFACE_PREFIX = "BRFSI"


def is_vibroacoustic(analysis_cfg):
    """True if the analysis config is vibro-acoustic."""
    return bool((analysis_cfg or {}).get("vibroacoustic", False))


def _starts(name, prefixes):
    upper = (name or "").upper()
    for p in prefixes:
        if upper.startswith(p):
            return True
    return False


def _r(x):
    import bridge_mesh
    return bridge_mesh._real(float(x))


def _may_apply(run_cfg, model_data):
    """True if this run is vibro-acoustic or can become so ('auto' with
    a Frequency model, resolve_auto)."""
    if is_vibroacoustic(run_cfg):
        return True
    return (CONFIG_BRIDGE.get("active_analysis") == "auto" and
            model_data.get("analysis_type") == "V30" and
            ANALYSIS in CONFIG_BRIDGE.get("analyses", {}))


def wanted():
    """True if the active analysis is vibro-acoustic (bridge_mesh: then the
    coupling faces in the mesh)."""
    name = CONFIG_BRIDGE.get("active_analysis")
    return is_vibroacoustic(CONFIG_BRIDGE.get("analyses", {}).get(name))


# ==========================================
# PARSING
# ==========================================
def _materials(root):
    """{material: {"c": m/s or None, "rho": kg/m3 or None, "E": bool}}."""
    out = OrderedDict()
    for mat in root.findall("mat"):
        name = mat.get("name", "UnknownMat")
        mech = mat.find("mechanical")
        dens = mat.find("density")
        c = mech.get("speedofsound") if mech is not None else None
        rho = dens.get("density") if dens is not None else None
        out[name] = {
            "c": parse_and_convert(c, "velocity") if c else None,
            "rho": parse_and_convert(rho, "density") if rho else None,
            "E": mech is not None and mech.get("youngsmodulus") is not None,
            "type": mech.get("type", "Isotropic") if mech is not None
            else None}
    return out


def _selection_kind(model_data, name):
    if name in model_data.get("node_groups", {}):
        return "node"
    if name in model_data.get("face_selection_faces", {}):
        return "face"
    if name in model_data.get("element_selections", {}):
        return "element"
    return None


def parse_vibro(root, model_data, run_cfg):
    """
    Fluid parts and their conditions to model_data["vibro"] (None
    if the model has no fluid):
      "fluid_elsets": OrderedDict {Mecway part: material}
      "fluid_eids":   set(element ids)
      "materials":    {material: {"c", "rho", "E", "type"}}
      "open":         [(selection, "node"/"face")]  p = 0
      "coupling":     [face selection]  KOPPEL_ (manual)
      "pressure_src": [(selection, text)]  fluid pressure != 0
      "impedances":   [selection]
      "impedance_values": [(selection, Re Z, Im Z)]  (Pa.s/m; harmonic)
      "ignored":      [selection]  BRON_/ABSORBEREND_/MICROFOON_/INVALLEND_
      "named":        {role: [(selection, kind)]}  the same selections per
                      role (HARM_ROLES; vibroacoustic_harm_3d)
      "bad":          [text]  fatal input errors
      "interfaces":   {group: Mecway part} (interface_faces)
    Outside a vibro-acoustic run only a WARNING (the fluid would be
    computed as a solid with the default E of the bridge).
    """
    model_data["vibro"] = None
    mats = _materials(root)
    fluid = OrderedDict()
    bad = []
    for elset, mat in model_data.get("elsets", {}).items():
        props = mats.get(mat, {})
        by_mat = bool(props.get("c")) and not props.get("E")
        by_name = _starts(elset, FLUID_PREFIXES)
        if by_mat or by_name:
            fluid[elset] = mat
            if not props.get("c"):
                bad.append(tr(
                    "onderdeel '{0}' heet een fluidum, maar materiaal '{1}' "
                    "heeft geen geluidssnelheid (Speed of sound)",
                    "part '{0}' is named a fluid, but material '{1}' has no "
                    "speed of sound").format(elset, mat))
    if not fluid:
        return
    if not _may_apply(run_cfg, model_data):
        log(tr("WARNING: Onderde(e)l(en) {0} hebben een materiaal met een "
               "geluidssnelheid en zonder elasticiteitsmodulus (een "
               "fluidum). In deze analyse rekent de bridge ze als vaste stof "
               "(standaard E = 210 GPa; Mecway rekent met E = 0). Voor "
               "constructie + lucht/vloeistof: kies de analyse '{1}' (of "
               "'auto' bij een Frequency-model).",
               "WARNING: Part(s) {0} have a material with a speed of sound "
               "and without Young's modulus (a fluid). In this analysis the "
               "bridge computes them as a solid (default E = 210 GPa; Mecway "
               "uses E = 0). For structure + air/fluid: choose the analysis "
               "'{1}' (or 'auto' with a Frequency model).").format(
                   ", ".join("'%s'" % e for e in fluid), ANALYSIS))
        return
    eids = set(eid for eid, _s, _n, es in model_data.get("mesh_elements", [])
               if es in fluid)
    vib = {"fluid_elsets": fluid, "fluid_eids": eids, "materials": mats,
           "open": [], "coupling": [], "pressure_src": [], "impedances": [],
           "impedance_values": [], "ignored": [], "bad": bad,
           "interfaces": OrderedDict(),
           "named": dict((role, []) for role, _p in HARM_ROLES)}
    for kind, names in (("face", model_data.get("face_selection_faces", {})),
                        ("node", model_data.get("node_groups", {})),
                        ("element", model_data.get("element_selections",
                                                   {}))):
        for name in names:
            if _starts(name, OPEN_PREFIXES):
                if kind == "element":
                    bad.append(tr("OPEN_-selectie '{0}' is een "
                                  "elementselectie; kies knopen of vlakken",
                                  "OPEN_ selection '{0}' is an element "
                                  "selection; choose nodes or "
                                  "faces").format(name))
                else:
                    vib["open"].append((name, kind))
            elif _starts(name, COUPLING_PREFIXES):
                if kind != "face":
                    bad.append(tr("KOPPEL_-selectie '{0}' is een {1}"
                                  "selectie; kies een vlakselectie",
                                  "COUPLING_ selection '{0}' is a {1} "
                                  "selection; choose a face "
                                  "selection").format(name, kind))
                else:
                    vib["coupling"].append(name)
            elif _starts(name, _HARM_PREFIXES):
                vib["ignored"].append(name)
                for role, prefixes in HARM_ROLES:
                    if _starts(name, prefixes):
                        vib["named"][role].append((name, kind))
    for item in root:
        if item.tag not in ("fluidpressure", "impedance"):
            continue
        sel = item.get("selection", "")
        if item.get("suppressed", "") == "true":
            continue
        if item.tag == "impedance":
            import bridge_acoustic
            vib["impedances"].append(sel)
            vib["impedance_values"].append(
                (sel, bridge_acoustic._number(item.findtext(
                    "specificimpedancer")),
                 bridge_acoustic._number(item.findtext(
                     "specificimpedancei"))))
            continue
        text = item.findtext("value")
        try:
            value = float(parse_and_convert(text, "pressure")) if text \
                else 0.0
        except (TypeError, ValueError):
            value = None
        kind = _selection_kind(model_data, sel)
        if value is None or abs(value) > 0.0:
            vib["pressure_src"].append((sel, text))
        elif kind not in ("node", "face"):
            bad.append(tr("fluid pressure op '{0}': kies een knoop- of "
                          "vlakselectie",
                          "fluid pressure on '{0}': choose a node or face "
                          "selection").format(sel))
        elif (sel, kind) not in vib["open"]:
            vib["open"].append((sel, kind))
    for elset, mat in fluid.items():
        props = mats.get(mat, {})
        log("INFO: Vibro-acoustics: part '{0}' is fluid (material "
            "'{1}': c = {2} m/s, rho = {3} kg/m3).".format(
                elset, mat, props.get("c"), props.get("rho")))
    model_data["vibro"] = vib


def resolve_auto(resolved, model_data):
    """Analysis for 'auto': a Frequency model (V30 -> modal_3d) with a
    fluid -> vibroacoustic_modes_3d."""
    if (resolved == "modal_3d" and model_data.get("vibro") and
            ANALYSIS in CONFIG_BRIDGE.get("analyses", {})):
        log("INFO: Vibro-acoustics: the Frequency model has a fluid "
            "({0}); 'auto' chooses '{1}'.".format(
                ", ".join(model_data["vibro"]["fluid_elsets"]), ANALYSIS))
        return ANALYSIS
    return resolved


# ==========================================
# COUPLING FACES IN THE MESH (bridge_mesh.write_mesh)
# ==========================================
def interface_faces(model_data, conn):
    """
    Fluid-structure coupling faces as boundary elements: OrderedDict
    {group: [(type, nodes)]} with one group BRFSI<k> per fluid part
    (the coupling face gets the material of that fluid); sets
    model_data["vibro"]["interfaces"] = {group: Mecway part}. None on
    an error (ERROR logged).
    Automatic: a face of a fluid element whose corner nodes
    coincide with a face of a structural volume element or with a
    shell element. With KOPPEL_ face selections only those faces.
    """
    import bridge_mesh as bm
    vib = model_data.get("vibro") or {}
    fluid = vib.get("fluid_eids", set())
    shapes = model_data.get("elem_shapes", {})
    elem_elset = dict((eid, es) for eid, _s, _n, es
                      in model_data.get("mesh_elements", []))
    faces = OrderedDict()           # corner nodes -> [(eid, corners)]
    for eid in sorted(conn):
        if shapes.get(eid) not in bm._SOLID_SHAPES:
            continue
        atype, cn = conn[eid]
        for prefix, table in bm._FACE_CORNERS.items():
            if atype.startswith(prefix):
                for fid in sorted(table):
                    corners = [cn[i] for i in table[fid]]
                    faces.setdefault(frozenset(corners), []).append(
                        (eid, corners))
                break
    shells = {}
    for eid, (atype, cn) in conn.items():
        if shapes.get(eid) in bm._SHELL_SHAPES:
            shells.setdefault(frozenset(cn[:bm._N_CORNERS[atype]]),
                              []).append(eid)
    auto = OrderedDict()            # corner nodes -> (fluid eid, corners)
    double = []
    for key, owners in faces.items():
        flu = [o for o in owners if o[0] in fluid]
        if not flu:
            continue
        solid = [o for o in owners if o[0] not in fluid]
        if not solid and key not in shells:
            continue
        if len(flu) > 1:
            # Shell between two fluid elements with the same nodes: the
            # pressure would be continuous across the shell.
            double.extend(shells.get(key, []))
            continue
        auto[key] = flu[0]
    if double:
        log(tr("ERROR: Vibro-akoestiek: schaalelement(en) {0} hebben aan "
               "beide kanten fluidum met dezelfde knopen; de druk zou over de "
               "schaal doorlopen (geen drukverschil). Modelleer het paneel "
               "als volume-elementen (een laag hex/wedge) of laat het "
               "fluidum aan een kant weg.",
               "ERROR: Vibroacoustics: shell element(s) {0} have fluid on "
               "both sides with the same nodes; the pressure would be "
               "continuous across the shell (no pressure difference). Model "
               "the panel as solid elements (one layer of hex/wedge) or "
               "leave out the fluid on one side.").format(
                   ", ".join(str(e) for e in sorted(set(double))[:10])))
        return None
    chosen = auto
    manual = vib.get("coupling", [])
    if manual:
        chosen = OrderedDict()
        bad = []
        for sel in manual:
            for eid, fid in model_data.get("face_selection_faces", {}).get(
                    sel, []):
                if eid not in conn:
                    continue
                corners = bm._face_from_table(conn[eid][0], conn[eid][1],
                                              fid)
                if shapes.get(eid) in bm._SHELL_SHAPES:
                    atype, cn = conn[eid]
                    corners = cn[:bm._N_CORNERS[atype]]
                key = frozenset(corners or [])
                flu = [o for o in faces.get(key, []) if o[0] in fluid]
                if len(flu) != 1:
                    bad.append("{0} ({1} {2})".format(sel, eid, fid))
                    continue
                chosen[key] = flu[0]
        if bad:
            log(tr("ERROR: Vibro-akoestiek: vlak(ken) van KOPPEL_-selecties "
                   "liggen niet aan precies een fluidum-element: {0}. Een "
                   "koppelvlak deelt zijn knopen met een fluidum-element.",
                   "ERROR: Vibroacoustics: face(s) of COUPLING_ selections "
                   "do not border exactly one fluid element: {0}. A "
                   "coupling face shares its nodes with a fluid "
                   "element.").format(", ".join(bad[:10])))
            return None
        missing = [k for k in auto if k not in chosen]
        log("INFO: Vibro-acoustics: coupling faces from KOPPEL_ selections "
            "({0}): {1} face(s).".format(", ".join(manual), len(chosen)))
        if missing:
            log(tr("WARNING: Vibro-akoestiek: {0} vlak(ken) waar fluidum en "
                   "constructie knopen delen, staan niet in een KOPPEL_-"
                   "selectie en zijn niet gekoppeld.",
                   "WARNING: Vibroacoustics: {0} face(s) where fluid and "
                   "structure share nodes are not in a COUPLING_ selection "
                   "and are not coupled.").format(len(missing)))
    order = list(vib.get("fluid_elsets", {}))
    out = OrderedDict()
    groups = OrderedDict()
    for key, (eid, corners) in chosen.items():
        es = elem_elset.get(eid)
        group = "{0}{1}".format(INTERFACE_PREFIX, order.index(es) + 1)
        atype, cn = conn[eid]
        out.setdefault(group, []).append(bm._skin_element(atype, cn,
                                                          corners))
        groups[group] = es
    vib["interfaces"] = groups
    for group, es in groups.items():
        log("INFO: Vibro-acoustics: coupling face '{0}' ({1} faces) on "
            "fluid '{2}'.".format(group, len(out[group]), es))
    return out


# ==========================================
# BUILDER
# ==========================================
def _structure_view(model_data, fluid_ca, fluid_mats):
    """Copy of model_data with only the structure (for the blocks of
    bridge_to_aster: AFFE_MODELE, AFFE_CARA_ELEM, DEFI_MATERIAU,
    AFFE_MATERIAU, loads)."""
    md = dict(model_data)
    md["elset_modelisations"] = OrderedDict(
        (es, m) for es, m in model_data.get("elset_modelisations",
                                            {}).items()
        if es not in fluid_ca)
    md["elsets"] = OrderedDict(
        (es, m) for es, m in model_data.get("elsets", {}).items()
        if es not in fluid_ca)
    used = set(md["elsets"].values())
    md["materials"] = OrderedDict(
        (m, p) for m, p in model_data.get("materials", {}).items()
        if m in used or m not in fluid_mats)
    md.pop("_mat_concepts", None)
    return md


def _insert_affe(text, head, entries):
    """Put lines after the last _F of AFFE=( ... ) of the call that
    starts with head (AFFE_MODELE/AFFE_MATERIAU of bridge_to_aster)."""
    start = text.find(head)
    affe = text.find("    AFFE=(\n", start)
    end = text.find("\n    ),\n", affe)
    if start < 0 or affe < 0 or end < 0:
        return None
    return text[:end + 1] + entries + text[end + 1:]


def _check_fluid(model_data, vib, fluid_ca):
    """Shapes and materials of the fluid; list of errors."""
    bad = []
    wrong = OrderedDict()
    for eid, shape, _n, es in model_data.get("mesh_elements", []):
        if eid in vib["fluid_eids"] and shape not in _FLUID_SHAPES:
            wrong.setdefault(es, set()).add(shape)
    for es, shapes in wrong.items():
        bad.append(tr("fluidum '{0}' bevat {1}; alleen volume-elementen "
                      "(hex, wedge, tet, piramide)",
                      "fluid '{0}' contains {1}; only solid elements (hex, "
                      "wedge, tet, pyramid)").format(
                          es, ", ".join(sorted(shapes))))
    for mat in sorted(set(fluid_ca.values())):
        props = vib["materials"].get(mat, {})
        if not (props.get("rho") or 0.0) > 0.0:
            bad.append(tr("fluidum-materiaal '{0}' heeft geen dichtheid "
                          "(nodig: de koppeling en de toegevoegde massa "
                          "hangen ervan af)",
                          "fluid material '{0}' has no density (needed: the "
                          "coupling and the added mass depend on "
                          "it)").format(mat))
        if not (props.get("c") or 0.0) > 0.0:
            bad.append(tr("fluidum-materiaal '{0}' heeft geen "
                          "geluidssnelheid",
                          "fluid material '{0}' has no speed of "
                          "sound").format(mat))
    # Two fluids with shared nodes: PHI is continuous there, and with p =
    # rho w^2 PHI that is only correct for equal density (measured: tube
    # with rho 1.2 / 12 and c 340 / 680 gave 188.23 Hz, analytical
    # 306.47 Hz; with equal density exact, verification VA-04).
    nodes = OrderedDict()
    for eid, _shape, enodes, es in model_data.get("mesh_elements", []):
        if eid in vib["fluid_eids"]:
            nodes.setdefault(es, set()).update(enodes)
    names = list(nodes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ra = vib["materials"].get(vib["fluid_elsets"][a], {}).get("rho")
            rb = vib["materials"].get(vib["fluid_elsets"][b], {}).get("rho")
            if not (ra and rb) or abs(ra - rb) <= 1.0e-6 * max(ra, rb):
                continue
            if nodes[a] & nodes[b]:
                bad.append(tr(
                    "fluida '{0}' (rho {1}) en '{2}' (rho {3}) raken elkaar "
                    "met een andere dichtheid; dat kan de bridge niet "
                    "(bijv. lucht boven water: laat de lucht weg en leg "
                    "p = 0 op het wateroppervlak met een OPEN_-selectie)",
                    "fluids '{0}' (rho {1}) and '{2}' (rho {3}) touch with "
                    "a different density; the bridge cannot do that (e.g. "
                    "air above water: leave out the air and put p = 0 on "
                    "the water surface with an OPEN_ selection)").format(
                        a, "%g" % ra, b, "%g" % rb))
    return bad


def _mode_search_block(model_data, analysis, n):
    """
    res = the first n modes above vibro_freq_min (see the header: U_P_PHI
    gives spurious modes at 0 Hz, only OPTION 'BANDE' from f_min > 0 is
    clean). INFO_MODE (Sturm count, catalogue info_mode.py v17.4: FREQ =
    list, table NB_MODE) searches an upper limit with >= n modes: x4 per
    step, then two bisections (geometric) so as not to compute many more
    modes than needed. CALC_MODES BANDE (SOLVEUR_MODAL COEF_DIM_ESPACE 4,
    like adlv312a) without normalization, then the modes with f >= f_min
    and MASS_GENE > 0 (EXTR_MODE NUME_ORDRE, catalogue extr_mode.py) and
    NORM_MODE MASS_GENE (catalogue norm_mode.py: reuse on MODE).
    """
    try:
        fmin = float(analysis.get("vibro_freq_min", 0.1))
    except (TypeError, ValueError):
        fmin = 0.0
    if fmin <= 0.0:
        log(tr("WARNING: Vibro-akoestiek: vibro_freq_min moet > 0 zijn "
               "(valse modes bij 0 Hz); 0,1 Hz gebruikt.",
               "WARNING: Vibroacoustics: vibro_freq_min must be > 0 "
               "(spurious modes at 0 Hz); 0.1 Hz used."))
        fmin = 0.1
    nprec = int(analysis.get("solver_nprec", 8))
    seuil = "%.10g" % float(analysis.get("modal_tolerance", 1.0e-6))
    log("INFO: CALC_MODES vibro-acoustic: the first {0} modes above {1} "
        "Hz (OPTION 'BANDE', band searched with INFO_MODE).".format(
            n, "%.6g" % fmin))
    lines = [
        "# Coupled modes (U_P_PHI): every PHI degree of freedom gives a",
        "# spurious mode at 0 Hz; hence the band [f_min, f_max] with at least",
        "# bridge_n modes (Sturm count INFO_MODE) and CALC_MODES BANDE",
        "# (bridge_vibroacoustic._mode_search_block).",
        "bridge_n = {0}".format(n),
        "bridge_fmin = {0}".format(_r(fmin)),
        "",
        "def _bridge_count(_fhi):",
        "    _t = INFO_MODE(TYPE_MODE='DYNAMIQUE', MATR_RIGI=rigidite,",
        "                   MATR_MASS=masse, FREQ=(bridge_fmin, _fhi),",
        "                   SOLVEUR=_F(METHODE='MUMPS', NPREC={0}))".format(
            nprec),
        "    return int(_t.EXTR_TABLE().values()['NB_MODE'][0])",
        "",
        "_lo, _hi = bridge_fmin, max(10.0 * bridge_fmin, 1.0)",
        "_nhi = _bridge_count(_hi)",
        "while _nhi < bridge_n and _hi < 1.0e7:",
        "    _lo, _hi = _hi, 4.0 * _hi",
        "    _nhi = _bridge_count(_hi)",
        "for _k in range(2):",
        "    _mid = (_lo * _hi) ** 0.5",
        "    if _mid <= _lo * 1.0001:",
        "        break",
        "    _nmid = _bridge_count(_mid)",
        "    if _nmid >= bridge_n:",
        "        _hi, _nhi = _mid, _nmid",
        "    else:",
        "        _lo = _mid",
        "print('BRIDGE_VIBRO_BAND', bridge_fmin, _hi, _nhi)",
        "if _nhi < 1:",
        "    raise ValueError('BRIDGE_VIBRO: geen modes tussen %g en %g Hz'"
        " % (bridge_fmin, _hi))",
        "# Without NORM_MODE: BANDE can also return a spurious mode outside",
        "# the band (seen: 3e-5 Hz with MASS_GENE < 0); normalizing on",
        "# MASS_GENE gave <EXCEPTION> DVP_2. Filter first, then normalize.",
        "res_band = CALC_MODES(",
        "    TYPE_RESU='DYNAMIQUE',",
        "    MATR_RIGI=rigidite,",
        "    MATR_MASS=masse,",
        "    OPTION='BANDE',",
        "    CALC_FREQ=_F(FREQ=(bridge_fmin, _hi)),",
        "    SOLVEUR_MODAL=_F(COEF_DIM_ESPACE=4),",
        "    VERI_MODE=_F(SEUIL={0}, STOP_ERREUR='NON'),".format(seuil),
        "    SOLVEUR=_F(METHODE='MUMPS', NPREC={0}),".format(nprec),
        ")",
        "_tb = RECU_TABLE(CO=res_band, NOM_PARA=('FREQ', 'MASS_GENE'))"
        ".EXTR_TABLE().values()",
        "_good = [_i for _i, _f, _m in zip(_tb['NUME_ORDRE'], _tb['FREQ'],",
        "                                  _tb['MASS_GENE'])",
        "         if _f >= bridge_fmin * (1.0 - 1.0e-6) and _m > 0.0]",
        "_spur = len(_tb['NUME_ORDRE']) - len(_good)",
        "if _spur:",
        "    print('BRIDGE_VIBRO_VALS', _spur)",
        "if len(_good) < bridge_n:",
        "    print('BRIDGE_VIBRO_TEKORT', len(_good), bridge_n)",
        "if not _good:",
        "    raise ValueError('BRIDGE_VIBRO: geen bruikbare modes tussen %g en "
        "%g Hz' % (bridge_fmin, _hi))",
        "res = EXTR_MODE(FILTRE_MODE=_F(MODE=res_band,",
        "                               NUME_ORDRE=tuple(_good[:bridge_n])))",
        "res = NORM_MODE(reuse=res, MODE=res, NORME='MASS_GENE')",
    ]
    return "\n".join(lines) + "\n"


def _export_block(work_dir, model_data):
    """BRIDGE_MODE lines (only the frequency: the effective mass of
    Code-Aster has no meaning for U_P_PHI modes, adlv100a: 4.6e-20
    for the piston mode) and aster_results_export with displacements
    (structure) and the pressure (fluid, component PRES of DEPL)."""
    import bridge_to_aster as bta
    scripts = os.path.dirname(os.path.abspath(__file__))
    return ("# Resultaten in Mecway's eigen formaat (result_route 'liml')\n"
            "_tf = RECU_TABLE(CO=res, NOM_PARA=('FREQ',)).EXTR_TABLE()"
            ".values()\n"
            "for _i, _f in zip(_tf['NUME_ORDRE'], _tf['FREQ']):\n"
            "    print('BRIDGE_MODE {{0}} FREQ={{1!r}}'.format(_i, _f))\n"
            "import sys\n"
            "sys.path.insert(0, {0})\n"
            "import aster_results_export\n"
            "aster_results_export.export_results(\n"
            "    res, {1}, {2},\n"
            "    fields=['displacements', 'pressure'], precision='double')\n"
            ).format(bta._py_str(scripts),
                     bta._py_str(bta.results_file(work_dir)),
                     bta._py_str(model_data.get("liml_path", "")))


def build_vibroacoustic_modes(work_dir, model_data, msh_path, resu_name,
                              analysis):
    """
    Generate the .comm and .export for the coupled modes. Returns the path
    to the .export, or None on an error (ERROR logged).
    """
    import bridge_to_aster as bta
    log("--- Generating Aster Files (CALC_MODES vibro-akoestisch) ---")
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr("ERROR: De resultaatroute 'tabel' werkt niet voor modale "
               "analyses. Kies 'liml' (pagina Algemeen).",
               "ERROR: The result route 'tabel' does not work for modal "
               "analyses. Choose 'liml' (General page)."))
        return None
    vib = model_data.get("vibro")
    if not vib:
        log(tr("ERROR: Vibro-akoestiek: het model heeft geen fluidum. Geef "
               "het lucht- of vloeistofvolume een eigen onderdeel met een "
               "materiaal met 'Speed of sound' en een dichtheid (zonder "
               "Young's modulus), of een naam die begint met LUCHT_ of "
               "FLUID_.",
               "ERROR: Vibroacoustics: the model has no fluid. Give the air "
               "or liquid volume its own part with a material with 'Speed "
               "of sound' and a density (without Young's modulus), or a "
               "name starting with LUCHT_ or FLUID_."))
        return None
    bad = list(vib["bad"])
    bad += [tr("fluid pressure op '{0}' is {1}; in de modes kan alleen 0 "
               "(drukknoop)",
               "fluid pressure on '{0}' is {1}; in the modes only 0 is "
               "possible (pressure node)").format(s, t)
            for s, t in vib["pressure_src"]]
    if vib["impedances"]:
        # Complex coupled modes: not translated (KNOWN_BUGS 59; the
        # cavity modes with impedance are, aster_acoustic_complex.py).
        bad.append(tr("impedantie op {0} wordt in de modes niet vertaald "
                      "(complexe modes); onderdruk hem (Suppress) voor een "
                      "harde wand",
                      "impedance on {0} is not translated in the modes "
                      "(complex modes); suppress it for a hard "
                      "wall").format(", ".join(
                          "'%s'" % s for s in vib["impedances"])))
    renames = model_data.get("group_renames", {})
    fluid_ca = OrderedDict((renames.get(es, es), mat)
                           for es, mat in vib["fluid_elsets"].items())
    bad += _check_fluid(model_data, vib, fluid_ca)
    if bad:
        log(tr("ERROR: Vibro-akoestiek: {0}.",
               "ERROR: Vibroacoustics: {0}.").format("; ".join(bad)))
        return None
    if vib["ignored"]:
        log("INFO: Vibro-acoustics: selections {0} (source, absorbing, "
            "microphone, incident wave) are not used in the modes; "
            "absorbing faces are rigid walls. For the response per "
            "frequency: analysis 'vibroacoustic_harm_3d'.".format(
                ", ".join(vib["ignored"])))
    if model_data.get("analysis_type") not in ("V30", "A30"):
        log("INFO: Vibro-acoustics on a Mecway model of type '{0}' "
            "(expected: Frequency, V30).".format(
                model_data.get("analysis_type")))
    if not bta._check_linear(model_data, tr("een modale analyse",
                                            "a modal analysis")):
        return None
    bta._collapse_histories(model_data, "CALC_MODES")
    fluid_mats = set(m for m, p in vib["materials"].items()
                     if p.get("c") and not p.get("E"))
    fluid_mats |= set(fluid_ca.values())
    md_s = _structure_view(model_data, fluid_ca, fluid_mats)
    structure = bool(bta._model_groups(md_s))
    interfaces = vib.get("interfaces", OrderedDict())
    if structure and not interfaces:
        log(tr("WARNING: Vibro-akoestiek: geen koppelvlak gevonden; "
               "fluidum en constructie delen geen vlakken (dezelfde knopen). "
               "De modes zijn dan ongekoppeld. Mesh ze als een doorlopend "
               "mesh (gedeelde knopen op het grensvlak).",
               "WARNING: Vibroacoustics: no coupling face found; fluid and "
               "structure share no faces (the same nodes). The modes are "
               "then uncoupled. Mesh them as one continuous mesh (shared "
               "nodes on the interface)."))
    if not structure:
        log("INFO: Vibro-acoustics: fluid only (no structure); the "
            "density is used, also at an interface between media.")

    # --- mesh: groups, orientation of the coupling faces ---
    defigroup_block = bta._build_defigroup_block(md_s)
    if interfaces:
        defigroup_block += (
            "\n# Koppelvlakken: normaal uit het fluidum (ORIE_PEAU met "
            "GROUP_MA_INTERNE,\n# zoals adlv100b/adls102a)\n"
            "mesh = MODI_MAILLAGE(\n    reuse=mesh,\n    MAILLAGE=mesh,\n"
            "    ORIE_PEAU=(\n{0}    ),\n)\n").format("".join(
                "        _F(GROUP_MA_PEAU='{0}', GROUP_MA_INTERNE='{1}'),\n"
                .format(g, renames.get(es, es))
                for g, es in interfaces.items()))

    # --- model ---
    fluid_lines = "".join(
        "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
        "MODELISATION='3D_FLUIDE', FORMULATION='U_P_PHI'),\n".format(es)
        for es in fluid_ca)
    fluid_lines += "".join(
        "        _F(GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
        "MODELISATION='FLUI_STRU', FORMULATION='U_P_PHI'),\n".format(g)
        for g in interfaces)
    if structure:
        model_block = _insert_affe(bta._build_model_block(md_s),
                                   "model = AFFE_MODELE(", fluid_lines)
    else:
        model_block = ("model = AFFE_MODELE(\n    MAILLAGE=mesh,\n"
                       "    AFFE=(\n{0}    ),\n)\n").format(fluid_lines)
    cara_ref = "    CARA_ELEM=cara,\n" if bta._has_cara(md_s) else ""
    cara_elem_block = bta._build_cara_elem_block(md_s) if structure else \
        "#-- no structure --\n"

    # --- materials ---
    names = OrderedDict()
    mat_lines = []
    for k, mat in enumerate(sorted(set(fluid_ca.values()),
                                   key=list(vib["materials"]).index)):
        props = vib["materials"][mat]
        names[mat] = "MAF{0}".format(k + 1)
        mat_lines.append("{0}{1} = DEFI_MATERIAU(FLUIDE=_F(RHO={2}, "
                         "CELE_R={3}))".format(bta._mat_comment(mat),
                                               names[mat], _r(props["rho"]),
                                               _r(props["c"])))
    materials_block = ((bta._build_materials_block(md_s, analysis)
                        if structure else "") +
                       "\n".join(mat_lines) + "\n")
    flu_affe = "".join("        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        es, names[m]) for es, m in fluid_ca.items())
    flu_affe += "".join("        _F(GROUP_MA='{0}', MATER={1}),\n".format(
        g, names[vib["fluid_elsets"][es]]) for g, es in interfaces.items())
    if structure:
        fieldmat_block = _insert_affe(bta._build_fieldmat_block(md_s),
                                      "fieldmat = AFFE_MATERIAU(", flu_affe)
    else:
        fieldmat_block = ("fieldmat = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n"
                          "    MODELE=model,\n    AFFE=(\n{0}    ),\n)\n"
                          ).format(flu_affe)
    if model_block is None or fieldmat_block is None:
        log(tr("ERROR: Vibro-akoestiek: AFFE_MODELE/AFFE_MATERIAU niet "
               "herkend (interne fout).",
               "ERROR: Vibroacoustics: AFFE_MODELE/AFFE_MATERIAU not "
               "recognised (internal error)."))
        return None

    # --- boundary conditions: structure (without loads) and p = 0 ---
    charges = bta._build_charges(md_s) if structure else []
    dropped = [c for c in charges if bta._is_load_charge(c)]
    if dropped:
        kws = []
        for c in dropped:
            for kw in c[1]:
                if kw not in kws:
                    kws.append(kw)
        log(tr("WARNING: Vibro-akoestiek: belastingen ({0}) tellen niet mee "
               "in de modes (geen voorspanning).",
               "WARNING: Vibroacoustics: loads ({0}) do not count in the "
               "modes (no prestress).").format(", ".join(kws)))
        model_data.setdefault("skipped_loads", []).append(
            tr("belastingen in de vibro-akoestische modes ({0})",
               "loads in the vibroacoustic modes ({0})").format(
                   ", ".join(kws)))
        charges = [c for c in charges if not bta._is_load_charge(c)]
    extra = model_data.get("aster_custom", {}).get("excit", [])
    if charges or extra:
        loads_block, _excit = bta._render_charges(charges, md_s)
    else:
        loads_block = bta._custom_code(md_s, "code")
    charge_names = ["load_{0}".format(k + 1) for k in range(len(charges))]
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
    if entries:
        loads_block += ("\n# Drukknopen p = 0 (OPEN_-selecties, fluid "
                        "pressure 0): PRES en PHI\n"
                        "bc_flu = AFFE_CHAR_MECA(\n    MODELE=model,\n"
                        "    DDL_IMPO=(\n{0}    ),\n)\n").format(
                            "".join(entries))
        charge_names.append("bc_flu")
    charge_names += [n for n in extra if n not in charge_names]
    if not charge_names:
        log("INFO: Vibro-acoustics: no supports and no pressure nodes; "
            "modes at 0 Hz (rigid body motion, constant pressure) fall below "
            "the lower limit vibro_freq_min.")
    assemblage_block = (
        "ASSEMBLAGE(\n"
        "    MODELE=model,\n"
        "    CHAM_MATER=fieldmat,\n"
        "{cara}{charge}"
        "    NUME_DDL=CO('numedd'),\n"
        "    MATR_ASSE=(\n"
        "        _F(MATRICE=CO('rigidite'), OPTION='RIGI_MECA'),\n"
        "        _F(MATRICE=CO('masse'), OPTION='MASS_MECA'),\n"
        "    ),\n"
        ")\n").format(cara=cara_ref, charge=(
            "    CHARGE=({0},),\n".format(", ".join(charge_names))
            if charge_names else ""))
    n = bta._mode_count(model_data, analysis)
    calc_modes_block = _mode_search_block(model_data, analysis, n)
    export_block = (bta._custom_code(model_data, "post") +
                    _export_block(work_dir, model_data))
    if CONFIG_BRIDGE.get("med_export", False):
        impr_resu_block = ("IMPR_RESU(FORMAT='MED', UNITE=80, "
                           "RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL',)))\n")
    else:
        impr_resu_block = "#-- no MED export (setting med_export off) --\n"

    comm_path = os.path.join(work_dir, run_name(".comm"))
    try:
        template = bta._read_template(analysis["template"])
        bta._write_comm(comm_path, template.format(
            defigroup_block=defigroup_block,
            model_block=model_block,
            cara_elem_block=cara_elem_block,
            materials_block=materials_block,
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
                "P memory_limit {0}".format(analysis.get("memory_limit",
                                                         2048)),
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
        log(tr("ERROR: Genereren vibro-akoestische solver-bestanden mislukt: "
               "{0}",
               "ERROR: Generating the vibroacoustic solver files failed: "
               "{0}").format(str(e)))
    return None


def report_lines(work_dir):
    """Lines for the status box after the run (MecwayAsterBridgeMain): the
    band of the mode search and a shortage of modes (from the .mess)."""
    import re
    path = os.path.join(work_dir, run_name(".mess"))
    out = []
    try:
        f = open(path, "r")
        try:
            text = f.read()
        finally:
            f.close()
    except (IOError, OSError):
        return out
    m = re.search(r"BRIDGE_VIBRO_TEKORT\s+(\d+)\s+(\d+)", text)
    if m:
        out.append(tr(u"WARNING: Vibro-akoestiek: {0} van de {1} gevraagde "
                      u"modes gevonden. Controleer het model op "
                      u"mechanismen (te weinig opleggingen, een schaal met "
                      u"alleen een rotatie vast) of vraag minder modes.",
                      u"WARNING: Vibroacoustics: {0} of the {1} requested "
                      u"modes found. Check the model for mechanisms (too "
                      u"few supports, a shell with only one rotation fixed) "
                      u"or ask for fewer modes.").format(m.group(1),
                                                         m.group(2)))
    m = re.search(r"BRIDGE_VIBRO_VALS\s+(\d+)", text)
    if m:
        out.append(tr(u"Vibro-akoestiek: {0} valse mode(s) (onder de "
                      u"ondergrens of met massa <= 0) weggelaten.",
                      u"Vibroacoustics: {0} spurious mode(s) (below the "
                      u"lower bound or with mass <= 0) left out.").format(
                          m.group(1)))
    m = re.search(r"BRIDGE_VIBRO_BAND\s+(\S+)\s+(\S+)\s+(\d+)", text)
    if m:
        out.append(tr(u"Vibro-akoestiek: modes gezocht tussen {0} en {1} Hz "
                      u"({2} in die band). Velden in Mecway per mode: displ "
                      u"(constructie) en pressure (fluidum).",
                      u"Vibroacoustics: modes searched between {0} and {1} "
                      u"Hz ({2} in that band). Fields in Mecway per mode: "
                      u"displ (structure) and pressure (fluid).").format(
                          "%.4g" % float(m.group(1)),
                          "%.4g" % float(m.group(2)), m.group(3)))
    for line in out:
        log(line if line.startswith("WARNING") else u"INFO: " + line)
    return out
