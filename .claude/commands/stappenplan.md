---
description: Carry out steps from STAPPENPLAN.md (without an argument the next open step, then continue)
argument-hint: "[step id, e.g. S4a; S10 = first open S10 sub-step; empty = next open step]"
---

Carry out steps from `STAPPENPLAN.md` (root of the repo, on `develop`) completely and
independently.

Chosen step: `$ARGUMENTS`.
- Empty: the first step in the status table **in table order** (= build order) with
  status **open** whose prerequisite is met. Skip **later** and **not planned**.
  Report which steps you skipped and why.
- `S10` (or another id without a letter): its first open sub-step.

1. Start with procedure **A.1**: `git fetch` and a worktree on `stap-<id>` from
   `develop`. **Then** read from disk in that worktree `AGENTS.md`,
   `KNOWN_BUGS.md` and `STAPPENPLAN.md` (procedure A to F and the step). Do not rely
   on previously loaded context: it may be from an old commit.
2. Follow A to F literally, including the rule for a changed
   `Scripts/bridge_utils.py` in the main checkout (F.2), the clean-up (F.3) and the
   GUI test after the merge (D.6).
3. Do not ask the user how input should work: research it (Mecway itself, special
   group names, an own `#ASTER` keyword), choose and document it. Stop only in the
   cases under **Stop and report**.
4. If a step is too big for one run: build a usable, verified part and split
   the rest off as new rows in the status table (e.g. `S3a`, `S3b`).
5. After a finished step without a reason to stop: continue with the next open step (F.5).
   Collect questions in Findings and in the final report.
6. End with a short report in the user's language: per step what was built,
   how to use it in Mecway (with a reference to the doc), the verification (numbers
   against the tolerance), what was and was not tested in the Mecway GUI, open questions,
   and the next step.
