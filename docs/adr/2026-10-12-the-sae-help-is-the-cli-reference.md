---
title: The sae help is the CLI reference
type: architecture
status: accepted
date: 2026-10-12
source: DL-76, genesis review 2026-10-07 (G4); task 2026-10-12-1846--sae-findings-docs [DECISION-WHY-ONLY]
applies-to: [skills/shape-and-execute/scripts/sae_lib/cli.py, skills/shape-and-execute/SKILL.md, build_parser, fill_missing_help]
---

# The sae help is the CLI reference

## Context
The CLI was described three times: a CLI spec in the design docs, a `references/sae-cli.md` for
agents, and the code.

## Decision
- [human] `sae --help` and `sae <command> --help` are the agent reference for the CLI. Every
  command and option has help text. `SKILL.md` holds the exit-code table.
- [human] No CLI spec is kept beside the code: flags, messages, fields and exit codes live in
  the code, `--help` and the tests (see [Docs keep only the why](2026-10-12-docs-keep-only-the-why.md)).

## Why
- Three descriptions of one CLI drift.
- Help per command loads only what is needed, so a split reference is unnecessary.

## Rejected options
- `references/sae-cli.md` as the agent reference, whole or split per command.
- A CLI spec in the design docs as the design intent beside the code (DL-76 kept it until
  2026-10-12): it drifted from the code and from the task specs it copied.
