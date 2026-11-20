# MecwayAsterBridge

Solve a [Mecway](https://mecway.com) model with [Code_Aster](https://www.code-aster.org)
and get the results back in Mecway.

You build the model in Mecway as usual (mesh, materials, loads, constraints, selections)
and start the bridge from Mecway's *Tools* menu. The bridge reads the `.liml`, writes a
Code-Aster mesh, `.comm` and `.export`, starts Code-Aster in a separate window and loads
the results back into the Mecway model, where you post-process them with Mecway's own
tools. Features that Mecway has no input for can be added per model with `#ASTER` lines
in Mecway's *Custom model definition*.

[![Architecture diagram](https://gitdiagram.com/diagram-badge.svg)](https://gitdiagram.com/trednuk/mecwayasterbridge?utm_source=readme&utm_medium=badge)

Version: **V2026.18** (see [`CHANGELOG.md`](CHANGELOG.md)). Dutch documentation:
[`docs/Handleiding.md`](docs/Handleiding.md). Large models can use the optional
`aster_fast` helper (below). The version shown on the start screen stays **V2026.18**.

**Provided as is, without warranty (MPL-2.0, sections 6 and 7). Always check results
independently before you rely on them.**

## Requirements

- **Windows** with **Mecway 33, 34 or 36** (the bridge runs in Mecway's built-in IronPython 2.7
  scripting environment). Developed and verified with Mecway 34; Mecway 36 (36.0.9815, a release
  candidate of Mecway) was verified headless, with ten checks in the Mecway window with
  V2026.14 and with further checks in the window for V2026.15 (19 Nov 2026); Mecway 33 is
  supported, last fully verified with V2026.2 (features added since are
  verified with Mecway 34, or measured with Mecway 35 or 36, see
  [After an update](docs/en/After_an_update.md#6-mecway-versions--compatibility)). Mecway 35 is not
  in the list of tested versions (the bridge warns; single features were checked on it, see the
  same table); older versions have not been tested.
- **Code-Aster 17.4 for Windows**. Windows builds are available from
  <https://simulease.com/en/download/> (MSI installer "Code_Aster 2025", which installs
  version 17.4; accessed 6 October 2026). The official site
  [<https://www.code-aster.org>](https://open-simulation-center.org/downloads/code_aster/code_aster/17.4.0) does also list a Windows version.
- Nothing else to install with `pip`. The bridge uses only the Python that comes with
  Mecway and with Code-Aster. For a large mesh you can build `Scripts\aster_fast.exe`
  (see Installation). Without that file the bridge still runs; preparing the
  Code-Aster files is just slower.

## Installation

1. **Install Code-Aster.** With the MSI package the launcher ends up in
   `%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat`, which is the bridge's
   default; nothing needs to be set if you keep that location.
2. **Get the bridge.** Download and unpack the Windows release of
   [V2026.18](https://github.com/larsmei/MecwayAsterBridge/releases/tag/V2026.18),
   or clone this repository:
   ```
   git clone https://github.com/larsmei/MecwayAsterBridge.git
   ```
   The zip already contains `Scripts\aster_fast.exe`. A clone does not. To build
   the helper yourself you need [Rust](https://rustup.rs/) (the MSVC or GNU
   Windows target):
   ```
   cargo build --release --manifest-path rust/aster_fast/Cargo.toml
   copy rust\aster_fast\target\release\aster_fast.exe Scripts\
   ```
   Keep the folder in a fixed place: Mecway runs the scripts from there, and Code-Aster
   loads `Scripts/aster_results_export.py` from the same place during a run. Use a short
   path (work folder plus file name must stay below 259 characters).
3. **Add the script to Mecway.** As described in the Mecway manual (§16.2 Scripts):
   *Tools* > *Scripts...* > *New*, and choose the existing file
   `Scripts\MecwayAsterBridgeMain.py`. The script then appears as an item in the *Tools*
   menu; that is where you start the bridge. No other scripts need to be added.

### Large meshes (`aster_fast.exe`)

On a model of about 800,000 nodes, IronPython 2.7 can spend more than half an hour
building the files before Code-Aster starts. `Scripts\aster_fast.exe` does the two slow
steps outside IronPython: it reads the mesh out of the `.liml` (results under `<solution>`
are still skipped), counts the free faces of the solids and writes the Code-Aster `.mail`.
It also reads a `.rmed` and writes the Mecway result fragment (`aster_fast med`) when
results are taken from the MED file on the host. The mesh text is the same as the pure
Python writer. Materials, loads and constraints are
still read by the bridge. While those steps run, the **Preparing** window shows each step
and its status; it closes when the Code-Aster status window opens.

The helper is not required. This release's zip includes `Scripts\aster_fast.exe`
(built for Windows). To build it yourself, use the commands above and copy
`aster_fast.exe` next to `MecwayAsterBridgeMain.py`; the bridge then uses it on
its own. If the file is missing, or the environment variable `ASTER_FAST` is `0`
before Mecway starts, the bridge uses Python only. `ASTER_FAST` may also be the
full path of the program, if you do not want it inside `Scripts\`.

The program needs no settings screen. A log line `Mesh read with aster_fast` means it was
used.

## First run

1. Open a model in Mecway, for example a copy of
   [`TestFiles/Voorbeelden/Voorbeeld_C.liml`](TestFiles/Voorbeelden/Voorbeeld_C.liml)
   (two small hex8 blocks with contact, nonlinear static). Work on a copy: the bridge
   saves the model and writes the results into it (the previous version is kept as
   `.liml.bak`).
2. *Tools* > `MecwayAsterBridgeMain`. The **start screen** opens:
   - **General > Taal / Language**: `en` (English, default) or `nl` (Dutch);
   - **General > Code-Aster launcher (run_aster.bat)**: the path to `run_aster.bat`.
     Environment variables such as `%LOCALAPPDATA%` are allowed. If the file does not
     exist, the status box says so; choose the file with *Browse...*;
   - **General > Work folder**: where the run files go (`.comm`, `.mess`, results, log).
     Empty means `WorkDir` next to the `Scripts` folder; it is created when needed;
   - the active analysis follows the Mecway analysis type (`auto`); each analysis has
     its own page with settings. Hover over a setting for an explanation.
3. Click **Start**. A **Preparing** window shows each step until Code-Aster starts
   (reading the model, writing the mesh, writing `.comm` and `.export`), with counts and
   the elapsed time. Code-Aster then runs in a separate window; the convergence window shows
   the progress. A status window in Mecway shows the elapsed time and the current step,
   with a *Stop...* button; Mecway is locked until the run has finished. When Code-Aster
   has finished, the status window closes by itself, the model is reopened with the
   Code-Aster results, and the start screen comes back with the outcome and any messages.
   (With *General > Waiting for Code-Aster* = `confirm` you click OK in Mecway yourself
   when Code-Aster has finished, as in earlier versions.)

Settings are saved in `Scripts/bridge_utils.py` (`CONFIG_BRIDGE`) when you click Start
or Results...; the defaults and why they were chosen are in
[`docs/en/Default_settings_and_assumptions.md`](docs/en/Default_settings_and_assumptions.md).
The full workflow is in the [user guide](docs/en/UserGuide.md); the same documents can be
read on the *Documentation* page of the start screen.

## Features

| Topic | English | Dutch |
|---|---|---|
| Workflow, start screen, what is translated, files, errors | [User guide](docs/en/UserGuide.md) | [Handleiding](docs/Handleiding.md) |
| Which Mecway features are and are not translated (analysis types, loads, constraints, contact, elements, materials, results, settings) | [Mecway features](docs/en/Mecway_features.md) | [Mecway-functionaliteit](docs/Mecway_functionaliteit.md) |
| Linear and nonlinear static, implicit and explicit dynamics: contact, plasticity, large displacements, convergence window | [Settings contact and nonlinear](docs/en/Settings_contact_and_nonlinear.md) | [Instellingen contact en niet-lineair](docs/Instellingen_contact_en_nietlineair.md) |
| Element failure | [Failure](docs/en/Failure.md) | [Bezwijken](docs/Bezwijken.md) |
| Thermal, steady state and transient; thermo-mechanical | [Thermal](docs/en/Thermal.md) | [Thermisch](docs/Thermisch.md) |
| Welding: moving heat source, residual stress, distortion, metallurgy (phases, hardness), filler material that is born | [Welding](docs/en/Welding.md) | [Lassen](docs/Lassen.md) |
| Modal analysis (also prestressed and cyclic symmetry), linear and nonlinear buckling | [Modal and buckling](docs/en/Modal_and_buckling.md) | [Modaal en knik](docs/Modaal_en_knik.md) |
| Mode superposition and harmonic response | [Mode superposition](docs/en/Mode_superposition.md) | [Respons op modale basis](docs/Respons_op_modale_basis.md) |
| Acoustics (cavity modes, harmonic) and vibroacoustics | [Acoustics](docs/en/Acoustics.md) | [Akoestiek](docs/Akoestiek.md) |
| Response spectrum (earthquake, shock) | [Response spectrum](docs/en/Response_spectrum.md) | [Spectrumanalyse](docs/Spectrumanalyse.md) |
| Error estimator and adaptive mesh refinement | [Error estimator](docs/en/Error_estimator.md) | [Foutschatter](docs/Foutschatter.md) |
| Fracture mechanics: K and G along a meshed crack, XFEM crack without a mesh | [Fracture mechanics](docs/en/Fracture_mechanics.md) | [Breukmechanica](docs/Breukmechanica.md) |
| Fatigue: damage and life (Wöhler, rainflow, Miner, critical plane, Manson-Coffin) | [Fatigue](docs/en/Fatigue.md) | [Vermoeiing](docs/Vermoeiing.md) |
| The real shape of a general section on the beams, with the results on it | [User guide §4.3](docs/en/UserGuide.md#43-the-shape-of-a-general-section) | [Handleiding §4.3](docs/Handleiding.md#43-de-vorm-van-een-general-section) |
| Your own Code-Aster input (`#ASTER` lines) | [ASTER lines with examples](docs/en/ASTER_lines_examples.md) | [ASTER-regels met voorbeelden](docs/ASTER_regels_voorbeelden.md) |
| Code-Aster messages: cause and solution | [Code-Aster error messages](docs/en/CodeAster_error_messages.md) | [Foutmeldingen Code-Aster](docs/Foutmeldingen_CodeAster.md) |
| Verification | [Verification](docs/en/Verification.md) | [Verificatie](docs/Verificatie.md) |
| After an update of Mecway or Code-Aster: version warning, checking a new version | [After an update](docs/en/After_an_update.md) | [Na een update](docs/Na_een_update.md) |

The start screen, the messages, the WARNING/ERROR lines in the log, the convergence window and
the user documentation are available in English and Dutch. Developer-facing text is in English
only: INFO/SUCCESS lines in the log, comments in the code and in the generated `.comm`,
`KNOWN_BUGS.md` and `STAPPENPLAN.md`.

## Verification

The chain Mecway model → bridge → Code-Aster 17.4 → results is checked with
**579 test cases and 3072 checks** against analytical solutions and recognised
benchmarks (linear and nonlinear static, dynamics, modal, buckling, thermal, welding,
acoustics, fracture, fatigue and more), including mesh-convergence series. At the last
regression 3066 checks were within tolerance and 6 outside it because of a documented
limitation; none unexpected. In addition, 19 official Code-Aster validation tests were
run on the installation. Method, tolerances, results and how to rerun them:
[`docs/en/Verification.md`](docs/en/Verification.md) (scripts in
`TestFiles/Verificatie/`, `python run_verificatie.py`).

## Known limitations

Known deviations from Mecway and limitations of the translation are listed, with their
status, in [`KNOWN_BUGS.md`](KNOWN_BUGS.md). Among them: 2D and axisymmetric analyses
only in part (KNOWN_BUGS 126), not every Mecway load or constraint is translated (the bridge
reports what it skipped), Mecway has no scripting API for loads, so everything is read
from the `.liml` file, and a real run always needs Mecway and Code-Aster on Windows.

## Folders

- `Scripts/` – the bridge: `MecwayAsterBridgeMain.py` (started from Mecway), the
  `bridge_*.py` modules, the `aster_*.py` scripts that run inside the Code-Aster job and
  the `.comm` templates. The Windows release also puts `aster_fast.exe` here; that file
  is not stored in Git
- `rust/aster_fast/` – source of `aster_fast` (no library dependencies). Build instructions
  are under Installation
- `docs/` (Dutch) and `docs/en/` (English) – documentation
- `TestFiles/` – test models; `TestFiles/Voorbeelden/` – example models of the `#ASTER`
  documentation; `TestFiles/Verificatie/` – verification set
- `tests/` – offline unit tests (`python tests/test_*.py`)
- `WorkDir/` – default work folder (not in Git)

## License

MecwayAsterBridge is licensed under the **Mozilla Public License 2.0** (MPL-2.0), see
[`LICENSE`](LICENSE). In short (the licence text itself is binding): use, modification
and distribution are allowed, also commercially; modified files of the bridge that you
distribute stay under MPL-2.0 (file-level copyleft); the bridge may be part of a larger,
also proprietary, work. MPL-2.0 is compatible with the GNU GPL, which matters because
`aster_results_export.py` runs inside the Code-Aster job and imports `code_aster`.

Code-Aster itself (EDF R&D) is licensed under the GNU GPL version 3 or later and is
**not** included; you install it separately. Mecway is commercial software of Mecway Ltd
and is not included either.

## Acknowledgements

- This work was inspired by **Efficient** from Moonish Engineering:
  <https://engineering.moonish.biz/software/efficient.html>.
- The reading of Mecway 34's *Element orientation* cards and the explicit beam orientation for every beam
  were found in the fork by **MishalTPC**: <https://github.com/mishal0488/MecwayAsterBridge>. The beams
  with large rotations (`elem_beam` = `POU_D_T_GD`: the Code-Aster route and the benchmarks GB-01 to
  GB-03) come from the same fork, as do ideas for the flexible joint: the benchmark for the joint with
  all rotations free under large rotations, the joint on offset beams and showing preparation errors
  directly in the status box.
- Want to learn more about Code-Aster and how to use its commands? Use the work of
  **Jean-Pierre Aubry**: <https://jean-pierre-aubry.ouvaton.org/downloadcabooks.html>.

## Trademarks

Mecway is a product of Mecway Ltd. Code_Aster is a trademark of EDF. This project is not
affiliated with or endorsed by Mecway Ltd or EDF.

## References

- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*
  (installed with Mecway as `manual.pdf`), §16.2 Scripts.
- Simulease. *Download* (Code_Aster for Windows). <https://simulease.com/en/download/>,
  accessed 6 October 2026.
- EDF R&D. *code_aster*. <https://www.code-aster.org>, accessed 6 October 2026.
