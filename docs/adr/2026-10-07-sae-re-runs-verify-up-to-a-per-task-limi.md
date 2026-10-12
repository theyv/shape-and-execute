---
title: sae re-runs verify, up to a per-task limit
type: architecture
status: accepted
date: 2026-10-07
source: DL-33, design interview 2026-10-06 (D26); DL-73, genesis review 2026-10-07 (G1); DL-83, DL-86, implementation 2026-10-07
applies-to: [skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/references/roles/worker.md, run_verify, cmd_collect, max_verify_failures]
---

# sae re-runs verify, up to a per-task limit

## Context
A worker reports `done`. That is a claim: its `verify` commands may still fail.

## Decision
- [joint] Workers verify themselves, deterministically and by judgement. `sae collect` re-runs
  the job's declared `verify` commands. A mismatch goes back to the same worker (resume).
- [human] A per-task limit, `max_verify_failures`: at that count `sae collect` records the job
  as `failed` instead of sending it back again. No agent asks about it; it is not on the
  settings card; the owner changes it in the viewer or with `sae set`.
- [human] The default, 3, lives in the code of `sae`, like its other numeric limits
  (location `[joint]`). `config.defaults.max_verify_failures` may set another value for new
  tasks.
- [agent] `sae collect` counts the job's commits since its first dispatch, not since the current
  attempt.

## Why
- The owner accepted the token cost of a resume for a deterministic check of every "done".
- Without a limit, a worker that keeps claiming `done` while `verify` fails would loop without
  end and burn quota, worst in `full-auto` (genesis finding A11, unbounded per-item retries).
  The worker's own attempts inside one dispatch stay unlimited.
- The default is not a configuration value of the skill. The owner: "This is implemented in the application rather than the skill, so changing it requires a code change.".
- A resumed worker may have committed in an earlier attempt and fix nothing new in git.
