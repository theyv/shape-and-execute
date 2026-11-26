---
id: FIRST-RUN-WALKTHROUGH
covers: []
verify:
  - bash -n tests/tools/walkthrough/*.sh
scope:
  - tests/tools/walkthrough/**
---

# FIRST-RUN-WALKTHROUGH: A reusable first-run sandbox for the owner

## Objective
Build the tool in `tests/tools/walkthrough/` that starts a first-run session of the skill from
the current branch, as `specs.md` AMEND-4 describes, and prepare both scenarios for the owner.

## Inputs
- `specs.md` `## Amendments`, AMEND-4.
- `research/SANDBOX-ISOLATION.md`: the recommended approach and its commands, risks and open
  questions.
- The repository README (install steps of a new user).
- `.tasks/adr/2026-11-26-first-run-and-upgrade-changes-end-with-a.md` (draft).

## Scope
- One entry command with a short README in the folder: `start` a scenario (`fresh` or
  `upgrade`), and `clean` to delete the sandbox.
- Sandbox: a relocated `HOME` under a temporary folder, as the research recommends. The skill
  is installed the way the README tells a new user, from an export of the current branch.
- `upgrade` seeds a config without the `easy` column. Build it from the setup proposal before
  this task (`git show 3892f20:skills/shape-and-execute/references/modes/setup.md`), not from
  the owner's real config.
- Harness: Claude by default, with interactive `/login`. When `/login` cannot work under a
  relocated `HOME`, the tool says so and offers the `claude setup-token` path, where the
  owner types the token. Codex only with a flag (`--codex`), with a fresh `codex login`.
- The session opens in a new Orca terminal (`orca` CLI); without Orca, the tool prints the
  command to run.
- Guards: the tool refuses to run when the sandbox path is not under its temporary folder;
  `clean` deletes only that folder.

## Boundaries
- Hard stops: never read, copy or change the owner's credentials or configs (`~/.claude*`,
  `~/.ccs`, `~/.codex`, `~/.config/shape-and-execute`, APM files, Keychain). The owner logs in
  inside the sandbox.
- Do not launch a model session yourself. You may run the tool's steps that need no login
  (install, `sae doctor` in the sandbox) to prove them; then `clean`.
- No changes outside `tests/tools/walkthrough/`. A new problem becomes a finding.

## Expected output
Commits on the job branch; the result gives the exact commands the owner runs for each
scenario, what was proven without a login, and what stays unproven.

## Validation
- [ ] `fresh`: in the sandbox `sae doctor` shows no config; the skill files are inside the
  sandbox only.
- [ ] `upgrade`: `sae doctor` in the sandbox shows the `easy` fallback line.
- [ ] `clean` leaves nothing behind and touches nothing outside the sandbox.
