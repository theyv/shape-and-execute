---
title: No drift-check mechanism
type: architecture
status: accepted
date: 2026-10-06
source: DL-67, second design interview 2026-10-06 (S2-Q8, S2-D7)
applies-to: [skills/shape-and-execute/references/modes/shape.md]
---

# No drift-check mechanism

## Context
A backlog item can wait for weeks; the code moves on meanwhile. Its intent may be outdated
when someone picks it up.

## Decision
[human] Picking up a backlog item adds one clause to intake: the intent may be outdated, so
read it against the current code like any note. No mechanism beyond that.

## Why
The owner: "The need to check for drift should become clear during shaping.". Light in
its complexity.

## Rejected options
- A drift check as a step, with pointers printed by `sae`.
- A research job for drift.
- Checking the rest of a series at every pickup.
