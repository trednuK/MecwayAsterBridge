# Orthotroop en anisotroop materiaal

*English version: [en/Orthotropic_material.md](en/Orthotropic_material.md)*

De Mecway-materialen *Orthotropic*, *Stiffness matrix* en *Compliance matrix* (handleiding
v34 §8.5) hebben andere eigenschappen in de richtingen U, V en W van de elementassen. De
bridge vertaalt ze op **volume-elementen** (hex, wedge, tet, piramide, lineair of
kwadratisch) in **Lineair statisch** (S30, `lin_static_3d`), **Modaal** (V30, `modal_3d`)
en **Knik** (B30, `buckling_3d`) naar de orthotrope
elasticiteit `ELAS_ORTH` van Code-Aster, met Mecway's *Element orientation* als richting
van de materiaalassen. Schalen, andere analyses en een volledig anisotrope matrix kunnen
nog niet (§6).

## 1. Gebruik

1. Materiaal > *Mechanical* > *Orthotropic*: elasticiteitsmoduli in 1 (U), 2 (V) en 3 (W),
   Poisson-getallen 12, 23, 31, glijdingsmoduli 12 (UV), 23 (VW), 31 (WU) en, voor
   thermische spanning, drie uitzettingscoëfficiënten. Of *Stiffness matrix* /
   *Compliance matrix* (6 × 6, de volgorde 1..6 = UU, VV, WW, VW, WU, UV, gemeten; let op:
   het tabblad *Orthotropic* noemt de glijdingsmoduli 12 (UV), 23 (VW), 31 (WU)).
2. De materiaalassen zijn de elementassen U, V, W. Bij volume-elementen zijn dat standaard
   de globale X, Y, Z. Draaien: *Element properties* (per element) of *Loads and
   constraints* > *Element orientation* op een elementselectie: de richting van **U** en
   een vector voor **V**, eventueel een extra draaiing om U (*angle*). Geef **zowel** U als
   V: met maar één van beide, of met V evenwijdig aan U, rekent Mecway het model niet en
   geeft de bridge een ERROR; een hoek zonder vectoren heeft geen effect. De oriëntatie mag
   een formule van het elementmidden (x, y, z) zijn.
3. Kies *Static 3D*, *Frequency* of *Buckling* en start de bridge zoals gewoonlijk. Mecway
   zelf staat de matrixtypen alleen in Static 3D toe (handleiding §8.5).

![Materiaalassen U, V, W uit de elementoriëntatie](img/orthotropic_axes.svg)

1. Standaard (geen oriëntatie): U, V, W = globale X, Y, Z.
2. U: de opgegeven vector (genormaliseerd).
3. De opgegeven V-vector hoeft niet loodrecht op U te staan.
4. V: de projectie van de opgegeven vector op het vlak loodrecht op U.
5. W = U × V (rechtsdraaiend).
6. *Angle*: V en W draaien over deze hoek om U.

## 2. Poisson-getallen en matrices

Mecway gebruikt het **grote** Poisson-getal: ν12 = −ε2/ε1 bij een spanning in richting 1,
ν23 = −ε3/ε2 bij een spanning in 2, en ν31 = −ε1/ε3 bij een spanning in 3 (handleiding
§8.5). `NU_LT`, `NU_LN`, `NU_TN` van Code-Aster zijn grote getallen in de volgorde L→T,
L→N, T→N; de bridge schrijft dus `NU_LT` = ν12, `NU_TN` = ν23 en `NU_LN` = ν31 · E1 / E3
(dezelfde term van de compliantie). Met E1 = 100 GPa, E3 = 10 GPa en ν31 = 0,05: `NU_LN` =
0,5. Dat is geen fout: controleer met ν31/E3 = `NU_LN`/E1.

Een *Stiffness matrix* of *Compliance matrix* wordt vertaald als hij **orthotroop is in de
elementassen**: alle termen die een normaalrek aan een schuifrek koppelen, of twee
schuifrekken, zijn nul (c14 … c16, c24 … c26, c34 … c36, c45, c46, c56). De bridge leidt
daar de negen technische constanten uit af. Code-Aster heeft voor volume-elementen geen
algemene anisotrope elasticiteit (`DEFI_MATERIAU` kent daar alleen `ELAS_ORTH` en
`ELAS_ISTR`); een matrix met koppeltermen geeft daarom een ERROR (§5). Schuiftermen zijn
technische schuifrekken (γ = 2ε), zoals in Mecway. Compliantie in m²/N (of mm²/N),
stijfheid in een drukeenheid.

## 3. Hoe de bridge vertaalt

| Mecway | Code-Aster |
|---|---|
| *Orthotropic* E, ν, G, α in U, V, W | `DEFI_MATERIAU` `ELAS_ORTH` `E_L`, `E_T`, `E_N`, `NU_LT`, `NU_LN`, `NU_TN`, `G_LT`, `G_LN`, `G_TN`, `RHO`, bij thermische spanning `ALPHA_L/T/N` (L, T, N = U, V, W) |
| *Stiffness matrix* / *Compliance matrix* (orthotroop) | dezelfde `ELAS_ORTH` (constanten uit de inverse van het normaalblok en de schuifdiagonaal); geen thermische uitzetting (die hebben deze typen in Mecway ook niet) |
| elementassen U, V, W (attributen, kaart, standaard) | `AFFE_CARA_ELEM` `MASSIF` `ANGL_REP` = (α, β, γ) nautische hoeken, per groep `BRORI<n>` van elementen met dezelfde assen |

Elementen met dezelfde assen delen een groep: een oriëntatie die voor een hele component
gelijk is, geeft één `MASSIF`-regel; een formule per element geeft zoveel groepen als er
verschillende oriëntaties zijn (WARNING boven 1000). Een element met zowel een kaart als
attributen gebruikt de kaart (Mecway rekent zo'n model niet).

## 4. Resultaten in Mecway

Spanningen en rekken komen terug in de **globale** assen X, Y, Z (`stressxx` …), zoals
Mecway ze toont. In Lineair statisch schrijft de bridge bij het veld *stresses* ook Mecway's
veld *stress in element coordinates* (`lamuu`, `lamvv`, `lamww`, `lamuv`, `lamvw`, `lamwu`)
voor alle volume-elementen van een model met orthotroop materiaal: de spanningstensor
gedraaid naar de elementassen U, V, W (R σ Rᵀ per elementknoop; in een knoop van elementen
met verschillende assen het gemiddelde van de elementknoopwaarden, zoals Mecway). Zo zie je
de spanning langs de vezel (U) direct.

## 5. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Materiaal '...' (StiffnessMatrix): de matrix koppelt normaal- en schuifrekken ... (termen c14 ... niet nul) | een volledig anisotrope matrix | Code-Aster kan dit niet voor volume-elementen; is het materiaal orthotroop in andere assen, voer het dan in die assen in en draai de elementoriëntatie |
| ERROR: Materiaal '...' (Orthotropic): de constanten geven geen positief definiete stijfheid | een modulus ≤ 0, of te grote Poisson-getallen (bijv. het kleine getal als groot ingevoerd) | controleer ν12² < E1/E2 enz.; Mecway rekent dit ook niet |
| ERROR: Orthotroop/anisotroop materiaal op schalen, membranen of balken | het materiaal op 2D- of 1D-elementen | gebruik daar een isotroop materiaal (schalen: STAPPENPLAN S13b) |
| ERROR: Orthotroop/anisotroop materiaal (elset ...) wordt nu alleen in Lineair statisch, Modaal en Knik vertaald | een andere analyse (niet-lineair, dynamica, modale superpositie, harmonisch, spectrum, thermisch → mechanisch, akoestiek, ...) | gebruik Static 3D, Frequency of Buckling (andere analyses: STAPPENPLAN S13c) |
| ERROR: Element orientation van ... volume-element(en) met orthotroop materiaal: alleen een U- of alleen een V-vector, of U evenwijdig aan V | de oriëntatie van een volume-element geeft maar één van beide vectoren, of V langs U (Mecway rekent dit ook niet) | geef U en een V-vector die niet evenwijdig is aan U |

## 6. Wat niet kan

Zie ook KNOWN_BUGS 130.

- Een matrix met koppeltermen (echt anisotroop, 21 constanten): niet in Code-Aster voor
  volume-elementen.
- Orthotroop materiaal en *Composite* op schalen en membranen (STAPPENPLAN S13b).
- Andere analyses dan Lineair statisch, Modaal en Knik (STAPPENPLAN S13c), en orthotrope
  warmtegeleiding in thermische analyses. Modaal met voorspanning, complexe modes en
  cyclische symmetrie gebruiken hetzelfde materiaal, maar zijn niet apart geverifieerd.
- *Stress in element coordinates* in Modaal en Knik (per mode).

## 7. Testmodellen

OR-01 .. OR-06 en OR-09 in [`Verificatie.md`](Verificatie.md): een kubus onder enkelassige trek met
gedraaide materiaalassen (elementattributen, een kaart met een hoek, de stijfheids- en de
compliantiematrix): alle zes globale rekken gelijk aan de wet van Hooke in U, V, W gedraaid
naar X, Y, Z en aan Mecway 34's eigen oplossing; dezelfde kubus vrij verwarmd (thermische rek
α1, α2, α3 in U, V, W gedraaid naar X, Y, Z, geen spanning); een ingeklemde balk met E1 en met
E2 langs de balk (Timoshenko). OR-07, OR-08, OR-10: de ingeklemde balk in Frequency (eerste
buigfrequenties) en als kolom in Buckling, gelijk aan Euler-Bernoulli binnen het schuifeffect
en aan Mecway's eigen oplossing. OR-11: *stress in element coordinates* op een staaf met
twee verschillende elementassen (R σ Rᵀ, en op het grensvlak het gemiddelde van de
elementknoopwaarden, zoals Mecway).

## 8. Bronnen

- Mecway-handleiding v34 §7.4.2 (elementassen, projectie van de vector), §8.5 (orthotrope
  en anisotrope materialen, groot Poisson-getal, materiaalassen = elementassen, bij
  volume-elementen standaard globaal); attribuutnamen uit `mecway.exe` (`youngsmodulusu` …
  `shearmoduluswu`, `thermalexpansionu/v/w`, `c11` … `c66`, `s11` … `s66`); betekenis
  gemeten met headless oplossingen van Mecway 34 (kubussen onder een opgelegde homogene
  rek, 28 okt 2026).
- Code-Aster 17.4: catalogus `defi_materiau.py` (`ELAS_ORTH`, `ELAS_ISTR`; geen algemene
  3D-anisotropie), U4.43.01 (`ELAS_ORTH`); `affe_cara_elem.py` (`MASSIF` `ANGL_REP`),
  U4.42.01; nautische hoeken zoals in `code_aster/MacroCommands/observation_ops.py`
  (`anglnaut`).
