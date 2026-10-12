---
title: Every subagent gets an explicit effort
type: architecture
status: accepted
date: 2026-10-10
source: DL-100, task 2026-10-08-1733--sae-dogfood-fixes (D8, items 20, 23; [EFFORT-EVERY-DISPATCH])
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/scripts/sae_lib/prompts.py, skills/shape-and-execute/scripts/sae_lib/progress.py, build_prompt, external_review_command, cmd_dispatch]
---

# Every subagent gets an explicit effort

## Context
Claude subagents inherited the orchestrator's Opus · max and used up the limits.

## Decision
[agent] `sae dispatch` prints model and effort for both harnesses, never `n/a`, and the attempt
records both. In Claude Code the orchestrator passes them to the Agent tool; `claude -p` gets
`--effort`; Codex keeps `model_reasoning_effort` and the spawn parameters. `SKILL.md` tells the
orchestrator to set them exactly as printed.

## Why
- An inherited effort spends the quota of the orchestrator's level on every subagent.
- The Agent tool has a per-call `effort` (`research/HARNESS-FACTS.md` §1 in the record of task
  2026-10-08-1733--sae-dogfood-fixes). The earlier facts
  ([research/claude-code-facts.md](research/claude-code-facts.md), 2026-10-06) called it
  unavailable.
- The tool asks for an explicit instruction, so `SKILL.md` gives one.
