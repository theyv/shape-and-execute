---
id: PROMPT-LEAN
covers: [PROMPT-JOB, HARNESS-FALLBACK, TRIAGE, FIX-WORKER, DECISION-ANYTIME, LET-GO-REPORT, STAKES-ASK, EASY-UPGRADE]
verify:
  - python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers
  - grep -q "accept-review" skills/shape-and-execute/references/modes/execute.md
  - grep -q "sae job drop" skills/shape-and-execute/references/modes/execute.md
  - grep -q "(luna → terra → sol → astra)" skills/shape-and-execute/references/modes/setup.md
  - "! grep -q '\\*\\*care\\*\\*' skills/shape-and-execute/SKILL.md"
  - grep -q "\\*\\*stakes\\*\\* (the task's settings" skills/shape-and-execute/SKILL.md
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/SKILL.md
  - skills/shape-and-execute/references/**
  - skills/shape-and-execute/templates/**
  - tests/test_retired_terms.py
  - tests/test_findings.py
  - tests/test_sae_ask.py
  - tests/test_adr_rules.py
  - tests/test_resolves.py
  - tests/test_dispatch_pointers.py
---

# PROMPT-LEAN: Cut the prompt text that `sae` will print, in one diff the owner reads

## Objective
Apply the accepted prompt-file edits of the lean audit, so that the orchestrator's mode files
keep one pointer sentence where `sae` prints the rule.

## Inputs
- `research/PROMPT-LEAN-AUDIT.md` in the task folder: every "Paste into PROMPT-LEAN" block of
  proposals 1–5, and the proposed texts of proposals 6–9. The owner accepted proposals 1–9 and
  rejected proposal 10 (the routing tables stay as they are).
- The line numbers in the audit are those of the files at commit `34876a1`. Your branch starts
  there or later; find each passage by its text.
- AGENTS.md (prompt text stays lean); the `agentic-systems-guidelines` skill, if available.

## Scope
- Make every prompt-file edit of proposals 1–9, with the audit's replacement texts. You may
  smooth a sentence so it reads well in its place; keep its meaning.
- Proposal 1 includes the optional older duplicates in `plan.md` and `shape.md` ("When the
  printed output is a COMMAND … `sae` reads the COMMAND's tokens itself."): replace them too.
- When a test asserts text that an edit removes, change the test to assert the new text.

## Boundaries
- No code: `sae` prints the moved rules later, in `WRITER-LAUNCH`, `FIX-LOOP-EXITS` and
  `FIX-LOOP-GUIDANCE`. Until then the rules are printed nowhere. That is expected inside the
  task branch; do not keep the old text "for safety".
- The routing tables in `setup.md` stay as they are (two values per cell), except the Codex
  family order of proposal 5.
- No other rewording outside the audit's proposals. A new problem you see becomes a finding.

## Expected output
One commit on the job branch; the result lists each proposal with the file and the lines it
changed, and the net line count per file before and after.

## Validation
- [ ] execute.md, plan.md and shape.md hold no branch logic of the fallback rule (job kind,
      job status, interaction mode): only "follow what it prints".
- [ ] execute.md Loop step 3 still names triage, `[beyond stakes]`, the `--let-go` line,
      `sae job drop` only on the user's word, and `accept-review`.
- [ ] SKILL.md says **stakes** for the third axis; no file says "care" as an axis.
- [ ] setup.md lists the Codex families luna, terra, sol, astra in that order.
