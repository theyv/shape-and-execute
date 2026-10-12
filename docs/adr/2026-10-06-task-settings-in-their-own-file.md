---
title: Task settings in their own file
type: architecture
status: accepted
date: 2026-10-06
source: DL-21, design interview 2026-10-06 (Q33)
applies-to: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/planning.py, new_task_settings, settings_errors, cmd_set, settings.json]
---

# Task settings in their own file

## Context
A task's settings (interaction mode, levels, review points, overrides) change during a run,
from the CLI and from the viewer, while `sae` also writes the task state.

## Decision
[joint] Task settings live in `settings.json`, separate from `state.json`.

## Why
With both in one file, two writers (the CLI and the viewer) would overwrite each other's
changes, most likely during a run.

## Rejected options
- Settings as a header inside `state.json` (the owner's question).
