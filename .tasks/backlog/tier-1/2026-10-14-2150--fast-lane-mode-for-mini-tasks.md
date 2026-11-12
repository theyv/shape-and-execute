# Intent: A short "fast lane" mode of shape-and-execute for mini tasks

**Status: direction decided in grilling on 2026-11-03 [human]; not specified yet.**

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

## Decisions from grilling (2026-11-03)

These came up while shaping task 2026-11-03-2111--viewer-review-fast-lane. The owner moved
fast lane out of that batch, to be picked up as the next task [human].

- Why: sometimes the full process is not worth it for a change that could simply be typed into
  an agent; on the other hand, the trace (decision records and the like) is worth keeping [human].
- Flow: intake → optional research → short spec → one stop with a plain-words summary → the job
  is created automatically → a fresh worker implements it → integration review → finish [human].
- The orchestrator does not implement; a fresh worker does. The owner considered letting the spec
  author implement and chose the fresh worker [human].
- Models follow normal routing. Research and the worker need not run on a cheap model [human].
- After the spec and after the plan, ask the owner whether this task wants a spec review and a
  plan review. Sometimes it does, sometimes not [human].
- Owner's lean for a small task: job reviews off; the final integration review covers the jobs [human].
- Entry: the agent proposes the fast lane at intake and the owner confirms; the owner may also
  ask for it directly. The agent never picks it alone [human].
- Criteria are judgment, not hard thresholds. A fast-lane task may have two or three jobs when
  they are simple and independent and benefit from separate contexts. Rough signs: the change
  fits in one message to an agent, "done" is clear, the orchestrator can write the jobs inline
  without a planner, no open design decision, no risky area such as permissions or data
  migration. The skill must let this scale, not set a fixed job count [human].
- Wording of the criteria, accepted draft [human]:
  - When to propose: you could hand the whole change to agents after one short conversation. You
    write the spec and the jobs yourself, without a planner, and the owner can judge the result
    from one plain-words summary. The number of jobs does not decide: two or three simple,
    independent jobs fit, for example when separate contexts keep each worker focused. The owner
    confirms, or asks for the fast lane directly.
  - When to leave: stop and propose the full flow when any signal appears: jobs depend on each
    other (a contract, an order or shared files); a decision only the owner can make, with a real
    tradeoff; a risky area (permissions, deleting or migrating data, a public interface); research
    changes what the task is. Never switch alone; the owner decides.
- At every switch (proposal, entry, exit) the agent explains in a few lines what the fast lane is,
  what it skips, what it keeps, and how to leave it, so that a user who does not know the skill
  understands the choice [human].
- The switch messages are in English [human]. Their text should not live in SKILL.md: either
  `sae` prints it (for example on entry and exit), or a separate reference file holds it and is
  loaded only at a switch [human]. Which of the two is open.
- Every switch message follows one frame: what the fast lane is → what it skips and what it
  keeps → why now → how to change your mind [joint]. Sample messages:

  > ⚡ **This looks like a fast-lane task.**
  > The fast lane is a short path for simple changes:
  > - **skips:** a separate planner, spec, plan and job reviews, and several approvals;
  > - **keeps:** a spec with requirements, jobs in separate worktrees, a final review of the whole
  >   change, and the decision trail in the task files;
  > - **one stop:** I show a short plain-words summary; your "ok" starts execution. I also ask
  >   then whether you want a spec or plan review.
  >
  > Why here: the change fits in one conversation, it gives two independent jobs, and I see no
  > open decision or risky area. **Shall we take the fast lane?** (The full flow is fine too.)

  > ⚡ **Fast lane on.** I write a short spec and the jobs, then one stop with a summary. If
  > something bigger shows up, I stop and propose the full flow. You can switch at any time too.

  > ⚠️ **I propose to leave the fast lane.**
  > Research shows that the jobs depend on each other: both use a new `settings.json` format that
  > must be settled first. The fast lane expects simple, independent jobs; this needs a planner
  > and a review of the contract.
  > - **Full flow:** what we have stays (intent, research, draft spec); grilling, a planner and
  >   reviews per settings follow.
  > - **Stay in the fast lane:** I do it in order in one job, without a separate contract; you
  >   accept the risk of inconsistency.
  >
  > **Which do you choose?**

- Exit: when research or the spec shows dependent jobs, an open decision or risk, the agent
  stops and proposes the full flow; it does not switch alone [human].
- Mechanism: a reference file (for example `references/modes/fast.md`) plus a small `sae` preset
  (for example `sae new --fast`) that sets the review points and needs fewer approval commands [human].
- [agent] Already fixed since the original run: `sae check` warns about a missing "Riskiest
  assumptions" section only for two or more planned jobs.

## Open questions

- How the "one stop" and the two review questions fit together: one stop that asks both, or a
  stop after the spec and a short one after the plan.
- What the preset sets exactly, and whether one `sae approve` may cover spec and plan.

## Related
- Decision record draft "Every task gets a spec, a small task saves on reviews" (2026-10-13;
  not in this repository yet). The fast lane must keep it.
