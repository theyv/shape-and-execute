---
title: Every task executes in its own task worktree
type: architecture
status: accepted
date: 2026-10-10
source: task 2026-10-08-1733--sae-dogfood-fixes
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/scripts/sae_lib/workspaces.py, cmd_start, start_task_worktree, source_items, cmd_abandon, move_back_home, locate_tasks, task_checkouts, live_checkout, task_worktree_path]
---

# Every task executes in its own task worktree

## Context
`sae start` used to switch the owner's checkout to the task branch, and chain writers ran
there. Parallel work is the owner's normal case: a scan committing on `main`, Orca worktrees.

## Decision
- [joint] `sae start` creates a task worktree on the task branch and never switches the owner's
  checkout; uncommitted changes there only produce a warning. Chain writers run in the task
  worktree; job worktrees branch from it and merge into it. There is no in-place option.
- [joint] Every `sae` command finds the task in any worktree of the repository: it looks in
  `.tasks/<id>/` and `.tasks/done/<id>/` of every worktree, and a live (untracked) folder wins
  over a committed record [agent].
- [agent] At `sae start` the task folder moves from the home checkout into the task worktree,
  with the task's untracked findings, backlog items and decision drafts (by `source`), so
  `finish` commits them. `sae finding new`, `sae new --backlog` and `sae adr new` write into
  the checkout that holds the source task's live folder. `sae abandon` moves the task folder
  back home before it removes worktrees. `sae start` on an executing task resumes it.

## Why
- Parallel work is the normal case, and one path is simpler than two. Cost: each task pays the
  worktree setup once.
- Files written for a task must end up in its record, wherever the command runs.

## Rejected options
- `sae start` switching the current checkout (the earlier rule).
- Chain writers in the owner's checkout.
- A `--worktree` option next to in-place execution: two paths.
- Resolving the repository root to the main checkout, and `sae status` listing only this
  checkout's tasks (replaced by discovery across worktrees).

## Consequences
- A transition rule let tasks that an older `sae` executed in place finish there.
