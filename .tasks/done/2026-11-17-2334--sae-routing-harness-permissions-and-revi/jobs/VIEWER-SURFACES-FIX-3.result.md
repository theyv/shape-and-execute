---
status: done
summary: Stakes draft and revision come from one profile read; stakes reads, revisions and saves keep the profile's stored line endings
validation: pass
changes: made
resolved: []
---

# Result: VIEWER-SURFACES-FIX-3

Commits `36c5733` (one read) and `5d5906e` (line endings) on the VIEWER-SURFACES branch.

## Validation evidence
- `python3 tests/run.py test_viewer_surfaces test_stakes`: 42 tests OK.
- Full suite `python3 tests/run.py`: 442 tests OK (3 skipped).
- `git diff --check`: clean.
- REVIEW-VIEWER-SURFACES-3 finding 1: `stakes.section_and_revision` reads the profile once, and
  `server.stakes_data` takes `draft` and `base` from it. The test
  `OverlappingStakesSaveTests.test_a_save_during_a_settings_load_never_pairs_an_old_draft_with_the_new_base`
  makes another tab save right after the load's k-th profile read, for every k. The loading tab's save may
  return 200 only when its draft already held the other edit. Otherwise it must get 409. Before the fix it
  failed at k=2 (old draft, new base, 200).
- REVIEW-VIEWER-SURFACES-3 finding 2: stakes.py reads the profile as bytes (`read_stored`), so
  `section_revision` hashes the stored CRLF. The test `test_a_change_of_line_endings_only_moves_the_base` failed before the fix: it got 200 and expected 409.
- REVIEW-VIEWER-SURFACES finding 1: `save_profile_stakes` writes the bytes as they are (`_write_stored`), and
  the lines it adds take the profile's CRLF. The test `test_a_save_keeps_the_crlf_bytes_outside_the_section`
  checks that every byte outside the section stays the same and checks the exact new section bytes. Before the fix it failed because the whole file came back as LF.
- An ad-hoc check covered the cases with no section in a CRLF profile, at the end of the file and before another `##`. In
  both cases the result was CRLF, and a second save of the same text changed nothing. The same check on an LF profile gave the same output as before.
- The FIX-1 and FIX-2 tests (overlapping saves, trailing-space and comment-only saves) still pass.

## Decisions taken
- [agent] Local raw read/write helpers live in `stakes.py`. `common.read_text` and `write_atomic` stay as they are, because they are shared and out of scope. `_write_stored` writes bytes, so on Windows a CRLF line never gets a second CR.
- [agent] A save turns the incoming text's CRLF into LF before it adds the profile's own line ending.
- [agent] `find_stakes` still reads the profile on its own during a settings load. Its `text` and `source` only
  affect the display. The save checks only `base`, which now comes from the same read as `draft`.

## Risks
- None known.

## Findings filed
- None.
