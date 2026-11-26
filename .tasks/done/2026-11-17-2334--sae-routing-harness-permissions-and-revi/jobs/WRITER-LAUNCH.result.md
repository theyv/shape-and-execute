---
status: done
summary: Every job on the other harness gets a recorded COMMAND (bypass for non-review, read-only for reviews), a missing-CLI refusal before any change, the per-mode fallback rule, routing exceptions, sae job park and a status bypass line.
validation: pass
changes: made
resolved: []
---

# Result: WRITER-LAUNCH

Commit `a82fc94`. New logic is in `scripts/sae_lib/launch.py` (323 lines). The hot files only have call sites: `progress.py` (`cmd_dispatch`, status), `prompts.py` (`external_review_command` now calls `launch_command`), `reviews.py` (collect reads the tokens), `lifecycle.py` (final report section; finish also removes harness logs from `research/` and `decisions/`) and `planning.py` (registers `job park`).

## Validation evidence
- `test -f tests/test_writer_launch.py`: ok.
- `python3 tests/run.py test_writer_launch test_external_review_tokens test_record_privacy test_dispatch_pointers test_session_tokens`: 58 tests OK.
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Neighbouring modules (routing, sae, output_plain, control, task_worktree, reviews, integration_fixes, run_fixes, review_flag, retired_terms, sae_ask, resolves, model_config, findings, wait_signals, adr_rules, easy_difficulty, levels_premium): 211 tests OK. I did not run the full suite.
- `tests/test_writer_launch.py` (18 tests, fake `codex`/`claude` that log argv and cwd) covers:
  - WRITER-COMMAND in both directions: `codex exec … --dangerously-bypass-approvals-and-sandbox -C <workdir>`, with no `-s` and no `-o`. `cd <workdir> && claude -p … --permission-mode bypassPermissions`. The COMMAND runs and collect reads the tokens without `--tokens`, then deletes the output. The review COMMAND matches the old format exactly.
  - LAUNCH-RECORD: the exact placeholder commands and `bypass requested` / `read-only requested`, in state and in the `job.dispatched` event.
  - NO-SANDBOX-VISIBLE: the `Bypass:` line, from an override or a past bypass attempt.
  - HARNESS-FALLBACK:
    - A missing CLI leaves `state.json` and `events.jsonl` byte-identical and creates no worktree. Covered for a pending job in both directions, for a due REVIEW-SPEC (not added) and for `--resume` of a done research job.
    - One test per branch asserts the printed text: review; full-auto; another mode with a pending job; another mode with a running job after a failed COMMAND; a done research job with `--resume`.
    - With one writer slot: park after a failed COMMAND and after a missing CLI. The other writer then dispatches, and the owner's yes resumes the parked job on claude.
    - A route requested only by `--harness`: the exception names `codex · core · low`, and the next dispatch without flags has no exception. With an override, the route returns to codex after the fallback.
    - The final report lists the routing exception.
- `test_record_privacy.test_launch_records_hold_no_path_and_no_prompt_text`: the launch and exception records hold no path, and the prompt text is in neither `state.json` nor `events.jsonl`.

### For VIEWER-SURFACES
- `state.json`, per attempt:
  - `launch`: `{harness, model, effort, command, request}`. `command` uses the placeholders `<prompt>`, `<workdir>`, `<task-folder>`, `<output>` and `<result>`. `request` is `"bypass requested"` or `"read-only requested"`. It is present only on COMMAND attempts.
  - `routing_exception`: `{requested: {harness, model, effort}, actual: {harness, model, effort}, reason}`.
- A parked job: `status: "parked"`, `summary` = the park reason (`parked_reason` shows it).
- Events:
  - `job.dispatched` gains `launch` on COMMAND attempts.
  - New `routing.exception {job, attempt, requested, actual, reason}`.
  - New `job.parked {job, was, attempt, reason, by}`.
- Functions in `launch.py`:
  - `bypass_line(task)` gives the bypass line, or None. It is also in `sae status --json` as `bypass`.
  - `bypass_jobs(task)`.
  - `routing_exceptions(task)`.
  - `exception_text(exception)`.
  - `BYPASS_REQUESTED`, `READ_ONLY_REQUESTED`.
- `sae dispatch --json` for a COMMAND job adds `command`, `how_to_run`, `if_it_fails`, `rule` and `launch`. Every dispatch adds `routing_exception`.

## Decisions taken
- [agent] The recorded command also replaces the output, result and task-folder paths. The spec names only `<prompt>` and `<workdir>`, but these paths are private too.
- [agent] Claude writer COMMANDs add `--add-dir <task folder>`. The worker writes its result outside the job worktree it starts in.
- [agent] A dispatch flag on another harness than routing chose also records a routing exception, with routing's route as `requested`. This follows the domain definition. A fallback reads the requested route from its `--reason`. The review IF IT FAILS line now uses the fixed reason format too, so the review fallback records its exception.
- [agent] The missing-CLI refusal is exit 1. In a mode other than full-auto, the rule prints the park, ask, log and resume steps, with the exact `--resume` command. For a done, failed or already parked job it prints "The job stays <status>; do not park it." The question in `sae ask` is pre-filled.
- [agent] `sae job park` takes only pending or running non-review jobs. Reviews fall back in every mode, so they are never parked for this.
- [agent] Test sandboxes put failing fake `codex`/`claude` on the PATH (`saetest.write_fake_clis`). Without them, every existing test that dispatches a cross-harness review would hit the new refusal. `Sandbox.without_cli(name)` removes one and skips the test if a real CLI is on the test PATH.
- [agent] Writer COMMANDs do not delete an old result file. Only the output is cleaned, as for jobs run on the orchestrator.

## Risks
- The `claude -p … --add-dir` and `codex exec --dangerously-bypass-approvals-and-sandbox` flags come from the research reports. Only fakes ran them here.
- `FIX-LOOP-EXITS` reorders the gates in `cmd_dispatch`. Both CLI checks must stay before `add_due_review`, `prepare_workspace` and the attempt append.

## Findings filed
- `.tasks/findings/2026-11-20-1926--sae-doctor-says-the-other-harness-cli-is.md` (doctor text still says "only for cross-model review").
- `.tasks/findings/2026-11-20-1926--codex-commands-fail-outside-a-git-reposi.md` (no `--skip-git-repo-check` for no-git tasks; unverified).
