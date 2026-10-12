---
title: The plan gate names jobs without verify
type: architecture
status: accepted
date: 2026-10-07
source: DL-78, genesis review 2026-10-07 (G6)
applies-to: [skills/shape-and-execute/references/modes/plan.md, skills/shape-and-execute/scripts/sae_lib/graph.py, lint_plan, verify]
---

# The plan gate names jobs without verify

## Context
A job without `verify` commands has no deterministic check; `sae check` warns about it. The
warning could become a rule.

## Decision
[joint] The plan-gate summary lists the jobs that `sae check` warns have no `verify`. No new
rule.

## Why
Only judgement checks such jobs, so the owner sees them and can flag them for review.

## Rejected options
- A rule that every job must have `verify`.
