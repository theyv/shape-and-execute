---
title: Decision records live outside the skill
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-12-1846--sae-findings-docs [DECISION-ADR-OUTSIDE-SKILL]
applies-to: [docs/adr, skills/shape-and-execute]
---

# Decision records live outside the skill

## Context
The skill's "why" (`_intent.md` and its decision records) needs a home after the design notes go.
The skill folder is what users install.

## Decision
[human] They live in `docs/adr/` at the repository root, not inside the skill
folder.

## Why
The owner: "Keep the decision records outside the installed skill to avoid clutter.".

## Rejected options
- A docs folder inside the skill.

## Consequences
- An installed skill carries no records. The repository's ADR rules route records about
  `skills/shape-and-execute/` to this folder.
