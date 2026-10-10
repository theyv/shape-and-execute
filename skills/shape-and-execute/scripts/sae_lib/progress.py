"""Commands status, next and dispatch."""

from __future__ import annotations

import contextlib
import json
import re

from .common import (
    EXIT_OK,
    EXIT_USAGE,
    HARD_STOPS_LINE,
    HARNESSES,
    STALE_RUNNING_MINUTES,
    WRITER_KINDS,
    age_text,
    emit,
    fail,
    iso,
    minutes_since,
    mode_line,
    read_json,
    read_text,
    rel,
    sae_prefix,
    stamp_time,
    table,
)
from .config import cfg, load_config, settings_card
from .gitutil import find_root, git
from .graph import is_ready, kind_allowed_now, waits_for, writer_blocked
from .markdown import first_heading, has_content, md_section, split_frontmatter
from .prompts import build_prompt, external_review_command
from .reviews import materialize_integration_review
from .routing import model_text, resolve_model, routing_text, short_text
from .tasks import (
    Task,
    job_file,
    job_summary,
    last_model,
    list_task_ids,
    open_task,
    parked_reason,
    result_file,
    tasks_dir,
)
from .viewer import stamped_items
from .workspaces import prepare_workspace, workspace_of


def next_command(task: Task) -> str:
    phase, jobs = task.phase, task.jobs
    ready = [i for i in jobs if is_ready(task, i)]
    if phase == "shaping":
        if ready:
            return f"sae dispatch {task.id} {ready[0]}"
        if any(j["status"] == "running" for j in jobs.values()):
            return f"sae collect {task.id} <ID> when the subagent returns"
        return f"sae check {task.id}, then sae approve {task.id} spec"
    if phase == "planning":
        if ready:
            return f"sae dispatch {task.id} {ready[0]}"
        if any(j["status"] == "running" for j in jobs.values()):
            return f"sae collect {task.id} <ID> when the subagent returns"
        if "plan" in task.info["approvals"]:
            return f"sae start {task.id}"
        return f"sae check {task.id}, then sae approve {task.id} plan"
    if phase == "executing":
        return f"sae next {task.id}"
    return "none"


def task_status_data(task: Task) -> dict:
    rows, parked, ready, warnings = [], [], [], []
    for job_id, job in task.jobs.items():
        rows.append({"id": job_id, "kind": job["kind"], "status": job["status"], "merged": job["merged"],
                     "last_change": job["last_change"], "model": last_model(job),
                     "attempts": len(job["attempts"]), "needs": job["needs"], "difficulty": job["difficulty"]})
        if job["status"] == "parked":
            parked.append({"id": job_id, "reason": parked_reason(task, job_id)})
        if is_ready(task, job_id):
            ready.append(job_id)
        if job["status"] == "running" and minutes_since(job["last_change"]) >= STALE_RUNNING_MINUTES:
            if not result_file(task, job_id).exists():
                warnings.append(f"{job_id}: running with no change for {age_text(job['last_change'])[:-4]} — check on it")
            else:
                warnings.append(f"{job_id}: a result file exists — collect it")
    return {"task": task.id, "title": task.info["title"], "phase": task.phase, "branch": task.info.get("branch"),
            "layout": task.info.get("layout"), "last_change": task.info.get("last_change"),
            "settings": task.settings,
            "settings_card": settings_card(task.settings, task.info.get("orchestrator_harness")),
            "approvals": task.info.get("approvals", {}), "jobs": rows, "parked": parked, "ready": ready,
            "warnings": warnings, "next": next_command(task)}


def cmd_status(args) -> int:
    root, _ = find_root()
    if args.task:
        with open_task(root, args.task) as task:
            data = task_status_data(task)
        lines = [f"{data['title']}", f"{data['task']} · phase: {data['phase']}"
                 + (f" · branch: {data['branch']}" if data["branch"] else "")
                 + (f" · layout: {data['layout']}" if data["layout"] else ""),
                 f"Settings: {data['settings_card']}", f"Last change: {age_text(data['last_change'])}"]
        approvals = ", ".join(f"{k} by {v['by']}" for k, v in data["approvals"].items())
        if approvals:
            lines.append(f"Approved: {approvals}")
        if data["jobs"]:
            rows = [["ID", "kind", "status", "last change", "model"]]
            for r in data["jobs"]:
                status = r["status"] + (" ✓merged" if r["merged"] else "")
                rows.append([r["id"], r["kind"], status, age_text(r["last_change"]), r["model"]])
            lines += ["", "Jobs:", table(rows)]
        if data["parked"]:
            lines += ["", "Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
        if data["ready"]:
            lines += ["", "Ready: " + ", ".join(data["ready"])]
        if data["warnings"]:
            lines += ["", "Warnings:"] + [f"  - {w}" for w in data["warnings"]]
        lines += ["", f"Next: {data['next']}"]
        emit(args, "\n".join(lines), data)
        return EXIT_OK
    tasks = []
    for task_id in reversed(list_task_ids(root)):
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            state = read_json(tasks_dir(root) / task_id / "state.json")
            statuses = [j["status"] for j in state["jobs"].values()]
            tasks.append({"id": task_id, "title": state["task"]["title"], "phase": state["task"]["phase"],
                          "last_change": state["task"].get("last_change"), "running": statuses.count("running"),
                          "parked": statuses.count("parked")})
    backlog = []
    for path in stamped_items(tasks_dir(root) / "backlog"):
        meta, body = split_frontmatter(read_text(path, ""))
        backlog.append({"file": rel(path, root), "title": re.sub(r"^Intent:\s*", "", first_heading(body) or path.stem),
                        "source": meta.get("source"), "created": stamp_time(path.name)})
    findings = len(stamped_items(tasks_dir(root) / "findings"))
    lines = []
    if tasks:
        rows = [["task", "phase", "title", "last change", "running", "parked"]]
        rows += [[t["id"], t["phase"], t["title"], age_text(t["last_change"]), str(t["running"]), str(t["parked"])]
                 for t in tasks]
        lines += ["Tasks:", table(rows)]
    else:
        lines.append("No tasks.")
    if backlog:
        rows = [[b["file"], b["title"], age_text(b["created"]), f"from {b['source']}" if b["source"] else ""]
                for b in backlog]
        lines += ["", "Backlog:", table(rows)]
    lines += ["", f"Open findings: {findings}"]
    emit(args, "\n".join(lines), {"tasks": tasks, "backlog": backlog, "open_findings": findings})
    return EXIT_OK


def next_text(task: Task, config: dict | None) -> str:
    data = next_data(task, config)
    lines = [mode_line(task.settings["interaction"]), HARD_STOPS_LINE, ""]
    if data["running"]:
        lines += ["Running:"] + [f"  {r['id']} — last change {age_text(r['last_change'])}" for r in data["running"]]
    if data["parked"]:
        lines += ["Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
    if data["ready"]:
        rows = [[r["id"], r["kind"], r["difficulty"], r["model"], r["workspace"], r.get("blocked") or ""]
                for r in data["ready"]]
        lines += ["Ready (dispatch each: sae dispatch <task> <ID>):", table(rows)]
    if data["blocked"]:
        lines += ["Blocked:"] + [f"  {b['id']} — waits for {', '.join(b['waits_for'])}" for b in data["blocked"]]
    if data["failed"]:
        lines += ["Failed:"] + [f"  {f['id']} — {f['summary']}" for f in data["failed"]]
    if data["all_done"]:
        lines.append(f"All jobs done. Run: sae finish {task.id}")
    elif not (data["running"] or data["ready"] or data["parked"]):
        lines.append("Nothing can run. Adapt the graph, resume a failed job, or finish with --with-open.")
    return "\n".join(lines).rstrip()


def next_data(task: Task, config: dict | None) -> dict:
    running, parked, ready, blocked, failed = [], [], [], [], []
    for job_id, job in task.jobs.items():
        status = job["status"]
        if status == "running":
            running.append({"id": job_id, "last_change": job["last_change"]})
        elif status == "parked":
            parked.append({"id": job_id, "reason": parked_reason(task, job_id)})
        elif status == "failed":
            failed.append({"id": job_id, "summary": job_summary(task, job_id)})
        elif status == "pending":
            reasons = waits_for(task, job_id)
            if reasons:
                blocked.append({"id": job_id, "waits_for": reasons})
                continue
            if config is None:
                cfg(config, "routing")
            model = resolve_model(task, job_id, config, exact=False)
            workdir, _ = workspace_of(task, job_id, config)
            entry = {"id": job_id, "kind": job["kind"], "difficulty": model["difficulty"],
                     "model": short_text(model), "routing": model,
                     "workspace": "worktree" if workdir != task.root else
                                  ("repo root, writes" if job["kind"] in WRITER_KINDS else "repo root, read-only")}
            if job["kind"] in WRITER_KINDS:
                entry["blocked"] = writer_blocked(task, job_id, config)
            ready.append(entry)
    open_statuses = {j["status"] for j in task.jobs.values()} & {"running", "pending", "parked"}
    return {"running": running, "parked": parked, "ready": ready, "blocked": blocked, "failed": failed,
            "all_done": not open_statuses and task.phase == "executing"}


def cmd_next(args) -> int:
    root, _ = find_root()
    config = load_config()
    with open_task(root, args.task) as task:
        if task.phase != "executing":
            fail(EXIT_USAGE, f"The task is in {task.phase}. Next: {next_command(task)}")
        out: list[str] = []
        materialize_integration_review(task, out)
        text = ("\n".join(out) + "\n" if out else "") + next_text(task, config)
        data = next_data(task, config)
        data["reminder"] = [mode_line(task.settings["interaction"]), HARD_STOPS_LINE]
        emit(args, text, data)
    return EXIT_OK


def cmd_dispatch(args) -> int:
    root, _ = find_root()
    config = load_config()
    with open_task(root, args.task) as task:
        job_id = args.id
        job = task.job(job_id)
        if args.resume:
            if not (args.reason or "").strip():
                fail(EXIT_USAGE, "--resume needs --reason.")
            if job["status"] not in ("running", "parked", "failed"):
                fail(EXIT_USAGE, f"{job_id} is {job['status']}; --resume is for running, parked or failed jobs.")
            if not kind_allowed_now(task, job):
                fail(EXIT_USAGE, f"{job['kind']} jobs do not run in phase {task.phase}.")
        else:
            if job["status"] != "pending":
                fail(EXIT_USAGE, f"{job_id} is {job['status']}. To run it again: --resume --reason \"<why>\".")
            reasons = waits_for(task, job_id)
            if reasons:
                fail(EXIT_USAGE, f"{job_id} is not ready: waits for {', '.join(reasons)}.")
        if job["kind"] in WRITER_KINDS and job["status"] != "running":
            blocked = writer_blocked(task, job_id, config)
            if blocked:
                fail(EXIT_USAGE, f"{job_id} must wait: {blocked}.")
        model = resolve_model(task, job_id, config, harness=args.harness, provider=args.provider)
        workdir, branch = prepare_workspace(task, job_id, config)
        head = git(workdir, "rev-parse", "HEAD") if (task.info.get("git") and job["kind"] in WRITER_KINDS) else None
        attempt = {"n": len(job["attempts"]) + 1, "harness": model["harness"], "model": model["model"],
                   "model_entry": model["model_entry"], "effort": model["effort"], "source": model["source"],
                   "tier": model["tier"], "started": iso(), "ended": None,
                   "tokens": None, "duration_s": None, "agent_ref": None, "reason": args.reason, "head": head}
        job["attempts"].append(attempt)
        job["status"] = "running"
        task.touch(job)
        task.event("job.dispatched", job=job_id, attempt=attempt["n"], harness=model["harness"],
                   model=model["model"], effort=model["effort"], source=model["source"], tier=model["tier"],
                   workspace=rel(workdir, root) or ".",
                   reason=args.reason)
        external = job["kind"] == "review" and model["harness"] != task.info.get("orchestrator_harness")
        prompt = build_prompt(task, job_id, workdir, branch, model, config, external=external)
        if args.resume:
            extra = []
            log = task.dir / "jobs" / f"{job_id}.verify.log"
            if args.reason.startswith("verify") and log.exists():
                extra.append(f"Read first: {log}")
            follow = md_section(read_text(job_file(task, job_id), "") or "", "Follow-up questions")
            if has_content(follow):
                extra.append(f"Read first: the \"Follow-up questions\" section of {job_file(task, job_id)}")
            prompt = "\n".join([f"RESUME {job_id} — reason: {args.reason}", *extra,
                                "Continue from your earlier work and commits; the pointers are unchanged.", "",
                                prompt])
        header = (f"HARNESS: {model['harness']} · MODEL: {model_text(model)} · EFFORT: {model['effort']}\n"
                  f"ROUTING: {routing_text(model)}")
        data = {"job": job_id, "attempt": attempt["n"], "workspace": str(workdir), "branch": branch, **model}
        if external:
            command = external_review_command(task, job_id, model, prompt)
            fallback = (f"{sae_prefix()} dispatch {task.id} {job_id} --provider {task.info['orchestrator_harness']} "
                        f"--resume --reason \"provider failed: <exit code or empty result>\"")
            data.update({"command": command, "if_it_fails": fallback})
            emit(args, f"{header}\nCOMMAND:\n{command}\nIF IT FAILS:\n{fallback}", data)
        else:
            data["prompt"] = prompt
            emit(args, f"{header}\nPROMPT:\n{prompt}", data)
    return EXIT_OK


def register_status(sub, command):
    """Add the `status` command to the parser."""
    p = command(sub, "status", "Where things are. The first command after any context reset.",
                "Without a task: every task, the backlog and the number of open findings.\n"
                "With a task: settings card, phase, branch, jobs, parked jobs with reasons, ready jobs, warnings,\n"
                "and the next suggested command.", ["status", "status claims-status --json"], [0, 1], cmd_status)
    p.add_argument("task", nargs="?")


def register_next(sub, command):
    """Add the `next` command to the parser."""
    p = command(sub, "next", "Reminder lines, then running, parked, ready and blocked jobs.",
                "Read the two reminder lines every time. Ready jobs show harness · model · effort (with the source\n"
                "when it is not global, or override) and the workspace kind.",
                ["next claims-status"], [0, 1, 2], cmd_next)
    p.add_argument("task")


def register_dispatch(sub, command):
    """Add the `dispatch` command to the parser."""
    p = command(sub, "dispatch", "Prepare the workspace and print HARNESS, MODEL, EFFORT and PROMPT for one job.",
                "Spawn a subagent with the printed PROMPT, passing the printed MODEL and EFFORT explicitly (Claude\n"
                "Code: the Agent tool's model and effort; Codex: the spawn model and reasoning_effort); no subagent\n"
                "inherits your effort. ROUTING says where the pair came from (phase table, tier, level, override).\n"
                "For a review in the\n"
                "other harness it prints COMMAND (run it in the background) and an IF IT FAILS line (run it when the\n"
                "command exits non-zero or leaves no review). --resume runs a running, parked or failed job again\n"
                "with --reason; the message also works for a fresh agent.",
                ["dispatch claims-status STATUS-API", "dispatch claims-status STATUS-API --resume --reason verify-failed"],
                [0, 1, 2, 4], cmd_dispatch)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--provider", choices=HARNESSES, help="review jobs: the harness that reviews")
    p.add_argument("--harness", choices=HARNESSES, help="override the harness for this dispatch")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--reason")
