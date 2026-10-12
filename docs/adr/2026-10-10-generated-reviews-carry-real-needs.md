---
title: Generated reviews carry real needs
type: architecture
status: accepted
date: 2026-10-10
source: DL-90, DL-146, task 2026-10-08-1733--sae-dogfood-fixes (D3, item 17, R6, R7, [GENERATED-JOB-EDGES], VIEWER-TASK-VIEWS)
applies-to: [skills/shape-and-execute/scripts/sae_lib/graph.py, skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/assets/viewer/task-views.js, add_generated_job, place_final_after, planned_reviews, generated_needs]
---

# Generated reviews carry real needs

## Context
`sae` adds reviews by itself. `REVIEW-INTEGRATION` appeared in the first column of the graph
with no edge to the final validation, and the owner could not see that an integration review
would happen at all.

## Decision
- [human] Generated reviews carry real `needs`: the integration review needs every writer job,
  a job review its job, the final validation the last integration round. Later rounds keep
  these edges (fix jobs and late writers are writers too; a job review's round also needs the
  round's fix jobs). `sae` marks these edges as its own, so the viewer never shows them as plan
  changes.
- [human] Before a review exists, the viewer draws it as a dotted, semi-transparent "planned"
  node in its final place. Planned nodes do not count in progress. Planned spec and plan
  reviews show as chips, not nodes [agent].

## Why
The owner must see from the graph which reviews will run and where.

## Rejected options
- A placement in the viewer only: other readers of `state.json` would not see the rule.
