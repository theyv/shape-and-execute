---
title: Workers commit on their branches
type: architecture
status: accepted
date: 2026-10-06
source: DL-48, design interview 2026-10-06 (Q26)
applies-to: [skills/shape-and-execute/references/roles/worker.md, skills/shape-and-execute/references/commit-message.md, skills/shape-and-execute/scripts/sae_lib/prompts.py]
---

# Workers commit on their branches

## Context
Someone has to commit each job's work: the worker, or `sae` alone at collect.

## Decision
[human] Workers commit on their job branch (or on the task branch in a chain) at meaningful
checkpoints.

## Why
The owner prefers granular history, so later validation and fixes can find where something
broke.

## Rejected options
- Only `sae` commits, and workers get no git rights (the agent's proposal).
