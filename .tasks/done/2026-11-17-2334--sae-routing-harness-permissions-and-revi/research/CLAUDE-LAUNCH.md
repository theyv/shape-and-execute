---
status: done
confidence: high
---

# Research: CLAUDE-LAUNCH

Evidence covers the installed Claude Code **2.1.326** and Codex CLI **0.169.0** on macOS.
Experiments used disposable linked worktrees, an isolated Claude config directory, and canned
API responses served over loopback. They used zero model calls.

## Answers

### 1. Which launch can edit, verify, and write Git without prompts?

**Answer.** For known verification commands, start Claude at the job worktree root in
`dontAsk` mode. Approve worktree edits, the exact verification commands, and the necessary Git
verbs in a per-launch settings file or with `--allowedTools`. This is the narrowest tool
approval pattern tested. For arbitrary commands selected during the job, bare `Bash` allows
all Bash calls that pass the remaining checks. Another option is the Bash sandbox's
auto-approval, which permits commands that can run within its OS policy.

```sh
cd "$job_worktree" &&
  claude -p "$prompt" --model "$model" --effort "$effort" \
    --permission-mode dontAsk --permission-prompts none \
    --settings "$writer_settings" --output-format json
```

In the fixture, `permissions.allow` contained `Edit(./**)`, `Bash(python3 verify.py)`,
`Bash(git add *)`, `Bash(git commit *)`, and `Bash(git merge *)`. Replace the fixture
verification rule with a rule for each actual command. The parent sandbox still has to
permit each operation.

**Evidence**

- [primary, 2.1.326 scratch replay] Both the settings file and the equivalent CLI rules let
  `Write`, the verifier, `git add`, `git commit`, and a non-fast-forward `git merge` run in a
  linked worktree. The CLI-rule replay denied a file write outside the worktree. An explicit
  Bash deny beat an overlapping allow, and an unlisted Bash call was denied. This exercised
  tool approval with Claude's inner Bash sandbox off and the existing outer policy in force.
  The replay used `--setting-sources '' --strict-mcp-config --safe-mode --no-session-persistence`
  to isolate the fixture from local customizations and session storage.
- [primary] `acceptEdits` approves ordinary file edits and selected filesystem commands in
  working directories. Git writes and general verification still need approval. Manual
  (`default`) approves reads and recognized read-only Bash. `plan` blocks ordinary edits.
  `auto` uses a classifier that can refuse commands and depends on account, model, and
  policy. `bypassPermissions` drops most approval checks, including protected-path checks,
  while explicit denials and some prompts still apply. `--dangerously-skip-permissions`
  selects that mode. In plain print mode with no host,
  unanswered prompts are denied. `--permission-prompts none` also disables waiting on a
  permission host, where present, in v2.1.259 and later.
  [Permission modes](https://code.claude.com/docs/en/permission-modes#available-modes)
  [Bypass mode](https://code.claude.com/docs/en/permission-modes#skip-all-checks-with-bypasspermissions-mode)
  [Unattended print runs](https://code.claude.com/docs/en/headless#turn-off-permission-prompts-in-unattended-runs)
- [primary] `--allowedTools` adds approvals alongside `permissions.allow`. Built-in reads
  and recognized read-only shell commands can run independently of that list. `--tools`
  controls built-in tool visibility. Compound shell commands need approval for each segment.
  Exact verification rules have a smaller scope than `Bash(git *)`, `Bash(python3 *)`, or
  bare `Bash`. Even a narrow Bash approval authorizes the program it runs, including any
  file and network access it gets from the OS.
  [CLI flags](https://code.claude.com/docs/en/cli-reference#cli-flags)
  [Bash rule syntax](https://code.claude.com/docs/en/permissions#bash)
  [Tool approval](https://code.claude.com/docs/en/headless#auto-approve-tools)
- [primary] The launch directory already counts as a working directory. `--add-dir` and
  `permissions.additionalDirectories` extend the working directories and sandbox write
  roots. They leave edit approval to the mode and rules. The flag also discovers some
  additional configuration. `Edit(path)` covers all built-in editing tools. Absolute
  patterns use `//` at the start, which the current setup snippet obtains by prepending
  `/` to an absolute root. The current snippet grants the entire worktree root and all
  `git` verbs, beyond what the scratch writer needed.
  [Working directories](https://code.claude.com/docs/en/permissions#working-directories)
  [Path patterns](https://code.claude.com/docs/en/permissions#how-path-patterns-match)
  [Setup snippet](../../../skills/shape-and-execute/scripts/sae_lib/setup_mode.py#L507)

**Confidence** High for the tested launch. Availability depends on effective policy and the
specific verification command.

### 2. Which settings win, and can the launch select a separate file?

**Answer.** Yes. Precedence for ordinary scalar keys is managed policy, `--settings` JSON
or file, project-local, project, then user. The file passed with `--settings` is a
session overlay. `CLAUDE_CONFIG_DIR` selects the account's config and state location.

**Evidence**

- [primary] The user file is `$CLAUDE_CONFIG_DIR/settings.json` or `~/.claude/settings.json`.
  The project file is `.claude/settings.json` under the primary working directory. Recent
  versions normally read `.claude/settings.local.json` at the main checkout's root in a
  linked worktree, subject to ownership and platform exceptions. `--permission-mode` sets
  the starting mode ahead of `permissions.defaultMode`, subject to mode availability and
  managed restrictions. Permission lists normally merge across sources. Matching rules are
  evaluated deny, then ask, then allow. Managed locks can reject lower-tier entries.
  [Settings locations and precedence](https://code.claude.com/docs/en/settings#settings-precedence)
  [Local file in Git](https://code.claude.com/docs/en/settings#where-claude-code-keeps-the-local-file-in-a-git-repository)
  [Rule precedence](https://code.claude.com/docs/en/permissions#manage-permissions)
  [Account configuration](https://code.claude.com/docs/en/authentication#log-in-with-multiple-accounts)
- [primary, 2.1.326 scratch handshake] A user file in `CLAUDE_CONFIG_DIR` loaded. Local
  `defaultMode` beat project and user, and the launch file beat local. All four allow lists
  appeared in the merged snapshot. `--setting-sources ''` omitted user, project, and local
  and kept the launch file. `--setting-sources user` loads the account's user settings
  without the two repository tiers. Managed policy loads regardless of that selection.
  [CLI flags](https://code.claude.com/docs/en/cli-reference#cli-flags)
  [Settings sources](https://code.claude.com/docs/en/agent-sdk/typescript#settingsource)
- [primary] Print mode skips the trust dialog. Shared project allow rules and additional
  directories can still be withheld for an untrusted workspace, while some repository
  hooks and settings can run. The scratch handshake emitted the trust warning despite
  listing the shared rule in the merge. The installed `--help` also warns that print mode
  can ignore invalid settings files without a dialog.
  [Project trust](https://code.claude.com/docs/en/permissions#what-runs-before-you-trust-a-folder)
  [Fix invalid settings](https://code.claude.com/docs/en/settings#fix-a-broken-settings-file)

**Confidence** High.

### 3. Does the Claude sandbox apply to print mode?

**Answer.** Yes. When `sandbox.enabled` is true, Claude Code applies its sandbox to Bash
and its descendants, subject to the configured exclusions and retry policy. The Claude
process, model API client, and built-in file tools run outside that inner Bash sandbox.

**Evidence**

- [primary] The documented filesystem policy allows writes in working directories and
  per-user temp. From a linked worktree root it also allows writes in the main repository's
  shared Git directory, with protection for hooks and config. Use resolved
  `git rev-parse --git-dir` and `--git-common-dir` paths to identify the two metadata
  locations. Parent restrictions still apply to both.
  [Claude filesystem isolation](https://code.claude.com/docs/en/sandboxing#filesystem-isolation)
  [Git worktree details](https://git-scm.com/docs/git-worktree#_details)
- [primary] On macOS, `sandbox.network.allowUnixSockets` permits named Unix socket
  paths. `allowAllUnixSockets` opens all paths and is the available switch when Linux/WSL2
  seccomp blocks AF_UNIX. Without that filter, Linux/WSL2 does not enforce that block.
  On macOS `allowLocalBinding: true` permits listening on any local address and connecting
  to any loopback port. Linux/WSL2 use a separate network namespace, so this key has no
  effect and direct loopback cannot reach a host service.
  [Unix socket settings](https://code.claude.com/docs/en/settings-reference#sandbox-network-allowunixsockets)
  [Local binding settings](https://code.claude.com/docs/en/settings-reference#sandbox-network-allowlocalbinding)
- [primary] `sandbox.network.allowedDomains` pre-approves proxy destinations and can
  include ports. `deniedDomains` takes precedence. Direct sockets and clients that ignore
  proxy variables need their own compatible path. `autoAllowBashIfSandboxed: false` keeps
  explicit tool checks for Bash. `allowUnsandboxedCommands: false` disables unsandboxed
  retries. `failIfUnavailable: true` checks platform support and dependencies at startup.
  [Network isolation](https://code.claude.com/docs/en/sandboxing#network-isolation)
  [Sandbox modes](https://code.claude.com/docs/en/sandboxing#sandbox-modes)
  [Sandbox availability](https://code.claude.com/docs/en/settings-reference#sandbox-failifunavailable)
- [primary, 2.1.326 scratch replay] With the inner sandbox on, the built-in file write
  passed. The permitted Bash commands failed when nested Seatbelt tried to apply.
  `failIfUnavailable: true` still let this session initialize. This worker's direct
  scratch AF_UNIX bind/connect and its loopback HTTP fixture both passed under the outer
  policy. The inner socket settings could not be exercised here.

**Confidence** High for documented behavior and the nested failure. Native operation of
the inner sandbox on the target launch host is unknown.

### 4. What can a preflight prove without a model call?

**Answer.** Configuration and startup can be inspected without a model call. A canned
local API response can exercise the actual tool path without model inference. A live
account and provider check needs the real account, endpoint, and launch environment.

**Evidence**

- [primary, 2.1.326 scratch handshake] Run `claude -p --input-format stream-json
  --output-format stream-json --verbose` with the settings and mode under test. Send
  newline-delimited `control_request` objects with `request_id` and
  `request: {"subtype":"initialize"}`, then `{"subtype":"get_settings"}`, and close stdin
  without a user message. The successful `initialize` response contained
  `current_permission_mode`. `get_settings` returned `effective`, `sources`, and `applied`.
  It showed the merged settings, including a trust-filtered allow rule, and omitted
  CLI-supplied `--allowedTools` from the settings lists. Treat it as a configuration
  snapshot. The raw field and request support were observed on this version.
  [SDK startup handshake](https://code.claude.com/docs/en/agent-sdk/typescript#startup)
- [primary] The SDK documents model-free `startup()` and an alpha `resolveSettings()`
  helper. The static resolver has differences from a live session, including managed
  policy helpers, server-managed settings and linked-worktree local settings. No documented
  dry-run evaluator for arbitrary tool inputs was found in the print CLI. Test the parent
  path directly or use a replay to cover Claude's own tool checks too.
  [SDK settings resolver](https://code.claude.com/docs/en/agent-sdk/typescript#resolvesettings)
  [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [primary, 2.1.326 scratch replay] A fake Messages API emitted fixed tool calls. This
  deterministically tested real file writes, Git changes, tool denials, and sandbox
  execution failures at zero model cost. It substituted a fake API key and endpoint,
  so live auth, provider connectivity, and model behavior remain unknown. It covered only
  the operations and launch environment exercised.
  [API endpoint override](https://code.claude.com/docs/en/env-vars#variables)
- [primary evidence, inference] A short run with a cheap supported model, low effort,
  turn and budget caps, and a benign sentinel in a disposable linked worktree can add a
  live end-to-end check. Observe the exact tool calls, their results, and resulting files
  or Git state. A missing tool call is inconclusive. Each required Unix socket, TCP port,
  or outbound route must be exercised from the relevant process. A run can make multiple
  model requests, and a passing fixture covers only its own inputs.
  [Print run limits](https://code.claude.com/docs/en/cli-reference#cli-flags)
  [Cost accounting](https://code.claude.com/docs/en/agent-sdk/cost-tracking)

**Confidence** High for the fixture and startup observations. The live account was outside
the experiment.

### 5. What machine-readable fields report the result?

**Answer.** Use the `system/init` event for `permissionMode` and the terminal
`type: "result"` record for the session ID, denials, usage and run outcome.

**Evidence**

- [primary, 2.1.326 scratch replay] Plain `--output-format json` returned a single result
  object. Adding `--verbose` returned an array that included `system/init`. With
  `--output-format stream-json --verbose`, records were JSON lines. The init event carried
  `permissionMode`, `session_id` and `claude_code_version`. The result carried
  `session_id`, `subtype`, `is_error`, `usage`, `modelUsage`, `total_cost_usd` and
  `permission_denials`, with no `permissionMode` field.
  [Headless formats](https://code.claude.com/docs/en/headless#get-structured-output)
  [Init schema](https://code.claude.com/docs/en/agent-sdk/typescript#sdksystemmessage)
  [Result schema](https://code.claude.com/docs/en/agent-sdk/typescript#sdkresultmessage)
- [primary] Each denial in `permission_denials` has `tool_name`, `tool_use_id` and
  `tool_input`. A best-effort `system/permission_denied` event can also include a reason.
  Its absence is inconclusive. The result's `usage` covers the main loop. `modelUsage`
  aggregates by model across the query pipeline and can include prior session totals on
  resume. Helper calls such as the permission classifier can be outside that accounting.
  [Denial event](https://code.claude.com/docs/en/agent-sdk/typescript#sdkpermissiondeniedmessage)
  [Denial entry](https://code.claude.com/docs/en/agent-sdk/typescript#sdkpermissiondenial)
  [Usage accounting](https://code.claude.com/docs/en/agent-sdk/typescript#sdkresultmessage)
- [primary, 2.1.326 scratch replay] Exit zero and a successful result coexisted with
  tool denials. In the nested sandbox replay, approved commands failed as tool execution
  errors and never appeared in `permission_denials`. The two deliberately denied calls
  appeared in the array. A preflight needs the individual tool results or independent
  state checks as well as result metadata.

**Confidence** High.

### 6. What must a Codex parent allow?

**Answer.** A `claude` process launched by a sandboxed Codex shell inherits the outer
platform restrictions. Its own flags can govern a narrower set of operations. Verify
the settings of the parent that actually starts Claude.

**Evidence**

- [primary] The child needs executable and working-directory access, provider/auth
  network access, and writes for any state it persists. The selected Claude config
  directory holds account state and sessions. macOS auth can use Keychain.
  `--no-session-persistence` prevents transcripts and resume, with other config access
  dependent on the launch. Codex's `shell_environment_policy` can filter the account
  selector and provider variables. Codex's own model transport is separate from the
  command network used by the Claude child.
  [Claude credentials](https://code.claude.com/docs/en/authentication#credential-management)
  [Claude CLI flags](https://code.claude.com/docs/en/cli-reference#cli-flags)
  [Codex environment policy](https://learn.chatgpt.com/docs/config-file/config-advanced#shell-environment-policy)
  [Codex command network](https://learn.chatgpt.com/docs/permissions#what-the-network-proxy-does-not-control)
- [primary] Legacy `workspace-write` can enable command network with
  `sandbox_workspace_write.network_access = true` and add writable roots. Default
  protection can keep Git metadata read-only, including the linked-worktree gitdir.
  A named permission profile can explicitly scope writes to the job, Git metadata, and
  required state paths. Use `default_permissions` with `[permissions.*]` and omit legacy
  `--sandbox` or `sandbox_mode` when selecting the profile. Profile
  `network.enabled = true` grants command network. Activate `features.network_proxy`
  or the managed proxy to enforce destination rules. For local ports and sockets, the
  proxy allowlists and OS enforcement depend on client transport and platform.
  [Codex profiles](https://learn.chatgpt.com/docs/permissions)
  [Codex local networks and sockets](https://learn.chatgpt.com/docs/permissions#local-and-private-networks)
  [Codex 0.169.0 backend notes](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/README.md#macos)
- [primary] A Codex-approved escalation or an external launcher has its own boundary.
  A local Codex `prefix_rule` with `decision = "allow"` can run matching commands outside
  the Codex sandbox where policy permits. A prefix matching all `claude` invocations
  would cover other launches and flags too.
  [Codex execution rules](https://learn.chatgpt.com/docs/agent-configuration/rules#understand-rule-fields)
- [primary, macOS scratch experiment] The active parent allowed the isolated config
  directory and loopback HTTP. Both Claude's nested sandboxed Bash and a direct Codex
  0.169.0 `sandbox -P :workspace -- /usr/bin/true` test failed to apply nested Seatbelt.
  A different parent launch can have different results.

**Confidence** High for inheritance and the observed failure. The production account's
auth, paths, and effective parent policy are unknown.

## Options and tradeoffs

| Option | Tradeoff |
| --- | --- |
| Launch overlay with `dontAsk`, scoped edits, and command rules | Limits pre-approvals to job needs. Verification commands must be known or supplied by the job. |
| Bare `Bash` or sandbox auto-approval | Supports verification commands chosen at run time. Bare Bash is broad. Sandboxed Bash relies on the OS boundary and successful sandbox startup. |
| User-scope settings | Reusable for that account's sessions. Permission lists apply across the account's projects and can widen headless review approvals. |
| Keep user/project layers with `--settings`, or select fewer layers | Keeping them preserves account and repo configuration. Fewer layers reduce variability and can omit required customizations. |
| Handshake, fixture, or live preflight | Handshake proves startup and exposes configuration. The fixture exercises chosen operations. A live probe adds evidence about real auth, provider connectivity, and the actual launcher at API cost. |

## Open questions

- What verifier commands, sockets, ports, and outbound endpoints does each routed job need?
- Does the intended launch apply a compatible outer sandbox and account configuration?
- Which Claude versions must support model-free settings inspection? The raw
  `get_settings` request was checked on 2.1.326 only.

## Implications for the spec

- A per-launch file can carry the writer's settings without editing the account's user
  settings. The selected config directory, enabled settings sources, trust and managed
  policy still affect the run.
- Check writing ordinary files and Git metadata independently. A successful startup or
  allowed Bash call can still fail to execute. A meaningful readiness claim names the
  operations actually exercised.
- The existing review command supplies additive approvals. Inherited settings and the
  OS boundary determine its actual write access.
  [Current Claude review invocation](../../../skills/shape-and-execute/scripts/sae_lib/prompts.py#L423)
  [Tool approval semantics](https://code.claude.com/docs/en/headless#auto-approve-tools)
- Raw denial records can contain tool inputs. Store only the operational metadata needed
  to explain the attempt in public task files.
  [Denial entry fields](https://code.claude.com/docs/en/agent-sdk/typescript#sdkpermissiondenial)

## Follow-up questions
