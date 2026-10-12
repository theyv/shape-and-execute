---
title: sae is the only writer of state and events
type: architecture
status: accepted
date: 2026-10-06
source: DL-19, DL-23, design interview 2026-10-06 (Q2, D23)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/scripts/sae_lib/graph.py, Task, append_event_to, state.json, events.jsonl]
---

# sae is the only writer of state and events

## Context
Task state, the event log and what the viewer shows must agree. An orchestrator that updates
them by hand needs several steps per change, and it forgets some.

## Decision
- [joint] `sae` is the only writer of `state.json` and `events.jsonl`. One call updates the
  state, appends the event and validates. The viewer server writes through `sae` too. State
  covers the whole life cycle of a task, not only execution.
- [joint] Gates live in the CLI: `sae` refuses wrong transitions (for example `dispatch`
  before plan approval, `collect` without a result file). Harness hooks that would guarantee
  that steps ran are not used.

## Why
Three manual steps per change would drift. On hooks the owner said: "This may be outside the current scope; we can consider it later.".

## Rejected options
- The orchestrator edits state and events by hand.
- Harness hooks now: deferred, not rejected for good.
