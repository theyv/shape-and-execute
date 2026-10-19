# Intent: Abandon a task and preserve it in an archive

**Status: rough idea. Not shaped [human].**

## Problem

Shape and Execute needs a way to stop pursuing a task when it did not work out
or the owner decides to abandon it, without treating it as successfully completed.

Example: in another task the owner had to start a new task because sae could not go back
from execution to shaping. The owner's note (2026-10-16): "We had to start a new task because we could not return to an earlier phase.". The agent's message then:
"Old task: closed as abandoned; the branch with the three prototypes stays. A new task is
better, because sae does not move a task from execution back to shaping. Your answers from round 1
are already in the intent." The owner: "Whether this is the right behavior still needs consideration."

## Direction to explore

Provide a task abandonment mechanism. Moving the task to an archive (for example
`archived`) is one possible approach, not a decided design. Preserve the reason
for abandoning it and the useful history.

## Open questions

- How should abandonment be represented in task state and storage?
- What happens to running jobs, worktrees, branches, and unfinished changes?
- Can an abandoned task be resumed, and how?

Design and implementation are deferred until this item is picked up [human].
