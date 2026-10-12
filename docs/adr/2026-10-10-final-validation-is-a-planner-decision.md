---
title: Final validation is a planner decision
type: architecture
status: accepted
date: 2026-10-10
source: DL-44, design interview 2026-10-06; DL-107, task 2026-10-08-1733--sae-dogfood-fixes (R3, [DECISION-FINAL-VALIDATION-NAME])
applies-to: [skills/shape-and-execute/references/roles/planner.md, skills/shape-and-execute/templates/plan.md, skills/shape-and-execute/scripts/sae_lib/graph.py, place_final_after, final-validation, --final]
---

# Final validation is a planner decision

## Context
After all jobs merged and the integration review passed, one more job can check the whole task
against the spec. For a small chain that adds nothing.

## Decision
- [joint] The planner decides whether a task gets a final validation job (`--final`, kind
  `validation`): when several workstreams meet, behavior crosses system boundaries, acceptance
  or end-to-end tests matter, or regression risk is real. For a small chain, the last job's
  validation is enough.
- [agent] The final job keeps the name `final-validation`.

## Why
- No validator for its own sake; the notes put it as no unnecessary validation roles.
- "Verify" already names a job's check command, and the job's kind is `validation`.

## Rejected options
- A final validation for every task.
- The name `final-verification` (the owner's suggestion; open for veto).
