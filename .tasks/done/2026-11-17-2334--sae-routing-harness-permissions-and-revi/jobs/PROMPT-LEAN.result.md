---
status: done
summary: Applied lean-audit proposals 1–9 to the prompt files in one commit (ef5b4b9); orchestrator mode files keep pointer sentences.
validation: pass
changes: made
resolved: []
---

# Result: PROMPT-LEAN

## Proposals applied (line numbers at 34876a1)

| # | file | lines changed |
|---|---|---|
| 1 | references/modes/execute.md | 33–46 → 4-line Loop step 2 |
| 1 | references/modes/plan.md | 12–21 → 2 lines; optional 41–43 → 2 lines |
| 1 | references/modes/shape.md | 52–55 → 3 lines; 65–72 → 2 lines; optional 132–134 → 2 lines |
| 2 | references/modes/execute.md | 63–86 → 12-line changes-required bullet (Approach proposal bullet merged in) |
| 3 | references/modes/execute.md | 5–6 → "read only that section" sentence (line 104 example kept) |
| 4 | SKILL.md | 18: **care** → **stakes** |
| 5 | references/modes/setup.md | 68–69 swapped (luna, terra, sol, astra); 81: `(luna → terra → sol → astra)` |
| 6 | references/modes/setup.md | 17–29 → 7-line upgrade paragraph |
| 7 | references/modes/shape.md | 29–32 → 3 lines |
| 8 | references/interaction-modes.md | 56–58 → pointer to execute.md "Finish", step 3 |
| 9 | references/roles/reviewer.md | 59–64 → 5 lines |

## Line counts (before → after)

SKILL.md 108 → 108; interaction-modes.md 61 → 61; execute.md 180 → 158; plan.md 98 → 89;
setup.md 215 → 209; shape.md 145 → 136; reviewer.md 74 → 73. Total −47 (49 added, 96 removed).

## Validation evidence

- `python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers`: 71 tests OK.
- All five grep verifies pass (accept-review, sae job drop, luna order, no **care**, **stakes** line).
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Checklist: execute.md, plan.md and shape.md hold no fallback branch logic (no job kind,
  status or mode branches; no IF IT FAILS / park / log text); execute.md Loop step 3 names
  triage, `[beyond stakes]`, `--let-go`, `sae job drop` only on the user's word, and
  `accept-review`; only "care" left in prompt files is planner.md's ordinary noun, not an axis.
- No test asserted removed text; no test change was needed.

## Decisions taken

- [agent] Light smoothing only: plan.md/shape.md optional duplicates became "When it prints a
  COMMAND, follow what it prints. Collect it." as the audit proposed.

## Risks

- Until WRITER-LAUNCH, FIX-LOOP-EXITS and FIX-LOOP-GUIDANCE land, the fallback, round-limit
  and fix-round rules are printed nowhere (expected per job boundaries).
