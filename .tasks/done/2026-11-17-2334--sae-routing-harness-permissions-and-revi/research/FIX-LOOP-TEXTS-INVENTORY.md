# Fix-loop texts printed by `sae` (range 2343cee..d721274)

Rendered from a scratch run of the worktree's `sae.py` (tests' Sandbox). Task IDs shortened to `<task>`.
All paths are `skills/shape-and-execute/scripts/sae_lib/<file>:<line>`. NEW = added in the range, CHANGED = existed, edited, UNCHANGED = existed before but now wired into the loop.

## 1. Changes-required round below the limit

### 1.1 Job review round (CHANGED, was "Add fix jobs: ...")
Printed by `sae collect` of a REVIEW-<JOB> round with verdict changes-required.
```
REVIEW-CORE: done — verdict: changes-required
CORE: changes required. Triage first (execute.md, Loop step 3).
Fix job for the findings you keep:
  sae job add <task> CORE-FIX-1 --kind implementation --fix-of CORE --reason "REVIEW-CORE: changes required"
Each finding you set aside, logged with its reason:
  sae log <task> decision "<number>: <reason>" --job REVIEW-CORE --let-go
Or accept when the mode lets you decide:
  sae merge <task> CORE --accept-review "<why>"
```
fix_loop.py:31-39 (`changes_required_lines`), reviews.py:710-711. The fix command gets the next free `-FIX-<n>` (reviews.py:~427, CHANGED, `fix_job_command`).

### 1.2 Integration review round (CHANGED)
Printed by `sae collect` of REVIEW-INTEGRATION[-n] below the limit.
```
REVIEW-INTEGRATION: done — verdict: changes-required
REVIEW-INTEGRATION: changes required. Triage first (execute.md, Loop step 3).
Fix job for the findings you keep (sae adds the next round when it is merged):
  sae job add <task> INTEGRATION-FIX-1 --kind implementation --fix-of REVIEW-INTEGRATION --reason "REVIEW-INTEGRATION: changes required"
Each finding you set aside, logged with its reason:
  sae log <task> decision "<number>: <reason>" --job REVIEW-INTEGRATION --let-go
Or accept when the mode lets you decide:
  sae accept-review <task> REVIEW-INTEGRATION --reason "<why>"
Or, on the owner's word, close anyway:
  sae finish <task> --override "<reason>"
```
fix_loop.py:31-39, reviews.py:730-732.

### 1.3 Integration notice in `sae next` / `sae status` (CHANGED: accept lines added)
Printed while the last integration round requires changes and no fix job exists yet.
```
REVIEW-INTEGRATION requires changes. Add fix jobs (sae adds the next round when they are merged):
  sae job add <task> INTEGRATION-FIX-1 --kind implementation --fix-of REVIEW-INTEGRATION --reason "<finding>"
Or accept when the mode lets you decide:
  sae accept-review <task> REVIEW-INTEGRATION --reason "<why>"
Or, on the owner's word:
  sae finish <task> --override "<reason>"
```
progress.py:305-318. Also shown as the `Blocked:` line (graph.py:~177, CHANGED wording gate `{last} (changes-required: fix jobs, then the next round)`, now skipped once the round is accepted).

### 1.4 `sae finish` refused (CHANGED: accept line added)
```
Finish refused: REVIEW-INTEGRATION says changes-required.
Ways forward:
  - fix jobs:
    sae job add <task> INTEGRATION-FIX-1 --kind implementation --fix-of REVIEW-INTEGRATION --reason "<finding>"
  - or accept the round when the mode lets you decide:
    sae accept-review <task> REVIEW-INTEGRATION --reason "<why>"
  - or close anyway, with the owner's reason:
    sae finish <task> --override "<reason>"
```
reviews.py:509-515. For a job review the accept line is `sae merge <task> <JOB> --accept-review "<why>"` (accept_line, fix_loop.py:23-28).

## 2. Let-go (`sae log ... --let-go`)

### 2.1 Success (UNCHANGED output)
```
Logged decision.
```
findings.py:~117-135 (logic NEW; the output text is the old one).

### 2.2 Usage errors (all NEW)
```
--let-go logs one finding set aside in triage: a decision with --job <REVIEW-ID>.
  sae log <task> decision "<number>: <reason>" --job <REVIEW-ID> --let-go
```
findings.py:120 (no review job or not a decision).
```
--let-go names one finding of REVIEW-CORE by its number:
  sae log <task> decision "<number>: <reason>" --job REVIEW-CORE --let-go
```
fix_loop.py:239 (no number).
```
REVIEW-CORE has no finding 7; its findings are 1, 2:
  sae log <task> decision "<number>: <reason>" --job REVIEW-CORE --let-go
```
fix_loop.py:244 (variants: "numbers finding N more than once"; "its review lists no numbered findings yet").
```
--let-go needs a reason after "2:":
  sae log <task> decision "<number>: <reason>" --job REVIEW-CORE --let-go
```
fix_loop.py:246.

### 2.3 Help text (CHANGED, findings.py:~451-458)
`sae log --help`: "--let-go: a decision that sets one review finding aside in triage, with --job <REVIEW-ID> and the summary "<number>: <reason>" (the finding's number in the review); the final report lists it under Findings let go." Example `log <task> decision "2: beyond the Project Stakes" --job REVIEW-STATUS-API --let-go`; flag help "one finding of the --job review set aside in triage".

## 3. Round-limit park (the owner's choice)

### 3.1 Park opening line (NEW constant `PARK_OPENING`)
First line of every park message and every park story.
```
Parked at the round limit: the choice is the user's, in every mode. Add no fix job and accept nothing before the user answers: a fix job unparks the job. Relay the story with your recommendation and its reason.
```
park_story.py:19-21.

### 3.2 Job park message (CHANGED, replaces "Ask the user. Accept with: ...")
Printed by `sae collect` of the review round that hits max-review-rounds.
```
REVIEW-CORE-3: done — verdict: changes-required
<PARK_OPENING>
CORE parked: 3 review rounds required changes (max-review-rounds is 3). The story to relay, round by round: sae next <task>
Options:
  - another round:
    sae job add <task> CORE-FIX-3 --kind implementation --fix-of CORE --reason "<finding>"
    sae set <task> max-review-rounds=4
  - change the approach:
    sae job drop <task> CORE --reason "<why>"  (only on the user's word)
    sae decision new <task> --from REVIEW-CORE-3
  - reduce the requirement:
    an amendment: append it under ## Amendments in specs.md, then
    sae log <task> amendment "<summary>" --id <AMEND-ID> --by human
  - accept:
    sae merge <task> CORE --accept-review "<why>"
While you wait for the answer: sae ask <task> "<question>" --job CORE
```
reviews.py:700-708; options park_story.py:210-243 (NEW). The `sae set ... max-review-rounds=N+1` line is dropped when limit >= 10 (park_story.py:216).

### 3.3 Task (integration) park message (CHANGED, replaces "Ask the owner: more fix jobs / close anyway")
```
REVIEW-INTEGRATION-2: done — verdict: changes-required
<PARK_OPENING>
The task is parked: REVIEW-INTEGRATION-2 still requires changes after a fix round (max-review-rounds is 2). The story to relay, round by round: sae next <task>
Options:
  - another round:
    sae job add <task> INTEGRATION-FIX-2 --kind implementation --fix-of REVIEW-INTEGRATION-2 --reason "<finding>"
    sae set <task> max-review-rounds=3
  - change the approach:
    sae job drop <task> <ID> --reason "<why>"  (only on the user's word)
    sae decision new <task> --from REVIEW-INTEGRATION-2
  - reduce the requirement:
    an amendment: append it under ## Amendments in specs.md, then
    sae log <task> amendment "<summary>" --id <AMEND-ID> --by human
  - accept:
    sae accept-review <task> REVIEW-INTEGRATION-2 --reason "<why>"
  - close anyway:
    sae finish <task> --override "<reason>"
While you wait for the answer: sae ask <task> "<question>" --job REVIEW-INTEGRATION-2
```
reviews.py:720-728; park_story.py:228-229 adds "close anyway" for the task.

## 4. Park story in `sae next` / `sae status` (all NEW)

### 4.1 Job park story
Printed after the `Parked:` list (and in `--json` as `park_stories`).
```
Parked:
  CORE — REVIEW-CORE-3: changes required after 3 review rounds (max-review-rounds 3) — human decision

<PARK_OPENING>
CORE is parked for the owner: 3 review rounds required changes (max-review-rounds 3).
Objective of CORE: Cache the claim status for the portal.
Its result: CORE
Round 1 — REVIEW-CORE: changes-required
  Finding: Stale status after an update
    Suggested fix: Clear the cache on write
  Finding: Cache never expires
    Suggested fix: Add a TTL
  Fix CORE-FIX-1 (done): clears on write
    Limit: Do not touch the portal, because the portal is out of scope.
Round 2 — REVIEW-CORE-2: changes-required
  Finding: Stale status after a delete
    Suggested fix: Clear it on delete too
  Fix CORE-FIX-2 (done): clears on delete
Round 3 — REVIEW-CORE-3: changes-required
  Finding: Stale status after a bulk import
    Suggested fix: Store the status once, not derived
Options:
  ... (same Options block as 3.2)
While you wait for the answer: sae ask <task> "<question>" --job CORE
```
park_story.py:289-318 (`park_story_text`), progress.py:293-299 (`job_story_lines`, called at 180 and 268).
Variants: "(no finding titles in its review file)"; "Round N — ID: changes-required, accepted"; "no summary" for a fix without a summary.

### 4.2 Task park story
Same shape; also printed as the error of `sae dispatch` while parked (progress.py ~438-440).
```
<PARK_OPENING>
The task is parked for the owner: REVIEW-INTEGRATION-2 still requires changes after a fix round (2 changes-required integration rounds, max-review-rounds 2). Nothing is dispatched until the owner chooses (decision jobs still run).
Task: <task title>
Round 1 — REVIEW-INTEGRATION: changes-required
  Finding: Two retry rules
    Suggested fix: One retry helper
  Fix INTEGRATION-FIX-1 (done): one helper
    Limit: Never change the API, because clients depend on it.
Round 2 — REVIEW-INTEGRATION-2: changes-required
  Finding: Retry in LEFT
    Suggested fix: Call the helper
Options:
  ... (same Options block as 3.3)
While you wait for the answer: sae ask <task> "<question>" --job REVIEW-INTEGRATION-2
```
park_story.py:292-296.

### 4.3 `--help` text (CHANGED)
`sae next --help`, `sae status --help`, `sae dispatch --help` gained sentences about the story ("the story of each park at the review-round limit (relay it to the user)", "A decision job only advises, so it passes both. A dropped job never runs again.") progress.py:~526-566.

## 5. Approach paragraph and Approach proposal

### 5.1 Approach paragraph in the fix-job prompt (text UNCHANGED, wiring NEW)
Appended after "Fixes job X — review to address:" when the fix answers round k >= max-review-rounds - 1 (and every later fix of the same target).
```
FIX 2 of CORE. CORE parks for the owner after review round 3.
Before you patch, read the earlier review rounds of CORE and answer under "Decisions taken"
in your result:
1. Do the findings share one cause? Typical causes: the same value computed in several
   places; a function that gets a new special case in every round; a requirement read
   wider than the spec states.
2. Would a different approach remove that cause, so the same kind of finding cannot come
   back? Typical approaches: one function that every place calls; a value stored once
   instead of derived; a smaller reading of the requirement.
If yes and it fits your job, use it. If your job forbids it, still make your best fix and
describe the approach under "Approach proposal" in your result.
Review rounds of CORE so far:
  <path>/reviews/REVIEW-CORE.md
  <path>/reviews/REVIEW-CORE-2.md
```
Constant prompts.py:42-53 (existed before the range); `approach_lines` prompts.py:261-268 (NEW, "Review rounds of {target} so far:" is NEW); call prompts.py:~310. For an integration fix the target reads `REVIEW-INTEGRATION`.

### 5.2 `sae collect` of a fix with an Approach proposal (NEW)
```
CORE-FIX-2: done — clears on delete
Approach proposal in <path>/jobs/CORE-FIX-2.result.md: read that section; it is a decision (execute.md, Decision flow).
Added REVIEW-CORE-3: dispatch it.
```
park_story.py:23 (constant), reviews.py:593-595.

### 5.3 Pointer in the next review round's prompt (text UNCHANGED, wiring NEW)
```
Read first: the "Approach proposal" in <path>/jobs/CORE-FIX-2.result.md
```
prompts.py:39 (constant), prompts.py:386.

## 6. Accept

### 6.1 `sae accept-review` success (NEW)
```
REVIEW-INTEGRATION-2 accepted: remaining findings are beyond the Project Stakes
The task continues as after a pass: the final validation and sae finish need no --override for this round. The final report lists its findings with this reason.
Next: sae next <task>
```
fix_loop.py:178-183.

### 6.2 `sae accept-review` refusals (NEW)
```
--reason is required: sae accept-review <task> <REVIEW-ID> --reason "<why>"
<ID> is a <kind> job, not a review round.
REVIEW-CORE-3 reviews the job CORE. Accept a job review with:
  sae merge <task> CORE --accept-review "<why>"
REVIEW-X reviews the <target>; its verdict does not block, so there is nothing to accept.
REVIEW-INTEGRATION is not the last integration round; REVIEW-INTEGRATION-2 is. Accept that one:
  sae accept-review <task> REVIEW-INTEGRATION-2 --reason "<why>"
<ID> is <verdict pass|status>; only a changes-required round is accepted.
REVIEW-INTEGRATION-2 is accepted already: <reason>
```
fix_loop.py:154-172 (the first is shadowed by argparse's "required" error, see issues).

### 6.3 Fix job on an accepted round (NEW, planning.py:211)
```
--fix-of REVIEW-INTEGRATION-2: the round was accepted (sae accept-review), so it needs no fix jobs. Add an ordinary job: sae job add <task> INTEGRATION-FIX-2 --kind implementation --reason "<why>"
```

### 6.4 `sae merge --accept-review` (CHANGED help only; output still `CORE: merged`)
`sae merge --help`: "--accept-review logs a decision event with the reason; the final report lists each finding of the last review round with it. Refuses a dropped job (sae job drop). An integration review round is accepted with sae accept-review instead." reviews.py:~795-797. Refusal for dropped: "CORE is dropped: dropped jobs never merge." (reviews.py:746, also 235).

### 6.5 `sae accept-review --help` (NEW, fix_loop.py:190-196)
"When the mode lets you decide, or on the owner's word at the round limit. The integration gate, the final validation and sae finish then proceed as after a pass, without --override; a park at the round limit ends. Logs a decision; the final report lists every finding of the round with this reason. A job review is accepted with sae merge <task> <ID> --accept-review "<why>" instead."

## 7. Job drop (all NEW)

### 7.1 Success
```
Dropped CORE, CORE-FIX-1, REVIEW-CORE, REVIEW-CORE-2: owner: the cache approach is wrong; rebuild it
Dropped jobs never merge; their branches and result files stay.
Next: sae next <task>
```
fix_loop.py:117-121 (plus any "Added REVIEW-INTEGRATION" line from `materialize_integration_review`).

### 7.2 Refusals
```
CORE-FIX-1 is a fix job of CORE and commits to its branch. Drop the group: sae job drop <task> CORE --reason "<why>"
INTEGRATE-X resolves the merge conflict of X; dropped alone, X could never merge. Drop the group: sae job drop <task> X --reason "<why>"
AFTER needs a job of the group of CORE. Change the needs first:
  sae job edit <task> AFTER --needs "" --reason "CORE is dropped"
AFTER is pending: it never ran. Remove it instead: sae job remove <task> AFTER --reason "<why>"
CORE is dropped already.
CORE is merged already; a drop cannot take it out of the task branch.
REVIEW-CORE is a review job; only writer jobs are dropped.
CORE cannot be dropped: in a task without worktrees its changes are already in the shared checkout. Undo them with a new job instead.   (variant: "a task without git")
X is running. Collect it first: sae collect <task> X
--reason is required: the owner's reason to drop the job.
```
fix_loop.py:74-105.

### 7.3 After a drop (NEW)
```
CORE is dropped: a dropped job never runs again.                      (sae dispatch, progress.py:427)
CORE is dropped: dropped jobs never merge.                            (sae merge, reviews.py:746)
--fix-of CORE: CORE is dropped; dropped jobs never merge. Add an ordinary job: sae job add <task> CORE-FIX-9 --kind implementation --reason "<why>"   (planning.py:202)
CORE (dropped)                                                        (waits_for reason of a job that needs it, graph.py:167)
```

### 7.4 `sae job drop --help` and `sae job --help` (NEW, fix_loop.py:128-139, planning.py:421-426)
Long description plus example `job drop claims-status STATUS-API --reason "owner: the cache approach is wrong; rebuild it"`.

## 8. Decision job pointers (`sae decision new`, decision job prompt)

### 8.1 `sae decision new` (CHANGED: `--from` optional, `--question` NEW)
```
Added DECISION-REVIEW-CORE-3-1. Dispatch it: sae dispatch <task> DECISION-REVIEW-CORE-3-1
```
```
Name what the decision is about: --from <job or review round>, --question "<question>", or both.
  sae decision new <task> --question "<question>"
```
findings.py:90-110.

### 8.2 Decision job file (job file body written by `decision new`; NEW/CHANGED)
Review round:
```
# DECISION-REVIEW-CORE-3-1: decision for REVIEW-CORE-3

## Objective
Advise on the review round REVIEW-CORE-3 (target CORE).

## Inputs
- The review file of the round: reviews/REVIEW-CORE-3.md.
```
Parked by sae at the limit (`--from CORE`):
```
## Objective
Advise on CORE: REVIEW-CORE-3 still requires changes at the review-round limit.

## Inputs
- The review round that parked it: reviews/REVIEW-CORE-3.md.
- The job file of CORE: jobs/CORE.md.
```
Question only:
```
# DECISION-1: decision

## Objective
Answer the question below.

## Question
Keep the cache?
```
Other literals: "Answer the decision request of {job}." with `- The section "Decision request" of {result}.` (parked worker job, was the only old form); "Advise on {job}." with `- The job file of {job}: ...` and `- Its result: ...`; "Answer the question below, about {job}." (question plus --from). findings.py:57-105.

### 8.3 Pointer lines in the decision job's prompt (NEW/CHANGED, was one "Decision request" pointer)
```
Job file — the question:               <path>/jobs/DECISION-REVIEW-CORE-3-1.md
Review round — the findings:          <path>/reviews/REVIEW-CORE-3.md
```
Other forms: `Decision request (section "Decision request"): <result>` (unchanged); parked by sae: `Review round that parked CORE: ...`, `Job file of CORE: ...`, `Result of CORE: ...`; any other job: `Job file of X: ...`, `Result of X: ...`. prompts.py:240-258, call prompts.py:~393.

### 8.4 `sae decision new --help` (CHANGED, findings.py:~427-440)
"--from takes any job or review round, --question a question; give one or both. ... The job it concerns need not park. A decision job only advises: it dispatches and collects also during a hold or while the task is parked."

## 9. Final report sections (all NEW; lifecycle.py:382 calls fix_loop_report_lines)

```
## Findings let go
- REVIEW-INTEGRATION: Dup config — let go: cosmetic
- REVIEW-INTEGRATION-2: Retry in LEFT — accepted: remaining findings are beyond the Project Stakes

## Accepted integration rounds
- REVIEW-INTEGRATION-2: remaining findings are beyond the Project Stakes

## Dropped jobs
- CORE (with CORE-FIX-1, REVIEW-CORE, REVIEW-CORE-2): owner: the cache approach is wrong; rebuild it
  Their branches stay; nothing of them was merged.
```
fix_loop.py:293-311, let_go_lines fix_loop.py:250-290. Other literals: `- REVIEW-X: <summary>` (old let-go without number); `- REVIEW-X: every finding (no finding titles in its review file) — accepted: <reason>`; `finding N` when the title is unknown. Agent decisions that are let-go are no longer repeated under "To check before you merge" (lifecycle.py:~385).
The `sae finish --help` text also changed (lifecycle.py:728-733).

## Possible issues

1. PARK_OPENING says "a fix job unparks the job" but is also used for the task park, where nothing is parked as a job (park_story.py:19).
2. The Options block (about 15 lines) is printed in full three times for one park: collect message, `sae next`/`sae status`, and the dispatch refusal. The collect message says "The story to relay ... sae next", yet it already holds the options.
3. "change the approach" for a task park prints `sae job drop <task> <ID> ...` with an unfilled `<ID>`; the "another round" option lists a fix job while PARK_OPENING says "Add no fix job" (the intent is "after the user answers", the wording does not say so).
4. Job park has no "close anyway"; the task park has it. Job park text also omits that `sae merge --accept-review` is an agent decision "on the owner's word" at the limit, while PARK_OPENING says "in every mode".
5. "Triage first (execute.md, Loop step 3)" and "Decision flow" point into references/modes/execute.md; the path is not given, and the agent must find the file.
6. Lead line differs by target: job round says "CORE: changes required", the preceding line says "REVIEW-CORE: done — verdict: changes-required" (repetitive). Job round message has no "close anyway" but the integration one has (inconsistent).
7. Job fix command in 1.1 uses `--reason "REVIEW-CORE: changes required"` (a filled reason) while the park, `sae next` and finish messages use `"<finding>"`.
8. `--reason is required` text in `sae accept-review` and `sae job drop` is unreachable: argparse marks `--reason` required and prints its own usage error first (fix_loop.py:74, 154).
9. `sae job drop` success does not tell the agent that the final report lists the drop or what to do with a task whose only remaining jobs are dropped; "Next: sae next" only.
10. Final report "## Reviews" still lists `REVIEW-CORE → CORE: changes-required` for a dropped job and the Jobs list shows `REVIEW-CORE-2 · dropped · not dispatched`, which reads as noise.
11. The same decision-job inputs are built twice with different wording: job file (findings.py:57-82, relative paths, "Advise on...") and prompt pointers (prompts.py:240-258, absolute paths). Two places to keep in sync.
12. Words alternate between "owner" and "user" in the same message (PARK_OPENING "the user's"; story head "parked for the owner"; "(only on the user's word)"; accept line "owner's word").
13. Task park story prints `Task: <title>` taken from the task title; in the demo it equals the slug, but an empty title would print `Task: None` (park_story.py:296).
14. `let_go_errors` for a review id whose review file has no numbered findings says "its review lists no numbered findings yet", which blocks the let-go and gives no way forward.
