# First-run walkthrough

Starts the skill from the current branch the way a new user meets it: in a throwaway `HOME`,
installed with the README's APM command, in a new Orca terminal. Use it to read the setup
guide, the setup proposal and the prompts after an upgrade as a user would.

```bash
tests/tools/walkthrough/walkthrough.sh start fresh            # no sae config: the skill starts setup
tests/tools/walkthrough/walkthrough.sh start upgrade          # a config from before the easy column
tests/tools/walkthrough/walkthrough.sh start fresh --codex    # the session runs in Codex
tests/tools/walkthrough/walkthrough.sh clean                  # delete every sandbox
```

In the session, type `/shape-and-execute <a rough note>` (Claude) or `$shape-and-execute <a
rough note>` (Codex).

## What `start` does

- Builds `/tmp/sae-walkthrough/<scenario>` (a short path: Unix socket paths are limited). A
  second `start` of the same scenario replaces it.
- Exports `skills/shape-and-execute` at `--ref` (default `HEAD`) with `git archive`: only
  committed files. After a change, commit and `start` again.
- Runs `apm install -g <export> --target claude` (or `codex`) with `HOME`,
  `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `XDG_*`, `SAE_STATE_DIR` and `TMPDIR` inside the sandbox,
  through `env -i`: nothing of your environment, settings, skills, plugins or logins comes in.
  `PATH` holds `/usr/bin`, `/bin` and links to `git`, `python3` and the session's harness (plus `node` for Codex).
- Creates a throwaway repository with one commit, and for `upgrade` writes
  `upgrade-config.json` with the sandbox's worktree root. Only the session's harness part of
  that config is kept, and the review provider is that harness.
- Checks the isolation: the harness is not logged in, and `sae doctor` prints no path of your
  `HOME`. Then it opens `launch.sh` in a new Orca terminal (`--orca-worktree <selector>`,
  default `active`), or prints the command when Orca is missing (`--no-orca`).

## Logging in

- Claude: Enter at the prompt runs Claude, and you log in with `/login`. When Claude is not
  logged in after that session, the launcher offers the fallback: run `claude setup-token` in
  a normal terminal and paste the token (hidden). The token lasts a year; `clean` does not
  revoke it.
- Codex: a fresh `codex login` into the sandbox's `CODEX_HOME`.

## What `clean` does

Closes the Orca terminal that `start` opened, stops the sandbox's viewer, runs `claude auth
logout` and `codex logout` in the sandbox (a `/login` Keychain entry is keyed by the sandbox's
config folder, so yours stay), and deletes the sandbox. It refuses any path that is not a
directory directly under `/tmp/sae-walkthrough`, a symlink, or a folder without the sandbox's
`env.sh`. After a `/login` it prints a command to confirm that no Keychain entry is left.

## `upgrade-config.json`

A schema-2 config built from the setup proposal before the `easy` column
(`git show 3892f20:skills/shape-and-execute/references/modes/setup.md`): its model lists, tiers
and routing tables, with tier, model and effort in every cell. Values the proposal leaves open:
every level `balanced`, English, 3 parallel writers, a 600 s verify timeout. When a later change
needs another "before" state, replace this file.
