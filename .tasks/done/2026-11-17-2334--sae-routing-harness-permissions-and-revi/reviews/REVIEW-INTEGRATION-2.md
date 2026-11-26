---
target: integration
verdict: changes-required
---

# Review: REVIEW-INTEGRATION-2

## Findings

### 1. A stored open fence can still delete validation commands — blocking

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:66–97,232–247`

**Affects:** `STAKES-VIEWER`. Prior finding 1.

**Why it matters:** I reproduced the data loss in memory with an unclosed fence in Project Stakes followed by `## Validation commands` and a fenced shell example under `## Worktree notes`. The parser treats the shell example’s opening fence as a close, then takes the first `#` shell comment as a section heading. The save passes the fence check and deletes the validation commands.

**Correction:** Refuse the save when the replacement would remove a profile section heading that the fence parser skipped. Add a regression test with a later shell example containing a comment and verify that the profile bytes are preserved.

### 2. Title-based triage can still select the wrong finding — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/fix_loop.py:269–305,332–363`

**Affects:** `TRIAGE` and `LET-GO-REPORT`. Prior finding 6.

**Why it matters:** With findings titled `Retry` and `Retry: lost write`, the input `Retry: lost write: the caller retries` can mean the shorter title with reason `lost write: the caller retries`. The resolver silently selects the longer title. I confirmed the selection in memory. The final report then attributes the decision to the wrong finding.

**Correction:** Refuse summaries with multiple valid title-and-reason splits and provide an explicit way to pass the finding and reason separately. Test both selections with the same pair of titles.

### 3. The viewer still shows an accepted integration round as failed — minor

**Evidence:** `skills/shape-and-execute/assets/viewer/task-views.js:150–155,201–206,670–673`

**Affects:** `ACCEPT-INTEGRATION` and the viewer’s Plan and Reviews tabs. Prior finding 7.

**Why it matters:** The CLI releases the integration gate after acceptance. The Plan card still shows `✕ changes required`, and the Reviews tab omits the recorded acceptance and reason.

**Correction:** Show the recorded acceptance and reason in both places and retain the original verdict in the review history.

## Notes

Prior findings 2–5 are closed. The regression tests cover a fallback that preserves tracked edits, a parked fallback that waits for hold release, and a decision job that dispatches and collects before plan approval. All eight tiers and 72 routing cells match the approved AMEND-3 proposal.

`git diff --check`, JavaScript syntax checks, and 10 read-only tests passed. I reviewed the file-writing regression tests without running them in the read-only worktree.