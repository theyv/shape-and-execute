---
title: Backlog pickup at start, and start is atomic
type: architecture
status: accepted
date: 2026-10-10
source: DL-114, DL-142, task 2026-10-08-1733--sae-dogfood-fixes (D4, item 13, [BACKLOG-PICKUP], DOCS-FIX, DOCS-FIX-2, SAE-TASK-WORKTREE)
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, cmd_start, pickup_item, commit_backlog_pickup, pickup_item_untracked, copy_untracked_repo_files, check_models]
---

# Backlog pickup at start, and start is atomic

## Context
The pilot-project pickup of a backlog item failed halfway (`git rm --cached` plus a pathspec
commit). It left a switched branch and an orphaned deletion (`research/FORENSICS.md` §4 in the
record of task 2026-10-08-1733--sae-dogfood-fixes).

## Decision
[agent] `sae new --from` keeps the backlog file. `sae start` removes it in the task worktree and
commits the removal as the first commit on the task branch; an item that was never committed
moves into the task worktree with the task folder and is deleted there once the start
succeeded. `start` is atomic:
- it refuses before it changes anything when the task folder is committed on HEAD, the task
  branch or worktree path exists, or a pending job cannot be routed;
- if any later step fails, nothing new remains (branch, worktree, moved files): a stack of undo
  steps runs in reverse, the task stays in `planning` with its approvals, and a second run
  works.

`start` moves the task folder and copies the untracked `.tasks/repo/` files before it runs the
task worktree's setup, so a repository's first task uses its new setup files; the home checkout
keeps them.

## Why
A failed start must leave nothing to repair by hand, and the backlog must never show started
work as open.

## Rejected options
- Deleting an untracked item from the home checkout: the removal belongs in the task worktree,
  and a failed start could not restore it.
- Moving the untracked `.tasks/repo/` files into the task worktree: a second task started from
  the home checkout would lack its setup.
