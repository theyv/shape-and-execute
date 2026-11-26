---
status: done
summary: A Project Stakes save keeps the user's text; the editor is locked while a save is pending, and each profile save runs its base check and write under one lock.
validation: pass
changes: made
resolved: []
---

# Result: VIEWER-SURFACES-FIX-1

## Validation evidence
- `python3 tests/run.py test_viewer_surfaces test_stakes`: 37 tests, OK.
- Full suite `python3 tests/run.py`: 437 tests, OK (skipped=3).
- `git diff --check`: clean.
- Each new test failed before the fix (checked with the source changes stashed):
  - Finding 2, `ProjectStakesTests.test_typing_is_blocked_while_a_save_is_pending`. The test holds a save open in node, then types. Before the fix the box was not disabled, and the typed text went into the draft that success then cleared.
  - Finding 3, `OverlappingStakesSaveTests.test_overlapping_saves_from_one_base`. Two in-process request threads save from the same base, with a slowed writer. Before the fix they returned `[200, 200]`; now they return `[200, 409]`.
  - Finding 3, missing base. The new step in `test_refusals_leave_every_file_as_it_was` expects 400 and an unchanged file. Before the fix the save was accepted with 200.
- Commit `6a5fe3d` on the VIEWER-SURFACES branch.

## Decisions taken
- [agent] Finding 2: while a save is pending, the text box, Save and Discard are disabled, and the input handler ignores input. The job file names this as the simplest correct option, so the fix does not track draft versions. After the save answers, the page redraws and the box can be used again. A failed save keeps the draft.
- [agent] Finding 3: the server holds one `threading.Lock` per resolved profile path (`server.stakes_lock`). A process lock is enough because the request threads of the one viewer server are the only writers of the section. The source check, the base check and the write all run inside that lock. A request without a string `base` is refused with 400 before the lock is taken.
- Findings 1 and 4 were let go by the orchestrator and were not worked on.

## Risks
- A save made outside the viewer, such as a hand edit or a second viewer process, is not covered by the lock. The base check still catches edits made before the check.

## Findings filed
None.
