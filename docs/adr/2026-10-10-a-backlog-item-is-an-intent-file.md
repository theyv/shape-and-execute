---
title: A backlog item is an intent file
type: architecture
status: accepted
date: 2026-10-10
source: DL-63, second design interview 2026-10-06 (S2-Q4, S2-Q14, S2-D1); pickup moved by DL-114, task 2026-10-08-1733--sae-dogfood-fixes
applies-to: [skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/templates/intent.md, new_backlog_item, cmd_new, picked_up_items, --backlog, --from]
---

# A backlog item is an intent file

## Context
Deferred work needs a form and a way to become a task. The first design added a backlog phase
and a command to shape it.

## Decision
[human] A backlog item is `.tasks/backlog/<YYYY-MM-DD-HHMM--slug>.md` in the intent format,
created with `sae new "<title>" --backlog [--source <task>]`. `sae new "<title>" --from <file>`
turns it into a new task: the file's text becomes `intent.md`. The file stays until `sae start`
removes it on the task branch (see [Backlog pickup at start, and start is atomic](2026-10-10-backlog-pickup-at-start-and-start-is-ato.md)).

## Why
- The owner: "Use an optional parameter on the existing command to keep the interface simple.".
- No new phase and no new command; settings appear at `sae new` as for any task. A backlog file
  is not a task folder, so it can be committed (see [Backlog files go into git like findings](2026-10-06-backlog-files-go-into-git-like-findings.md)).
- `sae` removes the file deterministically when the task starts, so the backlog never lists
  started work as open; until then the item shows as picked up (agent).

## Rejected options
- `sae new --from` removing the file at once (the first design): started from another checkout,
  the removal failed halfway.
- A `backlog` phase with `sae shape <task>` (accepted first, then replaced by the owner's
  proposal).
- A shaping task with a flag.
- The file as a plain note without a flag: the agent could forget to remove it.
