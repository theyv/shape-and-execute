---
status: done
summary: Project Stakes texts now use the owner's final wording; tests updated.
validation: pass
changes: made
resolved: []
---

# Result: STAKES-TEXT-FIX

Commit 9ac7326 on the job branch.

## Changed lines
- `skills/shape-and-execute/scripts/sae_lib/prompts.py`: `STAKES_LINE` and `STAKES_NOT_SET_LINE` (example list removed; "They never lower the requirements you were given").
- `skills/shape-and-execute/templates/repo/profile.md`: the "Not set by the owner" line in the Project Stakes comment (lines 24-26).
- `tests/test_stakes.py`: the template-line assertion (old "never leave out ... must deliver" text) and a new assertion on the shared wording in both prompt constants (also checks no "edge cases").

## Validation evidence
- `python3 tests/run.py test_stakes test_dispatch_pointers test_retired_terms`: OK, 49 tests.
- The three `grep` verify commands: pass.
- The texts match the job file word for word (the job file's line wraps are joined with single spaces).

## Decisions taken
- [agent] Wrapped the Python strings at the file's existing width; the rendered text has the exact single-line wording.
