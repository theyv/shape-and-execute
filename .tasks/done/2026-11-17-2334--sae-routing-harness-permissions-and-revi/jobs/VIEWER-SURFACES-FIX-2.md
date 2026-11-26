---
id: VIEWER-SURFACES-FIX-2
covers: [STAKES-VIEWER]
verify:
  - python3 tests/run.py test_viewer_surfaces test_stakes
scope:
  - skills/shape-and-execute/assets/viewer/**
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - tests/**
---

# VIEWER-SURFACES-FIX-2: The Project Stakes save base is the exact stored section

## Objective
Fix finding 1 of `reviews/REVIEW-VIEWER-SURFACES-2.md` with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-VIEWER-SURFACES-2.md` finding 1 (Evidence, Correction).
- `jobs/VIEWER-SURFACES-FIX-1.result.md`: the lock and the base check it added.

## Scope
- The save base is a revision of the exact stored section (for example, a hash of its raw
  text), not the normalized text. `sae` compares it under the existing lock.
- The normalized text stays what the viewer shows.
- A save that changes only comments or trailing spaces also makes a second save from the old
  base get a conflict.

## Boundaries
- No other behavior changes. A new problem becomes a finding.
- Findings 1 and 4 of `reviews/REVIEW-VIEWER-SURFACES.md` stay let go. Do not work on them.

## Expected output
Commits on the VIEWER-SURFACES branch; the result names the fix and the test.

## Validation
- [ ] The test from the review's Correction: the first save changes the stored section but not
  its normalized text; the second save from the same base gets a conflict. It fails before
  the fix.
- [ ] The FIX-1 tests still pass.
