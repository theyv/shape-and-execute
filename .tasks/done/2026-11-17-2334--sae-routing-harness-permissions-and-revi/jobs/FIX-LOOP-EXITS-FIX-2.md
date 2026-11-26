---
id: FIX-LOOP-EXITS-FIX-2
covers: [LET-GO-REPORT, TRIAGE]
verify:
  - python3 tests/run.py
scope:
  - skills/shape-and-execute/scripts/sae_lib/**
  - tests/**
---

# FIX-LOOP-EXITS-FIX-2: Accept only the latest changes-required round; validate let-go entries

## Objective
Fix findings 1 and 2 of `reviews/REVIEW-FIX-LOOP-EXITS-2.md`, each with a test that fails before
the fix.

## Inputs
- `reviews/REVIEW-FIX-LOOP-EXITS-2.md` findings 1–2 (Evidence, Correction).
- `jobs/FIX-LOOP-EXITS-FIX-1.result.md`.

## Scope
- 1: `--accept-review` takes the latest completed round; it records it as accepted only when its
  verdict is `changes-required`. Keep the pending-round test; add a newer-passing-round test.
- 2: `--let-go` refuses a number that does not identify exactly one finding in the named review,
  and a blank reason.
- Finding 3 is let go by the orchestrator (old title-based entries; no backward compatibility).
  Do not work on it.

## Boundaries
- No prompt text changes. No other behavior changes; a new problem becomes a finding.

## Expected output
Commits on the FIX-LOOP-EXITS branch; the result lists each finding with its fix and test.

## Validation
- [ ] One test per finding, failing before the fix.
