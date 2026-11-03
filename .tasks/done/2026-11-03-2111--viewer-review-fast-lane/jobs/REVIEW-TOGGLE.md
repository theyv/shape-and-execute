---
id: REVIEW-TOGGLE
covers: [JOB-REVIEW-CONTROL]
verify:
  - python3 tests/run.py test_viewer_server
  - python3 tests/run.py test_reviews
  - python3 tests/run.py test_graph_cards
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/planning.py
  - skills/shape-and-execute/scripts/sae_lib/reviews.py
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/scripts/sae_lib/control.py
  - skills/shape-and-execute/assets/viewer/**
  - tests/test_review_flag.py
  - tests/test_reviews.py
  - tests/test_viewer_server.py
  - tests/test_graph_cards.py
  - tests/test_control.py
  - tests/test_sae.py
---

# REVIEW-TOGGLE: Change a job's review flag in the viewer and on a running job

## Objective
The owner turns a writer job's review flag on or off, pending or running, in the viewer or the
CLI, until its result is collected.

## Inputs
- Spec: [JOB-REVIEW-CONTROL] and [DECISION-RUNNING-FLAG] in `specs.md`.
- CLI: `cmd_job_edit` in `sae_lib/planning.py` (refuses non-pending jobs today).
- Collection: `after_writer_done`, `review_due` and `review_mark` in `sae_lib/reviews.py`.
- Viewer writes: `WRITE_ROUTES`, `route_hold` and `run_write` in `sae_lib/server.py`; the hold
  button (`holdBtn`) and the review marks in `assets/viewer/task-views.js` are the pattern.
- Next-step card notices of changes: `sae_lib/control.py`.

## Scope
- `sae job edit --review | --no-review` also works on a running writer job; every other field of
  a running job still refuses. Done, failed and non-writer jobs refuse with a clear message.
- Check that nothing reads the flag before collection in a way that the change would bypass
  (planned reviews, cards). `sae collect` uses the flag as it is at collection.
- A viewer control on pending and running writer jobs, through a new write route that runs
  `sae job edit`. During execution `--reason` is required: the viewer sends a fixed reason
  (for example "changed in the viewer"); the event records the viewer origin.
- The control shows when the flag has no effect (`all-jobs`, or job reviews off) and never
  changes review points.
- Tests (a new `tests/test_review_flag.py` where it fits) for: running job on and off, refusals, collection after a change, the new route.

## Boundaries
- No cancel of a running review job (a separate backlog item).
- No change to review points or to the next-step card format beyond listing the change.

## Expected output
Commits with CLI, server and viewer changes and their tests.

## Validation
- [ ] The control is reachable by keyboard and has an accessible name.
