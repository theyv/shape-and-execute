---
status: done
summary: Fix-loop texts fixed for issues 1-8, 10-12, 14; the options print in full only in the story; "user" is the word for the human
validation: pass
changes: made
resolved: []
---

# Result: FIX-LOOP-TEXTS

## Validation evidence
- `python3 tests/run.py`: 427 tests OK (3 skipped), after the commit 99b2a20. The first run
  failed 2 tests in `test_review_rounds_setting`, which looked for the options in the
  `sae collect` message. They now look for them in `sae next`.
- `python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance test_reviews`: 45 tests OK.
- Tests now assert the new texts in full where they asserted the old ones (collect message of a
  job round and of an integration round, `sae next` notice, the job and task park options,
  the park message of `sae collect`, the dispatch refusal, decision-job inputs in the job file
  and the prompt). New tests: let-go by title (issue 14), empty `--reason` (issue 8), the final
  report after a drop (issue 10).
- Every command printed in the fix loop now runs as printed once its placeholders are filled.
  There is no `<ID>` left, and no trailing comment such as `(only on the user's word)` after a
  command.

## Issues, before → after
1, 3. PARK_OPENING: "… Add no fix job and accept nothing before the user answers: a fix job
   unparks the job. Relay the story …" → "Parked at the round limit: the choice is the user's,
   in every mode. Relay the story with your recommendation and its reason, and run an option
   only after the user answers." This fits both a job park and a task park. The task park's
   "change the approach" no longer prints `sae job drop <task> <ID>`. The integration review
   runs only after every live writer merged, and a merged job cannot be dropped, so no job is
   left to drop. It keeps `sae decision new … --from <round>`.
2. The full options are printed only in the story (`sae next` and `sae status`; the spec's
   [PARK-STORY] wants the story in both). `sae collect` at the limit: options block → "CORE
   parked: 3 review rounds required changes (max-review-rounds is 3). The story and the
   options to relay: sae next <task>". The `sae dispatch` refusal while the task is parked: the
   whole story → "The task is parked at the round limit by REVIEW-INTEGRATION-2: only decision
   jobs are dispatched until the user chooses. The story and the options: sae next <task>".
4, 6. "Close anyway" stays for integration only. The job park and the job round do not get it.
   The spec's options do not list it, and it cannot pass: `sae finish --override` still waits
   for the final validation, which waits for the unmerged job (reproduced; see the defect
   finding). Every other exit is now the same for both. The repeated lead line "CORE: changes
   required. Triage first (execute.md, Loop step 3)." → "Triage the findings first
   (references/modes/execute.md, Loop step 3).", printed right after "REVIEW-CORE: done —
   verdict: changes-required". `sae next` prints "REVIEW-INTEGRATION requires changes." and
   then the same lines from the same builder (`changes_required_lines`), let-go included. That
   builder also adds "Or close anyway, on the user's word:" for integration. Before, it was
   appended in `reviews.py`, worded differently in `progress.py`, and worded a third way in
   the finish refusal.
5. "(execute.md, Loop step 3)", "(execute.md, Decision flow)", "(see execute.md)" and
   "Decision flow: …" → `references/modes/execute.md` with the section name
   (`fix_loop.EXECUTE_MD`).
7. The fix command's `--reason` is filled in everywhere ("REVIEW-CORE-3: changes required",
   computed by `fix_job_command`, now in `fix_loop.py`). This covers the park, `sae next`, the
   finish refusal and the `--fix-of` refusal in planning. Before, three of these printed
   `"<finding>"`. Every other `--reason` placeholder is `"<why>"`. `--override "<reason>"` and
   the let-go summary `"<number>: <reason>"` keep their form, the one execute.md uses.
8. argparse owns a missing `--reason` (`required=True` stays, as everywhere in `sae`). The
   custom check now fires only for an empty value, and says so. "--reason is required: …" →
   "--reason is empty: give the user's reason to drop the job." and "--reason is empty: sae
   accept-review <task> <ID> --reason "<why>"".
10. Final report: `## Reviews` leaves out the rounds of a dropped job. `## Jobs` leaves out a
   dropped job that never ran (for example `REVIEW-RIGHT-2 · dropped · not dispatched`).
   `## Dropped jobs` names them all. A dropped job that ran keeps its line, with its tokens.
11. One function, `findings.decision_inputs`, returns the objective and the (label, path)
   inputs. The job file lists them as `- <label>: <relative path>`, and the prompt as the same
   labels in the pointer column with absolute paths. Labels: "Job file of A", "Result of A",
   "Review round REVIEW-A — the findings", "Review round that parked A", "Decision request of
   P (section "Decision request")". The job file of a limit park now also lists the result.
12. Word: **user**. SKILL.md, the mode files, interaction-modes.md and the role files use "user"
   (about 90 times in the mode files, "owner" never). prompts.py has one "owner", in
   APPROACH_PARAGRAPH. Changed to "user": the park story heads, the drop and accept-review help,
   the close-anyway lines, the finish help and its `--override` error, the `sae job` group help,
   and the examples ("user: the cache approach is wrong; …").
14. Let-go on a review that numbers no finding. Before: "its review lists no numbered findings
   yet", with no way forward. After: the finding is named by its title, `sae log <task>
   decision "<finding>: <reason>" --job <REVIEW-ID> --let-go`. `sae collect` already prints that
   form for such a review, and the error names it too. The report lists "- REVIEW-X: <title> —
   let go: <reason>" once, and an acceptance does not list that finding again. A review without
   a verdict says: "REVIEW-X is running: it has no findings to let go yet. Log them after sae
   collect <task> REVIEW-X."

Left as the owner decided: 9 and 13.

## Decisions taken
- [agent] APPROACH_PARAGRAPH keeps "parks for the owner". The spec quotes it ([PROMPT-SAE]),
  and the brief and prompts.py say that only the prompt-text job rewords [PROMPT-SAE] constants.
  It is a one-word change once the owner says yes; it is in the follow-up finding.
- [agent] "One word" covers the fix-loop texts and their command help. The other "owner" texts
  in `sae` (holds, asks, harness fallback) are in the follow-up finding, not changed here.
- [agent] The "reduce the requirement" option puts its instruction in the choice label ("…:
  append an amendment under ## Amendments in specs.md, then log it"). Its command list now holds
  only the runnable `sae log … amendment` line. The JSON shape `{choice, commands}` stays.
- [agent] `fix_job_command` moved from `reviews.py` to `fix_loop.py`, next to the other
  fix-loop lines. This removes the late import in park_story.
- [agent] Fixed the plural "1 review rounds" in the park message and the story head.

## Disputed findings
- Issue 8 was only partly right. The custom message could be reached with an empty value
  (`--reason ""`), so it was not dead code, but its wording was wrong for that case. Fixed as
  described above, not removed.
- Issue 2: the story, options included, is printed by both `sae next` and `sae status`, because
  [PARK-STORY] requires both. "One place" here means one builder, and the other places point to
  it.

## Risks
- The decision-job prompt labels changed. Anything that matched "Decision request (section…)",
  "Job file of X: " or "Review round — the findings:" literally needs the new labels. Only the
  tests did, and they are updated.

## Findings filed
- .tasks/findings/2026-11-22-1936--finish-refusal-offers-a-close-anyway-tha.md
- .tasks/findings/2026-11-22-1936--owner-and-user-both-name-the-human-in-sa.md
