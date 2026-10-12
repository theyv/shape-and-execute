---
title: Checks always cover the code that will be merged
type: architecture
status: accepted
date: 2026-10-10
source: DL-89, DL-143, task 2026-10-08-1733--sae-dogfood-fixes ([NO-STALE-CHECKS], SAE-REVIEWS)
applies-to: [skills/shape-and-execute/scripts/sae_lib/reviews.py, stale_gate, merged_after, reset_final_after_late_merge, finish_merges, check_finish_gates]
---

# Checks always cover the code that will be merged

## Context
A writer can merge after the integration review passed or the final validation ran: a job
added during execution, a fix after a failed final validation. The checks then describe code
that is no longer the task's code.

## Decision
- [joint] A writer merged after the integration review passed adds the next round, limited to
  the new changes, and sets the final validation back to pending. `finish` refuses until both
  ran again, unless overridden with a reason.
- [agent] A done writer that `finish` would merge after an integration round or the final
  validation ran makes `finish` refuse before it merges, naming `sae merge <task> <ID>` and then
  `sae next`; `--override` merges it and closes. Late merges are found from events
  (`job.merged` after the last round's `review.completed`), not from stored state.

## Why
The spec review (Codex) found that a late merge would leave the checks stale; the owner
accepted the finding.

## Rejected options
- Re-checking the gates after every merge: a second path through `finish` for a rare case.
