---
id: WRITER-LAUNCH
covers: [WRITER-COMMAND, LAUNCH-RECORD, NO-SANDBOX-VISIBLE, HARNESS-FALLBACK]
verify:
  - test -f tests/test_writer_launch.py
  - python3 tests/run.py test_writer_launch test_external_review_tokens test_record_privacy test_dispatch_pointers test_session_tokens
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/launch.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - skills/shape-and-execute/scripts/sae_lib/reviews.py
  - skills/shape-and-execute/scripts/sae_lib/routing.py
  - skills/shape-and-execute/scripts/sae_lib/lifecycle.py
  - skills/shape-and-execute/scripts/sae_lib/control.py
  - skills/shape-and-execute/scripts/sae_lib/config.py
  - skills/shape-and-execute/scripts/sae_lib/planning.py
  - tests/test_writer_launch.py
  - tests/test_external_review_tokens.py
  - tests/test_record_privacy.py
  - tests/saetest.py
---

# WRITER-LAUNCH: Launch commands, launch records and the fallback for the other harness

## Objective
Give every non-review job routed to the other harness a recorded launch COMMAND without a
sandbox, and a fallback that `sae` states per interaction mode and records as a routing exception.

## Inputs
- `specs.md` [WRITER-COMMAND], [LAUNCH-RECORD], [NO-SANDBOX-VISIBLE], [HARNESS-FALLBACK],
  [DECISION-YOLO-WRITERS], [DECISION-FALLBACK-BY-MODE].
- `research/CODEX-LAUNCH.md`, `research/CLAUDE-LAUNCH.md` in the task folder: flags and output.
- `brief.md` "Invariants" and "Architecture facts".
- `progress.py` `cmd_dispatch`; `prompts.py` `build_prompt`, `external_review_command`,
  `review_output_file`, `review_output_tokens`; `reviews.py` `cmd_collect`; `lifecycle.py`
  `final_report`.
- `research/PROMPT-LEAN-AUDIT.md` proposal 1, the block "Paste into WRITER-LAUNCH Inputs"
  (owner accepted): the whole fallback rule lives in `sae dispatch` output, printed only for
  the case at hand, and the missing-CLI check runs before a `--resume` appends its attempt.
  `PROMPT-LEAN` cut the rule from the mode files; they now say "follow what it prints".
- The "Contradictions" section of `jobs/PROMPT-TEXT.result.md`.

## Scope
- The COMMAND for implementation, integration, validation, research and decision jobs on the
  other harness: workdir, routed model and effort, bypass flag, machine-readable output kept
  for `sae collect`, which reads its tokens without `--tokens`. The worker still writes its own
  result file. Review COMMANDs stay as they are.
- Before it prints a COMMAND, `sae dispatch` checks that the other harness's CLI is on the PATH.
  Missing: refuse before any state change (also before a due review is added) and print the
  fallback command, which works for a pending job and for a due spec or plan review.
- The IF IT FAILS line of a non-review COMMAND resumes the job on the orchestrator's harness.
  With both, print the rule: a review falls back in every mode; any other job only in
  `full-auto`; in the other modes the orchestrator parks it with `sae job park`, independent
  work continues, and it asks the owner with `sae ask`; the owner's yes runs the fallback
  command with `--resume`.
- `sae job park <task> <ID> --reason "harness fallback: …"` (brief "How"): parks a pending
  job, or a running one whose COMMAND failed (its attempt ends). A parked job leaves the ready
  queue and frees its writer slot; `sae status` shows the reason.
- The requested route travels in the printed fallback command's `--reason`, in the fixed
  format of brief "How". The routing exception reads the requested route from there, so a
  route requested only by a dispatch flag survives the refusal.
- Each COMMAND attempt records its launch in `state.json`: harness, model, effort, the command
  with `<prompt>` and `<workdir>` placeholders, and `bypass requested` or `read-only requested`.
- Every dispatch on another harness than routing chose (a fallback, including the existing
  review fallback) records a routing exception: requested route, actual route, reason. The next
  dispatch uses routing again. The final report lists the exceptions.
- `sae status` shows one line when the task sends any non-review job to the other harness:
  such jobs start with a bypass request.
- Help of `dispatch` and `collect`, and contradictions in your scope from the PROMPT-TEXT result.

## Boundaries
- No sandboxed launch, no capability probe, no permission settings: backlog.
- The viewer shows the records and the exception mark: `VIEWER-SURFACES`.
- Prompt text files: `PROMPT-TEXT`, `PROMPT-LEAN`.

## Expected output
Code, mostly in a module of its own, and `tests/test_writer_launch.py`. In the result, list the
`state.json` fields and events you added, and the function that gives the bypass line, for
`VIEWER-SURFACES`.

## Validation
- [ ] Tests with fake `codex` and `claude` executables on PATH cover each acceptance item of the
      four requirements, in both orchestrator directions.
- [ ] A missing CLI leaves `state.json` and `events.jsonl` unchanged.
- [ ] With one writer slot and a second independent writer: after a missing-CLI refusal and
      after a failed COMMAND, `sae job park` frees the slot, the other writer dispatches, and
      the owner's yes resumes the parked job on the orchestrator's harness.
- [ ] A route requested only by `--harness`: refusal, fallback, the exception record names the
      flag's route as requested, and the next ordinary dispatch uses routing again.
- [ ] No absolute path and no prompt text reaches `state.json` or the events
      (`test_record_privacy`).
- [ ] Audit proposal 1: every COMMAND prints the how-to-run line (in the background, in a
      shell, not as a subagent, no `--tokens`); one test per fallback branch asserts the printed
      text (review; `full-auto`; another mode with a pending job; another mode with a running
      job after a failed COMMAND; a done research or planning job with `--resume`).
