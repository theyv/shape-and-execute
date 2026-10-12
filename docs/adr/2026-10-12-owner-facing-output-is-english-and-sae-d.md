---
title: Owner-facing output is English and sae does not wrap prose
type: architecture
status: accepted
date: 2026-10-12
source: DL-108, task 2026-10-08-1733--sae-dogfood-fixes (R3, [NARROW-OUTPUT]); task 2026-10-12-1846--sae-findings-docs [DECISION-NO-WRAP], [OUT-NO-PROSE-WRAP], [OUT-RELAY-RULE]
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/scripts/sae_lib/common.py, skills/shape-and-execute/scripts/sae_lib/control.py, skills/shape-and-execute/scripts/sae_lib/config.py, emit, process_map, settings_card]
---

# Owner-facing output is English and sae does not wrap prose

## Context
The first launch card was wide, sat in a code block and wrapped so badly that it was "too difficult to read". A 72-column rule for all output
followed. Three fix rounds of `sae`'s prose wrapping in the dogfood fixes (FINAL-FIX, -2, -3)
were still wrong: lines starting with "sae" printed unwrapped, wrapping cut a word, and it split
a git command.

## Decision
- [human] Everything `sae` prints for the owner is English.
- [joint] `sae` does not wrap prose. Notices, errors, usage and reports print whole; the
  terminal wraps them by words. Commands, paths and words are never split. Only the
  fixed-layout blocks (the process map, the settings card, the next-step card) keep a narrow
  layout, by their template.
- [joint] The orchestrator relays the process map and fixed-layout blocks in a code block, as
  `sae` prints them, and relays notices and reports as prose, never in a code block. It never
  relays a wide table.

## Why
- The owner's concern was only the ugly wrapping of one wide card in a code block.
- On the wrapping rounds: "This has become unnecessarily complicated.".
- "Keep the design simple.".

## Rejected options
- `sae` wrapping prose to 72 columns (DL-108, until 2026-10-12): three fix rounds were still
  wrong, and it split words and commands.
