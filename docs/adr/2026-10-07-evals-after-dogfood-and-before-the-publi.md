---
title: Evals after dogfood and before the public release
type: business
status: superseded
date: 2026-10-07
source: DL-80, genesis review 2026-10-07 (G3)
applies-to: [skills/shape-and-execute, tests, evals]
---

# Evals after dogfood and before the public release

## Context
The genesis review noted that nothing shows the skill beats a plain session with the same
model. Two research notes looked at what exists:
[research/superpowers-evals.md](research/superpowers-evals.md) (Quorum, the superpowers eval
lab: methods to copy, no license to fork) and
[research/evals-landscape.md](research/evals-landscape.md) (existing benchmarks; RoadmapBench
through Harbor fits scale and decomposition).

## Decision
[human] Dogfood first; evals before the public release, starting with an MVP that can grow. The
evals must show the problems the skill exists for (see `_intent.md`).

## Why
Agent's reading: real use finds the real problems first, and evals built before that would
measure a design that is still moving.

## Consequences
- The draft eval plan lived in the to-do list of the design notes; when the design notes were removed
  (2026-10-12), its open items became follow-up findings.
