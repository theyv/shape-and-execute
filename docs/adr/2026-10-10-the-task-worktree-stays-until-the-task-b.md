---
title: The task worktree stays until the task branch is merged
type: architecture
status: accepted
date: 2026-10-10
source: DL-111, task 2026-10-08-1733--sae-dogfood-fixes (R1, R2, [TASK-WORKTREE-LIFECYCLE]); task 2026-10-12-1846--sae-findings-docs [FINAL-REPORT-WORKTREES]
applies-to: [skills/shape-and-execute/scripts/sae_lib/workspaces.py, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/doctor.py, sweep_merged_task_worktrees, merged_into_base, remove_task_worktrees, final_report]
---

# The task worktree stays until the task branch is merged

## Context
After `finish` the owner still has to test and merge the task branch. The task worktree could
go at once, or stay.

## Decision
[joint] The task worktree lives in `sae`'s worktree cache (the owner accepted the agent's
proposal). After `finish` it stays, and the final report names its path. When the task branch
has been merged into its base, the next writing `sae` command or `sae doctor` removes the
worktree and the merged branch.

## Why
The owner can test the result where it was built, and nothing has to be cleaned by hand.
