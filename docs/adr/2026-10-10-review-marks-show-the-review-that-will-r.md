---
title: Review marks show the review that will really run
type: architecture
status: accepted
date: 2026-10-10
source: DL-91, DL-146, task 2026-10-08-1733--sae-dogfood-fixes (D19 changed, item 17b, R5, R6, [JOB-REVIEW-FLAG-HONESTY])
applies-to: [skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/scripts/sae_lib/control.py, skills/shape-and-execute/references/roles/planner.md, skills/shape-and-execute/assets/viewer/task-views.js, review_mark, unreviewed_flagged]
---

# Review marks show the review that will really run

## Context
The planner can flag a job for review, but the task's review points decide whether job reviews
run. The graph showed "review due" from the flag alone, and two flagged jobs merged
unreviewed, because the review points had no `selected-jobs`.

## Decision
[human] Each job shows the review that will really run, and why: a review forced by the
settings (an unflagged job under `all-jobs`), or a struck-through flag when job reviews are
off. A tooltip says why and on which model and effort the review is planned. `sae check` warns
about flags that will not run; the plan's next-step card lists them in one line. Nothing asks
the owner. The planner flags jobs only when job reviews are on. The viewer's label comes from
the effective mark, never from the flag alone [agent].

## Why
A mark must not promise a review that will not happen.

## Rejected options
- A question to the owner (D19 as first proposed).
- A flag that implies a review: it would override the owner's review points.
