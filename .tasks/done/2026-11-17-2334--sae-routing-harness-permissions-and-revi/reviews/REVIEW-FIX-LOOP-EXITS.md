---
target: FIX-LOOP-EXITS
verdict: changes-required
---

# Review: REVIEW-FIX-LOOP-EXITS

## Findings

### 1. Dropping a conflict-resolution job leaves its target stuck — major

**Evidence:** `sae_lib/fix_loop.py:44–59, 75–92` and `sae_lib/reviews.py:239–252`.

**Affects:** JOB-DROP and merge recovery.

**Why it matters:** After `A` hits a merge conflict, the owner can drop a failed `INTEGRATE-A` by itself. Retrying the merge of `A` tells the orchestrator to dispatch `INTEGRATE-A` again, but that job is permanently dropped. `A` stays unmerged and blocks integration review.

**Correction:** Refuse a standalone drop of a generated conflict-resolution job and name its target’s group drop command, or let merge recovery create a fresh resolution job.

### 2. Accepting a job review can record an unfinished round — major

**Evidence:** `sae_lib/reviews.py:756–769` and `sae_lib/fix_loop.py:234–244`.

**Affects:** LET-GO-REPORT.

**Why it matters:** After a fix creates pending `REVIEW-A-2`, `sae merge A --accept-review` bypasses the completed verdict from `REVIEW-A` but records `REVIEW-A-2` as accepted. The final report reads the unfinished round and omits the findings that were waived.

**Correction:** Record the completed changes-required round whose verdict the merge bypasses. Test acceptance with a newer round still pending.

### 3. A let-go decision can hide a different finding — major

**Evidence:** `sae_lib/fix_loop.py:215–244`.

**Affects:** TRIAGE and LET-GO-REPORT.

**Why it matters:** If a review contains `Retry` and `Retry on timeout`, logging `Retry on timeout: rare` and then accepting the round hides `Retry` from the final report. The prefix match treats the decision as applying to both findings.

**Correction:** Resolve each let-go decision to one finding by its number or complete title. Use that identity to keep the individual reason and list each accepted finding once.

### 4. Decision jobs can point to a request that does not exist — major

**Evidence:** `sae_lib/findings.py:57–74`, `sae_lib/prompts.py:239–252`, and `sae_lib/reviews.py:691–705`.

**Affects:** DECISION-ANYTIME.

**Why it matters:** When `sae` parks a writer at the review-round limit, the writer’s result can still be a normal completed result without a `Decision request` section. `sae decision new --from A` tells the adviser to answer that missing request, and the dispatch prompt omits the review that caused the park.

**Correction:** Use the `Decision request` section when it exists. For a review-limit park, point the job file and dispatch prompt to the review round that caused it.

## Notes

`git diff --check`, CLI help checks, and in-memory probes ran without file writes. The verification suite requires temporary repositories, so its results come from the worker’s report.