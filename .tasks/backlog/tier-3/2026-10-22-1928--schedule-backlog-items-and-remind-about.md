# Intent: Schedule backlog items and remind about overdue work

## Problem
Backlog items have no planned date. Work intended for a specific day can remain unnoticed when
new work starts.

## Goal
Allow a backlog item to have a scheduled date. When any shaping session starts, `sae` reports
scheduled backlog items whose date has passed and which have not been picked up.

### Success means
- A backlog item can have an optional scheduled date.
- Starting any shaping session reports overdue backlog items.
- The reminder identifies each overdue item and does not block shaping.
- Unscheduled backlog items continue to work as before.

## Proposed outcome
Add an optional scheduled date to backlog items. At shaping intake, `sae` checks these dates and
shows overdue items. The reminder is informational. It does not start overdue work automatically.

## Affected users and systems
The owner sees the reminders. The change affects backlog item metadata, backlog loading and the
start of the shaping flow.

## Constraints
- Use the user's local date and timezone consistently.
- Do not change the behavior of backlog items without a scheduled date.
- Do not block shaping because an overdue item exists.

## Nice to have
Cron-based reminders and automatic task execution may follow when the shape-and-execute process
supports more autonomous operation. They are not part of this work.

## Open questions
- Should an item scheduled for today be shown immediately or only from the next day?
- Should reminders appear only at shaping intake, or also in commands such as `sae status` and
  `sae next`?
- How can the owner reschedule or remove a scheduled date?
