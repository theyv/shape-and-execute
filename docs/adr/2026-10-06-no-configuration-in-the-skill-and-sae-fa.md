---
title: No configuration in the skill and sae fails loudly
type: architecture
status: accepted
date: 2026-10-06
source: DL-57, DL-60, design interview 2026-10-06 (Q32)
applies-to: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/references/modes/setup.md, skills/shape-and-execute/SKILL.md, config_path, load_config, validate_config]
---

# No configuration in the skill and sae fails loudly

## Context
The skill needs personal values: model lists, routing, languages, worktree root, defaults for
new tasks. They could ship with the skill as defaults, or live outside it.

## Decision
- [human] The skill ships no configuration values, not even defaults. The user config holds
  everything personal. `sae` reads only that file and fails loudly (exit 2) when something is
  missing.
- [human] Setup is error-driven: no check at every start. When `sae` exits 2, the orchestrator
  offers setup mode.

## Why
Mixing config into skill files makes copying a skill look like copying a configuration. A copied
skill must never run silently with someone else's models.

## Rejected options
- Defaults shipped inside the skill.
- A configuration check at every start.

## Consequences
- Model names in the skill: see [Model names only in the setup proposal and the Claude family list](2026-10-12-model-names-only-in-the-setup-proposal-a.md).
- Numeric limits such as `max_verify_failures` are built into `sae`'s code, not configuration of
  the skill.
