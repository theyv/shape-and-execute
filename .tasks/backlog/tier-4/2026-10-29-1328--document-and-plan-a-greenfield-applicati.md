# Intent: Document and plan a greenfield application before coding

## Problem

Starting a whole application from scratch needs an overall intent and design before individual
implementation tasks make sense. The owner wants a way to establish that foundation and identify
initial work without starting to write code immediately.

## Goal

Provide a task mode for designing a new application from its main idea. Produce documentation
that can guide a set of initial tasks, then outline those tasks together before implementation.

### Success means

- The owner can start from the application's main idea and develop its overall documentation.
- The mode produces a set of initial tasks based on that documentation. Ten or fifteen tasks
  are examples; the number depends on the project.
- The design and task breakdown happen before application code is written.
- Later work can use the documentation and pick up the resulting tasks.

## Proposed outcome

Explore a documentation-first task mode for greenfield projects. It should help develop the
application's intent and design, then break the initial work into tasks. The exact documents,
level of detail and task creation process need shaping.

The referenced `th-skillmaker` workflow is an inspiration: it develops an intent, decisions and
specifications before code. Adapt the useful ideas to whole applications rather than assuming its
skill-specific workflow applies unchanged.

## Affected users and systems

Owners starting a new application and agents using shape-and-execute to plan its work.

## Related decisions

[Big work goes lazily through the backlog](../../../docs/adr/2026-10-06-big-work-goes-lazily-through-the-backlog.md)
rejects fully specifying a series of tasks up front. Consider how an initial task breakdown fits
with that decision, or whether this greenfield mode needs a deliberate exception.

## Open questions

- What documentation is needed before the first implementation tasks can be outlined?
- How detailed should the initial tasks be, and when should their individual specifications be
  written?
- How should this mode create or represent the tasks and keep the overall design useful as the
  project changes?
