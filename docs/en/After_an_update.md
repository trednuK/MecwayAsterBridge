# After an update of Mecway or Code-Aster

The bridge has been tested with specific versions of Mecway and Code-Aster. A newer version
usually works too, but not always. This page explains what the version warning means and how to
check a new version.

## 1. The version warning

On every run the bridge looks at which versions are running:

- **Mecway**: the `version` attribute of `<liml>` in the saved model (Mecway 34 writes
  `<liml version="34">`).
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
TESTED_MECWAY_VERSIONS = ("33", "34")
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
- Units that Mecway writes differently: a WARNING "Unit not recognised" in the log.

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
`.liml` (a tag or attribute). An item that a Mecway version does not write is simply absent,
and the bridge then behaves as without that item. Status per area, with the release in which
it was last verified:

| Area | Mecway 33 | Mecway 34 |
|---|---|---|
| Translation up to V2026.2 (reading the `.liml`, mesh, loads, constraints, materials, analyses, results back into the `.liml`) | verified (V2026.2) | verified (V2026.4) |
| Results in a model with configurations (V2026.2; Mecway 34 could not open the earlier format) | verified (V2026.2) | verified (V2026.4) |
| Waiting for Code-Aster, convergence window, version check (V2026.2) | verified (V2026.2) | verified (V2026.4) |
| Beams with large rotations `POU_D_T_GD` (V2026.3) | NOT verified | verified (V2026.3) |
| *Element orientation* cards in Loads & Constraints (V2026.3) | n/a (Mecway 33 has no such card) | verified (V2026.3) |
| Explicit `ORIENTATION` `VECT_Y` for every beam (V2026.3) | NOT verified | verified (V2026.3) |
| Start screen: status box, missing model folder, second window (V2026.3) | NOT verified | verified (V2026.3) |
| Line3 trusses and cables (V2026.4) | NOT verified (not checked whether Mecway 33 offers them; no effect on a model without them) | verified (V2026.4) |
| Hyperelastic Neo Hooke / Mooney-Rivlin (V2026.4) | NOT verified (not checked whether Mecway 33 offers them; no effect on a model without them) | verified (V2026.4) |
| `#ASTER-SECTIE` (from MecwaySectionProps, own repository) and several custom model definitions | NOT verified (not checked whether Mecway 33 keeps an imported custom model definition) | verified (headless, 23 Oct 2026) |
| Plastic curve: E is the slope of the first segment (V2026.4) | NOT verified (measured in Mecway 34 with CCX) | verified (V2026.4) |
| Mode shapes with displacement magnitude (V2026.4) | NOT verified; Mecway 33's own modal solution shows no magnitude, so it is one extra item (harmless) | verified (V2026.4) |
| Flexible joints: `POU_D_T_GD` and offset beams (V2026.4) | NOT verified | verified (V2026.4) |
| Convergence window buttons, work folder next to the model, preparation errors in the status box (V2026.4) | NOT verified | verified (V2026.4) |
| Result formulas computed by the bridge, heat flux per element node (V2026.5) | NOT verified | verified (V2026.5) |
| Principal stresses/strains and acceleration under Mecway's names (V2026.5) | NOT verified | verified (V2026.5) |
| Principal values of shells, Green-Lagrange principal strains and `GLe1` (V2026.6) | NOT verified | verified (headless) |
| Rubber on hex8: locking warning, no `3D_SI` with `ELAS_HYPER`, *Element type* card (V2026.5) | NOT verified | verified (V2026.5) |
| Code-Aster summary as *Saved monitor* (V2026.6, option `save_monitor_liml`; `<savedmonitor>` in the `.liml`) | NOT verified | format measured headless (34.0.9772, 28 Oct 2026: written by Mecway's own solve, kept by open and `save_as`); the item in the tree NOT checked in the GUI |
| Bonded contact solid on solid: only the slave nodes CCX's `*TIE` ties (V2026.6, KNOWN_BUGS 128) | NOT verified | verified headless (Mecway 34 solve with CCX; Samples/BoltedJoint with bonded contacts, LS-07l/m, 28 Oct 2026); verified in the Mecway GUI on 29 Oct 2026 (LS-07l) |
| Frictionless/symmetry next to displacement 0 on the same nodes reduced; modal with only bonded contact or couplings as free-free (V2026.6, GitHub issue #9) | NOT verified | verified headless (Mecway 34 solve of the same models as reference, 28 Oct 2026); a run from Mecway's GUI: NOT yet |
| Beam with warping `POU_D_TG`, setting `beam_warping` (V2026.6) | NOT verified | verified in the Mecway GUI (28/29 Oct 2026: BU-38, LS-94, LS-95 = Mecway; Mecway writes nothing new in the `.liml` for it) |
| Orthotropic / stiffness matrix / compliance matrix on solids with the element orientation as material axes (V2026.6, S13a) | NOT verified (not checked whether Mecway 33 writes the same attributes; no effect on a model without them) | verified headless (34.0.9772, 28 Oct 2026: OR-01..22 against Mecway's own solve of the same `.liml`; attribute names confirmed by Mecway's solve (σ = C·ε)); not yet in the Mecway GUI |
| *Pre-tension section* (`force="true"` / `adjustment="true"`, V2026.6) | NOT verified (Samples/BoltedJoint has the same tag; not checked whether Mecway 33 writes the `adjustment` attribute) | verified headless (28 Oct 2026: PT-01..05 against Mecway's own CCX solve, model saved by Mecway; dynamic response PT-06..08 against CCX and the spring element variant PT-09/10 against the internal solver, S15b, also identical through models saved by Mecway); verified in the Mecway GUI on 29 Oct 2026 with the spring variant (PT-09), the prism variant not yet |
| Static 2D (S20), Static Axisymmetric (SA0), Dynamic Response 2D/Axisymmetric (D20, DA0): `C_PLAN`/`D_PLAN`/`AXIS`, results under Mecway's names (S16a, S16b, V2026.6) | NOT verified | verified headless (28 October 2026: Mecway's own solution, `mw.face_nodes`, the fields recognised after opening); a run in the Mecway GUI still to do |
| Acoustic Resonance 2D (A20): `PHENOMENE='ACOUSTIQUE'`, `PLAN` / `PLAN_ABSO` (S16d, V2026.6) | NOT verified | verified headless (34.0.9772, 28 October 2026: Mecway's own A20 solution of AK-10 … AK-15 and of the organ pipe tutorial, bridge results opened by Mecway with `solution.node_value`); a run in the Mecway GUI still to do |
| Traction/pressure on the side face of a beam (faceid 1), hydrostatic pressure on shell edges (S17, V2026.6) | NOT verified | verified headless (28 October 2026: faces of a beam with `mw.face_nodes`, traction = T × perimeter and pressure = no load against the internal solver, LS-92; Mecway applies no hydrostatic pressure on shell edges, LS-93 against its Pressure formula); not yet in the Mecway GUI |
| Imperfection, step guard `gd_step_limit` and jump check with `POU_D_T_GD` beams (V2026.7, GitHub issue #10) | NOT verified | NOT verified (Mecway 34 was not available). Code-Aster runs NK-05 to NK-10; verified on Mecway 35 (35.0.9802) in the GUI with the column of issue #10 (6 Nov 2026) |
| Shape of a General section: `** SECTIE-VORM`, "Show section", "Section in results" (User guide §4.3) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 only (35.0.9802): headless, and both views seen in the Mecway window (6 Nov 2026), also the shape that goes into the results at the end of a run |
| Check of the direction of a General section: `** SECTIE-RICHTING` (User guide §4.3) | NOT verified | NOT verified (Mecway 34 was not available). On Mecway 35 the line and the orientation card were written by MecwaySectionProps in a hidden run, and read by the bridge on a Code-Aster run outside Mecway (45 degrees reported, nothing with the right V). Not checked in the Mecway window |
| Status window a normal window after 10 s, with a taskbar button (V2026.8) | NOT verified | NOT verified: checked with a dummy job in Mecway's IronPython, not on a real run in Mecway |
| `FACTOR_57` after `DIAGNOSTIC JOB : OK` in the convergence window, summary and status box (V2026.8) | NOT verified | NOT verified: checked on the `.mess` of a real run, not in the Mecway window |
| WARNING for a beam without warping on an open General section (V2026.8) | NOT verified | NOT verified: offline tests; the difference between `POU_D_E` and `POU_D_TG` was measured with Code-Aster 17.4 outside Mecway |
| Selection names with spaces (models from Mecway 33) | allowed | Mecway 34 replaces the spaces by `_` when it opens such a model and then loses the reference in a contact (`selectionmaster=""`, seen 22 October 2026); the bridge stops before Code-Aster with an ERROR that says so where the contact counts (nonlinear static and dynamics; bonded contact in every analysis), elsewhere it gives a WARNING (Mecway ignores unilateral contact there too). Select the contact faces again. The example models use names without spaces. |
| Stress over beam sections, S41 (`beamvonmisesmax`, `sectionshear` ...) (V2026.9) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) |
| Main window: menu "Section ▾", navigation scrollbar, layout at a display scale of 125 % (V2026.9) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) |
| Convergence window: look of the main window, readable at 125 % (V2026.9) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) |
| `POU_D_TG` stresses and reactions from one elastic `STAT_NON_LINE` step (V2026.9, KNOWN_BUGS 123) | NOT verified | NOT verified (Mecway 34 was not available). Verified on Mecway 35 (35.0.9802) in the Mecway window (10 Nov 2026) |
| Keep the Code-Aster base with a manifest, `keep_base` (V2026.9) | NOT verified | NOT verified: offline tests; with the setting off (default) mesh and `.comm` stay the same |
| Buttons "ParaView" and "AsterStudy" in the Results window and the convergence window, setting `salome_meca_dir` (V2026.10) | NOT verified | Mecway 35 (35.0.9802): verified in the Mecway window (11 Nov 2026); also started from a hidden Mecway (10 Nov 2026: ParaView 6.2.1 with a `.pvd`, AsterStudy *Results* with a `.rmed`); from the convergence window's Python: `.rmed`, `_xfem.rmed`, `_verfijnd.rmed` |
| Hiding failed elements, `hide_failed`; `failed` 1 from the step after the failure (V2026.11) | NOT verified | Mecway 35 (35.0.9802): verified in the Mecway window with `BezwijkenTrekstaaf` (11 Nov 2026); files also checked offline and with `BezwijkenTrekstaaf` (Code-Aster 17.4, splice under IronPython 2.7.9) |
| Convergence window under Mecway's taskbar button; long path over several lines (V2026.11) | NOT verified | Mecway 35 in Program Files: a test window with the same taskbar ID sat under Mecway's button, and the convergence window itself after a run (11 Nov 2026) |
| WARNING for a *Fixed support* on a node selection with shell or solid nodes, KNOWN_BUGS 135 (V2026.12) | NOT verified | NOT verified in the Mecway window: offline tests; that Mecway 35 (35.0.9802) leaves such nodes free was measured headless with Mecway's own solver on quad and hex nodes (11 Nov 2026; trusses from the manual, NOT measured); the `.comm` of all 578 comparable verification cases is the same |
| Results after Code-Aster's time limit: extra time after a `TimeLimitError`, time guard of the step loops (V2026.12) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (`StopTest_LongRun`, WE-12, 11 Nov 2026); linear and thermal analyses still lose the results (KNOWN_BUGS 137) |
| Hiding failed elements with core `liml_failed.py` 1.0.5: other node values follow the original, marker `failed_hidden`, supports stay in place (V2026.12) | NOT verified | NOT verified in the Mecway window: offline tests (CPython and IronPython 2.7.9) and the copy test against AdvancedToolsHub; that Mecway 35 keeps the marker on a save was measured outside the bridge |
| WARNING for an isotropic material without Young's modulus, KNOWN_BUGS 60 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; that Mecway computes such a material with E = 0 was seen headless in a Frequency model (13 Nov 2026) |
| WARNING for bonded shell faces (face to face, shell on solid), KNOWN_BUGS 128 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; the lap of two bonded plates measured headless with Code-Aster 17.4 and Mecway's own solver against a solid hex20 reference (13 Nov 2026) |
| WARNING for linear buckling with DKT/DST shells, naming `COQUE_3D`, KNOWN_BUGS 132 (V2026.13) | NOT verified | NOT verified in the Mecway window: offline tests; the T beam of BU-43c measured headless with Code-Aster 17.4 (DKT and `COQUE_3D`) and Mecway's own solver on the same mesh (13 Nov 2026) |
| Default `lin_solver_resi` 1e-5 instead of 1e-6 in linear static, nonlinear static, modal and buckling, KNOWN_BUGS 138, found and fixed in this release (V2026.13) | NOT verified | NOT verified in the Mecway window: measured headless with Code-Aster 17.4 (160 x 32 quad4 plate and hex20 lap compute, the lap equals Mecway; 40 x 8 plate bit-identical to 1e-6, 13 Nov 2026); the 293 verification cases whose `.comm` changes plus the fastest of every group: no status change |

"Verified" means the verification of §2 and a run in Mecway with that version. Comparisons
with Mecway's own solver in the other documents name the Mecway version they were measured
with; that is the version of the reference, not a limitation of the bridge.
