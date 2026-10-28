# Mecway features in the bridge

*Nederlandse versie: [Mecway_functionaliteit.md](../Mecway_functionaliteit.md)*

Which Mecway input the bridge translates to Code-Aster. Each line has a status:
**Yes** (translated), **Partly** (translated with a limitation) or **No** (not
translated). The remark gives the limitation, the number in
[`KNOWN_BUGS.md`](../../KNOWN_BUGS.md) (KB) and, for Partly and No, what you
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
| S20 Static 2D (plane stress, plane strain) | Partly | `lin_static_3d` (`MECA_STATIQUE`, `C_PLAN`/`D_PLAN`) | Plane elements only, one thickness and type per model; loads and constraints: [`2D_and_axisymmetric.md`](2D_and_axisymmetric.md) §1.1, §3 (KB126). Verification PL-01 … PL-03, PL-05. |
| SA0 Static Axisymmetric | Partly | `lin_static_3d` (`MECA_STATIQUE`, `AXIS`) | As S20; Y = axis, `stresszz` = hoop stress, reactions for 360 degrees (KB126). Verification PL-04, PL-06. |
| D20, DA0 Dynamic Response 2D / Axisymmetric | Partly | `dyna_impl_3d` (`DYNA_NON_LINE`, `C_PLAN`/`D_PLAN`/`AXIS`) | As S20/SA0; equal to Mecway with NEWMARK, PETIT and one step per Mecway step (KB127); no explicit, mode superposition or initial velocity (KB126). Verification PL-10 … PL-12. |
| A20 Acoustic Resonance 2D | Yes | `acoustic_modes_3d` (`PHENOMENE='ACOUSTIQUE'`, `PLAN`) | Cavity modes, also with impedance; a thickness does not count (as in Mecway); triangles slightly higher than Mecway (KB130); no harmonic pressure field in 2D (KB126). [`Acoustics.md`](Acoustics.md) §3.5. Verification AK-10 … AK-15. |
| E30 DC Current Flow | No | – | The run stops. |
| Electrostatics and piezoelectricity (in S30) | No | – | Electric loads are skipped; a piezo or matrix material stops the run (§5). |
| no Mecway type | – | `harmonic_3d`, `spectrum_3d` (choose it yourself) | Extra analyses of the bridge: [`Mode_superposition.md`](Mode_superposition.md), [`Response_spectrum.md`](Response_spectrum.md). |

## 2. Loads

| Mecway | Status | Remark |
|---|---|---|
| Force (nodes, faces, elements) | Yes | On nodes divided equally, on faces as force per area. |
| Pressure | Yes | Follower load in nonlinear analyses (a formula in x, y, z stays fixed). On shell edges and beam ends as nodal forces (KB5). |
| Traction | Yes | On a shell face with the moment of half the thickness, as in Mecway. |
| Line pressure | Yes | Global or local (U, V, W). Combinations on one beam are summed; local and global on the same beam: No (ERROR, KB20). |
| Hydrostatic pressure | Partly | Not on shell edges (KB5). |
| Moment | Yes | On one node with rotations, or as forces over faces. |
| Gravity | Yes | With a time table only for a fixed direction. |
| Centrifugal force | Partly | Only a constant angular velocity, one per model (no gyroscopic effect); spin softening only on solids (KB19). |
| Mass, Rotational inertia | Yes | Only on nodes; rotational inertia on one node. |
| Temperature (`temperature2`) + Thermal stress | Yes | Constant temperature; a time table or formula in t in L30 and D31 (`EVOL_THER`, NL-70..75, DY-70..72). Static/modal/buckling: a time history is left out, as with Mecway's own solver. D30 ignores it like Mecway. Shells: Mecway expands less than the bridge; the bridge gives the theoretical free expansion αΔT·L (measured on a plate: bridge +3% (quad4) and +2% (quad8), Mecway −22% and −44%; solids equal to Mecway). So do not compare with Mecway for shells with thermal strain (KB95). |
| Node temperature (`temperature3`) in a mechanical analysis | Yes | Also after *Transfer temperatures from solution*. Static, nonlinear static, modal (prestress) and buckling, like Temperature; nodes without a temperature at the Thermal stress reference (LS-08). D30 ignores it like Mecway; D31 reported (not in Mecway's list). |
| Rayleigh damping | Partly | Only on the whole model, not on a selection (KB27). |
| Initial velocity | Yes | Dynamics only; not with mode superposition (KB54). |
| Initial displacement | No | Reported. |
| Value as a table or a formula in t | Yes | 10001 samples as Mecway does for CCX. Linear static, modal and buckling: the value at the end time. Many points = many steps (KB104). |
| Formula in x, y, z (mechanical) | Yes | Pressure, traction, force, line pressure, prescribed displacement/rotation: `FORMULE` of X, Y, Z (also with t) in `AFFE_CHAR_MECA_F` (LS-40..44, NL-40). Mecway 34 itself does not apply force, line pressure and displacement/rotation with x, y, z (WARNING). Not: gravity, moment, centrifugal, direction as a formula, pressure on shell edges; not in explicit, harmonic, spectrum (KB104). DKT/DST shells take the formula at the nodes (+0.8% on a coarse mesh, LS-44a). Pressure as a formula stays a fixed load at large displacements. The error estimator treats a face with a formula load as unloaded (too large an error there). |
| Load on the side face of a beam | No | KB5. Put the load on an element selection of the beam. |
| Pre-tension section | Partly | Prism of solid elements (Mecway's CCX variant), force or length adjustment, in static and nonlinear static: cut with `LIAISON_DDL` to a reference node (PT-01..05, [`Bolt_pretension.md`](Bolt_pretension.md)). Not: dynamic response, the spring element variant (KB122). |
| Electric potential, Charge, Current, Robin | No | No electric analyses (§1). |
| Thermal loads (temperature, heat flow, heat flux, heat generation, convection, radiation) | Yes | In T30/T31; formulas in x, y, z, t too. Details: [`Thermal.md`](Thermal.md). |
| Forced convection, Mass flow rate, cavity radiation | No | KB16. |
| Fluid pressure, Impedance (acoustics) | Partly | Fluid pressure only 0; impedance not frequency dependent, harmonic only real (KB55, KB57). |
| OpenRadioss cards in the model definition | No | Only `/FUNCT` (for `PLAS_TAB`) is read; the rest is reported (KB4). |

## 3. Constraints, couplings and contact

| Mecway | Status | Remark |
|---|---|---|
| Fixed support | Yes | Overlap with other constraints: Code-Aster does not clean up duplicate constraints like Mecway; the bridge catches the known cases and reports the rest (WARNING, KB8). |
| Pinned support | Yes | Nodes and faces of solid elements, as in Mecway. |
| Frictionless support | Partly | Not on beams; normal displacement ≠ 0 not on curved shells and shell edges (KB5). Next to a displacement/node rotation 0 on the same nodes (e.g. frictionless on the rim edges of a round plate plus X, Y, Z = 0, GitHub issue #9) the bridge drops the part of the relation that is already fixed, as Mecway reduces it (MO-09, LS-83). |
| Elastic support | Yes | Faces of solids and shell faces. |
| Compression only support | Partly | Only in nonlinear analyses, not together with contact; on shells the rotations stay free (KB22). |
| Displacement, Node rotation | Yes | Value as a formula in x, y, z: Yes; direction as a formula: No (KB104). Prescribed rotations with large rotations: KB11. |
| Velocity | Yes | Dynamics. |
| Symmetry | Yes | Faces of solids, shell edges and beam ends. |
| Cyclic symmetry | Partly | Only in Frequency (V30) and only solid elements; in static and thermal reported and computed as a loose sector (KB61). |
| Constraint equation | Yes | KB27. Explicit: a constant ≠ 0 becomes an imposed motion (DY-20b; Mecway itself does not allow it there). |
| Node-surface coupling, Rigid (RBE2) | Yes | `LIAISON_SOLIDE`; large rotations: KB11. Not in thermal (reported). |
| Node-surface coupling, Distributing (RBE3) | Yes | `LIAISON_RBE3`. Not in thermal (reported). |
| Flexible joint on beam | Yes | Free rotation about U, V and/or W (local beam axes as in Mecway) at a beam end: the element gets its own node there, coupled with `LIAISON_DDL` (translations and the rotations that are not free). Mecway has no stiffness in the joint, only free or fixed. Also on line3 beams and in Frequency, dynamics, buckling and nonlinear static (the latter not in Mecway). With `POU_D_T_GD` (large rotations) only a joint with U, V and W free (exact, NL-90); a joint with only some rotations free then stops beforehand with an ERROR (KB106). Verification LS-51 (equal to Mecway); section forces per element also next to the joint and on line3 (LS-53). A constraint on an *element selection* or component that contains the element with the joint acts on the joint's own node instead of on the nodes of the element as in Mecway: the result can differ and Code-Aster can stop with `FACTOR_11` (WARNING). Put it on nodes or faces (KB106). With an element offset on the same element (linear static and modal, line2): the joint sits at the end of the rigid arm, between the offset point and the element, as in Mecway 34 (Mecway node → arm → joint → element; LS-52a/b/c equal to Mecway in deflection and rotations); elsewhere a WARNING and no joint (KB108). Not in the thermal → mechanical chain (WARNING). |
| Contact, Unilateral (faces of solids and shell faces) | Yes | Nonlinear only, as in Mecway. Formulation and friction: KB43; pairs with shared slave nodes become one zone (reported, KB10). |
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
| hex8 | Partly | `3D` | Stiffer than Mecway (no incompatible modes, KB1); with rubber (hyperelastic) ~3x too stiff. Better: *Elements* > hex8 `LINE_QUAD`. |
| tet4, tet10, pyr5, pyr13, wedge6, wedge15, hex20 | Yes | `3D` | Pyramids not in acoustics (KB55). Strongly curved hex20/wedge15: natural frequencies up to 0.8% higher than Mecway (KB62). |
| tri3, quad4 (shell) | Yes | `DKT` (or `DST`/`COQUE_3D` as a choice) | ~0.7% different from Mecway (KB2). |
| tri6, quad8 (shell) | Yes | `COQUE_3D` | As master of bonded contact: displacements with `LIAISON_DDL`, rotations with `LIAISON_MAIL` (LS-07i..k). |
| linear and quadratic shells in one component | Partly | – | The quadratic ones are not modelled (ERROR). Split the component. |
| beam line2 | Yes | `POU_D_E` (or `POU_D_T`, `POU_D_T_GD`, `POU_D_TG`) | Orientation from *Element properties* or an *Element orientation* card (see Element orientation below). No plasticity (KB6). Large rotations only with `elem_beam` = `POU_D_T_GD` in nonlinear static with large displacements ([Settings §2.9](Settings_contact_and_nonlinear.md#29-beams-with-large-rotations-elem_beam--pou_d_t_gd); elsewhere `POU_D_T`, WARNING; verification NL-80–89); with `POU_D_E`/`POU_D_T` beams stay geometrically linear (KB11). Flexural-torsional and lateral-torsional buckling of open profiles (T, C, L, I) with `elem_beam` = `POU_D_TG`: warping and shear centre, warping at supports according to `beam_warping` ([Modal and buckling §3.5.1](Modal_and_buckling.md#351-beam-with-warping-elem_beam--pou_d_tg); verification BU-38 … BU-42, LS-90, LS-91); Mecway's own beam has no warping. |
| beam line3 | Yes | `POU_D_E` (or `POU_D_T`, `POU_D_T_GD`, `POU_D_TG`) | Each element is split at its midside node into two SEG2 cells (Code-Aster has no quadratic beam); results on all three nodes. Mecway itself solves line3 beams only with CCX. A curved element (midside node off the chord) thus becomes two straight pieces with a kink, Mecway computes the curved shape (WARNING; refine the curve, KB107). Verification LS-50. Spring, gap and damper on line3: No (ERROR; line2 only in Mecway); the bridge then stops before Code-Aster, as for every elset that cannot be translated. |
| truss line2 | Yes | `BARRE` | Small displacements (KB40). No linear buckling (no `RIGI_GEOM`, ERROR; [`Modal_and_buckling.md`](Modal_and_buckling.md) §3.3). Beams and trusses in one component become two groups (`<name>_TRUSS`). |
| truss line3 | Yes | `BARRE` | Each element is split at its midside node into two SEG2 cells (`BARRE` exists only on SEG2). Across the chord the midside node follows the mean of the end nodes (`LIAISON_DDL`, as Mecway); a direction already fixed on all three nodes (e.g. uz = 0 in a plane model) is left out. Curved element: two straight pieces (WARNING, KB107). The midside condition also suppresses the isolated midside-node modes that CalculiX gives without such a condition. No linear buckling (as line2). Verification LS-54 (bar), MO-08 (NAFEMS CP5: 451.15 / 1049.9 Hz, reference 451.1 / 1049.9; Mecway 34 itself 450 / 1030). |
| spring, damper, gap (line2) | Yes | `DIS_T` (gap: `DIS_CHOC`) | Along the element's own axis. Gap nonlinear only (KB23); springs/dampers not compared with Mecway (KB47). |
| tension only (line2, line3) | Partly | `CABLE` | Nonlinear only; compressive stiffness 1e-4 E (KB23). Line3 split into two SEG2 cells like truss line3 (LS-54b, LS-54c; Mecway 34 gave no solution headless for tension only). |
| elements of different dimension in one component | Partly | – | Only the highest dimension is modelled (ERROR). Split the component. |
| plane, axisymmetric (2D): tri3, tri6, quad4, quad8 | Yes | `C_PLAN`, `D_PLAN`, `AXIS` | Only in S20 and SA0 (§1); displacements equal to Mecway, also quad4 (no incompatible modes in Mecway's 2D). [`2D_and_axisymmetric.md`](2D_and_axisymmetric.md). |
| shells in a thermal analysis | Partly | `PLAN` with a thickness factor | Only shells in parallel planes (KB15); others: No (KB16). |
| fin, fluid network element, resistor | No | – | Thermal 1D and DC current: KB16. |
| Element offset (shell, beam) | Yes | DKT/DST: `COQUE` `EXCENTREMENT` (+ `INER_ROTA`); COQUE_3D and beams: element on its own nodes + rigid arm (`LIAISON_DDL`) | Shell: *Element coordinates*, only W counts (as in Mecway; u/v have no effect there either). Beam: *Global coordinates* x/y/z (u/v/w on a beam: no effect in Mecway, WARNING). Displacement, rotation and reaction at the Mecway nodes; stresses of the offset element shown at those nodes, also as element values (LS-65). In all mechanical analyses (Mecway: static only), not in the thermal → mechanical chain (WARNING, KB64). Rigid arm: small rotations, also with `GROT_GDEP` (WARNING for offset shells, KB108). A node with a value of its own (other element) keeps it; the stress of the offset element does not count there (KB108). A load on a face selection on edges of offset shells is applied at the nodes by the bridge, at the offset edge by Mecway (WARNING, KB108). A flexible joint on an offset beam element: in linear static and modal at the end of the arm, between the offset point and the element, as in Mecway (LS-52); elsewhere not translated (WARNING, KB108); bonded contact on offset shells: WARNING (KB108). Verification LS-60–67, LS-52. |
| Element orientation (local U/V axes) | Yes | beams: `AFFE_CARA_ELEM` `ORIENTATION` `CARA='VECT_Y'` | Mecway stores the orientation in two ways: per element (*Element properties*: attributes `orientationux`…`vz`, `angle`) and as an item in Loads & Constraints (*Element orientation* on an element selection: `<orientation selection="…">` with `ux`…`vz` and `angleu`, also as a formula of the element centre x, y, z; Mecway 34 keeps the card like this when saving). The bridge reads both in the same way. Beams: V axis and angle; every beam gets Mecway's V axis explicitly as `VECT_Y`, also without orientation (default V = Z × U, along Z V = Y). Gaps: U = direction. Shells: U axis of the result field `shell_forces` (§6). Solids, trusses, cables, springs and dampers: no effect (INFO); with an isotropic material that does not change the result, orthotropic material: §5 (No). An element with an orientation from both a card and the attributes, or from two cards: Mecway does not solve then (*already has its orientation defined elsewhere*), the bridge gives a WARNING and uses the card (of two cards the last one in the file). A U axis on beams, a V axis or angle on shells (Mecway does not solve then either) and a beam card without a V vector (Mecway: singular): WARNING, ignored. A card on a component name without an element selection of that name has no effect in Mecway: ERROR. Verification MO-31, LS-79–82, BU-25, LS-31d. |

## 5. Materials and cross-sections

| Mecway | Status | Remark |
|---|---|---|
| Isotropic (E, ν, ρ, α) | Yes | Without E the bridge uses 210 GPa, Mecway 0 (KB60). |
| Plastic, isotropic hardening curve | Yes | `VMIS_ISOT_TRAC`. E = slope of the first segment of the curve, as in Mecway (WARNING when *Young's modulus* differs; [`Settings_contact_and_nonlinear.md`](Settings_contact_and_nonlinear.md) §2.4). Not on beams (elastic, WARNING; KB6). |
| Plastic, Bilinear isotropic / kinematic | Yes | `ECRO_LINE`; Mecway's *tangent modulus* is the plastic modulus H, `D_SIGM_EPSI` = E·H/(E+H); perfectly plastic with tangent modulus 0. |
| Plastic, Kinematic (curve) | Partly | Only a curve with linear hardening (`VMIS_CINE_LINE`); a nonlinear curve is computed as elastic (reported). No equivalentplasticstrain (KB6). |
| Plastic, Ramberg-Osgood | Yes | Sampled curve (KB6). |
| Spring, Damper, Gap, Tension only | Yes | Only on line2 (§4); tension only also on line3 (LS-54b). Gap: *force of open gap* not used (KB23). |
| Neo Hooke, Mooney-Rivlin (hyperelastic) | Yes | `ELAS_HYPER` (C10, C01, K = 2/D1) with `GREEN_LAGRANGE`, in nonlinear static and dynamics (implicit and explicit), volume elements only (as in Mecway). D1 = 0, shells/beams and linear analyses: ERROR; thermal expansion ignored (WARNING). [`Settings_contact_and_nonlinear.md`](Settings_contact_and_nonlinear.md) §2.4, verification NL-50..53. |
| Orthotropic, Anisotropic (matrix), Composite, piezo | No | WARNING, then the run stops ("elset without a usable material"). No alternative in the bridge. Hyperfoam: ERROR (not possible with Code-Aster 17.4 on Windows: no MFront support; see [Settings contact and nonlinear](Settings_contact_and_nonlinear.md), hyperelastic material). |
| Failure criterion (factor of safety) | Partly | Von Mises (*tensile strength*): `factorofsafety` to Mecway (result field `safety_factor`, §6). Tsai-Wu and other criteria: WARNING, no factor of safety. For plastic failure: [`Failure.md`](Failure.md). |
| Thermal: conductivity, specific heat, also *Temperature dependent* | Yes | [`Thermal.md`](Thermal.md). Formulas in material properties: No (KB16). |
| Speed of sound (acoustics) | Yes | Media with different density: No (KB55, KB59). |
| OpenRadioss law `PLAS_TAB` | Partly | Fields not translated: KB34. Law `VOID`: elements left out (reported); other laws: No. |
| Section circular and rectangular (solid and hollow), General section, I, T, L, C | Yes | Mecway's *Stress recovery point* is not used. Other geometry types: No (WARNING). |
| Plate thickness (Plate) | Yes | Shells; in S20 the thickness of the plane elements, with *plane strain* `D_PLAN`. |

## 6. Results back in Mecway

| Mecway field | Status | Remark |
|---|---|---|
| Displacement, rotation | Yes | Modal and buckling: the mode shapes. |
| Stress tensor of solid elements (node and element node) | Yes | Code-Aster averaging, different from Mecway (KB3). Route `tabel`: KB7. |
| von Mises (solids; shells top/middle/bottom) | Yes | KB3. |
| Stress tensor of shells (global, top/middle/bottom), forces and moments per length | Yes | Fields `shell_stresses` (off by default) and `shell_forces`; route `liml` only. `shell_forces` is on for static and nonlinear and makes the results about 2.5 times larger with shells (WARNING; untick it on the page of the analysis). Mecway's *stress in element coordinates* (`stressuu` ..) not. U axis from *Element properties* or an *Element orientation* card ([`UserGuide.md`](UserGuide.md) §4.1). |
| Beam stress | Partly | Only smallest/largest axial stress for rectangular and circular sections (`beamsixxmin/max`); not with `POU_D_T_GD` (WARNING). |
| Section forces and moments of beams | Yes | Field `beam_forces` (`tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv/w`), also per mode. With `POU_D_T_GD` from `SIEF_ELNO`, one value per element in the co-rotating axes (NL-81, NL-83). |
| Reaction forces and moments | Yes | Not with mode superposition, harmonic and vibroacoustics (KB54, KB59). |
| Velocity, acceleration | Yes | Dynamics; acceleration not with mode superposition (KB54). |
| Plastic strain, equivalent plastic strain | Partly | Equivalent plastic strain not with kinematic hardening (KB6). |
| Total strain | Yes | Field `strain` (off by default): `lstrain*`, nonlinear `greenlagrangestrain*`; shells top/middle/bottom. No logarithmic strain and no principal strains. |
| Contact pressure, contact state | Partly | Field `contact`: `contactpressure`, `contactstate` (0/1/2). No contact shear stress and displacement; sliding (2) NOT verified. |
| Factor of safety | Yes | Field `safety_factor` (von Mises, §5). |
| Principal stress, Tresca stress, principal strain | Yes | Fields `principal_stresses` and `principal_strains` (off by default): `principal1..3`, `tresca`, `lprincipalstrain1..3` (Green-Lagrange: `greenlagrangeprincipalstrain1..3`) of solids and `principal1u1`, `trescau1`, `lprincipalstrain1u1` .. (top/middle/bottom) of shells, computed as Mecway does (eigenvalues per element node, node = average). Verification FX-02, FX-04, FX-05. |
| Temperature, heat flux | Yes | Thermal. |
| Natural frequencies, buckling factors, effective mass | Yes | Effective mass fraction differs from Mecway (KB49). |
| Acoustic pressure | Yes | [`Acoustics.md`](Acoustics.md). |
| *Saved monitor* (Solution) | Yes | The output of the Code-Aster run instead of Mecway's solver messages (setting `save_monitor`, route `liml`; [`UserGuide.md`](UserGuide.md) §5.2). |

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
| Time step size | Yes | D30, T31 and L30 (L30: Mecway's steps up to the period plus the kinks of the load tables; without a step size `substeps_per_interval`). With *Automatic time stepping* see the row below. |
| Output times, *Generate solution every n time steps* | Yes | |
| Automatic time stepping | Yes | L30 (nonlinear static): `DEFI_LIST_INST METHODE='AUTO'` between Mecway's output times, `ARCHIVAGE` at those times; setting `auto_time_stepping`. Dynamic not: fixed steps, cutting on divergence. |
| Incompatible hex8 | No | KB1. |
| Solution > Formula (result formulas, e.g. `qf.z/3600/(12^2)`) | Partly | Computed by the bridge from the results, in the units of the formula, per node and time step, as Mecway does in its own solve (FX-01 .. FX-03); `s1`, `tr`, `e1`, `GLe1` with the fields `principal_stresses` / `principal_strains`. Not: element coordinates, shell forces, material symbols (WARNING; create the formula again after loading, KB121). [`UserGuide.md`](UserGuide.md) §4.2. |
| CCX > custom element type (e.g. Hex8 → C3D8R) | No | CalculiX only: WARNING, Code-Aster uses the *Elements* page (hex8 `3D` = C3D8, `LINE_QUAD` = C3D20; C3D8R/C3D8I have no equal). [`Settings_contact_and_nonlinear.md`](Settings_contact_and_nonlinear.md), hyperelastic material. |
| Configurations | Yes | One per run, chosen on the start screen (*Configuration*); results in the solution of that configuration ([`UserGuide.md`](UserGuide.md) §4, LS-20). |
| Custom model definition (CCX, OpenRadioss, Nastran) | Partly | Only `#ASTER` lines; ordinary CCX cards are ignored without a message. |
