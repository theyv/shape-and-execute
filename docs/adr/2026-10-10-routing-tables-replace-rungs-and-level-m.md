---
title: Routing tables replace rungs and level maps
type: architecture
status: accepted
date: 2026-10-10
source: DL-95, task 2026-10-08-1733--sae-dogfood-fixes (R1, R2, Q4, Q6, Q7; items 1, 19; [ROUTING-TABLES], [DECISION-ROUTING-TABLES])
applies-to: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/routing.py, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, routing_layers, effective_routing, resolve_model, routing_tables_text]
---

# Routing tables replace rungs and level maps

## Context
The first design had three rungs per harness and a map from level to rung. The owner could not
tell which model `balanced` or `max` used.

## Decision
[joint] The user config holds one routing table per harness and phase (research, planning,
execution, review). Rows are the levels, columns the difficulties; a cell names a model ·
effort, or a tier.

## Why
- The owner: "A table could make this easier to understand.". What you
  see is what you edit.
- A gap between two rungs ("a substantial gap") could not be filled without a fourth rung.

## Rejected options
- Three rungs per harness with a level map (the first design).
- Four rungs instead of three: still hides the model behind a name.
- The review model following the chosen level (`economy` and `balanced` → L2, `max` → L3): the
  review phase has its own table.
