---
status: done
summary: Every dispatch moves an existing result aside in one function, so collect accepts only a result the attempt wrote; the fingerprint check is gone
validation: pass
changes: made
resolved: []
---

# Result: WRITER-LAUNCH-FIX-3

Commit `7be0c55` on the WRITER-LAUNCH branch.

**The single function:** `empty_result_slot(task, job_id)` in `sae_lib/tasks.py`. It has one call site: `cmd_dispatch` (`sae_lib/progress.py`), right before the new attempt is appended. That point comes after every refusal (missing CLI, hold, readiness, writer slot), so a refused dispatch moves nothing. Every dispatch path reaches it: first dispatch, `--resume`, COMMAND, the fallback after a failed COMMAND, the fallback after a missing-CLI refusal, review and non-review. `cmd_dispatch` is the only code that appends an attempt.
- An existing result file moves to `<ID>.result.attempt-<N>.md` in the same folder. N is the latest attempt's `n`, or 0 when the job has none. If that name is taken, the copy gets `-2`, `-3`, and so on, so no file is overwritten.
- The function returns the earlier result to build on: the file it just moved, or else the latest file that an earlier dispatch moved (`latest_earlier_result`). The prompt then starts with `EARLIER_RESULT_POINTER` (new in `prompts.py`): "Read first: your earlier result, moved aside: {path}. Build on it and write the full result again." On a resume, this line comes first in the RESUME block.
- `sae collect` now needs only that the result file exists. Its existing "No result file at …" message covers a missing one.

**Removed (FIX-2):** `result_fingerprint`, `needs_fresh_result` and `result_unchanged` from `launch.py` (and its `hashlib` import); the `result_before` field set in `cmd_dispatch`; the "unchanged since attempt" refusal in `cmd_collect` (`reviews.py`). No fingerprint code remains (`grep result_before|fingerprint` finds nothing under `skills/`).

**Tests** (`tests/test_writer_launch.py`):
- `test_missing_cli_fallback_after_a_local_attempt_needs_a_new_result`: review round 3's scenario. A local attempt, then a follow-up routed with `--harness codex` to a missing CLI. The refusal leaves the record and the report unchanged. The printed fallback moves the report to `R.result.attempt-1.md` (old content) and points to it. Collect then rejects until the report is rewritten, and accepts it after.
- `test_same_second_retry_starts_with_an_empty_result_slot` (adapted from FIX-2's same-second test).
- `test_fallback_collect_refuses_a_result_left_unchanged` (adapted): a fallback after a COMMAND that wrote nothing still points to `attempt-1`.
- `test_collect_refuses_a_result_the_current_attempt_did_not_write` (adapted): the moved file exists with the old content, and the COMMAND carries the pointer.
- `test_a_moved_result_never_overwrites_an_existing_file`.

## Validation evidence
- `python3 tests/run.py test_writer_launch test_record_privacy test_dispatch_pointers`: OK (included in a 90-test run, also with test_sae and test_worktree_cleanup).
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: OK.
- Full suite `python3 tests/run.py`: 372 tests. The only failures were the 4 described below, and they pass after the test changes. `git diff --check` is clean.
- Readers: the viewer (`app.js` `resultPath`, `task-views.js`) and the prompts look up exact result paths. `server.task_files` lists every `.md` file, so a moved file is shown as one more file, which causes no problem. Finish (`remove_harness_logs`, `tilde_home_files`) treats a moved file like any other record file. No reader change was needed.

## Decisions taken
- [agent] **Tests outside the scope changed:** `tests/test_sae.py` (2 flows) and `tests/test_worktree_cleanup.py` (2 tests). These tests wrote the result before dispatch, or collected the earlier attempt's result after a `--resume`. Under the owner's rule, both cases are exactly what must now be refused. The job's own `verify` command runs one of these flows, so it could not pass without the change. Each change only moves or repeats an `sb.result(...)` line. No assertion changed.
- [agent] The pointer also names a file moved by an earlier dispatch. Without that, a fallback after a COMMAND that wrote nothing would lose the report it should build on.
- [agent] The old open finding `findings/2026-11-20-2002--subagent-retries-can-collect-the-previou.md` is fixed by this rule, because subagent retries now also start with an empty slot. My job file has no `resolves`, so I did not list it in `resolved`. Triage can close it.
- [agent] Harness output files (`<stem>.codex.jsonl`, …) are not moved. The new COMMAND overwrites them.

## Disputed findings
None.

## Risks
- A research worker answering follow-up questions now writes the full report again, as the job asks. `references/roles/research-worker.md` still says to answer "at the end of your report". The prompt's pointer line says to write the full result. The role file is outside the scope, and the two do not contradict each other.

## Findings filed
None.
