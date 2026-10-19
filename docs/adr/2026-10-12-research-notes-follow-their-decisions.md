---
title: Research notes follow their decisions
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-12-1846--sae-findings-docs
applies-to: [docs/adr/research]
---

# Research notes follow their decisions

## Context
The research folder of the design notes held the notes of the design sessions. Without the design notes, they need a
home or none.

## Decision
[agent] A research note moves to `docs/adr/research/` only when a kept
decision record cites it. Mockups and other notes are deleted (git keeps them), unless code or
tests use them.

## Why
The folder keeps only the "why" (see [Docs keep only the why](2026-10-12-docs-keep-only-the-why.md)). A note is part of the why only
as the evidence of a decision.

## Consequences
- The research notes of later tasks stay in their task records, for example
  `research/FORENSICS.md` of task 2026-10-08-1733--sae-dogfood-fixes.
