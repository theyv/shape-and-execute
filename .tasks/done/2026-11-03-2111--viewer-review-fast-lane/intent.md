# Intent: Viewer and review maintenance

<!-- The task ID still says "fast-lane": fast lane moved out to its own task during shaping. -->

## Problem

Several small Tier 1 improvements can share one task and one validation pass. Research rows
overlap in the Shape card. Only the orchestrator can change a job's review flag. Spec review
gives no method for finding missing edge cases. The planner does not check shared foundations
before dependent jobs use them. The `sae adr new` help still states an old rule.

## Goal

[human] A batch of mechanical items that can run largely on their own once the spec is approved.
Use separate jobs where files and checks can be owned independently.

### Success means

- Shape research rows stay readable with long model, effort and override text.
- The owner can change a pending job's review flag in the viewer. The owner can also enable
  review for a running job before its result is collected, in the viewer or the CLI.
- Spec review actively searches for relevant scenarios that the spec does not list.
- The planner recognizes foundation jobs and places a check before dependent jobs use them,
  within the task's review settings.
- `sae adr new` help agrees with the current rule for decisions worth recording.
- The source backlog items and the finding are closed with a pointer to this task.

## Affected users and systems

Task owners, planners, reviewers and the task viewer. Changes stay in the source under
`skills/shape-and-execute/`, its tests and task records. Installed copies are not edited.

## Constraints

- Python 3.9 or newer, standard library only.
- Preserve the owner's control of settings, reviews and hard stops.
- Keep unrelated uncommitted changes in the home checkout intact.
- Never push or change the base branch.

## Sources

[human] The batch holds four Tier 1 items and one finding:

- [Shape card text overlap](../backlog/tier-1/2026-10-16-1858--shape-card-research-text-overlap.md) (picked up by `sae new --from`).
- [Spec review edge cases](../backlog/tier-1/2026-10-18-1319--spec-review-edge-case-finder.md).
- [Foundation job review](../backlog/tier-1/2026-10-18-1319--review-foundation-jobs-before-dependent-work.md).
- [Job review toggle](../backlog/tier-1/2026-10-22-2250--toggle-job-review-in-the-viewer.md).
- [ADR help wording](../findings/2026-10-19-1654--sae-adr-new-help-text-keeps-the-old-coul.md).

## Related tasks

- [human] Fast lane moved out of this batch: it needs design, not mechanical work. Its decisions
  from this shaping are in [the fast-lane backlog item](../backlog/tier-1/2026-10-14-2150--fast-lane-mode-for-mini-tasks.md).
  Pick it up as the next task after this one.
- [human] The abandon item moved out: `sae abandon` already exists. The real gap was returning
  a task to an earlier phase. Rewritten as
  [Return a task to an earlier phase](../backlog/tier-1/2026-10-16-1823--return-a-task-to-an-earlier-phase.md).

## Open questions

- See `specs.md`, "Open questions".
