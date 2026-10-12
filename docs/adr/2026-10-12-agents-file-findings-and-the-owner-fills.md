---
title: Agents file findings and the owner fills the backlog
type: architecture
status: accepted
date: 2026-10-12
source: DL-39, DL-64, design interviews 2026-10-06 (Q22, S2-Q2, S2-Q9, S2-D3, S2-D5, S2-D6); task 2026-10-12-1846--sae-findings-docs [RESOLVES-CLOSE], [CLOSED-VISIBLE]
applies-to: [skills/shape-and-execute/scripts/sae_lib/findings.py, skills/shape-and-execute/templates/finding.md, skills/shape-and-execute/templates/job.md, skills/shape-and-execute/templates/job-result.md, skills/shape-and-execute/references/roles/worker.md, skills/shape-and-execute/references/modes/triage-findings.md, cmd_finding_new, cmd_finding_close, cmd_triage, resolves, resolved]
---

# Agents file findings and the owner fills the backlog

## Context
Agents meet problems and useful work outside their job. The owner defers work while shaping,
during execution, at the final report and in triage. Before this decision a worker wrote
follow-ups into the body of its result, which the orchestrator reads only when a job fails or
parks, so they were lost.

## Decision
- [agent], extended [human]: problems an agent finds outside its job become findings
  (`sae finding new`), never side fixes. Types: `defect`, `friction`, `follow-up`. The owner
  added the friction type and the triage loop.
- [joint] Work the owner defers becomes a backlog item. Work an agent finds on its own becomes a
  `follow-up` finding. Triage's outcome "later" moves a finding to the backlog. The bare word
  "follow-up" has one meaning: the job-result section is "Risks", the research section is
  "Follow-up questions".
- [human] A finding closes as a side effect of the job that fixes it. A job file names the
  findings it should fix in `resolves`; the worker lists in its result's `resolved` the ones it
  fixed or confirmed fixed. When the job succeeds, `sae` closes each finding in both lists. The
  closure counts at once in every checkout of the repository.

## Why
- The same split as everywhere: agents report, the owner decides. The backlog holds only what
  the owner chose.
- Follow-ups in result bodies were lost.
- After the dogfood-fixes task, 34 findings were open and 18 of them were already fixed. The
  owner: "There are many findings, and I cannot tell whether they are all still current.".

## Rejected options
- Deferred work is always a task: agents would fill the backlog.
- Deferred work is always a finding: the owner's own deferrals would wait for triage.
- Nothing new: cut scope stays in "Out of scope" and is forgotten.
- The type names `todo` and `missing`.
- Closing fixed findings in a separate triage step: the open list goes stale between triages,
  and it costs the owner a step.
