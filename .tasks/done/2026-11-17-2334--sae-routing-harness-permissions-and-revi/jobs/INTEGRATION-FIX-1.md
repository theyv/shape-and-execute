---
id: INTEGRATION-FIX-1
covers: [STAKES-VIEWER]
verify:
  - python3 tests/run.py test_viewer_surfaces test_stakes
scope:
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/assets/viewer/**
  - tests/**
---

# INTEGRATION-FIX-1: A Project Stakes save never hides or deletes the next profile section

## Objective
Fix finding 1 of `reviews/REVIEW-INTEGRATION.md` with tests that fail before the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION.md` finding 1 (Evidence, Correction).
- `jobs/VIEWER-SURFACES-FIX-3.result.md`: how the section is read, hashed and written now.

## Scope
- A save whose text would hide the next profile section (for example, an unclosed code fence)
  is refused with a clear message. The file stays as it was.
- When the stored section already has an ambiguous end, a save is refused and the file stays
  as it was.
- The simplest correct rule wins. Keep the line-ending and revision behavior of
  VIEWER-SURFACES-FIX-1..3.

## Boundaries
- No other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the fix and the tests.

## Validation
- [ ] Both cases of the review's Correction are tested with a section after Project Stakes.
- [ ] The VIEWER-SURFACES-FIX-1..3 tests still pass.
