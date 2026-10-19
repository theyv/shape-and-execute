# Index: shape-and-execute

Read this index first, then open only the records you need. One line per file: a link and its
decision in one sentence. Whoever writes a record adds its line here.

- [Intent: shape-and-execute](_intent.md) — Why the skill exists, what it must do, the owner's assumptions and roughly how it works; read it first.
- [Big work goes lazily through the backlog](2026-10-06-big-work-goes-lazily-through-the-backlog.md) — Very large work is not planned up front; deferred parts wait in the backlog as intents and get their spec when picked up.
- [Explicit invocation only](2026-10-06-explicit-invocation-only.md) — Only the user's explicit call starts the skill, in Claude Code and in Codex.
- [Follow PROSE without ceremony](2026-10-06-follow-prose-without-ceremony.md) — The skill follows PROSE where it adds no step to a run: router links, one-deliverable jobs, pointer prompts, hard stops.
- [No configuration in the skill and sae fails loudly](2026-10-06-no-configuration-in-the-skill-and-sae-fa.md) — The skill ships no config values; `sae` reads only the user config and exits 2 when something is missing, which leads to setup.
- [One skill with five modes](2026-10-06-one-skill-with-five-modes.md) — Shape, plan, execute, setup and triage are modes of one skill, each with one reference loaded only when needed.
- [Relations between tasks are prose](2026-10-06-relations-between-tasks-are-prose.md) — Relations between tasks are an optional prose section in the intent, with no fields or order checks.
- [Repository facts live under the tasks folder](2026-10-06-repository-facts-live-under-the-tasks-fo.md) — Repository facts live in `.tasks/repo/`, and the skill puts nothing in the repository root.
- [Split offer, one question and never forced](2026-10-06-split-offer-one-question-and-never-force.md) — One task of any size is the default; the agent offers a split only when it would have to guess a whole area of the spec.
- [The orchestrator never implements](2026-10-06-the-orchestrator-never-implements.md) — The orchestrator never implements, and any session can continue a task from its files.
- [The task record is untracked while it runs and committed whole at finish](2026-10-06-the-task-record-is-untracked-while-it-ru.md) — The task folder stays untracked during the run and is committed whole once, at `sae finish`.
- [Without git, offer git init and no snapshots](2026-10-06-without-git-offer-git-init-and-no-snapsh.md) — Without git the skill offers `git init`; if declined, the task runs without a safety net.
- [Worktrees live in a persistent user cache](2026-10-06-worktrees-live-in-a-persistent-user-cach.md) — Worktrees live in a configurable per-user cache folder.
- [Jobs merge into the task branch and the owner merges the task](2026-10-07-jobs-merge-into-the-task-branch-and-the.md) — Each job merges into the task branch once done and reviewed, and the owner merges the task branch.
- [No fits-one-session prompt at intake](2026-10-07-no-fits-one-session-prompt-at-intake.md) — Intake does not ask whether a task fits one session; a small task gets a short spec and one worker.
- [One list of hard stops for every mode](2026-10-07-one-list-of-hard-stops-for-every-mode.md) — Hard stops hold in every mode and live only in `references/interaction-modes.md`.
- [Cheap decisions that keep the door open for teams](2026-10-10-cheap-decisions-that-keep-the-door-open.md) — Relative paths, schema versions, task authors and per-attempt model traceability keep the door open for teams.
- [Decision records are drafted where the context is fresh and accepted in triage](2026-10-10-decision-records-are-drafted-where-the-c.md) — Shaping and execution draft decision records into `.tasks/adr/`, and triage accepts or rejects them.
- [Every subagent gets an explicit effort](2026-10-10-every-subagent-gets-an-explicit-effort.md) — `sae dispatch` prints model and effort for both harnesses, and the orchestrator sets them exactly as printed.
- [Every task executes in its own task worktree](2026-10-10-every-task-executes-in-its-own-task-work.md) — `sae start` creates a task worktree on the task branch and never switches the owner's checkout.
- [sae creates job worktrees from the task branch](2026-10-10-sae-creates-job-worktrees-from-the-task.md) — `sae` creates job worktrees from the task branch, only when writers run in parallel.
- [Agents file findings and the owner fills the backlog](2026-10-12-agents-file-findings-and-the-owner-fills.md) — Problems outside a job become findings, never side fixes, and work the owner defers becomes a backlog item.
- [Docs keep only the why](2026-10-12-docs-keep-only-the-why.md) — At release the design notes are removed and `docs/adr/` keeps only `_intent.md` and decision records.
- [Jobs never update design docs](2026-10-12-jobs-never-update-design-docs.md) — No job writes or re-syncs design docs; decisions reach `docs/adr/` through triage.
- [Model names only in the setup proposal and the Claude family list](2026-10-12-model-names-only-in-the-setup-proposal-a.md) — Model names appear only in the setup proposal text and in `sae`'s list of known Claude families.
- [Research notes follow their decisions](2026-10-12-research-notes-follow-their-decisions.md) — A research note stays in `research/` only when a kept decision record cites it.

## Research notes

Cited by the records above.

- [Claude Code facts](research/claude-code-facts.md) — Facts about Claude Code 2.1.290 collected 2026-10-06 from the official docs and the local CLI.
- [Codex facts](research/codex-facts.md) — Facts about `codex-cli 0.160.0` collected 2026-10-06 from the local CLI and the `openai/codex` source.
- [Nested worktrees and test runners](research/nested-worktrees-and-test-runners.md) — Whether tools run in the main checkout pick up job worktrees kept inside the repository.
- [PROSE review of the design](research/prose-spec.md) — A PROSE evaluation of the early design summary and what the design took from it.
- [Wayfinder (mattpocock/skills)](research/wayfinder.md) — How the `wayfinder` skill handles work too big for one session, drift and out-of-scope work.
