# Intent: Change the model or effort of a finished job while its review runs

## Problem
`sae job override` refuses a running or finished job ("a running or finished job keeps its
model"). A job that is done and waits for its review cannot get a cheaper model or effort for
its fix round. The fix runs as a new job (`<ID>-FIX-1`), so the worker's context is lost.

Example: SAE-ADR-MIGRATION ran on opus · xhigh for about 23 minutes. While Codex reviewed it,
the owner wanted the fix round on opus · medium, so that it does not take as long again.
Owner's words: "I should be able to change it while the review is running, before that context is lost.".

## Goal
The owner can change the model or effort of a finished job while its review runs, and the fix
round uses the new setting.

### Success means
- During a job review, `sae job override <task> <ID> --effort medium` succeeds and the fix
  round runs on that effort.
- The fix keeps the worker's context where the harness allows it.

## Affected users and systems
`sae job override`, job reviews and fix jobs (`--fix-of`), `sae dispatch --resume`.

## Related tasks
Spun off from an earlier task, sae-findings-docs, where the owner hit the refusal during the
review of SAE-ADR-MIGRATION.

## Open questions
- Can a resumed worker change its effort or model in each harness (Claude Code SendMessage,
  Codex resume)? If not, keeping context and changing effort conflict; the owner chooses.
