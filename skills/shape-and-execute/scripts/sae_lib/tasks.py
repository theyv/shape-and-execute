"""Task discovery, the Task record, events, job files, templates and job display helpers."""

from __future__ import annotations

import contextlib
import dataclasses
import fcntl
import json
from pathlib import Path

from .common import (
    EXIT_USAGE,
    SKILL_DIR,
    TASK_ID_RE,
    fail,
    iso,
    read_json,
    read_text,
    write_atomic,
    write_json,
)
from .config import settings_diff, settings_errors
from .gitutil import git, git_ok, worktree_paths
from .markdown import has_content, md_section, split_frontmatter, strip_html_comments


CLOSED_PHASES = ("done", "abandoned")  # no command writes into these records ([FINISHED-TASKS-READ-ONLY])


def tasks_dir(root: Path) -> Path:
    return root / ".tasks"


def list_task_ids(root: Path) -> list[str]:
    """Task IDs at the top of this checkout's `.tasks/` (not `.tasks/done/`, not other worktrees)."""
    folder = tasks_dir(root)
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir()
                  if p.is_dir() and TASK_ID_RE.match(p.name) and (p / "state.json").exists())


@dataclasses.dataclass
class TaskCopy:
    """One copy of a task folder in one checkout of the repository."""
    task_id: str
    checkout: Path      # the worktree that holds the folder
    folder: Path        # .tasks/<id>/ or .tasks/done/<id>/
    live: bool          # untracked in its worktree: the copy sae writes to
    last_change: str


def task_checkouts(root: Path) -> list[Path]:
    """Every checkout of the repository: `root` first, then the other worktrees (home checkout,
    task worktrees, job worktrees, other checkouts). Without git: `root` only."""
    if not git_ok(root, "rev-parse", "--git-dir"):
        return [root]
    resolved = root.resolve()
    return [root] + [p for p in worktree_paths(root) if p.resolve() != resolved]


def task_copies(root: Path) -> list[TaskCopy]:
    copies = []
    is_git = git_ok(root, "rev-parse", "--git-dir")
    for checkout in task_checkouts(root):
        folders = []
        for base in (tasks_dir(checkout), tasks_dir(checkout) / "done"):
            if base.is_dir():
                folders += [p for p in base.iterdir()
                            if p.is_dir() and TASK_ID_RE.match(p.name) and (p / "state.json").exists()]
        if not folders:
            continue
        tracked = set(git(checkout, "ls-files", "--", ".tasks", check=False).splitlines()) if is_git else set()
        for folder in folders:
            last = ""
            with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
                last = read_json(folder / "state.json")["task"].get("last_change") or ""
            state = (folder / "state.json").relative_to(checkout).as_posix()
            copies.append(TaskCopy(folder.name, checkout, folder, state not in tracked, last))
    return copies


def locate_tasks(root: Path) -> dict[str, TaskCopy]:
    """Task ID → the copy that counts ([TASK-WORKTREE], DL-110): searched in `.tasks/` and
    `.tasks/done/` of every worktree. The live (untracked) copy wins over a committed record;
    among equals the newest `task.last_change` wins."""
    best: dict[str, TaskCopy] = {}
    for copy in task_copies(root):
        current = best.get(copy.task_id)
        if current is None or (copy.live, copy.last_change) > (current.live, current.last_change):
            best[copy.task_id] = copy
    return best


def find_task(root: Path, ref: str) -> TaskCopy:
    ref = ref.rstrip("/").split("/")[-1]
    located = locate_tasks(root)
    if ref in located:
        return located[ref]
    matches = sorted(i for i in located if i.endswith(ref))
    if len(matches) == 1:
        return located[matches[0]]
    if not matches:
        fail(EXIT_USAGE, f"No task matches {ref!r} in any worktree of {root}.")
    fail(EXIT_USAGE, f"{ref!r} matches several tasks: {', '.join(matches)}. Use more of the ID.")


def resolve_task(root: Path, ref: str) -> str:
    return find_task(root, ref).task_id


def live_checkout(root: Path, ref: str) -> Path:
    """The checkout that holds the live folder of a task: the home checkout while shaping and
    planning, the task worktree during execution. Findings and decision drafts sourced from the
    task go there, so `sae start` and `sae finish` carry them ([DECISION-DRAFTS]). A finished or
    abandoned task: `root`."""
    copy = find_task(root, ref)
    return copy.checkout if copy.live and task_phase(copy) not in CLOSED_PHASES else root


def picked_up_items(located: dict[str, TaskCopy]) -> dict[str, str]:
    """Backlog file → the live task (not done or abandoned) that came from it ([BACKLOG-PICKUP])."""
    picked = {}
    for task_id, copy in located.items():
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            if read_json(copy.folder / "state.json")["task"]["phase"] in ("done", "abandoned"):
                continue
            first = read_text(copy.folder / "events.jsonl", "").split("\n", 1)[0]
            item = ((json.loads(first) if first.strip() else {}).get("from") or {}).get("file")
            if item:
                picked[item] = task_id
    return picked


class Task:
    """One task folder. Changes are buffered and written by `save()`.

    `root` is the checkout that holds the live folder: the home checkout while shaping and
    planning, the task worktree during execution, the checkout itself for an old task executing
    in place. `move_to` rebinds both when `sae start` moves the folder."""

    def __init__(self, root: Path, task_id: str, folder: Path | None = None):
        self.root = root
        self.id = task_id
        self.dir = folder or tasks_dir(root) / task_id
        self.state: dict = {}
        self.settings: dict = {}
        self.new_events: list[dict] = []
        self.dirty = False
        self.saved = False
        self.writable = True    # False: opened read-only; save() refuses ([READ-ONLY-COMMANDS])
        self.closed = False     # loaded as done or abandoned: save() refuses ([FINISHED-TASKS-READ-ONLY])

    # paths
    @property
    def state_path(self) -> Path:
        return self.dir / "state.json"

    @property
    def settings_path(self) -> Path:
        return self.dir / "settings.json"

    @property
    def events_path(self) -> Path:
        return self.dir / "events.jsonl"

    # shortcuts
    @property
    def info(self) -> dict:
        return self.state["task"]

    @property
    def jobs(self) -> dict:
        return self.state["jobs"]

    @property
    def phase(self) -> str:
        return self.info["phase"]

    @property
    def uses_worktrees(self) -> bool:
        return bool(self.info.get("git")) and self.info.get("layout") == "worktrees"

    @property
    def worktree(self) -> Path | None:
        """The task worktree, or None (not started, no git, or an old task executing in place)."""
        path = self.info.get("worktree")
        return Path(path) if path else None

    def move_to(self, root: Path) -> None:
        self.root = root
        self.dir = tasks_dir(root) / self.id

    def move_into_done(self) -> None:
        """[DONE-FOLDER]: `.tasks/<id>/` → `.tasks/done/<id>/` in the same checkout."""
        dest = tasks_dir(self.root) / "done" / self.id
        if dest.exists():
            fail(EXIT_USAGE, f"{dest} exists already. Move it away, then run the command again.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.dir.rename(dest)
        self.dir = dest

    def job(self, job_id: str) -> dict:
        if job_id not in self.jobs:
            fail(EXIT_USAGE, f"No job {job_id} in task {self.id}.")
        return self.jobs[job_id]

    def load(self, read_only: bool = False) -> None:
        """Reads state and settings. A writing load also logs an external settings change; a
        read-only load never does ([READ-ONLY-COMMANDS])."""
        self.state = read_json(self.state_path)
        try:
            settings = read_json(self.settings_path)
        except FileNotFoundError:
            fail(EXIT_USAGE, f"{self.settings_path} is missing.")
        except json.JSONDecodeError as exc:
            fail(EXIT_USAGE, f"{self.settings_path} is not valid JSON: {exc}")
        errors = settings_errors(settings)
        if errors:
            fail(EXIT_USAGE, f"{self.settings_path}: " + "; ".join(errors))
        self.settings = settings
        self.closed = self.phase in CLOSED_PHASES
        if read_only or self.closed:
            return  # a read-only load or a finished record logs no settings change
        seen = self.info.get("settings_seen")
        if seen != settings:
            changes = settings_diff(seen or {}, settings)
            if changes:
                self.event("settings.changed", changes=changes, by="external")
            self.info["settings_seen"] = settings
            self.dirty = True

    def event(self, type_: str, **fields) -> None:
        self.new_events.append({"at": iso(), "type": type_, **fields})
        self.dirty = True

    def touch(self, job: dict | None = None) -> None:
        if job is not None:
            job["last_change"] = iso()
        self.dirty = True

    def events(self) -> list[dict]:
        events = []
        text = read_text(self.events_path, "")
        for line in text.splitlines():
            if line.strip():
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(line))
        return events + self.new_events

    def save(self) -> None:
        if not self.writable:
            raise RuntimeError(f"task {self.id} was opened read-only")
        if self.closed:
            refuse_closed(self.id, self.phase)
        self.info["last_change"] = iso()
        write_json(self.state_path, self.state)
        if self.new_events:
            with self.events_path.open("a", encoding="utf-8") as handle:
                for event in self.new_events:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.new_events = []
        self.dirty = False
        self.saved = True

    def write_settings(self, settings: dict) -> None:
        if self.closed:
            refuse_closed(self.id, self.phase)
        write_json(self.settings_path, settings)
        self.settings = settings
        self.info["settings_seen"] = settings
        self.dirty = True


def refuse_closed(task_id: str, phase: str):
    fail(EXIT_USAGE, f"The task is {phase}; its record is read-only: {task_id}.")


@contextlib.contextmanager
def open_task(root: Path, ref: str, write: bool = True):
    """Locks the task, loads it, and saves it when the block ends without an exception (the
    block may also save it earlier). After the lock is released, a saved task re-renders the
    viewer data.

    `write=False` ([READ-ONLY-COMMANDS]): no lock file, no settings-change event, no save and
    no viewer render, so the command runs without write access. Changes made in the block are
    dropped; a command that finds it must change the task opens it again with `write=True`.

    A writing open of a done or abandoned task is refused ([FINISHED-TASKS-READ-ONLY]); a
    read-only open may load it, and its `save()` refuses either way. A block may still close
    an active task (finish, abandon)."""
    copy = find_task(root, ref)
    if write and task_phase(copy) in CLOSED_PHASES:
        refuse_closed(copy.task_id, task_phase(copy))
    task = Task(copy.checkout, copy.task_id, copy.folder)
    if not write:
        task.writable = False
        task.load(read_only=True)
        yield task
        return
    with (task.dir / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        task.load()
        yield task
        if task.dirty:
            task.save()
        changed = task.saved
    if changed:
        from .viewer import remember_repo_safely  # late import: viewer imports this module
        from .workspaces import sweep_merged_task_worktrees
        sweep_merged_task_worktrees(root)  # writing commands only ([TASK-WORKTREE-LIFECYCLE])
        remember_repo_safely(root)


def task_phase(copy: TaskCopy) -> str:
    with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
        return read_json(copy.folder / "state.json")["task"]["phase"]
    return ""


def append_event_to(root: Path, ref: str, type_: str, **fields) -> bool:
    """Appends one event to another task (finding and decision-draft sources). A finished or
    abandoned task gets nothing ([FINISHED-TASKS-READ-ONLY]). Returns whether it was written."""
    if task_phase(find_task(root, ref)) in CLOSED_PHASES:
        return False
    with open_task(root, ref) as task:
        task.event(type_, **fields)
    return True


def ensure_tasks_folder(root: Path) -> None:
    folder = tasks_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / ".gitignore").exists():
        write_atomic(folder / ".gitignore", ".lock\n")
    if not (folder / ".gitattributes").exists():
        write_atomic(folder / ".gitattributes", "findings/closed.md merge=union\n")


def template(name: str) -> str:
    text = read_text(SKILL_DIR / "templates" / name)
    if text is None:
        fail(EXIT_USAGE, f"Template {SKILL_DIR / 'templates' / name} is missing: the skill is incomplete.")
    return text


def new_job(kind: str, needs: list[str], difficulty: str, review: bool = False, final: bool = False,
            fix_of: str | None = None, target: str | None = None) -> dict:
    return {
        "kind": kind, "needs": needs, "difficulty": difficulty, "review": review, "final": final,
        "fix_of": fix_of, "target": target, "status": "pending", "merged": False,
        "review_rounds": 0, "last_change": iso(), "attempts": [], "commits": [],
    }


def is_generated(job_id: str, job: dict) -> bool:
    """Jobs that sae adds itself: reviews and integration jobs. They have no job file."""
    return job["kind"] == "review" or job_id.startswith("INTEGRATE-")


def job_file(task: Task, job_id: str) -> Path:
    return task.dir / "jobs" / f"{job_id}.md"


def result_file(task: Task, job_id: str) -> Path:
    kind = task.jobs[job_id]["kind"]
    if kind == "research":
        return task.dir / "research" / f"{job_id}.md"
    if kind == "review":
        return task.dir / "reviews" / f"{job_id}.md"
    if kind == "decision":
        return task.dir / "decisions" / f"{job_id}.md"
    return task.dir / "jobs" / f"{job_id}.result.md"


def job_meta(task: Task, job_id: str) -> dict:
    text = read_text(job_file(task, job_id))
    return split_frontmatter(text)[0] if text else {}


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None and v != ""]
    return [value]


def last_model(job: dict) -> str:
    if not job["attempts"]:
        return "-"
    attempt = job["attempts"][-1]
    effort = f" ({attempt['effort']})" if attempt.get("effort") else ""
    return f"{attempt['model']}{effort}"


def job_summary(task: Task, job_id: str) -> str:
    job = task.jobs[job_id]
    return job.get("summary") or ""


def parked_reason(task: Task, job_id: str) -> str:
    summary = job_summary(task, job_id)
    path = result_file(task, job_id)
    text = read_text(path)
    if text:
        request = md_section(split_frontmatter(text)[1], "Decision request")
        if has_content(request):
            first = [l.strip() for l in strip_html_comments(request).splitlines() if l.strip()][:2]
            return (summary + " — " if summary else "") + " ".join(first)
    return summary or "see the result file"
