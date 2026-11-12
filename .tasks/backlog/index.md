# Backlog priorities

## Goal and status

- [human, 2026-10-30] Public adoption and marketing guide priorities. Favor features that make
  SaE useful to new users and give it a clear value proposition.
- [human, 2026-11-03] Restore this index alongside the tier folders and include newer items.
  Record agent maintenance of the index as Tier 2 work.
- This index reflects the current folders. It does not change CLI ordering or approval gates.
  Other rankings remain proposals unless the owner confirmed them. Placement does not approve
  implementation scope.

## Tier 1 — most urgent

- [GitHub sync](tier-1/2026-10-10-1136--github-sync.md) — connect backlog, tasks, and pull requests.
  The first integration scope remains undecided.
- [Orca integration](tier-1/2026-10-14-1321--orca-integration-worktrees-and-browser.md) — fit task
  worktrees and browser use into Orca.
- [Fast lane](tier-1/2026-10-14-2150--fast-lane-mode-for-mini-tasks.md) — reduce ceremony for small tasks.
  Direction decided on 2026-11-03.
- [External E2E integration](tier-1/2026-10-16-1010--consider-tester-army-e2e-integration.md) — investigate
  tester-army/e2e integration.
- [Return to an earlier phase](tier-1/2026-10-16-1823--return-a-task-to-an-earlier-phase.md) — move a task
  back from execution to shaping or planning. `sae abandon` already covers stopping a task.
- [Chrome notifications](tier-1/2026-10-22-2145--chrome-push-notifications-when-a-task-ne.md) — surface
  tasks that need attention.
- [First-task guidance](tier-1/2026-10-29-1330--guide-new-users-through-their-first-task.md) — help
  new users learn through their first tasks.
- [Concurrent job limits](tier-1/2026-10-29-1658--configure-concurrent-job-limits.md) — control task
  and global concurrency.
- [Risk and review](tier-1/2026-10-30-1311--consider-risk-independently-of-difficult.md) — assess
  consequences separately from implementation difficulty.

## Tier 2 — urgent

- [Headless orchestrator](tier-2/2026-10-13-1141--headless-orchestrator-for-unattended-ful.md) — run the
  orchestrator unattended.
- [Three lifecycle fixes](tier-2/2026-10-13-1141--shape-and-execute-four-fixes-from-the-20.md) — address
  review cancellation, finding closure location, and pickup of multiple backlog items.
- [PR impact report](tier-2/2026-10-16-1321--pr-impact-report-at-task-completion.md) — explain delivered
  value, decisions, and validation.
- [Demo GIF](tier-2/2026-10-18-1539--short-demo-gif-of-shape-and-execute-made.md) — demonstrate the
  workflow for public adoption.
- [Evals MVP](tier-2/2026-10-18-1937--evals-mvp-and-a-non-interactive-entry-fo.md) — gather evidence
  for the workflow's value and establish its non-interactive entry.
- [Autonomous backlog route](tier-2/2026-10-22-2311--autonomous-route-for-backlog-tasks.md) — define
  unattended work and decision boundaries.
- [Orchestrator context load](tier-2/2026-11-03-2034--orchestrator-context-load-large-task-gra.md) —
  assess repeated status output in large task graphs. Added since the earlier index.
- [Backlog folder option and template reminder](tier-2/2026-11-03-2038--backlog-folder-and-template-reminder.md) —
  simplify item placement and remind agents to complete descriptions. Added since the earlier index.
- [Agent maintenance of the index](tier-2/2026-11-03-2104--agent-maintenance-of-the-backlog-index.md) —
  keep entries, tier placement, descriptions, and links current. Added with this restoration.
- [Cross-project active task overview](tier-2/2026-11-03-2207--cross-project-active-task-overview.md) —
  explore one viewer screen for active tasks across all projects. For further consideration.
- [Roles, workflows and knowledge layout](tier-2/2026-11-04-1630--adopt-the-roles-workflows-and-knowledge.md) —
  rename `references/modes/` to `workflows/` and move loose knowledge files into `knowledge/`.

## Tier 3 — moderately urgent

- [Model changes after a job finishes](tier-3/2026-10-12-2206--change-the-model-or-effort-of-a-finished.md) —
  control fix-round model and effort while preserving context where possible.
- [Owner steps](tier-3/2026-10-13-1141--owner-steps-before-and-after-a-task.md) — surface operational
  steps around a task.
- [Improvement findings](tier-3/2026-10-18-1319--capture-improvement-proposals-for-owner-decision.md) —
  distinguish proposals and finding types.
- [Scheduled backlog work](tier-3/2026-10-22-1928--schedule-backlog-items-and-remind-about.md) —
  remind about overdue items.
- [Updates and model configuration](tier-3/2026-10-29-1053--update-notifications-and-model-configura.md) —
  help users maintain their installation and model choices.

## Tier 4 — can wait

- [Viewer v2](tier-4/2026-10-13-1141--viewer-v2-kanban-action-buttons-mixed-re.md) — expand boards,
  actions, and repository views.
- [Backlog folder tip](tier-4/2026-10-13-1154--sae-status-hints-at-backlog-subfolders-w.md) — make
  folder grouping discoverable.
- [Commit attribution trailer](tier-4/2026-10-21-1300--orchestrated-by-trailer.md) — identify
  commits orchestrated by SaE.
- [Greenfield application design](tier-4/2026-10-29-1328--document-and-plan-a-greenfield-applicati.md) —
  establish an application design before implementation tasks.

## Findings and unresolved candidates

- [Open findings](../findings/) remain a separate queue. The lifecycle batch overlaps the
  cancellation finding. Cross-harness writer dispatch and sandbox commit failures should
  be considered together.