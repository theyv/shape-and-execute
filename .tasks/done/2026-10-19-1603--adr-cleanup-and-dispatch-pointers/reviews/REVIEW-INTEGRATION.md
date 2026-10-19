---
target: integration
verdict: changes-required
---

# Review: REVIEW-INTEGRATION

## Findings

### 1. Recursive scopes miss folder records and nested instructions — major
**Evidence:** `skills/shape-and-execute/scripts/sae_lib/prompts.py:96–98,125–130`.
**Affects:** [WORKER-POINTERS], [DIR-POINTERS].
**Why it matters:** Scope `skills/shape-and-execute/scripts/**/*.py` does not match a record guarding `skills/shape-and-execute/scripts/sae_lib/`. It also omits the existing `sae_lib/AGENTS.md`. Read-only calls reproduced both omissions. The comparisons treat the glob as a literal path, and instruction discovery stops before its first wildcard.
**Correction:** Match glob scopes against the folders they cover and collect the applicable nested instructions. Add regression tests for recursive scopes.

### 2. The fallback parser ignores top-level folder names — major
**Evidence:** `skills/shape-and-execute/scripts/sae_lib/prompts.py:75–78,99–102`.
**Affects:** [WORKER-POINTERS], [DIR-POINTERS].
**Why it matters:** `path_tokens("Change src/")` returns nothing. A job without scope that names `src/` therefore gets neither a record guarding `src/main.py` nor `src/AGENTS.md`, although the fallback explicitly allows naming a record’s folder.
**Correction:** Recognize single-component directory paths ending in `/`. Test record and instruction pointers for this case.

### 3. Review matching loses the source of a rename — major
**Evidence:** `skills/shape-and-execute/scripts/sae_lib/prompts.py:93–95`.
**Affects:** [REVIEW-POINTERS].
**Why it matters:** With rename detection, `git diff --name-only` returns only the destination. Renaming a guarded file can therefore remove its record and source-directory instructions from the review prompt. This was reproduced against the repository’s existing rename commit `7e2918c`.
**Correction:** Include both source and destination paths, using `--no-renames` or parsing rename statuses. Add job-review and integration-review regression coverage.

## Notes

The cleanup list covers all 103 records, and the resulting files follow its actions. The index has no missing, duplicate, or broken links, and no `DL-` references remain.

Validation used read-only checks and reproductions. The full suite was not rerun under the no-write constraint; the cleanup result reports 318 tests passing, with five skipped.