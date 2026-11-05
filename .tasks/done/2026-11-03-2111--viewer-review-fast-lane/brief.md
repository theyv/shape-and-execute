# Brief: Viewer and review maintenance

## Why
Four small Tier 1 items and one finding, batched so that they run largely on their own. The
owner wants each change light: no new ceremony, no new review gates, no token-heavy steps.

## What
Readable Shape research rows; a review-flag control in the viewer and on running jobs; an edge
case filter in spec review; a narrow foundation rule for the planner; current ADR help text.
See `specs.md` for requirements.

## How (high level)
- Reuse existing mechanisms: viewer writes run `sae` as a subprocess; job review already
  gates dependent jobs.
- Protocol text changes are a few sentences, not new sections.

## Invariants
- Task state changes only through `sae`.
- The owner's settings (review points, levels) are never changed as a side effect.

## Constraints
- Python 3.9 or newer, standard library only (`AGENTS.md`).
- Plain words, short sentences in every text an agent reads.

## Validation
- `.tasks/repo/profile.md`: the smoke command in every writer job; the full suite only in FINAL-CHECK.
