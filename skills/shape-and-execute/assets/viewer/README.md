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
| `settings.css` / `settings.js` | the settings card, the settings dialog, saving through the server |

Classic scripts in this order: `app.js`, `task-views.js`, `settings.js`. They share their
top-level names; `app.js` boots on `DOMContentLoaded`, when all three are loaded. No build step,
no ES modules, no CDN, no web fonts, no external requests.

## How it is used

- `sae view [<task>] [--open]` starts the server or reuses the running one and prints
  `http://127.0.0.1:<port>/#repo=<key>&task=<id>&tab=plan`. `sae new` prints the same link.
- Reads: `GET /api/projects`, `/api/repo?repo=K`, `/api/task?repo=K&task=ID`,
  `/api/settings?repo=K[&task=ID]`, `/api/file?…` (prototype files). The server reads every
  worktree and `.tasks/done/` at each request; no data files are generated. Each answer has a
  `version`; the page re-renders only when it changes.
- Writes: `post(route, body)` in `app.js` sends `POST /api/<route>` with the token in
  `X-SAE-Token`; the server answers with the command's `--json` output (`ok`, `result`, `error`).
  Routes are `WRITE_ROUTES` in `server.py`; a new one is one entry there.
- Polling: every 3 s while the open repository has an executing task, else every 30 s; paused
  while the tab is hidden.
- UI state lives in the URL hash (`#repo=…&task=…&tab=…&job=…`); small conveniences (theme,
  open sections) in `localStorage`, every access in `try`/`catch`.

## Rules for changing it

- The data shape comes from `repo_data`, `task_data` and `settings_data` in `server.py`; computed
  values (routing, review marks, planned reviews, the ready list) come from the same functions as
  the CLI. Do not recompute them in the page.
- Colors of models, tiers and efforts come only from the palette in `app.js` (`modelColor`,
  `tierColor`, `effortWord`, `routeWords`) and the tokens in `app.css`: fixed and discrete, a
  model by its place in the model list, a tier by its number, `ultra` as `max` underlined.
- No model names or config values in these files.
- Dark theme first, light theme as a second token set on `:root[data-theme=light]`. Status is
  never shown by colour alone: every status pill carries a glyph and a label.
