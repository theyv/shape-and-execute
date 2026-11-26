---
status: done
summary: easy is a fourth difficulty for execution and research; with no easy cell in any layer it uses the effective mechanical cell, and sae and the viewer name that fallback
validation: pass
changes: made
resolved: []
---

# Result: EASY-DIFFICULTY

## Validation evidence
- `test -f tests/test_easy_difficulty.py`: passes.
- `python3 tests/run.py test_easy_difficulty test_routing test_model_config test_levels_premium test_review_rounds_setting test_viewer_server`: 61 tests OK.
- Smoke `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: OK.
- Nearby modules (test_control, test_viewer_fixes, test_owner_ui_changes, test_retired_terms, test_output_plain, test_graph_cards, test_reviews, test_record_privacy): 79 tests OK.
- How each item is tested in `tests/test_easy_difficulty.py`:
  - [DIFF-EASY]: `job add` accepts easy for research and implementation and refuses it for planning (on add and on edit), with "takes --difficulty normal or hard". `decision new --help` lists easy. A review of an easy job dispatches on the review `normal` cell. `sae set` and `sae project set` accept `easy` in execution and research and refuse it in planning and review. `setup save` refuses an easy cell in the review table.
  - [EASY-UPGRADE]:
    - With no easy cell, the job runs on the effective mechanical cell. `sae next` and the card say "· mechanical cell", and the dispatch ROUTING line says "(no easy cell: uses the mechanical cell; fix: setup mode)".
    - A task-level mechanical cell is the fallback when no layer sets easy.
    - A global easy cell plus a task-level mechanical override uses the global easy cell.
    - Tiers on and off are tested, both with and without easy cells.
    - `sae status` (text and the `routing_notice` JSON field), `sae doctor` (a `!` line) and `setup show` (the easy column, `= mechanical` in fallback cells, the same line) all show the fallback.
  - Three-column configuration: `config_for` has no easy cells, and every existing test still loads, validates and dispatches with it. `setup save` accepts it.
  - Viewer: a node run of `sxRouting` on the real `/api/settings` answer, for Project and Global, with and without easy cells. It checks the easy column, the fallback line, "uses the mechanical cell", that planning and review easy cells show "not used", and that `sxBad()` is 0.

## Decisions taken
- [agent] The fallback works when sae reads the config (`config.effective_cell`, `FALLBACK_COLUMNS = {"easy": "mechanical"}`). Validation never requires an easy cell, even in the global config, and `sae` writes no cell.
- [agent] `resolve_model` and `route` return a new key, `fallback` (`"mechanical"` or None). The dispatch header, `short_text` (cards, `sae next`) and the settings snapshot show it. The first card after this change lists the new easy routing rows as a settings change.
- [agent] Server data for the fallback line: none added. The viewer works out the line from the effective `routing` tables it already gets, so the Global draft shows it too. `sae status --json` has a new `routing_notice` field.
- [agent] A schema-1 conversion proposes no easy cells: the old level maps had none. Setup mode fills the column.
- [agent] In tier mode the empty easy cell's select shows "= mechanical (Lx)". With tiers off it shows "— not set —". Picking a value sets the easy cell on that level.
- [agent] `sae doctor` checks only the global routing. `sae status` checks the task's merged routing (global, project and task).

## Risks
- The test that the old error message was "never mechanical" (`tests/test_routing.py`) now expects "Planning takes --difficulty normal or hard, not mechanical". No prompt text names the old message.
