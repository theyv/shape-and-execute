---
status: done
summary: Fixed REVIEW-WRITER-LAUNCH findings 1–4, each with a test that failed before the fix
validation: pass
changes: made
resolved: []
---

# Result: WRITER-LAUNCH-FIX-1

Commit `72a0b72` on the WRITER-LAUNCH branch.

| # | Fix | Test (tests/test_writer_launch.py) |
|---|-----|------|
| 1 | `cmd_dispatch` (progress.py) runs the integration-park, hold and dependency checks for a first dispatch and also for `--resume` of a parked job with no attempts | `test_parked_job_without_attempts_meets_an_active_hold_through_the_fallback` |
| 2 | `sae collect` (reviews.py, `result_predates`) refuses a COMMAND attempt's result last changed before the attempt started; the earlier result stays in place | `test_collect_refuses_a_result_the_current_attempt_did_not_write` |
| 3 | `command_line` (launch.py) adds `--skip-git-repo-check` to a Codex writer COMMAND in a task without git, in the printed and the recorded command | `test_codex_writer_in_a_task_without_git_skips_the_repo_check` |
| 4 | A `--resume` dispatch sets `ended` on the open COMMAND attempt it replaces (same timestamp as the new attempt's `started`) | `test_fallback_closes_the_failed_command_attempt` |

## Validation evidence
- All four new tests failed before the fixes, each for its finding's reason (exit 0 instead of 3, `ended` None, flag missing, stale collect accepted).
- `python3 tests/run.py test_writer_launch test_record_privacy`: 25 tests OK.
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: OK.
- Full suite `python3 tests/run.py`: 368 tests OK (3 skipped). `git diff --check` clean.

## Decisions taken
- [agent] Finding 2 uses the result file's mtime against the attempt's `started` (second precision). No new state field. The previous result is not moved, so a reopened research job can still update its report in place.
- [agent] Finding 2 applies only to COMMAND attempts (those with `launch`). With every attempt checked, two test_sae flows (a verify-failed resume, and wt-flow B) failed under load: they resume a subagent and collect the unchanged result. test_sae.py is outside this job's scope, and the job allows no other behavior changes. Filed as a follow-up.
- [agent] Finding 4 closes the open COMMAND attempt on any `--resume`, not only a fallback. Any resume abandons that attempt.
- [agent] Finding 3 covers writers only, as the review asks. The review COMMAND is unchanged and filed as a finding.

## Disputed findings
None.

## Risks
- If a result was written before dispatch but within the same second, the mtime check still accepts it. That cannot happen in a real retry.

## Findings filed
- ~/Library/Caches/shape-and-execute/worktrees/shape-and-execute-3f2d3e60/2026-11-17-2334--sae-routing-harness-permissions-and-revi/task/.tasks/findings/2026-11-20-1959--codex-review-command-in-a-task-without-g.md
- ~/Library/Caches/shape-and-execute/worktrees/shape-and-execute-3f2d3e60/2026-11-17-2334--sae-routing-harness-permissions-and-revi/task/.tasks/findings/2026-11-20-2002--subagent-retries-can-collect-the-previou.md
