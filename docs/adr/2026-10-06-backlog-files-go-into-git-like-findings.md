---
title: Backlog files go into git like findings
type: architecture
status: accepted
date: 2026-10-06
source: DL-68, second design interview 2026-10-06 (S2-Q12, S2-Q15)
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, sourced_items, commit_task_record, commit_backlog_pickup, .tasks/backlog]
---

# Backlog files go into git like findings

## Context
Backlog items are plain files. They could stay local or be committed. The owner also raised
the team case: two people starting the same task, and unfinished tasks invisible to others.

## Decision
[joint] The task named in a backlog file's `source` commits it at `sae finish`; the task that
picks a backlog item up commits the removal of its file. A backlog file without a source stays
untracked until the owner commits it. Running task folders stay untracked (see [The task record is untracked while it runs and committed whole at finish](2026-10-06-the-task-record-is-untracked-while-it-ru.md)). Team claims are parked for the team
version.

## Why
- A backlog file is never a running task folder, so tracking it leaves no stale copies in
  worktrees.
- Tracking task folders would not give a team visibility anyway, because nothing is pushed
  (agent).
- The owner on the team case: "Leaving this untracked until execution may be a flaw in the design.". Accepted advice: claims and visibility of work in progress need one shared, live
  place, such as an issue tracker with assignees or a service tied to pull requests. The owner:
  "For team collaboration, the viewer may need to become a separate service.".

## Rejected options
- Committing the task folder at `sae start`.
- An untracked backlog (accepted first, then revisited).
