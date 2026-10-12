---
title: Two review rounds, then park
type: architecture
status: accepted
date: 2026-10-12
source: DL-43, design interview 2026-10-06; DL-144, task 2026-10-08-1733--sae-dogfood-fixes (SAE-REVIEWS); task 2026-10-12-1846--sae-findings-docs [PARKED-THEN-PASSED]
applies-to: [skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/scripts/sae_lib/graph.py, skills/shape-and-execute/scripts/sae_lib/tasks.py, apply_review, merge_job, review_rounds, parked_reason]
---

# Two review rounds, then park

## Context
A job review that says `changes-required` gets fix jobs and then another round. Without a
limit, review and fix could loop.

## Decision
- [agent] After a second `changes-required` round, the job parks for the owner. The integration
  review follows the same rule (see [The integration review has rounds](2026-10-10-the-integration-review-has-rounds.md)).
- [agent] A new fix job for a target parked after round 2 sets the target back to `done`, and
  the next round runs.
- [human] A later round that passes ends the park: the job ends `done` and merged, not
  `parked`.

## Why
- Agent's reasoning: review and fix must not loop without end. A second `changes-required`
  after a fix means the problem needs the owner, not another round.
- The owner's word when a parked job's later round passed and `sae` kept it parked (finding of
  2026-10-10).

## Consequences
- The owner has not confirmed the number of rounds yet; it was listed for confirmation.
