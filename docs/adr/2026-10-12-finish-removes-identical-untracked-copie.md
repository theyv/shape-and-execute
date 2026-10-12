---
title: Finish removes identical untracked copies
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-12-1846--sae-findings-docs [DECISION-MERGE-CLEANUP], [OWNER-MERGE-FIRST-TASK]
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, cmd_finish, commit_task_record]
---

# Finish removes identical untracked copies

## Context
In a repository's first task, `.tasks/` files such as the repo profile are untracked in the
home checkout and committed by the task record. The owner's `git merge task/<id>` then fails,
because untracked files would be overwritten (finding of 2026-10-10).

## Decision
[agent] `sae finish` deletes the untracked files in the home checkout that are byte-identical to
what the task record committed, and reports them. A file whose content differs is never
deleted.

## Why
No information is lost, and the owner needs no manual step before the merge.

## Rejected options
- The owner commits the `.tasks/` files once: an extra step.
- These files leave the task record: they would be lost.

## Consequences
- The riskiest assumption of this decision: `sae` deletes files in the owner's home checkout,
  even if only identical ones.
