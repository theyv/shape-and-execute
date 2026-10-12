---
title: A process map starts every step
type: architecture
status: accepted
date: 2026-10-12
source: DL-106, task 2026-10-08-1733--sae-dogfood-fixes (D12 changed, R2, R3, R5; item 2; [PROCESS-MAP]); task 2026-10-12-1846--sae-findings-docs [OUT-MAP-LAYOUT], [VIEWER-PROCESS-MAP]
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/scripts/sae_lib/control.py, skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/scripts/sae_lib/server.py, skills/shape-and-execute/assets/viewer/task-views.js, process_map, map_steps, step_text, cmd_status, cmd_next]
---

# A process map starts every step

## Context
The owner often did not know where a task stood or what came next.

## Decision
[human] `sae status` and `sae next` print the process map. The orchestrator starts each step's
message with it, relayed in a code block as printed, and may annotate the current step. The
viewer's task view shows the same map. The layout (2026-10-12) is a template with no width
counting:
- each phase name, with its emoji, on its own line;
- the phase's steps on fixed lines below it, `|` between steps;
- a `↓` line between phases;
- marks: `✓` done, `►` current, `□` pending (a pending approval gate too), `–` off.

Review steps have exact names. An approval is a gate, not a step (the owner's question in R2).

## Why
- A "what comes next" message was "very good".
- The first one-line form was too dense.
- The `↓` line shows progress, and an agent does not drop it as it drops blank lines.
- `⬥` for a pending gate read as already done.

## Rejected options
- One line for all phases: too dense.
- One line per phase, a blank line between phases and `⬥` for a gate (until 2026-10-12).
