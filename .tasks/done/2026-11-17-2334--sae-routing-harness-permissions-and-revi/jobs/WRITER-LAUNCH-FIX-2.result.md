---
status: done
summary: Collect refuses a result unchanged since dispatch, for a COMMAND attempt and for its fallback, using one fingerprint rule
validation: pass
changes: made
resolved: []
---

# Result: WRITER-LAUNCH-FIX-2

Commit `fa6564b` on the WRITER-LAUNCH branch.

**Rule:** at dispatch, an attempt that is a COMMAND attempt, or that follows one (the fallback, which has no `launch` record), stores `result_before`: the result file's size, `mtime_ns` and SHA-256, or null if the file is missing (`launch.py`: `result_fingerprint` and `needs_fresh_result`; set in `progress.py` `cmd_dispatch`). `sae collect` checks every result through `result_unchanged`. It refuses a result whose fingerprint still matches, without changing any state, and leaves the earlier result in place. This replaces FIX-1's `result_predates`, which compared timestamps to the second.

**Tests** (`tests/test_writer_launch.py`):
- `test_collect_refuses_an_unchanged_result_written_in_the_retrys_start_second`: the report's mtime is not earlier than the retry's start second.
- `test_fallback_collect_refuses_a_result_left_unchanged`: a COMMAND retry, then the printed fallback to claude, which leaves the report unchanged. A rewritten report is then collected.

## Validation evidence
- Before the fix, both new tests failed: `sae collect` exited 0 and marked the job done.
- `python3 tests/run.py test_writer_launch test_record_privacy`: 27 tests OK.
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: OK.
- Full suite `python3 tests/run.py`: 370 tests OK (3 skipped). `git diff --check` is clean.

## Decisions taken
- [agent] Only COMMAND attempts and the attempt right after one are checked. A subagent retry that follows a subagent attempt is not checked, because test_sae flows resume a subagent and collect the unchanged result. FIX-1 already filed this as a finding (`findings/2026-11-20-2002--subagent-retries-can-collect-the-previou.md`), and it stays open.
- [agent] A file rewritten with identical content counts as written, because its `mtime_ns` changes.
- [agent] The test helper `args_of` moved up to the shared `LaunchTestCase` base class so that both test classes can use it.

## Disputed findings
None.

## Risks
- A fallback that is itself retried as a subagent (a third attempt after the fallback) is not checked, by the rule above.

## Findings filed
None.
