# Intent: Configure concurrent job limits

## Problem

Users need control over how many jobs can run at the same time within a task and across tasks.

## Goal

Allow users to configure a concurrent job limit per task and a global limit.

### Success means

- A user can set how many jobs may run concurrently for a task.
- A user can set a global limit on concurrent jobs across tasks.
- Both limits are respected when jobs are started.

## Open questions

- Where should each setting live, and what should its default be?
- What scope should the global limit cover, and how should concurrent starts coordinate?
- How should jobs waiting for an available slot appear to the user?
