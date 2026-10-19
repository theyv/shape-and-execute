---
title: Big work goes lazily through the backlog
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, new_backlog_item]
---

# Big work goes lazily through the backlog

## Context
The owner asked whether shaping should get an optional loop for big tasks, in the style of Matt
Pocock's wayfinder skill, and whether work cut out of scope should be kept instead of lost.
Facts: [research/wayfinder.md](research/wayfinder.md).

## Decision
[joint] Very large work is not planned up front as a series of fully specified tasks. When the
owner splits it, the deferred parts wait in the backlog as intents and get their spec when
someone picks them up, against the code that exists then. Shaping gets no decision map.

## Why
- A spec written for code that does not exist yet drifts, and correcting it costs a second
  round (agent).
- Wayfinder's own lazy rule and its stale 27-ticket map point the same way.
- Shaping already resumes from files and runs research in parallel (agent).

## Rejected options
- A series with intent and spec for every task up front, corrected at each plan: the owner's
  first idea. The agent called it a turbo complication; the owner agreed.
- Wayfinder's decision map inside shaping, light or full.
