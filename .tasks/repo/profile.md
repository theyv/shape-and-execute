---
adr_folder: docs/adr
---

# Repo profile

<!-- Facts only. Do not repeat what AGENTS.md or CLAUDE.md already say; link them instead. -->

## Validation commands
- Smoke: `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish` (main sae flow, about 6 s)
- Full suite: `python3 tests/run.py` (parallel runner, about 1 minute; `python3 tests/run.py <module|test>` runs a part)
