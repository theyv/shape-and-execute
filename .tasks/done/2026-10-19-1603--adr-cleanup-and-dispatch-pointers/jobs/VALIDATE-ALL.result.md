---
status: done
summary: Full suite passes (323 OK, 5 skipped); the cleanup matches the approved list; links, index and path entries are clean; pointers work on the real docs/adr; no private data found.
validation: pass
changes: none
resolved: []
---

# Result: VALIDATE-ALL

## Validation evidence

**Verify commands**
- `python3 tests/run.py`: 323 tests OK, 5 skipped, exit 0.
- `! grep -rn 'DL-' docs/adr`: no match (grep exit 1).

**Cleanup against the approved list** (a script parsed the list in `CLEANUP-LIST.result.md`):
- The list has 103 record rows, and 25 of them say keep. `docs/adr/` holds exactly those 25
  records: none is missing and none is extra. It also holds `_intent.md`, `index.md` and
  `research/`.
- The research notes are the 5 the list keeps. The 3 removed notes are gone.
- `index.md` has 31 links for 31 files (25 records, `_intent.md` and 5 notes). Each file has
  exactly one line, and no link dangles.
- No relative link is broken in `README.md`, `CREDITS.md`, the root `AGENTS.md`,
  `sae_lib/AGENTS.md`, `docs/adr/**` or `.tasks/backlog/**` (54 files checked).
- No file under `skills/`, `tests/`, `docs/`, `.tasks/backlog`, `.tasks/repo` or the root files
  names a record that was removed or moved.
- All 14 code-comment targets carry their comment in the diff: `progress.py`, `app.css`,
  `graph.py` (2), `server.py`, `settings.js`, `routing.py` (2), `common.py` (`REVIEW_POINTS`,
  `emit`), `viewer.py`, `control.py`, `tests/test_retired_terms.py` and `setup_mode.py`. The
  record mentions the list names in `common.py`, `gitutil.py`, `lifecycle.py`, `workspaces.py`
  and `reviews.py` are gone.
- `skills/shape-and-execute/scripts/sae_lib/AGENTS.md` exists and holds both moved rules (one
  module per area; read-only commands write nothing).
- Owner changes at the hold:
  - docs-keep-only-the-why now has `applies-to: [docs/adr]`.
  - one-skill-with-five-modes is narrowed to `SKILL.md` and `references/modes/setup.md`.
  - follow-prose names single files, not the `roles/` folder.
  - `prose-spec.md` paraphrases the chapter and carries no local APM skill path (now "a local
    note on APM usage").
  - `codex-facts.md` says "a local catalog" and "a local config".

**Path entries of kept records**: every one of the 25 kept records has at least one path entry,
and every path entry names an existing path. Nothing to report.

**Pointers against the real `docs/adr/`**. The branch's `prompts.guard_lines` and
`index_lines` were called in-process on this task. It was opened with `open_task(write=False)`,
and an in-memory probe job got `scope` through a patched `job_meta`. `git status` was the same
before and after.
- `skills/shape-and-execute/assets/viewer/` gets one record line (model-names-only) and no
  directory file.
- `skills/shape-and-execute/assets/viewer/app.css` gets no lines, because no record names it.
- `skills/shape-and-execute/scripts/sae_lib/prompts.py` gets 3 record lines (follow-prose,
  hard-stops, explicit-effort) and `sae_lib/AGENTS.md`.
- `skills/shape-and-execute/scripts/**/*.py` gets 10 record lines, then "+5 more, see
  docs/adr/index.md", then `sae_lib/AGENTS.md`.
- `skills/shape-and-execute/references/roles/planner.md` gets 3 record lines (follow-prose,
  split-offer, jobs-never-update-design-docs).
- `docs/adr/` gets 2 record lines (docs-keep-only-the-why, research-notes-follow).
- `tests/test_findings.py` gets no lines.
- The root `AGENTS.md` never appears. Links are relative to the workdir (`docs/adr/…`).
- `index_lines` gives the absolute path of `docs/adr/index.md`.

**Private data**: I scanned the changed files.
- No owner names, emails or home-folder paths. No pilot-project terms.
- No Polish text. The only Polish letters are the old `ł` transliteration in
  `common.py` slugify.
- Kept quotes are English and short.

**Spec acceptance items**
- Checked here:
  - CLEANUP-APPLY: the DL- grep, the index lines, and no private data. Whether each kept record
    passes the test is left to the integration review.
  - THREE-PLACES: `plan.md` states the three places and the test. `execute.md` and
    `triage-decisions.md` point to it. A few lines each.
  - REVISIT-WHEN template: the field has a one-line comment.
  - REVIEW-POINTERS: `reviewer.md` has the one rule.
  - INDEX-POINTER: `planner.md` and `decision-worker.md` name the index.
  - PLANNER-SCOPE: `planner.md` has the sentence. The `scope` comment in `job.md` is no longer
    limited to parallel writers.
  - CLEANUP-LIST: 103 + 8 rows, and the hold with the owner's changes.
- Covered by tests in `tests/test_dispatch_pointers.py`:
  - WORKER-POINTERS: scope file and folder, the job-file fallback, code names, no-match
    identity.
  - REVIEW-POINTERS: the diff, no guarded change, the external command, integration, renames.
  - DIR-POINTERS: below the root, globs, and 10 + 1 lines.
  - POINTER-LIMIT: 12 records give 10 lines.
  - EDGE-MANY-FOLDERS, and INDEX-POINTER for the planner and the decision worker.
- Covered by `tests/test_adr_index.py`: the index check, and `revisit-when` with `sae adr new`
  and `sae adr accept`.

## Decisions taken
- [agent] I built the pointer lines in-process (`guard_lines`), not with `sae dispatch`. A
  dispatch would write state to the running task. The function is the one `build_prompt` uses.

## Risks
- The viewer folder has `assets/viewer/README.md` ("Rules for changing it"), which several
  removals lean on. No prompt points to it, because DIR-POINTERS finds only `AGENTS.md` and
  `CLAUDE.md`. CLEANUP-LIST already flagged this at the hold, so it is known and not filed again.
- A broad glob scope such as `scripts/**/*.py` matches 15 records. The limit of 10 holds, but
  that much breadth makes the pointers weak for such jobs.

## Findings filed
None.
