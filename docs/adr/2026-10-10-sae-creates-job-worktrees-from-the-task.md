---
title: sae creates job worktrees from the task branch
type: architecture
status: accepted
date: 2026-10-10
source: task 2026-10-08-1733--sae-dogfood-fixes
applies-to: [skills/shape-and-execute/scripts/sae_lib/workspaces.py, prepare_workspace, job_branch, setup_worktree, task_worktrees_dir]
revisit-when: Claude Code bases subagent worktrees on the parent's HEAD and Codex gets per-subagent worktrees
---

# sae creates job worktrees from the task branch

## Context
Writers that run in parallel need separate workspaces, each starting from the current task
branch. Both harnesses have their own worktree features.

## Decision
- [agent] `sae` creates job worktrees with `git worktree add` from the task branch.
- [agent] Writers of a chain run in the task worktree. Job worktrees exist only when writers run
  in parallel, and then every writer gets one.

## Why
Harness isolation cannot do it in both harnesses. Claude Code bases a subagent's worktree on
the default branch, not on the parent's HEAD; Codex has no per-subagent worktrees
([research/claude-code-facts.md](research/claude-code-facts.md),
[research/codex-facts.md](research/codex-facts.md) "Subagents").

## Rejected options
- The harnesses' own worktree isolation.
- Chain writers in the owner's checkout (replaced by the task worktree; see [Every task executes in its own task worktree](2026-10-10-every-task-executes-in-its-own-task-work.md)).
