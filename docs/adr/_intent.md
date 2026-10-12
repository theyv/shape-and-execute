# Intent: shape-and-execute

The decisions behind this file are the records beside it. Read this file first, then the
records whose `applies-to` your change touches.

## Why it exists

Larger tasks with coding agents fail in predictable ways. The agent starts to build before the
owner knows exactly what they want; often the owner understands only the effect, not the way to
get there. One long session fills its context with research, dead ends and rejected ideas, and
later decisions inherit that noise. Work is either one huge thread ("vibe coding on YOLO") or
multi-agent theater: many agents, much coordination, little gain. Parallel agents collide on
shared files and shared assumptions. Months later nobody can tell what was intended, what was
decided, by whom, with which model, and why. And most workflows have one weight for every
task: small tasks drown in ceremony, big tasks get too little structure.

The owner named six problems (2026-10-07). Each one must stay solved:

1. **Scale.** Some tasks do not fit one context; after several compactions the context becomes
   imprecise. The skill keeps state in files and splits the work so that each unit fits a fresh
   context, for tasks from medium to "very large". A task that fits one context probably does not need the skill.
2. **Decomposition.** A model that must split a task and implement it at the same time cannot
   hold attention on both. A model whose only job is to split does it well. Split only when it
   is needed.
3. **Resumability.** After a clear or several compactions, the intent, the business problem,
   gets lost. Another agent, even another model or the other harness, must resume from the
   files alone, without the conversation.
4. **Orchestration efficiency.** With high reasoning, an agent spawns too many subagents, and
   the owner has little control over cheaper models for them. Research does not need the
   orchestrator's big model; review must be strong, execution light. Both the model per role
   and the topology itself (is it overkill?) matter.
5. **Intent persistence.** The problem is precise at the start of a conversation and vague
   after compactions. Intent and spec keep it written down, in the repository.
6. **Intent matures while coding.** The intent usually becomes clear only during
   implementation, when a change of course is expensive. The skill moves that moment to the
   spec: grilling and the spec review surface the decisions before any code exists. Evals can
   hardly measure this one ("not feasible"); the design solves it.

## What it must do

- A medium-small task feels like a few grill questions, one or two workers, done. No files to
  babysit.
- A big feature feels like parallel research, a solid spec checked by a second model, a plan
  visible as a graph, parallel workers, review by a second model, and one clean task branch at
  the end.
- The owner keeps working in the same repository while a task runs.
- The owner always knows where the task is, what starts next, and on which model and effort,
  and can change it before it starts.
- Work bigger than one task is the owner's choice: one task with a huge graph, or a split where
  the later parts wait as intents and get their spec only when someone picks them up. Nothing
  the owner defers is lost.
- The orchestrator's context stays clean, and any session can restart from the files alone.
- Half a year later the task folder answers what was intended, what was decided and by whom,
  what was planned, what was done, by which model, and why.
- Per task, the owner chooses how often to be asked: from full autonomy (a morning with quota
  to burn, a low-stakes task) to every decision (when the result must be exactly as intended),
  and how much model power each phase gets, also mid-run when a quota runs low.
- It works for code repositories and, as far as possible, for text-only folders without git
  ("ordinary problems", agent projects made of Markdown files).
- Every run leaves the repository a little more agent-friendly, through findings.

## The owner's assumptions

- The owner works alone for now, with Claude Code and Codex subscriptions; these two harnesses
  carry almost all of the work. Teams may come later, so cheap decisions keep that door open.
- Model quota is limited and uneven across harnesses and models. If it were free and endless,
  routing models per role would matter much less.
- Decisions are the owner's; facts and implementation details are the agents'. An agent's
  tradeoff presented as the owner's decision corrupts the record.
- A contract written before the code is what lets parallel jobs start from one base, and a
  check on it is far cheaper than fixing several code jobs. A contract stated twice drifts.
- A worker's "done" is a claim, and so is a reviewer's finding. Only a re-run check or the
  owner settles it.
- A run that needs bookkeeping work from agents fails the owner, even when the system behind it
  is sophisticated.

## How it differs

Plain long sessions and "vibe coding" keep everything in one context; this skill keeps the
memory in files and gives every unit of work a fresh context.

Workflows such as Superpowers share much of the base: understand before building, keep intent
in files, fresh implementer and reviewer contexts, verification evidence instead of trust,
model choice per role. None of that is this skill's invention. The difference is how tightly
state and authority are formalized:

- It is called only on purpose, never triggered by itself.
- Parallel writers are first-class planned work: a job graph with dependencies, owners of
  shared files, separate branches and integration, instead of a ban on parallel implementers.
- The owner's authority is explicit: gates, a chosen interaction mode, provenance on every
  decision, hard stops, and nothing reaches the base branch without the owner.
- Deterministic work (state, model choice, worktrees, merges, check re-runs, the finish gates)
  goes through a CLI, not through agent tokens.
- Work found outside the task has a life cycle (findings, triage, backlog) instead of being
  dropped or fixed on the side.
- Its weight adapts to the task, so it competes with a plain session on small work and with a
  heavy process on big work.

It is weaker as a coding discipline: it prescribes no test-first or debugging method. The
repository's own conventions and validation decide that.

## Principles

- **Light in its complexity.** "light in its complexity", "Keep status management from replacing productive work.". The system may be sophisticated; a run must feel
  light. Statuses change as side effects of real work; a file exists only when it carries
  content; defaults replace questions. This rule stands above every other one.
- **Files are the memory; phases are context boundaries.** Intent and spec compress the
  exploratory conversation, so rejected ideas stay behind. Workers return files, not
  transcripts.
- **Deterministic where it must be exact.** What must be exactly right goes through `sae`;
  agents do judgement: shaping, planning, implementing, deciding, reviewing.
- **Scale by three axes, each decided where its information appears:** uncertainty sets the
  shaping depth, breadth sets the execution topology, stakes set the settings.
- **The spec is a contract; the graph is a hypothesis.** The orchestrator may adapt the graph
  with a reason; accepted behavior changes only through an amendment. Above one task: specify
  only what can be seen; the rest waits as an intent.
- **Avoid multi-agent theater.** Start with one worker; fan out only for a real benefit.
  Optimize total cost, not parallelism.
- **Human authority, made explicit.** Agents decide, ask or park according to the owner's
  chosen mode; agents change settings only on the owner's word; every decision carries its
  provenance.
- **Descriptive and plain.** The owner wants to understand at once what a step or a setting
  does: short sentences, one term per meaning, values that say what they do.
- **Claude Code and Codex parity.** Every mechanism works in both, and a task can move between
  them.
- **No configuration in the skill.** Copying the skill must never look like copying a working
  configuration; personal settings live outside it.
- **PROSE where it adds no step to a run.** Conscious deviations are recorded.

## How it works, roughly

One skill with five modes, always called by name: shape, plan, execute, setup, triage.

- **Shape** turns a rough request into an intent and a spec, through grilling, research by
  subagents when needed, and an optional review of the spec by a second model. The owner
  approves the spec.
- **Plan** has a planner split the spec into a graph of jobs, each small enough for a fresh
  context, with its checks. The owner approves the plan.
- **Execute** runs the jobs with fresh workers in their own worktrees, on the model and effort
  the routing gives each phase and difficulty. `sae` re-runs every job's checks, merges the
  jobs into one task branch, and gates the finish on the review verdicts. The owner sees each
  launch before it starts and merges the task branch.
- **Setup** writes the owner's configuration and the repository's profile.
- **Triage** turns findings and decision-record drafts into tasks, backlog items and accepted
  records.

The task folder under `.tasks/` holds the intent, spec, plan, job files and results, findings
and the event log; `sae`, a Python CLI, is its only writer of state. A local viewer shows the
plan graph, what starts next and the settings for every task.

## Constraints

- Simple to run: "light in its complexity".
- Claude Code and Codex only.
- No configuration and no model names in the skill, except the setup proposal, which `sae`
  never reads.
- Nothing is pushed. Only the owner touches the base branch.
- No orphaned processes: anything `sae` leaves running listens only locally and stops by
  itself.
- Artifacts in English; the conversation in the owner's language.
- Python standard library only.
