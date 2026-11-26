---
id: FIX-LOOP-EXITS
covers: [DECISION-ANYTIME, JOB-DROP, ACCEPT-INTEGRATION, LET-GO-REPORT, TRIAGE]
verify:
  - test -f tests/test_fix_loop_exits.py
  - python3 tests/run.py test_fix_loop_exits test_reviews test_review_rounds_setting test_integration_fixes test_run_fixes test_control test_validation_gaps test_worktree_cleanup
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/common.py
  - skills/shape-and-execute/scripts/sae_lib/findings.py
  - skills/shape-and-execute/scripts/sae_lib/planning.py
  - skills/shape-and-execute/scripts/sae_lib/graph.py
  - skills/shape-and-execute/scripts/sae_lib/reviews.py
  - skills/shape-and-execute/scripts/sae_lib/lifecycle.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/control.py
  - skills/shape-and-execute/scripts/sae_lib/cli.py
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - tests/test_fix_loop_exits.py
  - tests/test_reviews.py
  - tests/saetest.py
---

# FIX-LOOP-EXITS: Decision jobs at any time, job drop, accepted integration rounds, let-go report

## Objective
Give the orchestrator and the owner the exits from a fix loop (a decision job for any job,
round or question, `sae job drop`, `sae accept-review`) and list in the final report every
finding that was let go.

## Inputs
- `specs.md` [DECISION-ANYTIME], [JOB-DROP], [ACCEPT-INTEGRATION], [LET-GO-REPORT], [TRIAGE],
  "Technical contract".
- `brief.md` "How": the fixed command names, flags and the `dropped` status. Use them as written.
- `jobs/WRITER-LAUNCH.result.md`: the CLI check and `sae job park` it added to `cmd_dispatch`
  and `planning.py`.
- `findings.py` `cmd_decision_new`, `cmd_log`; `graph.py` `waits_for`, `integration_parked`,
  `requires_changes`; `reviews.py` `apply_review`, `apply_integration_review`,
  `materialize_integration_review`, `verdict_gate`, `stale_gate`, `check_finish_gates`,
  `cmd_merge`; `lifecycle.py` `final_report`; `progress.py` `cmd_dispatch`, status and next.
- `references/modes/execute.md` as `PROMPT-LEAN` left it, and the "Contradictions" section
  of `jobs/PROMPT-TEXT.result.md`.
- `research/PROMPT-LEAN-AUDIT.md` proposal 2, the block "Paste into FIX-LOOP-EXITS Inputs"
  (owner accepted): the changes-required messages print the lead line, a fresh fix command
  (`-FIX-<n>`), the `--let-go` line and the accept line; execute.md now relies on them.

## Scope
- `sae decision new`: `--from` takes any job or review round, `--question` takes a question,
  alone or with `--from`; the job file points to the question, the round, or the parked
  job's decision request. A decision job only advises: it dispatches and collects while a job
  or the task is parked or held. `--from <parked job>` works as today.
- `sae job drop` as in [JOB-DROP]. The group is the target and every fix job that commits to
  its branch, with their review rounds; they all become `dropped`. Naming a fix job alone is
  refused with its target's ID. A running group member blocks the drop. `--fix-of` and the
  merge path (`sae merge`, the merges in `collect` and `finish`) refuse a dropped target, so its
  commits never reach the task branch. Other refusals before any state change (shared checkout; a job outside the group needs
  a dropped job → print the `sae job edit --needs` call); a logged decision. Integration
  review rounds, the final validation and the `finish` gates ignore dropped jobs; `sae status`,
  `sae next` and readiness treat `dropped` as final. Branches and result files stay.
- `sae accept-review <task> <REVIEW-ID> --reason "<why>"`: accepts the last changes-required
  integration round; the integration gate, the final validation and `sae finish` then proceed
  without `--override`. For a job review it refuses and names `sae merge --accept-review`.
- `sae log … decision … --let-go` marks one finding set aside in triage. Both accept commands
  mark their decision as an acceptance; the final report then lists every finding title of
  that review or round (read from its review file) with the acceptance reason. A finding
  already logged on its own keeps its own reason and appears once. The park and changes-required messages in `reviews.py` name
  `sae accept-review` where they offered only `sae finish --override`.
- The final report lists the findings let go with their reasons, the accepted integration
  rounds and the dropped jobs.
- `cmd_dispatch` gate order: you own the merged order. A decision job passes a hold or a park;
  writers still wait; the CLI check of `WRITER-LAUNCH` still comes before any state change.
- Help of the commands you change, and contradictions in your scope from the PROMPT-TEXT result.

- The decision prompt (`prompts.py` `build_prompt`, the "Decision request" pointer) points to
  the parked job's Decision request, the review round's review file, or the question in the
  job file, whichever applies (`research/PROMPT-REVIEW-OPUS.md`, finding 5).

## Boundaries
- The park story and the approach paragraph: `FIX-LOOP-GUIDANCE`. The viewer: `VIEWER-SURFACES`.
- Routing exceptions in the final report: done in `WRITER-LAUNCH`; keep them.
- `sae` does not enforce interaction modes; the prompt text does.

## Expected output
Code, `tests/test_fix_loop_exits.py`. In the result, list the new status, fields and events,
for `VIEWER-SURFACES`.

## Validation
- [ ] Each acceptance item of the five requirements has a test, including: after a drop, the
      integration review and the final validation become ready once the other writers merge;
      a drop in a task without worktrees changes nothing; a decision job runs while the
      integration round limit parks the task.
- [ ] TRIAGE scenario: a let-go decision for one finding of a round appears, with its reason,
      in the final report.
- [ ] An accepted review with several findings lists each title with the reason; in a mixed
      round, a finding logged on its own appears once, with its own reason.
- [ ] A dropped fix's commits do not reach the task branch; `--fix-of` a dropped target is
      refused; a drop with a running member is refused.
- [ ] Merged gate order: a decision job dispatches during a hold, a writer still waits, and a
      missing external CLI leaves `state.json` and `events.jsonl` unchanged.
- [ ] Existing gate tests pass unchanged.
- [ ] Audit proposal 2: a test asserts the four changes-required lines (lead line, fix command
      with a fresh `-FIX-<n>`, `--let-go` line, accept line) for a job and for the integration,
      and a second job round prints `-FIX-2`.
- [ ] A test for each decision-prompt source: a parked job, a review round, a question.
