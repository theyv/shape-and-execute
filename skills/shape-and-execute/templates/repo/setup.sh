#!/usr/bin/env sh
# Prepares a fresh task or job worktree. sae runs it after `git worktree add`.
# sae runs git with hooks off: put dependency installs here, not in a git hook.
# cwd: the new worktree. Env: SAE_REPO_ROOT, SAE_WORKTREE, SAE_TASK,
# SAE_JOB (`task` for the task worktree).
# A non-zero exit stops the dispatch (or `sae start`). Keep it fast and idempotent.
set -eu

# Examples — keep what fits this repository:
# pnpm install --frozen-lockfile --prefer-offline
# uv sync --frozen
