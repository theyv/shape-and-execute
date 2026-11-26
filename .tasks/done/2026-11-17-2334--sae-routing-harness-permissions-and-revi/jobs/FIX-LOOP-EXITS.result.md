---
status: done
summary: Decision jobs for any job, round or question (they pass holds and the parked task); sae job drop with the dropped status; sae accept-review; --let-go; the four changes-required lines; a final report with findings let go, accepted rounds and dropped jobs.
validation: pass
changes: made
resolved: []
---

# Result: FIX-LOOP-EXITS

Commit `e74d4c2`. The new logic is in `scripts/sae_lib/fix_loop.py` (266 lines). It holds `sae job drop`, `sae accept-review`, the changes-required lines and the report sections. The other files only gained call sites and small gate changes.

## Validation evidence
- `test -f tests/test_fix_loop_exits.py`: ok.
- `python3 tests/run.py test_fix_loop_exits test_reviews test_review_rounds_setting test_integration_fixes test_run_fixes test_control test_validation_gaps test_worktree_cleanup`: 83 tests OK.
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Neighbouring modules: 226 tests OK, 3 skipped. They were test_sae, test_writer_launch, test_findings, test_resolves, test_graph_cards, test_viewer_server, test_owner_ui_changes, test_retired_terms, test_output_plain, test_dispatch_pointers, test_record_privacy, test_wait_signals, test_sae_ask, test_header_overview, test_stakes and test_review_flag. I did not run the full suite.
- `tests/test_fix_loop_exits.py` has 14 tests. Each validation item of the job file has one:
  - DECISION-ANYTIME:
    - `--question` alone creates `DECISION-1`, with the question in the job file.
    - `--from` a review round points to its review file.
    - `--from` a done job points to its job file and result.
    - `--from` a parked job works as before.
    - The prompt test covers all three sources.
    - A decision job dispatches and collects while the round limit parks the task. A writer still gets exit 3.
  - Gate order during a hold:
    - A decision job with `--harness codex` and no codex CLI exits 1, with `state.json` and `events.jsonl` byte-identical.
    - A writer gets exit 3.
    - The decision job then dispatches.
  - Audit proposal 2:
    - The exact four lines appear for a job round and for an integration round.
    - The second job round prints `A-FIX-2` and `--job REVIEW-A-2`.
    - The finish refusal and `sae next` name `sae accept-review`.
  - ACCEPT-INTEGRATION:
    - After the acceptance, FINAL is ready and `sae finish` passes without `--override`.
    - At the round limit, the acceptance ends the park.
    - `--fix-of` an accepted round is refused.
    - A job review is refused, with the `sae merge --accept-review` line. A pass round and a non-review are refused too.
  - TRIAGE and LET-GO:
    - In a real fix round, one finding is let go, and the report lists it once.
    - An accepted round lists each finding title with the reason. A finding logged on its own, by number or by title, appears once with its own reason.
  - JOB-DROP:
    - A drop is refused while a member is running, for a fix job named alone (the message names the target), and while FINAL needs RIGHT (the message prints `sae job edit … --needs "LEFT"`). Every refusal leaves the record unchanged.
    - After the drop, the group is `dropped`, and merge, dispatch and `--fix-of` are refused.
    - REVIEW-INTEGRATION is added with `needs: [LEFT]` once LEFT merges. FINAL is then ready, and `sae finish` runs with no flags.
    - The task branch has none of RIGHT's files. The branch and the result files stay.
    - A drop in a chain-layout task is refused before any change. Pending, merged and non-writer jobs are refused too.
- `tests/test_reviews.py`: one notice assertion now expects the audit's new lead line. No gate test changed.

### For VIEWER-SURFACES
- **Status:**
  - `dropped` is in `common.JOB_STATUSES`.
  - `FINAL_STATUSES = ("done", "dropped")`.
- **Job fields in `state.json`:**
  - `drop: {group, reason, was, at}` on every dropped member. `group` is the job named in the drop; `was` is the status before the drop.
  - `accepted: {reason, at, by}` on an accepted integration round. Its `verdict` stays `changes-required`.
- **Events:**
  - `job.dropped {job, group, was: {id: status}, reason, by}`.
  - `decision` gains these fields:
    - `let_go: true` on a let-go log.
    - `accepted_review: <REVIEW-ID>` and `reason` on both accept commands. `sae merge --accept-review` adds `accepted_review` only when the job has a review round.
    - `dropped: [ids]` on the drop decision, with `by: human`.
- **Functions:**
  - `graph`: `is_dropped(job)`, `unaccepted_changes(job)`, `live_writers(task)` and `round_fixes(task, review_id)`.
  - `fix_loop`: `drop_group(task, id)`, `let_go_lines(task, events)`, `review_findings(text)` and `fix_loop_report_lines(task, events)`.
- **Final report sections:** "Findings let go", "Accepted integration rounds" and "Dropped jobs".

## Decisions taken
- [agent] `fix_loop.py` is a new module, which is not in the job's scope list. The brief and `sae_lib/AGENTS.md` ask for one module per area, and `reviews.py` was at about 785 lines. The collect scope audit will warn about this file.
- [agent] An accepted round keeps `requires_changes`, so it still counts toward `max-review-rounds`. Only `unaccepted_changes` blocks: the parked task, the final validation, the verdict and stale gates, the next round and the notices. After the acceptance, a late merge adds a "changes" round, as after a pass.
- [agent] The drop group also takes `INTEGRATE-<ID>` when its target is in the group. Otherwise that job would merge the dropped commits.
- [agent] Integration review rounds ignore dropped needs, so they never block a drop. Any other job that needs a dropped job waits with "<ID> (dropped)".
- [agent] `sae job drop` refuses a pending job and points to `sae job remove`. The spec names parked, failed or done jobs.
- [agent] The drop decision is logged with `by: human`, because it happens only on the owner's word. So it is not under "To check before you merge"; the report lists it under "Dropped jobs". `--let-go` decisions are also left out of "To check", because they have their own section. `sae accept-review` logs `by: agent`, as `merge --accept-review` does.
- [agent] `--let-go` needs `type decision` and a review in `--job`. A let-go names a finding of an accepted round when its summary starts with the finding's title, or when the part before ":" is its number (`2`, `#2`, `finding 2`).
- [agent] `cmd_dispatch` gate order: first the parked task and the hold (a decision job skips both), then waits_for, then the writer slot, then the CLI check. All of them run before any change. The due-review CLI check keeps its place before `add_due_review`.
- [agent] Park messages: the integration park in `apply_integration_review` and in `integration_notice` gained only the accept line. The job park and the rest of the story stay for FIX-LOOP-GUIDANCE.

## Risks
- None of the prompt texts that I compared contradicts the code. execute.md names `sae job drop`, the `--let-go` line, `sae accept-review` and the Finish list as the code now has them.

## Findings filed
None.
