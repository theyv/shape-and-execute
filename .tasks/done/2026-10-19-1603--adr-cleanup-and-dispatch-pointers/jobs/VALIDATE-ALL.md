---
id: VALIDATE-ALL
covers: [TESTS, CLEANUP-APPLY, WORKER-POINTERS, REVIEW-POINTERS]
verify:
  - python3 tests/run.py
  - "! grep -rn 'DL-' docs/adr"
---

# VALIDATE-ALL: Validate the merged task branch

## Objective
A validation report on the merged task branch: the full suite passes, the cleanup meets its
acceptance checks, and the pointers work against the real `docs/adr/`.

## Inputs
- `specs.md`: every requirement's acceptance items, especially [TESTS] and [CLEANUP-APPLY].
- `brief.md`: "Invariants".
- `jobs/CLEANUP-LIST.result.md` (the approved list), `jobs/CLEANUP-APPLY.result.md`.

## Scope
- Run the full suite (verify).
- Check the cleanup against the approved list: counts, actions, links from `README.md`,
  `CREDITS.md`, `AGENTS.md` and records into `docs/adr/` resolve.
- Check that each kept record has at least one path entry and that its path entries name
  existing paths; report the ones that do not.
- Build a worker prompt for a realistic `scope` in this repository (for example the viewer
  assets) with the branch's `sae` code, without changing the repository, and report which
  pointer lines it gets.
- Scan the changed files for private data (names, pilot-project context, unsmoothed quotes).

## Boundaries
- Read-only. Report failures; do not fix them.
- Judging whether each kept record passes the test belongs to the integration review.

## Expected output
`jobs/VALIDATE-ALL.result.md` with the evidence per check.

## Validation
- [ ] Every acceptance item of the spec is either checked here or named as covered by a test.
