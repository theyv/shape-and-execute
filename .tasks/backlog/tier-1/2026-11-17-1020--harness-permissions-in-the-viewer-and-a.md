# Intent: Harness permissions in the viewer, and a safe default when a harness cannot run a job

## Problem

A recent task routed its implementation jobs (docs and end-to-end tests) to Codex. The Claude
orchestrator started them with `codex exec -s workspace-write`. In that sandbox the Codex worker
could not commit (no Codex permission profile for `.git` writes) and could not open the tsx IPC
socket, so the test commands failed. The orchestrator then moved every Codex-routed
implementation job to the Claude harness (Sonnet) on its own decision. The owner's routing was
silently not followed for the rest of the task, and the owner found out only by asking.

An earlier task in the same repository ran the same kind of jobs on Codex without this problem,
also with a Claude orchestrator. Nothing in the task records says which sandbox or permission
setup made that work, so the next orchestrator could not repeat it.

`sae setup snippets` already prints a Codex permission profile and Claude Code settings, but
applying them is a manual step outside the viewer, and nothing checks them before a task
dispatches a job to that harness.

## Goal

Make the permissions of each harness (Claude Code and Codex) visible and configurable from the
viewer, and give `sae` a reasonable default for the case where a routed harness cannot run a job.

### Success means

- The viewer shows, per harness, whether the permissions that jobs need are in place (git
  writes, the worktree root, sockets and network the verify commands need, subagent cap), and
  can apply the recommended setup after the owner confirms.
- `sae doctor` (or `sae start`) detects a missing permission before the first dispatch to that
  harness, not after a worker fails.
- The exact command and sandbox mode used for each external-harness job are recorded in the
  task state, so a later task can see how an earlier one ran.
- When a routed harness cannot run a job, the default behavior is defined and visible: for
  example, ask the owner (or notify when away) before falling back to another harness, and
  record the fallback as a routing exception that the viewer shows.

## Open questions

- Which default fits when the owner is away: fall back and notify, park the job, or fall back
  only for some job kinds?
- Should a fallback switch back automatically once the permission is fixed, including for a
  running job (park the worker with a work-in-progress commit, resume on the routed harness)?
- Option A (a separate Codex profile, `codex -p shape-and-execute`) or option B (the global
  config) as the recommended default, and how `codex exec` from a Claude orchestrator picks it.
- How to cover verify commands that need local sockets or ports inside the Codex sandbox.
