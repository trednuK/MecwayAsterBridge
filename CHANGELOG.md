# Changelog

## Unreleased (develop)

- **Bonded (Tie) contact between shells** now works: a shell face or edge glued onto a
  shell face no longer stops with a singular matrix (`FACTOR_11`); the drilling rotation is
  left out of `LIAISON_MAIL`. Example `TestFiles/Voorbeelden/Voorbeeld_T.liml`, verification
  LS-07a–e, docs §3.10 of the contact settings. Skewed or curved masters: KNOWN_BUGS 91.
- **New overview** of which Mecway functionality the bridge does and does not translate
  (`docs/en/Mecway_features.md`, Dutch `docs/Mecway_functionaliteit.md`), also on the
  Documentation page of the start screen.
- **Bonded contact in thermal analyses** (T30/T31) is now translated instead of silently
  dropped (KNOWN_BUGS 88): *Tie* / *Constraint equations* → `AFFE_CHAR_THER`
  `LIAISON_MAIL`, *Elastic* → thermal resistance `ECHANGE_PAROI` with Mecway's *Thermal
  conductance per unit area* (conforming solid faces; otherwise ideally bonded with a
  warning). Models with solids and shells together: ERROR (Code-Aster cannot couple
  them). Verification TH-04a–d.
- KNOWN_BUGS 88–90 recorded (bonded contact in thermal analyses, node temperature in
  mechanical analyses, quadratic shell as bonded master).
- **Version check** (warning only): the log shows the Mecway version (from the `.liml`) and the
  Code-Aster version (launcher path, then the `.mess`); an untested version gives a WARNING. New page
  *After an update of Mecway or Code-Aster* (`docs/en/After_an_update.md`).
- README: Mecway 34, acknowledgements. Verification: 277 test cases, 1643 checks.

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
