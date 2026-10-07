#!/usr/bin/env sh
# Prepares a fresh job worktree. sae runs it after `git worktree add`.
# cwd: the new worktree. Env: SAE_REPO_ROOT, SAE_WORKTREE, SAE_TASK, SAE_JOB.
# A non-zero exit stops the dispatch. Keep it fast and idempotent.
set -eu

# Examples — keep what fits this repository:
# pnpm install --frozen-lockfile --prefer-offline
# uv sync --frozen
