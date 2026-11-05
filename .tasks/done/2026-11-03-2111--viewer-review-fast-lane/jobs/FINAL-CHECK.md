---
id: FINAL-CHECK
covers: [BATCH-VALIDATION]
verify:
  - python3 tests/run.py
---

# FINAL-CHECK: Full suite on the integrated task branch

## Objective
Run the full suite on the task branch with all jobs merged and report the result.

## Inputs
- `.tasks/repo/profile.md`: validation commands.
- Spec: [BATCH-VALIDATION].

## Scope
Run the smoke command and the full suite. A failure is reported with the failing tests and
their likely job; do not fix code.

## Boundaries
- No code changes. The visual check of the viewer is the owner's, in the task worktree at finish.

## Expected output
The result file with the test outcome.

## Validation
- [ ] Both commands from the profile ran on the integrated branch.
