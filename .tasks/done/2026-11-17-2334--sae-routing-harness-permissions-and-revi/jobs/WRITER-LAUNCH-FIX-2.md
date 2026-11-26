---
id: WRITER-LAUNCH-FIX-2
covers: [WRITER-COMMAND, HARNESS-FALLBACK]
verify:
  - python3 tests/run.py test_writer_launch test_record_privacy
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/launch.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/reviews.py
  - skills/shape-and-execute/scripts/sae_lib/common.py
  - tests/test_writer_launch.py
  - tests/saetest.py
---

# WRITER-LAUNCH-FIX-2: A retry never collects the previous attempt's result

## Objective
Fix finding 1 of `reviews/REVIEW-WRITER-LAUNCH-2.md`: `sae collect` accepts a result only when
the current attempt wrote or replaced it, also for the fallback attempt.

## Inputs
- `reviews/REVIEW-WRITER-LAUNCH-2.md` (finding 1, Correction) and `reviews/REVIEW-WRITER-LAUNCH.md`
  (finding 2, the first try).
- `jobs/WRITER-LAUNCH-FIX-1.result.md`: what the first fix did.

## Scope
- At dispatch, record the existing result file's metadata (for example size, mtime in
  nanoseconds and a content hash), not only a start time in seconds.
- At collect, refuse an unchanged result for a COMMAND retry and for its fallback attempt (the
  attempt without a `launch` record). The earlier report stays readable for the retry.
- Regression tests: a same-second retry, and a fallback that leaves the report unchanged.
- This is round 3 of 3: the next changes-required round parks the job for the owner. Fix the
  cause, not the case: one freshness rule that every collect path uses.

## Boundaries
- No prompt text changes; no other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the WRITER-LAUNCH branch; the result names the rule and the tests.

## Validation
- [ ] Both regression tests fail before the fix.
