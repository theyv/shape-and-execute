---
title: The task record is untracked while it runs and committed whole at finish
type: architecture
status: accepted
date: 2026-10-06
source: DL-46, DL-47, design interview 2026-10-06 (Q4, Q21)
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, commit_task_record, cmd_finish]
---

# The task record is untracked while it runs and committed whole at finish

## Context
A task folder `.tasks/<task-id>/` changes all the time during a run. Workers work in worktrees,
which hold tracked files only.

## Decision
- [joint] The task folder stays untracked during the run and is committed once, at
  `sae finish`.
- [human] The whole task record is committed: intent, spec, plan, job files, results, reviews,
  state and events.

## Why
- The owner: "This will avoid clutter." Workers never see stale copies of the task folder, because
  worktrees hold only tracked files.
- The agent proposed a compact record. The owner: the job definitions explain what each job was
  meant to be; without them, "STATUS-API completed" means nothing half a year later.

## Rejected options
- A compact task record (the agent's proposal). The owner keeps the idea open if committing
  everything turns out too heavy: "We can reconsider if this approach does not work well.".
- Committing the task folder at `sae start` (see [Backlog files go into git like findings](2026-10-06-backlog-files-go-into-git-like-findings.md)).
