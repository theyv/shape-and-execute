# Intent: Orchestrator context load when checking large task graphs

## Problem

The orchestrator needs to identify active jobs and decide what to do next. In a large task graph, repeated state checks may fill its context with job information that does not require action.

`sae status <task>` lists every job, including completed jobs. `sae next <task>` omits completed jobs but lists all blocked jobs with their dependencies. The execution instructions require `next` in every loop and `status` after a restart. These outputs can grow with the graph and repeat across the run.

The owner raised this concern after inspecting a large task graph. The actual context cost and its effect on orchestration have not been measured.

## Goal

Assess whether checking job state creates unnecessary context load in large tasks and whether the orchestrator can easily identify the jobs that need attention.

## Constraints

- [human] Tier 2. Record the problem for consideration. Leave solutions undecided.

## Open questions

- How much context do repeated state checks consume as a task graph grows?
- Which job information does the orchestrator need for routine checks and after a restart?
- Does the volume of output make active jobs or required actions harder to identify?

## Evidence: a job's effective model is hard to read

Observed 2026-11-04 in a large task (120 jobs), after a handoff to a new orchestrator session.

- The owner asked to keep Sol overrides only on mechanical jobs. The orchestrator answered that no
  pending job had an override. This was wrong: eight pending jobs had one, and the viewer showed them.
- Cause: no `sae` command printed the override or the effective harness, model and effort of a
  pending job. `sae status` and `sae next` do not show them. The orchestrator read `state.json` itself,
  looked in the per-job records, and did not find the overrides, which are kept in a separate
  task-level section.
- Effect: a wrong statement to the owner, corrected only because the owner compared it with the viewer.

Open question added: should `sae status` or `sae next` show, per pending job, the harness, model and
effort that the next dispatch will use, and mark the ones that come from an override?
