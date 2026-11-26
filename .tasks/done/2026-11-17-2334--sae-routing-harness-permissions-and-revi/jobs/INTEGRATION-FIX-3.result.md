---
status: done
summary: Decision jobs dispatch and collect in shaping and planning; --let-go resolves to exactly one finding and stores finding and reason apart
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-3

## Validation evidence
- Finding 5: `common.py` `KINDS_BY_PHASE` now includes `decision` in shaping and planning; the
  phase check in `graph.kind_allowed_now` (dispatch, `--resume`, `sae next`) and
  `session_tokens.kind_phases` follow from it. Test
  `test_decision_job_from_a_plan_review_runs_before_plan_approval`: a done changes-required
  REVIEW-PLAN, then `sae decision new --from REVIEW-PLAN`, which is ready in `sae next`,
  dispatched (prompt points to `reviews/REVIEW-PLAN.md`) and collected while the task is still
  in planning. An implementation job still waits for `phase planning`. Before the fix, the test
  failed because the decision job was not ready.
- Finding 6: `fix_loop.resolve_let_go` (replaces `let_go_errors`) returns (finding, reason,
  error). `cmd_log` stores `finding` and `reason` on the decision event; `let_go_lines` uses
  them, and parses the summary only for older events. Test
  `test_let_go_by_title_names_exactly_one_finding`: "Retry: rare" and "Missing: rare" are refused
  against the titles "Retry: lost write" and "Slow path". "Retry: lost write: the queue retries it"
  is stored as finding "Retry: lost write" with its own reason, and the report lists it once.
  Before the fix, the test failed: the absent title was accepted.
- `python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance` (verify): 31 tests OK.
- Full suite `python3 tests/run.py`: 445 tests OK (3 skipped). `git diff --check` clean.

## Decisions taken
- [agent] Title matching picks the longest review title that the summary starts with, followed
  by a colon. A title with a colon stays whole. When the review also has a shorter title that is
  a prefix ("Retry" and "Retry: lost write"), the longer one wins. Two identical titles are
  refused.
- [agent] Decision jobs are allowed in every phase through `KINDS_BY_PHASE`, so they also work
  for a spec-review decision in shaping, as the review notes.

## Risks
- A decision event from before this change, against a review that has both "Retry" and
  "Retry: lost write", is now read with the longest match. The old reading took the shorter one.

## Findings filed
None.
