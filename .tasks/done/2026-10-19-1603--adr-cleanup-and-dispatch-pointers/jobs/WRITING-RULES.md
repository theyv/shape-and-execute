---
id: WRITING-RULES
covers: [THREE-PLACES, REVISIT-WHEN]
verify:
  - python3 tests/run.py test_adr_index test_adr_rules test_retired_terms
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/references/modes/plan.md
  - skills/shape-and-execute/references/modes/execute.md
  - skills/shape-and-execute/references/modes/triage-decisions.md
  - skills/shape-and-execute/templates/decision-record.md
  - tests/test_adr_index.py
---

# WRITING-RULES: Three places for "why" knowledge, and revisit-when

## Objective
The writing rules name the three places by reach and the test, and the decision-record template
has an optional `revisit-when:` field.

## Inputs
- `specs.md`: [THREE-PLACES], [REVISIT-WHEN], "Domain language" (the test),
  [DECISION-REVISIT-OPTIONAL].
- `intent.md`: "Proposed outcome", the three places and their examples.
- Files: `references/modes/plan.md` section "Decision-record drafts", `references/modes/execute.md`
  section "Finish", `references/modes/triage-decisions.md`, `templates/decision-record.md`;
  `cmd_adr_new` and `cmd_adr_accept` in `scripts/sae_lib/findings.py` (read only).

## Scope
- One file states the three places and the test; the other two point to it in a line or two.
- `revisit-when:` in the template, optional, with a one-line comment.
- The `applies-to` comment in the template may say that path entries bring the record to the
  agents that change those paths; keep it one line.
- A test that `sae adr new` and `sae adr accept` work with and without the field (extend
  `tests/test_adr_index.py`).

## Boundaries
- A few lines per file. No lint or check for `revisit-when` (out of scope).
- No `sae` code change. If one turns out to be needed, park with a decision request.
- Do not touch role files, `templates/job.md` or `docs/adr/`.

## Expected output
Commits on the job branch: the rule changes, the template field, the test.

## Validation
- [ ] The three files agree and do not repeat each other at length.
- [ ] The test of the triage step "could a later agent rebuild this from the code?" is replaced
      or sharpened by the spec's test, not kept beside it.
