---
# artifact_language: en   # optional: pin the artifact language for everyone in this repository
# adr_folder: docs/adr     # optional: one flat folder for accepted decision records
# adr_rules:               # optional, instead: ADR rules, path prefix -> folder; longest prefix wins
#   - services/billing/ -> docs/adr/billing/
#   - services/claims/ -> docs/adr/claims/
---

# Repo profile

<!-- Facts, and the owner's Project Stakes. Do not repeat what AGENTS.md or CLAUDE.md
     already say; link them instead. -->

## Project Stakes
<!-- Why the project exists and how much care it needs. Every agent reads it.
     Example, a small game for a kid:
     - Who uses it and why: A game for a kid to play in the evenings.
     - Acceptable breakage: Any. We restart and laugh; at worst a high score is lost.
     - What matters now: Speed. We are still finding out what is fun.
     - Don't build: Save-file versioning or recovery for nearly impossible races.
     - So build it like: A toy.
     Do not name risky areas or exceptions here; hard limits belong in the repository
     instructions. When the owner does not set Project Stakes, keep only this line:
     - Not set by the owner. Set the bar yourself from the repository instructions and the
       README. Leaving out what it does not need is expected; never leave out what your job
       must deliver to be correct. -->
- Who uses it and why:
- Acceptable breakage:   <!-- how much, in one or two sentences; not a list -->
- What matters now:
- Don't build:           <!-- optional: only what agents have already overbuilt here -->
- So build it like:      <!-- a toy | a tool for friends | a product people pay for | a bank -->

## Validation commands
- Smoke:        <!-- seconds: the core path works; every job's verify adds it -->
- Full suite:   <!-- every test, the fastest way; runs once, in the final job -->
- Unit:
- Typecheck:
- Lint:
- End-to-end:

## Hot files
<!-- Files that many jobs tend to change: lockfiles, registries, migrations, barrel exports,
     translations. -->
-

## Worktree notes
<!-- What a fresh worktree needs. setup.sh does the work. -->
