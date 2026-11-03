---
id: SHAPE-ROWS
covers: [SHAPE-ROW-READABILITY]
verify:
  - python3 tests/run.py test_viewer_server
  - python3 tests/run.py test_graph_cards
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/assets/viewer/**
  - tests/test_viewer_server.py
  - tests/test_graph_cards.py
  - tests/test_viewer_fixes.py
---

# SHAPE-ROWS: Readable research rows in the Shape card

## Objective
Research rows of the Shape card show label, model, effort and override mark without overlap.

## Inputs
- Spec: [SHAPE-ROW-READABILITY] in `specs.md`.
- Screenshots: `.tasks/backlog/assets/2026-10-16-shape-card-text-overlap.png` (in the repository)
  and `evidence/2026-10-29-shape-card-text-overlap.png` in this task folder (Research 3–5 overlap).
- Rows and the model label: `rowsOf`, `phaseCard` and `mlab` in
  `skills/shape-and-execute/assets/viewer/task-views.js`; styles in `task-views.css`.

## Scope
Fix the layout so that the reported case (five or more research rows, overrides active, long
model names) stays readable at the card width of the screenshots. Shortened text keeps the full
value in the tooltip. Add a regression test where the existing node-based viewer tests allow it.

## Boundaries
- No change to the server data or to routing.
- No redesign of the card; other cards keep their look.

## Expected output
A commit with the viewer fix and its test.

## Validation
- [ ] Rows without an override, review rows and keyboard focus on the model label still work.
