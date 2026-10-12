---
title: sae checks the Codex subagent cap
type: architecture
status: accepted
date: 2026-10-07
source: DL-84, implementation 2026-10-07
applies-to: [skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/scripts/sae_lib/doctor.py, skills/shape-and-execute/references/modes/setup.md, codex_subagent_cap, codex_cap_text, max_threads]
---

# sae checks the Codex subagent cap

## Context
A Codex session holds only a few open subagents. Parallel writers, reviews and research then
fail with "agent thread limit reached", and nothing queues.

## Decision
Idea [human], numbers [joint]: `sae setup show`, `sae setup snippets` and `sae doctor` read the
Codex config. When a Codex session may hold fewer than 8 subagents, they recommend
`[agents] max_threads = 10`. Setup mode offers to apply it, after the owner agrees and with a
backup, like the permission profile.

## Why
- The owner: "If the limit is below eight, suggest raising it to at least eight, or possibly ten.".
- Facts ([research/codex-facts.md](research/codex-facts.md) §1, codex-cli 0.160.1):
  `max_threads` counts open subagents, not the root; the default is 3 for multi-agent v2
  models (all current default models) and 6 for v1. The owner's guess ("the default may be six") was
  right for v1 only.
- Why 8 and 10 (agent): up to 3 writers plus reviews, research and decision workers can be open
  at once. Claude Code allows 20 concurrent subagents by default, so the cap is a Codex problem
  only.
