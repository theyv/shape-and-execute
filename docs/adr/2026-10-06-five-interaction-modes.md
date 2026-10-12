---
title: Five interaction modes
type: business
status: accepted
date: 2026-10-06
source: DL-27, DL-28, DL-35, design interview 2026-10-06 (Q7, Q10, Q14)
applies-to: [skills/shape-and-execute/references/interaction-modes.md, skills/shape-and-execute/scripts/sae_lib/common.py, skills/shape-and-execute/scripts/sae_lib/findings.py, INTERACTION_MODES, cmd_decision_new, interaction]
---

# Five interaction modes

## Context
During execution, agents meet decisions the spec does not settle. Sometimes the owner sits at
the computer and wants to answer; sometimes a morning run must finish on its own.

## Decision
- [human] Five modes: `full-auto`, `auto`, `critical-only`, `collaborative`, `interactive`.
  The table of decision classes is `[joint]`: each mode adds one decision class to "ask". The
  name `critical-only` and the settings key `interaction` are `[agent]`, chosen to be
  descriptive.
- [joint] A spec gap is an implementation decision. A spec change is an amendment, handled
  according to the mode.
- [human] Parked work never blocks independent work.

## Why
The agent first proposed three modes. The owner kept the most interactive one ("I prefer answering questions so the result matches what I want.") and split autonomy, so morning runs finish
instead of stopping halfway.

## Rejected options
- Three modes (the agent's first proposal).
