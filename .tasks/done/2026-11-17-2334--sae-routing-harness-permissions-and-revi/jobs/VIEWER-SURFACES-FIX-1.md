---
id: VIEWER-SURFACES-FIX-1
covers: [STAKES-VIEWER]
verify:
  - python3 tests/run.py test_viewer_surfaces test_stakes
scope:
  - skills/shape-and-execute/assets/viewer/**
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - tests/**
---

# VIEWER-SURFACES-FIX-1: A Project Stakes save never loses the user's text

## Objective
Fix findings 2 and 3 of `reviews/REVIEW-VIEWER-SURFACES.md`, each with a test that fails before
the fix.

## Inputs
- `reviews/REVIEW-VIEWER-SURFACES.md` findings 2–3 (Evidence, Correction).
- `jobs/VIEWER-SURFACES.result.md`.

## Scope
- 2: text typed while a save is pending is kept. The simplest correct way wins (for example,
  disable the editor while the save is pending).
- 3: the base check and the write happen under one lock per profile; two overlapping saves from
  the same base give one success and one conflict. A missing base is refused.
- Findings 1 and 4 are let go by the orchestrator (Project Stakes). Do not work on them.

## Boundaries
- No other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the VIEWER-SURFACES branch; the result lists each finding with its fix and test.

## Validation
- [ ] One test per finding, failing before the fix.
