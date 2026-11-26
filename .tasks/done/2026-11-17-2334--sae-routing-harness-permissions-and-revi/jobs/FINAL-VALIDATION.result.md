---
status: done
summary: Full suite green (470 tests, 3 skipped); every acceptance item of all 27 requirements passes on the integrated branch, 3 judged against AMEND-3.
validation: pass
changes: none
resolved: []
---

# Result: FINAL-VALIDATION

## Validation evidence

**Suite:**
- `python3 tests/run.py` ran 470 tests in 485 s with 10 workers: `OK (skipped=3)`, exit 0.
- Smoke `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish` ran 1 test: OK.

**Method:**
- Each acceptance item was checked by its covering test, and additionally by a CLI walk in scratch repositories. The walks used `tests/saetest.Sandbox`, with `SAE_CONFIG`, `CODEX_HOME` and `SAE_STATE_DIR` redirected and fake `codex` and `claude` on PATH. The real config and the workdir were not touched.
- Prompt text was judged by reading.
- Paths are relative to `skills/shape-and-execute/`.

### Difficulty and routing
- **[DIFF-EASY]**
  - PASS: `job add --difficulty easy` works for research and implementation. Planning gets "Planning takes --difficulty normal or hard, not easy." (`test_easy_is_accepted_for_execution_and_research_and_refused_for_planning_and_review`).
  - PASS: `job edit --difficulty easy` on a pending REVIEW-INTEGRATION gets "Review takes --difficulty normal or hard, not easy.". A job review gets "takes the difficulty of <target>".
    - REVIEW-SPEC and REVIEW-PLAN are created already running, so `job edit` refuses them on status first.
    - `job add` has no `--kind review`, because sae adds reviews itself.
  - PASS: a review of an `easy` job routes through the review table's `normal` cell (`test_a_review_of_an_easy_job_routes_through_the_review_normal_cell`).
  - PASS: the `easy` column is shown and accepted in execution and research only. This holds for `sae set` and `project set` (other phases are refused), for `setup show` and for the viewer (`test_a_three_column_config_saves_and_an_easy_column_only_where_allowed`, `test_the_routing_panel_shows_the_easy_column_and_its_fallback`).
  - PASS: help texts and errors name four difficulties. `common.py` `DIFFICULTIES` is the one source. `job add --help` shows `{mechanical,easy,normal,hard}`. A grep finds no three-value list left.
- **[EASY-UPGRADE]**
  - PASS: without any `easy` cell, the card shows "mechanical cell" and "(no easy cell: uses the mechanical cell; fix: setup mode)" (`test_without_easy_cells_an_easy_job_uses_the_mechanical_cell_named_on_the_card`, `test_the_fallback_is_the_effective_mechanical_cell`). Status, doctor and the viewer give one line with the fix (`test_status_doctor_and_setup_show_say_when_easy_falls_back`). This task's own `sae status` shows that line.
  - PASS: a global `easy` cell wins over a task-level `mechanical` override (`test_a_global_easy_cell_wins_over_a_task_level_mechanical_override`).
  - PASS, judged against [AMEND-3] points 1–2: setup proposes the `easy` column as tier-only cells. Their tiers resolve to the spec's pairs, with Codex L1 as terra · high per AMEND-3.1. The proposal saves with `sae setup save`.
    - "A family the configuration does not list falls back to the `mechanical` cell" is superseded: cells now carry no pair.
    - At runtime, a config without easy cells still falls back to mechanical.
  - PASS: with tiers on, an `easy` cell `L2 · opus · low` dispatches as sonnet · high · L2. With tiers off, it dispatches as opus · low (`test_tiers_on_and_off`).
- **[TIERS-FOLLOW-DIFFICULTY]**
  - PASS (tier-only per AMEND-3): every proposal cell has a tier, and every tier has a model · effort. The scratch walk matched 72/72 cells and 8/8 tiers against `prototypes/setup-routing-owner.json` (`SetupProposalTest.test_every_cell_is_a_tier_only`).
  - PASS: in Tiers mode, Claude balanced mechanical/normal/hard resolve to sonnet·medium, opus·medium and opus·high, the same as the merge-base proposal (3892f20).
  - Job scope: the proposal was saved, then research and implementation jobs of every difficulty were dispatched at every level under both orchestrators. Tiers on: 24/24 claude and 24/24 codex routes match. Tiers off, after the Free-mode copy: also 24/24 and 24/24.
  - Codex balanced `normal` and `hard` differ: sol · high · L3 against sol · xhigh · L4.
- **[SETUP-PROPOSAL]**
  - PASS (per AMEND-3): `setup.md` holds the new tier table and the `easy` column between `mechanical` and `normal`. The cells equal the owner's JSON.
  - The "2. Guide" block is byte-identical to `prototypes/setup-guide.md` and names four difficulties.
  - "No other cell changes its model · effort" is superseded by tier-only cells.
  - Upgrade of a three-column config (step "1. Look", AMEND-3.5), both modes:
    - every existing cell keeps its model · effort in the saved file;
    - in Free mode every non-`easy` route is unchanged;
    - in Tiers mode the routes follow the new tiers.
- **[DIFF-GUIDANCE]**
  - PASS: `references/roles/planner.md:41-44` has one line per difficulty. `references/modes/shape.md:46` has `--difficulty mechanical|easy|normal|hard`. No required reason and no CLI check.

### Harness launches and fallback
- **[WRITER-COMMAND]**
  - PASS: under a Claude orchestrator, a Codex-routed implementation job prints `codex exec -m … -c model_reasoning_effort=… --dangerously-bypass-approvals-and-sandbox -C <workdir> --ephemeral --json`, with no `-s`. The fake received the job worktree (`test_codex_writer_under_claude_runs_without_sandbox_and_records_tokens`).
  - PASS: under a Codex orchestrator, the job prints `cd <workdir> && … claude -p … --output-format json --model … --effort … --permission-mode bypassPermissions`. The fake's cwd was the workspace (`test_claude_writer_under_codex_runs_in_the_workdir_with_bypass`).
  - PASS: `sae collect` recorded tokens without `--tokens`: 2100 for codex and 7310 for claude in the scratch run.
  - PASS: review COMMANDs are rebuilt with main's formula and match byte for byte, apart from the stakes block in the prompt (`test_review_command_is_unchanged_and_records_a_read_only_request`).
- **[LAUNCH-RECORD]**
  - PASS: `attempts[n].launch` stores the harness, model, effort, the command with `<prompt>`/`<workdir>`/`<output>` placeholders, and `"bypass requested"` (a review stores `"read-only requested"`) (`test_attempt_records_the_placeholder_command_and_the_request`).
  - PASS: the viewer job view's "Launch commands" section shows the request with "requested" (`assets/viewer/task-views.js:708-712`, `test_command_attempt_shows_its_launch_and_the_card_marks_the_exception`).
- **[NO-SANDBOX-VISIBLE]**
  - PASS: `sae status` prints "Bypass: jobs on the other harness start with a bypass request (no sandbox, no approvals): <jobs>". The line is absent when no writer leaves the orchestrator. The viewer settings card shows the same (`settings.js` `sxBypass`, `test_status_shows_one_bypass_line_for_a_job_sent_to_the_other_harness`).
- **[HARNESS-FALLBACK]**
  - PASS: with the CLI missing, the dispatch exits 1 with "Nothing was dispatched and nothing changed". `state.json` and `events.jsonl` are byte-identical before and after.
  - The printed fallback ran for a pending job: park, then `sae ask`, then the yes with `--resume` ran on claude. It also ran for a due plan review (`--provider claude`).
  - Tests: `test_missing_cli_refuses_before_any_change_for_a_pending_job`, `test_missing_cli_branch_*`.
  - PASS: after a failed fake COMMAND, the IF IT FAILS line resumed the running job on claude, and it collected and merged (`test_if_it_fails_branches_for_a_running_job`, `test_review_if_it_fails_branch`).
  - PASS: the attempt stores `routing_exception {requested, actual, reason}`. The viewer card shows "⇄ routing exception", and the final report has "## Routing exceptions". The next dispatch uses routing again (`test_override_route_returns_after_the_fallback_and_the_final_report_lists_it`).

### Project Stakes (with AMEND-1, AMEND-2)
- **[STAKES-LOOKUP]**
  - PASS: the lookup order is profile → AGENTS.md → CLAUDE.md, and the first section with content wins. Empty labels are skipped. The old `## Stakes` heading is not read (`test_sources_are_read_in_order_and_the_first_with_content_wins`, `test_there_is_no_fallback_to_the_old_section_name`).
  - PASS: a task worktree and a linked worktree read the main worktree's profile. A planted stale copy is ignored.
  - PASS: a viewer save (`POST /api/stakes`, 200) during execution reached the next dispatch prompt (`test_a_task_worktree_reads_and_names_the_home_profile`).
  - PASS (for stakes): no write site in `scripts/` targets AGENTS.md or CLAUDE.md. The viewer refuses with 409 when stakes come from them (`test_the_writer_never_touches_agents_or_claude_md`). See the Risks section for two older instructions.
- **[STAKES-TEMPLATE]**
  - PASS: the template's example (`templates/repo/profile.md:14-19`) equals the viewer help (`assets/viewer/settings.js:65`) word for word (`test_the_help_shows_the_template_example_word_for_word`).
- **[STAKES-ASK]**
  - PASS: `references/modes/shape.md:29-30` holds the step. It points to the question that `sae status` prints, which asks for a draft from AGENTS.md/CLAUDE.md and the README.
  - PASS: after a skip, `sae status` names the profile and prints no question. Without a source, it prints the question (`test_the_not_set_line_and_prose_are_content`, `test_status_without_a_task_prints_the_question_only_while_stakes_are_not_set`).
- **[STAKES-POINTER]**
  - PASS (per AMEND-1, "one block"): exactly one block appears in each prompt kind: planner, research, decision, worker, reviewer and review COMMAND (`test_every_prompt_kind_carries_exactly_one_stakes_block`, `test_the_planner_prompt_carries_one_stakes_block`).
  - A section over 15 lines is named, not pasted. Without stakes, the not-set text says what Project Stakes are.
- **[STAKES-VIEWER]**
  - PASS: "Project settings" sits above "Defaults for new tasks in".
  - An HTTP save changed only the Project Stakes section: the bytes before it and the `## Hot files` tail are unchanged. AGENTS.md stakes are read-only (`test_the_writer_replaces_only_the_section_and_keeps_the_help_comment`, `test_refusals_leave_every_file_as_it_was`).
  - The help matches the template example.
- **[AMEND-2]**
  - PASS: `grep -rnE '## Stakes|section "Stakes"|\[beyond stakes\]' skills tests` hits only:
    - the retired-terms list (`tests/test_retired_terms.py:59-61`) and its self-test;
    - one `assertNotIn` (`tests/test_viewer_surfaces.py:264`).
  - Prompts, `sae status` ("Project Stakes: <path>") and the viewer use "Project Stakes".

### Reviews and fix rounds
- **[FINDING-SHAPE]**
  - PASS: `templates/review.md:10-15` and `references/roles/reviewer.md:59-63` use Evidence, Breaks, Expected/Actual, Also in and Suggested fix. Affects, Why it matters and Correction are gone.
- **[STAKES-GRADING]**
  - PASS: `reviewer.md:65-69` covers grading, "never drop it", `[beyond Project Stakes]` with one sentence why, the safeguard check and judging an Approach proposal.
- **[TRIAGE]**
  - PASS: `references/modes/execute.md:53-65` holds the triage step.
  - PASS: the scenario with one real failure and one speculative safeguard works. The fix names only the first. After `sae log … --let-go 2 --reason …`, finish lists "## Findings let go: … Lock for a nearly impossible race — let go: beyond the Project Stakes" (`LetGoReportTests.test_triage_scenario_one_fix_one_finding_let_go`, plus a scratch walk).
- **[ACCEPT-INTEGRATION]**
  - PASS: `sae accept-review <task> REVIEW-INTEGRATION --reason …` works. Before it, FINAL was refused. After it, FINAL is ready and `finish` succeeds without `--override` (no "Overridden gates").
  - PASS: the report has "## Accepted integration rounds" and each finding under "Findings let go" (`AcceptIntegrationTests`).
- **[LET-GO-REPORT]**
  - PASS: `sae finish` lists the findings from logged decisions. `execute.md:151` names them in Finish step 3 (`test_accepted_job_review_lists_each_finding_once`, 7 `test_let_go_*`).
- **[FIX-WORKER]**
  - PASS: `references/roles/worker.md:27-35` and `templates/job-result.md:26-28` hold the rules and the section.
  - PASS: the next round's prompt reads `Read first: the "Approach proposal" in …/CORE-FIX-2.result.md` (`ApproachProposalTests`). `reviewer.md:68-69` says to judge it.
- **[APPROACH-CHECK]**
  - PASS: with N = 3, the fix of round 1 has no paragraph and the fix of round 2 has "FIX 2 of CORE. CORE parks for the user after review round 3. …". With N = 1, every fix has it (`test_three_rounds_paragraph_story_and_raised_limit`, `test_one_round_every_fix_gets_the_paragraph`).
- **[PARK-STORY]**
  - PASS: `sae next` and `sae status` print the same story: target, rounds against the limit, objective, first result summary, then per round the findings with suggested fixes, the "do not" limits with "because" and the fix summaries, then the options.
  - PASS: `scripts/sae_lib/park_story.py` reads only result summaries, finding titles, suggested fixes, objectives and limits. It reads no transcripts.
- **[DECISION-ANYTIME]**
  - PASS: `decision new --question` creates DECISION-1 with a `## Question`, and `--from REVIEW-INTEGRATION` points to `reviews/REVIEW-INTEGRATION.md`.
  - PASS: `--from <parked job>` points to its Decision request.
  - PASS: a decision job was dispatched and collected while the round limit parked the task (`test_decision_job_runs_while_the_round_limit_parks_the_task`).
- **[JOB-DROP]**
  - PASS: after the drop, REVIEW-INTEGRATION and then FINAL became ready. Finish lists "## Dropped jobs", and branches and results stay (`test_drop_then_the_integration_review_and_final_validation_run`).
  - PASS: a drop of a needed job is refused with the `sae job edit … --needs "LEFT" --reason …` command. State is byte-identical.
  - PASS: in a task without worktrees, the drop is refused before any change (`test_refused_without_worktrees_before_any_change`).
  - PASS: `execute.md:54-55` says "only on the user's word".
- **[RESULT-SECTIONS]**
  - PASS: PROMPT-TEXT resolved the finding (`finding.closed`, job PROMPT-TEXT). The template marks every optional section "Delete when it does not apply". `worker.md` says "Leave out sections that do not apply."
- **[PROMPT-JOB]**
  - PASS: the plan has one prompt job with a hold after it (`hold.set PROMPT-TEXT` in events).
  - PASS: `jobs/PROMPT-TEXT.result.md` "Contradictions" lists 11 items. The CLI-help items are resolved: `accept-review`, `decision new --question/--from`, `job park|drop`, `log --let-go`.
- **[SHARED-RULE-OWNER]**
  - PASS: `references/roles/planner.md:31-34` holds the approved text. The old contract-job line is gone.

### Job-scope checks
- **Prompt text limited to the allowed sources: PASS.**
  - Every hunk of `SKILL.md`, `references/**`, `templates/**` and the `prompts.py` constants since 3892f20 traces to one of:
    - the spec drafts;
    - the PROMPT-TEXT contradiction fixes;
    - PROMPT-LEAN proposals 1–9;
    - PROMPT-STAKES;
    - AMEND-1–4.
  - Text from owner-directed or review-fix jobs is documented in their job files and results:
    - INTEGRATION-FIX-4/5/6: the setup layout sentence, the GUI note, the stakes question pointer and the Free-mode `easy` rule;
    - WRITER-LAUNCH-FIX-3: the `EARLIER_RESULT_POINTER`;
    - the STAKES-IN-PROMPTS `STAKES_LONG_SUFFIX`;
    - the structural pointer labels from the FIX-LOOP jobs.
  - No hunk is unattributed.
- **PROMPT-LEAN cut rules (audit proposals 1–3): PASS.** `sae` prints each one:
  1. the fallback rule per mode, on a missing CLI;
  2. the changes-required triage, fix, let-go and accept lines, and the round-limit park opening, in collect, next and status;
  3. the collect line "Approach proposal in …: read that section; it is a decision".
- **Invariants: PASS.**
  - Model names in `sae` code: the only hit is `setup_mode.py` `CLAUDE_FAMILIES`, which predates the task and is a documented exception.
  - Read-only commands write nothing: 12 commands, each run alone, changed no file under the repo, task, config or state (`test_status_writes_nothing`).
  - Private paths: launch records use only placeholders. The absolute paths in `task.worktree`/`task.home`, `task.started` and `job.dispatched.workspace` are older than this task, and finish rewrites them to `~` (`test_record_privacy`).

## Decisions taken
- [agent] Three acceptance texts are judged against [AMEND-3], which replaced them:
  - the [EASY-UPGRADE] missing-family fallback;
  - [TIERS-FOLLOW-DIFFICULTY] "a tier and a model · effort" per cell;
  - [SETUP-PROPOSAL] "no other cell changes its model · effort".

  Cells now carry only a tier. Each check was against the amended rule.
- [agent] [DIFF-EASY] "refused for review jobs" was checked through `sae job edit`. `sae job add` takes no review kind, and spec and plan reviews never sit pending.

## Risks
- The brief invariant "no SaE instruction writes to AGENTS.md or CLAUDE.md" holds for stakes, but two older instructions, unchanged by this task, still have an agent write AGENTS.md:
  - `references/modes/triage-decisions.md:19-22` adds an ADR pointer line after the user approves;
  - `references/modes/plan.md:70` puts one-directory knowledge in that directory's `AGENTS.md`.

  Read literally, the invariant covers them. The orchestrator decides whether it does.

## Findings filed
- `.tasks/findings/2026-11-26-1319--sae-job-edit-help-describes-no-review-as.md`: the `--no-review` help says "flag the job for review". This predates the task.
