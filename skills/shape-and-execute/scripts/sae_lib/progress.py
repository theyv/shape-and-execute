"""Commands status, next and dispatch."""

from __future__ import annotations

import contextlib
import json
import re
from pathlib import Path

from .common import (
    EXIT_GATE,
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
from .asks import ask_reminder_line, open_asks
from .config import ask_signal, cfg, load_config, settings_card
from .gitutil import find_root, git
from .control import (
    hold_notices,
    holds_data,
    next_step_card,
    process_map,
    record_card,
)
from .findings import open_findings
from .graph import (
    active_holds,
    add_due_review,
    due_reviews,
    integration_parked,
    is_ready,
    kind_allowed_now,
    last_round,
    requires_changes,
    release_command,
    waits_for,
    writer_blocked,
    writer_slot_notice,
)
from .markdown import first_heading, has_content, md_section, split_frontmatter
from .prompts import build_prompt, external_review_command
from .reviews import fix_job_command, materialize_integration_review
from .routing import model_text, resolve_model, routing_text, short_text
from .tasks import (
    Task,
    job_file,
    job_summary,
    last_model,
    locate_tasks,
    open_task,
    picked_up_items,
    parked_reason,
    result_file,
    tasks_dir,
)
from .viewer import stamped_items
from .workspaces import prepare_workspace, workspace_of


def ready_ids(task: Task) -> list[str]:
    """Ready jobs, with a due spec or plan review that is not a job yet."""
    return [i for i in task.jobs if is_ready(task, i)] + due_reviews(task)


def next_command(task: Task) -> str:
    phase, jobs = task.phase, task.jobs
    ready = ready_ids(task)
    if phase == "shaping":
        if ready:
            return f"sae dispatch {task.id} {ready[0]}"
        if any(j["status"] == "running" for j in jobs.values()):
            return f"When the subagent returns:\n  sae collect {task.id} <ID>"
        return f"sae check {task.id}\nThen:\n  sae approve {task.id} spec"
    if phase == "planning":
        if ready:
            return f"sae dispatch {task.id} {ready[0]}"
        if any(j["status"] == "running" for j in jobs.values()):
            return f"When the subagent returns:\n  sae collect {task.id} <ID>"
        if "plan" in task.info["approvals"]:
            return f"sae start {task.id}"
        return f"sae check {task.id}\nThen:\n  sae approve {task.id} plan"
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
    ready += due_reviews(task)
    return {"task": task.id, "title": task.info["title"], "phase": task.phase, "branch": task.info.get("branch"),
            "worktree": task.info.get("worktree"), "home": task.info.get("home"), "folder": str(task.dir),
            "layout": task.info.get("layout"), "last_change": task.info.get("last_change"),
            "settings": task.settings,
            "settings_card": settings_card(task.settings, task.info.get("orchestrator_harness")),
            "approvals": task.info.get("approvals", {}), "jobs": rows, "parked": parked, "ready": ready,
            "warnings": warnings, "integration": integration_notice(task), "parked_task": integration_parked(task),
            "holds": holds_data(task), "asks": open_asks(task), "ask_signal": ask_signal(task.settings),
            "map": process_map(task)["lines"], "next": next_command(task)}


def cmd_status(args) -> int:
    root, _ = find_root()
    if args.task:
        with open_task(root, args.task, write=False) as task:  # [READ-ONLY-COMMANDS]
            data = task_status_data(task)
            notices = hold_notices(task)
        lines = ["\n".join(data["map"]), "", data["title"], f"{data['task']}",
                 " · ".join([f"phase: {data['phase']}"] + ([f"branch: {data['branch']}"] if data["branch"] else [])
                            + ([f"layout: {data['layout']}"] if data["layout"] else []))]
        if data["worktree"]:
            lines.append(f"Task worktree: {data['worktree']}")
        lines += [data["settings_card"], f"Last change: {age_text(data['last_change'])}"]
        approvals = ", ".join(f"{k} by {v['by']}" for k, v in data["approvals"].items())
        if approvals:
            lines.append(f"Approved: {approvals}")
        if data["holds"]:
            lines += ["", "Holds:"] + [f"  after {h['job']}" + (" (active)" if h["active"] else "")
                                       + (f" — {h['reason']}" if h["reason"] else "") for h in data["holds"]]
        if data["jobs"]:
            lines += ["", "Jobs:"]
            for r in data["jobs"]:
                status = r["status"] + (" ✓merged" if r["merged"] else "")
                lines.append("  " + " · ".join([r["id"], r["kind"], status, age_text(r["last_change"])]))
                if r["model"] != "-":
                    lines.append(f"    {r['model']}")
        if data["parked"]:
            lines += ["", "Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
        if data["asks"]:
            # "waiting" only in executing, like owner_wait()
            heading = "Open asks (waiting for the owner):" if data["phase"] == "executing" else "Open asks:"
            lines += ["", heading] + [
                f"  {a['n']}." + (f" {a['job']}:" if a["job"] else "") + f" {a['question']}" for a in data["asks"]]
        if data["integration"]:
            lines += ["", data["integration"]]
        if notices:
            lines += [""] + notices
        if data["ready"]:
            lines += ["", "Ready: " + ", ".join(data["ready"])]
        if data["warnings"]:
            lines += ["", "Warnings:"] + [f"  - {w}" for w in data["warnings"]]
        lines += ["", f"Next: {data['next']}"]
        emit(args, "\n".join(lines), data)
        return EXIT_OK
    tasks = []
    located = locate_tasks(root)
    for task_id in sorted(located, reverse=True):
        copy = located[task_id]
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            state = read_json(copy.folder / "state.json")
            statuses = [j["status"] for j in state["jobs"].values()]
            tasks.append({"id": task_id, "title": state["task"]["title"], "phase": state["task"]["phase"],
                          "last_change": state["task"].get("last_change"), "running": statuses.count("running"),
                          "parked": statuses.count("parked"), "location": str(copy.checkout),
                          "folder": str(copy.folder)})
    picked = picked_up_items(located)
    backlog = []
    for path in stamped_items(tasks_dir(root) / "backlog", areas=True):
        meta, body = split_frontmatter(read_text(path, ""))
        backlog.append({"file": rel(path, root), "title": re.sub(r"^Intent:\s*", "", first_heading(body) or path.stem),
                        "source": meta.get("source"), "created": stamp_time(path.name),
                        "picked_up_by": picked.get(rel(path, root))})
    findings = len(open_findings(root))
    lines = []
    if tasks:
        lines.append("Tasks:")
        for entry in tasks:
            lines += [f"  {entry['id']}", f"    {entry['title']}",
                      "    " + " · ".join([entry["phase"], age_text(entry["last_change"]),
                                           f"running: {entry['running']}", f"parked: {entry['parked']}"])]
            if Path(entry["location"]).resolve() != root.resolve():
                lines += ["    Location:", f"      {entry['location']}"]
    else:
        lines.append("No tasks.")
    if backlog:
        rows = [[b["file"], b["title"], age_text(b["created"]),
                 (f"from {b['source']}" if b["source"] else "")
                 + (f" picked up by {b['picked_up_by']}" if b["picked_up_by"] else "")]
                for b in backlog]
        lines += ["", "Backlog:", table(rows)]
    lines += ["", f"Open findings: {findings}"]
    emit(args, "\n".join(lines), {"tasks": tasks, "backlog": backlog, "open_findings": findings})
    return EXIT_OK


def reminder_lines(task: Task, ask_reminder: bool = False) -> list[str]:
    """The mode with the classes to ask on, the hard stops, then, for `sae next` only
    (`ask_reminder`), the sae ask line when it is due ([ASK-REMINDER])."""
    ask = ask_reminder_line(task) if ask_reminder else None
    return [mode_line(task.settings["interaction"]), HARD_STOPS_LINE] + ([ask] if ask else [])


def next_text(task: Task, config: dict | None, data: dict | None = None, ask_reminder: bool = False) -> str:
    """The `sae next` text. On a writable task (sae start) the start next-step card it prints
    is recorded; `sae next` itself is read-only and only prints it. `ask_reminder`: `sae next`
    passes True; `sae start` leaves the sae ask line out ([ASK-REMINDER])."""
    data = data or next_data(task, config)
    if task.writable and data["card"] is not None and data["card"].get("start"):
        record_card(task, data["card"])
    lines = ["\n".join(data["map"]), ""] + reminder_lines(task, ask_reminder) + [""]
    notices = hold_notices(task)
    if data["integration"]:
        notices.append(data["integration"])
    if data["slots"]:
        notices.append(data["slots"])
    notices.append(f"Another session:\n  sae start {task.id} --harness claude|codex")  # [RESUME-HARNESS-HINT]
    lines += notices + [""]
    if data["card"] is not None:
        lines += [data["card"]["text"], ""]
    if data["running"]:
        lines += ["Running:"] + [f"  {r['id']} — last change {age_text(r['last_change'])}" for r in data["running"]]
    if data["parked"]:
        lines += ["Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
    if data["ready"]:
        lines += ["Ready (dispatch each):", "  sae dispatch <task> <ID>"]
        for r in data["ready"]:
            lines.append("  " + " · ".join([r["id"], r["kind"], r["difficulty"]]))
            lines.append("    " + " · ".join([r["model"], r["workspace"]]))
            if r.get("blocked"):
                lines.append(f"    waits: {r['blocked']}")
    if data["blocked"]:
        lines += ["Blocked:"] + [f"  {b['id']} — waits for {', '.join(b['waits_for'])}" for b in data["blocked"]]
    if data["failed"]:
        lines += ["Failed:"] + [f"  {f['id']} — {f['summary']}" for f in data["failed"]]
    if data["all_done"]:
        lines.append(f"All jobs done. Run: sae finish {task.id}")
    elif data["holds_active"]:
        lines.append(f"Held: report to the owner. Release with: {release_command(task, data['holds_active'][0])}")
    elif task.phase in ("shaping", "planning") and not (data["running"] or data["ready"]):
        lines.append(f"Next: {next_command(task)}")
    elif not (data["running"] or data["ready"] or data["parked"] or data["integration"]):
        lines.append("Nothing can run. Adapt the graph, resume a failed job, or finish with --with-open.")
    return "\n".join(lines).rstrip()


def integration_notice(task: Task) -> str | None:
    """The parked task, or a changes-required integration round that waits for fix jobs
    ([INTEGRATION-REVIEW-ROUNDS]), with the ways forward."""
    last = last_round(task, "integration")
    if not last or not requires_changes(task.jobs[last]):
        return None
    forward = f"sae finish {task.id} --override \"<reason>\""
    if integration_parked(task):
        return "\n".join([f"The task is parked for the owner: {last} still requires changes after a fix round. "
                          "Nothing is dispatched until the owner chooses:",
                           "  - more fix jobs:", f"    {fix_job_command(task, last)}",
                           "  - or close anyway:", f"    {forward}"])
    if any(j.get("fix_of") == last for j in task.jobs.values()):
        return None
    return "\n".join([f"{last} requires changes. Add fix jobs (sae adds the next round when they are merged):",
                      f"  {fix_job_command(task, last)}",
                       "Or, on the owner's word:", f"  {forward}"])


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
            if reasons == [f"phase {task.phase}"] and task.phase in ("shaping", "planning"):
                continue  # a job of a later phase: not blocked, just not yet
            if reasons:
                blocked.append({"id": job_id, "waits_for": reasons})
                continue
            model = resolve_model(task, job_id, cfg_or_fail(config), exact=False)
            workdir, _ = workspace_of(task, job_id, config)
            entry = {"id": job_id, "kind": job["kind"], "difficulty": model["difficulty"],
                     "model": short_text(model), "routing": model,
                     "workspace": "job worktree" if workdir != task.root else
                                  (f"{task_checkout_name(task)}, writes" if job["kind"] in WRITER_KINDS
                                   else f"{task_checkout_name(task)}, read-only")}
            if job["kind"] in WRITER_KINDS:
                entry["blocked"] = writer_blocked(task, job_id, config)
            ready.append(entry)
    for review_id in due_reviews(task):
        model = resolve_model(task, review_id, cfg_or_fail(config), exact=False)
        ready.append({"id": review_id, "kind": "review", "difficulty": model["difficulty"], "due": True,
                      "model": short_text(model), "routing": model,
                      "workspace": f"{task_checkout_name(task)}, read-only"})
    open_statuses = {j["status"] for j in task.jobs.values()} & {"running", "pending", "parked"}
    notice = integration_notice(task)
    card = next_step_card(task, config, [r["id"] for r in ready])
    return {"running": running, "parked": parked, "ready": ready, "blocked": blocked, "failed": failed,
            "integration": notice, "parked_task": integration_parked(task),
            "holds": holds_data(task), "holds_active": active_holds(task),
            "slots": writer_slot_notice(task, config), "card": card,
            "map": process_map(task)["lines"],
            "resume": f"sae start {task.id} --harness claude|codex",
            "all_done": not open_statuses and not notice and task.phase == "executing"}


def cfg_or_fail(config: dict | None) -> dict:
    if config is None:
        cfg(config, "routing")  # exits 2 with the setup hint
    return config


def task_checkout_name(task: Task) -> str:
    if task.worktree:
        return "task worktree"
    return "home checkout" if task.info.get("git") else "folder"


def cmd_next(args) -> int:
    root, _ = find_root()
    config = load_config()
    with open_task(root, args.task, write=False) as task:  # [READ-ONLY-COMMANDS]
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        probe: list[str] = []
        materialize_integration_review(task, probe)
    out: list[str] = []
    if probe:  # a round is due: the one case in which next changes the task
        with open_task(root, args.task) as task:
            materialize_integration_review(task, out)
            data = next_data(task, config)
            text = next_text(task, config, data, ask_reminder=True)
    else:
        with open_task(root, args.task, write=False) as task:
            data = next_data(task, config)
            text = next_text(task, config, data, ask_reminder=True)
    data["reminder"] = reminder_lines(task, ask_reminder=True)
    emit(args, ("\n".join(out) + "\n" if out else "") + text, data)
    return EXIT_OK


def cmd_dispatch(args) -> int:
    root, _ = find_root()
    config = load_config()
    with open_task(root, args.task) as task:
        job_id = args.id
        due = [] if args.resume else due_reviews(task)
        card = None
        if not args.resume and (job_id in due or (job_id in task.jobs and is_ready(task, job_id))):
            card = next_step_card(task, config, ready_ids(task))  # the card sae next shows now
        if job_id not in task.jobs and job_id in due:
            add_due_review(task, job_id)  # a due spec or plan review is added by its dispatch
        job = task.job(job_id)
        if args.resume:
            if not (args.reason or "").strip():
                fail(EXIT_USAGE, "--resume needs --reason.")
            reopen = job["status"] == "done" and job["kind"] in ("research", "planning")  # [RESEARCH-FOLLOW-UP]
            if job["status"] not in ("running", "parked", "failed") and not reopen:
                fail(EXIT_USAGE, f"{job_id} is {job['status']}; --resume is for running, parked or failed jobs, "
                                 "and for done research or planning jobs.")
            if not kind_allowed_now(task, job):
                fail(EXIT_USAGE, f"{job['kind']} jobs do not run in phase {task.phase}.")
        else:
            if job["status"] != "pending":
                fail(EXIT_USAGE, f"{job_id} is {job['status']}. To run it again: --resume --reason \"<why>\".")
            parked = integration_parked(task)
            if parked:
                fail(EXIT_GATE, integration_notice(task))
            held = active_holds(task)
            if held:
                fail(EXIT_GATE, f"Hold after {held[0]}: nothing new is dispatched. Report to the owner.\n"
                                f"  Release: {release_command(task, held[0])}")
            reasons = waits_for(task, job_id)
            if reasons:
                fail(EXIT_USAGE, f"{job_id} is not ready: waits for {', '.join(reasons)}.")
        if job["kind"] in WRITER_KINDS and job["status"] != "running":
            blocked = writer_blocked(task, job_id, config)
            if blocked:
                fail(EXIT_USAGE, f"{job_id} must wait: {blocked}.")
        model = resolve_model(task, job_id, config, harness=args.harness, provider=args.provider)
        workdir, branch = prepare_workspace(task, job_id, config)
        head = None
        if task.info.get("git") and job["kind"] in WRITER_KINDS:
            head = git(workdir, "rev-parse", "HEAD")
        elif task.info.get("git") and job.get("target") == "integration" and task.info.get("branch"):
            head = git(task.root, "rev-parse", task.info["branch"])  # the next round's diff starts here
        attempt = {"n": len(job["attempts"]) + 1, "harness": model["harness"], "model": model["model"],
                   "model_entry": model["model_entry"], "effort": model["effort"], "source": model["source"],
                   "tier": model["tier"], "started": iso(), "ended": None,
                   "tokens": None, "duration_s": None, "agent_ref": None, "reason": args.reason, "head": head}
        job["attempts"].append(attempt)
        if card is not None and job_id in [b["id"] for b in card["jobs"]]:
            record_card(task, card)
        job["status"] = "running"
        task.touch(job)
        task.event("job.dispatched", job=job_id, attempt=attempt["n"], harness=model["harness"],
                   model=model["model"], effort=model["effort"], source=model["source"], tier=model["tier"],
                   workspace=rel(workdir, task.root) or ".",
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
            plan_review = last_round(task, "plan")
            if job["kind"] == "planning" and plan_review and task.jobs[plan_review]["status"] == "done":
                extra.append(f"Read first: the plan review {result_file(task, plan_review)}")
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
    p = command(sub, "status", "Where things are. The first command after any context reset. Read-only.",
                "Without a task: every task, the backlog and the number of open findings.\n"
                "With a task: the process map, settings card, phase, branch, holds, jobs, parked jobs with reasons,\n"
                "open asks (sae ask), ready jobs, warnings, and the next suggested command. Writes nothing.", ["status", "status claims-status --json"], [0, 1], cmd_status)
    p.add_argument("task", nargs="?")


def register_next(sub, command):
    """Add the `next` command to the parser."""
    p = command(sub, "next", "Process map, reminder, notices, next-step card, then running, ready and blocked jobs.",
                "Read the reminder every time. Notices: an active hold and its release command, the parked task,\n"
                "full writer slots, how to resume in another session. A next-step card comes before research, the\n"
                "planner, a spec, plan or integration review, and the start of execution; sae dispatch of a job\n"
                "on it records it. Ready jobs show harness · model · effort (with the source when it is not\n"
                "global, or override) and the workspace kind; a due spec or plan review is listed too.\n"
                "Read-only, except when it adds a due integration review round.",
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
                "with --reason, or reopens a done research or planning job (a follow-up question; the planner\n"
                "after a plan review); sae collect then reads the updated report or result. The message also\n"
                "works for a fresh agent. A due spec or plan review is added first. Exit 3: an active hold (the\n"
                "message names the release command), or the task is parked after a second changes-required\n"
                "integration round.",
                ["dispatch claims-status STATUS-API", "dispatch claims-status STATUS-API --resume --reason verify-failed",
                 'dispatch claims-status PLAN --resume --reason "REVIEW-PLAN: changes required"'],
                [0, 1, 2, 3, 4], cmd_dispatch)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--provider", choices=HARNESSES, help="review jobs: the harness that reviews")
    p.add_argument("--harness", choices=HARNESSES, help="override the harness for this dispatch")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--reason")
