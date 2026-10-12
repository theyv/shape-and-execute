---
title: sae's git plumbing skips hooks
type: architecture
status: accepted
date: 2026-10-10
source: DL-115, DL-142, task 2026-10-08-1733--sae-dogfood-fixes (D24, items 15, 28; [GIT-HOOKS-OFF-FOR-SAE], [DECISION-HOOKS-OFF], SAE-TASK-WORKTREE)
applies-to: [skills/shape-and-execute/scripts/sae_lib/gitutil.py, skills/shape-and-execute/scripts/sae_lib/doctor.py, skills/shape-and-execute/templates/repo/setup.sh, HOOKS_OFF, run, configured_hooks_path, hooks_found]
---

# sae's git plumbing skips hooks

## Context
The owner's global `post-checkout` and `post-merge` hooks ran `apm install`. In `sae`'s
worktrees they rewrote a tracked file, blocked merges and left dead worktrees
(`research/FORENSICS.md` §5, §8 in the record of task 2026-10-08-1733--sae-dogfood-fixes).

## Decision
- [joint] Worktree add and remove, job merges and `sae`'s own commits run with hooks off.
  Workers' commits keep hooks. A repository that installs dependencies in a hook moves that
  into `.tasks/repo/setup.sh`; `sae doctor --repo` says so.
- [agent] The switch sits in `gitutil.run`, so every git call of `sae` skips hooks.

## Why
`sae`'s merges are internal plumbing. Hooks still run on the owner's own merges and on the
workers' commits.

## Rejected options
- A per-repository list of paths the dirty check ignores: it treats the symptom.
