---
title: Tiers L1 to L4 with tiers in cells on by default
type: architecture
status: accepted
date: 2026-10-12
source: DL-96, task 2026-10-08-1733--sae-dogfood-fixes (R2, R6, R7); task 2026-10-12-1846--sae-findings-docs [SEED-PROPOSAL]
applies-to: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/assets/viewer/settings.js, skills/shape-and-execute/references/modes/setup.md, cell_use, tiers_in_cells, tiers]
---

# Tiers L1 to L4 with tiers in cells on by default

## Context
Routing tables have many cells. Changing one model everywhere means editing every cell, and
some owners prefer to see the model in each cell.

## Decision
[human] A tier (L1–L4) is a named model · effort; editing a tier changes every cell that uses
it. Tiers are optional: the switch "tiers in cells" picks whether cells use their tier or their
own model · effort. It is on by default, also in setup's proposal.

## Why
- "easier to understand". The owner wants both views: "Offer both views because one may be visually overwhelming.".
- The default stays on although the owner works with it off (2026-10-12): "Keep tiers enabled by default.".

## Consequences
- The seed values moved out of the decision log: setup proposes the owner's tuned config (see
  [Setup explains itself and proposes the owner's tuned config](2026-10-12-setup-explains-itself-and-proposes-the-o.md)).
