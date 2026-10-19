---
title: No fits-one-session prompt at intake
type: architecture
status: accepted
date: 2026-10-07
applies-to: [skills/shape-and-execute/references/modes/shape.md]
revisit-when: the fast-lane backlog item (2026-10-14-2150) is shaped
---

# No fits-one-session prompt at intake

## Context
For a small task the whole flow may look heavy. Intake could ask whether the task fits one
plain session instead.

## Decision
[human] Intake does not ask it. A small task gets an intent, a short spec and one worker.

## Why
That is useful anyway. A user who does not want grilling for a small task leaves on their own:
"The user can choose to leave the workflow."

## Rejected options
- A "this fits one session" prompt at intake.
