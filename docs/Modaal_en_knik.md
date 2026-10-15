# Modale analyse en lineaire knik

*English version: [Modal_and_buckling.md](en/Modal_and_buckling.md)*

De bridge rekent twee eigenwaardeproblemen met Code-Aster `CALC_MODES` (EDF R&D,
U4.52.02):

| Mecway-analyse | Bridge-analyse (pagina) | Wat Code-Aster rekent | Resultaat in Mecway |
|---|---|---|---|
| Frequency (V30) | `modal_3d` (Modaal) | stijfheid K en massa M (`ASSEMBLAGE`), `CALC_MODES`; met belastingen eerst `MECA_STATIQUE` en dan K + K_g (voorspanning, §2.5) | per mode de eigenfrequentie (Hz) en de trillingsvorm (als optie de spanningen, §1.4) |
| Buckling (B30) | `buckling_3d` (Knik) | `MECA_STATIQUE` met de belastingen, geometrische stijfheid Kg uit de spanningen (`RIGI_GEOM`), `CALC_MODES TYPE_RESU='MODE_FLAMB'` | per mode de kniklastfactor en de knikvorm |

De resultaten staan in Mecway zoals bij Mecway's eigen oplossing: onder *Solution*
een lijst *Mode 1, Mode 2, ...* met de frequentie of de kniklastfactor
(hetzelfde `<mode>`-formaat in de `.liml`). Algemene werking van de bridge:
[`Handleiding.md`](Handleiding.md). Niet-lineaire knik (stabiliteit per stap met
`CRIT_STAB`, knikvorm als imperfectie) in een niet-lineaire statische analyse: §5.
Modes met demping (gedempte frequentie en dempingsverhouding per mode, als optie):
§6. Modes van een cyclisch symmetrische constructie uit één sector (Mecway's *Cyclic
symmetry*): §7. De respons in de tijd op deze modes (Mecway's *Dynamic Response* met *Mode
superposition*): [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md).

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Analysetype.** Kies in de analyse-instellingen *Frequency* (modaal) of
   *Buckling* (knik).
2. **Aantal modes** (*Number of modes*). De bridge rekent precies zoveel modes.
   Ontbreekt het, dan geldt de instelling *Aantal modes (zonder maxmode in Mecway)* op
   de pagina Modaal of Knik. Tel bij een los (niet opgelegd) model de starre modes
   mee: tot 6 modes met ~0 Hz.
3. **Shift point** (alleen knik in Mecway). Dat is een instelling van Mecway's eigen
   oplosser (Mecway Ltd., 2026, §6.6), geen zoekcentrum: Mecway's BucklingPlate met
   shift 1000 gaf in Mecway gewoon de kleinste factoren (7…12). De bridge gebruikt hem
   niet (INFO in de log) en zoekt, zoals Mecway, altijd de kleinste
   kniklastfactoren (§2.2).
4. **Materiaal.**
   - Modaal: geef elk materiaal een **dichtheid** (*Density*). Zonder dichtheid is er
     geen massa en meldt de log een WARNING. Puntmassa's (*Mass*, *Rotational
     inertia*) tellen mee.
   - Knik: dichtheid is alleen nodig als zwaartekracht een van de belastingen is.
5. **Opleggingen.** Fixed, pinned, displacement, node rotation, symmetry,
   frictionless, koppelingen en veren tellen mee zoals in de statische analyse. Bij
   modaal telt alleen welke vrijheidsgraden vastliggen, niet de waarde van een
   opgelegde verplaatsing. Met voorspanning (belastingen, punt 6) moet die waarde 0
   zijn: Mecway rekent dat niet (Mecway Ltd., 2026, §6.3) en de bridge stopt met een
   ERROR (§4).
   - Modaal zonder enige oplegging (vrij-vrij): de bridge rekent het toch (§3.2);
     de eerste modes zijn dan starre bewegingen met ~0 Hz.
   - Een mechanisme in een verder opgelegd model (bijv. een balk die alleen
     scharnierend vastzit, een los onderdeel): Code-Aster stopt met `ALGELINE3_81`;
     oplossing in §4 (KNOWN_BUGS 48).
   - Knik zonder opleggingen kan niet (de statische berekening is singulier): ERROR.
   - Verbindingen uit `#ASTER`-code (`LIAISON_ELEM`, `LIAISON_MAIL`, `DDL_IMPO`, ...)
     tellen mee als de last in `#ASTER-EXCIT` staat (§2.1, §2.2;
     [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §2).
6. **Belastingen.**
   - Modaal: met belastingen rekent de bridge, zoals Mecway, een **voorgespannen**
     modale analyse (*stress stiffening*, Mecway Ltd., 2026, §6.3): eerst lineair
     statisch onder alle belastingen, dan de modes met de stijfheid plus de
     geometrische stijfheid uit dat spanningsveld (§2.5). **Trek verhoogt de
     frequenties, druk verlaagt ze**; druk boven de kniklast geeft een negatieve
     frequentie (WARNING). Alle belastingen tellen mee (krachten, druk,
     zwaartekracht, centrifugaalkracht, thermische rek met *Thermal stress*). Een
     centrifugaalkracht geeft ook *spin softening* (§2.5). Wil je de onbelaste
     frequenties: zet *Voorspanning door belastingen* uit (pagina Modaal); de
     belastingen vervallen dan met een WARNING.
   - Knik: de belastingen bepalen het spanningsveld en daarmee het knikpatroon. Alle
     belastingen tellen mee (krachten, druk, zwaartekracht, ...). De
     **kniklastfactor is het veelvoud van alle aangebrachte belastingen samen** waarbij
     de constructie knikt. Breng daarom een referentielast aan (bijv. 1 kN of de
     ontwerplast); bij een eenheidslast is de factor direct de kniklast. Een constante
     last (zoals het eigen gewicht) wordt ook vermenigvuldigd; om die vast te houden
     pas je de variabele last aan tot de factor 1 is (Mecway Ltd., 2026, §6.6).
   - Een belasting met een tijdstabel krijgt de laatste waarde van de tabel (WARNING).

### 1.2 In het hoofdvenster van de bridge

1. **Actieve analyse (auto = volgens Mecway):** `auto` kiest bij V30 `modal_3d` en bij
   B30 `buckling_3d`; of kies de analyse zelf.
2. **Resultaten naar Mecway** moet `liml` zijn (pagina Algemeen); met `tabel` stopt
   de bridge vóór de run met een melding.
3. Pagina **Modaal** of **Knik** (alleen aanpassen als dat nodig is):

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Aantal modes (zonder maxmode in Mecway) | 10 (modaal), 4 (knik) | alleen als het Mecway-model geen *Number of modes* heeft |
| Zoekfrequentie [Hz] (0 = laagste modes; alleen modaal) | 0 | > 0: de modes het dichtst bij deze frequentie (`OPTION='CENTRE'`; dichtst bij gemeten in ω², niet in Hz), bijv. rond een excitatiefrequentie. < 0, bijv. -10 x de verwachte eerste elastische frequentie: ook de laagste modes, maar rekenbaar met een mechanisme dat massa heeft (§4). 0 zonder opleggingen: de bridge verschuift zelf (§3.2) |
| Normering trillings-/knikvormen (NORM_MODE) | `MASS_GENE` (modaal), `RIGI_GENE` (knik) | zelden; zie §2.3. Alleen de vorm heeft betekenis. `MASS_GENE` bij knik wordt `RIGI_GENE` (WARNING: knik heeft geen massamatrix) |
| Controle modes (VERI_MODE SEUIL) | 1e-6 | groter (bijv. 1e-4) als de log `ALGELINE5_15` meldt bij een grof of slecht geconditioneerd model |
| Voorspanning door belastingen (stress stiffening; alleen modaal) | aan | uit om de onbelaste frequenties te zien, of als een opgelegde verplaatsing ≠ 0 alleen als oplegging moet tellen (§2.5) |
| Complexe modes met demping (Rayleigh, dempers; alleen modaal) | uit | aan voor de gedempte frequentie en de dempingsverhouding ζ per mode bij Rayleigh-demping of dempers (*Damper*); §6. Uit = zoals Mecway: de demping telt niet mee |
| Resultaatvelden naar Mecway (alleen modaal) | `displacements` | vink `stresses` en/of `vonmises` aan voor **spanningen per mode** (§1.4): waar een trillingsvorm de grootste spanning geeft, bijv. om een sensor of een vermoeiingsgevoelige plek te kiezen. Andere velden (reacties, ...) worden genegeerd (INFO). Bij knik alleen de vormen |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | grote modellen |

4. De elementkeuzes op de pagina **Elementen** gelden ook hier. Hex8 met `3D` is te
   stijf bij buiging (KNOWN_BUGS 1): frequenties en kniklastfactoren worden te hoog.
   Gebruik `LINE_QUAD` of kwadratische elementen (hex20) in Mecway. Gemeten met de
   bridge (ingeklemde balk 1 x 0,1 x 0,1 m, 20x2x2 hex8, Euler-Bernoulli
   f1 = 83,55 Hz): hex8 `3D` 89,11 Hz (+6,7%), `LINE_QUAD` 83,48 Hz (-0,09%).

### 1.3 Starten en volgen

Klik *Starten*. Wat je ziet:

- **Log en statusvak** na afloop: per mode de frequentie met de **effectieve massa**
  per translatierichting (X/Y/Z, als % van de totale massa) en per rotatie (RX/RY/RZ:
  om de globale assen door de oorsprong, als % van het traagheidsmoment om die as;
  §1.5) en de som over de modes, of de kniklastfactor per mode. Voorbeeld
  (verificatietest MO-01): `Mode 1: 16.7103 Hz (eff. massa X/Y/Z 0.0/61.3/0.0%,
  RX/RY/RZ 0.0/0.0/97.1%)`. De log geeft ook de totale massa, het zwaartepunt en de
  traagheidsmomenten om de assen door de oorsprong en door het zwaartepunt
  (`INFO: Massa 4.71 kg, zwaartepunt (0.5, 0, 0) m; ...`). Het statusvak toont de
  eerste 20 modes, de log alle. Dezelfde effectieve massa staat per mode ook in Mecway
  (§1.4).
- **Convergentiescherm:** de meldingen en de diagnose; in de statusregel de eerste
  modes (`modes 1: 16.71 Hz, 2: 25.07 Hz, ...`). Bij knik ook de statische
  berekening (lineaire oplosser).
- **WARNING's** die bij modes horen: geen dichtheid, belastingen genegeerd
  (voorspanning uit), vrij-vrij, mode 1 met ~0 Hz (starre beweging of mechanisme),
  negatieve frequentie (druk boven de kniklast), negatieve kniklastfactor, en de
  alarmen van de modecontrole (`ALGELINE5_23`, `ALGELINE2_74`, `ALGELINE5_15`; §4).
- Met *Eerst Mecway-solve ter controle* vergelijkt de log per mode de frequentie of
  factor van Mecway en van Code-Aster (geen CSV: vormen hebben een willekeurig teken).

### 1.4 Resultaten in Mecway bekijken

- Onder *Solution* staan *Mode 1 ... Mode n* met de frequentie (Hz) of de
  kniklastfactor. Klik een mode en kies een veld (*displacement*); met *Animate* zie je
  de beweging.
- Velden: verplaatsingen `displx/y/z` (en `rotx/y/z` bij balken en schalen), bij knik
  ook `displmag`, zoals Mecway's standaardoplossing. Reactiekrachten horen niet bij een
  mode.
- **Spanningen per mode** (alleen modaal, als *Resultaatvelden naar Mecway* `stresses`
  of `vonmises` bevat): `stressxx` ... `stresszx` en `vonmises` (volume-elementen, per
  knoop en per element-knoop), `vonmisesu1/m/b` (schalen, boven-/midden-/ondervlak) en
  `beamsixxmin/max` (balken met RECTANGLE- of CERCLE-doorsnede), dezelfde namen als
  statisch. Mecway rekent ze zelf ook per mode als je ze vóór het oplossen onder
  *Solution* toevoegt (headless nagelopen). **Alleen relatief betekenisvol:** de
  spanning hoort bij de genormeerde vorm (φᵀMφ = 1, eenheid Pa/√kg), dus de waarde
  in Pa zegt niets over een werkelijke trilling; wel waar de spanning het grootst is en
  hoe de spanning over het model verdeeld is. Het teken wisselt met het teken van de
  vorm. Werkelijke spanningen bij een trilling vragen een responsberekening (de
  modale amplitude vermenigvuldigt vorm én spanning;
  [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md)).
- **Effectieve massa per mode (modaal):** onder *Solution* staan ook *modal effective
  mass* (kg voor X/Y/Z, kg·m² voor de rotaties) en *modal effective mass fraction*,
  per mode en per richting `tx`, `ty`, `tz`, `rx`, `ry`, `rz`. Dat zijn Mecway's eigen
  variabelen (`modaleffectivemassty`, `modaleffectivemassfractionty`, ...), in het
  resultaat precies zoals Mecway's eigen modale oplossing ze schrijft (headless
  nagelopen; zie §2.1); Mecway maakt de twee items zelf aan bij het openen. Ze bevatten
  de waarden van de log (§1.3), met 15 cijfers:
  - *modal effective mass*: Γ² = (φᵀMR)² met φ massagenormeerd; hetzelfde begrip als
    in Mecway (Mecway Ltd., 2026, §6.3);
  - *modal effective mass fraction*: **de fractie van Code-Aster**
    (`MASS_EFFE_UN_D*`; rotaties met dezelfde noemer): gedeeld door de **totale**
    massa of het totale traagheidsmoment, inclusief de opgelegde knopen. Mecway's
    eigen solver deelt door de *vrije* massa; de bridge rekent dat niet om (§1.5,
    *Verschil met Mecway in de fractie*). Wil je Mecway's fractie, deel dan *modal
    effective mass* door de vrije massa;
  - daarnaast de **cumulatieve fractie** (som van de fracties van mode 1 tot en met
    deze mode, Code-Aster's noemer) als `cumulativeeffectivemassfractiontx` ...
    `rz`: een eigen naam van de bridge. Mecway bewaart die bij het opslaan (headless
    nagelopen); of Mecway's venster hem als item toont, is NIET geverifieerd. De som
    over alle modes staat in elk geval in de log en het statusvak.

  Een richting zonder waarde (bijv. geen rotaties omdat de eigen controle faalde, §4)
  ontbreekt ook in Mecway. Bij complexe modes (§6) is het de effectieve massa uit het
  reële deel van de vorm. Niet bij knik, akoestische modes, vibro-akoestiek en
  cyclische symmetrie (daar ook niet in de log), en niet bij een respons op modale
  basis (daar staan tijdstappen in Mecway, geen modes).
- **De schaal van een vorm heeft geen fysische betekenis** (Mecway Ltd., 2026, §6.3).
  Een trillingsvorm zegt hoe de knopen ten opzichte van elkaar bewegen, niet hoeveel.
  Normering (zoals Mecway): trillingsvormen met gegeneraliseerde massa 1
  (phi^T M phi = 1; eenheid m/sqrt(kg)), knikvormen met gegeneraliseerde stijfheid 1
  (phi^T K phi = 1). Het teken van een vorm is willekeurig.
- De resultaten blijven ook los bewaard (`<model>_<run-id>_results.xml`) en zijn
  opnieuw in te laden met *Resultaten...* ([Handleiding §5.1](Handleiding.md#51-resultaten-later-opnieuw-inladen-kleine-liml)).

### 1.5 Interpretatie en controles

- **Kniklast = kniklastfactor x aangebrachte belasting.** De eerste (kleinste
  positieve) factor is maatgevend. Een factor < 1 betekent dat de constructie al onder
  de aangebrachte last knikt.
- **Lineaire knik overschat meestal de werkelijke kniklast.** De berekening gaat uit
  van een perfecte constructie zonder imperfecties, excentriciteit, plasticiteit of
  verplaatsingen vóór het knikken (Mecway Ltd., 2026, §6.6; EDF R&D, U2.08.04). Gebruik
  een knockdownfactor volgens de toepasselijke norm, of een niet-lineaire analyse met
  een imperfectie (`nonlin_static_3d`, §5).
- **Modaal met voorspanning:** vergelijk met de onbelaste frequenties (zet
  *Voorspanning door belastingen* uit) om het effect van de last te zien. Een
  frequentie die naar 0 gaat bij toenemende druk wijst op knik; de kniklast zelf
  reken je met een knikanalyse (B30). Een negatieve frequentie betekent dat de
  constructie onder deze last instabiel is (Mecway geeft dan 0 Hz).
- **Modaal:** de effectieve massa laat zien welke modes in een richting meedoen. Voor
  een seismische of responsberekening wordt vaak ~90% effectieve massa per richting
  aangehouden (vuistregel, afhankelijk van de norm; NIET geverifieerd in de bronnen
  hieronder): vraag dan meer modes.
- **Effectieve massa voor de rotaties (RX/RY/RZ)** geldt, zoals bij Mecway, voor een
  starre rotatie om de **globale assen door de oorsprong** (Mecway Ltd., 2026, §6.3;
  nagelopen met Mecway's eigen waarden, §2.1). De fractie is de effectieve massa
  gedeeld door het traagheidsmoment om die as (in de log). Ligt het model ver van de
  oorsprong, dan is een rotatie om de oorsprong vooral een verplaatsing, en lijken de
  RX/RY/RZ-fracties op die van de translaties. Wil je de rotatie om een eigen punt
  (zwaartepunt, voet van een gebouw voor kantelen): leg in Mecway de oorsprong in dat
  punt (Mecway's *Tools → Center of mass* toont het zwaartepunt; de log geeft het
  ook). De som over de modes nadert met genoeg modes 100% (bij een vrij model al met
  de 6 starre modes; zie ook het volgende punt). Bij een ingeklemde uitkragende balk met de oorsprong in de inklemming
  geeft mode 1 al 97% rotatie, tegen 61% translatie (verificatie MO-01, MO-07).
- **Verschil met Mecway in de fractie:** de bridge deelt, zoals Code-Aster bij de
  translaties (`MASS_EFFE_UN_D*`), door de **totale** massa of het totale
  traagheidsmoment, inclusief de opgelegde knopen; Mecway door de *vrije* massa (zonder
  de opgelegde knopen). De effectieve massa zelf (kg, kg·m²) is gelijk (≤ 0,02%), maar
  de fracties van de bridge zijn bij een ingeklemd model iets lager: het ingeklemde
  blok van §2.1 1 x 0,1 x 0,05 m met 10 x 2 x 2 hex20 61,0% (bridge) tegen 62,3%
  (Mecway) in Z. Met een fijner mesh wordt het verschil kleiner. De som over de modes
  blijft bij de bridge daardoor iets onder 100%. Dat geldt ook voor *modal effective
  mass fraction* in Mecway (§1.4): de bridge zet daar Code-Aster's fractie in, niet
  omgerekend; *modal effective mass* zelf is wel direct vergelijkbaar.
- **Eenheden:** controleer de eenheden van dichtheid en E in Mecway. Een dichtheid die
  een factor 1e9 afwijkt, geeft een factor ~3e4 in de frequentie (f ~ 1/sqrt(rho)).
- **Mesh-convergentie:** reken een tweede keer met een fijner mesh; de frequentie of
  factor moet nauwelijks veranderen. Lineaire volume-elementen zijn te stijf bij
  buiging: gebruik kwadratische elementen of `LINE_QUAD` (§1.2).
- **Handberekening** ter controle (formules uit de verificatie,
  [`Verificatie.md`](Verificatie.md)):
  - ingeklemde balk: f1 = 0,5596 / L² · sqrt(EI / (rho A)) (Blevins, 1979);
  - scharnierende balk met axiale kracht P (trek > 0): f_n = f_n0 · sqrt(1 + P /
    Pcr_n), Pcr_n = n² pi² EI / L² (vergelijking van Code-Aster-testcase sdll101a;
    verificatie MP-01/02);
  - Euler-knik: Pcr = pi² EI / (k L)², k = 2 ingeklemd-vrij, k = 1 scharnierend
    (Timoshenko & Gere, 1961);
  - vrij opgelegde vierkante plaat onder eenzijdige druk: sigma_cr = 4 pi² D / (b² t)
    (Timoshenko & Gere, 1961).

  - effectieve massa van een ingeklemde balk (Euler-Bernoulli, oorsprong in de
    inklemming): mode 1 61,3% translatie, 97,1% rotatie; modes 2 en 3 18,8 / 6,5%
    translatie en 2,5 / 0,3% rotatie (verificatie MO-01, MO-07).

  De verificatietests MO-01..05 en BU-01..04 geven met het fijnste mesh een afwijking
  van ten hoogste 0,25% (balkelementen < 0,002%); met grove meshes is de afwijking
  groter (tot 4% bij BU-04 met 8x8 DKT) en neemt ze af met orde 2.

## 2. Hoe de bridge vertaalt

### 2.1 Modaal (`modal_3d`)

`ASSEMBLAGE` (EDF R&D, U4.61.21) maakt de stijfheid (`RIGI_MECA`) en de massa
(`MASS_MECA`: de consistente massamatrix, niet de diagonale `MASS_MECA_DIAG`; met
puntmassa's) met de opleggingen en de `#ASTER-EXCIT`-lasten als `CHARGE`
(Lagrange-multiplicatoren). Verbindingen uit `#ASTER`-code tellen zo mee; krachten in
zo'n last dragen niet bij aan de matrices (`CHARGE` levert alleen de kinematische
condities, U4.61.21). Daarna
`CALC_MODES` met `OPTION='PLUS_PETITE'` en `CALC_FREQ=_F(NMAX_FREQ=n)`, of
`OPTION='CENTRE'` rond de zoekfrequentie. Zonder opleggingen: `CENTRE` rond een kleine
negatieve frequentie (§3.2). Na de berekening leest `aster_results_export.py` de
frequenties en de effectieve massa voor de translaties (`RECU_TABLE`,
`MASS_EFFE_UN_DX/DY/DZ`).

**Effectieve massa voor de rotaties.** Code-Aster kent die niet als parameter
(`RECU_TABLE` met `MASS_EFFE_UN_DRX` geeft `UTILITAI3_5`). `aster_results_export.py`
rekent hem in de job zelf (numpy), met de definitie van Mecway (Mecway Ltd., 2026,
§6.3): participatiefactor Γ = φᵀMR met R de starre rotatie om de globale as door de
oorsprong (u = θ × x, en θ zelf op de rotatievrijheidsgraden van balken, schalen en
discrete elementen), effectieve massa Γ²/(φᵀMφ), fractie = effectieve massa / RᵀMR.
M is de geassembleerde massamatrix (`masse`, `getValuesWithDescription`), de koppeling
vrijheidsgraad → knoop en component komt uit `getNodeAndComponentFromDOF()` (Lagrange-
vrijheidsgraden tellen niet mee). Controle in elke run: dezelfde berekening voor de
translaties moet Code-Aster's `MASS_EFFE_UN_D*` geven (afwijking ≤ 1e-4), anders geeft
de bridge geen rotaties (melding in de `.mess`, §4). Gemeten: ingeklemd blok 1 x 0,1 x
0,05 m vanaf (1, 2, 3) m, 10 x 2 x 2 hex20, mode 1 / 2 rotatie X 100,613 / 219,306
kg·m² tegen Mecway 100,627 / 219,335 kg·m² (−0,014%); traagheidsmoment om de X-as
524,151 kg·m² = m(b² + h²)/12 + m·d² exact.

**Effectieve massa naar Mecway.** Mecway's eigen modale oplossing (interne solver, met
*modal effective mass* en *modal effective mass fraction* onder *Solution*) schrijft
per `<mode>`, vóór de `<nodevariable>`s, per richting `tx` ... `rz` om en om
`<globalvariable name="modaleffectivemassty">57.7394288067102</globalvariable>` en
`<globalvariable name="modaleffectivemassfractionty">0.627861821259979</globalvariable>`
(headless gezien met Mecway 33 op het voorbeeld VibratingCantileverSolid). Een
resultaat met deze regels geeft bij het openen zelf de twee items onder *Solution*
(headless nagelopen: Mecway voegt de `<fieldvariable>`s toe). `aster_results_export.py`
schrijft dezelfde regels in het resultaatbestand: de effectieve massa Γ²/(φᵀMφ) uit de
eigen berekening hierboven (alle 6 richtingen; alleen als de controle op de
translaties slaagt), de fractie van Code-Aster (`MASS_EFFE_UN_D*`) en voor de
rotaties de eigen fractie met dezelfde noemer RᵀMR, plus
`cumulativeeffectivemassfraction*` (eigen naam, §1.4). Verificatie: MO-01 (Mecway-
variabele = waarde in de `.mess` = Euler-Bernoulli) en MO-06 (cumulatief 1 bij een
vrij blok). Met *Resultaatvelden* `stresses`/`vonmises`
volgt `CALC_CHAMP` op het modale resultaat zoals statisch (`SIGM_ELNO`/`SIGM_NOEU`,
`SIEQ_*`, schalen via `POST_CHAMP EXTR_COQUE`, balken `SIPM_ELNO`; geen `REAC_NODA`).

### 2.2 Knik (`buckling_3d`)

`MECA_STATIQUE` met alle lasten (ook de `#ASTER-EXCIT`-lasten) → spanningsveld
`SIEF_ELGA` (`CREA_CHAMP`) → `ASSEMBLAGE` met `RIGI_MECA` en `RIGI_GEOM` (met dat
veld; opleggingen en `#ASTER-EXCIT`-lasten als `CHARGE`, zoals bij modaal) →
`CALC_MODES TYPE_RESU='MODE_FLAMB'`, `OPTION='PLUS_PETITE'`, `NMAX_CHAR_CRIT = n`
(route als Code-Aster-testcase ssll105a; methodiek: EDF R&D, U2.08.04). `CHAR_CRIT` van
Code-Aster is direct Mecway's kniklastfactor (nagelopen: Mecway-voorbeeld BucklingBeam,
41124,699 in beide); negatief = knik bij de omgekeerde belasting (KNOWN_BUGS 46).

De bridge zoekt altijd de kleinste ∣factoren∣, zoals Mecway; er is geen instelling
voor een zoekcentrum. `OPTION='CENTRE'` negeert `CHAR_CRIT` bij `MODE_FLAMB` in
Code-Aster 17.4 (de `.mess` meldt "La valeur de décalage en charge critique est :
0.00000E+00"; gemeten op BU-01 met 90, 200 en −200: steeds de kleinste factoren).
`OPTION='BANDE'` werkt wel (`CHAR_CRIT=(100, 300)` gaf 209,853 en 259,086), maar wordt
niet aangeboden ([`Standaardinstellingen_en_aannames.md`](Standaardinstellingen_en_aannames.md)
§3.8).

### 2.3 Normering

| Normering | Betekenis | Gebruik |
|---|---|---|
| `MASS_GENE` | phi^T M phi = 1 | modaal standaard, zoals Mecway |
| `RIGI_GENE` | phi^T K phi = 1 | knik standaard, zoals Mecway (Code-Aster kent dit niet voor knik; de bridge normeert zelf met Kg) |
| `TRAN_ROTA` | grootste verplaatsing of rotatie = 1 | standaard van Code-Aster (catalogus `calc_modes.py`) |
| `TRAN` | grootste verplaatsing = 1 | handig om vormen te vergelijken |
| `EUCL` | euclidische norm = 1 | |

### 2.4 Controle van de modes

`VERI_MODE` controleert per mode de relatieve fout (grens `SEUIL`, standaard 1e-6 zoals
in Code-Aster) en telt met de Sturm-test of er geen modes gemist zijn. De bridge zet
`STOP_ERREUR='NON'`: een mislukte controle wordt een alarm (`<A>`) en een WARNING met
uitleg in de log, in plaats van een fout die de run stopt. Reden: bij meervoudige modes
op de grens van het gevraagde aantal faalt de Sturm-test terwijl de modes goed zijn
(§3.1). Controleer bij zo'n WARNING de modes zelf.

### 2.5 Modaal met voorspanning

Met de instelling *Voorspanning door belastingen* aan (standaard) en minstens één
belasting of thermische rek (*Thermal stress* met *Temperature*):

1. `MECA_STATIQUE` met alle lasten (ook `#ASTER-EXCIT`) → spanningsveld `SIEF_ELGA`
   (`CREA_CHAMP`), zoals bij knik (§2.2).
2. `ASSEMBLAGE` met `RIGI_MECA`, `MASS_MECA` en `RIGI_GEOM` (met dat veld); bij een
   centrifugaalkracht ook `RIGI_ROTA` (centrifugale stijfheid, *spin softening*; de
   `ROTATION`-last staat dan in `CHARGE`).
3. `COMB_MATR_ASSE`: K = `RIGI_MECA` + `RIGI_GEOM` (+ `RIGI_ROTA`), alle met
   coëfficiënt 1 (Code-Aster-testcases sdll101a, gespannen snaar, en sdll133a,
   draaiend wiel).
4. `CALC_MODES` met deze K en de massa, verder als §2.1.

Trek geeft een positieve `RIGI_GEOM` (hogere frequenties), druk een negatieve. Zoals
Mecway (Mecway Ltd., 2026, §6.3; voorbeelden VibratingMembrane en VibratingString,
§11.20 en §11.22) telt thermische rek mee, en geeft een centrifugaalkracht ook spin
softening (voorbeeld Impeller, §11.21). Een `#ASTER-EXCIT`-last zonder
Mecway-belasting start de voorspanning niet.

Gemeten (verificatie MP, [`Verificatie.md`](Verificatie.md) §7): balken en volumes
gelijk aan headless Mecway (< 1e-5), ook de draaiende hex20-balk; plaat met
thermische druk −0,07 / −0,25% t.o.v. Mecway (Mecway's quad4 convergeert trager);
analytisch ≤ 0,11%. Afwijkingen (KNOWN_BUGS 49): de draaiende **balk** (`POU_D_E`)
geeft in het rotatievlak tot 0,5% lagere frequenties dan Mecway (Code-Aster's
`RIGI_ROTA` van balken); met **schalen** wordt de centrifugaalkracht een
formule-last en ontbreekt de spin softening (WARNING); voor **knoopmassa's** ook
(WARNING).

## 3. Bijzonderheden

### 3.1 Meervoudige modes

Bij symmetrie (vierkante doorsnede, vierkante plaat) zijn er modes met (bijna) dezelfde
frequentie. Valt zo'n paar op de grens van het gevraagde aantal, dan meldt Code-Aster
het Sturm-alarm `ALGELINE5_23` (de controle telt een mode meer dan berekend). De
resultaten zijn bruikbaar; vraag een mode meer als je het hele paar wilt. De vorm van
een meervoudige mode is niet uniek (elke combinatie is ook een vorm), dus vergelijk
vormen met Mecway alleen bij enkelvoudige modes.

### 3.2 Vrij-vrij en starre modes

Zonder opleggingen is K singulier en faalt de standaard-shift 0 van Code-Aster. De
bridge zoekt dan rond een kleine negatieve frequentie (`CENTRE`, regel
`BRIDGE_FREE_SHIFT` in de `.mess`); de 6 starre modes komen met |f| van orde 1e-4 Hz
(verificatie MO-04: |f| < 6e-4 Hz; soms negatief, numeriek nul), daarna de elastische.

### 3.3 Wat niet kan

- Demping: standaard niet (zoals Mecway); met de instelling *Complexe modes met
  demping* wel, als complexe modes (§6). Cyclische symmetrie: alleen
  modaal, met grenzen (§7.5). Akoestische holtemodes (Mecway A30): [`Akoestiek.md`](Akoestiek.md).
- Voorspanning met een opgelegde verplaatsing of rotatie ≠ 0 (ook Mecway niet).
- Spin softening bij centrifugaalkracht op schalen en knoopmassa's (§2.5).
- Effectieve massa voor de rotaties om een ander punt dan de oorsprong (leg de
  oorsprong in Mecway in dat punt, §1.5), en de fractie met Mecway's noemer (vrije
  massa; de bridge geeft die van Code-Aster, §1.4).
- Contact, gaps, tension/compression only: niet in een modale of knikanalyse (ERROR).
- Spanningen per knikvorm (alleen per trillingsvorm, §1.4).

### 3.4 Balkorientatie en doorsneden

De bridge draait de doorsnede van een balk zoals Mecway (*orientation vector* en
*angle* per element, Mecway-handleiding v33 §7.5; zonder orientatie de standaard van
Mecway: V = Z × U, langs Z V = Y). Nagelopen voor modaal, statisch en knik met balken
langs X, Y, Z en schuin, zonder orientatie, met een vector en met vector + hoek, alle
doorsneden van de bridge en een raamwerk ([`Verificatie.md`](Verificatie.md) §7,
*Balkorientatie*, MO-20 … MO-29): frequenties, trillingsvormen (richting van de
uitwijking) en effectieve massa per richting gelijk aan Mecway en aan Euler-Bernoulli.
Net als Mecway rekent `POU_D_E` met de polaire traagheid voor torsie, maar zonder
rotatietraagheid van de doorsnede bij buiging en zonder verschoven dwarskrachtcentrum
(T, L, C). Knik met buigende momenten (raamwerken) en zuivere torsieknik wijken af van
Mecway (KNOWN_BUGS 112, 113).

## 4. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| WARNING: Modaal: elset(s) ... hebben geen dichtheid | geen massa | geef het materiaal een dichtheid |
| WARNING: Modale analyse: belastingen (...) worden genegeerd | voorspanning uit, model met lasten | gewenst? Anders *Voorspanning door belastingen* aan (pagina Modaal) |
| ERROR: Modaal met voorspanning: opgelegde verplaatsing of rotatie <> 0 op ... | voorspanning met een opgelegde verplaatsing ≠ 0 (Mecway rekent dat ook niet) | zet de waarde op 0, of zet de voorspanning uit (dan telt alleen dat de vrijheidsgraad vastligt) |
| ERROR: Modaal met voorspanning zonder opleggingen | de statische berekening onder de lasten is singulier | leg het model vast, of zet de voorspanning uit |
| WARNING: Negatieve frequentie(s) | druk boven de kniklast van die mode | verlaag de drukbelasting; controleer met een knikanalyse |
| WARNING: Centrifugaalkracht in een model met schalen / van knoopmassa's | spin softening ontbreekt daar (§2.5) | frequenties zijn iets hoger dan in Mecway; vergelijk zo nodig met Mecway |
| WARNING: Geen opleggingen (vrij-vrij) | los model | normaal voor een vrij lichaam; tel 6 starre modes mee |
| ERROR: Knik zonder belasting / Knik zonder opleggingen | knik vraagt een last en opleggingen | breng de referentielast en opleggingen aan |
| `<EXCEPTION> <ALGELINE3_81>` (le shift ... coïncide avec une valeur propre) | singuliere stijfheid: mechanisme, los onderdeel, scharnier | leg het model beter vast, of kies een negatieve zoekfrequentie (bijv. -10 x de verwachte eerste elastische frequentie); de starre modes komen dan met ~0 Hz mee. Dat helpt alleen als het losse deel massa heeft (dichtheid of puntmassa). Een verbinding uit `#ASTER`-code telt alleen mee via `#ASTER-EXCIT` |
| alarm `ALGELINE3_82` (la borne minimale ... est une valeur propre) | de ondergrens van de Sturm-band valt (bijna) op een eigenwaarde, meestal een starre mode bij ~0 Hz (gezien met een vrij-vrij model en een negatieve zoekfrequentie) | meestal onschuldig: controleer het aantal modes, of verschuif de zoekfrequentie iets |
| `ALGELINE5_49` / `ALGELINE3_78` (te weinig modes) | zoekfrequentie ver van de modes; of veel valse modes bij ~0 Hz (bijv. een membraan met een kunstmatig kleine E en voorspanning, zoals Mecway's VibratingMembrane: rotatiemodes van `COQUE_3D` zonder stijfheid) | zoekfrequentie dichter bij de verwachte frequenties, 0, of minder modes; bij het membraan een zoekfrequentie rond de verwachte frequentie (KNOWN_BUGS 49) |
| alarm `ALGELINE5_23` (Sturm) | meervoudige mode op de grens, of een gemiste mode | vraag een of twee modes meer en vergelijk |
| alarm `ALGELINE5_15` ("... a une norme d'erreur ... supérieure au seuil admis") | een mode haalt de nauwkeurigheid niet | fijner/beter mesh, of *Controle modes* groter (1e-4) |
| alarm `ALGELINE2_74` | een van de `VERI_MODE`-controles is niet gehaald | zie de alarmen ervoor en de tabel in de `.mess` |
| WARNING: Negatieve kniklastfactor(en) | knik bij de omgekeerde last (bijv. trek in plaats van druk) | controleer de richting van de last; alleen positieve factoren horen bij de aangebrachte richting |
| WARNING: Mode 1 heeft ~0 Hz | starre beweging of mechanisme | opleggingen controleren |
| Geen RX/RY/RZ achter de modes; in de `.mess`: `aster_results_export: WAARSCHUWING: effectieve massa rotaties niet ...` | de eigen berekening lukte niet of kwam voor de translaties niet uit op Code-Aster's waarden (bijv. een onbekend soort vrijheidsgraad) | de frequenties, vormen en translaties zijn goed; meld het model als fout (KNOWN_BUGS). Een rotatie-effectieve massa kun je dan in Mecway zelf opvragen (*modal effective mass*, interne solver) |
| RX/RY/RZ-fracties lijken op de translaties | het model ligt ver van de oorsprong: een rotatie om de oorsprong is dan vooral een verplaatsing | leg de oorsprong in het punt waarom je de rotatie wilt (§1.5) |
| INFO: Modes: ... genegeerd: reactions (of een ander veld) | bij modes gaan alleen vormen en spanningen naar Mecway | normaal; reacties horen niet bij een mode |
| De resultaatroute 'tabel' werkt niet ... | modes alleen via `liml` | zet *Resultaten naar Mecway* op `liml` |

## 5. Niet-lineaire knik

Lineaire knik (§2.2) gaat uit van een perfecte constructie en kleine verplaatsingen
vóór het knikken. Twee aanvullingen in de **niet-lineaire statische analyse**
(`nonlin_static_3d`, Mecway *Nonlinear Static*, L30), los of samen te gebruiken:

| Functie | Instelling (pagina Niet-lineair statisch) | Wat het geeft |
|---|---|---|
| Stabiliteit per stap | *Stabiliteit per stap (CRIT_STAB)* | na elke stap hoe ver de huidige toestand van knik af is, in de log en het statusvak, en een melding als knik bereikt is |
| Knikvorm als imperfectie | *Imperfectie: amplitude*, *knikvorm nr.*, *amplitude in* | de berekening op een licht voorvervormde vorm (knikvorm × amplitude): de uitbuiging groeit met de last en de draagkracht daalt, zoals bij een echte constructie |

Mecway heeft hier zelf geen invoer voor: Mecway's voorbeeld BucklingPlateNonlinear
(Mecway Ltd., 2026, §11.9) brengt een kleine dwarskracht aan als verstoring. Dat
werkt met de bridge ook; de knikvorm als imperfectie is de aanpak die Code-Aster
aanraadt (EDF R&D, U2.08.04 §2.2).

### 5.1 Werkwijze

1. **Model in Mecway**: analysetype *Nonlinear Static*. Breng de last aan met een
   **tijdstabel** die vanaf 0 oploopt (bijv. 0 op t = 0 en de ontwerplast of iets
   boven de verwachte kniklast op t = 1). Zonder tabel staat de volle last er vanaf
   de eerste stap; dan zie je de opbouw niet.
2. **Stappen**: *Substappen per tijdsinterval* bepaalt hoeveel punten je krijgt
   (standaard 10; 20 tot 40 geeft een nauwkeuriger knikpunt).
3. **Elementen**: gebruik **volume-elementen** (bij voorkeur kwadratisch, of hex8
   met `LINE_QUAD`) of schalen met `elem_shell` = `COQUE_3D`. Balken (`POU_D_E`) en
   DKT/DST-schalen rekenen in de bridge geometrisch lineair (KNOWN_BUGS 11): daar
   werkt CRIT_STAB wel (als lastfactor), maar groeit de uitbuiging met een
   imperfectie niet (WARNING).
4. **Pagina Niet-lineair statisch** (of per model met `#ASTER-OPTIE`,
   [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §2):

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Stabiliteit per stap (CRIT_STAB) | `crit_stab` | uit | aan als je wilt weten bij welke last de constructie knikt of een grenspunt bereikt. Kost per stap een eigenwaardeberekening (extra rekentijd per stap; bij grote modellen merkbaar) |
| Imperfectie: amplitude (0 = geen) | `imperfection_amplitude` | 0 | > 0 voor een imperfectie, bijv. L/1000 tot L/300 of de waarde uit de norm. Negatief keert de vorm om (het teken van een knikvorm is willekeurig) |
| Imperfectie: knikvorm nr. | `imperfection_mode` | 1 | een andere vorm (2 = de op een na kleinste kniklastfactor), bijv. bij twee vormen met bijna dezelfde factor |
| Imperfectie: amplitude in (m / x L) | `imperfection_unit` | `m` | `L`: amplitude als fractie van de grootste afmeting van het model (0.001 = L/1000; de log noemt L en de amplitude in m) |

5. **Starten.** Bij een imperfectie rekent Code-Aster eerst de lineaire knik onder
   de lasten op de eindtijd (zoals `buckling_3d`), vervormt het mesh met de gekozen
   knikvorm en rekent dan niet-lineair.
6. **Resultaten**: de verplaatsingen per stap in Mecway, plus in de log en het
   statusvak de imperfectie en de stabiliteit (§5.3).

### 5.2 Hoe de bridge vertaalt

**CRIT_STAB.** `STAT_NON_LINE` krijgt `CRIT_STAB=_F(OPTION='PLUS_PETITE',
NMAX_CHAR_CRIT=1)` (catalogus `stat_non_line.py`, testcases ssll105d/e/f): na elke
stap de kleinste |λ| van een eigenwaardeprobleem met de tangentstijfheid K_T van dat
moment (EDF R&D, U4.51.03 §3.18; U2.08.04 §2.1). Na de berekening zet de job de
tabel `ANALYSE_MODALE` als `BRIDGE_CRIT_STAB`-regels in de `.mess`. Wat λ betekent,
hangt af van de kinematica (`deformation`, per elset gekozen,
[Instellingen §2.3](Instellingen_contact_en_nietlineair.md#23-kinematica-deformation)):

| Kinematica | Probleem | λ betekent | Knik als |
|---|---|---|---|
| kleine verplaatsingen (`PETIT`, `PETIT_REAC`; balken altijd) | det(K_T + λ K_g) = 0, K_g uit de spanning van de stap | **kritische lastfactor van de huidige last**: knik bij λ × de last van dat moment | 0 < λ ≤ 1 |
| grote verplaatsingen (`GROT_GDEP`, `GREEN_LAGRANGE`, `GDEF_LOG`; standaard voor volumes en `COQUE_3D`) | det(K_T + λ I) = 0 (K_T bevat K_g al) | **kleinste eigenwaarde van K_T met omgekeerd teken** (een stijfheid, geen lastfactor): < 0 stabiel | λ wordt 0 |

Rekent één elset met grote verplaatsingen, dan geldt de tweede regel voor het hele
model (gemeten). Bij grote verplaatsingen schat de bridge het knikpunt: wisselt λ van
teken tussen twee stappen, dan lineair geïnterpoleerd; anders worden de laatste twee
stappen lineair doorgetrokken naar 0. Loopt de last vanaf 0 evenredig met de tijd op,
dan is de kniklast ≈ t_knik / t × de last op t. De schatting is beter naarmate de
laatste stap dichter bij knik ligt (NK-02a: vanaf 0,9 Pcr +0,4 %).

Wil je een lastfactor bij volume-elementen: zet `deformation` op `PETIT` (NK-02b,
exact). Dat is dan wel een lineaire schatting rond de huidige toestand, zonder
tweede-orde-effect op de verplaatsingen.

**Imperfectie** (`bridge_to_aster._imperfection_blocks`):

1. `MECA_STATIQUE` met alle lasten op de eindtijd (`INST`), `SIEF_ELGA`,
   `ASSEMBLAGE` `RIGI_MECA` + `RIGI_GEOM`, `CALC_MODES` `MODE_FLAMB` (zoals §2.2), met
   `NORM_MODE` `TRAN`: de grootste verplaatsingscomponent van de vorm is 1. Een
   meebewegende druk telt hier als vaste last.
2. `MODI_MAILLAGE` `DEFORME` `TRAN` met amplitude × knikvorm k (`CREA_CHAMP`
   `COMB`; zoals testcase ssnl502d), daarna `AFFE_CARA_ELEM` opnieuw (balk- en
   schaalassen op de vervormde vorm).
3. `STAT_NON_LINE` en `CALC_CHAMP` op het vervormde mesh.
4. Het mesh terug met −amplitude × knikvorm (zoals testcase hsna105a), zodat de
   resultaten op de knopen van het Mecway-model passen (de export controleert de
   coördinaten tegen de `.liml`).

De **verplaatsingen in Mecway zijn t.o.v. de imperfecte vorm**: de totale uitbuiging
is de imperfectie (in de knikvorm, maximaal de amplitude) plus de getoonde
verplaatsing. Spanningen en reacties horen bij de imperfecte constructie.

### 5.3 Interpretatie

Wat de log en het statusvak tonen (voorbeelden uit de verificatie):

- `Imperfectie: knikvorm 1 (kniklastfactor 1.11339 van de lasten op de eindtijd),
  amplitude 0.001 m.` De kniklastfactor is die van de lineaire knik onder de lasten
  op de eindtijd (zelfde getal als `buckling_3d`).
- Kleine verplaatsingen: `Stabiliteit (CRIT_STAB): op t = 1 kritische lastfactor
  1.11111: de last van dat moment x 1.11111 geeft knik`. Bij een last die lineair
  oploopt, is λ(t) × P(t) constant (de kniklast). Per stap staat λ in de log.
- Grote verplaatsingen: `Stabiliteit (CRIT_STAB, grote verplaatsingen): op t = 1
  criterium -2.70 ... Geschat knikpunt t ~ 1.115`. Alleen het teken en het nulpunt
  hebben betekenis; de grootte hangt af van de eenheden en het mesh.
- **Knik bereikt** (WARNING): λ ≤ 1 (kleine verplaatsingen) of λ wisselt van teken
  (grote verplaatsingen). Een **perfecte** constructie blijft in de berekening recht,
  ook boven de kniklast; de melding zegt dan alleen dat ze daar instabiel is. Voor
  het gedrag na knik: een imperfectie. Gaat λ na de tekenwissel weer onder 0, dan
  is de constructie na knik weer stabiel (bijv. een plaat, Mecway's
  BucklingPlateNonlinear: wissel bij t ≈ 0,57, last 7,15 N; theorie 7,06 N).
- **Grenspunt / draagkracht.** Met een imperfectie (en plasticiteit) heeft de
  last-verplaatsingslijn een maximum. Met een last als tijdstabel stopt Code-Aster
  daar (`MECANONLINE9_7`, de resultaten tot dat moment worden geladen), en gaat het
  criterium naar 0 (WARNING "bijna 0"). **De last op het laatste tijdstip is de
  draagkracht** (NK-04: 0,49 Pcr bij e0 = L/200, tegen Pcr voor de perfecte kolom).
- **Controle**: de totale uitbuiging w = e0 / (1 − P/Pcr) (versterkingsfactor van
  een staaf met een beginkromming in de knikvorm; Timoshenko & Gere, 1961,
  hoofdstuk 1), en een Southwell-grafiek (extra uitbuiging δ tegen δ/P is een rechte
  met helling Pcr; Southwell, 1932) geeft Pcr terug (NK-03: binnen 0,5 %).

### 5.4 Wat niet kan

- CRIT_STAB en de imperfectie alleen in `nonlin_static_3d`, niet in dynamica
  (`DYNA_NON_LINE` kent CRIT_STAB wel, NIET ingebouwd).
- Imperfectie niet samen met contact, compression only, gaps of tension only
  (ERROR): de knikvorm komt uit een lineaire berekening.
- Eén knikvorm als imperfectie; geen combinatie van vormen, geen gemeten geometrie.
- De knikvorm van CRIT_STAB zelf (`MODE_FLAMB` in het resultaat) gaat niet naar
  Mecway; de imperfectie is altijd de lineaire knikvorm onder de eindlast.
- Boogslengtemethode (`PILOTAGE`), om voorbij het grenspunt te rekenen: niet
  ingebouwd.
- Zie KNOWN_BUGS 53.

### 5.5 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| WARNING: Knik bereikt: vanaf t = ... is de kritische lastfactor <= 1 | de last is boven de (lineair geschatte) kniklast | verlaag de last, of reken met een imperfectie voor het gedrag na knik |
| WARNING: Knik of instabiliteit bereikt rond t = ... | λ wisselt van teken (grote verplaatsingen) | idem; bij een plaat kan het gedrag na knik stabiel zijn |
| WARNING: Het stabiliteitscriterium is bijna 0 | dicht bij knik of een grenspunt | stopt de berekening daar (`MECANONLINE9_7`), dan is de last op het laatste tijdstip de draagkracht |
| WARNING: CRIT_STAB gaf geen waarden | de tabel `ANALYSE_MODALE` ontbreekt (bijv. de run stopte in de eerste stap) | zie de `.mess`; eerst de gewone convergentie oplossen |
| ERROR: Imperfectie (knikvorm) niet mogelijk met contact ... | de knikvorm komt uit een lineaire berekening | amplitude 0, of die onderdelen onderdrukken in een configuratie |
| ERROR: Imperfectie: ongeldige amplitude of modenummer / eenheid onbekend | invoer | getal, mode ≥ 1, eenheid `m` of `L` |
| WARNING: Imperfectie met kleine verplaatsingen (DEFORMATION=...) | `PETIT`: geen tweede-orde-effect | `deformation` = `GROT_GDEP` (standaard) |
| WARNING: Imperfectie: balken en DKT/DST-schalen ... rekenen geometrisch lineair | daar groeit de uitbuiging niet | volume-elementen of `elem_shell` = `COQUE_3D` |
| WARNING: Imperfectie: knikvorm k hoort bij de omgekeerde last | negatieve kniklastfactor (bijv. trek) | kies een mode met een positieve factor, of controleer de lastrichting |
| WARNING: Imperfectie: knikvorm k niet gevonden | minder modes gevonden dan k | kleiner modenummer; zie de `.mess` |

## 6. Modaal met demping: complexe modes

Een gewone modale analyse rekent zonder demping: K φ = ω² M φ, reële modes. Met
demping (matrix C) trilt een mode uit en wordt het eigenwaardeprobleem
kwadratisch: (K + s C + s² M) φ = 0, met s = −ζω_n ± i·ω_d. Per mode geeft dat:

| Grootheid | Betekenis |
|---|---|
| f_d = ω_d / 2π | **gedempte frequentie**: de frequentie waarmee de mode werkelijk trilt |
| ζ | **dempingsverhouding** (fractie van kritisch): de amplitude neemt af als e^(−ζ·2πf_n·t) |
| f_n = \|s\| / 2π | f_d / √(1 − ζ²); bij Rayleigh-demping precies de ongedempte eigenfrequentie |
| decay rate = ζ·2πf_n | uitdempingssnelheid [1/s], zoals Mecway hem bij complexe akoestische modes geeft |

**Wat Mecway doet** (Mecway 33, headless gemeten): een *Frequency*-analyse (V30)
negeert Rayleigh-demping (massa op een balk met α = 3,55 1/s: dezelfde frequenties
5,6494 / 8,4741 / 564,94 Hz als zonder, geen decay rate) en geeft met een
*Damper*-element geen oplossing. Rayleigh-demping hoort volgens de manual bij
*Dynamic Response* (Mecway Ltd., 2026, §9.26). Complexe modes kent Mecway alleen in
de akoestiek met impedantie (§6.9.2). De bridge volgt daarom Code-Aster
(`CALC_MODES` met `MATR_AMOR`, testcase sdld21c) als **optie**; standaard rekent hij
zoals Mecway.

### 6.1 Werkwijze

1. **Model in Mecway**: analysetype *Frequency* met *Number of modes*, zoals §1.1.
2. **Demping** (een van beide of samen):
   - *Rayleigh damping* op het hele model (zonder selectie): C = αM + βK (Mecway
     Ltd., 2026, §9.26). Volgens de manual hoort deze last bij *Dynamic
     Response*; of de Mecway-GUI hem in een *Frequency*-model toelaat of bij het
     wisselen van analysetype bewaart, is NIET nagelopen. Staat hij in de `.liml`
     (`<rayleighdamping selection="">`), dan leest de bridge hem; Mecway's eigen
     solve negeert hem (headless gezien). Per mode is ζ_n = α/(2ω_n) + βω_n/2:
     α dempt de lage, β de hoge modes.
   - *Damper*-elementen: line2 met het materiaal *Damper* (*Viscous damping
     coefficient* c, Mecway Ltd., 2026, §7.8), demping langs de as van het element.
3. **Hoofdvenster**, pagina Modaal: zet *Complexe modes met demping (Rayleigh,
   dempers)* aan. De andere instellingen gelden zoals in §1.2 (*Zoekfrequentie*,
   *Aantal modes*, voorspanning).
4. **Starten** en de resultaten bekijken (§6.3).

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Complexe modes met demping (Rayleigh, dempers) | `modal_complex` | uit | aan als je wilt weten hoe sterk elke mode gedempt is en met welke frequentie hij uittrilt, bijv. om α en β te kiezen of te controleren vóór een respons op modale basis ([`Respons_op_modale_basis.md`](Respons_op_modale_basis.md)), of om het effect van dempers op de modes te zien. Uit: de demping telt niet mee (INFO in de log), zoals Mecway |

Zonder demping in het model geeft de instelling gewone reële modes (INFO).

### 6.2 Hoe de bridge vertaalt

`bridge_modal_damping.py`:

1. `ASSEMBLAGE` zoals §2.1 (met voorspanning §2.5), plus bij dempers `AMOR_MECA`
   (de `A_T_D_L` van de dempers; de andere discrete elementen krijgen demping 0,
   anders alarm `DISCRETS_28`).
2. De dempingsmatrix `amor` = α·M + β·K + C_dempers met `COMB_MATR_ASSE`. M en K zijn
   de matrices van het eigenwaardeprobleem: Rayleigh werkt op het hele model, ook
   op knoopmassa's (*mass*) en veren (*Spring*), en met voorspanning op K + K_g.
   Zo is ζ_n = α/(2ω_n) + βω_n/2 met de ω_n van dezelfde modes, precies de
   dempingsverhouding die de respons op modale basis per mode gebruikt
   ([`Respons_op_modale_basis.md`](Respons_op_modale_basis.md) §2.3; MC-04).
3. `CALC_MODES` met `MATR_AMOR=amor`: zonder zoekfrequentie `OPTION='PLUS_PETITE'`
   met `SOLVEUR_MODAL=_F(METHODE='TRI_DIAG')` (Lanczos; `SORENSEN` kan bij een
   kwadratisch probleem niet met `PLUS_PETITE`, `<EXCEPTION> ALGELINE2_71`); met een
   zoekfrequentie `OPTION='CENTRE'` met `SORENSEN`; zonder opleggingen `CENTRE` rond
   een kleine negatieve frequentie (§3.2). Gemeten: `TRI_DIAG`, `QZ` en `SORENSEN`
   (`CENTRE`) gaven dezelfde f_d en ζ (verschil ≤ 1e-9).
4. Het resultaat is een `MODE_MECA_C` met complexe vormen. Code-Aster's `FREQ` is de
   **gedempte** frequentie f_d, `AMOR_REDUIT` is ζ (gemeten: ζ = 0,3 gaf
   5,38919 = 5,64944·√(1 − 0,09) Hz). `aster_results_export.py` schrijft per mode
   `<mode frequency="f_d Hz" decayrate="ζ·2πf_n 1/s">` (het formaat van Mecway's
   complexe akoestische modes) met als vorm het **reële deel**: eerst een
   fasedraaiing die het reële deel zo groot mogelijk maakt (θ = ½·arg(φᵀMφ)), dan
   genormeerd op φᵀMφ = 1 en de grootste component positief. Bij Rayleigh-demping
   (proportioneel) is de vorm dan precies de reële, massagenormeerde mode
   (gemeten: gelijk tot 2e-9). De instelling *Normering* geldt hier niet.
5. In de `.mess` per mode `BRIDGE_MODE nr FREQ=f_d AMOR_REDUIT=ζ FREQ_NAT=f_n
   DECAY=.. IMAG=..` met de effectieve massa, die de bridge zelf uit het reële deel
   rekent (of Code-Aster `MASS_EFFE_UN_*` ook voor complexe modes geeft, is niet
   nagelopen). `IMAG` = ‖Im‖/‖Re‖ (in de M-norm) na
   de fasedraaiing: 0 bij proportionele demping, groter bij dempers.

### 6.3 Interpretatie

- **Log en statusvak**: `Mode 1: 42.2257 Hz gedempt (zeta 0.05093, f_n 42.2806 Hz)
  (eff. massa ...)` (verificatie MC-04). In Mecway staat onder *Solution* de
  gedempte frequentie f_d; Mecway's API leest de modes en vormen (headless
  nagelopen); de decay rate in de Mecway-GUI is NIET nagelopen.
- **Gedempt of ongedempt?** f_d is de frequentie van een vrij uittrillende
  constructie, f_n die van de ongedempte. Bij lichte demping is het verschil klein
  (ζ = 0,05: 0,13%; ζ = 0,2: 2%; ζ = 0,5: 13%). Voor resonantie onder een
  harmonische last ligt de piek bij f_n·√(1 − 2ζ²), dus nog iets lager dan f_d
  (Clough & Penzien, 1993, hoofdstuk 3).
- **ζ per mode** zegt hoe snel een mode uitsterft: na n trillingen is de amplitude
  e^(−2πnζ/√(1 − ζ²)) van het begin (ζ = 0,05: na 10 trillingen 4%).
- **Rayleigh**: controleer met ζ_n = α/(2ω_n) + βω_n/2 of de demping per mode is
  wat je bedoelde; met alleen β zijn de hoge modes sterk gedempt, met alleen α de
  lage. Voor ζ₁ bij f₁ en ζ₂ bij f₂ volgen α en β uit de formules in Mecway's manual
  (§9.26).
- **Dempers** geven meestal **niet-proportionele** demping: de vorm is dan complex
  (de knopen bewegen niet meer in fase). De log meldt `IMAG` > 1%; in Mecway staat
  het reële deel, en de effectieve massa (uit het reële deel) is een benadering
  (de som over de modes kan iets boven 100% komen; MC-03: 107%).
- **Overkritisch gedempte modes** (ζ ≥ 1) trillen niet en worden door Code-Aster niet
  gegeven; je krijgt dan minder modes dan gevraagd (alarm `ALGELINE5_79`). Hetzelfde
  geldt voor starre modes in een vrij model (s = 0 of reëel): mode 1 is dan de
  eerste elastische mode (MC-05).

### 6.4 Wat niet kan

- Spanningen per mode bij complexe modes (alleen de vorm; INFO).
- Rayleigh-demping op een selectie (ook in Mecway alleen het hele model bij
  *mode superposition*, §9.26): niet vertaald, gemeld aan het eind van de run.
- Hysteretische (structurele) demping (`AMOR_HYST`, complexe stijfheid), modale
  demping als ζ per mode (*Extra modale demping* van de respons op modale basis is
  geen matrix en telt hier niet mee), demping in knik en akoestiek.
- Het imaginaire deel van de vorm naar Mecway (alleen het reële deel). mecway.exe
  kent intern wel een imaginaire verplaatsing (`DisplacementXImaginary`), maar de
  naam in de `.liml` en de weergave zijn niet uitgezocht.
- Overkritisch gedempte modes (ζ ≥ 1).

### 6.5 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| INFO: Modaal: Rayleigh-demping (...) / dempers (...) telt niet mee | demping in het model, instelling uit (standaard, zoals Mecway) | gewenst? Anders *Complexe modes met demping* aan |
| INFO: Complexe modes gevraagd, maar het model heeft geen demping | instelling aan zonder Rayleigh of dempers | normaal: reële modes; breng demping aan in Mecway |
| INFO: Complexe modes: ... geen spanningen per mode | *Resultaatvelden* met `stresses`/`vonmises` | alleen vormen; zet de instelling uit voor spanningen per (ongedempte) mode |
| WARNING: Negatieve Rayleigh-coefficient | α < 0 of β < 0 | controleer de invoer: negatieve demping laat modes aangroeien |
| WARNING: Code-Aster-alarm ALGELINE5_79 (minder modes dan gevraagd) | overkritisch gedempte modes (ζ ≥ 1) of starre modes, die niet trillen | verlaag α (lage modes) of β (hoge modes) als je ze wilt zien; zie ζ per mode in de log |
| WARNING: Code-Aster-alarm FACTOR_11 | singuliere stijfheid bij het ontbinden: met complexe modes in een vrij model normaal (gezien in MC-05, resultaten gelijk aan Mecway) | zonder vrij model: opleggingen controleren |
| `<EXCEPTION> ALGELINE2_71` | `SORENSEN` met `PLUS_PETITE` bij een kwadratisch probleem (alleen met eigen `#ASTER`-code) | de bridge gebruikt zelf `TRI_DIAG` of `CENTRE` |
| alarm `ALGELINE5_15` | de foutnorm van een mode ligt boven `SEUIL` (gezien met zoekfrequentie 100 Hz op MC-04: de `.mess` gaf 0.000001 bij een grens van 0.000001, f_d en ζ gelijk aan `TRI_DIAG` tot 1e-9) | onschuldig als het net boven de grens is; anders *Controle modes* 1e-5 |

## 7. Cyclische symmetrie

Een constructie die uit N gelijke segmenten rond een as bestaat (schijf, waaier,
rotor, flens met bouten) kan als één sector gerekend worden. Elke trillingsvorm van
het hele wiel hoort dan bij een **aantal nodal diameters** ND = 0 … N/2 (naar
beneden afgerond): de vorm herhaalt zich van segment tot segment met een
faseverschuiving van ND·360°/N.

**Wat Mecway doet** (Mecway Ltd., 2026, §9.41; headless gemeten met Mecway 33): de
*Cyclic symmetry*-constraint koppelt een master- en een slave-snijvlak. In een
*Frequency*-analyse rekent Mecway per ND het aantal *Number of modes* en zet ze op
volgorde van ND en frequentie (ring met 12 segmenten en 2 modes: 14 modes, ND 0
… 6). Een paar staande golven (0 < ND < N/2) telt als één mode. De oplossing toont
het hele wiel. In de `.liml`:
`<cyclicsymmetry axis="3" segments="12" selectionmaster="A" selectionslave="B" />`
met `axis` 1 = X, 2 = Y, 3 = Z (de as door de oorsprong).

**Wat de bridge doet**: Code-Aster `MODE_ITER_CYCL` (EDF R&D, U4.52.05; cyclische
substructurering, R4.06.03) op de sector, met dezelfde modes in dezelfde volgorde
als Mecway; in Mecway staan de vormen, net als bij Mecway's eigen oplossing, op het
**hele wiel** (instelling `cyclic_full_wheel`, standaard aan; uit = alleen de
sector).

### 7.1 Werkwijze

1. **Model in Mecway**: één segment (sector) met **dezelfde knopenpatronen op beide
   snijvlakken** (Mecway eist dat ook met de interne solver). Alleen
   volume-elementen; met hex8 liever kwadratisch (hex20) dan `LINE_QUAD` (dat kan
   hier niet, §7.5).
2. **Analysetype** *Frequency* met *Number of modes* = het aantal modes **per
   nodal diameter** (zoals Mecway; het totaal is dat maal N/2 + 1).
3. **Cyclic symmetry**: kies de knoop- of vlakselectie van het ene snijvlak als
   master en die van het andere als slave, de as (X, Y of Z, door de oorsprong) en
   het aantal segmenten van het **hele** wiel. Welke kant master is, maakt niet uit
   (de bridge bepaalt de draairichting zelf).
4. **Opleggingen**: zoals gewoon (bijv. *Fixed support* op de naaf). Op een
   snijvlak mogen knopen alleen **volledig** vastliggen (§7.5). Een los wiel (zonder
   opleggingen) kan ook: dan zijn er starre modes bij ~0 Hz in ND 0 en 1.
5. **Belastingen** geven, zoals bij §2.5, een voorgespannen modale analyse (bijv.
   *Centrifugal force* om de symmetrieas: spanningsverstijving en spin softening).
6. **Hoofdvenster**: `auto` (of `modal_3d`), resultaatroute `liml`. *Starten*.

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Cyclische symmetrie: sectormodes in de basis (0 = automatisch) | `cyclic_base_modes` | 0 = max(20, 4 × modes per ND) | bij veel modes per ND of als de hoogste modes per ND ertoe doen: verhogen; reken ter controle met het dubbele, de frequenties moeten gelijk blijven (§7.3) |
| Zoekfrequentie [Hz] | `modal_shift_hz` | 0 | > 0: per ND de modes het dichtst bij deze frequentie (`OPTION='CENTRE'`); < 0 heeft hier geen zin (de sector met vaste snijvlakken heeft geen starre modes) |
| Voorspanning door belastingen | `modal_prestress` | aan | zoals §1.2 |
| Aantal modes (zonder maxmode) | `modal_modes` | 10 | zoals §1.2, per ND |
| Cyclische symmetrie: het hele wiel naar Mecway | `cyclic_full_wheel` | aan | uit bij een groot model als het resultaatbestand te groot wordt (het wiel is N keer zo groot als de sector); de frequenties blijven gelijk |

`modal_norm`, `modal_complex` en spanningen per mode (`fields`) gelden niet bij
cyclische symmetrie (INFO of WARNING in de log).

### 7.2 Hoe de bridge vertaalt

`bridge_cyclic.py`, template `AsterTemplate_ModeIterCycl.comm`, in de job
`aster_cyclic.py`:

1. **Paren**: elke masterknoop krijgt de slaveknoop op ±360°/N om de as (binnen
   1e-5 × de modelgrootte); de kant op +360°/N wordt `GAUCHE`, de andere `DROITE`
   (Code-Aster: trigonometrische richting, U4.52.05 §1; omgekeerd gaf `<EXCEPTION>
   ALGORITH16_58`). Knopen op de as vormen de interface `AXE`. Volledig vaste knopen
   op een snijvlak vallen uit de interfaces; ligt maar één knoop van een paar vast,
   dan legt de bridge de andere ook vast (INFO). De paren staan als knoopgroepen
   `BRCYC_D`, `BRCYC_G`, `BRCYC_A`, `BRCYC_F` in het mesh, in dezelfde volgorde.
2. **As**: `MODE_ITER_CYCL` eist de Z-as. Bij een X- of Y-as schrijft de bridge de
   coördinaten met een cyclische verwisseling van de assen (een rotatie van 120°
   om (1, 1, 1): de symmetrieas wordt Z) en zet de richtingen in de lasten mee om
   (DX/DY/DZ, FX/FY/FZ, richtingen van zwaartekracht en centrifugaalkracht); de job
   draait het mesh en de vormen terug. Gemeten: de ring om X gaf bitgelijke
   frequenties en vormen als om Z (CY-03).
3. **Basis** (Craig-Bampton): `ASSEMBLAGE` met de snijvlakken vast (`DDL_IMPO`),
   `CALC_MODES` met `cyclic_base_modes` sectormodes, `DEFI_INTERF_DYNA` (`CRAIGB`) en
   `DEFI_BASE_MODALE CLASSIQUE` (plus een statische mode per vrijheidsgraad van de
   snijvlakken). Met voorspanning eerst `MECA_STATIQUE` met de relaties van ND 0
   (`LIAISON_DDL`: u_gauche = R(360°/N) u_droite; knopen op de as alleen axiaal),
   dan K + K_g (+ `RIGI_ROTA`) zoals §2.5.
4. `MODE_ITER_CYCL` met `NB_SECTEUR` = N, `NB_DIAM` = 0 … N/2 (`TOUT_DIAM` rekent bij
   een oneven N één ND te veel) en `NMAX_FREQ` = modes per ND; `REST_SOUS_STRUC
   SECTEUR=1` geeft de vormen op de sector (let op: `NOM_CHAM` is standaard
   `'ACCE'`, de bridge vraagt `'DEPL'`).
5. **Het hele wiel** (`cyclic_full_wheel`): `DEFI_SQUELETTE` (`CYCLIQUE`,
   `SECTEUR=_F(TOUT='OUI')`) bouwt een skelet met de N sectoren en `REST_SOUS_STRUC
   SQUELETTE` zet elke mode daarop: sector j is de sector gedraaid over +j·360°/N,
   met de fase van de ND (testcases sdlv134a, sdls04a, sdls01c).
6. `aster_cyclic.collect`: per ND de modes oplopend, van een paar het eerste lid,
   regel `BRIDGE_MODE nr FREQ=.. ND=..` in de `.mess` (en `BRIDGE_CYCL ... WIEL=1`
   als het wiel gelukt is); het koppelt elke knoop van Mecway's wiel op coördinaat
   aan het skelet. `aster_results_export` schrijft de modes als `<mode>` in Mecway's
   nummering van het wiel, en `bridge_results_liml.splice_results` zet de knopen en
   elementen van alle sectoren in de modelkopie van `<solution>`, precies zoals
   Mecway's eigen cyclische oplossing (hieronder). Lukt het wiel niet, dan gaat de
   sector naar Mecway (WARNING in de `.mess`, §7.6).

**Mecway's formaat van het hele wiel** (headless gemeten met Mecway 33 op CY-01,
CY-04, CY-05, Mecway's Impeller en varianten met twee elsets, een losse knoop en
verwisselde master/slave): de modelkopie in `<solution>` heeft N kopieën van alle
knopen en elementen. Knoop i van sector j (0 … N−1) heet **i + j·n** (n = aantal
knopen van het model) en ligt op de sector gedraaid over **+j·360°/N** om de as
(rechtsom-positief, onafhankelijk van welke kant master is); element e heet **e +
j·ne** (ne = hoogste elementnummer) met de knopen van zijn sector; per elset staan de
elementen per sector achter elkaar. Ook de knopen op de snijvlakken en op de as zijn
kopieën (niet samengevoegd). Selecties, belastingen en `<cyclicsymmetry>` blijven die
van de sector. De bridge schrijft hetzelfde: nagelopen tegen Mecway's eigen oplossing
(zelfde knoop- en elementnummers, elementen en elsetvolgorde gelijk, coördinaten ≤ 1e-15
m), en Mecway's API leest het wiel van de bridge zoals zijn eigen (headless
`mecway.exe <model> script`: 960 knopen, 72 elementen, 14 modes, `node_value` op alle
knopen, `interpolate` in een element van de laatste sector).

Testcases als syntaxbron: sdlv134a (3D, knopen op de as), sdls04a/b (plaat),
sdlv301a (waaier); catalogus `mode_iter_cycl.py` (code_aster 17.4).

### 7.3 Interpretatie

- **Log en statusvak**: `Mode 7: 72.8659 Hz (ND 3)`. In Mecway onder *Solution* de
  modes in dezelfde volgorde als Mecway's eigen oplossing: eerst alle modes van ND
  0, dan ND 1, enz. Mode k van ND d is mode d × (modes per ND) + k.
- **ND = 0**: alle segmenten bewegen gelijk (bijv. de schijf als paraplu, de
  bladen in fase). **ND = N/2** (even N): naburige segmenten in tegenfase. **0 < ND
  < N/2**: de vorm heeft ND knooplijnen door het midden; bij elke mode hoort een
  tweede met dezelfde frequentie (dezelfde vorm, een kwart golf gedraaid). Het
  volledige model geeft die paren als twee modes (CY-02: 25,7385 Hz twee keer);
  Mecway en de bridge tonen er één.
- **Wat je in Mecway ziet** (`cyclic_full_wheel` aan): de vorm op het **hele wiel**,
  zoals bij Mecway's eigen oplossing. Bij ND = 0 bewegen alle sectoren gelijk; bij 0 <
  ND < N/2 zie je één staande golf met ND knooplijnen (van een paar het eerste lid;
  de tweede is dezelfde vorm, een kwart golf om de as gedraaid, en staat niet in
  Mecway); bij ND = N/2 wisselt het teken van sector tot sector. Welke staande golf
  van een paar je ziet (de stand van de knooplijnen) is willekeurig en kan van die
  in Mecway's eigen oplossing verschillen. Met de instelling uit: alleen de sector.
  De schaal van de vorm is willekeurig (zoals bij REST_SOUS_STRUC; `modal_norm`
  geldt hier niet), en dus ook anders dan in Mecway.
- **Een mode met n golven rond de omtrek** verschijnt bij ND = n als n ≤ N/2, en
  anders bij het gespiegelde ND (|n − kN|); bij een ring met 12 segmenten valt de
  mode met 12 golven in ND 0 (aliasing; gemeten: 1402,72 Hz, in het volledige
  model een paar).
- **Nauwkeurigheid**: de basis (sectormodes + statische modes) is exact voor de
  statica; de dynamica hangt af van het aantal sectormodes. Gemeten (§7.4) waren de
  laagste modes per ND met de standaardbasis gelijk aan het volledige model (≤
  0,0012%). Hoge modes per ND (bij de hoogste sectormodes in de basis) kunnen iets
  te hoog zijn: reken ter controle met het dubbele aantal.
- **Effectieve massa** geeft de bridge hier niet (Mecway ook niet: "Effective mass
  not available with MPCs or cyclic symmetry", mecway.exe).
- **Handberekening**: dunne ring in het vlak f_n = 1/(2π)·√(EI/(ρAR⁴))·n(n² −
  1)/√(n² + 1) (Blevins, 1979); ingeklemde cirkelvormige plaat f = λ²/(2πa²)·√(D/(ρh))
  met λ² = 10,216 (ND 0), 21,26 (ND 1), 34,88 (ND 2), 51,03 (ND 3) (Leissa, 1969).

### 7.4 Gemeten (verificatie CY, [`Verificatie.md`](Verificatie.md) §7)

| Model | Tegen | Afwijking |
|---|---|---|
| vrije ring, 12 segmenten om Z (CY-01) | volledig model (CY-02) / Mecway / Blevins | ≤ 2e-6 / ≤ 2e-6 / +0,59 … +1,18% (dunne-ringtheorie) |
| dezelfde ring om X (CY-03) | idem | gelijk aan CY-01 (bitgelijk) |
| ingeklemde plaat, 6 segmenten, knopen op de as (CY-04) | Mecway / Leissa | ≤ 0,03% / +0,58 … +0,66% |
| draaiende schijf om Y, 3000 r/min, naaf vast, 12 segmenten (CY-05) | volledig model (CY-06) / Mecway | ≤ 0,0012% / ≤ 0,0012% |
| Mecway's voorbeeld Impeller (17 segmenten om Y, 100 000 r/min, hex20 + wedge15; niet in de suite) | Mecway | +0,01 … +0,92%; de sector zonder cyclische symmetrie wijkt evenveel af (+0,02 … +0,79%): een verschil in de elementen, niet in de cyclische route (KNOWN_BUGS 62) |
| vormen op het hele wiel: ring (CY-01) en draaiende schijf (CY-05), elke mode | volledig model (CY-02, CY-06): subspace-MAC binnen de frequentieband (een paar: beide modes) | 1 − MAC ≤ 5,2e-7 (criterium 1e-3); snijvlakken doorlopend ≤ 1,3e-14 |
| knopen op de as (CY-04, ND 1) | Mecway's eigen oplossing | sprong tussen de kopieën op de as 6,2e-4 relatief (Mecway zelf 9,4e-4) |

### 7.5 Wat niet kan

- Cyclische symmetrie buiten de modale analyse (statisch, niet-lineair,
  thermisch): niet vertaald, ERROR; het model rekent dan als losse sector.
- Schalen, balken en veren (ook Mecway niet in een *Frequency*-analyse), `LINE_QUAD`.
- Een gedeeltelijke oplegging of een relatie (symmetry, frictionless, pinned,
  constraint equation, koppeling) op een knoop van een snijvlak; Mecway staat met de
  interne solver een axiale verplaatsing en een radiale 0 toe.
- 8 segmenten met knopen op de as (een fout in Code-Aster 17.4, §7.6).
- Bij een X- of Y-as: lasten met een functie of formule, `LIAISON_OBLIQUE`
  (symmetry/frictionless op schuine vlakken); `#ASTER`-code rekent in het gedraaide
  frame (WARNING).
- Een dubbele eigenwaarde binnen ND 0 (bijv. de ring-mode met n = N golven, die in
  ND 0 valt): `MODE_ITER_CYCL` vindt de tweede niet goed (gemeten +1,3%, ook met 80
  sectormodes). In ND N/2 ging een dubbele eigenwaarde wel goed.
- Beide leden van een paar, spanningen per mode, complexe modes en effectieve massa.
  Op het hele wiel alleen de verplaatsingen.

### 7.6 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Cyclische symmetrie: de slave-knopen liggen niet op +/-360/N graden van de master-knopen | ander aantal segmenten, een andere as, de as niet door de oorsprong, of knopenpatronen die niet op elkaar passen | controleer *Number of segments* en de as; leg de as door de oorsprong; maak de snijvlakken met hetzelfde mesh (bijv. de sector door kopiëren en draaien) |
| ERROR: ... master en slave hebben een verschillend aantal knopen | de selecties zijn niet even groot | selecteer de volledige snijvlakken |
| ERROR: ... gedeeltelijke oplegging of een relatie op de snijvlakken | een oplegging die niet alle verplaatsingen vastlegt op een snijvlakknoop | haal de oplegging van het snijvlak, of leg die knopen volledig vast |
| ERROR: ... 8 segmenten en knopen op de as | Code-Aster 17.4 (`ctetax.F90`): bij 45° is cos − sin = 0 en "ontbreekt" DX (`ALGORITH14_95`) | een klein gat op de as (geen knopen op de as), of het volledige model rekenen |
| ERROR: Cyclische symmetrie om de X/Y-as: ... kan ... niet meedraaien | een last die de bridge niet naar de Z-as kan omzetten | draai het model in Mecway zo dat de symmetrieas Z is |
| ERROR: Cyclische symmetrie met elem_hex8 = LINE_QUAD kan niet | de nieuwe middenknopen hebben geen paar | hex20 in Mecway, of `elem_hex8` = `3D` |
| ERROR: Cyclische symmetrie wordt alleen in een modale analyse vertaald | Mecway's *Static*, *Nonlinear static* of *Thermal* met cyclische symmetrie | reken het volledige model, of alleen de modes |
| `<EXCEPTION> ALGORITH16_52` "axe de symétrie cyclique différent de Oz" | Code-Aster vond de paren niet om de Z-as (de bridge zet ruis rond 0 in de coördinaten al op 0) | meld het model (KNOWN_BUGS 61) |
| `aster_cyclic: WAARSCHUWING: ... modes uit MODE_ITER_CYCL, verwacht ...` (in de `.mess`) | Code-Aster gaf een ander aantal modes; de ND per mode is onbekend | de frequenties kloppen; meld het model |
| `aster_cyclic: WAARSCHUWING: het hele wiel is niet opgebouwd (...)` of `... skelet van het hele wiel niet gemaakt` (in de `.mess`); in de log "In Mecway alleen de sector" | het skelet van Code-Aster paste niet op Mecway's wiel (bijv. een knoop van het wiel zonder knoop van het skelet op die plaats) | de modes en frequenties kloppen, alleen de sector staat in Mecway; meld het model, of zet `cyclic_full_wheel` uit |

## 8. Bronnen

- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold, tabel 8-1 (balken) en tabel 9-2 (ringen). Niet lokaal ingezien;
  de formules zijn nagerekend in de verificatie ([`Verificatie.md`](Verificatie.md),
  MO-01, CY-01).
- EDF R&D. *Code_Aster, documentation U4.52.02: Opérateur CALC_MODES*. Documentnummer
  geverifieerd via de verwijzing in U2.08.04; het document zelf is niet lokaal
  aanwezig. Standaardwaarden nagelopen in de catalogus
  `lib/aster/code_aster/Cata/Commands/calc_modes.py` (code_aster 17.4).
- EDF R&D (2018). *Code_Aster, documentation U2.08.04: Notice de calcul au flambage*.
  Versie "default", 12-01-2018 (lokale kopie).
- EDF R&D (2021). *Code_Aster, documentation U4.61.21: Opérateur ASSEMBLAGE*. Versie
  "default", 03-11-2021 (lokale kopie).
- EDF R&D (2020). *Code_Aster, documentation U4.51.03: Opérateur STAT_NON_LINE*.
  Versie "default", 30-04-2020 (lokale kopie), §3.18 `CRIT_STAB`. Standaardwaarden
  nagelopen in de catalogus `Cata/Commands/stat_non_line.py` (code_aster 17.4).
- EDF R&D (2025). *code_aster 17.4, testcases* sdll101a (gespannen balk, "corde à
  piano", `RIGI_MECA` + `RIGI_GEOM`) en sdll133a (draaiend wiel, `RIGI_GEOM` +
  `RIGI_ROTA`); ssll105d/e/f (`CRIT_STAB` in `STAT_NON_LINE`), ssnl502d
  (voordeformatie volgens de knikvorm met `MODI_MAILLAGE DEFORME`) en hsna105a (mesh
  vervormen en terugzetten), `share/aster/tests` van de installatie; sdld21c, sdld23a
  en sdld27a (massa-veersystemen met dempers, `CALC_MODES` met `MATR_AMOR`, `FREQ` en
  `AMOR_REDUIT`).
- Clough, R.W. & Penzien, J. (1993). *Dynamics of Structures* (2nd ed.). New York:
  McGraw-Hill, hoofdstuk 2 en 3 (gedempte vrije trilling, resonantie). Niet lokaal
  ingezien; de formules zijn nagerekend in de verificatie (MC-01..05).
- EDF R&D. *Code_Aster, documentation U4.52.05: Opérateur MODE_ITER_CYCL* (versie
  30-05-2016, online kopie) en *R4.06.03: Sous-structuration dynamique cyclique*: de
  Z-as als symmetrieas, DROITE/GAUCHE in trigonometrische richting, de interface
  AXE (alleen ND 0 en 1). Syntax nagelopen in de catalogi `mode_iter_cycl.py`,
  `rest_sous_struc.py`, `defi_interf_dyna.py` (code_aster 17.4) en de broncode
  `bibfor/algorith/ctetax.F90` (gitlab.com/codeaster/src, controle van de asknopen).
- EDF R&D (2025). *code_aster 17.4, testcases* sdlv134a, sdls04a/b, sdlv301a
  (cyclische substructurering).
- Leissa, A.W. (1969). *Vibration of Plates*. NASA SP-160, tabel 2.1 (ingeklemde
  cirkelvormige plaat). Niet lokaal ingezien; de waarden zijn nagerekend in de
  verificatie (CY-04).
- EDF R&D (2025). *code_aster 17.4, meldingencatalogus* (`lib/aster/code_aster/Messages/algeline2.py`,
  `algeline3.py`, `algeline5.py`): teksten van de genoemde ALGELINE-meldingen.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: §6.3
  Frequency (stress stiffening, modale effectieve massa), §6.6 Buckling, §6.9.2
  complexe akoestische modes, §7.8 Damper, §9.26 Rayleigh damping, §9.41 Cyclic
  symmetry, §11.9
  BucklingPlateNonlinear, §11.20–11.22 voorbeelden VibratingMembrane, Impeller en
  VibratingString.
- Southwell, R.V. (1932). On the analysis of experimental observations in problems of
  elastic stability. *Proceedings of the Royal Society of London A*, 135, 601–616. Niet
  lokaal ingezien; de methode is nagerekend in de verificatie (NK-03).
- Timoshenko, S.P. & Gere, J.M. (1961). *Theory of Elastic Stability*, 2nd ed. New
  York: McGraw-Hill, hoofdstuk 1 (staaf met beginkromming), §2.1, §2.3 en §9.2. Niet
  lokaal ingezien; de formules zijn nagerekend in de verificatie (BU-01, BU-02, BU-04,
  NK-03).
