---
type: defect
confidence: medium
paths: []
---

# Completed review cannot be dispatched again

## Observation
Another agent reported that sae instructs it to use --resume to rerun a completed review, but then rejects --resume. The agent ran a second review manually with the same prompt, saved it as reviews/REVIEW-SPEC-2.md, and noted the workaround in the task. Exact commands and errors were not provided; reproduce and verify the expected behavior.

## Evidence

Reported by another agent. The agent used the same review prompt for a manual second run and
recorded the workaround in the task. The task ID and exact command output were not supplied.

## Cost

An agent cannot rerun the review through the suggested CLI path and must work around it manually.

## Suggestion

Reproduce the conflicting guidance and rejection. Make rerunning a completed review possible,
or provide clear, consistent guidance for the supported way to request another review.
