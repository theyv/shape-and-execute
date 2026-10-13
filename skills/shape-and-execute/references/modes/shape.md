# Shape: from a rough note to an approved intent and spec

Phase `shaping`. You are the main session. Goal: an approved `intent.md` and `specs.md` that a
planner can use without asking the user anything.

Keep the start short and concrete. The deep work comes after research.

## 1. Intake

1. `sae new "<short title>"`. For a backlog item: `sae new "<short title>" --from <file>`;
   the item becomes `intent.md`. Note the task ID.
2. Give the user the viewer link that `sae new` prints. When it prints a start command
   instead (a sandbox without local sockets), give the user that command for their own
   terminal; in Codex, also suggest running Codex with full access (`--yolo`).
3. Write `intent.md` at once from the user's note. Keep every detail; cut repetition and
   filler. Short sentences. Use the template sections; delete empty ones. A backlog item's
   intent is already written, but it may be outdated: check it against the code in step 5.
4. Show the settings card (`sae status <task>`) with one sentence about the interaction mode:
   what it lets agents decide alone during execution, and that the user can change it any
   time (in the chat, or in the viewer).
5. Read the repository instructions (AGENTS.md, CLAUDE.md) and `.tasks/repo/profile.md` if
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
3. `sae next <task>` prints the next-step card for the batch. Show it and wait (ok, change,
   refine first, skip).
4. For each job: `sae dispatch <task> <TOPIC-ID>`, then spawn a subagent with the printed
   prompt, model and effort. Run them in parallel.
5. Use the wait:
   - ask for settings changes: interaction mode, levels for planning, execution and review,
     review points and provider. Apply what the user asks with `sae set`;
   - ask grill questions that do not depend on the research.
6. When a subagent finishes: `sae collect <task> <TOPIC-ID>` (add `--tokens`, `--duration-s`
   and `--agent-ref` when your harness reports them). Read the report.
7. Follow-up questions — the ones you have after putting the reports together, or later during
   grilling — go to the research agent that holds the context:
   - write them under `## Follow-up questions` in that topic's job file;
   - `sae dispatch <task> <TOPIC-ID> --resume --reason "follow-up questions"`;
   - resume that agent with the printed message (Claude Code: SendMessage; Codex: send_input
     or followup_task). If it cannot be resumed, spawn a new one with the same message;
   - collect again.

## 4. Spec

Always write `specs.md` (template `templates/specs.md`); it is the only place for requirement
IDs. For a small task, keep only the sections with content, often Summary, Requirements and
Decisions.

- Requirements get semantic IDs: `### [CLAIM-STATUS] Show current claim status`, each with
  acceptance checks.
- Describe final behavior, not implementation.
- Decisions: `### [DECISION-...]` with decision, reason, basis and `[human]`, `[agent]` or
  `[joint]`. Quote the user's words where they carry the "why": decision records are drafted
  from them later.
- Research basis: link the reports that support decisions. Do not copy them.
- No traceability table: `sae check` computes coverage.
- Mockups and throwaway prototypes for this task go to `.tasks/<task-id>/prototypes/`, never
  into the repository.

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

**Task difficulty.** Before the first review or planner dispatch, set the task's size and risk:
`sae set <task> task-difficulty=hard` for a large or risky task (default `normal`). The spec,
plan and integration reviews and the planner run on it; the next-step card shows it, and the
user may change it there. For a small task, also propose the review points `spec` off and
`plan` on: the plan review sees the spec and the jobs together. Change them only on the
user's word (`sae set`).

## 6. Spec review (when `spec` is a review point)

When grilling is done: `sae check <task>`. A clean check makes `REVIEW-SPEC` due.
`sae next <task>` prints its next-step card: show it and wait (ok, change, refine first, skip;
skip turns the `spec` review point off with `sae set`). Then `sae dispatch <task> REVIEW-SPEC`
and spawn a subagent with the printed prompt, model and effort. When the printed output is a
COMMAND (review in the other harness), run it in the background; when it fails, run the
IF IT FAILS line printed with it. Collect it.

Turn its findings into the last grill round: for each, say whether you would change the spec
and why. The user decides. Update `specs.md` and `intent.md`. The verdict never blocks the
gate, and there is no second review unless the user asks for one.

## 7. Approval

When the user approves: `sae approve <task> spec` (it refuses while a due `REVIEW-SPEC` is not
collected). Then load [plan.md](plan.md) — planning phase, plan gate and decision-record
drafts.
