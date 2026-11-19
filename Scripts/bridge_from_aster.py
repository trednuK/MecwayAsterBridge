# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_from_aster.py
# Responsibility: the registry of result fields (RESULT_FIELD_SPECS) and the
# comparison of Code-Aster's results with Mecway's own solve (setting
# mecway_solve_first): the largest difference per variable in the log and
# <model>_<run_id>_vergelijking.csv. The results themselves reach Mecway
# through the .liml (aster_results_export.py, bridge_results_liml.py); the
# table route that read a .resu into Mecway's solution was removed in
# V2026.15.
#
# Architecture:
#   - RESULT_FIELD_SPECS is the central registry of all supported
#     result fields. Per analysis CONFIG_BRIDGE["analyses"][...]
#     ["fields"] selects a subset of it (also the list on the start screen).
#     Adding a field: entry here + FIELD_TABLE in aster_results_export.py.
#
# Compatible with IronPython 2.7.9.

import os
from collections import OrderedDict

from bridge_utils import log, tr, run_name


# ==========================================
# RESULT FIELDS REGISTRY
#
# Mapping per result group (the names of CONFIG_BRIDGE["analyses"][...]
# ["fields"]) to {Code-Aster component name: Mecway variable name}; an
# empty map: the variables are computed in the job (aster_results_export).
# ==========================================
RESULT_FIELD_SPECS = OrderedDict([
    # Rotations (DRX/DRY/DRZ, radians) only exist on nodes of beams,
    # shells and DIS_TR elements; on volume nodes the .resu has '-' and
    # the value stays None (as in Mecway's own solution).
    ('displacements', OrderedDict([
        ('DX', 'displx'),
        ('DY', 'disply'),
        ('DZ', 'displz'),
        ('DRX', 'rotx'),
        ('DRY', 'roty'),
        ('DRZ', 'rotz'),
    ])),
    # stresses / vonmises: only 3D elements (SIGM_NOEU / SIEQ_NOEU,
    # global coordinate system). Shells and beams: aster_results_export.
    ('stresses', OrderedDict([
        ('SIXX', 'stressxx'),
        ('SIYY', 'stressyy'),
        ('SIZZ', 'stresszz'),
        ('SIXY', 'stressxy'),
        ('SIYZ', 'stressyz'),
        ('SIXZ', 'stresszx'),
    ])),
    ('vonmises', OrderedDict([
        ('VMIS', 'vonmises'),
    ])),
    # velocities: only DYNA_NON_LINE (VITE); names as Mecway stores them for
    # OpenRadioss results (velx/vely/velz, velmag).
    ('velocities', OrderedDict([
        ('DX', 'velx'),
        ('DY', 'vely'),
        ('DZ', 'velz'),
    ])),
    # accelerations: ACCE (dynamics; response spectrum: maximum absolute
    # acceleration, bridge_spectrum.py). Mecway's names accx/y/z (Mecway
    # 34's own D30 solution).
    ('accelerations', OrderedDict([
        ('DX', 'accx'),
        ('DY', 'accy'),
        ('DZ', 'accz'),
    ])),
    # REAC_NODA: DRX/DRY/DRZ are reaction moments (only on nodes with
    # rotational degrees of freedom). Mecway names as in Mecway's own
    # solution (reactionmomx/y/z, reactionmommag).
    ('reactions', OrderedDict([
        ('DX', 'reactionforcex'),
        ('DY', 'reactionforcey'),
        ('DZ', 'reactionforcez'),
        ('DRX', 'reactionmomx'),
        ('DRY', 'reactionmomy'),
        ('DRZ', 'reactionmomz'),
    ])),
    # ----------------------------------------------------------
    # PLASTIC STRAIN  (STAT_NON_LINE with VMIS_ISOT_TRAC)
    #
    # plastic_strain  (EPSP_NOEU) gives the plastic strain TENSOR
    # in the same components as the stress tensor:
    #   EPXX, EPYY, EPZZ, EPXY, EPYZ, EPXZ.
    #
    # plastic_strain_eq (VARI_NOEU)  gives the accumulated
    # equivalent plastic strain as internal variable V1
    # (for isotropic hardening). INTITULE in the .resu: 'plastic_strain_e'
    # (16 characters); the parser maps it back via _intitule_lookup().
    #
    # Mecway names: after a CCX solve with *EL FILE PEEQ, Mecway 33
    # itself creates 'equivalentplasticstrain' (field "equivalent plastic
    # strain"); V1 uses the same name. Mecway does not create a plastic
    # strain tensor (not with PE either); 'plasticstrainxx' etc. are the
    # bridge's own names.
    # ----------------------------------------------------------
    ('plastic_strain', OrderedDict([
        ('EPXX', 'plasticstrainxx'),
        ('EPYY', 'plasticstrainyy'),
        ('EPZZ', 'plasticstrainzz'),
        ('EPXY', 'plasticstrainxy'),
        ('EPYZ', 'plasticstrainyz'),
        ('EPXZ', 'plasticstrainzx'),
    ])),
    ('plastic_strain_eq', OrderedDict([
        ('V1', 'equivalentplasticstrain'),
    ])),
    # Thermal (analysis ther_3d, bridge_thermal.py): aster_results_export.py
    # FIELD_TABLE (TEMP in Celsius becomes Kelvin there). Here for the field choice on the start screen.
    ('temperature', OrderedDict([
        ('TEMP', 'temperature'),
    ])),
    ('heat_flux', OrderedDict([
        ('FLUX', 'heatfluxx'),
        ('FLUY', 'heatfluxy'),
        ('FLUZ', 'heatfluxz'),
    ])),
    # Metallurgy (#ASTER-METALLURGIE, bridge_metallurgy.py; CALC_META):
    # FIELD_TABLE group "metallurgy"; with
    # #ASTER-METALLURGIE always included (bridge_metallurgy.fields).
    ('metallurgy', OrderedDict([
        ('V1', 'ferrite'),
        ('V2', 'pearlite'),
        ('V3', 'bainite'),
        ('V4', 'martensite'),
        ('V5', 'austenite'),
        ('HV', 'hardness'),
    ])),
    # Error estimator (errorestimate, errorestimaterel): no entry here; the
    # field is FIELD_TABLE group "error_estimate" of aster_results_export
    # and depends on the setting
    # error_estimator, not on "fields" (docs/Foutschatter.md).
    # ----------------------------------------------------------
    # EXTRA FIELDS (only when selected; aster_results_export
    # OPT_IN_GROUPS, bridge_to_aster._optional_fields). Mecway names
    # checked headless in Mecway 34 (see aster_results_export FIELD_TABLE
    # and _plan_derived).
    # strain: total strain of volume elements (EPSI_NOEU; linear, Mecway
    # lstrain*). Nonlinear with large displacements: Green-Lagrange
    # (EPSG_NOEU). Shells: lstrain<ij>u/m/b.
    ('strain', OrderedDict([
        ('EPXX', 'lstrainxx'),
        ('EPYY', 'lstrainyy'),
        ('EPZZ', 'lstrainzz'),
        ('EPXY', 'lstrainxy'),
        ('EPYZ', 'lstrainyz'),
        ('EPXZ', 'lstrainzx'),
    ])),
    # beam_forces: section forces of beams (EFGE_NOEU, local axes).
    ('beam_forces', OrderedDict([
        ('N', 'tensileforce'),
        ('VY', 'sheary'),
        ('VZ', 'shearz'),
        ('MT', 'torsion'),
        ('MFY', 'bendingmomv'),
        ('MFZ', 'bendingmomw'),
    ])),
    # Computed in the job (aster_results_export):
    #   shell_stresses: stress<ij>u1/m1/b1 (global tensor top/middle/
    #                   bottom);
    #   shell_forces:   forceperlengthu/v/uv, momentu/v/uv, shearuw/vw;
    #   safety_factor:  factorofsafety (von Mises failure criterion);
    #   contact:        contactpressure (-LAGS_C) and contactstate.
    ('shell_stresses', OrderedDict()),
    ('shell_forces', OrderedDict()),
    ('safety_factor', OrderedDict()),
    # Principal stresses and Tresca / principal strains of volume elements
    # (S34) and of shells per surface (S34b): computed in the job from
    # SIGM_ELNO / EPSI_ELNO (EPSG_ELNO)
    # (aster_results_export._principal_vars, _shell_principal_vars).
    ('principal_stresses', OrderedDict()),
    ('principal_strains', OrderedDict()),
    ('contact', OrderedDict([
        ('LAGS_C', 'contactpressure'),
    ])),
])


def empty_solution_reason(solution, solved_now=False):
    """
    Reason text when Mecway has no solution of the model: solution is
    None or has no nodes. Mecway's own solve raises no exception when it
    fails (e.g. contact on shell edges, a component without a material);
    it then leaves a solution with 0 nodes. "" when the solution has
    nodes, and also when its nodes cannot be read. solved_now: mw.solve()
    just ran in this run.
    """
    if solution is not None:
        try:
            for _nid in solution.all_nodes():
                return ""       # one node is enough
        except Exception:
            return ""
    if solved_now:
        return tr("Er is geen Mecway-solution van dit model: de "
                  "Mecway-solve liep zonder fout, maar liet een solution "
                  "zonder knopen achter.",
                  "There is no Mecway solution of this model: the Mecway "
                  "solve ran without an error, but left a solution "
                  "without nodes.")
    return tr("Er is geen Mecway-solution van dit model: de "
              "Mecway-solve is mislukt of niet uitgevoerd.",
              "There is no Mecway solution of this model: the Mecway "
              "solve failed or was not run.")


# ==========================================
# COMPARISON MECWAY <-> CODE-ASTER
# ==========================================
def _compare_modes_with_mecway(solution, modes, nearest=False):
    """
    Compare the frequencies/buckling load factors of Code-Aster (modes:
    bridge_results_liml.read_modes) with those of the Mecway solve
    (solution.modes(), solution.frequency(m) / buckling_factor(m),
    API_reference Mecway). Only the values: the shapes have an
    arbitrary sign and are not unique for multiple modes. Logs both
    values and the difference per mode.
    nearest: per Code-Aster mode the Mecway mode with the nearest
    frequency instead of the same number (complex acoustic modes: Mecway
    arbitrarily omits 0 Hz modes, manual v33 sec. 6.9.2, so the numbers
    do not match; modes with ~0 Hz are then not compared).
    """
    if nearest:
        _compare_nearest(solution, modes)
        return
    try:
        mw_modes = list(solution.modes() or [])
    except Exception as e:
        log(tr("WARNING: Mecway-modes niet leesbaar: {0}",
               "WARNING: Mecway modes not readable: {0}").format(e))
        return
    if not mw_modes:
        log(tr("WARNING: De Mecway-solution heeft geen modes; geen "
               "vergelijking.",
               "WARNING: The Mecway solution has no modes; no "
               "comparison."))
        return
    for mid, kind, value in modes:
        if mid not in mw_modes:
            continue
        try:
            mw_value = (solution.buckling_factor(mid)
                        if kind == "bucklingfactor"
                        else solution.frequency(mid))
        except Exception:
            mw_value = None
        if mw_value is None:
            continue
        rel = (value - mw_value) / abs(mw_value) if mw_value else 0.0
        # %-formatting: format() gives a comma in IronPython (locale)
        log("INFO: Comparison mode {0}: Mecway {1}, Code-Aster {2} "
            "({3}%).".format(mid, "%.6g" % mw_value, "%.6g" % value,
                             "%+.2f" % (100.0 * rel)))


def _compare_nearest(solution, modes):
    """See _compare_modes_with_mecway (nearest=True)."""
    try:
        mw = [(m, solution.frequency(m)) for m in (solution.modes() or [])]
    except Exception as e:
        log(tr("WARNING: Mecway-modes niet leesbaar: {0}",
               "WARNING: Mecway modes not readable: {0}").format(e))
        return
    mw = [(m, f) for m, f in mw if f is not None and abs(f) > 1.0e-3]
    if not mw:
        log(tr("WARNING: De Mecway-solution heeft geen modes; geen "
               "vergelijking.",
               "WARNING: The Mecway solution has no modes; no "
               "comparison."))
        return
    for mid, _kind, value in modes:
        if abs(value) <= 1.0e-3:
            continue
        m, f = min(mw, key=lambda t: abs(t[1] - value))
        log("INFO: Comparison mode {0}: Mecway mode {1} {2}, Code-Aster "
            "{3} ({4}%).".format(mid, m, "%.6g" % f, "%.6g" % value,
                                 "%+.2f" % (100.0 * (value - f) / abs(f))))


def _compare_with_mecway(solution, arrays, names, work_dir):
    """
    Compare Code-Aster values with those of the Mecway solve, before they
    are overwritten. Only meaningful directly after mw.solve() ("Eerst
    Mecway-solve ter controle"): then the solution contains Mecway's own
    result on the same mesh.

    Writes <model>_<run_id>_vergelijking.csv (node, variable, mecway,
    aster) in the work folder and logs the largest difference per variable.
    """
    rows = []
    # With time steps (transient, dynamics) node_value() without
    # time_step gives nothing (API_reference: "Time step number if there are time
    # steps in the solution"); then compare the last time step of Mecway
    # with the last one of Code-Aster.
    step = None
    try:
        steps = list(solution.time_steps() or [])
        if steps:
            step = steps[-1]
            log("INFO: Comparison at the last time step of Mecway (t = "
                "{0} s).".format(solution.time(step)))
    except Exception:
        step = None
    for name in names:
        aster = arrays.get(name)
        if aster is None:
            continue
        max_m = max_a = max_d = 0.0
        node_d = None
        for i, a in enumerate(aster):
            if a is None:
                continue
            try:
                m = solution.node_value(name, i + 1, step)
            except Exception:
                m = None
            if m is None:
                continue
            rows.append("{0},{1},{2!r},{3!r}".format(i + 1, name, m, a))
            max_m = max(max_m, abs(m))
            max_a = max(max_a, abs(a))
            if abs(m - a) > max_d:
                max_d, node_d = abs(m - a), i + 1
        if node_d is None and max_m == 0.0:
            continue
        rel = max_d / max_m if max_m > 0.0 else 0.0
        log("INFO: Comparison {0}: max|Mecway|={1}, max|Code-Aster|="
            "{2}, max difference={3} ({4:.1%} of max|Mecway|) at node "
            "{5}.".format(name, max_m, max_a, max_d, rel, node_d))
    if rows:
        path = os.path.join(work_dir, run_name("_vergelijking.csv"))
        try:
            f = open(path, "w")
            try:
                f.write("knoop,variabele,mecway,aster\n")
                f.write("\n".join(rows) + "\n")
            finally:
                f.close()
        except Exception as e:
            log(tr("WARNING: {0} niet geschreven: {1}",
                   "WARNING: {0} not written: {1}").format(path, str(e)))
