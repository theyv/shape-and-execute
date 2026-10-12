---
title: The viewer in a sandbox, without a file fallback
type: architecture
status: accepted
date: 2026-10-10
source: DL-121, task 2026-10-08-1733--sae-dogfood-fixes (R4, [EDGE-NO-SOCKETS], [DECISION-AGENT-DEFAULTS])
applies-to: [skills/shape-and-execute/scripts/sae_lib/viewer.py, check_sockets, start_command, NoSockets, NoStateFolder, cmd_view]
---

# The viewer in a sandbox, without a file fallback

## Context
Codex without network access forbids local sockets, so the viewer server cannot start from
the agent's shell.

## Decision
- [human] The orchestrator still runs `sae view` first. When it fails, `sae` prints the one
  command that starts the server in the owner's terminal, and the orchestrator suggests running
  Codex with full access (`--yolo`), which the owner often uses. Nothing else in `sae` depends
  on the server.
- [agent] There is no `file://` fallback viewer.

## Why
- The owner often runs Codex with full access anyway.
- The viewer is optional: every command works without it. A second, static viewer would be a
  second code path for a rare case (agent's reasoning).

## Rejected options
- A `file://` fallback viewer.
