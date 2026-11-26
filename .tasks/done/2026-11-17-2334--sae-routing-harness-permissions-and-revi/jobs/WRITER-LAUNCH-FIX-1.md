---
id: WRITER-LAUNCH-FIX-1
covers: [WRITER-COMMAND, HARNESS-FALLBACK]
verify:
  - python3 tests/run.py test_writer_launch test_record_privacy
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/launch.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/reviews.py
  - skills/shape-and-execute/scripts/sae_lib/workspaces.py
  - tests/test_writer_launch.py
  - tests/saetest.py
---

# WRITER-LAUNCH-FIX-1: Fix the four findings of the WRITER-LAUNCH review

## Objective
Fix findings 1–4 of `reviews/REVIEW-WRITER-LAUNCH.md`, each with the test that the review names.

## Inputs
- `reviews/REVIEW-WRITER-LAUNCH.md` in the task folder: findings 1–4 (Evidence, Correction).
- `jobs/WRITER-LAUNCH.md` and `jobs/WRITER-LAUNCH.result.md`.

## Scope
- 1 (blocking): a parked job with no started attempt is a first dispatch for the hold and
  dependency checks, also through the printed fallback with `--resume`.
- 2: `sae collect` accepts only a result that the current attempt wrote or updated; the earlier
  report stays available to the retry.
- 3: a Codex writer COMMAND in a task without git carries `--skip-git-repo-check`, in the
  printed and the recorded command.
- 4: a successful fallback dispatch closes the failed COMMAND attempt (`ended` set).
- Check each finding before you act; list one you believe wrong under "Disputed findings".

## Boundaries
- No prompt text changes. No other behavior changes; a new problem becomes a finding.

## Expected output
Commits on the WRITER-LAUNCH branch; the result lists each finding with its fix and test.

## Validation
- [ ] One test per finding, failing before the fix.
