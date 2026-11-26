---
id: INTEGRATION-FIX-2
covers: [HARNESS-FALLBACK, DECISION-ANYTIME]
verify:
  - python3 tests/run.py test_writer_launch
scope:
  - skills/shape-and-execute/scripts/sae_lib/launch.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/workspaces.py
  - tests/**
---

# INTEGRATION-FIX-2: A writer fallback continues unfinished work and respects holds

## Objective
Fix findings 2 and 3 of `reviews/REVIEW-INTEGRATION.md`, each with a test that fails before
the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION.md` findings 2–3 (Evidence, Correction).
- Spec `[HARNESS-FALLBACK]`; the hold rule in `references/interaction-modes.md`.
- `jobs/WRITER-LAUNCH.result.md` and its FIX results: how the fallback and the park work.

## Scope
- 2: the printed fallback command continues the same writer's unfinished work in the task
  worktree (a one-writer task), so tracked edits left by the failed command do not block it.
  A first dispatch keeps the clean-checkout guard.
- 3: a parked writer that starts a new attempt goes through the hold and integration-park
  checks, also when it already has a failed attempt.

## Boundaries
- No other behavior changes. A new problem becomes a finding.
- Uncommitted edits are never discarded.

## Expected output
Commits on the job branch; the result lists each finding with its fix and test.

## Validation
- [ ] 2: a failed command leaves a tracked edit; the fallback starts and the edit is kept.
- [ ] 3: the sequence from the review (failed attempt, parked, hold activated by another job,
  fallback approved) is refused while the hold is active.
