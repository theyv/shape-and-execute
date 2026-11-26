---
status: done
confidence: medium
---

# Research: CODEX-LAUNCH

Scope is Codex CLI 0.169.0, release commit `d32063f96c2dff1dc96af839b3952abb6acfeda4`.
Local checks used macOS, the installed binary, Git 2.56.0 and a fresh temporary
`CODEX_HOME` without credentials. Zero model calls. [primary] [Release](https://github.com/openai/codex/releases/tag/rust-v0.169.0), [installed CLI checks](#5-model-free-capability-probe).

## Answers

### 1. Config profile and launch precedence

**Answer**

Use `codex exec -p shape-and-execute -C "$job_worktree" --ephemeral --json -`
to read the job prompt from stdin. The file `$CODEX_HOME/shape-and-execute.config.toml`
can set `default_permissions`, define the named permission profile and set `[agents]`.
Interactive `codex -p shape-and-execute -C "$job_worktree"` uses the same overlay.
Specify model, effort and `-o` independently if the route needs them.

**Evidence**

- [primary] Exec and the TUI both pass the profile file to the loader. The overlay
  wins over base user config. Trusted project config, session `-c` overrides, legacy
  managed config and managed requirements can affect the result. A same-named
  legacy `[profiles.NAME]` table or `profile = "NAME"` selector in the base config
  is a load error. [Exec](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/lib.rs#L376-L402), [TUI](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/main.rs#L2127-L2157),
  [layer order](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/loader/README.md#L24-L46), [legacy profile conflict](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/loader/mod.rs#L293-L341).
- [primary] `-s` wins and selects the legacy policy. The profile file still loads,
  including the agent cap. When working with config keys alone, higher layers choose
  between `sandbox_mode` and `default_permissions`, with the named selector winning
  a tie. `-c 'default_permissions="shape-and-execute"'` explicitly selects the named
  profile in the session layer. Managed requirements can still reject or replace it.
  [Exec flag](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/lib.rs#L355-L367), [resolver](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/permission_config.rs#L34-L75),
  [managed fallback](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L5160-L5195).
- [primary] Locally `codex -p sae-network -C "$job" debug prompt-input 'No turn'`
  reported the profile's custom writable roots and enabled network. Adding
  `-s workspace-write` dropped those roots and reported restricted network.
  Adding `-s read-only` reported read-only with restricted network. See §5 for
  what a rendered prompt establishes.

**Confidence** High.

### 2. Setup snippet and corrected profile

**Answer**

The existing snippet is valid TOML and loads on 0.169.0. The only legacy key
in the snippet is `agents.max_threads`, an accepted alias for
`agents.max_concurrent_threads_per_session`. `description`, `extends = ":workspace"`,
`":workspace_roots"`, the scoped filesystem paths and the absolute extra root
are recognized. The problem is the targets of the Git rules. In a linked checkout
`.git` is a pointer file. `.git/hooks` and `.git/config` under that checkout
cannot protect the common Git directory. The snippet also inherits restricted
networking. [primary] [SaE snippet](../../../skills/shape-and-execute/scripts/sae_lib/setup_mode.py#L507-L529),
[profile schema](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/permissions_toml.rs#L111-L119),
[workspace inheritance](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/permissions.rs#L225-L244),
[scoped paths](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/permissions.rs#L646-L695),
[special paths](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/permissions.rs#L828-L847),
[cap alias](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/key_aliases.rs#L12-L25).

A corrected example for ordinary Git files refs follows. Substitute the absolute
SaE worktree root, common Git directory and job Git directory from §3. It grants
the common write locations for add/commit/merge and preserves reads elsewhere
in the common directory. [primary] [Git layout](https://git-scm.com/docs/gitrepository-layout),
[Codex path specificity and exact exceptions](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/protocol/src/permissions.rs#L1619-L1644).

```toml
default_permissions = "shape-and-execute"

[permissions.shape-and-execute]
description = "SaE workspace and local Git writes"
extends = ":workspace"

[permissions.shape-and-execute.filesystem]
"/absolute/sae/worktrees" = "write"
"/absolute/main/.git/objects" = "write"
"/absolute/main/.git/refs" = "write"
"/absolute/main/.git/logs" = "write"

[permissions.shape-and-execute.filesystem.":workspace_roots"]
".git" = "read"
".codex" = "read"
".agents" = "read"

[permissions.shape-and-execute.filesystem."/absolute/main/.git/worktrees/job"]
"." = "write"
"commondir" = "read"
"gitdir" = "read"
"config.worktree" = "read"

[agents]
max_concurrent_threads_per_session = 10
```

**Evidence**

- [primary] With a temporary home, `codex exec --strict-config -p original -C "$job" --ephemeral --json </dev/null`
  reached the missing prompt error. The no-turn prompt renderer showed an extra
  write grant for the checkout's `.git` file and no explicit common Git grant.
  The permission resolver applies the built-in workspace's filesystem rules and
  starts a custom profile with restricted networking. [Workspace parent](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/permissions.rs#L225-L244),
  [network compilation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/permissions.rs#L457-L518).

**Confidence** High for the schema and target paths. Medium for OS enforcement of
the corrected example pending the probe in §5.

### 3. Linked worktree Git writes

**Answer**

Run these read-only queries on the target worktree.

```sh
git -C "$job_worktree" rev-parse --absolute-git-dir
git -C "$job_worktree" rev-parse --path-format=absolute --git-common-dir
```

- [primary] `git add` needs the per-worktree index and its lock plus the shared
  object store. `git commit` needs the per-worktree index/reflog and shared objects,
  branch refs, reflogs and their locks. A detached commit updates the per-worktree
  `HEAD`. Retain write access to the directories containing these files so Git
  can create locks and rename them.
- [primary] `git merge` also needs the checked-out files and per-worktree merge
  state, for example `ORIG_HEAD` and `MERGE_HEAD`. A merge commit writes shared
  objects and updates the current branch ref and reflog. Fast-forward alone tests
  fewer operations. Git resolves linked worktree state separately from shared
  objects and refs. [Git worktree details](https://git-scm.com/docs/git-worktree#_details),
  [repository layout](https://git-scm.com/docs/gitrepository-layout),
  [merge](https://git-scm.com/docs/git-merge#_true_merge).
- [primary] The checkout's `.git` pointer, common `config` and `hooks`, and
  per-worktree `config.worktree`, `gitdir` and `commondir` can remain read-only
  for these operations. A configured `core.hooksPath` can point elsewhere.
  Read-only hooks can still execute and may need their own runtime permissions.
  Reftable, submodules, custom hooks, ref packing, GC, worktree creation and
  removal can require different paths or operations. [Git config](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corehooksPath),
  [worktree configuration](https://git-scm.com/docs/git-worktree#_configuration_file),
  [ref storage](https://git-scm.com/docs/git-init#Documentation/git-init.txt---ref-formatltformatgt).
- [primary] Codex can also protect the resolved `gitdir:` target automatically,
  including under a writable temp directory. An explicit rule at the exact
  resolved per-worktree admin path suppresses that default carveout. Granting
  only its common parent can leave the child read-only. [Runtime projection](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/protocol/src/permissions.rs#L1619-L1644),
  [default carveouts](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/protocol/src/permissions.rs#L1709-L1724),
  [macOS linked worktree test](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt_tests.rs#L2970-L3030).

**Confidence** High for the standard Git layout and policy construction.

### 4. TCP, Unix sockets and Internet

**Answer**

- [primary] For a legacy workspace-write launch, `[sandbox_workspace_write] network_access = true`
  requests enabled shell networking. For a custom named profile, use
  `[permissions.shape-and-execute.network] enabled = true`. Default for the custom
  profile is restricted. These enable network at the sandbox policy layer.
  Managed proxy requirements can limit the resulting access. [Legacy translation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/permission_config.rs#L80-L102),
  [named policy](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/permissions.rs#L532-L544),
  [network preparation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/network_config.rs#L89-L127).
- [primary] On macOS, the full-network Seatbelt branch grants broad inbound and
  outbound access. The explicit listener and pathname socket rules are separate.
  In the managed proxy branch, configure `allow_local_binding = true` under the
  profile's `network` table for TCP bind and loopback traffic. For pathname IPC,
  add `"/absolute/short/ipc-dir" = "allow"` under
  `[permissions.shape-and-execute.network.unix_sockets]` and give the process
  filesystem write access for the bind. The generated Seatbelt rules cover
  `AF_UNIX` creation, bind and connect under the allowed path. For a local
  user-configured proxy, set `features.network_proxy = true` as well as
  `network.enabled = true`. Allow rules alone do not start the proxy. Proxy
  internet access depends on its domain rules and the client using it.
  [Seatbelt socket rules](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt.rs#L158-L187),
  [bind/connect and full-network branches](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt.rs#L266-L365),
  [proxy feature gate](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/network_config.rs#L89-L109),
  [domain rules](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/network-proxy/README.md#L35-L81).
- [primary] macOS `codex sandbox --allow-unix-socket "$ipc"` can explicitly
  allow a path even with restricted network and no proxy. This diagnostic flag
  changes the policy of that invocation. `codex exec` has no corresponding flag.
  Treat success with this option as a diagnostic of the missing socket grant.
  A writable temp path or `network.enabled = true` alone does not establish
  that an exec job can bind the tsx IPC socket. The actual direct-mode macOS
  bind and IPC results are unknown in this research environment. [CLI flag](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/lib.rs#L89-L102),
  [macOS no-proxy test](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt_tests.rs#L1597-L1629),
  [exec CLI](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/cli.rs).
- [primary] Linux 0.169.0 uses bubblewrap with seccomp for filesystem-restricted
  execution. The legacy Landlock switch is rejected for these policies. With
  restricted networking, seccomp blocks `bind`, `listen` and `connect` even
  when creating `AF_UNIX` sockets is permitted. An unnamed socketpair can
  therefore pass while tsx fails. Full network without a managed proxy uses
  the host network namespace and permits ordinary TCP and Unix IPC, subject
  to filesystem permissions and the host. Managed proxy mode has an isolated
  loopback and allows IP sockets inside that namespace. It blocks standalone
  `AF_UNIX` sockets unless the managed context allows all of them. A
  path-specific allowlist is a Seatbelt mechanism for native bind/connect.
  A TCP self-test inside the Linux namespace cannot establish access to a
  service on host `127.0.0.1`. [Linux backend](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/linux-sandbox/README.md#L41-L68),
  [proxy isolation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/linux-sandbox/README.md#L88-L101),
  [seccomp rules](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/linux-sandbox/src/seccomp.rs#L202-L269),
  [network mode selection](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/linux-sandbox/src/linux_run_main.rs#L430-L440).

**Confidence** High for the tagged policy branches. Medium for platform behavior
until verified on the target host and proxy configuration.

### 5. Model-free capability probe

**Answer**

`codex sandbox -p <overlay> -P <permission-name> --include-managed-config -C <job> -- <command>`
uses the platform sandbox and named policy without a model call. In 0.169.0
`-C` requires `-P` on this subcommand. `-P` is an explicit selector and without
`--include-managed-config` excludes managed requirements. To check the natural
selector from the file and runtime layers, run `codex sandbox -p <overlay> -- <command>`
with the process cwd set to the job. The latter defaults legacy-only configurations
to read-only unless given an explicit `-c sandbox_mode=...`. Keep probe and launch
selectors aligned when project config could override the overlay.
[primary] [CLI arguments](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/lib.rs#L52-L142),
[requirements handling](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/debug_sandbox.rs#L186-L202),
[selection and fallback](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/debug_sandbox.rs#L561-L664).

Run the following as a shell script from the main session outside an existing sandbox. It uses
a short temporary Unix socket path and creates an isolated Git repository.
The narrow read rule on the fixture root prevents the inherited temp write grant
from covering the common Git directory. Each capability reports independently.

```sh
set -eu
probe_dir="$(mktemp -d /tmp/sae-codex.XXXXXX)"
probe_dir="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$probe_dir")"
mkdir "$probe_dir/home" "$probe_dir/worktrees" "$probe_dir/ipc"
main="$probe_dir/main"
job="$probe_dir/worktrees/job"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
git init -q --ref-format=files -b main "$main"
git -C "$main" -c user.name=Probe -c user.email=probe@example.invalid \
  commit --allow-empty -qm base
git -C "$main" worktree add -qb sae-job "$job"
printf 'merge source\n' > "$main/merge-source.txt"
git -C "$main" add merge-source.txt
git -C "$main" -c user.name=Probe -c user.email=probe@example.invalid commit -qm source
common="$(git -C "$job" rev-parse --path-format=absolute --git-common-dir)"
gitdir="$(git -C "$job" rev-parse --absolute-git-dir)"

cat > "$probe_dir/home/sae-probe.config.toml" <<EOF
default_permissions = "shape-and-execute"

[permissions.shape-and-execute]
extends = ":workspace"

[permissions.shape-and-execute.filesystem]
"$probe_dir" = "read"
"$probe_dir/worktrees" = "write"
"$probe_dir/ipc" = "write"
"$common/objects" = "write"
"$common/refs" = "write"
"$common/logs" = "write"

[permissions.shape-and-execute.filesystem.":workspace_roots"]
".git" = "read"

[permissions.shape-and-execute.filesystem."$gitdir"]
"." = "write"
"config.worktree" = "read"
"commondir" = "read"
"gitdir" = "read"
EOF

cat > "$probe_dir/probe.py" <<'PY'
import socket
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
worktrees = root / "worktrees"
job = worktrees / "job"

def root_write():
    (worktrees / "outside-job.txt").write_text("probe\n")

def git(*args):
    subprocess.run(
        ["git", "-C", str(job), "-c", "user.name=Probe",
         "-c", "user.email=probe@example.invalid", "-c", "core.hooksPath=/dev/null",
         "-c", "gc.auto=0", *args], check=True,
    )

def git_commit():
    (job / "job.txt").write_text("writer\n")
    git("add", "job.txt")
    git("commit", "-qm", "writer")

def merge():
    git("merge", "-q", "--no-ff", "--no-edit", "main")

def round_trip(family, address):
    with socket.socket(family, socket.SOCK_STREAM) as server:
        server.settimeout(3)
        server.bind(address)
        server.listen(1)
        with socket.socket(family, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(server.getsockname())
            with server.accept()[0] as accepted:
                client.sendall(b"x")
                if accepted.recv(1) != b"x":
                    raise RuntimeError("missing probe byte")

def unix():
    sock_path = root / "ipc" / "p.sock"
    try:
        round_trip(socket.AF_UNIX, str(sock_path))
    finally:
        sock_path.unlink(missing_ok=True)

failures = 0
for name, check in (
    ("worktree-root-write", root_write),
    ("git-add-commit", git_commit),
    ("git-merge", merge),
    ("tcp-loopback", lambda: round_trip(socket.AF_INET, ("127.0.0.1", 0))),
    ("unix-socket", unix),
):
    try:
        check()
        print(f"PASS {name}", flush=True)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"FAIL {name}: {error}", flush=True)
        failures += 1
sys.exit(int(failures != 0))
PY

CODEX_HOME="$probe_dir/home" codex sandbox \
  -p sae-probe -P shape-and-execute --include-managed-config -C "$job" -- \
  "$(command -v python3)" "$probe_dir/probe.py" "$probe_dir"
```

**Evidence and expected output**

- [primary] The installed binary rejected `codex sandbox -p original -C "$job"`
  without `-P`. With `-P` and `--include-managed-config`, all nested Seatbelt
  attempts, including `/usr/bin/true` with the original and corrected variants,
  ended at `sandbox-exec: sandbox_apply: Operation not permitted` (exit 71).
  No probe child ran through nested Seatbelt. This is a sandbox startup failure,
  so the capabilities are unknown in that run. [Tag test recognizing the same failure](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt_network_tests.rs#L49-L61).
- [primary] The exact fixture ran through Git setup and failed at the same
  nested wrapper startup. Running the identical Python payload directly in
  a fresh fixture under the existing outer policy printed all five `PASS`
  lines. This validates the probe's setup and operations on this host.
- [primary] With the fixture profile above and a working sandbox, expect
  `PASS worktree-root-write`, `PASS git-add-commit` and `PASS git-merge`.
  Expect `FAIL tcp-loopback` and `FAIL unix-socket` when the default restricted
  policy applies. To test a macOS IPC-only diagnostic, rerun on a fresh fixture
  and add `--allow-unix-socket "$probe_dir/ipc"` before `--`. Expected result
  changes to `PASS unix-socket`. To test a writer profile with network grants,
  rerun on a fresh fixture with the applicable §4 settings. Expect `PASS`
  for each socket operation the resulting policy permits, subject to host
  support. Permission errors, timeouts and wrapper startup failures have
  different meanings. [Mac policy](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt.rs#L266-L365),
  [Linux policy](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/linux-sandbox/src/seccomp.rs#L202-L269).
- [primary] `codex -p <overlay> -C <job> debug prompt-input 'No turn'` can report
  Codex's rendered permission context before a model call. It does not execute
  the test. `codex sandbox` launches a child through the backend directly with
  no per-command grants or tool approval flow. It measures the tested OS
  operations at the tested paths under its resolved policy. It cannot establish
  exec tool rules, later approvals, remote executor parity, web search or the
  agent cap. A temp fixture also cannot establish permissions at a different
  repository path. [Prompt renderer](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/main.rs#L2125-L2194),
  [direct sandbox child](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/debug_sandbox.rs#L350-L438).

**Confidence** High for CLI syntax and startup observations. Medium for expected
results until the host probe runs.

### 6. Agent concurrency

**Answer**

`agents.max_concurrent_threads_per_session` reads from the merged configuration,
including the overlay. It counts spawned threads. `agents.max_threads` is the
legacy alias, normalized before layer merge. V1 defaults to six. V2 prioritizes
`features.multi_agent_v2.max_concurrent_threads_per_session`, which includes the
root, and otherwise converts the `[agents]` value by adding one. V2's default
is four including the root. A separate V2 override can make the value in the
profile's `[agents]` table ineffective.

**Evidence**

- [primary] With a base value of 3 and the overlay alias set to 0, both
  `codex exec -p` and interactive `codex -p` failed at config validation for
  `agents.max_concurrent_threads_per_session`. Exec with `-s workspace-write`
  failed the same way. [Alias](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/key_aliases.rs#L12-L55),
  [schema](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/config_toml.rs#L761-L773),
  [validation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L4134-L4146).
- [primary] V2 resolution gives the feature setting priority. The runtime
  subtracts one for spawned capacity. SaE currently reads the base file only.
  [Defaults](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L273-L275),
  [V2 resolution](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L2879-L2892),
  [runtime count](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L1771-L1784),
  [SaE cap check](../../../skills/shape-and-execute/scripts/sae_lib/setup_mode.py#L108-L126).

**Confidence** High.

### 7. Web search for research

**Answer**

Set top-level `web_search = "live"` in the overlay or pass
`codex exec -c 'web_search="live"' …`. `cached` is the default for a
sandboxed run absent other settings. `indexed` and `disabled` are also
recognized. The installed `codex exec --search --help` rejected `--search`.
The interactive `--search` maps to `live`. Built-in search uses the
Codex/provider tool path and does not require network permission for spawned
shell commands. Provider support, model availability and managed requirements
still apply. A shell fetch such as `curl` uses the shell network policy.

**Evidence**

- [primary] [Config resolution](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L2801-L2822),
  [default](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L4019-L4024),
  [turn/provider constraints](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L3214-L3258),
  [interactive flag mapping](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/main.rs#L2131-L2141),
  [provider web search tool](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/ext/web-search/src/extension.rs#L120-L167).

**Confidence** High for the flag and configuration. Provider access was untested.

### 8. Machine-readable records

**Answer**

No `codex exec --json` event reports effective sandbox mode, profile identity
or resolved permissions in 0.169.0. `thread.started` has only `thread_id`.
`command_execution` items carry command, output, exit code and status.
`turn.completed` carries usage. Warnings and model text are free-form.

**Evidence**

- [primary] The JSONL processor reduces internal configuration to the thread
  ID. Human-mode startup prints a sandbox summary. [JSONL schema](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/exec_events.rs#L8-L56),
  [command fields](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/exec_events.rs#L159-L166),
  [JSONL conversion](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L406-L410),
  [human summary](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/event_processor_with_human_output.rs#L441-L465).
- [primary] The separate app-server `thread/start` response exposes `sandbox`
  as a legacy projection and experimental `activePermissionProfile` as
  provenance. The standalone app-server CLI rejected `-p` locally, so it is
  not a direct preflight for the selected runtime overlay. Persistent
  `turn_context` records can carry `permission_profile` and
  `active_permission_profile`. `--ephemeral` disables persisted sessions.
  [App-server response](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/app-server-protocol/src/protocol/v2/thread.rs#L187-L218),
  [persistent context](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/protocol/src/protocol.rs#L3664-L3686),
  [exec options](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/cli.rs).

**Confidence** High.

## Options and tradeoffs

- [primary] Narrow Git grants cover the tested files-ref operations and keep
  shared hooks/config outside the writable set. A broader grant to the common
  and per-worktree Git directories can cover more Git operations. It also
  covers more shared metadata and requires explicit read-only children for
  hooks and config. [Git layout](https://git-scm.com/docs/gitrepository-layout),
  [Codex path carveouts](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/protocol/src/permissions.rs#L1709-L1740).
- [primary] Direct networking is broader and simpler to configure. Managed
  networking can restrict internet destinations and provide macOS local
  binding and socket grants, with different Linux namespace semantics.
  [macOS rules](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/sandboxing/src/seatbelt.rs#L305-L365),
  [Linux network isolation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/linux-sandbox/README.md#L88-L101).

## Open questions

- The actual OS probe results on the main macOS session and a Linux host are
  unknown. Run the fixture against the relevant platform settings, then check
  the real project's test command if it has a different socket path or needs
  a service outside the sandbox.
- The Git backend and verification requirements vary by repository. The
  specific Git write paths, socket directory, need for host-loopback access and
  need for internet access are inputs to a job's real capability check.

## Implications for the spec

- [primary] A writer launch that relies on a named profile requires its
  effective selector and resolved Git paths. `-s read-only` can still select the
  separate legacy review policy. A config filename alone establishes neither
  the runtime sandbox nor the agent limit. [Permission precedence](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/config/src/permission_config.rs#L34-L75),
  [V2 cap resolution](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/config/mod.rs#L2879-L2892).
- [primary] The dispatch command, the profile requested, the policy reported
  by a diagnostic and the capabilities tested are distinct facts. An
  `exec --json` log can provide a thread ID and usage, with no effective
  sandbox attestation. [JSONL events](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/exec/src/exec_events.rs#L8-L56),
  [sandbox probe implementation](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/cli/src/debug_sandbox.rs#L350-L438).

## Follow-up questions
