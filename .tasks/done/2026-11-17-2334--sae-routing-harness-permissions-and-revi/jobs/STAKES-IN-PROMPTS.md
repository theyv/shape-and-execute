---
id: STAKES-IN-PROMPTS
covers: [STAKES-LOOKUP, STAKES-POINTER, STAKES-ASK]
verify:
  - test -f tests/test_stakes.py
  - python3 tests/run.py test_stakes test_dispatch_pointers test_task_worktree
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - tests/test_stakes.py
  - tests/test_dispatch_pointers.py
  - tests/saetest.py
  - skills/shape-and-execute/templates/repo/profile.md
---

# STAKES-IN-PROMPTS: Stakes lookup, the stakes line in every prompt, and the profile writer

## Objective
Find the project's stakes in the agreed order, name them in every dispatch prompt and in `sae
status`, and provide the function that saves the profile's Stakes section.

## Inputs
- `specs.md` [STAKES-LOOKUP], [STAKES-POINTER] with AMEND-1, [STAKES-ASK], [DECISION-STAKES-IN-SAE].
- `templates/repo/profile.md` (the Stakes section) and `references/modes/shape.md` (the
  `stakes: not set` wording), both as `PROMPT-TEXT` wrote them.
- The stakes constants in `prompts.py` (from `PROMPT-TEXT`); `build_prompt`,
  `external_review_command`.
- `config.main_worktree` / `gitutil.main_worktree` for the home checkout.
- The "Contradictions" section of `jobs/PROMPT-TEXT.result.md`.

## Scope
- One profile location for every reader and writer: `.tasks/repo/profile.md` of the main
  worktree (brief "How"), also when the task was created from a linked worktree or runs in its
  task worktree. Lookup (`[AMEND-2]`): its `## Project Stakes` section; then a `## Project Stakes` section of AGENTS.md, then CLAUDE.md; no fallback to `## Stakes`. The
  first section with content wins. A section is empty when, after HTML comments are stripped,
  only the five labels with no value, or nothing, remain. Any other text is content, also prose
  and the template's "Not set by the owner" line.
- `sae status` with a task prints `Project Stakes: <source>` or `Project Stakes: not set`, with the profile path
  to write them to (shaping writes there).
- Every dispatch prompt (planner, research, decision, worker, reviewer, and the prompt inside a
  review COMMAND) carries exactly one stakes block, from the constants, or the "not set" text.
  `specs.md` AMEND-1: the block is the header line plus the section text with HTML comments
  stripped; a section longer than 15 lines falls back to naming the source and section. The
  header and the "not set" text start with `Project Stakes:` and name the section "Project
  Stakes" (`[AMEND-2]`); remove their retired-terms exemption. The header says nothing about other copies of the profile (owner decision). The "not set" text
  also says what stakes are (`research/PROMPT-REVIEW-OPUS.md`, finding 4).
- The exact texts (owner decision, 2026-11-20; keep them word for word):
  - header, when set: `Project Stakes: how much care this project needs (from <path>, section
    "Project Stakes"). Work to this bar. Leaving out what the bar does not need (extra tests,
    rare edge cases, polish, abstractions) is expected, not a failure. Never leave out what your
    job must deliver to be correct:` followed by the section text.
  - not set: `Project Stakes: how much care this project needs. Not set, so set the bar
    yourself: from the repository instructions and the README, judge who uses it, what breakage
    is acceptable and what matters now. Then work to that bar. Leaving out what the bar does not
    need (extra tests, rare edge cases, polish, abstractions) is expected, not a failure. Never
    leave out what your job must deliver to be correct. State your estimate in one line in what
    you write back.`
  - `templates/repo/profile.md`, the "not set" line in the Project Stakes comment: replace
    "Estimate the Project Stakes … neither over- nor under-engineer" with the same meaning as
    the not-set text above: set the bar yourself, leaving out what it does not need is
    expected, never leave out what the job must deliver to be correct. Keep it short; it is
    section content that the header above then introduces.
  - the 15-line fallback keeps the header's sentences and names the source instead of the text.
- A function that replaces only the Stakes section of the home profile (it adds the section
  when missing, where the template puts it). `VIEWER-SURFACES` calls it from the server.
- A viewer edit during execution reaches the next dispatch (the lookup reads at dispatch).

## Boundaries
- Never write AGENTS.md or CLAUDE.md.
- Do not reword the constants, except `STAKES_LINE` and `STAKES_NOT_SET_LINE` (AMEND-1), and
  the template's "not set" line; a
  wording problem goes into your result.
- The viewer: `VIEWER-SURFACES`. Prompt text files: `PROMPT-TEXT`, `PROMPT-LEAN`.
- Read-only commands stay lock-free and write nothing.

## Expected output
`stakes.py` (or the module you choose), the call sites, `tests/test_stakes.py`. In the result,
name the lookup and writer functions and what they return, for `VIEWER-SURFACES`.

## Validation
- [ ] Tests for the order of sources, the empty test, a worktree reading the home profile, the
      "not set" line as content, and one stakes line per prompt kind.
- [ ] The writer changes only the Stakes section (byte-equal elsewhere).
- [ ] A task created from a linked worktree: status names the main worktree's profile; a save
      there reaches the next dispatch.
