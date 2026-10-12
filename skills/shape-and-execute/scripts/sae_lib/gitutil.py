"""Running processes and git; finding the repository root."""

from __future__ import annotations

import contextlib
import hashlib
import shutil
import subprocess
from pathlib import Path

from .common import EXIT_GIT, TASK_ID_RE, fail


# sae's own git operations run without the owner's hooks ([GIT-HOOKS-OFF-FOR-SAE],
# record 2026-10-10-sae-s-git-plumbing-skips-hooks.md):
# a hook that rewrites a tracked file would dirty the task worktree after every merge.
# Workers commit with their hooks; they never go through this module.
HOOKS_OFF = ["-c", "core.hooksPath=/dev/null"]


def run(cmd: list[str], cwd: Path, check: bool = False, timeout: float | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess:
    if cmd and cmd[0] == "git":
        cmd = ["git", *HOOKS_OFF, *cmd[1:]]
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


def configured_hooks_path(cwd: Path) -> str:
    """The owner's `core.hooksPath`, read without the override that `run` injects."""
    try:
        proc = subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=str(cwd),
                              capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_ok(cwd: Path, *args: str) -> bool:
    try:
        return run(["git", *args], cwd).returncode == 0
    except FileNotFoundError:
        return False


def hash8(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:8]


def worktree_paths(root: Path) -> list[Path]:
    """Every worktree of the repository that exists on disk, the main worktree first."""
    listing = git(root, "worktree", "list", "--porcelain", check=False)
    paths = [Path(line[len("worktree "):]) for line in listing.splitlines() if line.startswith("worktree ")]
    return [p for p in paths if p.is_dir()]


def main_worktree(root: Path) -> Path:
    """The repository's main worktree: the first entry of `git worktree list`
    (record 2026-10-10-every-task-executes-in-its-own-task-work.md)."""
    listing = git(root, "worktree", "list", "--porcelain", check=False)
    for line in listing.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):])
    return root


def repo_cache_name(root: Path) -> str:
    """`<repo>-<hash8>` of the worktree cache, named after the main worktree."""
    main = main_worktree(root)
    return f"{main.name}-{hash8(main)}"


def find_root() -> tuple[Path, bool]:
    """The repository root and whether it is a git repository.

    A task or job worktree (`<worktrees.root>/<repo>-<hash8>/<task-id>/task|<JOB-ID>`) resolves
    to the main worktree. Commands with a task argument find the task in any worktree anyway."""
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
