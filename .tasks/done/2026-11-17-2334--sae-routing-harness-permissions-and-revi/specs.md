# Spec: SaE routing, harness launches and review workflow

## Summary

Routing gains a fourth difficulty, `easy`, for simple work that needs local judgment. Writer
jobs routed to the other harness get a launch command from `sae`, run without a sandbox for now,
and a harness that cannot run a job has a visible default per interaction mode. Projects get a
short Stakes section that every agent reads; reviewers grade findings against it, and findings
get a fixed shape that separates what must become true from how. Fix loops get an explicit
approach check before the round limit, a plain story at the limit, decision jobs without a
parked job, and a way to drop a job. The planner gives a shared interface or business rule one
owner.

## Domain language

**Stakes** — the project's `## Stakes` section: who uses it and why, acceptable breakage, what
matters now, what not to build, and what to build it like. It sets the level of care.
_Avoid:_ risk level, criticality.

**Beyond stakes** — a finding that needs more care than the stakes justify. It is reported in
Notes and does not block.

**Fix round** — one changes-required review round of a target (a job or the integration) and
the fix jobs that answer it. `max-review-rounds` (N) limits the rounds.

**Approach proposal** — a fix worker's description of a different approach that would stop the
same kind of finding from coming back.

**Routing exception** — a dispatch on another harness than routing chose, with the requested
route, the actual route and the reason.

**Dropped job** — a writer job that the owner decided must never merge.

## Scope

### In scope
- The `easy` difficulty in routing, setup, the viewer and the planner guidance.
- A launch command for writer jobs in the other harness; its record; the fallback per mode.
- Stakes: location, template, the first-round question, dispatch pointers, the viewer section.
- Review findings, triage, fix rounds, the park story, decision jobs, `sae job drop`.
- Job results without empty sections (finding
  [Job results keep empty sections](../findings/2026-11-20-1339--job-results-keep-empty-sections-such-as.md)).
- One planner rule for shared interfaces and business rules.

### Out of scope
- A sandboxed writer launch, a capability probe and applying permission settings from the
  viewer: backlog item
  [Sandboxed writer launches](../backlog/2026-11-20-1159--sandboxed-writer-launches-for-cross-harn.md).
- A separate risk setting per task: backlog item
  [Risk and review](../backlog/tier-1/2026-10-30-1311--consider-risk-independently-of-difficult.md).
- Moving or rewriting a project's existing AGENTS.md content; a "Hard rules" section.
- Tier-based tables for existing configurations.

## Requirements

### Difficulty and routing

### [DIFF-EASY] Four difficulties
Difficulties are `mechanical`, `easy`, `normal` and `hard`. Execution and research allow all
four. Planning and review allow `normal` and `hard`; `task_difficulty` stays `normal | hard`.
A review of a `mechanical` or `easy` job routes through the review table's `normal` cell.
`L1`–`L4` stay the names of model tiers, and the tiers follow the difficulties: L1 mechanical,
L2 easy, L3 normal, L4 hard ([TIERS-FOLLOW-DIFFICULTY]).

Acceptance:
- [ ] `sae job add --difficulty easy` works for research and implementation jobs and is refused
      for planning and review jobs, with a message that names the allowed values.
- [ ] Routing, `sae set routing.<h>.<phase>.<level>.easy=…`, `sae setup show` and the viewer
      tables show and accept the `easy` column for execution and research only.
- [ ] Help texts and error messages name four difficulties where they named three.

### [EASY-UPGRADE] An older configuration gains the easy column
Configuration layers (global, project, task) are partial; the nearest layer that sets a cell
wins, as today. When no layer sets an `easy` cell for a table, `easy` resolves to the effective
`mechanical` cell, and `sae status`, `sae doctor` and the viewer say so in one line with the fix:
setup mode. Setup mode proposes, and saves after the owner's yes, the tiers of
[TIERS-FOLLOW-DIFFICULTY] for the owner's own tiers and the `easy` column. `sae` itself changes
no cell and no tier. See [DECISION-EASY-UPGRADE].

Acceptance:
- [ ] Without any `easy` cell, an `easy` job dispatches on the effective `mechanical` cell, and
      the card names that source.
- [ ] With a global `easy` cell and a task-level `mechanical` override, an `easy` job uses the
      global `easy` cell.
- [ ] Setup mode proposes the `easy` column with these model · effort values, each cell with
      its tier, and saves it after the owner's yes:

      | `easy` | economy | balanced | premium |
      | --- | --- | --- | --- |
      | Claude | L1 · sonnet · medium | L2 · sonnet · high | L3 · opus · medium |
      | Codex | L1 · terra · medium | L2 · sol · medium | L3 · sol · high |

      A family the configuration does not list falls back to the `mechanical` cell.
- [ ] With tiers in cells on, an `easy` job dispatches on its cell's tier; off, on the cell's
      model · effort.

### [TIERS-FOLLOW-DIFFICULTY] Tiers follow the difficulties
The four tiers match the four difficulties at the balanced level. The setup proposal's tiers:

| tier | difficulty | Claude | Codex |
| --- | --- | --- | --- |
| L1 | mechanical | sonnet · medium | terra · medium |
| L2 | easy | sonnet · high | sol · medium |
| L3 | normal | opus · medium | sol · high |
| L4 | hard | opus · high | sol · xhigh |

For Claude this inserts sonnet · high as L2 and renumbers the old L2 and L3 to L3 and L4, so the
balanced `normal` and `hard` routes do not change. The old L4 (opus · xhigh) has no tier of its
own: its cells take L4 and keep opus · xhigh as their model · effort. With tiers in cells on,
they use opus · high. For Codex the tiers follow the owner's table, which routes `normal` and
`hard` one step higher than the old proposal. In tier mode every cell has a tier; the viewer
allows nothing else. Setup mode proposes the same renumbering for an existing configuration.

Acceptance:
- [ ] Every cell of the setup proposal has a tier and a model · effort.
- [ ] With tiers in cells on, Claude balanced `mechanical`, `normal` and `hard` resolve to the
      same model · effort as before the change.

### [SETUP-PROPOSAL] Setup proposal for new installations
The setup proposal uses the tiers of [TIERS-FOLLOW-DIFFICULTY] and inserts the `easy` column
between `mechanical` and `normal` in the execution and research tables, with the cells of
[EASY-UPGRADE]. Every other cell keeps its model · effort; its tier label follows the
renumbering. The setup guide names four difficulties.

Acceptance:
- [ ] `references/modes/setup.md` holds the new tier table, and the execution and research
      tables with the `easy` column; no other cell changes its model · effort.

### [DIFF-GUIDANCE] Classification guidance
The planner guidance describes the four difficulties in one short line each and leaves the
choice to the model. No required reasons, no CLI checks. Text: [PROMPT-PLANNER].

Acceptance:
- [ ] `planner.md` and `shape.md` name four difficulties; nothing requires a reason for a
      difficulty.

### Harness launches and fallback

### [WRITER-COMMAND] Launch command for writer jobs in the other harness
When a job other than a review (implementation, integration, validation, research, decision)
routes to the harness that does not orchestrate, `sae dispatch` prints a COMMAND and an IF IT FAILS line, as
for reviews. The command runs without a sandbox: Codex
`--dangerously-bypass-approvals-and-sandbox`, Claude Code `--permission-mode bypassPermissions`.
It starts in the job's workdir, sets the routed model and effort, and keeps the harness's
machine-readable output so that `sae collect` reads the tokens, as for review COMMANDs. Review
COMMANDs are unchanged.

Acceptance:
- [ ] A Codex-routed implementation job under a Claude orchestrator prints a `codex exec`
      COMMAND with the bypass flag, `-C <workdir>`, the model and effort, and no `-s`.
- [ ] A Claude-routed job under a Codex orchestrator prints a `claude -p` COMMAND with
      `--permission-mode bypassPermissions`, run in the workdir.
- [ ] `sae collect` records the tokens of such a job without `--tokens`.
- [ ] Review COMMANDs are unchanged.

### [LAUNCH-RECORD] The attempt records the launch
Each attempt of a job started by a COMMAND records the launch: harness, model, effort, the
command with the prompt and absolute paths replaced by placeholders (`<prompt>`, `<workdir>`),
and what the command requested (`bypass requested` or `read-only requested`). The record states
the request, not the effective permissions: the launch environment can still restrict a job, and
Codex reports no effective sandbox. Task records hold no private paths.

Acceptance:
- [ ] `state.json` holds the placeholder command and the request for each COMMAND attempt.
- [ ] The viewer's job view shows them with the word "requested".

### [NO-SANDBOX-VISIBLE] Writers without a sandbox are visible
`sae status` and the viewer say that jobs in the other harness start with a bypass request.

Acceptance:
- [ ] The settings card or the status shows one line when a task routes any writer job to the
      other harness.

### [HARNESS-FALLBACK] Default when a harness cannot run a job
Before it prints a COMMAND, `sae dispatch` checks that the other harness's CLI is on the PATH.
When it is not, it refuses before any state changes, and prints the fallback command that works
for a job that has not started (a dispatch on the orchestrator's harness, without `--resume`).
When a started COMMAND fails, the IF IT FAILS line resumes the job on the orchestrator's harness.
`sae` prints the rule with both, so it holds in every phase:
- a review falls back in every mode (unchanged);
- any other job falls back only in `full-auto`; in the other modes it stays where it is,
  independent work continues, and the orchestrator asks the owner (`sae ask`, so the wait is
  visible); the owner's yes runs the fallback command.

Every fallback dispatch is a routing exception. A running job finishes on the harness it runs on;
the next dispatch uses routing again.

Acceptance:
- [ ] A missing CLI refuses the dispatch before any state changes and prints a fallback command
      that works for a pending job and for a due spec or plan review.
- [ ] A failed COMMAND's IF IT FAILS line works for the running job.
- [ ] A fallback attempt records the requested route, the actual route and the reason; the
      viewer marks the job with the exception; the final report lists it.

### Stakes

### [STAKES-LOOKUP] Where stakes live
`sae` reads the stakes from the `## Stakes` section of `.tasks/repo/profile.md` in the home
checkout, the copy that the viewer edits, also while a task executes in its worktree. When that
section is missing or its five lines are empty, it reads a `## Stakes` section of the
repository's AGENTS.md, then CLAUDE.md. SaE writes stakes only to the profile, never to AGENTS.md
or CLAUDE.md. `sae status` names the source, or says `not set`.

Acceptance:
- [ ] The sources are read in that order; the first section with content wins.
- [ ] A viewer edit during execution reaches the next dispatch.
- [ ] No `sae` command and no SaE instruction writes to AGENTS.md or CLAUDE.md.

### [STAKES-TEMPLATE] Template with one agreed example
`templates/repo/profile.md` holds the Stakes section with five bullet lines, one agreed example
and the "not set" line ([PROMPT-PROFILE]). Agents that draft stakes use it.

Acceptance:
- [ ] The template and the viewer help show the same example.

### [STAKES-ASK] Shaping asks once per repository
When `sae status` shows `stakes: not set`, the first grill round of a task adds one question with
a draft of the section, based on AGENTS.md (or CLAUDE.md) and the README. The owner's answer is
written to the profile. When the owner skips, the profile gets the "not set" line, and shaping
does not ask again in that repository.

Acceptance:
- [ ] `shape.md` holds the step ([PROMPT-SHAPE]).
- [ ] After a skip, `sae status` names the profile as the source, and the next task asks
      nothing.

### [STAKES-POINTER] Every role gets the stakes
Every dispatch prompt (planner, research, decision, worker, reviewer, also a review COMMAND)
names the stakes source (in the home checkout) and section. Without stakes it prints the "not set" instruction instead.
Text: [PROMPT-SAE].

Acceptance:
- [ ] Each prompt kind carries exactly one stakes line.

### [STAKES-VIEWER] Project settings in the viewer
The viewer's Project tab gets a new first section, "Project settings", above "Defaults for new
tasks in <repo>". It shows the stakes with their source. Stakes from the profile are editable
there and saved to the profile's Stakes section after the owner saves; stakes from AGENTS.md or
CLAUDE.md are shown read-only with "edit there". A "?" opens a help text that explains the
topic: what stakes are, how SaE uses them (reviewers grade findings and report `[beyond stakes]`
notes; planners and workers size their work), the example, and that hard limits do not belong
there.

Acceptance:
- [ ] Editing changes only the Stakes section of the profile.
- [ ] The help text and the template example match.

### Reviews and fix rounds

### [FINDING-SHAPE] Findings separate the outcome from the method
Every review finding (spec, plan, job and integration reviews) has: severity, evidence, what it
breaks and how (a requirement, the intent or a stakes line), expected and actual behavior, other
places that apply the same rule (only when the reviewer found them by search), and a suggested
fix. The suggested fix is a proposal and may be a change of approach. Text: [PROMPT-REVIEW].

Acceptance:
- [ ] `templates/review.md` and `reviewer.md` use these fields; "Affects", "Why it matters"
      and "Correction" are gone.

### [STAKES-GRADING] Reviewers grade against the stakes
The reviewer reports everything it finds. The stakes decide only whether a finding blocks. A
finding that needs more care than the stakes justify goes to Notes as `[beyond stakes]` with
one sentence why. When a change adds a safeguard, the reviewer checks what new failure it can cause in normal use.

Acceptance:
- [ ] `reviewer.md` holds these rules ([PROMPT-REVIEW]).

### [TRIAGE] The orchestrator triages before fix jobs
Before it adds fix jobs, the orchestrator applies the same bar to every changes-required finding.
Each finding it sets aside is logged with its reason (`sae log … decision`), so the final report
can list it. One review round gets one fix job by default: the reviewed work was one job, so one
fix fits its scope. The orchestrator splits a round only when its findings touch unrelated parts
and one job would not fit one context. A fix job names the findings it must fix and their
expected behavior, with every place listed under `Also in`; it does not limit the worker to
single instances. The orchestrator may set any limit, but each "do not" in a fix job gives its
reason ("because …"), also when it rules out a fix that a review proposed.

Acceptance:
- [ ] `execute.md` holds the triage step.
- [ ] With a review that holds one real failure and one speculative safeguard, the fix job names
      only the first, and the final report lists the second with its reason.

### [ACCEPT-INTEGRATION] An integration round can be accepted
The orchestrator can accept a changes-required integration round with a reason, under the same
mode rules as `sae merge --accept-review`. The task then continues as after a pass. The decision
is logged.

Acceptance:
- [ ] A `sae` command accepts the last integration round with a reason; the integration gate,
      the final validation and `sae finish` then proceed without `--override`.
- [ ] The acceptance appears in the final report.

### [LET-GO-REPORT] The owner sees what was let go
At the hand-over for merge, the final report lists every finding the orchestrator let go
(`[beyond stakes]` triage, accepted job reviews, accepted integration rounds) with its reason.

Acceptance:
- [ ] `sae finish` prints the list from logged decisions; `execute.md` "Finish" names it.

### [FIX-WORKER] Fix workers meet the expected behavior
A fix worker makes the expected behavior of each finding its job names true in every listed
place; findings of the review that the job does not name are not its work. It may use a
better way than the suggested fix and says why. It may still dispute a finding. When it sees a
different approach that would stop the same kind of finding from coming back, it finishes its
job anyway and writes an Approach proposal in its result. Text: [PROMPT-WORKER].

Acceptance:
- [ ] `worker.md` and `templates/job-result.md` hold the rules and the section.
- [ ] The next review round's prompt points to an Approach proposal when the fix result has
      one, and `reviewer.md` says to judge it.

### [APPROACH-CHECK] Explicit approach check from fix round N-1
A fix job that answers changes-required round k of its target, with k ≥ N − 1, gets the approach
paragraph of [PROMPT-SAE] in its dispatch prompt. With N = 3, the fix after round 2 gets it,
which is the last fix before the limit; every later fix after the owner raises the limit gets
it too.

Acceptance:
- [ ] With N = 3: no paragraph for the fix of round 1, the paragraph for the fix of round 2.
- [ ] With N = 1: every fix, which runs only after the owner's go at the park, gets it.

### [PARK-STORY] A plain story at the round limit
When a job, or the task for the integration, parks at the round limit, `sae` prints a story
built from the files: the target, the round count against the limit, the job's objective, the
first result's summary, then per round the finding titles with their suggested fixes, the
fix jobs' "do not" limits with their reasons, and the fix results' summaries, and the options: change the approach, reduce the requirement, another
round. The orchestrator relays it and adds its recommendation with the reason. The viewer shows
the same story on the parked job.

Acceptance:
- [ ] `sae next` and `sae status` print the story for a job parked at the limit.
- [ ] The story uses only result summaries, finding titles and suggested fixes; no transcripts.

### [DECISION-ANYTIME] Decision jobs without a parked job
`sae decision new` accepts a parked job, any other job or review round, or only a question. The
job it concerns does not have to park; independent work continues. A decision job only advises,
so it may run while a job or the task is parked or held. `execute.md` tells the
orchestrator to use a decision job when the analysis would fill its context, with examples:
a finding proposes a change of approach, a worker's Approach proposal, two results contradict
each other, a fix chain near its round limit. Simple decisions are still logged with `sae log`.

Acceptance:
- [ ] `sae decision new <task> --question "<text>"` and `--from <review round>` create a decision
      job whose job file points to the question or the round.
- [ ] `--from <parked job>` works as today.
- [ ] A decision job dispatches and collects while the integration round limit parks the task.

### [JOB-DROP] Drop a parked job and its fix chain
On the owner's word, `sae job drop <task> <ID> --reason "<why>"` marks an unmerged writer job
(parked, failed or done) as dropped, together with its fix jobs and their review rounds. Dropped
jobs never merge. The integration review, the final validation and the `finish` gates ignore
them. Branches and result files stay. The command refuses when the job's changes are already in
the shared checkout (a task without worktrees, or without git), and says why. It refuses while a
job outside the dropped group needs a dropped job, and names the `sae job edit --needs` call to
run first; the group's own fix jobs and reviews do not block it. The drop is logged as a decision,
the final report lists dropped jobs, and the viewer shows them as dropped.

Acceptance:
- [ ] After a drop, the integration review and the final validation become ready when all other
      writers are merged.
- [ ] A drop of a job that another job needs is refused with the fix command.
- [ ] A drop in a task without worktrees is refused before any state changes.
- [ ] `execute.md` names the command, only on the owner's word.

### [RESULT-SECTIONS] Job results without empty sections
The job-result template marks optional sections "delete when it does not apply", and the worker
protocol says to leave out empty sections. Text: [PROMPT-WORKER].

Acceptance:
- [ ] The finding is resolved by the job that changes the template.

### [PROMPT-JOB] Prompt changes in one job, checked by the owner
All changes to the skill's prompt text (SKILL.md, `references/`, `templates/`, and the text that
`sae` prints into prompts) are made by one job. It starts from the drafts in "Prompt text" below
and keeps them lean. It also checks the rest of the skill and the CLI help for contradictions with
the new text and lists them in its result. A hold after this job lets the owner read the diff
before anything else builds on it.

Acceptance:
- [ ] The plan has one prompt job with a hold after it.
- [ ] Its result lists the contradictions it found, or says that it found none.

### [SHARED-RULE-OWNER] One owner for a shared interface or business rule
The planner gives a shared interface or business rule one owner job: the first job that needs
it builds it once, as a thin working slice with its tests, and the others wait for it. A
separate contract job only when the spec already fixes the shape and several jobs must start at
once. Text: [PROMPT-PLANNER].

Acceptance:
- [ ] `planner.md` line "Parallel jobs that share an interface" is replaced by the text.

## Technical contract

### Interfaces
- New or changed commands: `sae job add --difficulty easy`; `sae decision new --question`,
  `--from <any job or review>`; `sae job drop`; one command (or flag) that accepts an integration
  round with a reason. Names other than `sae job drop` are the planner's choice.
- A new job status or flag for dropped jobs: the planner's choice; `sae status`, `sae next`,
  the gates and the viewer must treat it as final.

### Technical constraints
- `sae` stays standard-library Python 3.9 or newer, with no model names in its code
  ([DECISION-EASY-UPGRADE]).
- Read-only commands stay lock-free and write nothing (`scripts/sae_lib/AGENTS.md`).
- Prompt text changes follow [PROMPT-JOB].

## Prompt text

Drafts for [PROMPT-JOB]. The owner approved the planner rule, the approach paragraph, the
stakes template and the finding fields as worded here; the job keeps their meaning and may
tighten the rest. "Before" quotes the current text where a change replaces it.

### [PROMPT-PLANNER] `references/roles/planner.md`

Before:

    - Parallel jobs that share an interface: add a contract job first (types, schema, API stubs).
      It merges before the fan-out.

After:

    - Parallel jobs that share an interface or a business rule: the first job that needs it
      builds it once, as a thin working slice with its tests (walking skeleton, tracer bullet);
      the other jobs wait for it. Add a separate contract job (contract first) only when the
      spec already fixes the shape and several jobs must start at once.

Before:

    - Set a difficulty per job: `mechanical`, `normal` or `hard`. It selects the model.

After:

    - Set a difficulty per job; it selects the model. `mechanical`: follow a clear procedure.
      `easy`: a simple change that needs local judgment. `normal`: design a solution for a
      difficult implementation task. `hard`: especially demanding logic or complex UI
      interactions.

Added after "Optimize total cost, not parallelism: …":

    - Match the care in the plan to the stakes in your prompt: add a job, check or safeguard
      only when the stakes justify it.

### [PROMPT-REVIEW] `templates/review.md` and `references/roles/reviewer.md`

`templates/review.md`, the finding block and Notes. Before:

    ### 1. <title> — blocking | major | minor
    **Evidence:** <file:lines, or artifact section>
    **Affects:** <REQ-ID or component>
    **Why it matters:** …
    **Correction:** …

    ## Notes

After:

    ### 1. <title> — blocking | major | minor
    **Evidence:** <file:lines, or artifact section>
    **Breaks:** <REQ-ID, intent or stakes line>: how this contradicts it
    **Expected:** <what should happen> **Actual:** <what happens now>
    **Also in:** <other places that apply the same rule, found by search; delete when none>
    **Suggested fix:** <a proposal; may be a change of approach>

    ## Notes
    <!-- Remarks that do not block. A finding below the stakes: `[beyond stakes]` and one
         sentence why. -->

`reviewer.md`, section "Output". Before:

    Output (template `templates/review.md`): frontmatter `target` and `verdict` (`pass`,
    `pass-with-notes`, `changes-required`); then each finding with severity (`blocking`, `major`,
    `minor`), evidence (file and lines, or the spec section), the requirement or component it
    affects, why it matters, and the recommended correction. Short and concrete.

After:

    Output (template `templates/review.md`): frontmatter `target` and `verdict` (`pass`,
    `pass-with-notes`, `changes-required`); then each finding with its severity (`blocking`,
    `major`, `minor`) and the template's fields. `Expected` is what the fix must make true.
    `Suggested fix` is a proposal; when patches would not converge, propose a change of
    approach. When the broken rule applies in more places, search for them and list them under
    `Also in`. Short and concrete.

    Grade every finding against the stakes in your prompt. Report everything you find; the
    stakes decide only whether it blocks. A finding that needs more care than the stakes
    justify goes to Notes as `[beyond stakes]`, with one sentence why. When a change adds a
    safeguard, check what new failure it can cause in normal use. When your prompt points to an
    Approach proposal, judge it: when it holds, make it the `Suggested fix` of a finding.

### [PROMPT-WORKER] `references/roles/worker.md` and `templates/job-result.md`

`worker.md`, section "Work". Before:

    - **Review findings are claims.** When your job answers a review (your prompt points to it),
      check each finding against the code before you change anything. Do not implement a finding
      you believe wrong: list it under `## Disputed findings` in your result, with the reason.

After:

    - **Review findings are claims.** When your job answers a review (your prompt points to it),
      check each finding your job names against the code before you change anything. Make its
      `Expected` true, also in every place under `Also in`. Its `Suggested fix` is a proposal:
      use a better way when you find one, and say why. Do not implement a finding you believe
      wrong: list it under `## Disputed findings` in your result, with the reason.
    - If you see a different approach that would stop the same kind of finding from coming
      back, finish your job anyway and describe it under `## Approach proposal` in your result,
      also when a "do not" in your job blocks it: name that limit and why its reason is weak.
      The next review judges it.

`worker.md`, section "Result", added at the end of its first paragraph:

    Leave out sections that do not apply.

`templates/job-result.md`: each of "Decision request", "Disputed findings", "Risks" and
"Findings filed" gets "Delete when it does not apply." in its comment. Added after "Disputed
findings":

    ## Approach proposal
    <!-- Only when a different approach would stop the same kind of finding from coming back.
         The approach in a few sentences, and why. Delete when it does not apply. -->

### [PROMPT-EXECUTE] `references/modes/execute.md`

"Loop", step 2. Before:

    When the output is a COMMAND (a
       review in the other harness), run it in the background; when it fails, run the IF IT FAILS
       line printed with it.

After:

    When the output is a COMMAND (a
       job in the other harness), run it in the background. When it fails, or `sae` refuses
       because the other harness is missing: for a review, run the IF IT FAILS line; for any other
       job, run it only in `full-auto`; in the other modes keep the job waiting, continue with
       independent work and ask the user first. `sae` records each such run as a routing
       exception; later dispatches use routing again.

"Loop", step 3: the two bullets "job review `changes-required`" and "integration review
`changes-required`" are replaced by:

    - review `changes-required` (a job or the integration) → triage first, against the stakes.
      A finding that needs more care than the stakes justify becomes `[beyond stakes]` in
      your report. For the rest, add fix jobs (`sae job add <task> <ID>-FIX-1 --kind
      implementation --fix-of <ID or round ID> --reason "<review>: changes required"`). A fix
      job states each finding's `Expected` and every place under `Also in`; it does not limit
      the worker to single instances; each "do not" in it gives its reason ("because …"),
      also when it rules out a fix that a review proposed. One round gets one fix job unless
      its findings touch unrelated parts and one job would not fit one context. Log each
      finding you set aside with its reason. When no finding is left, accept
      the review when the mode lets you decide: `sae merge <task> <ID> --accept-review "<why>"`
      for a job, `<accept command> "<why>"` for the integration. A finding that proposes a
      change of approach is a decision (below).
      After `max-review-rounds` changes-required rounds (default 3), the job, or for the
      integration the task, parks for the user. Relay the story `sae` prints and ask, in every
      mode: change the approach, reduce the requirement, or another round; add your
      recommendation and its reason. To change the approach, a job may be dropped, only on the
      user's word: `sae job drop <task> <ID> --reason "<why>"`.

"Decision flow", step 2. Before:

    2. Otherwise classify it (see interaction-modes.md). When it needs analysis, do not research
       it in your own context: `sae decision new <task> --from <ID>`, dispatch, collect.

After:

    2. Otherwise classify it (see interaction-modes.md). When its analysis would fill your
       context (several files, review rounds or options to compare), do not do it yourself:
       `sae decision new <task> --from <ID>` or `--question "<question>"`, dispatch, collect.
       The job it concerns need not park; independent work continues. Typical cases: a finding
       proposes a change of approach; a worker's Approach proposal; two results contradict each
       other; a fix chain near its round limit.

"Finish", step 3: "(agent decisions, settled disputes, amendments, overridden gates)" becomes
"(agent decisions, settled disputes, findings let go with their reasons, routing exceptions,
dropped jobs, amendments, overridden gates)".

### [PROMPT-SHAPE] `references/modes/shape.md`

"2. First round", added to the list of what the round has:

    - when `sae status` shows `stakes: not set`, one question about the project's stakes: a
      draft of the Stakes section of `templates/repo/profile.md`, based on AGENTS.md (or
      CLAUDE.md) and the README. Write the answer into `.tasks/repo/profile.md`; when the owner
      skips, write the template's "not set" line there.

"3. Research", step 1: `--difficulty normal|hard` becomes `--difficulty easy|normal|hard`.

### [PROMPT-PROFILE] `templates/repo/profile.md`

The comment "Facts only. …" becomes "Facts, and the owner's stakes. Do not repeat what AGENTS.md
or CLAUDE.md already say; link them instead." Added after it:

    ## Stakes
    <!-- Why the project exists and how much care it needs. Every agent reads it.
         Example, a small game for a kid:
         - Who uses it and why: A game for a kid to play in the evenings.
         - Acceptable breakage: Any. We restart and laugh; at worst a high score is lost.
         - What matters now: Speed. We are still finding out what is fun.
         - Don't build: Save-file versioning or recovery for nearly impossible races.
         - So build it like: A toy.
         Do not name risky areas or exceptions here; hard limits belong in the repository
         instructions. When the owner does not set stakes, keep only this line:
         - Not set by the owner. Estimate the stakes from the repository instructions and the
           README, and build and review to that level: neither over- nor under-engineer. -->
    - Who uses it and why:
    - Acceptable breakage:   <!-- how much, in one or two sentences; not a list -->
    - What matters now:
    - Don't build:           <!-- optional: only what agents have already overbuilt here -->
    - So build it like:      <!-- a toy | a tool for friends | a product people pay for | a bank -->

### [PROMPT-SAE] Text that `sae` prints into prompts

Stakes line, in every dispatch prompt:

    Stakes (read before you start): <path>, section "Stakes"

Without stakes:

    Stakes: not set. Estimate them from the repository instructions and the README, and work to
    that level: neither over- nor under-engineer.

Next review round, when the fix result has an Approach proposal:

    Read first: the "Approach proposal" in <fix result path>

Approach paragraph, for a fix of round k ≥ N − 1:

    FIX {n} of {TARGET}. The job parks for the owner after review round {N}.
    Before you patch, read the earlier review rounds of this job and answer in your result:
    1. Do the findings share one cause? Typical causes: the same value computed in several
       places; a function that gets a new special case in every round; a requirement read
       wider than the spec states.
    2. Would a different approach remove that cause, so the same kind of finding cannot come
       back? Typical approaches: one function that every place calls; a value stored once
       instead of derived; a smaller reading of the requirement.
    If yes and it fits your job, use it. If your job forbids it, still make your best fix and
    describe the approach under "Approach proposal" in your result.

### [PROMPT-SETUP] `references/modes/setup.md`

The "Tiers" table becomes the table of [TIERS-FOLLOW-DIFFICULTY]. The execution and research
tables gain an `easy` column between `mechanical` and `normal`, with the cells of
[EASY-UPGRADE]; the other cells keep their model · effort and renumber their tier (old L2 → L3,
old L3 → L4, old L4 → L4). The Codex seed families gain terra. The guide in "2. Guide" names
four difficulties. For example, the Claude execution table after:

    | claude · execution | mechanical | easy | normal | hard |
    |---|---|---|---|---|
    | economy | L1 · sonnet · medium | L1 · sonnet · medium | L1 · sonnet · high | L3 · opus · low |
    | balanced | L1 · sonnet · high | L2 · sonnet · high | L3 · opus · medium | L4 · opus · high |
    | premium | L3 · opus · low | L3 · opus · medium | L4 · opus · high | L4 · opus · xhigh |

"5. Harness permissions", after:

    ## 5. Harness permissions

    Writer jobs need git writes in their worktree and often local sockets for their checks. For
    now SaE starts them with a bypass request:

    - **Orchestrator session:** run it with full access (Claude Code: bypassed permissions;
      Codex: `codex --yolo`). Its subagents inherit it.
    - **Jobs in the other harness:** `sae dispatch` prints a launch command without a sandbox.
    - **Codex subagent cap:** `[agents] max_threads`. By default a Codex session holds only 3
      subagents (6 on older models); parallel writers, reviews and research then fail with
      "agent thread limit reached". When `sae` reports fewer than 8, recommend 10 and offer to
      set it.

    A sandboxed setup waits in the backlog. `sae setup snippets` prints a draft of it; its Codex
    git rule does not work in linked worktrees yet.

    Show each change, explain it in one sentence, and apply it only after the user says yes.
    Back up the file first.

## Decisions

### [DECISION-FOUR-DIFFICULTIES] Four difficulties, `easy` in execution and research
**Decision:** Add `easy`; planning and review keep `normal` and `hard`.
**Reason:** The owner sees `hard` used too often and wants a cheaper route for simple work that
needs judgment. Planning and review should always be done well: "it is one moment, with a
potentially large gain later".
**Based on:** user decision
**Provenance:** [human]

### [DECISION-EASY-UPGRADE] `easy` falls back to `mechanical` until setup fills it
**Decision:** `sae` does not write the owner's model defaults into configurations; setup mode
proposes them. Until then `easy` uses the `mechanical` cell of the same layer.
**Reason:** The owner chose to fill the new column with their defaults. The repository's intent
forbids model names in `sae` ("No configuration and no model names in the skill, except the
setup proposal, which `sae` never reads"). Setup mode reads the proposal, so it can fill the
column without breaking that rule.
**Based on:** user decision; `docs/adr/_intent.md`
**Provenance:** [agent]

### [DECISION-YOLO-WRITERS] Writers in the other harness run without a sandbox
**Decision:** The COMMAND bypasses the sandbox; a sandboxed launch waits in the backlog.
**Reason:** SaE is at an early stage, and a permission setup is complexity the owner does not want
yet. Research showed that `-s workspace-write` disables a Codex permission profile and blocks git
writes and local sockets ([CODEX-LAUNCH](research/CODEX-LAUNCH.md),
[probe](prototypes/codex-probe/README.md)).
**Based on:** user decision; research
**Provenance:** [human]

### [DECISION-FALLBACK-BY-MODE] Fallback depends on the interaction mode
**Decision:** `full-auto` falls back and records; other modes ask first; reviews keep their
automatic fallback.
**Reason:** A silent reroute broke the owner's routing in an earlier task.
**Based on:** user decision
**Provenance:** [human]

### [DECISION-STAKES-IN-SAE] Stakes are a part of SaE, read from the profile first
**Decision:** SaE stores stakes in the repo profile and never writes AGENTS.md or CLAUDE.md; it
reads an existing section there as a fallback.
**Reason:** The owner does not want SaE to change files of their ecosystem. Stakes are a part of
how SaE thinks, so it asks once per repository. A passive section in AGENTS.md seemed to have
little effect in a real project; SaE uses stakes actively where decisions are made.
**Based on:** user decision
**Provenance:** [human]

### [DECISION-REVIEWER-KNOWS-STAKES] The reviewer reports everything; stakes decide what blocks
**Decision:** As in [STAKES-GRADING].
**Reason:** The reviewer holds the evidence; filtering only in the orchestrator let speculative
findings through in an earlier task. Rejected: a hard burden-of-proof rule (agents bend it),
per-spec promise lists (cannot be complete), a precedents file (cannot be maintained).
**Based on:** user decision
**Provenance:** [human]

### [DECISION-FINDING-SHAPE] Expected behavior binds; the suggested fix is a proposal
**Decision:** As in [FINDING-SHAPE] and [FIX-WORKER].
**Reason:** A free "Correction" let orchestrators prescribe wrong solutions and forbid simple
ones. The owner's idea: the worker meets the finding's intent and may find a better way, which
also checks the review.
**Based on:** user decision; backlog item
[Fix the broken rule](../backlog/tier-1/2026-11-13-1324--fix-the-broken-rule-not-one-instance.md)
**Provenance:** [joint]

### [DECISION-NO-PARK-FOR-APPROACH] Workers propose an approach; they do not park for it
**Decision:** As in [FIX-WORKER]; parking stays at the round limit.
**Reason:** The owner expects workers to park too often otherwise, and wants a review to check
the proposal.
**Based on:** user decision
**Provenance:** [human]

### [DECISION-APPROACH-CHECK-N-1] The approach check starts at fix round N − 1
**Decision:** As in [APPROACH-CHECK].
**Reason:** No fixed count of fixes: several fix rounds are often justified. N − 1 gives the last
fix a chance to save the job.
**Based on:** user decision
**Provenance:** [human]

### [DECISION-DECISION-JOBS] Decision jobs whenever analysis would fill the orchestrator's context
**Decision:** As in [DECISION-ANYTIME].
**Reason:** Local task records showed one decision job in about 1,750 jobs, and about 500
decisions logged without one: the command needs a parked job, and workers rarely park. The owner
accepts this for now and may tune it after real use.
**Based on:** user decision; scan of local task records (2026-11-20)
**Provenance:** [human]

### [DECISION-SHARED-RULE-OWNER] The first job that needs a shared rule builds it
**Decision:** As in [SHARED-RULE-OWNER].
**Reason:** A contract cannot be fully foreseen, and a separate contract job adds a job. In one
codebase, a walking skeleton gives the real interface; contract first fits a fixed shape and
parallel starts.
**Based on:** user decision
**Provenance:** [joint]

## Open questions

None. Command names other than `sae job drop` are left to planning.

## Research basis

- [CODEX-LAUNCH](research/CODEX-LAUNCH.md), [CLAUDE-LAUNCH](research/CLAUDE-LAUNCH.md) and the
  [Codex probe](prototypes/codex-probe/README.md): the basis for [DECISION-YOLO-WRITERS] and the
  sandboxed backlog item.

## Amendments

### [AMEND-1] The prompt carries the stakes text, not a pointer
**Change:** [STAKES-POINTER]. Every dispatch prompt carries the stakes themselves: one header
line, then the section's lines with HTML comments stripped. The header line names the source
and says what stakes are, for example: `Stakes: how much care this project needs; build and
review to this level (from <path>, section "Stakes"):`. When the stripped section is longer
than 15 lines, the prompt names the source and section instead, as before. No sentence about
other copies of the profile (owner: noise). Without stakes, the "not set" text also says what stakes are
(who uses it, acceptable breakage, what matters now). The acceptance "Each prompt kind carries exactly one stakes
line" becomes "exactly one stakes block". `STAKES_LINE` in `prompts.py` changes to the header.
**Reason:** `sae` inserts the stakes deterministically anyway. The text saves every subagent a
tool call, makes sure it reads them, and defines the term also when the stakes come from
AGENTS.md or CLAUDE.md, where the template's comment is absent. This is a conscious deviation
from "Dispatch prompts carry pointers, not pasted content" (decision record "Follow PROSE
without ceremony"): here the pointer adds a step to every run.
**Provenance:** [human] the owner proposed it on 2026-11-20; [agent] the header wording and
the 15-line limit.

### [AMEND-2] The term is "Project Stakes"
**Change:** the project's stakes have the proper name **Project Stakes**, in every place that
means them. The section heading is `## Project Stakes` in `.tasks/repo/profile.md`, in the
profile template and in the lookup in AGENTS.md and CLAUDE.md (no fallback to `## Stakes`). The
prompt block of [AMEND-1] starts with `Project Stakes:` and names the section "Project Stakes".
The "not set" text starts with `Project Stakes:` too. The review tag `[beyond stakes]` becomes
`[beyond Project Stakes]`. `sae status` prints `Project Stakes: <source>` or `Project Stakes: not
set`. The viewer labels and its help use the name. Code identifiers (`STAKES_LINE`, module and
test file names) stay. `[beyond stakes]`, `## Stakes` and `section "Stakes"` become retired
terms.
**Reason:** a model reads the plain word "stakes" in its everyday sense. A capitalized proper
name reads as a defined term. "Settings" was rejected: it collides with the task's settings
(levels, review), the confusion of review finding 1.
**Provenance:** [human] the owner asked for a proper name and chose "Project Stakes" on
2026-11-20; [agent] the tag, the status wording and the retired terms follow from it.

### [AMEND-3] Setup proposal: the owner's tiers, cells carry only a tier, Tiers and Free mode
**Change:** [SETUP-PROPOSAL], [TIERS-FOLLOW-DIFFICULTY], [EASY-UPGRADE] (setup text only).
1. Tiers. The proposal's tiers are the owner's table in `prototypes/setup-routing-owner.json`
   (`tiers`). Against [TIERS-FOLLOW-DIFFICULTY], Codex L1 is terra · high.
2. Cells. Every routing cell of the proposal (all phases, both harnesses, the `easy` column
   included) carries only a tier, as in `prototypes/setup-routing-owner.json` (`cells`). It
   carries no own model · effort. This replaces "Every other cell keeps its model · effort" and
   "Save both in every cell". The first switch to Free mode copies the tier's model · effort
   into each cell without one (`settings.js` does this today), so the switch changes no route.
   The proposal keeps no hand-set extra such as sol · max: Free mode is where the user sets
   those.
3. Names. The two ways to set routes are **Tiers mode** (cells point to L1–L4; the default) and
   **Free mode** (each cell has its own model · effort). The viewer's switch and its help use
   these names. The config key `tiers_in_cells` stays.
4. Guide. Step "2. Guide" of `setup.md` becomes the text in `prototypes/setup-guide.md`.
5. Upgrade of an existing config (step "1. Look"): the user's own model · effort in each cell
   stays (it is the user's data). The upgrade proposes the new tiers, the new tier label per
   cell from the owner's table, and the `easy` cells, and it says that with Tiers mode on the
   routes follow the new tiers.
**Reason:** neither the spec's old pairs nor the code's per-cell pairs rose evenly with the
difficulty (integration review finding 4). One default (tiers) is simpler to maintain when
models change, and switching modes must not change routes by itself.
**Provenance:** [human] the owner set every tier and cell in a settings mockup, chose one
default config of tiers with Free mode as the user's own fine-tuning, named the modes, and
approved the guide text (2026-11-26); [agent] the upgrade rule (point 5).

### [AMEND-4] Owner walkthrough of the first run
**Change:** new job `FIRST-RUN-WALKTHROUGH`. It builds a reusable tool in
`tests/tools/walkthrough/` that starts a first-run session of the skill in a sandbox (a
relocated `HOME`, per `research/SANDBOX-ISOLATION.md`), in a new Orca terminal. Two scenarios:
a fresh install (no `sae` config) and an upgrade (a copy of a config without `easy`). Claude is
the default harness, with interactive `/login`; a `setup-token` token is the fallback. Codex is
supported on demand (a flag). After the job, a hold lets the owner walk through both scenarios
before the integration review round and the final validation.
**Reason:** setup text and upgrade prompts are UX that tests do not show; the owner wants to
see the first run as a new user.
**Provenance:** [human] the owner asked for the walkthrough, the folder, Claude by default with
interactive login, and Codex on demand (2026-11-26); [agent] the two scenarios and the place
before the final validation.
