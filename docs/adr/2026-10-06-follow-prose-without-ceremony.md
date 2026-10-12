---
title: Follow PROSE without ceremony
type: architecture
status: accepted
date: 2026-10-06
source: DL-06, DL-30, DL-31, DL-32, design interview 2026-10-06 (D24, D28, D29, D30)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/roles, skills/shape-and-execute/references/modes/execute.md, skills/shape-and-execute/templates/brief.md, skills/shape-and-execute/templates/job.md, skills/shape-and-execute/scripts/sae_lib/prompts.py, BRIEF_MAX_LINES]
---

# Follow PROSE without ceremony

## Context
PROSE (Daniel Meppiel, The Agentic SDLC Handbook, chapter 13) gives five constraints for
agentic systems: progressive disclosure, reduced scope, orchestrated composition, safety
boundaries, explicit hierarchy. A research subagent evaluated the design against it:
[research/prose-spec.md](research/prose-spec.md).

## Decision
[human] The skill follows PROSE where it adds no step to a run:
- `SKILL.md` is a router with labelled links; role protocols are read only by their subagents.
- A job is one sentence and one deliverable. The brief is at most about a page.
- Dispatch prompts carry pointers, not pasted content.
- A role authority table, kept small: the owner asked that safety not take much space
  [agent].
- Hard stops hold in every mode (see [One list of hard stops for every mode](2026-10-07-one-list-of-hard-stops-for-every-mode.md)); `sae` re-runs
  `verify` (see [sae re-runs verify, up to a per-task limit](2026-10-07-sae-re-runs-verify-up-to-a-per-task-limi.md)).
- Precedence: repository instructions > spec > brief > job file. A lower level may refine a
  higher one, never silently override it [agent].

## Why
The owner wants the skill to follow PROSE, filtered through [Light in its complexity](2026-10-06-light-in-its-complexity.md): an idea
is kept when it adds no step to a run.

## Rejected options
- Per-role agent files under `.apm/agents/` with tool whitelists (agent, as ceremony). Authority
  is stated in the role protocols and enforced by worktrees, sandboxes and read-only reviewer
  flags. Revisit if workers overstep their authority.
- A planner that cannot write files, whose output `sae` writes (agent, as ceremony). The planner
  writes its own files, limited to the task folder.
