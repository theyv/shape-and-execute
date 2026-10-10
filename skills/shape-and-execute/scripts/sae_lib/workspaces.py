"""Job branches, worktrees, ignored-file copy, setup script and dirty checks."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from pathlib import Path

from .common import EXIT_GIT, WRITER_KINDS, fail, read_text, warn, write_atomic
from .config import worktree_root
from .gitutil import git, git_ok, main_worktree, repo_cache_name, run
from .tasks import Task, tasks_dir

TASK_WORKTREE_NAME = "task"  # job IDs are upper case, so it never collides


def job_branch(task: Task, job_id: str) -> str:
    return f"job/{task.id}/{job_id}"


def task_worktrees_dir(task: Task, config: dict) -> Path:
    """`<worktrees.root>/<repo>-<hash8>/<task-id>/`, named after the main worktree, so the home
    checkout, the task worktree and every job worktree compute the same folder."""
    return worktree_root(config) / repo_cache_name(task.root) / task.id


def task_worktree_path(task: Task, config: dict) -> Path:
    return task_worktrees_dir(task, config) / TASK_WORKTREE_NAME


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


def uncommitted_outside_tasks(root: Path) -> list[str]:
    """Tracked changes and untracked files that are not ignored, outside .tasks/."""
    proc = run(["git", "status", "--porcelain"], root)
    if proc.returncode != 0:
        return []
    paths = [line[3:].split(" -> ")[-1].strip('"') for line in proc.stdout.splitlines()]
    return [p for p in paths if not p.startswith(".tasks/")]


def require_on_task_branch(task: Task) -> None:
    branch = task.info.get("branch")
    current = git(task.root, "branch", "--show-current", check=False)
    if current != branch:
        fail(EXIT_GIT, f"The task checkout {task.root} is on {current or 'a detached HEAD'}, not on {branch}. "
                       f"Run there: git switch {branch}")
    dirty = tracked_changes_outside_tasks(task.root)
    if dirty:
        fail(EXIT_GIT, f"Tracked files outside .tasks/ have uncommitted changes in {task.root}: "
                       + ", ".join(dirty[:10]))


def running_checkout() -> Path | None:
    """The checkout that runs sae (the current directory's worktree), or None."""
    proc = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    return Path(proc.stdout.strip()) if proc.returncode == 0 else None


def include_pattern_files(live: Path) -> list[Path]:
    """`.tasks/repo/worktreeinclude` and a root `.worktreeinclude`, read from the checkout that
    holds the task's live folder."""
    return [f for f in (tasks_dir(live) / "repo" / "worktreeinclude", live / ".worktreeinclude") if f.exists()]


def ignored_matches(source: Path, pattern_file: Path) -> list[str]:
    listing = git(source, "ls-files", "--others", "--ignored", f"--exclude-from={pattern_file}", check=False)
    candidates = [line for line in listing.splitlines() if line]
    if not candidates:
        return []
    proc = subprocess.run(["git", "check-ignore", "--stdin"], cwd=str(source), input="\n".join(candidates),
                          capture_output=True, text=True)
    return proc.stdout.splitlines()


def pattern_matches_in(source: Path, pattern: str) -> bool:
    listing = git(source, "ls-files", "--others", "--ignored", "--directory", f"--exclude={pattern}", check=False)
    return bool(listing.strip())


def copy_worktree_includes(live: Path, worktree: Path) -> tuple[list[str], list[str]]:
    """Copies the ignored files listed for worktrees into a new worktree ([SETUP-SOURCE],
    DL-116): from the main worktree, and a file missing there from the checkout that runs sae.
    Returns (copied paths, patterns that match nothing in either place)."""
    sources = []
    for source in (main_worktree(live), running_checkout()):
        if source is not None and source.is_dir() and source.resolve() != worktree.resolve() \
                and source.resolve() not in [s.resolve() for s in sources]:
            sources.append(source)
    copied, missing = [], []
    for pattern_file in include_pattern_files(live):
        for source in sources:
            for path in ignored_matches(source, pattern_file):
                src, dest = source / path, worktree / path
                if src.is_file() and not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    copied.append(path)
        for line in (read_text(pattern_file, "") or "").splitlines():
            pattern = line.strip()
            if pattern and not pattern.startswith(("#", "!")) \
                    and not any(pattern_matches_in(source, pattern) for source in sources):
                missing.append(pattern)
    return copied, missing


def run_setup_script(live: Path, worktree: Path, task_id: str, job_id: str, log: Path,
                     notes: list[str] | None = None) -> None:
    """Runs .tasks/repo/setup.sh in a new worktree; a non-zero exit is exit 4."""
    script = tasks_dir(live) / "repo" / "setup.sh"
    head = "".join(f"{note}\n" for note in notes or [])
    if not script.exists():
        if head:
            write_atomic(log, head)
        return
    env = {**os.environ, "SAE_REPO_ROOT": str(main_worktree(live)), "SAE_WORKTREE": str(worktree),
           "SAE_TASK": task_id, "SAE_JOB": job_id}
    proc = subprocess.run(["sh", str(script)], cwd=str(worktree), capture_output=True, text=True, env=env)
    write_atomic(log, f"{head}$ sh {script}\nexit {proc.returncode}\n\n{proc.stdout}\n{proc.stderr}")
    if proc.returncode != 0:
        fail(EXIT_GIT, f"Worktree setup failed (exit {proc.returncode}). Log: {log}\n"
                       f"The worktree is kept for inspection: {worktree}")


def setup_worktree(live: Path, worktree: Path, task_id: str, job_id: str, log: Path) -> list[str]:
    """Setup of a new worktree (§7.3): ignored files, then setup.sh. Returns the report lines
    for listed files found nowhere; they are also printed and logged."""
    _, missing = copy_worktree_includes(live, worktree)
    notes = [f"setup: no ignored file matches {p!r} in the main worktree or in this checkout" for p in missing]
    for note in notes:
        warn(note)
    run_setup_script(live, worktree, task_id, job_id, log, notes)
    return notes


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
        fresh = True
        setup_worktree(task.root, workdir, task.id, job_id, task.dir / "jobs" / f"{job_id}.setup.log")
    elif fresh:
        run_setup_script(task.root, workdir, task.id, job_id, task.dir / "jobs" / f"{job_id}.setup.log")
    if fresh:
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
            if path.name == TASK_WORKTREE_NAME:
                continue  # the task worktree stays after finish for the owner's tests
            if path.is_dir() and not remove_worktree(task, path):
                kept.append(str(path))
        with contextlib.suppress(OSError):
            folder.rmdir()
    git(task.root, "worktree", "prune", check=False)
    return kept
