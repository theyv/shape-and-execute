# Setup mode

Configure the user config and the repo profile. Run it when the user asks ("shape-and-execute
setup", "change model config"), or after `sae` exits with code 2 and the user agrees.

The skill holds no configuration values. Everything goes into the user config,
`~/.config/shape-and-execute/config.json`. `sae` reads only that file and fails loudly when
something is missing, so a copied skill never runs silently with someone else's models.

## 1. Look

Run `sae doctor` and `sae setup show`. They show what exists, which harness CLIs are installed,
the Codex model list (when Codex is installed) and the default worktree root for this OS.

## 2. Propose — one compact block, one confirmation

- **Rungs per harness.** L1 = a solid mid model, L2 = a strong model, L3 = the strongest model
  (with high reasoning where the harness allows it). Never the lightest models.
  - Claude Code: model aliases that your Agent tool accepts. Reasoning effort cannot be set per
    dispatch, so Claude rungs hold a model only.
  - Codex: model IDs from `codex debug models`, each with an `effort`.
- **Level map.** Suggested starting table (`sae` never reads this text; only the config
  counts):

  | level | mechanical | normal | hard |
  |---|---|---|---|
  | economy | L1 | L1 | L2 |
  | balanced | L1 | L2 | L3 |
  | max | L2 | L3 | L3 |

  Review level map: economy → L2, balanced → L2, max → L3.
- **Languages:** the conversation language and the artifact language.
- **Defaults for new tasks:** interaction mode, level per phase, review points, review
  provider. Propose `spec` among the review points: a second model checks the spec against the
  intent before the spec gate.
- **Worktree root:** macOS `~/Library/Caches/shape-and-execute/worktrees/`; Linux
  `${XDG_CACHE_HOME:-~/.cache}/shape-and-execute/worktrees/`. A temporary folder also works
  (ephemeral setup); jobs commit their work, so a lost worktree loses only uncommitted changes.
- **Parallel writers:** a cap, for example 3.

Ask in the conversation language: "ok, or change something?"

## 3. Save

Pipe the confirmed JSON to `sae setup save`. It validates the file and backs up the old one.

## 4. Harness permissions

`sae setup snippets` prints what each harness needs:

- **Codex:** a permission profile that lets git write `.git` (but keeps `.git/hooks` and
  `.git/config` read-only) and makes the worktree root writable. Without it, Codex blocks every
  commit and merge.
- **Claude Code:** the worktree root in `additionalDirectories`, and optional allow rules for
  `git` and the `sae` command for users who do not run with bypassed permissions.

Show each snippet, explain it in one sentence, and apply it only after the user says yes. Back
up the file first.

## 5. Verify

Run `sae doctor` again. Fix every ✗ together with the user.

## 6. Repo profile (once per repository)

At the first task in a repository, or when the user asks:

- `.tasks/repo/profile.md` (template `templates/repo/profile.md`): only what AGENTS.md and
  CLAUDE.md do not already say — validation commands (unit, typecheck, lint, end-to-end),
  known hot files, notes for worktree setup. Optional `artifact_language` pin in the
  frontmatter, for a team.
- `.tasks/repo/setup.sh`: prepares a new worktree, for example
  `pnpm install --frozen-lockfile`. Optional.
- `.tasks/repo/worktreeinclude`: ignored files to copy into each worktree, in gitignore syntax,
  for example `.env`.

Draft them from the repository, show them, write them after approval, then run
`sae doctor --repo`.

A later change of model config follows the same steps: show, propose, save, doctor.
