# shape-and-execute

This repository holds the shape-and-execute skill for Claude Code and Codex.

- `skills/shape-and-execute/`: the skill. `SKILL.md` is the entry point; `scripts/sae.py` is its
  CLI. Installs copy only this folder.
- `tests/`: the tests of `sae`. Run `python3 tests/run.py` from the repository root.
- `docs/adr/`: decision records. `docs/images/`: README images; their source is in
  `docs/images/src/` (see its README).
- `.tasks/`: the project's work log, kept by shape-and-execute (see [.tasks/README.md](.tasks/README.md)).
  Validation commands for tasks are in `.tasks/repo/profile.md`.

Rules:

- `sae` stays Python 3.9 or newer, standard library only.
- Development uses shape-and-execute itself: new work starts as a task or a backlog item in
  `.tasks/`. Edit `state.json` and `events.jsonl` only through `sae`.
- Write in English, in short sentences.
