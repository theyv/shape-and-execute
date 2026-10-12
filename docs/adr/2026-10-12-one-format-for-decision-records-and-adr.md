---
title: One format for decision records and ADR rules pick the folder
type: architecture
status: accepted
date: 2026-10-12
source: DL-130, task 2026-10-08-1733--sae-dogfood-fixes (R2, [DECISION-RECORD-FORMAT]); task 2026-10-12-1846--sae-findings-docs [ADR-RULES], [EDGE-ADR-TWO-RULES], [SETUP-ADR-QUESTION]
applies-to: [skills/shape-and-execute/templates/decision-record.md, skills/shape-and-execute/templates/repo/profile.md, skills/shape-and-execute/scripts/sae_lib/findings.py, skills/shape-and-execute/references/modes/setup.md, adr_target_folder, cmd_adr_accept, ADR_FOLDERS, ADR_DEFAULT_FOLDER, adr_folder, applies-to]
---

# One format for decision records and ADR rules pick the folder

## Context
Accepted decision records must be found later, by people and by agents that read the code.
One repository can hold several areas, such as several skills, each with its own records.

## Decision
- [joint] One format (`templates/decision-record.md`): title, `type` (`architecture` |
  `business`), `status` (`proposed`, `accepted`, `rejected`, `superseded`), date, source,
  context, decision, why, rejected options, consequences, and `applies-to`: the paths and code
  names the record governs. File names are the date and a slug.
- [joint] The repo profile may hold ADR rules: a path prefix → an ADR folder. `sae adr accept`
  puts a record into the folder of the rule whose prefix matches the draft's `applies-to`
  paths, the longest prefix first. A draft whose paths match rules of different folders is
  refused, with the folders named; the user narrows `applies-to` or splits the draft. Without
  rules, or when no rule matches: the `adr_folder` pin of the profile, else the repository's
  existing ADR folder, else `docs/decisions/`. Setup asks once per repository: one flat folder,
  or rules per path.

## Why
- A search in the code must find the "why" of the code it reads; `applies-to` makes that work.
- One area's records belong together, apart from other areas; this repository keeps one folder
  per skill.

## Rejected options
- Copying a draft that spans two rule folders into both ([agent] assumption at the spec gate):
  one decision would live twice.
