---
id: INTEGRATION-FIX-8
covers: [TRIAGE, LET-GO-REPORT]
verify:
  - python3 tests/run.py test_fix_loop_exits test_fix_loop_guidance
scope:
  - skills/shape-and-execute/scripts/sae_lib/fix_loop.py
  - skills/shape-and-execute/scripts/sae.py
  - skills/shape-and-execute/references/modes/execute.md
  - tests/**
---

# INTEGRATION-FIX-8: Let-go names its finding and its reason separately

## Objective
Fix finding 2 of `reviews/REVIEW-INTEGRATION-2.md` with a test that fails before the fix.

## Inputs
- `reviews/REVIEW-INTEGRATION-2.md` finding 2 and `reviews/REVIEW-INTEGRATION.md` finding 6.
- `jobs/INTEGRATION-FIX-3.result.md`: the resolver today.

## Scope
Fix the rule, not the instance: stop guessing where a title ends. The finding and the reason
are passed separately (for example `--let-go <number or exact title>` plus `--reason`), and the
resolver matches the finding exactly or refuses, listing the candidates. Update the help text
and the one place in `execute.md` that shows the call, if it shows one.

## Boundaries
- No other behavior changes. A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the new call shape and the tests.

## Validation
- [ ] With findings `Retry` and `Retry: lost write`, each can be let go on its own, with its
      own reason, and the final report names the right one.
- [ ] An unknown title or number is refused with the list of findings.
