# Instellingen voor contact en niet-lineaire analyses

*English version: [Settings_contact_and_nonlinear.md](en/Settings_contact_and_nonlinear.md)*

Voor wie Mecway kent en nieuw is in Code-Aster. Dit document beschrijft wat de
bridge werkelijk in de `.comm` van een run (`<model>_<run-id>.comm`, zie
[Handleiding §5](Handleiding.md#5-bestanden-in-de-werkmap)) zet, en welke
Code-Aster-opties er verder bestaan. Bij twijfel is de code leidend. Code-Aster-versie: 17.4.

Waarom elke standaardwaarde zo gekozen is, met het bewijs per instelling:
[`Standaardinstellingen_en_aannames.md`](Standaardinstellingen_en_aannames.md).
Verwijzingen als (EDF R&D, U2.04.04 §4.1) zijn het documentnummer en de paragraaf van
de Code-Aster-documentatie; de volledige gegevens staan in §5. "Catalogus" is de
syntaxdefinitie van de geïnstalleerde Code-Aster 17.4 (`code_aster/Cata`), de bron
voor standaardwaarden. Test-id's als NL-01 verwijzen naar [Verificatie.md](Verificatie.md),
R-... naar de controleruns in [Standaardinstellingen_en_aannames.md](Standaardinstellingen_en_aannames.md) §5.

---

## 1. Overzicht

### Welke analyse wordt welk Code-Aster-commando

| Mecway-analyse | Bridge-analyse (`active_analysis`) | Code-Aster | Tijdsintegratie |
|---|---|---|---|
| S30, lineair statisch | `lin_static_3d` | `MECA_STATIQUE` | geen |
| L30, niet-lineair statisch | `nonlin_static_3d` | `STAT_NON_LINE` | pseudo-tijd, Newton per stap |
| D31, dynamisch, impliciet | `dyna_impl_3d` | `DYNA_NON_LINE` | HHT (of NEWMARK), Newton per stap |
| D31, dynamisch, expliciet | `dyna_expl_3d` | `DYNA_NON_LINE` | DIFF_CENT (of TCHAMWA), geen iteraties |
| D30, lineair dynamisch (zonder *Mode superposition*) | `dyna_impl_3d` | `DYNA_NON_LINE` | NEWMARK met `deformation` `PETIT` = Mecway's schema (anders WARNING) |
| D30 met *Mode superposition* | `dyna_modal_3d` | `CALC_MODES` + `DYNA_VIBRA` `GENE` | NEWMARK per mode ([Respons_op_modale_basis.md](Respons_op_modale_basis.md)) |

Met "Actieve analyse" = `auto` (standaard) volgt de bridge het analysetype in de
`.liml` (`bridge_utils.resolve_auto_analysis`): S30, L30, D30 en D31 zoals in de
tabel (D31 wordt altijd `dyna_impl_3d`), T30/T31 `ther_3d` ([Thermisch.md](Thermisch.md)),
V30 `modal_3d` (met een fluïdum-onderdeel `vibroacoustic_modes_3d`), B30 `buckling_3d`
([Modaal_en_knik.md](Modaal_en_knik.md)) en A30 `acoustic_modes_3d` (met een bron
`acoustic_harm_3d`; [Akoestiek.md](Akoestiek.md)). Een ander type stopt de bridge met
een melding. Expliciet dynamisch kies je zelf in het
startscherm.

Wat de niet-lineaire analyses ondersteunen:

- materiaal: `ELAS`; met plasticiteit `VMIS_ISOT_TRAC` (hardingscurve,
  Ramberg-Osgood, OpenRadioss `PLAS_TAB`), `VMIS_ISOT_LINE` of `VMIS_CINE_LINE`
  (bilineair); hyperelastisch (Neo Hooke, Mooney-Rivlin) `ELAS_HYPER` (§2.4);
  tension only `CABLE`, gap `DIS_CHOC`; balken met grote rotaties
  `ELAS_POUTRE_GR` (`elem_beam` = `POU_D_T_GD`, §2.9);
- contact: Mecway `contact2` wordt `DEFI_CONTACT` (§3); compression only
  `DEFI_CONTACT FORMULATION='LIAISON_UNIL'`;
- dynamica: beginsnelheid (Mecway `initialconditions/velocity`) wordt
  `ETAT_INIT=_F(VITE=...)`;
- tijdsafhankelijke lasten via `DEFI_FONCTION`.

### Waar je de instellingen vindt

- **Startscherm**, een pagina per analyse. Een veld verschijnt alleen als de
  sleutel in die analyse bestaat (`CONFIG_BRIDGE["analyses"]` in
  `Scripts/bridge_utils.py`, `ANALYSIS_SPECS` in `bridge_gui.py`):

| Groep (kopje op de pagina) | Sleutels | Analyses |
|---|---|---|
| Code-Aster-run | `time_limit`, `memory_limit` | alle |
| Oplosser | `solver_nprec`; `lin_solver`, `lin_solver_resi` | alle; `lin_solver` alleen statisch, `lin_solver_resi` statisch en de statische stap van modaal, knik en de imperfectie |
| Stappen en convergentie | `substeps_per_interval` (statisch), `newton_max_iter`, `newton_reac_iter`, `default_time_end`, `convergence_criterion`, `convergence_resi_rela`, `convergence_resi_maxi`, `line_search`, `auto_time_stepping` (statisch) | niet-lineair statisch, dynamisch impliciet; `default_time_end` ook expliciet |
| Contact | `contact_algo`, `contact_smoothing`, `contact_pene_maxi` | niet-lineair statisch, dynamisch impliciet (`contact_algo` ook expliciet) |
| Materiaal en kinematica | `plastic_strain_definition`, `deformation` | niet-lineair statisch, dynamisch |
| Tijdschema | `schema`, `hht_alpha`, `substeps_per_output` (impliciet), `explicit_dt_factor` (expliciet) | dynamisch |
| Bezwijken | `element_failure`, `failure_plastic_strain`, `failure_stiffness_factor` | niet-lineair statisch, dynamisch ([Bezwijken.md](Bezwijken.md)) |
| Controle | `energy_balance`; `error_estimator` | dynamisch impliciet; statisch |
| Niet-lineaire knik | `crit_stab`, `imperfection_amplitude`, `imperfection_mode`, `imperfection_unit` | niet-lineair statisch ([Modaal_en_knik.md](Modaal_en_knik.md) §5) |

- **Per model**: `#ASTER-OPTIE sleutel = waarde` (§3.9).

---

## 2. Instellingen

Legenda: **Bridge** = standaardwaarde in `bridge_utils.py`; **CA** =
Code-Aster-standaard als je het sleutelwoord weglaat (catalogus 17.4).

### 2.1 Tijdstappen

| Sleutel (label) | Analyse | Wat het doet | Bridge | CA |
|---|---|---|---|---|
| `substeps_per_interval` (Substappen per tijdsinterval) | statisch | Alleen voor een model zonder Mecway's *Time step size*: rekenstappen per interval tussen de tijdspunten van de tijdsafhankelijke lasten (`DEFI_LIST_REEL`, `NOMBRE`); zonder tijdslast 0 tot `default_time_end`. Met een stapgrootte rekent de bridge Mecway's stappen plus de knikken van de lasttabellen (§2.1). | 10 | - |
| `auto_time_stepping` (Mecway's Automatic time stepping volgen) | statisch | Alleen met Mecway's *Automatic time stepping*: aan = `DEFI_LIST_INST METHODE='AUTO'` tussen Mecway's uitvoertijden, resultaten op die tijden (§2.1); uit = vaste stappen. | aan | - |
| `substeps_per_output` (Rekenstappen per Mecway-tijdstap) | impliciet | Rekenstappen per tijdstap van Mecway: bij Dynamic Response (D30, D20, DA0) per *Time step size*, ook met *Generate solution every n time steps* > 1 (dan n × deze waarde per uitvoerinterval; resultaten alleen op de uitvoertijden); anders (D31, `timepointsincrement`) per uitvoerinterval. Knikpunten van lastfuncties komen er als extra tijdspunt bij. | 1 | - |
| `default_time_end` (Eindtijd zonder tijdsbelasting) [s] | alle | Eindtijd als het model geen tijdslast (statisch) of geen `<timesteps>` (dynamisch) heeft. | 1.0 | - |
| `explicit_dt_factor` (Tijdstap / kritieke tijdstap) | expliciet | Tijdstap ≤ factor × de kritieke tijdstap zoals de bridge die schat, per uitvoerinterval gelijk verdeeld (zo is elke uitvoertijd een rekenstap). | 0.5 | - |

**Statisch (`STAT_NON_LINE`).** Net als bij impliciete dynamica maakt de bridge een
`DEFI_LIST_INST` met automatisch knippen (zie hieronder); met alleen een
`DEFI_LIST_REEL` zou Code-Aster de stap niet verkleinen (EDF R&D, U4.51.03; melding
`SUBDIVISE_3`). Naar Mecway gaan (route `liml`) alle gearchiveerde rekenstappen tot
het laatst bereikte tijdstip (de bridge zet geen `ARCHIVAGE`), of (route `tabel`)
alleen dat laatste tijdstip. De rekenstappen zijn die van Mecway (*Time step size*,
`<timesteps stepsize>`: dt, 2 dt, ... tot de periode), plus de knikken van de
lasttabellen die ertussen vallen; zo staan in Mecway dezelfde tijdstippen als bij
Mecway's eigen solver. Lasttijden na de periode vallen weg. Staat Mecway's *Automatic time stepping* aan (`automatictimestepping="true"`, met de
interne solver naast *Time step size*, met CCX naast de *time points*), dan maakt de
bridge `DEFI_LIST_INST(METHODE='AUTO', DEFI_LIST=_F(LIST_INST=times, PAS_MINI=...,
PAS_MAXI=...))` (EDF R&D, U4.34.03; Aubry, 2019, §14.1) met hetzelfde `ECHEC` als
fallback. De tijden in de lijst zijn verplichte rekenpunten: Mecway's stappen of
*time points* plus de knikken van de lasttabellen; daartussen past Code-Aster de stap
aan (`ADAPTATION` standaard: groter na twee makkelijke stappen, `PAS_MAXI` = Mecway's
stap of *time-point*-interval, `PAS_MINI` = 1e-6 daarvan). `ARCHIVAGE` houdt alleen
Mecway's uitvoertijden (bij CCX de *time points*, zonder de knikken), zodat Mecway de
tijden krijgt die het verwacht. Geverifieerd: NL-21a (zelfde tijden en waarden als
NL-20) en NL-21b (*time points* 0,5 s: 6 in plaats van 30 rekenstappen, waarden
binnen 0,2 %). `auto_time_stepping` uit = vaste stappen zoals zonder de optie (met
een WARNING). Zonder de optie in Mecway verandert er niets. Met bezwijken van
elementen archiveert de bridge elke rekenstap. Bij een draagkrachtberekening tot
bezwijken kan de laatst geconvergeerde last iets verschuiven (NK-04 met de optie:
P_u/Pcr 0,480 in plaats van 0,488).
Alleen een model zonder stapgrootte gebruikt `substeps_per_interval`.

**Impliciet dynamisch.** De bridge maakt een `DEFI_LIST_INST` met:

```
ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE',
         SUBD_METHODE='MANUEL', SUBD_PAS=4, SUBD_NIVEAU=6)
```

- `EVENEMENT='ERREUR'` omvat o.a. te veel Newton-iteraties, mislukte integratie van
  de materiaalwet en een singuliere matrix (EDF R&D, U4.34.03, "Event ERREUR").
- `DECOUPE` met `SUBD_PAS=4`: de mislukte stap wordt in **4** gelijke stappen
  gedeeld (geen halvering). `SUBD_NIVEAU=6`: dat kan 6 keer genest, dus tot 1/4096
  van de oorspronkelijke stap.
- CA-standaard volgens de catalogus: `SUBD_PAS=4`, `SUBD_NIVEAU=3`. U4.34.03 noemt
  voor de automatisch toegevoegde `ERREUR` `SUBD_NIVEAU=4`; de catalogus zegt 3.
  Welke van de twee Code-Aster gebruikt, is NIET geverifieerd (de bridge zet hem
  toch expliciet op 6).
- Resultaten worden alleen op de uitvoertijden gearchiveerd (`ARCHIVAGE`), en
  alle uitvoertijden gaan naar Mecway.

**Hoeveel substappen.** Kleinere stappen maken een niet-lineair probleem meestal
makkelijker (EDF R&D, U2.04.01), maar niet altijd: NL-02a (grote doorbuiging,
elastisch) gaf met 1 substap per interval dezelfde uitkomst als met 10 (R-SUB1), en
NL-01 (plastische volumes) stopte met 40 substappen en `RESI_GLOB_RELA` 1e-6 al op
t = 0,013, omdat de restkracht van `GDEF_LOG` bij een kleine last boven 1e-6 van de
reactie blijft (R-SUB40; §2.2; met de standaard 1e-5 rekent hij door).

**Expliciet (`DIFF_CENT`).**

- Stabiliteit: de tijdstap moet onder de Courant-grens (CFL) blijven. Voor
  `DIFF_CENT` is de kritieke stap 2/ω_max (EDF R&D, U2.06.13).
- De bridge schat de kritieke stap als kleinste ribbe / drukgolfsnelheid
  `c = sqrt(E(1-ν)/(ρ(1+ν)(1-2ν)))` over alle elementen met een dichtheid. Dat is
  een schatting, niet de waarde van Code-Aster.
- Code-Aster berekent de CFL-grens zelf en stopt met `DYNAMIQUE_2` als een stap te
  groot is (`STOP_CFL='OUI'`, standaard; EDF R&D, U4.53.01). De bridge laat dat aan.
- **Factor en CFL-grens.** De factor geldt voor de schatting van de bridge. In DY-03a
  (hex8-kubussen van 10 mm, ν = 0) was de grens van Code-Aster de helft van die
  schatting (9,667e-7 s tegen 1,933e-6 s): de standaard 0,5 komt uit op de grens zelf
  (door de gelijke verdeling per uitvoerinterval 0,86 × de grens), en met 0,7 of meer
  weigert Code-Aster de run (R-DT). U2.06.13 raadt 0,5 tot 0,7 × de CFL-grens aan; dat
  is hier een factor 0,25 tot 0,35 (0,3 gaf in DY-03a dezelfde uitkomst binnen de
  tolerantie). Voor andere elementvormen is de verhouding NIET gemeten.
- De CFL wordt alleen aan het begin berekend (U2.06.13). Elementen die sterk
  krimpen, of penalty-contact, kunnen de grens verlagen: verlaag dan de factor.
- De bridge zet `MASS_DIAG='OUI'` (diagonale massa, aanbevolen in U4.53.01).
- Expliciet wordt de stap nooit automatisch verkleind (U2.06.13).
- **Geen mass scaling.** Een optie zoals `/DT/NODA/CST` in OpenRadioss (massa
  toevoegen om de stap te vergroten) staat niet in U4.53.01 en U2.06.13 (NIET
  gevonden). `COEF_MASS_SHIFT` is iets anders (M + coef·K, om een singuliere
  massamatrix inverteerbaar te maken). De stap volgt dus uit het kleinste element.
  Boven 2 000 000 stappen schrijft de bridge een WARNING; overweeg dan `dyna_impl_3d`.
- **Demping en discrete elementen.** Rayleigh-demping verkleint de stabiele stap:
  dt = (2/ω)(√(1+ξ²) − ξ) met ξ = α/(2ω) + βω/2 (Belytschko e.a., 2000; factor
  < 0,1: WARNING, overweeg `dyna_impl_3d`). Losse veren, dempers en knoopmassa's tellen
  mee (ω² = Σk(1/m_i + 1/m_j) per knoop); zonder elementen met materiaal kan
  Code-Aster de CFL niet zelf bepalen (`DYNAMIQUE_4`), dan zet de bridge
  `STOP_CFL='NON'`.
- **Opgelegde verplaatsing.** `DIFF_CENT`/`TCHAMWA` kennen alleen
  `FORMULATION='ACCELERATION'`: `DDL_IMPO` legt daar een versnelling op. De bridge zet
  een opgelegde verplaatsing, rotatie of snelheid ≠ 0 om naar de versnelling die het
  schema oplegt; op elke rekenstap klopt u(t) (DY-03b). Knikken in u(t) worden
  rekentijden; een waarde zonder tijdshistorie wordt in de eerste stap bereikt (stoot,
  WARNING). Een verplaatsing 0 blijft gewoon vast.
- **Schalen.** Expliciet met DKT gaf dezelfde trilling als impliciet (R-STRIP: periode
  +0,6 % ten opzichte van Euler-Bernoulli); de bridge zet geen `INER_ROTA`.

### 2.2 Newton en convergentie

| Sleutel (label) | Code-Aster | Bridge | CA | Wanneer aanpassen |
|---|---|---|---|---|
| `newton_max_iter` (Max. Newton-iteraties) | `CONVERGENCE/ITER_GLOB_MAXI` | 20 | 10 | Verhogen bij contact (`CONTINUE`): U4.51.03 zegt dat contact vaak meer iteraties vraagt. Heel veel iteraties wijst meestal op een modelfout of een te grote stap (U4.51.03). Met 1 substap had NL-02a 11 iteraties nodig (R-SUB1). |
| `newton_reac_iter` (NEWTON REAC_ITER) | `NEWTON/REAC_ITER` | 1 | 1 | Houd 1: tangentmatrix elke iteratie opnieuw (robuust, aanbevolen in EDF R&D, U2.04.01 en U2.04.04 §4.5.2). Met 0 stopte NL-02a in de eerste stap met `DVP_2` (R-REAC0); het startscherm accepteert daarom minimaal 1. |
| `convergence_criterion` (Convergentiecriterium) | `RESI_GLOB_RELA`, `RESI_GLOB_MAXI`, of beide met `VERIF='AU_MOINS_UN'` | `RELA` | `RELA` | Zie hieronder. |
| `convergence_resi_rela` (Convergentie RESI_GLOB_RELA) | `CONVERGENCE/RESI_GLOB_RELA` | 1e-5 (thermisch 1e-6) | 1e-6 | Relatief t.o.v. de opgelegde last plus reacties (U4.51.03). De bridge wijkt af van de CA-standaard 1e-6 omdat het residu daar bij plastische volumes (`GDEF_LOG`) op stagneert (zie hieronder). 1e-6 kan, eventueel met `RELA_OF_MAXI`. Verder niet losser maken: dat verbergt problemen. |
| `convergence_resi_maxi` (Convergentie RESI_GLOB_MAXI) [N] | `CONVERGENCE/RESI_GLOB_MAXI` | 1e-3 | - | Alleen met `MAXI` en `RELA_OF_MAXI`. `MAXI`: klein kiezen ten opzichte van de verwachte krachten. `RELA_OF_MAXI`: boven de absolute rest waarop het residu stagneert (kolom `RESI_GLOB_MAXI` in de `.mess`). |
| `line_search` (Lijnzoeken RECH_LINEAIRE) | `RECH_LINEAIRE` (`METHODE='CORDE'`, `ITER_LINE_MAXI=3`) | `auto` | uit | Newton schaalt elke correctie zodat het residu daalt (U2.04.01; catalogus `c_rech_lineaire.py` 17.4). `auto` = alleen bij kabels (`CABLE`, *Tension only*) en zonder contact, zoals Aubry (2019, §10.2) aanraadt. `on`: proberen als Newton heen en weer springt of stappen worden opgedeeld; het geconvergeerde resultaat verandert niet, een iteratie kost iets meer. Niet met contact `CONTINUE` (Code-Aster stopt met `MECANONLINE3_91`; de bridge laat het dan weg met een WARNING) en niet expliciet. Afgeraden bij balken met grote rotaties (`POU_D_T_GD`; met `on` wordt het toch geschreven, met een WARNING): met `on` stopten NL-81/83/84/85/90 zonder convergentie (`MECANONLINE9_7`) deelden NL-80/89 de stappen op in 1000-2000 substappen met 0,6-0,7% afwijking en week NL-82 7,6% af; de bridge waarschuwt dan. SaggingCable met *Tension only*: 7 in plaats van 9 Newton-iteraties, zelfde resultaat; NL-01/02/04 (volumes, `COQUE_3D`) en NL-86/87/88/90b met `on` binnen 4e-6 (S27). De keten thermisch-mechanisch (`bridge_thermomech`, `ITER_LINE_MAXI=5` bij plasticiteit) houdt zijn eigen lijnzoeken. |

**`RELA` of `MAXI`.** `RELA` = `RESI_GLOB_RELA`: grootste restkracht gedeeld door de
opgelegde last plus reacties. `MAXI` = `RESI_GLOB_MAXI`: grootste restkracht in N
(`convergence_resi_maxi`). Wordt de referentie van `RELA` nul (bijv. volledig
ontlasten), dan schakelt Code-Aster zelf over op een absoluut criterium, maar niet in
de eerste stap (U4.51.03, "Convergence settings"). Kies dus `MAXI` als de last en de
reacties vanaf het begin ~0 zijn (een opgelegde beweging zonder weerstand of
contactkracht): een starre translatie stopte met `RELA` in stap 1 en was met `MAXI`
1e-3 N exact (R-RIGID). Samples/PipeClip bleef met `RELA` in stap 1 hangen
(RESI_GLOB_RELA 1..13 bij ~1e-12 N) en rekent met `MAXI` 1e-3 N door.

**`RELA_OF_MAXI`.** De bridge zet dan beide criteria met `VERIF='AU_MOINS_UN'`:
geconvergeerd als het relatieve **of** het absolute criterium gehaald is (catalogus
`c_convergence.py` 17.4; U4.51.03). Zonder `VERIF` eist Code-Aster beide
(`VERIF='TOUT'`). Zo werkt ook CCX: een relatief criterium met een absolute
ondergrens bij kleine krachten. U4.51.03 waarschuwt dat `'AU_MOINS_UN'` een
onnauwkeurige uitkomst kan accepteren; kies `convergence_resi_maxi` dus niet groter
dan nodig: net boven de absolute rest waarop het residu stagneert (kolom
`RESI_GLOB_MAXI` in de `.mess` of het convergentiescherm, §4.4). Gemeten op NL-01 met
`RESI_GLOB_RELA` 1e-6: met `RESI_GLOB_MAXI` 0,05 N exact tot t = 3 (verificatiecase
NL-01b); met 1e-3 N niet, want de absolute rest stagneert op ~1e-2 N (R-ROM).

**Stagnatie met `GDEF_LOG`; waarom standaard 1e-5.** Bij plastische volumes
(`GDEF_LOG`, §2.3) blijft de restkracht steken: rond 5e-4 N bij een kleine last en
~1e-2 N bij het ontlasten (trekstaaf van NL-01, 12 kN; `RESI_GLOB_RELA` ~1,5…2,3e-6).
Met de CA-standaard 1e-6 is dat meer dan het criterium; de stap wordt geknipt, de last
nog kleiner, en de run stopt met `MECANONLINE9_7`. Gezien bij ontlasten (NL-01 stopte
op t = 2,92), met 40 substappen (stop op t = 0,013) en met een hardingscurve (stop op
t = 0,013). Met 1e-5 (NL-01, R-SUB40-1E5, R-CURVE), `MAXI` 1e-2 N (R-MAXI) of
`RELA_OF_MAXI` (NL-01b) rekenen ze door en zijn ze exact. Daarom is de standaard van
de bridge 1e-5 (`nonlin_static_3d`, `dyna_impl_3d`). Over alle NL- en
DY-verificatiecases veranderde 1e-6 → 1e-5 de resultaten hooguit 3,75e-6 relatief
(R-1E5); CCX en Abaqus gebruiken 5e-3.

Niet instelbaar in de bridge: `NEWTON/PREDICTION`. Normaal laat de bridge het
weg; de catalogus geeft geen standaardwaarde en welke voorspelling Code-Aster dan
gebruikt, staat niet eenduidig in U4.51.03 (NIET geverifieerd). U2.04.01 en U2.04.04
§4.5.2 raden `PREDICTION='ELASTIQUE'` aan bij convergentieproblemen. Uitzondering: met
[bezwijken van elementen](Bezwijken.md) zet de bridge het wel: `'TANGENTE'`, en in de
stap direct na een bezwijkmoment `'ELASTIQUE'` (statisch en impliciet dynamisch).
Expliciet blijft het altijd `'TANGENTE'` (Code-Aster staat bij een expliciet schema
niets anders toe).

### 2.3 Kinematica: `deformation`

`COMPORTEMENT/DEFORMATION` (EDF R&D, U4.51.11, "Operand DEFORMATION"). Code-Aster:
`PETIT`; de bridge gebruikt voor de niet-lineaire analyses standaard `GROT_GDEP`,
omdat Mecway's niet-lineaire analyse (CCX) geometrisch niet-lineair rekent (een
plastische staaf: met `PETIT` 14 % te stijf, met grote verplaatsingen +1 % t.o.v.
Mecway; eerdere run, model niet in de repository). De waarde in het startscherm is een
keuze voor het hele model; kies je een vorm voor grote verplaatsingen (`GROT_GDEP`,
`GREEN_LAGRANGE`, `GDEF_LOG`, `SIMO_MIEHE`), dan zet de bridge per elset de vorm die
Code-Aster 17.4 bij dat element en die materiaalwet accepteert
(`bridge_to_aster._deformation_for`, nagelopen met runs op een gemengd model). Eén
WARNING per run noemt de balk- en DKT/DST-elsets die geometrisch lineair blijven; de
details per elset staan als INFO in het log.

| Elset | Grote verplaatsingen gekozen | Waarom |
|---|---|---|
| volume, elastisch | `GREEN_LAGRANGE`, of `GDEF_LOG` als dat gekozen is | `GROT_GDEP` mag niet op 3D (`COMPOR5_22`) |
| volume, plastisch | `GDEF_LOG`, of `SIMO_MIEHE` als dat gekozen is (met `VMIS_CINE_LINE` altijd `GDEF_LOG`) | `GREEN_LAGRANGE` met `VMIS_*` geweigerd, `SIMO_MIEHE` met `VMIS_CINE_LINE` ook (`COMPOR1_44`) |
| DKT/DST | `GREEN_LAGRANGE` (met `VMIS_CINE_LINE` `PETIT`) | `GROT_GDEP` convergeerde niet, `GDEF_LOG` geweigerd (`COMPOR1_99`); `GREEN_LAGRANGE` gaf dezelfde uitkomst als `PETIT`, dus in feite geometrisch lineair. Grote rotaties van schalen: `elem_shell` = `COQUE_3D` |
| `COQUE_3D` | `GROT_GDEP` | alarm `COMPOR1_47`: rotaties < 2π; NL-02b exact |
| balk `POU_D_E`/`POU_D_T` | `PETIT` | `GROT_GDEP` op `POU_D_E` convergeerde niet (KNOWN_BUGS 11); voor grote rotaties `elem_beam` = `POU_D_T_GD` |
| balk `POU_D_T_GD` | `GROT_GDEP` met `ELAS_POUTRE_GR` | grote rotaties van balken (§2.9) |
| kabel (tension only) | altijd `GROT_GDEP` | `RELATION='CABLE'` vraagt dat; kleine voorspanning `N_INIT` = `cable_n_init_factor` × E × A (standaard 1e-6, pagina **Elementen**), anders is een rechte kabel singulier |
| discreet (veer, knoopmassa, elastic support) | `PETIT` (`PETIT_REAC` als gekozen) | grote verplaatsingen voor discreten NIET geverifieerd |

`PETIT` en `PETIT_REAC` gaan ongewijzigd naar alle elsets (behalve kabels).

**Meebewegende lasten.** Met een vorm voor grote verplaatsingen is uniforme druk een
meebewegende last (`TYPE_CHARGE='SUIV'`), zoals in Mecway (Mecway, 2026, §9.14), op
volumes en `COQUE_3D`; op DKT/DST kan Code-Aster dat niet (`CALCUL_42`), daar blijft
de druk vast (WARNING). Hydrostatische druk blijft vast. Centrifugaalkracht gebruikt in
`STAT_NON_LINE` de vervormde straal (spin softening, zoals Mecway §9.20) als alleen
volumes draaien. Plasticiteit op balken wordt elastisch gerekend (WARNING).

| Waarde | Wat | Wanneer |
|---|---|---|
| `PETIT` | Kleine verplaatsingen, rotaties en rekken (onder ca. 5 %). | Lineair statisch; niet-lineair alleen bij echt kleine vervormingen of voor vergelijking met lineaire theorie (DY-03). |
| `PETIT_REAC` | Evenwicht op de bijgewerkte geometrie, wet in kleine rekken. Alleen goed bij kleine stappen, kleine rotaties, overwegend plastische rek, isotroop gedrag. Afgeraden voor schalen en balken. | Zelden; liever `GDEF_LOG`. |
| `GROT_GDEP` | Grote verplaatsingen en rotaties, **kleine rekken**. Code-Aster: `COQUE_3D` (alle wetten), `DKT` (alleen lineair elastisch), multivezelbalken. | Knik, slanke schalen, grote verplaatsingen in het algemeen (de bridge kiest per elset, zie boven). |
| `SIMO_MIEHE` | Grote plastische rekken (o.a. `VMIS_ISOT_TRAC`). Alleen 3D/2D-volume-elementen. Niet-symmetrische tangentmatrix. | Grote plastische vervorming. |
| `GDEF_LOG` | Grote rekken met logaritmische rekmaat (o.a. `VMIS_ISOT_*`). Alleen 3D/2D. Elastische rek moet klein blijven. | Grote plastische vervorming (omvormen, knippen). Eerste keus naast `SIMO_MIEHE`; let op de stagnatie in §2.2. |
| `GREEN_LAGRANGE` | Green-Lagrange-rek. | Elastische volumes met grote verplaatsingen (NL-02a). |

Opgelegde rotaties (`DDL_IMPO` DRX/DRY/DRZ) en starre koppelingen
(`LIAISON_SOLIDE`) blijven ook met grote verplaatsingen kleine rotaties (op de knopen
van `POU_D_T_GD`-balken is een opgelegde rotatie de totale rotatievector, §2.9); een
opgelegde rotatie boven ~6° geeft een WARNING (`_warn_large_rotations`). Een star
deel draai je robuust via `#ASTER` (`ASTER_regels_voorbeelden.md` voorbeeld 9).

### 2.4 Plasticiteit: `plastic_strain_definition`

Code-Aster `TRACTION/SIGM` verwacht de spanning als functie van de **totale** rek.
Het eerste punt is de vloeigrens; een punt met rek nul mag niet (EDF R&D, U4.43.01
§5.1.1). De bridge rekent Mecway's hardingscurve om (instelling "Rekdefinitie
hardingscurve"):

| Waarde | Betekenis van de Mecway-rek | Omrekening |
|---|---|---|
| `plastic` | plastische rek | rek_totaal = rek_plastisch + σ/E |
| `total` | totale rek | beginpunt (0, 0) vervalt |
| `auto` (standaard) | afgeleid uit het eerste punt | (0, 0) of eerste rek > 0: total (zoals Mecway); (0, σ>0): plastic, met een WARNING |

Mecway's hardingscurve gebruikt de **totale** rek (gemeten met Mecway/CCX headless op
de staaf van NL-01, R-CURVE): de curve (0, 0), (σy/E, σy), (0,1, …) gaf de verwachte
spanning en plastische rek; een curve die met (0, σy) begint, gaf in Mecway een
onfysische uitkomst. `auto` leest daarom een curve met beginpunt (0, 0), of een curve
die direct op de vloeigrens (σy/E, σy) begint, als totale rek.

**E bij een curve in totale rek.** Mecway's tabblad *Plastic*: de eerste twee punten
bepalen het lineair-elastische gebied. Mecway rekent dan met de helling van dat eerste
stuk, niet met *Young's modulus* van het tabblad *Elastic*: gemeten met Mecway/CCX
headless (staaf in trek, *Young's modulus* 200 GPa, curve (0, 0), (0,001; 210 MPa),
(0,011; 310 MPa)) gaf rek 5·10⁻⁴ een spanning van 104,97 MPa (niet-lineair statisch) en
105,00 MPa (lineair statisch, CCX), dus E = 210 GPa. De bridge doet hetzelfde: bij een
curve die als totale rek gelezen wordt (isotroop en kinematisch, `auto` of `total`) is
E de helling van de oorsprong tot het eerste punt met rek > 0, met een WARNING met
beide waarden als die van het tabblad afwijkt. Die E geldt voor het materiaal in elke
analyse van het model (ook lineair, modaal en de zachte elementen bij bezwijken). Een
curve zonder (0, 0) krijgt de helling oorsprong → eerste punt, zoals Mecway (gemeten:
(0,001; 210 MPa), (0,011; 310 MPa) gaf 104,98 MPa niet-lineair en 105,00 MPa lineair,
verificatie NL-04c). Niet voor een curve als plastische rek (begint met (0, σ > 0), zoals WE-12c en
Ramberg-Osgood) en niet voor OpenRadioss `PLAS_TAB`: daar blijft E van het materiaal.
Code-Aster stopt met `MATERIAL1_5` als de helling tot het eerste curvepunt meer dan 1 %
van E afwijkt; de bridge controleert dat vooraf en stopt dan met een ERROR met beide
waarden (bijv. een curve als plastische rek waarvan de eerste plastische rek niet 0
is). Verificatie NL-04 (isotroop) en NL-04b (kinematisch).

Begint de curve met (0, σ > 0), dan leest `auto` hem als plastische rek, met
een WARNING dat Mecway dezelfde curve als totale rek leest (de Mecway-oplossing kan
dan afwijken); kies `plastic` of `total` om de melding te vermijden. Gemeten op NL-01
met `auto`: curve met en zonder (0, 0) exact tot t = 3 (σ op t = 2: 433,49 MPa,
analytisch), curve (0, 355 MPa) als plastische rek ook exact (R-CURVE). Controleer bij
twijfel de vloeigrens in de `.comm` (eerste punt van de functie). Bilineaire plasticiteit:
Mecway's *tangent modulus* is de plastische modulus H; de bridge zet
`D_SIGM_EPSI` = E·H/(E+H) (NL-01).

**Hyperelastisch materiaal (Neo Hooke, Mooney-Rivlin).** Mecway 34 heeft Neo Hooke
(C10, D1, thermische uitzetting) en Mooney-Rivlin (C10, C01, D1, thermische uitzetting),
alleen in *Nonlinear static 3D* en *Nonlinear dynamic response 3D*. De bridge maakt er
`DEFI_MATERIAU ELAS_HYPER` (C10, C01, K, RHO) van met `RELATION='ELAS_HYPER'` en
altijd `DEFORMATION='GREEN_LAGRANGE'` (de instelling `deformation` telt dan niet voor die
elset), in niet-lineair statisch en in dynamisch impliciet en expliciet. De
compressiemodulus is K = 2/D1 (Mecway/CCX: volumeterm (J − 1)²/D1). Gecontroleerd met een
kubus in eenassige trek (λ = 1,5) en druk (λ = 0,7) tegen 2(λ − λ⁻²)(C10 + C01/λ):
NL-50/51 binnen 0,11 %, gelijk aan Mecway/CCX headless (NL-52 impliciet, NL-53 expliciet).
`SIXX` is de Cauchy-spanning. Expliciet: de kritieke tijdstap gebruikt de equivalente
waarden bij kleine rek, G = 2(C10 + C01), E = 2G(1 + ν) met ν uit K en G. Meldingen:

| Situatie | Melding |
|---|---|
| D1 = 0 (volledig onsamendrukbaar) | ERROR: Code-Aster heeft een eindige K nodig; geef D1 > 0, bijv. 2/K met K ≈ 1000 × 2(C10 + C01) |
| thermische uitzetting ingevuld, of *Thermal stress* | WARNING: genegeerd (`ELAS_HYPER` heeft geen `ALPHA`) |
| Rayleigh-demping in dynamica | WARNING: geldt niet voor dit materiaal |
| schalen, balken of 2D | ERROR (alleen volume-elementen, zoals Mecway) |
| lineair statisch, modaal, knik, thermisch → mechanisch | ERROR (Mecway biedt het ook alleen niet-lineair) |
| `imperfection_amplitude` | ERROR (de knikanalyse vooraf heeft `ELAS` nodig) |
| ander type, bijv. hyperfoam | ERROR: niet vertaald; hyperfoam kan niet met Code-Aster 17.4 op Windows (zie hieronder) |
| hex8 met *Hex8* = `3D` | WARNING: volumetrische locking, met K/G van het materiaal (zie hieronder) |
| hex8 met *Hex8* = `3D_SI` | WARNING: die elset krijgt `3D` (Code-Aster kent geen `GREEN_LAGRANGE` op lineaire elementen met onderintegratie, `ELEMENTSSI_1`) |
| CCX > *custom element type* (bijv. C3D8R) | WARNING: alleen CalculiX, niet vertaald (zie hieronder) |

**Kies *Hex8* = `LINE_QUAD` voor rubber op hex8.** Bijna onsamendrukbaar materiaal op een
volledig geïntegreerde lineaire hex8 of tet4 'lockt' volumetrisch: het element kan niet
vervormen bij gelijk volume en is veel te stijf, ook zonder buiging. Gemeten aan een
verlijmde rubbercilinder (GitHub-issue #5: kwartmodel R 16 × H 18 mm, 684 hex8, Neo Hooke
C10 = 0,348 MPa, D1 = 0,005 mm²/N, dus K/G = 575, 3 mm ingedrukt):

| Element | Kracht bij 3 mm | t.o.v. referentie |
|---|---|---|
| Code-Aster `3D` (= CCX C3D8) | 368,5 N | ×3,0 |
| CCX C3D8R (onderintegratie) | 181,8 N | +46 % |
| Code-Aster `LINE_QUAD` (= CCX C3D20) | 132,3 N | +6 % |
| referentie: CCX C3D20R en C3D8I op het 2× verfijnde mesh | ~124 N | (binnen 1 %) |

Met hetzelfde element geven Code-Aster en CCX dezelfde kracht (binnen 0,1 N); een
verschil met een CCX-model komt dus meestal van het elementtype. Mecway's *custom element
type* in de CCX-instellingen (bijv. Hex8 → C3D8R) is een CalculiX-instelling: de bridge
vertaalt die niet (WARNING) en Code-Aster neemt de formulering van de pagina Elementen;
C3D8R en C3D8I hebben geen gelijke in Code-Aster. `3D_SI` werkt niet met `ELAS_HYPER`.
Met `LINE_QUAD` haalde hetzelfde model ook de volle 10 mm, waar `3D` na 6 mm veel
stapverkleiningen nodig had.

**Hyperfoam: niet mogelijk met Code-Aster 17.4 op Windows** (gecontroleerd 22 oktober
2026). Mecway 34 heeft zelf geen hyperfoam-materiaal (alleen Neo Hooke en Mooney-Rivlin;
de naam bestaat alleen in Mecway's import van CalculiX-`.inp`-bestanden). De wet van
Code-Aster voor samendrukbaar schuim, `HYPER_HILL` (`ALPHA`, `BETA`, `MU`; dezelfde vorm
als Abaqus/CalculiX *HYPERFOAM*), is een MFront-wet en vraagt een Code-Aster die met
MFront-ondersteuning (MGIS) gebouwd is. Geen van beide Windows-versies van Code-Aster 17.4
heeft die:

| Versie | MFront/MGIS-bibliotheken | Uitkomst validatietest `ssnv520a` (`HYPER_HILL`) |
|---|---|---|
| Simulease "Code_Aster v2025" (standaard van de bridge) | niet meegeleverd; log: "Librairie MFront : non disponible" | staat op `exclude-testlist.txt` van die versie |
| open-simulation-center `code_aster-17.4.0-win64.msi` | meegeleverd (MFront 4.2.3, MGIS 2.2), maar Code-Aster zelf is zonder gebouwd: "Librairie MFront : non disponible" | stopt in `STAT_NON_LINE` met `NameError: The object 'MGISBehaviour' is not available in this installation` (terwijl `run_aster` toch `DIAGNOSTIC JOB : OK` meldt) |

Een Linux- of containerversie van Code-Aster met MFront biedt `HYPER_HILL` waarschijnlijk
wel; dat past niet bij de bridge, die standalone op Windows draait met alleen Mecway en een
Code-Aster-installatie. Hyperfoam staat gepland voor zodra er een Windows-versie met
MFront-ondersteuning is (STAPPENPLAN S14).

### 2.5 Tijdschema (dynamica): `schema`, `hht_alpha`

`DYNA_NON_LINE/SCHEMA_TEMPS` (EDF R&D, U4.53.01, U2.06.13).

| `schema` | Type | Wat de bridge zet | Opmerking |
|---|---|---|---|
| `HHT` (standaard `dyna_impl_3d`) | impliciet | `ALPHA=hht_alpha`, `FORMULATION='DEPLACEMENT'` | Volledig HHT-schema (CA-standaard `MODI_EQUI='OUI'`; Hilber e.a., 1977). DY-01a, DY-02, DY-03c. |
| `NEWMARK` | impliciet | `FORMULATION='DEPLACEMENT'`, geen BETA/GAMMA | CA: β = 0,25, γ = 0,5 (trapeziumregel). Geen numerieke demping; kan niet-lineair instabiel zijn (U4.53.01). DY-01b/c/d (periodefout van orde 2, Hughes, 2000). |
| `DIFF_CENT` (standaard `dyna_expl_3d`) | expliciet | `MASS_DIAG='OUI'`, `FORMULATION='ACCELERATION'` | Geen numerieke demping. DY-03a/b. |
| `TCHAMWA` | expliciet | idem | Dempt hoge frequenties (CA: `PHI=1.05`). DY-03a met TCHAMWA binnen de tolerantie (R-TCHAMWA). |

`hht_alpha` (HHT ALPHA): bridge -0,1, CA -0,1. Hoe negatiever, hoe meer numerieke
demping. U2.06.13: begin bij -0,1; -0,3 is een bovengrens die nog bruikbaar is; doe een
parameterstudie en kies de waarde het dichtst bij nul die nog een goede oplossing
geeft. Met -0,3 volgde DY-01 het schema exact (periode +1,21 %, piek −0,87 %,
R-ALPHA). Een staplast krijgt bij HHT in de eerste stap een iets te kleine impuls
(Code-Aster gebruikt F₀ = 0; DY-01a: piek −0,44 %).

**`MODI_EQUI`.** De bridge laat de CA-standaard `'OUI'` staan: het volledige
HHT-schema, tweede orde, dat vooral hoge frequenties dempt en dat U2.06.13
aanbeveelt (`'NON'` = gemodificeerde gemiddelde versnelling, eerste orde).

**Rayleigh-demping in niet-lineaire dynamica.** De dempingsmatrix C = α M + β K
gebruikt in `DYNA_NON_LINE` de Code-Aster-standaard `AMOR_RAYL_RIGI='ELASTIQUE'`
(catalogus `code_aster/Cata/Commands/dyna_non_line.py` van 17.4: `defaut="ELASTIQUE"`,
keuze `"TANGENTE"`): K is de **elastische** stijfheid, niet de tangentiële. Bij
plasticiteit of grote verplaatsingen blijft het β-deel dus even groot als in het
elastische model (de tangentiële stijfheid zou het verkleinen). De bridge zet het
sleutelwoord niet en verandert de standaard niet (er is geen instelling of
`#ASTER`-regel voor `'TANGENTE'`).

### 2.6 Lineaire solver: `solver_nprec`, `lin_solver`, `lin_solver_resi`

`SOLVEUR=_F(METHODE='MUMPS', NPREC=...)`. NPREC is het aantal decimalen dat bij
de factorisatie verloren mag gaan voor Code-Aster de matrix singulier noemt.

| | `lin_static_3d` | niet-lineair, modaal, knik, thermisch | CA |
|---|---|---|---|
| `solver_nprec` (MUMPS NPREC) | 8 | 8 | 8 |

Bij niet-lineair telt een singuliere matrix als `ERREUR` en leidt (impliciet
dynamisch) tot stapverkleining (U4.34.03). Een vrij bewegend deel geeft in
`MECA_STATIQUE` met -1 `FACTOR_57` (foutgrens te groot) en met 8 `FACTOR_11` (R-FREE);
beide stoppen de run. In `STAT_NON_LINE`/`DYNA_NON_LINE` controleert MUMPS de
foutgrens standaard niet (`RESI_RELA` = -1 voor niet-lineaire commando's, catalogus
`c_solveur.py`); NPREC is daar de enige singulariteitscontrole. NL-03a
(lijncontact, `STANDARD`) rekende met -1 door, maar 1,6 % naast de contactkracht
(R-NPREC-CONTACT): gebruik daar `PENALISATION` (§3.1).

**Statische analyse (`lin_static_3d`): `lin_solver` en `lin_solver_resi`.**
`MECA_STATIQUE` lost één stelsel Ku = F op. De bridge zet daar altijd `INFO=2`
bij, zodat de statistiek van de oplosser in de `.mess` komt (convergentiescherm,
§4.4). Dat is ongeveer 15 kB tekst, ook bij 270 000 vergelijkingen (gemeten).

| Instelling (label) | Waarden | Code-Aster |
|---|---|---|
| `lin_solver` (Lineaire oplosser) | `MUMPS` (standaard): directe oplosser, factoriseert de matrix | `SOLVEUR=_F(METHODE='MUMPS', NPREC=..., RESI_RELA=...)` |
| | `GCPC`: iteratief, geconjugeerde gradiënt met onvolledige factorisatie | `SOLVEUR=_F(METHODE='GCPC', PRE_COND='LDLT_INC', RESI_RELA=...)` |
| `lin_solver_resi` (Nauwkeurigheid oplosser) | `RESI_RELA`, standaard 1e-6 (= CA-standaard bij `MECA_STATIQUE`) | |

- **MUMPS**: `RESI_RELA` is de grens voor de *geschatte relatieve fout in de
  verplaatsingen*. MUMPS schat die als conditiegetal × 'backward error'; is ze
  groter dan `RESI_RELA`, dan stopt Code-Aster met `FACTOR_57` (EDF R&D, U4.50.01
  §3.5.3; U2.08.03 §7.2.1). Met `solver_nprec` = -1 is dit de enige controle op een
  singuliere matrix (U2.08.03 tabel 7.1-1, geval 5). Kies MUMPS tenzij je een
  reden hebt: het is robuust en meestal het snelst. Een slank volumemodel op buiging
  kan zonder mechanisme boven 1e-6 komen (hex20-uitkragende balk 1000 × 40 × 10 mm:
  7,0e-6; een mechanisme geeft `FACTOR_11`, of met -1 een fout van orde 10); de melding
  van de bridge noemt dan de waarde voor `lin_solver_resi`
  ([Foutmeldingen](Foutmeldingen_CodeAster.md), `FACTOR_57`).
- **Andere analyses**: `lin_solver_resi` staat ook op de pagina's *Modaal* (de
  `MECA_STATIQUE` voor de voorspanning), *Knik* (de statische stap) en *Niet-lineair
  statisch* (de `MECA_STATIQUE` van de imperfectie). Daar is de oplosser altijd MUMPS
  (`NPREC` = `solver_nprec`). `STAT_NON_LINE` en `CALC_MODES` controleren de foutgrens
  niet (`RESI_RELA` -1, catalogus `c_solveur.py`).
- **GCPC**: `RESI_RELA` is het convergentiecriterium ‖r‖/‖f‖ (restkracht gedeeld
  door de belasting). Maximaal aantal iteraties: het aantal vergelijkingen / 2
  (`NMAX_ITER=0`; daarna stopt Code-Aster met `ALGELINE4_3`). GCPC gebruikt minder
  geheugen, maar convergeert alleen goed bij een goed geconditioneerd model
  (U2.08.03 §3: conditiegetal < 1e4); bij slanke constructies (balken van
  volume-elementen) zijn honderden iteraties normaal: de balk van LS-02 (hex8) had
  232 iteraties bij 20 169 vergelijkingen en 499 bij 141 321, met dezelfde uitkomst
  als MUMPS binnen de tolerantie (R-GCPC). Zie je in het convergentiescherm een lange
  vlakke lijn, gebruik dan MUMPS.
- **PETSC** staat in de catalogus, maar de Windows-versie van Code-Aster is
  sequentieel en heeft geen PETSc (`FERMETUR_10`, gezien in een testrun;
  U4.50.01 §3.7). De bridge biedt het daarom niet aan.

### 2.7 Overig

`time_limit` (Tijdslimiet run_aster) [s] en `memory_limit` (Geheugenlimiet run_aster)
[MB] gaan naar de `.export` (limieten van `run_aster`). Een afgebroken run door de
tijdslimiet levert geen volledige resultaten.

`energy_balance` (Energiebalans; alleen impliciete dynamica, standaard uit): zie §4.4.

`error_estimator` (Foutschatter; alleen statisch, standaard aan): geschatte
discretisatiefout per element met `CALC_ERREUR` `ERME`, zie
[Foutschatter.md](Foutschatter.md).

`crit_stab` (Stabiliteit per stap, standaard uit) en `imperfection_*` (knikvorm als
imperfectie, standaard amplitude 0 = geen; alleen niet-lineair statisch): `CRIT_STAB`
in `STAT_NON_LINE` en een lineaire knikvorm als voorvervorming van het mesh, zie
[Modaal_en_knik.md](Modaal_en_knik.md) §5. Met de standaard `deformation` (grote
verplaatsingen) is `CRIT_STAB` geen lastfactor maar een eigenwaarde die naar 0 gaat.

### 2.8 Modaal, knik en thermisch

De instellingen van modaal en knik (`modal_modes`, `modal_shift_hz`, `modal_norm`,
`modal_tolerance`) staan in [Modaal_en_knik.md](Modaal_en_knik.md) §1.2, die van
thermisch (`theta` en de Newton-instellingen van `THER_NON_LINE`) in
[Thermisch.md](Thermisch.md) §2. Onderbouwing en controleruns:
[Standaardinstellingen_en_aannames.md](Standaardinstellingen_en_aannames.md) §3.6 tot
§3.8. Knik zoekt altijd de kleinste kniklastfactoren (`OPTION='PLUS_PETITE'`), zoals
Mecway; een zoekcentrum (`OPTION='CENTRE'`) negeert `CHAR_CRIT` in Code-Aster 17.4
(R-BSHIFT) en is daarom geen instelling.

### 2.9 Balken met grote rotaties: `elem_beam` = `POU_D_T_GD`

Standaard rekenen balken in de niet-lineaire analyses geometrisch lineair (`POU_D_E`/
`POU_D_T` met `PETIT`, §2.3; KNOWN_BUGS 11). Voor grote verplaatsingen en rotaties van
balken kies je op de pagina **Elementen** `elem_beam` = `POU_D_T_GD`. De bridge zet dan:

```python
model = AFFE_MODELE(..., AFFE=_F(GROUP_MA=..., MODELISATION='POU_D_T_GD'))
res = STAT_NON_LINE(...,
    COMPORTEMENT=_F(GROUP_MA=..., RELATION='ELAS_POUTRE_GR', DEFORMATION='GROT_GDEP'))
```

Een elastische Timoshenko-balk (met afschuifvervorming; `AY`/`AZ` als bij `POU_D_T`)
met grote verplaatsingen en rotaties en kleine rekken (EDF R&D, U4.51.11; Code-Aster-
testcase ssnl103a). Het idee, de Code-Aster-route, de eerste lijst beperkingen en de
benchmarks NL-80 tot NL-82 komen uit de fork van MishalTPC
(`github.com/mishal0488/MecwayAsterBridge`, MPL-2.0); de bridge heeft ze opnieuw
gebouwd voor element offset, flexible joint, line3, balkorientatie en `beam_forces`.

| Combinatie | Wat de bridge doet |
|---|---|
| niet-lineair statisch met grote verplaatsingen (`deformation` standaard `GROT_GDEP`) | `POU_D_T_GD`: kracht en moment (constant, NL-80c, of als tabel in de tijd), line pressure (constant of als formule in x, y, z, t), zwaartekracht, Thermal stress, Mecway's *Time step size*, configuraties (NL-80 tot NL-90) |
| line3-balk | twee SEG2-cellen per element, zoals bij `POU_D_E` (NL-84) |
| balkorientatie (attributen en *Element orientation*) | expliciete `VECT_Y` per cel (NL-85) |
| centrifugaalkracht | `ROTATION` kan niet op dit element (`CHAR_MECA_ROTA_R`, `CALCUL_37`); de bridge zet `FORCE_POUTRE` als formule van de beginpositie: een vaste last, zonder spin softening (NL-86); trusses (`BARRE`) in zo'n model krijgen ook `FORCE_POUTRE` (NL-86b) |
| plastisch materiaal | elastisch gerekend (WARNING), zoals bij de andere balken |
| bezwijken van elementen ([`Bezwijken.md`](Bezwijken.md)) | ERROR: na het eerste bezweken element vraagt de volgende stap `RIGI_MECA` (`CALCUL_37`); zet het bezwijken uit of kies `POU_D_E`/`POU_D_T` |
| andere analyses (statisch, modaal, knik, harmonisch, spectrum, dynamica) en niet-lineair met `PETIT`/`PETIT_REAC` | `POU_D_T` met een WARNING: dezelfde balk bij kleine verplaatsingen (NL-80b). Het element kent geen `RIGI_MECA` (`CALCUL_37` in `MECA_STATIQUE`); dynamica (testcase sdnl103a) is in de bridge NIET geverifieerd |
| `crit_stab` | ERROR: de tangentmatrix is niet symmetrisch (`ALGELINE4_41`) |
| `imperfection_amplitude` > 0 | ERROR: de lineaire knik vooraf vraagt `RIGI_MECA`; leg de beginkromming in de mesh (NL-82) |
| flexible joint met U, V en W vrij (kogelscharnier) | koppelt alleen de verplaatsingen (DX, DY, DZ): exact bij elke rotatie (NL-90, NL-90b; naar de fork van MishalTPC) |
| flexible joint met een deel van de rotaties vrij (U, V, W, UV, UW, VW) | ERROR vooraf: de rotaties langs de niet-vrije assen zijn een lineaire relatie in de onvervormde assen, en bij eindige rotaties geeft dat een onjuiste extra rotatie in het scharnier (KNOWN_BUGS 106). Kies `POU_D_E`/`POU_D_T` (kleine rotaties) of maak U, V en W vrij |
| element offset, koppelingen | rekenen (offset bij kleine lasten gelijk aan `POU_D_T`; koppelingen NIET geverifieerd), maar blijven lineaire relaties in de onvervormde assen: WARNING (KNOWN_BUGS 11, 108) |
| opgelegde rotatie (`noderotation`) | de totale rotatievector (exact voor een rotatie om één vaste as), maar slanke balken convergeren slecht: WARNING (KNOWN_BUGS 11) |

**Resultaten.** Verplaatsingen, rotaties en reacties zoals altijd. Snedekrachten
(`beam_forces`: `tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv`,
`bendingmomw`) komen uit `SIEF_ELNO`/`SIEF_NOEU` (`EFGE_ELNO` stopt bij dit element met
`DVP_1`), in de meedraaiende assen van de doorsnede, met dezelfde namen en tekens als bij
`POU_D_E`. Het is één waarde per element (één integratiepunt, in het midden); de
knoopwaarde is het gemiddelde van de aangrenzende elementen, dus bij de inklemming een
half element naast de maximale waarde. Balkspanningen (`beamsixxmin`/`beamsixxmax`) zijn
er niet: het element kent `SIPM_ELNO` niet (`CALCUL_37`). Een WARNING per run noemt dat.

**Aanwijzingen.**

- `POU_D_T_GD` is een lineair element: neem 20 tot 40 elementen per staaf (met 40
  elementen ≤ 0,03 % van de analytische oplossing, NL-81 en NL-83).
- Laat de last oplopen (een tabel in de tijd, Mecway's *Time step size*): NL-81 buigt
  90 graden in 20 stappen.
- Bij een kleine last stagneert `RESI_GLOB_RELA` op afronding: kies
  `convergence_criterion` = `RELA_OF_MAXI` met een absolute grens (§2.2, NL-80).
- Krachten houden hun richting (vaste last, zoals in Mecway: NL-83 ligt binnen 0,02 %
  van Mecway 34 met CCX). Een moment om een vaste as (vlakke buiging) is exact (NL-81);
  een moment in 3D is NIET geverifieerd.
- Mecway 34 rekent niet-lineaire balken alleen met CCX (de eigen solver gaf geen
  oplossing); het eindmoment van NL-81 haalde CCX niet verder dan t = 0,55 s.
- **Grote rotaties om een scheve as (3D): kleine stappen en controleer ze.** In een test
  met een exacte starre rotatie (22 oktober 2026) was `POU_D_T_GD` exact om een globale
  as, maar om een scheve as kreeg het valse snedekrachten die kleiner worden met de
  stapgrootte (bij 10 graden om (1,1,0): 6 % van EI/L met 2 stappen, 0,06 % met 16
  stappen); om (1,2,3) convergeerde het vanaf ongeveer 60 graden niet meer. Buiging in
  een vlak (NL-80 t/m NL-90) heeft er geen last van. Bij 3D-rotaties van tientallen
  graden: halveer de *Time step size* één keer en controleer dat de resultaten niet
  veranderen (KNOWN_BUGS 11, STAPPENPLAN S21).

---

## 3. Contact

### 3.1 Wat de bridge genereert

Mecway `contact2` wordt:

```
contact = DEFI_CONTACT(
    MODELE=model,
    FORMULATION='CONTINUE',
    FROTTEMENT='SANS',          # 'COULOMB' als een paar wrijving > 0 heeft
    ZONE=(_F(GROUP_MA_MAIT='<master>', GROUP_MA_ESCL='<slave>'),),  # + COULOMB=mu
)
```

- **Formulering (`contact_algo`, label "Contactmethode").** `CONTINUE` met per zone
  `ALGO_CONT`:
  - `STANDARD` (standaard, CA-standaard): augmented-Lagrangiaan (EDF R&D, U4.44.11),
    met contactdruk als extra onbekende op de slave-kant; geen stijfheid nodig, geen
    penetratie.
  - `PENALISATION`: contactdruk = `COEF_PENA_CONT` × penetratie, met
    `COEF_PENA_CONT` = Mecway's *normal stiffness* (Pa/m); bij wrijving
    `ALGO_FROT='PENALISATION'` met `COEF_PENA_FROT` = *tangential stiffness* (is die 0,
    dan Lagrange-wrijving). Zo rekent Mecway zelf (Mecway, 2026, §9.9.2). Kies dit als
    `STANDARD` het contact verliest of stopt met `MECANONLINE9_4` met `LAGS_C` in de
    melding (lijncontact). Geverifieerd: de penetratie is exact p/kn (NL-03d/f) en
    lijncontact tussen hex20-balken is exact (NL-03b), waar `STANDARD` faalt (NL-03a).
    Tegen Mecway (headless): Samples/PipeClip met `PENALISATION` + `MAXI` volgt de
    clipverplaatsing binnen 2..8 % (met `STANDARD` ging het contact verloren);
    Tutorials/AssemblyWithContact (Fixed_support) 21,74 tegen 21,97 µm (met
    `STANDARD`: `MECANONLINE9_4`).

- **Penetratiecontrole (`contact_pene_maxi`, alleen `PENALISATION`).** Een te lage
  *normal stiffness* laat de delen merkbaar in elkaar zakken zonder foutmelding. Na de
  run neemt de bridge de grootste penetratie uit de kolom `CONTACT PENETRATION` van de
  convergentietabel in study.mess (laatste Newton-iteratie van elke geconvergeerde
  stap) en geeft een WARNING (NL+EN, ook in het venster na de run) als die groter is
  dan `contact_pene_maxi` × de kortste rand van de slave-vlakken (standaard 0,05; 0 =
  uit). De resultaten veranderen niet: verhoog zelf de *normal stiffness* of kies
  `STANDARD`. Niet via `DEFI_LIST_INST ECHEC=_F(EVENEMENT='INTERPENETRATION',
  PENE_MAXI=..., ACTION='ARRET')` (catalogus `defi_list_inst.py` 17.4; de andere actie
  `ADAPT_COEF_PENA` past de stijfheid zelf aan): met `FORMULATION='CONTINUE'` stopte
  Code-Aster 17.4 in de eerste stap met `<EXCEPTION> JEVEUX_26` (object
  `&&OP0070.RESOC.COCO` ontbreekt) en zonder resultaten. Geverifieerd: NL-03p (kn =
  1e10 Pa/m, penetratie 1 mm = 15 % van de rand: WARNING); NL-03b/d/f (1 µm) geen.

  Verschil met Mecway bij `STANDARD`: Mecway "unilateral elastic" is een
  penalty-methode met een stijfheid per oppervlak (Mecway, 2026, §9.9):
  Mecway laat iets penetratie toe, Code-Aster op de slave-punten niet (KNOWN_BUGS 43).
- **Integratie.** Op kwadratische slave-vlakken (tet10, hex20, quad8 ...) zet de bridge
  `INTEGRATION='NCOTES'`; lineaire vlakken houden de CA-standaard `'AUTO'`. Met
  `'AUTO'` haalde de contact-patchtest op hex20 met niet-passende meshes het niet
  (1,5 tot 4,6 % fout), met `'NCOTES'` exact (NL-03c tot f). Code-Aster meldt dan het
  onschuldige alarm `CONTACT3_16` (geen `CONT_NOEU`). Een eigen
  `#ASTER-ZONE INTEGRATION=...` gaat voor.
- **Mecway-contacttype.** Mecway kent `unilateralelastic` (contact) en
  `bondedelastic`, `bondedtie` en `bondedce` (verlijmd). Alleen
  `unilateralelastic` wordt `DEFI_CONTACT`. Een verlijmd paar wordt
  `AFFE_CHAR_MECA/LIAISON_MAIL` (star; `bondedelastic` zonder de stijfheid, gemeld):
  `TYPE_RACCORD='MASSIF'` (volume op volume, master = de volume-elementen achter de
  vlakken), `'COQUE'` (schaal op schaal, ook een schaalrand op een schaalvlak; stijf,
  zonder de rotatie om de normaal, §3.10) of `'MASSIF_COQUE'` (volume-slave op
  schaal-master). Schaal-slave op volume-master: een schaalvlak koppelt de
  verplaatsingen (`'MASSIF'` met de schaalknopen); schaalranden van één component
  worden stijf verbonden (`'COQUE_MASSIF'` met de dikte en het normaalveld van de
  schaal), anders werkt de rand als scharnier (WARNING). Balkuiteinden als slave
  worden gemeld en overgeslagen (KNOWN_BUGS 21).
- **Alleen niet-lineair.** `contact2` gaat alleen naar `STAT_NON_LINE`/
  `DYNA_NON_LINE`; met `lin_static_3d` (ook S30 via `auto`) stopt de bridge met een
  ERROR. Kies bij contact `nonlin_static_3d`. Verlijmd contact (`LIAISON_MAIL`) werkt
  ook lineair.
- **Compression only support** (Mecway) wordt `DEFI_CONTACT
  FORMULATION='LIAISON_UNIL'` (U4.44.11 §3.8), alleen in een model zonder
  `contact2` (één `DEFI_CONTACT` per berekening; KNOWN_BUGS 22).
- **Wrijving.** Heeft minstens één paar een wrijvingscoëfficiënt > 0, dan
  `FROTTEMENT='COULOMB'` voor alle zones, met `COULOMB=` per zone (0 voor paren
  zonder wrijving).
- **Adaptatie.** CA-standaard `ADAPTATION='CYCLAGE'`: wisselt een contactpunt
  steeds van status, dan schakelt Code-Aster daar zelf over op penalty met een
  maximale penetratie (U4.44.11, "Operand ADAPTATION"; U2.04.04 §4.1). Controleer
  dan de penetratie in de convergentietabel in de `.mess`.
- **Vlakken.** Alleen vlakken van volume-elementen en schaalvlakken. Andere paren
  worden gemeld (ERROR in `<model>_<run-id>_bridge_log.txt`) en overgeslagen.
- Een **onderdrukt** contact in Mecway (`suppressed`) wordt overgeslagen. Handig
  om contact tijdelijk uit te zetten (§4).
- **Vastgezette slave-knopen.** Slave-knopen die ook in een fixed support zitten,
  sluit de bridge per zone uit met `SANS_GROUP_NO` (U4.44.11 §3.1.3;
  `bridge_mesh._exclude_fixed_slaves`, INFO in het log). Een eigen
  `#ASTER-ZONE SANS_GROUP_NO=...` gaat voor. Andere voorwaarden op slave-knopen
  (symmetry, displacement, ...) worden niet uitgesloten (§3.7).
- **Grove slave.** Is de slave-kant duidelijk grover dan de master (elementmaat
  meer dan 2× zo groot), dan geeft de bridge een WARNING (`bridge_mesh._check_contact_sides`):
  de fijne master kan dan zonder contactkracht door de slave dringen. De bridge
  wisselt niet zelf (§3.2).

### 3.2 Master en slave

De bridge neemt master en slave over zoals in Mecway ingesteld. Kies ze goed;
Code-Aster voorkomt alleen dat slave-punten in het master-vlak dringen, andersom
kan wel (EDF R&D, U2.04.04 §2.1).

| Master (`GROUP_MA_MAIT`) als het vlak... | Slave (`GROUP_MA_ESCL`) als het vlak... |
|---|---|
| star is | gekromd is |
| het andere bedekt (groter is) | kleiner is |
| een veel grotere schijnbare stijfheid (N/m) heeft | een kleine schijnbare stijfheid heeft |
| veel grover gemesht is | veel fijner gemesht is |

(U2.04.04 §2.2.1 en §2.2.2.) Kort: master = stijf gereedschap / grof vlak,
slave = fijn of vervormend vlak. Een scherpe hoek die je niet kunt vermijden: het
vlak met die hoek wordt slave (U2.04.04, "Sharp angles"). Bij convergentieproblemen,
vooral met plasticiteit, kan het helpen de rollen om te draaien (U2.04.04 §2.2.3).
Veel master-knopen in het slave-vlak na de berekening: mesh te grof of te groot
verschil in fijnheid (U2.04.04 §2.2.5).

### 3.3 Normalen

Contactvlakken moeten een **naar buiten** gerichte normaal hebben (U2.04.04,
"Orientation of the normals"; U4.44.11).

- De bridge zet `MODI_MAILLAGE ORIE_PEAU` op de contact- (en druk-)vlakken van
  volume-elementen.
- Voor schaalvlakken zet de bridge geen `ORIE_NORM_COQUE`.
- Code-Aster controleert de oriëntatie standaard en stopt bij een fout
  (`VERI_NORM='OUI'`, catalogus).
- **Normalen gladstrijken (`contact_smoothing`, label "Normalen gladstrijken (LISSAGE, gebogen vlakken)"; standaard uit).** Schrijft `LISSAGE='OUI'` in `DEFI_CONTACT` (globaal sleutelwoord bij `CONTINUE`, catalogus `defi_contact.py` 17.4): de normaal in elke knoop is het gemiddelde van de aangrenzende vlakken. Gebruik het bij gebogen contactvlakken (cilinder, bol, buis) met weinig facetten: de facetnormalen springen van vlak tot vlak, wat een ongelijkmatige contactdruk geeft en de convergentie kan hinderen. Niet gebruiken als het contactvlak scherpe randen of hoeken heeft (een blokrand, een trap): daar wijst de gemiddelde normaal de verkeerde kant op. Een eigen `#ASTER-CONTACT LISSAGE=...` gaat voor. Bij vlakke contactvlakken (NL-03a..f) en bij het fijn gemeshte Samples/PipeClip verandert de optie niets meetbaars (S28); het telt bij grove facetten.

### 3.4 Beginspleet en beginpenetratie

De bridge zet `CONTACT_INIT` niet, dus geldt de CA-standaard `'INTERPENETRE'`
(catalogus 17.4, U4.44.11): aan het begin zijn alle punten met spleet nul of met
penetratie actief. Tolerantie: 1e-6 × de kleinste ribbe (U2.04.04 §4.4.1).

- Een beginpenetratie wordt weggedrukt en **geeft krachten**; het is geen
  geometrische correctie (U2.04.04 §4.4.1). Zorg dus in Mecway voor een mesh
  zonder overlap.
- Andere waarden (niet via de bridge): `'OUI'` activeert alle punten, ook met
  spleet (handig als vlakken net niet sluiten); `'NON'` activeert niets.
- **Delen die alleen door contact op hun plaats blijven.** Statisch is de matrix
  dan singulier zolang er geen contact is. Oplossingen (U2.04.04 §4.4, §4.1; Mecway,
  2026, §6.2.3): begincontact (spleet nul), zwakke veren (elastic support), of eerst
  een stap met opgelegde verplaatsing tot er contact is. In dynamica mag een
  star-lichaambeweging wel.

### 3.5 Zones die slave-knopen delen

Code-Aster verbiedt knopen die in de slave-vlakken van twee zones zitten
(melding `CONTACT2_16`; U2.04.04 §2.1, U4.44.11). Mecway staat dat wel toe
(bijvoorbeeld een profiel dat slave is tegen een mes én tegen een contour).

De bridge voegt zulke paren samen tot één zone: master = unie van de masters,
slave = unie van de slaves (`DEFI_GROUP ... UNION`, groepen `CMAIT<n>`/`CESCL<n>`).
Wrijving: de grootste coëfficiënt; staat er een WARNING in `<model>_<run-id>_bridge_log.txt` als
die verschilden (KNOWN_BUGS 10). De oplossing die `CONTACT2_16` zelf voorstelt (master
en slave wisselen) gebruikt de bridge niet: dan wordt het stijve gereedschap slave.

Master- en slave-vlak van **één** zone mogen ook geen knopen delen, anders stopt
Code-Aster (U2.04.04 §2.3.4). De bridge sluit zulke knopen niet uit.

### 3.6 Self-contact

Niet mogelijk in Code-Aster, behalve als je het contactgebied vooraf kent en als
twee aparte vlakken opgeeft (U2.04.04 §2.2). De bridge meldt een self-contact
(of master = slave) als ERROR en slaat het over.

### 3.7 Contact en randvoorwaarden (symmetrie)

Ligt een slave-knoop ook op een symmetrievlak of een andere randvoorwaarde, dan
kan de wrijvingsvoorwaarde daarmee botsen; de matrix wordt singulier zodra er
contact is (U2.04.04 §4.7). Code-Aster-oplossingen:

- `SANS_GROUP_NO`: geen contact op die knopen, de randvoorwaarde wint
  (U2.04.04 §2.3.4). De bridge zet dit zelf voor knopen van een **fixed
  support** (§3.1); voor andere voorwaarden met `#ASTER-ZONE`;
- `SANS_GROUP_NO_FR` met `DIRE_EXCL_FROT`: sluit één wrijvingsrichting uit
  (U2.04.04 §4.7; niet door de bridge gezet);
- `ALGO_CONT='LAC'` heeft dit probleem niet (U2.04.04 §3.1.4).

Voorwaarden die knopen delen (pinned, frictionless, symmetry, displacement,
koppelingen) meldt de bridge vooraf met een WARNING met de selectienamen
(`bridge_mesh._report_constraint_overlaps`); oplossen doe je in Mecway. Zie ook
KNOWN_BUGS 8 (dubbele randvoorwaarden).

### 3.8 Alternatieven in Code-Aster

De bridge zet deze opties (behalve `LIAISON_MAIL`) niet zelf. Je kunt ze meegeven met `#ASTER`-regels
(§3.9), bijvoorbeeld `#ASTER-ZONE ALGO_CONT='PENALISATION'`.

| Optie | Waarvoor | Bron |
|---|---|---|
| `ALGO_CONT='PENALISATION'` met `ADAPTATION='ADAPT_COEF'` (CONTINUE) | Penalty zonder Mecway-stijfheid: Code-Aster kiest de stijfheid zelf uit `PENE_MAXI` (standaard 1e-2 × kleinste ribbe). Penalty met Mecway's stijfheid is de instelling `contact_algo` (§3.1). | U4.44.11, U2.04.04 §4.12 |
| `FORMULATION='DISCRETE'` | Weinig contactvrijheidsgraden zonder wrijving (`CONTRAINTE`); `GCP` voor veel. Kan geen delen aan die alleen door contact op hun plaats blijven. Met wrijving: liever CONTINUE. | U2.04.04 §3.4, §4.4 |
| `ALGO_CONT='LAC'` | Sterk niet-passende meshes, nauwkeurige contactdruk. Vraagt `CREA_MAILLAGE/DECOUPE_LAC`. Volgens U2.04.04 §3.1.4 nog zonder wrijving; de 17.4-catalogus accepteert LAC wel in het wrijvingsblok (NIET geverifieerd of dat werkt). | U2.04.04 §2.1, §3.1.4 |
| `GLISSIERE='OUI'` | Blijvend contact: vlakken blijven op elkaar (bilateraal), mogen glijden. | U4.44.11, U2.04.04 §4.1 |
| `AFFE_CHAR_MECA/LIAISON_MAIL` | Verlijmen van twee vlakken, ook met niet-passende meshes (geen contact). De bridge gebruikt het voor Mecway's verlijmde contact (§3.1); ook bruikbaar voor zeer lokaal contact of als voorberekening. | U4.44.01 §5.13, U2.04.04 §4.1, §4.5.2 |
| Veren `DIS_T` + `DIS_CHOC` | Puntcontact in een vaste richting (penalty); niet voor grote verplaatsingen. | U2.04.04 §4.10 |
| `CONTACT_INIT`, `SANS_GROUP_NO(_FR)` | Zie §3.4 en §3.7. | U4.44.11 |

### 3.9 Eigen Code-Aster-invoer: `#ASTER`-regels

Voor wat Mecway niet kan invoeren, zet je `#ASTER`-regels in een vrij tekstveld
van Mecway (OpenRadioss: `#ASTER`, Mystran: `$ASTER`, CCX: `**ASTER`). Syntax,
selectienamen (`<<Mecway-selectie>>`), valkuilen en doorgerekende voorbeelden
(o.a. `#ASTER-CONTACT`, `#ASTER-ZONE` en `#ASTER-OPTIE` bij contact) staan in
[`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md).

### 3.10 Voorbeeld: platen verlijmen (bonded contact tussen schalen)

Twee plaatdelen met elk een eigen mesh verbind je met Mecway's verlijmde contact; de
meshes hoeven niet op elkaar te passen. Voorbeeldmodel:
[`TestFiles/Voorbeelden/Voorbeeld_T.liml`](../TestFiles/Voorbeelden/Voorbeeld_T.liml)
(gemaakt met `maak_voorbeelden.py`, zelfde model als verificatiecase LS-07a).

**Model.** Ingeklemde plaatstrook 200 × 20 mm, dikte 2 mm, staal, uit twee delen:
`Deel_A` (x = 0..100 mm, 10 × 4 quad4) en `Deel_B` (x = 100..200 mm, 10 × 7 quad4, eigen
knopen). Ingeklemd op x = 0, 1 N in −Z op de vrije rand.

**Zo zet je het op in Mecway:**
1. Mesh de twee delen apart (eigen knopen, niet samenvoegen). Elk deel krijgt een
   materiaal met een plaatdikte (*Plate*).
2. Maak twee vlakselecties: de **master** = schaalvlakken van deel A langs de naad (hier
   de laatste rij elementen, `Lijm_A`; alle vlakken van A mag ook), de **slave** = de
   rand van deel B die op A ligt (`Lijm_B`; schaalranden selecteer je als vlakken van de
   elementen). Neem de fijnste kant als slave.
3. Voeg een contact toe met master `Lijm_A`, slave `Lijm_B` en als type verlijmd
   (*bonded*, in de `.liml` `type="bondedtie"`). Tolerantie 0 (automatisch) is goed:
   de bridge koppelt dan alle slave-knopen (geen `DISTANCE_MAX`). *Bonded elastic*
   wordt star verlijmd (de stijfheid wordt niet vertaald, gemeld).
4. Analyse lineair statisch (`lin_static_3d`): verlijmd contact is geen `DEFI_CONTACT`
   en werkt ook lineair.

**Wat de bridge ervan maakt:** `AFFE_CHAR_MECA` met `LIAISON_MAIL`
(`GROUP_MA_MAIT` = de schaalelementen van de master, `GROUP_NO_ESCL` = de knopen van de
slave-rand, `TYPE_RACCORD='COQUE'`, `DDL=('DX','DY','DZ','DRX','DRY')`). De rotaties in
het mastervlak gaan mee, dus de naad draagt een moment (geen scharnier). De rotatie om
de plaatnormaal (*drilling*, bij DKT alleen een fictieve stijfheid) laat de bridge weg:
met die koppeling stopt Code-Aster met `FACTOR_11` (singuliere matrix).

**Resultaat (geverifieerd, [Verificatie.md](Verificatie.md) LS-07):**

| Grootheid | Verlijmd (bridge) | Eén mesh (bridge) | Mecway, één mesh | Analytisch |
|---|---|---|---|---|
| doorbuiging tip | 0,94220 mm | 0,94257 mm | 0,94148 mm | 0,95238 mm |
| rotatie tip | 7,0899 mrad | 7,0938 mrad | 7,0901 mrad | 7,1429 mrad |

Analytisch is de Euler-balk P L³/(3EI) en P L²/(2EI) met E (niet E/(1−ν²)): met vrije
zijranden buigt de strook als een balk; de inklemming maakt hem iets stijver (−1,0 %).
De verlijmde strook wijkt 0,04 % af van één doorlopende mesh en 0,08 % van Mecway; de
rotatie is aan beide kanten van de naad gelijk (0,01 %).

**T-stuk** (rand van een rib verlijmd op het vlak van een plaat, LS-07c..e): de rib
brengt zijn moment via de lijm in de plaat. Ligt de voetlijn op een meshlijn van de
plaat, dan is de uitbuiging van de rib 0,1 % van die met gedeelde knopen (0,4 % van
Mecway). Ligt de voetlijn midden in de plaatelementen, dan interpoleert `LIAISON_MAIL`
de rotatie van de plaat lineair over de knik onder de rib: 5 % te stijf bij 4 mm
elementen, 11 % bij 12 mm. Leg de voetlijn dus op een meshlijn (of verfijn daar).

**Scheve of gekromde master** (LS-07f, g): `DDL` van `LIAISON_MAIL` kent alleen
globale componenten, dus de rotatie om de normaal kan daar alleen weg als de master
loodrecht op een globale as staat. Anders schrijft de bridge de koppeling zelf, per
slave-knoop als `LIAISON_DDL`: de drie verplaatsingen en de twee rotaties in het
raakvlak van de master in het geprojecteerde punt (dezelfde interpolatie als
`LIAISON_MAIL`). MUMPS ziet dan nog steeds ten onrechte een bijna-singuliere matrix
(de drilling-rotatie heeft alleen een fictieve stijfheid); de bridge zet daarom voor
die run `solver_nprec` op −1 (WARNING). Bij lineair statisch controleert `RESI_RELA`
de oplossing nog: dezelfde strook zonder inklemming stopt met `FACTOR_57`.

| Model | Verlijmd (bridge) | Referentie |
|---|---|---|
| strook 30° gedraaid (LS-07f), doorbuiging tip | 0,94220 mm | 0,94220 mm (LS-07a, in het XY-vlak) |
| buis R 20 mm, 16 en 24 elementen rond (LS-07g) | 2,7306e-4 mm | 2,7277e-4 mm (één mesh, 24 rond); Mecway 2,7235e-4 mm; Timoshenko 2,7233e-4 mm |

**Kwadratische schaal (tri6/quad8, `COQUE_3D`) als master** (LS-07i..k): de
middenknoop die Code-Aster toevoegt (QUAD9/TRIA7) heeft alleen rotaties, en
`LIAISON_MAIL` vraagt daar een verplaatsing (`CHARGES2_31`). De bridge schrijft de
verplaatsingen daarom zelf (`LIAISON_DDL` met de vormfuncties van de quad8/tri6) en laat
de rotaties bij `LIAISON_MAIL` (`DDL` alleen rotaties, de middenknoop telt dan mee).
Bij een scheve of gekromde kwadratische master zijn dat alle drie de rotaties, met
`solver_nprec` −1. Quad8-plaat 10 × 4 met een rib midden in de elementen, zijlast op
de rib: 1,1342e-2 mm, gedeelde knopen 1,1536e-2 mm (−1,7 %, de knik onder de rib),
30° gedraaid 1,1336e-2 mm.

**Beperkingen:**
- Een schaalvlak op een volume koppelt alleen de verplaatsingen; balkuiteinden als slave
  worden niet vertaald (KNOWN_BUGS 21).
- Mecway's eigen solver koppelt bij een schaalrand als slave geen rotaties: de verlijmde
  strook en het T-stuk worden daar een mechanisme (headless gemeten, Mecway 34). Een
  vergelijking met Mecway kan dus alleen met een doorlopende mesh.
- Schalen met een *Element offset* in het contact: de slave-knopen (altijd de
  Mecway-knopen) gaan naar de knopen van de master; alleen bij `LIAISON_MAIL` op een
  master op eigen knopen (volume op een quad8-schaal) naar het verschoven vlak. De
  bridge meldt welk vlak (WARNING); wat Mecway doet is niet nagelopen (KNOWN_BUGS 108).
  Schaal op schaal met een offset op eigen knopen (quad8/tri6): `solver_nprec` −1,
  anders onterecht `FACTOR_11` (LS-66: 0,94266 mm, Mecway doorlopend 0,94148 mm).

### 3.11 Delen die alleen door contact vastzitten

**Symptoom**: *Niet-lineair statisch* stopt in de eerste stap met `MECANONLINE9_4`
("matrice non inversible") en een pivot nul op DX, DY of DZ van een knoop, terwijl Mecway
het model zelf wel rekent. Vóór de run schrijft de bridge al:
`WARNING: Een deel van ... element(en) (...) wordt alleen door contact op zijn plaats gehouden (...)`.

**Oorzaak**: dat deel heeft geen eigen oplegging, verlijmd contact, koppeling of veer;
alleen contact houdt het op zijn plaats. Code-Aster's `STAT_NON_LINE` begint met de
stijfheid van de onvervormde toestand, waarin contact (en de Coulomb-wrijving) bij
contactdruk nul geen stijfheid langs het contactvlak geeft: het deel kan vrij schuiven of
draaien en de matrix is singulier. Mecway's penalty-contact (CCX) houdt het deel vanaf het
begin vast. Hetzelfde geldt voor de kant van een bout achter een *Pre-tension section* met
een kracht: die kracht is een last, de snede geeft geen stijfheid langs de bout
([Boutvoorspanning.md](Boutvoorspanning.md)). De bridge vindt zulke delen (verbonden via
elementen, verlijmd contact, koppelingen en constraint equations; opleggingen en elastic
supports tellen als vastgehouden) en noemt ze met hun elementen en contactselecties; ze
voegt zelf geen opleggingen toe.

**Oplossingen in Mecway** (één per deel):

1. Een zwakke **Elastic support** op een groot vlak van het deel (bijv. de bovenkant van
   een plaat): stijfheid × oppervlak orde 1e-5 .. 1e-4 van de eigen stijfheid E·A/L van het
   deel, zodat ze geen merkbare last draagt. Neem een groot vlak (of vlakken ver uit elkaar),
   zodat ook de rotaties vastliggen: op Samples/BoltedJoint gaf 1e9 Pa/m op het kleine
   eindvlak van plaat B (k·A = 2,5e5 N/m) nog een pivot nul (de rotatie om het eindvlak
   wordt aan het verre eind maar met ~70 N/m gehouden), 1e8 Pa/m op de hele bovenkant
   (4,4e5 N/m) niet meer.
2. Een **oplegging** waar het deel in werkelijkheid vastzit (Fixed, Frictionless,
   Displacement, symmetrie).
3. **Verlijmd contact** in plaats van contact als het deel niet mag schuiven of loskomen.
4. Bij een pre-tension section ook: *Length adjustment* in plaats van *Force* (de lengte
   ligt dan vast, de boutkant wordt langs zijn as gehouden).

Mecway's eigen tutorial AssemblyWithContact (handleiding v34 §17.7) beschrijft hetzelfde
probleem: de configuratie *Naive* faalt ook in Mecway omdat de delen alleen door wrijvingsloos
contact worden gehouden, en de remedies van de tutorial zijn een fixed support (om de oorzaak
te controleren), wrijving, een zwakke elastic support en een zachter (kwadratisch) oplopende
last. De bridge meldt de configuratie *Naive* ook (één deel van 10 elementen); de andere
modellen met contact in de verificatie (NL-03, NL-30, PipeClip, Voorbeeld_C) worden niet
gemeld.

**Samples/BoltedJoint** (28 oktober 2026): er worden twee delen gemeld, plaat B (gehouden
door wrijvingscontact met plaat A en door het moercontact) en het bovenste deel van de bout
(moercontact en de voorspankracht). Met een zwakke elastic support op beide (1e8 Pa/m op de
bovenkant van plaat B, 1e9 Pa/m op het moervlak) zijn de pivots nul op DX/DY/DZ weg. Het
wrijvingscontact (coëfficiënt 0,5) zelf convergeert in Code-Aster dan nog niet: met
*Contactmethode* = PENALISATION een pivot nul op de wrijvingsvrijheidsgraden (`LAGS_F`) van
knopen van plaat B zonder contactdruk, met `CONTACT_INIT='NON'`, `ALGO_FROT` standaard of
gepenaliseerd, `ALGO_RESO_FROT='POINT_FIXE'`, `INTEGRATION='GAUSS'`, een kleinere
wrijvingspenalty, een oplopende voorspanning of `solver_nprec` −1 geen convergentie in de
eerste stap (KNOWN_BUGS 43). Zonder wrijving (coëfficiënt 0) en met de twee zwakke steunen
rekent het model; de voorspanfase (t = 0,1, geen externe kracht) is dan van dezelfde orde als
Mecway met dezelfde steunen (verplaatsingen van de bout binnen ~20%, spanningen binnen ~35%
op dit grove mesh van 76 hex20-elementen).

---

## 4. "Mijn berekening convergeert niet"

### 4.1 Wat de bridge dan doet

- Code-Aster stopt `STAT_NON_LINE`/`DYNA_NON_LINE` met een `ConvergenceError`,
  meestal `MECANONLINE9_7` (te veel Newton-iteraties). De opgeslagen stappen blijven
  bewaard (EDF R&D, U4.51.03, "Shutdown management"; tekst van `MECANONLINE9_7` in 17.4).
- De bridge vangt die fout op (`try/except` in de `.comm`), schrijft
  `BRIDGE_ONVOLLEDIG <tijd>` in de `.mess` en gaat door met de nabewerking.
- In Mecway verschijnt de melding met de foutcode, een advies en "Laatste tijdstip
  met resultaten: ... s".
- **Dynamisch**: alle uitvoertijden tot dat tijdstip gaan naar Mecway.
- **Statisch**: route `liml` alle gearchiveerde stappen tot dat tijdstip, route
  `tabel` alleen het laatst bereikte tijdstip (§2.1).
- Een andere Code-Aster-fout in de stappenlus (bijv. `DVP_2`, een te sterk vervormd
  element) gaat op dezelfde manier, als er al een stap na het begin gearchiveerd is: bij
  elke Code-Aster-fout staat het resultaat met de stappen tot dan in de `.comm`
  (gezien met 17.4 bij `FONCT0_9` in stap 12 van 20: resultaten tot t = 0,5). Mecway
  toont die foutcode met "Laatste tijdstip met resultaten". Een fout vóór de eerste
  stap, of een Python-fout, stopt de run zonder resultaten.
- Andere foutcodes, met oorzaak en oplossingen: [`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md).

### 4.2 Stappenplan

Werk van boven naar beneden. Bron: EDF R&D, U2.04.04 §4.1 en §4.5, U2.04.01; Mecway
(2026) §6.2.3. Volgens U2.04.04 §4.1 hebben contactproblemen "very often" een
fysische oorzaak, geen numerieke.

1. **Lees de melding.** Kijk in `<model>_<run-id>_bridge_log.txt` (overgeslagen contacten, WARNINGs)
   en de `.mess` (convergentietabel: residu, contactstatus, penetratie).
2. **Controleer het model.**
   - master/slave-keuze (§3.2), normalen (§3.3);
   - beginspleten en -penetraties (§3.4);
   - delen die alleen via contact vastzitten (§3.4);
   - randvoorwaarden op slave-knopen (§3.7);
   - overgeslagen contactparen of self-contact (§3.6);
   - mislukte integratie van de materiaalwet kan komen door een element dat door
     het contact binnenstebuiten klapt (U2.04.04 §4.1, figuur 4.1-1).
3. **Kijk naar het residu** (convergentiescherm, grafiek (a)):
   - `RESI_GLOB_RELA` blijft hoog terwijl `RESI_GLOB_MAXI` heel klein is (beweging
     zonder weerstand): `convergence_criterion` = `MAXI` (§2.2, R-RIGID);
   - `RESI_GLOB_RELA` stagneert net boven het criterium (plastische volumes,
     `GDEF_LOG`; bijv. ~2e-6 bij 1e-6): `convergence_resi_rela` = 1e-5 (de standaard),
     of `convergence_criterion` = `RELA_OF_MAXI` met `convergence_resi_maxi` boven de
     absolute rest waarop het stagneert (§2.2, NL-01, NL-01b).
4. **Ontkoppel de niet-lineariteiten** (U2.04.04 §4.5.1). Zet ze niet allemaal
   tegelijk aan:
   1. alleen contact, lineair elastisch materiaal, `deformation` = `PETIT`
      (haal in Mecway de hardingscurve weg);
   2. plasticiteit zonder contact (contact in Mecway onderdrukken);
   3. eventueel grote vervorming zonder contact en zonder plasticiteit; lukt dat
      niet, probeer een andere `deformation` (`SIMO_MIEHE`, `GDEF_LOG`,
      `PETIT_REAC`).
5. **Wrijving later.** Begin zonder wrijving (coëfficiënt 0 in Mecway)
   (U2.04.04 §4.1).
6. **Contactmethode.** Bij lijncontact, contact dat verloren gaat of
   `MECANONLINE9_4` met `LAGS_C`: `contact_algo` = `PENALISATION` (§3.1, NL-03b).
7. **Kleinere stappen.** Verklein Mecway's *Time step size* (statisch; zonder
   stapgrootte `substeps_per_interval` verhogen) of verhoog `substeps_per_output`
   (impliciet; of verklein Mecway's *Time step size*). Code-Aster knipt een mislukte stap al zelf
   (`DECOUPE`, tot 6 niveaus, §2.1); kleinere beginstappen helpen als hij steeds
   op hetzelfde tijdstip vastloopt. Niet bij stagnatie van het residu (stap 3):
   kleinere stappen maken dat erger (R-SUB40).
8. **Newton.** Houd `newton_reac_iter` = 1 (R-REAC0). Verhoog `newton_max_iter` bij
   contact (U4.51.03). `PREDICTION='ELASTIQUE'` helpt volgens U2.04.04 §4.5.2, maar
   is niet instelbaar in de bridge.
9. **Grote rekken.** Boven ca. 5 % rek: `GDEF_LOG` of `SIMO_MIEHE` in plaats van
   `PETIT` (§2.3).
10. **Laatste redmiddel voor quasi-statisch:** reken langzaam dynamisch
    (`dyna_impl_3d`) over een lange tijd, met de echte dichtheid en grote stappen.
    De massa stabiliseert; controleer dat de traagheidskrachten klein blijven
    (U2.04.04 §4.5.3).
11. **Geconvergeerd is niet hetzelfde als juist** (U2.04.04 §4.1). Controleer
    penetratie, oscillaties in de contactdruk en zo nodig een meshconvergentiestudie.

Niet als instelling, wel met `#ASTER-CONTACT`/`#ASTER-ZONE` (§3.9), volgens
U2.04.04: `ADAPTATION` (§4.12), `ALGO_RESO_FROT='POINT_FIXE'` bij wrijving (§4.1),
`RESI_GEOM`, `ITER_GEOM_MAXI`, `LISSAGE='OUI'` bij gekromde grove vlakken (§2.4.3).
Alleen met de hand in de `.comm`: een voorspellende berekening met
`PREDICTION='DEPL_CALCULE'` (§4.1).

### 4.3 Wat Code-Aster niet kan

- **Geen elementverwijdering.** Doorsnijden of bezwijken waarbij elementen
  verdwijnen (erosie, zoals in expliciete crashcodes) staat niet in de gelezen
  Code-Aster-documentatie (NIET gevonden). Schade wordt als interne variabele
  gemodelleerd; het element blijft in het mesh (bijv. `ENDO_HETEROGENE`:
  "gebroken" element = schadevariabele 1, EDF R&D, U4.51.11). Een berekening die tot
  doorsnijden gaat, convergeert dus niet meer of geeft zwaar vervormde elementen.
  De bridge kan wel **bezwijken van elementen** nabootsen: een element boven een
  grens voor de plastische rek krijgt een zeer lage stijfheid en spanning nul
  (niet-lineair statisch en dynamisch; [`Bezwijken.md`](Bezwijken.md)).
- **Schade- en breukmodellen bestaan wel**, maar de bridge ondersteunt ze niet
  (alleen `ELAS`, `VMIS_ISOT_*`/`VMIS_CINE_LINE`, `CABLE` en de discrete wetten, §1):
  - `ROUSSELIER` (ductiele breuk door holtegroei; met `SIMO_MIEHE`);
  - `ENDO_*`-wetten (o.a. `ENDO_ISOT_BETON`, `ENDO_SCALAIRE`, `ENDO_CARRE`);
  - cohesieve zones `CZM_*` met voegelementen, of in XFEM (`ALGO_CONT='CZM'`).
  (U4.51.11, U4.44.11.)
- **HOMARD** (`MACR_ADAP_MAIL`) is mesh-adaptatie: het verfijnt of vergroft een
  bestaand mesh op basis van een veld of een geometrische regel, en kan velden
  overzetten (EDF R&D, U7.03.01). Het is geen automatisch hermeshen van vervormde
  elementen en geen elementverwijdering. Niet ondersteund door de bridge.

### 4.4 Convergentiescherm

Bij elke analyse opent de bridge een apart venster (startscherm: "Convergentie- en
meldingenscherm", standaard aan). Bij een niet-lineaire analyse (`STAT_NON_LINE`, `DYNA_NON_LINE`,
`THER_NON_LINE`) volgt het de convergentie live; bij een lineair-statische
analyse (`MECA_STATIQUE`) toont het de lineaire oplosser (zie *Lineaire analyse*
hieronder); bij `THER_LINEAIRE` de meldingen (fouten en alarmen met uitleg in de
gekozen taal) en de diagnose. Achteraf: de
knop *Convergentiescherm* in het hoofdvenster van de bridge toont de laatste run uit
de werkmap; met "Open .mess ..." kies je een ander bestand. De knoppen bovenaan horen bij de getoonde run: *Samenvatting* opent `<model>_<run-id>_aster_summary.txt` in de standaard-teksteditor (gemaakt uit de `.mess` als het ontbreekt; [Handleiding §5.2](Handleiding.md#52-samenvatting-van-de-code-aster-run)), *.comm* en *.mail* openen het bestand in Kladblok (deze extensies hebben geen bestandskoppeling; grijs als het bestand ontbreekt), *Map* opent de Verkenner op de werkmap met de `.mess` geselecteerd, *ParaView* opent `<model>_<run-id>.rmed` (alleen met *MED-bestand voor ParaView*; anders zegt het scherm dat; welke ParaView: instelling *ParaView*, [Handleiding §3](Handleiding.md#3-het-hoofdvenster)), *Opnieuw lezen* leest de bron opnieuw. Het scherm blijft open
naast Mecway en het hoofdvenster. Het venster draait in de Python van Code-Aster; sluiten
heeft geen invloed op de run of op Mecway.

| Grafiek | Wat je ziet | Waar je op let |
|---|---|---|
| (a) Residu | `RESI_GLOB_RELA` (links, rode lijn = criterium) en `RESI_GLOB_MAXI` (rechts) per Newton-iteratie, voor de laatste N rekenpogingen | Gezond: per poging een snelle daling tot onder de rode lijn. Blijft het residu rond 1 of springt het op en neer, kijk dan naar (d). Blijft `RELA` hoog bij een `MAXI` van ~0, of stagneert `RELA` net boven de lijn: §4.2 stap 3. |
| (b) Voortgang | Tijdstip per rekenpoging; rood = mislukt (Code-Aster deelt de stap op), grijze trap = opdelingsniveau | Veel rode punten op hetzelfde tijdstip: de berekening loopt daar vast. Kijk wat er dan fysisch gebeurt (eerste contact, doorsnijden, §4.3). |
| (c) Newton per poging | Iteraties per poging met `ITER_GLOB_MAXI`; zwarte punten = geometrische contactlussen | Stijgend aantal iteraties vóór een mislukking: de stap is te groot of het contact verandert sterk (§4.2 stap 7 en 8). |
| (d) Contact | Per Newton-iteratie: statuswisselingen (grijze balken, kolom `VARI. CONT.`), `PRESSURE ERROR` en `CRITERE VALEUR` aan het eind van een geometrische lus (G2, G3 ...) | Gaan de statuswisselingen niet naar 0, dan springen punten tussen contact en geen contact: controleer master/slave, normalen en beginspleten (§3.2-3.4). Zonder contact en met `energy_balance` aan: de energiebalans. |
| (e) Meldingen | Fouten en alarmen met de Code-Aster-code en uitleg | "Pivot nul ... component LAGS_C": contactvoorwaarde overbepaald of een deel hangt alleen aan contact (§3.4, §3.7). "Python-fout in `<model>_<run-id>.comm`": meestal een tikfout in `#ASTER`-regels. |

Onder de grafieken staan de details van de gekozen poging (schuif "Poging" of klik
in (b)/(c)): aantal contactliaisons, statuswisselingen, de knoop met het grootste
residu en de CPU-tijd. De geschatte resttijd volgt uit het percentage van
Code-Aster en is ruw. Dat `VARI. CONT.` het aantal statuswisselingen is, is een
lezing van de bridge; de U-documentatie zegt het niet zo (NIET geverifieerd).

`energy_balance` (Energiebalans; alleen impliciete dynamica, standaard uit) zet
`ENERGIE=_F()` in `DYNA_NON_LINE` (EDF R&D, U4.53.01 §3.22); de uitkomst verandert
niet (R-ENERGY). Met contact `CONTINUE` stopt Code-Aster dan met `MECANONLINE5_15`;
de bridge laat het in dat geval weg en meldt dat in het log.

#### Lineaire analyse (`MECA_STATIQUE`)

Een lineaire analyse heeft geen Newton-iteraties: Code-Aster bouwt de
stijfheidsmatrix en lost Ku = F één keer op. Zoals de solver-monitor van
gangbare pre/post-software toont het scherm dan vier kaarten (de bridge zet
`INFO=2` in `MECA_STATIQUE`, §2.6):

| Kaart | Wat je ziet | Waar je op let |
|---|---|---|
| (a) Stelsel en oplosser | Aantal vergelijkingen (fysieke vrijheidsgraden + Lagrange-parameters van opleggingen en koppelingen), knopen, niet-nul-termen en vulling van de matrix; bij MUMPS ook de ordening (METIS, AMF ...), termen in de factoren, het werk in flop, het geheugen en de pivots; de criteria (`RESI_RELA`, `NPREC`) | Geheugen bijna gelijk aan `memory_limit`: verhoog die of gebruik GCPC. Oranje pivots: zie (d). |
| (b) Tijdverloop per fase | Stijfheidsmatrix (elementen + assemblage), analyse (ordening), factorisatie, belastingsvector, oplossen, spanningen + opslag; tijdens de run loopt de actieve fase (blauw) live mee | Bij grote modellen domineert de factorisatie. MUMPS meldt pas aan het eind van een fase dat die klaar is; het geschatte werk (flop) staat in (a). |
| (c) Kwaliteit (MUMPS) | Op log-schaal: geschaald residu, 'backward errors' ω₁/ω₂, de foutgrens (rood gestippeld: `RESI_RELA`) en de conditiegetallen (groen < 1e4, oranje > 1e12) | De foutgrens moet links van de rode lijn liggen. |
| (c) Residu (GCPC) | Relatief residu ‖r‖/‖f‖ per iteratie op log-schaal, met `RESI_RELA` | Een lange vlakke trap = trage convergentie. |
| (d) Beoordeling | Groen = in orde, grijs = informatie, oranje = let op, rood = fout, met uitleg | Zie de tabel hieronder. |

Wat de getallen betekenen (EDF R&D, U2.08.03 §7.2.1; MUMPS-handleiding: RINFOG(6)-(11)):

- **Foutgrens** (RINFOG(9)): bovengrens voor de relatieve fout in de
  verplaatsingen, ongeveer conditiegetal × backward error. Code-Aster vergelijkt
  hem met `RESI_RELA`; groter = stop met `FACTOR_57`. In de testmodellen
  (252 tot 268 569 vergelijkingen): 1e-11 tot 1e-8.
- **Backward error** ω₁, ω₂ (RINFOG(7)/(8)): hoe goed de berekende oplossing het
  stelsel zelf oplost. Bij een gezonde factorisatie in de orde van de
  machineprecisie (~1e-15). Groter dan 1e-12 (grens van de bridge) wijst op
  numerieke moeite van de factorisatie.
- **Conditiegetal** (RINFOG(10)/(11)): gevoeligheid van de oplossing voor
  afrondfouten. Volgens U2.08.03 ligt het tussen 1e4 (goed geconditioneerd) en
  1e20 (zeer slecht); in de testmodellen 5e4 tot 2e7. Boven 1e12
  wijst het op een (bijna) singuliere matrix (U2.08.03 §7.1): een deel dat niet of nauwelijks is
  vastgehouden, een mechanisme, of extreme stijfheidsverschillen (bijv. een
  zeer stijve veer naast een slap deel). Gemeten: 2e16 bij een blok dat alleen in
  X is vastgehouden (R-FREE: 5,8e16, foutgrens 12,6).
- **Residu voor/na iteratieve verfijning**: MUMPS verbetert de oplossing met
  enkele extra stappen als dat helpt (`POSTTRAITEMENTS='AUTO'`, maximaal 4,
  U4.50.01 §3.5.3); 0 stappen betekent dat de eerste oplossing al goed was.
- **Negatieve pivots**: een stelsel met Lagrange-parameters is niet positief
  definiet; in de testruns was het aantal negatieve pivots gelijk aan het aantal
  Lagrange-parameters. Zijn het er meer, dan is de stijfheid zelf niet positief
  definiet (mechanisme of negatieve stijfheid; gemeten: 10 bij 8 Lagrange met een
  vrij bewegend blok). Dit is een afleiding van de bridge (NIET geverifieerd in de
  U-documentatie).
- **Uitgestelde pivots** (INFOG(13)): MUMPS moest numeriek pivoteren; een paar is
  onschuldig, veel wijst op een slecht geschaald stelsel.
- **GCPC**: Code-Aster schrijft een iteratie alleen als het residu met een factor
  10 gedaald is (`gcpc.F90`, `paraaf = 0.1`; elke iteratie alleen bij `INFO=3`,
  dat `MECA_STATIQUE` niet toestaat). De grafiek is daarom een trap. Meer dan
  20 % van het aantal vergelijkingen aan iteraties markeert de bridge als traag
  (keuze van de bridge).

Bij een melding `FACTOR_57` (foutgrens > `RESI_RELA`) is de oorzaak bijna altijd
de invoer, niet de oplosser: zoek het deel dat vrij kan bewegen (zie
[`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md)). `RESI_RELA` groter zetten
verbergt dat alleen (U2.08.03 §7.2.1: "doit être prise au sérieux").

---

## 5. Bronnen

**Code-Aster-documentatie** (EDF R&D, versie "default"; in de tekst als
"EDF R&D, U4.51.03" of, binnen een alinea, alleen het documentnummer). De
standaardwaarden zijn tegen de 17.4-catalogus gecontroleerd.

- EDF R&D (2020). *Notice d'utilisation des solveurs linéaires*, U2.08.03. Gelezen: versie 11-01-2024, `https://code-aster.org/doc/default/fr/man_u/u2/u2.08.03.pdf` (§3 keuze van de oplosser, §7.1 singuliere matrix, §7.2.1 foutgrens en conditiegetal). Lokaal: versie 05-05-2020.
- EDF R&D (2020). *Opérateur STAT_NON_LINE*, U4.51.03, 30-04-2020. Lokaal; online "Calculation parametrization", "Nonlinear solver settings", "Convergence settings".
- EDF R&D (2021). *Mot clé SOLVEUR*, U4.50.01. Gelezen: versie 11-01-2024, `https://code-aster.org/doc/default/fr/man_u/u4/u4.50.01.pdf` (§3.5.3 `RESI_RELA`/`POSTTRAITEMENTS`, §3.6 GCPC, §3.7 PETSC). Lokaal: versie 04-11-2021.
- EDF R&D (2021). *Opérateur DEFI_CONTACT*, U4.44.11, 04-11-2021. Lokaal en online (alle operanden).
- EDF R&D (2021). *Opérateur DEFI_MATERIAU*, U4.43.01, 03-11-2021. Lokaal (`TRACTION` §5.1.1).
- EDF R&D (2021). *Opérateurs AFFE_CHAR_MECA*, U4.44.01, 04-11-2021. Lokaal (`LIAISON_MAIL` §5.13).
- EDF R&D (z.j.). *Instructions for using contact in code_aster*, U2.04.04. Online, §1 tot §4.
- EDF R&D (z.j.). *Tips for using STAT_NON_LINE*, U2.04.01. Online, "Introduction" en "Convergence tools".
- EDF R&D (z.j.). *General tips for using DYNA_NON_LINE*, U2.06.13. Online, "Discretization of the ongoing problem" en "Optimizing performance".
- EDF R&D (z.j.). *Operator DEFI_LIST_INST*, U4.34.03. Online, "DEFI_LIST" en "ECHEC".
- EDF R&D (z.j.). *Operator DYNA_NON_LINE*, U4.53.01. Online, "Operands" (`SCHEMA_TEMPS`, `MASS_DIAG`, `ENERGIE`).
- EDF R&D (z.j.). *Nonlinear behaviors, keyword COMPORTEMENT*, U4.51.11. Online, `DEFORMATION`, schademodellen.
- EDF R&D (z.j.). *Macro-command MACR_ADAP_MAIL*, U7.03.01. Online, doel.

Lokaal = Engelse machinevertaling in een lokale map met Code-Aster-documentatie.
Online = DocAster, `https://docaster-en-codeaster-doc-4113bb35b8213385c636b94f1536856d7f617.gitlab.io/manuals/man_u/`
(`u2/u2.04.04/index.html` enz.), geraadpleegd 5 oktober 2026; de site vermeldt geen
versienummer.

**Code-Aster-installatie** (EDF R&D, code_aster 17.4, Windows-build v2025):
`%LOCALAPPDATA%/code_aster/v2025/17.4/lib/aster/code_aster/`

- `Cata/Commands/defi_contact.py`, `stat_non_line.py`, `dyna_non_line.py`,
  `defi_list_inst.py`, `meca_statique.py` (`INFO` 1 of 2);
- `Cata/Commons/c_convergence.py`, `c_newton.py`, `c_comportement.py`,
  `c_solveur.py`;
- `Messages/contact2.py` (`CONTACT2_16`), `contact3.py` (`CONTACT3_16`),
  `mecanonline9.py` (`MECANONLINE9_7`), `subdivise.py` (`SUBDIVISE_3`).
- GCPC-uitvoer: `bibfor/algeline/gcpc.F90` in `https://gitlab.com/codeaster/src`
  (welke iteraties bij `INFO=2` geschreven worden).

**Mecway**: Mecway (2026). *Mecway Finite Element Analysis, Manual, version 33*,
`C:\Program Files\Mecway\manual.pdf`: §6.2 (niet-lineair statisch, convergentie),
§9.9 (contact), §9.14 (druk), §9.20 (centrifugaalkracht).

**Literatuur**

- Belytschko, T., Liu, W.K. en Moran, B. (2000). *Nonlinear Finite Elements for Continua and Structures*. Chichester: Wiley. Stabiele stap van centrale differenties met demping (geciteerd in `bridge_to_aster._damped_step_factor`; paragraaf NIET in het boek gecontroleerd).
- Hilber, H.M., Hughes, T.J.R. en Taylor, R.L. (1977). Improved numerical dissipation for time integration algorithms in structural dynamics. *Earthquake Engineering and Structural Dynamics*, 5, 283–292.
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite Element Analysis*. Mineola: Dover. Hoofdstuk 9.

**Bridge-code**: `Scripts/bridge_utils.py` (`resolve_auto_analysis`),
`Scripts/bridge_to_aster.py` (`_build_nonlin_static`, `_build_listinst_block`,
`_build_contact_block`, `_build_dyna_listinst_block`, `_critical_time_step`,
`_build_etat_init_block`, `_build_comportement_block`, `_deformation_for`,
`_convergence_args`), `Scripts/bridge_mesh.py` (`_merge_contact_zones`,
`_exclude_fixed_slaves`, `_check_contact_sides`, `_report_constraint_overlaps`),
`Scripts/bridge_run_aster.py`, `Scripts/bridge_gui.py`.
