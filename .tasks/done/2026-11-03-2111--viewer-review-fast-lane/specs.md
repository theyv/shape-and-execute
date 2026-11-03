# Spec: Viewer and review maintenance

## Summary

Four Tier 1 items and one finding. The viewer gets readable research rows in the Shape card and
a control for a job's review flag. The CLI allows changing it on a running job. The spec
review protocol gets an edge case pass. The planner protocol gets a rule for foundation jobs.
The `sae adr new` help uses the current decision-record rule.

## Scope

### In scope

- The four backlog items and the finding listed in [intent.md](intent.md).
- Viewer and CLI changes, their tests, and the reviewer and planner protocols.
- Closing the source items with a pointer to this task.

### Out of scope

- Fast lane: [backlog item](../backlog/tier-1/2026-10-14-2150--fast-lane-mode-for-mini-tasks.md), next task.
- Returning a task to an earlier phase: [backlog item](../backlog/tier-1/2026-10-16-1823--return-a-task-to-an-earlier-phase.md).
- A new scheduler mechanism or a new review gate.
- Installed skill copies.

## Requirements

### [SHAPE-ROW-READABILITY] Keep Shape research rows readable

Research labels, model names, effort and the override mark stay distinct and readable at the
card width of the reported screenshots. Model override controls stay usable.

Acceptance:
- [ ] A test or fixture builds the reported case: at least five research rows, overrides active.
- [ ] Labels do not overlap model, effort or override text, also with long model names.
- [ ] Shortened text keeps the full value in the tooltip.
- [ ] Rows without an override, review rows and keyboard access still work.

### [JOB-REVIEW-CONTROL] Change a job's review flag in the viewer and during a run

The owner turns the review flag of a pending or running writer job on or off, in the viewer
or the CLI, until its result is collected. The worker is not stopped or restarted.

Acceptance:
- [ ] A pending or running writer job shows its review flag and an accessible control to change it.
- [ ] The viewer write goes through the existing server route pattern and runs `sae job edit`.
- [ ] `sae job edit --review` and `--no-review` work on a running writer job; other fields of a running job still refuse.
- [ ] `sae collect` uses the flag as it is at collection, and adds the job review when
  `selected-jobs` is a review point.
- [ ] The control shows when the flag has no effect (`all-jobs`, or job reviews off) and does
  not change review points.
- [ ] Done, failed and non-writer jobs refuse the change with a clear message.
- [ ] Each change is logged with a reason and its origin (viewer or CLI) and shows on the
  next next-step card.

### [SPEC-EDGE-SEARCH] Edge cases in spec review: a filter, not a generator

Two or three sentences in the existing `Target spec` section of the reviewer protocol. The
reviewer walks the key flows through boundaries (empty or missing data, failure and retry, two
at once). It reports a gap only when the scenario is realistic for this intent and the spec
gives no answer. It does not report invented cases.

Acceptance:
- [ ] The addition sits in the existing `Target spec` section; no new section, pass, agent or review point.
- [ ] Each reported gap has the form: scenario → consequence → the decision the spec needs.
- [ ] The text tells the reviewer not to report scenarios outside the intent or without a concrete consequence.

### [FOUNDATION-CHECK] Review a foundation job before dependent work

One rule in the planner protocol. A foundation job delivers text that other jobs build on: a
contract, a schema or a design document, not code that tests check. When three or more jobs
use it in parallel, the planner flags it with `--review`. A reviewed writer merges only after its
review passes, and dependent jobs wait for the merge, so no new mechanism is needed. When job
reviews are off, the planner does nothing extra: the owner's setting wins.

Acceptance:
- [ ] One rule in the planner protocol, next to the existing rule for review flags; no new `plan.md` section.
- [ ] The rule excludes code checked by tests and jobs with fewer than three parallel users.
- [ ] The rule keeps the existing condition: flag only when job reviews are on.

### [ADR-HELP-CONSISTENCY] Current decision-record rule in `sae adr new` help

Acceptance:
- [ ] The help no longer says "a later agent could not rebuild from the code".
- [ ] It states the current test: without the record, an agent would "fix" something on purpose,
  or bring back a rejected option.
- [ ] The finding is closed through `sae` with a pointer to this task.

### [BATCH-VALIDATION] Validate the integrated result

Acceptance:
- [ ] The smoke command and the full suite from `.tasks/repo/profile.md` pass.
- [ ] The Shape card and the review control are checked visually in the viewer.

## Technical contract

- Task state changes only through `sae`; the viewer runs `sae` as a subprocess.
- Parallel writer jobs do not share files; viewer files `task-views.js` and `task-views.css`
  get one owner job or ordered jobs.

## Decisions

### [DECISION-RUNNING-FLAG] Both directions on a running job
**Decision:** On a running writer job the owner may turn review on and off, until `sae collect`.
**Reason:** The same flag change before collection; a job can turn out simpler or riskier than planned.
**Based on:** user decision · **Provenance:** [human]

### [DECISION-BATCH] Mechanical batch only
**Decision:** Four Tier 1 items and one finding. Fast lane and the abandon item move out.
**Reason:** The owner asked for mechanical work that runs largely on its own; fast lane needs design.
**Based on:** user decision · **Provenance:** [human]

### [DECISION-EDGE-LIGHT] Edge case search stays light
**Decision:** A few sentences in the existing reviewer protocol, written as a filter against invented cases.
**Reason:** The owner fears that a model invents unrealistic cases and burns tokens; a requirement of a concrete
scenario and consequence limits that. No extra agent or review.
**Based on:** user decision · **Provenance:** [human]

### [DECISION-FOUNDATION-NARROW] Narrow foundation rule
**Decision:** Only text deliverables used by three or more parallel jobs; code checked by tests is excluded.
**Reason:** A rule based on any two dependants would flag most early jobs of a graph and add review for nothing.
**Based on:** user decision · **Provenance:** [human]

### [DECISION-REVIEW-POINTS] Plan and integration review only
**Decision:** This task runs with review points plan and integration.
**Reason:** The jobs are independent; nothing builds on them, so the integration review sees what job reviews would.
**Based on:** user decision · **Provenance:** [human]

### [DECISION-FOUNDATION-REUSE] Reuse job review for foundation checks
**Decision:** The check is a job review on the foundation job, not a new mechanism.
**Reason:** Dependent jobs already wait for the reviewed job's merge.
**Based on:** existing architecture (`graph.waits_for`, `reviews.after_writer_done`) · **Provenance:** [agent]

## Open questions

- None.
