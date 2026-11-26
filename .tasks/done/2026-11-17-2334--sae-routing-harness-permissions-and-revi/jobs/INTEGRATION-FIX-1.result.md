---
status: done
summary: A Project Stakes save is refused, file untouched, when the new text or the stored section leaves a code fence open
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-1

Commit `0c00d01`. Fix in `stakes.save_profile_stakes` (`_leaves_fence_open`); the server route
already turns its ValueError into a 400 with the message.

## Validation evidence
- `python3 tests/run.py test_viewer_surfaces test_stakes`: 44 tests OK. Before the fix, the 3 new or extended tests failed. The route returned 200 and the section swallowed `## Validation commands` and `## Hot files`.
- New tests, both with sections after Project Stakes:
  - `test_stakes.WriterTests.test_text_with_an_unclosed_code_fence_is_refused_and_the_next_section_stays`: an unclosed fence is refused, the bytes stay the same, a closed fence (even around a `## ` line) is accepted, and the next save keeps `## Validation commands`.
  - `test_stakes.WriterTests.test_a_stored_section_with_an_unclosed_code_fence_is_never_overwritten`: the stored section is ambiguous, so the save is refused and the bytes stay the same.
  - `test_viewer_surfaces.ProjectStakesTests.test_refusals_leave_every_file_as_it_was`: both cases go through `POST /api/stakes`. Each gets 400 with "code fence", and the file stays the same.
- The VIEWER-SURFACES-FIX-1..3 tests (overlapping saves, CRLF bytes, revision from one read) still pass.
- `git diff --check`: clean. Full suite `python3 tests/run.py`: 445 tests OK (3 skipped).

## Decisions taken
- [agent] One rule for both cases: the section must close every code fence it opens (the fence count is even, using the same ```` ``` ```` test as the heading reader). I rejected a fence-blind heading scan because it would also refuse legitimate code that has `# comment` lines inside a closed fence.
- [agent] A stored section with an unclosed fence is refused even when it is the last section and nothing is hidden. The owner fixes the file by hand. This is the simplest safe rule.

## Risks
- The stored-section check can miss one case: a heading is swallowed, but the fence count still balances. That needs a second, separate unbalanced fence in a later section, so the rest of the profile is already malformed. It is not detected.

## Findings filed
- None.
