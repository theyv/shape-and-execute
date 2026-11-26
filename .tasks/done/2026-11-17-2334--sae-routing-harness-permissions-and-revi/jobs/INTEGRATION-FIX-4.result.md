---
status: done
summary: setup.md, the skeleton of `sae setup show` and the viewer switch follow AMEND-3 (owner's tiers, tier-only cells, Tiers mode | Free mode, new guide, upgrade rule)
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-4

Commit `0a32d07` on the job branch.

## AMEND-3, point by point
1. **Tiers:** `setup.md` step 3 tiers table = `prototypes/setup-routing-owner.json` `tiers` (Codex L1 terra · high).
   Its lead sentence now says only execution has one tier per difficulty at balanced (research does not, in the owner's table).
2. **Cells:** all 8 routing tables in step 3 show only the tier, as in the JSON `cells`. The "Save both in every cell"
   paragraph now says that cells carry only a tier and that the first switch to Free mode copies the tier's model · effort into each cell.
   The Codex catalog rule now replaces a missing family "in the tiers" only, not "in the tiers and the cells".
   `setup_mode.py` `config_skeleton`: cells are now `{"tier": "<L1-L4>"}`. The old `model`/`effort` placeholders were removed (see Decisions).
3. **Names:** the viewer switch is a radio segment "Tiers mode | Free mode" (`data-act="sxtic"`, still flips `tiers_in_cells`). The tiers help
   and the status line use the names. `sae setup show` prints `Tiers mode (tiers_in_cells on)` or `Free mode (tiers_in_cells off)`.
   `setup.md` has no "tier mode" or "tiers in cells" left. The config key is unchanged.
4. **Guide:** step 2 is the code block of `prototypes/setup-guide.md`, byte for byte (script check: `True`).
5. **Upgrade (step 1):** the proposal includes the new tiers and the step-3 tier for every cell. A cell's own model · effort stays,
   and the `easy` cells get one tier each. It also says that in Tiers mode the routes follow the new tiers and that in Free mode
   the existing cells keep their routes.

## Validation evidence
- Verify: `python3 tests/run.py test_model_config test_viewer_surfaces test_viewer_fixes test_retired_terms`: 36 tests OK.
- Nearby: `test_routing test_easy_difficulty test_viewer_server test_owner_ui_changes test_adr_rules test_levels_premium test_sidebar_tabs`:
  80 tests OK (1 skipped). Smoke test OK.
- One-off script against the JSON: 8 tiers and 72 cells match `setup.md` cell by cell, and the 72 table cells equal the 72 JSON cells.
- New tests:
  - `test_model_config.SetupProposalTest`: every cell is L1–L4. The proposal built from `setup.md` passes `validate_config`,
    and every tier model · effort is in its model list. The guide names both modes, and the skeleton cells carry only a tier.
  - `SetupShowModeTest`: the mode line in both modes.
  - `test_viewer_fixes.RoutingModeSwitchTests`: node renders and clicks the switch. Global: Free mode sets `tiers_in_cells` false
    and copies the tier into the cells, a second click on Free does nothing, and Tiers mode switches back.
    Project: the click posts `tiers-in-cells.claude=off` and the cell copies.
  - Mutation checks: the tests fail with `terra · ultra` in the tiers table and without the click guard.
- `test_retired_terms`: "tiers in cells" is a retired term.

## Decisions taken
- [agent] The skeleton's `"model": "<model, used when tiers are off>"` was a placeholder, but `sae setup show` says "fill every <...>".
  That invites an own model · effort in every cell, against AMEND-3 point 2, so the skeleton cell now holds only the tier.
- [agent] Upgrade of a config already in Free mode: each new `easy` cell also gets its tier's model · effort. A tier-only cell has no route
  in Free mode, and `sae setup save` would refuse it. This does the same copy as the first switch to Free mode.
- [agent] The switch is a two-option segment (the existing `sxSeg`), not a toggle labeled with one name, so both mode names are visible.
  A click on the mode already shown is ignored. The unused `.tgl` CSS was removed.
- [agent] `tiers in cells` is a retired term, with an allowance for `config.py`, which is out of scope (finding below).

## Risks
- None known. The guide drops the old "Where: `sae set` / `sae project set` / viewer tabs" line because the prototype text is word for word.

## Findings filed
- ~/Library/Caches/shape-and-execute/worktrees/shape-and-execute-3f2d3e60/2026-11-17-2334--sae-routing-harness-permissions-and-revi/task/.tasks/findings/2026-11-26-1155--two-sae-error-messages-still-name-the-ol.md
