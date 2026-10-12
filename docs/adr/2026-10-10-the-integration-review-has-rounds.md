---
title: The integration review has rounds
type: architecture
status: accepted
date: 2026-10-10
source: DL-88, DL-144, task 2026-10-08-1733--sae-dogfood-fixes (D2, item 21, [INTEGRATION-REVIEW-ROUNDS], DOCS-FIX, SAE-REVIEWS)
applies-to: [skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/scripts/sae_lib/graph.py, skills/shape-and-execute/scripts/sae_lib/planning.py, materialize_integration_review, apply_integration_review, integration_parked, fix_target, --fix-of]
---

# The integration review has rounds

## Context
An integration review that says `changes-required` gets fix jobs. `sae` could not re-run a done
review, so an agent had to invent an `INTEGRATION-RECHECK` validation job.

## Decision
- [agent] Fix jobs declare `--fix-of <integration review ID>`. When all of them are merged,
  `sae` adds the next round (`REVIEW-INTEGRATION-2`, …), limited to the earlier findings.
- [agent] After a second `changes-required`, the task parks for the owner, as job reviews do.
  While the task is parked no job is ready and `sae dispatch` refuses new work; running jobs
  finish and are collected; a fix job of the round ends the parking.
- [agent] The final validation waits for a round that passed, not only for a done one.
- [agent] Integration fix jobs get no job review, even under `all-jobs`: the next round reviews
  them.

## Why
- A re-check is a review round, not a job an agent invents.
- A job review of a fix job would review the same change twice; the next integration round
  already covers it.
