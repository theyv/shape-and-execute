---
type: defect
confidence: high
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/FIX-LOOP-TEXTS
paths: [skills/shape-and-execute/scripts/sae_lib/reviews.py]
---

# Finish refusal offers a close-anyway that cannot pass for a job review

## Observation
sae finish refused for a job review that says changes-required prints "or close anyway, on the user's word: sae finish <task> --override "<reason>"". In a task with a final validation that needs the job, that command cannot pass: without --with-open it stops at "Open jobs: FINAL", and with --with-open --override it stops at "The final validation FINAL is not done" (check_finish_gates: verdict_gate holds the final validation only for an integration round). Reproduced with one reviewed job A, FINAL needs A, max-review-rounds=1. FIX-LOOP-TEXTS therefore did not add "close anyway" to the job park or to the job round message; the finish refusal still prints it for job reviews. Either make --override pass a held job review (leave the job out, like a drop) or print the line only when it can pass.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
