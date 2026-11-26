# Prompt review (Opus): PROMPT-TEXT, PROMPT-LEAN and EASY-DIFFICULTY

Range: `3892f20..3fb7bd0`, without `.tasks`. Yardsticks: the `agentic-systems-guidelines` skill
(CORE-1, CORE-2, WRITE-1, ORC-1, ORC-4) and `docs/adr/_intent.md`. Read-only review.

## Verdict

Mostly yes. The role texts and templates are lean and say what the spec asks. The mode files
now hold pointer sentences where `sae` will print the rule, which is the right home ("deterministic
where it must be exact"). Three things need fixing before the code jobs run: the term "stakes"
has two meanings for the orchestrator and no definition for other agents; FINAL-VALIDATION will
mark PROMPT-LEAN's accepted text as a failure; and the rules cut from the mode files reach the
code jobs only through an Inputs pointer, so nothing checks that `sae` prints them. The
EASY-DIFFICULTY code is correct as far as I traced it. Its tests pass (33 in 4 modules).

## The stakes question

**Answer: no, not for sure.** A reviewer or planner will usually guess right when the stakes
come from the profile. In every other case it has to guess.

Evidence, traced end to end:

1. **The prompt line.** After STAKES-IN-PROMPTS, every prompt carries `prompts.py:27`
   `Stakes (read before you start): {path}, section "Stakes"`, or `prompts.py:28-29`
   `Stakes: not set. Estimate them from the repository instructions and the README, and work to
   that level: neither over- nor under-engineer.` Neither line says what stakes are. The first
   line says only "read it".
2. **What the agent then reads.**
   - Source = profile: `templates/repo/profile.md:14-30`. The comment defines it: "Why the
     project exists and how much care it needs." The five labels and the example make it
     clear. This case works.
   - Source = AGENTS.md or CLAUDE.md: only what the owner wrote under `## Stakes`. The
     template comment is not there. No definition.
   - Not set: no section at all. "Estimate them" has no referent: the agent does not know the
     five questions it should estimate.
3. **Role files.** No role file defines the term. `reviewer.md:65-69` uses it ("Grade every
   finding against the stakes in your prompt", "needs more care than the stakes justify").
   `planner.md:26-27` uses it. `worker.md`, `research-worker.md`, `decision-worker.md` and
   `integration-worker.md` never mention stakes. So a worker gets "read before you start" and
   no rule for what to do with it. The spec says workers "size their work" ([STAKES-VIEWER]).
4. **The orchestrator has a different definition.** `SKILL.md:18` defines **stakes** as "the
   task's settings: levels per phase and review". The spec's Domain language defines Stakes as
   the project's `## Stakes` section, which *sets* the level of care. `execute.md:55-56` then
   says "triage against the stakes", with no pointer to a section. The orchestrator gets no
   dispatch prompt, so its only definition is SKILL.md's. It can let a finding go because the
   review level is `economy`. See finding 1.
5. **Two copies in one prompt.** A writer's prompt points to the repo profile in the task
   worktree (`prompts.py:256`, `tasks_dir(task.root)`), and the stakes line points to the copy
   in the home checkout ([STAKES-LOOKUP]). The profile is tracked in git. A viewer edit during
   execution, or a shaping answer that was never committed, exists only in the home copy. The
   worker then sees two different `## Stakes` sections. When the stakes come from AGENTS.md,
   the worktree profile shows an empty section next to the "A toy" example. See finding 4.

**Smallest fix:** define the term in the one line every prompt carries, and say which copy
wins. This is one home for the definition (CORE-2) and covers every role and every source.

```python
STAKES_LINE = ('Stakes — how much care this project needs; plan, build and review to that level. '
               'Read this copy, not another: {path}, section "Stakes"')
STAKES_NOT_SET_LINE = ("Stakes — how much care this project needs: not set. Estimate them from the "
                       "repository instructions and the README (who uses it, acceptable breakage, "
                       "what matters now), and work to that level: neither over- nor under-engineer.")
```

Plus two orchestrator lines (finding 1). Carrier: a new prompt fix, because STAKES-IN-PROMPTS
says "Do not reword the constants". The cheapest way: lift that boundary for these two
constants in `jobs/STAKES-IN-PROMPTS.md`, with the text above.

## Findings

### 1. "Stakes" has two meanings for the orchestrator — blocking

- **File:** `SKILL.md:18`; `references/modes/execute.md:55-56`.
- **Breaks:** WRITE-1 (one term, one meaning); spec Domain language "Stakes"; [TRIAGE] ("the
  same bar" as the reviewer).
- **Expected:** the orchestrator triages against the project's Stakes section, the same bar the
  reviewer used.
- **Actual:** SKILL.md, which every run loads, says stakes are "the task's settings: levels per
  phase and review". execute.md says "triage against the stakes" and names no source. The
  orchestrator can triage against the review level.
- **Note:** the owner accepted audit proposal 4 ("one axis at two scopes"). The wording does
  not say that. It says the settings *are* the stakes; `_intent.md` says "stakes set the
  settings".
- **Suggested fix:** `SKILL.md:18`:
  `jobs) and **stakes** (how much care the project needs, in its Stakes section; the task's settings follow them: levels per phase and review). A small task is`
  `execute.md:55-56`:
  `Otherwise triage against the stakes (the Stakes section that `sae status` names): a finding that needs more care than they justify is`
- **Carrier:** needs a new prompt fix.

### 2. FINAL-VALIDATION will fail PROMPT-LEAN's accepted text — blocking

- **File:** `jobs/FINAL-VALIDATION.md:31-32`.
- **Breaks:** owner decision on audit proposals 1–9.
- **Expected:** the validator accepts the spec drafts, PROMPT-TEXT's contradiction fixes and
  PROMPT-LEAN's edits.
- **Actual:** it checks "no text beyond the spec drafts and the contradiction fixes listed in
  `jobs/PROMPT-TEXT.result.md`". PROMPT-LEAN replaced the drafted execute.md step 2 and step 3,
  plan.md, shape.md, setup.md step 1, interaction-modes.md and reviewer.md Output. PROMPT-TEXT's
  result still says SKILL.md uses "care". The validator must report these as failures, and the
  orchestrator then adds fix jobs that restore the cut text.
- **Suggested fix:** `- Check that the prompt files contain no text beyond the spec drafts, the
  contradiction fixes in `jobs/PROMPT-TEXT.result.md`, and the edits in
  `jobs/PROMPT-LEAN.result.md` (audit proposals 1–9).`
- **Carrier:** edit `jobs/FINAL-VALIDATION.md` before it runs (orchestrator, no prompt fix).

### 3. Cut rules reach the code jobs only through an Inputs pointer — major

- **File:** `jobs/WRITER-LAUNCH.md:38-41` vs Scope 49-56 and Validation 82-92;
  `jobs/FIX-LOOP-EXITS.md:42-44` vs Scope and Validation 82-95;
  `jobs/FIX-LOOP-GUIDANCE.md:32-35` vs Scope 37-51 and Validation 63-69.
- **Breaks:** ORC-4 (done is checked, not reported); the brief's rule that a cut rule must not
  get lost.
- **Expected:** each rule PROMPT-LEAN cut is in the Scope or the Validation of the job that
  prints it, so the job's own checks fail when it is missing.
- **Actual:** every cut rule has a carrier, but only inside the audit block that Inputs points
  to. Scope and Validation do not name these items:
  - WRITER-LAUNCH: the "how to run" line printed with every COMMAND (in the background, in a
    shell, not as a subagent, no `--tokens`). This replaces the cut "run it in the background".
    Also the branch for a done research or planning job ("the job stays done; do not park
    it"), and the per-branch tests.
  - FIX-LOOP-EXITS: the lead line "Triage first", the printed `--let-go` line, and the fresh
    `-FIX-<n>` (today `apply_review` always prints `-FIX-1`, and round 2 fails on a duplicate
    ID). Its test asserts the four lines.
  - FIX-LOOP-GUIDANCE: the park opening "Add no fix job and accept nothing before the user
    answers: a fix job unparks the job", and the `sae collect` line for an Approach proposal.
    `execute.md:5-6` and `:63-64` rely on that line.
  - FINAL-VALIDATION does not check that the cut rules are printed.
- **Also in:** none found beyond these four files.
- **Suggested fix:** copy each audit block's "Validation:" sentence into the job's Validation
  list, word for word. Add to FINAL-VALIDATION Scope: "For each rule PROMPT-LEAN cut (audit
  proposals 1–3), run the case in a scratch task and confirm `sae` prints it."
- **Carrier:** WRITER-LAUNCH, FIX-LOOP-EXITS, FIX-LOOP-GUIDANCE, FINAL-VALIDATION (job file edits
  by the orchestrator before dispatch).

### 4. The stakes line neither defines stakes nor says which copy wins — major

- **File:** `scripts/sae_lib/prompts.py:27-29`; `prompts.py:256` and `:287` (profile pointer in
  the task worktree); `templates/repo/profile.md:15-25`.
- **Breaks:** [STAKES-LOOKUP] (the home copy is the source); [STAKES-POINTER]; the spec's
  "planners and workers size their work".
- **Expected:** every agent knows what stakes are, what to do with them, and reads the home
  copy.
- **Actual:** see "The stakes question", points 1–3 and 5. Workers, research, decision and
  integration workers get no use rule. With AGENTS.md as the source, or when not set, nothing
  defines the term. The writer and planner prompts point to two profile copies that can differ.
- **Suggested fix:** the two constants in "The stakes question" above.
- **Carrier:** STAKES-IN-PROMPTS, if the owner lifts its "Do not reword the constants" boundary
  for these two lines; otherwise a new prompt fix.

### 5. A decision job for a review round or a done job points to a missing section — major

- **File:** `scripts/sae_lib/prompts.py:346-348`; `jobs/FIX-LOOP-EXITS.md:8-20` (scope).
- **Breaks:** [DECISION-ANYTIME]; "a role told to do something it cannot see".
- **Expected:** a decision job made with `--from <review round>`, `--from <done job>` or
  `--question` points to the round, the job or the question.
- **Actual:** `build_prompt` always adds `Decision request (section "Decision request")` of the
  target's result whenever the target is a job. A done result has no such section (the template
  now says to delete it). PROMPT-TEXT listed this under Contradictions. FIX-LOOP-EXITS owns
  decision jobs, but `prompts.py` is not in its scope, and no other pending job names it. The
  decision worker is sent to a section that does not exist.
- **Suggested fix:** add `prompts.py` to FIX-LOOP-EXITS scope (it runs after WRITER-LAUNCH and
  STAKES-IN-PROMPTS, before FIX-LOOP-GUIDANCE, so the order holds). Scope line: "The decision
  prompt points to the parked job's Decision request, the review round's review file, or the
  question in the job file, whichever applies." Validation: a test for each of the three.
- **Carrier:** FIX-LOOP-EXITS (job file edit).

### 6. The inline planner has no prompt to read stakes from — minor

- **File:** `references/roles/planner.md:26-27`; `references/modes/plan.md:14-16`.
- **Breaks:** "a role told to do something it cannot see".
- **Expected:** an orchestrator that plans a small task inline finds the stakes.
- **Actual:** "Match the care in the plan to the stakes in your prompt". Inline, there is no
  dispatch prompt.
- **Suggested fix:** `- Match the care in the plan to the stakes (your prompt names them; when
  you plan inline, the section `sae status` names): add a job, check or safeguard only when
  the stakes justify it.`
- **Carrier:** needs a new prompt fix.

### 7. "Stakes line" and "below/beyond the stakes" in the review template — minor

- **File:** `templates/review.md:12`, `:18`.
- **Breaks:** WRITE-1.
- **Expected:** one phrase per meaning.
- **Actual:** `**Breaks:** <REQ-ID, intent or stakes line>` means a bullet of the Stakes
  section. The spec uses "stakes line" for the prompt's pointer line ([STAKES-POINTER]), and
  the prompt line starts with "Stakes". A reviewer may cite the pointer. The Notes comment says
  "A finding below the stakes" for the `[beyond stakes]` tag; reviewer.md says "needs more care
  than the stakes justify". "Below" and "beyond" point in opposite directions for one idea.
- **Suggested fix:** `**Breaks:** <REQ-ID, intent or a Stakes bullet>: how this contradicts it`
  and `<!-- Remarks that do not block. A finding that needs more care than the stakes justify:
  `[beyond stakes]` and one sentence why. -->`
- **Carrier:** needs a new prompt fix.

### 8. "Blocks" vs severity `blocking`, and "report everything" vs the spec-review filter — minor

- **File:** `references/roles/reviewer.md:65-67`; `:32-34`.
- **Expected:** the reviewer knows what the stakes change and that the spec-review filter still
  holds.
- **Actual:** "the stakes decide only whether it blocks" can read as "decide the severity
  `blocking`". The intended meaning is "Findings or Notes". "Report everything you find" sits
  below the spec-target rule "Report a gap only when the scenario is realistic for the intent".
- **Suggested fix:** `Grade every finding against the stakes. They decide only where it goes:
  Findings, or Notes as `[beyond stakes]` with one sentence why; never drop it.`
- **Carrier:** needs a new prompt fix.

### 9. The approach paragraph is wrong for the integration — minor

- **File:** `scripts/sae_lib/prompts.py:33-42`.
- **Expected:** the text fits a job and the integration.
- **Actual:** "The job parks for the owner" and "read the earlier review rounds of this job".
  For an integration fix the task parks, and the rounds are integration rounds. "Answer in
  your result" names no section; the result template has none for these answers. PROMPT-TEXT
  flagged the first part; FIX-LOOP-GUIDANCE may not reword it. The owner approved the wording.
- **Suggested fix:** `FIX {fix} of {target}. {target} parks for the owner after review round
  {max_rounds}.` and `read the earlier review rounds of {target} and answer under "Decisions
  taken" in your result:`
- **Carrier:** needs a new prompt fix (owner's call: approved wording).

### 10. The example in the profile is read on every job — minor (leanness)

- **File:** `templates/repo/profile.md:15-25`.
- **Expected:** text that every agent reads carries only what every agent needs (CORE-1).
- **Actual:** writer, research and planner prompts point to the profile. Each reads a 10-line
  comment with the toy example, even when the stakes come from AGENTS.md. With an empty section,
  a hasty reader may take the example as the stakes.
- **Suggested fix:** none required; [STAKES-TEMPLATE] asks for the example in the template.
  Once finding 4's line says which copy to read, the risk is small. Keep it.
- **Carrier:** none; owner-approved.

### 11. setup.md points at a draft that does not work — minor

- **File:** `references/modes/setup.md:172-173`.
- **Actual:** "`sae setup snippets` prints a draft of it; its Codex git rule does not work in
  linked worktrees yet." This invites the agent to offer a broken snippet in setup.
- **Suggested fix:** `A sandboxed setup waits in the backlog.`
- **Carrier:** needs a new prompt fix.

### 12. The empty test for a Stakes section assumes the bullet form — minor

- **File:** `jobs/STAKES-IN-PROMPTS.md:36-37`; `references/modes/shape.md:29-31`.
- **Actual:** shaping writes the section by hand. "Empty when its five bullets have no value"
  does not say what happens when the agent or the owner writes prose instead of bullets, or
  removes a label.
- **Suggested fix:** in STAKES-IN-PROMPTS Scope: "A section is empty when, after HTML comments
  are stripped, only the five labels with no value, or nothing, remain. Any other text is
  content."
- **Carrier:** STAKES-IN-PROMPTS.

### 13. EASY-DIFFICULTY: small gaps in tests and output — minor

- **No test for the review-job refusal.** [DIFF-EASY] asks that `easy` is refused for planning
  *and review* jobs. `tests/test_easy_difficulty.py:52-66` covers planning (add and edit). It
  does not run `sae job edit` with `easy` on a spec, plan or integration review
  (`planning.py:265-267`). Carrier: FINAL-VALIDATION, or a line in a later job's tests.
- **A spurious settings change.** `control.py:105` adds "(mechanical cell)" to the snapshot.
  For a task that already runs, the first card after the upgrade lists the easy rows as a
  settings change (the job result says so). The spec does not ask for it. Acceptable; mention
  it to the owner.
- **Style:** `routing.py:246-248` has three blank lines before `easy_fallback_notice`.
  `cmd_status` loads the config a second time for the notice. Harmless.

## What is good and should stay

- Pointer sentences ("when it prints a COMMAND, follow what it prints") in place of branch logic
  in three mode files. The rule belongs in `sae`, printed only for the case at hand.
- `execute.md:53-55` keeps the one rule that must hold before `sae` prints anything: at the
  round limit the choice is the user's, and a drop needs the user's word.
- The finding shape (`Expected` binds, `Suggested fix` proposes, `Also in` by search) in
  `templates/review.md`, `reviewer.md` and `worker.md`: short, and the three files agree.
- `[PROMPT-SAE]` texts as named constants with their spec tags (`prompts.py:24-42`).
- "Delete when it does not apply" in `templates/job-result.md`.
- `planner.md`: the shared-rule owner and the four one-line difficulties.
- EASY-DIFFICULTY: `sae` writes no cell; `easy` falls back to the effective `mechanical` cell
  in one function (`config.effective_cell`), used by routing, validation, setup show and the
  viewer. The fallback is named on the card, in the ROUTING line, in `sae status` and in
  `sae doctor`. Older configurations still validate.
- `setup.md` tables match [TIERS-FOLLOW-DIFFICULTY], [EASY-UPGRADE] and the plan's Codex rule,
  cell by cell.
