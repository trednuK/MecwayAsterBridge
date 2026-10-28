# Responsspectrumanalyse (aardbeving, schok)

*English version: [Response_spectrum.md](en/Response_spectrum.md)*

Een responsspectrum geeft per eigenfrequentie (of periode) de grootste versnelling
van een 1-vrijheidsgraadsysteem onder een grondbeweging, zoals een aardbeving of een
schok. De spectrumanalyse rekent daarmee de grootste respons van de constructie
zonder een berekening in de tijd: per mode de respons op het spectrum en daarna een
combinatie over de modes en de richtingen. Mecway heeft geen spectrumanalyse (Mecway
Ltd., 2026, hoofdstuk 6); de bridge rekent hem met Code-Aster:

| Mecway | Bridge-analyse (pagina) | Code-Aster | Resultaat in Mecway |
|---|---|---|---|
| *Frequency* (V30) met een *Gravity* met tabel als spectrum | `spectrum_3d` (Responsspectrum) | `CALC_MODES` → `COMB_SISM_MODAL` (`MONO_APPUI`), met missing mass `MODE_STATIQUE` | een stap met de maxima: verplaatsing, absolute versnelling, spanningen, von Mises, reacties |

Wanneer gebruiken: een lineair model onder een aardbevingsspectrum uit een norm of
een schokspectrum (bijv. een ontwerpspectrum voor transport of een
stootbelasting). Voor de respons in de tijd op een bekend tijdsverloop:
[Respons_op_modale_basis.md](Respons_op_modale_basis.md). Voor alleen de
eigenfrequenties: [Modaal_en_knik.md](Modaal_en_knik.md).

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Analysetype** *Frequency* (V30) met het **aantal modes** (*Number of modes*).
   Neem zoveel modes dat ze samen ~90% van de massa dragen in elke richting van het
   spectrum (§3), of laat de missing mass aan (standaard, §1.2). De log geeft de
   effectieve massa per richting (§1.3).
2. **Materiaal** met een **dichtheid**; puntmassa's (*Mass*) tellen mee.
3. **Opleggingen** (*Fixed*, *Displacement* = 0, ...): de grond beweegt via alle
   opleggingen tegelijk (één spectrum voor alle steunpunten). Een opgelegde
   verplaatsing ≠ 0 of met een tabel kan niet (§4).
4. **Het spectrum** is een **Gravity** met een **tabel** per richting:
   - Klik *Gravity*, en geef de X-, Y- en/of Z-component een **tabel** (*Table*). In
     de kolom *time* staat de **periode T in s** (standaard; of de frequentie in Hz,
     instelling *Spectrumtabel: kolom 'time' is*), als waarde de **spectrale
     versnelling** in m/s². Een tabel kun je uit een spreadsheet plakken.
   - Tussen de punten interpoleert de bridge lineair (in T), buiten de tabel geldt de
     eerste of laatste waarde, zoals bij elke Mecway-tabel (Mecway Ltd., 2026,
     hoofdstuk 9).
   - Een component **zonder tabel** met een waarde ≠ 0 is een **vlak spectrum** (overal
     die versnelling). Een component 0 heeft geen spectrum: die richting doet niet
     mee.
   - Elke richting met een spectrum wordt apart gerekend en daarna met de
     richtingscombinatie samengevoegd (§1.2). Het teken van een waarde speelt geen
     rol.
   - In deze analyse is de gravity **geen last**: er is geen eigen gewicht. Andere
     belastingen (krachten, druk, ...) doen niet mee (WARNING).
5. **Demping**: de dempingsverhouding van de modes is een instelling (standaard 5%,
   §1.2); *Rayleigh damping* in Mecway telt per mode op. Het spectrum moet bij die
   demping horen.

Voorbeeld: elastisch spectrum EN 1998-1 type 1, grondtype B (S = 1,2; T_B = 0,15 s,
T_C = 0,5 s, T_D = 2,0 s; NEN-EN 1998-1, §3.2.2.2, tabel 3.2), 5% demping (η = 1),
a_g = 1 m/s². Tabel van de Y-component (periode in s, versnelling in m/s²):

| T [s] | 0 | 0,15 | 0,5 | 0,6 | 0,8 | 1,0 | 1,5 | 2,0 | 3,0 | 4,0 |
|---|---|---|---|---|---|---|---|---|---|---|
| S_e [m/s²] | 1,2 | 3,0 | 3,0 | 2,5 | 1,875 | 1,5 | 1,0 | 0,75 | 0,333 | 0,1875 |

Tussen T_C en T_D daalt het spectrum met 1/T: lineaire interpolatie tussen de punten
ligt daar iets boven de kromme (aan de veilige kant); neem meer punten voor een
nauwkeuriger spectrum. Controleer de waarden voor je land (nationale bijlage) en
vermenigvuldig met a_g. Dit is een illustratie, geen ontwerpspectrum.

### 1.2 In het hoofdvenster van de bridge

1. **Actieve analyse**: kies **`spectrum_3d`** zelf. `auto` kiest bij *Frequency* de
   modale analyse (`modal_3d`): het Mecway-model zegt niet dat het een spectrum is.
2. **Resultaten naar Mecway** moet `liml` zijn (pagina Algemeen).
3. Pagina **Responsspectrum**:

| Instelling (label) | Sleutel | Standaard | Wanneer aanpassen |
|---|---|---|---|
| Resultaatvelden naar Mecway | `fields` | `displacements`, `accelerations`, `stresses`, `vonmises`, `reactions` | velden uitzetten voor een kleinere `.liml`. `velocities` en de plastische rek horen niet bij deze analyse (INFO) |
| Aantal modes (zonder maxmode in Mecway) | `modal_modes` | 20 | alleen als het Mecway-model geen *Number of modes* heeft |
| Controle modes (VERI_MODE SEUIL) | `modal_tolerance` | 1e-6 | zoals bij modaal ([Modaal_en_knik.md](Modaal_en_knik.md) §1.2) |
| Spectrumtabel: kolom 'time' is | `spectrum_abscissa` | `period` | `frequency` als je spectrum in Hz gegeven is (het getal in de kolom *time* is dan de frequentie) |
| Modale demping (fractie van kritisch) | `spectrum_damping` | 0.05 | de demping waarvoor het spectrum geldt (bijv. 0.02 voor gelast staal volgens sommige normen). Met Rayleigh-demping in Mecway: 0, anders tellen ze op |
| Combinatie modes | `modal_combination` | `CQC` | `SRSS` alleen als de frequenties goed gescheiden zijn (en de norm het vraagt); `ABS` als bovengrens |
| Combinatie richtingen | `direction_combination` | `SRSS` | `100-30-30` (EN 1998-1 §4.3.3.5.2 (4)), `100-40-40` (Newmark, standaard van Code-Aster) of `ABS`; alleen met meer dan één spectrumrichting |
| Missing mass (pseudo-modes, MODE_CORR) | `missing_mass` | aan | uit om alleen de modes te tellen (zoals veel normen bij ≥ 90% effectieve massa); dan WARNING onder 90% |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | | 1800 s, 2048 MB, 8 | grote modellen |

De elementkeuzes op de pagina **Elementen** gelden ook hier (hex8 met `3D` is te stijf
bij buiging, KNOWN_BUGS 1).

Per model kan een instelling ook met `#ASTER-OPTIE` (bijv. `#ASTER-OPTIE
modal_combination = SRSS`; [ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md)).
Een eigen Code-Aster-spectrum per richting, bijvoorbeeld spectra voor meerdere
dempingen of in een andere grootheid: `#ASTER-SPECTRE` (§2.2).

### 1.3 Starten en volgen

- **Log en statusvak** na afloop: de modes met frequentie en effectieve massa (zoals
  bij modaal), daarna per richting de **effectieve massa van de modes** (`Spectrum Y:
  effectieve massa van de modes 61.2%`), bij missing mass de afsnijfrequentie en het
  spectrum daar, en de **totale reactiekracht** (*base shear*) per richting, correct
  gecombineerd (§3).
- **study.mess** (`<model>_<run-id>.mess`): per mode de frequentie, de demping en de
  spectrale versnelling per richting (`BRIDGE_SPECTRUM_MODE 1 FREQ=4.39309 XI=0.05
  SA_X=6.08555`), en de tabel van `COMB_SISM_MODAL` zelf ("VALEURS DU SPECTRE").
- **WARNING** als de modes in een spectrumrichting minder dan 90% van de massa dragen
  en de missing mass uit staat.

### 1.4 Resultaten in Mecway

Onder *Solution* staat **één stap** (geen tijdstappen, geen modes) met de maxima:

| Mecway-variabele | Betekenis |
|---|---|
| `displx/y/z`, `displmag` | grootste verplaatsing t.o.v. de grond (rotaties `rotx/y/z` bij balken en schalen) |
| `accx/y/z`, `accmag` | grootste **absolute** versnelling (grond + constructie), eigen namen van de bridge (Mecway kent geen versnellingsveld) |
| `stressxx` ... `stresszx` | grootste spanningscomponent (volume-elementen; per knoop en per element-knoop) |
| `vonmises` | von Mises per knoop, per mode berekend en gecombineerd (§3) |
| `reactionforcex/y/z`, `reactionforcemag` | grootste reactie per knoop |

## 2. Hoe de bridge vertaalt

### 2.1 Keten

1. `ASSEMBLAGE` (`RIGI_MECA`, `MASS_MECA` met de opleggingen) en `CALC_MODES`
   `PLUS_PETITE` met `NORM_MODE='MASS_GENE'`, zoals de modale analyse
   ([Modaal_en_knik.md](Modaal_en_knik.md) §2.1), zonder voorspanning. Op de modes
   `CALC_CHAMP` met `REAC_NODA` en, voor spanningen, `SIGM_ELNO`/`SIGM_NOEU` op de
   volume-elementen (zoals testcase sdlx02a).
2. Per richting het spectrum als `FORMULE` in `AMOR` en `FREQ` (de tabel, lineair in
   de periode of frequentie, constant buiten de tabel), of de eigen `DEFI_NAPPE` van
   `#ASTER-SPECTRE`.
3. Dempingsverhouding per mode ξ_i = α/(2ω_i) + β·ω_i/2 + `spectrum_damping`
   (Mecway's Rayleigh-demping, Mecway Ltd., 2026, §9.26) als `AMOR_REDUIT`. ξ_i ≥ 1
   of een mode met f ≤ 0 stopt de job met een melding (§5).
4. Missing mass (standaard): `MODE_STATIQUE` `PSEUDO_MODE` per spectrumrichting (de
   statische respons ψ op een eenheidsversnelling) met dezelfde `CALC_CHAMP`.
5. `COMB_SISM_MODAL` `TYPE_ANALYSE='MONO_APPUI'` met `OPTION` `DEPL`, `ACCE_ABSOLU`,
   `REAC_NODA`, `SIGM_ELNO`, `COMB_MODE` en `COMB_DIRECTION` uit de instellingen, en
   bij missing mass `MODE_CORR='OUI'` met `FREQ_COUP` = de hoogste gerekende
   frequentie. Met `100-30-30` vraagt de bridge de respons per richting
   (`TYPE_RESU` `VALE_DIRE`) en combineert zelf.
6. `aster_spectrum.maxima`: de maxima als een resultaat met één index (`CREA_RESU`),
   `CALC_CHAMP` `SIGM_NOEU`, von Mises (§3), en `aster_results_export` schrijft één
   stap naar de `.liml`.

### 2.2 Wat Code-Aster per mode rekent

Uit de macro `comb_sism_modal_ops.py` (Code-Aster 17.4), per richting d en mode i,
met Γ_i,d de participatiefactor (`FACT_PARTICI_D*`), φ_i de massa-genormeerde vorm en
S_i = S_d(ξ_i, f_i):

- verplaatsing, spanning, reactie: R_i = S_i·Γ_i,d/ω_i² · (φ_i, σ_i, r_i);
- absolute versnelling: R_i = S_i·Γ_i,d·φ_i, plus altijd de rest (1 − Σ Γ_i,d·φ_i)·S(f_c)
  (de constructie beweegt voor de hoge modes mee met de grond);
- modale combinatie: SRSS √(Σ R_i²); CQC √(Σ_i Σ_j ρ_ij R_i R_j) met de correlatie van
  Der Kiureghian (1981): ρ_ij = 8√(ξ_iξ_j)(ξ_i ω_i + ξ_j ω_j)ω_iω_j·√(ω_iω_j) /
  ((ω_i² − ω_j²)² + 4ξ_iξ_jω_iω_j(ω_i² + ω_j²) + 4(ξ_i² + ξ_j²)ω_i²ω_j²); ABS Σ|R_i|;
- missing mass: R_c = (ψ_d − Σ Γ_i,d/ω_i² · φ_i)·S(f_c), kwadratisch opgeteld:
  √(R_m² + R_c²), met f_c de afsnijfrequentie;
- richtingen: SRSS √(R_X² + R_Y² + R_Z²); 100-40-40 (`NEWMARK`): de grootste van
  R_a + 0,4 R_b + 0,4 R_c; 100-30-30 (bridge): de grootste van R_a + 0,3 R_b + 0,3 R_c.

`CORR_FREQ` staat uit (de spectra zijn pseudo-versnellingen bij de ongedempte
frequentie), `NATURE` is `ACCE`. Met `#ASTER-SPECTRE` kun je beide per richting
anders zetten.

**Eigen spectrum (`#ASTER-SPECTRE`).** In het custom-model-veld van Mecway
([ASTER_regels_voorbeelden.md](ASTER_regels_voorbeelden.md) §2): `#ASTER`-code met
een `DEFI_NAPPE` (parameter `AMOR`, functies van `FREQ`) of een `FORMULE` in `AMOR`
en `FREQ`, en `#ASTER-SPECTRE X, Y = naam` voor de richtingen; extra sleutelwoorden
voor `SPECTRE` achter een komma (`ECHELLE=9.81`, `NATURE='DEPL'`, `CORR_FREQ='OUI'`).
Zo'n richting heeft geen gravity-tabel nodig; een gravity in dezelfde richting wordt
dan genegeerd (INFO). Een `DEFI_FONCTION` alleen in `FREQ` kan niet
(`COMB_SISM_MODAL` vraagt een nappe of formule). Verificatie SP-01 (testcase
sdld25a).

## 3. Interpretatie

- **Maxima zonder teken.** Elke waarde is het grootste verwachte (absolute) maximum
  op die plek, en elke component apart. De maxima vallen niet op hetzelfde moment:
  een verplaatsingsveld uit maxima is geen evenwichtstoestand, `displmag` en
  `accmag` zijn een bovengrens (√ van de som van de kwadraten van de maxima), en
  spanningscomponenten mag je niet tot een hoofdspanning combineren.
- **Totale reactie niet optellen.** De som van de reacties per knoop is groter dan
  de werkelijke totale reactie: tel in Mecway dus niet `reactionforce*` op. De log
  geeft de **totale reactiekracht per richting** (`Totale reactiekracht
  (gecombineerd)`): per mode de som over alle knopen, daarna gecombineerd zoals de
  velden (verificatie SP-02 … SP-04, SP-07).
- **von Mises** is per mode berekend (VM_i uit de spanningen van mode i) en
  gecombineerd met dezelfde regel, plus de missing mass. Bij SRSS is dat precies de
  verwachtingswaarde van de kwadratische vorm σᵀPσ (modes onafhankelijk); bij CQC
  een bovengrens (|σ_iᵀPσ_j| ≤ VM_i·VM_j). Von Mises uit de gecombineerde componenten
  (zoals sommige programma's doen) kan te laag zijn, bijv. bij afschuiving.
- **Genoeg modes?** Kijk naar de effectieve massa per richting in de log. Veel normen
  vragen ~90% (bijv. EN 1998-1 §4.3.3.3.1: modes tot 90% van de massa en alle modes
  met meer dan 5%). Met missing mass (standaard) telt de rest quasi-statisch mee met
  het spectrum op de hoogste gerekende frequentie; dat is goed als het spectrum
  daar al op zijn eindwaarde (de piekgrondversnelling, *ZPA*) is. Ligt de hoogste
  frequentie nog op het plateau, reken dan meer modes.
- **CQC of SRSS.** Bij modes met dicht bij elkaar liggende frequenties (binnen ~10%,
  of een kleine massa op een grote) geeft SRSS een verkeerde waarde (te hoog of te
  laag); CQC houdt rekening met de correlatie (SP-03: ρ = 0,17 bij f₂/f₁ = 1,25 en 5%
  demping; verplaatsing m2 −6,5% t.o.v. SRSS, totale reactie +7,9%).
- **Absolute versnelling** (`accel*`) is de versnelling van de massa zelf (voor
  apparatuur op de constructie); bij een opgelegde knoop is het de grondversnelling op
  de afsnijfrequentie.
- **Handcontrole** (1-vrijheidsgraad, massa m, ω = √(k/m)): verplaatsing S(T)/ω²,
  reactie m·S(T), absolute versnelling S(T). Ingeklemde balk, mode 1: tipverplaatsing
  1,566·S/ω₁², totale reactie 0,613·m·S (Euler-Bernoulli, uit de vorm van Blevins,
  1979, tabel 8-1; verificatie SP-07).

## 4. Wat niet kan

- Een spectrum per steunpunt (`MULT_APPUI`, verschillende grondbewegingen) en
  `ENVELOPPE`: de grond beweegt overal hetzelfde (`MONO_APPUI`).
- Opgelegde verplaatsingen ≠ 0 of met een tabel (ERROR); belastingen doen niet mee.
- Contact, gaps, tension/compression only (ERROR: lineair).
- Spanningen op schalen en balken (alleen verplaatsingen en reacties; INFO), en
  snelheden (pseudo-snelheid).
- Een spectrum dat met de demping varieert uit een gravity-tabel (één spectrum voor
  alle modes); daarvoor `#ASTER-SPECTRE` met een `DEFI_NAPPE`. Mecway's
  Rayleigh-demping maakt ξ per mode verschillend (WARNING bij een tabel).
- Het teken van de respons, en combinaties met andere lastgevallen (zoals eigen
  gewicht): reken die apart en combineer volgens de norm.
- `auto` kiest deze analyse niet; vergelijken met Mecway's eigen oplossing kan niet
  (Mecway heeft geen spectrumanalyse; *Eerst Mecway-solve* slaat de vergelijking over).
- Zie KNOWN_BUGS 56.

## 5. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Spectrumanalyse zonder spectrum | geen gravity met een waarde en geen `#ASTER-SPECTRE` | breng een Gravity met tabel aan (§1.1) |
| ERROR: Spectrum X: negatieve periode/frequentie in de tabel | tabel begint onder 0 | controleer de kolom *time* |
| ERROR: Spectrumanalyse zonder opleggingen | geen steunpunten: de grond kan de constructie niet bewegen | leg het model vast |
| ERROR: Opgelegde verplaatsing of rotatie <> 0 / met een tijdstabel | alleen vaste opleggingen | zet de waarde op 0, haal de tabel weg |
| ERROR: ... kan niet in een spectrumanalyse (lineair) | contact, gap, tension/compression only | verwijder of onderdruk het |
| ERROR: Instelling ... is onbekend / spectrum_damping | keuze of waarde buiten de lijst | zie §1.2 |
| ERROR: De resultaatroute 'tabel' werkt niet | maxima alleen via `liml` | *Resultaten naar Mecway* = `liml` |
| ERROR: '#ASTER-SPECTRE ...': verwacht 'X, Y = naam' | schrijfwijze | `#ASTER-SPECTRE X = spec, ECHELLE=9.81` |
| WARNING: Spectrumanalyse: belastingen (...) doen niet mee | krachten, druk, ... in het model | gewenst (de belasting is het spectrum); reken eigen gewicht apart |
| WARNING: Het Mecway-model is geen Frequency-analyse | ander analysetype | kies *Frequency* in Mecway (Number of modes) |
| WARNING: De demping verschilt per mode (Rayleigh) ... | gravity-tabel met Rayleigh-demping | gewenst? Anders `#ASTER-SPECTRE` met een `DEFI_NAPPE` per demping |
| WARNING: Spectrum X: de modes dragen ...% van de massa (< 90%) | te weinig modes, missing mass uit | meer modes, of *Missing mass* aan |
| WARNING: Modaal: elset(s) ... hebben geen dichtheid | geen massa | geef het materiaal een dichtheid |
| Code-Aster meldt: Spectrumanalyse: dempingsverhouding >= 1 | overkritische demping in een mode (vaak een hoge mode met Rayleigh β) | verlaag β of `spectrum_damping`, of minder modes |
| Code-Aster meldt: Spectrumanalyse: een mode met frequentie <= 0 | mechanisme of los onderdeel | leg het model volledig vast |
| `SEISME_*` in de `.mess` | melding van `COMB_SISM_MODAL` (bijv. een `#ASTER-SPECTRE`-naam die geen nappe of formule is) | lees de tekst; controleer de `#ASTER`-code |
| `ALGELINE*` en andere `CALC_MODES`-meldingen | als bij modaal | [Modaal_en_knik.md](Modaal_en_knik.md) §4 |

## 6. Verificatie

[Verificatie.md](Verificatie.md) §7, *Responsspectrum (SP)*: Code-Aster-testcase
sdld25a nagebouwd met Mecway-veren en -massa's en het spectrum via `#ASTER-SPECTRE`:
frequenties en absolute versnellingen gelijk aan de TEST_RESU-waarden (≤ 1e-6
relatief); twee massa's met een tabel als spectrum: SRSS, CQC, missing mass en de
totale reactie gelijk aan de handberekening (≤ 1e-6); richtingscombinatie SRSS,
100-30-30 en 100-40-40 exact; ingeklemde hex20-balk: tipverplaatsing −0,02%,
spanning en von Mises +0,4%, totale reactie −0,1% t.o.v. Euler-Bernoulli. Mecway leest
het resultaat (één stap onder een *Frequency*-analyse) via zijn API (headless
nagelopen); de weergave in de Mecway-GUI is NIET geverifieerd.

## 7. Bronnen

- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold, tabel 8-1. Niet lokaal ingezien; nagerekend in de verificatie.
- CEN (2004). *EN 1998-1: Eurocode 8: Design of structures for earthquake resistance
  – Part 1*. §3.2.2.2 (elastisch spectrum), §4.3.3.3.1 (aantal modes), §4.3.3.5.2
  (combinatie van de richtingen). Niet lokaal ingezien; waarden uit het geheugen,
  controleer de norm en de nationale bijlage.
- Chopra, A.K. (2012). *Dynamics of Structures* (4th ed.). Upper Saddle River:
  Prentice Hall, hoofdstuk 13. Niet lokaal ingezien; de formules zijn nagerekend in
  de verificatie (SP-02 … SP-07).
- Der Kiureghian, A. (1981). A response spectrum method for random vibration
  analysis of MDF systems. *Earthquake Engineering and Structural Dynamics*, 9,
  419–435. Niet lokaal ingezien; de formule is die van Code-Aster
  (`comb_sism_modal_ops.py`, `cqc_array`).
- EDF R&D (2025). *code_aster 17.4*: catalogus `comb_sism_modal.py`, macro
  `MacroCommands/comb_sism_modal_ops.py`, testcases sdld25a en sdlx02a
  (`share/aster/tests`).
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: hoofdstuk
  6 (analysetypen), hoofdstuk 9 (tabellen), §9.26 Rayleigh damping.
