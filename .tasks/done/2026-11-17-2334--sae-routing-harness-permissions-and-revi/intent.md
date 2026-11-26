# Intent: SaE routing, harness permissions and review workflow

## Problem

### Difficulty and model routing

The current difficulties are `mechanical`, `normal` and `hard`. Simple changes that need
local judgment tend to receive `normal` or `hard`. The owner sees `hard` used too often.
The current balanced example uses Sonnet High, Opus Medium and Opus High, respectively.
An extra category could route mechanical work more cheaply while keeping a Sonnet option
for simple changes.

### Harness permissions

A cross-harness writer launched with `codex exec -s workspace-write` could neither commit
nor run a verify command that needed a local IPC socket. The orchestrator routed the
remaining writer jobs to another harness without telling the owner. A previous run with the
same harness pair succeeded, but the attempt record did not explain the difference.

`sae setup snippets` prints permission settings for Codex and Claude Code. The viewer
does not apply or check them. `sae doctor` checks the local environment and the Codex
subagent cap. It does not test whether the effective launch of a routed job can perform
the job's required operations. Dispatch records the route and emits a launch command for
cross-harness reviews, but the attempt does not record the effective command or sandbox.

### Repeated findings against the same rule

A review took four rounds because several code paths implemented a shared rule separately.
Each fix job scoped the work to one instance. The next reviewer found another consumer
with the same defect. The fourth round found the consumers and fixed the rule at its source.
Most first-round findings in that task were independent and closed with local fixes.
A prescribed fix also introduced a new error in how the code read older data.

### Reviews that exceed the project's risk needs

In a single-owner local app, a legitimate startup failure led to speculative findings about
concurrent startup and narrow crash windows. The orchestrator turned the findings into fix
jobs. The resulting safeguards brought back the startup failure a user had actually hit.
The review ignored the project's stated preference for a simple design.

## Goal

[human] Deliver all four Tier 1 backlog items in one task.

[human] Use the backlog proposals as starting points. Confirm the intended behavior
in shaping before turning any proposal into a requirement.

### Success means

These are draft checks from the backlog. Confirm them during shaping.

- Users can distinguish procedural work from simple work that needs judgment. The CLI, setup,
  viewer and classification guidance agree on which phases allow each difficulty.
- The viewer shows effective job permissions for both harnesses and can apply recommended
  settings after confirmation. SaE detects a missing capability before dispatch to the
  affected harness. Attempts record the actual launch command and sandbox mode.
- An unavailable harness has a visible default behavior. A permitted change of harness records
  the requested route, the actual route and the reason. The viewer shows the exception.
- An actionable finding against a shared rule leads to one fix that covers the affected
  consumers. A repeated finding against a rule from an earlier round triggers a root-cause
  check before another patch. Fix jobs state the outcome and keep sibling paths in scope.
- Reviewers grade findings against the project's supported use, risk and promised guarantees.
  Orchestrators triage changes-required findings using the same bar before scheduling fixes.
  A new safeguard is also checked for failures it can introduce during supported use.

## Proposed outcome

### Difficulty

[human proposal] Use four implementation difficulties. The entries below illustrate the
proposed starting routes (balanced level). Backlog priority tiers and model tiers are separate
concepts.

| Difficulty | When to use it | Claude profile | Codex-only profile |
| --- | --- | --- | --- |
| `mechanical` | Follow a clear procedure. | Sonnet Medium | Terra Medium |
| `easy` | Make a simple change that needs local judgment. | Sonnet High | Sol Medium |
| `normal` | Design a solution for a difficult implementation task. | Opus Medium | Sol High |
| `hard` | Implement especially demanding logic or complex UI interactions. | Opus High | Sol Extra High |

[human] Difficulties have word names only. `L1`–`L4` stay the names of model tiers. The owner
noted that four tiers against three difficulties did not map; four difficulties fix that.

[human] `easy` is added to execution and research. Planning and review keep `normal` and
`hard` only, and `task_difficulty` stays `normal | hard`. Reason, in the owner's words:
planning and review should always be done well; "it is one moment, with a potentially large
gain later".

[human] An older configuration gains only the `easy` column, in execution and research tables
of every layer. The new cells take the owner's defaults; for economy and premium they move one
step along the owner's ladder (Claude: Sonnet Medium, Sonnet High, Opus Medium, Opus High;
Codex: Terra Medium, Sol Medium, Sol High, Sol Extra High). A missing model falls back to a copy
of the `mechanical` cell. All other cells, task and job labels and custom routes stay as they are.

| `easy` cell | economy | balanced | premium |
| --- | --- | --- | --- |
| Claude | Sonnet Medium | Sonnet High | Opus Medium |
| Codex | Terra Medium | Sol Medium | Sol High |

[human] Existing routing stays as it is: no switch to tier-based tables. The owner sometimes
picks models by hand or tests a new model.

[human] The tiers follow the difficulties: L1 mechanical, L2 easy, L3 normal, L4 hard. For
Claude, sonnet · high becomes the new L2 and the old L2 and L3 move up, so balanced `normal` and
`hard` keep their routes. In tier mode every cell has a tier (the viewer allows nothing else), so
cells that used opus · xhigh take L4; that is the accepted trade-off. Codex follows the owner's
table (terra · medium, sol · medium, sol · high, sol · xhigh). Setup mode proposes the same
renumbering for an existing configuration.

[human] Classification guidance stays short and leaves the choice to the model, without extra
ceremony (no required reasons, no CLI checks). The owner tested this in tasks with a prompt of
this form, and the model usually chose well: "mechanical tasks Sonnet Medium, ordinary Sonnet
High, hard Opus Medium; raise especially demanding logic and complex UI to Opus High".

### Harness permissions and fallback

[human] When the routed harness cannot run a job, the behavior depends on the interaction mode.
In `full-auto` the orchestrator switches the harness itself and records a routing exception
(requested route, actual route, reason). In the other modes the affected job parks,
independent work continues, and the orchestrator asks the owner; the owner's yes records a
one-job exception. The existing automatic review fallback (IF IT FAILS) stays, and the viewer
shows it as an exception too.

[human] `sae dispatch` prints a launch COMMAND for writer jobs routed to the other harness too,
and the attempt records the exact command. For now the command runs without a sandbox: Codex
`--dangerously-bypass-approvals-and-sandbox`, Claude Code `--permission-mode bypassPermissions`.
SaE is at an early stage, and a permission setup is complexity the owner does not want yet.
`sae status` and the viewer show that writers run without a sandbox. Review launches stay
read-only. Before a dispatch to the other harness, `sae` checks that its CLI is available.

[human] Out of scope: a sandboxed writer launch, a capability probe and applying permission
settings from the viewer. They wait in the backlog item
[Sandboxed writer launches](../backlog/2026-11-20-1159--sandboxed-writer-launches-for-cross-harn.md),
which links the research and the probe of this task.

[human] After a fallback, a running job finishes on the harness it runs on. Later dispatches use
the configured route again as soon as it is available.

### Review triage and fixes

The review flow below is settled in the decisions of 2026-11-20 and in `specs.md`.

- [human] An integration review round can also be accepted with a reason, under the same mode
  rules as `--accept-review`. When the orchestrator hands the task over for merge, it lists
  explicitly every finding it let go and why.
- [human] (Superseded on 2026-11-20 for the location: stakes become a part of SaE; see
  "Decisions of 2026-11-20" below.) Project stakes are a short `## Stakes` section in the repository's AGENTS.md (or
  CLAUDE.md when only that exists), read by every agent. It gives the agent the why, in prose,
  not hard rules: today's models over-engineer like a very strict developer, and a game for a
  child needs no guards for rare events while a bank does. Template, five lines:

  ```markdown
  ## Stakes

  Who uses it and why: <who, and what for>
  When it breaks: <what is survivable, what is not>
  What matters now: <speed / correctness / maintainability, and why now>
  Don't build: <optional: only what agents have already overbuilt here>
  So build it like: <a toy | a tool for friends | a product people pay for | a bank>
  ```

  When the section is missing, shaping asks the three questions once per repository, drafts
  the section and adds it after the owner confirms.
- [human] The reviewer still reports everything it finds; stakes decide only whether a finding
  blocks. Findings below the stakes go to the review's Notes tagged `[beyond stakes]`, with one
  sentence why. The orchestrator triages with the same bar. A fix that adds safeguards is
  checked for new failures in normal use. Rejected alternatives: a hard burden-of-proof rule
  (agents bend it), per-spec promise lists (cannot be complete; worthwhile fixes get skipped),
  a precedents file (cannot be maintained).

### Decisions of 2026-11-20

- [human] Stakes are a part of SaE. SaE never writes to the repository's AGENTS.md or CLAUDE.md.
  The viewer's Project tab gets a new top section, "Project settings", above "Defaults for new
  tasks in <repo>". It holds the stakes, with a "?" help that explains the topic in full.
  The owner finds the design heavy and accepts it unless a lighter one exists.
- [human] The stakes template lives in the skill's templates, and agents that draft stakes use
  it. Its line about breakage asks for how much breakage is acceptable, in one or two sentences,
  not for a list. Example values: a toy, "any"; a bank, "none, every failure is critical".
- [human] Review findings get a fixed shape: what the finding breaks (requirement, intent or
  stakes line) and how; expected and actual behavior; other places with the same rule, when the
  reviewer found them; and a suggested fix. The fix worker must make the expected behavior true.
  The suggested fix is a proposal: the worker may use a better way and says why.
- [human] A reviewer may propose a change of approach instead of a patch (for example: stop this
  job, add a job that gives the whole app one source for a value, then continue). The
  orchestrator decides under the interaction mode; when unsure, it runs a decision job for a
  recommendation.
- [human] From fix round N-1, where N is `max-review-rounds`, `sae dispatch` adds an explicit
  paragraph to the fix worker's prompt: the job is close to its limit, check whether the rounds
  share one cause and whether a different approach removes it. N-1 leaves the last fix a chance to
  save the job.
- [human] When a job parks at the round limit, the owner gets a plain step-by-step story: the
  job's intent, what the job did, each review round with its suggested fix, each fix, then the
  options (change the approach, reduce the requirement, another round) with a recommendation and
  its reason. The owner often does not follow a long full-auto job and needs this to decide.
- [human] Every change to SaE prompt text (skill, mode and role references, templates) needs a
  clear preview for the owner, so that the prompts do not grow without need.
- [human] The repository's AGENTS.md now says that the repository is public and examples stay
  anonymous.
- [human] The stakes template carries one agreed example, so that agents see what is meant;
  agents have misunderstood the section more than once. The spec writes the exact text of every
  prompt change as before and after, for the owner to approve; the repository's AGENTS.md now
  requires this preview outside `full-auto` unless the owner waives it.
- [human] When a fix worker sees a different approach, it finishes its job anyway and describes
  the approach under "Approach proposal" in its result; the next review round judges it. Parking
  stays at the round limit only. `sae` builds the step-by-step story for a park at the limit
  from the job and review files; the orchestrator adds its recommendation.

- [human] The decision job can also start from a review round, for one case only: a finding
  proposes a change of approach. Today `sae decision new` accepts only a parked job; local task
  records showed one decision job in about 1,750 jobs, while orchestrators logged about 500
  decisions without a job.
- [human] In scope: `sae job drop` for a parked writer job and its fix chain (backlog item
  [Drop a parked job](../backlog/tier-1/2026-11-20-1133--drop-a-parked-job-and-its-fix-chain.md)).
  It is the exit when the owner chooses "change the approach" at a park.
- [human] In scope: job results without empty sections (finding
  [Job results keep empty sections](../findings/2026-11-20-1339--job-results-keep-empty-sections-such-as.md)).
- [human] The planner rule for shared interfaces and business rules becomes one rule, named with
  the engineering terms that models know (walking skeleton, tracer bullet, contract first):

  ```
  - Parallel jobs that share an interface or a business rule: the first job that needs it
    builds it once, as a thin working slice with its tests (walking skeleton, tracer bullet);
    the other jobs wait for it. Add a separate contract job (contract first) only when the
    spec already fixes the shape and several jobs must start at once.
  ```

- [human] The repository's AGENTS.md now asks agents to name an established engineering pattern
  briefly when it helps the owner think, without listing patterns or steering toward them.
- [human] SaE asks about stakes when they are not set; it is a part of how the system thinks.
  It asks in the first grill round of a task, once per repository. When the owner skips, the
  profile's Stakes section reads: "Not set by the owner. Estimate the stakes from the repository
  instructions and the README, and build and review to that level: neither over- nor
  under-engineer." Not the code: agents must not read the whole repository for it. The viewer
  can change it later.
- [human] The orchestrator may start a decision job whenever it meets a serious problem whose
  analysis would fill its context. The job it concerns need not park. The owner accepts this for
  now and may tune it after real use.
- [human] Accepted as proposed: the explicit paragraph from fix round N-1, the park story that
  `sae` builds from the job and review files, and the worker's "Approach proposal".
- [human] The line about engineering patterns stays in this repository's AGENTS.md only, not in
  the skill. Its examples: single source of truth, make illegal states unrepresentable, parse
  don't validate, YAGNI.
- [human] Job results: optional sections say "delete when it does not apply" in the template,
  and the worker protocol says to leave empty sections out.

- [human] The orchestrator may set any limit in a fix job, but each "do not" gives its reason,
  also when it rules out a fix that a review proposed. A worker whose simpler approach a limit
  blocks says so in its Approach proposal, and the next review judges it. This keeps the
  orchestrator flexible and stops an unexplained limit from closing the simple exit.
- [human] Spec review triage (2026-11-20): one review round gets one fix job by default, because
  the reviewed work was one job; the fix job names the findings it must fix, and each finding set
  aside is logged with its reason. No early root-cause trigger: a second round is usually not a
  loop, so the paragraph from round N-1 stays the safety net. The read-only gap of Claude review
  commands goes to the sandboxed-launch backlog item. `sae job drop` refuses when the job's
  changes are already in the shared checkout.
- [human] Prompt changes are not written out in full in the spec. One job makes them from the
  drafts, checks the rest of the skill for contradictions and reports them, and a hold after it
  lets the owner read the diff.
- [human] Rejected: a reviewer rule that grades money, accounts and security "like any other
  topic". Wording: a finding or a plan step is measured by what the stakes justify, not by what
  they "call for".

## Constraints

- [human] Changes to skill files (SKILL.md, mode and role references, templates) follow the
  `agentic-systems-guidelines` skill and stay lean.
- SaE remains standard-library Python 3.9 or newer.
- Keep reviews grounded in concrete evidence. A failing example still matters when the fix
  covers a broader rule.
- Check reasonable crash recovery and other guarantees when the project or spec requires
  them. A theoretical possibility alone does not justify more machinery.
- Viewer permission changes require explicit confirmation. Task records for a public
  repository must omit secrets, private paths, private names and raw harness logs.

## Related tasks

The four source items remain available while the task is shaped:

- [Four difficulty levels](../backlog/tier-1/2026-11-13-1158--four-difficulty-levels.md)
- [Fix the broken rule](../backlog/tier-1/2026-11-13-1324--fix-the-broken-rule-not-one-instance.md)
- [Harness permissions and fallback](../backlog/tier-1/2026-11-17-1020--harness-permissions-in-the-viewer-and-a.md)
- [Review findings against real use](../backlog/tier-1/2026-11-17-1840--reviews-judge-against-the-projects-real.md)

[Risk and review](../backlog/tier-1/2026-10-30-1311--consider-risk-independently-of-difficult.md)
explores a separate risk setting. This task uses project risk to judge findings and leaves
the separate setting for that work.

## Open questions

None. Command names other than `sae job drop` are left to planning.
