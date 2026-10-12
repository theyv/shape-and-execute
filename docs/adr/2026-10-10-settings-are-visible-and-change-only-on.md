---
title: Settings are visible and change only on the owner's word
type: architecture
status: accepted
date: 2026-10-10
source: DL-103, task 2026-10-08-1733--sae-dogfood-fixes (D13, D14, D20, items 5, 27; [SETTINGS-VISIBLE]); DL-58, design interview 2026-10-06 (Q9)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/control.py, skills/shape-and-execute/scripts/sae_lib/graph.py, settings_card, settings_diff, change_lines, writer_slot_notice]
---

# Settings are visible and change only on the owner's word

## Context
The owner never saw the interaction modes, had to ask where the writer limit came from, and an
agent removed the `plan` review point with no recorded reason.

## Decision
- [agent] At task start, the settings card comes with one sentence about the interaction mode
  and how to change it. Agents change task settings only when the owner asks; every change
  appears on the next next-step card. A notice that names a limit also names its source, for
  example the user-config key of the writer cap. The orchestrator sets only the task
  difficulty on its own.
- [human] Settings are asked while research runs; the research level comes in the first round,
  with the depth proposal.

## Why
- The owner must know what runs and why, and an agent must not quietly weaken a review.
- Asking while research runs uses the waiting time (the owner's idea).

## Rejected options
- A required reason field for every settings change (D20): it stayed open; the next card shows
  the change instead, which needs no field.
