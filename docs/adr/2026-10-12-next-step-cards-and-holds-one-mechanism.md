---
title: Next-step cards and holds, one mechanism of owner control
type: architecture
status: accepted
date: 2026-10-12
source: DL-102, task 2026-10-08-1733--sae-dogfood-fixes (R1, R2, Q3; items 3, 4, 12, 23; [LAUNCH-CARD], [HOLD-AFTER-JOB], [DECISION-LAUNCH-CARD], DOCS-FIX); task 2026-10-12-1846--sae-findings-docs [OUT-NEXT-STEP-CARD]
applies-to: [skills/shape-and-execute/scripts/sae_lib/control.py, skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/modes, record_card, cmd_hold, cmd_next, NEXT STEP]
---

# Next-step cards and holds, one mechanism of owner control

## Context
The owner wanted to see and change which models run before work starts, and to intervene at
any moment. Items 3, 4, 12 and 23 of the dogfood fixes asked for overlapping controls.

## Decision
- [joint] Before every bigger dispatch, `sae next` prints a next-step card, headed `NEXT STEP`
  (for example `NEXT STEP · spec review · 1 job`): per job its ID, model · effort and a
  one-line purpose, then the settings changed since the last card. In shaping, planning and at
  start, the orchestrator waits for ok, change, refine first or skip; during execution it only
  shows the card. A hold stops dispatching after a chosen job, in every mode.
- [agent] `sae` prints the card. `sae next` stays read-only: `sae dispatch` of a job on the
  card, or `sae start`, records it, and the next card lists the changes since the last
  recorded one.
- [human] The purpose line is never cut; a long one may wrap.
- [human] The name is "next-step card"; "launch card" is a retired term.

## Why
- The owner: "The user should retain control while actively supervising the work."; "I should be able to intervene at any time and change the models and reasoning effort.".
- One mechanism, because the four items asked for overlapping controls. Printed by `sae`,
  because the orchestrator runs `sae next` before every dispatch anyway, so the card costs no
  call.
- On cutting the purpose: "Wrap the text rather than truncate it.".
- On the old name: "The label is unclear.".

## Rejected options
- An "ask before" setting.
- Questions inside execution.
- `sae next` recording the card: a read-only command would write.
- The name "launch card" and the header `LAUNCH` (until 2026-10-12).
- A purpose line cut to fit the width.
