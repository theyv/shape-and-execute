---
title: Repository facts live under the tasks folder
type: architecture
status: accepted
date: 2026-10-06
source: DL-52, design interview 2026-10-06 (Q17)
applies-to: [skills/shape-and-execute/templates/repo, skills/shape-and-execute/references/modes/setup.md, skills/shape-and-execute/scripts/sae_lib/workspaces.py, include_pattern_files, run_setup_script]
---

# Repository facts live under the tasks folder

## Context
The skill needs shared facts per repository: validation commands, hot files, a worktree setup
script, ignored files to copy into worktrees.

## Decision
[human] They live in `.tasks/repo/` (`profile.md`, `setup.sh`, `worktreeinclude`). The skill
puts nothing in the repository root.

## Why
The owner: nothing in the repository root. The root belongs to the project's own tooling, and
`.tasks/` already holds everything the skill keeps.

## Consequences
- `sae` also reads a root `.worktreeinclude` when a repository has one (Claude Code's
  convention), but it never writes one.
