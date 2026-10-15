# Mecway features in the bridge

*Nederlandse versie: [Mecway_functionaliteit.md](../Mecway_functionaliteit.md)*

Which Mecway input the bridge translates to Code-Aster. Each line has a status:
**Yes** (translated), **Partly** (translated with a limitation) or **No** (not
translated). The remark gives the limitation, the number in
[`KNOWN_BUGS.md`](../../KNOWN_BUGS.md) (KB, in Dutch) and, for Partly and No, what you
can do instead. An `#ASTER` line is your own Code-Aster input in Mecway's *Custom
model definition* ([`ASTER_lines_examples.md`](ASTER_lines_examples.md), "example n").

What the bridge does not translate is reported with an ERROR in the log and in the
list of skipped items at the end of the run. Exceptions are marked in the table
("without a message"). Mechanical loads in a thermal analysis and vice versa are
ignored with only an INFO, as Mecway itself does.

## 1. Analysis types

| Mecway | Status | Bridge (Code-Aster) | Remark |
|---|---|---|---|
| S30 Static 3D | Yes | `lin_static_3d` (`MECA_STATIQUE`) | Gap, tension only, compression only and contact need `nonlin_static_3d`: the bridge stops with an ERROR. |
| L30 Nonlinear Static 3D | Yes | `nonlin_static_3d` (`STAT_NON_LINE`) | Solver steps = Mecway's *Time step size* plus the kinks of the load tables. Contact: KB43. |
| D30 Dynamic Response 3D | Yes | `dyna_impl_3d` (`DYNA_NON_LINE`) | Same as Mecway (Newmark) with schema NEWMARK and deformation PETIT; otherwise a WARNING. |
| D30 with *Mode superposition* | Yes | `dyna_modal_3d` (`CALC_MODES` + `DYNA_VIBRA` `GENE`) | No prescribed displacement ≠ 0, initial velocity or dampers (KB54); then choose `dyna_impl_3d`. |
| D31 Nonlinear Dynamic Response 3D | Yes | `dyna_impl_3d`; explicit: `dyna_expl_3d` (choose it yourself) | |
| V30 Frequency | Yes | `modal_3d` (`CALC_MODES`) | Prestress from loads as in Mecway; no damping by default, complex modes as an option (KB49); cyclic symmetry ([`Modal_and_buckling.md`](Modal_and_buckling.md) §2.5, §6, §7). With a fluid part: `vibroacoustic_modes_3d` / `vibroacoustic_harm_3d` ([`Acoustics.md`](Acoustics.md) §6, §7; KB59). |
| B30 Buckling | Yes | `buckling_3d` (`CALC_MODES` `MODE_FLAMB`) | Mecway's *Shift point* is not used; negative buckling factors too (KB46). See [`Modal_and_buckling.md`](Modal_and_buckling.md). |
| T30 / T31 Thermal | Yes | `ther_3d` (`THER_LINEAIRE` / `THER_NON_LINE`) | See [`Thermal.md`](Thermal.md). Transient scheme KB14. |
| A30 Acoustic Resonance 3D | Yes | `acoustic_modes_3d`; with a source `acoustic_harm_3d` | KB55, KB57; [`Acoustics.md`](Acoustics.md). |
| 2D and axisymmetric (e.g. S20, SA0, D20, A20) | No | – | The run stops ("analysis type is not supported"). Alternative: model in 3D, e.g. a slice with symmetry. |
| E30 DC Current Flow | No | – | The run stops. |
| Electrostatics and piezoelectricity (in S30) | No | – | Electric loads are skipped; a piezo or matrix material stops the run (§5). |
| no Mecway type | – | `harmonic_3d`, `spectrum_3d` (choose it yourself) | Extra analyses of the bridge: [`Mode_superposition.md`](Mode_superposition.md), [`Response_spectrum.md`](Response_spectrum.md). |

## 2. Loads

| Mecway | Status | Remark |
|---|---|---|
| Force (nodes, faces, elements) | Yes | On nodes divided equally, on faces as force per area. |
| Pressure | Yes | Follower load in nonlinear analyses (a formula in x, y, z stays fixed). On shell edges and beam ends as nodal forces (KB5). |
| Traction | Yes | On a shell face with the moment of half the thickness, as in Mecway. |
| Line pressure | Yes | Global or local (U, V, W). Combinations on one beam: KB20. |
| Hydrostatic pressure | Partly | Not on shell edges (KB5). |
| Moment | Yes | On one node with rotations, or as forces over faces. |
| Gravity | Yes | With a time table only for a fixed direction. |
| Centrifugal force | Partly | Only a constant angular velocity, one per model (no gyroscopic effect); spin softening only on solids (KB19). |
| Mass, Rotational inertia | Yes | Only on nodes; rotational inertia on one node. |
| Temperature (`temperature2`) + Thermal stress | Yes | Constant temperature; a time table or formula in t in L30 and D31 (`EVOL_THER`, NL-70..75, DY-70..72). Static/modal/buckling: a time history is left out, as with Mecway's own solver. D30 ignores it like Mecway. |
| Node temperature (`temperature3`) in a mechanical analysis | Yes | Also after *Transfer temperatures from solution*. Static, nonlinear static, modal (prestress) and buckling, like Temperature; nodes without a temperature at the Thermal stress reference (LS-08). D30 ignores it like Mecway; D31 reported (not in Mecway's list). |
| Rayleigh damping | Partly | Only on the whole model, not on a selection (KB27). |
| Initial velocity | Yes | Dynamics only; not with mode superposition (KB54). |
| Initial displacement | No | Reported. |
| Value as a table or a formula in t | Yes | 10001 samples as Mecway does for CCX. Linear static, modal and buckling: the value at the end time. Many points = many steps (KB104). |
| Formula in x, y, z (mechanical) | Yes | Pressure, traction, force, line pressure, prescribed displacement/rotation: `FORMULE` of X, Y, Z (also with t) in `AFFE_CHAR_MECA_F` (LS-40..44, NL-40). Mecway 34 itself does not apply force, line pressure and displacement/rotation with x, y, z (WARNING). Not: gravity, moment, centrifugal, direction as a formula, pressure on shell edges; not in explicit, harmonic, spectrum (KB104). |
| Load on the side face of a beam | No | KB5. Put the load on an element selection of the beam. |
| Pre-tension section | No | No alternative in the bridge. |
| Electric potential, Charge, Current, Robin | No | No electric analyses (§1). |
| Thermal loads (temperature, heat flow, heat flux, heat generation, convection, radiation) | Yes | In T30/T31; formulas in x, y, z, t too. Details: [`Thermal.md`](Thermal.md). |
| Forced convection, Mass flow rate, cavity radiation | No | KB16. |
| Fluid pressure, Impedance (acoustics) | Partly | Fluid pressure only 0; impedance not frequency dependent, harmonic only real (KB55, KB57). |
| OpenRadioss cards in the model definition | No | Only `/FUNCT` (for `PLAS_TAB`) is read; the rest is reported (KB4). |

## 3. Constraints, couplings and contact

| Mecway | Status | Remark |
|---|---|---|
| Fixed support | Yes | Overlap with other constraints: KB8. |
| Pinned support | Yes | Nodes and faces of solid elements, as in Mecway. |
| Frictionless support | Partly | Not on beams; normal displacement ≠ 0 not on curved shells and shell edges (KB5). |
| Elastic support | Yes | Faces of solids and shell faces. |
| Compression only support | Partly | Only in nonlinear analyses, not together with contact; on shells the rotations stay free (KB22). |
| Displacement, Node rotation | Yes | Value as a formula in x, y, z: Yes; direction as a formula: No (KB104). Prescribed rotations with large rotations: KB11. |
| Velocity | Yes | Dynamics. |
| Symmetry | Yes | Faces of solids, shell edges and beam ends. |
| Cyclic symmetry | Partly | Only in Frequency (V30) and only solid elements; in static and thermal reported and computed as a loose sector (KB61). |
| Constraint equation | Yes | KB27. Explicit: a constant ≠ 0 becomes an imposed motion (DY-20b; Mecway itself does not allow it there). |
| Node-surface coupling, Rigid (RBE2) | Yes | `LIAISON_SOLIDE`; large rotations: KB11. Not in thermal (reported). |
| Node-surface coupling, Distributing (RBE3) | Yes | `LIAISON_RBE3`. Not in thermal (reported). |
| Flexible joint on beam | Yes | Free rotation about U, V and/or W (local beam axes as in Mecway) at a beam end: the element gets its own node there, coupled with `LIAISON_DDL` (translations and the rotations that are not free). Mecway has no stiffness in the joint, only free or fixed. Also on line3 beams and in Frequency, dynamics, buckling and nonlinear static (the latter not in Mecway; large rotations: KB106). Verification LS-51 (equal to Mecway); section forces per element also next to the joint and on line3 (LS-53). A constraint on an *element selection* that contains the element with the joint: see KB106. With an element offset on the same element: see KB108 (LS-52). Not in the thermal → mechanical chain (WARNING). |
| Contact, Unilateral (faces of solids and shell faces) | Yes | Nonlinear only, as in Mecway. Formulation and friction: KB43; shared slave nodes: KB10. |
| Contact, Unilateral, *Self contact* | No | Reported. Make two separate face selections. |
| Contact, Unilateral, on shell edges or beams | No | Reported. |
| Contact, Bonded *Tie* / *Constraint equations* | Yes | `LIAISON_MAIL` (rigid), see the table below. Also works in linear analyses. Automatic tolerance: all slave nodes are tied (KB21). |
| Contact, Bonded *Elastic* | Partly | Rigidly bonded; the stiffness is not translated (reported, KB21). |
| Bonded contact in T30/T31 | Yes | *Tie* / *Constraint equations*: `AFFE_CHAR_THER` `LIAISON_MAIL` (also non-conforming and shell on shell). *Elastic*: thermal resistance (*Thermal conductance per unit area*) as `ECHANGE_PAROI` for solid faces that are node-to-node opposite each other, otherwise ideally bonded (reported). Not in a model with solids and shells together (ERROR; shared nodes). [Thermal.md](Thermal.md) sec. 3, verification TH-04. |
| Bonded contact in acoustics | No | Reported (KB55). |

Bonded contact per combination (slave on master):

| Slave → master | Status | Code-Aster | Remark |
|---|---|---|---|
| solid → solid | Yes | `MASSIF` | |
| shell → shell | Yes | `COQUE` (or `LIAISON_DDL`) | Also a shell edge on a shell face (in-plane seam, T-joint): rigid, the rotations are tied (no hinge; Mecway's own solver does not do this). Linear shells as master stay DKT, also with the choice COQUE_3D. A quadratic master (tri6/quad8) and a skewed or curved master: the bridge writes the tie (partly) itself as `LIAISON_DDL`; skewed or curved sets `solver_nprec` to −1 for that run (WARNING). Verified in LS-07a..k, example `Voorbeeld_T.liml` ([contact §3.10](Settings_contact_and_nonlinear.md#310-example-bonding-plates-bonded-contact-between-shells)). |
| shell face → solid | Yes | `MASSIF` | Displacements only; measured equal to shared nodes (KB21). |
| shell edge → solid | Partly | `COQUE_MASSIF` or `MASSIF` | Rigid if all edges belong to one component with a thickness; otherwise the edge acts as a hinge (WARNING, KB21). Make one bonded contact per component (example 2). |
| solid → shell | Yes | `MASSIF_COQUE` | Also on a quadratic shell (quad8 with a hex20 block, nodes in the middle of the plate elements: measured equal to relations written by the bridge). |
| beam → solid | No | – | Reported and skipped. Alternative: Node-surface coupling with the beam end as reference node, or `#ASTER` `LIAISON_ELEM` `3D_POU` (example 1). |
| beam → shell | No | – | Reported and skipped. Alternative: Node-surface coupling with the beam end as reference node. |
| beam → beam | No | – | Not possible in Mecway either (the master must be a face). Connect with a shared node or constraint equations. |

## 4. Elements

| Mecway | Status | Code-Aster | Remark |
|---|---|---|---|
| hex8 | Partly | `3D` | Stiffer than Mecway (no incompatible modes, KB1). Better: *Elements* > hex8 `LINE_QUAD`. |
| tet4, tet10, pyr5, pyr13, wedge6, wedge15, hex20 | Yes | `3D` | Pyramids not in acoustics (KB55). Strongly curved hex20/wedge15: KB62. |
| tri3, quad4 (shell) | Yes | `DKT` (or `DST`/`COQUE_3D` as a choice) | ~0.7% different from Mecway (KB2). |
| tri6, quad8 (shell) | Yes | `COQUE_3D` | As master of bonded contact: displacements with `LIAISON_DDL`, rotations with `LIAISON_MAIL` (LS-07i..k). |
| linear and quadratic shells in one component | Partly | – | The quadratic ones are not modelled (ERROR). Split the component. |
| beam line2 | Yes | `POU_D_E` (or `POU_D_T`) | Orientation from *Element properties*. No plasticity (KB6), no large rotations (KB11). |
| beam line3 | Yes | `POU_D_E` (or `POU_D_T`) | Each element is split at its midside node into two SEG2 cells (Code-Aster has no quadratic beam); results on all three nodes. Mecway itself solves line3 beams only with CCX. Verification LS-50. Truss, spring, gap, damper and tension-only on line3: No (ERROR; line2 only in Mecway). |
| truss line2 | Yes | `BARRE` | Small displacements (KB40). Beams and trusses in one component become two groups (`<name>_TRUSS`). |
| spring, damper, gap (line2) | Yes | `DIS_T` (gap: `DIS_CHOC`) | Along the element's own axis. Gap nonlinear only (KB23); springs/dampers not compared with Mecway (KB47). |
| tension only (line2, truss) | Partly | `CABLE` | Nonlinear only; compressive stiffness 1e-4 E (KB23). |
| elements of different dimension in one component | Partly | – | Only the highest dimension is modelled (ERROR). Split the component. |
| plane, axisymmetric (2D) | No | – | Only in 2D analyses (§1). |
| shells in a thermal analysis | Partly | `PLAN` with a thickness factor | Only shells in parallel planes (KB15); others: No (KB16). |
| fin, fluid network element, resistor | No | – | Thermal 1D and DC current: KB16. |
| Element offset (shell, beam) | Yes | DKT/DST: `COQUE` `EXCENTREMENT` (+ `INER_ROTA`); COQUE_3D and beams: element on its own nodes + rigid arm (`LIAISON_DDL`) | Shell: *Element coordinates*, only W counts (as in Mecway; u/v have no effect there either). Beam: *Global coordinates* x/y/z (u/v/w on a beam: no effect in Mecway, WARNING). Displacement, rotation and reaction at the Mecway nodes; stresses of the offset element shown at those nodes, also as element values (LS-65). In all mechanical analyses (Mecway: static only), not in the thermal → mechanical chain (WARNING, KB64). Rigid arm: small rotations (KB108). A load on a face selection on edges of offset shells is applied at the nodes by the bridge, at the offset edge by Mecway (WARNING, KB108). A flexible joint on an offset beam element is not translated (WARNING; Mecway does apply it, KB108); bonded contact on offset shells: WARNING (KB108). Verification LS-60–67, LS-52. |
| Element orientation (local U/V axes per element) | Partly | – | Mecway stores the orientation per element (`orientationux`…`vz`, `angle`). Used for beams (section orientation), gaps (direction) and for shells the U axis of the result field `shell_forces` (§6). Otherwise ignored without a message for solids and shells; with an isotropic material that does not change the result. Only needed for orthotropic materials (§5, No). |

## 5. Materials and cross-sections

| Mecway | Status | Remark |
|---|---|---|
| Isotropic (E, ν, ρ, α) | Yes | Without E the bridge uses 210 GPa, Mecway 0 (KB60). |
| Plastic, isotropic hardening curve | Yes | `VMIS_ISOT_TRAC`. Not on beams (elastic, WARNING; KB6). |
| Plastic, Bilinear isotropic / kinematic | Yes | `ECRO_LINE`; Mecway's *tangent modulus* is the plastic modulus H, `D_SIGM_EPSI` = E·H/(E+H); perfectly plastic with tangent modulus 0. |
| Plastic, Kinematic (curve) | Partly | Only a curve with linear hardening (`VMIS_CINE_LINE`); a nonlinear curve is computed as elastic (reported). No equivalentplasticstrain (KB6). |
| Plastic, Ramberg-Osgood | Yes | Sampled curve (KB6). |
| Spring, Damper, Gap, Tension only | Yes | Only on line2 (§4). Gap: *force of open gap* not used (KB23). |
| Orthotropic, Anisotropic (matrix), Composite, Neo Hooke, Mooney-Rivlin, piezo | No | WARNING, then the run stops ("elset without a usable material"). No alternative in the bridge. |
| Failure criterion (factor of safety) | Partly | Von Mises (*tensile strength*): `factorofsafety` to Mecway (result field `safety_factor`, §6). Tsai-Wu and other criteria: WARNING, no factor of safety. For plastic failure: [`Failure.md`](Failure.md). |
| Thermal: conductivity, specific heat, also *Temperature dependent* | Yes | [`Thermal.md`](Thermal.md). Formulas in material properties: No (KB16). |
| Speed of sound (acoustics) | Yes | Media with different density: No (KB55, KB59). |
| OpenRadioss law `PLAS_TAB` | Partly | Fields not translated: KB34. Law `VOID`: elements left out (reported); other laws: No. |
| Section circular and rectangular (solid and hollow), General section, I, T, L, C | Yes | Mecway's *Stress recovery point* is not used. Other geometry types: No (WARNING). |
| Plate thickness (Plate) | Yes | |

## 6. Results back in Mecway

| Mecway field | Status | Remark |
|---|---|---|
| Displacement, rotation | Yes | Modal and buckling: the mode shapes. |
| Stress tensor of solid elements (node and element node) | Yes | Code-Aster averaging, different from Mecway (KB3). Route `tabel`: KB7. |
| von Mises (solids; shells top/middle/bottom) | Yes | KB3. |
| Stress tensor of shells (global, top/middle/bottom), forces and moments per length | Yes | Fields `shell_stresses` (off by default) and `shell_forces`; route `liml` only. Mecway's *stress in element coordinates* (`stressuu` ..) not. Element orientation as a load: not read ([`UserGuide.md`](UserGuide.md) §4.1). |
| Beam stress | Partly | Only smallest/largest axial stress for rectangular and circular sections (`beamsixxmin/max`). |
| Section forces and moments of beams | Yes | Field `beam_forces` (`tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv/w`), also per mode. |
| Reaction forces and moments | Yes | Not with mode superposition, harmonic and vibroacoustics (KB54, KB59). |
| Velocity, acceleration | Yes | Dynamics; acceleration not with mode superposition (KB54). |
| Plastic strain, equivalent plastic strain | Partly | Equivalent plastic strain not with kinematic hardening (KB6). |
| Total strain | Yes | Field `strain` (off by default): `lstrain*`, nonlinear `greenlagrangestrain*`; shells top/middle/bottom. No logarithmic strain and no principal strains. |
| Contact pressure, contact state | Partly | Field `contact`: `contactpressure`, `contactstate` (0/1/2). No contact shear stress and displacement; sliding (2) NOT verified. |
| Factor of safety | Yes | Field `safety_factor` (von Mises, §5). |
| Temperature, heat flux | Yes | Thermal. |
| Natural frequencies, buckling factors, effective mass | Yes | Effective mass fraction differs from Mecway (KB49). |
| Acoustic pressure | Yes | [`Acoustics.md`](Acoustics.md). |

Extra fields of the bridge (error estimator, fatigue, metallurgy) and which Code-Aster
field belongs to which Mecway name: [`UserGuide.md`](UserGuide.md) §4.1.

## 7. Mecway analysis and solver settings

| Mecway | Status | Remark |
|---|---|---|
| Analysis type | Yes | Chooses the analysis with `auto` (§1). |
| Solver (Internal, CCX, OpenRadioss) | No | The bridge always computes with Code-Aster; read only for messages. |
| Number of modes | Yes | Modal, buckling, mode superposition, acoustics. |
| Shift point (buckling) | No | INFO only (KB46). |
| Mode superposition (D30) | Yes | §1. |
| Time period | Yes | |
| Time step size | Yes | D30, T31 and L30 (L30: Mecway's steps up to the period plus the kinks of the load tables; without a step size `substeps_per_interval`). *Automatic time stepping* not reproduced: fixed step, Code-Aster only cuts on divergence. |
| Output times, *Generate solution every n time steps* | Yes | |
| Automatic time stepping | No | Without a message; the bridge halves the step itself on divergence. |
| Incompatible hex8 | No | KB1. |
| Configurations | Yes | One per run, chosen on the start screen (*Configuration*); results in the solution of that configuration ([`UserGuide.md`](UserGuide.md) §4, LS-20). |
| Custom model definition (CCX, OpenRadioss, Nastran) | Partly | Only `#ASTER` lines; ordinary CCX cards are ignored without a message. |
