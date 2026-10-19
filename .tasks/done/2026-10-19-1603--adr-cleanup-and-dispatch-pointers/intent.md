# Intent: Decision records earn their place and reach the agent at the change

## Problem
`docs/adr/` holds 103 records and about 24,000 words for one skill. Most came over one to one
from the design log on 2026-10-12 (`source: DL-…`), without the triage test "could a later agent
rebuild this from the code?". Many only restate current behavior ("Task settings in their own
file", "Finished tasks live in the done folder"). Some are taste that matters for one file only
(the Supabase-style viewer). The `DL-…` sources point to private records that the public
repository does not have.

Nothing reads the records at the right moment. Only the decision worker is told to read ADRs, and
triage proposes one AGENTS.md line at the first record. Workers, planners and reviewers never get
them. `applies-to` only picks the target folder in `sae adr accept`; it never brings a record to an
agent. An agent finds a record only when it digs through old commits. The owner: "This has to
serve a purpose; right now it is a collection of spam."

## Goal
A record exists only when it carries knowledge that the code does not show, and it reaches the
agent that is about to change the code it guards.

### Success means
- Every kept record passes the test: without it, an agent would "fix" something on purpose, or
  bring back a rejected option.
- A worker whose job scope touches a record's `applies-to` paths gets a pointer to that record in
  its dispatch prompt. A job with no matching record gets nothing extra.
- A reviewer of a job gets pointers to the records whose `applies-to` paths the diff changed, and
  checks that the diff breaks no record. The integration review does the same for the whole diff.
- The repository is clean before the first push.

## Proposed outcome
- **Three places for "why" knowledge, by reach** (PROSE explicit hierarchy):
  - one file → a short comment in that file (example: the viewer's dark default goes to the top
    of `app.css`);
  - one directory → the `AGENTS.md` of that directory;
  - cross-cutting, or a rejected option that someone will propose again → a decision record.
- **Clean up the existing records** with that test. Each record gets one action: keep, move to a
  code comment, move to a directory `AGENTS.md`, or remove. The owner approves the list before
  anything moves. `_intent.md` stays. Remove the `DL-…` sources. Update `index.md`.
  - [human] The list is made during execution: the first job classifies the records, a hold
    stops the run after it, the owner approves the list, then the jobs that move and remove
    records start.
  - [human] The research reports in `docs/adr/research/` follow their records: a report stays
    while at least one kept record links it; otherwise it is removed.
- **Pointers at dispatch.** `sae dispatch` adds one line per record whose `applies-to` matches the
  job, to the worker prompt and to the review prompt ("pointers, not pastes"). The owner called
  this the key idea.
  - [human] The line is the record's Markdown link and its short description from `index.md`.
    The agent opens the record only when it needs it.
  - [human] The worker matches on the job's `scope`. A job review matches on the files that the
    diff changed; the integration review on the whole diff. The planner gives a writer job a
    `scope` when it can.
  - [human] A job without `scope` also matches the `applies-to` paths (or their folders) that
    its job file names word for word. A job with `scope` matches on `scope` only.
  - [human] At most 10 pointer lines per prompt, then one line "+N more, see index.md".
  - [human] Directory `AGENTS.md` / `CLAUDE.md` files get pointer lines too, outside the limit.
    Neither harness reliably loads them for a `sae` worker (research NESTED-AGENTS-MD).
  - [joint] Validation jobs get pointers like the other worker jobs.
  - [human] Besides the planner, the decision worker gets a pointer to `index.md` (it replaces
    "read ADRs"). Reviewers do not get the index. The owner is not sure about this: reviewers
    might catch more with it, "but on the other hand this could provide too much noise for an
    agent that should be as focused as it can". This choice gets its own decision record.
- **Planner** reads only `index.md`.
- **Template:** one field `revisit-when:` (when the decision stops holding). The owner expects it
  to rot without a mechanism, but it is better than nothing.
  - [human] The field is optional in every record. The cleanup fills it only where the condition
    is obvious.
- **Writing rules** in plan.md "Decision-record drafts", execute.md "Finish" and
  triage-decisions.md follow the three places and the stricter test.

## Affected users and systems
Every user of the skill (writing and reading rules), `sae dispatch`, the decision-record
template, `docs/adr/`, and the AGENTS.md files of this repository.

## Constraints
- Work directly in this repository (`~/code/shape-and-execute`), on top
  of the release history, as normal commits. Do not wipe its git history: the 142 commits are the
  release ([PUBLIC-REPO] of task 2026-10-18-1334--public-release-of-shape-and-execute).
- From now on this repository is the source of truth, not the private build repository. Its
  repair path (rebuild and force-push) would drop these commits; repairs happen here.
- Slim, like the rest of the skill: few added lines, no new ceremony.
- No private data: the same rules as the release (no names, no pilot-project context, quotes in
  English and smoothed).

## Related tasks
Follows 2026-10-18-1334--public-release-of-shape-and-execute (in the private build repository). Do this before the
first push of the release. After this task, the owner continues the release with the owner steps
in that task's record (`.tasks/done/2026-10-18-1334--public-release-of-shape-and-execute/jobs/RELEASE-CUT.result.md`
on the private build repository's task branch), with three corrections:
- Step 2: use `export SAE_CONFIG="$T/sae-config.json"` instead of `export XDG_CONFIG_HOME=…`
  (the latter hides the `gh` login); `unset SAE_CONFIG` after the test.
- Step 3: repairs happen in this repository, not by rebuilding the private build repository and force-pushing.
- Step 5: the owner's global copy was already restored to the APM-pinned version; step 5 still
  updates it to the release.
