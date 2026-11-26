---
target: VIEWER-SURFACES
verdict: changes-required
---

# Review: REVIEW-VIEWER-SURFACES-3

## Findings

### 1. A settings load can pair a stale draft with the latest revision — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/server.py:507–512` reads the draft and its revision separately. In a read-only reproduction, one tab saved between those reads. The second tab received the original draft with the new revision. Its save returned `200` and overwrote the first tab’s edit.

**Affects:** `STAKES-VIEWER` stale-save protection.

**Why it matters:** The revision check accepts a draft that never reflected the revision it carries.

**Correction:** Derive the draft and revision from a single profile read. Add a regression check that exercises a settings load during a save.

### 2. The revision ignores changes to stored line endings — minor

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:96–104` hashes text read through `common.py:192–196`, which converts CRLF to LF. In a read-only reproduction, the first save converted a CRLF section to LF, and both saves from the original base returned `200`.

**Affects:** The round-two requirement to base saves on the section exactly as stored.

**Why it matters:** A save can change the stored section while leaving the old revision valid.

**Correction:** Hash the stored section with its original line endings. Add a regression check for a save that changes only those endings.

## Notes

The read-only checks confirmed that comment-only and trailing-space-only saves now return `200` followed by `409`. `git diff --check` passed. The full suite requires writable fixtures and was not rerun.