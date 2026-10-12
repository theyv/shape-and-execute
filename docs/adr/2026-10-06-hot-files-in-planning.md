---
title: Hot files in planning
type: architecture
status: accepted
date: 2026-10-06
source: DL-36, design interview 2026-10-06 (D8)
applies-to: [skills/shape-and-execute/references/roles/planner.md, skills/shape-and-execute/templates/plan.md, skills/shape-and-execute/templates/repo/profile.md, skills/shape-and-execute/scripts/sae_lib/graph.py, hot_files, scopes_overlap, scope]
---

# Hot files in planning

## Context
The needs graph says which jobs depend on each other. Jobs without a dependency can still edit
the same file (a lockfile, a route registry, migrations) and collide at merge.

## Decision
[agent] The planner handles hot files: each gets an owner job, or the edits move into one later
job, or a trivial conflict is accepted. Parallel writer jobs declare `scope`. The repo profile
may list known hot files.

## Why
Accepted by the owner after explanation: the graph captures logical dependencies; hot files are
physical collisions between logically independent jobs.
