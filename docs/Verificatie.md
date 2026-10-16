# Verificatie van de MecwayAsterBridge

*English version: [Verification.md](en/Verification.md)*

Dit rapport toont met reproduceerbare tests dat de keten Mecway-model (`.liml`) →
MecwayAsterBridge → Code-Aster 17.4 → resultaten in Mecway juiste antwoorden geeft.
Elke test vergelijkt een FEM-grootheid met een analytische oplossing of een erkende
benchmark, in de stijl van de NAFEMS-benchmarks (NAFEMS, 1990): klein, gericht en met
een vooraf onderbouwde tolerantie. Daarnaast is de Code-Aster-installatie zelf getoetst
met 19 officiële validatietests (§10).

Inhoud: 1 Werkwijze · 2 Uitvoeren · 3 Samenvatting · 4 Lineair statisch (LS) en foutschatter (FS) ·
5 Niet-lineair statisch (NL) · 6 Dynamica (DY) · 7 Modaal (MO) en knik (BU) ·
8 Thermisch (TH) · 9 Aannames en niet gedekt · 10 Officiële Code-Aster-validatietests ·
11 Bronnen

## 1. Werkwijze

- **Modellen** worden door Python-scripts gegenereerd
  (`TestFiles/Verificatie/tests_*.py`, met `verif_lib.py`) en opgeslagen als gewone
  Mecway-modellen in `TestFiles/Verificatie/modellen/` (te openen in Mecway).
- **Rekenen**: `TestFiles/Verificatie/_run_one.py` doorloopt per model dezelfde
  stappen als een run vanuit Mecway (`bridge_from_liml` → `bridge_mesh` →
  `bridge_to_aster`/`bridge_thermal` → Code-Aster), zonder de Mecway-API. De
  resultaten komen uit hetzelfde resultaatbestand dat Mecway inleest.
- **Door Mecway geschreven modellen**: de generator schrijft de `.liml` zelf, niet
  Mecway. Met `--mecway-opslaan` (§2) opent Mecway elk model eerst en slaat het zelf
  weer op (eigen XML-opmaak en volgorde, eenheden bij elke waarde, standaardwaarden
  zoals `colorrgb`, een lege `<solution>`), zodat de bridge het bestand leest zoals
  een gebruiker het in Mecway bewaart. Uitkomst (7 oktober 2026, bridge 8742df0): alle
  270 testcases konden door Mecway, en alle 1611 controles zijn identiek aan de gewone
  run (zelfde status, zelfde FEM-waarde); de `.comm` is gelijk, op de laatste cijfers
  van 15 cases na (Mecway schrijft getallen met 15 significante cijfers).
- **Instellingen**: de standaardwaarden van `CONFIG_BRIDGE`
  (`Scripts/bridge_utils.py`), tenzij bij een test anders vermeld.
- **Vergelijken**: per controle de FEM-waarde, de referentie, de afwijking en de
  tolerantie. Status OK, NOK, FOUT (geen resultaat, of het gevraagde tijdstip is niet
  bereikt) of BEKEND (afwijking door een gedocumenteerde beperking, met het nummer in
  `KNOWN_BUGS.md`).
- **Mesh-convergentie**: reeksen met afnemende elementgrootte h. Per reeks de fout per
  mesh, de orde p uit opeenvolgende fouten en een Richardson-extrapolatie uit de
  laatste drie meshes (orde en limiet, onafhankelijk van de referentie). Een limiet die
  afwijkt van de referentie wijst op een modelfout van de theorie (bijv. de ingeklemde
  volumebalk tegen de balktheorie), niet op discretisatie.
- **Tolerantiebeleid**: het fijnste mesh krijgt tol_f = modelfout van de analytische
  theorie + afronding van de referentie + ruim de geschatte discretisatiefout. Een
  grover mesh met elementgrootte h krijgt tol_f·(h/h_f)^p (p = verwachte orde, begrensd
  op 50%); een grof mesh toetst zo alleen of de fout past bij convergentie naar de
  referentie. Waar de FEM-oplossing exact is (bijv. Euler-balk met eindlast, homogene
  spanning) is de tolerantie 0,1% of kleiner. Toleranties zijn niet achteraf verruimd;
  elke afwijking van deze regel is bij de test onderbouwd.
- **Referentiewaarden** komen uit de literatuur (§11) of uit een eigen nauwkeurige
  berekening (reeksontwikkeling, Runge-Kutta, hetzelfde discrete schema in 1D), die in
  de testmodule staat.

## 2. Uitvoeren

```bash
cd TestFiles/Verificatie
python run_verificatie.py            # alles (ongeveer een uur)
python run_verificatie.py LS NL-02   # alleen ids die zo beginnen
python run_verificatie.py --report   # alleen het rapport opnieuw maken
```

Nodig: CPython 3 en een werkende Code-Aster-installatie (`exe_aster` in
`Scripts/bridge_utils.py`). Uitvoer: `TestFiles/Verificatie/resultaten/resultaten.md`
(alle controles en de mesh-convergentie), `resultaten.csv`, `resultaten.json` en de
gegenereerde `.comm` per test in `resultaten/comm/` (absolute paden daarin vervangen door
`<WORKDIR>` en `<REPO>`, zodat er geen machinegebonden paden in de repo staan). Werkbestanden staan in
`%TEMP%/mab_verificatie` (instelbaar met de omgevingsvariabele `VERIF_WORK`). Zware cases buiten de standaardregressie (WE-10b, ~1 uur) draaien alleen met `VERIF_ZWAAR=1`.

**Via Mecway** (`python run_verificatie.py --mecway-opslaan [ids]`, of
`VERIF_MECWAY=1`): elk gegenereerd model gaat eerst door Mecway,
`mecway.exe <model>.liml script TestFiles/Tools/mw_save_as.py` (Mecway-handleiding
§16.1: het model openen, het script draaien, afsluiten; zonder venster en zonder
solve, dus ook voor analyses die Mecway zelf niet kan rekenen, zoals XFEM, lassen
en vermoeiing). Het script doet alleen `mw.save_as()`. De bridge rekent
daarna die Mecway-kopie (in `VERIF_WORK/_mecway/`); `run_verificatie` controleert
vooraf dat Mecway knoopnummers, coördinaten en knoopselecties niet veranderd heeft.
Uitvoer in `resultaten/mecway/` (de gewone resultaten blijven ongewijzigd) en
`resultaten/mecway/vergelijking.md` (alleen dat bestand staat in de repo): per controle status en FEM-waarde naast de
gewone run en of de `.comm` (zonder commentaar en paden) gelijk is.
`--mecway-opslaan --vergelijk` maakt alleen die vergelijking opnieuw. Kost ongeveer
2 s Mecway per model bovenop de gewone run. Wat Mecway bij het opslaan verandert:
eenheden bij waarden zonder eenheid (`816.0` → `816 Pa.s/m`), getallen anders
geschreven (`1e+08 Pa` → `100000000 Pa`, 15 significante cijfers), selecties in een
andere volgorde, standaardwaarden erbij (`colorrgb`, `selfcontact`, een lege
`<mechanical type="Isotropic" />` bij een alleen-thermisch materiaal, een
`<hardeningcurve strain="0" stress="0 Pa" />` bij bilineaire plasticiteit) en
sommige attributen weg (`automatictimestepping="false"`, de constante waarden naast
een TempDependent-tabel). Knoop- en elementnummers blijven gelijk. AD-02
rekent na de eerste lus al op modellen die Mecway zelf verfijnd en opgeslagen heeft;
WE-10b (alleen met `VERIF_ZWAAR=1`) zat niet in de vergelijking.

Een test toevoegen: een `Case` in een `tests_<groep>.py` met een functie die een
`Model` bouwt en een lijst `Check`s (zie `verif_lib.py` en de bestaande modules).

## 3. Samenvatting

Stand 16 oktober 2026. De hele tabel komt uit één revisie: de regressie in
`TestFiles/Verificatie/resultaten/resultaten.md`, een volledige run op bridge `de08b40`
(alle stappen, de eindcontrole S11 en de uitbreidingen van 15 oktober; Code-Aster 17.4):
401 testcases, 2212 controles, 2205 OK, 7 BEKEND, 0 NOK/FOUT.

| Groep | Testcases | Controles | OK | Bekend |
|---|---|---|---|---|
| Adaptieve verfijning | 8 | 14 | 14 | 0 |
| Akoestiek | 7 | 78 | 78 | 0 |
| Akoestiek harmonisch | 10 | 103 | 103 | 0 |
| Akoestiek impedantie | 10 | 227 | 227 | 0 |
| Cyclische symmetrie | 6 | 171 | 171 | 0 |
| Breukmechanica | 14 | 63 | 62 | 1 |
| Dynamica | 16 | 47 | 47 | 0 |
| Foutschatter | 10 | 32 | 32 | 0 |
| Harmonische respons | 11 | 40 | 40 | 0 |
| Knik | 21 | 62 | 61 | 1 |
| Lassen | 18 | 117 | 117 | 0 |
| Lineair statisch | 107 | 369 | 367 | 2 |
| Metallurgie | 8 | 56 | 56 | 0 |
| Modaal | 22 | 221 | 221 | 0 |
| Modaal met demping | 7 | 47 | 47 | 0 |
| Modaal (voorspanning) | 7 | 38 | 38 | 0 |
| Niet-lineair statisch | 25 | 97 | 94 | 3 |
| Niet-lineaire knik | 5 | 13 | 13 | 0 |
| Respons op modale basis | 8 | 21 | 21 | 0 |
| Responsspectrum | 9 | 41 | 41 | 0 |
| Thermisch | 24 | 92 | 92 | 0 |
| Thermische spanning | 2 | 7 | 7 | 0 |
| Vermoeiing | 25 | 52 | 52 | 0 |
| Vibro-akoestiek | 8 | 29 | 29 | 0 |
| Vibro-akoestiek harmonisch | 13 | 175 | 175 | 0 |
| **Totaal** | **401** | **2212** | **2205** | **7** |

Geen NOK of FOUT (WE-10b, alleen met `VERIF_ZWAAR=1`, niet meegeteld: 9 van 9 OK). Officiële Code-Aster-tests: 19 van 19 OK (1598 TEST_RESU-controles,
0 NOOK).

**Bekende beperkingen** (status BEKEND):
- KNOWN_BUGS 43: Lagrange-contact (`contact_algo` = STANDARD) op een lijncontact tussen
  hex20-volumes stopt (NL-03a, 3 controles). Gebruik PENALISATION (NL-03b: exact).
- KNOWN_BUGS 83: K_I uit `CALC_G_XFEM` op een gekromd front +5,3 % (BR-10, 1 controle,
  tolerantie 5 %). Gebruik daar K uit `POST_K1_K2_K3` (+1,6 %) of uit G (+1,0 %).

**Fouten in de bridge die deze verificatie vond en die zijn opgelost**:
- Foutschatter: Code-Aster's `ERME` rekent `FORCE_FACE` met het omgekeerde teken (blok onder
  uniforme trek: 15% i.p.v. 0); de bridge keert het om in de last van de schatter (AD,
  [Foutschatter.md](Foutschatter.md) §2.3; FS ongewijzigd, ≤ 3e-4).
- Mecway's *tangent modulus* bij bilineaire plasticiteit werd als helling in totale rek
  gelezen; het is de plastische modulus H. Nu `D_SIGM_EPSI` = E·H/(E+H) (NL-01).
- Contact op kwadratische vlakken haalde de patchtest niet met de standaardintegratie
  (tot 4,6% fout); nu `INTEGRATION='NCOTES'` bij een kwadratisch slave-vlak (NL-03c–f).
- Veren en dempers werkten alleen in globaal X; nu langs de eigen as (LS-06).
- *Node temperature* (`temperature3`) telde in een mechanische analyse niet mee (alleen
  een INFO); nu als temperatuur per knoop in het knoopveld (LS-08).
- Een temperatuur gaf in `DYNA_NON_LINE` geen thermische spanning (het veld vanaf t = 0
  telde als begintoestand, KNOWN_BUGS 94, opgelost); nu een `EVOL_THER` vanaf de referentie
  (DY-70). Een tijdstabel van een *Temperature* werd niet vertaald; nu in L30 en D31
  (NL-70..74, DY-71).
- Verlijmd contact tussen schalen stopte met `FACTOR_11` (de rotatie om de
  plaatnormaal werd meegekoppeld); nu zonder die rotatie (LS-07). Een scheve of
  gekromde master en een kwadratische schaal (quad8/tri6) als master stopten nog met
  `FACTOR_11` en `CHARGES2_31`; nu schrijft de bridge die koppeling zelf (LS-07f–k).
- In expliciete dynamica gaf afronding in `DEFI_LIST_INST` een extra rekenstap.
- Temperatuurafhankelijke ρc: `THER_NON_LINE` interpoleert de enthalpie lineair tussen
  de tabelpunten; de bridge verfijnt de tabel nu (energiebalans van −2,8% naar 0,002%,
  WE-04b).
- Twee lasbronnen (`#ASTER-LASBRON`) werkten als twee keer de eerste: Code-Aster 17.4
  rekent twee lasten `AFFE_CHAR_THER_F` met `SOURCE` in één analyse met de functie van
  de eerste; de lasbronnen staan nu in één last (WE-11), nu ook met de
  Mecway-bronnen als formule of tijdstabel (TH-40 .. TH-42).
- Toevoegmateriaal: met de consistente warmtecapaciteit warmde een nog niet geboren
  knooppunt via de massakoppeling op (+138 K); nu `3D_DIAG` (WE-13).

## 4. Lineair statisch (LS)

Mecway S30 → bridge `lin_static_3d` → `MECA_STATIQUE`. Module
`tests_lineair_statisch.py`, draaien met `python run_verificatie.py LS`. Materiaal
overal staal, E = 210 GPa, ν = 0,3 (G = 80,77 GPa); eenheden SI. De kolom "orde p" in
`resultaten.md` is berekend uit de fout ten opzichte van de referentie; heeft de
referentie een modelfout (LS-02), dan staat hieronder de orde uit de verschillen tussen
opeenvolgende meshes.

### LS-01 Ingeklemde balk, balkelementen

- **Doel**: balkelementen (`POU_D_E`), `fixed` en een puntlast.
- **Model**: L = 1 m, rond Ø 20 mm, 10 line2.
- **Randvoorwaarden en belasting**: ingeklemd op x = 0, eindlast P = 100 N dwars.
- **Referentie**: δ = PL³/3EI, θ = PL²/2EI (Young & Budynas, 2002, tabel 8.1, geval 1a).
- **Resultaat**: δ, θ en de reactie 0,00% af (tolerantie 0,1%).
- **Interpretatie**: Euler-Bernoulli-elementen zijn voor deze last exact; de vertaling
  van doorsnede, materiaal en last klopt.

### LS-02 Ingeklemde balk, volume-elementen

- **Doel**: volume-elementen (hex8 `3D`, hex8 `LINE_QUAD`, hex20), `traction`,
  knoopspanningen (`SIGM_NOEU`) en reacties.
- **Model**: 1 × 0,1 × 0,1 m (as x), doorsnede n × n en lengte 10n kubussen. Reeksen
  hex8 `3D` (standaard; n = 1, 2, 4, 8, 16), hex8 `LINE_QUAD` (n = 1, 2, 4) en hex20
  (n = 1, 2, 4).
- **Randvoorwaarden en belasting**: `fixed` op x = 0; `traction` −1 MPa in z op het
  eindvlak (P = 10 kN).
- **Referentie**: Timoshenko-balk δ = PL³/3EI + PL/(κGA), κ = 5/6:
  1,9048e-3 + 0,0149e-3 = 1,9196e-3 m (afschuiving 0,77%). σ_xx = Mc/I = 48,0 MPa op
  x = 0,2 m, bovenvlak (buiten de verstoring door de inklemming). Reactie ΣRz = P.
  Gemeten: gemiddelde DZ van het eindvlak; `stressxx` in de knoop het dichtst bij
  (0,2; 0,05; 0,1).
- **Resultaat**: hex20 n = 4: δ −0,81% (tol. 1%), σ_xx 0,00%. `LINE_QUAD` geeft op elk
  mesh hetzelfde als hex20 (zelfde HEXA20-mesh). hex8 `3D`: δ −35,7 / −13,1 / −4,3 /
  −1,7 / −0,9% (n = 1…16). De reactie is op elk mesh exact.
- **Interpretatie**:
  - Kwadratisch: de verschillen tussen opeenvolgende meshes (18,8e-6 en 4,7e-6 m)
    geven p = 2,0 en de Richardson-limiet δ∞ = 1,9057e-3 m: +0,05% boven
    Euler-Bernoulli en −0,72% onder Timoshenko. Dat is een modelfout van de
    balktheorie: een volledig vastgehouden eindvlak verhindert welving en
    dwarscontractie en verstijft ongeveer net zoveel als de afschuifterm toevoegt. De
    singuliere randen van de inklemming beperken de orde tot 2. Mecway headless
    (interne solver en CCX, C3D20) geeft op dezelfde meshes δ = 1,904148e-3 (n = 4) en
    1,899446e-3 m (n = 2), gelijk aan de bridge op 7 cijfers. tol_f = 1%.
  - hex8 `3D` (volledig geïntegreerd, zonder incompatibele modes) is met weinig
    elementen over de hoogte veel te stijf (KNOWN_BUGS 1); Mecway (incompatibele hex8)
    geeft op dezelfde meshes −1,5 / −1,3 / −1,0% (n = 1, 2, 4). De reeks convergeert met
    p ≈ 1,9 naar dezelfde limiet (Richardson n = 4/8/16: 1,9067e-3 m). De knoopspanning
    convergeert langzaam en niet monotoon (+0,8 / +1,3 / +0,9% bij n = 4/8/16), zoals
    een geëxtrapoleerde knoopspanning van een lineair element (O(h)). tol_f: 2% (δ),
    3% (σ).

### LS-03 Vierkante plaat, vrij opgelegd, gelijkmatige druk

- **Doel**: schalen (DKT en `COQUE_3D`), `surfacepressure` op schaalvlakken,
  `noderotation` en de von Mises-velden van schalen.
- **Model**: a = 1 m, t = 10 mm (a/t = 100), vlak z = 0, n × n elementen. Reeksen quad4
  → DKT (n = 4, 8, 16, 32) en quad8 → `COQUE_3D` (n = 2, 4, 8, 16).
- **Randvoorwaarden en belasting**: alle randknopen DX = DY = DZ = 0 (drie
  `displacement`s) en "hard" vrij opgelegd: `noderotation` 0 om x op x = 0 en x = a,
  om y op y = 0 en y = a. Druk 10 kPa op het bovenvlak.
- **Referentie**: Navier-reeks (Timoshenko & Woinowsky-Krieger, 1959, §30, tabel 8;
  m, n ≤ 401): w = αqa⁴/D met α = 0,0040624, D = Et³/12(1−ν²) → 2,1124e-3 m;
  M = βqa² met β = 0,047886 → σ = 6M/t² = 28,73 MPa. In het midden is σ_x = σ_y en
  τ_xy = 0, dus von Mises = |σ_x|; vergeleken met `vonmisesu1`/`vonmisesb` (de bridge
  zet van schalen alleen von Mises naar Mecway).
- **Resultaat**: DKT n = 32: w −0,003%, σ +0,06%. `COQUE_3D` n = 16: w +0,05%, σ +0,41%.
- **Interpretatie**: DKT convergeert met p ≈ 2,1–2,3 (w) en 2,0 (σ) naar 2,11241e-3 m en
  28,732 MPa (−0,0005% en +0,002%). `COQUE_3D`: σ met p ≈ 2,0 naar 28,717 MPa (−0,05%),
  w naar 2,11351e-3 m (+0,052%); dat verschil is de afschuifdoorbuiging van de
  Mindlin-formulering, 2π²D/(κGta²) = +0,056%. Mecway (`COQUE_3D`-mesh n = 16):
  2,1146e-3 m (+0,05% t.o.v. de bridge). tol_f: w 0,2%, σ 0,5% (DKT) en 1% (`COQUE_3D`).
  Twee opmerkingen over opleggingen: (1) Mecway's `pinnedsupport` is "gemiddelde
  verplaatsing nul" over de selectie (de bridge vertaalt het als `LIAISON_DDL`); voor
  een rand die per knoop vastligt is `displacement` nodig. (2) Met alleen DZ = 0
  ("zacht" opgelegd) convergeert `COQUE_3D` naar +0,91% (w) en +1,06% (σ): de randlaag
  van een Mindlin-plaat, een effect van orde t/a. DKT (Kirchhoff) merkt het niet. De
  harde oplegging hoort bij de Navier-oplossing.

### LS-04 Dikwandige cilinder onder inwendige druk (Lamé)

- **Doel**: `symmetry` (`LIAISON_OBLIQUE`), `frictionless` (`FACE_IMPO`) en druk op een
  gekromd vlak.
- **Model**: a = 0,1 m, b = 0,2 m, kwartmodel (0–90°), axiale dikte 0,01 m, één element
  in z; hex20, n radiaal × 2n tangentieel (n = 1, 2, 4, 8), middenknopen op de cirkel.
- **Randvoorwaarden en belasting**: `symmetry` op y = 0 en x = 0; `frictionless` op
  z = 0 en z = L (vlakke rek, ε_z = 0); druk 100 MPa op de binnenwand.
- **Referentie** (Lamé; Timoshenko & Goodier, 1970): A = pa²/(b²−a²),
  B = pa²b²/(b²−a²); σ_θ(a) = A + B/a² = 166,67 MPa; σ_zz = 2νA = 20 MPa;
  u_r(a) = (1+ν)/E·[(1−2ν)Aa + B/a] = 9,0794e-5 m. Gemeten in de knoop (a, 0, 0):
  `displx`, `stressyy` (= σ_θ) en `stresszz`.
- **Resultaat** n = 8: u_r −0,001%, σ_θ −0,18%, σ_zz +0,42%.
- **Interpretatie**: u_r convergeert met p ≈ 3,8 naar 9,07937e-5 m (exact), σ_zz met
  p ≈ 1,8 naar 19,98 MPa. σ_θ op de binnenwand (+0,10 / −0,62 / −0,46 / −0,18%) is nog
  pre-asymptotisch: de knoop ligt op het symmetrievlak en σ_θ ∝ 1/r² wordt naar de
  belaste rand geëxtrapoleerd. Verder in de wand is de fout in de hoekknopen ≤ 0,15%,
  in de middenknopen 1–2% (n = 4), het gebruikelijke beeld van hex20-knoopspanningen.
  tol_f: u_r 0,1%, σ_θ 0,5% (p = 1), σ_zz 1%.

### LS-05 NAFEMS LE1, elliptisch membraan

- **Doel**: een erkende benchmark met spanningsconcentratie; schalen als membraan en
  volumes; druk op schaalranden.
- **Model**: binnenellips (x/2)² + y² = 1, buitenellips (x/3,25)² + (y/2,75)² = 1,
  dikte 0,1 m, kwartmodel, punt D = (2, 0). Mesh n × 2n (n = 2, 4, 8, 16), in beide
  richtingen verdicht naar D (stuksgewijs lineair, zodat middenknopen in het midden
  van de ribbe liggen; een gladde verdichting zet ze op het kwartpunt en geeft een
  singulier element in D). Reeksen quad8 → `COQUE_3D` (DZ = 0 op alle knopen) en hex20,
  één element dik (DZ = 0 in één knoop).
- **Randvoorwaarden en belasting**: `symmetry` op y = 0 en x = 0; druk −10 MPa (trek)
  op de buitenrand. Op schaalranden worden dat consistente knoopkrachten; controle
  ΣR_x = −2,75 MN en ΣR_y = −3,25 MN (= p·t·2,75 en p·t·3,25).
- **Referentie**: σ_yy(D) = 92,7 MPa, vlakke spanning (NAFEMS, 1990, test LE1). Schaal:
  `vonmisesm` (in D is σ_xx = τ_xy = 0, dus von Mises = σ_yy); volume: `stressyy`.
- **Resultaat** n = 16: `COQUE_3D` 92,654 MPa (−0,05%), hex20 92,660 MPa (−0,04%).
- **Interpretatie**: beide reeksen convergeren met p ≈ 3,8–4,1 naar 92,66 MPa
  (Richardson); het resterende verschil valt binnen de afronding van de referentie
  (92,65…92,75). tol_f = 0,5%. Mecway (`COQUE_3D`-mesh n = 8): u_x(D) gelijk op 0,06%.
  Code-Aster 17.4 bevat zelf geen LE1-test (wel LE3 = ssls105a, §10).

### LS-06 Ingeklemde balk met een veer aan de tip

- **Doel**: Mecway-veer (line2 met materiaal *Spring*) langs zijn eigen as
  (`DISCRET` met `REPERE='LOCAL'`).
- **Model**: balk als LS-01 (10 line2, Ø 20 mm); een veer k = 1000 N/m van de tip naar
  een vast punt op 0,5 m afstand, (a) langs Y, (b) onder 45° in het XY-vlak.
- **Randvoorwaarden en belasting**: balk ingeklemd, veerpunt `fixed`; P = 10 N in Y op
  de tip.
- **Referentie**: balk en veer parallel: (a) δ = P/(3EI/L³ + k), veerkracht kδ;
  (b) de tip beweegt (axiaal vrijwel star) alleen in Y, de veer rekt δ/√2 en levert in
  Y kδ/2: δ = P/(3EI/L³ + k/2).
- **Resultaat**: (a) δ en veerkracht 0,00% af (tol. 0,1%); (b) δ 0,00% (tol. 0,2%).
- **Interpretatie**: de veer werkt langs zijn eigen as. Vóór de correctie werkte een
  veer altijd in globaal X, ook als hij langs Y lag (KNOWN_BUGS 47 beschrijft wat nog
  niet met Mecway is vergeleken).

### LS-07 Verlijmd contact tussen schalen

- **Doel**: Mecway's verlijmde contact (`bondedtie`) tussen platen met niet-passende
  meshes → `LIAISON_MAIL` `TYPE_RACCORD='COQUE'`; draagt de lijmnaad een moment?
- **Model**: (a) ingeklemde plaatstrook 200 × 20 × 2 mm (DKT quad4) uit twee delen met
  eigen knopen: A (x = 0..100 mm, 10 × 4) en B (x = 100..200 mm, 10 × 7), verlijmd langs
  de naad (slave = rand van B, master = schaalvlakken van A); (b) dezelfde strook als
  één mesh 20 × 4. (c–e) T-stuk: plaat 100 × 60 mm, lange randen ingeklemd, met een
  rib 60 × 40 mm (vlak y = 30 mm) waarvan de onderrand op de plaat is verlijmd: (c) rib
  13 elementen lang tegen 20 in de plaat, voetlijn op een meshlijn van de plaat;
  (d) voetlijn midden in de plaatelementen (15 over de breedte); (e) gedeelde knopen.
  Voorbeeldmodel (a): `TestFiles/Voorbeelden/Voorbeeld_T.liml`.
- **Randvoorwaarden en belasting**: (a, b) `fixed` op de rand x = 0, P = 1 N in −Z op de
  vrije rand; (c–e) 1 N in +Y op de bovenrand van de rib (de rib buigt uit zijn vlak;
  als de lijm een scharnier was, zou het model een mechanisme zijn).
- **Referentie**: (a, b) Euler-balk δ = PL³/(3EI), φ = PL²/(2EI) met E: met vrije
  zijranden is M_y = 0 en is de buigstijfheid per breedte E t³/12; de inklemming
  verhindert de anticlastische kromming over een strook ~b (b/L = 0,1), daardoor is de
  plaat iets stijver (tolerantie 2 %). Daarnaast Mecway 34 (eigen solver) op model (b)
  (tolerantie 0,5 %) en de rotatie aan beide kanten van de naad (gelijk, 0,5 %).
  (c, d) model (e) (zelfde schema) en Mecway 34 op (e).
- **Resultaat**: (a) δ −1,07 % t.o.v. Euler, +0,08 % t.o.v. Mecway; φ −0,74 % en
  −0,00 %; rotatie B/A over de naad 0,99992. (b) δ −1,03 %, Mecway +0,12 %.
  (c) +0,10 % onder (e), +0,42 % t.o.v. Mecway. (d) −5,2 % (tolerantie 7 %). (e) +0,51 %
  t.o.v. Mecway.
- **Interpretatie**: de naad is stijf, ook voor buiging: de verlijmde strook ligt binnen
  0,04 % van één doorlopende mesh. Zonder de correctie in `bridge_mesh._coque_ddl`
  koppelde `LIAISON_MAIL` ook de rotatie om de plaatnormaal (bij DKT alleen een
  fictieve stijfheid) en stopte Code-Aster met `FACTOR_11`; nu blijft die rotatie weg
  als de master loodrecht op een globale as staat (anders zie (f–k)). Bij (d)
  interpoleert `LIAISON_MAIL` de plaatrotatie lineair over de knik onder de rib: 12 mm
  elementen −11 %, 4 mm −5 %, 1,3 mm −2 %; leg de voetlijn op een meshlijn. Mecway's
  eigen solver rekent (a), (c) en (d) niet: bij een schaalrand als slave koppelt hij
  geen rotaties (mechanisme, tip 3,7e6 m), daarom is Mecway alleen op de doorlopende
  meshes vergeleken.
- **Model (f–k)**: (f) strook (a) 30° gedraaid om de x-as (scheve master), last langs
  de plaatnormaal; (g) dunwandige buis R = 20 mm, t = 2 mm, L = 200 mm, ingeklemd, 1 N
  in −Z op de vrije rand, uit twee delen (16 en 24 elementen rond) verlijmd op
  x = 100 mm (gekromde master); (h) dezelfde buis als één mesh, 24 rond; (i) quad8-plaat
  100 × 40 mm (`COQUE_3D`, 10 × 4), ingeklemd op x = 0, met een quad8-rib (hoogte 20 mm)
  waarvan de voetlijn midden in de plaatelementen ligt (y = 25 mm), 10 N zijlast op de
  bovenrand; (j) idem met gedeelde knopen (plaat 10 × 8); (k) model (i) 30° gedraaid.
- **Referentie (f–k)**: (f) model (a) en Euler; (g) model (h) en Timoshenko
  (I = πR³t, schuifoppervlak πRt); (h) Timoshenko en Mecway 34; (i) model (j);
  (j) Mecway 34; (k) model (i) (zelfde model in het XY-vlak) en (j).
- **Resultaat (f–k)**: (f) δ 0,94220 mm, gelijk aan (a); rotatie B/A 0,99992. (g)
  2,7306e-7 m: +0,11 % t.o.v. (h), +0,27 % t.o.v. Timoshenko (de buis met 16 rond als
  één mesh: 2,7707e-7 m; de verlijmde buis ligt daartussen). (h) +0,16 % t.o.v.
  Timoshenko, +0,15 % t.o.v. Mecway. (i) −1,7 % onder (j) (de knik onder de rib, zoals
  (d); plaat 10 × 12: −0,5 %, 20 × 20: +0,1 % t.o.v. (j)). (j) +1,2 % t.o.v. Mecway
  (eigen quad8-schaal). (k) −0,05 % t.o.v. (i).
- **Interpretatie (f–k)**: bij een scheve of gekromde master schrijft de bridge per
  slave-knoop `LIAISON_DDL` (verplaatsingen en de twee rotaties in het raakvlak van de
  master) en zet `NPREC` op −1: anders meldt MUMPS ten onrechte `FACTOR_11` (gemeten:
  NPREC 8 en 10 stoppen, 12 en −1 geven dezelfde oplossing). Bij een kwadratische master
  schrijft de bridge alleen de verplaatsingen (`LIAISON_MAIL` vroeg DX van de
  QUAD9-middenknoop, `CHARGES2_31`); de rotaties blijven bij `LIAISON_MAIL`, zodat de
  middenknoop meetelt. Met de rotaties zonder middenknoop was (i) 8,7 % te slap.

### LS-08 Node temperature (thermische spanning per knoop)

- **Doel**: Mecway's *Node temperature* (`temperature3`, een temperatuur per knoop, ook
  het resultaat van *Transfer temperatures from solution*) met een *Thermal stress* →
  knoopveld `TEMP` in `AFFE_VARC`, zoals *Temperature* (`temperature2`).
- **Model**: α = 1,2e-5 1/K, E = 210 GPa, ν = 0,3, Tref = 293,15 K. (a) staaf als
  TH-03b (1 × 0,1 × 0,1 m, 4 hex8, u_x = 0 op beide uiteinden, dwarsrichting vrij),
  Node temperature Tref + 100 K op alle knopen. (b) vrije balk 100 × 10 × 10 mm (10 × 1
  × 4 hex20) met T = Tref + 100 K · z/h op elke knoop (lineair over de dikte); u_x = 0 op
  x = 0, u_y = 0 op y = 0, u_z = 0 in de oorsprong. (c) vrije staaf 100 × 10 × 10 mm (4
  hex8): `temperature2` Tref + 100 K op de knopen in x = 0 en Node temperature
  Tref + 200 K op die in x = L; de knopen ertussen krijgen geen temperatuur. (d) als (b)
  met hex8 en `elem_hex8` = `LINE_QUAD`.
- **Referentie**: (a) σ_xx = −EαΔT, u_y = (1+ν)αΔT·b, reactie EαΔT·A. (b, d) lineaire
  temperatuur in een vrij lichaam: spanningsloos, u_z = −αg(x² + y² − z²)/2 met
  g = ΔT/h (Timoshenko & Goodier §150): u_z(L, 0, 0) = −6,0e-4 m. (c) knopen zonder
  temperatuur op Tref, elementgemiddelden +50 en +100 K: u_x(L) = α·150 K·L/4 =
  4,5e-5 m. Daarnaast Mecway 34 (eigen solver, headless) op (a)–(c).
- **Resultaat**: alle grootheden exact (≤ 2e-10); max |σ_xx| in (b) en (d) 0,04 Pa.
  Mecway: (a) reactie 2,52e6 N, (b) −6,0000e-4 m, (c) 4,5000e-5 m, alle drie gelijk.
- **Interpretatie**: Node temperature werkt als Temperature; knopen zonder temperatuur
  staan op de referentie, ook naast knopen met een temperatuur (c, gelijk aan Mecway).
  Mecway 34 interpoleert de knooptemperatuur in het element (b: ook met één laag hex20
  exact), niet het elementgemiddelde uit de manual (KNOWN_BUGS 17). In (d) krijgen de
  middenknopen die `LINE_QUAD` toevoegt de geïnterpoleerde temperatuur; met de
  referentietemperatuur zou de balk niet kloppen. Mecway zelf rekent (d) met
  incompatibele hex8: −6,28e-4 m (+4,7 %). Verder headless vergeleken (8 hex8, Node
  temperature +50 K, `LINE_QUAD`): modaal met voorspanning 284,96 Hz tegen Mecway
  286,18 Hz, knik 3,3969 tegen 3,4010; in de bridge en in Mecway geven `temperature2`
  en `temperature3` dezelfde uitkomst (ook statisch, niet-lineair statisch en D30).
### LS-60 – LS-63 Element offset (schalen en balken)

- **Doel**: Mecway's *Element offset* (`<offset>` op een elementselectie,
  `bridge_offset.py`). Schaal: middenvlak op afstand w langs +W (elementnormaal);
  DKT/DST krijgen `EXCENTREMENT` (+ `INER_ROTA`), COQUE_3D kent dat niet
  (`CALCULEL2_31`) en ligt op eigen knopen met een starre arm (`LIAISON_DDL`) naar elke
  Mecway-knoop. Balk: as op (x, y, z) globaal van de knopen, ook met starre armen.
- **Model**: (60a/b) ingeklemde strook 200 × 20 × 2 mm, 20 × 4 quad4 (a, DKT) of quad8
  (b, COQUE_3D), w = 10 mm, 100 N trek (+X) op de knopen van de vrije rand. (61) twee
  DKT-lagen op hetzelfde knoopnet, w = +10 en −10 mm, 100 N eindlast. (62) T-balk:
  flens DKT 1000 × 50 × 5 mm, lijf RectBar 5 × 100 mm op de middellijn met offset
  z = −52,5 mm, 100 N eindlast. (63) samengestelde balk als Mecway's voorbeeld
  *CompositeBeam* (manual par. 11.2): lijf RectBar 0,2 × 0,01 m (E = 5,2 GPa),
  flens 6 × 2 quad8 (t = 0,01 m, E = 2,6 GPa) met w = 0,105 m, torsiemoment 6 N m.
- **Referentie**: (60) uniforme kromming P e/(EI): tip w = P e L²/(2EI) = 7,143 mm,
  σ = P/(BT) ± 6Pe/(BT²) = 77,5 / 72,5 MPa; (61) I = 2(BT³/12 + BTe²) (Steiner),
  w = PL³/(3EI) = 0,1582 mm; (62) T-doorsnede (Steiner), 0,18108 mm; (63) hoek
  ML/(J(G_f + G_w)) = 0,108 rad (manual), draaiing om het dwarskrachtcentrum. Daarnaast
  Mecway 34 (eigen solver, headless) op elk model; reacties: evenwicht.
- **Resultaat**: (60a) 7,085 mm (Mecway 7,090, −0,07 %), (60b) 7,097 mm (Mecway 7,096,
  +0,02 %), rotatie ≤ 0,2 % van Mecway, von Mises onder/boven 77,50 / 72,50 MPa; (61)
  0,15657 mm (Steiner −1,0 %, Mecway 0,16090: −2,7 %); (62) 0,18100 mm (Steiner
  −0,05 %, Mecway 0,18490: −2,1 %); (63) 0,10918 rad (Mecway 0,10913) en
  zijverplaatsing 11,407 mm (Mecway 11,405); som van de reacties overal gelijk aan de
  last (moment om de X-as in 63: 6,000 N m).
- **Interpretatie**: het teken van w en de starre arm komen overeen met Mecway; de
  verschillen in 61/62 zitten in de plaat (Mecway's MITC4 iets slapper), de bridge
  ligt daar dichter bij Steiner. Met de starre armen nemen de knopen de reactie op
  (de krachten in de arm zelf vallen weg). Met *Fixed support* op een knoopselectie
  rekent Mecway in model 63 met een fijner mesh anders dan met de vlakken (KNOWN_BUGS
  108c); de bridge is in beide gelijk. Zonder `POSTTRAITEMENTS='FORCE'` stopte
  CompositeBeam met `FACTOR_57` (foutgrens 5e-6); de bridge zet die verfijning aan
  zodra er starre armen zijn.

### LS-64 – LS-67 Element offset: combinaties

- **Doel**: element offset samen met andere invoer (`tests_offset.py`). (64) twee
  schaalelsets die elk voor een deel verschoven zijn: elke elset krijgt een eigen
  restgroep zonder `EXCENTREMENT` (eerder kreeg de tweede elset dezelfde groepsnaam en de
  eerste geen `COQUE`: `CALCULEL_6`). (65) de extra resultaatvelden van verschoven
  quad8-schalen (cellen op eigen knopen, via de knoopgroepen `BROFL` terug naar de
  Mecway-elementen; eerder ontbraken ze stil). (66) verlijmd contact met een verschoven
  quad8-strook als master (eerder onterecht `FACTOR_11`). (67) een last op het randvlak
  van een verschoven schaal.
- **Model**: strook 200 × 20 × 2 mm als LS-60. (64) in de breedte twee elsets van 20 × 2
  quad4 (DKT), w = 10 mm op de elementen met x < L/2, 100 N trek op de knopen van de
  vrije rand. (65) LS-60b (quad8) met `shell_stresses`, `shell_forces`, `strain` en
  `safety_factor` (S = 250 MPa). (66) LS-07a met quad8, w = 1 mm op deel A (master),
  1 N eindlast. (67) LS-60a met de 100 N als last op het randvlak.
- **Referentie**: (64) kromming P e/(EI) alleen over x < L/2: tip 3 P e L²/(8EI) =
  5,357 mm; σ bij L/4 als LS-60, bij 3L/4 alleen P/(BT) = 2,5 MPa. (65) bij x = L/2:
  σxx onder/boven 77,5 / −72,5 MPa, N_u = P/B = 5000 N/m, εxx onder = σ/E, factor of
  safety S/σ_vM = 3,226; elk van de 80 elementen een waarde. (66) P L³/(3EI) =
  0,95238 mm; Mecway rekent het verlijmde model niet (LS-07a), dus de doorlopende strook
  (0,94148 mm). (67) Mecway 34: tip 0 (de last grijpt aan op de verschoven rand).
  Daarnaast Mecway 34 headless op 64.
- **Resultaat**: (64) 5,268 mm (−1,7 %; Mecway 5,277 mm, −0,16 %), σ 77,19 MPa (L/4)
  en 2,500 MPa (3L/4). (65) alle 80 elementen, waarden op 1e-5 gelijk aan de theorie,
  ook de knoopwaarden. (66) 0,94266 mm (−1,0 % t.o.v. Euler, +0,13 % t.o.v. Mecway
  doorlopend). (67) 7,085 mm tegen 0 in Mecway: **BEKEND** (KNOWN_BUGS 108).
- **Interpretatie**: (67) de bridge zet een last op een vlakselectie op de randcel op de
  Mecway-knopen (`FORCE_ARETE`, ook bij `EXCENTREMENT`), Mecway op de verschoven rand;
  het verschil is een moment w × F per lengte (WARNING). Een last op een knoopselectie
  werkt in beide op de knopen (LS-60). Bij verlijmd contact op verschoven schalen meldt
  de bridge aan welk vlak hij koppelt (KNOWN_BUGS 108).

### LS-20 Configuraties (lastgevallen G, Q en ULS)

- **Doel**: de instelling *Configuratie* (`configuration`) kiest welke configuratie de
  bridge rekent; `auto` volgt de regel (de enige, de enige zonder onderdrukte items,
  anders de eerste).
- **Model**: staaf 1 × 0,1 × 0,1 m, 4 × 1 × 1 hex20, staal (ρ = 7850 kg/m³),
  symmetrievlakken x = 0, y = 0, z = 0. Configuraties G (gravity 9,81 m/s² langs x),
  Q (trek 1 MPa op het eindvlak) en ULS (eigen lastitems 1,2 g en 1,5 q, zoals in
  Mecway: een configuratie heeft geen factor); elk lastitem is in de andere twee
  onderdrukt (`<suppressed configuration=".."/>`).
- **Referentie**: eindverplaatsing u = ρgL²/(2E) + qL/E (eenassig) en reactiekracht
  ρgAL + qA (evenwicht), met de factoren van de gekozen configuratie.
- **Resultaat**: LS-20a/b/c (G, Q, ULS gekozen): reactiekracht exact, u ≤ 0,06% af
  (bij G hindert u = 0 op x = 0 de dwarscontractie iets). ULS = 1,2 G + 1,5 Q op
  4,6e-16 relatief (alle knopen, nagerekend uit de drie runs). LS-20d (`auto`, elke
  configuratie heeft onderdrukte items): G met een WARNING. LS-20e (kopie met alleen
  ULS, instelling Q die niet in het model staat): WARNING daarover, dan ULS; geen
  WARNING meer over een dubbelzinnige keuze. Met Mecway's
  IronPython: `pick_configuration` + `splice_results` zetten de resultaten in de
  solution van de gekozen configuratie en laten die van de andere staan.

### LS-50 Ingeklemde balk met line3-elementen

- **Doel**: kwadratische balkelementen (line3). Code-Aster heeft geen kwadratisch
  balkelement; de bridge splitst elk line3-element in de middenknoop in twee SEG2-cellen
  (`POU_D_E`), met de oriëntatie per helft (KNOWN_BUGS 107). Module `tests_balken.py`.
- **Model**: L = 1 m, 5 line3-elementen langs X, rechthoekige staaf (RectBar);
  (a, b) 20 × 20 mm, (c) 20 × 10 mm met oriëntatievector (0, 0, 1) per element (V = Z).
- **Randvoorwaarden en belasting**: ingeklemd in x = 0; (a) P = 100 N in −Z op de tip;
  (b) line pressure q = 100 N/m in −Z op een elementselectie met alle elementen
  (`FORCE_POUTRE`); (c) P = 100 N in −Y op de tip (buiging om V, I = a b³/12).
- **Referentie**: Euler-balk (Roark tabel 8.1 gevallen 1a en 2a): δ = PL³/(3EI),
  φ = PL²/(2EI), w(x) op de middenknoop x = 0,1 m, δ = qL⁴/(8EI); reactie = evenwicht.
  Daarnaast Mecway 34 headless: (1) dezelfde balk met 10 line2-elementen op dezelfde
  knopen in Mecway's eigen solver (die kent geen line3-balk; tolerantie 0,1 %) en (2) het
  line3-model met CCX (B32R; tolerantie 4 %, zie interpretatie).
- **Resultaat**: alle grootheden exact (< 1e-6) t.o.v. Euler en t.o.v. Mecway met line2;
  ook de middenknopen. Mecway/CCX: −2,3 % (a), −3,0 % (b), −3,2 % (c).
- **Interpretatie**: twee Euler-cellen per element zijn exact voor een eindlast en een
  gelijkmatige last; de middenknoop krijgt gewone resultaten. De oriëntatievector werkt
  per helft (zonder zou (c) vier keer zo stijf zijn). CCX zet de B32R uit in een C3D20R per
  element (één element over de doorsnede) en is daardoor 2–3 % stijver dan de theorie;
  dat is een eigenschap van CCX. Een ronde staaf rekent Mecway/CCX niet (Mecway schrijft
  `SECTION=PIPE` met binnenstraal 0, CCX: "nonpositive jacobian"), daarom een rechthoek.

### LS-51 Flexible joint on beam

- **Doel**: Mecway's *Flexible joint on beam* (`<flexiblejoint><rotu/><rotv/><rotw/>`,
  manual v33 par. 9.12): het uiteinde van een balkelement roteert vrij om de gekozen
  lokale assen. Vertaling: een eigen knoop voor dat uiteinde, met `LIAISON_DDL` aan de
  Mecway-knoop gekoppeld (translaties en de niet-vrije rotaties, in de lokale assen
  zoals Mecway: U langs de balk, V uit de oriëntatie, W = U × V).
- **Model**: L = 1 m, Ø 20 mm, 10 line2 (e: 4 line3), beide uiteinden ingeklemd, P = 100 N
  in het midden; joint op het eindvlak van het element rechts van het midden.
  (a) balk langs X, last −Y, joint om W (= Z); (b) idem, joint om V (= Y); (c) joint om W
  aan beide kanten van de middenknoop; (d) joint om U, V en W op het ingeklemde eindvlak
  bij x = L; (e) als (a) met line3-elementen; (f) balk langs Z, last +X, joint om V
  (Mecway: V = Y bij een verticale balk; buiging om Y).
- **Referentie**: (a, c, e, f) twee ingeklemde balken L/2 met P/2 aan de tip:
  δ = PL³/(48EI), rotatie links van het scharnier PL²/(16EI); (b) geen effect,
  δ = PL³/(192EI) (Roark 1d); (d) ingeklemd-scharnierend: δ = 7PL³/(768EI), moment in de
  inklemming 3PL/16 (Roark 1c). Daarnaast Mecway 34 (eigen solver) op hetzelfde model;
  (c) middenknoop: rotatie 0, zoals Mecway. Mecway rekent (e) niet (line3 alleen met
  CCX, de joint niet met CCX).
- **Resultaat**: alle controles exact (< 1e-9) t.o.v. de theorie en t.o.v. Mecway. Ook
  een modale analyse van (a) met dichtheid geeft dezelfde frequenties als Mecway
  (57,887 / 92,089 / 253,905 Hz); model (c) modaal rekent Code-Aster wel, Mecway niet.
- **Interpretatie**: de lokale assen en de keuze van de vrije rotaties komen overeen met
  Mecway; (b) en (f) zouden met verwisselde assen fout gaan. Heeft de knoop geen ander
  element met rotaties (c, d), dan krijgt hij een POI1 `DIS_TR` zonder stijfheid en de
  overgebleven rotatie(s) op 0 (tenzij een voorwaarde ze vastlegt, d). Een vaste
  voorwaarde op een *elementselectie* met het element met de joint stopt met `FACTOR_11`
  (KNOWN_BUGS 106); leg hem op knopen of vlakken.

### LS-52, LS-53 Flexible joint met element offset en snedekrachten per element

- **Doel**: (52) flexible joint samen met een element offset (`tests_balken.py`). Eerder
  kreeg een joint op een verschoven element een eigen knoop die in geen cel zat, en een
  knoop met alleen een verschoven balk en een balk met een joint had geen
  vrijheidsgraden (beide `CHARGES2_31`). (53) de snedekrachten per element
  (`beam_forces` als elementwaarden) naast een joint en op line3-balken; eerder ontbrak
  het element met de joint en elke line3-balk stil.
- **Model**: LS-51a (joint om W rechts van het midden) met een offset z = 10 mm
  (globaal, loodrecht op het buigvlak) op (52a) de rechterhelft, dus ook op het element
  met de joint, of (52b) de linkerhelft. (53a) LS-51a, (53b) LS-51e (4 line3), met
  `beam_forces`.
- **Referentie**: (52a) de joint vervalt (WARNING), dubbel ingeklemd: δ = PL³/(192EI) =
  0,31578 mm; (52b) scharnier: δ = PL³/(48EI) = 1,2631 mm; Mecway 34 (eigen solver)
  geeft in beide 1,2636 mm. (53) elke helft is een ingeklemde balk L/2 met P/2: M = 0 in
  het scharnier, (P/2) h verder op het element, V = P/2.
- **Resultaat**: (52a) 0,31628 mm (+0,16 %; t.o.v. Mecway **BEKEND**, KNOWN_BUGS 108);
  (52b) 1,2636 mm (+0,04 %, gelijk aan Mecway); reacties = last. (53a) alle 10
  elementen, M in het scharnier 2e-13 N m, 5,000 N m op x = 0,6 m, V = 50 N; (53b)
  alle 4 elementen met drie waarden: 0 / 6,25 / 12,5 N m.
- **Interpretatie**: Mecway houdt een joint op een verschoven element wel aan; de bridge
  verbindt het element dan star met de arm (open, KNOWN_BUGS 108). Een line3-balk
  krijgt zijn elementwaarden uit beide SEG2-helften (eind 1 en midden uit de eerste,
  eind 2 uit de tweede).

### Extra resultaatvelden (LS-30 .. LS-32, NL-30 .. NL-32, MO-30, DY-30)

Velden `beam_forces`, `shell_stresses`, `shell_forces`, `strain`, `safety_factor` en
`contact` ([`Handleiding.md`](Handleiding.md) §4.1), getest onder Mecway's eigen
variabelenamen (`TestFiles/Verificatie/tests_resultaatvelden.py`). De namen, assen en
tekens zijn eerst headless in Mecway 34 nagelopen op dezelfde modellen; daaronder de
vergelijking met Mecway's oplossing.

| Case | Model | Gecontroleerd | Referentie | Resultaat |
|---|---|---|---|---|
| LS-30 / LS-30b | ingeklemde balk 1 m (4 POU_D_E, 20 x 30 mm), tipkracht N 1000 / V_v 200 / V_w -300 N en T 50 N.m; recht en onder 30° | `tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv` (inklemming), `bendingmomw` (midden) | statica | alle exact (≤ 1e-12); Mecway headless: zelfde waarden en tekens |
| LS-31 | schaalstrook 100 x 20 x 2 mm scheef in de ruimte (quad4, DKT), trek 600 N + dwarskracht 3 N | `forceperlengthu`, `momentu`, `stress<ij>u1/m1/b1` (globaal), `lstrain<ij>u/b`, `factorofsafety` op x = L/2 | plaattheorie, σ = N/t ± 6M/t², eenassig e1 e1^T | ≤ 0,8% (lstrainxxb), de rest ≤ 0,2% |
| LS-31b | idem quad8 (COQUE_3D) | idem + `shearuw` (gemiddeld over de breedte) | -P/b = -150 N/m | ≤ 0,6%; Q exact |
| LS-31c | idem quad4 met `orientationu*` langs de breedte | `forceperlengthv` = N_u, `momentv`, `forceperlengthu` ≈ 0 | idem | exact |
| LS-31d | idem met de U-as uit een *Element orientation*-kaart | als LS-31c | idem | exact, gelijk aan LS-31c |
| LS-32 / LS-32b | staaf hex8 eenassige trek 100 MPa; kubus zuivere afschuiving 50 MPa | `lstrainxx/yy/zz`, `lstrainxy` (γ), `factorofsafety` | σ/E, -νσ/E, τ/G; S/σ, S/(√3 τ) | exact |
| NL-30 / NL-30b | contact-patchtest hex8 passend (STANDARD, `CONT_NOEU`) en hex20 (PENALISATION, alleen `LAGS_C`) | `contactpressure` (gemiddeld, kleinste), `contactstate` | p = F/A = 10 MPa, status 1 | exact |
| NL-30c | twee balken met de tips op elkaar (NL-03b) | `contactstate` tip 1, begin slave-zone 0; `contactpressure` daar | open: 0 | status exact; druk 448 Pa (0,06% van de piek, numeriek) |
| NL-31 | staaf hex20, 5% opgelegde rek | `greenlagrangestrainxx` | (λ² - 1)/2 = 0,05125 | exact |
| NL-32 | model van LS-30 in STAT_NON_LINE | als LS-30 | statica | exact |
| MO-30 | ingeklemde balk (20 POU_D_E), mode 1 | M(0) / w(L) (grootte) | E I λ1² / L² (Blevins tabel 8-1) | exact (14767) |
| DY-30 | balk van LS-30, last in 2 s opgebouwd (DYNA_NON_LINE) | `bendingmomv` inklemming op t = 2,5 s | statica 300 N.m | +0,05% |

Vergelijking met Mecway (headless, Mecway 34, zelfde modellen, interne solver; contact
met CCX):

- balken (LS-30, LS-30b): alle zes snedekrachten in elke knoop gelijk (≤ 1e-11);
- schaalstrook in het XY-vlak onder 30° en scheef in de ruimte (= LS-31, quad4 en
  quad8): membraankrachten gelijk (< 1e-6), op x = L/2 globale spanningen en rekken
  0,0 .. 0,2% verschil, momenten < 1%; bij de inklemming tot ~15% (DKT/COQUE_3D tegen
  MITC4/MITC8, zie KNOWN_BUGS 2); de dwarskracht verloopt in beide over de breedte
  (Mecway quad8 -253 / -150 / -47 N/m, de bridge -247 / -150 / -53);
- totale rek staaf (S30): `lstrainxx` 4,7619e-4 in beide; enkelvoudige afschuiving:
  Mecway's `lstrainzx` = τ/G, dus γ (de bridge rekent EPXY x 2);
- contact-patchtest (CCX): `contactpressure` 9,99974 MPa (Mecway) tegen 10,000 MPa;
  `greenlagrangestrain*` gelijk (zz -4,76e-5);
- `factorofsafety`: Mecway schrijft hem headless niet (hij rekent hem bij het tonen);
  een door de bridge geschreven `factorofsafety` toont Mecway als item *failure*.

Mecway leest de gesplitste resultaten (IronPython `bridge_results_liml.splice_results`,
daarna headless `mw.open` en `solution.node_value`) en maakt zelf de items *tensile
force*, *shear force*, *bending moment*, *torsion moment*, *stress*, *strain*, *force
per length*, *moment per length*, *failure*, *contact stress* en *contact state* aan.
Route `tabel` (LS-30, LS-32, NL-31 met een nep-solution in CPython): `beam_forces` en
`strain` (ook Green-Lagrange) gelijk aan route `liml`.
### LS-40 .. LS-44 Formules in x, y, z

- **Doel**: Mecway-formules in x, y, z (KNOWN_BUGS 45, opgelost; grenzen KNOWN_BUGS 104)
  voor druk, traction, kracht, line pressure en opgelegde verplaatsing/rotatie →
  `FORMULE` van X, Y, Z in `AFFE_CHAR_MECA_F`. Module `tests_formules.py`.
- **Model**: blok 1 × 2 × 0,1 m (hex8 4 × 8 × 1), onderkant `fixed`; ingeklemde balk
  (10 line2, Ø 20 mm, L = 1 m); plaat 1 × 2 m, t = 10 mm (quad4 4 × 8), rand y = 0
  ingeklemd.
- **Belasting**: (40a) druk `3*y^2` kPa op de bovenkant (positie in m); (40b) idem als
  `3e-6*y^2` met positie in mm; (41) druk `3*y^2` op de helft y < 1, `10*x` op de helft
  y > 1 en traction X = `2*x+1` kPa, drie functielasten in één run; (42a) opgelegde
  verplaatsing Z = `0.001*x+0.002*y` mm op de bovenkant; (42b) idem langs (1, 1, 0) =
  `0.001*(1+x)` mm (`LIAISON_OBLIQUE`); (42c) opgelegde rotatie om Y =
  `0.001*(1+x)` rad aan de tip van de balk; (43a) line pressure Z = `-1000*x` N/m op de
  balk; (43b) idem met gravity (ρ = 7850 kg/m³); (44a) druk `3*y^2` Pa op de plaat
  (DKT), (44b) idem met `COQUE_3D`.
- **Referentie**: de integraal van de formule: 40: reactie ∫3y² dA = 8 kN, moment om X
  ∫3y³ dA = 12 kN·m, om Y −4 kN·m; 41: 1 + 5 = 6 kN, 0,75 + 7,5 = 8,25 kN·m, reactie X
  −4 kN; 42: de formule in de knopen (42c: θ = 0,002 rad, zuiver moment w = θL/2); 43: reactie q₀L/2 (+ ρAgL), doorbuiging tip
  11q₀L⁴/(120EI) (+ ρAgL⁴/(8EI)) (Roark tabel 8.1); 44: reactie 8 N en Mecway 34 (eigen
  solver) voor de doorbuiging van de vrije rand.
- **Resultaat**: 40a/b, 41, 42, 43 exact (≤ 1e-6). 44a: reactie 8,0625 N (+0,78 %,
  tolerantie 1 %), doorbuiging +1,3 % t.o.v. Mecway (tolerantie 2 %); 44b: reactie
  exact, doorbuiging +0,63 % (tolerantie 1 %; ook met een constante druk liggen
  schalen ~0,7 % van Mecway, KNOWN_BUGS 2).
- **Interpretatie**: Code-Aster integreert de formule op volumevlakken, `COQUE_3D` en
  balken in de integratiepunten (exact voor deze veeltermen); DKT neemt een functie in
  de knopen (trapeziumregel: +0,78 % op dit grove mesh, O(h²)). Mecway 34 (headless,
  `mw_solve.py`) geeft voor 40 en 41 dezelfde reacties en momenten (8000 N,
  12000 N·m; 6000 N, 8250 N·m), ook met positie in mm. Kracht, line pressure en
  opgelegde verplaatsing/rotatie met x, y, z in de formule legt Mecway 34 niet op
  (reacties 0, interne solver en CCX); de bridge wel, met een WARNING. Druk op schalen
  gaat via `FORCE_COQUE PRES` (`PRES_REP` met een functie stopt op DKT en COQUE_3D met
  `ELEMENTS4_92`). Drie lasten `AFFE_CHAR_MECA_F` met elk een `FORMULE` in één
  `EXCIT` rekenen elk met hun eigen functie (anders dan thermisch `SOURCE`, [Thermisch.md](Thermisch.md) §3); twee functies in één
  `DDL_IMPO`-last (testrun met twee selecties) ook.

### LS-70 … LS-78 Balkorientatie (statisch)

Uitkragende balk en raamwerk met en zonder Mecway-orientatie (*orientation vector* en
*angle*); toelichting, model en resultaten in §7, *Balkorientatie*. Alle tipverplaatsingen
en σ_xx max/min in de inklemming ≤ 1e-7 t.o.v. Euler-Bernoulli, het raamwerk gelijk aan
Mecway (≤ 3e-8).

### Conclusie lineair statisch

Alle 49 cases (122 controles) liggen binnen de tolerantie. Waar de theorie exact is
(Navier, Lamé, LE1, Euler-balk), convergeren de vertaalde modellen met de verwachte orde
naar de referentie; in LS-02 is het verschil met Timoshenko een modelfout, dezelfde in
Mecway en CCX. Geverifieerd zijn: `traction` op volumevlakken, `surfacepressure` op
volume-, schaal- en schaalrandvlakken, `fixed`, `displacement`, `noderotation`,
`symmetry` (volumevlakken en schaalranden), `frictionless`, `force`, veren, de
elementkeuzes hex8 `3D`/`LINE_QUAD`, hex20, DKT, `COQUE_3D` en `POU_D_E`, en de
resultaatvelden `displ*`, `stress*` (`SIGM_NOEU`), `vonmisesu1/m/b` en
`reactionforce*`.

### Foutschatter (FS)

Mecway S30 → `lin_static_3d` met `error_estimator` aan (standaard) → `CALC_ERREUR`
`ERME` ([Foutschatter.md](Foutschatter.md)). Module `tests_foutschatter.py`, draaien
met `python run_verificatie.py FS`. De globale schatting komt uit het blok dat
Code-Aster in de `.mess` zet (`verif_lib.error_summary`), het veld `errorestimate` uit
het resultaatbestand. De orde in een reeks is p = ln(η_grof / η_fijn) / ln 2 van de
absolute globale schatting η tussen twee opeenvolgende meshes (h gehalveerd).

#### FS-01 Ingeklemde balk, hex8 (model van LS-02-h8)

- **Doel**: daalt de schatting bij verfijnen met de verwachte orde, volgt ze de
  werkelijke fout, en zit de grootste fout waar je hem verwacht?
- **Model**: LS-02 (1 x 0,1 x 0,1 m, traction P = 10 kN op het eindvlak, eindvlak van
  de inklemming vast), hex8 `3D`, n = 1, 2, 4, 8, 16 elementen over de hoogte.
- **Referentie**: (1) doorbuiging: Timoshenko-balk (Young & Budynas, 2002, tabel 8.1
  geval 1a, plus afschuiving), zoals LS-02. (2) Werkelijke relatieve fout in de
  energienorm: met een gelijkmatige traction is de uitwendige arbeid P·w (w =
  gemiddelde doorbuiging van het eindvlak), dus ‖u − u_h‖²_E = P (w_∞ − w_h)
  (Galerkin-orthogonaliteit) en de relatieve fout sqrt((w_∞ − w_h)/w_∞). w_∞ =
  0,001906 m is de limiet van het 3D-model (Richardson op LS-02-h20: 0,0019057 m; op
  LS-02-h8 n = 4…16: 0,0019067 m). (3) Lineaire elementen: energiefout O(h), orde 1
  (Verfürth, 1996). (4) De fout is het grootst bij de singuliere randen van de
  inklemming.
- **Controles**: doorbuiging (tolerantie als LS-02); effectiviteitsindex = geschatte /
  werkelijke relatieve fout, verwacht O(1) en ongeveer constant (Ainsworth & Oden,
  2000): 2,0 ± 1,0; orde van η 1,0 ± 0,2 (vanaf n = 4); x van de knoop met de grootste
  `errorestimate` op x = 0 (± één element).
- **Resultaat**:

| n | knopen | globale fout (schatting) | η | orde p | werkelijke fout | effectiviteit | doorbuiging t.o.v. w_∞ |
|---|---|---|---|---|---|---|---|
| 1 | 44 | 79,5% | 2,33e6 | – | 59,4% | 1,34 | −35,3% |
| 2 | 189 | 61,1% | 1,51e6 | (0,62) | 35,3% | 1,73 | −12,5% |
| 4 | 1025 | 37,9% | 8,22e5 | 0,88 | 18,9% | 2,01 | −3,6% |
| 8 | 6561 | 20,6% | 4,24e5 | 0,96 | 9,7% | 2,11 | −0,95% |
| 16 | 46529 | 10,7% | 2,17e5 | 0,96 | 4,8% | 2,22 | −0,23% |

  De grootste fout zit op elk mesh bij de inklemming (x = 0).
- **Interpretatie**: de globale fout daalt monotoon; η convergeert met orde 0,88 →
  0,96, dus naar 1 zoals verwacht voor lineaire elementen (n = 1 → 2 is nog niet
  asymptotisch). De relatieve fout zelf (η / sqrt(η² + ‖σ‖²)) heeft bij de grove meshes
  een lagere orde (0,69 tussen n = 2 en 4) omdat hij naar 100% verzadigt; vanaf n = 4
  0,88 en 0,94. De effectiviteitsindex is O(1) en loopt maar langzaam op (1,3 → 2,2): de
  schatter is een betrouwbare, iets pessimistische maat voor de energiefout. De
  doorbuigingsfout is veel kleiner dan de energiefout (ongeveer het kwadraat).

#### FS-02 Dikwandige cilinder, hex20 (model van LS-04)

- **Doel**: orde bij kwadratische elementen en een gladde oplossing; plek van de
  grootste fout.
- **Model**: LS-04 (a = 0,1 m, b = 0,2 m, p = 100 MPa, kwart cilinder, symmetry op de
  zijvlakken, frictionless op de einden, buitenwand vrij), hex20, n = 1, 2, 4, 8
  elementen over de wand (2n in de omtrek).
- **Referentie**: Lamé (Timoshenko & Goodier, 1970); kwadratische elementen en een
  gladde oplossing: energiefout O(h²), orde 2; de grootste spanningsgradiënt aan de
  binnenwand.
- **Controles**: u_r binnenwand (als LS-04); orde van η 2,0 ± 0,3; straal van de knoop
  met de grootste `errorestimate` = a (± één element).
- **Resultaat**: globale fout 12,5 / 3,44 / 0,894 / 0,239%; orde 1,87 / 1,95 / 1,91; de
  grootste fout op elk mesh aan de binnenwand.
- **Interpretatie**: orde 2 zoals verwacht. De vrije buitenwand krijgt de druk ~0 van
  de bridge (twee tot zestien vrije vlakken); de symmetrie- en frictionless-vlakken
  hebben geen randterm.

#### FS-03 Code-Aster-testcase sslv153a via de bridge

- **Doel**: dezelfde schatting als Code-Aster's eigen testcase, via de hele keten
  (`.liml` → bridge → Code-Aster), met een gemengd mesh.
- **Model**: het mesh van sslv153a (`sslv153a.mmed`: 11 knopen, een hexa8, penta6,
  pyram5 en tetra4), in de `.liml` gezet; `elem_hex8` = `LINE_QUAD` (de test doet
  `CREA_MAILLAGE LINE_QUAD`); E = 400 000, ν = 0,3; fixed op MURHEXA en MURPENT; druk 13,
  14, 15 en 16 op CHARTETR, CHARPYRA, CHARPENT en CHARHEXA. De groepen LIBRE en LIBRE2
  (druk 1e-14 in de test) zijn in de `.liml` gewone vlakken zonder last: de bridge
  maakt er zelf vrije vlakken van.
- **Referentie**: TEST_RESU van sslv153a (primair probleem, NON_REGRESSION): DZ in
  knoop MESURE −0,018667672103377813, `ERREST` van `ERME_NOEU` 9339,361119203888; de
  globale fout 51,518% uit de `.mess` van de testcase (§10).
- **Resultaat**: alle drie gelijk binnen 1e-6 relatief.
- **Interpretatie**: de vrije-vlakkenzoeker vindt precies de spanningsvrije randen van
  de testcase, de lasten zijn goed samengevoegd en `ERME_NOEU` komt als knoopveld in de
  resultaten.

#### Conclusie foutschatter

Alle 10 cases (32 controles) liggen binnen de tolerantie. De schatting daalt met de
verwachte orde (1 voor hex8, 2 voor hex20), volgt de werkelijke energiefout met een
effectiviteitsindex van 1,3…2,2, wijst de inklemming en de binnenwand aan als
grootste fout, en is gelijk aan Code-Aster's eigen testcase. Niet gedekt: tet- en
wedge-elementen apart (wel in sslv153a en sslv111f), schalen en balken (geen
schatting). De weergave in de Mecway-GUI is met de hand nagelopen.

### Breukmechanica (BR)

Mecway S30 met `SCHEUR_`-selecties → `lin_static_3d` → `MECA_STATIQUE`, daarna
`DEFI_FOND_FISS`, `CALC_G` `OPTION=('G', 'K')` en `POST_K1_K2_K3`
([Breukmechanica.md](Breukmechanica.md)). Module `tests_breukmechanica.py`, draaien met
`python run_verificatie.py BR`; XFEM (BR-07..14) onderaan dit hoofdstuk. De waarden komen uit de tabel
`<model>_verif_scheur.csv` van de run (`bridge_fracture.read_csv`); "midden" is het
frontpunt het dichtst bij de halve frontlengte. Standaardinstellingen (R_INF/R_SUP
automatisch, `LINEAIRE`), behalve BR-04.

#### BR-01 Middenscheur in een plaat, vlakke rek, beide lippen

- **Doel**: K_I en G van een doorgaande scheur onder trek, met een scheur die open is
  zoals na Mecway's *Disconnect elements* (dubbele knopen op de lippen).
- **Model**: plaat met halve breedte b = 0,1 m, halve scheurlengte a = 0,05 m (a/b =
  0,5), halve hoogte H = 0,3 m (H/b = 3), dikte 0,05 m; half model in x (symmetrie
  door het scheurmidden), beide helften in y; de onderhelft heeft eigen knopen op y = 0
  voor x < a. DZ = 0 op beide zijvlakken (vlakke rek). hex20, aan het front h = a/40 =
  1,25 mm, geometrisch oplopend; 2 elementen over de dikte (5 frontknopen). Trek σ =
  100 MPa op y = ±H. E = 210 GPa, ν = 0,3. 8997 knopen, 1536 elementen.
- **Referentie**: K_I = σ √(πa) F(a/b), F = √(sec(πa/2b)) (1 − 0,025 (a/b)² +
  0,06 (a/b)⁴) = 1,1862 (Tada, Paris & Irwin, 2000, p. 2.2; nauwkeurig 0,1 %):
  K_I = 47,014 MPa·√m. G = K_I² (1 − ν²)/E = 9578,2 J/m².
- **Controles**: K_I (`CALC_G`) en G binnen 3 %; G/(K_I²/E') binnen 2 % (theta-methode
  tegen interactie-integraal); K_I (`POST_K1_K2_K3`) binnen 5 % (controlemethode);
  spreiding van K_I langs het front < 1 %; K_II < 1 % van K_I.

| Grootheid | Bridge | Referentie | Verschil |
|---|---|---|---|
| K_I `CALC_G` | 46,967 MPa·√m | 47,014 | −0,10 % |
| G `CALC_G` | 9539,0 J/m² | 9578,2 | −0,41 % |
| G/(K_I²/E') | 0,9979 | 1 | −0,21 % |
| K_I `POST_K1_K2_K3` | 45,376 MPa·√m | 47,014 | −3,5 % |
| spreiding K_I langs het front | 1,6e-5 | 0 | – |
| K_II | −1,5e-7 Pa·√m | 0 | – |

- **Interpretatie**: `CALC_G` is op dit mesh vrijwel exact; `POST_K1_K2_K3`
  (extrapolatie van de lipverplaatsing) is zonder kwartpuntelementen 3,5 % te laag. Met
  kwartpuntknopen (buiten de regressie: de middenknopen van de ribben vanaf het front
  op 1/4) werd het −0,1 %, `CALC_G` +0,02 %; een mesh-studie staat in
  [Breukmechanica.md](Breukmechanica.md) §3.

#### BR-02 Hetzelfde als half model met symmetrie (SYME='OUI')

- **Model**: BR-01 alleen voor y ≥ 0, *Symmetry* (DY = 0) op het ligament (x > a),
  alleen `SCHEUR_LIP_BOVEN`. 4549 knopen, 768 elementen.
- **Resultaat**: K_I, G, G/(K_I²/E') en K_I (`POST_K1_K2_K3`) gelijk aan BR-01 (op
  alle cijfers): Code-Aster rekent met `SYME='OUI'` K en G voor de hele scheur.

#### BR-03 Dikke plaat met vrije zijvlakken

- **Doel**: vlakke rek in het midden van een dikke plaat en het randeffect.
- **Model**: als BR-01 met dikte B = 4a = 0,2 m, half model in de dikte (symmetrie
  op het middenvlak z = 0, vrij oppervlak z = 0,1 m), 10 elementen over de halve dikte
  (verfijnd naar het oppervlak). 35 221 knopen, 7680 elementen.
- **Referentie**: in het midden van een dikke plaat geldt vlakke rek: K_I volgens Tada
  (zoals BR-01), tolerantie 3 %, ook op een afstand a van het oppervlak.

| Grootheid | Bridge | Referentie | Verschil |
|---|---|---|---|
| K_I `CALC_G` middenvlak | 47,337 MPa·√m | 47,014 | +0,69 % |
| G `CALC_G` middenvlak | 9690,4 J/m² | 9578,2 | +1,2 % |
| G/(K_I²/E') middenvlak | 0,9980 | 1 | −0,20 % |
| K_I `POST_K1_K2_K3` middenvlak | 45,706 MPa·√m | 47,014 | −2,8 % |
| K_I `CALC_G` op a van het oppervlak | 48,033 MPa·√m | 47,014 | +2,2 % |

- **Interpretatie**: in het middenvlak is de toestand vlakke rek (G/(K²/E') = 0,998). Naar
  het vrije oppervlak toe stijgt K_I tot +6 % (op 0,9 x de halve dikte) en daalt in de
  oppervlakteknoop zelf: daar is de singulariteit geen 1/√r meer en is K niet
  betrouwbaar ([Breukmechanica.md](Breukmechanica.md) §1.6).

#### BR-04 Code-Aster-testcase forma07a via de bridge

- **Model**: het mesh van forma07a (`share/aster/tests/forma07a.mmed`, Code-Aster
  17.4): schijfvormige scheur met straal a = 2 m in een blok, kwartmodel, hex20 en
  penta15 (wedge15 aan het front), met de kwartpuntknopen van de test
  (`MODI_MAILLAGE NOEUD_QUART`) al in de `.liml` (omgezet met Code-Aster, `IMPR_RESU
  FORMAT='ASTER'`). `LEV_SUP`/`LEV_INF`/`LFF` als `SCHEUR_LIP_BOVEN`/`_ONDER`/
  `SCHEUR_FRONT`; `FACE_AV`/`FACE_LAT` *frictionless*, knoop D DZ = 0; *traction* ±1 MPa
  op `FACE_SUP`/`FACE_INF`; E = 200 GPa, ν = 0,3; R_INF/R_SUP = 0,2/0,5 m zoals de test,
  met `#ASTER-OPTIE` ([ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md)
  voorbeeld 16). 5227 knopen, 1216 elementen. De bridge herkent het kwartcirkelfront en
  geeft `CALC_G` `FORM_FISS='CERCLE', RAYON=2.0`.
- **Referentie**: TEST_TABLE van forma07a: K1 MAX van `POST_K1_K2_K3` VALE_CALC
  1 607 011,55098 (NON_REGRESSION) en VALE_REFE 1,5957e6 (analytisch 2σ√(a/π),
  PRECISION 0,8 %); G_REF = 11,58648 J/m² uit de `.comm` van de test. De testcase zelf
  draait op deze installatie met `DIAGNOSTIC JOB : OK`.

| Grootheid | Bridge | Referentie | Verschil (tol.) |
|---|---|---|---|
| K1 MAX `POST_K1_K2_K3` | 1 607 011,551 | 1 607 011,55098 (VALE_CALC) | 1e-11 (1 %) |
| K1 MAX `POST_K1_K2_K3` | 1 607 011,551 | 1 595 700 (analytisch) | +0,71 % (0,8 %) |
| K_I `CALC_G` midden | 1 583 312 | 1 595 700 | −0,78 % (1 %) |
| G `CALC_G` midden | 11,684 J/m² | 11,586 | +0,84 % (1,5 %) |

- **Interpretatie**: de bridge bouwt forma07a exact na. Zonder krommingscorrectie gaf
  K uit `CALC_G` op dit front +5,6 % (gemeten bij de bouw), met `FORM_FISS` +0,1 %
  (R automatisch) en −0,8 % (R = 0,2/0,5 m).

#### BR-05 Middenscheur met lineaire elementen (hex8)

- **Model**: BR-01 met hex8 (`3D`, volledig geïntegreerd) en 8 elementen over de
  dikte. 7533 knopen, 6144 elementen.

| Grootheid | Bridge | Referentie | Verschil |
|---|---|---|---|
| K_I `CALC_G` | 46,700 MPa·√m | 47,014 | −0,67 % |
| G `CALC_G` | 9391,3 J/m² | 9578,2 | −1,95 % |
| G/(K_I²/E') | 0,9937 | 1 | −0,63 % |

- **Interpretatie**: ook met hex8 is `CALC_G` bruikbaar. `POST_K1_K2_K3` geeft met
  hex8 ~10 % te laag (geen controle). Met maar 2 elementen over de dikte (3
  frontknopen) oscilleerden G en K per knoop met `LINEAIRE` (§2.3 van
  [Breukmechanica.md](Breukmechanica.md); de bridge waarschuwt dan).

#### BR-06 Twee fronten als twee scheuren (achtervoegsel)

- **Model**: de plaat van BR-01 over de volle breedte x ∈ [−b, b] (geen symmetrie in
  x): de middenscheur heeft twee fronten, ingevoerd als twee scheuren
  `SCHEUR_FRONT_L`/`SCHEUR_LIP_BOVEN_L`/`SCHEUR_LIP_ONDER_L` (x < 0) en idem `_R`.
  Starre beweging vast met DX en DY op x = b, y = 0 en DY op x = −b, y = 0. 17 728
  knopen, 3072 elementen.
- **Resultaat**: per front K_I −0,10 % en G −0,41 % t.o.v. Tada, gelijk aan BR-01; de
  tabel heeft de scheuren `_L` en `_R`.

#### XFEM (BR-07 .. BR-14)

Mecway S30 zonder scheur in het mesh, met een `#ASTER-XFEM`-regel (BR-13: een
vlakselectie `XFEM_`) → `DEFI_FISS_XFEM`,
`MODI_MODELE_XFEM`, `MECA_STATIQUE`, `CALC_G_XFEM` `OPTION='CALC_K_G'` en
`POST_K1_K2_K3` `FISSURE=` ([Breukmechanica.md](Breukmechanica.md) §7). Module
`tests_breukmechanica_xfem.py`; de waarden komen uit `<model>_verif_xfem.csv`
(`bridge_fracture.read_csv`), "midden" is het frontpunt het dichtst bij de halve
frontlengte. Standaardinstellingen (R_INF/R_SUP automatisch, `glad` per vorm),
behalve BR-11. Tolerantie op K_I en G: 5 % (klaar-criterium S6b).

##### BR-07 Middenscheur in een plaat als HALFVLAK (hex8)

- **Model**: de plaat van BR-01 (a = 0,05 m, b = 0,1 m, H = 0,3 m, dikte 0,05 m,
  vlakke rek, σ = 100 MPa), half model in x, maar **zonder scheur in het mesh**:
  `#ASTER-XFEM vorm=HALFVLAK, front=(0.05, 0, 0), normaal=(0, 1, 0), richting=(1, 0,
  0)`. hex8, uniform h = a/20 = 2,5 mm rond het front, het scheurvlak y = 0 en het
  front x = a lopen midden door de elementen; 4 elementen over de dikte. 5280 knopen,
  3968 elementen.
- **Referentie**: Tada e.a. (2000) p. 2.2 zoals BR-01: K_I = 47,014 MPa·√m, G = 9578,2
  J/m²; symmetrie om y = 0 voor de opening van de lippen.

| Grootheid | Bridge | Referentie | Verschil (tol.) |
|---|---|---|---|
| K_I `CALC_G_XFEM` | 46,975 MPa·√m | 47,014 | −0,08 % (5 %) |
| G `CALC_G_XFEM` | 9561,2 J/m² | 9578,2 | −0,18 % (5 %) |
| K_I `POST_K1_K2_K3` | 46,903 MPa·√m | 47,014 | −0,24 % (5 %) |
| G/(K_I²/E') | 0,99991 | 1 | −0,01 % (2 %) |
| spreiding K_I langs het front | 0,0041 | 0 | (0,01) |
| opening bovenlip / onderlip in Mecway (x = 0) | −0,99993 | −1 | 0,01 % (1 %) |

- **Interpretatie**: XFEM met hex8 is op dit mesh even nauwkeurig als de gemeshte
  scheur met hex20 (BR-01). De laatste controle laat zien dat Mecway de fysische
  verplaatsing van elke lip krijgt (`POST_CHAM_XFEM` + `PROJ_CHAMP`), niet de
  XFEM-vrijheidsgraden.

##### BR-08 Idem met hex20

- **Model**: BR-07 met hex20. 19 739 knopen, 3968 elementen.
- **Resultaat**: K_I +0,10 %, G +0,17 %, `POST_K1_K2_K3` −0,13 %, G/(K_I²/E') 0,9997.
  Code-Aster 17.4 kent kwadratische XFEM-elementen (alarm `XFEM_63`: de levelset is op
  de kwadratische elementen bijgesteld).

##### BR-09 Scheurvlak door knopen, front op elementgrenzen (hex8)

- **Model**: BR-07 met een knooplaag op y = 0 en knopen op x = a (de levelsets zijn
  daar 0). 5115 knopen, 3840 elementen.
- **Resultaat**: K_I −0,06 %, G −0,05 %, `POST_K1_K2_K3` +1,1 %, G/(K_I²/E') 1,0008.

##### BR-10 Cirkelvormige scheur in een blok (penny crack)

- **Model**: kwartmodel van een blok 5a × 5a × 10a (a = 20 mm), symmetrie x = 0 en y = 0,
  trek σ = 1 MPa op z = ±5a; `#ASTER-XFEM vorm=CIRKEL, centrum=(0, 0, 0), r=20 mm,
  normaal=(0, 0, 1), naam=penny`. hex8, uniform h = a/20 tot r = 1,5a en |z| < 5,5h,
  het scheurvlak midden door de elementen; het front snijdt de elementen schuin. 48 672
  knopen, 44 764 elementen.
- **Referentie**: oneindig medium (Tada, Paris & Irwin, 2000, p. 24.2; Sneddon, 1946): K_I = 2σ√(a/π) =
  0,15958 MPa·√m; opening in het midden δ = 8(1 − ν²)σa/(πE) = 2,2069e-7 m (de knopen
  liggen op ±h/2, wat σh/E ≈ +2 % toevoegt; het blok is eindig).

| Grootheid | Bridge | Referentie | Verschil (tol.) |
|---|---|---|---|
| K_I `POST_K1_K2_K3` midden | 0,16219 MPa·√m | 0,15958 | +1,6 % (5 %) |
| K uit G: √(G E/(1 − ν²)) midden | 0,16112 MPa·√m | 0,15958 | +1,0 % (5 %) |
| K_I `CALC_G_XFEM` midden | 0,16797 MPa·√m | 0,15958 | +5,3 % (5 %; BEKEND, KNOWN_BUGS 83) |
| opening van de scheur (displz in Mecway) | 2,2796e-7 m | 2,2069e-7 | +3,3 % (5 %) |

- **Interpretatie**: `CALC_G_XFEM` heeft geen krommingscorrectie (anders dan `CALC_G`
  met `FORM_FISS='CERCLE'` bij de gemeshte scheur, BR-04); op een gekromd front is K
  uit `POST_K1_K2_K3` of uit G de waarde om te gebruiken (de bridge waarschuwt). Een
  mesh-studie (h = a/10, a/5) staat in [Breukmechanica.md](Breukmechanica.md) §7.4.
  De controle op K_I uit `CALC_G_XFEM` heeft dezelfde tolerantie van 5 % als de andere
  XFEM-controles en staat als BEKEND (KNOWN_BUGS 83): een ruimere tolerantie is niet
  te onderbouwen met de discretisatiefout, want de afwijking daalt met het mesh (+15 /
  +10 / +5,3 % bij h = a/5, a/10, a/20) maar is een tekortkoming van de methode op een
  gekromd front, niet van de vertaling.

##### BR-11 Code-Aster-testcase forma07b via de bridge

- **Model**: het mesh van forma07b (`forma07b.41`, Code-Aster 17.4: met HOMARD rond
  het front verfijnd, hex8 + pyram5 + tetra4), omgezet naar een `.liml` (`IMPR_RESU
  FORMAT='ASTER'`): schijfvormige scheur met straal 2 m in een kwartblok 10 × 10 × 20 m
  als `#ASTER-XFEM vorm=ELLIPSE, centrum=(0, 0, 0), a=2, b=2, vect_x=(1, 0, 0),
  vect_y=(0, 1, 0), glad=LAGRANGE, punten=20`; `FACE_AV`/`FACE_LAT` *Symmetry*, knoop D
  DZ = 0, druk −1 MPa op `FACE_SUP`/`FACE_INF`; E = 200 GPa, ν = 0,3; R_INF/R_SUP =
  2h/5h (h = 0,078 m) met `#ASTER-OPTIE`, zoals forma07b.com2. 22 365 knopen, 33 466
  elementen.
- **Referentie**: TEST_TABLE van forma07b.com2: K1 MAX van `CALC_G_XFEM` (LAGRANGE,
  `NB_POINT_FOND=20`) VALE_CALC 1 671 075,88 en van `POST_K1_K2_K3`
  (`NB_POINT_FOND=20`, `ABSC_CURV_MAXI=R_SUP`) VALE_CALC 1 607 458,57
  (NON_REGRESSION), VALE_REFE 1,5957e6 (analytisch 2σ√(a/π), PRECISION 1 %).

| Grootheid | Bridge | Referentie | Verschil (tol.) |
|---|---|---|---|
| K1 MAX `CALC_G_XFEM` | 1 671 075,9 | 1 671 075,88 (VALE_CALC) | < 1e-6 (1 %) |
| K1 MAX `POST_K1_K2_K3` | 1 607 458,6 | 1 607 458,57 (VALE_CALC) | < 1e-6 (1 %) |
| K1 MAX `POST_K1_K2_K3` | 1 607 458,6 | 1 595 700 (analytisch) | +0,74 % (1 %) |

- **Interpretatie**: de bridge bouwt forma07b exact na. Bij de bouw gaf de *Symmetry*
  als `LIAISON_OBLIQUE` (zoals zonder XFEM) K1 MAX +0,3 % (`CALC_G_XFEM`) en +3,8 %
  (`POST_K1_K2_K3`): de maxima liggen aan de symmetrievlakken, waar `LIAISON_OBLIQUE`
  de XFEM-vrijheidsgraden niet vastlegt. Met XFEM maakt de bridge er nu `DDL_IMPO` van.

##### BR-12 Middenscheur over de volle breedte als RECHTHOEK (twee fronten)

- **Model**: de plaat van BR-07 over de volle breedte x ∈ [−b, b] (zoals BR-06),
  `#ASTER-XFEM vorm=RECHTHOEK, centrum=(0, 0, 0.025), a=0.05, b=0.05, vect_x=(1, 0, 0),
  vect_y=(0, 0, 1)`: de rechthoek steekt in z buiten de plaat, dus twee rechte fronten
  (`NUME_FOND` 1 en 2). 10 400 knopen, 7936 elementen.
- **Resultaat**: front 1 K_I −0,09 %, G −0,19 %, `POST_K1_K2_K3` −0,29 %; front 2 K_I
  −0,09 %, G −0,18 %, `POST_K1_K2_K3` −0,24 % (tolerantie 5 %); de tabel heeft de
  fronten 1 en 2.

##### BR-13 Scheur uit een vlakselectie (XFEM_), scheurvlak op een knooplaag (hex8)

- **Model**: het mesh van BR-09 (knooplaag op y = 0, knopen op x = a) zonder
  `#ASTER-XFEM`-regel; de scheur is de vlakselectie `XFEM_midden`: de vlakken op y = 0
  voor x < a, afwisselend van het element eronder en erboven gekozen (de bridge moet de
  normalen gelijk richten). `DEFI_FISS` `GROUP_MA_FISS`/`GROUP_MA_FOND` met de cellen
  van `bridge_xfem.mesh_cells` ([Breukmechanica.md](Breukmechanica.md) §7.8). 5115
  knopen, 3840 elementen.
- **Referentie**: Tada e.a. (2000) p. 2.2 zoals BR-07; symmetrie om y = 0 voor de
  opening (knooplagen y = ±h, want de knopen op y = 0 krijgen de waarde van één lip).

| Grootheid | Bridge | Referentie | Verschil (tol.) |
|---|---|---|---|
| K_I `CALC_G_XFEM` | 46,985 MPa·√m | 47,014 | −0,06 % (5 %) |
| G `CALC_G_XFEM` | 9573,5 J/m² | 9578,2 | −0,05 % (5 %) |
| K_I `POST_K1_K2_K3` | 47,548 MPa·√m | 47,014 | +1,1 % (5 %) |
| G/(K_I²/E') | 1,0008 | 1 | +0,08 % (2 %) |
| opening bovenlip / onderlip in Mecway (x = 0, y = ±h) | −1,0004 | −1 | 0,04 % (1 %) |

- **Interpretatie**: gelijk aan BR-09 (dezelfde scheur als `HALFVLAK`) in alle cijfers;
  de levelsets LNNO/LTNO van beide zijn gelijk (bij de bouw met `CREA_CHAMP` vergeleken).
  Bij de bouw gaf de tegengestelde normaal van het scheurvlak K gelijk binnen 0,05 %,
  maar een bovenlip die 1,8 % verder openging; de bridge kiest de normaal daarom vast
  (grootste component positief).

##### BR-14 MED-bestand voor ParaView met het mesh dat de scheur volgt

- **Model**: BR-07 met de instelling `med_export` (*MED-bestand voor ParaView*). 5280
  knopen, 3968 elementen.
- **Controle**: `<model>_verif_xfem.rmed` teruggelezen met de MEDCoupling van de
  Code-Aster-installatie (Python 3.11 van Code-Aster): de velden `DEPL`, `SIGM_NOEU` en
  `SIEQ_NOEU` (`res_xvis...`) en de groep `Plaat` staan erin; de opening tussen de
  lipknopen op (0, 0, a/2) (`POST_MAIL_XFEM` geeft elke lip eigen knopen) gedeeld door
  de opening die Mecway tussen de knopen op y = ±h/2 krijgt: 0,996 (referentie 1,
  tolerantie 3 %: de knopen van Mecway liggen h/2 van het scheurvlak, σh/E ≈ 1 %).

Buiten de regressie (bij de bouw): BR-07 met `elem_hex8` = `LINE_QUAD` K_I 0,0 %,
`POST_K1_K2_K3` −0,1 %.

#### Conclusie breukmechanica

Alle 6 cases (26 controles) liggen binnen de tolerantie: K_I uit `CALC_G` binnen 0,8 %
van Tada en van forma07a, G binnen 2 %, G en K_I²/E' consistent binnen 0,7 %, en de
dubbele knopen op de lippen, het halve model, meer scheuren met een achtervoegsel, een
krom front en `#ASTER-OPTIE` werken.
XFEM (8 cases, 37 controles): K_I en G op een recht front binnen 0,2 % van Tada met
hex8 en hex20, ook met het front en het scheurvlak door elementen of door knopen, met
twee fronten en met de scheur uit een vlakselectie `XFEM_` (BR-13, gelijk aan BR-09);
het MED-bestand `_xfem.rmed` voor ParaView heeft de velden op het mesh dat de scheur
volgt (BR-14); de penny crack binnen 1,6 % (`POST_K1_K2_K3`, K uit G), `CALC_G_XFEM`
+5,3 % (geen krommingscorrectie; BEKEND, KNOWN_BUGS 83); forma07b exact nagebouwd; Mecway krijgt de fysische
verplaatsing per lip (opening +3,3 % t.o.v. Sneddon). Niet gedekt bij XFEM: tet10,
wedge15, pyr13, `groep=`, een ELLIPSE met a ≠ b, reacties op knopen van gesneden
elementen (KNOWN_BUGS 63).
Niet gedekt: een gesloten front, tet10, een grensvlak tussen materialen, thermische
rek, druk op de lippen (KNOWN_BUGS 63); de werkwijze in de Mecway-GUI (*Disconnect
elements*) is NIET nagelopen.

### Adaptieve verfijning (AD)

Mecway S30 → `lin_static_3d` met `adapt_refine` aan → na elke run kiest
`bridge_adapt.after_run` de elementen (standaard met het criterium van Dörfler, 1996) en verfijnt `bridge_adapt.refine_in_mecway`
ze in Mecway ([Foutschatter.md](Foutschatter.md) §6). Module `tests_adaptief.py`,
draaien met `python run_verificatie.py AD`. De lus van het hoofdscript draait offline
met dezelfde functies: de bridge en Code-Aster zoals in elke case, de verfijning in
**headless Mecway** (`mecway.exe <model> script <script.py>`, met
`bridge_adapt.refine_in_mecway(mw, ...)`). De tussenmodellen staan als
`TestFiles/Verificatie/modellen/AD-02-L0.liml` … `AD-02-L5.liml` (in Mecway te
openen). Is headless Mecway er niet (`mecway.exe` niet gevonden of de verfijning
mislukt), dan valt de lus terug op die opgeslagen modellen; de controle "lus met
Mecway gedraaid" (fractie van de verfijningsstappen die Mecway echt deed, referentie
1, tolerantie 0) is dan NOK, zodat AD-02 nooit stil op oude modellen slaagt.

- **Model**: kwart plaat met een rond gat (r = 10 mm) onder trek 100 MPa, breedte W =
  100 mm (d/W = 0,2), lengte 300 mm, hex20; een plak van 10 mm met symmetrie op beide
  z-vlakken (vlakke rek). Vlakke rek en vlakke spanning geven dezelfde Kt (de spanningen
  van een vlak probleem met randlasten hangen niet af van ν); nagerekend met dezelfde
  plaat 1 mm dik in vlakke spanning: n = 32 −0,08%.
- **Referentie**: Kt_n = σ_xx(0, r) / σ_nom met σ_nom = σ W/(W − d); Peterson (Pilkey &
  Pilkey, 2008, chart 4.1): 2 + 0,284(1 − d/W) − 0,600(1 − d/W)² + 1,32(1 − d/W)³ =
  2,519; ter controle Heywood (1952) 2 + (1 − d/W)³ = 2,512 en Roark (Young & Budynas, 2002, tabel 17.1, geval 2a)
  2,508. Klaar-criterium S7: Kt binnen 2% na de lus, met minder elementen dan uniform
  verfijnen.

| ID | Model | Resultaat |
|---|---|---|
| AD-01-n1 … n32 | uniform: 2n × 2n hex20 per blok, 1 laag (12·4^k elementen) | Kt −27,2 / −14,3 / −6,34 / −2,47 / −0,75 / −0,14% (n = 1 … 32); binnen 2% vanaf n = 16 |
| AD-02 | de lus: grof mesh (12 hex20), doel 1,5%, Dörfler 0,5, max. 6 lussen | 5 lussen, alle 5 verfijningen door headless Mecway (fractie 1); Kt +0,82% met 15 810 elementen; uniform Refine x2 tot 2%: 49 152 (factor 0,32); globale fout daalt elke lus; 98% van de verfijnde elementen binnen 3r van het gat |
| AD-03 | balk hex20 met fixed op een knoopselectie | de lus stopt met een ERROR vóór het verfijnen |

Per lus (AD-02):

| Lus | Elementen | Knopen | Globale fout | Kt_n | t.o.v. Peterson | Verfijnd |
|---|---|---|---|---|---|---|
| 0 | 12 | 127 | 4,57% | 1,834 | −27,2% | 2 |
| 1 | 88 | 424 | 3,60% | 1,872 | −25,7% | 7 |
| 2 | 422 | 1 408 | 2,92% | 2,202 | −12,6% | 21 |
| 3 | 1 666 | 4 306 | 2,40% | 2,385 | −5,33% | 60 |
| 4 | 5 088 | 12 464 | 1,81% | 2,370 | −5,93% | 162 |
| 5 | 15 810 | 35 233 | 1,11% | 2,540 | +0,82% | – (doel bereikt) |

Verdere controles in AD-02: √(Σ η_e²) uit het resultaatbestand = de globale η uit de
`.mess` (≤ 1e-3; de lus leest de goede elementwaarden); σ_xx aan het eindvlak 100 MPa
(+0,01%: de traction op de vlakselectie gaat mee met de verfijning). Alle meshes zijn
conform (elk binnenvlak bij twee elementen).

Waarnemingen:
- Mecway's Refine x2 op alles verdeelt ook de dikte; Kt verandert daar niet door
  (vlakke rek), dus uniform verfijnen kost 12·8^k elementen voor dezelfde Kt als AD-01:
  49 152 voor binnen 2% (n = 16). De lus haalt dat met 15 810 (+0,82%).
- De lus verfijnt in stappen: Kt verbetert pas als de elementen op de piek aan de
  beurt zijn (lus 3 → 4 iets slechter, −5,3 → −5,9%); de globale fout daalt elke lus
  (verhouding ≤ 0,82).
- Buiten de regressie gemeten (zelfde plaat, [Foutschatter.md](Foutschatter.md) §6.5):
  een dunne plaat (dikte 1/40 van de elementbreedte) gaf in lus 2 bijna platte hex20
  en een stijgende schatting (3,7 → 19,6%): de lus stopt met een WARNING; tet10 stopte
  na de eerste lus; met een bufferlaag (*Ook de buren verfijnen*) haalde de dikke plaat
  Kt binnen 2% pas bij 22 956 elementen.
- Een Code-Aster-fout in de schatter gevonden en omzeild: `FORCE_FACE` telt in `ERME`
  met het omgekeerde teken (blok onder uniforme trek: 15% i.p.v. 0); zonder de
  correctie koos de lus in de eerste lus de elementen aan het belaste eindvlak
  ([Foutschatter.md](Foutschatter.md) §2.3).
- De Mecway-GUI zelf (de lus met het wachten op Code-Aster per lus) is NIET nagelopen; headless is de stap van
  het hoofdscript wel nagelopen op een model met resultaten: `after_run` in Mecway's
  IronPython, `solution.element_node_value("errorestimate", 1, 1)` = de waarde uit het
  resultaatbestand (11963,69), `refine_x2` en `save_as` met een oplossing in het model.

### Vermoeiing (VM)

Wöhler-curve per materiaal (`#ASTER-WOHLER`), rainflow en Miner op blokken of een
signaal bij lineair statisch (`#ASTER-BLOK`, `#ASTER-SIGNAAL`) en op de tijdstappen van
`STAT_NON_LINE`/`DYNA_NON_LINE` ([Vermoeiing.md](Vermoeiing.md); `bridge_fatigue.py`,
job-module `aster_fatigue.py`). Module `tests_vermoeiing.py`, draaien met
`python run_verificatie.py VM`. Gelezen worden de velden `damage` en `life` van de
`.liml`-route en de cyclustabel `<model>_verif_vermoeiing.csv`.

- **Model (alle cases)**: staaf 0,1 × 0,01 × 0,01 m, 2 hex8 (VM-06: een kubus van
  0,01 m, 1 hex8), E = 210 GPa, ν = 0,3, symmetrievlakken x = 0, y = 0, z = 0 (knoop-
  verplaatsing 0 in de normaal) en een traction op x = L (VM-07 ook op y = A):
  eenassige, homogene spanning σ_xx = traction in elke knoop, dus de schade is in elke
  knoop gelijk (de checks eisen dat binnen 10⁻⁹).
- **Referenties**: Miner (D = Σ n/N) met de opgegeven curve, met de hand in de
  testmodule (los van de bridge); ASTM E1049-85 fig. 6 (rainflow); Code-Aster-testcases
  szlz100a (`POST_FATIGUE`, `VALE_REFE`) en szlz105a (`CALC_FATIGUE`, `VALE_REFE`);
  Code-Aster's eigen `POST_FATIGUE`/`CALC_FATIGUE` in dezelfde job (`#ASTER-POST`, regel
  `VERIF_CA_D` in de `.mess`).

| Case | Invoer | Grootheid | Bridge | Referentie | Verschil | Tolerantie |
|---|---|---|---|---|---|---|
| VM-01a | tabel S = [100, 150, 250, 400] MPa, N = [10⁷, 2·10⁶, 2·10⁵, 10⁴]; σ = 100 MPa, `#ASTER-BLOK 2.0, 0, 1e4` (S_a = 200 MPa) | D / life | 0,0182869 / 54,684 | Miner, log-log | 0 / 2·10⁻¹⁴ | 0,1 % |
| VM-01b | Basquin Sf = 900 MPa, b = −0,1; S_a = 150 MPa, 1000 cycli | D | 3,3076·10⁻⁵ | ½(S/Sf)^(1/b) | 7·10⁻¹⁵ | 0,1 % |
| VM-01c | macht S = 40 MPa, N = 2·10⁶, m = 3, Se = 25 MPa; 5·10⁴ cycli op 60 MPa + 10⁹ op 20 MPa (< Se) | D | 0,084375 | 5·10⁴/(2·10⁶ (40/60)³) | 4·10⁻¹⁵ | 0,1 % |
| VM-02a | tabel; 10⁵ cycli op 120 MPa + 5·10³ op 300 MPa | D | 0,100536 | Miner, twee blokken | 6·10⁻¹⁶ | 0,1 % |
| VM-02b | Basquin + Goodman (Su = 600 MPa), blokken (1,5; 0,5; 10⁴) en (0,8; 1,0; 2·10⁵), 5 herhalingen | D / life | 4,32931·10⁻³ / 1154,92 | Goodman, Miner × 5 | 1·10⁻¹⁴ / 6·10⁻¹⁴ | 0,1 % |
| VM-03a | ASTM-signaal −2, 1, −3, 5, −1, 3, −4, 4, −2 × 55 MPa, `telling = ASTM` | cycli per bereik 3/4/6/8/9 | 0,5/1,5/0,5/1/0,5 | ASTM E1049 fig. 6 | exact | 10⁻¹² |
| VM-03a | idem | D | 5,8025·10⁻⁶ | Miner op de ASTM-cycli | 1·10⁻¹⁴ | 0,1 % |
| VM-03b | idem, `RAINFLOW` (standaard), signaal over twee regels | aantal cycli; D; D/`POST_FATIGUE` | 4; 6,4638·10⁻⁶; 1 | 4 gesloten cycli; Miner; `POST_FATIGUE RAINFLOW` | exact; 1·10⁻¹⁴; 2·10⁻¹⁴ | 10⁻¹²; 0,1 %; 10⁻⁶ |
| VM-04 | szlz105a: traction 0, 3, 1, 4, 2, 4, 1, 2, −3 MPa (t = 0..8 s), niet-lineair statisch (`PETIT`), N = 1000 − 100 S (`INTERPOL = LIN`) | D; D/`CALC_FATIGUE` | 4,81332·10⁻³; 1 | szlz105a `VALE_REFE` 4,8133·10⁻³; `CALC_FATIGUE CUMUL_DOMMAGE` op `res` | 3·10⁻⁶ (afronding van `VALE_REFE`); 0 | 1 %; 10⁻⁶ |
| VM-05a/b/c | szlz100a: signaal 50, 600, 50, −500, 50 MPa, tabel WHOL (`PROL_GAUCHE = LINEAIRE`), Su = 850 MPa: geen correctie / Gerber / Goodman | D | 1,05326·10⁻³ / 1,06363·10⁻³ / 1,25022·10⁻³ | szlz100a `VALE_REFE` (TAB_1, TAB_3, TAB_4) | 5·10⁻⁸ / 1·10⁻⁸ / 8·10⁻⁹ | 1 % |
| VM-06 | dynamisch (`dyna_impl_3d`, HHT), traction 0 → 300 → −150 → 250 → −50 → 0 MPa in 10 ms, 101 uitvoertijden | D/`CALC_FATIGUE` | 1 | `CALC_FATIGUE CUMUL_DOMMAGE` (`DOMA_ELNO_SIGM`) op `res` | 2·10⁻⁸ (single precision) | 10⁻⁶ |
| VM-07a | σ_xx = 100, σ_yy = −150 MPa, Basquin, `spanning = VMIS_SG` | D | 1,38699·10⁻³ | S = √(σx² + σy² − σxσy) = 217,9 MPa | 1·10⁻¹⁵ | 0,1 % |
| VM-07b | idem, `spanning = PRIN` | D | 3,3076·10⁻⁵ | S = \|σ_yy\| = 150 MPa | 2·10⁻¹⁴ | 0,1 % |

- **Interpretatie**: de bridge is op machineprecisie gelijk aan de handberekening, aan
  ASTM E1049 en aan Code-Aster's eigen `POST_FATIGUE` en `CALC_FATIGUE`; de verschillen
  met `VALE_REFE` van szlz100a/szlz105a zijn de afronding van die waarden. Bij de bouw
  gemeten (geen controle in de regressie): Code-Aster's `POST_FATIGUE`/`CALC_FATIGUE`
  trekt `PROL_*='LINEAIRE'` lineair in (S, N) door, ook bij `INTERPOL='LOG'` (een
  kleine cyclus gaf in een eerste versie van VM-06 met `PROL_GAUCHE='LINEAIRE'`
  3,85·10⁻⁸ extra schade in `CALC_FATIGUE`, = 1/N(0) met N(0) = 2,6·10⁷ lineair
  doorgetrokken); de bridge trekt log-log door ([Vermoeiing.md](Vermoeiing.md) §3).
- **Mecway**: geen vermoeiing, dus geen vergelijking met een Mecway-oplossing. Mecway's
  API leest `damage` en `life` uit de resultaten van VM-01a (statisch) en VM-06 (101
  tijdstappen, in elke stap dezelfde waarde) (headless `mecway.exe <model> script`:
  `node_value` gelijk aan de bridge); de GUI-weergave is NIET bekeken (KNOWN_BUGS 66).

#### Multiaxiaal, schalen en Manson-Coffin (VM-08 .. VM-11, S8b)

Multiaxiaal: `#ASTER-VERMOEIING criterium = DANG_VAN|MATAKE|CROSSLAND` met
`CALC_FATIGUE FATIGUE_MULTI DOMA_NOEUD` (kritiek vlak in Code-Aster, N uit SIGEQ met de
curve van de bridge); schalen: de uniaxiale route op `res_sup`/`res_inf`
(`damage_top`/`damage_bottom`); rek: Manson-Coffin op `EPSI_NOEU`
([Vermoeiing.md](Vermoeiing.md) §1.7–1.9).

- **Modellen**: VM-08: de kubus van sslv135a (10 mm, 1 hex8, E = 200 GPa, ν = 0,3),
  symmetrievlakken en tractions op x = L en y = A met het verloop van sslv135a (σ_xx =
  0, +100, 0, −100, 0 en σ_yy = 0, −200, 0, +200, 0 MPa op t = 0..4 s, stap 0,5 s),
  niet-lineair statisch (`PETIT`), Wöhler-tabel WHOL van sslv135a (`PROL_GAUCHE =
  LINEAIRE`), a = 1, c = 1,5; VM-08d alleen de ramp 0 → t = 1. VM-09: kubus 10 mm, 2 × 2
  × 2 hex8, 3-2-1-opleggingen en tractions op vier vlakken: homogeen σ_xx = 120, τ_xy =
  80 MPa (trek + afschuiving, proportioneel), lineair statisch met `#ASTER-SIGNAAL 0, 1,
  0, −1, 0` of twee blokken, tabel T1 of Basquin, a = 0,3, b = 110 MPa, c = 1,5. VM-10:
  vrije plaat 100 × 20 × 2 mm, 10 × 2 DKT quad4, consistente knoopmomenten m = σ t²/6
  (m h/2 op de hoeken, m h in het midden) op beide uiteinden, 3-2-1-opleggingen: zuivere
  buiging σ = ±150 MPa; Basquin + Goodman (Su = 600 MPa), `#ASTER-BLOK 0.5, 0.5, 1e5`.
  VM-11a: staaf van VM-01 met opgelegde verlenging 0, +0,6, −0,6, 0 mm (t = 0..3 s, stap
  0,25 s), bilineair plastisch (vloeigrens 250 MPa, H = 10 GPa), `PETIT`; VM-11b:
  elastisch, σ = 100 MPa, `#ASTER-SIGNAAL 0, 2, -2, 0`, `rek = VMIS_SG`. Curve VM-11:
  Sf = 900 MPa, b = −0,09, ef = 0,3, c = −0,55, E = 210 GPa.
- **Referenties**: sslv135a `VALE_REFE` (knoop N1, `DOMA_NOEUD`): Matake SIGEQ1 = 300 MPa,
  NBRUP1 = 10946, ENDO1 = 9,1356·10⁻⁵; Dang Van 275 MPa, 14903, 6,7100·10⁻⁵. Met de hand
  (in de testmodule): Mohr R = √((σ/2)² + τ²) = 100 MPa, P_max = σ/3 = 40 MPa, N_max =
  σ/2 = 60 MPa, √J₂ = √(σ²/3 + τ²) = 105,83 MPa; Dang Van c (R + a P_max) = 168 MPa,
  Matake c (R + a N_max) = 177 MPa, Crossland c (√J₂ + a P_max) = 176,75 MPa; blok 0..1
  van Dang Van: c (R/2 + a P_max) = 93 MPa. Plaat σ = 6m/t²; Goodman boven S_eq = 75/(1
  − 75/600), onder 75/(1 + 75/600) MPa. Manson-Coffin: N met Newton in ln 2N uit ε_a =
  Sf/E (2N)^b + ef (2N)^c, ε_a = u/L = 0,006 (VM-11a) en ε_eq = 2/3 (1 + ν) · 2σ/E
  (VM-11b).

| Case | Grootheid | Bridge | Referentie | Verschil | Tolerantie |
|---|---|---|---|---|---|
| VM-08a (Matake) | SIGEQ / life / D | 300,0 MPa / 10946,1 / 9,13565·10⁻⁵ | sslv135a 300 / 10946 / 9,13565·10⁻⁵ | 8·10⁻¹⁶ / 1,2·10⁻⁵ (afronding NBRUP1) / 1·10⁻¹⁴ | 1 % |
| VM-08b (Dang Van) | SIGEQ / life / D | 275,0 MPa / 14903,2 / 6,70996·10⁻⁵ | sslv135a 275 / 14903 / 6,70996·10⁻⁵ | 6·10⁻¹⁶ / 1,5·10⁻⁵ / 4·10⁻¹⁵ | 1 % |
| VM-08c (Dang Van, niet-periodiek) | D | 6,70996·10⁻⁵ | 1/N(275 MPa), één cyclus | 4·10⁻¹⁵ | 1 % |
| VM-08d (ramp 0 → 1, Matake) | SIGEQ | 112,5 MPa | 1,5 · 150/2 (N_max < 0); zonder kopie 56,25 MPa | 0 | 10⁻⁶ |
| VM-09a (Dang Van, signaal) | SIGEQ / (τ_a + aP)/b / D | 167,9996 MPa / 1,01818 / 8,3333·10⁻⁷ | 168 / 1,01818 / 8,3334·10⁻⁷ | −2,3·10⁻⁶ / −2,3·10⁻⁶ / −1,0·10⁻⁵ | 0,1 % |
| VM-09b (Dang Van, twee blokken, Basquin) | SIGEQ / D | 167,9996 MPa / 1,30488·10⁻⁵ | 168 / 1,30491·10⁻⁵ | −2,3·10⁻⁶ / −2,3·10⁻⁵ | 0,1 % |
| VM-09c (Matake) | SIGEQ / ratio / D | 177,10 MPa / 1,0733 / 1,0571·10⁻⁶ | 177 / 1,0727 / 1,0543·10⁻⁶ | 5,8·10⁻⁴ / 5,8·10⁻⁴ / 2,6·10⁻³ | 1 % |
| VM-09d (Crossland) | SIGEQ / ratio / D | 176,745 MPa / 1,07118 / 1,04752·10⁻⁶ | idem | 3·10⁻¹⁵ / 3·10⁻¹⁵ / 2·10⁻¹⁴ | 0,1 % |
| VM-10 (schaal, buiging) | σ boven / D boven / D onder / D | 150,0 MPa / 1,22783·10⁻⁵ / 9,9470·10⁻⁷ / 1,22783·10⁻⁵ | 6m/t² / Goodman, Basquin | 7·10⁻¹³ / 8·10⁻¹² / 6·10⁻¹² / 8·10⁻¹² | 0,1 % |
| VM-11a (Manson-Coffin, plastisch) | rekamplitude / D | 0,006000 / 7,42636·10⁻⁴ | u/L / 1/N, N = 1346,6 | 0 / 1,6·10⁻⁹ | 10⁻⁶ / 0,1 % |
| VM-11b (Manson-Coffin, `VMIS_SG`) | D | 1,92211·10⁻⁸ | 1/N(ε_eq) | 0 | 0,1 % |

- **Interpretatie**: SIGEQ van Code-Aster volgt de formules c (Δτ/2 + a max(P_max, 0))
  (Dang Van), c (Δτ/2 + a max(N_max, 0)) (Matake) en c (√J₂,a + a max(P_max, 0))
  (Crossland, via `AMPCIS`); de bridge zet SIGEQ op de eigen Wöhler-curve, gelijk aan
  sslv135a. De kleine afwijkingen bij Dang Van (−2·10⁻⁶) en Matake (+6·10⁻⁴) komen van
  de zoekrichting van het kritieke vlak in Code-Aster (een raster van normalen): bij
  Dang Van telt een kleine hoekfout kwadratisch (Δτ is maximaal), bij Matake lineair
  (N_max verandert met de hoek); Crossland is vlakonafhankelijk en exact. De schaal
  volgt de plaattheorie exact (DKT met consistente randmomenten, anticlastisch vrij);
  boven en onder verschillen alleen door het teken van het gemiddelde (Goodman). De
  rek is bij de verplaatsingsgestuurde staaf exact u/L, ook met plasticiteit.
- **Bij de bouw gemeten** (geen controle in de regressie): `CALC_FATIGUE
  FATIGUE_MULTI` slaat `NUME_ORDRE` 0 van `STAT_NON_LINE` over (alarm `PREPOST4_27`; de
  bridge kopieert daarom, VM-08d); `DOMA_NOEUD` zonder `EPSI_NOEU` geeft
  `<EXCEPTION> CALCULEL_29`; `D_VAN_B`/`MATAKE_B` tellen niet mee in SIGEQ; onder de
  tabel met `EXCLU` geeft Code-Aster `NBRUP1` = 0 en `ENDO1` ≈ 10⁻³⁰⁸; `PERIODIQUE`
  telt één cyclus per verloop (twee periodes: dezelfde schade), `NON_PERIODIQUE` twee;
  `MATAKE_MODI_AV` kiest een ander vlak dan `MATAKE_MODI_AC` (schade 3,5·10⁻⁴ i.p.v.
  9,1·10⁻⁵ op sslv135a); `EPSI_NOEU` is ook met `GDEF_LOG` de lineaire rek (0,0060000
  bij u/L = 0,006); met `GDEF_LOG` convergeerde het terugbelasten van VM-11a niet
  (KNOWN_BUGS 82). Rooktests buiten de regressie: Dang Van in een dynamische run
  (`dyna_impl_3d`, diagnose OK) en een model met een volume en een schaal (beide
  schade, diagnose OK).

#### Conclusie vermoeiing

Alle 25 cases (52 controles) liggen binnen de tolerantie. VM-01..07 (S8), met
verschillen van machineprecisie: constante amplitude (tabel, Basquin, machtsvorm met
Se) en een twee-niveau-spectrum (met Goodman en herhalingen) volgens Miner, de
rainflow-cycli van ASTM E1049 exact, periodieke rainflow en de schade gelijk aan
`POST_FATIGUE` en `CALC_FATIGUE` (statisch, niet-lineair statisch en dynamisch), en
szlz100a/szlz105a in 3D. VM-08..11 (S8b): sslv135a in 3D gelijk aan `VALE_REFE`
(Matake, Dang Van, periodiek en niet-periodiek), de kritiekvlakcriteria met de hand
nagerekend bij trek + afschuiving (Dang Van en Crossland ≤ 2·10⁻⁵; Matake 0,26 % door
het zoekraster van Code-Aster, tolerantie 1 %), de schaal onder zuivere buiging op de
boven- en onderzijde en Manson-Coffin (plastisch en elastisch) op machineprecisie. Niet
gedekt: balken, multiaxiaal op schalen en per Gauss-punt, een niet-proportionele
belasting met een analytische referentie, een niet-homogeen spanningsveld met een
analytische referentie, `dyna_expl_3d` (zelfde code als `dyna_impl_3d`) en de
Mecway-GUI.

## 5. Niet-lineair statisch (NL)

Mecway L30 → bridge `nonlin_static_3d` → `STAT_NON_LINE`. Module
`tests_niet_lineair.py`, draaien met `python run_verificatie.py NL`. Standaard-
instellingen: `deformation` = `GROT_GDEP`, door de bridge per element omgezet naar
`GDEF_LOG` (plastische volumes), `GREEN_LAGRANGE` (elastische volumes) en `GROT_GDEP`
(`COQUE_3D`); `convergence_resi_rela` = 1e-5 (de standaard van de bridge; de
Code-Aster-standaard 1e-6 stagneert bij NL-01, zie daar); de rekenstappen zijn Mecway's
*Time step size* (0,1 s, zoals de samples) plus de knikken van de lasttabellen (NL-20).

### NL-01 Trekstaaf, bilineaire isotrope versteviging, ontlasten

- **Doel**: bilineaire plasticiteit (`BilinearIsotropic`), grote rekken (`GDEF_LOG`) en
  elastisch ontlasten.
- **Model**: staaf 100 × 10 × 10 mm, 2 × 1 × 1 hex20; E = 210 GPa, ν = 0,3,
  σy = 355 MPa, *tangent modulus* H = 10 GPa.
- **Randvoorwaarden en belasting**: symmetrievlakken x = 0, y = 0, z = 0
  (dwarscontractie vrij); opgelegde verlenging op x = L: 0 → 0,10 mm (t = 1 s,
  elastisch) → 1,00 mm (t = 2 s, plastisch) → 0,85 mm (t = 3 s, ontlasten).
- **Referentie**: homogene eenassige toestand, exact uit te rekenen. Met `GDEF_LOG`
  (additieve logaritmische rek; de duale spanning is bij eenassige trek zonder rotatie
  de Kirchhoff-spanning τ): τ = σy + H·p, p = ln(1+e) − τ/E, ontlasten elastisch;
  F = A0·τ/(1+e), σ = τ/J met J = exp((1−2ν)τ/E). Tolerantie 0,2% (elk element is
  exact; over blijven de Newton-tolerantie en J − 1 < 0,1%).
- **Resultaat**: F, σ_xx en p op t = 1; 1,5; 2 en 3 s (na ontlasten: F = 12 071 N):
  0,00% af, met de standaardinstellingen. NL-01b (zelfde model met de
  Code-Aster-standaard `convergence_resi_rela` = 1e-6, `convergence_criterion` =
  `RELA_OF_MAXI` en `convergence_resi_maxi` = 0,05 N) rekent ook door tot t = 3 s,
  0,00% af.
- **Interpretatie**:
  1. *Tangent modulus*. Mecway's *tangent modulus* is de plastische modulus H (spanning
     tegen plastische rek), geen helling in totale rek. Doorslaggevend (Mecway/CCX
     headless, *tangent modulus* 100 GPa, 1% rek): CCX 915,8 MPa, gelezen als H
     914,5 MPa, gelezen als helling in totale rek 1181 MPa. De bridge geeft Code-Aster nu
     `D_SIGM_EPSI` = E·H/(E+H) (helling in totale rek; EDF R&D, U4.43.01); vóór die
     correctie was de piekkracht 0,87% te hoog.
  2. *Ontlasten*. Met de Code-Aster-standaard 1e-6 en alleen `RESI_GLOB_RELA`
     stagneert Newton op RESI_GLOB_RELA 1,5–2,3e-6 (restkracht ~1e-2 N bij 12 kN); de
     stap wordt 6× gedeeld en de run stopt op t = 2,92 s (`MECANONLINE9_7`). Tot dat
     moment is elke stap exact, dus de norm is alleen te streng voor deze toestand.
     Daarom is de standaard van de bridge 1e-5 (NL-01). Met 1e-6 rekent hij door met
     `RELA_OF_MAXI` en een absolute grens boven de stagnerende rest (NL-01b, 0,05 N; met
     1e-3 N niet) of met `DEFORMATION` = `PETIT`.
  3. *Rekmaat*. Met `PETIT` geeft de bridge exact de kleine-rekformule
     F = A0·(σy + H·p); het verschil met de logaritmische rek is bij 1% rek 1,1%.

### NL-20 Mecway's stapgrootte met knikken van de lasttabel ertussen

- **Doel**: niet-lineair statisch rekent met Mecway's *Time step size*
  (`<timesteps stepsize>`) en volgt toch het lastpad exact.
- **Model**: NL-01 met `<timesteps timeperiod="3 s" stepsize="0.4 s">`; de knikken van
  de opgelegde verlenging (t = 1 en 2 s) vallen tussen twee stappen.
- **Referentie**: uitvoertijden 0,4; 0,8; 1,0; 1,2; 1,6; 2,0; 2,4; 2,8; 3,0 s (Mecway's
  stappen plus de knikken); F, σ_xx en p als NL-01.
- **Resultaat**: de uitvoertijden kloppen exact; F, σ_xx en p op t = 1, 2 en 3 s 0,00%
  af (dezelfde waarden als NL-01 met 30 stappen).
- **Interpretatie**: de knikken als extra rekenstap houden de belasting per stap lineair,
  zodat radial return exact blijft. Mecway's eigen uitvoertijden zijn niet headless
  nagegaan (Mecway-solve was niet beschikbaar toen deze case werd toegevoegd).

### NL-02 Ingeklemde balk, grote doorbuiging (elastica)

- **Doel**: grote verplaatsingen en rotaties met volumes (`GREEN_LAGRANGE`) en
  `COQUE_3D` (`GROT_GDEP`).
- **Model**: L = 1 m; (a) volume 10 × 10 mm, 20 × 1 × 2 hex20; (b) strook 50 mm breed,
  10 mm dik, 20 × 1 quad8 met `elem_shell` = `COQUE_3D`. E = 210 GPa, ν = 0 (de
  elastica hangt niet van ν af; zo geen dwarscontractie bij de inklemming).
- **Randvoorwaarden en belasting**: ingeklemd op x = 0; eindkracht in −z met vaste
  richting (`force` op de knopen van het eindvlak, `FORCE_NODALE`), tijdstabel
  PL²/EI = 1, 2, 3 op t = 1, 2, 3 s.
- **Referentie**: onrekbare Euler-elastica θ'' = −α cos θ, numeriek opgelost (RK4 en
  schieten) in de testmodule; gelijk aan Bisshopp & Drucker (1945) en Mattiasson
  (1981): α = 1: v/L 0,30172, u/L 0,05643; α = 2: 0,49346 / 0,16064; α = 3: 0,60325 /
  0,25442. Gemeten in de knoop op de as van de tip. Tolerantie 1% (discretisatie;
  afschuiving ~1e-4 en rek van de as ~1e-5 zijn verwaarloosbaar).
- **Resultaat**: (a) hex20 −0,12 … −0,57% (licht stijf, groeiend met de last);
  (b) `COQUE_3D` +0,01% op alle niveaus.
- **Interpretatie**: grote verplaatsingen werken voor volumes en `COQUE_3D`, en de
  kracht houdt zijn richting. DKT en de balken `POU_D_E`/`POU_D_T` blijven in de bridge
  geometrisch lineair (KNOWN_BUGS 11); dezelfde elastica met balken `POU_D_T_GD`: NL-83.

### NL-03 Contact

**NL-03a/b: twee uitkragende balken met de tips op elkaar.**

- **Doel**: lijncontact tussen hex20-volumes, Lagrange (a) en penalty (b).
- **Model**: twee balken 100 × 10 × 5 mm (b × h), beide ingeklemd op x = 0, hex20
  20 × 1 × 1 (onderste balk 22 elementen, 10 mm overstek). Het bovenvlak van de onderste
  balk raakt de bovenste balk alleen op x = L (geen spleet) en loopt naar de inklemming
  0,5 mm weg: het contact is een lijn op x = L. Wrijvingsloos; slave = onderkant
  bovenste balk (laatste 20 mm), master = bovenkant onderste balk. E = 210 GPa, ν = 0
  (met ν = 0,3 gaf het 3D-model door plaatwerking bij de inklemming 1,35% minder
  doorbuiging dan de balktheorie, met ν = 0 0,01%).
- **Randvoorwaarden en belasting**: P = 10 N in −z op het eindvlak van de bovenste balk;
  (a) `contact_algo` = STANDARD, (b) PENALISATION met kn = 1e13 Pa/m.
- **Referentie**: C = L³/3EI + L/(κGA) (Young & Budynas, 2002, tabel 8.1, geval 1a, plus
  afschuiving); gelijke stijfheid, dus contactkracht R = P/2 en tip bovenste balk
  (P − R)·C = 7,6305e-5 m. Het gemiddelde (w_boven + w_onder)/2 = P·C/2 geldt voor
  elke contactwet. Tolerantie 0,5%.
- **Resultaat**: (a) geen bruikbaar resultaat: de rand dringt tussen de
  integratiepunten door (R ≈ 0) en bij t ≈ 0,03 s stopt Code-Aster met
  `MECANONLINE9_4` (matrix niet inverteerbaar); status BEKEND (KNOWN_BUGS 43).
  (b) tip −0,01% (gemiddeld) / +0,07% (boven), R = 4,996 N (−0,07%).
- **Interpretatie**: Lagrange-contact lukt niet bij dit lijncontact op hex20 (QUAD8-
  vlakken). Eerder ook geprobeerd, zonder succes: `AUTO` (pivot nul op `LAGS_C` van een
  hoekknoop in de eerste stap, ook met master en slave omgedraaid), `GAUSS` (zelfde
  beeld als `NCOTES`) en `NCOTES` met omgedraaide rollen (rekent door, maar R = 4,74 N
  en tip boven +7%). Penalty is exact: R = P/(2 + k_b/K_c) met k_b = 1/C geeft K_c ≈ 5e7 N/m, dus
  het effect van kn = 1e13 Pa/m is < 0,1%. Een zachtere kn laat de balken in elkaar
  dringen en verschuift last naar de bovenste balk (het gemiddelde blijft gelijk).

**NL-03c–f: contact-patchtest.**

- **Doel**: contact tussen niet-passende kwadratische meshes, Lagrange en penalty, en
  de vertaling van Mecway's *normal stiffness*.
- **Model**: twee blokken 20 × 20 × 10 mm op elkaar, onderblok 2 × 2 × 1 hex20,
  bovenblok 3 × 3 × 1 hex20; E = 210 GPa, ν = 0,3.
- **Randvoorwaarden en belasting**: symmetrievlakken x = 0 en y = 0 (beide blokken),
  onderkant z = 0 vast in z; 4000 N gelijkmatig op de bovenkant (p = 10 MPa). (c, e)
  STANDARD, (d, f) PENALISATION met kn = 1e13 Pa/m; (e, f) met de integratie expliciet
  als `#ASTER-ZONE INTEGRATION='NCOTES'`.
- **Referentie**: eenassige druk, contactdruk p overal: indrukking p·H/E = 4,762e-7 m
  per blok; met penalty extra p/kn = 1,0e-6 m (Mecway: contactdruk = *normal
  stiffness* × penetratie). Tolerantie 0,5% (de toestand is exact te representeren).
- **Resultaat**: alle verplaatsingen en de penetratie ≤ 0,01% af, in c–f.
- **Interpretatie**: `COEF_PENA_CONT` = Mecway's *normal stiffness* is juist vertaald
  (NL-03d/f; Mecway/CCX headless op hetzelfde model: −1,95245e-6 m tegen referentie
  −1,95238e-6 m). Met de oude standaardintegratie (`AUTO`, voor deze vlakken gelijk
  aan `SIMPSON`) haalde Code-Aster de patchtest niet (STANDARD tot +2,8% / −1,5%,
  PENALISATION +4,6% en penetratie −2,1%); daarom zet de bridge nu `NCOTES` bij een
  kwadratisch slave-vlak. Met passende meshes is ook `AUTO` exact. `NCOTES` is niet
  apart getest op tet10 of gekromde vlakken (wel rekenen de Mecway-voorbeelden
  PipeClip en AssemblyWithContact ermee door, zie `bridge_to_aster.py`).

### NL-70 .. NL-75 Temperatuur in de tijd (thermische rek)

- **Doel**: een *Temperature* met tijdstabel of formule in t, en een constante
  temperatuur met en zonder *Quasi-static*, in `STAT_NON_LINE` (`EVOL_THER` vanaf de
  referentie, [Thermisch.md](Thermisch.md) §3.1).
- **Model**: staaf 0,1 × 0,01 × 0,01 m, 4 × 1 × 1 hex8, E = 210 GPa, ν = 0,3,
  α = 1,2e-5 1/K, *Thermal stress* Tref = 293,15 K, `temperature2` op alle knopen
  (NL-74: tabel op de knopen x = 0 en *Node temperature* +200 K op x = L). *Quasi-static*
  met *Time period* 2 s (NL-73b en NL-75 zonder `<timesteps>`). Tabel ΔT = (0 s; 10 K),
  (1 s; 100 K), (2 s; 50 K); formule Tref + 100·t. `deformation` = `PETIT`; NL-70b met de
  standaard `GROT_GDEP`.
- **Randvoorwaarden**: symmetrievlakken x = 0, y = 0, z = 0 (vrij uitzetten); NL-71 ook
  u_x = 0 op x = L (ingeklemd in x, dwarsrichting vrij).
- **Referentie**: vrij u_x(L, t) = α·ΔT(t)·L, ingeklemd σ_xx(t) = −E·α·ΔT(t)
  (Timoshenko & Goodier, 1970, §150; uniforme rek, exact met hex8); NL-74 als LS-08c met
  de elementgemiddelden; NL-70b met Green-Lagrange-rek α·ΔT: L·(√(1 + 2αΔT) − 1).
  Daarnaast Mecway 34 met CCX op dezelfde modellen (headless; Mecway's eigen solver
  rekent L30 niet zonder venster). Tolerantie 1e-6 (analytisch), 1e-4 resp. 0,5 %
  (Mecway/CCX).
- **Resultaat**: alle controles exact (≤ 1e-6) op t = 0,5/1/2 s (tabel), 1/2 s
  (formule), de eerste stap t = 0,25 s (NL-73a: volle uitzetting) en t = 0,5 s (NL-73b:
  halve uitzetting, oplopend). Gelijk aan Mecway/CCX (verplaatsing exact; spanning: CCX
  0,2–0,4 % lager, hex8 van CCX).
- **Interpretatie**: Mecway volgt de tabel lineair, ook tussen de punten; met
  *Quasi-static* staat een constante temperatuur vanaf de eerste stap (Mecway/CCX: volle
  uitzetting op t = 0,25 s), zonder loopt hij op. De bridge doet hetzelfde. Met
  `GROT_GDEP` telt de thermische rek als Green-Lagrange-rek (0,03–0,06 % minder
  verlenging dan Mecway/CCX, NL-70b). Zonder *Quasi-static* neemt Mecway/CCX van een
  tabel de waarde op t = 1 s (de staptijd), ook als de tabel verder loopt; de bridge
  rekent dan tot t = 1 s (NL-75: 1,2e-4 m, exact en gelijk aan Mecway/CCX).
### NL-40 Formule in y en t

- **Doel**: een formule in x, y, z én t in `STAT_NON_LINE` (`FORMULE` van Y en `INST`)
  naast een gewone krachttabel (`DEFI_FONCTION`, `FONC_MULT`).
- **Model**: blok van LS-40, Mecway L30 met *Time period* 2 s.
- **Belasting**: druk `3*y^2*t` kPa op de bovenkant en een kracht Z van 0 (t = 0) tot
  −2000 N (t = 2 s) op dezelfde vlakken.
- **Referentie**: reactie 8 kN·t + 1 kN·t: 9 kN bij t = 1 s, 18 kN bij t = 2 s; moment om
  X bij t = 2 s 24 + 2 = 26 kN·m.
- **Resultaat**: alle drie exact (≤ 1e-6).
- **Interpretatie**: `INST` in de `FORMULE` is de rekentijd van `STAT_NON_LINE` (de
  rekenstappen zijn Mecway's stapgrootte, 0,5 s). Mecway 34 met CCX
  rekent dezelfde formule ook (verplaatsing evenredig met t, zelfde verhouding tot de
  bridge als bij een constante druk). In lineair statisch neemt de bridge t = eindtijd
  (WARNING).

### NL-80 .. NL-89 Balken met grote rotaties (`POU_D_T_GD`)

- **Doel**: `elem_beam` = `POU_D_T_GD` ([Instellingen §2.9](Instellingen_contact_en_nietlineair.md#29-balken-met-grote-rotaties-elem_beam--pou_d_t_gd)):
  `MODELISATION='POU_D_T_GD'`, `RELATION='ELAS_POUTRE_GR'`, `DEFORMATION='GROT_GDEP'`,
  snedekrachten uit `SIEF_ELNO`, met de combinaties die de bridge sinds V2026.1 kent
  (line3, orientatiekaart, formules, Mecway's tijdstap). NL-80 tot NL-82 zijn de
  benchmarks GB-01 tot GB-03 van de fork van MishalTPC
  (`github.com/mishal0488/MecwayAsterBridge`, commit dd4c958), hier als Mecway-model
  door de hele bridge. Module `tests_balken_grote_rotaties.py`.
- **Model**: ingeklemde balk L = 1 m langs X, RectBar 10 × 20 mm (10 mm langs V),
  E = 210 GPa, ν = 0,3, 40 line2 (NL-84: 20 line3); vaste inklemming in x = 0.
- **Referenties** (k = 5/6, `AY` = 1,2 van `RECTANGLE`):

| Case | Belasting | Referentie |
|---|---|---|
| NL-80 | eindkracht 1 N in Y (kleine last) | F L³/(3EI) + F L/(kGA) (GB-01) |
| NL-80b | hetzelfde model in lineair statisch | idem; de bridge maakt er `POU_D_T` van (WARNING) |
| NL-80c | constante eindkracht 1 N in Y en constant eindmoment 0,5 Nm om Z (geen tijdtabel) | doorbuiging F L³/(3EI) + F L/(kGA) + M L²/(2EI), rotatie F L²/(2EI) + M L/(EI) |
| NL-81 | eindmoment M = (π/2)·EI/L om Z in 20 stappen (Mecway-stap 0,05 s) | cirkelboog: tip x = L sin θ/θ, y = L (1 − cos θ)/θ, θ = π/2 (GB-02); M constant, N = 0 |
| NL-82 | kolom met beginkromming e0 (1 − cos(πx/2L)), e0 = 1e-4 L in de mesh, drukkracht 0,5 P_cr | totale uitwijking / e0 = 1/(1 − P/P_cr) = 2 (GB-03) |
| NL-83 | eindkracht van vaste richting, PL²/EI = 1, 2, 3 op t = 1, 2, 3 s | Reissner-balk (rek en afschuiving), schieten met RK4 in de testmodule; onrekbaar gelijk aan Mattiasson (1981) |
| NL-84 | NL-81 met 20 line3 (40 SEG2-cellen) | als NL-81 |
| NL-85 | NL-81 met een *Element orientation*-kaart V = Z en het moment om Y | als NL-81 in het XZ-vlak; zonder de kaart zou I vier keer zo groot zijn |
| NL-86 | centrifugaalkracht 300 r/min om Z (balk radiaal) | u(L) = ρω²L³/(3E), reactie ρAω²L²/2 |
| NL-86b | NL-86 plus een radiale truss (40 line2, `BARRE`) op y = 0,5 m, knopen vast in Y en Z | als NL-86 voor de truss |
| NL-87 | line pressure 20 N/m en zwaartekracht in −Z, configuratie GQ | w L⁴/(8EI) + w L²/(2kGA), w = q + ρAg; reactie w L |
| NL-87b | hetzelfde model, configuratie G (line pressure onderdrukt) | idem met w = ρAg |
| NL-88 | Thermal stress, ΔT = 100 K | α ΔT L |
| NL-89 | line pressure als formule `-30*x*t` N/m in −Z (Mecway-stap 0,5 s) | 11 q0 L⁴/(120EI) + q0 L²/(3kGA) (Roark), evenredig met t; reactie q0 L/2 |

  NL-83 vergelijkt ook de snedekrachten met de statica in de vervormde stand (FEM-
  coördinaten): `bendingmomw` van element 1 = P (x_tip − x_midden), `sheary` en
  `tensileforce` van het laatste element = P cos φ en P sin φ (φ = hoek van de koorde
  van dat element). NL-82 en NL-83 zijn ook headless met Mecway 34 gerekend (CCX 2.23,
  B31; `TestFiles/Tools/mw_solve.py`, gemiddelde van de doorsnedeknopen op x = L).
  Tolerantie 0,1 %; strenger: het moment in NL-81, NL-84 en NL-85 0,01 %, de
  normaalkracht daar absoluut 0,05 N (referentie 0), de reacties in NL-83, NL-87,
  NL-87b en NL-89 en de verlenging in NL-88 1e-6 relatief.
- **Resultaat**: alle controles OK.

| Case | Grootheid | Afwijking | Fork (GB) | Mecway 34 + CCX |
|---|---|---|---|---|
| NL-80 | doorbuiging tip | −0,0157 % | −0,0157 % | – |
| NL-80b | doorbuiging tip | 0,0000 % | – | – |
| NL-80c | doorbuiging tip / tiprotatie | −0,0091 / −0,0001 % | – | – |
| NL-81 | tip x / y / rotatie / M | +0,0112 / +0,0064 / 0,0000 / 0,0000 % | +0,0113 / +0,0064 % | CCX stopt bij t = 0,55 s |
| NL-82 | uitwijking / e0 | −0,0213 % | −0,0213 % | +0,0047 % |
| NL-83 | tip u_y op t = 1, 2, 3 | −0,0123 / −0,0079 / −0,0054 % | – | +0,0087 / +0,0125 / +0,0157 % |
| NL-83 | tip u_x op t = 1, 2, 3 | +0,0331 / +0,0247 / +0,0194 % (kleiner) | – | +0,0036 / −0,0030 / −0,0085 % |
| NL-83 | snedekrachten tegen de statica (M, V, N) | 0,0000 / +0,0065 / −0,0029 % | – | – |
| NL-84, NL-85 | als NL-81 | dezelfde waarden als NL-81 | – | – |
| NL-86 | tipverlenging / reactie | −0,0156 / 0,0000 % | – | – |
| NL-86b | tipverlenging / reactie truss | +0,0312 / 0,0000 % | – | – |
| NL-87, NL-87b | doorbuiging tip / reactie | +0,0008 / 0,0000 %; +0,0002 / 0,0000 % | – | – |
| NL-88 | tipverlenging | 0,0000 % | – | – |
| NL-89 | doorbuiging tip op t = 0,5 en 1 / reactie | +0,0285 / +0,0287 / 0,0000 % (kleiner) | – | – |

- **Interpretatie**:
  1. De route van de fork geeft door de hele bridge dezelfde getallen als de fork (tot
     op ~1e-6 relatief: NL-81 tip x +0,0112 tegen +0,0113 %; de fork rekende NL-81 met
     40 gelijke substappen, hier Mecway's 20 stappen).
  2. `POU_D_T_GD` is een lineair element met één integratiepunt: de snedekracht is een
     waarde per element, in het midden; de knoopwaarde is het gemiddelde van de twee
     elementen. Tegen de statica in de vervormde stand klopt hij tot 0,01 % (NL-83), in
     de meedraaiende assen van de doorsnede (aan de tip N = P sin φ).
  3. Line3 en de orientatiekaart veranderen niets aan de kinematica (NL-84, NL-85 gelijk
     aan NL-81); de kaart bepaalt welke I telt.
  4. Mecway 34 rekent niet-lineaire balken alleen met CCX (de eigen solver gaf headless
     geen oplossing). Met een eindkracht (NL-83) en de kolom (NL-82) ligt de bridge binnen
     0,02 % van Mecway/CCX; het eindmoment van NL-81 haalde CCX niet verder dan
     t = 0,55 s (daar wel op de cirkelboog).
  5. Niet in deze cases (WARNING in de bridge, KNOWN_BUGS 11): grote opgelegde rotaties
     (een slanke balk convergeerde tot 0,41 rad), element offset, flexible joint en
     koppelingen bij grote rotaties (lineaire relaties), een moment in 3D. Bezwijken van
     elementen in een model met `POU_D_T_GD` geeft vooraf een ERROR (`CALCUL_37` na het
     eerste bezwijken, [`Bezwijken.md`](Bezwijken.md)).

## 6. Dynamica (DY)

Mecway D31 met `<timesteps>` (uitvoerinterval `timepointsincrement`). Impliciet:
`dyna_impl_3d` (`DYNA_NON_LINE`, HHT of NEWMARK, `substeps_per_output` = 1, dus
rekenstap = uitvoerinterval). Expliciet: `dyna_expl_3d` (`DIFF_CENT`, diagonale massa,
stap ≤ 0,5 × de geschatte kritieke tijdstap, gelijk verdeeld over het uitvoerinterval).
Module `tests_dynamisch.py`, draaien met `python run_verificatie.py DY` (ca. 1 minuut).

**Toleranties.** De verwachte afwijking komt uit hetzelfde tijdschema, los van de
bridge in Python berekend:
- `scheme_period_ratio`: periodeverlenging en numerieke demping uit de eigenwaarden
  van de versterkingsmatrix (Hughes, 2000, hfdst. 9; HHT: Hilber e.a., 1977, met
  γ = 1/2 − α en β = (1 − α)²/4);
- `sdof_response` / `modal_step_response`: het schema op een systeem met één
  vrijheidsgraad of op exacte eigenmodes;
- `bar_chain`: de staaf als 1D-keten (consistente massa + HHT, of diagonale massa +
  centrale differenties).

Tolerantie = 1,5 × de verwachte afwijking + een marge (0,1% voor periode en één
vrijheidsgraad, 0,2% voor de rest), afgerond op 2 cijfers. Daarnaast de controle
"verloop t.o.v. schema/keten": max |u_FEM − u_Python| / max |u| over alle
uitvoertijden; grens 1e-5 waar het Python-model exact is (DY-01, DY-03; uitvoer in
enkele precisie, Newton `RESI_GLOB_RELA` 1e-5) en 0,2% bij DY-02 (meshfout van de hogere modes).

**Code-Aster-gedrag dat de vergelijking nodig had** (gemeten met 17.4; niet in de
U-documentatie gevonden):
- De beginversnelling volgt uit het evenwicht op t = 0: a0 = M⁻¹F(0), ook impliciet.
- HHT, eerste stap: de term −αF₀ gebruikt F₀ = 0, ook bij een last die op t = 0 al
  aanstaat. Met F₀ = F wijkt DY-01a 1,5% van de amplitude af, met F₀ = 0 4e-8. Een
  staplast krijgt met HHT in de eerste stap dus een iets te kleine impuls (DY-01a: piek
  −0,44% bij α = −0,1 en Δt = T/20; verdwijnt met Δt → 0). Newmark heeft dit niet.

### DY-01 Massa-veersysteem, staplast

- **Doel**: veer (`DIS_T K_T_D_L`), knoopmassa (`mass2` → `POI1 M_T_D_N`), staplast en
  de schema-instellingen.
- **Model**: line2 met Mecway *Spring* k = 1000 N/m van een vaste knoop naar een knoop
  met m = kT²/4π² = 25,33 kg (T = 1 s); de massaknoop is alleen vrij in X.
- **Randvoorwaarden en belasting**: F = 10 N vanaf t = 0, 5 perioden. DY-01a HHT
  α = −0,1 (Δt = T/20); DY-01b/c/d Newmark (trapeziumregel) met Δt = T/10, T/20, T/40.
- **Referentie**: u = F/k·(1 − cos ωt): periode 2π√(m/k), maximum 2F/k (Clough &
  Penzien, 1993). Periode gemeten als kleinste-kwadratenlijn door de kruisingen van F/k,
  piek met een parabool door het grootste monster.
- **Resultaat**: periode +1,02% (HHT) en +3,21 / +0,81 / +0,21% (Newmark), elk gelijk
  aan de voorspelling van het schema; convergentieorde 1,98 en 1,99 (theorie 2:
  periodefout (ωΔt)²/12). Piek −0,44% (HHT), 0,00…−0,02% (Newmark). Verloop t.o.v. de
  recursie van het schema 4,5e-8.
- **Interpretatie**: veer, massa, last, uitvoertijden en schema komen exact in
  Code-Aster aan; de afwijkingen zijn de bekende periodefout van het schema.

### DY-02 Ingeklemde balk, eerste eigenperiode

- **Doel**: consistente massa en stijfheid van balkelementen in de tijd.
- **Model**: console L = 1 m, rond Ø 20 mm, staal (ρ = 7850 kg/m³), 20 line2
  (`POU_D_E`). HHT α = −0,1, Δt = T1/40, 6 perioden.
- **Randvoorwaarden en belasting**: ingeklemd; staplast 10 N in Z op de tip (vrije
  trilling rond de statische stand).
- **Referentie**: f1 = (1,875²/2π)·√(EI/(mL⁴)) = 14,47 Hz, T1 = 0,06910 s (Blevins, 1979,
  tabel 8-1). Tipverplaatsing als modale superpositie Σ c_i(1 − cos ω_i t) met
  c_i = 4FL³/(EIλ_i⁴) (30 modes, Σ c_i = FL³/3EI); maximum 1,9658 × statisch.
- **Resultaat**: periode +0,27% (verwacht met HHT +0,268%), maximum −0,30% (verwacht
  −0,297%), verloop t.o.v. 30 modes met HHT 2,8e-6.
- **Interpretatie**: balkstijfheid en -massa kloppen; de afwijking is de
  HHT-periodefout. Rotatietraagheid en meshfout zijn hier verwaarloosbaar.

### DY-03 Longitudinale golf in een staaf

- **Doel**: dichtheid, diagonale massa, kritieke tijdstap en stapindeling, `FORCE_FACE`
  en een opgelegde snelheid in expliciete dynamica.
- **Model**: staaf L = 1 m, 10 × 10 mm, 100 × 1 × 1 hex8 (h = 10 mm), staal met ν = 0
  (de beweging is dan exact 1D, c = √(E/ρ) = 5172 m/s). `deformation` = `PETIT`:
  met de standaard (`GREEN_LAGRANGE` voor volumes) wijkt het verloop 1,4e-4…6,9e-4 af
  van de lineaire keten (rek ~5e-5), wat fysisch is en geen fout.
- **Randvoorwaarden en belasting**: x = 0 vast. DY-03a expliciet, staplast F = 1000 N op
  x = L; DY-03b expliciet, opgelegde snelheid v = 0,25 m/s op x = L (uitvoer elke 5 µs,
  eind 600 µs = 3,1 L/c, 6 rekenstappen per uitvoerinterval); DY-03c impliciet HHT,
  staplast, Δt = 10 µs (T/77), eind 2,4 ms.
- **Referentie** (Graff, 1975): achter het front σ = F/A resp. ρcv; deeltjessnelheid
  F/(ρcA); aankomst aan de inklemming na L/c; reflectie aan het vaste einde verdubbelt
  de reactie; tipverplaatsing vt tot 2L/c, maximum 2FL/EA; periode van de vast-vrije
  staaf 4L/c.
- **Resultaat**: DY-03a: tipsnelheid +0,21%, spanning +0,09%, aankomst +0,90% (het front
  loopt ~1 element achter door dispersie), reactie −0,06%, maximum −0,58%. DY-03b:
  spanning +0,08%, reactie −0,04%, opgelegde u en v exact. DY-03c: periode +0,23%,
  tipsnelheid +0,76%, maximum −2,67% (HHT dempt de hoge harmonischen die de knik van de
  driehoeksgolf vormen). Alle drie volgen de 1D-keten op 4e-8.
- **Interpretatie**: de expliciete en impliciete vertaling is exact; de omzetting van
  een opgelegde snelheid naar een versnelling (`FORMULATION='ACCELERATION'`) werkt.
  Impliciet geeft met hetzelfde mesh een gladder golffront (piek −2,7% tegen −0,6%
  expliciet) met ~12× minder stappen.

### DY-20 Expliciet: frictionless en constraint equation als opgelegde beweging

- **Doel**: in expliciete dynamica legt `FORMULATION='ACCELERATION'` ook bij
  `FACE_IMPO`, `LIAISON_OBLIQUE` en `LIAISON_DDL` de versnelling op; de bridge zet die
  waarden om (`_explicit_kinematics`), zoals bij DY-03b.
- **Modellen**: DY-20a = DY-03b met frictionless op het eindvlak en
  normaalverplaatsing −v·t (positief = het vlak in; `FACE_IMPO DNOR`). DY-20b = dezelfde
  staaf zonder last, op elke knoop van het eindvlak een constraint equation
  1·ux = C (C = 1e-5 m). DY-20c = vlakke plaat 0,2 × 0,1 m, 4 × 2 quad4 (DKT),
  frictionless op het hele schaalvlak met normaalverplaatsing −v·t
  (`LIAISON_OBLIQUE DX`).
- **Referentie**: DY-20a als DY-03b; DY-20b u = C vanaf de eerste rekenstap (de
  constante wordt een stoot, zoals een opgelegde verplaatsing zonder tijdshistorie);
  DY-20c starre beweging |u| = v·t, |v| = 0,25 m/s.
- **Resultaat**: DY-20a dezelfde getallen als DY-03b (spanning +0,08%, reactie
  −0,04%, u en v exact, 1D-keten 4,7e-8). DY-20b: u = C op alle uitvoertijden (2,5e-8
  relatief); met de vorige versie 1,8e-12 m (de constante werkte als versnelling).
  DY-20c: u en v exact.
- **Interpretatie**: de omzetting werkt voor alle opgelegde bewegingen. Mecway staat een
  constante ≠ 0 in een constraint equation alleen bij statisch toe (manual §9.42); de
  bridge vertaalt haar toch, met een WARNING.

### DY-70 .. DY-73 Temperatuur in dynamica

- **Doel**: thermische rek in `DYNA_NON_LINE` (KNOWN_BUGS 94, opgelost: het constante veld vanaf
  t = 0 gaf geen thermische spanning, alarm `MECANONLINE2_97`) en het weglaten in D30.
- **Model**: staaf 10 × 10 mm, hex8, staal (ρ = 7850 kg/m³), α = 1,2e-5 1/K,
  Tref = 293,15 K, `temperature2` op alle knopen. DY-70: L = 0,2 m, 8 elementen, `fixed`
  op x = 0, u_x = 0 op x = L, +50 K constant, 1 N dwars op x = L, 2 ms (de reproductie van
  KNOWN_BUGS 94, opgelost). DY-71: L = 0,1 m, 4 elementen, vrij (symmetrievlakken), tabel van Tref
  naar +100 K in 10 ms, uitvoer elke 0,5 ms. DY-72: idem, +100 K constant, ν = 0,
  NEWMARK, stap T/40 van de axiale periode T = 4L/c = 77 µs, 3T. DY-73: als DY-72 als D30
  met 1 N axiaal.
- **Referentie**: DY-70 hetzelfde model statisch (S30, `MECA_STATIQUE`): gemiddelde
  σ_xx over de doorsnede x = L/2 = −1,32502e8 Pa (5 % boven −E·α·ΔT door de verhinderde
  dwarsuitzetting bij `fixed` en het grove mesh). DY-71 quasi-statisch α·ΔT(t)·L (de
  opwarming duurt 130 axiale perioden). DY-72 een staplast F = E·A·α·ΔT op het vrije
  einde: maximum 2·α·ΔT·L, trilling om α·ΔT·L (Chopra, 2012, §4.3). DY-73: Mecway 34
  negeert *Temperature* in D30 (headless, ook met tijdstabel). Tolerantie 1 % (DY-70/71),
  3 % (DY-72), 1e-3·α·ΔT·L (DY-73).
- **Resultaat**: DY-70 −0,18 % / −0,10 % (t = 0,2 / 2 ms; met de oude vertaling
  σ_xx ≈ 0 en alarm `MECANONLINE2_97`). DY-71 −0,002 % / −0,06 % (t = 5 / 10 ms). DY-72
  maximum −1,5 %, gemiddelde −1,4 %. DY-73 max |u_x| = 9e-9 m (alleen de 1 N).
- **Interpretatie**: de temperatuur werkt in D31 nu als in Mecway's quasi-statische
  L30: een constante temperatuur is een staplast vanaf de eerste stap, een tabel wordt
  gevolgd. Mecway rekent D31 headless niet (eigen solver: geen oplossing, CCX: een lege
  oplossing), dus niet tegen Mecway vergeleken. Het maximum van DY-72 ligt door de
  dispersie van 4 hex8 iets onder 2·α·ΔT·L (met HHT α = −0,1 en ν = 0,3: −3,6 %).

## 7. Modaal (MO) en knik (BU)

- **Modaal**: Mecway V30 met `maxmode` → `modal_3d`: `ASSEMBLAGE` (`RIGI_MECA`,
  `MASS_MECA`, opleggingen als `CHARGE`) en `CALC_MODES` `PLUS_PETITE`,
  `NORM_MODE='MASS_GENE'`; zonder opleggingen `CENTRE` rond −f_s (zie onder).
- **Knik**: Mecway B30 → `buckling_3d`: `MECA_STATIQUE` met de lasten → `SIEF_ELGA` →
  `RIGI_MECA` + `RIGI_GEOM` → `CALC_MODES TYPE_RESU='MODE_FLAMB'` `PLUS_PETITE`;
  kniklastfactor = `CHAR_CRIT`.

Modules `tests_modaal.py` (MO, 10 cases) en `tests_knik.py` (BU, 7 cases), draaien met
`python run_verificatie.py MO BU` (ca. 1 minuut). Gebruikersdocumentatie:
[Modaal_en_knik.md](Modaal_en_knik.md). Toleranties: discrete modellen en balken
0,01–0,2% (een Euler-balk met 20 elementen wijkt < 0,002% af); mesh-reeksen als in §4
met p = 2. Plaatranden (MO-03, BU-04): DZ = 0 en de rotatie om de randnormaal nul
("hard", als LS-03); MO-03 houdt ook DX = DY = 0 (geen membraanmodes), BU-04 alleen
DX = 0 op x = 0 en DY = 0 in een hoek, zodat de spanning zuiver eenassig is.

| ID | Doel en model | Referentie | Resultaat |
|---|---|---|---|
| MO-01 | ingeklemde balk L = 1 m, 0,02 × 0,03 m, 20 `POU_D_E`, 6 modes | Euler-Bernoulli, λL = 1,8751 / 4,6941 / 7,8548 in beide vlakken (Blevins, 1979, tabel 8-1) | alle 6 frequenties < 0,002%; tip mode 1 = 2/√m (`MASS_GENE`) exact |
| MO-02 | dezelfde balk, hex20 50 × 2 × 3 en 100 × 4 × 6 | idem | f1 +0,20% / +0,13%; de resterende 0,13% is 3D t.o.v. Euler (inklemming, dwarscontractie); f3 −0,05% (afschuiving, rotatietraagheid) |
| MO-03 | vrij opgelegde plaat 0,6 × 0,4 m, t = 4 mm, DKT 12 × 8 / 24 × 16 / 48 × 32 | Kirchhoff f_mn = π/2·(m²/a² + n²/b²)·√(D/ρt) (Leissa, 1969) | 4 modes, orde 1,93–2,00; fijnste mesh −0,05 … −0,12% |
| MO-04 | vrije vierkante plaat 0,4 m, t = 4 mm, DKT 24 × 24, 7 modes | 6 starre modes; mode 7 ωa²√(ρt/D) = 13,468 (ν = 0,3; Leissa, 1969) | \|f1…f6\| < 6e-4 Hz; f7 +0,01% |
| MO-05 | massa-veerketen grond–k–m–k–m (*Spring* + `mass2`) | ω² = (k/m)·(3 ∓ √5)/2 | exact (< 1e-6) |
| MO-06 | vrij blok 1 × 0,1 × 0,05 m vanaf (1, 2, 3) m, hex20 10 × 2 × 2, 12 modes | som van de effectieve rotatiemassa = I om de as door de oorsprong = m(b² + h²)/12 + m·d² (Steiner); I om het zwaartepunt m(b² + h²)/12 | RX/RY/RZ 524,151 / 450,754 / 256,564 kg·m² exact (< 1e-6); om het zwaartepunt exact; som translatie X = 1 |
| MO-07 | ingeklemde balk als MO-02, hex20 50 × 2 × 3, 6 modes, `fields` met `stresses` en `vonmises` | Euler-Bernoulli: rotatiefractie om de inklemming mode 1 = 3(∫W₁x dx)²/L⁴ = 0,97069; som over de modes → I = m(L²/3 + a²/12); σ_xx(L/2, a/2) = E·(a/2)·W₁''(L/2)/√(ρAL) (massagenormeerd); Mecway headless | rotatie mode 1 / 2 −0,03 / −0,02%; som 6 modes −0,15%; σ_xx +0,43%; t.o.v. Mecway σ_xx +0,01%, fracties 0,0000% |
| BU-01 | ingeklemde kolom, 20 `POU_D_E`, druk 1000 N | Pcr = (2i−1)²π²EI/(4L²), beide vlakken (Timoshenko & Gere, 1961) | factoren 10,363 / 23,317 / 93,268 exact; tip mode 1 = 1/√(EI(π/2L)⁴L/2) (φᵀKφ = 1) exact |
| BU-02 | scharnierende kolom, idem | Pcr = i²π²EI/L² (Timoshenko & Gere, 1961) | < 0,002% |
| BU-03 | ingeklemde kolom hex20 50 × 2 × 3 / 100 × 4 × 6, `traction` op de kop | Euler | +0,20% / +0,13% (zelfde modelfout als MO-02) |
| BU-04 | vrij opgelegde vierkante plaat 0,4 m, t = 4 mm, lijnlast 1 N/m in X, DKT 8² / 16² / 32² | σ_cr·t = kπ²D/b², k = 4 (m = 1) en 6,25 (m = 2) (Timoshenko & Gere, 1961) | orde 2,00; fijnste mesh +0,09% / +0,25% |

**Effectieve massa en spanningen per mode** ([Modaal_en_knik.md](Modaal_en_knik.md)
§1.4, §1.5, §2.1): de rotaties (om de globale assen door de oorsprong, zoals Mecway)
rekent de bridge zelf; de controles staan in MO-01, MO-04, MO-06 en MO-07. Referenties:
de effectieve massa van de Euler-Bernoulli-uitkragende balk volgt uit de genormeerde
vormen W_i (Blevins, 1979, tabel 8-1) als (∫W_i·R dx)² / (L·∫R² dx), met R = 1
(translatie: 0,6131 / 0,1883 / 0,0647) of R = x (rotatie om de inklemming: 0,97069 /
0,02472 / 0,00315; eigen numerieke integratie in `tests_modaal.py`). Tolerantie 0,2%
(balkelementen) en 1% (volume, som over de modes).
- MO-01 (balk): translatie Y mode 1 0,61308 (Code-Aster) en rotatie Z mode 1 / Y mode 2
  0,97069 exact (< 0,001%); Mecway headless 0,97071. Som rotatie Z over 6 modes −0,15%
  t.o.v. m·L²/3 (3 modes in dit vlak: analytisch 0,99856).
- MO-04 (vrije plaat, DKT): som over de 7 modes van X, Z, RX en RZ = 1 (< 1e-6; de
  starre modes bevatten elke starre beweging, ook met de rotatievrijheidsgraden van de
  schaal); J_Z om de oorsprong = m·2a²/3 (< 0,001%).
- Translaties ongewijzigd: de eigen berekening van de translaties moet in elke run
  gelijk zijn aan `MASS_EFFE_UN_D*` van Code-Aster (≤ 1e-4); in alle MO-runs (balk,
  schaal, volume, veer + `mass2`) gehaald.
- Spanningen per mode t.o.v. Mecway headless (ingeklemd blok 1 × 0,1 × 0,05 m,
  hex20 10 × 2 × 2, 12 modes): verplaatsingen gelijk (< 1e-6), σ_xx buiten de eerste
  20% van de lengte ≤ 1% (halverwege bij mode 1 en 2 ≤ 0,11%); bij de inklemming en voor de
  schuifspanningen (2 elementen over de hoogte) tot 10–20% verschil in de knoopwaarde
  (andere middeling naar de knopen). Mecway's API leest de spanningen per mode uit de
  door de bridge gevulde `.liml` (`node_value` / `element_node_value` met `mode=`).

**Vergelijking met Mecway** (Mecway 33, interne solver, headless `mecway.exe … solve`,
dezelfde `.liml` uit `modellen/`):

| Case | Mode | Analytisch | Bridge | Mecway |
|---|---|---|---|---|
| MO-01 | 1 / 3 / 6 | 16,7103 / 104,722 / 439,836 Hz | +0,000 / +0,000 / +0,002% | +0,000 / +0,000 / +0,002% |
| MO-03 (48 × 32) | 1 / 2 / 4 | 88,782 / 170,734 / 307,322 Hz | −0,045 / −0,094 / −0,117% | +0,072 / +0,125 / +0,319% |
| MO-04 | 7 | 83,874 Hz | +0,007% | −0,024% |
| BU-01 | 1 / 2 / 3 | 10,3631 / 23,3169 / 93,2678 | +0,000% (alle) | +0,000% (alle) |
| BU-02 | 1 / 3 | 41,4523 / 165,809 | +0,000 / +0,001% | +0,000 / +0,001% |
| BU-04 (32²) | 1 / 2 | 303 680 / 474 500 | +0,094 / +0,248% | +0,078 / +0,317% |

Mecway-voorbeelden (Samples, headless opgelost) tegen de bridge:
VibratingCantileverBeam 7,07368 / 14,1474 / 44,3802 / 88,7605 / 125,082 Hz, verschil
< 1e-10 en vormen per knoop gelijk (< 1e-12); VibratingTrussTower 2,90265 / 2,90268 /
7,64340 Hz gelijk; VibratingFreePlate (quad8) mode 7–9 331,73 / 480,57 / 562,86 Hz tegen
Mecway 332,65 / 480,60 / 562,87 Hz (`COQUE_3D` QUAD9 t.o.v. Mecway's quad8);
VibratingCantileverSolid (8 hex20, zonder Poisson-getal in de `.liml`) 7,206 tegen
7,088 Hz (+1,7%) zolang de bridge zonder Poisson-getal ν = 0,3 nam; Mecway neemt dan ν = 0.
Na die correctie (standaard ν = 0) gelijk: 7,08845 / 14,15294 Hz;
met ν expliciet opgegeven gelijk binnen 1e-8 (ν = 0: 7,08845 Hz, ν = 0,3: 7,20627 Hz); BucklingBeam 41124,699
/ 41124,699 / 371034,90 (verschil < 2e-12; vierkante doorsnede, dus dubbele modes
zonder unieke vorm) en BucklingPlate (hex20) 7,148014 / 8,600503 / 11,14455 / 11,97405
(verschil < 2e-8, vormen per knoop gelijk op 4e-9). Een headless Mecway-script leest
`solution.modes()`, `frequency(m)` / `buckling_factor(m)` en `node_value(.., mode=m)`
uit de door de bridge gevulde `.liml` met dezelfde waarden.

**Code-Aster-gedrag dat de vertaling nodig had** (gezien met 17.4):
- `NORM_MODE='RIGI_GENE'` bestaat niet voor `MODE_FLAMB` (`ALGELINE4_77`); de bridge
  normeert de knikvormen zelf: φᵀKφ = |CHAR_CRIT·φᵀK_gφ|, met K_g uit
  `getValuesWithDescription()`.
- `CHAR_CRIT` en `MASS_EFFE_UN_D*` staan niet in `getAccessParameters()`, wel in
  `RECU_TABLE`; `MASS_EFFE_UN_DRX` bestaat niet (`UTILITAI3_5`): de bridge rekent de
  rotaties zelf (hierboven).
- De Sturm-controle faalt als een meervoudige mode op de grens valt (`ALGELINE5_23`,
  BucklingBeam); na een `<E>` stopt Code-Aster bij het volgende commando
  (`CATAMESS_6`). Daarom `VERI_MODE STOP_ERREUR='NON'` (alarmen, WARNING met uitleg).
- Vrij-vrij: shift 0 en Code-Aster's eigen verschuiving (−0,01 Hz) zijn singulier
  (`ALGELINE3_81`), ook −0,83 Hz bij een dunne plaat, en `TRI_DIAG` met
  `MODE_RIGIDE='OUI'` ook. `CENTRE` rond −f_s met (2πf_s)² = 1e-8·max(diag K/diag M)
  werkt (MO-04, VibratingFreePlate). Altijd verschuiven werkt niet: met factor 1e-6
  vond Sorensen bij de hex20-balk (f_s = 636 Hz, f1 = 16,7 Hz) geen mode
  (`ALGELINE5_49`, `ALGELINE3_78`); daarom alleen zonder opleggingen.
- Teken: BucklingBeam (druk) geeft `CHAR_CRIT` = +41124,7; dezelfde kolom onder trek
  −10,36 / −23,32 / −93,27 (Mecway zelf 8,5e13; KNOWN_BUGS 46).

### Balkorientatie (MO-20 … MO-29, LS-70 … LS-78, BU-20 … BU-24)

- **Doel**: nagaan of de bridge de doorsnede van een balk net zo draait als Mecway, in
  modaal, statisch en knik: zonder orientatie (Mecway-standaard), met een
  *orientation vector* en met vector + *angle* (`orientationvx/vy/vz`, `angle` per
  `<elem>`; bridge: groepen `BORnnnnn` met `AFFE_CARA_ELEM ORIENTATION CARA='VECT_Y'`,
  sinds V2026.2 voor elke balk, ook zonder orientatie met Mecway's standaard-V). Module `tests_balkorientatie.py`,
  `python run_verificatie.py MO-2 LS-7 BU-2` (ca. 2 minuten).
- **Model**: uitkragende balk L = 1 m, 20 `POU_D_E`, staal, RectBar 40 × 10 mm (I_W =
  16 I_V), langs X, Y, Z en schuin (1,1,1), en een I-profiel 100/50/10/8 mm langs Y
  (vector X + 90°). Raamwerk (MO-28, LS-78): kolom langs Z (standaard), ligger langs X
  (vector (0,1,1) + 30°), schuine staaf naar (1, 1, 1,5) (vector Z).
- **Referentie**: de V-as met de hand uit de regel van de Mecway-handleiding (v33 §7.5:
  vector loodrecht op U geprojecteerd, rechtsom om U gedraaid met *angle*; zonder
  vector V = Z × U, langs Z V = Y), W = U × V, RectBar `recta` langs V. Daarmee:
  Euler-Bernoulli-frequenties (Blevins, 1979, tabel 8-1) met I_V = recta·rectb³/12
  (uitwijking langs W) en I_W = rectb·recta³/12 (langs V), de richting van de
  tipverplaatsing per mode (|u·e|/|u| = 1, tolerantie 1e-4), de effectieve massa per
  richting (0,6131·(e·W)², MO-23/25), torsie f = √(GJ/ρI_p)/(4L) (J uit Roark, 7e druk,
  tabel 10.7; I_p = I_V + I_W) en langs √(E/ρ)/(4L) (MO-20); statisch u = F_U·L/(EA)·U +
  F_V·L³/(3EI_W)·V + F_W·L³/(3EI_V)·W en σ_xx = N/A ± |M_V|·(rectb/2)/I_V ±
  |M_W|·(recta/2)/I_W in de inklemming; knik met een geleiding (alle knopen in één
  richting vast) Pcr = π²E·I/(4L²) met I = I_V(a·V)² + I_W(a·W)² om de krommingsas a
  (Timoshenko & Gere, 1961). Daarnaast Mecway 34 headless op dezelfde `.liml`.
- **Resultaat**: alle frequenties ≤ 0,026% van de analytische waarde (de torsie- en
  langsmode door de lineaire interpolatie van 20 elementen), alle richtingen 1 op
  < 3e-7, effectieve massa ≤ 1e-5 absoluut, statisch ≤ 1e-7, knik ≤ 5e-6. Tegen Mecway:
  frequenties, tipverplaatsingen en kniklastfactoren gelijk op ≤ 2e-7 (ook het
  raamwerk, met de vorm van mode 1–3). Een draaiing van de doorsnede over 90° wisselt
  de zwakke en sterke as zoals verwacht: BU-20 1,7272 → BU-21 27,635 (= 16×), BU-22
  (langs Z, standaard: sterke as) 27,635, BU-23 (vector X + 30°) 8,2041 = (0,75 +
  0,25 × 16) × 1,7272.

| Case | Orientatie | Analytisch | Bridge | Mecway |
|---|---|---|---|---|
| MO-20 | langs X, standaard (V = Y) | f1 / f2 8,35517 (W) / 33,4207 Hz (V) | +0,000% / +0,000% | +0,000% / +0,000% |
| MO-20 | idem, torsie f7 / langs f14 | 357,052 / 1293,05 Hz | +0,026% / +0,026% | gelijk aan de bridge |
| MO-21 … MO-26 | Y, Z, schuin, vector Z, schuin + 30°, Z + 30° | 8,35517 / 33,4207 Hz | +0,000% | +0,000%; vormen gelijk |
| MO-27 | I-profiel langs Y, vector X + 90° | 32,8876 (W) / 108,253 (torsie) / 110,135 Hz (V) | +0,000 / +0,026 / +0,000% | gelijk (< 2e-9) |
| MO-28 | raamwerk | – | 1,39869 / 1,67958 / 4,75549 Hz | gelijk (≤ 1,4e-7) |
| MO-29 | L = 0,1 m (L/h = 2,5) | 835,516 / 3342,065 Hz (zonder rotatietraagheid) | +0,000% | +0,000% |
| LS-70 … LS-77 | als MO-20 … MO-27 | u_tip, σ_xx max/min | ≤ 1e-7 | gelijk (≤ 1e-10) |
| LS-78 | raamwerk | – | – | u en rotatie tip ≤ 3e-8 |
| BU-20 … BU-23 | geleide kolom, zie boven | 1,7272 / 27,635 / 27,635 / 8,2041 | +0,000% | +0,000% |
| BU-24 | schuin, vector Z + 30°, vrij | 1,7272 / 15,545 / 27,635; vorm 1 langs W, 3 langs V | ≤ 4e-6 | gelijk |

Bevindingen (ook gemeten buiten de vaste cases: RectBar in 20 combinaties van richting
en orientatie, RectTube, UniformGeneralSection, I, T, C, L en CircularBar langs X en
schuin, met en zonder vector + 30°):
- Modaal en statisch rekent de bridge in alle gevallen hetzelfde als Mecway (relatief
  ≤ 1e-7, vormen gelijk). Welke as I_V en welke I_W draagt, klopt voor alle
  doorsneden: RECTANGLE `HY` = recta langs V, `iyy` van de *UniformGeneralSection* =
  `IY` (om V), en de profielen met I om V en W zoals Mecway ze toont (bij L de
  hoofdassen). Bij de CircularBar zijn de buigmodes dubbel, de vorm is dan niet uniek.
- Massamatrix: Mecway en `POU_D_E` nemen de polaire traagheid ρI_p (I_p = I_V + I_W)
  mee voor torsie, maar geen rotatietraagheid van de doorsnede bij buiging: ook bij
  L/h = 2,5 (MO-29) is de frequentie de Euler-Bernoulli-waarde. Een Rayleigh- of
  Timoshenko-balk zou daar lager uitkomen; gebruik dan `POU_D_T` (instelling
  `elem_beam`, niet als Mecway) of volume-elementen.
- Geen van beide rekent met een verschoven dwarskrachtcentrum (T, L, C): buiging en
  torsie zijn ontkoppeld, ook bij knik.
- Knik met alleen drukkracht in de staafas is gelijk aan Mecway. Afwijkingen die niet
  met de orientatie te maken hebben: zuivere torsieknik (I-profiel: bridge 2414 =
  GJ·A/I_p, Mecway 2743; KNOWN_BUGS 112) en knik met buigende momenten in een
  raamwerk (vanaf mode 2; KNOWN_BUGS 113). In beide heeft de bridge gelijk, zie
  *Knik van balken: torsie en raamwerken* hieronder. Mecway gaf voor een knikmodel met een
  L-profiel headless geen oplossing (ook niet bij een tweede poging); de bridge gaf
  daar 135,1 (zwakke hoofdas) en 601,0 (G·J·A/I_p om het zwaartepunt; de echte
  buig-torsieknik van een hoekprofiel ligt lager, KNOWN_BUGS 115).

### Orientatiekaart (MO-31, LS-79 … LS-82, BU-25, LS-31d)

- **Doel**: Mecway 34 slaat de orientatie ook op als item in Loads & Constraints
  (*Element orientation* op een elementselectie): `<orientation selection="…">` met
  `<ux>`…`<vz>` en `<angleu>` (gevonden in de fork van MishalTPC,
  github.com/mishal0488/MecwayAsterBridge). Nagaan dat de bridge die kaart precies zo
  gebruikt als de attributen per element. Module `tests_balkorientatie.py` (LS-31d:
  `tests_resultaatvelden.py`), `python run_verificatie.py MO-31 LS-79 LS-8 BU-25 LS-31d`.
- **Mecway (headless gemeten, 16 okt 2026)**: een kaart geeft dezelfde verplaatsingen
  als de attributen met dezelfde vector en hoek; Mecway schrijft de kaart in zijn eigen
  oplossingsbestand terug met alle zeven kinderen (nul-vector = niet opgegeven, een hoek
  zonder eenheid in rad) en zet hem niet om naar attributen. Een formule
  (`unit=""`/`positionunit`) geldt per element in het middelpunt. Mecway rekent niet bij
  een element met een oriëntatie uit kaart én attributen of uit twee kaarten, bij een
  U-as op balken en bij een V-as of hoek op schalen; een balkkaart zonder V-vector geeft
  een singuliere oplossing; een kaart op een componentnaam heeft geen effect. De bridge
  geeft daar een WARNING (bij overlap wint de kaart, van twee de laatste) of ERROR.
- **Model**: als MO-25, LS-75, BU-23, LS-78 (een kaart per staaf) en LS-31c, nu met een
  kaart in plaats van de attributen; LS-81: balk langs X met V = (0, x, 1 − x) en hoek
  30·x graden als formule; LS-82: kaart (vector Z) op elementen 1–10 van 20.
- **Referentie**: de analytische referenties van de tweeling-cases en Mecway 34
  headless op de kaart-`.liml` zelf.
- **Resultaat**: alle 60 controles OK. De bridge geeft met kaart exact dezelfde getallen
  als met de attributen (MO-31 = MO-25, LS-79 = LS-75, BU-25 = BU-23, LS-80 = LS-78,
  LS-31d = LS-31c, verschil 0). Tegen Mecway: frequenties ≤ 1e-9, kniklastfactor 5e-12,
  tipverplaatsingen en -rotaties ≤ 3e-8 (raamwerk), formule en halve kaart ≤ 6e-10.
  Sinds deze versie krijgt elke balk Mecway's V-as expliciet als `VECT_Y` (ook zonder
  orientatie); alle bestaande balkcases gaven daarmee exact dezelfde uitkomst.

### Knik van balken: torsie en raamwerken (BU-30 … BU-37)

- **Doel**: uitzoeken wie gelijk heeft bij de twee knikverschillen met Mecway
  (KNOWN_BUGS 112, 113), met een referentie die niet uit een balkformulering komt: een
  volume- (hex20) of schaalmodel van dezelfde constructie, gerekend door de bridge
  (Code-Aster) en door Mecway 34 headless met de eigen solver en met CCX
  (`TestFiles/Tools/mw_solve.py`, 15 okt 2026, dezelfde `.liml`), of Code-Aster-testcase
  ssll105. Module `tests_knik_balk.py`, `python run_verificatie.py BU-3` (ca. 1 minuut).
- **Theorie**: `RIGI_GEOM` van `POU_D_E` (R3.08.01 §6) bevat N, de momenten, de
  dwarskrachten, de torsieterm N·(I_y + I_z)/A om het zwaartepunt en in de knopen de
  termen van matige rotaties (±M/2 tussen torsie en buigrotatie). Torsieknik zonder
  welving: P = G·J·A/I_p, onafhankelijk van de lengte (Timoshenko & Gere, 1961, §5.3 met
  C_w = 0); met welving (ingeklemd-vrij, kniklengte 2L) P = (G·J + π²E·C_w/(2L)²)·A/I_p.
  Een eigen balkcode (Euler-Bernoulli, 3D) met en zonder de knoopterm reproduceert
  Code-Aster (testcase ssll105a tot 1e-4) en Mecway (L-raamwerk tot 1e-4).

| ID | Model | Referentie | Resultaat |
|---|---|---|---|
| BU-30 | ingeklemde kolom L = 1 m, I 100/50/10/8 mm, 20 `POU_D_E`, 1000 N | Euler (factor 1–3); G·J·A/I_p = 2413,87; hex20 BU-31 | factoren 1–3 en torsie exact; mode 4 zuivere torsie; +1,2% t.o.v. hex20 |
| BU-31 | dezelfde kolom in hex20 (3000 el., voet ingeklemd) | Mecway 34 op dezelfde `.liml` (eigen solver en CCX 2384,28); G·J·A/I_p | gelijk aan Mecway (< 1e-6); −1,2% t.o.v. G·J·A/I_p |
| BU-32 | L-raamwerk van KNOWN_BUGS 113 (kolom Z, ligger X, 1 m, RectBar 40 × 10 mm, 100 N) | Euler van de kolom; hex20 van het raamwerk (Mecway, 200 × 8 × 4 el. per staaf: 44,86 / 124,12; Code-Aster 100 × 4 × 2: −53,54) | 17,272 exact; 44,53 (−0,7%), 122,44 (−1,4%), −53,04 (−0,9%) |
| BU-33 | haaks raamwerk ssll105 (benen 240 mm, 30 × 0,6 mm, E = 71 240 MPa, F_X = −1 N), 10 `POU_D_E` per been | `VALE_REFE` 0,68 / −1,088; `VALE_CALC` van ssll105a | 0,6813 / −1,0901 (+0,2%); gelijk aan ssll105a (< 1e-8) |
| BU-34 | hetzelfde raamwerk als strook in DKT (5 mm) | Mecway 34 (eigen solver 0,7036; met F_X = +1: 1,1894; CCX 0,7085 / 1,2045); balkreferentie 0,68 | −0,06% / −0,18% t.o.v. Mecway; +3,4% t.o.v. de balk |
| BU-35 | ingeklemde kolom, C 100 × 50 × 6 mm, 20 `POU_D_E` | hex20 BU-36; G·J·A/I_p = 616,43 | factor 1 +0,45%; factor 2 616,43 tegen 393,03 (+57%, BEKEND, KNOWN_BUGS 115) |
| BU-36 | dezelfde C-kolom in hex20 (3600 el.) | Mecway 34 op dezelfde `.liml` (393,0329; CCX 393,033); buig-torsieknik dunwandig 386,1 | gelijk aan Mecway; +1,8% t.o.v. de theorie |
| BU-37 | het L-raamwerk van BU-32 in hex20 (100 × 4 × 2 el. per staaf, 1616 el.), `lin_solver_resi` 1e-3 | Euler van de kolom; Mecway 34 hex20 200 × 8 × 4 per staaf (44,86 / 124,12) | 17,315 (+0,25%); 45,030 (+0,4%), 124,64 (+0,4%); gelijk aan `RESI_RELA` -1 |

- **Torsieknik (KNOWN_BUGS 112)**: Mecway's balk heeft geen torsieknik. Zijn vierde
  factor 2743,03 is de derde buigknikmode (25 × 109,72, bij de bridge mode 6); met J of A
  verdubbeld (UniformGeneralSection) blijven Mecway's factoren gelijk. De bridge geeft
  G·J·A/I_p als meervoudige eigenwaarde: met 20 elementen telt de Sturm-controle 24
  factoren in [109, 2757] waar er 6 berekend zijn (`ALGELINE5_23`). Hex20: 2384,28
  (3000 el.) en 2367,7 (12 000 el.), Mecway en CCX gelijk. Dat ligt onder G·J·A/I_p
  ondanks de verhinderde welving in de voet: de exacte J (eindige differenties op de
  doorsnede, h = 0,25 mm: 46,4e3 mm⁴, geëxtrapoleerd ~46,3e3) is 1,7% kleiner dan
  Mecway's formule (47,13e3), en de doorsnede vervormt (in de top draaien de flenzen
  ~10% minder dan het lijf). `POU_D_TG` met C_w = 4,22e-10 m⁶ (handmatig in de `.comm`,
  `GRX` vast in de voet) geeft 2552,48 = de welvingsformule; voor deze gedrongen kolom
  ligt de welvingsloze waarde dichter bij het volumemodel.
- **Raamwerken (KNOWN_BUGS 113)**: het verschil zit in de knik uit het vlak. Mecway's
  balk: L-raamwerk 19,71 (hex20 44,86), ssll105 0,4226 en met F_X = +1 0,5525 (referentie
  0,68 en 1,088). Mecway's eigen solver en CCX op het hex20-model en op het DKT-model
  geven wel de juiste waarden. Oorzaak: Mecway's balk mist de termen van matige rotaties
  in de knopen; de eigen balkcode geeft zonder die termen precies Mecway's waarden
  (19,71 / 0,4225 / 0,5526) en met die termen die van Code-Aster (44,53 / 0,6813 /
  1,0901). CCX met B32R (`.inp` direct gerekend) geeft voor het L-raamwerk 17,35 / 20,90:
  de starre knoop van CCX is lineair en mist dezelfde termen; Mecway met solver CCX geeft
  voor balken headless geen knikoplossing. Mecway geeft alleen positieve factoren en met
  zijn standaard-shift 1 sloeg het bij ssll105 de factor 0,4226 over (met shift 0,3 wel).
- **Buig-torsieknik (KNOWN_BUGS 115)**: bij een C-profiel koppelt de buiging om de
  sterke as met torsie om het dwarskrachtcentrum. Theorie (dunwandig, hartlijnmaten
  b = 47, h = 94, t = 6 mm, e = 3b²t/(6bt + ht), C_w = tb³h²/12·(3b + 2h)/(6b + h)):
  P_T = 490,5, P_x = 864,2, gekoppeld 386,1; volumemodel (hex20) 393,03. De balk geeft 616,43: te
  hoog. De bridge waarschuwt nu bij knik met T-, C- en L-profielen.
- **Volumemodel van het L-raamwerk (BU-37)**: met de standaard `RESI_RELA` 1e-6 stopt
  de statische stap met `FACTOR_57` (fout van MUMPS 5,0e-5) zonder mechanisme. De
  bridge meldt dan de waarde voor `lin_solver_resi` (hier 1e-3); daarmee rekent het door
  en zijn de factoren gelijk aan een run met `RESI_RELA=-1` (en aan Mecway en CCX op dit
  mesh). Dezelfde controle met Code-Aster 17.4 op een hex20-uitkragende balk 1000 × 40 ×
  10 mm (100 × 4 × 2, 100 N dwars, fout 7,0e-6): *Statisch* met 1e-4 doorbuiging
  47,43 mm (PL³/3EI 47,62, −0,4%); *Modaal* met voorspanning met 1e-4 f₁ = 8,3765 Hz
  (zonder voorspanning gelijk, analytisch 8,355); *Knik* axiaal gedrukt (fout 1,1e-6,
  met 1e-5) 17,317 (Euler 17,272). Een echt mechanisme (voet alleen in X vast) stopt met
  `FACTOR_11`, met `solver_nprec` -1 met `FACTOR_57` en een fout van 13 (los deel: 64):
  dan geeft de bridge de melding over een singuliere matrix.

### Modaal met voorspanning (MP)

Mecway V30 mét belastingen → `modal_3d` met `modal_prestress` aan (standaard):
`MECA_STATIQUE` → `SIEF_ELGA` → `RIGI_MECA` + `RIGI_GEOM` (+ `RIGI_ROTA` bij
centrifugaalkracht) met `COMB_MATR_ASSE` → `CALC_MODES`
([Modaal_en_knik.md](Modaal_en_knik.md) §2.5). Module `tests_modaal_voorspanning.py`
(groep "Modaal (voorspanning)", 7 cases), draaien met `python run_verificatie.py MP`.
Balk en plaat als MO-01/BU-02 en MO-03/BU-04; Pcr1 = π²EI_z/L² = 41 452 N. De
Mecway-waarden zijn headless berekend (`TestFiles/Tools/mw_solve.py`, Mecway 33,
interne solver) op dezelfde `.liml` uit `modellen/` en staan in de testmodule.
Tolerantie: analytisch 0,2% (balkelementen) of 1% (volume, plaat); t.o.v. Mecway 1%.

| ID | Doel en model | Referentie | Analytisch | Mecway |
|---|---|---|---|---|
| MP-01 | scharnierende balk, 20 `POU_D_E`, trek P = Pcr1, 4 modes | f_n = f_n0·√(1 + P/Pcr_n) (vergelijking van testcase sdll101a; f1 = √2·f10) | ≤ 0,0006% | 0,0000% |
| MP-02 | idem, druk P = −0,5·Pcr1 | idem (f1 = f10/√2) | ≤ 0,0008% | 0,0000% |
| MP-03 | idem als hex20 50 × 2 × 4, scharnier op de lijn z = 0 van de eindvlakken, trek als *traction* op beide eindvlakken | idem, 2 modes | −0,05 / −0,11% (3D t.o.v. Euler) | 0,0000% |
| MP-04 | ingeklemde balk, 20 `POU_D_E`, *centrifugal* 200 rad/s om Z | Mecway (geen gesloten oplossing) | eigen FE (consistente Hermite-matrices): 20,918 / 42,635 Hz | −0,52 / 0,000 / −0,09 / 0,000% |
| MP-05 | vrij opgelegde vierkante plaat 0,4 m, t = 4 mm, DKT 40 × 40, randen in het vlak vast, ΔT = 5,27 K: biaxiale druk N = 0,5·Ncr | ρtω² = π⁴D(m²+n²)²/a⁴ − Nπ²(m²+n²)/a² (Navier; Ncr = 2π²D/a²) | −0,02 / −0,05 / −0,05% | −0,07 / −0,25 / −0,25% |
| MP-06 | MP-01 met `modal_prestress` uit | onbelaste scharnierende balk | ≤ 0,0007% | – |
| MP-07 | MP-04 als hex20 50 × 2 × 3 | Mecway | – | 0,0000% (4 modes) |

Waarnemingen:
- **Teken:** trek verhoogt en druk verlaagt de frequenties (MP-01, MP-02, MP-05);
  `RIGI_GEOM` met coëfficiënt +1, zoals sdll101a.
- **Druk boven de kniklast** (dezelfde balk, P = −2,5·Pcr1, voorbij beide eerste
  kniklasten): de bridge geeft −57,45 en −23,45 Hz (negatieve ω²; WARNING), Mecway
  0 / 0 Hz ("non-physical modes with zero frequencies", Mecway Ltd., 2026, §6.3); de modes
  daarboven gelijk (114,899 / 239,180 Hz).
- **Spin softening:** zonder `RIGI_ROTA` gaf de eigen FE-berekening voor MP-04 in het
  rotatievlak 38,08 Hz in plaats van 20,9 Hz; Mecway rekent hem dus mee. Met
  `POU_D_E` ligt Code-Aster in het rotatievlak 0,5% lager (KNOWN_BUGS 49); met hex20
  (MP-07) exact gelijk.
- **Plaat:** Mecway's quad4 wijkt bij 20 × 20 al zonder last +0,25 / +0,93% af (met
  voorspanning +0,39 / +1,08%; DKT −0,07 / −0,20%), daarom 40 × 40.
- **Opgelegde verplaatsing ≠ 0 met een last:** Mecway geeft geen oplossing (Mecway
  Ltd., 2026, §6.3: "not allowed"), de bridge een ERROR met de oplossing.
- **Mecway-voorbeelden:** VibratingString (hex8, kracht 40 N) 10 modes +0,01 … +0,22%
  (Code-Aster `3D` t.o.v. Mecway's incompatibele hex8); VibratingMembrane (tri6,
  thermische rek, E = 0,001 Pa) faalt met de laagste modes (`ALGELINE5_49`, valse
  rotatiemodes van `COQUE_3D`); met zoekfrequentie 2 Hz is de trommelmode
  2,007456 Hz gelijk aan Mecway (KNOWN_BUGS 49).

### Niet-lineaire knik (NK)

`nonlin_static_3d` met `crit_stab` (`CRIT_STAB` in `STAT_NON_LINE`) en/of
`imperfection_*` (lineaire knikvorm als voorvervorming via `MODI_MAILLAGE DEFORME`;
[Modaal_en_knik.md](Modaal_en_knik.md) §5). Module `tests_niet_lineaire_knik.py` (groep
"Niet-lineaire knik", 5 cases), draaien met `python run_verificatie.py NK` (ca. 1,5
minuut). Model: ingeklemde kolom L = 1 m, 0,02 × 0,03 m (zwakke as Y), staal, drukkracht
als tijdstabel P(t) = t·P_eind; Euler Pcr = π²EI/(2L)² = 10 363 N (Timoshenko & Gere,
1961). De CRIT_STAB-waarden en de imperfectie leest de test uit de `.mess` met dezelfde
functies als de bridge (`bridge_results_liml.read_crit_stab`, `crit_stab_estimate`,
`read_imperfection`). Toleranties: het klaar-criterium van stap S10c (CRIT_STAB 2%
van Euler, versterking 5%), strenger waar de oplossing exact is (balken 0,2%, factor met
`PETIT` en de lineaire knik 0,5%: de 3D-modelfout van BU-03 is +0,2%).

| ID | Doel en model | Referentie | Resultaat |
|---|---|---|---|
| NK-01 | 20 `POU_D_E` (altijd `PETIT`), P_eind = 0,9 Pcr, 10 stappen | λ(t)·P(t) = Pcr | 10 363 N op t = 0,5 en 1 (< 0,001%); gelijk aan BU-01 |
| NK-02a | hex20 50 × 2 × 3, standaard (`GREEN_LAGRANGE`) | knikpunt (λ lineair naar 0 uit de laatste twee stappen) × P_eind = Pcr | 10 402 N (+0,38%); λ van −22,6 (t = 0,1) naar −2,70 (t = 1) |
| NK-02b | idem met `deformation` = `PETIT` | λ(t)·P(t) = Pcr | 10 384 N (+0,20%, gelijk aan BU-03-h20-n2) |
| NK-03 | NK-02a met imperfectie 0,001 L in knikvorm 1 (eenheid `L`), 20 stappen (stepsize 0,05 s) | lineaire knik van de imperfectiestap; totale uitbuiging e0/(1 − P/Pcr) (Timoshenko & Gere, 1961, hfdst. 1); Southwell (1932) | kniklastfactor × P_eind 10 384 N (+0,20%); knikpunt 10 400 N (+0,36%); w/e0 bij 0,27 / 0,495 / 0,675 Pcr −0,09 / −0,21 / −0,44%; Southwell-Pcr 10 384 N (+0,20%) |
| NK-04 | NK-03 bilineair plastisch (fy = 25,9 MPa: Npl = 1,5 Pcr; H = 210 MPa), e0 = 5 mm, P_eind = 0,8 Pcr, 40 stappen (stepsize 0,025 s) | P_u tussen de eerste vloei (Ayrton & Perry, 1886: P/A + P·e0/((1 − P/Pcr)·W) = fy, 0,419 Pcr) en het plastisch scharnier op de elastische uitbuiging ((P/Npl)² + M/Mpl = 1, 0,563 Pcr) | stop op het grenspunt (`MECANONLINE9_7`, verwacht) bij P_u = 0,488 Pcr; λ_eind/λ_begin = 0,007 (CRIT_STAB gaat naar 0) |

Waarnemingen:
- **Wat CRIT_STAB uitrekent** hangt af van de kinematica: met kleine verplaatsingen
  det(K_T + λK_g) = 0 (lastfactor; de `.mess` toont ~35 "produits B\*X" per stap), met
  grote verplaatsingen det(K_T + λI) = 0 ("produits B\*X = 0"), zoals U4.51.03 §3.18
  beschrijft. Eén elset met grote verplaatsingen is genoeg (gemeten met een hex20-kolom
  plus een losse balk, in beide volgorden). `PETIT_REAC` gaf dezelfde factoren als
  `PETIT`; `GDEF_LOG` (NK-04) rekent als `GREEN_LAGRANGE`.
- **Boven de kniklast** (NK-01-model tot 1,2 Pcr): λ = 0,926 op t = 0,9; de perfecte
  kolom blijft recht, Code-Aster geeft geen melding en rekent door; de bridge meldt
  "Knik bereikt".
- **Extrapolatie** bij grote verplaatsingen: de reeks λ(t) is licht gekromd; met de
  laatste stap op 0,27 Pcr gaf de schatting +4,7%, op 0,9 Pcr +0,4% (KNOWN_BUGS 53).
- **Mesh terug na de berekening**: de export controleert de knopen tegen de `.liml`
  (`_check_node_order`); na het terugzetten met −e0·φ is het verschil op
  afrondingsniveau (NK-03, NK-04 geladen zonder melding).
- **Met bezwijken van elementen** (de lus van `bridge_failure`, `reuse`): de tabel
  `ANALYSE_MODALE` bevat alle stappen (NK-04-model met `failure_plastic_strain` 0,02).
- **Mecway-voorbeeld BucklingPlateNonlinear** (hex20, last 6 → 8 N, verstoring 0,1 mN):
  λ wisselt van teken tussen t = 0,5 en 0,6, geïnterpoleerd t = 0,575, last 7,15 N
  (theorie 7,06 N, Mecway: "7,0–7,1 N", Mecway Ltd., 2026, §11.9); daarna weer λ < 0 (stabiel
  gedrag na knik van een plaat).
- **`#ASTER-OPTIE`**: dezelfde instellingen per model gaven dezelfde getallen als
  NK-03 ([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) voorbeeld 10).

### Respons op modale basis (MD)

Mecway D30 met *Mode superposition* → `dyna_modal_3d`: `CALC_MODES` → `PROJ_BASE` →
`DYNA_VIBRA` `BASE_CALCUL='GENE'` (NEWMARK, 50 stappen per periode van de hoogste
mode) → `REST_GENE_PHYS` ([Respons_op_modale_basis.md](Respons_op_modale_basis.md)).
Module `tests_dynamisch_modaal.py` (groep "Respons op modale basis", 8 cases), draaien
met `python run_verificatie.py MD` (ca. 1 minuut). De Mecway-waarden zijn headless
berekend (`TestFiles/Tools/mw_solve.py`, Mecway 33, interne solver, Mode
superposition) op dezelfde `.liml` uit `modellen/` en staan als tijdreeks (elke n-de
uitvoertijd) in de testmodule. "Verloop" is max |u − u_ref| over alle (of de
opgeslagen) uitvoertijden, gedeeld door de grootste |u_ref|. Tolerantie: analytisch
1% (piek, verloop), periode 0,5%, t.o.v. Mecway 2%.

Model MD-01 … MD-04 en MD-07: ingeklemde balk 1 m, 10 `POU_D_E`, 20 × 30 mm, 1 kg/m³
(eigen massa 6e-4 kg), 10 kg op de tip: k = 3EI/L³ = 12 600 N/m, f = 5,649 Hz;
staplast 100 N (u_st = 7,937 mm) in Y op de tip, 3 modes. Referentie:
1-vrijheidsgraadsysteem, exacte oplossing (Duhamel in gesloten vorm; Clough &
Penzien, 1993, hoofdstuk 3 en 4).

| ID | Doel en model | Referentie | Analytisch | Mecway |
|---|---|---|---|---|
| MD-01 | staplast, ongedempt, Mecway-tijdstap 0,01 s (ω·Δt = 0,355), 1 s | u = u_st(1 − cos ωt): piek 2u_st (DAF 2), T = 2π√(m/k) | piek −0,00%, periode −0,00%, verloop 1,2e-4 | verloop 1,4e-5 |
| MD-02 | staplast, Rayleigh α = 2ζω (ζ = 0,05) | piek u_st(1 + e^(−πζ/√(1−ζ²))); gedempte staprespons | piek −0,00%, verloop 2,9e-5 | verloop 4,2e-6 |
| MD-03 | F = 100·sin(0,8ωt) N als tabel (400 punten over 2 s), ζ = 0,05, tijdstap 5 ms | exacte respons uit rust (inschakelverschijnsel + stationair, DAF stationair 2,71) | verloop 1,7e-3 (de tabel wijkt ~0,2% af van de sinus), piek −0,17% | verloop 6,9e-6 |
| MD-04 | als MD-01 met de instelling `modal_damping` = 0,05 (geen Mecway-invoer) | als MD-02 | piek −0,00%, verloop 2,8e-5 | – |
| MD-05 | console 1 × 0,1 × 0,05 m, hex20 10 × 2 × 1, 6 modes, 1000 N in Z op het eindvlak, Rayleigh β = 1e-4 s, 0,1 s, tijdstap 0,5 ms | Mecway | – | verloop tip `displz` 3,8e-5, `velz` 1,4e-4, `stressxx` (halverwege, bovenvlak) 4,0e-4 |
| MD-06a | Euler-console, 20 `POU_D_E`, staal, puntlast 100 N op de tip, α = 20 1/s, 1 mode, 2 s, *keepeverynthtimestep* 10 | eindverplaatsing = 12/λ₁⁴ · PL³/3EI = 0,97069 · u_st (bijdrage van mode 1; Blevins, 1979, tabel 8-1); 201 uitvoertijden | −0,00%; 201 | verloop 3,4e-3 |
| MD-06b | als MD-06a met `static_correction` | eindverplaatsing = PL³/3EI | +0,00% | – (Mecway heeft geen statische correctie) |
| MD-07 | model MD-01 zonder Mode superposition, tijdstap 0,02 s, `dyna_impl_3d` met NEWMARK en `PETIT` | dezelfde Newmark-recursie (`sdof_response`, ω·Δt = 0,71: periodefout +4%) | verloop 1,0e-4 | verloop 3,1e-8 |

Waarnemingen:
- **Mecway integreert de modale vergelijkingen exact:** met tijdstap 0,02 s en
  0,001 s dezelfde respons, binnen 1e-4 van u_st(1 − cos ωt) (bij de directe Newmark
  van Mecway is de afwijking dan 58%). De bridge rekent NEWMARK met een kleine stap en
  komt op 1,4e-5 van Mecway (MD-01).
- **Geen statische correctie in Mecway** (MD-06a: 0,97069 · u_st, ook met 6 modes
  0,99856 = de som 12/λ_i⁴ van de 3 modes in dat vlak), en **geen voorspanning door
  de belastingen** (10 kN trek op de tip van MD-01: periode onveranderd in Mecway en de
  bridge).
- **Mecway-voorbeeld DampedVibratingStrip** (quad8-schalen, `COQUE_3D`, 10 modes,
  Rayleigh α = 1, β = 0,005): disply in de tabelknoop max. 1,9% verschil over 10 s,
  piek −0,6%, grootste `vonmisesu1` +0,9%. De frequenties van de schalen wijken af van
  Mecway (mode 1 / 2: −0,6 / +0,3%; KNOWN_BUGS 2), waardoor de fase in 10 s verloopt.
  Mode 2 (1,1017 Hz, ω = 6,92 rad/s) krijgt ξ = 0,0895, de Mecway-handleiding noemt 0,08978 bij
  ω = 6,91 rad/s (Mecway Ltd., 2026, §11.24).
- **Dempingsverhouding ≥ 1** (bijv. `modal_damping` 1,2): de job stopt met
  `BRIDGE_DYNA_MODAL_FOUT DEMPING`; de bridge meldt oorzaak en oplossing.

### Harmonische respons (HR)

Eigen analyse `harmonic_3d` (Mecway heeft geen harmonische analyse; het model is een
*Frequency*-analyse): `CALC_MODES` → statische verrijking → `PROJ_BASE` →
`DYNA_VIBRA` `TYPE_CALCUL='HARM'` `BASE_CALCUL='GENE'` → `REST_GENE_PHYS`, of direct
`BASE_CALCUL='PHYS'` ([Respons_op_modale_basis.md](Respons_op_modale_basis.md) §7).
Module `tests_harmonisch.py` (groep "Harmonische respons", 11 cases), draaien met
`python run_verificatie.py HR` (ca. 1 minuut). U = displ + i·displi in de knoop;
"max. afwijking" is het maximum over alle frequenties van de run. Tolerantie
(klaar-criterium S10h): amplitude 1%, fase 1°, GENE t.o.v. PHYS 1%.

Model HR-01, HR-04, HR-05: veer k = 1000 N/m (line2, *Spring*) en knoopmassa 2 kg
(f_n = 3,559 Hz), de massaknoop alleen vrij in X, kracht F₀ = 10 N in X (u_st = 10 mm),
1 mode. Referentie: 1-vrijheidsgraadsysteem U = u_st/((1 − r²) + 2iζr), r = f/f_n
(Clough & Penzien, 1993, hoofdstuk 3). Model HR-02: ingeklemde balk 1 m, 20 `POU_D_E`,
20 × 30 mm, staal 7850 kg/m³, 100 N in Y op de tip (u_st = 7,937 mm), Rayleigh α =
4,20 1/s (ζ = 0,02 in mode 1), 8 modes (4 in het Y-vlak: 16,71 / 104,72 / 293,2 /
574,6 Hz), 1–200 Hz (100) + 5 per mode. Referentie: exacte Euler-Bernoulli-receptantie
van de tip w(L)/F = (sin βL cosh βL − cos βL sinh βL)/(EIβ³(1 + cos βL cosh βL)), β⁴ =
ρA(ω² − iαω)/EI (afgeleid; Bishop & Johnson, 1960; statische limiet L³/3EI, polen bij
de eigenfrequenties van Blevins, 1979, tabel 8-1). Model HR-03: de hex20-console van
MD-05 (1000 N in Z, β = 1e-4 s, 6 modes), 1–300 Hz (60) + 5 per mode.

| ID | Doel en model | Referentie | Resultaat |
|---|---|---|---|
| HR-01a | 1 vrijheidsgraad, `modal_damping` 0,05, GENE, 0,5–7 Hz (27) + 5 rond f_n | exact (ζ = 0,05) | \|U\| max. 5,5e-8, fase max. 7,5e-6°, Re/Im 5,1e-8; piek 0,10013 m en piekfrequentie f_n√(1−2ζ²) exact; \|a\| = ω²\|U\| (1e-7); 32 frequenties |
| HR-01b | idem, Rayleigh α = 2ζω_n (C = αM) | exact (ζ = α/2ω_n) | als HR-01a |
| HR-01c | idem, PHYS (direct, C = αM) | exact | als HR-01a |
| HR-01d | demper (Mecway *Damper*, c = 2ζ√(km), ζ = 0,2), PHYS, lijst met f_n | exact (ζ = 0,2) | \|U\| 3,6e-8, fase 5,8e-6°, Re/Im 4,8e-8 |
| HR-02a | balk, GENE 8 modes met statische verrijking | Euler-Bernoulli exact; PHYS (HR-02b, opgeslagen) | 6,6e-4 (fase 0,04°) over 1–200 Hz, met twee resonanties en de antiresonantie bij 73 Hz; t.o.v. PHYS 1,9e-5 |
| HR-02b | idem, PHYS | Euler-Bernoulli exact | 6,6e-4 (fase 0,04°): de discretisatiefout van 20 elementen |
| HR-02c | idem, GENE zonder verrijking | statisch deel van de weggelaten modes 1 − Σ_{i≤4} 12/λ_i⁴ = 6,226e-4 | 6,222e-4 (−0,06%); t.o.v. exact 4,6e-3 tot 45 Hz en 5,2e-3 rond mode 2 (95–115 Hz) |
| HR-03a | hex20-console, GENE 6 modes met verrijking | PHYS (HR-03b, opgeslagen) | tip U_z 4,3e-6, von Mises bij de inklemming 4,3e-5, \|σ_xx\| halverwege 2,3e-3 |
| HR-03b | idem, PHYS | piekfrequentie f₁√(1−2ξ₁²), ξ₁ = βω₁/2 | exact (de verfijning legt een punt op de piek) |
| HR-04 | 1 vrijheidsgraad, amplitude uit een Mecway-tabel F(f) = 10 + 2f N, `#ASTER-FASE Last = 90`, frequenties met `#ASTER-OPTIE`, `MEETPUNT_Massa` | exact met F(f) en fase +90° | \|U\| 2,5e-8, fase 3,6e-6°; CSV = knoopwaarde |
| HR-05 | twee krachten op de massa: 10 N fase 0 en 4 N met `#ASTER-FASE Last2 = 180` | exact met 6 N | \|U\| 2,8e-8, fase 1,9e-6° |

Waarnemingen:
- **Fase-afspraak** (gemeten in een prototype op de hex20-console): `PHAS_DEG` = φ
  geeft F·e^{iφ}, U = F·e^{iφ}/(k − mω² + iωc) en u(t) = Re(U·e^{iωt}); ver onder de
  resonantie in fase, bij de resonantie −90°, erboven −180° (HR-01).
- **Modale truncatie:** zonder verrijking mist de modale basis het statische deel van
  de hogere modes, een constante 6,2e-4·u_st (HR-02c, precies de reeks van
  Blevins). Waar de respons klein is (antiresonantie, boven mode 2) wordt de relatieve
  fout groot (64% in de antiresonantie, 7% bij 200 Hz). Met de statische verrijking
  (zoals `DYNA_LINE` `ENRI_STAT`, standaard aan) is GENE gelijk aan PHYS (HR-02a,
  HR-03a). Ligt de statische vorm al in de modes (1 vrijheidsgraad), dan laat
  `DEFI_BASE_MODALE` hem weg ("Nombre de modes propres limité à 1").
- **Verfijning:** `DEFI_LIST_FREQ` `LARGEUR_3DB` met 5 punten centreert op
  f_n√(1−2ζ²), de piek van \|U\|: piek en piekfrequentie exact (HR-01a, HR-03b).
- **Tabel als functie van de frequentie:** `FONC_MULT` met een `DEFI_FONCTION` van
  `FREQ` werkt in GENE en PHYS (HR-04).
- **Mecway:** geen harmonische analyse, dus geen vergelijking met een Mecway-oplossing.
  Mecway's API leest het resultaat van HR-02a (headless `mecway.exe <model> script
  <script.py>`: 120 frequenties, `node_value` van de verplaatsingsvelden gelijk aan de
  bridge); de GUI-weergave is NIET bekeken (KNOWN_BUGS 54).

### Modaal met demping: complexe modes (MC)

Mecway V30 met Rayleigh-demping en/of dempers en de instelling `modal_complex` →
`CALC_MODES` met `MATR_AMOR` ([Modaal_en_knik.md](Modaal_en_knik.md) §6). Module
`tests_modaal_demping.py` (groep "Modaal met demping", 7 cases), draaien met
`python run_verificatie.py MC` (ca. 15 s). Gecontroleerd per mode: de gedempte
frequentie f_d (`<mode frequency>`), ζ (`AMOR_REDUIT`) en f_n = |s|/2π uit de
`BRIDGE_MODE`-regels. Tolerantie (klaar-criterium S10f): 1% voor ζ en f_d; f_n t.o.v.
Mecway 0,1%; MC-03 0,1%.

Model MC-01/02: grond — veer k = 1000 N/m (*Spring*, line2) — 2 kg (*mass*) — demper
(*Damper*, line2) — grond, langs X (massa alleen vrij in X): f_n = √(k/m)/2π =
3,5588 Hz. Referentie: 1-vrijheidsgraadsysteem (Clough & Penzien, 1993, hoofdstuk 2).

| ID | Doel en model | Referentie | Resultaat |
|---|---|---|---|
| MC-01a/b | demper c = 2ζ√(km), ζ = 0,1 en 0,5 | ζ; f_d = f_n√(1 − ζ²) = 3,5410 / 3,0820 Hz; f_n; vorm reëel | ζ, f_d en f_n ≤ 1,3e-15; ‖Im‖/‖Re‖ ≤ 4e-17 |
| MC-02a | geen demper, Rayleigh α = 2ζω_n (ζ = 0,2): C = αM op de knoopmassa | ζ = α/(2ω_n); f_d = 3,4869 Hz | ≤ 1,3e-15 |
| MC-02b | idem met β = 2ζ/ω_n: C = βK op de veer | ζ = βω_n/2 | ≤ 1,3e-15 |
| MC-03 | grond — k₁ = 2000 — m₁ = 2 kg — k₂ = 1000 — m₂ = 1 kg — c = 30 N·s/m — grond (niet-proportioneel) | wortels van (m₁s² + k₁ + k₂)(m₂s² + cs + k₂) − k₂² = 0 (Durand-Kerner; Kerner, 1966): f_d = 3,2945 / 6,6902 Hz, ζ = 0,48765 / 0,081509 | ≤ 1,1e-14; vorm complex (‖Im‖/‖Re‖ = 0,16 / 0,36) |
| MC-04 | hex20-console 1 × 0,1 × 0,05 m (10 × 2 × 1, als MD-05), 6 modes, Rayleigh α = 20 1/s, β = 1e-4 s | ζ_n = α/(2ω_n) + βω_n/2 en f_d = f_n√(1 − ζ_n²) met f_n van Mecway (headless; Mecway negeert de demping): ζ = 0,0509 … 0,2308 | ζ ≤ 2e-11, f_d ≤ 8,4e-11; f_n t.o.v. Mecway ≤ 8,4e-11 |
| MC-05 | als MC-04 zonder inklemming (vrij-vrij), 10 modes gevraagd | de 6 starre modes zijn met demping reëel (s = 0, s = −α) en vallen weg; elastische modes = Mecway's modes 7–10 | 6 modes (alarm `ALGELINE5_79`); ζ ≤ 3e-11, f_n t.o.v. Mecway ≤ 3e-11 |

Waarnemingen:
- **Mecway** (headless) geeft bij V30 met Rayleigh-demping dezelfde frequenties als
  zonder (5,6494 / 8,4741 / 564,94 Hz, massa op een balk) en met een *Damper* geen
  oplossing; f_n van de bridge is daarom gelijk aan Mecway's frequentie (MC-04/05).
- Code-Aster's `FREQ` is de **gedempte** frequentie en `AMOR_REDUIT` = ζ = −Re(s)/|s|
  (MC-01b: ζ = 0,5 geeft 3,0820 Hz = 0,866·f_n).
- Bij Rayleigh-demping is de vorm reëel en na de normering gelijk aan de reële
  massagenormeerde mode (gemeten met een tipmassa op een balk: verschil 2e-9); met een
  demper op één massa (MC-03) is de vorm complex.
- `TRI_DIAG` (standaard), `QZ` en `SORENSEN` met `CENTRE` (zoekfrequentie) gaven
  dezelfde f_d en ζ (≤ 1e-9); `SORENSEN` met `PLUS_PETITE` stopt (`ALGELINE2_71`).
- Met β = 1e-3 s op MC-04 (ζ ≥ 1 vanaf mode 4) gaf Code-Aster 3 van de 6 modes met
  `ALGELINE5_79`; de bridge meldt de oorzaak (overkritische demping).

### Cyclische symmetrie (CY)

Mecway V30 met *Cyclic symmetry* → `MODE_ITER_CYCL` op de sector
([Modaal_en_knik.md](Modaal_en_knik.md) §7). Module `tests_cyclisch.py` (groep
"Cyclische symmetrie", 6 cases, 171 controles), draaien met `python
run_verificatie.py CY` (ca. 2 min; CY-02 en CY-06 lezen het hele wiel van CY-01 en
CY-05 uit de werkmap, draai die dus eerst). Mode k van ND d is mode d·maxmode + k (Mecway's
volgorde). Referenties: het **volledige model** (de sector N keer, hetzelfde mesh,
gewone modale route; CY-02, CY-06), **Mecway 33** headless met zijn eigen cyclische
symmetrie (interne solver, zelfde `.liml`), en analytisch: dunne ring in het vlak
f_n = 1/(2π)·√(EI/(ρAR⁴))·n(n² − 1)/√(n² + 1) (Blevins, 1979, tabel 9-2) en de
ingeklemde cirkelvormige plaat (Leissa, 1969, tabel 2.1). Tolerantie (klaar-criterium
S10g): volledig model en Mecway 1%, analytisch 2%; starre modes |f| ≤ 0,05 Hz.
Staal E = 210 GPa, ν = 0,3, ρ = 7800 kg/m³.

**Het hele wiel** (S10i, instelling `cyclic_full_wheel`, standaard aan): elke cyclische
case controleert dat elke mode op alle N × n knopen staat (Mecway's eigen oplossing
heeft er evenveel) en dat de vorm doorloopt over de snijvlakken (samenvallende
knopen van naburige sectoren gelijk, relatief ≤ 1e-6). CY-02 en CY-06 vergelijken
de vorm van elke mode van het wiel van CY-01 en CY-05 met het volledige model: de
**subspace-MAC** ‖P u‖²/‖u‖² met P de projectie op de modes van het volledige model
binnen de frequentieband van de mode (relatief 1e-4, starre modes < 0,05 Hz; een paar
of een dubbele frequentie geeft meer dan één mode, want welke staande golf van een paar
je krijgt is willekeurig). Klaar-criterium S10i: 1 − MAC ≤ 1e-3 (MAC ≥ 0,999).

| ID | Doel en model | Referentie | Resultaat |
|---|---|---|---|
| CY-01 | vrije ring R = 0,5 m, radiaal 0,01 × axiaal 0,03 m, sector 30° (12 segmenten) om Z, 6 hex20, 2 modes per ND (ND 0 … 6) | Blevins (eerste mode van ND n = buiging in het vlak, n = 2 … 6); volledig model; Mecway; hele wiel | Blevins +0,59 … +1,18% (dunne-ringtheorie, t/R = 0,02; het volledige model wijkt evenveel af); volledig model en Mecway ≤ 2e-6; ND 0/1: starre modes ≤ 0,005 Hz; wiel 960 knopen, snijvlakken ≤ 3,7e-15 |
| CY-02 | dezelfde ring volledig (72 hex20), 40 modes, gewone modale route | Blevins; vormen van het hele wiel van CY-01 | +0,59 … +1,18% (dezelfde waarden als CY-01); 1 − MAC ≤ 5,1e-7 (14 modes, starre modes 0) |
| CY-03 | CY-01 met de as langs X (Mecway `axis="1"`) | als CY-01 | bitgelijk aan CY-01 (de bridge draait het model naar Z en terug); wiel 960 knopen, snijvlakken ≤ 3,7e-15 |
| CY-04 | ingeklemde cirkelvormige plaat a = 0,5 m, h = 0,01 m, 6 segmenten (16 × 6 elementen: hex20 + wedge15 in het midden), knopen op de as (interface `AXE`) | Leissa (0,1), (0,2), (1,1), (2,1), (3,1); Mecway; hele wiel | Leissa +0,58 … +0,66% (mesh; Mecway geeft hetzelfde); Mecway ≤ 0,03%; wiel 4530 knopen, snijvlakken ≤ 9e-15, op de as 6,2e-4 (Mecway's eigen oplossing 9,4e-4, criterium 2e-3) |
| CY-05 | draaiende schijf om Y (Mecway `axis="2"`), naaf r = 0,1 m ingeklemd, a = 0,5 m, h = 0,01 m, 3000 r/min, 12 segmenten | volledig model (CY-06); Mecway; hele wiel | ≤ 0,0012% en ≤ 0,0012% (voorspanning: spanningsverstijving + spin softening; paren met een vaste naafknoop); wiel 1524 knopen, snijvlakken ≤ 1,3e-14 |
| CY-06 | dezelfde schijf volledig (144 hex20), 30 modes | Mecway; vormen van het hele wiel van CY-05 | ≤ 1e-6; 1 − MAC ≤ 2,1e-8 (14 modes) |

Waarnemingen:
- **Mecway** (headless): `axis` 1 = X, 2 = Y, 3 = Z (een ringsector om Z gaf met 3 de
  frequenties van de volledige ring, met 1 en 2 niet); per ND *Number of modes* modes,
  op volgorde van ND; een paar staande golven één keer; de oplossing heeft het hele
  wiel (eigen knopen en elementen in `<solution>`). Een slave op −360°/N werkt ook
  (de bridge bepaalt de richting). Mecway's API leest de `.liml` met de modes van de
  bridge (headless script: `modes()` 1 … 14, `frequency` en `node_value` gelijk aan
  de bridge).
- **Formaat van het hele wiel** (S10i; headless `mw_solve.py` op CY-01, CY-04, CY-05,
  Mecway's Impeller en drie varianten van CY-01: twee elsets met door elkaar lopende
  elementnummers, een losse knoop, master en slave verwisseld): knoop i van sector j
  = i + j·n, gedraaid over +j·360°/N (rechtsom-positief, ook met verwisselde
  master/slave), element e + j·ne, per elset de sectoren achter elkaar, alle knopen
  gekopieerd (ook op de snijvlakken en de as). De bridge schrijft hetzelfde: de
  modelkopie in `<solution>` van de bridge (fragment van CY-01, en de `<results>` van
  Mecway's eigen oplossingen van de varianten en de Impeller ingeplakt met
  `splice_results`) heeft dezelfde knoopnummers in dezelfde volgorde, dezelfde
  elementen en elsetvolgorde, en coördinaten ≤ 1,1e-15 m van die van Mecway (alleen
  het 15e cijfer kan verschillen). Mecway's API (headless `mecway.exe <model>
  script`) leest het wiel van de bridge zoals zijn eigen: 960 knopen, 72 elementen,
  14 modes, `node_value` op alle knopen, `solution.volume` en `interpolate` in een
  element van de laatste sector; idem Mecway's Impeller door de bridge (17 sectoren om
  Y, 9996 knopen, 1479 elementen, 27 modes). Omdat de nummering gelijk is, zijn de
  vormen knoop voor knoop met Mecway's eigen wiel te vergelijken: ND 0 van CY-05 MAC
  1,000000, van de Impeller 0,99958 … 0,99994 (de elementen wijken iets af, KNOWN_BUGS
  62); bij een paar of een dubbele frequentie kiezen Mecway en Code-Aster een andere
  staande golf (lage MAC per mode, verwacht). De Mecway-GUI is NIET bekeken.
- **Resultaten... bij een X- of Y-as** (CY-05, Mecway's IronPython): het `.mail` van
  de run staat in het rekenframe (as → Z); `check_results_fit` draait de coördinaten
  terug (`bridge_cyclic.to_model_frame`) en accepteert het resultaat van CY-05 (vóór
  de correctie: "Knoop 109 ligt in het model anders dan in de run (verschil 0.5)"). Een
  knoop die in het model 0,01 m verschoven is, wordt nog steeds geweigerd.
- **Negatieve controle** van de MAC: een wiel zonder fase (sector 0 alleen gedraaid
  naar elke sector) gaf voor ND 2, 3 en 4 van CY-01 1 − MAC = 1,000; de controle
  onderscheidt dus de fase van de sectoren.
- **Basis**: met de standaard (20 sectormodes) zijn de laagste modes per ND gelijk aan
  het volledige model; de 4e mode van ND 1 van de ring was met 10/20/40/80 sectormodes
  1658,7 / 1657,5 / 1663,8 / 1656,7 Hz (Mecway 1656,6): de hoogste modes per ND
  hangen van de basis af.
- **Dubbele eigenwaarde in ND 0**: de ring-mode met n = 12 golven valt in ND 0
  (Mecway 1402,72 Hz, twee keer). `MODE_ITER_CYCL` gaf voor de tweede 1420,8 Hz
  (+1,3%), ook met 80 sectormodes en `PREC_AJUSTE` 1e-12 niet beter; de dubbele
  eigenwaarde in ND 6 (333,089 Hz) ging wel goed. Daarom rekenen CY-01/03 2 modes per
  ND (KNOWN_BUGS 61).
- **8 segmenten met knopen op de as**: `<EXCEPTION> ALGORITH14_95` (Code-Aster
  `ctetax.F90`: cos 45° − sin 45° = 0); met 6 en 12 segmenten niet. De bridge stopt
  dan met een ERROR (KNOWN_BUGS 61); CY-04 gebruikt 6 segmenten.
- **Mecway's voorbeeld Impeller** (17 segmenten om Y, 100 000 r/min, 66 hex20 + 21
  wedge15; niet in de suite, het bestand hoort bij Mecway): de 27 modes (ND 0 … 8)
  +0,01 … +0,92% t.o.v. Mecway, in dezelfde volgorde; zonder centrifugaalkracht
  +0,01 … +0,92%, en de sector **zonder** cyclische symmetrie (gewone modale route)
  +0,02 … +0,79%: een verschil in de (sterk gekromde) elementen, niet in de cyclische
  route (KNOWN_BUGS 62). Met 60 i.p.v. 20 sectormodes veranderde mode 1 met 1e-5.

### Akoestiek: holtemodes (AK)

Mecway A30 (*Acoustic Resonance 3D*) → `acoustic_modes_3d`: `PHENOMENE='ACOUSTIQUE'`,
`RIGI_ACOU`/`MASS_ACOU`, `CALC_MODES` ([Akoestiek.md](Akoestiek.md) §2). Module
`tests_akoestiek.py` (groep "Akoestiek", 7 cases), draaien met
`python run_verificatie.py AK`. Lucht c = 340 m/s; buis 1 × 0,1 × 0,1 m (eerste
dwarsmode 1700 Hz). De Mecway-waarden zijn headless berekend (`mw_solve.py`, Mecway 33,
interne solver) op dezelfde `.liml` en staan in de testmodule; ook de grootste ∣p∣ van
mode 1 en 2 (normering). Tolerantie: analytisch 0,5% (klaar-criterium S2), t.o.v. Mecway
1% (frequentie) en 0,1% (∣p∣).

| ID | Model | Referentie | Analytisch (grootste afwijking) | Mecway |
|---|---|---|---|---|
| AK-01 | buis gesloten-gesloten, hex20 20 × 1 × 1, geen drukknoop | f_n = n·c/(2L), n = 0…4; ∣p∣ mode 1 = c/√V | +0,011% (680 Hz); mode 1 2,9e-5 Hz; ∣p∣ 3400 exact | < 1e-13 |
| AK-02 | buis open-gesloten, *fluid pressure* 0 op de knopen van x = L | f_n = (2n − 1)·c/(4L), n = 1…5 | +0,017% (765 Hz) | < 1e-12 |
| AK-03 | buis open-open, hex8 50 × 1 × 1, *fluid pressure* 0 op beide eindvlakken (vlakselecties) | f_n = n·c/(2L), n = 1…4 | +0,016 / +0,066 / +0,15 / +0,26% | < 1e-13 |
| AK-04 | ruimte 1,0 × 0,7 × 0,4 m, hex20 10 × 7 × 4, harde wanden | f_lmn = c/2·√((l/Lx)² + (m/Ly)² + (n/Lz)²), 8 modes | ≤ +0,026% | < 4e-10 |
| AK-05 | buis van twee media (c = 340 / 680 m/s, elk 0,5 m), hex20 | k1·tan(k1L1) + k2·tan(k2L2) = 0 (druk en dp/dx continu) | ≤ +0,024% | – (Mecway: één materiaal) |
| AK-06 | AK-01 met wedge6 (40 hex8-blokken gesplitst) | als AK-01 | +0,36% (680 Hz) | < 1e-13 |
| AK-07 | AK-01 met tet4 (Kuhn-splitsing, 6 per blok) | als AK-01 | +0,31% (680 Hz) | < 1e-13 |

Waarnemingen:
- **Gelijk aan Mecway** op afronding na, ook de normering van het drukveld (pᵀMp = 1,
  M = ∫NᵀN/c² dV): beide gebruiken dezelfde lineaire/kwadratische elementen zonder
  extra's, dus dezelfde discrete eigenwaarden.
- **Lineaire elementen** (hex8, wedge6, tet4): de fout volgt Δf/f ≈ (kh)²/24 (AK-03:
  1,645e-4 gemeten en berekend voor n = 1); hex20 is bij 9 elementen per golflengte
  0,017% (AK-02).
- **Harde wanden:** mode 1 is de constante druk (~1e-5 Hz); `PLUS_PETITE` gaf daarbij
  `ALGELINE3_81`, de bridge zoekt rond een kleine negatieve frequentie (alarm
  `ALGELINE3_82`, onschuldig).
- **Dichtheid:** een buis van twee media met ρ = 1,2 / 12 kg/m³ gaf dezelfde frequenties
  als zonder dichtheid (248,98 Hz; met de dichtheidssprong is 306,47 Hz juist): de
  akoestische matrices van Code-Aster bevatten ρ niet. De bridge stopt daarom bij
  verschillende dichtheden met een ERROR ([Akoestiek.md](Akoestiek.md) §3.2).
- **Impedantie** (S2b): complexe modes, zie hieronder (AI).

### Akoestiek: impedantie, complexe modes (AI)

Mecway A30 met *Impedance* → `acoustic_modes_3d`: `RIGI_ACOU`/`MASS_ACOU` en per rand
`AMOR_ACOU` (`CELE_R = 1`), het kwadratische eigenwaardeprobleem (K + λC + λ²M)P = 0,
C = Σ ρ/Z ∫NNᵀdA, in de job met scipy (`aster_acoustic_complex.py`,
[Akoestiek.md](Akoestiek.md) §3.3). Module `tests_akoestiek_impedantie.py` (groep
"Akoestiek impedantie", 10 cases, 227 controles), draaien met
`python run_verificatie.py AI`. Lucht c = 340 m/s, ρ = 1,2 kg/m³ (ρc = 408 Pa·s/m);
buis 1 × 0,1 × 0,1 m, harde wand op x = 0, impedantie op x = L. Per mode de frequentie
f = Im λ/2π en de decay rate σ = −Re λ (de bridge-mode met λ het dichtst bij de
referentie), en de vorm als P(L)/P(0) (grootte en faseverschil; schaal-onafhankelijk).

Referenties: (a) **analytisch** (vlakke golven, zelf afgeleid uit p = cosh(λx/c) en de
randvoorwaarde ∂p/∂x = −ρλp/Z): tanh(λL/c) = −ρc/Z, dus
λₙ = (c/L)·(−artanh(ρc/Z) + iπn) — reële Z > ρc: fₙ = n·c/(2L), σ = (c/L)·artanh(ρc/Z);
Z < ρc: fₙ = (2n − 1)·c/(4L), σ = (c/L)·artanh(Z/(ρc)); Z → ∞: harde wand; Z = ρc: geen
wortel; P(L)/P(0) = cosh(λL/c); met een drukknoop op x = 0: tanh(λL/c) = −Z/(ρc).
(b) **Mecway 33 headless** (`mw_solve.py`) op dezelfde `.liml`: alle modes (f, σ) en
P(L)/P(0) van één mode. Tolerantie: 1% (klaar-criterium S2b) voor f en σ, 0,1% voor
∣P(L)/P(0)∣ en 0,05° voor de fase t.o.v. analytisch; t.o.v. Mecway 1% (f, σ), 1e-4
(∣P∣-verhouding) en 0,01° (fase).

| ID | Model | Analytisch (grootste afwijking) | Mecway (grootste afwijking) |
|---|---|---|---|
| AI-01 | Z = 2000 (5ρc), hex20 20 × 1 × 1 | n = 0…5 (n = 0 niet-oscillerend, f = 0, σ = 70,347 1/s): f ≤ 0,026%, σ ≤ 0,097% (850 Hz); ∣P(L)/P(0)∣ = 1,02148 op 2e-8, fase 3e-7° | ≤ 8e-11 |
| AI-02 | Z = 200 (< ρc) | fₙ = 85, 255, … 765 Hz: ≤ 0,017%; σ = 182,35 1/s ≤ 0,11%; ∣P(L)/P(0)∣ = 0,5624 (−90°) op 1e-8 | ≤ 4e-10 |
| AI-03 | Z = 1e9 (→ ∞) | fₙ = n·c/(2L) ≤ 0,011%, σ = (c/L)·ρc/Z = 1,39e-4 1/s ≤ 0,09%; f₂ = AK-01 (harde wanden, Mecway) op 3e-13 | f ≤ 2e-11; σ (1,4e-4 1/s) op 6e-8 1/s |
| AI-04 | Z = ρc = 408 | geen wortel: elke oscillerende mode dempt ≥ 10× sneller dan bij Z = 2000 (σ ≥ 1588 1/s, Q ≤ 1,51; discretisatiemodes) | ≤ 6e-9 (ook de discretisatiemodes) |
| AI-05 | Z = 2000 − 1000i | fₙ = 170n − 4,5 Hz ≤ 0,025%, σ = 55,60 1/s ≤ 0,097%; P(L)/P(0) op 5e-9, fase 7e-7° | ≤ 2e-10 |
| AI-06 | Z = 1000 + 3000i | fₙ = 170n + 6,60 Hz ≤ 0,026%, σ = 13,674 1/s ≤ 0,10% | ≤ 3e-9 |
| AI-07 | Z = 1000i (zuiver reactief) | fₙ = 170n + 20,96 Hz ≤ 0,028%, σ = 0 (≤ 1e-6) | ≤ 1e-11 |
| AI-08 | drukknoop op x = 0, Z = 2000 | fₙ = (2n + 1)·c/(4L) ≤ 0,037%, σ = 70,347 1/s ≤ 0,14% (935 Hz) | ≤ 3e-11 |
| AI-09 | Z = 2000, hex8 20 × 1 × 1 (168 vrijheidsgraden gelineariseerd: dicht, `scipy.linalg.eig`) | n = 0, 1: f +0,10%, σ +0,41%; ∣P(L)/P(0)∣ 4e-5 | ≤ 8e-8 (ook n = 2, 3: f +0,41/+0,93%, σ +1,7/+3,8% t.o.v. analytisch, mesh) |
| AI-10 | ruimte 1,0 × 0,7 × 0,4 m, hex20 10 × 7 × 4, vloer Z = 1000, plafond Z = 600 − 300i | – (3D) | 10 modes (maxmode 8: zoals Mecway de 2·8 kleinste \|λ\| met f ≥ 0): ≤ 3e-12; vorm hoek-hoek op 1e-12 |

Waarnemingen:
- **Gelijk aan Mecway** op afronding na (≤ 1e-8), ook de lijst modes op de 0-Hz-modes
  na: dezelfde matrices (`RIGI_ACOU`, `MASS_ACOU` = Mecway's K en M, AK) en dezelfde
  randterm C = ρ/Z ∫NNᵀdA met Z = R + iX. Mecway laat de constante druk (λ = 0) en
  niet-oscillerende modes door afrondingsruis wisselend weg (AI-01: wel de
  niet-oscillerende, niet de constante; AI-09 omgekeerd); de bridge geeft beide.
- **Decay rate en mesh:** σ is gevoeliger voor de mesh dan f (AI-09 hex8: bij 340 Hz f
  +0,41%, σ +1,7%); hex20 met 20 elementen per meter (≥ 8 per golflengte bij 850 Hz)
  ≤ 0,14%.
- **Reactantie:** X > 0 verhoogt de frequenties (AI-06, AI-07), zoals een massa op de
  rand bij e^{iωt}; geen demping bij Re Z = 0 (AI-07).
- **Zonder dichtheid** rekent Mecway met ρ = 0 (headless: Z = 2000 gaf de harde-wand-
  frequenties met σ ~1e-10); de bridge stopt dan met een ERROR (Akoestiek.md §4).
- Mecway kiest de 2 × maxmode eigenwaarden met de kleinste |λ| en toont die met f ≥ 0
  (headless nagegaan met maxmode 3, 6, 8 en 10); de bridge doet hetzelfde.
- Rekentijd: een ruimte van 13 000 knopen (hex20) met 20 modes 14 s (niet in de
  regressie).

### Responsspectrum (SP)

Mecway *Frequency* met een Gravity-tabel als spectrum → `spectrum_3d`: `CALC_MODES` →
(`MODE_STATIQUE` `PSEUDO_MODE`) → `COMB_SISM_MODAL` `MONO_APPUI` → maxima als één stap
([Spectrumanalyse.md](Spectrumanalyse.md)). Module `tests_spectrum.py` (groep
"Responsspectrum", 9 cases), draaien met `python run_verificatie.py SP` (ca. 1
minuut). Referenties: Code-Aster-testcase sdld25a (TEST_RESU) en handberekeningen
(eigenwaarden van 2 × 2-matrices, Γ_i = φ_iᵀM1, respons Γ_i·S_i/ω_i²·φ_i; CQC met
de correlatie van Der Kiureghian, 1981; Chopra, 2012, hoofdstuk 13), in de
testmodule nagerekend. Tolerantie: sdld25a 1% (klaar-criterium; de bridge haalt
1e-7), handberekening 0,5%, volumebalk t.o.v. Euler-Bernoulli 0,5% (verplaatsing,
versnelling), 1% (reactie), 2% (spanning, als MO-07).

| ID | Model | Referentie | Resultaat |
|---|---|---|---|
| SP-01 | sdld25a nagebouwd: 8 × 10 kg (`mass2`) tussen 9 veren van 1e5 N/m (Mecway *Spring*), Y/Z vast, Rayleigh β = 5e-4 s (= de dempers 50 N·s/m van sdld25a), spectrum = de `DEFI_NAPPE` van sdld25a via `#ASTER` + `#ASTER-SPECTRE X`, SRSS | TEST_RESU `VALE_CALC` van sdld25a: 8 frequenties (5,5274 … 31,347 Hz) en `ACCE_ABSOLU` DX in A, P1 … P4 (1,1364; 10,450; 19,030; 25,318; 28,945 m/s²) | frequenties ≤ 3e-14, versnellingen ≤ 3,5e-8 (enkele precisie van het resultaatbestand) |
| SP-02 | grond – k1 – m1 – k2 – m2 langs X (100 kg aan 1e5 N/m, 5 kg afgestemd op 1/(1+μ)): f = 4,393 / 5,491 Hz; spectrumtabel in de periode (0; 2), (0,1; 8), (0,3; 5), (2; 1) m/s², beide perioden op het schuine deel: S = 6,0855 / 6,7684 m/s²; SRSS | handberekening: u m1, u m2, reactie in de grond (Γ_i²·S_i), totale reactie uit de log, absolute versnelling m2 | ≤ 1e-6 (log: zes cijfers) |
| SP-03 | als SP-02, CQC (ρ₁₂ = 0,1656 bij ξ = 0,05) | idem met CQC | ≤ 1e-6; CQC t.o.v. SRSS: u m2 −6,5%, reactie +7,9% |
| SP-04 | als SP-02 met 1 mode en missing mass (standaard) | mode 1 plus de rest (ψ − Γ₁φ₁/ω₁²)·S(f₁), ψ = K⁻¹M1; reactie √((M_eff,1·S₁)² + ((M − M_eff,1)·S₁)²); versnelling met (1 − Γ₁φ₁)·S(f₁) | ≤ 4e-8 |
| SP-05 | als SP-04 zonder missing mass | alleen mode 1 (M_eff,1 = 56% van de massa) | ≤ 4e-8; de log geeft de WARNING onder 90% |
| SP-06a/b/c | 50 kg aan twee loodrechte veren onder 30° en 120° (2e5 en 5e4 N/m), spectra in X en Y (twee gravity-tabellen); modes SRSS, richtingen SRSS / 100-30-30 / 100-40-40 | handberekening per richting, daarna √(R_X² + R_Y²), max(R_a + 0,3 R_b), max(R_a + 0,4 R_b) | ≤ 4e-8 |
| SP-07 | ingeklemde volumebalk hex20 50 × 2 × 3 (als MO-07), vlak spectrum 1 m/s² in Y (gravity zonder tabel), 1 mode, zonder missing mass; frequentie uit de run | Euler-Bernoulli: f₁; u_tip·ω₁² = Γ₁φ₁(L)·S = 1,5660 S; σ_xx en von Mises halverwege = Γ₁·S/ω₁²·σ(φ₁); totale reactie M_eff,1·S = 0,6131 m·S; absolute versnelling tip | f₁ +0,20%, u_tip −0,02%, σ_xx +0,38%, von Mises +0,38%, reactie −0,12%, versnelling −0,02% |

Waarnemingen:
- De bridge geeft precies wat `COMB_SISM_MODAL` rekent; de handberekening volgt de
  formules van de macro (`comb_sism_modal_ops.py`) onafhankelijk na, ook voor de
  missing mass, de automatische restterm van `ACCE_ABSOLU` en 100-30-30 (die de
  bridge zelf rekent).
- Met de missing mass (standaard) is de reactie in de grond compleet, ook met 1 van
  de 2 modes (SP-04: 454,6 N; zonder missing mass 355,0 N; met beide modes SRSS
  475,2 N).
- Mecway leest het resultaat (één stap onder een *Frequency*-analyse) via de API
  (headless `mecway.exe <model> script`: `node_value` geeft de waarden, `modes()` en
  `time_steps()` zijn leeg). De weergave in de Mecway-GUI is NIET geverifieerd.

### Akoestiek: harmonisch drukveld (AH)

Mecway A30-model → `acoustic_harm_3d`: `PHENOMENE='ACOUSTIQUE'`, `RIGI_ACOU`/`MASS_ACOU`/
`AMOR_ACOU`, `DYNA_VIBRA` `HARM` ([Akoestiek.md](Akoestiek.md) §5). Module
`tests_akoestiek_harmonisch.py` (groep "Akoestiek harmonisch", 10 cases, 103
controles), draaien met `python run_verificatie.py AH`. Lucht ρ = 1,2 kg/m³, c = 340
m/s; buis 1 × 0,1 × 0,1 m langs x, bron `BRON_Zuiger` op x = 0 (1 mm/s, de fluid in),
controle langs de as y = z = 0. Referenties: 1D Helmholtz met p(t) = Re(P e^{iωt}),
k = ω/c (afgeleid in de testmodule) en testcase ahlv100a (TEST_RESU). Tolerantie: 1%
(klaar-criterium S3a), hex8 bij 10 per golflengte 2%.

| ID | Model | Referentie | Resultaat (grootste afwijking) |
|---|---|---|---|
| AH-01 | absorberend einde (`ABSORBEREND_`), hex20 20 × 1 × 1; 100/340/680 Hz (680 Hz: 10 elementen per golflengte) | \|P\| = ρcv0 = 0,408 Pa, faseval kL | \|p\| −0,018%, fase −0,011% (680 Hz); SPL 83,182 dB exact |
| AH-01b | als AH-01, hex20 10 × 1 × 1 (5 per golflengte bij 680 Hz) | idem | \|p\| −0,25%, fase −0,16% |
| AH-02a | als AH-01, hex8 20 × 1 × 1 (10 per golflengte) | idem | \|p\| +1,7%, fase −1,6% (≈ (kh)²/24); tolerantie 2% |
| AH-02b | als AH-01, hex8 40 × 1 × 1 (20 per golflengte) | idem | \|p\| +0,41%, fase −0,41% |
| AH-03 | harde wand op x = L, hex20; 100/250/420 Hz (resonanties 170/340/510) | P = −iρcv0·cos(k(L−x))/sin(kL) | \|P − P_exact\| ≤ 1,2e-4·max\|P\| (420 Hz) |
| AH-04 | ahlv100a nagebouwd: 1 × 0,1 × 0,2 m, hex20 15 × 2 × 2, ρ 1,3, c 343, 0,014 m/s, 500 Hz | TEST_RESU van ahlv100a in NO1, NO780, NO751, NO763 (teken omgekeerd: VNOR de fluid in) | VALE_REFE: Re −0,025%, Im +0,33% (ahlv100a zelf ook; PRECISION 3,3e-3); VALE_CALC: Re ≤ 2,2e-7, Im ≤ 3e-7 Pa; SPL + 3,0103 = 109,8866 dB (DB van ahlv100a) |
| AH-05 | idem, holtemodes (`acoustic_modes_3d`, harde wanden) | CALC_MODES-deel van ahlv100a, 8 modes | VALE_CALC ≤ 2e-8; analytisch ≤ +0,38% (dwarsmode 6) |
| AH-06 | Mecway *impedance* Z = 2ρc = 816 Pa·s/m op x = L, hex20; 100/250 Hz | R = (Z − ρc)/(Z + ρc) = 1/3, P = A(e^{−ikx} + R e^{−ik(2L−x)}) | \|P − P_exact\| ≤ 6,9e-6·max\|P\|; max/min langs de as 1,994 (2 tussen de knopen) |
| AH-07 | *fluid pressure* 2 Pa op x = 0 (opgelegde druk), absorberend einde; 170/500 Hz | P = 2 e^{−ikx} | \|p\| ≤ 5e-5, fase ≤ 3e-5 |
| AH-08 | `#ASTER-BRON Luidspreker = 2 mm/s, 90` (vlakselectie zonder voorvoegsel), frequenties met `#ASTER-OPTIE harm_freq_list`, microfoons `MICROFOON_Eind` (1 knoop) en `MICROFOON_Midden` (8 knopen) | P(0) = iρcv, SPL 89,203 dB, fase 90° − kL | Im p(0) −2e-6, Re p(0) ≤ 1e-5 Pa; SPL ≤ 3e-4 dB; fase ≤ 0,017° |

Waarnemingen:
- **Tekenafspraak:** met `EXCIT` `COEF_MULT=+1, PUIS_PULS=1, PHAS_DEG=90` (iω·v) geeft
  `VITE_FACE` p = +ρcv op de bron: v is de snelheid de fluid in. ahlv100a gebruikt −1
  (v naar buiten) en heeft daardoor −6,2426 Pa op de bron; de bridge-waarden zijn op
  afronding na het tegengestelde (AH-04).
- **Absorberende rand en impedantie:** `3D_ABSO` legt (1/c)∫NNᵀdA op met de c van het
  materiaal van het vlak, zonder ρ (gemeten); Mecway's impedantie Z wordt daarmee een
  eigen materiaal met c = Z/ρ (AH-06 exact op discretisatie na).
- **Mesh:** hex20 heeft bij 5 elementen per golflengte nog 0,25%; hex8 ijlt na met
  ≈ (kh)²/24 per golflengte (1,6% bij 10, 0,41% bij 20), en de kleine
  impedantiefout van de discrete golf geeft een lichte staande golf (\|p\| +1,7% bij
  10). Vandaar de WARNING onder 10 (lineair) / 5 (kwadratisch) per golflengte.
- **SPL:** de bridge rekent met de effectieve waarde (\|P\|/√2); Code-Aster's `PRAC_ELNO`
  DB met \|P\| zelf, 3,0103 dB hoger (AH-04 = ahlv100a op 2e-8).
- **Mecway:** Mecway heeft geen harmonische akoestiek, dus geen vergelijking met een
  Mecway-oplossing. Mecway's API leest het resultaat van AH-08 (headless script:
  `solution.modes()` = [1, 2], `frequency` 200/500 Hz, `node_value` van `pressure`,
  `pressurei`, `pressuremag`, `pressurephase`, `spl` gelijk aan de bridge-waarden); de
  GUI-weergave is NIET bekeken (KNOWN_BUGS 57).

### Vibro-akoestiek (VA)

Mecway *Frequency* (V30) met een fluïdum-onderdeel → `vibroacoustic_modes_3d`:
`3D_FLUIDE` + `FLUI_STRU` + de constructie, `FORMULATION='U_P_PHI'`, `INFO_MODE` +
`CALC_MODES` `BANDE` ([Akoestiek.md](Akoestiek.md) §6). Module
`tests_vibroakoestiek.py` (groep "Vibro-akoestiek", 8 cases, 29 controles), draaien met
`python run_verificatie.py VA` (ca. 2 minuten). Referenties: 1D-golfvergelijking in
een kolom met harde zijwanden, met de randvoorwaarden afgeleid in de testmodule (de
wortels met bisectie), testcase adlv100a (VALE_REFE), Kirchhoff-plaat (Leissa §4.1) en
de holtemodes f_lmn. Tolerantie: adlv100a 0,5% (klaar-criterium S3b), het tweede
analytische geval 1% (klaar-criterium), verder 0,1–1%.

| ID | Model | Referentie | Resultaat |
|---|---|---|---|
| VA-01 | adlv100a nagebouwd: water 0,05 m (vrij oppervlak, `OPEN_Vrij`), stalen zuiger 0,025 m (zijdelings geleid), lucht 0,075 m (gesloten), doorsnede 0,05 × 0,05 m; hex20 4 + 1 + 6 | adlv100a VALE_REFE 13,8285 Hz; exacte wortel van m + ρ1·tan(k1L1)/k1 − ρ2·cot(k2L2)/k2 = 0 (13,82768 / 2266,75 Hz); p/u op beide zuigervlakken | f1 −6,0e-5 t.o.v. adlv100a, −9,8e-7 t.o.v. de wortel; f2 +5,1e-5; p/u lucht −1,9e-6, water −2,0e-6 |
| VA-01k | als VA-01, koppelvlakken als `KOPPEL_`-vlakselecties | idem | gelijk aan VA-01 |
| VA-02 | elastische staaf (E 3 GPa, ρ 1400, ν 0, Zs/Zf = 1,38) 0,5 m, ingeklemd en zijdelings geleid, + gesloten waterkolom 1 m; hex20 10 + 20 | Zs·cot(ksLs) + Zf·cot(kfLf) = 0 (513,85 / 960,19 / 1475,68 / 1987,83 Hz) | ≤ +2,4e-5 (mode 4) |
| VA-03 | schaalzuiger (DKT quad4 2 × 2, t = 10 mm, translatie x vrij, rotaties vast) op een gesloten luchtkolom 0,5 m; hex8 50 × 2 × 2 | m·k·tan(kL) = ρ (9,480 / 340,26 / 680,13 Hz) | +2e-7 / +1,6e-4 / +6,6e-4 (hex8: (kh)²/24) |
| VA-04 | buis van twee media (c 340 / 680 m/s, gelijke dichtheid), alleen fluïdum; hex20 10 + 10 | tan(k1L1)/Z1 + tan(k2L2)/Z2 = 0 (248,98 / 431,02 / 680 Hz) | ≤ +8,6e-5 |
| VA-05 | stalen plaat 0,5 × 0,4 m, 2 mm, vrij opgelegd (DKT 30 × 24) op een gesloten luchtholte 0,5 × 0,4 × 0,3 m (hex8 30 × 24 × 12), lucht 1000× lichter | ongekoppeld: plaat in vacuüm (Leissa §4.1) en holte met harde wanden, 8 modes in volgorde | plaat −0,09 … −0,61% (DKT-discretisatie, 20 × 16 gaf nog −1,35% voor (3,2)), holte (1,0,0) +0,045% |
| VA-05b | als VA-05 met gewone lucht | pompmode (1,1) met de luchtveer, één mode: ω² = ω0² + ρc²(∫φ dA)²/(V·M) (benadering) = 55,23 Hz | −0,48% (54,96 Hz; in vacuüm 50,52 Hz) |
| VA-05c | als VA-05b, `#ASTER-OPTIE vibro_freq_min = 100`, 3 modes | plaatmodes (2,1), (1,2), (2,2) in vacuüm; lucht + discretisatie < 1% | −0,66 / −0,52 / −0,69% |

Waarnemingen:
- **Formulering en eigenwaarden:** `U_P_PHI` geeft per vrijheidsgraad φ een valse
  mode bij 0 Hz (adlv100a-mesh: 40, `MASS_GENE` < 0); `PLUS_PETITE` stopt met
  `ALGELINE3_81`, `CENTRE` geeft eerst de valse modes. De Sturm-telling van
  `INFO_MODE` boven 0 Hz klopt (VA-02: 6 van 6 modes tot 3 kHz in een losse run), dus
  `BANDE` vanaf `vibro_freq_min` geeft alleen de echte modes. `U_P` gaf met
  `PLUS_PETITE` een verkeerde reeks (1147 Hz als eerste mode van adlv100a) en met
  `CENTRE` `<F> JEVEUX_26`; niet gebruikt.
- **Dichtheid:** zit in de matrices: VA-02 met ρ_water 1 i.p.v. 1000 gaf de eigen
  analytische wortels (726,19 / 745,74 Hz …; losse run). Twee fluïda met een
  verschillende dichtheid en gedeelde knopen geven een fout resultaat (buis ρ 1,2/12:
  188,23 Hz, analytisch 306,47 Hz; φ is continu): de bridge stopt dan met een ERROR;
  met gelijke dichtheid is het exact (VA-04).
- **Koppeling en teken:** p/u op beide zuigervlakken klopt op 2e-6 (VA-01): de
  normaal van de koppelvlakken (uit het fluïdum, `ORIE_PEAU`) en het teken van de
  druk zijn goed; de koppeling werkt ook via een schaal (VA-03, VA-05).
- **Robuustheid:** een schaal waarvan maar één rotatie vastlag (kantelmechanisme) gaf
  in een losse run een valse mode bij 3e-5 Hz met `MASS_GENE` < 0 in de `BANDE`-
  uitvoer; normeren gaf `DVP_2`. De bridge filtert nu eerst (f ≥ ondergrens, massa >
  0) en meldt een tekort aan modes (WARNING).
- **Mecway:** Mecway rekent een materiaal zonder Young's modulus als vaste stof met
  E = 0 (headless: modes van 1e-7 Hz), dus geen vergelijking. Mecway's API leest het
  resultaat van VA-01 (headless script: `modes()` = [1, 2], `frequency` 13,8277 /
  2266,87 Hz, `displx` op de zuigerknopen en `pressure` op de fluïdumknopen; op een
  koppelvlakknoop beide, p/u = 1,849e6 Pa/m). De GUI-weergave is NIET bekeken
  (KNOWN_BUGS 59).

### Vibro-akoestiek harmonisch (VH)

Hetzelfde Mecway-model als VA, nu per frequentie → `vibroacoustic_harm_3d`:
`3D_FLUIDE` + `FLUI_STRU` + `3D_FLUI_ABSO`, `U_P_PHI`, `DYNA_VIBRA` `HARM` `PHYS` met
`MATR_IMPE_PHI` ([Akoestiek.md](Akoestiek.md) §7). Module
`tests_vibroakoestiek_harmonisch.py` (groep "Vibro-akoestiek harmonisch", 13 cases, 175
controles), draaien met `python run_verificatie.py VH` (ca. 1 minuut). Referenties: de
testcases ahlv101a en ahlv100b (TEST_RESU, nagebouwd op het mesh van AH-04) en de
1D-golfvergelijking met een stijve zuiger (massa m, veer k, kracht F) op een kolom:
U = F/(k − mω² + iω(c_s + A·Z_in)), Z_in = ρc bij een ρc-einde en ρc(1 + R e^{−2ikL})/(1 −
R e^{−2ikL}) bij een impedantie Z, P(x) uit de zuigersnelheid (afgeleid in de
testmodule). Tolerantie: ahlv101a/ahlv100b de PRECISION 1e-3 van VALE_REFE en 1e-6 van
VALE_CALC, verder 1% (klaar-criterium S3c) en 0,5° in de fase. Zuiger: lucht ρ 1,2, c 340,
kolom 1 × 0,1 × 0,1 m (hex20 10 × 1 × 1), zuiger hex20 10 mm (ρ 500: m = 0,05 kg,
zijdelings geleid), veer k = 3000 N/m (f0 = 38,98 Hz), F = 1 N, ρcA = 4,08 N·s/m (ζ =
0,17); frequenties 5, 20, 35, 39, 45, 60, 100, 200 Hz.

| ID | Model | Referentie | Resultaat (grootste afwijking) |
|---|---|---|---|
| VH-01 | ahlv101a nagebouwd: 1 × 0,1 × 0,2 m, hex20 15 × 2 × 2, ρ 1,3, c 343; `INVALLEND_Inlaat` (`incident_pressure` 0,5 Pa = `ONDE_FLUI` `PRES` 1), `ABSORBEREND_Uitlaat`, 500 Hz | TEST_RESU van ahlv101a in NO1, NO780, NO751, NO763 (P = 0,5·e^{−ikx}) | VALE_REFE ≤ 8,0e-4 (NO751, ahlv101a zelf ook); VALE_CALC ≤ 1,3e-7; SPL microfoon 84,9485 dB (exact op 3e-7 dB) |
| VH-01b | ahlv100b nagebouwd: idem met `BRON_Inlaat` (`source_velocity` 0,014 m/s) | TEST_RESU van ahlv100b (teken omgekeerd: VNOR de fluid in) | VALE_REFE ≤ 8,9e-4; VALE_CALC ≤ 2,3e-7 |
| VH-07 | als VH-01b met `#ASTER-BRON Inlaat = 14 mm/s, 90` (vlakselectie zonder voorvoegsel), frequentie uit `#ASTER-OPTIE` | ahlv100b VALE_CALC × i | ≤ 2,3e-7; fase microfoon −74,73° exact |
| VH-08 | als VH-01 met `#ASTER-BRON Inlaat = 0.5 Pa, -30` (druk = invallende golf) | ahlv101a VALE_CALC × e^{−i30°} | ≤ 1,1e-7 |
| VH-02 | zuiger met ρc-einde (`ABSORBEREND_`), microfoon x = 0,5 m, meetpunt op de zuiger; spanningen in de zuiger | U = F/(k − mω² + iωρcA), P = iωρcU·e^{−ikx} | U ≤ 1,3e-4, fase ≤ 6,8e-4°, P ≤ 2,9e-5; SPL (CSV) in de piek −4e-5 dB, \|U\| (CSV) −9e-6 |
| VH-02t | als VH-02, kracht uit een Mecway-tabel F(f) = 1 + f/100 N, `#ASTER-FASE Last = 90` | U·F(f)·i | ≤ 1,3e-4 |
| VH-03 | als VH-02 met Mecway *impedance* Z = 2ρc op x = L | Z_in met R = 1/3 | U ≤ 1,2e-4, fase ≤ 7,4e-4°, P ≤ 1,7e-5 (Z verandert U in de piek 7%) |
| VH-04 | als VH-02 met Rayleigh α = 200 1/s | c_s = αm = 10 N·s/m (alleen de constructie) | U ≤ 1,3e-4, fase ≤ 1,5e-3°, P ≤ 2,9e-5 |
| VH-04b | als VH-02 met Rayleigh β = 2e-3 s | c_s = βk = 6 N·s/m (de starre zuiger vervormt niet) | U ≤ 4,5e-5, fase ≤ 2,4e-3°, P ≤ 2,8e-5 |
| VH-04c | als VH-02 met een Mecway-demper 10 N·s/m parallel aan de veer | c_s = 10 N·s/m | U ≤ 1,2e-4, fase ≤ 7,2e-4°, P ≤ 1,6e-5 |
| VH-05 | alleen lucht, hex20 20 × 1 × 1, `INVALLEND_Inlaat` (1 Pa), harde wand op x = L; 100/250/420 Hz | P = e^{−ikx} + e^{−ik(2L−x)} (de inlaat laat de teruggekaatste golf door) | ≤ 1,2e-4 van max\|P\| |
| VH-05b | idem met `OPEN_Einde` (p = 0) | P = e^{−ikx} − e^{−ik(2L−x)} | ≤ 1,2e-4 |
| VH-06 | schaalzuiger (DKT quad4 2 × 2, t = 10 mm, ρ 500, rotaties vast) met veer, lucht hex8 20 × 2 × 2; 5/39/100/200 Hz | zoals VH-02 | U ≤ 2,5e-4, P ≤ 3,4e-3 (hex8, 34 per golflengte bij 200 Hz) |

Waarnemingen:
- **Invallende golf:** `ONDE_FLUI` met `PRES` geeft een golf `PRES`/2 het fluïdum in
  (randvoorwaarde ∂p/∂n + ikp = ik·`PRES`) en laat de teruggekaatste golf zonder
  reflectie door (VH-05/05b exact op discretisatie na); de bridge schrijft `PRES` = 2 ×
  `incident_pressure`, zodat de instelling de amplitude van de binnenlopende golf is.
- **Teken:** `VITE_FACE` in `U_P_PHI` met `COEF_MULT=+1` geeft p = −ρcv (ahlv100b:
  `VNOR` naar buiten); de bridge gebruikt −1 (v de fluid in; VH-01b, VH-07). In de
  akoestiek (`ACOUSTIQUE`, AH) is het omgekeerd: daar geeft +1 al p = +ρcv.
- **Impedantie:** `IMPE_MECA` van `3D_FLUI_ABSO` hoort bij Z = ρ·c van het materiaal van
  het vlak; een eigen materiaal met `CELE_R = Z/ρ` geeft de juiste ingangsimpedantie
  (VH-03).
- **Demping:** Rayleigh via `RIGI_MECA`/`MASS_MECA` met `GROUP_MA` van de constructie
  (VH-04/04b); `AMOR_MECA` met `GROUP_MA` stopte met `DVP_1`, zonder `GROUP_MA` (met
  `AMOR_FLUI='NON'`) klopt de demper (VH-04c). `IMPE_MECA` weigert `CARA_ELEM`
  (`SUPERVIS_4` met een veer in het model): eigen `ASSEMBLAGE` zonder `CARA_ELEM`.
- **Mesh:** hex20 10 per golflengte geeft ≤ 1,3e-4 (VH-02 bij 200 Hz: 17 per
  golflengte); de schaalzuiger met hex8-lucht ≤ 3,4e-3 (VH-06), zoals AH-02.
- **Mecway:** geen vergelijking (Mecway heeft geen gekoppelde of harmonische analyse).
  Mecway's API leest het resultaat van VH-02 (headless script: `modes()` = 1..8,
  `frequency` 5…200 Hz, `node_value` van `displx`/`displix` op de zuiger en
  `pressure`/`pressurei`/`spl` in de kolom); de GUI-weergave is NIET bekeken (KNOWN_BUGS
  59).

## 8. Thermisch (TH)

Bridge `ther_3d`: Mecway T30 → `THER_LINEAIRE` stationair, T31 → `THER_LINEAIRE`
transient, convectie op een schaalvlak → `THER_NON_LINE`; TH-03 met `lin_static_3d` en
`<thermalstress>` (`AFFE_VARC TEMP`). Module `tests_thermisch.py`, draaien met
`python run_verificatie.py TH` (groepen "Thermisch" en "Thermische spanning" in
`resultaten.md`). Gebruikersdocumentatie: [Thermisch.md](Thermisch.md). Lassen
(bewegende bron, temperatuurafhankelijk materiaal, formules): WE hieronder.

### TH-01 Stationaire geleiding

- **Doel**: `THER_LINEAIRE` stationair, `temperature2` (`TEMP_IMPO`), `heatgeneration`
  (`SOURCE`), `convectionbc` (`ECHANGE`), de warmteflux (`FLUX_NOEU`) en thermische
  schalen (`PLAN` met diktefactor).
- **Model en belasting**:
  - TH-01a: wand 0,1 m, q = 1e6 W/m³, beide zijden 300 K, hex8 (8 elementen);
  - TH-01b: idem, hex20 (2 elementen);
  - TH-01c: 400 K links, convectie h = 250 W/m²K naar T∞ = 300 K rechts (Bi = 0,5);
  - TH-01d: q = 1e6 W/m³, x = 0 geïsoleerd, convectie h = 500 W/m²K (Bi = 0,5);
  - TH-01e: vin als schaal 2 mm (10 quad8), convectie h = 25 W/m²K op het vlak, voet
    400 K.
- **Referentie** (Incropera e.a., 2007, §3.1, 3.5 en 3.6.2): T_max − T0 = qL²/8k = 25 K
  en de flux bij L/4 (a) of x = 0 (b); serieschakeling L/k + 1/h: T(L) = 366,67 K,
  q = 16 667 W/m² (c); Ts = T∞ + qL/h = 400 K, T(0) − Ts = qL²/2k = 25 K (d); vin met
  geïsoleerd uiteinde (T − T∞)/(T0 − T∞) = cosh m(L−x)/cosh mL, m = √(h/kt) (e).
- **Resultaat**: (a–d) relatieve afwijking ≤ 9e-14 (tolerantie 1e-5); (e) 6e-7
  (tolerantie 1e-3).
- **Interpretatie**: een temperatuurveld dat alleen van x afhangt, is in een
  gestructureerd hex8-blok de oplossing met lineaire 1D-elementen; Galerkin geeft voor
  −kT'' = q exacte knoopwaarden, ook met een convectierand, en hex20 is exact voor een
  kwadratische T. Het knoopgemiddelde van de flux bij twee gelijke elementen is het
  centrale verschil, exact voor kwadratische T. De tolerantie is dus alleen afronding.
  TH-01e: mL = 1,58 en 10 quad8 geven een discretisatiefout ~(mh)⁴ < 1e-4; dit
  controleert ook de diktefactor (`PLAN`, f = t) en de convectie op het schaalvlak
  (`SOUR_NL`, `THER_NON_LINE`).

### TH-02 Transient: half-oneindig lichaam

- **Doel**: `THER_LINEAIRE` transient: θ-schema (instelling `theta`), tijdstap,
  ρ·cp, begin- en randtemperatuur.
- **Model**: staaf 0,1 m, 100 hex8-elementen (h = 1 mm, doorsnede 2 × 2 mm, zijvlakken
  geïsoleerd), λ = 10 W/mK, ρ = 1000 kg/m³, cp = 1000 J/kgK (α = 1e-5 m²/s);
  begintemperatuur Ti = 300 K, randtemperatuur Ts = 400 K op x = 0 vanaf t = 0 (de staaf
  is lang genoeg om half-oneindig te zijn). TH-02a/b/c: θ = 0,57 / 0,5 / 1,0 bij Δt = 0,1 s; TH-02d–f: Δt = 0,4 /
  0,2 / 0,05 s bij θ = 0,5 en 1,0; TH-02g/h/i: grove stap Δt = 1 s (Δt·α/h² = 10),
  θ = 0,5 / 0,57 / 1,0.
- **Referentie**: T − Ti = (Ts − Ti)·erfc(x/2√(αt)) (Carslaw & Jaeger, 1959, hfdst. 2;
  Incropera e.a., 2007, §5.7), op t = 10 en 40 s (a–f) of 4 s (g–i). Daarnaast een
  replica: `_fe1d_theta` rekent hetzelfde discrete probleem in 1D (lineaire elementen,
  consistente massa, θ-methode, T(0) = Ts vanaf de eerste stap).
- **Resultaat**: grootste afwijking t.o.v. erfc 0,12 K (a–c, tolerantie 0,5 K), 0,51 K
  (d–f, Δt = 0,4 s, θ = 1; tolerantie 1 K) en 3,1 K (g–i, tolerantie 5 K). Verschil met
  de replica ≤ 1,3e-5 K in alle 15 cases (tolerantie 1e-4 K).
- **Interpretatie**: de replica bewijst dat θ, Δt, ρ·cp, λ en begin- en
  randtemperatuur exact zo in de `.comm` staan; de tolerantie 1e-4 K volgt uit de
  enkele precisie waarin de bridge transiente resultaten schrijft (ulp bij 380 K =
  3e-5 K). De afwijking t.o.v. erfc is schemafout: de sprong van de randtemperatuur op
  t = 0 wordt over de eerste stap uitgesmeerd (orde Δt, ≤ 0,25 K bij Δt = 0,1 s); de
  ruimtefout bij h = 1 mm is < 0,02 K. De toleranties 0,5 / 1 / 5 K zijn met hetzelfde
  1D-schema geschat.

**Effect van θ** (instelling `theta`):

| θ | T − Ti bij 8 mm, 10 s (Δt 0,1 s; ref. 57,161 K) | T − Ti bij 1 mm, 4 s (Δt 1 s; ref. 91,10 K) |
|---|---|---|
| 0,5 (Crank-Nicolson, = Mecway) | 57,070 | 93,89 (overschiet +2,8 K) |
| 0,57 (standaard bridge en Code-Aster) | 57,065 | 91,71 |
| 1,0 (Euler impliciet) | 57,037 | 90,16 |

- Met een kleine stap (Δt·α/h² = 1) maakt θ weinig uit: de fout wordt bepaald door de
  sprong op t = 0 en convergeert met orde 1 in Δt voor alle θ (gemeten p = 0,97–1,13,
  tabel "Mesh-convergentie" in `resultaten.md`), ook voor Crank-Nicolson, dat voor
  gladde problemen orde 2 heeft.
- Met een grove stap (Δt·α/h² = 10) overschiet Crank-Nicolson vlak bij het oppervlak
  (geen discreet maximumprincipe); θ = 0,57 dempt dat, θ = 1 is monotoon maar trager.
  Dat is schemagedrag, geen fout van de bridge (de replica geeft dezelfde waarden).
- Mecway rekent Crank-Nicolson met de belasting op het einde van de stap; bij een
  constante randtemperatuur is dat gelijk aan θ = 0,5 ([Thermisch.md](Thermisch.md) §5).
  Wie Mecway exact wil volgen, kiest `theta` = 0,5; de standaard 0,57 is iets gedempt.

### TH-03 Thermische spanning

- **Doel**: een temperatuurveld als belasting in een mechanische analyse
  (`<thermalstress>`, `AFFE_VARC TEMP`, `ALPHA`).
- **Model**: staaf van 4 hex8-elementen, uniforme opwarming ΔT = 100 K t.o.v. de
  referentietemperatuur, α = 1,2e-5 1/K.
- **Randvoorwaarden**: symmetrievlakken x = 0, y = 0 en z = 0 (TH-03a: verder vrij);
  TH-03b ook x = L vast in x (ingeklemd in x, dwars vrij).
- **Referentie** (Timoshenko & Goodier, 1970): (a) u = αΔT·L, σ = 0; (b)
  σ_xx = −EαΔT = −252 MPa, u_y = (1+ν)αΔT·b, reactie EαΔT·A.
- **Resultaat**: verplaatsingen, σ_xx en reactie ≤ 3e-15 relatief (tolerantie 1e-6);
  restspanning ≤ 1,2e-6 Pa (tolerantie 252 Pa = 1e-6·EαΔT).
- **Interpretatie**: een uniforme rek en spanning zijn exact met hex8; `ALPHA`, de
  referentietemperatuur en het temperatuurveld zijn juist vertaald.

### TH-04 Verlijmd contact in een thermische analyse

- **Doel**: Mecway *Bonded contact* (`contact2`) in T30: *Tie* / *Constraint equations*
  → `AFFE_CHAR_THER` `LIAISON_MAIL`, *Elastic* (thermische weerstandslaag) →
  `ECHANGE_PAROI` (voorheen ging er zonder melding geen warmte over de naad).
- **Model**: staaf 0,1 × 0,01 × 0,01 m uit twee hex8-blokken met eigen knopen (x = 0..0,05
  en 0,05..0,1 m), λ = 50 W/mK, verlijmd op x = 0,05 m (master blok A), 300 K links en
  400 K rechts, zijkanten geïsoleerd. TH-04a: *Tie*, 5 × 1 × 1 elementen per blok
  (conform); TH-04b: *Constraint equations*, naad 2 × 2 (master) tegen 3 × 3 (slave);
  TH-04c: *Elastic*, h = 2000 W/m²K (`<conductanceperarea>`), conform; TH-04d: twee
  schaalstroken (quad4, 2 mm, `PLAN`) in één vlak, rand van B op de laatste kolom van A,
  3 tegen 4 knopen op de naad.
- **Referentie** (Incropera e.a., 2007, §3.1): T lineair, 350 K op de naad, q =
  −k dT/dx = −50 000 W/m² (a, b, d); weerstanden in serie L/2k + 1/h + L/2k: q =
  40 000 W/m², 340 / 360 K aan beide kanten van de naad (c).
- **Resultaat**: (a, c) relatieve afwijking ≤ 1e-14 (tolerantie 1e-6); (b) naad 350,067 K,
  flux −50 083 W/m² (+0,17 %); (d) naad 350,036 K, flux −0,04 % (tolerantie 0,1 % op T,
  0,5 % op de flux).
- **Interpretatie**: conform is de knoop-op-vlak-koppeling exact. Niet-conform is ze niet
  conform in de FEM-zin (tussen de slave-knopen een kleine sprong), dus ook een lineair
  veld niet exact; Mecway 34 (interne solver, zonder GUI) rekent dezelfde koppeling:
  verschil per knoop 0,0024 K (b) en 0,0056 K (d). Mecway's interne solver gaf voor *Tie*
  (a) en *Elastic* (c) géén koppeling (300 / 400 K); met de CCX-solver 350 K (a) en
  340,0 / 360,0 K, flux −39 998 W/m² (c), gelijk aan de bridge. Volumes en schalen samen
  in één model kan Code-Aster thermisch niet koppelen (CHARGES7_6 / CHARGES6_2, ERROR;
  [Thermisch.md](Thermisch.md) §3).

### TH-40 .. TH-42 Meer warmtebronnen met een formule of tijdstabel

- **Doel**: Code-Aster 17.4 rekent twee lasten `AFFE_CHAR_THER_F` met `SOURCE` in één
  analyse allebei met de functie van de eerste last. De bridge zet alle functiebronnen
  in één last, met per deel van het mesh een `FORMULE` met de som van de bronnen die er
  liggen ([Thermisch.md](Thermisch.md) §3). Voor de oplossing gaven TH-40 en TH-41
  37,50 i.p.v. 39,58 K en 4,00 i.p.v. 2,75 K (twee of drie keer de eerste bron).
- **Model**: wand 0,1 × 0,01 × 0,01 m, 10 hex8 in x, λ = 50 W/mK, zijkanten geïsoleerd.
  TH-40 (T30): 300 K op x = 0 en L; drie *Internal heat generation*s als formule:
  5e5 W/m³ op alles, 2e7·x W/m³ op de linkerhelft, 1,5e6 W/m³ op de rechterhelft (twee
  delen met een som-`FORMULE`). TH-41 (T31, 2 s, stap 0,1 s, `theta` 0,5): overal
  geïsoleerd, 2e6·t W/m³ (formule) links en een tijdstabel 0 → 1e6 W/m³ (0..1 s), daarna
  constant, rechts (ρc = 1e6 J/m³K; twee `SOURCE`-regels zonder overlap). TH-42 (T31,
  2 s): blok 40 × 10 × 10 mm (hex8 1 mm, ρc = 4,68e6 J/m³K) met een
  `#ASTER-LASBRON` (Gauss r = 2 mm, Q = 100 W, `symmetrie=1`) en een tijdstabel
  0 → 2e7 W/m³ op het hele blok, samen in de last `lasbron`.
- **Referentie**: TH-40: T(x) − T0 = 1/k ∫ G(x, s) q(s) ds met de Green-functie van de
  wand (Incropera e.a., 2007, §3.5); met lineaire elementen zijn de knoopwaarden in 1D
  exact (Strang & Fix §1.2). TH-41/42: energiebalans ρc ∫(T − T0) dV = ∫∫ q dV dt;
  met θ = 0,5 en q lineair per stap is het schema exact, en ∫T dV volgt exact uit de
  knoopwaarden (consistente capaciteit). TH-42: de energie van de lasbron uit zijn eigen
  energiecontrole (`BRIDGE_LASBRON`, opgenomen vermogen 50,0001 W = Q/2).
- **Resultaat**: TH-40 relatieve afwijking ≤ 2,2e-13 (tolerantie 1e-5); TH-41 0
  (tolerantie 1e-4); TH-42 restterm van de energiebalans −2e-6 J (tolerantie 0,18 J),
  gemiddelde stijging 9,61539 K (+1,0e-6).
- **Mecway** (34, interne solver, zonder GUI): TH-40 verschil per knoop 2e-12 K. TH-41
  0,2 K: Mecway neemt de last op het einde van de stap (KNOWN_BUGS 14); zijn gemiddelde
  stijging 2,875 K is precies de som van dat schema (2,75 K exact). Ook een scratch-model
  met drie schaalvlak-fluxen (formule, tabel en overlappend, `SOURCE` q/t) gaf exact 2,0
  K, Mecway 2,075 K (zelfde verklaring).
- **Ook nagegaan** (Code-Aster 17.4, scratch-runs): twee functielasten met `FLUX_REP`,
  `ECHANGE` of `SOUR_NL` en twee lasten `AFFE_CHAR_MECA_F` (`FORCE_INTERNE`,
  `FORCE_FACE`, `PRES_REP`, `FORMULE` of `DEFI_FONCTION`) rekenen goed (energie /
  reactiekracht exact); alleen `SOURCE` heeft het gedrag.

### Lassen: bewegende warmtebron (WE)

Module `tests_lassen.py` (groep "Lassen" in `resultaten.md`, draaien met
`python run_verificatie.py WE`). Gebruikersdocumentatie: [Lassen.md](Lassen.md).

- **Doel**: de bewegende lasbron (`#ASTER-LASBRON`: Goldak-vorm (Goldak, Chakravarti & Bibby, 1984), baan, η, symmetrie,
  energiecontrole in de job), dezelfde bron als Mecway-formule in x, y, z, t
  (`heatgeneration` → `FORMULE`), formules in andere thermische lasten, en
  temperatuurafhankelijke λ en c (Mecway *TempDependent* → `THER_NL`, `THER_NON_LINE`).
- **Model WE-01/01b/02/03/05**: halve stalen plaat (symmetrievlak y = 0) 55 × 15 × 15 mm,
  λ = 30 W/mK, ρ = 7800 kg/m³, c = 600 J/kgK (a = 6,41e-6 m²/s), geïsoleerd, T0 =
  293,15 K; hex8 met 0,5 mm langs de baan en tot 7 mm ervan (35 600 knopen); bron
  1000 W (η·Q) met 5 mm/s over 30 mm vanaf x = 10 mm in 6 s, controle op t = 6 s.
  WE-01: halve Gauss-bol r = 0,75 mm, Δt = 0,05 s (v·Δt = (af + ar)/6); WE-01b: idem
  Δt = 0,15 s (de grens van de tijdstapmelding); WE-02: Goldak 1/2/1/1 mm, Q = 1250 W,
  η = 0,8, Δt = 0,1 s; WE-03: de bron van WE-01 als Mecway-formule op een
  elementselectie; WE-05: WE-02 met λ(T) 30 → 20 W/mK en c(T) 450/600/750 J/kgK
  (300/800/1300 K). WE-04a: staaf 100 mm (20 hex8), 300 en 1300 K aan de uiteinden,
  λ = 20 + 0,02 (T − 300) W/mK; WE-04b: staaf 20 mm (40 hex8), geïsoleerd, flux
  1e7 W/m² op x = 0 gedurende 2 s, λ(T) 50 → 25, c(T) als WE-05. WE-06: staaf 100 ×
  10 × 10 mm, stationair, temperatuur 100 + y (°C, y in mm), convectie h = 25(1 + 100y)
  (y in m), flux 1000·x (W/m², x in mm).
- **Referenties**: (a) Rosenthal (1946): quasi-stationair, puntbron op een
  half-oneindig geïsoleerd lichaam, T − T0 = Q/(2πkR)·exp(−v(R + ξ)/(2a)), op zes punten
  naast, achter en onder de bron (R = 3–6 mm, ≥ 4 r); (b) dezelfde (Goldak-)bron
  analytisch gevouwen met de Green-functie (`goldak_exact`, Carslaw & Jaeger, 1959):
  in y en z exact, in x per halve Gauss-kromme met erf, over de tijd numeriek; (c) de
  energiebalans ∫ρ(H(T) − H(T0))dV = η·Q·t/2 (halve plaat), uit de knooptemperaturen
  met dezelfde 2 × 2 × 2 Gauss-punten als Code-Aster; (d) de regel `BRIDGE_LASBRON`
  (som van de knooplasten = opgenomen vermogen); (e) WE-04a: Kirchhoff-transformatie
  (∫λ dT lineair in x, nodaal exact voor lineaire elementen); (f) Mecway 33 headless
  (`mw_solve.py`, interne solver) op dezelfde `.liml`.
- **Resultaat**:

| Case | Controle | Afwijking | Tolerantie |
|---|---|---|---|
| WE-01 | Rosenthal, 6 punten | −0,94 … +0,90% | 5% |
| WE-01 | energie; opgenomen vermogen (job) | +0,06%; +0,09% | 2%; 0,5% |
| WE-01b | Rosenthal, 6 punten (Δt op de meldingsgrens) | −3,6 … +1,6% | 5% |
| WE-02 | Goldak analytisch, 6 punten | −1,2 … +0,2% | 2% |
| WE-02 | energie; opgenomen vermogen | 0,00%; 0,00% | 2%; 0,5% |
| WE-03 | Rosenthal; Gauss-bron analytisch | ≤ 0,94%; ≤ 1,4% | 5%; 2% |
| WE-03 | energie t.o.v. Mecway | 1e-9 | 1e-4 |
| WE-03 | temperatuur t.o.v. Mecway (2 punten) | −2,9%; +1,6% | 6% |
| WE-04a | Kirchhoff (3 punten); Mecway | ≤ 2e-12; 3e-12 | 1e-4; 1e-3 |
| WE-04b | energie t = 1 en 2 s; Mecway (3 punten) | −0,003%, −0,002%; ≤ 0,13% | 0,5%; 2% |
| WE-05 | energie (enthalpie); opgenomen vermogen | −0,007%; 0,00% | 2%; 0,5% |
| WE-06 | Mecway (3 punten) | ≤ 1e-14 | 1e-9 |

- **Interpretatie**:
  - De bron, η, de verdeling ff/fr en de symmetrie komen exact in het mesh: het
    opgenomen vermogen is 500,00 W (WE-02) en de energiebalans sluit tot 0,06%; het
    restje is de integratie van de Gauss-bron met 2 punten per richting bij h = 0,67 r.
  - Rosenthal: het verschil is de bronvorm (de Gauss-bol t.o.v. een punt: +1,4% naast
    de bron, analytisch) plus de discretisatie. Met Δt op de meldingsgrens
    (v·Δt = (af + ar)/2) wordt de lasas 6 mm achter de bron 2,9% te koud; met
    v·Δt = af + ar (Δt = 0,3 s, buiten de regressie) 26%: de bron slaat knopen over. Met
    Δt = 0,05 s (WE-01) is het −0,25% t.o.v. dezelfde bron analytisch; de melding staat
    daarom op ½(af + ar) ([Lassen.md](Lassen.md) §4.1).
  - Goldak: de vergelijking met dezelfde bron analytisch controleert vorm, oriëntatie
    (voor/achter, dwars, diepte) en normering; de afwijking is de mesh (h = 0,5 mm
    tegen b = c = 1 mm).
  - Mecway-formule: de bridge geeft dezelfde temperaturen als `#ASTER-LASBRON` (WE-03 =
    WE-01) en dezelfde energie als Mecway. Mecway's temperaturen wijken af door zijn
    tijdschema (de last op het einde van de stap, KNOWN_BUGS 14): de bron loopt v·Δt/2
    voor; Mecway ligt binnen 1,5% van de analytische oplossing op t + Δt/2.
  - Temperatuurafhankelijk: λ(T) is exact (WE-04a, ook Mecway). Voor c(T) verfijnt de
    bridge de ρc-tabel: met alleen Mecway's tabelpunten miste `THER_NON_LINE` 13% van de
    energie na de eerste stap en 2,8% na 2 s (de enthalpie wordt tussen de tabelpunten
    lineair geïnterpoleerd); nu 0,003%. Mecway's eigen energiebalans: −0,3% / −0,2%.
  - WE-06: formules in x, y, z voor `TEMP_IMPO`, `ECHANGE` en `FLUX_REP` met eenheden
    mm, m en °C zijn gelijk aan Mecway tot op de afronding.

### Lassen: keten thermisch → mechanisch (WE-07 .. WE-10)

Module `tests_lassen_mech.py` (groep "Lassen", `python run_verificatie.py WE-07 WE-08
WE-09 WE-10`; WE-10b alleen met `VERIF_ZWAAR=1`, ~1 uur). Gebruikersdocumentatie:
[Lassen.md](Lassen.md) §9.

- **Doel**: de keten thermisch → mechanisch (T31 met een Thermal stress →
  `THER_LINEAIRE` en daarna `STAT_NON_LINE` met `AFFE_VARC` `TEMP`, `EVOL` = het
  thermische resultaat; `bridge_thermomech.py`): thermische rek, verhinderde uitzetting
  met bilineaire plasticiteit en restspanning na terugkoelen, temperatuurafhankelijke
  E, SY, α (`#ASTER-MATERIAAL`, `ELAS_FO`/`ECRO_LINE_FO`), en een lasrups op een plaat.
- **Model WE-07..09**: staaf 100 × 10 × 10 mm (hex8 4 × 1 × 1), E = 210 GPa, ν = 0,3,
  α = 1,2e-5 1/K; de temperatuur komt uit de thermische solve (opgelegde temperatuur op
  alle knopen met een tijdstabel T0 → T0 + ΔT → T0, Δt = 1 s, T0 = Thermal stress =
  293,15 K). WE-07: drie symmetrievlakken (vrij), ΔT = 100 K. WE-08: daarbij x = L vast
  in x (eenassig verhinderd, dwars vrij), BilinearIsotropic SY = 250 MPa, H = 20 GPa
  (Mecway's tangent modulus), ΔT = 150 K (vloeien vanaf 99,2 K). WE-09: als WE-08 met
  `#ASTER-MATERIAAL`: E 210 → 150 GPa, SY 300 → 100 MPa, α 1,2 → 1,4e-5 1/K lineair
  tussen 20 en 520 °C (α secans t.o.v. 20 °C), H = 0, ΔT = 400 K.
- **Model WE-10**: halve plaat 40 × 15 × 5 mm (symmetrievlak y = 0; hex8 1 mm, 40 × 10
  × 5), Goldak 2/4/2/2 mm, 1000 W, 5 mm/s over 30 mm (6 s), afkoelen tot 60 s met de
  rand y = 15 mm op T0 (de rest geïsoleerd), Δt = 0,3 s; staal met E, SY en α van 20 tot
  1500 °C (illustratief, verloop zoals voor S355), H = 1 GPa, `TC_CUT` = 1500 °C;
  mechanisch statisch bepaald (symmetrievlak, knoop (0, 0, −5 mm) x en z vast, knoop
  (40, 0, −5 mm) z vast). WE-10b: idem met `elem_hex8` = LINE_QUAD.
- **Referenties**: (a) eenassige handberekening: vrij ε = α·ΔT, σ = 0 (Timoshenko &
  Goodier, 1970, §150); verhinderd σ = −E·α·ΔT tot SY, daarna p = (α·ΔT − SY/E)/(1 +
  H/E), |σ| = SY + H·p, dwarsrek α·ΔT − ν·σ/E + p/2; terugkoelen elastisch, σ_res = E·p
  (geen omgekeerd vloeien zolang E·p < SY + H·p); (b) WE-09: dezelfde formules met E(T),
  SY(T), α(T) langs het pad (opwarmen, afkoelen, omgekeerd vloeien bij σ = +SY(T)),
  numeriek in kleine stappen (`tdep_path`); (c) WE-10: evenwicht van de restspanning in
  een vrije plaat (netto kracht en moment over de doorsnede x = 20 mm, trapeziumregel op
  de knopen), het vloeien in de las (von Mises = SY + H·p), en de tekens van het patroon
  en de krimp (Radaj, 1992; Masubuchi, 1980); de dwarskrimp tussen 0,2 en 1 × de
  bovengrens α·q/(v·ρ·c·t) = 0,103 mm.
- **Resultaat**:

| Case | Controle | Afwijking | Tolerantie |
|---|---|---|---|
| WE-07 | u_x en u_y bij ΔT = 40 en 100 K | ≤ 4·10⁻⁸ | 0,1% |
| WE-07 | max \|σxx\|; u_x na terugkoelen | 3·10⁻⁷ Pa; 4·10⁻²² m | 1e-4·E·α·ΔT; 1e-4·α·ΔT·L |
| WE-08 | σxx elastisch (ΔT = 50 K); plastisch (150 K); p; dwarsverplaatsing | ≤ 3·10⁻⁸ | 1% |
| WE-08 | restspanning +116,87 MPa; ε_p,xx; dwarsverplaatsing; reactiekracht na terugkoelen | ≤ 4·10⁻⁸ | 1% |
| WE-09 | σxx elastisch −124,44 MPa; plastisch −140 MPa (= −SY(T)); afkoelen elastisch +107,15 MPa | ≤ 2·10⁻⁸ | 1% |
| WE-09 | restspanning +300 MPa (= SY(T0), omgekeerd vloeien); ε_p,xx −1,4286e-3 | ≤ 1·10⁻⁸ | 1% |
| WE-10 | evenwicht: netto kracht / (SY·A); moment / (SY·A·t) (x = 20 mm) | −0,0002; −0,010 | ±0,03 |
| WE-10 | von Mises in de las / (SY + H·p) | 1,002 | 5% |
| WE-10 | trek in de las, druk op y ≥ 8 mm, hoekverdraaiing naar de laskant, langs- en dwarskrimp | alle in orde | teken |
| WE-10 | dwarskrimp hele plaat / (α·q/(v·ρ·c·t)) | 0,75 | 0,2 … 1,0 |
| WE-10b | idem met LINE_QUAD; σxx in de las / SY(T0) | evenwicht 0,0005 / −0,0004; von Mises 1,014; dwarskrimp 0,83; σxx 1,13 | als WE-10; 1 ± 35% |

- **Interpretatie**:
  - De keten is exact voor homogene toestanden: de temperatuur gaat per stap
    ongewijzigd van het thermische naar het mechanische resultaat (`ARCHIVAGE` op de
    thermische tijden), `VALE_REF` en de functies van TEMP staan in °C, en Mecway's
    *tangent modulus* is ook hier de plastische modulus H.
  - WE-09 bevestigt de conventie van `ELAS_FO`: α is de secans-coëfficiënt t.o.v.
    `TEMP_DEF_ALPHA` (= de referentietemperatuur), en Code-Aster schaalt de spanning
    bij een veranderende E mee (elastisch afkoelen: σ = E(T)·(p − α(T)·ΔT)). Het
    omgekeerd vloeien tijdens het afkoelen geeft de klassieke restspanning gelijk aan
    de vloeigrens bij kamertemperatuur.
  - WE-10 (hex8 `3D`, 9,9 min): de restspanning is in evenwicht en in de las vloeit het
    materiaal (von Mises = SY + H·p). Het patroon klopt met de literatuur: trek in de
    lasrichting in de las, druk ernaast (−220 … −370 MPa op y = 8 … 15 mm: de plaat is
    smal, de drukzone moet de trek binnen 15 mm opvangen), de randen draaien 8,9 mrad
    naar de laskant, langskrimp 0,013 mm op de lasas (40 mm) en dwarskrimp 0,077 mm
    (hele plaat, midden dikte; 0,126 mm aan de bovenkant). De grootte van σxx in de las
    is met lineaire hex8 niet betrouwbaar: 466 / 641 / 923 MPa boven / midden / onder
    (1,3–2,6 × SY) met σyy tot 418 en σzz 194 MPa midden in een plaat van 5 mm, een
    triaxiale toestand die volumetrische locking aanwijst (KNOWN_BUGS 64; Radaj en
    Masubuchi noemen langsspanningen van de orde van de vloeigrens). WE-10b (LINE_QUAD)
    gaf met kwadratische elementen (53 min) de langsspanning in de las 400–450 MPa
    (1,13 × SY(T0), gelijk aan SY + H·p), σzz ≈ 0 en het evenwicht tot 0,05%; de
    hoekverdraaiing is 39% groter (12,4 mrad): [Lassen.md](Lassen.md) §9.5.
  - Zonder `TC_CUT` en lijnzoeken convergeerde de LINE_QUAD-variant niet (Newton
    divergeerde in de tweede stap, ook na drie keer knippen): de thermische rek liep in
    het smeltbad door tot 4,6% bij 3400 K. Beide zijn nu in de bridge (`TC_CUT` als
    sleutel, `RECH_LINEAIRE` bij plasticiteit).

### Lassen: metallurgie (MT-01 .. MT-08)

Module `tests_lassen_meta.py` (groep "Metallurgie", `python run_verificatie.py MT`).
Gebruikersdocumentatie: [Lassen.md](Lassen.md) §10.

- **Doel**: de fase-omzettingen van `#ASTER-METALLURGIE` (`CALC_META`, staalmodel
  `ACIER`, met de standaard-datasets 16MND5 en HSNV101A of een eigen `DEFI_TRC`), de
  hardheid, en de metallurgische wet in de keten thermisch → mechanisch
  (`mechanica=ja`: `ELAS_META_FO`, `META_P_IL`, `AFFE_VARC` `M_ACIER`).
- **Model MT-01..05, MT-08**: staaf 100 × 10 × 10 mm (hex8 4 × 1 × 1) met een opgelegde
  temperatuur op alle knopen (tijdstabel), zodat elk punt hetzelfde verloop heeft (zoals
  hsnv101a en mtlp100b). MT-01: 900 → 0 °C in 180 s (Δt 1 s), `staal=HSNV101A,
  begin=austeniet, mechanica=ja`, Thermal stress T_ref = 900 °C, traction 0 → 360 MPa
  (0..60 s) op x = L, symmetrievlakken (hsnv101a in 3D). MT-02: 900 → 20 °C met
  1000 °C/s (Δt 0,02 s), `staal=16MND5, begin=austeniet`. MT-03: 600 → 1000 °C met
  10 °C/s (Δt 0,1 s), `begin=ferriet`. MT-04: 20 → 1000 °C (10 s), 2 s vast, afschrikken
  met 1000 °C/s (Δt 0,02 s), `mechanica=ja, ALPHA_F=1.4e-5, ALPHA_A=2.2e-5,
  DEPS=1e-2, SY=1e10` (elastisch), vrije staaf; MT-05: idem met x = L vast. MT-08: 900 →
  20 °C met 100 °C/s, een eigen `DEFI_TRC` in `#ASTER`-code (twee geschiedenissen zonder
  omzetting) met `MS0=300, ALPHA=-0.011`.
- **Model MT-06, MT-07**: de lasrups van WE-10 (halve plaat 40 × 15 × 5 mm, Goldak
  1000 W, 5 mm/s, Δt 0,3 s). MT-06 alleen thermisch met `staal=16MND5, begin=ferriet,
  TAUX_1=TAUX_3=0.001`; MT-07 daarbij de keten met `mechanica=ja` (ALPHA_A 2,35·10⁻⁵,
  DEPS 1·10⁻², vloeigrens per fase illustratief) en `#ASTER-MATERIAAL` van WE-10.
- **Referenties**: (a) MT-01: de testcase hsnv101a zelf (AXIS, Code-Aster 17.4,
  gedraaid met een extra `CREA_TABLE` van `META_NOEU` in knoop N13: de testcase heeft
  geen TEST_RESU op de fasen) en de TEST_RESU-waarden van hsnv101a (SIYY, EPYY in N13
  op 47, 48, 64 en 114 s); (b) Koistinen-Marburger Z_M = Z_a(Ms)·(1 − exp(ALPHA·(MS0 −
  T))) (Koistinen & Marburger, 1959; met de minteken-conventie van `META_ACIER`); (c)
  austenitiseren dZ/dt = (Z_eq(T) − Z)/τ met Z_eq lineair tussen Ac1 en Ac3, analytisch
  bij een lineaire temperatuur en constante τ; (d) de rek van `ELAS_META_FO` met
  `PHASE_REFE='FROID'`: ε = (1 − Z_a)·α_f·ΔT + Z_a·(α_a·ΔT − DEPS), en σ = −E·ε bij
  verhinderde uitzetting; (e) MT-06/MT-07: consistentie met Ac1/Ac3, evenwicht van de
  restspanning en het teken t.o.v. WE-10.
- **Resultaat**:

| Case | Controle | Afwijking | Tolerantie |
|---|---|---|---|
| MT-01 | bainiet op 64 .. 112 s en austeniet op 100 s t.o.v. hsnv101a (6 cijfers) | ≤ 1,3·10⁻⁶ | 1% |
| MT-01 | σxx (47, 64, 114 s) t.o.v. TEST_RESU SIYY | ≤ 5·10⁻⁷ | 1% |
| MT-01 | εxx (47, 48, 64, 114 s) t.o.v. TEST_RESU EPYY (3,47·10⁻² met vloeien) | ≤ 5,2·10⁻⁵ | 1% |
| MT-02 | martensiet bij 400 .. 240 °C (Koistinen-Marburger); hardheid (mengregel) | ≤ 4·10⁻⁸ | 1% |
| MT-02 | martensiet bij 20 °C (KM 0,99995) | −0,68% (Code-Aster stopt bij 0,69% austeniet) | 1% |
| MT-03 | austeniet bij 740, 780, 820, 840 °C | ≤ 2·10⁻⁸ | 1% |
| MT-03 | austeniet bij 850 / 860 °C (vlak boven Ac3) | +0,22% / +0,01% | 1% |
| MT-04 | εxx bij 1000, 600, 400, 340, 300 °C (opwarmen, austeniet, martensiet) | ≤ 6·10⁻⁶ | 1% |
| MT-04 | εxx na afschrikken; max \|σxx\| | −6,9·10⁻⁵ (−0,0069·DEPS); 1·10⁻⁵ Pa | 0,01·DEPS; 0,1 MPa |
| MT-05 | σxx = −E·ε bij dezelfde temperaturen (−2312 .. −106 MPa) | ≤ 6·10⁻⁶ | 1% |
| MT-06 | knopen in strijd met Ac1/Ac3; ferriet in de basis; som fasen; austeniet na afkoelen | 0; 1; 1; 0,005 | 0; 1e-9; 1e-6; 0,01 |
| MT-06 | hardheid in de las > basis; breedte austenietzone | 423 HV > 184 HV; 3 mm | teken; 1 .. 5 mm |
| MT-07 | evenwicht netto kracht / moment; martensiet + bainiet in de las | 0,0009 / −0,0039; 0,995 | ±0,03; ±0,02 |
| MT-07 | σxx lasas boven < WE-10 (466 MPa) | 176 MPa | teken |
| MT-08 | martensiet bij 250, 150, 50, 20 °C met eigen TRC (MS0 300 °C, ALPHA −0,011) | ≤ 3·10⁻⁸ | 1% |

- **Interpretatie**:
  - De bridge geeft `CALC_META` dezelfde invoer als de testcases: MT-01 reproduceert
    hsnv101a in 3D (fasen en de mechanische TEST_RESU-waarden, inclusief vloeien
    tijdens de omzetting). De temperatuur staat in °C, zoals AR3/MS0/AC1/AC3 en het
    TRC-diagram.
  - Koistinen-Marburger en de austenitisering bij langzaam opwarmen zijn exact; de
    formule van `ELAS_META_FO` (transformatierek) is met de hand bevestigd en bepaalt
    zowel de rek van een vrije staaf als de spanning van een ingeklemde.
  - Gemeten grenzen (KNOWN_BUGS 72, [Lassen.md](Lassen.md) §10.5): de martensietvorming
    stopt bij ~0,7% austeniet; bij snel opwarmen met grote stappen loopt de
    austenitisering achter (MT-06 met de dataset-τ 0,34 s: lasas 6% austeniet; met
    τ = 0,001 s volledig). Met τ = 0,001 s geeft MT-06 een plausibele warmte-beïnvloede
    zone: smeltzone en grofkorrelige WBZ 82% martensiet en 18% bainiet (423 HV),
    interkritisch op 3 mm (piek 796 °C) 44% ferriet, 20% bainiet, 36% martensiet
    (304 HV), daarbuiten ferriet (184 HV).
  - MT-07 (hex8, 13,6 min): de martensietuitzetting verlaagt de langsspanning in de las
    (176 / 4 MPa boven / midden t.o.v. 466 / 641 MPa in WE-10) en verplaatst de trekpiek
    naar de rand van de omgezette zone; de hoekverdraaiing daalt van 8,9 naar 5,2 mrad.
    Kwalitatief (illustratieve fasegegevens, locking van hex8).

### Lassen: toevoegmateriaal dat geboren wordt (WE-11 .. WE-13)

Module `tests_lassen_geboorte.py` (groep "Lassen", `python run_verificatie.py WE-11
WE-12 WE-13`). Gebruikersdocumentatie: [Lassen.md](Lassen.md) §11.

- **Doel**: toevoegmateriaal dat pas meedoet als de bron er langs komt (`#ASTER-LASBRON
  geboorte=`, "quiet element"): thermisch geen warmteopslag en geleiding vóór de
  geboorte (ρ·c × 10⁻⁴, λ × 10⁻⁸, `THER_FO` van `INST` en `NEUT1`, of een stil
  `THER_NL`-materiaal en `THER_NON_LINE` per geboortestap), mechanisch geen stijfheid
  en spanning vóór de geboorte en spanningsvrij bij de geboorte (`STAT_NON_LINE` per
  geboortestap, `ETAT_INIT` met de spanning van de nieuwe elementen op nul).
- **Model WE-11**: halve plaat 30 × 8 × 4 mm (symmetrievlak y = 0, hex8 0,75 mm) met
  een rups van 30 × 2,25 × 1,5 mm erop in twee stukken (`LASNAAD_1` x 0..15 mm,
  `LASNAAD_2` x 15..30 mm), elk met een eigen Goldak-bron 1,5/3/1,5/1,5 mm, 500 W
  (250 W in de halve plaat), 5 mm/s: stuk 1 van t = 0 tot 1,8 s (x 3..12 mm), stuk 2
  van 4 tot 5,8 s (x 18..27 mm); afkoelen tot 9 s; Δt = 0,1 s, θ = 0,57; alle vlakken
  geïsoleerd; staal λ = 30 W/m/K, ρ = 7800 kg/m³, c = 600 J/kg/K. WE-11b: idem met
  λ 30 → 25 W/m/K en c 500 → 800 J/kg/K (300 .. 1500 K; `THER_NON_LINE`).
- **Model WE-12**: staaf 100 × 10 × 10 mm (hex8 4 × 1 × 1); deel A (x 0..50 mm)
  bestaat vanaf het begin, deel B (`LASNAAD_B`) wordt op t = 6 s in één keer geboren
  (`geboorte=ja, voorloop=1`); opgelegde temperatuur op alle knopen T0 → T0 + 100 K (5
  s), vast tot 6 s, terug naar T0 (11 s); x = 0 en x = L vast in x, dwars vrij. E = 210
  GPa, α = 1,2e-5 1/K; WE-12b bilineair SY = 250 MPa, H = 20 GPa; WE-12c een
  hardingscurve 250 → 270 MPa bij plastische rek 0,01 (`TRACTION`).
- **Model WE-13**: halve plaat 30 × 8 × 4 mm (hex8 1 mm langs de las), laag 1 (30 ×
  2,25 × 1,5 mm, `LASNAAD_1`) en laag 2 erop (30 × 1,5 × 1,5 mm, `LASNAAD_2`), elk
  geboren met een eigen bron (500 W, 5 mm/s, x 5..25 mm; laag 1 van 0 tot 4 s, laag 2
  van 6 tot 10 s), afkoelen tot 30 s met de rand y = 8 mm op T0, Δt = 0,2 s; keten
  thermisch → mechanisch met E/SY/α(T) als WE-10 (H = 1 GPa, `TC_CUT` = 1500 °C);
  symmetrievlak + statisch bepaald; hex8 `3D` (1 140 elementen).
- **Referenties**: (a) energiebalans van het levende volume (geïsoleerd): ∫ρ(H(T) −
  H(T0)) dV = de ingebrachte energie volgens het θ-schema met de bron aan op [t0,
  t_eind] (Σ Δt (θ F_k + (1 − θ) F_k−1): na het einde van een bron q (t_aan + (1 − θ)
  Δt)); welke elementen leven rekent de test zelf uit de geboorteregel (§10.3 van
  Lassen.md), los van de bridge; (b) eenassige handberekening (Timoshenko & Goodier,
  1970, §150): A zet vrij uit (α·ΔT·L/2), na de geboorte op T1 en afkoelen naar T0 σ = E·α·
  (T1 − T0) in A en B, met lineaire versteviging p = (α·ΔT − SY/E)/(1 + H/E), σ = SY + H·p;
  (c) WE-13 kwalitatief (Radaj, 1992; Masubuchi, 1980): smelten, afkoelen tussen de
  lagen, opnieuw opwarmen, trek in de rups, druk ernaast, evenwicht.
- **Resultaat**:

| Case | Controle | Afwijking / waarde | Tolerantie |
|---|---|---|---|
| WE-11 | energie van het levende volume t = 3,5 s (stuk 2 ongeboren) / 5 s (stuk 2 wordt geboren) / 9 s | +1,19 / +1,49 / +1,59% | 2% |
| WE-11 | warmte in het ongeboren stuk 2 als het echt materiaal was / ingebracht (3,5 s) | 0,50% | 1% |
| WE-11 | max. T bovenop het ongeboren stuk 2 (3,5 s), naast het warme stuk 1 | T0 + 0,49 K | 1 K |
| WE-11 | opgenomen vermogen bron 1 / bron 2 (job) | −0,18 / −0,10% | 2% |
| WE-11b | idem met λ(T), c(T) (`THER_NON_LINE` per geboortestap) | +1,12 / +1,40 / +1,54%; 0,50%; T0 + 0,62 K | als WE-11 |
| WE-12 | u_x(L/2) vóór de geboorte (α·ΔT·L/2) | −0,02% | 1% |
| WE-12 | \|σxx\| in het ongeboren B / (E·α·ΔT) | 1,8·10⁻⁴ | 10⁻³ |
| WE-12 | σxx in B 1 s na de geboorte (E·α·20 K = 50,4 MPa) | −0,04% | 1% |
| WE-12 | restspanning B / A (E·α·ΔT = 252 MPa) | −0,01 / −0,01% | 1% |
| WE-12b | restspanning B (SY + H·p = 250,17 MPa); p | 0,00%; −0,7% | 1% |
| WE-12c | restspanning B met hardingscurve (250,02 MPa); p | 0,00%; +0,01% | 1% |
| WE-13 | top laag 1: piek / 1773 K; afgekoeld tussen de lagen; opnieuw opgewarmd | 1,52; 530 K; 1 750 K | 1 ± 0,5 × …; teken |
| WE-13 | laag 2 vóór de geboorte: max. von Mises / SY; max. T | 4,7·10⁻⁴; T0 + 0,03 K | 10⁻³; 1 K |
| WE-13 | evenwicht netto langskracht / (SY·A) (x = 15 mm); trek bovenop de rups; druk aan de rand | −0,0025; in orde | ±0,03; teken |

- **Interpretatie**:
  - Vóór de geboorte neemt het toevoegmateriaal geen warmte op: de energie van het
    levende volume volgt de ingebrachte energie, en zelfs met de echte ρ·c zou er minder
    dan 1% in het ongeboren stuk zitten (alleen de knopen op het grensvlak zijn warm;
    werkelijk opgeslagen 10⁻⁴ daarvan). Bij de geboorte neemt een element de temperatuur
    van zijn knopen over; die op het grensvlak zijn al warm: daardoor ligt de energie
    na de geboorte ~1% boven de ingebrachte (tolerantie 2%).
  - WE-11 en WE-11b rekenen langs de twee routes (`THER_FO` in één solve;
    `THER_NON_LINE` per geboortestap, met c(T)); met constante tabellen gaf de tweede
    route in een prototype dezelfde energie als de eerste (tot 10⁻⁶).
  - WE-12 bewijst het spanningsvrij geboren worden: zonder geboorte zou de staaf na het
    terugkoelen spanningsloos zijn; met de geboorte op T0 + 100 K krimpt B α·ΔT t.o.v.
    zijn geboortetemperatuur en volgt σ = E·α·ΔT = 252 MPa. De restspanning in A is 30
    kPa lager dan in B: A had bij de geboorte de spanning waarmee het het stille B
    (E × 10⁻⁴) indrukte (−60 kPa); B start op nul.
  - Gevonden en opgelost bij deze stap: (1) Code-Aster 17.4 rekent twee lasten
    `AFFE_CHAR_THER_F` met `SOURCE` in één analyse allebei met de functie van de
    eerste (met twee bronnen ging in WE-11 2 × de energie van bron 1 in het model en
    bron 2 nooit; ook constante `FORMULE`s): de lasbronnen staan nu in één last
    (nu ook de Mecway-formulebronnen, TH-40 .. TH-42); (2) met de consistente
    warmtecapaciteit volgde een stil knooppunt via de massakoppeling de temperatuur-
    snelheid van zijn warme buren (WE-13: +138 K voor de geboorte, met een dip onder T0
    tijdens het opwarmen): het toevoegmateriaal rekent nu met `3D_DIAG`; (3) de bron
    stond op het eindtijdstip door afronding soms uit (v·(t_eind − t0) net boven L):
    nu met een marge van 10⁻⁹.

## 9. Aannames en niet gedekt

**Aannames van de verificatie**
- De referentie is een analytische oplossing voor het geïdealiseerde probleem
  (lineaire elasticiteit, Euler- of Timoshenko-balk, Kirchhoff-plaat, 1D-golf,
  half-oneindig lichaam). Waar het FE-model iets anders beschrijft (3D-inklemming,
  Mindlin-schaal), is dat als modelfout benoemd en in de tolerantie opgenomen.
- Grootheden worden in knopen gelezen (`displ*`, `stress*` = `SIGM_NOEU`, von Mises van
  schalen, `temperature`, `heatflux*`), dus zoals de gebruiker ze in Mecway ziet.
  Knoopspanningen zijn geëxtrapoleerd en gemiddeld en convergeren langzamer dan
  verplaatsingen.
- Transiente resultaten staan in enkele precisie in het resultaatbestand (zie TH-02);
  stationaire en mechanische resultaten in dubbele precisie.
- Mecway-vergelijkingen zijn headless gerekend met Mecway 33 (`mecway.exe model.liml
  solve` met `<solutionfile>`); de interne solver van Mecway rekent geen plasticiteit,
  daarvoor is CCX gebruikt.

**Niet gedekt door deze tests** (wel deels elders vergeleken; nagelopen tegen §4–§8):
- straling (`RAYONNEMENT`; Code-Aster-test tpna01b in §10 en de vergelijking met
  Mecway in [Thermisch.md](Thermisch.md) §5), `heatflow` op knopen, tijdstabellen voor
  andere thermische belastingen dan een opgelegde temperatuur (die wel: WE-07 .. WE-10,
  MT) en thermische schalen buiten Z = constant (idem);
- kinematische versteviging en Ramberg-Osgood (wel bilineair isotroop: NL-01, WE-08,
  VM-11a; een hardingscurve: WE-12c; zie de varianten in [Bezwijken.md](Bezwijken.md)
  §5), bezwijken van elementen ([Bezwijken.md](Bezwijken.md) §5);
- wrijving (NL-03 is wrijvingsloos), verlijmd contact behalve schaal op schaal (LS-07),
  contact in dynamica (impliciet
  en expliciet);
- DKT bij grote verplaatsingen (KNOWN_BUGS 11; NL-02 alleen volumes en `COQUE_3D`;
  balken met grote rotaties: `POU_D_T_GD`, NL-80 .. NL-89), en bij `POU_D_T_GD` grote
  opgelegde rotaties, element offset, flexible joint en koppelingen;
- gap- en tension-only-elementen, dempers in transiente dynamica (DY, MD; dempers wel
  harmonisch en in complexe modes: HR-01d, MC, VH-04c).

Wel gedekt en daarom niet meer in deze lijst: een temperatuurveld als belasting in een
mechanische analyse (TH-03; uit een thermische analyse: WE-07 .. WE-10, MT),
centrifugaalkracht (MP-04, CY), dempers (HR-01d, MC, VH-04c) en een hardingscurve
(WE-12c).

## 10. Officiële Code-Aster-validatietests

De bridge-verificatie toetst de vertaling Mecway → Code-Aster. Deze aanvulling toetst
de Code-Aster-installatie zelf (17.4, Windows-build `v2025`) op de onderdelen die de
bridge gebruikt, met de officiële validatietests uit `share/aster/tests`. Elke test
heeft een V-document met dezelfde naam in de Code-Aster-documentatie (V2 lineaire
dynamica, V3 lineaire statica, V4 thermisch, V6 niet-lineaire statica; bijv. SSLL102 =
V3.01.102; EDF R&D, z.j.).

```
cd TestFiles/Verificatie/code_aster_testcases
python run_code_aster_tests.py            # alle 19, ca. 1 minuut
python run_code_aster_tests.py -j 3 ssn   # selectie, parallel
```

Per test: `run_aster.bat --ctest <installatie>/share/aster/tests/<test>.export` in
`%TEMP%/ca_testcases/<test>` (zoals ctest); mesh en `.comm` blijven in de installatie.
Uit de `.mess` komen de diagnose en elke TEST_RESU-regel (OK/NOOK per referentietype),
uit de `.code` de werkelijk gebruikte opties (MODELISATION, RELATION, DEFORMATION,
SCHEMA, FORMULATION, SOLVEUR METHODE). Uitkomst:
`TestFiles/Verificatie/code_aster_testcases/resultaten.md`, `.csv` en `.json`.

**Uitkomst: 19 van 19 tests OK, 1598 TEST_RESU-controles, 0 NOOK.**

| Test | Raakt in de bridge | Onderwerp | Referentie (aantal) | Max. fout (tol.) |
|---|---|---|---|---|
| sslv04b | `MECA_STATIQUE` 3D, hex20/penta15, `PRES_REP` | dikwandige cilinder onder inwendige druk (Lamé) | ANALYTIQUE 77 | 4,8% (6%) |
| ssll102a | `POU_D_E` | ingeklemde balk, eenheidskrachten en -momenten | ANALYTIQUE 318 | 9e-7 (1e-6) |
| ssls101b | DKT, `FORCE_COQUE`, `PESANTEUR` | ronde plaat onder druk | ANALYTIQUE 35 | 5,6% (6%) |
| ssls105a | DKT dubbel gekromd | NAFEMS LE3, halve bol dubbel geknepen | SOURCE_EXTERNE 2 | 0,66% (1%) |
| ssls114a | `COQUE_3D`, `PRES_REP`/`FORCE_COQUE` | cilinderschaal onder druk | ANALYTIQUE 48 | 27% (28%), zie onder |
| ssnp15a | `VMIS_ISOT_LINE` | plaat, niet-proportionele trek + afschuiving | ANALYTIQUE 44, AUTRE_ASTER 34 | 2,4% (3%) |
| ssnp14b | `VMIS_CINE_LINE` | NAFEMS trek + afschuiving, kinematisch | alleen NON_REGRESSION 13 | – |
| hsnv100g | `VMIS_ISOT_TRAC` + `ALPHA`/`AFFE_VARC TEMP` | thermoplasticiteit | ANALYTIQUE 12 | 0,001% (0,1%) |
| ssnp159a | `GDEF_LOG` (ook `PETIT`, `SIMO_MIEHE`) | trek tot grote rek | ANALYTIQUE 6 | 0,15% (1%) |
| ssnv122a | `GREEN_LAGRANGE`, `PRES_REP` meebewegend | starre rotatie + meebewegende druk | ANALYTIQUE 18 | 0,004% (0,1%) |
| ssnv167d | `DEFI_CONTACT` CONTINUE (Newton) | twee blokken in contact | ANALYTIQUE 20 | 4e-16 (1e-8) |
| sdls115a | `DYNA_NON_LINE` `DIFF_CENT` en HHT | plaatstrook met sinusoplossing | ANALYTIQUE 8, AUTRE_ASTER 3 | 5,5% (10%) |
| sdlv121d | `DYNA_NON_LINE` HHT/NEWMARK, continuum | vlakke golf in een kolom | ANALYTIQUE 8 | 2,1% (2,2%) |
| tpll01e | `THER_LINEAIRE` stationair | `TEMP_IMPO`, `FLUX_REP`, `ECHANGE` | ANALYTIQUE 7 | 4e-9 (1e-3) |
| ttlv01a | `THER_LINEAIRE` transient, θ | lichaam met convectie in de tijd | ANALYTIQUE 50 | 3,3% (5%) |
| tpna01b | `THER_NON_LINE`, `RAYONNEMENT` | geleiding met straling | ANALYTIQUE 5 | 0,087% (0,2%) |
| tplv101c | `THER_NON_LINE`, `PLAN` (thermische schaal) | vlak model met bronnen, flux, opgelegde temperatuur en wandcontact | ANALYTIQUE 70 | 1e-14 (1e-3) |
| sslv153a | `CALC_ERREUR` `ERME` (foutschatter) | blok hexa/penta/pyram/tetra, `LINE_QUAD`, vrije randen met druk ~0 | alleen NON_REGRESSION 8 | – (ook via de bridge: FS-03) |
| sslv111f | `CALC_ERREUR` `ERME` en `ERZ1` in 3D | plaat met gat (Kirsch), hexa8/pyram5/tetra4, `FORCE_FACE` | ANALYTIQUE 17 | 12% (15%) |

"Max. fout" is de grootste relatieve fout van een referentiecontrole (niet
NON_REGRESSION), met de tolerantie die de officiële test zelf stelt. MUMPS is de
oplosser in 17 van de 19 tests (tpll01e en een deel van sdlv121d kiezen LDLT,
ssls105a lost zelf op met `FACTORISER`/`RESOUDRE`).

Opmerkingen:
- **Geen NOOK, geen ontbrekende modules**: MUMPS, MED en de Python-hulpbestanden werken
  in de Windows-build. De lijst van tests die op Windows falen (`validation.md` in de
  installatie, 17 van 3769) bevat geen van deze tests.
- **Alarmen** (diagnose `<A>_ALARM`, test geslaagd): ssls114a `MODELISA8_14`,
  `UTILITAI_4`; ssnv122a `CHARGES9_53`; sdls115a `MODELISA8_14`; sdlv121d
  `MECANONLINE_23`. Alle in de test zelf bedoeld.
- **ssls114a, `COQUE_3D`**: de verplaatsingen kloppen tot 3,5%, maar `SIGM_NOEU` SIXX
  wijkt op enkele punten 25–27% af van de analytische waarde; de officiële test
  accepteert dat (tolerantie 27–28%). De oorzaak (oppervlaktelaag, extrapolatie naar de
  knopen of dunne- tegen dikke-schaaltheorie) is NIET geverifieerd. Voor de bridge, die
  schaalspanningen als `SIGM_NOEU` naar Mecway stuurt: knoopspanningen van `COQUE_3D` op
  gekromde schalen met voorzichtigheid gebruiken.
- **ssnp14b (NAFEMS)**: de `.comm` vergelijkt alleen met eigen eerdere uitkomsten
  (NON_REGRESSION); voor kinematische versteviging is dit geen onafhankelijke
  verificatie.
- **Niet gekozen**: expliciete dynamica in 3D (geen 3D-`DIFF_CENT`-test met een
  analytische referentie in 17.4), penalty-contact in 3D (de tests met penalisatie zijn
  2D/axisymmetrisch of hebben alleen SOURCE_EXTERNE), `GROT_GDEP` voor kabels en
  schalen.

Conclusie: de installatie rekent de gebruikte onderdelen (3D, DKT, `COQUE_3D`,
`POU_D_E`, von Mises-plasticiteit isotroop/kinematisch/trekkromme, `GDEF_LOG`,
`GREEN_LAGRANGE` met meebewegende druk, continu contact, HHT en `DIFF_CENT`, lineaire en
niet-lineaire thermiek met straling en `PLAN`, MUMPS) volgens de eigen validatietests.
Afwijkingen in de bridge-verificatie komen dus uit de vertaling of de discretisatie,
niet uit de installatie.

## 11. Bronnen

- Ainsworth, M. & Oden, J.T. (2000). *A Posteriori Error Estimation in Finite Element
  Analysis*. New York: Wiley.
- ASTM International (2017). *ASTM E1049-85 (Reapproved 2017): Standard Practices for
  Cycle Counting in Fatigue Analysis*, fig. 6 (rainflow; VM). West Conshohocken: ASTM.
  Niet lokaal ingezien; het voorbeeld is algemeen bekend en nagerekend.
- Ayrton, W.E. & Perry, J. (1886). On struts. *The Engineer*, 62, 464–465 en 513–515
  (eerste vloei van een staaf met imperfectie; NK-04). Niet lokaal ingezien.
- Bishop, R.E.D. & Johnson, D.C. (1960). *The Mechanics of Vibration*. Cambridge:
  Cambridge University Press (receptanties van balken; HR). Niet lokaal ingezien; de
  receptantie is afgeleid en nagerekend.
- Bisshopp, K.E. & Drucker, D.C. (1945). Large deflection of cantilever beams.
  *Quarterly of Applied Mathematics*, 3(3), 272–275.
- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold.
- Carslaw, H.S. & Jaeger, J.C. (1959). *Conduction of Heat in Solids* (2nd ed.).
  Oxford: Clarendon Press.
- Chopra, A.K. (2012). *Dynamics of Structures* (4th ed.). Upper Saddle River:
  Prentice Hall, hoofdstuk 13 (responsspectrum). Niet lokaal ingezien; de formules
  zijn nagerekend in `tests_spectrum.py`.
- Clough, R.W. & Penzien, J. (1993). *Dynamics of Structures* (2nd ed.). New York:
  McGraw-Hill.
- Der Kiureghian, A. (1981). A response spectrum method for random vibration analysis
  of MDF systems. *Earthquake Engineering and Structural Dynamics*, 9, 419–435 (CQC;
  formule zoals in Code-Aster `comb_sism_modal_ops.py`).
- Dörfler, W. (1996). A convergent adaptive algorithm for Poisson's equation. *SIAM
  Journal on Numerical Analysis*, 33(3), 1106–1124 (keuze van de elementen; AD). Niet
  lokaal ingezien.
- EDF R&D (z.j.). *Code_Aster, documentatie versie 17.4*: U2.06.13 (gebruik van
  `DYNA_NON_LINE`), U4.43.01 (`DEFI_MATERIAU`), U4.51.03 (`STAT_NON_LINE`), U4.53.01
  (`DYNA_NON_LINE`) en de V-documenten van de validatietests. https://www.code-aster.org
- Goldak, J., Chakravarti, A. & Bibby, M. (1984). A new finite element model for welding
  heat sources. *Metallurgical Transactions B*, 15, 299–305 (WE).
- Graff, K.F. (1975). *Wave Motion in Elastic Solids*. Columbus: Ohio State University
  Press (herdruk Dover, 1991).
- Heywood, R.B. (1952). *Designing by Photoelasticity*. London: Chapman & Hall (Kt van
  een plaat met gat; AD). Niet lokaal ingezien; formule via `tests_adaptief.py`.
- Hilber, H.M., Hughes, T.J.R. & Taylor, R.L. (1977). Improved numerical dissipation for
  time integration algorithms in structural dynamics. *Earthquake Engineering &
  Structural Dynamics*, 5(3), 283–292.
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite
  Element Analysis*. Mineola: Dover.
- Incropera, F.P., DeWitt, D.P., Bergman, T.L. & Lavine, A.S. (2007). *Fundamentals of
  Heat and Mass Transfer* (6th ed.). Hoboken: Wiley.
- Kerner, I.O. (1966). Ein Gesamtschrittverfahren zur Berechnung der Nullstellen von
  Polynomen. *Numerische Mathematik*, 8, 290–294 (methode van Durand-Kerner;
  MC-03). Niet lokaal ingezien; de methode staat in
  `tests_modaal_demping.py` (iteratie tot een stap < 1e-14).
- Koistinen, D.P. & Marburger, R.E. (1959). A general equation prescribing the extent
  of the austenite-martensite transformation in pure iron-carbon alloys and plain
  carbon steels. *Acta Metallurgica*, 7(1), 59–60 (MT).
- Leissa, A.W. (1969). *Vibration of Plates* (NASA SP-160). Washington, DC: NASA.
- Masubuchi, K. (1980). *Analysis of Welded Structures: Residual Stresses, Distortion,
  and their Consequences*. Oxford: Pergamon Press.
- Mattiasson, K. (1981). Numerical results from large deflection beam and frame
  problems analysed by means of elliptic integrals. *International Journal for
  Numerical Methods in Engineering*, 17(1), 145–153.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*
  (`C:\Program Files\Mecway\manual.pdf`; in de tekst "Mecway Ltd., 2026, §…" of
  "Mecway-handleiding"): o.a. §6.3, §6.9.2, §8.6, §9.26, §11.9, §11.24.
- NAFEMS (1990). *The Standard NAFEMS Benchmarks* (TNSB, rev. 3). Glasgow: NAFEMS.
- Pilkey, W.D. & Pilkey, D.F. (2008). *Peterson's Stress Concentration Factors* (3e
  druk). Hoboken: Wiley, chart 4.1 (AD). Niet lokaal ingezien.
- Radaj, D. (1992). *Heat Effects of Welding: Temperature Field, Residual Stress,
  Distortion*. Berlin: Springer.
- Rosenthal, D. (1946). The theory of moving sources of heat and its application to
  metal treatments. *Transactions of the ASME*, 68, 849–866 (WE).
- Sneddon, I.N. (1946). The distribution of stress in the neighbourhood of a crack in
  an elastic solid. *Proceedings of the Royal Society of London A*, 187, 229–260
  (cirkelvormige scheur; BR-10). Niet lokaal ingezien; via Tada e.a. p. 24.2.
- Southwell, R.V. (1932). On the analysis of experimental observations in problems of
  elastic stability. *Proceedings of the Royal Society of London A*, 135, 601–616.
- Tada, H., Paris, P.C. & Irwin, G.R. (2000). *The Stress Analysis of Cracks
  Handbook* (3e druk). New York: ASME Press, p. 2.2 (middenscheur in een strook) en
  p. 24.2 (cirkelvormige scheur) (BR).
- Timoshenko, S.P. & Gere, J.M. (1961). *Theory of Elastic Stability* (2nd ed.). New
  York: McGraw-Hill.
- Timoshenko, S.P. & Goodier, J.N. (1970). *Theory of Elasticity* (3rd ed.). New York:
  McGraw-Hill.
- Timoshenko, S.P. & Woinowsky-Krieger, S. (1959). *Theory of Plates and Shells* (2nd
  ed.). New York: McGraw-Hill.
- Verfürth, R. (1996). *A Review of A Posteriori Error Estimation and Adaptive
  Mesh-Refinement Techniques*. Stuttgart: Wiley-Teubner.
- Young, W.C. & Budynas, R.G. (2002). *Roark's Formulas for Stress and Strain* (7th
  ed.). New York: McGraw-Hill.
