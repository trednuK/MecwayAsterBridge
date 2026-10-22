# Changelog

## V2026.4 – 22 October 2026

Quadratic trusses, hyperelastic materials, the elastic modulus from the plastic curve as
in Mecway, buttons in the convergence window, a work folder next to the model and better
flexible joints, most of them from GitHub issues (trednuK/MecwayAsterBridge). Tested in
Mecway 34 with Code-Aster 17.4; verification 428 test cases, 2301 checks (2295 OK, 6 known
limitations, 0 unexpected).

- **Line3 trusses** (issue #6): quadratic trusses and cables (line3, `truss="true"`) are
  now translated instead of stopping Code-Aster with `MODELE1_6`. Each element becomes two
  `BARRE`/`CABLE` cells; the midside node is tied to the end nodes. Verification MO-08
  (NAFEMS Challenge Problem 5: 451.1 / 1049.9 Hz, equal to the reference) and LS-54a (exact).
  An element set that cannot be translated as a whole now stops the bridge before
  Code-Aster with an error, instead of failing in Code-Aster.
- **Plastic curve** (issue #2): with a hardening curve in total strain, E is the slope of
  the first segment, as Mecway does, with a warning that gives both values. If the first
  slope still differs from E by more than 1 %, the bridge stops with an error before
  Code-Aster (before: a warning at 5 % and `MATERIAL1_5` in Code-Aster). Verification NL-04,
  NL-04b.
- **Hyperelastic materials** (issue #5): Mecway's *Neo Hooke* and *Mooney-Rivlin* become
  `ELAS_HYPER` (C10, C01, K = 2/D1) with `GREEN_LAGRANGE` in nonlinear static and dynamic
  analyses. Verification NL-50 to NL-53 (tension and compression, within 0.11 %, equal to
  Mecway with CCX). Hyperfoam is not possible: Code-Aster 17.4 on Windows has no MFront.
- **Convergence window** (issue #3): buttons *.comm*, *.mail*, *Folder* and *ParaView* for
  the run shown. New setting `paraview_exe` (empty = search automatically, Salome-Meca's
  ParaView with a MED reader first).
- **Work folder next to the model** (issue #4): new setting `work_dir_beside_model`; the
  files of a run go to `<model>_aster` next to the open `.liml`. The start screen shows the
  folder in use.
- **Mode shapes** now also get the displacement magnitude, as in Mecway 34.
- **Flexible joints**: a joint with U, V and W free is exact with `POU_D_T_GD` at any
  rotation and no longer gives a warning (NL-90, NL-90b). A joint with only some rotations
  free on `POU_D_T_GD` beams gives an error before the run. Joints on offset beams are
  translated in linear static and modal analyses, with the joint at the end of the rigid
  arm as in Mecway 34 (LS-52a/b/c equal to Mecway in deflection and rotations). Ideas and benchmarks from the fork by MishalTPC
  (github.com/mishal0488/MecwayAsterBridge).
- Docs: Mecway 33/34 compatibility table and version policy
  ([After an update](docs/en/After_an_update.md) §6, `AGENTS.md`).
- **Preparation errors** (reading the model, mesh, solver files) are shown directly in the
  status box instead of only "see the log".
- The ParaView button starts Salome-Meca's ParaView through its `run_paraview.bat` (sets
  the Salome environment; `paraview.exe` on its own stops with "Qt5Widgets.dll not
  found"), also when `paraview_exe` points to that `paraview.exe`.
- A contact whose face selections are empty (Mecway 34 replaces spaces in selection names
  by `_` when it opens an older model and then loses the reference) now stops before
  Code-Aster with a clear message instead of a non-converging run (nonlinear static and
  dynamics; bonded contact always); in linear and thermal analyses, where Mecway ignores
  unilateral contact, it is a warning. The example models
  `Voorbeeld_A` and `Voorbeeld_C` use selection names without spaces.
- Documented limitation: `POU_D_T_GD` under large rotations about a skew axis gives
  step-size dependent forces (STAPPENPLAN S21, KNOWN_BUGS 11).
- STAPPENPLAN: S14 (hyperelastic material) done, hyperfoam waiting for a Windows build with
  MFront; S21 (selective joint on `POU_D_T_GD` via a stub element) tried and documented.

## V2026.3 – 16 October 2026

Beams with large rotations (`POU_D_T_GD`) in nonlinear static, and Mecway 34's *Element
orientation* cards are read, so beams rotated with *Loads & Constraints > Element orientation*
get the right section axes. Both build on the fork by MishalTPC
(github.com/mishal0488/MecwayAsterBridge). Tested in Mecway 34; verification 415 test cases,
2267 checks (2260 OK, 7 known limitations, 0 unexpected).

- **Beams with large rotations** (`elem_beam` = `POU_D_T_GD` on the Elements page; default
  stays `POU_D_E`): in nonlinear static with large displacements, beams are computed as
  `POU_D_T_GD` (Timoshenko, `ELAS_POUTRE_GR`, `GROT_GDEP`). Elsewhere, including nonlinear
  static with `PETIT`/`PETIT_REAC`, they become `POU_D_T` with a warning. Supported: forces
  and moments (constant or as a time table), line pressure (also formulas in x, y, z, t),
  gravity, Thermal stress, configurations, line3, orientation cards, centrifugal force as a
  fixed load (trusses too) and section forces (`beam_forces`, one value per element). No beam
  stresses. `crit_stab`, `imperfection_amplitude` and element failure give an error
  beforehand. Offset arms, flexible joints and couplings stay linear relations (warning;
  couplings not verified). Idea, Code-Aster route and benchmarks from the fork by MishalTPC
  (github.com/mishal0488/MecwayAsterBridge). Verification NL-80 to NL-89 (14 cases, 55
  checks, ≤ 0.04 %; within 0.02 % of Mecway 34 with CCX).
- **Element orientation in Loads & Constraints** (`<orientation>` card on an element
  selection, also with formulas of the element centre) is now read instead of skipped, so
  beams no longer keep the default section orientation: V axis and angle for beams, U
  axis for gaps and for the shell result field `shell_forces`, exactly like the
  orientation in *Element properties*. Overlap with the element attributes or a second
  card (Mecway itself does not solve that) gives a warning; the card wins. In addition
  **every beam gets Mecway's V axis explicitly** as `ORIENTATION` `VECT_Y`, also without
  orientation, so the bridge no longer relies on Code-Aster's default. Both found in the
  fork by MishalTPC (github.com/mishal0488/MecwayAsterBridge). Verification MO-31,
  LS-79–82, BU-25, LS-31d: the same results as with the attributes and equal to Mecway 34;
  all existing beam cases unchanged.
- **Start screen**: the status box is higher when there is a message, uses a larger
  font, and can be made larger or smaller by dragging its upper edge. If the folder of the
  open model no longer exists (moved or deleted), Start and *Results...* say so and ask to
  save the model with *File > Save As...*; before, the status box only showed a bare
  Windows error. Start no longer rewrites `bridge_utils.py` when nothing was changed (the
  order of the result fields was saved again in another order on every Start). Starting
  the bridge again from *Tools* while its window is open or a run is going on now only
  says that the window is already open; before, Mecway opened a second window, so two
  runs on the same model were possible (KNOWN_BUGS 38).
- Fixes: the results export no longer reports the section-force source of the other beam
  formulation as missing; centrifugal force on trusses in models that use the formula route.
- STAPPENPLAN: S19 (beam element with warping, `POU_D_TG`, for flexural-torsional buckling)
  planned.
- README: acknowledgement of the fork by MishalTPC.

## V2026.2 – 16 October 2026

More of Mecway is translated (bonded contact for shells and in thermal analyses, element
offset, flexible joint, quadratic beams, formulas in x, y, z, node temperature and
temperature in time), more results come back into Mecway, the bridge waits for Code-Aster
by itself, and the configurations of a model can be chosen. Tested with Mecway 33 and 34 and
Code-Aster 17.4; verification 394 test cases, 2152 checks (2145 OK, 7 known limitations,
0 unexpected).

### Workflow
- **No more "click OK when Code-Aster has finished"**: the bridge now waits by itself. A
  modal status window shows the elapsed time, the current step (time, attempt, iteration or
  solver phase) and the messages so far, with a *Stop...* button that ends only this run's
  Code-Aster processes; when Code-Aster has finished the window closes and the results are
  loaded. The end is detected from an end marker with the exit code of `run_aster`
  (`Scripts/aster_launch.bat`), else from `DIAGNOSTIC JOB` in the `.mess`; a non-zero exit
  code, a closed Code-Aster window and a stop are reported in the status box and the
  convergence window. New setting *Waiting for Code-Aster* (`wait_for_aster`, General):
  `auto` (default) or `confirm` (the old OK dialog). The status window stays on top of the
  Code-Aster console (which opens without the focus). Test `tests/test_bridge_wait.py`;
  model for testing Stop: `TestFiles/Tools/StopTest_LongRun.liml` (~95 s).
- **Choose the configuration** (load case) on the start screen: new setting *Configuration*
  (`configuration`, General), `auto` = the previous rule; the results go into that
  configuration's solution. No more unjustified warning with a single configuration
  (was KNOWN_BUGS 68). Verification LS-20a–e.
- **Fix: results of a model with configurations** (e.g. load cases G, Q, ULS): Mecway 34 could
  not open the `.liml` after the bridge wrote the results into it ("Error opening file"). The
  model copy in `<solution configuration="X">` is now written as Mecway writes it: without the
  `<configuration>` definitions and `<suppressed configuration>` children, with
  `suppressed="true"` on the items suppressed in X. Test `tests/test_results_configuration.py`.
- **Version check** (warning only): the log shows the Mecway version (from the `.liml`) and the
  Code-Aster version (launcher path, then the `.mess`); an untested version gives a WARNING. New page
  *After an update of Mecway or Code-Aster* (`docs/en/After_an_update.md`).

### Mecway functionality now translated
- **Bonded (Tie) contact between shells** now works: a shell face or edge glued onto a
  shell face no longer stops with a singular matrix (`FACTOR_11`); the drilling rotation is
  left out of `LIAISON_MAIL`. Example `TestFiles/Voorbeelden/Voorbeeld_T.liml`, verification
  LS-07a–e, docs §3.10 of the contact settings. Also with a skewed or curved master and
  with a quadratic shell (tri6/quad8) as master: the bridge then writes the tie itself as
  `LIAISON_DDL` (skewed/curved: MUMPS `NPREC` −1 for that run, with a warning).
  Verification LS-07f–k (KNOWN_BUGS 90–92 solved).
- **Bonded contact in thermal analyses** (T30/T31) is now translated instead of silently
  dropped (KNOWN_BUGS 88): *Tie* / *Constraint equations* → `AFFE_CHAR_THER`
  `LIAISON_MAIL`, *Elastic* → thermal resistance `ECHANGE_PAROI` with Mecway's *Thermal
  conductance per unit area* (conforming solid faces; otherwise ideally bonded with a
  warning). Models with solids and shells together: ERROR (Code-Aster cannot couple
  them). Verification TH-04a–d.
- **Element offset** (Loads & Constraints) for shells and beams is now translated instead
  of skipped: linear shells (DKT/DST) with `EXCENTREMENT`, quadratic shells (COQUE_3D) and
  beams on their own nodes with rigid arms to the Mecway nodes. Results stay on the Mecway
  nodes (reactions include the arm). Verification LS-60–63 (incl. Mecway's CompositeBeam
  sample).
- **Quadratic beams (line3)** are now translated (were not modelled): each element is
  split at its midside node into two SEG2 beam cells; results on all three nodes.
  **Flexible joint on beam** is translated: an own node per beam end, coupled with
  `LIAISON_DDL` in Mecway's local axes. Verification LS-50 and LS-51 (equal to
  Mecway); limits KNOWN_BUGS 106–107.
- **Formulas in x, y, z for mechanical loads** (also combined with t) are now translated
  instead of skipped (KNOWN_BUGS 45): pressure, traction, force, line pressure and
  prescribed displacement/rotation become a `FORMULE` of X, Y, Z (INST) in
  `AFFE_CHAR_MECA_F`, e.g. a hydrostatic-like pressure `3*y^2`. Pressure and traction match
  Mecway 34 exactly; force, line pressure and displacement with x, y, z are not applied by
  Mecway 34 itself (warning). Verification LS-40–44, NL-40; limits KNOWN_BUGS 104.
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
- **Mecway's time step size** in Nonlinear static is now used for the output times (load
  table kinks in between become extra steps); `substeps_per_interval` only applies without a
  step size (was KNOWN_BUGS 44). Verification NL-20.
- **Explicit dynamics**: a constraint equation with a constant ≠ 0 is now converted to an
  imposed acceleration (with a warning; was KNOWN_BUGS 41). Verification DY-20a–c.

### More results in Mecway
- New result fields: **contact pressure and contact status**, **beam section forces and
  moments** (N, V, T, M in Mecway's local axes), **shell stresses** (top/mid/bottom, off by
  default) and **forces and moments per unit length**, **total strain** (off by default) and
  the **factor of safety** of Mecway's *failure criterion*. `shell_forces` is on by default
  and gives a warning with its effect (about 2.5× larger results in the `.liml`).
  Verification LS-30–32, NL-30–32, MO-30, DY-30.

### Fixes
- **Several heat sources with a formula or time table** (*Internal heat generation*, heat
  flux on shell faces, `#ASTER-LASBRON`) now each give their own heat: Code-Aster 17.4
  computed two such loads both with the function of the first. All function sources are
  now in one load, overlapping sources summed per part of the mesh; a weld source next to
  a formula/table source no longer gives a warning (KNOWN_BUGS 70 solved). Verification
  TH-40–42.
- **`FACTOR_57` without a mechanism** (slender volume models in bending, MUMPS error estimate
  just above `RESI_RELA` 1e-6): the setting *Solver accuracy (RESI_RELA)* (`lin_solver_resi`,
  default 1e-6 as Code-Aster) is now also on the pages Modal (static step for the prestress,
  also cyclic), Buckling (static step) and Nonlinear static (static step of the imperfection).
  The error message reads the computed error from `study.mess`: below 1e-3 it names the page
  and the value to enter, above it the mechanism advice. Verification BU-37 (hex20 L frame).
  Was KNOWN_BUGS 114.
- **Cyclic symmetry about X or Y**: *Results...* reloads the results again (was KNOWN_BUGS 78).
- Final review fixes: two partly offset shell groups, offset and flexible joint on
  the same beam, element results of quad8 shells with offset, beam ends with a joint and
  line3 beams (they were silently missing), clear warnings in the thermal → mechanical
  chain and for offset combined with bonded contact.

### Verification, warnings and documentation
- **Beam orientation** verified for statics, natural frequencies and buckling against
  analytical values and Mecway 34 (MO-20–29, LS-70–78, BU-20–24): identical to Mecway.
- **Buckling of beams** investigated (BU-30–37): pure torsional buckling and frames with
  bending moments are right in the bridge (solid models and Code-Aster test ssll105 agree);
  Mecway's own beam element misses those terms. T, C and L sections cannot buckle
  flexural-torsionally with the beam elements (warning, KNOWN_BUGS 115; planned as STAPPENPLAN S19).
- Limits of the remaining open points are in the documentation and, where they can be
  detected, as warnings (curved line3 beams, joint on an element selection, offset shells
  with large rotations).
- **New overview** of which Mecway functionality the bridge does and does not translate
  (`docs/en/Mecway_features.md`, Dutch `docs/Mecway_functionaliteit.md`), also on the
  Documentation page of the start screen.
- Example `TestFiles/TieContact_Plates.liml` (bonded plates, with Code-Aster results).
- README: Mecway 34, acknowledgements.
- **Developer text in English**: code comments, docstrings, comments in the `.comm`
  templates (and the generated `study.comm`), INFO/SUCCESS log lines, `AGENTS.md`,
  `KNOWN_BUGS.md` and `STAPPENPLAN.md`. The user interface, messages, WARNING/ERROR lines,
  the convergence window and the user documentation (`docs/` Dutch, `docs/en/` English)
  stay bilingual.

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
