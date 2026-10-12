---
title: A review waits for its target to be done, not merged
type: architecture
status: accepted
date: 2026-10-10
source: DL-94, DL-144, task 2026-10-08-1733--sae-dogfood-fixes (item 32, [FIX-REVIEW-NO-DEADLOCK], SAE-REVIEWS); DL-86, implementation 2026-10-07
applies-to: [skills/shape-and-execute/scripts/sae_lib/graph.py, works_on_unmerged, waits_for, is_ready, fix_target]
---

# A review waits for its target to be done, not merged

## Context
A job review and an `INTEGRATE-<ID>` job work on their target before it merges. A fix job works
on its target's branch, and the target merges only after its review passes.

## Decision
[agent] A job review and an `INTEGRATE-<ID>` job need their target only `done`, not `merged`.
A job review also needs its target's fix jobs only `done`; the fix merges together with its
target after the review passes. The next job-review round waits for every open fix job of its
target.

## Why
Waiting for the merge would deadlock: round 2 waited for the fix job's merge, which comes only
after round 2 passes, and an agent had to clear `needs` by hand.
