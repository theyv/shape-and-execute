---
title: Routing cells keep a tier and an own model and effort
type: business
status: proposed          # proposed | accepted | rejected | superseded
date: 2026-11-20
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi
applies-to: [skills/shape-and-execute/references/modes/setup.md, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/assets/viewer/]
revisit-when: the viewer or setup drops one of the two ways to set routes
---

# Routing cells keep a tier and an own model and effort

## Context
A lean audit of the routing tables in `setup.md` saw cells whose tier and own model · effort
disagree (for example `L3 · sonnet · high`, where L3 is opus · medium) and proposed one value
per cell. An agent took the two values for a defect. They are two ways to set routes on purpose.

## Decision
Every routing cell can keep both values: a tier (L1–L4) and its own model · effort. The switch
picks which one applies (`config.py` `cell_use`): **Tiers mode** (the default) or **Free mode**
(config key `tiers_in_cells`). The two modes are independent: a change in one never affects the
other. The default config of the setup proposal fills only the tiers; the first switch to Free
mode copies each tier into its cell, so the switch alone changes no route.

## Why
There are two kinds of users:
- A default user does not want a complex matrix with a different model for every action. They
  set four tiers (model · effort) once, and every cell maps to a tier. To change the strongest
  model, they change it in one place.
- An advanced owner turns the tiers off and sets model · effort per cell, for finer control.

In the owner's words: "Either the user picks the levels 1 to 4 and defines the whole config
with them, or they pick a config per action and get finer granularity. It may look odd in the
Markdown files, but it always worked, and in the user interface it is clear."

## Rejected options
- One value per cell (only a tier, or only model · effort): it removes one of the two use cases.
- Making the own model · effort always equal to the tier's: the own value is the advanced
  user's setting, not a copy.
- Shipping a second, hand-tuned default for Free mode: switching modes would change routes by
  itself, and two defaults double the upkeep when models change.

## Consequences
- In a config file, a cell's two values may differ. That is not a defect.
- The setup proposal in `setup.md` shows only tiers in cells.
- The viewer is where the owner reads routes; it shows the value the switch selects.
