# Intent: Chrome push notifications when a task needs attention

## Problem
The owner may miss a task that needs attention while working outside the task viewer.

## Goal
Send a push notification in Chrome when a shape-and-execute task needs the owner's attention.

### Success means
- Chrome shows a notification for a task that needs attention.
- The notification identifies the task and what needs attention.

## Proposed outcome
Add Chrome push notifications for task events that require the owner's action.

## Affected users and systems
The owner receives notifications. The change affects task attention signals and the task viewer's
browser integration.

## Open questions
- Which task events count as needing attention: approval, a question, a blocked job, or others?
- Must notifications arrive when the task viewer is closed?
- What should happen when the owner clicks a notification?
- How should the owner enable, disable, or silence notifications?
