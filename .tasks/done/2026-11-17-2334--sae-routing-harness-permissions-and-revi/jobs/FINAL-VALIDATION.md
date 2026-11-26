---
id: FINAL-VALIDATION
covers: [DIFF-EASY, EASY-UPGRADE, TIERS-FOLLOW-DIFFICULTY, SETUP-PROPOSAL, DIFF-GUIDANCE, WRITER-COMMAND, LAUNCH-RECORD, NO-SANDBOX-VISIBLE, HARNESS-FALLBACK, STAKES-LOOKUP, STAKES-TEMPLATE, STAKES-ASK, STAKES-POINTER, STAKES-VIEWER, FINDING-SHAPE, STAKES-GRADING, TRIAGE, ACCEPT-INTEGRATION, LET-GO-REPORT, FIX-WORKER, APPROACH-CHECK, PARK-STORY, DECISION-ANYTIME, JOB-DROP, RESULT-SECTIONS, PROMPT-JOB, SHARED-RULE-OWNER]
verify:
  - python3 tests/run.py
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
---

# FINAL-VALIDATION: Full suite and every acceptance check on the integrated branch

## Objective
Confirm on the integrated task branch that every requirement's acceptance items hold.

## Inputs
- `specs.md` "Requirements" (every acceptance list) and "Technical contract".
- `brief.md`; the results of every earlier job.
- `.tasks/repo/profile.md`: the full suite.

## Scope
- Run the full suite once.
- Walk every acceptance item. Prefer a deterministic check: the test that covers it, or a CLI
  run in a scratch repository with fake `codex` and `claude` executables on PATH. Judge by
  reading only where no run can show it (prompt text, the TRIAGE scenario in `execute.md`).
- Build a configuration from the setup proposal in `references/modes/setup.md`, save it with
  `sae setup save` in a scratch config, and dispatch jobs of each difficulty with tiers on and
  off: the routes match the proposal, and Codex balanced `normal` and `hard` differ. Apply the
  upgrade steps to a three-column configuration: every existing cell keeps its model · effort.
- Check the invariants in `brief.md`: no `sae` code path writes AGENTS.md or CLAUDE.md; no
  model names in `sae` code; read-only commands write nothing; task records hold no private
  paths.
- Check that the prompt files contain no text beyond the spec drafts, the contradiction fixes
  in `jobs/PROMPT-TEXT.result.md`, the edits in `jobs/PROMPT-LEAN.result.md` (audit proposals
  1–9), the edits in `jobs/PROMPT-STAKES.result.md`, and `specs.md` amendments.
- For each rule that PROMPT-LEAN cut from the mode files (`research/PROMPT-LEAN-AUDIT.md`,
  proposals 1–3), run its case in a scratch task and confirm that `sae` prints it.
- `[AMEND-2]`: no file under `skills/` or `tests/` (except the retired-terms list) uses
  `## Stakes`, `section "Stakes"` or `[beyond stakes]`; prompts, `sae status` and the viewer
  say "Project Stakes".
- `easy` is refused for a review job too (`sae job edit` on a spec, plan or integration
  review), not only for planning ([DIFF-EASY]).

## Boundaries
- Do not fix anything. A failed item goes into your result with its evidence; the orchestrator
  adds fix jobs.

## Expected output
`jobs/FINAL-VALIDATION.result.md`: per requirement, each acceptance item with pass or fail and
its evidence (test name, command and output excerpt, or file and lines).

## Validation
- [ ] Every requirement in `specs.md` appears in the result.
- [ ] The full suite passed, or each failure is listed with its cause.
