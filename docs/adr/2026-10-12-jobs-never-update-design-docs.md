---
title: Jobs never update design docs
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-12-1846--sae-findings-docs
applies-to: [skills/shape-and-execute/references/roles/planner.md, skills/shape-and-execute/references/modes/plan.md, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/references/roles/worker.md]
---

# Jobs never update design docs

## Context
In the dogfood-fixes task, one job copied the spec into design docs before the code, and
another re-synced them after it. Without the design notes, one option left was that each job updates
the docs of its area.

## Decision
[human] No job writes or re-syncs design docs, before or after the code. A planner plans no
docs-sync job. The contract before the code is the task's `specs.md`; decisions reach
`docs/adr/` as decision records through triage.

## Why
The owner: "This biases the context toward confirming the implementation." A job would write the
document it is checked against.

## Rejected options
- Each job updates the docs of its area.
- A design-docs job before the code and a docs-sync job after it.
