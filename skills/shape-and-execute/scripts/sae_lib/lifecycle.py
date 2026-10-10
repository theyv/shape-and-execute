"""Commands new, start, finish and abandon; backlog pickup, task record and final report."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
from pathlib import Path

from .common import (
    EXIT_GATE,
    EXIT_GIT,
    EXIT_OK,
    EXIT_USAGE,
    HARNESSES,
    SCHEMA_VERSION,
    SaeError,
    WRITER_KINDS,
    emit,
    fail,
    file_stamp,
    iso,
    read_text,
    rel,
    slugify,
    table,
    write_atomic,
    write_json,
)
from .config import cfg, load_config, new_task_settings, require_harness, settings_card
from .gitutil import find_root, git, git_ok, git_user, run
from .graph import fix_target, parallel_possible
from .markdown import split_frontmatter
from .progress import next_text
from .reviews import check_finish_gates, finish_merges, merge_job
from .routing import resolve_model
from .tasks import (
    Task,
    append_event_to,
    ensure_tasks_folder,
    open_task,
    parked_reason,
    resolve_task,
    result_file,
    tasks_dir,
    template,
)
from .viewer import render_viewer_safely, stamped_items, viewer_link
from .workspaces import (
    TASK_WORKTREE_NAME,
    job_branch,
    remove_task_worktrees,
    require_on_task_branch,
    setup_worktree,
    task_worktree_path,
    uncommitted_outside_tasks,
)


def cmd_new(args) -> int:
    root, is_git = find_root()
    title = args.title.strip()
    if not title:
        fail(EXIT_USAGE, "The title is empty.")
    slug = slugify(args.slug or title)
    if args.backlog:
        return new_backlog_item(args, root, title, slug)
    settings = new_task_settings(load_config())
    harness = require_harness(args.harness)
    from_item = None
    intent = template("intent.md").replace("<title>", title)
    if args.from_file:
        item = Path(args.from_file)
        item = item if item.is_absolute() else (Path.cwd() / item)
        text = read_text(item)
        if text is None:
            fail(EXIT_USAGE, f"No backlog item at {item}.")
        meta, body = split_frontmatter(text)
        intent = body.lstrip("\n")
        from_item = {"file": rel(item, root), "source": meta.get("source")}
    task_id = f"{file_stamp()}--{slug}"
    folder = tasks_dir(root) / task_id
    if folder.exists():
        fail(EXIT_USAGE, f"Task {task_id} exists. Choose another --slug.")
    ensure_tasks_folder(root)
    folder.mkdir()
    author = git_user(root)
    write_atomic(folder / "intent.md", intent)
    write_json(folder / "settings.json", settings)
    state = {"schema": SCHEMA_VERSION, "task": {
        "id": task_id, "title": title, "created": iso(), "author": author, "phase": "shaping", "git": is_git,
        "layout": None, "orchestrator_harness": harness, "branch": None, "base": None, "home": str(root),
        "approvals": {},
        "settings_seen": settings, "last_change": iso()}, "jobs": {}}
    write_json(folder / "state.json", state)
    event = {"at": iso(), "type": "task.created", "title": title, "author": author}
    if from_item:
        event["from"] = from_item
    write_atomic(folder / "events.jsonl", json.dumps(event, ensure_ascii=False) + "\n")
    render_viewer_safely(root, [task_id])
    url, viewer_line = viewer_link(root, task_id)  # [VIEWER-LINK-AT-NEW]; never fails the command
    text = (f"Task: {task_id}\nFolder: {folder}\nIntent: {folder / 'intent.md'}\n"
            f"Settings: {settings_card(settings)}")
    if from_item:
        text += f"\nPicked up from the backlog: {from_item['file']} (it stays; sae start removes it on the task branch)."
    text += f"\n{viewer_line}"
    emit(args, text, {"task": task_id, "folder": str(folder), "intent": str(folder / "intent.md"),
                      "settings": settings, "from": from_item, "viewer": url, "viewer_hint": viewer_line})
    return EXIT_OK


def new_backlog_item(args, root: Path, title: str, slug: str) -> int:
    source = resolve_task(root, args.source) if args.source else None
    ensure_tasks_folder(root)
    path = tasks_dir(root) / "backlog" / f"{file_stamp()}--{slug}.md"
    if path.exists():
        fail(EXIT_USAGE, f"{path} exists. Choose another --slug.")
    body = template("intent.md").replace("<title>", title)
    front = f"---\nsource: {source}   # the task during which the owner deferred the work\n---\n\n" if source else ""
    write_atomic(path, front + body)
    if source:
        append_event_to(root, source, "backlog.created", file=rel(path, root))
    else:
        render_viewer_safely(root, [])
    emit(args, f"Backlog item: {path}", {"file": str(path), "source": source})
    return EXIT_OK


def cmd_start(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        if task.phase not in ("planning", "executing"):
            fail(EXIT_USAGE, f"The task is in {task.phase}.")
        if "plan" not in task.info["approvals"]:
            fail(EXIT_GATE, f"The plan is not approved. Run: sae approve {task.id} plan")
        if args.harness:
            task.info["orchestrator_harness"] = args.harness
        elif not task.info.get("orchestrator_harness"):
            task.info["orchestrator_harness"] = require_harness(None)
        resumed = task.phase == "executing"
        undo: list = []
        picked_up = None
        try:
            if resumed:
                lines = [where_it_runs(task)]
            else:
                check_models(task, config)
                is_git = git_ok(task.root, "rev-parse", "--git-dir")
                task.info["git"] = is_git
                task.info.setdefault("home", str(task.root))
                if not task.info.get("layout"):
                    writers = [i for i, j in task.jobs.items() if j["kind"] in WRITER_KINDS]
                    chained = all(not parallel_possible(task.jobs, a, b)
                                  for x, a in enumerate(writers) for b in writers[x + 1:])
                    task.info["layout"] = "chain" if chained or not is_git else "worktrees"
                if task.uses_worktrees:
                    cfg(config, "parallel.max_writers")
                if is_git:
                    lines, picked_up = start_task_worktree(task, config, undo)
                else:
                    lines = ["No git: no branches, worktrees or commits. Agents change files directly; nothing "
                             "can undo their changes. Copy the folder first if you want a way back."]
                task.info["phase"] = "executing"
            task.event("execution.started", branch=task.info.get("branch"), base=task.info.get("base"),
                       layout=task.info["layout"], worktree=task.info.get("worktree"), resumed=resumed)
            lines.insert(0, f"Executing {task.id} · branch: {task.info.get('branch') or '-'} · "
                            f"layout: {task.info['layout']}")
            lines += ["", next_text(task, config)]
            task.save()  # inside the rollback: the start counts once its state is on disk
        except BaseException:
            for step in reversed(undo):
                with contextlib.suppress(Exception):
                    step()
            raise
        if picked_up:
            with contextlib.suppress(FileNotFoundError):
                os.remove(task.root / picked_up)
            lines.insert(-2, f"Removed the uncommitted backlog item {picked_up}.")
        emit(args, "\n".join(lines), {"task": task.id, "branch": task.info.get("branch"),
                                      "layout": task.info["layout"], "base": task.info.get("base"),
                                      "worktree": task.info.get("worktree"), "home": task.info.get("home")})
    return EXIT_OK


def check_models(task: Task, config: dict | None) -> None:
    """Resolves the model of every pending job before `sae start` changes anything: a config
    that cannot route the task fails here, not after the task worktree exists."""
    for job_id, job in task.jobs.items():
        if job["status"] == "pending":
            if config is None:
                cfg(config, "routing")
            resolve_model(task, job_id, config, exact=False)


def where_it_runs(task: Task) -> str:
    if task.worktree:
        return f"Task worktree: {task.worktree}"
    if task.info.get("git"):
        return f"Executes in place in {task.root} (started by an older sae)."
    return f"Executes in {task.root} (no git)."


def start_task_worktree(task: Task, config: dict | None, undo: list) -> tuple[list[str], str | None]:
    """`sae start` with git ([TASK-WORKTREE], [BACKLOG-PICKUP], 07-cli-spec §8): task branch and
    task worktree from the home checkout's HEAD, backlog pickup commit, task folder moved into
    the worktree, setup. Appends an undo step for every change to `undo`; the caller runs them
    on any failure until the task state is saved, so the task stays in planning. Returns the
    report lines and the untracked backlog item to delete once the state is saved. The home
    checkout never changes branch."""
    home = task.root
    if not git_ok(home, "rev-parse", "--verify", "--quiet", "HEAD"):
        fail(EXIT_GIT, "The repository has no commits. Make a first commit, then run sae start again.")
    worktree = task_worktree_path(task, config)
    branch = f"task/{task.id}"
    if git_ok(home, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        fail(EXIT_GIT, f"Branch {branch} exists already. Delete it (git branch -D {branch}) or start "
                       "a new task.")
    if worktree.exists():
        fail(EXIT_GIT, f"{worktree} exists already. Remove it, then run sae start again.")
    task_rel = rel(task.dir, home)
    if git_ok(home, "cat-file", "-e", f"HEAD:{task_rel}"):
        fail(EXIT_USAGE, f"{task_rel} is committed on the current branch. sae moves an uncommitted task "
                         "folder into the task worktree; commit nothing of a task before its finish.")
    lines = []
    dirty = uncommitted_outside_tasks(home)
    current = git(home, "branch", "--show-current", check=False)
    commit = git(home, "rev-parse", "HEAD")
    for folder in (worktree.parent.parent, worktree.parent):
        if not folder.exists():
            folder.mkdir(parents=True)
            undo.append(lambda f=folder: f.rmdir())
    git(home, "worktree", "add", "--quiet", "-b", branch, str(worktree), commit)
    undo.append(lambda: (run(["git", "worktree", "remove", "--force", str(worktree)], home),
                         run(["git", "worktree", "prune"], home),
                         run(["git", "branch", "-D", branch], home)))
    lines += commit_backlog_pickup(task, worktree)
    untracked_item = pickup_item_untracked(task, home)
    saved = {name: (task.dir / name).read_bytes() for name in ("state.json", "events.jsonl")
             if (task.dir / name).is_file()}
    home_dir = task.dir

    def restore_state() -> None:
        """Runs after the folder has moved back: the state and events as they were before."""
        for name, data in saved.items():
            (home_dir / name).unlink(missing_ok=True)
            (home_dir / name).write_bytes(data)
    undo.append(restore_state)
    moves = [task.dir] + source_items(task, home) + ([home / untracked_item] if untracked_item else [])
    for source in moves:
        dest = worktree / source.relative_to(home)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(dest))
        undo.append(lambda s=source, d=dest: shutil.move(str(d), str(s)))
    task.move_to(worktree)
    undo.append(lambda: task.move_to(home))
    copy_untracked_repo_files(home, worktree)
    try:
        lines += setup_worktree(worktree, worktree, task.id, TASK_WORKTREE_NAME,
                                task.dir / "jobs" / f"{TASK_WORKTREE_NAME}.setup.log")
    except SaeError as exc:
        first = str(exc).splitlines()[0].split(". Log:")[0]
        raise SaeError(exc.code, f"Task worktree setup: {first}. sae start was undone; the task stays "
                                 f"in planning. Log: {home / task_rel / 'jobs' / 'task.setup.log'}") from exc
    task.info.update({"branch": branch, "worktree": str(worktree),
                      "base": {"branch": current or None, "commit": commit[:7]}})
    lines.append(f"Task worktree: {worktree}")
    lines.append(f"Home checkout {home} stays on {current or 'its detached HEAD'}.")
    if dirty:
        lines.append("Not part of the task (uncommitted in the home checkout): " + ", ".join(dirty[:10])
                     + (" …" if len(dirty) > 10 else ""))
    return lines, untracked_item


def pickup_item(task: Task) -> str | None:
    created = next((e for e in task.events() if e["type"] == "task.created"), {})
    return (created.get("from") or {}).get("file")


def commit_backlog_pickup(task: Task, worktree: Path) -> list[str]:
    """Removes the backlog item the task came from on the task branch: its first commit."""
    item = pickup_item(task)
    if not item or not git_ok(worktree, "cat-file", "-e", f"HEAD:{item}"):
        return []
    git(worktree, "rm", "--quiet", "--", item)
    git(worktree, "commit", "--quiet", "-m", f"{task.id}: picked up from backlog", "-m", f"Task: {task.id}")
    return [f"Committed the removal of {item} on the task branch."]


def pickup_item_untracked(task: Task, home: Path) -> str | None:
    """The backlog item the task came from when it was never committed: it moves with the task."""
    item = pickup_item(task)
    if not item or not (home / item).is_file() or git_ok(home, "ls-files", "--error-unmatch", "--", item):
        return None
    return item


def source_items(task: Task, home: Path) -> list[Path]:
    """Untracked findings, backlog items and decision drafts whose source is this task."""
    listing = git(home, "ls-files", "--others", "--", ".tasks/findings", ".tasks/backlog", ".tasks/adr",
                  check=False)
    found = []
    for line in listing.splitlines():
        path = home / line
        if path.suffix == ".md" and path.is_file():
            source = str(split_frontmatter(read_text(path, ""))[0].get("source") or "")
            if source == task.id or source.startswith(task.id + "/"):
                found.append(path)
    return found


def copy_untracked_repo_files(home: Path, worktree: Path) -> None:
    """Copies the untracked `.tasks/repo/` files, the `.tasks/` git files and a root
    `.worktreeinclude` into the task worktree ([SETUP-SOURCE]): its setup and its job worktrees
    read them there. The home checkout keeps them for the next task."""
    listing = git(home, "ls-files", "--others", "--", ".tasks/repo", ".tasks/.gitignore",
                  ".tasks/.gitattributes", ".worktreeinclude", check=False)
    for line in listing.splitlines():
        dest = worktree / line
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(home / line, dest)
    ensure_tasks_folder(worktree)


def final_report(task: Task, with_open: bool) -> str:
    jobs = task.jobs
    events = task.events()
    lines = [f"# Final report: {task.info['title']}", f"Task: {task.id}"]
    finals = [i for i, j in jobs.items() if j["final"]]
    if finals:
        job = jobs[finals[0]]
        lines += ["", "## Outcome", f"Final validation {finals[0]}: {job['status']} — {job.get('summary', '')}",
                  f"Details per requirement: {result_file(task, finals[0])}"]
    rows = [["job", "kind", "status", "attempts", "models", "tokens"]]
    for job_id, job in jobs.items():
        models = ", ".join(dict.fromkeys(a["model"] for a in job["attempts"])) or "-"
        tokens = sum(a.get("tokens") or 0 for a in job["attempts"])
        rows.append([job_id, job["kind"], job["status"] + (" ✓merged" if job["merged"] else ""),
                     str(len(job["attempts"])), models, str(tokens) if tokens else "-"])
    lines += ["", "## Jobs", table(rows, "")]
    reviews = [e for e in events if e["type"] == "review.completed"]
    if reviews:
        lines += ["", "## Reviews"] + [f"- {e['job']} → {e['target']}"
                                       + (f", round {e['round']}" if (e.get("round") or 1) > 1 else "")
                                       + f": {e['verdict']} ({e.get('provider')}, {e.get('model')})" for e in reviews]
    overridden = [e for e in events if e["type"] == "gate.overridden"]
    if overridden:
        lines += ["", "## Overridden gates"] + [f"- {e['gate']} gate: {', '.join(e.get('jobs') or []) or '-'}. "
                                                f"Reason: {e.get('reason')}" for e in overridden]
    agent = [e for e in events if e["type"] in ("decision", "amendment") and e.get("by") == "agent"]
    lines += ["", "## To check before you merge"]
    lines += [f"- {e['type']}{' ' + e['id'] if e.get('id') else ''}: {e.get('summary')}"
              + (f" ({e['class']})" if e.get("class") else "") for e in agent] or ["- No agent decisions or amendments."]
    if with_open:
        open_items = [(i, j) for i, j in jobs.items() if j["status"] in ("pending", "parked", "failed")]
        if open_items:
            lines += ["", "## Open items"] + [f"- {i}: {j['status']} — {j.get('summary') or parked_reason(task, i)}"
                                              for i, j in open_items]
    created = [e.get("finding") or e.get("file") for e in events if e["type"] in ("finding.created", "backlog.created")]
    if created:
        lines += ["", "## Findings and backlog items from this task"] + [f"- {c}" for c in created]
    lines += ["", "## Branch"]
    if task.info.get("git"):
        base = task.info.get("base") or {}
        count = git(task.root, "rev-list", "--count", f"{base.get('commit')}..{task.info['branch']}", check=False)
        lines.append(f"{task.info['branch']} (base {base.get('branch') or '-'} @ {base.get('commit')}), "
                     f"{count or '?'} commits.")
        lines.append("Nothing was pushed. Merge or open a merge request yourself.")
    else:
        lines.append("No git: the changes are in the working folder.")
    return "\n".join(lines)


def cmd_finish(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        if task.phase != "executing":
            fail(EXIT_USAGE, f"The task is in {task.phase}; finish needs executing.")
        if args.override is not None and not args.override.strip():
            fail(EXIT_USAGE, f"--override needs the owner's reason: sae finish {task.id} --override \"<reason>\"")
        # 1. Gates, before anything merges: they judge the code that will be closed.
        overridden = check_finish_gates(task, args.with_open, args.override)
        out: list[str] = []
        # 2. Merge what the gates allowed (with --override also writers the checks do not cover).
        if task.info.get("git"):
            require_on_task_branch(task)
            for job_id in finish_merges(task):
                code = merge_job(task, job_id, config, out)
                if code != EXIT_OK:
                    emit(args, "\n".join(out), {"exit": code, "messages": out})
                    return code
        for gate in overridden:
            task.event("gate.overridden", gate=gate["gate"], jobs=gate["jobs"], reason=args.override)
            out.append(f"Gate overridden: {gate['gate']} ({', '.join(gate['jobs'])}).")
        # 3. Close: worktrees, branches, phase, task record, report.
        if task.info.get("git"):
            kept = remove_task_worktrees(task, config)
            for job_id, job in task.jobs.items():
                if job["merged"] and not fix_target(task, job_id):
                    run(["git", "branch", "-d", job_branch(task, job_id)], task.root)
            if kept:
                out.append("Worktrees kept (uncommitted changes): " + ", ".join(kept))
        report = final_report(task, args.with_open)
        head = git(task.root, "rev-parse", "--short", "HEAD") if task.info.get("git") else None
        task.info["phase"] = "done"
        task.event("task.finished", branch=task.info.get("branch"), commit=head)
        task.save()
        if task.info.get("git"):
            commit_task_record(task, out)
        emit(args, "\n".join(out + ["", report]).strip(), {"report": report, "messages": out,
                                                            "overridden": overridden})
    render_viewer_safely(root, [task.id])
    return EXIT_OK


def commit_task_record(task: Task, out: list[str]) -> None:
    root = task.root
    paths = [f".tasks/{task.id}"]
    for folder in ("findings", "backlog"):
        for path in stamped_items(tasks_dir(root) / folder):
            source = str(split_frontmatter(read_text(path, ""))[0].get("source") or "")
            if source == task.id or source.startswith(task.id + "/"):
                paths.append(rel(path, root))
    for extra in (".tasks/repo", ".tasks/.gitignore", ".tasks/.gitattributes"):
        if (root / extra).exists():
            paths.append(extra)
    git(root, "add", "--", *paths)
    staged = git(root, "diff", "--cached", "--name-only", "--", *paths)
    if not staged:
        return
    git(root, "commit", "--quiet", "-m", f"{task.id}: task record", "-m", f"Task: {task.id}", "--", *paths)
    out.append(f"Committed the task record on {task.info['branch']}.")


def cmd_abandon(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        kept = remove_task_worktrees(task, config)
        task.info["phase"] = "abandoned"
        task.event("task.abandoned", reason=args.reason)
        text = f"Abandoned {task.id}. Branches are kept."
        if kept:
            text += "\nWorktrees kept (uncommitted changes): " + ", ".join(kept)
        emit(args, text, {"task": task.id, "kept_worktrees": kept})
    return EXIT_OK


def register_new(sub, command):
    """Add the `new` command to the parser."""
    p = command(sub, "new", "Create a task, or a backlog item with --backlog.",
                "Creates .tasks/<id>/ with intent.md, settings.json (from the config defaults), state.json\n"
                "(phase shaping) and events.jsonl. Prints the task ID and paths.\n"
                "--from <file>: the backlog item becomes intent.md; the file stays until sae start removes it.\n"
                "--backlog: creates .tasks/backlog/<stamp>--<slug>.md for work the user deferred; no task, no config.",
                ['new "Claims status self-service"', 'new "Billing export" --from .tasks/backlog/2026-10-06-1520--billing.md',
                 'new "Billing export" --backlog --source claims-status'], [0, 1, 2], cmd_new)
    p.add_argument("title")
    p.add_argument("--slug", help="folder slug; default: from the title")
    p.add_argument("--harness", choices=HARNESSES, help="orchestrator harness; default: detected")
    p.add_argument("--from", dest="from_file", metavar="FILE", help="backlog item to turn into this task")
    p.add_argument("--backlog", action="store_true", help="create a backlog item instead of a task")
    p.add_argument("--source", metavar="TASK", help="with --backlog: the task during which the user deferred the work")


def register_start(sub, command):
    """Add the `start` command to the parser."""
    p = command(sub, "start", "Begin execution in a task worktree, then the first next.",
                "Needs the plan approval. With git: creates task/<id> from the home checkout's HEAD and the task\n"
                "worktree in the worktree cache, commits the removal of a picked-up backlog item there, moves the\n"
                "task folder into it and runs the worktree setup. The home checkout keeps its branch; its\n"
                "uncommitted changes only give a warning. Atomic: a failure undoes every step. Prints the task\n"
                "worktree path. On an executing task: the resume path (records --harness, prints next).\n"
                "Without git: prints the notice.",
                ["start claims-status", "start claims-status --harness codex"], [0, 1, 2, 3, 4], cmd_start)
    p.add_argument("task")
    p.add_argument("--harness", choices=HARNESSES, help="the orchestrator's harness, when it changes")


def register_finish(sub, command):
    """Add the `finish` command to the parser."""
    p = command(sub, "finish", "Merge the rest, remove worktrees, commit the task record, print the final report.",
                "Gates, checked before anything merges: nothing running; nothing pending or parked unless --with-open;\n"
                "no last review round (integration, or a job review of an unmerged job) says changes-required;\n"
                "no stale checks (a round or final validation after a late merge has not run, or a done writer\n"
                "that the checks would not cover is still unmerged); the final validation and the integration\n"
                "review done. --override passes the verdict and stale-check gates with the owner's reason; it is\n"
                "logged and listed in the final report. Never pushes.",
                ["finish claims-status", "finish claims-status --with-open",
                 'finish claims-status --override "owner accepts the remaining finding"'],
                [0, 1, 3, 4], cmd_finish)
    p.add_argument("task")
    p.add_argument("--with-open", action="store_true", help="the user accepts open jobs; they are listed in the report")
    p.add_argument("--override", metavar="REASON",
                   help="the owner's reason to close despite changes-required or stale checks")


def register_abandon(sub, command):
    """Add the `abandon` command to the parser."""
    p = command(sub, "abandon", "Stop a task: phase abandoned, worktrees removed, branches kept.", "",
                ['abandon claims-status --reason "superseded by billing work"'], [0, 1], cmd_abandon)
    p.add_argument("task")
    p.add_argument("--reason", required=True)
