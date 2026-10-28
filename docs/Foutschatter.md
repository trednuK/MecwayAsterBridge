# Foutschatter (discretisatiefout per element)

*English version: [Error_estimator.md](en/Error_estimator.md)*

Bij een lineair statische analyse (Mecway *Static*, S30; bridge-analyse
`lin_static_3d`) schat de bridge met Code-Aster `CALC_ERREUR` hoe groot de
discretisatiefout van de mesh is: per element, per knoop en voor het hele model. Zo
zie je waar de mesh te grof is en waar verfijnen het meest oplevert.

| Wat | Waar je het ziet |
|---|---|
| geschatte fout per element (absoluut) | veld `errorestimate` in Mecway, per element (contour *per element*) en per knoop (gemiddeld) |
| geschatte fout per element, relatief (%) | veld `errorestimaterel` |
| globale relatieve fout (%) van het hele model | log en statusvak na de run |

De schatter is de **residu-schatter** van Code-Aster (`ERME`): per element telt hij
hoe slecht de berekende spanningen het evenwicht halen (in het element, als sprong
tussen buurelementen en ten opzichte van de last op de rand). Alleen
**volume-elementen** krijgen een schatting. Algemene werking van de bridge:
[`Handleiding.md`](Handleiding.md).

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Analysetype** *Static* (S30). Bij andere analyses doet de bridge geen
   foutschatting (§3.3).
2. **Volume-elementen** (hex8, hex20, tet4, tet10, wedge, pyramide). Schalen, balken en
   veren in hetzelfde model rekenen gewoon mee, maar krijgen geen schatting.
3. **Randvoorwaarden en lasten** zoals altijd. Vlakken zonder voorwaarde of last zijn
   voor de schatter vrije (spanningsloze) randen; de bridge zoekt ze zelf op (§2.2).
   Extra selecties zijn niet nodig.

### 1.2 In het hoofdvenster van de bridge

1. **Resultaten naar Mecway** = `liml` (tabblad Algemeen, standaard). Met `tabel`
   staat alleen de globale fout in de log, niet het veld.
2. Pagina (tabblad) **Statisch**, kopje *Controle*:

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Foutschatter (CALC_ERREUR, alleen volumes) | `error_estimator` | aan | uit als elke seconde telt of de extra velden in de `.liml` (vier variabelen) te groot worden; de schatting kost alleen elementberekeningen, geen extra oplossing van het stelsel |

Voor één model kan het ook met een `#ASTER-OPTIE`-regel in Mecway's custom input
(`#ASTER-OPTIE error_estimator = nee`, zie
[`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md)).

**Waarom standaard aan:** de schatting gebruikt de al berekende verplaatsingen
(alleen elementberekeningen, geen tweede oplossing van Ku = F) en geeft altijd een
indruk van de mesh-kwaliteit. Gemeten (tijdtabel in de `.mess`): de ingeklemde balk
van FS-01 met 41 000 hex8 (46 500 knopen) kostte voor de schatter 1,8 s van de 17,6 s
van de hele job (`CALC_ERREUR` 0,9 s, `SIGM_ELNO` 0,4 s, model en last 0,4 s; de
oplossing `MECA_STATIQUE` zelf 9,2 s). De schatter groeit lineair met het aantal
elementen, de oplossing sneller.

### 1.3 Starten en volgen

Klik *Starten*. Na afloop staat in de log en het statusvak bijvoorbeeld:

```
Foutschatter: globale relatieve fout 20.6% (residu-schatter ERME; deel volume
10.7%, sprongen 8.85%, rand 2.86%). Veld in Mecway: errorestimate (absoluut) en
errorestimaterel (%). Boven 20%: de mesh is grof; verfijn waar errorestimate groot is.
```

(FS-01 met n = 8.) De laatste zin voegt de bridge alleen boven 20% toe. In de log staat ook welke lasten
de schatter niet meeneemt (§2.3) en hoeveel vrije vlakken hij gevonden heeft.

### 1.4 Resultaten in Mecway bekijken

- Kies onder *Solution* het veld `errorestimate`. Met de contourweergave *per element*
  zie je de echte elementwaarde (constant per element); de knoopwaarde is het
  gemiddelde van de aansluitende elementen (`ERME_NOEU`).
- `errorestimate` is absoluut (eenheid: spanning x lengte^1,5, de norm over het
  element). Vergelijk de waarden onderling: waar ze het grootst zijn, is de mesh het
  grofst ten opzichte van de spanningsgradiënt.
- `errorestimaterel` is de fout van het element ten opzichte van zijn eigen
  spanningsniveau (%). Dat is groot waar de spanning klein is (bij een neutrale lijn,
  een vrij uiteinde); gebruik voor de plek van verfijnen vooral `errorestimate`.
- Mecway kent zelf geen foutveld; de namen zijn van de bridge, in hetzelfde formaat
  als de spanningen (`<nodevariable>` en `<elementnodevariable>`). Mecway toont ze onder
  *Solution* als `errorestimate` en `errorestimaterel`; de elementwaarde geeft een contour
  die per element constant is (in Mecway 33 nagelopen, 6 okt 2026).

### 1.5 Interpretatie: wat is groot, wat doe je ermee

De globale relatieve fout is 100 · η / sqrt(η² + ‖σ‖²), met η de geschatte fout en
‖σ‖ de norm van de spanningen over het hele model (§2.4). Het is een fout in de
**energienorm**, geen fout in een verplaatsing of een piekspanning:

- De schatting is ongeveer **2x de werkelijke energiefout** (verificatie FS-01:
  effectiviteitsindex 1,3 op het grofste en 2,0 tot 2,2 op de fijnere meshes).
- Een verplaatsing is veel nauwkeuriger dan de energiefout (ongeveer het kwadraat).
  FS-01, ingeklemde balk met hex8: schatting 37,9% / 20,6% / 10,7% bij een
  doorbuiging die 3,6% / 1,0% / 0,23% kleiner is dan de 3D-limiet.
- Spanningen (vooral piekspanningen) convergeren langzamer dan verplaatsingen.

Vuistregel (uit de verificatie, geen norm):

| Globale relatieve fout | Betekenis |
|---|---|
| < 5% | fijne mesh; verplaatsingen en gladde spanningen betrouwbaar |
| 5 tot 20% | bruikbaar voor verplaatsingen; controleer de spanningen waar het om gaat met een fijnere mesh |
| > 20% | grove mesh (melding in het statusvak); verfijn waar `errorestimate` groot is |

**Wat je ermee doet:** verfijn de mesh lokaal waar `errorestimate` het grootst is en
reken opnieuw. Met lineaire elementen halveert de fout ongeveer als de elementen
twee keer zo klein worden (orde 1); met kwadratische elementen (hex20, tet10, of
`LINE_QUAD`) wordt hij ongeveer vier keer zo klein (orde 2). Blijft de fout op één
plek groot bij elke verfijning, dan zit daar een **singulariteit**: een scherpe
inwendige hoek, een puntlast, de rand van een inklemming. Daar convergeert de
spanning niet; beoordeel de spanning op enige afstand (Saint-Venant) of rond de hoek
af in het model.

## 2. Hoe de bridge vertaalt

### 2.1 Code-Aster-commando's

Na `MECA_STATIQUE` en de gewone `CALC_CHAMP` (in de `.comm` onder *Foutschatter*):

```
model_err   = AFFE_MODELE(...)        # alleen de volume-elementen en hun randvlakken
fieldmat_err = AFFE_MATERIAU(...)     # zelfde materialen (en temperatuurveld)
load_err    = AFFE_CHAR_MECA(...)     # alle vlak- en volumelasten in één last,
                                      # plus PRES_REP 1e-14 op de vrije vlakken
u_err   = CREA_CHAMP(... DEPL van res, alleen DX, DY, DZ)
res_err = CREA_RESU(... DEPL, MODELE=model_err, CHAM_MATER=fieldmat_err)
res_err = CALC_CHAMP(reuse=res_err, CONTRAINTE=('SIGM_ELNO',))
res_err = CALC_ERREUR(reuse=res_err, OPTION=('ERME_ELEM', 'ERME_ELNO', 'ERME_NOEU'),
                      EXCIT=_F(CHARGE=load_err))
```

`aster_results_export.py` schrijft `ERME_NOEU` (knoop) en `ERME_ELNO` (per element,
alleen volume-elementen) als `errorestimate` (component `ERREST`) en
`errorestimaterel` (component `NUEST`) in de `.liml`. De globale fout drukt Code-Aster
zelf af in de `.mess` (blok *ESTIMATEUR D'ERREUR EN RESIDU EXPLICITE*); de bridge leest
dat blok.

Waarom een eigen model, last en resultaat (alles nagelopen met Code-Aster 17.4 bij de
bouw):

- **Eigen model:** met balken in het model stopt `CALC_ERREUR` met `<EXCEPTION>
  CALCUL_37` (*MECA_POU_D_E ne sait pas calculer l'option INIT_MAIL_VOIS*), en
  `CALC_ERREUR` kent geen `GROUP_MA`. Het model van de schatter heeft alleen de
  volume-elementen; de spanningen moeten daarop **overal** berekend zijn
  (`SIGM_ELNO` alleen op een deel gaf alarm `INDICATEUR_2` en `<EXCEPTION>
  CALCUL_29`).
- **Eigen last:** de schatter accepteert per soort last maar één last (twee lasten met
  `PRES_REP` gaven alarm `INDICATEUR_7` "Le choix PRESS apparaît au moins dans 2
  charges" en `<EXCEPTION> INDICATEUR_8`) en kent geen puntlasten (`FORCE_NODALE`:
  alarm `INDICATEUR_6` en `INDICATEUR_8`). De bridge zet daarom alle lasten die de
  schatter kent samen in één `AFFE_CHAR_MECA` (§2.3). De oplossing zelf gebruikt die
  last niet.
- **Eigen resultaat:** met `reuse` op `res` en een andere `EXCIT` weigert Code-Aster
  (`<EXCEPTION> CALCULEL_39`); zonder `reuse` zoeken `ERME_ELNO`/`ERME_NOEU` hun
  bronveld in het oude resultaat (`UTILITAI8_13`, `CALCUL_29`/`CALCUL_17`).
  `CREA_RESU` met de verplaatsingen van `res` werkt zonder alarm.

### 2.2 Vrije randen

De randterm van de schatter (σ·n − g, met g de last) rekent Code-Aster alleen op
vlakken waar een last op staat. Een vlak zonder last telt als **opgelegde
verplaatsing**: geen randterm. Bron: Code-Aster-testcase sslv153a ("ces bords sont
consideres comme a deplacement impose par le calcul des indicateurs d'erreur") en
sslv07a ("le calcul de ERME_ELEM est faux car des bords a contrainte nulle n'ont pas
ete definis"). De bridge zoekt daarom alle **vrije vlakken** van de volume-elementen
en geeft die een druk van 1e-14 Pa (groep `BRERRVRIJ`, ook in het model en in
`ORIE_PEAU`). Een druk van precies 0 werkt niet: dan bleef de randterm gelijk aan die
zonder de vlakken (gemeten); sslv153a gebruikt ook 1e-14.

Vrij is een vlak van precies één volume-element, dat:

- niet in een vlakselectie zit die een voorwaarde, last, contact of koppeling gebruikt
  (die vlakken hebben hun eigen last, of zijn opgelegd);
- niet met al zijn hoekknopen in een knoopselectie van een opgelegde verplaatsing
  zit (fixed, pinned, displacement, node rotation, frictionless, symmetry,
  compression only, elastic support);
- niet samenvalt met een schaalelement.

In de log: `INFO: Error estimator: n free faces of volume elements as group 'BRERRVRIJ'`.

### 2.3 Lasten in de schatter

| Last in Mecway | In de schatter |
|---|---|
| surface pressure, traction, force op vlakken van volume-elementen (`PRES_REP`, `FORCE_FACE`) | ja (constante waarde); `FORCE_FACE` met omgekeerd teken in de last van de schatter (zie onder) |
| gravity (`PESANTEUR`), centrifugal (`ROTATION`) | ja |
| force/moment op knopen (`FORCE_NODALE`), lasten op schalen en balken, line pressure op schaalranden (`FORCE_ARETE`), hydrostatic pressure (formule) | nee: voor de schatter een spanningsvrije rand (INFO in de log). Rond een puntlast is de geschatte fout dan groot; dat klopt: de spanning is daar singulier |
| fixed, displacement, symmetry, frictionless, ... op vlakken | geen randterm (zoals Code-Aster een opgelegde rand behandelt) |

**Teken van `FORCE_FACE`** (gemeten, Code-Aster 17.4): de randterm van `ERME` rekent
een `FORCE_FACE` als σ·n + g in plaats van σ·n − g. Een blok onder gelijkmatige trek van
100 MPa (exacte oplossing, hex20) gaf met de traction zoals in de oplossing een
geschatte fout van 15% (alleen de randterm), met het omgekeerde teken 0,000%; een druk
(`PRES_REP`) gaf 0,000%. De bridge zet `FORCE_FACE` daarom met omgekeerd teken in de
last van de schatter (`bridge_to_aster._erme_force_face`; de oplossing zelf gebruikt die
last niet). Alleen de normaalcomponent telt in de randterm ("TERME NORMAL"): een
tangentiële traction zoals bij FS-01 verandert de schatting niet (randterm 6,65 / 6,66 /
6,66% met FZ = +1e6 / −1e6 / 0). Een U-doc of de bron is hierover NIET ingezien.

Overlappen twee lasten van dezelfde soort op een vlak (bijv. twee drukken op
hetzelfde vlak), dan neemt de schatter er maar één mee (in een `AFFE_CHAR_MECA`
overschrijft de laatste de eerste; WARNING in de log). De oplossing telt ze wel op.

### 2.4 Wat de getallen zijn

Per element (componenten van `ERME_ELEM`, nagerekend in een run):

- `ERREST` = η_e, de geschatte fout van het element (→ `errorestimate`);
- `SIGCAL` = de norm van de spanning over het element;
- `NUEST` = 100 · η_e / sqrt(η_e² + SIGCAL²) in % (→ `errorestimaterel`).

Globaal: η = sqrt(Σ η_e²), ‖σ‖ = sqrt(Σ SIGCAL²), relatieve fout = 100 · η /
sqrt(η² + ‖σ‖²). De `.mess` splitst de fout in het volumedeel (evenwicht in het
element), de sprongen tussen elementen en de randterm.

## 3. Bijzonderheden

### 3.1 Elementtypen

Getest met hex8 (`3D`), hex8 met `LINE_QUAD`, hex20, en een gemengd blok van
hexa/penta/pyram/tetra (sslv153a, `LINE_QUAD`). Een model met schalen en balken naast
volumes (een gemengd testmodel, met `lin_solver_resi` 0,01: dat model
stopt ook zonder schatter met `FACTOR_57`) rekent: alleen de volumes krijgen een
schatting. Een overgang volume → schaal of balk is voor de schatter een vrije rand
(de kracht van de schaal of balk telt niet als last); daar is de geschatte fout groter
dan werkelijk. Tet4/tet10 en wedge zitten in de Code-Aster-testcases (sslv153a,
sslv111f), niet apart in de bridge-verificatie.

### 3.2 Thermische spanning

Met een temperatuurbelasting (`thermalstress`) rekent de schatter met dezelfde
temperatuur (het materiaalveld met `AFFE_VARC`). Gecontroleerd met TH-03b (staaf
ingeklemd, uniform opgewarmd, constante spanning): globale fout 0,000%. Bij een
(vrijwel) spanningsloos model, zoals vrije uitzetting (TH-03a), is de relatieve fout
betekenisloos (ruis gedeeld door ruis: daar 64% bij een absolute fout van 7e-8).
Andere gevallen met thermische spanning: NIET geverifieerd.

### 3.3 Wat niet kan

- **Niet-lineair statisch, dynamica, modaal, knik:** geen foutschatting. De
  residu-schatter van Code-Aster is bedoeld voor lineaire elasticiteit (sslv07a noemt
  het bij `STAT_NON_LINE` "stricto sensu faux" als de randen ontbreken); met grote
  vervormingen (`GROT_GDEP`, de standaard) en lasten in de tijd zou de schatting per
  stap een eigen last vragen. De instelling bestaat daar niet; een `#ASTER-OPTIE
  error_estimator` geeft daar een ERROR (onbekende optie).
- **Thermisch** (`ERTH_ELEM`): niet gebouwd.
- **Schalen en balken:** geen schatting (de bridge gebruikt `ERME` alleen op volumes).
- **Zienkiewicz-Zhu** (`ERZ1_ELEM`/`ERZ2_ELEM`) en de doelgerichte schatter
  (`QIRE_ELEM`, vraagt een tweede, duaal probleem) worden niet aangeboden (de
  Code-Aster-testcases met ZZ zijn grotendeels 2D; sslv111f gebruikt `ERZ1_ELEM` in
  3D).
- **Adaptieve verfijning**: met Mecway's eigen verfijning, zie §6; thermisch en niet-lineair met HOMARD, zie §7.

## 4. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| INFO: Foutschatter: niet meegenomen lasten (FORCE_NODALE, ...) | puntlasten of lasten op schalen/balken | normaal; rond die lasten is de geschatte fout groter |
| WARNING: Foutschatter: het model heeft geen volume-elementen | alleen schalen/balken | geen schatting mogelijk; zet de instelling uit om de melding te vermijden |
| WARNING: Foutschatter: ... op overlappende vlakken | twee drukken/tractions op hetzelfde vlak | de schatter neemt er één mee; voor een betrouwbare schatting de lasten samenvoegen in Mecway |
| WARNING: Foutschatter: geen last of vrij vlak voor CALC_ERREUR | alle randen opgelegd en geen vlaklast | geen schatting |
| WARNING: Foutschatter (error_estimator) werkt alleen bij lineair statisch | instelling bij een andere analyse | normaal; geen schatting |
| INFO: Foutschatter: het veld gaat alleen via result_route 'liml' | route `tabel` | zet *Resultaten naar Mecway* op `liml` |
| statusvak: "Boven 20%: de mesh is grof" | grove mesh | verfijn waar `errorestimate` groot is (§1.5) |

De Code-Aster-meldingen bij een eigen `CALC_ERREUR` (bijv. in `#ASTER-POST`-code) staan
in [`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md) (`INDICATEUR_2/6/7/8`,
`CALCULEL_39`, `RESULT1_40/65`, `CALCUL_37`).

## 5. Verificatie

[`Verificatie.md`](Verificatie.md) hoofdstuk Foutschatter (FS):

- **FS-01** ingeklemde balk, hex8 n = 1 … 16: de globale fout daalt monotoon (79,5 /
  61,1 / 37,9 / 20,6 / 10,7%); de absolute schatting η met orde 0,88 / 0,96 / 0,96
  (verwacht 1); effectiviteitsindex 1,3 … 2,2; grootste fout bij de inklemming.
- **FS-02** dikwandige cilinder (Lamé), hex20 n = 1 … 8: orde 1,87 / 1,95 / 1,91
  (verwacht 2); grootste fout aan de binnenwand.
- **FS-03** Code-Aster-testcase sslv153a via de bridge: `ERREST` in knoop MESURE
  9339,36 (TEST_RESU 9339,361119), globale fout 51,518%, gelijk aan de testcase.

## 6. Adaptieve verfijning

Met de instelling **Adaptieve verfijning** rekent de bridge, verfijnt het model in
Mecway waar de geschatte fout het grootst is (Mecway's eigen *Refine x2*,
`mw.refine_x2`), en rekent opnieuw, tot de globale relatieve fout onder het doel
komt of een grens bereikt is. Alles gebeurt in het open Mecway-model: selecties,
lasten en randvoorwaarden op vlakken, materialen en onderdelen verfijnt Mecway mee.
Code: `Scripts/bridge_adapt.py`, de lus in `MecwayAsterBridgeMain.main()`
(`_adapt_step`).

### 6.1 Werkwijze in Mecway stap voor stap

1. Maak het model zoals in §1.1: *Static* (S30), volume-elementen, bij voorkeur
   **hex20** (§6.5). Een grof mesh is goed: de lus verfijnt zelf.
2. Leg **randvoorwaarden en lasten op vlakken** (vlakselecties), niet op een
   knoopselectie met meerdere knopen: Mecway neemt nieuwe knopen niet op in een
   knoopselectie (§6.4). Een puntlast of een oplegging op één knoop mag.
3. Hoofdvenster, pagina **Statisch**, kopje *Adaptieve verfijning*: zet
   *Adaptieve verfijning (Mecway refine_x2)* aan en kies het doel (§6.2). De
   foutschatter moet aan staan (standaard), *Resultaten naar Mecway* = `liml`
   (standaard).
4. Klik *Starten*. Per lus start Code-Aster en wacht de bridge zoals altijd tot de
   berekening klaar is (statusvenster, of OK met *Wachten op Code-Aster* = `confirm`;
   [Handleiding §2](Handleiding.md#2-werkwijze) stap 5). *Stoppen...* beëindigt ook de lus.
   Daarna laadt de bridge de resultaten, kiest de
   elementen, verfijnt, slaat het model op en start de volgende lus.
5. Na de laatste lus staan de resultaten van het fijnste mesh in Mecway. Het
   statusvak toont per lus het aantal elementen, de globale fout en het aantal
   verfijnde elementen, en waarom de lus stopte.
6. Het **oorspronkelijke model** (met zijn resultaten) staat als
   `<model>_<run_id>_voor_verfijning.liml` in de werkmap; Mecway's verfijning is via
   de API niet ongedaan te maken. Het model zelf is na de lus verfijnd en opgeslagen.

Voor één model kan het ook met `#ASTER-OPTIE`-regels, bijv.
`#ASTER-OPTIE adapt_refine = ja` en `#ASTER-OPTIE adapt_target_error = 1.5`.

### 6.2 Instellingen

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Adaptieve verfijning (Mecway refine_x2) | `adapt_refine` | uit | aan voor de lus; elke lus is een extra run |
| Doel: globale relatieve fout [%] | `adapt_target_error` | 2 | 2 tot 5 voor verplaatsingen en gladde spanningen; 1 tot 1,5 voor een piekspanning (AD-02: Kt binnen 2% bij 1,1%, nog −5,9% bij 1,8%) |
| Max. aantal verfijningslussen | `adapt_max_loops` | 5 | hoger als het doel nog niet bereikt is en het model klein blijft |
| Keuze van de elementen | `adapt_select` | `dorfler` | `fraction` of `factor` als je een vaste hoeveelheid per lus wilt |
| Keuzewaarde | `adapt_fraction` | 0,5 | dorfler: kleiner (0,3) = minder elementen per lus en meer lussen; fraction: bijv. 0,1 (10% van de elementen); factor: bijv. 2 (fout > 2 x het gemiddelde) |
| Ook de buren verfijnen (dunne elementen) | `adapt_neighbours` | uit | aan bij dunne elementen (dikte veel kleiner dan de breedte), zie §6.5 |
| Max. aantal elementen na verfijnen | `adapt_max_elements` | 200000 | naar het geheugen van de computer; zet ook de geheugenlimiet van de run (`memory_limit`) hoog genoeg |

**Keuze `dorfler`** (Dörfler 1996, *bulk criterion*): de elementen met de grootste
fout η_e, net zoveel tot ze samen de fractie 0,5 van Σ η_e² dragen. Zo verfijnt elke
lus waar de fout echt zit, ongeacht hoeveel elementen dat zijn.

**Waarom deze standaarden:** het doel 2% is een energienorm die voor verplaatsingen en
gemiddelde spanningen ruim voldoende is (§1.5); 5 lussen maken een grof mesh ~1000x
zo fijn op de kritieke plek (2⁵ per richting); 200 000 elementen rekent Code-Aster
op een gewone pc (lus 6 van de plaat met gat: 48 776 hex20 met de standaardgeheugenlimiet
2048 MB; 156 019 hex20 gaf geen resultaat meer).

### 6.3 Interpretatie

- De lus stuurt op de **globale relatieve fout in de energienorm** (§1.5). Een
  verplaatsing is al bij een paar procent nauwkeurig; een **piekspanning** vraagt
  een kleinere globale fout. Plaat met gat (AD-02): globale fout 2,4 / 1,8 / 1,1% bij
  Kt −5,3 / −5,9 / +0,8%.
- De verfijning concentreert zich waar de spanning snel verandert: in AD-02 lag 98%
  van alle verfijnde elementen binnen 3r van het gat.
- **Minder elementen dan uniform**: AD-02 haalt Kt binnen 2% met 15 810 elementen;
  globaal Refine x2 (alles verfijnen) heeft er 49 152 nodig.
- Een piekspanning hoeft niet elke lus beter te worden (AD-02 lus 3 → 4: −5,3 → −5,9%)
  zolang de elementen op de piek zelf nog niet verfijnd zijn; de globale fout daalt
  wel elke lus.
- Bij een **singulariteit** (scherpe inwendige hoek, puntlast, rand van een
  inklemming) blijft de lus daar verfijnen zonder dat de spanning convergeert (§1.5);
  beoordeel de spanning daar niet, of rond de hoek af.

### 6.4 Wat Mecway's verfijning doet (gemeten)

Headless nagelopen met `mecway.exe <model> script <script.py>` (Mecway 33):

- Een gekozen element wordt 2 x 2 x 2 elementen van dezelfde vorm; de buren krijgen
  **overgangselementen** (hex8 → hex8 + pyr5 + tet4; hex20 → hex20 + pyr13 + tet10;
  tet10 → tet10 + pyr13 + wedge15). Het mesh blijft conform: geen hangende knopen (elk
  binnenvlak hoort bij twee elementen, nagelopen op alle lussen van AD-02).
- **Vlakselecties** (en dus vlaklasten en -voorwaarden), **elementselecties** en
  **onderdelen** (elset en materiaal) gaan mee naar de nieuwe elementen.
- **Knoopselecties niet**: na verfijnen hoort een nieuwe knoop op een rand of vlak van
  een knoopselectie er niet bij (8 → 8 knopen na globale verfijning van een vlak van
  hex20). Daarom stopt de lus met een ERROR als een knoopselectie met een last of
  voorwaarde op een ribbe ligt die verfijnd zou worden (AD-03).
- Nieuwe knopen liggen op de elementgeometrie: bij **hex20/tet10** volgt een gebogen
  rand de kwadratische vorm (een gatrand bleef binnen 5e-4 r van de cirkel); bij
  **hex8/tet4** liggen ze op de rechte ribbe, zodat een gebogen rand de veelhoek van
  het grove mesh blijft (de spanning aan zo'n rand convergeert dan niet naar die van
  de echte vorm).
- Elementen en knopen worden hernummerd; de oude oplossing blijft in de `.liml`
  staan tot de volgende run hem vervangt.
- Middenknopen van pyr13, tet10 en wedge15 uit de verfijning liggen in de
  knoopvolgorde die `bridge_mesh` aanneemt (nagelopen op de AD-02-lussen: een
  verkeerde volgorde zou alle middenknopen van een element verschuiven; in lus 5 wijken
  bij 90 van de 15 810 elementen 1 of 2 middenknopen meer dan 1/4 van de ribbelengte af
  van het ribbemidden: sterk gekromde overgangsribben, geen volgordefout).

### 6.5 Elementvorm en slechte overgangen

Na een paar lussen kunnen Mecway's overgangen slechte elementen maken. Gemeten op de
plaat met gat (`tests_adaptief.py`, buiten de regressie):

| Mesh | Resultaat |
|---|---|
| hex20, elementen ongeveer even lang als breed (AD-02, plak in vlakke rek) | 5 lussen, globale fout daalt elke lus, Kt +0,8%; het mesh wordt vooral overgangselementen (lus 5: 1452 hex20, 6831 tet10, 3799 pyr13, 3728 wedge15) en de slechtste hex zakt naar 0,04 (WARNING vanaf lus 4), zonder dat de fout stijgt |
| hex20, dunne plaat (dikte 1/40 van de elementbreedte) | lus 2: bijna platte hex20 (geschaalde Jacobiaan 0,015), globale fout stijgt van 3,7 naar 19,6%: de lus stopt (WARNING); met *Ook de buren verfijnen* pas in lus 4 (Kt −2,6% bij 8415 elementen) |
| tet10 (Kuhn-splitsing van hetzelfde mesh, dik en dun) | na de eerste lus stijgt de globale fout (5,8 → 6,7%): de lus stopt; doorrekenen gaf na 5 lussen Kt −5,4% bij 16 307 elementen |

Daarom: gebruik **hex20** met elementen die niet veel dunner dan breed zijn; zet bij
een dunwandig model *Ook de buren verfijnen* aan. De bridge meldt hex-elementen met een
geschaalde Jacobiaan < 0,1 (WARNING) en stopt de lus als de globale fout niet meer
daalt. Bij een tet-mesh: verfijn liever met Mecway's automesh (*Point/Surface
refinement*) op de plek waar `errorestimate` groot is.

### 6.6 Wat niet kan

- Alleen **lineair statisch** (de foutschatter bestaat alleen daar, §3.3).
- Alleen **volume-elementen** worden gekozen; schalen en balken verfijnt de lus niet.
- **Knoopselecties** met een last of voorwaarde op een te verfijnen ribbe: ERROR (zet
  de voorwaarde op vlakken).
- **Thermisch en niet-lineair statisch**: daarvoor is er de verfijning met HOMARD
  binnen de Code-Aster-job, zie §7 (het Mecway-model blijft daar ongewijzigd).
- Afgrenzen (*unrefine*) doet de lus niet.

Deze grenzen staan ook in `KNOWN_BUGS.md` (punt 65).

### 6.7 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| Adaptieve verfijning: doel bereikt | globale fout <= doel | klaar |
| Adaptieve verfijning: maximaal aantal lussen bereikt | doel nog niet gehaald | meer lussen (`adapt_max_loops`) of een lager doel accepteren |
| WARNING: Adaptieve verfijning gestopt: de globale fout daalt niet meer | singulariteit, een last die de schatter niet kent (§2.3), of slechte overgangselementen (§6.5) | bekijk `errorestimate` in Mecway; rond de hoek af, gebruik hex20, of zet *Ook de buren verfijnen* aan |
| WARNING: ... element(en) met een slechte vorm | platte hex-elementen na verfijnen | zie §6.5; begin opnieuw met het oorspronkelijke model (`_voor_verfijning.liml`) |
| ERROR: ... de knoopselectie(s) ... liggen op ribben die verfijnd worden | voorwaarde/last op een knoopselectie | leg ze op een vlakselectie |
| Adaptieve verfijning gestopt: ... zou het model ongeveer ... elementen hebben | grens `adapt_max_elements` | hogere grens (en `memory_limit`), of een ruimer doel |
| WARNING: Adaptieve verfijning (adapt_refine) vraagt een lineair statische analyse met de foutschatter | andere analyse of foutschatter uit | `error_estimator` aan, analyse `lin_static_3d` |
| Adaptieve verfijning: alleen met resultaatroute 'liml' | route `tabel` | *Resultaten naar Mecway* = `liml` |
| Adaptieve verfijning gestopt: geen globale foutschatting in de .mess | de schatter draaide niet (geen volumes, geen last) | zie §4 |
| ERROR: Mecway-verfijning (refine_x2) mislukt | Mecway weigerde | zie de log; verfijn met de hand in Mecway |

### 6.8 Verificatie

[`Verificatie.md`](Verificatie.md) hoofdstuk Adaptieve verfijning (AD): plaat met gat
(d/W = 0,2) onder trek, Kt tegen Peterson (2,519). Uniform (AD-01) −27,2 / −14,3 / −6,3 /
−2,5 / −0,75 / −0,14% voor 12·4^k elementen in het vlak; de lus (AD-02, headless Mecway)
Kt +0,82% met 15 810 elementen, uniform Refine x2 tot 2% 49 152; AD-03: de lus stopt bij
een knoopselectie-voorwaarde.

## 7. Adaptieve verfijning met HOMARD (thermisch, niet-lineair statisch)

Met de instelling **Adaptieve verfijning (HOMARD, binnen de job)** verfijnt Code-Aster het
mesh zelf, in één run: oplossen, foutindicator, de elementen met de grootste fout
verfijnen met HOMARD (`MACR_ADAP_MAIL`), opnieuw oplossen, tot het doel of een grens. Het
resultaat komt daarna terug op het **oorspronkelijke Mecway-mesh**; het Mecway-model zelf
verandert niet. Dit werkt bij **thermisch** (Mecway T30/T31, `ther_3d`) en **niet-lineair
statisch** (L30, `nonlin_static_3d`), waar de foutschatter van §1 niet bestaat. Lineair
statisch houdt de Mecway-route van §6. Code: `Scripts/bridge_homard.py` (bridge) en
`Scripts/aster_adapt.py` (in de job); onderzoek: stap S35a in `STAPPENPLAN.md`.

### 7.1 Werkwijze in Mecway stap voor stap

1. Bouw het model met **volume-elementen** (bij voorkeur hex20; tet10, wedge en pyramide
   kan ook). Een grof mesh is goed: de lus verfijnt zelf.
2. Zet **lasten en voorwaarden op vlakselecties** (temperatuur, warmtestroom, convectie,
   symmetrie, frictionless, inklemming, druk, traction). Een knoopselectie met één knoop
   mag; een knoopselectie met meer knopen niet (§7.7).
3. Hoofdvenster, pagina **Thermisch** of **Niet-lineair**, kop *Adaptieve verfijning*:
   zet *Adaptieve verfijning (HOMARD, binnen de job)* aan en kies het doel (§7.2).
4. Klik *Start*. De bridge herkent de gekromde randen (§7.4) en schrijft de lus in
   `study.comm`; Code-Aster rekent alle lussen in één run (geen OK per lus).
5. Na de run staan de resultaten op het Mecway-mesh. Het statusvenster toont per lus het
   aantal elementen en de globale fout, en waarom de lus stopte. Met `med_export` of
   `vtu_export` staat het verfijnde resultaat zelf in `<model>_<run_id>_verfijnd.rmed`
   (ParaView, MWHub Post).

![Adaptieve verfijning op de pagina Thermisch](img/thermal_adapt_homard_nl.png)

1. *Adaptieve verfijning (HOMARD, binnen de job)* (`adapt_homard`): de lus aan.
2. *Doel: globale fout ZZ [%]* (`adapt_homard_target`).
3. *Max. aantal verfijningslussen* (`adapt_homard_max_loops`).
4. *Max. aantal elementen na verfijnen* (`adapt_homard_max_elements`).

Op de pagina *Niet-lineair statisch* staan dezelfde vier instellingen.

Voor één model kan het ook met `#ASTER-OPTIE`, bijv. `#ASTER-OPTIE adapt_homard = ja` en
`#ASTER-OPTIE adapt_homard_target = 0.3`.

### 7.2 Instellingen

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Adaptieve verfijning (HOMARD, binnen de job) | `adapt_homard` | uit | aan voor de lus; elke lus is een volledige oplossing |
| Doel: globale fout ZZ [%] | `adapt_homard_target` | 1 | 1 voor het globale veld; voor een piekwaarde veel lager: plaat met gat binnen 1% bij 0,15% (thermisch, AD-10) en 0,4% (plasticiteit, AD-11) |
| Max. aantal verfijningslussen | `adapt_homard_max_loops` | 5 | hoger als het doel nog niet gehaald is (AD-10/11: 8 à 9 lussen vanaf 12 elementen) |
| Max. aantal elementen na verfijnen | `adapt_homard_max_elements` | 200000 | naar het geheugen; ook `memory_limit` |

**Vast** (geen instelling): Dörfler-keuze 0,5 per lus (de elementen met de grootste fout
die samen de helft van Σ η² dragen, zoals §6.2); de lus stopt bij het doel, het maximum
aantal lussen of elementen, of als de fout **twee lussen achter elkaar** boven de beste
waarde ligt. Eén stijgende lus stopt de lus niet: HOMARD's overgangselementen laten de
globale fout soms even stijgen (AD-10: 1,92 → 1,71 → 0,83 → 1,24 → 0,62 %).

**Waarom deze standaard:** 1% is een ruim doel voor het globale veld; een lager doel kost
snel veel elementen. Zie §7.6 voor een piekwaarde.

### 7.3 Hoe de bridge het vertaalt

![HOMARD-lus binnen de job](img/homard_loop.svg)

1. Grof Mecway-mesh, zoals de bridge het schrijft.
2. Oplossen in Code-Aster (`THER_LINEAIRE`/`THER_NON_LINE`, of `STAT_NON_LINE` met de hele
   lastgeschiedenis) op het huidige mesh.
3. Foutindicator per element (ZZ: het verschil tussen de spanning of warmtestroom per
   element en het gemiddelde in de knopen); de elementen boven de rode lijn (Dörfler 0,5)
   worden gekozen.
4. HOMARD verfijnt de gekozen elementen (`MACR_ADAP_MAIL`), met overgangselementen
   (pyramides, tetraëders) zodat het mesh conform blijft, en legt nieuwe knopen op de
   gekromde randen (§7.4).
5. Het verfijnde mesh; terug naar 2 tot het doel of een grens bereikt is.
6. Na de laatste lus: het resultaat met `PROJ_CHAMP` op het oorspronkelijke Mecway-mesh,
   zodat het naar Mecway kan (§7.5).

Details:
- **Indicator:** de bridge rekent een eigen ZZ-indicator (Zienkiewicz-Zhu): per element
  η² = V · gemiddelde over de knopen van |σ_element − σ_knoop|², globaal
  100 √(Σ η² / (Σ η² + Σ ‖σ‖²)) %, een L2-norm van de spanning (thermisch: de
  warmtestroom), niet de energienorm van §1.5. De indicatoren van Code-Aster zelf stoppen
  op HOMARD's overgangselementen (S35a, gemeten: `ERTH_ELEM` kan niet op `PYRAM13` en niet
  na een stationaire `THER_NON_LINE`; `ERZ1_ELEM` faalt op een HOMARD-`TETRA10`, `ERZ2_ELEM`
  met randelementen).
- **Niet-lineair:** elke lus rekent de **hele lastgeschiedenis** opnieuw op het nieuwe
  mesh. Velden tussen stappen overzetten (`MAJ_CHAM`) faalde voor de plastische
  toestand op HOMARD's meshes (S35a); opnieuw rekenen is betrouwbaar, kost wel per lus een
  volledige analyse. De indicator gebruikt het laatste tijdstip.
- **Groepen:** HOMARD verfijnt elementgroepen (componenten, vlakselecties) mee, maar
  knoopgroepen houden alleen hun oude knopen en de knopen worden hernummerd. Daarom zet
  de bridge in deze modus **symmetrie op volumevlakken** om naar `FACE_IMPO DNOR = 0` op
  het vlak (net als frictionless) in plaats van `LIAISON_OBLIQUE` per knoopgroep.
- **Pyramides in het Mecway-mesh:** HOMARD weigert ze zonder `ELEMENTS_ACCEPTES=
  'IGNORE_PYRA'`; de bridge zet dat zelf, de pyramides blijven dan onverfijnd.

### 7.4 Gekromde randen

![Randvolgen bij HOMARD](img/homard_boundary.svg)

1. As (midden) van de cilinder.
2. Zonder randvolgen: de nieuwe knoop ligt op de rechte rand van het grove element.
3. De randvlakken van het grove mesh (een veelhoek op de cilinder).
4. Met randvolgen: de nieuwe knopen liggen op de cilinder.
5. Het echte gekromde vlak.

Zonder randvolgen houdt een gat de veelhoek van het grove mesh en werken de knikken als
inspringende hoeken: de warmtestroom aan het gat liep in S35a op tot +21% en bleef stijgen.
De bridge zoekt daarom zelf de gekromde randen:
- alle **vrije vlakken** van de volume-elementen worden in stukken verdeeld (buurvlakken
  met minder dan 50° tussen de normalen horen bij elkaar);
- elk stuk wordt gepast als **cilinder** of **bol**: alle knopen moeten binnen 0,001 x de
  straal van het vlak liggen (knopen van een Mecway-mesh liggen op het CAD-vlak);
- een herkend vlak wordt een groep randelementen `BRRAND<n>` met
  `FRONTIERE_ANALYTIQUE` (cilinder: midden, as, straal; bol: midden, straal). De log
  meldt elk herkend vlak (INFO) en elk gekromd stuk dat niet herkend is (WARNING; daar
  liggen nieuwe knopen op de rechte elementranden).

Kegels en vrije vormen worden niet herkend. Geef een cilinder of bol zelf op, of zet het
randvolgen uit, met **`#ASTER-RAND`** per vlakselectie (Engels `#ASTER-BOUNDARY`):

```
#ASTER-RAND Gat = CILINDER 0, 0, 0, 0, 0, 1, 10 mm
#ASTER-RAND Kop = BOL 0, 0, 0.2, 25 mm
#ASTER-RAND Rand = GEEN
```

CILINDER: een punt op de as (x, y, z), de asrichting (ax, ay, az, zonder eenheid) en de
straal; BOL: middelpunt en straal; lengtes in m of met eenheid; GEEN: dit vlak niet volgen.
De vlakken van die selectie doen dan niet mee met het automatisch herkennen. Voorbeeld en
uitleg ook in [ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md).

### 7.5 Resultaten in Mecway

- **Knoopwaarden** (temperatuur, verplaatsing, spanning, plastische rek, warmtestroom in de
  knopen) zijn in de oorspronkelijke knopen gelijk aan het verfijnde resultaat (de knopen
  van het grove mesh blijven bestaan; S35a: verschil < 1e-16 relatief).
- **Elementknoopwaarden** (per element in een knoop): in een knoop die bij twee grove
  elementen hoort, krijgen beide de waarde van één verfijnd buurelement; de sprong tussen
  de grove elementen gaat verloren (S35a: beide 214,27 MPa, verfijnd 214,27 en 236,12). Kijk
  voor een piek naar de knoopwaarde of naar het verfijnde resultaat in ParaView.
- **Reactiekrachten** gaan niet naar Mecway (WARNING): knoopkrachten van het verfijnde mesh
  laten zich niet interpoleren naar de grove knopen.
- Alle tijdstappen van een niet-lineaire of transiënte analyse worden overgezet.
- Het verfijnde resultaat zelf: `<model>_<run_id>_verfijnd.rmed` met `med_export` of
  `vtu_export`.

### 7.6 Interpretatie

- Het doel geldt voor de **globale** ZZ-fout. Een piekwaarde aan een gat heeft een veel
  kleiner doel nodig: plaat met gat (AD-10) warmtestroom binnen 1% bij 0,15%; met
  plasticiteit (AD-11) spanning binnen 1% bij 0,4%.
- **Minder elementen dan uniform:** AD-10 −0,87% met 2621 elementen, uniform verfijnd
  dezelfde nauwkeurigheid met 6144 (factor 2,3); AD-11 +0,9% met 4364, uniform +2,4% met
  6144 (bij 1932 elementen al gelijk aan uniform: factor 3,2).
- De piek verbetert soms pas laat: bij plasticiteit bleef de spanning aan het gat drie
  lussen gelijk tot de elementen aan het gat zelf verfijnd werden.
- Bij een **singulariteit** (scherpe inspringende hoek, puntlast) blijft de lus daar
  verfijnen zonder dat de waarde convergeert (zoals §1.5).

### 7.7 Wat niet kan

Deze eerste versie geeft een ERROR (en rekent niet) bij:
- **schalen, balken, veren, puntmassa's** (alleen volume-elementen);
- **knoopselecties met meer dan één knoop** in een last of voorwaarde (HOMARD vult ze niet
  aan; zet de last op een vlakselectie);
- **contact**, verlijmd contact, koppelingen, vergelijkingen tussen knopen,
  **Compression only**, voorspansecties, flexibele verbindingen;
- **bezwijken van elementen**, `LINE_QUAD` (`elem_hex8`), resultaatroute `tabel`, 2D.

Verder: de lus vergroft niet, en de elementknoopwaarden en reacties zie §7.5. Deze grenzen
staan ook in `KNOWN_BUGS.md` (punt 65).

### 7.8 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| Adaptieve verfijning gestopt: doel bereikt | globale ZZ-fout <= doel | klaar |
| Adaptieve verfijning gestopt: maximum aantal lussen bereikt | doel nog niet gehaald | meer lussen of een hoger doel |
| Adaptieve verfijning gestopt: het maximum aantal elementen zou overschreden worden | grens `adapt_homard_max_elements` | hogere grens (en `memory_limit`) of hoger doel |
| Adaptieve verfijning gestopt: de fout stijgt twee lussen achter elkaar | singulariteit of slechte overgangen | kijk naar het verfijnde resultaat; rond de hoek af |
| Adaptieve verfijning gestopt: HOMARD maakte geen nieuw mesh | HOMARD faalde (zie de .mess) | het resultaat van de laatste lus staat in Mecway; meld het geval |
| ERROR: Adaptieve verfijning (adapt_homard): ... | iets uit §7.7 in het model | pas het model aan of zet `adapt_homard` uit |
| WARNING: ... gekromd randvlak ... niet herkend | geen cilinder of bol (kegel, vrije vorm, of een afgerond stuk dat aan een vlak vastzit) | `#ASTER-RAND` als het toch een cilinder of bol is; anders accepteren |
| WARNING: ... de reactiekrachten gaan niet naar Mecway | knoopkrachten zijn niet te projecteren | reacties uit een run zonder verfijning |
| ERROR: '#ASTER-RAND ...': verwacht ... | verkeerde regel | zie §7.4 |

### 7.9 Verificatie

[`Verificatie.md`](Verificatie.md) hoofdstuk Adaptieve verfijning (AD): AD-10 thermisch
(warmtestroom aan het gat −0,87% tegen uniform n32, 2621 elementen, factor 2,3 minder dan
uniform), AD-10b dezelfde rand met `#ASTER-RAND`, AD-11 plasticiteit (spanning +0,9%, rek
+1,5%, 4364 elementen), AD-12 een temperatuur op een knoopselectie geeft een ERROR.

## 8. Bronnen

- EDF R&D. *code_aster 17.4*: catalogus `Cata/Commands/macr_adap_mail.py` (`ELEMENTS_ACCEPTES`, `FRONTIERE_ANALYTIQUE`, `MAJ_CHAM`), `proj_champ.py`, testcases forma07b (indicatorveld + `CRIT_RAFF_ABS`), forma20c, forma21a, ssnp158a. De U-documenten U7.03.01 en U4.72.05 zijn niet lokaal ingezien.
- Zienkiewicz, O.C. & Zhu, J.Z. (1987). A simple error estimator and adaptive procedure for practical engineering analysis. *International Journal for Numerical Methods in Engineering*, 24(2), 337–357. Niet lokaal ingezien.
- EDF R&D. *code_aster 17.4*: catalogus `lib/aster/code_aster/Cata/Commands/calc_erreur.py`
  (opties, `EXCIT`, geen `GROUP_MA`), `Cata/Commons/c_nom_cham_into.py` (velden
  `ERME_ELEM`/`ELNO`/`NOEU`), `Messages/indicateur.py` (meldingen). De U- en R-documenten
  van `CALC_ERREUR` en de residu-schatter zijn niet lokaal aanwezig: NIET ingezien.
- EDF R&D. Validatietestcases `sslv153a`, `sslv07a`, `sslv111f`, en voor HOMARD
  `sslv110f` (gedraaid, §6.6) en `sslv319a` (`share/aster/tests`, code_aster 17.4).
- Mecway Ltd. *Mecway manual* (versie 33), §4.4 Refinement Tools, §16.1 Command Line
  Parameters (`script`); de API `mw.refine_x2` uit Mecway's scripting-documentatie.
- Dörfler, W. (1996). A convergent adaptive algorithm for Poisson's equation. *SIAM
  Journal on Numerical Analysis*, 33(3), 1106–1124 (keuze `dorfler`). Niet lokaal
  ingezien.
- Pilkey, W.D. & Pilkey, D.F. (2008). *Peterson's Stress Concentration Factors* (3e
  druk). Hoboken: Wiley, chart 4.1 (verificatie AD). Niet lokaal ingezien.
- Ainsworth, M. & Oden, J.T. (2000). *A Posteriori Error Estimation in Finite Element
  Analysis*. New York: Wiley (effectiviteitsindex, residu-schatters). Niet lokaal
  ingezien; algemene achtergrond.
- Verfürth, R. (1996). *A Review of A Posteriori Error Estimation and Adaptive
  Mesh-Refinement Techniques*. Stuttgart: Wiley-Teubner. Niet lokaal ingezien;
  algemene achtergrond.
