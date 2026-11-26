---
target: PROMPT-TEXT
verdict: changes-required
---

# Review: REVIEW-PROMPT-TEXT

## Findings

### 1. The review loop can bypass the owner at the round limit — major

**Evidence:** `references/modes/execute.md:57–75` tells the orchestrator to add a fix or accept the review before it checks whether the round limit has parked the job. `scripts/sae_lib/planning.py:223–228` treats adding a fix as the owner's choice and clears the target's park.

**Affects:** [PARK-STORY] and the round-limit stop in `references/interaction-modes.md`.

**Why it matters:** On the last allowed round, following the steps in order can unpark a writer before the owner sees the story or chooses another round.

**Correction:** Check for a round-limit park before adding fixes or accepting the review. When parked, relay the story and wait for the owner's decision.

### 2. The fallback contract omits completed jobs reopened for more work — major

**Evidence:** `references/modes/plan.md:28–39` and `references/modes/shape.md:63–66` reopen completed jobs with `--resume`. `scripts/sae_lib/progress.py:382–385` supports that path. `jobs/WRITER-LAUNCH.md:46–56` specifies a missing-CLI fallback for pending jobs and allows parking pending or running jobs.

**Affects:** [HARNESS-FALLBACK] and [PROMPT-JOB].

**Why it matters:** If the other CLI disappears after a research result, a follow-up dispatch leaves the job `done`. The pending-job fallback cannot reopen it, and the approval path has no way to park it.

**Correction:** Record the handoff contradiction and cover reopened jobs in the fallback contract. Preserve `--resume` for the retry and define how to record the owner's approval while the prior result remains `done`.

### 3. The orchestrator is told to skip the section that can trigger a decision job — major

**Evidence:** `references/modes/execute.md:3–5` permits reading a result body only for parked or failed jobs or disputed findings. Lines 89–94 name a worker's Approach proposal as a reason to use a decision job. `jobs/PROMPT-TEXT.result.md:52` identifies the missing collection notice.

**Affects:** [FIX-WORKER] and [DECISION-ANYTIME].

**Why it matters:** A successful fix can contain an Approach proposal and no dispute. The next reviewer may see the proposal, but the orchestrator has no instruction to read it even if collection reports it.

**Correction:** Make a reported Approach proposal an explicit exception to the result-reading rule and direct the orchestrator to read that section.

### 4. The fix command always uses the first job ID — minor

**Evidence:** `references/modes/execute.md:61–62` uses `<ID>-FIX-1` for every round. `scripts/sae_lib/planning.py:185–188` rejects duplicate IDs.

**Affects:** [TRIAGE] and [APPROACH-CHECK].

**Why it matters:** The documented command fails on a second fix for the same writer, and it provides no distinct IDs when a round needs multiple fixes.

**Correction:** Use `<FIX-ID>` and say to choose a fresh ID for each fix, or show `-FIX-1` as a first-round example.

## Notes

`git diff --check` passed. Test results were taken from the job result and were not rerun during this read-only review.