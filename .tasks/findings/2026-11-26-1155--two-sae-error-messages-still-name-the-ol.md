---
type: follow-up
confidence: high
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/INTEGRATION-FIX-4
paths: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/routing.py, tests/test_retired_terms.py]
---

# Two sae error messages still name the old routing modes

## Observation
AMEND-3 names the two ways to set routes Tiers mode and Free mode. Two user-facing error messages outside INTEGRATION-FIX-4's scope still use the old wording: config.py (routing check) 'nothing usable: tiers in cells are off and the cell has no model and effort', and routing.py 'the cell has no model and effort while tiers are off'. Expected: both say Free mode, e.g. 'the cell has no model and effort in Free mode'. test_retired_terms.py now retires 'tiers in cells' with an allowance for config.py only; drop that allowance when the message changes.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
