#!/usr/bin/env python3
"""sae: the command-line half of the shape-and-execute skill.

Agents decide; sae records, checks, computes and moves files and git refs. It never calls a
model, never pushes, and holds no configuration value of its own: models, routing tables, the
worktree root and the defaults for new tasks come from the user config.

Run `sae --help` for every command, `sae <command> --help` for one command.
Python >= 3.9, standard library only, non-interactive.

This file is the entry point. The code lives in the package sae_lib/ next to it; see README.md.
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # running sae must not leave __pycache__ in the skill folder
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sae_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
