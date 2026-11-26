# Brief: SaE routing, harness launches and review workflow

## Why
`hard` is overused because simple work that needs judgment has no cheaper route. Writer jobs on
the other harness failed in a sandbox and were rerouted silently. Reviews took several rounds
because fixes patched one instance of a shared rule, and speculative findings became fix jobs
that broke a real startup path. Details: `intent.md` "Problem".

## What
A fourth difficulty `easy`; launch commands for jobs on the other harness, recorded, with a
visible fallback per mode; project stakes that every agent reads and that reviewers grade
against; findings that separate the expected outcome from the suggested fix; fix loops with an
approach check, a plain story at the limit, decision jobs at any time, `sae job drop` and an
accepted integration round. Requirements: `specs.md` "Requirements".

## How (high level)
- All prompt text (SKILL.md, `references/`, `templates/`, and the [PROMPT-SAE] texts that `sae`
  prints into prompts) changes in `PROMPT-TEXT` only. A hold after it lets the owner read the diff.
- The [PROMPT-SAE] texts are named constants in `scripts/sae_lib/prompts.py`, written by
  `PROMPT-TEXT`. Later jobs call them; they do not reword them.
- The backend jobs expose data and functions; `VIEWER-SURFACES` shows them, except the `easy`
  column, which `EASY-DIFFICULTY` adds to the viewer itself.
- Interfaces fixed by this plan (the prompt text names them before the code exists):
  - `sae accept-review <task> <REVIEW-ID> --reason "<why>"`: accepts the last changes-required
    integration round. Job reviews keep `sae merge <task> <ID> --accept-review "<why>"`.
  - `sae log <task> decision "<finding>: <reason>" --job <REVIEW-ID> --let-go`: one finding set
    aside in triage. An accepted review or round lets go every finding in it: the final report
    lists each finding title with the acceptance reason.
  - `sae job drop <task> <ID> --reason "<why>"`; the job status `dropped` is final. The group
    is the target and every fix job that commits to its branch.
  - `sae job park <task> <ID> --reason "harness fallback: …"`: parks a pending or running job
    that waits for the owner's yes to a harness fallback; it frees its writer slot. The yes runs
    the printed fallback command with `--resume`.
  - The printed fallback command carries the requested route in its `--reason`
    (`harness fallback: requested <harness> · <model> · <effort>; <why>`); the routing exception
    record reads it from there.
  - `sae decision new <task> --from <any job or review round>` and/or `--question "<text>"`.
  - `sae status` prints `stakes: <source>` or `stakes: not set`, with the profile path to write
    them to.
- One stakes location: `.tasks/repo/profile.md` of the main worktree (`git worktree list`, first
  entry), for shaping, status, dispatch and the viewer, also when the task was created from a
  linked worktree.

## Invariants
- Configurations without an `easy` cell stay valid; `sae` writes no cell and no tier.
- No `sae` command and no SaE instruction writes to AGENTS.md or CLAUDE.md.
- Task records hold no private paths: launch records use `<prompt>` and `<workdir>`.
- Review COMMANDs stay as they are, apart from the stakes line in their prompt.
- Read-only commands take no lock and write nothing (`scripts/sae_lib/AGENTS.md`).

## Domain terms
Stakes, beyond stakes, fix round, approach proposal, routing exception, dropped job: as in
`specs.md` "Domain language". Difficulties are words; `L1`–`L4` are model tiers.

## Constraints
- `sae` stays standard-library Python 3.9+, with no model names in its code.
- New logic goes into a module of its own area; hot files (`progress.py`, `prompts.py`,
  `reviews.py`, `lifecycle.py`) get call sites. Parallel jobs collide in big shared hunks.
- Code jobs do not edit prompt text files. A contradiction you find there: say so in your
  result. CLI help of the commands you change is yours; read the "Contradictions" section of
  `jobs/PROMPT-TEXT.result.md` for items in your scope.
- The repository is public: anonymous examples, no local paths (AGENTS.md).

## Architecture facts
- CLI: `scripts/sae.py` → `scripts/sae_lib/` (one module per area, under about 1,000 lines).
- Jobs reach the other harness only through `sae job override --harness`, a `--harness` or
  `--provider` flag, or the review provider. Routing itself keeps writers on the orchestrator.
- Viewer: `assets/viewer/` served by `scripts/sae_lib/server.py`; see `assets/viewer/README.md`.

## Validation
Smoke and full suite: `.tasks/repo/profile.md`. Every job adds tests for what it changes. Tests
never need a real `codex` or `claude` CLI: put fake ones on PATH. Only `FINAL-VALIDATION` runs
the full suite.
