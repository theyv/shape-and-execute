---
status: done
summary: A let-go selector is a number only when the whole argument is one; a selector matching two findings is refused.
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-11

## Validation evidence
`python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance`: 34 tests OK.

Rule (`resolve_let_go` in `fix_loop.py`): number only via `WHOLE_NUMBER_RE` (whole argument: `2`, `#2`, `finding 2`); otherwise exact title; if the number and an exact title name different findings, refused with the findings list.

Tests: `test_let_go_number_is_the_whole_argument_and_a_double_match_is_refused` (`2` selects finding 2, `2: Retry on timeout` selects finding 1) and `test_let_go_refuses_a_selector_that_matches_two_findings`.

## Decisions taken
[agent] A finding titled "2" that is finding 2 is not a double match (same finding).

## Risks
None known.
