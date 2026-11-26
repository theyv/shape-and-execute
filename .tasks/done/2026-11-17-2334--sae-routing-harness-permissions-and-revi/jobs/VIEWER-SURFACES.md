---
id: VIEWER-SURFACES
covers: [STAKES-VIEWER, LAUNCH-RECORD, HARNESS-FALLBACK, NO-SANDBOX-VISIBLE, PARK-STORY, JOB-DROP]
verify:
  - test -f tests/test_viewer_surfaces.py
  - python3 tests/run.py test_viewer_surfaces test_viewer_server test_owner_ui_changes test_graph_cards test_viewer_fixes test_header_overview test_wait_signals test_sidebar_tabs
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/scripts/sae_lib/asks.py
  - skills/shape-and-execute/assets/viewer/**
  - tests/test_viewer_surfaces.py
  - tests/test_viewer_server.py
  - tests/test_graph_cards.py
  - tests/saetest.py
---

# VIEWER-SURFACES: The viewer shows stakes, launches, exceptions, park stories and dropped jobs

## Objective
Show the task's new data in the viewer and let the owner edit the profile's stakes in a new
"Project settings" section.

## Inputs
- `specs.md` [STAKES-VIEWER], [LAUNCH-RECORD], [HARNESS-FALLBACK], [NO-SANDBOX-VISIBLE],
  [PARK-STORY], [JOB-DROP].
- The results of `STAKES-IN-PROMPTS`, `WRITER-LAUNCH`, `FIX-LOOP-EXITS` and `FIX-LOOP-GUIDANCE`:
  the functions, state fields and events they added for the viewer.
- `templates/repo/profile.md`: the stakes example the help must show.
- `assets/viewer/README.md`; `server.py` (`task_data`, `settings_data`, `run_write`, routes);
  `settings.js` (Project tab); `task-views.js` (cards, job panel, waiting rows).

## Scope
- Project tab: a new first section "Project settings" above "Defaults for new tasks in <repo>".
  It shows the Project Stakes (the name from `[AMEND-2]`, also in labels and help) and their source. Stakes from the profile are editable and saved, after
  the owner presses Save, through a server route that calls the profile writer. Stakes from
  AGENTS.md or CLAUDE.md are read-only with "edit there". A "?" help explains what stakes are,
  how SaE uses them (reviewers grade findings and note `[beyond Project Stakes]`; planners and workers
  size their work), the template's example, and that hard limits do not belong there.
- Job view: each COMMAND attempt's launch record, with the word "requested"; a mark on jobs
  with a routing exception (requested route, actual route, reason).
- The settings card: the bypass line when `sae status` shows it.
- A parked job, and the parked task, show the park story.
- Dropped jobs appear as dropped in cards, rows, lists and counts, and count as final.
- `assets/viewer/README.md` names the new server data and the new section.

## Boundaries
- No backend logic beyond reading and serving data and the one save route; a missing backend
  function parks the job.
- Prompt text: `PROMPT-TEXT`. The routing tables' `easy` column: done in `EASY-DIFFICULTY`.
- The save writes only the Stakes section of `.tasks/repo/profile.md` in the home checkout.

## Expected output
Server and viewer changes, `tests/test_viewer_surfaces.py`, the README update.

## Validation
- [ ] Tests for the served data, the save route (only the Stakes section changes; AGENTS.md
      and CLAUDE.md sources are refused), and the rendering of each surface where the existing
      node-based viewer tests allow it.
- [ ] Open the viewer on a scratch task (`sae view`) and check each surface in light and dark
      mode; record what you checked in the result.
- [ ] The help example matches the template's example word for word.
