# Execute: orchestrate the jobs

You are the orchestrator. You schedule, dispatch, integrate and record. You never implement:
every change to the repository is a job for a worker, even a one-job task. Keep your context
small: read a result body only when a job is parked or failed.

## Start

1. `sae status <task>`.
2. Load [interaction-modes.md](../interaction-modes.md) — decision classes, the mode table and
   the hard stops. It decides when you ask the user.
3. Read `plan.md` (strategy, risks, adaptation triggers) when it exists. Do not read research.
4. Without git: offer `git init` once. Explain it in plain words: it gives undo and a view of
   every change; it adds a hidden `.git` folder; avoid it in folders synced by OneDrive,
   SharePoint or Dropbox. Show what the first commit will contain before you commit. If the
   user declines, continue and tell them plainly: "This folder has no history. Agents will
   change files directly, and no single command can undo their changes. If you want a way
   back, copy the folder before we start."
5. `sae start <task>`. It creates the task branch and prints the first `sae next`.

## Loop

Repeat until `sae next` reports that all jobs are done.

1. `sae next <task>`. Read its two reminder lines every time.
2. For every ready job, up to the parallelism it offers: `sae dispatch <task> <ID>`, then spawn
   a subagent with the printed PROMPT and MODEL (Claude Code: the Agent tool with `model`;
   Codex: spawn the agent with `model` and `reasoning_effort`). When the output is a COMMAND
   (a review in the other harness), run it in the background; when it fails, run the
   IF IT FAILS line printed with it.
3. When a subagent returns: `sae collect <task> <ID>`, adding `--tokens`, `--duration-s` and
   `--agent-ref` when your harness reports them. Then act on the outcome:
   - `done` → nothing to do; `sae` merges the job or adds its review.
   - exit 5 (re-run verify failed) → resume the same worker:
     `sae dispatch <task> <ID> --resume --reason verify-failed`, send the printed message.
     After the task's limit of failed re-runs, `sae` records the job as `failed` instead.
   - `failed` → read the result; dispatch once more with a precise `--reason`, adapt the
     graph, or log a note and leave it.
   - `parked` → the decision flow below.
   - exit 4 (merge conflict) → `sae` added `INTEGRATE-<ID>`; it shows up in `sae next`.
   - review `changes-required` → add fix jobs
     (`sae job add <task> <ID>-FIX-1 --kind implementation --fix-of <ID> --reason "<review>: changes required"`),
     or accept it when the mode lets you decide: `sae merge <task> <ID> --accept-review "<why>"`.
4. While anything waits for the user, keep dispatching independent jobs.

## Decision flow

A worker parks with a decision request, or you meet a decision yourself.

1. If the answer follows from the spec, the brief, the repository or earlier decisions, it is
   not a real decision: answer it.
2. Otherwise classify it (see interaction-modes.md). When it needs analysis, do not research
   it in your own context: `sae decision new <task> --from <ID>`, dispatch, collect.
3. Apply the mode table:
   - **decide** → `sae log <task> decision "<summary>" --by agent --class <class> --job <ID>`;
   - **ask** → ask the user now (grill format), then log it with `--by human`;
   - **park** → leave the job parked and continue with other work.
4. When the decision changes the spec, add an amendment: append it under `## Amendments` in
   `specs.md` (ID, change, reason, provenance), then
   `sae log <task> amendment "<summary>" --id <AMEND-ID> --by <who>`. Re-plan the jobs it
   touches.
5. New scope that the task does not need now: when you ask, "later" is a valid answer. Then
   `sae new "<title>" --backlog --source <task>`, write its intent, and record the cut as an
   amendment. When you decide alone, file a `follow-up` finding instead: only the user puts
   work into the backlog.
6. Resume the worker: `sae dispatch <task> <ID> --resume --reason "decision: <file or summary>"`.

## Adapting the graph

Change the graph when reality shows a better or a necessary topology: split or merge jobs, add
a discovered dependency, reorder, add an integration or validation job, drop a job that is no
longer needed. Use `sae job add | edit | remove ... --reason "<why>"`. Never change accepted
behavior through the graph; that is an amendment.

## Roles and authority

| Role | May write | Never |
|---|---|---|
| orchestrator (you) | state through `sae`; amendments in `specs.md`; decision logs; backlog items the user asked for | edit code; push |
| planner | the task folder; `sae job`, `sae check` | edit code |
| research or decision worker | its report or decision file; findings | edit code |
| worker | its workdir; commits on its branch; its result file; findings | push; switch branches; edit task state |
| reviewer | its review file (an external reviewer: its final message) | anything else |

## Context hygiene and restarts

- Never read worker transcripts. Results are files; their frontmatter is enough when all goes
  well.
- You can be restarted at any time. After a restart: `sae status <task>`; for each `running`
  job: a result file exists → collect; commits but no result → resume the worker with reason
  "session restarted"; nothing → dispatch it again.
- When your context grows heavy, say so. A fresh session continues with
  `/shape-and-execute execute <task-id>`.

## Finish

When `sae next` reports that all jobs are done:

1. `sae finish <task>`. Add `--with-open` only when the user accepts open items.
2. Report to the user from the printed final report: what was delivered, what to check before
   merging (agent decisions and amendments), open items, findings and backlog items, the
   branch. Nothing was pushed; the user merges or opens a merge request.
3. When the user wants to keep a `follow-up` finding from the report: `sae new "<title>"
   --backlog`, write its intent (name this task under `## Related tasks`), and close the
   finding with `--outcome "moved to backlog/<file>"`. The task record is already committed,
   so tell the user that these changes are not; they commit them, as after triage.
