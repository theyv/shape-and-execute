# Execute: orchestrate the jobs

You are the orchestrator. You schedule, dispatch, integrate and record. You never implement:
every change to the repository is a job for a worker, even a one-job task. Keep your context
small: read a result body only when a job is parked or failed, or lists disputed findings.

## Start

1. `sae status <task>`. It works from any checkout of the repository: you may stay in the
   home checkout.
2. Load [interaction-modes.md](../interaction-modes.md) — decision classes, the mode table and
   the hard stops. It decides when you ask the user.
3. Read `plan.md` (strategy, risks, adaptation triggers) when it exists. Do not read research.
4. Without git: offer `git init` once. Explain it in plain words: it gives undo and a view of
   every change; it adds a hidden `.git` folder; avoid it in folders synced by OneDrive,
   SharePoint or Dropbox. Show what the first commit will contain before you commit. If the
   user declines, continue and tell them plainly: "This folder has no history. Agents will
   change files directly, and no single command can undo their changes. If you want a way
   back, copy the folder before we start."
5. `sae start <task>` (add `--harness claude|codex` when this session runs in the other
   harness). It creates the task branch and the task worktree, prints its path and resumes a
   task that already executes. The home checkout keeps its branch; its uncommitted changes
   only warn: they are not part of the task, so tell the user. Show the start next-step card
   it prints and wait (skip means not starting now).

## Loop

Repeat until `sae next` reports that all jobs are done.

1. `sae next <task>`. Read its reminder block every time. A next-step card during execution (an
   integration review, research): show it and continue, without waiting.
2. For every ready job, up to the parallelism it offers: `sae dispatch <task> <ID>`, then spawn
   a subagent with the printed PROMPT, MODEL and EFFORT. When the output is a COMMAND (a job in
   the other harness), run it in the background. When it fails, or `sae` refuses because the
   other harness is missing, `sae` prints a fallback command (the IF IT FAILS line). For a
   review, run it. For any other job, run it only in `full-auto`. In the other modes park the
   job (`sae job park <task> <ID> --reason "harness fallback: <why>"`), ask the user and
   continue with independent work; on the user's yes, run the fallback command with
   `--resume`. `sae` records each fallback run as a routing exception; later dispatches use
   routing again.
3. When a subagent returns: `sae collect <task> <ID>`, adding `--tokens`, `--duration-s` and
   `--agent-ref` when your harness reports them. A COMMAND job needs no `--tokens`: `sae` reads
   them from the output the COMMAND kept, then deletes that output. When you run a harness
   yourself, keep its output outside `.tasks/`. Then act on the outcome:
   - `done` → nothing to do; `sae` merges the job or adds its review.
   - exit 5 (re-run verify failed) → resume the same worker:
     `sae dispatch <task> <ID> --resume --reason verify-failed`, send the printed message.
     After the task's limit of failed re-runs, `sae` records the job as `failed` instead.
   - `failed` → read the result; dispatch once more with a precise `--reason`, adapt the
     graph, or log a note and leave it.
   - `parked` → the decision flow below.
   - exit 4 (merge conflict) → `sae` added `INTEGRATE-<ID>`; it shows up in `sae next`.
   - "N disputed findings" → settle them (below).
   - "Closed finding …" → nothing to do: the job resolved it and `sae` committed the closure
     on the task branch. "Finding stays open: …" → the worker did not list it as resolved;
     its result says why. Mention it in your report; it stays for the next triage.
   - review `changes-required` (a job or the integration) → triage first, against the stakes.
     A finding that needs more care than the stakes justify becomes `[beyond stakes]` in your
     report. Log each finding you set aside with its reason:
     `sae log <task> decision "<finding>: <reason>" --job <REVIEW-ID> --let-go`. For the rest,
     add fix jobs
     (`sae job add <task> <ID>-FIX-1 --kind implementation --fix-of <ID or round ID> --reason "<review>: changes required"`).
     A fix job states each finding's `Expected` and
     every place under `Also in`; it does not limit the worker to single instances; each "do
     not" in it gives its reason ("because …"), also when it rules out a fix that a review
     proposed. One round gets one fix job unless its findings touch unrelated parts and one job
     would not fit one context. When no finding is left, accept the review when the mode lets
     you decide: `sae merge <task> <ID> --accept-review "<why>"` for a job,
     `sae accept-review <task> <REVIEW-ID> --reason "<why>"` for the integration. A finding
     that proposes a change of approach is a decision (below).
     After `max-review-rounds` changes-required rounds (default 3), the job, or for the
     integration the task, parks for the user. Relay the story `sae` prints and ask, in every
     mode: change the approach, reduce the requirement, or another round; add your
     recommendation and its reason. To change the approach, a job may be dropped, only on the
     user's word: `sae job drop <task> <ID> --reason "<why>"`.
4. While anything waits for the user, keep dispatching independent jobs.

**Holds and changes.** On the user's word: a hold after any job (`sae hold <task> <ID>`,
`--release`; or the viewer), and level, routing or override changes, which apply from the
next dispatch. When `sae next` names an active hold, report the results so far and wait for
the release; running jobs finish normally.

## Decision flow

A worker parks with a decision request, or you meet a decision yourself.

1. If the answer follows from the spec, the brief, the repository or earlier decisions, it is
   not a real decision: answer it.
2. Otherwise classify it (see interaction-modes.md). When its analysis would fill your
   context (several files, review rounds or options to compare), do not do it yourself:
   `sae decision new <task> --from <ID>` or `--question "<question>"`, dispatch, collect.
   The job it concerns need not park; independent work continues. Typical cases: a finding
   proposes a change of approach; a worker's Approach proposal; two results contradict each
   other; a fix chain near its round limit.
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
6. When the job parked, resume the worker: `sae dispatch <task> <ID> --resume --reason "decision: <file or summary>"`.

## Disputed findings

A fix worker checks each review finding before it acts. The ones it believes wrong are not
implemented; its result lists them under `## Disputed findings`, with the reason. Read that
section and settle each one as a decision (the flow above): who is right, by the evidence. Log
the outcome (`sae log <task> decision "disputed: <finding>: <outcome>" --job <ID> ...`). When
the finding stands after all, add a fix job for it.

## Adapting the graph

Change the graph when reality shows a better or a necessary topology: split or merge jobs, add
a discovered dependency, reorder, add an integration or validation job, drop a job that is no
longer needed. Use `sae job add | edit | remove ... --reason "<why>"`. Never change accepted
behavior through the graph; that is an amendment.

## Roles and authority

| Role | May write | Never |
|---|---|---|
| orchestrator (you) | state through `sae`; amendments in `specs.md`; decision logs; decision-record drafts; backlog items the user asked for | edit code; push |
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
  `/shape-and-execute execute <task-id>` and `sae start <task>`, in either harness:
  `--harness claude|codex` records a switch.

## Finish

When `sae next` reports that all jobs are done:

1. Draft decision records from the logged decisions and amendments (`decision` and
   `amendment` lines in `events.jsonl`, `## Amendments` in `specs.md`), as
   [plan.md](plan.md) "Decision-record drafts" says: the three places by reach, and a record
   only when it passes the test; often none.
2. Quote review (SKILL.md, "Quote review at approvals"): list the user's quotes written since
   the plan approval, these drafts included, with the file of each. When there are new quotes,
   wait for the user to accept, reword or remove them, in every interaction mode; apply the
   changes to the files, and only then run `sae finish <task>`. With no new quotes, run it
   at once. Add `--with-open` only when the user accepts open items. When it
   refuses because a review's last round says `changes-required`, or a check is stale: add fix
   jobs, accept the round (Loop, step 3), or, only on the user's word, `--override "<reason>"`.
3. Report to the user from the printed final report: what was delivered, what to check before
   merging (agent decisions, settled disputes, findings let go with their reasons, routing
   exceptions, dropped jobs, amendments, overridden gates), open items,
   findings, backlog items and decision-record drafts, the branch, and the task worktree path
   to test in. Nothing was pushed; the user merges or opens a merge request; `sae` removes the
   task worktree after the merge.
4. When the user wants to keep a `follow-up` finding from the report: `sae new "<title>"
   --backlog`, write its intent (name this task under `## Related tasks`), and close the
   finding with `--outcome "moved to backlog/<file>"`. The task record is already committed,
   so tell the user that these changes are not; they commit them, as after triage.
