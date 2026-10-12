---
title: The viewer is offered at task creation and opened at the plan gate
type: architecture
status: accepted
date: 2026-10-10
source: DL-109, task 2026-10-08-1733--sae-dogfood-fixes (D7, D11; [VIEWER-LINK-AT-NEW], [RESUME-HARNESS-HINT]); DL-26, design interview 2026-10-06
applies-to: [skills/shape-and-execute/scripts/sae_lib/viewer.py, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/references/modes/plan.md, viewer_link, cmd_new, --harness]
---

# The viewer is offered at task creation and opened at the plan gate

## Context
The viewer is a separate local server that shows the task graph and the settings. A task can be
resumed in either harness.

## Decision
- [human] The orchestrator opens the viewer at the plan gate, where the owner approves the graph
  and the settings.
- [agent] `sae new` prints a clickable viewer link, or the one command that starts the viewer.
- [agent] Every printed resume instruction names `sae start <task> --harness codex|claude`.

## Why
- The owner did not know the viewer existed.
- Resuming in the other harness needed a flag nobody mentioned.
- At the plan gate the owner approves the graph and the settings, which the viewer shows best
  (agent's reading).
