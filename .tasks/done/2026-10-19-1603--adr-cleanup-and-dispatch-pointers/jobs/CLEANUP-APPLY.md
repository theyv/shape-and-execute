---
id: CLEANUP-APPLY
covers: [CLEANUP-APPLY]
verify:
  - "! grep -rn 'DL-' docs/adr"
  - python3 tests/run.py test_adr_index test_adr_rules test_retired_terms
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
---

# CLEANUP-APPLY: Apply the approved cleanup list

## Objective
The repository follows the owner-approved cleanup list: every record and research note has its
action, `index.md` is current, and no `DL-…` source remains.

## Inputs
- The approved list: `jobs/CLEANUP-LIST.result.md`, section `## Cleanup list`, with the owner's
  changes already in it. It is the contract; do not reclassify.
- `specs.md`: [CLEANUP-APPLY], [DECISION-DL-SOURCES], [DECISION-NOTES-FOLLOW],
  [DECISION-REVISIT-OPTIONAL].
- `brief.md`: "Invariants" (private data, `_intent.md`), "Constraints" (what ships with installs).
- `skills/shape-and-execute/SKILL.md`, "Smooth every quote".

## Scope
- Remove the records and notes the list removes.
- Move knowledge to the code comment or directory `AGENTS.md` the list names: short, in the
  target's own voice, only the "why" the code does not show.
- In kept records: drop `DL-…` and the private interview references from `source` (keep a task
  ID; drop the field when nothing remains); add `revisit-when:` where the list gives one; fix
  path entries where the list says.
- `docs/adr/index.md`: one line per remaining record and note, no dangling line.
- Fix every link into `docs/adr/` that the list names (`README.md`, `CREDITS.md`, `AGENTS.md`,
  other records). Point the repository's `AGENTS.md` files to what moved only where needed.

## Boundaries
- Only the actions in the list. A row you believe wrong: apply it and say so under `## Risks`
  in your result; a row you cannot apply: park with a decision request.
- `_intent.md` stays. No new record.
- No `sae` code or test logic change; a moved comment in a code file is fine.

## Expected output
Commits on the job branch; the result lists any row applied with doubt.

## Validation
- [ ] Every row of the list is applied; the counts in the list match the remaining files.
- [ ] Every file in `docs/adr/` except `index.md` has exactly one index line.
- [ ] No names, no pilot-project context; quotes in English and smoothed.
- [ ] Every moved text is a few lines at most.
