---
title: Routing on three levels, global, project and task
type: architecture
status: accepted
date: 2026-10-10
source: DL-99, DL-138, task 2026-10-08-1733--sae-dogfood-fixes (R4, R5, R6, Q18; [PROJECT-DEFAULTS], [ROUTING-TABLES], DESIGN-DOCS)
applies-to: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, routing_layers, effective_routing, project_key, project_entry, cmd_project_set, change_project]
---

# Routing on three levels, global, project and task

## Context
Defaults and routing lived only in the global user config. Some repositories and some tasks
need other models or defaults.

## Decision
- [human] Three levels: global (the user config), project (a personal override for one
  repository, kept in the user config, never in the repository) and task (`settings.json`). A
  project overrides the defaults for new tasks and, when the owner wants, single tiers or
  cells; a task may override single tiers or cells. A value resolves task → project → global.
  Model lists stay global.
- [agent] The routing block has one shape on all three levels; a lower level replaces a whole
  cell or a whole tier. Project entries are keyed by the repository's main worktree path.

## Why
The owner first called the project level "potentially unnecessary complexity", then accepted it. On routing
per project and task: "Model settings should be configurable at project and task level as well as globally."

## Rejected options
- Routing tables and model lists only global (R4): rejected for routing; model lists stay
  global.

## Consequences
- Moving a repository loses its project entries until they are re-keyed.
