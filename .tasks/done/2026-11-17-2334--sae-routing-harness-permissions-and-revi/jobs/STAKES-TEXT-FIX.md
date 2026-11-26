---
id: STAKES-TEXT-FIX
covers: [STAKES-POINTER]
verify:
  - python3 tests/run.py test_stakes test_dispatch_pointers test_retired_terms
  - "! grep -q 'rare edge cases' skills/shape-and-execute/scripts/sae_lib/prompts.py"
  - "! grep -q 'must deliver to be correct' skills/shape-and-execute/scripts/sae_lib/prompts.py skills/shape-and-execute/templates/repo/profile.md"
  - grep -q 'They never lower the requirements you were given' skills/shape-and-execute/scripts/sae_lib/prompts.py
scope:
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - skills/shape-and-execute/templates/repo/profile.md
  - tests/test_stakes.py
  - tests/test_dispatch_pointers.py
---

# STAKES-TEXT-FIX: The owner's final wording of the Project Stakes texts

## Objective
Replace `STAKES_LINE`, `STAKES_NOT_SET_LINE` and the profile template's "not set" line with the
owner's final wording below.

## Inputs
- `scripts/sae_lib/prompts.py`: `STAKES_LINE`, `STAKES_NOT_SET_LINE` (from `STAKES-IN-PROMPTS`).
- `templates/repo/profile.md`: the "Not set by the owner" line in the Project Stakes comment.
- `jobs/STAKES-IN-PROMPTS.result.md`: which tests assert these texts.

## Scope
Owner decision, 2026-11-20. Two changes to the texts that `STAKES-IN-PROMPTS` wrote:
1. No list of examples of what to leave out: what the bar needs depends on the stakes, so a
   list (tests, edge cases) misleads.
2. The bound is "They never lower the requirements you were given." It does not force the
   work through: a worker that cannot meet a requirement still parks, as its protocol says.

Exact texts, word for word (`{path}` as now):
- `STAKES_LINE`: `Project Stakes: how much care this project needs (from {path}, section "Project
  Stakes"). Work to this bar. Leaving out what the bar does not need is expected, not a failure.
  They never lower the requirements you were given:`
- `STAKES_NOT_SET_LINE`: `Project Stakes: how much care this project needs. Not set, so set the
  bar yourself: from the repository instructions and the README, judge who uses it, what
  breakage is acceptable and what matters now. Then work to that bar. Leaving out what the bar
  does not need is expected, not a failure. They never lower the requirements you were given.
  State your estimate in one line in what you write back.`
- Template line: `- Not set by the owner. Set the bar yourself from the repository instructions
  and the README. Leaving out what it does not need is expected; it never lowers the
  requirements you were given.` (keep the comment's line wrapping style).

Update the tests that assert the old texts.

## Boundaries
- No other prompt text, no code logic.

## Expected output
One commit; the result names the changed lines.

## Validation
- [ ] The three texts match the ones above word for word.
