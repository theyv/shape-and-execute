---
title: Research leaves files and agents are resumed first
type: architecture
status: accepted
date: 2026-10-10
source: DL-38, design interview 2026-10-06 (D14, D16); DL-132, task 2026-10-08-1733--sae-dogfood-fixes (item 31, AMEND-2, [RESEARCH-FOLLOW-UP])
applies-to: [skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/references/modes/plan.md, skills/shape-and-execute/references/roles/research-worker.md, skills/shape-and-execute/templates/research-report.md, cmd_dispatch, --resume]
---

# Research leaves files and agents are resumed first

## Context
Research and planning run as subagents. Follow-up questions often come after the job is done,
and sessions restart.

## Decision
- [human] A research job leaves its report as a file (`research/<ID>.md`). A follow-up question
  goes first to the agent that already holds the context: resume it.
- [agent] `sae dispatch <task> <ID> --resume --reason "<why>"` reopens a `done` research or
  planning job: a new attempt, and `sae collect` reads the updated report or result. When a
  resume is not possible, a fresh agent gets the same pointers plus the earlier report.

## Why
- Research runs as a job like any other: model and effort from routing, a generated prompt, a
  recorded attempt, a report file. The owner can later see which model researched what.
- `shape.md`'s follow-up questions and `plan.md`'s planner resume were refused while `sae`
  could not reopen a done job.
