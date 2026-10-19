---
title: One skill with five modes
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/modes/setup.md]
revisit-when: the fast-lane backlog item (2026-10-14-2150) is shaped
---

# One skill with five modes

## Context
shape-and-execute shapes a task, plans it, executes it, configures models and permissions, and
triages findings and decision-record drafts. These could be one skill or a pack of skills.

## Decision
[joint] Shape, plan, execute, setup and triage are modes of one skill. `SKILL.md` is a short
router with labelled links; each mode has one reference in `references/modes/`, loaded only
for the current mode.

## Why
- One entry in the skill list.
- The modes share `scripts/` and `templates/`. Separately installed skills cannot safely share
  files.
- A short router with labelled links keeps loading under control.

## Rejected options
- A pack of skills: it clutters the skill list (the owner's concern).
- A separate setup skill: used rarely, and it still clutters the list.
