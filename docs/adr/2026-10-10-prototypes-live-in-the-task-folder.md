---
title: Prototypes live in the task folder
type: architecture
status: accepted
date: 2026-10-10
source: DL-135, task 2026-10-08-1733--sae-dogfood-fixes (R3, [PROTOTYPES-FOLDER])
applies-to: [skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/scripts/sae_lib/server.py, prototype_files, prototype_url, prototypes]
---

# Prototypes live in the task folder

## Context
Shaping sometimes produces mockups and throwaway prototypes.

## Decision
[human] Mockups and throwaway prototypes made for a task go to
`.tasks/<task-id>/prototypes/`. The viewer lists and serves them.

## Why
They do not litter the repository, and they stay with the task record that explains them.
