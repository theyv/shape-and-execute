---
title: Without git, offer git init and no snapshots
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/references/modes/execute.md, skills/shape-and-execute/references/interaction-modes.md]
---

# Without git, offer git init and no snapshots

## Context
Branches, worktrees and merges are the skill's safety net. Some folders have no git.

## Decision
[human] In a folder without git, the skill offers `git init`. If the user declines, the task
runs without a safety net, with a plain notice.

## Why
Automatic snapshots were "appealing but overly complex".

## Rejected options
- Automatic snapshots of the folder.

## Consequences
- A hard stop protects such folders: without git, an agent never deletes a file that existed
  before the task unless the spec asks for it.
