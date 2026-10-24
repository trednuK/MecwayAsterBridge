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
| Selection names with spaces (models from Mecway 33) | allowed | Mecway 34 replaces the spaces by `_` when it opens such a model and then loses the reference in a contact (`selectionmaster=""`, seen 22 October 2026); the bridge stops before Code-Aster with an ERROR that says so where the contact counts (nonlinear static and dynamics; bonded contact in every analysis), elsewhere it gives a WARNING (Mecway ignores unilateral contact there too). Select the contact faces again. The example models use names without spaces. |

"Verified" means the verification of §2 and a run in Mecway with that version. Comparisons
with Mecway's own solver in the other documents name the Mecway version they were measured
with; that is the version of the reference, not a limitation of the bridge.
