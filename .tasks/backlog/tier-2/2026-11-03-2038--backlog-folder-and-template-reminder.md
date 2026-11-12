# Intent: Backlog folder option and template completion reminder

## Problem

`sae new --backlog` creates an item at the backlog root. An agent must move it manually when the intended folder is already known.

The command creates an intent template and reports success. Agents sometimes leave that template unchanged, including when another agent delegates backlog capture. The item then lacks the intended description.

## Goal

Make backlog capture easier and remind agents to finish the description.

## Proposed outcome

- [human] Accept an optional folder parameter when creating a backlog item. The folder is relative to `.tasks/backlog/`.
- [human] After creation, print a short reminder to fill in the template and follow its structure where possible.

## Constraints

- Keep the structure flexible. The reminder is guidance, not mandatory section validation.
- This request does not add parameters for individual content sections.
- Record this work in the backlog. Do not implement it now.
