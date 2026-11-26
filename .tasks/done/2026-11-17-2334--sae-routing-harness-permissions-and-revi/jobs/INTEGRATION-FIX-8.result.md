---
status: done
summary: Let-go takes the finding and the reason as separate arguments; no title is guessed.
validation: pass
changes: fix_loop.py resolve_let_go and let_go_line, findings.py log command and help, tests/test_fix_loop_exits.py
---

New call shape: `sae log <task> decision --job <REVIEW-ID> --let-go "<number or exact title>" --reason "<why>"`.
The summary argument is now optional (omitted with --let-go). Unknown finding, ambiguous title or
missing/blank reason is refused with the review's findings listed; nothing is written then.
`execute.md` shows no call (it points to the line `sae` prints), so it is unchanged. Old events
without the stored finding still parse in the report.

## Validation
- `python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance`: 32 tests OK.
- New test `test_let_go_of_titles_that_start_each_other_keeps_each_reason`: "Retry" and
  "Retry: lost write" let go separately, each reason correct in the final report.
- Unknown title/number refusal tests updated.

## Decisions taken
- [agent] Numbered reviews also accept an exact title (mapped to its number); by-title reviews accept titles only.
