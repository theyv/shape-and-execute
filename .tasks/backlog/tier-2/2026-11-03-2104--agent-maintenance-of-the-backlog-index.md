# Intent: Agent maintenance of the backlog index

## Problem

The backlog index can become stale when agents add, move, rename, or pick up backlog items.
The owner then has to request updates to keep the overview useful.

## Goal

Let the agent maintain the backlog index as part of normal backlog work.

### Success means

- The index reflects the current backlog items and their tier folders.
- New items appear with a link and a short description.
- Moves, renames, and task pickup do not leave stale entries or broken links.
- Maintenance preserves the owner's priorities and records unresolved decisions accurately.

## Constraints

- [human, 2026-11-03] Tier 2. Record this work for later implementation.
- The index to maintain is [backlog/index.md](../index.md).
- This item does not authorize automatic priority changes or starting backlog work.

## Related tasks

[Backlog folder option and template reminder](2026-11-03-2038--backlog-folder-and-template-reminder.md)
improves creation of backlog items. This item keeps the overview current afterward.

## Open questions

- Should maintenance use agent instructions, CLI support, or both?
- Which workflow steps should trigger an update, and how should stale entries be detected?
