---
title: Codex permission profile
type: architecture
status: accepted
date: 2026-10-06
source: DL-53, design interview 2026-10-06 (Q28)
applies-to: [skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/references/modes/setup.md, cmd_setup_snippets]
---

# Codex permission profile

## Context
Codex's default sandbox keeps `.git` read-only, and the worktree root lies outside the working
folder.

## Decision
[joint] Setup offers a Codex permission profile: `.git` writable except its hooks and config,
plus the worktree root. `sae setup snippets` prints it; setup mode applies it only after the
user agrees, with a backup.

## Why
Without it, Codex blocks every commit and merge. Facts:
[research/codex-facts.md](research/codex-facts.md) ("Sandbox and git", "Permission profiles").
