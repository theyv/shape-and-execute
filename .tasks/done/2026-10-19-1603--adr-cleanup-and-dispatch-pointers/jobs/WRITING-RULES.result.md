---
status: done
summary: Writing rules name three places by reach and the test; template has optional revisit-when; test covers adr new/accept with and without it.
validation: pass
changes: made
resolved: []
---

# Result: WRITING-RULES

## Validation evidence
- `python3 tests/run.py test_adr_index test_adr_rules test_retired_terms test_findings`: 26 tests OK.
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: OK.
- [THREE-PLACES]: `plan.md` "Decision-record drafts" states the three places and the test. `execute.md`
  "Finish" step 1 and `triage-decisions.md` step 2 point to it in one or two lines. The old
  "could not rebuild from the code" test is gone from all three files, not kept beside the new one.
- [REVISIT-WHEN]: `templates/decision-record.md` has `revisit-when:` with a one-line comment. The new
  test `test_new_and_accept_work_with_and_without_revisit_when` in `tests/test_adr_index.py`
  accepts an empty field, a filled field and a draft without the field.
- The `applies-to` comment now says that path entries bring the record to the agents that change them.
- Commit: dd5e151 on the job branch.

## Decisions taken
- [agent] I updated `tests/test_findings.py` (outside the listed scope), so the template-fields set
  includes `revisit-when`. Without this change the test fails.
- [agent] `plan.md` is the file that states the rule, because `execute.md` already pointed there.

## Risks
- None known.

## Findings filed
- ~/Library/Caches/shape-and-execute/worktrees/shape-and-execute-3f2d3e60/2026-10-19-1603--adr-cleanup-and-dispatch-pointers/task/.tasks/findings/2026-10-19-1654--sae-adr-new-help-text-keeps-the-old-coul.md
  (the `sae adr new` help text still states the old test; changing it needs a `sae` code change)
