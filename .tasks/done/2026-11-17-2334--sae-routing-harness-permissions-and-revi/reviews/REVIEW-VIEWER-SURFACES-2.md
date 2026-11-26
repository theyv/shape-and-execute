---
target: VIEWER-SURFACES
verdict: changes-required
---

# Review: REVIEW-VIEWER-SURFACES-2

## Findings

### 1. Prior finding 3 remains open for edits that leave the normalized text unchanged — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/server.py:506–511` and `:652–666` use normalized section text as the save base. `skills/shape-and-execute/scripts/sae_lib/stakes.py:77–92` strips comments and trailing spaces, while `:141–161` can write them. An in-memory check held the first save open while a second save started from the same base. When the first save added trailing spaces, both requests returned `200` and the second overwrote the first. When the first changed the wording, the requests returned `200` and `409` as expected.

**Affects:** `STAKES-VIEWER` and the fix requirement that overlapping saves from the same base yield one success and one conflict.

**Why it matters:** The lock serializes the saves, but an edit that changes the stored section without changing its normalized text leaves the old base valid. The first tab reports success even though the second tab can overwrite its edit.

**Correction:** Use a revision derived from the exact stored section as the save base. Compare it under the existing lock and keep the normalized text for display. Add a regression test where the first save changes the stored section while leaving the normalized text unchanged.

## Notes

Prior finding 2 is resolved. The read-only Node check confirmed that the editor and both buttons are disabled during a pending save. Prior findings 1 and 4 were let go by the orchestrator. `git diff --check` passed. The full suite was not rerun because its fixtures require writes.