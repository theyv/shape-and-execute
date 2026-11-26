---
id: FIX-LOOP-EXITS-FIX-1
covers: [JOB-DROP, LET-GO-REPORT, TRIAGE, DECISION-ANYTIME]
verify:
  - python3 tests/run.py
scope:
  - skills/shape-and-execute/scripts/sae_lib/**
  - tests/**
---

# FIX-LOOP-EXITS-FIX-1: Fix the four findings of the FIX-LOOP-EXITS review

## Objective
Fix findings 1–4 of `reviews/REVIEW-FIX-LOOP-EXITS.md`, each with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-FIX-LOOP-EXITS.md`: findings 1–4 (Evidence, Correction).
- `jobs/FIX-LOOP-EXITS.md`, `jobs/FIX-LOOP-EXITS.result.md`.
- `research/PROMPT-REVIEW-OPUS.md` finding 5: the same defect as finding 4 here.

## Scope
- 1: a generated `INTEGRATE-<ID>` job cannot be dropped alone; the refusal names the command
  that drops its target with it. (Prefer this over creating a fresh resolution job: one rule,
  no new state.)
- 2: `--accept-review` records the completed changes-required round whose verdict it bypasses,
  never a pending round. Test with a newer round pending.
- 3: a let-go decision names one finding by its number (and round); no prefix matching. The
  final report lists each accepted finding once with its own reason. Adjust the printed
  `--let-go` line so the orchestrator passes the number.
- 4: a decision job points to the target's `Decision request` section only when it exists; for
  a review-limit park it points to the review round that caused the park, in the job file and
  in the dispatch prompt.
- Check each finding before you act; list one you believe wrong under "Disputed findings".

## Boundaries
- No prompt text changes beyond the printed `--let-go` line and the decision pointer. No other
  behavior changes; a new problem becomes a finding.

## Expected output
Commits on the FIX-LOOP-EXITS branch; the result lists each finding with its fix and test.

## Validation
- [ ] One test per finding, failing before the fix.
