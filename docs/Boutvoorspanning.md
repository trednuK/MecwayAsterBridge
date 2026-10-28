# Boutvoorspanning (Pre-tension section)

*English version: [Bolt_pretension.md](en/Bolt_pretension.md)*

Mecway's *Pre-tension section* (handleiding v34 §9.11) spant een bout of een ander
prismatisch deel voor: met een **kracht** (trek positief) of een **lengteverandering**
(*Length adjustment*: de vrije lengte verandert, positief = verkorting). De bridge
vertaalt de variant met een prisma van volume-elementen (in Mecway de CCX-variant) in
**Lineair statisch** (S30, `lin_static_3d`) en **Niet-lineair statisch** (L30,
`nonlin_static_3d`).

## 1. Gebruiken

1. Modelleer de bout (of het voor te spannen deel) met volume-elementen: hex, wedge,
   tet of piramide, lineair of kwadratisch. Het deel waar de doorsnede komt moet
   prismatisch zijn (dezelfde doorsnede langs de as).
2. *Loads and constraints* > *Pre-tension section*: selecteer minstens twee
   **buitenvlakken van de schacht onder verschillende hoeken**, bijv. het hele
   cilindervlak van een stuk schacht. Die vlakken bepalen de as (loodrecht op hun
   normalen) en de axiale lengte; de doorsnede komt in het **midden** van die lengte.
   Selecteer vlakken aan beide kanten van de plek waar de doorsnede moet komen.
3. Kies *Force* (bijv. `10 kN`) of *Length adjustment* (bijv. `0.01 mm`). Beide
   mogen constant zijn, een tabel in de tijd of een formule in t.
4. Mecway rekent de doorsnede zelf alleen met CCX; voor de bridge maakt de
   solverkeuze in Mecway niet uit. Kies de analyse Static 3D of Nonlinear static 3D
   en start de bridge zoals gewoonlijk.

Er zijn geen instellingen. De bridge meldt de doorsnede in de log: as, axiale
lengte, plek van de doorsnede, doorsnede-oppervlak met de nominale spanning F/A, het
aantal elementen aan beide kanten en het referentieknooppunt.

## 2. Kracht of lengteverandering

| Mecway | Wat vast blijft | Onder een extra externe last |
|---|---|---|
| Force | de kracht in de doorsnede, de hele berekening lang | de boutkracht blijft F (de bout rekt mee); er is geen "vergrendeling" na het aanspannen |
| Length adjustment | de verkorting | de boutkracht verandert met de stijfheden (verbindingsdiagram: + P kb/(kb + kc)) |

![Boutkracht tegen externe last](img/pretension_force_vs_adjustment.svg)

1. Kracht: de boutkracht Fb blijft gelijk aan de opgegeven kracht, wat de externe last P ook is.
2. Lengteverandering: de boutkracht stijgt met P met de helling kb/(kb + kc) (kb bout, kc geklemde delen), zolang de delen geklemd blijven.
3. De voorspanning Fp bij P = 0 (beide manieren; bij de lengteverandering Fp = kb kc/(kb + kc) × verkorting).

Zo doet Mecway het (CCX: de kracht blijft een `*CLOAD` op het pre-tension-knooppunt,
de lengteverandering is een `*BOUNDARY`) en zo doet de bridge het (verificatie PT-03
en PT-04: gelijk aan Mecway binnen 0,01%). Wilt u een aangespannen en daarna
vergrendelde bout onder een latere last? Gebruik de lengteverandering met de
verkorting die de gewenste voorspanning geeft (PT-03: Fp = kb kc/(kb + kc) ×
verkorting; Mecway heeft ook geen twee stappen "kracht, dan vastzetten").

Tijdsverloop: zoals een gewone kracht of opgelegde verplaatsing. In Niet-lineair
statisch met Mecway's *Quasi-static* tijdstappen werkt een constante waarde vanaf de
eerste stap volledig (zoals in Mecway, BoltedJoint); zonder tijdstappen lopen de
lasten op.

## 3. Hoe de bridge vertaalt

![Prisma, doorsnede en knooppaar](img/pretension_cut.svg)

1. De geselecteerde buitenvlakken van de schacht (minstens twee onder verschillende hoeken).
2. De as n, loodrecht op de normalen van die vlakken.
3. De axiale lengte van de geselecteerde vlakken; het prisma zijn de volume-elementen daarbinnen.
4. De doorsnede in het midden van die lengte.
5. De kant onder (langs n): de elementen krijgen kopieën van de knopen van de doorsnede.
6. De kant boven: houdt de Mecway-knopen; Mecway toont deze waarden.
7. Een Mecway-knoop op de doorsnede (kant boven).
8. Zijn kopie (kant onder), op dezelfde plek; de twee verschillen de verkorting δ langs n en zijn gelijk dwars op n.
9. Het referentieknooppunt: zijn DX is δ; het draagt de kracht F of de opgelegde δ.

- **Prisma** (zoals Mecway, handleiding §9.11): de as is de mediaan van de
  kruisproducten van de normalen van elk paar geselecteerde vlakken (hoogstens 1000
  vlakken), de axiale lengte die van de geselecteerde vlakken; het prisma bevat alle
  volume-elementen binnen die lengte die met de geselecteerde vlakken of met elkaar
  verbonden zijn.
- **Doorsnede**: elk prisma-element ligt onder of boven het midden van de lengte (zijn
  zwaartepunt langs de as). De knopen die beide kanten delen zijn de doorsnede; in een
  gestructureerd mesh is dat een laag elementvlakken, in een tet-mesh een zigzagvlak
  over vlakken, ribben en hoekknopen (PT-05). Mecway voegt daar voor CCX een dunne laag
  elementen in; de bridge heeft die niet nodig.
- **Snede**: de elementen onder (langs de as) krijgen een kopie van de knopen van de
  doorsnede (nieuwe knopen na de Mecway-knopen). Per knooppaar drie `LIAISON_DDL`:
  u(boven) − u(onder) + δ·n = 0, met n de as en δ de verkorting = `DX` van een
  **referentieknooppunt** (POI1 met `DIS_T` stijfheid 0, groep `BRPRET`; `DY` = `DZ` =
  0). De tangentiële componenten blijven gelijk, de normale verschillen δ; dat is de
  formulering van CCX zelf (`pretensionsections.f`) en het aanspannen van de officiële
  testcase ssnv106a.
- **Belasting**: kracht → `FORCE_NODALE FX` = F op het referentieknooppunt (de
  arbeidsgeconjugeerde van δ is de normaalkracht, trek positief); lengteverandering →
  `DDL_IMPO DX` = δ. De Mecway-belasting wijst naar de knoopgroep `BRPT<k>` van dat
  knooppunt.

## 4. Resultaten in Mecway

- De knopen op de doorsnede tonen de waarden van de kant **boven** (de hogere kant
  langs de as, de grootste ascomponent positief). De sprong δ over de doorsnede is in
  Mecway niet te zien (de kopieën zijn geen Mecway-knopen); in Mecway zelf zijn de
  knopen van de ingevoegde laag ook niet te zien.
- De boutkracht is bij een kracht precies F. Controleer hem met de nominale spanning
  in de log, of met de spanning in de schacht (in een grof mesh wijkt de knoopspanning
  bij de overgang naar de kop af; neem een knoop halverwege de schacht).

## 5. Testmodellen

PT-01 .. PT-05 in [`Verificatie.md`](Verificatie.md): staaf met kracht en met
lengteverandering (handberekening exact, Mecway 34 −0,004%), bout met huls tussen
stijve platen (verbindingsdiagram met lengteverandering, en met kracht onder een
oplopende externe last in Niet-lineair statisch), en een staaf in tet4 met een
zigzagdoorsnede.

## 6. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| ERROR: Pre-tension section op '...': alleen in lineair en niet-lineair statisch | een andere analyse (dynamische respons, modaal, knik, ...) | gebruik Statisch of Niet-lineair statisch (KNOWN_BUGS 122) |
| ERROR: ... alleen vlakken van volume-elementen (CCX-variant); de variant met een veerelement ... | de selectie bevat het eindvlak van een veer (Mecway's variant voor de interne solver) of vlakken van schalen/balken | selecteer vlakken van volume-elementen; vervang de veer door een kort staafje van volume-elementen (KNOWN_BUGS 122) |
| ERROR: ... geen as: kies minstens twee vlakken onder verschillende hoeken | alle geselecteerde vlakken evenwijdig (bijv. alleen één platte kant van een vierkante staaf) | selecteer ook een vlak onder een andere hoek (bijv. de aangrenzende kant) |
| ERROR: ... geen doorsnede door het prisma gevonden | één element langs de as, of de vlakken overspannen de plek van de doorsnede niet | selecteer vlakken van minstens twee elementlagen, aan beide kanten van de gewenste doorsnede |
| ERROR: ... de doorsnede raakt elementen buiten het prisma | elementen rond de doorsnede die buiten de axiale lengte reiken (bijv. een moer of plaat die samen met de bout gemesht is) | selecteer vlakken over een stuk schacht met alleen schachtelementen, of mesh de bout als eigen onderdeel (contact of bonded contact met de platen) |
| ERROR: ... de doorsnede gaat door knopen van een andere pre-tension section | twee doorsneden op dezelfde plek | verplaats er een |
| WARNING: Keuze LINE_QUAD ... niet toegepast: ... pre-tension section | hex8 met `elem_hex8` = LINE_QUAD | de middenknopen die Code-Aster maakt zouden in de doorsnede los blijven; gebruik hex20 in Mecway |

## 7. Wat niet kan

Zie ook KNOWN_BUGS 122.

- Dynamische respons (D30/D31) en de andere analyses: Mecway staat dynamica met CCX toe;
  de bridge stopt de doorsnede daar met een ERROR.
- De variant met een veerelement (interne solver, één veer met een lengteverandering).
- Een meedraaiende richting: de as blijft vast bij grote rotaties (ook in Mecway).
- Lasten, opleggingen en contact op vlakken die de doorsnede raken: aan de kant onder
  werken ze op de kopie (last, contact) of op de Mecway-knoop (alleen opleggingen); het
  verschil is hoogstens δ, zoals bij Mecway's ingevoegde laag.
- Samples/BoltedJoint zelf rekent niet met Code-Aster: plaat B wordt alleen door
  wrijvingscontact gehouden en Code-Aster stopt in de eerste stap (`MECANONLINE9_4`,
  pivot op een plaatknoop), ook zonder pre-tension section (KNOWN_BUGS 43).

## 8. Bronnen

- Mecway-handleiding v34 §9.11 (prisma, as, lengte, dunne laag, beperkingen); XML en
  CCX-invoer van Samples/BoltedJoint.liml en testmodellen, gelezen tijdens headless
  Mecway 34-solves (28 okt 2026): `force="true"` = kracht, `adjustment="true"` =
  lengteverandering, `*CLOAD` resp. `*BOUNDARY` op het pre-tension-knooppunt.
- CalculiX 2.23-bron die met Mecway meekomt, `pretensionsections.f`: per knooppaar twee
  tangentiële MPC's en één normale MPC met de vrijheidsgraad van het
  referentieknooppunt.
- Code-Aster 17.4: `LIAISON_DDL` (catalogus `affe_char_meca.py`, U4.44.01); testcase
  ssnv106a (aanspannen als relatieve verplaatsing tussen verdubbelde knopen).
