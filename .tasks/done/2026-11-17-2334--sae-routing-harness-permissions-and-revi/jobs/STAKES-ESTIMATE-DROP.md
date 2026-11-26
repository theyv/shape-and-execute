---
id: STAKES-ESTIMATE-DROP
covers: [STAKES-POINTER]
verify:
  - python3 tests/run.py test_stakes test_dispatch_pointers test_retired_terms
  - "! grep -q 'State your estimate' skills/shape-and-execute/scripts/sae_lib/prompts.py"
scope:
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - tests/test_stakes.py
  - tests/test_dispatch_pointers.py
---

# STAKES-ESTIMATE-DROP: Remove the estimate request from the "not set" text

## Objective
Delete the last sentence, "State your estimate in one line in what you write back.", from
`STAKES_NOT_SET_LINE` in `prompts.py`, and update the tests that assert it.

## Inputs
- `scripts/sae_lib/prompts.py`: `STAKES_NOT_SET_LINE` (from `STAKES-TEXT-FIX`).

## Scope
Owner decision, 2026-11-20: the request may make every agent comb the whole repository to
estimate the stakes. Keep the rest of the text word for word.

## Boundaries
- No other text or code changes.

## Expected output
One commit; the result names the changed lines.

## Validation
- [ ] The rest of `STAKES_NOT_SET_LINE` is unchanged.
