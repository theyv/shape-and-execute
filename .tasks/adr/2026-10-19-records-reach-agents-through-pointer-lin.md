---
title: Records reach agents through pointer lines, not domain AGENTS.md files
type: architecture
status: proposed          # proposed | accepted | rejected | superseded
date: 2026-10-19
source: 2026-10-19-1603--adr-cleanup-and-dispatch-pointers
applies-to: [skills/shape-and-execute/scripts/sae_lib/prompts.py, docs/adr, build_prompt]
revisit-when: most jobs get the same record pointers, or a file matches more than 10 records
---

# Records reach agents through pointer lines, not domain AGENTS.md files

## Context
`sae dispatch` adds one pointer line per record whose `applies-to` paths match the job (at most
10, then "+N more"). At the cleanup hold the owner doubted it: some files or folders could
collect many records, and those records would then reach "almost every change in this repo",
which fills the context. The owner proposed to drop the record pointers and to put the rules
into domain `AGENTS.md` files.

## Decision
[human] Keep the record pointers as built: up to 10 lines per prompt, matched on `scope`, the
job file or the diff.

## Why
After the cleanup, 25 records remain, and the stricter test keeps new records rare: only
cross-cutting knowledge, or a rejected option that someone will propose again. With narrowed path
entries, the most-matched file (`SKILL.md`) gets 8 lines; most files get 0 to 2. A pointer is
one index line, not the record's text. A cross-cutting record has no domain folder of its own:
its `AGENTS.md` would sit high in the tree and reach every job below it, which is the noise the
owner wanted to avoid.

## Rejected options
- Drop the record pointers; move the rules into domain `AGENTS.md` files: cross-cutting rules
  would land in a high folder and reach more jobs, not fewer.
- A lower limit (for example 5): not needed at the current match counts.

## Consequences
Records must keep narrow path entries. A broad entry (a whole skill folder) brings the record
to almost every job; narrow it, or remove the record.
