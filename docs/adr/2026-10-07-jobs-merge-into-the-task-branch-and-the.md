---
title: Jobs merge into the task branch and the owner merges the task
type: architecture
status: accepted
date: 2026-10-07
source: DL-45, design interview 2026-10-06 (Q19, D11); DL-72, genesis review 2026-10-07 (stop A)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, merge_job, cmd_merge, cmd_finish]
---

# Jobs merge into the task branch and the owner merges the task

## Context
A task's jobs change the code in many steps. The base branch belongs to the owner. The genesis
review proposed gates between waves of jobs.

## Decision
- [joint] Each task has its own task branch. The base branch stays untouched, nothing is pushed,
  and the owner merges the task branch.
- [human] `sae` merges each job into the task branch as soon as it is done and reviewed. There
  is no stop at dependency or wave boundaries, in any interaction mode.

## Why
- Nothing reaches the base branch without the owner, so even `full-auto` has a safety net: the
  task branch and the final report.
- The owner first wanted stops outside the auto modes, then: "If the changes go to the task branch, keep the existing behavior.".

## Rejected options
- Genesis A5 WAVE EXECUTION: a gate between waves.
- A human stop before each merge.
