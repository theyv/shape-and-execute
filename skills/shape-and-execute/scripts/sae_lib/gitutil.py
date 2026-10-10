"""Running processes and git; finding the repository root."""

from __future__ import annotations

import contextlib
import hashlib
import shutil
import subprocess
from pathlib import Path

from .common import EXIT_GIT, TASK_ID_RE, fail


def run(cmd: list[str], cwd: Path, check: bool = False, timeout: float | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=check,
                          timeout=timeout, env=env)


def git(cwd: Path, *args: str, check: bool = True) -> str:
    try:
        proc = run(["git", *args], cwd)
    except FileNotFoundError:
        fail(EXIT_GIT, "git is not installed")
    if check and proc.returncode != 0:
        fail(EXIT_GIT, f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()}")
    return proc.stdout.strip()


def git_ok(cwd: Path, *args: str) -> bool:
    try:
        return run(["git", *args], cwd).returncode == 0
    except FileNotFoundError:
        return False


def hash8(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:8]


def find_root() -> tuple[Path, bool]:
    """The repository root and whether it is a git repository.

    A job worktree (`<worktrees.root>/<repo>-<hash8>/<task-id>/<JOB-ID>`) resolves to its main
    checkout, so a worker's `sae finding new` writes to the one live `.tasks/`."""
    cwd = Path.cwd()
    top = None
    with contextlib.suppress(FileNotFoundError):
        proc = run(["git", "rev-parse", "--show-toplevel"], cwd)
        if proc.returncode == 0:
            top = Path(proc.stdout.strip())
    if top is not None:
        common = git(top, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False)
        if common:
            main = Path(common).parent
            if (main != top and TASK_ID_RE.match(top.parent.name)
                    and top.parent.parent.name == f"{main.name}-{hash8(main)}"):
                return main, True
        return top, True
    for folder in (cwd, *cwd.parents):
        if (folder / ".tasks").is_dir():
            return folder, False
    return cwd, False


def git_user(root: Path) -> str:
    name = git(root, "config", "user.name", check=False) if shutil.which("git") else ""
    if name:
        return name
    import getpass
    return getpass.getuser()
