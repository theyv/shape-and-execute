# Intent: Adopt the roles, workflows and knowledge skill layout

## Problem

The skill mixes two layouts. `references/modes/` holds the processes and `references/roles/`
holds the subagent protocols, while shared knowledge files (`grill.md`,
`interaction-modes.md`, `commit-message.md`) sit loose in `references/`.

The owner now uses one layout for every multi-agent skill. `SKILL.md` is the head of a
department and routes the work. `references/roles/` holds the agents (the department's
people). `references/workflows/` holds the processes any of them can run. `references/knowledge/`
holds the knowledge they share. The word "mode" reads as a working mode of one role, but these
files are processes, and one role may run several of them at once.

## Goal

The skill follows the same layout as the owner's other agent systems, so a reader knows where
to look before opening a file.

### Success means

- `references/` holds only `roles/`, `workflows/` and `knowledge/`.
- Every link in `SKILL.md`, the references, the scripts and the tests resolves.
- `sae` behaves exactly as before.

## Proposed outcome

- [human, 2026-11-04] Rename `references/modes/` to `references/workflows/`.
- [human, 2026-11-04] Move the shared knowledge files that sit loose in `references/` into
  `references/knowledge/`.
- [human, 2026-11-04] Name the step files of a multi-step workflow so they say what the step
  does and can be found by search: `NN-<abbr>-<what-the-step-does>.md`, where `<abbr>` is the
  workflow's initials (unique in the skill), for example `meta-analysis/01-ma-sync-sources.md`;
  never a bare name such as `start.md`. A file in a knowledge folder starts with that folder's
  abbreviation too. Names say what the file does in at least two words, usually three, never
  one; the number and the abbreviation do not count. [human, 2026-11-04, revised the same day]
- Update the paths in `SKILL.md`, the scripts that build reference paths (`prompts.py`,
  `planning.py`, `routing.py`, `common.py`) and the tests.

## Constraints

- A pure move: no change of behavior or wording beyond the paths.
- The skill stays public and depends on no other skill. It adopts the layout; it does not link
  the owner's private guidelines.
- [human, 2026-11-04] Tier 2. Record this work for later implementation.

## Open questions

- Does user-facing text keep the word "mode" ("setup mode", "triage mode", "Pick the mode") or
  switch to "workflow"? One term for one meaning argues for switching; the description and the
  docs would change with it.
