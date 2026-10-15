# Modal analysis and linear buckling

*Nederlandse versie: [Modaal_en_knik.md](../Modaal_en_knik.md)*

The bridge solves two eigenvalue problems with Code-Aster `CALC_MODES` (EDF R&D,
U4.52.02):

| Mecway analysis | Bridge analysis (page) | What Code-Aster computes | Result in Mecway |
|---|---|---|---|
| Frequency (V30) | `modal_3d` ("Modal") | stiffness K and mass M (`ASSEMBLAGE`), `CALC_MODES`; with loads first `MECA_STATIQUE` and then K + K_g (prestress, §2.5) | per mode the natural frequency (Hz) and the mode shape (optionally the stresses, §1.4) |
| Buckling (B30) | `buckling_3d` ("Buckling") | `MECA_STATIQUE` with the loads, geometric stiffness Kg from the stresses (`RIGI_GEOM`), `CALC_MODES TYPE_RESU='MODE_FLAMB'` | per mode the buckling factor and the buckling mode shape |

The results appear in Mecway just like Mecway's own solution: under *Solution* a list
*Mode 1, Mode 2, ...* with the frequency or the buckling factor (the same `<mode>`
format in the `.liml`). General operation of the bridge: [`UserGuide.md`](UserGuide.md).
Nonlinear buckling (stability per step with `CRIT_STAB`, buckling mode as
imperfection) in a nonlinear static analysis: §5.
Modes with damping (damped frequency and damping ratio per mode, as an option): §6.
Modes of a cyclically symmetric structure from one sector (Mecway's *Cyclic
symmetry*): §7.
The response in time on these modes (Mecway's *Dynamic Response* with *Mode
superposition*): [`Mode_superposition.md`](Mode_superposition.md).

## 1. Step-by-step workflow

### 1.1 In Mecway: the model

1. **Analysis type.** Choose *Frequency* (modal) or *Buckling* in the analysis
   settings.
2. **Number of modes.** The bridge computes exactly that many modes. If it is missing,
   the setting "Number of modes (without maxmode in Mecway)" on the Modal or Buckling page applies. For a loose
   (unsupported) model, count the rigid modes: up to 6 modes with ~0 Hz.
3. **Shift point** (buckling only, in Mecway). This is a setting of Mecway's own
   solver (Mecway Ltd., 2026, §6.6), not a search centre: Mecway's BucklingPlate with
   shift 1000 simply gave the smallest factors (7…12) in Mecway. The bridge does not
   use it (INFO in the log) and, as Mecway does, always looks for the smallest
   buckling factors (§2.2).
4. **Material.**
   - Modal: give every material a **density**. Without density there is no mass and
     the log shows a WARNING. Point masses (*Mass*, *Rotational inertia*) are included.
   - Buckling: density is only needed if gravity is one of the loads.
5. **Supports.** Fixed, pinned, displacement, node rotation, symmetry, frictionless,
   couplings and springs are used as in the static analysis. For modal only the
   constrained degrees of freedom matter, not the value of a prescribed displacement.
   With prestress (loads, item 6) that value must be 0: Mecway does not solve this
   (Mecway Ltd., 2026, §6.3) and the bridge stops with an ERROR (§4).
   - Modal without any support (free-free): the bridge still solves it (§3.2); the
     first modes are then rigid body motions with ~0 Hz.
   - A mechanism in an otherwise supported model (e.g. a beam held only by a hinge, a
     loose part): Code-Aster stops with `ALGELINE3_81`; solution in §4 (KNOWN_BUGS 48).
   - Buckling without supports is not possible (the static analysis is singular):
     ERROR.
   - Connections from `#ASTER` code (`LIAISON_ELEM`, `LIAISON_MAIL`, `DDL_IMPO`, ...)
     count if the load is in `#ASTER-EXCIT` (§2.1, §2.2;
     [`ASTER_lines_examples.md`](ASTER_lines_examples.md) §2).
6. **Loads.**
   - Modal: with loads the bridge, like Mecway, computes a **prestressed** modal
     analysis (*stress stiffening*, Mecway Ltd., 2026, §6.3): first linear static
     under all loads, then the modes with the stiffness plus the geometric stiffness
     of that stress field (§2.5). **Tension raises the frequencies, compression
     lowers them**; compression above the buckling load gives a negative frequency
     (WARNING). All loads count (forces, pressure, gravity, centrifugal force,
     thermal strain with *Thermal stress*). A centrifugal force also gives *spin
     softening* (§2.5). For the unloaded frequencies: switch off "Prestress from loads
     (stress stiffening)" on the Modal page; the loads are then
     dropped with a WARNING.
   - Buckling: the loads determine the stress field and hence the buckling pattern. All
     loads are included (forces, pressure, gravity, ...). The **buckling factor is the
     multiple of all applied loads together** at which the structure buckles. So apply
     a reference load (e.g. 1 kN or the design load); with a unit load the factor is
     the buckling load directly. A constant load (such as self-weight) is multiplied as
     well; to keep it fixed, adjust the variable load until the factor becomes 1
     (Mecway Ltd., 2026, §6.6).
   - A load with a time table gets the last value of the table (WARNING).

### 1.2 In the main window of the bridge

1. **"Active analysis (auto = follow Mecway)":** `auto` picks `modal_3d` for V30 and `buckling_3d` for B30; or choose the
   analysis yourself.
2. **"Results to Mecway"** must be `liml` (General page); with
   `tabel` the bridge stops before the run with a message.
3. **"Modal"** or **"Buckling"** page (change only when needed):

| Setting (label) | Default | When to change |
|---|---|---|
| "Number of modes (without maxmode in Mecway)" | 10 (modal), 4 (buckling) | only if the Mecway model has no *Number of modes* |
| "Search frequency [Hz] (0 = lowest modes)" (modal only) | 0 | > 0: the modes closest to this frequency (`OPTION='CENTRE'`; closest measured in ω², not in Hz), e.g. around an excitation frequency. < 0, e.g. -10 x the expected first elastic frequency: also the lowest modes, but solvable with a mechanism that has mass (§4). 0 without supports: the bridge shifts by itself (§3.2) |
| "Mode shape normalisation (NORM_MODE)" | `MASS_GENE` (modal), `RIGI_GENE` (buckling) | rarely; see §2.3. Only the shape is meaningful. `MASS_GENE` for buckling becomes `RIGI_GENE` (WARNING: buckling has no mass matrix) |
| "Mode check (VERI_MODE SEUIL)" | 1e-6 | larger (e.g. 1e-4) if the log reports `ALGELINE5_15` for a coarse or ill-conditioned model |
| "Prestress from loads (stress stiffening)" (modal only) | on | off to see the unloaded frequencies, or if an imposed displacement ≠ 0 should only count as a support (§2.5) |
| "Complex modes with damping (Rayleigh, dampers)" (modal only) | off | on for the damped frequency and the damping ratio ζ per mode with Rayleigh damping or dampers (*Damper*); §6. Off = like Mecway: damping is not included |
| "Result fields to Mecway" (modal only) | `displacements` | tick `stresses` and/or `vonmises` for **stresses per mode** (§1.4): where a mode shape gives the largest stress, e.g. to place a sensor or find a fatigue-sensitive spot. Other fields (reactions, ...) are ignored (INFO). Buckling: shapes only |
| Time limit / memory limit run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | large models |

4. The element choices on the **"Elements"** page apply here too. Hex8 with
   `3D` is too stiff in bending (KNOWN_BUGS 1): frequencies and buckling factors become
   too high. Use `LINE_QUAD` or quadratic elements (hex20) in Mecway. Measured with the
   bridge (cantilever 1 x 0.1 x 0.1 m, 20x2x2 hex8, Euler-Bernoulli f1 = 83.55 Hz):
   hex8 `3D` 89.11 Hz (+6.7%), `LINE_QUAD` 83.48 Hz (-0.09%).

### 1.3 Start and follow

Click "Start". What you see:

- **Log and status box** afterwards: per mode the frequency with the **effective
  mass** per translation direction (X/Y/Z, as % of the total mass) and per rotation
  (RX/RY/RZ: about the global axes through the origin, as % of the moment of inertia
  about that axis; §1.5) and the sum over the modes, or the buckling factor per mode.
  Example (verification test MO-01): `Mode 1: 16.7103 Hz (eff. mass X/Y/Z
  0.0/61.3/0.0%, RX/RY/RZ 0.0/0.0/97.1%)`. The log also gives the total mass, the
  centre of mass and the moments of inertia about the axes through the origin and
  through the centre of mass (`INFO: Mass 4.71 kg, centre of gravity (0.5, 0, 0) m; ...`).
  The status box shows the first 20 modes, the log all of them. The same effective
  mass is also in Mecway per mode (§1.4).
- **Convergence window:** the messages and the diagnosis; the status line shows the
  first modes (`modes 1: 16.71 Hz, 2: 25.07 Hz, ...`). For buckling also the static
  analysis (linear solver).
- **WARNINGs** that belong to modes: no density, loads ignored (prestress off),
  free-free, mode 1 with ~0 Hz (rigid motion or mechanism), negative frequency
  (compression above the buckling load), negative buckling factor, and the alarms of the
  mode check (`ALGELINE5_23`, `ALGELINE2_74`, `ALGELINE5_15`; §4).
- With "Mecway solve first as a check" the log
  compares Mecway's and Code-Aster's frequency or factor per mode (no CSV: shapes have
  an arbitrary sign).

### 1.4 Viewing the results in Mecway

- Under *Solution* you find *Mode 1 ... Mode n* with the frequency (Hz) or the buckling
  factor. Click a mode and choose a field (*displacement*); *Animate* shows the motion.
- Fields: displacements `displx/y/z` (and `rotx/y/z` for beams and shells), for
  buckling also `displmag`, as in Mecway's default solution. Reaction forces do not
  belong to a mode.
- **Stresses per mode** (modal only, when "Result fields to Mecway" contains `stresses` or `vonmises`): `stressxx` ... `stresszx` and
  `vonmises` (solid elements, per node and per element node), `vonmisesu1/m/b`
  (shells, top/middle/bottom surface) and `beamsixxmin/max` (beams with a RECTANGLE or
  CERCLE section), the same names as for static. Mecway itself also computes them per
  mode if you add them under *Solution* before solving (checked headless). **Only
  meaningful relative to each other:** the stress belongs to the normalised shape
  (φᵀMφ = 1, unit Pa/√kg), so the value in Pa says nothing about a real vibration; it
  does show where the stress is largest and how it is distributed over the model. The
  sign changes with the sign of the shape. Real stresses in a vibration need a response
  analysis (the modal amplitude multiplies both shape and stress).
- **Effective mass per mode (modal):** under *Solution* you also find *modal effective
  mass* (kg for X/Y/Z, kg·m² for the rotations) and *modal effective mass fraction*,
  per mode and per direction `tx`, `ty`, `tz`, `rx`, `ry`, `rz`. These are Mecway's
  own variables (`modaleffectivemassty`, `modaleffectivemassfractionty`, ...), in the
  result exactly as Mecway's own modal solution writes them (checked headless; see
  §2.1); Mecway creates the two items itself when opening. They hold the values of the
  log (§1.3), with 15 digits:
  - *modal effective mass*: Γ² = (φᵀMR)² with φ mass-normalised; the same quantity as
    in Mecway (Mecway Ltd., 2026, §6.3);
  - *modal effective mass fraction*: **Code-Aster's fraction** (`MASS_EFFE_UN_D*`;
    rotations with the same denominator): divided by the **total** mass or total
    moment of inertia, including the supported nodes. Mecway's own solver divides by
    the *free* mass; the bridge does not convert (§1.5, *Difference with Mecway in the
    fraction*). For Mecway's fraction, divide *modal effective mass* by the free mass;
  - in addition the **cumulative fraction** (sum of the fractions of mode 1 up to and
    including this mode, Code-Aster's denominator) as
    `cumulativeeffectivemassfractiontx` ... `rz`: a name of the bridge's own. Mecway
    keeps it when saving (checked headless); whether Mecway's window shows it as an
    item is NOT verified. The sum over all modes is in the log and the status box in
    any case.

  A direction without a value (e.g. no rotations because the own check failed, §4) is
  also missing in Mecway. For complex modes (§6) it is the effective mass from the real
  part of the shape. Not for buckling, acoustic modes, vibro-acoustics and cyclic
  symmetry (not in the log either), and not for a response on a modal basis (Mecway
  then has time steps, not modes).
- **The scale of a shape has no physical meaning** (Mecway Ltd., 2026, §6.3). A mode
  shape tells how the nodes move relative to each other, not how much. Normalisation
  (as Mecway): mode shapes with generalised mass 1 (phi^T M phi = 1; unit
  m/sqrt(kg)), buckling shapes with generalised stiffness 1 (phi^T K phi = 1). The sign
  of a shape is arbitrary.
- The results are also kept separately (`<model>_<run-id>_results.xml`) and can be
  reloaded with "Results..." ([User guide §5.1](UserGuide.md#51-loading-results-again-later-small-liml)).

### 1.5 Interpretation and checks

- **Buckling load = buckling factor x applied load.** The first (smallest positive)
  factor governs. A factor < 1 means the structure already buckles under the applied
  load.
- **Linear buckling usually overestimates the real buckling load.** It assumes a
  perfect structure without imperfections, eccentricity, plasticity or displacements
  before buckling (Mecway Ltd., 2026, §6.6; EDF R&D, U2.08.04). Use a knockdown factor
  according to the applicable standard, or a nonlinear analysis with an imperfection
  (`nonlin_static_3d`, §5).
- **Modal with prestress:** compare with the unloaded frequencies (switch off
  "Prestress from loads (stress stiffening)") to see the effect of the load. A frequency that
  goes to 0 with increasing compression indicates buckling; compute the buckling load
  itself with a buckling analysis (B30). A negative frequency means the structure is
  unstable under this load (Mecway then gives 0 Hz).
- **Modal:** the effective mass shows which modes take part in a direction. For a
  seismic or response analysis ~90% effective mass per direction is often used (rule
  of thumb, depends on the standard; NOT verified in the references below): ask for
  more modes.
- **Effective mass for the rotations (RX/RY/RZ)** applies, as in Mecway, to a rigid
  rotation about the **global axes through the origin** (Mecway Ltd., 2026, §6.3;
  checked against Mecway's own values, §2.1). The fraction is the effective mass
  divided by the moment of inertia about that axis (in the log). If the model lies far
  from the origin, a rotation about the origin is mostly a translation, and the
  RX/RY/RZ fractions look like those of the translations. For the rotation about a
  point of your own (centre of mass, base of a building for rocking): put the origin
  at that point in Mecway (Mecway's *Tools → Center of mass* shows the centre of mass;
  the log gives it too). With enough modes the sum over the modes approaches 100% (for
  a free model already with the 6 rigid modes; see also the next item). For a clamped
  cantilever with the origin at the clamp, mode 1 already gives 97% rotation, against
  61% translation (verification MO-01, MO-07).
- **Difference with Mecway in the fraction:** the bridge divides, as Code-Aster does
  for the translations (`MASS_EFFE_UN_D*`), by the **total** mass or total moment of
  inertia, including the supported nodes; Mecway by the *free* mass (without the
  supported nodes). The effective mass itself (kg, kg·m²) is equal (≤ 0.02%), but the
  bridge's fractions are slightly lower for a clamped model: the clamped block of §2.1,
  1 x 0.1 x 0.05 m with 10 x 2 x 2 hex20, 61.0% (bridge) against 62.3% (Mecway) in Z.
  A finer mesh reduces the difference. The bridge's sum over the modes therefore stays
  slightly below 100%. This also applies to *modal effective mass fraction* in Mecway
  (§1.4): the bridge puts Code-Aster's fraction there, not converted; *modal effective
  mass* itself is directly comparable.
- **Units:** check the units of density and E in Mecway. A density that is off by a
  factor 1e9 gives a factor ~3e4 in frequency (f ~ 1/sqrt(rho)).
- **Mesh convergence:** run again with a finer mesh; the frequency or factor should
  hardly change. Linear solid elements are too stiff in bending: use quadratic
  elements or `LINE_QUAD` (§1.2).
- **Hand calculation** as a check (formulas from the verification,
  [`Verification.md`](Verification.md)):
  - cantilever beam: f1 = 0.5596 / L² · sqrt(EI / (rho A)) (Blevins, 1979);
  - pinned-pinned beam with axial force P (tension > 0): f_n = f_n0 · sqrt(1 + P /
    Pcr_n), Pcr_n = n² pi² EI / L² (equation of Code-Aster test case sdll101a;
    verification MP-01/02);
  - Euler buckling: Pcr = pi² EI / (k L)², k = 2 cantilever, k = 1 pinned-pinned
    (Timoshenko & Gere, 1961);
  - simply supported square plate under uniaxial compression:
    sigma_cr = 4 pi² D / (b² t) (Timoshenko & Gere, 1961).

  - effective mass of a cantilever (Euler-Bernoulli, origin at the clamp): mode 1
    61.3% translation, 97.1% rotation; modes 2 and 3 18.8 / 6.5% translation and
    2.5 / 0.3% rotation (verification MO-01, MO-07).

  The verification tests MO-01..05 and BU-01..04 deviate at most 0.25% with the finest
  mesh (beam elements < 0.002%); with coarse meshes the deviation is larger (up to 4%
  for BU-04 with 8x8 DKT) and decreases with order 2.

## 2. How the bridge translates

### 2.1 Modal (`modal_3d`)

`ASSEMBLAGE` (EDF R&D, U4.61.21) builds the stiffness (`RIGI_MECA`) and the mass
(`MASS_MECA`: the consistent mass matrix, not the diagonal `MASS_MECA_DIAG`; with point
masses) with the supports and the `#ASTER-EXCIT` loads as `CHARGE` (Lagrange
multipliers). Connections from `#ASTER` code thus count; forces in such a load do not
contribute to the matrices (`CHARGE` only supplies the kinematic conditions,
U4.61.21). Then `CALC_MODES` with
`OPTION='PLUS_PETITE'` and `CALC_FREQ=_F(NMAX_FREQ=n)`, or `OPTION='CENTRE'` around the
search frequency. Without supports: `CENTRE` around a small negative frequency (§3.2).
After the analysis `aster_results_export.py` reads the frequencies and the effective
mass for the translations (`RECU_TABLE`, `MASS_EFFE_UN_DX/DY/DZ`).

**Effective mass for the rotations.** Code-Aster does not have it as a parameter
(`RECU_TABLE` with `MASS_EFFE_UN_DRX` gives `UTILITAI3_5`). `aster_results_export.py`
computes it in the job itself (numpy), with Mecway's definition (Mecway Ltd., 2026,
§6.3): participation factor Γ = φᵀMR with R the rigid rotation about the global axis
through the origin (u = θ × x, and θ itself on the rotational degrees of freedom of
beams, shells and discrete elements), effective mass Γ²/(φᵀMφ), fraction = effective
mass / RᵀMR. M is the assembled mass matrix (`masse`, `getValuesWithDescription`), the
mapping degree of freedom → node and component comes from
`getNodeAndComponentFromDOF()` (Lagrange degrees of freedom do not count). Check in
every run: the same computation for the translations must give Code-Aster's
`MASS_EFFE_UN_D*` (deviation ≤ 1e-4), otherwise the bridge gives no rotations (message
in the `.mess`, §4). Measured: clamped block 1 x 0.1 x 0.05 m from (1, 2, 3) m,
10 x 2 x 2 hex20, mode 1 / 2 rotation X 100.613 / 219.306 kg·m² against Mecway
100.627 / 219.335 kg·m² (−0.014%); moment of inertia about the X axis 524.151 kg·m² =
m(b² + h²)/12 + m·d² exactly.

**Effective mass to Mecway.** Mecway's own modal solution (internal solver, with
*modal effective mass* and *modal effective mass fraction* under *Solution*) writes
per `<mode>`, before the `<nodevariable>`s, per direction `tx` ... `rz` alternately
`<globalvariable name="modaleffectivemassty">57.7394288067102</globalvariable>` and
`<globalvariable name="modaleffectivemassfractionty">0.627861821259979</globalvariable>`
(seen headless with Mecway 33 on the sample VibratingCantileverSolid). A result with
these lines gives the two items under *Solution* by itself when opened (checked
headless: Mecway adds the `<fieldvariable>`s). `aster_results_export.py` writes the
same lines into the result file: the effective mass Γ²/(φᵀMφ) from the own computation
above (all 6 directions; only if the check on the translations passes), Code-Aster's
fraction (`MASS_EFFE_UN_D*`) and for the rotations the own fraction with the same
denominator RᵀMR, plus `cumulativeeffectivemassfraction*` (own name, §1.4).
Verification: MO-01 (Mecway variable = value in the `.mess` = Euler-Bernoulli) and
MO-06 (cumulative 1 for a free block). With "Result fields to Mecway"
`stresses`/`vonmises`, `CALC_CHAMP` follows on the modal result as for static
(`SIGM_ELNO`/`SIGM_NOEU`, `SIEQ_*`, shells via `POST_CHAMP EXTR_COQUE`, beams
`SIPM_ELNO`; no `REAC_NODA`).

### 2.2 Buckling (`buckling_3d`)

`MECA_STATIQUE` with all loads (including the `#ASTER-EXCIT` loads) → stress field
`SIEF_ELGA` (`CREA_CHAMP`) → `ASSEMBLAGE` with `RIGI_MECA` and `RIGI_GEOM` (with that
field; supports and `#ASTER-EXCIT` loads as `CHARGE`, as for modal) → `CALC_MODES
TYPE_RESU='MODE_FLAMB'`, `OPTION='PLUS_PETITE'`, `NMAX_CHAR_CRIT = n` (route as in the
Code-Aster test case ssll105a; method: EDF R&D, U2.08.04). Code-Aster's `CHAR_CRIT`
is Mecway's buckling factor directly (checked: Mecway sample BucklingBeam, 41124.699 in
both); negative = buckling under the reversed load (KNOWN_BUGS 46).

The bridge always looks for the smallest ∣factors∣, as Mecway does; there is no setting
for a search centre. `OPTION='CENTRE'` ignores `CHAR_CRIT` with `MODE_FLAMB` in
Code-Aster 17.4 (the `.mess` reports "La valeur de décalage en charge critique est :
0.00000E+00"; measured on BU-01 with 90, 200 and −200: always the smallest factors).
`OPTION='BANDE'` does work (`CHAR_CRIT=(100, 300)` gave 209.853 and 259.086), but is
not offered ([`Default_settings_and_assumptions.md`](Default_settings_and_assumptions.md)
§3.8).

### 2.3 Normalisation

| Normalisation | Meaning | Use |
|---|---|---|
| `MASS_GENE` | phi^T M phi = 1 | modal default, as Mecway |
| `RIGI_GENE` | phi^T K phi = 1 | buckling default, as Mecway (Code-Aster does not support it for buckling; the bridge normalises itself with Kg) |
| `TRAN_ROTA` | largest displacement or rotation = 1 | Code-Aster's default (catalogue `calc_modes.py`) |
| `TRAN` | largest displacement = 1 | handy to compare shapes |
| `EUCL` | Euclidean norm = 1 | |

### 2.4 Check of the modes

`VERI_MODE` checks the relative error of each mode (limit `SEUIL`, default 1e-6 as in
Code-Aster) and counts with the Sturm test whether no modes were missed. The bridge
sets `STOP_ERREUR='NON'`: a failed check becomes an alarm (`<A>`) and a WARNING with an
explanation in the log, instead of an error that stops the run. Reason: with multiple
modes on the limit of the requested number the Sturm test fails while the modes are
correct (§3.1). With such a WARNING, check the modes yourself.

### 2.5 Modal with prestress

With the setting "Prestress from loads (stress stiffening)" on (default)
and at least one load or thermal strain (*Thermal stress* with *Temperature*):

1. `MECA_STATIQUE` with all loads (also `#ASTER-EXCIT`) → stress field `SIEF_ELGA`
   (`CREA_CHAMP`), as for buckling (§2.2).
2. `ASSEMBLAGE` with `RIGI_MECA`, `MASS_MECA` and `RIGI_GEOM` (with that field); with a
   centrifugal force also `RIGI_ROTA` (centrifugal stiffness, *spin softening*; the
   `ROTATION` load is then in `CHARGE`).
3. `COMB_MATR_ASSE`: K = `RIGI_MECA` + `RIGI_GEOM` (+ `RIGI_ROTA`), all with
   coefficient 1 (Code-Aster test cases sdll101a, tensioned string, and sdll133a,
   rotating wheel).
4. `CALC_MODES` with this K and the mass, otherwise as §2.1.

Tension gives a positive `RIGI_GEOM` (higher frequencies), compression a negative
one. Like Mecway (Mecway Ltd., 2026, §6.3; samples VibratingMembrane and
VibratingString, §11.20 and §11.22) thermal strain counts, and a centrifugal force
also gives spin softening (sample Impeller, §11.21). An `#ASTER-EXCIT` load without a
Mecway load does not start the prestress.

Measured (verification MP, [`Verification.md`](Verification.md) §7): beams and solids
equal to headless Mecway (< 1e-5), also the rotating hex20 beam; plate with thermal
compression −0.07 / −0.25% against Mecway (Mecway's quad4 converges more slowly);
analytical ≤ 0.11%. Deviations (KNOWN_BUGS 49): the rotating **beam** (`POU_D_E`)
gives up to 0.5% lower frequencies in the plane of rotation than Mecway (Code-Aster's
`RIGI_ROTA` for beams); with **shells** the centrifugal force becomes a formula load
and spin softening is missing (WARNING); for **point masses** too (WARNING).

## 3. Particulars

### 3.1 Multiple modes

With symmetry (square section, square plate) there are modes with (nearly) the same
frequency. If such a pair falls on the limit of the requested number, Code-Aster
reports the Sturm alarm `ALGELINE5_23` (the check counts one mode more than computed).
The results are usable; ask for one more mode if you want the whole pair. The shape of
a multiple mode is not unique (any combination is also a shape), so compare shapes with
Mecway only for single modes.

### 3.2 Free-free and rigid modes

Without supports K is singular and Code-Aster's default shift 0 fails. The bridge then
searches around a small negative frequency (`CENTRE`, line `BRIDGE_FREE_SHIFT` in the
`.mess`); the 6 rigid modes come with |f| of the order of 1e-4 Hz (verification MO-04:
|f| < 6e-4 Hz; sometimes negative, numerically zero), followed by the elastic ones.

### 3.3 Not possible

- Damping: not by default (like Mecway); with the setting *Complex modes with
  damping* it is, as complex modes (§6). Cyclic symmetry: modal only, with
  limits (§7.5). Acoustic cavity modes (Mecway A30): [`Acoustics.md`](Acoustics.md).
- Prestress with an imposed displacement or rotation ≠ 0 (Mecway neither).
- Spin softening for centrifugal force on shells and point masses (§2.5).
- Effective mass for the rotations about a point other than the origin (put the origin
  at that point in Mecway, §1.5), and the fraction with Mecway's denominator (free
  mass; the bridge gives Code-Aster's, §1.4).
- Contact, gaps, tension/compression only: not in a modal or buckling analysis
  (ERROR).
- Stresses per buckling mode (only per vibration mode, §1.4).

### 3.4 Beam orientation and sections

The bridge rotates a beam cross-section like Mecway (*orientation vector* and *angle*
per element, Mecway manual v33 §7.5; without orientation Mecway's default: V = Z × U,
along Z V = Y). Checked for modal, static and buckling with beams along X, Y, Z and
skew, without orientation, with a vector and with vector + angle, all sections of the
bridge and a frame ([`Verification.md`](Verification.md) §7, *Beam orientation*,
MO-20 … MO-29): frequencies, mode shapes (direction of the deflection) and effective
mass per direction equal to Mecway and to Euler-Bernoulli. Like Mecway, `POU_D_E` uses
the polar inertia for torsion, but no rotary inertia of the cross-section in bending and
no offset shear centre (T, L, C). Buckling with bending moments (frames) and pure
torsional buckling differ from Mecway; there the bridge is right (§3.5).

### 3.5 Buckling of beams: torsion, frames and open sections

`RIGI_GEOM` of `POU_D_E`/`POU_D_T` (Code-Aster R3.08.01 §6) contains the axial force
(for torsion with the term N·(I_y + I_z)/A about the centroid), the bending moments and
shear forces, and at the nodes the terms of moderate rotations (±M/2 between the twist
and the bending rotations). Warping and a shear centre outside the centroid are not in
it. Checked with volume and shell models of the same structure, in Code-Aster, Mecway's
own solver and CCX ([`Verification.md`](Verification.md) §7, BU-30 … BU-36):

- **Pure torsional buckling** (doubly symmetric section): the bridge gives
  P = G·J·A/I_p (torsional buckling without warping, Timoshenko & Gere, 1961, §5.3).
  I column 100/50/10/8 mm, L = 1 m: 2413.9; the same model in hex20 2384.3 (−1.2%).
  Without warping the factor does not depend on the length: it comes back as a multiple
  factor (in theory one per element) and Code-Aster then gives the Sturm alarm
  `ALGELINE5_23`. That is not an error. Mecway's own beam computes no torsional
  buckling: its fourth factor (2743.0) is the third flexural mode (KNOWN_BUGS 112).
- **Frames with bending moments**: the bridge agrees with volume and shell models and
  with Code-Aster test case ssll105 (right-angle frame of Argyris). Mecway's beam lacks
  the terms at the nodes and gives too low factors for buckling out of the plane:
  L frame 19.71 against 44.53 (bridge) and 44.86 (hex20) (KNOWN_BUGS 113). For a
  straight beam (lateral-torsional buckling of a cantilever) both are equal.
- **T, C and L profiles**: the shear centre is not in the centroid, so bending and
  torsion couple (flexural-torsional buckling). `POU_D_E` misses that coupling and then
  gives too high factors: C column 100 × 50 × 6 mm 616 against 393 (hex20). The bridge
  gives a WARNING for buckling with these profiles; check such structures with shell or
  volume elements (KNOWN_BUGS 115).
- **Negative factors**: the bridge also gives the factors for the reversed load (for the
  L frame −53.0). Mecway gives only positive factors and with its default *shift* 1
  sometimes skips a factor below 1 (ssll105: 0.4226 only with shift 0.3).
- **Slender volume models**: the static step of the buckling analysis can stop with
  `FACTOR_57` without a mechanism (hex20 frame of 1 m, 40 × 10 mm; KNOWN_BUGS 114).
  There is no setting yet to avoid that.

## 4. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| WARNING: Modal: elset(s) ... have no density | no mass | give the material a density |
| WARNING: Modal analysis: loads (...) are ignored | prestress off, model with loads | intended? Otherwise switch on "Prestress from loads (stress stiffening)" (Modal page) |
| ERROR: Modal with prestress: imposed displacement or rotation <> 0 on ... | prestress with an imposed displacement ≠ 0 (Mecway does not solve this either) | set the value to 0, or switch off the prestress (then only the fixed degree of freedom counts) |
| ERROR: Modal with prestress without supports | the static analysis under the loads is singular | add supports, or switch off the prestress |
| WARNING: Negative frequency (frequencies) | compression above the buckling load of that mode | reduce the compressive load; check with a buckling analysis |
| WARNING: Centrifugal force in a model with shells / of point masses | spin softening is missing there (§2.5) | frequencies are slightly higher than in Mecway; compare with Mecway if needed |
| WARNING: No supports (free-free) | loose model | normal for a free body; count 6 rigid modes |
| ERROR: Buckling without a load / Buckling without supports | buckling needs a load and supports | apply the reference load and supports |
| `<EXCEPTION> <ALGELINE3_81>` (le shift ... coïncide avec une valeur propre) | singular stiffness: mechanism, loose part, hinge | support the model better, or choose a negative search frequency (e.g. -10 x the expected first elastic frequency); the rigid modes then appear with ~0 Hz. That only helps if the loose part has mass (density or point mass). A connection from `#ASTER` code only counts via `#ASTER-EXCIT` |
| alarm `ALGELINE3_82` (la borne minimale ... est une valeur propre) | the lower bound of the Sturm band (nearly) coincides with an eigenvalue, usually a rigid mode at ~0 Hz (seen with a free-free model and a negative search frequency) | usually harmless: check the number of modes, or shift the search frequency slightly |
| `ALGELINE5_49` / `ALGELINE3_78` (too few modes) | search frequency far from the modes; or many spurious modes at ~0 Hz (e.g. a membrane with an artificially small E and prestress, like Mecway's VibratingMembrane: rotation modes of `COQUE_3D` without stiffness) | search frequency closer to the expected frequencies, 0, or fewer modes; for the membrane a search frequency around the expected frequency (KNOWN_BUGS 49) |
| alarm `ALGELINE5_23` (Sturm) | multiple mode on the limit, or a missed mode | ask for one or two more modes and compare |
| alarm `ALGELINE5_15` ("... a une norme d'erreur ... supérieure au seuil admis") | a mode does not reach the accuracy | finer/better mesh, or a larger "Mode check (VERI_MODE SEUIL)" (1e-4) |
| alarm `ALGELINE2_74` | one of the `VERI_MODE` checks failed | see the alarms before it and the table in the `.mess` |
| WARNING: Negative buckling factor(s) | buckling under the reversed load (e.g. tension instead of compression) | check the load direction; only positive factors belong to the applied direction |
| WARNING: Buckling with T, C or L profiles | flexural-torsional buckling is missing in the beam elements (shear centre, warping) | check with shell or volume elements (§3.5, KNOWN_BUGS 115) |
| INFO: Buckling of beams ... appears as several equal factors | torsional buckling without warping: one factor per element (§3.5) | normal; the Sturm alarm `ALGELINE5_23` belongs to it |
| WARNING: Mode 1 has ~0 Hz | rigid motion or mechanism | check the supports |
| No RX/RY/RZ after the modes; in the `.mess`: `aster_results_export: WARNING: effective mass of the rotations not ...` | the own computation failed or did not match Code-Aster's values for the translations (e.g. an unknown kind of degree of freedom) | frequencies, shapes and translations are fine; report the model as a bug (KNOWN_BUGS). You can then request a rotational effective mass in Mecway itself (*modal effective mass*, internal solver) |
| RX/RY/RZ fractions look like the translations | the model lies far from the origin: a rotation about the origin is then mostly a translation | put the origin at the point about which you want the rotation (§1.5) |
| INFO: Modes: ... ignored: reactions (or another field) | for modes only shapes and stresses go to Mecway | normal; reactions do not belong to a mode |
| The result route 'tabel' does not work ... | modes only via `liml` | set "Results to Mecway" to `liml` |

## 5. Nonlinear buckling

Linear buckling (§2.2) assumes a perfect structure and small displacements before
buckling. Two additions in the **nonlinear static analysis** (`nonlin_static_3d`,
Mecway *Nonlinear Static*, L30), usable separately or together:

| Feature | Setting (page Nonlinear static) | What it gives |
|---|---|---|
| Stability per step | *Stability per step (CRIT_STAB)* | after each step how far the current state is from buckling, in the log and the status box, and a message when buckling is reached |
| Buckling mode as imperfection | *Imperfection: amplitude*, *buckling mode no.*, *amplitude in* | the analysis on a slightly pre-deformed shape (buckling mode × amplitude): the deflection grows with the load and the load capacity drops, as in a real structure |

Mecway has no input for this itself: Mecway's sample BucklingPlateNonlinear (Mecway
Ltd., 2026, §11.9) applies a small transverse force as a perturbation. That also works
with the bridge; the buckling mode as imperfection is the approach Code-Aster
recommends (EDF R&D, U2.08.04 §2.2).

### 5.1 Workflow

1. **Model in Mecway**: analysis type *Nonlinear Static*. Apply the load with a **time
   table** rising from 0 (e.g. 0 at t = 0 and the design load, or a little above the
   expected buckling load, at t = 1). Without a table the full load is present from the
   first step; you then do not see the build-up.
2. **Steps**: *Substeps per time interval* sets how many points you get (default 10; 20
   to 40 gives a more accurate buckling point).
3. **Elements**: use **solid elements** (preferably quadratic, or hex8 with
   `LINE_QUAD`) or shells with `elem_shell` = `COQUE_3D`. Beams (`POU_D_E`) and DKT/DST
   shells are geometrically linear in the bridge (KNOWN_BUGS 11): CRIT_STAB works there
   (as a load factor), but the deflection does not grow with an imperfection (WARNING).
4. **Page Nonlinear static** (or per model with `#ASTER-OPTIE`,
   [`ASTER_lines_examples.md`](ASTER_lines_examples.md) §2):

| Setting (label) | Key | Default | When to change |
|---|---|---|---|
| Stability per step (CRIT_STAB) | `crit_stab` | off | on to find the load at which the structure buckles or reaches a limit point. Costs an eigenvalue solution per step (extra run time per step; noticeable for large models) |
| Imperfection: amplitude (0 = none) | `imperfection_amplitude` | 0 | > 0 for an imperfection, e.g. L/1000 to L/300 or the value from the design code. Negative reverses the shape (the sign of a buckling mode is arbitrary) |
| Imperfection: buckling mode no. | `imperfection_mode` | 1 | another shape (2 = the second smallest buckling factor), e.g. with two shapes with almost the same factor |
| Imperfection: amplitude in (m / x L) | `imperfection_unit` | `m` | `L`: amplitude as a fraction of the largest dimension of the model (0.001 = L/1000; the log gives L and the amplitude in m) |

5. **Start.** With an imperfection Code-Aster first solves the linear buckling problem
   under the loads at the end time (like `buckling_3d`), deforms the mesh with the
   chosen mode and then solves nonlinearly.
6. **Results**: the displacements per step in Mecway, plus the imperfection and the
   stability in the log and the status box (§5.3).

### 5.2 How the bridge translates

**CRIT_STAB.** `STAT_NON_LINE` gets `CRIT_STAB=_F(OPTION='PLUS_PETITE',
NMAX_CHAR_CRIT=1)` (catalogue `stat_non_line.py`, test cases ssll105d/e/f): after each
step the smallest |λ| of an eigenvalue problem with the tangent stiffness K_T of that
moment (EDF R&D, U4.51.03 §3.18; U2.08.04 §2.1). After the analysis the job writes the
table `ANALYSE_MODALE` as `BRIDGE_CRIT_STAB` lines into the `.mess`. What λ means
depends on the kinematics (`deformation`, chosen per elset,
[Settings §2.3](Settings_contact_and_nonlinear.md#23-kinematics-deformation)):

| Kinematics | Problem | λ means | Buckling when |
|---|---|---|---|
| small displacements (`PETIT`, `PETIT_REAC`; beams always) | det(K_T + λ K_g) = 0, K_g from the stress of the step | **critical load factor of the current load**: buckling at λ × the load of that moment | 0 < λ ≤ 1 |
| large displacements (`GROT_GDEP`, `GREEN_LAGRANGE`, `GDEF_LOG`; default for solids and `COQUE_3D`) | det(K_T + λ I) = 0 (K_T already contains K_g) | **smallest eigenvalue of K_T with reversed sign** (a stiffness, not a load factor): < 0 stable | λ becomes 0 |

If one elset uses large displacements, the second row applies to the whole model
(measured). With large displacements the bridge estimates the buckling point: if λ
changes sign between two steps, by linear interpolation; otherwise by extending the last
two steps linearly to 0. If the load rises from 0 in proportion to time, the buckling
load is ≈ t_buckling / t × the load at t. The estimate improves as the last step gets
closer to buckling (NK-02a: from 0.9 Pcr +0.4 %).

For a load factor with solid elements: set `deformation` to `PETIT` (NK-02b, exact).
That is then a linear estimate about the current state, without a second-order effect
on the displacements.

**Imperfection** (`bridge_to_aster._imperfection_blocks`):

1. `MECA_STATIQUE` with all loads at the end time (`INST`), `SIEF_ELGA`, `ASSEMBLAGE`
   `RIGI_MECA` + `RIGI_GEOM`, `CALC_MODES` `MODE_FLAMB` (as §2.2), with `NORM_MODE`
   `TRAN`: the largest displacement component of the shape is 1. A follower pressure
   counts as a dead load here.
2. `MODI_MAILLAGE` `DEFORME` `TRAN` with amplitude × buckling mode k (`CREA_CHAMP`
   `COMB`; as test case ssnl502d), then `AFFE_CARA_ELEM` again (beam and shell axes on
   the deformed shape).
3. `STAT_NON_LINE` and `CALC_CHAMP` on the deformed mesh.
4. The mesh back with −amplitude × buckling mode (as test case hsna105a), so that the
   results fit the nodes of the Mecway model (the export checks the coordinates against
   the `.liml`).

The **displacements in Mecway are relative to the imperfect shape**: the total
deflection is the imperfection (in the buckling mode, at most the amplitude) plus the
displacement shown. Stresses and reactions belong to the imperfect structure.

### 5.3 Interpretation

What the log and the status box show (examples from the verification):

- `Imperfection: buckling mode 1 (buckling factor 1.11339 of the loads at the end
  time), amplitude 0.001 m.` The buckling factor is that of the linear buckling
  analysis under the loads at the end time (the same number as `buckling_3d`).
- Small displacements: `Stability (CRIT_STAB): at t = 1 critical load factor 1.11111:
  the load at that moment x 1.11111 gives buckling`. With a linearly rising load
  λ(t) × P(t) is constant (the buckling load). The log has λ per step.
- Large displacements: `Stability (CRIT_STAB, large displacements): at t = 1 criterion
  -2.70 ... Estimated buckling point t ~ 1.115`. Only the sign and the zero crossing
  are meaningful; the magnitude depends on the units and the mesh.
- **Buckling reached** (WARNING): λ ≤ 1 (small displacements) or λ changes sign (large
  displacements). A **perfect** structure stays straight in the analysis, even above
  the buckling load; the message then only says that it is unstable there. For the
  behaviour after buckling: an imperfection. If λ goes below 0 again after the sign
  change, the structure is stable again after buckling (e.g. a plate, Mecway's
  BucklingPlateNonlinear: change at t ≈ 0.57, load 7.15 N; theory 7.06 N).
- **Limit point / load capacity.** With an imperfection (and plasticity) the
  load-displacement curve has a maximum. With the load as a time table Code-Aster stops
  there (`MECANONLINE9_7`; the results up to that moment are loaded), and the criterion
  goes to 0 (WARNING "almost 0"). **The load at the last time is the load capacity**
  (NK-04: 0.49 Pcr with e0 = L/200, against Pcr for the perfect column).
- **Check**: the total deflection w = e0 / (1 − P/Pcr) (amplification factor of a bar
  with an initial curvature in the buckling mode; Timoshenko & Gere, 1961, chapter 1),
  and a Southwell plot (additional deflection δ against δ/P is a straight line with
  slope Pcr; Southwell, 1932) returns Pcr (NK-03: within 0.5 %).

### 5.4 Not possible

- CRIT_STAB and the imperfection only in `nonlin_static_3d`, not in dynamics
  (`DYNA_NON_LINE` does have CRIT_STAB, NOT built in).
- Imperfection not together with contact, compression only, gaps or tension only
  (ERROR): the buckling mode comes from a linear analysis.
- One buckling mode as imperfection; no combination of shapes, no measured geometry.
- The buckling mode of CRIT_STAB itself (`MODE_FLAMB` in the result) does not go to
  Mecway; the imperfection is always the linear buckling mode under the end load.
- Arc-length method (`PILOTAGE`), to continue past the limit point: not built in.
- See KNOWN_BUGS 53.

### 5.5 Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| WARNING: Buckling reached: from t = ... the critical load factor is <= 1 | the load exceeds the (linearly estimated) buckling load | reduce the load, or use an imperfection for the behaviour after buckling |
| WARNING: Buckling or instability reached around t = ... | λ changes sign (large displacements) | idem; for a plate the behaviour after buckling may be stable |
| WARNING: The stability criterion is almost 0 | close to buckling or a limit point | if the analysis stops there (`MECANONLINE9_7`), the load at the last time is the load capacity |
| WARNING: CRIT_STAB gave no values | the table `ANALYSE_MODALE` is missing (e.g. the run stopped in the first step) | see the `.mess`; first solve the ordinary convergence |
| ERROR: Imperfection (buckling mode) not possible with contact ... | the buckling mode comes from a linear analysis | amplitude 0, or suppress those parts in a configuration |
| ERROR: Imperfection: invalid amplitude or mode number / unit unknown | input | number, mode ≥ 1, unit `m` or `L` |
| WARNING: Imperfection with small displacements (DEFORMATION=...) | `PETIT`: no second-order effect | `deformation` = `GROT_GDEP` (default) |
| WARNING: Imperfection: beams and DKT/DST shells ... are geometrically linear | the deflection does not grow there | solid elements or `elem_shell` = `COQUE_3D` |
| WARNING: Imperfection: buckling mode k belongs to the reversed load | negative buckling factor (e.g. tension) | choose a mode with a positive factor, or check the load direction |
| WARNING: Imperfection: buckling mode k not found | fewer modes found than k | smaller mode number; see the `.mess` |

## 6. Modal with damping: complex modes

A normal modal analysis solves without damping: K φ = ω² M φ, real modes. With
damping (matrix C) a mode decays and the eigenvalue problem becomes quadratic:
(K + s C + s² M) φ = 0, with s = −ζω_n ± i·ω_d. Per mode this gives:

| Quantity | Meaning |
|---|---|
| f_d = ω_d / 2π | **damped frequency**: the frequency at which the mode actually vibrates |
| ζ | **damping ratio** (fraction of critical): the amplitude decays as e^(−ζ·2πf_n·t) |
| f_n = \|s\| / 2π | f_d / √(1 − ζ²); with Rayleigh damping exactly the undamped natural frequency |
| decay rate = ζ·2πf_n | decay rate [1/s], as Mecway gives it for complex acoustic modes |

**What Mecway does** (Mecway 33, measured headless): a *Frequency* analysis (V30)
ignores Rayleigh damping (mass on a beam with α = 3.55 1/s: the same frequencies
5.6494 / 8.4741 / 564.94 Hz as without, no decay rate) and gives no solution with a
*Damper* element. According to the manual Rayleigh damping belongs to *Dynamic
Response* (Mecway Ltd., 2026, §9.26). Mecway only knows complex modes in acoustics
with impedance (§6.9.2). The bridge therefore follows Code-Aster (`CALC_MODES` with
`MATR_AMOR`, test case sdld21c) as an **option**; by default it computes like Mecway.

### 6.1 Workflow

1. **Model in Mecway**: analysis type *Frequency* with *Number of modes*, as in §1.1.
2. **Damping** (either or both):
   - *Rayleigh damping* on the whole model (without a selection): C = αM + βK (Mecway
     Ltd., 2026, §9.26). According to the manual this load belongs to *Dynamic
     Response*; whether the Mecway GUI allows it in a *Frequency* model or keeps it
     when the analysis type is changed has NOT been checked. If it is in the
     `.liml` (`<rayleighdamping selection="">`), the bridge reads it; Mecway's own
     solve ignores it (seen headless). Per mode ζ_n = α/(2ω_n) + βω_n/2: α damps the
     low, β the high modes.
   - *Damper* elements: line2 with the material *Damper* (*Viscous damping
     coefficient* c, Mecway Ltd., 2026, §7.8), damping along the element axis.
3. **Main window**, Modal page: switch on "Complex modes with damping (Rayleigh, dampers)". The other settings
   apply as in §1.2 (search frequency, number of modes, prestress).
4. **Start** and view the results (§6.3).

| Setting (label) | Key | Default | When to change |
|---|---|---|---|
| Complex modes with damping (Rayleigh, dampers) | `modal_complex` | off | on if you want to know how strongly each mode is damped and at which frequency it decays, e.g. to choose or check α and β before a mode superposition response ([`Mode_superposition.md`](Mode_superposition.md)), or to see the effect of dampers on the modes. Off: damping is not included (INFO in the log), like Mecway |

Without damping in the model the setting gives ordinary real modes (INFO).

### 6.2 How the bridge translates

`bridge_modal_damping.py`:

1. `ASSEMBLAGE` as in §2.1 (with prestress §2.5), plus with dampers `AMOR_MECA` (the
   `A_T_D_L` of the dampers; the other discrete elements get damping 0, otherwise
   alarm `DISCRETS_28`).
2. The damping matrix `amor` = α·M + β·K + C_dampers with `COMB_MATR_ASSE`. M and K are
   the matrices of the eigenvalue problem: Rayleigh acts on the whole model, also on
   point masses (*mass*) and springs (*Spring*), and with prestress on K + K_g. So
   ζ_n = α/(2ω_n) + βω_n/2 with the ω_n of the same modes, exactly the damping ratio
   that the mode superposition response uses per mode
   ([`Mode_superposition.md`](Mode_superposition.md) §2.3; MC-04).
3. `CALC_MODES` with `MATR_AMOR=amor`: without a search frequency
   `OPTION='PLUS_PETITE'` with `SOLVEUR_MODAL=_F(METHODE='TRI_DIAG')` (Lanczos;
   `SORENSEN` cannot be used with `PLUS_PETITE` for a quadratic problem,
   `<EXCEPTION> ALGELINE2_71`); with a search frequency `OPTION='CENTRE'` with
   `SORENSEN`; without supports `CENTRE` around a small negative frequency (§3.2).
   Measured: `TRI_DIAG`, `QZ` and `SORENSEN` (`CENTRE`) gave the same f_d and ζ
   (difference ≤ 1e-9).
4. The result is a `MODE_MECA_C` with complex shapes. Code-Aster's `FREQ` is the
   **damped** frequency f_d, `AMOR_REDUIT` is ζ (measured: ζ = 0.3 gave 5.38919 =
   5.64944·√(1 − 0.09) Hz). `aster_results_export.py` writes per mode
   `<mode frequency="f_d Hz" decayrate="ζ·2πf_n 1/s">` (the format of Mecway's complex
   acoustic modes) with the **real part** as the shape: first a phase rotation that
   makes the real part as large as possible (θ = ½·arg(φᵀMφ)), then normalised to
   φᵀMφ = 1 with the largest component positive. With Rayleigh damping
   (proportional) the shape is then exactly the real, mass-normalised mode
   (measured: equal to 2e-9). The *Normalisation* setting does not apply here.
5. In the `.mess` per mode `BRIDGE_MODE nr FREQ=f_d AMOR_REDUIT=ζ FREQ_NAT=f_n
   DECAY=.. IMAG=..` with the effective mass, which the bridge computes itself from
   the real part (whether Code-Aster also gives `MASS_EFFE_UN_*` for complex modes has
   not been checked). `IMAG` = ‖Im‖/‖Re‖ (in the M norm) after
   the phase rotation: 0 for proportional damping, larger with dampers.

### 6.3 Interpretation

- **Log and status box**: `Mode 1: 42.2257 Hz damped (zeta 0.05093, f_n 42.2806 Hz)
  (eff. mass ...)` (verification MC-04). In Mecway, *Solution* shows the damped
  frequency f_d; Mecway's API reads the modes and shapes (checked headless); the decay
  rate in the Mecway GUI has NOT been checked.
- **Damped or undamped?** f_d is the frequency of a freely decaying structure, f_n
  that of the undamped one. With light damping the difference is small (ζ = 0.05:
  0.13%; ζ = 0.2: 2%; ζ = 0.5: 13%). For resonance under a harmonic load the peak is
  at f_n·√(1 − 2ζ²), so slightly below f_d (Clough & Penzien, 1993, chapter 3).
- **ζ per mode** tells how quickly a mode dies out: after n cycles the amplitude is
  e^(−2πnζ/√(1 − ζ²)) of the initial one (ζ = 0.05: 4% after 10 cycles).
- **Rayleigh**: check with ζ_n = α/(2ω_n) + βω_n/2 whether the damping per mode is
  what you intended; with only β the high modes are heavily damped, with only α the
  low ones. For ζ₁ at f₁ and ζ₂ at f₂, α and β follow from the formulas in Mecway's
  manual (§9.26).
- **Dampers** usually give **non-proportional** damping: the shape is then complex
  (the nodes no longer move in phase). The log reports `IMAG` > 1%; Mecway shows the
  real part, and the effective mass (from the real part) is an approximation (the
  sum over the modes can exceed 100% slightly; MC-03: 107%).
- **Overdamped modes** (ζ ≥ 1) do not vibrate and are not given by Code-Aster; you
  then get fewer modes than requested (alarm `ALGELINE5_79`). The same holds for
  rigid body modes in a free model (s = 0 or real): mode 1 is then the first elastic
  mode (MC-05).

### 6.4 Not possible

- Stresses per mode with complex modes (only the shape; INFO).
- Rayleigh damping on a selection (in Mecway, too, only the whole model with *mode
  superposition*, §9.26): not translated, reported at the end of the run.
- Hysteretic (structural) damping (`AMOR_HYST`, complex stiffness), modal damping as
  ζ per mode (the *Extra modal damping* of the mode superposition response is not a
  matrix and does not count here), damping in buckling and acoustics.
- The imaginary part of the shape to Mecway (only the real part). mecway.exe does
  know an imaginary displacement internally (`DisplacementXImaginary`), but the name
  in the `.liml` and the display have not been investigated.
- Overdamped modes (ζ ≥ 1).

### 6.5 Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| INFO: Modal: Rayleigh damping (...) / dampers (...) is not included | damping in the model, setting off (default, like Mecway) | intended? Otherwise switch on *Complex modes with damping* |
| INFO: Complex modes requested, but the model has no damping | setting on without Rayleigh or dampers | normal: real modes; add damping in Mecway |
| INFO: Complex modes: ... no stresses per mode | *Result fields* with `stresses`/`vonmises` | shapes only; switch the setting off for stresses per (undamped) mode |
| WARNING: Negative Rayleigh coefficient | α < 0 or β < 0 | check the input: negative damping makes modes grow |
| WARNING: Code-Aster alarm ALGELINE5_79 (fewer modes than requested) | overdamped modes (ζ ≥ 1) or rigid body modes, which do not vibrate | lower α (low modes) or β (high modes) to see them; see ζ per mode in the log |
| WARNING: Code-Aster alarm FACTOR_11 | singular stiffness in the factorisation: normal for complex modes in a free model (seen in MC-05, results equal to Mecway) | without a free model: check the supports |
| `<EXCEPTION> ALGELINE2_71` | `SORENSEN` with `PLUS_PETITE` for a quadratic problem (only with your own `#ASTER` code) | the bridge itself uses `TRI_DIAG` or `CENTRE` |
| alarm `ALGELINE5_15` | the error norm of a mode is above `SEUIL` (seen with search frequency 100 Hz on MC-04: the `.mess` gave 0.000001 with a limit of 0.000001, f_d and ζ equal to `TRI_DIAG` to 1e-9) | harmless if just above the limit; otherwise *Mode check* 1e-5 |

## 7. Cyclic symmetry

A structure made of N identical segments around an axis (disc, impeller, rotor,
bolted flange) can be computed as one sector. Each mode shape of the whole wheel then
belongs to a **number of nodal diameters** ND = 0 … N/2 (rounded down): the shape
repeats from segment to segment with a phase shift of ND·360°/N.

**What Mecway does** (Mecway Ltd., 2026, §9.41; measured headless with Mecway 33):
the *Cyclic symmetry* constraint couples a master and a slave cut face. In a
*Frequency* analysis Mecway computes the *Number of modes* per ND and orders them by
ND and frequency (ring with 12 segments and 2 modes: 14 modes, ND 0 … 6). A pair of
standing waves (0 < ND < N/2) counts as one mode. The solution shows the whole wheel.
In the `.liml`:
`<cyclicsymmetry axis="3" segments="12" selectionmaster="A" selectionslave="B" />`
with `axis` 1 = X, 2 = Y, 3 = Z (the axis through the origin).

**What the bridge does**: Code-Aster `MODE_ITER_CYCL` (EDF R&D, U4.52.05; cyclic
substructuring, R4.06.03) on the sector, with the same modes in the same order as
Mecway; in Mecway the shapes are shown, as in Mecway's own solution, on the **whole
wheel** (setting `cyclic_full_wheel`, on by default; off = only the sector).

### 7.1 Workflow

1. **Model in Mecway**: one segment (sector) with **the same node patterns on both
   cut faces** (Mecway requires that with the internal solver too). Solid elements
   only; with hex8 preferably quadratic (hex20) rather than `LINE_QUAD` (not possible
   here, §7.5).
2. **Analysis type** *Frequency* with *Number of modes* = the number of modes **per
   nodal diameter** (like Mecway; the total is that times N/2 + 1).
3. **Cyclic symmetry**: choose the node or face selection of one cut face as master
   and that of the other as slave, the axis (X, Y or Z, through the origin) and the
   number of segments of the **whole** wheel. Which side is the master does not
   matter (the bridge determines the direction of rotation itself).
4. **Supports**: as usual (e.g. *Fixed support* on the hub). On a cut face nodes may
   only be **fully** fixed (§7.5). A free wheel (without supports) is possible too:
   there are then rigid body modes at ~0 Hz in ND 0 and 1.
5. **Loads** give, as in §2.5, a prestressed modal analysis (e.g. *Centrifugal
   force* about the symmetry axis: stress stiffening and spin softening).
6. **Main window**: `auto` (or `modal_3d`), result route `liml`. *Start*.

| Setting (label) | Key | Default | When to change |
|---|---|---|---|
| Cyclic symmetry: sector modes in the basis (0 = automatic) | `cyclic_base_modes` | 0 = max(20, 4 × modes per ND) | with many modes per ND or when the highest modes per ND matter: increase; as a check, run with twice as many, the frequencies should stay the same (§7.3) |
| Search frequency [Hz] | `modal_shift_hz` | 0 | > 0: per ND the modes closest to this frequency (`OPTION='CENTRE'`); < 0 makes no sense here (the sector with fixed cut faces has no rigid body modes) |
| Prestress from loads | `modal_prestress` | on | as §1.2 |
| Number of modes (without maxmode) | `modal_modes` | 10 | as §1.2, per ND |
| Cyclic symmetry: the whole wheel to Mecway | `cyclic_full_wheel` | on | off for a large model if the result file becomes too large (the wheel is N times as large as the sector); the frequencies stay the same |

`modal_norm`, `modal_complex` and stresses per mode (`fields`) do not apply with
cyclic symmetry (INFO or WARNING in the log).

### 7.2 How the bridge translates

`bridge_cyclic.py`, template `AsterTemplate_ModeIterCycl.comm`, in the job
`aster_cyclic.py`:

1. **Pairs**: each master node gets the slave node at ±360°/N about the axis (within
   1e-5 × the model size); the side at +360°/N becomes `GAUCHE`, the other `DROITE`
   (Code-Aster: trigonometric direction, U4.52.05 §1; the other way round gave
   `<EXCEPTION> ALGORITH16_58`). Nodes on the axis form the interface `AXE`. Fully
   fixed nodes on a cut face are left out of the interfaces; if only one node of a
   pair is fixed, the bridge fixes the other one too (INFO). The pairs are node
   groups `BRCYC_D`, `BRCYC_G`, `BRCYC_A`, `BRCYC_F` in the mesh, in the same order.
2. **Axis**: `MODE_ITER_CYCL` requires the Z axis. With an X or Y axis the bridge
   writes the coordinates with a cyclic permutation of the axes (a rotation of 120°
   about (1, 1, 1): the symmetry axis becomes Z) and converts the directions in the
   loads along with it (DX/DY/DZ, FX/FY/FZ, directions of gravity and centrifugal
   force); the job rotates the mesh and the shapes back. Measured: the ring about X
   gave bit-identical frequencies and shapes as about Z (CY-03).
3. **Basis** (Craig-Bampton): `ASSEMBLAGE` with the cut faces fixed (`DDL_IMPO`),
   `CALC_MODES` with `cyclic_base_modes` sector modes, `DEFI_INTERF_DYNA` (`CRAIGB`)
   and `DEFI_BASE_MODALE CLASSIQUE` (plus one static mode per degree of freedom of the
   cut faces). With prestress first `MECA_STATIQUE` with the relations of ND 0
   (`LIAISON_DDL`: u_gauche = R(360°/N) u_droite; nodes on the axis axial only), then
   K + K_g (+ `RIGI_ROTA`) as §2.5.
4. `MODE_ITER_CYCL` with `NB_SECTEUR` = N, `NB_DIAM` = 0 … N/2 (`TOUT_DIAM` computes one
   ND too many for an odd N) and `NMAX_FREQ` = modes per ND; `REST_SOUS_STRUC
   SECTEUR=1` gives the shapes on the sector (note: `NOM_CHAM` is `'ACCE'` by default,
   the bridge asks for `'DEPL'`).
5. **The whole wheel** (`cyclic_full_wheel`): `DEFI_SQUELETTE` (`CYCLIQUE`,
   `SECTEUR=_F(TOUT='OUI')`) builds a skeleton with the N sectors and `REST_SOUS_STRUC
   SQUELETTE` puts each mode on it: sector j is the sector rotated by +j·360°/N, with
   the phase of the ND (test cases sdlv134a, sdls04a, sdls01c).
6. `aster_cyclic.collect`: per ND the modes in ascending order, of a pair the first
   member, line `BRIDGE_MODE nr FREQ=.. ND=..` in the `.mess` (and `BRIDGE_CYCL ...
   WIEL=1` if the wheel succeeded); it matches every node of Mecway's wheel by
   coordinate to the skeleton. `aster_results_export` writes the modes as `<mode>` in
   Mecway's numbering of the wheel, and `bridge_results_liml.splice_results` puts the
   nodes and elements of all sectors in the model copy of `<solution>`, exactly like
   Mecway's own cyclic solution (below). If the wheel fails, the sector goes to Mecway
   (WARNING in the `.mess`, §7.6).

**Mecway's format of the whole wheel** (measured headless with Mecway 33 on CY-01,
CY-04, CY-05, Mecway's Impeller and variants with two element sets, a loose node and
swapped master/slave): the model copy in `<solution>` has N copies of all nodes and
elements. Node i of sector j (0 … N−1) is numbered **i + j·n** (n = number of nodes
of the model) and lies on the sector rotated by **+j·360°/N** about the axis
(right-handed, independent of which side is the master); element e is numbered **e +
j·ne** (ne = highest element number) with the nodes of its sector; per element set
the elements are listed sector by sector. The nodes on the cut faces and on the axis
are copies too (not merged). Selections, loads and `<cyclicsymmetry>` stay those of
the sector. The bridge writes the same: checked against Mecway's own solution (same
node and element numbers, elements and element set order equal, coordinates ≤ 1e-15
m), and Mecway's API reads the bridge's wheel like its own (headless `mecway.exe
<model> script`: 960 nodes, 72 elements, 14 modes, `node_value` on all nodes,
`interpolate` in an element of the last sector).

Test cases as a syntax source: sdlv134a (3D, nodes on the axis), sdls04a/b (plate),
sdlv301a (impeller); catalogue `mode_iter_cycl.py` (code_aster 17.4).

### 7.3 Interpretation

- **Log and status box**: `Mode 7: 72.8659 Hz (ND 3)`. In Mecway under *Solution*
  the modes in the same order as Mecway's own solution: first all modes of ND 0, then
  ND 1, etc. Mode k of ND d is mode d × (modes per ND) + k.
- **ND = 0**: all segments move alike (e.g. the disc as an umbrella, the blades in
  phase). **ND = N/2** (even N): neighbouring segments in antiphase. **0 < ND < N/2**:
  the shape has ND nodal lines through the centre; each mode has a second one with
  the same frequency (the same shape, rotated by a quarter wave). The full model
  gives those pairs as two modes (CY-02: 25.7385 Hz twice); Mecway and the bridge
  show one.
- **What you see in Mecway** (`cyclic_full_wheel` on): the shape on the **whole
  wheel**, as in Mecway's own solution. At ND = 0 all sectors move alike; at 0 < ND <
  N/2 you see one standing wave with ND nodal lines (of a pair the first member; the
  second is the same shape rotated by a quarter wave about the axis and is not in
  Mecway); at ND = N/2 the sign alternates from sector to sector. Which standing wave
  of a pair you see (the position of the nodal lines) is arbitrary and can differ
  from the one in Mecway's own solution. With the setting off: only the sector. The
  scale of the shape is arbitrary (as with REST_SOUS_STRUC; `modal_norm` does not
  apply here), and therefore also different from Mecway.
- **A mode with n waves around the circumference** appears at ND = n if n ≤ N/2, and
  otherwise at the mirrored ND (|n − kN|); for a ring with 12 segments the mode with
  12 waves falls in ND 0 (aliasing; measured: 1402.72 Hz, a pair in the full model).
- **Accuracy**: the basis (sector modes + static modes) is exact for the statics; the
  dynamics depend on the number of sector modes. Measured (§7.4), the lowest modes per
  ND with the default basis equalled the full model (≤ 0.0012%). High modes per ND
  (near the highest sector modes in the basis) can be slightly too high: run with
  twice as many as a check.
- **Effective mass** is not given here (Mecway neither: "Effective mass not available
  with MPCs or cyclic symmetry", mecway.exe).
- **Hand calculation**: thin ring in its plane f_n = 1/(2π)·√(EI/(ρAR⁴))·n(n² −
  1)/√(n² + 1) (Blevins, 1979); clamped circular plate f = λ²/(2πa²)·√(D/(ρh)) with
  λ² = 10.216 (ND 0), 21.26 (ND 1), 34.88 (ND 2), 51.03 (ND 3) (Leissa, 1969).

### 7.4 Measured (verification CY, [`Verification.md`](Verification.md) §7)

| Model | Against | Deviation |
|---|---|---|
| free ring, 12 segments about Z (CY-01) | full model (CY-02) / Mecway / Blevins | ≤ 2e-6 / ≤ 2e-6 / +0.59 … +1.18% (thin ring theory) |
| the same ring about X (CY-03) | idem | equal to CY-01 (bit-identical) |
| clamped plate, 6 segments, nodes on the axis (CY-04) | Mecway / Leissa | ≤ 0.03% / +0.58 … +0.66% |
| rotating disc about Y, 3000 r/min, hub fixed, 12 segments (CY-05) | full model (CY-06) / Mecway | ≤ 0.0012% / ≤ 0.0012% |
| Mecway's sample Impeller (17 segments about Y, 100 000 r/min, hex20 + wedge15; not in the suite) | Mecway | +0.01 … +0.92%; the sector without cyclic symmetry deviates as much (+0.02 … +0.79%): a difference in the elements, not in the cyclic route (KNOWN_BUGS 62) |
| shapes on the whole wheel: ring (CY-01) and rotating disc (CY-05), every mode | full model (CY-02, CY-06): subspace MAC within the frequency band (a pair: both modes) | 1 − MAC ≤ 5.2e-7 (criterion 1e-3); cut faces continuous ≤ 1.3e-14 |
| nodes on the axis (CY-04, ND 1) | Mecway's own solution | jump between the copies on the axis 6.2e-4 relative (Mecway itself 9.4e-4) |

### 7.5 Not possible

- Cyclic symmetry outside the modal analysis (static, nonlinear, thermal): not
  translated, ERROR; the model is then computed as a single sector.
- Shells, beams and springs (Mecway neither in a *Frequency* analysis), `LINE_QUAD`.
- A partial support or a relation (symmetry, frictionless, pinned, constraint
  equation, coupling) on a node of a cut face; Mecway allows an axial displacement
  and a zero radial one with the internal solver.
- 8 segments with nodes on the axis (a bug in Code-Aster 17.4, §7.6).
- With an X or Y axis: loads with a function or formula, `LIAISON_OBLIQUE`
  (symmetry/frictionless on oblique faces); `#ASTER` code is computed in the rotated
  frame (WARNING).
- A double eigenvalue within ND 0 (e.g. the ring mode with n = N waves, which falls in
  ND 0): `MODE_ITER_CYCL` does not find the second one correctly (measured +1.3%,
  also with 80 sector modes). In ND N/2 a double eigenvalue was fine.
- Both members of a pair, stresses per mode, complex modes and effective mass. On the
  whole wheel only the displacements.

### 7.6 Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Cyclic symmetry: the slave nodes do not lie at +/-360/N degrees from the master nodes | a different number of segments, a different axis, the axis not through the origin, or node patterns that do not match | check *Number of segments* and the axis; put the axis through the origin; make the cut faces with the same mesh (e.g. the sector by copying and rotating) |
| ERROR: ... master and slave have a different number of nodes | the selections differ in size | select the complete cut faces |
| ERROR: ... a partial support or a relation on the cut faces | a support that does not fix all displacements on a cut face node | remove the support from the cut face, or fix those nodes completely |
| ERROR: ... 8 segments and nodes on the axis | Code-Aster 17.4 (`ctetax.F90`): at 45° cos − sin = 0 and DX "is missing" (`ALGORITH14_95`) | a small hole on the axis (no nodes on the axis), or compute the full model |
| ERROR: Cyclic symmetry about the X/Y axis: ... cannot rotate ... | a load the bridge cannot convert to the Z axis | rotate the model in Mecway so that the symmetry axis is Z |
| ERROR: Cyclic symmetry with elem_hex8 = LINE_QUAD is not possible | the new midside nodes have no pair | hex20 in Mecway, or `elem_hex8` = `3D` |
| ERROR: Cyclic symmetry is only translated in a modal analysis | Mecway's *Static*, *Nonlinear static* or *Thermal* with cyclic symmetry | compute the full model, or only the modes |
| `<EXCEPTION> ALGORITH16_52` "axe de symétrie cyclique différent de Oz" | Code-Aster did not find the pairs about the Z axis (the bridge already sets noise around 0 in the coordinates to 0) | report the model (KNOWN_BUGS 61) |
| `aster_cyclic: WARNING: ... modes from MODE_ITER_CYCL, expected ...` (in the `.mess`) | Code-Aster gave a different number of modes; the ND per mode is unknown | the frequencies are correct; report the model |
| `aster_cyclic: WARNING: the whole wheel was not built (...)` or `... skeleton of the whole wheel not built` (in the `.mess`); in the log "In Mecway only the sector" | Code-Aster's skeleton did not fit Mecway's wheel (e.g. a node of the wheel without a skeleton node at that place) | the modes and frequencies are correct, only the sector is in Mecway; report the model, or switch `cyclic_full_wheel` off |

## 8. References

- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold, table 8-1 (beams) and table 9-2 (rings). Not consulted locally;
  the formulas have been recomputed in the verification
  ([`Verification.md`](Verification.md), MO-01, CY-01).
- EDF R&D. *Code_Aster, documentation U4.52.05: Opérateur MODE_ITER_CYCL* (version
  30-05-2016, online copy) and *R4.06.03: Sous-structuration dynamique cyclique*: the Z
  axis as symmetry axis, DROITE/GAUCHE in trigonometric direction, the interface AXE
  (only ND 0 and 1). Syntax checked in the catalogues `mode_iter_cycl.py`,
  `rest_sous_struc.py`, `defi_interf_dyna.py` (code_aster 17.4) and the source code
  `bibfor/algorith/ctetax.F90` (gitlab.com/codeaster/src, check of the axis nodes).
- EDF R&D (2025). *code_aster 17.4, test cases* sdlv134a, sdls04a/b, sdlv301a (cyclic
  substructuring).
- Leissa, A.W. (1969). *Vibration of Plates*. NASA SP-160, table 2.1 (clamped circular
  plate). Not consulted locally; the values have been recomputed in the verification
  (CY-04).
- EDF R&D. *Code_Aster, documentation U4.52.02: Opérateur CALC_MODES*. Document number
  verified via the reference in U2.08.04; the document itself is not available
  locally. Defaults checked in the catalogue
  `lib/aster/code_aster/Cata/Commands/calc_modes.py` (code_aster 17.4).
- EDF R&D (2018). *Code_Aster, documentation U2.08.04: Notice de calcul au flambage*.
  Version "default", 12-01-2018 (local copy).
- EDF R&D (2021). *Code_Aster, documentation U4.61.21: Opérateur ASSEMBLAGE*. Version
  "default", 03-11-2021 (local copy).
- EDF R&D (2020). *Code_Aster, documentation U4.51.03: Opérateur STAT_NON_LINE*.
  Version "default", 30-04-2020 (local copy), §3.18 `CRIT_STAB`. Defaults checked in
  the catalogue `Cata/Commands/stat_non_line.py` (code_aster 17.4).
- EDF R&D (2025). *code_aster 17.4, test cases* sdll101a (tensioned beam, "corde à
  piano", `RIGI_MECA` + `RIGI_GEOM`) and sdll133a (rotating wheel, `RIGI_GEOM` +
  `RIGI_ROTA`); ssll105d/e/f (`CRIT_STAB` in `STAT_NON_LINE`), ssnl502d
  (pre-deformation along the buckling mode with `MODI_MAILLAGE DEFORME`) and hsna105a
  (deforming the mesh and restoring it), `share/aster/tests` of the installation;
  sdld21c, sdld23a and sdld27a (mass-spring systems with dampers, `CALC_MODES` with
  `MATR_AMOR`, `FREQ` and `AMOR_REDUIT`).
- Clough, R.W. & Penzien, J. (1993). *Dynamics of Structures* (2nd ed.). New York:
  McGraw-Hill, chapters 2 and 3 (damped free vibration, resonance). Not consulted
  locally; the formulas have been recomputed in the verification (MC-01..05).
- EDF R&D (2025). *code_aster 17.4, message catalogue*
  (`lib/aster/code_aster/Messages/algeline2.py`, `algeline3.py`, `algeline5.py`): texts
  of the ALGELINE messages named here.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: §6.3
  Frequency (stress stiffening, modal effective mass), §6.6 Buckling, §6.9.2
  complex acoustic modes, §7.8 Damper, §9.26 Rayleigh damping, §9.41 Cyclic
  symmetry, §11.9
  BucklingPlateNonlinear, §11.20–11.22 samples VibratingMembrane, Impeller and
  VibratingString.
- Southwell, R.V. (1932). On the analysis of experimental observations in problems of
  elastic stability. *Proceedings of the Royal Society of London A*, 135, 601–616. Not
  consulted locally; the method has been recomputed in the verification (NK-03).
- Timoshenko, S.P. & Gere, J.M. (1961). *Theory of Elastic Stability*, 2nd ed. New
  York: McGraw-Hill, chapter 1 (bar with initial curvature), §2.1, §2.3, §5.3
  (torsional and flexural-torsional buckling) and §9.2. Not consulted locally; the
  formulas have been recomputed in the verification (BU-01, BU-02, BU-04,
  BU-30 … BU-36, NK-03).
- EDF R&D (2019). *Code_Aster, documentation R3.08.01: Éléments "exacts" de poutres*.
  Version "default", 22-11-2019 (local English machine translation), §6 (geometric
  stiffness `RIGI_GEOM`: axial force, moments, shear forces and the terms of moderate
  rotations at the nodes).
- EDF R&D (2025). *code_aster 17.4, test case* ssll105a/b (right-angle frame,
  out-of-plane buckling, `POU_D_E`/`POU_D_T`; `VALE_REFE` 1.088 and 0.68 with
  `REFERENCE='NON_DEFINI'`), `share/aster/tests` of the installation. The literature
  source behind that reference has not been checked.
