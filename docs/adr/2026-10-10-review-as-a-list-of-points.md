---
title: Review as a list of points
type: architecture
status: accepted
date: 2026-10-10
source: DL-40, design interview 2026-10-06 (Q9, Q29, Q36); DL-123, task 2026-10-08-1733--sae-dogfood-fixes (planner)
applies-to: [skills/shape-and-execute/scripts/sae_lib/common.py, skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/assets/viewer/settings.js, REVIEW_POINTS, review_due, planned_reviews, selected-jobs, all-jobs]
---

# Review as a list of points

## Context
A task can review its spec, its plan, single jobs and the whole change. The settings must say
which, for each task.

## Decision
- [joint] The review setting is a list of points: `spec`, `plan`, `selected-jobs` or
  `all-jobs`, `integration`. An empty list means no review. The `spec` point has its own record
  ([Spec review](2026-10-06-spec-review.md)).
- [agent] Task settings keep the values `selected-jobs` and `all-jobs`. The viewer shows them as
  one `jobs` checkbox with the switch "agent-selected jobs | all jobs".

## Why
- The owner wanted descriptive names and an explicit integration review. A list avoids preset
  names for every combination.
- Keeping the two values needs no migration of existing tasks; the spec allowed either form.

## Rejected options
- Named presets that combine review targets.
- One `jobs` value in `settings.json`: it would need a migration of existing tasks.
