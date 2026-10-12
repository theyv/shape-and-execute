---
title: Finish refuses unresolved review findings
type: architecture
status: accepted
date: 2026-10-10
source: DL-87, task 2026-10-08-1733--sae-dogfood-fixes (D1, item 21, [FINISH-VERDICT-GATE], DOCS-FIX)
applies-to: [skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, verdict_gate, check_finish_gates, cmd_finish, --override]
---

# Finish refuses unresolved review findings

## Context
Two pilot-project tasks finished with an integration review that said `changes-required`:
`sae finish` checked the review job's status, not its verdict. The agent report of that day
called this the most important fix.

## Decision
[agent] `sae finish` refuses while the last round of the integration review, or of a job review
of an unmerged job, says `changes-required`. `--override "<reason>"` passes; the event and the
final report keep the reason. The gates judge the code that `finish` closes: a writer that
`finish` would still merge counts as a late merge. The refusal names the fix target: the
reviewed job for a job review, the round ID for the integration review. The override also
passes the jobs these gates hold back (a stale integration round, a final validation waiting
for a passed round), which stay pending; finishing with open jobs alone never does.

## Why
A task must not close with review findings nobody resolved, least of all in a `full-auto` run.

## Rejected options
- A warning only: a `full-auto` run would still close the task.
