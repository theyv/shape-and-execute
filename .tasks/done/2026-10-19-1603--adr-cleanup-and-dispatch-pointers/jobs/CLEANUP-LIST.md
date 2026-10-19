---
id: CLEANUP-LIST
covers: [CLEANUP-LIST]
verify:
  - git diff --quiet HEAD -- docs skills tests README.md CREDITS.md AGENTS.md
---

# CLEANUP-LIST: Write the cleanup list for every record and research note

## Objective
A cleanup list in this job's result file that gives every record and research note in
`docs/adr/` one action, for the owner to approve.

## Inputs
- `specs.md`: [CLEANUP-LIST], "Domain language" (the test), [DECISION-NOTES-FOLLOW],
  [DECISION-REVISIT-OPTIONAL], [DECISION-DL-SOURCES].
- `intent.md`: "Proposed outcome", the three places by reach and their examples.
- `brief.md`: "Invariants", "Constraints" (what ships with installs).
- `docs/adr/` (103 records, `_intent.md`, `index.md`, 8 notes in `docs/adr/research/`), and the
  code each record guards, to judge whether the code already shows it.
- Links into `docs/adr/` from outside it: `README.md`, `CREDITS.md`, `AGENTS.md`.

## Scope
- Read every record and check it against the code. Give each one action:
  - keep: it passes the test;
  - code comment: name the target file (one file's concern);
  - directory `AGENTS.md`: name the target folder (one directory's concern);
  - remove: the code shows it, or nobody would undo it.
- One reason per record, by the test. A `revisit-when` only where the condition is obvious.
- For a kept record: flag path entries that name no existing path, with the corrected path.
- Per research note: keep or remove, by whether a kept record links it.
- Name every link from outside `docs/adr/` that a removal would break, with what it should
  point to instead (or "drop the link").
- Flag private data you see in a kept record or a moved text (names, pilot-project context,
  unsmoothed or non-English quotes).
- Put the list in the result file under `## Cleanup list`: one table for records (file, action,
  target, reason, revisit-when), one for notes (file, action, kept records that link it), then
  the flags. Open with the counts per action. The owner reads it at the hold.

## Boundaries
- Change no repository file. Write only the result file.
- `_intent.md` stays; it is not a record. `index.md` is not listed.
- Do not draft the moved texts; `CLEANUP-APPLY` writes them.
- Merging two records into one is not an action; list both and note the overlap in the reason.

## Expected output
`jobs/CLEANUP-LIST.result.md` (status done, `changes: none`) with the `## Cleanup list` section.

## Validation
- [ ] All 103 records and 8 research notes appear once each; the counts add up.
- [ ] Every "code comment" row names a file and every "directory AGENTS.md" row names a folder.
- [ ] Every kept record's reason states what an agent would "fix" or bring back without it.
- [ ] A note marked keep is linked by at least one kept record.
