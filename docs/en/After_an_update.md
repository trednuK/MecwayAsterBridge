# After an update of Mecway or Code-Aster

The bridge has been tested with specific versions of Mecway and Code-Aster. A newer version
usually works too, but not always. This page explains what the version warning means and how to
check a new version.

## 1. The version warning

On every run the bridge looks at which versions are running:

- **Mecway**: the `version` attribute of `<liml>` in the saved model (Mecway 36 writes
  `<liml version="36">`).
- **Code-Aster**: before the run from the launcher path (`...\17.4\bin\run_aster.bat`), after the
  run from the header of the `.mess` (`Version 17.4.0 ...`). The version from the `.mess` counts; it
  is the version that actually computed. Only major.minor (17.4) is compared.

Both versions are at the top of the run log (`<model>_<run_id>_bridge_log.txt`), for example
`INFO: Mecway version 34 (tested).` and `INFO: Code-Aster version 17.4.0 according to .mess (tested).`

If a version has not been tested, a **WARNING** appears in the log and a message in the status box
at the end of the run. The run simply continues: it is only a warning. Check the results more
carefully then (for example against Mecway's own solver) and run the check of §2 when you can. If
a version cannot be determined (old model without `version`, your own Code-Aster build in a
different path), the log only has an INFO line.

The tested versions are in `Scripts/bridge_utils.py`, outside `CONFIG_BRIDGE`:

```python
TESTED_MECWAY_VERSIONS = ("33", "34", "36")
TESTED_ASTER_VERSIONS = ("17.4",)
```

## 2. Checking a new version

Needed: CPython 3 and the repository (see [`Verification.md`](Verification.md) §2).

| New version of | Run (in `TestFiles/Verificatie`) |
|---|---|
| Code-Aster | `python run_verificatie.py` (about an hour) and `python code_aster_testcases/run_code_aster_tests.py` (official Code-Aster tests) |
| Mecway | `python run_verificatie.py --mecway-opslaan`: Mecway first opens and saves every test model, then the bridge computes that copy saved by Mecway |

What to look at:

- `resultaten/resultaten.md` (with `--mecway-opslaan`: `resultaten/mecway/vergelijking.md`):
  **0 NOK and 0 FOUT** (error). BEKEND (known) is fine if they are the same known limitations as in
  the baseline.
- Compare the counts per group with the baseline in [`Verification.md`](Verification.md) §3.
- The official Code-Aster tests: all OK, no NOOK.

When you then update the documentation (tested versions, baseline), run
`python TestFiles/Tools/check_docs.py` from the main folder: it checks links and anchors,
references to `KNOWN_BUGS.md` and verification cases, the defaults in
[`Default_settings_and_assumptions.md`](Default_settings_and_assumptions.md) and the tooltips
against `CONFIG_BRIDGE`, and whether the Dutch and English pages have the same structure
(`--parity`: also the numbers per section). Expected: `0 finding(s)`.

## 3. What typically breaks

**Mecway**

- Tag and attribute names in the `.liml` (loads, constraints, materials, selections): a new name is
  not recognised and the load ends up in the "NOT translated" list at the end of the run
  (`bridge_from_liml.py`, `bridge_bcs.py`).
- The result format in `<solution>`: results do not load, or load in the wrong place
  (`aster_results_export.py`, `bridge_results_liml.py`).
- Units that Mecway writes differently: a WARNING "Unit not recognised" in the log. The other way
  round, a unit that Mecway no longer accepts: Mecway shows a message when it opens the model
  (Mecway 36 calls `N/m³` for an elastic support an incorrect unit and reads it as `Pa/m`), and with
  `--mecway-opslaan` the test case stops.

**Code-Aster**

- Keywords in the templates (`Scripts/AsterTemplate_*.comm`) and in the generated `.comm`: a renamed
  or removed keyword gives a syntax error in the `.mess`.
- The Python API used by the scripts in the job: `aster_results_export.py`, `aster_spectrum.py`,
  `aster_acoustic_export.py`, `aster_acoustic_complex.py`, `aster_cyclic.py`, `aster_fatigue.py`.
  An error is in the `.mess` or in `<model>_<run_id>_console.txt`.
- The `.mess` text that the bridge reads (convergence window and messages, `bridge_convergence.py`,
  `bridge_run_aster.py`): a different layout gives an empty or incomplete convergence window, or a
  missed error.

**A newer bridge**

- A setting in an older `Scripts/bridge_utils.py` that the new bridge no longer knows is
  ignored; which settings were added or removed is in `CHANGELOG.md`. From
  V2026.10: the setting for AdvancedToolsHub is gone, `salome_meca_dir` is new (empty = search automatically).
- The cell array of failed elements in the `.vtu` files ("VTU/PVD files for ParaView") is now
  called `failed` instead of `BEZWEKEN`: adjust a saved ParaView state that filters on
  `BEZWEKEN` (*Threshold*).
- From V2026.15 the result route `tabel` no longer exists: the results always go through
  the `.liml`. A kept `bridge_utils.py` with `"result_route": "tabel"` gives a WARNING and
  the run goes through the `.liml`; remove that line.

## 4. Choosing another Code-Aster version

Each Code-Aster version has its own folder with its own `run_aster.bat`. On the **General** page of
the start screen, choose the `run_aster.bat` of the desired version at *Code-Aster launcher
(run_aster.bat)* with *Browse...*, for example
`%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat`. The verification (§2) uses the same
setting. To go back to the previous version, choose the old path again.

## 5. After a successful check

Add the new version to `TESTED_MECWAY_VERSIONS` or `TESTED_ASTER_VERSIONS` in
`Scripts/bridge_utils.py` (by hand; these lines are outside `CONFIG_BRIDGE`, the start screen does
not change them) and update the baseline in [`Verification.md`](Verification.md) §3. From then on
the bridge gives no warning for that version. For a new Mecway version, also add a column
to the table in §6 with what was verified in it.

## 6. Mecway versions / compatibility

The bridge does not branch on the Mecway version: it recognises features by what is in the
`.liml` (a tag or attribute), or by what the scripting API offers (`mw.liml_text()` of
Mecway 36). An item that a Mecway version does not write is simply absent,
and the bridge then behaves as without that item. Status per area, with the release in which
it was last verified:

| Area | Mecway 33 | Mecway 34 (35 where named) | Mecway 36 |
|---|---|---|---|
| Translation up to V2026.2 (reading the `.liml`, mesh, loads, constraints, materials, analyses, results back into the `.liml`) | verified (V2026.2) | verified (V2026.4) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Results in a model with configurations (V2026.2; Mecway 34 could not open the earlier format) | verified (V2026.2) | verified (V2026.4) | verified headless (36.0.9815, 17 Nov 2026: results of LS-20a opened; a save adds an empty solution for each configuration without results); in the Mecway window (18 Nov 2026): LS-20a, after reopening the results are under the right configuration and the other ones stay empty |
| Waiting for Code-Aster, convergence window, version check (V2026.2) | verified (V2026.2) | verified (V2026.4) | version check verified headless (36.0.9815, 17–18 Nov 2026); waiting and the convergence window checked in the Mecway window (18 Nov 2026) |
| Beams with large rotations `POU_D_T_GD` (V2026.3) | NOT verified | verified (V2026.3) | verified headless (36.0.9815, 17–18 Nov 2026; the Mecway + CCX references of NL-82/NL-83 re-measured on Mecway 36: equal within 1e-4) |
| *Element orientation* cards in Loads & Constraints (V2026.3) | n/a (Mecway 33 has no such card) | verified (V2026.3) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Explicit `ORIENTATION` `VECT_Y` for every beam (V2026.3) | NOT verified | verified (V2026.3) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Start screen: status box, missing model folder, second window (V2026.3) | NOT verified | verified (V2026.3) | partly in the Mecway window (18 Nov 2026): the start screen opens, the version line without the WARNING "not tested", a second start gives the message that the bridge is busy; status box and missing model folder NOT verified |
| Line3 trusses and cables (V2026.4) | NOT verified (not checked whether Mecway 33 offers them; no effect on a model without them) | verified (V2026.4) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Hyperelastic Neo Hooke / Mooney-Rivlin (V2026.4) | NOT verified (not checked whether Mecway 33 offers them; no effect on a model without them) | verified (V2026.4) | verified headless (36.0.9815, 17–18 Nov 2026) |
| `#ASTER-SECTIE` (from MecwaySectionProps, own repository) and several custom model definitions | NOT verified (not checked whether Mecway 33 keeps an imported custom model definition) | verified (headless, 23 Oct 2026) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Plastic curve: E is the slope of the first segment (V2026.4) | NOT verified (measured in Mecway 34 with CCX) | verified (V2026.4) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Mode shapes with displacement magnitude (V2026.4) | NOT verified; Mecway 33's own modal solution shows no magnitude, so it is one extra item (harmless) | verified (V2026.4) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Flexible joints: `POU_D_T_GD` and offset beams (V2026.4) | NOT verified | verified (V2026.4) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Convergence window buttons, work folder next to the model, preparation errors in the status box (V2026.4) | NOT verified | verified (V2026.4) | partly in the Mecway window (18 Nov 2026): work folder next to the model (every run of the checks); the convergence window buttons and preparation errors NOT verified |
| Result formulas computed by the bridge, heat flux per element node (V2026.5) | NOT verified | verified (V2026.5) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Principal stresses/strains and acceleration under Mecway's names (V2026.5) | NOT verified | verified (V2026.5) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Principal values of shells, Green-Lagrange principal strains and `GLe1` (V2026.6) | NOT verified | verified (headless) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Rubber on hex8: locking warning, no `3D_SI` with `ELAS_HYPER`, *Element type* card (V2026.5) | NOT verified | verified (V2026.5) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Code-Aster summary as *Saved monitor* (V2026.6, option `save_monitor_liml`; `<savedmonitor>` in the `.liml`) | NOT verified | format measured headless (34.0.9772, 28 Oct 2026: written by Mecway's own solve, kept by open and `save_as`); the item in the tree NOT checked in the GUI | format verified headless (36.0.9815, 17 Nov 2026: kept by open and `save_as`); in the Mecway window (18 Nov 2026): the item is in the tree and stays after save and reopen; a double-click shows the summary in Mecway's *Saved monitor* window, as with Mecway's own solver (the model is black then, with Mecway's own solver too) |
| Bonded contact solid on solid: only the slave nodes CCX's `*TIE` ties (V2026.6, KNOWN_BUGS 128) | NOT verified | verified headless (Mecway 34 solve with CCX; Samples/BoltedJoint with bonded contacts, LS-07l/m, 28 Oct 2026); verified in the Mecway GUI on 29 Oct 2026 (LS-07l) | verified headless (36.0.9815, 17 Nov 2026; the Mecway + CCX reference of LS-07l/m re-measured on Mecway 36: equal) |
| Frictionless/symmetry next to displacement 0 on the same nodes reduced; modal with only bonded contact or couplings as free-free (V2026.6, GitHub issue #9) | NOT verified | verified headless (Mecway 34 solve of the same models as reference, 28 Oct 2026); a run from Mecway's GUI: NOT yet | verified headless (36.0.9815, 17–18 Nov 2026) |
| Beam with warping `POU_D_TG`, setting `beam_warping` (V2026.6) | NOT verified | verified in the Mecway GUI (28/29 Oct 2026: BU-38, LS-94, LS-95 = Mecway; Mecway writes nothing new in the `.liml` for it) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Orthotropic / stiffness matrix / compliance matrix on solids with the element orientation as material axes (V2026.6, S13a) | NOT verified (not checked whether Mecway 33 writes the same attributes; no effect on a model without them) | verified headless (34.0.9772, 28 Oct 2026: OR-01..22 against Mecway's own solve of the same `.liml`; attribute names confirmed by Mecway's solve (σ = C·ε)); not yet in the Mecway GUI | verified headless (36.0.9815, 17–18 Nov 2026) |
| *Pre-tension section* (`force="true"` / `adjustment="true"`, V2026.6) | NOT verified (Samples/BoltedJoint has the same tag; not checked whether Mecway 33 writes the `adjustment` attribute) | verified headless (28 Oct 2026: PT-01..05 against Mecway's own CCX solve, model saved by Mecway; dynamic response PT-06..08 against CCX and the spring element variant PT-09/10 against the internal solver, S15b, also identical through models saved by Mecway); verified in the Mecway GUI on 29 Oct 2026 with the spring variant (PT-09), the prism variant not yet | verified headless (36.0.9815, 17–18 Nov 2026) |
| Static 2D (S20), Static Axisymmetric (SA0), Dynamic Response 2D/Axisymmetric (D20, DA0): `C_PLAN`/`D_PLAN`/`AXIS`, results under Mecway's names (S16a, S16b, V2026.6) | NOT verified | verified headless (28 October 2026: Mecway's own solution, `mw.face_nodes`, the fields recognised after opening); a run in the Mecway GUI still to do | translation and results verified headless (36.0.9815, 17–18 Nov 2026); in the Mecway window (18 Nov 2026): PL-07 runs without an error, values as in the regression (`mw.face_nodes`) |
| Acoustic Resonance 2D (A20): `PHENOMENE='ACOUSTIQUE'`, `PLAN` / `PLAN_ABSO` (S16d, V2026.6) | NOT verified | verified headless (34.0.9772, 28 October 2026: Mecway's own A20 solution of AK-10 … AK-15 and of the organ pipe tutorial, bridge results opened by Mecway with `solution.node_value`); a run in the Mecway GUI still to do | verified headless (36.0.9815, 17–18 Nov 2026) |
| Thermal stress in S20/SA0 (S44c) and nonlinear 2D with `**ASTER-PLANE` on S30/L30 shells (S44a, V2026.13) | NOT verified | NOT verified (measured with Mecway 35.0.9802 headless, 13 Nov 2026: Mecway's own S20/SA0 solutions for PL-20 … PL-28 and S30 for PL-33; PL-30 … PL-32 and PL-34 … PL-36 against closed forms and Code-Aster); opening a result in the Mecway GUI still to do | verified headless (36.0.9815, 17–18 Nov 2026) |
| Axisymmetric heat transfer with `**ASTER-PLANE AXIS` in T30/T31 and the thermomechanical chain (T31 with *Thermal stress*) (S44d, V2026.14) | NOT verified | NOT verified (Code-Aster 17.4 against closed forms, PL-50 … PL-59; Mecway has no axisymmetric thermal type, so no Mecway reference; opening a result in the Mecway GUI still to do) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Axisymmetric shells: line3 elements in S30/L30 with `**ASTER-PLANE AXIS` and `**ASTER-SHELL` (`COQUE_AXIS`, S44e, V2026.14; stresses and section forces per surface) | NOT verified | NOT verified (Code-Aster 17.4 against closed forms and ssls114i, PL-60 … PL-68). Mecway 35 (35.0.9802), in the Mecway window (17 Nov 2026): accepts a *Pressure* on the side faces of line3 in S30 and draws the arrows on the face where the bridge applies it (PL-60); shows displacement, rotation Z and the reactions on the meridian line (PL-62); the component, the pressure and the symmetry show red in the tree. The stresses on line elements were not yet seen in Mecway 35. | verified headless (36.0.9815, 17–18 Nov 2026); in the Mecway window (17 Nov 2026, after the fix of the pressure side): PL-60 and PL-62 rerun, all values as expected (deflection, reactions, `vonmises…`, `hoopstress…`, `meridionalstress…`, `momentu`) |
| Traction/pressure on the side face of a beam (faceid 1), hydrostatic pressure on shell edges (S17, V2026.6) | NOT verified | verified headless (28 October 2026: faces of a beam with `mw.face_nodes`, traction = T × perimeter and pressure = no load against the internal solver, LS-92; Mecway applies no hydrostatic pressure on shell edges, LS-93 against its Pressure formula); not yet in the Mecway GUI | translation and results verified headless (36.0.9815, 17–18 Nov 2026); in the Mecway window (18 Nov 2026): LS-92a runs without an error, values as in the regression (`mw.face_nodes`) |
| Imperfection, step guard `gd_step_limit` and jump check with `POU_D_T_GD` beams (V2026.7, GitHub issue #10) | NOT verified | NOT verified (Mecway 34 was not available). Code-Aster runs NK-05 to NK-10; verified on Mecway 35 (35.0.9802) in the GUI with the column of issue #10 (6 Nov 2026) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Shape of a General section: `** SECTIE-VORM`, "Show section", "Section in results" (User guide §4.3) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 only (35.0.9802): headless, and both views seen in the Mecway window (6 Nov 2026), also the shape that goes into the results at the end of a run | in the Mecway window (18 Nov 2026): LS-97a, the shells visible with values, none black; "Hide" removes them before a run |
| Check of the direction of a General section: `** SECTIE-RICHTING` (User guide §4.3) | NOT verified | NOT verified (Mecway 34 was not available). On Mecway 35 the line and the orientation card were written by MecwaySectionProps in a hidden run, and read by the bridge on a Code-Aster run outside Mecway (45 degrees reported, nothing with the right V). Not checked in the Mecway window | NOT verified (not part of the headless checks) |
| Status window a normal window after 10 s, with a taskbar button (V2026.8) | NOT verified | NOT verified: checked with a dummy job in Mecway's IronPython, not on a real run in Mecway | in the Mecway window (18 Nov 2026): under Mecway 36's taskbar button |
| `FACTOR_57` after `DIAGNOSTIC JOB : OK` in the convergence window, summary and status box (V2026.8) | NOT verified | NOT verified: checked on the `.mess` of a real run, not in the Mecway window | NOT verified (needs the Mecway window) |
| WARNING for a beam without warping on an open General section (V2026.8) | NOT verified | NOT verified: offline tests; the difference between `POU_D_E` and `POU_D_TG` was measured with Code-Aster 17.4 outside Mecway | n/a (does not depend on Mecway) |
| Selection names with spaces (models from Mecway 33) | allowed | Mecway 34 replaces the spaces by `_` when it opens such a model and then loses the reference in a contact (`selectionmaster=""`, seen 22 October 2026); the bridge stops before Code-Aster with an ERROR that says so where the contact counts (nonlinear static and dynamics; bonded contact in every analysis), elsewhere it gives a WARNING (Mecway ignores unilateral contact there too). Select the contact faces again. The example models use names without spaces. | NOT verified (not measured on Mecway 36) |
| Stress over beam sections, S41 (`beamvonmisesmax`, `sectionshear` ...) (V2026.9) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Main window: menu "Section ▾", navigation scrollbar, layout at a display scale of 125 % (V2026.9) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) | NOT verified (needs the Mecway window) |
| Convergence window: look of the main window, readable at 125 % (V2026.9) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) | in the Mecway window (18 Nov 2026): readable at 125 % |
| `POU_D_TG` stresses and reactions from one elastic `STAT_NON_LINE` step (V2026.9, KNOWN_BUGS 123) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) | verified headless (36.0.9815, 17–18 Nov 2026) |
| Keep the Code-Aster base with a manifest, `keep_base` (V2026.9) | NOT verified | NOT verified: offline tests; with the setting off (default) mesh and `.comm` stay the same | n/a (does not depend on Mecway) |
| Buttons "ParaView" and "AsterStudy" in the Results window and the convergence window, setting `salome_meca_dir` (V2026.10) | NOT verified | Mecway 35 (35.0.9802): verified in the Mecway window (11 Nov 2026); also started from a hidden Mecway (10 Nov 2026: ParaView 6.2.1 with a `.pvd`, AsterStudy *Results* with a `.rmed`); from the convergence window's Python: `.rmed`, `_xfem.rmed`, `_verfijnd.rmed` | in the Mecway window (18 Nov 2026): both buttons in the Results window open their file; in the convergence window NOT verified |
| Hiding failed elements, `hide_failed`; `failed` 1 from the step after the failure (V2026.11) | NOT verified | Mecway 35 (35.0.9802): verified in the Mecway window with `BezwijkenTrekstaaf` (11 Nov 2026); files also checked offline and with `BezwijkenTrekstaaf` (Code-Aster 17.4, splice under IronPython 2.7.9) | files verified headless (36.0.9815, 17 Nov 2026: `BezwijkenTrekstaaf`, the processed file opened by Mecway 36); in the Mecway window (18 Nov 2026): the failed elements are gone from the step after the failure, also after a save in Mecway 36 and reopening |
| Convergence window under Mecway's taskbar button; long path over several lines (V2026.11) | NOT verified | Mecway 35 in Program Files: a test window with the same taskbar ID sat under Mecway's button, and the convergence window itself after a run (11 Nov 2026) | in the Mecway window (18 Nov 2026): under Mecway 36's taskbar button; long path NOT verified |
| WARNING for a *Fixed support* on a node selection with shell or solid nodes, KNOWN_BUGS 135 (V2026.12) | NOT verified | NOT verified in the Mecway window: offline tests; that Mecway 35 (35.0.9802) leaves such nodes free was measured headless with Mecway's own solver on quad and hex nodes (11 Nov 2026; trusses from the manual, NOT measured); the `.comm` of all 578 comparable verification cases is the same | NOT verified (Mecway's own behaviour not re-measured on Mecway 36) |
| Results after Code-Aster's time limit: extra time after a `TimeLimitError`, time guard of the step loops (V2026.12) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (`StopTest_LongRun`, WE-12, 11 Nov 2026); linear static and thermal since S45 phase 1 (headless, FX-04, TH-02a, WE-04b, 13 Nov 2026); other linear analyses and the thermal chains still lose the results (KNOWN_BUGS 137) | n/a (does not depend on Mecway) |
| Hiding failed elements with core `liml_failed.py` 1.0.5: other node values follow the original, marker `failed_hidden`, supports stay in place (V2026.12) | NOT verified | NOT verified in the Mecway window: offline tests (CPython and IronPython 2.7.9) and the copy test against AdvancedToolsHub; that Mecway 35 keeps the marker on a save was measured outside the bridge | verified headless (36.0.9815, 17–18 Nov 2026): the marker `failed_hidden` stays on a save by Mecway 36 |
| WARNING for an isotropic material without Young's modulus, KNOWN_BUGS 60 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; that Mecway computes such a material with E = 0 was seen headless in a Frequency model (13 Nov 2026) | n/a (does not depend on Mecway) |
| Pinned support on several nodes in 2D as the mean displacement, KNOWN_BUGS 134 (V2026.13) | NOT verified | NOT verified in the Mecway window: measured with Mecway 35.0.9802 headless (17 Nov 2026): S20 plane stress (PL-07), plane strain and SA0 equal to Mecway's own solution; D20/DA0 not measured | verified headless (36.0.9815, 17–18 Nov 2026) |
| WARNING for bonded shell faces (face to face, shell on solid), KNOWN_BUGS 128 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; the lap of two bonded plates measured headless with Code-Aster 17.4 and Mecway's own solver against a solid hex20 reference (13 Nov 2026) | n/a (does not depend on Mecway) |
| WARNING for linear buckling with DKT/DST shells, naming `COQUE_3D`, KNOWN_BUGS 132 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; the T beam of BU-43c measured headless with Code-Aster 17.4 (DKT and `COQUE_3D`) and Mecway's own solver on the same mesh (13 Nov 2026) | n/a (does not depend on Mecway) |
| Default `lin_solver_resi` 1e-5 instead of 1e-6 in linear static, nonlinear static, modal and buckling, KNOWN_BUGS 138, found and fixed in this release (V2026.13) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (160 x 32 quad4 plate and hex20 lap compute, the lap equals Mecway; 40 x 8 plate bit-identical to 1e-6, 13 Nov 2026); the 293 verification cases whose `.comm` changes plus the fastest of every group: no status change | n/a (does not depend on Mecway) |
| Contact in 2D and axisymmetric with `**ASTER-PLANE` (edges of plane elements, also friction), WARNING for KNOWN_BUGS 141 (S44b, V2026.13) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (PL-40 … PL-46 against Lamé, Hertz, Coulomb and the Code-Aster test ssnp121a); Mecway 35 (35.0.9802), in the Mecway window (17 Nov 2026): PL-40 opens without a message after the fix of the example models (V2026.14); the analysis, the components and the contact show red in the tree; the result shows the strip flat in 3D with the stress tensor under Mecway's names. | verified headless (36.0.9815, 17–18 Nov 2026); in the Mecway window (17 Nov 2026): PL-47 shows `radialstress`, `axialstress`, `hoopstress`, `shearstressrz` and the contact pressure (as *contact stress pressure*) with the values of [`2D_and_axisymmetric.md`](2D_and_axisymmetric.md) §1.5 example 8 (V2026.14) |
| Results after Code-Aster's time limit in linear static and thermal: extra time after the solve, `MECA_STATIQUE` with `OPTION='SANS'` (S45 phase 1, V2026.13) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (FX-04, TH-02a, WE-04b with a delay past the limit, results bit-identical; 291 verification cases whose `.comm` changes: no status change) | n/a (does not depend on Mecway) |
| Total harmonic stresses with hysteretic damping, E(1 + iη)ε per material, KNOWN_BUGS 120 (V2026.14; V2026.13 only gave a WARNING) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (HR-06e … HR-06g, bar in tension, `PHYS` and `GENE`, two materials in series) | n/a (does not depend on Mecway) |
| WARNING for linear buckling with an eccentric general section (`ASTER-SECTIE` with the shear centre off the centroid), KNOWN_BUGS 115 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; the buckling factor of such a section is not measured | n/a (does not depend on Mecway) |
| Element failure (`#ASTER-BEZWIJKEN`) in 2D and axisymmetric with `**ASTER-PLANE` in L30, WARNING for KNOWN_BUGS 144 (V2026.14) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (PL-70 … PL-74 against closed forms) | NOT verified in the Mecway window (headless runs do not depend on the Mecway version) |
| The thermomechanical chain (T31 with *Thermal stress*) with `**ASTER-PLANE C_PLAN` or `D_PLAN`, and with plasticity in `AXIS` (V2026.14) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (PL-75 … PL-80 against closed forms) | NOT verified in the Mecway window (headless runs do not depend on the Mecway version) |
| Gaps with their own U axis (*Element orientation* card), no lateral stiffness of a closed gap, KNOWN_BUGS 23 (V2026.14) | NOT verified | Mecway 35 (35.0.9802) headless: NL-92e … NL-92l equal to Mecway's own solution; NL-92m against the hand calculation | NOT verified (Mecway's own gap not re-measured on Mecway 36) |
| The model as text through `mw.liml_text()`: a run and "Show section" read a copy of the open model; the model is saved only when the results (or the Saved monitor) go into it (V2026.15) | n/a (no `mw.liml_text()`: the model is saved as before) | n/a (no `mw.liml_text()`: the model is saved as before) | verified headless (36.0.9815, 18 Nov 2026: the former route `tabel` and "Show section" in a hidden Mecway, the model file unchanged, the same `.comm`, mesh and fatigue result as with saving; 19 Nov 2026: a run on VM-01a and LS-20a, the same results and model file as with saving first, a failed run leaves the file unchanged); verified in the Mecway window (36.0.9815, 19 Nov 2026, bridge a434d50: an unsaved edit in VM-01a is saved once, right before the results, the copy is removed; a failed run leaves the file and the edit as they were with "Summary also as Saved monitor in the .liml" off, and saves it with the monitor on; LS-20a with three configurations, the status window modal, "Results..." > "Load"; a read-only model stops before Code-Aster; an untitled model stops with a message; "Show section" saves nothing; "Results..." > "Remove from model" and "Load"; no route choice on the start screen and the WARNING for a kept `result_route` line). After a run that left the file as it was Mecway asks "Save changes?" when another model is opened: Mecway does that after every script, even one that changes nothing (36.0.9815, 19 Nov 2026, a script `x = 1`; user guide §2) |
| Contact (V2026.15): contact method `auto` (also implicit dynamics), D31 *Time step size*, `SEUIL_INIT` with friction, double supports on bonded slave nodes (KNOWN_BUGS 147), `bonded_close_gap`, rigid friction stick (KNOWN_BUGS 149) | NOT verified | NOT verified | verified headless (36.0.9815, 18-19 Nov 2026: NL-03g/h/i/j/k/l/m and LS-07n/p/q against Mecway 36's own CCX solve, LS-07o against the Mecway 34 reference of LS-07m); verified in the Mecway window (36.0.9815, 19 Nov 2026, bridge a434d50: NL-03g with `auto` = penalty, w 1.952e-6 m; the `#ASTER-ZONE`/`#ASTER-BONDED` checks; NL-03h with the kt WARNING, `SEUIL_INIT` and 10 steps; LS-07n without `FACTOR_11`; gap WARNING and `bonded_close_gap` on LS-07 with a 1.5 mm and a 0.2 mm gap; the CCX keyword WARNING, and none when the item is suppressed; PipeClip with the RELA_OF_MAXI advice and AssemblyWithContact *Friction* completing) |
| Load tables in nonlinear static without *Quasi-static* (up to t = 1 s) and with CCX *time points* without *Automatic time stepping* (up to the period) (V2026.15) | NOT verified | temperature table at t = 1 s verified (Mecway 34 with CCX, NL-75); the rest NOT verified | verified headless (36.0.9815, 19 Nov 2026: force, imposed displacement and temperature tables, NL-75b..f; only the end state with time points, NL-75e..g) |
| Shells in implicit dynamics: zero initial acceleration with DKT, `COQUE_3D` with `PETIT` (KNOWN_BUGS 156 fixed) (V2026.15) | NOT verified | NOT verified | verified headless (36.0.9815 with CCX, 19 Nov 2026: DY-40a..h against Mecway's own solve) |
| Element per component (`#ASTER-ELEMENT`) (V2026.15) | NOT verified | NOT verified | NOT verified (offline only: the bridge reads the CCX field like the other `#ASTER` lines; LS-98a/b with Code-Aster 17.4 (19 Nov 2026), reference Mecway 34 on LS-07b) |
| Force on shell edges of several components, shared by length × thickness (V2026.15) | NOT verified | NOT verified | verified headless (36.0.9815, internal solver, 19 Nov 2026: LS-98d, two strips of 2 and 4 mm) |
| Very large models: the `.mail` written in pieces, a faster model read, `mumps_memory` with its WARNING when `low_rank` has no effect, the WARNING when MUMPS put its factorization on disk, the window "Please wait" (V2026.15) | NOT verified | NOT verified | in the Mecway window (36.0.9815, 19 Nov 2026): "Please wait" while the mesh is written and while the results are loaded (the latter seen only by its title), gone once the Code-Aster status window opens, and the out-of-core WARNING on a large block; the rest measured headless with Code-Aster 17.4 and IronPython 2.7.9 |
| Mouse wheel over a closed choice list on the start screen scrolls the page instead of changing its value (V2026.15) | n/a (does not depend on Mecway) | n/a | n/a (offscreen test of the start screen only) |
| PETSc and MPI: `mpi_nbcpu`, `matr_distribuee`, `lin_solver` PETSC with `petsc_algo` and `petsc_precond` (V2026.16) | NOT verified | NOT verified | NOT verified in the Mecway window (`tests/test_bridge_petsc_mpi.py`; the defaults leave the `.comm` and the `.export` as in V2026.15; PETSc needs a parallel Code-Aster, the Windows build does not have it) |
| Results on the host from the MED file, `results_from_med` (V2026.16) | NOT verified | NOT verified | NOT verified in the Mecway window (`tests/test_bridge_med.py`; off by default, a Windows job still writes the fragment itself) |
| Preparation window and `aster_fast` (mesh index, free faces, read buffer on the heap) (V2026.16; earlier the fork releases V2026.14-fast.1 … fast.3) | NOT verified | NOT verified | NOT verified in the Mecway window (`tests/test_bridge_fast.py`; without `aster_fast.exe` the Python path stays) |
| Results window with the step and a bar (MED field, variable, percent written into the `.liml`, opening the model) (V2026.17) | NOT verified | NOT verified | NOT verified in the Mecway window (the same window as the preparation; the `.comm` and the `.export` are unchanged) |

"Verified" means the verification of §2 and a run in Mecway with that version. Comparisons
with Mecway's own solver in the other documents name the Mecway version they were measured
with; that is the version of the reference, not a limitation of the bridge.

*Verified headless* in the column Mecway 36: the verification of §2 with that version and the
checks below, without the Mecway window. Mecway 36 is in `TESTED_MECWAY_VERSIONS` on that basis
(§5).

Mecway 36 (36.0.9815, a release candidate) was verified headless on 17 and 18 November 2026,
with Code-Aster 17.4:

- the verification of §2 on bridge d9780c5: 631 test cases, 3267 checks, 3261 OK, 6 BEKEND
  (known), 0 NOK/FOUT; with `--mecway-opslaan` on models saved by Mecway 36, 3262 checks
  identical to the normal run, 1 different only in round-off (LS-97c), and LS-20e not possible
  (an inconsistent model on purpose; [`Verification.md`](Verification.md) §1). This run is not
  the baseline of [`Verification.md`](Verification.md) §3, which comes from one revision at the
  release;
- on bridge 4cdb284 (V2026.14 in development, after the changes to gaps, 2D results and
  axisymmetric shells): with `--mecway-opslaan` 122 test cases: those that the changes touch
  (`TestFiles/Tools/regression_scope.py`), all PL cases and the fastest case of every group; all
  checks identical to the normal run or OK where the normal run has no value yet (PL-47);
- the references that came from Mecway (its own solver and CCX), measured again with
  Mecway 36: 557 of the 589 checks that can be compared agree within 1e-4 relative; the
  others come from another reference model or from rounding of the stored value;
- Mecway 36 with CCX returns a beam as the solid elements CCX expands it into (hex8 for
  line2, hex20 for line3), with their own node numbers: 4 or 8 nodes around the section per
  node of the beam. Their mean is the displacement of the beam node; measured that way,
  NL-82, NL-83 and LS-50 give the references of Mecway 34 with CCX back within 1e-4. Only
  displacements were compared; rotations, beam forces and shells with CCX were NOT checked
  on Mecway 36; CCX on solids is unchanged;
- results of the bridge opened by Mecway 36 (`node_value`, `element_node_value`): 4826
  values equal to what the bridge wrote; a save in Mecway 36 keeps the Saved monitor and
  `failed_hidden`, drops the empty `<nodes />`/`<values />` tails (as Mecway 35) and adds an
  empty solution for each configuration without results;
- the bridge starts in Mecway 36 (`mw.version()` gives 36) and translates
  `Voorbeeld_A.liml` (linear and nonlinear static).

In the Mecway 36 window: PL-47, PL-60 and PL-62 (17 November 2026), and ten checks
(18 November 2026, bridge d86a39b): the start screen with the version line and a second start; linear static with
route `liml` (`Voorbeeld_A.liml` with the lines of example 1 of
[`ASTER_lines_examples.md`](ASTER_lines_examples.md); contour per element without black
faces); configurations (LS-20a); the Saved monitor; hiding failed elements
(`BezwijkenTrekstaaf`); showing and hiding the section (LS-97a); the status window and the
convergence window; the buttons ParaView and AsterStudy; `mw.face_nodes` (PL-07, LS-92a); route
`tabel` (a cantilever beam, tip displacement −35.3 mm; that route no longer exists since V2026.15). All ten as expected (see the table, where a row exists). The check
of the version compares the major version only, so 36 also covers the final build of Mecway 36: run
§2 with `--mecway-opslaan` again on that build.
