---
title: Worktrees live in a persistent user cache
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/workspaces.py, default_worktree_root, worktree_root, task_worktrees_dir]
---

# Worktrees live in a persistent user cache

## Context
Task and job worktrees need a folder. Candidates: `/tmp`, a folder inside the repository, or a
per-user cache.

## Decision
[human] Worktrees live in a per-user cache folder (on macOS
`~/Library/Caches/shape-and-execute/worktrees/`), configurable in the user config. A temporary
folder remains an option for those who want it.

## Why
- The owner on `/tmp`: "an unreliable location".
- Inside the repository, Jest and Vitest scan nested hidden folders by default, so every
  repository would need tool-config changes
  ([research/nested-worktrees-and-test-runners.md](research/nested-worktrees-and-test-runners.md)).

## Rejected options
- `/tmp` as the default.
- A folder inside the repository, such as `.tasks/.worktrees/`.
