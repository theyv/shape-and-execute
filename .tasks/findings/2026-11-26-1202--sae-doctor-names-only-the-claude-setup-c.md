---
type: defect
confidence: high
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/FIRST-RUN-WALKTHROUGH
paths: []
---

# sae doctor names only the Claude setup command when the config is missing

## Observation
In a Codex sandbox (harness: codex), 'sae doctor' without a config prints 'fix: Run setup mode: /shape-and-execute setup' (doctor.py line 41). Codex users type '$shape-and-execute setup'. config.py already has SETUP_FIX naming both; the missing-config check does not use it. Seen in the first-run walkthrough, fresh scenario with --codex.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
