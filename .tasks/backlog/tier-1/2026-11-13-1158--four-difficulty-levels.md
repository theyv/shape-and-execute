# Intent: Four difficulty levels for model routing

## Problem

The current difficulties are `mechanical`, `normal`, and `hard`. The owner reports that
most everyday tasks receive `normal` or `hard`, with `hard` assigned too often. There is
no clear category for simple work that still needs judgment and is not mechanical.

The owner's balanced routing example is Sonnet High for mechanical work, Opus Medium for
normal work, and Opus High for hard work. A fourth difficulty would allow cheaper routing
for mechanical work while keeping a separate Sonnet option for simple work. The owner
suspects the current grouping spends tokens unnecessarily.

## Goal

[human] Add a fourth difficulty category. Keep this work in backlog Tier 1.
Make difficulty more descriptive and give users finer control over model and effort selection.

### Success means

- Mechanical work and simple work that needs judgment have distinct categories.
- Classification guidance separates simple, normal, and hard work clearly enough to
  reduce unnecessary escalation to stronger models.
- Users can configure all four difficulties in routing. Setup guidance and the viewer
  present the same categories.

## Proposed outcome

[human proposal] Use four implementation difficulty levels with the following initial routing.

| Level | Difficulty | When to use it | Claude profile | Codex-only profile |
|---|---|---|---|---|
| L1 | `mechanical` | Follow a clear implementation procedure. | Sonnet Medium | Terra Medium |
| L2 | `easy` | Make a simple change that requires local judgment. | Sonnet High | Sol Medium |
| L3 | `normal` | Design a solution for a difficult implementation task. | Opus Medium | Sol High |
| L4 | `hard` | Implement especially demanding logic or complex UI interactions. | Opus High | Sol Extra High |

These are proposed implementation profiles. Backlog priority tiers are separate from
model tiers.

## Related tasks

[Risk and review](2026-10-30-1311--consider-risk-independently-of-difficult.md) considers
consequences separately from difficulty. Coordinate classification and routing with that work.

## Open questions

- What criteria distinguish each difficulty and prevent overuse of `hard`?
- How should the proposed L1–L4 mapping interact with economy, balanced, and premium
  routing and phase-specific rules?
- How should existing configurations and task or job difficulties migrate?
- Which difficulties should planning and review allow? They currently exclude `mechanical`.
