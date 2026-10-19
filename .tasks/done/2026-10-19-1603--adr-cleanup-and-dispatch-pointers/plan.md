# Plan: ADR cleanup and dispatch pointers

## Strategy
Two independent streams meet at the end. The cleanup is judgement over 111 files with an owner
gate in the middle. The `sae` change is one coherent chain (matching → prompt lines → protocol
lines → tests) and belongs in one strong job. The prose rules are a third, small, disjoint
context. The apply step waits for all three, so it lands last on the skill files and fills the
new `revisit-when:` field from a template that already has it.

## Jobs at a glance
- `CLEANUP-LIST` — write the cleanup list for all records and research notes in its result
  file; change no repository file. **The orchestrator sets `sae hold <task> CLEANUP-LIST`
  before the first dispatch.** The owner's changes go into the list before `CLEANUP-APPLY`.
- `DISPATCH-POINTERS` — pointer lines, directory pointers, limit and index pointer in
  `sae dispatch`, the protocol lines for them, and their tests.
- `WRITING-RULES` — three places and the test in the writing rules; optional `revisit-when:`.
- `CLEANUP-APPLY` — apply the approved list to `docs/adr/` and the files it names.
- `VALIDATE-ALL` (final) — full suite and the cleanup acceptance checks on the merged branch.

## Parallelism
`CLEANUP-LIST`, `DISPATCH-POINTERS` and `WRITING-RULES` start together; their files do not
overlap. The two code-side jobs normally finish while the run waits on the owner's approval.
`CLEANUP-APPLY` deliberately waits for both code-side jobs: the list may move knowledge into
comments in skill files that those jobs edit (`prompts.py`, `plan.md`, role files). It is one job,
not one per action, because `docs/adr/index.md` and the moved-text targets are shared.

## Hot files
- `docs/adr/index.md`, `docs/adr/**` → edited only in `CLEANUP-APPLY`.
- `skills/shape-and-execute/references/roles/planner.md` (index pointer and scope sentence) →
  `DISPATCH-POINTERS`.
- `skills/shape-and-execute/templates/decision-record.md` → `WRITING-RULES`.
- `skills/shape-and-execute/templates/job.md` → `DISPATCH-POINTERS`.
- `README.md`, `CREDITS.md`, root `AGENTS.md` (links into `docs/adr/`) → `CLEANUP-APPLY`.

## Integration points
- The approved list in `jobs/CLEANUP-LIST.result.md`, section `## Cleanup list`, is the
  contract for `CLEANUP-APPLY`.
- After `CLEANUP-APPLY`, the pointer code runs against the real, smaller `docs/adr/`;
  `VALIDATE-ALL` checks that kept records' path entries name existing paths.

## Final validation
`VALIDATE-ALL` (`--final`): three workstreams meet, the profile names a full suite, and the
cleanup has repository-wide acceptance checks. The integration review (codex) then judges the
whole diff, including "every kept record passes the test" ([CLEANUP-APPLY]).

## Review flags
None. Job reviews are off (review points: `integration` only). The integration review covers
the `sae` change and the cleanup.

## Risks and adaptation triggers
- The owner rewrites much of the list, or the list moves knowledge into many files: split
  `CLEANUP-APPLY` by action (removals and index, then moves), keeping `index.md` in one job.
- `DISPATCH-POINTERS` finds no reliable changed-file list for a job review in some layout (no
  git, no commits): it adds no lines there and says so; no graph change.
- `WRITING-RULES` finds that `sae adr new` or `accept` needs a code change for `revisit-when:`:
  it parks; the change then goes to a fix job after `DISPATCH-POINTERS` (scope `scripts/`).
- The list shows private data in kept records: `CLEANUP-APPLY` removes or smooths it; the
  integration review checks.

## Riskiest assumptions
- **Directory `AGENTS.md` files and code comments under `skills/shape-and-execute/` ship with
  every install.** The intent's example (a comment in `app.css`) accepts this for comments. A
  directory `AGENTS.md` inside the skill folder would also reach users' disks. The list job
  names the target of each move; the owner sees it at approval.
- `CLEANUP-LIST` is an `implementation` job that changes nothing: a `research` job would block
  the plan approval, and the list must be a file the owner can edit. The hold is set by the
  orchestrator, not by the graph.
- Pointer lines read records from the agent's workdir (task branch state), so jobs after
  `CLEANUP-APPLY` see the cleaned set, and every link opens from the prompt's workdir.
- The list also flags kept records whose path entries name no existing path, and
  `CLEANUP-APPLY` fixes them where the approved list says. This goes slightly past the spec's
  wording, in service of "reaches the agent": a stale path never matches.
- One worker can classify 103 records and 8 notes with a consistent judgement in one context
  (about 24,000 words plus code checks).
- `sae adr new` and `sae adr accept` need no code change for an optional `revisit-when:` (the
  template is copied as text; `accept` does not validate fields).
