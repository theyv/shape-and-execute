---
title: Explicit invocation only
type: architecture
status: accepted
date: 2026-10-06
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/agents/openai.yaml, disable-model-invocation, allow_implicit_invocation]
---

# Explicit invocation only

## Context
The skill starts a heavy workflow: intake, research subagents, grilling, worktrees, a graph of
jobs. Both harnesses can invoke a skill implicitly from its description.

## Decision
[human] Only the user's explicit call starts the skill: `disable-model-invocation: true` in the
`SKILL.md` frontmatter (Claude Code; the owner found the flag) and
`policy.allow_implicit_invocation: false` in `agents/openai.yaml` (Codex).

## Why
Agent's reasoning: a heavy workflow must never start by accident.

Facts behind the flags: [research/claude-code-facts.md](research/claude-code-facts.md) ("Explicit
invocation only") and [research/codex-facts.md](research/codex-facts.md) ("Skills").
