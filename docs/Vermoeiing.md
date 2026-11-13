# Vermoeiing: schade en levensduur (Wöhler, rainflow, Miner, multiaxiaal, Manson-Coffin)

*English version: [Fatigue.md](en/Fatigue.md)*

De bridge rekent per knoop de **vermoeiingsschade** D en de **levensduur** uit een
belastingsverloop, met een Wöhler-curve (S-N-curve) of een rek-levensduurcurve
(Manson-Coffin) per materiaal en de regel van Miner. Voor een multiaxiale
spanningstoestand kan een **kritiekvlakcriterium** (Dang Van, Matake, Crossland of een
eigen formule) van Code-Aster de equivalente spanning geven. Mecway kent zelf geen
vermoeiing: de manual heeft geen S-N-curve, fatigue- of Wöhler-invoer (Mecway Ltd.,
2026; nagelopen). De invoer gaat daarom met `#ASTER`-regels in een vrij tekstveld van
Mecway ([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §1).

| Wat | Waar je het ziet |
|---|---|
| schade D per knoop (`damage`) | Mecway, veld *damage* (bij een tijdsverloop in elke tijdstap dezelfde waarde); bij schalen de grootste van boven- en onderzijde |
| levensduur per knoop (`life`): herhalingen van het signaal of blokkenspectrum tot D = 1 | Mecway, veld *life* |
| schalen: schade op de boven- en onderzijde (`damage_top`, `damage_bottom`) | Mecway, velden *damage_top*, *damage_bottom* (§1.8) |
| multiaxiaal: equivalente spanning van het criterium (`fatigue_eq`, Pa) en de criteriumwaarde (`fatigue_ratio`) | Mecway, velden *fatigue_eq*, *fatigue_ratio* (§1.7) |
| grootste schade (knoop, plaats, materiaal), levensduur daar, aantal knopen met D ≥ 1 | log en statusvak na de run |
| cycli van de knoop met de grootste schade (laag, min, max, amplitude, gemiddelde, aantal, N, schade) | tabel `<model>_<run-id>_vermoeiing.csv` in de werkmap |

Algemene werking van de bridge: [`Handleiding.md`](Handleiding.md).

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Volume-elementen** (hex, tet, wedge, piramide) en/of **schalen** (plaat- of
   schaalelementen, DKT/COQUE_3D). De schade van volumes komt uit de knoopspanning
   `SIGM_NOEU` (of de rek `EPSI_NOEU` bij een rekcurve), die van schalen uit de
   spanning op de boven- en onderzijde (§1.8). Balken krijgen geen schade (WARNING,
   §4).
2. **Een analyse met een belastingsverloop**:
   - *Static* (S30, `lin_static_3d`): de statische spanning is de spanning van "één
     eenheid last"; het verloop geef je als **blokken** of een **signaal** (§1.3);
   - *Nonlinear static* (L30, `nonlin_static_3d`) of *Dynamic response* zonder
     *Mode superposition* / D31 (`dyna_impl_3d`, `dyna_expl_3d`): de **tijdstappen van
     de run** zijn het signaal, per knoop. Geef de lasten een tijdstabel (bijv.
     heen en weer), zoals voor elke niet-lineaire of dynamische analyse.
   Andere analyses (modaal, harmonisch, spectrum, respons op modale basis,
   thermisch): WARNING, geen schade.
3. **Materialen met een naam**: de Wöhler-curve hoort bij een Mecway-materiaal
   (de naam in de boom onder *Materials*).

### 1.2 De Wöhler-curve: `#ASTER-WOHLER`

Eén regel per materiaal (`*` = alle materialen zonder eigen regel):

```
#ASTER-WOHLER Staal: S = [160, 200, 280, 400] MPa, N = [2e6, 1e6, 1e5, 1e4]
#ASTER-WOHLER Alu: Sf = 900 MPa, b = -0.1, Se = 60 MPa
#ASTER-WOHLER *: S = 40 MPa, N = 2e6, m = 3
#ASTER-WOHLER Gietstaal: Sf = 900 MPa, b = -0.09, ef = 0.3, c = -0.55
```

**S is de spanningsamplitude** σ_a = (σ_max − σ_min)/2, niet de spanningsvariatie
Δσ; zo rekent Code-Aster (`DEFI_MATERIAU` `FATIGUE` `WOHLER`; gemeten met szlz100a:
cyclus 600/−500 MPa geeft N(550 MPa)). Een curve met Δσ (bijv. Eurocode 3
detailcategorieën) deel je dus eerst door 2: Δσ_C = 80 MPa bij 2·10⁶ wordt
`S = 40 MPa, N = 2e6, m = 3`.

Vier vormen:

| Vorm | Sleutels | N(S) |
|---|---|---|
| tabel | `S = [..] <eenheid>`, `N = [..]` (S oplopend, N niet stijgend, minstens 2 punten) | interpolatie tussen de punten, standaard log-log (`INTERPOL = LOG`, zoals `DEFI_FONCTION INTERPOL='LOG'`) of lineair (`INTERPOL = LIN`) |
| macht | `S`, `N`, `m` (getallen) | N = N_ref · (S_ref / S)^m |
| Basquin | `Sf`, `b` (b < 0) | S = Sf · (2N)^b, dus N = ½ (S/Sf)^(1/b) |
| rek (Manson-Coffin) | `Sf`, `b`, `ef`, `c` (b, c < 0), eventueel `E` | ε_a = Sf/E · (2N)^b + ef · (2N)^c, N opgelost per cyclus (§1.9) |

Extra sleutels (hoofd- of kleine letters):

| Sleutel | Standaard | Betekenis | Wanneer aanpassen |
|---|---|---|---|
| `PROL_GAUCHE` (tabel) | `EXCLU` | onder de eerste S van de tabel: `EXCLU` geen schade (vermoeiingsgrens; Code-Aster's standaard, gemeten), `CONSTANT` N van het eerste punt, `LINEAIRE` het eerste stuk doorgetrokken (log-log bij `LOG`) | `LINEAIRE` als de curve geen vermoeiingsgrens heeft (bijv. lassen, corrosie, Miner "elementair") |
| `PROL_DROITE` (tabel) | `LINEAIRE` | boven de laatste S: het laatste stuk doorgetrokken (met een WARNING), of `CONSTANT` (N van het laatste punt) | tabel liever uitbreiden naar hogere spanningen |
| `Se` (macht, Basquin) | geen | geen schade onder deze amplitude (vermoeiingsgrens) | als de curve een knik naar oneindige levensduur heeft |
| `correctie` | `GEEN` | gemiddelde-spanningscorrectie: `GOODMAN` S_eq = S_a / (1 − S_m/S_u), `GERBER` S_eq = S_a / (1 − (S_m/S_u)²) | als de curve bij R = −1 (gemiddelde 0) gemeten is en de belasting een gemiddelde heeft (niet bij een rekcurve of een multiaxiaal criterium: ERROR) |
| `Su` | – | treksterkte (nodig bij `GOODMAN`/`GERBER`) | – |
| `E` (rekcurve) | E van het Mecway-materiaal | elasticiteitsmodulus in Sf/E | alleen als de curve bij een andere E gemeten is, of bij `*` met materialen van verschillende E (dan verplicht) |

Spanningen (`S`, `Sf`, `Se`, `Su`, `E`) hebben een eenheid nodig: Pa, kPa, MPa, GPa,
N/mm2, psi of ksi. N, m, b, ef en c zijn dimensieloos.

### 1.3 Het belastingsverloop

**(a) Blokken (lineair statisch):** per regel n cycli met een amplitude en een
gemiddelde als **factor op de statische spanning**:

```
#ASTER-BLOK 1.0, 0.0, 1e5
#ASTER-BLOK 0.5, 0.5, 2e6
```

Hier: 10⁵ cycli wisselend (±1 × de statische last) en 2·10⁶ cycli tussen 0 en 1 × de
statische last (amplitude 0,5, gemiddelde 0,5). Per knoop met equivalente spanning
σ_eq (§1.4): S_a = |a·σ_eq|, S_m = m·σ_eq. Alle blokken samen zijn één herhaling van
het spectrum (de volgorde telt bij Miner niet). Ook `#ASTER-BLOCK`. Met een
multiaxiaal criterium is elk blok een cyclus tussen (m − a) en (m + a) × de statische
spanningstensor (§1.7).

**(b) Signaal (lineair statisch):** een reeks lastfactoren; de bridge telt de cycli
met rainflow op signaal × σ_eq. Meer regels worden achter elkaar gezet.

```
#ASTER-SIGNAAL 0, 1, -0.5, 0.8, -1, 0
```

Ook `#ASTER-SIGNAL`. Tussenpunten op een rechte lijn hoeven niet: alleen de
keerpunten tellen.

**(c) De tijdstappen van de run (niet-lineair statisch, dynamisch):** zonder blokken
of signaal is de spanningsgeschiedenis per knoop over alle gearchiveerde tijdstappen
het signaal (in dynamica de uitvoertijden van Mecway's *timesteps*; kies ze fijn
genoeg om de pieken te vangen). De begintoestand (t = 0) telt mee. `#ASTER-BLOK`/
`-SIGNAAL` worden daar genegeerd (WARNING).

### 1.4 Opties: `#ASTER-VERMOEIING`

```
#ASTER-VERMOEIING spanning = VMIS_SG, telling = RAINFLOW, herhalingen = 1e4
```

| Sleutel (ook EN) | Standaard | Keuzes | Wanneer aanpassen |
|---|---|---|---|
| `spanning` (`stress`) | `VMIS_SG` | `VMIS_SG`: von Mises met het teken van het spoor (zoals `CALC_FATIGUE CUMUL_DOMMAGE`); `PRIN`: de hoofdspanning met de grootste absolute waarde, met teken | `PRIN` bij een (bijna) eenassige wisselende spanning waar von Mises de druk/trek-fase slecht volgt, of bij scheurgroei loodrecht op de grootste hoofdspanning (bros, lassen) |
| `rek` (`strain`) | `PRIN` | equivalente rek bij een rekcurve: `PRIN` de hoofdrek met de grootste absolute waarde (bij een staaf de rek in de lengterichting, zoals een rekgestuurde proef); `VMIS_SG`: √(2/3 e:e) van de rekdeviator, met het teken van het spoor | `VMIS_SG` bij een duidelijk multiaxiale rek; let op: bij elastische eenassige rek is die 2/3 (1 + ν) × de lengterek (0,87 bij ν = 0,3) |
| `telling` (`counting`) | `RAINFLOW` | `RAINFLOW`: het signaal wordt herhaald (begint bij de grootste absolute waarde, alleen gesloten cycli; `POST_FATIGUE COMPTAGE='RAINFLOW'`); `ASTM`: één doorgang volgens ASTM E1049 §5.4.4, de rest telt als halve cycli | `ASTM` als het signaal één keer optreedt (een enkele gebeurtenis); bij een herhalend bedrijf is `RAINFLOW` juist |
| `herhalingen` (`repeats`) | 1 | aantal keer dat het signaal/spectrum optreedt: D = herhalingen × D per herhaling | de ontwerplevensduur, bijv. aantal ritten of jaren × spectra per jaar |
| `criterium` (`criterion`) | `GEEN` | `DANG_VAN`, `MATAKE`, `CROSSLAND`, `FORMULE` (§1.7) | bij een multiaxiale, vooral niet-proportionele belasting |
| `a`, `b`, `c` | – | constanten van het criterium (§1.7); `b` met een spanningseenheid | – |
| `formule` (`formula`) | – | eigen equivalente spanning bij `criterium = FORMULE` (§1.7) | – |
| `belasting` (`loading`) | `PERIODIEK` | `PERIODIEK` (`PERIODIC`) of `NIET_PERIODIEK` (`NON_PERIODIC`), alleen met een criterium | `NIET_PERIODIEK` als het verloop meer dan één cyclus heeft (variabele amplitude) |
| `projectie` (`projection`) | `UN_AXE` | `UN_AXE` of `DEUX_AXES`: projectie van de schuifspanning op het kritieke vlak bij `NIET_PERIODIEK` (Code-Aster `PROJECTION`) | `DEUX_AXES` bij een sterk niet-proportionele schuifspanning (gemeten op sslv135a: gelijk) |

Ook `#ASTER-FATIGUE`.

### 1.5 Starten en resultaten

Start de bridge zoals altijd. Na de run:

- **Mecway:** de velden `damage` (D) en `life` (levensduur in herhalingen tot D = 1,
  begrensd op 10¹²; ook bij D = 0); bij schalen ook `damage_top`/`damage_bottom`,
  met een criterium ook `fatigue_eq`/`fatigue_ratio`. Bij een tijdsverloop hebben ze
  in elke tijdstap dezelfde waarde (de schade van het hele verloop). Mecway's API leest
  ze (headless nagelopen, statisch en dynamisch); de weergave in de GUI is NIET
  bekeken.
- **Statusvak en log:** grootste schade met knoop, plaats en materiaal, de levensduur
  daar, het aantal cycli per herhaling, het aantal knopen met D ≥ 1 (WARNING), bij
  een criterium de equivalente spanning en de grootste criteriumwaarde, en meldingen
  (§5).
- **Cyclustabel** `<model>_<run-id>_vermoeiing.csv`: per cyclus van de kritieke knoop
  `node`, `material`, `layer` (volume, top, bottom), `cycle`, `s_min`, `s_max`, `amplitude`, `mean`, `count`,
  `s_eq` (na de correctie), `n_failure` en `damage` (in Pa, bij een rekcurve als rek;
  `inf` = onder de vermoeiingsgrens). Met een criterium is elke rij een resultaat
  (het verloop, of een blok) met `s_eq` = SIGEQ; `s_min`/`s_max`/`mean` zijn dan `nan`.

### 1.6 Interpretatie

- **Miner:** D = Σ nᵢ/Nᵢ; bij D = 1 voorspelt de regel breuk. Miner negeert de
  volgorde van de belasting en is een gemiddelde: in de praktijk faalt een onderdeel
  tussen D ≈ 0,3 en 3. Normen eisen daarom vaak D ≤ 0,5 of een veiligheidsfactor op
  de spanning of op N.
- **Levensduur** = 1 / (D per herhaling): het aantal herhalingen van het signaal of
  spectrum. Bij één blok van n cycli is n × life het aantal cycli tot breuk.
- **Wöhler-curve en spanning:** de curve hoort bij de spanning die de bridge
  gebruikt: de nominale knoopspanning van het mesh (`SIGM_NOEU`, gemiddeld per knoop).
  In een kerf telt het mesh de spanningsconcentratie al mee; gebruik dan een curve
  van glad materiaal (niet een curve die de kerf al bevat). Een fijn mesh in de kerf
  is nodig: de schade gaat met de spanning tot de macht m (vaak 3 tot 10), dus 5 %
  spanningsfout geeft 15 tot 60 % schadefout.
- **Gemiddelde spanning:** zonder correctie telt alleen de amplitude. Goodman is
  conservatief voor de meeste metalen, Gerber minder. Code-Aster (en dus de bridge)
  neemt het teken van het gemiddelde mee: een gemiddelde **druk** verlaagt bij Goodman
  de equivalente amplitude (gemeten). Wil je dat voordeel niet, zet de correctie uit.
- **Multiaxiaal:** `VMIS_SG` en `PRIN` maken van een spanningstensor één getal per
  tijdstap. Dat is goed bij een proportionele belasting (de richtingen van de
  hoofdspanningen blijven gelijk). Bij een niet-proportionele belasting (bijv. buiging
  en torsie uit fase) of als de gemiddelde spanning via het kritieke vlak moet
  meetellen: een criterium (§1.7).
- **Plasticiteit:** de spanningsroute is hoog-cyclisch. Bij plastische rek per cyclus
  (laag-cyclisch, N < ~10⁴) is de rekroute (Manson-Coffin, §1.9) beter: de rek blijft
  bij vloeien gevoelig voor de belasting, de spanning niet.

### 1.7 Multiaxiaal: `criterium` (Dang Van, Matake, Crossland, formule)

```
#ASTER-WOHLER Staal: S = [138, 200, 295, 430] MPa, N = [1e6, 5e4, 1.2e4, 2e3]
#ASTER-VERMOEIING criterium = DANG_VAN, a = 0.3, b = 110 MPa, c = 1.5
```

Code-Aster zoekt per knoop het **kritieke vlak** (`CALC_FATIGUE TYPE_CALCUL=
'FATIGUE_MULTI'`, `OPTION='DOMA_NOEUD'`) en geeft een equivalente spanning SIGEQ,
die de bridge als amplitude op de Wöhler-curve van het materiaal zet (gemeten
in Code-Aster 17.4, sslv135a en VM-09):

| Criterium | Code-Aster | SIGEQ |
|---|---|---|
| `DANG_VAN` | `DANG_VAN_MODI_AC` (periodiek), `DANG_VAN_MODI_AV` (niet-periodiek), `CISA_PLAN_CRIT` `D_VAN_A` = a, `COEF_CISA_TRAC` = c | c · (Δτ/2 + a · max(P_max, 0)): Δτ/2 de schuifamplitude op het kritieke vlak, P_max de grootste hydrostatische spanning |
| `MATAKE` | `MATAKE_MODI_AC`/`_AV`, `MATAKE_A` = a, `COEF_FLEX_TORS` = c | c · (Δτ/2 + a · max(N_max, 0)): N_max de grootste normaalspanning op dat vlak |
| `CROSSLAND` | `FORMULE_CRITERE` met `AMPCIS` (zoals szlz107a), alleen periodiek | c · (√J₂,a + a · max(P_max, 0)): √J₂,a = √J₂ van de amplitudetensor (`AMPCIS`, gemeten) |
| `FORMULE` | `FORMULE_CRITERE`, `FORMULE_GRDEQ` | de eigen formule, bijv. `formule = '1.5*(DTAUMA + max(PHYDRM,0))'` (parameters van Code-Aster: `DTAUMA`, `PHYDRM`, `NORMAX`, `NORMOY`, `AMPCIS`, `RAYSPH`, `DSIGEQ`, `EPNMAX`, ...; de bridge controleert de namen) |

**Constanten kiezen** uit de vermoeiingsgrenzen σ₋₁ (wisselende trek-druk) en τ₋₁
(wisselende torsie) van het materiaal (de klassieke kalibratie: een zuivere torsie op
τ₋₁ en een trek-druk op σ₋₁ liggen dan beide precies op de grens):

| Criterium | b | a | c |
|---|---|---|---|
| Dang Van | τ₋₁ | 3 (τ₋₁/σ₋₁ − ½) | σ₋₁/τ₋₁ |
| Matake | τ₋₁ | 2 τ₋₁/σ₋₁ − 1 | σ₋₁/τ₋₁ |
| Crossland | τ₋₁ | 3 τ₋₁/σ₋₁ − √3 (szlz107a) | σ₋₁/τ₋₁ |

Met deze c is SIGEQ een "trek-equivalente" amplitude: bij zuivere wisselende trek of
torsie op de grens is SIGEQ = σ₋₁, zodat de gewone (trek-)Wöhler-curve past. Code-Aster
staat voor Dang Van en Matake 1 ≤ c ≤ 1,7321 toe (catalogus `defi_materiau.py`; buiten
dat bereik ERROR). a en c zijn verplicht; b is optioneel en geeft het veld
`fatigue_ratio` = SIGEQ / (c b) = (τ_a + a P)/b (bij `FORMULE`: SIGEQ / b): **> 1
betekent boven de vermoeiingsgrens van het criterium** (eindige levensduur), ≤ 1
oneindige levensduur volgens het criterium. Code-Aster's `D_VAN_B`/`MATAKE_B` tellen in
SIGEQ niet mee (gemeten: b = 2 en b = 100 geven dezelfde SIGEQ).

**Periodiek of niet** (`belasting`):

- `PERIODIEK` (standaard): het hele verloop (signaal, tijdstappen of één blok) is
  **één cyclus**: Code-Aster neemt het grootste schuifbereik over alle tijdstappen
  (`METHODE='CERCLE_EXACT'`). D per herhaling = Σ_blokken n / N(SIGEQ). Twee
  identieke periodes in het verloop geven dezelfde schade als één (gemeten), dus bij
  een signaal met meer cycli een WARNING.
- `NIET_PERIODIEK`: Code-Aster telt met rainflow op het kritieke vlak en geeft de
  schade (`ENDO1`, met de Wöhler-functie die de bridge uit de curve maakt); twee
  periodes geven twee keer de schade (gemeten). Geen `fatigue_eq`. Blokken kunnen hier
  niet (ERROR), Crossland ook niet. Let op: `MATAKE_MODI_AV` kiest een ander kritiek
  vlak dan `MATAKE_MODI_AC` (gemeten op sslv135a: schade 3,5·10⁻⁴ i.p.v. 9,1·10⁻⁵);
  `DANG_VAN_MODI_AV` gaf bij één proportionele cyclus dezelfde schade als periodiek.

**Bij lineair statisch** bouwt de bridge uit de statische spanning en rek een resultaat
met tijdstappen (`CREA_RESU`): het signaal × de statische toestand, of per blok de twee
toestanden (m − a) en (m + a). **Bij een niet-lineaire/dynamische run** kopieert hij
het resultaat met alle tijdstappen, omdat `CALC_FATIGUE FATIGUE_MULTI` de begintoestand
(`NUME_ORDRE` 0) anders overslaat (alarm `PREPOST4_27`; gemeten: een ramp 0 → 1 gaf de
halve amplitude, VM-08d).

**Interpretatie:** het kritieke vlak volgt de richting van de schuifspanning, dus
ook een draaiende hoofdspanning (niet-proportioneel) telt goed; de term a · P_max
(of N_max) neemt de gemiddelde spanning mee (trek ongunstig, druk telt niet, max(·, 0)).
Dang Van en Crossland gebruiken de hydrostatische spanning (vlakonafhankelijk), Matake
de normaalspanning op het vlak. Een gemiddelde-spanningscorrectie (`correctie`) erbij
kan dus niet (ERROR).

### 1.8 Schalen: boven- en onderzijde

Plaat- en schaalelementen krijgen schade op de **bovenzijde** (`damage_top`, de kant
van de positieve elementnormaal, Code-Aster `NIVE_COUCHE='SUP'`, in Mecway dezelfde
zijde als *vonmisesu1*) en de **onderzijde** (`damage_bottom`, `'INF'`, *vonmisesb*).
`damage` en `life` zijn de grootste schade van de twee. De bridge neemt de
spanning van `POST_CHAMP EXTR_COQUE` (zoals voor von Mises) als `SIEQ_NOEU`:
`spanning = VMIS_SG` gebruikt de component `VMIS_SG`, `PRIN` de `PRIN_i` met de
grootste absolute waarde. Dat zijn invarianten, dus het lokale assenstelsel van de
schaal speelt geen rol. Bij buiging hebben boven en onder hetzelfde bereik maar een
tegengesteld gemiddelde: met Goodman verschilt de schade (VM-10).

Niet bij schalen: een rekcurve en een multiaxiaal criterium (WARNING, schalen
overgeslagen). Balken: geen schade.

### 1.9 Rek-levensduur: Manson-Coffin

```
#ASTER-WOHLER Staal: Sf = 900 MPa, b = -0.09, ef = 0.3, c = -0.55
#ASTER-VERMOEIING rek = PRIN
```

De curve ε_a = Sf/E · (2N)^b + ef · (2N)^c (Basquin + Coffin-Manson, met E van het
materiaal; Sf = σ'f, ef = ε'f) geldt voor de **totale rekamplitude** ε_a = Δε/2. De
bridge leest de rek `EPSI_NOEU` per knoop en tijdstap (bij een niet-lineaire run ook
de plastische rek in de totale rek), maakt er per tijdstap één equivalente rek van
(`rek`), telt de cycli met rainflow en lost N per cyclus op (bisectie in ln 2N,
relatief < 10⁻¹³). Bij lineair statisch werken blokken en een signaal op de statische
rek, net als bij spanning.

Gebruik de rekroute voor laag-cyclische vermoeiing met plasticiteit (Mecway: *Nonlinear
static* met een plastisch materiaal en een heen-en-weer-last of opgelegde
verplaatsing). `EPSI_NOEU` is ook bij grote vervorming de lineaire (technische) rek
uit de verplaatsing, niet de logaritmische (gemeten met `GDEF_LOG`: 0,0060000 bij u/L
= 0,006, ln 1,006 = 0,005982); bij rekken van enkele procenten is het verschil
klein. Bij een heen-en-weer-plasticiteit werken beide: de standaard (plastisch volume →
`GDEF_LOG`) rekent het terugbelasten van de staaf van VM-11a door, en `deformation =
PETIT` (instelling *Vervorming*) geeft ongeveer dezelfde spanningen en plastische rekken
(13 nov 2026: ongeveer 0,1%, 3% van de spanning bij de nuldoorgang); het verschil is de
logaritmische maat in de spanning en de plastische rek.
Geen gemiddelde-
spanningscorrectie (Morrow, Smith-Watson-Topper) en geen `Se`: ERROR.

## 2. Overzicht van de sleutelwoorden

| Regel | Waar | Voorbeeld |
|---|---|---|
| `#ASTER-WOHLER materiaal: K=V, ...` | elke ondersteunde analyse (§1.1) | `#ASTER-WOHLER Staal: Sf = 900 MPa, b = -0.1, Su = 600 MPa, correctie = GOODMAN` |
| `#ASTER-VERMOEIING K=V, ...` (`#ASTER-FATIGUE`) | idem | `#ASTER-VERMOEIING herhalingen = 5`; `#ASTER-VERMOEIING criterium = MATAKE, a = 0.4, c = 1.6, belasting = NIET_PERIODIEK` |
| `#ASTER-BLOK a, m, n` (`#ASTER-BLOCK`) | alleen lineair statisch | `#ASTER-BLOK 1.5, 0.5, 1e4` |
| `#ASTER-SIGNAAL f1, f2, ...` (`#ASTER-SIGNAL`) | alleen lineair statisch | `#ASTER-SIGNAAL -2, 1, -3, 5, -1, 3, -4, 4, -2` |

Blokken en een signaal samen: ERROR (kies een van beide). Er zijn geen instellingen in
het hoofdvenster: de gegevens horen bij het model (zoals `#ASTER-LASBRON`).
Voorbeelden 19, 20, 35 en 36 in [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md).

## 3. Hoe de bridge vertaalt

1. `bridge_fatigue.py` leest de regels (IronPython) en zet na `CALC_CHAMP` een aanroep
   van `aster_fatigue.compute` (of, met een criterium, `CALC_FATIGUE` +
   `aster_fatigue.compute_multi`) in de `.comm` (Python 3 met numpy in de
   Code-Aster-job).
2. Uniaxiaal, per tijdstap: `SIGM_NOEU` van de volume-elsets (rekcurve: `EPSI_NOEU`,
   een extra `CALC_CHAMP DEFORMATION`) en `SIEQ_NOEU` van `res_sup`/`res_inf` voor
   schalen → equivalente spanning of rek per knoop (§1.4).
3. Per knoop: cycli (rainflow op de geschiedenis; bij blokken of een signaal op
   factor × σ_eq), dan N per cyclus uit de curve van het materiaal, met de correctie,
   en D = herhalingen × Σ n/N. Een knoop op de grens van twee materialen met een curve
   krijgt de grootste schade van de twee; bij schalen de grootste van boven en onder.
4. Multiaxiaal: per materiaal een eigen `DEFI_MATERIAU` (`ELAS`, `FATIGUE=_F(WOHLER=)`,
   `CISA_PLAN_CRIT`) en `AFFE_MATERIAU` (alleen voor `CALC_FATIGUE`), `CALC_CHAMP
   EPSI_NOEU` (`DOMA_NOEUD` vraagt `SIGM_NOEU` én `EPSI_NOEU`: zonder rek `<EXCEPTION>
   CALCULEL_29`, gemeten), het resultaat (`CREA_RESU`, §1.7) en `CALC_FATIGUE
   TYPE_CALCUL='FATIGUE_MULTI' OPTION='DOMA_NOEUD'` per resultaat. Periodiek: N uit
   max(`SIGEQ1`, `SIGEQ2`) met de curve van de bridge (Code-Aster's `NBRUP1` is op een
   geheel getal afgerond, gemeten 10946,0 bij N = 10946,1); niet-periodiek: D =
   `ENDO1` van Code-Aster. De Wöhler-functie voor Code-Aster (`DEFI_FONCTION`) krijgt
   de log-log-doortrekking als extra punten (tot N = 10¹² links en N = 1 rechts),
   omdat Code-Aster's `PROL 'LINEAIRE'` lineair in (S, N) doortrekt; onder de tabel
   met `EXCLU` geeft Code-Aster `NBRUP1` = 0 en `ENDO1` ≈ 10⁻³⁰⁸ (gemeten), wat de
   bridge als D = 0 leest.
5. `damage`, `life` (en de extra velden) gaan als knoopvelden mee in de
   resultaatexport (`aster_results_export`, `node_fields`); de cyclustabel en de
   regels `BRIDGE_VERMOEIING_*` in de `.mess` leest de bridge na de run (log,
   statusvak).

**Waarom niet `CALC_FATIGUE` voor het uniaxiale veld?** Code-Aster's `CALC_FATIGUE`
`TYPE_CALCUL='CUMUL_DOMMAGE'` rekent hetzelfde (rainflow op `VMIS_SG`, Wöhler, Miner)
maar alleen op een resultaat met tijdstappen, per element-knoop (`DOMA_ELNO_SIGM`),
zonder gemiddelde-spanningscorrectie, zonder blokken en met één materiaal
(`MATER`). De bridge rekent het zelf en is gelijk aan Code-Aster: `CALC_FATIGUE` op
hetzelfde resultaat geeft dezelfde schade (VM-04 en VM-06: verschil < 10⁻⁶) en
`POST_FATIGUE` op hetzelfde signaal ook (VM-03b, VM-05). Het kritieke vlak
(multiaxiaal) komt wel van Code-Aster.

**Gemeten verschillen met Code-Aster's vermoeiingsroutines** (Code-Aster 17.4, bij de
bouw nagelopen met `POST_FATIGUE`):

- `PROL_GAUCHE`/`PROL_DROITE='LINEAIRE'` trekt in `POST_FATIGUE`/`CALC_FATIGUE` de
  curve **lineair in (S, N)** door, ook bij `INTERPOL='LOG'`: N(50 MPa) = 1,8·10⁷ bij
  een tabel vanaf (100 MPa, 10⁷), en boven de tabel zelfs een **negatieve** schade
  (−8,6·10⁻⁶ bij 500 MPa). De functie zelf (`WH(50e6)` in Python) geeft wel log-log
  (1,57·10⁸). De bridge trekt bij `LOG` log-log door (een rechte lijn in het
  S-N-diagram).
- Boven de tabel met de standaard `PROL_DROITE='EXCLU'` stopt `POST_FATIGUE` met een
  fout; de bridge trekt standaard door, met een WARNING.
- Onder de tabel met `EXCLU` geeft `POST_FATIGUE` schade 0 (gemeten); de bridge ook.
- Multiaxiaal: Code-Aster zoekt de normaal van het kritieke vlak op een raster; bij
  Matake (N_max hangt lineair af van de richting) gaf dat SIGEQ +0,06 % t.o.v. de
  handberekening (VM-09c), bij Dang Van −2·10⁻⁶.

## 4. Wat niet kan

- **Balken:** geen schade; WARNING.
- **Schalen met een rekcurve of een multiaxiaal criterium:** niet gebouwd (WARNING,
  schalen overgeslagen); schalen werken uniaxiaal (§1.8).
- **Multiaxiaal per Gauss-punt** (`DOMA_ELGA`), **Papadopoulos** (`RAYSPH`, alleen via
  `criterium = FORMULE`), **Fatemi-Socie** (`FATESOCI_MODI_AV`), `VMIS_TRESCA`,
  `COEF_PREECROU`, `INST_INIT_CYCL` en eigen constanten per materiaal (a, b, c gelden
  voor alle materialen): niet gebouwd.
- **Rek-gebaseerd:** geen gemiddelde-spanningscorrectie (Morrow, SWT), geen
  vermoeiingsgrens, geen Taheri en Lemaitre-schade; de rek is `EPSI_NOEU` (ook bij
  grote vervorming de lineaire rek, gemeten).
- **Trillingsvermoeiing** op modale basis (`FATIGUE_VIBR`), random/spectrale
  vermoeiing (`POST_FATI_ALEA`) en een harmonische analyse als belasting: niet gebouwd;
  in respons op modale basis, harmonische en spectrumanalyse geeft de bridge een
  WARNING.
- **Een signaal of blokken in een niet-lineaire/dynamische run:** daar is het verloop
  van de run het signaal.
- **Schade per element-knoop** (`elementnodevariable`): alleen per knoop.
- **Volgorde-effecten** (niet-lineaire schadeaccumulatie, Marco-Starkey, ...): alleen
  Miner.
- **Een filter op kleine cycli** (`DELTA_OSCI` van `POST_FATIGUE`): niet gebouwd; met
  `PROL_GAUCHE = EXCLU` (standaard) tellen cycli onder de tabel toch niet.
- Resultaatroute `tabel`: de velden gaan niet naar Mecway (INFO); de log en de
  cyclustabel wel.

Zie ook KNOWN_BUGS 66.

## 5. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: #ASTER-WOHLER ...: verwacht 'materiaal: K=V, ...' | dubbele punt na de materiaalnaam vergeten | `#ASTER-WOHLER Staal: S = [..] MPa, N = [..]` |
| ERROR: ... materiaal '...' bestaat niet in het model | typefout of een andere naam dan in Mecway | de naam uit de Mecway-boom (*Materials*), of `*` |
| ERROR: ... heeft een spanningseenheid nodig | `S`, `Sf`, `Se`, `Su` of `E` zonder eenheid | bijv. `S = [200, 400] MPa` |
| ERROR: ... een tabel heeft S en N als lijsten van gelijke lengte | ongelijke lijsten of één punt | evenveel S- als N-waarden, minstens 2 |
| ERROR: ... S moet oplopen en N mag niet stijgen | punten in de verkeerde volgorde, of S en N verwisseld | S van laag naar hoog, N van hoog naar laag |
| ERROR: ... INTERPOL = LOG vraagt S > 0 en N > 0 | een punt met S = 0 of N = 0 | `INTERPOL = LIN` of het punt weglaten |
| ERROR: ... geef een tabel, een machtsvorm of Basquin | ontbrekende sleutels | §1.2 |
| ERROR: ... Manson-Coffin vraagt Sf, b, ef en c | `ef` of `c` zonder de rest | alle vier, §1.9 |
| ERROR: ... Se / correctie / Su kan niet bij een rekcurve | rekcurve met een vermoeiingsgrens of correctie | weglaten (§1.9) |
| ERROR: ... E geldt alleen voor een rekcurve | `E` bij tabel/macht/Basquin | `E` weglaten |
| ERROR: ... de rekcurve (Manson-Coffin) vraagt E | `*` voor materialen met verschillende E | `E = 210 GPa` in de regel, of een regel per materiaal |
| ERROR: ... correctie GOODMAN vraagt de treksterkte Su | `Su` ontbreekt | `Su = 500 MPa` |
| ERROR: #ASTER-VERMOEIING ...: onbekend / kies ... | onbekende sleutel of keuze | §1.4 |
| ERROR: ... criterium ... vraagt a en c | constante ontbreekt | §1.7 (tabel met de kalibratie) |
| ERROR: ... Code-Aster staat voor DANG_VAN/MATAKE 1 <= c <= 1,7321 toe | c buiten het bereik van `COEF_CISA_TRAC`/`COEF_FLEX_TORS` | c = σ₋₁/τ₋₁ (meestal 1,5–1,7) |
| ERROR: ... b = ...: verwacht een spanning met eenheid | `b` zonder eenheid | `b = 110 MPa` |
| ERROR: ... a, b, c geldt alleen met een multiaxiaal criterium | constanten zonder `criterium` | `criterium = DANG_VAN` erbij, of de constanten weglaten |
| ERROR: ... formule '...': onbekende naam ... | naam die Code-Aster niet kent | de parameternamen uit de melding (hoofdletters) |
| ERROR: ... CROSSLAND kan alleen periodiek | `belasting = NIET_PERIODIEK` met Crossland | `PERIODIEK`, of Dang Van/Matake |
| ERROR: Vermoeiing: criterium = ... rekcurve ... past daar niet bij | rekcurve met een criterium | een Wöhler-curve, of geen criterium |
| ERROR: Vermoeiing: criterium = ... heeft zijn eigen term voor de gemiddelde spanning | `correctie` met een criterium | `correctie` weglaten |
| ERROR: Vermoeiing: #ASTER-BLOK met belasting = NIET_PERIODIEK kan niet | blokken niet-periodiek | `PERIODIEK`, of een `#ASTER-SIGNAAL` |
| ERROR: #ASTER-BLOK ...: verwacht 'amplitude, gemiddelde, aantal' | geen drie getallen, of aantal ≤ 0 | `#ASTER-BLOK 1.0, 0.0, 1e5` (decimale punt) |
| ERROR: Vermoeiing: #ASTER-BLOK en #ASTER-SIGNAAL samen | beide gegeven | kies een van beide |
| WARNING: ... een lineair statische analyse heeft een belastingsverloop nodig | Wöhler-curve zonder blokken of signaal | `#ASTER-BLOK` of `#ASTER-SIGNAAL` toevoegen |
| WARNING: ... #ASTER-BLOK/#ASTER-SIGNAAL gelden alleen bij lineair statisch | blokken in een niet-lineaire/dynamische run | normaal: daar is het verloop van de run het signaal |
| WARNING: ... belasting = PERIODIEK telt een cyclus per signaal | signaal met meer cycli en een criterium | `belasting = NIET_PERIODIEK` of blokken |
| WARNING: ... criterium = ... werkt alleen op volume-elementen | criterium op schalen | voor schalen geen criterium (§1.8) |
| WARNING: ... de rekcurve ... werkt alleen op volume-elementen | rekcurve op schalen | een spanningscurve voor de schalen |
| WARNING: ... materiaal '...' zit niet in volume- of schaalelementen | curve op balken | alleen volumes en schalen (§4) |
| WARNING: Vermoeiing (#ASTER-WOHLER) werkt alleen bij ... | andere analyse | gebruik lineair statisch met blokken/signaal of een niet-lineaire/dynamische run |
| WARNING: Vermoeiing: schade D = ... >= 1 | breuk volgens Miner | lagere spanning, minder herhalingen of een andere curve |
| WARNING: ... een amplitude groter dan de hoogste S van de Wöhler-tabel | spanning buiten de tabel | tabel uitbreiden; nu is N doorgetrokken (`PROL_DROITE`) |
| WARNING: ... de gemiddelde spanning van een cyclus >= Su | statisch bezwijken | spanning of `Su` controleren; zo'n cyclus telt als N = 1 |
| WARNING: ... geeft de Wöhler-curve N < 1 | ver boven de curve (doorgetrokken) | tabel uitbreiden; daar geldt N = 1 |
| WARNING: ... de run stopte voor de eindtijd | niet-lineaire run niet geconvergeerd | eerst de convergentie oplossen ([Instellingen §4](Instellingen_contact_en_nietlineair.md#4-mijn-berekening-convergeert-niet)) |
| WARNING: Vermoeiing mislukt in de Code-Aster-job: ... | fout in de job (bijv. geen `SIGM_NOEU`) | zie de traceback in de `.mess` |

## 6. Verificatie

[`Verificatie.md`](Verificatie.md) hoofdstuk Vermoeiing (VM), module
`tests_vermoeiing.py`: constante amplitude (tabel, Basquin, machtsvorm met Se) en een
twee-niveau-spectrum (met Goodman en herhalingen) exact volgens Miner (≤ 10⁻⁶ t.o.v.
de handberekening, tolerantie 0,1 %); rainflow op het ASTM E1049-signaal: de cycli
van de norm exact en de schade ≤ 10⁻⁶; periodieke rainflow gelijk aan `POST_FATIGUE`;
szlz100a (Wöhler-tabel, Goodman, Gerber) en szlz105a (`CALC_FATIGUE`,
Downing-Socie) in 3D binnen 10⁻⁶ van `VALE_REFE`; een dynamische run gelijk aan
`CALC_FATIGUE` op hetzelfde resultaat; `VMIS_SG` en `PRIN` bij tweeassige spanning.
S8b: sslv135a in 3D (Matake en Dang Van, periodiek en niet-periodiek) gelijk aan
`VALE_REFE` (SIGEQ exact, `NBRUP1` 1,5·10⁻⁵ door de afronding, schade ≤ 10⁻¹⁴); de
begintoestand telt mee (VM-08d); trek + afschuiving met de hand: Dang Van en Crossland
≤ 2·10⁻⁵, Matake 0,26 % (zoekraster van Code-Aster, tolerantie 1 %), twee blokken
2·10⁻⁵; schaalplaat onder zuivere buiging: σ = 6m/t² en de schade boven/onder met
Goodman ≤ 10⁻¹¹; Manson-Coffin bij opgelegde plastische rek 2·10⁻⁹ en elastisch met
`rek = VMIS_SG` exact.

## 7. Bronnen

- ASTM International (2017). *ASTM E1049-85 (Reapproved 2017): Standard Practices for
  Cycle Counting in Fatigue Analysis*, §5.4.4 en fig. 6 (rainflow). West
  Conshohocken: ASTM. Niet lokaal ingezien; het voorbeeld en de tabel zijn algemeen
  bekend en nagerekend.
- Coffin, L.F. (1954). A study of the effects of cyclic thermal stresses on a ductile
  metal. *Transactions of the ASME*, 76, 931–950. Manson, S.S. (1953). *Behavior of
  materials under conditions of thermal stress* (NACA TN 2933). Niet ingezien; de
  vorm ε_a = σ'f/E (2N)^b + ε'f (2N)^c is de standaardvorm uit de handboeken.
- Crossland, B. (1956). Effect of large hydrostatic pressures on the torsional fatigue
  strength of an alloy steel. *Proc. Int. Conf. on Fatigue of Metals*, 138–149. Dang
  Van, K. (1973/1989), Matake, T. (1977): de kritiekvlakcriteria zoals Code-Aster ze
  implementeert; NIET ingezien, het gedrag van Code-Aster is gemeten (§1.7).
- EDF R&D. *code_aster 17.4*: catalogus `lib/aster/code_aster/Cata/Commands/`
  `post_fatigue.py`, `calc_fatigue.py`, `defi_materiau.py` (`FATIGUE`,
  `CISA_PLAN_CRIT`); testcases `szlz100a`, `szlz105a`, `sslv135a`, `sslv135c`,
  `szlz107a` (`share/aster/tests`). De U-documenten (U4.83.01 `POST_FATIGUE`, U4.83.02
  `CALC_FATIGUE`, R7.04.01 rainflow, R7.04.04 multiaxiale criteria) zijn niet lokaal
  aanwezig: NIET ingezien; het gedrag is met runs nagelopen (§1.7, §3).
- Miner, M.A. (1945). Cumulative damage in fatigue. *Journal of Applied Mechanics*,
  12, A159–A164.
- Mecway Ltd. (2026). *Mecway 33 manual* (`C:\Program Files\Mecway\manual.pdf`):
  geen vermoeiing.
