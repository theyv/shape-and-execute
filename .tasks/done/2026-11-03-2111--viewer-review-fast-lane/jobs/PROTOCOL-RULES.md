---
id: PROTOCOL-RULES
covers: [SPEC-EDGE-SEARCH, FOUNDATION-CHECK, ADR-HELP-CONSISTENCY]
verify:
  - "! grep -q 'could not rebuild' skills/shape-and-execute/scripts/sae_lib/findings.py"
  - python3 tests/run.py test_findings
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/references/roles/reviewer.md
  - skills/shape-and-execute/references/roles/planner.md
  - skills/shape-and-execute/scripts/sae_lib/findings.py
  - tests/test_findings.py
  - tests/test_adr_rules.py
resolves:
  - .tasks/findings/2026-10-19-1654--sae-adr-new-help-text-keeps-the-old-coul.md
---

# PROTOCOL-RULES: Edge case filter, foundation rule, ADR help

## Objective
Three short text changes: an edge case filter in spec review, a foundation rule for the
planner, and the current decision-record test in `sae adr new` help.

## Inputs
- Spec: [SPEC-EDGE-SEARCH], [FOUNDATION-CHECK], [ADR-HELP-CONSISTENCY] and the decisions
  [DECISION-EDGE-LIGHT], [DECISION-FOUNDATION-NARROW] in `specs.md`.
- `references/roles/reviewer.md`, section "Target `spec`".
- `references/roles/planner.md`, the rule "Flag a job for review".
- `register_adr` in `sae_lib/findings.py`; the current test is in `references/modes/plan.md`,
  section "Decision-record drafts".

## Scope
- Reviewer: two or three sentences in the existing section. They work as a filter against
  invented cases, not as a generator.
- Planner: one rule next to the existing review-flag rule.
- ADR help: replace the old test with the current one; keep it short.
- If a test asserts the old help text, update it.

## Boundaries
- No new section, pass, agent, review point or `plan.md` section.
- Plain words, short sentences (repository rules in `AGENTS.md`).

## Expected output
A commit with the three changes.

## Validation
- [ ] Each addition reads as one rule an agent cannot misread; no example the agent would copy.
