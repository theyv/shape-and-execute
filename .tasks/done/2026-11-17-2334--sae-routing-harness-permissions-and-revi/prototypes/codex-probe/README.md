# Codex sandbox probe

Model-free probe of a Codex permission profile, run by the main session outside any sandbox
on macOS with Codex CLI 0.169.0 (2026-11-18). Based on the probe in
[CODEX-LAUNCH](../../research/CODEX-LAUNCH.md#5-model-free-capability-probe), changed to bind
the Unix socket by a relative path (short `sun_path`) and to add an internet check.

`make.sh <dir> <extra.toml>` builds a main checkout, a linked job worktree and a profile file
with narrow Git grants (common `objects`, `refs`, `logs`; the job's per-worktree Git dir), then
appends `extra.toml`. Run:

    CODEX_HOME=<dir>/home codex sandbox -p sae-probe -P shape-and-execute \
      --include-managed-config -C <dir>/worktrees/job -- python3 probe.py <dir>

## Results

| Variant | root write | git add/commit | git merge | TCP loopback | Unix socket | internet |
|---|---|---|---|---|---|---|
| `none.toml` (no network keys) | PASS | PASS | PASS | FAIL | FAIL | FAIL |
| `net.toml` (`network.enabled = true`) | PASS | PASS | PASS | PASS | PASS | PASS |
| `local.toml` (`allow_local_binding`, `unix_sockets` allow, no proxy) | PASS | PASS | PASS | FAIL | FAIL | FAIL |
| `net.toml` without the Git grants | PASS | FAIL | FAIL | – | – | – |
| `net.toml` without Git grants in the file, Git grants passed as one `-c 'permissions.shape-and-execute.filesystem={...}'` inline table | PASS | PASS | PASS | PASS | PASS | PASS |

Findings:

- The narrow Git grants are enough for add, commit and a `--no-ff` merge in a linked worktree.
- Without network, TCP loopback and Unix sockets fail. This matches the tsx IPC failure.
- On macOS without a managed proxy, the local-only keys have no effect. Only
  `network.enabled = true` opens loopback and Unix sockets, and it also opens the internet.
- Repository-specific Git paths can stay out of the profile file: a per-launch `-c` inline table
  merges with the file's filesystem table. A dotted `-c` key with a quoted path is rejected.
- `codex sandbox` fails to start inside another Seatbelt sandbox (`sandbox_apply: Operation not
  permitted`), so the probe must run from an unsandboxed process.
