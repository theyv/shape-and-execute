---
title: Docs keep only the why
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-12-1846--sae-findings-docs [DECISION-WHY-ONLY], [WHY-ONLY-DOCS]
applies-to: [docs/adr, docs/adr/_intent.md, skills/shape-and-execute, wip-docs]
---

# Docs keep only the why

## Context
The same contract of the skill lived in four places: the task spec (`specs.md`), the design
docs in the design notes, the compiled skill prose (`SKILL.md`, references) and the code (`--help`,
tests). They drifted apart. In the dogfood-fixes task (2026-10-10), a DESIGN-DOCS job copied
the task spec into the design notes (19 files, about +2400/−640 lines); a DOCS-CHECK then found 8
blocking and 9 minor conflicts, most from one contract stated in several places; a whole job,
DOCS-SYNC, existed only to bring the copies back together after the code. What worked: a
contract written before the code let five parallel jobs start from one base.

## Decision
[human] Option B. At the release, the design notes are removed. `docs/adr/` keeps
only the "why": `_intent.md` (the owner's assumptions, what the skill must do, how it differs
from other tools, why it exists, roughly how it works; "WHY" first, then "HOW", little "WHAT")
and one decision record per decision. The exact contract (flags, messages, `state.json` fields,
exit codes) lives in the code, `--help` and the tests. Before the code, a task's `specs.md` is
the contract.

## Why
- The owner's question: "Is it useful to maintain this documentation alongside the code?".
- The owner: "The documentation helped build the tool, but I am unsure whether it needs to be maintained with it." Accepted: "I agree with option B.".
- What the docs-first flow did well: "We first wrote down what we wanted, then gave it to the job as context so it could check its work.". A task's `specs.md` already
  does that: a contract written before the code, approved by the owner, given to every job.
- On `_intent.md`: "Explain why first, then how. The spec already defines what is required.".

## Rejected options
- Design docs kept in step with the code beside it: four copies of one contract drift.
- Each job updates the docs of its area (see [Jobs never update design docs](2026-10-12-jobs-never-update-design-docs.md)).

## Consequences
- The decision log became these records on 2026-10-12. The area docs, the CLI and viewer specs,
  the parking lot and the genesis review were deleted; git keeps them. Open parked items became
  follow-up findings.
- The glossary is replaced by a retired-terms test (see [A retired-terms test instead of a glossary](2026-10-12-a-retired-terms-test-instead-of-a-glossa.md)).
