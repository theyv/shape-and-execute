---
status: done
summary: Pointer matching handles glob scopes (records and nested AGENTS.md / CLAUDE.md), single top-level folders like `src/` in job files, and both sides of a rename in review diffs; 5 regression tests
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-1

## Validation evidence
- `python3 tests/run.py`: 323 tests OK (5 skipped).
- `python3 tests/run.py test_dispatch_pointers`: 19 tests OK (5 new).
- Each fix was reverted on its own, and its tests failed:
  - without `--no-renames`: `test_job_review_of_a_rename_matches_its_source` and
    `test_integration_review_of_a_rename_matches_its_source` fail (finding 3);
  - with the old `path_tokens` regex: `test_job_file_names_a_top_level_folder` fails (finding 2);
  - without the glob test in record matching: `test_glob_scope_matches_the_folders_it_covers` fails (finding 1);
  - without the glob folder walk: `test_glob_scope_gets_the_files_of_the_folders_it_covers` fails (finding 1).
- Checked on this repository: scope `skills/shape-and-execute/scripts/**/*.py` now covers
  `scripts/sae_lib`, so `sae_lib/AGENTS.md` is listed.
- All three findings were checked against the code first, and all three were correct.

## Decisions taken
- [agent] A glob covers a folder entry when it can match some path inside that folder. This is
  checked folder by folder, with the semantics of `glob_regex`. So `a/**/*.py` covers `a/b`, and
  `a/*.py` does not. A path entry that is a file in the checkout is never treated as a folder,
  so `scripts/notes.txt` does not match `scripts/**/*.py`.
- [agent] For a glob, the directory instructions also come from the folders under the glob's
  literal start that the glob covers. `sae` walks the checkout and skips `.git`. The folders
  above the literal start are used as before.
- [agent] The fallback also accepts a single folder name that ends in `/` (`src/`). A name
  without the slash (`src`) still never matches, so code names cannot match.
- [agent] Finding 3 uses `git diff --name-only --no-renames`. A rename then lists both its
  source and its destination. This holds for job reviews and the integration review.
- [agent] The shared `reviewed()` test helper now commits a 40-line `prompts.py` and a
  `skills/x/scripts/AGENTS.md`, so that the rename test gets a real rename. The existing review
  tests still pass with it.
- [agent] `is_glob` treats only `*` and `?` as wildcards, the same as `glob_regex`. The old
  literal-start check also counted `[`, but `glob_regex` matches `[` as a plain character.

## Risks
- With a scope like `**/*.py`, the instruction search walks the whole checkout once per
  dispatch. This is cheap in this repository but could be slow in a very large one.

## Findings filed
None.
