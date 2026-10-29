---
title: Invocation by explicit request
type: architecture
status: accepted
date: 2026-10-30
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/agents/openai.yaml, disable-model-invocation, allow_implicit_invocation]
---

# Invocation by explicit request

## Context
The skill starts a heavy workflow: intake, research subagents, grilling, worktrees, a graph of
jobs. Both harnesses can invoke a skill implicitly from its description.

Until 2026-10-30 the skill set `disable-model-invocation: true` (Claude Code) and
`policy.allow_implicit_invocation: false` (Codex). Then a quota handoff stalled a running task: the
new session was told to continue it, but the Skill tool refused the skill, so the task waited for
the owner to type the command by hand.

## Decision
[human] The agent may invoke the skill: neither flag blocks it. The description still limits it to
an explicit request, from the user or from a handoff the user set up.

## Why
Agent's reasoning: a handoff must be able to resume a running task without the owner present, and
the description is enough to keep a heavy workflow from starting by accident.

Facts behind the flags: [research/claude-code-facts.md](research/claude-code-facts.md) ("Explicit
invocation only") and [research/codex-facts.md](research/codex-facts.md) ("Skills").
