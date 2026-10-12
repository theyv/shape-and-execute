---
title: A finding always has a body
type: architecture
status: accepted
date: 2026-10-10
source: DL-128, task 2026-10-08-1733--sae-dogfood-fixes (D22, item 25, [FINDING-BODY-REQUIRED])
applies-to: [skills/shape-and-execute/scripts/sae_lib/findings.py, skills/shape-and-execute/templates/finding.md, cmd_finding_new, finding_body]
---

# A finding always has a body

## Context
A finding is read later, in triage, without the context of the agent that filed it.

## Decision
[agent] `sae finding new` refuses a finding without its observation (the body) and a title
that is too long.

## Why
Two pilot-project findings held only a title, one of them in an over-long title. Nobody could
triage them.
