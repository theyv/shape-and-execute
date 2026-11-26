---
title: Project stakes live in the repo profile, never in AGENTS.md
type: architecture
status: proposed          # proposed | accepted | rejected | superseded
date: 2026-11-20
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi
applies-to: [skills/shape-and-execute/templates/repo/profile.md, skills/shape-and-execute/scripts/sae_lib]
revisit-when:             # optional: when this decision stops holding
---

# Project stakes live in the repo profile, never in AGENTS.md

## Context
Agents over-engineer when they do not know what a failure costs. A short Stakes section (who
uses the project, acceptable breakage, what matters now, what not to build, what to build it
like) sets the level of care. SaE reviewers grade findings against it.

## Decision
SaE keeps a project's stakes in the `## Stakes` section of `.tasks/repo/profile.md` in the main
worktree. It reads an existing `## Stakes` section in AGENTS.md or CLAUDE.md only as a fallback,
and never writes to those files. Shaping asks once per repository; a skip writes a "not set"
line that tells agents to estimate the stakes themselves.

## Why
The owner does not want a tool to change files of their own agent setup. A passive section in
AGENTS.md also seemed to have little effect in a real project; SaE uses stakes actively, in each
role's prompt and where reviews and triage decide.

## Rejected options
- Writing the section into AGENTS.md: touches the owner's files, which tools may also generate.
- A separate `stakes.md` file: one more file, and a second copy that drifts.
- Promise lists per spec and a precedents file: cannot be complete or maintained.

## Consequences
One stakes source for status, dispatch, shaping and the viewer. Agents outside SaE see the stakes
only when the owner also puts them in AGENTS.md.
