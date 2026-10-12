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

**Model lists**, lightest to strongest (the order sets each model's color). Every entry is a
family (the newest version of it), switched on:

| harness | family | efforts |
|---|---|---|
| Claude | sonnet | low, medium, high, xhigh, max |
| Claude | opus | low, medium, high, xhigh, max |
| Codex | luna | low, medium, high, xhigh, max |
| Codex | sol | low, medium, high, xhigh, max, ultra |
| Codex | astra | low, medium, high, xhigh, max, ultra |

Drop a family the user does not want; it can be ticked on again later. Other families (for
example haiku, fable, terra) and older Codex versions can be added; pick Codex versions from the
catalog of `sae setup show`, never type them.

**Codex against the catalog.** Without a Codex catalog in `sae setup show`, leave the Codex
part (model list and routing) out. With one:
- Keep only the efforts that the catalog lists for the family's newest version.
- A seed family missing from the catalog is replaced, in the tiers and the cells, by the
  nearest stronger family that is there (luna → sol → astra), else the nearest weaker one; drop
  its entry. Keep each effort when the new model's list has it, else take the nearest effort in
  that list (the stronger on a tie). Effort order: low, medium, high, xhigh, max, ultra.

**Tiers** (model · effort):

| tier | Claude | Codex |
|---|---|---|
| L1 | sonnet · medium | luna · xhigh |
| L2 | opus · medium | sol · low |
| L3 | opus · high | sol · medium |
| L4 | opus · xhigh | sol · high |

**Routing tables**, "tiers in cells" on. Each cell is tier · model · effort: the tier applies
while tiers in cells is on, the model · effort when the user turns it off. Save both in every
cell.

| claude · research | mechanical | normal | hard |
|---|---|---|---|
| economy | L1 · sonnet · medium | L1 · sonnet · medium | L2 · sonnet · high |
| balanced | L1 · sonnet · medium | L2 · sonnet · high | L3 · opus · low |
| max | L2 · sonnet · high | L3 · opus · low | L4 · opus · medium |

| claude · execution | mechanical | normal | hard |
|---|---|---|---|
| economy | L1 · sonnet · medium | L1 · sonnet · high | L2 · opus · low |
| balanced | L1 · sonnet · high | L2 · opus · medium | L3 · opus · high |
| max | L2 · opus · low | L3 · opus · high | L4 · opus · xhigh |

| claude · planning | normal | hard |
|---|---|---|
| economy | L2 · sonnet · high | L3 · opus · medium |
| balanced | L3 · opus · high | L4 · opus · xhigh |
| max | L4 · opus · xhigh | L4 · opus · xhigh |

| claude · review | normal | hard |
|---|---|---|
| economy | L1 · sonnet · high | L2 · opus · medium |
| balanced | L2 · opus · medium | L3 · opus · high |
| max | L3 · opus · high | L4 · opus · xhigh |

| codex · research | mechanical | normal | hard |
|---|---|---|---|
| economy | L1 · luna · high | L1 · luna · xhigh | L2 · sol · low |
| balanced | L1 · luna · xhigh | L3 · sol · medium | L4 · sol · high |
| max | L3 · sol · medium | L4 · sol · high | L4 · sol · xhigh |

| codex · execution | mechanical | normal | hard |
|---|---|---|---|
| economy | L1 · luna · xhigh | L1 · luna · xhigh | L2 · sol · low |
| balanced | L2 · sol · low | L3 · sol · medium | L4 · sol · high |
| max | L3 · sol · medium | L4 · sol · high | L4 · sol · xhigh |

| codex · planning | normal | hard |
|---|---|---|
| economy | L2 · sol · low | L3 · sol · medium |
| balanced | L4 · sol · high | L4 · sol · xhigh |
| max | L4 · sol · xhigh | L4 · sol · max |

| codex · review | normal | hard |
|---|---|---|
| economy | L2 · sol · low | L3 · sol · medium |
| balanced | L3 · sol · medium | L4 · sol · high |
| max | L4 · sol · high | L4 · sol · xhigh |

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
pipe it to `sae setup save`. It validates the file, refuses an invalid model–effort pair and a
Codex exact version or effort that the catalog does not offer, and backs up the old one.

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
  known hot files, notes for worktree setup. Optional frontmatter pin: `artifact_language`
  (for a team).
- Ask once where decision records go, and write the answer into the profile:
  - one flat folder: `adr_folder: docs/adr` (no answer: an existing ADR folder, else
    `docs/decisions/`);
  - rules per path: `adr_rules`, one ADR rule `<path prefix> -> <folder>` per item, for
    example `- skills/billing/ -> docs/adr/billing/`. `sae adr accept` uses the rule with the
    longest prefix that matches the draft's `applies-to`; with no match, the flat folder.
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
