---
status: done
summary: Applied every "Prompt text" draft to the skill files, added the four PROMPT-SAE constants (unwired) to prompts.py, and listed the CLI and code contradictions
validation: pass
changes: made
resolved: [.tasks/findings/2026-11-20-1339--job-results-keep-empty-sections-such-as.md]
---

# Result: PROMPT-TEXT

## Validation evidence
- `python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers`: 71 tests OK.
- All six `grep` verify commands pass. Smoke `test_worktrees_review_verify_and_finish`: OK.
- Checklist: planner.md and shape.md name four difficulties, and nothing asks for a reason. Every setup cell has a tier and a model · effort. With tiers in cells on, Claude balanced execution resolves as before: mechanical L1 sonnet · medium, normal L3 opus · medium, hard L4 opus · high. Codex balanced execution: L1 terra · medium, L2 sol · medium, L3 sol · high, L4 sol · xhigh. The upgrade steps keep every cell's model · effort. The profile Stakes block matches [PROMPT-PROFILE] word for word. The review fields and result sections match the drafts.
- Commit 956113a on the job branch.

## Decisions taken
- [agent] execute.md says "ask the user" and does not name `sae ask`. The reason: [ASK-REMINDER] and `test_sae_ask.test_references_never_mention_sae_ask` keep that command out of SKILL.md and `references/`, and only the `sae next` reminder names it, when the ask signal is on. The spec says `sae` prints the fallback rule, so that printed rule can name `sae ask` (see Contradictions).
- [agent] shape.md research jobs: `--difficulty mechanical|easy|normal|hard` instead of the draft's `easy|normal|hard`. Research allows all four, and DIFF-GUIDANCE requires shape.md to name four difficulties.
- [agent] Codex seed list: terra is first (lightest), and the fallback chain is `terra → luna → sol → astra`. It is an assumption that terra is lighter than luna. luna stays in the list, but no seed cell uses it.
- [agent] Claude tiers are renumbered mechanically, as the job says. Some research and planning cells now show odd labels, for example `L3 · sonnet · high`. That is the old `L2 · sonnet · high` relabelled, and it runs opus · medium in tier mode, as the old L2 did.
- [agent] Codex planning and review cells take the tier with the nearest model · effort. Pairs sol · low map to L2 (sol · medium), and sol · max maps to L4.
- [agent] To fix contradictions inside prompt files, I made small edits that no draft names (listed below as "contradiction fix").

## Changes for the owner
- `references/roles/planner.md`: the stakes care rule, the shared interface or rule owner (walking skeleton), and four difficulties with one line each. [PROMPT-PLANNER], SHARED-RULE-OWNER, DIFF-GUIDANCE.
- `references/roles/reviewer.md`: Output uses the template fields, plus stakes grading, `[beyond stakes]`, the safeguard check and judging an Approach proposal. [PROMPT-REVIEW], FINDING-SHAPE, STAKES-GRADING, FIX-WORKER.
- `templates/review.md`: Breaks, Expected/Actual, Also in and Suggested fix replace Affects, Why it matters and Correction; Notes gets a comment. [PROMPT-REVIEW].
- `references/roles/worker.md`: fix workers make `Expected` true in every `Also in` place, and the suggested fix is a proposal; a new Approach proposal bullet; "Leave out sections that do not apply". The result list now names the approach proposal (contradiction fix). [PROMPT-WORKER], FIX-WORKER, RESULT-SECTIONS.
- `templates/job-result.md`: "Delete when it does not apply." on the four optional sections, and a new `## Approach proposal`. [PROMPT-WORKER], RESULT-SECTIONS.
- `references/modes/execute.md`: Loop step 2 holds the COMMAND for any job and the fallback rule by mode (`sae job park`, ask, the yes runs it with `--resume`). Loop step 3 holds triage, the `--let-go` log, the fix-job rules, `sae accept-review`, the park story and `sae job drop`. Decision flow step 2 covers decision jobs at any time, and step 6 resumes only a parked job. Finish step 2 adds accepting a round, and step 3 adds let-go findings, routing exceptions and dropped jobs. "A COMMAND job needs no --tokens" (contradiction fix). [PROMPT-EXECUTE], TRIAGE, HARNESS-FALLBACK, DECISION-ANYTIME, JOB-DROP, LET-GO-REPORT.
- `references/modes/shape.md`: the stakes question in the first round, written to the profile that `sae status` names; four research difficulties; the COMMAND and fallback sentence for research dispatch (contradiction fix). [PROMPT-SHAPE], STAKES-ASK.
- `references/modes/plan.md`: the COMMAND and fallback sentence for the planner dispatch (contradiction fix; a planning job can now route to the other harness). HARNESS-FALLBACK.
- `references/modes/setup.md`: the guide names four difficulties; terra is a seed family; the new tier table; all tables relabelled, with `easy` columns in execution and research; Codex execution and research tables by the owner's table; planning and review at the nearest tier; upgrade steps for an existing config in step 1; "5. Harness permissions" as drafted. [PROMPT-SETUP], SETUP-PROPOSAL, TIERS-FOLLOW-DIFFICULTY, EASY-UPGRADE.
- `templates/repo/profile.md`: the new comment and the Stakes section with the agreed example and the "not set" line. [PROMPT-PROFILE], STAKES-TEMPLATE.
- `references/roles/decision-worker.md` and `templates/decision.md`: the question can be a parked job's request, a job, a review round or a question. DECISION-ANYTIME.
- `references/interaction-modes.md`: the full-auto safety net also lists findings let go and routing exceptions (contradiction fix). LET-GO-REPORT, HARNESS-FALLBACK.
- `templates/plan.md`: the Integration points comment names the job that builds a shared rule first (contradiction fix). SHARED-RULE-OWNER.
- `SKILL.md`: the third scaling axis is now called **care**, because "stakes" now means the project's Stakes section, one term per meaning (contradiction fix).
- `scripts/sae_lib/prompts.py`: `STAKES_LINE`, `STAKES_NOT_SET_LINE`, `APPROACH_PROPOSAL_POINTER` and `APPROACH_PARAGRAPH` (placeholders `{path}`, `{result}`, `{fix}`, `{target}`, `{max_rounds}`). Nothing calls them yet. [PROMPT-SAE].

## Contradictions
- `sae --help` (cli list): "decision  Create a decision job for a parked job." Also `sae decision new --help`: "Add DECISION-<ID>-<n> for a parked job", `--from ID  the parked job whose decision request this answers`, and no `--question`. This conflicts with DECISION-ANYTIME and execute.md Decision flow step 2.
- `prompts.py` `build_prompt`, decision branch: it always points to `Decision request (section "Decision request")` of the target's result. For a review round or a non-parked job, that pointer is wrong (DECISION-ANYTIME).
- `common.py:40` `DIFFICULTIES = ("mechanical", "normal", "hard")`. Also `cli.py:94`: "mechanical | normal | hard". Also `sae job add --help` and `sae decision new --help` show `{mechanical,normal,hard}`. And `planning.py:214,265,430`: "never mechanical: use normal or hard", which should also refuse `easy` for planning and review. This conflicts with DIFF-EASY, planner.md and setup.md.
- `sae dispatch --help`: "For a review in the other harness it prints COMMAND … and an IF IT FAILS line (run it when the command exits non-zero…)". This now covers every job, and the IF IT FAILS line for a non-review job runs only in `full-auto` (WRITER-COMMAND, HARNESS-FALLBACK, execute.md step 2).
- `sae job --help`: lists only `add|edit|remove|override`. execute.md names `sae job park` and `sae job drop`.
- `sae log --help`: has no `--let-go`. execute.md step 3 uses `sae log … decision "<finding>: <reason>" --job <REVIEW-ID> --let-go`.
- `sae --help` has no `accept-review` command. execute.md step 3 and Finish step 2 use `sae accept-review <task> <REVIEW-ID> --reason`.
- `sae finish --help`: "no last review round (integration …) says changes-required … --override passes the verdict". This needs the exception for an integration round accepted with `sae accept-review` (ACCEPT-INTEGRATION).
- The fallback rule that `sae` prints with the fallback command (HARNESS-FALLBACK) should name `sae ask <task> "<question>" --job <ID>` for the non-full-auto case. execute.md cannot name it ([ASK-REMINDER] test), and the `sae next` ask reminder appears only when the ask signal is on.
- `reviews.py` collect (around line 575) reports disputed findings, but says nothing when a result has an `## Approach proposal`. execute.md Decision flow lists "a worker's Approach proposal" as a typical decision-job case, so the orchestrator gets no signal unless it reads the result (FIX-WORKER, DECISION-ANYTIME).
- The `APPROACH_PARAGRAPH` text (approved wording) says "The job parks for the owner after review round {max_rounds}". For an integration fix, the task parks, not a job. I kept the approved wording; the caller may pass a target name that makes this clear.

## Risks
- The terra rank and the seed efforts (low…max) are assumptions; the catalog filter in setup corrects the efforts.
