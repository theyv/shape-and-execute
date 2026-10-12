---
title: Commands never write into a finished task
type: architecture
status: accepted
date: 2026-10-10
source: DL-118, DL-142, task 2026-10-08-1733--sae-dogfood-fixes (D21, item 24, [FINISHED-TASKS-READ-ONLY], SAE-TASK-WORKTREE)
applies-to: [skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, open_task, refuse_closed, new_backlog_item]
---

# Commands never write into a finished task

## Context
`sae new --backlog --source <task>` appended a `backlog.created` event to the source task. For
a finished task, that dirtied a committed task record for good.

## Decision
[agent] No command writes into a finished task. A backlog item records its source only in its
own file. A read-only command may load a closed task; a writing command refuses it.

## Why
The event dirtied a committed task record for good. A finished record stays as it was
committed.
