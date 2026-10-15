# Thermal analyses (Mecway T30 / T31)

*Nederlandse versie: [Thermisch.md](../Thermisch.md)*

What the bridge does with a thermal Mecway model (`Scripts/bridge_thermal.py`,
template `Scripts/AsterTemplate_Thermique.comm`). Code-Aster 17.4.

## 1. Analysis and solver

| Mecway | Bridge (`active_analysis`) | Code-Aster |
|---|---|---|
| T30, thermal steady state | `ther_3d` (also via "auto") | `THER_LINEAIRE` `TYPE_CALCUL='STAT'` |
| T31, thermal transient | `ther_3d` (also via "auto") | `THER_LINEAIRE` `TYPE_CALCUL='TRAN'` |
| with radiation, convection/radiation on a shell face or a temperature-dependent material | `ther_3d` | `THER_NON_LINE` (material `THER_NL`) |
| T31 with a moving weld source (`#ASTER-LASBRON`) | `ther_3d` | as above, with a source `AFFE_CHAR_THER_F` ([Welding.md](Welding.md)) |
| T31 with a *Thermal stress* (and mechanical supports) | `ther_3d` | as above, then `STAT_NON_LINE` with the temperature as `AFFE_VARC` (residual stress and distortion, [Welding.md](Welding.md) §9) |

- **Celsius.** Code-Aster's `RAYONNEMENT` works with `T + 273.15` (U4.44.02), so
  the whole analysis is in °C. Mecway values (K, °C or °F) are converted; the
  result `temperature` goes back to Mecway in Kelvin.
- **Time steps (T31):** `<timesteps timeperiod stepsize>` (or
  `timepointsincrement`): fixed step, every step is written (including t = 0, the
  initial state).
- **Initial temperature:** `<initialconditions><temperature2>`; nodes without an
  initial temperature start, as in Mecway, at 0 K (manual v33 §6.7.2). The bridge
  warns if there is no initial temperature.
- **Results:** only via `result_route = "liml"`: `temperature` (nodes) and the
  heat flux `heatfluxx/y/z` + `heatfluxmag` (`FLUX_NOEU` = −λ grad T; nodes).

## 2. Settings (start screen, page "Thermal")

| Setting (key) | Default | Meaning |
|---|---|---|
| "Time scheme THETA (0 .. 1)" (`theta`) | 0.57 | `SCHEMA_TEMPS` THETA, transient only (0 = explicit, 0.5 = Crank-Nicolson, 1 = implicit Euler); Code-Aster default 0.57 (catalogue `ther_lineaire.py`). Mecway uses Crank-Nicolson with the load at the end of the step: 0.5 follows Mecway exactly for a constant load (§5). |
| "Max. Newton iterations (ITER_GLOB_MAXI)", "Convergence RESI_GLOB_RELA", "NEWTON REAC_ITER" (`newton_max_iter`, `convergence_resi_rela`, `newton_reac_iter`) | 20, 1e-6, 1 | `THER_NON_LINE` (`CONVERGENCE`, `NEWTON`) and the mechanical `STAT_NON_LINE` of the thermal → mechanical chain. |
| "COMPORTEMENT DEFORMATION", "Strain definition hardening curve" (`deformation`, `plastic_strain_definition`) | PETIT, auto | only the thermal → mechanical chain (T31 with a Thermal stress, [Welding.md](Welding.md) §9.3). |
| "MUMPS NPREC (-1 = check off)" (`solver_nprec`) | 8 | MUMPS NPREC. |
| "Result fields to Mecway" (`fields`) | temperature, heat_flux | which fields are sent to Mecway. |
| "Time limit run_aster [s]" / "Memory limit run_aster [MB]" (`time_limit`, `memory_limit`) | 1800 s, 4096 MB | limits of the Code-Aster job. |

## 3. Translation of elements and loads

| Mecway | Code-Aster |
|---|---|
| solid element | `MODELISATION='3D'`, `THER` (LAMBDA, RHO_CP = ρ·cp) |
| shells in parallel planes | `MODELISATION='PLAN'` with factor f = t / t_ref on LAMBDA, RHO_CP and all loads (t_ref = 1 m with solids, otherwise the most used thickness); a sub-group per thickness; the flux is computed by `CALC_CHAMP` with the real λ. If the shells are not in Z = constant, the `.comm` rotates the mesh (`MODI_MAILLAGE ROTATION`) and the flux back to global axes; alarm MODELE1_53 is then normal |
| beam / fin element, shells that are not all parallel | **not translated** (Code-Aster has no thermal 1D element; the thermal `COQUE` has three temperatures through the thickness) |
| `temperature2` (nodes, faces, elements) | `TEMP_IMPO` (time table: `AFFE_CHAR_THER_F`) |
| `nodetemperature` | `TEMP_IMPO` per node group |
| `heatflux` on faces | `FLUX_REP FLUN` (solid, shell edge); shell face: `SOURCE` q/t; faces 5 and 6 of a shell in one selection: both sides (factor 2, like Mecway) |
| `heatflow` on faces / elements | total ÷ area (shell edge: length × thickness) or ÷ volume, then as above |
| `heatflow` on nodes | Q/N per node (manual §9.27) as a source field M⁻¹F (`MASS_THER`, `RESOUDRE`, `SOURCE SOUR_CALCULEE`); time table via `FONC_MULT` |
| `heatgeneration` | `SOURCE` |
| formula as a value (x, y, z, t; `temperature2`, `heatflux`, `heatgeneration`, `convectionbc`, `radiationbc` on solid faces and shell edges, `heatflow` in t only) | `FORMULE` of X, Y, Z, INST in `AFFE_CHAR_THER_F`, with the units from the Mecway attributes (`unit`, `positionunit`, `timeunit`); steady state: t = 1 s. Verification WE-03/WE-06 ([Verification.md](Verification.md) §8) |
| temperature-dependent material (`TempDependent`: λ(T), c(T)) | `THER_NL` with `DEFI_FONCTION` of TEMP (PROL constant, as Mecway §8.6); ρc table extended and refined every 10 degrees ([Welding.md](Welding.md) §6) |
| moving weld source | `#ASTER-LASBRON` ([Welding.md](Welding.md)) |
| `convectionbc` | `ECHANGE` (shell face: `SOUR_NL`; with a time table a source plus a sink with `FONC_MULT`) |
| `radiationbc` | `RAYONNEMENT` σ = 5.670374419e-8 (shell face: `SOUR_NL`, tabulated every 5 °C) |
| bonded contact (`contact2`) *Tie* / *Constraint equations* | `AFFE_CHAR_THER` `LIAISON_MAIL`: the temperature of each slave node is the one at its projected point on the master face (manual §9.9.1); also non-conforming meshes and shells (`PLAN`) among themselves |
| bonded contact *Elastic* (thermal resistive layer, *Thermal conductance per unit area* h) | `AFFE_CHAR_THER` `ECHANGE_PAROI` `COEF_H` = h between the faces of both sides (flux h·ΔT across the bond). Only solid faces that are node-to-node opposite each other; otherwise (non-conforming, shells, no h) ideally bonded (`LIAISON_MAIL`) with a WARNING and in the not-translated list |
| bonded contact in a model with solids **and** shells | **not translated** (ERROR): Code-Aster cannot apply `LIAISON_MAIL` (CHARGES7_6) or `ECHANGE_PAROI` (CHARGES6_2) then; use shared nodes (*Merge nearby nodes*) |
| `forcedconvection`, `massflowrate`, cavity radiation, formulas for convection/radiation on a shell face, a formula in x, y, z for a total `heatflow` or as an initial temperature, formulas in material properties | **not translated** (reported) |

A steady-state analysis with a time table takes the value at t = 1 s, like Mecway
with CCX (Mecway's internal solver treats a table as 0; the bridge then warns). A
`temperature2` with a time interval (`starttime`/`endtime` ≠ 0) is applied for the
whole analysis (reported).

**Bonded contact.** In a T31 with *Thermal stress* (thermal → mechanical chain) the
thermal part gets the thermal coupling above and the mechanical part the usual
mechanical `LIAISON_MAIL` (TYPE_RACCORD, [Mecway_features.md](Mecway_features.md));
with *Elastic* the mechanical layer is rigid (reported), the thermal resistance is
translated. Mecway's internal solver (Mecway 34, without GUI) solved *Tie* and
*Elastic* in a T30 without any coupling (300 / 400 K on both sides); with the CCX
solver it did couple (350 K, and 340 / 360 K with h = 2000 W/m²K), equal to the bridge
(TH-04a/c).

## 4. Additional checks (Code-Aster 17.4, offline)

The reproducible tests with tolerances and references are in
[Verification.md](Verification.md) §8 (TH-01 .. TH-04). In addition, the translation
was checked by hand on these models (analytical values according to Incropera et al.
(2007), ch. 3; ConductionConvectionRadiation according to the Mecway manual §11.13):

| Model | Expected | Code-Aster via the bridge |
|---|---|---|
| ConductionConvectionRadiation (shell + solid; fin left out) | T right 380.2783 K, q = 3591.65 W/m² (manual §11.13) | 380.278 K, 3591.65 W/m² in shell and solid |
| bar 0.1 m, 400/300 K, k = 50 | linear, q = 50 000 W/m² | exact |
| same, 1e6 W/m³ (`heatgeneration` and `heatflow` 10 W on the elements), ends 300 K | T_max = 325 K | 325.000 K |
| bar as fin, h = 25 on sides and end | T(L) = 344.51 K, T(L/2) = 357.32 K | 344.47 / 357.28 K |
| shell 2 mm, 1e6 W/m³ / 1000 W/m² on the face | 325 K / 312.5 K | 325.000 / 312.500 K |
| shell, convection h = 25 on one face | T(L) = 300 + 100/cosh(mL) = 339.48 K (fin, m = √(h/(k·t)), insulated tip) | 339.42 K |
| shell, convection on the edge x = L | q = 2380.95 W/m², T(L) = 395.238 K | exact |
| shell + solid (f = 0.01) in series | same heat flow in both | 4.71 W in both |
| bar, `heatflow` 100 W for 10 s, insulated | mean rise 27.87 K | 27.87 K |
| bar, convection h = 1000 with time table T∞ | lumped capacitance: ≈ 382.8 K after 20 s | 381.7–384.8 K |
| OscillatingHeatFlow (quad8 shell, `heatflow` table) | mean rise Q/(ρcV) = 18.009 K | 17.998 K (t = 40 and 80 s) |

## 5. Comparison with Mecway's own thermal solver

Mecway solves without the GUI: `mecway.exe model.liml solve`, with
`<solutionfile filename="...\x_sol.liml" />` in the `.liml` (the solution only
contains `temperature`, no heat flux). Measured with Mecway 33 (KNOWN_BUGS 14 in
`KNOWN_BUGS.md`, Dutch):

| Case | Max. difference bridge – Mecway |
|---|---|
| steady state: convection, flux, heatflow, source, edge loads, shell + solid, also one selection over two thicknesses and loads on both sides | ≤ 1e-11 K |
| radiation (table every 5 °C) | 1e-3 K |
| ConductionConvectionRadiation | 1.8e-6 K |
| `heatflow` on nodes (solid, two thicknesses, mixed) | ≤ 2e-12 K |
| shells in the XZ plane and in an inclined plane | ≤ 3e-12 K |
| steady state with a time table, Mecway with CCX | 4e-4 K |
| transient, constant load, `theta` = 0.5 | 1.5e-5 K |
| OscillatingHeatFlow (1601 steps), `theta` 0.57 / 0.5 / 1.0 | max 1.40 / 1.49 / 2.61 K (RMS 0.13 / 0.14 / 0.06 K) |
| time-dependent convection/radiation on a shell face, `theta` 0.5 | 0.10–0.21 K |
| bonded contact *Constraint equations*, non-conforming (solids TH-04b, shells TH-04d; Mecway 34) | 0.0024 / 0.0056 K |
| bonded contact *Tie* and *Elastic* (TH-04a/c), Mecway 34 with CCX | < 0.002 K |

Mecway's transient scheme is Crank-Nicolson (θ = 0.5) with the load at the end of
the step; Code-Aster takes the θ-weighted average. With a time table a difference of
the order of the step remains (with the table shifted by half a step,
OscillatingHeatFlow drops to RMS 0.007 K). The default 0.57 stays (damped;
Crank-Nicolson gave non-monotonic first steps in Mecway).

## 6. Assumptions

- The analysis is in °C (because of `RAYONNEMENT`); temperatures go back to Mecway in
  K.
- A shell is a `PLAN` layer with factor f = t / t_ref on λ, ρ·cp and the loads; there
  is no temperature variation through the thickness (as in Mecway, manual §7.4).
- Steady state with a time table: the value at t = 1 s (as Mecway with CCX). A
  `temperature2` with a time interval applies to the whole analysis.
- Nodes without an initial temperature start at 0 K (as in Mecway).
- A formula as a value is evaluated in the Gauss points at every step (θ-weighted);
  in steady state with t = 1 s. Mecway's internal solver applies the load at the end
  of the step (KNOWN_BUGS 14; [Welding.md](Welding.md) §5).
- Temperature-dependent material: λ(T) and ρc(T) linear between the table points,
  constant outside (as Mecway); the ρc table is refined so that the enthalpy of
  `THER_NON_LINE` is right ([Welding.md](Welding.md) §6).
- `heatflow` on nodes: Q/N per node (manual §9.27), distributed as a source field.
- Radiation on a shell face is tabulated as a function of T per 5 °C (linearly
  interpolated; difference from Mecway ~1e-3 K, §5); convection on a shell face is
  exact (linear in T).
- Transient results are written in single precision (~3e-5 K at 380 K).
- `theta` = 0.57 is a deliberate choice (damped, no overshoot with a coarse step,
  [Verification.md](Verification.md) TH-02); 0.5 if Mecway must be followed exactly.

## 7. References

- EDF R&D (n.d.). *Code_Aster documentation, version 17.4*: U4.43.01 (`DEFI_MATERIAU`
  `THER`/`THER_NL`), U4.44.02 (`AFFE_CHAR_THER`), U4.54.01 (`THER_LINEAIRE`), U4.54.02
  (`THER_NON_LINE`). https://www.code-aster.org
- Incropera, F.P., DeWitt, D.P., Bergman, T.L. & Lavine, A.S. (2007). *Fundamentals of
  Heat and Mass Transfer* (6th ed.). Hoboken: Wiley.
- Mecway (2026). *Mecway manual*, version 33 (`manual.pdf` in the installation
  folder). Cited as "manual §…".
