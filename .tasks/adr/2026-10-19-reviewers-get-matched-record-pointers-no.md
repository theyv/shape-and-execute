---
title: Reviewers get matched record pointers, not the index
type: architecture
status: proposed          # proposed | accepted | rejected | superseded
date: 2026-10-19
source: 2026-10-19-1603--adr-cleanup-and-dispatch-pointers
applies-to: [skills/shape-and-execute/scripts/sae_lib/prompts.py, build_prompt, skills/shape-and-execute/references/roles/reviewer.md]
revisit-when: a review misses a broken decision record that the index would have shown, or evals compare reviews with and without the index
---

# Reviewers get matched record pointers, not the index

## Context
`sae dispatch` gives each agent pointers to the decision records that guard its work. The
planner and the decision worker get a pointer to the whole `index.md`, because their choices
can bring back a rejected option anywhere. A reviewer could get the index too.

## Decision
[human] A job reviewer gets only the pointers to records whose `applies-to` paths the diff
changed; the integration reviewer the same for the whole diff. Reviewers do not get `index.md`.

## Why
The owner is not sure. The index might help a reviewer catch a decision that the matching
misses, "but on the other hand this could provide too much noise for an agent that should be as
focused as it can".

## Rejected options
- The index for every reviewer: broader coverage, more noise in a context that must stay
  focused on the diff.

## Consequences
A record with wrong or missing `applies-to` paths never reaches a reviewer. Good `applies-to`
paths matter more than before.
