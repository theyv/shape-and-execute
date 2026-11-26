---
target: FIX-LOOP-EXITS
verdict: changes-required
---

# Review: REVIEW-FIX-LOOP-EXITS-2

## Findings

### 1. Merge can record acceptance of a superseded review — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/reviews.py:202–208, 757–771` and `skills/shape-and-execute/scripts/sae_lib/graph.py:88–98`.

**Affects:** LET-GO-REPORT and prior finding 2.

**Why it matters:** If round 1 requires changes and round 2 passes, the automatic merge can still hit a conflict and leave the job unmerged. A subsequent `sae merge --accept-review` records round 1 as accepted. The final report then lists its findings as waived even though round 2 superseded them.

**Correction:** Select the latest completed round first. Record it as accepted only if its verdict is `changes-required`. Keep the regression test for a newer pending round and add one for a newer passing round.

### 2. A let-go decision can name an absent finding or omit its reason — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/fix_loop.py:219–243, 263–268`.

**Affects:** TRIAGE, LET-GO-REPORT, and prior finding 3.

**Why it matters:** `--let-go` accepts `2: rare` when the review has no numbered findings. If the pending review later produces a finding 2, the final report attributes that decision to a finding the orchestrator had never seen. The command also accepts `2:` and reports the finding without a reason.

**Correction:** Before writing the event, require the number to identify exactly one finding in the review and require a nonblank reason.

### 3. Earlier title-based decisions duplicate accepted findings — minor

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/fix_loop.py:258–262, 274–285`.

**Affects:** LET-GO-REPORT and prior finding 3.

**Why it matters:** An earlier log of `Retry on timeout: rare` is printed as a standalone decision. When the round is accepted, the same finding appears again with the round’s reason. The report gives the owner two entries and two reasons for one finding.

**Correction:** Resolve earlier title-based entries by exact, unique title and use the resulting finding number for deduplication. Preserve the individual reason.

## Notes

The conflict-resolution drop guard and both parked decision sources passed read-only checks. The newer pending-round case and the overlapping-title case also behaved as expected. `git diff --check` passed. The worker reported 416 tests passed and 3 skipped. The suite requires temporary repositories, so I used in-memory checks for this review.