---
title: Provenance on every decision
type: architecture
status: accepted
date: 2026-10-06
source: DL-16, design interview 2026-10-06 (D6)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/templates/specs.md, skills/shape-and-execute/templates/plan.md, skills/shape-and-execute/templates/job-result.md, skills/shape-and-execute/templates/decision-record.md]
---

# Provenance on every decision

## Context
Decisions come from the owner, from discussion, or from an agent alone. Later readers, and
the owner at each gate, need to know which.

## Decision
[agent] Every decision carries a provenance tag: `[human]`, `[joint]` or `[agent]`. Each gate
shows the riskiest `[agent]` assumptions.

## Why
Taken from the owner's agent rules. An agent must never present its own tradeoff as the owner's decision,
and the owner checks the riskiest assumptions where it is cheap: at the gate.
