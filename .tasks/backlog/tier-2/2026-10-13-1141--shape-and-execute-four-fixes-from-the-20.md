# Intent: shape-and-execute: three fixes from the 2026-10-12 triage

## Problem
Two defects and one friction found while running sae-findings-docs; details below.
The fourth item (sae collect takes 5 minutes per job) moved to a separate task,
sae-fast-collect, on 2026-10-13 [human].

## Goal
All three are fixed in one task. Owner's triage on 2026-10-13: fix them together.

## Findings this item replaces
Closed in triage on 2026-10-13; their text:

### A dispatched spec or plan review cannot be skipped

## Observation
The owner asked to skip the plan review after REVIEW-PLAN was dispatched. sae set review=spec,integration turns the point off, but the running REVIEW-PLAN stays: sae job remove refuses a running job ('only pending jobs can be removed'), sae approve plan refuses while a plan review is not done (planning.py cmd_approve), and the verdicts allow no 'skipped'. There is no command to cancel a running job. The only ways on are to run the review anyway or to write a placeholder review result.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion

### sae finding close in a job worktree writes closed.md to the home checkout

## Observation
Running 'sae finding close' in a job worktree removed the finding file in the worktree but appended the closed.md line to the home checkout's .tasks/findings/closed.md (find_root resolves to home), leaving it dirty. cmd_finding_close passes root to close_finding.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion

### sae new --from takes only one backlog item

## Observation
The owner put two backlog items into one task in triage. sae new --from accepts one file; the second item was folded into intent.md by hand, and sae start will not remove its backlog file (only the --from file is recorded in the task.created event).

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
