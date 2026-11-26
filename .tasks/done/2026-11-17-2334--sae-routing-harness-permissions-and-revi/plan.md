# Plan: SaE routing, harness launches and review workflow

## Strategy
Prompt text first, in one job with a hold after it ([PROMPT-JOB]); the owner reads that diff
before the code builds on it. The `easy` difficulty does not build on the prompt text, so it runs
alongside. After the hold, harness launches and stakes run in parallel; the fix loop follows
(its exits, then its guidance), after the launches, because both change the gate order in
`cmd_dispatch`. One viewer job wires the new data into the viewer at
the end, because the viewer is one dense context and four parallel jobs would collide in
`task-views.js` and `server.py`. One final validation runs the full suite.

**Orchestrator, before the first dispatch:**
`sae hold <task> PROMPT-TEXT --reason "owner reads the prompt diff ([PROMPT-JOB])"`. The hold
becomes active once PROMPT-TEXT is reviewed and merged.

## Jobs at a glance
- `PROMPT-TEXT` — every prompt change from the spec drafts, the [PROMPT-SAE] constants, and a contradiction report.
- `EASY-DIFFICULTY` — `easy` in routing, validation, setup show/save, status, doctor and the viewer's routing tables.
- `WRITER-LAUNCH` — COMMANDs for jobs on the other harness, launch records, CLI check, fallback rule, `sae job park`, routing exceptions.
- `STAKES-IN-PROMPTS` — stakes lookup, the stakes line in every prompt, `stakes:` in status, the profile writer.
- `FIX-LOOP-EXITS` — decision jobs at any time, `sae job drop`, `sae accept-review`, let-go logging and the final report.
- `FIX-LOOP-GUIDANCE` — approach paragraph from round N−1, Approach proposal pointer, the park story.
- `VIEWER-SURFACES` — Project settings with stakes, launch records, exceptions, bypass line, park story, dropped jobs.
- `FINAL-VALIDATION` — full suite and every acceptance check.

## Parallelism
- `PROMPT-TEXT` ∥ `EASY-DIFFICULTY`: no shared file; `easy` does not use the new prompt text.
- After both: `WRITER-LAUNCH` ∥ `STAKES-IN-PROMPTS`. They need `EASY-DIFFICULTY` because it
  changes `common.py`, `config.py`, `routing.py` and `progress.py` first.
- `FIX-LOOP-EXITS` waits for `WRITER-LAUNCH`: both change the order of the checks in
  `cmd_dispatch` (CLI check before any state change; decision jobs through a hold or park).
  `FIX-LOOP-EXITS` owns the merged gate order. It also waits for `STAKES-IN-PROMPTS` (status
  lines in `progress.py`). The lost parallelism is accepted.
- `FIX-LOOP-GUIDANCE` waits for `FIX-LOOP-EXITS` (same park messages in `reviews.py`; the story
  names the drop and accept commands).
- `VIEWER-SURFACES` waits for all backend jobs: it shows their data.
- Not split further: the drop, accept and decision changes all touch the same gates in
  `graph.py` and `reviews.py`, so they stay in one job.

## Hot files
- `references/`, `templates/`, `SKILL.md` → edited only in `PROMPT-TEXT`.
- `scripts/sae_lib/prompts.py` → `PROMPT-TEXT` (constants), then `WRITER-LAUNCH` (command builder)
  beside `STAKES-IN-PROMPTS` (a line in `build_prompt`): different functions, trivial conflict
  accepted; then `FIX-LOOP-GUIDANCE`.
- `scripts/sae_lib/progress.py` → `EASY-DIFFICULTY` first; then `WRITER-LAUNCH` and
  `STAKES-IN-PROMPTS` (status lines: trivial conflict accepted); `cmd_dispatch` gate order:
  `WRITER-LAUNCH`, then `FIX-LOOP-EXITS` (owner of the merged order), then `FIX-LOOP-GUIDANCE`.
- `scripts/sae_lib/lifecycle.py` `final_report` → `WRITER-LAUNCH`, then `FIX-LOOP-EXITS` (ordered).
- `scripts/sae_lib/planning.py` → `EASY-DIFFICULTY`, `WRITER-LAUNCH` (`sae job park`),
  `FIX-LOOP-EXITS` (`sae job drop`), ordered.
- `scripts/sae_lib/reviews.py` → `FIX-LOOP-EXITS`, then `FIX-LOOP-GUIDANCE`; `WRITER-LAUNCH`
  changes only collect's token reading.
- `scripts/sae_lib/common.py` → `EASY-DIFFICULTY`, then `FIX-LOOP-EXITS` (ordered).
- `scripts/sae_lib/graph.py` → `FIX-LOOP-EXITS` only.
- `scripts/sae_lib/server.py`, `assets/viewer/` → `EASY-DIFFICULTY` (routing tables), then
  `VIEWER-SURFACES` (ordered).
- `tests/saetest.py` → shared helpers; trivial conflict accepted. Each job adds its own test module.

## Integration points
- The fixed interfaces in `brief.md` "How": `PROMPT-TEXT` writes them into `execute.md`;
  `FIX-LOOP-EXITS` and `STAKES-IN-PROMPTS` implement them as written.
- The [PROMPT-SAE] constants: written by `PROMPT-TEXT`, called by `STAKES-IN-PROMPTS` and
  `FIX-LOOP-GUIDANCE`.
- The data contracts for the viewer: each backend job describes its new state fields and
  functions in its result; `VIEWER-SURFACES` reads those results.

## Final validation
`FINAL-VALIDATION` (`--final`) runs the full suite once and checks every acceptance item, after
the integration review. No other job runs the full suite.

## Review flags
- `PROMPT-TEXT`: a foundation for every later job (constants, templates, command names), and
  the owner reads it at the hold.
- `WRITER-LAUNCH`: launches agents without a sandbox, must keep private paths out of records and
  refuse before any state change; real CLIs cannot run in tests.
- `FIX-LOOP-EXITS`: changes finish and integration gates; a mistake skips or blocks a gate.
- `VIEWER-SURFACES`: UI, hard to check by tests, and it writes the repository profile.
- Not flagged: `EASY-DIFFICULTY`, `STAKES-IN-PROMPTS`, `FIX-LOOP-GUIDANCE`. Their tests check them,
  and the integration review covers them.

## Risks and adaptation triggers
- The owner changes texts or command names at the hold: update `brief.md` "How" and the
  affected job files before the release.
- The PROMPT-TEXT result lists CLI help contradictions outside every job's scope: add them to
  the closest job's Inputs, or file a finding.
- A merge conflict between `WRITER-LAUNCH` and `STAKES-IN-PROMPTS` that is more than trivial:
  resolve it in `FIX-LOOP-EXITS`, which follows both.
- `FIX-LOOP-EXITS` does not fit one context: move `sae job drop` into a job of its own after it.
- `WRITER-LAUNCH` cannot read a writer COMMAND's tokens without changing the result contract:
  it parks, and a decision job compares the options.
- `VIEWER-SURFACES` finds backend data missing: a small server-side read is in its scope; a
  logic change parks the job.

## Riskiest assumptions
- [agent] `EASY-DIFFICULTY` may run before the owner reads the prompt diff: it does not build on
  the prompt text, and the hold is meant for jobs that do.
- [agent] Command and flag names chosen by the plan: `sae accept-review`, `sae log … --let-go`,
  the `dropped` status and `sae decision new --question`. The prompt text names them before the
  code exists.
- [agent] [PROMPT-JOB] "the text that `sae` prints into prompts" means the [PROMPT-SAE] texts. CLI
  help and orchestrator-facing output (fallback rule, park story, notices) belong to the code jobs
  that own those commands; PROMPT-TEXT only lists their contradictions.
- [agent] Writer jobs reach the other harness only through an override or a dispatch flag, so
  the bypass line in `sae status` follows overrides for non-review jobs.
- [agent] The final report finds let-go findings by a marker on the decision event, not by
  reading summaries. For an accepted review or round it lists every finding title of that review
  with the acceptance reason; no per-finding flags (plan review F5).
- [agent] The drop group is the target and every fix job that commits to its branch; `--fix-of`
  and the merge path refuse a dropped target; a running member blocks the drop; naming a fix
  job alone is refused with its target's ID (plan review F1).
- [agent] A job that waits for the owner's yes to a harness fallback is parked with
  `sae job park` (reason names the fallback): it leaves the ready queue and frees its slot; the
  yes resumes it on the fallback route (plan review F2). The spec's "refuse before any state
  changes" still holds for `sae dispatch` itself; the park is a separate command.
- [agent] The requested route travels in the fallback command's `--reason`, in a fixed format
  that `sae` writes and reads; no new flag (plan review F3).
- [agent] Codex tiers are redefined by the owner's table, not renumbered. Codex execution and
  research: balanced L1–L4 by difficulty, economy one tier down (floor L1), premium one tier up
  (cap L4), each cell with its tier's model · effort; planning and review keep their
  model · effort and take the tier with the nearest pair (plan review F4).
- [agent] One stakes location: the main worktree's `.tasks/repo/profile.md` (plan review F6).
- [agent] Once a target's fix got the approach paragraph, or the target parked at its limit,
  every later fix of that target gets it, whatever the limit is raised to (plan review F8).
- [agent] Stakes are empty when the five template bullets have no value once comments are
  stripped; the "Not set by the owner" line counts as content, so the profile is the source.
