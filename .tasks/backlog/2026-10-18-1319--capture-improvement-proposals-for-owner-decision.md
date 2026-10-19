# Intent: Add improve findings and clarify finding types by urgency

## Problem

While working on an app, SaE can notice an optional new idea, an opportunity to improve
something that exists, friction, or a defect outside the current task. These observations
need distinct types so the owner can understand their urgency and decide what to do.

The aim is for the app to improve gradually through useful observations made during normal
tasks.

## Goal

Add `improve` as a finding type and use the four types below. Let SaE capture optional ideas
it notices during normal tasks as proposals in the backlog. Make their pending status clear
so the owner can later accept or reject them. Implementation follows the owner's acceptance.

## Finding types

The owner specified this order from least to most urgent [human, 2026-10-18]:

`improve` → `follow-up` → `friction` → `defect`

- `improve`: a new idea for something that could work well in the app. It can be entirely
  optional; AI noticed an opportunity that could be valuable or exciting.
- `follow-up`: an improvement to something that already exists.
- `friction`: something exists and works poorly or causes inconvenience, but it is not a
  critical bug.
- `defect`: something is broken and needs fixing.

This classification covers the app and its behavior as well as its code and the agent's
experience working in the repository.

### Success means

- A proposal explains what SaE noticed, where, why it matters, and what improvement it
  suggests, with enough evidence for the owner to assess it.
- Findings use the four definitions above, and triage presents their relative urgency.
- The owner can distinguish proposals awaiting a decision from work already accepted.
- Accepted proposals can become tasks; rejected proposals retain enough history to avoid
  repeated suggestions.
- Recording a proposal fits into the current task without expanding its implementation scope.

## Current behavior

[Worker instructions](../../skills/shape-and-execute/references/roles/worker.md)
already collect out-of-scope observations as `defect`, `friction`, or `follow-up` findings.
They restrict `follow-up` to work the task or user clearly needs.
[Finding triage](../../skills/shape-and-execute/references/modes/triage-findings.md)
lets the owner fix now, move to the backlog, leave open, or reject.

This covers part of the desired flow. The current finding types have no `improve` category,
and their definitions need to match the owner's classification above. The worker's current
friction examples focus on difficulties working in the repository; the desired meaning also
covers friction in the app itself.

## Open questions

- How should pending `improve` proposals appear in the backlog?
- What makes an observation valuable enough to propose, and how should duplicates be handled?
- How should acceptance, rejection, and conversion into a task be recorded?

Design and implementation are deferred until this item is picked up [human, 2026-10-18].
