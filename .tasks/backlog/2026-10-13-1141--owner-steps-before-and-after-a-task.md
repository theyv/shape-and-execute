# Intent: Owner steps before and after a task

## Problem
See the finding below. Example from 2026-10-13: after merging the task sae-findings-docs, the owner's APM configuration still pointed at the skill's old path; nothing reminded the owner.

## Goal
The skill tells the owner which operational steps follow a task (push, apm path or install, re-pin), for example in the final report.

## Findings this item replaces
Closed in triage on 2026-10-13; their text:

### Operational steps before or after a task have no place in the skill

## Observation
Parked in shape-and-execute's parking lot (Later features). Dogfood traces from another of the owner's repositories show steps around a task: pushing, reinstalling a skill, re-pinning a dependency. The skill has no place for them, and pushing is a hard stop. Decide whether they belong in the skill (for example as owner steps in the final report) or stay outside it.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
