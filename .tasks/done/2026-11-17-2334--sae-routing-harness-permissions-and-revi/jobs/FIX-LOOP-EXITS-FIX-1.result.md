---
status: done
summary: Fixed REVIEW-FIX-LOOP-EXITS findings 1–4. INTEGRATE-<ID> cannot be dropped alone. --accept-review records the completed changes-required round. A let-go names one finding by its number. A decision job for a review-limit park points to the review round.
validation: pass
changes: made
resolved: []
---

# Result: FIX-LOOP-EXITS-FIX-1

Commit `fe8402e`.

## Validation evidence
- `python3 tests/run.py`: 416 tests OK, 3 skipped.
- `git diff --check`: clean.
- New tests are in `tests/test_fix_loop_exits.py`, class `ReviewFixLoopExitsTests`. With the `sae_lib` changes stashed, all four fail; with the fix, all four pass.
  - **1. `test_integrate_job_is_not_dropped_alone`.**
    - Setup: a real merge conflict, then `INTEGRATE-RIGHT` parks.
    - `sae job drop … INTEGRATE-RIGHT` is refused and prints `sae job drop <task> RIGHT --reason "<why>"`. `state.json` and `events.jsonl` stay unchanged.
    - `sae job drop … RIGHT` drops `RIGHT` and `INTEGRATE-RIGHT` together.
    - Fix: `fix_loop.cmd_job_drop`.
  - **2. `test_accept_review_records_the_completed_round_not_a_pending_one`.**
    - Setup: `REVIEW-A` says changes-required, `A-FIX-1` adds `REVIEW-A-2`, which stays pending. Then `sae merge A --accept-review`.
    - The event records `accepted_review: REVIEW-A`.
    - The report lists the findings of `REVIEW-A`.
    - Fix: new `graph.last_changes_round`, used in `reviews.cmd_merge`.
  - **3. `test_let_go_names_one_finding_by_number`.**
    - Setup: a review whose findings are `Retry` and `Retry on timeout`.
    - Refused: a let-go given by title (`Retry on timeout: rare`), and one naming a number the round does not have (`3: …`).
    - Two let-go logs for finding 2 appear once, with the later reason.
    - After the round is accepted, `Retry` is still listed, with the acceptance reason.
    - The printed line now reads `sae log <task> decision "<number>: <reason>" --job <REVIEW> --let-go`.
    - Fixes:
      - `fix_loop`: `let_go_finding`, `let_go_errors` and `let_go_lines`.
      - The check in `findings.cmd_log`.
      - The `sae log` help text and its example.
  - **4. `test_decision_job_for_a_review_limit_park_points_to_the_review`.**
    - Setup: `max-review-rounds=1`, so `A` parks after `REVIEW-A`.
    - The job file of `DECISION-A-1` names `reviews/REVIEW-A.md` as "the review round that parked it", and also lists `A`'s job file.
    - The prompt prints `Review round that parked A: …/reviews/REVIEW-A.md`. Neither the job file nor the prompt mentions "Decision request".
    - Fixes: `findings.decision_source` and `prompts.decision_source_lines`. Both use the `Decision request` section only when it has content.
- Existing tests updated to the number form. The report lines change:
  - Old: `- <REVIEW>: <summary>`.
  - New: `- <REVIEW>: <title> — let go: <reason>`.

## Decisions taken
- [agent] Finding 1: `sae job drop` refuses an `INTEGRATE-<ID>` job named alone and prints the target's drop command. The job file prefers this to a fresh resolution job.
- [agent] Finding 3:
  - `sae log --let-go` now refuses a summary that has no finding number, or that names a number the round does not have. The number is the only identity; the review number is in `--job`.
  - In the report, a let-go line shows the finding's title from the review file.
  - Let-go events logged before this change have no number. The report prints them raw, as before.
- [agent] Finding 3: when one finding is let go twice, the report keeps the latest reason, so the finding is listed once.

## Risks
- `findings.py` is now 824 lines, `reviews.py` 806 and `fix_loop.py` 307.

## Findings filed
None.
