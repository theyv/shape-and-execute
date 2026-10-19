# Intent: Make shape-and-execute worktrees work with Orca (browser, integration)

## Problem
The owner works in Orca and uses its embedded browser, but shape-and-execute worktrees do not
fit it yet. Owner's words (2026-10-14): "Make the worktrees work with the embedded browser and explore other useful integration features.".

## Goal
Decide how sae worktrees and Orca work together, then build the smallest version that the owner
really uses.

## Open questions
- What breaks today: do sae job and task worktrees show up in Orca, and can the Orca browser
  open the viewer or the app of a job worktree?
- Should sae create worktrees through the `orca` CLI (see the orca-cli skill) instead of raw
  `git worktree`?
- Which existing sae features does the owner not use (so that Orca replaces them instead of
  adding to them)? Candidates: own worktree handling, terminals, the viewer.
