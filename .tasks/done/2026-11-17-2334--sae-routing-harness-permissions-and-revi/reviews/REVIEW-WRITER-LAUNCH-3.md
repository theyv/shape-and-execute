---
target: WRITER-LAUNCH
verdict: changes-required
---

# Review: REVIEW-WRITER-LAUNCH-3

## Findings

### 1. A missing-CLI fallback can still collect the previous result — major

**Evidence:** `sae_lib/launch.py:111–121, 194–210`, `sae_lib/progress.py:438–448`, and `tests/test_writer_launch.py:429–455`.

**Affects:** WRITER-COMMAND and HARNESS-FALLBACK. Round-two finding 1 remains open on the missing-CLI path.

**Why it matters:** If a research job first ran on the orchestrator’s harness and a follow-up routes to a missing CLI, the refused dispatch adds no attempt. The printed fallback then sees a previous attempt with no `launch` record and skips saving the result fingerprint. An in-memory probe followed the printed fallback and confirmed that `sae collect` accepted the unchanged report and marked the follow-up done.

**Correction:** Save the result fingerprint when dispatch recognizes a printed harness fallback, including after a missing-CLI refusal. Add a regression that starts with a local attempt, follows the printed fallback, and checks that collection rejects the unchanged report and accepts a rewritten one.

## Notes

In-memory probes confirmed that the same-second COMMAND retry and the fallback after a launched COMMAND now reject unchanged reports and accept rewritten ones. `git diff --check` passed. The fixture-based suite was not rerun in the read-only workspace.