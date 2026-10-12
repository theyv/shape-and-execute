---
title: sae is an entry point plus the package sae_lib
type: architecture
status: accepted
date: 2026-10-10
source: DL-136, task 2026-10-08-1733--sae-dogfood-fixes (AMEND-1, [SAE-MODULES]); DL-86, implementation 2026-10-07
applies-to: [skills/shape-and-execute/scripts/sae.py, skills/shape-and-execute/scripts/sae_lib, skills/shape-and-execute/scripts/README.md]
---

# sae is an entry point plus the package sae_lib

## Context
`sae.py` had grown to 3,400 lines, and almost every requirement of the dogfood fixes touched
it.

## Decision
[human] (the agent's proposal) `python3 <SKILL_DIR>/scripts/sae.py …` stays the entry point.
The code lives in the package `scripts/sae_lib/`, one module per area (module docstrings,
`scripts/README.md`). No module above about 1,000 lines. Standard library only, Python 3.9 or
newer. The split changed no behavior and came first.

## Why
- Parallel jobs would collide in one file, and it would grow to about 5,000 lines.
- Python 3.9: the system `python3` of the owner's macOS is 3.9 (agent's reading).

## Rejected options
- One file.
- A Python 3.10 minimum.
