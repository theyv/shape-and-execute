# Intent: Model routing reminder in worker prompts

## Problem

Workers dispatched by SaE sometimes spawn their own subagents. These helpers often run on the
wrong model or effort, for example several Opus agents for simple reading work. Nothing in the
worker prompt tells a worker how to choose a helper's model.

## Context: the stopgap so far (2026-11-26)

- `sae routing <claude|codex> [--level L]` (new, read-only) prints, for one level (default
  balanced), the model and effort for each phase and difficulty, with the current project's
  overrides and Codex families resolved. Its output also carries the usage rules: pick the phase
  and difficulty, pass that model and effort, and never go stronger than your own model and
  effort.
- The owner's global instruction files (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`) have a short
  "Subagent models" section: before spawning a subagent at any depth, run `sae routing` and follow
  it; balanced unless the user names a level; an orchestrator dispatching a job keeps the model
  `sae dispatch` prints. Whether and how many to spawn stays the agent's call.
- [human] The global files are a patch: they reach only the owner's machines and do not ship with
  the skill.

## Goal

The worker prompt that `sae dispatch` builds carries the reminder itself, so every SaE user's
workers pick helper models by the routing.

### Success means

- A worker on an easy job of a premium task spawns helpers no stronger than its own route.
- The rule works without any line in the user's global instruction files.

## Proposed outcome

- [human] Add a short pointer to `sae routing` in the worker prompt (`build_prompt` in
  `scripts/sae_lib/prompts.py`).
- [agent] The prompt could also state the job's own model and effort, so the worker knows its
  ceiling. Today it names the model (commit trailer line) but not the effort.

## Constraints

- The reminder covers only the model and effort of a helper. It must not push workers to spawn
  more helpers.

## Open questions

- [human] Once the worker prompt has the reminder, do we still need the global instruction lines,
  so that routing also applies outside SaE tasks? Or do we drop them?
