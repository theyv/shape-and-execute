---
status: done
summary: PROMPT-TEXT (review, hold) ∥ EASY-DIFFICULTY → WRITER-LAUNCH (review) ∥ STAKES-IN-PROMPTS → FIX-LOOP-EXITS (review) → FIX-LOOP-GUIDANCE → VIEWER-SURFACES (review) → FINAL-VALIDATION (final)
validation: pass
changes: made
resolved: []
---

# Result: PLAN

## Validation evidence
- `sae check 2026-11-17-2334--sae-routing-harness-permissions-and-revi`: no errors. Warnings:
  - CODEX-LAUNCH and CLAUDE-LAUNCH: objective longer than one sentence. These are done shaping
    research jobs; the plan does not depend on them.
  - One scope overlap: WRITER-LAUNCH and STAKES-IN-PROMPTS share `progress.py` (status lines),
    `prompts.py` (different functions) and `tests/saetest.py`. These conflicts are expected to
    be trivial, and `plan.md` "Hot files" accepts them. FIX-LOOP-EXITS follows both.
- Coverage: every requirement is covered by at least one writer job, and FINAL-VALIDATION
  covers all of them. PROMPT-TEXT covers the prompt-text part of 17 requirements and resolves
  the finding about empty result sections ([RESULT-SECTIONS]).
- `brief.md` (about one page) and `plan.md` with riskiest assumptions are in the task folder.

## Decisions taken
- [agent] **The orchestrator must run `sae hold <task> PROMPT-TEXT --reason "owner reads the
  prompt diff ([PROMPT-JOB])"` before the first dispatch.** The hold becomes active once
  PROMPT-TEXT has been reviewed and merged, so the owner reads a diff that has passed review.
- [agent] EASY-DIFFICULTY runs in parallel with PROMPT-TEXT. It does not build on the prompt
  text, and it uses the wait for the owner's reading.
- [agent] Names the spec left to planning: `sae accept-review <task> <REVIEW-ID> --reason`, the
  `--let-go` flag on `sae log … decision`, the job status `dropped`, and `sae decision new
  --question`. They are fixed in `brief.md` "How", so the prompt text can name them first.
- [agent] [PROMPT-SAE] texts are constants in `prompts.py`, written by PROMPT-TEXT and wired by
  STAKES-IN-PROMPTS and FIX-LOOP-GUIDANCE. CLI help and orchestrator-facing output belong to
  the code jobs; PROMPT-TEXT lists the contradictions it finds in them.
- [agent] One viewer job at the end (VIEWER-SURFACES), except for the `easy` routing column,
  which EASY-DIFFICULTY adds while no other job touches the viewer.
- [agent] Review flags: PROMPT-TEXT, WRITER-LAUNCH, FIX-LOOP-EXITS, VIEWER-SURFACES (reasons in
  `plan.md`).
- [agent] This task runs on the home checkout's `sae`, which knows only three difficulties, so
  no job is `easy`.

## Risks
- The middle phase is now mostly serial (plan review F7), which makes the task take longer.
- `sae job park` is a new command that the spec does not name. It follows the orchestrator's
  choice for F2 and keeps the spec's "refuse before any state changes" for `sae dispatch`.

## Plan review (REVIEW-PLAN) applied
All eight findings hold against the code. Each was applied with the orchestrator's choice:
- F1: the drop group is the target plus the fix jobs on its branch; `--fix-of` and the merge path
  refuse a dropped target; a running member blocks the drop; a fix named alone is refused
  (FIX-LOOP-EXITS, brief).
- F2: `sae job park` parks a job that waits for the owner's fallback yes, which frees its slot;
  the yes resumes it (WRITER-LAUNCH, PROMPT-TEXT execute.md, brief). It is tested with one
  writer slot and a second writer.
- F3: the requested route travels in the fallback command's `--reason`, in a fixed format; a
  test covers a route requested only by a flag (WRITER-LAUNCH, brief).
- F4: Codex tiers are redefined, not renumbered, and the existing-config upgrade steps are added
  to setup.md (PROMPT-TEXT, which now also covers EASY-UPGRADE). FINAL-VALIDATION dispatches
  from a saved proposal with tiers on and off, and checks the upgrade.
- F5: an accepted review or round lists every finding title with the acceptance reason; it is
  tested with several findings and with a mixed round (FIX-LOOP-EXITS, brief).
- F6: there is one stakes location, the main worktree's profile, for shaping, status, dispatch and
  the viewer; it is tested from a linked worktree (STAKES-IN-PROMPTS, PROMPT-TEXT shape.md,
  brief).
- F7: FIX-LOOP-EXITS now needs WRITER-LAUNCH and STAKES-IN-PROMPTS and owns the merged gate order
  of `cmd_dispatch`; FIX-LOOP-GUIDANCE needs only FIX-LOOP-EXITS. Job IDs are unchanged.
- F8: once a target's fix got the approach paragraph, or the target parked at its limit, every
  later fix gets it (FIX-LOOP-GUIDANCE).
The choices are listed as [agent] in `plan.md` "Riskiest assumptions".

## Disputed findings
None.
