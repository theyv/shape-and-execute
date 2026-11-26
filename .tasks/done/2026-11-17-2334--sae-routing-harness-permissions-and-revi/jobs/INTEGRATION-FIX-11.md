---
id: INTEGRATION-FIX-11
covers: [TRIAGE, LET-GO-REPORT]
verify:
  - python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance
scope:
  - skills/shape-and-execute/scripts/sae_lib/fix_loop.py
  - tests/**
---

# INTEGRATION-FIX-11: A let-go selector matches one finding exactly

## Objective
Fix finding 2 of `reviews/REVIEW-INTEGRATION-3.md` with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION-3.md` finding 2.
- `jobs/INTEGRATION-FIX-8.result.md`: the resolver today.

## Scope
- A selector is a finding number only when the whole argument is a number.
- Otherwise it must equal one finding's title exactly.
- A selector that matches more than one finding (by number and by title) is refused, with the
  list of findings.

## Boundaries
- No other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the rule and the tests.

## Validation
- [ ] In a numbered review where finding 1 is titled `2: Retry on timeout`: `2` selects
      finding 2 and `2: Retry on timeout` selects finding 1.
- [ ] A selector that matches two findings is refused.
