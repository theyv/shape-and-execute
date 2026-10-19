# Brief: ADR cleanup and dispatch pointers

## Why
`docs/adr/` holds 103 records, about 24,000 words, mostly copied one to one from a private
design log. Many only restate the code, and nothing brings a record to the agent that is about
to change the code it guards. The owner: "This has to serve a purpose; right now it is a
collection of spam." See `intent.md`.

## What
- Records that pass the test, and nothing else; moved knowledge sits in a code comment or a
  directory `AGENTS.md`; no `DL-…` source; a current `index.md`.
- `sae dispatch` adds pointer lines (record links, plus directory `AGENTS.md` / `CLAUDE.md`
  files) to worker and review prompts, and an `index.md` pointer to planner and decision
  worker prompts.
- Writing rules that name three places for "why" knowledge, and an optional `revisit-when:`.

## How (high level)
- The cleanup runs in two steps: a list job, a hold for the owner's approval, then one job
  applies the approved list ([DECISION-LIST-IN-EXECUTION]).
- Pointer lines are built in `build_prompt` (`scripts/sae_lib/prompts.py`), reusing the index
  helpers and ADR folder rules of `scripts/sae_lib/findings.py` and `in_scope` of
  `scripts/sae_lib/reviews.py`.

## Invariants
- A prompt with no matching record and no ADR folder is byte-for-byte as today
  ([EDGE-NO-ADR-FOLDER]).
- Only path entries (items with `/`) match ([DECISION-PATH-ENTRIES]).
- Pointers, not pastes: one line per record or directory file, never its content.
- `_intent.md` stays. The root `AGENTS.md` is never a pointer line.
- No private data in any file: no names, no pilot-project context, quotes in English and smoothed
  (`skills/shape-and-execute/SKILL.md`, "Smooth every quote").

## Domain terms
Record, pointer line, path entry, the test: see `specs.md` "Domain language". Say "record",
not "ADR", in task files.

## Constraints
- `sae` stays Python 3.9+, standard library only. No new command, setting or state.
- Few added lines, in code and in prose. No new ceremony.
- Edit the skill in this repository (`skills/shape-and-execute/`), never an installed copy.
- Installs copy only `skills/shape-and-execute/`: whatever lands there ships to every user.
- Nothing is pushed.

## Architecture facts
- ADR folders: `adr_folder` / `adr_rules` in `.tasks/repo/profile.md`; this repository uses
  `docs/adr`. `adr_index_line` builds an index line from a record.
- `tests/test_adr_index.py` already checks that every file in this repository's ADR folder has
  one index line and every line points to a file.
- `tests/saetest.py` has the sandbox and `dispatch_workspace` helpers for dispatch tests.

## Validation
Commands: `.tasks/repo/profile.md`. Writer jobs run their own tests and the smoke command; only
`VALIDATE-ALL` runs the full suite.
