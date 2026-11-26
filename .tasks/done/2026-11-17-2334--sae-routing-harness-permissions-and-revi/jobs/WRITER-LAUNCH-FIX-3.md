---
id: WRITER-LAUNCH-FIX-3
covers: [WRITER-COMMAND, HARNESS-FALLBACK]
verify:
  - python3 tests/run.py test_writer_launch test_record_privacy test_dispatch_pointers
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/**
  - tests/test_writer_launch.py
  - tests/saetest.py
  - tests/test_dispatch_pointers.py
---

# WRITER-LAUNCH-FIX-3: An empty result slot at every dispatch replaces the fingerprint check

## Objective
Make a stale result impossible to collect by moving an existing result file aside at every
dispatch, and remove the fingerprint check that `WRITER-LAUNCH-FIX-2` added.

## Inputs
- `reviews/REVIEW-WRITER-LAUNCH-3.md` (finding 1: the missing-CLI fallback path), and rounds 1–2
  (`reviews/REVIEW-WRITER-LAUNCH.md` finding 2, `reviews/REVIEW-WRITER-LAUNCH-2.md` finding 1).
- `jobs/WRITER-LAUNCH-FIX-1.result.md`, `jobs/WRITER-LAUNCH-FIX-2.result.md`: the earlier fixes.

## Scope
Owner decision, 2026-11-22. Three rounds patched one dispatch path at a time; this fix removes
the cause.
- Rule: when a dispatch starts an attempt and the job's result file exists, `sae` renames it to
  `<ID>.result.attempt-<N>.md` (N = the attempt it belongs to; never overwrite an existing
  file). Collect then needs only "the result file exists".
- Put the rule in the ONE function that every dispatch passes (first dispatch, `--resume`,
  COMMAND, fallback after a failed COMMAND, fallback after a missing-CLI refusal, review and
  non-review). Not per path. If no such single place exists, create it.
- Remove the fingerprint code and its recorded fields from FIX-2; keep its regression tests
  where they still describe behavior, adapted to the new rule.
- A follow-up or retry prompt points to the moved file as the earlier report to build on (one
  pointer line; reuse an existing pointer constant when one fits). The agent writes the full
  result again.
- Readers that list or show results (viewer data, finish, record checks) ignore or tolerate
  `*.result.attempt-*.md`.
- Tests: the scenario of review round 3 (a local attempt, then a follow-up routed to a missing
  CLI, then the printed fallback; collect rejects when nothing new is written and accepts a
  rewritten result); a same-second retry; the moved file exists with the old content.
- This is the last review round (4 of 4).

## Boundaries
- No other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the WRITER-LAUNCH branch; the result names the single function, the removed code
and the tests.

## Validation
- [ ] Every dispatch path goes through the one function (name the call sites in the result).
- [ ] No fingerprint code remains.
