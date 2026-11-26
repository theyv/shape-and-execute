---
title: First-run and upgrade changes end with an owner walkthrough
type: process
status: proposed          # proposed | accepted | rejected | superseded
date: 2026-11-26
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi
applies-to: [skills/shape-and-execute/references/modes/setup.md, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/doctor.py, tests/tools/walkthrough/]
revisit-when: an automated check can judge the first-run and upgrade experience
---

# First-run and upgrade changes end with an owner walkthrough

## Context
The setup guide, the setup proposal and the prompts after an update are what a new user sees
first. Tests check that they are correct, not that they are clear. In this task the owner
needed a settings mockup and several rounds to see what the proposal really meant.

## Decision
When a task changes the first-run setup (the guide, the proposal, the config schema) or adds
anything that asks the user for an action or an answer after an update, the plan gets a job
`FIRST-RUN-WALKTHROUGH` near the end: after the integration fixes, before the final
validation. It runs the tool in `tests/tools/walkthrough/` (a sandbox with a relocated `HOME`,
Claude by default, Codex on demand) for two scenarios, a fresh install and an upgrade, and a
hold lets the owner walk through them. The rule is in `.tasks/repo/profile.md`, which the
planner and every worker read.

## Why
- The owner judges UX by using it, not by reading a diff.
- Before the final validation, so fixes from the walkthrough are validated too.
- A reusable tool makes each later walkthrough cheap.

## Rejected options
- The rule only in this record: records reach workers whose job touches the guarded paths, but
  the planner, who adds the job, does not read them.
- A walkthrough after the final validation: its fixes would skip validation.

## Consequences
- Tasks that touch these paths get one more job and one hold.
- The walkthrough tool must keep working when the install path or the harness CLIs change.
