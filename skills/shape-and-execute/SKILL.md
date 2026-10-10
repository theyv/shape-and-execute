---
name: shape-and-execute
description: "Shape a rough task into an approved intent, spec and job plan. Then run the plan with fresh worker agents, in parallel where this helps, with validation and adversarial review. Setup mode configures models and permissions. Triage mode turns collected findings and decision-record drafts into tasks, backlog items and documentation. Use only when the user explicitly calls shape-and-execute."
disable-model-invocation: true
metadata:
  version: "0.1"
---

# Shape and Execute

This skill takes a task from a rough note to a validated branch in three phases:

1. **Shape** — capture the intent, research what is unknown, grill the user, write the spec.
2. **Plan** — design a graph of jobs that fresh workers can do and check on their own.
3. **Execute** — dispatch the jobs, collect results, merge, review, validate, finish.

The skill scales by three things, each decided when the information exists:
**uncertainty** (grill only, or research first), **breadth** (one worker, or a graph of
jobs) and **stakes** (the task's settings: levels per phase and review). A small task is
`intent.md` and one or two jobs. A large task gets research, a spec, a planner, reviews and a
fresh session for execution. Work the user defers waits in `.tasks/backlog/` as an intent, and
gets its spec when someone picks it up.

Files are the memory. A fresh session can continue any task from its task folder; `sae` finds
it in any checkout of the repository.

## Pick the mode

When the user names an existing task, run `sae status <task>` first.

| The user wants | Load |
|---|---|
| a new task (a note or a backlog item), or to continue a task in phase `shaping` | [references/modes/shape.md](references/modes/shape.md) — intake, research, grilling, spec, spec review, spec approval |
| to continue a task in phase `planning` | [references/modes/plan.md](references/modes/plan.md) — planner, plan review, plan gate, decision-record drafts, hand-off |
| to execute a task (plan approved, or phase `executing`) | [references/modes/execute.md](references/modes/execute.md) — task worktree, orchestration loop, holds, decisions, finish |
| setup or model changes, or `sae` exited with code 2 | [references/modes/setup.md](references/modes/setup.md) — model lists, routing tables, harness permissions, repo profile |
| to review findings or decision-record drafts | [references/modes/triage.md](references/modes/triage.md) — picks one of the two queues |

Load only the reference for the current mode.

## The CLI: sae

All task state goes through `sae`, a Python script in this skill:

    python3 <SKILL_DIR>/scripts/sae.py <command> ...

`<SKILL_DIR>` is the folder that contains this file; Claude Code also provides it as
`${CLAUDE_SKILL_DIR}`. Never edit `state.json` or `events.jsonl` by hand. For a command or an
option that your mode reference does not show, run `sae --help` or `sae <command> --help`.

| Exit | Meaning | Do |
|---|---|---|
| 0 | ok | continue |
| 1 | usage or precondition error | read the message; fix the call or the precondition |
| 2 | user config missing, invalid or old | tell the user and offer setup mode |
| 3 | refused: lint, approval, review, hold, verdict or stale check | do what the message names |
| 4 | git problem: dirty tree, merge conflict, worktree or setup failure | read the message; a conflict added `INTEGRATE-<ID>` |
| 5 | re-run verify failed | resume the same worker with the printed command |

## Rules for every mode

- **Process map first.** Start each step's message to the user with the process map that
  `sae status` or `sae next` prints. You may annotate the current step (a grill round).
- **Model and effort exactly as printed.** This skill asks you to spawn subagents and to set
  the model and the reasoning effort of every one exactly as `sae dispatch` prints them
  (Claude Code: the Agent tool's `model` and `effort`; Codex: `model` and
  `reasoning_effort`). No subagent inherits your effort.
- **Launch cards.** Before a bigger launch, `sae next` prints a launch card. Where your mode
  reference says to wait, wait for one of: **ok** (dispatch); **change** (apply it, show the
  new card); **refine first** (improve the job files or the plan, then show it again);
  **skip** (do not launch it). Otherwise show it and continue.
- **Settings change only on the user's word.** Levels, routing, review points, overrides,
  holds: change them only when the user asks (`sae set`, `sae job override`, `sae hold`).
  `task-difficulty` is yours to set ([shape.md](references/modes/shape.md)). The next launch
  card lists every change.
- **Narrow output.** Show the user short blocks that fit 72 columns. Never relay a wide code
  block or a wide table.
- **Write it down.** Decisions, answers and changes go into the task files, not only into the
  chat. Tag each decision `[human]`, `[agent]` or `[joint]`.
- **Pointers, not pastes.** Give a subagent the prompt that `sae dispatch` prints. Do not add
  pasted file content to it.
- **Role protocols belong to subagents.** The files in `references/roles/` and
  `references/commit-message.md` are read by the subagent that the dispatch prompt points to.
  Do not load them yourself, except `roles/planner.md` when you plan a small task inline.
- **Never push**, deploy or touch the base branch. Commits happen only on task and job branches.
- **Languages.** Talk to the user in the conversation language from the user config. Write
  task files, code comments and commit messages in the artifact language; a repo pin in
  `.tasks/repo/profile.md` wins, and the repository's existing convention wins for code
  comments. When a translation would lose a nuance of the user's words, quote the original.
- **Plain words.** Write for agents in short sentences, one term per meaning (ASD-STE100 style).
- **Out of scope.** Problems and follow-up work that an agent finds become findings
  (`sae finding new`), never side fixes. Only the user puts work into the backlog.
- **Parked work does not stop independent work.**

## Invocation

Claude Code: `/shape-and-execute <note or backlog item>`, `/shape-and-execute continue <task>`,
`/shape-and-execute execute <task>`, `/shape-and-execute setup`, `/shape-and-execute triage`.
Codex: the same with `$shape-and-execute`.
