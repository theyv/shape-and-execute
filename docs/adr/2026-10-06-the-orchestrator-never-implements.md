---
title: The orchestrator never implements
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/modes/execute.md, skills/shape-and-execute/references/modes/plan.md]
revisit-when: the fast-lane backlog item (2026-10-14-2150) is shaped
---

# The orchestrator never implements

## Context
In execution the main session schedules, dispatches, collects and records. For a task with one
small job it is tempting to implement directly.

## Decision
[agent] The orchestrator never implements, not even a one-job task. It is restartable: any
session continues a task from its files (`sae status`, `sae start`).

## Why
Agent's reasoning: the main session stays clean; every change has a result file and a recorded
model; one rule is simpler than "implement it yourself when it is small".

## Rejected options
- "Implement it yourself when it is small."

## Consequences
- The owner has not confirmed this agent decision yet; it was listed for confirmation.
