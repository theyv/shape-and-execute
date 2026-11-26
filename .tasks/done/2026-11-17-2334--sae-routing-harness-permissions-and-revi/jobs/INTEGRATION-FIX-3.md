---
id: INTEGRATION-FIX-3
covers: [DECISION-ANYTIME, TRIAGE, LET-GO-REPORT]
verify:
  - python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance
scope:
  - skills/shape-and-execute/scripts/sae_lib/findings.py
  - skills/shape-and-execute/scripts/sae_lib/common.py
  - skills/shape-and-execute/scripts/sae_lib/graph.py
  - skills/shape-and-execute/scripts/sae_lib/fix_loop.py
  - tests/**
---

# INTEGRATION-FIX-3: Decision jobs run before execution; let-go names exactly one finding

## Objective
Fix findings 5 and 6 of `reviews/REVIEW-INTEGRATION.md`, each with a test that fails before
the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION.md` findings 5–6 (Evidence, Correction).
- Spec `[DECISION-ANYTIME]`, `[TRIAGE]`, `[LET-GO-REPORT]`.

## Scope
- 5: a decision job (advisory) can be dispatched and collected in the shaping and planning
  phases, for example one made with `sae decision new --from REVIEW-PLAN` before plan approval.
  Other job kinds keep the phase rule.
- 6: `--let-go` resolves its input to exactly one finding of the review, or refuses. The
  decision stores the finding's identifier and the reason apart, so a colon in a title does
  not split it.

## Boundaries
- No other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the job branch; the result lists each finding with its fix and test.

## Validation
- [ ] 5: create, dispatch and collect a decision job from a done plan review before plan
  approval.
- [ ] 6: an absent title is refused; a title with a colon is reported once, with its reason.
