---
type: defect
confidence: high
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/FINAL-VALIDATION
paths: []
---

# sae job edit --help describes --no-review as flag the job for review

## Observation
In `sae job edit --help`, --no-review shows the same help as --review: 'flag the job for review (review point selected-jobs)'. It should say that it removes the review flag. Seen in the final validation of the routing task; the parser is in scripts/sae_lib/planning.py (job edit, --review/--no-review).

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
