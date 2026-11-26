---
type: defect
confidence: high
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/FINAL-VALIDATION
paths: []
---

# Validation job files go stale when the owner accepts later changes

## Observation
The planner writes the final validation job file at planning time. Its check 'no text beyond the spec drafts and the contradiction fixes of PROMPT-TEXT' did not know about later jobs the owner accepted (PROMPT-LEAN). Run as written, the validator would report the accepted cuts as failures, and the orchestrator would add fix jobs that restore the removed text. Nothing in sae or execute.md tells the orchestrator to update a pending validation job when the graph changes or an amendment lands. Expected: a validation job checks against the spec with its amendments and the results of every merged job, or sae reminds the orchestrator to refresh pending validation job files after job add or amendment.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
