---
type: friction
confidence: high
paths: [skills/shape-and-execute/scripts/sae.py]
---

# No way to cancel a dispatched job; collect marks it done

## Observation
A research job was dispatched with --resume for follow-up questions. The user then asked for a different model, so the main session stopped the worker before it wrote anything. sae job override refuses a running job ('a running or finished job keeps its model'), and sae has no cancel command for one job (only abandon for the whole task). The only way out was sae collect, which marked the job done with confidence high from the old report, although the follow-up questions were never answered. The questions moved to a new job. The task history now shows the job as done and gives no sign that the follow-up was cancelled, so the user cannot tell what happened.

## Evidence
- `sae job override <task> <JOB>` on the dispatched job: exit 1, "<JOB> is not pending; a running or finished job keeps its model."
- `sae --help`: no command cancels or withdraws one job.
- `sae collect <task> <JOB>` after the stop: "<JOB>: done — research done, confidence high"; the result file was the unchanged report from the first run.

## Cost
The user sees a finished research job with no new result and no reason, and has to ask the agent what happened. The task record loses the fact that a dispatch was withdrawn and why. Changing a model mid-run costs a new job ID and a hand copy of the questions.


## Suggestion
The user should be able to strike out a dispatched job. For example `sae job cancel <task> <JOB> --reason "<why>"`: status `cancelled` (not done), the reason in the event log and in the viewer, the result file left as it was. For a `--resume` dispatch, cancel returns the job to its previous state (done with the earlier report) and records that the follow-up was withdrawn. Optionally, allow `job override` on a cancelled job, so a re-dispatch on another model keeps the same job ID.
