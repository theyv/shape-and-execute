---
id: PROMPT-STAKES
covers: [STAKES-GRADING, TRIAGE, APPROACH-CHECK, FINDING-SHAPE]
verify:
  - python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers
  - grep -q "Project Stakes" skills/shape-and-execute/SKILL.md
  - grep -q "Project Stakes" skills/shape-and-execute/references/modes/execute.md
  - grep -q "^## Project Stakes" skills/shape-and-execute/templates/repo/profile.md
  - "! grep -rqi 'beyond stakes' skills/shape-and-execute"
  - "! grep -q 'stakes line' skills/shape-and-execute/templates/review.md"
  - "! grep -q 'sae setup snippets' skills/shape-and-execute/references/modes/setup.md"
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/SKILL.md
  - skills/shape-and-execute/references/**
  - skills/shape-and-execute/templates/**
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - tests/test_retired_terms.py
  - tests/test_dispatch_pointers.py
---

# PROMPT-STAKES: One meaning of "stakes" for every role, and small prompt wording fixes

## Objective
Apply the prompt-text findings 1, 6, 7, 8, 9 and 11 of the Opus prompt review, so that every
role reads "stakes" as the project's Stakes section.

## Inputs
- `research/PROMPT-REVIEW-OPUS.md` in the task folder: findings 1, 6, 7, 8, 9 and 11, each with
  its file, lines and suggested text. Line numbers are those at commit `3fb7bd0`; find each
  passage by its text.
- `specs.md` "Domain language" (Stakes, Beyond stakes) and `[AMEND-1]`: the prompt will carry
  the stakes text itself, with a header that defines the term (built later by
  `STAKES-IN-PROMPTS`).
- `docs/adr/_intent.md` "Principles": stakes set the settings.

## Scope
- Finding 1: `SKILL.md` third axis and `execute.md` triage sentence, with the suggested texts.
- Finding 6: `planner.md`, the inline-planning case.
- Finding 7: `templates/review.md`, "Breaks" and the Notes comment.
- Finding 8: `reviewer.md`, the stakes grading sentence.
- Finding 9: `APPROACH_PARAGRAPH` in `prompts.py`: it fits a job and the integration, and names
  "Decisions taken" as the place for the answers. Keep the rest of its wording.
- Finding 11: `setup.md`, the sandboxed-setup sentence.
- `[AMEND-2]`: rename the term to **Project Stakes** in all prompt text you own: SKILL.md,
  `references/**` (also shape.md's `stakes: not set` wording and setup.md), `templates/**` (the
  profile heading `## Project Stakes`, the review tag `[beyond Project Stakes]`), and the
  prompt constants in `prompts.py` except the two below. Add `[beyond stakes]`, `## Stakes` and
  `section "Stakes"` to `tests/test_retired_terms.py`; exempt `STAKES_LINE` and
  `STAKES_NOT_SET_LINE` until `STAKES-IN-PROMPTS` rewrites them.
- You may smooth a suggested text so it reads well in its place; keep its meaning.

## Boundaries
- Do not touch `STAKES_LINE` or `STAKES_NOT_SET_LINE`: `STAKES-IN-PROMPTS` rewrites them by
  `[AMEND-1]`.
- No other rewording; no code beyond the prompt constants and the
  retired-terms test. A new problem becomes a finding.

## Expected output
One commit on the job branch; the result lists each finding with the file and the lines it
changed.

## Validation
- [ ] No file uses "stakes" for the task's settings; SKILL.md says the settings follow the
      stakes.
- [ ] reviewer.md, review.md and execute.md use one phrase for a finding that needs more care
      than the Project Stakes justify (`[beyond Project Stakes]`), never "below the stakes".
- [ ] No prompt file uses `## Stakes`, `section "Stakes"` or `[beyond stakes]`.
