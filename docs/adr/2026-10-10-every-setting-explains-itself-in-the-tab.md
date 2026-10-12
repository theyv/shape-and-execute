---
title: Every setting explains itself in the tabs Task, Project and Global
type: architecture
status: accepted
date: 2026-10-10
source: DL-125, task 2026-10-08-1733--sae-dogfood-fixes (D10, R1, R4, R5, R6; item 4; [VIEWER-SETTINGS-HELP]); DL-26, design interview 2026-10-06
applies-to: [skills/shape-and-execute/assets/viewer/settings.js, skills/shape-and-execute/assets/viewer/settings.css, skills/shape-and-execute/scripts/sae_lib/server.py, settings_data]
---

# Every setting explains itself in the tabs Task, Project and Global

## Context
Settings exist on three levels (global, project, task). The owner wants to understand at once
what a setting does.

## Decision
[human] Every setting on every tab has a `[?]` that explains it and each of its options. The
interaction mode is a five-position switch. Review points are checkboxes `spec`, `plan`,
`jobs`, `integration`. The tabs are Task, Project and Global, in this order. The header's
settings card is editable in place.

## Why
- Settings must be understood without reading docs.
- The task level changes most often, so it comes first.

## Rejected options
- A "?" help for two settings levels only (the first form at the plan gate).
