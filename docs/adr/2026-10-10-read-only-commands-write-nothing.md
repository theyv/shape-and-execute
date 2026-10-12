---
title: Read-only commands write nothing
type: architecture
status: accepted
date: 2026-10-10
source: DL-133, task 2026-10-08-1733--sae-dogfood-fixes (item 33, AMEND-2, [READ-ONLY-COMMANDS], DOCS-FIX); DL-140 (sweep)
applies-to: [skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/scripts/sae_lib/planning.py, skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/scripts/sae_lib/graph.py, cmd_status, cmd_next, cmd_check, open_task, add_due_review]
---

# Read-only commands write nothing

## Context
The Codex plan reviewer could not run `sae status`: it opened `.lock` for writing, and the
reviewer runs under a read-only sandbox.

## Decision
[agent] `sae status`, `sae next`, `sae check`, `--help` and the other read-only commands take
no lock and write nothing. What they only compute is stored by the writing command that acts
on it: `sae dispatch` adds a due spec or plan review and records the next-step card; `sae start`
records the start card. The sweep of merged task worktrees runs only in writing commands and
`sae doctor`.

## Why
A reviewer under a read-only sandbox must be able to run them, and a command that looks
read-only must be safe to run any time.

## Rejected options
- `sae check` adding a due review and `sae next` recording its card, with a stderr note when
  write access is missing: they would still write in the normal case.
