# Setup mode

Configure the user config and the repo profile. Run it when the user asks ("shape-and-execute
setup", "change model config"), or after `sae` exits with code 2 and the user agrees.

The skill holds no configuration values. Everything goes into the user config,
`~/.config/shape-and-execute/config.json`. `sae` reads only that file and fails loudly when
something is missing, so a copied skill never runs silently with someone else's models.

## 1. Look

Run `sae doctor` and `sae setup show`. They show what exists, which harness CLIs are installed,
the Codex catalog (families with their newest versions, older versions, efforts), the Codex
subagent cap and the default worktree root for this OS. With a config they print the model
lists, the tiers and one routing table per phase and harness.

A schema-1 config (rungs and level maps) makes `sae` exit 2. Then `sae setup show` prints the
proposed conversion: each rung becomes a tier, each cell points to the tier that the old level
map chose, and the model lists hold the models the rungs used. Claude rungs had no effort:
propose one per tier from the seed in step 3. Show it, save it after the user agrees (step 4),
and skip the guide.

## 2. Guide (first setup only)

Show this before the proposal, in the conversation language:

```
How models are chosen
- Each phase (research, planning, execution, review)
  has a level: economy, balanced or max.
- Each job has a difficulty: mechanical, normal or hard.
  Planning and review are never mechanical.
- A routing table per harness and phase maps
  level x difficulty to a model and an effort, directly
  or through a tier (L1-L4: one named model + effort).
- Change it any time, per phase: plan on max, execute
  on economy. The next dispatch uses the change.
- Where: tell me in the chat; `sae set` (one task);
  `sae project set` (this repository); the viewer
  (Task, Project, Global tabs); setup (global).
```

## 3. Propose — tables, one confirmation

This proposal is advice for you; `sae` never reads this text. Show each part as a small table.

**Model lists**, lightest to strongest (the order sets each model's color):

| harness | entries |
|---|---|
| Claude | haiku, sonnet, opus, fable — families (the newest of each); efforts low … max |
| Codex | luna, terra, sol, astra — families with the newest versions from `sae setup show`; older versions only picked from the catalog, never typed; efforts from the catalog (`ultra` only where listed) |

Drop a family the user does not want; it can be ticked on again later.

**Tiers** (model · effort):

| tier | Claude | Codex |
|---|---|---|
| L1 | sonnet · medium | luna · xhigh |
| L2 | opus · low | sol · low |
| L3 | opus · medium | sol · medium |
| L4 | opus · high | sol · high |

**Routing tables**, the same tiers for both harnesses, "tiers in cells" on:

| research, execution | mechanical | normal | hard |
|---|---|---|---|
| economy | L1 | L1 | L2 |
| balanced | L1 | L2 | L3 |
| max | L2 | L3 | L4 |

| planning, review | normal | hard |
|---|---|---|
| economy | L2 | L3 |
| balanced | L2 | L3 |
| max | L3 | L4 |

A cell may also hold its own model · effort, for example haiku for cheap mechanical work.

**Defaults for new tasks:** interaction mode `critical-only`; levels per phase; review points
`spec, plan, selected-jobs, integration` (a second model checks the spec against the intent
before the spec gate); review provider `cross-harness` (Codex reviews when Claude
orchestrates, Claude when Codex does).

**Also:** the conversation language and the artifact language; the worktree root (macOS
`~/Library/Caches/shape-and-execute/worktrees/`, Linux
`${XDG_CACHE_HOME:-~/.cache}/shape-and-execute/worktrees/`; a temporary folder also works,
since jobs commit their work); parallel writers, a cap such as 3.

Ask in the conversation language: "ok, or change something?"

## 4. Save

Build the schema-2 JSON from the skeleton or the conversion that `sae setup show` prints, and
pipe it to `sae setup save`. It validates the file, refuses an invalid model–effort pair, and backs up
the old one.

## 5. Harness permissions

`sae setup snippets` prints what each harness needs:

- **Codex:** a permission profile that lets git write `.git` (but keeps `.git/hooks` and
  `.git/config` read-only) and makes the worktree root writable. Without it, Codex blocks every
  commit and merge.
- **Codex subagent cap:** `[agents] max_threads`. By default a Codex session holds only 3
  subagents (6 on older models); parallel writers, reviews and research then fail with "agent
  thread limit reached". When `sae` reports fewer than 8, recommend 10 and offer to set it.
- **Claude Code:** the worktree root in `additionalDirectories`, and optional allow rules for
  `git` and the `sae` command for users who do not run with bypassed permissions.

Show each snippet, explain it in one sentence, and apply it only after the user says yes. Back
up the file first.

## 6. Verify

Run `sae doctor` again. Fix every ✗ together with the user.

## 7. Repo profile (once per repository)

At the first task in a repository, or when the user asks:

- `.tasks/repo/profile.md` (template `templates/repo/profile.md`): only what AGENTS.md and
  CLAUDE.md do not already say — validation commands (unit, typecheck, lint, end-to-end),
  known hot files, notes for worktree setup. Optional frontmatter pins: `artifact_language`
  (for a team) and `adr_folder` (where accepted decision records go).
- `.tasks/repo/setup.sh`: prepares a new task or job worktree, for example
  `pnpm install --frozen-lockfile`. Optional. `sae` runs its own git operations with hooks
  off, so a dependency install that a git hook does belongs here.
- `.tasks/repo/worktreeinclude`: ignored files to copy into each worktree, in gitignore syntax,
  for example `.env`.

Draft them from the repository, show them, write them after approval, then run
`sae doctor --repo`.

## Later changes

The same steps: show, propose, save, doctor; or the viewer's Global tab. Defaults and routing
for one repository: `sae project set` or the viewer's Project tab (personal, kept in the user
config).
