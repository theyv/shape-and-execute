---
type: defect
confidence: medium
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/WRITER-LAUNCH-FIX-1
paths: []
---

# Codex review COMMAND in a task without git lacks --skip-git-repo-check

## Observation
WRITER-LAUNCH-FIX-1 added --skip-git-repo-check to Codex writer COMMANDs in tasks without git (launch.py command_line). The review branch of command_line (codex exec -s read-only -C <task root>) still lacks it, so an external Codex review in a no-git task likely cannot start. Left out: the job forbade other behavior changes.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
