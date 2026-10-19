# Intent: Review foundation jobs before dependent work starts

## Problem

A job can produce documentation or another shared contract that many later jobs depend on.
If that foundation is wrong, its mistakes spread through the dependent work before the
integration review catches them. The planner does not explicitly identify this risk.

In an earlier task, sae-dogfood-fixes, DESIGN-DOCS prepared documentation for five
jobs. The owner added DOCS-CHECK during execution and made those jobs wait for it. The check
found contract conflicts that needed fixes before the dependent work could start.

## Goal

Make the planner identify foundation jobs and plan an appropriate review or independent
validation immediately after them, before dependent jobs use their output.

Keep a coherent task together when that makes sense. The agent's observation was that
splitting it into several tasks would add specs and gates; the missing piece was a check
after the job on which the rest depended.

### Success means

- The planner recognizes a job whose incorrect output could mislead many later jobs.
- The plan explains the risk and places a check before dependent work starts.
- The mechanism respects the task's review settings; any required setting change stays
  with the user.

## Existing evidence

- The DOCS-CHECK job of sae-dogfood-fixes and that task's events: DOCS-CHECK was added on
  the owner's request on 2026-10-10, then five jobs were made to wait for it. The task record
  predates this repository and is not part of it.
- [Planner protocol](../../skills/shape-and-execute/references/roles/planner.md) has
  general risk criteria for review flags, but no explicit rule for foundation jobs.

Design and implementation are deferred until this item is picked up [human, 2026-10-18].
