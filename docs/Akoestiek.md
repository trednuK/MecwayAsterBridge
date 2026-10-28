# Akoestiek: holtemodes, harmonisch drukveld en vibro-akoestiek

*English version: [Acoustics.md](en/Acoustics.md)*

De bridge rekent Mecway's *Acoustic Resonance 3D* (analysetype A30) met Code-Aster:
de eigenmodes (resonanties) van een lucht- of vloeistofvolume, zoals de staande golven
in een buis, een ruimte of een autocabine, en (§5) het drukveld per frequentie bij een
bron, met absorberende randen en microfoons (harmonische respons; Mecway zelf heeft
die analyse niet). §6 (vibro-akoestiek) koppelt het fluïdum aan een constructie: de
gekoppelde modes van bijv. een paneel op een luchtholte, een zuiger in een
vloeistofkolom of een tank met water (ook dat kan Mecway zelf niet). §7 rekent
hetzelfde gekoppelde model **per frequentie**: een trillend paneel dat geluid afstraalt,
een zuiger op een luchtkolom met een absorberend einde, een luidspreker in een kast
(verplaatsing van de constructie en druk/SPL in het fluïdum).

| Mecway-analyse | Bridge-analyse (pagina) | Wat Code-Aster rekent | Resultaat in Mecway |
|---|---|---|---|
| Acoustic Resonance 3D (A30) | `acoustic_modes_3d` (Akoestiek (holtemodes)) | `PHENOMENE='ACOUSTIQUE'`, matrices `RIGI_ACOU` en `MASS_ACOU` (`ASSEMBLAGE`), `CALC_MODES` | per mode de frequentie (Hz) en het drukveld `pressure` |
| Acoustic Resonance 3D (A30) met *Impedance* (§3.3) | `acoustic_modes_3d` (Akoestiek (holtemodes)) | dezelfde matrices + `AMOR_ACOU` per impedantierand; het kwadratische eigenwaardeprobleem lost de bridge in de job op met scipy (`aster_acoustic_complex.py`) | per mode de frequentie, de *decay rate* en het complexe drukveld `pressure` + `pressurei`, zoals Mecway |
| Acoustic Resonance 3D (A30) met een bron (`BRON_`-selectie, §5) | `acoustic_harm_3d` (Akoestiek (harmonisch)) | `PHENOMENE='ACOUSTIQUE'`, `RIGI_ACOU`, `MASS_ACOU`, `AMOR_ACOU`, `DYNA_VIBRA` `HARM` | per frequentie de complexe druk (`pressure`, `pressurei`), amplitude, fase en geluidsdrukniveau; microfoonrespons in de log en een CSV |
| Frequency 3D (V30) met een fluïdum-onderdeel (§6) | `vibroacoustic_modes_3d` (Vibro-akoestiek (modes)) | `PHENOMENE='MECANIQUE'`: `3D_FLUIDE` + `FLUI_STRU` + de constructie, `FORMULATION='U_P_PHI'`, `CALC_MODES` `BANDE` | per mode de frequentie, de verplaatsing van de constructie (`displ`) en de druk in het fluïdum (`pressure`) |
| hetzelfde model met een bron (§7) | `vibroacoustic_harm_3d` (Vibro-akoestiek (harmonisch)); zelf kiezen | als hierboven + `3D_FLUI_ABSO`, `DYNA_VIBRA` `HARM` `PHYS` met `MATR_IMPE_PHI` | per frequentie de complexe verplaatsing van de constructie en de complexe druk, amplitude, fase en SPL in het fluïdum; microfoons en meetpunten in de log en CSV's |

Het probleem is de Helmholtz-vergelijking ∇²p + (ω/c)²p = 0 voor de akoestische druk
p (Mecway Ltd., 2026, §6.9.1). De resultaten staan in Mecway zoals bij Mecway's eigen
oplossing: onder *Solution* een lijst *Mode 1, Mode 2, ...* met de frequentie. Algemene
werking van de bridge: [`Handleiding.md`](Handleiding.md); modale analyse van
constructies: [`Modaal_en_knik.md`](Modaal_en_knik.md).

## 1. Werkwijze stap voor stap

### 1.1 In Mecway: het model

1. **Mesh alleen het fluïdum.** Het lucht- of vloeistofvolume wordt gemesht, niet de
   wanden eromheen. Volume-elementen: hex8, hex20, wedge6, wedge15, tet4, tet10.
   Piramides, schalen en balken kunnen niet (Code-Aster heeft er geen akoestisch
   element voor; ERROR, §4). Een opening naar een grote ruimte (zoals de orgelpijp van
   Mecway's tutorial 17.13) mesh je mee als een stuk van die ruimte.
2. **Analysetype.** Kies *Acoustic Resonance 3D* en zet *Number of modes*.
   *Acoustic Resonance 2D* (A20) vertaalt de bridge niet (alleen 3D).
3. **Materiaal.** *Isotropic* met *Speed of sound* (bijv. 340 m/s voor lucht van
   15 °C, ~1480 m/s voor water). Een dichtheid is niet nodig: de modes hangen er niet
   van af. Mecway rekent akoestiek met één materiaal; de bridge kan ook meer media
   aan (bijv. twee gassen met een andere geluidssnelheid), maar alleen met **dezelfde
   dichtheid** (§3.2).
4. **Randen.**
   - Een vlak zonder voorwaarde is een **harde wand** (∂p/∂n = 0, Mecway Ltd., 2026,
     §6.9.1). Zonder andere voorwaarde is mode 1 de constante druk met 0 Hz.
   - **Fluid pressure = 0** (op knopen of vlakken) maakt een **drukknoop**: een plaats
     waar de druk nul blijft, bijv. het open einde van een buis (Mecway Ltd., 2026,
     §9.34). Een andere waarde dan 0 kan niet (ook Mecway weigert dat).
   - **Impedance** (absorberende rand, op vlakken) met *specific impedance* Z = R + iX
     in Pa·s/m (getal zonder eenheid; Mecway Ltd., 2026, §9.35): de modes worden
     **complex**, met een frequentie én een *decay rate* (uitdemping), zoals in Mecway
     (§3.3). Het materiaal moet dan een **dichtheid** hebben (de randterm is ρ/Z).
5. **Overige belastingen** (krachten, opleggingen, temperaturen, ...) doen in een
   akoestische analyse niet mee (INFO in de log). Contact (ook *bonded*),
   *node-surface coupling* en *constraint equations* vertaalt de bridge in de
   akoestiek niet: ze worden gemeld (ERROR, lijst aan het eind van de run) en
   weggelaten. Mesh het volume daarom als één doorlopend mesh.

### 1.2 In het hoofdvenster van de bridge

1. **Actieve analyse:** `auto` kiest bij A30 `acoustic_modes_3d`; of kies hem zelf.
2. **Resultaten naar Mecway** moet `liml` zijn (pagina Algemeen).
3. Pagina **Akoestiek (holtemodes)** (alleen aanpassen als dat nodig is):

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Aantal modes (zonder maxmode in Mecway) | 10 | alleen als het Mecway-model geen *Number of modes* heeft |
| Zoekfrequentie [Hz] (0 = laagste modes) | 0 | > 0: de modes het dichtst bij deze frequentie (`OPTION='CENTRE'`), bijv. rond een bromtoon of de toerentalfrequentie van een ventilator. Met 0 en harde wanden zonder drukknoop kiest de bridge zelf een kleine negatieve zoekfrequentie (§2) |
| Controle modes (VERI_MODE SEUIL) | 1e-6 | groter (bijv. 1e-4) als de log `ALGELINE5_15` meldt |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | grote modellen |

De elementkeuzes op de pagina **Elementen** (hex8 `3D`/`3D_SI`/`LINE_QUAD`) gelden hier
niet: de druk is een scalair veld en hex8 heeft geen last van de te grote stijfheid bij
buiging van constructies (KNOWN_BUGS 1); de bridge gebruikt altijd de elementen van het
mesh zoals ze zijn.

### 1.3 Starten en volgen

Klik *Starten*. In de log en het statusvak staan na afloop de frequenties per mode
(`Mode 2: 170 Hz`; met impedantie ook de decay rate, nagalmtijd T60 en Q, §3.3). Bij
harde wanden zonder drukknoop is mode 1 de constante druk met ~0 Hz (INFO, geen fout).
Met *Eerst Mecway-solve ter controle* vergelijkt de log per mode de frequentie van
Mecway en Code-Aster (alleen bij één materiaal: met twee rekent Mecway het model zelf
niet; met impedantie met de Mecway-mode met de dichtstbijzijnde frequentie, omdat
Mecway 0-Hz-modes willekeurig weglaat).

### 1.4 Resultaten in Mecway bekijken

- Onder *Solution* staan *Mode 1 ... Mode n* met de frequentie. Klik een mode en kies
  het veld **pressure** (Mecway's eigen naam): rood en blauw zijn drukbuiken met
  tegengesteld teken, de nullijn is een drukknoop.
- **De schaal van het drukveld heeft geen fysische betekenis** (Mecway Ltd., 2026,
  §6.9.1). De bridge normeert zoals Mecway (pᵀMp = 1 met M = ∫NᵀN/c² dV; bijv. de
  constante mode van een volume V heeft p = c/√V), dus de getallen zijn gelijk aan die
  van Mecway (verificatie AK-01…04: verschil < 1e-9). Het teken is willekeurig.
- Met impedantie staat bij elke mode ook de *decay rate* en zijn er twee velden:
  **pressure** (reëel deel van P) en **pressurei** (imaginair deel), zoals in Mecway's
  eigen oplossing (§3.3).
- De resultaten blijven ook los bewaard (`<model>_<run-id>_results.xml`), opnieuw in te
  laden met *Resultaten...* ([Handleiding §5.1](Handleiding.md#51-resultaten-later-opnieuw-inladen-kleine-liml)).

### 1.5 Interpretatie en controles

- **Handberekening** (vlakke golven in een buis met lengte L, geluidssnelheid c):
  - gesloten-gesloten (harde einden): f_n = n·c/(2L), n = 0, 1, 2, ... (n = 0 is de
    constante druk);
  - open-gesloten (p = 0 aan één einde): f_n = (2n − 1)·c/(4L);
  - open-open: f_n = n·c/(2L), n = 1, 2, ...;
  - rechthoekige ruimte met harde wanden: f_lmn = c/2·√((l/Lx)² + (m/Ly)² + (n/Lz)²).
  Een buis gedraagt zich zo tot de eerste dwarsmode, f ≈ c/(2·breedte).
- **Open einde:** p = 0 precies op het einde is een idealisatie. Een echte open pijp
  straalt uit en is akoestisch iets langer (eindcorrectie; Mecway's orgelpijp-tutorial,
  §17.13, telt de breedte van de pijp erbij). Wil je dat meenemen, mesh dan een stuk
  van de omgeving mee in plaats van p = 0 op te leggen.
- **Mesh-fijnheid:** de fout groeit met de frequentie. Gemeten
  ([`Verificatie.md`](Verificatie.md) §7, akoestiek AK):
  - hex8: Δf/f ≈ (kh)²/24 met k = 2π/λ en h de elementlengte (AK-03: 25 elementen per
    golflengte gaf +0,26%); voor 0,5% zijn ~18 elementen per golflengte nodig;
  - hex20: veel nauwkeuriger; 9 elementen per golflengte gaf +0,017% (AK-02, mode 5).
  Reken bij twijfel een tweede keer met een fijner mesh.
- **Twee media:** op het grensvlak zijn de druk en ∂p/∂n continu (zoals bij gelijke
  dichtheid); verificatie AK-05.

## 2. Hoe de bridge vertaalt

`bridge_acoustic.py` maakt de `.comm` (template `AsterTemplate_Akoestiek.comm`);
syntax volgens de Code-Aster-testcases ahlv100a en adlv101f:

1. `AFFE_MODELE` met `PHENOMENE='ACOUSTIQUE'`, `MODELISATION='3D'` op de volumes.
2. `DEFI_MATERIAU(FLUIDE=_F(RHO=ρ, CELE_R=c))` per materiaal (zonder dichtheid ρ = 1
   kg/m³: `RHO` is verplicht in Code-Aster, maar speelt in de modes geen rol, §3.2).
3. Drukknopen: `AFFE_CHAR_ACOU(PRES_IMPO=_F(GROUP_NO=... of GROUP_MA=..., PRES=0j))`.
4. `ASSEMBLAGE` met `RIGI_ACOU` en `MASS_ACOU` (complexe matrices) en de reële delen
   met `COMB_MATR_ASSE(PARTIE='REEL')`.
5. `CALC_MODES` met `OPTION='PLUS_PETITE'` (`NMAX_FREQ` = het aantal modes), of
   `OPTION='CENTRE'` rond de zoekfrequentie. Harde wanden zonder drukknoop maken de
   stijfheid singulier (de constante druk): `PLUS_PETITE` stopt dan met
   `ALGELINE3_81`. De bridge zoekt dan rond −0,1·c_min/(2D), met D de diagonaal van het
   omhullende blok van het volume (ruim onder de eerste mode met drukvariatie); dat
   staat als INFO in de log. `VERI_MODE` met `STOP_ERREUR='NON'` (zoals modaal).
6. `aster_results_export.py` schrijft per mode `<mode id="k" frequency="f Hz">` met de
   knoopvariabele `pressure`. `NORM_MODE` werkt in Code-Aster 17.4 niet voor
   akoestische modes (de vorm bleef op max |p| = 1); de bridge schaalt zelf met
   1/√`MASS_GENE` (pᵀMp = 1, zoals Mecway).

Met impedantie (complexe modes) wijken stap 3–6 af: zie §3.3.

## 3. Bijzonderheden

### 3.1 Mode met 0 Hz

Bij harde wanden zonder drukknoop is mode 1 de constante druk (een gelijkmatige
drukverhoging in het hele volume, frequentie 0). Mecway geeft hem ook (|f| van orde
1e-4…4e-3 Hz, numeriek nul; de bridge ~1e-5 Hz). Tel hem mee bij het aantal modes.
Daarbij hoort het alarm `ALGELINE3_82` in de `.mess`: onschuldig (§4).

### 3.2 Dichtheid en meer media

Code-Aster's `RIGI_ACOU` en `MASS_ACOU` bevatten de dichtheid niet (gemeten: ρ = 1,2 en
ρ = 1 geven dezelfde frequenties en vormen; NIET in de broncode nagelopen). Mecway
rekent ook zonder (K = ∫∇Nᵀ∇N dV, Mecway Ltd., 2026, §6.9.1). Voor één medium maakt dat
niets uit. Op een grensvlak tussen twee media is daardoor ∂p/∂n continu, wat alleen
klopt bij **gelijke dichtheid** (fysisch is (1/ρ)·∂p/∂n continu): een buis van twee
media met ρ = 1,2 en 12 kg/m³ gaf 248,98 Hz, waar 306,47 Hz juist is. Daarom stopt de
bridge met een ERROR als de materialen een verschillende dichtheid hebben. Twee media
met verschillende geluidssnelheid en gelijke dichtheid, of allebei zonder dichtheid,
rekent de bridge wel (AK-05, ≤ 0,03%); Mecway zelf geeft met twee materialen geen
oplossing. Heeft het ene medium wel een dichtheid en het andere niet, dan rekent de
bridge door met een **WARNING**: het grensvlak wordt dan behandeld alsof de dichtheden
gelijk zijn, wat alleen klopt als het medium zonder dichtheid werkelijk dezelfde
dichtheid heeft. Code-Aster krijgt voor dat medium ρ = 1 kg/m³; dat telt alleen voor
een snelheidsbron of impedantie op dat medium, en die vragen zelf een dichtheid
(ERROR). Vul dus bij elk medium de dichtheid in.

### 3.3 Impedantie: complexe modes

Een *Impedance*-rand (Mecway Ltd., 2026, §9.35) is een absorbeerder, of een rand met
een eigen "veer" of "massa": Z = p/vₙ is de verhouding tussen de druk en de
normaalsnelheid naar buiten, de *specific acoustic impedance* in Pa·s/m. In Mecway
*specific impedance (real)* R en *(imaginary)* X, dus Z = R + iX. Mecway rekent dan het
**kwadratische eigenwaardeprobleem** (Mecway Ltd., 2026, §6.9.2)

  (K + λC + λ²M)·P = 0,  K = ∫∇N·∇Nᵀ dV,  M = ∫NNᵀ/c² dV,  C = ∫(ρ/Z)·NNᵀ dA,

met λ = iω − σ en de druk in de tijd p(t) = Re(P·e^{λt}): elke mode heeft een
**frequentie** f = ω/2π en een **decay rate** σ (amplitude ∝ e^{−σt}). De bridge rekent
precies hetzelfde probleem (verificatie AI: gelijk aan Mecway tot 1e-8).

**Werkwijze:** zoals §1, met een *Impedance* op de absorberende vlakken. Geef het
materiaal een **dichtheid** (lucht 1,2 kg/m³): C bevat ρ. Mecway zelf rekent zonder
dichtheid met ρ = 0 (headless gezien: de impedantie werkt dan niet, een harde wand);
de bridge stopt dan met een ERROR. Meer impedantieranden met elk een eigen Z kunnen
(AI-10); twee impedanties op dezelfde vlakken tellen op (ρ/Z₁ + ρ/Z₂).

**Welke waarde voor Z** (ρc = 408 Pa·s/m voor lucht van 15 °C, ≈ 1,48·10⁶ voor water):

| Z | Betekenis | Reflectiefactor (loodrechte inval) R = (Z − ρc)/(Z + ρc) |
|---|---|---|
| Z → ∞ | harde wand (zoals zonder impedantie) | 1 |
| reëel, Z > ρc | gedeeltelijk absorberende wand | 0 < R < 1 |
| Z = ρc | volledig absorberend voor een loodrecht invallende vlakke golf ("oneindig lange buis"): geen resonanties | 0 |
| reëel, Z < ρc | "zachte" rand, richting een open einde (p = 0) | −1 < R < 0 |
| Z = iX, X > 0 | massa-achtige rand (bij e^{iωt} is een massa Z = iωm), geen demping; de frequenties gaan **omhoog** t.o.v. de harde wand (zoals een zware vrije zuiger: de 0-Hz-mode wordt een massa-veertrilling) | \|R\| = 1 |
| Z = iX, X < 0 | veer-achtige rand (Z = k/(iω)), geen demping | \|R\| = 1 |
| Re Z < 0 | de rand voert energie toe: modes groeien aan (negatieve decay rate; WARNING) | \|R\| > 1 |

In werkelijkheid hangt Z van de frequentie af; Mecway en de bridge gebruiken één vaste
Z per rand. Mecway's tip (§9.35): een configuratie per Z, en per mode de configuratie
kiezen waarvan Z bij die frequentie hoort.

**Resultaten:** per mode `<mode frequency="f Hz" decayrate="σ 1/s">` met de velden
`pressure` = Re P en `pressurei` = Im P (Mecway's namen en formaat). In de log en het
statusvak per mode f, σ, de **nagalmtijd T60 = 3·ln(10)/σ = 6,91/σ** (de tijd waarin
de mode 60 dB uitdempt) en de **kwaliteitsfactor Q = |λ|/(2σ)** (≈ π·f/σ; de halve-
waardebreedte van de resonantiepiek in een harmonische berekening is Δf ≈ f/Q ≈ σ/π).
In de `.mess` staat ook ζ = σ/|λ| (regel `BRIDGE_MODE ... ZETA`). Een mode met f = 0 en
σ > 0 is **niet-oscillerend**: de druk zakt zonder te trillen (bij een buis met Z > ρc
de "n = 0"-mode met σ = (c/L)·artanh(ρc/Z)). Mecway's API leest de modes van de
bridge (headless script: `solution.modes()`, `frequency(m)`, `node_value('pressure' /
'pressurei', .., mode=m)`); de weergave in de Mecway-GUI is nog niet bekeken
(KNOWN_BUGS 55).

**Handberekening** (buis met lengte L, harde wand op x = 0, Z op x = L, vlakke golven;
[`Verificatie.md`](Verificatie.md) §7 AI): tanh(λL/c) = −ρc/Z, dus
λₙ = (c/L)·(−artanh(ρc/Z) + iπn):
- reële Z > ρc: fₙ = n·c/(2L) (als de harde wand) en voor alle modes
  σ = (c/L)·artanh(ρc/Z); bijv. Z = 2000 Pa·s/m, L = 1 m: σ = 70,35 1/s, T60 = 0,098 s;
- reële Z < ρc: fₙ = (2n − 1)·c/(4L) (als een open einde) en σ = (c/L)·artanh(Z/(ρc));
- complexe Z: f schuift op (X > 0 omhoog, X < 0 omlaag) en σ = (c/L)·Re(artanh(ρc/Z));
- met een drukknoop op x = 0 in plaats van de harde wand: tanh(λL/c) = −Z/(ρc).
- De decay rate is gevoeliger voor de mesh dan de frequentie: hex8 met 20 elementen
  per meter gaf bij 340 Hz f +0,41% maar σ +1,7% (AI-09); hex20 met 20 per meter
  ≤ 0,1% tot 850 Hz (AI-01). Reken bij twijfel een tweede keer met een fijner mesh.

**Welke modes:** zoals Mecway (headless nagegaan): de 2 × *Number of modes*
eigenwaarden met de kleinste |λ| = |iω − σ|, en daarvan die met f ≥ 0, oplopend in
frequentie. Het aantal is daardoor niet altijd precies *Number of modes* (een ruimte
met maxmode 8 gaf in Mecway én in de bridge 10 modes). Sterk gedempte modes (grote σ)
kunnen ontbreken als je te weinig modes vraagt (Mecway Ltd., 2026, §6.9.2). Mecway laat
modes met 0 Hz (de constante druk zonder drukknoop, niet-oscillerende modes) door
afrondingsruis willekeurig weg of geeft ze dubbel; de bridge geeft ze altijd één keer,
met f = 0. Een eigenwaarde met een negatieve frequentie valt weg (hij hoort bij de
toegevoegde impedantie conj(Z)). Met een **zoekfrequentie** > 0 (pagina Akoestiek
(holtemodes)) geeft de bridge de *Number of modes* modes met f ≥ 0 waarvan λ het
dichtst bij i·2π·f ligt; een negatieve zoekfrequentie telt hier niet (WARNING).

**Schaal van P:** Mecway schaalt willekeurig (gemeten: Euclidische norm 1 met een
willekeurige fase). De bridge normeert zoals de reële modes: de fase zo dat PᵀMP reëel
is, dan PᴴMP = 1 en de grootste component van Re P positief. Bij Z → ∞ is dat precies
de reële holtemode (AI-03). Alleen verhoudingen en faseverschillen tussen knopen hebben
betekenis (AI: P(L)/P(0) gelijk aan Mecway tot 1e-7 en aan cosh(λL/c)).

**Hoe de bridge vertaalt** (`bridge_acoustic._complex_modes_comm`,
`aster_acoustic_complex.py`). Code-Aster's `CALC_MODES` kan dit probleem niet aan
(`MATR_AMOR` alleen voor verplaatsings- of gegeneraliseerde matrices, catalogus
`calc_modes.py`; `AFFE_CHAR_ACOU` kent geen impedantie; een complexe Z geeft een
complexe C). Daarom:
1. `AFFE_MODELE`: de volumes `3D` en de impedantievlakken `3D_ABSO`.
2. `ASSEMBLAGE` van `RIGI_ACOU` en `MASS_ACOU` zonder lasten.
3. Per impedantierand `CALC_MATR_ELEM(OPTION='AMOR_ACOU')` met een eigen
   `CHAM_MATER`: `CELE_R = 1` op die rand (de `3D_ABSO`-matrix is (1/c)·∫NNᵀdA, gemeten),
   dus A = ∫NNᵀdA; `ASSE_MATRICE` met dezelfde nummering.
4. In de job (Python 3 met numpy en scipy uit de Code-Aster-installatie): C = Σ(ρ/Z)·A,
   de drukknopen (*fluid pressure* 0) eruit, linearisering (2n vrijheidsgraden),
   shift-invert met ARPACK (`scipy.sparse.linalg.eigs`, factorisatie `splu`); kleine
   modellen dicht (`scipy.linalg.eig`). Per mode het residu
   ‖Q(λ)P‖/((‖K‖ + |λ|‖C‖ + |λ|²‖M‖)·‖P‖); boven *Controle modes* een WARNING.
5. De job schrijft de modes direct in Mecway's formaat. Er is geen Code-Aster-resultaat:
   `med_export` en `#ASTER-POST` op `res` werken hier niet.
Rekentijd (gemeten): een ruimte van 13 000 knopen (hex20) met 20 modes 14 s.

### 3.4 Wat niet kan

- Een **frequentieafhankelijke** impedantie (ook Mecway niet, §9.35) en een complexe
  impedantie in de **harmonische** analyse (§5.6).
- Acoustic Resonance 2D (A20), Mecway's *acoustic displacement* als resultaatveld,
  media met verschillende dichtheid (§3.2), contact en koppelingen in de akoestiek,
  piramide-elementen.
- Koppeling met een constructie: de gekoppelde modes staan in §6 (vibro-akoestiek).
  Het drukveld bij een excitatiefrequentie (harmonisch) staat in §5.

## 4. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Akoestiek: materiaal ... heeft geen geluidssnelheid | *Speed of sound* ontbreekt | vul bij het materiaal (*Isotropic*) *Speed of sound* in |
| ERROR: Akoestiek: alleen volume-elementen (hex, wedge, tet; geen piramides, schalen of balken) | het model bevat piramides, schalen, balken of een elset zonder materiaal | mesh alleen het fluïdum met hex/wedge/tet; geef elke elset een materiaal |
| ERROR: Akoestiek: de media hebben een verschillende dichtheid | twee materialen met een andere dichtheid (§3.2) | gelijke dichtheid (of geen) als het verschil klein is, of de media apart rekenen |
| WARNING: Akoestiek: medium '...' heeft geen dichtheid, medium '...' wel (...) | één medium met en een zonder *Density*; het grensvlak rekent dan als gelijke dichtheid (§3.2) | vul bij elk medium de dichtheid in; is die gelijk, dan is het resultaat juist |
| ERROR: Akoestiek: fluid pressure op '...' is ...; alleen 0 kan | *Fluid pressure* ≠ 0 bij de holtemodes | zet de waarde op 0 (drukknoop), of reken harmonisch (§5: dan is het een opgelegde druk) |
| ERROR: Akoestiek: fluid pressure op '...': kies een knoop- of vlakselectie | *Fluid pressure* op een elementselectie | kies knopen of vlakken |
| ERROR: Akoestiek: impedantie op '...': materiaal '...' heeft geen dichtheid | impedantie zonder dichtheid (C = ρ/Z, §3.3) | vul bij het materiaal een dichtheid in (lucht 1.2 kg/m³) |
| ERROR: Akoestiek: impedantie op '...' is 0 | *specific impedance* R = X = 0 | een open einde is *fluid pressure* = 0 (drukknoop) |
| ERROR: Akoestiek: impedantie op '...': kies een vlakselectie | impedantie op knopen of elementen | maak een *Face selection* |
| ERROR: Akoestiek: impedantie op '...': Re Z en Im Z moeten getallen zijn | tekst of een eenheid in het veld | alleen het getal (Pa·s/m), zonder eenheid |
| ERROR: Akoestiek: impedantie '...' ligt aan 2 media | de selectie grenst aan twee materialen | per medium een eigen selectie |
| WARNING: Akoestiek: impedantie op '...' heeft Re Z < 0 | negatieve weerstand: de rand voert energie toe | controleer het teken; Re Z ≥ 0 voor een gewone absorbeerder |
| WARNING: Complexe modes: residu ... > ... (Controle modes) | een mode is onnauwkeurig opgelost (bijv. bijna-meervoudig of zeer sterk gedempt) | mesh verfijnen, minder modes vragen, of *Controle modes* ruimer |
| WARNING: Akoestiek: geen MED-export bij complexe modes | `med_export` aan | normaal: de modes staan in Mecway |
| WARNING: Akoestiek: #ASTER-EXCIT ... wordt bij complexe modes niet gebruikt | eigen lasten bij een model met impedantie | normaal; drukknopen via *fluid pressure* = 0 |
| `aster_acoustic_complex: FOUT: ...` in de `.mess`, geen resultaten | bijv. ARPACK convergeert niet, of Q(σ) is singulier | andere zoekfrequentie of minder modes; blijft het: melden (KNOWN_BUGS) |
| ERROR: Acoustic Resonance 2D (A20) wordt niet vertaald | 2D-model | maak een 3D-model (A30) |
| ERROR: 'contact2' / 'nodesurfacecoupling' / 'constraintequation' op ... wordt in een akoestische analyse niet vertaald | koppeling in de akoestiek | gebruik één doorlopend mesh |
| INFO: Load '...' on '...' does not count in an acoustic analysis | mechanische of thermische belasting in het model | normaal |
| INFO: Mode 1 is at ~0 Hz: constant pressure | harde wanden zonder drukknoop | normaal (§3.1) |
| alarm `ALGELINE3_82` (la borne minimale ... est une valeur propre) | de ondergrens van de Sturm-controle valt op de 0-Hz-mode (harde wanden) | onschuldig; de frequenties zijn goed (AK-01, AK-05) |
| `<EXCEPTION> <ALGELINE3_81>` | singuliere stijfheid: een los deel van het volume zonder drukknoop terwijl er elders wel drukknopen zijn, of alleen `#ASTER-EXCIT`-lasten | kies een kleine negatieve zoekfrequentie (bijv. −10 Hz); de 0-Hz-mode komt dan mee |
| alarm `ALGELINE5_15` / `ALGELINE5_23` | een mode haalt de nauwkeurigheid niet / meervoudige mode op de grens (bijv. een vierkante doorsnede) | als bij modaal ([`Modaal_en_knik.md`](Modaal_en_knik.md) §4) |

Meer meldingen: [`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md).

## 5. Harmonisch drukveld (`acoustic_harm_3d`)

Mecway heeft geen harmonische analyse (Mecway Ltd., 2026, hoofdstuk 6). De bridge
rekent daarom het **A30-model** (zelfde mesh, materiaal, *fluid pressure* en
*impedance*) als **harmonische respons**: het drukveld bij elke frequentie van een
lijst, aangestoten door een bron (een trillend vlak of een opgelegde druk), met harde
wanden, drukknopen en absorberende randen. Voorbeelden: een luidspreker in een kast,
een uitlaat of kanaal, een ruimte met een absorberend plafond.

| Wat | Hoe in Mecway | Code-Aster |
|---|---|---|
| analyse | *Acoustic Resonance 3D* (A30); in de bridge `acoustic_harm_3d` (pagina *Akoestiek (harmonisch)*); `auto` kiest hem zelf als het model een bron heeft | `PHENOMENE='ACOUSTIQUE'`, `DYNA_VIBRA` `TYPE_CALCUL='HARM'` |
| bron: trillend vlak | vlakselectie **`BRON_...`** (of `SOURCE_...`): normaalsnelheid = instelling *Snelheid BRON_-vlakken*; of **`#ASTER-BRON selectie = snelheid [, fase]`** | `AFFE_CHAR_ACOU` `VITE_FACE` |
| bron: opgelegde druk | *Fluid pressure* met een waarde ≠ 0 (knopen of vlakken) | `AFFE_CHAR_ACOU` `PRES_IMPO` |
| drukknoop | *Fluid pressure* = 0 | `PRES_IMPO` 0 |
| absorberende rand (ρc) | vlakselectie **`ABSORBEREND_...`** (of `ABSORBING_...`) | `MODELISATION='3D_ABSO'` |
| impedantie Z (reëel) | Mecway *Impedance* (*specific impedance*, Im = 0) | `3D_ABSO` met c = Z/ρ |
| harde wand | vlak zonder voorwaarde | (niets: ∂p/∂n = 0) |
| microfoon | knoopselectie **`MICROFOON_...`** (of `MICROPHONE_...`) | frequentierespons in de log en een CSV |

De voorvoegsels gelden voor de naam van de selectie in Mecway; hoofdletters maken niet
uit (`Bron_luidspreker` werkt ook).

### 5.1 Werkwijze in Mecway stap voor stap

1. **Model zoals voor de holtemodes** (§1.1): mesh alleen het fluïdum (hex, wedge,
   tet), analysetype *Acoustic Resonance 3D*, materiaal *Isotropic* met *Speed of
   sound* **en een dichtheid** (bijv. 1.2 kg/m³ voor lucht, 1000 kg/m³ voor water):
   een snelheidsbron geeft p = ρ·c·v, dus zonder dichtheid stopt de bridge (§5.7).
2. **Bron.** Selecteer de vlakken van de bron (bijv. de conus van een luidspreker, een
   inlaat) als *Face selection* en noem die `BRON_Luidspreker`. De normaalsnelheid is
   dan de instelling *Snelheid BRON_-vlakken* (standaard 1 mm/s), gericht **de fluid
   in** (een zuiger die duwt), fase 0. Een andere snelheid of fase per bron: zet in
   Mecway in een vrij tekstveld (bijv. *CCX > Custom model definition*) de regel
   `** ASTER-BRON Luidspreker = 2 mm/s, 90` (snelheid in m/s of mm/s, fase in graden;
   de selectie heeft dan geen voorvoegsel nodig). Twee luidsprekers in tegenfase:
   twee regels met fase 0 en 180. Een **opgelegde druk** als bron: *Fluid pressure*
   met een waarde (bijv. 2 Pa) op knopen of vlakken; Mecway zelf weigert dat bij de
   holtemodes, de bridge gebruikt het alleen hier.
3. **Absorberende randen.** Een open einde naar een grote ruimte, een anechoïsche
   afsluiting of een "oneindig lange" buis: vlakselectie `ABSORBEREND_Uitlaat`. De
   bridge legt daar de karakteristieke impedantie ρc van het aangrenzende medium op:
   een vlakke golf die er loodrecht op valt, wordt niet teruggekaatst. Een absorbeerder
   met een andere (reële) impedantie: Mecway's *Impedance* met *specific impedance* Z
   in Pa·s/m (Z = ρc = 408 voor lucht; Z > ρc is harder, Z < ρc zachter); het
   imaginaire deel moet 0 zijn (§5.6).
4. **Microfoons.** Knoopselectie `MICROFOON_Oor` met één knoop (of meer, zie §5.4).
5. **Mesh-fijnheid.** Kies de elementgrootte op de hoogste frequentie: λ = c/f_max,
   minstens **10 lineaire** of **5 kwadratische** elementen per golflengte (§5.4); de
   bridge waarschuwt als het mesh grover is.

### 5.2 In het hoofdvenster van de bridge

1. **Actieve analyse:** `auto` kiest bij A30 met een bron (`BRON_`-selectie,
   `#ASTER-BRON` of *fluid pressure* ≠ 0) `acoustic_harm_3d`, zonder bron
   `acoustic_modes_3d`. Wil je van een model met een bron toch de holtemodes: kies
   `acoustic_modes_3d` zelf (de bron- en absorberende selecties zijn dan harde wanden,
   INFO in de log).
2. **Resultaten naar Mecway** moet `liml` zijn.
3. Pagina **Akoestiek (harmonisch)**:

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Startfrequentie / Eindfrequentie [Hz] | 50 / 1000 | het bereik van de vraag (bijv. 20–2000 Hz voor het gehoor, of rond een bromtoon). De eindfrequentie bepaalt de mesh-fijnheid (§5.4) |
| Aantal frequenties | 20 | meer om resonantiepieken te vinden: de stap moet kleiner zijn dan de breedte van een piek (§5.4); de rekentijd groeit lineair met het aantal |
| Verdeling (lin / log) | lin | `log` over een breed bereik (gelijke verhoudingen, zoals octaafbanden) |
| Frequentielijst [Hz] (0 = bereik hierboven) | 0 | eigen frequenties, bijv. `100, 250, 500` (punt als decimaalteken); vervangt het bereik |
| Snelheid BRON_-vlakken [m/s] | 0.001 | de werkelijke amplitude van de bron; alles schaalt lineair (p ∝ v), dus voor een overdrachtsfunctie p/v is elke waarde goed |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | grote modellen of veel frequenties |

Per model met `#ASTER-OPTIE` (zie [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md)),
bijv. `** ASTER-OPTIE harm_freq_list = 125, 250, 500, 1000` of
`** ASTER-OPTIE harm_freq_count = 200`.

### 5.3 Resultaten in Mecway

Onder *Solution* staat per frequentie een regel (*Mode 1 ... Mode n* met de frequentie
in Hz; het zijn **geen** eigenmodes maar de respons bij die frequentie). Velden per
frequentie (knoopwaarden):

| Veld | Betekenis | Eenheid |
|---|---|---|
| `pressure` | reëel deel van de complexe druk P (de druk op t = 0) | Pa |
| `pressurei` | imaginair deel van P | Pa |
| `pressuremag` | amplitude \|P\| (piekwaarde van de sinus) | Pa |
| `pressurephase` | fase van P ten opzichte van de bron, −180…180 | graden |
| `spl` | geluidsdrukniveau 20·log10(\|P\| / (√2 · 20 µPa)) | dB |

De druk in de tijd is p(t) = Re(P·e^{iωt}) (dezelfde afspraak als Mecway's complexe
modes, Mecway Ltd., 2026, §6.9.2). Mecway's eigen API leest de frequenties en alle vijf
velden per frequentie (headless nagelopen met een Mecway-script); de weergave in de
Mecway-GUI is nog niet bekeken (KNOWN_BUGS 57).

In de **log** en het statusvak staan het aantal frequenties en per microfoon het
hoogste niveau; per microfoon en frequentie |p|, fase en SPL staan in de log en in
`<model>_<run-id>_microfoons.csv` in de werkmap (kolommen `microfoon,
frequentie_Hz, p_re_Pa, p_im_Pa, p_amp_Pa, fase_graden, spl_dB, knopen`; komma's en een
punt als decimaalteken; met taal Engels Engelse kolomnamen). Een spreadsheet maakt
daar direct een frequentierespons (SPL tegen f) van.

### 5.4 Interpretatie en controles

- **Vlakke golf (handberekening):** in een buis met een bron v aan het begin en een
  absorberend einde is |p| = ρ·c·v overal en daalt de fase met k·x (k = 2πf/c). Met een
  harde wand aan het einde (lengte L): |p(x)| = ρ c v |cos(k(L−x)) / sin(kL)|, oneindig
  bij de resonanties f_n = n·c/(2L). Een reële impedantie Z aan het einde kaatst
  R = (Z − ρc)/(Z + ρc) terug; de staande golf heeft max/min = (1+|R|)/(1−|R|).
- **SPL:** gebaseerd op de effectieve waarde |P|/√2 (zoals een geluidsmeter). 1 Pa
  amplitude = 91,0 dB. Code-Aster's eigen `PRAC_ELNO` DB (testcase ahlv100a) rekent met
  |P| zelf en ligt 3,01 dB hoger. Een drukknoop (p = 0) krijgt −200 dB.
- **Fase:** ten opzichte van de bron (fase 0 = in fase met de snelheid de fluid in).
  Bij een vlakke golf de fluid in staat de druk in fase met de snelheid.
- **Resonanties:** zonder absorberende rand is er geen demping en is de respons bij een
  holtemode oneindig (de bridge waarschuwt; Code-Aster geeft daar een bijna-singuliere
  matrix). Reken eerst de holtemodes (`acoustic_modes_3d`) en kies de frequenties
  ertussen, of neem een absorberende rand op. Met absorptie zijn de pieken eindig; hun
  breedte hangt af van de absorptie: kies de frequentiestap minstens 3–5 keer kleiner
  dan de verwachte piekbreedte, of reken een tweede keer met een fijnere lijst rond de
  piek.
- **Elementen per golflengte** (gemeten, [`Verificatie.md`](Verificatie.md) §7, AH):
  - hex20: 10 per golflengte gaf |p| op 0,02% en de faseval over 2 golflengten op
    0,01% (AH-01); 5 per golflengte nog ≤ 0,3% (AH-01b);
  - hex8: de fase ijlt na met ≈ (kh)²/24 per golflengte: 10 per golflengte gaf −1,6%
    fase en +1,7% |p| (AH-02a), 20 per golflengte −0,4% (AH-02b). Voor 1% fase zijn
    ~13 lineaire elementen per golflengte nodig.
  De bridge waarschuwt onder 10 (lineair) / 5 (kwadratisch) per golflengte bij de
  hoogste frequentie, gemeten met de **grootste** elementrand (ook dwars). De fout
  stapelt zich op met de afstand: in een lange buis of grote ruimte fijner meshen.
- **Absorberende rand (ρc):** exact voor een vlakke golf die er loodrecht op valt. Een
  schuin invallende golf of een bolgolf dicht bij de bron kaatst deels terug; leg de
  rand daarom een eind van de bron (vuistregel: ≥ een halve golflengte bij de laagste
  frequentie). Dwarsmodes in een buis (boven f ≈ c/(2·breedte)) worden ook deels
  teruggekaatst.

### 5.5 Hoe de bridge vertaalt

`bridge_acoustic.build_acoustic_harm` maakt de `.comm` (template
`AsterTemplate_AkoestiekHarm.comm`); route van testcase ahlv100a:

1. `AFFE_MODELE` `PHENOMENE='ACOUSTIQUE'`: volumes en bronvlakken `MODELISATION='3D'`
   (de bronvlakken moeten in het model en een materiaal hebben), absorberende vlakken
   `'3D_ABSO'`.
2. `DEFI_MATERIAU(FLUIDE=_F(RHO, CELE_R))` per medium; per impedantie een eigen
   materiaal met `CELE_R = Z/ρ` op dat vlak. Gemeten: de `3D_ABSO`-dempingsmatrix is
   (1/c)∫NNᵀdA met de c van het vlak en zonder ρ (een andere RHO op het vlak veranderde
   niets; `CELE_R` 680 i.p.v. 340 gaf reflectie 1/3, zoals Z = 2ρc), en Mecway's
   impedantieterm is (ρ/Z)∫NNᵀdA (Mecway Ltd., 2026, §6.9.2).
3. Bron: `AFFE_CHAR_ACOU(VITE_FACE=_F(GROUP_MA, VNOR=v))`, opgelegde druk en
   drukknopen: `PRES_IMPO`.
4. `ASSEMBLAGE`: `RIGI_ACOU`, `MASS_ACOU`, `AMOR_ACOU` (alleen met absorberende randen)
   en de lastvectoren `CHAR_ACOU` (snelheid en opgelegde druk apart).
5. `DYNA_VIBRA(TYPE_CALCUL='HARM', BASE_CALCUL='PHYS', LIST_FREQ=...)` met de
   snelheidsbron als `EXCIT` `PUIS_PULS=1, PHAS_DEG=90` (= iω·v) en de opgelegde druk
   zonder factor. Gemeten: `COEF_MULT=+1` geeft p = +ρcv op de bron bij een absorberend
   einde, dus v de fluid in; ahlv100a gebruikt −1 (v naar buiten).
6. `aster_acoustic_export.py` (in de job) schrijft per frequentie een `<mode>` met de
   vijf velden en de microfoonrespons (CSV, regels `BRIDGE_MIC` in de `.mess`).

Met `med_export` aan schrijft de bridge het reële en imaginaire deel als
`PRES_REEL`/`PRES_IMAG` in de `.rmed`. Eigen nabewerking op het resultaat `res`
(type `ACOU_HARMO`, veld `PRES` complex) kan met `#ASTER-POST`, bijv.
`CALC_CHAMP(... ACOUSTIQUE=('INTE_ELNO',))` voor de intensiteit (ahlv100a).

### 5.6 Wat niet kan

- **Complexe impedantie** (Im Z ≠ 0) en frequentie-afhankelijke impedantie: Code-Aster's
  `3D_ABSO` met een complexe `CELE_I` gaf niet de reflectie van een complexe Z, en
  `DYNA_VIBRA` kent geen frequentie-afhankelijke term (KNOWN_BUGS 57): ERROR.
- **Volumedemping** (luchtdemping, poreuze materialen) en complexe geluidssnelheid:
  niet vertaald.
- **Koppeling met een constructie** (trillend paneel): niet in deze analyse; daarvoor
  §6 (gekoppelde modes) en §7 (harmonische respons van constructie + fluïdum).
- Een bron op een knoop of in het volume (puntbron, monopool): niet; gebruik een
  klein bronvlak of een opgelegde druk.
- Microfoons op vlak- of elementselecties (alleen knoopselecties tellen; WARNING).
- Vergelijking met een Mecway-solve (*Eerst Mecway-solve ter controle*): Mecway heeft
  geen harmonische analyse (INFO).
- Verder alles wat bij de holtemodes niet kan (§3.4): 2D, media met verschillende
  dichtheid, contact en koppelingen, piramides.

### 5.7 Meldingen en oplossingen (harmonisch)

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Akoestiek harmonisch: geen bron | geen `BRON_`-vlakselectie, `#ASTER-BRON` of *fluid pressure* ≠ 0 | geef de bronvlakken een naam `BRON_...` |
| ERROR: Akoestiek harmonisch: materiaal ... heeft geen dichtheid | snelheidsbron zonder dichtheid (p = ρcv) | vul bij het materiaal een dichtheid in |
| ERROR: ... bron '...' is een knoopselectie; een bron moet een vlakselectie zijn | `BRON_` op knopen of elementen | maak een *Face selection* |
| ERROR: ... '#ASTER-BRON ...': verwacht 'selectie = snelheid ...' | schrijffout in de regel | bijv. `** ASTER-BRON Luidspreker = 2 mm/s, 90` (punt als decimaalteken) |
| ERROR: ... #ASTER-BRON: '...' is geen vlakselectie | de naam bestaat niet als vlakselectie | naam precies als in Mecway |
| ERROR: ... '...' ligt aan 2 media; maak per medium een eigen selectie | bron- of absorberende selectie grenst aan twee materialen | splits de selectie |
| ERROR: ... selectie '...' is zowel bron als absorberend | dezelfde selectie met twee rollen | aparte selecties |
| ERROR: ... impedantie op '...' is complex (Im Z = ...) | *specific impedance (imaginary)* ≠ 0 | alleen een reële Z (§5.6) |
| ERROR: ... impedantie op '...': materiaal '...' heeft geen dichtheid | Z/ρ zonder ρ | dichtheid invullen |
| ERROR: ... frequentielijst (harm_freq_list) '...' is ongeldig | geen getallen, of ≤ 0 | bijv. `100, 250, 500`, of `0` voor het bereik |
| ERROR: ... frequentiebereik ... is ongeldig | start ≤ 0, eind < start of aantal < 1 | instellingen op de pagina |
| WARNING: ... geen absorberende rand ...: de respons bij een holtemode is oneindig | alleen harde wanden en drukknopen | absorberende rand toevoegen of frequenties tussen de resonanties |
| WARNING: ... minder dan 10 (lineair) / 5 (kwadratisch) elementen per golflengte | mesh te grof voor de hoogste frequentie | mesh verfijnen of de eindfrequentie verlagen (§5.4) |
| WARNING: ... microfoon '...' is een vlakselectie | microfoon geen knoopselectie | maak een *Node selection* |
| ERROR: Akoestiek: fluid pressure op '...' is ...; alleen 0 kan (drukknoop; als bron: ...) | holtemodes (`acoustic_modes_3d`) met *fluid pressure* ≠ 0 | zet hem op 0, of reken harmonisch (`auto` doet dat vanzelf) |

## 6. Vibro-akoestiek: gekoppelde modes (`vibroacoustic_modes_3d`)

Een constructie en een lucht- of vloeistofvolume in één model: de bridge rekent de
**gekoppelde eigenmodes**, waarin de constructie het fluïdum laat meetrillen en het
fluïdum terugduwt. Voorbeelden: een paneel op een luchtholte (de "pompmode" wordt
stijver door de luchtveer), een zuiger of membraan in een vloeistofkolom, een tank of
leiding met water (het water geeft **toegevoegde massa**: de constructie trilt lager),
een luidsprekerkast. Mecway heeft geen gekoppelde analyse (Mecway Ltd., 2026,
hoofdstuk 6) en rekent akoestiek met één materiaal; de bridge gebruikt daarom een
gewoon *Frequency*-model (V30) waarin het fluïdum een eigen onderdeel is.

| Wat | Hoe in Mecway | Code-Aster |
|---|---|---|
| analyse | *Frequency 3D* (V30) met *Number of modes*; `auto` kiest `vibroacoustic_modes_3d` zodra het model een fluïdum heeft | `PHENOMENE='MECANIQUE'`, `CALC_MODES` `OPTION='BANDE'` |
| fluïdum | een onderdeel (component) met een materiaal *Isotropic* met **Speed of sound** en **Density**, zonder Young's modulus; of een onderdeel met een naam die begint met **`LUCHT_`**, **`VLOEISTOF_`** of **`FLUID_`** | `MODELISATION='3D_FLUIDE'`, `FORMULATION='U_P_PHI'`, `DEFI_MATERIAU(FLUIDE=_F(RHO, CELE_R))` |
| constructie | de andere onderdelen, zoals in een modale analyse (volumes, schalen, balken, veren, opleggingen) | de gewone mechanische elementen |
| koppelvlak | **automatisch**: elk vlak van een fluïdum-element dat samenvalt met een vlak van een constructie-volume-element of met een schaalelement (gedeelde knopen); handmatig: vlakselecties **`KOPPEL_...`** (of `COUPLING_...`) | `MODELISATION='FLUI_STRU'` (randelementen, normaal uit het fluïdum) |
| p = 0 (vrij oppervlak, open einde) | knoop- of vlakselectie **`OPEN_...`** (of Mecway's *fluid pressure* = 0, als die in het model staat) | `DDL_IMPO` `PRES=0`, `PHI=0` |
| harde wand | vlak van het fluïdum zonder voorwaarde en zonder constructie | (niets: ∂p/∂n = 0) |

De voorvoegsels gelden voor de naam in Mecway; hoofdletters maken niet uit.

### 6.1 Werkwijze in Mecway stap voor stap

1. **Mesh de constructie én het fluïdum als één doorlopend mesh**: op het grensvlak
   delen ze de knopen (zoals twee onderdelen die in Mecway samengevoegd zijn). Het
   fluïdum: hex, wedge, tet of piramide (lineair of kwadratisch); de constructie: alles
   wat de modale analyse kent. Een schaal mag op een fluïdumvlak liggen (de schaal
   deelt zijn knopen met het fluïdum), maar niet met fluïdum aan **beide** kanten: dan
   zouden de twee kanten dezelfde druk hebben (ERROR; maak het paneel dan van een laag
   volume-elementen).
2. **Analysetype** *Frequency 3D* met *Number of modes*.
3. **Materiaal van het fluïdum**: *Isotropic* met alleen *Speed of sound* (bijv.
   340 m/s voor lucht, 1480 m/s voor water) en een *Density* (1,2 kg/m³ lucht, 1000
   kg/m³ water). Laat *Young's modulus* leeg: daaraan herkent de bridge het fluïdum.
   De dichtheid is nodig: de koppeling en de toegevoegde massa hangen ervan af.
   Twee fluïda (bijv. water en lucht) moeten elkaar **niet raken** als ze een andere
   dichtheid hebben (ERROR, §6.6); met gelijke dichtheid en een andere
   geluidssnelheid mag het wel.
4. **Constructie** zoals bij een modale analyse: materiaal met E, ν en dichtheid,
   doorsnede/dikte, opleggingen (*fixed*, *displacement*, ...). Belastingen tellen
   niet mee (WARNING; er is geen voorspanning in de vibro-akoestiek).
5. **Randen van het fluïdum**:
   - een vlak tegen de constructie: koppelvlak (automatisch);
   - een vlak zonder iets: harde wand (bijv. een stijve tankwand die je niet meesht);
   - een vrij wateroppervlak of een open einde naar een grote ruimte: p = 0 met een
     knoop- of vlakselectie `OPEN_Oppervlak`. (Lucht boven water mesh je niet mee:
     andere dichtheid, en voor de waterbeweging is p = 0 de gangbare benadering;
     klotsen door de zwaartekracht neemt de bridge niet mee.)
6. **Mesh-fijnheid**: zoals bij de holtemodes (§1.5): kies het fluïdummesh op de
   hoogste frequentie die je zoekt; ≥ 10 lineaire of ≥ 5 kwadratische elementen per
   golflengte c/f. De constructie zoals bij een modale analyse (schaal: genoeg
   elementen per halve golf).

### 6.2 In het hoofdvenster van de bridge

1. **Actieve analyse:** `auto` kiest bij een Frequency-model met een fluïdum
   `vibroacoustic_modes_3d` (INFO in de log); of kies hem zelf. Kies je bij zo'n model
   `modal_3d`, dan rekent de bridge het fluïdum als vaste stof (WARNING).
2. **Resultaten naar Mecway** moet `liml` zijn.
3. **Eerst Mecway-solve ter controle**: heeft geen zin (Mecway rekent een materiaal
   zonder Young's modulus als vaste stof met E = 0; de bridge vergelijkt dan niet).
4. Pagina **Vibro-akoestiek (modes)**:

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Aantal modes (zonder maxmode in Mecway) | 10 | alleen als het Mecway-model geen *Number of modes* heeft |
| Ondergrens frequentie [Hz] (`vibro_freq_min`) | 0,1 | de modes **boven** deze frequentie. Hoger: de modes vanaf een frequentie (bijv. rond een bromtoon of toerental). Lager dan 0,1 Hz alleen bij een heel slappe constructie (verwachte modes onder 0,1 Hz); > 0 blijft nodig (§6.5) |
| Controle modes (VERI_MODE SEUIL) | 1e-6 | groter (bijv. 1e-5) als de log `ALGELINE5_15` meldt (de fout van een mode net boven 1e-6, gezien met hex8-lucht) |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | grote modellen |

Per model met `#ASTER-OPTIE`, bijv. `** ASTER-OPTIE vibro_freq_min = 100`
([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md), voorbeeld 14).

### 6.3 Resultaten in Mecway

Onder *Solution* staan *Mode 1 … Mode n* met de frequentie, zoals bij een modale
analyse. Per mode:

| Veld | Waar | Betekenis |
|---|---|---|
| `displ` (`displx`, `disply`, `displz`; schalen en balken ook `rot*`) | knopen van de constructie (ook die op het koppelvlak) | trillingsvorm van de constructie |
| `pressure` | knopen van het fluïdum (ook die op het koppelvlak) | akoestische druk van dezelfde mode |

De schaal is willekeurig (zoals elke trillingsvorm), maar **verplaatsing en druk horen
bij elkaar**: de verhouding p/u is fysisch (verificatie VA-01: op de zuiger op 2e-6
gelijk aan de analytische ρω²·cot(kL)/k). De bridge normeert op gegeneraliseerde massa
1 (`NORM_MODE MASS_GENE` van de gekoppelde massamatrix). Fluïdumknopen hebben geen
verplaatsing, constructieknopen buiten het koppelvlak geen druk. Mecway's API leest
de frequenties en beide velden per mode (headless nagelopen met een Mecway-script op
VA-01); de weergave in de Mecway-GUI is nog niet bekeken (KNOWN_BUGS 59). In de log
en het statusvak: de frequenties en de band waarin gezocht is.

### 6.4 Interpretatie en controles

- **Gekoppelde mode**: constructie en fluïdum trillen samen met één frequentie. Een
  zware vloeistof op een lichte constructie verandert de frequenties sterk; lucht op
  een stalen plaat weinig, behalve als de lucht ingesloten is en de plaat er als een
  zuiger op werkt.
- **Toegevoegde massa** (vloeistof die mee moet bewegen) verlaagt de frequentie; de
  **luchtveer** van een ingesloten volume verhoogt die van een mode die het volume
  samendrukt. Gemeten (VA-05b, stalen plaat 0,5 × 0,4 m, 2 mm, op een gesloten
  luchtholte 0,5 × 0,4 × 0,3 m): de pompmode (1,1) gaat van 50,52 naar 54,96 Hz
  (+8,8%; een handberekening met één mode en de luchtveer ρc²(∫φ dA)²/V geeft 55,23
  Hz); de andere plaatmodes dalen 0,2–0,5% (toegevoegde massa); de eerste holtemode
  daalt 0,7% (de plaat geeft mee).
- **Handberekening voor een kolom** (zuiger met massa m per oppervlak tussen een
  waterkolom L1 met vrij oppervlak en een gesloten luchtkolom L2):
  m + ρ1·tan(k1L1)/k1 − ρ2·cot(k2L2)/k2 = 0; voor lage frequentie
  f ≈ 1/(2π)·√(ρ2c2²/(L2(m + ρ1L1))) (massa plus de meebewegende waterkolom op de
  luchtveer). Testcase adlv100a: 13,83 Hz (VA-01).
- **Controle van de koppeling**: zet de dichtheid van het fluïdum tijdelijk 1000×
  kleiner; dan moeten de modes de losse constructiemodes (*Modaal*) en de holtemodes
  (*Akoestiek (holtemodes)*, harde wanden) zijn (VA-05: ≤ 0,6%, de afwijking is de
  schaaldiscretisatie).
- **Geen modes bij 0 Hz**: een starre beweging of een constante druk in een gesloten
  volume valt onder de ondergrens en wordt niet gegeven.

### 6.5 Hoe de bridge vertaalt

`bridge_vibroacoustic.py` maakt de `.comm` (template `AsterTemplate_VibroAkoestiek.comm`);
syntax van de testcases adlv100a (zuiger + vloeistofkolom), adlv100p en adlv312a:

1. `bridge_mesh` schrijft de koppelvlakken als randelementen (groepen `BRFSI1`,
   `BRFSI2`, … per fluïdum-onderdeel); `MODI_MAILLAGE ORIE_PEAU` met
   `GROUP_MA_INTERNE` = het fluïdum richt hun normaal uit het fluïdum (adlv100b,
   adls102a).
2. `AFFE_MODELE`: de constructie zoals modaal, het fluïdum `3D_FLUIDE` en de
   koppelvlakken `FLUI_STRU`, beide `FORMULATION='U_P_PHI'` (de Code-Aster-standaard;
   onbekenden verplaatsing, druk p en verplaatsingspotentiaal φ; symmetrische
   matrices). Gemeten: `U_P` (niet-symmetrisch) gaf met `PLUS_PETITE` een verkeerde
   reeks en met `CENTRE` een `<F> JEVEUX_26`; `U_PSI` kent geen `DDL_IMPO PRES`.
3. `DEFI_MATERIAU(FLUIDE=_F(RHO, CELE_R))` op het fluïdum en zijn koppelvlakken. De
   dichtheid zit in de matrices (gemeten: staaf + waterkolom met ρ 1000 en 1 gaven elk
   hun eigen analytische frequenties), anders dan bij de holtemodes (§3.2).
4. Opleggingen van de constructie zoals modaal; p = 0 als `DDL_IMPO PRES=0, PHI=0`.
   `ASSEMBLAGE` `RIGI_MECA` en `MASS_MECA`.
5. **Modes zoeken.** In `U_P_PHI` heeft de stijfheid geen term voor φ: elke
   vrijheidsgraad φ geeft een valse mode bij 0 Hz (gemeten: 40 op het kleine mesh van
   adlv100a, met negatieve gegeneraliseerde massa). `PLUS_PETITE` stopt dan met
   `ALGELINE3_81` en `CENTRE` geeft eerst die valse modes. Daarom zoekt de bridge met
   `INFO_MODE` (Sturm-telling) een band [`vibro_freq_min`, f_max] met minstens het
   gevraagde aantal modes (×4 per stap, daarna twee halveringen), rekent
   `CALC_MODES OPTION='BANDE'` en houdt de eerste modes met f ≥ `vibro_freq_min` en
   positieve gegeneraliseerde massa (`EXTR_MODE`), genormeerd met `NORM_MODE`
   `MASS_GENE`. De Sturm-telling klopt (staaf + waterkolom: 6 van 6 analytische modes).
6. `aster_results_export` schrijft per mode `displ` (DX…) en `pressure` (component
   `PRES` van `DEPL`).

### 6.6 Wat niet kan

- **Harmonische respons** van constructie + fluïdum (kracht of bron per frequentie,
  absorberende randen): niet in de modes, maar in de analyse `vibroacoustic_harm_3d`
  op hetzelfde model (§7). Voor het drukveld zonder constructie: §5.
- **Twee fluïda die elkaar raken met een andere dichtheid** (bijv. lucht boven water):
  op gedeelde knopen is φ continu, wat met p = ρω²φ alleen bij gelijke dichtheid klopt
  (gemeten: buis met ρ 1,2/12 gaf 188,23 Hz, analytisch 306,47 Hz): ERROR. Gescheiden
  door een constructie (zoals in adlv100a) kan wel.
- Een schaal met fluïdum aan beide kanten (gedeelde knopen): ERROR (stap 1 van §6.1).
- Een niet-doorlopend mesh (fluïdum en constructie met eigen knopen op het
  grensvlak): geen koppelvlak (WARNING). *Bonded contact* tussen fluïdum en
  constructie: NIET geverifieerd (geen koppelvlak; gebruik gedeelde knopen).
- Impedantie, *fluid pressure* ≠ 0, bron-, absorberende en microfoonselecties: tellen
  niet mee in de modes (impedantie en *fluid pressure* ≠ 0: ERROR; de selecties: INFO).
- Voorspanning door belastingen, demping en complexe modes, zwaartekracht op het vrije
  oppervlak (klotsen, `2D_FLUI_PESA`), effectieve massa per mode (Code-Aster's waarde
  heeft voor deze modes geen betekenis), vergelijking met een Mecway-solve.
- `elem_hex8` = `LINE_QUAD` met een fluïdum: NIET geverifieerd.

### 6.7 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Vibro-akoestiek: het model heeft geen fluïdum | geen onderdeel met een materiaal met *Speed of sound* zonder Young's modulus, en geen `LUCHT_`/`FLUID_`-naam | geef het lucht-/vloeistofvolume een eigen onderdeel en materiaal |
| ERROR: … onderdeel '…' heet een fluïdum, maar materiaal '…' heeft geen geluidssnelheid | naam met `LUCHT_`/`FLUID_`, materiaal zonder *Speed of sound* | vul *Speed of sound* in, of hernoem het onderdeel |
| ERROR: … fluïdum-materiaal '…' heeft geen dichtheid | *Density* ontbreekt | vul de dichtheid in (1,2 lucht, 1000 water) |
| ERROR: … fluïdum '…' bevat quad4 … alleen volume-elementen | schalen of balken in een fluïdum-onderdeel | mesh het fluïdum met volume-elementen; schalen in een eigen onderdeel met een constructiemateriaal |
| ERROR: … fluïda '…' en '…' raken elkaar met een andere dichtheid | twee fluïda met gedeelde knopen (§6.6) | laat één fluïdum weg (lucht boven water: p = 0 met `OPEN_`), of gelijke dichtheid |
| ERROR: … schaalelement(en) … hebben aan beide kanten fluïdum | schaal tussen twee fluïdumvolumes met dezelfde knopen | paneel als een laag volume-elementen, of fluïdum aan één kant |
| ERROR: … vlak(ken) van KOPPEL_-selecties liggen niet aan precies een fluïdum-element | `KOPPEL_`-vlak dat geen fluïdumvlak is | kies vlakken op het grensvlak fluïdum–constructie |
| ERROR: … OPEN_-selectie '…' is een elementselectie / KOPPEL_-selectie '…' is een …selectie | verkeerde soort selectie | `OPEN_`: knopen of vlakken; `KOPPEL_`: vlakken |
| ERROR: … fluid pressure op '…' is …; in de modes kan alleen 0 / impedantie op … | *fluid pressure* ≠ 0 of *impedance* in het model | zet de waarde op 0 (of gebruik `OPEN_`), onderdruk de impedantie |
| WARNING: … geen koppelvlak gevonden | fluïdum en constructie delen geen knopen | voeg de knopen samen (één doorlopend mesh) |
| WARNING: … belastingen (…) tellen niet mee in de modes | krachten/drukken in het model | normaal; ze hebben geen invloed op de modes |
| WARNING: … N van de M gevraagde modes gevonden | de oplosser vond in de band niet alle modes; meestal een mechanisme (bijv. een schaal waarvan maar één rotatie vastligt, valse modes bij ~0 Hz) | controleer de opleggingen; vraag minder modes of verhoog `vibro_freq_min` |
| INFO: … valse mode(s) … weggelaten | Code-Aster gaf een mode onder de ondergrens of met massa ≤ 0 terug (§6.5) | normaal |
| WARNING: Onderde(e)l(en) … hebben een materiaal met een geluidssnelheid en zonder elasticiteitsmodulus | een fluïdum in een andere analyse dan `vibroacoustic_modes_3d` | kies `vibroacoustic_modes_3d` (of `auto` bij een Frequency-model) |
| alarm `MODELISA4_8` / `MODELISA8_13` (mailles doubles) | een schaal op een fluïdumvlak: schaal en koppelvlak zijn aparte cellen met dezelfde knopen | onschuldig (VA-03, VA-05) |
| alarm `ALGELINE5_15` | de fout van een mode is net groter dan *Controle modes* | *Controle modes* 1e-5 |

## 7. Vibro-akoestiek harmonisch (`vibroacoustic_harm_3d`)

Hetzelfde model als §6 (constructie + fluïdum, één doorlopend mesh), maar nu **per
frequentie** aangestoten: de bridge rekent de stationaire respons op een harmonische
kracht op de constructie, een trillend vlak in het fluïdum of een invallende
geluidsgolf, met absorberende randen waar het geluid wegloopt. Voorbeelden: een
machinekap of paneel dat geluid afstraalt naar een ruimte (SPL op een microfoon), een
zuiger of membraan op een kanaal met een anechoïsch einde, een luidspreker in een kast,
een tankwand die door een drukgolf in het water wordt aangestoten. Mecway heeft geen
harmonische en geen gekoppelde analyse (Mecway Ltd., 2026, hoofdstuk 6); `auto` blijft
bij zo'n model de gekoppelde modes kiezen (§6), deze analyse kies je zelf.

| Wat | Hoe in Mecway | Code-Aster |
|---|---|---|
| analyse | *Frequency 3D* (V30) met een fluïdum-onderdeel (§6.1); in de bridge `vibroacoustic_harm_3d` (pagina *Vibro-akoestiek (harmonisch)*) | `DYNA_VIBRA` `TYPE_CALCUL='HARM'`, `BASE_CALCUL='PHYS'` |
| kracht op de constructie | Mecway-belastingen (*force*, *pressure*, *gravity*, ...) = de amplitude; fase met `#ASTER-FASE selectie = graden`; een Mecway-tabel = amplitude tegen de frequentie (kolom *time* = Hz), zoals de harmonische respons ([`Respons_op_modale_basis.md`](Respons_op_modale_basis.md)) | `CALC_VECT_ELEM` → `EXCIT` (`PHAS_DEG`, `FONC_MULT`) |
| snelheidsbron in het fluïdum | vlakselectie **`BRON_...`** (of `SOURCE_...`) op een vlak van het fluïdum: normaalsnelheid = *Snelheid BRON_-vlakken*, de fluid in; of **`#ASTER-BRON selectie = v [m/s, mm/s] [, fase]`** | `AFFE_CHAR_MECA` `VITE_FACE` |
| invallende golf | vlakselectie **`INVALLEND_...`** (of `INCIDENT_...`): een vlakke golf met amplitude *Amplitude invallende golf* loopt door dit vlak het fluïdum in; het vlak laat teruggekaatste golven ongehinderd door; of **`#ASTER-BRON selectie = p [Pa] [, fase]`** | `AFFE_CHAR_MECA` `ONDE_FLUI` + matrix `ONDE_FLUI` |
| absorberende rand (ρc) | vlakselectie **`ABSORBEREND_...`** (of `ABSORBING_...`) | `MODELISATION='3D_FLUI_ABSO'`, matrix `IMPE_MECA` |
| impedantie Z (reëel) | Mecway *Impedance* (*specific impedance*, Im = 0) op een vlak van het fluïdum | `3D_FLUI_ABSO` met een eigen materiaal c = Z/ρ |
| p = 0 | `OPEN_...` (knopen of vlakken), zoals §6 | `DDL_IMPO PRES=0, PHI=0` |
| microfoon | knoopselectie **`MICROFOON_...`** in het fluïdum: druk, fase en SPL per frequentie | log, CSV |
| meetpunt | knoopselectie **`MEETPUNT_...`** (of `PROBE_...`) op de constructie: verplaatsing per frequentie | log, CSV |
| demping van de constructie | Mecway *Rayleigh damping* (alleen op de constructie) en *Damper*-elementen | `MATR_AMOR` = α·M_s + β·K_s + `AMOR_MECA` |

De voorvoegsels gelden voor de naam in Mecway; hoofdletters maken niet uit.

### 7.1 Werkwijze in Mecway stap voor stap

1. **Model zoals voor de gekoppelde modes** (§6.1): constructie en fluïdum als één
   doorlopend mesh, fluïdum-materiaal met *Speed of sound* en *Density* zonder Young's
   modulus, opleggingen van de constructie, `OPEN_` voor p = 0. Een paneel dat naar een
   (half)open ruimte straalt: mesh een stuk lucht voor het paneel en sluit het af met
   een absorberende rand (stap 3).
2. **Bron.** Een kracht of druk op de constructie (bijv. een *force* op het
   bevestigingspunt van een motor): de waarde is de amplitude bij elke frequentie; voor
   een andere fase per selectie: `** ASTER-FASE Kracht2 = 90` in *CCX > Custom model
   definition*. Of een bron in het fluïdum: vlakselectie `BRON_Luidspreker` op een vlak
   van het fluïdum (snelheid de fluid in) of `INVALLEND_Inlaat` (een binnenkomende golf,
   bijv. de inlaat van een kanaal). Per selectie een eigen waarde en fase:
   `** ASTER-BRON Inlaat = 2 mm/s, 90` (snelheid) of `** ASTER-BRON Inlaat = 0.5 Pa, -30`
   (druk: invallende golf); de selectie heeft dan geen voorvoegsel nodig.
3. **Absorberende randen** waar het geluid het model uit moet: vlakselectie
   `ABSORBEREND_Wand` (ρc van het fluïdum: een loodrecht invallende vlakke golf kaatst
   niet terug), of Mecway's *Impedance* met een reële Z voor een gedeeltelijk
   absorberende wand (Z = ρc = 408 Pa·s/m voor lucht; Z > ρc harder, Z < ρc zachter).
   Leg een absorberende rand een eind van de bron (≥ een halve golflengte bij de
   laagste frequentie, §5.4).
4. **Microfoons en meetpunten:** knoopselectie `MICROFOON_Oor` in het fluïdum en
   `MEETPUNT_Kap` op de constructie (één knoop, of meer: dan het kwadratisch
   gemiddelde van de amplitude, zoals §5.4).
5. **Mesh-fijnheid:** het fluïdum zoals §5.1 (≥ 10 lineaire of ≥ 5 kwadratische
   elementen per golflengte bij de hoogste frequentie; de bridge waarschuwt), de
   constructie fijn genoeg voor de buiggolven bij de hoogste frequentie.
6. **Analyse:** kies in het hoofdvenster `vibroacoustic_harm_3d` (`auto` rekent de
   modes, §6).

### 7.2 In het hoofdvenster van de bridge

Pagina **Vibro-akoestiek (harmonisch)**:

| Instelling (label) | Standaard | Wanneer aanpassen |
|---|---|---|
| Resultaatvelden naar Mecway | verplaatsing, versnelling, spanning, von Mises | de druk gaat altijd mee; minder velden voor een kleinere `.liml`; spanningen alleen op volume-elementen van de constructie |
| Startfrequentie / Eindfrequentie [Hz] | 20 / 500 | het bereik van de vraag; de eindfrequentie bepaalt de mesh-fijnheid van het fluïdum (§7.1) |
| Aantal frequenties | 50 | meer om resonantiepieken te vangen (stap kleiner dan de piekbreedte, §7.4); de rekentijd groeit lineair (één factorisatie per frequentie) |
| Verdeling (lin / log) | lin | `log` over een breed bereik |
| Frequentielijst [Hz] (0 = bereik hierboven) | 0 | eigen frequenties, bijv. `100, 250, 500`; rond een gekoppelde mode uit §6 een fijne lijst |
| Snelheid BRON_-vlakken [m/s] | 0.001 | de werkelijke amplitude van de bron (p ∝ v) |
| Amplitude invallende golf INVALLEND_ [Pa] | 1 | de amplitude van de golf die het model in loopt (alles is lineair) |
| Tijdslimiet / Geheugenlimiet run_aster, MUMPS NPREC | 1800 s, 2048 MB, 8 | grote modellen of veel frequenties |

Per model met `#ASTER-OPTIE`, bijv. `** ASTER-OPTIE harm_freq_list = 125, 250, 500`
([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md), voorbeeld 27).
*Eerst Mecway-solve ter controle* heeft geen zin (INFO in de log).

### 7.3 Resultaten in Mecway

Onder *Solution* staat per frequentie een regel (*Mode 1 … Mode n* met de frequentie;
geen eigenmodes, maar de respons bij die frequentie). Velden per frequentie
(knoopwaarden):

| Veld | Waar | Betekenis |
|---|---|---|
| `displx/y/z`, `displix/y/z` | constructie (ook de knopen op het koppelvlak) | reëel en imaginair deel van de verplaatsing U [m] |
| `displampx/y/z`, `displmag`, `displphasex/y/z` | constructie | amplitude per richting, totale amplitude, fase [graden] |
| `rot*`, `rotamp*` | schalen en balken | rotatie (Re) en amplitude [rad] |
| `accamp*`, `accmag` (en `velamp*`, `velmag` met *velocities*) | constructie | ω²·\|U\| (ω·\|U\|) |
| `stress..`, `stressamp..`, `vonmises` | volume-elementen van de constructie | spanning (Re), amplitude per component, grootste von Mises over een periode |
| `pressure`, `pressurei` | fluïdum (ook de knopen op het koppelvlak) | reëel en imaginair deel van de druk P [Pa] |
| `pressuremag`, `pressurephase`, `spl` | fluïdum | \|P\|, fase [graden], geluidsdrukniveau 20·log10(\|P\|/(√2·20 µPa)) [dB] |

De tijdsfunctie is u(t) = Re(U·e^{iωt}) en p(t) = Re(P·e^{iωt}) (zoals §5.3 en de
harmonische respons van constructies). Mecway's API leest de frequenties en de velden
(headless nagelopen met een Mecway-script op VH-02: 8 frequenties, `displx`/`displix`
op de zuiger, `pressure`/`pressurei`/`spl` in de kolom); de weergave in de Mecway-GUI
is nog niet bekeken (KNOWN_BUGS 59).

In de **log** en het statusvak: het aantal frequenties, per microfoon het hoogste
niveau en per meetpunt de grootste amplitude; per frequentie in de log en in
`<model>_<run-id>_microfoons.csv` (kolommen als §5.3) en
`<model>_<run-id>_meetpunten.csv` (kolommen als de harmonische respons:
`meetpunt, frequentie_Hz, u_amp_m, a_amp_m_s2, ux_re_m, ...`).

### 7.4 Interpretatie en controles

- **Stralingsdemping:** een constructie die geluid afstraalt, verliest energie aan de
  golf die wegloopt; dat werkt als een demper. Een stijve zuiger met oppervlak A op een
  kolom met een ρc-einde voelt een kracht −ρcA·v, dus
  U = F / (k − mω² + iωρcA), ζ = ρcA/(2√(km)): de resonantiepiek blijft eindig zonder
  andere demping (verificatie VH-02: ζ = 0,17, U en de druk op ≤ 1,3e-4). Met een
  impedantie Z op het einde ziet de zuiger de ingangsimpedantie
  Z_in = ρc(1 + R·e^{−2ikL})/(1 − R·e^{−2ikL}), R = (Z − ρc)/(Z + ρc) (VH-03). Lucht op
  een staalplaat geeft weinig stralingsdemping, water of een lichte constructie veel.
- **Ingesloten fluïdum zonder absorptie:** geen stralingsdemping; bij een gekoppelde
  eigenfrequentie (§6) is de respons oneindig (WARNING). Geef de constructie demping
  (Rayleigh, dempers) of een absorberende rand, of kies frequenties tussen de modes.
- **Druk en SPL:** een vlakke golf met snelheid v heeft p = ρcv (lucht: 408 Pa per
  m/s); 1 Pa amplitude is 91,0 dB. SPL op de effectieve waarde (\|P\|/√2), zoals §5.4.
- **Invallende golf:** de amplitude is die van de golf die het model in loopt; met een
  absorberend einde is \|P\| overal die amplitude, met een harde wand op het einde 2× op
  de wand, met p = 0 (`OPEN_`) 0 (VH-05, VH-05b). Code-Aster's `ONDE_FLUI` met `PRES`
  geeft een binnenlopende golf met amplitude `PRES`/2 (ahlv101a: `PRES` 1 → 0,5 Pa); de
  bridge schrijft `PRES` = 2× de instelling.
- **Demping van de constructie:** Mecway's *Rayleigh damping* C = αM + βK werkt alleen
  op de constructie (de massa- en stijfheidsmatrix van de constructie-elementen), niet
  op het fluïdum (VH-04: α, VH-04b: β); dempers als in een modaal model (VH-04c).
- **Fase:** ten opzichte van de bron (fase 0); naijlen is negatief. Bij een
  weglopende golf staan de snelheid van de bron en de druk ervoor in fase.
- **Eigen controle:** de zuiger van het eerste punt (stijve plaat met een veer, kolom
  met een `ABSORBEREND_`-einde) is een eenvoudige testopstelling naast een eigen model.

### 7.5 Hoe de bridge vertaalt

`bridge_vibroacoustic_harm.py` maakt de `.comm` (template
`AsterTemplate_VibroAkoestiekHarm.comm`); route van de testcases ahlv101a (invallende
golf: `ONDE_FLUI` + `IMPE_MECA` als `MATR_IMPE_PHI`), ahlv100b (`VITE_FACE` met
`3D_FLUI_ABSO`) en ahlv302a:

1. Mesh, model en materialen zoals §6.5 (koppelvlakken `FLUI_STRU`, `U_P_PHI`), plus de
   bron- en golfvlakken als `3D_FLUIDE` en de absorberende vlakken als `3D_FLUI_ABSO`,
   alle randvlakken met de normaal uit het fluïdum (`ORIE_PEAU`). Een impedantie krijgt
   een eigen materiaal met `CELE_R = Z/ρ` (gemeten: VH-03 klopt daarmee op 1,2e-4).
2. Belastingen op de constructie zoals de harmonische respons (`CALC_VECT_ELEM` per
   last, fase `PHAS_DEG`, tabel `FONC_MULT` in de frequentie); bronnen per vlak
   `AFFE_CHAR_MECA(VITE_FACE=...)` en `AFFE_CHAR_MECA(ONDE_FLUI=_F(PRES=2·p_in))`
   (beide kennen alleen een reële waarde; de fase zit in `EXCIT`).
3. `ASSEMBLAGE` `RIGI_MECA`, `MASS_MECA` (Rayleigh: dezelfde matrices alleen op de
   constructie-groepen; dempers: `AMOR_MECA` met `AMOR_FLUI='NON'`), en apart
   `ONDE_FLUI` en `IMPE_MECA` op dezelfde nummering (`IMPE_MECA` weigert `CARA_ELEM`:
   `SUPERVIS_4`; `AMOR_MECA` met `GROUP_MA` gaf `DVP_1`).
4. `DYNA_VIBRA(TYPE_CALCUL='HARM', BASE_CALCUL='PHYS', MATR_IMPE_PHI=..., MATR_AMOR=...,
   AMOR_FLUI='NON')`: de bronnen als `EXCIT` met `PUIS_PULS=1, PHAS_DEG=90` (iω × de
   vector, zoals ahlv101a/ahlv100b), `VITE_FACE` met `COEF_MULT=−1` (ahlv100b geeft met
   +1 p = −ρcv: `VNOR` naar buiten; de bridge legt v de fluid in op). `AMOR_FLUI='NON'`
   zoals `DYNA_LINE` met `MATR_AMOR` en `MATR_IMPE_PHI` samen.
5. `CALC_CHAMP SIGM_NOEU` op de volume-elementen van de constructie;
   `aster_harmonic_export.py` schrijft per frequentie één `<mode>` met de verplaatsing
   (componenten DX…) en de druk (component `PRES` van `DEPL`), plus de CSV's.

**Waarom direct (`PHYS`) en niet op modale basis** (zoals `harmonic_3d` standaard): in
`U_P_PHI` geeft elke vrijheidsgraad φ een valse mode bij 0 Hz (§6.5), dus een modale
basis heeft de `BANDE`-zoektocht nodig en mist de quasi-statische bijdrage; de
absorberende rand is geen proportionele demping, zodat de reële modes niet ontkoppelen
(en de stralingsdemping is juist wat je wilt zien); de testcases rekenen ook zo. Nadeel:
één factorisatie per frequentie.

Met `med_export` aan schrijft de bridge `DEPL_REEL`/`DEPL_IMAG` (met `PRES`) in de
`.rmed`. Eigen nabewerking op `res` (type `DYNA_HARMO`) met `#ASTER-POST`; lasten uit
`#ASTER-EXCIT` tellen alleen als oplegging (zoals de harmonische respons).

### 7.6 Wat niet kan

- **Complexe of frequentieafhankelijke impedantie** (Im Z ≠ 0): ERROR (KNOWN_BUGS 59;
  zoals §5.6).
- **Opgelegde druk ≠ 0** (*fluid pressure* met een waarde): ERROR; gebruik `BRON_`,
  `INVALLEND_` of `#ASTER-BRON`. Een opgelegde (basis)beweging van de constructie ≠ 0:
  ERROR (zoals de harmonische respons).
- **Schuine inval** of een bolgolf: `ONDE_FLUI` en `3D_FLUI_ABSO` zijn exact voor een
  loodrecht invallende vlakke golf; schuin kaatst deels terug (zoals §5.4).
- Volumedemping in het fluïdum, poreuze materialen, hysteretische demping van de
  constructie (`AMOR_HYST`), extra modale demping (`modal_damping`; de berekening is
  direct).
- Een bron op een knoop of in het volume (bronnen alleen op vlakselecties, microfoons
  alleen op knoopselecties: WARNING).
- Alles wat in de gekoppelde modes niet kan (§6.6): twee fluïda met een verschillende
  dichtheid die elkaar raken, een schaal met fluïdum aan beide kanten, voorspanning,
  klotsen.
- Spanningen in schalen en balken (alleen verplaatsingen/rotaties), reacties.
- Vergelijking met een Mecway-solve (Mecway heeft deze analyse niet).

### 7.7 Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Vibro-akoestiek harmonisch: het model heeft geen fluïdum | geen fluïdum-onderdeel (§6.1) | fluïdum-onderdeel met *Speed of sound* en *Density* zonder E, of kies `harmonic_3d` |
| ERROR: … geen bron: geen belasting op de constructie …, geen BRON_- of INVALLEND_-vlakselectie en geen #ASTER-BRON | niets drijft het model aan | een kracht/druk op de constructie of een bronvlak |
| ERROR: … bron / invallende golf / absorberende rand '…' ligt niet aan precies een fluïdum | de vlakken liggen (deels) op de constructie of aan twee fluïda | kies vlakken van één fluïdum-onderdeel (*Face selection* op de lucht) |
| ERROR: … '…' is een knoop-/elementselectie; kies een vlakselectie | `BRON_`/`INVALLEND_`/`ABSORBEREND_` op knopen | maak een *Face selection* |
| ERROR: … selectie '…' is zowel … als … | dezelfde selectie met twee rollen | aparte selecties |
| ERROR: … '#ASTER-BRON …': verwacht 'selectie = snelheid [m/s, mm/s, …] of druk [Pa, N/m2, …] [, fase in graden]' (eventueel: eenheid '…' niet herkend) | schrijffout of een onbekende eenheid | bijv. `** ASTER-BRON Inlaat = 2 mm/s, 90` (punt als decimaalteken) |
| ERROR: … impedantie op '…' is complex / Re Z moet een getal > 0 zijn | *specific impedance* met Im ≠ 0 of Re ≤ 0 | alleen een reële Z > 0 |
| ERROR: … fluid pressure op '…' is …; een opgelegde druk != 0 … | *fluid pressure* met een waarde | `OPEN_` (p = 0) of een bron |
| ERROR: … opgelegde verplaatsing of rotatie <> 0 | basisbeweging | waarde 0; de belasting als kracht of bron |
| ERROR: … frequentielijst / frequentiebereik … is ongeldig | instellingen | bijv. `100, 250, 500`, of `0` voor het bereik |
| WARNING: … geen absorberende rand … en geen demping … oneindig | gesloten fluïdum zonder demping | absorberende rand of Rayleigh/dempers, of frequenties tussen de modes (§6) |
| WARNING: … geen koppelvlak gevonden | fluïdum en constructie delen geen knopen | één doorlopend mesh (§6.1) |
| WARNING: Akoestiek harmonisch: … minder dan 10 (lineair) / 5 (kwadratisch) elementen per golflengte | fluïdummesh te grof voor de hoogste frequentie | mesh verfijnen of de eindfrequentie verlagen |
| WARNING: … microfoon '…' is een vlakselectie | microfoon geen knoopselectie | *Node selection* |
| alarm `MODELISA4_8` / `MODELISA8_13` | schaal op een fluïdumvlak (koppelvlak en schaal zijn aparte cellen), of twee discrete elementen op dezelfde knopen | onschuldig (VH-06, VH-04c) |

## 8. Bronnen

- EDF R&D (2025). *code_aster 17.4, testcases* adlv100a (zuiger tussen een waterkolom
  met vrij oppervlak en een gesloten luchtkolom: `3D_FLUIDE`, `FLUI_STRU`, `DDL_IMPO
  PRES`/`PHI`, `CALC_MODES`, VALE_REFE 13,8285 Hz), adlv100b/adls102a/fdlv112h
  (`ORIE_PEAU` met `GROUP_MA_INTERNE` = fluïdum), adlv100p, adlv312a (schaal + fluïdum,
  `BANDE`, `COEF_DIM_ESPACE`), sdlv102a (`FORMULATION='U_P'`) en ahlv101a (`U_P_PHI`
  harmonisch met `3D_FLUI_ABSO` en `ONDE_FLUI`: TEST_RESU nagebouwd in VH-01),
  ahlv100b (`VITE_FACE` met `3D_FLUI_ABSO`, `IMPE_MECA`: VH-01b) en ahlv302a
  (`DYNA_LINE` met `MATR_IMPE_PHI`), `share/aster/tests` van de installatie; catalogus
  `affe_modele.py` (`FORMULATION` U_P_PHI/U_P/U_PSI, standaard U_P_PHI), `info_mode.py`,
  `extr_mode.py`, `norm_mode.py`, `dyna_vibra.py` (`MATR_IMPE_PHI`, `AMOR_FLUI`),
  `affe_char_meca.py` (`VITE_FACE`, `ONDE_FLUI`: alleen reële waarden), `assemblage.py`
  (`IMPE_MECA`, `ONDE_FLUI`); `MacroCommands/dyna_line_ops.py` (`AMOR_FLUI='NON'` met
  `MATR_AMOR` en `MATR_IMPE_PHI`); elementen `MEFL_*` (fluïdum, ook piramides) en
  `MEFS_FACE*` (koppelvlak) in `lib/aster/elem.1`.
- EDF R&D (2025). *code_aster 17.4, testcases* ahlv100a (golfgeleider, `RIGI_ACOU`,
  `MASS_ACOU`, `COMB_MATR_ASSE PARTIE='REEL'`, `CALC_MODES`; harmonisch: `3D_ABSO`,
  `AMOR_ACOU`, `VITE_FACE`, `DYNA_VIBRA HARM`, `PRAC_ELNO`) en adlv101f
  (`AFFE_CHAR_ACOU PRES_IMPO`, `PRES=0j`), `share/aster/tests` van de installatie.
- EDF R&D (2025). *code_aster 17.4, catalogus* `lib/aster/code_aster/Cata/Commands/`:
  `calc_modes.py` (`MATR_AMOR` alleen `matr_asse_depl_r`/`gene_r`), `dyna_vibra.py`
  (`HARM` `PHYS` met `matr_asse_pres_c`, `LIST_FREQ`, `EXCIT` `PUIS_PULS`/`PHAS_DEG`),
  `affe_char_acou.py`, `defi_materiau.py` (`FLUIDE`: `RHO`, `CELE_R`, `CELE_I`); elementen `ACOU_HEXA8/20`,
  `ACOU_PENTA6/15`, `ACOU_TETRA4/10` in `lib/aster/elem.1`.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: hoofdstuk
  6 (analysetypen, geen harmonische akoestiek), §6.9 Acoustic Resonance (§6.9.2
  complexe modes en de impedantieterm), §9.34 Fluid pressure, §9.35 Impedance, §17.13 Acoustic Analysis
  of an Organ Pipe.
- Kinsler, L.E., Frey, A.R., Coppens, A.B. & Sanders, J.V. *Fundamentals of
  Acoustics*. New York: Wiley. Niet lokaal ingezien; de formules in §1.5 en §5.4 zijn
  nagerekend in de verificatie (AK-01…05, AH-01…08); de kolomformules van §6.4 in
  VA-01…04; de zuiger- en golfformules van §7.4 in VH-02…06.
