---
id: INTEGRATION-FIX-10
covers: [STAKES-VIEWER, STAKES-LOOKUP]
verify:
  - python3 tests/run.py test_stakes test_viewer_surfaces
scope:
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - tests/**
---

# INTEGRATION-FIX-10: An ambiguous Project Stakes heading is refused, not guessed

## Objective
Fix finding 1 of `reviews/REVIEW-INTEGRATION-3.md` with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION-3.md` finding 1.
- `jobs/INTEGRATION-FIX-7.result.md`: the rule today (no fence parsing; a save never changes a
  byte outside the section).

## Scope
Do not bring fence parsing back. The rule: when the profile holds more than one line that is
exactly the Project Stakes heading (`## Project Stakes`), the section is ambiguous. Then a save
is refused with a message that names the line numbers, and the file stays as it was. The
lookup that feeds prompts and the viewer says the section is ambiguous instead of picking one
(keep the message short; pick the existing "not set" or error path that fits best and say which
in the result).

## Boundaries
- Keep every rule of INTEGRATION-FIX-7 and VIEWER-SURFACES-FIX-1..3.
- A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the rule and the test.

## Validation
- [ ] The review's case (a fenced example with `## Project Stakes` before the real section):
      the save is refused and the file is byte for byte unchanged.
- [ ] A profile with one Project Stakes heading saves as before.
