---
target: integration
verdict: changes-required
---

# Review: REVIEW-INTEGRATION

## Findings

### 1. Editing Project Stakes can delete validation commands — blocking

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:66–87,171–203`

**Affects:** `STAKES-VIEWER`.

**Why it matters:** The viewer accepts an unclosed Markdown code fence in Project Stakes. On the next save, the section reader treats every following heading as part of the fence. I reproduced this in memory. Saving an incomplete example and then correcting it deleted the entire `## Validation commands` section.

**Correction:** Reject edits that would hide the next profile section. If the stored section already has an ambiguous boundary, refuse the save and preserve the file. Test both cases with a section after Project Stakes.

### 2. The fallback command cannot resume a chain writer that left edits — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/launch.py:188–194`, `skills/shape-and-execute/scripts/sae_lib/progress.py:446–449`, `skills/shape-and-execute/scripts/sae_lib/workspaces.py:73–82,167–174`

**Affects:** `HARNESS-FALLBACK`.

**Why it matters:** In a one-writer task, the worker edits files in the task worktree. If the external harness exits before committing, the printed `IF IT FAILS` command hits the clean-checkout check before the replacement worker starts. The partial edits remain, and the prescribed recovery cannot continue from them.

**Correction:** Let a fallback continue the same writer’s unfinished work in the task worktree while preserving the clean-checkout guard for first dispatches. Test a failed command that leaves a tracked edit behind.

### 3. A parked writer can resume through an active hold — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/launch.py:304–311`, `skills/shape-and-execute/scripts/sae_lib/progress.py:412–445`, `tests/test_writer_launch.py:585–600`

**Affects:** `HARNESS-FALLBACK`, `DECISION-ANYTIME`, and the hold rule in `references/interaction-modes.md`.

**Why it matters:** Suppose a failed external command parks job A while an independent job B finishes and activates a user hold. Approving A’s fallback then starts a new worker through that hold because A already has an attempt. The test covers a job parked before its first attempt, which still goes through the hold check.

**Correction:** Apply hold and integration-park checks when a parked writer starts a new attempt. Test the sequence with a failed attempt already recorded.

### 4. The setup proposal changes 14 existing direct Codex routes — major

**Evidence:** `specs.md`, `SETUP-PROPOSAL`; `skills/shape-and-execute/references/modes/setup.md:89–127`, compared with `3892f20`

**Affects:** `SETUP-PROPOSAL` and `TIERS-FOLLOW-DIFFICULTY`.

**Why it matters:** The spec keeps each existing cell’s direct model and effort while changing its tier. The proposal changes 14 direct pairs across Codex execution and research. For example, balanced mechanical execution changes from `sol · low` to `terra · medium` with tiers off. The plan describes that choice, but the spec has no amendment for it.

**Correction:** Keep the new tier mapping and restore the previous direct pairs outside the `easy` column, or record the change in an approved amendment. Check the proposal with tiers both on and off.

### 5. A decision job created from a plan review cannot run during planning — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/findings.py:85–109`, `skills/shape-and-execute/scripts/sae_lib/common.py:57–61`, `skills/shape-and-execute/scripts/sae_lib/graph.py:68–74,186–188`

**Affects:** `DECISION-ANYTIME`.

**Why it matters:** `sae decision new --from REVIEW-PLAN` creates a job and tells the orchestrator to dispatch it. Dispatch refuses until execution. The recommendation arrives too late to inform the plan decision that prompted it. The same phase restriction applies to a decision about a spec review.

**Correction:** Allow advisory jobs to dispatch in shaping and planning. Test creation, dispatch, and collection from a completed plan review before plan approval.

### 6. Title-based triage can misreport which finding was set aside — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/fix_loop.py:269–293,305–337`

**Affects:** `TRIAGE` and `LET-GO-REPORT`.

**Why it matters:** For an unnumbered review, `--let-go` accepts any nonblank title, even one absent from the review. A title containing a colon also gets split at the wrong point. I reproduced a report that listed `Retry` as let go and then listed the same finding, `Retry: lost write`, as accepted with a different reason.

**Correction:** Resolve the input to exactly one finding when logging the decision. Store that finding’s identifier and reason separately. Test an absent title and a title containing a colon.

### 7. The viewer still shows an accepted integration round as failed — minor

**Evidence:** `skills/shape-and-execute/assets/viewer/task-views.js:121–129,150–155,201–206,670–673`

**Affects:** `ACCEPT-INTEGRATION` and the viewer’s Plan and Reviews tabs.

**Why it matters:** The CLI releases the integration gate after acceptance. The graph still displays `✕ changes required`, and the Reviews tab shows the original verdict without the acceptance. The owner sees a failed review alongside a task that can finish.

**Correction:** Display the recorded acceptance and its reason on the integration card and review row while retaining the original verdict in the review history.

## Notes

`git diff --check`, all four retired-term tests, and JavaScript syntax checks passed. I used read-only and in-memory checks and skipped the full suite because it creates temporary files. `sae check` on the live task record reported missing objectives for `PROMPT-TEXT-FIX-1` and `PROMPT-TEXT-FIX-2`.