# assets/viewer/

The viewer of the shape-and-execute skill: a small web app that the **viewer server** inside
`sae` serves (`scripts/sae_lib/server.py`). It shows every task of every repository where `sae`
has run, and changes settings only through the server, which runs the `sae` commands.

## Files

| File | Holds |
|---|---|
| `index.html` | the shell; the server fills in `<meta name="sae-token">` |
| `app.css` | tokens (dark and light), layout, shared components, the fixed palette |
| `app.js` | data loading, palette, tabs, sidebar, Markdown, project switcher, events, boot |
| `task-views.css` / `task-views.js` | the Plan graph and the other task tabs (`TAB.*`), the job panel |
| `settings.css` / `settings.js` | the Settings tab (Task, Project, Global), the routing panel, the model lists, the editable header card; saving through the server |
| `favicon.svg` / `favicon-wait.svg` | the owner's icon (its dark half turns light under `prefers-color-scheme: dark`); the second with the dot of "waiting for the owner" |

Classic scripts in this order: `app.js`, `task-views.js`, `settings.js`. They share their
top-level names; `app.js` boots on `DOMContentLoaded`, when all three are loaded. No build step,
no ES modules, no CDN, no web fonts, no external requests.

## The Plan graph

`graph()` in `task-views.js` builds a card model (`graph().cards`), then draws it as SVG:

- **Cards**: the Shape card and the Plan card (phase cards), a job card per writer, validation,
  research or decision job, one Integration card, the dashed jobs placeholder before the plan exists,
  and the Finish card. Card IDs of their own start with `@` (`@shape`, `@plan`, `@jobs`,
  `@integration`, `@finish`).
- **Rows** below a card's separator: a job's review rounds and fix jobs (`--fix-of`), the integration
  rounds and their fixes, the shaping research and the spec review (Shape), the plan review (Plan).
  `homes()` says which card each job belongs to; edges of a row's job start or end at its card.
- **Feedback edges**: rows can close a cycle of cards that the job graph has not
  (A → REVIEW-A → CHECK → A-FIX-1 makes A ⇄ CHECK). Inside a cycle, an edge into the card that starts
  earlier in the job graph is a feedback edge (`fb`, dashed, drawn below the cards); it is left out of
  the layers and the Plan edges, and the card with the cycle's last job gets the Finish edge.
- **Server data**: `steps` (`control.map_steps`, the steps of the process map) and `finish`
  (`reviews.finish_readiness`: the gates of `sae finish`, without side effects). `planned_reviews`
  also holds the next round of a changes-required round while its fixes are open
  (`reviews.next_review_rounds`: `key` is the override key of every round, `like` the round whose
  routing it gets). `planned_planner` is `PLAN` while the planner job may still be added; its
  routing is served, and `sae job override <task> PLAN` sets its model.
- **Tuning**: sizes and character widths in `GC`, wheel and pinch rates in `GZR` (`task-views.js`);
  timings and strengths as `--g-*` on `:root` in `task-views.css`; colors (`--pass`, `--edge-hi`,
  `--frame-wait`, `--added-hatch`) in `app.css`.
- **Waiting for the owner** ([WAIT-FRAMES], [WAIT-TAB-TITLE]): the server sends `asks` (open asks, any
  phase) and `waiting` (one `{kind, job, text}` per reason, empty outside executing), both from
  `asks.owner_wait`. In executing, a card with a parked job or row, or named by an open ask, gets the red
  frame (`--frame-wait`); while `waiting` is not empty, the graph area gets the yellow pulsing frame
  (`--frame-ask`, `--g-wpulse`) and the banner `waitBanner()`, the title starts with "● Needs you" and
  the favicon is `favicon-wait.svg` (`signal()` in `app.js`).
- Hover or keyboard focus on a card highlights its edges (`gvHi`, `gvLinks`); the highlight survives
  a refresh.

## The header and the Overview

- Below the title, `slimHead()` draws the step bar (Shape → Plan → Execute n/m → Finish, from
  `steps`) and the key stats; the settings card (`headerCard()`, `settings.js`) follows. The
  terminal-style process map stays in the CLI (`sae status`) only.
- **Server data**: `phase_stats` (`session_tokens.phase_stats`: one row per phase with main-session
  and subagent tokens, times, jobs and attempts; a running phase's `wall_s` is null, the page counts
  it from `started`) and `git_lines` (`server.git_lines`: `{added, removed, files}` of
  `git diff --shortstat` from the merge base of the base and the task branch to the task branch;
  null without a task branch).
- Tokens show the sum with the main session only when every started phase knows its main-session
  tokens; otherwise the subagent tokens, marked "subagents only".

## How it is used

- `sae view [<task>] [--open]` starts the server or reuses the running one and prints
  `http://127.0.0.1:<port>/#repo=<key>&task=<id>&tab=plan`. `sae new` prints the same link.
- Reads: `GET /api/projects`, `/api/repo?repo=K`, `/api/task?repo=K&task=ID`,
  `/api/settings?repo=K[&task=ID]`. Prototype files: `/proto/<repo>/<task>/<path>` (sandboxed;
  the URL keeps the folder structure, so relative assets load). The server reads every
  worktree and `.tasks/done/` at each request; no data files are generated. Each answer has a
  `version`; the page re-renders only when it changes.
- Writes: `post(route, body)` in `app.js` sends `POST /api/<route>` with the token in
  `X-SAE-Token`; the server answers with the command's `--json` output (`ok`, `result`, `error`).
  The body names its `repo` (and `task`): the one the change was made for, captured when the
  owner made it, never the selection when a queued save leaves; `post` refuses a body without it.
  Routes are `WRITE_ROUTES` in `server.py`; a new one is one entry there.
- Polling: every 3 s while the open repository has an executing task, else every 30 s. A hidden
  tab keeps polling, slower (15 s and 60 s), so the title and favicon follow the task.
- UI state lives in the URL hash (`#repo=…&task=…&tab=…&job=…`); small conveniences (theme,
  open sections) in `localStorage`, every access in `try`/`catch`.

## Rules for changing it

- The data shape comes from `repo_data`, `task_data` and `settings_data` in `server.py`; computed
  values (routing, review marks, planned reviews, the ready list, each pending job's waiting
  reasons, active holds) come from the same functions as
  the CLI. Do not recompute them in the page.
- Colors of models, tiers and efforts come only from the palette in `app.js` (`modelColor`,
  `tierColor`, `effortWord`, `routeWords`) and the tokens in `app.css`: fixed and discrete, a
  model by its place in the model list, a tier by its number, `ultra` as `max` underlined.
- No model names or config values in these files.
- Dark theme first, light theme as a second token set on `:root[data-theme=light]`. Status is
  never shown by colour alone: every status pill carries a glyph and a label.
