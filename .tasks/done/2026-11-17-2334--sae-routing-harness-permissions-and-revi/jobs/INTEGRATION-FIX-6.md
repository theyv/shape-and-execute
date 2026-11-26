---
id: INTEGRATION-FIX-6
covers: []
verify:
  - python3 tests/run.py test_stakes
scope:
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/references/modes/setup.md
  - skills/shape-and-execute/references/modes/shape.md
  - tests/**
---

# INTEGRATION-FIX-6: sae status prints the Project Stakes question also without a task

## Objective
`sae status` without a task prints the Project Stakes question while they are not set, so
setup can ask it before the first task exists.

## Inputs
- `jobs/INTEGRATION-FIX-5.result.md`, section "Round 2" and its Risks: today only
  `sae status <task>` prints `stakes.ask_text`.
- `setup.md` step 7 and `shape.md` "2. First round": the one-line pointers to it.

## Scope
- `sae status` without a task, run in a repository whose Project Stakes are not set, prints
  the same `ask_text` block once (the profile path of that repository). With the stakes set,
  it prints nothing about them, as today.
- Check that the pointers in `setup.md` step 7 and `shape.md` stay true; if setup should name
  plain `sae status`, say so in its line. Keep each pointer one line.

## Boundaries
- The question text itself stays as it is (the owner approved it).
- A new problem becomes a finding.

## Expected output
Commits on the job branch; the result names the change and the test.

## Validation
- [ ] A test: `sae status` with no task in a repository without Project Stakes prints the
      question; with Project Stakes set it does not.
