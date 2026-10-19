---
status: done
summary: Applied the approved list. 25 records and 5 notes remain; 14 records moved to code comments and 2 to sae_lib/AGENTS.md; 62 records and 3 notes removed; index current, no DL- source.
validation: pass
changes: made
resolved: []
---

# Result: CLEANUP-APPLY

## Validation evidence
- `! grep -rn 'DL-' docs/adr`: no match.
- `python3 tests/run.py test_adr_index test_adr_rules test_retired_terms`: 14 tests OK.
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Full suite `python3 tests/run.py`: 318 tests OK (5 skipped). Code files changed only in comments.
- Counts: `docs/adr/` holds 25 records, `_intent.md`, `index.md` and 5 notes. The index has 31
  lines, one per file. 78 records were removed (62 + 14 + 2), as the list gives.
- A script checked every relative Markdown link in `docs/adr/`, `README.md`, `CREDITS.md`,
  `AGENTS.md`, `.tasks/backlog/` and the new `sae_lib/AGENTS.md`. None is broken.
- The links the list names are fixed: in the kept records, `research/wayfinder.md`, both backlog
  items, and the record mentions in the comments of `common.py`, `gitutil.py`, `lifecycle.py`,
  `workspaces.py`, `graph.py` and `reviews.py`.
- Owner changes: `prose-spec.md` paraphrases the handbook and has no local APM path.
  `codex-facts.md` talks of "a local catalog" and "a local config". The broad path entries are
  narrowed.

## Decisions taken
- [agent] `source` keeps only task IDs. Spec IDs and item numbers are dropped, because they
  point into task records this repository does not hold. 15 records had no task ID, so they lost
  the field.
- [agent] Narrowed paths. one-skill-with-five-modes: `SKILL.md` and `references/modes/setup.md`
  (the router, and the split the owner rejected). follow-prose: `references/roles` becomes
  `references/roles/planner.md`. docs-keep-only-the-why: `docs/adr`.
- [agent] The `revisit-when` values are the list's own words. The fast-lane condition reads
  "the fast-lane backlog item (2026-10-14-2150) is shaped".
- [agent] I fixed the stray `".` after closing quotes in the kept records. `_intent.md` has one
  too, and I left it as it is.
- [agent] The root `AGENTS.md` gets no new pointer. The new `sae_lib/AGENTS.md` is found by the
  directory pointers of `sae dispatch`. It also carries "`sae next` stays read-only", from the
  next-step-cards row.

## Risks
- `prose-spec.md`: I paraphrased the long quotes and the 11-question checklist by hand. Very
  short terms stay quoted ("controls attention", "Inherits: root"). Some meaning may have shifted
  a little.
- The new `skills/shape-and-execute/scripts/sae_lib/AGENTS.md` ships with every install, as the
  owner approved.

## Findings filed
None.
