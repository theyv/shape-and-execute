# Intent: Return a task to an earlier phase

**Status: rough idea. Not shaped [human].**

## Problem

`sae` cannot move a task from execution back to shaping or planning. In another task the owner
had to abandon the task and start a new one, because sae could not return to an earlier phase.
The owner then asked whether this is the right behavior.

## Goal

Decide whether and how a task can return to an earlier phase, for example when execution shows
that the spec is wrong.

## Existing behavior

- [agent] `sae abandon <task> --reason` already stops a whole task: phase `abandoned`, the reason
  in the events, branches kept, clean worktrees removed, dirty or failed worktrees kept. The next
  successful `sae finish` moves the record into `.tasks/done/`. The original item ("abandon a task
  and archive it") is covered by it [human, 2026-11-03].
- [agent] The documentation does not mention `sae abandon` yet; add one sentence when this item
  is picked up.

## Open questions

- Which phase changes are allowed: execution → planning, execution → shaping, planning → shaping?
- What happens to running jobs, worktrees, branches, merged work and approvals.
- Is it a new command, an option of `sae approve`, or a new task linked to the old one?

Design and implementation are deferred until this item is picked up [human].
