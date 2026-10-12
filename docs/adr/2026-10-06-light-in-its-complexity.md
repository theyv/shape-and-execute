---
title: Light in its complexity
type: business
status: accepted
date: 2026-10-06
source: DL-05, design interview 2026-10-06
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references, skills/shape-and-execute/scripts/sae_lib]
---

# Light in its complexity

## Context
A workflow with phases, gates, jobs and reviews easily turns into ceremony: status changes,
mandatory files and questions that do not move the work.

## Decision
[human] The skill stays light in its complexity. Every design choice is filtered through this:
statuses change as side effects of real actions, a file exists only when it carries content,
defaults replace questions, and the owner's waiting time is used.

## Why
The owner: "Let's not overdo the ceremonies, so we don't end up changing statuses instead of doing the work." And: "light in its complexity".

## Consequences
- Later decisions cite this one when they reject a mechanism as ceremony (for example the
  drift check, the decision map for big work, per-role agent files).
