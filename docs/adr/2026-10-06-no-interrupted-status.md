---
title: No interrupted status
type: architecture
status: accepted
date: 2026-10-06
source: DL-22, design interview 2026-10-06 (D9)
applies-to: [skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/assets/viewer/task-views.js, age_text, last_change]
---

# No interrupted status

## Context
When a session ends or a worker dies, its job still shows `running`. A status for such a job
was proposed.

## Decision
[human] There is no "interrupted" status. `sae status` and the viewer show "last change N min
ago" for a running job, not "running for N min".

## Why
"Running for N min" would claim that the job still works. An "interrupted" status would be
visible only for a moment, at resume, so it adds nothing.

## Rejected options
- An "interrupted" status.
- "Running for N min".
