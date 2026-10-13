# scripts/

`sae.py` is the shape-and-execute CLI: Python 3.9 or newer, standard library only. It is the
entry point; the code lives in the package `sae_lib/` next to it, one module per area (see the
module docstrings; `cli.py` assembles the parser, each module defines the subcommands of its
own commands).

    python3 sae.py --help              # every command and the exit codes
    python3 sae.py <command> --help    # one command: usage, options, examples, exit codes

Main-session tokens (`sae_lib/session_tokens.py`): `new`, `approve`, `start`, `finish`, and
`dispatch` and `collect` during execution read the token total of the session that runs them
from the harness's own session file (Claude Code transcript, Codex rollout) and add a
`session.snapshot` event: harness, session ID, total; never conversation text. An unreadable
file or an unknown format adds nothing. Read-only commands read no session file.

Tests: `python3 tests/run.py [name ...]` from the repository root runs them in
parallel; `python3 -m unittest discover -s tests` still works. Shared helpers
are in `tests/saetest.py` (repository root).
