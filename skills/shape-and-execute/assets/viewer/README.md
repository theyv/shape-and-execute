# assets/viewer/

The viewer of the shape-and-execute skill: a small web app that the **viewer server** inside
`sae` serves (`scripts/sae_lib/server.py`). It shows every task of every repository where `sae`
has run, and changes settings only through the server, which runs the `sae` commands (the Project
Stakes save calls the profile writer instead; see "Project settings").

## Files

| File | Holds |
|---|---|
| `index.html` | the shell; the server fills in `<meta name="sae-token">` |
| `app.css` | tokens (dark and light), layout, shared components, the fixed palette |
| `app.js` | data loading, palette, tabs, sidebar, Markdown, project switcher, events, boot |
| `task-views.css` / `task-views.js` | the Plan graph and the other task tabs (`TAB.*`), the job panel |
| `settings.css` / `settings.js` | the Settings tab (Task, Project, Global), the Project settings section, the routing panel, the model lists, the editable header card; saving through the server |
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
  the layers.
- **Plan and Finish edges** come from the job graph, not the card graph, whose cycles hide them: Plan →
  every card that holds an entry job (no needs, planned before plan approval); every card that holds a
  terminal job (nothing needs it) → Finish, except a card outside a cycle that already has an edge out.
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
  the favicon is `favicon-wait.svg` (`signal()` in `app.js`). An active hold (a `waiting` reason of kind
  `hold`) turns frame and banner red ([WAIT-HOLD-FRAME]); the banner names the hold and the other waits
  and carries "Release hold". There is no separate hold bar.
- No status legend above the graph ([GRAPH-NO-LEGEND]): cards and rows say their status in words; the rule
  where a review lives is in the Integration card's tooltip, the added-after-approval fill in the tooltip of
  a filled card. The legend of kinds and marks below the graph stays.
- Hover or keyboard focus on a card highlights its edges (`gvHi`, `gvLinks`); the highlight survives
  a refresh.
- **Dropped jobs** ([JOB-DROP]): status `dropped` is final, like `done` (`isFinal` in `app.js`). A
  dropped card and its rows are faded and dashed, with the ID struck through and the pill "⊘ dropped";
  the card has no verdict badge. Counts ("n / m done" in the step bar, the Overview and the sidebar)
  leave dropped jobs out of both numbers and show them on their own. The job panel shows the
  `drop` record (`{group, reason, was, at}`) and the jobs dropped with it; the final report lists each
  dropped group.
- **Routing exceptions** ([HARNESS-FALLBACK]): the server sends `routing_exceptions`
  (`launch.routing_exceptions`, each with its `text` from `launch.exception_text`). A card whose job has
  one gets the mark "⇄ routing exception" on line 4 (requested route, actual route and reason in its
  tooltip); the job panel lists them.

## The header and the Overview

- The task's title and phase are in the top bar only (`renderTop()`, [HEADER-TOP-BAR]). Below it the
  page has the settings card (`headerCard()`, `settings.js`), "All settings" and "?". The ask signal is
  in the Settings tab only ([ASK-SETTING-TEXT]).
- `slimHead()` draws the step bar (Shape → Plan → Execute n/m → Finish, from `steps`) and the key
  stats on the Plan tab, below the graph and above "Next up". The terminal-style process map stays in
  the CLI (`sae status`) only.
- The Overview starts with the branch and the task worktree (`whereLine()`), then the KPI row, "Needs
  you", the stats per phase ([OVERVIEW-STATS-FIRST]), the merge checks and the risks.
- **Server data**: `phase_stats` (`session_tokens.phase_stats`: one row per phase with main-session
  and subagent tokens, times, jobs and attempts; a running phase's `wall_s` is null, the page counts
  it from `started`) and `git_lines` (`server.git_lines`: `{added, removed, files}` of
  `git diff --shortstat` from the merge base of the base and the task branch to the task branch;
  null without a task branch).
- Tokens show the sum with the main session only when every started phase knows its main-session
  tokens; otherwise the subagent tokens, marked "subagents only".
- The settings card shows the `bypass` line of `sae status` when the task sends a writer job to the
  other harness ([NO-SANDBOX-VISIBLE], `launch.bypass_line`, served in `status`).
- **Park stories** ([PARK-STORY]): `status.park_stories` (`park_story.park_stories`, as `sae next --json`
  and `sae status --json`). `storyBox()` draws a story: the target, the rounds against the limit, the
  objective and first result, each round's findings with their suggested fixes, the fix jobs'
  summaries and "do not" limits, and the options with copyable commands. It appears in the panel of a
  job parked at the round limit, in the panel of the integration round that parked the task, and in
  the Overview below "Needs you".

## The job panel

`jobBody()` in `task-views.js`: status, the drop record, routing exceptions, summary, needs and
reviews, the park story, the attempts, and **Launch commands** ([LAUNCH-RECORD]): for each attempt
with a `launch` record (`{harness, model, effort, command, request}`), the route, the request
("bypass requested" or "read-only requested") and the command with `<prompt>`, `<workdir>` and the
other placeholders. It records what the command requested, not the permissions the job had.

## Project settings

The Project tab of Settings starts with "Project settings", above "Defaults for new tasks in
<repo>" ([STAKES-VIEWER], [AMEND-2]). It shows the Project Stakes with their source and a "?" whose
help (`HELP.stakes`) holds the example of `templates/repo/profile.md` word for word.

- **Server data**: `stakes` in the settings answer (`server.stakes_data`, from `stakes.find_stakes`):
  `{title, source, source_name, text, editable, profile, profile_name, base, draft}`. `editable` is
  true when the stakes come from the profile or no source has any; stakes from AGENTS.md or
  CLAUDE.md are read-only with "edit there". `draft` fills the edit box; `base` is the profile's
  section as the page read it.
- **Save**: `POST /api/stakes {repo, text, base}` (`server.save_stakes`, the one entry of
  `DIRECT_ROUTES`) calls `stakes.save_profile_stakes`: only the Project Stakes section of
  `.tasks/repo/profile.md` in the main worktree changes. It refuses (409) while AGENTS.md or
  CLAUDE.md is the source and when the section changed since `base`; a heading in the text is 400.
  The edit stays in `SX.stk` until Save or Discard, so a refresh keeps it and its caret.

## Findings and Decisions: this task or all

A switch ([SCOPE-TOGGLE], `S.sc`, `scope=all` in the hash; default "this task") filters both tabs, and
their counts follow it. A finding belongs to the task when its `source` names it, when the task's events
say it filed it (`finding.created`) or closed it (`finding.closed`), or when its `closed.md` outcome names
the task (the server's `closed_list`: `{date, stem, title, outcome, task, job}`). A decision-record draft
belongs to it when its `source` names it or an `adr.created` event of the task does. Decision jobs and
decision events are the task's own in both views.

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
  Routes are `WRITE_ROUTES` in `server.py`; a new one is one entry there. The one route that runs no
  `sae` command is `stakes` (`DIRECT_ROUTES`, see "Project settings").
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
