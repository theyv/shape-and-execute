---
title: Codex detection by its thread ID variable
type: architecture
status: accepted
date: 2026-10-07
source: DL-85, implementation 2026-10-07
applies-to: [skills/shape-and-execute/scripts/sae_lib/common.py, skills/shape-and-execute/scripts/sae_lib/config.py, CODEX_ENV_VARS, CODEX_THREAD_ID, detect_harness]
---

# Codex detection by its thread ID variable

## Context
`sae` must know which harness runs it, to print the right dispatch and fallback commands.

## Decision
[agent] `sae` detects a Codex shell by `CODEX_THREAD_ID` (or `CODEX_SESSION_ID`), which the
Codex shell tool sets in every command.

## Why
`CODEX_SANDBOX` is absent with `danger-full-access`, so it cannot be used. Facts:
[research/codex-facts.md](research/codex-facts.md) §2.

## Rejected options
- `CODEX_SANDBOX`.
