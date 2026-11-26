---
id: VIEWER-SURFACES-FIX-3
covers: [STAKES-VIEWER]
verify:
  - python3 tests/run.py test_viewer_surfaces test_stakes
scope:
  - skills/shape-and-execute/assets/viewer/**
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - tests/**
---

# VIEWER-SURFACES-FIX-3: The Project Stakes draft and its revision come from one read

## Objective
Fix findings 1 and 2 of `reviews/REVIEW-VIEWER-SURFACES-3.md` and finding 1 of
`reviews/REVIEW-VIEWER-SURFACES.md`, each with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-VIEWER-SURFACES-3.md` finding 1 (Evidence, Correction).
- `jobs/VIEWER-SURFACES-FIX-1.result.md` and `jobs/VIEWER-SURFACES-FIX-2.result.md`: the lock
  and the revision they added.

## Scope
- A settings load derives the draft and its revision from one read of the profile. A save
  that lands between two reads can no longer give a tab an old draft with a new revision.
- Line endings (owner decision: small, quick Windows fixes are in): the revision hashes the
  stored section with its original line endings, and a save keeps the bytes outside the
  Project Stakes section as they were (a CRLF profile stays CRLF there). Keep it small. If it
  needs more than a local change in `stakes.py` and its reads, park and say why.

## Boundaries
- No other behavior changes. A new problem becomes a finding.
- Let go by the orchestrator (Project Stakes), do not work on it: finding 4 of
  `reviews/REVIEW-VIEWER-SURFACES.md`.

## Expected output
Commits on the VIEWER-SURFACES branch; the result names the fix and the test.

## Validation
- [ ] A test where a save lands during a settings load; the stale tab's save then gets a
  conflict. It fails before the fix.
- [ ] A test where a save changes only the line endings of the section; a second save from
  the old base gets a conflict.
- [ ] A save test with a CRLF profile: the sections outside Project Stakes keep their bytes.
- [ ] The FIX-1 and FIX-2 tests still pass.
