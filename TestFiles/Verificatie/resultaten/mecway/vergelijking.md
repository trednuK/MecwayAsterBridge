# Mecway-route: vergelijking met de gewone run

Gemaakt door `run_verificatie.py --mecway-opslaan` op 2026-11-18. Elk model is eerst door Mecway geopend en opgeslagen (`TestFiles/Tools/mw_save_as.py`), daarna door de bridge en Code-Aster gerekend en vergeleken met `../resultaten.json`.

**3315 controles identiek** (zelfde status, FEM-waarde gelijk tot 1e-6 relatief, of tot 1e-6 x de absolute tolerantie bij grootheden rond 0), **2 anders**, **4 niet mogelijk** (645 testcases).

.comm (zonder commentaarregels en paden) anders dan in de gewone run: FX-02, FX-05, MT-01, MT-04, MT-05, MT-07, WE-07, WE-08, WE-09, WE-10, WE-12, WE-12b, WE-12c, WE-13; alleen in de laatste cijfers van getallen (Mecway schrijft 15 significante cijfers): BU-24, BU-31, BU-34, BU-36, BU-40, BU-45b, BU-45d, DY-01a, DY-01b, DY-01c, DY-01d, DY-02, DY-04b, DY-72, DY-73, FX-04, HR-01d, HR-02a, HR-02b, HR-02c, LS-07f, LS-07k, LS-30b, LS-31, LS-31b, LS-31c, LS-31d, LS-62, LS-97a, LS-97b, LS-97c, LS-97g, LS-97h, LS-97i, LS-97j, LS-97k, LS-97l, MC-01b, MC-02b, MD-03, MP-01, MP-02, MP-03, MP-20b, NK-10, NL-90b, OR-03, OR-04, OR-14, PL-10, PL-67.

| ID | Controle | Gewoon | Mecway | rel. verschil | Toelichting |
|---|---|---|---|---|---|
| LS-20e | u eindvlak |  |  |  | niet mogelijk: MECWAY_TIMEOUT (opslaan) |
| LS-20e | reactiekracht X |  |  |  | niet mogelijk: MECWAY_TIMEOUT (opslaan) |
| LS-20e | massa (controle) |  |  |  | niet mogelijk: MECWAY_TIMEOUT (opslaan) |
| LS-20e | som reacties X (controle) |  |  |  | niet mogelijk: MECWAY_TIMEOUT (opslaan) |
| LS-97c | torque MT = 0 | OK | OK | 4.95e-06 | 5.7980e-12 -> 8.5265e-13 |
| PL-47 | hoopstress binnenring binnenwand (minimum) | - | OK |  | niet in de gewone run |
