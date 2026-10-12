---
title: Model lists per harness
type: architecture
status: accepted
date: 2026-10-12
source: DL-98, DL-138, task 2026-10-08-1733--sae-dogfood-fixes (R4, R6, [MODEL-LISTS], DESIGN-DOCS); task 2026-10-12-1846--sae-findings-docs [CODEX-CATALOG-CHECK], [DOCTOR-CODEX-FAMILIES], [SETTINGS-CLAUDE-FAMILIES]
applies-to: [skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/setup_mode.py, skills/shape-and-execute/scripts/sae_lib/routing.py, skills/shape-and-execute/scripts/sae_lib/doctor.py, skills/shape-and-execute/assets/viewer/settings.js, model_entry, model_list_errors, routing_pair_errors, codex_catalog, codex_families, family_of, resolve_family, newest_of_family]
---

# Model lists per harness

## Context
Routing cells and tiers name models. Which models exist, which efforts they accept and which
the owner uses differ per harness and change over time.

## Decision
- [human] Per harness, a list of the models the owner uses, lightest to strongest. The place in
  the list sets the model's color; disabled entries keep their place, so unticking one recolors
  nothing. An entry is a family ("the newest of this family") or an exact older version picked
  from the models the harness offers, never typed: Codex from its catalog; Claude by family
  only. `sae` resolves a family at dispatch and records the exact model. Each entry records the
  efforts it accepts, so an invalid pair cannot be saved.
- [agent] Codex families resolve from the local catalog: the newest listed model whose name
  ends in the family word. An unticked or removed model is invalid in a cell or a tier.
- [human] When a Codex catalog is present, `sae setup save` and `sae doctor` refuse an exact
  version the catalog does not offer or hides, and an effort it does not list for that model;
  `sae doctor` checks that every enabled Codex family resolves. Without a catalog, validation
  stays as before. The viewer offers every known Claude family that is not in the list.

## Why
- Claude's Agent tool accepts family names only.
- A typed name or an invalid pair would fail only at dispatch, in the middle of a run.
- Haiku came back for mechanical work (R4).
- Without the catalog checks, entries the catalog does not offer passed `setup save`, and the
  owner could not add haiku or fable in the viewer (findings of 2026-10-10).

## Rejected options
- Typed model names.
