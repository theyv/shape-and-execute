---
id: SANDBOX-ISOLATION
covers: []
verify: []
---

# SANDBOX-ISOLATION: How to run a first-run walkthrough of SaE in isolation

## Objective
Recommend one way to give the owner a first-run experience of the skill, on this Mac, without
the owner's own setup leaking in, with exact commands.

## Inputs
- `research/CLAUDE-LAUNCH.md` and `research/CODEX-LAUNCH.md` (how harness CLIs are launched).
- The repository README (how a new user installs the skill) and `skills/shape-and-execute/
  references/modes/setup.md` (what a first setup does).
- `skills/shape-and-execute/scripts/sae_lib/config.py`: where `sae` reads its config
  (`XDG_CONFIG_HOME`) and the worktree root.
- Primary documentation of Claude Code (settings sources, `CLAUDE_CONFIG_DIR`, skill locations,
  plugins) and Codex (`CODEX_HOME`, skills). Prefer official docs over blog posts.

## Scope
The walkthrough has two scenarios: a fresh install (no `sae` config) and an upgrade (a copy of
an older config). It runs in a new Orca terminal (`orca` CLI) so the owner talks to the agent
directly. Answer:
1. How to start Claude Code so that it loads only the skill from the task branch: not the
   owner's global skills, CLAUDE.md, hooks, output style or plugins, while it stays logged in
   (for example a separate config dir with copied credentials, a settings-source flag, or a
   bare mode). Name what each option keeps and what it drops.
2. The same for Codex, if it is cheap; else say what it would take.
3. How to install the skill the way a new user would (from the README), into the sandbox only.
4. How to isolate `sae` state: config, worktree root, the throwaway repository.
5. How to open the session in a new Orca terminal.
6. Cleanup: what to delete afterwards, and what must never be touched.

## Boundaries
- Read only. Do not change any config of the owner (`~/.claude*`, `~/.ccs`, `~/.codex`,
  `~/.config/shape-and-execute`, APM files), and do not launch a harness session.
- Running `--help` of a CLI is fine.

## Expected output
`research/SANDBOX-ISOLATION.md`: the recommended approach first, exact commands, then the
options compared, risks, and sources with links.

## Validation
- [ ] Each claim about a CLI flag or env variable names its source (docs link or `--help`).
