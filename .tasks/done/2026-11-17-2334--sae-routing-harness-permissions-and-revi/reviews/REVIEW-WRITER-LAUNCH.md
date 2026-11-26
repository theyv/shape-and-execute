---
target: WRITER-LAUNCH
verdict: changes-required
---

# Review: REVIEW-WRITER-LAUNCH

## Findings

### 1. A parked first dispatch can bypass an active hold — blocking

**Evidence:** `launch.py:147–158, 297–303` and `progress.py:396–425`.

**Affects:** HARNESS-FALLBACK and dispatch holds.

**Why it matters:** A pending writer can be parked after a missing-CLI refusal. While it waits, an independent job can complete and activate a hold. The printed fallback uses `--resume`, which skips the hold and dependency checks even though the writer has never started. An in-memory probe confirmed that this path reaches workspace preparation with an active hold.

**Correction:** Treat a parked job with no attempts as a first dispatch for readiness checks. Test the printed fallback after an independent job activates a hold.

### 2. A retry can collect the previous attempt’s result — major

**Evidence:** `launch.py:63–68` and `reviews.py:537–565`.

**Affects:** WRITER-COMMAND and HARNESS-FALLBACK.

**Why it matters:** Writer COMMANDs clear the harness output and retain the existing result. If a reopened research job exits successfully without updating its report, `sae collect` accepts the old report as the new result. An in-memory probe confirmed that collection marks the job done and assigns the new attempt’s tokens to that stale result.

**Correction:** Require a result produced or updated by the current attempt before collecting it. Keep the earlier report available as context for the retry. Test a reopened job whose COMMAND exits without writing a result.

### 3. Codex writer COMMANDs fail in projects without Git — major

**Evidence:** `launch.py:63–65` and `workspaces.py:167–171`. The installed `codex exec --help` identifies `--skip-git-repo-check` as the flag that permits execution outside a Git repository.

**Affects:** WRITER-COMMAND.

**Why it matters:** SaE supports tasks in ordinary folders. When a writer in one of those folders routes to Codex, the PATH check passes and dispatch records an attempt, but the printed COMMAND cannot start.

**Correction:** Include `--skip-git-repo-check` in both the printed and recorded Codex writer command for no-Git tasks. Cover that path with a test.

### 4. Automatic fallback leaves the failed attempt open — major

**Evidence:** `launch.py:139–142, 297–300` and `progress.py:431–451`.

**Affects:** HARNESS-FALLBACK and the attempt traceability ADR.

**Why it matters:** The park path sets the failed attempt’s `ended` timestamp. The direct fallback used in `full-auto` and for reviews appends a replacement attempt without closing the failed one. An in-memory probe confirmed that the fallback succeeds while the first attempt’s `ended` remains unset.

**Correction:** Close the failed COMMAND attempt when the fallback dispatch succeeds. Test the recorded timestamps after executing the printed fallback in `full-auto`.

## Notes

`git diff --check` passed. The probes ran in memory. The test suite requires writable fixtures, so this read-only review did not rerun it.