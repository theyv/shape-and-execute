---
status: done
confidence: medium
---

# Research: SANDBOX-ISOLATION

Installed CLIs on the research day: Claude Code 2.1.332, Codex CLI 0.171.0, APM 0.34.0, Orca CLI
(app 1.4.268), macOS. Paths below use `$HOME`/`~`; the owner's real paths are not recorded.
"Observed" means a command run in a scratch directory with a relocated `HOME`; no harness
session was started and no model was called. Nothing of the owner's was changed (checked
afterwards: the owner's APM manifest and skill folders kept their timestamps).

## Recommendation (read this first)

Run the walkthrough in a **relocated home**: one throwaway folder `$SB` that becomes `HOME`,
`CLAUDE_CONFIG_DIR` and `CODEX_HOME` of the session, started through `env -i` from a **new Orca
terminal** that only runs a launch script. Everything that reads `~` (APM, `sae` config,
`sae` worktree root and viewer state, Codex skills, git config, shell history of the harness)
then lands in `$SB` by default, so a forgotten variable cannot leak the owner's setup. Install the
skill with the README's APM command, with the package spec swapped for a `git archive` export of
the task branch. Authenticate Claude with a `setup-token` OAuth token typed into the launch
prompt (a copied credentials file does not work on macOS, see Q1). Authenticate Codex with a fresh
`codex login` inside the sandbox.

What was observed to work (zero model calls):

- `apm install -g <local skill dir> --target claude,codex` with `HOME` and `CLAUDE_CONFIG_DIR`
  set wrote only inside `$SB`: `$SB/home/.claude/skills/shape-and-execute` (a copy, not a
  symlink), `$SB/home/.agents/skills/shape-and-execute`, `$SB/home/.apm/`.
- `claude auth status` and `codex login status` in that environment: "Not logged in" (the
  owner's login does not leak in). `codex doctor --json` showed every Codex path
  (control socket, daemon state, auth file, logs, sqlite) under `$SB`.
- `sae doctor` in that environment printed the config path `$SB/home/.config/shape-and-execute/
  config.json` ("missing": the fresh-install state, `sae` asks for setup), and, after copying a
  config without an `easy` column, printed the upgrade hint ("easy falls back to the mechanical
  cell ... setup mode").
- With `PATH=$SB/bin:/usr/bin:/bin` and symlinks only for `claude`, `codex`, `node`, `python3`,
  `git`, `python3 sae.py doctor` still passes, and `gh`, `brew` and the owner's own tools are not
  reachable.

Not verified (needs the session itself): that Claude actually lists and runs the skill from
`$SB/home/.claude/skills`; that `CLAUDE_CODE_OAUTH_TOKEN` logs in (no token was minted);
that Claude `/login` works under a relocated `HOME` (Keychain access unknown); that Codex
lists the skill from `$HOME/.agents/skills` (documented, not run).

### Commands

Step 0, create the sandbox (run once per scenario, in the owner's normal terminal; `SRC` is the
task-branch checkout, which must be committed because `git archive HEAD` exports committed
files only):

```bash
SRC=<path of the task-branch checkout>
SB=$(mktemp -d /tmp/sae-wt.XXXXXX) && SB=$(cd "$SB" && pwd -P)   # short path: Unix socket paths are limited to ~100 chars
mkdir -p "$SB"/{bin,home,repo,src,state}
for t in claude codex node python3; do ln -s "$(command -v $t)" "$SB/bin/$t"; done
git -C "$SRC" archive HEAD skills/shape-and-execute | tar -x -C "$SB/src"
cat > "$SB/env.sh" <<'EOF'
#!/bin/bash
# Runs "$@" in the sandbox environment. Nothing else of the caller's environment is passed.
SB="$(cd "$(dirname "$0")" && pwd -P)"
exec env -i HOME="$SB/home" CLAUDE_CONFIG_DIR="$SB/home/.claude" CODEX_HOME="$SB/home/.codex" \
  XDG_CONFIG_HOME="$SB/home/.config" SAE_STATE_DIR="$SB/state" \
  PATH="$SB/bin:/usr/bin:/bin" TERM="${TERM:-xterm-256color}" LANG=en_US.UTF-8 \
  USER="$USER" LOGNAME="${LOGNAME:-$USER}" SHELL=/bin/zsh \
  DISABLE_AUTOUPDATER=1 ENABLE_CLAUDEAI_MCP_SERVERS=false "$@"
EOF
chmod +x "$SB/env.sh"
```

Step 1, install the skill like a new user ([README Install](../../../README.md#install), same
flags, only the package spec differs: the README's `theyv/shape-and-execute/...` spec fetches
the published default branch, and the task branch is not pushed):

```bash
APM=$(type -P apm)            # the binary, not a shell function
cd "$SB" && "$SB/env.sh" "$APM" install -g "$SB/src/skills/shape-and-execute" --target claude,codex
```

Step 2, the throwaway repository (a repo-local identity, because the relocated `HOME` has no
`~/.gitconfig`; `git commit` fails without one):

```bash
cd "$SB/repo" && "$SB/env.sh" git init -q -b main . \
 && "$SB/env.sh" git config user.name "SaE Walkthrough" \
 && "$SB/env.sh" git config user.email "walkthrough@example.invalid" \
 && echo "# demo" > README.md && "$SB/env.sh" git add . && "$SB/env.sh" git commit -qm init
mkdir -p "$SB/home/Library/Caches/shape-and-execute/worktrees"   # the default worktree root under the relocated HOME
```

Step 3, the scenario:

- Fresh install: nothing to do. `sae` finds no config at `$SB/home/.config/shape-and-execute/
  config.json`, exits 2 and the skill starts setup.
- Upgrade: copy an older config and point its worktree root into the sandbox (a config is
  `schema` 2 JSON; the owner's current one has no `easy` column, which is what the upgrade path
  of `setup.md` step 1 handles):

```bash
mkdir -p "$SB/home/.config/shape-and-execute"
python3 -I - "$SB" <<'EOF'
import json, os, sys
sb = sys.argv[1]
d = json.load(open(os.path.expanduser('~/.config/shape-and-execute/config.json')))  # or an older .bak
d['worktrees']['root'] = sb + '/home/Library/Caches/shape-and-execute/worktrees'
d['projects'] = {}                                  # per-repo defaults of the owner's repositories
json.dump(d, open(sb + '/home/.config/shape-and-execute/config.json', 'w'), indent=2)
EOF
chmod 600 "$SB/home/.config/shape-and-execute/config.json"
```

Step 4, isolation check before the owner types anything (all of these were run and passed):

```bash
cd "$SB/repo"
"$SB/env.sh" claude auth status --text       # expect: Not logged in (before the token), no owner account
"$SB/env.sh" codex login status              # expect: Not logged in
"$SB/env.sh" env SAE_HARNESS=claude python3 "$SB/home/.claude/skills/shape-and-execute/scripts/sae.py" doctor
#   every printed path must start with $SB
```

Step 5, the launch scripts (written by the orchestrator, one per harness):

```bash
cat > "$SB/launch-claude.sh" <<'EOF'
#!/bin/bash
SB="$(cd "$(dirname "$0")" && pwd -P)"
cd "$SB/repo" || exit 1
printf 'Paste a CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token` (Enter alone: log in with /login inside): '
read -rs tok; echo
if [ -n "$tok" ]; then exec "$SB/env.sh" env CLAUDE_CODE_OAUTH_TOKEN="$tok" claude
else exec "$SB/env.sh" claude; fi
EOF
cat > "$SB/launch-codex.sh" <<'EOF'
#!/bin/bash
SB="$(cd "$(dirname "$0")" && pwd -P)"
cd "$SB/repo" || exit 1
"$SB/env.sh" codex login status >/dev/null 2>&1 || "$SB/env.sh" codex login   # browser login into $SB/home/.codex
exec "$SB/env.sh" codex --no-daemon -C "$SB/repo"
EOF
chmod +x "$SB"/launch-*.sh
```

Step 6, open the session in a new Orca terminal. `--command` is typed into the terminal's login
shell, so keep it to one short command; the script does the rest. `--worktree` must name an
existing Orca workspace (the terminal opens there, then the script `cd`s away). No Orca repo or
worktree is added, so Orca's registry stays as it was:

```bash
orca terminal create --worktree active --title "SaE walkthrough (claude)" \
  --command "bash $SB/launch-claude.sh" --focus --json
# keep result.handle for cleanup; the second harness: same call with launch-codex.sh
```

(`active` resolves the Orca workspace that encloses the caller's cwd; from anywhere else use
`path:<abs path of an existing Orca workspace>`. Source: `orca terminal create --help`.)

In the session the owner types `/shape-and-execute <rough note>` (Claude) or
`$shape-and-execute <rough note>` (Codex), as in the README's First run.

### Cleanup, and what must never be touched

Delete (all inside `$SB`, or things created for it):

```bash
orca terminal close --terminal <handle> --tab            # only the handle(s) you created
"$SB/env.sh" python3 "$SB/home/.claude/skills/shape-and-execute/scripts/sae.py" view --stop
# only if Claude /login was used inside the sandbox (token mode writes no Keychain entry):
"$SB/env.sh" claude auth logout
security dump-keychain 2>/dev/null | grep -c 'Claude Code-credentials'   # compare with the count taken before the walkthrough
# last, with a guard:
case "$SB" in /private/tmp/sae-wt.*|/tmp/sae-wt.*) [ -d "$SB/home" ] && rm -rf "$SB";; esac
```

The throwaway repo's job worktrees live under `$SB/home/Library/Caches/...`, so they go with
`$SB`. A Keychain entry created by a sandbox login is named `Claude Code-credentials-<8 hex>`
where the 8 hex are the first 8 characters of `sha256(CLAUDE_CONFIG_DIR string)` (observed:
this reproduces two existing entries for two known config dirs). Delete only the entry that
appeared during the walkthrough (diff the service list before and after); a wrong delete logs
the owner out.

Never touch: `~/.claude*` and any `CLAUDE_CONFIG_DIR` of the owner's accounts, the account
manager's instance folders, `~/.codex`, `~/.agents`, `~/.apm`, `~/.config/shape-and-execute`,
`~/Library/Application Support/shape-and-execute` (the owner's viewer state), the Keychain
entries that existed before (above all the unsuffixed `Claude Code-credentials`), Orca's own
settings and every Orca workspace other than the terminal you opened, the task worktree `$SRC`
(it is read by `git archive` only), and the owner's repositories. Do not run
`orca terminal close --worktree ... --all`: it stops every terminal of that workspace.

## Answers

### 1. Starting Claude Code with only the task-branch skill, still logged in

**Answer:** Relocate the config directory and `HOME`, and bring the login in through an
environment token, not through a copied file. On macOS the login is in the Keychain, keyed
by the config directory, so a new directory is logged out by design; `.credentials.json` is only
a fallback store.

**Evidence:**
- Config, settings, history and plugins live under `CLAUDE_CONFIG_DIR`; credentials too, "and
  keys the macOS Keychain entry to that directory too, so a session with a different
  `CLAUDE_CONFIG_DIR` reads a different entry" — https://code.claude.com/docs/en/authentication
  (Credential management) [primary]; https://code.claude.com/docs/en/env-vars (`CLAUDE_CONFIG_DIR`) [primary].
- On this Mac the owner's config-dir `.credentials.json` holds only MCP OAuth data (key names
  checked, no values read); the login sits in Keychain services named `Claude Code-credentials`
  and `Claude Code-credentials-<8 hex>`; the 8 hex match `sha256(<config dir>)[:8]` for two known
  directories — `security dump-keychain | grep svce`, `shasum -a 256` [primary, observed].
  Copying `.credentials.json` therefore carries no login.
- `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`, "does not save the token anywhere") ranks
  above Keychain credentials and is "the token you set for the whole session"; it can only make
  model requests, so claude.ai connectors are not fetched; bare mode ignores it —
  https://code.claude.com/docs/en/authentication (Authentication precedence, Generate a long-lived
  token), https://code.claude.com/docs/en/env-vars (`CLAUDE_CODE_OAUTH_TOKEN`) [primary].
  `claude auth status --text` with a dummy token printed `Auth token: CLAUDE_CODE_OAUTH_TOKEN`
  and did not validate it [primary, observed]; so that check proves the source, not that the token works.
- Skill locations: personal `~/.claude/skills`, project `.claude/skills`, plugin skills,
  claude.ai account skills ("terminal sessions where you sign in with that account") —
  https://code.claude.com/docs/en/skills (Choose where skills load) [primary]. The docs show
  `~/.claude/` and do not say the personal path follows `CLAUDE_CONFIG_DIR`; the APM install
  wrote to `$CLAUDE_CONFIG_DIR/skills` [observed]. Session transcripts are read from
  `CLAUDE_CONFIG_DIR/projects` by `sae` itself ([setup_mode.py L77-L80](../../../skills/shape-and-execute/scripts/sae_lib/setup_mode.py), [session_tokens.py L63-L66](../../../skills/shape-and-execute/scripts/sae_lib/session_tokens.py)).
- Inherited variables are a real leak path: the owner's shell exports `CLAUDE_CONFIG_DIR`,
  `CLAUDE_CODE_PLUGIN_DIRS` (a terminal-manager plugin, "loaded the way a `--plugin-dir` flag loads
  it"; https://code.claude.com/docs/en/env-vars), `ENABLE_CLAUDEAI_MCP_SERVERS` and several account
  manager variables [primary, observed in `env`]. `env -i` removes all of them at once.
- What the options keep and drop is in the table below.

| Option | Keeps | Drops / leaks | Source |
|---|---|---|---|
| **A. Relocated `HOME` + `CLAUDE_CONFIG_DIR` + `env -i` + env token (recommended)** | model access via token; the skill (installed in `$SB`); nothing else of the owner | Drops global skills, CLAUDE.md, hooks, output style, plugins, MCP servers, memory, history, settings, `~/.gitconfig`, `gh`/ssh. Does not drop managed policy (none on this Mac: `/Library/Application Support/ClaudeCode` and `/etc/claude-code` absent) or server-managed settings of the token's organization (unknown) | docs above; observed |
| B. Relocate only `CLAUDE_CONFIG_DIR` | as A | `~/.agents`, `~/.gitconfig`, `~/.config/shape-and-execute`, `~/.apm`, `~/.codex` stay the owner's unless each is overridden; a missed variable silently leaks | observed: `sae` and APM read `~` by default |
| C. Owner's config dir + `--setting-sources project,local` (+ `--strict-mcp-config`) | the existing Keychain login, no token step | `user` source covers user settings, CLAUDE.md, rules, skills, commands, subagents, but "`~/.claude.json` global config" (MCP servers), auto memory, managed policy and claude.ai connectors are read regardless; transcripts and history are written into the owner's config dir (breaks "never touch") | https://code.claude.com/docs/en/agent-sdk/claude-code-features (What settingSources does not control); `claude --help` |
| D. `--safe-mode` | auth, model, permissions | disables skills too, so the skill under test is off | `claude --help`; https://code.claude.com/docs/en/cli-reference |
| E. `--bare` (+ `--add-dir` with the skill) | minimal system prompt | no OAuth or Keychain (API key only); a skill in an `--add-dir` loads but Claude "doesn't get the list of available skills"; not a first-run experience | https://code.claude.com/docs/en/headless (Start faster with bare mode) |
| F. `--restricted` | managed settings and `--settings` only | removes Bash and other command tools, which `sae` needs | `claude --help` |
| G. Keychain login for `$SB` by copying the owner's entry | no token step | reads and re-writes the owner's secret, unsupported, and a rotating refresh token could invalidate the owner's own login (unknown, not tested) | rejected |

**Login fallback (no token):** leave the token prompt empty and run `/login` inside the sandbox.
This is the real first-run flow, and `claude auth logout` in the sandbox environment removes it.
Unknown: whether the Keychain is reachable when `HOME` is relocated. The docs say Claude falls
back to `$CLAUDE_CONFIG_DIR/.credentials.json` when the Keychain write fails, which would keep
the login inside `$SB`.

**Confidence:** medium. Documentation and local observations agree; the token login and skill
discovery were not exercised.

### 2. The same for Codex

**Answer:** Cheap. `CODEX_HOME` plus a relocated `HOME` plus `env -i` isolates everything
observed; the skill is installed to `$HOME/.agents/skills`.

**Evidence:**
- `codex doctor --json` with `HOME=$SB/home CODEX_HOME=$SB/home/.codex`: config, auth file
  (`auth storage mode: File`), sqlite, logs, control socket and daemon state all under `$SB`
  [primary, observed]. Without `HOME` the log directory is `$HOME/Library/Logs/com.openai.codex`,
  so relocate `HOME` too.
- Codex user skills: `$HOME/.agents/skills` (not `$CODEX_HOME/skills`); repository skills in
  `.agents/skills` up to the repo root; admin `/etc/codex/skills` —
  https://learn.chatgpt.com/docs/build-skills (formerly developers.openai.com/codex/skills) [primary].
  APM `--target codex` wrote `$HOME/.agents/skills/shape-and-execute` [observed].
- Credentials: `auth.json` under `CODEX_HOME` or the OS store, chosen by
  `cli_auth_credentials_store` (`file`, `keyring`, `auto`, `ephemeral`) —
  https://learn.chatgpt.com/docs/auth [primary]. The owner's config uses a file store (an
  `auth.json` exists; contents not read), so a copy is possible: the docs give "Copy
  `~/.codex/auth.json` ... on the headless machine" as a fallback and warn to treat it like a
  password. Prefer a fresh login in the sandbox: `codex login` or `codex login --device-auth`
  (`codex login --help`); the docs do not say whether two runners can share one `auth.json`
  with token refresh, so a copy might invalidate the owner's own refresh token (unknown).
  API key via stdin is documented too (`printenv OPENAI_API_KEY | codex login --with-api-key`).
- `codex --no-daemon` "Run without the shared background server, even if it is already
  running" (`codex --help`); the daemon state is already under `CODEX_HOME`, so this is a
  precaution, not a requirement.
- `sae setup show` in the sandbox resolved all four Codex families without a login (it calls
  the CLI catalog), so setup's Codex part works in a fresh sandbox [observed].
- `codex exec --ignore-user-config` exists but skips only `$CODEX_HOME/config.toml` and is for
  exec; not needed once `CODEX_HOME` is a new folder (`codex exec --help`).

**Confidence:** medium-high. Skill discovery by Codex in the sandbox was not run.

### 3. Installing the skill the way a new user would, into the sandbox only

**Answer:** The README's APM command with the package spec replaced by the exported task
branch, under the relocated environment (Step 1). A new user would use
`apm install -g theyv/shape-and-execute/skills/shape-and-execute --target claude` (or `codex`) or
`npx skills add theyv/shape-and-execute --skill shape-and-execute -g -y --agent claude-code`
([README](../../../README.md#install)).

**Evidence:**
- Observed: `apm install -g <dir> --target claude,codex` created `$SB/home/.apm/{apm.yml,
  apm.lock.yaml,apm_modules}`, `$CLAUDE_CONFIG_DIR/skills/shape-and-execute` and
  `$HOME/.agents/skills/shape-and-execute`, and nothing outside. `-g` is "user scope
  (`~/.apm/`)" in `apm install --help`.
- The owner's shell wraps `apm -g` with `env -u CLAUDE_CONFIG_DIR` (seen via `type apm`): that
  wrapper is a zsh function and the script uses the binary (`type -P apm`), and the sandbox
  environment sets its own `CLAUDE_CONFIG_DIR` on purpose.
- Why not install from GitHub with a branch ref: the task branch is local and nothing is
  pushed. A local path installs a copy of the current files. `git archive HEAD` pins the
  committed state and leaves out untracked and ignored files (`__pycache__` was the only
  difference between the working tree and the installed copy).
- `npx skills add`: its README documents `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1`, but not
  local-path sources or the global target directories, and it was not run
  (https://github.com/vercel-labs/skills) [primary, incomplete]. Prefer APM for the sandbox.
- The installed copy does not follow later edits of the task branch; reinstall (rerun Step 0's
  `git archive` and Step 1) after a change. APM records the export's absolute path in
  `$SB/home/.apm/apm.yml`, so do not delete `$SB/src` during the walkthrough.

**Confidence:** high for the install; medium for how the harnesses then load it.

### 4. Isolating `sae` state: config, worktree root, throwaway repository

**Answer:** `HOME` relocation moves every default; the explicit variables make it visible.

**Evidence (source: [config.py](../../../skills/shape-and-execute/scripts/sae_lib/config.py), [setup_mode.py](../../../skills/shape-and-execute/scripts/sae_lib/setup_mode.py), [viewer.py](../../../skills/shape-and-execute/scripts/sae_lib/viewer.py)) [primary]:**
- Config: `SAE_CONFIG` if set, else `$XDG_CONFIG_HOME/shape-and-execute/config.json`, else
  `~/.config/...` (config.py L64-L68). The sandbox sets `XDG_CONFIG_HOME`; `SAE_CONFIG` is the
  stricter alternative (one exact file).
- Worktree root: the config's `worktrees.root` (absolute path, validated); setup proposes
  `~/Library/Caches/shape-and-execute/worktrees` on macOS or `${XDG_CACHE_HOME:-~/.cache}/...` on
  Linux (setup_mode.py L66-L71). A copied config must have `worktrees.root` rewritten, as in
  Step 3; a fresh setup under the relocated `HOME` proposes a path inside `$SB`. `sae doctor`
  reports a missing root as a failed check, so create the folder (Step 2).
- Viewer: state folder `SAE_STATE_DIR`, else `~/Library/Application Support/shape-and-execute`
  (macOS) or `$XDG_STATE_HOME`/`~/.local/state` (viewer.py L38, L64-L69). The server binds an
  ephemeral loopback port (`bind(("127.0.0.1", 0))`), so it cannot collide with the owner's
  viewer, but it is a background process that survives the session: stop it with `sae view --stop`
  (viewer.py L328). `SAE_VIEWER=off` stops `sae new` from starting it, which the test sandbox
  uses ([tests/saetest.py L236-L240](../../../tests/saetest.py)); leave it on for a faithful walkthrough.
- Harness detection: `SAE_HARNESS`, else `CLAUDECODE=1`, else Codex thread variables
  (config.py L872-L882). `env -i` removes the owner's values; the harness sets its own inside
  the session, so the walkthrough needs no `SAE_HARNESS`.
- Claude and Codex homes are read for session tokens and for the setup snippets from
  `CLAUDE_CONFIG_DIR` and `CODEX_HOME` (setup_mode.py L73-L80; session_tokens.py L63-L75): the
  same variables isolate them.
- Throwaway repository: any folder with `git init` and a commit inside `$SB/repo`. A repo-local
  `user.name` and `user.email` are needed because the relocated `HOME` has no global git config
  [observed: with them, `git commit` works]. The `tests/` suite already follows this pattern
  (clean environment, repo-local identity, `SAE_CONFIG`/`SAE_STATE_DIR`/`CODEX_HOME` in a temp
  folder; tests/saetest.py `clean_env`, `Sandbox`), which is evidence the variables are the
  complete set.
- Upgrade fixture: the owner's current config is schema 2 without `easy`; in the sandbox
  `sae doctor` printed `! easy falls back to the mechanical cell ...` [observed]. A schema-1 config
  (`rungs`, level maps) would make `sae` exit 2 with the conversion text; no fixture of it was
  searched for outside tests.

**Confidence:** high.

### 5. Opening the session in a new Orca terminal

**Answer:** `orca terminal create --worktree <existing workspace> --title ... --command "bash
$SB/launch-claude.sh" --focus --json`, then `orca terminal close --terminal <handle> --tab` at the end.

**Evidence:**
- `orca terminal create [--worktree <selector>] [--title] [--command] [--focus] [--json]`: "Creates
  a visible terminal tab without switching focus when possible", `--command` runs "on startup", and
  it is "typed into whatever shell the host started" (`orca terminal create --help`, Orca skill
  guide `orca skills get orca-cli`) [primary].
- `orca agent launch` and `orca worktree create --agent` go through Orca's agent launch with the
  owner's agent settings, which this walkthrough must avoid; `terminal create` makes "a terminal
  for shells and commands" (same guide) [primary].
- A terminal opened by Orca inherits the owner's login shell and Orca-injected variables
  (`ORCA_*`, a profile pointer, `CLAUDE_CODE_PLUGIN_DIRS`, `CLAUDE_CONFIG_DIR`) [observed in
  `env`]; the launcher's `exec env -i` resets them.
- `terminal close --terminal <handle> [--tab]`; `--worktree <sel> --all` "stops every terminal
  process owned by that workspace" (`orca terminal close --help`): do not use it.
- An Orca agent in that tab will not report status to Orca, because the Orca variables are
  removed; expected, not a defect for this purpose (inference).

**Confidence:** medium (the Orca command was not run; the CLI help and guide were read).

### 6. Cleanup and never-touch

See the section "Cleanup, and what must never be touched" above. Key facts: the whole sandbox is
one folder; the only state outside it can be (a) a Keychain entry, if Claude `/login` was used,
(b) the Orca terminal tab, (c) a background viewer process (`sae view --stop`, which also lives
under `$SB/state`). An OAuth token minted by `claude setup-token` has no documented revoke
command; the docs say only that it lasts one year (unknown: revocation path; the owner can
check the account's authorised sessions in the claude.ai settings, not verified).

**Confidence:** medium-high.

## Options and tradeoffs

- Auth for Claude: token (repeatable, no Keychain write, but a one-year credential that is not
  revoked by cleanup) versus `/login` in the sandbox (the true first-run flow, revoked by
  `claude auth logout`, but a browser step each time and an unverified Keychain path under a
  relocated `HOME`). The owner chooses.
- Auth for Codex: fresh `codex login` (clean, one browser step) versus copying `auth.json`
  (documented, no step, possible refresh-token interference with the owner's login).
- Sandbox location: a short `/tmp/sae-wt.*` folder (socket-path friendly, removed on reboot
  or after a few idle days, so a walkthrough should not span days) versus a folder under
  `~/Library/Caches/` (survives, longer paths: the `tsx` IPC socket case from the task intent
  needs short paths).
- PATH: only `claude`, `codex`, `node`, `python3` plus `/usr/bin:/bin` (tight, nothing of the
  owner's tools; verification commands that need `pnpm` or `npm` must be added as symlinks) versus
  the full PATH (convenient, exposes `gh` whose token sits in the Keychain, so an agent could
  act as the owner on GitHub).
- Same sandbox for both harnesses (a cross-harness review needs both logged in under one
  `HOME`) versus one per harness (simpler cleanup, no cross-harness scenario).

## Risks

- Keychain under a relocated `HOME`: behaviour unverified for `/login`; the token path avoids it.
- Server-managed settings and organization policy follow the account, not the folder; a token
  from a managed organization would bring them in (docs: endpoint policy is a file or plist,
  server-managed settings are fetched "when the session authenticates with a qualifying
  credential"; https://code.claude.com/docs/en/agent-sdk/claude-code-features).
- Claude's first-run screens (theme, folder trust) will appear in the fresh config; they are the
  harness's, not the skill's. Pre-seeding them was not investigated.
- `claude.ai` account skills load for a signed-in account (skills page); the token mode does not
  fetch connectors, but whether it also skips account-synced skills is unknown. The launch
  environment sets `ENABLE_CLAUDEAI_MCP_SERVERS=false` for the `/login` mode.
- The token is visible in the session's environment to the agent's shell tools.
- The Claude binary self-updates by default; `DISABLE_AUTOUPDATER=1` is set so the walkthrough
  cannot replace the owner's installed binary (`~/.local/bin/claude` is a symlink target).
- Tests and fixtures in `tests/` never run a real harness, so there is no existing path that
  proves a real harness session under a relocated `HOME`.

## Open questions

1. Does `claude` under a relocated `HOME` accept `/login` (Keychain or file fallback)? One
   short interactive try answers it.
2. Does `CLAUDE_CODE_OAUTH_TOKEN` work with `claude auth status`/a session in the sandbox, and can
   the owner revoke it? Needs the owner to run `claude setup-token`.
3. Does Claude list the skill from `$CLAUDE_CONFIG_DIR/skills` in the session (`/status`, `/mcp`
   and the skills list are the expected checks; not run here)?
4. Does a Codex session list `$HOME/.agents/skills/shape-and-execute` with the relocated `HOME`?
5. Should the walkthrough helper be a real part of the repository (a `scripts/` or `tests/`
   tool) or stay a procedure in the task? Not answered by research.

## Implications for the spec

- A first-run walkthrough needs three relocated roots at once: `HOME`, `CLAUDE_CONFIG_DIR`,
  `CODEX_HOME`. Overriding only the variables `sae` reads (`SAE_CONFIG`, `SAE_STATE_DIR`) is
  not enough: APM, git, Codex skills and the harness login read `~`.
- `sae`'s own configuration surface is small and already testable: `SAE_CONFIG` or
  `XDG_CONFIG_HOME`, `worktrees.root` inside the config, `SAE_STATE_DIR`, `SAE_VIEWER`,
  `CLAUDE_CONFIG_DIR`, `CODEX_HOME`. A harness-permission check (the task's second problem) that
  inspects `claude_settings_file()` and `codex_home()` will look at the sandbox's files, not the
  owner's, under this setup, which is what a sandboxed first run needs.
- On macOS a Claude login cannot be copied between config directories; a spec line that says
  "copy credentials" is wrong for this machine. Token or fresh login only.
- The README's install command installs from the published default branch; testing a task
  branch needs a local-path install. The viewer, `sae` and setup are the same code in both cases.
- Do not run `sae` commands from the walkthrough against the owner's config. The setup flow
  writes `config.json` and may offer to edit `$CLAUDE_CONFIG_DIR/settings.json` and
  `$CODEX_HOME/config.toml` (setup.md step 5, setup_mode.py L543-L565); in the sandbox those are
  the sandbox's files.
- Public-repo rule: transcripts and logs of the walkthrough contain local paths and an account;
  keep them out of the task record, or sanitise them first.

## Follow-up questions
