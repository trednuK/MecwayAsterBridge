# Changelog

## Unreleased (develop)

- **No more "click OK when Code-Aster has finished"**: the bridge now waits by itself. A
  modal status window shows the elapsed time, the current step (time, attempt, iteration or
  solver phase) and the messages so far, with a *Stop...* button that ends only this run's
  Code-Aster processes; when Code-Aster has finished the window closes and the results are
  loaded. The end is detected from an end marker with the exit code of `run_aster`
  (`Scripts/aster_launch.bat`), else from `DIAGNOSTIC JOB` in the `.mess`; a non-zero exit
  code, a closed Code-Aster window and a stop are reported in the status box and the
  convergence window. New setting *Waiting for Code-Aster* (`wait_for_aster`, General):
  `auto` (default) or `confirm` (the old OK dialog). Test `tests/test_bridge_wait.py`.
- **`FACTOR_57` without a mechanism** (slender volume models in bending, MUMPS error estimate
  just above `RESI_RELA` 1e-6): the setting *Solver accuracy (RESI_RELA)* (`lin_solver_resi`,
  default 1e-6 as Code-Aster) is now also on the pages Modal (static step for the prestress,
  also cyclic), Buckling (static step) and Nonlinear static (static step of the imperfection).
  The error message reads the computed error from `study.mess`: below 1e-3 it names the page
  and the value to enter, above it the mechanism advice. Verification BU-37 (hex20 L frame).
  Was KNOWN_BUGS 114.
- **Fix: results of a model with configurations** (e.g. load cases G, Q, ULS): Mecway 34 could
  not open the `.liml` after the bridge wrote the results into it ("Error opening file"). The
  model copy in `<solution configuration="X">` is now written as Mecway writes it: without the
  `<configuration>` definitions and `<suppressed configuration>` children, with
  `suppressed="true"` on the items suppressed in X. Test `tests/test_results_configuration.py`.
- **Developer text in English**: code comments, docstrings, comments in the `.comm`
  templates (and the generated `study.comm`), INFO/SUCCESS log lines, `AGENTS.md`,
  `KNOWN_BUGS.md` and `STAPPENPLAN.md`. The user interface, messages, WARNING/ERROR lines,
  the convergence window and the user documentation (`docs/` Dutch, `docs/en/` English)
  stay bilingual.
- **Quadratic beams (line3)** are now translated (were not modelled): each element is
  split at its midside node into two SEG2 beam cells; results on all three nodes.
  **Flexible joint on beam** is translated: an own node per beam end, coupled with
  `LIAISON_DDL` in Mecway's local axes. Verification LS-50 and LS-51 (equal to
  Mecway); limits KNOWN_BUGS 106–107.
- **Element offset** (Loads & Constraints) for shells and beams is now translated instead
  of skipped: linear shells (DKT/DST) with `EXCENTREMENT`, quadratic shells (COQUE_3D) and
  beams on their own nodes with rigid arms to the Mecway nodes. Results stay on the Mecway
  nodes (reactions include the arm). Verification LS-60–63 (incl. Mecway's CompositeBeam
  sample).
- **Bonded (Tie) contact between shells** now works: a shell face or edge glued onto a
  shell face no longer stops with a singular matrix (`FACTOR_11`); the drilling rotation is
  left out of `LIAISON_MAIL`. Example `TestFiles/Voorbeelden/Voorbeeld_T.liml`, verification
  LS-07a–e, docs §3.10 of the contact settings. Also with a skewed or curved master and
  with a quadratic shell (tri6/quad8) as master: the bridge then writes the tie itself as
  `LIAISON_DDL` (skewed/curved: MUMPS `NPREC` −1 for that run, with a warning).
  Verification LS-07f–k (KNOWN_BUGS 90–92 solved).
- **Formulas in x, y, z for mechanical loads** (also combined with t) are now translated
  instead of skipped (KNOWN_BUGS 45): pressure, traction, force, line pressure and
  prescribed displacement/rotation become a `FORMULE` of X, Y, Z (INST) in
  `AFFE_CHAR_MECA_F`, e.g. a hydrostatic-like pressure `3*y^2`. Pressure and traction match
  Mecway 34 exactly; force, line pressure and displacement with x, y, z are not applied by
  Mecway 34 itself (warning). Verification LS-40–44, NL-40; limits KNOWN_BUGS 104.
- **New overview** of which Mecway functionality the bridge does and does not translate
  (`docs/en/Mecway_features.md`, Dutch `docs/Mecway_functionaliteit.md`), also on the
  Documentation page of the start screen.
- **Bonded contact in thermal analyses** (T30/T31) is now translated instead of silently
  dropped (KNOWN_BUGS 88): *Tie* / *Constraint equations* → `AFFE_CHAR_THER`
  `LIAISON_MAIL`, *Elastic* → thermal resistance `ECHANGE_PAROI` with Mecway's *Thermal
  conductance per unit area* (conforming solid faces; otherwise ideally bonded with a
  warning). Models with solids and shells together: ERROR (Code-Aster cannot couple
  them). Verification TH-04a–d.
- **Node temperature** (`temperature3`, also after *Transfer temperatures from solution*) now
  gives thermal strain in static, nonlinear static, modal and buckling analyses, like
  *Temperature*; nodes the bridge adds (`LINE_QUAD`, `COQUE_3D` centre node) get the
  interpolated temperature. Verification LS-08a–d. KNOWN_BUGS 89 fixed; 95 recorded
  (Mecway expands shells less).
- **Temperature in time** (`temperature2` with a time table or a formula in t) now gives
  thermal strain in nonlinear static (L30) and nonlinear dynamic response (D31): an
  `EVOL_THER` from the reference temperature, following the table like Mecway (with CCX).
  A constant temperature acts from the first step (Quasi-static, D31) or ramps up (L30
  without Quasi-static, up to t = 1 s like Mecway). Temperatures now give thermal stress in `DYNA_NON_LINE`
  (KNOWN_BUGS 94 fixed); D30 ignores them like Mecway. Verification NL-70..75, DY-70..73.
- **Several heat sources with a formula or time table** (*Internal heat generation*, heat
  flux on shell faces, `#ASTER-LASBRON`) now each give their own heat: Code-Aster 17.4
  computed two such loads both with the function of the first. All function sources are
  now in one load, overlapping sources summed per part of the mesh; a weld source next to
  a formula/table source no longer gives a warning (KNOWN_BUGS 70 solved). Verification
  TH-40–42.
- **Version check** (warning only): the log shows the Mecway version (from the `.liml`) and the
  Code-Aster version (launcher path, then the `.mess`); an untested version gives a WARNING. New page
  *After an update of Mecway or Code-Aster* (`docs/en/After_an_update.md`).
- README: Mecway 34, acknowledgements. Verification: 394 test cases, 2152 checks (2145 OK, 7 known, 0 unexpected).

## V2026.1 – first public release

First public version of the MecwayAsterBridge: a Mecway 33 model (`.liml`) is solved with
Code-Aster 17.4 for Windows and the results come back into Mecway. Standalone: only the
Python of Mecway and of Code-Aster, no `pip` packages.

- **Start screen** in English and Dutch, with settings per analysis, tooltips, a
  convergence and messages window, and the documentation built in.
- **Analyses**: linear and nonlinear static (contact, plasticity, large displacements,
  element failure), implicit and explicit nonlinear dynamics, mode superposition and
  harmonic response, thermal (steady state and transient) and thermo-mechanical, modal
  (also prestressed), linear and nonlinear buckling (CRIT_STAB, imperfection).
- **Acoustics**: cavity modes and harmonic pressure field (sources, absorbing boundaries,
  microphones); vibroacoustics, coupled modes and harmonic response.
- **Welding and metallurgy**: moving heat source along a weld bead, residual stress and
  distortion, filler material that is born, phases and hardness.
- **Fracture mechanics**: K and G along a meshed crack, and XFEM cracks without a mesh.
- **Fatigue**: damage and life per node (Wöhler curve, rainflow, Miner, critical-plane
  criteria, Manson-Coffin).
- **Cyclic symmetry** for modal analysis of a sector.
- **Response spectrum** (earthquake, shock) on a frequency model.
- **Error estimator** per element (linear static) and **adaptive refinement** of the
  mesh in Mecway.
- **`#ASTER` lines** in Mecway's *Custom model definition* for Code-Aster input that
  Mecway has no field for.
- **Verification set**: 272 test cases with 1629 checks against analytical solutions
  and benchmarks, plus 19 official Code-Aster validation tests
  ([`docs/en/Verification.md`](docs/en/Verification.md)).
