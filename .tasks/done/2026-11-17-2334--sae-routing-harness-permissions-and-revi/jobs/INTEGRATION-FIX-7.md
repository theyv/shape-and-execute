---
id: INTEGRATION-FIX-7
covers: [STAKES-VIEWER]
verify:
  - python3 tests/run.py test_stakes test_viewer_surfaces
scope:
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/assets/viewer/**
  - tests/**
---

# INTEGRATION-FIX-7: A Project Stakes save can never remove another profile section

## Objective
Fix finding 1 of `reviews/REVIEW-INTEGRATION-2.md` with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION-2.md` finding 1 and `reviews/REVIEW-INTEGRATION.md` finding 1.
- `jobs/INTEGRATION-FIX-1.result.md` and `jobs/VIEWER-SURFACES-FIX-3.result.md`: the fence
  check and the section read and write today.

## Scope
This is the third data-loss finding on the same parser. Fix the rule, not the instance: a
save must never change any byte outside the Project Stakes section. Prefer the simplest rule
that guarantees it, for example:
- Project Stakes text may hold no code fence line and no heading line; a save with one is
  refused with a clear message.
- The section ends at the next line that starts with `## `, with no fence parsing at all.
- After building the new file, check that every other section's bytes are unchanged; if not,
  refuse and leave the file as it was.
Choose one, say why in the result, and remove fence handling that the rule makes unneeded.

## Boundaries
- Keep the revision, lock and line-ending behavior of VIEWER-SURFACES-FIX-1..3.
- A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the rule and the tests.

## Validation
- [ ] The review's case (open fence in Project Stakes, then `## Validation commands`, then a
      fenced shell example with a `#` comment) keeps every byte outside the section.
- [ ] A save with a fence or heading line in the new text is refused, file unchanged.
- [ ] Earlier stakes and viewer tests still pass.
