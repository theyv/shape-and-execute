---
status: done
summary: Profile sections are read without fence parsing; a Project Stakes save refuses fence lines and can no longer change a byte outside the section
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-7

Commit `d6bc4e3`. Code: `skills/shape-and-execute/scripts/sae_lib/stakes.py`.

## Validation evidence
- `python3 tests/run.py test_stakes test_viewer_surfaces`: 51 tests OK. Before the fix, 3 new tests in `test_stakes` failed (35 run, run with the old `stakes.py`).
- New tests in `tests/test_stakes.py`:
  - `test_a_stored_open_fence_never_costs_the_sections_after_it`: the review's case (open fence in Project Stakes, `## Validation commands`, a fenced shell example with `# set up once` under `## Worktree notes`). The save is refused with bytes unchanged. After the owner removes the open fence, a save keeps every byte outside the section.
  - `test_a_fenced_shell_comment_in_another_section_is_not_part_of_the_stakes_section`.
  - `test_text_with_a_code_fence_line_is_refused_and_the_file_stays` (open, closed and indented fences) and `test_text_with_a_heading_of_level_one_or_two_is_refused_and_the_file_stays` (a `###` heading is still allowed).
  - `test_a_stored_section_with_a_code_fence_line_is_never_overwritten`.
- `test_viewer_surfaces.ProjectStakesTests.test_refusals_leave_every_file_as_it_was` extended: open and closed fence through `POST /api/stakes` give 400, file unchanged. Revision, lock and CRLF tests of VIEWER-SURFACES-FIX-1..3 still pass.
- `git diff --check` clean. Full suite not run (only FINAL-VALIDATION runs it).

## Decisions taken
- [agent] The rule is options 1 and 2 of the job together: no fence parsing at all, and the section ends at the next level 1 or 2 heading line. A fence line is refused in the new text and in the stored section. I chose it because every earlier fix relied on fence parity, which breaks when any fence anywhere in the file is unbalanced. Now a `# comment` in a fenced example can only end a section early, never make it run into the next one, so the bytes outside the section are kept by construction. `_leaves_fence_open` and the fence tracking in `_headings` are removed.
- [agent] Option 3 (compare the other sections' bytes after building) is not added: with the same reader it is true by construction.
- [agent] The stored section with a fence line is refused even when no data would be lost, because a fenced `# comment` inside it ends the section early and the save would leave the rest of the example as junk in the file. The owner edits the file by hand.
- [agent] A `###` or deeper heading in the new text stays allowed (it cannot end the section); the job text said "no heading line", but only level 1 and 2 matter for the rule.

## Risks
- A `## Project Stakes` line inside another section's fenced example, before the real section, would now be taken as the section. This needs a hand-written profile with that example; fence-aware reading had its own, worse failure (data loss).
- The viewer's `section()` in `app.js` still tracks fences. It only reads job and result files (Decision request, Objective, Riskiest assumptions), not the profile, so I left it.

## Findings filed
- None.
