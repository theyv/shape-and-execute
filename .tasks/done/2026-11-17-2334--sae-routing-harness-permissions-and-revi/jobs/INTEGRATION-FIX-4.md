---
id: INTEGRATION-FIX-4
covers: [SETUP-PROPOSAL, TIERS-FOLLOW-DIFFICULTY]
verify:
  - python3 tests/run.py test_model_config test_viewer_surfaces test_viewer_fixes test_retired_terms
scope:
  - skills/shape-and-execute/references/modes/setup.md
  - skills/shape-and-execute/scripts/sae_lib/setup_mode.py
  - skills/shape-and-execute/assets/viewer/**
  - tests/**
---

# INTEGRATION-FIX-4: The setup proposal follows AMEND-3

## Objective
Make the setup proposal, the guide and the viewer's mode switch match `specs.md` AMEND-3.

## Inputs
- `specs.md` `## Amendments`, AMEND-3 (all five points).
- `prototypes/setup-routing-owner.json`: the owner's tiers and the tier of every cell. Ignore
  the `changed` flags; take every value as given.
- `prototypes/setup-guide.md`: the guide text, word for word.
- `reviews/REVIEW-INTEGRATION.md` finding 4.
- `.tasks/adr/2026-11-20-routing-cells-keep-a-tier-and-an-own-mod.md` (draft, updated).

## Scope
- `setup.md` step 3: the tiers table and every routing table from the JSON. Cells show only
  the tier. Replace "Save both in every cell" with: cells carry only a tier; the first switch
  to Free mode copies the tier into each cell.
- `setup.md` step 2: the guide from `prototypes/setup-guide.md`.
- `setup.md` step 1 (upgrade of an existing config): AMEND-3 point 5.
- `setup.md` and the viewer: the two modes are named Tiers mode and Free mode, in the switch,
  its help text and any other user-facing text. The config key `tiers_in_cells` stays.
- `setup_mode.py`: if the skeleton or the conversion writes a model · effort into cells for
  the proposal, align it with AMEND-3. If it is only a placeholder, leave it.
- Check that every model and effort in the tables is in the proposal's model lists.

## Boundaries
- No change to how `sae` resolves routes (`config.py` `cell_use`) or to the config schema.
- Model names only in the setup proposal text and the Claude family list (decision record).
- A new problem becomes a finding.

## Expected output
Commits on the job branch; the result lists each AMEND-3 point with where it is done.

## Validation
- [ ] Every table in `setup.md` step 3 matches the JSON, cell by cell (a script check is fine).
- [ ] The guide in step 2 is the prototype text.
- [ ] The viewer shows "Tiers mode" and "Free mode"; the switch still flips `tiers_in_cells`.
