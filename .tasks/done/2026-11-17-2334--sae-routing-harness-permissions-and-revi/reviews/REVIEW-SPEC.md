---
target: spec
verdict: changes-required
---

# Review: REVIEW-SPEC

## Findings

### 1. The Claude review command does not enforce read-only access — blocking

**Evidence:** `specs.md:118–126,144–151`, `research/CLAUDE-LAUNCH.md:291–302`, `skills/shape-and-execute/scripts/sae_lib/prompts.py:409–427`.

**Affects:** `WRITER-COMMAND`, `HARNESS-FALLBACK`.

**Why it matters:** Claude’s `dontAsk` mode still honors inherited write approvals. The command’s read-tool allowlist adds approvals, so an existing project setting can let a reviewer edit the checkout. The spec requires read-only reviews and also requires this command to stay unchanged.

**Correction:** Define how read-only access is enforced for both harnesses and their automatic fallbacks. Check that a review can read the diff and cannot write to the checkout when the launch environment already grants writes.

### 2. The launch record can overstate the writer’s permissions — major

**Evidence:** `specs.md:111–142,598–605`, `research/CLAUDE-LAUNCH.md:115–119,222–234`, `research/CODEX-LAUNCH.md:426–448`.

**Affects:** `WRITER-COMMAND`, `LAUNCH-RECORD`, `NO-SANDBOX-VISIBLE`.

**Why it matters:** A Claude writer can start with `bypassPermissions` while its Bash sandbox remains enabled or its Codex parent restricts writes. The writer can then hit the Git or socket failure that motivated this task while the viewer reports `none`. Codex’s JSON output also provides no effective sandbox attestation.

**Correction:** Decide whether an unrestricted launch environment is a prerequisite or whether the contract promises a bypass request. Give the command record, status and viewer the same meaning. The bypass request can be recorded without a capability probe.

### 3. A missing CLI needs a fallback that works before an attempt exists — major

**Evidence:** `specs.md:144–160,469–482`, `skills/shape-and-execute/scripts/sae_lib/progress.py:365–409,441–449`, `skills/shape-and-execute/references/modes/shape.md:40–49,114–122`.

**Affects:** `HARNESS-FALLBACK`.

**Why it matters:** A missing CLI must leave the job pending, or uncreated for a due spec or plan review. The existing `IF IT FAILS` uses `--resume`, which refuses a pending job. An emitted command can also fail after the job is already running, which needs a different transition. The new instructions appear only in execute mode, so shaping has no instructions for a refused launch or a cross-harness research command.

**Correction:** Specify a working fallback for each starting state and carry it into every affected phase. Define how a job waiting for owner approval stays visible and out of the ready queue while independent jobs continue.

### 4. Dropping a job can leave its changes in the delivery — blocking

**Evidence:** `specs.md:307–319`, `skills/shape-and-execute/scripts/sae_lib/lifecycle.py:169–184`, `skills/shape-and-execute/scripts/sae_lib/workspaces.py:41–49`, `skills/shape-and-execute/scripts/sae_lib/reviews.py:213–225,275–299`.

**Affects:** `JOB-DROP`.

**Why it matters:** In a chain-layout task, the writer and its fixes commit directly to the task branch before the review passes. Changing their status to dropped and ignoring them at the gates can deliver the rejected work. In a worktree task, generated reviews depend on the target and its fixes, so counting dependencies within the drop group can also make the command refuse its intended case.

**Correction:** Define what must happen to changes already in the shared checkout before a drop can succeed, including in folders without Git. Only dependants outside the group being dropped should block the operation.

### 5. A fix worker can implement a finding the orchestrator set aside — major

**Evidence:** `specs.md:233–271,439–449,487–496`, `skills/shape-and-execute/scripts/sae_lib/prompts.py:230–244`.

**Affects:** `TRIAGE`, `FIX-WORKER`, `LET-GO-REPORT`.

**Why it matters:** A review can contain one startup failure and one speculative safeguard. Triage keeps the first and sets aside the second, but the worker receives the entire review and is told to make each finding’s `Expected` true. The final report also promises a reason for every finding let go, while the mixed-triage flow requires no durable record for those individual findings.

**Correction:** Make the fix job’s selected findings authoritative, with the review as evidence. Require a durable reference and reason for each finding set aside. Check the fix and final report with a review that contains both kinds of finding.

### 6. Recurring defects can still produce separate patches — major

**Evidence:** `intent.md:26–32,59–61,182–185`, `specs.md:233–240,262–281,487–493,570–581`.

**Affects:** `TRIAGE`, `FIX-WORKER`, `APPROACH-CHECK`.

**Why it matters:** If two findings break one rule, the spec allows separate fix jobs and only requires the worker to cover places the reviewer listed. If a second round finds another consumer with the same defect and the limit is five, the required cause check waits until round four. Both paths permit the repeated local fixes that prompted the task.

**Correction:** Require one fix objective per broken shared rule, with the affected consumers in scope. Decide whether a repeated finding triggers an immediate cause check, as the intent describes, with the `N − 1` paragraph as a backstop. Also settle whether a fix authorized after a park at `N = 1` gets the paragraph. The formula and the acceptance check currently give different answers.

### 7. The setup proposal can make `easy` and `mechanical` route identically — major

**Evidence:** `intent.md:89–102`, `specs.md:71–99,583–594`, `skills/shape-and-execute/references/modes/setup.md:70–81`, `skills/shape-and-execute/scripts/sae_lib/config.py:368–397`.

**Affects:** `EASY-UPGRADE`, `SETUP-PROPOSAL`.

**Why it matters:** With the setup proposal’s default tier switch on, the new `easy` cell takes the `mechanical` tier. Balanced Claude therefore gets Sonnet Medium for both, even though the new cell shows Sonnet High. Existing project and task tables are also partial. When a task overrides only `mechanical` and global setup has filled `easy`, the spec leaves it unclear which route wins.

**Correction:** Specify the effective `easy` route with tiers on and off, and define how explicit inherited `easy` cells interact with a nearer `mechanical` override. Check dispatch results as well as the table display.

### 8. The viewer and the next dispatch can read different stakes — major

**Evidence:** `specs.md:164–211,532–553`, `skills/shape-and-execute/scripts/sae_lib/tasks.py:136–141`, `skills/shape-and-execute/scripts/sae_lib/server.py:450–467`.

**Affects:** `STAKES-LOOKUP`, `STAKES-ASK`, `STAKES-POINTER`, `STAKES-VIEWER`.

**Why it matters:** Execution uses a task worktree while the Project tab addresses the repository. A viewer edit can save the home profile while the next reviewer reads an older copy from the task worktree. On a fresh setup, the proposed template also has a `## Stakes` heading with blank fields. Under the first-section-found rule, that placeholder can suppress the one-time question.

**Correction:** Choose a canonical source that the viewer, status and new dispatches resolve consistently across checkouts. Define how a missing or blank section differs from an explicit skip. Check a viewer edit during execution and the first grill after profile setup.

### 9. A decision job can be created at an integration park but cannot run — major

**Evidence:** `intent.md:178–189,203–206,230–232`, `specs.md:283–305,508–515`, `skills/shape-and-execute/scripts/sae_lib/graph.py:99–109,143–149`, `skills/shape-and-execute/scripts/sae_lib/progress.py:386–396`.

**Affects:** `DECISION-ANYTIME`, `PARK-STORY`.

**Why it matters:** At the integration round limit, the orchestrator may need a decision worker to compare a change of approach with another fix before recommending either to the owner. The current park blocks every new dispatch. The proposed acceptance only proves that the decision job can be created.

**Correction:** Define whether a read-only advisory decision can run while the integration park remains in force. If it can, check dispatch and collection while the owner’s approval still gates further fixes.

### 10. The prompt changes lack a complete approval preview — major

**Evidence:** `intent.md:190–197`, `AGENTS.md:21–23`, `specs.md:346–356,583–615`, `skills/shape-and-execute/references/modes/setup.md:23–41`.

**Affects:** Prompt approval, `DIFF-EASY`, `SETUP-PROPOSAL`.

**Why it matters:** The setup preview gives one example table, omits the guide that still teaches three difficulties, and supplies only the replacement for the permissions section. The technical contract lets a worker report deviations in its result, after the owner was supposed to see the exact wording.

**Correction:** Complete the exact before-and-after preview for affected prompt text and bring any later wording change to the owner before it is written, under the repository’s existing exceptions.

## Notes

Evidence comes from the supplied launch reports and a read-only inspection of the current source.