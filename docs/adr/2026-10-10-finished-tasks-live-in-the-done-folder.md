---
title: Finished tasks live in the done folder
type: architecture
status: accepted
date: 2026-10-10
source: DL-117, task 2026-10-08-1733--sae-dogfood-fixes (D15 changed, item 7, [DONE-FOLDER], [DECISION-AGENT-DEFAULTS])
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/tasks.py, move_finished_tasks, commit_task_record, locate_tasks, .tasks/done]
---

# Finished tasks live in the done folder

## Context
Finished task records stayed at the top of `.tasks/`, next to running tasks, the backlog and
the findings.

## Decision
- [human] `sae finish` moves the task folder to `.tasks/done/<task-id>/` in the task-record
  commit. `sae` and the viewer find tasks in both places.
- [agent] The same commit moves any other finished or abandoned task found at the top of
  `.tasks/`, on the task branch only.

## Why
With more than ten tasks a flat `.tasks/` becomes a mess.
