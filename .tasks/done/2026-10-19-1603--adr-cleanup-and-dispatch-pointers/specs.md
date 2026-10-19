# Spec: ADR cleanup and dispatch pointers

## Summary
Decision records in `docs/adr/` keep only knowledge that the code does not show. Each existing
record is kept, moved to a code comment, moved to a directory `AGENTS.md`, or removed, by a list
the owner approves during execution. `sae dispatch` adds pointer lines (index line: link and
short description) for the records that guard a job, to the worker prompt and the review
prompts. The planner and the decision worker get a pointer to `index.md`. The writing rules
name three places for "why" knowledge, by reach, and the stricter test.

## Domain language

**Record** — a decision record file in an ADR folder, with `applies-to` in its frontmatter. Not
`_intent.md`, not `index.md`, not a research note.
_Avoid:_ ADR (in task files), decision (that is a `[DECISION-…]` or a logged decision)

**Pointer line** — one line in a dispatch prompt: the record's line from `index.md` (Markdown
link and short description), with a link the agent can open from its workdir.

**Path entry** — an `applies-to` item that contains `/`. Other items are code names; they stay
for code search and are not matched.

**The test** — a record is kept only when, without it, an agent would "fix" something on
purpose, or bring back a rejected option.

## Scope

### In scope
- Pointer lines in `sae dispatch` prompts; the index pointer for planner and decision worker.
- The `revisit-when:` field in the decision-record template.
- Writing rules in `plan.md` "Decision-record drafts", `execute.md` "Finish",
  `triage-decisions.md`, and one sentence about `scope` for the planner.
- Cleanup of the existing records and research notes in `docs/adr/` of this repository.
- Tests of the matching in `tests/`.

### Out of scope
- A lint or a check for `revisit-when` (the owner expects it to rot; no mechanism).
- Reviewers getting `index.md` (draft record
  `.tasks/adr/2026-10-19-reviewers-get-matched-record-pointers-no.md`).
- Changes to the owner's release steps in the private build repository's task record; the three corrections
  are repeated in this task's final report.

## Requirements

### [THREE-PLACES] Writing rules name three places by reach
The rules for writing "why" knowledge name three places: one file → a short comment in that
file; one directory → that directory's `AGENTS.md`; cross-cutting, or a rejected option that
someone will propose again → a record. A record must pass the test.

Acceptance:
- [ ] `plan.md` "Decision-record drafts", `execute.md` "Finish" and `triage-decisions.md` state
      the three places and the test, without repeating each other at length (one states it, the
      others point to it).
- [ ] The added text is short: a few lines per file.

### [REVISIT-WHEN] Optional revisit-when field
The decision-record template has one optional frontmatter field `revisit-when:` (when the
decision stops holding).

Acceptance:
- [ ] `templates/decision-record.md` has `revisit-when:` with a one-line comment.
- [ ] `sae adr new` and `sae adr accept` work with and without the field.

### [WORKER-POINTERS] A worker job gets pointers to the records that guard it
`sae dispatch` of an implementation, integration or validation job adds pointer lines for every record
that matches the job: a path entry inside the job's `scope`, or a `scope` pattern inside a path
entry that is a folder. A job without `scope` matches the path entries (or their folders) that
its job file names word for word. A job with `scope` matches on `scope` only. No match: no extra
lines.

Acceptance:
- [ ] A job with `scope: [skills/x/assets/viewer/]` gets the pointer of a record with
      `applies-to: [skills/x/assets/viewer/app.css]`, and of a record with
      `applies-to: [skills/x/assets/]`.
- [ ] A job without `scope` whose job file names `skills/x/scripts/prompts.py` gets the pointer
      of a record with that path entry.
- [ ] A job that matches no record gets a prompt identical to today's.
- [ ] Code names in `applies-to` never cause a match.

### [REVIEW-POINTERS] Reviewers get pointers matched on the diff
`sae dispatch` of a job review adds pointer lines for the records whose path entries the target
job's diff changed (a changed file equals a path entry or lies inside it). The integration
review does the same for the whole task diff. The reviewer protocol tells the reviewer to check
that the diff breaks no pointed record.

Acceptance:
- [ ] A job review whose target changed `skills/x/scripts/prompts.py` gets the pointer of a
      record with that path entry.
- [ ] A review with no changed file under any path entry gets no extra lines.
- [ ] `references/roles/reviewer.md` has one rule about pointed records.
- [ ] The external review COMMAND (other harness) carries the same lines.

### [DIR-POINTERS] Directory instructions reach the agent
Every prompt that gets record pointers also gets one line per `AGENTS.md` or `CLAUDE.md` in a
folder above a matched path (from `scope`, the job file or the diff), below the repository
root. The root files are left out: both harnesses load them. These lines do not count toward
[POINTER-LIMIT].

Acceptance:
- [ ] A job with `scope: [skills/x/assets/viewer/app.css]` and a file
      `skills/x/assets/viewer/AGENTS.md` gets a line with that file's path.
- [ ] The root `AGENTS.md` never appears as a pointer line.
- [ ] A job with 10 record pointers and one directory file gets all 11 lines and no "+N more".

### [POINTER-LIMIT] At most 10 record pointer lines
A prompt has at most 10 record pointer lines, in `index.md` order, then one line
"+N more, see <index path>".

Acceptance:
- [ ] A job that matches 12 records gets 10 pointer lines and "+2 more, see …/index.md".

### [INDEX-POINTER] Planner and decision worker get the index
The planner prompt and the decision-worker prompt carry a pointer to `index.md` of each ADR
folder that has one. The planner protocol says to read the index and only the records it needs.
The decision-worker protocol replaces "ADRs" with this pointer. Reviewers do not get it.

Acceptance:
- [ ] `sae dispatch` of the planner and of a decision job prints the index path when it exists,
      and nothing when it does not.
- [ ] `planner.md` and `decision-worker.md` name the index.

### [PLANNER-SCOPE] The planner gives writer jobs a scope
The planner protocol and the job template say: give a writer job a `scope` when you can; it
also brings the records that guard those paths.

Acceptance:
- [ ] `planner.md` has one sentence; the `scope` comment in `templates/job.md` no longer limits
      it to parallel writers.

### [CLEANUP-LIST] The owner approves a cleanup list before anything moves
The first execution job reads every record and research note in `docs/adr/` and writes a list:
per record one action (keep, code comment with the target file, directory `AGENTS.md` with the
target folder, remove), one reason by the test, and `revisit-when` only where the condition is
obvious. Per research note: keep or remove, by whether a kept record links it. A hold stops
the run after this job. Move jobs start only after the owner approves the list.

Acceptance:
- [ ] The list covers all 103 records and 8 research notes.
- [ ] The run holds after the list job; the owner's changes go into the list before move jobs.

### [CLEANUP-APPLY] The repository follows the approved list
Each record gets the approved action. Moved knowledge is short and sits where the list says.
`_intent.md` stays. No `DL-…` source remains. `index.md` has one line per remaining record and
note. The repository's AGENTS.md files point to what moved where only when needed.

Acceptance:
- [ ] `grep -r "DL-" docs/adr` finds nothing.
- [ ] Every file in `docs/adr/` (except `index.md`) has exactly one index line, and every index
      line points to an existing file.
- [ ] Every kept record passes the test, in the integration review's judgement.
- [ ] No private data: no names, no pilot-project context, quotes in English and smoothed.

### [TESTS] Tests cover the matching
Acceptance:
- [ ] `tests/` covers [WORKER-POINTERS], [REVIEW-POINTERS], [DIR-POINTERS], [POINTER-LIMIT] and
      [INDEX-POINTER].
- [ ] `python3 tests/run.py` passes.

## Rules and edge cases

### [EDGE-NO-ADR-FOLDER] A repository without records
No ADR folder, or no record with path entries: prompts are as today.

### [EDGE-MANY-FOLDERS] Several ADR folders
With `adr_rules`, records come from every rule folder and the flat folder; each pointer line
links its own folder's file, and "+N more" names each index involved.

### [EDGE-NO-INDEX-LINE] A record without an index line
The pointer line is built from the record the way `sae adr accept` builds index lines.

## Technical contract

### Technical constraints
- `sae` stays Python 3.9+, standard library only.
- Few added lines; no new command, no new setting, no new state.
- Work on top of the release history in this repository, as normal commits; nothing is pushed.

## Decisions

### [DECISION-LIST-IN-EXECUTION] The cleanup list is made in execution, with a hold
**Decision:** The first job writes the list; a hold stops the run; the owner approves; then the
moves.
**Reason:** The owner chose it over classifying during shaping.
**Based on:** user decision
**Provenance:** [human]

### [DECISION-MATCH] Worker on scope, reviewer on the diff, job file as fallback
**Decision:** See [WORKER-POINTERS] and [REVIEW-POINTERS].
**Reason:** The diff gives the reviewer an exact match for free; the worker depends on a
declared `scope`; the job-file fallback is cheap because a pointer is one line.
**Based on:** user decision (Q2 B, Q5 A); `scope` already exists as optional globs
**Provenance:** [human]

### [DECISION-POINTER-FORMAT] A pointer is the index line
**Decision:** Link plus short description from `index.md`; the agent opens the record when it
needs it.
**Reason:** "pointers, not pastes"; the owner asked for the link and the brief description only.
**Based on:** user decision
**Provenance:** [human]

### [DECISION-LIMIT] 10 lines, then "+N more"
**Decision:** See [POINTER-LIMIT].
**Based on:** user decision (Q7 B)
**Provenance:** [human]

### [DECISION-INDEX-ROLES] Index for planner and decision worker, not reviewers
**Decision:** See [INDEX-POINTER].
**Reason:** The owner is not sure; the index might help a reviewer, "but on the other hand this
could provide too much noise for an agent that should be as focused as it can".
**Based on:** user decision; draft record `.tasks/adr/2026-10-19-reviewers-get-matched-record-pointers-no.md`
**Provenance:** [human]

### [DECISION-NOTES-FOLLOW] Research notes follow their records
**Decision:** A note stays while a kept record links it.
**Based on:** user decision; existing record "Research notes follow their decisions"
**Provenance:** [human]

### [DECISION-REVISIT-OPTIONAL] revisit-when is optional
**Decision:** Optional everywhere; the cleanup fills it only where obvious; no lint.
**Based on:** user decision (Q4 C)
**Provenance:** [human]

### [DECISION-PATH-ENTRIES] Only path entries match
**Decision:** An `applies-to` item matches only when it contains `/`.
**Reason:** Code names like `cmd_set` or `settings.json` would match by accident.
**Based on:** existing architecture (all 103 records carry path entries)
**Provenance:** [agent]

### [DECISION-DL-SOURCES] DL sources go, task IDs stay
**Decision:** Remove `DL-…` (and the private interview references with them) from `source`;
keep a task ID when the record has one; drop the field when nothing remains.
**Based on:** intent
**Provenance:** [agent]

### [DECISION-DIR-POINTERS] sae points to directory AGENTS.md files
**Decision:** See [DIR-POINTERS]; outside the limit of 10.
**Reason:** Neither harness reliably loads a directory `AGENTS.md` for a `sae` worker: Codex
reads only root to working directory, at start; Claude Code loads nested files on a Read, and
documents it only under the working directory, while `sae` worktrees live outside it.
**Based on:** user decision (Q8 A); research/NESTED-AGENTS-MD.md
**Provenance:** [human]

### [DECISION-VALIDATION-POINTERS] Validation jobs get pointers too
**Decision:** Validation jobs match like the other worker jobs.
**Reason:** A validator that does not know a record can report intended behavior as a failure,
and that report starts a fix job. One rule for every worker job is also simpler than an
exception.
**Based on:** the owner's question; agent reasoning
**Provenance:** [joint]

## Research basis
- [research/NESTED-AGENTS-MD.md](research/NESTED-AGENTS-MD.md) — how Claude Code and Codex load
  nested `AGENTS.md` / `CLAUDE.md`; basis of [DECISION-DIR-POINTERS].
