---
title: Model names only in the setup proposal and the Claude family list
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-08-1733--sae-dogfood-fixes, task 2026-10-12-1846--sae-findings-docs
applies-to: [skills/shape-and-execute/references/modes/setup.md, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/scripts/sae_lib/server.py, skills/shape-and-execute/assets/viewer/settings.js, settings_data]
---

# Model names only in the setup proposal and the Claude family list

## Context
The skill holds no configuration ([No configuration in the skill and sae fails loudly](2026-10-06-no-configuration-in-the-skill-and-sae-fa.md)). Yet
setup's proposal needs model names to be useful, and the viewer could offer only the Claude
families it saw in the config during the page session, so the owner could not add haiku or
fable (reported 2026-10-12).

## Decision
[agent] Model names appear in two places only:
- the proposal text of `references/modes/setup.md`, which `sae` never reads;
- the list of known Claude families in `sae` (haiku, sonnet, opus, fable). The settings API
  sends it, and the viewer's "Add family" offers each family that is not in the model list.

The rest of the code, the viewer and the prose name no model; tests use fake names. Codex
families come from the local catalog.

## Why
- The setup proposal is advice for the agent, not configuration.
- Claude has no catalog to read, and the Agent tool accepts family names only, so a fixed
  family list is the only way to offer a family the config lacks.

## Rejected options
- Model names in the setup proposal only (until 2026-10-12): the viewer could not offer a
  Claude family that the config did not already hold.
