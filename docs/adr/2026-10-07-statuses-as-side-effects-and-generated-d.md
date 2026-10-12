---
title: Statuses as side effects and generated dispatch prompts
type: architecture
status: accepted
date: 2026-10-07
source: DL-20, design interview 2026-10-06 (D20); DL-86, implementation 2026-10-07
applies-to: [skills/shape-and-execute/scripts/sae_lib/prompts.py, skills/shape-and-execute/scripts/sae_lib/progress.py, skills/shape-and-execute/scripts/sae_lib/reviews.py, build_prompt, cmd_dispatch, cmd_collect]
---

# Statuses as side effects and generated dispatch prompts

## Context
The owner worried about ceremony: agents changing statuses instead of doing the work. The
original notes also asked that the orchestrator should not improvise subagent prompts.

## Decision
- [agent] Job statuses change as side effects of real commands (`sae dispatch`, `sae collect`,
  merges), never as a separate step.
- [agent] `sae dispatch` prints the prompt of every subagent. A prompt holds pointers only:
  role protocol, job file, brief, spec, repo profile, workdir, branch, result path, commit
  trailers, interaction mode.
- [agent] Every prompt except a review's holds the full `sae finding new` command; the
  planner's prompt names `sae job add` and `sae check`.

## Why
- Direct answer to the ceremony concern ([Light in its complexity](2026-10-06-light-in-its-complexity.md)) and to the wish that the
  orchestrator should not improvise prompts.
- A worker cannot know the skill path otherwise, so it could not file a finding.
