---
target: VIEWER-SURFACES
verdict: changes-required
---

# Review: REVIEW-VIEWER-SURFACES-4

## Findings

### 1. The revision can miss the section’s final newline — minor

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:117–122` drops the newline before the next heading when it reconstructs the section for hashing. In an in-memory check, removing the following section and leaving Project Stakes at EOF without a final newline kept the same revision. The stale save returned `200`.

**Affects:** `STAKES-VIEWER` stale-save protection for the section exactly as stored.

**Why it matters:** A change to the section’s final line ending can leave a stale draft eligible to save.

**Correction:** Hash the exact stored section through the start of the next heading, or through EOF. Add a regression check for a section that becomes the last section in the file and loses its final newline.

## Notes

The draft and revision now come from one profile read. In-memory checks confirmed that a save between settings reads keeps them paired and that a CRLF-to-LF change invalidates the old revision. `git diff --check` passed. The full suite requires writable fixtures and was not rerun.