# 2D and axisymmetric analyses

*Nederlandse versie: [2D_en_axisymmetrisch.md](../2D_en_axisymmetrisch.md)*

The bridge translates Mecway's two static 2D analysis types to Code-Aster
`MECA_STATIQUE` with plane elements (U3.13.01 "Modélisations AXIS, D_PLAN, C_PLAN"):

| Mecway analysis | Mecway material | Code-Aster | Result in Mecway |
|---|---|---|---|
| Static 2D (S20) | *Shell/membrane* with a thickness | `C_PLAN` (plane stress) | displacement X, Y; stress (σ_zz = 0); von Mises; reactions for the thickness t |
| Static 2D (S20) | *Shell/membrane* with a thickness and *plane strain* | `D_PLAN` (plane strain) | as above, σ_zz = ν(σ_xx + σ_yy) |
| Static Axisymmetric (SA0) | no geometry (isotropic material) | `AXIS` | displacement X (radial), Y (axial); stress with `stresszz` = hoop stress; reactions for 360 degrees |

The bridge analysis is `lin_static_3d` ("Static"): with *Active analysis* = `auto` the
bridge chooses it for S20 and SA0. General operation of the bridge:
[`UserGuide.md`](UserGuide.md). The other 2D types of Mecway (Dynamic Response 2D
(D20), Dynamic Response Axisymmetric (DA0), Acoustic Resonance 2D (A20)) are not
translated (§4). Mecway has no thermal 2D type: a thermal model in a plane is made of
shells ([`Thermal.md`](Thermal.md)).

## 1. Step-by-step workflow

### 1.1 In Mecway: the model

1. **Analysis type.** *Static 2D* or *Static Axisymmetric* in the analysis settings.
2. **Mesh.** Plane elements tri3, tri6, quad4 or quad8 in the XY plane, all nodes with
   Z = 0 (Mecway ignores Z; the bridge stops if Z ≠ 0, §3). Axisymmetric: Y is the axis
   of symmetry, X the radius, all nodes with X ≥ 0 (Mecway Ltd., 2026, §6.1.3, §7.2).
   Quadratic elements may have curved edges (midside node off the chord).
3. **Material.**
   - S20: give the material a geometry *Shell/membrane* with a **thickness** t; for
     plane strain also tick *plane strain*. Without a thickness Mecway does not solve
     and the bridge stops (§3). The whole model has one thickness and one type (plane
     stress or plane strain), otherwise the bridge stops.
   - SA0: no geometry. A thickness does not count (the bridge ignores it with a
     WARNING; Mecway's own solve gives no solution then).
   - Density for gravity and centrifugal force.
4. **Supports.** *Fixed support*, *Pinned support* and *Displacement* along X or Y on
   nodes or on edges (face selection of edges, faceid 1..4), *Symmetry* with normal X
   or Y on edges. Axisymmetric: Mecway asks for a support in X on nodes on the axis
   (X = 0) (Mecway Ltd., 2026, §7.2); do the same for the bridge (without it NOT
   verified). One support in Y is needed against rigid motion along the axis.
5. **Loads** (all values as in Mecway, see §2.2):
   - *Pressure* and *Traction* on edges;
   - *Force* on nodes (total, equally per node) or on edges (total, uniform over the
     edge area);
   - *Gravity* in the XY plane (SA0: only along Y);
   - *Centrifugal force* about Z (S20) or about Y (SA0).
   Other items stop or are skipped with an ERROR (§3, §4).

### 1.2 In the main window of the bridge

*Active analysis* `auto` (or `lin_static_3d`) and *Result route* `liml` (General page;
the route `tabel` does not scale the reactions, the bridge stops). The settings of the
Static page apply as in 3D. The result fields `strain` and `shell_*` give nothing in 2D;
`principal_stresses` gives `principal1..3` and `tresca` as Mecway does (eigenvalues of
the 3D tensor with σ_zz, per element node, node = average). The error estimator is not
used in 2D (INFO).

### 1.3 Viewing the results in Mecway

The results have Mecway's own names and appear under the same items as Mecway's own
S20/SA0 solution (measured: Mecway adds *displacement*, *stress*, *von Mises stress*,
*reaction force*, *principal stress* and *Tresca stress* when it opens the result):

| Mecway variable | Code-Aster | Meaning |
|---|---|---|
| `displx`, `disply`, `displmag` | `DEPL` DX, DY | X, Y (SA0: radial, axial); no `displz` (as Mecway) |
| `stressxx`, `stressyy`, `stressxy` | `SIGM_NOEU`/`SIGM_ELNO` | in-plane stresses (SA0: σ_r, σ_z, τ_rz) |
| `stresszz` | `SIGM_*` SIZZ | 0 in plane stress, ν(σ_xx + σ_yy) in plane strain, **hoop stress** in SA0 |
| `stressyz`, `stresszx` | – | 0 (as Mecway) |
| `vonmises` | `SIEQ_*` | 3D von Mises with σ_zz |
| `reactionforcex/y/mag` | `REAC_NODA` × t or × 2π | for the whole thickness (S20) or 360 degrees (SA0), as Mecway |

## 2. How the bridge translates

### 2.1 Elements and mesh

The bridge writes the plane elements as `TRIA3`/`TRIA6`/`QUAD4`/`QUAD8` cells with
`COOR_3D` and Z = 0; Code-Aster reads such a mesh as 2D (measured, no alarm). Each
component gets `MODELISATION='C_PLAN'`, `'D_PLAN'` or `'AXIS'`; edges with a pressure
or an edge load become `SEG2`/`SEG3` cells with the same modelisation (pressure edges
oriented outwards with `MODI_MAILLAGE ORIE_PEAU`). Measured against Mecway's own
solution (headless): tri3, tri6, quad4 and quad8 give the same displacements (≤ 1e-11
relative); Mecway's quad4 in 2D has no incompatible modes (unlike hex8, KB1).

### 2.2 Thickness and 360 degrees

Code-Aster computes `C_PLAN`/`D_PLAN` per unit thickness (there is no thickness in
`AFFE_CARA_ELEM`; measured: the reaction of a pressure on an edge of 20 mm is p × 0.02 m
× 1 m) and `AXIS` per radian (U4.44.01 §3.5: forces "brought back to a sector of 1
radian"). Mecway gives forces and reactions for the whole thickness t (also in plane
strain) and for 360 degrees (measured). The bridge therefore:

| Mecway | Code-Aster | Factor |
|---|---|---|
| force on nodes (N, total) | `FORCE_NODALE` | / t (S20) or / 2π (SA0) |
| force on edges (N, total) | `FORCE_CONTOUR` = F / A | A = L·t (S20) or 2π∫r dl (SA0) |
| pressure, traction (Pa) | `PRES_REP`, `FORCE_CONTOUR` | none |
| gravity, centrifugal force | `PESANTEUR`, `ROTATION` | none |
| reaction forces | `REAC_NODA` | × t or × 2π |

The mass in the log (`BRIDGE_STATCHECK`) is that of the whole thickness or of 360
degrees (Code-Aster's `MASS_INER` of `AXIS` is already for 360 degrees, measured).

### 2.3 Constraints

`fixed`, `pinnedsupport`: `DDL_IMPO` DX = DY = 0; `displacement` along X or Y:
`DDL_IMPO`; `symmetry` with normal X or Y: `DDL_IMPO` DX = 0 or DY = 0. Components the
2D model does not have (DZ, rotations, FZ) are left out.

## 3. Not possible

KNOWN_BUGS 123; planned steps in `STAPPENPLAN.md` (S16b … S16e).

- Beams, trusses, springs or solids in a 2D analysis (Mecway's S20 allows beams and
  trusses): ERROR, the bridge stops.
- Several thicknesses, or plane stress and plane strain in one model: ERROR.
- Moment, line pressure, hydrostatic pressure, frictionless and elastic support,
  compression only, node rotation, constraint equations, couplings, contact, point
  masses, temperatures (thermal stress): ERROR (stop or skipped).
- Displacement along an oblique direction, symmetry with an oblique normal: skipped
  (ERROR).
- Nonlinear static, modal, buckling, dynamics with a 2D model: ERROR (only
  `lin_static_3d`). Mecway itself has no nonlinear, frequency or buckling 2D type
  (Mecway 34 converts V20 to V30 and B20 to S30).
- The error estimator (INFO) and the result route `tabel` (ERROR).

## 4. Other 2D analysis types (not translated)

| Mecway | Status | Alternative |
|---|---|---|
| Dynamic Response 2D (D20), Dynamic Response Axisymmetric (DA0) | No (ERROR) | model in 3D (a slice with symmetry) |
| Acoustic Resonance 2D (A20) | No (ERROR) | [`Acoustics.md`](Acoustics.md): 3D (A30) |

## 5. Interpretation

- Displacements and reaction forces are equal to Mecway's own S20/SA0 solution
  (≤ 1e-11 relative, verification PL-01, PL-02, PL-04 … PL-06).
- Nodal stresses differ from Mecway where the stress varies strongly over an element
  (e.g. 1 to 3% at the hole of PL-01 with n = 16, 2% at the inner wall of a coarse
  ring): another extrapolation from the integration points, as for solids (KB3). Where
  the stress is uniform or linear in the element they are equal.
- Pressure on curved quadratic edges: Mecway's resultant is slightly too large (quarter
  ring a = 0.1 m, t = 10 mm, 100 MPa: Mecway 100161 N instead of p·a·t = 100000 N, u_r at
  the inner wall 0.17% smaller than the bridge); the bridge is exact (KB122).

## 6. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Elset '…': Static 2D (S20) needs a thickness | material without *Shell/membrane* geometry | give the material a thickness (also for plane strain) |
| ERROR: The 2D analysis has elsets with different modelisation or thickness | two materials with a different thickness or type | one thickness and one type per model; or compute in 3D |
| ERROR: A 2D analysis (…) needs all nodes in the XY plane (Z = 0) | mesh not in the XY plane | move or rotate the mesh into the XY plane |
| ERROR: Axisymmetric (SA0): all nodes must have X >= 0 | part of the mesh at X < 0 | mirror the mesh to X ≥ 0 (Y = axis) |
| ERROR: Elset '…' contains line2 …; in a 2D analysis … | beams, trusses, springs or solids in the model | remove them or compute in 3D |
| ERROR: … in a 2D analysis (…) is not translated (yet) | contact, coupling, constraint equation, point mass or temperature | remove it or compute in 3D |
| ERROR: … on '…' in a 2D analysis: … NOT included. | load or constraint without a 2D route (§3) | replace it by a supported load (§1.1) |
| ERROR: Mecway analysis type D20 … is not translated (yet) | dynamic or acoustic 2D | compute in 3D |
| ERROR: A 2D analysis (…) only works with the result route 'liml' | route `tabel` chosen | choose `liml` on the General page |
