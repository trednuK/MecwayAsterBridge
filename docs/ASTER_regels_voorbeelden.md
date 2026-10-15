# `#ASTER`-regels: eigen Code-Aster-invoer vanuit Mecway

*English version: [ASTER_lines_examples.md](en/ASTER_lines_examples.md)*

Met `#ASTER`-regels zet je Code-Aster-commando's in het model waar Mecway geen invoer
voor heeft (bijv. een balk aan een volumevlak, een schaal op een volume,
contactinstellingen, extra nabewerking). De bridge leest ze uit de `.liml`
(`Scripts/bridge_custom.py`) en zet ze op een vaste plek in de `.comm` van de run
(`<model>_<run-id>.comm`, zie [Handleiding §5](Handleiding.md#5-bestanden-in-de-werkmap);
hieronder kort `.comm` en `.mess`). De bridge controleert de Code-Aster-syntax niet:
fouten komen uit Code-Aster ([`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md)).

Alle voorbeelden in §5 zijn op 06-10-2026 met de huidige bridge gegenereerd en met
Code-Aster 17.4.0 doorgerekend; de `.comm`-fragmenten en uitkomsten komen uit die runs
(de voorbeelden 1 tot 8 op 07-10-2026 opnieuw, in de modellen van
`TestFiles/Voorbeelden/`). Overzicht: [§6](#6-overzicht-van-de-controle).

## 1. Waar typ je de regels

In een vrij tekstveld van een van de Mecway-solvers. Zet in *Analysis settings* de
solver op die solver; dan verschijnt in de outline-boom een tak met het veld
(Mecway, 2026: §13.2-13.3, §14.2.8, §15.1.5). Mecway geeft de tekst ook aan die solver;
daarom begint de regel met het commentaarteken van die solver:

| Mecway-veld (XML-tag in de `.liml`) | Voorvoegsel |
|---|---|
| CCX > Custom model definition (`ccxmodeldefinition`) | `**ASTER` |
| CCX > Custom step contents (`ccxstep`) | `**ASTER` |
| OpenRadioss > Custom model definition (`radiossmodeldefinition`) | `#ASTER` |
| OpenRadioss > Custom engine input (`radiossengineinput`) | `#ASTER` |
| Mystran > Custom bulk data (`nastranbulkdata`) | `$ASTER` |

- De bridge leest alle vijf velden, welke solver er ook gekozen is. Praktisch:
  statica in een Mystran-analyse (`$ASTER`), niet-lineair/contact/dynamica in een
  OpenRadioss- of CCX-analyse.
- Na het voorvoegsel is de syntax overal gelijk. Hieronder staat steeds `#ASTER`; in
  het Mystran-veld schrijf je `$ASTER`, in een CCX-veld `**ASTER`. Spaties tussen
  voorvoegsel en `ASTER` mogen (`$ ASTER`, `** ASTER`).
- Andere regels in het veld (gewone solver-invoer, commentaar zoals `$ tekst` of
  `** tekst`) slaat de bridge over. Een regel die op een `#ASTER`-regel lijkt maar niet
  past (bijv. `#ASTER_EXCIT`), geeft een ERROR in de log en wordt overgeslagen.
- Volgorde in de `.comm`: de velden in de volgorde van de tabel hierboven, binnen een
  veld van boven naar beneden.

## 2. Soorten regels

| Regel | Wat de bridge ermee doet |
|---|---|
| `#ASTER <code>` | Code-Aster-code, letterlijk na de lasten van de bridge (`load_1`, ...) en vóór de solve (zie de tabel hieronder). De ene spatie na `#ASTER` valt weg, de rest van de regel blijft staan. |
| `#ASTER-EXCIT naam, naam2` | Zet `_F(CHARGE=naam)` in `EXCIT` van de solve. Alleen `CHARGE`: geen `FONC_MULT` of `TYPE_CHARGE` (tijdsafhankelijk: voorbeeld 4). |
| `#ASTER-CONTACT K=V, ...` | Extra regel in `DEFI_CONTACT` (globale sleutelwoorden). Alleen als het model Mecway-contact (`contact2`) heeft; anders vervalt de regel zonder melding. |
| `#ASTER-ZONE K=V, ...` | Wordt achter **elke** contactzone (`ZONE=_F(...)`) gezet; één zone apart instellen kan niet. Een eigen `SANS_GROUP_NO` vervangt die van de bridge (vastgezette slave-knopen), een eigen `INTEGRATION` die van de bridge (`NCOTES` bij kwadratische slave-vlakken). |
| `#ASTER-OPTIE sleutel = waarde` | Geen Code-Aster-code: overschrijft een instelling van de actieve analyse (de sleutels van `CONFIG_BRIDGE["analyses"]`, zie [Instellingen §2](Instellingen_contact_en_nietlineair.md#2-instellingen)), alleen voor dit model en deze run. |
| `#ASTER-POST <code>` | Code-Aster-code na de `CALC_CHAMP`-aanroepen van de bridge, vóór de resultaatexport naar Mecway en `IMPR_RESU`. |
| `#ASTER-BEZWIJKEN materiaal = rek` | Geen Code-Aster-code: elementen van dit Mecway-materiaal bezwijken bij deze vergelijkingsplastische rek (`*` = alle plastische materialen; ook `#ASTER-FAILURE`). Alleen niet-lineair statisch en dynamisch: [`Bezwijken.md`](Bezwijken.md). |
| `#ASTER-SPECTRE X, Y = naam [, K=V]` | Geen Code-Aster-code: in de spectrumanalyse (`spectrum_3d`) is `naam` (een `DEFI_NAPPE` in `AMOR` en `FREQ` of een `FORMULE` uit `#ASTER`-code) het spectrum voor deze richtingen, in plaats van de gravity-tabel; `K=V` gaat mee in `SPECTRE` (`ECHELLE`, `NATURE`, `CORR_FREQ`). Ook `#ASTER-SPECTRUM`. Voorbeeld 11, [`Spectrumanalyse.md`](Spectrumanalyse.md) §2.2. |
| `#ASTER-BRON selectie = snelheid [, fase]` | Geen Code-Aster-code: in de harmonische akoestiek (`acoustic_harm_3d`) een bron op deze vlakselectie, normaalsnelheid de fluid in (m/s of mm/s), fase in graden (ook `#ASTER-SOURCE`; voorbeeld 12, [`Akoestiek.md`](Akoestiek.md) §5). In de harmonische vibro-akoestiek (`vibroacoustic_harm_3d`) ook met een druk (Pa, kPa, bar, ...): een invallende golf met die amplitude (voorbeeld 27, [`Akoestiek.md`](Akoestiek.md) §7). |
| `#ASTER-LASBRON K=V, ...` | Geen Code-Aster-code: een bewegende lasbron (Goldak) in een transiente thermische analyse (ook `#ASTER-WELD`); de bridge schrijft de `FORMULE` en de last zelf. Sleutels en voorbeelden: [`Lassen.md`](Lassen.md), voorbeeld 13. |
| `#ASTER-FASE selectie = graden` | Geen Code-Aster-code: in de harmonische respons (`harmonic_3d`) krijgt de belasting op deze selectie deze fase (`PHAS_DEG`; ook `#ASTER-PHASE`; voorbeeld 15, [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md) §7). |
| `#ASTER-MATERIAAL naam: K=V, ...` | Geen Code-Aster-code: temperatuurafhankelijke E, ν, α, vloeigrens en versteviging van een Mecway-materiaal in de keten thermisch → mechanisch (T31 met een Thermal stress; ook `#ASTER-MATERIAL`). Sleutels: [`Lassen.md`](Lassen.md) §9.2, voorbeeld 17. |
| `#ASTER-WOHLER materiaal: K=V, ...` | Geen Code-Aster-code: Wöhler-curve (tabel `S = [..] MPa, N = [..]`, machtsvorm `S, N, m` of Basquin `Sf, b`; S = amplitude) van dit Mecway-materiaal (`*` = de rest) voor vermoeiing: schade en levensduur per knoop (velden `damage`, `life`). Met `#ASTER-VERMOEIING K=V` (ook `#ASTER-FATIGUE`: `spanning`, `telling`, `herhalingen`), en bij lineair statisch `#ASTER-BLOK a, m, n` (ook `#ASTER-BLOCK`) of `#ASTER-SIGNAAL f1, f2, ...` (ook `#ASTER-SIGNAL`). Voorbeelden 19 en 20, [`Vermoeiing.md`](Vermoeiing.md). |
| `#ASTER-METALLURGIE naam: K=V, ...` | Geen Code-Aster-code: fase-omzettingen in staal (`CALC_META` met een TRC-diagram) voor een Mecway-materiaal in een transiente thermische analyse, met als optie de metallurgische wet in de keten thermisch → mechanisch (ook `#ASTER-METALLURGY`). Sleutels en datasets: [`Lassen.md`](Lassen.md) §10, voorbeeld 25. |
| `#ASTER-XFEM K=V, ...` | Geen Code-Aster-code: een scheur die niet in het mesh zit (XFEM-levelset: `vorm=` CIRKEL, ELLIPSE, RECHTHOEK of HALFVLAK met zijn maten), bij lineair statisch; de bridge schrijft `DEFI_FISS_XFEM`, `MODI_MODELE_XFEM`, `CALC_G_XFEM` en `POST_K1_K2_K3` en zet de velden terug op het mesh van Mecway. Een regel met `vorm=` start een nieuwe scheur. Voorbeeld 29, [`Breukmechanica.md`](Breukmechanica.md) §7. |
| `<<Mecway-selectie>>` | In `#ASTER`, `-POST`, `-ZONE` en `-CONTACT`: wordt de Code-Aster-groepsnaam van die selectie (§3). |

- De soort (`-EXCIT`, `-POST`, ...) mag in hoofd- of kleine letters. Een onbekende soort
  (bijv. `#ASTER-FOO`) geeft `ERROR: Onbekende regel '#ASTER-FOO' wordt overgeslagen`.
- `#ASTER-OPTIE`: het type volgt de bestaande waarde (geheel getal, getal, tekst;
  ja/nee: `ja`/`nee`, `aan`/`uit`, `yes`/`no`, `on`/`off`, `true`/`false`, `1`/`0`,
  `oui`/`non`; een ander woord geeft een WARNING en de instelling blijft). Een sleutel die de analyse niet
  heeft, geeft een ERROR met de lijst van bekende sleutels en wordt genegeerd
  (voorbeeld 6). Elke toegepaste optie staat in de log:
  `INFO: #ASTER-OPTIE newton_max_iter = 40 (was 20).`

Plaats per analyse:

| Analyse (pagina) | `#ASTER` | `#ASTER-EXCIT` | `#ASTER-POST` | `t_res` |
|---|---|---|---|---|
| Statisch, Niet-lineair statisch, Dynamisch (impliciet/expliciet) | na de lasten, vóór `MECA_STATIQUE`/`STAT_NON_LINE`/`DYNA_NON_LINE` | in `EXCIT` van de solve | na `CALC_CHAMP` | alleen niet-lineair en dynamisch |
| Thermisch | na de thermische lasten, vóór `THER_LINEAIRE`/`THER_NON_LINE` | in `EXCIT` van de thermische solve | na de flux-nabewerking; met een Thermal stress (keten thermisch → mechanisch, [`Lassen.md`](Lassen.md) §9) na de mechanische `CALC_CHAMP` (`res` = mechanisch, `res_ther` = thermisch) | met een Thermal stress |
| Modaal | na de lasten, vóór `ASSEMBLAGE` | in de matrices (`CHARGE` van `ASSEMBLAGE`; INFO in de log) en, met *Voorspanning door belastingen* (standaard aan), in `MECA_STATIQUE` (spanningstoestand) | vóór de export | nee |
| Knik | na de lasten, vóór de statische stap | in `MECA_STATIQUE` (spanningstoestand) en in de matrices (`CHARGE` van `ASSEMBLAGE`) | vóór de export | nee |
| Respons op modale basis, Responsspectrum, Harmonische respons | na de opleggingen, vóór `ASSEMBLAGE` | in de matrices (`CHARGE` van `ASSEMBLAGE`) | vóór de export (harmonisch: `res` is een `DYNA_HARMO` met complexe `DEPL`) | nee |
| Akoestiek (harmonisch) | na `AFFE_CHAR_ACOU`, vóór `ASSEMBLAGE` | niet gebruikt (WARNING): `DYNA_VIBRA` neemt hier alleen lastvectoren; gebruik `#ASTER-BRON` | na `DYNA_VIBRA` (resultaat `res`, `ACOU_HARMO`), vóór de export | nee |
| Vibro-akoestiek (harmonisch) | na de lasten van de constructie, vóór de drukknopen en bronnen | in de matrices (`CHARGE` van `ASSEMBLAGE`, alleen als oplegging) | na `CALC_CHAMP` (resultaat `res`, `DYNA_HARMO` met complexe `DEPL`, ook `PRES`), vóór de export | nee |

Gevolg voor *Modaal* en *Knik*: een verbinding die alleen via `#ASTER`-code bestaat
(`LIAISON_ELEM`, `LIAISON_MAIL`, `DDL_IMPO`, ...; bijv. voorbeeld 1 of 2), telt mee in
het eigenwaardeprobleem als de last in `#ASTER-EXCIT` staat. Zonder `#ASTER-EXCIT`
hangt het losse deel los (`ALGELINE3_81`). Krachten in zo'n last dragen niet bij aan
de matrices (`CHARGE` van `ASSEMBLAGE` levert alleen de kinematische condities; EDF
R&D, 2021d); bij *Knik*, en bij *Modaal* met voorspanning, bepalen ze via
`MECA_STATIQUE` wel de spanningstoestand.
Doorgerekend: voorbeeld 1 in beide analyses (§6).

## 3. Selectienamen en groepen

Code-Aster accepteert alleen groepsnamen met een letter vooraan, letters, cijfers en
`_`, maximaal 24 tekens. De bridge hernoemt (`bridge_mesh._aster_names`): ongeldige
tekens worden `_`, een naam die niet met een letter begint krijgt `G` ervoor, te lang
wordt afgekapt en dubbel krijgt `_1`, `_2`. Schrijf daarom altijd `<<Mecway-naam>>`,
nooit de naam zelf. Voorbeelden uit de log:

```
INFO: Groepsnaam '02 Last-punt' -> 'G02_Last_punt' (Code-Aster: letter eerst, ...)
INFO: Groepsnaam '01 Contact onder' -> 'G01_Contact_onder' ...
```

| Mecway | Code-Aster |
|---|---|
| node selection | `GROUP_NO` |
| face selection | `GROUP_MA` met vlakelementen (geen `GROUP_NO`) |
| element selection, elset (materiaal/onderdeel) | `GROUP_MA` met de elementen |

Een volumevlak dat je in `#ASTER`-code noemt, neemt de bridge als randelement in het
model op (anders kan bijv. `LIAISON_ELEM` het niet gebruiken). Een onbekende selectie
geeft `ERROR: #ASTER: selectie 'X' bestaat niet in het mesh.` in
`<model>_<run-id>_bridge_log.txt`; de naam blijft staan en Code-Aster stopt erop
(`MODELISA7_75`; meldingstekst in `Messages/modelisa7.py`, EDF R&D, 2026b).

## 4. Algemene valkuilen

- **Eenheden**: de bridge rekent in SI (m, N, Pa, s; het mesh staat in meter). Waarden
  in `#ASTER`-regels worden niet omgerekend: `FX=200.0` is 200 N, `EPAIS=0.002` is 2 mm.
- **Namen**: kies eigen conceptnamen die de bridge niet gebruikt. De bridge gebruikt
  o.a. `mesh`, `model`, `cara`, `fieldmat`, `MAT_*`, `TRAC_*`, `FN_*`, `load_1`,
  `load_2`, ..., `times`, `outlist`, `listinst`, `contact`, `res`, `res_sup`/`res_moy`/
  `res_inf`, `res_flux`, `t_res`, `tab_*`, en bij *Modaal*/*Knik* `rigidite`, `masse`,
  `rigi_geo`, `numedd`, `stat`, `sig`. Een eigen voorvoegsel (bijv. `u_`) voorkomt
  botsingen. Lange namen (bijv. `verbinding_balk`) werken in 17.4.
- **Inspringen**: de `.comm` is Python. Een regel op het hoogste niveau moet na
  `#ASTER ` direct beginnen; binnen haakjes mag je vrij inspringen.
- **`#ASTER-EXCIT` niet vergeten**: een last die niet in `EXCIT` staat, doet niets.
  Voorbeeld 1 zonder `#ASTER-EXCIT`: de balk hangt los, `FACTOR_11` of `FACTOR_42`
  (*Statisch*, afhankelijk van het model; met `solver_nprec` -1 ook `FACTOR_57`) of `MECANONLINE9_4` (*Niet-lineair statisch*). Bij *Modaal* en *Knik* geldt hetzelfde:
  zonder `#ASTER-EXCIT` ontbreekt de verbinding in de matrices (`ALGELINE3_81`).
- **Niets herhalen wat de bridge schrijft**: bijv. `FROTTEMENT` via `#ASTER-CONTACT`, of
  `ALGO_CONT`/`COEF_PENA_CONT` via `#ASTER-ZONE` als *Contactmethode* = PENALISATION.
  Python stopt dan met `SyntaxError: keyword argument repeated: ...`. Zo'n fout staat
  alleen in het Code-Aster-venster en in `<model>_<run-id>_console.txt`, niet in de
  `.mess` (die eindigt zonder `<FIN>`, met `DIAGNOSTIC JOB : OK`). De bridge leest de
  console-uitvoer en meldt de Python-fout met de foutregel.
- **Resultaat in de tijd**: `t_res` (het laatst berekende tijdstip) bestaat alleen bij
  niet-lineair statisch en dynamica (tabel in §2); gebruik anders `NUME_ORDRE=1`.

## 5. Voorbeelden

Testmodellen (staal: E = 210 GPa, ν = 0,3, ρ = 7850 kg/m³; maten in mm). A, C en S
staan in `TestFiles/Voorbeelden/` (`Voorbeeld_A.liml`, `Voorbeeld_C.liml`,
`Voorbeeld_S.liml`, zonder `#ASTER`-regels: plak de regels van het voorbeeld in het
genoemde veld en kies de analyse). Ze zijn gemaakt met `maak_voorbeelden.py` in die map;
`python maak_voorbeelden.py --run` rekent alle varianten van de voorbeelden 1 tot 8 door
(bridge + Code-Aster, zonder Mecway) en print de uitkomsten hieronder.

- **(A)** hex20-blok 20 × 20 × 20 (2 × 2 × 2 elementen, elset `Blok`, x = 0 … 20) met
  een losse buis 8/6 mm (*UniformCircularTube*), L = 50 mm, 5 line2-elementen (elset
  `Balk`) vanuit het midden van het eindvlak x = 20 in +x, zonder gedeelde knopen.
  Selecties: `Root` (vlak x = 0, *Fixed*), `Tip` (vlak x = 20, waar de balk begint),
  `BalkStart` en `BalkEind` (eerste en laatste balkknoop), `02 Last-punt` (dezelfde knoop
  als `BalkEind`); 50 N in Y en −100 N in Z op `BalkEind`.
- **(C)** twee hex8-blokken 20 × 20 × 10 (elk 2 × 2 × 1, elsets `Onder` z = 0 … 10 en
  `Boven` z = 10 … 20) met eigen knopen; Mecway-contact (*unilateral elastic*, *normal
  stiffness* 100000 GPa/m, zonder wrijving) tussen `01 Contact onder` (bovenvlak van
  `Onder`, master) en `02 Contact boven` (ondervlak van `Boven`); `Bodem` (onderkant)
  vast, `Top` (bovenkant) 0,01 mm omlaag en in x en y vast. *Niet-lineair statisch*,
  1 s, stap 0,1 s.
- **(S)** hex8-blok 20 × 20 × 10 (4 × 4 × 2, elset `Blok`, `Bodem` vast) met een losse
  quad4-plaat 20 × 20, dikte 2 mm (4 × 4, elset `Plaat`), rechtop in het vlak x = 10
  (z = 10 … 30); `Plaatvoet` = de knopen van de onderrand (op het bovenvlak van het
  blok, niet gedeeld), `PlaatTop` = de knopen van de bovenrand, met 10 N in X.
- **(R)** uitkragende hex8-balk 100x10x10 mm (`Root` vast, `Tip` = eindvlak); niet in de
  repository.

### Voorbeeld 1 – Balk aan een volumevlak (`LIAISON_ELEM`, `3D_POU`)

Doel: een balk die op een volumevlak staat zonder gedeelde knopen verbinden. De
balkknoop krijgt zes relaties met het vlak (EDF R&D, 2021a; catalogus
`affe_char_meca.py`, blok `b_3d_pou`, EDF R&D, 2026a).

OpenRadioss > Custom model definition:

```
#ASTER verb = AFFE_CHAR_MECA(MODELE=model,
#ASTER     LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='<<Tip>>',
#ASTER                     GROUP_NO_2='<<BalkStart>>'))
#ASTER-EXCIT verb
```

In de `.comm` (na `load_2`, vóór `MECA_STATIQUE`):

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

Uitkomst (model A): *Statisch* verplaatsing van `BalkEind` DY = 7,346e-5 m,
DZ = −1,469e-4 m; alleen de ingeklemde buis (F·L³/3EI) geeft 7,218e-5 en −1,444e-4 m,
het verschil (1,8%) is het meeverende blok. *Niet-lineair statisch* gelijk (< 0,01%; de
balk blijft daar geometrisch lineair, WARNING).

Valkuilen:
- `GROUP_MA_1` is een face selection op het volume (het vlak onder de balk),
  `GROUP_NO_2` een node selection met precies één balkknoop.
- Doorgerekend met een hex20-volume; een lineair (hex8) volume is niet getest. Volgens
  U4.44.01 moet het volume kwadratisch zijn: NIET geverifieerd in de 17.4-documentatie.
- Zonder `#ASTER-EXCIT verb` hangt de balk los (§4).
- *Modaal* en *Knik*: werkt met `#ASTER-EXCIT verb` (de verbinding komt dan in de
  matrices, §2): *Modaal* f1 = f2 = 2855,4 Hz (een paar, Y en Z), *Knik* ±363,5 en
  ±993,3 (model A). Controle met een star blok (model A met E = 2,1·10¹⁸ Pa voor het
  blok): f1 = f2 = 2894,35 Hz tegen analytisch 2894,3 Hz (ingeklemde buis 8/6 mm,
  L = 50 mm, 5 balkelementen; 07-10-2026). Met het stalen blok ligt f1 1,3% lager: het
  blok veert mee.
- Schaal aan balk: `OPTION='COQ_POU'` (vraagt `CARA_ELEM` en `AXE_POUTRE`); schaal aan
  volume: `OPTION='COQ_3D'` (vraagt `GROUP_MA_COQUE`, `GROUP_MA_MASSIF` en
  `CARA_ELEM`), of `LIAISON_MAIL` (voorbeeld 2). Beide opties staan in de
  17.4-catalogus; niet doorgerekend.

### Voorbeeld 2 – Schaal op een volume (`LIAISON_MAIL`, `COQUE_MASSIF`)

Doel: de rand van een schaal (DKT) stijf verbinden met een volume zonder gedeelde
knopen, inclusief de rotaties. De rotaties van de schaalknopen volgen uit de
verplaatsingen van het volume over de dikte `EPAIS`; `EPAIS` en `CHAM_NORMALE` (de
normaal van de schaal) zijn daarvoor verplicht (catalogus `affe_char_meca.py`, blok
`b_COQUE_MASSIF`).

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

In de `.comm`:

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

Uitkomst (model S): 10 N dwars op de bovenrand geeft 0,00897 mm uitbuiging (gemiddeld
over `PlaatTop`, beide statische analyses); een ingeklemde plaatstrook (F·L³/3EI met
1-ν²) geeft 0,00867 mm, het verschil (3,5%) is vooral het meeverende blok. De
verbinding werkt dus als een inklemming.

Valkuilen:
- `GROUP_MA_MAIT` zijn de **volume-elementen** (de elset), niet een vlak.
- `EPAIS` in meter, gelijk aan de plaatdikte.
- Staat de plaat loodrecht op X, dan zet de bridge zelf een `VECTEUR` in
  `AFFE_CARA_ELEM COQUE` (anders `PLATE1_40`).

### Voorbeeld 3 – Extra last en blokkering

Doel: een puntkracht en een rotatieblokkering die je niet in Mecway wilt zetten, op een
selectie met een "lastige" naam. Model A met voorbeeld 1 in het OpenRadioss-veld.

Mystran > Custom bulk data (node selection `02 Last-punt` = de balkeindknoop):

```
$ Extra last en blokkering voor Code-Aster (SI-eenheden: N, m)
$ASTER extra = AFFE_CHAR_MECA(MODELE=model,
$ASTER     FORCE_NODALE=_F(GROUP_NO='<<02 Last-punt>>', FX=200.0),
$ASTER     DDL_IMPO=_F(GROUP_NO='<<02 Last-punt>>', DRX=0.0))
$ASTER-EXCIT extra
```

In de `.comm` (de regels uit het OpenRadioss-veld staan ervoor, §1):

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

Uitkomst: DX van de balkeindknoop 2,211e-6 m (*Statisch*; alleen de buis, F·L/EA:
2,165e-6 m).

Valkuilen:
- De eerste regel (`$ Extra ...`) is Mystran-commentaar; de bridge slaat hem over.
- `DRX`/`DRY`/`DRZ` alleen op balk- en schaalknopen; volumeknopen hebben geen rotaties.
- Een blokkering op knopen die Mecway al vastzet, geeft een dubbele voorwaarde en kan
  een singuliere matrix geven (KNOWN_BUGS 8).

### Voorbeeld 4 – Tijdsafhankelijke extra last (niet-lineair)

Doel: een last die in de tijd oploopt. `#ASTER-EXCIT` kent geen `FONC_MULT`; maak de
last daarom met `AFFE_CHAR_MECA_F` en een functie van `INST` (catalogus
`defi_fonction.py`). Model A met voorbeeld 1 in het OpenRadioss-veld *Custom model
definition*.

OpenRadioss > Custom engine input:

```
#ASTER f_ramp = DEFI_FONCTION(NOM_PARA='INST', VALE=(0.0, 0.0, 1.0, 300.0),
#ASTER                        PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')
#ASTER ramp = AFFE_CHAR_MECA_F(MODELE=model,
#ASTER     FORCE_NODALE=_F(GROUP_NO='<<BalkEind>>', FX=f_ramp))
#ASTER-EXCIT ramp
```

In de `.comm` (vóór `STAT_NON_LINE`):

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

Uitkomst (DX van de balkeindknoop per tijdstap in de resultaten; in de `.mess` kan het
met `POST_RELEVE_T` van `DEPL` en `TOUT_ORDRE='OUI'`, zoals voorbeeld 7): DX neemt per
0,1 s toe met 3,317e-7 m (de oplopende 300 N), van 3,317e-7 m op t = 0,1 tot
3,317e-6 m op t = 1 (alleen de buis, F·L/EA: 3,248e-6 m). Zonder deze last is DX
vrijwel 0 (−1,4e-11 m): de balk rekent ook hier geometrisch lineair. DY/DZ van de
constante Mecway-kracht zijn vanaf de eerste stap volledig.

Valkuilen:
- Alleen voor niet-lineair statisch en dynamisch. `MECA_STATIQUE` rekent op INST = 0:
  daar is deze last nul (doorgerekend: DX = 0).
- Constante lasten zonder functie (ook die van de bridge) werken vanaf de eerste
  tijdstap volledig.

### Voorbeeld 5 – Contact: penalty en Newton voor de geometrie

Doel: de contactformulering van de bridge (`FORMULATION='CONTINUE'`) per zone aanpassen.
Voor penalty-contact met Mecway's eigen stijfheid is de instelling *Contactmethode* =
PENALISATION de eerste keus ([Instellingen §3](Instellingen_contact_en_nietlineair.md#3-contact));
dit voorbeeld laat zien hoe het met `#ASTER`-regels gaat, bijv. als Mecway geen
*normal stiffness* heeft. Sleutelwoorden volgens de catalogus `defi_contact.py`
(EDF R&D, 2026a; achtergrond EDF R&D, 2021b).

OpenRadioss > Custom model definition:

```
#ASTER-ZONE ALGO_CONT='PENALISATION', COEF_PENA_CONT=1.0E14
#ASTER-CONTACT ALGO_RESO_GEOM='NEWTON'
```

In de `.comm`:

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

Uitkomst (model C): de reactiekracht (voorbeeld 7) is 42,36 kN met penalty tegen
47,41 kN zonder: met penalty dringen de blokken een beetje in elkaar. Handcontrole: de
contactveer 1e14 Pa/m × 4·10⁻⁴ m² = 4·10¹⁰ N/m in serie met de blokken
(47,41 kN / 0,01 mm = 4,74·10⁹ N/m) geeft 42,39 kN. *Contactmethode* = PENALISATION
met *normal stiffness* 100000 GPa/m (= 1e14 Pa/m) in Mecway geeft dezelfde 42,36 kN.

Valkuilen:
- `ALGO_RESO_GEOM`/`ALGO_RESO_CONT` horen bij `DEFI_CONTACT` (`#ASTER-CONTACT`),
  `ALGO_CONT`/`COEF_PENA_CONT`/`CONTACT_INIT`/`INTEGRATION` bij `ZONE` (`#ASTER-ZONE`).
- Niet samen met *Contactmethode* = PENALISATION: `ALGO_CONT` staat er dan twee keer
  (doorgerekend: `SyntaxError: keyword argument repeated: ALGO_CONT`). Zonder *normal
  stiffness* in Mecway valt die instelling terug op STANDARD (WARNING).
- Niet herhalen wat de bridge schrijft: `FORMULATION`, `FROTTEMENT`, `COULOMB`,
  `GROUP_MA_MAIT`/`GROUP_MA_ESCL` (§4).
- Zonder Mecway-contact worden `-CONTACT`/`-ZONE` genegeerd.

### Voorbeeld 6 – Contactstart en solverinstellingen (`#ASTER-OPTIE`)

Doel: alle contactpunten bij de start actief, vaste-puntiteratie voor het contact, en
voor dit model meer Newton-iteraties, strengere convergentie en kleine verplaatsingen.
Minder stappen: *Time step size* 0,25 s in Mecway (de bridge rekent Mecway's stappen;
`substeps_per_interval` geldt alleen in een model zonder stapgrootte).

OpenRadioss > Custom model definition:

```
#ASTER-ZONE CONTACT_INIT='OUI'
#ASTER-CONTACT ALGO_RESO_CONT='POINT_FIXE', ITER_CONT_MAXI=50
#ASTER-OPTIE newton_max_iter = 40
#ASTER-OPTIE convergence_resi_rela = 1e-8
#ASTER-OPTIE deformation = PETIT
```

In de `.comm`:

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

Uitkomst (model C): reactiekracht 47,45 kN na 4 stappen (met de standaard GROT_GDEP
47,41 kN).

Valkuilen:
- De sleutels zijn bridge-instellingen (pagina van de analyse), geen
  Code-Aster-woorden. Welke er zijn, hangt van de analyse af: `schema = HHT` in een
  niet-lineair statische analyse geeft
  `ERROR: #ASTER-OPTIE 'schema' bestaat niet voor deze analyse; genegeerd. Bekend:
  contact_algo, convergence_criterion, convergence_resi_maxi, ...`.
- `deformation` is een keuze voor het hele model; bij grote verplaatsingen zet de bridge
  per elementtype de vorm die Code-Aster accepteert
  ([Instellingen §2.3](Instellingen_contact_en_nietlineair.md#23-kinematica-deformation)).
- Nuttige opties bij convergentieproblemen: `convergence_criterion = MAXI` of
  `RELA_OF_MAXI` (met `convergence_resi_maxi`), `contact_algo = PENALISATION`
  (`convergence_resi_rela` is al standaard 1e-5)
  ([`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md#mecanonline9_7--newton-convergeert-niet));
  in de `.comm` nagelopen dat ze als `RESI_GLOB_MAXI` en `ALGO_CONT` aankomen.

### Voorbeeld 7 – Reactiekracht op een vlak in de `.mess`

Doel: de totale reactiekracht op de ingeklemde onderkant als tabel (`POST_RELEVE_T`:
catalogus `post_releve_t.py`, EDF R&D, 2026a; achtergrond EDF R&D, 2021c).

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

In de `.comm` (na de `CALC_CHAMP`-aanroepen; `REAC_NODA` is er dan al):

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

Uitvoer in de `.mess` (model C, *Niet-lineair statisch*):

```
INTITULE         RESU     NOM_CHAM         NUME_ORDRE   INST         DX           DY           DZ
reactie          00000009 REAC_NODA                  10  1.00000E+00  6.82121E-13  4.54747E-13  4.74133E+04
```

Valkuilen:
- Een face selection is een `GROUP_MA`. `POST_RELEVE_T` wil hier `GROUP_NO`;
  `GROUP_MA=` in `ACTION` gaf `SUPERVIS_4`, en `GROUP_NO='Bodem'` (bestaat niet als
  knoopgroep) gaf zonder melding een **lege** tabel. Maak de knoopgroep dus met
  `DEFI_GROUP`. In deze tests werkte `DEFI_GROUP(reuse=mesh)` na de solve; breekt een
  job daarop zonder melding af, zie
  [Foutmeldingen §9](Foutmeldingen_CodeAster.md#zonder-code-crash-afgebroken-job-of-loggingfout).
- `UNITE=6` schrijft naar de `.mess`. Unit 8 is het `.resu`-bestand dat de bridge in de
  route `tabel` zelf leest (in de route `liml` bestaat het niet); daar niet naartoe
  schrijven.
- *Statisch*: `t_res` bestaat niet; schrijf `NUME_ORDRE=1` (doorgerekend op model A met
  `GROUP_MA='<<Root>>'`: reactie (0; -50; 100) N, gelijk aan minus de last).

### Voorbeeld 8 – Maximale von Mises in de `.mess`

Doel: de grootste en kleinste von Mises-spanning (knoopwaarde) als tabel.

OpenRadioss > Custom engine input:

```
#ASTER-POST tmax = POST_RELEVE_T(ACTION=_F(OPERATION='EXTREMA',
#ASTER-POST     INTITULE='vmis_max', RESULTAT=res, NOM_CHAM='SIEQ_NOEU',
#ASTER-POST     NOM_CMP='VMIS', TOUT='OUI'))
#ASTER-POST IMPR_TABLE(TABLE=tmax, UNITE=6)
```

Uitvoer in de `.mess` (model A met voorbeeld 1, *Statisch*):

```
INTITULE         RESU     NOM_CHAM         NUME_ORDRE   INST         EXTREMA  NOEUD    CMP      VALE
vmis_max         0000000a SIEQ_NOEU                   1  0.00000E+00 MAX      22       VMIS      7.08280E+06
vmis_max         0000000a SIEQ_NOEU                   1  0.00000E+00 MIN      8        VMIS      2.05799E+05
...                                                                 (ook MAXI_ABS, MINI_ABS)
```

Valkuilen:
- De bridge berekent `SIGM_NOEU`, `SIEQ_NOEU` en, in de route `liml`, voor
  volume-elementen ook `SIGM_ELNO`/`SIEQ_ELNO` al zelf (bij model A staan `stressxx` …
  `vonmises` als knoop- en als elementknoopwaarden in de resultaten, met of zonder
  extra regels). Een eigen
  `CALC_CHAMP(... CONTRAINTE=('SIGM_ELNO',), CRITERES=('SIEQ_ELNO',))` voegt niets toe
  en geeft alarm `CALCCHAMP_1`.
- Velden die de export niet kent, komen niet in Mecway en ook niet in de MED-uitvoer
  van de bridge (vaste veldenlijst); print ze met `IMPR_TABLE`.
- Bij niet-lineair en dynamica geeft `TOUT='OUI'` zonder `INST` een tabel per tijdstap;
  met `INST=t_res` alleen het laatste tijdstip.

### Voorbeeld 9 – Star deel 90 graden draaien (grote rotatie, `FORMULE`)

Doel: een star deel (rol, stempel, klem) over een grote hoek om een as draaien. Een
opgelegde knooprotatie (Mecway *Node rotation*), een balk als arm en een starre
koppeling (RBE2, `LIAISON_SOLIDE`) gaan in Code-Aster uit van kleine rotaties; bij grote
rotaties werkt dat niet (KNOWN_BUGS 11). Robuust is de exacte starre beweging als
opgelegde verplaatsing: u = (R(t) - I)(X - C), met C een punt op de as. Zo is
een buigmodel (profiel om een mal) impliciet tot 90 graden gerekend.

Mecway: zet *Node rotation*, de arm en de RBE2 op *suppressed* (of verwijder ze) en maak
een selectie van de knopen of vlakken van het starre deel, hier `Tip`. Kies
*Niet-lineair statisch*. CCX > Custom model definition (`**ASTER`), OpenRadioss
(`#ASTER`) of Mystran (`$ASTER`):

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

Voor een draaiing om de z-as wissel je de rollen: `FDX` en `FDY` met (X, Y), `FDZ` nul.

Uitkomst (model R, tipvlak 90 graden om de x-as door (0,1; 0,005; 0,005) m): knoop
(0,1; 0; 0) verplaatst (0; 0,01; 0) m, exact de starre rotatie (10 stappen, geen
stapverkleining).

Valkuilen:
- `X`, `Y`, `Z` in een `FORMULE` zijn de beginposities van de knopen; de hoek moet een
  functie van `INST` zijn, en de tijdstappen klein genoeg (de bridge deelt een stap
  automatisch als Newton niet convergeert).
- `deformation = GROT_GDEP` is de standaard; de regel maakt de keuze alleen expliciet.
- Een knoop die al vastgezet is (fixed), mag niet ook in de geroteerde groep zitten
  (dubbele voorwaarde).
- `cos`/`sin` en eigen functies geef je als argument aan `FORMULE` mee.

### Voorbeeld 10 – Niet-lineaire knik per model (`#ASTER-OPTIE`)

Doel: in één model de stabiliteit per stap (`CRIT_STAB`) en een knikvorm als
imperfectie aanzetten, zonder de instellingen van de pagina *Niet-lineair statisch* te
veranderen (uitleg: [`Modaal_en_knik.md`](Modaal_en_knik.md) §5). Mecway: *Nonlinear
Static*, de last met een tijdstabel vanaf 0. CCX > Custom model definition:

```
** ASTER-OPTIE crit_stab = ja
** ASTER-OPTIE imperfection_amplitude = 0.001
** ASTER-OPTIE imperfection_unit = L
```

Twintig stappen: *Time step size* 0,05 s bij een periode van 1 s (de bridge rekent
Mecway's stappen).

`imperfection_unit = L` maakt de amplitude een fractie van de grootste afmeting van het
model (hier L/1000); met `m` (standaard) is het een lengte in meter. Een andere
knikvorm: `imperfection_mode = 2`.

Uitkomst (de kolom van verificatie NK-03, hex20, last tot 0,9 Pcr): de log toont de
vier opties (`INFO: #ASTER-OPTIE crit_stab = True (was False).` enz.), `Imperfectie:
amplitude 0.001 x L, L = 1 m ... = 0.001 m`, de kniklastfactor van de imperfectiestap
1,11339 en per stap het stabiliteitscriterium (op t = 1: −2,70); `DIAGNOSTIC JOB : OK`,
dezelfde getallen als NK-03 met de instellingen op de pagina.

### Voorbeeld 11 – Eigen responsspectrum met meerdere dempingen (`#ASTER-SPECTRE`)

Doel: een spectrum dat met de demping varieert (hier voor 0,5% en 5%, logaritmisch in
de frequentie, lineair in de demping), zoals Code-Aster-testcase sdld25a. Een
gravity-tabel kan dat niet: die geldt voor één demping. Mecway: *Frequency* met de
modes, analyse `spectrum_3d` (uitleg: [`Spectrumanalyse.md`](Spectrumanalyse.md)).
CCX > Custom model definition:

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

De versnellingen in `VALE` staan in m/s² (met `, ECHELLE=9.81` achter de naam zijn het
eenheden g). De demping per mode komt hier uit Mecway's *Rayleigh damping* (β =
5e-4 s), dus `spectrum_damping = 0`. Een richting met `#ASTER-SPECTRE` heeft geen
gravity nodig. Het spectrum moet een `DEFI_NAPPE` (parameter `AMOR`) of een `FORMULE`
in `AMOR` en `FREQ` zijn; een `DEFI_FONCTION` alleen in `FREQ` geeft een fout van
`COMB_SISM_MODAL`.

Uitkomst (verificatie SP-01, de nabouw van sdld25a met Mecway-veren en -massa's): de
log meldt `INFO: #ASTER-regels: 6 code, ..., 1 SPECTRE, ...` en de twee opties; de
absolute versnellingen `accelx` zijn gelijk aan de TEST_RESU-waarden van sdld25a
(bijv. P1 10,4498 m/s²).

### Voorbeeld 12 – Akoestiek harmonisch: bron met fase en eigen frequenties (`#ASTER-BRON`)

Doel: een luidspreker met 2 mm/s en 90 graden fase op een vlakselectie zonder
voorvoegsel, en de frequenties per model (uitleg: [`Akoestiek.md`](Akoestiek.md) §5).
Mecway: *Acoustic Resonance 3D*, lucht met dichtheid, vlakselectie `Luidspreker` op
x = 0, vlakselectie `ABSORBEREND_Einde` op x = L en knoopselecties `MICROFOON_Eind`,
`MICROFOON_Midden`. CCX > Custom model definition:

```
** ASTER-BRON Luidspreker = 2 mm/s, 90
** ASTER-OPTIE harm_freq_list = 200, 500
```

`#ASTER-BRON selectie = snelheid [, fase]`: normaalsnelheid de fluid in (m/s of mm/s),
fase in graden (`, fase = 90` mag ook); ook `#ASTER-SOURCE`. De selectie moet een
vlakselectie zijn; een regel voor een `BRON_`-selectie vervangt de standaardsnelheid.
Met een bron kiest `auto` de analyse *Akoestiek (harmonisch)*. In de `.comm`:

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

Uitkomst (verificatie AH-08, hex20-buis 1 x 0,1 x 0,1 m): op x = 0 is p = i·ρcv =
0,816i Pa (Re < 1e-5 Pa), beide microfoons 89,20 dB, de fase in `MICROFOON_Eind`
90° − kL binnen 0,02°; `DIAGNOSTIC JOB : OK`.

### Voorbeeld 14 – Vibro-akoestiek: modes vanaf een frequentie (`#ASTER-OPTIE`)

Doel: in een paneel-op-holte-model alleen de gekoppelde modes boven 100 Hz (uitleg:
[`Akoestiek.md`](Akoestiek.md) §6). Mecway: *Frequency 3D* met *Number of modes* 3,
een stalen plaat (onderdeel `Paneel`, schalen) op een luchtvolume (onderdeel `Lucht`,
materiaal met alleen *Speed of sound* en *Density*: daaraan herkent de bridge het
fluïdum; een onderdeelnaam `LUCHT_...` of `FLUID_...` mag ook). Speciale
selectienamen van de vibro-akoestiek (geen `#ASTER`-regel nodig): `OPEN_...` (knopen
of vlakken, p = 0) en `KOPPEL_...` (vlakken, handmatige koppelvlakken; ook
`COUPLING_...`). CCX > Custom
model definition:

```
** ASTER-OPTIE vibro_freq_min = 100
```

Met een fluïdum kiest `auto` de analyse *Vibro-akoestiek (modes)*. In de `.comm` wordt
de ondergrens van de band waarin `INFO_MODE` en `CALC_MODES OPTION='BANDE'` zoeken:

```
bridge_n = 3
bridge_fmin = 100.0
...
res_band = CALC_MODES(
    ...
    OPTION='BANDE',
    CALC_FREQ=_F(FREQ=(bridge_fmin, _hi)),
```

Uitkomst (verificatie VA-05c, plaat 0,5 × 0,4 m, 2 mm, op een luchtholte 0,5 × 0,4 ×
0,3 m): de pompmode (54,96 Hz) valt weg; mode 1–3 zijn de plaatmodes (2,1), (1,2),
(2,2) met 109,0 / 142,3 / 200,9 Hz; `DIAGNOSTIC JOB : <A>_ALARM`, alleen
`MODELISA4_8`/`MODELISA8_13` (schaal en koppelvlak zijn aparte cellen op dezelfde
knopen, [`Akoestiek.md`](Akoestiek.md) §6.7).

### Voorbeeld 27 – Vibro-akoestiek harmonisch: invallende golf met fase (`#ASTER-BRON` met een druk)

Doel: een kanaal waarin een geluidsgolf van 0,5 Pa binnenkomt met −30° fase, bij één
frequentie (uitleg: [`Akoestiek.md`](Akoestiek.md) §7). Mecway: *Frequency 3D* met een
luchtvolume (materiaal met alleen *Speed of sound* en *Density*), vlakselectie `Inlaat`
op x = 0 (zonder voorvoegsel), vlakselectie `ABSORBEREND_Uitlaat` op x = L, knoopselectie
`MICROFOON_Uitlaat`; analyse `vibroacoustic_harm_3d` zelf kiezen (`auto` rekent de
gekoppelde modes). CCX > Custom model definition:

```
** ASTER-BRON Inlaat = 0.5 Pa, -30
** ASTER-OPTIE harm_freq_list = 500
```

In de vibro-akoestiek maakt een **druk-eenheid** (Pa, N/m2, kPa, kN/m2, MPa, N/mm2, GPa,
bar, mbar, psi) van `#ASTER-BRON` een
invallende golf (`ONDE_FLUI`, de amplitude van de golf die het fluïdum in loopt), een
snelheid (m/s, mm/s, mm/ms, in/s, ft/s of geen eenheid) een snelheidsbron (`VITE_FACE`);
een andere eenheid geeft een ERROR. Bijvoorbeeld
`** ASTER-BRON Inlaat = 14 mm/s, 90`. Zonder `#ASTER`-regel: een vlakselectie
`INVALLEND_...` met de instelling *Amplitude invallende golf* of `BRON_...` met
*Snelheid BRON_-vlakken*. In de `.comm`:

```
ch_onde_1 = AFFE_CHAR_MECA(MODELE=model, ONDE_FLUI=_F(GROUP_MA='Inlaat', PRES=1.0))
...
        _F(VECT_ASSE=vec_onde_1, COEF_MULT=1.0, PUIS_PULS=1, PHAS_DEG=60.0),  # #ASTER-BRON Inlaat
```

(`PRES` = 2 × 0,5 Pa: Code-Aster's rand geeft een binnenlopende golf met amplitude
`PRES`/2; `PHAS_DEG` = 90 + fase, want de vector wordt met iω vermenigvuldigd.)

Uitkomst (verificatie VH-08, golfgeleider 1 × 0,1 × 0,2 m, hex20, ρ 1,3, c 343): de druk
in de vier knopen van ahlv101a is de TEST_RESU-waarde van ahlv101a × e^{−i30°} op
≤ 1,1e-7; met `14 mm/s, 90` (VH-07) is het ahlv100b × i op ≤ 2,3e-7;
`DIAGNOSTIC JOB : OK`.

### Voorbeeld 13 – Bewegende lasbron (`#ASTER-LASBRON`)

Doel: het temperatuurveld van een lasrups met een Goldak-bron, zonder zelf een formule
te schrijven (uitleg en alle sleutels: [`Lassen.md`](Lassen.md)). Mecway: *Thermal
transient* (T31) met een begintemperatuur; CCX > Custom model definition:

```
** ASTER-LASBRON Q=1250, eta=0.8, v=0.005, start=(0.01, 0, 0), richting=(1, 0, 0)
** ASTER-LASBRON af=0.001, ar=0.002, b=0.001, c=0.001, symmetrie=1
```

De bridge zet in de `.comm` (na de thermische lasten):

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

met `lasbron_1` in `EXCIT`, en na de solve de energiecontrole (`BRIDGE_LASBRON` in de
`.mess`).

Uitkomst (verificatie WE-02, halve plaat 55 × 15 × 15 mm, 35 600 knopen): `DIAGNOSTIC
JOB : OK`, het mesh neemt 500,00 W op (100,0% van η·Q/2), de temperaturen naast en
achter de bron liggen binnen 1,2% van dezelfde bron analytisch gevouwen.

Valkuilen:
- Waarden in SI: coördinaten in meter, ook als het Mecway-model in mm is.
- Een tweede bron begint met een regel die met `Q=` begint; elke bron krijgt een eigen
  `t0`. Alle bronnen staan samen in een last (`lasbron`, KNOWN_BUGS 70).
- Alleen in een transiente thermische analyse; in een mechanische analyse wordt de
  regel genegeerd (WARNING).

### Voorbeeld 15 – Harmonische respons: lastfase en meetpunt (`#ASTER-FASE`)

Doel: twee harmonische krachten in tegenfase op een constructie en de
frequentierespons in een punt (uitleg: [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md)
§7). Mecway: *Frequency 3D* (of *Dynamic Response 3D*) met de krachten op de
knoopselecties `Last` en `Last2` (de waarde is de amplitude), Rayleigh-demping, en een
knoopselectie `MEETPUNT_Tip`; in het hoofdvenster de analyse *Harmonische respons*
(`harmonic_3d`). CCX > Custom model definition:

```
** ASTER-FASE Last2 = 180
** ASTER-OPTIE harm_freq_list = 5, 10, 16.7, 25
```

`#ASTER-FASE selectie = graden`: de belasting op die selectie krijgt die fase
(`PHAS_DEG` in `EXCIT`; ook `#ASTER-PHASE`); belastingen zonder regel hebben fase 0.
De selectie moet een belasting hebben (anders ERROR); een last die op meerdere
selecties met verschillende fasen werkt (samengevoegde balklasten), kan niet (ERROR:
geef elke selectie een eigen belasting). In de `.comm`:

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

Een amplitude die met de frequentie verandert: geef de belasting in Mecway een tabel;
de kolom *time* is dan de frequentie in Hz (bijv. een onbalanskracht m·e·ω²).
De knoopselectie `MEETPUNT_...` (of `PROBE_...`) geeft per frequentie |u|, |a|, Re/Im
en fase in de log en in `<model>_<run-id>_meetpunten.csv`.

Uitkomst (massa op een veer, `DIAGNOSTIC JOB` OK met alarm `MODELISA8_14` van het
veerelement, ook zonder deze regels): verificatie HR-05 (10 N op `Last`, 4 N op `Last2`
met `#ASTER-FASE Last2 = 180`): de respons is die van 6 N (amplitude < 1e-7, fase
< 1e-5 graden van de 1-vrijheidsgraadoplossing); HR-04 (F(f) = 10 + 2f N uit een tabel,
`#ASTER-FASE Last = 90`, `MEETPUNT_Massa`): idem, en de CSV gelijk aan de
knoopwaarden.

### Voorbeeld 16 – Breukmechanica: eigen R_INF/R_SUP per model (`#ASTER-OPTIE`)

Doel: K en G langs een gemeshte scheur met een eigen ring voor `CALC_G` (uitleg:
[`Breukmechanica.md`](Breukmechanica.md)). Mecway: *Static 3D*; de scheur is open
gemaakt met *Disconnect elements* en heeft de speciale selectienamen (geen
`#ASTER`-regel nodig): knoopselectie `SCHEUR_FRONT` en vlakselecties
`SCHEUR_LIP_BOVEN`/`SCHEUR_LIP_ONDER` (of `CRACK_FRONT`, `CRACK_LIP_UPPER`,
`CRACK_LIP_LOWER`; meer scheuren met een achtervoegsel, `SCHEUR_FRONT_A`, ...). CCX >
Custom model definition:

```
** ASTER-OPTIE fracture_r_inf = 0.2
** ASTER-OPTIE fracture_r_sup = 0.5
```

In de `.comm` (na de resultaatexport):

```
scheur_g_1 = CALC_G(
    RESULTAT=res_fiss,
    OPTION=('G', 'K'),
    THETA=_F(FISSURE=fond_1, R_INF=0.2, R_SUP=0.5), FORM_FISS='CERCLE', RAYON=2.0...,
)
```

Uitkomst (verificatie BR-04, Code-Aster-testcase forma07a via de bridge, schijfvormige
scheur met straal 2 m): K1 MAX van `POST_K1_K2_K3` 1 607 011,55 Pa·√m (gelijk aan
de TEST_TABLE-waarde), G 11,68 J/m² (analytisch 11,59); `DIAGNOSTIC JOB : OK`.

### Voorbeeld 17 – Restspanning met temperatuurafhankelijk staal (`#ASTER-MATERIAAL`)

Doel: na het thermische lassen (voorbeeld 13) de restspanning en vervorming, met E,
vloeigrens en α die met de temperatuur dalen/stijgen (Mecway kent dat alleen voor λ
en c). Mecway: *Thermal transient* (T31) met de lasbron, plus **Fixed support** of
**Displacement** en een **Thermal stress** (referentie = begintemperatuur) in hetzelfde
model; materiaal met *Young's modulus*, *Poisson's ratio* en *Thermal expansion
coefficient*. CCX > Custom model definition (naast de `ASTER-LASBRON`-regels):

```
** ASTER-MATERIAAL Staal: TC=(20, 600, 1200, 1500), E=(210e9, 120e9, 15e9, 10e9),
** ASTER-MATERIAAL     SY=(355e6, 150e6, 15e6, 10e6), H=1e9,
** ASTER-MATERIAAL     ALPHA=(1.2e-5, 1.35e-5, 1.5e-5, 1.5e-5), TC_CUT=1500
```

De bridge zet in de `.comm` (na de thermische solve, met `res_ther` = het thermische
resultaat; temperaturen in °C):

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

Uitkomst (verificatie WE-09, eenassig verhinderde staaf met eigen `#ASTER-MATERIAAL`-waarden:
E, SY en α lineair in T):
`DIAGNOSTIC JOB : OK`, spanning elastisch, plastisch, tijdens het afkoelen en de
restspanning (= SY(T0) na omgekeerd vloeien) gelijk aan de handberekening tot 4·10⁻⁸;
WE-10 (lasrups op een plaat): [`Lassen.md`](Lassen.md) §9.5.

Valkuilen:
- De naam vóór de `:` is de **Mecway-materiaalnaam** (exact); een onbekende naam geeft
  een ERROR met de bekende namen.
- `ALPHA` is de gemiddelde (secans) coëfficiënt vanaf `T_ALPHA` (standaard de
  referentietemperatuur), niet de momentane.
- `H` is Mecway's *tangent modulus* (plastische modulus); `ET` de helling in totale rek
  (Code-Aster `D_SIGM_EPSI`); één van beide.
- Zet bij lassen altijd `TC_CUT` (de thermische rek bevriest boven de smelttemperatuur).

### Voorbeeld 18 – Adaptieve verfijning per model (`#ASTER-OPTIE`)

Doel: in één model de verfijningslus aanzetten met een lager doel voor een
piekspanning, zonder de pagina *Statisch* te veranderen (uitleg:
[`Foutschatter.md`](Foutschatter.md) §6). Mecway: *Static*, volume-elementen (bij
voorkeur hex20), voorwaarden en lasten op vlakselecties. CCX > Custom model definition:

```
** ASTER-OPTIE adapt_refine = ja
** ASTER-OPTIE adapt_target_error = 1.5
** ASTER-OPTIE adapt_select = fraction
** ASTER-OPTIE adapt_fraction = 0.1
```

Uitkomst (offline nagelopen met `bridge_custom.parse` en `bridge_adapt.adapt_settings`):
de lus staat aan met doel 1,5% en verfijnt per lus de 10% elementen met de grootste fout;
de andere instellingen (max. 5 lussen, 200 000 elementen) blijven die van de pagina.
Zonder `adapt_select`/`adapt_fraction` kiest de lus met Dörfler 0,5 (verificatie AD-02).

### Voorbeeld 19 – Vermoeiing: blokkenspectrum op een statische run (`#ASTER-WOHLER`, `#ASTER-BLOK`)

Doel: schade en levensduur van een staaf met een twee-niveau-spectrum, Basquin-curve
en Goodman-correctie (uitleg: [`Vermoeiing.md`](Vermoeiing.md)). Mecway: *Static 3D*
met de last van "één eenheid" (hier een traction van 100 MPa) en materiaal `Staal`.
CCX > Custom model definition:

```
** ASTER-WOHLER Staal: Sf = 900 MPa, b = -0.1, Su = 600 MPa, correctie = GOODMAN
** ASTER-VERMOEIING herhalingen = 5
** ASTER-BLOK 1.5, 0.5, 1e4
** ASTER-BLOK 0.8, 1.0, 2e5
```

Per herhaling 10⁴ cycli 100 ± 150 MPa (amplitude 1,5 en gemiddelde 0,5 × de statische
spanning) en 2·10⁵ cycli 100 ± 80 MPa; het spectrum treedt 5 keer op. In de `.comm`
na `CALC_CHAMP`:

```
import aster_fatigue
_bridge_vermoeiing = aster_fatigue.compute(
    res, r'...\model.liml', r'...\model_<run>_vermoeiing.csv',
    [{'material': 'Staal', 'form': 'basquin', 'Sf': 900000000.0, 'b': -0.1,
      'Su': 600000000.0, 'correction': 'GOODMAN'}],
    {'stress': 'VMIS_SG', 'counting': 'RAINFLOW', 'repeats': 5.0, ...},
    blocks=[(1.5, 0.5, 10000.0), (0.8, 1.0, 200000.0)], signal=None, shells=None)
```

Uitkomst (verificatie VM-02b): D = 4,329·10⁻³ en `life` 1155 herhalingen in elke knoop,
gelijk aan de handberekening (Goodman S_eq = S_a/(1 − S_m/S_u), Basquin, Miner × 5)
binnen 10⁻⁶; statusvak: "Vermoeiing: grootste schade D = 0.004329 ...".

### Voorbeeld 20 – Vermoeiing: het verloop van een niet-lineaire run (`#ASTER-WOHLER`)

Doel: rainflow op de spanningsgeschiedenis van elke knoop, met een Wöhler-tabel (hier
de lineaire curve van Code-Aster-testcase szlz105a, N = 1000 − 100 S met S in MPa).
Mecway: *Nonlinear static 3D*, een traction met een tijdstabel 0, 3, 1, 4, 2, 4, 1, 2,
−3 MPa op t = 0 … 8 s. CCX > Custom model definition:

```
** ASTER-WOHLER Staal: S = [0, 10] MPa, N = [1000, 0], INTERPOL = LIN
```

Geen `#ASTER-BLOK`/`-SIGNAAL`: alle tijdstappen van `STAT_NON_LINE` zijn het signaal.
Uitkomst (verificatie VM-04): D = 4,8133·10⁻³ (szlz105a: `VALE_REFE` 4,8133·10⁻³),
gelijk aan `CALC_FATIGUE CUMUL_DOMMAGE` op hetzelfde resultaat (10⁻⁶); de cyclustabel
`<model>_<run>_vermoeiing.csv` heeft 4 cycli (bereiken 7, 2, 2 en 1 MPa, de laatste
twee bij gemiddelde 3 en 1,5 MPa).

### Voorbeeld 25 – Metallurgie met een eigen TRC-diagram (`#ASTER-METALLURGIE`)

Doel: fasen (ferriet .. martensiet) en hardheid na een afkoeling, voor een staal
waarvan je zelf het TRC-diagram hebt (zonder eigen diagram: `staal=16MND5`,
[`Lassen.md`](Lassen.md) §10.3). Mecway: *Thermal transient* (T31) met de afkoeling
(of een lasbron, voorbeeld 13). CCX > Custom model definition: de `DEFI_TRC` als
`#ASTER`-code (per afkoelgeschiedenis: afkoelsnelheid bij 700 °C [°C/s], korrelgrootte,
zes coëfficiënten en daarna viertallen Z_ferriet, Z_perliet, Z_bainiet, T [°C]; syntax
zoals de testcases hsnv101a en mtlp103a) en de regel `#ASTER-METALLURGIE` met de
`META_ACIER`-waarden (verificatie MT-08):

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

De bridge zet `META_ACIER` dan in een eigen materiaal (de `DEFI_TRC` staat in de `.comm`
na de thermische materialen) en rekent na de thermische solve:

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

Uitkomst (MT-08, afkoelen 900 → 20 °C met 100 °C/s): martensiet = 1 − exp(−0,011·(300
− T)) tot 3·10⁻⁸; alarm `RESULT1_39` (ander materiaal dan in het resultaat) is hier
bedoeld.

Valkuilen:
- `ALPHA` is **negatief** (Code-Aster: Z_M = 1 − exp(ALPHA·(Ms − T))); een positieve
  waarde geeft een ERROR.
- Met `trc=` zijn `AR3`, `ALPHA`, `MS0`, `AC1`, `AC3`, `TAUX_1` en `TAUX_3` verplicht
  (°C en s); de naam vóór de `:` is de Mecway-materiaalnaam.
- Bij lassen `TAUX_1`/`TAUX_3` klein (0,001 s), anders loopt de austenitisering achter
  ([`Lassen.md`](Lassen.md) §10.5).

### Voorbeeld 23 – Toevoegmateriaal dat geboren wordt, twee lagen (`#ASTER-LASBRON geboorte=`)

Doel: een rups in twee lagen waarvan het toevoegmateriaal pas meedoet als de bron er
langs komt (warmteopslag, stijfheid en spanning pas na de geboorte; uitleg:
[`Lassen.md`](Lassen.md) §11). Mecway: *Thermal transient* (T31) met een
begintemperatuur; elke laag een elementselectie of component `LASNAAD_1`,
`LASNAAD_2` die knopen deelt met het basismateriaal; voor de restspanning ook Thermal
stress, opleggingen en `#ASTER-MATERIAAL` (voorbeeld 17). CCX > Custom model
definition:

```
** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.0015), richting=(1, 0, 0), lengte=0.02
** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetrie=1, geboorte=<<LASNAAD_1>>
** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.003), richting=(1, 0, 0), lengte=0.02, t0=6
** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetrie=1, geboorte=<<LASNAAD_2>>
```

De bridge zet in de `.comm` (thermisch, `THER_LINEAIRE`):

```
gb_tb = CREA_CHAMP(TYPE_CHAM='CART_NEUT_R', OPERATION='AFFE', MAILLAGE=mesh, AFFE=(
    _F(GROUP_MA='TH2', NOM_CMP='X1', VALE=0.1), ...))     # midden van de geboortestap
MTH1_GB_L = FORMULE(VALE='L if INST > NEUT1 else L * Q * Q', NOM_PARA=('INST', 'NEUT1'), L=30.0, Q=0.0001)
MTH1_GB_C = FORMULE(VALE='C if INST > NEUT1 else C * Q', NOM_PARA=('INST', 'NEUT1'), C=4680000.0, Q=0.0001)
MTH1_GB = DEFI_MATERIAU(THER_FO=_F(LAMBDA=MTH1_GB_L, RHO_CP=MTH1_GB_C))
fieldmat = AFFE_MATERIAU(..., AFFE=(..., _F(GROUP_MA='TH..', MATER=MTH1_GB)),
    AFFE_VARC=_F(GROUP_MA='TH..', NOM_VARC='NEUT1', CHAM_GD=gb_tb))
LBS1 = FORMULE(VALE='(_lb_goldak(X, Y, Z, INST, _LB1) + _lb_goldak(X, Y, Z, INST, _LB2)) '
               'if _lb_born(X, Y, Z, INST, _GB2) else 0.0', ...)
lasbron = AFFE_CHAR_THER_F(MODELE=model, SOURCE=(_F(GROUP_MA='TH..', SOUR=LBS1), ...))
```

en mechanisch een lus `STAT_NON_LINE` per geboortestap (stil materiaal `MAT_1_Q` met E ×
1e-4; bij de geboorte het gewone materiaal en spanning/interne variabelen op nul via
`ETAT_INIT`).

Uitkomst (verificatie WE-13, halve plaat 30 × 8 × 4 mm met twee lagen, 1 140 hex8, 150
stappen): `DIAGNOSTIC JOB : OK`, laag 2 zonder spanning en op de begintemperatuur tot
zijn geboorte, laag 1 opnieuw opgewarmd door laag 2, restspanning in evenwicht met trek
in de rups. WE-11 (rups in twee stukken): energie van het levende volume binnen 0,8%.

Valkuilen:
- Elke laag een eigen selectie (`geboorte=<<..>>`); `geboorte=ja` alleen bij één bron.
- Met `geboorte` werkt de bron op alle elementen bij de baan (ook het basismateriaal),
  niet alleen op `LASNAAD_`.
- Mecway's eigen solver kent geen geboorte; vergelijken met Mecway kan alleen zonder.

### Voorbeeld 29 – Breukmechanica met XFEM: een scheur zonder mesh (`#ASTER-XFEM`)

Doel: K en G langs een scheur die niet in het mesh zit (uitleg:
[`Breukmechanica.md`](Breukmechanica.md) §7). Mecway: *Static 3D*, een ongescheurd
blok van volume-elementen, fijn (h ≈ a/20) rond de plek van het front. CCX > Custom
model definition (verificatie BR-10, cirkelvormige scheur met straal 20 mm in het
vlak z = 0):

```
** ASTER-XFEM vorm=CIRKEL, centrum=(0, 0, 0), r=20 mm, normaal=(0, 0, 1), naam=penny
```

Andere vormen (elke regel met `vorm=` is een nieuwe scheur; een regel zonder `vorm=`
gaat verder met de vorige):

```
** ASTER-XFEM vorm=HALFVLAK, front=(0.05, 0, 0), normaal=(0, 1, 0),
** ASTER-XFEM     richting=(1, 0, 0)
** ASTER-XFEM vorm=RECHTHOEK, centrum=(0, 0, 0.025), a=0.05, b=0.05,
** ASTER-XFEM     vect_x=(1, 0, 0), vect_y=(0, 0, 1)
** ASTER-XFEM vorm=ELLIPSE, centrum=(0, 0, 0), a=2, b=2, vect_x=(1, 0, 0),
** ASTER-XFEM     vect_y=(0, 1, 0), glad=LAGRANGE, punten=20
```

In de `.comm` (vóór de lasten; `model_sain` is het model van de bridge):

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

en na de export per front `CALC_G_XFEM` en `POST_K1_K2_K3` (Breukmechanica.md
§7.3). Uitkomst (BR-10): K_I uit `POST_K1_K2_K3` 0,1622 MPa·√m (analytisch 2σ√(a/π)
= 0,1596: +1,6 %), uit `CALC_G_XFEM` +5,3 % (geen krommingscorrectie, WARNING); de
laatste ELLIPSE-regel met `#ASTER-OPTIE fracture_r_inf/_sup` is forma07b (BR-11,
gelijk aan de testcase); `DIAGNOSTIC JOB : <A>_ALARM` (`QUALITY1_1`: XFEM is in
Code-Aster niet gekwalificeerd voor veiligheidsstudies, en `XFEM_63`: kleine
verschuiving van de levelset; beide onschuldig,
[`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md#xfem_63-quality1_1-modele1_63--xfem-alarmen)).

Zonder `#ASTER-XFEM`-regel: een scheur met een vrije vorm op een knooplaag is een
vlakselectie `XFEM_<naam>` met de vlakken in het scheurvlak (DEFI_FISS
`GROUP_MA_FISS`/`GROUP_MA_FOND`, Breukmechanica.md §7.8, BR-13). Met de instelling
*MED-bestand voor ParaView* schrijft de bridge ook `<model>_<run-id>_xfem.rmed`, het
mesh dat de scheur volgt met `DEPL`, `SIGM_NOEU` en `SIEQ_NOEU` (§7.9, BR-14).

### Voorbeeld 35 – Vermoeiing multiaxiaal: Dang Van op een statische run (`#ASTER-VERMOEIING criterium`)

Doel: schade met het kritiekvlakcriterium van Dang Van bij trek + afschuiving
(uitleg: [`Vermoeiing.md`](Vermoeiing.md) §1.7). Mecway: *Static 3D* met de last van
"één eenheid" (hier σ_xx = 120 MPa en τ_xy = 80 MPa als traction op de vlakken) en
materiaal `Staal`. CCX > Custom model definition:

```
** ASTER-WOHLER Staal: S = [100, 150, 250, 400] MPa, N = [1e7, 2e6, 2e5, 1e4]
** ASTER-VERMOEIING criterium = DANG_VAN, a = 0.3, b = 110 MPa, c = 1.5
** ASTER-SIGNAAL 0, 1, 0, -1, 0
```

De bridge bouwt uit de statische spanning en rek een resultaat met vijf tijdstappen
(signaal × de statische toestand) en laat Code-Aster het kritieke vlak zoeken. In de
`.comm` na `CALC_CHAMP` (ingekort):

```
res = CALC_CHAMP(reuse=res, RESULTAT=res, GROUP_MA=('Kubus', ), DEFORMATION=('EPSI_NOEU', ))
_FW1 = DEFI_FONCTION(NOM_PARA='SIGM', INTERPOL='LOG', PROL_GAUCHE='EXCLU', PROL_DROITE='CONSTANT', VALE=(...))
_FM1 = DEFI_MATERIAU(ELAS=_F(E=210000000000.0, NU=0.3), FATIGUE=_F(WOHLER=_FW1),
                     CISA_PLAN_CRIT=_F(CRITERE='DANG_VAN_MODI_AC', D_VAN_A=0.3, D_VAN_B=110000000.0, COEF_CISA_TRAC=1.5))
_FCM = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=(_F(GROUP_MA=('Kubus', ), MATER=_FM1), ))
...                                   # _fat_resu: CREA_RESU met SIGM_NOEU en EPSI_NOEU x factor
_FRES = [(_fat_resu([0.0, 1.0, 0.0, -1.0, 0.0]), 1.0)]
_FCHAM = [(CALC_FATIGUE(TYPE_CALCUL='FATIGUE_MULTI', OPTION='DOMA_NOEUD', TYPE_CHARGE='PERIODIQUE',
                        RESULTAT=r_, CHAM_MATER=_FCM, MAILLAGE=mesh, GROUP_MA=('Kubus', ),
                        CRITERE='DANG_VAN_MODI_AC', METHODE='CERCLE_EXACT'), n_) for r_, n_ in _FRES]
_bridge_vermoeiing = aster_fatigue.compute_multi(_FCHAM, ...)
```

Uitkomst (verificatie VM-09a): `fatigue_eq` = 168,0 MPa = 1,5 · (100 + 0,3 · 40) (de
grootste schuifspanning R = √(60² + 80²) = 100 MPa, P_max = 120/3 = 40 MPa),
`fatigue_ratio` = 112/110 = 1,018 (net boven de vermoeiingsgrens van het criterium),
D = 8,333·10⁻⁷ per herhaling (N(168 MPa) uit de tabel), alles binnen 10⁻⁵ van de
handberekening. Met `belasting = NIET_PERIODIEK` telt Code-Aster zelf de cycli op het
kritieke vlak (rainflow); met `#ASTER-BLOK` is elk blok een eigen cyclus.

### Voorbeeld 36 – Vermoeiing: rek-levensduur (Manson-Coffin) bij plasticiteit

Doel: laag-cyclische vermoeiing van een staaf met een opgelegde verlenging ±0,6 mm
op 100 mm (ε_a = 0,006) en een bilineair plastisch materiaal (vloeigrens 250 MPa).
Mecway: *Nonlinear static 3D*, opgelegde verplaatsing met een tijdstabel 0, +0,6, −0,6,
0 mm op t = 0, 1, 2, 3 s (stap 0,25 s); op de pagina Niet-lineair *Vervorming* =
`PETIT` (zie [`Vermoeiing.md`](Vermoeiing.md) §1.9). CCX > Custom model definition:

```
** ASTER-WOHLER Staal: Sf = 900 MPa, b = -0.09, ef = 0.3, c = -0.55
```

(`#ASTER-VERMOEIING rek = PRIN` is de standaard: de hoofdrek met de grootste absolute
waarde, hier de lengterek.) In de `.comm` na `CALC_CHAMP`:

```
res = CALC_CHAMP(reuse=res, RESULTAT=res, GROUP_MA=('Staaf', ), DEFORMATION=('EPSI_NOEU', ))
_bridge_vermoeiing = aster_fatigue.compute(
    res, r'...\model.liml', r'...\model_<run>_vermoeiing.csv',
    [{'material': 'Staal', 'form': 'strain', 'Sf': 900000000.0, 'b': -0.09, 'ef': 0.3, 'c': -0.55,
      'correction': 'GEEN', 'E': 210000000000.0}],
    {'stress': 'VMIS_SG', 'counting': 'RAINFLOW', 'repeats': 1.0, 'strain': 'PRIN', ...},
    blocks=None, signal=None, shells=None)
```

E komt uit het Mecway-materiaal (210 GPa). Uitkomst (verificatie VM-11a): de
cyclustabel heeft één cyclus met rekamplitude 0,006000; N = 1347 uit
0,006 = 900/210000 · (2N)^−0,09 + 0,3 · (2N)^−0,55 en D = 7,426·10⁻⁴ per herhaling,
binnen 2·10⁻⁹ van de handberekening. Schalen werken zonder extra regel: een
`#ASTER-WOHLER` voor het plaatmateriaal geeft `damage_top` en `damage_bottom` (VM-10).

## 6. Overzicht van de controle

Doorgerekend op 06-10-2026 met de bridge (code van commit ac20b66; de rijen *Modaal*,
*Knik* met `#ASTER-EXCIT` in de matrices met commit 41bcf1e) en Code-Aster 17.4.0,
offline: `.liml` met de regels in het genoemde veld → `bridge_from_liml`,
`bridge_mesh`, `bridge_to_aster` → `run_aster` → `bridge_run_aster.aster_mess_errors`.

Opnieuw nagelopen op 07-10-2026 (integrale controle S11, code van commit 8742df0): de
regels van §5 letterlijk uit deze tekst, in de verificatiemodellen die bij elk voorbeeld
staan, of (voorbeelden 1 tot 9) in de modellen A, C, S en R. De voorbeelden 1 tot 8
zijn daarna (07-10-2026, code van commit bfb1e8e plus de meldingen van stap S12) opnieuw
doorgerekend in de modellen A, C en S van `TestFiles/Voorbeelden/`
(`maak_voorbeelden.py --run`); de getallen in §5 en in deze tabel komen uit die runs.
Model R (voorbeeld 9) staat niet in de repository. Code-Aster
zonder `<F>` (en, waar het model hetzelfde is, met de uitkomsten hierboven) voor de voorbeelden 1 (*Statisch*,
*Niet-lineair statisch*, *Dynamisch (impliciet)*, *Modaal*, *Knik*), 2 tot 17, 19,
20, 23, 25, 27, 29, 35 en 36, en voor `#ASTER-BEZWIJKEN`
(`TestFiles/BezwijkenTrekstaaf.liml`); voorbeeld 18 offline. Voorbeeld 17 en 23 rekenen
in WE-09 en WE-13 zonder fout, maar met andere waarden dan die verificaties (die hebben
eigen regels). De Engelse sleutels van de Engelse versie (`direction`, `symmetry`,
`birth`, `shape=CIRCLE`, `correction`, `repeats`, `criterion`, ...) geven dezelfde
`.comm`. De foutmeldingen in de laatste kolom zijn met een fout geschreven regel
opgewekt.

| # | Voorbeeld | Veld | Analyse(s) | Uitkomst |
|---|---|---|---|---|
| 1 | `LIAISON_ELEM` 3D_POU | OpenRadioss, CCX (beide velden) | Statisch, Niet-lineair statisch, Dynamisch (impliciet) | OK |
| 1 | idem, zonder `#ASTER-EXCIT` | OpenRadioss | Statisch / Niet-lineair statisch | `FACTOR_11` (model A, `solver_nprec` 8, 08-10-2026; met -1 `FACTOR_57`) / `MECANONLINE9_4` (verwacht) |
| 1 | idem | OpenRadioss | Modaal, Knik | OK: Modaal f1 = f2 = 2855,4 Hz (paar, Y/Z); Knik ±363,5 en ±993,3 (model A) |
| 1 | idem, star blok (model A, blok E = 2,1·10¹⁸ Pa) | OpenRadioss | Modaal | f1 = f2 = 2894,35 Hz; analytisch 2894,3 Hz (ingeklemde buis 8/6 mm, L = 50 mm, 5 balkelementen) |
| 3, 4 | `FORCE_NODALE` + `DDL_IMPO` / `AFFE_CHAR_MECA_F` in `#ASTER-EXCIT` | Mystran + OpenRadioss / OpenRadioss | Modaal, Knik | OK (de run loopt; de lasten staan ook in `CHARGE` van `ASSEMBLAGE`) |
| 2 | `LIAISON_MAIL` COQUE_MASSIF | Mystran | Statisch, Niet-lineair statisch | OK (0,00897 mm, model S) |
| 3 | `FORCE_NODALE` + `DDL_IMPO` | Mystran + OpenRadioss | Statisch, Niet-lineair statisch | OK |
| 4 | `AFFE_CHAR_MECA_F` + `DEFI_FONCTION` | OpenRadioss (beide velden) | Niet-lineair statisch (Statisch: last 0) | OK |
| 5 | penalty + `ALGO_RESO_GEOM` | OpenRadioss | Niet-lineair statisch met contact | OK (42,36 kN, model C; zonder 47,41 kN) |
| 5 | idem met *Contactmethode* = PENALISATION | OpenRadioss | idem | `SyntaxError` (verwacht, §4) |
| 6 | `CONTACT_INIT`, `POINT_FIXE`, `#ASTER-OPTIE` | OpenRadioss | Niet-lineair statisch met contact | OK; onbekende sleutel geeft ERROR |
| 7 | reactiekracht, `POST_RELEVE_T` + `IMPR_TABLE` | OpenRadioss | Niet-lineair statisch; Statisch met `NUME_ORDRE=1` | OK |
| 8 | `EXTREMA` van `SIEQ_NOEU` | OpenRadioss | Statisch, Niet-lineair statisch | OK |
| 9 | starre rotatie 90 graden, `FORMULE` + `DDL_IMPO` | CCX | Niet-lineair statisch, GROT_GDEP | OK (exact) |
| 10 | `#ASTER-OPTIE` `crit_stab`, `imperfection_*` (doorgerekend 06-10-2026, stap S10c) | CCX | Niet-lineair statisch | OK (gelijk aan NK-03) |
| 11 | `#ASTER-SPECTRE` met `DEFI_NAPPE` en `#ASTER-OPTIE` (doorgerekend 07-10-2026, stap S10e) | CCX | Responsspectrum | OK (gelijk aan sdld25a, SP-01); een fout geschreven regel (`#ASTER-SPECTRE Q = x`) geeft een ERROR |
| 12 | `#ASTER-BRON` met fase, `#ASTER-OPTIE harm_freq_list` (doorgerekend 07-10-2026, stap S3a) | CCX | Akoestiek (harmonisch) | OK (verificatie AH-08) |
| 13 | `#ASTER-LASBRON` (doorgerekend 07-10-2026, stap S4a) | CCX | Thermisch transient | OK (WE-02; ook een geknikt `pad`, `groep`, `LASNAAD_` en de foutmeldingen van [`Lassen.md`](Lassen.md) §8) |
| 14 | `#ASTER-OPTIE vibro_freq_min` (doorgerekend 07-10-2026, stap S3b) | CCX | Vibro-akoestiek (modes) | OK (verificatie VA-05c) |
| 27 | `#ASTER-BRON` met een druk (invallende golf) en met een snelheid, `#ASTER-OPTIE harm_freq_list` (doorgerekend 07-10-2026, stap S3c) | CCX | Vibro-akoestiek (harmonisch) | OK (verificatie VH-07, VH-08); een regel zonder getal geeft een ERROR |
| 15 | `#ASTER-FASE`, tabel als functie van de frequentie, `#ASTER-OPTIE harm_freq_list` (doorgerekend 07-10-2026, stap S10h) | CCX | Harmonische respons | OK (verificatie HR-04); onbekende selectie of regel zonder `=` geeft een ERROR |
| 16 | `#ASTER-OPTIE fracture_r_inf`/`fracture_r_sup` met `SCHEUR_`-selecties (doorgerekend 07-10-2026, stap S6a) | CCX | Statisch | OK (verificatie BR-04) |
| 17 | `#ASTER-MATERIAAL` met `#ASTER-LASBRON` (doorgerekend 07-10-2026, stap S4b) | CCX | Thermisch transient met Thermal stress (keten thermisch → mechanisch) | OK (WE-09, WE-10; een onbekende sleutel of materiaalnaam en lijsten van ongelijke lengte geven een ERROR) |
| 19 | `#ASTER-WOHLER` (Basquin, Goodman), `#ASTER-VERMOEIING`, `#ASTER-BLOK` (doorgerekend 07-10-2026, stap S8) | CCX | Statisch | OK (verificatie VM-02b) |
| 20 | `#ASTER-WOHLER` (tabel, `INTERPOL = LIN`) met het verloop van de run (doorgerekend 07-10-2026, stap S8) | CCX | Niet-lineair statisch | OK (verificatie VM-04, szlz105a) |
| 23 | `#ASTER-LASBRON` met `geboorte=` (doorgerekend 07-10-2026, stap S4c) | CCX | Thermisch transient, ook met Thermal stress (keten) | OK (WE-11, WE-11b, WE-12, WE-13; `geboorte=ja` bij twee bronnen en een selectie zonder `<< >>` geven een ERROR) |
| 25 | `#ASTER-METALLURGIE` met een `DEFI_TRC` in `#ASTER`-code (doorgerekend 07-10-2026, stap S5) | CCX | Thermisch transient | OK (MT-08; ook `staal=16MND5`/`HSNV101A` en `mechanica=ja`, MT-01 .. MT-07; een onbekende dataset, `trc` zonder `META_ACIER`-waarden of `ALPHA` > 0 geven een ERROR) |
| 29 | `#ASTER-XFEM` (CIRKEL, HALFVLAK, RECHTHOEK, ELLIPSE met `glad`/`punten`) en `#ASTER-OPTIE fracture_r_inf`/`_sup` (doorgerekend 07-10-2026, stap S6b) | CCX | Statisch | OK (verificatie BR-07..12; een scheur buiten het model, een onbekende `groep`, R_INF ≥ R_SUP en een onbekende sleutel geven een ERROR) |
| – | `#ASTER-POST` met `EXTREMA` | OpenRadioss | Thermisch, Dynamisch (expliciet) | OK |
| – | `$ ASTER` (spatie), `#ASTER-FOO`, `#ASTER_EXCIT`, onbekende `<<selectie>>` | Mystran, OpenRadioss | Statisch | OK / ERROR in de log zoals beschreven |

## 7. Aannames

- De regels worden in de volgorde van §1 in de `.comm` gezet; de bridge controleert de
  Code-Aster-syntax niet.
- De uitkomsten in §5 gelden voor de genoemde kleine testmodellen; ze tonen dat de
  regels werken, niet dat het mesh convergeert.
- Waar een eis van de U-documentatie niet in de 17.4-catalogus of met een run is
  nagelopen, staat "NIET geverifieerd".

## 8. Bronnen

- EDF R&D (2026a). *code_aster 17.4.0, commandocatalogus*. Installatie
  `code_aster/v2025/17.4/lib/aster/code_aster/Cata/Commands/` (`affe_char_meca.py`,
  `affe_char_meca_f.py`, `defi_contact.py`, `defi_fonction.py`, `formule.py`,
  `post_releve_t.py`, `impr_table.py`, `crea_champ.py`, `defi_group.py`).
- EDF R&D (2026b). *code_aster 17.4.0, berichtencatalogus*. Installatie
  `code_aster/v2025/17.4/lib/aster/code_aster/Messages/`.
- EDF R&D (2021a). *Opérateur AFFE_CHAR_MECA*. Code_Aster-documentatie U4.44.01. Lokale
  PDF in `Code_Aster_documentation/important documents/` (aangemaakt 17-12-2021; ouder
  dan 17.4).
- EDF R&D (2021b). *Opérateur DEFI_CONTACT*. Code_Aster-documentatie U4.44.11. Lokale
  PDF (aangemaakt 18-12-2021; ouder dan 17.4).
- EDF R&D (2021c). *Opérateur POST_RELEVE_T*. Code_Aster-documentatie U4.81.21. Lokale
  PDF (aangemaakt 18-12-2021; ouder dan 17.4).
- EDF R&D (2021d). *Opérateur ASSEMBLAGE*. Code_Aster-documentatie U4.61.21. Versie
  "default", 03-11-2021 (lokale kopie; ouder dan 17.4).
- Mecway (2026). *Mecway Finite Element Analysis – Manual*, versie 33.
  `C:\Program Files\Mecway\manual.pdf`.
