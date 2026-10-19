---
id: NESTED-AGENTS-MD
---

# NESTED-AGENTS-MD: How Claude Code and Codex load nested AGENTS.md and CLAUDE.md

## Objective
Settle whether a directory-level `AGENTS.md` reliably reaches a worker subagent that edits files
in that directory, in Claude Code and in Codex. The decision: does `sae dispatch` need to add
pointers to directory `AGENTS.md` files (like the decision-record pointers), or does the
harness cover them?

## Questions
1. Claude Code: does it read `AGENTS.md` at all (root and nested), or only `CLAUDE.md`? Since
   which version, and is it on by default?
2. Claude Code: when does it load a nested `CLAUDE.md` / `AGENTS.md` in a subdirectory: at
   session start, or on demand when the agent reads or edits a file in that subtree? Does
   the same hold for a subagent spawned with the Agent tool (its own context)?
3. Codex: which `AGENTS.md` files does it load (root to working directory only, or also
   nested files below the working directory when the agent touches them)? Does a subagent
   or a `codex exec` worker behave the same way?
4. Both harnesses: is there a size limit or truncation for the combined instruction files?
5. Given the answers: for a worker whose working directory is the repository root (a git
   worktree) and whose job edits `skills/x/assets/viewer/app.css`, does
   `skills/x/assets/viewer/AGENTS.md` reach it, in each harness? Answer yes, no or unknown,
   with evidence.

## Already known
- Codex (as remembered, not verified): it concatenates `AGENTS.md` files from the repository
  root down to the current working directory at session start.
- This Claude Code session received the root `AGENTS.md` of this repository as project
  instructions (there is no `CLAUDE.md`).
- `docs/adr/research/claude-code-facts.md` and `docs/adr/research/codex-facts.md` hold earlier
  facts about both harnesses; `docs/adr/research/prose-spec.md` lines 130–175 and 300–310
  mention directory-scoped context files, with dated, unverified sources.

## Limits
- Primary sources only: official docs, changelogs, release notes, the Codex source code
  (github.com/openai/codex). Mark each claim with its source and date; say UNKNOWN when the
  sources do not settle it.
- Local checks are allowed (`claude --version`, `codex --version`, `--help`). Do not start
  paid or long sessions.
- No design proposals beyond question 5.

## Follow-up questions
