---
title: The brief instead of a context file
type: architecture
status: accepted
date: 2026-10-06
source: DL-12, design interview 2026-10-06 (Q5)
applies-to: [skills/shape-and-execute/templates/brief.md, brief.md]
---

# The brief instead of a context file

## Context
Every worker needs the same short summary of the task: why, what, conventions, invariants.

## Decision
[joint] The file is `brief.md`.

## Why
The owner found the term context ambiguous. The name brief describes the file's purpose.

## Rejected options
- `context.md`.
