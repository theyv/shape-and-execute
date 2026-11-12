---
type: friction
confidence: high
paths: [skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/scripts/sae_lib/prompts.py, skills/shape-and-execute/references/modes/execute.md]
---

# Cross-harness override of a writer job prints a PROMPT, not a COMMAND

## Observation
The user asked for implementation jobs on a Codex model while a Claude session orchestrates. `sae job override <task> <JOB> --harness codex` accepts this for an implementation job. But `sae dispatch` builds an external COMMAND only for review jobs. For an implementation or validation job on the other harness it prints a plain PROMPT, as if the orchestrator could spawn it as its own subagent. A Claude orchestrator cannot spawn a subagent on a Codex model, and the reverse is also true. The orchestrator concluded that the setup was not possible and asked the user to move the orchestration to the other harness. The user expected sae to run any job on any harness.

## Evidence
- `sae_lib/progress.py`, dispatch: `external = job["kind"] == "review" and model["harness"] != task.info.get("orchestrator_harness")`. Only reviews get a COMMAND and an IF IT FAILS line.
- `sae_lib/prompts.py`, `external_review_command`: the Codex command is `-s read-only`; no variant exists for a job that writes and commits.
- `sae job override --help`: "Run one job, or its review, on another harness, model or effort." No limit to reviews is stated.
- `references/modes/execute.md`, Loop step 2: "When the output is a COMMAND (a review in the other harness), run it in the background". It does not say what to do with a PROMPT for a model of the other harness.

## Cost
The orchestrator stopped and asked a needless question; the user had to push back. To continue, the orchestrator must build the external command by hand: model, effort, a sandbox that allows writes, extra write access to the repository's `.git` folder so that commits in a linked worktree work, and the result file. sae records no tokens for such a job, because no COMMAND output log exists. Each orchestrator does this differently, so it is fragile.

## Suggestion
Make `external` true for every job whose resolved harness differs from the orchestrator harness. For writer kinds, print a COMMAND that runs in the job workdir with write access (Codex: `-s workspace-write -C <workdir> --add-dir <git common dir>`; Claude: a permission mode and tools that allow edits and commits), keeps the JSON output for token accounting, and has an IF IT FAILS line. Update execute.md Loop step 2 to say "a job in the other harness", not "a review". If writer jobs on the other harness stay unsupported, `job override` should refuse them with a clear message instead of accepting them.

Also document the option in the README: one harness can orchestrate while jobs run on the other (for example a Claude orchestrator with Codex implementation jobs and Claude reviews), and how to set it up with `sae job override` or routing. Users do not expect that this is possible.
