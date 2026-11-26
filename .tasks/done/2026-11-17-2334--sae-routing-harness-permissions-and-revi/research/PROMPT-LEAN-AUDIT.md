# Lean audit of the PROMPT-TEXT diff

**Owner decisions, 2026-11-20 [human]:** proposals 1–9 are accepted. Proposal 10 is rejected:
the routing tables keep a tier and an own model · effort in every cell (two intended modes).
The job this report calls PROMPT-TEXT-FIX-3 is `PROMPT-LEAN`.


Read-only audit of the prompt files. Yardsticks: the `agentic-systems-guidelines` rules (CORE-1
light, CORE-2 one home per fact, SKILL-3 deterministic work in scripts) and `docs/adr/_intent.md`
("light in its complexity", "deterministic where it must be exact"). Line numbers are those of
the files at 34876a1.

## Lines added (net)

| file | who reads it | net now | after accepted | after all |
|---|---|---|---|---|
| SKILL.md | every run | 0 | 0 | 0 |
| interaction-modes.md | orchestrator, execute | +1 | +1 | +1 |
| modes/execute.md | orchestrator, execute | +31 | +8 | +8 |
| modes/shape.md | orchestrator, shape | +13 | +6 | +5 |
| modes/plan.md | orchestrator, plan | +9 | +1 | +1 |
| modes/setup.md | setup only | +19 | +19 | +13 |
| roles/planner.md | planner | +7 | +7 | +7 |
| roles/reviewer.md | every reviewer | +8 | +8 | +7 |
| roles/worker.md | every worker | +6 | +6 | +6 |
| roles/decision-worker.md | decision worker | +1 | +1 | +1 |
| templates (5 files) | subagents | +30 | +30 | +30 |
| prompts.py (constants) | printed when wired | +21 | +21 | +21 |
| **total** | | **+146** | **about +108** | **about +100** |

The orchestrator's mode files (execute, plan, shape, interaction-modes) go from +54 to about
+16. The text that moves out comes back as `sae` output, printed only at the moment it applies.

## What `sae` prints today (checked)

- `sae dispatch` (`progress.py cmd_dispatch`, lines 444–452): a COMMAND and an IF IT FAILS line
  only for a review in the other harness. The IF IT FAILS line is a bare `--resume` command. No
  rule is printed, there is no CLI check, and a `--resume` of a done research or planning job
  appends its attempt before anything could refuse.
- `sae collect` for a changes-required job review (`reviews.py apply_review`, 692–697): it
  already prints a fix command and the accept command. Bug: it always prints
  `<target>-FIX-1`, so a second round fails on a duplicate ID. For the integration
  (`apply_integration_review`, 716–725) it uses `fix_job_command`, which picks a fresh ID.
- At the round limit (`apply_review` 681–690; integration 715–720) it prints "Ask the user"
  and the accept, fix and raise-the-limit commands. It does not say "add no fix job before the
  user answers", and it prints no story.
- No `--let-go` line, and no Approach proposal report. Disputed findings already get a collect
  line (`reviews.py` around 575), which is the model for the Approach proposal line.

So most of execute.md's step 3 repeats what `sae` already prints. Step 2's fallback rule is
printed nowhere yet. WRITER-LAUNCH must add it.

## Where the prompt-file edits go

The plan says that `references/`, `templates/` and `SKILL.md` are "edited only in PROMPT-TEXT",
and [PROMPT-JOB] wants one prompt diff for the owner. So I recommend one more fix job of
PROMPT-TEXT at the current hold (call it PROMPT-LEAN; scope and verify as PROMPT-TEXT).
It makes all the prompt-file edits below. Each code job gets what it must print, plus a test
for the printed text, so a cut rule cannot get lost. Also remove "`references/modes/execute.md`
'Loop' step 2 as `PROMPT-TEXT` wrote it" from WRITER-LAUNCH's Inputs: the rule now lives in
`sae`.

## Proposals, biggest gain first

### 1. Fallback rule: move it to `sae` via WRITER-LAUNCH — accepted

Saves about 25 lines in three orchestrator files. Touches [HARNESS-FALLBACK],
[DECISION-FALLBACK-BY-MODE]. Wording only: [HARNESS-FALLBACK] already says "`sae` prints the
rule".

**Paste into WRITER-LAUNCH Inputs:**

> Audit 2026-11-20 (owner accepted): the whole fallback rule lives in `sae dispatch` output.
> The mode files will only say "when it prints a COMMAND, follow what it prints". So:
> 1. With every COMMAND, print one line on how to run it: in the background, in a shell, not
>    as a subagent; `sae collect` reads its tokens, so add no `--tokens`.
> 2. With every fallback command (the IF IT FAILS line of a COMMAND, and the refusal for a
>    missing CLI), print only the branch that applies, chosen from the job kind, the job
>    status and the task's interaction mode (name the mode):
>    - a review, any mode: run the fallback command now;
>    - any other job in `full-auto`: run it now;
>    - any other job in another mode, pending or running (a started COMMAND that failed):
>      `sae job park <task> <ID> --reason "harness fallback: <why>"`; ask the user with
>      `sae ask <task> "<question>" --job <ID>`; continue with independent work; on the
>      user's yes, log it with `sae log <task> decision "harness fallback: <ID>: <answer>"
>      --by human --job <ID>` and run the fallback command with `--resume`;
>    - a done research or planning job that `--resume` reopens, refused for a missing CLI:
>      "the job stays done; do not park it", then the same ask, log and run, with the
>      fallback command keeping `--resume`.
> 3. The missing-CLI check also covers `--resume` of a done research or planning job. It
>    runs before the attempt is appended (today the attempt is appended at
>    `progress.py:413–421`), so a refusal changes no state.
> 4. A routing exception needs no text for the orchestrator: `sae` records it, and the
>    ROUTING line names it.
>
> Validation: one test per branch asserts the printed text (review; `full-auto`; another mode
> with a pending job; another mode with a running job after a failed COMMAND; a done job with
> `--resume`).

**Paste into PROMPT-LEAN, prompt-file edits:**

- `execute.md` 33–46: replace with
  > 2. For every ready job, up to the parallelism it offers: `sae dispatch <task> <ID>`, then
  >    spawn a subagent with the printed PROMPT, MODEL and EFFORT. When it prints a COMMAND
  >    instead (a job in the other harness), run it as printed. When it fails, or `sae`
  >    refuses, follow the rule `sae` prints with the fallback command.
- `plan.md` 12–21: replace with
  >   printed prompt, model and effort; when it prints a COMMAND instead, follow what it prints.
  >   Collect it when it returns.
- `shape.md` 52–55: replace with
  > 4. For each job: `sae dispatch <task> <TOPIC-ID>`, then spawn a subagent with the printed
  >    prompt, model and effort; when it prints a COMMAND instead, follow what it prints. Run
  >    them in parallel.
- `shape.md` 65–72: replace with
  >    - `sae dispatch <task> <TOPIC-ID> --resume --reason "follow-up questions"`; for a
  >      COMMAND or a refusal, follow what it prints;
- Optional, older text with the same duplicate: `plan.md` 41–43 and `shape.md` 132–134 ("When
  the printed output is a COMMAND … `sae` reads the COMMAND's tokens itself."). Each could
  become "When it prints a COMMAND, follow what it prints. Collect it." Not counted above.

### 2. Round-limit park and fix-round commands: move them to `sae` via FIX-LOOP-EXITS and FIX-LOOP-GUIDANCE — accepted

Saves about 13 lines in execute.md (together with proposal 3). Touches [TRIAGE], [PARK-STORY],
[JOB-DROP], [ACCEPT-INTEGRATION]. Wording only. execute.md keeps the triage step ([TRIAGE]
acceptance), the `sae job drop` name "only on the user's word" ([JOB-DROP] acceptance) and
the word `accept-review` (PROMPT-TEXT verify).

**Paste into FIX-LOOP-EXITS Inputs:**

> Audit 2026-11-20 (owner accepted): execute.md Loop step 3 will tell the orchestrator to use
> the commands `sae collect` prints for a changes-required review. So the changes-required
> messages without a park (`reviews.py apply_review` and `apply_integration_review`) print:
> - a lead line: "<target>: changes required. Triage first (execute.md, Loop step 3).";
> - the fix command from `fix_job_command` (a fresh `-FIX-<n>`; `apply_review` hard-codes
>   `-FIX-1` today, and the second round then fails on a duplicate ID);
> - the let-go line: `sae log <task> decision "<finding>: <reason>" --job <REVIEW-ID> --let-go`;
> - the accept line, "when the mode lets you decide": `sae merge <task> <ID> --accept-review
>   "<why>"` for a job, `sae accept-review <task> <REVIEW-ID> --reason "<why>"` for the
>   integration. `sae finish --override` stays, marked "on the owner's word".
>
> Validation: a test asserts the four lines for a job and for the integration, and that a
> second job round prints `-FIX-2`.

**Paste into FIX-LOOP-GUIDANCE Inputs:**

> Audit 2026-11-20 (owner accepted):
> 1. Every park message at the round limit (`apply_review` and `apply_integration_review`,
>    the parked branches) and the story in `sae next` and `sae status` open with: "Parked at
>    the round limit: the choice is the user's, in every mode. Add no fix job and accept
>    nothing before the user answers: a fix job unparks the job. Relay the story with your
>    recommendation and its reason." The options name their commands: another round (the
>    fix command with a fresh ID; `sae set <task> max-review-rounds=<n>`); change the
>    approach (`sae job drop <task> <ID> --reason "<why>"`, only on the user's word, or
>    `sae decision new <task> --from <REVIEW-ID>`); reduce the requirement (an amendment);
>    accept (the accept command of FIX-LOOP-EXITS). It may name `sae ask <task> "<question>"
>    --job <ID>` for the wait.
> 2. `sae collect` reports an Approach proposal: when a done result has a non-empty
>    `## Approach proposal`, print "Approach proposal in <result path>: read that section; it
>    is a decision (execute.md, Decision flow)." Model it on the disputed-findings line.
>
> Validation: tests assert the opening line for a parked job and for the parked task, and the
> collect line with and without the section.

**Paste into PROMPT-LEAN:** `execute.md` 63–86 (the changes-required bullet and the
Approach proposal bullet): replace with

>    - review `changes-required` (a job or the integration) → when `sae collect` reports a
>      park at the round limit, follow what it prints: the choice is the user's, in every
>      mode, and a job is dropped (`sae job drop`) only on the user's word. Otherwise triage
>      against the stakes: a finding that needs more care than they justify is
>      `[beyond stakes]`; log each finding you set aside with the `--let-go` line `sae`
>      prints. For the rest, add one fix job with the printed command; split a round only
>      when its findings touch unrelated parts and one job would not fit one context. The fix
>      job names each finding's `Expected` and every `Also in` place, never only one
>      instance, and each "do not" in it says "because …". With nothing left to fix, accept
>      the review with the printed command (`sae merge --accept-review` or
>      `sae accept-review`) when the mode lets you decide. A change of approach, or an
>      Approach proposal that `sae collect` reports, is a decision (below).

### 3. Approach proposal rule in three places in execute.md — accepted

Lines 5–6 (the exception), 85–86 (the outcome bullet) and 104 (a decision example). The bullet
merges into proposal 2's text above. Line 104 stays, because [DECISION-ANYTIME] asks for the
examples. Touches [FIX-WORKER], [DECISION-ANYTIME]. Wording only. The `sae collect` report is
item 2 of FIX-LOOP-GUIDANCE above.

**Paste into PROMPT-LEAN:** `execute.md` 5–6: replace with

> small: read a result body only when a job is parked or failed; when `sae collect` reports
> disputed findings or an Approach proposal, read only that section.

### 4. Revert "care" to "stakes" in SKILL.md — accepted

`SKILL.md` 18 is the only use of "care" as an axis. No other file uses "stakes" for the axis.
The spec defines the Stakes section as what "sets the level of care", and `_intent.md` says
"stakes set the settings": the project section and the task settings are one axis at two
scopes. No rename and no retired term are needed. 0 lines. Wording only.

**Paste into PROMPT-LEAN:** `SKILL.md` 18: restore the base text,
`jobs) and **stakes** (the task's settings: levels per phase and review). A small task is`.

### 5. Codex seed order in setup.md is wrong — owner's fact, a correctness fix

The order is luna < terra < sol < astra. The PROMPT-TEXT result assumed that terra is lighter
than luna. Only setup.md names these families (no code or viewer file does).

**Paste into PROMPT-LEAN:**
- `setup.md` 68–69: swap the two rows, so the list reads luna, terra, sol, astra ("lightest to
  strongest; the order sets each model's color").
- `setup.md` 81: `(terra → luna → sol → astra)` becomes `(luna → terra → sol → astra)`.

### 6. setup.md upgrade steps: shorten — open, wording only

Lines 17–29 (13 lines; read in setup mode only) say the tier change three times: the tier
table, step 1 and step 2. Saves 6 lines. Touches [EASY-UPGRADE], [TIERS-FOLLOW-DIFFICULTY].
Proposed text:

> A config without an `easy` column works: `easy` jobs use the `mechanical` cell, and `sae`
> says so. To upgrade it, propose these changes, save them after the user's yes (step 4), and
> skip the guide: the tiers of step 3; every cell keeps its model · effort and gets a new tier
> label (Claude: L2 → L3, L3 → L4, L4 stays, and say that cells on the old L4, opus · xhigh,
> run opus · high in tier mode; Codex execution and research: the label step 3 shows there;
> Codex planning and review: the tier nearest to its model · effort); the `easy` columns of
> step 3 (a family the config does not list copies its `mechanical` cell).

Moving the relabel into `sae setup show` (like the schema-1 conversion) would cut more. But no
pending job owns `setup_mode.py`, so that is a backlog item.

### 7. shape.md stakes question: shorten — open, wording only

Lines 29–32. STAKES-IN-PROMPTS makes `sae status` print the profile path, so "(the main
worktree's copy)" can go. Saves 1 line. Touches [STAKES-ASK].

> - when `sae status` shows `stakes: not set`, one question: a draft of the Stakes section
>   (`templates/repo/profile.md`) from AGENTS.md or CLAUDE.md and the README. Write the answer,
>   or on a skip the template's "not set" line, to the profile path `sae status` names.

### 8. Two lists of the final report — open, wording only

`interaction-modes.md` 56–58 and `execute.md` 171–173 both list what the final report holds.
They have already drifted: interaction-modes has no dropped jobs and no overridden gates.
execute.md must keep its list ([LET-GO-REPORT]). Replace interaction-modes 56–58 with: "Nothing
reaches the base branch without the user. The final report lists every `[agent]` decision and
everything else to check before merging (execute.md, "Finish", step 3), so the user reviews
them first." 0 lines; one home.

### 9. reviewer.md Output: one line shorter — optional, wording only

Lines 59–64. The severity values are already in the template. Keeps the approved meaning:

> Output (template `templates/review.md`): frontmatter `target` and `verdict`, then each
> finding in the template's fields. `Expected` is what the fix must make true; `Suggested fix`
> is a proposal, and a change of approach when patches would not converge. When the broken
> rule applies in more places, search for them and list them under `Also in`. Short and
> concrete.

### 10. Routing tables: the second value in a cell — open, spec change: owner decides

The owner reads routes in the viewer, so only the hidden second value matters. Each cell
stores a tier and a model · effort, and the "tiers in cells" switch picks one
(`config.py cell_use`). This is older than the change. The change made it worse: with the
mechanical relabel, several Claude cells now hold a model · effort that is another tier (for
example `L3 · sonnet · high`, where sonnet · high is L2). [TIERS-FOLLOW-DIFFICULTY] requires
both values in every cell, and it requires each cell to keep its model · effort. Any one-value
cell changes that requirement. No more analysis here, as the owner asked.

## Keep as is

- planner.md (shared-rule owner, stakes line, four difficulties): the owner approved them, or
  [DIFF-GUIDANCE] asks for one line each. There is no shorter wording with the same meaning.
- reviewer.md stakes grading (66–70) and the Approach proposal judgment: approved meaning;
  [FIX-WORKER] wants it in reviewer.md.
- worker.md 27–35 and 72–76: [FIX-WORKER] and [RESULT-SECTIONS]; already short.
- execute.md Decision flow step 2 (100–105): [DECISION-ANYTIME] asks for the examples.
- execute.md Finish steps 2–3: [LET-GO-REPORT] and [ACCEPT-INTEGRATION] ask for them.
- The templates (review fields, the profile Stakes example, "Delete when it does not apply"):
  approved texts, or the fix of a finding. They are read only by the agent that fills them.
- prompts.py constants: approved wording, printed only when wired.
- setup.md "5. Harness permissions": the spec drafted it; it is read in setup only.

## Verdict

The subagent text and the templates are lean, and most of their wording is owner-approved. The
weight was in the orchestrator's mode files. Two review fix rounds made them spell out branch
logic (which job, which status, which mode, which command) that `sae` can decide exactly at the
moment it applies. The one thing that matters most: WRITER-LAUNCH prints the fallback rule for
the case at hand, and execute.md, plan.md and shape.md keep one pointer sentence. With
proposals 2 and 3, this takes the orchestrator files from +54 to about +16 lines.
