# assets/viewer/

`index.html` is the static viewer of the shape-and-execute skill: one page that shows every task
of a repository (phase, plan graph, jobs, timeline, reviews, decisions, intent and spec, findings)
and what waits for the user.

## How it is used

- `sae` copies `index.html` to `.tasks/.viewer/index.html` when the copy is missing or older, and
  writes `data/index.js` and `data/<task-id>.js` next to it after every mutating command.
- `sae view [<task>] [--open]` renders everything and prints the `file://` URL.
- The page needs no server. It loads the data as classic scripts and re-injects them every 3 s
  while a task is executing (30 s otherwise, paused while the tab is hidden). Browsers that block
  this degrade to a manual reload.
- UI state lives in the URL hash (`#task=<id>&tab=plan&job=<ID>`), so a reload keeps the view.

## Rules for changing it

- One self-contained file: inline CSS and JS, no CDN, no web fonts, no external requests,
  no ES modules (`file://` blocks them). Keep it lean (about 90 KB today).
- Bump `<meta name="sae-viewer-version" content="N">` whenever the file changes in a way users
  should get, so `sae` replaces older copies. The data shape comes from `render_viewer`,
  `build_index` and `build_task_data` in `scripts/sae.py`; "ready" mirrors `waits_for`.
- The page is read-only except for this task's `settings.json`. Chromium browsers write it
  through the File System Access API (the user picks the `.tasks` folder once; the handle is kept
  in IndexedDB). Every control also has **Copy command** (`sae set <task> key=value`), which is
  the only way in Safari and Firefox.
- Dark theme first, light theme as a second token set on `:root[data-theme=light]`. Status is
  never shown by colour alone: every status pill carries a glyph and a label.
