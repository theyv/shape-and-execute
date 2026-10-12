---
title: Cheap decisions that keep the door open for teams
type: architecture
status: accepted
date: 2026-10-10
source: DL-61, design interview 2026-10-06 (D31-D34); DL-138, task 2026-10-08-1733--sae-dogfood-fixes (DESIGN-DOCS)
applies-to: [skills/shape-and-execute/scripts/sae_lib/tasks.py, skills/shape-and-execute/scripts/sae_lib/lifecycle.py, skills/shape-and-execute/scripts/sae_lib/gitutil.py, skills/shape-and-execute/references/commit-message.md, git_user, author, schema]
---

# Cheap decisions that keep the door open for teams

## Context
The system is for one person now. The owner asked for small design decisions that keep the
door open for teams and larger organizations, without paying for that today.

## Decision
- [agent] Committed files hold only relative paths. `state.json`, `settings.json` and the user
  config carry a schema version. Tasks record their `author`. Personal config (models,
  routing, languages, project defaults) stays outside the repository; shared facts live in
  `.tasks/repo/`.
- [human] Model traceability: every attempt records harness, model, effort, start, end and
  tokens; commits carry `Task:`, `Job:` and `Model:` trailers.

## Why
- Records work on every clone and machine; tools can migrate old records; the team sees who
  started what.
- Which model produced which work, and the cost per task. The owner asked for this explicitly.
- Team members keep their own subscriptions, models and languages; the repository stays
  neutral.

## Consequences
- `task.worktree` and `task.home` in `state.json` are absolute paths: local facts that other
  clones ignore, an exception to the relative-path rule.
- Not addressed on purpose: roles, assignment, several people on one task, team views, central
  storage, claims (see [Backlog files go into git like findings](2026-10-06-backlog-files-go-into-git-like-findings.md)).
