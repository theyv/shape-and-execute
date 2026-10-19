# Intent: Add an explicit edge case search to spec review

## Problem

Specs can pass review while important edge cases still surface during implementation.
The reviewer protocol mentions missing flows and edge cases, but gives no separate pass
or method for finding them.

## Goal

Add a dedicated section to the spec review prompt that makes the reviewer actively look
for overlooked edge cases and gaps in the behavior contract.

The owner wants stronger guidance inside the existing review. Decide the method when this
item is picked up.

### Success means

- The reviewer checks beyond the scenarios already listed in the spec.
- Findings describe a concrete scenario, its consequence, and the behavior or decision
  the spec needs to define.
- The review stays focused on behavior relevant to the intent.

## Current behavior

[Reviewer protocol](../../skills/shape-and-execute/references/roles/reviewer.md)
already asks about missing flows or edge cases that change behavior. This item strengthens
that instruction.

Design and implementation are deferred until this item is picked up [human, 2026-10-18].
