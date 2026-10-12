---
title: Claude Code and Codex only
type: business
status: accepted
date: 2026-10-06
source: DL-02, design interview 2026-10-06
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/agents/openai.yaml, skills/shape-and-execute/scripts/sae_lib/config.py, detect_harness, HARNESSES]
---

# Claude Code and Codex only

## Context
Dispatch, external reviews, permissions and harness detection differ per harness. Each
supported harness costs a path in `sae` and in the references.

## Decision
[human] The skill supports Claude Code and Codex, with parity between them. No other harness,
no Orca integration.

## Why
The owner on Orca: "Relatively few people use it.". Agent's reasoning: these are the two
harnesses the owner uses, and every mechanism must work in both (worktrees by `sae`, explicit
model and effort, cross-harness review), so each extra harness multiplies that work.

## Rejected options
- Other harnesses.
- An Orca integration.

## Consequences
- Other harnesses and Orca stay possible later features, not part of the design.
