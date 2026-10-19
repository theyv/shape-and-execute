---
title: sae points to directory AGENTS.md files
type: architecture
status: proposed          # proposed | accepted | rejected | superseded
date: 2026-10-19
source: 2026-10-19-1603--adr-cleanup-and-dispatch-pointers
applies-to: [skills/shape-and-execute/scripts/sae_lib/prompts.py, build_prompt]
revisit-when: Claude Code and Codex both load a nested AGENTS.md for a subagent whose files lie outside its working directory
---

# sae points to directory AGENTS.md files

## Context
"Why" knowledge for one directory lives in that directory's `AGENTS.md`. `sae` workers run in
worktrees outside the main checkout, with the worktree root as working directory.

## Decision
[human] `sae dispatch` adds one line per `AGENTS.md` or `CLAUDE.md` in a folder above a matched
path, below the repository root. These lines do not count toward the limit of 10 record pointers.

## Why
Neither harness reliably loads these files for a `sae` worker (checked 2026-10-19, Claude Code
2.1.303, Codex 0.163.0). Codex reads only the files from the project root to the working
directory, once, at start. Claude Code loads a nested `AGENTS.md` on a Read, documented only for
subdirectories of the working directory.

## Rejected options
- Leave it to the harness: the file does not reach the worker.
- Only two places (code comment, record): sessions without `sae` lose directory knowledge.
- [human] Directory lines for Codex workers only, on the belief that Claude Code finds nested
  files itself: rejected at the cleanup hold. `sae` worktrees lie outside the subagent's working
  directory, so Claude Code probably misses them too, and a duplicate line costs one line.

## Consequences
The root `AGENTS.md` is never pointed to: both harnesses load it.
