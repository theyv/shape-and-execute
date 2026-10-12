# Claude Code facts

Collected 2026-10-06 for Claude Code 2.1.290 by a research subagent (official docs at
code.claude.com and the local CLI), plus observations from the design session itself and one
fact supplied by the owner. Unverified items are marked UNKNOWN.

| Topic | Fact | Source |
|---|---|---|
| Subagent worktree isolation | Based on the repository's **default branch**, not the parent's HEAD, unless `worktree.baseRef: "head"` is set. Worktrees in `.claude/worktrees/<name>/`, branch `worktree-<name>`. Removed when unchanged; changes stay uncommitted. | docs: worktrees |
| Gitignored files in worktrees | `.worktreeinclude` (gitignore syntax) copies matching ignored files, such as `.env`, into new worktrees. | docs: worktrees |
| Nested subagents | UNKNOWN: the docs do not say whether a subagent can spawn subagents. | — |
| Resuming a subagent | `SendMessage` to the agent ID continues it with full context. Lifetime after a session restart: UNKNOWN. | docs: sub-agents |
| Model per dispatch | The Agent tool takes a `model` (aliases such as sonnet, opus, haiku, fable, or full IDs in agent frontmatter). Reasoning effort comes from the agent definition; per-dispatch effort: UNKNOWN, treated as not available. | docs: sub-agents; tool schema in the session |
| Completion notifications | Background subagents notify the parent on completion, with usage (`subagent_tokens`, `tool_uses`, `duration_ms`). | observed in the session |
| Headless reviewer | `claude -p "<prompt>" --model <m> --permission-mode dontAsk --allowedTools "<read-only list>" --output-format json`. Keep the allowlist strictly read-only (for example `Bash(git diff:*)`, not `Bash(git *)`). | docs: headless (flags to re-verify) |
| Skill folder at runtime | `${CLAUDE_SKILL_DIR}`. | docs: skills |
| Explicit invocation only | `disable-model-invocation: true` in `SKILL.md` frontmatter. | the owner |
| Default commit behavior | The harness tells the model to commit or push only when the user asks; the skill must authorize commits on task and job branches explicitly. | session system instructions |
| Sandbox | Off by default; covers Bash only. Writes allowed: working folder, temp, `--add-dir` / `additionalDirectories`, `allowWrite`. `.git/hooks` and `.git/config` denied. Subagents share the sandbox config and start in the parent's folder (`cd` does not persist). | docs: sandboxing, sub-agents |
| Editing outside the working folder | Prompts unless the folder is in `additionalDirectories` (or permissions are bypassed). `acceptEdits` does not auto-approve `git commit`, `merge` or `worktree add`; allow rules are needed. | docs: permissions, permission modes |

Consequences for the design: `sae` creates worktrees itself from the task branch; the worktree
root goes into `additionalDirectories` at setup; dispatch prompts give absolute paths and tell
workers to run every command in their workdir.

## Verified 2026-10-07 for Claude Code 2.1.292 (sae implementation)

Sources: `claude --help` (2.1.292), docs at code.claude.com/docs/en (headless, permission-modes, permissions, sub-agents, env-vars, skills), strings in the local binary, the env of the Bash tool in this session, and two cheap `claude -p` probes. "Probe" means run locally on 2026-10-07.

### 1. Headless read-only reviewer

| Fact | Source |
|---|---|
| `--permission-mode` choices in 2.1.292: `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`. `dontAsk` is real. | `claude --help` |
| `dontAsk` denies every tool call that would otherwise prompt. It does not wait for input. Still allowed: reads in the working dirs, the built-in read-only Bash command set, calls matched by `--allowedTools` or `permissions.allow`, and calls approved by a PreToolUse hook. | docs: headless (Auto-approve tools), permission-modes (dontAsk section) |
| Probe: `claude -p ... --model haiku --permission-mode dontAsk --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*),Bash(git show:*)"`. The prompt asked for `git log -1 --oneline` and `touch <file>`. Result: git log ran, touch was denied, the file was not created. Exit code 0. | probe |
| The legacy `Bash(cmd:*)` suffix is valid and equals `Bash(cmd *)`. The docs now write the space form. `:*` is recognised only at the end of a pattern. The probe used `:*` and it worked. | docs: permissions (Bash rules); probe |
| `--allowedTools` takes a comma- or space-separated list. | `claude --help` |
| `--model` accepts an alias (`fable`, `opus`, `sonnet`, `haiku`) or a full model name. `--model haiku` ran in the probe. | `claude --help`; probe |
| Default `--output-format text`: stdout held only the final message (`LOG=ok TOUCH=denied`). stderr was empty. | probe; docs: headless |
| `--output-format json` returns one object with `result`, `session_id`, usage and `total_cost_usd`. `stream-json` ends with a `result` message. | docs: headless |
| Exit code: 0 on success, non-zero when the run fails. An invalid flag is reported on stderr before the run starts. A failure inside the run (for example missing auth) is printed as the result on stdout. | docs: headless |
| Probe: `ANTHROPIC_API_KEY=<invalid> claude --bare -p hi --model haiku`. stdout: `Failed to authenticate. API Error: 401 API key is invalid.` stderr empty. Exit 1. The call did not return within 180 s (retries), so the orchestrator needs its own timeout. | probe |
| Quota failure exit code: UNKNOWN (not probed). Treat any non-zero exit as failure. Rate-limit waits can be long: the watchdog backs off up to 5 minutes between attempts. | docs: env-vars (retry watchdog entry) |
| SIGTERM on a `-p` run exits with 143 and records no result for the turn. | docs: headless |
| `--permission-prompts none` (v2.1.259+) denies anything that would prompt and tells the model not to retry. Useful with `dontAsk` for unattended runs. | docs: headless; `claude --help` |
| `--bare` skips hooks, skills, plugins, MCP, auto memory and CLAUDE.md. It needs `ANTHROPIC_API_KEY`; OAuth/keychain are not read. So it does not work on a subscription login. | `claude --help`; docs: headless |
| `--no-session-persistence` (only with `-p`) avoids saving the session. | `claude --help` |
| Open: a Bash allow rule matches by command prefix, so `Bash(git diff *)` also allows `git diff --output=<file>`, which writes a file. Whether `dontAsk` plus this rule is safe enough for a reviewer is UNKNOWN. Pipe the diff in instead if strict read-only is required. | docs: headless (typo-linter example pipes `git diff`); inference |

### 2. Concurrent subagents

- Default cap: 20 running subagents per session. Past it, the Agent tool fails with `Concurrent subagent limit reached` and tells the model not to retry. It succeeds again when the count drops. (docs: sub-agents)
- Configurable with `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (positive integer, plain digits, v2.1.217+). The cap can be changed but not disabled. (docs: env-vars)
- Three writers plus several readers is well below 20. No change needed.

### 3. Nested subagents

- Yes. A subagent can spawn subagents, up to 3 layers below the main conversation by default. (docs: sub-agents, "Let subagents spawn their own subagents")
- Change with `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; `1` turns nesting off. At the limit the `Agent` tool is withheld from subagents except forks. (docs: sub-agents, env-vars)
- A subagent gets `Agent` only if its `tools` list includes it (or it inherits all tools). To keep a reviewer from spawning, omit `Agent` from `tools` or add it to `disallowedTools`. A type list inside `Agent(...)` is ignored in a subagent definition; it works only for `claude --agent` main-thread agents. (docs: sub-agents)
- History: v2.1.172-2.1.216 default depth 5, not changeable; v2.1.217-2.1.218 default 1; v2.1.219+ default 3. (docs: sub-agents)
- In `-p` and SDK mode, a launching subagent does not wait for its background children. A late child reports to the main conversation. (docs: sub-agents)

### 4. Resuming a subagent after a restart

- Documented as working: "You can resume a subagent after restarting Claude Code by resuming the same session." Resume the session (`claude --resume <session-id>`), then `SendMessage` with the agent ID or name in `to`. (docs: sub-agents, Resume subagents)
- Transcripts: `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`. They are deleted after `cleanupPeriodDays` (default 30). (docs: sub-agents)
- `SendMessage` to a completed subagent resumes it in the background under the same ID. It works for one stopped with `TaskStop` once its run has exited. It is refused for one the user stopped by hand. (docs: sub-agents)
- Explore and Plan agents are one-shot and return no agent ID. Use `general-purpose` or a custom agent for resumable work. (docs: sub-agents)
- `SendMessage` does not need agent teams to be enabled. (docs: sub-agents)
- A name can go stale: `SendMessage` refuses a name that now points to a newer agent. Address by agent ID. (docs: sub-agents)
- Not tested end to end here (no model call spent on it). Treat the restart case as documented but unverified locally.

### 5. Environment of Bash tool commands

Observed in this session's Bash tool (a normal interactive CLI session):

| Variable | Value / note |
|---|---|
| `CLAUDECODE` | `1`. Docs: set in Bash/PowerShell tool, hook, status line and stdio MCP subprocesses. |
| `CLAUDE_CODE_CHILD_SESSION` | `1`. Docs: set for Bash/PowerShell/Monitor tools, hooks, status line (not stdio MCP). |
| `CLAUDE_CODE_ENTRYPOINT` | `cli`. Observed. Not in the docs env-vars page. The binary also sets `sdk-ts` when started through the SDK. Do not rely on it for detection; use `CLAUDECODE`. |
| `CLAUDE_CODE_SESSION_ID` | The session UUID. Observed only. Not found in the docs pages read. |
| `CLAUDE_CODE_EXECPATH` | Path of the running binary. Observed only. |
| `CLAUDE_CODE_SESSION_ATTENDED` | `1`. Observed only. |
| `CLAUDE_PID`, `CLAUDE_EFFORT` | Observed only (`CLAUDE_EFFORT=high` here). |
| `CLAUDE_CODE_MESSAGING_SOCKET`, `CLAUDE_CODE_MESSAGING_TOKEN` | Documented (v2.1.224/228+). Per-session; the token is a secret. |
| `CLAUDE_CONFIG_DIR` | Set here by the CCS wrapper, not by Claude Code. |

- `CLAUDE_SKILL_DIR`: documented as the substitution `${CLAUDE_SKILL_DIR}`, replaced in the skill's markdown content and in Bash rules in `allowed-tools` frontmatter. The docs do not describe it as an exported environment variable. Use the `${CLAUDE_SKILL_DIR}` form inside SKILL.md instructions. `${CLAUDE_PROJECT_DIR}` works the same way. (docs: skills)
- `sae` can detect "running under Claude Code" with `CLAUDECODE=1`. A `claude -p` child started from a Bash tool call inherits it, so do not use it as an "already inside sae" guard.

### 6. Extra directories and rule syntax

- Three ways to add a directory: `--add-dir <path>` at startup, `/add-dir` in a session, or `permissions.additionalDirectories` in a settings file (a JSON array of paths). (docs: permissions, Working directories)
- Files there follow the normal rules: readable without prompts. Edits follow the permission mode (`acceptEdits` auto-accepts edits there). (docs: permissions; permission-modes table)
- `permissions.additionalDirectories` grants file access only. `--add-dir` also loads some config (skills, and others listed in the docs). (docs: permissions)
- `additionalDirectories` and `allow` rules in a project `.claude/settings.json` are used only after the workspace trust dialog is accepted. In `-p` runs on an untrusted folder they are not used, and a warning goes to stderr. (docs: permissions)
- Path rules for `Read` and `Edit` use gitignore syntax: `//path` is an absolute path from the filesystem root (`Edit(//tmp/wt/**)`), `~/path` is from home, `/path` is relative to the settings source (project settings: the primary working dir), `path` or `./path` is relative to the cwd. `/home/alice/file` is NOT absolute. (docs: permissions)
- Only `Edit(path)` and `Read(path)` rules are consulted for file paths. `Edit` covers Write and NotebookEdit. A `Write(path)` rule is accepted but never used, and a startup warning is printed. A `Read` deny also blocks Edit/Write on that path. (docs: permissions)
- In a worktree session, `/path` rules anchor at that worktree's primary working directory. Saved "don't ask again" rules go to `.claude/settings.local.json` at the main checkout root (v2.1.211+). (docs: permissions)
- `--allowedTools` entries are added as session rules. Path patterns written there anchor at the primary working directory. For an absolute worktree path use `Edit(//abs/path/**)`. Not probed. (docs: permissions)

### Consequences for sae

- Reviewer command: `claude -p "<prompt>" --model <alias> --permission-mode dontAsk --allowedTools "Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(git show *)"`. Capture stdout as the final message. Treat non-zero exit as failure. Enforce a wall-clock timeout in `sae`.
- Prefer `--output-format json` when `sae` needs cost, session ID or error detail, and parse `result`.
- Optionally add `--permission-prompts none` and `--no-session-persistence` for reviewers.
- Writers: put the worktree root in `permissions.additionalDirectories`, and add `Edit(//abs/worktree/**)` allow rules if edits must not prompt.
- Subagent cap (20) and depth (3) need no configuration for 3 writers plus several readers. Keep `Agent` out of reviewer tool lists.
