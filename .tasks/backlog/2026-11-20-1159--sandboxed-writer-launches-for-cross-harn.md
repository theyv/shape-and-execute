# Intent: Sandboxed writer launches for cross-harness jobs

## Problem

Task 2026-11-17-2334 makes `sae dispatch` print a launch command for writer jobs routed to the
other harness. [human] For now that command runs without a sandbox (Codex
`--dangerously-bypass-approvals-and-sandbox`, Claude Code `--permission-mode bypassPermissions`).
SaE is at an early stage, and a permission setup adds complexity that the owner does not want yet.
Only the hard stops in the instructions and the worktree isolation limit a writer.

The sandboxed variant was researched and partly tested during that task:

- [CODEX-LAUNCH](../2026-11-17-2334--sae-routing-harness-permissions-and-revi/research/CODEX-LAUNCH.md):
  `codex exec -p <profile>` layers a SaE-owned profile file on the user config; `-s` overrides it.
  Linked worktrees need write grants on the common Git dir (`objects`, `refs`, `logs`) and the
  job's per-worktree Git dir; the current `sae setup snippets` rule `.git = write` does not work
  there.
- [CLAUDE-LAUNCH](../2026-11-17-2334--sae-routing-harness-permissions-and-revi/research/CLAUDE-LAUNCH.md):
  `claude -p --settings <file>` is a per-launch overlay; a model-free handshake reports the
  effective permission mode and settings.
- [Codex probe](../2026-11-17-2334--sae-routing-harness-permissions-and-revi/prototypes/codex-probe/README.md):
  on macOS only `network.enabled = true` opens loopback ports and Unix sockets (and the
  internet); repository-specific Git grants can be passed per launch with `-c`; the probe must
  run outside another sandbox.

## Goal

Offer a sandboxed launch for writer jobs in both harnesses, check its capabilities before
dispatch, and show the result in the viewer.

## Related tasks

Builds on 2026-11-17-2334--sae-routing-harness-permissions-and-revi — start after it is merged.

## Open questions

- Network for writers: full network, or a managed proxy with local-only rules?
- When the probe runs (doctor, viewer, `sae start`), and what "unverified" means for dispatch.
- What the viewer may write, and whether overlays or the user's global settings carry the rules.
- `sae setup snippets` gives a Git rule that does not work in linked worktrees: fix or remove it.
- The Claude review COMMAND is not strictly read-only: under `dontAsk`, write approvals inherited
  from user or project settings still apply (spec review of 2026-11-17-2334, finding 1).
