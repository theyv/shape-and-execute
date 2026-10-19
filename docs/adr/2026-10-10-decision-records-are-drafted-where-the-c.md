---
title: Decision records are drafted where the context is fresh and accepted in triage
type: architecture
status: accepted
date: 2026-10-10
source: task 2026-10-08-1733--sae-dogfood-fixes
applies-to: [skills/shape-and-execute/scripts/sae_lib/findings.py, skills/shape-and-execute/references/modes/plan.md, skills/shape-and-execute/references/modes/execute.md, skills/shape-and-execute/references/modes/triage.md, skills/shape-and-execute/references/modes/triage-decisions.md, skills/shape-and-execute/references/modes/triage-findings.md, cmd_adr_new, cmd_adr_accept, cmd_adr_reject, cmd_triage, triage_counts]
---

# Decision records are drafted where the context is fresh and accepted in triage

## Context
Durable decisions were lost with the conversation. The owner: agentic coding gives too little
weight to "why" and too much to "how".

## Decision
- [joint] The shaping session drafts decision records at plan approval, from the conversation
  and the task files, quoting the owner's words where they carry the "why". The execution
  session drafts them at finish, from logged decisions and amendments. Drafts go to
  `.tasks/adr/` with status `proposed`, are committed with the task record and never block a
  run. Only durable decisions become drafts: ones a later agent could not rebuild from the code.
- [human] Triage has two queues, findings and decision drafts. It starts with a table of counts
  (findings by type, decision drafts, the oldest of each) and asks which queue to work on; each
  queue has its own reference, loaded only when chosen. At the first accepted record in a
  repository, triage proposes one line for the repository's agent instructions that points to
  the ADR folder; the owner approves it.

## Why
- An inbox: a decision is not a problem to triage, but it needs a human gate so the repository
  does not fill with rubble. The owner rarely reads drafts during a run.
- The drafting session still holds the owner's words.

## Rejected options
- `.tasks/decisions/` as the drafts folder (R3). `.tasks/adr/` and `sae adr …` were agent
  assumptions the owner did not veto (R5).
