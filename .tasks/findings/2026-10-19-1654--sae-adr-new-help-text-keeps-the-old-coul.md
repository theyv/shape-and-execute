---
type: follow-up
confidence: medium
source: 2026-10-19-1603--adr-cleanup-and-dispatch-pointers/WRITING-RULES
paths: []
---

# sae adr new help text keeps the old 'could not rebuild from the code' test

## Observation
register_adr in skills/shape-and-execute/scripts/sae_lib/findings.py: the 'adr new' help says 'Draft only durable decisions a later agent could not rebuild from the code'. The writing rules now use the spec's test (an agent would 'fix' something on purpose, or bring back a rejected option) and the three places by reach. WRITING-RULES could not change sae code.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
