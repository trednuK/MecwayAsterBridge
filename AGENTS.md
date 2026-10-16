# AGENTS.md

Mecway → Code-Aster bridge: `.liml` → mesh (ASTER format) + `study.comm`/`.export` → Code-Aster →
results back in Mecway (by default in the `.liml` itself, `aster_results_export.py`). Entry point, architecture
and order of work are described in `Scripts/MecwayAsterBridgeMain.py`. The code is leading; keep the user docs
in `docs/` up to date.

Known bugs are listed in `KNOWN_BUGS.md`. If you find a bug that does not belong to your current task, do not
fix it, but add it there (in the format described at the top of that file). If you fix one, remove it there.
Planned extensions and the procedure for them are in `STAPPENPLAN.md` (run with `/stappenplan`).

## Runtime

- Runs in **IronPython 2.7.9** (Mecway). Write Python 2.7 code: no f-strings,
  type hints or `pathlib`; use `"{0}".format(x)`.
- Standard library only, plus `clr`/WinForms in `bridge_gui.py`. No pip packages.
- Exceptions (Code-Aster's Python 3): `aster_results_export.py` and
  `aster_spectrum.py`, `aster_acoustic_export.py`, `aster_acoustic_complex.py` (also scipy from the
  Code-Aster installation), `aster_cyclic.py`, `aster_fatigue.py` (inside the job) and
  the convergence window `aster_convergence_monitor.py` (separate process, tkinter). The
  parser `bridge_convergence.py` is shared and must work in both 2.7 and 3
  (test: `python tests/test_bridge_convergence.py`).
- `mw` and `solution` exist only in the main script; pass them as parameters to the `bridge_*` modules.
- Mecway API: only what is in Mecway's scripting documentation (Mecway manual;
  locally possibly `API_reference Mecway.txt`, copyright Mecway Ltd, not in the repo). There is no API to
  read loads/constraints, so take BCs, materials and selections from the
  `.liml` XML (`bridge_from_liml.py`). Code-Aster: v17.4.

## Branches and files

- Work on `develop`. The user updates `main` from `develop` (release); do not push `main` yourself.
- Mecway runs the scripts from the main checkout (the folder of this repo from which Mecway
  starts `MecwayAsterBridgeMain.py`). Do not switch branches there.
- `WorkDir/` is generated output (gitignored); test in a temporary folder.
  `TestFiles/*.liml` are test models.
- This repo is public: the content, commit message and time of every commit are public. Do not commit
  personal data or own paths (not even through a `bridge_utils.py` saved by the start screen, see
  below), and clear the author name in the metadata of Office and PDF files.
- Agreements and paths that apply to one PC only belong in `CLAUDE.local.md` (gitignored, read by Claude Code
  next to `CLAUDE.md`), not in this file.

## `bridge_utils.py` / `CONFIG_BRIDGE`

The start screen (`bridge_gui.save_to_bridge_utils`) rewrites this block line by line
with a regex. A diff here may therefore be a saved setting; a `.bak` is normal.

- One key per line: `"key":   value,`. Only lists may span several
  lines. Do not put expressions or variables in this block.
- A new setting: key in `CONFIG_BRIDGE` + entry in `GENERAL_SPECS`/`ANALYSIS_SPECS` (`bridge_gui.py`)
  + explanation (tooltip) in `bridge_glossary.SETTING_HELP`; a new choice value or code in `GLOSSARY`.
- A new document in `docs/` (and `docs/en/`) also goes into `bridge_docs.DOCS` (page Documentation).
- Paths without personal data: `exe_aster` defaults to `%LOCALAPPDATA%\code_aster\...`, `work_dir`
  defaults to `""` (= `WorkDir` next to `Scripts/`). Always read them through `bridge_utils.exe_aster_path()` and
  `work_dir_path()` (environment variables expanded, default work folder), never directly from `CONFIG_BRIDGE`.
- `BRIDGE_VERSION` (outside `CONFIG_BRIDGE`) is the version on the start screen and in the log; for a
  release also update `CHANGELOG.md`.

## Extending

| What | Where |
|---|---|
| BC/load | subclass of `BaseBC` in `bridge_bcs.py` (`parse_xml`, `to_aster_dict`) + `SUPPORTED_BCS` under the `.liml` tag name |
| Analysis type | `Scripts/AsterTemplate_<Name>.comm` + builder in `bridge_to_aster.py` + `SOLVER_BUILDERS_ASTER` + entry in `CONFIG_BRIDGE["analyses"]` |
| Result field | group in `RESULT_FIELD_SPECS` (`bridge_from_aster.py`; also the selection list on the start screen) + `FIELD_TABLE` in `aster_results_export.py` (route `liml`, default) + for route `tabel` POST_RELEVE_T with the same INTITULE in `bridge_to_aster._result_tables` |
| Section/material type | `_parse_geometric_props()` / material block in `bridge_from_liml.py`; OpenRadioss cards (PLAS_TAB, /FUNCT) in `bridge_radioss.py` |
| Code-Aster feature without Mecway input | user: `#ASTER` lines in Mecway's custom model definition (`bridge_custom.py`; examples in `docs/ASTER_regels_voorbeelden.md`) |

`model_data` (from `extract_aster_data_from_liml`, completed by `write_mesh`) is the
contract between the modules. Read optional keys with `.get()`.

## Pitfalls

- Mecway values have units (`"210 GPa"`, `"10000 mm⁴"`): always convert to SI with
  `parse_and_convert(val, type)`. An unknown unit comes back unchanged
  (with a WARNING in the log); a new unit belongs in the tables there.
- In the templates `str.format()` fills in the placeholders `{name}`. Write a literal
  brace as `{{ }}`.
- `bridge_mesh.py` writes the mesh directly from the `.liml` (no Gmsh: it truncated
  names to 8 characters). Group names in Code-Aster: letter first, only letters/digits/_,
  max. 24 characters; `bridge_mesh` renames in `model_data`, so use group names from
  `model_data`. `INTITULE` ≤ 16 characters.
- Output files of a run are named `<model>_<run_id><suffix>` (name of the Mecway file +
  timestamp): get the name from `bridge_utils.run_name(suffix)`, never use a fixed name. Without
  `set_run_log()` (smoke test) it is `study<suffix>`.
- `solution.set_variable()` expects one value per node of the last Mecway solve.
- `run_AsterSolver()` waits until Code-Aster has ended and returns an `AsterJob` (`state`,
  `exit_code`): with `wait_for_aster` = `"auto"` in the modal status window
  (`bridge_gui.run_status_dialog`, polls `AsterJob.poll()`), with `"confirm"` (or without
  Windows Forms) via `mw.message()`. End detection: the end marker of `aster_launch.bat`,
  else `DIAGNOSTIC JOB` in the `.mess`. `AsterJob.stop()` only kills the process tree of the
  cmd window it started (`taskkill /T`). Test: `python tests/test_bridge_wait.py`.

## Checking

A real run is only possible in Mecway. Tools without the Mecway GUI in `TestFiles/Tools/`: `run_ipy.ps1`
(run a script with Mecway's IronPython 2.7.9), `gui_cap.py` (main window offscreen to PNG), `mw_solve.py`
(let Mecway solve headless as a reference). Offline syntax check (Python 3; check Python 2.7 compatibility yourself):

```bash
cd Scripts && for f in *.py; do python -c "import ast,io;ast.parse(io.open('$f',encoding='utf-8').read())" || echo "ERROR: $f"; done
```

Also in `TestFiles/Tools/` (CPython 3):

- `python TestFiles/Tools/check_docs.py` checks the documentation: settings and defaults against
  `CONFIG_BRIDGE`, tooltips in both languages, links and anchors, `KNOWN_BUGS n` references, verification
  cases, § references and NL/EN parity of the docs (`--parity`: also the numbers per section). Must report
  0 findings.
- `TestFiles/Tools/StopTest_LongRun.liml`: `BezwijkenTrekstaafDynamisch.liml` with 1000 time
  steps (~95 s with Code-Aster 17.4), to test the Stop button of the status window in Mecway.
- `python TestFiles/Tools/check_code_unchanged.py <git-ref> [files...]` checks that a text-only change
  (comments, docstrings, INFO/SUCCESS log texts, comment lines in the `.comm` templates) leaves the code
  unchanged (syntax tree of `.py`, code lines and placeholders of `.comm`).

Smoke test liml → mesh/`.comm`/`.export` (CPython, temporary folder `T` with `model.liml`, e.g. a
copy of `TestFiles/Voorbeelden/Voorbeeld_A.liml` (static) or `TestFiles/BezwijkenTrekstaaf.liml`
(nonlinear); the templates are file names in `CONFIG_BRIDGE` and are looked up in the folder of the
scripts, `bridge_utils.template_path`):

```python
import sys, shutil; sys.path.insert(0, "Scripts")
import bridge_utils as u; u.CONFIG_BRIDGE["work_dir"] = T   # in memory only
from bridge_from_liml import extract_aster_data_from_liml
from bridge_mesh import write_mesh
from bridge_to_aster import generate_AsterSolver_files
for name in ("lin_static_3d", "nonlin_static_3d"):
    u.CONFIG_BRIDGE["active_analysis"] = name
    md = extract_aster_data_from_liml(T + "/model.liml")
    assert write_mesh(T + "/model_mesh.mail", md)   # without Mecway: faceid table
    assert generate_AsterSolver_files(T, md, T + "/model_mesh.mail", "test.resu")
```

Then look at `T/study.comm` and `T/bridge_log.txt`. Do not call the save functions of
`bridge_gui` (they rewrite `bridge_utils.py`).

## Conventions

- License: MPL-2.0 (`LICENSE`). A new source file (.py, .comm) gets at the top (after an
  optional coding line) the header from `Scripts/bridge_utils.py` (Copyright + MPL-2.0 notice).

- English for developer text: code comments, docstrings, comments in the `.comm` templates (and so in
  the generated `study.comm`), INFO/SUCCESS log lines, `AGENTS.md`, `KNOWN_BUGS.md`, `STAPPENPLAN.md`
  and commit messages. Log with `log("INFO|WARNING|ERROR|SUCCESS: ...")`. Older Dutch text may still
  occur; translate it when you touch it.
- Text for the user stays bilingual (`CONFIG_BRIDGE["language"]`, `nl`/`en`): start screen,
  `mw.message()`, WARNING/ERROR lines, `skipped_loads`, convergence window:
  `log(tr("WARNING: ... {0}", "WARNING: ... {0}").format(x))` with `tr` from `bridge_utils` (Dutch first,
  then English); same prefix and placeholders in both.
- User documentation is bilingual too: Dutch in `docs/`, English in `docs/en/`, with the same structure
  (`check_docs.py` checks the parity); update both.
- Fatal error in a module: `log("ERROR: ...")` and return `None`/`False`; `main()` then stops with `mw.message()`.
- Support Code-Aster behaviour in a comment with a source (U doc, catalogue, `.F90`), otherwise "NOT verified".
