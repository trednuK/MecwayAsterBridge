# Welding: moving heat source, residual stress, distortion and metallurgy

*Nederlandse versie: [Lassen.md](../Lassen.md)*

The temperature field of a weld bead: a heat source moving at constant speed along a
path, in a transient thermal analysis (Mecway *Thermal transient*, T31 → `ther_3d`,
`THER_LINEAIRE` or `THER_NON_LINE`; see [Thermal.md](Thermal.md)). With a *Thermal
stress* in the same model the bridge then computes, in the same job, the **residual
stress and distortion** (`STAT_NON_LINE` with the temperature as the load, §9). With
`#ASTER-METALLURGIE` the bridge also computes the **phase transformations** in steel
(ferrite, pearlite, bainite, martensite, austenite), the **hardness** and, as an option,
their effect on the residual stress (§10). Code: `Scripts/bridge_welding.py` (the
source), `Scripts/bridge_thermal.py` (the rest of the thermal model),
`Scripts/bridge_thermomech.py` (the mechanical chain), `Scripts/bridge_metallurgy.py`
(metallurgy). Code-Aster 17.4.

Two input routes, both without Mecway extensions:

| Route | When | How |
|---|---|---|
| **A. `#ASTER-LASBRON`** (recommended) | an ordinary weld source along a straight line or a path of nodes | one line in Mecway's *Custom model definition*: power, efficiency, speed, path and the Goldak dimensions; the bridge builds the source, chooses the elements, checks time step and mesh and reports after the run how much of the power the mesh takes up |
| **B. Mecway formula** | your own source shape, or also solving the model with Mecway's own solver | *Internal heat generation* (elements) or *Heat flux* (faces) with a formula in x, y, z and t; the bridge translates the formula literally into a Code-Aster `FORMULE` |

There is **no separate analysis**: a T31 model with a weld source simply runs in
*Thermal* (`ther_3d`, also via `auto`); add a *Thermal stress* and the
mechanical chain follows by itself (§9); a line `#ASTER-METALLURGIE` adds the phases
(§10); filler material that is only "born" when the source passes: key
`geboorte=`/`birth=` (§11). Limits: §7, §9.7, §10.8 and §11.6.

## 1. Workflow in Mecway, step by step

Example: verification model `TestFiles/Verificatie/modellen/WE-02.liml` (open it in
Mecway): half a steel plate (symmetry plane y = 0) of 55 × 15 × 15 mm, a 30 mm weld
along the x axis on the top face z = 0, 5 mm/s, 1000 W into the workpiece.

### 1.1 The model

1. **Geometry and mesh.** Solid elements (hex8, hex20, tet, wedge). Make the mesh
   **fine along the bead**: elements no larger than 0.8 × the smallest semi-axis of the
   source in that direction (§4.2). In the example: 0.5 mm up to 7 mm from the path,
   larger outside (up to ~3 mm). A symmetry plane through the path halves the number of
   elements: an insulated face (no boundary condition) is the symmetry plane.
2. **Material.** *Thermal*: conductivity and specific heat, plus the density.
   Temperature dependent is allowed (*Temperature dependent*: tables for λ(T) and c(T),
   Mecway manual §8.6); the bridge then uses `THER_NON_LINE` (§6).
3. **Analysis.** *Analysis settings* → *Thermal transient*; *Time period* = the welding
   time plus any cooling time, *Time step* according to §4.1 (example: 6 s, 0.1 s).
4. **Initial temperature.** *Initial conditions* → *Temperature* on all nodes (e.g.
   293.15 K). Without an initial temperature Mecway, and therefore the bridge, starts at
   0 K.
5. **Boundaries.** Convection and radiation on the free faces are allowed
   (*Convection*, *Radiation*); in the example all faces are insulated, so that the
   energy balance can be checked exactly.

### 1.2 The weld source (route A)

In *Analysis settings* choose the CCX solver (the outline tree then shows *CCX* →
*Custom model definition*) and type (example WE-02):

```
** ASTER-LASBRON Q=1250, eta=0.8, v=0.005, start=(0.01, 0, 0), richting=(1, 0, 0)
** ASTER-LASBRON af=0.001, ar=0.002, b=0.001, c=0.001, symmetrie=1
```

- All values in **SI**: W, m/s, m, s (like all `#ASTER` lines). Coordinates are those
  of the Mecway model in metres: a point at 10 mm is written as 0.01.
- Consecutive lines belong to one source; a line starting with `Q=` (or with the word
  `new`/`nieuw`) starts the next source (several layers or welds one after the other,
  each with its own `t0`).
- In an OpenRadioss field write `#ASTER-LASBRON`, in Mystran `$ASTER-LASBRON`
  ([ASTER_lines_examples.md](ASTER_lines_examples.md) §1). `#ASTER-WELD` also works.
- The keys have English synonyms (§2): `direction=` for `richting=`, `symmetry=` for
  `symmetrie=`, etc.

### 1.3 Or: the source as a Mecway formula (route B)

Make an element selection with the elements along the bead (the formula is evaluated
in every Gauss point of those elements at every step; a small selection is faster) and
apply *Internal heat generation* with a formula, e.g. a Gaussian half sphere with r =
0.75 mm, 1000 W, 5 mm/s from x = 10 mm (verification WE-03; unit W/m³, position in mm,
time in s):

```
4.423879394e12*e^(-3*((x-10-5*t)^2+y^2+z^2)/0.75^2)
```

Mecway has no `exp`: write `e^(...)`. The bridge converts the formula to Python (`^` →
`**`, functions such as `sin`, `heaviside`, `unittriangle`) with the units from the
Mecway attributes. The same route works for *Heat flux* on faces, *Convection*
(coefficient, ambient temperature), *Radiation* and *Temperature* (verification WE-06).

### 1.4 Starting and following the run

Main window: *Active analysis* `auto` (or *Thermal*), *Start*. The log (`<model>_<run-id>_bridge_log.txt`) shows per source (INFO lines stay
Dutch):

```
INFO: #ASTER-LASBRON 1: brongroep automatisch, 9718 elementen binnen 0.006 m van de baan.
INFO: #ASTER-LASBRON 1: verspringing 0.0005 m per stap (0.167 x af + ar).
INFO: #ASTER-LASBRON 1: elementen langs de baan tot 0.50 x de halve as (along the weld direction).
INFO: #ASTER-LASBRON 1: Goldak, Q_eff = 1000 W (eta 0.8), v = 0.005 m/s, baan 0.03 m van t = 0.0 tot 6 s, ...
```

(source group chosen automatically, jump per step, element size relative to the
semi-axes, the source data.) After the run the status box shows the **energy check**:
how much of η·Q the mesh actually takes up, at five times (example: "the mesh takes up
100.0..100.0% of the power 500 W"; 500 W because of `symmetrie=1`). If it deviates
more than 2%, a WARNING follows: the mesh is too coarse for the source, or the source
lies partly outside the model.

### 1.5 Results in Mecway

`temperature` per time step (Kelvin) and the heat flux `heatflux*`, as in any
transient thermal analysis. Look at the temperature history in a node next to the bead
(*Graph* of a node over time), the peak temperature per node (the fusion zone is where
it exceeds the melting temperature) and the isotherms behind the source.

## 2. Keys of `#ASTER-LASBRON`

| Key (synonyms) | Unit | Default | Meaning | When to change |
|---|---|---|---|---|
| `Q` (`vermogen`, `power`) | W | required | arc power U·I | - |
| `eta` (`rendement`, `efficiency`) | - | 1 | fraction of Q entering the workpiece (0 < η ≤ 1) | TIG ~0.6–0.7, MIG/MAG ~0.8, submerged arc ~0.9 (literature values, NOT measured by the bridge) |
| `v` (`snelheid`, `speed`) | m/s | required | welding speed | - |
| `start` (`begin`) | m | - | start point (x, y, z) of a straight path | - |
| `richting` (`dir`, `direction`) | - | - | direction of the straight path (normalised) | - |
| `lengte` (`length`) | m | until the end of the analysis | length of the straight path | the weld stops before the end of the analysis (cooling) |
| `pad` (`path`, `baan`) | `<<node selection>>` | - | path through nodes (instead of start/direction): the nodes become a chain starting at the node closest to `start` (otherwise at an end) | curved or kinked weld (piecewise straight) |
| `diepte` (`depth`) | - | (0, 0, −1) | direction into the material (normal to the surface) | the weld face is not the top face z = max |
| `af`, `ar` | m | required (or `r`) | semi-axis in front of and behind the source (along the weld direction) | calibrate on the fusion zone (macro etch); rule of thumb af ≈ half width, ar ≈ 2–4 × af (Goldak et al., 1984; NOT measured by the bridge) |
| `b` | m | required (or `r`) | half width (transverse) | idem: half width of the fusion zone |
| `c` | m | required (or `r`) | depth | penetration depth |
| `r` | m | - | af = ar = b = c = r (Gaussian half sphere) | a simple source |
| `ff`, `fr` | - | 2af/(af+ar), 2ar/(af+ar) | front/rear distribution (q continuous in the source) | only if the literature gives other values; ff + fr ≠ 2 gives a WARNING (power (ff+fr)/2·η·Q) |
| `t0` (`tstart`) | s | 0 | start time of the source | second layer or second weld |
| `t1` (`teind`, `tend`) | s | end of the path | end time of the source | stop the source earlier |
| `groep` (`group`) | `<<element selection or component>>` | selections/components with prefix `LASNAAD_`, otherwise automatic | elements the source acts on | your own choice; the automatic group is all solid elements within 3 × the largest semi-axis of the path |
| `symmetrie` (`symmetry`) | - | 0 | number of symmetry planes through the path (only for the energy check: the mesh gets 1/2ⁿ of the source) | half plate: 1 |
| `geboorte` (`birth`) | `ja`/`yes` / `nee`/`no` / `<<selection>>` | `no` | filler material that is only born when the source passes (§11) | welding with filler material, several layers |
| `voorloop` (`lead`) | m | 2 × `af` | distance ahead of the source at which the filler is born (§11.2) | rarely |

An unknown key, a missing required value or a value that is not a number gives an
ERROR and the run stops (§8).

## 3. How the bridge translates

- **Source shape** (Goldak et al., 1984), with ξ along the weld direction relative to
  the current source position, η transverse, ζ the depth:
  q = 6√3·f·η·Q / (a·b·c·π√π) · exp(−3ξ²/a² − 3η²/b² − 3ζ²/c²), a = af and f = ff in
  front of the source (ξ ≥ 0), a = ar and f = fr behind it. Over the half space below
  the surface the integral is (ff + fr)/2·η·Q. Position s(t) = v·(t − t0) along the
  path; outside [t0, t1] and past the end of the path q = 0. On a kinked path the axes
  follow each segment.
- **Code-Aster**: a Python function `_lb_goldak` in the `.comm`, a
  `FORMULE(NOM_PARA=('X', 'Y', 'Z', 'INST'))` and `AFFE_CHAR_THER_F` `SOURCE` on the
  source group (catalogue `affe_char_ther_f.py`); the load is in `EXCIT` of
  `THER_LINEAIRE`/`THER_NON_LINE`. Code-Aster evaluates the source per step in the
  Gauss points (θ-weighted between the start and end of the step, setting `theta`).
- **Source group**: solid elements only (shells and beams get no source, WARNING).
  Automatic: elements within 3 × the largest semi-axis of the path (outside it q is
  < 2·10⁻¹² of the peak); this limits the computing time of the formula.
- **Energy check** (after the solve, in the job): `CALC_VECT_ELEM` `CHAR_THER` +
  `ASSE_VECTEUR` gives the nodal loads of the source as the solver integrates them;
  their sum is the power the mesh takes up. Line `BRIDGE_LASBRON <source> <t> <W>
  <target W>` in the `.mess`, summarised in the log and the status box.
- **Route B** (formula): `FORMULE` with the Mecway expression, x/y/z/t converted with
  `positionunit`/`timeunit` and the result with `unit` (mechanical loads: see
  [UserGuide.md](UserGuide.md), Formulas). In steady state (T30) a formula in t gets the value at t = 1 s (like
  a time table).
- **Several sources together**: all sources given as a function (weld sources, and
  *Internal heat generation*s with a formula or time table) are put in **one** load;
  per part of the mesh a `FORMULE` adds up the sources that lie there. Otherwise
  Code-Aster 17.4 computes two `AFFE_CHAR_THER_F` loads with `SOURCE` in one analysis
  both with the function of the first. A weld source and a formula or table source can
  therefore be combined (TH-42).
- **Shells in the model** that the bridge computes as `PLAN` and rotates for that
  ([Thermal.md](Thermal.md) §3): the path and formulas are rotated along.

## 4. Settings: time step, mesh, theta

### 4.1 Time step

The source jumps v·Δt per step. The bridge gives a **WARNING if v·Δt > ½(af + ar)**,
with the step that satisfies it. Measured (WE-01/WE-01b, Gaussian source r = 0.75 mm,
h = 0.5 mm, θ = 0.57; deviation of the temperature from the analytical solution for
the same source, `tests_lassen.goldak_exact`):

| v·Δt | next to the source (3 mm) | on the weld axis 6 mm behind |
|---|---|---|
| (af + ar)/6 (Δt = 0.05 s) | −1.4% | −0.25% |
| (af + ar)/2 (Δt = 0.15 s, limit of the warning) | −2.2% | −2.9% |
| 1 × (af + ar) (Δt = 0.3 s) | −4.9% | −26% (the source skips nodes) |

Relative to the run with (af + ar)/6 the limit is −0.8% (next to the source) and −2.7%
(weld axis); those numbers are in the comment at `bridge_welding.MAX_JUMP`. It is a
deviation of the temperature, not an energy loss: the energy at t = 6 s is +0.06% for
both steps (WE-01, WE-01b; measured again on 07-10-2026, the row 1 × (af + ar) when it
was built).

Advice: v·Δt ≤ (af + ar)/2 for the temperature field next to the bead, ≤ (af + ar)/6
for peak temperatures on the weld axis. After welding (cooling) a larger step is fine:
use a second analysis or a step that fits everywhere.

### 4.2 Mesh along the bead

The source is integrated per element with 2 Gauss points per direction (hex8).
Integration error per direction, worst position of the source relative to the
elements (computed): 0.03% at h = 0.67·a, 0.3% at 0.8·a, 1.8% at 1.0·a, 7.6% at
1.33·a (a = the semi-axis in that direction). The bridge gives a **WARNING if an
element along the path is larger than 0.8 × the semi-axis in some direction** (weld
direction: min(af, ar); transverse: b; depth: c). The energy check after the run shows
the actual effect (WE-01, h = 0.67 r: +0.09%; a trial model with elements of 2 × r:
+19%).

Further out the mesh may become coarser, but not too fast: the temperature field next
to and behind the source is steep. In WE-01 the fine zone is 7 mm wide and deep (~10 ×
the source radius), followed by 5 elements growing geometrically to 15 mm.

### 4.3 Theta

`theta` (page *Thermal*, default 0.57) stays. Measured on a WE-01 variant (h = 0.375
mm, Δt = 0.15 s, Δt·a/h² ≈ 7): Crank-Nicolson (0.5) gave 21% less than θ = 0.57 on the
weld axis 6 mm behind the source (non-monotone scheme at a large Δt·a/h²); θ = 1
differed up to 10% from 0.57 (higher next to the source, lower obliquely behind it). A
smaller step makes θ less important.

## 5. Interpretation

- **Rosenthal** (1946): a point source Q on a semi-infinite insulated body gives in the
  quasi-steady state T − T0 = Q/(2πkR)·exp(−v(R + ξ)/(2a)). Outside the source (R ≥ 4 ×
  the source radius) the FEM solution is within 1% of it (WE-01; with v·Δt at the
  warning limit 3.6%, WE-01b). Closer to the source the source shape determines the
  temperature; Rosenthal has no meaning there.
- **Source parameters** are not material constants: calibrate af, ar, b, c (and η) on a
  measured fusion zone (macro etch) or thermocouple. The temperature inside the fusion
  zone is model dependent; temperatures outside the fusion zone and cooling times
  (t8/5) are more reliable.
- **Latent heat**: the bridge has no latent heat; include it in c(T) (a peak around the
  melting range, *Temperature dependent*), so that the enthalpy is right.
- **Energy balance**: without convection and radiation ∫ρ(H(T) − H(T0))dV = η·Q·t
  (WE-01/02/05: ≤ 0.06%); smaller with losses.
- **Comparison with Mecway** (route B, WE-03, headless): Mecway integrates the formula
  in the same way (energy equal to 1e-4), but applies the load at the end of the step
  (KNOWN_BUGS 14): the source then runs v·Δt/2 ahead. Next to the source Mecway is
  therefore warmer (WE-03, Δt = 0.05 s: +4.6% relative to the bridge, +3.2% relative to
  the analytical solution; estimate exp(v²Δt/(4a)) − 1 = 5%), on the weld axis 6 mm
  behind it colder (−2.1% / −2.3%); Mecway is within 1.5% of the analytical solution at
  t + Δt/2. A smaller step reduces the difference proportionally.

## 6. Temperature-dependent λ and c (Mecway *Temperature dependent*)

Mecway writes `<thermal type="TempDependent">` with `<thermalconductivity temp=".."
value=".."/>` and `<specificheat temp=".." value=".."/>` rows (linearly interpolated,
outside the table the nearest point: Mecway manual §8.6). The bridge turns this into
`DEFI_MATERIAU` `THER_NL` (`LAMBDA` and `RHO_CP` as `DEFI_FONCTION` of the
temperature, `PROL` constant) and computes with `THER_NON_LINE` (`newton_*` settings
of the *Thermal* page). Two adjustments, measured with Code-Aster 17.4 (WE-04b):

- the ρc table is extended to 0 K and to 10 000 K above the last point, and refined to
  points every 10 degrees: `THER_NON_LINE` works with the enthalpy β(T) it derives
  from the table points; with only Mecway's points 13% of the energy was missing after
  the first step (2.8% after 2 s), now 0.01%;
- λ(T) stays as entered (WE-04a: exactly equal to the Kirchhoff solution).

Mecway itself uses an apparent c(T): its energy balance is off by 0.2–0.3%; the
temperatures are within 0.15% of the bridge (WE-04b).

## 7. Not (yet) possible

- **Mechanical chain** (residual stress, distortion): see §9; its limits in §9.7.
- **Filler material that is born**: possible with `birth=` (§11); its limits in
  §11.6.
- **Metallurgy** (phases, hardness, transformation strain): §10; its limits in §10.8.
- The weld source only acts on **solid elements**, not on shells or beams.
- Only the **Goldak** shape (and the Gaussian half sphere as a special case); another
  shape (conical, surface Gaussian) can be given as a Mecway formula (route B).
- A **curved path** is piecewise straight between the nodes of `pad`; the speed is
  constant.
- Route B: a formula in x, y, z for a *total* heat flow (*Heat flow*), for convection
  or radiation on a **shell face** or as an initial temperature is not translated
  (ERROR with the reason).

## 8. Messages → cause → solution

| Message (log) | Cause | Solution |
|---|---|---|
| `ERROR: #ASTER-LASBRON needs a transient thermal analysis` | the model is T30 (steady state) or mechanical | Mecway *Thermal transient* (T31) |
| `WARNING: #ASTER-LASBRON only works in a transient thermal analysis ...; ignored here` | the line is in a mechanical model | remove it, or make the analysis T31 |
| `ERROR: #ASTER-LASBRON: unknown or incomplete '...'` | typo in a key, or a `key` without `=` | a key from §2 |
| `ERROR: #ASTER-LASBRON (source n): missing: ...` | Q, v or the dimensions are missing | add them (or `r=`) |
| `ERROR: ... give the path: start=... and direction=..., or path=<<node selection>>` | no path | `start` + `direction`, or `path` |
| `ERROR: ... '...' has no valid value` | not a number, vector without three values, selection without `<< >>` | `start=(0.01, 0, 0)`, `path=<<Name>>` |
| `ERROR: ... no solid elements within ... m of the weld path` | path outside the model, usually mm instead of m | coordinates in metres |
| `ERROR: ... path '...' is not a node selection with nodes` | wrong name, or a face/element selection | a node selection along the weld |
| `ERROR: ... the source group has no solid elements` | `group` points at shells or beams | an element selection with solid elements |
| `WARNING: ... the source jumps ... m per time step` | v·Δt > ½(af + ar) | smaller *Time step* (advice in the message) |
| `WARNING: ... elements along the weld path are ... m` | mesh coarse relative to the source | refine the mesh along the bead (§4.2) or enlarge the source |
| `WARNING: ... at the end of the analysis ... the source has not yet reached the end of the path` | *Time period* shorter than the welding time | longer duration, or `length`/`t1` |
| `WARNING: Weld source n: the absorbed power deviates more than 2%` | coarse mesh, the source lies partly outside the model, or a symmetry plane without `symmetry=` | refine the mesh; `symmetry=1` for a half plate (if the mesh takes up 1/2 or 1/4 of the source, the message names `symmetry=1` or `2`) |
| `WARNING: ... ff + fr = ... <> 2` | your own ff/fr | intended? Otherwise leave ff/fr out |
| `ERROR: Not translated: heatflow on '...': formula in x, y, z for a total heat flow` | route B with *Heat flow* | *Internal heat generation* (W/m³) or *Heat flux* (W/m²) |

## 9. Residual stress and distortion: the thermal → mechanical chain

A T31 model with a **Thermal stress** (Mecway manual §9.25) is computed twice by the
bridge in one Code-Aster job: first thermally as above, then mechanically
(`STAT_NON_LINE`) with the temperature field of every time step as the load. Mecway
itself only uses a Thermal stress in a mechanical analysis, but keeps it (with Fixed
support, Displacement and the mechanical material data) in a thermal model too; the
bridge then reads them. Without a Thermal stress it stays an ordinary thermal analysis
(the mechanical constraints do not count, INFO in the log). There is no separate
analysis and no setting to switch on: `auto` sends T31 to *Thermal* (`ther_3d`) and
the Thermal stress switches the chain on.

### 9.1 Workflow in Mecway, step by step

Example: `TestFiles/Verificatie/modellen/WE-10.liml` (open it in Mecway): a half plate
40 × 15 × 5 mm (symmetry plane y = 0) with a 30 mm bead on the top face.

1. **Thermal model** as in §1: *Thermal transient*, initial temperature, the weld
   source (`#ASTER-LASBRON`) and the thermal boundaries. Let the analysis run long
   enough to cool down (§9.5): the residual stress is the stress at the last time.
2. **Material**, tab *Mechanical*: *Young's modulus*, *Poisson's ratio* and *Thermal
   expansion coefficient* (no α means no thermal strain: WARNING). Plasticity (tab
   *Plastic*): *Bilinear isotropic*/*kinematic* (yield strength, *tangent modulus*) or a
   hardening curve. Temperature-dependent E, ν, α, yield strength and hardening are not
   known to Mecway (manual §8.6: only λ and c): they come from `#ASTER-MATERIAL`
   (§9.2).
3. **Supports**: *Fixed support* or *Displacement* (a Displacement is a displacement
   along one direction; for x and z use two constraints). Hold a freely shrinking part
   **statically determinate**: symmetry planes plus one node with x and z fixed and a
   second node with only z fixed (WE-10). Clamping prevents the shrinkage and gives
   higher residual stresses (and less distortion).
4. **Thermal stress** with the initial temperature as *Reference temperature*
   (WARNING if different: there is then thermal strain at t = 0 already). Mecway may
   only offer Thermal stress, Fixed support and Displacement for a mechanical analysis
   type: then first set the analysis to *Static 3D*, add them, and set the analysis back
   to *Thermal transient* (Mecway keeps them; checked headless with Mecway 33 on WE-08:
   the constraints stay in the saved `.liml` and Mecway solves the thermal part without
   a message). That the GUI shows them this way is NOT checked in the Mecway GUI.
5. Optionally `#ASTER-MATERIAL` in *Custom model definition* (§9.2).
6. Main window: *Active analysis* `auto` (or *Thermal*), *Start*.

Mecway receives per time step: `temperature` and `heatflux*` (thermal) and `displ*`,
`stress*`, `vonmises`, `reactionforce*`, `plasticstrain*` and
`equivalentplasticstrain` (mechanical; all by default, or the choice under *Result
fields to Mecway* if a mechanical field is ticked there). The log and the status box
show the summary at the last time (line `Thermomechanical, t = ...`): temperature
range, largest displacement per direction, von Mises and the range of σxx, σyy, σzz,
and the largest cumulative plastic strain.

### 9.2 `#ASTER-MATERIAL`: temperature-dependent mechanical properties

```
** ASTER-MATERIAL Steel: TC=(20, 200, 400, 600, 800, 1000, 1200, 1500),
** ASTER-MATERIAL     E=(210e9, 200e9, 180e9, 120e9, 60e9, 30e9, 15e9, 10e9),
** ASTER-MATERIAL     SY=(355e6, 300e6, 250e6, 150e6, 50e6, 25e6, 15e6, 10e6),
** ASTER-MATERIAL     ALPHA=(1.2e-5, 1.25e-5, 1.3e-5, 1.35e-5, 1.4e-5, 1.45e-5,
** ASTER-MATERIAL            1.5e-5, 1.5e-5), H=1e9, TC_CUT=1500
```

A line starting with `<Mecway material>:` starts a material; the following lines
without a name belong to it (a list may run over two lines). Also `#ASTER-MATERIAAL`.
Only in the thermal → mechanical chain; values in SI.

| Key | Unit | Default | Meaning | When to change |
|---|---|---|---|---|
| `T` or `TC` | K or °C | - | temperatures of the table (increasing); required with lists | always with temperature-dependent values |
| `E` | Pa | Mecway *Young's modulus* | Young's modulus | literature table of the material; above ~1200 °C not below ~5% of E(20 °C) (convergence) |
| `NU` | - | Mecway *Poisson's ratio* | Poisson's ratio | rarely |
| `ALPHA` | 1/K | Mecway *Thermal expansion coefficient* | **mean (secant) expansion coefficient** relative to `T_ALPHA`: ε_th = α(T)·(T − T_ALPHA) | tables often give the mean α from 20 °C: then set `TC_ALPHA=20`; convert an *instantaneous* α first |
| `T_ALPHA` / `TC_ALPHA` | K / °C | reference temperature of the Thermal stress | temperature at which ε_th = 0 in the table (`TEMP_DEF_ALPHA`) | if the α table has another reference |
| `T_CUT` / `TC_CUT` | K / °C | none | above this temperature the thermal strain stays constant (melting; Lindgren 2001) | **always in welding**: the solidus or melting temperature. Without a cut-off the strain keeps growing in the weld pool (4.6% at 3400 K in WE-10b) and the mechanical step converges badly |
| `SY` | Pa | Mecway *yield strength* (bilinear) | yield strength | literature table; above ~1200 °C a small value (e.g. 10 MPa) |
| `H` | Pa | Mecway *tangent modulus* | plastic modulus dσ/dε_p (as Mecway's tangent modulus, [Settings_contact_and_nonlinear.md](Settings_contact_and_nonlinear.md)) | linear hardening |
| `ET` | Pa | - | instead of `H`: slope after yield in **total** strain (Code-Aster `D_SIGM_EPSI`) | if the table is given that way; ET = E·H/(E + H) |
| `hardening` (`versteviging`) | `iso` / `kin` | the Mecway type (isotropic if not plastic) | isotropic (`VMIS_ISOT_LINE`) or kinematic (`VMIS_CINE_LINE`) hardening | kinematic for repeated heating/cooling (Bauschinger effect, multi-pass welding) |

A single number is a constant; a list has as many values as `T`. Linearly
interpolated, constant outside the table (like Mecway's own tables, §8.6). A missing
key takes the Mecway value. With `SY` (or `H`/`ET`) the material becomes bilinear
plastic, also when the Mecway material is elastic; a Mecway hardening curve
(`TRACTION`) is then replaced (WARNING). Without `#ASTER-MATERIAL` the chain uses the
constant Mecway values, also with a hardening curve.

### 9.3 Settings

Page *Thermal* (`ther_3d`); the Newton and convergence settings apply to both solves.

| Setting (key) | Default | When to change |
|---|---|---|
| *COMPORTEMENT DEFORMATION* (`deformation`) | PETIT | small strains and rotations: fine for most welds (WE-07..10). `GDEF_LOG` only for large distortion (thin plates that buckle); NOT verified in the chain |
| *Strain definition hardening curve* (`plastic_strain_definition`) | auto | only with a Mecway hardening curve (see Nonlinear static) |
| *Max. Newton iterations*, *Convergence RESI_GLOB_RELA*, *NEWTON REAC_ITER* | 20, 1e-6, 1 | with `BRIDGE_ONVOLLEDIG` (not converged): first check `TC_CUT` and E/SY above 1200 °C, then `convergence_resi_rela` 1e-5 |
| *Element formulation hex8* (`elem_hex8`, page Elements) | 3D | **LINE_QUAD with plasticity**: linear hex8 'lock' in plastic flow (§9.5, WARNING); the temperature then goes to the quadratic mesh with `PROJ_CHAMP`. Takes ~5× longer |
| *Time step* (Mecway) | - | the mechanical steps are the thermal ones (§4.1); if Code-Aster cuts a step (`DECOUPE`), only the thermal times are stored |
| *Time limit run_aster* (`time_limit`) | 1800 s | the chain takes much longer than the thermal part alone (WE-10: hex8 ~10 min, LINE_QUAD ~1 hour); raise it, otherwise Code-Aster stops halfway |

### 9.4 How the bridge translates

- After the thermal solve and the flux the result is called `res_ther`; then a second
  model (`PHENOMENE='MECANIQUE'`, `3D`) on the same mesh, with the constraints as in
  *Nonlinear static*.
- `AFFE_MATERIAU` `AFFE_VARC=_F(NOM_VARC='TEMP', EVOL=res_ther, NOM_CHAM='TEMP',
  VALE_REF=<reference>)` (U4.43.03; syntax source test case hsnv100e). The computation
  is in °C (see [Thermal.md](Thermal.md)), so `VALE_REF` and the functions of TEMP too.
- Material: `ELAS` (constant) or `ELAS_FO` with `DEFI_FONCTION` of TEMP for E, ν, α
  (`TEMP_DEF_ALPHA` = `T_ALPHA`), `ECRO_LINE` / `ECRO_LINE_FO` (`SY`, `D_SIGM_EPSI` =
  E·H/(E + H) per table point) or `TRACTION` (Mecway hardening curve, constant in T);
  relation `VMIS_ISOT_LINE`, `VMIS_CINE_LINE` or `VMIS_ISOT_TRAC`.
- `STAT_NON_LINE` at the thermal times (`DEFI_LIST_INST` with `ECHEC DECOUPE`,
  `ARCHIVAGE` at the thermal times, so that temperature and stress per step belong
  together); then `CALC_CHAMP` (`SIGM_NOEU`, `SIEQ_NOEU`, `EPSP_NOEU`, `VARI_NOEU`,
  `REAC_NODA`) and the summary (`BRIDGE_THERMOMECA` in the `.mess`).
- `#ASTER` code and `#ASTER-EXCIT` belong to the thermal part; `#ASTER-POST` comes after
  the mechanical post-processing (`res` there is the mechanical result, `res_ther` the
  thermal one).

### 9.5 Interpretation

- **Residual stress** = the stress at the last time, if the part is (nearly) back at
  the initial temperature there: look at the temperature range in the summary. A
  remaining temperature difference ΔT still gives a thermal stress of the order E·α·ΔT
  (2.5 MPa per K for steel).
- **Pattern** (Radaj 1992, Masubuchi 1980): along the bead tension in the welding
  direction of the order of the yield strength, compression next to it that balances
  the tension; smaller stresses transverse to the weld. For a free part the net force
  and the net moment over every cross-section are zero (check in WE-10: 0.02% of SY·A and 1% of
  SY·A·t).
- **Distortion**: longitudinal and transverse shrinkage and angular distortion (the
  edges rotate towards the weld side for a bead on a plate). A simple upper bound for
  the transverse shrinkage of a fully penetrated plate: α·q/(v·ρ·c·t) (the heat per
  length as uniform heating of a strip that shrinks completely).
- **Hex8 and plasticity**: linear, fully integrated hex8 'lock' in volume-preserving
  plastic flow and give too high, often triaxial stresses in the weld (WE-10 with `3D`:
  σxx in the weld 1.3–2.6 × SY from top to bottom, σzz 190 MPa in the middle of a 5 mm plate). Use
  `LINE_QUAD` or hex20/tet10 in Mecway for the stresses in and next to the weld; the
  equilibrium and the distortion are usable with hex8.
- **Weld pool**: above `T_CUT` the thermal strain freezes; E and SY are at the last
  table value there. The stresses in the weld pool itself have no physical meaning;
  without `birth=` the bead is there from the start; with `birth=` (§11) only once the
  source passes.

WE-10 (half plate 40 × 15 × 5 mm, 1000 W, 5 mm/s, edge y = 15 mm at T0, cooling until
60 s; temperature at the end 293.2..301.3 K), measured with hex8 `3D` (see above) and
LINE_QUAD:

| Quantity (cross-section x = 20 mm, t = 60 s) | hex8 `3D` (WE-10) | LINE_QUAD (WE-10b) |
|---|---|---|
| σxx in the weld (y = 0), top / middle / bottom | 466 / 641 / 923 MPa | 400 / 446 / 350 MPa |
| σyy in the weld, top / middle | 163 / 418 MPa | 5 / 135 MPa |
| σzz in the weld, middle (free surface at 2.5 mm) | 194 MPa | −5 MPa |
| von Mises in the weld, top / (SY + H·p) | 1.002 | 1.014 |
| σxx at the edge y = 15 mm, top / middle / bottom | −372 / −364 / −329 MPa | −357 / −367 / −326 MPa |
| width of the tensile zone (mid-thickness) | ~5.5 mm | ~5.5 mm |
| net force N/(SY·A); moment M/(SY·A·t) | −0.0002; −0.010 | 0.0005; −0.0004 |
| angular distortion (dz(y = 15) − dz(0))/15 mm, bottom | 8.9 mrad (0.51°) | 12.4 mrad (0.71°) |
| sag of the weld axis relative to the supports (x = 20 mm) | 0.054 mm | 0.076 mm |
| longitudinal shrinkage over 40 mm, weld axis / edge | 0.013 / 0.041 mm | 0.011 / 0.046 mm |
| transverse shrinkage full plate, mid-thickness / top (upper bound α·q/(v·ρ·c·t) = 0.103 mm) | 0.077 / 0.126 mm | 0.085 / 0.151 mm |
| largest cumulative plastic strain | 0.069 | 0.071 |
| Newton iterations per step; computing time (loaded pc) | 3–4; 10 min | 10; 53 min |

Comparison with the literature (qualitative; Radaj 1992, Masubuchi 1980): with
LINE_QUAD the longitudinal stress in the weld is 400–450 MPa, equal to the current yield
strength SY + H·p (355 MPa + 1 GPa × 0.05) and hence "of the order of the yield
strength"; the transverse stress is small at the surface; next to the weld compression
that balances the tension. The compressive zone is large here (up to ~SY at the edge)
because the plate is narrow (15 mm half width): in a wide plate the compression is lower
and spread further. The edges rotate towards the weld side (angular distortion for a
bead with partial penetration), the plate shrinks along and across the weld; the
transverse shrinkage at mid-thickness is below the upper bound of a fully shrinking
strip. Hex8 `3D` gives the same pattern and equilibrium, but through locking a too high,
triaxial stress in the weld and a stiffer plate (angular distortion 28% smaller).

### 9.6 Verification

[Verification.md](Verification.md) §8, WE-07..WE-10: free expansion (strain α·ΔT,
stress 0), uniaxially restrained with bilinear hardening (σ = −E·α·ΔT, yielding,
residual stress E·p after cooling back) and with E(T), SY(T), α(T) (`#ASTER-MATERIAL`,
also reverse yielding during cooling: residual stress = SY(T0)): all within 4·10⁻⁸ of
the hand calculation (tolerance 0.1% and 1%). Weld bead WE-10: equilibrium and the
qualitative pattern.

### 9.7 Not possible

- Only **solid elements** (no shells, beams, springs); contact and couplings
  (RBE2/RBE3) are not computed by the chain.
- Only a **transient** thermal analysis (T31); steady state (T30) with a Thermal
  stress: use Mecway's *Transfer temperatures from solution* and a static analysis.
- The mechanical steps are the thermal ones; a larger step for cooling is not possible
  (one *Time step* in Mecway).
- Without `birth=` the bead is present from t = 0 and carries load even before it is
  welded (limited with `T_CUT` and low E/SY above the melting temperature); with
  `birth=` it is not (§11).
- **Metallurgy** (phases and transformation strain) only with `#ASTER-METALLURGIE`
  `mechanica=ja` (§10.4); even then no annealing of the hardening: plastic strain from
  heating remains after melting (no 'annealing').
- No temperature-dependent **hardening curve** (`TRACTION` per temperature); only
  bilinear (`ECRO_LINE_FO`).
- No creep or viscoplasticity.

### 9.8 Messages → cause → solution

| Message (log) | Cause | Solution |
|---|---|---|
| `INFO: Mechanische belasting '...' telt niet mee in de thermische analyse (alleen met een Thermal stress ...)` | T31 with supports but without Thermal stress | add a Thermal stress (§9.1) if you want residual stress |
| `ERROR: Thermomechanical without mechanical constraints` | no Fixed support / Displacement | hold statically determinate (§9.1 step 3) |
| `<SolverError> <MECANONLINE9_4>` in the `.mess`, `BRIDGE_ONVOLLEDIG 0.0` | singular matrix: the part can still move freely (a Displacement is one direction) | a separate Displacement per direction; fix the six rigid-body motions |
| `ERROR: Thermomechanical ...: solid elements only` | shells, beams or springs in the model | solid elements |
| `ERROR: Thermomechanical: elset(s) ... have no thermal material` | a part without thermal conductivity | assign a thermal material |
| `WARNING: ... the reference temperature of Thermal stress ... is not the initial temperature` | Reference temperature ≠ Initial condition | make them equal |
| `WARNING: ... has no thermal expansion coefficient` | α = 0 | *Thermal expansion coefficient* or `ALPHA` |
| `WARNING: Plastic hex8 elements ... stay linear` | `elem_hex8` = 3D with plasticity | `LINE_QUAD` or quadratic elements (§9.5) |
| `ERROR: #ASTER-MATERIAL ...: unknown or incomplete` / `has no valid value` | typo, not a number or list | keys of §9.2 |
| `ERROR: #ASTER-MATERIAL ...: lists ... need the temperatures` / `... has n values, T has m` | list without `T`/`TC`, or unequal length | `TC=(...)` with as many values |
| `ERROR: #ASTER-MATERIAL '...': no (mechanical) material with that name` | name differs from the Mecway material | the exact Mecway name (case, spaces) |
| `ERROR: ...: ET >= E at ... K` | tangent modulus too large at a high temperature (small E) | use `H`, or a smaller ET |
| `ERROR: ...: H/ET without SY` | hardening without a yield strength | give `SY` |
| `WARNING: #ASTER-MATERIAL only works ...; ignored here` | the line is in a mechanical model or a thermal model without Thermal stress | add a Thermal stress (T31), or remove the line |
| `BRIDGE_ONVOLLEDIG <t>` / `MECANONLINE` in the `.mess` | the mechanical step does not converge, even after cutting | set `TC_CUT`, E and SY above 1200 °C not extremely small, `convergence_resi_rela` 1e-5, smaller *Time step* |
| `WARNING: Thermomechanical: the time steps ... differ` | (should not happen) | report it; the temperature in Mecway may belong to another step |

## 10. Metallurgy: phases, hardness and the effect on residual stress

Welding changes the structure of steel: above Ac1 the transformation to **austenite**
starts, above Ac3 the steel is fully austenitic; on cooling, austenite transforms back
into **ferrite**, **pearlite**, **bainite** or (cooled fast, below Ms) **martensite**.
Which phase forms depends on the cooling rate (the CCT diagram, TRC in Code-Aster:
*transformation en refroidissement continu*). Code-Aster computes this after the thermal
solve with `CALC_META` (Waeckel's model), per element node, from the temperature
history. The bridge puts the phase fractions and the hardness per time step into
Mecway; with `mechanica=ja` the thermal → mechanical chain (§9) uses a **metallurgical
law**: the volume change of the transformation (transformation strain) and a yield
strength per phase.

Mecway has no metallurgy: the input is one `#ASTER-METALLURGIE` line per Mecway
material, with a **standard dataset** (CCT diagram and transformation data from a
Code-Aster test case, §10.3) or your own CCT diagram in `#ASTER` code.

### 10.1 Workflow in Mecway, step by step

Example: `TestFiles/Verificatie/modellen/MT-06.liml` (the weld bead of WE-10, thermal
only) and `MT-07.liml` (the same bead with the metallurgical law in the chain).

1. **Thermal model** as in §1: *Thermal transient* (T31), initial temperature, weld
   source (`#ASTER-LASBRON` or a formula) and the thermal boundaries. Let the analysis
   run long enough to cool below ~100 °C: martensite only forms below Ms (16MND5:
   415 °C).
2. **Metallurgy**: in *Custom model definition* (next to the `ASTER-LASBRON` lines),
   with the exact Mecway material name before the colon:

   ```
   ** ASTER-METALLURGIE Staal: staal=16MND5, begin=ferriet, TAUX_1=0.001, TAUX_3=0.001
   ```

   For welding always use a small `TAUX_1`/`TAUX_3` (§10.5).
3. **Residual stress with phases** (option): a *Thermal stress* as in §9.1, and
   `mechanica=ja` in the same line with the expansion of austenite and the strain
   difference (§10.4):

   ```
   ** ASTER-METALLURGIE Staal: staal=16MND5, begin=ferriet, TAUX_1=0.001,
   ** ASTER-METALLURGIE     TAUX_3=0.001, mechanica=ja, ALPHA_A=2.35e-5, DEPS=1.0e-2
   ```

4. Main window: *Active analysis* `auto` (or *Thermal*), *Start*.

Mecway receives per time step the phase fractions `ferrite`, `pearlite`, `bainite`,
`martensite`, `austenite` (0..1; sum 1) and, with hardness data, `hardness` (HV). The
group *metallurgy* in *Result fields to Mecway* is always included with
`#ASTER-METALLURGIE`. The log and the status box show the summary (line `Metallurgy, t =
...`): the range of each phase at the last time, the largest austenite fraction during
the run (peak temperature), the number of nodes that became (partly) austenite (the
**heat-affected zone**, HAZ) and the hardness range.

### 10.2 Keys of `#ASTER-METALLURGIE`

Same form as `#ASTER-MATERIAAL` (§9.2): `<Mecway material>: key=value, ...`; the
following lines without a name belong to it. Also `#ASTER-METALLURGY`. Temperatures of
`META_ACIER` in **°C** (as in Code-Aster), the rest in SI.

| Key (synonyms) | Unit | Default | Meaning | When to change |
|---|---|---|---|---|
| `staal` (`steel`, `dataset`) | - | (or `trc`) | standard dataset: `16MND5` or `HSNV101A` (§10.3) | another steel: `trc` |
| `trc` | name | - | a `DEFI_TRC` from `#ASTER` code (example 25 in [ASTER_lines_examples.md](ASTER_lines_examples.md)); `AR3`, `ALPHA`, `MS0`, `AC1`, `AC3`, `TAUX_1`, `TAUX_3` are then required | your own steel with a measured CCT diagram |
| `AR3`, `MS0`, `AC1`, `AC3` | °C | dataset | start of ferrite on cooling; martensite start (Ms); start and end of austenite on heating | data of your own steel |
| `ALPHA` | 1/K | dataset | Koistinen-Marburger: Z_M = 1 − exp(ALPHA·(Ms − T)), **negative** | literature value β ≈ 0.011: `ALPHA=-0.011` |
| `TAUX_1`, `TAUX_3` | s | dataset (0.34) | time constant of austenitisation at Ac1 and Ac3 | **0.001 for welding** (§10.5) |
| `LAMBDA0`, `QSR_K`, `D10`, `WSR_K` | - | none | grain growth (`META_ACIER`, NOT verified) | only with data |
| `HV` (`hardheid`, `hardness`) | HV | dataset (16MND5: 184, 184, 309, 450, 100) | hardness of ferrite, pearlite, bainite, martensite, austenite (`DURT_META`); the bridge gives the linear mixture Σ Z·HV | other values for the steel |
| `begin` (`initial`) | phase or 5 fractions | `ferriet` | structure at t = 0: `ferriet`/`ferrite`, `perliet`/`pearlite`, `bainiet`/`bainite`, `martensiet`/`martensite`, `austeniet`/`austenite` or `(Zf, Zp, Zb, Zm, Za)` summing to 1 | bainitic base metal (quenched and tempered 16MND5): `bainiet`; a quench from austenite: `austeniet` |
| `korrel` (`grain`) | - | dataset (16MND5: 11) | austenite grain size at t = 0 (with `GRAIN_AUST`) | rarely |
| `mechanica` (`mechanics`) | yes/no | no | metallurgical law in the thermal → mechanical chain (§10.4) | residual stress with transformation strain |
| `ALPHA_F`, `ALPHA_A`, `DEPS`, `REF`, `SY…`, `ET…`/`H…`, `T`/`TC` | | | mechanical data per phase (§10.4) | with `mechanica=ja` |

An unknown key, a missing required value or a value that is not a number gives an ERROR
and the run stops (§10.9).

### 10.3 Standard datasets

| `staal=` | Source | Contents | Use |
|---|---|---|---|
| `16MND5` | Code-Aster test case **mtlp103a** (V4.61.103, "trempe d'un barreau en 16MND5"; 16MND5 = A508 cl. 3, pressure-vessel steel) | CCT diagram with 29 cooling histories (0.05 .. 400 °C/s; ferrite, bainite), `GRAIN_AUST DREF=11`, `TEMP_MS` (SEUIL 0.38, AKM −30.791, BKM 11.698, TPLM −1), AR3 830, MS0 415, ALPHA −0.0249, AC1 724, AC3 846, TAUX 0.34 s, hardness 184/184/309/450/100 HV; no mechanical data | welding and quenching of low-alloy steel; without data of your own the best starting point |
| `HSNV101A` | Code-Aster test case **hsnv101a** (fictitious steel of the test case) | CCT with 2 histories (bainite between 600 and 345 °C), MS0 200, ALPHA −0.03, and the mechanical data of the test case (α_f 15·10⁻⁶, α_a 23.5·10⁻⁶, DEPS 2.52·10⁻³ at 900 °C (`REF=warm`), yield strength and slope per phase as functions of T) | verification only (MT-01) |

The data are in `Scripts/bridge_metallurgy.py` (`DATASETS`), literally from the test
case. A dataset belongs to one steel grade: another steel (S355, ...) needs its own CCT
diagram (`trc=`, example 25 in [ASTER_lines_examples.md](ASTER_lines_examples.md)); the 16MND5 diagram then only gives an indication.

### 10.4 Residual stress with phases (`mechanica=ja`)

With a *Thermal stress* (§9) and `mechanica=ja` the chain uses the metallurgical law
`META_P_IL` (isotropic linear hardening per phase, test case hsnv101a). Two effects on
the residual stress:

- **Transformation strain**: the cold phases (ferrite, pearlite, bainite, martensite)
  have a larger volume than austenite. Code-Aster (`ELAS_META_FO`) uses one strain for
  all cold phases and one for austenite; with `REF=koud` (cold; default for a cold
  `begin`, reference = the *Reference temperature* of the Thermal stress):

  ε_th = (1 − Z_a)·α_f·(T − T_ref) + Z_a·(α_a·(T − T_ref) − DEPS)

  and with `REF=warm` (hot; default for `begin=austeniet`):
  ε_th = Z_a·α_a·(T − T_ref) + (1 − Z_a)·(α_f·(T − T_ref) + DEPS). On heating the steel
  therefore shrinks by DEPS between Ac1 and Ac3; on cooling it expands again below Ms
  (martensite) or in the bainite range. Both formulas were checked by hand (MT-04,
  MT-05: ≤ 6·10⁻⁶; `warm` via hsnv101a, MT-01).
- **Yield strength per phase** with a linear mixture rule; hard martensite yields
  later.

| Key | Unit | Default | Meaning | When to change |
|---|---|---|---|---|
| `ALPHA_A` | 1/K | dataset; otherwise **required** | mean (secant) expansion of austenite from T_ref | always (literature: ~2.2–2.4·10⁻⁵) |
| `DEPS` | - | dataset; otherwise **required** | strain of cold phases − austenite at T_ref (`EPSF_EPSC_TREF`) | always; ~1·10⁻² at 20 °C (from hsnv101a: 2.52·10⁻³ at 900 °C converted to 20 °C) |
| `ALPHA_F` | 1/K | Mecway *Thermal expansion* or `ALPHA` of `#ASTER-MATERIAAL` | expansion of the cold phases | rarely |
| `REF` | `koud`/`warm` (`cold`/`hot`) | follows `begin` | reference phase at T_ref (`PHASE_REFE`) | rarely: the reference is the phase at t = 0 |
| `SY_F`, `SY_P`, `SY_B`, `SY_M`, `SY_A` (or `SY` for all) | Pa | Mecway *yield strength* / `SY` of `#ASTER-MATERIAAL` | yield strength per phase | martensite and bainite higher, austenite lower |
| `H_F` .. `H_A` or `ET_F` .. `ET_A` (or `H`/`ET`) | Pa | Mecway / `#ASTER-MATERIAAL` | hardening per phase (plastic modulus H or slope ET) | if known |
| `T` / `TC` | K / °C | - | temperatures for lists (as §9.2); one list for all keys of the line | temperature-dependent values |

E and ν come from the Mecway material or `#ASTER-MATERIAAL`; `TC_CUT` from
`#ASTER-MATERIAAL` also applies to α_a and α_f. The bridge does not give the equivalent
plastic strain (`equivalentplasticstrain`) with this law (the internal variables are
hardening variables per phase, V7 is a stress; seen in hsnv101a and MT-07); the plastic
strain tensor (`plasticstrain*`) is given.

### 10.5 Time step and TAUX: measured behaviour of `CALC_META`

| What | Measured (Code-Aster 17.4) | Consequence |
|---|---|---|
| Austenitisation, slow (10 °C/s, Δt 0.1 s) | Z_a follows dZ/dt = (Z_eq − Z)/τ exactly (Z_eq linear between Ac1 and Ac3; MT-03: ≤ 2·10⁻⁸ between Ac1 and Ac3, 0.22% just above Ac3) | - |
| Austenitisation, fast (1000 °C/s) | exact with ΔT = 4 °C per time step; with 40 °C per step ~8× slower (at 1020 °C 9% instead of 51% austenite); in welding (WE-10, Δt 0.3 s: 240 to 1800 °C per step) the weld axis became only 6% austenite with τ = 0.34 s | **for welding `TAUX_1=0.001, TAUX_3=0.001`**: the steel is then almost immediately austenite above Ac3 (equilibrium), also with large steps (MT-06). The bridge gives a WARNING when nodes got well above Ac3 but became < 90% austenite |
| Martensite (Koistinen-Marburger) | exact, independent of the time step (MT-02, MT-08) | - |
| Retained austenite | Code-Aster stops the martensite formation at ~0.4–0.7% austenite (16MND5: 0.69%; ALPHA −0.05: 0.41%; with ALPHA −0.011 and Ms 300 °C not yet reached at 20 °C: 4.6%, = KM). Cause NOT found | martensite ≤ 99.3% (16MND5) |
| CCT at fast cooling | 16MND5 at 200 °C/s: still 3% bainite, although the fastest history with a transformation is −80 °C/s; at 1000 °C/s martensite only | the interpolation between histories is Code-Aster's; NOT investigated further |
| Partial austenite (peak between Ac1 and Ac3) | the austenite transforms to bainite/martensite on cooling; the original ferrite stays (MT-06: peak 796 °C → 44% ferrite, 20% bainite, 36% martensite) | intercritical HAZ |

Time step for cooling: the phases depend on the cooling rate around 800–500 °C (t8/5),
which follows from the thermal result. The step of §4.1 (jump of the source) is usually
small enough.

### 10.6 How the bridge translates

- `META_ACIER=_F(TRC=trc_<dataset>, AR3, ALPHA, MS0, AC1, AC3, TAUX_1, TAUX_3)` and
  `DURT_META` in the **thermal** `DEFI_MATERIAU` (as in hsnv101a: THER + META_ACIER in
  one material); the CCT diagram as `DEFI_TRC` before the materials. With your own
  `trc=` the `DEFI_TRC` is in `#ASTER` code (after the materials in the `.comm`): then
  a separate `DEFI_MATERIAU` and `CHAM_MATER` for `CALC_META` (alarm `RESULT1_39` is
  then intended).
- After the thermal solve: initial state `CREA_CHAMP` `CART_VAR2_R` (V1..V5 = the
  phases, V6 = sum of cold phases, V7 = grain size), `CALC_META(reuse=res,
  COMPORTEMENT=_F(RELATION='ACIER'), OPTION=('META_ELNO', 'META_NOEU'))` and with
  hardness `OPTION=('DURT_ELNO', 'DURT_NOEU')`; only on the elsets of the material.
- In Mecway: `META_NOEU` V1..V5 → `ferrite` .. `austenite`, `DURT_NOEU` HV →
  `hardness` (nodal average, like the other nodal fields).
- Chain (`mechanica=ja`): `AFFE_VARC=(_F(NOM_VARC='TEMP', ...), _F(NOM_VARC='M_ACIER',
  EVOL=res_ther, NOM_CHAM='META_ELNO'))`, `DEFI_MATERIAU(ELAS_META_FO=_F(E, NU,
  F_ALPHA, C_ALPHA, PHASE_REFE, EPSF_EPSC_TREF, TEMP_DEF_ALPHA, F1_SY..C_SY,
  SY_MELANGE), META_ECRO_LINE=_F(F1_D_SIGM_EPSI..C_D_SIGM_EPSI))` and
  `COMPORTEMENT=_F(RELATION='META_P_IL', RELATION_KIT=('ACIER',))`; everything else as
  in §9.4.

### 10.7 Interpretation

- **Heat-affected zone**: nodes that became (partly) austenite (summary: number of nodes
  > 1% austenite). Peak above Ac3: fully transformed (coarse-grained HAZ, fusion zone);
  between Ac1 and Ac3: intercritical (mixture of old ferrite and new phases); below Ac1:
  unchanged. Tempering of martensite by a second pass is not available (`ACIER_REVENU`
  not translated).
- **Martensite and hardness**: much martensite and a high hardness in the weld and the
  HAZ point to too fast cooling (cold-cracking susceptibility; preheating lowers the
  cooling rate). The hardness is a linear mixture of the phase hardnesses.
- **Residual stress**: the transformation strain counteracts the shrinkage on cooling.
  MT-07 (16MND5, Ms 415 °C) compared with WE-10 without metallurgy: in the martensite (weld axis, top and
  mid-thickness) the longitudinal stress σxx drops from 466 / 641 MPa to 176 / 4 MPa;
  the tensile peak moves to the edge of the transformed zone (y = 3 mm: 407 / 349 MPa)
  and to the bottom of the weld, which did not transform (794 MPa; WE-10 923 MPa).
  Equilibrium holds (net force 0.0009 SY·A, moment −0.004 SY·A·t), the angular distortion
  drops from 8.9 to 5.2 mrad, the transverse shrinkage stays 0.073 mm (WE-10 0.077 mm).
  This is the known effect of the martensite expansion (filler metals with a low Ms are
  used to lower the residual stress for this reason); with linear hex8 (locking, §9.5)
  and illustrative phase data the numbers are qualitative only. Run time 14 min.
- The phases are nodal values (`META_NOEU`, averaged over the adjacent elements); with a
  coarse mesh a narrow HAZ is smeared out.

### 10.8 Not possible

- Only **transient thermal** (T31) and only **solid elements** (`CALC_META` has no
  shells; a material with metallurgy on a shell gives an ERROR).
- Only the steel model `ACIER` (Waeckel); no tempering (`ACIER_REVENU`), no zirconium
  (`ZIRC`).
- Mechanically only `META_P_IL` (isotropic linear hardening per phase); no kinematic
  hardening (`META_P_CL`), viscoplasticity (`META_V_*`) or **transformation
  plasticity** (`META_PT`, TRIP); not with `elem_hex8 = LINE_QUAD` (ERROR: the phases
  are on the linear mesh; use hex20 in Mecway).
- Hardness only as a linear mixture (`DURT_META`).
- A CCT diagram for another steel must be written by the user (`trc=`).

### 10.9 Messages → cause → solution

| Message (log) | Cause | Solution |
|---|---|---|
| `ERROR: #ASTER-METALLURGY needs a transient thermal analysis` | T30 or a mechanical model | Mecway *Thermal transient* (T31) |
| `WARNING: #ASTER-METALLURGY only works in a transient thermal analysis ...; ignored here` | the line is in a mechanical model | remove it, or make the analysis T31 |
| `ERROR: #ASTER-METALLURGIE ...: unknown or incomplete '...'` | typo, or `key` without `=` | keys of §10.2/§10.4 |
| `ERROR: ...: no standard dataset '...'` | unknown name for `staal=` | `16MND5` or `HSNV101A`, or `trc=` |
| `ERROR: ...: give a standard dataset staal=... or an own TRC diagram trc=...` | neither | `staal=16MND5` |
| `ERROR: ...: with trc=... missing: ...` | own CCT without the `META_ACIER` values | give `AR3`, `ALPHA`, `MS0`, `AC1`, `AC3`, `TAUX_1`, `TAUX_3` |
| `ERROR: ...: ALPHA = ...: ... ALPHA < 0` | Koistinen-Marburger constant entered as positive | with a minus sign, e.g. `ALPHA=-0.011` |
| `ERROR: #ASTER-METALLURGY '...': no (thermal) material with that name` | name differs from the Mecway material | exact name |
| `ERROR: ...: solid elements only; the shell elsets ...` | material also on shells | give the shells another material |
| `ERROR: ...: mechanica=ja needs ALPHA_A, DEPS ...` | dataset without mechanical data (16MND5) | give `ALPHA_A` and `DEPS` (§10.4) |
| `ERROR: ...: mechanica=ja needs a yield strength ...` | Mecway material elastic and no `SY` | `SY_F` .. `SY_A` or `SY`, or a plastic material |
| `ERROR: #ASTER-METALLURGY mechanica=ja does not work with elem_hex8 = LINE_QUAD` | LINE_QUAD on the Elements page | hex20 in Mecway, or `elem_hex8 = 3D` |
| `WARNING: #ASTER-METALLURGY '...': mechanica=ja without Thermal stress` | no *Thermal stress* in the T31 model | add a Thermal stress (§9.1), or remove `mechanica=ja` |
| `WARNING: ... mechanical data without mechanica=ja; ignored` | `ALPHA_A`, `SY_M`, ... without `mechanica=ja` | add `mechanica=ja` or remove the keys |
| `WARNING: Metallurgy: n nodes got well above Ac3 but did not become fully austenite` | fast heating with a large time step and τ = 0.34 s (§10.5) | `TAUX_1=0.001, TAUX_3=0.001` |
| `WARNING: Metallurgy: at the last time there is still austenite` | not yet cooled below Ms | compute longer |
| `<A> RESULT1_39` in the `.mess` | own `trc=` (own CHAM_MATER for `CALC_META`) | intended; no action |

### 10.10 Verification

[Verification.md](Verification.md) §8, "Welding: metallurgy" (MT-01 .. MT-08):
hsnv101a in 3D (phases equal to the AXIS test case to 1.3·10⁻⁶, the TEST_RESU values of
σ to 5·10⁻⁷ and of ε to 5·10⁻⁵ with the metallurgical law; tolerance 1%),
Koistinen-Marburger with the dataset and with an own CCT ≤ 4·10⁻⁸, austenitisation
≤ 2·10⁻⁸ between Ac1 and Ac3 (0.22% just above Ac3), transformation strain and the
stress in a clamped bar ≤ 6·10⁻⁶ against the hand calculation; the weld bead (MT-06,
MT-07) qualitatively.
## 11. Filler material that is born (`birth=`)

By default the bead is present from t = 0: it takes up heat and (in the chain) carries
load before it has been welded. With **`birth=yes`** (or `birth=<<selection>>`; Dutch
`geboorte=ja`) in an `#ASTER-LASBRON` the elements of the filler material are only
"born" when the source passes ("element birth", the **quiet element** method; Lindgren
2001, Michaleris 2014):

- **before birth** the elements are *quiet*: ρ·c × 10⁻⁴ and λ × 10⁻⁸ (no heat storage
  and no conduction), E × 10⁻⁴ (no stiffness, so no stress either), and the source does
  not act in them;
- **at birth** they get their normal material; mechanically they are **stress-free**
  in their (co-moved) position at the temperature of that moment: from then on only the
  strain and the thermal strain from there count (shrinkage α·ΔT relative to the birth
  temperature).

Code-Aster 17.4 has no element birth of its own (no keyword in `STAT_NON_LINE`,
`THER_LINEAIRE` or `AFFE_MATERIAU`, no test case); the bridge builds it from material
functions, command variables and a loop (§11.3).

### 11.1 Workflow in Mecway, step by step

Example: `TestFiles/Verificatie/modellen/WE-13.liml` (two layers on a plate, with the
thermal → mechanical chain).

1. **Mesh**: the base material and the bead (or the layers) as solid elements that
   **share nodes** at the interface (*Merge nearby nodes*). The bead may be a part of its
   own or an element selection inside the same part.
2. **Name**: per weld or layer an element selection or component with the prefix
   **`LASNAAD_`**, e.g. `LASNAAD_1` and `LASNAAD_2`.
3. **Weld source** per weld/layer (§1.2), with `birth=`:

   ```
   ** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.0015), direction=(1, 0, 0), length=0.02
   ** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetry=1, birth=<<LASNAAD_1>>
   ** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.003), direction=(1, 0, 0), length=0.02, t0=6
   ** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetry=1, birth=<<LASNAAD_2>>
   ```

   With a single weld `birth=yes` is enough (all `LASNAAD_` selections/components). The
   path lies on top of the bead (`start` on the top face): the source sits in the bead
   and extends into the base material.
4. Thermal: *Thermal transient*, initial temperature, boundaries (§1.1). Mechanical
   (residual stress): Thermal stress, supports and `#ASTER-MATERIAL` as in §9.1; with
   welding set `TC_CUT`.
5. Main window: *Active analysis* `auto` (or *Thermal*), *Start*. The log shows per
   source `INFO: #ASTER-LASBRON 1: toevoegmateriaal 180 elementen, geboren van t = 0 tot
   4 s (voorloop 0.003 m).` (filler elements, born from t = .. to .. s), and in the
   chain `INFO: Thermomechanisch: toevoegmateriaal ... STAT_NON_LINE per
   geboortestap.`

### 11.2 Keys

| Key (synonyms) | Unit | Default | Meaning | When to change |
|---|---|---|---|---|
| `geboorte` (`birth`) | `ja`/`yes` / `nee`/`no` / `<<selection>>` | `no` | filler material of this source: `yes` = the selections/components with `LASNAAD_`; `<<Name>>` = that element selection or component | `<<..>>` with several welds or layers (each source its own part; overlap gives an ERROR) |
| `voorloop` (`lead`) | m | 2 × `af` | an element is born when the centre of the source is at `lead` from its rearmost node (along the path) | larger: the material lies further ahead of the arc (with 1 × af ~0.5% of the power is lost in not-yet-born material, with 2 × af 10⁻⁷); smaller is not needed |

With `birth` the `LASNAAD_` group is the filler material and not the source group: the
source then acts on **all solid elements near the path** (automatic, within 3 × the
largest semi-axis; also the base material and earlier layers, which melt again), unless
`group=` is given. The factors of the quiet material (10⁻⁴; λ 10⁻⁸) are fixed.

### 11.3 How the bridge translates

- **Birth time per element**: tb = max(t0, t0 + (s_min − lead)/v), with s_min the
  smallest arc length (along the path) of its corner nodes (0 before the start,
  extended beyond the end of the path); so every point of the element lies on or after
  its birth. The element is alive from the first time step after tb (an element that
  already lies within the lead at the start, tb = t0: from t0). An element whose tb lies
  after the end of the source or of the analysis (e.g. more than the lead beyond the end
  of the path) is never born (WARNING).
- **Thermal, `THER_LINEAIRE`**: one group per birth step; a field `NEUT1` (the middle
  of the birth step) as command variable (`AFFE_VARC NOM_VARC='NEUT1'` `CHAM_GD`, test
  case ssnp160a) and for the filler `THER_FO` with `LAMBDA` and `RHO_CP` as a
  `FORMULE` of `INST` and `NEUT1` (test case ttnp201a): quiet while INST ≤ NEUT1. One
  solve.
- **Thermal, `THER_NON_LINE`** (λ(T), c(T) or radiation): `BETA`/`RHO_CP` of `THER_NL`
  may not be a formula or a nappe in Code-Aster 17.4 (`MODELISA6_31`, `MODELISA6_58`);
  the bridge creates a quiet `THER_NL` material (the tables × 10⁻⁴ and × 10⁻⁸) and runs
  `THER_NON_LINE` **per birth step** with a new `AFFE_MATERIAU` (`reuse`, `ETAT_INIT
  EVOL_THER`). With constant tables both routes gave the same energy in a prototype
  (to 10⁻⁶); WE-11b checks the second one with c(T).
- The filler uses a **diagonal heat capacity** (`3D_DIAG`, test case ttnp201a): with
  the consistent capacity a quiet node followed the temperature rate of its hot
  neighbours through the mass coupling (WE-13: +138 K before birth, with a dip below T0
  while they heated).
- **The source** acts in a point of the filler only when that point has already been
  born (the same rule in the `FORMULE`, `_lb_born`); elsewhere as usual.
- **Several sources** are put in **one** load (`lasbron`, also with Mecway sources as a
  formula or time table): Code-Aster 17.4 computes two `AFFE_CHAR_THER_F` loads with
  `SOURCE` in one analysis both with the function of the first (found in this step,
  §3). The energy check remains per weld source.
- **Mechanical** (chain, §9): a quiet copy of each material of the filler (E × 10⁻⁴,
  also `D_SIGM_EPSI`; a hardening curve with the strain / 10⁻⁴; yield stress unchanged,
  so the quiet element stays elastic) and `STAT_NON_LINE` **per birth step**: a new
  `AFFE_MATERIAU` with the born elements on their normal material, and the next step
  starts from the state at the beginning of the birth step with stress and internal
  variables of the new elements set to zero (`ETAT_INIT` `DEPL`/`SIGM`/`VARI`,
  `CREA_CHAMP ASSE`; `NEWTON PREDICTION='ELASTIQUE'` in that step, as after element
  failure). Also with `LINE_QUAD` (quadratic mechanical mesh).

### 11.4 Interpretation

- **Energy**: before birth the filler takes up no heat (WE-11: with the real ρ·c it
  would hold 0.5% of the input energy: only the nodes on the interface with the base
  material are hot). At birth an element takes the temperature of its nodes; those on
  the interface are already hot. That brings in a little energy: WE-11 +1.2 … +1.6% of
  η·Q·t (tolerance 2%).
- **Stress-free at birth**: at the temperature at the **start of the step** in which
  the element is born, in the deformed position of that moment (the quiet element moves
  along with its neighbours). An element is born ahead of the arc (`lead`), so at the
  temperature of the base material there; afterwards it heats up and melts. With
  `TC_CUT` (thermal strain frozen above the melting temperature) and a low E and SY at
  high temperature the stress in the weld pool is small; the residual stress develops
  during cooling. Without `TC_CUT` the heating of freshly born material gives large
  compressive stresses.
- **In Mecway**: a not-yet-born element is at the initial temperature and has
  (virtually) no stress; its nodes move with the base material (the displacement is not
  zero). Look at the stress at the last time or in a section behind the source.
- **Run time**: the mechanical loop (and `THER_NON_LINE` with c(T)) computes a solve per
  birth step (WE-13: 1 140 hex8, 150 steps of which 35 with births: 5.5 min).
- WE-13 (two layers on a plate, hex8 `3D`): the top of layer 1 melts (peak 2 690 K),
  cools in the 2 s pause to 530 K and is reheated by layer 2 to 1 750 K; layer 2 has no
  stress before its birth (von Mises < 5·10⁻⁴ × SY) and is at the initial temperature
  (+0.03 K); after cooling (30 s) σxx in the beads is 160–570 MPa tension (x = 15 mm),
  compression next to them (−510 MPa at y = 4 mm, −345 MPa at the edge y = 8 mm), net
  longitudinal force −0.25% of SY·A. The absolute values are too high with hex8 `3D`
  (locking, §9.5); the ends of the layers beyond the path (x > 27 mm) are not born
  (WARNING, 6 + 4 elements).

### 11.5 Verification

[Verification.md](Verification.md) §8, WE-11 .. WE-13 (`tests_lassen_geboorte.py`):

| Case | Check | Result | Tolerance |
|---|---|---|---|
| WE-11 (bead in two pieces, `THER_LINEAIRE`) | energy of the living volume after piece 1 (piece 2 unborn), during piece 2, at the end | +1.19 / +1.49 / +1.59% | 2% |
| WE-11 | heat in the unborn piece as if it were real material / input; T on top of the unborn piece | 0.50%; +0.49 K | 1%; 1 K |
| WE-11b (same with λ(T), c(T), `THER_NON_LINE` per step) | same | +1.12 / +1.40 / +1.54%; 0.50%; +0.62 K | same |
| WE-12 (bar, B born at T0 + 100 K) | u_x(L/2) before birth; \|σ\| in B before birth / E·α·ΔT | −0.02%; 1.8·10⁻⁴ | 1%; 10⁻³ |
| WE-12 | σ 1 s after birth (cooled 20 K); residual stress E·α·ΔT = 252 MPa in A and B | −0.04%; −0.01% | 1% |
| WE-12b (same, bilinear) | residual stress SY + H·p; p | 0.00%; −0.7% | 1% |
| WE-13 (two layers, chain) | melting, cooling between the layers and reheating; layer 2 stress-free and at T0 before birth; equilibrium; tension in the bead, compression next to it | see Verification.md | qualitative |

### 11.6 Not possible

- Birth follows the **path of the source** (arc length along a straight path or a
  `path`), not the distance to the arc: filler that lies far beside the path is born
  when the source is level with it.
- An element is born at once (no partial elements) and stress-free at the temperature
  of the **start of its birth step** (resolution Δt).
- Solid elements only; every element belongs to at most one source. No variant
  "present from the start but soft" (that is the normal chain with `TC_CUT` and a low
  E/SY above the melting temperature, §9).
- The plastic strain and hardening of the quiet element are reset at birth; history of
  the filler (wire, weld pool) does not count.
- With c(T) or radiation (THER_NON_LINE per step) and in the chain (STAT_NON_LINE per
  step) longer run time. `GDEF_LOG` with birth and kinematic hardening: NOT verified.
- The factors 10⁻⁴ / 10⁻⁸ are not keys.
- Mecway's own solver has no birth: a comparison with Mecway is only possible without
  `birth`.

### 11.7 Messages → cause → solution

| Message (log) | Cause | Solution |
|---|---|---|
| `ERROR: ... birth=yes needs an element selection or component with prefix LASNAAD_` | no `LASNAAD_` selection | create one or use `birth=<<Name>>` |
| `ERROR: ... birth '...' is not an element selection or component` | typo in the name, or a node/face selection | exact Mecway name of an element selection |
| `ERROR: ... '...' has no valid value (yes, no or <<Mecway selection>>)` | e.g. `birth=LASNAAD_1` without `<< >>` | `birth=<<LASNAAD_1>>` |
| `ERROR: ... n filler element(s) also belong to source k` | two sources with the same filler (e.g. `birth=yes` twice) | a selection of its own per source |
| `ERROR: ... the filler material ... has n element(s) that are not (modelled) solid elements` | shells or beams in the selection | solid elements only |
| `ERROR: ... no element of the filler material is born` | the source does not pass the filler, or starts after the end of the analysis | check path/`t0` (coordinates in m) |
| `WARNING: ... n filler element(s) are never born` | filler more than the lead beyond the end of the path, or the source or the analysis stops earlier | intended (the bead is longer than the weld)? Otherwise adjust `length`, `t1` or *Time period* |
| `WARNING: ... lead without birth=...; ignored` | `lead` without `birth` | add `birth=` or remove `lead` |
| `BRIDGE_ONVOLLEDIG` in the `.mess` with birth | the mechanical step after a birth does not converge | set `TC_CUT`, smaller *Time step*, E/SY above 1200 °C not extremely small (§9.8) |

## 12. Verification

[Verification.md](Verification.md) §8, group "Lassen" (WE-01 .. WE-06): Rosenthal
within 1% (tolerance 5%), Goldak against the same source folded analytically within
1.2%, energy balance ≤ 0.06% (tolerance 2%), Mecway formula equal to `#ASTER-LASBRON`
(energy equal to Mecway to 1e-9), temperature-dependent λ exact (Kirchhoff) and energy
0.01%, formulas in temperature/convection/flux equal to Mecway (7e-12 K). The thermal →
mechanical chain (WE-07 .. WE-10): §9.6. Metallurgy (MT-01 .. MT-08): §10.10. Filler
material that is born (WE-11 .. WE-13): §11.5.

## 13. References

- Goldak, J., Chakravarti, A. & Bibby, M. (1984). A new finite element model for welding
  heat sources. *Metallurgical Transactions B*, 15, 299–305.
- Rosenthal, D. (1946). The theory of moving sources of heat and its application to
  metal treatments. *Transactions of the ASME*, 68, 849–866.
- Carslaw, H.S. & Jaeger, J.C. (1959). *Conduction of Heat in Solids* (2nd ed.).
  Oxford: Clarendon Press (Kirchhoff transformation; sources and the Green's function
  of the heat equation).
- EDF R&D (n.d.). *Code_Aster, documentation version 17.4*: U4.44.02
  (`AFFE_CHAR_THER`), U4.43.01 (`DEFI_MATERIAU` `THER_NL`, `ELAS_FO`,
  `ECRO_LINE_FO`), U4.43.03 (`AFFE_MATERIAU` `AFFE_VARC`), U4.51.03 (`STAT_NON_LINE`,
  `RECH_LINEAIRE`), U4.54.02 (`THER_NON_LINE`); catalogues `affe_char_ther_f.py`,
  `formule.py`, `calc_vect_elem.py`, `defi_materiau.py`, `affe_materiau.py`,
  `proj_champ.py`; test cases hsnv100e, ssnp160a (`THER_FO` with a function of
  `NEUT1`, `AFFE_VARC` `CHAM_GD`) and ttnp201a (`THER_FO` with a function of `INST`,
  `3D_DIAG`); metallurgy: catalogues `calc_meta.py`,
  `defi_trc.py`, `defi_materiau.py` (`META_ACIER`, `DURT_META`, `ELAS_META_FO`,
  `META_ECRO_LINE`), `Behaviours/acier.py`, `meta_p_isot_line.py`; test cases hsnv101a,
  mtlp100b and mtlp103a (V4.61.103). https://www.code-aster.org
- Koistinen, D.P. & Marburger, R.E. (1959). A general equation prescribing the extent
  of the austenite-martensite transformation in pure iron-carbon alloys and plain
  carbon steels. *Acta Metallurgica*, 7(1), 59–60.
- Lindgren, L.-E. (2001). Finite element modeling and simulation of welding. Part 1:
  Increased complexity. *Journal of Thermal Stresses*, 24(2), 141–192 (among others
  the activation of filler material: "quiet" and "inactive" elements).
- Lindgren, L.-E. (2001). Finite element modeling and simulation of welding. Part 2:
  Improved material modeling. *Journal of Thermal Stresses*, 24(3), 195–231.
- Michaleris, P. (2014). Modeling metal deposition in heat transfer analyses of
  additive manufacturing processes. *Finite Elements in Analysis and Design*, 86,
  51–60 (quiet versus inactive elements, energy at activation).
- Masubuchi, K. (1980). *Analysis of Welded Structures: Residual Stresses, Distortion,
  and their Consequences*. Oxford: Pergamon Press.
- Waeckel, F. (1994). *Une loi de comportement thermo-métallurgique des aciers pour le
  calcul mécanique des structures* (PhD thesis). ENSAM Paris (the steel model `ACIER`
  of `CALC_META`; background, not consulted: the behaviour in §10.5 was measured).
- Radaj, D. (1992). *Heat Effects of Welding: Temperature Field, Residual Stress,
  Distortion*. Berlin: Springer.
- Timoshenko, S.P. & Goodier, J.N. (1970). *Theory of Elasticity* (3rd ed.). New York:
  McGraw-Hill.
- Mecway (2026). *Mecway manual*, version 33: §8.6 (temperature dependent
  properties), §9 (formulas), §9.28–9.29 (heat flux, internal heat generation).
