---
title: References split into modes and roles
type: architecture
status: accepted
date: 2026-10-07
source: DL-75, genesis review 2026-10-07 (G2)
applies-to: [skills/shape-and-execute/references/modes, skills/shape-and-execute/references/roles, skills/shape-and-execute/SKILL.md]
---

# References split into modes and roles

## Context
`references/` mixed what the main session loads with what fresh subagents load. File names such
as `plan.md` and `planner.md` sat side by side.

## Decision
Idea [human], layout [joint]: `references/modes/` holds what the main session loads (shape,
plan, execute, setup, triage). `references/roles/` holds what fresh subagents load, named after
the role: `worker.md`, `research-worker.md`, `planner.md`, `reviewer.md`, `decision-worker.md`,
`integration-worker.md`. Shared files stay at the top: `grill.md`, `interaction-modes.md`,
`commit-message.md`.

## Why
- The owner could not tell `plan.md` from `planner.md` from the names alone.
- The genesis review draws the same seam: mode procedures versus personas loaded into fresh
  threads.

## Rejected options
- A folder named `agents/`: it already holds Codex metadata, and in Claude Code it means
  subagent definitions.
