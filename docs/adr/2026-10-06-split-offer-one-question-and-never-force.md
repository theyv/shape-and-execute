---
title: Split offer, one question and never forced
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/references/roles/planner.md]
---

# Split offer, one question and never forced

## Context
Some tasks are big. The question is when, and by whom, a task should be split into several.

## Decision
[joint] One task of any size is the default; a huge graph is allowed. While shaping, at the
latest at the spec gate, the agent offers a split only when it would have to guess a whole area
of the spec, because that area depends on code this task will create. The guessed area goes to
the backlog; the owner decides. After spec approval nothing is split, and the planner does not
flag size.

## Why
- The owner: "A well-defined spec should avoid the need to remove scope during planning."; "I do not want to require the user to create many separate tasks."
- The owner found lists of signals non-deterministic ("authentication" can mean one outcome or several).
  One question separates the cases: auth has nothing to guess, so it stays one task; in a whole
  application, billing would guess the data model, so a split pays off. A wrong judgment costs
  one ignored sentence, never an action (agent).

## Rejected options
- A list of signals.
- A fixed "split" line at every spec gate.
- A split only on request.
- A split proposed by the planner.
