---
target: plan
verdict: changes-required
---

# Review: REVIEW-PLAN

## Findings

### 1. A dropped fix can still reach the task branch — blocking

**Evidence:** `jobs/FIX-LOOP-EXITS.md:46–50,71–78`, `skills/shape-and-execute/scripts/sae_lib/workspaces.py:35–49`, `planning.py:196–212`, `reviews.py:213–229,275–294` in the same package.

**Affects:** `JOB-DROP`.

**Why it matters:** A fix job commits to its parent’s branch. Marking that fix `dropped` can leave its commits on a branch that later merges. The current `--fix-of` path also accepts an unmerged writer regardless of its status. The planned readiness test would miss both paths.

**Correction:** Define the drop group around the branch that holds the changes. Specify what happens when a fix is named directly or a group member is running. Guard fix creation and the shared merge path, and test that dropped commits stay out of the task branch.

### 2. A fallback waiting for approval can block independent work — major

**Evidence:** `jobs/WRITER-LAUNCH.md:45–51,71–76`, `skills/shape-and-execute/scripts/sae_lib/asks.py:82–104`, `graph.py:122–154,192–208` in the same package.

**Affects:** `HARNESS-FALLBACK`.

**Why it matters:** `sae ask` records the question without changing scheduling. After a missing CLI refusal, the job stays ready and the execute loop can retry it. After a failed COMMAND, the job stays `running` and can occupy the only writer slot while the owner decides.

**Correction:** Assign how the workflow defers the affected job, frees the failed attempt’s slot, and resumes after approval. Test both failure paths with one writer slot and a second independent writer.

### 3. A fallback can lose a route requested by a dispatch flag — major

**Evidence:** `brief.md:52–55`, `jobs/WRITER-LAUNCH.md:45–56,71–76`, `skills/shape-and-execute/scripts/sae_lib/routing.py:163–179`.

**Affects:** `HARNESS-FALLBACK`.

**Why it matters:** A pending job dispatched with `--harness` can request a different route from the configured one. If the CLI is missing, refusal leaves no attempt. The printed fallback must carry the rejected route forward or the next dispatch can record the configured route as both requested and actual.

**Correction:** Fix the handoff for the requested route in the printed fallback command. Test a flag-only request through refusal, fallback, exception recording, and the next ordinary dispatch.

### 4. The setup jobs can publish the wrong balanced Codex routes — major

**Evidence:** `specs.md:97–127,640–652`, `jobs/PROMPT-TEXT.md:41–44,70–75`, `jobs/EASY-DIFFICULTY.md:67–73`, `skills/shape-and-execute/references/modes/setup.md:107–117`.

**Affects:** `EASY-UPGRADE`, `TIERS-FOLLOW-DIFFICULTY`, `SETUP-PROPOSAL`.

**Why it matters:** Applying the draft’s blanket tier renumbering moves balanced Codex execution `mechanical` from L2 to L3 and `normal` from L3 to L4. With tiers enabled, `normal` and `hard` then both use L4. The prompt job checks Claude’s effective routes, and the code job can pass with a hand-built configuration that never exercises the proposal. The prompt job also leaves the upgrade steps for an existing schema-2 configuration implicit.

**Correction:** Give `PROMPT-TEXT` explicit ownership of the balanced Codex mapping and the existing-config upgrade instructions. Validate the saved proposal through dispatch with tiers on and off, and check that the upgrade preserves the existing cells’ direct model and effort values.

### 5. Accepted reviews can disappear into a round-level summary — major

**Evidence:** `specs.md:283–298`, `brief.md:24–27`, `jobs/FIX-LOOP-EXITS.md:51–58,71–78`.

**Affects:** `LET-GO-REPORT`, `ACCEPT-INTEGRATION`.

**Why it matters:** One acceptance event can record a reason for the round without identifying the findings it sets aside. The planned test covers one individually logged finding. It can pass even if accepting a review with several findings leaves the owner with only a round ID and a reason.

**Correction:** Specify how both accept commands associate their reason with each finding they set aside. Test a multi-finding acceptance and a mixed round where one finding was already logged separately.

### 6. Shaping and the viewer can write stakes to different checkouts — major

**Evidence:** `specs.md:197–225,582–585`, `jobs/STAKES-IN-PROMPTS.md:29–42`, `skills/shape-and-execute/scripts/sae_lib/gitutil.py:82–104`, `lifecycle.py:98–106`, `viewer.py:130–136` in the same package.

**Affects:** `STAKES-LOOKUP`, `STAKES-ASK`, `STAKES-VIEWER`.

**Why it matters:** A task created from an ordinary linked worktree records that checkout as its home. The viewer uses the main worktree, and the stakes job points to the main-worktree helper. Shaping can save the owner’s answer to the local profile while status and the next dispatch read a different copy. A test that starts in the main checkout misses this case.

**Correction:** Fix one profile location for shaping, status, dispatch, and the viewer. Test the save and the next dispatch for a task created from a linked worktree.

### 7. Parallel jobs own the same dispatch control flow — major

**Evidence:** `plan.md:25–46,80–81`, `jobs/WRITER-LAUNCH.md:40–51`, `jobs/FIX-LOOP-EXITS.md:41–45`, `skills/shape-and-execute/scripts/sae_lib/progress.py:374–426`.

**Affects:** Execution order and the dispatch gates.

**Why it matters:** The plan treats the overlap in `progress.py` as a trivial call-site conflict. Both jobs change the order of checks in `cmd_dispatch`. One must check CLI availability before state changes, and the other must let an advisory job through a park or hold. Each branch can pass its tests while the merged control flow violates one of those rules.

**Correction:** Give one job ownership of dispatch gate ordering, either by sequencing the two jobs or by assigning their shared call site to one owner. Check that a decision job can run during a hold, a writer still waits, and a missing external CLI leaves task state unchanged.

### 8. Raising the review limit can remove the approach check — major

**Evidence:** `specs.md:312–320`, `jobs/FIX-LOOP-GUIDANCE.md:34–37,58–62`.

**Affects:** `APPROACH-CHECK`.

**Why it matters:** The job computes the threshold from the limit at dispatch. If round 3 parks a task and the owner raises the limit from 3 to 5, the fix for round 3 falls below the new threshold. It loses the paragraph just after the owner has had to intervene, although the spec says later fixes retain it.

**Correction:** Settle the threshold across a limit increase before implementation. Check the fix immediately after raising the limit on a parked round.

## Notes

`sae check` reported no errors and four scope overlaps between parallel jobs. This review used the plan, the registered graph, and a read-only inspection of the relevant source.