---
title: Planning and review are never mechanical
type: architecture
status: accepted
date: 2026-10-10
source: DL-97, DL-138, DL-141, task 2026-10-08-1733--sae-dogfood-fixes (R4, R5, DESIGN-DOCS, DOCS-FIX, SAE-ROUTING); confirmed in task 2026-10-12-1846--sae-findings-docs [DIFFICULTY-DISPLAY]
applies-to: [skills/shape-and-execute/scripts/sae_lib/routing.py, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/planning.py, job_context, planned_review_target, task_difficulty, cmd_job_edit]
---

# Planning and review are never mechanical

## Context
Jobs have a difficulty: `mechanical`, `normal` or `hard`. Planning and review jobs need one too,
and a review could take its own or its target's.

## Decision
- [human] The planning and review tables have only `normal` and `hard`; the viewer keeps the
  three-column layout with the mechanical column empty. A job review takes its job's
  difficulty, a mechanical job counting as `normal`. The planner and the spec, plan and
  integration reviews take the task difficulty (`normal` or `hard`), which the orchestrator sets
  by the size and risk of the task; the owner can change it on the next-step card.
- [agent] Only a spec, plan or integration review can get its own difficulty
  (`sae job edit --difficulty`). A planned review resolves by its own ID the same way. Review
  prompts and the viewer show this effective difficulty.

## Why
- The owner rejected a weaker model for targeted review. On 2026-10-12 the owner confirmed the
  rule again; only its display was wrong.
- The owner wants the spec, plan and integration reviews runnable on `normal`.

## Rejected options
- A weaker model for a targeted review.
- The integration review always counting as `hard` (R2).
- An editable difficulty for every generated review: it would let a job review ignore its
  target's difficulty. An exceptional job review uses `sae job override --review`.
