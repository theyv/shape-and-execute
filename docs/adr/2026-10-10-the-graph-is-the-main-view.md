---
title: The graph is the main view
type: architecture
status: accepted
date: 2026-10-10
source: DL-124, task 2026-10-08-1733--sae-dogfood-fixes (items 16, 22; D9; [VIEWER-PLAN-FIRST])
applies-to: [skills/shape-and-execute/assets/viewer/task-views.js, skills/shape-and-execute/assets/viewer/task-views.css, skills/shape-and-execute/assets/viewer/app.js]
---

# The graph is the main view

## Context
The viewer has several tabs per task. The owner mostly looks at the job graph.

## Decision
[human] Plan is the default tab. Each job kind has its own border color, with a legend; a
running job has a dashed, animated border (static under reduced motion); model and effort on a
node use the routing colors, slightly muted. The left sidebar collapses, and the page remembers
it.

## Why
The owner: "The graph is the clearest view of the work.".
