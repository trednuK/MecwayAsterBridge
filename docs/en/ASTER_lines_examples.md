# `#ASTER` lines: your own Code-Aster input from Mecway

*Nederlandse versie: [ASTER_regels_voorbeelden.md](../ASTER_regels_voorbeelden.md)*

With `#ASTER` lines you put Code-Aster commands into the model for things Mecway has no
input for (e.g. a beam attached to a solid face, a shell on a solid, contact settings,
extra post-processing). The bridge reads them from the `.liml`
(`Scripts/bridge_custom.py`) and places them at a fixed position in the `.comm` of the
run (`<model>_<run-id>.comm`, see [User guide §5](UserGuide.md#5-files-in-the-working-directory);
below, `.comm` and `.mess` for short). The bridge does not check the Code-Aster syntax:
errors come from Code-Aster ([`CodeAster_error_messages.md`](CodeAster_error_messages.md)).

All examples in §5 were generated with the current bridge on 06-10-2026 and solved with
Code-Aster 17.4.0; the `.comm` excerpts and results come from those runs (examples 1 to
8 again on 07-10-2026, in the models of `TestFiles/Voorbeelden/`). Overview:
[§6](#6-overview-of-the-checks).

## 1. Where to type the lines

In a free text field of one of the Mecway solvers. In *Analysis settings*, set the solver
to that solver; a branch with the field then appears in the outline tree (Mecway, 2026:
§13.2-13.3, §14.2.8, §15.1.5). Mecway also passes the text to that solver; that is why
the line starts with that solver's comment character:

| Mecway field (XML tag in the `.liml`) | Prefix |
|---|---|
| CCX > Custom model definition (`ccxmodeldefinition`) | `**ASTER` |
| CCX > Custom step contents (`ccxstep`) | `**ASTER` |
| OpenRadioss > Custom model definition (`radiossmodeldefinition`) | `#ASTER` |
| OpenRadioss > Custom engine input (`radiossengineinput`) | `#ASTER` |
| Mystran > Custom bulk data (`nastranbulkdata`) | `$ASTER` |

- The bridge reads all five fields, whichever solver is selected. In practice: statics in
  a Mystran analysis (`$ASTER`), nonlinear/contact/dynamics in an OpenRadioss or CCX
  analysis.
- After the prefix the syntax is the same everywhere. Below, `#ASTER` is always used; in
  the Mystran field you write `$ASTER`, in a CCX field `**ASTER`. Spaces between the
  prefix and `ASTER` are allowed (`$ ASTER`, `** ASTER`).
- Other lines in the field (normal solver input, comments such as `$ text` or
  `** text`) are skipped by the bridge. A line that looks like an `#ASTER` line but does
  not fit (e.g. `#ASTER_EXCIT`) gives an ERROR in the log and is skipped.
- Order in the `.comm`: the fields in the order of the table above, within a field from
  top to bottom.

## 2. Kinds of lines

| Line | What the bridge does with it |
|---|---|
| `#ASTER <code>` | Code-Aster code, literally after the bridge's loads (`load_1`, ...) and before the solve (see the table below). The single space after `#ASTER` is dropped, the rest of the line is kept. |
| `#ASTER-EXCIT name, name2` | Puts `_F(CHARGE=name)` in `EXCIT` of the solve. Only `CHARGE`: no `FONC_MULT` or `TYPE_CHARGE` (time-dependent: example 4). |
| `#ASTER-CONTACT K=V, ...` | Extra line in `DEFI_CONTACT` (global keywords). Only if the model has Mecway contact (`contact2`); otherwise the line is dropped without a message. |
| `#ASTER-ZONE K=V, ...` | Appended to **every** contact zone (`ZONE=_F(...)`); setting one zone separately is not possible. Your own `SANS_GROUP_NO` replaces the bridge's (fixed slave nodes), your own `INTEGRATION` replaces the bridge's (`NCOTES` for quadratic slave faces). |
| `#ASTER-OPTIE key = value` | Not Code-Aster code: overrides a setting of the active analysis (the keys of `CONFIG_BRIDGE["analyses"]`, see [Settings §2](Settings_contact_and_nonlinear.md#2-settings)), only for this model and this run. |
| `#ASTER-POST <code>` | Code-Aster code after the bridge's `CALC_CHAMP` calls, before the result export to Mecway and `IMPR_RESU`. |
| `#ASTER-BEZWIJKEN material = strain` | Not Code-Aster code: elements of this Mecway material fail at this equivalent plastic strain (`*` = all plastic materials; also `#ASTER-FAILURE`). Only nonlinear static and dynamic: [`Failure.md`](Failure.md). |
| `#ASTER-SPECTRE X, Y = name [, K=V]` | Not Code-Aster code: in the response spectrum analysis (`spectrum_3d`) `name` (a `DEFI_NAPPE` in `AMOR` and `FREQ` or a `FORMULE` from `#ASTER` code) is the spectrum for these directions, instead of the gravity table; `K=V` goes into `SPECTRE` (`ECHELLE`, `NATURE`, `CORR_FREQ`). Also `#ASTER-SPECTRUM`. Example 11, [`Response_spectrum.md`](Response_spectrum.md) §2.2. |
| `#ASTER-FASE selection = degrees` | Not Code-Aster code: in the harmonic response (`harmonic_3d`) the load on this selection gets this phase (`PHAS_DEG`; also `#ASTER-PHASE`; example 15, [`Mode_superposition.md`](Mode_superposition.md) §7). |
| `#ASTER-BRON selection = velocity [, phase]` | Not Code-Aster code: in harmonic acoustics (`acoustic_harm_3d`) a source on this face selection, normal velocity into the fluid (m/s or mm/s), phase in degrees (also `#ASTER-SOURCE`; example 12, [`Acoustics.md`](Acoustics.md) §5). In harmonic vibroacoustics (`vibroacoustic_harm_3d`) also with a pressure (Pa, kPa, bar, ...): an incident wave with that amplitude (example 27, [`Acoustics.md`](Acoustics.md) §7). |
| `#ASTER-LASBRON K=V, ...` | Not Code-Aster code: a moving weld source (Goldak) in a transient thermal analysis (also `#ASTER-WELD`); the bridge writes the `FORMULE` and the load itself. Keys and examples: [`Welding.md`](Welding.md), example 13. |
| `#ASTER-HYST material = eta` | Not Code-Aster code: in the harmonic response (`harmonic_3d`) this Mecway material gets the loss factor eta (hysteretic damping, `AMOR_HYST`, stiffness K(1 + i eta); `*` = all materials; wins over the setting `loss_factor`). [`Mode_superposition.md`](Mode_superposition.md) §7.2. |
| `#ASTER-MATERIAL name: K=V, ...` | Not Code-Aster code: temperature-dependent E, ν, α, yield strength and hardening of a Mecway material in the thermal → mechanical chain (T31 with a Thermal stress; also `#ASTER-MATERIAAL`). Keys: [`Welding.md`](Welding.md) §9.2, example 17. |
| `#ASTER-WOHLER material: K=V, ...` | Not Code-Aster code: Wöhler curve (table `S = [..] MPa, N = [..]`, power form `S, N, m` or Basquin `Sf, b`; S = amplitude) of this Mecway material (`*` = the rest) for fatigue: damage and life per node (fields `damage`, `life`). With `#ASTER-FATIGUE K=V` (also `#ASTER-VERMOEIING`: `stress`, `counting`, `repeats`), and for linear static `#ASTER-BLOCK a, m, n` (also `#ASTER-BLOK`) or `#ASTER-SIGNAL f1, f2, ...` (also `#ASTER-SIGNAAL`). Examples 19 and 20, [`Fatigue.md`](Fatigue.md). |
| `#ASTER-METALLURGIE name: K=V, ...` | Not Code-Aster code: phase transformations in steel (`CALC_META` with a CCT diagram) for a Mecway material in a transient thermal analysis, optionally with the metallurgical law in the thermal → mechanical chain (also `#ASTER-METALLURGY`). Keys and datasets: [`Welding.md`](Welding.md) §10, example 25. |
| `#ASTER-XFEM K=V, ...` | Not Code-Aster code: a crack that is not in the mesh (XFEM level set: `shape=` CIRCLE, ELLIPSE, RECTANGLE or HALF_PLANE with its dimensions), for linear static; the bridge writes `DEFI_FISS_XFEM`, `MODI_MODELE_XFEM`, `CALC_G_XFEM` and `POST_K1_K2_K3` and puts the fields back on Mecway's mesh. A line with `shape=` starts a new crack. Example 29, [`Fracture_mechanics.md`](Fracture_mechanics.md) §7. |
| `#ASTER-CONSTANT name, name2` | Not Code-Aster code: linear buckling with constant (dead) loads. A name is a Mecway selection (all loads on it) or a load type without selection (`gravity`); those loads stay constant and the buckling factor applies to the other loads only (K + Kg(constant) as `MATR_RIGI`). [`Modal_and_buckling.md`](Modal_and_buckling.md) §2.2.1. |
| `#ASTER-SECTION material: K=V, ...` | Not Code-Aster code: extra characteristics of a Mecway *General section* that Mecway has no field for (`AY`, `AZ`, `EY`, `EZ`, `RY`, `RZ`, `RT`, `JG`, `IYR2`, `IZR2`; SI), next to a copy of `A`, `IY`, `IZ`, `JX` as a check. The bridge puts `EY`, `EZ`, `RY`, `RZ`, `RT` in `AFFE_CARA_ELEM` (every beam) and `AY`, `AZ` for Timoshenko beams. Written by MecwaySectionProps (also `#ASTER-SECTIE`): [`MecwaySectionProps.md`](MecwaySectionProps.md) §5. |
| `<<Mecway selection>>` | In `#ASTER`, `-POST`, `-ZONE` and `-CONTACT`: becomes the Code-Aster group name of that selection (§3). |

- The kind (`-EXCIT`, `-POST`, ...) may be upper or lower case. An unknown kind (e.g.
  `#ASTER-FOO`) gives `ERROR: Unknown line '#ASTER-FOO' is skipped`.
- `#ASTER-OPTIE`: the type follows the existing value (integer, number, text; yes/no as
  `yes`/`no`, `on`/`off`, `true`/`false`, `1`/`0`, `ja`/`nee`, `aan`/`uit`, `oui`/`non`;
  any other word gives a WARNING and the setting is kept). A key the analysis does not have
  gives an ERROR with the list of known keys and is ignored (example 6). Each applied
  option is in the log: `INFO: #ASTER-OPTIE newton_max_iter = 40 (was 20).`

Position per analysis:

| Analysis (page) | `#ASTER` | `#ASTER-EXCIT` | `#ASTER-POST` | `t_res` |
|---|---|---|---|---|
| Static, Nonlinear static, Dynamic (implicit/explicit) | after the loads, before `MECA_STATIQUE`/`STAT_NON_LINE`/`DYNA_NON_LINE` | in `EXCIT` of the solve | after `CALC_CHAMP` | nonlinear and dynamic only |
| Thermal | after the thermal loads, before `THER_LINEAIRE`/`THER_NON_LINE` | in `EXCIT` of the thermal solve | after the flux post-processing; with a Thermal stress (thermal → mechanical chain, [`Welding.md`](Welding.md) §9) after the mechanical `CALC_CHAMP` (`res` = mechanical, `res_ther` = thermal) | with a Thermal stress |
| Modal | after the loads, before `ASSEMBLAGE` | in the matrices (`CHARGE` of `ASSEMBLAGE`; INFO in the log) and, with *Prestress from loads* (on by default), in `MECA_STATIQUE` (stress state) | before the export | no |
| Buckling | after the loads, before the static step | in `MECA_STATIQUE` (stress state) and in the matrices (`CHARGE` of `ASSEMBLAGE`) | before the export | no |
| Mode superposition, Response spectrum, Harmonic response | after the supports, before `ASSEMBLAGE` | in the matrices (`CHARGE` of `ASSEMBLAGE`) | before the export (harmonic: `res` is a `DYNA_HARMO` with complex `DEPL`) | no |
| Acoustics (harmonic) | after `AFFE_CHAR_ACOU`, before `ASSEMBLAGE` | not used (WARNING): `DYNA_VIBRA` only takes load vectors here; use `#ASTER-BRON` | after `DYNA_VIBRA` (result `res`, `ACOU_HARMO`), before the export | no |
| Vibroacoustics (harmonic) | after the loads of the structure, before the pressure nodes and sources | in the matrices (`CHARGE` of `ASSEMBLAGE`, as a support only) | after `CALC_CHAMP` (result `res`, `DYNA_HARMO` with complex `DEPL`, also `PRES`), before the export | no |

Consequence for *Modal* and *Buckling*: a connection that only exists through `#ASTER`
code (`LIAISON_ELEM`, `LIAISON_MAIL`, `DDL_IMPO`, ...; e.g. example 1 or 2) counts in
the eigenvalue problem if the load is in `#ASTER-EXCIT`. Without `#ASTER-EXCIT` the
part is loose (`ALGELINE3_81`). Forces in such a load do not contribute to the
matrices (`CHARGE` of `ASSEMBLAGE` only supplies the kinematic conditions; EDF R&D,
2021d); for *Buckling*, and for *Modal* with prestress, they do determine the stress
state through `MECA_STATIQUE`.
Computed: example 1 in both analyses (§6).

## 3. Selection names and groups

Code-Aster only accepts group names with a letter first, letters, digits and `_`, at
most 24 characters. The bridge renames (`bridge_mesh._aster_names`): invalid characters
become `_`, a name that does not start with a letter gets a `G` in front, too long is
cut and duplicates get `_1`, `_2`. So always write `<<Mecway name>>`, never the name
itself. Examples from the log:

```
INFO: Group name '02_Last-punt' -> 'G02_Last_punt' (Code-Aster: letter first, ...)
INFO: Group name '01_Contact_onder' -> 'G01_Contact_onder' ...
```

| Mecway | Code-Aster |
|---|---|
| node selection | `GROUP_NO` |
| face selection | `GROUP_MA` with face elements (no `GROUP_NO`) |
| element selection, elset (material/component) | `GROUP_MA` with the elements |

A solid face named in `#ASTER` code is added to the model as a boundary element
(otherwise e.g. `LIAISON_ELEM` cannot use it). An unknown selection gives
`ERROR: #ASTER: selection 'X' does not exist in the mesh.` in
`<model>_<run-id>_bridge_log.txt`; the name stays as it is and Code-Aster stops on it
(`MODELISA7_75`; message text in `Messages/modelisa7.py`, EDF R&D, 2026b).

## 4. General pitfalls

- **Units**: the bridge works in SI (m, N, Pa, s; the mesh is in metres). Values in
  `#ASTER` lines are not converted: `FX=200.0` is 200 N, `EPAIS=0.002` is 2 mm.
- **Names**: choose your own concept names that the bridge does not use. The bridge uses
  among others `mesh`, `model`, `cara`, `fieldmat`, `MAT_*`, `TRAC_*`, `FN_*`, `load_1`,
  `load_2`, ..., `times`, `outlist`, `listinst`, `contact`, `res`, `res_sup`/`res_moy`/
  `res_inf`, `res_flux`, `t_res`, `tab_*`, and in *Modal*/*Buckling* `rigidite`,
  `masse`, `rigi_geo`, `numedd`, `stat`, `sig`. A prefix of your own (e.g. `u_`) avoids
  clashes. Long names (e.g. `verbinding_balk`) work in 17.4.
- **Indentation**: the `.comm` is Python. A top-level line must start directly after
  `#ASTER `; inside brackets you can indent freely.
- **Do not forget `#ASTER-EXCIT`**: a load that is not in `EXCIT` does nothing. Example 1
  without `#ASTER-EXCIT`: the beam is loose, `FACTOR_11` or `FACTOR_42` (*Static*,
  depending on the model; with `solver_nprec` -1 also `FACTOR_57`) or `MECANONLINE9_4` (*Nonlinear static*). The same applies to *Modal* and *Buckling*: without
  `#ASTER-EXCIT` the connection is missing from the matrices (`ALGELINE3_81`).
- **Do not repeat what the bridge writes**: e.g. `FROTTEMENT` via `#ASTER-CONTACT`, or
  `ALGO_CONT`/`COEF_PENA_CONT` via `#ASTER-ZONE` when *Contact method* = PENALISATION.
  Python then stops with `SyntaxError: keyword argument repeated: ...`. Such an error is
  only shown in the Code-Aster window and in `<model>_<run-id>_console.txt`, not in the
  `.mess` (which ends without `<FIN>`, with `DIAGNOSTIC JOB : OK`). The bridge reads the
  console output and reports the Python error with the error line.
- **Result over time**: `t_res` (the last computed time) only exists in nonlinear static
  and dynamics (table in §2); otherwise use `NUME_ORDRE=1`.

## 5. Examples

Test models (steel: E = 210 GPa, ν = 0.3, ρ = 7850 kg/m³; dimensions in mm). A, C and
S are in `TestFiles/Voorbeelden/` (`Voorbeeld_A.liml`, `Voorbeeld_C.liml`,
`Voorbeeld_S.liml`, without `#ASTER` lines: paste the lines of the example into the
named field and choose the analysis). They were made with `maak_voorbeelden.py` in that
folder; `python maak_voorbeelden.py --run` computes all variants of examples 1 to 8
(bridge + Code-Aster, without Mecway) and prints the results below.

- **(A)** hex20 block 20 × 20 × 20 (2 × 2 × 2 elements, elset `Blok`, x = 0 … 20) with
  a separate tube 8/6 mm (*UniformCircularTube*), L = 50 mm, 5 line2 elements (elset
  `Balk`) from the centre of the end face x = 20 in +x, without shared nodes.
  Selections: `Root` (face x = 0, *Fixed*), `Tip` (face x = 20, where the beam starts),
  `BalkStart` and `BalkEind` (first and last beam node), `02_Last-punt` (the same node
  as `BalkEind`); 50 N in Y and −100 N in Z on `BalkEind`.
- **(C)** two hex8 blocks 20 × 20 × 10 (each 2 × 2 × 1, elsets `Onder` z = 0 … 10 and
  `Boven` z = 10 … 20) with their own nodes; Mecway contact (*unilateral elastic*,
  *normal stiffness* 100000 GPa/m, no friction) between `01_Contact_onder` (top face of
  `Onder`, master) and `02_Contact_boven` (bottom face of `Boven`); `Bodem` (bottom)
  fixed, `Top` (top) 0.01 mm down and fixed in x and y. *Nonlinear static*, 1 s, step
  0.1 s.
- **(S)** hex8 block 20 × 20 × 10 (4 × 4 × 2, elset `Blok`, `Bodem` fixed) with a
  separate quad4 plate 20 × 20, thickness 2 mm (4 × 4, elset `Plaat`), upright in the
  plane x = 10 (z = 10 … 30); `Plaatvoet` = the nodes of the bottom edge (on the top face
  of the block, not shared), `PlaatTop` = the nodes of the top edge, with 10 N in X.
- **(R)** cantilever hex8 beam 100x10x10 mm (`Root` fixed, `Tip` = end face); not in
  the repository.

### Example 1 – Beam attached to a solid face (`LIAISON_ELEM`, `3D_POU`)

Goal: connect a beam that stands on a solid face without shared nodes. The beam node gets
six relations with the face (EDF R&D, 2021a; catalogue `affe_char_meca.py`, block
`b_3d_pou`, EDF R&D, 2026a).

OpenRadioss > Custom model definition:

```
#ASTER verb = AFFE_CHAR_MECA(MODELE=model,
#ASTER     LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='<<Tip>>',
#ASTER                     GROUP_NO_2='<<BalkStart>>'))
#ASTER-EXCIT verb
```

In the `.comm` (after `load_2`, before `MECA_STATIQUE`):

```
# --- #ASTER-code van de gebruiker (Mecway custom input) ---
verb = AFFE_CHAR_MECA(MODELE=model,
    LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='Tip',
                    GROUP_NO_2='BalkStart'))
# --- einde ---
...
res = MECA_STATIQUE(
    ...
    EXCIT=(
        _F(CHARGE=load_1),
        _F(CHARGE=load_2),
        _F(CHARGE=verb),
    ),
```

Result (model A): *Static* displacement of `BalkEind` DY = 7.346e-5 m,
DZ = −1.469e-4 m; the clamped tube alone (F·L³/3EI) gives 7.218e-5 and −1.444e-4 m, the
difference (1.8%) is the block deflecting too. *Nonlinear static* equal (< 0.01%; the
beam stays geometrically linear there, WARNING).

Pitfalls:
- `GROUP_MA_1` is a face selection on the solid (the face under the beam), `GROUP_NO_2`
  a node selection with exactly one beam node.
- Computed with a hex20 solid; a linear (hex8) solid was not tested. According to
  U4.44.01 the solid must be quadratic: NOT verified in the 17.4 documentation.
- Without `#ASTER-EXCIT verb` the beam is loose (§4).
- *Modal* and *Buckling*: works with `#ASTER-EXCIT verb` (the connection then goes into
  the matrices, §2): *Modal* f1 = f2 = 2855.4 Hz (a pair, Y and Z), *Buckling* ±363.5
  and ±993.3 (model A). Check with a rigid block (model A with E = 2.1·10¹⁸ Pa for the
  block): f1 = f2 = 2894.35 Hz vs analytical 2894.3 Hz (clamped tube 8/6 mm,
  L = 50 mm, 5 beam elements; 07-10-2026). With the steel block f1 is 1.3% lower: the
  block deflects too.
- Shell to beam: `OPTION='COQ_POU'` (needs `CARA_ELEM` and `AXE_POUTRE`); shell to solid:
  `OPTION='COQ_3D'` (needs `GROUP_MA_COQUE`, `GROUP_MA_MASSIF` and `CARA_ELEM`), or
  `LIAISON_MAIL` (example 2). Both options are in the 17.4 catalogue; not computed.

### Example 2 – Shell on a solid (`LIAISON_MAIL`, `COQUE_MASSIF`)

Goal: connect the edge of a shell (DKT) rigidly to a solid without shared nodes,
including the rotations. The rotations of the shell nodes follow from the displacements
of the solid over the thickness `EPAIS`; `EPAIS` and `CHAM_NORMALE` (the normal of the
shell) are mandatory for this (catalogue `affe_char_meca.py`, block `b_COQUE_MASSIF`).

Mystran > Custom bulk data:

```
$ASTER nplaat = CREA_CHAMP(TYPE_CHAM='NOEU_GEOM_R', OPERATION='NORMALE',
$ASTER     MODELE=model, GROUP_MA='<<Plaat>>')
$ASTER lijm = AFFE_CHAR_MECA(MODELE=model,
$ASTER     LIAISON_MAIL=_F(TYPE_RACCORD='COQUE_MASSIF',
$ASTER         GROUP_MA_MAIT='<<Blok>>', GROUP_NO_ESCL='<<Plaatvoet>>',
$ASTER         EPAIS=0.002, CHAM_NORMALE=nplaat))
$ASTER-EXCIT lijm
```

In the `.comm`:

```
# --- #ASTER-code van de gebruiker (Mecway custom input) ---
nplaat = CREA_CHAMP(TYPE_CHAM='NOEU_GEOM_R', OPERATION='NORMALE',
    MODELE=model, GROUP_MA='Plaat')
lijm = AFFE_CHAR_MECA(MODELE=model,
    LIAISON_MAIL=_F(TYPE_RACCORD='COQUE_MASSIF',
        GROUP_MA_MAIT='Blok', GROUP_NO_ESCL='Plaatvoet',
        EPAIS=0.002, CHAM_NORMALE=nplaat))
# --- einde ---
...
    EXCIT=(
        _F(CHARGE=load_1),
        _F(CHARGE=load_2),
        _F(CHARGE=lijm),
    ),
```

Result (model S): 10 N transverse on the top edge gives 0.00897 mm deflection (mean
over `PlaatTop`, both static analyses); a clamped plate strip (F·L³/3EI with 1-ν²)
gives 0.00867 mm, the difference (3.5%) is mainly the block deflecting too. So the
connection acts as a clamp.

Pitfalls:
- `GROUP_MA_MAIT` are the **solid elements** (the elset), not a face.
- `EPAIS` in metres, equal to the plate thickness.
- If the plate is perpendicular to X, the bridge itself sets a `VECTEUR` in
  `AFFE_CARA_ELEM COQUE` (otherwise `PLATE1_40`).

### Example 3 – Extra load and restraint

Goal: a point force and a rotation restraint you do not want to put in Mecway, on a
selection with an "awkward" name. Model A with example 1 in the OpenRadioss field.

Mystran > Custom bulk data (node selection `02_Last-punt` = the beam end node):

```
$ Extra last en blokkering voor Code-Aster (SI-eenheden: N, m)
$ASTER extra = AFFE_CHAR_MECA(MODELE=model,
$ASTER     FORCE_NODALE=_F(GROUP_NO='<<02_Last-punt>>', FX=200.0),
$ASTER     DDL_IMPO=_F(GROUP_NO='<<02_Last-punt>>', DRX=0.0))
$ASTER-EXCIT extra
```

In the `.comm` (the lines from the OpenRadioss field come first, §1):

```
# --- #ASTER-code van de gebruiker (Mecway custom input) ---
verb = AFFE_CHAR_MECA(MODELE=model,
    LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='Tip',
                    GROUP_NO_2='BalkStart'))
extra = AFFE_CHAR_MECA(MODELE=model,
    FORCE_NODALE=_F(GROUP_NO='G02_Last_punt', FX=200.0),
    DDL_IMPO=_F(GROUP_NO='G02_Last_punt', DRX=0.0))
# --- einde ---
...
        _F(CHARGE=verb),
        _F(CHARGE=extra),
```

Result: DX of the beam end node 2.211e-6 m (*Static*; the tube alone, F·L/EA:
2.165e-6 m).

Pitfalls:
- The first line (`$ Extra ...`) is a Mystran comment; the bridge skips it.
- `DRX`/`DRY`/`DRZ` only on beam and shell nodes; solid nodes have no rotations.
- A restraint on nodes that Mecway already fixes gives a duplicated condition and can
  give a singular matrix (KNOWN_BUGS 8).

### Example 4 – Time-dependent extra load (nonlinear)

Goal: a load that increases over time. `#ASTER-EXCIT` has no `FONC_MULT`; so create the
load with `AFFE_CHAR_MECA_F` and a function of `INST` (catalogue `defi_fonction.py`).
Model A with example 1 in the OpenRadioss field *Custom model definition*.

OpenRadioss > Custom engine input:

```
#ASTER f_ramp = DEFI_FONCTION(NOM_PARA='INST', VALE=(0.0, 0.0, 1.0, 300.0),
#ASTER                        PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')
#ASTER ramp = AFFE_CHAR_MECA_F(MODELE=model,
#ASTER     FORCE_NODALE=_F(GROUP_NO='<<BalkEind>>', FX=f_ramp))
#ASTER-EXCIT ramp
```

In the `.comm` (before `STAT_NON_LINE`):

```
# --- #ASTER-code van de gebruiker (Mecway custom input) ---
verb = AFFE_CHAR_MECA(MODELE=model,
    LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='Tip',
                    GROUP_NO_2='BalkStart'))
f_ramp = DEFI_FONCTION(NOM_PARA='INST', VALE=(0.0, 0.0, 1.0, 300.0),
                       PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')
ramp = AFFE_CHAR_MECA_F(MODELE=model,
    FORCE_NODALE=_F(GROUP_NO='BalkEind', FX=f_ramp))
# --- einde ---
...
        EXCIT=(
            _F(CHARGE=load_1),
            _F(CHARGE=load_2),
            _F(CHARGE=verb),
            _F(CHARGE=ramp),
        ),
```

Result (DX of the beam end node per time step in the results; in the `.mess` it can be
done with `POST_RELEVE_T` of `DEPL` and `TOUT_ORDRE='OUI'`, as in example 7): DX
increases by 3.317e-7 m per 0.1 s (the rising 300 N), from 3.317e-7 m at t = 0.1 to
3.317e-6 m at t = 1 (the tube alone, F·L/EA: 3.248e-6 m). Without this load DX is
practically 0 (−1.4e-11 m): the beam is geometrically linear here as well. DY/DZ of
the constant Mecway force are complete from the first step.

Pitfalls:
- Only for nonlinear static and dynamic. `MECA_STATIQUE` computes at INST = 0: this load
  is zero there (computed: DX = 0).
- Constant loads without a function (including the bridge's) act fully from the first
  time step.

### Example 5 – Contact: penalty and Newton for the geometry

Goal: change the bridge's contact formulation (`FORMULATION='CONTINUE'`) per zone. For
penalty contact with Mecway's own stiffness the setting *Contact method* = PENALISATION
is the first choice ([Settings §3](Settings_contact_and_nonlinear.md#3-contact)); this
example shows how to do it with `#ASTER` lines, e.g. when Mecway has no *normal
stiffness*. Keywords according to the catalogue `defi_contact.py` (EDF R&D, 2026a;
background EDF R&D, 2021b).

OpenRadioss > Custom model definition:

```
#ASTER-ZONE ALGO_CONT='PENALISATION', COEF_PENA_CONT=1.0E14
#ASTER-CONTACT ALGO_RESO_GEOM='NEWTON'
```

In the `.comm`:

```
contact = DEFI_CONTACT(
    MODELE=model,
    FORMULATION='CONTINUE',
    FROTTEMENT='SANS',
    ALGO_RESO_GEOM='NEWTON',
    ZONE=(
        _F(GROUP_MA_MAIT='G01_Contact_onder', GROUP_MA_ESCL='G02_Contact_boven', ALGO_CONT='PENALISATION', COEF_PENA_CONT=1.0E14),
    ),
)
```

Result (model C): the reaction force (example 7) is 42.36 kN with penalty against
47.41 kN without: with penalty the blocks penetrate each other slightly. Hand check: the
contact spring 1e14 Pa/m × 4·10⁻⁴ m² = 4·10¹⁰ N/m in series with the blocks
(47.41 kN / 0.01 mm = 4.74·10⁹ N/m) gives 42.39 kN. *Contact method* = PENALISATION with
*normal stiffness* 100000 GPa/m (= 1e14 Pa/m) in Mecway gives the same 42.36 kN.

Pitfalls:
- `ALGO_RESO_GEOM`/`ALGO_RESO_CONT` belong to `DEFI_CONTACT` (`#ASTER-CONTACT`),
  `ALGO_CONT`/`COEF_PENA_CONT`/`CONTACT_INIT`/`INTEGRATION` to `ZONE` (`#ASTER-ZONE`).
- Not together with *Contact method* = PENALISATION: `ALGO_CONT` then appears twice
  (computed: `SyntaxError: keyword argument repeated: ALGO_CONT`). Without *normal
  stiffness* in Mecway that setting falls back to STANDARD (WARNING).
- Do not repeat what the bridge writes: `FORMULATION`, `FROTTEMENT`, `COULOMB`,
  `GROUP_MA_MAIT`/`GROUP_MA_ESCL` (§4).
- Without Mecway contact, `-CONTACT`/`-ZONE` are ignored.

### Example 6 – Contact start and solver settings (`#ASTER-OPTIE`)

Goal: all contact points active at the start, fixed-point iteration for the contact, and
for this model more Newton iterations, stricter convergence and small displacements.
Fewer steps: *Time step size* 0.25 s in Mecway (the bridge computes Mecway's steps;
`substeps_per_interval` only applies to a model without a step size).

OpenRadioss > Custom model definition:

```
#ASTER-ZONE CONTACT_INIT='OUI'
#ASTER-CONTACT ALGO_RESO_CONT='POINT_FIXE', ITER_CONT_MAXI=50
#ASTER-OPTIE newton_max_iter = 40
#ASTER-OPTIE convergence_resi_rela = 1e-8
#ASTER-OPTIE deformation = PETIT
```

In the `.comm`:

```
times = DEFI_LIST_REEL(
    VALE=(0.0, 0.25, 0.5, 0.75, 1.0),
)
...
contact = DEFI_CONTACT(
    MODELE=model,
    FORMULATION='CONTINUE',
    FROTTEMENT='SANS',
    ALGO_RESO_CONT='POINT_FIXE', ITER_CONT_MAXI=50,
    ZONE=(
        _F(GROUP_MA_MAIT='G01_Contact_onder', GROUP_MA_ESCL='G02_Contact_boven', CONTACT_INIT='OUI'),
    ),
)
...
        COMPORTEMENT=(
            _F(GROUP_MA='Onder', RELATION='ELAS', DEFORMATION='PETIT'),
            _F(GROUP_MA='Boven', RELATION='ELAS', DEFORMATION='PETIT'),
        ),
        ...
        CONVERGENCE=_F(RESI_GLOB_RELA=1e-08, ITER_GLOB_MAXI=40),
```

Result (model C): reaction force 47.45 kN after 4 steps (with the default GROT_GDEP
47.41 kN).

Pitfalls:
- The keys are bridge settings (page of the analysis), not Code-Aster words. Which ones
  exist depends on the analysis: `schema = HHT` in a nonlinear static analysis gives
  `ERROR: #ASTER-OPTIE 'schema' does not exist for this analysis; ignored. Known:
  contact_algo, convergence_criterion, convergence_resi_maxi, ...`.
- `deformation` is a choice for the whole model; with large displacements the bridge
  sets the form Code-Aster accepts per element type
  ([Settings §2.3](Settings_contact_and_nonlinear.md#23-kinematics-deformation)).
- Useful options for convergence problems: `convergence_criterion = MAXI` or
  `RELA_OF_MAXI` (with `convergence_resi_maxi`), `contact_algo = PENALISATION`
  (`convergence_resi_rela` is already 1e-5 by default)
  ([`CodeAster_error_messages.md`](CodeAster_error_messages.md#mecanonline9_7--newton-does-not-converge));
  checked in the `.comm` that they arrive as `RESI_GLOB_MAXI` and `ALGO_CONT`.

### Example 7 – Reaction force on a face in the `.mess`

Goal: the total reaction force on the clamped bottom as a table (`POST_RELEVE_T`:
catalogue `post_releve_t.py`, EDF R&D, 2026a; background EDF R&D, 2021c).

OpenRadioss > Custom model definition:

```
#ASTER-POST mesh = DEFI_GROUP(reuse=mesh, MAILLAGE=mesh,
#ASTER-POST     CREA_GROUP_NO=_F(NOM='bodem_n', GROUP_MA='<<Bodem>>'))
#ASTER-POST reac = POST_RELEVE_T(ACTION=_F(OPERATION='EXTRACTION',
#ASTER-POST     INTITULE='reactie', RESULTAT=res, NOM_CHAM='REAC_NODA',
#ASTER-POST     GROUP_NO='bodem_n', RESULTANTE=('DX', 'DY', 'DZ'),
#ASTER-POST     INST=t_res))
#ASTER-POST IMPR_TABLE(TABLE=reac, UNITE=6)
```

In the `.comm` (after the `CALC_CHAMP` calls; `REAC_NODA` exists by then):

```
# --- #ASTER-POST-code van de gebruiker (Mecway custom input) ---
mesh = DEFI_GROUP(reuse=mesh, MAILLAGE=mesh,
    CREA_GROUP_NO=_F(NOM='bodem_n', GROUP_MA='Bodem'))
reac = POST_RELEVE_T(ACTION=_F(OPERATION='EXTRACTION',
    INTITULE='reactie', RESULTAT=res, NOM_CHAM='REAC_NODA',
    GROUP_NO='bodem_n', RESULTANTE=('DX', 'DY', 'DZ'),
    INST=t_res))
IMPR_TABLE(TABLE=reac, UNITE=6)
# --- einde ---
```

Output in the `.mess` (model C, *Nonlinear static*):

```
INTITULE         RESU     NOM_CHAM         NUME_ORDRE   INST         DX           DY           DZ
reactie          00000009 REAC_NODA                  10  1.00000E+00  6.82121E-13  4.54747E-13  4.74133E+04
```

Pitfalls:
- A face selection is a `GROUP_MA`. `POST_RELEVE_T` needs `GROUP_NO` here; `GROUP_MA=` in
  `ACTION` gave `SUPERVIS_4`, and `GROUP_NO='Bodem'` (does not exist as a node group)
  gave an **empty** table without a message. So create the node group with
  `DEFI_GROUP`. In these tests `DEFI_GROUP(reuse=mesh)` after the solve worked; if a job
  aborts on it without a message, see
  [Error messages §9](CodeAster_error_messages.md#no-code-crash-aborted-job-or-logging-error).
- `UNITE=6` writes to the `.mess`. Unit 8 is the `.resu` file the bridge itself reads in
  the `tabel` route (it does not exist in the `liml` route); do not write there.
- *Static*: `t_res` does not exist; write `NUME_ORDRE=1` (computed on model A with
  `GROUP_MA='<<Root>>'`: reaction (0; -50; 100) N, equal to minus the load).

### Example 8 – Maximum von Mises in the `.mess`

Goal: the largest and smallest von Mises stress (nodal value) as a table.

OpenRadioss > Custom engine input:

```
#ASTER-POST tmax = POST_RELEVE_T(ACTION=_F(OPERATION='EXTREMA',
#ASTER-POST     INTITULE='vmis_max', RESULTAT=res, NOM_CHAM='SIEQ_NOEU',
#ASTER-POST     NOM_CMP='VMIS', TOUT='OUI'))
#ASTER-POST IMPR_TABLE(TABLE=tmax, UNITE=6)
```

Output in the `.mess` (model A with example 1, *Static*):

```
INTITULE         RESU     NOM_CHAM         NUME_ORDRE   INST         EXTREMA  NOEUD    CMP      VALE
vmis_max         0000000a SIEQ_NOEU                   1  0.00000E+00 MAX      22       VMIS      7.08280E+06
vmis_max         0000000a SIEQ_NOEU                   1  0.00000E+00 MIN      8        VMIS      2.05799E+05
...                                                                 (also MAXI_ABS, MINI_ABS)
```

Pitfalls:
- The bridge already computes `SIGM_NOEU`, `SIEQ_NOEU` and, in the `liml` route, for
  solid elements also `SIGM_ELNO`/`SIEQ_ELNO` itself (for model A `stressxx` …
  `vonmises` are in the results as node and as element-node values, with or without
  extra lines). Your own
  `CALC_CHAMP(... CONTRAINTE=('SIGM_ELNO',), CRITERES=('SIEQ_ELNO',))` adds nothing and
  gives alarm `CALCCHAMP_1`.
- Fields the export does not know do not reach Mecway, nor the bridge's MED output (fixed
  list of fields); print them with `IMPR_TABLE`.
- In nonlinear analyses and dynamics, `TOUT='OUI'` without `INST` gives a table per time
  step; with `INST=t_res` only the last time.

### Example 9 – Rotating a rigid part by 90 degrees (large rotation, `FORMULE`)

Goal: rotate a rigid part (roller, punch, clamp) through a large angle about an axis. An
imposed node rotation (Mecway *Node rotation*), a beam as an arm and a rigid coupling
(RBE2, `LIAISON_SOLIDE`) assume small rotations in Code-Aster; with large rotations that
does not work (KNOWN_BUGS 11). Robust is the exact rigid motion as an imposed
displacement: u = (R(t) - I)(X - C), with C a point on the axis. A bending model (profile around a die)
was computed implicitly up to 90 degrees this way.

Mecway: set *Node rotation*, the arm and the RBE2 to *suppressed* (or delete them) and
create a selection of the nodes or faces of the rigid part, here `Tip`. Choose
*Nonlinear static*. CCX > Custom model definition (`**ASTER`), OpenRadioss (`#ASTER`) or
Mystran (`$ASTER`):

```
#ASTER-OPTIE deformation = GROT_GDEP
#ASTER import math
#ASTER # Starre rotatie om de as door C, richting x; hoek lineair 0 -> 90 graden in t = 0..1
#ASTER _C = (0.1, 0.005, 0.005)
#ASTER def _hoek(t):
#ASTER     return 0.5 * math.pi * min(max(t, 0.0), 1.0)
#ASTER FDX = FORMULE(VALE="0.0*INST", NOM_PARA=['INST'])
#ASTER FDY = FORMULE(VALE="(cos(_hoek(INST))-1)*(Y-_C[1]) - sin(_hoek(INST))*(Z-_C[2])",
#ASTER               cos=math.cos, sin=math.sin, _hoek=_hoek, _C=_C, NOM_PARA=['Y', 'Z', 'INST'])
#ASTER FDZ = FORMULE(VALE="sin(_hoek(INST))*(Y-_C[1]) + (cos(_hoek(INST))-1)*(Z-_C[2])",
#ASTER               cos=math.cos, sin=math.sin, _hoek=_hoek, _C=_C, NOM_PARA=['Y', 'Z', 'INST'])
#ASTER rotdrive = AFFE_CHAR_MECA_F(MODELE=model,
#ASTER     DDL_IMPO=_F(GROUP_MA='<<Tip>>', DX=FDX, DY=FDY, DZ=FDZ))
#ASTER-EXCIT rotdrive
```

For a rotation about the z axis swap the roles: `FDX` and `FDY` with (X, Y), `FDZ` zero.

Result (model R, tip face 90 degrees about the x axis through (0.1; 0.005; 0.005) m):
node (0.1; 0; 0) moves (0; 0.01; 0) m, exactly the rigid rotation (10 steps, no step
subdivision).

Pitfalls:
- `X`, `Y`, `Z` in a `FORMULE` are the initial positions of the nodes; the angle must be
  a function of `INST`, and the time steps small enough (the bridge subdivides a step
  automatically if Newton does not converge).
- `deformation = GROT_GDEP` is the default; the line only makes the choice explicit.
- A node that is already fixed must not also be in the rotated group (duplicated
  condition).
- Pass `cos`/`sin` and your own functions to `FORMULE` as arguments.

### Example 10 – Nonlinear buckling per model (`#ASTER-OPTIE`)

Goal: switch on the stability per step (`CRIT_STAB`) and a buckling mode as
imperfection in one model, without changing the settings of the page *Nonlinear
static* (explanation: [`Modal_and_buckling.md`](Modal_and_buckling.md) §5). Mecway:
*Nonlinear Static*, the load with a time table from 0. CCX > Custom model definition:

```
** ASTER-OPTIE crit_stab = ja
** ASTER-OPTIE imperfection_amplitude = 0.001
** ASTER-OPTIE imperfection_unit = L
```

Twenty steps: *Time step size* 0.05 s with a period of 1 s (the bridge computes
Mecway's steps).

`imperfection_unit = L` makes the amplitude a fraction of the largest dimension of the
model (here L/1000); with `m` (default) it is a length in metres. Another buckling
mode: `imperfection_mode = 2`.

Result (the column of verification NK-03, hex20, load up to 0.9 Pcr): the log shows
the three options (`INFO: #ASTER-OPTIE crit_stab = True (was False).` etc.),
`Imperfectie: amplitude 0.001 x L, L = 1 m ... = 0.001 m`, the buckling factor of the
imperfection step 1.11339 and per step the stability criterion (at t = 1: −2.70);
`DIAGNOSTIC JOB : OK`, the same numbers as NK-03 with the settings on the page.

### Example 11 – Own response spectrum with several damping values (`#ASTER-SPECTRE`)

Goal: a spectrum that varies with damping (here for 0.5% and 5%, logarithmic in the
frequency, linear in the damping), as in Code-Aster test case sdld25a. A gravity table
cannot do that: it holds for one damping. Mecway: *Frequency* with the modes, analysis
`spectrum_3d` (explanation: [`Response_spectrum.md`](Response_spectrum.md)). CCX >
Custom model definition:

```
** ASTER A_0_5 = DEFI_FONCTION(NOM_PARA='FREQ', INTERPOL='LOG',
** ASTER     VALE=(1.0, 1.0, 3.0, 25.0, 13.0, 25.0, 33.0, 1.0))
** ASTER A_5_0 = DEFI_FONCTION(NOM_PARA='FREQ', INTERPOL='LOG',
** ASTER     VALE=(1.0, 1.0, 3.0, 10.0, 13.0, 10.0, 33.0, 1.0))
** ASTER SPECT = DEFI_NAPPE(NOM_PARA='AMOR', INTERPOL=('LIN', 'LOG'),
** ASTER     PARA=(0.005, 0.05), FONCTION=(A_0_5, A_5_0))
** ASTER-SPECTRE X = SPECT
** ASTER-OPTIE spectrum_damping = 0
** ASTER-OPTIE modal_combination = SRSS
```

The accelerations in `VALE` are in m/s² (with `, ECHELLE=9.81` after the name they
are units of g). The damping per mode comes from Mecway's *Rayleigh damping* here
(β = 5e-4 s), hence `spectrum_damping = 0`. A direction with `#ASTER-SPECTRE` needs
no gravity. The spectrum must be a `DEFI_NAPPE` (parameter `AMOR`) or a `FORMULE` in
`AMOR` and `FREQ`; a `DEFI_FONCTION` in `FREQ` only gives an error of
`COMB_SISM_MODAL`.

Outcome (verification SP-01, the rebuild of sdld25a with Mecway springs and masses):
the log reports `INFO: #ASTER lines: 6 code, ..., 1 SPECTRE, ...` and the two options;
the absolute accelerations `accelx` equal the TEST_RESU values of sdld25a (e.g. P1
10.4498 m/s²).

### Example 12 – Harmonic acoustics: source with phase and own frequencies (`#ASTER-BRON`)

Goal: a loudspeaker with 2 mm/s and 90 degrees phase on a face selection without a
prefix, and the frequencies per model (explanation: [`Acoustics.md`](Acoustics.md) §5).
Mecway: *Acoustic Resonance 3D*, air with a density, face selection `Luidspreker` at
x = 0, face selection `ABSORBEREND_Einde` at x = L and node selections
`MICROFOON_Eind`, `MICROFOON_Midden`. CCX > Custom model definition:

```
** ASTER-BRON Luidspreker = 2 mm/s, 90
** ASTER-OPTIE harm_freq_list = 200, 500
```

`#ASTER-BRON selection = velocity [, phase]`: normal velocity into the fluid (m/s or
mm/s), phase in degrees (`, fase = 90` is allowed too); also `#ASTER-SOURCE`. The
selection must be a face selection; a line for a `SOURCE_` selection replaces the
default velocity. With a source, `auto` chooses the analysis *Acoustics (harmonic)*.
In the `.comm`:

```
ch_vite = AFFE_CHAR_ACOU(
    MODELE=model,
    VITE_FACE=(
        _F(GROUP_MA='Luidspreker', VNOR=('RI', 0.0, 0.002)),  # #ASTER-BRON Luidspreker
    ),
)
...
freqs = DEFI_LIST_REEL(VALE=(200.0, 500.0,))
```

Result (verification AH-08, hex20 duct 1 x 0.1 x 0.1 m): at x = 0, p = i·ρcv = 0.816i
Pa (Re < 1e-5 Pa), both microphones 89.20 dB, the phase in `MICROFOON_Eind`
90° − kL within 0.02°; `DIAGNOSTIC JOB : OK`.

### Example 14 – Vibroacoustics: modes from a frequency on (`#ASTER-OPTIE`)

Goal: in a panel-on-cavity model only the coupled modes above 100 Hz (explanation:
[`Acoustics.md`](Acoustics.md) §6). Mecway: *Frequency 3D* with *Number of modes* 3, a
steel plate (part `Paneel`, shells) on an air volume (part `Lucht`, material with only
*Speed of sound* and *Density*: that is how the bridge recognises the fluid; a part
name `LUCHT_...` or `FLUID_...` works too). Special selection names of vibroacoustics
(no `#ASTER` line needed): `OPEN_...` (nodes or faces, p = 0) and `KOPPEL_...` (faces,
manual coupling faces; also `COUPLING_...`). CCX > Custom model definition:

```
** ASTER-OPTIE vibro_freq_min = 100
```

With a fluid, `auto` chooses the analysis *Vibroacoustics (modes)*. In the `.comm` this
becomes the lower bound of the band in which `INFO_MODE` and `CALC_MODES
OPTION='BANDE'` search:

```
bridge_n = 3
bridge_fmin = 100.0
...
res_band = CALC_MODES(
    ...
    OPTION='BANDE',
    CALC_FREQ=_F(FREQ=(bridge_fmin, _hi)),
```

Result (verification VA-05c, plate 0.5 × 0.4 m, 2 mm, on an air cavity 0.5 × 0.4 ×
0.3 m): the pumping mode (54.96 Hz) drops out; modes 1–3 are the plate modes (2,1),
(1,2), (2,2) at 109.0 / 142.3 / 200.9 Hz; `DIAGNOSTIC JOB : <A>_ALARM`, only
`MODELISA4_8`/`MODELISA8_13` (shell and coupling face are separate cells on the same
nodes, [`Acoustics.md`](Acoustics.md) §6.7).

### Example 27 – Vibroacoustics harmonic: incident wave with phase (`#ASTER-BRON` with a pressure)

Goal: a duct into which a sound wave of 0.5 Pa enters with −30° phase, at one
frequency (explanation: [`Acoustics.md`](Acoustics.md) §7). Mecway: *Frequency 3D* with
an air volume (material with only *Speed of sound* and *Density*), face selection
`Inlet` at x = 0 (without prefix), face selection `ABSORBING_Outlet` at x = L, node
selection `MICROPHONE_Outlet`; choose the analysis `vibroacoustic_harm_3d` yourself
(`auto` computes the coupled modes). CCX > Custom model definition:

```
** ASTER-BRON Inlet = 0.5 Pa, -30
** ASTER-OPTIE harm_freq_list = 500
```

In vibroacoustics a **pressure unit** (Pa, N/m2, kPa, kN/m2, MPa, N/mm2, GPa, bar, mbar,
psi) makes `#ASTER-BRON` an incident
wave (`ONDE_FLUI`, the amplitude of the wave entering the fluid), a velocity (m/s, mm/s,
mm/ms, in/s, ft/s or no unit) a velocity source (`VITE_FACE`); any other unit gives an
ERROR. For example `** ASTER-BRON Inlet = 14 mm/s,
90`. Without an `#ASTER` line: a face selection `INCIDENT_...` with the setting
*Amplitude incident wave* or `SOURCE_...` with *Velocity SOURCE_ faces*. In the
`.comm`:

```
ch_onde_1 = AFFE_CHAR_MECA(MODELE=model, ONDE_FLUI=_F(GROUP_MA='Inlet', PRES=1.0))
...
        _F(VECT_ASSE=vec_onde_1, COEF_MULT=1.0, PUIS_PULS=1, PHAS_DEG=60.0),  # #ASTER-BRON Inlet
```

(`PRES` = 2 × 0.5 Pa: Code-Aster's boundary gives an incoming wave with amplitude
`PRES`/2; `PHAS_DEG` = 90 + phase, because the vector is multiplied by iω.)

Outcome (verification VH-08, wave guide 1 × 0.1 × 0.2 m, hex20, ρ 1.3, c 343): the
pressure in the four nodes of ahlv101a equals the TEST_RESU value of ahlv101a ×
e^{−i30°} within 1.1e-7; with `14 mm/s, 90` (VH-07) it is ahlv100b × i within 2.3e-7;
`DIAGNOSTIC JOB : OK`.

### Example 13 – Moving weld source (`#ASTER-LASBRON`)

Goal: the temperature field of a weld bead with a Goldak source, without writing a
formula yourself (explanation and all keys: [`Welding.md`](Welding.md)). Mecway:
*Thermal transient* (T31) with an initial temperature; CCX > Custom model definition:

```
** ASTER-LASBRON Q=1250, eta=0.8, v=0.005, start=(0.01, 0, 0), direction=(1, 0, 0)
** ASTER-LASBRON af=0.001, ar=0.002, b=0.001, c=0.001, symmetry=1
```

The bridge writes in the `.comm` (after the thermal loads):

```
def _lb_goldak(X, Y, Z, INST, P):
    ...
_LB1 = (0.0, 0.005, 0.03,
    ((0.01, 0.0, 0.0), (0.04, 0.0, 0.0),),
    ...)
LB1 = FORMULE(VALE='_lb_goldak(X, Y, Z, INST, _LB1)', NOM_PARA=('X', 'Y', 'Z', 'INST'),
    _lb_goldak=_lb_goldak, _LB1=_LB1)
lasbron_1 = AFFE_CHAR_THER_F(MODELE=model, SOURCE=(
    _F(GROUP_MA='TH1', SOUR=LB1),
))
```

with `lasbron_1` in `EXCIT`, and after the solve the energy check (`BRIDGE_LASBRON` in
the `.mess`).

Result (verification WE-02, half plate 55 × 15 × 15 mm, 35 600 nodes): `DIAGNOSTIC
JOB : OK`, the mesh takes up 500.00 W (100.0% of η·Q/2), the temperatures next to and
behind the source are within 1.2% of the same source folded analytically.

Pitfalls:
- Values in SI: coordinates in metres, also when the Mecway model is in mm.
- A second source starts with a line beginning with `Q=`; each source gets its own
  `t0`. All sources are put together in one load (`lasbron`), also with an *Internal
  heat generation* as a formula or time table ([Thermal.md](Thermal.md) §3).
- Only in a transient thermal analysis; in a mechanical analysis the line is ignored
  (WARNING).

### Example 15 – Harmonic response: load phase and probe (`#ASTER-FASE`)

Goal: two harmonic forces in antiphase on a structure and the frequency response at
a point (explanation: [`Mode_superposition.md`](Mode_superposition.md) §7). Mecway:
*Frequency 3D* (or *Dynamic Response 3D*) with the forces on the node selections
`Last` and `Last2` (the value is the amplitude), Rayleigh damping, and a node
selection `PROBE_Tip`; in the main window the analysis *Harmonic response*
(`harmonic_3d`). CCX > Custom model definition:

```
** ASTER-FASE Last2 = 180
** ASTER-OPTIE harm_freq_list = 5, 10, 16.7, 25
```

`#ASTER-FASE selection = degrees`: the load on that selection gets that phase
(`PHAS_DEG` in `EXCIT`; also `#ASTER-PHASE`); loads without a line have phase 0. The
selection must carry a load (otherwise ERROR); a load acting on several selections
with different phases (merged beam loads) is not possible (ERROR: give each
selection its own load). In the `.comm`:

```
harm = DYNA_VIBRA(
    TYPE_CALCUL='HARM',
    BASE_CALCUL='GENE',
    ...
    EXCIT=(
        _F(VECT_ASSE_GENE=fgen_1, COEF_MULT=1.0, PHAS_DEG=0.0),
        _F(VECT_ASSE_GENE=fgen_2, COEF_MULT=1.0, PHAS_DEG=180.0),
    ),
)
```

An amplitude that changes with frequency: give the load a table in Mecway; the
*time* column is then the frequency in Hz (e.g. an unbalance force m·e·ω²). The node
selection `PROBE_...` (or `MEETPUNT_...`) gives |u|, |a|, Re/Im and phase per
frequency in the log and in `<model>_<run-id>_meetpunten.csv`.

Result (a mass on a spring, `DIAGNOSTIC JOB` OK with alarm `MODELISA8_14` from the
spring element, also without these lines): verification HR-05 (10 N on `Last`, 4 N on
`Last2` with `#ASTER-FASE Last2 = 180`): the response is that of 6 N (amplitude
< 1e-7, phase < 1e-5 degrees from the single-degree-of-freedom solution); HR-04
(F(f) = 10 + 2f N from a table, `#ASTER-FASE Last = 90`, `MEETPUNT_Massa`): likewise,
and the CSV equal to the nodal values.

### Example 16 – Fracture mechanics: own R_INF/R_SUP per model (`#ASTER-OPTIE`)

Goal: K and G along a meshed crack with an own ring for `CALC_G` (explanation:
[`Fracture_mechanics.md`](Fracture_mechanics.md)). Mecway: *Static 3D*; the crack was
opened with *Disconnect elements* and has the special selection names (no `#ASTER`
line needed): node selection `CRACK_FRONT` and face selections
`CRACK_LIP_UPPER`/`CRACK_LIP_LOWER` (or `SCHEUR_FRONT`, `SCHEUR_LIP_BOVEN`,
`SCHEUR_LIP_ONDER`; several cracks with a suffix, `CRACK_FRONT_A`, ...). CCX > Custom
model definition:

```
** ASTER-OPTIE fracture_r_inf = 0.2
** ASTER-OPTIE fracture_r_sup = 0.5
```

In the `.comm` (after the result export):

```
scheur_g_1 = CALC_G(
    RESULTAT=res_fiss,
    OPTION=('G', 'K'),
    THETA=_F(FISSURE=fond_1, R_INF=0.2, R_SUP=0.5), FORM_FISS='CERCLE', RAYON=2.0...,
)
```

Result (verification BR-04, Code-Aster test case forma07a through the bridge,
penny-shaped crack with radius 2 m): K1 MAX of `POST_K1_K2_K3` 1,607,011.55 Pa·√m
(equal to the TEST_TABLE value), G 11.68 J/m² (analytical 11.59); `DIAGNOSTIC JOB :
OK`.

### Example 17 – Residual stress with temperature-dependent steel (`#ASTER-MATERIAL`)

Goal: after the thermal welding run (example 13) the residual stress and distortion,
with E, yield strength and α that change with temperature (Mecway only knows that for
λ and c). Mecway: *Thermal transient* (T31) with the weld source, plus **Fixed
support** or **Displacement** and a **Thermal stress** (reference = initial
temperature) in the same model; a material with *Young's modulus*, *Poisson's ratio*
and *Thermal expansion coefficient*. CCX > Custom model definition (next to the
`ASTER-LASBRON` lines):

```
** ASTER-MATERIAL Steel: TC=(20, 600, 1200, 1500), E=(210e9, 120e9, 15e9, 10e9),
** ASTER-MATERIAL     SY=(355e6, 150e6, 15e6, 10e6), H=1e9,
** ASTER-MATERIAL     ALPHA=(1.2e-5, 1.35e-5, 1.5e-5, 1.5e-5), TC_CUT=1500
```

The bridge writes into the `.comm` (after the thermal solve, with `res_ther` = the
thermal result; temperatures in °C):

```
MAT_1_E = DEFI_FONCTION(NOM_PARA='TEMP', VALE=(
    20.0, 210000000000.0,
    600.0, 120000000000.0,
    ...), PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')
...
MAT_1 = DEFI_MATERIAU(
    ELAS_FO=_F(E=MAT_1_E, NU=MAT_1_NU, RHO=MAT_1_RHO, ALPHA=MAT_1_ALPHA, TEMP_DEF_ALPHA=20.0),
    ECRO_LINE_FO=_F(D_SIGM_EPSI=MAT_1_ET, SY=MAT_1_SY),
)
fieldmat = AFFE_MATERIAU(MAILLAGE=mesh, MODELE=model, AFFE=(...),
    AFFE_VARC=_F(TOUT='OUI', NOM_VARC='TEMP', EVOL=res_ther, NOM_CHAM='TEMP', VALE_REF=20.0),
)
res = STAT_NON_LINE(..., COMPORTEMENT=_F(GROUP_MA='Plaat', RELATION='VMIS_ISOT_LINE',
    DEFORMATION='PETIT'), INCREMENT=_F(LIST_INST=listinst), ARCHIVAGE=_F(LIST_INST=times), ...)
```

Result (verification WE-09, uniaxially restrained bar with its own `#ASTER-MATERIAL`
values: E, SY and α linear in T):
`DIAGNOSTIC JOB : OK`, the stress elastic, plastic, during cooling and the residual
stress (= SY(T0) after reverse yielding) equal to the hand calculation to 4·10⁻⁸;
WE-10 (weld bead on a plate): [`Welding.md`](Welding.md) §9.5.

Pitfalls:
- The name before the `:` is the **Mecway material name** (exactly); an unknown name
  gives an ERROR listing the known names.
- `ALPHA` is the mean (secant) coefficient from `T_ALPHA` (default the reference
  temperature), not the instantaneous one.
- `H` is Mecway's *tangent modulus* (plastic modulus); `ET` the slope in total strain
  (Code-Aster `D_SIGM_EPSI`); give one of them.
- In welding always set `TC_CUT` (the thermal strain freezes above the melting
  temperature).

### Example 18 – Adaptive refinement per model (`#ASTER-OPTIE`)

Goal: switch on the refinement loop in one model with a lower target for a peak
stress, without changing the page *Static* (explanation:
[`Error_estimator.md`](Error_estimator.md) §6). Mecway: *Static*, solid elements
(preferably hex20), constraints and loads on face selections. CCX > Custom model
definition:

```
** ASTER-OPTIE adapt_refine = ja
** ASTER-OPTIE adapt_target_error = 1.5
** ASTER-OPTIE adapt_select = fraction
** ASTER-OPTIE adapt_fraction = 0.1
```

Outcome (checked offline with `bridge_custom.parse` and `bridge_adapt.adapt_settings`):
the loop is on with target 1.5% and refines the 10% of elements with the largest error
in each loop; the other settings (max. 5 loops, 200 000 elements) stay those of the
page. Without `adapt_select`/`adapt_fraction` the loop selects with Dörfler 0.5
(verification AD-02).

### Example 19 – Fatigue: block spectrum on a static run (`#ASTER-WOHLER`, `#ASTER-BLOCK`)

Goal: damage and life of a bar with a two-level spectrum, Basquin curve and Goodman
correction (explanation: [`Fatigue.md`](Fatigue.md)). Mecway: *Static 3D* with the
load of "one unit" (here a traction of 100 MPa) and material `Steel`. CCX > Custom
model definition:

```
** ASTER-WOHLER Steel: Sf = 900 MPa, b = -0.1, Su = 600 MPa, correction = GOODMAN
** ASTER-FATIGUE repeats = 5
** ASTER-BLOCK 1.5, 0.5, 1e4
** ASTER-BLOCK 0.8, 1.0, 2e5
```

Per repetition 10⁴ cycles 100 ± 150 MPa (amplitude 1.5 and mean 0.5 × the static
stress) and 2·10⁵ cycles 100 ± 80 MPa; the spectrum occurs 5 times. In the `.comm`
after `CALC_CHAMP`:

```
import aster_fatigue
_bridge_vermoeiing = aster_fatigue.compute(
    res, r'...\model.liml', r'...\model_<run>_vermoeiing.csv',
    [{'material': 'Steel', 'form': 'basquin', 'Sf': 900000000.0, 'b': -0.1,
      'Su': 600000000.0, 'correction': 'GOODMAN'}],
    {'stress': 'VMIS_SG', 'counting': 'RAINFLOW', 'repeats': 5.0, ...},
    blocks=[(1.5, 0.5, 10000.0), (0.8, 1.0, 200000.0)], signal=None, shells=None)
```

Result (verification VM-02b): D = 4.329·10⁻³ and `life` 1155 repetitions at every
node, equal to the hand calculation (Goodman S_eq = S_a/(1 − S_m/S_u), Basquin, Miner
× 5) within 10⁻⁶; status box: "Fatigue: largest damage D = 0.004329 ...".

### Example 20 – Fatigue: the history of a nonlinear run (`#ASTER-WOHLER`)

Goal: rainflow on the stress history of every node, with a Wöhler table (here the
linear curve of Code-Aster test case szlz105a, N = 1000 − 100 S with S in MPa).
Mecway: *Nonlinear static 3D*, a traction with a time table 0, 3, 1, 4, 2, 4, 1, 2,
−3 MPa at t = 0 … 8 s. CCX > Custom model definition:

```
** ASTER-WOHLER Steel: S = [0, 10] MPa, N = [1000, 0], INTERPOL = LIN
```

No `#ASTER-BLOCK`/`-SIGNAL`: all time steps of `STAT_NON_LINE` are the signal.
Result (verification VM-04): D = 4.8133·10⁻³ (szlz105a: `VALE_REFE` 4.8133·10⁻³),
equal to `CALC_FATIGUE CUMUL_DOMMAGE` on the same result (10⁻⁶); the cycle table
`<model>_<run>_vermoeiing.csv` has 4 cycles (ranges 7, 2, 2 and 1 MPa, the last two
at means 3 and 1.5 MPa).

### Example 25 – Metallurgy with your own CCT diagram (`#ASTER-METALLURGIE`)

Goal: phases (ferrite .. martensite) and hardness after cooling, for a steel whose CCT
(TRC) diagram you have yourself (without one: `staal=16MND5`,
[`Welding.md`](Welding.md) §10.3). Mecway: *Thermal transient* (T31) with the cooling
(or a weld source, example 13). CCX > Custom model definition: the `DEFI_TRC` as
`#ASTER` code (per cooling history: cooling rate at 700 °C [°C/s], grain size, six
coefficients and then groups of four Z_ferrite, Z_pearlite, Z_bainite, T [°C]; syntax
as in the test cases hsnv101a and mtlp103a) and the line `#ASTER-METALLURGIE` with the
`META_ACIER` values (verification MT-08):

```
** ASTER TRC_EIGEN = DEFI_TRC(
** ASTER     HIST_EXP=(
** ASTER         _F(VALE=(-100.0, 11.0, 0., 0., 0., 0., 0., 0.,
** ASTER                  0., 0., 0., 830.0)),
** ASTER         _F(VALE=(-400.0, 11.0, 0., 0., 0., 0., 0., 0.,
** ASTER                  0., 0., 0., 830.0)),
** ASTER     ),
** ASTER     TEMP_MS=_F(SEUIL=0.38, AKM=-30.791, BKM=11.698, TPLM=-1.0),
** ASTER )
** ASTER-METALLURGIE Staal: trc=TRC_EIGEN, AR3=830, MS0=300, ALPHA=-0.011,
** ASTER-METALLURGIE     AC1=724, AC3=846, TAUX_1=0.34, TAUX_3=0.34, begin=austeniet
```

The bridge then puts `META_ACIER` in a separate material (the `DEFI_TRC` is in the
`.comm` after the thermal materials) and computes after the thermal solve:

```
meta_mat1 = DEFI_MATERIAU(META_ACIER=_F(TRC=TRC_EIGEN, AR3=830.0, ALPHA=-0.011, MS0=300.0, ...))
fieldmat_meta = AFFE_MATERIAU(MAILLAGE=mesh, MODELE=model, AFFE=(_F(GROUP_MA=('Staaf',), MATER=meta_mat1),))
meta_init = CREA_CHAMP(OPERATION='AFFE', TYPE_CHAM='CART_VAR2_R', MAILLAGE=mesh, AFFE=(
    _F(GROUP_MA=('Staaf',), NOM_CMP=('V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7'),
       VALE=(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)),))
res = CALC_META(reuse=res, RESULTAT=res, MODELE=model, CHAM_MATER=fieldmat_meta,
    ETAT_INIT=_F(META_INIT_ELNO=meta_init),
    COMPORTEMENT=_F(RELATION='ACIER', GROUP_MA=('Staaf',)), OPTION=('META_ELNO', 'META_NOEU'))
```

Result (MT-08, cooling 900 → 20 °C at 100 °C/s): martensite = 1 − exp(−0.011·(300 −
T)) to 3·10⁻⁸; alarm `RESULT1_39` (a different material than in the result) is
intended here.

Pitfalls:
- `ALPHA` is **negative** (Code-Aster: Z_M = 1 − exp(ALPHA·(Ms − T))); a positive
  value gives an ERROR.
- With `trc=` the values `AR3`, `ALPHA`, `MS0`, `AC1`, `AC3`, `TAUX_1` and `TAUX_3`
  are required (°C and s); the name before the `:` is the Mecway material name.
- For welding keep `TAUX_1`/`TAUX_3` small (0.001 s), otherwise the austenitisation lags
  behind ([`Welding.md`](Welding.md) §10.5).

### Example 23 – Filler material that is born, two layers (`#ASTER-LASBRON birth=`)

Goal: a bead in two layers whose filler only takes part once the source passes (heat
storage, stiffness and stress only after birth; explanation:
[`Welding.md`](Welding.md) §11). Mecway: *Thermal transient* (T31) with an initial
temperature; each layer an element selection or component `LASNAAD_1`, `LASNAAD_2`
that shares nodes with the base material; for the residual stress also Thermal stress,
supports and `#ASTER-MATERIAL` (example 17). CCX > Custom model definition:

```
** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.0015), direction=(1, 0, 0), length=0.02
** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetry=1, birth=<<LASNAAD_1>>
** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.003), direction=(1, 0, 0), length=0.02, t0=6
** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetry=1, birth=<<LASNAAD_2>>
```

The bridge writes in the `.comm` (thermal, `THER_LINEAIRE`):

```
gb_tb = CREA_CHAMP(TYPE_CHAM='CART_NEUT_R', OPERATION='AFFE', MAILLAGE=mesh, AFFE=(
    _F(GROUP_MA='TH2', NOM_CMP='X1', VALE=0.1), ...))     # middle of the birth step
MTH1_GB_L = FORMULE(VALE='L if INST > NEUT1 else L * Q * Q', NOM_PARA=('INST', 'NEUT1'), L=30.0, Q=0.0001)
MTH1_GB_C = FORMULE(VALE='C if INST > NEUT1 else C * Q', NOM_PARA=('INST', 'NEUT1'), C=4680000.0, Q=0.0001)
MTH1_GB = DEFI_MATERIAU(THER_FO=_F(LAMBDA=MTH1_GB_L, RHO_CP=MTH1_GB_C))
fieldmat = AFFE_MATERIAU(..., AFFE=(..., _F(GROUP_MA='TH..', MATER=MTH1_GB)),
    AFFE_VARC=_F(GROUP_MA='TH..', NOM_VARC='NEUT1', CHAM_GD=gb_tb))
LBS1 = FORMULE(VALE='(_lb_goldak(X, Y, Z, INST, _LB1) + _lb_goldak(X, Y, Z, INST, _LB2)) '
               'if _lb_born(X, Y, Z, INST, _GB2) else 0.0', ...)
lasbron = AFFE_CHAR_THER_F(MODELE=model, SOURCE=(_F(GROUP_MA='TH..', SOUR=LBS1), ...))
```

and mechanically a loop of `STAT_NON_LINE` per birth step (quiet material `MAT_1_Q` with
E × 1e-4; at birth the normal material and stress/internal variables set to zero via
`ETAT_INIT`).

Outcome (verification WE-13, half plate 30 × 8 × 4 mm with two layers, 1 140 hex8, 150
steps): `DIAGNOSTIC JOB : OK`, layer 2 stress-free and at the initial temperature until
its birth, layer 1 reheated by layer 2, residual stress in equilibrium with tension in
the bead. WE-11 (bead in two pieces): energy of the living volume within 0.8%.

Pitfalls:
- Each layer its own selection (`birth=<<..>>`); `birth=yes` only with one source.
- With `birth` the source acts on all elements near the path (also the base material),
  not only on `LASNAAD_`.
- Mecway's own solver has no birth; comparing with Mecway is only possible without it.

### Example 29 – Fracture mechanics with XFEM: a crack without a mesh (`#ASTER-XFEM`)

Goal: K and G along a crack that is not in the mesh (explanation:
[`Fracture_mechanics.md`](Fracture_mechanics.md) §7). Mecway: *Static 3D*, an
uncracked block of solid elements, fine (h ≈ a/20) around the location of the front.
CCX > Custom model definition (verification BR-10, penny-shaped crack with radius
20 mm in the plane z = 0):

```
** ASTER-XFEM shape=CIRCLE, centre=(0, 0, 0), r=20 mm, normal=(0, 0, 1), name=penny
```

Other shapes (every line with `shape=` is a new crack; a line without `shape=`
continues the previous one):

```
** ASTER-XFEM shape=HALF_PLANE, point=(0.05, 0, 0), normal=(0, 1, 0),
** ASTER-XFEM     direction=(1, 0, 0)
** ASTER-XFEM shape=RECTANGLE, centre=(0, 0, 0.025), a=0.05, b=0.05,
** ASTER-XFEM     vect_x=(1, 0, 0), vect_y=(0, 0, 1)
** ASTER-XFEM shape=ELLIPSE, centre=(0, 0, 0), a=2, b=2, vect_x=(1, 0, 0),
** ASTER-XFEM     vect_y=(0, 1, 0), smoothing=LAGRANGE, points=20
```

In the `.comm` (before the loads; `model_sain` is the bridge's model):

```
fiss_1 = DEFI_FISS_XFEM(
    MAILLAGE=mesh,
    TYPE_DISCONTINUITE='FISSURE',
    DEFI_FISS=_F(FORM_FISS='ELLIPSE', DEMI_GRAND_AXE=0.02, DEMI_PETIT_AXE=0.02,
                     CENTRE=(0.0, 0.0, 0.0), VECT_X=(1.0, 0.0, 0.0),
                     VECT_Y=(0.0, 1.0, 0.0)),
)
model = MODI_MODELE_XFEM(MODELE_IN=model_sain, FISSURE=(fiss_1,))
```

and after the export per front `CALC_G_XFEM` and `POST_K1_K2_K3`
(Fracture_mechanics.md §7.3). Result (BR-10): K_I from `POST_K1_K2_K3` 0.1622
MPa·√m (analytical 2σ√(a/π) = 0.1596: +1.6 %), from `CALC_G_XFEM` +5.3 % (no
curvature correction, WARNING); the last ELLIPSE line with `#ASTER-OPTIE
fracture_r_inf/_sup` is forma07b (BR-11, equal to the test case); `DIAGNOSTIC JOB :
<A>_ALARM` (`QUALITY1_1`: XFEM is not qualified for safety studies in Code-Aster,
and `XFEM_63`: small shift of the level set; both harmless,
[`CodeAster_error_messages.md`](CodeAster_error_messages.md#xfem_63-quality1_1-modele1_63--xfem-alarms)).

Without an `#ASTER-XFEM` line: a crack of any shape on a layer of nodes is a face
selection `XFEM_<name>` with the faces in the crack plane (DEFI_FISS
`GROUP_MA_FISS`/`GROUP_MA_FOND`, Fracture_mechanics.md §7.8, BR-13). With the setting
*MED file for ParaView* the bridge also writes `<model>_<run-id>_xfem.rmed`, the mesh
that follows the crack with `DEPL`, `SIGM_NOEU` and `SIEQ_NOEU` (§7.9, BR-14).

### Example 35 – Multiaxial fatigue: Dang Van on a static run (`#ASTER-FATIGUE criterion`)

Goal: damage with the critical-plane criterion of Dang Van under tension + shear
(explanation: [`Fatigue.md`](Fatigue.md) §1.7). Mecway: *Static 3D* with the load of
"one unit" (here σ_xx = 120 MPa and τ_xy = 80 MPa as tractions on the faces) and
material `Staal`. CCX > Custom model definition:

```
** ASTER-WOHLER Staal: S = [100, 150, 250, 400] MPa, N = [1e7, 2e6, 2e5, 1e4]
** ASTER-FATIGUE criterion = DANG_VAN, a = 0.3, b = 110 MPa, c = 1.5
** ASTER-SIGNAL 0, 1, 0, -1, 0
```

The bridge builds a result with five time steps from the static stress and strain
(signal × the static state) and lets Code-Aster search the critical plane. In the
`.comm` after `CALC_CHAMP` (shortened):

```
res = CALC_CHAMP(reuse=res, RESULTAT=res, GROUP_MA=('Kubus', ), DEFORMATION=('EPSI_NOEU', ))
_FW1 = DEFI_FONCTION(NOM_PARA='SIGM', INTERPOL='LOG', PROL_GAUCHE='EXCLU', PROL_DROITE='CONSTANT', VALE=(...))
_FM1 = DEFI_MATERIAU(ELAS=_F(E=210000000000.0, NU=0.3), FATIGUE=_F(WOHLER=_FW1),
                     CISA_PLAN_CRIT=_F(CRITERE='DANG_VAN_MODI_AC', D_VAN_A=0.3, D_VAN_B=110000000.0, COEF_CISA_TRAC=1.5))
_FCM = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=(_F(GROUP_MA=('Kubus', ), MATER=_FM1), ))
...                                   # _fat_resu: CREA_RESU with SIGM_NOEU and EPSI_NOEU x factor
_FRES = [(_fat_resu([0.0, 1.0, 0.0, -1.0, 0.0]), 1.0)]
_FCHAM = [(CALC_FATIGUE(TYPE_CALCUL='FATIGUE_MULTI', OPTION='DOMA_NOEUD', TYPE_CHARGE='PERIODIQUE',
                        RESULTAT=r_, CHAM_MATER=_FCM, MAILLAGE=mesh, GROUP_MA=('Kubus', ),
                        CRITERE='DANG_VAN_MODI_AC', METHODE='CERCLE_EXACT'), n_) for r_, n_ in _FRES]
_bridge_vermoeiing = aster_fatigue.compute_multi(_FCHAM, ...)
```

Result (verification VM-09a): `fatigue_eq` = 168.0 MPa = 1.5 · (100 + 0.3 · 40) (the
largest shear stress R = √(60² + 80²) = 100 MPa, P_max = 120/3 = 40 MPa),
`fatigue_ratio` = 112/110 = 1.018 (just above the fatigue limit of the criterion),
D = 8.333·10⁻⁷ per repetition (N(168 MPa) from the table), all within 10⁻⁵ of the hand
calculation. With `loading = NON_PERIODIC` Code-Aster counts the cycles on the
critical plane itself (rainflow); with `#ASTER-BLOCK` each block is a cycle of its own.

### Example 36 – Fatigue: strain life (Manson-Coffin) with plasticity

Goal: low-cycle fatigue of a bar with an imposed elongation of ±0.6 mm on 100 mm
(ε_a = 0.006) and a bilinear plastic material (yield strength 250 MPa). Mecway:
*Nonlinear static 3D*, imposed displacement with a time table 0, +0.6, −0.6, 0 mm at
t = 0, 1, 2, 3 s (step 0.25 s); on the Nonlinear page *Deformation* = `PETIT` (see
[`Fatigue.md`](Fatigue.md) §1.9). CCX > Custom model definition:

```
** ASTER-WOHLER Staal: Sf = 900 MPa, b = -0.09, ef = 0.3, c = -0.55
```

(`#ASTER-FATIGUE strain = PRIN` is the default: the principal strain with the largest
absolute value, here the axial strain.) In the `.comm` after `CALC_CHAMP`:

```
res = CALC_CHAMP(reuse=res, RESULTAT=res, GROUP_MA=('Staaf', ), DEFORMATION=('EPSI_NOEU', ))
_bridge_vermoeiing = aster_fatigue.compute(
    res, r'...\model.liml', r'...\model_<run>_vermoeiing.csv',
    [{'material': 'Staal', 'form': 'strain', 'Sf': 900000000.0, 'b': -0.09, 'ef': 0.3, 'c': -0.55,
      'correction': 'GEEN', 'E': 210000000000.0}],
    {'stress': 'VMIS_SG', 'counting': 'RAINFLOW', 'repeats': 1.0, 'strain': 'PRIN', ...},
    blocks=None, signal=None, shells=None)
```

E comes from the Mecway material (210 GPa). Result (verification VM-11a): the cycle
table has one cycle with strain amplitude 0.006000; N = 1347 from
0.006 = 900/210000 · (2N)^−0.09 + 0.3 · (2N)^−0.55 and D = 7.426·10⁻⁴ per repetition,
within 2·10⁻⁹ of the hand calculation. Shells work without an extra line: an
`#ASTER-WOHLER` for the plate material gives `damage_top` and `damage_bottom` (VM-10).

## 6. Overview of the checks

Computed on 06-10-2026 with the bridge (code of commit ac20b66; the *Modal*,
*Buckling* rows with `#ASTER-EXCIT` in the matrices with commit 41bcf1e) and
Code-Aster 17.4.0, offline: `.liml` with the lines in the field named → `bridge_from_liml`,
`bridge_mesh`, `bridge_to_aster` → `run_aster` → `bridge_run_aster.aster_mess_errors`.

Checked again on 07-10-2026 (integral check S11, code of commit 8742df0): the lines of
§5 taken literally from this text, in the verification models named with each example,
or (examples 1 to 9) in the models A, C, S and R. Examples 1 to 8 were then computed
again (07-10-2026, code of commit bfb1e8e plus the messages of step S12) in the models
A, C and S of `TestFiles/Voorbeelden/` (`maak_voorbeelden.py --run`); the numbers in §5
and in this table come from those runs. Model R (example 9) is not in the repository.
Code-Aster without `<F>` (and,
where the model is the same, with the results above) for examples 1 (*Static*, *Nonlinear static*, *Dynamic
(implicit)*, *Modal*, *Buckling*), 2 to 17, 19, 20, 23, 25, 27, 29, 35 and 36, and for
`#ASTER-BEZWIJKEN` (`TestFiles/BezwijkenTrekstaaf.liml`); example 18 offline. Examples
17 and 23 run without errors in WE-09 and WE-13, but with other values than those
verifications (which have their own lines). The English keys of this version
(`direction`, `symmetry`, `birth`, `shape=CIRCLE`, `correction`, `repeats`,
`criterion`, ...) give the same `.comm` as the Dutch ones. The error messages in the
last column were provoked with a deliberately wrong line.

| # | Example | Field | Analysis/analyses | Result |
|---|---|---|---|---|
| 1 | `LIAISON_ELEM` 3D_POU | OpenRadioss, CCX (both fields) | Static, Nonlinear static, Dynamic (implicit) | OK |
| 1 | same, without `#ASTER-EXCIT` | OpenRadioss | Static / Nonlinear static | `FACTOR_11` (model A, `solver_nprec` 8, 08-10-2026; with -1 `FACTOR_57`) / `MECANONLINE9_4` (expected) |
| 1 | same | OpenRadioss | Modal, Buckling | OK: Modal f1 = f2 = 2855.4 Hz (pair, Y/Z); Buckling ±363.5 and ±993.3 (model A) |
| 1 | same, rigid block (model A, block E = 2.1·10¹⁸ Pa) | OpenRadioss | Modal | f1 = f2 = 2894.35 Hz; analytical 2894.3 Hz (clamped tube 8/6 mm, L = 50 mm, 5 beam elements) |
| 3, 4 | `FORCE_NODALE` + `DDL_IMPO` / `AFFE_CHAR_MECA_F` in `#ASTER-EXCIT` | Mystran + OpenRadioss / OpenRadioss | Modal, Buckling | OK (the run completes; the loads are also in `CHARGE` of `ASSEMBLAGE`) |
| 2 | `LIAISON_MAIL` COQUE_MASSIF | Mystran | Static, Nonlinear static | OK (0.00897 mm, model S) |
| 3 | `FORCE_NODALE` + `DDL_IMPO` | Mystran + OpenRadioss | Static, Nonlinear static | OK |
| 4 | `AFFE_CHAR_MECA_F` + `DEFI_FONCTION` | OpenRadioss (both fields) | Nonlinear static (Static: load 0) | OK |
| 5 | penalty + `ALGO_RESO_GEOM` | OpenRadioss | Nonlinear static with contact | OK (42.36 kN, model C; without 47.41 kN) |
| 5 | same with *Contact method* = PENALISATION | OpenRadioss | same | `SyntaxError` (expected, §4) |
| 6 | `CONTACT_INIT`, `POINT_FIXE`, `#ASTER-OPTIE` | OpenRadioss | Nonlinear static with contact | OK; unknown key gives ERROR |
| 7 | reaction force, `POST_RELEVE_T` + `IMPR_TABLE` | OpenRadioss | Nonlinear static; Static with `NUME_ORDRE=1` | OK |
| 8 | `EXTREMA` of `SIEQ_NOEU` | OpenRadioss | Static, Nonlinear static | OK |
| 9 | rigid rotation 90 degrees, `FORMULE` + `DDL_IMPO` | CCX | Nonlinear static, GROT_GDEP | OK (exact) |
| 10 | `#ASTER-OPTIE` `crit_stab`, `imperfection_*` (run 06-10-2026, step S10c) | CCX | Nonlinear static | OK (equal to NK-03) |
| 11 | `#ASTER-SPECTRE` with `DEFI_NAPPE` and `#ASTER-OPTIE` (run 07-10-2026, step S10e) | CCX | Response spectrum | OK (equal to sdld25a, SP-01); a malformed line (`#ASTER-SPECTRE Q = x`) gives an ERROR |
| 12 | `#ASTER-BRON` with phase, `#ASTER-OPTIE harm_freq_list` (run 07-10-2026, step S3a) | CCX | Acoustics (harmonic) | OK (verification AH-08) |
| 13 | `#ASTER-LASBRON` (run 07-10-2026, step S4a) | CCX | Thermal transient | OK (WE-02; also a kinked `path`, `group`, `LASNAAD_` and the error messages of [`Welding.md`](Welding.md) §8) |
| 14 | `#ASTER-OPTIE vibro_freq_min` (run 07-10-2026, step S3b) | CCX | Vibroacoustics (modes) | OK (verification VA-05c) |
| 27 | `#ASTER-BRON` with a pressure (incident wave) and with a velocity, `#ASTER-OPTIE harm_freq_list` (run 07-10-2026, step S3c) | CCX | Vibroacoustics (harmonic) | OK (verification VH-07, VH-08); a line without a number gives an ERROR |
| 15 | `#ASTER-FASE`, table as a function of frequency, `#ASTER-OPTIE harm_freq_list` (run 07-10-2026, step S10h) | CCX | Harmonic response | OK (verification HR-04); an unknown selection or a line without `=` gives an ERROR |
| 16 | `#ASTER-OPTIE fracture_r_inf`/`fracture_r_sup` with `CRACK_` selections (run 07-10-2026, step S6a) | CCX | Static | OK (verification BR-04) |
| 17 | `#ASTER-MATERIAL` with `#ASTER-LASBRON` (run 07-10-2026, step S4b) | CCX | Thermal transient with Thermal stress (thermal → mechanical chain) | OK (WE-09, WE-10; an unknown key or material name and lists of unequal length give an ERROR) |
| 19 | `#ASTER-WOHLER` (Basquin, Goodman), `#ASTER-VERMOEIING`, `#ASTER-BLOK` (run 07-10-2026, step S8) | CCX | Static | OK (verification VM-02b) |
| 20 | `#ASTER-WOHLER` (table, `INTERPOL = LIN`) with the history of the run (run 07-10-2026, step S8) | CCX | Nonlinear static | OK (verification VM-04, szlz105a) |
| 23 | `#ASTER-LASBRON` with `birth=` (run 07-10-2026, step S4c) | CCX | Thermal transient, also with Thermal stress (chain) | OK (WE-11, WE-11b, WE-12, WE-13; `birth=yes` with two sources and a selection without `<< >>` give an ERROR) |
| 25 | `#ASTER-METALLURGIE` with a `DEFI_TRC` in `#ASTER` code (run 07-10-2026, step S5) | CCX | Thermal transient | OK (MT-08; also `staal=16MND5`/`HSNV101A` and `mechanica=ja`, MT-01 .. MT-07; an unknown dataset, `trc` without the `META_ACIER` values or `ALPHA` > 0 give an ERROR) |
| 29 | `#ASTER-XFEM` (CIRCLE, HALF_PLANE, RECTANGLE, ELLIPSE with `smoothing`/`points`) and `#ASTER-OPTIE fracture_r_inf`/`_sup` (run 07-10-2026, step S6b) | CCX | Static | OK (verification BR-07..12; a crack outside the model, an unknown `group`, R_INF ≥ R_SUP and an unknown key give an ERROR) |
| – | `#ASTER-POST` with `EXTREMA` | OpenRadioss | Thermal, Dynamic (explicit) | OK |
| – | `$ ASTER` (space), `#ASTER-FOO`, `#ASTER_EXCIT`, unknown `<<selection>>` | Mystran, OpenRadioss | Static | OK / ERROR in the log as described |

## 7. Assumptions

- The lines are placed in the `.comm` in the order of §1; the bridge does not check the
  Code-Aster syntax.
- The results in §5 apply to the small test models named; they show that the lines work,
  not that the mesh has converged.
- Where a requirement of the U documentation has not been checked in the 17.4 catalogue
  or with a run, it says "NOT verified".

## 8. References

- EDF R&D (2026a). *code_aster 17.4.0, command catalogue*. Installation
  `code_aster/v2025/17.4/lib/aster/code_aster/Cata/Commands/` (`affe_char_meca.py`,
  `affe_char_meca_f.py`, `defi_contact.py`, `defi_fonction.py`, `formule.py`,
  `post_releve_t.py`, `impr_table.py`, `crea_champ.py`, `defi_group.py`).
- EDF R&D (2026b). *code_aster 17.4.0, message catalogue*. Installation
  `code_aster/v2025/17.4/lib/aster/code_aster/Messages/`.
- EDF R&D (2021a). *Opérateur AFFE_CHAR_MECA*. Code_Aster documentation U4.44.01. Local
  PDF in `Code_Aster_documentation/important documents/` (created 17-12-2021; older than
  17.4).
- EDF R&D (2021b). *Opérateur DEFI_CONTACT*. Code_Aster documentation U4.44.11. Local PDF
  (created 18-12-2021; older than 17.4).
- EDF R&D (2021c). *Opérateur POST_RELEVE_T*. Code_Aster documentation U4.81.21. Local
  PDF (created 18-12-2021; older than 17.4).
- EDF R&D (2021d). *Opérateur ASSEMBLAGE*. Code_Aster documentation U4.61.21. Version
  "default", 03-11-2021 (local copy; older than 17.4).
- Mecway (2026). *Mecway Finite Element Analysis – Manual*, version 33.
  `C:\Program Files\Mecway\manual.pdf`.
