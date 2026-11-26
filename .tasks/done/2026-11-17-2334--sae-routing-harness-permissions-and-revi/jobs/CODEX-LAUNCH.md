---
id: CODEX-LAUNCH
---

# CODEX-LAUNCH: Codex launch permissions for SaE jobs

## Objective
Settle the exact `codex exec` launch that `sae dispatch` must print for a Codex writer job, how
its permissions come from a SaE-owned profile, and how SaE can check the effective permissions
before dispatch. Decisions that wait on it: the COMMAND for cross-harness writer jobs, what the
viewer may write, and the pre-dispatch capability check.

## Questions
1. `codex exec -p <name>` layers `$CODEX_HOME/<name>.config.toml` on the base config (from
   `codex exec --help`, codex-cli 0.169.0). Do `default_permissions`, `[permissions.<name>]`
   (with `extends`, filesystem entries for `.git` and an extra root) and `[agents] max_threads`
   take effect from such a profile file, in `codex exec` and in an interactive `codex -p` session?
   Does `-s/--sandbox` on the same command line override or conflict with the profile's
   permissions? What wins when both are present?
2. Is the profile in `sae setup snippets` (see `skills/shape-and-execute/scripts/sae_lib/setup_mode.py`,
   `cmd_setup_snippets`) valid for this Codex version? Name every key that is wrong, unknown or
   deprecated, and give the corrected profile.
3. Git writes: what must be writable so a Codex worker in a linked worktree (worktree under the
   SaE worktree root, git common dir in the main checkout) can `git add`, `git commit` and
   `git merge`? Which paths stay safely read-only (hooks, config)?
4. Local sockets, ports and network inside the sandbox on macOS (seatbelt) and Linux (landlock
   or bubblewrap): can a verify command open a Unix domain socket (e.g. the tsx IPC socket
   under the temp dir), bind and connect to 127.0.0.1 ports, and reach the internet? Which
   config keys allow each (e.g. `sandbox_workspace_write.network_access`, permission-profile
   network entries)? Are Unix sockets covered by the network switch?
5. Can the effective permissions be tested without a model call? For example `codex sandbox`
   (macOS/Linux) or `codex debug ...` running a shell command under the same policy that
   `codex exec -p <name>` would use. Give the exact commands for a probe that: commits in a
   throwaway linked worktree, binds a 127.0.0.1 port, opens a Unix socket in the temp dir, and
   writes in the worktree root. State what such a probe cannot prove.
6. Subagent cap: where is `agents.max_threads` read from, and does a profile file override it?
7. Web search and network for a research worker launched with `codex exec`: which flag or
   config key enables web search, and does it need sandbox network?
8. Machine-readable output: with `--json`, which events carry the effective sandbox or
   permission policy, so `sae` could record what actually ran?

## Already known
- `codex exec --help` (0.169.0) lists `-p/--profile` ("Layer $CODEX_HOME/<name>.config.toml on
  top of the base user config"), `-s/--sandbox` (read-only, workspace-write, danger-full-access),
  `--add-dir`, `-c key=value`, `--ignore-user-config`, `--json`, `-o`, `--ephemeral`.
- Today `sae dispatch` prints a launch COMMAND only for a review in the other harness
  (`prompts.py`, `external_review_command`: `codex exec ... -s read-only -C <root> -o <result>
  --ephemeral --json`). A writer job routed to Codex from a Claude orchestrator gets only a
  PROMPT. In one incident the orchestrator used `codex exec -s workspace-write`; the worker could
  not commit and could not open a tsx IPC socket.
- No `*.config.toml` profile exists in this machine's `$CODEX_HOME` yet. Do not create one
  there; use a temporary `CODEX_HOME` copy if you need to experiment.

## Limits
- Primary sources: the Codex source code (github.com/openai/codex) at the tag that matches the
  installed version, official docs, and local experiments with the installed CLI. Mark each
  claim `[primary]` or `[secondary]` and say which version a claim holds for.
- Do not change the user's Codex or Claude configuration. Experiments go to the scratch folder
  of this job or a temporary `CODEX_HOME`. Do not run a model call except, at most, one cheap
  check that needs it; say so in the report.
- You run inside `codex exec -s workspace-write` with network on. A nested sandbox experiment
  (e.g. `codex sandbox` inside your sandbox) may fail or give misleading results. When it does,
  say so, and list the exact commands the main session should run outside a sandbox, with the
  expected output for each outcome.
- Do not design SaE changes. Report facts, options and tradeoffs.

## Follow-up questions
