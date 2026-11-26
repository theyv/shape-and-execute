---
status: done
summary: execute, plan and shape keep a reopened done job unparked only when sae refuses for a missing CLI; a follow-up COMMAND that starts and fails is parked like a running job
validation: pass
changes: made
resolved: []
---

# Result: PROMPT-TEXT-FIX-2

## Validation evidence
- REVIEW-PROMPT-TEXT-2 finding 1 checked against the code: `progress.py` `cmd_dispatch` appends an attempt and sets `status = "running"` after the `--resume` checks pass, so a reopened job whose COMMAND then fails is running, not done. Finding confirmed.
- execute.md Loop step 2, plan.md (planner subagent) and shape.md step 7 now limit the stays-done rule to the missing-CLI refusal. A started-then-failed COMMAND follows the running-job rule: outside `full-auto`, park it, ask, and on the yes run the fallback with `--resume`.
- `python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers`: 71 tests OK. `grep -q "accept-review" .../execute.md`: OK. `git diff --check`: clean.
- Commit on branch job/.../PROMPT-TEXT (HEAD after 9633af6).

## Decisions taken
- [agent] plan.md and shape.md spell out the `sae job park` command for the failed case. execute.md says "park it as above", because the park command sits two lines earlier in the same step.

## Risks
- The missing-CLI refusal for a `--resume` dispatch is spec'd for WRITER-LAUNCH ([HARNESS-FALLBACK]) and is not in `progress.py` yet. The prompt text assumes that refusal happens before the attempt is recorded, so the job stays done. WRITER-LAUNCH should keep that order.

## Findings filed
None.
