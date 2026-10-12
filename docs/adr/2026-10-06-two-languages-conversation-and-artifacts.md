---
title: Two languages, conversation and artifacts
type: architecture
status: accepted
date: 2026-10-06
source: DL-59, design interview 2026-10-06 (Q24)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/scripts/sae_lib/prompts.py, skills/shape-and-execute/templates/repo/profile.md, artifact_language]
---

# Two languages, conversation and artifacts

## Context
The owner talks to agents in Polish and keeps task files, code and documentation in English.
A team may need one documentation language.

## Decision
[joint] The user config has two languages: conversation (questions, explanations, notices) and
artifacts (task files, code comments, commit messages, documentation). A repository may pin
the artifact language in `.tasks/repo/profile.md`. For code comments the repository's existing
convention wins. When a translation would lose a nuance of the owner's words, agents quote the
original.

## Why
- Each person talks in their own language, while the repository keeps one language for its
  files.
- A team can require one documentation language through the pin.
- Quoting keeps the owner's exact meaning, which decision records depend on.
