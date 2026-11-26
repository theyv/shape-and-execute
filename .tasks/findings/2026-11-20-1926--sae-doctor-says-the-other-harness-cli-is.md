---
type: defect
confidence: high
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/WRITER-LAUNCH
paths: []
---

# sae doctor says the other harness CLI is only for cross-model review

## Observation
doctor.py prints '<name> CLI on PATH (only for cross-model review)'. Since WRITER-LAUNCH, any job routed to the other harness (override or dispatch flag) runs through a COMMAND, and sae dispatch refuses when that CLI is missing. The check text and its fix line should say so.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
