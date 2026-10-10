"""Task discovery, the Task record, events, job files, templates and job display helpers."""

from __future__ import annotations

import contextlib
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
from .markdown import has_content, md_section, split_frontmatter, strip_html_comments


def tasks_dir(root: Path) -> Path:
    return root / ".tasks"


def list_task_ids(root: Path) -> list[str]:
    folder = tasks_dir(root)
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir()
                  if p.is_dir() and TASK_ID_RE.match(p.name) and (p / "state.json").exists())


def resolve_task(root: Path, ref: str) -> str:
    ref = ref.rstrip("/").split("/")[-1]
    ids = list_task_ids(root)
    if ref in ids:
        return ref
    matches = [i for i in ids if i.endswith(ref)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        fail(EXIT_USAGE, f"No task matches {ref!r} in {tasks_dir(root)}.")
    fail(EXIT_USAGE, f"{ref!r} matches several tasks: {', '.join(matches)}. Use more of the ID.")


class Task:
    """One task folder. Changes are buffered and written by `save()`."""

    def __init__(self, root: Path, task_id: str):
        self.root = root
        self.id = task_id
        self.dir = tasks_dir(root) / task_id
        self.state: dict = {}
        self.settings: dict = {}
        self.new_events: list[dict] = []
        self.dirty = False

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

    def job(self, job_id: str) -> dict:
        if job_id not in self.jobs:
            fail(EXIT_USAGE, f"No job {job_id} in task {self.id}.")
        return self.jobs[job_id]

    def load(self) -> None:
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
        self.info["last_change"] = iso()
        write_json(self.state_path, self.state)
        if self.new_events:
            with self.events_path.open("a", encoding="utf-8") as handle:
                for event in self.new_events:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.new_events = []
        self.dirty = False

    def write_settings(self, settings: dict) -> None:
        write_json(self.settings_path, settings)
        self.settings = settings
        self.info["settings_seen"] = settings
        self.dirty = True


@contextlib.contextmanager
def open_task(root: Path, ref: str):
    """Locks the task, loads it, and saves it when the block ends without an exception.
    After the lock is released, a changed task re-renders the viewer data."""
    task = Task(root, resolve_task(root, ref))
    with (task.dir / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        task.load()
        yield task
        changed = task.dirty
        if changed:
            task.save()
    if changed:
        from .viewer import render_viewer_safely  # late import: viewer imports this module
        render_viewer_safely(root, [task.id])


def append_event_to(root: Path, ref: str, type_: str, **fields) -> None:
    """Appends one event to another task (backlog and finding sources)."""
    with open_task(root, ref) as task:
        task.event(type_, **fields)


def ensure_tasks_folder(root: Path) -> None:
    folder = tasks_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / ".gitignore").exists():
        write_atomic(folder / ".gitignore", ".viewer/\n.lock\n")
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
