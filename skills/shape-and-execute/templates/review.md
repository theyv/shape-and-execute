---
target: <spec | plan | JOB-ID | integration>
verdict: pass        # pass | pass-with-notes | changes-required
---

# Review: <REVIEW-ID>

## Findings

### 1. <title> — blocking | major | minor
**Evidence:** <file:lines, or artifact section>
**Breaks:** <REQ-ID, intent or stakes line>: how this contradicts it
**Expected:** <what should happen> **Actual:** <what happens now>
**Also in:** <other places that apply the same rule, found by search; delete when none>
**Suggested fix:** <a proposal; may be a change of approach>

## Notes
<!-- Remarks that do not block. A finding below the stakes: `[beyond stakes]` and one
     sentence why. -->
