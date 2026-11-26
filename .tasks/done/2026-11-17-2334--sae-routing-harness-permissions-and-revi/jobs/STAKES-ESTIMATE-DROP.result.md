---
status: done
summary: Removed the estimate sentence from STAKES_NOT_SET_LINE and updated the test that asserted it.
validation: pass
changes: made
resolved: []
---

# Result: STAKES-ESTIMATE-DROP

## Validation evidence
- `python3 tests/run.py test_stakes test_dispatch_pointers test_retired_terms`: 49 tests, OK.
- `! grep -q 'State your estimate' skills/shape-and-execute/scripts/sae_lib/prompts.py`: passes.
- The rest of `STAKES_NOT_SET_LINE` is unchanged; the string now ends at "...the requirements you were given."

## Changed lines
- `skills/shape-and-execute/scripts/sae_lib/prompts.py`, `STAKES_NOT_SET_LINE` (lines 33-36): last two string pieces merged into `"expected, not a failure. They never lower the requirements you were given.")`.
- `tests/test_stakes.py` line 134: `assertIn("State your estimate in one line", block)` became `assertNotIn("estimate", block)`.
- `tests/test_dispatch_pointers.py`: no change needed.

## Decisions taken
- [agent] The test asserts the absence of "estimate" instead of deleting the assertion, so the request cannot return unnoticed.

## Risks
None.

## Findings filed
None.
