---
id: PLAN
covers: []
verify: []
---

# PLAN: Plan the ADR cleanup and the dispatch pointers

## Objective
A job graph that delivers every requirement of `specs.md` with fresh workers.

## Inputs
- `intent.md`, `specs.md`, `research/NESTED-AGENTS-MD.md` (only for [DIR-POINTERS]).
- Repository instructions: `AGENTS.md` (root); validation commands in `.tasks/repo/profile.md`.
- The skill to change is `skills/shape-and-execute/` in this repository, not an installed copy.
  Pointer code goes near `build_prompt` in `scripts/sae_lib/prompts.py`; index helpers and ADR
  folder rules are in `scripts/sae_lib/findings.py`; `in_scope` is in `scripts/sae_lib/reviews.py`.

## Scope
- [CLEANUP-LIST] is one job whose result is the list. The owner holds the run after it
  ([DECISION-LIST-IN-EXECUTION]); give it a clear ID so the orchestrator can set the hold. Jobs
  that move or remove records depend on it and read the approved list from its result file.
- The cleanup and the `sae` code change touch different files; plan for parallelism only where
  it pays.

## Boundaries
- Nothing is pushed. Work happens on the task branch of this repository.
- Do not write the cleanup list yourself; that is the list job's work.

## Expected output
`brief.md`, `plan.md`, job files, jobs registered with `sae job add`, a clean `sae check`.

## Validation
- [ ] Every requirement is covered.
- [ ] The riskiest assumptions are listed in `plan.md`.
