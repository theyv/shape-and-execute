---
status: done
summary: merge --accept-review records only a latest completed changes-required round; --let-go refuses an absent or duplicated finding number and a blank reason
validation: pass
changes: made
resolved: []
---

# Result: FIX-LOOP-EXITS-FIX-2

## Validation evidence
- `python3 tests/run.py`: 419 tests passed, 3 skipped.
- Finding 1 (`reviews.py` `cmd_merge`): new test `test_accept_review_after_a_passing_round_records_no_accepted_round`. It sets up LEFT and A editing the same file. Round 1 requires changes, the fix runs, round 2 passes, the merge conflicts (exit 4), and then `sae merge A --accept-review`. Before the fix it failed because `accepted_review: REVIEW-A` was in the decision. The pending-round test `test_accept_review_records_the_completed_round_not_a_pending_one` still passes.
- Finding 2 (`fix_loop.py` `let_go_errors`): new tests `test_let_go_refuses_an_absent_finding` (`2: rare` against a review with no numbered findings) and `test_let_go_refuses_a_blank_reason` (`2:` and `2:   `). Both failed before the fix, which I checked by temporarily restoring the old `fix_loop.py`. Both also check that state.json and events.jsonl are unchanged after the refusal.
- `git diff --check` passes.

## Decisions taken
- [agent] Finding 1 is fixed inside `cmd_merge` only. `graph.last_changes_round` stays as it was, because `findings.py` and `prompts.py` use it for the round-limit park source, where the latest changes-required round is the right answer. I removed the import from `reviews.py` because nothing there uses it any more.
- [agent] A review whose findings have no numbers now refuses every `--let-go`. Before, it accepted any number. This is what "exactly one finding" means. The orchestrator can still accept the whole round instead.
- [agent] Finding 3 is not addressed, as the job file says (the orchestrator lets it go).

## Risks
- None known.

## Findings filed
- None.
