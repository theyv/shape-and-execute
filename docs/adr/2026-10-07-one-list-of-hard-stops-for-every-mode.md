---
title: One list of hard stops for every mode
type: architecture
status: accepted
date: 2026-10-07
source: DL-29, design interview 2026-10-06 (D25); DL-74, genesis review 2026-10-07 (G2)
applies-to: [skills/shape-and-execute/references/interaction-modes.md, skills/shape-and-execute/references/roles/worker.md, skills/shape-and-execute/scripts/sae_lib/prompts.py, hard_stop_lines]
---

# One list of hard stops for every mode

## Context
Some actions are never safe for an agent alone, whatever the interaction mode: pushing,
secrets, deleting what the job did not create. The worker protocol once had its own, shorter
list of them.

## Decision
- [agent], refined [human]: hard stops hold in every mode, `full-auto` included. Destruction is
  allowed only for what the job created, or inside its own worktree.
- [joint] The hard stops live only in `references/interaction-modes.md`, section "Hard stops".
  The worker protocol points to that section, and the worker's dispatch prompt names it next to
  the interaction mode.

## Why
The worker's own shorter list had already lost two items. One of them was the rule that
protects pre-existing files in a folder without git, where there is no undo.

## Rejected options
- A second, shorter list in the worker protocol.
