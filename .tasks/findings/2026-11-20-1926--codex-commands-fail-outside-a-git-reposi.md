---
type: defect
confidence: medium
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/WRITER-LAUNCH
paths: []
---

# codex COMMANDs fail outside a git repository

## Observation
The codex review and writer COMMANDs run 'codex exec -C <dir>' without --skip-git-repo-check. In a task without git the workdir is not a git repository, and codex exec refuses to start there (not verified with a real codex; tests use fakes). Expected: a codex COMMAND starts in a no-git task folder too.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
