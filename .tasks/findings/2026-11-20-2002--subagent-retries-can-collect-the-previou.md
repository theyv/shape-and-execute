---
type: follow-up
confidence: low
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/WRITER-LAUNCH-FIX-1
paths: []
---

# Subagent retries can collect the previous attempt's result

## Observation
WRITER-LAUNCH-FIX-1 made sae collect refuse a result older than the current attempt, but only for COMMAND attempts (launch record). A resumed subagent attempt can still be collected on the unchanged earlier result; test_sae tests (verify-failed resume, wt-flow B) rely on that today. Decide whether the check should cover every attempt.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
