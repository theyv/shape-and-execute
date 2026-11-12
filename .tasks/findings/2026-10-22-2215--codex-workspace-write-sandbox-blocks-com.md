---
type: defect
confidence: high
paths: [skills/shape-and-execute/scripts/sae_lib/prompts.py, skills/shape-and-execute/references/modes/execute.md]
---

# Codex workspace-write sandbox blocks commits in a job worktree

## Observation
A Claude orchestrator ran five implementation jobs as `codex exec -s workspace-write -C <job workdir> --add-dir <task worktree> --add-dir <repo .git>`. All five did their edits and checks, then parked: `git add` and `git commit` failed. A job workdir is a linked worktree; its index and refs live in the main repository's `.git/worktrees/<job>/`. The Codex sandbox keeps `.git` read-only even when it is listed with `--add-dir`. One job also could not run a package-manager install that takes a global lock outside the workdir. The work was complete but stranded, and every job needed a second run without the sandbox.

Until now the jobs had almost always run in the same harness as the orchestrator: subagents inherit the orchestrator's permissions, so the problem did not show. It appears as soon as a writer job runs in Codex from a Claude orchestrator (see the finding on cross-harness writer jobs).

## Evidence
- Worker result: `fatal: Unable to create '<common-git-dir>/worktrees/<job>/index.lock': Operation not permitted`.
- The same failure in 5 of 5 jobs, with `--add-dir` on the repository's `.git`.
- The existing review COMMAND uses `-s read-only`, so reviews never hit this.

## Cost
One full worker run per job wasted up to the commit, a park, a question to the user and a resume. Five parked jobs at the same time look like five separate problems.

## Suggestion
When sae builds a Codex COMMAND for a job that writes, use a mode that allows Git metadata writes: `--dangerously-bypass-approvals-and-sandbox` (the job is isolated in its own worktree), or a narrower setting if Codex offers one. Say in execute.md that a Codex writer cannot commit under `workspace-write`. Optionally, `sae doctor` checks this once with a test commit in a scratch worktree.
