---
status: done
summary: Pending and running writer review flags can change through the CLI and viewer until collection.
validation: pass
changes: made
resolved: []
---

# Result: REVIEW-TOGGLE

Commit: `88ef537`.

## Validation evidence

- `python3 tests/run.py test_viewer_server test_reviews test_graph_cards test_control`: 62 tests passed; two skipped.
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: passed.
- `python3 tests/run.py test_review_flag test_graph_cards`: 26 tests passed; two skipped. This includes six new tests.
- `python3 tests/run.py test_plan_lint_and_gate`: passed.
- `git diff --check`: passed. Worktree clean after commit.

The tests cover pending changes, both running directions, refusals, reason and origin events,
planned reviews, next-step card notices, and collection under selected-jobs, all-jobs and job
reviews off. The server route runs the CLI. Settings remain unchanged. Native buttons have an
accessible name and pressed state. Controls appear in job details and Next up. The rendered
markup was checked with Node; browser visual inspection remains part of FINAL-CHECK.

Collection and planned reviews already read the current flag. No review scheduling change
was needed.

## Decisions taken

None beyond the specified behavior and existing route pattern.

## Risks

None identified.

## Findings filed

None.
