"""The viewer server: serves assets/viewer/, reads task data
live from every worktree of every known repository, and writes only by running `sae` itself.

Routes (GET reads need no token; every POST needs `X-SAE-Token` and a same-origin `Origin`):
  /                      the viewer shell, with the token embedded
  /<file>.css|.js        the viewer files
  /api/health            pid, port, version (used by `sae view` to reuse a server)
  /api/projects          the known repositories
  /api/repo?repo=K       tasks with location, findings (open; closed with the task that closed them),
                         backlog, decision drafts
  /api/task?repo=K&task=ID         one task: files, events, the process-map steps, routing,
                                   effective difficulty, review marks, waits, next, finish readiness,
                                   per-phase stats, changed lines
  /api/settings?repo=K[&task=ID]   effective settings with sources, project entry, config,
                                   Codex catalog, known Claude families
  /proto/K/ID/<path>     a file under the task's prototypes/ (sandboxed); the folder structure
                         is kept in the URL, so relative CSS, scripts, images and links load
  POST /api/<route>      a write route of WRITE_ROUTES; body JSON {repo, …}
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import http.server
import json
import mimetypes
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

from .common import (
    DEFAULT_MAX_REVIEW_ROUNDS,
    DEFAULT_MAX_VERIFY_FAILURES,
    JOB_ID_RE,
    SKILL_DIR,
    SaeError,
    iso,
    read_json,
    read_text,
    rel,
    sae_prefix,
    stamp_time,
)
from .config import upgrade_level_names
from .viewer import (
    VIEWER_ASSETS,
    code_version,
    idle_limit,
    known_repos,
    read_state,
    state_path,
    stamped_items,
    write_private,
)

STATIC_FILES = ("app.css", "app.js", "task-views.css", "task-views.js", "settings.css", "settings.js",
                "favicon.svg", "favicon-wait.svg")
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
TOKEN_META = '<meta name="sae-token" content="">'
MAX_BODY = 2 * 1024 * 1024
WRITE_TIMEOUT_S = 120
CHANGED_BY_ENV = "SAE_CHANGED_BY"   # common.changed_by(): events of a viewer write say by: viewer
PAGE_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'")
# A prototype runs in an opaque origin: it can show itself, never read the viewer or post as it.
FILE_CSP = "sandbox allow-scripts allow-forms allow-popups; frame-ancestors 'self'"


class RequestError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- reads

def repo_by_key(key: str | None) -> Path:
    for repo in known_repos():
        if repo.get("key") == key:
            return Path(repo["path"])
    raise RequestError(404, f"Unknown repository {key!r}. Run sae view in it once.")


def projects_data() -> dict:
    return {"projects": [{"key": r["key"], "name": r["name"], "path": r["path"], "last_seen": r.get("last_seen")}
                         for r in known_repos()]}


def merged_items(root: Path, sub: str) -> list[tuple[Path, Path]]:
    """(checkout, file) of `.tasks/<sub>/*.md` in every checkout, one per file name, the
    repository's main worktree first ([VIEWER-ALL-WORKTREES])."""
    from .tasks import task_checkouts, tasks_dir
    seen: dict[str, tuple[Path, Path]] = {}
    for checkout in task_checkouts(root):
        folder = tasks_dir(checkout) / sub
        files = stamped_items(folder, areas=sub == "backlog") if sub != "adr" else (
            sorted((p for p in folder.glob("*.md") if p.name != "closed.md"), reverse=True) if folder.is_dir() else [])
        for path in files:
            seen.setdefault(path.name, (checkout, path))
    return sorted(seen.values(), key=lambda item: item[1].name, reverse=True)


def task_location(copy, info: dict) -> tuple[str, str]:
    """Where a task is: `.tasks/done/`, its task worktree, its home checkout, or another checkout."""
    path = str(copy.checkout)
    if copy.folder.parent.name == "done":
        return "done", str(copy.folder.parent)
    if info.get("worktree") and Path(info["worktree"]).expanduser().resolve() == copy.checkout.resolve():
        return "task worktree", path
    if info.get("home") and Path(info["home"]).expanduser().resolve() == copy.checkout.resolve():
        return "home checkout", path
    return "checkout", path


def hold_count(info: dict) -> int:
    holds = info.get("holds")
    if isinstance(holds, (list, dict)):
        return len(holds)
    return 0


CLOSED_BY_RE = re.compile(r"^fixed in (\S+?)(?: by (\S+))?$")


def closed_findings_list(text: str) -> list[dict]:
    """The lines of `closed.md` (`- <date> · <stem> · <title> · <outcome>`), newest last, with the
    task (and job) that closed each one when its outcome says `fixed in <task-id> [by <JOB-ID>]`
    ([SCOPE-TOGGLE]: the Findings tab shows the findings a task closed)."""
    out = []
    for line in text.splitlines():
        if not line.lstrip().startswith(("-", "*")):
            continue
        parts = [p.strip() for p in line.lstrip("-* ").split(" · ")]
        if len(parts) < 4:
            out.append({"date": "", "stem": "", "title": " · ".join(parts), "outcome": "", "task": None, "job": None})
            continue
        outcome = parts[-1]
        m = CLOSED_BY_RE.match(outcome)
        out.append({"date": parts[0], "stem": parts[1], "title": " · ".join(parts[2:-1]), "outcome": outcome,
                    "task": m.group(1) if m else None, "job": m.group(2) if m else None})
    return out


def repo_data(key: str) -> dict:
    from .markdown import first_heading, split_frontmatter
    from .tasks import locate_tasks, picked_up_items, tasks_dir
    root = repo_by_key(key)
    located = locate_tasks(root)
    tasks = []
    for task_id, copy in located.items():
        with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
            state = read_json(copy.folder / "state.json")
            info = state["task"]
            counts: dict[str, int] = {}
            for job in state["jobs"].values():
                counts[job["status"]] = counts.get(job["status"], 0) + 1
            location, where = task_location(copy, info)
            entry = {"id": task_id, "title": info.get("title"), "phase": info.get("phase"),
                     "last_change": info.get("last_change"), "counts": counts, "parked": counts.get("parked", 0),
                     "holds": hold_count(info), "plan_approved": "plan" in info.get("approvals", {}),
                     "branch": info.get("branch"), "worktree": info.get("worktree"), "home": info.get("home"),
                     "location": location, "location_path": where, "folder": str(copy.folder)}
            if copy.checkout.resolve() != root.resolve():
                entry["checkout"] = str(copy.checkout)
            tasks.append(entry)
    tasks.sort(key=lambda t: t["id"], reverse=True)
    from .findings import closed_lines, closed_text
    closed = closed_lines(root)  # [CLOSED-VISIBLE]: closed in any counting checkout
    findings = []
    for checkout, path in merged_items(root, "findings"):
        if path.stem in closed:
            continue
        meta, body = split_frontmatter(read_text(path, ""))
        findings.append({"file": rel(path, checkout), "path": str(path), "title": first_heading(body) or path.stem,
                         "type": meta.get("type"), "confidence": meta.get("confidence"),
                         "source": meta.get("source"), "created": stamp_time(path.name), "text": body})
    picked = picked_up_items(located)
    backlog = []
    for checkout, path in merged_items(root, "backlog"):
        meta, body = split_frontmatter(read_text(path, ""))
        title = re.sub(r"^Intent:\s*", "", first_heading(body) or path.stem)
        backlog.append({"file": rel(path, checkout), "path": str(path), "title": title, "source": meta.get("source"),
                        "created": stamp_time(path.name), "text": body,
                        "picked_up_by": picked.get(rel(path, checkout))})
    drafts = []
    for checkout, path in merged_items(root, "adr"):
        meta, body = split_frontmatter(read_text(path, ""))
        drafts.append({"file": rel(path, checkout), "path": str(path), "title": meta.get("title") or first_heading(body)
                       or path.stem, "type": meta.get("type"), "status": meta.get("status"),
                       "source": meta.get("source"), "date": str(meta.get("date") or path.name[:10]), "text": body})
    open_drafts = sum(1 for d in drafts if d["status"] in (None, "proposed"))
    closed_md = closed_text(root)
    return {"repo": root.name, "root": str(root), "key": key, "sae": sae_prefix(), "tasks": tasks,
            "findings": findings, "backlog": backlog, "drafts": drafts, "open_drafts": open_drafts,
            "closed_findings": closed_md, "closed_list": closed_findings_list(closed_md)}


def load_config_quietly() -> tuple[dict | None, str | None]:
    from .config import load_config
    try:
        return load_config(required=False), None
    except SaeError as exc:
        return None, str(exc)


def task_files(folder: Path) -> dict:
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
    return files


def prototype_files(folder: Path, key: str, task_id: str) -> list[dict]:
    base = folder / "prototypes"
    if not base.is_dir():
        return []
    out = []
    for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.name.startswith(".")):
        name = path.relative_to(folder).as_posix()
        out.append({"path": name, "size": path.stat().st_size,
                    "url": prototype_url(key, task_id, path.relative_to(base).as_posix())})
    return out


PROTO_PREFIX = "/proto/"


def prototype_url(key: str, task_id: str, inner: str) -> str:
    """/proto/<repo>/<task>/<path under prototypes/>: a prototype's relative links stay inside it."""
    return PROTO_PREFIX + "/".join(urllib.parse.quote(part, safe="") for part in [key, task_id, *inner.split("/")])


def computed(task, config: dict | None) -> dict:
    """What the views need, from the same functions as the CLI (`sae next`)."""
    from .progress import next_data, task_status_data
    from .reviews import finish_readiness, next_review_rounds, planned_reviews, review_mark
    from .control import map_steps
    from .routing import PLANNER_ID, job_context, planned_planner, resolve_model
    from .graph import active_holds, waits_for
    from .asks import owner_wait
    out: dict = {"routing": {}, "review_marks": {}, "planned_reviews": [], "next": None, "status": None,
                 "waits": {}, "holds_active": [], "difficulty": {}}
    # readiness for the graph and job panels: the rules of `sae next`, never a copy in app.js
    with contextlib.suppress(Exception):
        out["waits"] = {i: waits_for(task, i) for i, j in task.jobs.items() if j["status"] == "pending"}
        out["holds_active"] = active_holds(task)
    for job_id in task.jobs:
        with contextlib.suppress(Exception):
            out["review_marks"][job_id] = review_mark(task, job_id)
        # the effective difficulty, as `sae next` shows it ([DIFFICULTY-DISPLAY])
        with contextlib.suppress(Exception):
            out["difficulty"][job_id] = job_context(task, job_id)["difficulty"]
    with contextlib.suppress(Exception):
        out["status"] = task_status_data(task)
    # the steps of the Shape and Plan cards and the Finish card's readiness ([GRAPH-PHASE-CARDS], [GRAPH-PLACEHOLDER-FINISH])
    out["steps"], out["finish"] = [], None
    with contextlib.suppress(Exception):
        out["steps"] = map_steps(task)
    with contextlib.suppress(Exception):
        out["finish"] = finish_readiness(task)
    # open asks and what waits for the owner ([WAIT-FRAMES], [WAIT-TAB-TITLE]); `waiting` is empty outside executing
    out["asks"], out["waiting"] = [], []
    with contextlib.suppress(Exception):
        out.update(owner_wait(task))
    if config is None:
        return out
    try:
        # the reviews sae will add, then the next round of a changes-required round while its fixes are open
        out["planned_reviews"] = planned_reviews(task, config) + next_review_rounds(task, config)
    except Exception as exc:
        out["planned_reviews_error"] = str(exc)
    # the planner job PLAN before it exists: its routing, and `sae job override <task> PLAN` sets its model
    out["planned_planner"] = None
    with contextlib.suppress(Exception):
        out["planned_planner"] = PLANNER_ID if planned_planner(task) else None
    # a next round routes as the round before it (`like`); its own ID resolves to nothing yet
    like = {p["id"]: p.get("like") or p["id"] for p in out["planned_reviews"]}
    if out["planned_planner"]:
        like[PLANNER_ID] = PLANNER_ID
    for job_id, as_id in like.items():
        with contextlib.suppress(Exception):
            out["difficulty"][job_id] = job_context(task, as_id)["difficulty"]
    for job_id, as_id in [(i, i) for i in task.jobs] + list(like.items()):
        try:
            out["routing"][job_id] = resolve_model(task, as_id, config, exact=False)
        except Exception as exc:  # incomplete routing: the view shows why
            out["routing"][job_id] = {"error": str(exc).splitlines()[0]}
    if task.phase == "executing":
        try:
            out["next"] = next_data(task, config)
        except Exception as exc:
            out["next"] = {"error": str(exc).splitlines()[0]}
    return out


SHORTSTAT_RE = re.compile(r"(\d+) (file|insertion|deletion)")
GIT_LINES_CACHE: dict = {}  # (checkout, from, to) -> counts: two commits always give the same diff


def merged_start(checkout: Path, tip: str, base_tip: str, run) -> str:
    """The merge base of a task branch already merged into its base branch and kept: computed
    against the base as it stood just before the merge commit that brought the tip in (its first
    parent), so newer base commits the task took before merging are not counted. "" when no such
    merge commit exists (a fast-forward, or the base tip is the task tip): the history no longer
    tells the task's own commits from the base's, so the number is missing, never wrong."""
    proc = run(["git", "rev-list", "--first-parent", "--ancestry-path", f"{tip}..{base_tip}"], checkout)
    chain = proc.stdout.split() if proc.returncode == 0 else []
    if not chain:
        return ""
    proc = run(["git", "rev-list", "--parents", "-n", "1", chain[-1]], checkout)
    parents = proc.stdout.split()[1:] if proc.returncode == 0 else []
    if len(parents) < 2 or parents[0] == tip:
        return ""
    proc = run(["git", "merge-base", parents[0], tip], checkout)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_lines(checkout: Path, info: dict) -> dict | None:
    """The task's changed lines ([GIT-LINES]): `git diff --shortstat` from the merge base of the
    base branch and the task branch to the task branch tip, as {added, removed, files}. None
    without a task branch (not started, or deleted after merge) or after a fast-forward merge:
    missing, never wrong. A task branch still at its start commit gives zeros."""
    from .gitutil import run
    branch, base = info.get("branch"), info.get("base") or {}
    if not info.get("git") or not branch:
        return None

    def rev(ref: str) -> str | None:
        proc = run(["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"], checkout)
        return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None

    tip = rev("refs/heads/" + branch)
    if tip is None:
        return None
    # a deleted base branch: the commit the task started from stands in for it
    base_tip = (rev("refs/heads/" + base["branch"]) if base.get("branch") else None) or (
        rev(base["commit"]) if base.get("commit") else None)
    if base_tip is None:
        return None
    proc = run(["git", "merge-base", base_tip, tip], checkout)
    start = proc.stdout.strip() if proc.returncode == 0 else ""
    if start == tip:
        # still at the commit the task started from: nothing merged into the task branch yet
        started = rev(base["commit"]) if base.get("commit") else None
        start = tip if started == tip else merged_start(checkout, tip, base_tip, run)
    if not start:
        return None
    key = (str(checkout), start, tip)
    if key not in GIT_LINES_CACHE:
        proc = run(["git", "diff", "--shortstat", start, tip], checkout)
        if proc.returncode != 0:
            return None
        counts = {kind: int(n) for n, kind in SHORTSTAT_RE.findall(proc.stdout)}
        GIT_LINES_CACHE[key] = {"added": counts.get("insertion", 0), "removed": counts.get("deletion", 0),
                                "files": counts.get("file", 0)}
    return dict(GIT_LINES_CACHE[key])


def task_data(key: str, task_id: str | None) -> dict:
    from .tasks import Task, locate_tasks
    root = repo_by_key(key)
    copy = locate_tasks(root).get(task_id or "")
    if copy is None:
        raise RequestError(404, f"No task {task_id!r} in {root}.")
    folder = copy.folder
    events = []
    for line in read_text(folder / "events.jsonl", "").splitlines():
        with contextlib.suppress(ValueError):
            if line.strip():
                events.append(json.loads(line))
    settings = None
    with contextlib.suppress(OSError, ValueError):
        settings = upgrade_level_names(read_json(folder / "settings.json"))
    state = read_json(folder / "state.json")
    location, where = task_location(copy, state["task"])
    data = {"state": state, "settings": settings, "settings_default_max_verify_failures": DEFAULT_MAX_VERIFY_FAILURES,
            "settings_default_max_review_rounds": DEFAULT_MAX_REVIEW_ROUNDS,
            "events": events, "files": task_files(folder), "folder": str(folder), "location": location,
            "location_path": where, "worktree": state["task"].get("worktree"),
            "overrides": state["task"].get("overrides") or {},
            "prototypes": prototype_files(folder, key, copy.task_id)}
    # the Overview's numbers, computed here so the page only draws them ([OVERVIEW-PHASE-STATS], [GIT-LINES])
    data["phase_stats"], data["git_lines"] = None, None
    with contextlib.suppress(Exception):
        from .session_tokens import phase_stats
        data["phase_stats"] = phase_stats(state, events)
        for row in data["phase_stats"]:  # a running phase's wall time grows each second: the page counts it
            if row["running"]:            # from `started`, so the answer's version stays put between changes
                row["wall_s"] = None
    with contextlib.suppress(Exception):
        data["git_lines"] = git_lines(copy.checkout, state["task"])
    task = Task(copy.checkout, copy.task_id, folder)
    try:
        task.load()  # read only: nothing is saved
    except SaeError as exc:
        data["error"] = str(exc)
        return data
    config, config_error = load_config_quietly()
    if config_error:
        data["config_error"] = config_error
    data["models"] = (config or {}).get("models")  # the model lists set the palette (app.js modelColor)
    data.update(computed(task, config))
    return data


def level_sources(task_settings: dict | None, global_defaults: dict, project_defaults: dict) -> dict:
    """{settings key: global | project | task}: the level each task value comes from. A value
    equal to the project's own value is `project`, equal to the global default `global`."""
    from .config import defaults_as_settings, flatten_settings, merge_defaults
    global_flat = flatten_settings(defaults_as_settings(global_defaults))
    project_flat = flatten_settings(defaults_as_settings(merge_defaults(global_defaults, project_defaults)))
    out = {}
    for name, value in flatten_settings(task_settings or {}).items():
        if not name.startswith("routing.") and _project_sets(project_defaults, name) and value == project_flat.get(name):
            out[name] = "project"
        elif not name.startswith("routing.") and value == global_flat.get(name):
            out[name] = "global"
        else:
            out[name] = "task"
    return out


def _project_sets(defaults: dict, flat_name: str) -> bool:
    node = defaults
    for part in flat_name.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def settings_data(key: str, task_id: str | None) -> dict:
    from .common import HARNESSES
    from .config import effective_routing, routing_layers
    from .setup_mode import CLAUDE_FAMILIES, codex_catalog
    root = repo_by_key(key)
    config, config_error = load_config_quietly()
    project = ((config or {}).get("projects") or {}).get(str(root)) or {}
    task_settings = None
    if task_id:
        from .tasks import locate_tasks
        copy = locate_tasks(root).get(task_id)
        if copy is None:
            raise RequestError(404, f"No task {task_id!r} in {root}.")
        with contextlib.suppress(OSError, ValueError):
            task_settings = upgrade_level_names(read_json(copy.folder / "settings.json"))
    routing = {}
    if config:
        layers = routing_layers(config, root, task_settings, project=project)
        for harness in HARNESSES:
            if harness not in (config.get("routing") or {}):
                continue
            eff = effective_routing(layers, harness)
            routing[harness] = {
                "tiers_in_cells": dict(zip(("value", "source"), eff.get("tiers_in_cells", (True, None)))),
                "tiers": {n: {"value": v, "source": s} for n, (v, s) in eff["tiers"].items()},
                "tables": {p: {lv: {d: {"value": c, "source": s} for d, (c, s) in row.items()}
                               for lv, row in table.items()} for p, table in eff["tables"].items()}}
    return {"project_key": str(root), "project": project, "config": config, "config_error": config_error,
            "task": task_id, "task_settings": task_settings,
            "sources": level_sources(task_settings, (config or {}).get("defaults") or {}, project.get("defaults") or {})
            if task_settings and config else {},
            "routing": routing, "codex_catalog": codex_catalog(), "claude_families": list(CLAUDE_FAMILIES)}


def prototype_path(url_path: str) -> Path:
    """The file of /proto/<repo>/<task>/<path>; a folder serves its index.html. Only files
    under the task's prototypes/ are served: `..`, encoded or not, and symlinks out are 404."""
    from .tasks import locate_tasks
    parts = [urllib.parse.unquote(p) for p in url_path[len(PROTO_PREFIX):].split("/")]
    if len(parts) < 3 or not parts[0] or not parts[1] or any("\0" in p or "\\" in p for p in parts):
        raise RequestError(404, "No such file.")
    root = repo_by_key(parts[0])
    copy = locate_tasks(root).get(parts[1])
    if copy is None:
        raise RequestError(404, "No such file.")
    base = (copy.folder / "prototypes").resolve()
    target = base.joinpath(*[p for p in parts[2:] if p]).resolve()
    if target.is_dir():
        target = (target / "index.html").resolve()
    if base not in target.parents or not target.is_file():
        raise RequestError(404, "Only files under the task's prototypes/ are served.")
    return target


def versioned(data: dict) -> dict:
    """Adds `version` (changes exactly when the data changes) and `generated`."""
    data["version"] = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]
    data["generated"] = iso()
    return data


# ---------------------------------------------------------------- writes

def _plain(value, what: str) -> str:
    """One argument for `sae`: a non-empty string that cannot be read as an option."""
    if not isinstance(value, str) or not value or value.startswith("-") or "\n" in value:
        raise RequestError(400, f"{what}: expected a plain string, got {value!r}.")
    return value


def _plain_list(value, what: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RequestError(400, f"{what}: expected a non-empty list.")
    return [_plain(v, what) for v in value]


def route_set(body: dict):
    return ["set", _plain(body.get("task"), "task"), *_plain_list(body.get("pairs"), "pairs")], None


def route_override(body: dict):
    job = _plain(body.get("job"), "job")
    if not JOB_ID_RE.match(job):
        raise RequestError(400, f"job: {job!r} is not a job ID.")
    argv = ["job", "override", _plain(body.get("task"), "task"), job]
    if body.get("review"):
        argv.append("--review")
    if body.get("clear"):
        argv.append("--clear")
    for name in ("harness", "model", "effort", "reason"):
        if body.get(name):
            argv += [f"--{name}", _plain(body[name], name)]
    return argv, None


def route_hold(body: dict):
    job = _plain(body.get("job"), "job")
    if not JOB_ID_RE.match(job):
        raise RequestError(400, f"job: {job!r} is not a job ID.")
    argv = ["hold", _plain(body.get("task"), "task"), job]
    if body.get("release"):
        argv.append("--release")
    if body.get("reason"):
        argv += ["--reason", _plain(body["reason"], "reason")]
    return argv, None


def route_project_set(body: dict):
    return ["project", "set", *_plain_list(body.get("pairs"), "pairs")], None


def route_project_unset(body: dict):
    return ["project", "unset", *_plain_list(body.get("keys"), "keys")], None


def route_global(body: dict):
    if not isinstance(body.get("config"), dict):
        raise RequestError(400, "config: expected the whole user config as an object.")
    return ["setup", "save"], json.dumps(body["config"])


# Route → builder of the `sae` arguments (and stdin). A new write is one entry here, never a
# second implementation: the command validates, locks, logs and refuses exactly as in a terminal.
WRITE_ROUTES = {
    "set": route_set,                       # task settings: sae set <task> key=value …
    "override": route_override,             # per-job override: sae job override …
    "hold": route_hold,                     # a hold after a job: sae hold <task> <job> [--release]
    "project-set": route_project_set,       # project defaults: sae project set …
    "project-unset": route_project_unset,   # sae project unset …
    "global": route_global,                 # the global config: sae setup save < config
}


def run_write(route: str, body: dict) -> tuple[int, dict]:
    # `sae` runs as a subprocess, not the command functions in-process: they rely on the working
    # folder and process state, and `sae` stays the only writer.
    builder = WRITE_ROUTES.get(route)
    if builder is None:
        raise RequestError(404, f"No write route {route!r}.")
    root = repo_by_key(body.get("repo"))
    argv, stdin = builder(body)
    env = {**os.environ, CHANGED_BY_ENV: "viewer"}
    proc = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "sae.py"), *argv, "--json"], cwd=str(root),
                          env=env, input=stdin, capture_output=True, text=True, timeout=WRITE_TIMEOUT_S)
    try:
        result = json.loads(proc.stdout) if proc.stdout.strip() else None
    except ValueError:
        result = {"text": proc.stdout}
    answer = {"ok": proc.returncode == 0, "code": proc.returncode, "result": result,
              "error": proc.stderr.strip() or None, "command": "sae " + " ".join(argv)}
    return (200 if proc.returncode == 0 else 422), answer


# ---------------------------------------------------------------- HTTP

class ViewerHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, token: str):
        super().__init__(address, ViewerHandler)
        self.token = token
        self.version = code_version()
        self.started = iso()
        self.last_request = time.monotonic()

    @property
    def port(self) -> int:
        return self.server_address[1]


class ViewerHandler(http.server.BaseHTTPRequestHandler):
    server: ViewerHTTPServer
    server_version = "sae-viewer"
    sys_version = ""

    def log_message(self, format, *args):  # noqa: A002 - quiet: the log keeps only startup errors
        pass

    # -- helpers
    def send(self, status: int, body: bytes, content_type: str, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, status: int, data) -> None:
        self.send(status, json.dumps(data, ensure_ascii=False, default=str).encode(), "application/json; charset=utf-8")

    def host_ok(self) -> bool:
        """DNS rebinding: only 127.0.0.1:<port> and localhost:<port> are this server."""
        host = (self.headers.get("Host") or "").lower()
        return host in (f"127.0.0.1:{self.server.port}", f"localhost:{self.server.port}")

    def change_allowed(self) -> bool:
        """Every change: the token of this server and an Origin equal to its own origin."""
        token = self.headers.get("X-SAE-Token") or ""
        origin = self.headers.get("Origin") or ""
        own = "http://" + (self.headers.get("Host") or "").lower()
        return hmac.compare_digest(token.encode(), self.server.token.encode()) and origin.lower() == own

    def query(self) -> dict:
        parsed = urllib.parse.urlparse(self.path)
        return {k: v[-1] for k, v in urllib.parse.parse_qs(parsed.query).items()}

    # -- verbs
    def do_GET(self):  # noqa: N802
        self.server.last_request = time.monotonic()
        if not self.host_ok():
            return self.send_json(403, {"error": "Host not allowed."})
        path = urllib.parse.urlparse(self.path).path
        q = self.query()
        try:
            if path in ("/", "/index.html"):
                html = (VIEWER_ASSETS / "index.html").read_text(encoding="utf-8")
                html = html.replace(TOKEN_META, f'<meta name="sae-token" content="{self.server.token}">')
                return self.send(200, html.encode(), "text/html; charset=utf-8", {"Content-Security-Policy": PAGE_CSP})
            if path.lstrip("/") in STATIC_FILES:
                name = path.lstrip("/")
                return self.send(200, (VIEWER_ASSETS / name).read_bytes(), STATIC_TYPES[Path(name).suffix])
            if path == "/api/health":
                return self.send_json(200, {"ok": True, "pid": os.getpid(), "port": self.server.port,
                                            "version": self.server.version, "started": self.server.started})
            if path == "/api/projects":
                return self.send_json(200, versioned(projects_data()))
            if path == "/api/repo":
                return self.send_json(200, versioned(repo_data(q.get("repo"))))
            if path == "/api/task":
                return self.send_json(200, versioned(task_data(q.get("repo"), q.get("task"))))
            if path == "/api/settings":
                return self.send_json(200, versioned(settings_data(q.get("repo"), q.get("task"))))
            if path.startswith(PROTO_PREFIX):
                target = prototype_path(path)
                kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                if kind.startswith("text/") or kind in ("application/json", "image/svg+xml"):
                    kind += "; charset=utf-8"
                return self.send(200, target.read_bytes(), kind, {"Content-Security-Policy": FILE_CSP})
            return self.send_json(404, {"error": "Not found."})
        except RequestError as exc:
            return self.send_json(exc.status, {"error": str(exc)})
        except Exception as exc:  # a broken task folder never stops the server
            return self.send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def do_HEAD(self):  # noqa: N802
        return self.do_GET()

    def do_POST(self):  # noqa: N802
        self.server.last_request = time.monotonic()
        if not self.host_ok():
            return self.send_json(403, {"error": "Host not allowed."})
        if not self.change_allowed():
            return self.send_json(403, {"error": "Changes need this server's token and a same-origin request."})
        path = urllib.parse.urlparse(self.path).path
        if not path.startswith("/api/"):
            return self.send_json(404, {"error": "Not found."})
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.send_json(415, {"error": "Send application/json."})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            return self.send_json(413, {"error": "Body too large or missing length."})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("expected an object")
            status, answer = run_write(path[len("/api/"):], body)
            return self.send_json(status, answer)
        except RequestError as exc:
            return self.send_json(exc.status, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            return self.send_json(400, {"ok": False, "error": f"Invalid JSON: {exc}"})
        except subprocess.TimeoutExpired:
            return self.send_json(504, {"ok": False, "error": "sae did not finish in time."})

    def do_OPTIONS(self):  # noqa: N802 - never a permissive CORS answer
        return self.send_json(405, {"error": "Not allowed."})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS


# ---------------------------------------------------------------- process

def bind(port: int, token: str) -> ViewerHTTPServer:
    """On the last port when it is free, else on a port the OS picks."""
    if port:
        try:
            return ViewerHTTPServer(("127.0.0.1", port), token)
        except OSError as exc:
            if isinstance(exc, PermissionError):
                raise
    return ViewerHTTPServer(("127.0.0.1", 0), token)


def serve() -> int:
    """Runs the server in this process until the idle limit or SIGTERM; removes viewer.pid."""
    last = read_state("viewer.json") or {}
    token = last.get("token") if isinstance(last.get("token"), str) and len(last["token"]) >= 32 else \
        secrets.token_urlsafe(32)
    try:
        server = bind(last.get("port") if isinstance(last.get("port"), int) else 0, token)
    except PermissionError as exc:
        print(f"Viewer cannot listen on 127.0.0.1: {exc}", file=sys.stderr)
        return 1
    try:  # from here on, any failure still closes the socket and removes viewer.pid
        write_private(state_path("viewer.json"), {"port": server.port, "token": token})
        write_private(state_path("viewer.pid"), {"pid": os.getpid(), "port": server.port, "version": server.version,
                                                 "started": server.started})
        idle = idle_limit()

        def watch_idle():
            while True:
                time.sleep(min(30.0, max(0.1, idle / 4)))
                if time.monotonic() - server.last_request > idle:
                    server.shutdown()
                    return

        threading.Thread(target=watch_idle, daemon=True).start()
        signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        with contextlib.suppress(OSError, ValueError):
            if (read_state("viewer.pid") or {}).get("pid") == os.getpid():
                state_path("viewer.pid").unlink()
    return 0
