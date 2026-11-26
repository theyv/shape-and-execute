---
status: done
summary: The Project Stakes save base is now a SHA-256 revision of the exact stored section, compared under the existing lock; regression tests for comment-only and trailing-space-only saves.
validation: pass
changes: made
resolved: []
---

# Result: VIEWER-SURFACES-FIX-2

Commit `de2b768` on the VIEWER-SURFACES branch.

- Fix: `stakes.section_revision(path)` gives a SHA-256 of the raw section (heading to end, with
  comments and spaces), or "" when the section is missing. `server.stakes_data` sends it as
  `base`. `server.save_stakes` compares it under `stakes_lock`. `text` and `draft` stay the
  normalized text. The viewer treats `base` as an opaque value. Only a comment in
  `settings.js` and the README line changed.
- Tests (`tests/test_viewer_surfaces.py`, `OverlappingStakesSaveTests`):
  `test_a_save_of_trailing_spaces_only_moves_the_base` and
  `test_a_save_of_a_comment_only_moves_the_base`. In each, the first save changes the stored section
  but leaves `section_text` the same and returns 200. The second save from the same base returns
  409, and the file stays as the first save left it. The overlapping-saves test now takes its
  base from `stakes_data`.

## Validation evidence
- Before the fix, both new tests failed: the second save returned 200 and overwrote the first.
- After the fix, `python3 tests/run.py test_viewer_surfaces test_stakes` ran 39 tests: OK. The FIX-1
  tests are among them.
- `python3 tests/run.py` (full suite) ran 439 tests: OK (3 skipped). The run began after the code fix;
  only the README wording changed after that.
- `git diff --check` was clean.

## Decisions taken
- [agent] The revision covers the heading line through the section end. It does not cover the
  whole file, so edits elsewhere in the profile never block a stakes save.

## Risks
- A page that loaded before this change and still holds a text base gets one 409 on its next save.
  The user then reloads, as the message already says.
