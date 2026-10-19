---
status: done
summary: CLEANUP-LIST (hold) ∥ DISPATCH-POINTERS ∥ WRITING-RULES → CLEANUP-APPLY → VALIDATE-ALL (final)
validation: pass
changes: made
resolved: []
---

# Result: PLAN

## Validation evidence
- `sae check 2026-10-19-1603--adr-cleanup-and-dispatch-pointers`: no errors. One warning, about
  the shaping job file `NESTED-AGENTS-MD.md` (objective longer than one sentence). That job is
  done, and the warning does not affect the plan.
- Coverage: CLEANUP-LIST → [CLEANUP-LIST]; DISPATCH-POINTERS → [WORKER-POINTERS],
  [REVIEW-POINTERS], [DIR-POINTERS], [POINTER-LIMIT], [INDEX-POINTER], [PLANNER-SCOPE], [TESTS];
  WRITING-RULES → [THREE-PLACES], [REVISIT-WHEN]; CLEANUP-APPLY → [CLEANUP-APPLY];
  VALIDATE-ALL → the full suite and the cross-checks.
- `plan.md` lists the riskiest assumptions.

## Decisions taken
- [agent] CLEANUP-LIST is an `implementation` job that changes nothing (`changes: none`). It
  writes the list to its result file. A `research` job would block the plan approval
  (`sae approve` refuses while a research job is open). **The orchestrator must run
  `sae hold <task> CLEANUP-LIST` before the first dispatch.**
- [agent] CLEANUP-APPLY waits for DISPATCH-POINTERS and WRITING-RULES as well as the list. Moved
  comments may land in skill files those jobs edit. The extra wait costs little, because the
  hold is usually the longest wait.
- [agent] The list also flags kept records whose path entries name no existing path.
  CLEANUP-APPLY fixes those where the approved list says so.
- [agent] No `--review` flags: the review points are `integration` only.

## Risks
- Directory `AGENTS.md` files and comments under `skills/shape-and-execute/` ship with every
  install. The owner sees each target in the list at the hold.

## Findings filed
None.
