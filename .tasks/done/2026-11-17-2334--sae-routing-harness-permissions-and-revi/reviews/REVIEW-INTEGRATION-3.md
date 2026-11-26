---
target: integration
verdict: changes-required
---

# Review: REVIEW-INTEGRATION-3

## Findings

### 1. Saving Project Stakes can overwrite a fenced example — blocking

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:70–91,231–242`

**Affects:** `STAKES-VIEWER` and `STAKES-LOOKUP`. Round-two finding 1.

**Why it matters:** In an in-memory probe, a fenced Markdown example under `## Worktree notes` contained `## Project Stakes` and `## Validation commands` before the real sections. The viewer read the example as the project’s stakes. Saving replaced the example’s text and left the real stakes stale.

**Correction:** Use fence-aware section lookup and refuse the save when a malformed fence makes the replacement range uncertain. Test that saving edits the real section and preserves the fenced example byte for byte.

### 2. A numbered title can still select the wrong finding — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/fix_loop.py:297–316,342–345`

**Affects:** `TRIAGE` and `LET-GO-REPORT`. Round-two finding 2.

**Why it matters:** In a numbered review, finding 1 can have the exact title `2: Retry on timeout`. I passed that title to `--let-go` and reproduced the resolver selecting finding 2. The final report attributed the decision and reason to finding 2.

**Correction:** Match numeric selectors against the whole argument. Resolve exact titles separately and reject any selector that matches two findings. Test that `2` selects finding 2 and `2: Retry on timeout` selects finding 1.

## Notes

The original malformed-fence example is refused before writing. The two unnumbered `Retry` titles now resolve independently. Round-two finding 3 is closed. The Plan card and Reviews tab show the acceptance and reason, and the Reviews tab displays the original verdict.

Verification covered in-memory probes, `git diff --check`, and `node --check`. The file-writing regression suite was unrun in the read-only worktree.