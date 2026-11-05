# Plan: Viewer and review maintenance

## Strategy
Three independent workstreams by file area: the Shape card (viewer), the review flag (CLI,
server, viewer), protocol and help text. One final validation runs the full suite. The owner
skipped the planner; the plan was written inline.

## Jobs at a glance
- `SHAPE-ROWS` — research rows of the Shape card stay readable with overrides.
- `REVIEW-TOGGLE` — review flag control in the viewer and on running jobs, CLI included.
- `PROTOCOL-RULES` — edge case filter, foundation rule, ADR help; resolves the ADR finding.
- `FINAL-CHECK` — full suite on the integrated branch.

## Parallelism
`PROTOCOL-RULES` runs in parallel with the viewer chain. `REVIEW-TOGGLE` waits for `SHAPE-ROWS`:
both change `task-views.js` and `task-views.css`.

## Hot files
- `assets/viewer/task-views.js`, `task-views.css` → `SHAPE-ROWS`, then `REVIEW-TOGGLE` (ordered).
- `tests/` → each job adds its own tests; a trivial conflict is accepted.

## Integration points
None beyond the shared viewer files.

## Final validation
`FINAL-CHECK` runs the smoke command and the full suite. The visual check of the Shape card and
the review control is the owner's, in the task worktree at finish.

## Review flags
None: job reviews are off for this task [human]. The integration review covers all jobs.

## Risks and adaptation triggers
- `REVIEW-TOGGLE` finds that the flag is read before collection (planned reviews, cards): the
  worker fixes it within its scope; if it reaches beyond, it parks.
- `SHAPE-ROWS` cannot reproduce the overlap in node tests: it fixes from the screenshots and
  leaves the visual check to the owner.

## Riskiest assumptions
- [agent] Nothing snapshots the review flag before `sae collect`; enabling it on a running job
  is enough for collection to add the review.
- [agent] The overlap is a viewer-only layout bug (JS/CSS), with no server change.
- [agent] The viewer sends a fixed reason for review-flag changes instead of asking the owner.
- [agent] Closing the three source backlog items (untracked in the home checkout) is done by the
  orchestrator after finish, not by a job: the task worktree does not see them.
