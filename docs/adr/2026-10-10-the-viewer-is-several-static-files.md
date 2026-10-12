---
title: The viewer is several static files
type: architecture
status: accepted
date: 2026-10-10
source: DL-122, task 2026-10-08-1733--sae-dogfood-fixes (planner)
applies-to: [skills/shape-and-execute/assets/viewer, skills/shape-and-execute/assets/viewer/index.html, skills/shape-and-execute/assets/viewer/app.js, skills/shape-and-execute/assets/viewer/task-views.js, skills/shape-and-execute/assets/viewer/settings.js]
---

# The viewer is several static files

## Context
The viewer was one HTML file, a requirement of `file://`. With the viewer server it can be
served as several files.

## Decision
[agent] `index.html`, shared `app.css` and `app.js`, `task-views.*` and `settings.*`, served by
the viewer server. Classic scripts, no build step, no external requests.

## Why
The single file existed for `file://`. A split lets two jobs edit the UI in parallel.

## Rejected options
- A single HTML file (the earlier rule of the viewer spec).
