---
id: EASY-DIFFICULTY
covers: [DIFF-EASY, EASY-UPGRADE]
verify:
  - test -f tests/test_easy_difficulty.py
  - python3 tests/run.py test_easy_difficulty test_routing test_model_config test_levels_premium test_review_rounds_setting test_viewer_server
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/common.py
  - skills/shape-and-execute/scripts/sae_lib/config.py
  - skills/shape-and-execute/scripts/sae_lib/routing.py
  - skills/shape-and-execute/scripts/sae_lib/planning.py
  - skills/shape-and-execute/scripts/sae_lib/findings.py
  - skills/shape-and-execute/scripts/sae_lib/setup_mode.py
  - skills/shape-and-execute/scripts/sae_lib/doctor.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/control.py
  - skills/shape-and-execute/scripts/sae_lib/server.py
  - skills/shape-and-execute/scripts/sae_lib/cli.py
  - skills/shape-and-execute/assets/viewer/settings.js
  - skills/shape-and-execute/assets/viewer/settings.css
  - tests/test_easy_difficulty.py
  - tests/test_routing.py
  - tests/test_model_config.py
  - tests/test_levels_premium.py
  - tests/saetest.py
---

# EASY-DIFFICULTY: The fourth difficulty in sae and the viewer's routing tables

## Objective
Make `easy` a working difficulty for execution and research, with a visible fallback to the
`mechanical` cell where no configuration layer sets it.

## Inputs
- `specs.md` [DIFF-EASY], [EASY-UPGRADE], [DECISION-EASY-UPGRADE]; `brief.md` "Invariants".
- `scripts/sae_lib/routing.py` (`job_context`, `route`), `config.py` (layers, validation,
  `apply_routing_key`), `setup_mode.py` (`routing_tables_text`, `cmd_setup_save`).
- `assets/viewer/settings.js` (routing tables, `SXD`, `SXPD`, help texts).

## Scope
- `sae job add|edit --difficulty easy` for research and implementation-type jobs, and
  `sae decision new --difficulty easy` if decisions route through execution or research;
  refused for planning and review, with a message that names the allowed values.
- A review of a `mechanical` or `easy` job routes through the review table's `normal` cell.
- Routing tables: the `easy` column exists for execution and research only. `sae set
  routing.…easy=…`, `sae setup show` and `sae setup save` show and accept it there and refuse it
  elsewhere. Configurations without any `easy` cell stay valid in every layer.
- Fallback: when no layer sets the `easy` cell of a table, `easy` resolves to the effective
  `mechanical` cell. The dispatch header and the `sae next` card name that source. The nearest
  layer that sets `easy` wins, as for other cells.
- `sae status`, `sae doctor` and the viewer say in one line when `easy` falls back, with the
  fix: setup mode.
- The viewer's routing tables show and edit the `easy` column for execution and research.
- Help texts and error messages that named three difficulties name four.

## Boundaries
- `setup.md`, `planner.md`, `shape.md` and other prompt text: `PROMPT-TEXT`.
- `sae` writes no cell and no tier, and its code has no model names.
- `task_difficulty` stays `normal | hard`.
- Do not touch `prompts.py` (PROMPT-TEXT runs in parallel).

## Expected output
Code, viewer change and `tests/test_easy_difficulty.py`. In the result, name the server data
you added for the fallback line, if any.

## Validation
- [ ] Each acceptance item of [DIFF-EASY] and [EASY-UPGRADE] has a test, including: no `easy`
      cell → the effective `mechanical` cell, named on the card; a global `easy` cell and a
      task-level `mechanical` override → the global `easy` cell; tiers on and off.
- [ ] An existing configuration with three columns loads, validates and dispatches unchanged.
- [ ] The viewer's routing panel loads with and without `easy` cells (open it with `sae view`
      on a scratch config, or test the data the panel reads).
