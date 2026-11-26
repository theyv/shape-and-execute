---
id: CLAUDE-LAUNCH
---

# CLAUDE-LAUNCH: Claude Code headless launch permissions for SaE jobs

## Objective
Settle the exact headless `claude -p` launch that `sae dispatch` must print for a Claude writer
job started by a Codex orchestrator, which settings give it the permissions it needs, and how
SaE can check them before dispatch. Decisions that wait on it: the COMMAND for cross-harness
writer jobs, what the viewer may write into Claude Code settings, and the pre-dispatch check.

## Questions
1. Which flags and settings let `claude -p` edit files, run any verify command, and run
   `git add/commit/merge` in a linked worktree under the SaE worktree root without prompts?
   Compare `--permission-mode` values (`acceptEdits`, `dontAsk`, `bypassPermissions`, others),
   `--allowedTools`, `--add-dir`, and the `permissions` block in settings files
   (`allow`, `additionalDirectories`, `defaultMode`). Which is least broad but sufficient?
2. Settings precedence: user, project, local and managed settings files, plus `--settings
   <file-or-json>` on the command line. Can a SaE-owned settings file be passed per launch
   (like a Codex profile), so the user's global `settings.json` stays untouched? Does
   `CLAUDE_CONFIG_DIR` change which user settings file is read?
3. Claude Code sandboxing (the `sandbox` settings block, if present in current versions): does it
   apply to `claude -p`? Does it block local Unix sockets, 127.0.0.1 ports or network, and
   which keys allow them?
4. Can the effective permissions be tested without a model call? If not, what is the cheapest
   reliable probe, and what can it not prove?
5. Machine-readable output: with `--output-format json` or `stream-json`, which fields report
   the permission mode, denied tool calls, token usage and the session ID?
6. A Codex orchestrator that launches `claude -p`: does it need the Codex sandbox to allow
   anything for the child (network to the API, writes to the Claude config dir)? Which Codex
   settings make that work?

## Already known
- Today `sae dispatch` prints a launch COMMAND only for a review in the other harness
  (`skills/shape-and-execute/scripts/sae_lib/prompts.py`, `external_review_command`):
  `claude -p <prompt> --output-format json --model <m> --effort <e> --permission-mode dontAsk
  --allowedTools 'Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(git show *)'`.
- `sae setup snippets` (`setup_mode.py`, `cmd_setup_snippets`) recommends merging into the
  user's Claude settings: `additionalDirectories: [<worktree root>]` and allow rules
  `Bash(git *)`, `Bash(python3 <sae.py> *)`, `Edit(/<root>/**)`.
- The user may run several Claude Code accounts with separate config dirs; do not assume
  `~/.claude`.

## Limits
- Primary sources: official Claude Code docs (code.claude.com / docs.anthropic.com), the CLI's
  `--help`, and local experiments with the installed CLI. Mark each claim `[primary]` or
  `[secondary]` with the version it holds for.
- Do not change the user's Claude or Codex configuration. Experiments use a scratch folder.
  At most one cheap model call, and only if a question cannot be settled otherwise; say so.
- Do not design SaE changes. Report facts, options and tradeoffs.

## Follow-up questions
