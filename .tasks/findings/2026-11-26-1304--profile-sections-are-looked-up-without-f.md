---
type: defect
confidence: medium
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/REVIEW-INTEGRATION-4
paths: []
---

# Profile sections are looked up without fence awareness

## Observation
In .tasks/repo/profile.md, stakes.py finds the Project Stakes section by its heading line without knowing about code fences. When Project Stakes are not set and the only '## Project Stakes' line sits inside a fenced example, the lookup returns the example as the stakes and a viewer save rewrites the example. Two headings are refused since INTEGRATION-FIX-10. The owner accepted the remaining case in REVIEW-INTEGRATION-4 as unlikely: a generated profile needs a hand-pasted example. Earlier fence parsing broke three times (REVIEW-INTEGRATION, -2, -3), so a fix should be one simple rule.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
