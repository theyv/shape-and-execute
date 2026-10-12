---
title: Scale by uncertainty, breadth and stakes
type: architecture
status: accepted
date: 2026-10-06
source: DL-07, DL-08, DL-10, DL-11, design interview 2026-10-06 (Q1, Q11, Q13)
applies-to: [skills/shape-and-execute/SKILL.md, skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/references/modes/plan.md, skills/shape-and-execute/references/modes/execute.md]
---

# Scale by uncertainty, breadth and stakes

## Context
Tasks range from a one-file fix to a large feature. A single size knob decides how much
shaping, planning and review a task gets.

## Decision
[joint] The skill scales by three axes, each decided when its information appears:
- uncertainty → shaping depth (grill only, or research first), at intake;
- breadth → topology (one worker, or a graph of jobs), at planning;
- stakes → the task's settings (interaction mode, levels, review points), by the owner.

Details:
- The agent proposes the depth in the first round, in one sentence with a reason; the owner
  confirms or overrides. "Quick" leans to grill only [joint].
- Context boundaries follow a rule: a planner subagent for two or more jobs or after deep
  shaping; a fresh execution session after deep shaping or a long conversation; otherwise the
  same session [joint].
- Research count is flexible: usually 2–5 research jobs, sometimes one, when a task is hard in
  orchestration rather than in knowledge [human].

## Why
Size hides the "small but unknown" and the "big but obvious" cases.

## Rejected options
- Two tracks (light and full).
- Fixed S/M/L tiers.
- A "dispatch score": it was only an illustration in the notes [human].
