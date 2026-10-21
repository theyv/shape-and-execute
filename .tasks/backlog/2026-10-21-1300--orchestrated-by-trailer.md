# Intent: Orchestrated-by trailer on the commits sae makes

**Status: rough idea. Not shaped [human].**

## Problem
Commits made through shape-and-execute carry no sign of it. Nobody can tell from `git log`
which commits went through a task, and the project gets no credit in the repositories that
use it. The owner (2026-10-21): "Add something like the Co-Authored-By line to commits, but
for shape-and-execute."

## Proposed outcome
A trailer of its own on the commits sae makes, for example:
`Orchestrated-by: shape-and-execute (https://github.com/theyv/shape-and-execute)`.
Git reads it like any trailer (`git log --format='%(trailers:key=Orchestrated-by)'`,
`git interpret-trailers`), so commits made through sae can be counted.

## Constraints
- Not `Co-Authored-By`. GitHub treats it as a co-author: without an e-mail tied to a GitHub
  account it shows a grey co-author with no profile. sae orchestrates; it does not write the
  code, and the harness already credits the model that does.
- Only on the commits sae makes or composes (job merges, the task branch, finish), never on
  the user's own commits.
- A setting, on by default, easy to switch off; the README says so. Some teams have strict
  rules for commit messages.

## Open questions
- Where sae composes commit messages: `references/commit-message.md` and the merge and finish
  code in `scripts/sae_lib/`.
- The setting's name and where it lives (user config or per-task settings).
- How it sits next to the harness's own trailers (Claude Code's `Co-Authored-By`, Codex).
