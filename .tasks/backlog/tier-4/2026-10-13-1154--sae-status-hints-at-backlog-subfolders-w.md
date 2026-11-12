# Intent: sae status hints at backlog subfolders when the backlog grows

## Problem
Since 2026-10-13 the backlog may group items in subfolders (`.tasks/backlog/<module>/`), and
every listing scans one level of them. Only one sentence in SKILL.md says so. A user learns it
only by asking the agent.

## Goal
When the backlog has many flat items (about 10 or more) and no subfolders, `sae status` prints
one line: "tip: group backlog items in subfolders, one per module". Nothing more.

## Constraints
- No setting, no setup question, no flag. One line of output, one test.
