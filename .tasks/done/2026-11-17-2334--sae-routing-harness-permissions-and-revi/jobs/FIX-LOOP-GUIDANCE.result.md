---
status: done
summary: Approach paragraph in fix prompts from round N-1 (sticky after a park or an earlier paragraph), Approach proposal pointer in the next review round and in sae collect, park story in sae next/status with the audit opening line in every round-limit park message.
validation: pass
changes: made
resolved: []
---

# Result: FIX-LOOP-GUIDANCE

Commit `e5c939b`. The new logic is in `scripts/sae_lib/park_story.py`. `prompts.py`, `progress.py` and `reviews.py` only gained call sites.

## Validation evidence
- `test -f tests/test_fix_loop_guidance.py`: ok.
- `python3 tests/run.py test_fix_loop_guidance test_reviews test_review_rounds_setting test_dispatch_pointers test_integration_fixes`: OK (run again after the last edit, together with test_output_plain: 62 tests OK).
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Other modules: 212 tests OK, 3 skipped. They were test_fix_loop_exits, test_sae, test_retired_terms, test_output_plain, test_record_privacy, test_sae_ask, test_wait_signals, test_viewer_server, test_graph_cards, test_control, test_run_fixes, test_validation_gaps, test_writer_launch, test_stakes, test_header_overview and test_owner_ui_changes. I did not run the full suite.
- `tests/test_fix_loop_guidance.py` has 7 tests:
  - Job, N = 3: the fix after round 1 has no paragraph. The fix after round 2 gets "FIX 2 of CORE. CORE parks for the owner after review round 3." and the paths of the earlier rounds.
  - At the park, the collect message opens with the audit line and points to `sae next`. The story in `sae next` and `sae status` (text and `--json`) shows the objective, the first summary, each round's findings with their suggested fixes, the fix summaries, the "do not" limits, the options and `sae ask`.
  - After the owner raises the limit from 3 to 5, the next fix gets "… after review round 5".
  - Sticky without a park: a fix got the paragraph, then the limit was raised to 8 before round 2. The next fix still gets it.
  - Job, N = 1, and integration, N = 1: the fix after the park gets the paragraph.
  - Integration, N = 3: round 1 has no paragraph, round 2 gets it. The task-park story appears in `sae next` and `sae status`, exactly once. The collect message holds the opening line and the accept-review line.
  - Pointer: no pointer and no collect line when the section is missing or holds only a comment. With the section, the collect line is exact and the next round's prompt has the pointer. This is tested for a job round and an integration round.
- Judgment check: I printed the story for a fixture. A reader who did not follow the task can tell round by round what was found, what each fix did and what it was not allowed to do, and what the options are.

### For VIEWER-SURFACES
- **Function:** `park_story.park_story(task, key) -> dict | None`. `key` is a job ID, or `"integration"` for the parked task. It returns None when that target is not parked at the round limit.
- **Other functions:**
  - `park_stories(task) -> list[dict]` returns every story of the task.
  - `park_story_text(task, story) -> str` returns the printed text.
- **Where the data appears:** `sae next --json` and `sae status --json` both carry `park_stories`.
- **Fields of a story dict:**
  - `target`: a job ID or `"integration"`.
  - `parked_by`: the review round that parked it.
  - `opening`: the audit line.
  - `changes_rounds`, `max_rounds`: the changes-required round count and the limit.
  - `objective`: the job file's Objective. For the integration, the task title.
  - `first_summary`: the summary in the target's result frontmatter. None for the integration.
  - `rounds`: a list of `{id, round, verdict, accepted, findings, fixes}`.
    - Each finding: `{number, title, suggested_fix}`.
    - Each fix: `{id, status, summary, do_not}`.
  - `options`: a list of `{choice, commands}`. The choices are another round, change the approach, reduce the requirement, accept, and, for the integration only, close anyway.
  - `wait`: the `sae ask` line.
- **New state fields:**
  - `approach_check: {round, fix, max_rounds}` on a fix job whose prompt carried the paragraph.
  - `limit_park: <limit>` on the review round that parked its target.

## Decisions taken
- [agent] The `{fix}` number is k, the changes-required round the fix answers, not its position in the chain. Two fix jobs of one split round both read "FIX k", which matches "parks after review round N".
- [agent] `{max_rounds}` is max(N, k + 1). After a park without a raise, the next changes-required round parks again, so "after review round N" would point to a round that is already over.
- [agent] For an integration fix, `{target}` is `REVIEW-INTEGRATION`. See the wording note below.
- [agent] A job fix answers the last changes-required round of its target that completed before the fix was added. I take this from the order in events.jsonl, so older tasks need no new field. An integration fix answers its `fix_of`.
- [agent] The pointer goes into review round j for each done fix that answered round j−1 and has a non-empty `## Approach proposal`.
- [agent] Below the opening line, the collect park messages keep their old headlines, which existing tests assert. They now list the same options as the story, including `sae job drop` (only on the user's word), `sae decision new --from <REVIEW-ID>`, the amendment and `sae ask`.
- [agent] When the task parks, `integration_notice` now returns the story text, so `sae next` and `sae status` print it once. `raise_limit_hint` was no longer used, so I removed it.
- [agent] "Do not" limits are every line of the fix job file that contains "do not", "don't" or "never", with bullet markers removed.

## Risks
- **Wording problems in the constants** (the boundary says to report them, not reword them):
  1. `APPROACH_PARAGRAPH` reads "{target} parks for the owner". For an integration fix it is the task that parks, so "REVIEW-INTEGRATION parks for the owner" is a little wrong. A `{parks}` slot, or "the task parks", would fix it.
  2. The audit opening line, which I used verbatim, says "a fix job unparks the job". For the parked task it unparks the task.
- `limit_parked_jobs` also counts a job as parked at the limit when its round count is at least the current limit, even when no `limit_park` marker exists. This covers parks from before this job.

## Findings filed
None.
