---
title: Release without evals, evals come after it
type: business
status: accepted
date: 2026-10-19
source: task 2026-10-18-1334--public-release-of-shape-and-execute ([EVALS-DECISION], [DECISION-NO-EVALS])
applies-to: [skills/shape-and-execute, tests, evals]
---

# Release without evals, evals come after it

## Context
[Evals after dogfood and before the public release](2026-10-07-evals-after-dogfood-and-before-the-publi.md)
put evals before the public release. Dogfood is done, but no evals exist yet, and the owner
needed a public link to the skill by 2026-10-19.

## Decision
[human] Release the skill now, as an early version without evals. Evals and a non-interactive
entry for them come after the release, from the backlog. This record replaces
`2026-10-07-evals-after-dogfood-and-before-the-publi.md`.

## Why
- Evals take days; the public link was needed on 2026-10-19. The owner: "Release without evals."
- The evals must still show the problems the skill exists for (see `_intent.md`); only their
  place in time changes.

## Consequences
- The first public version is an early version: no eval result backs it.
- Nothing yet shows that the skill beats a plain session with the same model.
