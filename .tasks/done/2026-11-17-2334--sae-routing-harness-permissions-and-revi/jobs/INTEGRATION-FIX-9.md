---
id: INTEGRATION-FIX-9
covers: [ACCEPT-INTEGRATION]
verify:
  - python3 tests/run.py test_viewer_surfaces test_viewer_fixes
scope:
  - skills/shape-and-execute/assets/viewer/**
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - tests/**
---

# INTEGRATION-FIX-9: The viewer shows an accepted integration round as accepted

## Objective
Fix finding 3 of `reviews/REVIEW-INTEGRATION-2.md` with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION-2.md` finding 3 (Evidence, Correction).
- Spec `[ACCEPT-INTEGRATION]`; how `sae` records the acceptance (the decision event and the
  state it writes).

## Scope
- Plan tab: the card of an accepted integration round shows it as accepted (not
  `✕ changes required`), with the reason, for example in its tooltip or a short line.
- Reviews tab: the row of that round shows the original verdict and the recorded acceptance
  with its reason.
- Use the data `sae` already records. If the server does not send it to the viewer yet, a small
  read in `server.py` is in scope.

## Boundaries
- No change to how `sae` accepts a round. A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the change and the test.

## Validation
- [ ] A test with an accepted integration round: both tabs show the acceptance and its reason,
      and the original verdict stays visible in the review history.
