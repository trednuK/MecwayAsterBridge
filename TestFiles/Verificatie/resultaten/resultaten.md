# Verificatieresultaten MecwayAsterBridge

Gemaakt door `run_verificatie.py` op 2026-10-23 (bridge 8298c14, Code-Aster 17.4). Toelichting en bronnen: `docs/Verificatie.md`.

**2312 van 2318 controles binnen de tolerantie** (431 testcases); 6 buiten de tolerantie door een bekende beperking (BEKEND, zie `KNOWN_BUGS.md`), 0 onverwacht (NOK/FOUT).

## Adaptieve verfijning

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| AD-01-n1 | Plaat met gat (vlakke rek), uniform hex20 2x2 per blok | Kt_n | 2.519  | 1.8339 | -27.20% | 30% | OK |
| AD-01-n16 | Plaat met gat (vlakke rek), uniform hex20 32x32 per blok | Kt_n | 2.519  | 2.5 | -0.75% | 2% | OK |
| AD-01-n2 | Plaat met gat (vlakke rek), uniform hex20 4x4 per blok | Kt_n | 2.519  | 2.1595 | -14.27% | 16% | OK |
| AD-01-n32 | Plaat met gat (vlakke rek), uniform hex20 64x64 per blok | Kt_n | 2.519  | 2.5156 | -0.14% | 0.5% | OK |
| AD-01-n4 | Plaat met gat (vlakke rek), uniform hex20 8x8 per blok | Kt_n | 2.519  | 2.3593 | -6.34% | 8% | OK |
| AD-01-n8 | Plaat met gat (vlakke rek), uniform hex20 16x16 per blok | Kt_n | 2.519  | 2.4569 | -2.47% | 3% | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | lus met Mecway gedraaid (fractie verfijningsstappen) | 1  | 1 | +0.00% | 0  | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | Kt_n na de lus | 2.519  | 2.5397 | +0.82% | 2% | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | elementen / uniform (Refine x2) tot 2% | 0  | 0.32166 | 0.32166 | 0.999  | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | globale fout daalt elke lus (max rel_k/rel_k-1) | 0  | 0.82005 | 0.82005 | 0.999  | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | verfijnd binnen 3r van het gat (fractie) | 1  | 0.98016 | -1.98% | 0.1  | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | sqrt(som eta_e^2) / eta globaal | 1  | 1 | +0.00% | 0.1% | OK |
| AD-02 | Plaat met gat: adaptieve verfijningslus (Mecway refine_x2) | sigma_xx aan het eindvlak | 1.0000e+08 Pa | 1.0001e+08 | +0.01% | 0.5% | OK |
| AD-03 | Adaptieve verfijning: inklemming op een knoopselectie -> ERROR | lus stopt voor verfijnen (1 = ja) | 1  | 1 | +0.00% | 0  | OK |

## Akoestiek harmonisch

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=100 Hz: max|p| (lambda = 3.4 m) | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=100 Hz: min|p| | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=100 Hz: faseval over L | 1.848 rad | 1.848 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=340 Hz: max|p| (lambda = 1 m) | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=340 Hz: min|p| | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=340 Hz: faseval over L | 6.2832 rad | 6.2831 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=680 Hz: max|p| (lambda = 0.5 m) | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=680 Hz: min|p| | 0.408 Pa | 0.40793 | -0.02% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=680 Hz: faseval over L | 12.566 rad | 12.565 | -0.01% | 1% | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=340 Hz: spl op x = 0 | 83.182 dB | 83.182 | -0.00% | 0.01 dB | OK |
| AH-01 | Vlakke golf, absorberend einde, hex20 20x1x1 | f=340 Hz: pressuremag = |pressure + i pressurei| | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=100 Hz: max|p| (lambda = 3.4 m) | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=100 Hz: min|p| | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=100 Hz: faseval over L | 1.848 rad | 1.848 | -0.00% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=340 Hz: max|p| (lambda = 1 m) | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=340 Hz: min|p| | 0.408 Pa | 0.40793 | -0.02% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=340 Hz: faseval over L | 6.2832 rad | 6.2825 | -0.01% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=680 Hz: max|p| (lambda = 0.5 m) | 0.408 Pa | 0.408 | -0.00% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=680 Hz: min|p| | 0.408 Pa | 0.40698 | -0.25% | 1% | OK |
| AH-01b | Vlakke golf, absorberend einde, hex20 10x1x1 (5 per golflengte bij 680 Hz) | f=680 Hz: faseval over L | 12.566 rad | 12.546 | -0.16% | 1% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=100 Hz: max|p| (lambda = 3.4 m) | 0.408 Pa | 0.40828 | +0.07% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=100 Hz: min|p| | 0.408 Pa | 0.40813 | +0.03% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=100 Hz: faseval over L | 1.848 rad | 1.8472 | -0.04% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=340 Hz: max|p| (lambda = 1 m) | 0.408 Pa | 0.40969 | +0.41% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=340 Hz: min|p| | 0.408 Pa | 0.408 | +0.00% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=340 Hz: faseval over L | 6.2832 rad | 6.2575 | -0.41% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=680 Hz: max|p| (lambda = 0.5 m) | 0.408 Pa | 0.41502 | +1.72% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=680 Hz: min|p| | 0.408 Pa | 0.40826 | +0.06% | 2% | OK |
| AH-02a | Vlakke golf, absorberend einde, hex8 20x1x1 (10 per golflengte bij 680 Hz) | f=680 Hz: faseval over L | 12.566 rad | 12.365 | -1.60% | 2% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=100 Hz: max|p| (lambda = 3.4 m) | 0.408 Pa | 0.40807 | +0.02% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=100 Hz: min|p| | 0.408 Pa | 0.40803 | +0.01% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=100 Hz: faseval over L | 1.848 rad | 1.8478 | -0.01% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=340 Hz: max|p| (lambda = 1 m) | 0.408 Pa | 0.40842 | +0.10% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=340 Hz: min|p| | 0.408 Pa | 0.408 | +0.00% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=340 Hz: faseval over L | 6.2832 rad | 6.2767 | -0.10% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=680 Hz: max|p| (lambda = 0.5 m) | 0.408 Pa | 0.40969 | +0.41% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=680 Hz: min|p| | 0.408 Pa | 0.408 | +0.00% | 1% | OK |
| AH-02b | Vlakke golf, absorberend einde, hex8 40x1x1 (20 per golflengte bij 680 Hz) | f=680 Hz: faseval over L | 12.566 rad | 12.515 | -0.41% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=100 Hz: |p(0)| | 0.11609 Pa | 0.11609 | -0.00% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=100 Hz: |p(L)| | 0.42419 Pa | 0.42419 | -0.00% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=100 Hz: max|P - P_exact| / max|P_exact| | 0 - | 1.1510e-07 | 1.1510e-07 | 0.01 - | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=250 Hz: |p(0)| | 0.037807 Pa | 0.03781 | +0.01% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=250 Hz: |p(L)| | 0.40975 Pa | 0.40975 | -0.00% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=250 Hz: max|P - P_exact| / max|P_exact| | 0 - | 8.9654e-06 | 8.9654e-06 | 0.01 - | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=420 Hz: |p(0)| | 0.037807 Pa | 0.037856 | +0.13% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=420 Hz: |p(L)| | 0.40975 Pa | 0.40975 | -0.00% | 1% | OK |
| AH-03 | Buis met harde wand op x = L, hex20 20x1x1 | f=420 Hz: max|P - P_exact| / max|P_exact| | 0 - | 1.2033e-04 | 1.2033e-04 | 0.01 - | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO1 Re p (ahlv100a VALE_REFE) | -6.2426 Pa | -6.2425 | +0.00% | 0.1% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO1 Re p (ahlv100a VALE_CALC) | -6.2425 Pa | -6.2425 | +0.00% | 0.0001% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO1 Im p (ahlv100a VALE_REFE = 0) | 0 Pa | -3.1802e-04 | -3.1802e-04 | 0.0062426 Pa | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO1 Im p (ahlv100a VALE_CALC) | -3.1779e-04 Pa | -3.1802e-04 | -0.07% | 6.24251e-06 Pa | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO780 Re p (ahlv100a VALE_REFE) | -6.2426 Pa | -6.2425 | +0.00% | 0.1% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO780 Re p (ahlv100a VALE_CALC) | -6.2425 Pa | -6.2425 | +0.00% | 0.0001% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO780 Im p (ahlv100a VALE_REFE = 0) | 0 Pa | -3.1802e-04 | -3.1802e-04 | 0.0062426 Pa | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO780 Im p (ahlv100a VALE_CALC) | -3.1772e-04 Pa | -3.1802e-04 | -0.09% | 6.24251e-06 Pa | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO751 Re p (ahlv100a VALE_REFE) | 6.0237 Pa | 6.0222 | -0.03% | 0.1% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO751 Re p (ahlv100a VALE_CALC) | 6.0222 Pa | 6.0222 | -0.00% | 0.0001% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO751 Im p (ahlv100a VALE_REFE) | 1.6387 Pa | 1.6441 | +0.33% | 0.33% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO751 Im p (ahlv100a VALE_CALC) | 1.6441 Pa | 1.6441 | +0.00% | 6.24256e-06 Pa | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO763 Re p (ahlv100a VALE_REFE) | 6.0237 Pa | 6.0222 | -0.03% | 0.1% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO763 Re p (ahlv100a VALE_CALC) | 6.0222 Pa | 6.0222 | -0.00% | 0.0001% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO763 Im p (ahlv100a VALE_REFE) | 1.6387 Pa | 1.6441 | +0.33% | 0.33% | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO763 Im p (ahlv100a VALE_CALC) | 1.6441 Pa | 1.6441 | +0.00% | 6.24256e-06 Pa | OK |
| AH-04 | ahlv100a harmonisch nagebouwd (500 Hz), hex20 15x2x2 | NO1 spl + 3,0103 dB = ahlv100a DB | 109.89 dB | 109.89 | -0.00% | 0.01 dB | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f2 (ahlv100a mode 1, VALE_CALC) | 171.5 Hz | 171.5 | -0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f3 (ahlv100a mode 2, VALE_CALC) | 343.01 Hz | 343.01 | +0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f4 (ahlv100a mode 3, VALE_CALC) | 514.55 Hz | 514.55 | +0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f5 (ahlv100a mode 4, VALE_CALC) | 686.23 Hz | 686.23 | +0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f6 (ahlv100a mode 5, VALE_CALC) | 858.18 Hz | 858.18 | +0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f7 (ahlv100a mode 6, VALE_CALC) | 860.72 Hz | 860.72 | -0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f8 (ahlv100a mode 7, VALE_CALC) | 877.64 Hz | 877.64 | -0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f9 (ahlv100a mode 8, VALE_CALC) | 926.57 Hz | 926.57 | -0.00% | 0.001% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f2 (ahlv100a mode 1, VALE_REFE) | 171.5 Hz | 171.5 | +0.00% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f3 (ahlv100a mode 2, VALE_REFE) | 343 Hz | 343.01 | +0.00% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f4 (ahlv100a mode 3, VALE_REFE) | 514.5 Hz | 514.55 | +0.01% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f5 (ahlv100a mode 4, VALE_REFE) | 686 Hz | 686.23 | +0.03% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f6 (ahlv100a mode 5, VALE_REFE) | 857.5 Hz | 858.18 | +0.08% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f7 (ahlv100a mode 6, VALE_REFE) | 857.5 Hz | 860.72 | +0.38% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f8 (ahlv100a mode 7, VALE_REFE) | 874.48 Hz | 877.64 | +0.36% | 1% | OK |
| AH-05 | ahlv100a holtemodes nagebouwd, hex20 15x2x2 | f9 (ahlv100a mode 8, VALE_REFE) | 923.56 Hz | 926.57 | +0.33% | 1% | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | f=100 Hz: |p(0)| | 0.23238 Pa | 0.23238 | -0.00% | 1% | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | f=100 Hz: |p(L)| | 0.41996 Pa | 0.41996 | -0.00% | 1% | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | f=100 Hz: max|P - P_exact| / max|P_exact| | 0 - | 1.1990e-07 | 1.1990e-07 | 0.01 - | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | f=250 Hz: |p(0)| | 0.20725 Pa | 0.20725 | -0.00% | 1% | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | f=250 Hz: |p(L)| | 0.40931 Pa | 0.40931 | -0.00% | 1% | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | f=250 Hz: max|P - P_exact| / max|P_exact| | 0 - | 6.9140e-06 | 6.9140e-06 | 0.01 - | OK |
| AH-06 | Buis met impedantie Z = 2 rho c op x = L (Mecway impedance), hex20 20x1x1 | max|p| / min|p| langs de as (250 Hz, staande golf) | 2 - | 1.9936 | -0.32% | 1% | OK |
| AH-07 | Opgelegde druk 2 Pa op x = 0 (fluid pressure), absorberend einde, hex20 20x1x1 | f=170 Hz: max|p| (lambda = 2 m) | 2 Pa | 2 | +0.00% | 1% | OK |
| AH-07 | Opgelegde druk 2 Pa op x = 0 (fluid pressure), absorberend einde, hex20 20x1x1 | f=170 Hz: min|p| | 2 Pa | 2 | -0.00% | 1% | OK |
| AH-07 | Opgelegde druk 2 Pa op x = 0 (fluid pressure), absorberend einde, hex20 20x1x1 | f=170 Hz: faseval over L | 3.1416 rad | 3.1416 | -0.00% | 1% | OK |
| AH-07 | Opgelegde druk 2 Pa op x = 0 (fluid pressure), absorberend einde, hex20 20x1x1 | f=500 Hz: max|p| (lambda = 0.68 m) | 2 Pa | 2 | +0.00% | 1% | OK |
| AH-07 | Opgelegde druk 2 Pa op x = 0 (fluid pressure), absorberend einde, hex20 20x1x1 | f=500 Hz: min|p| | 2 Pa | 1.9999 | -0.01% | 1% | OK |
| AH-07 | Opgelegde druk 2 Pa op x = 0 (fluid pressure), absorberend einde, hex20 20x1x1 | f=500 Hz: faseval over L | 9.24 rad | 9.2397 | -0.00% | 1% | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=200 Hz: Im p(0) = rho c v | 0.816 Pa | 0.816 | -0.00% | 1% | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=500 Hz: Im p(0) = rho c v | 0.816 Pa | 0.816 | -0.00% | 1% | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=200 Hz: Re p(0) = 0 | 0 Pa | 5.9363e-07 | 5.9363e-07 | 0.00816 Pa | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=500 Hz: Re p(0) = 0 | 0 Pa | -9.5432e-06 | -9.5432e-06 | 0.00816 Pa | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=200 Hz: microfoon Eind SPL | 89.203 dB | 89.203 | -0.00% | 0.05 dB | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=500 Hz: microfoon Eind SPL | 89.203 dB | 89.203 | -0.00% | 0.05 dB | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=200 Hz: microfoon Midden SPL (8 knopen) | 89.203 dB | 89.203 | -0.00% | 0.05 dB | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=500 Hz: microfoon Midden SPL (8 knopen) | 89.203 dB | 89.203 | -0.00% | 0.05 dB | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=200 Hz: microfoon Eind fase | 0 graden | 1.4988e-04 | 1.4988e-04 | 1 graden | OK |
| AH-08 | #ASTER-BRON 2 mm/s met fase 90 graden, microfoons, hex20 20x1x1 | f=500 Hz: microfoon Eind fase | 0 graden | 0.016897 | 0.016897 | 1 graden | OK |

## Akoestiek impedantie

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f (n=0, niet-oscillerend) | 0 Hz | 0 | 0 | 1e-06 Hz | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay rate (n=0) | 70.347 1/s | 70.347 | -0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f (n=1) | 170 Hz | 170 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay rate (n=1) | 70.347 1/s | 70.347 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f (n=2) | 340 Hz | 340 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay rate (n=2) | 70.347 1/s | 70.349 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f (n=3) | 510 Hz | 510.02 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay rate (n=3) | 70.347 1/s | 70.356 | +0.01% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f (n=4) | 680 Hz | 680.07 | +0.01% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay rate (n=4) | 70.347 1/s | 70.376 | +0.04% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f (n=5) | 850 Hz | 850.22 | +0.03% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay rate (n=5) | 70.347 1/s | 70.415 | +0.10% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | |P(L)/P(0)| (170 Hz) | 1.0215 - | 1.0215 | -0.00% | 0.1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | fase P(L)/P(0) t.o.v. analytisch (170 Hz) | 0 graden | -2.7689e-07 | -2.7689e-07 | 0.05 graden | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay 70.3469 1/s t.o.v. Mecway | 70.347 1/s | 70.347 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f 170 Hz t.o.v. Mecway | 170 Hz | 170 | -0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay 70.347 1/s t.o.v. Mecway | 70.347 1/s | 70.347 | -0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f 340.002 Hz t.o.v. Mecway | 340 Hz | 340 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay 70.3488 1/s t.o.v. Mecway | 70.349 1/s | 70.349 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f 510.017 Hz t.o.v. Mecway | 510.02 Hz | 510.02 | -0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay 70.3562 1/s t.o.v. Mecway | 70.356 1/s | 70.356 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f 680.072 Hz t.o.v. Mecway | 680.07 Hz | 680.07 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay 70.3758 1/s t.o.v. Mecway | 70.376 1/s | 70.376 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | f 850.217 Hz t.o.v. Mecway | 850.22 Hz | 850.22 | +0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | decay 70.4154 1/s t.o.v. Mecway | 70.415 1/s | 70.415 | -0.00% | 1% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (170 Hz) | 1.0215 - | 1.0215 | -0.00% | 0.01% | OK |
| AI-01 | Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (170 Hz) | 0 graden | 2.4165e-11 | 2.4165e-11 | 0.01 graden | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f (n=1) | 85 Hz | 85 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay rate (n=1) | 182.35 1/s | 182.35 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f (n=2) | 255 Hz | 255 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay rate (n=2) | 182.35 1/s | 182.35 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f (n=3) | 425 Hz | 425.01 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay rate (n=3) | 182.35 1/s | 182.37 | +0.01% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f (n=4) | 595 Hz | 595.04 | +0.01% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay rate (n=4) | 182.35 1/s | 182.42 | +0.04% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f (n=5) | 765 Hz | 765.13 | +0.02% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay rate (n=5) | 182.35 1/s | 182.54 | +0.11% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | |P(L)/P(0)| (85 Hz) | 0.5624 - | 0.5624 | +0.00% | 0.1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | fase P(L)/P(0) t.o.v. analytisch (85 Hz) | 0 graden | 2.4060e-06 | 2.4060e-06 | 0.05 graden | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f 85 Hz t.o.v. Mecway | 85 Hz | 85 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay 182.348 1/s t.o.v. Mecway | 182.35 1/s | 182.35 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f 255 Hz t.o.v. Mecway | 255 Hz | 255 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay 182.351 1/s t.o.v. Mecway | 182.35 1/s | 182.35 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f 425.006 Hz t.o.v. Mecway | 425.01 Hz | 425.01 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay 182.367 1/s t.o.v. Mecway | 182.37 1/s | 182.37 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f 595.036 Hz t.o.v. Mecway | 595.04 Hz | 595.04 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay 182.419 1/s t.o.v. Mecway | 182.42 1/s | 182.42 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | f 765.126 Hz t.o.v. Mecway | 765.13 Hz | 765.13 | -0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | decay 182.54 1/s t.o.v. Mecway | 182.54 1/s | 182.54 | +0.00% | 1% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (85 Hz) | 0.5624 - | 0.5624 | -0.00% | 0.01% | OK |
| AI-02 | Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (85 Hz) | 0 graden | 7.7830e-11 | 7.7830e-11 | 0.01 graden | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f (n=1) | 170 Hz | 170 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay rate (n=1) | 1.3872e-04 1/s | 1.3872e-04 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f (n=2) | 340 Hz | 340 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay rate (n=2) | 1.3872e-04 1/s | 1.3872e-04 | -0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f (n=3) | 510 Hz | 510.02 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay rate (n=3) | 1.3872e-04 1/s | 1.3871e-04 | -0.01% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f (n=4) | 680 Hz | 680.07 | +0.01% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay rate (n=4) | 1.3872e-04 1/s | 1.3884e-04 | +0.09% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | |P(L)/P(0)| (170 Hz) | 1 - | 1 | -0.00% | 0.1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | fase P(L)/P(0) t.o.v. analytisch (170 Hz) | 0 graden | -1.5930e-11 | -1.5930e-11 | 0.05 graden | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f2 = AK-01 (Mecway, harde wanden) | 170 Hz | 170 | -0.00% | 0.0001% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f 170 Hz t.o.v. Mecway | 170 Hz | 170 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay 0.00013872 1/s t.o.v. Mecway | 1.3872e-04 1/s | 1.3872e-04 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f 340.002 Hz t.o.v. Mecway | 340 Hz | 340 | -0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay 0.000138724 1/s t.o.v. Mecway | 1.3872e-04 1/s | 1.3872e-04 | -0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f 510.017 Hz t.o.v. Mecway | 510.02 Hz | 510.02 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay 0.000138739 1/s t.o.v. Mecway | 1.3874e-04 1/s | 1.3871e-04 | -0.02% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f 680.072 Hz t.o.v. Mecway | 680.07 Hz | 680.07 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay 0.000138777 1/s t.o.v. Mecway | 1.3878e-04 1/s | 1.3884e-04 | +0.04% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | f 850.218 Hz t.o.v. Mecway | 850.22 Hz | 850.22 | +0.00% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | decay 0.000138856 1/s t.o.v. Mecway | 1.3886e-04 1/s | 1.3892e-04 | +0.04% | 1% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (170 Hz) | 1 - | 1 | -0.00% | 0.01% | OK |
| AI-03 | Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde wand), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (170 Hz) | 0 graden | -4.5910e-11 | -4.5910e-11 | 0.01 graden | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | decay rate >= 10 x die bij Z = 2000 (geen resonantie) | 1 - | 1 | +0.00% | 1e-12 - | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | f 130.113 Hz t.o.v. Mecway | 130.11 Hz | 130.11 | +0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | decay 2105.1 1/s t.o.v. Mecway | 2105.1 1/s | 2105.1 | +0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | f 265.345 Hz t.o.v. Mecway | 265.35 Hz | 265.35 | -0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | decay 2006.12 1/s t.o.v. Mecway | 2006.1 1/s | 2006.1 | +0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | f 408.683 Hz t.o.v. Mecway | 408.68 Hz | 408.68 | -0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | decay 1870.53 1/s t.o.v. Mecway | 1870.5 1/s | 1870.5 | +0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | f 560.037 Hz t.o.v. Mecway | 560.04 Hz | 560.04 | -0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | decay 1725.64 1/s t.o.v. Mecway | 1725.6 1/s | 1725.6 | +0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | f 717.508 Hz t.o.v. Mecway | 717.51 Hz | 717.51 | -0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | decay 1588.07 1/s t.o.v. Mecway | 1588.1 1/s | 1588.1 | -0.00% | 1% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (130.113 Hz) | 244.29 - | 244.29 | +0.00% | 0.01% | OK |
| AI-04 | Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (130.113 Hz) | 0 graden | -8.4490e-07 | -8.4490e-07 | 0.01 graden | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f (n=1) | 165.48 Hz | 165.48 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=1) | 55.601 1/s | 55.602 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f (n=2) | 335.48 Hz | 335.48 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=2) | 55.601 1/s | 55.603 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f (n=3) | 505.48 Hz | 505.49 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=3) | 55.601 1/s | 55.609 | +0.01% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f (n=4) | 675.48 Hz | 675.55 | +0.01% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=4) | 55.601 1/s | 55.624 | +0.04% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f (n=5) | 845.48 Hz | 845.69 | +0.03% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=5) | 55.601 1/s | 55.655 | +0.10% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | |P(L)/P(0)| (165.5 Hz) | 1.01 - | 1.01 | -0.00% | 0.1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | fase P(L)/P(0) t.o.v. analytisch (165.5 Hz) | 0 graden | -6.8506e-07 | -6.8506e-07 | 0.05 graden | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f 165.475 Hz t.o.v. Mecway | 165.48 Hz | 165.48 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay 55.6016 1/s t.o.v. Mecway | 55.602 1/s | 55.602 | -0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f 335.477 Hz t.o.v. Mecway | 335.48 Hz | 335.48 | -0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay 55.6029 1/s t.o.v. Mecway | 55.603 1/s | 55.603 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f 505.492 Hz t.o.v. Mecway | 505.49 Hz | 505.49 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay 55.6087 1/s t.o.v. Mecway | 55.609 1/s | 55.609 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f 675.545 Hz t.o.v. Mecway | 675.55 Hz | 675.55 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay 55.624 1/s t.o.v. Mecway | 55.624 1/s | 55.624 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | f 845.688 Hz t.o.v. Mecway | 845.69 Hz | 845.69 | +0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | decay 55.6553 1/s t.o.v. Mecway | 55.655 1/s | 55.655 | -0.00% | 1% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (165.475 Hz) | 1.01 - | 1.01 | +0.00% | 0.01% | OK |
| AI-05 | Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (165.475 Hz) | 0 graden | -9.6252e-11 | -9.6252e-11 | 0.01 graden | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f (n=0) | 6.6013 Hz | 6.6013 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=0) | 13.674 1/s | 13.674 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f (n=1) | 176.6 Hz | 176.6 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=1) | 13.674 1/s | 13.674 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f (n=2) | 346.6 Hz | 346.6 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=2) | 13.674 1/s | 13.675 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f (n=3) | 516.6 Hz | 516.62 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=3) | 13.674 1/s | 13.676 | +0.01% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f (n=4) | 686.6 Hz | 686.68 | +0.01% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=4) | 13.674 1/s | 13.68 | +0.04% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f (n=5) | 856.6 Hz | 856.83 | +0.03% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay rate (n=5) | 13.674 1/s | 13.688 | +0.10% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | |P(L)/P(0)| (6.601 Hz) | 0.99338 - | 0.99338 | -0.00% | 0.1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | fase P(L)/P(0) t.o.v. analytisch (6.601 Hz) | 0 graden | 1.0687e-12 | 1.0687e-12 | 0.05 graden | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f 6.60133 Hz t.o.v. Mecway | 6.6013 Hz | 6.6013 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay 13.6743 1/s t.o.v. Mecway | 13.674 1/s | 13.674 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f 176.601 Hz t.o.v. Mecway | 176.6 Hz | 176.6 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay 13.6743 1/s t.o.v. Mecway | 13.674 1/s | 13.674 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f 346.604 Hz t.o.v. Mecway | 346.6 Hz | 346.6 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay 13.6747 1/s t.o.v. Mecway | 13.675 1/s | 13.675 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f 516.619 Hz t.o.v. Mecway | 516.62 Hz | 516.62 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay 13.6762 1/s t.o.v. Mecway | 13.676 1/s | 13.676 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f 686.676 Hz t.o.v. Mecway | 686.68 Hz | 686.68 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay 13.6801 1/s t.o.v. Mecway | 13.68 1/s | 13.68 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | f 856.826 Hz t.o.v. Mecway | 856.83 Hz | 856.83 | -0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | decay 13.6881 1/s t.o.v. Mecway | 13.688 1/s | 13.688 | +0.00% | 1% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (176.601 Hz) | 0.99338 - | 0.99338 | -0.00% | 0.01% | OK |
| AI-06 | Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (176.601 Hz) | 0 graden | 2.6214e-11 | 2.6214e-11 | 0.01 graden | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f (n=0) | 20.962 Hz | 20.962 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay rate (n=0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f (n=1) | 190.96 Hz | 190.96 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay rate (n=1) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f (n=2) | 360.96 Hz | 360.97 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay rate (n=2) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f (n=3) | 530.96 Hz | 530.98 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay rate (n=3) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f (n=4) | 700.96 Hz | 701.04 | +0.01% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay rate (n=4) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f (n=5) | 870.96 Hz | 871.2 | +0.03% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay rate (n=5) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | |P(L)/P(0)| (20.96 Hz) | 0.9259 - | 0.9259 | +0.00% | 0.1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | fase P(L)/P(0) t.o.v. analytisch (20.96 Hz) | 0 graden | 2.2698e-13 | 2.2698e-13 | 0.05 graden | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f 20.9624 Hz t.o.v. Mecway | 20.962 Hz | 20.962 | -0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay (f 20.9624 Hz) t.o.v. Mecway (0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f 190.962 Hz t.o.v. Mecway | 190.96 Hz | 190.96 | -0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay (f 190.962 Hz) t.o.v. Mecway (0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f 360.965 Hz t.o.v. Mecway | 360.97 Hz | 360.97 | -0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay (f 360.965 Hz) t.o.v. Mecway (0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f 530.983 Hz t.o.v. Mecway | 530.98 Hz | 530.98 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay (f 530.983 Hz) t.o.v. Mecway (0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f 701.044 Hz t.o.v. Mecway | 701.04 Hz | 701.04 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay (f 701.044 Hz) t.o.v. Mecway (0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | f 871.202 Hz t.o.v. Mecway | 871.2 Hz | 871.2 | +0.00% | 1% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | decay (f 871.202 Hz) t.o.v. Mecway (0) | 0 1/s | 0 | 0 | 1e-06 1/s | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (190.962 Hz) | 0.9259 - | 0.9259 | +0.00% | 0.01% | OK |
| AI-07 | Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (190.962 Hz) | 0 graden | -3.5714e-10 | -3.5714e-10 | 0.01 graden | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f (n=1) | 85 Hz | 85 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay rate (n=1) | 70.347 1/s | 70.347 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f (n=2) | 255 Hz | 255 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay rate (n=2) | 70.347 1/s | 70.348 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f (n=3) | 425 Hz | 425.01 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay rate (n=3) | 70.347 1/s | 70.351 | +0.01% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f (n=4) | 595 Hz | 595.04 | +0.01% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay rate (n=4) | 70.347 1/s | 70.364 | +0.02% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f (n=5) | 765 Hz | 765.13 | +0.02% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay rate (n=5) | 70.347 1/s | 70.393 | +0.06% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f (n=6) | 935 Hz | 935.35 | +0.04% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay rate (n=6) | 70.347 1/s | 70.446 | +0.14% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f 85 Hz t.o.v. Mecway | 85 Hz | 85 | -0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay 70.3469 1/s t.o.v. Mecway | 70.347 1/s | 70.347 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f 255.001 Hz t.o.v. Mecway | 255 Hz | 255 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay 70.3475 1/s t.o.v. Mecway | 70.348 1/s | 70.348 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f 425.007 Hz t.o.v. Mecway | 425.01 Hz | 425.01 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay 70.3515 1/s t.o.v. Mecway | 70.351 1/s | 70.351 | -0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f 595.037 Hz t.o.v. Mecway | 595.04 Hz | 595.04 | -0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay 70.364 1/s t.o.v. Mecway | 70.364 1/s | 70.364 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f 765.129 Hz t.o.v. Mecway | 765.13 Hz | 765.13 | -0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay 70.3925 1/s t.o.v. Mecway | 70.393 1/s | 70.393 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | f 935.348 Hz t.o.v. Mecway | 935.35 Hz | 935.35 | +0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | decay 70.4457 1/s t.o.v. Mecway | 70.446 1/s | 70.446 | -0.00% | 1% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | |P(B)/P(A)| t.o.v. Mecway (255.001 Hz) | 1.4293 - | 1.4293 | -0.00% | 0.01% | OK |
| AI-08 | Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1 | fase P(B)/P(A) t.o.v. Mecway (255.001 Hz) | 0 graden | -9.5634e-12 | -9.5634e-12 | 0.01 graden | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | f (n=0, niet-oscillerend) | 0 Hz | 0 | 0 | 1e-06 Hz | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | decay rate (n=0) | 70.347 1/s | 70.346 | -0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | f (n=1) | 170 Hz | 170.17 | +0.10% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | decay rate (n=1) | 70.347 1/s | 70.638 | +0.41% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | |P(L)/P(0)| (170 Hz) | 1.0215 - | 1.0215 | +0.00% | 0.1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | fase P(L)/P(0) t.o.v. analytisch (170 Hz) | 0 graden | 3.4043e-04 | 3.4043e-04 | 0.05 graden | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | f 170.171 Hz t.o.v. Mecway | 170.17 Hz | 170.17 | +0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | decay 70.6383 1/s t.o.v. Mecway | 70.638 1/s | 70.638 | +0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | f 341.392 Hz t.o.v. Mecway | 341.39 Hz | 341.39 | +0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | decay 71.5215 1/s t.o.v. Mecway | 71.522 1/s | 71.522 | -0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | f 514.719 Hz t.o.v. Mecway | 514.72 Hz | 514.72 | +0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | decay 73.0185 1/s t.o.v. Mecway | 73.018 1/s | 73.018 | -0.00% | 1% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | |P(B)/P(A)| t.o.v. Mecway (170.171 Hz) | 1.0215 - | 1.0215 | +0.00% | 0.01% | OK |
| AI-09 | Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte oplossing, < 300 vrijheidsgraden) | fase P(B)/P(A) t.o.v. Mecway (170.171 Hz) | 0 graden | 3.5333e-07 | 3.5333e-07 | 0.01 graden | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 139.306 Hz t.o.v. Mecway | 139.31 Hz | 139.31 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 401.529 1/s t.o.v. Mecway | 401.53 1/s | 401.53 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 218.674 Hz t.o.v. Mecway | 218.67 Hz | 218.67 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 442.508 1/s t.o.v. Mecway | 442.51 1/s | 442.51 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 276.489 Hz t.o.v. Mecway | 276.49 Hz | 276.49 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 466.373 1/s t.o.v. Mecway | 466.37 1/s | 466.37 | +0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 323.558 Hz t.o.v. Mecway | 323.56 Hz | 323.56 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 483.686 1/s t.o.v. Mecway | 483.69 1/s | 483.69 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 376.849 Hz t.o.v. Mecway | 376.85 Hz | 376.85 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 828.951 1/s t.o.v. Mecway | 828.95 1/s | 828.95 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 408.14 Hz t.o.v. Mecway | 408.14 Hz | 408.14 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 510.594 1/s t.o.v. Mecway | 510.59 1/s | 510.59 | +0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 411.819 Hz t.o.v. Mecway | 411.82 Hz | 411.82 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 838.108 1/s t.o.v. Mecway | 838.11 1/s | 838.11 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 445.385 Hz t.o.v. Mecway | 445.38 Hz | 445.38 | +0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 846.317 1/s t.o.v. Mecway | 846.32 1/s | 846.32 | -0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | f 482.972 Hz t.o.v. Mecway | 482.97 Hz | 482.97 | +0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | decay 528.989 1/s t.o.v. Mecway | 528.99 1/s | 528.99 | +0.00% | 1% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | |P(B)/P(A)| t.o.v. Mecway (139.306 Hz) | 1.2102 - | 1.2102 | -0.00% | 0.01% | OK |
| AI-10 | Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 en plafond Z = 600 - 300i Pa.s/m | fase P(B)/P(A) t.o.v. Mecway (139.306 Hz) | 0 graden | 7.7733e-11 | 7.7733e-11 | 0.01 graden | OK |

## Akoestiek

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f1 (constante druk) | 0 Hz | 2.8795e-05 | 2.8795e-05 | 0.01 Hz | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f2 | 170 Hz | 170 | +0.00% | 0.5% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f3 | 340 Hz | 340 | +0.00% | 0.5% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f4 | 510 Hz | 510.02 | +0.00% | 0.5% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f5 | 680 Hz | 680.07 | +0.01% | 0.5% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | max|p| mode 1 = c / sqrt(V) | 3400 Pa | 3400 | +0.00% | 0.0001% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f2 t.o.v. Mecway | 170 Hz | 170 | -0.00% | 1% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f3 t.o.v. Mecway | 340 Hz | 340 | +0.00% | 1% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f4 t.o.v. Mecway | 510.02 Hz | 510.02 | -0.00% | 1% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | f5 t.o.v. Mecway | 680.07 Hz | 680.07 | -0.00% | 1% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | max|p| mode 1 t.o.v. Mecway | 3400 Pa | 3400 | -0.00% | 0.1% | OK |
| AK-01 | Buis gesloten-gesloten, hex20 20x1x1 | max|p| mode 2 t.o.v. Mecway | 4808.3 Pa | 4808.3 | -0.00% | 0.1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f1 | 85 Hz | 85 | +0.00% | 0.5% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f2 | 255 Hz | 255 | +0.00% | 0.5% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f3 | 425 Hz | 425.01 | +0.00% | 0.5% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f4 | 595 Hz | 595.04 | +0.01% | 0.5% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f5 | 765 Hz | 765.13 | +0.02% | 0.5% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f1 t.o.v. Mecway | 85 Hz | 85 | -0.00% | 1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f2 t.o.v. Mecway | 255 Hz | 255 | -0.00% | 1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f3 t.o.v. Mecway | 425.01 Hz | 425.01 | -0.00% | 1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f4 t.o.v. Mecway | 595.04 Hz | 595.04 | -0.00% | 1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | f5 t.o.v. Mecway | 765.13 Hz | 765.13 | -0.00% | 1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | max|p| mode 1 t.o.v. Mecway | 4808.3 Pa | 4808.3 | -0.00% | 0.1% | OK |
| AK-02 | Buis open-gesloten (p = 0 op x = L), hex20 20x1x1 | max|p| mode 2 t.o.v. Mecway | 4808.3 Pa | 4808.3 | +0.00% | 0.1% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f1 | 170 Hz | 170.03 | +0.02% | 0.5% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f2 | 340 Hz | 340.22 | +0.07% | 0.5% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f3 | 510 Hz | 510.76 | +0.15% | 0.5% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f4 | 680 Hz | 681.79 | +0.26% | 0.5% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f1 t.o.v. Mecway | 170.03 Hz | 170.03 | -0.00% | 1% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f2 t.o.v. Mecway | 340.22 Hz | 340.22 | +0.00% | 1% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f3 t.o.v. Mecway | 510.76 Hz | 510.76 | +0.00% | 1% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | f4 t.o.v. Mecway | 681.79 Hz | 681.79 | +0.00% | 1% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | max|p| mode 1 t.o.v. Mecway | 4809.9 Pa | 4809.9 | -0.00% | 0.1% | OK |
| AK-03 | Buis open-open (p = 0 op beide eindvlakken), hex8 50x1x1 | max|p| mode 2 t.o.v. Mecway | 4805.2 Pa | 4805.2 | -0.00% | 0.1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f1 (constante druk) | 0 Hz | 1.2753e-05 | 1.2753e-05 | 0.01 Hz | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f2 mode 100 | 170 Hz | 170 | +0.00% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f3 mode 010 | 242.86 Hz | 242.86 | +0.00% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f4 mode 110 | 296.44 Hz | 296.45 | +0.00% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f5 mode 200 | 340 Hz | 340.04 | +0.01% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f6 mode 210 | 417.83 Hz | 417.86 | +0.01% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f7 mode 001 | 425 Hz | 425.11 | +0.03% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f8 mode 101 | 457.74 Hz | 457.84 | +0.02% | 0.5% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f2 t.o.v. Mecway | 170 Hz | 170 | +0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f3 t.o.v. Mecway | 242.86 Hz | 242.86 | -0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f4 t.o.v. Mecway | 296.45 Hz | 296.45 | -0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f5 t.o.v. Mecway | 340.04 Hz | 340.04 | -0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f6 t.o.v. Mecway | 417.86 Hz | 417.86 | -0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f7 t.o.v. Mecway | 425.11 Hz | 425.11 | -0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | f8 t.o.v. Mecway | 457.84 Hz | 457.84 | -0.00% | 1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | max|p| mode 1 t.o.v. Mecway | 642.54 Pa | 642.54 | -0.00% | 0.1% | OK |
| AK-04 | Rechthoekige ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4 | max|p| mode 2 t.o.v. Mecway | 908.7 Pa | 908.7 | -0.00% | 0.1% | OK |
| AK-05 | Buis van twee media (c = 340 / 680 m/s), hex20 20x1x1 | f1 (constante druk) | 0 Hz | 3.9557e-05 | 3.9557e-05 | 0.01 Hz | OK |
| AK-05 | Buis van twee media (c = 340 / 680 m/s), hex20 20x1x1 | f2 | 248.98 Hz | 248.98 | +0.00% | 0.5% | OK |
| AK-05 | Buis van twee media (c = 340 / 680 m/s), hex20 20x1x1 | f3 | 431.02 Hz | 431.03 | +0.00% | 0.5% | OK |
| AK-05 | Buis van twee media (c = 340 / 680 m/s), hex20 20x1x1 | f4 | 680 Hz | 680.06 | +0.01% | 0.5% | OK |
| AK-05 | Buis van twee media (c = 340 / 680 m/s), hex20 20x1x1 | f5 | 928.98 Hz | 929.2 | +0.02% | 0.5% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f1 (constante druk) | 0 Hz | -1.5787e-05 | -1.5787e-05 | 0.01 Hz | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f2 | 170 Hz | 170.04 | +0.02% | 0.5% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f3 | 340 Hz | 340.32 | +0.09% | 0.5% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f4 | 510 Hz | 511.05 | +0.21% | 0.5% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f5 | 680 Hz | 682.42 | +0.36% | 0.5% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f2 t.o.v. Mecway | 170.04 Hz | 170.04 | -0.00% | 1% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f3 t.o.v. Mecway | 340.32 Hz | 340.32 | -0.00% | 1% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f4 t.o.v. Mecway | 511.05 Hz | 511.05 | -0.00% | 1% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | f5 t.o.v. Mecway | 682.42 Hz | 682.42 | -0.00% | 1% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | max|p| mode 1 t.o.v. Mecway | 3400 Pa | 3400 | -0.00% | 0.1% | OK |
| AK-06 | Buis gesloten-gesloten, wedge6 (40 hex8-blokken gesplitst) | max|p| mode 2 t.o.v. Mecway | 4820 Pa | 4820 | -0.00% | 0.1% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f1 (constante druk) | 0 Hz | 3.5732e-05 | 3.5732e-05 | 0.01 Hz | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f2 | 170 Hz | 170.04 | +0.02% | 0.5% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f3 | 340 Hz | 340.3 | +0.09% | 0.5% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f4 | 510 Hz | 510.96 | +0.19% | 0.5% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f5 | 680 Hz | 682.14 | +0.32% | 0.5% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f2 t.o.v. Mecway | 170.04 Hz | 170.04 | +0.00% | 1% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f3 t.o.v. Mecway | 340.3 Hz | 340.3 | -0.00% | 1% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f4 t.o.v. Mecway | 510.96 Hz | 510.96 | +0.00% | 1% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | f5 t.o.v. Mecway | 682.14 Hz | 682.14 | -0.00% | 1% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | max|p| mode 1 t.o.v. Mecway | 3400 Pa | 3400 | +0.00% | 0.1% | OK |
| AK-07 | Buis gesloten-gesloten, tet4 (40 hex8-blokken gesplitst) | max|p| mode 2 t.o.v. Mecway | 4826.3 Pa | 4826.3 | +0.00% | 0.1% | OK |

## Breukmechanica

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| BR-01 | Middenscheur in een plaat, vlakke rek, beide lippen (hex20) | K_I CALC_G midden | 4.7014e+07 Pa.m^0.5 | 4.6967e+07 | -0.10% | 3% | OK |
| BR-01 | Middenscheur in een plaat, vlakke rek, beide lippen (hex20) | G CALC_G midden | 9578.2 J/m2 | 9539 | -0.41% | 3% | OK |
| BR-01 | Middenscheur in een plaat, vlakke rek, beide lippen (hex20) | G / (K_I^2/E') CALC_G midden | 1  | 0.99791 | -0.21% | 2% | OK |
| BR-01 | Middenscheur in een plaat, vlakke rek, beide lippen (hex20) | K_I POST_K1_K2_K3 midden | 4.7014e+07 Pa.m^0.5 | 4.5376e+07 | -3.49% | 5% | OK |
| BR-01 | Middenscheur in een plaat, vlakke rek, beide lippen (hex20) | spreiding K_I langs het front | 0  | 1.6046e-05 | 1.6046e-05 | 0.01  | OK |
| BR-01 | Middenscheur in een plaat, vlakke rek, beide lippen (hex20) | K_II midden | 0 Pa.m^0.5 | -1.5000e-07 | -1.5000e-07 | 470143 Pa.m^0.5 | OK |
| BR-02 | Middenscheur, vlakke rek, kwartmodel met symmetrie op het ligament (SYME='OUI') | K_I CALC_G midden | 4.7014e+07 Pa.m^0.5 | 4.6967e+07 | -0.10% | 3% | OK |
| BR-02 | Middenscheur, vlakke rek, kwartmodel met symmetrie op het ligament (SYME='OUI') | G CALC_G midden | 9578.2 J/m2 | 9539 | -0.41% | 3% | OK |
| BR-02 | Middenscheur, vlakke rek, kwartmodel met symmetrie op het ligament (SYME='OUI') | G / (K_I^2/E') CALC_G midden | 1  | 0.99791 | -0.21% | 2% | OK |
| BR-02 | Middenscheur, vlakke rek, kwartmodel met symmetrie op het ligament (SYME='OUI') | K_I POST_K1_K2_K3 midden | 4.7014e+07 Pa.m^0.5 | 4.5376e+07 | -3.49% | 5% | OK |
| BR-03 | Middenscheur in een dikke plaat (B = 4a) met vrije zijvlakken | K_I CALC_G middenvlak | 4.7014e+07 Pa.m^0.5 | 4.7337e+07 | +0.69% | 3% | OK |
| BR-03 | Middenscheur in een dikke plaat (B = 4a) met vrije zijvlakken | G CALC_G middenvlak | 9578.2 J/m2 | 9690.4 | +1.17% | 3% | OK |
| BR-03 | Middenscheur in een dikke plaat (B = 4a) met vrije zijvlakken | G / (K_I^2/E') CALC_G middenvlak | 1  | 0.99798 | -0.20% | 2% | OK |
| BR-03 | Middenscheur in een dikke plaat (B = 4a) met vrije zijvlakken | K_I POST_K1_K2_K3 middenvlak | 4.7014e+07 Pa.m^0.5 | 4.5706e+07 | -2.78% | 5% | OK |
| BR-03 | Middenscheur in een dikke plaat (B = 4a) met vrije zijvlakken | K_I CALC_G op a van het oppervlak | 4.7014e+07 Pa.m^0.5 | 4.8033e+07 | +2.17% | 3% | OK |
| BR-04 | Code-Aster-testcase forma07a (schijfvormige scheur) | K1 MAX POST_K1_K2_K3 | 1.6070e+06 Pa.m^0.5 | 1.6070e+06 | +0.00% | 1% | OK |
| BR-04 | Code-Aster-testcase forma07a (schijfvormige scheur) | K1 MAX POST_K1_K2_K3 (analytisch) | 1.5957e+06 Pa.m^0.5 | 1.6070e+06 | +0.71% | 0.8% | OK |
| BR-04 | Code-Aster-testcase forma07a (schijfvormige scheur) | K_I CALC_G midden (FORM_FISS CERCLE) | 1.5957e+06 Pa.m^0.5 | 1.5833e+06 | -0.78% | 1% | OK |
| BR-04 | Code-Aster-testcase forma07a (schijfvormige scheur) | G CALC_G midden | 11.586 J/m2 | 11.684 | +0.84% | 1.5% | OK |
| BR-05 | Middenscheur, vlakke rek, lineaire elementen (hex8, 8 over de dikte) | K_I CALC_G midden | 4.7014e+07 Pa.m^0.5 | 4.6700e+07 | -0.67% | 3% | OK |
| BR-05 | Middenscheur, vlakke rek, lineaire elementen (hex8, 8 over de dikte) | G CALC_G midden | 9578.2 J/m2 | 9391.3 | -1.95% | 3% | OK |
| BR-05 | Middenscheur, vlakke rek, lineaire elementen (hex8, 8 over de dikte) | G / (K_I^2/E') CALC_G midden | 1  | 0.99373 | -0.63% | 2% | OK |
| BR-06 | Middenscheur over de volle breedte: twee fronten als twee scheuren (_L, _R) | K_I CALC_G midden _L | 4.7014e+07 Pa.m^0.5 | 4.6967e+07 | -0.10% | 3% | OK |
| BR-06 | Middenscheur over de volle breedte: twee fronten als twee scheuren (_L, _R) | K_I CALC_G midden _R | 4.7014e+07 Pa.m^0.5 | 4.6967e+07 | -0.10% | 3% | OK |
| BR-06 | Middenscheur over de volle breedte: twee fronten als twee scheuren (_L, _R) | G CALC_G midden _L | 9578.2 J/m2 | 9539 | -0.41% | 3% | OK |
| BR-06 | Middenscheur over de volle breedte: twee fronten als twee scheuren (_L, _R) | G CALC_G midden _R | 9578.2 J/m2 | 9539 | -0.41% | 3% | OK |
| BR-07 | XFEM: middenscheur in een plaat (HALFVLAK), vlakke rek, hex8 | K_I CALC_G_XFEM midden | 4.7014e+07 Pa.m^0.5 | 4.6975e+07 | -0.08% | 5% | OK |
| BR-07 | XFEM: middenscheur in een plaat (HALFVLAK), vlakke rek, hex8 | G CALC_G_XFEM midden | 9578.2 J/m2 | 9561.2 | -0.18% | 5% | OK |
| BR-07 | XFEM: middenscheur in een plaat (HALFVLAK), vlakke rek, hex8 | K_I POST_K1_K2_K3 midden | 4.7014e+07 Pa.m^0.5 | 4.6903e+07 | -0.24% | 5% | OK |
| BR-07 | XFEM: middenscheur in een plaat (HALFVLAK), vlakke rek, hex8 | G / (K_I^2/E') CALC_G_XFEM midden | 1  | 0.99991 | -0.01% | 2% | OK |
| BR-07 | XFEM: middenscheur in een plaat (HALFVLAK), vlakke rek, hex8 | spreiding K_I langs het front | 0  | 0.0041414 | 0.0041414 | 0.01  | OK |
| BR-07 | XFEM: middenscheur in een plaat (HALFVLAK), vlakke rek, hex8 | opening boven- / onderlip (x = 0, t.o.v. x = b) | -1  | -0.99993 | +0.01% | 1% | OK |
| BR-08 | XFEM: middenscheur in een plaat, vlakke rek, hex20 | K_I CALC_G_XFEM midden | 4.7014e+07 Pa.m^0.5 | 4.7061e+07 | +0.10% | 5% | OK |
| BR-08 | XFEM: middenscheur in een plaat, vlakke rek, hex20 | G CALC_G_XFEM midden | 9578.2 J/m2 | 9594.7 | +0.17% | 5% | OK |
| BR-08 | XFEM: middenscheur in een plaat, vlakke rek, hex20 | K_I POST_K1_K2_K3 midden | 4.7014e+07 Pa.m^0.5 | 4.6954e+07 | -0.13% | 5% | OK |
| BR-08 | XFEM: middenscheur in een plaat, vlakke rek, hex20 | G / (K_I^2/E') CALC_G_XFEM midden | 1  | 0.99974 | -0.03% | 2% | OK |
| BR-09 | XFEM: middenscheur, scheurvlak door een knooplaag, front op elementgrenzen (hex8) | K_I CALC_G_XFEM midden | 4.7014e+07 Pa.m^0.5 | 4.6985e+07 | -0.06% | 5% | OK |
| BR-09 | XFEM: middenscheur, scheurvlak door een knooplaag, front op elementgrenzen (hex8) | G CALC_G_XFEM midden | 9578.2 J/m2 | 9573.5 | -0.05% | 5% | OK |
| BR-09 | XFEM: middenscheur, scheurvlak door een knooplaag, front op elementgrenzen (hex8) | K_I POST_K1_K2_K3 midden | 4.7014e+07 Pa.m^0.5 | 4.7548e+07 | +1.14% | 5% | OK |
| BR-09 | XFEM: middenscheur, scheurvlak door een knooplaag, front op elementgrenzen (hex8) | G / (K_I^2/E') CALC_G_XFEM midden | 1  | 1.0008 | +0.08% | 2% | OK |
| BR-10 | XFEM: cirkelvormige scheur (penny crack) in een blok onder trek, hex8 | K_I POST_K1_K2_K3 midden | 1.5958e+05 Pa.m^0.5 | 1.6219e+05 | +1.64% | 5% | OK |
| BR-10 | XFEM: cirkelvormige scheur (penny crack) in een blok onder trek, hex8 | K uit G (sqrt(G E')) midden | 1.5958e+05 Pa.m^0.5 | 1.6112e+05 | +0.97% | 5% | OK |
| BR-10 | XFEM: cirkelvormige scheur (penny crack) in een blok onder trek, hex8 | K_I CALC_G_XFEM midden (geen krommingscorrectie) | 1.5958e+05 Pa.m^0.5 | 1.6797e+05 | +5.26% | 5% | BEKEND (KNOWN_BUGS 83) |
| BR-10 | XFEM: cirkelvormige scheur (penny crack) in een blok onder trek, hex8 | opening van de scheur in het midden (displz) | 2.2069e-07 m | 2.2796e-07 | +3.29% | 5% | OK |
| BR-11 | XFEM: Code-Aster-testcase forma07b (schijfvormige scheur, levelset) | K1 MAX CALC_G_XFEM (LAGRANGE, 20 punten) | 1.6711e+06 Pa.m^0.5 | 1.6711e+06 | +0.00% | 1% | OK |
| BR-11 | XFEM: Code-Aster-testcase forma07b (schijfvormige scheur, levelset) | K1 MAX POST_K1_K2_K3 (20 punten) | 1.6075e+06 Pa.m^0.5 | 1.6075e+06 | +0.00% | 1% | OK |
| BR-11 | XFEM: Code-Aster-testcase forma07b (schijfvormige scheur, levelset) | K1 MAX POST_K1_K2_K3 (analytisch) | 1.5957e+06 Pa.m^0.5 | 1.6075e+06 | +0.74% | 1% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | K_I CALC_G_XFEM midden front 1 | 4.7014e+07 Pa.m^0.5 | 4.6974e+07 | -0.09% | 5% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | G CALC_G_XFEM midden front 1 | 9578.2 J/m2 | 9560.2 | -0.19% | 5% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | K_I POST_K1_K2_K3 midden front 1 | 4.7014e+07 Pa.m^0.5 | 4.6876e+07 | -0.29% | 5% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | G / (K_I^2/E') CALC_G_XFEM midden front 1 | 1  | 0.99984 | -0.02% | 2% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | K_I CALC_G_XFEM midden front 2 | 4.7014e+07 Pa.m^0.5 | 4.6974e+07 | -0.09% | 5% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | G CALC_G_XFEM midden front 2 | 9578.2 J/m2 | 9560.7 | -0.18% | 5% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | K_I POST_K1_K2_K3 midden front 2 | 4.7014e+07 Pa.m^0.5 | 4.6901e+07 | -0.24% | 5% | OK |
| BR-12 | XFEM: middenscheur over de volle breedte als RECHTHOEK (twee fronten), hex8 | G / (K_I^2/E') CALC_G_XFEM midden front 2 | 1  | 0.99991 | -0.01% | 2% | OK |
| BR-13 | XFEM: middenscheur uit een vlakselectie (XFEM_), scheurvlak op een knooplaag, hex8 | K_I CALC_G_XFEM midden | 4.7014e+07 Pa.m^0.5 | 4.6985e+07 | -0.06% | 5% | OK |
| BR-13 | XFEM: middenscheur uit een vlakselectie (XFEM_), scheurvlak op een knooplaag, hex8 | G CALC_G_XFEM midden | 9578.2 J/m2 | 9573.5 | -0.05% | 5% | OK |
| BR-13 | XFEM: middenscheur uit een vlakselectie (XFEM_), scheurvlak op een knooplaag, hex8 | K_I POST_K1_K2_K3 midden | 4.7014e+07 Pa.m^0.5 | 4.7548e+07 | +1.14% | 5% | OK |
| BR-13 | XFEM: middenscheur uit een vlakselectie (XFEM_), scheurvlak op een knooplaag, hex8 | G / (K_I^2/E') CALC_G_XFEM midden | 1  | 1.0008 | +0.08% | 2% | OK |
| BR-13 | XFEM: middenscheur uit een vlakselectie (XFEM_), scheurvlak op een knooplaag, hex8 | opening boven- / onderlip (x = 0, y = +-h, t.o.v. x = b) | -1  | -1.0004 | -0.04% | 1% | OK |
| BR-14 | XFEM: MED-bestand voor ParaView met het mesh dat de scheur volgt (med_export) | velden DEPL, SIGM_NOEU, SIEQ_NOEU in _xfem.rmed | 3  | 3 | +0.00% | 0  | OK |
| BR-14 | XFEM: MED-bestand voor ParaView met het mesh dat de scheur volgt (med_export) | groep Plaat in het MED-mesh | 1  | 1 | +0.00% | 0  | OK |
| BR-14 | XFEM: MED-bestand voor ParaView met het mesh dat de scheur volgt (med_export) | opening in het MED-bestand (dubbele knopen, x = 0) / opening Mecway (y = +-h/2) | 1  | 0.99608 | -0.39% | 3% | OK |

## Knik

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| BU-01 | Ingeklemde kolom, Euler-knik (20 balkelementen) | factor 1 | 10.363 - | 10.363 | +0.00% | 0.2% | OK |
| BU-01 | Ingeklemde kolom, Euler-knik (20 balkelementen) | factor 2 | 23.317 - | 23.317 | +0.00% | 0.2% | OK |
| BU-01 | Ingeklemde kolom, Euler-knik (20 balkelementen) | factor 3 | 93.268 - | 93.268 | +0.00% | 0.2% | OK |
| BU-01 | Ingeklemde kolom, Euler-knik (20 balkelementen) | tip Y mode 1 (phi^T K phi = 1) | 0.008844 m | 0.008844 | +0.00% | 0.5% | OK |
| BU-02 | Scharnierende kolom, Euler-knik (20 balkelementen) | factor 1 | 41.452 - | 41.452 | +0.00% | 0.2% | OK |
| BU-02 | Scharnierende kolom, Euler-knik (20 balkelementen) | factor 2 | 93.268 - | 93.268 | +0.00% | 0.2% | OK |
| BU-02 | Scharnierende kolom, Euler-knik (20 balkelementen) | factor 3 | 165.81 - | 165.81 | +0.00% | 0.2% | OK |
| BU-03-h20-n2 | Ingeklemde kolom, hex20 50x2x3 | factor 1 | 10.363 - | 10.384 | +0.20% | 2% | OK |
| BU-03-h20-n2 | Ingeklemde kolom, hex20 50x2x3 | factor 2 | 23.317 - | 23.344 | +0.12% | 2% | OK |
| BU-03-h20-n4 | Ingeklemde kolom, hex20 100x4x6 | factor 1 | 10.363 - | 10.377 | +0.13% | 0.5% | OK |
| BU-03-h20-n4 | Ingeklemde kolom, hex20 100x4x6 | factor 2 | 23.317 - | 23.33 | +0.06% | 0.5% | OK |
| BU-04-dkt-n16 | Vrij opgelegde plaat, eenzijdige druk, DKT 16x16 | factor 1 | 3.0368e+05 - | 3.0483e+05 | +0.38% | 2% | OK |
| BU-04-dkt-n16 | Vrij opgelegde plaat, eenzijdige druk, DKT 16x16 | factor 2 | 4.7450e+05 - | 4.7922e+05 | +0.99% | 2% | OK |
| BU-04-dkt-n32 | Vrij opgelegde plaat, eenzijdige druk, DKT 32x32 | factor 1 | 3.0368e+05 - | 3.0397e+05 | +0.09% | 0.5% | OK |
| BU-04-dkt-n32 | Vrij opgelegde plaat, eenzijdige druk, DKT 32x32 | factor 2 | 4.7450e+05 - | 4.7568e+05 | +0.25% | 0.5% | OK |
| BU-04-dkt-n8 | Vrij opgelegde plaat, eenzijdige druk, DKT 8x8 | factor 1 | 3.0368e+05 - | 3.0829e+05 | +1.52% | 8% | OK |
| BU-04-dkt-n8 | Vrij opgelegde plaat, eenzijdige druk, DKT 8x8 | factor 2 | 4.7450e+05 - | 4.9362e+05 | +4.03% | 8% | OK |
| BU-20 | Balkorientatie knik: langs X, Y vast, standaard (zwakke as) | factor 1 | 1.7272 - | 1.7272 | +0.00% | 0.2% | OK |
| BU-20 | Balkorientatie knik: langs X, Y vast, standaard (zwakke as) | factor 1 t.o.v. Mecway | 1.7272 - | 1.7272 | +0.00% | 0.01% | OK |
| BU-21 | Balkorientatie knik: langs X, Y vast, vector Z (sterke as) | factor 1 | 27.635 - | 27.635 | +0.00% | 0.2% | OK |
| BU-21 | Balkorientatie knik: langs X, Y vast, vector Z (sterke as) | factor 1 t.o.v. Mecway | 27.635 - | 27.635 | +0.00% | 0.01% | OK |
| BU-22 | Balkorientatie knik: langs Z, X vast, standaard (sterke as) | factor 1 | 27.635 - | 27.635 | +0.00% | 0.2% | OK |
| BU-22 | Balkorientatie knik: langs Z, X vast, standaard (sterke as) | factor 1 t.o.v. Mecway | 27.635 - | 27.635 | +0.00% | 0.01% | OK |
| BU-23 | Balkorientatie knik: langs Z, X vast, vector X + 30 graden | factor 1 | 8.2041 - | 8.2041 | +0.00% | 0.2% | OK |
| BU-23 | Balkorientatie knik: langs Z, X vast, vector X + 30 graden | factor 1 t.o.v. Mecway | 8.2041 - | 8.2041 | -0.00% | 0.01% | OK |
| BU-24 | Balkorientatie knik: schuin, vector Z + 30 graden, knikvorm | factor 1 | 1.7272 - | 1.7272 | +0.00% | 0.2% | OK |
| BU-24 | Balkorientatie knik: schuin, vector Z + 30 graden, knikvorm | factor 2 | 15.545 - | 15.545 | +0.00% | 0.2% | OK |
| BU-24 | Balkorientatie knik: schuin, vector Z + 30 graden, knikvorm | factor 3 | 27.635 - | 27.635 | +0.00% | 0.2% | OK |
| BU-24 | Balkorientatie knik: schuin, vector Z + 30 graden, knikvorm | knikvorm 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| BU-24 | Balkorientatie knik: schuin, vector Z + 30 graden, knikvorm | knikvorm 3 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| BU-24 | Balkorientatie knik: schuin, vector Z + 30 graden, knikvorm | factor 1 t.o.v. Mecway | 1.7272 - | 1.7272 | -0.00% | 0.01% | OK |
| BU-25 | Orientatiekaart knik: langs Z, X vast, vector X + 30 graden (als BU-23) | factor 1 | 8.2041 - | 8.2041 | +0.00% | 0.2% | OK |
| BU-25 | Orientatiekaart knik: langs Z, X vast, vector X + 30 graden (als BU-23) | factor 1 t.o.v. Mecway | 8.2041 - | 8.2041 | -0.00% | 0.01% | OK |
| BU-30 | Torsional buckling, I column, beam (POU_D_E) | factor 1 | 109.72 - | 109.72 | +0.00% | 0.2% | OK |
| BU-30 | Torsional buckling, I column, beam (POU_D_E) | factor 2 | 987.46 - | 987.46 | +0.00% | 0.2% | OK |
| BU-30 | Torsional buckling, I column, beam (POU_D_E) | factor 3 | 1230.4 - | 1230.4 | +0.00% | 0.2% | OK |
| BU-30 | Torsional buckling, I column, beam (POU_D_E) | factor 4 (torsion) | 2413.9 - | 2413.9 | +0.00% | 0.01% | OK |
| BU-30 | Torsional buckling, I column, beam (POU_D_E) | mode 4 pure torsion | 0 - | 7.4617e-14 | 7.4617e-14 | 1e-06 - | OK |
| BU-30 | Torsional buckling, I column, beam (POU_D_E) | factor 4 vs hex20 (BU-31) | 2384.3 - | 2413.9 | +1.24% | 2.5% | OK |
| BU-31 | Torsional buckling, I column, volume (hex20) | factor 1 | 109.72 - | 109.73 | +0.01% | 0.5% | OK |
| BU-31 | Torsional buckling, I column, volume (hex20) | factor 4 (torsion) vs Mecway | 2384.3 - | 2384.3 | +0.00% | 0.01% | OK |
| BU-31 | Torsional buckling, I column, volume (hex20) | factor 4 (torsion) vs G J A/I_p | 2413.9 - | 2384.3 | -1.23% | 2.5% | OK |
| BU-32 | Frame in L, bending moments, beams (POU_D_E) | positive factor 1 (in plane) | 17.272 - | 17.272 | +0.00% | 0.2% | OK |
| BU-32 | Frame in L, bending moments, beams (POU_D_E) | positive factor 2 (out of plane) | 44.861 - | 44.534 | -0.73% | 2% | OK |
| BU-32 | Frame in L, bending moments, beams (POU_D_E) | positive factor 3 (out of plane) | 124.12 - | 122.44 | -1.35% | 2% | OK |
| BU-32 | Frame in L, bending moments, beams (POU_D_E) | negative factor 1 (reversed load) | -53.543 - | -53.042 | +0.94% | 2% | OK |
| BU-33 | Right-angle frame ssll105, beams (POU_D_E) | positive factor 1 | 0.68 - | 0.68132 | +0.19% | 1% | OK |
| BU-33 | Right-angle frame ssll105, beams (POU_D_E) | negative factor 1 | -1.088 - | -1.0901 | -0.19% | 1% | OK |
| BU-33 | Right-angle frame ssll105, beams (POU_D_E) | positive factor 1 vs ssll105 | 0.68132 - | 0.68132 | -0.00% | 0.01% | OK |
| BU-33 | Right-angle frame ssll105, beams (POU_D_E) | negative factor 1 vs ssll105 | -1.0901 - | -1.0901 | +0.00% | 0.01% | OK |
| BU-34 | Right-angle frame ssll105, shell (DKT) | positive factor 1 vs Mecway | 0.7036 - | 0.70318 | -0.06% | 0.2% | OK |
| BU-34 | Right-angle frame ssll105, shell (DKT) | negative factor 1 vs Mecway (F_X = +1) | 1.1894 - | 1.1873 | -0.17% | 0.5% | OK |
| BU-34 | Right-angle frame ssll105, shell (DKT) | positive factor 1 vs beam reference | 0.68 - | 0.70318 | +3.41% | 5% | OK |
| BU-35 | Flexural-torsional buckling, C column, beam (POU_D_E) | factor 1 (uncoupled) | 135.41 - | 136.02 | +0.45% | 1% | OK |
| BU-35 | Flexural-torsional buckling, C column, beam (POU_D_E) | factor 2 vs G J A/I_p | 616.43 - | 616.43 | -0.00% | 0.01% | OK |
| BU-35 | Flexural-torsional buckling, C column, beam (POU_D_E) | factor 2 vs flexural-torsional | 393.03 - | 616.43 | +56.84% | 5% | BEKEND (KNOWN_BUGS 115) |
| BU-36 | Flexural-torsional buckling, C column, volume (hex20) | factor 1 vs pi^2 E I_V/(4L^2) | 136.02 - | 135.41 | -0.45% | 1% | OK |
| BU-36 | Flexural-torsional buckling, C column, volume (hex20) | factor 2 vs Mecway | 393.03 - | 393.03 | -0.00% | 0.01% | OK |
| BU-36 | Flexural-torsional buckling, C column, volume (hex20) | factor 2 vs flexural-torsional theory | 386.09 - | 393.03 | +1.80% | 3% | OK |
| BU-37 | Frame in L, bending moments, volume (hex20) | positive factor 1 (in plane) | 17.272 - | 17.315 | +0.25% | 0.5% | OK |
| BU-37 | Frame in L, bending moments, volume (hex20) | positive factor 2 (out of plane) vs Mecway | 44.861 - | 45.03 | +0.38% | 1% | OK |
| BU-37 | Frame in L, bending moments, volume (hex20) | positive factor 3 (out of plane) vs Mecway | 124.12 - | 124.64 | +0.42% | 1% | OK |

## Cyclische symmetrie

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND2 in het vlak (Blevins) | 25.587 Hz | 25.738 | +0.59% | 2% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND3 in het vlak (Blevins) | 72.371 Hz | 72.866 | +0.68% | 2% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND4 in het vlak (Blevins) | 138.76 Hz | 139.89 | +0.81% | 2% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND5 in het vlak (Blevins) | 224.41 Hz | 226.6 | +0.98% | 2% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND6 in het vlak (Blevins) | 329.21 Hz | 333.09 | +1.18% | 2% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND2 mode 1 = volledig model | 25.738 Hz | 25.738 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND2 mode 2 = volledig model | 52.879 Hz | 52.879 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND3 mode 1 = volledig model | 72.866 Hz | 72.866 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND3 mode 2 = volledig model | 173.48 Hz | 173.48 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND4 mode 1 = volledig model | 139.89 Hz | 139.89 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND4 mode 2 = volledig model | 358.34 Hz | 358.34 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND5 mode 1 = volledig model | 226.6 Hz | 226.6 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND5 mode 2 = volledig model | 459.54 Hz | 459.54 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND6 mode 1 = volledig model | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | ND6 mode 2 = volledig model | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f1 | 0 Hz | -4.3961e-04 | -4.3961e-04 | 0.05 Hz | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f2 | 0 Hz | 0.0052055 | 0.0052055 | 0.05 Hz | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f3 | 0 Hz | -0.0015069 | -0.0015069 | 0.05 Hz | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f4 | 0 Hz | 0.0021083 | 0.0021083 | 0.05 Hz | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f5 | 25.738 Hz | 25.738 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f6 | 52.879 Hz | 52.879 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f7 | 72.866 Hz | 72.866 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f8 | 173.48 Hz | 173.48 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f9 | 139.89 Hz | 139.89 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f10 | 358.34 Hz | 358.34 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f11 | 226.6 Hz | 226.6 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f12 | 459.54 Hz | 459.54 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f13 | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | Mecway f14 | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | hele wiel: knopen met verplaatsing | 960  | 960 | +0.00% | 0.5  | OK |
| CY-01 | Vrije ring, sector 30 graden (12 segmenten) om Z | hele wiel: sprong op de snijvlakken | 0  | 3.6548e-15 | 3.6548e-15 | 1e-06  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | n=2 in het vlak (Blevins) | 25.587 Hz | 25.738 | +0.59% | 2% | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | n=3 in het vlak (Blevins) | 72.371 Hz | 72.866 | +0.68% | 2% | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | n=4 in het vlak (Blevins) | 138.76 Hz | 139.89 | +0.81% | 2% | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | n=5 in het vlak (Blevins) | 224.41 Hz | 226.6 | +0.98% | 2% | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | n=6 in het vlak (Blevins) | 329.21 Hz | 333.09 | +1.18% | 2% | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 1 (ND 0): 1 - MAC hele wiel | 0  | 0 | 0 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 2 (ND 0): 1 - MAC hele wiel | 0  | 0 | 0 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 3 (ND 1): 1 - MAC hele wiel | 0  | 0 | 0 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 4 (ND 1): 1 - MAC hele wiel | 0  | 0 | 0 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 5 (ND 2): 1 - MAC hele wiel | 0  | 5.4713e-10 | 5.4713e-10 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 6 (ND 2): 1 - MAC hele wiel | 0  | 5.4178e-10 | 5.4178e-10 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 7 (ND 3): 1 - MAC hele wiel | 0  | 1.7068e-10 | 1.7068e-10 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 8 (ND 3): 1 - MAC hele wiel | 0  | 1.7882e-10 | 1.7882e-10 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 9 (ND 4): 1 - MAC hele wiel | 0  | 3.1006e-11 | 3.1006e-11 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 10 (ND 4): 1 - MAC hele wiel | 0  | 3.6155e-08 | 3.6155e-08 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 11 (ND 5): 1 - MAC hele wiel | 0  | 6.0174e-11 | 6.0174e-11 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 12 (ND 5): 1 - MAC hele wiel | 0  | 5.1437e-07 | 5.1437e-07 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 13 (ND 6): 1 - MAC hele wiel | 0  | 1.4593e-10 | 1.4593e-10 | 0.001  | OK |
| CY-02 | Vrije ring, volledig model (referentie CY-01) | CY-01 mode 14 (ND 6): 1 - MAC hele wiel | 0  | 5.1523e-10 | 5.1523e-10 | 0.001  | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND2 in het vlak (Blevins) | 25.587 Hz | 25.738 | +0.59% | 2% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND3 in het vlak (Blevins) | 72.371 Hz | 72.866 | +0.68% | 2% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND4 in het vlak (Blevins) | 138.76 Hz | 139.89 | +0.81% | 2% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND5 in het vlak (Blevins) | 224.41 Hz | 226.6 | +0.98% | 2% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND6 in het vlak (Blevins) | 329.21 Hz | 333.09 | +1.18% | 2% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND2 mode 1 = volledig model | 25.738 Hz | 25.738 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND2 mode 2 = volledig model | 52.879 Hz | 52.879 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND3 mode 1 = volledig model | 72.866 Hz | 72.866 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND3 mode 2 = volledig model | 173.48 Hz | 173.48 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND4 mode 1 = volledig model | 139.89 Hz | 139.89 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND4 mode 2 = volledig model | 358.34 Hz | 358.34 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND5 mode 1 = volledig model | 226.6 Hz | 226.6 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND5 mode 2 = volledig model | 459.54 Hz | 459.54 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND6 mode 1 = volledig model | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | ND6 mode 2 = volledig model | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f1 | 0 Hz | -4.3961e-04 | -4.3961e-04 | 0.05 Hz | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f2 | 0 Hz | 0.0052055 | 0.0052055 | 0.05 Hz | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f3 | 0 Hz | -0.0015069 | -0.0015069 | 0.05 Hz | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f4 | 0 Hz | 0.0021083 | 0.0021083 | 0.05 Hz | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f5 | 25.738 Hz | 25.738 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f6 | 52.879 Hz | 52.879 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f7 | 72.866 Hz | 72.866 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f8 | 173.48 Hz | 173.48 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f9 | 139.89 Hz | 139.89 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f10 | 358.34 Hz | 358.34 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f11 | 226.6 Hz | 226.6 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f12 | 459.54 Hz | 459.54 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f13 | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | Mecway f14 | 333.09 Hz | 333.09 | +0.00% | 1% | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | hele wiel: knopen met verplaatsing | 960  | 960 | +0.00% | 0.5  | OK |
| CY-03 | Vrije ring, sector om X (as gedraaid) | hele wiel: sprong op de snijvlakken | 0  | 3.6548e-15 | 3.6548e-15 | 1e-06  | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | ND0 mode 1 (Leissa 0,1) | 102.12 Hz | 102.77 | +0.64% | 2% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | ND0 mode 2 (Leissa 0,2) | 397.56 Hz | 400.05 | +0.63% | 2% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | ND1 mode 1 (Leissa 1,1) | 212.52 Hz | 213.81 | +0.61% | 2% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | ND2 mode 1 (Leissa 2,1) | 348.63 Hz | 350.67 | +0.58% | 2% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | ND3 mode 1 (Leissa 3,1) | 510.1 Hz | 513.45 | +0.66% | 2% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f1 | 102.77 Hz | 102.77 | +0.00% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f2 | 400.01 Hz | 400.05 | +0.01% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f3 | 213.8 Hz | 213.81 | +0.00% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f4 | 611.47 Hz | 611.6 | +0.02% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f5 | 350.65 Hz | 350.67 | +0.00% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f6 | 702.58 Hz | 702.7 | +0.02% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f7 | 513.43 Hz | 513.45 | +0.00% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | Mecway f8 | 513.43 Hz | 513.5 | +0.01% | 1% | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | hele wiel: knopen met verplaatsing | 4530  | 4530 | +0.00% | 0.5  | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | hele wiel: sprong op de snijvlakken | 0  | 8.9930e-15 | 8.9930e-15 | 1e-06  | OK |
| CY-04 | Ingeklemde cirkelvormige plaat, 6 segmenten, knopen op de as | hele wiel: sprong op de as | 0  | 6.2084e-04 | 6.2084e-04 | 0.002  | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND0 mode 1 = volledig model | 71.915 Hz | 71.915 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND0 mode 2 = volledig model | 365.19 Hz | 365.19 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND1 mode 1 = volledig model | 75.435 Hz | 75.435 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND1 mode 2 = volledig model | 387.44 Hz | 387.44 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND2 mode 1 = volledig model | 100.64 Hz | 100.64 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND2 mode 2 = volledig model | 460.55 Hz | 460.55 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND3 mode 1 = volledig model | 162.59 Hz | 162.59 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND3 mode 2 = volledig model | 594.38 Hz | 594.38 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND4 mode 1 = volledig model | 258.63 Hz | 258.63 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND4 mode 2 = volledig model | 788.96 Hz | 788.97 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND5 mode 1 = volledig model | 387.42 Hz | 387.42 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND5 mode 2 = volledig model | 761.08 Hz | 761.08 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND6 mode 1 = volledig model | 552.64 Hz | 552.64 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | ND6 mode 2 = volledig model | 552.64 Hz | 552.64 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f1 | 71.915 Hz | 71.915 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f2 | 365.19 Hz | 365.19 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f3 | 75.435 Hz | 75.435 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f4 | 387.44 Hz | 387.44 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f5 | 100.64 Hz | 100.64 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f6 | 460.55 Hz | 460.55 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f7 | 162.59 Hz | 162.59 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f8 | 594.38 Hz | 594.38 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f9 | 258.63 Hz | 258.63 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f10 | 788.96 Hz | 788.97 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f11 | 387.42 Hz | 387.42 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f12 | 761.08 Hz | 761.08 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f13 | 552.64 Hz | 552.64 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | Mecway f14 | 552.64 Hz | 552.64 | +0.00% | 1% | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | hele wiel: knopen met verplaatsing | 1524  | 1524 | +0.00% | 0.5  | OK |
| CY-05 | Draaiende schijf om Y (3000 r/min), naaf ingeklemd, 12 segmenten | hele wiel: sprong op de snijvlakken | 0  | 1.2957e-14 | 1.2957e-14 | 1e-06  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f1 | 71.915 Hz | 71.915 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f2 | 75.435 Hz | 75.435 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f3 | 75.435 Hz | 75.435 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f4 | 100.64 Hz | 100.64 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f5 | 100.64 Hz | 100.64 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f6 | 162.59 Hz | 162.59 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f7 | 162.59 Hz | 162.59 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f8 | 258.63 Hz | 258.63 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f9 | 258.63 Hz | 258.63 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f10 | 365.19 Hz | 365.19 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f11 | 387.42 Hz | 387.42 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f12 | 387.42 Hz | 387.42 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f13 | 387.44 Hz | 387.44 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f14 | 387.44 Hz | 387.44 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f15 | 460.55 Hz | 460.55 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f16 | 460.55 Hz | 460.55 | -0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f17 | 552.64 Hz | 552.64 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f18 | 552.64 Hz | 552.64 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f19 | 594.38 Hz | 594.38 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f20 | 594.38 Hz | 594.38 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f21 | 610.63 Hz | 610.63 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f22 | 761.08 Hz | 761.08 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f23 | 761.08 Hz | 761.08 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f24 | 788.96 Hz | 788.96 | -0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f25 | 788.96 Hz | 788.96 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f26 | 1021 Hz | 1021 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f27 | 1021 Hz | 1021 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f28 | 1039.4 Hz | 1039.4 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f29 | 1039.4 Hz | 1039.4 | +0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | Mecway f30 | 1056.7 Hz | 1056.7 | -0.00% | 1% | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 1 (ND 0): 1 - MAC hele wiel | 0  | 6.4130e-12 | 6.4130e-12 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 2 (ND 0): 1 - MAC hele wiel | 0  | 4.2539e-09 | 4.2539e-09 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 3 (ND 1): 1 - MAC hele wiel | 0  | 8.3787e-12 | 8.3787e-12 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 4 (ND 1): 1 - MAC hele wiel | 0  | 1.9443e-09 | 1.9443e-09 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 5 (ND 2): 1 - MAC hele wiel | 0  | 1.7000e-11 | 1.7000e-11 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 6 (ND 2): 1 - MAC hele wiel | 0  | 3.6342e-09 | 3.6342e-09 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 7 (ND 3): 1 - MAC hele wiel | 0  | 8.6350e-11 | 8.6350e-11 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 8 (ND 3): 1 - MAC hele wiel | 0  | 8.7528e-09 | 8.7528e-09 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 9 (ND 4): 1 - MAC hele wiel | 0  | 2.9693e-10 | 2.9693e-10 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 10 (ND 4): 1 - MAC hele wiel | 0  | 2.0667e-08 | 2.0667e-08 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 11 (ND 5): 1 - MAC hele wiel | 0  | 6.8725e-10 | 6.8725e-10 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 12 (ND 5): 1 - MAC hele wiel | 0  | 2.0029e-10 | 2.0029e-10 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 13 (ND 6): 1 - MAC hele wiel | 0  | 9.3763e-11 | 9.3763e-11 | 0.001  | OK |
| CY-06 | Draaiende schijf, volledig model (referentie CY-05) | CY-05 mode 14 (ND 6): 1 - MAC hele wiel | 0  | 8.0776e-10 | 8.0776e-10 | 0.001  | OK |

## Dynamica

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| DY-01a | Massa-veer, staplast, HHT alpha=-0,1 (dt=T/20) | periode | 1 s | 1.0102 | +1.02% | 1.7% | OK |
| DY-01a | Massa-veer, staplast, HHT alpha=-0,1 (dt=T/20) | max. verplaatsing | 0.02 m | 0.019911 | -0.44% | 0.77% | OK |
| DY-01a | Massa-veer, staplast, HHT alpha=-0,1 (dt=T/20) | verloop t.o.v. schema | 0 - | 4.4841e-08 | 4.4841e-08 | 1e-05 - | OK |
| DY-01b | Massa-veer, staplast, Newmark (dt=T/10) | periode | 1 s | 1.0321 | +3.21% | 5% | OK |
| DY-01b | Massa-veer, staplast, Newmark (dt=T/10) | max. verplaatsing | 0.02 m | 0.019996 | -0.02% | 0.14% | OK |
| DY-01b | Massa-veer, staplast, Newmark (dt=T/10) | verloop t.o.v. schema | 0 - | 4.5383e-08 | 4.5383e-08 | 1e-05 - | OK |
| DY-01c | Massa-veer, staplast, Newmark (dt=T/20) | periode | 1 s | 1.0081 | +0.81% | 1.4% | OK |
| DY-01c | Massa-veer, staplast, Newmark (dt=T/20) | max. verplaatsing | 0.02 m | 0.02 | -0.00% | 0.11% | OK |
| DY-01c | Massa-veer, staplast, Newmark (dt=T/20) | verloop t.o.v. schema | 0 - | 4.4349e-08 | 4.4349e-08 | 1e-05 - | OK |
| DY-01d | Massa-veer, staplast, Newmark (dt=T/40) | periode | 1 s | 1.0021 | +0.21% | 0.41% | OK |
| DY-01d | Massa-veer, staplast, Newmark (dt=T/40) | max. verplaatsing | 0.02 m | 0.02 | -0.00% | 0.11% | OK |
| DY-01d | Massa-veer, staplast, Newmark (dt=T/40) | verloop t.o.v. schema | 0 - | 4.4551e-08 | 4.4551e-08 | 1e-05 - | OK |
| DY-02 | Ingeklemde balk, staplast tip, 1e eigenperiode (POU_D_E, HHT, dt=T1/40) | periode 1e mode | 0.069101 s | 0.069286 | +0.27% | 0.51% | OK |
| DY-02 | Ingeklemde balk, staplast tip, 1e eigenperiode (POU_D_E, HHT, dt=T1/40) | max. doorbuiging tip | 0.0039729 m | 0.0039611 | -0.30% | 0.65% | OK |
| DY-02 | Ingeklemde balk, staplast tip, 1e eigenperiode (POU_D_E, HHT, dt=T1/40) | verloop t.o.v. modaal schema | 0 - | 2.8061e-06 | 2.8061e-06 | 0.002 - | OK |
| DY-03a | Staafgolf, staplast, expliciet (hex8, nu=0) | tipsnelheid | 0.24629 m/s | 0.24682 | +0.21% | 0.52% | OK |
| DY-03a | Staafgolf, staplast, expliciet (hex8, nu=0) | spanning midden | 1.0000e+07 Pa | 1.0009e+07 | +0.09% | 0.34% | OK |
| DY-03a | Staafgolf, staplast, expliciet (hex8, nu=0) | aankomsttijd inklemming | 1.9334e-04 s | 1.9508e-04 | +0.90% | 1.6% | OK |
| DY-03a | Staafgolf, staplast, expliciet (hex8, nu=0) | reactie na reflectie | 2000 N | 1998.8 | -0.06% | 0.27% | OK |
| DY-03a | Staafgolf, staplast, expliciet (hex8, nu=0) | max. tipverplaatsing | 9.5238e-05 m | 9.4685e-05 | -0.58% | 1.1% | OK |
| DY-03a | Staafgolf, staplast, expliciet (hex8, nu=0) | verloop t.o.v. 1D-keten | 0 - | 3.7864e-08 | 3.7864e-08 | 1e-05 - | OK |
| DY-03b | Staafgolf, opgelegde snelheid, expliciet | spanning midden | 1.0150e+07 Pa | 1.0158e+07 | +0.08% | 0.32% | OK |
| DY-03b | Staafgolf, opgelegde snelheid, expliciet | reactie na reflectie | 2030.1 N | 2029.2 | -0.04% | 0.26% | OK |
| DY-03b | Staafgolf, opgelegde snelheid, expliciet | tipverplaatsing eind | 1.5000e-04 m | 1.5000e-04 | +0.00% | 0.01% | OK |
| DY-03b | Staafgolf, opgelegde snelheid, expliciet | tipsnelheid | 0.25 m/s | 0.25 | +0.00% | 0.01% | OK |
| DY-03b | Staafgolf, opgelegde snelheid, expliciet | verloop t.o.v. 1D-keten | 0 - | 4.6547e-08 | 4.6547e-08 | 1e-05 - | OK |
| DY-03c | Staafgolf, staplast, impliciet (HHT, dt=T/77) | periode 1e mode | 7.7337e-04 s | 7.7511e-04 | +0.23% | 0.44% | OK |
| DY-03c | Staafgolf, staplast, impliciet (HHT, dt=T/77) | tipsnelheid | 0.24629 m/s | 0.24817 | +0.76% | 1.4% | OK |
| DY-03c | Staafgolf, staplast, impliciet (HHT, dt=T/77) | max. tipverplaatsing | 9.5238e-05 m | 9.2696e-05 | -2.67% | 4.3% | OK |
| DY-03c | Staafgolf, staplast, impliciet (HHT, dt=T/77) | verloop t.o.v. 1D-keten | 0 - | 3.9249e-08 | 3.9249e-08 | 1e-05 - | OK |
| DY-20a | Staafgolf, frictionless met normaalverplaatsing, expliciet (FACE_IMPO) | spanning midden | 1.0150e+07 Pa | 1.0158e+07 | +0.08% | 0.32% | OK |
| DY-20a | Staafgolf, frictionless met normaalverplaatsing, expliciet (FACE_IMPO) | reactie na reflectie | 2030.1 N | 2029.2 | -0.04% | 0.26% | OK |
| DY-20a | Staafgolf, frictionless met normaalverplaatsing, expliciet (FACE_IMPO) | tipverplaatsing eind | 1.5000e-04 m | 1.5000e-04 | +0.00% | 0.01% | OK |
| DY-20a | Staafgolf, frictionless met normaalverplaatsing, expliciet (FACE_IMPO) | tipsnelheid | 0.25 m/s | 0.25 | +0.00% | 0.01% | OK |
| DY-20a | Staafgolf, frictionless met normaalverplaatsing, expliciet (FACE_IMPO) | verloop t.o.v. 1D-keten | 0 - | 4.6547e-08 | 4.6547e-08 | 1e-05 - | OK |
| DY-20b | Staaf, constraint equation ux = C, expliciet | tipverplaatsing eind | 1.0000e-05 m | 1.0000e-05 | -0.00% | 0.0001% | OK |
| DY-20b | Staaf, constraint equation ux = C, expliciet | tipverplaatsing vanaf de eerste uitvoertijd | 0 - | 2.5262e-08 | 2.5262e-08 | 1e-06 - | OK |
| DY-20c | Plaat, frictionless schaalvlak met normaalverplaatsing, expliciet (LIAISON_OBLIQUE) | normaalverplaatsing eind (|uz| gemiddeld) | 1.5000e-04 m | 1.5000e-04 | +0.00% | 0.0001% | OK |
| DY-20c | Plaat, frictionless schaalvlak met normaalverplaatsing, expliciet (LIAISON_OBLIQUE) | normaalsnelheid (|vz| gemiddeld, laatste uitvoertijd) | 0.25 m/s | 0.25 | +0.00% | 0.01% | OK |
| DY-30 | Snedekrachten in DYNA_NON_LINE, quasi-statisch | M_v inklemming | 300 N.m | 300.16 | +0.05% | 2% | OK |
| DY-70 | Staaf met verhinderde uitzetting, constante temperatuur (KNOWN_BUGS 94) | gemiddelde sigma_xx op x = L/2, t = 0.0002 s | -1.3250e+08 Pa | -1.3227e+08 | +0.18% | 1% | OK |
| DY-70 | Staaf met verhinderde uitzetting, constante temperatuur (KNOWN_BUGS 94) | gemiddelde sigma_xx op x = L/2, t = 0.002 s | -1.3250e+08 Pa | -1.3237e+08 | +0.10% | 1% | OK |
| DY-71 | Vrije staaf, temperatuur langzaam oplopend (tijdstabel, quasi-statisch) | u_x(L) op t = 0.005 s | 6.0000e-05 m | 5.9999e-05 | -0.00% | 1% | OK |
| DY-71 | Vrije staaf, temperatuur langzaam oplopend (tijdstabel, quasi-statisch) | u_x(L) op t = 0.01 s | 1.2000e-04 m | 1.1993e-04 | -0.06% | 1% | OK |
| DY-72 | Vrije staaf, constante temperatuur vanaf de eerste stap (staplast) | max. u_x(L) | 2.4000e-04 m | 2.3637e-04 | -1.51% | 3% | OK |
| DY-72 | Vrije staaf, constante temperatuur vanaf de eerste stap (staplast) | gemiddelde u_x(L) over 0..3 T | 1.2000e-04 m | 1.1834e-04 | -1.38% | 3% | OK |
| DY-73 | Dynamic Response (D30): temperatuur telt niet mee | max. |u_x(L)| | 0 m | 9.3324e-09 | 9.3324e-09 | 1.2e-07 m | OK |

## Foutschatter

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| FS-01-h8-n1 | Foutschatter: ingeklemde balk hex8 10x1x1 | doorbuiging tip (gem.) | 0.0019196 m | 0.0012339 | -35.72% | 50% | OK |
| FS-01-h8-n1 | Foutschatter: ingeklemde balk hex8 10x1x1 | effectiviteitsindex | 2  | 1.3392 | -33.04% | 50% | OK |
| FS-01-h8-n1 | Foutschatter: ingeklemde balk hex8 10x1x1 | grootste fout bij inklemming (x) | 0 m | 0 | 0 | 0.1 m | OK |
| FS-01-h8-n16 | Foutschatter: ingeklemde balk hex8 160x16x16 | doorbuiging tip (gem.) | 0.0019196 m | 0.0019016 | -0.94% | 2% | OK |
| FS-01-h8-n16 | Foutschatter: ingeklemde balk hex8 160x16x16 | effectiviteitsindex | 2  | 2.2238 | +11.19% | 50% | OK |
| FS-01-h8-n16 | Foutschatter: ingeklemde balk hex8 160x16x16 | grootste fout bij inklemming (x) | 0 m | 0 | 0 | 0.00625 m | OK |
| FS-01-h8-n16 | Foutschatter: ingeklemde balk hex8 160x16x16 | orde globale schatting | 1  | 0.96286 | -3.71% | 20% | OK |
| FS-01-h8-n2 | Foutschatter: ingeklemde balk hex8 20x2x2 | doorbuiging tip (gem.) | 0.0019196 m | 0.0016682 | -13.10% | 50% | OK |
| FS-01-h8-n2 | Foutschatter: ingeklemde balk hex8 20x2x2 | effectiviteitsindex | 2  | 1.7291 | -13.54% | 50% | OK |
| FS-01-h8-n2 | Foutschatter: ingeklemde balk hex8 20x2x2 | grootste fout bij inklemming (x) | 0 m | 0 | 0 | 0.05 m | OK |
| FS-01-h8-n4 | Foutschatter: ingeklemde balk hex8 40x4x4 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018378 | -4.26% | 32% | OK |
| FS-01-h8-n4 | Foutschatter: ingeklemde balk hex8 40x4x4 | effectiviteitsindex | 2  | 2.0062 | +0.31% | 50% | OK |
| FS-01-h8-n4 | Foutschatter: ingeklemde balk hex8 40x4x4 | grootste fout bij inklemming (x) | 0 m | 0 | 0 | 0.025 m | OK |
| FS-01-h8-n4 | Foutschatter: ingeklemde balk hex8 40x4x4 | orde globale schatting | 1  | 0.88142 | -11.86% | 20% | OK |
| FS-01-h8-n8 | Foutschatter: ingeklemde balk hex8 80x8x8 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018879 | -1.65% | 8% | OK |
| FS-01-h8-n8 | Foutschatter: ingeklemde balk hex8 80x8x8 | effectiviteitsindex | 2  | 2.1146 | +5.73% | 50% | OK |
| FS-01-h8-n8 | Foutschatter: ingeklemde balk hex8 80x8x8 | grootste fout bij inklemming (x) | 0 m | 0 | 0 | 0.0125 m | OK |
| FS-01-h8-n8 | Foutschatter: ingeklemde balk hex8 80x8x8 | orde globale schatting | 1  | 0.95632 | -4.37% | 20% | OK |
| FS-02-h20-n1 | Foutschatter: dikwandige cilinder hex20 1x2x1 | u_r binnenwand | 9.0794e-05 m | 9.0257e-05 | -0.59% | 50% | OK |
| FS-02-h20-n1 | Foutschatter: dikwandige cilinder hex20 1x2x1 | grootste fout aan de binnenwand (r) | 0.1 m | 0.1 | +0.00% | 0.1 m | OK |
| FS-02-h20-n2 | Foutschatter: dikwandige cilinder hex20 2x4x1 | u_r binnenwand | 9.0794e-05 m | 9.0740e-05 | -0.06% | 6.4% | OK |
| FS-02-h20-n2 | Foutschatter: dikwandige cilinder hex20 2x4x1 | grootste fout aan de binnenwand (r) | 0.1 m | 0.1 | +0.00% | 0.05 m | OK |
| FS-02-h20-n2 | Foutschatter: dikwandige cilinder hex20 2x4x1 | orde globale schatting | 2  | 1.8716 | -6.42% | 30% | OK |
| FS-02-h20-n4 | Foutschatter: dikwandige cilinder hex20 4x8x1 | u_r binnenwand | 9.0794e-05 m | 9.0790e-05 | -0.00% | 0.8% | OK |
| FS-02-h20-n4 | Foutschatter: dikwandige cilinder hex20 4x8x1 | grootste fout aan de binnenwand (r) | 0.1 m | 0.1 | -0.00% | 0.025 m | OK |
| FS-02-h20-n4 | Foutschatter: dikwandige cilinder hex20 4x8x1 | orde globale schatting | 2  | 1.9486 | -2.57% | 30% | OK |
| FS-02-h20-n8 | Foutschatter: dikwandige cilinder hex20 8x16x1 | u_r binnenwand | 9.0794e-05 m | 9.0793e-05 | -0.00% | 0.1% | OK |
| FS-02-h20-n8 | Foutschatter: dikwandige cilinder hex20 8x16x1 | grootste fout aan de binnenwand (r) | 0.1 m | 0.1 | +0.00% | 0.0125 m | OK |
| FS-02-h20-n8 | Foutschatter: dikwandige cilinder hex20 8x16x1 | orde globale schatting | 2  | 1.905 | -4.75% | 30% | OK |
| FS-03 | Foutschatter: Code-Aster-testcase sslv153a | DZ knoop MESURE | -0.018668  | -0.018668 | -0.00% | 0.0001% | OK |
| FS-03 | Foutschatter: Code-Aster-testcase sslv153a | ERREST ERME_NOEU knoop MESURE | 9339.4  | 9339.4 | -0.00% | 0.0001% | OK |
| FS-03 | Foutschatter: Code-Aster-testcase sslv153a | globale relatieve fout | 51.518 % | 51.518 | +0.00% | 0.01% | OK |

## Harmonische respons

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | |U| over alle frequenties (max. rel. afwijking) | 0 - | 5.4837e-08 | 5.4837e-08 | 0.01 - | OK |
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | fase over alle frequenties (max. afwijking) | 0 graden | 7.4906e-06 | 7.4906e-06 | 1 graden | OK |
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | Re + i Im over alle frequenties (max. |U - U_exact| / |U_exact|) | 0 - | 5.1019e-08 | 5.1019e-08 | 0.01 - | OK |
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | piekamplitude | 0.10013 m | 0.10013 | +0.00% | 1% | OK |
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | frequentie van de piek | 3.5499 Hz | 3.5499 | +0.00% | 0.1% | OK |
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | versnellingsamplitude in de piek | 1 - | 1 | -0.00% | 0.001% | OK |
| HR-01a | 1 vrijheidsgraad, modale demping 0,05 (GENE) | aantal frequenties | 32 - | 32 | +0.00% | 0 - | OK |
| HR-01b | 1 vrijheidsgraad, Rayleigh alpha (GENE) | |U| over alle frequenties (max. rel. afwijking) | 0 - | 5.4837e-08 | 5.4837e-08 | 0.01 - | OK |
| HR-01b | 1 vrijheidsgraad, Rayleigh alpha (GENE) | fase over alle frequenties (max. afwijking) | 0 graden | 7.4906e-06 | 7.4906e-06 | 1 graden | OK |
| HR-01b | 1 vrijheidsgraad, Rayleigh alpha (GENE) | Re + i Im over alle frequenties (max. |U - U_exact| / |U_exact|) | 0 - | 5.1019e-08 | 5.1019e-08 | 0.01 - | OK |
| HR-01b | 1 vrijheidsgraad, Rayleigh alpha (GENE) | piekamplitude | 0.10013 m | 0.10013 | +0.00% | 1% | OK |
| HR-01b | 1 vrijheidsgraad, Rayleigh alpha (GENE) | frequentie van de piek | 3.5499 Hz | 3.5499 | +0.00% | 0.1% | OK |
| HR-01b | 1 vrijheidsgraad, Rayleigh alpha (GENE) | versnellingsamplitude in de piek | 1 - | 1 | -0.00% | 0.001% | OK |
| HR-01c | 1 vrijheidsgraad, Rayleigh alpha (PHYS, direct) | |U| over alle frequenties (max. rel. afwijking) | 0 - | 5.4837e-08 | 5.4837e-08 | 0.01 - | OK |
| HR-01c | 1 vrijheidsgraad, Rayleigh alpha (PHYS, direct) | fase over alle frequenties (max. afwijking) | 0 graden | 7.4906e-06 | 7.4906e-06 | 1 graden | OK |
| HR-01c | 1 vrijheidsgraad, Rayleigh alpha (PHYS, direct) | Re + i Im over alle frequenties (max. |U - U_exact| / |U_exact|) | 0 - | 5.1019e-08 | 5.1019e-08 | 0.01 - | OK |
| HR-01c | 1 vrijheidsgraad, Rayleigh alpha (PHYS, direct) | piekamplitude | 0.10013 m | 0.10013 | +0.00% | 1% | OK |
| HR-01c | 1 vrijheidsgraad, Rayleigh alpha (PHYS, direct) | frequentie van de piek | 3.5499 Hz | 3.5499 | +0.00% | 0.1% | OK |
| HR-01c | 1 vrijheidsgraad, Rayleigh alpha (PHYS, direct) | versnellingsamplitude in de piek | 1 - | 1 | -0.00% | 0.001% | OK |
| HR-01d | 1 vrijheidsgraad, demper zeta = 0,2 (PHYS) | |U| over alle frequenties (max. rel. afwijking) | 0 - | 3.6051e-08 | 3.6051e-08 | 0.01 - | OK |
| HR-01d | 1 vrijheidsgraad, demper zeta = 0,2 (PHYS) | fase over alle frequenties (max. afwijking) | 0 graden | 5.8339e-06 | 5.8339e-06 | 1 graden | OK |
| HR-01d | 1 vrijheidsgraad, demper zeta = 0,2 (PHYS) | Re + i Im over alle frequenties (max. |U - U_exact| / |U_exact|) | 0 - | 4.8383e-08 | 4.8383e-08 | 0.01 - | OK |
| HR-02a | Console (balk), harmonische tipkracht, GENE 8 modes + statische verrijking | tip t.o.v. Euler-Bernoulli, 1 .. 200 Hz (max. |U - U_ex| / |U_ex|) | 0 - | 6.5722e-04 | 6.5722e-04 | 0.01 - | OK |
| HR-02a | Console (balk), harmonische tipkracht, GENE 8 modes + statische verrijking | fase t.o.v. Euler-Bernoulli (max. afwijking) | 0 graden | 0.037656 | 0.037656 | 1 graden | OK |
| HR-02a | Console (balk), harmonische tipkracht, GENE 8 modes + statische verrijking | GENE t.o.v. PHYS (HR-02b), tip complex | 0 - | 1.8919e-05 | 1.8919e-05 | 0.01 - | OK |
| HR-02b | Console (balk), harmonische tipkracht, PHYS (direct) | tip t.o.v. Euler-Bernoulli, 1 .. 200 Hz (max. |U - U_ex| / |U_ex|) | 0 - | 6.5723e-04 | 6.5723e-04 | 0.01 - | OK |
| HR-02b | Console (balk), harmonische tipkracht, PHYS (direct) | fase t.o.v. Euler-Bernoulli (max. afwijking) | 0 graden | 0.037656 | 0.037656 | 1 graden | OK |
| HR-02c | Console (balk), GENE 8 modes zonder statische verrijking (modale truncatie) | statisch deel weggelaten modes bij 1 Hz: (|U_ex| - |U|) / u_st | 6.2258e-04 - | 6.2220e-04 | -0.06% | 2% | OK |
| HR-02c | Console (balk), GENE 8 modes zonder statische verrijking (modale truncatie) | tip t.o.v. Euler-Bernoulli, 1 .. 45 Hz | 0 - | 0.0045749 | 0.0045749 | 0.01 - | OK |
| HR-02c | Console (balk), GENE 8 modes zonder statische verrijking (modale truncatie) | tip t.o.v. Euler-Bernoulli rond mode 2 (95 .. 115 Hz) | 0 - | 0.0052097 | 0.0052097 | 0.01 - | OK |
| HR-03a | Hex20-console, GENE 6 modes + statische verrijking | GENE t.o.v. PHYS: tip U_z (complex) | 0 - | 4.2834e-06 | 4.2834e-06 | 0.01 - | OK |
| HR-03a | Hex20-console, GENE 6 modes + statische verrijking | GENE t.o.v. PHYS: von Mises (max. over de periode) bij de inklemming | 0 - | 4.2899e-05 | 4.2899e-05 | 0.01 - | OK |
| HR-03a | Hex20-console, GENE 6 modes + statische verrijking | GENE t.o.v. PHYS: |sigma_xx| halverwege | 0 - | 0.0022891 | 0.0022891 | 0.01 - | OK |
| HR-03b | Hex20-console, PHYS (direct) | frequentie van de piek (mode 1) | 42.273 Hz | 42.273 | +0.00% | 0.1% | OK |
| HR-04 | Fase 90 graden (#ASTER-FASE), amplitude uit een tabel, meetpunt | |U| (max. rel. afwijking) | 0 - | 2.5053e-08 | 2.5053e-08 | 0.01 - | OK |
| HR-04 | Fase 90 graden (#ASTER-FASE), amplitude uit een tabel, meetpunt | fase (max. afwijking) | 0 graden | 3.5806e-06 | 3.5806e-06 | 1 graden | OK |
| HR-04 | Fase 90 graden (#ASTER-FASE), amplitude uit een tabel, meetpunt | meetpunt-CSV: |u| bij 3 Hz | 0.053083 m | 0.053083 | -0.00% | 0.1% | OK |
| HR-04 | Fase 90 graden (#ASTER-FASE), amplitude uit een tabel, meetpunt | meetpunt-CSV: fase x bij 3 Hz | 73.759 graden | 73.759 | -0.00% | 0.1 graden | OK |
| HR-05 | Twee lasten in tegenfase (#ASTER-FASE Last2 = 180) | |U| (max. rel. afwijking) | 0 - | 2.8069e-08 | 2.8069e-08 | 0.01 - | OK |
| HR-05 | Twee lasten in tegenfase (#ASTER-FASE Last2 = 180) | fase (max. afwijking) | 0 graden | 1.9420e-06 | 1.9420e-06 | 1 graden | OK |

## Lineair statisch

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| LS-01 | Ingeklemde balk, eindlast (balkelementen) | doorbuiging tip | 0.02021 m | 0.02021 | +0.00% | 0.1% | OK |
| LS-01 | Ingeklemde balk, eindlast (balkelementen) | rotatie tip | 0.030315 rad | 0.030315 | +0.00% | 0.1% | OK |
| LS-01 | Ingeklemde balk, eindlast (balkelementen) | reactiekracht Z | 100 N | 100 | +0.00% | 0.0001% | OK |
| LS-02-h20-n1 | Ingeklemde balk volume, hex20, 10x1x1 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018806 | -2.03% | 16% | OK |
| LS-02-h20-n1 | Ingeklemde balk volume, hex20, 10x1x1 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8051e+07 | +0.11% | 8% | OK |
| LS-02-h20-n1 | Ingeklemde balk volume, hex20, 10x1x1 | reactiekracht Z | 10000 N | 10000 | -0.00% | 0.0001% | OK |
| LS-02-h20-n2 | Ingeklemde balk volume, hex20, 20x2x2 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018994 | -1.05% | 4% | OK |
| LS-02-h20-n2 | Ingeklemde balk volume, hex20, 20x2x2 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8019e+07 | +0.04% | 2% | OK |
| LS-02-h20-n2 | Ingeklemde balk volume, hex20, 20x2x2 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-h20-n4 | Ingeklemde balk volume, hex20, 40x4x4 | doorbuiging tip (gem.) | 0.0019196 m | 0.0019041 | -0.81% | 1% | OK |
| LS-02-h20-n4 | Ingeklemde balk volume, hex20, 40x4x4 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8000e+07 | +0.00% | 0.5% | OK |
| LS-02-h20-n4 | Ingeklemde balk volume, hex20, 40x4x4 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-h8-n1 | Ingeklemde balk volume, hex8 3D, 10x1x1 | doorbuiging tip (gem.) | 0.0019196 m | 0.0012339 | -35.72% | 50% | OK |
| LS-02-h8-n1 | Ingeklemde balk volume, hex8 3D, 10x1x1 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 3.6461e+07 | -24.04% | 48% | OK |
| LS-02-h8-n1 | Ingeklemde balk volume, hex8 3D, 10x1x1 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-h8-n16 | Ingeklemde balk volume, hex8 3D, 160x16x16 | doorbuiging tip (gem.) | 0.0019196 m | 0.0019016 | -0.94% | 2% | OK |
| LS-02-h8-n16 | Ingeklemde balk volume, hex8 3D, 160x16x16 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8413e+07 | +0.86% | 3% | OK |
| LS-02-h8-n16 | Ingeklemde balk volume, hex8 3D, 160x16x16 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-h8-n2 | Ingeklemde balk volume, hex8 3D, 20x2x2 | doorbuiging tip (gem.) | 0.0019196 m | 0.0016682 | -13.10% | 50% | OK |
| LS-02-h8-n2 | Ingeklemde balk volume, hex8 3D, 20x2x2 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.5731e+07 | -4.73% | 24% | OK |
| LS-02-h8-n2 | Ingeklemde balk volume, hex8 3D, 20x2x2 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-h8-n4 | Ingeklemde balk volume, hex8 3D, 40x4x4 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018378 | -4.26% | 32% | OK |
| LS-02-h8-n4 | Ingeklemde balk volume, hex8 3D, 40x4x4 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8367e+07 | +0.77% | 12% | OK |
| LS-02-h8-n4 | Ingeklemde balk volume, hex8 3D, 40x4x4 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-h8-n8 | Ingeklemde balk volume, hex8 3D, 80x8x8 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018879 | -1.65% | 8% | OK |
| LS-02-h8-n8 | Ingeklemde balk volume, hex8 3D, 80x8x8 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8611e+07 | +1.27% | 6% | OK |
| LS-02-h8-n8 | Ingeklemde balk volume, hex8 3D, 80x8x8 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-lq-n1 | Ingeklemde balk volume, hex8 LINE_QUAD, 10x1x1 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018806 | -2.03% | 16% | OK |
| LS-02-lq-n1 | Ingeklemde balk volume, hex8 LINE_QUAD, 10x1x1 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8051e+07 | +0.11% | 8% | OK |
| LS-02-lq-n1 | Ingeklemde balk volume, hex8 LINE_QUAD, 10x1x1 | reactiekracht Z | 10000 N | 10000 | -0.00% | 0.0001% | OK |
| LS-02-lq-n2 | Ingeklemde balk volume, hex8 LINE_QUAD, 20x2x2 | doorbuiging tip (gem.) | 0.0019196 m | 0.0018994 | -1.05% | 4% | OK |
| LS-02-lq-n2 | Ingeklemde balk volume, hex8 LINE_QUAD, 20x2x2 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8019e+07 | +0.04% | 2% | OK |
| LS-02-lq-n2 | Ingeklemde balk volume, hex8 LINE_QUAD, 20x2x2 | reactiekracht Z | 10000 N | 10000 | +0.00% | 0.0001% | OK |
| LS-02-lq-n4 | Ingeklemde balk volume, hex8 LINE_QUAD, 40x4x4 | doorbuiging tip (gem.) | 0.0019196 m | 0.0019042 | -0.81% | 1% | OK |
| LS-02-lq-n4 | Ingeklemde balk volume, hex8 LINE_QUAD, 40x4x4 | sigma_xx x=0,2 m boven | 4.8000e+07 Pa | 4.8000e+07 | +0.00% | 0.5% | OK |
| LS-02-lq-n4 | Ingeklemde balk volume, hex8 LINE_QUAD, 40x4x4 | reactiekracht Z | 10000 N | 10000 | -0.00% | 0.0001% | OK |
| LS-03-cq3-n16 | Vrij opgelegde plaat, druk, COQUE_3D quad8 16x16 | doorbuiging midden | 0.0021124 m | 0.0021135 | +0.05% | 0.2% | OK |
| LS-03-cq3-n16 | Vrij opgelegde plaat, druk, COQUE_3D quad8 16x16 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 2.8851e+07 | +0.41% | 1% | OK |
| LS-03-cq3-n16 | Vrij opgelegde plaat, druk, COQUE_3D quad8 16x16 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 2.8851e+07 | +0.41% | 1% | OK |
| LS-03-cq3-n2 | Vrij opgelegde plaat, druk, COQUE_3D quad8 2x2 | doorbuiging midden | 0.0021124 m | 0.0019919 | -5.70% | 12.8% | OK |
| LS-03-cq3-n2 | Vrij opgelegde plaat, druk, COQUE_3D quad8 2x2 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 3.6488e+07 | +26.99% | 50% | OK |
| LS-03-cq3-n2 | Vrij opgelegde plaat, druk, COQUE_3D quad8 2x2 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 3.6488e+07 | +26.99% | 50% | OK |
| LS-03-cq3-n4 | Vrij opgelegde plaat, druk, COQUE_3D quad8 4x4 | doorbuiging midden | 0.0021124 m | 0.0021017 | -0.51% | 3.2% | OK |
| LS-03-cq3-n4 | Vrij opgelegde plaat, druk, COQUE_3D quad8 4x4 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 3.0556e+07 | +6.35% | 16% | OK |
| LS-03-cq3-n4 | Vrij opgelegde plaat, druk, COQUE_3D quad8 4x4 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 3.0556e+07 | +6.35% | 16% | OK |
| LS-03-cq3-n8 | Vrij opgelegde plaat, druk, COQUE_3D quad8 8x8 | doorbuiging midden | 0.0021124 m | 0.0021133 | +0.04% | 0.8% | OK |
| LS-03-cq3-n8 | Vrij opgelegde plaat, druk, COQUE_3D quad8 8x8 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 2.9213e+07 | +1.67% | 4% | OK |
| LS-03-cq3-n8 | Vrij opgelegde plaat, druk, COQUE_3D quad8 8x8 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 2.9213e+07 | +1.67% | 4% | OK |
| LS-03-dkt-n16 | Vrij opgelegde plaat, druk, DKT quad4 16x16 | doorbuiging midden | 0.0021124 m | 0.0021122 | -0.01% | 0.8% | OK |
| LS-03-dkt-n16 | Vrij opgelegde plaat, druk, DKT quad4 16x16 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 2.8805e+07 | +0.26% | 2% | OK |
| LS-03-dkt-n16 | Vrij opgelegde plaat, druk, DKT quad4 16x16 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 2.8805e+07 | +0.26% | 2% | OK |
| LS-03-dkt-n32 | Vrij opgelegde plaat, druk, DKT quad4 32x32 | doorbuiging midden | 0.0021124 m | 0.0021124 | -0.00% | 0.2% | OK |
| LS-03-dkt-n32 | Vrij opgelegde plaat, druk, DKT quad4 32x32 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 2.8750e+07 | +0.06% | 0.5% | OK |
| LS-03-dkt-n32 | Vrij opgelegde plaat, druk, DKT quad4 32x32 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 2.8750e+07 | +0.06% | 0.5% | OK |
| LS-03-dkt-n4 | Vrij opgelegde plaat, druk, DKT quad4 4x4 | doorbuiging midden | 0.0021124 m | 0.0021037 | -0.41% | 12.8% | OK |
| LS-03-dkt-n4 | Vrij opgelegde plaat, druk, DKT quad4 4x4 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 3.0063e+07 | +4.63% | 32% | OK |
| LS-03-dkt-n4 | Vrij opgelegde plaat, druk, DKT quad4 4x4 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 3.0063e+07 | +4.63% | 32% | OK |
| LS-03-dkt-n8 | Vrij opgelegde plaat, druk, DKT quad4 8x8 | doorbuiging midden | 0.0021124 m | 0.0021112 | -0.06% | 3.2% | OK |
| LS-03-dkt-n8 | Vrij opgelegde plaat, druk, DKT quad4 8x8 | sigma midden bovenvlak (VM) | 2.8732e+07 Pa | 2.9032e+07 | +1.04% | 8% | OK |
| LS-03-dkt-n8 | Vrij opgelegde plaat, druk, DKT quad4 8x8 | sigma midden ondervlak (VM) | 2.8732e+07 Pa | 2.9032e+07 | +1.04% | 8% | OK |
| LS-04-h20-n1 | Dikwandige cilinder, inwendige druk, hex20 1x2x1 | u_r binnenwand | 9.0794e-05 m | 9.0257e-05 | -0.59% | 50% | OK |
| LS-04-h20-n1 | Dikwandige cilinder, inwendige druk, hex20 1x2x1 | sigma_theta binnenwand | 1.6667e+08 Pa | 1.6684e+08 | +0.10% | 4% | OK |
| LS-04-h20-n1 | Dikwandige cilinder, inwendige druk, hex20 1x2x1 | sigma_zz binnenwand | 2.0000e+07 Pa | 2.3501e+07 | +17.50% | 50% | OK |
| LS-04-h20-n2 | Dikwandige cilinder, inwendige druk, hex20 2x4x1 | u_r binnenwand | 9.0794e-05 m | 9.0740e-05 | -0.06% | 6.4% | OK |
| LS-04-h20-n2 | Dikwandige cilinder, inwendige druk, hex20 2x4x1 | sigma_theta binnenwand | 1.6667e+08 Pa | 1.6564e+08 | -0.62% | 2% | OK |
| LS-04-h20-n2 | Dikwandige cilinder, inwendige druk, hex20 2x4x1 | sigma_zz binnenwand | 2.0000e+07 Pa | 2.1203e+07 | +6.01% | 16% | OK |
| LS-04-h20-n4 | Dikwandige cilinder, inwendige druk, hex20 4x8x1 | u_r binnenwand | 9.0794e-05 m | 9.0790e-05 | -0.00% | 0.8% | OK |
| LS-04-h20-n4 | Dikwandige cilinder, inwendige druk, hex20 4x8x1 | sigma_theta binnenwand | 1.6667e+08 Pa | 1.6590e+08 | -0.46% | 1% | OK |
| LS-04-h20-n4 | Dikwandige cilinder, inwendige druk, hex20 4x8x1 | sigma_zz binnenwand | 2.0000e+07 Pa | 2.0331e+07 | +1.66% | 4% | OK |
| LS-04-h20-n8 | Dikwandige cilinder, inwendige druk, hex20 8x16x1 | u_r binnenwand | 9.0794e-05 m | 9.0793e-05 | -0.00% | 0.1% | OK |
| LS-04-h20-n8 | Dikwandige cilinder, inwendige druk, hex20 8x16x1 | sigma_theta binnenwand | 1.6667e+08 Pa | 1.6636e+08 | -0.18% | 0.5% | OK |
| LS-04-h20-n8 | Dikwandige cilinder, inwendige druk, hex20 8x16x1 | sigma_zz binnenwand | 2.0000e+07 Pa | 2.0083e+07 | +0.42% | 1% | OK |
| LS-05-cq3-n16 | NAFEMS LE1, COQUE_3D quad8 16x32 | sigma_yy in D (VM midden) | 9.2700e+07 Pa | 9.2654e+07 | -0.05% | 0.5% | OK |
| LS-05-cq3-n2 | NAFEMS LE1, COQUE_3D quad8 2x4 | sigma_yy in D (VM midden) | 9.2700e+07 Pa | 8.2724e+07 | -10.76% | 32% | OK |
| LS-05-cq3-n4 | NAFEMS LE1, COQUE_3D quad8 4x8 | sigma_yy in D (VM midden) | 9.2700e+07 Pa | 9.1346e+07 | -1.46% | 8% | OK |
| LS-05-cq3-n8 | NAFEMS LE1, COQUE_3D quad8 8x16 | sigma_yy in D (VM midden) | 9.2700e+07 Pa | 9.2568e+07 | -0.14% | 2% | OK |
| LS-05-h20-n16 | NAFEMS LE1, hex20 16x32x1 | sigma_yy in D | 9.2700e+07 Pa | 9.2660e+07 | -0.04% | 0.5% | OK |
| LS-05-h20-n2 | NAFEMS LE1, hex20 2x4x1 | sigma_yy in D | 9.2700e+07 Pa | 8.6584e+07 | -6.60% | 32% | OK |
| LS-05-h20-n4 | NAFEMS LE1, hex20 4x8x1 | sigma_yy in D | 9.2700e+07 Pa | 9.2088e+07 | -0.66% | 8% | OK |
| LS-05-h20-n8 | NAFEMS LE1, hex20 8x16x1 | sigma_yy in D | 9.2700e+07 Pa | 9.2629e+07 | -0.08% | 2% | OK |
| LS-06a | Ingeklemde balk met veer langs Y aan de tip | doorbuiging tip Y | 0.0016812 m | 0.0016812 | -0.00% | 0.1% | OK |
| LS-06a | Ingeklemde balk met veer langs Y aan de tip | veerkracht (reactie grond Y) | 1.6812 N | 1.6812 | -0.00% | 0.1% | OK |
| LS-06b | Ingeklemde balk met veer onder 45 graden | doorbuiging tip Y | 0.0018355 m | 0.0018355 | +0.00% | 0.2% | OK |
| LS-07a | Plaatstrook uit twee verlijmde delen (schaal op schaal, eigen meshes) | doorbuiging tip | 9.5238e-04 m | 9.4220e-04 | -1.07% | 2% | OK |
| LS-07a | Plaatstrook uit twee verlijmde delen (schaal op schaal, eigen meshes) | doorbuiging tip t.o.v. Mecway | 9.4148e-04 m | 9.4220e-04 | +0.08% | 0.5% | OK |
| LS-07a | Plaatstrook uit twee verlijmde delen (schaal op schaal, eigen meshes) | rotatie tip | 0.0071429 rad | 0.0070899 | -0.74% | 2% | OK |
| LS-07a | Plaatstrook uit twee verlijmde delen (schaal op schaal, eigen meshes) | rotatie tip t.o.v. Mecway | 0.0070901 rad | 0.0070899 | -0.00% | 0.5% | OK |
| LS-07a | Plaatstrook uit twee verlijmde delen (schaal op schaal, eigen meshes) | rotatie naad, deel B | 0.0053571 rad | 0.0053061 | -0.95% | 2% | OK |
| LS-07a | Plaatstrook uit twee verlijmde delen (schaal op schaal, eigen meshes) | rotatie naad B / A (geen scharnier) | 1 - | 0.99992 | -0.01% | 0.5% | OK |
| LS-07b | Plaatstrook uit één mesh (referentie LS-07a) | doorbuiging tip | 9.5238e-04 m | 9.4257e-04 | -1.03% | 2% | OK |
| LS-07b | Plaatstrook uit één mesh (referentie LS-07a) | doorbuiging tip t.o.v. Mecway | 9.4148e-04 m | 9.4257e-04 | +0.12% | 0.5% | OK |
| LS-07b | Plaatstrook uit één mesh (referentie LS-07a) | rotatie tip | 0.0071429 rad | 0.0070938 | -0.69% | 2% | OK |
| LS-07b | Plaatstrook uit één mesh (referentie LS-07a) | rotatie tip t.o.v. Mecway | 0.0070901 rad | 0.0070938 | +0.05% | 0.5% | OK |
| LS-07c | T-stuk: rib met de rand verlijmd op een plaat, voetlijn op een meshlijn | zijdelingse verplaatsing ribtop | 2.9470e-06 m | 2.9442e-06 | -0.10% | 0.5% | OK |
| LS-07c | T-stuk: rib met de rand verlijmd op een plaat, voetlijn op een meshlijn | idem t.o.v. Mecway | 2.9319e-06 m | 2.9442e-06 | +0.42% | 1% | OK |
| LS-07d | T-stuk: voetlijn midden in de plaatelementen | zijdelingse verplaatsing ribtop | 2.9470e-06 m | 2.7951e-06 | -5.16% | 7% | OK |
| LS-07e | T-stuk met gedeelde knopen (referentie) | zijdelingse verplaatsing ribtop t.o.v. Mecway | 2.9319e-06 m | 2.9470e-06 | +0.51% | 1% | OK |
| LS-07f | Plaatstrook uit twee verlijmde delen, 30 graden gedraaid (scheve master) | doorbuiging tip | 9.5238e-04 m | 9.4220e-04 | -1.07% | 2% | OK |
| LS-07f | Plaatstrook uit twee verlijmde delen, 30 graden gedraaid (scheve master) | doorbuiging tip t.o.v. LS-07a | 9.4220e-04 m | 9.4220e-04 | +0.00% | 0.1% | OK |
| LS-07f | Plaatstrook uit twee verlijmde delen, 30 graden gedraaid (scheve master) | rotatie tip | 0.0071429 rad | 0.0070899 | -0.74% | 2% | OK |
| LS-07f | Plaatstrook uit twee verlijmde delen, 30 graden gedraaid (scheve master) | rotatie naad B / A (geen scharnier) | 1 - | 0.99992 | -0.01% | 0.5% | OK |
| LS-07g | Buis uit twee verlijmde delen (gekromde master, 16 en 24 elementen rond) | doorbuiging tip | 2.7233e-07 m | 2.7306e-07 | +0.27% | 3% | OK |
| LS-07g | Buis uit twee verlijmde delen (gekromde master, 16 en 24 elementen rond) | doorbuiging tip t.o.v. LS-07h | 2.7277e-07 m | 2.7306e-07 | +0.11% | 0.5% | OK |
| LS-07h | Buis uit één mesh (referentie LS-07g) | doorbuiging tip | 2.7233e-07 m | 2.7277e-07 | +0.16% | 3% | OK |
| LS-07h | Buis uit één mesh (referentie LS-07g) | doorbuiging tip t.o.v. Mecway | 2.7235e-07 m | 2.7277e-07 | +0.15% | 1% | OK |
| LS-07i | Quad8-plaat (COQUE_3D) als master, rib midden in de plaatelementen | zijdelingse verplaatsing ribtop | 1.1536e-05 m | 1.1342e-05 | -1.68% | 3% | OK |
| LS-07j | Quad8-plaat met rib, gedeelde knopen (referentie LS-07i) | zijdelingse verplaatsing ribtop t.o.v. Mecway | 1.1404e-05 m | 1.1536e-05 | +1.16% | 2% | OK |
| LS-07k | Quad8-plaat met rib, 30 graden gedraaid (scheve kwadratische master) | verplaatsing ribtop t.o.v. LS-07i | 1.1342e-05 m | 1.1336e-05 | -0.05% | 0.2% | OK |
| LS-07k | Quad8-plaat met rib, 30 graden gedraaid (scheve kwadratische master) | verplaatsing ribtop t.o.v. LS-07j | 1.1536e-05 m | 1.1336e-05 | -1.74% | 3% | OK |
| LS-08a | Staaf ingeklemd in x, Node temperature op alle knopen | sigma_xx | -2.5200e+08 Pa | -2.5200e+08 | -0.00% | 0.0001% | OK |
| LS-08a | Staaf ingeklemd in x, Node temperature op alle knopen | u_y zijkant | 1.5600e-04 m | 1.5600e-04 | +0.00% | 0.0001% | OK |
| LS-08a | Staaf ingeklemd in x, Node temperature op alle knopen | |reactie x| op x = L | 2.5200e+06 N | 2.5200e+06 | +0.00% | 0.0001% | OK |
| LS-08a | Staaf ingeklemd in x, Node temperature op alle knopen | |reactie x| op x = L t.o.v. Mecway | 2.5200e+06 N | 2.5200e+06 | +0.00% | 0.0001% | OK |
| LS-08b | Vrije balk, lineaire temperatuur over de dikte (Node temperature, hex20) | u_z op (L, 0, 0) | -6.0000e-04 m | -6.0000e-04 | -0.00% | 0.01% | OK |
| LS-08b | Vrije balk, lineaire temperatuur over de dikte (Node temperature, hex20) | u_z op (L, 0, h) | -5.9400e-04 m | -5.9400e-04 | -0.00% | 0.01% | OK |
| LS-08b | Vrije balk, lineaire temperatuur over de dikte (Node temperature, hex20) | max |sigma_xx| | 0 Pa | 0.03991 | 0.03991 | 25200 Pa | OK |
| LS-08b | Vrije balk, lineaire temperatuur over de dikte (Node temperature, hex20) | u_z op (L, 0, 0) t.o.v. Mecway | -6.0000e-04 m | -6.0000e-04 | -0.00% | 0.01% | OK |
| LS-08c | Vrije staaf: temperature2 en Node temperature op verschillende knopen, overige op de referentie | gemiddelde u_x op x = L | 4.5000e-05 m | 4.5000e-05 | +0.00% | 1% | OK |
| LS-08c | Vrije staaf: temperature2 en Node temperature op verschillende knopen, overige op de referentie | gemiddelde u_x op x = L t.o.v. Mecway | 4.5000e-05 m | 4.5000e-05 | +0.00% | 1% | OK |
| LS-08d | Als LS-08b met hex8 en LINE_QUAD (middenknopen krijgen de geinterpoleerde temperatuur) | u_z op (L, 0, 0) | -6.0000e-04 m | -6.0000e-04 | -0.00% | 0.01% | OK |
| LS-08d | Als LS-08b met hex8 en LINE_QUAD (middenknopen krijgen de geinterpoleerde temperatuur) | u_z op (L, 0, h) | -5.9400e-04 m | -5.9400e-04 | -0.00% | 0.01% | OK |
| LS-08d | Als LS-08b met hex8 en LINE_QUAD (middenknopen krijgen de geinterpoleerde temperatuur) | max |sigma_xx| | 0 Pa | 0.039053 | 0.039053 | 25200 Pa | OK |
| LS-20a | Configuraties G/Q/ULS: G gekozen | u eindvlak | 1.8335e-07 m | 1.8324e-07 | -0.06% | 0.5% | OK |
| LS-20a | Configuraties G/Q/ULS: G gekozen | reactiekracht X | 770.09 N | 770.08 | -0.00% | 0.0001% | OK |
| LS-20b | Configuraties G/Q/ULS: Q gekozen | u eindvlak | 4.7619e-06 m | 4.7619e-06 | -0.00% | 0.5% | OK |
| LS-20b | Configuraties G/Q/ULS: Q gekozen | reactiekracht X | 10000 N | 10000 | -0.00% | 0.0001% | OK |
| LS-20c | Configuraties G/Q/ULS: ULS gekozen | u eindvlak | 7.3629e-06 m | 7.3627e-06 | -0.00% | 0.5% | OK |
| LS-20c | Configuraties G/Q/ULS: ULS gekozen | reactiekracht X | 15924 N | 15924 | -0.00% | 0.0001% | OK |
| LS-20d | Configuraties G/Q/ULS: auto (de eerste) | u eindvlak | 1.8335e-07 m | 1.8324e-07 | -0.06% | 0.5% | OK |
| LS-20d | Configuraties G/Q/ULS: auto (de eerste) | reactiekracht X | 770.09 N | 770.08 | -0.00% | 0.0001% | OK |
| LS-20e | Alleen configuratie ULS, items onderdrukt | u eindvlak | 7.3629e-06 m | 7.3627e-06 | -0.00% | 0.5% | OK |
| LS-20e | Alleen configuratie ULS, items onderdrukt | reactiekracht X | 15924 N | 15924 | -0.00% | 0.0001% | OK |
| LS-30 | Snedekrachten ingeklemde balk (beam_forces) | N (tensileforce) | 1000 N | 1000 | +0.00% | 0.0001% | OK |
| LS-30 | Snedekrachten ingeklemde balk (beam_forces) | V_v (sheary) | 200 N | 200 | +0.00% | 0.0001% | OK |
| LS-30 | Snedekrachten ingeklemde balk (beam_forces) | V_w (shearz) | -300 N | -300 | +0.00% | 0.0001% | OK |
| LS-30 | Snedekrachten ingeklemde balk (beam_forces) | T (torsion) | 50 N.m | 50 | -0.00% | 0.0001% | OK |
| LS-30 | Snedekrachten ingeklemde balk (beam_forces) | M_v inklemming (bendingmomv) | 300 N.m | 300 | +0.00% | 0.0001% | OK |
| LS-30 | Snedekrachten ingeklemde balk (beam_forces) | M_w midden (bendingmomw) | 100 N.m | 100 | +0.00% | 0.0001% | OK |
| LS-30b | Snedekrachten schuine balk (lokale assen) | N (tensileforce) | 1000 N | 1000 | -0.00% | 0.0001% | OK |
| LS-30b | Snedekrachten schuine balk (lokale assen) | V_v (sheary) | 200 N | 200 | -0.00% | 0.0001% | OK |
| LS-30b | Snedekrachten schuine balk (lokale assen) | V_w (shearz) | -300 N | -300 | -0.00% | 0.0001% | OK |
| LS-30b | Snedekrachten schuine balk (lokale assen) | T (torsion) | 50 N.m | 50 | -0.00% | 0.0001% | OK |
| LS-30b | Snedekrachten schuine balk (lokale assen) | M_v inklemming (bendingmomv) | 300 N.m | 300 | -0.00% | 0.0001% | OK |
| LS-30b | Snedekrachten schuine balk (lokale assen) | M_w midden (bendingmomw) | 100 N.m | 100 | -0.00% | 0.0001% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | N_u (forceperlengthu) | 30000 N/m | 30000 | -0.00% | 0.1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | M_u (momentu) | 7.5 N | 7.5 | -0.00% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | stressxxu1 | 1.1667e+07 Pa | 1.1671e+07 | +0.03% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | stresszzu1 | 2.9167e+06 Pa | 2.9175e+06 | +0.03% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | stressxyu1 | 1.1667e+07 Pa | 1.1663e+07 | -0.03% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | stressxyb1 | 1.6667e+06 Pa | 1.6698e+06 | +0.19% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | stressxxm1 | 6.6667e+06 Pa | 6.6619e+06 | -0.07% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | lstrainxxu | 3.4765e-05 - | 3.4757e-05 | -0.02% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | lstrainxyu | 1.4324e-04 - | 1.4349e-04 | +0.17% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | lstrainxxb | 4.9665e-06 - | 4.9281e-06 | -0.77% | 1% | OK |
| LS-31 | Schaalstrook scheef in de ruimte: tensor, rek, krachten per lengte, factor of safety (quad4, DKT) | factorofsafety | 9.5238  | 9.525 | +0.01% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | N_u (forceperlengthu) | 30000 N/m | 30000 | +0.00% | 0.1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | M_u (momentu) | 7.5 N | 7.5 | -0.00% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | stressxxu1 | 1.1667e+07 Pa | 1.1671e+07 | +0.04% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | stresszzu1 | 2.9167e+06 Pa | 2.9022e+06 | -0.50% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | stressxyu1 | 1.1667e+07 Pa | 1.1669e+07 | +0.02% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | stressxyb1 | 1.6667e+06 Pa | 1.6771e+06 | +0.62% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | stressxxm1 | 6.6667e+06 Pa | 6.6659e+06 | -0.01% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | lstrainxxu | 3.4765e-05 - | 3.4776e-05 | +0.03% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | lstrainxyu | 1.4324e-04 - | 1.4330e-04 | +0.04% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | lstrainxxb | 4.9665e-06 - | 4.9415e-06 | -0.50% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | factorofsafety | 9.5238  | 9.5249 | +0.01% | 1% | OK |
| LS-31b | Idem quad8 (COQUE_3D), ook de dwarskracht | Q_u (shearuw), gemiddeld over de breedte | -150 N/m | -150 | +0.00% | 1% | OK |
| LS-31c | Idem quad4 met een eigen U-as (orientationu* = breedterichting) | N_u (forceperlengthv) | 30000 N/m | 30000 | -0.00% | 0.1% | OK |
| LS-31c | Idem quad4 met een eigen U-as (orientationu* = breedterichting) | M_u (momentv) | 7.5 N | 7.5 | -0.00% | 1% | OK |
| LS-31c | Idem quad4 met een eigen U-as (orientationu* = breedterichting) | N_v (forceperlengthu) | 0 N/m | 0.12041 | 0.12041 | 30 N/m | OK |
| LS-31d | Idem met de U-as als Element orientation-kaart | N_u (forceperlengthv) | 30000 N/m | 30000 | -0.00% | 0.1% | OK |
| LS-31d | Idem met de U-as als Element orientation-kaart | M_u (momentv) | 7.5 N | 7.5 | -0.00% | 1% | OK |
| LS-31d | Idem met de U-as als Element orientation-kaart | N_v (forceperlengthu) | 0 N/m | 0.12041 | 0.12041 | 30 N/m | OK |
| LS-32 | Totale rek en factor of safety, eenassige trek (hex8) | lstrainxx | 4.7619e-04  | 4.7619e-04 | +0.00% | 0.01% | OK |
| LS-32 | Totale rek en factor of safety, eenassige trek (hex8) | lstrainyy | -1.4286e-04  | -1.4286e-04 | -0.00% | 0.01% | OK |
| LS-32 | Totale rek en factor of safety, eenassige trek (hex8) | lstrainzz | -1.4286e-04  | -1.4286e-04 | -0.00% | 0.01% | OK |
| LS-32 | Totale rek en factor of safety, eenassige trek (hex8) | factorofsafety | 2.5  | 2.5 | -0.00% | 0.01% | OK |
| LS-32b | Totale rek en factor of safety, zuivere afschuiving (hex8) | lstrainxy (gamma) | 6.1905e-04  | 6.1905e-04 | -0.00% | 0.01% | OK |
| LS-32b | Totale rek en factor of safety, zuivere afschuiving (hex8) | lstrainxx | 0  | 7.2593e-20 | 7.2593e-20 | 1e-09  | OK |
| LS-32b | Totale rek en factor of safety, zuivere afschuiving (hex8) | factorofsafety | 2.8868  | 2.8868 | +0.00% | 0.01% | OK |
| LS-40a | Druk als formule 3*y^2 (kPa, x/y/z in m) op een blok | reactie Z | 8000 N | 8000 | -0.00% | 0.0001% | OK |
| LS-40a | Druk als formule 3*y^2 (kPa, x/y/z in m) op een blok | moment om X | 12000 N.m | 12000 | +0.00% | 0.0001% | OK |
| LS-40a | Druk als formule 3*y^2 (kPa, x/y/z in m) op een blok | moment om Y | -4000 N.m | -4000 | +0.00% | 0.0001% | OK |
| LS-40b | Idem met positionunit mm (3e-6*y^2) | reactie Z | 8000 N | 8000 | -0.00% | 0.0001% | OK |
| LS-40b | Idem met positionunit mm (3e-6*y^2) | moment om X | 12000 N.m | 12000 | -0.00% | 0.0001% | OK |
| LS-40b | Idem met positionunit mm (3e-6*y^2) | moment om Y | -4000 N.m | -4000 | +0.00% | 0.0001% | OK |
| LS-41 | Twee drukken en een traction als formule in één run | reactie Z | 6000 N | 6000 | -0.00% | 0.0001% | OK |
| LS-41 | Twee drukken en een traction als formule in één run | moment om X | 8250 N.m | 8250 | -0.00% | 0.0001% | OK |
| LS-41 | Twee drukken en een traction als formule in één run | reactie X | -4000 N | -4000 | +0.00% | 0.0001% | OK |
| LS-42a | Opgelegde verplaatsing Z = 0,001 x + 0,002 y mm | DZ in (1, 2, 0,1) | 5.0000e-06 m | 5.0000e-06 | +0.00% | 1e-07% | OK |
| LS-42a | Opgelegde verplaatsing Z = 0,001 x + 0,002 y mm | DZ in (0,5, 0,75, 0,1) | 2.0000e-06 m | 2.0000e-06 | +0.00% | 1e-07% | OK |
| LS-42b | Opgelegde verplaatsing schuin (1, 1, 0) = 0,001 (1 + x) mm | verplaatsing langs (1,1,0) in (1, 2, 0,1) | 2.0000e-06 m | 2.0000e-06 | +0.00% | 1e-07% | OK |
| LS-42b | Opgelegde verplaatsing schuin (1, 1, 0) = 0,001 (1 + x) mm | idem in (0, 0, 0,1) | 1.0000e-06 m | 1.0000e-06 | +0.00% | 1e-07% | OK |
| LS-42c | Opgelegde rotatie om Y = 0,001 (1 + x) rad aan de tip van een ingeklemde balk | rotatie tip | 0.002 rad | 0.002 | +0.00% | 1e-07% | OK |
| LS-42c | Opgelegde rotatie om Y = 0,001 (1 + x) rad aan de tip van een ingeklemde balk | doorbuiging tip | 0.001 m | 1.0000e-03 | -0.00% | 0.0001% | OK |
| LS-43a | Ingeklemde balk, driehoekslast q = 1000 x N/m (line pressure als formule) | reactie Z | 500 N | 500 | +0.00% | 0.0001% | OK |
| LS-43a | Ingeklemde balk, driehoekslast q = 1000 x N/m (line pressure als formule) | doorbuiging tip | 0.055578 m | 0.055578 | +0.00% | 0.01% | OK |
| LS-43b | Idem met gravity op de balk | reactie Z | 524.19 N | 524.19 | +0.00% | 0.0001% | OK |
| LS-43b | Idem met gravity op de balk | doorbuiging tip | 0.057411 m | 0.057411 | +0.00% | 0.01% | OK |
| LS-44a | Plaat (DKT), druk 3*y^2 Pa als formule | reactie Z | 8 N | 8.0625 | +0.78% | 1% | OK |
| LS-44a | Plaat (DKT), druk 3*y^2 Pa als formule | doorbuiging rand y = 2 m t.o.v. Mecway | 7.5197e-04 m | 7.6170e-04 | +1.29% | 2% | OK |
| LS-44b | Idem met COQUE_3D | reactie Z | 8 N | 8 | +0.00% | 0.0001% | OK |
| LS-44b | Idem met COQUE_3D | doorbuiging rand y = 2 m t.o.v. Mecway | 7.5197e-04 m | 7.5668e-04 | +0.63% | 1% | OK |
| LS-50a | Ingeklemde balk, line3-elementen, eindlast | doorbuiging tip | 0.011905 m | 0.011905 | +0.00% | 0.1% | OK |
| LS-50a | Ingeklemde balk, line3-elementen, eindlast | doorbuiging middenknoop x = 0,1 m | 1.7262e-04 m | 1.7262e-04 | +0.00% | 0.1% | OK |
| LS-50a | Ingeklemde balk, line3-elementen, eindlast | rotatie tip | 0.017857 rad | 0.017857 | +0.00% | 0.1% | OK |
| LS-50a | Ingeklemde balk, line3-elementen, eindlast | reactiekracht Z | 100 N | 100 | +0.00% | 0.0001% | OK |
| LS-50a | Ingeklemde balk, line3-elementen, eindlast | doorbuiging tip t.o.v. Mecway 34, line2 | 0.011905 m | 0.011905 | +0.00% | 0.1% | OK |
| LS-50a | Ingeklemde balk, line3-elementen, eindlast | doorbuiging tip t.o.v. Mecway 34, CCX | 0.011633 m | 0.011905 | +2.34% | 4% | OK |
| LS-50b | Ingeklemde balk, line3-elementen, line pressure | doorbuiging tip | 0.0044643 m | 0.0044643 | +0.00% | 0.1% | OK |
| LS-50b | Ingeklemde balk, line3-elementen, line pressure | doorbuiging middenknoop x = 0,1 m | 8.3482e-05 m | 8.3482e-05 | +0.00% | 0.1% | OK |
| LS-50b | Ingeklemde balk, line3-elementen, line pressure | reactiekracht Z | 100 N | 100 | +0.00% | 0.0001% | OK |
| LS-50b | Ingeklemde balk, line3-elementen, line pressure | doorbuiging tip t.o.v. Mecway 34, line2 | 0.0044643 m | 0.0044643 | -0.00% | 0.1% | OK |
| LS-50b | Ingeklemde balk, line3-elementen, line pressure | doorbuiging tip t.o.v. Mecway 34, CCX | 0.0043292 m | 0.0044643 | +3.12% | 4% | OK |
| LS-50c | Line3-balk met orientatievector, eindlast | doorbuiging tip | 0.095238 m | 0.095238 | -0.00% | 0.1% | OK |
| LS-50c | Line3-balk met orientatievector, eindlast | doorbuiging tip t.o.v. Mecway 34, line2 | 0.095238 m | 0.095238 | -0.00% | 0.1% | OK |
| LS-50c | Line3-balk met orientatievector, eindlast | doorbuiging tip t.o.v. Mecway 34, CCX | 0.092149 m | 0.095238 | +3.35% | 4% | OK |
| LS-51a | Flexible joint: scharnier om W in het midden | doorbuiging midden | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-51a | Flexible joint: scharnier om W in het midden | rotatie links van het scharnier | 0.0037894 rad | 0.0037894 | +0.00% | 0.1% | OK |
| LS-51a | Flexible joint: scharnier om W in het midden | reactiekracht Y | 100 N | 100 | +0.00% | 0.0001% | OK |
| LS-51a | Flexible joint: scharnier om W in het midden | doorbuiging midden t.o.v. Mecway 34 | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-51b | Flexible joint om V: geen effect bij buiging om W | doorbuiging midden | 3.1578e-04 m | 3.1578e-04 | -0.00% | 0.1% | OK |
| LS-51b | Flexible joint om V: geen effect bij buiging om W | doorbuiging midden t.o.v. Mecway 34 | 3.1578e-04 m | 3.1578e-04 | +0.00% | 0.1% | OK |
| LS-51c | Flexible joint aan beide kanten van de knoop | doorbuiging midden | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-51c | Flexible joint aan beide kanten van de knoop | rotatie middenknoop | 0 rad | 0 | 0 | 1e-12 rad | OK |
| LS-51c | Flexible joint aan beide kanten van de knoop | doorbuiging midden t.o.v. Mecway 34 | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-51d | Flexible joint als scharnieroplegging | doorbuiging midden | 5.5262e-04 m | 5.5262e-04 | -0.00% | 0.1% | OK |
| LS-51d | Flexible joint als scharnieroplegging | reactiemoment Z | 18.75 N m | 18.75 | -0.00% | 0.1% | OK |
| LS-51d | Flexible joint als scharnieroplegging | doorbuiging midden t.o.v. Mecway 34 | 5.5262e-04 m | 5.5262e-04 | +0.00% | 0.1% | OK |
| LS-51e | Flexible joint op een line3-balk | doorbuiging midden | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-51f | Flexible joint om V op een verticale balk | doorbuiging midden | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-51f | Flexible joint om V op een verticale balk | doorbuiging midden t.o.v. Mecway 34 | 0.0012631 m | 0.0012631 | +0.00% | 0.1% | OK |
| LS-52a | Flexible joint op een balk met element offset | doorbuiging midden | 0.0012631 m | 0.0012636 | +0.04% | 1% | OK |
| LS-52a | Flexible joint op een balk met element offset | doorbuiging midden t.o.v. Mecway 34 | 0.0012636 m | 0.0012636 | -0.00% | 0.1% | OK |
| LS-52a | Flexible joint op een balk met element offset | rotx midden t.o.v. Mecway 34 | -9.8486e-05 rad | -9.8486e-05 | +0.00% | 0.1% | OK |
| LS-52a | Flexible joint op een balk met element offset | rotx bij x = 0,8 t.o.v. Mecway 34 | -3.9394e-05 rad | -3.9394e-05 | -0.00% | 0.1% | OK |
| LS-52a | Flexible joint op een balk met element offset | reactiekracht Y | 100 N | 100 | -0.00% | 0.0001% | OK |
| LS-52b | Flexible joint naast een balk met element offset (zelfde knoop) | doorbuiging midden | 0.0012631 m | 0.0012636 | +0.04% | 1% | OK |
| LS-52b | Flexible joint naast een balk met element offset (zelfde knoop) | doorbuiging midden t.o.v. Mecway 34 | 0.0012636 m | 0.0012636 | -0.00% | 0.1% | OK |
| LS-52b | Flexible joint naast een balk met element offset (zelfde knoop) | rotx midden t.o.v. Mecway 34 | -9.8486e-05 rad | -9.8486e-05 | +0.00% | 0.1% | OK |
| LS-52b | Flexible joint naast een balk met element offset (zelfde knoop) | rotx bij x = 0,8 t.o.v. Mecway 34 | -3.9394e-05 rad | -3.9394e-05 | -0.00% | 0.1% | OK |
| LS-52b | Flexible joint naast een balk met element offset (zelfde knoop) | reactiekracht Y | 100 N | 100 | -0.00% | 0.0001% | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | doorbuiging midden | 0.0012641 m | 0.0012641 | -0.00% | 0.01% | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | rotx midden (torsie linkerhelft) | -1.9690e-04 rad | -1.9690e-04 | +0.00% | 0.1% | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | rotx bij x = 0,2 (linkerhelft) | -7.8758e-05 rad | -7.8758e-05 | +0.00% | 0.1% | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | rotx bij x = 0,8 (rechterhelft zonder torsie) | 0 rad | -7.3525e-33 | -7.3525e-33 | 1e-09 rad | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | reactiekracht Y | 100 N | 100 | -0.00% | 0.0001% | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | doorbuiging midden t.o.v. Mecway 34 | 0.0012641 m | 0.0012641 | -0.00% | 0.1% | OK |
| LS-52c | Flexible joint U, V en W vrij op een balk met element offset: torsie via de arm | rotx midden t.o.v. Mecway 34 | -1.9690e-04 rad | -1.9690e-04 | +0.00% | 0.1% | OK |
| LS-53a | Snedekrachten per element naast een flexible joint (line2) | elementen met bendingmomw | 10  | 10 | +0.00% | 0  | OK |
| LS-53a | Snedekrachten per element naast een flexible joint (line2) | M in het scharnier (element 6, knoop 1) | 0 N m | 1.5632e-13 | 1.5632e-13 | 1e-06 N m | OK |
| LS-53a | Snedekrachten per element naast een flexible joint (line2) | M element 6, knoop 2 (x = 0,6 m) | 5 N m | 5 | +0.00% | 0.1% | OK |
| LS-53a | Snedekrachten per element naast een flexible joint (line2) | V element 6 | 50 N | 50 | +0.00% | 0.1% | OK |
| LS-53b | Snedekrachten per element, line3-balk met flexible joint | elementen met bendingmomw | 4  | 4 | +0.00% | 0  | OK |
| LS-53b | Snedekrachten per element, line3-balk met flexible joint | M in het scharnier (element 3, knoop 1) | 0 N m | 2.8422e-14 | 2.8422e-14 | 1e-06 N m | OK |
| LS-53b | Snedekrachten per element, line3-balk met flexible joint | M element 3, middenknoop (x = 0,625 m) | 6.25 N m | 6.25 | +0.00% | 0.1% | OK |
| LS-53b | Snedekrachten per element, line3-balk met flexible joint | M element 3, knoop 3 (x = 0,75 m) | 12.5 N m | 12.5 | +0.00% | 0.1% | OK |
| LS-53b | Snedekrachten per element, line3-balk met flexible joint | V element 2, middenknoop | 50 N | 50 | +0.00% | 0.1% | OK |
| LS-54a | Staaf, een line3-truss-element, trekkracht | verlenging tip | 6.0630e-05 m | 6.0630e-05 | +0.00% | 0.0001% | OK |
| LS-54a | Staaf, een line3-truss-element, trekkracht | verplaatsing middenknoop | 3.0315e-05 m | 3.0315e-05 | +0.00% | 0.0001% | OK |
| LS-54a | Staaf, een line3-truss-element, trekkracht | dwarsverplaatsing middenknoop | 0 m | 0 | 0 | 1e-12 m | OK |
| LS-54b | Kabel (tension only), een line3-element, trekkracht | verlenging tip | 6.0630e-05 m | 6.0625e-05 | -0.01% | 0.02% | OK |
| LS-54b | Kabel (tension only), een line3-element, trekkracht | verplaatsing middenknoop | 3.0315e-05 m | 3.0312e-05 | -0.01% | 0.02% | OK |
| LS-54b | Kabel (tension only), een line3-element, trekkracht | reactiekracht X | -1000 N | -1000 | -0.00% | 0.0001% | OK |
| LS-54c | Twee line3-kabels in serie, een op druk: draagt niets | verplaatsing knoop ertussen | 6.0630e-05 m | 6.0619e-05 | -0.02% | 0.1% | OK |
| LS-54c | Twee line3-kabels in serie, een op druk: draagt niets | reactie links (trekkabel) | -1000 N | -999.9 | +0.01% | 0.1% | OK |
| LS-54c | Twee line3-kabels in serie, een op druk: draagt niets | reactie rechts (drukkabel) | 0 N | -0.099972 | -0.099972 | 1 N | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | doorbuiging tip (+W) | 0.0071429 m | 0.0070851 | -0.81% | 2% | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | doorbuiging tip t.o.v. Mecway | 0.0070901 m | 0.0070851 | -0.07% | 0.5% | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | rotatie tip om Y | 0.071269 rad | 0.071231 | -0.05% | 0.5% | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | reactie X inklemming | 100 N | 100 | +0.00% | 0.1% | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | reactiemoment Y inklemming | 0 N m | -7.9705e-08 | -7.9705e-08 | 0.001 N m | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | von Mises onderkant, x = L/2 | 7.7500e+07 Pa | 7.7502e+07 | +0.00% | 2% | OK |
| LS-60a | Plaatstrook met element offset, trek in de knopen (DKT, EXCENTREMENT) | von Mises bovenkant, x = L/2 | 7.2500e+07 Pa | 7.2500e+07 | +0.00% | 2% | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | doorbuiging tip (+W) | 0.0071429 m | 0.007097 | -0.64% | 2% | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | doorbuiging tip t.o.v. Mecway | 0.0070956 m | 0.007097 | +0.02% | 0.5% | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | rotatie tip om Y | 0.071263 rad | 0.071409 | +0.20% | 0.5% | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | reactie X inklemming | 100 N | 100 | -0.00% | 0.1% | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | reactiemoment Y inklemming | 0 N m | -1.4659e-09 | -1.4659e-09 | 0.001 N m | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | von Mises onderkant, x = L/2 | 7.7500e+07 Pa | 7.7500e+07 | +0.00% | 2% | OK |
| LS-60b | Plaatstrook met element offset, trek in de knopen (COQUE_3D, starre armen) | von Mises bovenkant, x = L/2 | 7.2500e+07 Pa | 7.2500e+07 | +0.00% | 2% | OK |
| LS-61 | Sandwich: twee schaallagen met offset +e en -e (Steiner) | doorbuiging tip | 1.5820e-04 m | 1.5657e-04 | -1.03% | 3% | OK |
| LS-61 | Sandwich: twee schaallagen met offset +e en -e (Steiner) | doorbuiging tip t.o.v. Mecway | 1.6090e-04 m | 1.5657e-04 | -2.69% | 3% | OK |
| LS-61 | Sandwich: twee schaallagen met offset +e en -e (Steiner) | reactie Z inklemming | 100 N | 100 | -0.00% | 0.1% | OK |
| LS-61 | Sandwich: twee schaallagen met offset +e en -e (Steiner) | reactiemoment Y inklemming | 20 N m | 20 | -0.00% | 0.1% | OK |
| LS-62 | T-balk: plaat als flens, balk als lijf met offset (starre armen) | doorbuiging tip | 1.8108e-04 m | 1.8100e-04 | -0.05% | 3% | OK |
| LS-62 | T-balk: plaat als flens, balk als lijf met offset (starre armen) | doorbuiging tip t.o.v. Mecway | 1.8490e-04 m | 1.8100e-04 | -2.11% | 3% | OK |
| LS-62 | T-balk: plaat als flens, balk als lijf met offset (starre armen) | reactie Z inklemming | 100 N | 100 | -0.00% | 0.1% | OK |
| LS-62 | T-balk: plaat als flens, balk als lijf met offset (starre armen) | reactiemoment Y inklemming | 100 N m | 100 | -0.00% | 0.1% | OK |
| LS-63 | Samengestelde balk: lijf (balk) + flens (quad8 met offset), torsie (CompositeBeam) | torsiehoek tip | 0.108 rad | 0.10918 | +1.10% | 3% | OK |
| LS-63 | Samengestelde balk: lijf (balk) + flens (quad8 met offset), torsie (CompositeBeam) | torsiehoek tip t.o.v. Mecway | 0.10913 rad | 0.10918 | +0.05% | 0.5% | OK |
| LS-63 | Samengestelde balk: lijf (balk) + flens (quad8 met offset), torsie (CompositeBeam) | zijverplaatsing knooplijn tip t.o.v. Mecway | 0.011405 m | 0.011407 | +0.02% | 0.5% | OK |
| LS-63 | Samengestelde balk: lijf (balk) + flens (quad8 met offset), torsie (CompositeBeam) | reactiemoment om de X-as, inklemming | 6 N m | 6 | -0.00% | 0.1% | OK |
| LS-64 | Twee schaalelsets, elk voor de helft met element offset (DKT, restgroep per elset) | doorbuiging tip (+W) | 0.0053571 m | 0.0052683 | -1.66% | 2% | OK |
| LS-64 | Twee schaalelsets, elk voor de helft met element offset (DKT, restgroep per elset) | doorbuiging tip t.o.v. Mecway | 0.0052768 m | 0.0052683 | -0.16% | 0.5% | OK |
| LS-64 | Twee schaalelsets, elk voor de helft met element offset (DKT, restgroep per elset) | von Mises onderkant, x = L/4 | 7.7500e+07 Pa | 7.7187e+07 | -0.40% | 2% | OK |
| LS-64 | Twee schaalelsets, elk voor de helft met element offset (DKT, restgroep per elset) | von Mises onderkant, x = 3L/4 | 2.5000e+06 Pa | 2.5003e+06 | +0.01% | 2% | OK |
| LS-64 | Twee schaalelsets, elk voor de helft met element offset (DKT, restgroep per elset) | von Mises bovenkant, x = 3L/4 | 2.5000e+06 Pa | 2.5003e+06 | +0.01% | 2% | OK |
| LS-64 | Twee schaalelsets, elk voor de helft met element offset (DKT, restgroep per elset) | reactie X inklemming | 100 N | 100 | +0.00% | 0.1% | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | elementen met spanning onder (stressxxb1) | 80  | 80 | +0.00% | 0  | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | sigma_xx onder, elementen bij x = L/2 | 7.7500e+07 Pa | 7.7500e+07 | -0.00% | 2% | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | sigma_xx boven, elementen bij x = L/2 | -7.2500e+07 Pa | -7.2500e+07 | +0.00% | 2% | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | sigma_xx onder, knopen bij x = L/2 | 7.7500e+07 Pa | 7.7501e+07 | +0.00% | 2% | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | N_u (forceperlengthu), elementen bij x = L/2 | 5000 N/m | 5000 | -0.00% | 2% | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | eps_xx onder (lstrainxxb), elementen bij x = L/2 | 3.6905e-04  | 3.6905e-04 | -0.00% | 2% | OK |
| LS-65 | Resultaatvelden van verschoven quad8-schalen (COQUE_3D, starre armen) | factor of safety, elementen bij x = L/2 | 3.2258  | 3.2258 | -0.00% | 2% | OK |
| LS-66 | Verlijmd contact met een verschoven quad8-strook (COQUE_3D, starre armen) | doorbuiging tip | 9.5238e-04 m | 9.4266e-04 | -1.02% | 2% | OK |
| LS-66 | Verlijmd contact met een verschoven quad8-strook (COQUE_3D, starre armen) | doorbuiging tip t.o.v. Mecway | 9.4148e-04 m | 9.4266e-04 | +0.12% | 0.5% | OK |
| LS-67 | Randlast op een verschoven schaal (DKT; Mecway: op de verschoven rand) | doorbuiging tip t.o.v. Mecway | 0 m | 0.0070848 | 0.0070848 | 1e-06 m | BEKEND (KNOWN_BUGS 108) |
| LS-67 | Randlast op een verschoven schaal (DKT; Mecway: op de verschoven rand) | reactie X inklemming | 100 N | 100 | +0.00% | 0.1% | OK |
| LS-70 | Balkorientatie statisch: langs X, standaard | tip displx | 1.1905e-06 m | 1.1905e-06 | -0.00% | 1.42981e-05 m | OK |
| LS-70 | Balkorientatie statisch: langs X, standaard | tip disply | 0.0059524 m | 0.0059524 | -0.00% | 1.42981e-05 m | OK |
| LS-70 | Balkorientatie statisch: langs X, standaard | tip displz | 0.14286 m | 0.14286 | -0.00% | 1.42981e-05 m | OK |
| LS-70 | Balkorientatie statisch: langs X, standaard | beamsixxmax inklemming | 5.2525e+08 Pa | 5.2525e+08 | -0.00% | 0.1% | OK |
| LS-70 | Balkorientatie statisch: langs X, standaard | beamsixxmin inklemming | -5.2475e+08 Pa | -5.2475e+08 | +0.00% | 0.1% | OK |
| LS-71 | Balkorientatie statisch: langs Y, standaard | tip displx | 0.0029762 m | 0.0029762 | -0.00% | 1.42888e-05 m | OK |
| LS-71 | Balkorientatie statisch: langs Y, standaard | tip disply | 2.3810e-06 m | 2.3810e-06 | -0.00% | 1.42888e-05 m | OK |
| LS-71 | Balkorientatie statisch: langs Y, standaard | tip displz | 0.14286 m | 0.14286 | -0.00% | 1.42888e-05 m | OK |
| LS-71 | Balkorientatie statisch: langs Y, standaard | beamsixxmax inklemming | 4.8800e+08 Pa | 4.8800e+08 | -0.00% | 0.1% | OK |
| LS-71 | Balkorientatie statisch: langs Y, standaard | beamsixxmin inklemming | -4.8700e+08 Pa | -4.8700e+08 | +0.00% | 0.1% | OK |
| LS-72 | Balkorientatie statisch: langs Z, standaard (V = Y) | tip displx | 0.047619 m | 0.047619 | -0.00% | 4.79896e-06 m | OK |
| LS-72 | Balkorientatie statisch: langs Z, standaard (V = Y) | tip disply | 0.0059524 m | 0.0059524 | -0.00% | 4.79896e-06 m | OK |
| LS-72 | Balkorientatie statisch: langs Z, standaard (V = Y) | tip displz | 3.5714e-06 m | 3.5714e-06 | -0.00% | 4.79896e-06 m | OK |
| LS-72 | Balkorientatie statisch: langs Z, standaard (V = Y) | beamsixxmax inklemming | 2.2575e+08 Pa | 2.2575e+08 | -0.00% | 0.1% | OK |
| LS-72 | Balkorientatie statisch: langs Z, standaard (V = Y) | beamsixxmin inklemming | -2.2425e+08 Pa | -2.2425e+08 | +0.00% | 0.1% | OK |
| LS-73 | Balkorientatie statisch: schuin (1,1,1), standaard | tip displx | -0.025295 m | -0.025295 | -0.00% | 5.83591e-06 m | OK |
| LS-73 | Balkorientatie statisch: schuin (1,1,1), standaard | tip disply | -0.022319 m | -0.022319 | -0.00% | 5.83591e-06 m | OK |
| LS-73 | Balkorientatie statisch: schuin (1,1,1), standaard | tip displz | 0.047621 m | 0.047621 | +0.00% | 5.83591e-06 m | OK |
| LS-73 | Balkorientatie statisch: schuin (1,1,1), standaard | beamsixxmax inklemming | 2.1109e+08 Pa | 2.1109e+08 | +0.00% | 0.1% | OK |
| LS-73 | Balkorientatie statisch: schuin (1,1,1), standaard | beamsixxmin inklemming | -2.0936e+08 Pa | -2.0936e+08 | -0.00% | 0.1% | OK |
| LS-74 | Balkorientatie statisch: langs X, vector Z | tip displx | 1.1905e-06 m | 1.1905e-06 | -0.00% | 9.56557e-06 m | OK |
| LS-74 | Balkorientatie statisch: langs X, vector Z | tip disply | 0.095238 m | 0.095238 | -0.00% | 9.56557e-06 m | OK |
| LS-74 | Balkorientatie statisch: langs X, vector Z | tip displz | 0.0089286 m | 0.0089286 | -0.00% | 9.56557e-06 m | OK |
| LS-74 | Balkorientatie statisch: langs X, vector Z | beamsixxmax inklemming | 4.1275e+08 Pa | 4.1275e+08 | -0.00% | 0.1% | OK |
| LS-74 | Balkorientatie statisch: langs X, vector Z | beamsixxmin inklemming | -4.1225e+08 Pa | -4.1225e+08 | +0.00% | 0.1% | OK |
| LS-75 | Balkorientatie statisch: schuin, vector Z + 30 graden | tip displx | -0.047617 m | -0.047617 | +0.00% | 5.83591e-06 m | OK |
| LS-75 | Balkorientatie statisch: schuin, vector Z + 30 graden | tip disply | 0.022324 m | 0.022324 | -0.00% | 5.83591e-06 m | OK |
| LS-75 | Balkorientatie statisch: schuin, vector Z + 30 graden | tip displz | 0.0253 m | 0.0253 | -0.00% | 5.83591e-06 m | OK |
| LS-75 | Balkorientatie statisch: schuin, vector Z + 30 graden | beamsixxmax inklemming | 2.1109e+08 Pa | 2.1109e+08 | -0.00% | 0.1% | OK |
| LS-75 | Balkorientatie statisch: schuin, vector Z + 30 graden | beamsixxmin inklemming | -2.0936e+08 Pa | -2.0936e+08 | +0.00% | 0.1% | OK |
| LS-76 | Balkorientatie statisch: langs Z, vector X + 30 graden | tip displx | -0.024525 m | -0.024525 | -0.00% | 5.89314e-06 m | OK |
| LS-76 | Balkorientatie statisch: langs Z, vector X + 30 graden | tip disply | 0.053586 m | 0.053586 | +0.00% | 5.89314e-06 m | OK |
| LS-76 | Balkorientatie statisch: langs Z, vector X + 30 graden | tip displz | 3.5714e-06 m | 3.5714e-06 | +0.00% | 5.89314e-06 m | OK |
| LS-76 | Balkorientatie statisch: langs Z, vector X + 30 graden | beamsixxmax inklemming | 2.5553e+08 Pa | 2.5553e+08 | +0.00% | 0.1% | OK |
| LS-76 | Balkorientatie statisch: langs Z, vector X + 30 graden | beamsixxmin inklemming | -2.5403e+08 Pa | -2.5403e+08 | -0.00% | 0.1% | OK |
| LS-77 | Balkorientatie statisch: I-profiel langs Y, vector X + 90 graden | tip displx | 7.4962e-04 m | 7.4962e-04 | +0.00% | 7.75981e-08 m | OK |
| LS-77 | Balkorientatie statisch: I-profiel langs Y, vector X + 90 graden | tip disply | 5.8072e-07 m | 5.8072e-07 | -0.00% | 7.75981e-08 m | OK |
| LS-77 | Balkorientatie statisch: I-profiel langs Y, vector X + 90 graden | tip displz | 2.0053e-04 m | 2.0053e-04 | +0.00% | 7.75981e-08 m | OK |
| LS-78 | Balkorientatie statisch: raamwerk (3 staven, 3 orientaties) | tip displx t.o.v. Mecway | -0.29294 m | -0.29294 | -0.00% | 0.01% | OK |
| LS-78 | Balkorientatie statisch: raamwerk (3 staven, 3 orientaties) | tip disply t.o.v. Mecway | -0.013562 m | -0.013562 | +0.00% | 0.01% | OK |
| LS-78 | Balkorientatie statisch: raamwerk (3 staven, 3 orientaties) | tip displz t.o.v. Mecway | 0.52957 m | 0.52957 | +0.00% | 0.01% | OK |
| LS-78 | Balkorientatie statisch: raamwerk (3 staven, 3 orientaties) | tip rotx t.o.v. Mecway | 0.23933 rad | 0.23933 | -0.00% | 0.01% | OK |
| LS-78 | Balkorientatie statisch: raamwerk (3 staven, 3 orientaties) | tip roty t.o.v. Mecway | -0.26368 rad | -0.26368 | -0.00% | 0.01% | OK |
| LS-78 | Balkorientatie statisch: raamwerk (3 staven, 3 orientaties) | tip rotz t.o.v. Mecway | -0.0031322 rad | -0.0031322 | +0.00% | 0.01% | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip displx | -0.047617 m | -0.047617 | +0.00% | 5.83591e-06 m | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip disply | 0.022324 m | 0.022324 | -0.00% | 5.83591e-06 m | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip displz | 0.0253 m | 0.0253 | -0.00% | 5.83591e-06 m | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | beamsixxmax inklemming | 2.1109e+08 Pa | 2.1109e+08 | -0.00% | 0.1% | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | beamsixxmin inklemming | -2.0936e+08 Pa | -2.0936e+08 | +0.00% | 0.1% | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip displx t.o.v. Mecway | -0.047617 m | -0.047617 | +0.00% | 4.76167e-06 m | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip disply t.o.v. Mecway | 0.022324 m | 0.022324 | -0.00% | 4.76167e-06 m | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip displz t.o.v. Mecway | 0.0253 m | 0.0253 | -0.00% | 4.76167e-06 m | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip rotx t.o.v. Mecway | 0.0025775 rad | 0.0025775 | +0.00% | 6.31477e-06 rad | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip roty t.o.v. Mecway | -0.063148 rad | -0.063148 | +0.00% | 6.31477e-06 rad | OK |
| LS-79 | Orientatiekaart statisch: schuin, vector Z + 30 graden (als LS-75) | tip rotz t.o.v. Mecway | 0.06057 rad | 0.06057 | -0.00% | 6.31477e-06 rad | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip displx als LS-78 (attributen, Mecway) | -0.29294 m | -0.29294 | -0.00% | 0.01% | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip disply als LS-78 (attributen, Mecway) | -0.013562 m | -0.013562 | +0.00% | 0.01% | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip displz als LS-78 (attributen, Mecway) | 0.52957 m | 0.52957 | +0.00% | 0.01% | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip rotx als LS-78 (attributen, Mecway) | 0.23933 rad | 0.23933 | -0.00% | 0.01% | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip roty als LS-78 (attributen, Mecway) | -0.26368 rad | -0.26368 | -0.00% | 0.01% | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip rotz als LS-78 (attributen, Mecway) | -0.0031322 rad | -0.0031322 | +0.00% | 0.01% | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip displx t.o.v. Mecway | -0.29294 m | -0.29294 | -0.00% | 5.29567e-05 m | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip disply t.o.v. Mecway | -0.013562 m | -0.013562 | +0.00% | 5.29567e-05 m | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip displz t.o.v. Mecway | 0.52957 m | 0.52957 | +0.00% | 5.29567e-05 m | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip rotx t.o.v. Mecway | 0.23933 rad | 0.23933 | -0.00% | 2.63685e-05 rad | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip roty t.o.v. Mecway | -0.26368 rad | -0.26368 | -0.00% | 2.63685e-05 rad | OK |
| LS-80 | Orientatiekaart statisch: raamwerk, een kaart per staaf (als LS-78) | tip rotz t.o.v. Mecway | -0.0031322 rad | -0.0031322 | +0.00% | 2.63685e-05 rad | OK |
| LS-81 | Orientatiekaart statisch: vector en hoek als formule van de plaats | tip displx t.o.v. Mecway | 1.1905e-06 m | 1.1905e-06 | +0.00% | 6.17364e-06 m | OK |
| LS-81 | Orientatiekaart statisch: vector en hoek als formule van de plaats | tip disply t.o.v. Mecway | 0.061736 m | 0.061736 | -0.00% | 6.17364e-06 m | OK |
| LS-81 | Orientatiekaart statisch: vector en hoek als formule van de plaats | tip displz t.o.v. Mecway | 0.0038067 m | 0.0038067 | +0.00% | 6.17364e-06 m | OK |
| LS-81 | Orientatiekaart statisch: vector en hoek als formule van de plaats | tip rotx t.o.v. Mecway | 0 rad | 0 | 0 | 7.19087e-06 rad | OK |
| LS-81 | Orientatiekaart statisch: vector en hoek als formule van de plaats | tip roty t.o.v. Mecway | -0.011163 rad | -0.011163 | -0.00% | 7.19087e-06 rad | OK |
| LS-81 | Orientatiekaart statisch: vector en hoek als formule van de plaats | tip rotz t.o.v. Mecway | 0.071909 rad | 0.071909 | -0.00% | 7.19087e-06 rad | OK |
| LS-82 | Orientatiekaart statisch: kaart op de helft van de elementen | tip displx t.o.v. Mecway | 1.1905e-06 m | 1.1905e-06 | +0.00% | 8.40774e-06 m | OK |
| LS-82 | Orientatiekaart statisch: kaart op de helft van de elementen | tip disply t.o.v. Mecway | 0.084077 m | 0.084077 | -0.00% | 8.40774e-06 m | OK |
| LS-82 | Orientatiekaart statisch: kaart op de helft van de elementen | tip displz t.o.v. Mecway | 0.02567 m | 0.02567 | -0.00% | 8.40774e-06 m | OK |
| LS-82 | Orientatiekaart statisch: kaart op de helft van de elementen | tip rotx t.o.v. Mecway | 0 rad | 0 | 0 | 1.09375e-05 rad | OK |
| LS-82 | Orientatiekaart statisch: kaart op de helft van de elementen | tip roty t.o.v. Mecway | -0.063616 rad | -0.063616 | +0.00% | 1.09375e-05 rad | OK |
| LS-82 | Orientatiekaart statisch: kaart op de helft van de elementen | tip rotz t.o.v. Mecway | 0.10937 rad | 0.10937 | -0.00% | 1.09375e-05 rad | OK |

## Modaal met demping

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| MC-01a | Massa-veer-demper, zeta = 0.1 (Mecway Damper) | zeta | 0.1 - | 0.1 | +0.00% | 1% | OK |
| MC-01a | Massa-veer-demper, zeta = 0.1 (Mecway Damper) | f_d (gedempt, <mode frequency>) | 3.541 Hz | 3.541 | -0.00% | 1% | OK |
| MC-01a | Massa-veer-demper, zeta = 0.1 (Mecway Damper) | f_n = |s| / 2 pi | 3.5588 Hz | 3.5588 | +0.00% | 1% | OK |
| MC-01a | Massa-veer-demper, zeta = 0.1 (Mecway Damper) | vorm reeel (|Im| / |Re|) | 0 - | 3.1400e-17 | 3.1400e-17 | 1e-06 - | OK |
| MC-01b | Massa-veer-demper, zeta = 0.5 (Mecway Damper) | zeta | 0.5 - | 0.5 | +0.00% | 1% | OK |
| MC-01b | Massa-veer-demper, zeta = 0.5 (Mecway Damper) | f_d (gedempt, <mode frequency>) | 3.082 Hz | 3.082 | +0.00% | 1% | OK |
| MC-01b | Massa-veer-demper, zeta = 0.5 (Mecway Damper) | f_n = |s| / 2 pi | 3.5588 Hz | 3.5588 | +0.00% | 1% | OK |
| MC-01b | Massa-veer-demper, zeta = 0.5 (Mecway Damper) | vorm reeel (|Im| / |Re|) | 0 - | 9.7700e-18 | 9.7700e-18 | 1e-06 - | OK |
| MC-02a | Massa-veer, Rayleigh alpha (zeta = 0,2) | zeta | 0.2 - | 0.2 | +0.00% | 1% | OK |
| MC-02a | Massa-veer, Rayleigh alpha (zeta = 0,2) | f_d (gedempt, <mode frequency>) | 3.4869 Hz | 3.4869 | -0.00% | 1% | OK |
| MC-02a | Massa-veer, Rayleigh alpha (zeta = 0,2) | f_n = |s| / 2 pi | 3.5588 Hz | 3.5588 | +0.00% | 1% | OK |
| MC-02a | Massa-veer, Rayleigh alpha (zeta = 0,2) | vorm reeel (|Im| / |Re|) | 0 - | 3.3100e-17 | 3.3100e-17 | 1e-06 - | OK |
| MC-02b | Massa-veer, Rayleigh beta (zeta = 0,2) | zeta | 0.2 - | 0.2 | +0.00% | 1% | OK |
| MC-02b | Massa-veer, Rayleigh beta (zeta = 0,2) | f_d (gedempt, <mode frequency>) | 3.4869 Hz | 3.4869 | -0.00% | 1% | OK |
| MC-02b | Massa-veer, Rayleigh beta (zeta = 0,2) | f_n = |s| / 2 pi | 3.5588 Hz | 3.5588 | +0.00% | 1% | OK |
| MC-02b | Massa-veer, Rayleigh beta (zeta = 0,2) | vorm reeel (|Im| / |Re|) | 0 - | 3.3100e-17 | 3.3100e-17 | 1e-06 - | OK |
| MC-03 | Twee massa's, demper op een massa (niet-proportioneel) | f_d mode 1 | 3.2945 Hz | 3.2945 | -0.00% | 0.1% | OK |
| MC-03 | Twee massa's, demper op een massa (niet-proportioneel) | f_d mode 2 | 6.6902 Hz | 6.6902 | +0.00% | 0.1% | OK |
| MC-03 | Twee massa's, demper op een massa (niet-proportioneel) | zeta mode 1 | 0.48765 - | 0.48765 | -0.00% | 0.1% | OK |
| MC-03 | Twee massa's, demper op een massa (niet-proportioneel) | zeta mode 2 | 0.081509 - | 0.081509 | +0.00% | 0.1% | OK |
| MC-03 | Twee massa's, demper op een massa (niet-proportioneel) | vorm complex (|Im| / |Re| > 0,01) | 1 - | 1 | +0.00% | 1e-07% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | zeta mode 1 | 0.050925 - | 0.050925 | -0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_d mode 1 | 42.226 Hz | 42.226 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_n mode 1 t.o.v. Mecway | 42.281 Hz | 42.281 | +0.00% | 0.1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | zeta mode 2 | 0.045305 - | 0.045305 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_d mode 2 | 83.559 Hz | 83.559 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_n mode 2 t.o.v. Mecway | 83.645 Hz | 83.645 | +0.00% | 0.1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | zeta mode 3 | 0.088632 - | 0.088632 | -0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_d mode 3 | 261.82 Hz | 261.82 | -0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_n mode 3 t.o.v. Mecway | 262.85 Hz | 262.85 | -0.00% | 0.1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | zeta mode 4 | 0.16094 - | 0.16094 | -0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_d mode 4 | 495.65 Hz | 495.65 | -0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_n mode 4 t.o.v. Mecway | 502.19 Hz | 502.19 | -0.00% | 0.1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | zeta mode 5 | 0.19712 - | 0.19712 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_d mode 5 | 607.13 Hz | 607.13 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_n mode 5 t.o.v. Mecway | 619.28 Hz | 619.28 | +0.00% | 0.1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | zeta mode 6 | 0.23077 - | 0.23077 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_d mode 6 | 707.97 Hz | 707.97 | +0.00% | 1% | OK |
| MC-04 | Hex20-console, Rayleigh alpha en beta, 6 modes | f_n mode 6 t.o.v. Mecway | 727.61 Hz | 727.61 | +0.00% | 0.1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | zeta elastische mode 1 | 0.088979 - | 0.088979 | -0.00% | 1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | f_n mode 1 t.o.v. Mecway mode 7 | 264.04 Hz | 264.04 | -0.00% | 0.1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | zeta elastische mode 2 | 0.1646 - | 0.1646 | +0.00% | 1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | f_n mode 2 t.o.v. Mecway mode 8 | 514.08 Hz | 514.08 | +0.00% | 0.1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | zeta elastische mode 3 | 0.22857 - | 0.22857 | +0.00% | 1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | f_n mode 3 t.o.v. Mecway mode 9 | 720.53 Hz | 720.53 | +0.00% | 0.1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | zeta elastische mode 4 | 0.3853 - | 0.3853 | +0.00% | 1% | OK |
| MC-05 | Hex20-blok vrij-vrij, Rayleigh: starre modes vallen weg | f_n mode 4 t.o.v. Mecway mode 10 | 1222.3 Hz | 1222.3 | +0.00% | 0.1% | OK |

## Respons op modale basis

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| MD-01 | Massa op balk, staplast, ongedempt | max. verplaatsing (DAF) | 0.015873 m | 0.015873 | -0.00% | 1% | OK |
| MD-01 | Massa op balk, staplast, ongedempt | periode | 0.17701 s | 0.17701 | +0.00% | 0.5% | OK |
| MD-01 | Massa op balk, staplast, ongedempt | verloop t.o.v. u_st (1 - cos wt) | 0 - | 1.1882e-04 | 1.1882e-04 | 0.01 - | OK |
| MD-01 | Massa op balk, staplast, ongedempt | verloop t.o.v. Mecway (disply) | 0 - | 1.3571e-05 | 1.3571e-05 | 0.02 - | OK |
| MD-02 | Massa op balk, staplast, Rayleigh-demping | max. verplaatsing | 0.014718 m | 0.014717 | -0.01% | 1% | OK |
| MD-02 | Massa op balk, staplast, Rayleigh-demping | verloop t.o.v. exact (gedempt) | 0 - | 2.8551e-05 | 2.8551e-05 | 0.01 - | OK |
| MD-02 | Massa op balk, staplast, Rayleigh-demping | verloop t.o.v. Mecway (disply) | 0 - | 4.2211e-06 | 4.2211e-06 | 0.02 - | OK |
| MD-03 | Massa op balk, harmonische last, gedempt | verloop t.o.v. exact (harmonisch) | 0 - | 0.0016595 | 0.0016595 | 0.01 - | OK |
| MD-03 | Massa op balk, harmonische last, gedempt | max. verplaatsing | 0.029548 m | 0.029499 | -0.17% | 1% | OK |
| MD-03 | Massa op balk, harmonische last, gedempt | verloop t.o.v. Mecway (disply) | 0 - | 6.8522e-06 | 6.8522e-06 | 0.02 - | OK |
| MD-04 | Massa op balk, staplast, modale demping (instelling) | max. verplaatsing | 0.014718 m | 0.014717 | -0.01% | 1% | OK |
| MD-04 | Massa op balk, staplast, modale demping (instelling) | verloop t.o.v. exact (gedempt) | 0 - | 2.8298e-05 | 2.8298e-05 | 0.01 - | OK |
| MD-05 | Hex20-console, staplast, 6 modes | verloop t.o.v. Mecway (displz) | 0 - | 3.8083e-05 | 3.8083e-05 | 0.02 - | OK |
| MD-05 | Hex20-console, staplast, 6 modes | verloop t.o.v. Mecway (velz) | 0 - | 1.4157e-04 | 1.4157e-04 | 0.02 - | OK |
| MD-05 | Hex20-console, staplast, 6 modes | verloop t.o.v. Mecway (stressxx) | 0 - | 3.9633e-04 | 3.9633e-04 | 0.02 - | OK |
| MD-06a | Console, 1 mode, zonder statische correctie | eindverplaatsing | 0.0077039 m | 0.0077039 | +0.00% | 0.2% | OK |
| MD-06a | Console, 1 mode, zonder statische correctie | aantal uitvoertijden | 201 - | 201 | +0.00% | 0 - | OK |
| MD-06a | Console, 1 mode, zonder statische correctie | verloop t.o.v. Mecway (disply) | 0 - | 0.0033744 | 0.0033744 | 0.02 - | OK |
| MD-06b | Console, 1 mode, met statische correctie | eindverplaatsing | 0.0079365 m | 0.0079365 | +0.00% | 0.1% | OK |
| MD-07 | D30 direct via dyna_impl_3d (Newmark) | verloop t.o.v. Newmark-schema | 0 - | 1.0389e-04 | 1.0389e-04 | 0.002 - | OK |
| MD-07 | D30 direct via dyna_impl_3d (Newmark) | verloop t.o.v. Mecway (disply) | 0 - | 3.0673e-08 | 3.0673e-08 | 0.02 - | OK |

## Modaal

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | f1 | 16.71 Hz | 16.71 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | f2 | 25.065 Hz | 25.065 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | f3 | 104.72 Hz | 104.72 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | f4 | 157.08 Hz | 157.08 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | f5 | 293.22 Hz | 293.23 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | f6 | 439.84 Hz | 439.84 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | tip Y mode 1 (MASS_GENE) | 0.92155 m | 0.92155 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | eff. massa Y mode 1 (Code-Aster) | 0.61308  | 0.61308 | -0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | eff. massa RZ mode 1 | 0.97069  | 0.97069 | -0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | eff. massa RY mode 2 | 0.97069  | 0.97069 | -0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | som eff. massa RZ (6 modes) | 1.57 kg.m2 | 1.5677 | -0.14% | 1% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway: modaleffectivemassfractionty mode 1 | 0.61308  | 0.61308 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway = .mess: fractie ty mode 1 | 0  | 1.4667e-07 | 1.4667e-07 | 2e-06  | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway = .mess: fractie rz mode 1 | 0  | 1.8551e-07 | 1.8551e-07 | 2e-06  | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway: modaleffectivemassty mode 1 | 2.8876 kg | 2.8876 | +0.00% | 0.2% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway: modaleffectivemassrz mode 1 | 1.524 kg.m2 | 1.524 | +0.00% | 0.3% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway: cumulatief rz t/m mode 6 | 0.99856  | 0.99856 | +0.00% | 0.3% | OK |
| MO-01 | Ingeklemde balk, 6 modes (20 balkelementen) | Mecway = .mess: cumulatief rz t/m mode 6 | 0  | 2.1246e-07 | 2.1246e-07 | 1e-05  | OK |
| MO-02-h20-n2 | Ingeklemde balk, hex20 50x2x3 | f1 | 16.71 Hz | 16.745 | +0.20% | 2% | OK |
| MO-02-h20-n2 | Ingeklemde balk, hex20 50x2x3 | f2 | 25.065 Hz | 25.095 | +0.12% | 2% | OK |
| MO-02-h20-n2 | Ingeklemde balk, hex20 50x2x3 | f3 | 104.72 Hz | 104.75 | +0.02% | 2% | OK |
| MO-02-h20-n4 | Ingeklemde balk, hex20 100x4x6 | f1 | 16.71 Hz | 16.732 | +0.13% | 0.5% | OK |
| MO-02-h20-n4 | Ingeklemde balk, hex20 100x4x6 | f2 | 25.065 Hz | 25.081 | +0.06% | 0.5% | OK |
| MO-02-h20-n4 | Ingeklemde balk, hex20 100x4x6 | f3 | 104.72 Hz | 104.67 | -0.05% | 0.5% | OK |
| MO-03-dkt-k16 | Vrij opgelegde plaat, DKT 48x32 | f1 | 88.782 Hz | 88.742 | -0.05% | 0.5% | OK |
| MO-03-dkt-k16 | Vrij opgelegde plaat, DKT 48x32 | f2 | 170.73 Hz | 170.57 | -0.09% | 0.5% | OK |
| MO-03-dkt-k16 | Vrij opgelegde plaat, DKT 48x32 | f3 | 273.17 Hz | 273.02 | -0.06% | 0.5% | OK |
| MO-03-dkt-k16 | Vrij opgelegde plaat, DKT 48x32 | f4 | 307.32 Hz | 306.96 | -0.12% | 0.5% | OK |
| MO-03-dkt-k4 | Vrij opgelegde plaat, DKT 12x8 | f1 | 88.782 Hz | 88.152 | -0.71% | 8% | OK |
| MO-03-dkt-k4 | Vrij opgelegde plaat, DKT 12x8 | f2 | 170.73 Hz | 168.25 | -1.45% | 8% | OK |
| MO-03-dkt-k4 | Vrij opgelegde plaat, DKT 12x8 | f3 | 273.17 Hz | 270.77 | -0.88% | 8% | OK |
| MO-03-dkt-k4 | Vrij opgelegde plaat, DKT 12x8 | f4 | 307.32 Hz | 301.89 | -1.77% | 8% | OK |
| MO-03-dkt-k8 | Vrij opgelegde plaat, DKT 24x16 | f1 | 88.782 Hz | 88.622 | -0.18% | 2% | OK |
| MO-03-dkt-k8 | Vrij opgelegde plaat, DKT 24x16 | f2 | 170.73 Hz | 170.1 | -0.37% | 2% | OK |
| MO-03-dkt-k8 | Vrij opgelegde plaat, DKT 24x16 | f3 | 273.17 Hz | 272.54 | -0.23% | 2% | OK |
| MO-03-dkt-k8 | Vrij opgelegde plaat, DKT 24x16 | f4 | 307.32 Hz | 305.9 | -0.46% | 2% | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | f1 (star) | 0 Hz | -5.8534e-04 | -5.8534e-04 | 0.5 Hz | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | f6 (star) | 0 Hz | 1.9867e-04 | 1.9867e-04 | 0.5 Hz | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | f7 | 83.874 Hz | 83.88 | +0.01% | 1% | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | som eff. massa X (7 modes) | 1  | 1 | +0.00% | 0.1% | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | som eff. massa Z (7 modes) | 1  | 1 | -0.00% | 0.1% | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | som eff. massa RX (7 modes) | 1  | 1 | -0.00% | 0.1% | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | som eff. massa RZ (7 modes) | 1  | 1 | -0.00% | 0.1% | OK |
| MO-04 | Vrije vierkante plaat (vrij-vrij), DKT 24x24 | J_Z om de oorsprong | 0.53589 kg.m2 | 0.53589 | +0.00% | 0.1% | OK |
| MO-05 | Massa-veerketen, 2 vrijheidsgraden (veer + mass2) | f1 | 2.1995 Hz | 2.1995 | -0.00% | 0.01% | OK |
| MO-05 | Massa-veerketen, 2 vrijheidsgraden (veer + mass2) | f2 | 5.7583 Hz | 5.7583 | +0.00% | 0.01% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | som eff. massa RX (12 modes) | 524.15 kg.m2 | 524.15 | +0.00% | 1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | som eff. massa RY (12 modes) | 450.75 kg.m2 | 450.75 | -0.00% | 1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | som eff. massa RZ (12 modes) | 256.56 kg.m2 | 256.56 | +0.00% | 1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | J_X zwaartepunt | 0.040885 kg.m2 | 0.040885 | -0.00% | 0.1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | J_Y zwaartepunt | 3.279 kg.m2 | 3.279 | -0.00% | 0.1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | J_Z zwaartepunt | 3.3035 kg.m2 | 3.3035 | +0.00% | 0.1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | som eff. massa X (Code-Aster) | 1  | 1 | -0.00% | 0.1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | Mecway: cumulatief tx t/m mode 12 | 1  | 1 | +0.00% | 0.1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | Mecway: cumulatief ty t/m mode 12 | 1  | 1 | +0.00% | 0.1% | OK |
| MO-06 | Vrij blok buiten de oorsprong: effectieve rotatiemassa | Mecway: cumulatief tz t/m mode 12 | 1  | 1 | +0.00% | 0.1% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | eff. massa RZ mode 1 | 0.97069  | 0.97043 | -0.03% | 1% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | eff. massa RY mode 2 | 0.97069  | 0.97051 | -0.02% | 1% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | som eff. massa RZ (6 modes) | 1.5702 kg.m2 | 1.5678 | -0.15% | 1% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | som eff. massa RY (6 modes) | 1.5704 kg.m2 | 1.5681 | -0.15% | 1% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | stressxx mode 1 halverwege | 2.3102e+09 Pa/sqrt(kg) | 2.3203e+09 | +0.43% | 2% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | stressxx mode 1 t.o.v. Mecway | 2.3201e+09 Pa/sqrt(kg) | 2.3203e+09 | +0.01% | 1% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | eff. massa RZ mode 1 t.o.v. Mecway | 0.97043  | 0.97043 | -0.00% | 0.5% | OK |
| MO-07 | Ingeklemde balk hex20: rotatiemassa en spanningen per mode | eff. massa RY mode 2 t.o.v. Mecway | 0.97051  | 0.97051 | -0.00% | 0.5% | OK |
| MO-08 | NAFEMS CP5: twee line3-truss-elementen, 2 modes | f1 | 451.1 Hz | 451.15 | +0.01% | 0.2% | OK |
| MO-08 | NAFEMS CP5: twee line3-truss-elementen, 2 modes | f2 | 1049.9 Hz | 1049.9 | +0.00% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | +0.00% | 0.01% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | +0.00% | 0.01% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f7 torsie | 357.05 Hz | 357.14 | +0.03% | 0.2% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 7 torsie om U | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | f14 langs | 1293 Hz | 1293.4 | +0.03% | 0.1% | OK |
| MO-20 | Balkorientatie modaal: langs X, standaard | mode 14 langs U | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | +0.00% | 0.01% | OK |
| MO-21 | Balkorientatie modaal: langs Y, standaard | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | +0.00% | 0.01% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | +0.00% | 0.01% | OK |
| MO-22 | Balkorientatie modaal: langs Z, standaard (V = Y) | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | +0.00% | 0.01% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | mode 2 langs V | 1 - | 1 | -0.00% | 0.0001 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | mode 5 langs V | 1 - | 1 | -0.00% | 0.0001 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | -0.00% | 0.01% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | -0.00% | 0.01% | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | eff. massa X mode 1 | 0.10218 - | 0.10218 | -0.00% | 0.0002 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | eff. massa Y mode 1 | 0.10218 - | 0.10218 | -0.00% | 0.0002 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | eff. massa Z mode 1 | 0.40872 - | 0.40872 | -0.00% | 0.0002 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | eff. massa X mode 2 | 0.30654 - | 0.30654 | -0.00% | 0.0002 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | eff. massa Y mode 2 | 0.30654 - | 0.30654 | -0.00% | 0.0002 - | OK |
| MO-23 | Balkorientatie modaal: schuin (1,1,1), standaard | eff. massa Z mode 2 | 0 - | 7.5967e-24 | 7.5967e-24 | 0.0002 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | -0.00% | 0.01% | OK |
| MO-24 | Balkorientatie modaal: langs X, vector Z | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | +0.00% | 0.01% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | -0.00% | 0.01% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | +0.00% | 0.01% | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | eff. massa X mode 1 | 0.40872 - | 0.40872 | -0.00% | 0.0002 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | eff. massa Y mode 1 | 0.10218 - | 0.10218 | -0.00% | 0.0002 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | eff. massa Z mode 1 | 0.10218 - | 0.10218 | -0.00% | 0.0002 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | eff. massa X mode 2 | 1.7003e-32 - | 9.2643e-23 | +544867129061.25% | 0.0002 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | eff. massa Y mode 2 | 0.30654 - | 0.30654 | -0.00% | 0.0002 - | OK |
| MO-25 | Balkorientatie modaal: schuin, vector Z + 30 graden | eff. massa Z mode 2 | 0.30654 - | 0.30654 | -0.00% | 0.0002 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | -0.00% | 0.01% | OK |
| MO-26 | Balkorientatie modaal: langs Z, vector X + 30 graden | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | -0.00% | 0.01% | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | f2 torsie | 108.25 Hz | 108.28 | +0.03% | 0.2% | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | mode 2 torsie om U | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | f1 | 32.888 Hz | 32.888 | +0.00% | 0.2% | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | f3 | 110.13 Hz | 110.13 | +0.00% | 0.2% | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | mode 3 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | f1 t.o.v. Mecway | 32.888 Hz | 32.888 | -0.00% | 0.01% | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | f2 t.o.v. Mecway | 108.28 Hz | 108.28 | -0.00% | 0.01% | OK |
| MO-27 | Balkorientatie modaal: I-profiel langs Y, vector X + 90 graden | f3 t.o.v. Mecway | 110.13 Hz | 110.13 | -0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f1 t.o.v. Mecway | 1.3987 Hz | 1.3987 | -0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f2 t.o.v. Mecway | 1.6796 Hz | 1.6796 | +0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f3 t.o.v. Mecway | 4.7555 Hz | 4.7555 | +0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f4 t.o.v. Mecway | 6.4248 Hz | 6.4248 | +0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f5 t.o.v. Mecway | 8.7352 Hz | 8.7352 | -0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f6 t.o.v. Mecway | 21.243 Hz | 21.243 | -0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f7 t.o.v. Mecway | 35.752 Hz | 35.752 | +0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | f8 t.o.v. Mecway | 47.861 Hz | 47.861 | -0.00% | 0.01% | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | mode 1 tiprichting als Mecway | 1 - | 1 | -0.00% | 0.0001 - | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | mode 2 tiprichting als Mecway | 1 - | 1 | -0.00% | 0.0001 - | OK |
| MO-28 | Balkorientatie modaal: raamwerk (3 staven, 3 orientaties) | mode 3 tiprichting als Mecway | 1 - | 1 | -0.00% | 0.0001 - | OK |
| MO-29 | Korte balk L/h = 2,5: buiging zonder rotatietraagheid (als Mecway) | f1 zwak | 835.52 Hz | 835.52 | +0.00% | 0.01% | OK |
| MO-29 | Korte balk L/h = 2,5: buiging zonder rotatietraagheid (als Mecway) | f2 sterk | 3342.1 Hz | 3342.1 | +0.00% | 0.01% | OK |
| MO-30 | Buigmoment per trillingsvorm (beam_forces) | |M(0)|/|w(L)| mode 1 | 14767 N | 14767 | -0.00% | 1% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f1 | 8.3552 Hz | 8.3552 | +0.00% | 0.2% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | mode 1 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f2 | 33.421 Hz | 33.421 | +0.00% | 0.2% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | mode 2 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f3 | 52.361 Hz | 52.361 | +0.00% | 0.2% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | mode 3 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f4 | 146.61 Hz | 146.61 | +0.00% | 0.2% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | mode 4 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f5 | 209.44 Hz | 209.44 | +0.00% | 0.2% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | mode 5 langs V | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f6 | 287.3 Hz | 287.32 | +0.01% | 0.2% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | mode 6 langs W | 1 - | 1 | +0.00% | 0.0001 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f1 t.o.v. Mecway | 8.3552 Hz | 8.3552 | -0.00% | 0.01% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | f2 t.o.v. Mecway | 33.421 Hz | 33.421 | +0.00% | 0.01% | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | eff. massa X mode 1 | 0.40872 - | 0.40872 | -0.00% | 0.0002 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | eff. massa Y mode 1 | 0.10218 - | 0.10218 | -0.00% | 0.0002 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | eff. massa Z mode 1 | 0.10218 - | 0.10218 | -0.00% | 0.0002 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | eff. massa X mode 2 | 1.7003e-32 - | 9.2643e-23 | +544867129061.25% | 0.0002 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | eff. massa Y mode 2 | 0.30654 - | 0.30654 | -0.00% | 0.0002 - | OK |
| MO-31 | Orientatiekaart modaal: schuin, vector Z + 30 graden (als MO-25) | eff. massa Z mode 2 | 0.30654 - | 0.30654 | -0.00% | 0.0002 - | OK |

## Modaal (voorspanning)

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f1 | 66.336 Hz | 66.336 | +0.00% | 0.2% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f2 | 84.562 Hz | 84.562 | +0.00% | 0.2% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f3 | 209.77 Hz | 209.77 | +0.00% | 0.2% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f4 | 296.66 Hz | 296.67 | +0.00% | 0.2% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f1 t.o.v. Mecway | 66.336 Hz | 66.336 | +0.00% | 1% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f2 t.o.v. Mecway | 84.562 Hz | 84.562 | +0.00% | 1% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f3 t.o.v. Mecway | 209.77 Hz | 209.77 | -0.00% | 1% | OK |
| MP-01 | Scharnierende balk onder trek P = Pcr1 (20 balkelementen) | f4 t.o.v. Mecway | 296.67 Hz | 296.67 | -0.00% | 1% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f1 | 33.168 Hz | 33.168 | +0.00% | 0.2% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f2 | 62.052 Hz | 62.052 | +0.00% | 0.2% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f3 | 175.51 Hz | 175.51 | +0.00% | 0.2% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f4 | 273.51 Hz | 273.51 | +0.00% | 0.2% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f1 t.o.v. Mecway | 33.168 Hz | 33.168 | -0.00% | 1% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f2 t.o.v. Mecway | 62.052 Hz | 62.052 | -0.00% | 1% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f3 t.o.v. Mecway | 175.51 Hz | 175.51 | +0.00% | 1% | OK |
| MP-02 | Scharnierende balk onder druk P = 0,5 Pcr1 (20 balkelementen) | f4 t.o.v. Mecway | 273.51 Hz | 273.51 | -0.00% | 1% | OK |
| MP-03 | Scharnierende balk onder trek, hex20 50x2x4 | f1 | 66.336 Hz | 66.305 | -0.05% | 1% | OK |
| MP-03 | Scharnierende balk onder trek, hex20 50x2x4 | f2 | 84.562 Hz | 84.473 | -0.11% | 1% | OK |
| MP-03 | Scharnierende balk onder trek, hex20 50x2x4 | f1 t.o.v. Mecway | 66.305 Hz | 66.305 | -0.00% | 1% | OK |
| MP-03 | Scharnierende balk onder trek, hex20 50x2x4 | f2 t.o.v. Mecway | 84.473 Hz | 84.473 | -0.00% | 1% | OK |
| MP-04 | Draaiende ingeklemde balk, 200 rad/s om Z (centrifugal) | f1 t.o.v. Mecway | 20.903 Hz | 20.795 | -0.52% | 1% | OK |
| MP-04 | Draaiende ingeklemde balk, 200 rad/s om Z (centrifugal) | f2 t.o.v. Mecway | 42.635 Hz | 42.635 | +0.00% | 1% | OK |
| MP-04 | Draaiende ingeklemde balk, 200 rad/s om Z (centrifugal) | f3 t.o.v. Mecway | 128.57 Hz | 128.46 | -0.09% | 1% | OK |
| MP-04 | Draaiende ingeklemde balk, 200 rad/s om Z (centrifugal) | f4 t.o.v. Mecway | 176.79 Hz | 176.79 | -0.00% | 1% | OK |
| MP-05 | Vrij opgelegde plaat, thermische biaxiale druk 0,5 Ncr (DKT 40x40) | f1 | 86.924 Hz | 86.909 | -0.02% | 1% | OK |
| MP-05 | Vrij opgelegde plaat, thermische biaxiale druk 0,5 Ncr (DKT 40x40) | f2 | 274.88 Hz | 274.74 | -0.05% | 1% | OK |
| MP-05 | Vrij opgelegde plaat, thermische biaxiale druk 0,5 Ncr (DKT 40x40) | f3 | 274.88 Hz | 274.74 | -0.05% | 1% | OK |
| MP-05 | Vrij opgelegde plaat, thermische biaxiale druk 0,5 Ncr (DKT 40x40) | f1 t.o.v. Mecway | 86.972 Hz | 86.909 | -0.07% | 1% | OK |
| MP-05 | Vrij opgelegde plaat, thermische biaxiale druk 0,5 Ncr (DKT 40x40) | f2 t.o.v. Mecway | 275.43 Hz | 274.74 | -0.25% | 1% | OK |
| MP-05 | Vrij opgelegde plaat, thermische biaxiale druk 0,5 Ncr (DKT 40x40) | f3 t.o.v. Mecway | 275.43 Hz | 274.74 | -0.25% | 1% | OK |
| MP-06 | Scharnierende balk onder trek, voorspanning uit | f1 | 46.907 Hz | 46.907 | +0.00% | 0.2% | OK |
| MP-06 | Scharnierende balk onder trek, voorspanning uit | f2 | 70.36 Hz | 70.36 | +0.00% | 0.2% | OK |
| MP-06 | Scharnierende balk onder trek, voorspanning uit | f3 | 187.63 Hz | 187.63 | +0.00% | 0.2% | OK |
| MP-06 | Scharnierende balk onder trek, voorspanning uit | f4 | 281.44 Hz | 281.44 | +0.00% | 0.2% | OK |
| MP-07 | Draaiende ingeklemde balk, hex20 50x2x3, 200 rad/s om Z | f1 t.o.v. Mecway | 20.975 Hz | 20.975 | -0.00% | 1% | OK |
| MP-07 | Draaiende ingeklemde balk, hex20 50x2x3, 200 rad/s om Z | f2 t.o.v. Mecway | 42.652 Hz | 42.652 | +0.00% | 1% | OK |
| MP-07 | Draaiende ingeklemde balk, hex20 50x2x3, 200 rad/s om Z | f3 t.o.v. Mecway | 128.55 Hz | 128.55 | -0.00% | 1% | OK |
| MP-07 | Draaiende ingeklemde balk, hex20 50x2x3, 200 rad/s om Z | f4 t.o.v. Mecway | 176.32 Hz | 176.32 | +0.00% | 1% | OK |

## Metallurgie

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | bainiet t=64 s | 0.078401 - | 0.078401 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | bainiet t=80 s | 0.392 - | 0.392 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | bainiet t=90 s | 0.588 - | 0.588 | -0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | bainiet t=100 s | 0.78401 - | 0.78401 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | bainiet t=110 s | 0.98001 - | 0.98001 | -0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | bainiet t=112 s | 1 - | 1 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | austeniet t=100 s | 0.21599 - | 0.21599 | -0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | sigma_xx t=47 s | 2.8200e+08 Pa | 2.8200e+08 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | sigma_xx t=64 s | 3.6000e+08 Pa | 3.6000e+08 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | sigma_xx t=114 s | 3.6000e+08 Pa | 3.6000e+08 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | eps_xx t=47 s | -0.0041125 - | -0.0041125 | +0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | eps_xx t=48 s | -9.3464e-04 - | -9.3469e-04 | -0.01% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | eps_xx t=64 s | 0.034691 - | 0.034691 | -0.00% | 1% | OK |
| MT-01 | Metallurgie: hsnv101a in 3D (bainiet, META_P_IL) | eps_xx t=114 s | 0.036842 - | 0.036842 | -0.00% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | martensiet T=400 C | 0.31168 - | 0.31168 | -0.00% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | martensiet T=360 C | 0.74577 - | 0.74577 | +0.00% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | martensiet T=320 C | 0.9061 - | 0.9061 | -0.00% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | martensiet T=280 C | 0.96532 - | 0.96532 | +0.00% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | martensiet T=240 C | 0.98719 - | 0.98719 | +0.00% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | martensiet T=20 C | 0.99995 - | 0.99313 | -0.68% | 1% | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | bainiet + ferriet T=20 C | 0 - | 0 | 0 | 1e-06 - | OK |
| MT-02 | Metallurgie: snel afkoelen, martensiet (Koistinen-Marburger) | hardheid T=280 C | 437.86 HV | 437.86 | -0.00% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | austeniet T=740 C | 0.10353 - | 0.10353 | -0.00% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | austeniet T=780 C | 0.43115 - | 0.43115 | +0.00% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | austeniet T=820 C | 0.75902 - | 0.75902 | +0.00% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | austeniet T=840 C | 0.92295 - | 0.92295 | -0.00% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | austeniet T=850 C | 0.99141 - | 0.9936 | +0.22% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | austeniet T=860 C | 0.99955 - | 0.99966 | +0.01% | 1% | OK |
| MT-03 | Metallurgie: austenitiseren bij opwarmen | ferriet T=1000 C | 0 - | 0 | 0 | 0.001 - | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | eps_xx t=12 s (T=1000 C) | 0.01156 - | 0.01156 | +0.00% | 1% | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | eps_xx t=12.4 s (T=600 C) | 0.00276 - | 0.00276 | -0.00% | 1% | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | eps_xx t=12.6 s (T=400 C) | 5.2932e-04 - | 5.2932e-04 | -0.00% | 1% | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | eps_xx t=12.66 s (T=340 C) | 0.0033305 - | 0.0033305 | -0.00% | 1% | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | eps_xx t=12.7 s (T=300 C) | 0.0034772 - | 0.0034772 | -0.00% | 1% | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | eps_xx na afschrikken | -5.3518e-07 - | -6.8740e-05 | -12744.40% | 0.0001 - | OK |
| MT-04 | Metallurgie: transformatierek, vrije staaf | max |sigma_xx| t=12,6 s | 0 Pa | 1.1469e-05 | 1.1469e-05 | 100000 Pa | OK |
| MT-05 | Metallurgie: transformatierek, ingeklemde staaf (elastisch) | sigma_xx t=12 s (T=1000 C) | -2.3120e+09 Pa | -2.3120e+09 | +0.00% | 1% | OK |
| MT-05 | Metallurgie: transformatierek, ingeklemde staaf (elastisch) | sigma_xx t=12.4 s (T=600 C) | -5.5201e+08 Pa | -5.5201e+08 | +0.00% | 1% | OK |
| MT-05 | Metallurgie: transformatierek, ingeklemde staaf (elastisch) | sigma_xx t=12.6 s (T=400 C) | -1.0586e+08 Pa | -1.0586e+08 | +0.00% | 1% | OK |
| MT-05 | Metallurgie: transformatierek, ingeklemde staaf (elastisch) | sigma_xx t=12.66 s (T=340 C) | -6.6609e+08 Pa | -6.6609e+08 | +0.00% | 1% | OK |
| MT-05 | Metallurgie: transformatierek, ingeklemde staaf (elastisch) | sigma_xx t=12.7 s (T=300 C) | -6.9543e+08 Pa | -6.9543e+08 | +0.00% | 1% | OK |
| MT-06 | Metallurgie: lasrups op een plaat, warmte-beinvloede zone (16MND5) | knopen in strijd met Ac1/Ac3 (lijn x = 20 mm, boven) | 0 - | 0 | 0 | 0 - | OK |
| MT-06 | Metallurgie: lasrups op een plaat, warmte-beinvloede zone (16MND5) | ferriet basis (y = 15 mm, onder) | 1 - | 1 | +0.00% | 1e-09 - | OK |
| MT-06 | Metallurgie: lasrups op een plaat, warmte-beinvloede zone (16MND5) | som fasen lasas (eind) | 1 - | 1 | +0.00% | 1e-06 - | OK |
| MT-06 | Metallurgie: lasrups op een plaat, warmte-beinvloede zone (16MND5) | austeniet lasas (eind, afgekoeld) | 0 - | 0.0050737 | 0.0050737 | 0.01 - | OK |
| MT-06 | Metallurgie: lasrups op een plaat, warmte-beinvloede zone (16MND5) | hardheid lasas > basis (184 HV) | 1 - | 1 | +0.00% | 0 - | OK |
| MT-06 | Metallurgie: lasrups op een plaat, warmte-beinvloede zone (16MND5) | breedte austenietzone boven (x = 20 mm) | 0.003 m | 0.003 | +0.00% | 0.002 m | OK |
| MT-07 | Metallurgie: lasrups met metallurgische wet (restspanning) | evenwicht: int sigma_xx dA (x = 20 mm) / (SY A) | 0 - | 8.7152e-04 | 8.7152e-04 | 0.03 - | OK |
| MT-07 | Metallurgie: lasrups met metallurgische wet (restspanning) | evenwicht: int sigma_xx (z - zc) dA / (SY A t) | 0 - | -0.0039361 | -0.0039361 | 0.03 - | OK |
| MT-07 | Metallurgie: lasrups met metallurgische wet (restspanning) | martensiet + bainiet lasas boven | 1 - | 0.99493 | -0.51% | 0.02 - | OK |
| MT-07 | Metallurgie: lasrups met metallurgische wet (restspanning) | sigma_xx lasas boven < WE-10 (466 MPa) | 1 - | 1 | +0.00% | 0 - | OK |
| MT-08 | Metallurgie: eigen TRC-diagram (#ASTER-code) | martensiet T=250 C | 0.42305 - | 0.42305 | +0.00% | 1% | OK |
| MT-08 | Metallurgie: eigen TRC-diagram (#ASTER-code) | martensiet T=150 C | 0.80795 - | 0.80795 | -0.00% | 1% | OK |
| MT-08 | Metallurgie: eigen TRC-diagram (#ASTER-code) | martensiet T=50 C | 0.93607 - | 0.93607 | -0.00% | 1% | OK |
| MT-08 | Metallurgie: eigen TRC-diagram (#ASTER-code) | martensiet T=20 C | 0.95404 - | 0.95404 | +0.00% | 1% | OK |
| MT-08 | Metallurgie: eigen TRC-diagram (#ASTER-code) | bainiet + ferriet T=20 C | 0 - | 0 | 0 | 1e-06 - | OK |

## Niet-lineaire knik

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| NK-01 | Ingeklemde kolom, CRIT_STAB, 20 balkelementen | lambda P(t) t=0.5 | 10363 N | 10363 | +0.00% | 0.2% | OK |
| NK-01 | Ingeklemde kolom, CRIT_STAB, 20 balkelementen | lambda P(t) t=1 | 10363 N | 10363 | +0.00% | 0.2% | OK |
| NK-02a | Ingeklemde kolom, CRIT_STAB, hex20, grote verplaatsingen | knikpunt x P_eind | 10363 N | 10402 | +0.37% | 2% | OK |
| NK-02b | Ingeklemde kolom, CRIT_STAB, hex20, PETIT | lambda P(t) t=0.5 | 10363 N | 10384 | +0.20% | 0.5% | OK |
| NK-02b | Ingeklemde kolom, CRIT_STAB, hex20, PETIT | lambda P(t) t=1 | 10363 N | 10384 | +0.20% | 0.5% | OK |
| NK-03 | Ingeklemde kolom hex20 met imperfectie L/1000 (knikvorm 1) | lineaire knik imperfectiestap x P_eind | 10363 N | 10384 | +0.20% | 0.5% | OK |
| NK-03 | Ingeklemde kolom hex20 met imperfectie L/1000 (knikvorm 1) | CRIT_STAB knikpunt x P_eind | 10363 N | 10400 | +0.35% | 2% | OK |
| NK-03 | Ingeklemde kolom hex20 met imperfectie L/1000 (knikvorm 1) | w/e0 P=0.270 Pcr | 1.3699 - | 1.3687 | -0.08% | 5% | OK |
| NK-03 | Ingeklemde kolom hex20 met imperfectie L/1000 (knikvorm 1) | w/e0 P=0.495 Pcr | 1.9802 - | 1.976 | -0.21% | 5% | OK |
| NK-03 | Ingeklemde kolom hex20 met imperfectie L/1000 (knikvorm 1) | w/e0 P=0.675 Pcr | 3.0769 - | 3.0634 | -0.44% | 5% | OK |
| NK-03 | Ingeklemde kolom hex20 met imperfectie L/1000 (knikvorm 1) | Southwell Pcr (P <= 0,7 Pcr) | 10363 N | 10384 | +0.20% | 2% | OK |
| NK-04 | Ingeklemde kolom hex20, plastisch, imperfectie 5 mm: draagkracht | P_u/Pcr (Ayrton-Perry 0.419 .. scharnier 0.563) | 0.49096 - | 0.4881 | -0.58% | 0.0720993 - | OK |
| NK-04 | Ingeklemde kolom hex20, plastisch, imperfectie 5 mm: draagkracht | CRIT_STAB bij P_u / begin | 0 - | 0.0066231 | 0.0066231 | 0.05 - | OK |

*NK-04: diagnose OK; MECANONLINE9_7; BRIDGE_ONVOLLEDIG*

## Niet-lineair statisch

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | F t=1 (elastisch) | 20969 N | 20969 | +0.00% | 0.2% | OK |
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | F t=1.5 (plastisch) | 38908 N | 38908 | -0.00% | 0.2% | OK |
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | F t=2 (plastisch) | 42955 N | 42955 | -0.00% | 0.2% | OK |
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | F t=3 (ontlast) | 12071 N | 12071 | -0.00% | 0.2% | OK |
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | sigma_xx t=2 | 4.3349e+08 Pa | 4.3349e+08 | -0.00% | 0.2% | OK |
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | p t=2 | 0.0078844 - | 0.0078844 | +0.00% | 0.2% | OK |
| NL-01 | Trekstaaf, bilineaire isotrope versteviging, ontlasten | p t=3 (ontlast) | 0.0078844 - | 0.0078844 | +0.00% | 0.2% | OK |
| NL-01b | Trekstaaf, ontlasten (RELA 1e-6 of MAXI 0,05 N) | F t=3 (ontlast) | 12071 N | 12071 | -0.00% | 0.2% | OK |
| NL-01b | Trekstaaf, ontlasten (RELA 1e-6 of MAXI 0,05 N) | p t=3 (ontlast) | 0.0078844 - | 0.0078844 | +0.00% | 0.2% | OK |
| NL-02a | Ingeklemde balk, grote doorbuiging (hex20) | v/L PL2/EI=1 | 0.30172 - | 0.30135 | -0.12% | 1% | OK |
| NL-02a | Ingeklemde balk, grote doorbuiging (hex20) | u/L PL2/EI=1 | 0.056433 - | 0.056305 | -0.23% | 1% | OK |
| NL-02a | Ingeklemde balk, grote doorbuiging (hex20) | v/L PL2/EI=2 | 0.49346 - | 0.49234 | -0.23% | 1% | OK |
| NL-02a | Ingeklemde balk, grote doorbuiging (hex20) | u/L PL2/EI=2 | 0.16064 - | 0.15993 | -0.44% | 1% | OK |
| NL-02a | Ingeklemde balk, grote doorbuiging (hex20) | v/L PL2/EI=3 | 0.60325 - | 0.60155 | -0.28% | 1% | OK |
| NL-02a | Ingeklemde balk, grote doorbuiging (hex20) | u/L PL2/EI=3 | 0.25442 - | 0.25297 | -0.57% | 1% | OK |
| NL-02b | Ingeklemde balk, grote doorbuiging (COQUE_3D) | v/L PL2/EI=1 | 0.30172 - | 0.30174 | +0.01% | 1% | OK |
| NL-02b | Ingeklemde balk, grote doorbuiging (COQUE_3D) | u/L PL2/EI=1 | 0.056433 - | 0.05644 | +0.01% | 1% | OK |
| NL-02b | Ingeklemde balk, grote doorbuiging (COQUE_3D) | v/L PL2/EI=2 | 0.49346 - | 0.49349 | +0.01% | 1% | OK |
| NL-02b | Ingeklemde balk, grote doorbuiging (COQUE_3D) | u/L PL2/EI=2 | 0.16064 - | 0.16066 | +0.01% | 1% | OK |
| NL-02b | Ingeklemde balk, grote doorbuiging (COQUE_3D) | v/L PL2/EI=3 | 0.60325 - | 0.60329 | +0.01% | 1% | OK |
| NL-02b | Ingeklemde balk, grote doorbuiging (COQUE_3D) | u/L PL2/EI=3 | 0.25442 - | 0.25445 | +0.01% | 1% | OK |
| NL-03a | Contact: twee balken, tips op elkaar (STANDARD) | tip gemiddeld | 7.6305e-05 m | 2.1102e-06 | -97.23% | 0.5% | BEKEND (KNOWN_BUGS 43) |
| NL-03a | Contact: twee balken, tips op elkaar (STANDARD) | tip boven | 7.6305e-05 m | 4.2203e-06 | -94.47% | 0.5% | BEKEND (KNOWN_BUGS 43) |
| NL-03a | Contact: twee balken, tips op elkaar (STANDARD) | contactkracht | 5 N | 1.9683e-08 | -100.00% | 0.5% | BEKEND (KNOWN_BUGS 43) |
| NL-03b | Contact: twee balken, tips op elkaar (PENALISATION, kn = 1e13 Pa/m) | tip gemiddeld | 7.6305e-05 m | 7.6300e-05 | -0.01% | 0.5% | OK |
| NL-03b | Contact: twee balken, tips op elkaar (PENALISATION, kn = 1e13 Pa/m) | tip boven | 7.6305e-05 m | 7.6361e-05 | +0.07% | 0.5% | OK |
| NL-03b | Contact: twee balken, tips op elkaar (PENALISATION, kn = 1e13 Pa/m) | contactkracht | 5 N | 4.9964 | -0.07% | 0.5% | OK |
| NL-03c | Contact-patchtest (STANDARD) | w contactvlak onder | 4.7619e-07 m | 4.7622e-07 | +0.01% | 0.5% | OK |
| NL-03c | Contact-patchtest (STANDARD) | w boven (A,A) | 9.5238e-07 m | 9.5245e-07 | +0.01% | 0.5% | OK |
| NL-03c | Contact-patchtest (STANDARD) | w boven (A/3,2A/3) | 9.5238e-07 m | 9.5245e-07 | +0.01% | 0.5% | OK |
| NL-03d | Contact-patchtest (PENALISATION) | w contactvlak onder | 4.7619e-07 m | 4.7622e-07 | +0.01% | 0.5% | OK |
| NL-03d | Contact-patchtest (PENALISATION) | w boven (A,A) | 1.9524e-06 m | 1.9524e-06 | +0.00% | 0.5% | OK |
| NL-03d | Contact-patchtest (PENALISATION) | w boven (A/3,2A/3) | 1.9524e-06 m | 1.9524e-06 | +0.00% | 0.5% | OK |
| NL-03d | Contact-patchtest (PENALISATION) | penetratie | 1.0000e-06 m | 1.0000e-06 | +0.00% | 0.5% | OK |
| NL-03e | Contact-patchtest (STANDARD, NCOTES) | w contactvlak onder | 4.7619e-07 m | 4.7622e-07 | +0.01% | 0.5% | OK |
| NL-03e | Contact-patchtest (STANDARD, NCOTES) | w boven (A,A) | 9.5238e-07 m | 9.5245e-07 | +0.01% | 0.5% | OK |
| NL-03e | Contact-patchtest (STANDARD, NCOTES) | w boven (A/3,2A/3) | 9.5238e-07 m | 9.5245e-07 | +0.01% | 0.5% | OK |
| NL-03f | Contact-patchtest (PENALISATION, NCOTES) | w contactvlak onder | 4.7619e-07 m | 4.7622e-07 | +0.01% | 0.5% | OK |
| NL-03f | Contact-patchtest (PENALISATION, NCOTES) | w boven (A,A) | 1.9524e-06 m | 1.9524e-06 | +0.00% | 0.5% | OK |
| NL-03f | Contact-patchtest (PENALISATION, NCOTES) | w boven (A/3,2A/3) | 1.9524e-06 m | 1.9524e-06 | +0.00% | 0.5% | OK |
| NL-03f | Contact-patchtest (PENALISATION, NCOTES) | penetratie | 1.0000e-06 m | 1.0000e-06 | +0.00% | 0.5% | OK |
| NL-04 | Trekstaaf, hardingscurve met E (tabblad) != helling van de curve | F t=1 (elastisch) | 10492 N | 10492 | +0.00% | 0.2% | OK |
| NL-04 | Trekstaaf, hardingscurve met E (tabblad) != helling van de curve | F t=2 (plastisch) | 24863 N | 24863 | -0.00% | 0.2% | OK |
| NL-04 | Trekstaaf, hardingscurve met E (tabblad) != helling van de curve | sigma_xx t=1 (E = 210 GPa) | 1.0495e+08 Pa | 1.0495e+08 | -0.00% | 0.2% | OK |
| NL-04b | Als NL-04 met een kinematische (lineaire) curve | F t=1 (elastisch) | 10492 N | 10492 | +0.00% | 0.2% | OK |
| NL-04b | Als NL-04 met een kinematische (lineaire) curve | F t=2 (plastisch) | 24863 N | 24863 | -0.00% | 0.2% | OK |
| NL-04b | Als NL-04 met een kinematische (lineaire) curve | sigma_xx t=1 (E = 210 GPa) | 1.0495e+08 Pa | 1.0495e+08 | +0.00% | 0.2% | OK |
| NL-04c | Als NL-04 met een curve zonder (0, 0) | F t=1 (elastisch) | 10492 N | 10492 | +0.00% | 0.2% | OK |
| NL-04c | Als NL-04 met een curve zonder (0, 0) | F t=2 (plastisch) | 24863 N | 24863 | -0.00% | 0.2% | OK |
| NL-04c | Als NL-04 met een curve zonder (0, 0) | sigma_xx t=1 (E = 210 GPa) | 1.0495e+08 Pa | 1.0495e+08 | -0.00% | 0.2% | OK |
| NL-04c | Als NL-04 met een curve zonder (0, 0) | sigma_xx t=1 t.o.v. Mecway 34 | 1.0498e+08 Pa | 1.0495e+08 | -0.03% | 0.2% | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | uitvoertijden = Mecway-stappen + knikken | 0 s | 0 | 0 | 1e-09 s | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | F t=1 (elastisch) | 20969 N | 20969 | +0.00% | 0.2% | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | F t=2 (plastisch) | 42955 N | 42955 | -0.00% | 0.2% | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | F t=3 (ontlast) | 12071 N | 12071 | -0.00% | 0.2% | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | sigma_xx t=2 | 4.3349e+08 Pa | 4.3349e+08 | -0.00% | 0.2% | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | p t=2 | 0.0078844 - | 0.0078844 | +0.00% | 0.2% | OK |
| NL-20 | Trekstaaf, Mecway-stap 0,4 s met knikken van de lasttabel ertussen | p t=3 (ontlast) | 0.0078844 - | 0.0078844 | +0.00% | 0.2% | OK |
| NL-30 | Contactdruk en -status, patchtest hex8 (CONT_NOEU) | contactpressure (gemiddeld) | 1.0000e+07 Pa | 1.0000e+07 | +0.00% | 0.5% | OK |
| NL-30 | Contactdruk en -status, patchtest hex8 (CONT_NOEU) | contactpressure (kleinste) | 1.0000e+07 Pa | 1.0000e+07 | +0.00% | 0.5% | OK |
| NL-30 | Contactdruk en -status, patchtest hex8 (CONT_NOEU) | contactstate (kleinste) | 1  | 1 | +0.00% | 1e-09  | OK |
| NL-30b | Contactdruk en -status, patchtest hex20 (PENALISATION, LAGS_C) | contactpressure (gemiddeld) | 1.0000e+07 Pa | 1.0000e+07 | +0.00% | 0.5% | OK |
| NL-30b | Contactdruk en -status, patchtest hex20 (PENALISATION, LAGS_C) | contactpressure (kleinste) | 1.0000e+07 Pa | 1.0000e+07 | +0.00% | 0.5% | OK |
| NL-30b | Contactdruk en -status, patchtest hex20 (PENALISATION, LAGS_C) | contactstate (kleinste) | 1  | 1 | +0.00% | 1e-09  | OK |
| NL-30c | Contactstatus open/gesloten, balktips (PENALISATION) | contactstate aan de tip | 1  | 1 | +0.00% | 1e-09  | OK |
| NL-30c | Contactstatus open/gesloten, balktips (PENALISATION) | contactstate begin zone | 0  | 0 | 0 | 1e-09  | OK |
| NL-30c | Contactstatus open/gesloten, balktips (PENALISATION) | contactpressure begin zone | 0 Pa | 447.72 | 447.72 | 2000 Pa | OK |
| NL-31 | Green-Lagrange-rek bij 5% rek (strain) | greenlagrangestrainxx | 0.05125  | 0.05125 | +0.00% | 0.01% | OK |
| NL-32 | Snedekrachten balk in STAT_NON_LINE | N (tensileforce) | 1000 N | 1000 | +0.00% | 0.0001% | OK |
| NL-32 | Snedekrachten balk in STAT_NON_LINE | V_v (sheary) | 200 N | 200 | +0.00% | 0.0001% | OK |
| NL-32 | Snedekrachten balk in STAT_NON_LINE | V_w (shearz) | -300 N | -300 | +0.00% | 0.0001% | OK |
| NL-32 | Snedekrachten balk in STAT_NON_LINE | T (torsion) | 50 N.m | 50 | +0.00% | 0.0001% | OK |
| NL-32 | Snedekrachten balk in STAT_NON_LINE | M_v inklemming (bendingmomv) | 300 N.m | 300 | +0.00% | 0.0001% | OK |
| NL-32 | Snedekrachten balk in STAT_NON_LINE | M_w midden (bendingmomw) | 100 N.m | 100 | -0.00% | 0.0001% | OK |
| NL-40 | Druk als formule in y en t naast een krachttabel | reactie Z bij t = 1 s | 9000 N | 9000 | -0.00% | 0.0001% | OK |
| NL-40 | Druk als formule in y en t naast een krachttabel | reactie Z bij t = 2 s | 18000 N | 18000 | -0.00% | 0.0001% | OK |
| NL-40 | Druk als formule in y en t naast een krachttabel | moment om X bij t = 2 s | 26000 N.m | 26000 | -0.00% | 0.0001% | OK |
| NL-50 | Hyperelastisch: kubus Neo Hooke, trek l = 1,5 | F (nominaal, l=1.5) | 211.11 N | 210.99 | -0.06% | 0.5% | OK |
| NL-50 | Hyperelastisch: kubus Neo Hooke, trek l = 1,5 | sigma_xx Cauchy (l=1.5) | 3.1667e+06 Pa | 3.1632e+06 | -0.11% | 0.5% | OK |
| NL-50b | Hyperelastisch: kubus Neo Hooke, druk l = 0,7 | F (nominaal, l=0.7) | -268.16 N | -268.09 | +0.03% | 0.5% | OK |
| NL-50b | Hyperelastisch: kubus Neo Hooke, druk l = 0,7 | sigma_xx Cauchy (l=0.7) | -1.8771e+06 Pa | -1.8772e+06 | -0.00% | 0.5% | OK |
| NL-51 | Hyperelastisch: kubus Mooney-Rivlin, trek l = 1,5 | F (nominaal, l=1.5) | 197.04 N | 196.94 | -0.05% | 0.5% | OK |
| NL-51 | Hyperelastisch: kubus Mooney-Rivlin, trek l = 1,5 | sigma_xx Cauchy (l=1.5) | 2.9556e+06 Pa | 2.9526e+06 | -0.10% | 0.5% | OK |
| NL-51b | Hyperelastisch: kubus Mooney-Rivlin, druk l = 0,7 | F (nominaal, l=0.7) | -291.15 N | -291.06 | +0.03% | 0.5% | OK |
| NL-51b | Hyperelastisch: kubus Mooney-Rivlin, druk l = 0,7 | sigma_xx Cauchy (l=0.7) | -2.0380e+06 Pa | -2.0381e+06 | -0.00% | 0.5% | OK |
| NL-52 | Hyperelastisch: Neo Hooke trek l = 1,5 in Dynamisch (impliciet), quasi-statisch | F (nominaal, l=1.5) | 211.11 N | 210.99 | -0.06% | 0.5% | OK |
| NL-52 | Hyperelastisch: Neo Hooke trek l = 1,5 in Dynamisch (impliciet), quasi-statisch | sigma_xx Cauchy (l=1.5) | 3.1667e+06 Pa | 3.1632e+06 | -0.11% | 0.5% | OK |
| NL-53 | Hyperelastisch: Neo Hooke trek l = 1,5 in Dynamisch (expliciet), 20 ms | F (nominaal, l=1.5) | 211.11 N | 212.7 | +0.75% | 2% | OK |
| NL-53 | Hyperelastisch: Neo Hooke trek l = 1,5 in Dynamisch (expliciet), 20 ms | sigma_xx Cauchy (l=1.5) | 3.1667e+06 Pa | 3.1887e+06 | +0.70% | 2% | OK |
| NL-70 | Vrije staaf, temperatuur met tijdstabel (quasi-static) | u_x(L) op t = 0.5 s | 6.6000e-05 m | 6.6000e-05 | +0.00% | 0.0001% | OK |
| NL-70 | Vrije staaf, temperatuur met tijdstabel (quasi-static) | u_x(L) op t = 0.5 s t.o.v. Mecway (CCX) | 6.6000e-05 m | 6.6000e-05 | +0.00% | 0.01% | OK |
| NL-70 | Vrije staaf, temperatuur met tijdstabel (quasi-static) | u_x(L) op t = 1 s | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| NL-70 | Vrije staaf, temperatuur met tijdstabel (quasi-static) | u_x(L) op t = 1 s t.o.v. Mecway (CCX) | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.01% | OK |
| NL-70 | Vrije staaf, temperatuur met tijdstabel (quasi-static) | u_x(L) op t = 2 s | 6.0000e-05 m | 6.0000e-05 | +0.00% | 0.0001% | OK |
| NL-70 | Vrije staaf, temperatuur met tijdstabel (quasi-static) | u_x(L) op t = 2 s t.o.v. Mecway (CCX) | 6.0000e-05 m | 6.0000e-05 | +0.00% | 0.01% | OK |
| NL-70b | Als NL-70 met de standaard GROT_GDEP (Green-Lagrange) | u_x(L) op t = 0.5 s | 6.5978e-05 m | 6.5978e-05 | +0.00% | 0.0001% | OK |
| NL-70b | Als NL-70 met de standaard GROT_GDEP (Green-Lagrange) | u_x(L) op t = 1 s | 1.1993e-04 m | 1.1993e-04 | +0.00% | 0.0001% | OK |
| NL-70b | Als NL-70 met de standaard GROT_GDEP (Green-Lagrange) | u_x(L) op t = 2 s | 5.9982e-05 m | 5.9982e-05 | +0.00% | 0.0001% | OK |
| NL-71 | Staaf ingeklemd in x, temperatuur met tijdstabel (quasi-static) | sigma_xx op t = 0.5 s | -1.3860e+08 Pa | -1.3860e+08 | -0.00% | 0.0001% | OK |
| NL-71 | Staaf ingeklemd in x, temperatuur met tijdstabel (quasi-static) | sigma_xx op t = 0.5 s t.o.v. Mecway (CCX) | -1.3831e+08 Pa | -1.3860e+08 | -0.21% | 0.5% | OK |
| NL-71 | Staaf ingeklemd in x, temperatuur met tijdstabel (quasi-static) | sigma_xx op t = 1 s | -2.5200e+08 Pa | -2.5200e+08 | -0.00% | 0.0001% | OK |
| NL-71 | Staaf ingeklemd in x, temperatuur met tijdstabel (quasi-static) | sigma_xx op t = 1 s t.o.v. Mecway (CCX) | -2.5106e+08 Pa | -2.5200e+08 | -0.38% | 0.5% | OK |
| NL-71 | Staaf ingeklemd in x, temperatuur met tijdstabel (quasi-static) | sigma_xx op t = 2 s | -1.2600e+08 Pa | -1.2600e+08 | -0.00% | 0.0001% | OK |
| NL-71 | Staaf ingeklemd in x, temperatuur met tijdstabel (quasi-static) | sigma_xx op t = 2 s t.o.v. Mecway (CCX) | -1.2576e+08 Pa | -1.2600e+08 | -0.19% | 0.5% | OK |
| NL-72 | Vrije staaf, temperatuur als formule in t (quasi-static) | u_x(L) op t = 1 s | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| NL-72 | Vrije staaf, temperatuur als formule in t (quasi-static) | u_x(L) op t = 1 s t.o.v. Mecway (CCX) | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.01% | OK |
| NL-72 | Vrije staaf, temperatuur als formule in t (quasi-static) | u_x(L) op t = 2 s | 2.4000e-04 m | 2.4000e-04 | +0.00% | 0.0001% | OK |
| NL-72 | Vrije staaf, temperatuur als formule in t (quasi-static) | u_x(L) op t = 2 s t.o.v. Mecway (CCX) | 2.4000e-04 m | 2.4000e-04 | +0.00% | 0.01% | OK |
| NL-73a | Vrije staaf, constante temperatuur (quasi-static: vanaf de eerste stap) | u_x(L) op t = 0.25 s | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| NL-73a | Vrije staaf, constante temperatuur (quasi-static: vanaf de eerste stap) | u_x(L) op t = 0.25 s t.o.v. Mecway (CCX) | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.01% | OK |
| NL-73a | Vrije staaf, constante temperatuur (quasi-static: vanaf de eerste stap) | u_x(L) op t = 1 s | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| NL-73b | Vrije staaf, constante temperatuur (zonder quasi-static: oplopend) | u_x(L) op t = 0.5 s | 6.0000e-05 m | 6.0000e-05 | +0.00% | 0.0001% | OK |
| NL-73b | Vrije staaf, constante temperatuur (zonder quasi-static: oplopend) | u_x(L) op t = 1 s | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| NL-73b | Vrije staaf, constante temperatuur (zonder quasi-static: oplopend) | u_x(L) op t = 1 s t.o.v. Mecway (CCX) | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.01% | OK |
| NL-74 | Vrije staaf: temperatuur met tijdstabel op x = 0 en Node temperature op x = L (quasi-static) | gemiddelde u_x op x = L, t = 0.5 s | 3.8250e-05 m | 3.8250e-05 | +0.00% | 0.0001% | OK |
| NL-74 | Vrije staaf: temperatuur met tijdstabel op x = 0 en Node temperature op x = L (quasi-static) | gemiddelde u_x op x = L, t = 2 s | 3.7500e-05 m | 3.7500e-05 | +0.00% | 0.0001% | OK |
| NL-75 | Vrije staaf, temperatuur met tijdstabel zonder quasi-static (waarde op t = 1 s) | u_x(L) op t = 1 s | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| NL-75 | Vrije staaf, temperatuur met tijdstabel zonder quasi-static (waarde op t = 1 s) | u_x(L) op t = 1 s t.o.v. Mecway (CCX) | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.01% | OK |
| NL-75 | Vrije staaf, temperatuur met tijdstabel zonder quasi-static (waarde op t = 1 s) | laatste rekentijd | 1 s | 1 | +0.00% | 1e-07% | OK |
| NL-80 | POU_D_T_GD: ingeklemde balk, kleine eindkracht (Timoshenko) | doorbuiging tip | 9.5246e-04 m | 9.5231e-04 | -0.02% | 0.1% | OK |
| NL-80b | POU_D_T_GD in lineair statisch: wordt POU_D_T | doorbuiging tip | 9.5246e-04 m | 9.5246e-04 | +0.00% | 0.1% | OK |
| NL-80c | POU_D_T_GD: constante eindkracht en eindmoment (geen tijdtabel) | doorbuiging tip | 0.0016667 m | 0.0016666 | -0.01% | 0.1% | OK |
| NL-80c | POU_D_T_GD: constante eindkracht en eindmoment (geen tijdtabel) | tiprotatie | 0.0028571 rad | 0.0028571 | -0.00% | 0.1% | OK |
| NL-81 | POU_D_T_GD: zuivere buiging tot 90 graden | tip verplaatsing langs de as | -0.36338 m | -0.36334 | +0.01% | 0.1% | OK |
| NL-81 | POU_D_T_GD: zuivere buiging tot 90 graden | tip verplaatsing dwars | 0.63662 m | 0.63666 | +0.01% | 0.1% | OK |
| NL-81 | POU_D_T_GD: zuivere buiging tot 90 graden | tiprotatie | 1.5708 rad | 1.5708 | +0.00% | 0.1% | OK |
| NL-81 | POU_D_T_GD: zuivere buiging tot 90 graden | bendingmomw (min. over de elementen) | 549.78 N.m | 549.78 | +0.00% | 0.01% | OK |
| NL-81 | POU_D_T_GD: zuivere buiging tot 90 graden | bendingmomw (max. over de elementen) | 549.78 N.m | 549.78 | +0.00% | 0.01% | OK |
| NL-81 | POU_D_T_GD: zuivere buiging tot 90 graden | tensileforce (grootste |N|) | 0 N | 1.3989e-06 | 1.3989e-06 | 0.05 N | OK |
| NL-82 | POU_D_T_GD: kolom met beginkromming, tweede-orde-versterking | totale tipuitwijking / e0 | 2 - | 1.9996 | -0.02% | 0.1% | OK |
| NL-82 | POU_D_T_GD: kolom met beginkromming, tweede-orde-versterking | totale tipuitwijking / e0 t.o.v. Mecway 34 + CCX | 1.9995 - | 1.9996 | +0.00% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_y t=1 | 0.30174 m | 0.30171 | -0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_x t=1 | -0.056438 m | -0.056419 | +0.03% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tiprotatie t=1 | 0.46135 rad | 0.46136 | +0.00% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_y t=2 | 0.49349 m | 0.49345 | -0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_x t=2 | -0.16065 m | -0.16061 | +0.02% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tiprotatie t=2 | 0.78174 rad | 0.7818 | +0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_y t=3 | 0.6033 m | 0.60327 | -0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_x t=3 | -0.25443 m | -0.25438 | +0.02% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tiprotatie t=3 | 0.986 rad | 0.9861 | +0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | bendingmomw element 1 t=3 (statica vervormd) | 769.78 N.m | 769.78 | +0.00% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | sheary laatste element t=3 (statica vervormd) | 579.73 N | 579.77 | +0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tensileforce laatste element t=3 (statica vervormd) | 875.45 N | 875.42 | -0.00% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | reactiekracht Y | -1050 N | -1050 | +0.00% | 0.0001% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_y t=1 t.o.v. Mecway 34 + CCX | 0.30168 m | 0.30171 | +0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_x t=1 t.o.v. Mecway 34 + CCX | -0.056421 m | -0.056419 | +0.00% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_y t=2 t.o.v. Mecway 34 + CCX | 0.49339 m | 0.49345 | +0.01% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_x t=2 t.o.v. Mecway 34 + CCX | -0.16061 m | -0.16061 | -0.00% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_y t=3 t.o.v. Mecway 34 + CCX | 0.60317 m | 0.60327 | +0.02% | 0.1% | OK |
| NL-83 | POU_D_T_GD: elastica, eindkracht van vaste richting (PL^2/EI = 1, 2, 3) | tip u_x t=3 t.o.v. Mecway 34 + CCX | -0.25436 m | -0.25438 | -0.01% | 0.1% | OK |
| NL-84 | POU_D_T_GD: zuivere buiging tot 90 graden, line3 | tip verplaatsing langs de as | -0.36338 m | -0.36334 | +0.01% | 0.1% | OK |
| NL-84 | POU_D_T_GD: zuivere buiging tot 90 graden, line3 | tip verplaatsing dwars | 0.63662 m | 0.63666 | +0.01% | 0.1% | OK |
| NL-84 | POU_D_T_GD: zuivere buiging tot 90 graden, line3 | tiprotatie | 1.5708 rad | 1.5708 | +0.00% | 0.1% | OK |
| NL-84 | POU_D_T_GD: zuivere buiging tot 90 graden, line3 | bendingmomw (min. over de elementen) | 549.78 N.m | 549.78 | +0.00% | 0.01% | OK |
| NL-84 | POU_D_T_GD: zuivere buiging tot 90 graden, line3 | bendingmomw (max. over de elementen) | 549.78 N.m | 549.78 | +0.00% | 0.01% | OK |
| NL-84 | POU_D_T_GD: zuivere buiging tot 90 graden, line3 | tensileforce (grootste |N|) | 0 N | 1.3989e-06 | 1.3989e-06 | 0.05 N | OK |
| NL-85 | POU_D_T_GD: zuivere buiging tot 90 graden om de zwakke as uit een orientatiekaart | tip verplaatsing langs de as | -0.36338 m | -0.36334 | +0.01% | 0.1% | OK |
| NL-85 | POU_D_T_GD: zuivere buiging tot 90 graden om de zwakke as uit een orientatiekaart | tip verplaatsing dwars | -0.63662 m | -0.63666 | -0.01% | 0.1% | OK |
| NL-85 | POU_D_T_GD: zuivere buiging tot 90 graden om de zwakke as uit een orientatiekaart | tiprotatie | 1.5708 rad | 1.5708 | +0.00% | 0.1% | OK |
| NL-85 | POU_D_T_GD: zuivere buiging tot 90 graden om de zwakke as uit een orientatiekaart | bendingmomw (min. over de elementen) | -549.78 N.m | -549.78 | -0.00% | 0.01% | OK |
| NL-85 | POU_D_T_GD: zuivere buiging tot 90 graden om de zwakke as uit een orientatiekaart | bendingmomw (max. over de elementen) | -549.78 N.m | -549.78 | -0.00% | 0.01% | OK |
| NL-85 | POU_D_T_GD: zuivere buiging tot 90 graden om de zwakke as uit een orientatiekaart | tensileforce (grootste |N|) | 0 N | 1.2497e-06 | 1.2497e-06 | 0.05 N | OK |
| NL-86 | POU_D_T_GD: centrifugaalkracht op een radiale staaf | tipverlenging | 1.2298e-05 m | 1.2296e-05 | -0.02% | 0.1% | OK |
| NL-86 | POU_D_T_GD: centrifugaalkracht op een radiale staaf | reactiekracht X | -774.76 N | -774.76 | -0.00% | 0.1% | OK |
| NL-86b | POU_D_T_GD: centrifugaalkracht op een balk en een truss (BARRE) | tipverlenging truss | 1.2298e-05 m | 1.2302e-05 | +0.03% | 0.1% | OK |
| NL-86b | POU_D_T_GD: centrifugaalkracht op een balk en een truss (BARRE) | reactiekracht X truss | -774.76 N | -774.76 | +0.00% | 0.1% | OK |
| NL-87 | POU_D_T_GD: line pressure en zwaartekracht (configuratie GQ) | doorbuiging tip | -0.0031622 m | -0.0031622 | +0.00% | 0.1% | OK |
| NL-87 | POU_D_T_GD: line pressure en zwaartekracht (configuratie GQ) | reactiekracht Z | 35.402 N | 35.402 | +0.00% | 0.0001% | OK |
| NL-87b | POU_D_T_GD: zwaartekracht (configuratie G, line pressure onderdrukt) | doorbuiging tip | -0.0013757 m | -0.0013757 | +0.00% | 0.1% | OK |
| NL-87b | POU_D_T_GD: zwaartekracht (configuratie G, line pressure onderdrukt) | reactiekracht Z | 15.402 N | 15.402 | -0.00% | 0.0001% | OK |
| NL-88 | POU_D_T_GD: vrije thermische uitzetting | tipverlenging | 0.0012 m | 0.0012 | -0.00% | 0.0001% | OK |
| NL-89 | POU_D_T_GD: line pressure als formule in x en t | doorbuiging tip t=1 | -0.001965 m | -0.0019645 | +0.03% | 0.1% | OK |
| NL-89 | POU_D_T_GD: line pressure als formule in x en t | doorbuiging tip t=0,5 | -9.8251e-04 m | -9.8223e-04 | +0.03% | 0.1% | OK |
| NL-89 | POU_D_T_GD: line pressure als formule in x en t | reactiekracht Z t=1 | 15 N | 15 | +0.00% | 0.0001% | OK |
| NL-90 | POU_D_T_GD: flexible joint met U, V en W vrij (kogelscharnier), grote eindkracht | tip u_y | 0.49349 m | 0.49345 | -0.01% | 0.1% | OK |
| NL-90 | POU_D_T_GD: flexible joint met U, V en W vrij (kogelscharnier), grote eindkracht | tip u_x | -0.16065 m | -0.16061 | +0.02% | 0.1% | OK |
| NL-90 | POU_D_T_GD: flexible joint met U, V en W vrij (kogelscharnier), grote eindkracht | tiprotatie | 0.78174 rad | 0.7818 | +0.01% | 0.1% | OK |
| NL-90 | POU_D_T_GD: flexible joint met U, V en W vrij (kogelscharnier), grote eindkracht | reactiekracht Y wortel 2 | -700 N | -700 | -0.00% | 0.1% | OK |
| NL-90b | POU_D_T_GD: flexible joint met U, V en W vrij, torsie tot 90 graden | tiprotatie om X | 1.5708 rad | 1.5708 | -0.00% | 0.01% | OK |
| NL-90b | POU_D_T_GD: flexible joint met U, V en W vrij, torsie tot 90 graden | reactiemoment X wortel 1 | -177.62 N.m | -177.62 | +0.00% | 0.01% | OK |
| NL-90b | POU_D_T_GD: flexible joint met U, V en W vrij, torsie tot 90 graden | reactiemoment X wortel 2 | 0 N.m | 0 | 0 | 0.000177621 N.m | OK |

*NL-03a: diagnose <A>_ALARM; MECANONLINE9_4; BRIDGE_ONVOLLEDIG*

## Responsspectrum

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f1 | 5.5274 Hz | 5.5274 | +0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f2 | 10.887 Hz | 10.887 | -0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f3 | 15.915 Hz | 15.915 | -0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f4 | 20.461 Hz | 20.461 | +0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f5 | 24.384 Hz | 24.384 | -0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f6 | 27.566 Hz | 27.566 | -0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f7 | 29.911 Hz | 29.911 | +0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | f8 | 31.347 Hz | 31.347 | +0.00% | 0.01% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | ACCE_ABSOLU DX A | 1.1364 m/s2 | 1.1364 | -0.00% | 1% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | ACCE_ABSOLU DX P1 | 10.45 m/s2 | 10.45 | +0.00% | 1% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | ACCE_ABSOLU DX P2 | 19.03 m/s2 | 19.03 | -0.00% | 1% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | ACCE_ABSOLU DX P3 | 25.318 m/s2 | 25.318 | +0.00% | 1% | OK |
| SP-01 | sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS | ACCE_ABSOLU DX P4 | 28.945 m/s2 | 28.945 | +0.00% | 1% | OK |
| SP-02 | Twee massa's, spectrumtabel (periode), SRSS | u m1 | 0.0047517 m | 0.0047517 | -0.00% | 0.5% | OK |
| SP-02 | Twee massa's, spectrumtabel (periode), SRSS | u m2 | 0.024381 m | 0.024381 | -0.00% | 0.5% | OK |
| SP-02 | Twee massa's, spectrumtabel (periode), SRSS | reactie grond | 475.17 N | 475.17 | -0.00% | 0.5% | OK |
| SP-02 | Twee massa's, spectrumtabel (periode), SRSS | totale reactie (log) | 475.17 N | 475.17 | +0.00% | 0.5% | OK |
| SP-02 | Twee massa's, spectrumtabel (periode), SRSS | abs. versnelling m2 | 20.75 m/s2 | 20.75 | -0.00% | 0.5% | OK |
| SP-03 | Twee massa's, spectrumtabel (periode), CQC | u m1 | 0.0051277 m | 0.0051277 | +0.00% | 0.5% | OK |
| SP-03 | Twee massa's, spectrumtabel (periode), CQC | u m2 | 0.022806 m | 0.022806 | -0.00% | 0.5% | OK |
| SP-03 | Twee massa's, spectrumtabel (periode), CQC | reactie grond | 512.77 N | 512.77 | +0.00% | 0.5% | OK |
| SP-03 | Twee massa's, spectrumtabel (periode), CQC | totale reactie (log) | 512.77 N | 512.77 | -0.00% | 0.5% | OK |
| SP-03 | Twee massa's, spectrumtabel (periode), CQC | abs. versnelling m2 | 19.057 m/s2 | 19.057 | +0.00% | 0.5% | OK |
| SP-04 | Twee massa's, 1 mode met missing mass | u m1 | 0.0045461 m | 0.0045461 | -0.00% | 0.5% | OK |
| SP-04 | Twee massa's, 1 mode met missing mass | u m2 | 0.023976 m | 0.023976 | -0.00% | 0.5% | OK |
| SP-04 | Twee massa's, 1 mode met missing mass | reactie grond | 454.61 N | 454.61 | -0.00% | 0.5% | OK |
| SP-04 | Twee massa's, 1 mode met missing mass | abs. versnelling m2 | 20.07 m/s2 | 20.07 | -0.00% | 0.5% | OK |
| SP-05 | Twee massa's, 1 mode zonder missing mass | u m2 | 0.022187 m | 0.022187 | -0.00% | 0.5% | OK |
| SP-05 | Twee massa's, 1 mode zonder missing mass | reactie grond | 354.99 N | 354.99 | +0.00% | 0.5% | OK |
| SP-06a | Massa aan schuine veren, spectra X en Y, richtingen SRSS | u x | 0.0022775 m | 0.0022775 | +0.00% | 0.5% | OK |
| SP-06a | Massa aan schuine veren, spectra X en Y, richtingen SRSS | u y | 0.0034505 m | 0.0034505 | +0.00% | 0.5% | OK |
| SP-06b | Massa aan schuine veren, spectra X en Y, richtingen 100-30-30 | u x | 0.0022628 m | 0.0022628 | -0.00% | 0.5% | OK |
| SP-06b | Massa aan schuine veren, spectra X en Y, richtingen 100-30-30 | u y | 0.0033308 m | 0.0033308 | +0.00% | 0.5% | OK |
| SP-06c | Massa aan schuine veren, spectra X en Y, richtingen 100-40-40 | u x | 0.0023921 m | 0.0023921 | +0.00% | 0.5% | OK |
| SP-06c | Massa aan schuine veren, spectra X en Y, richtingen 100-40-40 | u y | 0.0035484 m | 0.0035484 | +0.00% | 0.5% | OK |
| SP-07 | Ingeklemde volumebalk hex20, vlak spectrum, mode 1 | f1 | 16.71 Hz | 16.745 | +0.20% | 0.5% | OK |
| SP-07 | Ingeklemde volumebalk hex20, vlak spectrum, mode 1 | u tip | 1.566 m/s2 | 1.5657 | -0.02% | 0.5% | OK |
| SP-07 | Ingeklemde volumebalk hex20, vlak spectrum, mode 1 | stressxx halverwege | 3.9258e+09 Pa/s2 | 3.9405e+09 | +0.38% | 2% | OK |
| SP-07 | Ingeklemde volumebalk hex20, vlak spectrum, mode 1 | vonmises halverwege | 3.9258e+09 Pa/s2 | 3.9407e+09 | +0.38% | 2% | OK |
| SP-07 | Ingeklemde volumebalk hex20, vlak spectrum, mode 1 | totale reactie Y | 2.8876 N | 2.8843 | -0.12% | 1% | OK |
| SP-07 | Ingeklemde volumebalk hex20, vlak spectrum, mode 1 | abs. versnelling tip | 1.6651 m/s2 | 1.6648 | -0.02% | 0.5% | OK |

## Thermisch

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| TH-01a | Wand met warmteproductie, T vast (hex8, 8 el.) | T_max - T0 (x = L/2) | 25 K | 25 | -0.00% | 0.001% | OK |
| TH-01a | Wand met warmteproductie, T vast (hex8, 8 el.) | T - T0 (x = L/4) | 18.75 K | 18.75 | -0.00% | 0.001% | OK |
| TH-01a | Wand met warmteproductie, T vast (hex8, 8 el.) | flux x (x = L/4) | -25000 W/m² | -25000 | +0.00% | 0.001% | OK |
| TH-01b | Wand met warmteproductie, T vast (hex20, 2 el.) | T_max - T0 (x = L/2) | 25 K | 25 | +0.00% | 0.001% | OK |
| TH-01b | Wand met warmteproductie, T vast (hex20, 2 el.) | T - T0 (x = L/4, middenknoop) | 18.75 K | 18.75 | +0.00% | 0.001% | OK |
| TH-01b | Wand met warmteproductie, T vast (hex20, 2 el.) | flux x (x = 0) | -50000 W/m² | -50000 | -0.00% | 0.001% | OK |
| TH-01c | Wand, T vast links, convectie rechts (Bi = 0,5) | T(L) - Tinf | 66.667 K | 66.667 | +0.00% | 0.001% | OK |
| TH-01c | Wand, T vast links, convectie rechts (Bi = 0,5) | flux x | 16667 W/m² | 16667 | -0.00% | 0.001% | OK |
| TH-01d | Wand met warmteproductie, geisoleerd + convectie | Ts - Tinf (x = L) | 100 K | 100 | +0.00% | 0.001% | OK |
| TH-01d | Wand met warmteproductie, geisoleerd + convectie | T(0) - Ts | 25 K | 25 | +0.00% | 0.001% | OK |
| TH-01d | Wand met warmteproductie, geisoleerd + convectie | T(L/2) - Tinf | 118.75 K | 118.75 | +0.00% | 0.001% | OK |
| TH-01e | Vin als schaal (quad8, convectie op het vlak) | T(L) - Tinf (uiteinde) | 39.477 K | 39.477 | +0.00% | 0.1% | OK |
| TH-01e | Vin als schaal (quad8, convectie op het vlak) | T(L/2) - Tinf | 52.47 K | 52.47 | +0.00% | 0.1% | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | T-Ti x=4 mm t=10 s | 77.73 K | 77.676 | -0.07% | 0.5 K | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | T-Ti x=8 mm t=10 s | 57.161 K | 57.065 | -0.17% | 0.5 K | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | T-Ti x=16 mm t=10 s | 25.79 K | 25.67 | -0.46% | 0.5 K | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | T-Ti x=4 mm t=40 s | 88.754 K | 88.747 | -0.01% | 0.5 K | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | T-Ti x=8 mm t=40 s | 77.73 K | 77.716 | -0.02% | 0.5 K | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | T-Ti x=16 mm t=40 s | 57.161 K | 57.137 | -0.04% | 0.5 K | OK |
| TH-02a | Half-oneindig lichaam, theta 0,57 (standaard) | zelfde schema 1D x=8 mm t=10 s | 57.065 K | 57.065 | -0.00% | 0.0001 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | T-Ti x=4 mm t=10 s | 77.73 K | 77.68 | -0.06% | 0.5 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | T-Ti x=8 mm t=10 s | 57.161 K | 57.07 | -0.16% | 0.5 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | T-Ti x=16 mm t=10 s | 25.79 K | 25.668 | -0.47% | 0.5 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | T-Ti x=4 mm t=40 s | 88.754 K | 88.747 | -0.01% | 0.5 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | T-Ti x=8 mm t=40 s | 77.73 K | 77.717 | -0.02% | 0.5 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | T-Ti x=16 mm t=40 s | 57.161 K | 57.138 | -0.04% | 0.5 K | OK |
| TH-02b | Half-oneindig lichaam, theta 0,5 (Crank-Nicolson) | zelfde schema 1D x=8 mm t=10 s | 57.07 K | 57.07 | +0.00% | 0.0001 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | T-Ti x=4 mm t=10 s | 77.73 K | 77.654 | -0.10% | 0.5 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | T-Ti x=8 mm t=10 s | 57.161 K | 57.037 | -0.22% | 0.5 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | T-Ti x=16 mm t=10 s | 25.79 K | 25.685 | -0.41% | 0.5 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | T-Ti x=4 mm t=40 s | 88.754 K | 88.744 | -0.01% | 0.5 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | T-Ti x=8 mm t=40 s | 77.73 K | 77.711 | -0.02% | 0.5 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | T-Ti x=16 mm t=40 s | 57.161 K | 57.13 | -0.05% | 0.5 K | OK |
| TH-02c | Half-oneindig lichaam, theta 1,0 (Euler impliciet) | zelfde schema 1D x=8 mm t=10 s | 57.037 K | 57.037 | -0.00% | 0.0001 K | OK |
| TH-02d1 | Half-oneindig lichaam, dt = 0.4 s, theta 0,5 | T-Ti x=4 mm t=10 s | 77.73 K | 77.536 | -0.25% | 1 K | OK |
| TH-02d1 | Half-oneindig lichaam, dt = 0.4 s, theta 0,5 | T-Ti x=8 mm t=10 s | 57.161 K | 56.779 | -0.67% | 1 K | OK |
| TH-02d1 | Half-oneindig lichaam, dt = 0.4 s, theta 0,5 | T-Ti x=16 mm t=10 s | 25.79 K | 25.306 | -1.88% | 1 K | OK |
| TH-02d1 | Half-oneindig lichaam, dt = 0.4 s, theta 0,5 | zelfde schema 1D x=8 mm t=10 s | 56.779 K | 56.779 | +0.00% | 0.0001 K | OK |
| TH-02d2 | Half-oneindig lichaam, dt = 0.4 s, theta 1,0 | T-Ti x=4 mm t=10 s | 77.73 K | 77.412 | -0.41% | 1 K | OK |
| TH-02d2 | Half-oneindig lichaam, dt = 0.4 s, theta 1,0 | T-Ti x=8 mm t=10 s | 57.161 K | 56.646 | -0.90% | 1 K | OK |
| TH-02d2 | Half-oneindig lichaam, dt = 0.4 s, theta 1,0 | T-Ti x=16 mm t=10 s | 25.79 K | 25.387 | -1.56% | 1 K | OK |
| TH-02d2 | Half-oneindig lichaam, dt = 0.4 s, theta 1,0 | zelfde schema 1D x=8 mm t=10 s | 56.646 K | 56.646 | -0.00% | 0.0001 K | OK |
| TH-02e1 | Half-oneindig lichaam, dt = 0.2 s, theta 0,5 | T-Ti x=4 mm t=10 s | 77.73 K | 77.625 | -0.13% | 1 K | OK |
| TH-02e1 | Half-oneindig lichaam, dt = 0.2 s, theta 0,5 | T-Ti x=8 mm t=10 s | 57.161 K | 56.973 | -0.33% | 1 K | OK |
| TH-02e1 | Half-oneindig lichaam, dt = 0.2 s, theta 0,5 | T-Ti x=16 mm t=10 s | 25.79 K | 25.548 | -0.94% | 1 K | OK |
| TH-02e1 | Half-oneindig lichaam, dt = 0.2 s, theta 0,5 | zelfde schema 1D x=8 mm t=10 s | 56.973 K | 56.973 | +0.00% | 0.0001 K | OK |
| TH-02e2 | Half-oneindig lichaam, dt = 0.2 s, theta 1,0 | T-Ti x=4 mm t=10 s | 77.73 K | 77.574 | -0.20% | 1 K | OK |
| TH-02e2 | Half-oneindig lichaam, dt = 0.2 s, theta 1,0 | T-Ti x=8 mm t=10 s | 57.161 K | 56.907 | -0.44% | 1 K | OK |
| TH-02e2 | Half-oneindig lichaam, dt = 0.2 s, theta 1,0 | T-Ti x=16 mm t=10 s | 25.79 K | 25.585 | -0.80% | 1 K | OK |
| TH-02e2 | Half-oneindig lichaam, dt = 0.2 s, theta 1,0 | zelfde schema 1D x=8 mm t=10 s | 56.907 K | 56.907 | +0.00% | 0.0001 K | OK |
| TH-02f1 | Half-oneindig lichaam, dt = 0.05 s, theta 0,5 | T-Ti x=4 mm t=10 s | 77.73 K | 77.707 | -0.03% | 1 K | OK |
| TH-02f1 | Half-oneindig lichaam, dt = 0.05 s, theta 0,5 | T-Ti x=8 mm t=10 s | 57.161 K | 57.118 | -0.07% | 1 K | OK |
| TH-02f1 | Half-oneindig lichaam, dt = 0.05 s, theta 0,5 | T-Ti x=16 mm t=10 s | 25.79 K | 25.728 | -0.24% | 1 K | OK |
| TH-02f1 | Half-oneindig lichaam, dt = 0.05 s, theta 0,5 | zelfde schema 1D x=8 mm t=10 s | 57.118 K | 57.118 | -0.00% | 0.0001 K | OK |
| TH-02f2 | Half-oneindig lichaam, dt = 0.05 s, theta 1,0 | T-Ti x=4 mm t=10 s | 77.73 K | 77.694 | -0.05% | 1 K | OK |
| TH-02f2 | Half-oneindig lichaam, dt = 0.05 s, theta 1,0 | T-Ti x=8 mm t=10 s | 57.161 K | 57.102 | -0.10% | 1 K | OK |
| TH-02f2 | Half-oneindig lichaam, dt = 0.05 s, theta 1,0 | T-Ti x=16 mm t=10 s | 25.79 K | 25.736 | -0.21% | 1 K | OK |
| TH-02f2 | Half-oneindig lichaam, dt = 0.05 s, theta 1,0 | zelfde schema 1D x=8 mm t=10 s | 57.102 K | 57.102 | -0.00% | 0.0001 K | OK |
| TH-02g | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.5 | T-Ti x=1 mm t=4 s | 91.098 K | 93.892 | +3.07% | 5 K | OK |
| TH-02g | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.5 | T-Ti x=8 mm t=4 s | 37.109 K | 34.136 | -8.01% | 5 K | OK |
| TH-02g | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.5 | T-Ti x=16 mm t=4 s | 7.3638 K | 5.3569 | -27.25% | 5 K | OK |
| TH-02g | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.5 | zelfde schema 1D x=8 mm t=4 s | 34.136 K | 34.136 | +0.00% | 0.0001 K | OK |
| TH-02h | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.57 | T-Ti x=1 mm t=4 s | 91.098 K | 91.711 | +0.67% | 5 K | OK |
| TH-02h | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.57 | T-Ti x=8 mm t=4 s | 37.109 K | 33.993 | -8.40% | 5 K | OK |
| TH-02h | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.57 | T-Ti x=16 mm t=4 s | 7.3638 K | 5.7293 | -22.20% | 5 K | OK |
| TH-02h | Half-oneindig lichaam, grove stap dt = 1 s, theta 0.57 | zelfde schema 1D x=8 mm t=4 s | 33.993 K | 33.993 | +0.00% | 0.0001 K | OK |
| TH-02i | Half-oneindig lichaam, grove stap dt = 1 s, theta 1 | T-Ti x=1 mm t=4 s | 91.098 K | 90.158 | -1.03% | 5 K | OK |
| TH-02i | Half-oneindig lichaam, grove stap dt = 1 s, theta 1 | T-Ti x=8 mm t=4 s | 37.109 K | 34.063 | -8.21% | 5 K | OK |
| TH-02i | Half-oneindig lichaam, grove stap dt = 1 s, theta 1 | T-Ti x=16 mm t=4 s | 7.3638 K | 7.5717 | +2.82% | 5 K | OK |
| TH-02i | Half-oneindig lichaam, grove stap dt = 1 s, theta 1 | zelfde schema 1D x=8 mm t=4 s | 34.063 K | 34.063 | +0.00% | 0.0001 K | OK |
| TH-04a | Verlijmd contact (tie), twee blokken, conform | T naad (kant A) | 350 K | 350 | +0.00% | 0.0001% | OK |
| TH-04a | Verlijmd contact (tie), twee blokken, conform | T naad (kant B) | 350 K | 350 | +0.00% | 0.0001% | OK |
| TH-04a | Verlijmd contact (tie), twee blokken, conform | T (x = L/5) | 320 K | 320 | +0.00% | 0.0001% | OK |
| TH-04a | Verlijmd contact (tie), twee blokken, conform | flux x (x = 3L/4) | -50000 W/m² | -50000 | +0.00% | 0.001% | OK |
| TH-04b | Verlijmd contact (constraint eq.), niet-conform | T naad (kant A) | 350 K | 350.07 | +0.02% | 0.1% | OK |
| TH-04b | Verlijmd contact (constraint eq.), niet-conform | T naad (kant B) | 350 K | 350.07 | +0.02% | 0.1% | OK |
| TH-04b | Verlijmd contact (constraint eq.), niet-conform | T (x = L/5) | 320 K | 319.99 | -0.00% | 0.1% | OK |
| TH-04b | Verlijmd contact (constraint eq.), niet-conform | flux x (x = 3L/4) | -50000 W/m² | -50083 | -0.17% | 0.5% | OK |
| TH-04c | Verlijmd contact elastic: thermische weerstand | T naad (kant A) | 340 K | 340 | +0.00% | 0.0001% | OK |
| TH-04c | Verlijmd contact elastic: thermische weerstand | T naad (kant B) | 360 K | 360 | +0.00% | 0.0001% | OK |
| TH-04c | Verlijmd contact elastic: thermische weerstand | flux x (x = L/4) | -40000 W/m² | -40000 | -0.00% | 0.001% | OK |
| TH-04d | Verlijmd contact, schaalrand op schaalvlak (PLAN) | T naad (kant A) | 350 K | 350.04 | +0.01% | 0.1% | OK |
| TH-04d | Verlijmd contact, schaalrand op schaalvlak (PLAN) | T naad (kant B) | 350 K | 350.04 | +0.01% | 0.1% | OK |
| TH-04d | Verlijmd contact, schaalrand op schaalvlak (PLAN) | T (x = L/5) | 320 K | 320 | -0.00% | 0.1% | OK |
| TH-04d | Verlijmd contact, schaalrand op schaalvlak (PLAN) | flux x (x = 3L/4) | -50000 W/m² | -49979 | +0.04% | 0.5% | OK |
| TH-40 | Drie warmtebronnen als formule, overlappend | T - T0 (x = 0.3 L) | 29.95 K | 29.95 | +0.00% | 0.001% | OK |
| TH-40 | Drie warmtebronnen als formule, overlappend | T - T0 (x = 0.5 L) | 39.583 K | 39.583 | +0.00% | 0.001% | OK |
| TH-40 | Drie warmtebronnen als formule, overlappend | T - T0 (x = 0.7 L) | 35.75 K | 35.75 | +0.00% | 0.001% | OK |
| TH-41 | Twee warmtebronnen in de tijd (formule + tabel) | T_gem - T0 (t = 1 s) | 0.75 K | 0.75 | +0.00% | 0.01% | OK |
| TH-41 | Twee warmtebronnen in de tijd (formule + tabel) | T_gem - T0 (t = 2 s) | 2.75 K | 2.75 | +0.00% | 0.01% | OK |
| TH-42 | Lasbron + Mecway-warmtebron als tijdstabel | energie: rho cp int dT dV - E_las - E_tabel | 0 J | -1.9987e-06 | -1.9987e-06 | 0.18 J | OK |
| TH-42 | Lasbron + Mecway-warmtebron als tijdstabel | T_gem - T0 (t = 2 s) | 9.6154 K | 9.6154 | +0.00% | 0.1% | OK |

## Thermische spanning

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| TH-03a | Vrije thermische uitzetting (hex8) | u_x eind | 0.0012 m | 0.0012 | +0.00% | 0.0001% | OK |
| TH-03a | Vrije thermische uitzetting (hex8) | u_y zijkant | 1.2000e-04 m | 1.2000e-04 | +0.00% | 0.0001% | OK |
| TH-03a | Vrije thermische uitzetting (hex8) | max |sigma_xx| | 0 Pa | 1.2139e-06 | 1.2139e-06 | 252 Pa | OK |
| TH-03b | Staaf ingeklemd in x, uniforme opwarming | sigma_xx | -2.5200e+08 Pa | -2.5200e+08 | -0.00% | 0.0001% | OK |
| TH-03b | Staaf ingeklemd in x, uniforme opwarming | max |sigma_yy| | 0 Pa | 5.4813e-07 | 5.4813e-07 | 252 Pa | OK |
| TH-03b | Staaf ingeklemd in x, uniforme opwarming | u_y zijkant | 1.5600e-04 m | 1.5600e-04 | +0.00% | 0.0001% | OK |
| TH-03b | Staaf ingeklemd in x, uniforme opwarming | |reactie x| op x = L | 2.5200e+06 N | 2.5200e+06 | +0.00% | 0.0001% | OK |

## Vibro-akoestiek

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| VA-01 | adlv100a nagebouwd: zuiger + water + lucht, hex20 | f1 t.o.v. adlv100a | 13.829 Hz | 13.828 | -0.01% | 0.5% | OK |
| VA-01 | adlv100a nagebouwd: zuiger + water + lucht, hex20 | f1 exact | 13.828 Hz | 13.828 | -0.00% | 0.1% | OK |
| VA-01 | adlv100a nagebouwd: zuiger + water + lucht, hex20 | f2 exact | 2266.7 Hz | 2266.9 | +0.01% | 0.5% | OK |
| VA-01 | adlv100a nagebouwd: zuiger + water + lucht, hex20 | p/u lucht op de zuiger (mode 1) | 1.8494e+06 Pa/m | 1.8494e+06 | -0.00% | 0.5% | OK |
| VA-01 | adlv100a nagebouwd: zuiger + water + lucht, hex20 | p/u water op de zuiger (mode 1) | 3.7742e+05 Pa/m | 3.7742e+05 | -0.00% | 0.5% | OK |
| VA-01k | adlv100a nagebouwd met KOPPEL_-vlakselecties | f1 exact | 13.828 Hz | 13.828 | -0.00% | 0.1% | OK |
| VA-01k | adlv100a nagebouwd met KOPPEL_-vlakselecties | f2 exact | 2266.7 Hz | 2266.9 | +0.01% | 0.5% | OK |
| VA-02 | Elastische staaf + gesloten waterkolom, hex20 10+20 | f1 | 513.85 Hz | 513.85 | +0.00% | 1% | OK |
| VA-02 | Elastische staaf + gesloten waterkolom, hex20 10+20 | f2 | 960.19 Hz | 960.19 | +0.00% | 1% | OK |
| VA-02 | Elastische staaf + gesloten waterkolom, hex20 10+20 | f3 | 1475.7 Hz | 1475.7 | +0.00% | 1% | OK |
| VA-02 | Elastische staaf + gesloten waterkolom, hex20 10+20 | f4 | 1987.8 Hz | 1987.9 | +0.00% | 1% | OK |
| VA-03 | Schaalzuiger (DKT) op een gesloten luchtkolom, hex8 50x2x2 | f1 | 9.4798 Hz | 9.4798 | +0.00% | 1% | OK |
| VA-03 | Schaalzuiger (DKT) op een gesloten luchtkolom, hex8 50x2x2 | f2 | 340.26 Hz | 340.32 | +0.02% | 1% | OK |
| VA-03 | Schaalzuiger (DKT) op een gesloten luchtkolom, hex8 50x2x2 | f3 | 680.13 Hz | 680.58 | +0.07% | 1% | OK |
| VA-04 | Buis van twee media (c 340 / 680 m/s, gelijke dichtheid, alleen fluidum), hex20 20x1x1 | f1 | 248.98 Hz | 248.98 | +0.00% | 0.5% | OK |
| VA-04 | Buis van twee media (c 340 / 680 m/s, gelijke dichtheid, alleen fluidum), hex20 20x1x1 | f2 | 431.02 Hz | 431.03 | +0.00% | 0.5% | OK |
| VA-04 | Buis van twee media (c 340 / 680 m/s, gelijke dichtheid, alleen fluidum), hex20 20x1x1 | f3 | 680 Hz | 680.06 | +0.01% | 0.5% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f1 plaat (1,1) | 50.562 Hz | 50.515 | -0.09% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f2 plaat (2,1) | 109.76 Hz | 109.55 | -0.19% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f3 plaat (1,2) | 143.05 Hz | 142.85 | -0.14% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f4 plaat (2,2) | 202.25 Hz | 201.43 | -0.40% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f5 plaat (3,1) | 208.41 Hz | 207.96 | -0.22% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f6 plaat (1,3) | 297.21 Hz | 296.75 | -0.15% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f7 plaat (3,2) | 300.91 Hz | 299.08 | -0.61% | 1% | OK |
| VA-05 | Paneel op een luchtholte, lucht 1000x lichter (ongekoppeld), DKT 30x24 + hex8 30x24x12 | f8 holte (1,0,0) | 340 Hz | 340.15 | +0.04% | 1% | OK |
| VA-05b | Paneel op een luchtholte, gewone lucht, DKT 30x24 + hex8 30x24x12 | f1 pompmode (1,1) met luchtveer | 55.225 Hz | 54.961 | -0.48% | 3% | OK |
| VA-05c | Als VA-05b, modes boven 100 Hz (#ASTER-OPTIE vibro_freq_min) | f1 plaat (2, 1) | 109.76 Hz | 109.03 | -0.66% | 1% | OK |
| VA-05c | Als VA-05b, modes boven 100 Hz (#ASTER-OPTIE vibro_freq_min) | f2 plaat (1, 2) | 143.05 Hz | 142.31 | -0.52% | 1% | OK |
| VA-05c | Als VA-05b, modes boven 100 Hz (#ASTER-OPTIE vibro_freq_min) | f3 plaat (2, 2) | 202.25 Hz | 200.86 | -0.69% | 1% | OK |

## Vibro-akoestiek harmonisch

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO1 |p - p_refe| / |p_refe| (ahlv101a VALE_REFE) | 0 - | 2.6409e-05 | 2.6409e-05 | 0.001 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO1 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 1.3356e-07 | 1.3356e-07 | 1e-06 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO780 |p - p_refe| / |p_refe| (ahlv101a VALE_REFE) | 0 - | 2.6409e-05 | 2.6409e-05 | 0.001 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO780 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 1.3195e-07 | 1.3195e-07 | 1e-06 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO751 |p - p_refe| / |p_refe| (ahlv101a VALE_REFE) | 0 - | 7.9714e-04 | 7.9714e-04 | 0.001 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO751 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 2.8679e-08 | 2.8679e-08 | 1e-06 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO763 |p - p_refe| / |p_refe| (ahlv101a VALE_REFE) | 0 - | 7.9714e-04 | 7.9714e-04 | 0.001 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO763 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 4.2503e-08 | 4.2503e-08 | 1e-06 - | OK |
| VH-01 | ahlv101a nagebouwd: invallende golf (INVALLEND_, ONDE_FLUI) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | microfoon uitlaat: SPL | 84.949 dB | 84.948 | -0.00% | 0.01 dB | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO1 |p - p_refe| / |p_refe| (ahlv100b VALE_REFE) | 0 - | 5.2808e-05 | 5.2808e-05 | 0.001 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO1 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 2.2265e-07 | 2.2265e-07 | 1e-06 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO780 |p - p_refe| / |p_refe| (ahlv100b VALE_REFE) | 0 - | 5.2808e-05 | 5.2808e-05 | 0.001 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO780 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 2.2818e-07 | 2.2818e-07 | 1e-06 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO751 |p - p_refe| / |p_refe| (ahlv100b VALE_REFE) | 0 - | 8.9348e-04 | 8.9348e-04 | 0.001 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO751 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 1.1126e-07 | 1.1126e-07 | 1e-06 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO763 |p - p_refe| / |p_refe| (ahlv100b VALE_REFE) | 0 - | 8.9348e-04 | 8.9348e-04 | 0.001 - | OK |
| VH-01b | ahlv100b nagebouwd: snelheidsbron (BRON_, VITE_FACE) en absorberende uitlaat, 500 Hz, hex20 15x2x2 | NO763 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 1.0181e-07 | 1.0181e-07 | 1e-06 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=5 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.1791e-07 | 1.1791e-07 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=5 Hz: fase U zuiger | 0 graden | -6.0988e-08 | -6.0988e-08 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=5 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 2.0299e-07 | 2.0299e-07 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=20 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 5.4855e-07 | 5.4855e-07 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=20 Hz: fase U zuiger | 0 graden | -3.1353e-05 | -3.1353e-05 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=20 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.7874e-06 | 1.7874e-06 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=35 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 9.2577e-06 | 9.2577e-06 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=35 Hz: fase U zuiger | 0 graden | -5.2358e-04 | -5.2358e-04 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=35 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.0727e-05 | 1.0727e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=39 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.4985e-05 | 1.4985e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=39 Hz: fase U zuiger | 0 graden | -6.7837e-04 | -6.7837e-04 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=39 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.4174e-05 | 1.4174e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=45 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.7226e-05 | 1.7226e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=45 Hz: fase U zuiger | 0 graden | -2.8276e-04 | -2.8276e-04 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=45 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.2320e-05 | 1.2320e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=60 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.8322e-05 | 1.8322e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=60 Hz: fase U zuiger | 0 graden | 7.3302e-05 | 7.3302e-05 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=60 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 7.5346e-06 | 7.5346e-06 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=100 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.5882e-05 | 3.5882e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=100 Hz: fase U zuiger | 0 graden | 2.0512e-04 | 2.0512e-04 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=100 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.6716e-06 | 6.6716e-06 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=200 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.2527e-04 | 1.2527e-04 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=200 Hz: fase U zuiger | 0 graden | 4.2542e-04 | 4.2542e-04 | 0.5 graden | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | f=200 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 2.8703e-05 | 2.8703e-05 | 0.01 - | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | microfoon midden 39 Hz: SPL (CSV) | 130.97 dB | 130.97 | -0.00% | 0.09 dB | OK |
| VH-02 | Zuiger (massa-veer) op een luchtkolom met rho-c-einde: stralingsdemping | meetpunt zuiger 39 Hz: |U| (CSV) | 0.0010002 m | 0.0010002 | -0.00% | 1% | OK |
| VH-02t | Zuiger op een luchtkolom met rho-c-einde: kracht uit een Mecway-tabel (amplitude tegen de frequentie) met fase 90 graden (#ASTER-FASE) | f=5 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.2196e-07 | 1.2196e-07 | 0.01 - | OK |
| VH-02t | Zuiger op een luchtkolom met rho-c-einde: kracht uit een Mecway-tabel (amplitude tegen de frequentie) met fase 90 graden (#ASTER-FASE) | f=39 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.4987e-05 | 1.4987e-05 | 0.01 - | OK |
| VH-02t | Zuiger op een luchtkolom met rho-c-einde: kracht uit een Mecway-tabel (amplitude tegen de frequentie) met fase 90 graden (#ASTER-FASE) | f=100 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.5882e-05 | 3.5882e-05 | 0.01 - | OK |
| VH-02t | Zuiger op een luchtkolom met rho-c-einde: kracht uit een Mecway-tabel (amplitude tegen de frequentie) met fase 90 graden (#ASTER-FASE) | f=200 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.2527e-04 | 1.2527e-04 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=5 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.4326e-07 | 1.4326e-07 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=5 Hz: fase U zuiger | 0 graden | 2.3184e-07 | 2.3184e-07 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=5 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 3.8614e-07 | 3.8614e-07 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=20 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 4.5267e-07 | 4.5267e-07 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=20 Hz: fase U zuiger | 0 graden | -1.3041e-05 | -1.3041e-05 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=20 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.4145e-06 | 1.4145e-06 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=35 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.9537e-06 | 3.9537e-06 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=35 Hz: fase U zuiger | 0 graden | -2.2653e-04 | -2.2653e-04 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=35 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 5.9083e-06 | 5.9083e-06 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=39 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 8.6870e-06 | 8.6870e-06 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=39 Hz: fase U zuiger | 0 graden | -4.9543e-04 | -4.9543e-04 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=39 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.0343e-05 | 1.0343e-05 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=45 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.9268e-05 | 1.9268e-05 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=45 Hz: fase U zuiger | 0 graden | -6.9134e-04 | -6.9134e-04 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=45 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.6614e-05 | 1.6614e-05 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=60 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.8139e-05 | 1.8139e-05 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=60 Hz: fase U zuiger | 0 graden | 2.7179e-05 | 2.7179e-05 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=60 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 8.1373e-06 | 8.1373e-06 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=100 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.6338e-05 | 3.6338e-05 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=100 Hz: fase U zuiger | 0 graden | 1.0711e-04 | 1.0711e-04 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=100 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.0231e-06 | 6.0231e-06 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=200 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.1961e-04 | 1.1961e-04 | 0.01 - | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=200 Hz: fase U zuiger | 0 graden | 7.3599e-04 | 7.3599e-04 | 0.5 graden | OK |
| VH-03 | Zuiger op een luchtkolom met impedantie Z = 2 rho c op het einde (Mecway impedance) | f=200 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.6667e-05 | 1.6667e-05 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=5 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.7748e-07 | 1.7748e-07 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=5 Hz: fase U zuiger | 0 graden | 7.2433e-07 | 7.2433e-07 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=5 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.6289e-07 | 6.6289e-07 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=20 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 2.1399e-06 | 2.1399e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=20 Hz: fase U zuiger | 0 graden | -1.4634e-05 | -1.4634e-05 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=20 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 3.0989e-06 | 3.0989e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=35 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 7.5430e-06 | 7.5430e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=35 Hz: fase U zuiger | 0 graden | 3.3567e-05 | 3.3567e-05 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=35 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 5.6795e-06 | 5.6795e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=39 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 9.3478e-06 | 9.3478e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=39 Hz: fase U zuiger | 0 graden | 8.0998e-05 | 8.0998e-05 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=39 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.0022e-06 | 6.0022e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=45 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.1870e-05 | 1.1870e-05 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=45 Hz: fase U zuiger | 0 graden | 1.6768e-04 | 1.6768e-04 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=45 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.3110e-06 | 6.3110e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=60 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.7913e-05 | 1.7913e-05 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=60 Hz: fase U zuiger | 0 graden | 3.7662e-04 | 3.7662e-04 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=60 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.0876e-06 | 6.0876e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=100 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.7755e-05 | 3.7755e-05 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=100 Hz: fase U zuiger | 0 graden | 7.4635e-04 | 7.4635e-04 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=100 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.4110e-06 | 6.4110e-06 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=200 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.2784e-04 | 1.2784e-04 | 0.01 - | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=200 Hz: fase U zuiger | 0 graden | 0.0015369 | 0.0015369 | 0.5 graden | OK |
| VH-04 | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping alpha op de constructie | f=200 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 2.8758e-05 | 2.8758e-05 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=5 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.3068e-07 | 1.3068e-07 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=5 Hz: fase U zuiger | 0 graden | 4.5996e-07 | 4.5996e-07 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=5 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 2.0906e-07 | 2.0906e-07 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=20 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 5.2933e-07 | 5.2933e-07 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=20 Hz: fase U zuiger | 0 graden | -2.4102e-05 | -2.4102e-05 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=20 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.5883e-06 | 1.5883e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=35 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 4.1169e-06 | 4.1169e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=35 Hz: fase U zuiger | 0 graden | -1.4815e-04 | -1.4815e-04 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=35 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 5.1439e-06 | 5.1439e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=39 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 5.5392e-06 | 5.5392e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=39 Hz: fase U zuiger | 0 graden | -1.3424e-04 | -1.3424e-04 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=39 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 5.7319e-06 | 5.7319e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=45 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 7.6479e-06 | 7.6479e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=45 Hz: fase U zuiger | 0 graden | -5.9493e-05 | -5.9493e-05 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=45 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.2259e-06 | 6.2259e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=60 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.1553e-05 | 1.1553e-05 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=60 Hz: fase U zuiger | 0 graden | 2.1817e-04 | 2.1817e-04 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=60 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 5.9793e-06 | 5.9793e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=100 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 2.1001e-05 | 2.1001e-05 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=100 Hz: fase U zuiger | 0 graden | 8.5470e-04 | 8.5470e-04 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=100 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.2738e-06 | 6.2738e-06 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=200 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 4.5446e-05 | 4.5446e-05 | 0.01 - | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=200 Hz: fase U zuiger | 0 graden | 0.0023982 | 0.0023982 | 0.5 graden | OK |
| VH-04b | Zuiger op een luchtkolom met rho-c-einde en Rayleigh-demping beta (C = beta K: de veer) | f=200 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 2.8418e-05 | 2.8418e-05 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=5 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 9.0755e-08 | 9.0755e-08 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=5 Hz: fase U zuiger | 0 graden | 8.4690e-07 | 8.4690e-07 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=5 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.9758e-07 | 1.9758e-07 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=20 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 4.4318e-07 | 4.4318e-07 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=20 Hz: fase U zuiger | 0 graden | -2.1609e-05 | -2.1609e-05 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=20 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.5355e-06 | 1.5355e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=35 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.1156e-06 | 3.1156e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=35 Hz: fase U zuiger | 0 graden | -1.5312e-04 | -1.5312e-04 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=35 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 4.5539e-06 | 4.5539e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=39 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 4.3697e-06 | 4.3697e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=39 Hz: fase U zuiger | 0 graden | -1.9640e-04 | -1.9640e-04 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=39 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 5.3254e-06 | 5.3254e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=45 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 6.3798e-06 | 6.3798e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=45 Hz: fase U zuiger | 0 graden | -2.5207e-04 | -2.5207e-04 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=45 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 6.3450e-06 | 6.3450e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=60 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.1974e-05 | 1.1974e-05 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=60 Hz: fase U zuiger | 0 graden | -3.1992e-04 | -3.1992e-04 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=60 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 7.9642e-06 | 7.9642e-06 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=100 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 3.2089e-05 | 3.2089e-05 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=100 Hz: fase U zuiger | 0 graden | -4.2605e-04 | -4.2605e-04 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=100 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.1037e-05 | 1.1037e-05 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=200 Hz: |U - U_exact| / |U_exact| zuiger | 0 - | 1.2225e-04 | 1.2225e-04 | 0.01 - | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=200 Hz: fase U zuiger | 0 graden | -7.1485e-04 | -7.1485e-04 | 0.5 graden | OK |
| VH-04c | Zuiger op een luchtkolom met rho-c-einde en een Mecway-demper (Damper) parallel aan de veer | f=200 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.6311e-05 | 1.6311e-05 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=100 Hz: |P - P_exact| / max|P_exact| op x = 0 | 0 - | 1.0956e-07 | 1.0956e-07 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=100 Hz: |P - P_exact| / max|P_exact| op x = 0.5 | 0 - | 6.9790e-08 | 6.9790e-08 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=100 Hz: |P - P_exact| / max|P_exact| op x = 1 | 0 - | 1.2945e-07 | 1.2945e-07 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=250 Hz: |P - P_exact| / max|P_exact| op x = 0 | 0 - | 8.9258e-06 | 8.9258e-06 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=250 Hz: |P - P_exact| / max|P_exact| op x = 0.5 | 0 - | 7.6347e-06 | 7.6347e-06 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=250 Hz: |P - P_exact| / max|P_exact| op x = 1 | 0 - | 9.1334e-06 | 9.1334e-06 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=420 Hz: |P - P_exact| / max|P_exact| op x = 0 | 0 - | 1.1982e-04 | 1.1982e-04 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=420 Hz: |P - P_exact| / max|P_exact| op x = 0.5 | 0 - | 9.3219e-05 | 9.3219e-05 | 0.01 - | OK |
| VH-05 | Invallende golf p_in = 1 Pa en een harde wand op x = L | f=420 Hz: |P - P_exact| / max|P_exact| op x = 1 | 0 - | 1.2086e-04 | 1.2086e-04 | 0.01 - | OK |
| VH-05b | Invallende golf p_in = 1 Pa en p = 0 op x = L (OPEN_-vlakselectie) | f=100 Hz: |P - P_exact| / max|P_exact| op x = 0 | 0 - | 7.6488e-08 | 7.6488e-08 | 0.01 - | OK |
| VH-05b | Invallende golf p_in = 1 Pa en p = 0 op x = L (OPEN_-vlakselectie) | f=100 Hz: |P - P_exact| / max|P_exact| op x = 0.5 | 0 - | 7.4178e-08 | 7.4178e-08 | 0.01 - | OK |
| VH-05b | Invallende golf p_in = 1 Pa en p = 0 op x = L (OPEN_-vlakselectie) | f=250 Hz: |P - P_exact| / max|P_exact| op x = 0 | 0 - | 9.2937e-06 | 9.2937e-06 | 0.01 - | OK |
| VH-05b | Invallende golf p_in = 1 Pa en p = 0 op x = L (OPEN_-vlakselectie) | f=250 Hz: |P - P_exact| / max|P_exact| op x = 0.5 | 0 - | 7.5229e-06 | 7.5229e-06 | 0.01 - | OK |
| VH-05b | Invallende golf p_in = 1 Pa en p = 0 op x = L (OPEN_-vlakselectie) | f=420 Hz: |P - P_exact| / max|P_exact| op x = 0 | 0 - | 1.2276e-04 | 1.2276e-04 | 0.01 - | OK |
| VH-05b | Invallende golf p_in = 1 Pa en p = 0 op x = L (OPEN_-vlakselectie) | f=420 Hz: |P - P_exact| / max|P_exact| op x = 0.5 | 0 - | 9.4126e-05 | 9.4126e-05 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=5 Hz: |U - U_exact| / |U_exact| plaat | 0 - | 3.3232e-08 | 3.3232e-08 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=5 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 1.0706e-07 | 1.0706e-07 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=39 Hz: |U - U_exact| / |U_exact| plaat | 0 - | 9.0049e-05 | 9.0049e-05 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=39 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 2.3383e-05 | 2.3383e-05 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=100 Hz: |U - U_exact| / |U_exact| plaat | 0 - | 1.1173e-04 | 1.1173e-04 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=100 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 7.5847e-04 | 7.5847e-04 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=200 Hz: |U - U_exact| / |U_exact| plaat | 0 - | 2.4808e-04 | 2.4808e-04 | 0.01 - | OK |
| VH-06 | Schaalzuiger (DKT) met veer op een luchtkolom met rho-c-einde, hex8 20x2x2 | f=200 Hz: |P - P_exact| / |P_exact| op x = 0.5 | 0 - | 0.0033463 | 0.0033463 | 0.01 - | OK |
| VH-07 | #ASTER-BRON 14 mm/s met fase 90 graden op een vlakselectie zonder voorvoegsel (ahlv100b x i) | NO1 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 2.2265e-07 | 2.2265e-07 | 1e-06 - | OK |
| VH-07 | #ASTER-BRON 14 mm/s met fase 90 graden op een vlakselectie zonder voorvoegsel (ahlv100b x i) | NO780 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 2.2818e-07 | 2.2818e-07 | 1e-06 - | OK |
| VH-07 | #ASTER-BRON 14 mm/s met fase 90 graden op een vlakselectie zonder voorvoegsel (ahlv100b x i) | NO751 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 1.1126e-07 | 1.1126e-07 | 1e-06 - | OK |
| VH-07 | #ASTER-BRON 14 mm/s met fase 90 graden op een vlakselectie zonder voorvoegsel (ahlv100b x i) | NO763 |p - p_calc| / |p_calc| (ahlv100b VALE_CALC) | 0 - | 1.0181e-07 | 1.0181e-07 | 1e-06 - | OK |
| VH-07 | #ASTER-BRON 14 mm/s met fase 90 graden op een vlakselectie zonder voorvoegsel (ahlv100b x i) | microfoon uitlaat: fase (CSV) | -74.73 graden | -74.73 | +0.00% | 0.01 graden | OK |
| VH-08 | #ASTER-BRON 0,5 Pa met fase -30 graden: invallende golf (ahlv101a x e^(-i 30)) | NO1 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 1.1227e-07 | 1.1227e-07 | 1e-06 - | OK |
| VH-08 | #ASTER-BRON 0,5 Pa met fase -30 graden: invallende golf (ahlv101a x e^(-i 30)) | NO780 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 1.1129e-07 | 1.1129e-07 | 1e-06 - | OK |
| VH-08 | #ASTER-BRON 0,5 Pa met fase -30 graden: invallende golf (ahlv101a x e^(-i 30)) | NO751 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 1.5961e-08 | 1.5961e-08 | 1e-06 - | OK |
| VH-08 | #ASTER-BRON 0,5 Pa met fase -30 graden: invallende golf (ahlv101a x e^(-i 30)) | NO763 |p - p_calc| / |p_calc| (ahlv101a VALE_CALC) | 0 - | 5.4537e-09 | 5.4537e-09 | 1e-06 - | OK |

## Vermoeiing

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| VM-01a | Constante amplitude (blok), Wohler-tabel | schade D | 0.018287  | 0.018287 | +0.00% | 0.1% | OK |
| VM-01a | Constante amplitude (blok), Wohler-tabel | levensduur | 54.684 herhalingen | 54.684 | +0.00% | 0.1% | OK |
| VM-01b | Constante amplitude, Basquin | schade D | 3.3076e-05  | 3.3076e-05 | -0.00% | 0.1% | OK |
| VM-01c | Machtsvorm met Se: blok onder Se zonder schade | schade D | 0.084375  | 0.084375 | -0.00% | 0.1% | OK |
| VM-02a | Twee-niveau-spectrum, Wohler-tabel | schade D | 0.10054  | 0.10054 | +0.00% | 0.1% | OK |
| VM-02b | Twee-niveau-spectrum, Basquin + Goodman, 5 herhalingen | schade D | 0.0043293  | 0.0043293 | -0.00% | 0.1% | OK |
| VM-02b | Twee-niveau-spectrum, Basquin + Goodman, 5 herhalingen | levensduur | 1154.9 herhalingen | 1154.9 | +0.00% | 0.1% | OK |
| VM-03a | Rainflow ASTM E1049 (een doorgang) | cycli bereik 3 | 0.5 cycli | 0.5 | +0.00% | 1e-12 cycli | OK |
| VM-03a | Rainflow ASTM E1049 (een doorgang) | cycli bereik 4 | 1.5 cycli | 1.5 | +0.00% | 1e-12 cycli | OK |
| VM-03a | Rainflow ASTM E1049 (een doorgang) | cycli bereik 6 | 0.5 cycli | 0.5 | +0.00% | 1e-12 cycli | OK |
| VM-03a | Rainflow ASTM E1049 (een doorgang) | cycli bereik 8 | 1 cycli | 1 | +0.00% | 1e-12 cycli | OK |
| VM-03a | Rainflow ASTM E1049 (een doorgang) | cycli bereik 9 | 0.5 cycli | 0.5 | +0.00% | 1e-12 cycli | OK |
| VM-03a | Rainflow ASTM E1049 (een doorgang) | schade D | 5.8025e-06  | 5.8025e-06 | -0.00% | 0.1% | OK |
| VM-03b | Rainflow periodiek op het ASTM-signaal | aantal cycli | 4 cycli | 4 | +0.00% | 1e-12 cycli | OK |
| VM-03b | Rainflow periodiek op het ASTM-signaal | schade D (hand) | 6.4638e-06  | 6.4638e-06 | -0.00% | 0.1% | OK |
| VM-03b | Rainflow periodiek op het ASTM-signaal | schade D / POST_FATIGUE | 1  | 1 | -0.00% | 0.0001% | OK |
| VM-04 | szlz105a in 3D (niet-lineair statisch) | schade D | 0.0048133  | 0.0048133 | +0.00% | 1% | OK |
| VM-04 | szlz105a in 3D (niet-lineair statisch) | schade D / CALC_FATIGUE | 1  | 1 | +0.00% | 0.0001% | OK |
| VM-05a | szlz100a in 3D: zonder correctie | schade D | 0.0010533  | 0.0010533 | -0.00% | 1% | OK |
| VM-05b | szlz100a in 3D: Gerber | schade D | 0.0010636  | 0.0010636 | +0.00% | 1% | OK |
| VM-05c | szlz100a in 3D: Goodman | schade D | 0.0012502  | 0.0012502 | +0.00% | 1% | OK |
| VM-06 | Dynamisch: schade = CALC_FATIGUE | schade D / CALC_FATIGUE | 1  | 1 | +0.00% | 0.0001% | OK |
| VM-07a | Tweeassig, VMIS_SG | schade D | 0.001387  | 0.001387 | -0.00% | 0.1% | OK |
| VM-07b | Tweeassig, PRIN | schade D | 3.3076e-05  | 3.3076e-05 | +0.00% | 0.1% | OK |
| VM-08a | sslv135a in 3D: Matake (periodiek) | SIGEQ | 300 MPa | 300 | +0.00% | 1% | OK |
| VM-08a | sslv135a in 3D: Matake (periodiek) | levensduur | 10946 cycli | 10946 | +0.00% | 1% | OK |
| VM-08a | sslv135a in 3D: Matake (periodiek) | schade D | 9.1356e-05  | 9.1356e-05 | +0.00% | 1% | OK |
| VM-08a | sslv135a in 3D: Matake (periodiek) | schade D (hand) | 9.1356e-05  | 9.1356e-05 | +0.00% | 0.0001% | OK |
| VM-08b | sslv135a in 3D: Dang Van (periodiek) | SIGEQ | 275 MPa | 275 | +0.00% | 1% | OK |
| VM-08b | sslv135a in 3D: Dang Van (periodiek) | levensduur | 14903 cycli | 14903 | +0.00% | 1% | OK |
| VM-08b | sslv135a in 3D: Dang Van (periodiek) | schade D | 6.7100e-05  | 6.7100e-05 | +0.00% | 1% | OK |
| VM-08b | sslv135a in 3D: Dang Van (periodiek) | schade D (hand) | 6.7100e-05  | 6.7100e-05 | -0.00% | 0.0001% | OK |
| VM-08c | sslv135a in 3D: Dang Van niet-periodiek | schade D | 6.7100e-05  | 6.7100e-05 | -0.00% | 1% | OK |
| VM-08d | sslv135a-kubus, ramp 0 -> 1: begintoestand telt | SIGEQ | 112.5 MPa | 112.5 | +0.00% | 0.0001% | OK |
| VM-09a | Trek + afschuiving: Dang Van met de hand | SIGEQ | 168 MPa | 168 | -0.00% | 0.1% | OK |
| VM-09a | Trek + afschuiving: Dang Van met de hand | criterium (tau_a + a P)/b | 1.0182  | 1.0182 | -0.00% | 0.1% | OK |
| VM-09a | Trek + afschuiving: Dang Van met de hand | schade D | 8.3334e-07  | 8.3333e-07 | -0.00% | 0.1% | OK |
| VM-09b | Trek + afschuiving: Dang Van, twee blokken | SIGEQ (grootste blok) | 168 MPa | 168 | -0.00% | 0.1% | OK |
| VM-09b | Trek + afschuiving: Dang Van, twee blokken | schade D | 1.3049e-05  | 1.3049e-05 | -0.00% | 0.1% | OK |
| VM-09c | Trek + afschuiving: Matake met de hand | SIGEQ | 177 MPa | 177.1 | +0.06% | 1% | OK |
| VM-09c | Trek + afschuiving: Matake met de hand | criterium (tau_a + a P)/b | 1.0727  | 1.0733 | +0.06% | 1% | OK |
| VM-09c | Trek + afschuiving: Matake met de hand | schade D | 1.0543e-06  | 1.0571e-06 | +0.26% | 1% | OK |
| VM-09d | Trek + afschuiving: Crossland met de hand | SIGEQ | 176.75 MPa | 176.75 | +0.00% | 0.1% | OK |
| VM-09d | Trek + afschuiving: Crossland met de hand | criterium (tau_a + a P)/b | 1.0712  | 1.0712 | +0.00% | 0.1% | OK |
| VM-09d | Trek + afschuiving: Crossland met de hand | schade D | 1.0475e-06  | 1.0475e-06 | +0.00% | 0.1% | OK |
| VM-10 | Schaalplaat, zuivere buiging: boven- en onderzijde | sigma boven | 150 MPa | 150 | +0.00% | 0.1% | OK |
| VM-10 | Schaalplaat, zuivere buiging: boven- en onderzijde | schade boven | 1.2278e-05  | 1.2278e-05 | +0.00% | 0.1% | OK |
| VM-10 | Schaalplaat, zuivere buiging: boven- en onderzijde | schade onder | 9.9470e-07  | 9.9470e-07 | +0.00% | 0.1% | OK |
| VM-10 | Schaalplaat, zuivere buiging: boven- en onderzijde | schade (grootste) | 1.2278e-05  | 1.2278e-05 | +0.00% | 0.1% | OK |
| VM-11a | Manson-Coffin: opgelegde rek, plastisch | rekamplitude | 0.006  | 0.006 | +0.00% | 0.0001% | OK |
| VM-11a | Manson-Coffin: opgelegde rek, plastisch | schade D | 7.4264e-04  | 7.4264e-04 | +0.00% | 0.1% | OK |
| VM-11b | Manson-Coffin: elastisch, rek = VMIS_SG | schade D | 1.9221e-08  | 1.9221e-08 | +0.00% | 0.1% | OK |

## Lassen

| ID | Test | Grootheid | Referentie | FEM | Afwijking | Tolerantie | Status |
|---|---|---|---|---|---|---|---|
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | T-T0 xi=0 y=3 z=0 mm | 548.85 K | 548.82 | -0.01% | 5% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | T-T0 xi=0 y=5 z=0 mm | 150.96 K | 152.32 | +0.90% | 5% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | T-T0 xi=-3 y=3 z=0 mm | 770.18 K | 768.09 | -0.27% | 5% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | T-T0 xi=-6 y=0 z=0 mm | 884.19 K | 875.85 | -0.94% | 5% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | T-T0 xi=0 y=0 z=-3 mm | 548.85 K | 548.82 | -0.01% | 5% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | T-T0 xi=-5 y=2 z=-2 mm | 690.77 K | 688.23 | -0.37% | 5% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | energie t=6 s | 3000 J | 3001.8 | +0.06% | 2% | OK |
| WE-01 | Bewegende Gauss-bron (r = 0,75 mm), Rosenthal | opgenomen vermogen (job) | 500 W | 500.44 | +0.09% | 0.5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | T-T0 xi=0 y=3 z=0 mm | 548.85 K | 544.51 | -0.79% | 5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | T-T0 xi=0 y=5 z=0 mm | 150.96 K | 153.33 | +1.57% | 5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | T-T0 xi=-3 y=3 z=0 mm | 770.18 K | 765.5 | -0.61% | 5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | T-T0 xi=-6 y=0 z=0 mm | 884.19 K | 852.51 | -3.58% | 5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | T-T0 xi=0 y=0 z=-3 mm | 548.85 K | 544.51 | -0.79% | 5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | T-T0 xi=-5 y=2 z=-2 mm | 690.77 K | 687.13 | -0.53% | 5% | OK |
| WE-01b | Idem, dt = 0,15 s (v dt = (af+ar)/2, grens) | energie t=6 s | 3000 J | 3001.8 | +0.06% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | T-T0 xi=0 y=3 z=0 mm (Goldak) | 492.02 K | 486.32 | -1.16% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | T-T0 xi=0 y=5 z=0 mm (Goldak) | 136.83 K | 137.14 | +0.23% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | T-T0 xi=-3 y=3 z=0 mm (Goldak) | 773.18 K | 769.81 | -0.43% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | T-T0 xi=-6 y=0 z=0 mm (Goldak) | 930.8 K | 927.55 | -0.35% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | T-T0 xi=0 y=0 z=-3 mm (Goldak) | 492.02 K | 486.32 | -1.16% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | T-T0 xi=-5 y=2 z=-2 mm (Goldak) | 709 K | 708.66 | -0.05% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | energie t=6 s | 3000 J | 3000 | +0.00% | 2% | OK |
| WE-02 | Bewegende Goldak-bron 1/2/1/1 mm, eta 0,8 | opgenomen vermogen (job) | 500 W | 500 | +0.00% | 0.5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=0 y=3 z=0 mm | 548.85 K | 548.82 | -0.01% | 5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=0 y=5 z=0 mm | 150.96 K | 152.32 | +0.90% | 5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=-3 y=3 z=0 mm | 770.18 K | 768.09 | -0.27% | 5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=-6 y=0 z=0 mm | 884.19 K | 875.85 | -0.94% | 5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=0 y=0 z=-3 mm | 548.85 K | 548.82 | -0.01% | 5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=-5 y=2 z=-2 mm | 690.77 K | 688.23 | -0.37% | 5% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=0 y=3 z=0 mm (Goldak) | 556.55 K | 548.82 | -1.39% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=0 y=5 z=0 mm (Goldak) | 153.03 K | 152.32 | -0.46% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=-3 y=3 z=0 mm (Goldak) | 768.4 K | 768.09 | -0.04% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=-6 y=0 z=0 mm (Goldak) | 878.02 K | 875.85 | -0.25% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=0 y=0 z=-3 mm (Goldak) | 556.55 K | 548.82 | -1.39% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | T-T0 xi=-5 y=2 z=-2 mm (Goldak) | 687.66 K | 688.23 | +0.08% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | energie t=6 s | 3000 J | 3001.8 | +0.06% | 2% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | Mecway energie t=6 s | 3001.8 J | 3001.8 | +0.00% | 0.01% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | Mecway T xi=0 y=3 | 867.3 K | 841.97 | -2.92% | 6% | OK |
| WE-03 | Gauss-bron als Mecway-formule (heat generation) | Mecway T xi=-6 y=0 | 1151 K | 1169 | +1.57% | 6% | OK |
| WE-04a | Temperatuurafhankelijke lambda, stationair | T x=25 mm | 622.88 K | 622.88 | +0.00% | 0.01% | OK |
| WE-04a | Temperatuurafhankelijke lambda, stationair | T x=50 mm | 881.14 K | 881.14 | +0.00% | 0.01% | OK |
| WE-04a | Temperatuurafhankelijke lambda, stationair | T x=75 mm | 1102.8 K | 1102.8 | +0.00% | 0.01% | OK |
| WE-04a | Temperatuurafhankelijke lambda, stationair | Mecway T x=L/2 | 881.14 K | 881.14 | +0.00% | 0.1% | OK |
| WE-04b | Temperatuurafhankelijke lambda en cp, transient | energie t=1 s | 1000 J | 999.97 | -0.00% | 0.5% | OK |
| WE-04b | Temperatuurafhankelijke lambda en cp, transient | energie t=2 s | 2000 J | 2000 | -0.00% | 0.5% | OK |
| WE-04b | Temperatuurafhankelijke lambda en cp, transient | Mecway T x=0 t=2 | 1623.7 K | 1623.1 | -0.04% | 2% | OK |
| WE-04b | Temperatuurafhankelijke lambda en cp, transient | Mecway T x=2 mm t=2 | 1017 K | 1018.4 | +0.13% | 2% | OK |
| WE-04b | Temperatuurafhankelijke lambda en cp, transient | Mecway T x=0 t=1 | 1196.8 K | 1196.9 | +0.01% | 2% | OK |
| WE-05 | Goldak-bron met temperatuurafhankelijke lambda en cp | energie t=6 s | 3000 J | 2999.8 | -0.01% | 2% | OK |
| WE-05 | Goldak-bron met temperatuurafhankelijke lambda en cp | opgenomen vermogen (job) | 500 W | 500 | +0.00% | 0.5% | OK |
| WE-06 | Formules in x, y, z: temperatuur, convectie, flux | T (0, 10, 0) mm | 383.15 K | 383.15 | +0.00% | 1e-07% | OK |
| WE-06 | Formules in x, y, z: temperatuur, convectie, flux | T (50, 5, 10) mm | 1081.2 K | 1081.2 | +0.00% | 1e-07% | OK |
| WE-06 | Formules in x, y, z: temperatuur, convectie, flux | T (100, 0, 0) mm | 1352.2 K | 1352.2 | +0.00% | 1e-07% | OK |
| WE-07 | Keten thermisch-mechanisch: vrij uitzetten | u_x eind t=5 s | 1.2000e-04 m | 1.2000e-04 | -0.00% | 0.1% | OK |
| WE-07 | Keten thermisch-mechanisch: vrij uitzetten | u_y zijkant t=5 s | 1.2000e-05 m | 1.2000e-05 | +0.00% | 0.1% | OK |
| WE-07 | Keten thermisch-mechanisch: vrij uitzetten | u_x eind t=2 s | 4.8000e-05 m | 4.8000e-05 | +0.00% | 0.1% | OK |
| WE-07 | Keten thermisch-mechanisch: vrij uitzetten | max |sigma_xx| t=5 s | 0 Pa | 3.1208e-07 | 3.1208e-07 | 25200 Pa | OK |
| WE-07 | Keten thermisch-mechanisch: vrij uitzetten | u_x eind na terugkoelen | 0 m | -4.1410e-22 | -4.1410e-22 | 1.2e-08 m | OK |
| WE-07 | Keten thermisch-mechanisch: vrij uitzetten | temperatuur t=5 s | 393.15 K | 393.15 | -0.00% | 0.0001% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | sigma_xx elastisch dT=50 K | -1.2600e+08 Pa | -1.2600e+08 | +0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | sigma_xx plastisch dT=150 K | -2.6113e+08 Pa | -2.6113e+08 | +0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | eq. plastische rek dT=150 K | 5.5652e-04 - | 5.5652e-04 | +0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | u_y zijkant dT=150 K | 2.4513e-05 m | 2.4513e-05 | -0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | restspanning sigma_xx na terugkoelen | 1.1687e+08 Pa | 1.1687e+08 | +0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | plastische rek xx na terugkoelen | -5.5652e-04 - | -5.5652e-04 | -0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | u_y zijkant na terugkoelen | 1.1130e-06 m | 1.1130e-06 | +0.00% | 1% | OK |
| WE-08 | Keten: verhinderde staaf, bilineair plastisch, restspanning | |reactie x| op x = L na terugkoelen | 11687 N | 11687 | -0.00% | 1% | OK |
| WE-09 | Keten: E(T), SY(T), alpha(T) (#ASTER-MATERIAAL) | sigma_xx elastisch dT=50 K | -1.2444e+08 Pa | -1.2444e+08 | +0.00% | 1% | OK |
| WE-09 | Keten: E(T), SY(T), alpha(T) (#ASTER-MATERIAAL) | sigma_xx plastisch dT=400 K | -1.4000e+08 Pa | -1.4000e+08 | +0.00% | 1% | OK |
| WE-09 | Keten: E(T), SY(T), alpha(T) (#ASTER-MATERIAAL) | sigma_xx afkoelen dT=300 K (elastisch) | 1.0715e+08 Pa | 1.0715e+08 | +0.00% | 1% | OK |
| WE-09 | Keten: E(T), SY(T), alpha(T) (#ASTER-MATERIAAL) | restspanning sigma_xx na terugkoelen | 3.0000e+08 Pa | 3.0000e+08 | +0.00% | 1% | OK |
| WE-09 | Keten: E(T), SY(T), alpha(T) (#ASTER-MATERIAAL) | plastische rek xx na terugkoelen | -0.0014286 - | -0.0014286 | +0.00% | 1% | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | evenwicht: int sigma_xx dA (x = 20 mm) / (SY A) | 0 - | -1.5873e-04 | -1.5873e-04 | 0.03 - | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | evenwicht: int sigma_xx (z - zc) dA / (SY A t) | 0 - | -0.010106 | -0.010106 | 0.03 - | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | von Mises lasas boven / (SY(T0) + H p): vloeit | 1 - | 1.0021 | +0.21% | 5% | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | sigma_xx lasas boven (x = 20 mm) > 0 (trek) | 1 - | 1 | +0.00% | 0 - | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | sigma_xx op y >= 8 mm (x = 20 mm, midden dikte) < 0 (druk) | 1 - | 1 | +0.00% | 0 - | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | hoekverdraaiing: dz(y = 15) - dz(y = 0) onder > 0 | 1 - | 1 | +0.00% | 0 - | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | langskrimp: dx(x = 40) - dx(x = 0) op de lasas < 0 | 1 - | 1 | +0.00% | 0 - | OK |
| WE-10 | Keten: lasrups op een plaat, restspanning en vervorming | dwarskrimp hele plaat / (alpha q/(v rho c t)) | 0.6 - | 0.75041 | +25.07% | 0.4 - | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | energie levend t=3.5 s (stuk 2 nog niet geboren) | 460.75 J | 466.23 | +1.19% | 2% | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | energie levend t=5 s (stuk 2 wordt geboren) | 725 J | 735.8 | +1.49% | 2% | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | warmte in ongeboren stuk 2 als echt materiaal t=3.5 s / (Q t) | 0 - | 0.0050116 | 0.0050116 | 0.01 - | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | max T bovenop ongeboren stuk 2 (x > 15 mm) t=3.5 s | 293.15 K | 293.64 | +0.17% | 1 K | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | energie levend t=9 s (beide stukken geboren) | 935.75 J | 950.63 | +1.59% | 2% | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | opgenomen vermogen bron 1 (job) | 250 W | 249.55 | -0.18% | 2% | OK |
| WE-11 | Toevoegmateriaal: rups in twee stukken, energiebalans (thermisch) | opgenomen vermogen bron 2 (job) | 250 W | 249.76 | -0.10% | 2% | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | energie levend t=3.5 s (stuk 2 nog niet geboren) | 460.75 J | 465.9 | +1.12% | 2% | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | energie levend t=5 s (stuk 2 wordt geboren) | 725 J | 735.14 | +1.40% | 2% | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | warmte in ongeboren stuk 2 als echt materiaal t=3.5 s / (Q t) | 0 - | 0.0050246 | 0.0050246 | 0.01 - | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | max T bovenop ongeboren stuk 2 (x > 15 mm) t=3.5 s | 293.15 K | 293.77 | +0.21% | 1 K | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | energie levend t=9 s (beide stukken geboren) | 935.75 J | 950.13 | +1.54% | 2% | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | opgenomen vermogen bron 1 (job) | 250 W | 249.55 | -0.18% | 2% | OK |
| WE-11b | Toevoegmateriaal: twee stukken met lambda(T), c(T) (THER_NON_LINE) | opgenomen vermogen bron 2 (job) | 250 W | 249.76 | -0.10% | 2% | OK |
| WE-12 | Toevoegmateriaal: staaf halverwege geboren, krimpspanning (elastisch) | u_x(L/2) t=5 s (B ongeboren: A zet vrij uit) | 6.0000e-05 m | 5.9987e-05 | -0.02% | 1% | OK |
| WE-12 | Toevoegmateriaal: staaf halverwege geboren, krimpspanning (elastisch) | |sigma_xx| in ongeboren B t=5 s / (E alpha dT) | 0 - | 1.8425e-04 | 1.8425e-04 | 0.001 - | OK |
| WE-12 | Toevoegmateriaal: staaf halverwege geboren, krimpspanning (elastisch) | sigma_xx B t=7 s (1 s na de geboorte, 20 K afgekoeld) | 5.0400e+07 Pa | 5.0379e+07 | -0.04% | 1% | OK |
| WE-12 | Toevoegmateriaal: staaf halverwege geboren, krimpspanning (elastisch) | restspanning sigma_xx B t=11 s | 2.5200e+08 Pa | 2.5198e+08 | -0.01% | 1% | OK |
| WE-12 | Toevoegmateriaal: staaf halverwege geboren, krimpspanning (elastisch) | restspanning sigma_xx A t=11 s | 2.5200e+08 Pa | 2.5197e+08 | -0.01% | 1% | OK |
| WE-12b | Toevoegmateriaal: staaf halverwege geboren, bilineair plastisch | u_x(L/2) t=5 s (B ongeboren: A zet vrij uit) | 6.0000e-05 m | 5.9987e-05 | -0.02% | 1% | OK |
| WE-12b | Toevoegmateriaal: staaf halverwege geboren, bilineair plastisch | |sigma_xx| in ongeboren B t=5 s / (E alpha dT) | 0 - | 1.8425e-04 | 1.8425e-04 | 0.001 - | OK |
| WE-12b | Toevoegmateriaal: staaf halverwege geboren, bilineair plastisch | sigma_xx B t=7 s (1 s na de geboorte, 20 K afgekoeld) | 5.0400e+07 Pa | 5.0379e+07 | -0.04% | 1% | OK |
| WE-12b | Toevoegmateriaal: staaf halverwege geboren, bilineair plastisch | restspanning sigma_xx B t=11 s (bilineair) | 2.5017e+08 Pa | 2.5017e+08 | +0.00% | 1% | OK |
| WE-12b | Toevoegmateriaal: staaf halverwege geboren, bilineair plastisch | eq. plastische rek B t=11 s | 8.6957e-06 - | 8.6329e-06 | -0.72% | 1% | OK |
| WE-12c | Toevoegmateriaal: staaf halverwege geboren, hardingscurve (TRACTION) | u_x(L/2) t=5 s (B ongeboren: A zet vrij uit) | 6.0000e-05 m | 5.9987e-05 | -0.02% | 1% | OK |
| WE-12c | Toevoegmateriaal: staaf halverwege geboren, hardingscurve (TRACTION) | |sigma_xx| in ongeboren B t=5 s / (E alpha dT) | 0 - | 1.8425e-04 | 1.8425e-04 | 0.001 - | OK |
| WE-12c | Toevoegmateriaal: staaf halverwege geboren, hardingscurve (TRACTION) | sigma_xx B t=7 s (1 s na de geboorte, 20 K afgekoeld) | 5.0400e+07 Pa | 5.0379e+07 | -0.04% | 1% | OK |
| WE-12c | Toevoegmateriaal: staaf halverwege geboren, hardingscurve (TRACTION) | restspanning sigma_xx B t=11 s (curve) | 2.5002e+08 Pa | 2.5002e+08 | +0.00% | 1% | OK |
| WE-12c | Toevoegmateriaal: staaf halverwege geboren, hardingscurve (TRACTION) | eq. plastische rek B t=11 s | 9.4340e-06 - | 9.4348e-06 | +0.01% | 1% | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | laag 1 smelt bij de eerste laag: T_max(x=15, boven laag 1) / 1773 K | 1.5 - | 1.518 | +1.20% | 0.5 - | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | laag 1 opnieuw opgewarmd door laag 2: T_max(6..12 s) > T(6 s) | 1 - | 1 | +0.00% | 0 - | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | laag 1 afgekoeld tussen de lagen: T(6 s) < T_max(0..6 s) / 2 | 1 - | 1 | +0.00% | 0 - | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | max von Mises bovenop ongeboren laag 2 t=5.8 s / SY | 0 - | 4.7063e-04 | 4.7063e-04 | 0.001 - | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | T bovenop ongeboren laag 2 t=5.8 s | 293.15 K | 293.18 | +0.01% | 1 K | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | evenwicht: int sigma_xx dA (x = 15 mm) t=30 s / (SY A) | 0 - | -0.0024528 | -0.0024528 | 0.03 - | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | sigma_xx bovenop laag 2 (x = 15 mm) t=30 s > 0 (trek) | 1 - | 1 | +0.00% | 0 - | OK |
| WE-13 | Toevoegmateriaal: twee lagen op een plaat, temperatuurgeschiedenis en restspanning | sigma_xx rand y = 8 mm midden dikte t=30 s < 0 (druk) | 1 - | 1 | +0.00% | 0 - | OK |

## Mesh-convergentie

**AD-01 hex20 – Kt_n**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| AD-01-n1 | 0.02 | 127 | 1.8339 | 27.198% |  |
| AD-01-n2 | 0.01 | 419 | 2.1595 | 14.273% | 0.93 |
| AD-01-n4 | 0.005 | 1507 | 2.3593 | 6.342% | 1.17 |
| AD-01-n8 | 0.0025 | 5699 | 2.4569 | 2.467% | 1.36 |
| AD-01-n16 | 0.00125 | 22147 | 2.5 | 0.754% | 1.71 |
| AD-01-n32 | 6.2500e-04 | 87299 | 2.5156 | 0.137% | 2.46 |

Richardson (laatste drie meshes): orde p = 1.47, limiet 2.5243 (+0.211% t.o.v. de referentie).

**BU-03 hex20 – factor 1**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| BU-03-h20-n2 | 0.01 | 2079 | 10.384 | 0.205% |  |
| BU-03-h20-n4 | 0.005 | 12893 | 10.377 | 0.131% | 0.64 |

**BU-03 hex20 – factor 2**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| BU-03-h20-n2 | 0.01 | 2079 | 23.344 | 0.116% |  |
| BU-03-h20-n4 | 0.005 | 12893 | 23.33 | 0.057% | 1.02 |

**BU-04 DKT – factor 1**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| BU-04-dkt-n8 | 0.05 | 81 | 3.0829e+05 | 1.519% |  |
| BU-04-dkt-n16 | 0.025 | 289 | 3.0483e+05 | 0.378% | 2.01 |
| BU-04-dkt-n32 | 0.0125 | 1089 | 3.0397e+05 | 0.094% | 2.00 |

Richardson (laatste drie meshes): orde p = 2.01, limiet 3.0368e+05 (+0.001% t.o.v. de referentie).

**BU-04 DKT – factor 2**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| BU-04-dkt-n8 | 0.05 | 81 | 4.9362e+05 | 4.029% |  |
| BU-04-dkt-n16 | 0.025 | 289 | 4.7922e+05 | 0.994% | 2.02 |
| BU-04-dkt-n32 | 0.0125 | 1089 | 4.7568e+05 | 0.248% | 2.01 |

Richardson (laatste drie meshes): orde p = 2.02, limiet 4.7452e+05 (+0.004% t.o.v. de referentie).

**DY-01 Newmark dt – periode**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| DY-01b | 0.1 | 2 | 1.0321 | 3.210% |  |
| DY-01c | 0.05 | 2 | 1.0081 | 0.814% | 1.98 |
| DY-01d | 0.025 | 2 | 1.0021 | 0.205% | 1.99 |

Richardson (laatste drie meshes): orde p = 1.98, limiet 0.99998 (-0.002% t.o.v. de referentie).

**DY-01 Newmark dt – max. verplaatsing**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| DY-01b | 0.1 | 2 | 0.019996 | 0.021% |  |
| DY-01c | 0.05 | 2 | 0.02 | 0.000% | 5.75 |
| DY-01d | 0.025 | 2 | 0.02 | 0.000% |  |

Richardson (laatste drie meshes): orde p = 5.75, limiet 0.02 (+0.000% t.o.v. de referentie).

**LS-02 hex20 – doorbuiging tip (gem.)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-h20-n1 | 0.1 | 128 | 0.0018806 | 2.031% |  |
| LS-02-h20-n2 | 0.05 | 621 | 0.0018994 | 1.051% | 0.95 |
| LS-02-h20-n4 | 0.025 | 3665 | 0.0019041 | 0.806% | 0.38 |

Richardson (laatste drie meshes): orde p = 2.00, limiet 0.0019057 (-0.724% t.o.v. de referentie).

**LS-02 hex20 – sigma_xx x=0,2 m boven**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-h20-n1 | 0.1 | 128 | 4.8051e+07 | 0.106% |  |
| LS-02-h20-n2 | 0.05 | 621 | 4.8019e+07 | 0.040% | 1.41 |
| LS-02-h20-n4 | 0.025 | 3665 | 4.8000e+07 | 0.000% | 10.15 |

Richardson (laatste drie meshes): orde p = 0.73, limiet 4.7971e+07 (-0.060% t.o.v. de referentie).

**LS-02 hex20 – reactiekracht Z**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-h20-n1 | 0.1 | 128 | 10000 | 0.000% |  |
| LS-02-h20-n2 | 0.05 | 621 | 10000 | 0.000% |  |
| LS-02-h20-n4 | 0.025 | 3665 | 10000 | 0.000% |  |

Richardson: op alle meshes gelijk (exact, geen discretisatiefout).

**LS-02 hex8 3D – doorbuiging tip (gem.)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-h8-n1 | 0.1 | 44 | 0.0012339 | 35.722% |  |
| LS-02-h8-n2 | 0.05 | 189 | 0.0016682 | 13.099% | 1.45 |
| LS-02-h8-n4 | 0.025 | 1025 | 0.0018378 | 4.261% | 1.62 |
| LS-02-h8-n8 | 0.0125 | 6561 | 0.0018879 | 1.652% | 1.37 |
| LS-02-h8-n16 | 0.00625 | 46529 | 0.0019016 | 0.941% | 0.81 |

Richardson (laatste drie meshes): orde p = 1.87, limiet 0.0019067 (-0.674% t.o.v. de referentie).

**LS-02 hex8 3D – sigma_xx x=0,2 m boven**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-h8-n1 | 0.1 | 44 | 3.6461e+07 | 24.039% |  |
| LS-02-h8-n2 | 0.05 | 189 | 4.5731e+07 | 4.728% | 2.35 |
| LS-02-h8-n4 | 0.025 | 1025 | 4.8367e+07 | 0.765% | 2.63 |
| LS-02-h8-n8 | 0.0125 | 6561 | 4.8611e+07 | 1.274% | -0.74 |
| LS-02-h8-n16 | 0.00625 | 46529 | 4.8413e+07 | 0.861% | 0.56 |

Richardson: niet monotoon of geen vaste verfijningsfactor.

**LS-02 hex8 3D – reactiekracht Z**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-h8-n1 | 0.1 | 44 | 10000 | 0.000% |  |
| LS-02-h8-n2 | 0.05 | 189 | 10000 | 0.000% |  |
| LS-02-h8-n4 | 0.025 | 1025 | 10000 | 0.000% |  |
| LS-02-h8-n8 | 0.0125 | 6561 | 10000 | 0.000% |  |
| LS-02-h8-n16 | 0.00625 | 46529 | 10000 | 0.000% |  |

Richardson: op alle meshes gelijk (exact, geen discretisatiefout).

**LS-02 hex8 LINE_QUAD – doorbuiging tip (gem.)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-lq-n1 | 0.1 | 44 | 0.0018806 | 2.031% |  |
| LS-02-lq-n2 | 0.05 | 189 | 0.0018994 | 1.051% | 0.95 |
| LS-02-lq-n4 | 0.025 | 1025 | 0.0019042 | 0.806% | 0.38 |

Richardson (laatste drie meshes): orde p = 2.00, limiet 0.0019057 (-0.724% t.o.v. de referentie).

**LS-02 hex8 LINE_QUAD – sigma_xx x=0,2 m boven**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-lq-n1 | 0.1 | 44 | 4.8051e+07 | 0.106% |  |
| LS-02-lq-n2 | 0.05 | 189 | 4.8019e+07 | 0.040% | 1.41 |
| LS-02-lq-n4 | 0.025 | 1025 | 4.8000e+07 | 0.000% | 10.15 |

Richardson (laatste drie meshes): orde p = 0.73, limiet 4.7971e+07 (-0.060% t.o.v. de referentie).

**LS-02 hex8 LINE_QUAD – reactiekracht Z**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-02-lq-n1 | 0.1 | 44 | 10000 | 0.000% |  |
| LS-02-lq-n2 | 0.05 | 189 | 10000 | 0.000% |  |
| LS-02-lq-n4 | 0.025 | 1025 | 10000 | 0.000% |  |

Richardson: op alle meshes gelijk (exact, geen discretisatiefout).

**LS-03 COQUE_3D quad8 – doorbuiging midden**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-03-cq3-n2 | 0.5 | 21 | 0.0019919 | 5.705% |  |
| LS-03-cq3-n4 | 0.25 | 65 | 0.0021017 | 0.507% | 3.49 |
| LS-03-cq3-n8 | 0.125 | 225 | 0.0021133 | 0.043% | 3.57 |
| LS-03-cq3-n16 | 0.0625 | 833 | 0.0021135 | 0.051% | -0.27 |

Richardson (laatste drie meshes): orde p = 5.94, limiet 0.0021135 (+0.052% t.o.v. de referentie).

**LS-03 COQUE_3D quad8 – sigma midden bovenvlak (VM)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-03-cq3-n2 | 0.5 | 21 | 3.6488e+07 | 26.994% |  |
| LS-03-cq3-n4 | 0.25 | 65 | 3.0556e+07 | 6.349% | 2.09 |
| LS-03-cq3-n8 | 0.125 | 225 | 2.9213e+07 | 1.673% | 1.92 |
| LS-03-cq3-n16 | 0.0625 | 833 | 2.8851e+07 | 0.414% | 2.02 |

Richardson (laatste drie meshes): orde p = 1.89, limiet 2.8717e+07 (-0.051% t.o.v. de referentie).

**LS-03 COQUE_3D quad8 – sigma midden ondervlak (VM)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-03-cq3-n2 | 0.5 | 21 | 3.6488e+07 | 26.994% |  |
| LS-03-cq3-n4 | 0.25 | 65 | 3.0556e+07 | 6.349% | 2.09 |
| LS-03-cq3-n8 | 0.125 | 225 | 2.9213e+07 | 1.673% | 1.92 |
| LS-03-cq3-n16 | 0.0625 | 833 | 2.8851e+07 | 0.414% | 2.02 |

Richardson (laatste drie meshes): orde p = 1.89, limiet 2.8717e+07 (-0.051% t.o.v. de referentie).

**LS-03 DKT quad4 – doorbuiging midden**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-03-dkt-n4 | 0.25 | 25 | 0.0021037 | 0.412% |  |
| LS-03-dkt-n8 | 0.125 | 81 | 0.0021112 | 0.058% | 2.84 |
| LS-03-dkt-n16 | 0.0625 | 289 | 0.0021122 | 0.012% | 2.26 |
| LS-03-dkt-n32 | 0.03125 | 1089 | 0.0021124 | 0.003% | 2.07 |

Richardson (laatste drie meshes): orde p = 2.31, limiet 0.0021124 (-0.001% t.o.v. de referentie).

**LS-03 DKT quad4 – sigma midden bovenvlak (VM)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-03-dkt-n4 | 0.25 | 25 | 3.0063e+07 | 4.634% |  |
| LS-03-dkt-n8 | 0.125 | 81 | 2.9032e+07 | 1.044% | 2.15 |
| LS-03-dkt-n16 | 0.0625 | 289 | 2.8805e+07 | 0.256% | 2.03 |
| LS-03-dkt-n32 | 0.03125 | 1089 | 2.8750e+07 | 0.064% | 2.01 |

Richardson (laatste drie meshes): orde p = 2.04, limiet 2.8732e+07 (+0.002% t.o.v. de referentie).

**LS-03 DKT quad4 – sigma midden ondervlak (VM)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-03-dkt-n4 | 0.25 | 25 | 3.0063e+07 | 4.634% |  |
| LS-03-dkt-n8 | 0.125 | 81 | 2.9032e+07 | 1.044% | 2.15 |
| LS-03-dkt-n16 | 0.0625 | 289 | 2.8805e+07 | 0.256% | 2.03 |
| LS-03-dkt-n32 | 0.03125 | 1089 | 2.8750e+07 | 0.064% | 2.01 |

Richardson (laatste drie meshes): orde p = 2.04, limiet 2.8732e+07 (+0.002% t.o.v. de referentie).

**LS-04 hex20 – u_r binnenwand**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-04-h20-n1 | 0.1 | 32 | 9.0257e-05 | 0.591% |  |
| LS-04-h20-n2 | 0.05 | 89 | 9.0740e-05 | 0.059% | 3.33 |
| LS-04-h20-n4 | 0.025 | 287 | 9.0790e-05 | 0.004% | 3.79 |
| LS-04-h20-n8 | 0.0125 | 1019 | 9.0793e-05 | 0.000% | 3.99 |

Richardson (laatste drie meshes): orde p = 3.78, limiet 9.0794e-05 (+0.000% t.o.v. de referentie).

**LS-04 hex20 – sigma_theta binnenwand**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-04-h20-n1 | 0.1 | 32 | 1.6684e+08 | 0.103% |  |
| LS-04-h20-n2 | 0.05 | 89 | 1.6564e+08 | 0.616% | -2.58 |
| LS-04-h20-n4 | 0.025 | 287 | 1.6590e+08 | 0.460% | 0.42 |
| LS-04-h20-n8 | 0.0125 | 1019 | 1.6636e+08 | 0.183% | 1.33 |

Richardson (laatste drie meshes): orde p = -0.83, limiet 1.6530e+08 (-0.818% t.o.v. de referentie).

**LS-04 hex20 – sigma_zz binnenwand**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-04-h20-n1 | 0.1 | 32 | 2.3501e+07 | 17.505% |  |
| LS-04-h20-n2 | 0.05 | 89 | 2.1203e+07 | 6.013% | 1.54 |
| LS-04-h20-n4 | 0.025 | 287 | 2.0331e+07 | 1.656% | 1.86 |
| LS-04-h20-n8 | 0.0125 | 1019 | 2.0083e+07 | 0.415% | 2.00 |

Richardson (laatste drie meshes): orde p = 1.81, limiet 1.9984e+07 (-0.078% t.o.v. de referentie).

**LS-05 COQUE_3D quad8 – sigma_yy in D (VM midden)**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-05-cq3-n2 | 0.625 | 37 | 8.2724e+07 | 10.761% |  |
| LS-05-cq3-n4 | 0.3125 | 121 | 9.1346e+07 | 1.461% | 2.88 |
| LS-05-cq3-n8 | 0.15625 | 433 | 9.2568e+07 | 0.143% | 3.35 |
| LS-05-cq3-n16 | 0.078125 | 1633 | 9.2654e+07 | 0.049% | 1.54 |

Richardson (laatste drie meshes): orde p = 3.81, limiet 9.2661e+07 (-0.042% t.o.v. de referentie).

**LS-05 hex20 – sigma_yy in D**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| LS-05-h20-n2 | 0.625 | 89 | 8.6584e+07 | 6.598% |  |
| LS-05-h20-n4 | 0.3125 | 287 | 9.2088e+07 | 0.660% | 3.32 |
| LS-05-h20-n8 | 0.15625 | 1019 | 9.2629e+07 | 0.077% | 3.10 |
| LS-05-h20-n16 | 0.078125 | 3827 | 9.2660e+07 | 0.043% | 0.85 |

Richardson (laatste drie meshes): orde p = 4.09, limiet 9.2662e+07 (-0.041% t.o.v. de referentie).

**MO-02 hex20 – f1**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-02-h20-n2 | 0.01 | 2079 | 16.745 | 0.205% |  |
| MO-02-h20-n4 | 0.005 | 12893 | 16.732 | 0.132% | 0.64 |

**MO-02 hex20 – f2**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-02-h20-n2 | 0.01 | 2079 | 25.095 | 0.119% |  |
| MO-02-h20-n4 | 0.005 | 12893 | 25.081 | 0.061% | 0.98 |

**MO-02 hex20 – f3**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-02-h20-n2 | 0.01 | 2079 | 104.75 | 0.023% |  |
| MO-02-h20-n4 | 0.005 | 12893 | 104.67 | 0.054% | -1.24 |

**MO-03 DKT – f1**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-03-dkt-k4 | 0.05 | 117 | 88.152 | 0.710% |  |
| MO-03-dkt-k8 | 0.025 | 425 | 88.622 | 0.180% | 1.98 |
| MO-03-dkt-k16 | 0.0125 | 1617 | 88.742 | 0.045% | 2.00 |

Richardson (laatste drie meshes): orde p = 1.98, limiet 88.783 (+0.001% t.o.v. de referentie).

**MO-03 DKT – f2**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-03-dkt-k4 | 0.05 | 117 | 168.25 | 1.454% |  |
| MO-03-dkt-k8 | 0.025 | 425 | 170.1 | 0.372% | 1.97 |
| MO-03-dkt-k16 | 0.0125 | 1617 | 170.57 | 0.094% | 1.99 |

Richardson (laatste drie meshes): orde p = 1.96, limiet 170.74 (+0.003% t.o.v. de referentie).

**MO-03 DKT – f3**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-03-dkt-k4 | 0.05 | 117 | 270.77 | 0.880% |  |
| MO-03-dkt-k8 | 0.025 | 425 | 272.54 | 0.231% | 1.93 |
| MO-03-dkt-k16 | 0.0125 | 1617 | 273.02 | 0.058% | 1.98 |

Richardson (laatste drie meshes): orde p = 1.91, limiet 273.19 (+0.004% t.o.v. de referentie).

**MO-03 DKT – f4**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| MO-03-dkt-k4 | 0.05 | 117 | 301.89 | 1.766% |  |
| MO-03-dkt-k8 | 0.025 | 425 | 305.9 | 0.462% | 1.94 |
| MO-03-dkt-k16 | 0.0125 | 1617 | 306.96 | 0.117% | 1.98 |

Richardson (laatste drie meshes): orde p = 1.92, limiet 307.34 (+0.007% t.o.v. de referentie).

**TH-02 tijdstap (theta 0,5) – T-Ti x=4 mm t=10 s**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| TH-02d1 | 0.4 | 404 | 77.536 | 0.249% |  |
| TH-02e1 | 0.2 | 404 | 77.625 | 0.135% | 0.89 |
| TH-02b | 0.1 | 404 | 77.68 | 0.064% | 1.06 |
| TH-02f1 | 0.05 | 404 | 77.707 | 0.030% | 1.13 |

Richardson (laatste drie meshes): orde p = 1.00, limiet 77.734 (+0.005% t.o.v. de referentie).

**TH-02 tijdstap (theta 0,5) – T-Ti x=8 mm t=10 s**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| TH-02d1 | 0.4 | 404 | 56.779 | 0.667% |  |
| TH-02e1 | 0.2 | 404 | 56.973 | 0.328% | 1.02 |
| TH-02b | 0.1 | 404 | 57.07 | 0.159% | 1.05 |
| TH-02f1 | 0.05 | 404 | 57.118 | 0.075% | 1.09 |

Richardson (laatste drie meshes): orde p = 1.00, limiet 57.166 (+0.009% t.o.v. de referentie).

**TH-02 tijdstap (theta 0,5) – T-Ti x=16 mm t=10 s**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| TH-02d1 | 0.4 | 404 | 25.306 | 1.878% |  |
| TH-02e1 | 0.2 | 404 | 25.548 | 0.939% | 1.00 |
| TH-02b | 0.1 | 404 | 25.668 | 0.474% | 0.99 |
| TH-02f1 | 0.05 | 404 | 25.728 | 0.242% | 0.97 |

Richardson (laatste drie meshes): orde p = 1.01, limiet 25.787 (-0.012% t.o.v. de referentie).

**TH-02 tijdstap (theta 1,0) – T-Ti x=4 mm t=10 s**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| TH-02d2 | 0.4 | 404 | 77.412 | 0.409% |  |
| TH-02e2 | 0.2 | 404 | 77.574 | 0.200% | 1.03 |
| TH-02c | 0.1 | 404 | 77.654 | 0.097% | 1.05 |
| TH-02f2 | 0.05 | 404 | 77.694 | 0.046% | 1.09 |

Richardson (laatste drie meshes): orde p = 1.01, limiet 77.734 (+0.005% t.o.v. de referentie).

**TH-02 tijdstap (theta 1,0) – T-Ti x=8 mm t=10 s**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| TH-02d2 | 0.4 | 404 | 56.646 | 0.900% |  |
| TH-02e2 | 0.2 | 404 | 56.907 | 0.443% | 1.02 |
| TH-02c | 0.1 | 404 | 57.037 | 0.216% | 1.03 |
| TH-02f2 | 0.05 | 404 | 57.102 | 0.103% | 1.07 |

Richardson (laatste drie meshes): orde p = 1.00, limiet 57.166 (+0.009% t.o.v. de referentie).

**TH-02 tijdstap (theta 1,0) – T-Ti x=16 mm t=10 s**

| ID | h | knopen | FEM | fout | orde p |
|---|---|---|---|---|---|
| TH-02d2 | 0.4 | 404 | 25.387 | 1.561% |  |
| TH-02e2 | 0.2 | 404 | 25.585 | 0.796% | 0.97 |
| TH-02c | 0.1 | 404 | 25.685 | 0.406% | 0.97 |
| TH-02f2 | 0.05 | 404 | 25.736 | 0.209% | 0.96 |

Richardson (laatste drie meshes): orde p = 0.99, limiet 25.788 (-0.008% t.o.v. de referentie).

