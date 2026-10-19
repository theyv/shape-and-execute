---
id: INTEGRATION-FIX-1
covers: [WORKER-POINTERS, REVIEW-POINTERS, DIR-POINTERS]
verify: ["python3 tests/run.py"]
scope:
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - tests/
---

# INTEGRATION-FIX-1: Pointer matching handles glob scopes, top-level folders and renames

## Objective
Fix the three findings of the integration review in the pointer matching of `sae dispatch`.

## Inputs
- `reviews/REVIEW-INTEGRATION.md` in this task folder: findings 1, 2 and 3. Check each one
  before you act; list the ones you believe wrong under `## Disputed findings`.
- Spec: [WORKER-POINTERS], [REVIEW-POINTERS], [DIR-POINTERS], [POINTER-LIMIT].
- `jobs/DISPATCH-POINTERS.result.md`: how the matching was built.

## Scope
- Finding 1: a glob `scope` (for example `skills/x/scripts/**/*.py`) matches a record whose path
  entry is a folder the glob covers, and gets the `AGENTS.md` / `CLAUDE.md` lines of folders
  inside what the glob covers.
- Finding 2: the job-file fallback recognizes a single-component folder path ending in `/`
  (for example `src/`), for record and directory pointers.
- Finding 3: review matching uses both the source and the destination of a rename.
- Regression tests for all three in `tests/`.

## Boundaries
- No change to the pointer format, the limit, or which jobs get pointers.
- No change to `docs/adr/` or to the cleanup.

## Expected output
Commits on the job branch: the matching fixes and their tests.

## Validation
- [ ] `python3 tests/run.py` passes.
- [ ] A test fails without each fix.
