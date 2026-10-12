---
title: Setup explains itself and proposes the owner's tuned config
type: architecture
status: accepted
date: 2026-10-12
source: DL-104, DL-96, task 2026-10-08-1733--sae-dogfood-fixes (D16, item 1, [SETUP-GUIDE]); task 2026-10-12-1846--sae-findings-docs [SEED-PROPOSAL]
applies-to: [skills/shape-and-execute/references/modes/setup.md, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, cmd_setup_show, cmd_setup_save, config_skeleton]
---

# Setup explains itself and proposes the owner's tuned config

## Context
The model setup was unreadable for the owner (item 1 of the dogfood fixes). A new user starts
with no config and has to fill model lists, tiers and eight routing tables.

## Decision
- [agent] The first setup shows a short guide: levels, difficulty, routing tables; settings
  change any time and per phase; where to change them. The proposal is shown as tables.
- [human] Setup mode proposes the owner's config as tuned on 2026-10-12 (snapshot
  `seed-config.json` in the record of task 2026-10-12-1846--sae-findings-docs): the model
  lists, the tiers L1–L4, and for every routing cell both the tier and the model · effort, with
  tiers in cells on.
- [agent] When the local Codex catalog lacks a seed family, the nearest stronger available
  family replaces it in the tiers and the cells, with the same effort when that model accepts
  it, else its nearest accepted effort. Without a Codex catalog the Codex part is left out. The
  proposal always passes `sae setup save` validation.
- The proposal stays advice for the agent in `references/modes/setup.md`; `sae` never reads it
  as config.

## Why
- The guide carries the owner's own example: "Plan with the higher-cost configuration and then switch to the lower-cost one, or the reverse.".
- A new user starts from values the owner tuned in real use, not from a first guess.
- A missing family must not break the proposal (spec review of 2026-10-12, finding 2; the owner
  approved the spec without choosing, so the replacement rule is `[agent]`).

## Rejected options
- The first proposal (until 2026-10-12): every known family in the lists and cells that pointed
  to tiers only. Replaced by the tuned config.
