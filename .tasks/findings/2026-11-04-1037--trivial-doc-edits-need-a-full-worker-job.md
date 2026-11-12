---
type: friction
confidence: high
paths: []
---

# Trivial doc edits need a full worker job

## Observation
The orchestrator never edits the repository, so a two-line change (a new glossary file plus one AGENTS.md line, already approved word for word by the owner) took a job file, a dispatch, a worker and a collect. The owner called this unnecessary ceremony. Consider letting the orchestrator make trivial, owner-approved documentation edits itself as a commit on the task branch, with a clear size limit and no code.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
