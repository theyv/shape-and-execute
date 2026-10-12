---
title: Jobs with semantic IDs instead of waves
type: architecture
status: accepted
date: 2026-10-06
source: DL-13, design interview 2026-10-06 (Q6)
applies-to: [skills/shape-and-execute/templates/job.md, skills/shape-and-execute/scripts/sae_lib/graph.py, JOB_ID_RE, needs]
---

# Jobs with semantic IDs instead of waves

## Context
The plan splits the work into units that fresh workers do. The notes called them "waves",
numbered in files.

## Decision
[joint] The unit is a "job" with `needs` (its dependencies). Job IDs are readable names such as
`STATUS-API` [human].

## Why
Elsewhere "wave" means a batch of parallel work, and numbered wave files suggest an order that
does not exist. "Job" with `needs` has the exact meaning, known from CI.

## Rejected options
- "Wave" as the unit name.
- Numbered wave files.
