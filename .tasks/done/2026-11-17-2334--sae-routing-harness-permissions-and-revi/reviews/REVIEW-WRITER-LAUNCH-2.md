---
target: WRITER-LAUNCH
verdict: changes-required
---

# Review: REVIEW-WRITER-LAUNCH-2

## Findings

### 1. A retry can still collect the previous attempt’s result — major

**Evidence:** `sae_lib/reviews.py:538–548, 568–586`, `sae_lib/common.py:115–120`, and `tests/test_writer_launch.py:187–208`.

**Affects:** WRITER-COMMAND and HARNESS-FALLBACK. Round-one finding 2 remains open.

**Why it matters:** Dispatch records the start time to the second. If a report was written earlier in that same second, an unchanged report passes the freshness check. The printed fallback to the orchestrator’s harness also skips the check because the replacement attempt has no `launch` record. In-memory probes confirmed that `sae collect` marked the job done in both cases. The first probe also assigned the new attempt’s tokens to the old report.

**Correction:** Record the existing result’s file metadata at dispatch and require evidence that the result was written or replaced before collecting a COMMAND retry or its fallback. Keep the earlier report available for context. Add regression cases for a same-second retry and a fallback that leaves the report unchanged.

## Notes

Round-one findings 1, 3, and 4 are resolved. Read-only probes confirmed that the hold and dependency gates run before workspace preparation, the no-Git flag appears in both Codex writer commands, and successful fallback closes the previous COMMAND attempt. `git diff --check` passed. The fixture-based suite requires a writable workspace.