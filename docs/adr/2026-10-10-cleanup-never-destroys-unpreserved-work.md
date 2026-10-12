---
title: Cleanup never destroys unpreserved work
type: architecture
status: accepted
date: 2026-10-10
source: DL-113, DL-142, task 2026-10-08-1733--sae-dogfood-fixes (D5, item 9, [WORKTREE-CLEANUP], SAE-WORKTREE-CLEANUP)
applies-to: [skills/shape-and-execute/scripts/sae_lib/workspaces.py, skills/shape-and-execute/scripts/sae_lib/gitutil.py, unpreserved_work, keep_worktree, remove_worktree, discard_worktree, remove_empty_cache_folders, leftover_reason, repo_cache_name, --discard]
---

# Cleanup never destroys unpreserved work

## Context
Dead worktrees piled up in the cache (item 9 of the dogfood fixes).

## Decision
- [joint] Job worktrees go after their merge, at finish and at abandon; empty cache folders go
  too. A worktree with uncommitted changes or untracked files (ignored setup files do not
  count), or of a failed job, is kept, and `sae` says why. Removing it needs the owner's
  explicit word (`sae doctor --discard`). Cache folders are named after the repository, not
  after the checkout.
- [agent] An untracked file byte-identical to the home checkout's or the main worktree's copy
  does not block cleanup. A merged task branch is deleted with `branch -D` after
  `merge-base --is-ancestor`. `--discard` accepts only `sae` cache worktrees of this repository
  and refuses one that holds the live folder of an open task. The sweep skips abandoned tasks.

## Why
- Dead worktrees cost space and attention. The preservation rule came from the spec review
  (Codex); the owner accepted it.
- `branch -d` compares with the running checkout's HEAD, which is not the base.

## Rejected options
- `git branch -d` for merged task branches.
