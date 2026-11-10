# Breukmechanica: K en G langs een gemeshte scheur of een XFEM-scheur

*English version: [Fracture_mechanics.md](en/Fracture_mechanics.md)*

Bij een lineair statische analyse (Mecway *Static*, S30; bridge-analyse
`lin_static_3d`) rekent de bridge met Code-Aster de **spanningsintensiteitsfactoren**
K_I, K_II, K_III en de **energie-afgifte** G langs het front van een scheur die je in
het mesh hebt gemaakt. Mecway kent zelf geen breukmechanica (Mecway Ltd., 2026); de
bridge herkent de scheur aan drie selecties met een vaste naam.

| Wat | Waar je het ziet |
|---|---|
| K_I, K_II, K_III en G per knoop langs het front | tabel `<model>_<run-id>_scheur.csv` in de werkmap |
| bereik van K_I en G langs het front, en meldingen | log en statusvak na de run |
| verplaatsingen, spanningen (gewone resultaten) | Mecway, zoals altijd |

K en G zijn **geen veld in Mecway** (KNOWN_BUGS 63): de waarden horen bij het front,
niet bij een knoop of element van het model. Algemene werking van de bridge:
[`Handleiding.md`](Handleiding.md).

Een scheur die **niet in het mesh** zit (dwars door de elementen, met een
`#ASTER-XFEM`-regel): **XFEM**, §7. §1 tot §6 gaan over de gemeshte scheur.

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Analysetype** *Static* (S30). Bij andere analyses geeft de bridge een WARNING en
   rekent geen K en G (§4).
2. **Geometrie met het scheurvlak als elementgrens.** De scheur is een vlak in het
   mesh: aan het scheurvlak liggen elementvlakken, het front is een lijn van
   elementranden. Een scheur die dwars door elementen loopt: XFEM (§7).
3. **Volume-elementen, bij voorkeur hex20 (of tet10/wedge15).** Met hex20 is K uit
   `CALC_G` al bij een grof mesh nauwkeurig (§3). hex8 kan ook, maar is minder
   nauwkeurig; `LINE_QUAD` (pagina Elementen) maakt hex8 kwadratisch en geeft dan
   hetzelfde als hex20.
4. **Fijn mesh rond het front.** Elementgrootte aan het front: ongeveer a/10 tot a/20
   (a = scheurlengte of -diepte) is genoeg voor K binnen 1 % met hex20 (§3). Verfijn
   vooral loodrecht op het front; langs het front minstens 4 elementen (5 knopen,
   §2.3).
5. **Materiaal:** isotroop elastisch (`E`, `ν`), bij voorkeur één materiaal rond het
   front (een scheur op een grensvlak tussen materialen is NIET geverifieerd).
6. **Randvoorwaarden en belastingen** zoals altijd. Zet geen voorwaarde op de lippen
   (dan is de scheur dicht).

### 1.2 De scheur openen

Een scheur heeft twee lippen die op dezelfde plek liggen maar **niet met elkaar
verbonden** zijn: op de lippen staan dubbele knopen, aan het front en daarbuiten (het
ligament) gedeelde knopen. Zo doe je dat in Mecway (Mecway Ltd., 2026, §4.2.10 en
§4.2.11):

1. Selecteer alle elementen aan **één kant** van het scheurvlak (bijv. alle elementen
   boven het vlak).
2. *Mesh tools > Disconnect elements*. Nu is het hele vlak losgemaakt, ook het
   ligament (controle: *View > Exploded view* of *View > Open cracks*).
3. Selecteer de **knopen van het ligament en van het front** (de knopen in het vlak
   die níet bij de scheur horen). Een kader-selectie neemt de dubbele knopen op
   dezelfde plek allebei mee.
4. *Mesh tools > Merge nearby nodes* met een kleine afstand (kleiner dan het kleinste
   element). Met een knoopselectie voegt Mecway alleen die knopen samen; de lippen
   blijven los.

Andere manieren: (a) bouw de twee helften als aparte onderdelen en voeg alleen het
ligament en het front samen (stap 3-4); (b) **half model met symmetrie**: model alleen
de helft boven het scheurvlak, zet een *Symmetry*-voorwaarde op het ligament en laat
de lip vrij; dan is er maar één lip en hoeft er niets open (§1.3).

Is de scheur niet open (de lippen delen knopen buiten het front), dan stopt de bridge
met een ERROR (§5).

### 1.3 Selecties benoemen

Maak met *Named selection* deze selecties (namen in hoofd- of kleine letters; Engelse
namen werken ook):

| Selectie | Soort | Wat | Engels |
|---|---|---|---|
| `SCHEUR_FRONT` | knoopselectie | alle knopen langs het front (hoek- en middenknopen; ontbreekt een middenknoop, dan neemt de bridge hem van het element) | `CRACK_FRONT` |
| `SCHEUR_LIP_BOVEN` | vlakselectie | de elementvlakken van de ene lip | `CRACK_LIP_UPPER` |
| `SCHEUR_LIP_ONDER` | vlakselectie | de elementvlakken van de andere lip; **weglaten** bij een half model met symmetrie | `CRACK_LIP_LOWER` |

- Welke lip "boven" is maakt niet uit: verwisselen gaf exact dezelfde K (gemeten).
- **Meer scheuren:** geef elke scheur een eigen achtervoegsel achter alle drie de
  namen, bijv. `SCHEUR_FRONT_A`, `SCHEUR_LIP_BOVEN_A`, `SCHEUR_LIP_ONDER_A` en
  `SCHEUR_FRONT_B`, ... De tabel heeft dan een kolom `crack` met `_A`, `_B`.
- Een front is één lijn: open (bijv. door de dikte van een plaat, of een kwart van
  een cirkel in een kwartmodel) of gesloten (een cirkel rond een schijfvormige
  scheur).

### 1.4 In het hoofdvenster van de bridge

Pagina **Statisch**, kopje *Breukmechanica (SCHEUR_-selecties)*. De instellingen doen
alleen iets als het model `SCHEUR_`-selecties heeft.

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Scheur: R_INF [m] (0 = automatisch) | `fracture_r_inf` | 0 | zelden. Code-Aster kiest 2 x de elementgrootte aan het front. Hangen G of K af van de keuze (vergelijk twee waarden), of is het mesh aan het front onregelmatig: kies R_INF = 2 à 3 elementen |
| Scheur: R_SUP [m] (0 = automatisch) | `fracture_r_sup` | 0 | Code-Aster kiest 4 x de elementgrootte. Kleiner kiezen als de ring daarmee over een andere scheur, een opgelegde of belaste rand of de rand van het model zou gaan; R_SUP > R_INF |
| Scheur: gladmaken langs het front | `fracture_smoothing` | `LINEAIRE` | `LEGENDRE` met graad 0 bij een kort front met minder dan 5 knopen (de bridge waarschuwt dan) of als je één gemiddelde waarde wilt |
| Scheur: Legendre-graad (0 .. 7) | `fracture_legendre_degree` | 5 | alleen bij `LEGENDRE`; kleiner dan het aantal knopen langs het front |

R_INF en R_SUP zijn de binnen- en buitenstraal van de ring rond het front waarover
`CALC_G` integreert (theta-methode). Voor één model kan het ook met `#ASTER-OPTIE`
in Mecway's custom input, bijv. `#ASTER-OPTIE fracture_r_inf = 0.002` en `#ASTER-OPTIE fracture_r_sup = 0.004`
([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) voorbeeld 16).

### 1.5 Starten en resultaten

Klik *Starten*. Na afloop staat in de log en het statusvak bijvoorbeeld (verificatie
BR-01):

```
Breukmechanica, scheur 1: 5 punten langs het front. K_I 46.97 MPa.m^0,5 (CALC_G),
45.38 MPa.m^0,5 (POST_K1_K2_K3); G 9539 J/m2. K_II tot 2.42e-13, K_III tot 6.78e-14
MPa.m^0,5. Tabel: BR-01_verif_scheur.csv
```

Varieert de waarde langs het front, dan staat er een bereik (`1.568 .. 1.611`). De
tabel `<model>_<run-id>_scheur.csv` (komma's, punt als decimaalteken; te openen in een
spreadsheet) heeft per knoop langs het front, in SI-eenheden:

| Kolom | Betekenis | Eenheid |
|---|---|---|
| `crack` | achtervoegsel van de scheur (`1` zonder achtervoegsel) | - |
| `point`, `node` | volgnummer langs het front en het nummer van de Mecway-knoop | - |
| `x`, `y`, `z`, `s` | plaats en booglengte langs het front | m |
| `G` | energie-afgifte uit `CALC_G` (theta-methode) | J/m² (= N/m) |
| `K1`, `K2`, `K3` | K_I, K_II, K_III uit `CALC_G` (interactie-integraal) | Pa·√m |
| `G_IRWIN` | G uit K1..K3 van `CALC_G`: (K1² + K2²)(1 − ν²)/E + K3²(1 + ν)/E | J/m² |
| `K1_POST_K`, `K2_POST_K`, `K3_POST_K`, `G_POST_K` | dezelfde grootheden uit `POST_K1_K2_K3` (controle; bij kwadratische elementen alleen in de hoekknopen, de middenknopen zijn leeg) | Pa·√m, J/m² |

De tabellen staan ook in de `.mess` (`IMPR_TABLE`).

### 1.6 Interpretatie

- **Welke waarde:** K1/K2/K3 en G uit `CALC_G` zijn het resultaat; ze zijn ook op een
  grof mesh nauwkeurig (§3). `POST_K1_K2_K3` is een onafhankelijke controle die zonder
  kwartpuntelementen een paar procent te laag uitkomt. Verschillen ze meer dan 5 %
  binnen het front, dan waarschuwt de bridge (mesh te grof, of R_INF/R_SUP).
- **G en K:** in vlakke rek (het binnenste van een dikke plaat) is G = K_I²/E' met
  E' = E/(1 − ν²); in vlakke spanning (dunne plaat) E' = E. `G` en `G_IRWIN` horen in
  vlakke rek gelijk te zijn (verificatie: 0,2 %).
- **Toetsen tegen de breuktaaiheid:** de scheur groeit (bros, lineair-elastisch) als
  K_I ≥ K_IC. K_IC is een materiaaleigenschap in vlakke rek (bijv. constructiestaal
  ~ 50–200 MPa·√m, aluminium ~ 20–40 MPa·√m; Anderson, 2005). Gebruik K_IC voor dikke
  delen; een dunne plaat (vlakke spanning) heeft een hogere schijnbare taaiheid K_C.
  Bij plasticiteit rond het front (grote plastische zone t.o.v. de afmetingen) geldt
  de lineair-elastische breukmechanica niet meer.
- **Gemengde belasting:** K_II (afschuiving in het vlak, loodrecht op het front) en
  K_III (afschuiving langs het front) zijn bij een symmetrische trekbelasting ~0. Een
  criterium voor gemengde belasting (bijv. G ≥ G_C met G = de som) kies je zelf.
- **Randeffect aan een vrij oppervlak:** waar het front een vrij oppervlak raakt is
  de spanningstoestand geen vlakke rek meer en is de singulariteit niet meer 1/√r. In
  het midden van een dikke plaat is K_I gelijk aan de 2D-waarde in vlakke rek
  (BR-03: +0,7 %); naar het oppervlak toe verandert K_I (BR-03: tot +6 %), en de
  waarde in de oppervlakteknoop zelf is geen betrouwbare K. Beoordeel K in het
  binnenste van het front.
- **K_I < 0:** de lippen gaan over elkaar (druk op de scheur). De bridge rekent zonder
  contact op de lippen, dus de waarde is fysisch zinloos (WARNING); de scheur is dan
  dicht en groeit niet in modus I.

## 2. Hoe de bridge vertaalt

### 2.1 Code-Aster-commando's

1. Mesh (`bridge_mesh.write_mesh`): de ribben van de volume-elementen waarvan beide
   eindknopen in `SCHEUR_FRONT` liggen worden SEG2/SEG3-cellen in groep
   `BRSCHEUR<n>` (`DEFI_FOND_FISS` kent het front alleen als cellen of als geordende
   knopen; Mecway kent geen ribben). De bridge controleert dat ze één lijn vormen en
   dat de lippen buiten het front geen knopen delen.
2. Na `MECA_STATIQUE` en de export van de gewone resultaten (een fout in de
   breukmechanica houdt de resultaten in Mecway dus niet tegen):

```
fieldmat_fiss = AFFE_MATERIAU(... TOUT='OUI' met het materiaal aan het front, daarna
                              het materiaal per elset ...)
res_fiss = CREA_RESU(OPERATION='AFFE', TYPE_RESU='EVOL_ELAS', AFFE=_F(NOM_CHAM='DEPL',
                     CHAM_GD=<verplaatsing van res>, CHAM_MATER=fieldmat_fiss, ...),
                     EXCIT=<de lasten van MECA_STATIQUE>)
res_fiss = CALC_CHAMP(reuse=res_fiss, RESULTAT=res_fiss, CONTRAINTE=('SIEF_ELGA',))
fond_1 = DEFI_FOND_FISS(MAILLAGE=mesh, FOND_FISS=_F(GROUP_MA='BRSCHEUR1'),
                        SYME='NON', LEVRE_SUP=_F(GROUP_MA='SCHEUR_LIP_BOVEN'),
                        LEVRE_INF=_F(GROUP_MA='SCHEUR_LIP_ONDER'), CONFIG_INIT='COLLEE')
scheur_g_1 = CALC_G(RESULTAT=res_fiss, OPTION=('G', 'K'), THETA=_F(FISSURE=fond_1))
scheur_pk_1 = POST_K1_K2_K3(RESULTAT=res_fiss, FOND_FISS=fond_1)
```

- Zonder `SCHEUR_LIP_ONDER`: `SYME='OUI'` (half model; Code-Aster rekent K en G
  voor de hele scheur, BR-02 gelijk aan BR-01).
- Een gesloten front: `TYPE_FOND='FERME'`.
- Een front dat een cirkel is met de lip binnen de cirkel (schijfvormige scheur):
  `FORM_FISS='CERCLE', RAYON=<straal>` (krommingscorrectie van de
  interactie-integraal; forma07a zonder: K_I +5,6 %, met: +0,1 %).
- `R_INF`/`R_SUP` en `DISCRETISATION`/`DEGRE` uit de instellingen (§1.4).

Waarom een eigen materiaalveld en resultaat: `CALC_G` rekent ook op de randcellen (de
lippen, belaste vlakken) in de ring en vraagt daar een materiaal (`<EXCEPTION>
CALCUL_20`, "Le matériau est nécessaire sur la maille", optie `CALC_K_G`, gezien bij de
bouw), terwijl de bridge het materiaal per elset geeft. De optie `G` leest `SIEF_ELGA`
(`<EXCEPTION> RUPTURE0_94` zonder).

### 2.2 Automatische R_INF en R_SUP

Zonder `R_INF`/`R_SUP` kiest Code-Aster ze zelf en meldt dat in de `.mess` ("Le
paramètre R_INF automatiquement choisi vaut ..."). Gemeten: R_INF = 2 h en R_SUP = 4 h,
met h de elementgrootte aan het front (BR-01, h = 1,25 mm: 2,5 en 5 mm).

### 2.3 Aantal knopen langs het front

Met `DISCRETISATION='LINEAIRE'` (standaard) en maar 3 knopen langs het front (2
elementen) oscilleerden G en K van knoop tot knoop (gemeten: 11 739 / 4 696 / 25 826
J/m² waar 9 391 verwacht; hex8 en hex20 gelijk). Met 5 knopen of meer niet. Bij minder
dan 5 knopen geeft de bridge een WARNING; kies dan een fijner mesh langs het front of
`LEGENDRE` met graad 0 (een constante, juist bij vlakke rek). Legendre met een te hoge
graad (5 bij 3 knopen) gaf −8 tot −22 %.

## 3. Nauwkeurigheid en mesh-advies

Middenscheur in een plaat (vlakke rek, a/b = 0,5, BR-01), afwijking van K_I en G in
het midden van het front t.o.v. Tada (2000), met de standaardinstellingen:

| Mesh aan het front (h) | hex20: K_I / G (`CALC_G`) | hex20: K_I (`POST_K1_K2_K3`) | hex8: K_I / G (`CALC_G`) | hex8: K_I (`POST_K1_K2_K3`) |
|---|---|---|---|---|
| h ≈ a/12 (grof) | −0,45 % / −1,6 % | −3,3 % | −1,3 % / −4,3 % | −8,7 % |
| h = a/20 | −0,24 % / −0,9 % | −2,9 % | −0,9 % / −2,8 % | −11 % |
| h = a/40 | −0,10 % / −0,4 % | −3,5 % | −0,7 % / −2,0 % | −10 % |
| h = a/40, kwartpuntknopen | +0,02 % / +0,02 % | −0,1 % | - | - |

(hex8 met 8 elementen over de dikte; met 2 zie §2.3.) Advies:

- **hex20** (of `LINE_QUAD`) met h ≈ a/10 … a/20 aan het front: K uit `CALC_G` binnen
  1 %, G binnen 2 %.
- **hex8**: K binnen 2 % vanaf h ≈ a/12, G vraagt h ≈ a/40 voor 2 %; `POST_K1_K2_K3`
  is met hex8 ~10 % te laag, gebruik `CALC_G`.
- **Kwartpuntknopen** (de middenknopen van de ribben vanaf het front op 1/4 van de
  rib) maken `POST_K1_K2_K3` exact. De bridge zet ze niet zelf (KNOWN_BUGS 63) en
  Mecway kan ze niet maken; voor `CALC_G` zijn ze niet nodig.
- `R_INF`/`R_SUP` (automatisch, 2 × /4 ×, 4 × /8 ×, 8 × /16 × h) gaven dezelfde waarden;
  R_INF = 0 gaf G −1,3 %.

## 4. Wat niet kan

- **Andere analyses** dan lineair statisch (niet-lineair, dynamica, modaal,
  thermisch): WARNING, geen K en G.
- **Contact op de lippen** en plasticiteit (J-integraal in een niet-lineaire analyse):
  niet gebouwd.
- **K en G als veld in Mecway:** niet; alleen de tabel en de log.
- **Kwartpuntknopen** door de bridge: niet (de resultaatexport controleert de
  knoopcoördinaten tegen de `.liml`). Staan ze al in de `.liml` (bijv. een mesh uit een
  ander programma), dan werkt het wel (BR-04).
- **Een scheur zonder hem te meshen**: XFEM, §7.
- **NIET geverifieerd:** een scheur op een grensvlak tussen materialen (WARNING),
  thermische rek, druk op de lippen, tet10-meshes rond het front (forma07a heeft
  wedge15 aan het front: BR-04), een gesloten front, schalen in het model.

## 5. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Breukmechanica: '...' moet een knoopselectie/vlakselectie zijn | `SCHEUR_FRONT` als vlakselectie, of een lip als knoopselectie | maak de selectie opnieuw van de juiste soort (§1.3) |
| ERROR: ... scheur '...' is onvolledig | front of bovenlip ontbreekt (bijv. een typefout in de naam) | alle selecties met dezelfde naam en hetzelfde achtervoegsel (§1.3) |
| ERROR: ... twee selecties voor dezelfde scheur | twee selecties die op dezelfde naam uitkomen (hoofdletters tellen niet) | een eigen achtervoegsel per scheur |
| ERROR: ... geen rib van een volume-element met beide eindknopen in '...' | de knopen van het front zijn geen naburen op een elementrand, of het front ligt op schalen | selecteer alle knopen langs het front; het front moet een rand van volume-elementen zijn |
| ERROR: ... vormen geen enkele lijn (vertakking / meerdere stukken) | twee fronten in één selectie, of extra knopen | een selectie per front, met een achtervoegsel |
| ERROR: ... boven- en onderlip delen ... knopen buiten het front: de scheur is niet open | de scheur is niet losgemaakt | §1.2 (Disconnect elements, dan Merge nearby nodes alleen voor ligament en front) |
| ERROR: ... de lippen moeten vlakken van volume-elementen zijn | een lip op schalen | scheur in volume-elementen modelleren |
| ERROR: ... fracture_r_inf en fracture_r_sup: nodig 0 <= R_INF < R_SUP | onjuiste instellingen | beide 0 (automatisch) of R_INF < R_SUP |
| WARNING: ... knopen van '...' liggen niet op een rib langs het front | losse knopen in de frontselectie | onschuldig; ze tellen niet mee |
| WARNING: ... de lippen ... delen geen frontknopen | het front is ook losgemaakt | voeg de frontknopen weer samen (§1.2 stap 3-4) |
| WARNING: ... heeft maar n knopen; ... oscilleren | kort front (< 5 knopen) | fijner mesh langs het front, of `LEGENDRE` graad 0 (§2.3) |
| WARNING: ... Legendre-graad ... bij n knopen | graad te hoog | graad kleiner dan het aantal knopen |
| WARNING: ... geen rechte lijn en geen schijfvormige cirkel | krom front, of een cirkel met de lip erbuiten | gebruik G of K uit `POST_K1_K2_K3` |
| WARNING: ... verschillende materialen | front op een grensvlak | NIET geverifieerd; controleer met een eigen berekening |
| WARNING: ... K_I is negatief | druk op de scheur (lippen over elkaar) | geen modus-I-groei; zonder contact zinloos (§1.6) |
| WARNING: ... K_I uit CALC_G en uit POST_K1_K2_K3 verschillen tot ...% | grof mesh, ongunstige R_INF/R_SUP of een krom front | verfijn het mesh rond het front (§3) |
| WARNING: ... POST_K1_K2_K3 gaf geen waarden | `POST_K1_K2_K3` faalde (fout in de `.mess` na `BRIDGE_SCHEUR_POSTK_FOUT`) | gebruik `CALC_G`; zie de `.mess` |
| WARNING: Breukmechanica (SCHEUR_-selecties) werkt alleen bij lineair statisch | andere analyse | normaal; geen K en G |

## 6. Verificatie

[`Verificatie.md`](Verificatie.md) hoofdstuk Breukmechanica (BR):

- **BR-01** middenscheur in een plaat, vlakke rek, hex20, beide lippen (dubbele
  knopen): K_I −0,10 % t.o.v. Tada, G −0,41 %, G/(K_I²/E') = 0,998.
- **BR-02** hetzelfde als half model (`SYME='OUI'`): gelijk aan BR-01.
- **BR-03** dikke plaat (B = 4a) met vrije zijvlakken: K_I in het middenvlak +0,7 %.
- **BR-04** Code-Aster-testcase forma07a via de bridge: K1 MAX van `POST_K1_K2_K3`
  1 607 011,55 = de TEST_TABLE-waarde; K_I uit `CALC_G` −0,8 % en G +0,8 % t.o.v. de
  analytische oplossing.
- **BR-05** zoals BR-01 met hex8: K_I −0,7 %, G −2,0 %.
- **BR-06** twee fronten als twee scheuren (`_L`, `_R`): per front gelijk aan BR-01.

XFEM (§7):

- **BR-07** de plaat van BR-01 zonder scheur in het mesh, `HALFVLAK`, hex8 h = a/20:
  K_I −0,08 %, G −0,18 %, `POST_K1_K2_K3` −0,24 %; de lippen gaan in Mecway even ver
  open.
- **BR-08** idem met hex20: K_I +0,10 %, G +0,17 %.
- **BR-09** idem met het scheurvlak door knopen en het front op elementgrenzen: K_I
  −0,06 %, G −0,05 %.
- **BR-10** cirkelvormige scheur in een blok, `CIRKEL`: K_I `POST_K1_K2_K3` +1,6 %, K
  uit G +1,0 %, K_I `CALC_G_XFEM` +5,3 % (geen krommingscorrectie); opening van de
  scheur +3,3 % (Sneddon).
- **BR-11** Code-Aster-testcase forma07b via de bridge: K1 MAX van `CALC_G_XFEM` en
  `POST_K1_K2_K3` gelijk aan de TEST_TABLE-waarden.
- **BR-12** middenscheur over de volle breedte als `RECHTHOEK` (twee fronten): per
  front als BR-07.
- **BR-13** de scheur van BR-09 als vlakselectie `XFEM_midden` (§7.8): K_I −0,06 %,
  G −0,05 %, `POST_K1_K2_K3` +1,1 %.
- **BR-14** BR-07 met `med_export`: `_xfem.rmed` met `DEPL`, `SIGM_NOEU` en
  `SIEQ_NOEU` op het mesh dat de scheur volgt; opening 99,6 % (§7.9).

## 7. XFEM: een scheur zonder hem te meshen

Met XFEM (*extended finite element method*) hoeft de scheur niet in het mesh te
zitten: je beschrijft hem met een vorm (cirkel, ellips, rechthoek of halfvlak) in een
`#ASTER-XFEM`-regel, of met een vlakselectie `XFEM_<naam>` in Mecway (een vrije vorm
op een knooplaag, §7.8), en Code-Aster laat hem als *levelset* dwars door de elementen
lopen (`DEFI_FISS_XFEM`). Zo kun je een scheur op elke plek en in elke stand in een
bestaand, ongescheurd mesh zetten, zonder *Disconnect elements* en zonder het mesh aan
het scheurvlak aan te passen. Je krijgt dezelfde uitvoer als bij een gemeshte scheur:
K_I, K_II, K_III en G langs het front, en de gewone resultaten in Mecway (§7.5).

| Wat | Waar je het ziet |
|---|---|
| K_I, K_II, K_III en G per punt langs het front | tabel `<model>_<run-id>_xfem.csv` in de werkmap |
| bereik van K_I en G per front, en meldingen | log en statusvak na de run |
| verplaatsingen, spanningen, reacties (met de scheur) | Mecway, zoals altijd (§7.5) |
| het mesh dat de scheur volgt, met verplaatsing en spanning (de opening is te zien) | `<model>_<run-id>_xfem.rmed` in de werkmap, alleen met de instelling *MED-bestand voor ParaView* (§7.9) |

### 7.1 Werkwijze stap voor stap

1. **Model in Mecway** zoals altijd: analysetype *Static* (S30), alleen
   volume-elementen (hex8, hex20, tet4, wedge, pyramide; geen schalen, balken, veren
   of losse knopen, §7.6), randvoorwaarden en belastingen. Maak **geen** scheur in het
   mesh.
2. **Mesh fijn rond de plek van het front**: elementen loodrecht op het front van
   ongeveer a/20 (a = straal of kleinste halve as; bij een doorgaande scheur de halve
   scheurlengte), §7.4. Het front en het scheurvlak mogen door de elementen lopen en
   ook door knopen of over elementgrenzen (BR-07, BR-09).
3. **De scheur beschrijven** in een vrij tekstveld van Mecway, bijv. *CCX > Custom
   model definition* (regel met `**`), *OpenRadioss > Custom model definition* (`#`)
   of *Mystran > Custom bulk data* (`$`), zie
   [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) voorbeeld 29:

   ```
   ** ASTER-XFEM vorm=CIRKEL, centrum=(0, 0, 0), r=20 mm, normaal=(0, 0, 1)
   ```

   Een regel die met `vorm=` begint, is een nieuwe scheur; een volgende regel zonder
   `vorm=` hoort bij dezelfde scheur (lange regels splitsen). Meer scheuren: meer
   regels met `vorm=` (elk met een eigen `naam=`). Of: een vlakselectie
   `XFEM_<naam>` met de vlakken in het scheurvlak, zonder `#ASTER-XFEM`-regel (§7.8).
4. **Instellingen** (pagina *Statisch*, kopje *Breukmechanica*): `fracture_r_inf` /
   `fracture_r_sup` gelden ook voor XFEM (§1.4); per scheur kan `r_inf=`/`r_sup=`.
5. *Starten*. De log en het statusvak geven per front het bereik van K_I uit
   `CALC_G_XFEM` en uit `POST_K1_K2_K3`, en G, bijvoorbeeld (BR-10: de regel hierboven met `naam=penny`):

   ```
   Breukmechanica XFEM, scheur penny: 38 punten langs het front. K_I 0.1648 .. 0.1728
   MPa.m^0,5 (CALC_G_XFEM), 0.1605 .. 0.1679 MPa.m^0,5 (POST_K1_K2_K3); G 0.1102 ..
   0.1165 J/m2. K_II tot 4.91e-05, K_III tot 0.00013 MPa.m^0,5. Tabel: BR-10_verif_xfem.csv
   ```

   De tabel heeft per punt dezelfde kolommen als bij een gemeshte scheur (§1.5), met
   een kolom `front` (1, 2, … per front van de scheur) en zonder `node` (de punten
   zijn snijpunten van het front met de elementen, geen knopen).

### 7.2 Sleutels van `#ASTER-XFEM`

Lengtes en coördinaten in m (zoals alle `#ASTER`-regels) of met een eenheid
(`r=20 mm`, `centrum=(10, 0, 5) mm`). Richtingen hoeven geen eenheidsvector te zijn.
Hoofd- en kleine letters maken niet uit; Engelse namen werken ook.

| Sleutel (Engels) | Bij vorm | Betekenis | Standaard | Wanneer aanpassen |
|---|---|---|---|---|
| `vorm` (`shape`) | – | `CIRKEL` (`CIRCLE`), `ELLIPSE`, `RECHTHOEK` (`RECTANGLE`) of `HALFVLAK` (`HALF_PLANE`, Code-Aster `DEMI_PLAN`) | verplicht | – |
| `centrum` (`centre`) | CIRKEL, ELLIPSE, RECHTHOEK | middelpunt (x, y, z) | verplicht | – |
| `r` (`radius`) | CIRKEL | straal | verplicht | – |
| `normaal` (`normal`) | CIRKEL, HALFVLAK | normaal op het scheurvlak | verplicht | – |
| `a`, `b` | ELLIPSE, RECHTHOEK | halve assen langs `vect_x` en `vect_y` | verplicht | – |
| `vect_x`, `vect_y` | ELLIPSE, RECHTHOEK | richting van de assen in het scheurvlak, loodrecht op elkaar | verplicht | – |
| `afronding` (`fillet`) | RECHTHOEK | straal van de afgeronde hoeken (`RAYON_CONGE`) | 0 | een rechthoek waarvan de hoeken in het materiaal liggen |
| `front` (`point`) | HALFVLAK | een punt op het (rechte) front | verplicht | – |
| `richting` (`direction`) | HALFVLAK | groeirichting van het front: in het scheurvlak, loodrecht op het front, van de scheur naar het ongescheurde materiaal | verplicht | – |
| `naam` (`name`) | alle | naam in de tabel en de log (letters, cijfers, `_`, max. 16) | 1, 2, … | meer scheuren |
| `groep` (`group`) | alle | `<<elementselectie>>`: alleen daar mag Code-Aster verrijken (`GROUP_MA_ENRI`) | het hele model | grote modellen; NIET geverifieerd |
| `glad` (`smoothing`) | alle | gladmaken langs het front in `CALC_G_XFEM`: `LAGRANGE` of `LEGENDRE` | recht front (HALFVLAK, RECHTHOEK): `LAGRANGE`; gekromd (CIRKEL, ELLIPSE): `LEGENDRE` | zie §7.3 |
| `graad` (`degree`) | `LEGENDRE` | graad van het polynoom (0 .. 7) | `fracture_legendre_degree` (5) | kort front: 0 of 1 (§7.3) |
| `punten` (`points`) | alle | aantal punten langs het front (`NB_POINT_FOND`, gelijk verdeeld) voor `CALC_G_XFEM` en `POST_K1_K2_K3` | de snijpunten van het front met de elementen | een regelmatige tabel; nooit meer dan het aantal snijpunten |
| `r_inf`, `r_sup` | alle | ring van het theta-veld (m) | `fracture_r_inf`/`_sup`, 0 = automatisch (2h/4h) | zoals §1.4 |

Een rechthoek die buiten het model uitsteekt geeft alleen fronten binnen het model:
een doorgaande scheur in een plaat is een `RECHTHOEK` die de dikte overspant (twee
rechte fronten, BR-12) of een `HALFVLAK` (één front, BR-07). Een `HALFVLAK` is overal
aan één kant van het front gescheurd: gebruik het als het front het enige einde van de
scheur in het model is (bijv. een randscheur, of een half model met de scheur tot het
symmetrievlak).

### 7.3 Hoe de bridge vertaalt

1. Het model van de bridge heet `model_sain`; per scheur `DEFI_FISS_XFEM` en daarna
   `model = MODI_MODELE_XFEM(MODELE_IN=model_sain, FISSURE=(...))`. Lasten en
   `MECA_STATIQUE` gebruiken het XFEM-model.
2. Een *Symmetry* langs een globale as wordt bij XFEM `DDL_IMPO` (anders
   `LIAISON_OBLIQUE`): `DDL_IMPO` legt ook de XFEM-vrijheidsgraden van de knopen van
   gesneden elementen vast, `LIAISON_OBLIQUE` niet. Gemeten (BR-11, symmetrievlakken
   door de scheur): met `LIAISON_OBLIQUE` K1 aan het symmetrievlak +3,8 %, met
   `DDL_IMPO` gelijk aan de testcase. Een schuine voorwaarde op zo'n knoop geeft een
   WARNING.
3. Resultaten voor Mecway: de verplaatsing van het XFEM-model heeft extra
   vrijheidsgraden en is op een knoop van een gesneden element niet de fysische
   verplaatsing. `POST_MAIL_XFEM` + `POST_CHAM_XFEM` geven de verplaatsing en de
   spanning op een mesh dat de scheur volgt; elke Mecway-knoop is een knoop van dat
   mesh, dus `PROJ_CHAMP` (`COLLOCATION`) zet `DEPL`, `SIGM_NOEU` en `SIEQ_NOEU` terug
   op de Mecway-knopen met de waarde aan de eigen kant van de scheur. `REAC_NODA` komt
   uit het XFEM-resultaat. Dat resultaat gaat zoals altijd naar Mecway.
4. Na de export, per scheur en per front (`NUME_FOND`; een rechthoek door een plaat
   heeft er twee):

```
_tg = CALC_G_XFEM(RESULTAT=res_xfem, OPTION='CALC_K_G',
                  THETA=_F(FISSURE=fiss_1, NUME_FOND=_k[, R_INF=.., R_SUP=..][, NB_POINT_FOND=..]),
                  LISSAGE=_F(LISSAGE_G='LEGENDRE', LISSAGE_THETA='LEGENDRE', DEGRE=5))
_tp = POST_K1_K2_K3(RESULTAT=res_xfem, FISSURE=fiss_1, NUME_FOND=_k
                    [, ABSC_CURV_MAXI=R_SUP][, NB_POINT_FOND=..])
```

`ABSC_CURV_MAXI = R_SUP` alleen als R_SUP is opgegeven (zoals testcase forma07b).

**Gladmaken** (gemeten bij de bouw, hex8): de frontpunten zijn de snijpunten van het
front met de elementvlakken. Bij een recht front door een regelmatig mesh liggen ze
regelmatig en is `LAGRANGE` goed (13 punten: K_I binnen ±1 %); `LEGENDRE` met graad 2
gaf daar ±3 % en graad 4-5 ±25 % (met 5 punten werkte alleen graad 0-1). Bij een
gekromd front liggen de snijpunten onregelmatig (soms vlak bij elkaar): `LAGRANGE`
oscilleerde daar van −0,1 tot 2 × K (penny, 38 punten), `LEGENDRE` graad 5 was glad.
Vandaar de standaard per vorm (§7.2). De tabel en de WARNING bij een verschil met
`POST_K1_K2_K3` (> 5 %) laten zien of het goed ging.

### 7.4 Nauwkeurigheid en mesh-advies

Gemeten met de bridge (verificatie BR-07..14, [`Verificatie.md`](Verificatie.md)):

| Geval | Mesh aan het front | K_I `CALC_G_XFEM` | G | K_I `POST_K1_K2_K3` |
|---|---|---|---|---|
| middenscheur plaat (Tada), HALFVLAK, front door de elementen (BR-07) | hex8, h = a/20 | −0,08 % | −0,18 % | −0,24 % |
| idem, hex20 (BR-08) | hex20, h = a/20 | +0,10 % | +0,17 % | −0,13 % |
| idem, scheurvlak door knopen, front op elementgrenzen (BR-09) | hex8, h = a/20 | −0,06 % | −0,05 % | +1,1 % |
| idem als RECHTHOEK, twee fronten (BR-12) | hex8, h = a/20 | −0,09 % | −0,19 % | −0,29 % |
| idem uit een vlakselectie `XFEM_` (mesh van BR-09, BR-13) | hex8, h = a/20 | −0,06 % | −0,05 % | +1,1 % |
| cirkelvormige scheur (2σ√(a/π)), CIRKEL (BR-10) | hex8, h = a/20 | +5,3 % (geen krommingscorrectie) | +1,9 % (K uit G +1,0 %) | +1,6 % |

Mesh-studie cirkelvormige scheur (hex8, midden van het front, buiten de regressie):

| h aan het front | K_I `CALC_G_XFEM` (`LEGENDRE` 5) | G | K_I `POST_K1_K2_K3` |
|---|---|---|---|
| a/20 | +5,3 % | +1,9 % | +1,6 % |
| a/10 | +10 % | +4,8 % | +3,2 % |
| a/5 | +15 % | +11 % | +1,5 % |

Advies:

- **Rechte fronten**: hex8 met h ≈ a/20 geeft K en G binnen 0,3 %; hex20 is niet
  nodig. Het front en het scheurvlak mogen overal in het mesh liggen.
- **Gekromde fronten** (CIRKEL, ELLIPSE): `CALC_G_XFEM` heeft geen
  krommingscorrectie (de gemeshte scheur wel, `FORM_FISS='CERCLE'`, §2.1): K uit
  `CALC_G_XFEM` ligt 3 tot 5 % te hoog bij h = a/20 en meer op een grover mesh.
  Gebruik **K uit `POST_K1_K2_K3`** (kolom `K1_POST_K`, +1,6 %) of K uit G:
  K = √(G E/(1 − ν²)) (vlakke rek, modus I; +1,0 %). De bridge geeft een WARNING.
- **Mesh**: h ≤ a/20 loodrecht op het front; boven a/10 geeft de bridge een WARNING.
  Verfijn alleen rond het front (een buis van een paar elementen); de rest mag grof.
- R_INF/R_SUP automatisch (2h/4h) was goed in alle cases; forma07b gebruikt 2h/5h.

### 7.5 Interpretatie

- **K en G**: zoals bij een gemeshte scheur (§1.6). Aan een vrij oppervlak of een
  symmetrievlak (de eindpunten van het front) wijken de methoden af; beoordeel het
  binnenste van het front.
- **Velden in Mecway**: de verplaatsing is de fysische verplaatsing van elke knoop aan
  zijn eigen kant van de scheur (BR-07: boven- en onderlip gaan even ver open; BR-10:
  de opening van de penny crack +3,3 % t.o.v. Sneddon, met de afstand van de knopen
  tot het scheurvlak). Spanningen en von Mises zijn knoopvelden uit het mesh dat de
  scheur volgt (geen elementknoopwaarden, `SIGM_ELNO`). Een knoop die precies op het
  scheurvlak ligt, krijgt de waarde van één lip. Mecway tekent de scheur niet: de
  elementen die hij snijdt, worden over de scheur heen geïnterpoleerd.
- **Reacties**: uit het XFEM-resultaat; op knopen van gesneden elementen alleen het
  klassieke deel (NIET geverifieerd). Voorwaarden ver van de scheur zijn gewoon.

### 7.6 Wat niet kan

- Andere analyses dan lineair statisch: WARNING, de scheur wordt genegeerd.
- Schalen, balken, veren en losse knopen in het model, of `elem_hex8` = `3D_SI`:
  ERROR. `LINE_QUAD` werkt (BR-07 met LINE_QUAD: K_I 0,0 %, buiten de regressie).
- Contact tussen de lippen (een scheur onder druk: K_I < 0, WARNING), scheurgroei
  (`PROPA_FISS`), cohesieve scheuren en vertakte scheuren (`JONCTION`).
- Foutschatter en vermoeiing samen met XFEM (INFO/WARNING; ze worden overgeslagen).
- Een vorm uit een eigen levelset (`FONC_LN`/`FONC_LT`): niet gebouwd; dat kan met
  eigen `#ASTER`-code. Een scheur uit een vlakselectie ligt altijd op een knooplaag
  (§7.8); een vrije vorm dwars door de elementen kan niet.
- **NIET geverifieerd**: tet10, wedge15, pyr13 (tet4 en pyram5 wel, BR-11), `groep=`,
  meer dan één XFEM-scheur in een model, een ELLIPSE met a ≠ b, `afronding`.

### 7.7 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: #ASTER-XFEM: onbekend of onvolledig '...' | typefout in een sleutel, of geen `=` | sleutels uit §7.2 |
| ERROR: #ASTER-XFEM: '...' heeft geen geldige waarde | bijv. een vector met twee getallen, of een groep zonder `<<` `>>` | `(x, y, z)`, `<<selectie>>`, getal met of zonder eenheid |
| ERROR: ... geef de vorm / ontbreekt bij ... | `vorm=` ontbreekt of een verplichte sleutel van die vorm | §7.2 |
| ERROR: ... vect_x en vect_y staan niet loodrecht op elkaar / richting moet loodrecht op de normaal staan | assen fout | assen in het scheurvlak, loodrecht |
| ERROR: ... de scheur snijdt geen enkel volume-element | de scheur ligt buiten het model; vaak mm i.p.v. m | coördinaten in m, of met eenheid (`r=20 mm`) |
| ERROR: ... het front ligt buiten het model | de scheur snijdt het model helemaal door (of een HALFVLAK met het front buiten het model) | kleinere scheur, andere vorm of `richting` omdraaien |
| ERROR: ... groep '...' is geen elementselectie | naam van `groep=` | een bestaande elementselectie |
| ERROR: ... R_INF ... en R_SUP | R_INF ≥ R_SUP | beide 0 of R_INF < R_SUP |
| ERROR: #ASTER-XFEM werkt alleen in een model met alleen volume-elementen / kent alleen MODELISATION '3D' | schalen, balken, veren of `3D_SI` | §7.6, of een gemeshte scheur (§1) |
| WARNING: ... de elementen aan het front ... zijn groter dan 1/10 van de scheurmaat | grof mesh | verfijn rond het front (§7.4) |
| WARNING: ... gekromd front; K uit CALC_G_XFEM heeft geen krommingscorrectie | CIRKEL/ELLIPSE | gebruik `K1_POST_K` of G (§7.4) |
| WARNING: ... de voorwaarde op '...' staat schuin (LIAISON_OBLIQUE) | schuine symmetrie of opgelegde richting op knopen van gesneden elementen | §7.3 punt 2 |
| WARNING: Breukmechanica XFEM ... K_I uit CALC_G_XFEM en uit POST_K1_K2_K3 verschillen tot ...% | gekromd front, grof mesh, of `glad`/`graad` ongunstig | §7.3, §7.4 |
| WARNING: Breukmechanica XFEM ... K_I is negatief | druk op de scheur | zie §1.6 |
| WARNING: Breukmechanica XFEM ... POST_K1_K2_K3 gaf geen waarden | `POST_K1_K2_K3` faalde (`BRIDGE_XFEM_POSTK_FOUT` in de `.mess`) | gebruik `CALC_G_XFEM`; zie de `.mess` |
| ERROR: XFEM-scheur '...': vlak ... is geen vlak van een volume-element | de `XFEM_`-selectie bevat een schaal- of balkvlak | alleen vlakken van volume-elementen (§7.8) |
| ERROR: XFEM-scheur '...': een rib hoort bij meer dan twee vlakken | vertakt scheurvlak (bijv. een T) | één `XFEM_`-selectie per tak |
| ERROR: XFEM-scheur '...': de vlakselectie heeft geen rand binnen het volume | het vlak loopt helemaal door het model, of het zijn buitenvlakken | alleen de vlakken van de scheur, niet het ligament (§7.8) |
| ERROR: XFEM: twee scheuren met naam '...' | `naam=` en `XFEM_<naam>` gelijk | andere naam |
| WARNING: XFEM: '...' is een knoopselectie / elementselectie | `XFEM_` op een selectie van de verkeerde soort | een vlakselectie (§7.8) |
| WARNING: XFEM (#ASTER-XFEM, XFEM_-selecties) werkt alleen bij lineair statisch | andere analyse | normaal; de scheur wordt genegeerd |
| `<A> <XFEM_63>` in de `.mess` (ajustement van de levelset) | kwadratische elementen of een scheurvlak vlak bij knopen | onschuldig (BR-08, BR-09) |
| `<A> <QUALITY1_1>` | Code-Aster: XFEM is niet gekwalificeerd voor veiligheidsstudies (*études de sûreté*) | ter kennisgeving |

### 7.8 Scheur uit een vlakselectie (`XFEM_<naam>`)

Een scheur met een vorm die geen cirkel, ellips, rechthoek of halfvlak is (bijv. een
L-vorm of een scheur langs een las), geef je als **vlakselectie** in Mecway. De invoer
volgt de regel van de bridge: eerst wat Mecway zelf kent (een vlakselectie), dan een
speciale naam; een `#ASTER-XFEM`-regel is niet nodig.

1. Het mesh moet een **knooplaag in het scheurvlak** hebben: het scheurvlak bestaat
   uit elementvlakken en het front uit elementranden. De scheur zit níet open in het
   mesh (geen *Disconnect elements*); XFEM opent hem.
2. Selecteer de **vlakken in het scheurvlak** (alleen de scheur, niet het ligament).
   Die vlakken liggen binnen het model: zet Mecway in *Select faces*, schuif de
   *Cutting plane* tot de elementen aan één kant van het vlak verborgen zijn en kies
   de vlakken van de zichtbare elementen (Mecway Ltd., 2026, §9.12 en §17.2; met een
   scheurvlak in het model NIET in de Mecway-GUI geprobeerd). Het maakt niet uit van
   welk element (boven of onder) een vlak komt: de bridge richt de normalen zelf
   gelijk (BR-13 kiest ze afwisselend).
3. Maak er een *Named selection* van met de naam **`XFEM_<naam>`**, bijv. `XFEM_A`
   (hoofd- of kleine letters; XFEM is in het Nederlands en het Engels gelijk).
   `<naam>` is de naam van de scheur in de tabel en de log. Meer scheuren: meer
   selecties (`XFEM_A`, `XFEM_B`); ze mogen samen met `#ASTER-XFEM`-regels.
4. *Starten*, verder als §7.1.

Hoe de bridge het vertaalt: de vlakken gaan als losse cellen (`QUAD4`/`TRIA3`, alleen
hoekknopen, normalen gelijk gericht) in groep `BRXF<n>S`, de rand van de selectie die
**binnen het volume** ligt als `SEG2`-cellen in `BRXF<n>F` (het front; een rand op een
buitenvlak of een symmetrievlak is de mond van de scheur, geen front). Die cellen
horen niet bij het model. De normaal van het scheurvlak is een vaste keuze: de grootste
component van de gemiddelde normaal positief (een scheur in het vlak y = 0 krijgt
normaal +y). Waarom: bij een scheurvlak op een knooplaag hangt de oplossing iets van de
normaal af; met normaal −y ging in BR-13 de bovenlip 1,8 % verder open dan de onderlip
(K gelijk binnen 0,05 %), met +y is het resultaat gelijk aan BR-09. Dan

```
fiss_1 = DEFI_FISS_XFEM(MAILLAGE=mesh, TYPE_DISCONTINUITE='FISSURE',
                        DEFI_FISS=_F(GROUP_MA_FISS='BRXF1S', GROUP_MA_FOND='BRXF1F'))
```

(catalogus `defi_fiss_xfem.py`; zo ook de Code-Aster-testcases `sslv314b` en
`sslv320d`, waar het scheurvlak een apart mesh is). Code-Aster rekent de levelsets uit
die cellen. Gladmaken: `LAGRANGE` als elk stuk van het front recht is, anders
`LEGENDRE` (zoals bij de vormen, §7.3); de instellingen `fracture_r_inf`/`_sup` en
`fracture_legendre_degree` gelden. Sleutels per scheur (`punten=`, `glad=`, `r_inf=`)
zijn er voor een selectie niet.

Gemeten (BR-13, mesh van BR-09 met de scheur als selectie): K_I −0,06 %, G −0,05 %,
`POST_K1_K2_K3` +1,1 % t.o.v. Tada, net als BR-09 met `HALFVLAK` (§7.4). Omdat het
scheurvlak op een knooplaag ligt, krijgen de knopen in het vlak in Mecway de waarde van
één lip (§7.5); de knooplagen ernaast gaan even ver open (boven/onder −1,0004).

Niet mogelijk: een scheurvlak dwars door de elementen (gebruik een vorm), een vertakt
scheurvlak in één selectie, vlakken van schalen. NIET geverifieerd: een gekromd
scheurvlak of front uit een selectie, tet-elementen en kwadratische elementen (de
cellen gebruiken alleen de hoekknopen).

### 7.9 MED-bestand voor ParaView: de scheur zien opengaan

Mecway tekent de XFEM-scheur niet (§7.5). Met de instelling **MED-bestand voor
ParaView** (`med_export`) schrijft de bridge naast de gewone `<model>_<run-id>.rmed`
ook **`<model>_<run-id>_xfem.rmed`**: het mesh van `POST_MAIL_XFEM`, waarin de
elementen langs de scheur zijn opgedeeld en elke lip eigen knopen heeft, met de velden
`DEPL`, `SIGM_NOEU` en `SIEQ_NOEU` van `POST_CHAM_XFEM` (`IMPR_RESU`, UNITE 81 in de
`.export`). Open het met de knop *ParaView* of *AsterStudy* in het resultatenscherm of het
convergentiescherm ([Handleiding §5.1](Handleiding.md#51-resultaten-later-opnieuw-inladen-kleine-liml)):
beide openen de `_xfem.rmed` vóór de andere resultaatbestanden van de run. Met *Warp By
Vector* op `DEPL` zie je de scheur opengaan. De groepen van het model (elsets, selecties) staan erin; de velden
heten `res_xvisDEPL`, `res_xvisSIGM_NOEU` en `res_xvisSIEQ_NOEU`. De gewone `.rmed`
heeft de velden op het oorspronkelijke mesh (zonder opening).

Gemeten (BR-14, teruggelezen met de MEDCoupling van de Code-Aster-installatie): de drie
velden en de groep van het onderdeel staan erin, en de opening tussen de lipknopen in
het midden van de scheur is 99,6 % van de opening die Mecway tussen de knopen op
±h/2 ziet.

## 8. Bronnen

- EDF R&D. *code_aster 17.4*: catalogus `lib/aster/code_aster/Cata/Commands/`
  `defi_fond_fiss.py`, `calc_g.py`, `post_k1_k2_k3.py`, `crea_resu.py`; testcase
  `forma07a` (`share/aster/tests`); XFEM: `defi_fiss_xfem.py`, `modi_modele_xfem.py`,
  `calc_g_xfem.py`, `post_mail_xfem.py`, `post_cham_xfem.py`, `proj_champ.py`,
  `MacroCommands/post_k1_k2_k3_ops.py` (meer fronten: `getCrackTipMultiplicity`),
  testcase `forma07b` (com1/com2, mesh `forma07b.41`); scheur uit een groep cellen
  (`GROUP_MA_FISS`/`GROUP_MA_FOND`): testcases `sslv314b`, `sslv320d`. De U-documenten (U4.82.03 `CALC_G`, U4.82.05
  `POST_K1_K2_K3`, U2.05.01 breukmechanica) zijn niet lokaal aanwezig: NIET ingezien.
- Mecway Ltd. (2026). *Mecway 33 manual*, §4.2.10 Disconnect elements, §4.2.11 Merge
  nearby nodes, §9.12 en §17.2 (*Select faces*, *Cutting plane*)
  (`C:\Program Files\Mecway\manual.pdf`).
- Tada, H., Paris, P.C. & Irwin, G.R. (2000). *The Stress Analysis of Cracks
  Handbook*, 3e druk. New York: ASME Press, p. 2.2 (middenscheur in een strook),
  p. 24.2 (cirkelvormige scheur: K = 2σ√(a/π), opening 8(1 − ν²)σ√(a² − r²)/(πE)).
- Sneddon, I.N. (1946). The distribution of stress in the neighbourhood of a crack in
  an elastic solid. *Proc. R. Soc. Lond. A* 187, 229-260 (cirkelvormige scheur). Niet
  lokaal ingezien; via Tada p. 24.2.
- Anderson, T.L. (2005). *Fracture Mechanics: Fundamentals and Applications*, 3e druk.
  Boca Raton: CRC Press (K_IC, vlakke rek, randeffect). Niet lokaal ingezien;
  algemene achtergrond.
