# Intent: Change the model or effort of a running or finished job

## Problem
`sae job override` refuses a running or finished job ("a running or finished job keeps its
model"). A job that is done and waits for its review cannot get a cheaper model or effort for
its fix round. The fix runs as a new job (`<ID>-FIX-1`), so the worker's context is lost.

Example: SAE-ADR-MIGRATION ran on opus · xhigh for about 23 minutes. While Codex reviewed it,
the owner wanted the fix round on opus · medium, so that it does not take as long again.
Owner's words: "I should be able to change it while the review is running, before that context is lost.".

A running job has the same gap. In the task sae-routing-harness-permissions-and-revi, the owner
asked to move a just-dispatched job from opus · medium to opus · high. The orchestrator had to
stop the worker and dispatch it again with `--resume`, spawning it on opus · high by hand. The
task record still shows the routed opus · medium, and the viewer shows a resume that was only a
model change. Owner's words: "otherwise the viewer fills up with clutter".

## Goal
The owner can change the model or effort of a running job, and of a finished job while its
review runs. The next run (a restart, or the fix round) uses the new setting, and the task
record and the viewer show the model that really ran, without a fake resume.

### Success means
- For a running job, one command (for example `sae job override` with a restart, or a cancel and
  a new dispatch on the same ID) changes the model or effort; the record shows the change and
  its reason once.
- During a job review, `sae job override <task> <ID> --effort medium` succeeds and the fix
  round runs on that effort.
- The fix keeps the worker's context where the harness allows it.

## Affected users and systems
`sae job override`, job reviews and fix jobs (`--fix-of`), `sae dispatch --resume`.

## Related tasks
Finding "No way to cancel a dispatched job; collect marks it done"
(`.tasks/findings/2026-10-22-2042--no-way-to-cancel-a-dispatched-job-collec.md`): a cancel
command would cover part of this.
Spun off from an earlier task, sae-findings-docs, where the owner hit the refusal during the
review of SAE-ADR-MIGRATION.

## Open questions
- Can a resumed worker change its effort or model in each harness (Claude Code SendMessage,
  Codex resume)? If not, keeping context and changing effort conflict; the owner chooses.
