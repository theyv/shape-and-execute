# Intent: Autonomous route for backlog tasks

## Problem

The owner may want to assign a backlog item for an unattended run, for example overnight. The current flow expects owner participation while the agent shapes the task, writes a spec, plans the work, and executes it. The owner needs to set how far the agent may proceed without a decision.

## Goal

Let the owner start a backlog item with an autonomy level. The agent shapes the task, writes the spec and plan, and completes as much work as that level permits.

### Success means

- The owner can give a backlog item an instruction to work on it unattended.
- The owner can choose or propose an autonomy level for that run.
- At the most autonomous level, the agent can carry the task through a validated task branch without intermediate owner decisions when it has enough information.
- At a more cautious level, the agent completes all independent work first. It groups decisions and tradeoffs for the owner at the end, then waits for answers before completing dependent work.
- A blocked decision does not stop unrelated work.
- The task record shows what the agent decided, what remains open, and why it stopped.

## Proposed outcome

Add an autonomous route from a backlog item through shaping, planning, and execution. The owner chooses the run's autonomy level at intake. The agent prepares the spec and other task files itself. It applies that level to approval points and choices that arise during the run. When owner input is needed, it leaves a concise decision list and a resumable task state.

## Affected users and systems

The owner, the shape-and-execute workflow, `sae` task state and gates, and unattended orchestration.

## Constraints

- Respect the autonomy level chosen for the run. Do not treat a request to work overnight as blanket approval for decisions outside that level.
- Preserve the task record and validation results so the owner can review and resume the work.
- Keep independent work moving when a decision is parked.

## Related tasks

- Related backlog item: `2026-10-13-1141--headless-orchestrator-for-unattended-ful.md`. It covers the headless runner for unattended full-auto execution. This item covers the owner-facing route and its autonomy levels. Decide their implementation relationship during shaping.
- Related backlog item: `2026-10-14-2150--fast-lane-mode-for-mini-tasks.md`. It addresses a shorter workflow for small tasks; this item addresses unattended work on backlog items.

## Open questions

- What autonomy levels should the owner be able to choose, and what decisions may the agent make at each level?
- Which approvals and review points can the agent satisfy during an unattended run, and which always require the owner?
- How should the agent identify a material tradeoff and present the deferred decisions when the owner returns?
- How should the route start, resume, and report progress to the owner?
