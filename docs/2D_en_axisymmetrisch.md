# 2D- en axisymmetrische analyses

*English version: [2D_and_axisymmetric.md](en/2D_and_axisymmetric.md)*

De bridge vertaalt de statische en dynamische 2D-analysetypen van Mecway naar
Code-Aster `MECA_STATIQUE` of `DYNA_NON_LINE` met vlakke elementen (U3.13.01
"Modélisations AXIS, D_PLAN, C_PLAN"):

| Mecway-analyse | Mecway-materiaal | Code-Aster | Resultaat in Mecway |
|---|---|---|---|
| Static 2D (S20) | *Shell/membrane* met een dikte | `C_PLAN` (vlakke spanning) | verplaatsing X, Y; spanning (σ_zz = 0); von Mises; reacties voor de dikte t |
| Static 2D (S20) | *Shell/membrane* met een dikte en *plane strain* | `D_PLAN` (vlakke rek) | als hierboven, σ_zz = ν(σ_xx + σ_yy) |
| Static Axisymmetric (SA0) | geen geometrie (isotroop materiaal) | `AXIS` | verplaatsing X (radiaal), Y (axiaal); spanning met `stresszz` = tangentiële spanning (hoop stress); reacties voor 360 graden |
| Dynamic Response 2D (D20), Dynamic Response Axisymmetric (DA0) | als S20 / SA0 | als S20 / SA0, in de tijd (§2.4) | als S20 / SA0 per uitvoertijd, plus snelheid en versnelling |
| Acoustic Resonance 2D (A20) | *Speed of sound* (een dikte telt niet) | `PHENOMENE='ACOUSTIQUE'`, `PLAN` (§4) | per mode de frequentie en het drukveld `pressure`, als A30 |

De bridge-analyse is `lin_static_3d` ("Statisch") voor S20 en SA0 en `dyna_impl_3d`
("Dynamisch (impliciet)") voor D20 en DA0: met *Actieve analyse (auto = volgens Mecway)*
= `auto` kiest de bridge die. Algemene werking van de bridge:
[`Handleiding.md`](Handleiding.md). Acoustic Resonance 2D (A20) gaat naar de akoestische holtemodes `acoustic_modes_3d` (§4). Mecway heeft geen thermisch 2D-type: een thermisch model in een vlak
maak je met schalen ([`Thermisch.md`](Thermisch.md)); axisymmetrisch warmtetransport: nog niet (§3).

![Axisymmetrisch: symmetrieas, straal en tangentiële richting](img/2d_axisymmetric_axes.svg)

1. Mecway's Y-as: de symmetrieas (SA0, Code-Aster `AXIS`).
2. Mecway's X-as: de straal r; alle knopen bij X ≥ 0.
3. De vlakke elementen in het XY-vlak: een doorsnede van het lichaam.
4. Straal r van een punt: Code-Aster integreert per radiaal (r dθ), de bridge vermenigvuldigt krachten en reacties met 2π.
5. Tangentiële richting θ: `stresszz` is de tangentiële spanning σ_θ (hoop stress).
6. De ring die de elementen voorstellen (360 graden): Mecway's krachten en reacties gelden voor deze hele ring.

![Vlakke spanning en vlakke rek: vlak en dikte](img/2d_plane_thickness.svg)

1. De vlakke elementen in het XY-vlak (Z = 0).
2. Dikte t: de *Shell/membrane*-dikte van het materiaal (S20); Mecway's krachten en reacties gelden voor de hele t, Code-Aster rekent per eenheid van dikte.
3. Een rand van de vlakke elementen (faceid 1..4): druk, traction en een randkracht werken op zo'n rand (randcellen `SEG2`/`SEG3`).
4. Een belasting op de rand, in het XY-vlak.
5. σ_zz, loodrecht op het vlak: 0 bij vlakke spanning (`C_PLAN`), ν(σ_xx + σ_yy) bij vlakke rek (`D_PLAN`).

## 1. Werkwijze stap voor stap

**Kies eerst de route.** Een 2D-model komt op een van twee manieren bij de bridge. De mesh is
dezelfde (vlakke elementen in het XY-vlak); de routes verschillen in het Mecway-analysetype en
in een regel tekst:

- **Route B: Mecway's eigen 2D-type.** *Static 2D* (S20), *Static Axisymmetric* (SA0),
  *Dynamic Response 2D* (D20) of *Dynamic Response Axisymmetric* (DA0). Alleen lineair. Geen
  extra regel. Mecway rekent hetzelfde model zelf, dus zijn eigen oplossing is een referentie
  (§5).
- **Route A: een 3D-type van Mecway op vlakke elementen.** *Nonlinear Static* (L30) of *Static
  3D* (S30). In een 3D-type
  behandelt Mecway de vlakke elementen als shells, dus het materiaal heeft een geometrie
  *Shell/membrane* met een dikte nodig. Een regel in CCX > *Custom model definition*,
  `**ASTER-PLANE C_PLAN` (vlakke spanning), `**ASTER-PLANE D_PLAN` (vlakke rek) of
  `**ASTER-PLANE AXIS` (axisymmetrisch), laat de bridge elk element als dat 2D-element rekenen
  in plaats van als shell. Mecway's eigen solver negeert de regel en rekent shells.
  Warmtetransport in een vlak (T30/T31 zonder de regel) is al een thermisch 2D-model (`PLAN`);
  de regel in T30/T31 is een ERROR (§1.6).
- **Nooit allebei.** De regel in een S20-, SA0-, D20- of DA0-model is een ERROR (§1.6). Een
  model heeft een regel; die geldt voor alle elementen.

![Route B en route A: dezelfde vlakke elementen in een 2D-type en in een 3D-type met de regel](img/2d_route_a_b.svg)

1. Route B: een 2D-analysetype van Mecway (S20, SA0, D20, DA0); de vlakke elementen zoals ze zijn, niets toevoegen.
2. Route A: een 3D-analysetype van Mecway (L30, S30) op dezelfde vlakke elementen in het XY-vlak (Z = 0); Mecway behandelt ze als shells.
3. De shell-dikte t (materiaalgeometrie *Shell/membrane*): Mecway heeft hem nodig in route A; `C_PLAN` en `D_PLAN` gebruiken hem als dikte (§2.2), `AXIS` negeert hem.
4. Het tekstveld CCX > *Custom model definition* in de outline-boom; het staat er als CCX de solver is in *Analysis settings* ([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §1).
5. De regel `**ASTER-PLANE C_PLAN`, `**ASTER-PLANE D_PLAN` of `**ASTER-PLANE AXIS` in dat veld: de bridge rekent de shells als elementen in vlakke spanning, vlakke rek of axisymmetrisch.

**Keuzetabel.** Zoek de rij van wat je wilt rekenen; de rij geeft het Mecway-analysetype (in
*Analysis settings*), de route, de elementen en het materiaal, de regel en waar het staat
uitgelegd. "Voorbeeld n" is een uitgewerkt voorbeeld met een modelbestand in §1.5.

| Wat je wilt | Mecway-analysetype | Route | Elementen en materiaal | Regel in CCX > *Custom model definition* | Waar |
|---|---|---|---|---|---|
| Lineair statisch, vlakke spanning of vlakke rek, ook met een temperatuur (thermische spanning) | *Static 2D* (S20) | B | vlakke elementen; materiaal *Shell/membrane* met de dikte t, voor vlakke rek ook *plane strain* aangevinkt | geen | §1.1 … §1.3, §2.5 |
| Lineair statisch, axisymmetrisch, ook met een temperatuur | *Static Axisymmetric* (SA0) | B | vlakke elementen bij X ≥ 0 (Y = as); materiaal zonder geometrie | geen | §1.1 … §1.3, §2.5; voorbeeld 1 |
| Lineaire dynamica in de tijd | *Dynamic Response 2D* (D20) of *Dynamic Response Axisymmetric* (DA0) | B | zoals S20 / SA0, met een dichtheid; geen temperatuur | geen | §1.1, §2.4 |
| Akoestische holtemodes in 2D | *Acoustic Resonance 2D* (A20) | – | vlakke elementen; *Speed of sound* | geen | §4 |
| Plasticiteit, grote vervormingen, laststappen (tijdtabellen), vlakke spanning of vlakke rek | *Nonlinear Static* (L30) | A | vlakke shell-elementen in het XY-vlak; *Shell/membrane* met de dikte t; plasticiteit zoals in 3D | `**ASTER-PLANE C_PLAN` of `**ASTER-PLANE D_PLAN` | §1.4; voorbeeld 3 |
| Hetzelfde, axisymmetrisch | *Nonlinear Static* (L30) | A | vlakke shell-elementen bij X ≥ 0; *Shell/membrane* met een willekeurige dikte (telt niet) | `**ASTER-PLANE AXIS` | §1.4; voorbeeld 2 |
| Contact tussen delen (krimpverbinding, delen die elkaar raken), ook met wrijving | alleen *Nonlinear Static* (L30) | A | zoals de twee rijen hierboven, plus een *Contact* (unilateraal) tussen twee vlakselecties van randen | `**ASTER-PLANE C_PLAN`, `D_PLAN` of `AXIS` | §1.4 punt 6; voorbeeld 4 |
| Lineair statisch als 3D-model (bijv. om te vergelijken met Mecway's eigen shell-solve) | *Static 3D* (S30) | A | zoals bij L30; geen contact | `**ASTER-PLANE C_PLAN` (nagelopen, PL-33); `D_PLAN` en `AXIS` volgen dezelfde route, niet nagelopen in S30 | §1.4; voorbeeld 3 |
| Warmtetransport in een vlak | *Thermal Steady State* (T30) of *Thermal Transient* (T31) | – (thermisch 3D-type, geen regel) | vlakke shell-elementen; de shell-dikte telt mee | geen (de bridge rekent `PLAN`) | [`Thermisch.md`](Thermisch.md) |
| Warmtetransport axisymmetrisch, de keten thermisch -> mechanisch in 2D | – | – | – | nog niet | §3 |
| Axisymmetrische schalen (lijnelementen) | – | – | – | nog niet | §3 |
| Niet-lineaire dynamica, modes, knik in 2D | – | – | – | niet mogelijk | §3 |

Waar typ je de regel: Mecway rekent L30 alleen met CCX; kies CCX ook voor S30 als
solver in *Analysis settings*, dan staat de tak CCX met *Custom model definition* in de
outline-boom. Het veld van een andere solver werkt ook, met het voorvoegsel van die solver:
`#ASTER-PLANE` in een OpenRadioss-veld, `$ASTER-PLANE` in een Mystran-veld
([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §1); `-VLAK` is de Nederlandse
spelling (`**ASTER-VLAK AXIS`). De bridge leest de regel welke solver er ook gekozen is.

### 1.1 In Mecway: het model (route B)

1. **Analysetype.** *Static 2D*, *Static Axisymmetric*, *Dynamic Response 2D* of
   *Dynamic Response Axisymmetric* in de analyse-instellingen (dynamisch: *Time period*,
   *Time step size* en *Generate solution every n time steps*; geen *Mode
   superposition*).
2. **Mesh.** Vlakke elementen tri3, tri6, quad4 of quad8 in het XY-vlak, alle knopen met
   Z = 0 (Mecway negeert Z; de bridge stopt als Z ≠ 0, §3). Axisymmetrisch: Y is de
   symmetrieas, X de straal, alle knopen met X ≥ 0 (Mecway Ltd., 2026, §6.1.3, §7.2).
   Kwadratische elementen mogen gekromde randen hebben (middenknoop naast de koorde).
3. **Materiaal.**
   - S20: geef het materiaal een geometrie *Shell/membrane* met een **dikte** t; voor
     vlakke rek ook *plane strain* aanvinken. Zonder dikte rekent Mecway niet en stopt
     de bridge (§3). Het hele model heeft een dikte en een type (vlakke spanning of
     vlakke rek), anders stopt de bridge.
   - SA0: geen geometrie. Een dikte telt niet (de bridge negeert hem met een WARNING;
     Mecway's eigen solve geeft dan geen oplossing).
   - Dichtheid voor zwaartekracht, centrifugaalkracht en dynamica.
4. **Opleggingen.** *Fixed support*, *Pinned support* en *Displacement* langs X of Y op
   knopen of op randen (vlakselectie van randen, faceid 1..4), *Symmetry* met normaal X
   of Y op randen. Axisymmetrisch: Mecway vraagt een oplegging in X op knopen op de as
   (X = 0) (Mecway Ltd., 2026, §7.2); doe dat ook voor de bridge (zonder NIET
   geverifieerd). Een oplegging in Y is nodig tegen starre beweging langs de as.
5. **Belastingen** (alle waarden zoals in Mecway, zie §2.2):
   - *Pressure* en *Traction* op randen;
   - *Force* op knopen (totaal, gelijk per knoop) of op randen (totaal, uniform over het
     randoppervlak);
   - *Gravity* in het XY-vlak (SA0: alleen langs Y);
   - *Centrifugal force* om Z (S20) of om Y (SA0);
   - S20 en SA0: *Thermal stress* met *Temperature* (op knopen, randen of elementen) of
     *Node temperature*, en de uitzettingscoëfficiënt in het materiaal (§2.5).
   Waarden mogen een tijdtabel zijn (dynamica). Dynamica: *Rayleigh damping* op het hele
   model. Andere items stoppen of worden overgeslagen met een ERROR (§3, §4).

### 1.2 In het hoofdvenster van de bridge

![Pagina Algemeen met de actieve analyse en de resultaatroute](img/general_analysis_results_nl.png)

1. *Actieve analyse (auto = volgens Mecway)*: `auto` (of `lin_static_3d`; voor D20/DA0
   `dyna_impl_3d`).
2. *Resultaten naar Mecway*: `liml`.

*Actieve analyse (auto = volgens Mecway)* `auto` (of `lin_static_3d`) en *Resultaten naar Mecway* `liml` (pagina
Algemeen; de route `tabel` schaalt de reacties niet, de bridge stopt). De instellingen
van de pagina Statisch of Dynamisch (impliciet) gelden zoals in 3D; voor D20/DA0 gelijk
aan Mecway: *Tijdschema (SCHEMA_TEMPS)* `NEWMARK`, `deformation` `PETIT` en
*Rekenstappen per Mecway-tijdstap* = 1 (standaard; §2.4). De
resultaatvelden `strain` en `shell_*`
geven niets in 2D; `principal_stresses` geeft `principal1..3` en `tresca` zoals Mecway
(eigenwaarden van de 3D-tensor met σ_zz, per elementknoop, knoop = gemiddelde). De
foutschatter wordt in 2D niet gebruikt (INFO).

### 1.3 De resultaten in Mecway bekijken

De resultaten hebben Mecway's eigen namen en staan onder dezelfde items als Mecway's
eigen S20/SA0-oplossing (gemeten: Mecway voegt *displacement*, *stress*, *von Mises
stress*, *reaction force*, *principal stress* en *Tresca stress* toe als het het
resultaat opent):

| Mecway-variabele | Code-Aster | Betekenis |
|---|---|---|
| `displx`, `disply`, `displmag` | `DEPL` DX, DY | X, Y (SA0: radiaal, axiaal); geen `displz` (zoals Mecway) |
| `stressxx`, `stressyy`, `stressxy` | `SIGM_NOEU`/`SIGM_ELNO` | spanningen in het vlak (SA0: σ_r, σ_z, τ_rz) |
| `stresszz` | `SIGM_*` SIZZ | 0 bij vlakke spanning, ν(σ_xx + σ_yy) bij vlakke rek, **tangentiële spanning** in SA0 |
| `stressyz`, `stresszx` | – | 0 (zoals Mecway) |
| `vonmises` | `SIEQ_*` | 3D-von Mises met σ_zz |
| `reactionforcex/y/mag` | `REAC_NODA` × t of × 2π | voor de hele dikte (S20) of 360 graden (SA0), zoals Mecway |

### 1.4 Niet-lineair in 2D: een 3D-model met `**ASTER-PLANE` (route A)

Mecway heeft geen niet-lineair 2D-type. Voor plasticiteit, grote vervormingen, tijdstappen,
lastopbouw en contact in 2D maak je het model als 3D-model van vlakke elementen en zeg je de
bridge met een regel het in 2D te rekenen (voorbeelden 2, 3 en 4 in §1.5):

1. **Analysetype.** *Nonlinear Static* (L30) in *Analysis settings*, met CCX als solver
   (Mecway rekent L30 alleen met CCX). *Static 3D* (S30) kan ook (lineair, zoals S20; geen
   contact).
2. **Mesh.** Vlakke elementen tri3, tri6, quad4 of quad8 in het XY-vlak (Z = 0), verder
   niets (geen balken, truss, veren of volume-elementen); in een 3D-type behandelt Mecway ze
   als shells. Axisymmetrisch: Y is de as, X de straal, alle knopen bij X ≥ 0 (eerste
   figuur).
3. **Materiaal.** Een geometrie *Shell/membrane* met een dikte (Mecway heeft hem nodig voor
   shells). Voor `C_PLAN` en `D_PLAN` is het de dikte t: Mecway's krachten en de reacties
   gelden voor t (§2.2). Voor `AXIS` een willekeurige waarde: hij telt niet (INFO). Alle
   elementen hebben dezelfde dikte. Plasticiteit (*Bilinear isotropic*, *Stress-strain
   curve*) zoals in 3D.
4. **De regel.** In CCX > *Custom model definition* een regel:

   ```
   **ASTER-PLANE C_PLAN
   ```

   met `C_PLAN` (vlakke spanning), `D_PLAN` (vlakke rek) of `AXIS` (axisymmetrisch). Schrijf
   het streepje: `**ASTER PLANE AXIS` (met een spatie) is een ERROR (§1.6). Mecway's eigen
   solver negeert de regel; de bridge rekent dan elke elset met die modelisatie in plaats van
   als shells (een vinkje *plane strain* op het materiaal telt dan niet; WARNING als het de
   regel tegenspreekt). Andere velden en voorvoegsels: zie "Waar typ je de regel" in §1.
5. **Opleggingen en belastingen** op knopen en op randen, zoals in §1.1. Een rand is een
   vlakselectie van randen van de vlakke elementen (faceid 1..4, figuur bij voorbeeld 4);
   een vlakselectie van de elementvlakken (faceid 5/6) geeft een ERROR ("alleen randen van
   vlakke elementen (faceid 1..4), hier shellface", §1.6). Opleggingen die alleen Z of
   rotaties vasthouden (*Node rotation*, een *Displacement* nul langs Z, een *Symmetry* met
   normaal Z: vaak aanwezig voor Mecway's eigen shell-solve) vallen weg met een INFO.
   *Thermal stress* met *Temperature* en *Node temperature* zoals in §2.5, ook als tijdtabel
   (PL-34, PL-36; Mecway's eigen CCX-solve van de shells geeft de helft van de thermische
   uitzetting, KNOWN_BUGS 139).
6. **Contact** (alleen L30): een *Contact* (unilateraal) tussen twee vlakselecties van randen
   van de vlakke elementen: de master-rand en de slave-rand (figuur en stappen: voorbeeld 4;
   welke kant master is: [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md) §3.2).
   De bridge schrijft ze als randcellen (`SEG2`/`SEG3`) voor `DEFI_CONTACT` met de
   instellingen van de pagina Niet-lineair statisch, zoals in 3D. Overlappende geometrie (een
   krimpverbinding) wordt in de eerste stap opgelost. Het resultaat `contactpressure` is een
   druk (geen factor t of 2π). Nagelopen in `AXIS` en `D_PLAN` (krimpverbinding,
   Hertz-lijncontact, een Code-Aster-testcase) en met Coulomb-wrijving (een blok dat over een
   blok glijdt); `C_PLAN` rekent (alleen nagelopen met ν = 0). Met wrijving kunnen
   slave-knopen die een andere oplegging langs de contactrand vasthoudt Code-Aster laten
   stoppen met een singuliere matrix: de bridge geeft dan een WARNING; laat die knopen weg met
   een knoopselectie en `**ASTER-ZONE SANS_GROUP_NO='<<selectie>>'` (KNOWN_BUGS 141).
   *Bonded* contact in 2D: ERROR. Of Mecway's venster shell-randen laat kiezen voor een
   contact is NIET nagelopen.
7. **Bridge.** *Actieve analyse (auto = volgens Mecway)* `auto` (→ `nonlin_static_3d` voor
   L30, `lin_static_3d` voor S30) en *Resultaten naar Mecway* `liml` (de route `tabel`:
   ERROR). Controleer in de log dat de regel gelezen is: per elset
   `INFO: Elset '…' -> MODELISATION='C_PLAN', thickness … m (Mecway L30).` (bij `AXIS` zonder
   de dikte) en een keer `INFO: 2D analysis L30: MODELISATION='…'; concentrated forces / …
   and reactions x … (…).` Zonder deze regels heeft de bridge de elementen als shells
   gerekend (de regel ontbreekt of staat in een veld dat de bridge niet leest).

De bridge-analyse is `nonlin_static_3d` (L30) of `lin_static_3d` (S30); de instellingen van
de pagina Niet-lineair statisch gelden zoals in 3D. *deformation* `GROT_GDEP` (de standaard)
wordt `GDEF_LOG` voor plastisch materiaal (`SIMO_MIEHE` als gekozen, alleen in
`D_PLAN`/`AXIS`) en `GREEN_LAGRANGE` voor elastisch materiaal; een druk is dan een
meebewegende belasting zoals in 3D. De plasticiteitswetten van de bridge kennen `C_PLAN`
zelf (catalogus Code-Aster 17.4). Resultaten per stap zoals in §1.3, plus
`plasticstrainxx/yy/zz/xy` en `equivalentplasticstrain`; de reactiekrachten met de factor t
of 2π in elke stap (PL-30, PL-32). Verificatie PL-30 … PL-36: een dikwandige cilinder met ideale
plasticiteit (Hill) in `D_PLAN` en `AXIS`, eerste vloei bij een gat in `C_PLAN`,
Code-Aster-testcase ssnp159b (`AXIS`, `GDEF_LOG`) door de bridge. NIET meegenomen: de
bezwijklus (`#ASTER-BEZWIJKEN`, WARNING), verlijmd contact, de keten thermisch -> mechanisch en axisymmetrisch warmtetransport (§3).
Contact: PL-40 … PL-46 (een krimpverbinding binnen 0,01% van Lamé, Hertz-lijncontact, een
Code-Aster-testcase, wrijving). Het
openen van zo'n resultaat in het Mecway-venster is NIET nagelopen (een test in de
Mecway-GUI moet nog).

### 1.5 Uitgewerkte voorbeelden

Vier modellen in de repository, een per soort gebruik; open er een in Mecway om elke instelling
te zien:

| Voorbeeld | Bestand (`TestFiles/Verificatie/modellen/`) | Route | Mecway-type | Regel | Wat het laat zien |
|---|---|---|---|---|---|
| 1 | `PL-24.liml` | B | SA0 | geen | een buis met een radiale temperatuur (thermische spanning) |
| 2 | `PL-31.liml` | A | L30 | `**ASTER-PLANE AXIS` | plasticiteit, axisymmetrisch, een druk in tijdstappen |
| 3 | `PL-32.liml` (en `PL-33.liml`) | A | L30 (S30) | `**ASTER-PLANE C_PLAN` | plasticiteit in vlakke spanning, een plaat met een gat |
| 4 | `PL-40.liml` | A | L30 | `**ASTER-PLANE AXIS` | contact: een krimpverbinding van twee ringen |

Voordat je begint:

- Eenheden SI; staal E = 210 GPa (`210000 MPa` in de bestanden), ν = 0,3. Elk model heeft een
  materiaal `Staal`.
- De selectienamen in de bestanden zijn Nederlands: `Onder` = onderrand, `Boven` = bovenrand,
  `Binnenwand` = binnenrand, `Einden` = de eindranden. Elke randselectie is een vlakselectie
  van randen (faceid 1..4). In voorbeeld 4 (`PL-40.liml`) zijn `Binnen` en `Buiten` de elsets
  van de binnen- en de buitenring; de randselecties daar hebben eigen namen.
- In de bestanden staat geen solver: kies CCX in *Analysis settings* om de regel te zien in
  CCX > *Custom model definition* (de bridge leest hem toch).
- De modellen zijn gemaakt door de scripts `tests_vlak_2d_thermisch.py`,
  `tests_vlak_2d_nonlin.py` en `tests_vlak_2d_contact.py` in
  `TestFiles/Verificatie/` en doorgerekend met de bridge (resultaten tegen gesloten
  oplossingen, [`Verificatie.md`](Verificatie.md) §2D en axisymmetrisch). Route A is nog niet in
  Mecway's venster nagelopen: of Mecway shell-randen laat kiezen voor een *Contact* en hoe het
  een resultaat van route A toont is NIET nagelopen. Mecway's eigen solve van de modellen van
  route A is niet nodig (die rekent shells).

De voorbeelden 1 en 2 gebruiken dezelfde plak van een dikwandige buis (a = 0,1 m,
b = 0,2 m, h = 0,01 m):

![Een plak van een dikwandige buis in het XY-vlak: randen, opleggingen en maten](img/2d_tube_slice.svg)

1. Mecway's Y-as: de symmetrieas van de buis (`AXIS`).
2. De binnenrand, X = a = 0,1 m (selectie `Binnenwand` in voorbeeld 2; faceid 4 van het eerste element).
3. De buitenrand, X = b = 0,2 m (faceid 2 van het laatste element).
4. De onderrand, Y = 0 (selectie `Onder`; faceid 1 van elk element).
5. De bovenrand, Y = h = 0,01 m (selectie `Boven`; faceid 3 van elk element).
6. De rollen: *Displacement* langs Y met waarde 0 op de onder- en bovenrand: beide einden van de plak axiaal vast, een lange buis in vlakke rek (voorbeelden 1 en 2).
7. De elementen: een rij quad8 door de wand (8 of 16 elementen, zie het voorbeeld), in het XY-vlak.

**Voorbeeld 1 – route B: een dikwandige buis met een radiale temperatuur (`PL-24.liml`).**

1. *Analysis settings*: *Static Axisymmetric* (SA0).
2. Mesh: elset `Buis`, 8 × 1 quad8 (8 door de wand, 1 langs de as), X = 0,1 … 0,2 m,
   Y = 0 … 0,01 m (figuur hierboven).
3. Materiaal `Staal`: isotroop, E, ν, *Thermal expansion* 1,2e-5 1/K; geen geometrie (SA0).
4. Opleggingen en belastingen:

   | Selectie | Waar (figuur hierboven) | Mecway-item |
   |---|---|---|
   | `Onder` (vlakselectie, 8 randen) | onderrand (4) | *Displacement* langs Y, waarde 0 |
   | `Boven` (vlakselectie, 8 randen) | bovenrand (5) | *Displacement* langs Y, waarde 0 |
   | alle 43 knopen | – | *Node temperature* per knoop: T(r) = 393 K − 100 K · ln(r/a) / ln(b/a), 393 K aan de binnen- en 293 K aan de buitenwand |
   | – | – | *Thermal stress* met *Reference temperature* 293 K |

   De knooptemperaturen kunnen ook uit een thermische oplossing van een 3D-model komen
   ([`Thermisch.md`](Thermisch.md)).
5. Bridge: *Actieve analyse (auto = volgens Mecway)* `auto` (→ `lin_static_3d`), *Resultaten
   naar Mecway* `liml`. De log toont `INFO: Elset 'Buis' -> MODELISATION='AXIS' (Mecway SA0).`
   en `INFO: 2D analysis SA0: MODELISATION='AXIS'; concentrated forces / 6.28319 and
   reactions x 6.28319 (per radian in Code-Aster, 360 degrees in Mecway).`
6. Resultaten: `stresszz` = tangentiële spanning σ_θ (ongeveer −219 MPa aan de binnenwand,
   +140 MPa aan de buitenwand), `stressyy` = axiale σ_z (ongeveer −318 MPa aan de binnenwand),
   `stressxx` = radiale σ_r (ongeveer −28 MPa midden in de wand); `displx` = radiale
   verplaatsing (0,0605 mm aan de binnenwand, 0,121 mm aan de buitenwand); de axiale reactie
   (`reactionforcey` opgeteld over de onderrand, 360 graden) 9,2155 MN in grootte. Een buis
   met vrije einden: §2.5 (een `#ASTER`-regel `LIAISON_UNIF`, `PL-25.liml`).

**Voorbeeld 2 – route A: een elastisch-plastische cilinder onder inwendige druk (`PL-31.liml`).**

1. *Analysis settings*: *Nonlinear Static* (L30), solver CCX, *Time period* 1 s, *Time step
   size* 0,05 s (20 stappen).
2. Mesh: elset `Cilinder`, 16 × 1 quad8, X = 0,1 … 0,2 m, Y = 0 … 0,01 m: dezelfde vlakke
   elementen, in een 3D-type (dus shell-elementen voor Mecway).
3. Materiaal `Staal`: *Shell/membrane* met dikte 10 mm (willekeurig: telt niet voor `AXIS`),
   isotroop E, ν, plasticiteit *Bilinear isotropic* met vloeigrens 250 MPa en tangent modulus
   0 (ideaal plastisch).
4. Opleggingen en belastingen:

   | Selectie | Waar (figuur hierboven) | Mecway-item |
   |---|---|---|
   | `Binnenwand` (vlakselectie, 1 rand) | binnenrand (2) | *Pressure* als tijdtabel: 0 op 0 s, 159,1 MPa op 0,5 s, 187,6 MPa op 1 s |
   | `Onder` (vlakselectie, 16 randen) | onderrand (4) | *Displacement* langs Y, waarde 0 |
   | `Boven` (vlakselectie, 16 randen) | bovenrand (5) | *Displacement* langs Y, waarde 0 |

5. De regel: in CCX > *Custom model definition*

   ```
   **ASTER-PLANE AXIS
   ```

6. Bridge: `auto` (→ `nonlin_static_3d`), `liml`, de pagina Niet-lineair statisch ongewijzigd.
   De log toont `INFO: Elset 'Cilinder': the shell thickness (0.01 m) does not count with
   #ASTER-PLANE AXIS.` en `INFO: Elset 'Cilinder' -> MODELISATION='AXIS' (Mecway L30).`
7. Resultaten per stap: `equivalentplasticstrain` (plastische zone tot r ≈ 0,13 m op 0,5 s
   en 0,16 m op 1 s), `displx` van de buitenwand (0,163 mm op 1 s, 1,7% boven Hills
   0,160 mm: de druk volgt de vervormde wand), `stresszz` = tangentiële spanning.

**Voorbeeld 3 – route A: eerste vloei bij een gat in vlakke spanning (`PL-32.liml`).**

![Een kwart plaat met een gat: symmetrieranden en trekbelasting](img/2d_plate_hole.svg)

1. Het gat, straal 0,01 m, middelpunt in de oorsprong; het gestippelde deel ligt buiten het model (symmetrie).
2. De rand X = 0 (Y = 0,01 … 0,05 m): selectie `SymX`, *Symmetry* met normaal X.
3. De rand Y = 0 (X = 0,01 … 0,15 m): selectie `SymY`, *Symmetry* met normaal Y.
4. De rand X = 0,15 m: selectie `Trek`, *Traction* langs X.
5. De vlakke elementen (een kwart van een plaat 0,3 × 0,1 m), dikte t = 1 mm loodrecht op de tekening.

Stappen:

1. *Analysis settings*: *Nonlinear Static* (L30), solver CCX, *Time period* 1 s, *Time step
   size* 0,02 s (50 stappen).
2. Mesh: elset `Plaat`, een kwart van een plaat 0,3 × 0,1 m met een gat met straal 0,01 m in
   het midden: X = 0 … 0,15 m, Y = 0 … 0,05 m, het middelpunt van het gat in de oorsprong;
   12 288 quad8 (fijn, dus de berekening duurt even).
3. Materiaal `Staal`: *Shell/membrane* met dikte 1 mm (dit is t: telt mee voor `C_PLAN`), E,
   ν, plasticiteit *Bilinear isotropic* met vloeigrens 250 MPa en tangent modulus 2100 MPa
   (0,01 E).
4. Opleggingen en belastingen:

   | Selectie | Waar (figuur hierboven) | Mecway-item |
   |---|---|---|
   | `SymX` (vlakselectie, 64 randen) | rand X = 0 (2) | *Symmetry* met normaal X |
   | `SymY` (vlakselectie, 128 randen) | rand Y = 0 (3) | *Symmetry* met normaal Y |
   | `Trek` (vlakselectie, 64 randen) | rand X = 0,15 m (4) | *Traction* langs X als tijdtabel: 71,46 MPa op 0 s, 87,33 MPa op 1 s |

5. De regel: in CCX > *Custom model definition* `**ASTER-PLANE C_PLAN`.
6. Bridge: `auto` (→ `nonlin_static_3d`), `liml`. De log toont `INFO: Elset 'Plaat' ->
   MODELISATION='C_PLAN', thickness 0.001 m (Mecway L30).` en `INFO: 2D analysis L30:
   MODELISATION='C_PLAN'; concentrated forces / 0.001 and reactions x 0.001 (per unit
   thickness in Code-Aster, thickness t in Mecway).`
7. Resultaten per stap: `equivalentplasticstrain` verschijnt het eerst bij het gat (X = 0,
   Y = 0,01 m), rond 0,6 s: de spanning in de netto doorsnede (traction / 0,8) is dan 1,8%
   boven σ_y / Kt = 250 / 2,519 = 99,2 MPa (Peterson). De som van `reactionforcex` op `SymX`
   op 1 s is −87,33 MPa × 0,05 m × 0,001 m = −4367 N: de reacties gelden voor de dikte t.

`PL-33.liml` is dezelfde plaat met 3 072 quad8 als *Static 3D* (S30), lineair, een constante
*Traction* van 100 MPa op `Trek`, dezelfde regel `**ASTER-PLANE C_PLAN`: `displx` in
(0,15, 0) = 7,377e-5 m en `disply` in (0, 0,01) = −5,394e-6 m, gelijk aan route B
(`PL-01-n16.liml`, S20) binnen 1e-6.

**Voorbeeld 4 – route A: een krimpverbinding met contact (`PL-40.liml`).**

![Krimpverbinding van twee ringen in het XY-vlak: slave-rand, master-rand en overmaat](img/2d_contact_edges.svg)

1. Mecway's Y-as: de symmetrieas (`AXIS`).
2. De binnenring: elset `Binnen`, X = 0,1 … 0,15005 m.
3. De buitenring: elset `Buiten`, X = 0,15 … 0,2 m. Elke ring heeft zijn eigen knopen; de ringen zijn niet verbonden.
4. De slave-rand: de buitenrand van de binnenring, X = 0,15005 m (vlakselectie `Binnenring_buiten`, faceid 2 van het laatste element van `Binnen`).
5. De master-rand: de binnenrand van de buitenring, X = 0,15 m (vlakselectie `Buitenring_binnen`, faceid 4 van het eerste element van `Buiten`).
6. De overmaat δ = 0,05 mm: de ringen overlappen in de mesh (vergroot getekend); het contact lost dat in de eerste stap op.
7. De rollen: *Displacement* langs Y met waarde 0 op de onder- en bovenranden van beide ringen (vlakselectie `Einden`, faceid 1 en 3).

Stappen:

1. *Analysis settings*: *Nonlinear Static* (L30), solver CCX, *Time period* 1 s, *Time step
   size* 1 s (een stap).
2. Mesh: twee elsets, `Binnen` (X = 0,1 … 0,15005 m) en `Buiten` (X = 0,15 … 0,2 m), beide
   Y = 0 … 0,01 m en 8 × 1 quad8; elke ring heeft zijn eigen knopen (voeg de knopen bij het
   contact niet samen).
3. Materiaal `Staal` voor beide: *Shell/membrane* met dikte 10 mm (telt niet voor `AXIS`),
   E, ν; elastisch.
4. Opleggingen en contact:

   | Selectie | Waar (figuur hierboven) | Mecway-item |
   |---|---|---|
   | `Binnenring_buiten` (vlakselectie, 1 rand) | slave-rand (4) | *Contact*: slave |
   | `Buitenring_binnen` (vlakselectie, 1 rand) | master-rand (5) | *Contact*: master |
   | `Einden` (vlakselectie, 32 randen) | onder- en bovenranden van beide ringen (7) | *Displacement* langs Y, waarde 0 |
   | `Slave` (knoopselectie, 3 knopen) | de knopen van de slave-rand | geen; alleen om de gemiddelde contactdruk af te lezen |

   Het *Contact*: type *unilateral elastic*, wrijvingscoëfficiënt 0, *normal stiffness*
   1000 GPa/m (Mecway vraagt een waarde; met het standaard contactalgoritme `STANDARD` van de
   bridge wordt hij niet gebruikt), tolerantie 0.
5. De regel: in CCX > *Custom model definition* `**ASTER-PLANE AXIS`.
6. Bridge: `auto` (→ `nonlin_static_3d`), `liml`; de contactinstellingen van de pagina
   Niet-lineair statisch zoals in 3D.
7. Resultaat: `contactpressure` op de slave-knopen, gemiddeld 12,465 MPa (Lamé, vlakke rek:
   12,464 MPa); de overlap wordt in de eerste stap opgelost. `PL-41.liml` is hetzelfde in
   `D_PLAN` (kwart ringen met *Symmetry*), `PL-46.liml` een contact met wrijving 0,3
   (`D_PLAN`).

### 1.6 Veelgemaakte fouten

De meldingen in de log, letterlijk; '…' staat voor een naam of getal uit je model. Een ERROR
met "NIET meegenomen" of "Niet vertaald" slaat alleen dat item over: de berekening gaat zonder
door en eindigt met een melding die het noemt. Elke andere ERROR hieronder stopt de bridge
voor Code-Aster. De bridge schrijft de regel als `#ASTER-PLANE`, ook als je `**ASTER-PLANE`
typte.

| Wat ging er mis | Melding van de bridge | Oplossing |
|---|---|---|
| Mesh niet in het XY-vlak | ERROR: Een 2D-analyse (…) heeft alle knopen in het XY-vlak nodig (Z = 0); hier tot Z = … m. Code-Aster rekent een 2D-model alleen met Z = 0 (Mecway negeert Z). | verplaats of draai de mesh naar Z = 0 |
| Knopen bij X < 0 in een axisymmetrisch model (ook route A) | ERROR: Axisymmetrisch (SA0): alle knopen moeten X >= 0 hebben (X = straal, Y = as); hier X tot … m. (ook in route A, waar het model L30 of S30 is) | Y is de as, X de straal (eerste figuur) |
| De as langs X getekend (alle X ≥ 0) | geen: de bridge neemt Y als as | teken de doorsnede met Y als as |
| Balken, truss, veren of volume-elementen in het model | ERROR: Elset '…' bevat …; in een 2D-analyse (…) vertaalt de bridge alleen vlakke elementen (tri3, tri6, quad4, quad8), geen balken, truss, veren of volume-elementen. | alleen vlakke elementen; of reken in 3D |
| Route A zonder de regel, of de regel in een veld dat de bridge niet leest | geen: de log heeft geen regel `INFO: Elset '…' -> MODELISATION=…`; de bridge rekent de elementen als shells | typ de regel in CCX > *Custom model definition* (§1.4 stap 4) |
| `**ASTER-PLANE` in een S20/SA0/D20/DA0-model | ERROR: '#ASTER-PLANE …' werkt alleen in Mecway's Static 3D (S30) en Nonlinear Static (L30) met vlakke shell-elementen in het XY-vlak; dit model is SA0 (al een 2D-type: haal de regel weg). | route B heeft geen regel nodig; haal hem weg |
| `**ASTER-PLANE` in een ander 3D-type (T30, T31, V30, D30, …) | ERROR: '#ASTER-PLANE …' werkt alleen in Mecway's Static 3D (S30) en Nonlinear Static (L30) met vlakke shell-elementen in het XY-vlak; dit model is …. | S30 of L30; warmtetransport in een vlak (T30/T31) heeft geen regel nodig, axisymmetrisch warmtetransport kan nog niet (§3) |
| `**ASTER-PLANE` met een andere waarde | ERROR: '#ASTER-PLANE …': verwacht C_PLAN, D_PLAN of AXIS. | schrijf C_PLAN, D_PLAN of AXIS |
| `**ASTER-PLANE` zonder waarde | ERROR: '#ASTER-PLANE' zonder waarde; verwacht C_PLAN, D_PLAN of AXIS. | schrijf C_PLAN, D_PLAN of AXIS |
| `**ASTER PLANE AXIS` (spatie in plaats van streepje) | ERROR: '#ASTER PLANE AXIS' is Code-Aster-code en wordt overgeslagen; bedoeld is '#ASTER-PLANE AXIS' (met een streepje). | schrijf `**ASTER-PLANE AXIS` |
| Twee `**ASTER-PLANE`-regels met verschillende waarden | WARNING: Meerdere #ASTER-PLANE-regels; de laatste telt (…). | houd een regel |
| `#ASTER-PLANE` getypt in het CCX-veld | geen van de bridge (die neemt `#`, `**`, `$`); Mecway's eigen CCX-solve kan over de `#`-regel struikelen | gebruik `**` in het CCX-veld, `#` in het OpenRadioss-veld |
| *Plane strain* aangevinkt op het materiaal met `**ASTER-PLANE C_PLAN` | WARNING: Materiaal '…' heeft plane strain, maar #ASTER-PLANE zegt C_PLAN; de bridge volgt de regel. | de regel beslist; haal het vinkje weg of schrijf D_PLAN |
| Route A met `C_PLAN`/`D_PLAN` maar zonder shell-dikte | ERROR: Elset '…': #ASTER-PLANE C_PLAN heeft een dikte nodig; geef materiaal '…' in Mecway een geometrie Shell/membrane met een dikte (ook voor plane strain; zonder dikte rekent Mecway zelf ook niet). | geef het materiaal *Shell/membrane* met de dikte t |
| Twee materialen met een verschillende dikte | ERROR: De 2D-analyse heeft elsets met verschillende modelisatie of dikte (…); de bridge vertaalt een model met een enkele dikte en een enkel type (plane stress of plane strain). | een dikte voor het hele model |
| Een andere bridge-analyse dan `auto` gekozen | ERROR: Mecway-analysetype L30 (2D) wordt alleen vertaald naar nonlin_static_3d, niet naar …. Kies op het startscherm 'auto' of nonlin_static_3d. | `auto` |
| Resultaatroute `tabel` | ERROR: Een 2D-analyse (…) werkt alleen met de resultaatroute 'liml' (pagina Algemeen); de route 'tabel' schaalt de reactiekrachten niet naar de dikte of 360 graden. | resultaatroute `liml` |
| Plasticiteit in een S20/SA0-model | WARNING: Materiaal '…' heeft plasticiteit, maar S20 is lineair (ook in Mecway); de bridge rekent elastisch. Voor plasticiteit in 2D: Nonlinear Static (L30) met vlakke shell-elementen en de regel '**ASTER-PLANE C_PLAN\|D_PLAN\|AXIS' (docs 2D par. 1.4). | route A (voorbeeld 2 of 3) |
| Een belasting of oplegging op de elementvlakken (faceid 5/6) in plaats van op randen in route A | ERROR: … op '…' in een 2D-analyse: alleen randen van vlakke elementen (faceid 1..4), hier shellface. NIET meegenomen. | een vlakselectie van randen |
| Een contact tussen elementvlakken in plaats van randen | ERROR: contact '…' / '…': in een 2D-analyse alleen randen van de vlakke elementen (hier […]). NIET meegenomen. | vlakselecties van randen (voorbeeld 4) |
| Contact in S30 met `**ASTER-PLANE` | ERROR: Contact in een 2D-analyse (S30) wordt (nog) niet vertaald; haal het weg of reken het model in 3D. | *Nonlinear Static* (L30) |
| *Bonded* contact in route A | ERROR: Bonded contact in een 2D-analyse (L30) wordt (nog) niet vertaald; haal het weg of reken het model in 3D. | laat het weg, of reken in 3D |
| Contact met wrijving, slave-knopen ook vastgehouden door een oplegging | WARNING: Contact met wrijving (slave '…'): slave-knopen worden ook vastgehouden door '…'. Een richting langs het contactvlak kan dan dubbel vastliggen en Code-Aster kan stoppen met een singuliere matrix (MECANONLINE9_4, KNOWN_BUGS 141). … | laat die knopen weg met `**ASTER-ZONE SANS_GROUP_NO='<<selectie>>'` |
| De bezwijklus (`#ASTER-BEZWIJKEN`) in route A | WARNING: Elset '…' (…, grens … uit …) kan niet bezwijken: alleen volume-elementen en schalen (… niet: de bezwijklus is in 2D NIET geverifieerd). | niet mogelijk in 2D (§3) |
| Een *Displacement* langs Z of een *Node rotation* uit het 3D-shell-model | route A: INFO: … on '…': only Z or rotations, which the 2D model does not have (#ASTER-PLANE); left out. In S20/SA0: ERROR: … op '…' in een 2D-analyse: …. NIET meegenomen. | niets te doen in route A |

## 2. Hoe de bridge vertaalt

### 2.1 Elementen en mesh

De bridge schrijft de vlakke elementen als `TRIA3`/`TRIA6`/`QUAD4`/`QUAD8`-cellen met
`COOR_3D` en Z = 0; Code-Aster leest zo'n mesh als 2D (gemeten, geen alarm). Elke
component krijgt `MODELISATION='C_PLAN'`, `'D_PLAN'` of `'AXIS'`; randen met een druk
of randbelasting worden `SEG2`/`SEG3`-cellen met dezelfde modelisatie (drukranden naar
buiten gericht met `MODI_MAILLAGE ORIE_PEAU`). Gemeten tegen Mecway's eigen oplossing
(headless): tri3, tri6, quad4 en quad8 geven dezelfde verplaatsingen (≤ 1e-11
relatief); Mecway's quad4 in 2D heeft geen incompatibele modes (anders dan hex8, KB1).

### 2.2 Dikte en 360 graden

Code-Aster rekent `C_PLAN`/`D_PLAN` per eenheid van dikte (er is geen dikte in
`AFFE_CARA_ELEM`; gemeten: de reactie van een druk op een rand van 20 mm is p × 0,02 m
× 1 m) en `AXIS` per radiaal (U4.44.01 §3.5: krachten "teruggebracht tot een sector van
1 radiaal"). Mecway geeft krachten en reacties voor de hele dikte t (ook bij vlakke
rek) en voor 360 graden (gemeten). De bridge doet daarom:

| Mecway | Code-Aster | Factor |
|---|---|---|
| kracht op knopen (N, totaal) | `FORCE_NODALE` | / t (S20) of / 2π (SA0) |
| kracht op randen (N, totaal) | `FORCE_CONTOUR` = F / A | A = L·t (S20) of 2π∫r dl (SA0) |
| druk, traction (Pa) | `PRES_REP`, `FORCE_CONTOUR` | geen |
| zwaartekracht, centrifugaalkracht | `PESANTEUR`, `ROTATION` | geen |
| reactiekrachten | `REAC_NODA` | × t of × 2π |

De massa in de log (`BRIDGE_STATCHECK`) is die van de hele dikte of van 360 graden
(Code-Aster's `MASS_INER` van `AXIS` is al voor 360 graden, gemeten).

### 2.3 Voorwaarden

`fixed`: `DDL_IMPO` DX = DY = 0; `pinnedsupport` op meerdere knopen: de gemiddelde
verplaatsing nul, `LIAISON_DDL` met gelijke gewichten op DX en DY (zoals Mecway 35: vlakke
spanning PL-07, vlakke rek en axisymmetrisch gelijk gemeten; D20/DA0 NIET geverifieerd),
op één knoop of op randen `DDL_IMPO` DX = DY = 0; `displacement` langs X of Y:
`DDL_IMPO`; `symmetry` met normaal X of Y: `DDL_IMPO` DX = 0 of DY = 0. Componenten die
het 2D-model niet heeft (DZ, rotaties, FZ) vallen weg. Een pinned support op meerdere
knopen laat de knopen ten opzichte van elkaar bewegen en samen draaien: zonder ander
steunpunt tegen die rotatie is het model een mechanisme (Code-Aster stopt met
`FACTOR_11`; Mecway geeft een willekeurige rotatie). Op randen houdt Mecway 35 in 2D niets
vast; de bridge houdt daar elke knoop vast (WARNING; KNOWN_BUGS 134).

### 2.4 Dynamica (D20, DA0)

D20 en DA0 gaan via `dyna_impl_3d` (`DYNA_NON_LINE`), precies als Mecway's 3D Dynamic
Response (D30) zonder *Mode superposition*: uitvoertijden elke n-de Mecway-stap,
belastingen als tijdtabel, Rayleigh-demping (`AMOR_RAYL`). De massa per eenheid van
dikte of per radiaal past bij de krachten van §2.2, dus geen extra factor. Mecway rekent
lineair met Newmark (gemiddelde versnelling): met *Tijdschema (SCHEMA_TEMPS)* `NEWMARK`,
`deformation` `PETIT` en een rekenstap per Mecway-stap (*Rekenstappen per
Mecway-tijdstap* = 1, de standaard) is de bridge gelijk aan Mecway's eigen
D20/DA0-oplossing (≤ 4e-8, PL-10 … PL-12). De rekenstap is Mecway's *Time step size*,
ook met *Generate solution every n time steps* > 1: de bridge rekent dan n stappen per
uitvoerinterval en schrijft alleen de uitvoertijden. Met de standaard HHT geeft de bridge
een WARNING (numerieke demping).

### 2.5 Thermische spanning (S20, SA0)

Een *Thermal stress* met *Temperature* of *Node temperature* gaat zoals in 3D: een
temperatuurveld in de knopen (`CREA_CHAMP` `NOEU_TEMP_R`, knopen zonder temperatuur op
de referentietemperatuur) als commandovariabele `AFFE_VARC` `NOM_VARC='TEMP'` met
`VALE_REF` = de referentietemperatuur, en `ALPHA` in `ELAS` (U4.43.03). Een temperatuur
is een rekbelasting: geen factor t of 2π (§2.2). Code-Aster interpoleert de
knooptemperaturen binnen het element.

| Model | Thermische rek | `stresszz` |
|---|---|---|
| vlakke spanning (`C_PLAN`) | α ΔT in X, Y en door de dikte (vrij) | 0 |
| vlakke rek (`D_PLAN`) | α ΔT in alle drie richtingen, totale ε_zz = 0 | ν(σ_xx + σ_yy) − E α ΔT |
| axisymmetrisch (`AXIS`) | α ΔT radiaal, axiaal en in de omtrek | omtrekspanning σ_θ |

Eindvoorwaarde van een buis in `AXIS`: een eindrand die axiaal is vastgehouden
(*Displacement* in Y) is vlak en vast; een eindrand zonder oplegging is vrij maar blijft
niet vlak. Een lange buis met vrije einden (gegeneraliseerde vlakke rek: vlakke einden die
axiaal mogen bewegen, axiale resultante nul) heeft een eindrand nodig die vlak blijft: zet
op die rand (hier de vlakselectie `Boven`) in de custom model definition

```
#ASTER vlak = AFFE_CHAR_MECA(MODELE=model, LIAISON_UNIF=_F(GROUP_MA='<<Boven>>', DDL='DY'))
#ASTER-EXCIT vlak
```

(`LIAISON_UNIF`: alle knopen van de rand krijgen dezelfde DY; [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md)).
Verificatie PL-20 … PL-28 ([`Verificatie.md`](Verificatie.md)): vrije uitzetting (ook
een volle schijf met knopen op de as en een temperatuur op randen) en rondom
vastgehouden platen exact, een dikwandige buis met een logaritmische temperatuur binnen
1% van Timoshenko & Goodier (|σ_r| 1,04% te groot, zie daar). Verplaatsingen en reacties zijn
gelijk aan Mecway's eigen S20/SA0-oplossing (≤ 1e-13, Mecway 35 headless; ook Mecway
interpoleert de knooptemperaturen binnen het element); knoopspanningen verschillen door de
extrapolatie (§5).

## 3. Niet mogelijk

KNOWN_BUGS 126; geplande stappen in `STAPPENPLAN.md`: S16e (belastingen en elementen in de
lineaire typen), S44 (niet-lineair en contact: gebouwd, §1.4;
axisymmetrisch warmtetransport en de keten thermisch -> mechanisch, S44d, en axisymmetrische
schalen, S44e: nog niet). A20 (akoestiek): §4. De letterlijke meldingen: §1.6
en §6.

- Balken, truss, veren of volume-elementen in een 2D-analyse (Mecway's S20 kent balken
  en truss): ERROR, de bridge stopt.
- Axisymmetrische schalen (lijnelementen in een axisymmetrisch model, Code-Aster
  `COQUE_AXIS`): nog niet (gepland als STAPPENPLAN S44e). Lijnelementen in een 2D-model geven
  de ERROR "Elset '…' bevat line2 …" (§1.6).
- Route A: contact alleen in L30 (in S30: ERROR); *Bonded* contact: ERROR; belastingen,
  opleggingen en contacten op de elementvlakken (faceid 5/6) in plaats van randen: ERROR, NIET
  meegenomen; de bezwijklus (`#ASTER-BEZWIJKEN`): WARNING, de elementen kunnen niet bezwijken
  (in 2D NIET geverifieerd).
- Meerdere diktes, of vlakke spanning en vlakke rek in een model: ERROR.
- Moment, line pressure, hydrostatische druk, frictionless en elastic support,
  compression only, node rotation, constraint equations, koppelingen, contact,
  puntmassa's: ERROR (stop of overgeslagen).
- Temperaturen (thermal stress) in D20/DA0: ERROR (in S20/SA0 vertaald, §2.5). Een
  *Temperature* met een tijdtabel in S20/SA0 valt weg (WARNING), zoals in 3D Static;
  Mecway's eigen S20 en SA0 geven er ook geen uitzetting mee (headless gemeten).
- Displacement in een schuine richting, symmetrie met een schuine normaal: overgeslagen
  (ERROR).
- S20/SA0 met een andere analyse dan `lin_static_3d`, D20/DA0 met een andere dan
  `dyna_impl_3d`, expliciete schema's, *Mode superposition* en een beginsnelheid in 2D:
  ERROR. Mecway zelf heeft geen niet-lineair, frequentie- of knik-2D-type (Mecway 34
  zet V20 om naar V30 en B20 naar S30); niet-lineair in 2D: §1.4. S20/SA0 met een
  plastisch materiaal rekenen elastisch (WARNING).
- `**ASTER-PLANE` mag alleen in S30 en L30; in een ander type (ook T30/T31), met een andere
  waarde dan `C_PLAN`, `D_PLAN`, `AXIS`, of zonder streepje: ERROR. Een element offset in een 2D-analyse (S20,
  SA0, D20, DA0 of `**ASTER-PLANE`): ERROR.
- Axisymmetrisch warmtetransport en de keten thermisch -> mechanisch in 2D (`C_PLAN`, `D_PLAN`,
  `AXIS`): nog niet (STAPPENPLAN S44d); `**ASTER-PLANE` in T30/T31 is een ERROR. Warmtetransport
  in een vlak: vlakke schalen in T30/T31 zonder de regel (`PLAN`, [`Thermisch.md`](Thermisch.md)).
- De foutschatter (INFO) en de resultaatroute `tabel` (ERROR).

## 4. Akoestiek in 2D

| Mecway | Status | Toelichting |
|---|---|---|
| Acoustic Resonance 2D (A20) | Ja: holtemodes (`acoustic_modes_3d`, `MODELISATION='PLAN'`), ook met impedantie | [`Akoestiek.md`](Akoestiek.md) §3.5; gelijk aan Mecway's eigen A20-oplossing (quads ≤ 1e-6, driehoeken iets hoger, KNOWN_BUGS 130); geen harmonisch drukveld in 2D (Mecway heeft daar in 2D geen invoer voor) |
| akoestiek axisymmetrisch | Mecway heeft dit type niet (de analysecodes in Mecway 34: S20, SA0, D20, DA0, A20 en de 3D-typen) | 3D (A30) of een doorsnede in 2D (A20) |

## 5. Interpretatie

- Verplaatsingen en reactiekrachten zijn gelijk aan Mecway's eigen S20/SA0-oplossing
  (≤ 1e-11 relatief, verificatie PL-01, PL-02, PL-04 … PL-06), de tijdsverlopen van
  D20/DA0 binnen 4e-8 (PL-10 … PL-12, met de instellingen van §2.4).
- Knoopspanningen verschillen van Mecway waar de spanning sterk varieert over een
  element (bijv. 1 tot 3% bij het gat van PL-01 met n = 16, 2% aan de binnenwand van
  een grove ring): een andere extrapolatie vanuit de integratiepunten, zoals bij
  volume-elementen (KB3). Waar de spanning uniform of lineair is in het element zijn ze
  gelijk.
- Druk op gekromde kwadratische randen: Mecway's resultante is iets te groot (kwart ring
  a = 0,1 m, t = 10 mm, 100 MPa: Mecway 100161 N in plaats van p·a·t = 100000 N, u_r aan
  de binnenwand 0,17% kleiner dan de bridge); de bridge is exact (KB125).

## 6. Meldingen en oplossingen

De meldingen van route A (`**ASTER-PLANE`, contact op randen), letterlijk: §1.6.

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Elset '…': Static 2D (S20) heeft een dikte nodig | materiaal zonder geometrie *Shell/membrane* | geef het materiaal een dikte (ook voor plane strain) |
| ERROR: De 2D-analyse heeft elsets met verschillende modelisatie of dikte | twee materialen met een andere dikte of type | een dikte en een type per model; of reken in 3D |
| ERROR: Een 2D-analyse (…) heeft alle knopen in het XY-vlak nodig (Z = 0) | mesh niet in het XY-vlak | verplaats of draai de mesh naar het XY-vlak |
| ERROR: Axisymmetrisch (SA0): alle knopen moeten X >= 0 hebben | deel van de mesh bij X < 0 | spiegel de mesh naar X ≥ 0 (Y = as) |
| ERROR: Elset '…' bevat line2 …; in een 2D-analyse … | balken, truss, veren of volume-elementen in het model | haal ze weg of reken in 3D |
| ERROR: … in een 2D-analyse (…) wordt (nog) niet vertaald | contact, koppeling, constraint equation, puntmassa, of een temperatuur in D20/DA0 | haal het weg of reken in 3D |
| ERROR: … op '…' in een 2D-analyse: … NIET meegenomen. | belasting of voorwaarde zonder 2D-route (§3) | vervang hem door een ondersteunde belasting (§1.1) |
| ERROR: Mecway-analysetype A20 (Acoustic Resonance 2D) wordt alleen vertaald naar de holtemodes … | een andere analyse gekozen | kies `auto` of `acoustic_modes_3d` ([`Akoestiek.md`](Akoestiek.md) §3.5) |
| ERROR: Mecway-analysetype D20 (2D) wordt alleen vertaald naar dyna_impl_3d, niet naar … | een andere analyse gekozen op het startscherm | kies `auto` of de genoemde analyse |
| ERROR: D20 (2D) wordt vertaald met het impliciete schema … | expliciet schema of *Mode superposition* | kies `NEWMARK` of `HHT`; zet *Mode superposition* in Mecway uit |
| ERROR: Een 2D-analyse (…) werkt alleen met de resultaatroute 'liml' | route `tabel` gekozen | kies `liml` op de pagina Algemeen |
| ERROR: '#ASTER-PLANE …' werkt alleen in Mecway's Static 3D (S30) en Nonlinear Static (L30) … | de schakelaar in een ander analysetype | gebruik S30 of L30 (§1.4), of haal de regel weg |
| ERROR: '#ASTER PLANE …' is Code-Aster-code en wordt overgeslagen; bedoeld is '#ASTER-PLANE …' | de schakelaar zonder streepje | schrijf `**ASTER-PLANE` (§1.4) |
| WARNING: Materiaal '…' heeft plasticiteit, maar S20 is lineair … | plasticiteit in S20/SA0 | Nonlinear Static (L30) met `**ASTER-PLANE` (§1.4) |
