---
title: Levels per phase and difficulty per job
type: architecture
status: accepted
date: 2026-10-10
source: DL-56, design interview 2026-10-06 (Q8, Q15); rungs replaced by DL-95, task 2026-10-08-1733--sae-dogfood-fixes
applies-to: [skills/shape-and-execute/scripts/sae_lib/common.py, skills/shape-and-execute/scripts/sae_lib/routing.py, skills/shape-and-execute/scripts/sae_lib/planning.py, DIFFICULTIES, job_context, cmd_set]
---

# Levels per phase and difficulty per job

## Context
Research, planning, execution and review need different model power, and so do single jobs.
Quotas run low in the middle of a run.

## Decision
[joint] Each phase (research, planning, execution, review) has its own level: `economy`,
`balanced` or `max`. Each job has a difficulty: `mechanical`, `normal` or `hard`. Routing
tables map level and difficulty to a model and an effort (see [Routing tables replace rungs and level maps](2026-10-10-routing-tables-replace-rungs-and-level-m.md)). Levels can change at any time; the next dispatch uses the change.

## Why
The owner: research and implementation often need different power, and quotas run low
mid-run.

## Rejected options
- One effort profile per task.
- Per-harness rungs with a level map (replaced by the routing tables).
