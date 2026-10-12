---
title: Relations between tasks are prose
type: architecture
status: accepted
date: 2026-10-06
source: DL-65, second design interview 2026-10-06 (S2-Q5, S2-Q6, S2-Q13)
applies-to: [skills/shape-and-execute/templates/intent.md, skills/shape-and-execute/references/modes/shape.md, Related tasks]
---

# Relations between tasks are prose

## Context
Tasks build on each other, spin off from each other, or sit side by side. A structure could
record that: parent and child fields, a computed series, order checks.

## Decision
[human] An optional `## Related tasks` section in the intent, in prose with task IDs: "Builds
on <id> — start after it is merged", "Spun off from <id>, because …". No `origin` or `after`
fields, no computed series, no order checks.

## Why
- The owner: "These tasks may be peers rather than a parent and its children.". Structure can wait until a GUI needs it.
- Most backlog items are neighbours, not parts of a series. A computed series would make
  shaping read earlier tasks it does not need. The shaping agent follows a pointer when it
  helps.

## Rejected options
- A series computed from an `origin` field.
- A hand-kept series map (wayfinder style).
- An umbrella task.
- Soft or hard order checks.
- A `## Series` section: it fits only one of the two cases.
