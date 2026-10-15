---
description: Voer stappen uit STAPPENPLAN.md uit (zonder argument de eerstvolgende open stap, daarna door)
argument-hint: "[stap-id, bijv. S4a; S10 = eerste open S10-deelstap; leeg = eerstvolgende open stap]"
---

Voer stappen uit `STAPPENPLAN.md` (root van de repo, op `develop`) volledig en
zelfstandig uit.

Gekozen stap: `$ARGUMENTS`.
- Leeg: de eerste stap in de statustabel **in tabelvolgorde** (= bouwvolgorde) met
  status **open** waarvan de voorwaarde klopt. **later** en **niet gepland** sla je
  over. Meld welke stappen je hebt overgeslagen en waarom.
- `S10` (of een ander id zonder letter): de eerste open deelstap daarvan.

1. Begin met werkwijze **A.1**: `git fetch` en een worktree op `stap-<id>` vanaf
   `develop`. Lees **daarna** vanaf schijf in die worktree `AGENTS.md`,
   `KNOWN_BUGS.md` en `STAPPENPLAN.md` (werkwijze A t/m F en de stap). Vertrouw niet
   op eerder geladen context: die kan van een oude commit zijn.
2. Volg A t/m F letterlijk, inclusief de regel voor een gewijzigde
   `Scripts/bridge_utils.py` in de hoofdcheckout (F.2), het opruimen (F.3) en de
   GUI-test na de merge (D.6).
3. Vraag de gebruiker niet hoe invoer moet: zoek het uit (Mecway zelf, speciale
   groepsnamen, eigen `#ASTER`-sleutelwoord), kies en documenteer. Stop alleen in de
   gevallen onder **Stoppen en melden**.
4. Is een stap te groot voor één run: bouw een bruikbaar, geverifieerd deel en splits
   de rest als nieuwe regels in de statustabel (bijv. `S3a`, `S3b`).
5. Na een afgeronde stap zonder stopreden: ga door met de volgende open stap (F.5).
   Vragen verzamel je in Bevindingen en in het eindrapport.
6. Eindig met een kort rapport in de taal van de gebruiker: per stap wat er gebouwd is,
   hoe je het in Mecway gebruikt (met verwijzing naar de doc), de verificatie (getallen
   tegen de tolerantie), wat wel en niet in de Mecway-GUI getest is, open vragen, en de
   volgende stap.
