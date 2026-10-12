---
title: Task IDs carry date and time
type: architecture
status: accepted
date: 2026-10-06
source: DL-17, design interview 2026-10-06 (Q23, Q30)
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/common.py, cmd_new, slugify, file_stamp]
---

# Task IDs carry date and time

## Context
Task IDs name folders, branches and commit trailers. They must sort well and must not collide
when several people or branches create tasks.

## Decision
[joint] A task ID is `YYYY-MM-DD-HHMM--slug`. Findings and backlog items use the same pattern
[human].

## Why
The agent proposed dropping the counter for teams; the owner pointed out that many tasks on one
day would then sort by slug. Time in the ID fixes both: no counter to collide on, and a
chronological order.

## Rejected options
- A counter in the ID: two people on two branches would produce the same ID.
- Date and slug only: many tasks on one day sort by slug.
