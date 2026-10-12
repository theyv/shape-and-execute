---
title: One job or its review can run on another model
type: architecture
status: accepted
date: 2026-10-10
source: DL-101, DL-141, task 2026-10-08-1733--sae-dogfood-fixes (R6, R7, [JOB-MODEL-OVERRIDE], SAE-ROUTING, INTEGRATE-SAE-REVIEWS)
applies-to: [skills/shape-and-execute/scripts/sae_lib/planning.py, skills/shape-and-execute/scripts/sae_lib/routing.py, skills/shape-and-execute/assets/viewer/task-views.js, cmd_job_override, override_key, resolve_model]
---

# One job or its review can run on another model

## Context
Routing picks the model by level and difficulty. Sometimes the owner wants one job, or its
review, on another harness, model or effort.

## Decision
- [human] On the owner's word, the orchestrator overrides harness, model and effort of one job
  or of its review (`sae job override`). The override wins over routing for that job, shows on
  the graph node and on next-step cards, and is logged. In the viewer, clicking a node's model
  label opens a dropdown that sets or clears it.
- [agent] Dispatch flags beat overrides: `--provider` and `--harness` win; an override's model
  and effort apply only when the flag names the override's harness. A non-review job can be
  overridden only while pending; a review key is refused while one of its rounds runs.

## Why
- The owner asked for it, "provided it does not add excessive complexity".
- A fallback to the other harness must not carry a model of the first one.

## Rejected options
- The override always wins: a fallback would send a Codex model to Claude.
