---
target: integration
verdict: changes-required
---

# Review: REVIEW-INTEGRATION-4

## Findings

### 1. Saving Project Stakes can still overwrite a fenced example — blocking

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:70–108,249–266`

**Affects:** `STAKES-VIEWER` and `STAKES-LOOKUP`. Round-three finding 1.

**Why it matters:** The fix refuses the original case with two matching headings. In a profile where the owner has yet to set Project Stakes, a fenced example can contain the only `## Project Stakes` line. An in-memory probe confirmed that lookup returns the example as the project’s stakes and saving replaces its text inside the fence. The real section is still missing.

**Correction:** Save only when the replacement or insertion point is known to be outside a fenced example. Add a regression test for a profile whose only matching heading is inside a fence. Verify that lookup ignores the example and that saving preserves its bytes.

## Notes

Round-three finding 2’s original case is fixed. In-memory probes confirmed that `2: Retry on timeout` records finding 1, `2` records finding 2, and a selector that matches both a number and another finding’s title is refused.

[beyond Project Stakes] If finding 1 is titled `2` and there is no finding 2, the resolver still reports a collision. Selecting finding 1 by its number works. `skills/shape-and-execute/scripts/sae_lib/fix_loop.py:309–313`

`git diff --check` passed. Verification used in-memory probes because the regression suite writes files.