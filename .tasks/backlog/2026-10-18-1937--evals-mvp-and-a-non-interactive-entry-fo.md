# Intent: Evals MVP and a non-interactive entry for shape-and-execute

## Problem
The decision record of 2026-10-07 put evals before the public release. On 2026-10-18 the owner
decided to release without them, as an early version (decision DECISION-NO-EVALS of the
first public release). The skill has no
measured evidence yet that it beats a plain session.

## Goal
Build the evals MVP and the non-interactive entry it needs, after the release.

## Related tasks
Builds on the first public release — start after it.

## Findings this item replaces
Text carried over from the release item (closed in triage on 2026-10-13):

### Build the shape-and-execute evals MVP

## Observation
Parked in shape-and-execute's parking lot (Skill evals) and in a to-do note on evals, both removed on 2026-10-12. Decided in a decision record, since removed from `docs/adr/` (see git history): dogfood first, evals before the public release, an MVP that can grow; they must show the six problems in docs/adr/_intent.md (P6 is solved by design and hardly measurable). The parked [agent] proposal, from two research notes on evals, since removed from `docs/adr/research/` (see git history): layer 0 dogfood; layer 1 a custom 'haunted feature' fixture of 4 to 8 jobs with traps (a constraint stated once in the first note and checked by a hidden test; three components on one interface with a hidden integration test; cut and resume at a checkpoint read from events.jsonl, also in the other harness; subagent count against a reference topology; forced compaction in the plain arm); layer 2 RoadmapBench through Harbor (MIT and Apache-2.0); layer 3 small SWE-bench Pro tasks as a negative control for overkill. Method from Quorum: the skill against a plain session on the same model; a simulated user with a private brief; deterministic checks first, an LLM judge only for plan quality as blind pairwise comparison; 2 to 3 runs per cell, deltas under about 20% are noise; pilot one run per arm first. Open fact: how Codex reports token use (Claude Code reports it in completion notifications), needed to measure extra quota.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion

### Decide a non-interactive entry for evals and benchmarks

## Observation
Parked in the to-do note on evals ('Non-interactive entry: open. Decide when the evals are built'). Benchmarks give a full spec and have no human. The skill needs a way to start from a ready spec, with gates answered by a simulated user or approved automatically. Related: docs/adr/research/prose-spec.md B10 ('keep each phase enterable alone'). Decide together with the evals MVP.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
