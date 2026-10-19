---
id: DISPATCH-POINTERS
covers: [WORKER-POINTERS, REVIEW-POINTERS, DIR-POINTERS, POINTER-LIMIT, INDEX-POINTER, PLANNER-SCOPE, TESTS]
verify:
  - python3 tests/run.py test_dispatch_pointers test_reviews test_external_review_tokens test_control
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/
  - skills/shape-and-execute/references/roles/
  - skills/shape-and-execute/templates/job.md
  - tests/test_dispatch_pointers.py
---

# DISPATCH-POINTERS: Pointer lines in sae dispatch prompts

## Objective
`sae dispatch` prompts carry record pointers, directory instruction pointers and the index
pointer as the spec says, with the protocol lines and tests that go with them.

## Inputs
- `specs.md`: [WORKER-POINTERS], [REVIEW-POINTERS], [DIR-POINTERS], [POINTER-LIMIT],
  [INDEX-POINTER], [PLANNER-SCOPE], [TESTS], "Rules and edge cases", "Technical contract",
  [DECISION-MATCH], [DECISION-POINTER-FORMAT], [DECISION-PATH-ENTRIES],
  [DECISION-VALIDATION-POINTERS], [DECISION-INDEX-ROLES].
- `research/NESTED-AGENTS-MD.md`, only for the reason behind [DIR-POINTERS].
- `brief.md`: "Invariants", "Architecture facts".
- Code: `build_prompt` and `diff_command` in `scripts/sae_lib/prompts.py`; ADR folder rules and
  index helpers in `scripts/sae_lib/findings.py`; `in_scope` in `scripts/sae_lib/reviews.py`;
  test helpers in `tests/saetest.py`.

## Scope
- Worker pointers for implementation, integration and validation jobs: match on `scope`, or on
  path entries the job file names word for word when there is no `scope`.
- Review pointers: a job review matches the files the target job's diff changed; the
  integration review matches the whole task diff. The external review COMMAND carries the
  same lines (it is built from the same prompt).
- Directory `AGENTS.md` / `CLAUDE.md` lines below the repository root, outside the limit.
- At most 10 record lines in `index.md` order, then "+N more, see <index path>" naming each
  index involved ([EDGE-MANY-FOLDERS]); a record without an index line gets a line built as
  `sae adr accept` builds one ([EDGE-NO-INDEX-LINE]).
- The index pointer in the planner and decision-worker prompts.
- Protocol lines: `reviewer.md` one rule about pointed records; `planner.md` reads the index
  and only the records it needs, and gives writer jobs a `scope` when it can;
  `decision-worker.md` names the index instead of "ADRs"; the `scope` comment in
  `templates/job.md` no longer limits it to parallel writers.
- Tests in `tests/test_dispatch_pointers.py` for every acceptance item of the covered
  requirements.

## Boundaries
- No new command, setting or state. Few added lines.
- Links in pointer lines must open from the prompt's workdir. Read the records from the
  checkout the agent works in, so a job sees the records of its branch.
- Do not touch `docs/adr/`, the writing rules in `references/modes/`, or
  `templates/decision-record.md` (other jobs own them).
- `worker.md` may get one line about pointed records if the prompt alone does not make their
  use clear; nothing more.

## Expected output
Commits on the job branch: the code, the protocol lines, the tests.

## Validation
- [ ] A prompt with no match, and a repository with no ADR folder, are identical to today's.
- [ ] Code names in `applies-to` never match; the root `AGENTS.md` never appears.
- [ ] Each acceptance item of the covered requirements has a test that fails without the change.
