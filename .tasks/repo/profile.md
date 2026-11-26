---
adr_folder: docs/adr
---

# Repo profile

<!-- Facts only. Do not repeat what AGENTS.md or CLAUDE.md already say; link them instead. -->

## Project Stakes
- Who uses it and why: The owner, daily, to build real projects and this skill itself. It is public and installable, so the first outside users may come any time.
- Acceptable breakage: Rough edges in the viewer, wording or setup are fine and get fixed as found. A bug that loses the user's work, task state or uncommitted files is not.
- What matters now: A lean, reliable core loop (shape, plan, execute) and sharp prompts: every line earns its place, whatever the length.
- Don't build: Backward compatibility or migrations for old configs and task records (no users yet), team features, deep Windows support. Small, quick Windows fixes are fine.
- So build it like: A solid personal tool getting ready for its first public users.

## Validation commands
- Smoke: `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish` (main sae flow, about 6 s)
- Full suite: `python3 tests/run.py` (parallel runner, about 1 minute; `python3 tests/run.py <module|test>` runs a part)

## Owner walkthrough
- A task that changes the first-run setup (the setup guide or proposal in `skills/shape-and-execute/references/modes/setup.md`, `setup_mode.py`, the config schema) or adds anything that asks the user for an action or an answer after an update gets a job `FIRST-RUN-WALKTHROUGH`: after the integration fixes, before the final validation, with a hold after it. The job runs the tool in `tests/tools/walkthrough/` (fresh install and upgrade; Claude by default, Codex on demand) and the owner walks through both. Why: the decision record "First-run and upgrade changes end with an owner walkthrough".

## Docs in sync
- A task that changes what users see (commands, setup, the viewer, texts the user reads) updates `README.md` in the same task. The `sae-release` skill checks it again before a release.
