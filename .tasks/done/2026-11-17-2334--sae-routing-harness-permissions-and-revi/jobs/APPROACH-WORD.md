---
id: APPROACH-WORD
covers: [APPROACH-CHECK]
verify:
  - python3 tests/run.py test_fix_loop_guidance test_dispatch_pointers
  - "! grep -q 'parks for the owner' skills/shape-and-execute/scripts/sae_lib/prompts.py"
scope:
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - tests/**
---

# APPROACH-WORD: "user" in APPROACH_PARAGRAPH

## Objective
In `APPROACH_PARAGRAPH` (`scripts/sae_lib/prompts.py`), change "parks for the owner" to "parks for
the user", and update the tests that assert it.

## Inputs
- `jobs/FIX-LOOP-TEXTS.result.md`, "Decisions taken": why this was left for the owner.

## Scope
Owner decision, 2026-11-22: the fix-loop texts use "user" for the human. Only this word.

## Boundaries
- No other text or code changes.

## Expected output
One commit; the result names the changed line.

## Validation
- [ ] The rest of `APPROACH_PARAGRAPH` is unchanged.
