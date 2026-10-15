# Code-Aster error messages: cause and solution

*Nederlandse versie: [Foutmeldingen_CodeAster.md](../Foutmeldingen_CodeAster.md)*

Reference of the Code-Aster messages (errors and alarms) that came up while building,
testing and verifying the bridge. For each code: the meaning, the usual cause in a
Mecway model, where the message was seen, the solution and the status.
Code-Aster version: 17.4.0 (Windows build, modified 22-01-2026, see the header of every
`.mess`).

The message texts come from the message catalogue of the installation (EDF R&D, 2026a):
`FACTOR_57` is in `Messages/factor.py` under number 57, `MECANONLINE9_7` in
`Messages/mecanonline9.py` under 7, and so on. "Seen" means: in a real run (Mecway,
Code-Aster directly or the verification framework `TestFiles/Verificatie`). "Derived
from the code" means: the bridge avoids the message based on an earlier run, described
in the comments of the function named. Commit numbers refer to the Git history of the
bridge.

**Status** per message:

- **fixed in the bridge**: the bridge prevents the message, or reports the cause
  beforehand;
- **model**: the cause lies in the Mecway model; adjust the model;
- **limitation**: Code-Aster cannot do it; there is a workaround or nothing can be done;
- **harmless**: expected alarm; the results are correct;
- **own input**: the cause lies in your own `#ASTER` lines or an edited `.comm`;
- **cause not determined**: seen, but not investigated.

Bugs in the bridge itself are listed in `KNOWN_BUGS.md` (Dutch); only the reference is
given here.

---

## Contents

- [Finding the message](#finding-the-message)
- [Adding a message](#adding-a-message)
- [1. Mesh and groups](#1-mesh-and-groups)
- [2. Model, elements and loads](#2-model-elements-and-loads)
- [3. Boundary conditions and singular matrix](#3-boundary-conditions-and-singular-matrix)
- [4. Contact](#4-contact)
- [5. Nonlinear analysis and dynamics](#5-nonlinear-analysis-and-dynamics)
- [6. Large rotations](#6-large-rotations)
- [7. Post-processing](#7-post-processing)
- [8. Syntax and `#ASTER` lines](#8-syntax-and-aster-lines)
- [9. System, solver and follow-on errors](#9-system-solver-and-follow-on-errors)
- [10. Modal and buckling](#10-modal-and-buckling)
- [11. Error estimator](#11-error-estimator)
- [Codes in alphabetical order](#codes-in-alphabetical-order)
- [Assumptions](#assumptions)
- [References](#references)

---

## Finding the message

All files of a run are named `<model>_<run-id>.*` (see
[User guide §5](UserGuide.md#5-files-in-the-working-directory)); below, `.mess`, `.comm` and
`.export` for short. Messages from the bridge give the real file name.

1. **In Mecway.** After the run the bridge shows the errors from the `.mess` in the
   status box of the main window (without the main window: as a Mecway message)
   (`bridge_run_aster.aster_mess_errors`): the code, the text from the message box and,
   for a known code, an explanation in the chosen language (`_MESS_HINTS` in
   `Scripts/bridge_run_aster.py`):
   - `FACTOR_10`, `FACTOR_11`, `FACTOR_42`, `FACTOR_57`: singular stiffness matrix;
   - `MECANONLINE9_4`: the same, plus the advice for a pivot on `LAGS_C` (contact):
     *Contact method* = PENALISATION (not `solver_nprec` = -1: it does run through, but
     is inaccurate, −1.6% / +2.8% in NL-03a, R-NPREC-CONTACT in
     [Default settings §5](Default_settings_and_assumptions.md#5-check-runs-for-this-review));
   - `MECANONLINE9_7`: Newton does not converge, with the next steps (see
     [`MECANONLINE9_7`](#mecanonline9_7--newton-does-not-converge)) and "Last time with
     results: ... s" if the job wrote `BRIDGE_ONVOLLEDIG <time>`;
   - `ALGELINE3_81`, `ALGELINE5_49`, `ALGELINE3_78`: modal and buckling (§10);
   - `ALGORITH16_52`, `ALGORITH16_58`, `ALGORITH14_94`: cyclic symmetry (§10).

   Alarms (`<A>`) are not part of that message, but appear as
   `WARNING: Code-Aster alarm <CODE> in <model>_<run-id>.mess.` in
   `<model>_<run-id>_bridge_log.txt`; for `ALGELINE5_23`, `ALGELINE3_82`,
   `ALGELINE2_74`, `MODELISA4_8`/`MODELISA8_13` (duplicate cells) and, with complex
   modes, `ALGELINE5_79` and `FACTOR_11` with an explanation (`_ALARM_HINTS`):
   `WARNING: Code-Aster alarm <CODE> in <model>_<run-id>.mess: <explanation>`. The convergence and messages window shows errors and
   alarms per run, with an explanation for a zero pivot per kind of degree of freedom
   (`bridge_convergence.pivot_hint`; [Settings §4.4](Settings_contact_and_nonlinear.md#44-convergence-screen)).
2. **The `.mess` in the work folder** (`work_dir`). Search for:
   - `<EXCEPTION>`, `<F>`, `<S>`, `<E>`: error; the job stops or skips the commands that
     follow;
   - `<ConvergenceError>`, `<SolverError>`, `<IntegrationError>` and other
     `<...Error>`: error in `STAT_NON_LINE`/`DYNA_NON_LINE`; the bridge catches it and
     continues with the post-processing (results up to the last time reached);
   - `<A>`: alarm, the job continues;
   - `<I> <CATAMESS_89>` at the end: all alarms with their count.

   Above the box is the command with `# Commande #00nn de ....comm.changed.py, ligne N`.
   `N` is the line number in the copy of the `.comm` adapted by Code-Aster; usually
   equal to the `.comm` itself (NOT verified for every case). The last line
   `--- DIAGNOSTIC JOB : ...` says `OK`, `<A>_ALARM` or `<F>_ABNORMAL_ABORT`. Note: even
   after an `<EXCEPTION>` it sometimes says `OK` or `<A>_ALARM` (seen: `FACTOR_42` with
   `DIAGNOSTIC JOB : OK`). Judge a run by the message boxes, not by that line; the bridge
   does the same.
3. **`<model>_<run-id>_bridge_log.txt`** in the work folder: errors before Code-Aster
   (ERROR/WARNING per step), renamed groups (`INFO: Groepsnaam 'x' -> 'y'`; INFO lines are in Dutch), merged
   contact zones, skipped loads.
4. **No message box.** With `<F>_ABNORMAL_ABORT` without a box, the cause is only shown
   in the Code-Aster window (which then stays open). If `<FIN>` is missing from the
   `.mess`, the `.comm` was not executed to the end (Python error); the bridge reports
   "Python error in `<model>_<run-id>.comm`" with the error line from
   `<model>_<run-id>_console.txt` ([§8](#8-syntax-and-aster-lines)).
5. **Running again without Mecway**: `run_aster.bat <model>_<run-id>.export` in the work
   folder. This lets you edit the `.comm` of that run by hand and try a solution.

## Adding a message

Copy this block under the right topic and fill in every field; if unknown:
"not determined" or "NOT verified".

```markdown
### `CODE` – short title

- **Message** (error/alarm): English summary of the text.
- **Cause in a Mecway model**: ...
- **Seen**: test model/situation (and commit of the fix).
- **Solution**: in Mecway: ... / in the bridge: ... / with `#ASTER` lines: ...
- **Status**: fixed in the bridge | model | limitation | harmless | own input | cause not determined.
```

Also add the code to [Codes in alphabetical order](#codes-in-alphabetical-order) and to
the Dutch version. If the bridge explains it, add the code to `_MESS_HINTS` (error) or
`_ALARM_HINTS` (alarm) in `Scripts/bridge_run_aster.py`.

---

## 1. Mesh and groups

The bridge writes the mesh itself in the ASTER format (`Scripts/bridge_mesh.py`,
`LIRE_MAILLAGE FORMAT='ASTER'`). Messages in this topic almost always point to an error in
that file, not in the model.

### `MODELISA7_85` – number expected in the mesh

- **Message** (error): "(LIGNE n) un nombre est attendu": line n contains no number
  Code-Aster can read.
- **Cause**: a coordinate such as `-1e-05` (without a decimal point) is not read as a
  number.
- **Seen**: a cutting model (dynamic, contact).
- **Solution**: in the bridge: `bridge_mesh._real` always writes a decimal point
  (`-1.0e-05`) (commit 117dba3).
- **Status**: fixed in the bridge.

### `MODELISA7_66` – item expected at the start of the line

- **Message** (error): "(LIGNE n) item attendu en début de ligne".
- **Cause**: (a) a line longer than 80 characters (HEXA20 with long node names); (b) a
  number with a comma (`0,25`): `"{0:.15g}".format()` follows the Dutch locale in
  Mecway's IronPython.
- **Seen**: (a) hex20 beam with pinned support; (b) IronPython test harness.
- **Solution**: in the bridge: lines wrapped at 79 characters (`bridge_mesh._wrap`,
  commit f9ac7f9) and `%` formatting in `_real` (commit 543fe80).
- **Status**: fixed in the bridge.

### `MODELISA7_81` – not a valid name

- **Message** (error): "un identificateur est attendu : 'x' n'en est pas un".
- **Cause**: a group name starting with a digit (`02ContactProfiel`) or containing
  brackets (`Linear(2)`). Mecway allows such names.
- **Seen**: name test with names like `02ContactProfielToRol`, `13FixZ`.
- **Solution**: in the bridge: `bridge_mesh._aster_names` renames (e.g.
  `G02ContactProfiel`) and logs it; in `#ASTER` lines use `<<Mecway name>>`
  (commit 93eaa5f).
- **Status**: fixed in the bridge.

### `MODELISA5_7` – cell does not exist

- **Message** (error): "La maille b déclaré dans le GROUP_MA a n'existe pas dans les
  connectivités".
- **Cause**: a group name with `.` or `-` (`a.b`, `Fix-Z`): the reader splits the name.
- **Seen**: name test (see `MODELISA7_81`).
- **Solution**: as for `MODELISA7_81`.
- **Status**: fixed in the bridge.

### `MODELISA7_82` – internal error with a long group name

- **Message** (error): "message d'erreur développeur", without explanation.
- **Cause**: a group name of more than 24 characters (24 works, 25 does not).
- **Seen**: name test when moving from Gmsh to the ASTER format.
- **Solution**: in the bridge: names are shortened to 24 characters and made unique
  (`ASTER_NAME_MAX`, `_aster_names`; commit 93eaa5f).
- **Status**: fixed in the bridge.

### `MODELISA_1` – mesh cannot be read

- **Message** (error): "Problème à la relecture du fichier de maillage".
- **Cause**: follows from an earlier mesh message (`MODELISA7_66`, `_81`, `_85`).
- **Seen**: together with those messages.
- **Solution**: fix the first message.
- **Status**: fixed in the bridge (through the causes above).

### `MODELISA4_80` – group empty

- **Message** (alarm): "le groupe X est vide. On l'ignore."
- **Cause**: the former Gmsh route cut group names to 8 characters; the group under the
  full name stayed empty.
- **Seen**: name test with the Gmsh route.
- **Solution**: in the bridge: no Gmsh any more, the mesh comes directly from the
  `.liml` (commit 93eaa5f). If you see this alarm now, a selection in Mecway is probably
  really empty.
- **Status**: fixed in the bridge.

### `MODELISA7_75`, `MODELISA7_77` – group does not exist

- **Message** (error): "le GROUP_NO X ne fait pas partie du maillage" (`7_75`) or "le
  GROUP_MA X ne fait pas partie du maillage" (`7_77`).
- **Cause**: (a) an `#ASTER` line names a selection that does not exist (typo);
  (b) a constraint, load or coupling on an empty or missing selection.
- **Seen**: (a) tests of `ASTER_lines_examples.md`; (b) derived from the code
  (`bridge_mesh`, comment on skipping empty selections).
- **Solution**: (a) the bridge first logs
  `ERROR: #ASTER: selection 'X' does not exist in the mesh.` (checked 06-10-2026);
  check the name in Mecway, the renamed names are in the log. (b) in the bridge: such a
  constraint or coupling is skipped and reported (`skipped_loads`).
- **Status**: own input (a) / fixed in the bridge (b).

### `MODELISA6_10` – cell not in the mesh

- **Message** (error): "la maille X ne fait pas partie du maillage Y".
- **Cause**: a group with cells by name (`M<eid>`) where Code-Aster expects the cell
  number.
- **Seen**: derived from the code (`bridge_thermal._list_group`; element IDs +1000 gave
  this error).
- **Solution**: in the bridge: the Mecway element number is translated to the cell
  number in the mesh (`model_data["cell_names"]`).
- **Status**: fixed in the bridge.

### `MODELISA5_8` – cell twice in a group

- **Message** (alarm): "La maille X est en double dans le GROUP_MA Y. On élimine les
  doublons."
- **Cause**: a face selection with face 5 and face 6 of the same shell element.
- **Seen**: derived from the code (`bridge_mesh`, `bridge_thermal`).
- **Solution**: in the bridge: each cell once per group; a thermal load on both sides of
  a shell gets its own group with factor 2.
- **Status**: fixed in the bridge.

### `SOUSTRUC_37`, `SOUSTRUC_38` – node group already exists / is empty

- **Message**: `SOUSTRUC_37` (error): the node group already exists; `SOUSTRUC_38`
  (alarm): the node group is empty and is not created.
- **Cause**: completing node groups after `CREA_MAILLAGE LINE_QUAD`, and the group of
  centre nodes of `COQUE_3D` shells.
- **Seen**: derived from the code (`bridge_to_aster`, `_LQ_GROUPS` and the group of
  QUAD9/TRIA7 centre nodes).
- **Solution**: in the bridge: delete an existing group first (`DETR_GROUP_NO`); shell
  edges are not put in the centre-node group.
- **Status**: fixed in the bridge.

### `UTILITAI5_1` – file for a unit missing

- **Message** (error): "Le fichier de nom 'fort.19' associé à l'unité logique 19
  n'existe pas."
- **Cause**: the `.export` names a mesh file that does not exist.
- **Seen**: offline test harness with the former Gmsh route.
- **Solution**: check the `F ... D <unit>` lines in the `.export`; let the bridge create
  `work_dir` and the `.export` itself.
- **Status**: cause in the test setup, not in the bridge.

### `MODELISA4_6` / `MODELISA8_11` – orphan nodes

- **Message** (alarm): "présence de noeuds orphelins" / "Le noeud N est orphelin".
- **Cause**: loose nodes in the Mecway model (auxiliary nodes, nodes left after deleting
  elements).
- **Seen**: solid model R_Voorbeeld; test C6_elastic.
- **Solution**: harmless as long as there is no load or support on that node; otherwise a
  singular matrix (`FACTOR_*`). In Mecway: delete or connect loose nodes.
- **Status**: harmless (usually).

### `MODELISA4_8` / `MODELISA8_13` – duplicate elements

- **Message** (alarm): "présence de mailles doubles" / "Les mailles A et B sont doubles".
- **Cause**: (a) two face selections on the same faces: each face was written twice as a
  boundary element; (b) a spring and a damper between the same nodes; (c)
  vibroacoustics: a shell on a fluid face and its coupling face (`FLUI_STRU`) are
  separate cells on the same nodes.
- **Seen**: (a) a mixed test model (RBE); (b) damper test D18_damper; (c) verification
  VA-03, VA-05 (frequencies exact).
- **Solution**: in the bridge: (a) a face selection with the same faces as an earlier
  group becomes a copy (`DEFI_GROUP CREA_GROUP_MA`, commit 631cc36); (b), (c) intended
  (a cell can have only one modelling).
- **Status**: fixed in the bridge (a) / harmless (b, c).

### `MODELISA8_14` – POI1 inside another element

- **Message** (alarm): "La maille POI1 N est incluse dans une autre."
- **Cause**: a point element (point mass, spring to ground, RBE master node) on a node
  that also belongs to another element.
- **Seen**: tests with point mass, centrifugal load, damper and gap elements; also in the
  official test cases ssls114a and sdls115a (`Verification.md`).
- **Solution**: none; intended.
- **Status**: harmless.

### `MESH1_4` – LINE_QUAD on part of the mesh

- **Message** (alarm): only part of the cells becomes quadratic; that can give a
  non-conforming mesh.
- **Cause**: *Linear shells* = `COQUE_3D` in a model with other elements as well: the
  bridge makes only the shell groups quadratic (`_resolve_line_quad`).
- **Seen**: derived from the code and the catalogue text (`mesh1.py`); NOT checked in a
  saved `.mess`.
- **Solution**: none needed if the bridge chose it: it only does so if the shells share
  no nodes with elements that stay linear (otherwise DKT with a WARNING).
- **Status**: harmless.

---

## 2. Model, elements and loads

### `MODELISA_78` – shear coefficient missing (beam)

- **Message** (alarm): "section GENERALE élément poutre : il manque la caractéristique
  AY1" (or AZ1); then `DVP_2`.
- **Cause**: `POU_D_T` with a general section (`SECTION='GENERALE'`) without AY/AZ.
- **Seen**: test model with all Mecway profile types.
- **Solution**: in the bridge: by default *Beams* = `POU_D_E` (Euler-Bernoulli, like
  Mecway; commit e772fab). With `POU_D_T` the bridge computes AY/AZ from the profile
  (`bridge_from_liml._profile_shear_coefs`); unknown profile: AY = AZ = 1 with a WARNING.
- **Status**: fixed in the bridge.

### `DVP_2` – floating point exception

- **Message** (error): "Erreur numérique (floating point exception)".
- **Cause**: (a) `POU_D_T` with `SECTION='GENERALE'` without AY/AZ (see `MODELISA_78`);
  (b) `POU_D_T_GD` with `RELATION='ELAS'`; that beam needs `ELAS_POUTRE_GR` (test case
  ssnl103a, EDF R&D, 2026c); (c) vibroacoustics: `NORM_MODE MASS_GENE` on a spurious mode
  with negative generalised mass (seen with a shell with only one rotation fixed; the
  bridge now filters those modes first, [`Acoustics.md`](Acoustics.md) §6.5).
- **Seen**: (a) profile test; (b) large-rotation trials.
- **Solution**: (a) see `MODELISA_78`; (b) only with your own `POU_D_T_GD` code:
  `ELAS_POUTRE_GR`. The bridge does not create `POU_D_T_GD`.
- **Status**: fixed in the bridge (a) / own input (b).

### `CALCUL_37` – element cannot compute this option

- **Message** (error): "Le TYPE_ELEMENT X ne sait pas encore calculer l'option: Y".
- **Cause**, five cases:
  1. `MECA_HEXS8` (hex8 as `3D_SI`) cannot compute `PAS_COURANT` (stable time step in
     explicit dynamics);
  2. `MECA_POU_D_T_GD` cannot compute `RIGI_MECA` (`PREDICTION='ELASTIQUE'` or
     `MATRICE='ELASTIQUE'` with a GD beam);
  3. `MEDKQU4` (DKT) and `MECA_DIS_T_N` (discrete element) cannot compute
     `CHAR_MECA_ROTA_R` (centrifugal load with shells or discrete elements);
  4. format test model F4_model (dynamics): element and option not checked;
  5. `MECABL2` (cable, tension only) cannot compute `ROTATION`.
- **Seen**: 1 explicit dynamics with `3D_SI`; 2 beam trials; 3 and 4 load tests; 5 code
  review (commit 6ce5cba).
- **Solution**: 1 the bridge always chooses `3D` with an explicit scheme (WARNING); 2 no
  `PREDICTION`/`MATRICE='ELASTIQUE'` with GD beams; 3 `ROTATION` only on elsets without
  discrete elements, in a model with shells as a `FORMULE` of X, Y, Z per elset and
  `FORCE_NODALE` on nodal masses (`_centrifugal_loads`); 4 not determined; 5 cables get
  no centrifugal force (ERROR; KNOWN_BUGS 19).
- **Status**: fixed in the bridge (1, 3; 5 as a message) / own input (2) / cause not
  determined (4).

### `CALCUL_42` – option not yet programmed (follower pressure on DKT)

- **Message** (error): "Le TYPE_ELEMENT MEDKQU4 devrait calculer l'option :
  RIGI_MECA_PRSU_F, mais il ne le fait pas encore".
- **Cause**: pressure as a follower load (`TYPE_CHARGE='SUIV'`, large displacements) on
  DKT/DST shells.
- **Seen**: derived from the code (`bridge_to_aster`, docstring of the follower
  pressure; test run).
- **Solution**: in the bridge: follower pressure only on solid faces and `COQUE_3D`; on
  DKT/DST the pressure stays fixed (WARNING). Choose *Linear shells* = `COQUE_3D` for
  follower pressure on shells.
- **Status**: fixed in the bridge (as a message).

### `CALCUL_20` – material missing

- **Message** (error): "Le matériau est nécessaire sur la maille ...".
- **Cause**: an elset in the model without a translated material.
- **Seen**: derived from the code (`bridge_to_aster`, material check; QA run).
- **Solution**: in the bridge: ERROR before Code-Aster with the name of the elset; give
  the component a material in Mecway.
- **Also seen**: `CALC_G` (fracture mechanics) on the boundary cells of the lips
  (`MECA_FACE8`, option `CALC_K_G`): the bridge assigns the material per elset, not to
  the boundary cells. Fixed in the bridge: `CALC_G` works on a result of its own with a
  material on all cells (`bridge_fracture._material_block`,
  [Fracture_mechanics.md](Fracture_mechanics.md) §2.1).
- **Status**: fixed in the bridge (as a message).

### `CALCULEL2_92` – more than one distributed load on a beam

- **Message** (error): "votre chargement contient plus d'une charge répartie, le calcul
  n'est pas possible pour les modèles de poutre".
- **Cause**: more than one load with a distributed beam load in one analysis (also in
  `CALC_CHAMP` `SIPM_ELNO`): line pressure, gravity and centrifugal force on beams.
- **Seen**: `FORCE_POUTRE` and `PESANTEUR` in separate loads; two line pressures on
  overlapping selections.
- **Solution**: in the bridge (`_prepare_beam_loads`): the beams are split into disjoint
  groups with the sum of the loads per group, in one load; with a time-dependent line
  pressure everything in one `AFFE_CHAR_MECA_F`. Not yet: local and global line pressure
  on the same beam and centrifugal force with a time-dependent line pressure (ERROR
  beforehand); gravity with a time history together with line pressures on beams
  (WARNING). See KNOWN_BUGS 20.
- **Status**: fixed in the bridge, except for the cases named.

### `MECANONLINE_3` (with alarm `CALCULEL_54`) – element not for nonlinear analysis

- **Message** (error): "les éléments ne sont pas programmés pour cela"; first alarm
  `CALCULEL_54` about `PCOMPOR` of `FULL_MECA`.
- **Cause**: shells as `DST` in `STAT_NON_LINE`/`DYNA_NON_LINE`.
- **Seen**: flat quad4 plate, nonlinear with DST.
- **Solution**: in the bridge: DST only with `MECA_STATIQUE`, otherwise DKT with a
  WARNING (commit 9ba9857).
- **Status**: fixed in the bridge.

### `COMPOR5_22` – GROT_GDEP not on solid elements

- **Message** (error): "COMPORTEMENT affecte le modèle de déformation GROT_GDEP sur une
  modélisation MECA_HEXA8. Ce n'est pas possible."
- **Cause**: `DEFORMATION='GROT_GDEP'` on solid elements.
- **Seen**: a bending model (contact) and an `#ASTER-OPTIE` test.
- **Solution**: in the bridge: `deformation` is translated per element type
  (`_deformation_for`): solids `GREEN_LAGRANGE` (elastic) or `GDEF_LOG` (plastic),
  DKT/DST `GREEN_LAGRANGE`, `COQUE_3D` `GROT_GDEP`, beams `PETIT`
  ([Settings §2.3](Settings_contact_and_nonlinear.md#23-kinematics-deformation)). If you
  still see the message, it comes from your own `#ASTER` code.
- **Status**: fixed in the bridge.

### `COMPOR1_44`, `COMPOR1_99` – strain measure does not suit the law or element

- **Message** (error): `COMPOR1_44`: the strain type does not suit the law;
  `COMPOR1_99`: structural elements cannot be used with `DEFORMATION='GDEF_LOG'`.
- **Cause**: `COMPOR1_44`: `GREEN_LAGRANGE` with a Von Mises law (`VMIS_*`);
  `COMPOR1_99`: `GDEF_LOG` on shells or beams.
- **Seen**: mixed model while working out large displacements (commit 1de4c87).
- **Solution**: in the bridge: see `COMPOR5_22`.
- **Status**: fixed in the bridge.

### `COMPOR1_47` – COQUE_3D with GROT_GDEP: rotations below 2π

- **Message** (alarm): with `COQUE_3D` and `GROT_GDEP` the rotations must stay below 2π.
- **Cause**: large displacements with `COQUE_3D` shells.
- **Seen**: runs with large displacements (comment at `_deformation_for`).
- **Solution**: none needed as long as a shell does not turn more than a full revolution.
- **Status**: harmless.

### `MODELE1_7` – 3D_SI only for parallelepipeds

- **Message** (alarm): "l'élément HEXA8 en 3D_SI ne fonctionne correctement que sur les
  parallélépipèdes".
- **Cause**: *Hex8 solid elements* = `3D_SI`.
- **Seen**: trials with 3D_SI.
- **Solution**: the bridge uses `3D_SI` only if an elset contains hex8 only. Prefer
  `LINE_QUAD` (KNOWN_BUGS 1).
- **Status**: harmless (deliberate choice); watch the stresses.

### `PLATE1_40` – shell cannot be oriented

- **Message** (error): "L'élément de plaque ne peut pas être orienté".
- **Cause**: a shell in a plane x = constant (normal along X).
- **Seen**: plate coupled to a block, rotated to x = constant.
- **Solution**: in the bridge: `_shell_ref_vector` then sets `VECTEUR` in
  `AFFE_CARA_ELEM COQUE` (commit 354c7e9). If one selection has normals along all axes
  (closed box), a WARNING: split the selection per plane in Mecway.
- **Status**: fixed in the bridge (except the box case).

### `MODELISA4_50` / `MODELISA4_51` – cell without element

- **Message**: `4_50` (alarm): "la maille N n'est pas affectée par un élément fini";
  `4_51` (error): none of the cells has an element.
- **Cause**: `#ASTER` code (`LIAISON_ELEM` 3D_POU) names a face selection of solid
  elements that was not in the model.
- **Seen**: beam attached to a solid face with `LIAISON_ELEM`.
- **Solution**: in the bridge: a solid face named as `<<name>>` in `#ASTER` lines is
  added to the model as a boundary element (`bridge_mesh`, `skin_groups`).
- **Status**: fixed in the bridge.

### `MODELISA6_96` / `PROJECTION4_55` – LIAISON_MAIL

- **Message**: `MODELISA6_96` (error): cells in `LIAISON_MAIL` do not belong to the model;
  `PROJECTION4_55` (error): the master cells must have the same dimension as the model.
- **Cause**: bonded contact or a force on shell edges, translated with faces that were
  not in the model, or with boundary faces as master.
- **Seen**: tests C15_bondedtie and S4_edge.
- **Solution**: in the bridge (`bridge_mesh._bonded`): master = the solid elements next
  to the face, slave = the nodes of the face (`GROUP_NO_ESCL`).
- **Status**: fixed in the bridge.

### `CHARGES2_31` – degree of freedom does not exist on the node

- **Message** (error): a boundary condition on degree of freedom X of node N, while that
  node does not carry X.
- **Cause**: the centre node of QUAD9/TRIA7 (`COQUE_3D`) has rotations only;
  `LIAISON_OBLIQUE` or `LIAISON_MAIL` puts `DX` on it.
- **Seen**: derived from the code (`bridge_to_aster`, QA model M15b_bonded_coque and
  frictionless on `COQUE_3D`).
- **Solution**: in the bridge: the centre nodes go into `SANS_GROUP_NO`; shells that are
  master of bonded contact stay DKT (WARNING; KNOWN_BUGS 21).
- **Status**: fixed in the bridge.

### `ELEMENTS4_92` – pressure as a function on a shell

- **Message** (error): a pressure load as a function (`PRES_REP`) on a shell element;
  Code-Aster requires `FORCE_COQUE` there.
- **Cause**: pressure with a time history on shells.
- **Seen**: derived from the code (`bridge_to_aster`, `bridge_mesh`; test run).
- **Solution**: in the bridge: `PRES = 1` with the history as `FONC_MULT`, or
  `FORCE_COQUE PRES` with a function.
- **Status**: fixed in the bridge.

### `CHARGES2_89` – no cell of the right type

- **Message** (alarm): none of the cells in the keyword has the right type; all are
  ignored.
- **Cause**: pressure (`PRES_REP`) on an element selection of solid elements.
- **Seen**: derived from the code (`bridge_mesh`, reported in a review; NOT checked with
  a run).
- **Solution**: in the bridge: pressure on an element selection only for shells;
  otherwise ERROR and not translated. Choose a face selection in Mecway.
- **Status**: fixed in the bridge (as a message).

### `POUTRE0_61` – plasticity on a classical beam

- **Message** (error): the law (e.g. `VMIS_ISOT_LINE`) is not available for classical
  beams; use multifibre beams.
- **Cause**: a plastic material on beam elements.
- **Seen**: derived from the code (`bridge_to_aster`, test run).
- **Solution**: in the bridge: the beam is computed elastically (WARNING and
  `skipped_loads`).
- **Status**: limitation (reported).

### `DISCRETS_26` – discrete element without mass

- **Message** (alarm): mass matrix of a discrete element without `M_*`; the mass is zero.
- **Cause**: springs and POI1 nodes (RBE master) without mass in `AFFE_CARA_ELEM`.
- **Seen**: a mixed test model (RBE, spring).
- **Solution**: in the bridge: every discrete element gets mass 0 (`M_T_D_N` etc.).
- **Status**: fixed in the bridge.

### `DISCRETS_28` – discrete element without damping

- **Message** (alarm): as `DISCRETS_26`, for the damping matrix.
- **Cause**: a discrete element without `A_*` in a dynamic analysis with damping.
- **Seen**: damper test D18_damper (decay 0.7303, theory 0.7301) and F4_model.
- **Solution**: none needed as long as those elements should have no damping.
- **Status**: harmless.

### `ELEMENTS2_63` – THER_NL missing in the material (thermal)

- **Message** (error): "On ne trouve pas le comportement THER_NL dans le matériau fourni."
- **Cause**: `THER_NON_LINE` with a material as `THER`.
- **Seen**: thermal trials.
- **Solution**: in the bridge: with `THER_NON_LINE`, `bridge_thermal.py` writes `THER_NL`.
- **Status**: fixed in the bridge.

### `MODELE1_3`, `MODELE1_14`, `MODELE1_53`, `CHARGES2_4` – thermal shells as PLAN

- **Message** (alarms): `MODELE1_3`: a plane modelling needs a mesh in z = 0;
  `MODELE1_14` / `CHARGES2_4`: 2D and 3D elements mixed; `MODELE1_53`: 2D elements in a
  3D mesh.
- **Cause**: in thermal analyses the bridge computes flat shells as `PLAN` with a
  thickness factor (KNOWN_BUGS 15, [`Thermal.md`](Thermal.md)).
- **Seen**: all thermal models with shells.
- **Solution**: none, as long as the shells lie in parallel planes (the bridge checks
  this and rotates the mesh with `MODI_MAILLAGE ROTATION` if needed). The results are
  correct (against Mecway ≤ 3e-12 K). `MODELE1_53` also appears if the z coordinates are
  not exactly equal (~1e-18): harmless as well.
- **Status**: harmless (deliberate choice).

### `MODELE1_63`, `MODELE1_64` – no stiffness

- **Message** (alarms): `MODELE1_63`: a boundary element borders no element with
  stiffness; `MODELE1_64`: the model has no elements with stiffness.
- **Cause**: trial model with boundary elements only.
- **Seen**: thermal trial job, not in a bridge run.
- **Solution**: check `AFFE_MODELE`.
- **Status**: not seen in the bridge.

---

## 3. Boundary conditions and singular matrix

A singular matrix almost always means: a part can move freely (mechanism), or a degree of
freedom is fixed twice. The code depends on *MUMPS NPREC* (`solver_nprec`; `SOLVEUR NPREC`, EDF R&D, 2021d): at 8
(default in all analyses) you get `FACTOR_10/11/42`. At -1 (check off) a near-mechanism
gives `FACTOR_57`; a completely loose part still gives `FACTOR_42` (MUMPS cannot
factorise). In `STAT_NON_LINE`/`DYNA_NON_LINE` the pivot text
(node and component) appears without a box in the convergence table and the run stops
with `MECANONLINE9_4` (seen 06-10-2026). Code-Aster's own advice is in the catalogue at
`FACTOR_10/11` (EDF R&D, 2026a): a physical degree of freedom points to a poorly
restrained rigid motion, a Lagrange degree of freedom to a redundant condition, often
from contact (`SANS_GROUP_NO`).

### `FACTOR_10` / `FACTOR_11` – (nearly) singular matrix

- **Message** (error): "la matrice est singulière ou presque singulière": (near) zero
  pivot; node and component are shown above the box.
- **Cause**: too few supports; a pinned support (in the bridge it only fixes the average
  displacement); a part held in place only by contact; a shell attached to a solid along
  a single line of nodes (hinge).
- **Seen**: `FACTOR_11` in a mixed test model nonlinear: the plate can
  rotate. `FACTOR_10` was not seen in a saved run; according to the catalogue it has the
  same causes, plus the number of lost decimals.
- **Solution**: in Mecway: enough supports; connect a plate over a face of the solid
  rather than along one line. With `#ASTER` lines: `LIAISON_MAIL
  TYPE_RACCORD='COQUE_MASSIF'` (computed, example 2 in
  [`ASTER_lines_examples.md`](ASTER_lines_examples.md)) or `LIAISON_ELEM
  OPTION='COQ_3D'` (catalogue `affe_char_meca.py`, EDF R&D, 2026b; with `GROUP_MA_COQUE`,
  `GROUP_MA_MASSIF` and `CARA_ELEM`; not computed).
- **Status**: model.

### `FACTOR_42` – MUMPS: matrix singular

- **Message** (error): "La matrice est non factorisable. Elle est détectée comme étant
  singulière".
- **Cause**: (a) duplicated condition: a node of a fixed support is also in a
  frictionless or oblique support; (b) an `#ASTER` load without `#ASTER-EXCIT`: the part
  it should connect is loose.
- **Seen**: (a) inclined plate with frictionless next to a clamp (test PL); (b) example 1
  of `ASTER_lines_examples.md` without `#ASTER-EXCIT`, recomputed on 06-10-2026:
  *Static* (`solver_nprec` -1) `FACTOR_42` with `DIAGNOSTIC JOB : OK`; *Nonlinear static*
  `MECANONLINE9_4`. On 07-10-2026 another model (loose tube beam on a hex20 block) gave
  `FACTOR_57` in *Static* (error bound 9.4, still with `solver_nprec` -1). Since
  08-10-2026 `solver_nprec` is 8 for *Static* too: example 1 (model A) then gives
  `FACTOR_11`. Which code appears depends on the model and NPREC; the explanation and
  the solution are the same.
- **Solution**: in the bridge: nodes of fixed supports are excluded from
  `LIAISON_OBLIQUE`/`FACE_IMPO` and from an imposed displacement, rotation or velocity
  (`SANS_GROUP_*`, commit ef86c7b; see `ASSEMBLA_26`). Other overlaps are reported
  beforehand as a WARNING with the selection names (`_report_constraint_overlaps`,
  KNOWN_BUGS 8): remove the overlap in Mecway. For (b): add `#ASTER-EXCIT name`.
- **Status**: partly fixed in the bridge / model / own input.

### `FACTOR_57` – MUMPS: solution too inaccurate

- **Message** (error): "La solution du système linéaire est trop imprécise: Erreur
  calculée ... Erreur acceptable 1e-06 (RESI_RELA)". Code-Aster advises increasing
  `RESI_RELA`; do not do that, it is almost always a mechanism.
- **Cause**: as `FACTOR_10/11`, but with `solver_nprec` = -1: MUMPS does not look for a
  singularity and the error only shows in the inaccurate solution.
- **Seen**: a mixed test model after the correct translation of pinned support: the
  plate can rotate freely. Mecway solves it, but shows ±499 N "reaction" on nodes without
  support. Also test T1 (plate attached to the block along one line).
- **Solution**: in Mecway: fix the plate further or connect it over a face (see
  `FACTOR_10`). Temporarily setting `solver_nprec` = 8 gives a `FACTOR_10/11` with node
  and component.
- **Status**: model.

### `ASSEMBLA_26` – degree of freedom blocked more than once

- **Message** (error): "le noeud: N composante: DX est bloqué plusieurs fois".
- **Cause**: a node with a fixed support is also in a time-dependent imposed
  displacement, rotation or velocity (`DDL_IMPO` in `AFFE_CHAR_MECA_F`). A constant
  value gave no message, but silently overrode the clamp.
- **Seen**: code review (commit 6ce5cba; comment in `_build_charges`).
- **Solution**: in the bridge: `DDL_IMPO` gets `SANS_GROUP_NO`/`SANS_GROUP_MA` with the
  fixed selections: the clamp wins. (Mecway reduces multiple conditions on a node to a
  minimal set; Mecway, 2026: §9.6.) Two other conditions on the same node are not resolved
  by the bridge (KNOWN_BUGS 8).
- **Status**: fixed in the bridge (fixed) / model (other overlap).

### `FACTOR_13` – problem during factorisation

- **Message** (error): "Problème lors de la factorisation de la matrice."
- **Cause**: not determined; seen in a thermal trial job with `SOUR_NL` on a `PLAN` shell
  (a route the bridge does not use).
- **Seen**: thermal trial job.
- **Solution**: not determined.
- **Status**: cause not determined.

### `MECANONLINE9_4` – matrix not invertible (nonlinear)

- **Message** (error, `<SolverError>`): "Arrêt pour cause de matrice non inversible"; the
  saved steps are kept. Above it, the pivot message per attempt.
- **Cause**:
  1. a contact slave node that is also fully fixed (pivot on `LAGS_C`);
     a bending model: node 15405 in slave `G03ContactProfielToMalUP` and in
     `G09FixYXZ`;
  2. Lagrange contact (*Contact method* = STANDARD) with line contact between quadratic
     solids: pivot on `LAGS_C` of a corner node;
  3. an `#ASTER` load without `#ASTER-EXCIT` (see `FACTOR_42`);
  4. tension only (cable) without compressive stiffness;
  5. format test models F2/F4: cause not determined.
- **Seen**: 1 a bending model (contact); 2 verification NL-03a (two beams, tips touching)
  and Samples/AssemblyWithContact (KNOWN_BUGS 43); 3 recomputed on 06-10-2026; 4 test
  B17; 5 F2_model/F4_model.
- **Solution**: 1 in the bridge: slave nodes in a fixed support are excluded per zone
  with `SANS_GROUP_NO` (`_exclude_fixed_slaves`, commit 7daa249; INFO in the log), as
  the catalogue advises at `FACTOR_10/11`; another condition on slave nodes: remove the
  node from the slave selection in Mecway or use
  `#ASTER-ZONE SANS_GROUP_NO='<<selection>>'` (applies to every zone and replaces the
  automatic one). 2 *Contact method* = PENALISATION with Mecway's *normal stiffness*
  (NL-03b: tip −0.01%, contact force −0.07%). 3 add `#ASTER-EXCIT`. 4 in the bridge:
  `EC_SUR_E` = 1e-4 (default of the catalogue `defi_materiau.py`). 5 not determined.
- **Status**: fixed in the bridge (1 for fixed, 4) / model (1 other, 2) / own input (3) /
  cause not determined (5).

### `CHARGES7_1` – bonding: relation is a tautology

- **Message** (alarm): the relation for a slave node is redundant, because the master
  element contains that node itself.
- **Cause**: bonded contact (`LIAISON_MAIL`) where slave and master faces share nodes.
- **Seen**: bonded test C15; reactions were correct.
- **Solution**: none needed.
- **Status**: harmless.

### `MECANONLINE2_97` – thermal strain in the initial state

- **Message** (alarm): the temperature already gives an inelastic strain in the initial
  state.
- **Cause**: a constant temperature field from t = 0 that differs from the reference
  temperature.
- **Seen**: thermal strain test C14_thermal (displacement 6.0e-5 m, expected 6e-5).
- **Solution**: in the bridge (`_build_temperature_field`): in `STAT_NON_LINE` the
  temperature ramps from the reference (t = 0) to the field at the end time. In
  `DYNA_NON_LINE` the field is constant from t = 0; the alarm remains there
  (KNOWN_BUGS 17).
- **Status**: fixed in the bridge (static) / limitation (dynamic).

### `MECANONLINE_78` – mass matrix nearly singular

- **Message** (alarm): the mass matrix for the initial acceleration is nearly singular;
  the initial acceleration may be too large at some nodes.
- **Cause**: degrees of freedom without mass: a material without density, or rotations
  without rotational inertia.
- **Seen**: D12_rotinertia (maximum angle 0.012611, equal to theory), F4_model, and
  example 1 of `ASTER_lines_examples.md` in *Dynamic (implicit)* (beam without density;
  06-10-2026). The bridge warns beforehand about an elset without density.
- **Solution**: give the material a density in Mecway; otherwise none needed if the
  results are correct.
- **Status**: harmless (in the cases seen) / model (no density).

---

## 4. Contact

Background and settings: [Settings §3](Settings_contact_and_nonlinear.md#3-contact);
`DEFI_CONTACT`: EDF R&D (2021b) and the catalogue `defi_contact.py`. See also
`MECANONLINE9_4` (pivot on `LAGS_C`).

### `CONTACT2_16` – zones share slave nodes

- **Message** (error): "Les zones de contact numéro 1 et numéro 2 ont N noeuds communs à
  leurs surfaces esclaves : c'est interdit."
- **Cause**: in Mecway the same face is slave in several contact pairs. Mecway allows
  that, Code-Aster does not.
- **Seen**: a cutting model (*Dynamic (implicit)*): 48 shared nodes.
- **What did not work**: `SANS_GROUP_NO` (the check is on the faces); swapping master
  and slave (diverged in the first step).
- **Solution**: in the bridge: such pairs become one zone (union of masters and slaves,
  largest friction coefficient; `_merge_contact_zones`, KNOWN_BUGS 10, commit cdc0a74),
  with a WARNING. Different friction per pair: do not let the slave selections overlap.
- **Status**: fixed in the bridge.

### `APPARIEMENT_1` – no node paired

- **Message** (alarm): "Aucun noeud n'est apparié": no slave node finds a master element.
  Code-Aster mentions `CONTACT_INIT='OUI'`, `TOLE_PROJ_EXT` and
  `ALGO_RESO_GEOM='POINT_FIXE'`.
- **Cause**: presumably the faces of a zone were (still) too far apart; NOT checked.
- **Seen**: a variant of a cutting model (dynamic); the run continued.
- **Solution**: check master/slave and the initial gap
  ([Settings §3.2-3.4](Settings_contact_and_nonlinear.md#32-master-and-slave)); extra
  options via `#ASTER-ZONE` / `#ASTER-CONTACT` (examples 5 and 6).
- **Status**: cause not determined (no effect seen).

### `MECANONLINE5_15` – energy not with continuous contact

- **Message** (error): "Le calcul des énergies n'est pas disponible avec le contact en
  formulation continue ou XFEM."
- **Cause**: `ENERGIE=_F()` in `DYNA_NON_LINE` with `FORMULATION='CONTINUE'`.
- **Seen**: trial for the energy balance.
- **Solution**: in the bridge: with contact the bridge leaves out `ENERGIE`, even if
  *Energy balance* is on.
- **Status**: fixed in the bridge (limitation of Code-Aster).

---

## 5. Nonlinear analysis and dynamics

Step-by-step plan and settings:
[Settings §2 and §4](Settings_contact_and_nonlinear.md#4-my-analysis-does-not-converge);
`STAT_NON_LINE`: EDF R&D (2021c) and the catalogue `stat_non_line.py`.

### `MECANONLINE9_7` – Newton does not converge

- **Message** (error, `<ConvergenceError>`): "Arrêt pour cause d'absence de convergence
  avec le nombre d'itérations requis": no convergence within `ITER_GLOB_MAXI`, not even
  after reducing the step (`SUBD_PAS` = 4, `SUBD_NIVEAU` = 6). The saved steps are kept.
- **What the bridge does**: the job catches the error, writes `BRIDGE_ONVOLLEDIG <time>`
  and loads the results up to the last time reached; Mecway shows the explanation
  (`_NEWTON_HINT`).
- **Cause**; read the convergence table in the `.mess` (columns `RESI_GLOB_RELA`,
  `RESI_GLOB_MAXI`, contact):
  1. **Relative residual stalls, absolute residual is ~0.** A bending model (profile, roller and die with contact):
     `RESI_GLOB_RELA` around 0.1 with `RESI_GLOB_MAXI` ~1e-11: an imposed motion without
     resistance, so no reference force: choose `convergence_criterion` = MAXI.
  2. **Stagnation just above the criterion** (e.g. 1.4–2.8e-6 at 1e-6), especially when
     unloading a plastic solid with `GDEF_LOG`; the absolute residual then gets stuck
     (NL-01: ~1e-2 N at 12 kN).
  3. **Cutting through or collapse.** A cutting model (dynamic, contact) stops at t = 0.11 s when the
     profile has been cut through; Code-Aster does not delete elements.
  4. **Steps too large** or a lot of nonlinearity at once (contact, plasticity, large
     deformation).
  5. **Rigid rotation with a GD beam** (`POU_D_T_GD`; see §6).
  6. **No load**: all loads skipped or zero (residual 0 in every iteration,
     `RESI_GLOB_RELA` = -1 in the table).
  7. **Buckling or limit point reached** (load capacity): with an imperfection or
     plasticity the load has a maximum; a load given as a time table cannot go further
     there. With *Stability per step (CRIT_STAB)* the criterion goes to 0
     ([`Modal_and_buckling.md`](Modal_and_buckling.md) §5).
- **Seen**: 1 a bending model (contact); 2 verification NL-01 with the Code-Aster default
  1e-6 (stop at t = 2.92 s); 3 a cutting model;
  4 general; 5 trials for a bending model; 6 a small hex8 test model (force on faces
  not translated, fixed in commit 8e86271) and a test model with a suppressed load
  (06-10-2026). Also with a tension-only cable (test B17, cause not determined).
  7 verification NK-04 (plastic column with imperfection, stop at 0.49 Pcr,
  expected).
- **Solution** (page of the analysis, or per model with `#ASTER-OPTIE`):
  1. *Convergence criterion* = MAXI (`convergence_criterion`; limit *Convergence
     RESI_GLOB_MAXI [N]*, default 1e-3 N). The bridge then writes
     `CONVERGENCE=_F(RESI_GLOB_MAXI=...)` (checked in the `.comm`). The effect was
     established by hand in the `.comm` of a bending model (step 0 → 0.5 s
     converged); the setting itself was not recomputed on that model;
  2. leave *Convergence RESI_GLOB_RELA* (`convergence_resi_rela`) at the default 1e-5
     (the Code-Aster default 1e-6 stalled in NL-01; with 1e-5 NL-01 runs to the end,
     exact). To keep 1e-6: *Convergence criterion* = RELA_OF_MAXI (`RESI_GLOB_RELA` and
     `RESI_GLOB_MAXI` with `VERIF='AU_MOINS_UN'`) with *Convergence RESI_GLOB_MAXI*
     above the absolute residual at which the residual stalls (column `RESI_GLOB_MAXI`
     in the `.mess`): NL-01b (1e-6 and 0.05 N) runs through exactly, with 1e-3 N it
     does not (`TestFiles/Verificatie/resultaten/resultaten.md`;
     [Settings §2.2](Settings_contact_and_nonlinear.md#22-newton-and-convergence));
  3. a failure limit ([`Failure.md`](Failure.md)); otherwise the results up to the
     collapse are loaded;
  4. increase *Substeps per time interval* / *Solver steps per output interval* and
     *Max. Newton iterations*, and switch on the nonlinearities one at a time
     ([Settings §4.2](Settings_contact_and_nonlinear.md#42-step-by-step-plan)); with
     contact *Contact method* = PENALISATION;
  5. not via the bridge;
  6. check the skipped loads in `<model>_<run-id>_bridge_log.txt`;
  7. not an error: the load at the last time is the load capacity. Continuing past
     the limit point is only possible with an imposed displacement instead of a
     force (the arc-length method `PILOTAGE` is not in the bridge).
- **Status**: model / limitation (per case).

### `SUBDIVISE_3` – step cannot be reduced

- **Message** (error): the time step cannot be subdivided because the feature is not
  active; use `DEFI_LIST_INST`.
- **Cause**: `STAT_NON_LINE` with only a `DEFI_LIST_REEL`.
- **Seen**: derived from the catalogue text; not saved as a run error.
- **Solution**: in the bridge: `DEFI_LIST_INST` with
  `ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE', SUBD_PAS=4, SUBD_NIVEAU=6)`
  (commit 57ffead; checked in a `.comm` of 06-10-2026).
- **Status**: fixed in the bridge.

### `DISCRETISATION_87` – time list not strictly increasing

- **Message** (error): "La liste d'instants n'est pas strictement croissante."
- **Cause**: two nearly coinciding times (e.g. 1e-20 s apart) from different load
  histories.
- **Seen**: derived from the code (`_merge_times`; test run).
- **Solution**: in the bridge: nearly duplicate times (difference ≤ 1e-9 × end time) are
  merged.
- **Status**: fixed in the bridge.

### `MECANONLINE5_80` – initial velocity on another model

- **Message** (alarm): the field in `ETAT_INIT` belongs to another model than the
  analysis; Code-Aster fills in zeros.
- **Cause**: not checked (presumably the extra degrees of freedom of contact).
- **Seen**: all dynamic runs with an initial velocity (a cutting model and
  variants); the runs continued. Whether the initial velocity was applied correctly
  everywhere was not checked separately.
- **Solution**: not determined; if in doubt, check the velocity at the first time in
  Mecway.
- **Status**: cause not determined.

### `DYNAMIQUE_4` – stability limit cannot be computed (explicit)

- **Message** (error with `STOP_CFL='OUI'`): the stability condition could not be
  computed for any element.
- **Cause**: an explicit model without elements with a material (springs, dampers and
  nodal masses only).
- **Seen**: derived from the code (`bridge_to_aster`, critical time step; test run with
  spring, damper and nodal mass).
- **Solution**: in the bridge: then `STOP_CFL='NON'` with its own estimate of the stable
  step of the discrete elements (`_discrete_time_step`; INFO in the log). See
  [Settings §2.1](Settings_contact_and_nonlinear.md#21-time-steps).
- **Status**: fixed in the bridge.

### `MECANONLINE5_1` – explicit only PREDICTION TANGENTE

- **Message** (error): with an explicit scheme only `PREDICTION='TANGENTE'` is possible.
- **Cause**: the failure loop used `PREDICTION='ELASTIQUE'` after a failure event.
- **Seen**: derived from the code (`bridge_failure`).
- **Solution**: in the bridge: explicit stays `TANGENTE`.
- **Status**: fixed in the bridge.

### `MECANONLINE9_3` – integration of the material law failed

- **Message** (error, `<IntegrationError>`): the integration of the material law failed;
  the saved steps are kept.
- **Cause**: very large deformation in soft (failed) elements; or setting only
  `SIEF_ELGA` to zero without the internal variables.
- **Seen**: failure trials (`bridge_failure`, [`Failure.md`](Failure.md) §6).
- **Solution**: in the bridge: on failure the internal variables are set to zero as well.
  In the model: smaller steps, or a larger *Stiffness of failed element*.
- **Status**: fixed in the bridge (cause 2) / model (cause 1).

### `MECANONLINE4_50` – initial stress with a multi-step scheme

- **Message** (alarm): an initial stress (`SIGM` in `ETAT_INIT`) with HHT/NEWMARK is
  discouraged: the initial acceleration is computed without that stress.
- **Cause**: the failure loop in *Dynamic (implicit)* restarts after a failure event with
  the stress of the previous step.
- **Seen**: failure trials (`bridge_failure`).
- **Solution**: in the bridge: the acceleration is passed in `ETAT_INIT` as well. Whether
  that prevents the recomputation is NOT verified; check the response for plausibility
  ([`Failure.md`](Failure.md) §6).
- **Status**: harmless (expected; NOT verified).

---

## 6. Large rotations

With *COMPORTEMENT DEFORMATION* for large displacements the bridge chooses the form per
element type (`COMPOR5_22`, `COMPOR1_44/47/99`); beams, imposed rotations (`DDL_IMPO`
DR*) and rigid couplings stay small rotations (KNOWN_BUGS 11). The bridge warns for an
imposed rotation above ~6° (`_warn_large_rotations`). Rotating a rigid part through a
large angle works robustly with an imposed displacement as a `FORMULE` (example 9 of
[`ASTER_lines_examples.md`](ASTER_lines_examples.md), recomputed on 06-10-2026).

### `CHARGES_36` – LIAISON_SOLIDE as a follower load with rotations

- **Message** (error): `LIAISON_SOLIDE` relations become nonlinear with
  `TYPE_CHARGE='SUIV'`; that is not possible if a node has DRX, DRY and DRZ.
- **Cause**: an RBE2 with large rotations and a beam node as master.
- **Seen**: trial with an edited `.comm` for a bending model.
- **Solution**: impose the rigid motion as `DDL_IMPO` with a `FORMULE` on the slave nodes
  (example 9), or a master node without rotational degrees of freedom. Only with your own
  code.
- **Status**: limitation.

Also with large rotations: `COMPOR5_22`, `COMPOR1_44`, `COMPOR1_47`, `COMPOR1_99`,
`DVP_2` (`POU_D_T_GD` with `ELAS`), `CALCUL_37` (`POU_D_T_GD` with
`PREDICTION='ELASTIQUE'`), `MECANONLINE9_7` case 5.

---

## 7. Post-processing

Errors after the solve (`CALC_CHAMP`, `POST_CHAMP`, `POST_RELEVE_T`, `IMPR_RESU`,
export): the solution has been computed, but the commands that follow are skipped.

### `CALCULEL_58` – component missing

- **Message** (error): "Il manque la composante : SIXX sur la maille : 8".
- **Cause**: `CALC_CHAMP` on the result of `POST_CHAMP EXTR_COQUE` without `GROUP_MA`.
- **Seen**: a mixed test model (solid, shell, beam).
- **Solution**: in the bridge: `GROUP_MA` with the shell groups (commit 631cc36).
- **Status**: fixed in the bridge.

### `POSTRELE_40` – node not connected to cell

- **Message** (error): "Le noeud numéro 1 n'est pas connecté à la maille de nom X".
- **Cause**: `POST_RELEVE_T` with a beam group and `GROUP_NO='all_nodes'`.
- **Seen**: a mixed test model (beam stress).
- **Solution**: in the bridge: a node group from the same cells (commit 65f8c7a).
- **Status**: fixed in the bridge.

### `POSTRELE_70` – SIGM_NOEU in the local coordinate system

- **Message** (alarm): with structural elements `SIGM_NOEU` is only meaningful in the
  local coordinate system; `REPERE` is ignored.
- **Cause**: mixed models. In the bridge `SIGM_NOEU` exists only on the 3D elements and
  is in the global system there (`_build_postreleve_block`).
- **Seen**: every mixed model.
- **Solution**: none needed.
- **Status**: harmless.

### `JEVEUX_10` – name already exists

- **Message** (error): "Le nom demandé existe déjà dans la base &&SSCGNO.LITMP2".
- **Cause**: `DEFI_GROUP CREA_GROUP_NO` with several groups in one `_F`.
- **Seen**: model with 6 beam groups.
- **Solution**: in the bridge: one `_F` per group (commit 18f308a).
- **Status**: fixed in the bridge.

### `UTILITAI_3` – fields with sub-points to nodes

- **Message** (alarm): an ELNO field with sub-points (layers of a shell) cannot become a
  NOEU field.
- **Cause**: `SIGM_NOEU` on the whole model, including shells.
- **Seen**: a mixed test model.
- **Solution**: in the bridge: `SIGM_NOEU`/`SIEQ_NOEU` only on 3D groups; shells via
  `POST_CHAMP EXTR_COQUE` per layer.
- **Status**: fixed in the bridge.

### `PREPOST2_57` – sub-points in IMPR_RESU GMSH

- **Message** (error): "nombre de sous-points différent de 1".
- **Cause**: `IMPR_RESU FORMAT='GMSH'` without `NOM_CHAM`.
- **Seen**: early version, mixed model.
- **Solution**: in the bridge: no GMSH export any more (commit a27ddba); with *MED file
  for ParaView* only nodal fields that exist in `res`.
- **Status**: fixed in the bridge.

### `CALCULEL2_15` – EXTR_COQUE without sub-points

- **Message** (error): extraction requested for fields without sub-points.
- **Cause**: `SIGM_ELNO` first only on the solids; the later `CALC_CHAMP` on the shells
  did not complete the field.
- **Seen**: mixed model ME (route `liml`).
- **Solution**: in the bridge: `SIGM_ELNO` once over solids and shells together (commit
  ed7971c).
- **Status**: fixed in the bridge.

### `CALCCHAMP_1` – field already exists

- **Message** (alarm): the field (e.g. `SIGM_ELNO`) is already in the result; nothing is
  recomputed.
- **Cause**: `CALC_CHAMP` asks for a field the bridge already created, e.g. your own
  `#ASTER-POST` code with `SIGM_ELNO`/`SIEQ_ELNO`.
- **Seen**: mixed model ME; the former form of example 8 (06-10-2026).
- **Solution**: none needed; leave out the duplicate `CALC_CHAMP`.
- **Status**: harmless.

### `ELEMENTS4_4`, `ELEMENTS4_64` – SIPM_ELNO not possible

- **Message**: `ELEMENTS4_4`: `SIPM_ELNO` is not possible with `SECTION='GENERALE'`;
  `ELEMENTS4_64` (error): for this option the material may only have `ELAS`.
- **Cause**: beam stress requested for an I/T/C/L or general profile, or for a beam with a
  plastic material.
- **Seen**: derived from the code (`bridge_to_aster`, posigr.F90; test run for
  `ELEMENTS4_64`).
- **Solution**: in the bridge: `SIPM_ELNO` only for `RECTANGLE` and `CERCLE`
  (`_SIPM_SECTIONS`) and only with an elastic material; otherwise an INFO message.
- **Status**: fixed in the bridge.

### `CALCULEL_33` / `RESULT1_39` – different material in CALC_CHAMP (thermal)

- **Message**: `CALCULEL_33` (error): `CALC_CHAMP` with `reuse` and a different
  `CHAM_MATER` is not allowed; `RESULT1_39` (alarm): the given material is used.
- **Cause**: thermal shells compute with a scaled λ; the flux needs the real λ.
- **Seen**: thermal model ConductionConvectionRadiation; also with
  `#ASTER-METALLURGIE` and an own `trc=` (`CALC_META` with its own `CHAM_MATER`,
  verification MT-08; [Welding.md](Welding.md) §10.6).
- **Solution**: in the bridge: the flux in a new result (`res_flux`); the alarm
  `RESULT1_39` is then intended (`bridge_thermal.py`, `bridge_metallurgy.py`).
- **Status**: fixed in the bridge (`CALCULEL_33`) / harmless (`RESULT1_39`).

### `ALGORITH2_12`, `CALCUL_5` – internal thermal post-processing

- **Message** (error): `ALGORITH2_12`: `MODI_REPERE` misses a component; `CALCUL_5`: the
  field does not have the quantity the option expects.
- **Cause**: `FLUZ` on `PLAN` nodes when rotating the flux back; a source field as
  `TEMP_R` instead of `SOUR_R`.
- **Seen**: derived from the code (`bridge_thermal`).
- **Solution**: fixed in the bridge (`FLUZ` only with solid elements; source as
  `NOEU_SOUR_R`).
- **Status**: fixed in the bridge.

### `RUPTURE0_94` – SIEF_ELGA missing for CALC_G

- **Message** (error): "Accès impossible au champ SIEF_ELGA pour le numéro d'ordre : 1
  ... vous calculez l'option 'G'".
- **Cause**: `CALC_G` `OPTION='G'` on a result without `SIEF_ELGA` (e.g. from
  `CREA_RESU`).
- **Seen**: while building the fracture mechanics (step S6a).
- **Solution**: in the bridge: `CALC_CHAMP CONTRAINTE=('SIEF_ELGA',)` before `CALC_G`
  ([Fracture_mechanics.md](Fracture_mechanics.md) §2.1); with own `#ASTER-POST` code:
  the same, or `OPTION='G_EPSI'`.
- **Status**: fixed in the bridge.

### `XFEM_63`, `QUALITY1_1`, `MODELE1_63` – XFEM alarms

- **Message** (alarm): `XFEM_63` "Éléments XFEM quadratiques ... On a effectué un
  ajustement géométrique de la fissure" (number of adjustments); `QUALITY1_1` "La
  fonctionnalité XFEM n'est pas qualifiée pour les études de sûreté"; `MODELE1_63` "La
  maille ... porte un élément fini de bord, mais elle ne borde aucun élément ayant une
  rigidité".
- **Cause**: `XFEM_63`: the level set cuts edges more than once or lies close to nodes
  (quadratic elements, crack plane through nodes) and is shifted slightly;
  `QUALITY1_1`: always with XFEM; `MODELE1_63`: the auxiliary model on the
  `POST_MAIL_XFEM` mesh with `TOUT='OUI'` also got the front cells (SEG2).
- **Seen**: while building XFEM (step S6b; BR-08, BR-09).
- **Solution**: `XFEM_63` and `QUALITY1_1`: harmless (K within 0.2 %, BR-08/BR-09);
  `MODELE1_63`: in the bridge: the auxiliary model only gets the solid element sets
  ([Fracture_mechanics.md](Fracture_mechanics.md) §7.3).
- **Status**: information (`XFEM_63`, `QUALITY1_1`); fixed in the bridge (`MODELE1_63`).

---

## 8. Syntax and `#ASTER` lines

Examples and pitfalls: [`ASTER_lines_examples.md`](ASTER_lines_examples.md). See also
`MODELISA7_75` (unknown selection), `FACTOR_42`/`MECANONLINE9_4` (load without
`#ASTER-EXCIT`) and `CALCCHAMP_1`.

### `SUPERVIS_4` – syntax error in a command

- **Message** (error): "Erreur de syntaxe dans <COMMAND>" with the reason, e.g. "Keyword
  INCREMENT is mandatory". The job stops (`<F>_ABNORMAL_ABORT`).
- **Cause**: a keyword that is missing, does not exist or is not allowed there. Seen:
  `GROUP_MA=` in `POST_RELEVE_T ACTION` (own `#ASTER-POST` code); `THER_LINEAIRE` without
  `INCREMENT`; `AFFE_MATERIAU` without `AFFE` in a model with discrete elements only.
- **Solution**: read the reason in the box; compare with the catalogue
  (`Cata/Commands/<command>.py`).
- **Status**: own input / fixed in the bridge (per case).

### Python error in the `.comm` (no code)

- **Message**: no message box; in `<model>_<run-id>_console.txt` a traceback or
  `SyntaxError`, e.g. `SyntaxError: keyword argument repeated: FROTTEMENT`. The `.mess`
  ends without `<FIN>`, often with `DIAGNOSTIC JOB : OK`.
- **Cause**: a typo in `#ASTER` lines, or a keyword the bridge already writes:
  `FROTTEMENT` via `#ASTER-CONTACT`, or `ALGO_CONT` via `#ASTER-ZONE` while *Contact
  method* = PENALISATION.
- **Seen**: both cases recomputed on 06-10-2026; the bridge reports "Python error in
  `<model>_<run-id>.comm`: SyntaxError: keyword argument repeated: ..." with the error
  line.
- **Solution**: do not repeat anything the bridge already writes
  ([`ASTER_lines_examples.md`](ASTER_lines_examples.md) §4).
- **Status**: own input.

---

## 9. System, solver and follow-on errors

Memory or time limit messages did not occur during testing. The limits are in the
`.export` (*Time limit run_aster [s]*, *Memory limit run_aster [MB]*).

### `JEVEUX_26` – object does not exist

- **Message** (error): "Objet inexistant dans les bases ouvertes: ... .ORDR".
- **Cause**: follow-on error: an earlier command failed (e.g. `COMPOR5_22`,
  `MECANONLINE_3`, `MECANONLINE5_15`, `CALCULEL2_15`, `CALCUL_37`), so the result does
  not exist.
- **Seen**: always together with one of those errors.
- **Solution**: fix the first error in the `.mess`.
- **Status**: follow-on error.

### `CATAMESS_6` – stop after an `<E>` message

- **Message** (error): "Fin à la suite de message(s) <E>".
- **Cause**: after an `<E>` message Code-Aster stops at the next command; a `try/except`
  in the `.comm` cannot catch that.
- **Seen**: mode check of `CALC_MODES` (verification, `Verification.md`).
- **Solution**: in the bridge: `VERI_MODE STOP_ERREUR='NON'`: the checks become alarms
  (§10).
- **Status**: fixed in the bridge.

### `FERMETUR_10` – PETSc not installed

- **Message** (error): the PETSc solver is not in this version.
- **Cause**: `METHODE='PETSC'`; the Windows version is sequential.
- **Seen**: test run (comment in `bridge_to_aster`).
- **Solution**: in the bridge: only MUMPS and GCPC (*Linear solver*).
- **Status**: limitation (not offered).

### `ALGELINE4_3` – GCPC does not converge

- **Message** (error): the iterative solver GCPC does not reach the criterion within the
  allowed number of iterations.
- **Cause**: *Linear solver* = GCPC with an ill-conditioned model (e.g. slender beams made
  of solid elements).
- **Seen**: NOT in a saved run; mentioned in
  [Settings §2.6](Settings_contact_and_nonlinear.md#26-linear-solver-solver_nprec-lin_solver-lin_solver_resi).
- **Solution**: *Linear solver* = MUMPS.
- **Status**: model / setting.

### `CATAMESS_41` – alarm no longer shown

- **Message** (alarm): alarm X has been issued 5 times and is no longer shown.
- **Status**: information; look at alarm X.

### `CATAMESS_89` – list of alarms

- **Message** (`<I>`): at the end of the `.mess`, all alarms with their count.
- **Status**: information.

### No code: crash, aborted job or logging error

- `Windows fatal exception: access violation` (`<F>_ABNORMAL_ABORT`, no box): seen with
  `DEFI_GROUP reuse=mesh` after the solve; fixed in the bridge by creating all groups
  before `AFFE_MODELE`. The traceback is only shown in the Code-Aster window.
- `Exception: Trying to close the database after an uncaught exception...`: an error in a
  command; the message above it is the cause. Seen after `FACTOR_42` (06-10-2026).
- `--- Logging error ---` with a traceback in the console output: a log line could not be
  written to a console (job without a window); the job continues. The bridge ignores this
  traceback (`bridge_convergence.python_errors`).
- No `<FIN>` in the `.mess`: the `.comm` was not executed to the end; see
  [§8](#python-error-in-the-comm-no-code).

---

## 10. Modal and buckling

`CALC_MODES` in *Modal* and *Buckling* (`bridge_to_aster._calc_modes_block`; background in
[`Modal_and_buckling.md`](Modal_and_buckling.md)). The mode check (`VERI_MODE`) is set to
`STOP_ERREUR='NON'`, so a failed check gives an alarm instead of a stop.

### `ALGELINE3_81` – search frequency coincides with an eigenvalue

- **Message** (error): the shift for the dynamic matrix coincides with an eigenvalue;
  despite shifting, the matrix remains singular.
- **Cause**: a mechanism or rigid motion in a model with supports (beam only pinned, loose
  part). Also: a connection made with `#ASTER` code (`LIAISON_ELEM`, `LIAISON_MAIL`, ...)
  whose load is not in `#ASTER-EXCIT`. With `#ASTER-EXCIT` the bridge also puts the load
  in `CHARGE` of `ASSEMBLAGE`, so the connection counts in the matrices of *Modal* and
  *Buckling* (see [`ASTER_lines_examples.md`](ASTER_lines_examples.md) §2).
- **Seen**: beam supported by hinges only (KNOWN_BUGS 48); example 1 of
  `ASTER_lines_examples.md` in *Modal* and *Buckling* when `#ASTER-EXCIT` did not yet go
  into the matrices (06-10-2026: the beam was loose). With the load in the matrices,
  example 1 runs through (*Modal* f1 = f2 = 841.8 Hz with the test model of that time;
  with model A from `TestFiles/Voorbeelden/` 2855.4 Hz).
- **Solution**: support the model better (connections from `#ASTER` code via
  `#ASTER-EXCIT`), or choose a negative *Search frequency [Hz]* (e.g. -10 × the expected
  first frequency); the rigid modes then appear with ~0 Hz. Checked on 06-10-2026
  (loose beam): with -1000 Hz six modes of ~1e-3 Hz and then 841.8 Hz. That only helps
  if the loose part has mass (density or point mass): the same model without density
  gave `ALGELINE3_81` again. The explanation in the log says this too.
- **Acoustics** (cavity modes, [`Acoustics.md`](Acoustics.md)): a volume with hard walls
  and no pressure node has a constant pressure mode (0 Hz); with `PLUS_PETITE` this gave
  `ALGELINE3_81` (seen, 07-10-2026). The bridge then searches around a small negative
  frequency itself. If the message remains (a separate part of the volume without a
  pressure node while there are pressure nodes elsewhere): choose a negative search
  frequency on the page *Acoustics (cavity modes)*.
- **Status**: model.

### `ALGELINE3_82` – band limit is an eigenvalue

- **Message** (alarm): the lower limit of the search interval (the Sturm band) (nearly)
  coincides with an eigenvalue; the Sturm count may be wrong.
- **Cause**: usually a rigid mode at ~0 Hz, with a negative search frequency.
- **Seen**: run with *Search frequency* -1000 Hz (06-10-2026) and a free-free model with
  a negative search frequency; the Sturm check then did count the correct number of
  modes. Also with acoustic cavity modes with hard walls (the 0 Hz constant pressure
  mode; verification AK-01 and AK-05, 07-10-2026): frequencies exact.
- **What the bridge does**: WARNING in the log with an explanation (`_ALARM_HINTS`).
- **Solution**: usually none needed. Check the number of rigid modes (six per free
  part), or shift the search frequency slightly.
- **Status**: harmless (in the cases seen).

### `ALGELINE5_49`, `ALGELINE3_78` – too few modes found

- **Message**: `ALGELINE5_49` (alarm): fewer modes computed than requested;
  `ALGELINE3_78` (error): no eigenvalue at the required accuracy.
- **Cause**: a search frequency far from the modes.
- **Seen**: hex20 beam with a shift far above the first mode (KNOWN_BUGS 48,
  `Verification.md`).
- **Solution**: a search frequency closer to the expected frequencies (0 = the lowest),
  or fewer modes.
- **Status**: model / setting.

### `ALGELINE5_23`, `ALGELINE2_74`, `ALGELINE5_15` – mode check

- **Message** (alarms, due to `STOP_ERREUR='NON'`): `ALGELINE5_23`: the Sturm check counts
  more eigenvalues than computed; `ALGELINE2_74`: the mode check failed; `ALGELINE5_15`:
  the error norm of a mode exceeds the limit.
- **Cause**: `5_23` usually a multiple mode (symmetry) on the limit of the number of
  modes, otherwise a missed mode; `5_15` a coarse or ill-conditioned model.
- **Seen**: BucklingBeam with a square section (`5_23`; `Verification.md`).
- **Solution**: `5_23`: ask for one or two more modes and compare; `5_15`: finer mesh or a
  larger *Mode check (VERI_MODE SEUIL)* (e.g. 1e-4). The bridge logs `5_23` and `2_74` as
  a WARNING with an explanation.
- **Status**: model / harmless (per case).

### `ALGELINE4_77`, `UTILITAI3_5` – normalisation and mode parameters

- **Message** (error): `ALGELINE4_77`: the normalisation is not implemented;
  `UTILITAI3_5`: the parameter does not exist.
- **Cause**: `NORM_MODE='RIGI_GENE'` with `MODE_FLAMB`; asking for a parameter such as
  `MASS_EFFE_UN_DRX`.
- **Seen**: while building modal and buckling (`Verification.md`).
- **Solution**: in the bridge: buckling modes are normalised by the bridge itself
  (phi^T K phi = 1, `aster_results_export.py`); only existing parameters are read.
- **Status**: fixed in the bridge.

### `ALGORITH16_52`, `ALGORITH16_58`, `ALGORITH14_94`, `ALGORITH14_95` – cyclic symmetry

- **Message** (error, `MODE_ITER_CYCL`): `ALGORITH16_52` "axe de symétrie cyclique
  différent de Oz" (a node pair is not a rotation about the Z axis); `ALGORITH16_58`
  "arrêt sur problème répétitivité cyclique" (with diagnosis "INVERSION INTERFACE
  DROITE/GAUCHE" or none); `ALGORITH14_94`/`_95` "erreur de répétitivité cyclique" /
  "il manque un ddl sur un noeud axe".
- **Cause**: cut faces that do not repeat about the Z axis; DROITE and GAUCHE swapped;
  noise around 0 in the axial coordinate (Code-Aster compares relatively); 8 segments
  with nodes on the axis (`ctetax.F90`: cos 45° − sin 45° = 0).
- **Seen**: while building S10g (ring sector, Mecway's Impeller with y = 1.9e-20 /
  6.0e-20 m, plate with 8 segments; `Verification.md` CY).
- **Solution**: in the bridge: the pairs are found and ordered by the bridge, GAUCHE is
  the side at +360°/N, coordinates < 1e-12 × the model size become 0, with an X/Y axis
  an exact permutation of the coordinates; 8 segments with nodes on the axis give an
  ERROR. In Mecway: a small hole on the axis. If `ALGORITH16_52` still occurs: report
  the model.
- **Status**: fixed in the bridge (noise, direction) / limitation (8 segments with
  nodes on the axis, KNOWN_BUGS 61).

---

## 11. Error estimator

`CALC_ERREUR` (residual estimator `ERME`) in *Static* with the setting
`error_estimator` (`bridge_to_aster._error_estimator_block`; background in
[`Error_estimator.md`](Error_estimator.md)). The bridge builds the estimator so that
none of these messages occur (own model, own load, own result); they only appear with
a `CALC_ERREUR` of your own in `#ASTER-POST` code. All seen with Code-Aster 17.4 while
building the error estimator (beam hex8 20x2x2, also with a point load, two pressures
and beams in the model).

### `INDICATEUR_2`, `CALCUL_29` – stresses not on the whole model

- **Message** (alarm, then error): "Le champ de contraintes n'a pas été calculé sur
  tout le modèle. On ne peut pas calculer l'option ERME_ELEM"; then `<EXCEPTION>
  CALCUL_29` (parameter `PERREUR` missing for `ERME_ELNO`).
- **Cause**: `SIGM_ELNO` only on part of the model (`GROUP_MA`), while the model also
  has skin elements (pressure faces) or other elements. A second `CALC_CHAMP` on the
  whole model does not complete the field (alarm `CALCCHAMP_1`).
- **Solution**: in the bridge: `SIGM_ELNO` without `GROUP_MA` on a separate model with
  only the solid elements and their faces.
- **Status**: fixed in the bridge.

### `INDICATEUR_6`, `INDICATEUR_7`, `INDICATEUR_8` – loads the estimator cannot handle

- **Message**: `INDICATEUR_6` (alarm) "ne sait pas traiter les charges du type de
  <load>" with `FORCE_NODALE`; `INDICATEUR_7` (alarm) "Le choix PRESS apparaît au
  moins dans 2 charges" with two loads with `PRES_REP`; then `<EXCEPTION>
  INDICATEUR_8` ("Problème sur les charges").
- **Cause**: the estimator accepts only one load per load type and no point loads. The
  bridge makes every load its own `AFFE_CHAR_MECA`.
- **Solution**: in the bridge: a separate load `load_err` with all loads the estimator
  knows together (`PRES_REP`, `FORCE_FACE`, `PESANTEUR`, `ROTATION`), through `EXCIT`
  of `CALC_ERREUR`; point loads are left out (INFO).
- **Status**: fixed in the bridge.

### `CALCULEL_39`, `RESULT1_40`, `RESULT1_65` – other loads than in the result

- **Message**: `<EXCEPTION> CALCULEL_39` "Le chargement (mot clé: EXCIT) fourni par
  l'utilisateur est différent de celui présent dans la structure de données Résultat.
  Dans ce cas, le reuse est interdit"; without `reuse` the alarms `RESULT1_65` ("Vous
  avez fourni 1 charges alors qu'il n'y a 2 ...") and `RESULT1_40` ("On poursuit les
  calculs avec le chargement fourni par l'utilisateur").
- **Cause**: `CALC_ERREUR` with an `EXCIT` that differs from the loads of the solution.
  Without `reuse`, `ERME_ELEM` goes into the new result, but `ERME_ELNO`/`ERME_NOEU`
  look for their source field in the old one (`UTILITAI8_13`, `CALCUL_29`,
  `CALCUL_17`).
- **Solution**: in the bridge: a separate result (`CREA_RESU` with the displacements),
  then `SIGM_ELNO` and `CALC_ERREUR` with `reuse` and `EXCIT`: no alarm.
- **Status**: fixed in the bridge.

### `CALCUL_37` (`INIT_MAIL_VOIS`) – beam in the estimator's model

- **Message** (error): "Le TYPE_ELEMENT MECA_POU_D_E ne sait pas encore calculer
  l'option: INIT_MAIL_VOIS".
- **Cause**: `CALC_ERREUR` on a model with beams (the estimator looks for the
  neighbours of each element); `CALC_ERREUR` has no `GROUP_MA`.
- **Solution**: in the bridge: the estimator's model has only the solid elements and
  their faces.
- **Status**: fixed in the bridge.

---

## Codes in alphabetical order

| Code | Topic | Status |
|---|---|---|
| `ALGELINE2_74` | [10](#algeline5_23-algeline2_74-algeline5_15--mode-check) | model / harmless (per case) |
| `ALGELINE3_78` | [10](#algeline5_49-algeline3_78--too-few-modes-found) | model / setting |
| `ALGELINE3_81` | [10](#algeline3_81--search-frequency-coincides-with-an-eigenvalue) | model |
| `ALGELINE3_82` | [10](#algeline3_82--band-limit-is-an-eigenvalue) | harmless (in the cases seen) |
| `ALGELINE4_3` | [9](#algeline4_3--gcpc-does-not-converge) | model / setting |
| `ALGELINE4_77` | [10](#algeline4_77-utilitai3_5--normalisation-and-mode-parameters) | fixed in the bridge |
| `ALGELINE5_15` | [10](#algeline5_23-algeline2_74-algeline5_15--mode-check) | model / harmless (per case) |
| `ALGELINE5_23` | [10](#algeline5_23-algeline2_74-algeline5_15--mode-check) | model / harmless (per case) |
| `ALGELINE5_49` | [10](#algeline5_49-algeline3_78--too-few-modes-found) | model / setting |
| `ALGORITH14_95` | [10](#algorith16_52-algorith16_58-algorith14_94-algorith14_95--cyclic-symmetry) | limitation (8 segments with nodes on the axis) |
| `ALGORITH16_52` | [10](#algorith16_52-algorith16_58-algorith14_94-algorith14_95--cyclic-symmetry) | fixed in the bridge |
| `ALGORITH16_58` | [10](#algorith16_52-algorith16_58-algorith14_94-algorith14_95--cyclic-symmetry) | fixed in the bridge |
| `ALGORITH2_12` | [7](#algorith2_12-calcul_5--internal-thermal-post-processing) | fixed in the bridge |
| `APPARIEMENT_1` | [4](#appariement_1--no-node-paired) | cause not determined (no effect seen) |
| `ASSEMBLA_26` | [3](#assembla_26--degree-of-freedom-blocked-more-than-once) | fixed in the bridge (fixed) / model (other overlap) |
| `CALCCHAMP_1` | [7](#calcchamp_1--field-already-exists) | harmless |
| `CALCULEL2_15` | [7](#calculel2_15--extr_coque-without-sub-points) | fixed in the bridge |
| `CALCULEL2_92` | [2](#calculel2_92--more-than-one-distributed-load-on-a-beam) | fixed in the bridge, except for the cases named |
| `CALCULEL_33` | [7](#calculel_33--result1_39--different-material-in-calc_champ-thermal) | fixed in the bridge (`CALCULEL_33`) / harmless (`RESULT1_39`) |
| `CALCULEL_39` | [11](#calculel_39-result1_40-result1_65--other-loads-than-in-the-result) | fixed in the bridge |
| `CALCULEL_54` | [2](#mecanonline_3-with-alarm-calculel_54--element-not-for-nonlinear-analysis) | fixed in the bridge |
| `CALCULEL_58` | [7](#calculel_58--component-missing) | fixed in the bridge |
| `CALCUL_20` | [2](#calcul_20--material-missing) | fixed in the bridge (as a message) |
| `CALCUL_29` | [11](#indicateur_2-calcul_29--stresses-not-on-the-whole-model) | fixed in the bridge |
| `CALCUL_37` | [2](#calcul_37--element-cannot-compute-this-option) | fixed in the bridge (1, 3; 5 as a message) / own input (2) / cause not determined (4) |
| `CALCUL_37` (`INIT_MAIL_VOIS`) | [11](#calcul_37-init_mail_vois--beam-in-the-estimators-model) | fixed in the bridge |
| `CALCUL_42` | [2](#calcul_42--option-not-yet-programmed-follower-pressure-on-dkt) | fixed in the bridge (as a message) |
| `CALCUL_5` | [7](#algorith2_12-calcul_5--internal-thermal-post-processing) | fixed in the bridge |
| `CATAMESS_41` | [9](#catamess_41--alarm-no-longer-shown) | information; look at alarm X |
| `CATAMESS_6` | [9](#catamess_6--stop-after-an-e-message) | fixed in the bridge |
| `CATAMESS_89` | [9](#catamess_89--list-of-alarms) | information |
| `CHARGES2_31` | [2](#charges2_31--degree-of-freedom-does-not-exist-on-the-node) | fixed in the bridge |
| `CHARGES2_4` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermal-shells-as-plan) | harmless (deliberate choice) |
| `CHARGES2_89` | [2](#charges2_89--no-cell-of-the-right-type) | fixed in the bridge (as a message) |
| `CHARGES7_1` | [3](#charges7_1--bonding-relation-is-a-tautology) | harmless |
| `CHARGES_36` | [6](#charges_36--liaison_solide-as-a-follower-load-with-rotations) | limitation |
| `COMPOR1_44` | [2](#compor1_44-compor1_99--strain-measure-does-not-suit-the-law-or-element) | fixed in the bridge |
| `COMPOR1_47` | [2](#compor1_47--coque_3d-with-grot_gdep-rotations-below-2π) | harmless |
| `COMPOR1_99` | [2](#compor1_44-compor1_99--strain-measure-does-not-suit-the-law-or-element) | fixed in the bridge |
| `COMPOR5_22` | [2](#compor5_22--grot_gdep-not-on-solid-elements) | fixed in the bridge |
| `CONTACT2_16` | [4](#contact2_16--zones-share-slave-nodes) | fixed in the bridge |
| `DISCRETISATION_87` | [5](#discretisation_87--time-list-not-strictly-increasing) | fixed in the bridge |
| `DISCRETS_26` | [2](#discrets_26--discrete-element-without-mass) | fixed in the bridge |
| `DISCRETS_28` | [2](#discrets_28--discrete-element-without-damping) | harmless |
| `DVP_2` | [2](#dvp_2--floating-point-exception) | fixed in the bridge (a) / own input (b) |
| `DYNAMIQUE_4` | [5](#dynamique_4--stability-limit-cannot-be-computed-explicit) | fixed in the bridge |
| `ELEMENTS2_63` | [2](#elements2_63--ther_nl-missing-in-the-material-thermal) | fixed in the bridge |
| `ELEMENTS4_4` | [7](#elements4_4-elements4_64--sipm_elno-not-possible) | fixed in the bridge |
| `ELEMENTS4_64` | [7](#elements4_4-elements4_64--sipm_elno-not-possible) | fixed in the bridge |
| `ELEMENTS4_92` | [2](#elements4_92--pressure-as-a-function-on-a-shell) | fixed in the bridge |
| `FACTOR_10` | [3](#factor_10--factor_11--nearly-singular-matrix) | model |
| `FACTOR_11` | [3](#factor_10--factor_11--nearly-singular-matrix) | model |
| `FACTOR_13` | [3](#factor_13--problem-during-factorisation) | cause not determined |
| `FACTOR_42` | [3](#factor_42--mumps-matrix-singular) | partly fixed in the bridge / model / own input |
| `FACTOR_57` | [3](#factor_57--mumps-solution-too-inaccurate) | model |
| `FERMETUR_10` | [9](#fermetur_10--petsc-not-installed) | limitation (not offered) |
| `INDICATEUR_2` | [11](#indicateur_2-calcul_29--stresses-not-on-the-whole-model) | fixed in the bridge |
| `INDICATEUR_6` | [11](#indicateur_6-indicateur_7-indicateur_8--loads-the-estimator-cannot-handle) | fixed in the bridge |
| `INDICATEUR_7` | [11](#indicateur_6-indicateur_7-indicateur_8--loads-the-estimator-cannot-handle) | fixed in the bridge |
| `INDICATEUR_8` | [11](#indicateur_6-indicateur_7-indicateur_8--loads-the-estimator-cannot-handle) | fixed in the bridge |
| `JEVEUX_10` | [7](#jeveux_10--name-already-exists) | fixed in the bridge |
| `JEVEUX_26` | [9](#jeveux_26--object-does-not-exist) | follow-on error |
| `MECANONLINE2_97` | [3](#mecanonline2_97--thermal-strain-in-the-initial-state) | fixed in the bridge (static) / limitation (dynamic) |
| `MECANONLINE4_50` | [5](#mecanonline4_50--initial-stress-with-a-multi-step-scheme) | harmless (expected; NOT verified) |
| `MECANONLINE5_1` | [5](#mecanonline5_1--explicit-only-prediction-tangente) | fixed in the bridge |
| `MECANONLINE5_15` | [4](#mecanonline5_15--energy-not-with-continuous-contact) | fixed in the bridge (limitation of Code-Aster) |
| `MECANONLINE5_80` | [5](#mecanonline5_80--initial-velocity-on-another-model) | cause not determined |
| `MECANONLINE9_3` | [5](#mecanonline9_3--integration-of-the-material-law-failed) | fixed in the bridge (cause 2) / model (cause 1) |
| `MECANONLINE9_4` | [3](#mecanonline9_4--matrix-not-invertible-nonlinear) | fixed in the bridge (1 for fixed, 4) / model (1 other, 2) / own input (3) / cause not determined (5) |
| `MECANONLINE9_7` | [5](#mecanonline9_7--newton-does-not-converge) | model / limitation (per case) |
| `MECANONLINE_3` | [2](#mecanonline_3-with-alarm-calculel_54--element-not-for-nonlinear-analysis) | fixed in the bridge |
| `MECANONLINE_78` | [3](#mecanonline_78--mass-matrix-nearly-singular) | harmless (in the cases seen) / model (no density) |
| `MESH1_4` | [1](#mesh1_4--line_quad-on-part-of-the-mesh) | harmless |
| `MODELE1_14` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermal-shells-as-plan) | harmless (deliberate choice) |
| `MODELE1_3` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermal-shells-as-plan) | harmless (deliberate choice) |
| `MODELE1_53` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermal-shells-as-plan) | harmless (deliberate choice) |
| `MODELE1_63` | [2](#modele1_63-modele1_64--no-stiffness) | not seen in the bridge |
| `MODELE1_64` | [2](#modele1_63-modele1_64--no-stiffness) | not seen in the bridge |
| `MODELE1_7` | [2](#modele1_7--3d_si-only-for-parallelepipeds) | harmless (deliberate choice); watch the stresses |
| `MODELISA4_50` | [2](#modelisa4_50--modelisa4_51--cell-without-element) | fixed in the bridge |
| `MODELISA4_51` | [2](#modelisa4_50--modelisa4_51--cell-without-element) | fixed in the bridge |
| `MODELISA4_6` | [1](#modelisa4_6--modelisa8_11--orphan-nodes) | harmless (usually) |
| `MODELISA4_8` | [1](#modelisa4_8--modelisa8_13--duplicate-elements) | fixed in the bridge (a) / harmless (b) |
| `MODELISA4_80` | [1](#modelisa4_80--group-empty) | fixed in the bridge |
| `MODELISA5_7` | [1](#modelisa5_7--cell-does-not-exist) | fixed in the bridge |
| `MODELISA5_8` | [1](#modelisa5_8--cell-twice-in-a-group) | fixed in the bridge |
| `MODELISA6_10` | [1](#modelisa6_10--cell-not-in-the-mesh) | fixed in the bridge |
| `MODELISA6_96` | [2](#modelisa6_96--projection4_55--liaison_mail) | fixed in the bridge |
| `MODELISA7_66` | [1](#modelisa7_66--item-expected-at-the-start-of-the-line) | fixed in the bridge |
| `MODELISA7_75` | [1](#modelisa7_75-modelisa7_77--group-does-not-exist) | own input (a) / fixed in the bridge (b) |
| `MODELISA7_77` | [1](#modelisa7_75-modelisa7_77--group-does-not-exist) | own input (a) / fixed in the bridge (b) |
| `MODELISA7_81` | [1](#modelisa7_81--not-a-valid-name) | fixed in the bridge |
| `MODELISA7_82` | [1](#modelisa7_82--internal-error-with-a-long-group-name) | fixed in the bridge |
| `MODELISA7_85` | [1](#modelisa7_85--number-expected-in-the-mesh) | fixed in the bridge |
| `MODELISA8_11` | [1](#modelisa4_6--modelisa8_11--orphan-nodes) | harmless (usually) |
| `MODELISA8_13` | [1](#modelisa4_8--modelisa8_13--duplicate-elements) | fixed in the bridge (a) / harmless (b) |
| `MODELISA8_14` | [1](#modelisa8_14--poi1-inside-another-element) | harmless |
| `MODELISA_1` | [1](#modelisa_1--mesh-cannot-be-read) | fixed in the bridge (through the causes above) |
| `MODELISA_78` | [2](#modelisa_78--shear-coefficient-missing-beam) | fixed in the bridge |
| `PLATE1_40` | [2](#plate1_40--shell-cannot-be-oriented) | fixed in the bridge (except the box case) |
| `POSTRELE_40` | [7](#postrele_40--node-not-connected-to-cell) | fixed in the bridge |
| `POSTRELE_70` | [7](#postrele_70--sigm_noeu-in-the-local-coordinate-system) | harmless |
| `POUTRE0_61` | [2](#poutre0_61--plasticity-on-a-classical-beam) | limitation (reported) |
| `PREPOST2_57` | [7](#prepost2_57--sub-points-in-impr_resu-gmsh) | fixed in the bridge |
| `PROJECTION4_55` | [2](#modelisa6_96--projection4_55--liaison_mail) | fixed in the bridge |
| `RESULT1_39` | [7](#calculel_33--result1_39--different-material-in-calc_champ-thermal) | fixed in the bridge (`CALCULEL_33`) / harmless (`RESULT1_39`) |
| `RESULT1_40` | [11](#calculel_39-result1_40-result1_65--other-loads-than-in-the-result) | fixed in the bridge |
| `RESULT1_65` | [11](#calculel_39-result1_40-result1_65--other-loads-than-in-the-result) | fixed in the bridge |
| `SOUSTRUC_37` | [1](#soustruc_37-soustruc_38--node-group-already-exists--is-empty) | fixed in the bridge |
| `SOUSTRUC_38` | [1](#soustruc_37-soustruc_38--node-group-already-exists--is-empty) | fixed in the bridge |
| `SUBDIVISE_3` | [5](#subdivise_3--step-cannot-be-reduced) | fixed in the bridge |
| `RUPTURE0_94` | [7](#rupture0_94--sief_elga-missing-for-calc_g) | fixed in the bridge |
| `XFEM_63`, `QUALITY1_1`, `MODELE1_63` | [7](#xfem_63-quality1_1-modele1_63--xfem-alarms) | information / fixed in the bridge |
| `SUPERVIS_4` | [8](#supervis_4--syntax-error-in-a-command) | own input / fixed in the bridge (per case) |
| `UTILITAI3_5` | [10](#algeline4_77-utilitai3_5--normalisation-and-mode-parameters) | fixed in the bridge |
| `UTILITAI5_1` | [1](#utilitai5_1--file-for-a-unit-missing) | cause in the test setup, not in the bridge |
| `UTILITAI_3` | [7](#utilitai_3--fields-with-sub-points-to-nodes) | fixed in the bridge |

---

## Assumptions

- The message texts and their numbers apply to Code-Aster 17.4.0; in another version the
  number or text may differ.
- A message "derived from the code" has not been reproduced again with this version of
  the bridge; the bridge avoids it based on an earlier run.
- "Harmless" means: in the cases seen the results agreed with a reference; it is no
  guarantee for every model.

## References

- EDF R&D (2026a). *code_aster 17.4.0, message catalogue*. Installation
  `code_aster/v2025/17.4/lib/aster/code_aster/Messages/<module>.py` (e.g. `factor.py`,
  `mecanonline9.py`, `algeline3.py`).
- EDF R&D (2026b). *code_aster 17.4.0, command catalogue*. Installation
  `code_aster/v2025/17.4/lib/aster/code_aster/Cata/Commands/<command>.py` (e.g.
  `affe_char_meca.py`, `defi_contact.py`, `defi_materiau.py`, `dyna_non_line.py`).
- EDF R&D (2026c). *code_aster 17.4.0, test cases* ssnl103a. Installation
  `code_aster/v2025/17.4/share/aster/tests/`.
- EDF R&D (2021a). *Opérateur AFFE_CHAR_MECA*. Code_Aster documentation U4.44.01. Local
  PDF in `Code_Aster_documentation/important documents/` (created 17-12-2021; older than
  17.4).
- EDF R&D (2021b). *Opérateur DEFI_CONTACT*. Code_Aster documentation U4.44.11. Local PDF
  (created 18-12-2021; older than 17.4).
- EDF R&D (2021c). *Opérateur STAT_NON_LINE*. Code_Aster documentation U4.51.03. Local
  PDF (created 17-12-2021; older than 17.4).
- EDF R&D (2021d). *Mot-clé SOLVEUR*. Code_Aster documentation U4.50.01. Local PDF
  (created 17-12-2021; older than 17.4).
- Mecway (2026). *Mecway Finite Element Analysis – Manual*, version 33.
  `C:\Program Files\Mecway\manual.pdf`.
- MecwayAsterBridge. `KNOWN_BUGS.md`, `docs/en/Verification.md` and
  `TestFiles/Verificatie/resultaten/resultaten.md` (verification results).
