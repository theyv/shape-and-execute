# Plan: planning phase and plan gate

Phase `planning`. You are the main session. Goal: an approved plan that fresh workers can
execute.

## 1. Who plans

- **Planner subagent** when the task will likely have two or more jobs, or when shaping went
  deep: `sae job add <task> PLAN --kind planning` (its difficulty is the task difficulty).
  `sae next <task>` prints the next-step card: show it and wait (ok, change, refine first, skip;
  skip means you plan inline). Then `sae dispatch <task> PLAN` and spawn a subagent with the
  printed prompt, model and effort. Collect it when it returns.
- **Inline** for a small task (one or two jobs, shallow shaping): load
  [roles/planner.md](../roles/planner.md) — how to design the graph and write job files —
  and plan yourself.

## 2. Light review

Check the result without redoing it:

- `sae check <task>` passes with no errors (every requirement is covered);
- the intent survives: no job drifts away from why the task exists;
- the decomposition makes sense: no agents for show, no job that mixes many domains;
- the riskiest assumptions are listed in `plan.md`.

For changes, resume the planner (`sae dispatch <task> PLAN --resume --reason "<feedback>"`,
send the printed message), then check again.

## 3. Plan review (when `plan` is a review point)

A clean `sae check` makes `REVIEW-PLAN` due. `sae next <task>` prints its next-step card: show it
and wait (skip turns the `plan` review point off with `sae set`). Dispatch it. When the printed
output is a COMMAND (review in the other harness), run it in the background; when it fails,
run the IF IT FAILS line printed with it. Collect it; `sae` reads the COMMAND's tokens itself.

For `changes-required`, resume the done planner:
`sae dispatch <task> PLAN --resume --reason "plan review: changes required"`, send the printed
message, collect `PLAN` again, then check again. The planner checks each finding first and
lists the ones it believes wrong under `## Disputed findings` in its result. Bring each
disputed finding to the plan gate with your view; the user settles it. Log the outcome:
`sae log <task> decision "<finding>: <outcome>" --by human`.

## 4. Plan gate

1. `sae view <task> --open` — the viewer opens the Plan tab: graph, jobs, review marks,
   assumptions, settings. When it prints a start command instead, give it to the user (in
   Codex, also suggest full access, `--yolo`).
2. In the chat, give a short summary:
   - the topology and why, in 2–4 lines;
   - the riskiest assumptions made instead of the user;
   - disputed findings of the plan review, with your view;
   - jobs without `verify` (a `sae check` warning): only judgement checks them, so name them
     and offer to flag them for review;
   - the settings card with its current values: "ok, or change something?";
   - holds: the user may stop execution after any job to look at its result
     (`sae hold <task> <ID>`, or the viewer);
   - the quote review (SKILL.md, "Quote review at approvals");
   - where execution should run: a fresh session after deep shaping or a long conversation,
     in either harness; this session for a small task.
3. Apply changes: settings with `sae set`; plan changes through the planner, or yourself
   when you planned inline.
4. On approval: `sae approve <task> plan`.
5. Draft decision records while the conversation is still in your context (below).

## 5. Decision-record drafts

Put each piece of "why" knowledge in the place that fits its reach:

- one file → a short comment in that file;
- one directory → that directory's `AGENTS.md`;
- cross-cutting, or a rejected option that someone will propose again → a decision record.

A record must pass the test: without it, an agent would "fix" something on purpose, or bring
back a rejected option. Usually zero to three per task.
Sources: this conversation, `intent.md`, the spec's decisions, the research reports. Quote the
user's words where they carry the "why", smoothed (SKILL.md, "Smooth every quote").

For each: `sae adr new <task> "<title>" --type architecture|business --applies-to <paths>`,
then write the draft that it prints the path of. Drafts wait in `.tasks/adr/` for triage; they
never block the run.

## 6. Hand-off

- **Fresh session:** ask the user to clear the context (`/clear` in Claude Code, `/new` in
  Codex) and then send `/shape-and-execute execute <task-id>` (Claude Code) or
  `$shape-and-execute execute <task-id>` (Codex). The other harness works too:
  `sae start <task> --harness codex|claude` records the switch. The session may stay in this
  checkout: `sae start` creates the task worktree and leaves this checkout as it is.
- **This session:** load [execute.md](execute.md) — the orchestration loop — and start.
