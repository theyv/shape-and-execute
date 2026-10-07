# sae command reference

    python3 <SKILL_DIR>/scripts/sae.py <command> [args]      # every command has --help

`<task>` is the task ID or a unique part of it (usually the slug). Add `--json` to any read
command for structured output.

Exit codes: `0` ok · `1` usage or precondition error · `2` user config missing → offer setup
mode · `3` gate refused (lint errors, approval or review missing) · `4` git problem (dirty
tree, merge conflict, worktree setup) · `5` re-run verify failed → resume the worker.

## Task

| Command | Use |
|---|---|
| `new "<title>" [--slug s] [--harness claude\|codex] [--from <backlog-file>]` | Create a task. Prints its ID. `--from` turns a backlog item into the task's `intent.md` and removes it from the backlog. |
| `new "<title>" --backlog [--slug s] [--source <task>]` | Create a backlog item for deferred work. Prints its path. |
| `status [<task>]` | Where things are. The first command after any context reset. Without a task: all tasks, the backlog, open findings. |
| `set <task> key=value ...` | Change settings: `interaction`, `research`, `planning`, `execution`, `review-level`, `review` (points `spec`, `plan`, `selected-jobs` or `all-jobs`, `integration`; or `off`), `reviewer` (`claude` \| `codex`), `max-verify-failures` (only when the user asks). |
| `approve <task> spec` | Spec gate: `shaping` → `planning`. Runs `check` first; refuses while a due `REVIEW-SPEC` is not collected. |
| `approve <task> plan` | Plan gate. Runs `check` first. |
| `start <task> [--allow-dirty]` | Begin execution: task branch, layout, first `next`. Commits the removal of a picked-up backlog item. |
| `finish <task> [--with-open]` | Merge the rest, remove worktrees, commit the task record, print the final report. |
| `abandon <task> --reason "..."` | Stop a task. |
| `view [<task>] [--open]` | Render the viewer and print (or open) its URL. |

## Graph

| Command | Use |
|---|---|
| `job add <task> <ID> --kind <kind> [--needs A,B] [--difficulty mechanical\|normal\|hard] [--review] [--final] [--fix-of <ID>] [--reason "..."]` | Add a job and scaffold its file. `--reason` is required during execution. |
| `job edit <task> <ID> [--needs ...] [--difficulty ...] [--review\|--no-review] [--reason "..."]` | Change a pending job. |
| `job remove <task> <ID> --reason "..."` | Drop a pending job. |
| `check <task>` | In shaping: lint requirement IDs, and add `REVIEW-SPEC` when it is due. Later: lint the graph and requirement coverage, and add `REVIEW-PLAN` when it is due. |

Kinds: `research`, `planning`, `implementation`, `integration`, `validation`, `review`,
`decision`.

## Execution

| Command | Use |
|---|---|
| `next <task>` | Reminder lines, then running, parked, ready (with model and workspace) and blocked jobs. |
| `dispatch <task> <ID> [--provider claude\|codex] [--resume --reason "..."]` | Prepare the workspace. Prints MODEL and PROMPT, or a COMMAND for a review in the other harness. |
| `collect <task> <ID> [--tokens N] [--duration-s N] [--agent-ref <ref>]` | Read the result, re-run `verify`, then merge or add the review. |
| `merge <task> <ID> [--accept-review "..."]` | Merge now; accept despite a review. |
| `decision new <task> --from <ID>` | Create a decision job for a parked job. |
| `log <task> decision\|amendment\|note "<summary>" [--by human\|agent\|joint] [--class <class>] [--id <AMEND-ID>] [--job <ID>] [--file <path>]` | Record what was decided. |

## Findings

| Command | Use |
|---|---|
| `finding new "<title>" --type friction\|defect\|follow-up --confidence high\|medium\|low [--source <task>/<ID>] [--paths a,b]` | File a finding. |
| `finding close <file> --outcome "..."` | Close it during triage: `fixed in <task-id>`, `moved to backlog/<file>`, `rejected: <reason>`, `duplicate of <finding>`. |

## Setup

| Command | Use |
|---|---|
| `setup show` | Current config, or a proposal skeleton with detected facts. |
| `setup save` | Validate config JSON from stdin and write it (with a backup). |
| `setup snippets` | Harness permission snippets for the configured worktree root. |
| `doctor [--repo]` | Check everything; prints a fix for each problem. |
