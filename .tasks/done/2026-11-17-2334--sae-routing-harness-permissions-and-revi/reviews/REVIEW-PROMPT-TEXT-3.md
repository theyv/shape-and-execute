---
target: PROMPT-TEXT
verdict: pass
---

# Review: REVIEW-PROMPT-TEXT-3

## Findings

None. Round-two finding 1 is resolved.

## Notes

The execution, planning, and shaping instructions now reserve the `done` exception for a missing-CLI refusal. If a follow-up command starts and fails, the attempt is `running`. Outside `full-auto`, the instructions say to park it, ask the owner, and retry with `--resume` after approval.

`git diff --check` passed. I did not rerun the test suite.