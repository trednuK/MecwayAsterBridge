# Lassen: bewegende warmtebron, restspanning, vervorming en metallurgie

*English version: [Welding.md](en/Welding.md)*

Het temperatuurveld van een lasrups: een warmtebron die met een vaste snelheid langs
een baan beweegt, in een transiente thermische analyse (Mecway *Thermal transient*,
T31 → `ther_3d`, `THER_LINEAIRE` of `THER_NON_LINE`; zie [Thermisch.md](Thermisch.md)).
Met een *Thermal stress* in hetzelfde model rekent de bridge daarna in dezelfde job de
**restspanning en vervorming** (`STAT_NON_LINE` met de temperatuur als belasting, §9).
Met `#ASTER-METALLURGIE` volgen ook de **fase-omzettingen** in staal (ferriet, perliet,
bainiet, martensiet, austeniet), de **hardheid** en, als optie, hun invloed op de
restspanning (§10). Code: `Scripts/bridge_welding.py` (de bron),
`Scripts/bridge_thermal.py` (de rest van het thermische model),
`Scripts/bridge_thermomech.py` (de mechanische keten), `Scripts/bridge_metallurgy.py`
(de metallurgie). Code-Aster 17.4.

Twee invoerroutes, allebei zonder Mecway-uitbreidingen:

| Route | Wanneer | Hoe |
|---|---|---|
| **A. `#ASTER-LASBRON`** (aanbevolen) | een gewone lasbron langs een rechte lijn of een knopenpad | een regel in Mecway's *Custom model definition*: vermogen, rendement, snelheid, baan en de Goldak-afmetingen; de bridge maakt de bron, kiest de elementen, controleert tijdstap en mesh en meldt na de run welk deel van het vermogen het mesh opneemt |
| **B. Mecway-formule** | een eigen bronvorm, of het model ook met Mecway's eigen solver rekenen | *Internal heat generation* (elementen) of *Heat flux* (vlakken) met een formule in x, y, z en t; de bridge vertaalt de formule letterlijk naar een Code-Aster-`FORMULE` |

Er is **geen aparte analyse**: een T31-model met een lasbron rekent gewoon in
*Thermisch* (`ther_3d`, ook via `auto`); zet je er een *Thermal stress* bij, dan volgt
de mechanische keten vanzelf (§9); een regel `#ASTER-METALLURGIE` voegt de fasen toe
(§10); toevoegmateriaal dat pas "geboren" wordt als de bron er langs komt: sleutel
`geboorte=` (§11). Grenzen: §7, §9.7, §10.8 en §11.6.

## 1. Werkwijze in Mecway, stap voor stap

Voorbeeld: verificatiemodel `TestFiles/Verificatie/modellen/WE-02.liml` (openen in
Mecway): een halve stalen plaat (symmetrievlak y = 0) van 55 × 15 × 15 mm, een las van
30 mm langs de x-as op het bovenvlak z = 0, 5 mm/s, 1000 W in het werkstuk.

### 1.1 Het model

1. **Geometrie en mesh.** Volume-elementen (hex8, hex20, tet, wedge). Maak de mesh
   **fijn langs de rups**: elementen niet groter dan 0,8 × de kleinste halve as van de
   bron in die richting (§4.2). In het voorbeeld: 0,5 mm tot 7 mm van de baan, daarbuiten
   groter (tot ~3 mm). Een symmetrievlak door de baan scheelt de helft van de elementen:
   een geïsoleerd vlak (geen randvoorwaarde) is het symmetrievlak.
2. **Materiaal.** *Thermal*: geleidbaarheid en soortelijke warmte, plus de dichtheid.
   Temperatuurafhankelijk mag (*Temperature dependent*: tabellen voor λ(T) en c(T),
   Mecway-handleiding §8.6); de bridge rekent dan met `THER_NON_LINE` (§6).
3. **Analyse.** *Analysis settings* → *Thermal transient*; *Time period* = de lastijd
   plus eventueel de afkoeltijd, *Time step* volgens §4.1 (voorbeeld: 6 s, 0,1 s).
4. **Begintemperatuur.** *Initial conditions* → *Temperature* op alle knopen (bijv.
   293,15 K). Zonder begintemperatuur start Mecway, en dus ook de bridge, op 0 K.
5. **Randen.** Convectie en straling op de vrije vlakken mogen (*Convection*,
   *Radiation*); in het voorbeeld zijn alle vlakken geïsoleerd, zodat de energiebalans
   exact te controleren is.

### 1.2 De lasbron (route A)

Kies in *Analysis settings* de solver CCX (dan verschijnt in de outline-boom *CCX* →
*Custom model definition*) en typ (het voorbeeld WE-02):

```
** ASTER-LASBRON Q=1250, eta=0.8, v=0.005, start=(0.01, 0, 0), richting=(1, 0, 0)
** ASTER-LASBRON af=0.001, ar=0.002, b=0.001, c=0.001, symmetrie=1
```

- Alle waarden in **SI**: W, m/s, m, s (zoals alle `#ASTER`-regels). Coördinaten zijn
  die van het Mecway-model in meter: een punt op 10 mm schrijf je als 0.01.
- Opeenvolgende regels horen bij één bron; een regel die met `Q=` begint (of met het
  woord `nieuw`/`new`), start een volgende bron (meerdere lagen of lassen achter elkaar,
  elk met een eigen `t0`).
- In een OpenRadioss-veld schrijf je `#ASTER-LASBRON`, in Mystran `$ASTER-LASBRON`
  ([ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md) §1). Ook `#ASTER-WELD`.
- De sleutels hebben Engelse synoniemen (§2): `direction=` voor `richting=`, `symmetry=`
  voor `symmetrie=`, enz.

### 1.3 Of: de bron als Mecway-formule (route B)

Maak een elementselectie met de elementen langs de rups (de formule wordt in elk
Gauss-punt van die elementen per stap uitgerekend; een kleine selectie rekent sneller)
en zet er *Internal heat generation* op met een formule, bijv. een halve Gauss-bol met
r = 0,75 mm, 1000 W, 5 mm/s vanaf x = 10 mm (verificatie WE-03; eenheid W/m³,
positie in mm, tijd in s):

```
4.423879394e12*e^(-3*((x-10-5*t)^2+y^2+z^2)/0.75^2)
```

Mecway kent geen `exp`: schrijf `e^(...)`. De bridge zet de formule om naar Python
(`^` → `**`, functies zoals `sin`, `heaviside`, `unittriangle`) met de eenheden uit
de Mecway-attributen. Dezelfde route werkt voor *Heat flux* op vlakken, *Convection*
(coëfficiënt, omgevingstemperatuur), *Radiation* en *Temperature* (verificatie WE-06).

### 1.4 Starten en volgen

Hoofdvenster: *Actieve analyse* `auto` (of *Thermisch*), *Starten*. De log
(`<model>_<run-id>_bridge_log.txt`) toont per bron:

```
INFO: #ASTER-LASBRON 1: brongroep automatisch, 9718 elementen binnen 0.006 m van de baan.
INFO: #ASTER-LASBRON 1: verspringing 0.0005 m per stap (0.167 x af + ar).
INFO: #ASTER-LASBRON 1: elementen langs de baan tot 0.50 x de halve as (langs de lasrichting).
INFO: #ASTER-LASBRON 1: Goldak, Q_eff = 1000 W (eta 0.8), v = 0.005 m/s, baan 0.03 m van t = 0.0 tot 6 s, ...
```

Na de run staat in het statusvak de **energiecontrole**: welk deel van η·Q het mesh
werkelijk opneemt, op vijf tijdstippen (voorbeeld: "het mesh neemt 100.0..100.0% van
het vermogen 500 W op"; 500 W door `symmetrie=1`). Wijkt het meer dan 2% af, dan volgt
een WARNING: de mesh is te grof voor de bron, of de bron ligt deels buiten het model.

### 1.5 Resultaten in Mecway

`temperature` per tijdstap (Kelvin) en de warmteflux `heatflux*`, zoals bij elke
transiente thermische analyse. Kijk naar het temperatuurverloop in een knoop naast de
rups (*Graph* van een knoop over de tijd), de piektemperatuur per knoop (de smeltzone
is waar die boven de smelttemperatuur komt) en de isothermen achter de bron.

## 2. Sleutelwoorden van `#ASTER-LASBRON`

| Sleutel (synoniemen) | Eenheid | Standaard | Betekenis | Wanneer aanpassen |
|---|---|---|---|---|
| `Q` (`vermogen`, `power`) | W | verplicht | boogvermogen U·I | - |
| `eta` (`rendement`, `efficiency`) | - | 1 | deel van Q dat in het werkstuk komt (0 < η ≤ 1) | TIG ~0,6–0,7, MIG/MAG ~0,8, onder poeder ~0,9 (literatuurwaarden, NIET door de bridge gemeten) |
| `v` (`snelheid`, `speed`) | m/s | verplicht | lassnelheid | - |
| `start` (`begin`) | m | - | beginpunt (x, y, z) van een rechte baan | - |
| `richting` (`dir`, `direction`) | - | - | richting van de rechte baan (wordt genormeerd) | - |
| `lengte` (`length`) | m | tot het einde van de analyse | lengte van de rechte baan | de las stopt vóór het einde van de analyse (afkoelen) |
| `pad` (`path`, `baan`) | `<<knoopselectie>>` | - | baan door knopen (in plaats van start/richting): de knopen worden een keten vanaf de knoop het dichtst bij `start` (anders een uiteinde) | gekromde of geknikte las (stuksgewijs recht) |
| `diepte` (`depth`) | - | (0, 0, −1) | richting het materiaal in (loodrecht op het oppervlak) | het lasvlak is niet het bovenvlak z = max |
| `af`, `ar` | m | verplicht (of `r`) | halve as vóór en achter de bron (langs de lasrichting) | ijken op de smeltzone (macro-etsfoto); vuistregel af ≈ halve breedte, ar ≈ 2–4 × af (Goldak e.a., 1984; NIET door de bridge gemeten) |
| `b` | m | verplicht (of `r`) | halve breedte (dwars) | idem: halve breedte van de smeltzone |
| `c` | m | verplicht (of `r`) | diepte | inbranddiepte |
| `r` | m | - | af = ar = b = c = r (halve Gauss-bol) | een eenvoudige bron |
| `ff`, `fr` | - | 2af/(af+ar), 2ar/(af+ar) | verdeling voor/achter (q continu in de bron) | alleen als de literatuur andere waarden geeft; ff + fr ≠ 2 geeft een WARNING (vermogen (ff+fr)/2·η·Q) |
| `t0` (`tstart`) | s | 0 | starttijd van de bron | tweede laag of tweede las |
| `t1` (`teind`, `tend`) | s | einde baan | eindtijd van de bron | de bron eerder stoppen |
| `groep` (`group`) | `<<elementselectie of component>>` | selecties/componenten met voorvoegsel `LASNAAD_`, anders automatisch | elementen waarop de bron werkt | een eigen keuze; de automatische groep is alle volume-elementen binnen 3 × de grootste halve as van de baan |
| `symmetrie` (`symmetry`) | - | 0 | aantal symmetrievlakken door de baan (alleen voor de energiecontrole: het mesh krijgt 1/2ⁿ van de bron) | halve plaat: 1 |
| `geboorte` (`birth`) | `ja` / `nee` / `<<selectie>>` | `nee` | toevoegmateriaal dat pas geboren wordt als de bron er langs komt (§11) | lassen met toevoegmateriaal, meerdere lagen |
| `voorloop` (`lead`) | m | 2 × `af` | afstand voor de bron waarop het toevoegmateriaal geboren wordt (§11.2) | zelden |

Een onbekende sleutel, een ontbrekende verplichte waarde of een waarde die geen getal
is, geeft een ERROR en de run stopt (§8).

## 3. Hoe de bridge vertaalt

- **Bronvorm** (Goldak e.a., 1984), met ξ langs de lasrichting t.o.v. de huidige
  bronpositie, η dwars, ζ de diepte:
  q = 6√3·f·η·Q / (a·b·c·π√π) · exp(−3ξ²/a² − 3η²/b² − 3ζ²/c²), a = af en f = ff vóór
  de bron (ξ ≥ 0), a = ar en f = fr erachter. Over de halve ruimte onder het oppervlak is
  de integraal (ff + fr)/2·η·Q. Positie s(t) = v·(t − t0) langs de baan; buiten
  [t0, t1] en voorbij het einde van de baan is q = 0. Bij een geknikt pad draait het
  assenstelsel per segment mee.
- **Code-Aster**: een Python-functie `_lb_goldak` in de `.comm`, een
  `FORMULE(NOM_PARA=('X', 'Y', 'Z', 'INST'))` en `AFFE_CHAR_THER_F` `SOURCE` op de
  brongroep (catalogus `affe_char_ther_f.py`); de last staat in `EXCIT` van
  `THER_LINEAIRE`/`THER_NON_LINE`. Code-Aster rekent de bron per stap in de
  Gauss-punten (θ-gewogen tussen begin en einde van de stap, instelling `theta`).
- **Brongroep**: alleen volume-elementen (schalen en balken krijgen geen bron, WARNING).
  Automatisch: elementen binnen 3 × de grootste halve as van de baan (daarbuiten is q
  < 2·10⁻¹² van de piek); dat beperkt de rekentijd van de formule.
- **Energiecontrole** (na de solve, in de job): `CALC_VECT_ELEM` `CHAR_THER` +
  `ASSE_VECTEUR` geeft de knooplasten van de bron zoals de solver ze integreert; hun som
  is het vermogen dat het mesh opneemt. Regel `BRIDGE_LASBRON <bron> <t> <W> <doel W>`
  in de `.mess`, samengevat in log en statusvak.
- **Route B** (formule): `FORMULE` met de Mecway-uitdrukking, x/y/z/t omgerekend met
  `positionunit`/`timeunit` en de uitkomst met `unit` (mechanische lasten: zie
  [Handleiding.md](Handleiding.md), Formules). Stationair (T30) krijgt een formule in t de waarde op t = 1 s
  (zoals een tijdstabel).
- **Meer bronnen samen**: alle bronnen met een functie (lasbronnen, en *Internal heat
  generation*s met een formule of tijdstabel) staan in **één** last; per deel van het
  mesh telt een `FORMULE` de bronnen op die er liggen. Code-Aster 17.4 rekent twee
  lasten `AFFE_CHAR_THER_F` met `SOURCE` in één analyse anders allebei met de functie
  van de eerste. Een lasbron en een formule- of tabelbron kunnen dus samen (TH-42).
- **Schalen in het model** die de bridge als `PLAN` rekent en daarvoor draait
  ([Thermisch.md](Thermisch.md) §3): baan en formules worden mee gedraaid.

## 4. Instellingen: tijdstap, mesh, theta

### 4.1 Tijdstap

De bron verspringt per stap v·Δt. De bridge geeft een **WARNING als v·Δt > ½(af + ar)**,
met de stap die het wel haalt. Gemeten (WE-01/WE-01b, Gauss-bron r = 0,75 mm, h = 0,5
mm, θ = 0,57; afwijking van de temperatuur t.o.v. de analytische oplossing van
dezelfde bron, `tests_lassen.goldak_exact`):

| v·Δt | naast de bron (3 mm) | op de lasas 6 mm erachter |
|---|---|---|
| (af + ar)/6 (Δt = 0,05 s) | −1,4% | −0,25% |
| (af + ar)/2 (Δt = 0,15 s, grens van de melding) | −2,2% | −2,9% |
| 1 × (af + ar) (Δt = 0,3 s) | −4,9% | −26% (de bron slaat knopen over) |

T.o.v. de run met (af + ar)/6 is de grens −0,8% (naast de bron) en −2,7% (lasas); die
getallen staan in het commentaar bij `bridge_welding.MAX_JUMP`. Het is een afwijking
van de temperatuur, geen energieverlies: de energie op t = 6 s is bij beide stappen
+0,06% (WE-01, WE-01b; opnieuw gemeten op 07-10-2026, de rij 1 × (af + ar) bij de
bouw).

Advies: v·Δt ≤ (af + ar)/2 voor het temperatuurveld naast de rups, ≤ (af + ar)/6 voor
piektemperaturen op de lasas. Na het lassen (afkoelen) mag de stap groter: maak dan
een tweede analyse of neem een stap die overal past.

### 4.2 Mesh langs de rups

De bron wordt per element met 2 Gauss-punten per richting (hex8) geïntegreerd.
Integratiefout per richting, slechtste ligging van de bron t.o.v. de elementen
(berekend): 0,03% bij h = 0,67·a, 0,3% bij 0,8·a, 1,8% bij 1,0·a, 7,6% bij 1,33·a (a =
de halve as in die richting). De bridge geeft een **WARNING als een element langs de
baan in een richting groter is dan 0,8 × de halve as** (lasrichting: min(af, ar);
dwars: b; diepte: c). De energiecontrole na de run laat het werkelijke effect zien
(WE-01, h = 0,67 r: +0,09%; een proefmodel met elementen van 2 × r: +19%).

Daarbuiten mag de mesh grover worden, maar niet te snel: het temperatuurveld naast en
achter de bron is steil. In WE-01 is de fijne zone 7 mm breed en diep (~10 × de
bronstraal) met daarna 5 elementen die geometrisch groeien tot 15 mm.

### 4.3 Theta

`theta` (pagina *Thermisch*, standaard 0,57) blijft. Gemeten op een WE-01-variant
(h = 0,375 mm, Δt = 0,15 s, Δt·a/h² ≈ 7): Crank-Nicolson (0,5) gaf op de lasas 6 mm
achter de bron 21% minder dan θ = 0,57 (niet-monotoon schema bij een grote Δt·a/h²);
θ = 1 week tot 10% af van 0,57 (naast de bron hoger, schuin erachter lager). Een
kleinere stap maakt θ minder belangrijk.

## 5. Interpretatie

- **Rosenthal** (1946): een puntbron Q op een half-oneindig, geïsoleerd lichaam geeft
  quasi-stationair T − T0 = Q/(2πkR)·exp(−v(R + ξ)/(2a)). Buiten de bron (R ≥ 4 × de
  bronstraal) ligt de FEM-oplossing daar binnen 1% van (WE-01; met v·Δt op de
  meldingsgrens 3,6%, WE-01b). Dichter bij de bron bepaalt de bronvorm de temperatuur;
  daar heeft Rosenthal geen betekenis.
- **Bronparameters** zijn geen materiaalconstanten: ijk af, ar, b, c (en η) op een
  gemeten smeltzone (macro-ets) of thermokoppel. De temperatuur in de smeltzone zelf is
  modelafhankelijk; temperaturen buiten de smeltzone en afkoeltijden (t8/5) zijn
  betrouwbaarder.
- **Smeltwarmte**: de bridge kent geen latente warmte; neem die op in c(T) (een piek
  rond het smelttraject, *Temperature dependent*), zodat de enthalpie klopt.
- **Energiebalans**: zonder convectie en straling is ∫ρ(H(T) − H(T0))dV = η·Q·t
  (WE-01/02/05: ≤ 0,06%); met verliezen kleiner.
- **Vergelijking met Mecway** (route B, WE-03, headless): Mecway integreert de formule
  net zo (energie gelijk tot 1e-4), maar rekent de last op het einde van de stap
  (KNOWN_BUGS 14): de bron loopt dan v·Δt/2 voor. Naast de bron is Mecway daardoor
  warmer (WE-03, Δt = 0,05 s: +4,6% t.o.v. de bridge, +3,2% t.o.v. de analytische
  oplossing; schatting exp(v²Δt/(4a)) − 1 = 5%), op de lasas 6 mm erachter kouder
  (−2,1% / −2,3%); Mecway ligt binnen 1,5% van de analytische oplossing op t + Δt/2.
  Een kleinere stap verkleint het verschil evenredig.

## 6. Temperatuurafhankelijke λ en c (Mecway *Temperature dependent*)

Mecway schrijft `<thermal type="TempDependent">` met `<thermalconductivity temp=".."
value=".."/>`- en `<specificheat temp=".." value=".."/>`-rijen (lineair geïnterpoleerd,
buiten de tabel het dichtstbijzijnde punt: Mecway-handleiding §8.6). De bridge maakt
daar `DEFI_MATERIAU` `THER_NL` van (`LAMBDA` en `RHO_CP` als `DEFI_FONCTION` van de
temperatuur, `PROL` constant) en rekent met `THER_NON_LINE` (`newton_*`-instellingen
van de pagina *Thermisch*). Twee aanpassingen, gemeten met Code-Aster 17.4 (WE-04b):

- de ρc-tabel wordt verlengd tot 0 K en 10 000 K boven het laatste punt, en verfijnd
  tot punten om de 10 graden: `THER_NON_LINE` rekent met de enthalpie β(T) die het uit
  de tabelpunten afleidt; met alleen Mecway's punten miste 13% van de energie na de
  eerste stap (2,8% na 2 s), nu 0,01%;
- λ(T) blijft zoals ingevoerd (WE-04a: exact gelijk aan de Kirchhoff-oplossing).

Mecway zelf rekent met een schijnbare c(T): zijn energiebalans wijkt 0,2–0,3% af; de
temperaturen liggen binnen 0,15% van de bridge (WE-04b).

## 7. Wat (nog) niet kan

- **Mechanische keten** (restspanning, vervorming): zie §9; de grenzen daarvan in
  §9.7.
- **Toevoegmateriaal dat geboren wordt**: kan met `geboorte=` (§11); de grenzen
  daarvan in §11.6.
- **Metallurgie** (fasen, hardheid, transformatierek): §10; de grenzen in §10.8.
- De lasbron werkt alleen op **volume-elementen**, niet op schalen of balken.
- Alleen de **Goldak**-vorm (en de halve Gauss-bol als bijzonder geval); een andere
  vorm (conisch, oppervlakte-Gauss) kan via een Mecway-formule (route B).
- Een **gekromde baan** is stuksgewijs recht tussen de knopen van `pad`; de snelheid
  is constant.
- Route B: een formule in x, y, z voor een *totale* warmtestroom (*Heat flow*), voor
  convectie of straling op een **schaalvlak** of als begintemperatuur wordt niet
  vertaald (ERROR met de reden).

## 8. Meldingen → oorzaak → oplossing

| Melding (log) | Oorzaak | Oplossing |
|---|---|---|
| `ERROR: #ASTER-LASBRON vraagt een transiente thermische analyse` | het model is T30 (stationair) of mechanisch | Mecway *Thermal transient* (T31) |
| `WARNING: #ASTER-LASBRON werkt alleen in een transiente thermische analyse ...; hier genegeerd` | de regel staat in een mechanisch model | verwijderen, of de analyse T31 maken |
| `ERROR: #ASTER-LASBRON: onbekend of onvolledig '...'` | tikfout in een sleutel, of `sleutel` zonder `=` | sleutel uit §2 |
| `ERROR: #ASTER-LASBRON (bron n): ontbreekt: ...` | Q, v of de afmetingen ontbreken | aanvullen (of `r=`) |
| `ERROR: ... geef de baan: start=... en richting=..., of pad=<<knoopselectie>>` | geen baan | `start` + `richting`, of `pad` |
| `ERROR: ... '...' heeft geen geldige waarde` | geen getal, vector zonder drie waarden, selectie zonder `<< >>` | `start=(0.01, 0, 0)`, `pad=<<Naam>>` |
| `ERROR: ... geen volume-elementen binnen ... m van de lasbaan` | baan buiten het model, meestal mm i.p.v. m | coördinaten in meter |
| `ERROR: ... pad '...' is geen knoopselectie met knopen` | verkeerde naam, of een vlak-/elementselectie | een knoopselectie langs de las |
| `ERROR: ... de brongroep heeft geen volume-elementen` | `groep` wijst schalen of balken aan | een elementselectie met volume-elementen |
| `WARNING: ... de bron verspringt ... m per tijdstap` | v·Δt > ½(af + ar) | kleinere *Time step* (advies in de melding) |
| `WARNING: ... elementen langs de lasbaan zijn ... groot` | mesh grof t.o.v. de bron | mesh verfijnen langs de rups (§4.2) of de bron groter |
| `WARNING: ... de bron is op het einde van de analyse ... nog niet aan het einde van de baan` | *Time period* korter dan de lastijd | langere tijdsduur, of `lengte`/`t1` |
| `WARNING: Lasbron n: opgenomen vermogen wijkt meer dan 2% af` | grove mesh, de bron ligt deels buiten het model, of een symmetrievlak zonder `symmetrie=` | mesh verfijnen; `symmetrie=1` bij een halve plaat (neemt het mesh 1/2 of 1/4 van de bron op, dan noemt de melding `symmetrie=1` of `2`) |
| `WARNING: ... ff + fr = ... <> 2` | eigen ff/fr | bewust? Anders ff/fr weglaten |
| `ERROR: Niet vertaald: heatflow op '...': formule in x, y, z voor een totale warmtestroom` | route B met *Heat flow* | *Internal heat generation* (W/m³) of *Heat flux* (W/m²) |

## 9. Restspanning en vervorming: de keten thermisch → mechanisch

Een T31-model met een **Thermal stress** (Mecway-handleiding §9.25) rekent de bridge in
één Code-Aster-job twee keer: eerst thermisch zoals hierboven, daarna mechanisch
(`STAT_NON_LINE`) met het temperatuurveld van elke tijdstap als belasting. Mecway zelf
gebruikt een Thermal stress alleen in een mechanische analyse, maar bewaart hem (met
Fixed support, Displacement en de mechanische materiaalgegevens) ook in een thermisch
model; de bridge leest ze dan wel. Zonder Thermal stress blijft het een gewone
thermische analyse (de mechanische voorwaarden tellen niet mee, INFO in de log).
Er is geen aparte analyse en geen instelling om aan te zetten: `auto` stuurt T31 naar
*Thermisch* (`ther_3d`) en de Thermal stress schakelt de keten in.

### 9.1 Werkwijze in Mecway, stap voor stap

Voorbeeld: `TestFiles/Verificatie/modellen/WE-10.liml` (openen in Mecway): een halve
plaat 40 × 15 × 5 mm (symmetrievlak y = 0) met een rups van 30 mm op het bovenvlak.

1. **Thermisch model** zoals in §1: *Thermal transient*, begintemperatuur, de lasbron
   (`#ASTER-LASBRON`) en de thermische randen. Laat de analyse lang genoeg doorlopen
   om af te koelen (§9.5): de restspanning is de spanning op het laatste tijdstip.
2. **Materiaal**, tabblad *Mechanical*: *Young's modulus*, *Poisson's ratio* en
   *Thermal expansion coefficient* (zonder α geen thermische rek: WARNING). Plasticiteit
   (tabblad *Plastic*): *Bilinear isotropic*/*kinematic* (vloeigrens, *tangent modulus*)
   of een hardingscurve. Temperatuurafhankelijke E, ν, α, vloeigrens en versteviging
   kent Mecway niet (handleiding §8.6: alleen λ en c): die komen uit
   `#ASTER-MATERIAAL` (§9.2).
3. **Opleggingen**: *Fixed support* of *Displacement* (een Displacement is een
   verplaatsing langs één richting; voor x en z twee voorwaarden). Een vrij krimpend
   werkstuk leg je **statisch bepaald** vast: symmetrievlakken plus een knoop met x en
   z vast en een tweede knoop met alleen z vast (WE-10). Een inklemming verhindert de
   krimp en geeft hogere restspanningen (en minder vervorming).
4. **Thermal stress** met als *Reference temperature* de begintemperatuur (WARNING als
   die verschilt: dan is er op t = 0 al thermische rek).
   Mecway toont Thermal stress, Fixed support en Displacement mogelijk alleen bij een
   mechanisch analysetype: zet de analyse dan eerst op *Static 3D*, voeg ze toe, en zet
   de analyse daarna terug op *Thermal transient* (Mecway bewaart ze; headless
   nagelopen met Mecway 33 op WE-08: de voorwaarden blijven in de opgeslagen `.liml`
   staan en Mecway rekent het thermische deel zonder melding). Dat de GUI ze zo
   toont, is NIET in de Mecway-GUI nagelopen.
5. Eventueel `#ASTER-MATERIAAL` in *Custom model definition* (§9.2).
6. Hoofdvenster: *Actieve analyse* `auto` (of *Thermisch*), *Starten*.

In Mecway komen per tijdstap: `temperature` en `heatflux*` (thermisch) en
`displ*`, `stress*`, `vonmises`, `reactionforce*`, `plasticstrain*` en
`equivalentplasticstrain` (mechanisch; standaard alle, of de keuze bij
*Resultaatvelden naar Mecway* als daar een mechanisch veld bij staat). In de log en het
statusvak staat de samenvatting op het laatste tijdstip (regel `Thermomechanisch, t =
...`): temperatuurbereik, grootste verplaatsing per richting, von Mises en het bereik
van σxx, σyy, σzz, en de grootste cumulatieve plastische rek.

### 9.2 `#ASTER-MATERIAAL`: temperatuurafhankelijke mechanische eigenschappen

```
** ASTER-MATERIAAL Staal: TC=(20, 200, 400, 600, 800, 1000, 1200, 1500),
** ASTER-MATERIAAL     E=(210e9, 200e9, 180e9, 120e9, 60e9, 30e9, 15e9, 10e9),
** ASTER-MATERIAAL     SY=(355e6, 300e6, 250e6, 150e6, 50e6, 25e6, 15e6, 10e6),
** ASTER-MATERIAAL     ALPHA=(1.2e-5, 1.25e-5, 1.3e-5, 1.35e-5, 1.4e-5, 1.45e-5,
** ASTER-MATERIAAL            1.5e-5, 1.5e-5), H=1e9, TC_CUT=1500
```

Een regel die met `<Mecway-materiaal>:` begint, start een materiaal; de volgende regels
zonder naam horen erbij (een lijst mag over twee regels lopen). Ook `#ASTER-MATERIAL`.
Alleen in de keten thermisch → mechanisch; waarden in SI.

| Sleutel | Eenheid | Standaard | Betekenis | Wanneer aanpassen |
|---|---|---|---|---|
| `T` of `TC` | K of °C | - | temperaturen van de tabel (oplopend); verplicht bij lijsten | altijd bij temperatuurafhankelijke waarden |
| `E` | Pa | Mecway *Young's modulus* | elasticiteitsmodulus | literatuurtabel van het materiaal; boven ~1200 °C niet lager dan ~5% van E(20 °C) (convergentie) |
| `NU` | - | Mecway *Poisson's ratio* | dwarscontractie | zelden |
| `ALPHA` | 1/K | Mecway *Thermal expansion coefficient* | **gemiddelde (secans) uitzettingscoëfficiënt** t.o.v. `T_ALPHA`: ε_th = α(T)·(T − T_ALPHA) | tabellen geven vaak de gemiddelde α vanaf 20 °C: zet dan `TC_ALPHA=20`; een *momentane* α eerst omrekenen |
| `T_ALPHA` / `TC_ALPHA` | K / °C | referentietemperatuur van de Thermal stress | temperatuur waarop ε_th = 0 in de tabel (`TEMP_DEF_ALPHA`) | als de α-tabel een andere referentie heeft |
| `T_CUT` / `TC_CUT` | K / °C | geen | boven deze temperatuur blijft de thermische rek constant (smelten; Lindgren 2001) | **altijd bij lassen**: de solidus- of smelttemperatuur. Zonder afkap groeit de rek in het smeltbad door (4,6% bij 3400 K in WE-10b) en convergeert de mechanische stap slecht |
| `SY` | Pa | Mecway *yield strength* (bilineair) | vloeigrens | literatuurtabel; boven ~1200 °C een kleine waarde (bijv. 10 MPa) |
| `H` | Pa | Mecway *tangent modulus* | plastische modulus dσ/dε_p (zoals Mecway's tangent modulus, [Instellingen_contact_en_nietlineair.md](Instellingen_contact_en_nietlineair.md)) | lineaire versteviging |
| `ET` | Pa | - | in plaats van `H`: helling na de vloeigrens in **totale** rek (Code-Aster `D_SIGM_EPSI`) | als de tabel zo gegeven is; ET = E·H/(E + H) |
| `versteviging` (`hardening`) | `iso` / `kin` | het Mecway-type (isotroop als niet plastisch) | isotrope (`VMIS_ISOT_LINE`) of kinematische (`VMIS_CINE_LINE`) versteviging | kinematisch bij herhaald opwarmen/afkoelen (Bauschinger-effect, meerlaags lassen) |

Eén getal is een constante; een lijst heeft evenveel waarden als `T`. Lineair
geïnterpoleerd, buiten de tabel constant (zoals Mecway's eigen tabellen, §8.6).
Ontbreekt een sleutel, dan geldt de Mecway-waarde. Met `SY` (of `H`/`ET`) wordt het
materiaal bilineair plastisch, ook als het Mecway-materiaal elastisch is; een
Mecway-hardingscurve (`TRACTION`) wordt dan vervangen (WARNING). Zonder
`#ASTER-MATERIAAL` rekent de keten met de constante Mecway-waarden, ook met een
hardingscurve.

### 9.3 Instellingen

Pagina *Thermisch* (`ther_3d`); de Newton- en convergentie-instellingen gelden voor
beide solves.

| Instelling (sleutel) | Standaard | Wanneer aanpassen |
|---|---|---|
| *COMPORTEMENT DEFORMATION* (`deformation`) | PETIT | kleine rekken en rotaties: goed voor de meeste lassen (WE-07..10). `GDEF_LOG` alleen bij grote vervorming (dunne platen die knikken); NIET geverifieerd in de keten |
| *Rekdefinitie hardingscurve* (`plastic_strain_definition`) | auto | alleen met een Mecway-hardingscurve (zie Niet-lineair statisch) |
| *Max. Newton-iteraties*, *Convergentie RESI_GLOB_RELA*, *NEWTON REAC_ITER* | 20, 1e-6, 1 | bij `BRIDGE_ONVOLLEDIG` (niet geconvergeerd): eerst `TC_CUT` en E/SY boven 1200 °C controleren, dan `convergence_resi_rela` 1e-5 |
| *Elementformulering hex8* (`elem_hex8`, pagina Elementen) | 3D | **LINE_QUAD bij plasticiteit**: lineaire hex8 'lockt' bij plastisch vloeien (§9.5, WARNING); de temperatuur gaat dan met `PROJ_CHAMP` naar het kwadratische mesh. Rekent ~5× langer |
| *Time step* (Mecway) | - | de mechanische stappen zijn de thermische (§4.1); knipt Code-Aster een stap (`DECOUPE`), dan worden alleen de thermische tijden bewaard |
| *Tijdslimiet run_aster* (`time_limit`) | 1800 s | de keten rekent veel langer dan alleen thermisch (WE-10: hex8 ~10 min, LINE_QUAD ~1 uur); verhogen, anders stopt Code-Aster halverwege |

### 9.4 Hoe de bridge vertaalt

- Na de thermische solve en de flux heet het resultaat `res_ther`; daarna een tweede
  model (`PHENOMENE='MECANIQUE'`, `3D`) op hetzelfde mesh, met de randvoorwaarden zoals
  bij *Niet-lineair statisch*.
- `AFFE_MATERIAU` `AFFE_VARC=_F(NOM_VARC='TEMP', EVOL=res_ther, NOM_CHAM='TEMP',
  VALE_REF=<referentie>)` (U4.43.03; syntaxbron testcase hsnv100e). De berekening staat
  in °C (zie [Thermisch.md](Thermisch.md)), dus ook `VALE_REF` en de functies van TEMP.
- Materiaal: `ELAS` (constant) of `ELAS_FO` met `DEFI_FONCTION` van TEMP voor E, ν, α
  (`TEMP_DEF_ALPHA` = `T_ALPHA`), `ECRO_LINE` / `ECRO_LINE_FO` (`SY`, `D_SIGM_EPSI` = E·H/
  (E + H) per tabelpunt) of `TRACTION` (Mecway-hardingscurve, constant in T); relatie
  `VMIS_ISOT_LINE`, `VMIS_CINE_LINE` of `VMIS_ISOT_TRAC`.
- `STAT_NON_LINE` op de thermische tijden (`DEFI_LIST_INST` met `ECHEC DECOUPE`,
  `ARCHIVAGE` op de thermische tijden, zodat temperatuur en spanning per stap bij
  elkaar horen); daarna `CALC_CHAMP` (`SIGM_NOEU`, `SIEQ_NOEU`, `EPSP_NOEU`,
  `VARI_NOEU`, `REAC_NODA`) en de samenvatting (`BRIDGE_THERMOMECA` in de `.mess`).
- `#ASTER`-code en `#ASTER-EXCIT` gelden voor het thermische deel; `#ASTER-POST` staat
  na de mechanische nabewerking (`res` is daar het mechanische resultaat, `res_ther`
  het thermische).

### 9.5 Interpretatie

- **Restspanning** = de spanning op het laatste tijdstip, als het werkstuk daar
  (nagenoeg) op de begintemperatuur is: kijk in de samenvatting naar het
  temperatuurbereik. Een resterend temperatuurverschil ΔT geeft nog een thermische
  spanning van de orde E·α·ΔT (2,5 MPa per K bij staal).
- **Patroon** (Radaj 1992, Masubuchi 1980): langs de rups trek in de lasrichting van de
  orde van de vloeigrens, daarnaast druk die de trek in evenwicht houdt; dwars op de las
  kleinere spanningen. Bij een vrij werkstuk is de netto kracht en het netto moment over
  elke doorsnede nul (controle in WE-10: 0,02% van SY·A en 1% van SY·A·t).
- **Vervorming**: langs- en dwarskrimp en hoekverdraaiing (de randen draaien naar de
  laskant bij een rups op een plaat). Een eenvoudige bovengrens voor de dwarskrimp van
  een volledig doorgelaste plaat: α·q/(v·ρ·c·t) (de warmte per lengte als uniforme
  opwarming van een strook die volledig krimpt).
- **Hex8 en plasticiteit**: lineaire, volledig geïntegreerde hex8 'locken' bij
  volumebehoudend plastisch vloeien en geven in de las te hoge, vaak triaxiale
  spanningen (WE-10 met `3D`: σxx in de las 1,3–2,6 × SY van boven naar onder, σzz 190 MPa midden in een plaat
  van 5 mm). Gebruik `LINE_QUAD` of hex20/tet10 in Mecway voor de spanningen in en naast
  de las; het evenwicht en de vervorming zijn met hex8 wel bruikbaar.
- **Smeltbad**: boven `T_CUT` bevriest de thermische rek; E en SY staan daar op de
  laatste tabelwaarde. De spanningen in het smeltbad zelf hebben geen fysische
  betekenis. Zonder `geboorte=` is de rups er vanaf het begin; met `geboorte=` (§11)
  pas als de bron er langs komt.

WE-10 (halve plaat 40 × 15 × 5 mm, 1000 W, 5 mm/s, rand y = 15 mm op T0, afkoelen tot
60 s; temperatuur aan het eind 293,2..301,3 K), gemeten met hex8 `3D` (zie hierboven) en
LINE_QUAD:

| Grootheid (doorsnede x = 20 mm, t = 60 s) | hex8 `3D` (WE-10) | LINE_QUAD (WE-10b) |
|---|---|---|
| σxx in de las (y = 0), boven / midden / onder | 466 / 641 / 923 MPa | 400 / 446 / 350 MPa |
| σyy in de las, boven / midden | 163 / 418 MPa | 5 / 135 MPa |
| σzz in de las, midden (vrij oppervlak op 2,5 mm) | 194 MPa | −5 MPa |
| von Mises in de las, boven / (SY + H·p) | 1,002 | 1,014 |
| σxx op de rand y = 15 mm, boven / midden / onder | −372 / −364 / −329 MPa | −357 / −367 / −326 MPa |
| breedte van de trekzone (midden dikte) | ~5,5 mm | ~5,5 mm |
| netto kracht N/(SY·A); moment M/(SY·A·t) | −0,0002; −0,010 | 0,0005; −0,0004 |
| hoekverdraaiing (dz(y = 15) − dz(0))/15 mm, onderkant | 8,9 mrad (0,51°) | 12,4 mrad (0,71°) |
| doorzakking lasas t.o.v. de steunpunten (x = 20 mm) | 0,054 mm | 0,076 mm |
| langskrimp over 40 mm, lasas / rand | 0,013 / 0,041 mm | 0,011 / 0,046 mm |
| dwarskrimp hele plaat, midden dikte / boven (bovengrens α·q/(v·ρ·c·t) = 0,103 mm) | 0,077 / 0,126 mm | 0,085 / 0,151 mm |
| grootste cumulatieve plastische rek | 0,069 | 0,071 |
| Newton-iteraties per stap; rekentijd (belaste pc) | 3–4; 10 min | 10; 53 min |

Vergelijking met de literatuur (kwalitatief; Radaj 1992, Masubuchi 1980): met LINE_QUAD
is de langsspanning in de las 400–450 MPa, gelijk aan de actuele vloeigrens SY + H·p
(355 MPa + 1 GPa × 0,05) en dus "van de orde van de vloeigrens"; de dwarsspanning is
klein aan het oppervlak; naast de las druk die de trek in evenwicht houdt. De drukzone is
hier groot (tot ~SY aan de rand) omdat de plaat smal is (15 mm halve breedte): in een
brede plaat is de druk lager en verder uitgesmeerd. De randen draaien naar de laskant
(hoekverdraaiing bij een rups met gedeeltelijke inbranding), de plaat krimpt in de
lasrichting en dwars erop; de dwarskrimp op halve dikte ligt onder de bovengrens van
een volledig krimpende strook. Hex8 `3D` geeft hetzelfde patroon en evenwicht, maar door
locking een te hoge, triaxiale spanning in de las en een stijvere plaat (hoekverdraaiing
28% kleiner).

### 9.6 Verificatie

[Verificatie.md](Verificatie.md) §8, WE-07..WE-10: vrij uitzetten (rek α·ΔT, spanning
0), eenassig verhinderd met bilineaire versteviging (σ = −E·α·ΔT, vloeien, restspanning
E·p na terugkoelen) en met E(T), SY(T), α(T) (`#ASTER-MATERIAAL`, ook omgekeerd vloeien
tijdens het afkoelen: restspanning = SY(T0)): alle 4·10⁻⁸ of beter t.o.v. de
handberekening (tolerantie 0,1% en 1%). Lasrups WE-10: evenwicht en het kwalitatieve
patroon.

### 9.7 Wat niet kan

- Alleen **volume-elementen** (geen schalen, balken, veren); contact en koppelingen
  (RBE2/RBE3) rekent de keten niet.
- Alleen een **transiente** thermische analyse (T31); stationair (T30) met een Thermal
  stress: gebruik Mecway's *Transfer temperatures from solution* en een statische
  analyse.
- De mechanische stappen zijn de thermische; een grotere stap voor het afkoelen kan
  niet (één *Time step* in Mecway).
- Zonder `geboorte=` is de rups vanaf t = 0 aanwezig en draagt hij mee, ook als hij
  nog niet gelast is (met `T_CUT` en lage E/SY boven de smelttemperatuur is dat
  beperkt); met `geboorte=` niet (§11).
- **Metallurgie** (fasen en transformatierek) alleen met `#ASTER-METALLURGIE`
  `mechanica=ja` (§10.4); ook dan geen ontlaten van de versteviging: plastische rek
  uit de verhitting blijft bestaan na het smelten (geen 'annealing').
- Temperatuurafhankelijke **hardingscurve** (`TRACTION` per temperatuur) niet; alleen
  bilineair (`ECRO_LINE_FO`).
- Kruip en viscoplasticiteit niet.

### 9.8 Meldingen → oorzaak → oplossing

| Melding (log) | Oorzaak | Oplossing |
|---|---|---|
| `INFO: Mechanische belasting '...' telt niet mee in de thermische analyse (alleen met een Thermal stress ...)` | T31 met opleggingen maar zonder Thermal stress | Thermal stress toevoegen (§9.1) als je restspanning wilt |
| `ERROR: Thermomechanisch zonder mechanische randvoorwaarden` | geen Fixed support / Displacement | statisch bepaald vastleggen (§9.1 stap 3) |
| `<SolverError> <MECANONLINE9_4>` in de `.mess`, `BRIDGE_ONVOLLEDIG 0.0` | matrix singulier: het werkstuk kan nog vrij bewegen (een Displacement is één richting) | per richting een eigen Displacement; zes starre bewegingen vastleggen |
| `ERROR: Thermomechanisch ...: alleen volume-elementen` | schalen, balken of veren in het model | volume-elementen |
| `ERROR: Thermomechanisch: elset(s) ... hebben geen thermisch materiaal` | een onderdeel zonder warmtegeleiding | thermisch materiaal toewijzen |
| `WARNING: ... referentietemperatuur van Thermal stress ... is niet de begintemperatuur` | Reference temperature ≠ Initial condition | gelijk maken |
| `WARNING: ... heeft geen thermische uitzettingscoefficient` | α = 0 | *Thermal expansion coefficient* of `ALPHA` |
| `WARNING: Plastische hex8-elementen ... blijven lineair` | `elem_hex8` = 3D met plasticiteit | `LINE_QUAD` of kwadratische elementen (§9.5) |
| `ERROR: #ASTER-MATERIAAL ...: onbekend of onvolledig` / `geen geldige waarde` | tikfout, geen getal of lijst | sleutels van §9.2 |
| `ERROR: #ASTER-MATERIAAL ...: lijsten ... vragen de temperaturen` / `... heeft n waarden, T heeft er m` | lijst zonder `T`/`TC`, of ongelijke lengte | `TC=(...)` met evenveel waarden |
| `ERROR: #ASTER-MATERIAAL '...': geen (mechanisch) materiaal met die naam` | naam wijkt af van het Mecway-materiaal | exacte Mecway-naam (hoofdletters, spaties) |
| `ERROR: ...: ET >= E bij ... K` | tangentmodulus te groot bij een hoge temperatuur (E klein) | `H` gebruiken, of ET kleiner |
| `ERROR: ...: H/ET zonder SY` | versteviging zonder vloeigrens | `SY` geven |
| `WARNING: #ASTER-MATERIAAL werkt alleen ...; hier genegeerd` | de regel staat in een mechanisch model of een thermisch model zonder Thermal stress | Thermal stress toevoegen (T31), of de regel weghalen |
| `BRIDGE_ONVOLLEDIG <t>` / `MECANONLINE` in de `.mess` | de mechanische stap convergeert niet, ook na knippen | `TC_CUT` zetten, E en SY boven 1200 °C niet extreem klein, `convergence_resi_rela` 1e-5, kleinere *Time step* |
| `WARNING: Thermomechanisch: de tijdstappen ... lopen niet gelijk` | (zou niet moeten voorkomen) | melden; de temperatuur in Mecway kan bij een andere stap horen |

## 10. Metallurgie: fasen, hardheid en de invloed op de restspanning

Bij het lassen verandert de structuur van staal: boven Ac1 begint de omzetting naar
**austeniet**, boven Ac3 is het staal volledig austenitisch; bij het afkoelen ontstaan
uit austeniet weer **ferriet**, **perliet**, **bainiet** of (snel afgekoeld, onder Ms)
**martensiet**. Welke fase ontstaat, hangt af van de afkoelsnelheid (het TRC-diagram,
*transformation en refroidissement continu*). Code-Aster rekent dat na de thermische
solve met `CALC_META` (model van Waeckel), per elementknoop, uit het temperatuurverloop.
De bridge zet de fasefracties en de hardheid per tijdstap in Mecway; met `mechanica=ja`
rekent de keten thermisch → mechanisch (§9) met een **metallurgische wet**: de
volumeverandering bij de omzetting (transformatierek) en een vloeigrens per fase.

Mecway kent geen metallurgie: de invoer is een regel `#ASTER-METALLURGIE` per
Mecway-materiaal, met een **standaard-dataset** (TRC-diagram en omzettingsgegevens uit
een Code-Aster-testcase, §10.3) of een eigen TRC-diagram in `#ASTER`-code.

### 10.1 Werkwijze in Mecway, stap voor stap

Voorbeeld: `TestFiles/Verificatie/modellen/MT-06.liml` (de lasrups van WE-10, alleen
thermisch) en `MT-07.liml` (dezelfde rups met de metallurgische wet in de keten).

1. **Thermisch model** zoals §1: *Thermal transient* (T31), begintemperatuur, lasbron
   (`#ASTER-LASBRON` of een formule) en de thermische randen. Laat de analyse lang
   genoeg doorlopen tot onder ~100 °C: de martensiet ontstaat pas onder Ms (16MND5: 415 °C).
2. **Metallurgie**: in *Custom model definition* (naast de `ASTER-LASBRON`-regels), met
   de exacte Mecway-materiaalnaam vóór de dubbele punt:

   ```
   ** ASTER-METALLURGIE Staal: staal=16MND5, begin=ferriet, TAUX_1=0.001, TAUX_3=0.001
   ```

   Bij lassen altijd een kleine `TAUX_1`/`TAUX_3` (§10.5).
3. **Restspanning met fasen** (optie): een *Thermal stress* zoals §9.1, en in dezelfde
   regel `mechanica=ja` met de uitzetting van austeniet en het rekverschil (§10.4):

   ```
   ** ASTER-METALLURGIE Staal: staal=16MND5, begin=ferriet, TAUX_1=0.001,
   ** ASTER-METALLURGIE     TAUX_3=0.001, mechanica=ja, ALPHA_A=2.35e-5, DEPS=1.0e-2
   ```

4. Hoofdvenster: *Actieve analyse* `auto` (of *Thermisch*), *Starten*.

In Mecway komen per tijdstap de fasefracties `ferrite`, `pearlite`, `bainite`,
`martensite`, `austenite` (0..1; som 1) en met hardheidsgegevens `hardness` (HV). De
groep *metallurgy* bij *Resultaatvelden naar Mecway* gaat met `#ASTER-METALLURGIE`
altijd mee. In de log en het statusvak staat de samenvatting (regel `Metallurgie, t =
...`): het bereik van elke fase op het laatste tijdstip, de grootste austenietfractie
tijdens de run (piektemperatuur), het aantal knopen dat (deels) austeniet werd (de
**warmte-beïnvloede zone**, WBZ) en het hardheidsbereik.

### 10.2 Sleutels van `#ASTER-METALLURGIE`

Vorm zoals `#ASTER-MATERIAAL` (§9.2): `<Mecway-materiaal>: sleutel=waarde, ...`; de
volgende regels zonder naam horen erbij. Ook `#ASTER-METALLURGY`. Temperaturen van
`META_ACIER` in **°C** (zoals Code-Aster), de rest in SI.

| Sleutel (synoniemen) | Eenheid | Standaard | Betekenis | Wanneer aanpassen |
|---|---|---|---|---|
| `staal` (`steel`, `dataset`) | - | (of `trc`) | standaard-dataset: `16MND5` of `HSNV101A` (§10.3) | een ander staal: `trc` |
| `trc` | naam | - | een `DEFI_TRC` uit `#ASTER`-code (voorbeeld 25 in [ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md)); dan zijn `AR3`, `ALPHA`, `MS0`, `AC1`, `AC3`, `TAUX_1`, `TAUX_3` verplicht | eigen staal met een gemeten TRC-diagram |
| `AR3`, `MS0`, `AC1`, `AC3` | °C | dataset | begin ferriet bij afkoelen; begin martensiet (Ms); begin en einde austeniet bij opwarmen | gegevens van het eigen staal |
| `ALPHA` | 1/K | dataset | Koistinen-Marburger: Z_M = 1 − exp(ALPHA·(Ms − T)), **negatief** | literatuurwaarde β ≈ 0,011: `ALPHA=-0.011` |
| `TAUX_1`, `TAUX_3` | s | dataset (0,34) | tijdconstante van de austenitisering bij Ac1 en Ac3 | **bij lassen 0,001** (§10.5) |
| `LAMBDA0`, `QSR_K`, `D10`, `WSR_K` | - | geen | korrelgroei (`META_ACIER`, NIET geverifieerd) | alleen met gegevens |
| `HV` (`hardheid`) | HV | dataset (16MND5: 184, 184, 309, 450, 100) | hardheid van ferriet, perliet, bainiet, martensiet, austeniet (`DURT_META`); de bridge geeft de lineaire mengregel Σ Z·HV | andere waarden van het staal |
| `begin` (`initial`) | fase of 5 fracties | `ferriet` | structuur op t = 0: `ferriet`, `perliet`, `bainiet`, `martensiet`, `austeniet` of `(Zf, Zp, Zb, Zm, Za)` met som 1 | basismateriaal bainitisch (16MND5 na veredelen): `bainiet`; een afschriksimulatie vanuit austeniet: `austeniet` |
| `korrel` (`grain`) | - | dataset (16MND5: 11) | austenietkorrelgrootte op t = 0 (bij `GRAIN_AUST`) | zelden |
| `mechanica` (`mechanics`) | ja/nee | nee | metallurgische wet in de keten thermisch → mechanisch (§10.4) | restspanning met transformatierek |
| `ALPHA_F`, `ALPHA_A`, `DEPS`, `REF`, `SY…`, `ET…`/`H…`, `T`/`TC` | | | mechanische gegevens per fase (§10.4) | met `mechanica=ja` |

Een onbekende sleutel, een ontbrekende verplichte waarde of een waarde die geen getal
is, geeft een ERROR en de run stopt (§10.9).

### 10.3 Standaard-datasets

| `staal=` | Bron | Inhoud | Gebruik |
|---|---|---|---|
| `16MND5` | Code-Aster-testcase **mtlp103a** (V4.61.103, "trempe d'un barreau en 16MND5"; 16MND5 = A508 cl. 3, drukvatstaal) | TRC-diagram met 29 afkoelgeschiedenissen (0,05 .. 400 °C/s; ferriet, bainiet), `GRAIN_AUST DREF=11`, `TEMP_MS` (SEUIL 0,38, AKM −30,791, BKM 11,698, TPLM −1), AR3 830, MS0 415, ALPHA −0,0249, AC1 724, AC3 846, TAUX 0,34 s, hardheid 184/184/309/450/100 HV; geen mechanische gegevens | lassen en afschrikken van laaggelegeerd staal; zonder eigen gegevens het beste uitgangspunt |
| `HSNV101A` | Code-Aster-testcase **hsnv101a** (fictief staal van de testcase) | TRC met 2 geschiedenissen (bainiet tussen 600 en 345 °C), MS0 200, ALPHA −0,03, en de mechanische gegevens van de testcase (α_f 15·10⁻⁶, α_a 23,5·10⁻⁶, DEPS 2,52·10⁻³ bij 900 °C (`REF=warm`), vloeigrens en helling per fase als functie van T) | alleen verificatie (MT-01) |

De gegevens staan in `Scripts/bridge_metallurgy.py` (`DATASETS`), letterlijk uit de
testcase. Een dataset hoort bij één staalsoort: voor een ander staal (S355, ...) is een
eigen TRC-diagram nodig (`trc=`, voorbeeld 25 in
[ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md)); het 16MND5-diagram geeft dan alleen een
indruk.

### 10.4 Restspanning met fasen (`mechanica=ja`)

Met een *Thermal stress* (§9) en `mechanica=ja` rekent de keten met de
metallurgische wet `META_P_IL` (isotrope lineaire versteviging per fase, testcase
hsnv101a). Twee effecten op de restspanning:

- **Transformatierek**: de koude fasen (ferriet, perliet, bainiet, martensiet) hebben
  een groter volume dan austeniet. Code-Aster (`ELAS_META_FO`) rekent met één rek voor
  alle koude fasen en één voor austeniet; met `REF=koud` (standaard bij een koud
  `begin`, referentie = de *Reference temperature* van de Thermal stress):

  ε_th = (1 − Z_a)·α_f·(T − T_ref) + Z_a·(α_a·(T − T_ref) − DEPS)

  en met `REF=warm` (standaard bij `begin=austeniet`):
  ε_th = Z_a·α_a·(T − T_ref) + (1 − Z_a)·(α_f·(T − T_ref) + DEPS). Bij het opwarmen
  krimpt het staal dus tussen Ac1 en Ac3 met DEPS; bij het afkoelen zet het onder Ms
  (martensiet) of in het bainietgebied weer uit. Beide formules zijn met de hand
  nagerekend (MT-04, MT-05: ≤ 6·10⁻⁶; `warm` via hsnv101a, MT-01).
- **Vloeigrens per fase** met een lineaire mengregel; harde martensiet vloeit later.

| Sleutel | Eenheid | Standaard | Betekenis | Wanneer aanpassen |
|---|---|---|---|---|
| `ALPHA_A` | 1/K | dataset; anders **verplicht** | gemiddelde (secans) uitzetting van austeniet vanaf T_ref | altijd (literatuur: ~2,2–2,4·10⁻⁵) |
| `DEPS` | - | dataset; anders **verplicht** | rek koude fasen − austeniet bij T_ref (`EPSF_EPSC_TREF`) | altijd; ~1·10⁻² bij 20 °C (uit hsnv101a: 2,52·10⁻³ bij 900 °C omgerekend naar 20 °C) |
| `ALPHA_F` | 1/K | Mecway *Thermal expansion* of `ALPHA` van `#ASTER-MATERIAAL` | uitzetting van de koude fasen | zelden |
| `REF` | `koud`/`warm` | volgt `begin` | referentiefase bij T_ref (`PHASE_REFE`) | zelden: de referentie is de fase op t = 0 |
| `SY_F`, `SY_P`, `SY_B`, `SY_M`, `SY_A` (of `SY` voor alle) | Pa | Mecway *yield strength* / `SY` van `#ASTER-MATERIAAL` | vloeigrens per fase | martensiet en bainiet hoger, austeniet lager |
| `H_F` .. `H_A` of `ET_F` .. `ET_A` (of `H`/`ET`) | Pa | Mecway / `#ASTER-MATERIAAL` | versteviging per fase (plastische modulus H of helling ET) | als bekend |
| `T` / `TC` | K / °C | - | temperaturen voor lijsten (zoals §9.2); één lijst voor alle sleutels van de regel | temperatuurafhankelijke waarden |

E en ν komen van het Mecway-materiaal of `#ASTER-MATERIAAL`; `TC_CUT` uit
`#ASTER-MATERIAAL` geldt ook voor α_a en α_f. De equivalente plastische rek
(`equivalentplasticstrain`) geeft de bridge bij deze wet niet (de interne variabelen
zijn verstevigingen per fase, V7 is een spanning; gezien in hsnv101a en MT-07); de
plastische rektensor (`plasticstrain*`) wel.

### 10.5 Tijdstap en TAUX: gemeten gedrag van `CALC_META`

| Wat | Gemeten (Code-Aster 17.4) | Gevolg |
|---|---|---|
| Austenitiseren, langzaam (10 °C/s, Δt 0,1 s) | Z_a volgt dZ/dt = (Z_eq − Z)/τ exact (Z_eq lineair tussen Ac1 en Ac3; MT-03: ≤ 2·10⁻⁸ tussen Ac1 en Ac3, 0,22% vlak boven Ac3) | - |
| Austenitiseren, snel (1000 °C/s) | met ΔT = 4 °C per tijdstap exact; met 40 °C per stap ~8× zo traag (bij 1020 °C 9% i.p.v. 51% austeniet); bij lassen (WE-10, Δt 0,3 s: 240 tot 1800 °C per stap) werd de lasas met τ = 0,34 s maar 6% austeniet | **bij lassen `TAUX_1=0.001, TAUX_3=0.001`**: dan is het staal boven Ac3 vrijwel direct austeniet (evenwicht), ook met grote stappen (MT-06). De bridge geeft een WARNING als knopen ruim boven Ac3 kwamen maar < 90% austeniet werden |
| Martensiet (Koistinen-Marburger) | exact, onafhankelijk van de tijdstap (MT-02, MT-08) | - |
| Restaustenite | Code-Aster stopt de martensietvorming bij ~0,4–0,7% austeniet (16MND5: 0,69%; ALPHA −0,05: 0,41%; met ALPHA −0,011 en Ms 300 °C bij 20 °C nog niet bereikt: 4,6%, = KM). Oorzaak NIET gevonden | martensiet ≤ 99,3% (16MND5) |
| TRC bij snelle afkoeling | 16MND5 bij 200 °C/s: nog 3% bainiet, hoewel de snelste geschiedenis met omzetting −80 °C/s is; bij 1000 °C/s alleen martensiet | interpolatie tussen de geschiedenissen is van Code-Aster; NIET verder uitgezocht |
| Gedeeltelijk austeniet (piek tussen Ac1 en Ac3) | het austeniet zet bij afkoelen om naar bainiet/martensiet; het oorspronkelijke ferriet blijft (MT-06: piek 796 °C → 44% ferriet, 20% bainiet, 36% martensiet) | interkritische WBZ |

Tijdstap voor het afkoelen: de fasen hangen af van de afkoelsnelheid rond 800–500 °C
(t8/5); die volgt uit het thermische resultaat. De stap uit §4.1 (verspringing van de
bron) is meestal klein genoeg.

### 10.6 Hoe de bridge vertaalt

- `META_ACIER=_F(TRC=trc_<dataset>, AR3, ALPHA, MS0, AC1, AC3, TAUX_1, TAUX_3)` en
  `DURT_META` in de **thermische** `DEFI_MATERIAU` (zoals hsnv101a: THER + META_ACIER
  in één materiaal); het TRC-diagram als `DEFI_TRC` vóór de materialen. Met een eigen
  `trc=` staat de `DEFI_TRC` in `#ASTER`-code (na de materialen in de `.comm`): dan een
  eigen `DEFI_MATERIAU` en `CHAM_MATER` voor `CALC_META` (alarm `RESULT1_39` is dan
  bedoeld).
- Na de thermische solve: begintoestand `CREA_CHAMP` `CART_VAR2_R` (V1..V5 = de fasen,
  V6 = som koude fasen, V7 = korrelgrootte), `CALC_META(reuse=res, COMPORTEMENT=_F(
  RELATION='ACIER'), OPTION=('META_ELNO', 'META_NOEU'))` en met hardheid `OPTION=
  ('DURT_ELNO', 'DURT_NOEU')`; alleen op de elsets van het materiaal.
- In Mecway: `META_NOEU` V1..V5 → `ferrite` .. `austenite`, `DURT_NOEU` HV → `hardness`
  (knoopgemiddelde, zoals de andere knoopvelden).
- Keten (`mechanica=ja`): `AFFE_VARC=(_F(NOM_VARC='TEMP', ...), _F(NOM_VARC='M_ACIER',
  EVOL=res_ther, NOM_CHAM='META_ELNO'))`, `DEFI_MATERIAU(ELAS_META_FO=_F(E, NU, F_ALPHA,
  C_ALPHA, PHASE_REFE, EPSF_EPSC_TREF, TEMP_DEF_ALPHA, F1_SY..C_SY, SY_MELANGE),
  META_ECRO_LINE=_F(F1_D_SIGM_EPSI..C_D_SIGM_EPSI))` en `COMPORTEMENT=_F(RELATION=
  'META_P_IL', RELATION_KIT=('ACIER',))`; alles verder als §9.4.

### 10.7 Interpretatie

- **Warmte-beïnvloede zone**: knopen die (deels) austeniet werden (samenvatting: aantal
  knopen > 1% austeniet). Piek boven Ac3: volledig omgezet (grofkorrelige WBZ, smeltzone);
  tussen Ac1 en Ac3: interkritisch (mengsel van oud ferriet en nieuwe fasen); onder Ac1:
  onveranderd. Ontlaten (tempering) van martensiet bij een tweede laag kent de bridge
  niet (`ACIER_REVENU` niet vertaald).
- **Martensiet en hardheid**: veel martensiet en een hoge hardheid in de las en de WBZ
  wijzen op een te snelle afkoeling (koudscheurgevoeligheid; voorwarmen verlaagt de
  afkoelsnelheid). De hardheid is een lineaire mengregel van de fasehardheden.
- **Restspanning**: de transformatierek werkt de krimp bij het afkoelen tegen. MT-07
  (16MND5, Ms 415 °C) t.o.v. WE-10 zonder metallurgie: in de martensiet (lasas, boven en
  midden) daalt de langsspanning σxx van 466 / 641 MPa naar 176 / 4 MPa; de trekpiek
  schuift naar de rand van de omgezette zone (y = 3 mm: 407 / 349 MPa) en naar de
  onderkant van de las, die niet omzette (794 MPa; WE-10 923 MPa). Het evenwicht blijft
  (netto kracht 0,0009 SY·A, moment −0,004 SY·A·t), de hoekverdraaiing daalt van 8,9
  naar 5,2 mrad, de dwarskrimp blijft 0,073 mm (WE-10 0,077 mm). Dit is het bekende
  effect van de martensietuitzetting (lastoevoegmateriaal met een lage Ms wordt daarom
  gebruikt om de restspanning te verlagen); de getallen zijn met lineaire hex8
  (locking, §9.5) en illustratieve fasegegevens alleen kwalitatief. Rekentijd 14 min.
- De fasen zijn knoopwaarden (`META_NOEU`, gemiddeld over de aansluitende elementen); bij
  een grove mesh smeert een smalle WBZ uit.

### 10.8 Wat niet kan

- Alleen **transient thermisch** (T31) en alleen **volume-elementen** (`CALC_META` kent
  geen schalen; een materiaal met metallurgie op een schaal geeft een ERROR).
- Alleen het staalmodel `ACIER` (Waeckel); geen ontlaten (`ACIER_REVENU`), geen
  zirkonium (`ZIRC`).
- Mechanisch alleen `META_P_IL` (isotrope lineaire versteviging per fase); geen
  kinematische versteviging (`META_P_CL`), viscoplasticiteit (`META_V_*`) of
  **transformatieplasticiteit** (`META_PT`, TRIP); niet met `elem_hex8 = LINE_QUAD`
  (ERROR: de fasen staan op het lineaire mesh; gebruik hex20 in Mecway).
- Hardheid alleen als lineaire mengregel (`DURT_META`).
- Een TRC-diagram voor een ander staal moet de gebruiker zelf schrijven (`trc=`).

### 10.9 Meldingen → oorzaak → oplossing

| Melding (log) | Oorzaak | Oplossing |
|---|---|---|
| `ERROR: #ASTER-METALLURGIE vraagt een transiente thermische analyse` | T30 of mechanisch model | Mecway *Thermal transient* (T31) |
| `WARNING: #ASTER-METALLURGIE werkt alleen in een transiente thermische analyse ...; hier genegeerd` | de regel staat in een mechanisch model | weghalen, of de analyse T31 maken |
| `ERROR: #ASTER-METALLURGIE ...: onbekend of onvolledig '...'` | tikfout, of `sleutel` zonder `=` | sleutels uit §10.2/§10.4 |
| `ERROR: ...: geen standaard-dataset '...'` | onbekende naam bij `staal=` | `16MND5` of `HSNV101A`, of `trc=` |
| `ERROR: ...: geef een standaard-dataset staal=... of een eigen TRC-diagram trc=...` | geen van beide | `staal=16MND5` |
| `ERROR: ...: met trc=... ontbreken: ...` | eigen TRC zonder de `META_ACIER`-waarden | `AR3`, `ALPHA`, `MS0`, `AC1`, `AC3`, `TAUX_1`, `TAUX_3` geven |
| `ERROR: ...: ALPHA = ...: ... ALPHA < 0` | Koistinen-Marburger-constante positief ingevuld | met minteken, bijv. `ALPHA=-0.011` |
| `ERROR: #ASTER-METALLURGIE '...': geen (thermisch) materiaal met die naam` | naam wijkt af van het Mecway-materiaal | exacte naam |
| `ERROR: ...: alleen volume-elementen; de schaal-elsets ...` | materiaal ook op schalen | de schalen een ander materiaal geven |
| `ERROR: ...: mechanica=ja vraagt ALPHA_A, DEPS ...` | dataset zonder mechanische gegevens (16MND5) | `ALPHA_A` en `DEPS` geven (§10.4) |
| `ERROR: ...: mechanica=ja vraagt een vloeigrens ...` | Mecway-materiaal elastisch en geen `SY` | `SY_F` .. `SY_A` of `SY`, of een plastisch materiaal |
| `ERROR: #ASTER-METALLURGIE mechanica=ja werkt niet met elem_hex8 = LINE_QUAD` | LINE_QUAD op de pagina Elementen | hex20 in Mecway, of `elem_hex8 = 3D` |
| `WARNING: #ASTER-METALLURGIE '...': mechanica=ja zonder Thermal stress` | geen *Thermal stress* in het T31-model | Thermal stress toevoegen (§9.1), of `mechanica=ja` weghalen |
| `WARNING: ... mechanische gegevens zonder mechanica=ja; genegeerd` | `ALPHA_A`, `SY_M`, ... zonder `mechanica=ja` | `mechanica=ja` toevoegen of de sleutels weghalen |
| `WARNING: Metallurgie: n knopen kwamen ruim boven Ac3 maar werden niet volledig austeniet` | snelle opwarming met een grote tijdstap en τ = 0,34 s (§10.5) | `TAUX_1=0.001, TAUX_3=0.001` |
| `WARNING: Metallurgie: op het laatste tijdstip is er nog austeniet` | nog niet afgekoeld tot onder Ms | langer doorrekenen |
| `<A> RESULT1_39` in de `.mess` | eigen `trc=` (eigen CHAM_MATER voor `CALC_META`) | bedoeld; geen actie |

### 10.10 Verificatie

[Verificatie.md](Verificatie.md) §8, "Lassen: metallurgie" (MT-01 .. MT-08):
hsnv101a in 3D (fasen gelijk aan de AXIS-testcase tot 1,3·10⁻⁶, de TEST_RESU-waarden
van σ tot 5·10⁻⁷ en van ε tot 5·10⁻⁵ met de metallurgische wet; tolerantie 1%),
Koistinen-Marburger met de dataset en met een eigen TRC ≤ 4·10⁻⁸, austenitiseren
≤ 2·10⁻⁸ tussen Ac1 en Ac3 (0,22% vlak boven Ac3), transformatierek en de spanning in
een ingeklemde staaf ≤ 6·10⁻⁶ t.o.v. de handberekening; de lasrups (MT-06, MT-07)
kwalitatief.
## 11. Toevoegmateriaal dat geboren wordt (`geboorte=`)

Zonder meer is de rups vanaf t = 0 aanwezig: hij neemt warmte op en (in de keten) draagt
hij mee voordat hij gelast is. Met **`geboorte=ja`** (of `geboorte=<<selectie>>`) in een
`#ASTER-LASBRON` worden de elementen van het toevoegmateriaal pas "geboren" als de bron
er langs komt ("element birth", de **quiet element**-methode; Lindgren 2001, Michaleris
2014):

- **voor de geboorte** zijn de elementen *stil*: ρ·c × 10⁻⁴ en λ × 10⁻⁸ (geen
  warmteopslag en geen geleiding), E × 10⁻⁴ (geen stijfheid, dus ook geen spanning), en
  de bron werkt er niet in;
- **bij de geboorte** krijgen ze hun gewone materiaal; mechanisch zijn ze
  **spanningsvrij** in hun (meebewogen) stand op de temperatuur van dat moment: daarna
  telt alleen de rek en de thermische rek vanaf daar (krimp α·ΔT t.o.v. de
  geboortetemperatuur).

Code-Aster 17.4 heeft geen eigen "element birth" (geen sleutelwoord in `STAT_NON_LINE`,
`THER_LINEAIRE` of `AFFE_MATERIAU`; ook geen testcase); de bridge bouwt het met
materiaalfuncties, commandovariabelen en een lus (§11.3).

### 11.1 Werkwijze in Mecway, stap voor stap

Voorbeeld: `TestFiles/Verificatie/modellen/WE-13.liml` (twee lagen op een plaat, met de
keten thermisch → mechanisch).

1. **Mesh**: het basismateriaal en de rups (of de lagen) als volume-elementen die
   **knopen delen** op het grensvlak (*Merge nearby nodes*). De rups mag een eigen
   onderdeel zijn of een elementselectie binnen hetzelfde onderdeel.
2. **Naam**: per las of laag een elementselectie of component met het voorvoegsel
   **`LASNAAD_`**, bijv. `LASNAAD_1` en `LASNAAD_2`.
3. **Lasbron** per las/laag (§1.2), met `geboorte=`:

   ```
   ** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.0015), richting=(1, 0, 0), lengte=0.02
   ** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetrie=1, geboorte=<<LASNAAD_1>>
   ** ASTER-LASBRON Q=500, v=0.005, start=(0.005, 0, 0.003), richting=(1, 0, 0), lengte=0.02, t0=6
   ** ASTER-LASBRON af=0.0015, ar=0.003, b=0.0015, c=0.0015, symmetrie=1, geboorte=<<LASNAAD_2>>
   ```

   Met één las volstaat `geboorte=ja` (alle `LASNAAD_`-selecties/-componenten).
   De baan ligt bovenop de rups (`start` op de bovenkant): de bron zit in de rups en
   loopt door in het basismateriaal.
4. Thermisch: *Thermal transient*, begintemperatuur, randen (§1.1). Mechanisch
   (restspanning): Thermal stress, opleggingen en `#ASTER-MATERIAAL` zoals in §9.1; zet
   bij lassen `TC_CUT`.
5. Hoofdvenster: *Actieve analyse* `auto` (of *Thermisch*), *Starten*. De log toont per
   bron `INFO: #ASTER-LASBRON 1: toevoegmateriaal 180 elementen, geboren van t = 0 tot
   4 s (voorloop 0.003 m).`, en in de keten `INFO: Thermomechanisch: toevoegmateriaal
   ... STAT_NON_LINE per geboortestap.`

### 11.2 Sleutels

| Sleutel (synoniemen) | Eenheid | Standaard | Betekenis | Wanneer aanpassen |
|---|---|---|---|---|
| `geboorte` (`birth`) | `ja` / `nee` / `<<selectie>>` | `nee` | toevoegmateriaal van deze bron: `ja` = de selecties/componenten met `LASNAAD_`; `<<Naam>>` = die elementselectie of component | `<<..>>` bij meer lassen of lagen (elke bron een eigen deel; overlap geeft een ERROR) |
| `voorloop` (`lead`) | m | 2 × `af` | een element wordt geboren als het midden van de bron op `voorloop` van zijn achterste knoop (langs de baan) is | groter: het materiaal ligt verder voor de boog (bij 1 × af gaat ~0,5% van het vermogen verloren in nog niet geboren materiaal, bij 2 × af 10⁻⁷); kleiner niet nodig |

Met `geboorte` is `LASNAAD_` het toevoegmateriaal en niet de brongroep: de bron werkt
dan op **alle volume-elementen bij de baan** (automatisch, binnen 3 × de grootste halve
as; ook het basismateriaal en eerdere lagen, die zo opnieuw smelten), tenzij `groep=`
gegeven is. De factoren van het stille materiaal (10⁻⁴; λ 10⁻⁸) zijn vast.

### 11.3 Hoe de bridge vertaalt

- **Geboortetijd per element**: tb = max(t0, t0 + (s_min − voorloop)/v), met s_min de
  kleinste booglengte (langs de baan) van zijn hoekknopen (voor de start 0, voorbij het
  einde van de baan doorgetrokken); zo ligt elk punt van het element op of na zijn
  geboorte. Het element leeft vanaf de eerste staptijd na tb (een element dat bij de
  start al binnen de voorloop ligt, tb = t0: vanaf t0). Een element waarvan tb na het
  einde van de bron of van de analyse ligt (bijv. verder dan de voorloop voorbij het
  einde van de baan), wordt nooit geboren (WARNING).
- **Thermisch, `THER_LINEAIRE`**: per geboortestap een groep; een veld `NEUT1` (het
  midden van de geboortestap) als commandovariabele (`AFFE_VARC NOM_VARC='NEUT1'`
  `CHAM_GD`, testcase ssnp160a) en voor het toevoegmateriaal `THER_FO` met `LAMBDA` en
  `RHO_CP` als `FORMULE` van `INST` en `NEUT1` (testcase ttnp201a): stil als INST ≤
  NEUT1. Eén solve.
- **Thermisch, `THER_NON_LINE`** (λ(T), c(T) of straling): `BETA`/`RHO_CP` van
  `THER_NL` mogen in Code-Aster 17.4 geen formule of nappe zijn (`MODELISA6_31`,
  `MODELISA6_58`); de bridge maakt een stil `THER_NL`-materiaal (de tabellen × 10⁻⁴ en ×
  10⁻⁸) en rekent `THER_NON_LINE` **per geboortestap** met een nieuw `AFFE_MATERIAU`
  (`reuse`, `ETAT_INIT EVOL_THER`). Met constante tabellen gaven beide routes in een
  prototype dezelfde energie (tot 10⁻⁶); WE-11b controleert de tweede met c(T).
- Het toevoegmateriaal rekent met een **diagonale warmtecapaciteit** (`3D_DIAG`,
  testcase ttnp201a): met de consistente capaciteit volgde een stil knooppunt via de
  massakoppeling de temperatuursnelheid van zijn warme buren (WE-13: +138 K voor de
  geboorte, met een dip onder T0 terwijl die opwarmden).
- **De bron** werkt in een punt van het toevoegmateriaal alleen als dat punt al
  geboren is (dezelfde regel in de `FORMULE`, `_lb_born`); elders gewoon.
- **Meer bronnen** staan in **één** last (`lasbron`, ook met Mecway-bronnen als
  formule of tijdstabel): Code-Aster 17.4 rekent twee lasten `AFFE_CHAR_THER_F` met
  `SOURCE` in één analyse allebei met de functie van de eerste (gevonden bij deze stap,
  §3). De energiecontrole blijft per lasbron.
- **Mechanisch** (keten, §9): een stille kopie van elk materiaal van het
  toevoegmateriaal (E × 10⁻⁴, ook `D_SIGM_EPSI`; een hardingscurve met de rek / 10⁻⁴;
  vloeigrens gelijk, zodat het stille element elastisch blijft) en `STAT_NON_LINE` **per
  geboortestap**: een nieuw `AFFE_MATERIAU` met de geboren elementen op hun gewone
  materiaal, en de volgende stap start uit de toestand van het begin van de
  geboortestap met spanning en interne variabelen van de nieuwe elementen op nul
  (`ETAT_INIT` `DEPL`/`SIGM`/`VARI`, `CREA_CHAMP ASSE`; `NEWTON PREDICTION='ELASTIQUE'`
  in die stap, zoals bij bezwijken). Met `LINE_QUAD` (kwadratisch mechanisch mesh) ook.

### 11.4 Interpretatie

- **Energie**: vóór de geboorte neemt het toevoegmateriaal geen warmte op (WE-11: met
  de echte ρ·c zou er 0,5% van de ingebrachte energie in zitten: alleen de knopen op het
  grensvlak met het basismateriaal zijn warm). Bij de geboorte neemt een element de
  temperatuur van zijn knopen over; die op het grensvlak zijn al warm. Dat brengt een
  beetje energie mee: WE-11 +1,2 … +1,6% van η·Q·t (tolerantie 2%).
- **Spanningsvrij bij de geboorte**: op de temperatuur aan het **begin van de stap**
  waarin het element geboren wordt, in de vervormde stand van dat moment (het stille
  element beweegt mee met zijn buren). Een element wordt geboren voor de boog
  (`voorloop`), dus op de temperatuur van het basismateriaal daar; daarna warmt het op
  en smelt het. Met `TC_CUT` (de thermische rek bevriest boven de smelttemperatuur) en
  een lage E en SY bij hoge temperatuur is de spanning in het smeltbad klein; de
  restspanning ontstaat bij het afkoelen. Zonder `TC_CUT` geeft het opwarmen van net
  geboren materiaal grote drukspanning.
- **In Mecway**: een nog niet geboren element staat op de begintemperatuur en heeft
  (vrijwel) geen spanning; zijn knopen bewegen mee met het basismateriaal (de
  verplaatsing is niet nul). Kijk naar de spanning op het laatste tijdstip of in een
  doorsnede achter de bron.
- **Rekentijd**: de mechanische lus (en `THER_NON_LINE` met c(T)) rekent per
  geboortestap een eigen solve (WE-13: 1 140 hex8, 150 stappen, waarvan 35 met
  geboortes: 5,5 min).
- WE-13 (twee lagen op een plaat, hex8 `3D`): de top van laag 1 smelt (piek 2 690 K),
  koelt in de pauze van 2 s af tot 530 K en wordt door laag 2 opnieuw opgewarmd tot
  1 750 K; laag 2 heeft vóór zijn geboorte geen spanning (von Mises < 5·10⁻⁴ × SY) en
  staat op de begintemperatuur (+0,03 K); na het afkoelen (30 s) is σxx in de rupsen
  160–570 MPa trek (x = 15 mm), ernaast druk (−510 MPa op y = 4 mm, −345 MPa aan de rand
  y = 8 mm), netto langskracht −0,25% van SY·A. De absolute waarden zijn met hex8 `3D`
  te hoog (locking, §9.5); de uiteinden van de lagen voorbij de baan (x > 27 mm) worden
  niet geboren (WARNING, 6 + 4 elementen).

### 11.5 Verificatie

[Verificatie.md](Verificatie.md) §8, WE-11 .. WE-13 (`tests_lassen_geboorte.py`):

| Case | Controle | Resultaat | Tolerantie |
|---|---|---|---|
| WE-11 (rups in twee stukken, `THER_LINEAIRE`) | energie van het levende volume na stuk 1 (stuk 2 ongeboren), tijdens stuk 2, op het einde | +1,19 / +1,49 / +1,59% | 2% |
| WE-11 | warmte in het ongeboren stuk als het echt materiaal was / ingebracht; T bovenop het ongeboren stuk | 0,50%; +0,49 K | 1%; 1 K |
| WE-11b (idem met λ(T), c(T), `THER_NON_LINE` per stap) | idem | +1,12 / +1,40 / +1,54%; 0,50%; +0,62 K | idem |
| WE-12 (staaf, B geboren op T0 + 100 K) | u_x(L/2) vóór de geboorte; \|σ\| in B vóór de geboorte / E·α·ΔT | −0,02%; 1,8·10⁻⁴ | 1%; 10⁻³ |
| WE-12 | σ 1 s na de geboorte (20 K afgekoeld); restspanning E·α·ΔT = 252 MPa in A en B | −0,04%; −0,01% | 1% |
| WE-12b (idem bilineair) | restspanning SY + H·p; p | 0,00%; −0,7% | 1% |
| WE-13 (twee lagen, keten) | smelten, afkoelen tussen de lagen en opnieuw opwarmen; laag 2 vóór de geboorte zonder spanning en op T0; evenwicht; trek in de rups, druk ernaast | zie Verificatie.md | kwalitatief |

### 11.6 Wat niet kan

- De geboorte volgt de **baan van de bron** (booglengte langs een rechte baan of een
  `pad`), niet de afstand tot de boog: toevoegmateriaal dat ver naast de baan ligt,
  wordt geboren als de bron er ter hoogte van is.
- Een element is in één keer geboren (geen gedeeltelijke elementen) en spanningsvrij op
  de temperatuur van het **begin van zijn geboortestap** (resolutie Δt).
- Alleen volume-elementen; elk element hoort bij hoogstens één bron. Geen variant
  "vanaf het begin aanwezig maar zacht" (dat is de gewone keten met `TC_CUT` en een
  lage E/SY boven de smelttemperatuur, §9).
- De plastische rek en versteviging van het stille element worden bij de geboorte op
  nul gezet; voorgeschiedenis van het toevoegmateriaal (draad, smeltbad) telt niet.
- Met c(T) of straling (THER_NON_LINE per stap) en in de keten (STAT_NON_LINE per
  stap) langere rekentijd. `GDEF_LOG` met geboorte en kinematische versteviging: NIET
  geverifieerd.
- De factoren 10⁻⁴ / 10⁻⁸ zijn geen sleutels.
- Mecway's eigen solver kent geen geboorte: een vergelijking met Mecway kan alleen
  zonder `geboorte`.

### 11.7 Meldingen → oorzaak → oplossing

| Melding (log) | Oorzaak | Oplossing |
|---|---|---|
| `ERROR: ... geboorte=ja vraagt een elementselectie of component met voorvoegsel LASNAAD_` | geen `LASNAAD_`-selectie | selectie maken of `geboorte=<<Naam>>` |
| `ERROR: ... geboorte '...' is geen element-selectie of component` | tikfout in de naam, of een knoop-/vlakselectie | exacte Mecway-naam van een elementselectie |
| `ERROR: ... '...' heeft geen geldige waarde (ja, nee of <<Mecway-selectie>>)` | bijv. `geboorte=LASNAAD_1` zonder `<< >>` | `geboorte=<<LASNAAD_1>>` |
| `ERROR: ... n element(en) van het toevoegmateriaal horen ook bij bron k` | twee bronnen met hetzelfde toevoegmateriaal (bijv. twee keer `geboorte=ja`) | per bron een eigen selectie |
| `ERROR: ... het toevoegmateriaal ... heeft n element(en) die geen (gemodelleerde) volume-elementen zijn` | schalen of balken in de selectie | alleen volume-elementen |
| `ERROR: ... geen element van het toevoegmateriaal wordt geboren` | de bron komt niet langs het toevoegmateriaal, of start na het einde van de analyse | baan/`t0` controleren (coördinaten in m) |
| `WARNING: ... n element(en) van het toevoegmateriaal worden nooit geboren` | toevoegmateriaal verder dan de voorloop voorbij het einde van de baan, of de bron of de analyse stopt eerder | bewust (de rups is langer dan de las)? Anders `lengte`, `t1` of *Time period* aanpassen |
| `WARNING: ... voorloop zonder geboorte=...; genegeerd` | `voorloop` zonder `geboorte` | `geboorte=` toevoegen of `voorloop` weghalen |
| `BRIDGE_ONVOLLEDIG` in de `.mess` met geboorte | de mechanische stap na een geboorte convergeert niet | `TC_CUT` zetten, kleinere *Time step*, E/SY boven 1200 °C niet extreem klein (§9.8) |

## 12. Verificatie

[Verificatie.md](Verificatie.md) §8, groep "Lassen" (WE-01 .. WE-06): Rosenthal binnen
1% (tolerantie 5%), Goldak tegen dezelfde bron analytisch gevouwen binnen 1,2%,
energiebalans ≤ 0,06% (tolerantie 2%), Mecway-formule gelijk aan `#ASTER-LASBRON`
(energie gelijk aan Mecway tot 1e-9), temperatuurafhankelijke λ exact (Kirchhoff) en
energie 0,01%, formules in temperatuur/convectie/flux gelijk aan Mecway (7e-12 K). De
keten thermisch → mechanisch (WE-07 .. WE-10): §9.6. Metallurgie (MT-01 .. MT-08):
§10.10. Toevoegmateriaal dat geboren wordt (WE-11 .. WE-13): §11.5.

## 13. Bronnen

- Goldak, J., Chakravarti, A. & Bibby, M. (1984). A new finite element model for welding
  heat sources. *Metallurgical Transactions B*, 15, 299–305.
- Rosenthal, D. (1946). The theory of moving sources of heat and its application to
  metal treatments. *Transactions of the ASME*, 68, 849–866.
- Carslaw, H.S. & Jaeger, J.C. (1959). *Conduction of Heat in Solids* (2nd ed.).
  Oxford: Clarendon Press (Kirchhoff-transformatie; bronnen en de Green-functie van de
  warmtevergelijking).
- EDF R&D (z.j.). *Code_Aster, documentatie versie 17.4*: U4.44.02 (`AFFE_CHAR_THER`),
  U4.43.01 (`DEFI_MATERIAU` `THER_NL`, `ELAS_FO`, `ECRO_LINE_FO`), U4.43.03
  (`AFFE_MATERIAU` `AFFE_VARC`), U4.51.03 (`STAT_NON_LINE`, `RECH_LINEAIRE`),
  U4.54.02 (`THER_NON_LINE`); catalogi `affe_char_ther_f.py`, `formule.py`,
  `calc_vect_elem.py`, `defi_materiau.py`, `affe_materiau.py`, `proj_champ.py`;
  testcases hsnv100e, ssnp160a (`THER_FO` met een functie van `NEUT1`, `AFFE_VARC`
  `CHAM_GD`) en ttnp201a (`THER_FO` met een functie van `INST`, `3D_DIAG`);
  metallurgie: catalogi `calc_meta.py`, `defi_trc.py`,
  `defi_materiau.py` (`META_ACIER`, `DURT_META`, `ELAS_META_FO`, `META_ECRO_LINE`),
  `Behaviours/acier.py`, `meta_p_isot_line.py`; testcases hsnv101a, mtlp100b en
  mtlp103a (V4.61.103). https://www.code-aster.org
- Koistinen, D.P. & Marburger, R.E. (1959). A general equation prescribing the extent
  of the austenite-martensite transformation in pure iron-carbon alloys and plain
  carbon steels. *Acta Metallurgica*, 7(1), 59–60.
- Lindgren, L.-E. (2001). Finite element modeling and simulation of welding. Part 1:
  Increased complexity. *Journal of Thermal Stresses*, 24(2), 141–192 (o.a. het
  activeren van toevoegmateriaal: "quiet" en "inactive" elementen).
- Lindgren, L.-E. (2001). Finite element modeling and simulation of welding. Part 2:
  Improved material modeling. *Journal of Thermal Stresses*, 24(3), 195–231.
- Michaleris, P. (2014). Modeling metal deposition in heat transfer analyses of
  additive manufacturing processes. *Finite Elements in Analysis and Design*, 86,
  51–60 (quiet tegen inactive elementen, energie bij activeren).
- Masubuchi, K. (1980). *Analysis of Welded Structures: Residual Stresses, Distortion,
  and their Consequences*. Oxford: Pergamon Press.
- Waeckel, F. (1994). *Une loi de comportement thermo-métallurgique des aciers pour le
  calcul mécanique des structures* (proefschrift). ENSAM Paris (het staalmodel `ACIER`
  van `CALC_META`; achtergrond, niet geraadpleegd: het gedrag in §10.5 is gemeten).
- Radaj, D. (1992). *Heat Effects of Welding: Temperature Field, Residual Stress,
  Distortion*. Berlin: Springer.
- Timoshenko, S.P. & Goodier, J.N. (1970). *Theory of Elasticity* (3rd ed.). New York:
  McGraw-Hill.
- Mecway (2026). *Mecway-handleiding*, versie 33: §8.6 (temperatuurafhankelijke
  eigenschappen), §9 (formules), §9.28–9.29 (heat flux, internal heat generation).
