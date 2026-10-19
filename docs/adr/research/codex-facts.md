# Codex facts

Collected 2026-10-06 by research subagents from the local `codex-cli 0.160.0` (help output,
`codex sandbox` runs without model calls) and the `openai/codex` repository at tag
`rust-v0.160.0` (source and docs). Unverified items are marked UNKNOWN.

## Skills

- Roots: every `<dir>/.agents/skills` from the working folder up to the repository root,
  `~/.agents/skills`, `/etc/codex/skills`, bundled `$CODEX_HOME/skills/.system`. In source only:
  `<project>/.codex/skills` and the deprecated `~/.codex/skills`.
- Invocation: `$name`, `/skills`, or implicitly through `description`. `name` defaults to the
  folder name; unknown frontmatter keys are tolerated.
- `agents/openai.yaml`: UI and harness metadata the model never reads —
  `interface` (display name, short description, icons, default prompt),
  `policy.allow_implicit_invocation: false` (explicit `$skill` only), `dependencies.tools`.

## Subagents

- Stable and on by default (`features.multi_agent`). Tool set depends on the model's
  `multi_agent_version`:
  - v1: `spawn_agent{message, agent_type, fork_context, model, reasoning_effort}`,
    `send_input`, `resume_agent`, `wait_agent`, `close_agent`;
  - v2: `spawn_agent{task_name, message, fork_turns, model, reasoning_effort}`,
    `followup_task`, `send_message`, `wait_agent`, `list_agents`, `interrupt_agent`.
- Parallel cap `agents.max_threads` (v1 default 6, v2 default 4 including the root).
- Model and reasoning effort can be set per spawn.
- The v1 spawn tool text says: do not spawn unless the user, AGENTS.md or a skill asks, and do
  not set `model` unless asked. **The skill must authorize both explicitly.**
- A child copies the parent's working folder, approval policy and permission profile.
  `spawn_agent` has no working-folder argument; a child reaches another folder only through
  the shell `workdir` parameter.
- No per-subagent worktrees; only whole sessions get `--worktree`.

## Headless reviewer

```
codex exec -m <model> -c model_reasoning_effort="high" -s read-only -C /abs/repo \
  -o /abs/review.md --ephemeral "Review …; do not edit."
```

- Reasoning effort only through `-c model_reasoning_effort`; values depend on the model.
- `exec` has no approval flag; approval is hard-coded to never.
- Pass `-s read-only` explicitly (docs disagree about the default).
- `-o` is not written on a failed or interrupted turn: delete the file first, check the exit
  code.
- `-s` and `-C` are not global flags; put them before `resume` or `review`.

## Models

`codex debug models [--bundled]` prints the catalog as JSON. Seen in a local catalog:
gpt-6.1-sol (default), gpt-6-astra, gpt-6-sol, gpt-6-luna, gpt-5.6-sol, gpt-5.6-terra,
gpt-5.6-luna. The "luna" models are the light ones.

## Sandbox and git

- `workspace-write` makes writable: the working folder, `/tmp`, `$TMPDIR` and `writable_roots`.
- Inside writable roots, `.git`, `.agents`, `.codex` and `.aws` stay read-only. So by default
  `git add`, `commit`, `branch`, `tag`, `merge` and `worktree add` fail
  ("Unable to create .git/index.lock"); `git status` works. Tested on macOS.
- Tested fix — a permission profile (selected with `default_permissions`; any `sandbox_mode`
  overrides it):

  ```toml
  [permissions.gitw2]
  extends = ":workspace"
  [permissions.gitw2.filesystem.":workspace_roots"]
  ".git" = "write"
  ".git/hooks" = "read"
  ".git/config" = "read"
  ".codex" = "read"
  ".agents" = "read"
  ".aws" = "read"
  ```

  With it: commit, fast-forward and three-way merge, branch, tag and `worktree add` inside the
  working folder pass; hooks, config and a worktree outside the working folder stay denied.
  (The test profile also made `/tmp` read-only only to isolate the test; that is not needed.)
- A worktree as the session's own working folder (`codex exec -C`) needs both `<main>/.git`
  and `<main>/.git/worktrees/<name>` writable.
- Linux (bubblewrap) uses the same protected names; Linux runtime behavior: UNKNOWN.
- UNKNOWN: the exact syntax for an absolute writable path (the worktree root) inside a
  permission profile; whether a profile can apply to selected sessions only.

## Verified 2026-10-07 for codex-cli 0.160.1 (sae implementation)

Sources: local `codex-cli 0.160.1` (`--help`, `codex debug models`, `codex sandbox`, and `codex exec`
runs with an empty `CODEX_HOME` and no credentials, so no paid model call) and a shallow clone of
`openai/codex` at tag `rust-v0.160.1`. Paths below are relative to `codex-rs/` at that tag.
Nothing in `~/.codex` was modified. Probe dirs were deleted.

### 1. Subagent cap `agents.max_threads`

- `max_threads` is a legacy alias. The canonical key is `agents.max_concurrent_threads_per_session`.
  Both parse to the same field. Source: `config/src/config_toml.rs:730-740` (`#[serde(alias = "max_threads")]`),
  `config/src/key_aliases.rs:20-23`, test `core/src/config/config_tests.rs:9614`.
- Config file: `[agents]` table in `$CODEX_HOME/config.toml`; default `CODEX_HOME` is `~/.codex`
  (`utils/home-dir/src/lib.rs:5-18`). Schema minimum is 1; `0` is rejected
  (`core/src/config/mod.rs:3879-3888`). No maximum exists in the config schema or loader
  (`core/config.schema.json:59-64`). Max allowed value: UNKNOWN beyond that (no clamp found).
- Override: `-c agents.max_threads=10` works. CLI overrides pass through the alias normalizer and a test
  uses exactly that key as a CLI override (`core/src/agent/control_tests.rs:3848-3891`).
  A profile file (`-p name`, see section 5) is another user layer and may contain `[agents]` too.
- Which multi-agent version a session uses (`core/src/config/mod.rs:1586-1613`), in order:
  1. `features.multi_agent_v2 = true` forces V2; `[agents] enabled = false` forces Disabled.
  2. Otherwise the model catalog field `multi_agent_version` of the active model.
  3. Otherwise feature `multi_agent` (default on, `features/src/lib.rs:1330-1335`) gives V1.
  `multi_agent_v2` itself defaults off (`features/src/lib.rs:1336-1341`).
- Bundled catalog (`codex debug models --bundled`): `v2` for gpt-6-astra, gpt-6.1-sol, gpt-6-sol,
  gpt-6-luna, gpt-5.6-sol, gpt-5.6-terra (and hidden gpt-daybreak-*); `v1` for gpt-5.6-luna and
  codex-auto-review; none for gpt-5.5 (falls back to V1 via the `multi_agent` feature).
  A live catalog (`codex debug models`, account-specific) may also list `gpt-reserve` as `v1`.
  So the default `gpt-6.1-sol` runs V2.
- Defaults (`core/src/config/mod.rs:254-255`):
  - V1: `DEFAULT_AGENT_MAX_THREADS = Some(6)` spawned agents. Used when `agents.max_threads` is unset
    (`effective_agent_max_threads`, `mod.rs:1615-1629`).
  - V2: `DEFAULT_MULTI_AGENT_V2_MAX_CONCURRENT_THREADS_PER_SESSION = 4`, which includes the root.
    So the default is 3 subagents. The V2 cap is `total - 1` (`mod.rs:1620-1624`).
- V2 off-by-one trap. `agents.max_threads = N` is converted to a V2 total of `N + 1`
  (`mod.rs:2762-2771`), so N subagents plus the root. `max_threads = 8` gives 8 subagents
  on V2. But `features.multi_agent_v2.max_concurrent_threads_per_session` (the same name, different
  meaning: it counts the root) takes precedence when set (`mod.rs:2763`,
  test `config_tests.rs:12110-12125`: features=5 and agents=9 gives 4 subagents).
- Root is not counted. V1: the registry counter is incremented only in `reserve_spawn_slot` for spawned
  agents and decremented only for non-root agents (`core/src/agent/registry.rs:89-127`). V2: only
  `SessionSource::SubAgent` threads are resident-limited
  (`core/src/agent/control/residency.rs:257-264`).
- Counts open agents, not total spawned per session. A slot is a live (registered) agent.
- What frees a slot:
  - V1: only `close_agent` (`core/src/agent/control/legacy.rs:49`, which calls `shutdown_live_agent`
    at `legacy.rs:9-46` and then `release_spawned_thread`), or an agent thread that died
    (`core/src/agent/control.rs:322-328`). A finished agent still holds its slot until closed.
    Spawn then fails.
  - V2: there is no `close_agent` tool (v2 handlers: followup_task, interrupt_agent, list_agents,
    send_message, spawn, wait; `core/src/tools/handlers/multi_agents_v2/`). When the resident
    limit is reached, the spawn path evicts the least recently used idle subagent (status Completed,
    Errored or Interrupted, no active turn, no pending mailbox items;
    `residency.rs:100-122, 266-273`). So finished subagents free their slot automatically.
    A second V2 limiter caps subagent turns that are running at the same time to the same N
    (`core/src/agent/control/execution.rs:33-60, 80-86`).
- Cap hit: spawn fails with `AgentLimitReached` (`protocol/src/error.rs:112`, text
  `agent thread limit reached`). `collab_spawn_error` returns it to the model as a tool error
  `collab spawn failed: agent thread limit reached`
  (`core/src/tools/handlers/multi_agents_common.rs:66-75`; used by V1 and V2 spawn handlers).
  The session continues; nothing is queued.
- `agents.max_depth` (V1 only; "Ignored by V2" per `config_toml.rs:741`): default `1`
  (`mod.rs:264`). A child at depth 2 cannot spawn. Other `[agents]` keys: `enabled`,
  `default_subagent_model`, `default_subagent_reasoning_effort`, `interrupt_message`.
- Is 10 reasonable for 3 writers plus several read-only agents? Yes.
  - V2 (the default models): 10 means 10 concurrent subagents. Idle finished ones are evicted, so
    it is a ceiling on concurrent work, not on total spawned.
  - V1: 10 counts all unclosed agents. The orchestrator prompt must tell the model to call
    `close_agent` when an agent is done, or finished agents eat slots.
  - Cost note: the TUI warns for Ultra reasoning when the V2 total is 8 or more
    (`tui/src/chatwidget/model_popups.rs:9, 757-768`). That is a hint, not a limit.
  - 10 leaves headroom for 3 writers + 7 readers.

### 2. Env vars set in commands run by the shell tool

All shell tool commands go through the unified-exec runtime (no separate shell runtime exists in
`core/src/tools/runtimes/`). Source: `core/src/unified_exec/process_manager.rs:1445-1454`,
`core/src/exec_env.rs:41-75`.

- `CODEX_THREAD_ID`: always set, id of the current (sub)agent thread. Also injected when
  `shell_environment_policy.include_only` is set (`exec_env.rs:26-31`;
  `protocol/src/shell_environment.rs:7,152`).
- `CODEX_SESSION_ID`: always set, the shared root-session id (same for all subagents).
- `CODEX_VERSION`: always set (`0.160.1` here).
- `CODEX_CI=1`: always set in unified exec (`process_manager.rs:93-104`). Plus `NO_COLOR=1`,
  `TERM=dumb`, `PAGER=cat`, `GIT_PAGER=cat`, `GH_PAGER=cat`, `LANG`/`LC_*=C.UTF-8`.
- `CODEX_PERMISSION_PROFILE`: set to the profile id only when a named permission profile is active;
  informational, children can overwrite it (`exec_env.rs:18-20, 56-72`).
- `CODEX_SANDBOX=seatbelt`: only on macOS and only when the Seatbelt sandbox wraps the command
  (`core/src/sandboxing/mod.rs:176-179`). Not set with `danger-full-access` (no sandbox) and not set
  on Linux in this version (doc comment `core/src/spawn.rs:23-26` says "may change").
- `CODEX_SANDBOX_NETWORK_DISABLED=1`: set whenever the network sandbox policy is restricted, even
  with no Seatbelt (`sandboxing/mod.rs:169-174`, `core/src/spawn.rs:21`).
- Checked by running `codex sandbox -- env`: showed `CODEX_SANDBOX=seatbelt` and
  `CODEX_SANDBOX_NETWORK_DISABLED=1`. That command does not inject thread/session vars
  (`cli/src/debug_sandbox.rs` calls `create_env` without a thread id), so those were verified from
  source only (no model call made).
- Detection recipe: test `CODEX_THREAD_ID` (best, set in every shell-tool command). `CODEX_CI=1` is a
  second signal. Do not use `CODEX_SANDBOX` alone.

### 3. `codex exec` flags

Confirmed by `codex exec --help` and by running them: `-m/--model`, `-c/--config key=value`,
`-s/--sandbox {read-only,workspace-write,danger-full-access}`, `-C/--cd <DIR>`,
`-o/--output-last-message <FILE>`, `--ephemeral`. Also present: `-p/--profile` (profile file, see
section 5), `--add-dir <DIR>`, `--json`, `--output-schema`, `--skip-git-repo-check`,
`--ignore-user-config`, `--ignore-rules`, `--worktree`.

- `-c model_reasoning_effort="low"` is honored: the run header printed `reasoning effort: low`.
- A run with all of `-m -c -s read-only -C --ephemeral -o` printed `approval: never` and
  `sandbox: read-only`.
- `-o` is written only when the turn status is `Completed`
  (`exec/src/event_processor_with_human_output.rs:322, 389`;
  `event_processor_with_jsonl_output.rs:526-541, 559-562, 631-636`). On Failed or Interrupted it is not
  written and any older file stays. If the turn completed with no final message it writes an empty file
  and prints a warning (`exec/src/event_processor.rs:31-40`).
  Probe: unauthenticated run (401) exited 1 and created no `-o` file. Delete the file before the run.
- Exit codes (`exec/src/lib.rs:1221-1323`): `0` on success; `1` when a non-retried error
  notification arrives, or the turn ends Failed or Interrupted, or a request is rejected;
  also `1` for startup errors (bad `-c` override, `CODEX_HOME` not found, execpolicy rules error,
  login restriction; `lib.rs:340, 358, 631, 641`). There is no separate code for quota or auth errors:
  all are `1`. Probe: no credentials gave exit 1 with `401 Unauthorized` text on stderr. Usage-limit text
  comes from `CodexErrorDetails::UsageLimitReached`, also exit 1. Clap argument errors exit 2 (clap
  default, not read in source). sae must parse stderr or `--json` events to tell quota from other errors.
- Stdin: if stdin is piped and a prompt argument is also given, stdin is appended as a `<stdin>` block
  (help text). The CLI printed `Reading additional input from stdin...` even with a prompt. sae should
  pass `stdin=subprocess.DEVNULL`.
- `-s` beats a permission profile: with `-s read-only` plus `-c default_permissions=...` the run used
  `sandbox: read-only` (probe, header). Do not pass `-s` when selecting a profile.
  Source: `core/src/config/mod.rs` `resolve_permission_config_syntax` (sandbox override means Legacy).

### 4. `codex debug models`

- Exists: `codex debug models [--bundled]` ("Render the raw model catalog as JSON").
  Source: `cli/src/main.rs:305-308, 2068-2092`.
- Output: one line of JSON on stdout, object `{"models":[ ... ]}`. Each model has `slug`,
  `display_name`, `visibility` (`list` or `hide`), `default_reasoning_level`,
  `supported_reasoning_levels[{effort,description}]`, `multi_agent_version` (`v1`/`v2`/absent),
  `multi_agent_reasoning_effort`, `context_window`, `priority`, `supported_in_api`, `tool_mode`, and more.
  Parsed with Python: bundled 11 models; a live catalog 10 (includes `gpt-reserve`).
- `--bundled` is fully local: it reads the catalog compiled into the binary (`models-manager/models.json`).
- Without `--bundled` it uses `RefreshStrategy::OnlineIfUncached`: a fresh `models_cache.json`
  (TTL 300 s, `models-manager/src/manager.rs:35`) is used; otherwise it fetches. If fetching fails it
  logs an error and still prints the in-memory catalog with exit 0 (`manager.rs:494-508`).
  Probes: with a bogus proxy and a fresh local cache it printed the 10-model cache, exit 0; with an
  empty `CODEX_HOME` it printed the 11 bundled models, exit 0. The stale-cache plus offline plus
  logged-in case was not run (UNKNOWN beyond the source reading).
- sae should prefer the live call and fall back to `--bundled`; the live list is account-specific.

### 5. Permission profiles and an extra absolute directory

- Filesystem keys must be absolute, or `~/...`, or start with `:` (special paths such as
  `:workspace_roots`). A relative key fails: `filesystem path `../x` must be absolute, use `~/...`, or
  start with `:``. Source: `core/src/config/permission_path.rs:20-33`; probe reproduced the error.
- Values are `"read"`, `"write"` or `"deny"` (`FileSystemAccessMode`); a key may also map to a scoped
  table of sub-paths (`config/src/permissions_toml.rs:224-229`). A profile may also set
  `extends`, `workspace_roots` and `network`.
- Probe results with `codex sandbox -P <name> -C <repo> -- sh -c 'touch ...'` on macOS, dirs under
  `$HOME` (not `/tmp`, which `:workspace` always makes writable):
  - built-in `:workspace`: writes to the repo allowed, to a sibling dir outside it denied;
  - custom profile extending `:workspace` with the absolute path as `"write"`: sibling dir writable too.
- Minimal snippet (verified with `codex sandbox`; works in config.toml or a profile file):

  ```toml
  default_permissions = "sae_writer"
  [permissions.sae_writer]
  extends = ":workspace"
  [permissions.sae_writer.filesystem]
  "/abs/path/to/worktrees-root" = "write"
  ```

- Scope to selected sessions only: yes, three ways.
  1. Profile file. `codex exec -p sae-writer` loads `$CODEX_HOME/sae-writer.config.toml` as a second
     user layer on top of `config.toml` (precedence 21; `config/src/loader/mod.rs:285-330`,
     `config/src/config_layer_source.rs:39-45`). Put the snippet above (including
     `default_permissions`) in that file. Sessions without `-p` are unaffected. Probe: with the file
     present, `codex exec -p sae-w` accepted it (run header showed `workspace-write`);
     `codex sandbox -p sae-w -P sae_w` wrote to the extra dir. The profile name must not clash with a
     legacy `profile = ` or `[profiles.<name>]` in `config.toml` (error text in `loader/mod.rs:312-326`).
  2. Inline `-c` flags, no file needed. Pass the whole table as one inline TOML value:
     `-c default_permissions="sae_writer" -c 'permissions.sae_writer={ extends=":workspace", filesystem={ "/abs/wt"="write" } }'`.
     Probe: `codex sandbox -P sae_w -c "permissions.sae_w={ extends=\":workspace\", filesystem={ \"/abs/dir.with.dots\"=\"write\" } }"`
     made the dir writable. A dotted `-c permissions.x.filesystem."/path"=...` key does NOT work (error
     `data did not match any variant of untagged enum FilesystemPermissionToml`); use the inline table.
     `codex exec` accepted the same flags (header `sandbox: workspace-write [workdir, /tmp, $TMPDIR]`;
     that header does not list extra roots, so the exec-time write was not observed, only the
     identical config path via `codex sandbox`).
  3. `codex exec --add-dir <DIR>` (repeatable, resolved against the cwd) adds extra workspace roots
     (`core/src/config/mod.rs:3455-3457, 3565-3572`). `:workspace_roots` rules, including the
     protected `.git`, `.agents`, `.codex`, `.aws`, apply to those roots as well. Not run end to end.
- Gotchas:
  - `codex sandbox` has no default profile: you must pass `-P` (`:workspace` etc.) or it prints a usage
    error. `codex exec` has no `-P` flag; select a profile via `default_permissions`.
  - If a config defines `[permissions.*]` profiles and no `default_permissions` is set anywhere, loading
    fails: `config defines `[permissions]` profiles but does not set `default_permissions``
    (`core/src/config/mod.rs:3496-3506`; skipped only when a layer sets legacy `sandbox_mode`). So do not
    put profile definitions in the base `config.toml` without also selecting one; keep them in the
    `-p` file or pass them inline.
  - A local config that sets neither `sandbox_mode` nor `default_permissions` is safe with
    either approach.
  - The git protection from the main notes still applies: a writer in a worktree needs
    `<main>/.git` and `<main>/.git/worktrees/<name>` writable too (see "Sandbox and git").
