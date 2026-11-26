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

A config without an `easy` column works: `easy` jobs use the `mechanical` cell, and `sae`
says so. To upgrade it, propose these changes, save them after the user's yes (step 4), and
skip the guide:
- the tiers of step 3;
- in every cell, the tier that step 3 shows there. A model · effort the cell already has
  stays: it is the user's data;
- the `easy` cells of step 3, a tier each. When the config is in Free mode
  (`tiers_in_cells` off), give each new `easy` cell its tier's model · effort as well, as the
  first switch to Free mode does.

Say that in Tiers mode the routes follow the new tiers, and that in Free mode every existing
cell keeps its route.

A schema-1 config (rungs and level maps) makes `sae` exit 2. Then `sae setup show` prints the
proposed conversion: each rung becomes a tier, each cell points to the tier that the old level
map chose, and the model lists hold the models the rungs used. Claude rungs had no effort:
propose one per tier from the seed in step 3. Show it, save it after the user agrees (step 4),
and skip the guide.

## 2. Guide (first setup only)

Show this before the proposal, in the conversation language:

```
### Task
- A task holds one or more goals that you state in its intent.
- It is split into jobs. A job is usually one objective that an
  agent can finish within one context window.

### Phases
A task goes through four phases:
> research, planning, execution, review

### Levels
Each phase has a level:
> economy, balanced or premium
Economy saves tokens. Premium buys quality.
The levels start from your defaults. You can change them for
each task; the agent asks about them while it shapes the task.

### Difficulties
Each job has a difficulty:
> mechanical, easy, normal or hard
The agent sets it when it plans the task.
Planning and review use only normal and hard.

## Model routing tables
- You can use different models for different difficulties.
- You can set a MODEL+EFFORT (cell) for every LEVEL (row)
  x DIFFICULTY (column), grouped by PHASE. You can edit the
  tables later in the GUI.
- Projects and tasks inherit the global tables. You can
  change them later per project or per task.

#### Two ways to set model routing
- Tiers mode (default, simpler): four named steps, L1 to L4,
  each one model + effort. A cell only points to a step.
  Change a step once, and every cell that points to it
  follows.
- Free mode: each cell has its own model + effort. Use it
  when four steps are too coarse and you want finer control.
- Tiers mode and Free mode are independent. Switch between
  them any time; a change in one never affects the other.
  Free mode starts as a copy of your tiers.

### Changing settings later
- You can change every setting in the GUI, or ask the agent
  to change it for you.
- Tip: phases can use different levels, for example "plan on
  premium, execute on economy." The next dispatch uses the
  change.
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
| Codex | terra | low, medium, high, xhigh, max |
| Codex | sol | low, medium, high, xhigh, max, ultra |
| Codex | astra | low, medium, high, xhigh, max, ultra |

Drop a family the user does not want; it can be ticked on again later. Other families (for
example haiku, fable) and older Codex versions can be added; pick Codex versions from the
catalog of `sae setup show`, never type them.

**Codex against the catalog.** Without a Codex catalog in `sae setup show`, leave the Codex
part (model list and routing) out. With one:
- Keep only the efforts that the catalog lists for the family's newest version.
- A seed family missing from the catalog is replaced, in the tiers, by the nearest stronger
  family that is there (luna → terra → sol → astra), else the nearest weaker one; drop its
  entry. Keep each effort when the new model's list has it, else take the nearest effort in
  that list (the stronger on a tie). Effort order: low, medium, high, xhigh, max, ultra.

**Tiers** (model · effort). They follow the difficulties: at the balanced level, each
difficulty of execution has its own tier.

| tier | difficulty | Claude | Codex |
|---|---|---|---|
| L1 | mechanical | sonnet · medium | terra · high |
| L2 | easy | sonnet · high | sol · medium |
| L3 | normal | opus · medium | sol · high |
| L4 | hard | opus · high | sol · xhigh |

**Routing tables**, Tiers mode (`tiers_in_cells` on). Cells carry only a tier, no model ·
effort of their own. The first switch to Free mode copies the tier's model · effort into each
cell, so the switch alone changes no route.

| claude · research | mechanical | easy | normal | hard |
|---|---|---|---|---|
| economy | L1 | L1 | L2 | L2 |
| balanced | L1 | L2 | L2 | L3 |
| premium | L2 | L2 | L3 | L4 |

| claude · execution | mechanical | easy | normal | hard |
|---|---|---|---|---|
| economy | L1 | L1 | L2 | L3 |
| balanced | L1 | L2 | L3 | L4 |
| premium | L2 | L3 | L3 | L4 |

| claude · planning | normal | hard |
|---|---|---|
| economy | L2 | L3 |
| balanced | L3 | L4 |
| premium | L4 | L4 |

| claude · review | normal | hard |
|---|---|---|
| economy | L1 | L2 |
| balanced | L3 | L4 |
| premium | L4 | L4 |

| codex · research | mechanical | easy | normal | hard |
|---|---|---|---|---|
| economy | L1 | L1 | L1 | L2 |
| balanced | L1 | L1 | L2 | L3 |
| premium | L1 | L2 | L3 | L4 |

| codex · execution | mechanical | easy | normal | hard |
|---|---|---|---|---|
| economy | L1 | L1 | L2 | L3 |
| balanced | L1 | L2 | L3 | L4 |
| premium | L2 | L3 | L3 | L4 |

| codex · planning | normal | hard |
|---|---|---|
| economy | L1 | L2 |
| balanced | L2 | L3 |
| premium | L3 | L4 |

| codex · review | normal | hard |
|---|---|---|
| economy | L1 | L2 |
| balanced | L2 | L3 |
| premium | L3 | L4 |

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

Writer jobs need git writes in their worktree and often local sockets for their checks. For
now SaE starts them with a bypass request:

- **Orchestrator session:** run it with full access (Claude Code: bypassed permissions;
  Codex: `codex --yolo`). Its subagents inherit it.
- **Jobs in the other harness:** `sae dispatch` prints a launch command without a sandbox.
- **Codex subagent cap:** `[agents] max_threads`. By default a Codex session holds only 3
  subagents (6 on older models); parallel writers, reviews and research then fail with
  "agent thread limit reached". When `sae` reports fewer than 8, recommend 10 and offer to
  set it.

A sandboxed setup waits in the backlog.

Show each change, explain it in one sentence, and apply it only after the user says yes.
Back up the file first.

## 6. Verify

Run `sae doctor` again. Fix every ✗ together with the user.

## 7. Repo profile (once per repository)

At the first task in a repository, or when the user asks:

- `.tasks/repo/profile.md` (template `templates/repo/profile.md`): only what AGENTS.md and
  CLAUDE.md do not already say — validation commands (smoke, full suite, unit, typecheck,
  lint, end-to-end), known hot files, notes for worktree setup. Optional frontmatter pin:
  `artifact_language` (for a team).
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
