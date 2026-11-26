---
status: done
summary: tests/tools/walkthrough/walkthrough.sh builds a relocated-HOME sandbox (fresh or upgrade), installs the skill with APM from a git export, checks isolation, opens the session in a new Orca terminal; clean removes it all.
validation: pass
changes: made
resolved: []
---

# Result: FIRST-RUN-WALKTHROUGH

## Commands for the owner
Run them from a checkout of the task branch (the tool exports committed files at `HEAD`):

```bash
tests/tools/walkthrough/walkthrough.sh start fresh      # Claude, no sae config
tests/tools/walkthrough/walkthrough.sh start upgrade    # Claude, config from before the easy column
#   add --codex for a Codex session; --no-orca prints the launch command instead
tests/tools/walkthrough/walkthrough.sh clean            # both sandboxes, or: clean fresh|upgrade
```

In the new terminal: Enter at the login prompt starts Claude, where you log in with `/login`
(or `t` for the `setup-token` path). Then type `/shape-and-execute <rough note>`. When the
tab opens in the wrong Orca workspace, pass `--orca-worktree <selector>`.

## Validation evidence
- `bash -n tests/tools/walkthrough/*.sh`: passes.
- `start fresh --no-orca` (Claude and `--codex`): `claude auth status`/`codex login status`
  say "Not logged in"; `sae doctor` shows `✗ config <sandbox>/home/.config/shape-and-execute/config.json missing`;
  every path it prints is under `/private/tmp/sae-walkthrough/`; the skill is installed only
  at `<sandbox>/home/.claude/skills/shape-and-execute` (Codex: `<sandbox>/home/.agents/skills/...`),
  `apm.yml` points to the export inside the sandbox, and the installed copy matches the export
  (`diff -rq`, checked by the tool).
- `start upgrade --no-orca`: doctor prints `! easy falls back to the mechanical cell (claude: 6 of 6 cells) ...`;
  with `--codex` the same line for codex, and all three families resolve from the catalog.
- `start upgrade` with Orca: the tab opened and showed the launcher's login prompt (no session
  started); `clean` closed that tab (status `exited`), deleted the sandbox and the root folder;
  no process with `sae-walkthrough` in its command line was left.
- Guards: a symlinked scenario folder, a symlinked root, a folder without `env.sh` and a
  scenario `../x` are all refused; the symlink target stayed intact.
- `python3 tests/run.py test_retired_terms test_record_privacy`: OK.

## Decisions taken
- [agent] Sandboxes live at `/tmp/sae-walkthrough/{fresh,upgrade}` (short path for sockets),
  both scenarios can coexist; a repeated `start` replaces its scenario.
- [agent] `--codex` means the session runs in Codex; only the session's harness is on the
  sandbox PATH. The upgrade config then keeps only that harness's part and the review provider
  is that harness, as the old proposal did when a CLI was missing. Otherwise doctor shows a
  failure for every Codex family in a Claude walkthrough.
- [agent] Claude login: Enter runs Claude for an in-session `/login`; when `claude auth status`
  says logged out after that session, the launcher says so and offers the token path.
- [agent] The tool never calls `security`: `claude auth logout` in the sandbox removes a
  `/login` entry (keyed by the sandbox's config folder). `clean` prints a command the owner can
  run to confirm no Keychain entry is left.
- [agent] `upgrade-config.json` is a static fixture, built once from the tables in
  `3892f20:.../setup.md`. Values the proposal leaves open: every level balanced, English, 3
  writers, 600 s verify timeout.

## Risks
Not proven (each needs a logged-in session):
- whether `/login` keeps a login under the relocated HOME, and whether the token fallback works;
- whether Claude lists the skill from `$CLAUDE_CONFIG_DIR/skills` and Codex lists it from
  `~/.agents/skills` in the session;
- `codex login` inside the sandbox;
- the setup conversation itself.

Expected noise: Codex sessions show `✗ Codex subagent cap: not set` (the sandbox has no
`~/.codex/config.toml`; setup offers to set it). Claude shows its own first-run screens
(theme, folder trust). A `setup-token` token lasts a year and `clean` does not revoke it.

## Findings filed
- task/.tasks/findings/2026-11-26-1202--sae-doctor-names-only-the-claude-setup-c.md
