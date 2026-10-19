---
status: done
summary: sae dispatch adds record pointers (scope / job file / diff), directory AGENTS.md / CLAUDE.md lines and the index pointer; protocol lines and tests added
validation: pass
changes: made
resolved: []
---

# Result: DISPATCH-POINTERS

## Validation evidence
- `python3 tests/run.py test_dispatch_pointers test_reviews test_external_review_tokens test_control`: 42 tests OK.
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: OK.
- Full suite `python3 tests/run.py`: 317 tests OK (5 skipped). Run only to check for regressions.
- `tests/test_dispatch_pointers.py` has 14 tests. With the code change stashed, 10 of them fail. The 4 that
  still pass are negative checks, which cannot fail without the feature: code names never match, no match
  gives the same prompt as no ADR folder, a review with no guarded change gets no lines, and no index gives
  no index line.
- Coverage by requirement:
  - [WORKER-POINTERS]: a scope matches a file record and a folder record. The job-file fallback works. Code
    names never match. No match gives a prompt identical to no ADR folder (the resumed prompt ends with the
    first prompt byte for byte).
  - [REVIEW-POINTERS]: a job review matches its diff, and the external COMMAND carries the same line. A review
    with no guarded change gets no lines. The integration review matches the whole task diff.
  - [DIR-POINTERS]: directory files below the root appear. Root `AGENTS.md` / `CLAUDE.md` never appear.
    10 records plus 1 directory file give 11 lines and no "+N more".
  - [POINTER-LIMIT]: 12 records give 10 lines in `index.md` order, then "+2 more, see docs/adr/index.md".
    [EDGE-MANY-FOLDERS] (each link points into its own folder) and [EDGE-NO-INDEX-LINE] are tested too.
  - [INDEX-POINTER]: the planner gets the index when it exists and nothing when it does not. The decision
    worker gets the index.
- Protocol lines:
  - `reviewer.md`: one rule.
  - `planner.md`: an index input, and one `scope` sentence (two old mentions that limited `scope` to
    parallel writers are now aligned).
  - `decision-worker.md`: "ADRs" is replaced with the index.
  - `templates/job.md`: the `scope` comment is changed.
  - `worker.md` is not changed: the prompt header says how to use the lines.
- Sanity run on this repository: 103 records have path entries, and this job's scope matches 88 of them,
  because the current records apply to broad folders. The limit of 10 caps that, and the cleanup will
  narrow it.

## Decisions taken
- [agent] `glob_regex` / `in_scope` moved from `reviews.py` to `common.py`. `reviews.py` imports
  `prompts.py`, so importing `in_scope` from `reviews.py` would make an import cycle.
- [agent] Job-file fallback ("path entries (or their folders) … word for word"). The job file's tokens that
  contain `/` are compared with each entry. A token matches when it equals the entry, lies inside a folder
  entry, or is the entry's immediate folder. Higher folders do not match, so a job file that names `skills/`
  does not pull in every record.
- [agent] Directory lines come from the same paths as record matching: scope patterns up to the first glob,
  path tokens in the job file, or the files in the diff. They do not depend on an ADR folder. A repository
  with no records but with directory files gets them too. The byte-for-byte invariant holds when there is
  neither.
- [agent] Links are relative to the workdir (`docs/adr/x.md`). Records are read from the workdir for
  workers, and from the task root for reviews (the reviewer's workdir). The ADR folders come from the task
  root's repo profile: the flat folder first, then the `adr_rules` folders.
- [agent] "+N more, see …" names the index of each folder whose records were left out.
- [agent] The index pointer uses the absolute path, like the other pointers in the planner and decision
  prompts (label `Decision-record index:`).

## Risks
- Spec and plan reviews get no record lines: they have no diff of their own. This follows the spec.

## Findings filed
None.
