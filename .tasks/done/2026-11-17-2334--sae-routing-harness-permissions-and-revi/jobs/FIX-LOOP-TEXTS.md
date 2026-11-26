---
id: FIX-LOOP-TEXTS
covers: [TRIAGE, PARK-STORY, JOB-DROP, LET-GO-REPORT, DECISION-ANYTIME]
verify:
  - python3 tests/run.py
scope:
  - skills/shape-and-execute/scripts/sae_lib/**
  - tests/**
---

# FIX-LOOP-TEXTS: Make the fix-loop texts that sae prints sharp, consistent and correct

## Objective
Fix the listed issues in the texts `sae` prints about the review fix loop, so each text is
correct, said once, and consistent with the others.

## Inputs
- `research/FIX-LOOP-TEXTS-INVENTORY.md` in the task folder: every fix-loop text with an
  example and file:line, and the "Possible issues" list at the end.
- `jobs/FIX-LOOP-EXITS.md`, `jobs/FIX-LOOP-GUIDANCE.md` and their results: what each text is for.
- `specs.md` sections those jobs cover.
- The repository's Project Stakes (in your prompt): sharp prompts, every line earns its place.

## Scope
Owner decision, 2026-11-22. Fix "Possible issues" 1–8, 10–12 and 14. Leave 9 and 13.
- 1, 3: PARK_OPENING fits both a job park and a task park; no unfilled placeholders such as
  `<ID>`; resolve "Add no fix job" against the "another round" option (the intent: add nothing
  until the user answers).
- 2: the park options are printed in full in one place; the other places point to it in one line.
- 4, 6: the job park and the integration park offer the same exits where the spec allows them
  (check the spec before you add "close anyway" to a job park); no repeated lead lines.
- 5: pointers into the skill's files give the path relative to the skill folder.
- 7: one form for the `--reason` placeholder in printed commands.
- 8: no unreachable messages: let argparse own required options, or make the custom message
  reachable; one of the two.
- 10: the final report does not list reviews or review rounds of a dropped job as open or noise.
- 11: decision-job inputs are built in one place and used by the job file and the prompt.
- 12: one word for the human in every printed text; use the word the skill's other printed
  texts use most (check `prompts.py` and the mode files) and say which in your result.
- 14: a let-go for a review without numbered findings gives the way forward.
For every issue, first check that it is real. List one you believe wrong under "Disputed
findings" with the evidence, and do not change it.

## Boundaries
- Only printed texts and the code that builds them; no behavior change beyond 8, 10, 11 and 14.
- Mode files, role files and templates stay as they are; a needed change there becomes a finding.

## Expected output
Commits on the job branch. The result lists each issue with before → after text (short), and
the word chosen for 12.

## Validation
- [ ] Tests assert the new texts where tests asserted the old ones.
- [ ] Every printed command in the fix loop can be copied and run as printed (no placeholders
      except the ones the agent must fill, written in one form).
