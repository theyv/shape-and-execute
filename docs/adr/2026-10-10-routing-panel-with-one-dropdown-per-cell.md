---
title: Routing panel with one dropdown per cell and fixed colors
type: architecture
status: accepted
date: 2026-10-10
source: DL-126, task 2026-10-08-1733--sae-dogfood-fixes (R3, R4, R6, R7; [VIEWER-ROUTING-PANEL], [DECISION-FIXED-COLORS])
applies-to: [skills/shape-and-execute/assets/viewer/settings.js, skills/shape-and-execute/assets/viewer/settings.css, skills/shape-and-execute/assets/viewer/app.css]
---

# Routing panel with one dropdown per cell and fixed colors

## Context
The routing tables must be readable and editable in the viewer. A mockup offered three
variants (`research/MOCKUP-ROUTING.md` and `prototypes/routing.html` in the record of task
2026-10-08-1733--sae-dogfood-fixes).

## Decision
[human] Variant C: one model · effort dropdown per cell. Colors are fixed and discrete: a
model's color comes from its place in the model list, a tier's from its number, and each effort
word has its own; `ultra` is `max` underlined. Levels and other often-changed settings come
first; routing and models lower. The accepted mockup is `prototypes/routing.html`, with the R7
changes (`cross-harness`, colored tooltips, semi-transparent planned nodes, the override
dropdown on the model label).

## Why
The owner: "Use fixed colors: blue for L1 and yellow for L2.", "Make the interface feel natural.".

## Rejected options
- A cool-to-warm color gradient: it hid the steps.
- Variant A (two dropdowns per cell) and variant B (a model dropdown plus an effort meter).
