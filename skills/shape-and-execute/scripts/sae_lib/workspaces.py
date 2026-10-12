"""Job branches, worktrees, ignored-file copy, setup script and dirty checks."""

from __future__ import annotations

import contextlib
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .common import EXIT_GIT, TASK_ID_RE, WRITER_KINDS, fail, read_json, read_text, warn, wrap_notice_lines, write_atomic
from .config import worktree_root
from .gitutil import git, git_ok, main_worktree, repo_cache_name, run
from .tasks import CLOSED_PHASES, Task, tasks_dir

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
        fail(EXIT_GIT, f"The task worktree {task.root} is on {current or 'a detached HEAD'}, not on {branch}. "
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


# Removal and preservation ([WORKTREE-CLEANUP], [TASK-WORKTREE-LIFECYCLE], 07-cli-spec §7.4).
# Automatic removal runs `git worktree remove` without --force, and only on worktrees proven
# clean; only `sae doctor --discard` forces it.


def unpreserved_work(worktree: Path, copies_from: list[Path] | tuple = ()) -> list[str]:
    """Tracked changes and untracked files that are not ignored. Ignored files (setup copies,
    dependencies) do not count, nor an untracked file byte-identical to the same path in one of
    `copies_from` (the files `sae start` copies into the task worktree)."""
    return worktree_status(worktree, copies_from)[0]


def worktree_status(worktree: Path, copies_from: list[Path] | tuple = ()) -> tuple[list[str], list[str]]:
    """One `git status` read: (unpreserved work, verified setup copies)."""
    proc = run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], worktree)
    if proc.returncode != 0:
        return [f"(git status failed: {proc.stderr.strip()})"], []
    work, copies, entries = [], [], proc.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            i += 1  # -z puts the rename source in the next field
        if code == "??" and setup_copy(worktree, path, copies_from):
            copies.append(path)
            continue
        work.append(path)
    return work, copies


def setup_copy(worktree: Path, path: str, copies_from) -> bool:
    mine = worktree / path
    for source in copies_from:
        other = Path(source) / path
        if other.resolve() != mine.resolve() and other.is_file() and mine.is_file() \
                and other.read_bytes() == mine.read_bytes():
            return True
    return False


def work_text(work: list[str]) -> str:
    return ", ".join(work[:5]) + (f" and {len(work) - 5} more" if len(work) > 5 else "")


def remove_empty_cache_folders(worktree: Path) -> None:
    """`<task-id>/` and `<repo>-<hash8>/` of the worktree cache, when nothing else is left."""
    for folder in (worktree.parent, worktree.parent.parent):
        with contextlib.suppress(OSError):
            folder.rmdir()


def remove_clean_worktree(repo: Path, path: Path, copies_from: list[Path] | tuple = ()) -> str | None:
    """Removes a worktree that holds no unpreserved work. Returns why it stays, or None."""
    if not path.exists():
        run(["git", "worktree", "prune"], repo)
        remove_empty_cache_folders(path)
        return None
    work, copies = worktree_status(path, copies_from)
    if work:
        return f"it holds uncommitted work: {work_text(work)}"
    for copy in copies:  # only the copies verified above, each checked again: git refuses them
        if setup_copy(path, copy, copies_from):
            (path / copy).unlink()
    # Anything created since the status read makes this plain remove fail: the worktree stays.
    proc = run(["git", "worktree", "remove", str(path)], repo)
    if proc.returncode != 0:
        return f"git refused to remove it: {(proc.stderr or proc.stdout).strip()}"
    run(["git", "worktree", "prune"], repo)
    remove_empty_cache_folders(path)
    return None


def task_copy_sources(task_info: dict, repo: Path) -> list[Path]:
    """Where the task worktree's untracked copies came from: the home checkout, the main worktree."""
    sources = [Path(task_info["home"])] if task_info.get("home") else []
    return sources + [main_worktree(repo)]


def keep_worktree(task: Task, path: Path, reason: str) -> str:
    warn(f"worktree kept, {reason}: {path}")
    task.event("worktree.kept", path=str(path), reason=reason)
    return f"{path}: {reason}"


def remove_worktree(task: Task, path: Path) -> bool:
    """A job worktree after its merge: removed unless it holds work, which is kept with a reason."""
    reason = remove_clean_worktree(task.root, path)
    if reason:
        keep_worktree(task, path, reason)
        return False
    return True


def remove_task_worktrees(task: Task, config: dict | None, with_task_worktree: bool = False) -> list[str]:
    """Job worktrees at finish and abandon (and the task worktree at abandon) under the
    preservation rule. A failed job's worktree stays for inspection. Returns "<path>: <reason>"
    for each kept worktree."""
    if not task.info.get("git") or config is None or "worktrees" not in config:
        return []
    folder = task_worktrees_dir(task, config)
    kept = []
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if not path.is_dir():
                continue
            if path.name == TASK_WORKTREE_NAME:
                if not with_task_worktree:
                    continue  # the task worktree stays after finish for the owner's tests
                reason = remove_clean_worktree(task.root, path, task_copy_sources(task.info, task.root))
            elif task.jobs.get(path.name, {}).get("status") == "failed":
                reason = "the job failed: kept for inspection"
            else:
                reason = remove_clean_worktree(task.root, path)
            if reason:
                kept.append(keep_worktree(task, path, reason))
        remove_empty_cache_folders(folder / TASK_WORKTREE_NAME)
    git(task.root, "worktree", "prune", check=False)
    return kept


def sae_worktrees(repo: Path) -> list[tuple[Path, str, str]]:
    """(path, task ID, name) of every registered worktree in this repository's cache folder:
    `<root>/<repo>-<hash8>/<task-id>/task|<JOB-ID>`."""
    listing = git(repo, "worktree", "list", "--porcelain", check=False)
    cache = repo_cache_name(repo)
    found = []
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):])
            if path.parent.parent.name == cache and TASK_ID_RE.match(path.parent.name):
                found.append((path, path.parent.name, path.name))
    return found


def record_in(worktree: Path, task_id: str) -> dict | None:
    """The task's state as the worktree holds it: `.tasks/done/<id>/` or `.tasks/<id>/`."""
    for folder in (tasks_dir(worktree) / "done" / task_id, tasks_dir(worktree) / task_id):
        with contextlib.suppress(OSError, ValueError):
            return read_json(folder / "state.json")
    return None


def merged_into_base(repo: Path, task_id: str, info: dict) -> str | None:
    """The base branch when `task/<id>` is merged into it, else None."""
    base = (info.get("base") or {}).get("branch")
    branch = info.get("branch") or f"task/{task_id}"
    if not base or not git_ok(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{base}"):
        return None
    return base if git_ok(repo, "merge-base", "--is-ancestor", f"refs/heads/{branch}", f"refs/heads/{base}") else None


def sweep_merged_task_worktrees(repo: Path, quiet: bool = False) -> tuple[list[str], list[str]]:
    """[TASK-WORKTREE-LIFECYCLE]: removes the task worktree of a finished task whose branch is
    merged into its base, and deletes that branch, when the worktree holds no unpreserved work.
    Runs in writing commands and `sae doctor`, never in read-only ones. Writes nothing into the
    finished task. Returns (removed lines, kept lines); kept lines are also printed."""
    if not git_ok(repo, "rev-parse", "--git-dir"):
        return [], []
    removed, kept = [], []
    for path, task_id, name in sae_worktrees(repo):
        if name != TASK_WORKTREE_NAME or not path.is_dir():
            continue
        state = record_in(path, task_id)
        info = (state or {}).get("task") or {}
        if info.get("phase") != "done":
            continue
        base = merged_into_base(repo, task_id, info)
        if not base:
            continue
        reason = remove_clean_worktree(repo, path, task_copy_sources(info, repo))
        if reason:
            line = f"{path}: task branch merged into {base}, but {reason}"
            kept.append(line)
            if not quiet:
                warn(f"task worktree kept, {line}. Commit or move it, or:\n"
                     f"  sae doctor --discard {shlex.quote(str(path))}")
            continue
        branch = info.get("branch") or f"task/{task_id}"
        # `-D` after the ancestry check above: `-d` compares with the HEAD of the checkout that runs
        # sae, which need not be the base branch. Nothing unmerged is lost.
        deleted = git_ok(repo, "branch", "-D", branch)
        line = (f"Removed the task worktree of {task_id} ({branch} is merged into {base})"
                + (f" and deleted {branch}." if deleted else f"; {branch} stays."))
        removed.append(line)
        if not quiet:
            print(wrap_notice_lines(line), file=sys.stderr)
    return removed, kept


def leftover_reason(repo: Path, path: Path, task_id: str, name: str, located: dict) -> tuple[str, bool]:
    """Why a worktree in the cache is still there ([WORKTREE-CLEANUP]: `sae doctor` lists it),
    and whether it needs the owner (it holds work, its job failed, or its task is closed)."""
    copy = located.get(task_id)
    state = None
    if copy is not None:
        with contextlib.suppress(OSError, ValueError):
            state = read_json(copy.folder / "state.json")
    state = state or record_in(path, task_id) or {}
    info, jobs = state.get("task") or {}, state.get("jobs") or {}
    phase = info.get("phase") or "unknown"
    work = unpreserved_work(path, task_copy_sources(info, repo) if name == TASK_WORKTREE_NAME else [])
    closed = phase in CLOSED_PHASES
    live = (name == TASK_WORKTREE_NAME and not closed and copy is not None and copy.live
            and copy.checkout.resolve() == path.resolve())
    if live:  # the task's own live folder is not work to save, and --discard refuses this worktree
        own = f".tasks/{task_id}/"
        work = [w for w in work if not w.startswith(own)]
    held = f"; it holds uncommitted work: {work_text(work)}" if work else ""
    if live:
        return f"task worktree of the live task ({phase}){held}", False
    if name == TASK_WORKTREE_NAME:
        if phase == "done":
            base = merged_into_base(repo, task_id, info)
            if base:
                return f"task finished and merged into {base}{held}", True
            return (f"task finished; {info.get('branch') or 'its branch'} is not merged into "
                    f"{(info.get('base') or {}).get('branch') or 'its base'} yet (test here, then merge){held}",
                    bool(work))
        return f"task worktree of a task in {phase}{held}", bool(work) or closed
    running = running_workspace_job(state, name)
    if running:
        return f"job running: {running}, task in {phase}{held}", False
    job = jobs.get(name) or {}
    if job.get("status") == "failed":
        return f"job {name} failed: kept for inspection{held}", True
    status = "merged" if job.get("merged") else job.get("status") or "not in the task's record"
    return f"job {name} is {status}, task in {phase}{held}", bool(work) or closed


def running_workspace_job(state: dict, name: str) -> str | None:
    """Find a running writer in this job worktree, including fixes that share its branch."""
    if (state.get("task") or {}).get("phase") in CLOSED_PHASES:
        return None
    jobs = state.get("jobs") or {}
    for job_id, job in jobs.items():
        if job.get("status") != "running" or job.get("kind") not in WRITER_KINDS:
            continue
        target = job.get("fix_of")
        owner = target if (jobs.get(target) or {}).get("kind") in WRITER_KINDS else job_id
        if owner == name:
            return job_id
    return None


def discard_worktree(repo: Path, target: Path, located: dict) -> list[str]:
    """`sae doctor --discard`: removes one worktree of this repository's cache although it holds
    work, after saying what is lost. Its branch stays."""
    target = target.resolve()
    match = next(((p, t, n) for p, t, n in sae_worktrees(repo) if p.resolve() == target), None)
    if match is None:
        fail(EXIT_GIT, f"{target} is not a sae worktree of this repository. List them:\n  sae doctor")
    path, task_id, name = match
    copy = located.get(task_id)
    state = None
    if copy is not None:
        with contextlib.suppress(OSError, ValueError):
            state = read_json(copy.folder / "state.json")
    state = state or record_in(path, task_id) or {}
    running = running_workspace_job(state, name)
    if running:
        fail(EXIT_GIT, f"Cannot discard: job running ({running}). Collect its result first.\nWorktree: {path}")
    if copy is not None and copy.live and copy.checkout.resolve() == target:
        phase = ""
        with contextlib.suppress(OSError, ValueError, KeyError):
            phase = read_json(copy.folder / "state.json")["task"]["phase"]
        if phase not in CLOSED_PHASES:
            fail(EXIT_GIT, f"Worktree: {target}\nIt holds the live folder of {task_id} ({phase}).\n"
                           f"Finish the task, or first run:\n  sae abandon {task_id} --reason \"...\"")
    work = unpreserved_work(path)
    lost = [f"Discarding {path}."]
    lost.append(f"Lost: {work_text(work)}." if work else "It holds no uncommitted work.")
    branch = git(path, "branch", "--show-current", check=False)
    proc = run(["git", "worktree", "remove", "--force", str(path)], repo)  # the owner's explicit word
    if proc.returncode != 0:
        fail(EXIT_GIT, f"git worktree remove failed: {(proc.stderr or proc.stdout).strip()}")
    run(["git", "worktree", "prune"], repo)
    remove_empty_cache_folders(path)
    lost.append(f"Branch {branch} stays." if branch else "No branch was checked out there.")
    return lost
