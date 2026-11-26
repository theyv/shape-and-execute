---
target: PROMPT-TEXT
verdict: changes-required
---

# Review: REVIEW-PROMPT-TEXT-2

## Findings

### 1. A failed follow-up command can leave the job running — major

**Evidence:** `references/modes/execute.md:35–43`, `references/modes/plan.md:12–17`, and `references/modes/shape.md:65–70` say a reopened job stays `done` whenever it needs fallback. `scripts/sae_lib/progress.py:413–421` records a new attempt and marks the job `running` when dispatch succeeds.

**Affects:** [HARNESS-FALLBACK] and first-round finding 2.

**Why it matters:** A missing CLI leaves the prior result `done`. If the CLI is present and the follow-up COMMAND exits with an error, the new attempt is already `running`. Applying the `done` instructions in that case leaves a failed attempt marked `running` while the owner decides.

**Correction:** Limit the `done` exception to a missing-CLI refusal. If a follow-up COMMAND starts and fails, use the running-job rule. Outside `full-auto`, park the failed attempt, record the ask, and wait for approval before retrying with `--resume`.

## Notes

First-round findings 1, 3, and 4 are resolved in the prompt text. The fix result records the CLI follow-ups for the Approach proposal notice and the printed fix ID. `git diff --check` passed. Tests were not rerun during this read-only review.