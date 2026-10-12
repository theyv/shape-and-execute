---
title: Review findings are claims
type: architecture
status: accepted
date: 2026-10-10
source: DL-92, task 2026-10-08-1733--sae-dogfood-fixes (R3, item 30, [FINDINGS-ARE-CLAIMS])
applies-to: [skills/shape-and-execute/references/roles/worker.md, skills/shape-and-execute/references/roles/planner.md, skills/shape-and-execute/references/modes/execute.md, skills/shape-and-execute/templates/job-result.md, skills/shape-and-execute/scripts/sae_lib/reviews.py, disputed_findings, Disputed findings]
---

# Review findings are claims

## Context
An adversarial reviewer tries to prove the work wrong. Some of its findings are wrong too.

## Decision
[joint] The agent that acts on a review (a fix worker, the planner after a plan review) checks
each finding against the code or the plan first. A finding it believes wrong is not
implemented; it is reported as disputed, with the reason. The orchestrator settles disputed
findings by decision class and interaction mode; settled disputes appear in the final report
like other decisions.

## Why
The owner's impression that agents implement everything an adversarial review says.
