"""Viewer data and the view command."""

from __future__ import annotations

import contextlib
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

from .common import (
    DEFAULT_MAX_VERIFY_FAILURES,
    EXIT_OK,
    SKILL_DIR,
    STAMPED_FILE_RE,
    VIEWER_VERSION,
    emit,
    iso,
    read_json,
    read_text,
    rel,
    sae_prefix,
    stamp_time,
    warn,
    write_atomic,
)
from .gitutil import find_root
from .markdown import first_heading, split_frontmatter
from .tasks import TaskCopy, locate_tasks, picked_up_items, resolve_task, tasks_dir


def render_viewer_safely(root: Path, task_ids: list[str] | None = None) -> Path | None:
    try:
        return render_viewer(root, task_ids)
    except Exception as exc:  # rendering never fails a command
        warn(f"viewer not rendered: {exc}")
        return None


def render_viewer(root: Path, task_ids: list[str] | None = None) -> Path:
    """Writes .tasks/.viewer/: the shell (when missing or older), data/index.js, and
    data/<task-id>.js for the given tasks (None: every task of every checkout)."""
    viewer = tasks_dir(root) / ".viewer"
    shell = SKILL_DIR / "assets" / "viewer" / "index.html"
    target = viewer / "index.html"
    if shell.exists():
        if viewer_version(target) < viewer_version(shell):
            viewer.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(shell, target)
    else:
        warn(f"viewer shell {shell} is missing; data only")
    located = locate_tasks(root)
    index = build_index(root, located)
    write_atomic(viewer / "data" / "index.js", "window.SAE_INDEX = " + json.dumps(index, ensure_ascii=False) + ";\n")
    wanted = set(located) if task_ids is None else set(task_ids) & set(located)
    for task_id in sorted(wanted):
        data = build_task_data(located[task_id].folder)
        write_atomic(viewer / "data" / f"{task_id}.js",
                     "window.SAE_TASKS = window.SAE_TASKS || {};\n"
                     f"window.SAE_TASKS[{json.dumps(task_id)}] = " + json.dumps(data, ensure_ascii=False) + ";\n")
    return target


def viewer_version(path: Path) -> int:
    text = read_text(path)
    if not text:
        return 0
    m = re.search(r'<meta\s+name="sae-viewer-version"\s+content="(\d+)"', text)
    return int(m.group(1)) if m else 0


def stamped_items(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.glob("*.md") if STAMPED_FILE_RE.match(p.name)), reverse=True)


def build_index(root: Path, located: dict[str, TaskCopy]) -> dict:
    """Every task of the repository ([TASK-WORKTREE], [DONE-FOLDER]): found in `.tasks/` and
    `.tasks/done/` of every worktree, the live copy first."""
    tasks = []
    for task_id, copy in located.items():
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            state = read_json(copy.folder / "state.json")
            counts: dict[str, int] = {}
            for job in state["jobs"].values():
                counts[job["status"]] = counts.get(job["status"], 0) + 1
            info = state["task"]
            entry = {"id": task_id, "title": info.get("title"), "phase": info.get("phase"),
                     "last_change": info.get("last_change"), "counts": counts,
                     "parked": counts.get("parked", 0), "plan_approved": "plan" in info.get("approvals", {}),
                     "branch": info.get("branch"), "worktree": info.get("worktree")}
            if copy.checkout.resolve() != root.resolve():
                entry["checkout"] = str(copy.checkout)
            tasks.append(entry)
    tasks.sort(key=lambda t: t["id"], reverse=True)
    findings = []
    for path in stamped_items(tasks_dir(root) / "findings"):
        meta, body = split_frontmatter(read_text(path, ""))
        findings.append({"file": rel(path, root), "title": first_heading(body) or path.stem,
                         "type": meta.get("type"), "confidence": meta.get("confidence"),
                         "source": meta.get("source"), "created": stamp_time(path.name), "text": body})
    backlog = []
    picked = picked_up_items(located)
    for path in stamped_items(tasks_dir(root) / "backlog"):
        meta, body = split_frontmatter(read_text(path, ""))
        title = first_heading(body) or path.stem
        backlog.append({"file": rel(path, root), "title": re.sub(r"^Intent:\s*", "", title),
                        "source": meta.get("source"), "created": stamp_time(path.name), "text": body,
                        "picked_up_by": picked.get(rel(path, root))})
    return {
        "generated": iso(), "viewer_version": VIEWER_VERSION, "repo": root.name, "root": str(root),
        "sae": sae_prefix(), "tasks": tasks, "findings": findings, "backlog": backlog,
        "closed_findings": read_text(tasks_dir(root) / "findings" / "closed.md", ""),
    }


def build_task_data(folder: Path) -> dict:
    files = {}
    for name in ("intent.md", "specs.md", "brief.md", "plan.md"):
        text = read_text(folder / name)
        if text is not None:
            files[name] = text
    for sub in ("jobs", "research", "reviews", "decisions"):
        directory = folder / sub
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix in (".md", ".log"):
                    files[f"{sub}/{path.name}"] = read_text(path, "")
    events = []
    for line in read_text(folder / "events.jsonl", "").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            if line.strip():
                events.append(json.loads(line))
    settings = None
    with contextlib.suppress(OSError, json.JSONDecodeError):
        settings = read_json(folder / "settings.json")
    return {"generated": iso(), "state": read_json(folder / "state.json"), "settings": settings,
            "settings_default_max_verify_failures": DEFAULT_MAX_VERIFY_FAILURES,
            "events": events, "files": files, "folder": str(folder)}


def cmd_view(args) -> int:
    root, _ = find_root()
    task_id = resolve_task(root, args.task) if args.task else None
    target = render_viewer(root, None)
    url = target.resolve().as_uri() + (f"#task={task_id}&tab=plan" if task_id else "")
    if args.open:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        if shutil.which(opener):
            subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            warn(f"{opener} not found; open the URL yourself")
    emit(args, url, {"url": url})
    return EXIT_OK


def register_view(sub, command):
    """Add the `view` command to the parser."""
    p = command(sub, "view", "Render the viewer and print its file:// URL.",
                "With a task, the URL opens its Plan tab. --open opens it in the browser.",
                ["view", "view claims-status --open"], [0, 1], cmd_view)
    p.add_argument("task", nargs="?")
    p.add_argument("--open", action="store_true")
