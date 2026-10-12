---
title: Setup files come from the main worktree
type: architecture
status: accepted
date: 2026-10-10
source: DL-116, task 2026-10-08-1733--sae-dogfood-fixes (D23, item 26, [SETUP-SOURCE])
applies-to: [skills/shape-and-execute/scripts/sae_lib/workspaces.py, copy_worktree_includes, task_copy_sources, setup_copy]
---

# Setup files come from the main worktree

## Context
A new worktree needs ignored files such as `.env` or `node_modules`, listed in the
`worktreeinclude` file. Started from a secondary checkout without `node_modules`, setup
"succeeded" and the worktrees had no dependencies.

## Decision
[agent] Listed ignored files are copied from the repository's main worktree; when missing
there, from the checkout that runs `sae`. A missing listed file is reported.

## Why
A setup that "succeeds" without its files fails only later, in the jobs. Agent's reasoning: the
main worktree is the checkout that most likely holds the full setup.
