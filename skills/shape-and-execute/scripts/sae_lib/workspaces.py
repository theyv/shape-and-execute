"""Job branches, worktrees, ignored-file copy, setup script and dirty checks."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from pathlib import Path

from .common import EXIT_GIT, WRITER_KINDS, fail, warn, write_atomic
from .config import worktree_root
from .gitutil import git, git_ok, hash8, run
from .tasks import Task, tasks_dir


def job_branch(task: Task, job_id: str) -> str:
    return f"job/{task.id}/{job_id}"


def task_worktrees_dir(task: Task, config: dict) -> Path:
    return worktree_root(config) / f"{task.root.name}-{hash8(task.root)}" / task.id


def workspace_owner(task: Task, job_id: str) -> str:
    """Fix jobs work in the workspace of the job they fix."""
    fix = task.jobs[job_id].get("fix_of")  # a fix of an integration review round is an ordinary writer
    return fix if fix in task.jobs and task.jobs[fix]["kind"] in WRITER_KINDS else job_id


def workspace_of(task: Task, job_id: str, config: dict | None) -> tuple[Path, str | None]:
    """(workdir, branch) of a job, without creating anything."""
    job = task.jobs[job_id]
    if job["kind"] not in WRITER_KINDS or not task.info.get("git"):
        return task.root, None
    if not task.uses_worktrees:
        return task.root, task.info.get("branch")
    owner = workspace_owner(task, job_id)
    return task_worktrees_dir(task, config) / owner, job_branch(task, owner)


def tracked_changes_outside_tasks(root: Path) -> list[str]:
    proc = run(["git", "status", "--porcelain", "--untracked-files=no"], root)
    if proc.returncode != 0:
        fail(EXIT_GIT, f"git status failed: {proc.stderr.strip()}")
    paths = []
    for line in proc.stdout.splitlines():  # unstripped: the first column is significant
        path = line[3:].split(" -> ")[-1].strip('"')
        if not path.startswith(".tasks/"):
            paths.append(path)
    return paths


def require_on_task_branch(task: Task) -> None:
    branch = task.info.get("branch")
    current = git(task.root, "branch", "--show-current", check=False)
    if current != branch:
        fail(EXIT_GIT, f"The repository root is on {current or 'a detached HEAD'}, not on {branch}. "
                       f"Run: git switch {branch}")
    dirty = tracked_changes_outside_tasks(task.root)
    if dirty:
        fail(EXIT_GIT, "Tracked files outside .tasks/ have uncommitted changes in the repository root: "
                       + ", ".join(dirty[:10]))


def copy_worktree_includes(root: Path, worktree: Path) -> list[str]:
    copied = []
    for pattern_file in (tasks_dir(root) / "repo" / "worktreeinclude", root / ".worktreeinclude"):
        if not pattern_file.exists():
            continue
        listing = git(root, "ls-files", "--others", "--ignored", f"--exclude-from={pattern_file}", check=False)
        candidates = [line for line in listing.splitlines() if line]
        if not candidates:
            continue
        proc = subprocess.run(["git", "check-ignore", "--stdin"], cwd=str(root), input="\n".join(candidates),
                              capture_output=True, text=True)
        for path in proc.stdout.splitlines():
            source, dest = root / path, worktree / path
            if source.is_file() and not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                copied.append(path)
    return copied


def run_setup_script(root: Path, worktree: Path, task_id: str, job_id: str, log: Path) -> None:
    """Runs .tasks/repo/setup.sh in a new worktree; a non-zero exit is exit 4."""
    script = tasks_dir(root) / "repo" / "setup.sh"
    if not script.exists():
        return
    env = {**os.environ, "SAE_REPO_ROOT": str(root), "SAE_WORKTREE": str(worktree),
           "SAE_TASK": task_id, "SAE_JOB": job_id}
    proc = subprocess.run(["sh", str(script)], cwd=str(worktree), capture_output=True, text=True, env=env)
    write_atomic(log, f"$ sh {script}\nexit {proc.returncode}\n\n{proc.stdout}\n{proc.stderr}")
    if proc.returncode != 0:
        fail(EXIT_GIT, f"Worktree setup failed (exit {proc.returncode}). Log: {log}\n"
                       f"The worktree is kept for inspection: {worktree}")


def prepare_workspace(task: Task, job_id: str, config: dict | None) -> tuple[Path, str | None]:
    job = task.jobs[job_id]
    workdir, branch = workspace_of(task, job_id, config)
    if job["kind"] not in WRITER_KINDS or not task.info.get("git"):
        return workdir, branch
    if not task.uses_worktrees:
        require_on_task_branch(task)
        return workdir, branch
    owner = workspace_owner(task, job_id)
    fresh = not task.jobs[owner]["attempts"]
    if not workdir.exists():
        workdir.parent.mkdir(parents=True, exist_ok=True)
        if git_ok(task.root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
            git(task.root, "worktree", "add", str(workdir), branch)
        else:
            git(task.root, "worktree", "add", "-b", branch, str(workdir), task.info["branch"])
        copy_worktree_includes(task.root, workdir)
        fresh = True
    if fresh:
        run_setup_script(task.root, workdir, task.id, job_id, task.dir / "jobs" / f"{job_id}.setup.log")
        if job["kind"] == "integration" and job.get("target"):
            # The worker resolves the conflicts of this merge; a non-zero exit is expected.
            run(["git", "merge", "--no-commit", "--no-ff", job_branch(task, job["target"])], workdir)
    return workdir, branch


def remove_worktree(task: Task, path: Path) -> bool:
    if not path.exists():
        return True
    proc = run(["git", "worktree", "remove", str(path)], task.root)
    if proc.returncode != 0:
        warn(f"worktree kept (it has changes): {path}")
        return False
    return True


def remove_task_worktrees(task: Task, config: dict | None) -> list[str]:
    if not task.info.get("git") or config is None or "worktrees" not in config:
        return []
    folder = task_worktrees_dir(task, config)
    kept = []
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.is_dir() and not remove_worktree(task, path):
                kept.append(str(path))
        with contextlib.suppress(OSError):
            folder.rmdir()
    git(task.root, "worktree", "prune", check=False)
    return kept
