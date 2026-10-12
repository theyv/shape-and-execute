---
title: One flat task folder with files only for content
type: architecture
status: accepted
date: 2026-10-06
source: DL-09, DL-14, design interview 2026-10-06 (Q12, D2, D4, D21, D22)
applies-to: [skills/shape-and-execute/templates, skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/references/modes/plan.md]
---

# One flat task folder with files only for content

## Context
A task needs a place for its intent, spec, plan, jobs, results, settings and state. Small and
large tasks need different amounts of it.

## Decision
- [joint] Every task has one layout. A file exists only when it has content.
- [agent] The task folder is flat and has no `run.md`. The protocol lives in the skill, settings
  in `settings.json`, the graph in `state.json`, the planner's reasoning in `plan.md`.

## Why
- One layout means one code path and no migration between layouts.
- Each fact has one home, so nothing has to be kept in sync with a run file.

## Rejected options
- A compact single `task.md` layout for small tasks: two code paths and a migration between
  layouts.
- A full set of thin files for every task: ceremony.
- A `run.md` that repeats the protocol and state.
