# Intent: Drop a parked job and its fix chain

**Status: rough idea. Not shaped [human].**

## Problem

[agent] The owner can decide that a parked writer job must never merge, for example when its
approach is wrong and a new job replaces it. `sae` has no command for that decision:

- `sae job remove` accepts only `pending` jobs.
- The integration review starts only when **every** writer job is merged
  (`materialize_integration_review`), so the first round never comes.
- The final validation waits until every other job is `done` (`waits_for`), so it never becomes
  ready.
- Its fix jobs (`<ID>-FIX-n`) are writers that also stay unmerged, with the same effect.

In a recent task a job stayed parked after seven review rounds. The owner replaced it with a new,
smaller job. The orchestrator could repoint the dependants with `sae job edit --needs`. The task
still cannot reach the integration review and the final validation, except through a hand edit of
`state.json`, which the skill forbids.

## Goal

[human] Add the missing command so that the owner's "drop it" decision has a supported path.

### Success means

- A command such as `sae job drop <task> <ID> --reason "<why>"` marks a parked, failed or done
  unmerged writer job as dropped, together with its fix chain and their review rounds.
- Dropped jobs never merge. The integration review, the final validation and the `finish` gates
  ignore them. The branches stay, as with `abandon`.
- The command refuses while another job still needs the dropped job, and names the
  `sae job edit --needs` call to run first.
- The drop is logged as a decision with the reason, and the final report lists dropped jobs.
- The viewer shows a dropped job as dropped, not parked.

## Constraints

- Only on the owner's word: the orchestrator does not drop a job alone.
- Never delete branches or result files of a dropped job.

## Open questions

- A new status `dropped`, or a flag on the job.
- Whether `sae job drop` also offers to add the replacement job in one step.

## Related

- [Fix the broken rule, not one instance](2026-11-13-1324--fix-the-broken-rule-not-one-instance.md):
  the case where the owner stops a non-converging fix loop is exactly when this command is needed.
