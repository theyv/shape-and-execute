# Intent: A short "fast lane" mode of shape-and-execute for mini tasks

**Status: rough idea. Not shaped [human].**

## Problem
For a mini task the full flow costs too much. The owner (2026-10-14): "Add a short fast-lane workflow for small tasks. The existing process is useful, but some steps should be skipped.".

sae itself stays useful (state, worktree, research jobs, routing, review at the
end). The ceremony around it is the cost.

## The run that showed it
A small filter change in another of the owner's repositories (2026-10-14). The
owner started it with: "This task does not need a separate shaping phase. Combine the spec and intent, plan one job, and start it without further questions. Run preliminary research if needed.".

What the orchestrator did, by hand:
1. `sae new --from <backlog item>`.
2. Two research jobs on Sonnet in parallel (useful: they changed the solution).
3. A short `specs.md` written straight from research, no grill rounds.
4. `sae set review=integration` (spec and plan reviews off), logged as `[human]`.
5. `sae approve spec`, one job added inline, `sae approve plan`, `sae start`.
6. Mid-execution: an amendment and one more job with a model override
   (`sae job override --model sonnet`) on the owner's word.

Friction seen:
- The orchestrator had to load `shape.md`, `plan.md` and `execute.md` in full
  to find which steps to skip.
- `sae check` warned "plan.md has no Riskiest assumptions section" for a one-job
  inline plan with no `plan.md`.
- After `sae start` the task folder exists only in the task worktree. Later
  amendments had to be written there; the home checkout path was gone.
- The owner still wanted one stop: "Show me the spec summary before starting the job.". "Do not ask further questions" did not mean "provide no information". A plain-words
  spec summary before the first dispatch was the one checkpoint that mattered.

## Proposed outcome (direction, not decided)
A short reference file (for example `references/modes/fast.md`) or a mini skill
that, for a mini task, runs: intake → optional research on a cheap model →
short spec → one plain-words spec summary to the owner → one inline job →
integration review → finish. Spec and plan reviews off by default. One file to
load instead of three.

## Open questions
- Mode file inside shape-and-execute, or a separate mini skill that calls `sae`?
- A `sae` preset (for example `sae new --fast`) that sets the review points and
  skips the plan gate, or only instructions?
- Which checks to relax for a one-job task (the plan.md warning above).
- When does the orchestrator leave the fast lane and fall back to the full flow
  (research shows a bigger task, more than one or two jobs)?
- Is the spec-summary stop always on, or only when the owner asks?

## Related
- Decision record draft "Every task gets a spec, a small task saves on reviews" (2026-10-13;
  not in this repository yet). The fast lane must keep it.
