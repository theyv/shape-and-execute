---
title: Intent and spec have separate jobs and stay in step
type: architecture
status: accepted
date: 2026-10-06
source: DL-15, DL-18, design interview 2026-10-06 (D5)
applies-to: [skills/shape-and-execute/templates/intent.md, skills/shape-and-execute/templates/specs.md, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/scripts/sae_lib/graph.py, requirement_ids]
---

# Intent and spec have separate jobs and stay in step

## Context
Shaping produces the why and the exact requirements. They can live in one file or two, and a
traceability table can link requirements to jobs.

## Decision
- [agent] `intent.md` holds the why and the outcome. `specs.md` is the only place for exact
  requirements, with IDs. No hand-maintained traceability table: `sae check` computes coverage
  from the requirement IDs and the jobs' `covers`; final validation gives the evidence.
- [human] After each grill round, both intent and spec are updated.

## Why
- A hand-maintained traceability table drifts. (Accepted after the owner asked why.)
- Each grill round can change both the why and the what. Keeping both current means the planner
  never reads two different stories.

## Rejected options
- A hand-maintained traceability table.
