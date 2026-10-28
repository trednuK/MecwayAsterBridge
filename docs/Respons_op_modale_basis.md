# Respons op modale basis (Mecway Dynamic Response met Mode superposition)

*English version: [Mode_superposition.md](en/Mode_superposition.md)*

Mecway's *Dynamic Response 3D* (analysetype D30) rekent de lineaire respons in de tijd
op een belasting die met de tijd verandert. Met de optie *Mode superposition* rekent
Mecway eerst de eigenmodes en daarna per mode een eenvoudige
1-vrijheidsgraadvergelijking (Mecway Ltd., 2026, §6.4). De bridge doet hetzelfde met
Code-Aster:

| Mecway | Bridge-analyse (pagina) | Code-Aster | Resultaat in Mecway |
|---|---|---|---|
| Dynamic Response 3D, *Mode superposition* aan | `dyna_modal_3d` (Respons op modale basis) | `CALC_MODES` → `PROJ_BASE` → `DYNA_VIBRA` `BASE_CALCUL='GENE'`, `TYPE_CALCUL='TRAN'` → `REST_GENE_PHYS` | tijdstappen met verplaatsing, rotatie, snelheid, hoeksnelheid en spanningen |
| Dynamic Response 3D, *Mode superposition* uit (Newmark op het hele model) | `dyna_impl_3d` (Dynamisch (impliciet)) | `DYNA_NON_LINE` | zie [Instellingen_contact_en_nietlineair.md](Instellingen_contact_en_nietlineair.md) |
| *Frequency 3D* of *Dynamic Response 3D*, last als sinus (Mecway kan dit niet) | `harmonic_3d` (Harmonische respons), zelf kiezen | `CALC_MODES` → `DYNA_VIBRA` `TYPE_CALCUL='HARM'` (`GENE` of `PHYS`) | per frequentie amplitude, fase, Re/Im, versnelling, spanning (§7) |

Wanneer gebruiken: een lineair model (geen contact, plasticiteit, gaps) onder een
schok, een stoot of een trilling, met veel tijdstappen. De berekening per stap is
goedkoop (alleen de modes); de dure stap is de modale analyse. Voor eigenfrequenties
alleen: [Modaal_en_knik.md](Modaal_en_knik.md).

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Analysetype.** *Dynamic Response 3D*. Zet in de analyse-instellingen de oplosser
   op *Mode superposition* en kies het **aantal modes** (*Number of modes*). Meestal
   zijn de eerste modes genoeg; bij een schok kan veel meer nodig zijn (Mecway Ltd.,
   2026, §6.4; zie §3 voor de controle).
2. **Tijd.** *Time period* (eindtijd) en *Time step*: Mecway en de bridge geven een
   oplossing op t = 0 en na elke tijdstap, of elke n-de stap met *Generate solution at: Every n time steps*
   (in de `.liml` `keepeverynthtimestep`). De eindtijd moet een veelvoud van de tijdstap zijn (§4). De bridge
   rekent intern met een kleinere stap (§2.4); de tijdstap van Mecway bepaalt dus
   alleen wanneer je resultaten ziet en hoe fijn een lasttabel gevolgd wordt.
3. **Materiaal** met een **dichtheid**: zonder massa geen trilling. Puntmassa's
   (*Mass*, *Rotational inertia*) tellen mee.
4. **Opleggingen.** Het model moet volledig vastliggen: starre bewegingen kunnen niet
   (ook niet in Mecway, Mecway Ltd., 2026, §6.4). Een opgelegde verplaatsing of
   rotatie moet 0 zijn (§4).
5. **Belastingen** met een tijdstabel (*force*, *pressure*, *gravity*, ...): de last
   volgt de tabel, lineair tussen de punten. Een belasting zonder tabel werkt vanaf
   t = 0 met de volle waarde (een staplast; de beginverplaatsing en -snelheid zijn 0).
   Een formule in t wordt een tabel ([Handleiding.md](Handleiding.md) §4).
6. **Demping.** *Rayleigh damping* op het hele model (zonder selectie): per mode de
   dempingsverhouding ξ_i = (α/ω_i + β·ω_i)/2 (Mecway Ltd., 2026, §9.26), en ξ_i < 1
   voor elke mode. α dempt vooral de lage, β de hoge modes. Voor ξ = ζ bij één
   frequentie ω: α = 2ζω (en β = 0), of β = 2ζ/ω (en α = 0). Dempers (*Damper*) kunnen
   niet met mode superposition (Mecway Ltd., 2026, §6.4).

### 1.2 In het hoofdvenster van de bridge

1. **Actieve analyse** `auto`: D30 met *Mode superposition* → `dyna_modal_3d`; D30
   zonder → `dyna_impl_3d` (§2.6). Of kies de analyse zelf.
2. **Resultaten naar Mecway** moet `liml` zijn (pagina Algemeen).
3. Pagina **Respons op modale basis**:

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Resultaatvelden naar Mecway | `displacements`, `velocities`, `stresses`, `vonmises` | velden uitzetten voor een kleinere `.liml` bij veel tijdstappen (spanningen kosten het meest). `reactions` en de plastische rek horen niet bij deze analyse (INFO) |
| Aantal modes (zonder maxmode in Mecway) | 10 | alleen als het Mecway-model geen *Number of modes* heeft |
| Controle modes (VERI_MODE SEUIL) | 1e-6 | zoals bij modaal ([Modaal_en_knik.md](Modaal_en_knik.md) §1.2) |
| Rekenstappen per periode van de hoogste mode | 50 | lager (bijv. 20) alleen als de run te lang duurt: de periodefout van de hoogste mode wordt dan 0,8%; hoger is zelden nodig (§2.4) |
| Extra modale demping (fractie van kritisch) | 0 | > 0 (bijv. 0,02) voor een dempingsverhouding op alle modes, bijv. uit een norm, zonder Rayleigh; telt op bij Mecway's Rayleigh-demping. Mecway kent deze invoer niet |
| Statische correctie weggelaten modes (MACRO_ELAS_MULT) | uit | aan als je weinig modes rekent en de quasi-statische bijdrage van de hogere modes wilt meenemen (verplaatsingen en vooral spanningen bij een langzaam veranderende last, §3). Uit = zoals Mecway |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 1800 s, 2048 MB, 8 | grote modellen |

De elementkeuzes op de pagina **Elementen** gelden ook hier (hex8 met `3D` is te stijf
bij buiging, KNOWN_BUGS 1; schalen wijken iets af van Mecway, KNOWN_BUGS 2).

### 1.3 Starten en volgen

- **Log en statusvak** na afloop: "Modale basis van de respons (n modes)" met per mode
  de frequentie en de effectieve massa (zoals bij modaal, [Modaal_en_knik.md](Modaal_en_knik.md)
  §1.3) en de som over de modes. Zo zie je of de modes de belasting dragen (§3).
- **study.mess** (`<model>_<run-id>.mess`): per mode de dempingsverhouding
  (`BRIDGE_DEMPING mode 1: 5.6494 Hz, xi = 0.05`, verificatie MD-04) en de rekenstap
  (`BRIDGE_DYNA_MODAL rekenstap 3.53357e-05 s (283 per uitvoerinterval), 28300 stappen`, verificatie MD-01).
- **Convergentiescherm:** de meldingen en de diagnose; er zijn geen
  Newton-iteraties.

### 1.4 Resultaten in Mecway

Onder *Solution* staan de tijdstappen (t = 0, de tijdstap van Mecway, ...), zoals bij
Mecway's eigen oplossing. Velden: `displx/y/z`, `displmag`, `rotx/y/z` (balken,
schalen), `velx/y/z`, `velmag`, `angularvelx/y/z`, `angularvelmag` (balken, schalen),
`stressxx` ... en `vonmises` (volume-elementen), `vonmisesu1/m/b` (schalen),
`beamsixxmin/max` (balken). Geen versnellingen en geen reacties (Mecway geeft bij mode
superposition ook geen versnellingen, Mecway Ltd., 2026, §6.4). Met een tabel in
Mecway (*Table*, tijd tegen een knoopwaarde) zie je het verloop in een knoop.

## 2. Hoe de bridge vertaalt

### 2.1 Modes

`ASSEMBLAGE` (`RIGI_MECA`, `MASS_MECA` met de opleggingen als `CHARGE`) en `CALC_MODES`
`PLUS_PETITE` met `NMAX_FREQ` = het aantal modes en `NORM_MODE='MASS_GENE'`, zoals de
modale analyse ([Modaal_en_knik.md](Modaal_en_knik.md) §2.1). Het modeoverzicht
(frequentie, effectieve massa) komt in de `.mess` en de log. Anders dan bij de modale
analyse geven de belastingen **geen voorspanning** (spanningsverstijving): Mecway ook
niet (headless gemeten: een trekkracht van 10 kN op de tip van MD-01, die de
frequentie bij voorspanning ~1,4 × zo hoog zou maken, liet de periode gelijk; de
bridge gaf dezelfde respons, 1,4e-5).

### 2.2 Belastingen

`DYNA_VIBRA` op modale basis vraagt per belasting een vector met een tijdsfunctie:
F(t) = Σ_j V_j·f_j(t) (catalogus `dyna_vibra.py`, `EXCIT` met `VECT_ASSE_GENE` en
`FONC_MULT`). De bridge maakt de lasten zoals bij de andere analyses en splitst ze:

- een last zonder tijdstabel wordt een vector met f = 1 (vanaf t = 0);
- een last met tabel(len): per tijdsfunctie een kopie van de last met die functie
  op 1 en de andere op 0, met de tabel als `FONC_MULT` (de last is lineair in de
  waarden; zo werken ook twee componenten met elk een eigen tabel);
- vectoren met `CALC_VECT_ELEM` (`CHAR_MECA`) en `ASSE_VECTEUR`, en met `PROJ_BASE`
  (`STOCKAGE='DIAG'`) op de modes geprojecteerd: gegeneraliseerde massa, stijfheid en
  krachten (syntax als Code-Aster-testcase forma12d).

Lasten uit `#ASTER-EXCIT` tellen alleen als oplegging of koppeling (in `ASSEMBLAGE`),
zoals bij modaal; een kracht daarin doet niet mee.

### 2.3 Demping

De modale dempingsverhouding per mode, uitgerekend in de job na `CALC_MODES`:
ξ_i = α/(2ω_i) + β·ω_i/2 + ζ (Mecway's Rayleigh-demping, Mecway Ltd., 2026, §9.26,
plus de instelling *Extra modale demping*) als `AMOR_MODAL=_F(AMOR_REDUIT=...)` in
`DYNA_VIBRA`. Is een ξ_i ≥ 1, of een frequentie ≤ 0 (starre beweging), dan stopt de
job met een melding (§5). Dezelfde ξ_i (zonder de extra modale demping) geeft de
modale analyse met *Complexe modes met demping* per mode, samen met de gedempte
frequentie ([Modaal_en_knik.md](Modaal_en_knik.md) §6; verificatie MC-04): zo kun je
α en β eerst met een modale analyse controleren.

### 2.4 Tijdintegratie

Mecway integreert de modale vergelijkingen exact: gemeten met Mecway 33 (headless),
massa op een balk onder een staplast, met tijdstap 0,02 s (ω·Δt = 0,71) en 0,001 s
dezelfde respons, binnen 1e-4 van u_st(1 − cos ωt). De bridge gebruikt `NEWMARK`
(gemiddelde versnelling, β = 1/4, γ = 1/2) met een kleine vaste stap: n stappen per
periode van de hoogste mode in de basis (instelling, standaard 50), afgerond op een
geheel aantal per uitvoerinterval. De periodefout van Newmark is (ω·Δt)²/12 (Hughes,
2000, §9.3): 0,13% voor de hoogste mode, minder voor de lagere. Gearchiveerd wordt
alleen op de uitvoertijden. Met 50 stappen per periode kost een model met een hoge
eerste-axiale mode veel stappen (bijv. 28 300 voor MD-01: axiale mode 565 Hz × 1 s × 50), maar
een stap op modale basis is goedkoop (seconden).

### 2.5 Terug naar de knopen, spanningen, statische correctie

`REST_GENE_PHYS` zet `DEPL`, `VITE` (en `ACCE`, nodig voor de balkspanningen
`SIPM_ELNO`, gezien: alarm `CALCULEL3_1` zonder versnellingen) terug op de knopen;
`CALC_CHAMP` rekent de spanningen zoals bij statisch, met `MODELE`/`CHAM_MATER`
expliciet. Met *Statische correctie* aan: `MACRO_ELAS_MULT` geeft de statische
respons op elke belastingsvector (`MODE_CORR`), `DYNA_VIBRA` en `REST_GENE_PHYS`
krijgen `CORR_STAT='OUI'` met de eerste en tweede afgeleide van de tijdsfunctie
(`CALC_FONCTION DERIVE`); route van testcase forma12d. Gemeten (MD-06b): met 1 mode
is de eindverplaatsing van een gedempte console precies de statische (< 1e-6), zonder
correctie 0,97069 daarvan.

### 2.6 D30 zonder Mode superposition

Mecway rekent dan Newmark (gemiddelde versnelling) op het hele model. `auto` kiest
`dyna_impl_3d` (`DYNA_NON_LINE`); de uitvoertijden komen uit Mecway's tijdstap. Met
*Tijdschema* `NEWMARK` en *COMPORTEMENT DEFORMATION* `PETIT` (pagina Dynamisch
(impliciet)) is dat hetzelfde schema: verificatie MD-07 gelijk aan Mecway tot 3e-8.
Met de standaard `HHT` (numerieke demping) en `GROT_GDEP` meldt de bridge een WARNING.

## 3. Interpretatie

- **Modale truncatie.** Alleen de gerekende modes bewegen. Een last die hogere modes
  aanspreekt, mist hun bijdrage, ook het statische deel. Gemeten op een ingeklemde
  balk met een puntlast op de tip (Euler-Bernoulli): met 1 mode bereikt de
  verplaatsing 97,07% van de statische (12/λ₁⁴, Blevins, 1979, tabel 8-1), met de 3
  modes in dat vlak 99,86%, en Mecway geeft precies hetzelfde (MD-06a; Mecway past
  geen statische correctie toe). Spanningen convergeren trager dan verplaatsingen.
- **Genoeg modes?** Kijk naar de som van de effectieve massa in de richting van de
  last (log, §1.3). Vuistregel: minstens 90% (Aubry, 2023, §3.3 en §11.3; zie ook
  [Modaal_en_knik.md](Modaal_en_knik.md) §1.5). Blijft de som in een belaste
  richting daaronder, dan geeft de bridge een WARNING (§5, ook harmonisch §7.7). De
  belaste richtingen volgen uit de resultante van de lastvectoren (ook gravity als
  basisversnelling): elke richting met minstens 1% van de grootste component. Is de
  resultante nagenoeg 0 (een druk op een gesloten vlak), dan elke richting waarin de
  last componenten heeft. De som telt alleen de echte modes, niet de pseudo-modes van
  de *Statische correctie* (die vangt het quasi-statische deel van de ontbrekende
  modes wel op; hun dynamica niet). Zekerder: reken een
  tweede keer met meer modes, of met *Statische correctie*; verandert de respons
  nauwelijks, dan zijn de modes genoeg. Een last op één plek (puntlast, schok) vraagt
  meer modes dan een verdeelde last.
- **Frequenties boven de hoogste mode** in de last worden niet gevolgd: kies het aantal
  modes zo dat de hoogste frequentie ruim boven de frequenties in de last ligt.
- **Tijdstap van Mecway.** Bepaalt de uitvoer en hoe een tabel bemonsterd wordt, niet
  de nauwkeurigheid van de integratie (§2.4). Een piek tussen twee uitvoertijden zie
  je niet: kies de tijdstap klein ten opzichte van de kortste periode die je wilt
  zien (Mecway Ltd., 2026, §6.4: begin bij de periode van de hoogste mode van
  belang). Een staplast geeft bij 0 demping een maximum van 2 × de statische
  verplaatsing (DAF 2; MD-01).
- **Hoge modes en de uitvoerstap.** Een mode met een periode korter dan twee
  uitvoerstappen is in de resultaten niet te volgen (de waarden op de uitvoertijden
  springen); de berekening zelf is wel nauwkeurig (§2.4). Gezien met een axiale mode
  van 565 Hz bij een uitvoerstap van 5 ms: gelijke piek als Mecway, maar per
  uitvoertijd andere waarden.
- **Demping per mode** staat in de `.mess`. Met alleen β zijn de hoge modes sterk
  gedempt (ξ ∝ ω), met alleen α de lage.
- **Hand­controle** (formules uit de verificatie): 1-vrijheidsgraad k, m: ω = √(k/m);
  staplast u_max = u_st(1 + e^(−πζ/√(1−ζ²))); harmonische last F₀ sin Ωt stationair
  u = u_st / √((1 − r²)² + (2ζr)²), r = Ω/ω (Clough & Penzien, 1993, hoofdstuk 3).

## 4. Wat niet kan

- Starre bewegingen (vrij model, mechanisme): ERROR of melding in de job (§5); ook
  Mecway niet.
- Een opgelegde verplaatsing of rotatie ≠ 0, ook met een tijdstabel (de modes hebben
  die vrijheidsgraden vast; daarvoor zijn statische modes nodig, niet gebouwd): ERROR,
  gebruik `dyna_impl_3d`.
- Dempers, beginsnelheid, thermische rek (*Thermal stress*), contact, gaps,
  tension/compression only: ERROR; gebruik `dyna_impl_3d`.
- Rayleigh-demping op een selectie (alleen het hele model, ook in Mecway).
- Uitvoertijden die niet op een regelmatig raster vanaf 0 liggen (eindtijd geen
  veelvoud van de tijdstap): ERROR.
- Versnellingen en reacties naar Mecway.
- De stationaire respons per frequentie (harmonische analyse in het
  frequentiedomein): niet met `dyna_modal_3d`, wel met de eigen analyse
  `harmonic_3d` (§7). Een sinusvormige last in de tijd kan hier wel (MD-03).

## 5. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Respons op modale basis zonder opleggingen | starre bewegingen | leg het model in Mecway vast |
| ERROR: Opgelegde verplaatsing of rotatie <> 0 op ... | de modes hebben die vrijheidsgraden vast | waarde 0, of `dyna_impl_3d` |
| ERROR: Een tijdsafhankelijke opgelegde verplaatsing kan niet ... | idem | `dyna_impl_3d` |
| ERROR: Dempers (...) kunnen niet in een respons op modale basis | Mecway ook niet | Rayleigh-demping, of `dyna_impl_3d` (Mecway: Mode superposition uit) |
| ERROR: Een beginsnelheid wordt ... niet vertaald | niet gebouwd | `dyna_impl_3d` |
| ERROR: Thermische rek ... niet vertaald | niet gebouwd | `dyna_impl_3d` |
| ERROR: De uitvoertijden ... liggen niet op een regelmatig raster | eindtijd geen veelvoud van de tijdstap | pas *Time period* of *Time step* aan |
| ERROR: ... kan niet in een respons op modale basis (lineair) | contact, gap, tension/compression only | verwijder of onderdruk het, of `dyna_impl_3d` |
| ERROR: De resultaatroute 'tabel' werkt niet ... | modes en tijdstappen alleen via `liml` | *Resultaten naar Mecway* = `liml` |
| WARNING: Het Mecway-model rekent Dynamic Response zonder Mode superposition ... | `dyna_modal_3d` zelf gekozen voor een D30 zonder mode superposition | gewenst? Anders `auto` of `dyna_impl_3d` |
| WARNING: Mecway Dynamic Response (D30) rekent lineair met Newmark ... | D30 zonder mode superposition, `dyna_impl_3d` met HHT of grote verplaatsingen | schema `NEWMARK` en deformation `PETIT` voor hetzelfde schema als Mecway (§2.6) |
| WARNING: Geen belastingen: de respons is overal 0 | geen last | breng de belasting aan |
| WARNING: Modale basis: effectieve massa (som over ... modes) onder 90% in de belaste richting(en): ... | te weinig modes in de richting van de last (§3) | meer modes (*Number of modes* in Mecway, of `modal_modes`), of directe tijdsintegratie (Mecway: Mode superposition uit, `dyna_impl_3d`) |
| WARNING: Modaal: elset(s) ... hebben geen dichtheid | geen massa | geef het materiaal een dichtheid |
| Code-Aster meldt: Respons op modale basis: dempingsverhouding >= 1 (mode=..) | overkritische demping in een mode (vaak een hoge mode met β, of een lage met α) | verlaag α/β of *Extra modale demping*, of minder modes; ξ per mode in de `.mess` (`BRIDGE_DEMPING`) |
| Code-Aster meldt: Respons op modale basis: een mode met frequentie <= 0 | mechanisme of los onderdeel | leg het model volledig vast |
| `ALGELINE3_81`, `ALGELINE5_*` en andere `CALC_MODES`-meldingen | als bij de modale analyse | [Modaal_en_knik.md](Modaal_en_knik.md) §4 |

## 6. Verificatie

[Verificatie.md](Verificatie.md) §7 (MD-01 … MD-07): massa op een balk onder een
staplast en een harmonische last, met en zonder demping, binnen 0,17% van de exacte
oplossing en binnen 1,4e-5 van headless Mecway; een hex20-console gelijk aan Mecway
(verplaatsing 4e-5, snelheid 1,4e-4, spanning 4e-4); modale truncatie en statische
correctie exact; D30 direct via `dyna_impl_3d` gelijk aan Mecway. Mecway-voorbeeld
DampedVibratingStrip (quad8-schalen, 10 modes, Rayleigh): verplaatsing in de tabelknoop
max. 1,9% verschil over 10 s, piek −0,6%, grootste von Mises +0,9%; de frequenties
van de schalen wijken 0,3–0,6% af van Mecway (`COQUE_3D`, KNOWN_BUGS 2), waardoor de
fase langzaam verloopt.

## 7. Harmonische respons (`harmonic_3d`)

De **stationaire** respons op een sinusvormige last F·cos(ωt + φ), per frequentie:
amplitude, fase, spanning en versnelling, zoals in een trillingsmeting of een
shakertest. Voorbeelden: een machine met onbalans op een frame, een pomp op een
vloer, controle of een bedrijfsfrequentie ver genoeg van een eigenfrequentie ligt.
Mecway heeft geen harmonische analyse (Mecway Ltd., 2026, hoofdstuk 6; *Dynamic
Response* rekent in de tijd). De bridge rekent daarom een Mecway *Frequency*- of
*Dynamic Response*-model in het frequentiedomein met Code-Aster `DYNA_VIBRA`
`TYPE_CALCUL='HARM'`:

| Bridge-analyse (pagina) | Code-Aster | Resultaat in Mecway |
|---|---|---|
| `harmonic_3d` (Harmonische respons), basis `GENE` (standaard) | `CALC_MODES` → statische verrijking → `PROJ_BASE` → `DYNA_VIBRA` `HARM` `BASE_CALCUL='GENE'` → `REST_GENE_PHYS` → `CALC_CHAMP` | per frequentie een "mode" met amplitude, fase, Re/Im, versnelling, spanning |
| idem, basis `PHYS` (controle, dempers) | `DYNA_VIBRA` `HARM` `BASE_CALCUL='PHYS'` op het hele model | idem |

Een sinusvormige last die **inschakelt** (met het inslingeren) is een transiënte
berekening: §1 met een tabel (MD-03). De harmonische analyse geeft alleen de
eindtoestand, maar wel voor veel frequenties tegelijk.

### 7.1 Werkwijze in Mecway stap voor stap

1. **Analysetype.** *Frequency 3D* met *Number of modes*, of *Dynamic Response 3D* met
   *Mode superposition* en *Number of modes*. Het aantal modes is de modale basis:
   kies het zo dat de hoogste mode ruim boven de hoogste frequentie van de vraag ligt
   (§7.5). Mecway's eigen *Solve* geeft dan de eigenfrequenties: handig om het
   frequentiebereik te kiezen.
2. **Materiaal met een dichtheid**; puntmassa's (*Mass*) tellen mee.
3. **Opleggingen.** Het model moet volledig vastliggen; een opgelegde verplaatsing of
   rotatie moet 0 zijn (§7.6).
4. **Belastingen** (*Force*, *Pressure*, *Gravity*, *Moment*, ...): de waarde is de
   **amplitude** (piekwaarde) van de sinus, in fase 0. Een **andere fase** per
   belasting: zet in een vrij tekstveld (bijv. *CCX > Custom model definition*)
   `** ASTER-FASE <selectie> = <graden>` ([ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md),
   voorbeeld 15). Een **amplitude die met de frequentie verandert** (bijv. een
   onbalanskracht m·e·ω²): geef de belasting een tabel; de kolom *time* is dan de
   frequentie in Hz (lineair ertussen, constant erbuiten).
5. **Demping.** *Rayleigh damping* op het hele model: per mode ξ_i = α/(2ω_i) +
   β·ω_i/2, of de instelling *Extra modale demping* (§7.2). Zonder demping is de
   respons bij een eigenfrequentie oneindig (WARNING). Dempers (*Damper*) alleen met
   basis `PHYS`. Een mode met ξ ≥ 1 (overkritisch) geeft een WARNING, maar de
   berekening gaat door (anders dan bij de respons in de tijd, §5).
6. **Meetpunten** (optioneel): een knoopselectie met de naam `MEETPUNT_...` (of
   `PROBE_...`), bijv. `MEETPUNT_Lager`. Per meetpunt komt de frequentierespons in de
   log en in een CSV (§7.3).
7. Sla op.

### 7.2 In het hoofdvenster van de bridge

1. **Actieve analyse:** kies *Harmonische respons* (`harmonic_3d`) zelf; `auto` kiest
   bij V30 de modale en bij D30 de transiënte analyse.
2. **Resultaten naar Mecway** moet `liml` zijn.
3. Pagina **Harmonische respons**:

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Resultaatvelden naar Mecway | `displacements`, `accelerations`, `stresses`, `vonmises` | velden uitzetten voor een kleinere `.liml` (spanningen kosten het meest); `velocities` voor ω\|U\| |
| Aantal modes (zonder maxmode in Mecway) | 10 | alleen als het Mecway-model geen *Number of modes* heeft |
| Extra modale demping (fractie van kritisch) | 0 | > 0 (bijv. 0,02) voor een dempingsverhouding op alle modes uit een norm of meting; telt op bij Rayleigh; alleen basis `GENE` |
| Statische correctie weggelaten modes | aan | uit alleen om de modale truncatie te zien (§7.5) |
| Startfrequentie / Eindfrequentie [Hz] | 1 / 100 | het bereik van de vraag, bijv. 0,5–2× de bedrijfsfrequentie; de hoogste mode van de basis hoort er ruim boven te liggen |
| Aantal frequenties | 100 | meer voor een gladder verloop tussen de pieken; de pieken zelf vangt de verfijning |
| Verdeling (lin / log) | lin | `log` over meerdere decades |
| Frequentielijst [Hz] (0 = bereik hierboven) | 0 | vaste frequenties, bijv. toerentallen `25, 50, 100`; dan precies deze frequenties, zonder verfijning |
| Basis (GENE modaal / PHYS direct) | GENE | `PHYS` als controle van de modale basis, met dempers, of als de last frequenties boven de modes heeft; per frequentie een oplossing van het hele model (duurder) |
| Extra frequenties per resonantie (0 = geen) | 5 | meer (7–11) voor een gladde piek; 0 = alleen het bereik |
| Verliesfactor eta (hysteretische demping, 0 = geen) | 0 | > 0 voor structurele demping van alle materialen (§7.4 punt 4), bijv. 0,02 voor een staalconstructie, 0,1–0,5 voor rubber; per materiaal met `#ASTER-HYST` |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 1800 s, 2048 MB, 8 | grote modellen of veel frequenties (PHYS) |

Per model met `#ASTER-OPTIE`, bijv. `** ASTER-OPTIE harm_freq_list = 25, 50` of
`** ASTER-OPTIE harm_basis = PHYS`.

**Hysteretische (structurele) demping.** Mecway kent geen verliesfactor (alleen
*Rayleigh damping* en het materiaal *Damper*). Geef hem op met de instelling
*Verliesfactor eta* (`loss_factor`, alle materialen) of per materiaal in de *custom
model definition* (zoals `#ASTER-FASE`):

```
** ASTER-HYST Rubber = 0.3
** ASTER-HYST * = 0.02
```

`materiaal = eta` met de Mecway-naam van het materiaal (ook een *Spring*-materiaal),
`*` = alle materialen; de regel gaat boven de instelling, de laatste regel per
materiaal telt. De stijfheid wordt K(1 + iη); bij een resonantie werkt η als een
viskeuze ξ = η/2 (Aubry, 2023, §3.3.4). Anders dan viskeuze demping hangt de
hysteretische demping niet van de frequentie af: de fase onder de resonantie is −atan η,
niet 0.

### 7.3 Resultaten in Mecway

Onder *Solution* staat per frequentie een regel (*Mode 1 ... n* met de frequentie in
Hz; het zijn **geen** eigenmodes maar de respons bij die frequentie, zoals bij de
harmonische akoestiek). Velden per frequentie (knoopwaarden):

| Veld | Betekenis | Eenheid |
|---|---|---|
| `displx/y/z` | Re(U): de verplaatsing op het moment dat de last (fase 0) maximaal is; Mecway's vervormde vorm en animatie gebruiken deze | m |
| `displix/y/z` | Im(U) | m |
| `displampx/y/z` | amplitude \|U\| per richting | m |
| `displmag` | √(\|Ux\|² + \|Uy\|² + \|Uz\|²) | m |
| `displphasex/y/z` | fase arg U ten opzichte van de last met fase 0, −180…180; negatief = naijlen | graden |
| `rotx/y/z`, `rotampx/y/z` | balk- en schaalknopen: Re en amplitude van de rotatie | rad |
| `velmag`, `velampx/y/z` | ω\|U\| (veld `velocities`) | m/s |
| `accmag`, `accampx/y/z` | ω²\|U\| (veld `accelerations`) | m/s² |
| `stressxx` … `stresszx` | Re van de spanning (fase 0), volume-elementen | Pa |
| `stressampxx` … | amplitude per component | Pa |
| `vonmises` | grootste von Mises-spanning **over een periode** (§7.4) | Pa |

De verplaatsing in de tijd is u(t) = Re(U·e^{iωt}) = \|U\|·cos(ωt + fase). In de
**log** en het statusvak: het aantal frequenties, de modes in het bereik met hun
demping, per meetpunt de grootste amplitude en de frequentie daarvan, en een WARNING
als de hoogste frequentie boven de hoogste mode van de basis ligt. Per meetpunt en
frequentie staan |u|, |a|, Re/Im en fase per richting in
`<model>_<run-id>_meetpunten.csv` (kolommen `meetpunt, frequentie_Hz, u_amp_m,
a_amp_m_s2, ux_re_m, ux_im_m, ..., ux_fase_graden, ..., knopen`; met taal Engels
Engelse kolomnamen); een spreadsheet maakt daar direct een frequentieresponsgrafiek
van. Een meetpunt met meer knopen: per richting het gemiddelde van U met als
amplitude de kwadratisch gemiddelde \|U\| (zoals de microfoons, [Akoestiek.md](Akoestiek.md) §5.3).

### 7.4 Hoe de bridge vertaalt

`bridge_harmonic.build_harmonic` (template `AsterTemplate_Harmonisch.comm`; syntax van
de Code-Aster-testcases sdld313d en sdld21b):

1. Model, materialen, opleggingen en lasten zoals bij de andere analyses; elke
   belasting (per Mecway-belasting, met tabel per tabel) wordt een lastvector
   (`CALC_VECT_ELEM`, `ASSE_VECTEUR`), zoals in §2.2.
2. `ASSEMBLAGE` en `CALC_MODES` (de laagste modes, `MASS_GENE`), modeoverzicht in de
   `.mess` en de log.
3. **Statische verrijking** (instelling *Statische correctie*, standaard aan): de
   statische respons op elke lastvector (`MACRO_ELAS_MULT`) komt bij de modes
   (`DEFI_BASE_MODALE` `RITZ`, `ORTHO`), daarna het eigenprobleem op die kleine basis
   (`CALC_MODES` `QZ`) en terug (`REST_GENE_PHYS`). Dat is de werkwijze van Code-Aster's
   eigen `DYNA_LINE` met `ENRI_STAT='OUI'` (de standaard daar;
   `MacroCommands/dyna_line_ops.py`). De extra vectoren worden "pseudo-modes" hoog
   boven de echte modes (in de `.mess`: `BRIDGE_HARM_VERRIJKING`); ligt de statische
   vorm al in de modes (1 vrijheidsgraad), dan valt hij weg.
4. **Demping:** per vector van de basis ξ_i = α/(2ω_i) + β·ω_i/2 + ζ als `AMOR_MODAL`
   (zoals §2.3; per mode in de `.mess`, `BRIDGE_DEMPING`). Basis `PHYS`: C = αM + βK
   (+ `AMOR_MECA` van de dempers) als `MATR_AMOR`; `modal_damping` bestaat daar niet.
   Is een ξ_i ≥ 1, dan print de job `BRIDGE_HARM_WAARSCHUWING DEMPING` en meldt de bridge
   een WARNING (ook vóór de run als `modal_damping` ≥ 1); de stationaire respons
   bestaat ook dan, alleen zonder resonantiepiek (HR-01a met ζ = 1,5 doorgerekend:
   |U| binnen 4,4e-8 van de exacte oplossing).
   **Verliesfactor** η (`loss_factor`, `#ASTER-HYST`): `AMOR_HYST` in `ELAS` van
   `DEFI_MATERIAU` en, bij veren, in `AFFE_CARA_ELEM` `DISCRET`; `ASSEMBLAGE` maakt
   daarmee de complexe stijfheid `RIGI_MECA_HYST` = K(1 + iη) (U2.06.03, Aubry,
   2023, §6). Basis `PHYS`: `DYNA_VIBRA` met die matrix als `MATR_RIGI`. Basis `GENE`:
   de projectie op de modes met `PROJ_MATR_BASE` (`PROJ_BASE` neemt alleen reële
   matrices) in volle opslag, dus een complexe gegeneraliseerde stijfheid, exact ook
   als η per materiaal verschilt (dan koppelen de modes); de modes zelf komen uit de
   reële K. Voor de verfijning rond de pieken telt ξ_i + η/2 (grootste η).
5. **Frequenties:** het bereik (lin/log) of de lijst; bij het bereik per mode in het
   bereik met 0 < ξ < 0,5 nog *n* frequenties over de halfwaardebreedte 2ξf rond de
   piek f·√(1−2ξ²) (`DEFI_LIST_FREQ` `RAFFINEMENT` `CRITERE='LARGEUR_3DB'`,
   `NB_POINTS` = *n*; bij een oneven *n* precies op de piek).
6. `DYNA_VIBRA` `TYPE_CALCUL='HARM'` met `EXCIT` per lastvector: `COEF_MULT=1` (of
   `FONC_MULT` = de tabel als `DEFI_FONCTION` van `FREQ`) en `PHAS_DEG` uit
   `#ASTER-FASE`. Gemeten: U = F·e^{iφ}/(k − mω² + iωc), dus naijlen is een negatieve
   fase (HR-01).
7. `REST_GENE_PHYS` (`DEPL`) en `CALC_CHAMP` `SIGM_NOEU` op de volume-elementen
   (complex). `aster_harmonic_export.py` schrijft per frequentie een `<mode>`. De
   **von Mises over een periode**: σ(t) = R·cos ωt − I·sin ωt, dus σ_vm² is een
   kwadratische vorm in cos 2ωt en sin 2ωt met maximum ½(q_RR + q_II) +
   √(¼(q_RR − q_II)² + q_RI²), exact berekend op de knoopspanning.

### 7.5 Interpretatie

- **Resonantie.** Bij een geïsoleerde mode met demping ξ is de piek ≈ (statische
  bijdrage van die mode)/(2ξ) bij f_n·√(1−2ξ²), de halfwaardebreedte 2ξ·f_n en de fase
  daar −90°. Onder de resonantie beweegt de constructie in fase met de last, ver erboven
  in tegenfase (−180°). Een kleine demping (ξ = 0,005: piek 100×) maakt het resultaat
  in de piek gevoelig voor de waarde van ξ: gebruik een gemeten of genormeerde demping.
- **Frequentiestap rond resonanties.** Een piek is 2ξ·f_n breed; een gewone stap mist
  hem. De verfijning (*Extra frequenties per resonantie*) legt punten op elke piek in
  het bereik (HR-01a: piekamplitude en -frequentie exact). Met een frequentielijst of
  zonder demping is er geen verfijning: kies dan zelf frequenties rond f_n (de
  eigenfrequenties staan in de log).
- **Aantal modes en modale truncatie.** Alleen de gerekende modes doen dynamisch mee.
  Met statische verrijking (standaard) is het quasi-statische deel van de hogere modes
  er wel, dus is de respons onder de hoogste mode goed (HR-02a: 6,6e-4 van de exacte
  oplossing, net als de directe berekening). Zonder verrijking mist een constante fout
  (HR-02c: 6,2e-4 × u_st), die groot wordt waar de respons klein is: bij een
  **antiresonantie** (bij een kracht en verplaatsing op dezelfde plek ligt tussen twee
  resonanties een frequentie met bijna geen beweging) en boven de laatste modes.
  Vuistregel: de hoogste mode ≥ 1,5–2× de hoogste frequentie (NIET geverifieerd in
  een bron); controleer twijfel met basis `PHYS` of meer modes. Boven de hoogste mode
  van de basis geeft de bridge een WARNING.
- **Fase.** Per richting ten opzichte van de last met fase 0. Twee punten met fase 0
  en ±180° bewegen in tegenfase. Bij meerdere lasten met verschillende fasen is er
  geen enkele "vorm": de vervormde vorm in Mecway (Re) is het moment ωt = 0.
- **Spanningen.** `stressxx`… is het moment ωt = 0, `stressamp…` de amplitude per
  component (die vallen niet tegelijk), `vonmises` het maximum over de periode (≥ de
  von Mises van `stressxx`…). Op knoopgemiddelde spanningen; bij een grof mesh lager
  dan de spanning in het element. Voor vermoeiing is de amplitude per component of
  de hoofdspanningsamplitude nodig (niet als veld).
- **Demping.** α (massa) dempt vooral de lage, β (stijfheid) de hoge modes; met alleen
  β is ξ ∝ f. Extra modale demping geeft alle modes dezelfde ξ.
- **Handcontrole** (1 vrijheidsgraad k, m): \|U\| = u_st/√((1−r²)² + (2ξr)²), fase
  −atan2(2ξr, 1−r²), r = f/f_n, u_st = F/k (Clough & Penzien, 1993, hoofdstuk 3).
  Met verliesfactor η: \|U\| = u_st/√((1−r²)² + η²), de piek precies bij f_n en
  gelijk aan u_st/η, fase daar −90° (Aubry, 2023, §3.3.4). Bij een balk of volume:
  (statische bijdrage van de mode)/η.

### 7.6 Wat niet kan

- **Opgelegde (basis)beweging** ≠ 0 (ERROR): de modes hebben die vrijheidsgraden vast.
  Een gelijkmatige versnelling van alle steunpunten (tafel, vloer) is in relatieve
  coördinaten een traagheidslast: een *Gravity* met de versnellingsamplitude in de
  tegengestelde richting geeft de beweging **ten opzichte van de steunpunten**
  (theorie, Clough & Penzien, 1993; NIET apart geverifieerd).
- Frequentieafhankelijke demping (ook een η die met de frequentie verandert).
  Verliesfactor bij andere discrete elementen dan Mecway-veren (*Elastic support*,
  dempers, puntmassa's): niet vertaald (η = 0 daar).
- Spanningen bij een verliesfactor: `CALC_CHAMP` rekent ze uit de verplaatsing met de
  reële E (NIET geverifieerd in de broncode of het η-deel meetelt); met de factor
  (1 + iη) zou de amplitude √(1 + η²) groter zijn (0,5% bij η = 0,1).
- Dempers op modale basis (ERROR; basis `PHYS` wel), `modal_damping` direct (ERROR).
- Voorspanning door de belastingen (Mecway's *Frequency* met belastingen rekent
  voorgespannen modes; hier zijn de belastingen de harmonische last).
- Thermische rek, contact, gaps, tension/compression only, plasticiteit (ERROR).
- Spanningen in schalen en balken (alleen verplaatsingen en rotaties), reacties,
  element-knoopspanningen.
- Vergelijking met een Mecway-solve: Mecway heeft geen harmonische analyse (INFO).
- De weergave in de Mecway-GUI (lijst per frequentie, animatie, contour) is NIET
  bekeken. Mecway's API leest het resultaat wel (headless `mecway.exe <model> script
  <script.py>` op HR-02a: `solution.modes()` 120 frequenties, `frequency(m)` en
  `node_value` van `disply`, `displiy`, `displampy`, `displphasey`, `displmag`, `rotz`,
  `rotampz` gelijk aan de bridge-waarden).

### 7.7 Meldingen en oplossingen (harmonisch)

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Harmonische analyse zonder opleggingen | starre bewegingen | leg het model in Mecway vast |
| ERROR: Harmonisch: geen belasting ... | geen kracht, druk, gravity, ... | breng de harmonische last aan (waarde = amplitude) |
| ERROR: Opgelegde verplaatsing of rotatie <> 0 op ... | basisbeweging niet vertaald | waarde 0; een gelijkmatige basisversnelling als gravity (§7.6) |
| ERROR: Harmonisch: een opgelegde verplaatsing met een tabel ... | idem | tabel weg of waarde 0 |
| ERROR: Dempers (...) kunnen niet in de harmonische analyse op modale basis | niet-proportionele demping | basis `PHYS`, of Rayleigh-demping |
| ERROR: Extra modale demping ... bestaat alleen op modale basis | `modal_damping` > 0 met basis `PHYS` | basis `GENE` of `modal_damping` 0 |
| ERROR: Harmonisch: frequentielijst (harm_freq_list) '...' is ongeldig | geen getallen of < 0 | bijv. `5, 10, 20` (punt als decimaalteken), of `0` |
| ERROR: Harmonisch: frequentiebereik ... is ongeldig | start ≤ 0, eind < start, aantal < 1 | instellingen op de pagina |
| ERROR: Harmonisch: basis (harm_basis) '...' is onbekend | schrijffout in `#ASTER-OPTIE` | `GENE` of `PHYS` |
| ERROR: Harmonisch: '#ASTER-FASE ...': verwacht 'selectie = fase in graden' | schrijffout | bijv. `** ASTER-FASE Last2 = 180` |
| ERROR: Harmonisch: #ASTER-FASE: '...' is geen selectie met een belasting | naam onbekend of zonder belasting | de naam van de selectie van de belasting, precies als in Mecway |
| ERROR: Harmonisch: een last op ... heeft verschillende fasen | één last op meerdere selecties (bijv. samengevoegde balklasten) | elke selectie een eigen belasting |
| ERROR: Thermische rek ... wordt in de harmonische analyse niet vertaald | *Thermal stress* aan | uitzetten |
| ERROR: Verliesfactor (loss_factor) ... is ongeldig | negatief of geen getal | een getal ≥ 0 |
| ERROR: '#ASTER-HYST ...': verwacht 'materiaal = eta' ... / materiaal '...' bestaat niet | schrijffout of onbekende naam | bijv. `** ASTER-HYST Staal = 0.02`, de naam zoals in Mecway (hoofdletters maken niet uit) of `*` |
| WARNING: Verliesfactor bij het hyperelastische materiaal ... wordt genegeerd | `ELAS_HYPER` kent geen `AMOR_HYST` | geen actie (de harmonische analyse is lineair) |
| WARNING: Harmonisch: het model heeft geen demping ... | geen Rayleigh, `modal_damping`, `loss_factor` of dempers | demping opgeven of frequenties tussen de eigenfrequenties |
| WARNING: Harmonisch: dempingsverhouding >= 1 (...), overkritisch ... De berekening gaat door. | een mode met ξ ≥ 1: `modal_damping` ≥ 1, of Rayleigh α (lage modes) of β (hoge modes) te groot | controleer α/β en *Extra modale demping* (vaak een eenheidsfout); ξ per mode in de `.mess` (`BRIDGE_DEMPING`). Bedoeld overkritisch: geen actie nodig |
| WARNING: Harmonisch: de hoogste frequentie (...) ligt boven de hoogste mode ... | te weinig modes voor het bereik | meer modes (*Number of modes*), basis `PHYS`, of een lagere eindfrequentie |
| WARNING: Modale basis: effectieve massa (som over ... modes) onder 90% in de belaste richting(en): ... | basis `GENE` met te weinig modes in de richting van de last (§3) | meer modes (*Number of modes*, of `modal_modes`), of basis `PHYS` (`harm_basis`) |
| WARNING: Harmonisch: meetpunt '...' is een vlakselectie ... | `MEETPUNT_` op een vlak of element | maak een *Node selection* |
| Code-Aster meldt: Respons op modale basis: een mode met frequentie <= 0 | mechanisme of los deel | leg het model volledig vast |

### 7.8 Verificatie

[Verificatie.md](Verificatie.md) §7 (HR-01 … HR-05): massa op een veer met modale
demping, Rayleigh α (GENE en PHYS) en een demper (ζ = 0,2): amplitude en fase over
het hele bereik binnen 6e-8 en 1e-5° van de exacte oplossing (criterium 1% en 1°),
piek en piekfrequentie exact; uitkragende balk (Euler-Bernoulli, Rayleigh α): GENE
met verrijking en PHYS binnen 6,6e-4 van de exacte receptantie over 1–200 Hz
(twee resonanties en een antiresonantie), GENE = PHYS binnen 1,9e-5; zonder
verrijking het statische deel van de weggelaten modes 6,22e-4 = 1 − Σ12/λ_i⁴ (−0,06%);
hex20-console GENE = PHYS: verplaatsing 4e-6, von Mises 4e-5, σ_xx-amplitude 2,3e-3;
fase met `#ASTER-FASE`, amplitude uit een tabel, twee lasten in tegenfase en de
meetpunt-CSV exact. Verliesfactor (HR-06): massa op een veer met η = 0,04 (GENE met
`loss_factor`, PHYS met `#ASTER-HYST`): amplitude en fase binnen 4,3e-8 en 7e-6°, de
piek u_st/η = 0,25 m (PHYS bij f_n exact, fase −90,00°); balk met η = 0,02 (GENE en
PHYS) binnen 2,1e-4 van de Euler-Bernoulli-receptantie met E(1 + iη) over 1–200 Hz,
de piek bij f₁ gelijk aan (12/λ₁⁴)·u_st/η (−0,003%).

## 8. Bronnen

- Aubry, J.-P. (2023). *Beginning DYNAmics with code_aster*, §3.3 en §11.3: de
  cumulatieve effectieve massa van de modale basis (minstens 90% in de belaste
  richting) als controle van een respons op modale basis; §3.3.4, §6 en bijlage §2.3:
  hysteretische demping (`AMOR_HYST`, `RIGI_MECA_HYST`, η/2 als equivalente ξ).
- Code-Aster, U2.06.03 (demping in dynamische berekeningen) en U4.53.11
  (`DYNA_VIBRA` harmonisch); catalogi `defi_materiau.py`, `affe_cara_elem.py`
  (`AMOR_HYST`), `proj_base.py`/`proj_matr_base.py` en `MacroCommands/assemblage_ops.py`
  (`RIGI_MECA_HYST` uit `RIGI_MECA`), versie 17.4.
- Bishop, R.E.D. & Johnson, D.C. (1960). *The Mechanics of Vibration*. Cambridge:
  Cambridge University Press (receptanties van balken). Niet lokaal ingezien; de
  receptantie van de console is afgeleid en nagerekend (statische limiet L³/3EI, polen
  bij de eigenfrequenties; HR-02b binnen 6,6e-4).
- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold, tabel 8-1. Niet lokaal ingezien; nagerekend in de verificatie.
- Clough, R.W. & Penzien, J. (1993). *Dynamics of Structures* (2nd ed.). New York:
  McGraw-Hill, hoofdstuk 3 en 4. Niet lokaal ingezien; de formules zijn nagerekend in
  de verificatie (MD-01 … MD-04).
- EDF R&D (2025). *code_aster 17.4, catalogi* `dyna_vibra.py`, `proj_base.py`,
  `rest_gene_phys.py`, `calc_vect_elem.py` (`lib/aster/code_aster/Cata/Commands`) en
  testcase forma12d (`share/aster/tests`); voor de harmonische respons ook
  `defi_list_freq.py`, `defi_base_modale.py`, `dyna_line.py`, de macro
  `MacroCommands/defi_list_freq_ops.py` en `dyna_line_ops.py` (statische verrijking
  `ENRI_STAT`), en de testcases sdld21b (`DEFI_LIST_FREQ` `RAFFINEMENT`) en sdld313d
  (`DYNA_VIBRA` `HARM` `PHYS` en `GENE`).
- EDF R&D (2023). *Forma 12d – Calcul transitoire sur base généralisée avec
  correction statique a posteriori* (trainingspresentatie, lokale kopie).
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite
  Element Analysis*. Mineola: Dover, §9.3.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: §6.4 Dynamic
  Response, §9.26 Rayleigh damping, §11.24 DampedVibratingStrip.
