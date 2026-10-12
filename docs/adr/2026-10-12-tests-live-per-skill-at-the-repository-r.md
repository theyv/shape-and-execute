---
title: Tests live per skill at the repository root
type: architecture
status: accepted
date: 2026-10-12
source: DL-81, implementation 2026-10-07; task 2026-10-12-1846--sae-findings-docs [TESTS-MOVED]
applies-to: [tests, tests/saetest.py, skills/shape-and-execute/scripts/README.md]
---

# Tests live per skill at the repository root

## Context
`sae` has a `unittest` suite that builds throwaway git repositories. Tests must never reach an
installed skill. Until 2026-10-12 the suite lived in the tests folder of the design notes inside the skill, and
the design notes never reached a released skill.

## Decision
[joint] The tests live in `tests/` at the repository root, one folder per
skill. They run from the repository root:
`python3 -m unittest discover -s tests`. No test file stays inside the skill.

## Why
- An installed skill is its folder; tests outside it never reach an installation.
- At the release the design notes are removed (see [Docs keep only the why](2026-10-12-docs-keep-only-the-why.md)), so the old rule had no
  folder left.

## Rejected options
- A tests folder in the design notes, inside the skill: the owner's choice of 2026-10-07, one rule ("Keep the design notes outside the released skill.") instead of two. Replaced because a released skill keeps no
  design notes.
- A separate `tests/` folder inside the skill: it would need its own rule to stay out of an
  installation.
