# Plan: planning phase and plan gate

Phase `planning`. You are the main session. Goal: an approved plan that fresh workers can
execute.

## 1. Who plans

- **Planner subagent** when the task will likely have two or more jobs, or when shaping went
  deep: `sae job add <task> PLAN --kind planning --difficulty hard`, then
  `sae dispatch <task> PLAN` and spawn a subagent with the printed prompt and model.
  Collect it when it returns.
- **Inline** for a small task (one or two jobs, shallow shaping): load
  [planner.md](planner.md) — how to design the graph and write job files — and plan yourself.

## 2. Light review

Check the result without redoing it:

- `sae check <task>` passes with no errors (every requirement is covered);
- the intent survives: no job drifts away from why the task exists;
- the decomposition makes sense: no agents for show, no job that mixes many domains;
- the riskiest assumptions are listed in `plan.md`.

For changes, resume the planner (`sae dispatch <task> PLAN --resume --reason "<feedback>"`,
send the printed message), then check again.

## 3. Plan review (when `plan` is a review point)

A clean `sae check` adds `REVIEW-PLAN`. Dispatch it. When the printed output is a COMMAND
(review in the other harness), run it in the background. When it fails (exit code, empty
result file; often a quota limit), re-dispatch with
`--provider <your harness> --resume --reason "provider failed: <message>"`. Collect it.
For `changes-required`, resume the planner with the findings and check again.

## 4. Plan gate

1. `sae view <task> --open` — the viewer opens the Plan tab: graph, jobs, assumptions,
   settings.
2. In the chat, give a short summary:
   - the topology and why, in 2–4 lines;
   - the riskiest assumptions made instead of the user;
   - the settings card with its current values: "ok, or change something?";
   - where execution should run: a fresh session after deep shaping or a long conversation;
     this session for a small task.
3. Apply changes: settings with `sae set`; plan changes through the planner, or yourself
   when you planned inline.
4. On approval: `sae approve <task> plan`.

## 5. Hand-off

- **Fresh session:** ask the user to clear the context (`/clear` in Claude Code, `/new` in
  Codex) and then send `/shape-and-execute execute <task-id>` (Claude Code) or
  `$shape-and-execute execute <task-id>` (Codex).
- **This session:** load [execute.md](execute.md) — the orchestration loop — and start.
