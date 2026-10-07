# Shape: from a rough note to an approved intent and spec

Phase `shaping`. You are the main session. Goal: an approved `intent.md` (and `specs.md` when
needed) that a planner can use without asking the user anything.

Keep the start short and concrete. The deep work comes after research.

## 1. Intake

1. `sae new "<short title>"`. For a backlog item: `sae new "<short title>" --from <file>`;
   the item becomes `intent.md`. Note the task ID.
2. Write `intent.md` at once from the user's note. Keep every detail; cut repetition and
   filler. Short sentences. Use the template sections; delete empty ones. A backlog item's
   intent is already written, but it may be outdated: check it against the code in step 3.
3. Read the repository instructions (AGENTS.md, CLAUDE.md) and `.tasks/repo/profile.md` if
   they exist. Look at the code area the note names, only enough to ask good questions.

## 2. First round

Ask one round in the grill format ([grill.md](../grill.md) — question format and rules). It has:

- 2–4 questions about intent, scope or success that the repository cannot answer;
- a **depth proposal** in one sentence with its reason:
  - "Grill only" — the area is familiar and the outcome is clear;
  - "Research: <topic>, <topic> at level <research level>" — there is an unknown external API
    or library, unclear user-facing behavior, several sensible architectures, an unfamiliar
    code area, or domain knowledge outside the repository.

If the user asked for a quick run, propose grill only.

After every answer round, update `intent.md`. Move resolved items out of "Open questions" and
"Nice to have" into the right sections.

## 3. Research (only when agreed)

1. One research job per distinct unknown. Usually 2–5; one is enough when the task is hard in
   orchestration rather than in knowledge.
   `sae job add <task> <TOPIC-ID> --kind research --difficulty normal|hard`
2. Fill `jobs/<TOPIC-ID>.md`: the questions, what is already known, the limits.
3. For each job: `sae dispatch <task> <TOPIC-ID>`, then spawn a subagent with the printed
   prompt and model. Run them in parallel.
4. Use the wait:
   - show the settings card (`sae status <task>`) and ask for changes: interaction mode,
     levels for planning, execution and review, review points and provider. Apply them with
     `sae set`;
   - ask grill questions that do not depend on the research.
5. When a subagent finishes: `sae collect <task> <TOPIC-ID>` (add `--tokens`, `--duration-s`
   and `--agent-ref` when your harness reports them). Read the report.
6. Follow-up questions — the ones you have after putting the reports together, or later during
   grilling — go to the research agent that holds the context:
   - write them under `## Follow-up questions` in that topic's job file;
   - `sae dispatch <task> <TOPIC-ID> --resume --reason "follow-up questions"`;
   - resume that agent with the printed message (Claude Code: SendMessage; Codex: send_input
     or followup_task). If it cannot be resumed, spawn a new one with the same message;
   - collect again.

## 4. Spec

Write `specs.md` (template `templates/specs.md`) when shaping went deep or exact contracts
matter: APIs, rules, data, permissions. Otherwise put acceptance criteria into `intent.md`
under `## Acceptance` and skip the spec.

- Requirements get semantic IDs: `### [CLAIM-STATUS] Show current claim status`, each with
  acceptance checks.
- Describe final behavior, not implementation.
- Decisions: `### [DECISION-...]` with decision, reason, basis and `[human]`, `[agent]` or
  `[joint]`.
- Research basis: link the reports that support decisions. Do not copy them.
- No traceability table: `sae check` computes coverage.

## 5. Grill the draft

Run grill rounds on the draft until nothing important is open. After each round update
**both** `specs.md` and `intent.md`, so they agree. At the end, "Open questions" holds only
what cannot be answered before execution, or what the user leaves open on purpose.

When grilling reveals a new unknown, propose more research.

**Offer a split only when you would guess.** When a whole area of the spec depends on code
that this task will create, so that you could only guess it today, offer a split: spec now
what you know, and put the guessed area into the backlog. Example: sign-in, sign-up and
password reset can all be specified today, so auth stays one task; billing in a new
application would guess the data model that the core will set, so it waits. The user decides.
One task with a huge graph is always allowed. Offer it at the latest before approval; after
approval nothing is split.

**Deferred work goes to the backlog.** When the user moves something out of this task for
later (a cut, or an accepted split): `sae new "<title>" --backlog --source <task>`. Write its
intent from what is known, keeping the user's details. Add `## Related tasks` in prose when it
builds on this task ("Builds on <task-id> — start after it is merged"), and a line about it in
this task's intent. In the spec, "Out of scope" names the backlog item; what the user rejects
goes there without one.

Before approval, list your riskiest `[agent]` assumptions: the ones you made instead of the
user.

## 6. Spec review (when `spec` is a review point and `specs.md` exists)

When grilling is done: `sae check <task>`. A clean check adds `REVIEW-SPEC`.
`sae dispatch <task> REVIEW-SPEC`, then spawn a subagent with the printed prompt and model.
When the printed output is a COMMAND (review in the other harness), run it in the background;
when it fails, run the IF IT FAILS line printed with it. Collect it.

Turn its findings into the last grill round: for each, say whether you would change the spec
and why. The user decides. Update `specs.md` and `intent.md`. The verdict never blocks the
gate, and there is no second review unless the user asks for one.

## 7. Approval

When the user approves: `sae approve <task> spec` (it refuses while a due `REVIEW-SPEC` is not
collected). Then load [plan.md](plan.md) — planning phase and plan gate.
