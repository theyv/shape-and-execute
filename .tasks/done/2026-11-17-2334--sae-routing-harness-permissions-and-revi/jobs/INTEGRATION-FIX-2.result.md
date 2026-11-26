---
status: done
summary: A fallback resume continues the same chain writer's uncommitted edits, and a parked job meets holds and the integration park on every resume
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-2

## Validation evidence
- Both new tests failed before the fix, each for the reason the review gives. Finding 2 failed with exit 4, "Tracked files outside .tasks/ have uncommitted changes". Finding 3 failed with exit 0 where exit 3 was expected.
- `python3 tests/run.py test_writer_launch`: 28 tests, OK (the `verify` command).
- Full suite `python3 tests/run.py`: 445 tests, one failure. My own docstring used the retired term "task checkout". I fixed it, then reran `test_retired_terms`, `test_writer_launch`, `test_task_worktree` and `test_sae`: 68 tests, OK. `git diff --check` is clean.
- Finding 2: `test_fallback_continues_a_chain_writer_that_left_a_tracked_edit`. In a chain layout, a first dispatch with a dirty tracked file is still refused. After a COMMAND attempt leaves a tracked edit, the job is parked and the printed fallback runs. It starts attempt 2 in the task worktree, and the edit is kept.
- Finding 3: `test_parked_job_with_a_failed_attempt_meets_an_active_hold_through_the_fallback`. The sequence is: A fails its COMMAND attempt and is parked; B finishes and a hold follows it; the owner's yes is logged; A's fallback runs. The fallback is refused with exit 3 and the state stays unchanged. After the hold is released, it runs as attempt 2.

## Decisions taken
- [agent] The clean-checkout guard is skipped only for a `--resume` of a writer that is running or parked, has an attempt, and is the last writer to start in the task (`continues_unfinished_writer` in `workspaces.py`). A failed or done writer, or one that another writer started after, still meets the guard. The branch check always runs.
- [agent] A parked job meets the parked-task and hold gates on every resume. The waits-for check still runs only on a first dispatch. Running and failed jobs that resume keep their earlier behavior.

## Risks
- The new gate condition applies to every parked non-decision job, not only writers. Today only `sae job park` sets `parked`, and it is used for harness fallbacks, so this matches the hold rule.
