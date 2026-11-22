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
from .fix_loop import changes_required_lines
from .graph import (
    active_holds,
    add_due_review,
    due_reviews,
    integration_parked,
    is_ready,
    kind_allowed_now,
    last_round,
    release_command,
    round_fixes,
    unaccepted_changes,
    waits_for,
    writer_blocked,
    writer_slot_notice,
)
from .markdown import first_heading, has_content, md_section, split_frontmatter
from .launch import (
    bypass_line,
    exception_text,
    how_to_run_line,
    if_it_fails,
    is_command_job,
    launch_command,
    launch_record,
    refuse_missing_cli,
    routing_exception,
)
from .park_story import INTEGRATION, limit_parked_jobs, mark_approach_check, park_stories, park_story, park_story_text
from .prompts import EARLIER_RESULT_POINTER, build_prompt
from .reviews import materialize_integration_review
from .routing import easy_fallback_notice, model_text, resolve_model, routing_text, short_text
from .stakes import find_stakes, profile_path, status_line as stakes_status_line
from .session_tokens import record_session_snapshot
from .tasks import (
    Task,
    empty_result_slot,
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
            "bypass": bypass_line(task),  # [NO-SANDBOX-VISIBLE]
            "approvals": task.info.get("approvals", {}), "jobs": rows, "parked": parked, "ready": ready,
            "warnings": warnings, "integration": integration_notice(task), "parked_task": integration_parked(task),
            "park_stories": park_stories(task),  # [PARK-STORY]
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
        found = find_stakes(task.root)  # [STAKES-LOOKUP]: read at status time, like a dispatch
        lines += [data["settings_card"]] + ([data["bypass"]] if data["bypass"] else [])
        lines += [stakes_status_line(task.root, found), f"Last change: {age_text(data['last_change'])}"]
        data["stakes"] = {"source": str(found.path) if found else None, "profile": str(profile_path(task.root))}
        data["routing_notice"] = easy_fallback_notice(task)  # [EASY-UPGRADE]
        if data["routing_notice"]:
            lines.append(data["routing_notice"])
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
            lines += job_story_lines(task)
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
        # "last change", never "running for", and no "interrupted" status: a dead worker
        # still shows `running`; only the age of its last change tells the owner.
        lines += ["Running:"] + [f"  {r['id']} — last change {age_text(r['last_change'])}" for r in data["running"]]
    if data["parked"]:
        lines += ["Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
        lines += job_story_lines(task)
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


def job_story_lines(task: Task) -> list[str]:
    """[PARK-STORY]: the story of each job parked at the round limit, after the parked list."""
    out: list[str] = []
    for job_id in limit_parked_jobs(task):
        story = park_story(task, job_id)
        if story:
            out += ["", park_story_text(task, story), ""]
    return out


def integration_notice(task: Task) -> str | None:
    """The parked task, or a changes-required integration round that waits for fix jobs
    ([INTEGRATION-REVIEW-ROUNDS]), with the ways forward."""
    last = last_round(task, "integration")
    if not last or not unaccepted_changes(task.jobs[last]):
        return None
    story = park_story(task, INTEGRATION)  # [PARK-STORY]: the parked task
    if story:
        return park_story_text(task, story)
    if round_fixes(task, last):
        return None
    return "\n".join([f"{last} requires changes.", *changes_required_lines(task, last, INTEGRATION)])


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
            "park_stories": park_stories(task),  # [PARK-STORY]
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
        cli_checked = False
        if job_id not in task.jobs and job_id in due:
            # [HARNESS-FALLBACK]: a missing CLI refuses before the due review is added
            refuse_missing_cli(task, job_id, cfg_or_fail(config), args.harness, args.provider, args.resume)
            cli_checked = True
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
        elif job["status"] == "dropped":
            fail(EXIT_USAGE, f"{job_id} is dropped: a dropped job never runs again.")
        elif job["status"] != "pending":
            fail(EXIT_USAGE, f"{job_id} is {job['status']}. To run it again: --resume --reason \"<why>\".")
        # Gate order, all before any change: the parked task and a hold (a decision job only advises,
        # so it passes both [DECISION-ANYTIME]), what the job waits for, a busy writer slot, then the
        # missing CLI [HARNESS-FALLBACK]. A parked job that never started (a missing CLI) is a first
        # dispatch, also with --resume.
        if not args.resume or (job["status"] == "parked" and not job["attempts"]):
            if job["kind"] != "decision":
                parked = integration_parked(task)
                if parked:
                    fail(EXIT_GATE, f"The task is parked at the round limit by {parked}: only decision jobs are "
                                    f"dispatched until the user chooses. The story and the options: sae next {task.id}")
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
        if not cli_checked:  # [HARNESS-FALLBACK]: before the workspace, the attempt and any event
            refuse_missing_cli(task, job_id, cfg_or_fail(config), args.harness, args.provider, args.resume)
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
        exception = routing_exception(task, job_id, config, model, args.harness, args.provider, args.reason)
        if exception:
            attempt["routing_exception"] = exception  # [HARNESS-FALLBACK]
        previous = job["attempts"][-1] if job["attempts"] else None
        if args.resume and previous and previous.get("launch") and not previous.get("ended"):
            previous["ended"] = attempt["started"]  # [HARNESS-FALLBACK]: the failed COMMAND's attempt ends here
        command_job = is_command_job(task, model["harness"])  # [WRITER-COMMAND]
        if command_job:
            attempt["launch"] = launch_record(task, job_id, model)  # [LAUNCH-RECORD]
        mark_approach_check(task, job_id)  # [APPROACH-CHECK]: later fixes of the target get it too
        earlier = empty_result_slot(task, job_id)  # the one place: collect accepts only a result this attempt writes
        job["attempts"].append(attempt)
        if card is not None and job_id in [b["id"] for b in card["jobs"]]:
            record_card(task, card)
        job["status"] = "running"
        task.touch(job)
        task.event("job.dispatched", job=job_id, attempt=attempt["n"], harness=model["harness"],
                   model=model["model"], effort=model["effort"], source=model["source"], tier=model["tier"],
                   workspace=rel(workdir, task.root) or ".",
                   reason=args.reason, **({"launch": attempt["launch"]} if command_job else {}))
        if exception:
            task.event("routing.exception", job=job_id, attempt=attempt["n"], **exception)
        if task.phase == "executing":
            record_session_snapshot(task, "dispatch", "executing")  # [MAIN-TOKENS], [AMEND-1]
        external = command_job and job["kind"] == "review"  # a review in the other harness replies with its text
        prompt = build_prompt(task, job_id, workdir, branch, model, config, external=external)
        extra = [EARLIER_RESULT_POINTER.format(path=earlier)] if earlier else []
        if args.resume:
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
        elif extra:
            prompt = "\n".join([*extra, "", prompt])
        header = (f"HARNESS: {model['harness']} · MODEL: {model_text(model)} · EFFORT: {model['effort']}\n"
                  f"ROUTING: {routing_text(model)}" + (f" · {exception_text(exception)}" if exception else ""))
        data = {"job": job_id, "attempt": attempt["n"], "workspace": str(workdir), "branch": branch, **model,
                "routing_exception": exception}
        if command_job:
            command = launch_command(task, job_id, model, prompt, task.root if external else workdir)
            fallback, rule = if_it_fails(task, job_id, model)
            how = how_to_run_line(task, job_id)
            data.update({"command": command, "how_to_run": how, "if_it_fails": fallback, "rule": rule,
                         "launch": attempt["launch"]})
            emit(args, "\n".join([header, "COMMAND:", command, how, "IF IT FAILS:", fallback, *rule]), data)
        else:
            data["prompt"] = prompt
            emit(args, f"{header}\nPROMPT:\n{prompt}", data)
    return EXIT_OK


def register_status(sub, command):
    """Add the `status` command to the parser."""
    p = command(sub, "status", "Where things are. The first command after any context reset. Read-only.",
                "Without a task: every task, the backlog and the number of open findings.\n"
                "With a task: the process map, settings card, phase, branch, holds, jobs, parked jobs with reasons\n"
                "(the story of each park at the review-round limit: rounds, findings, fix limits, options),\n"
                "open asks (sae ask), ready jobs, warnings, and the next suggested command. Writes nothing.", ["status", "status claims-status --json"], [0, 1], cmd_status)
    p.add_argument("task", nargs="?")


def register_next(sub, command):
    """Add the `next` command to the parser."""
    p = command(sub, "next", "Process map, reminder, notices, next-step card, then running, ready and blocked jobs.",
                "Read the reminder every time. Notices: an active hold and its release command, the parked task,\n"
                "the story of each park at the review-round limit (relay it to the user), full writer slots, how\n"
                "to resume in another session. A next-step card comes before research, the planner, a spec, plan\n"
                "or integration review, and the start of execution; sae dispatch of a job on it records it.\n"
                "Ready jobs show harness · model · effort (with the source when it is not global, or override)\n"
                "and the workspace kind; a due spec or plan review is listed too.\n"
                "Read-only, except when it adds a due integration review round.",
                ["next claims-status"], [0, 1, 2], cmd_next)
    p.add_argument("task")


def register_dispatch(sub, command):
    """Add the `dispatch` command to the parser."""
    p = command(sub, "dispatch", "Prepare the workspace and print HARNESS, MODEL, EFFORT and PROMPT for one job.",
                "Spawn a subagent with the printed PROMPT, passing the printed MODEL and EFFORT explicitly (Claude\n"
                "Code: the Agent tool's model and effort; Codex: the spawn model and reasoning_effort); no subagent\n"
                "inherits your effort. ROUTING says where the pair came from (phase table, tier, level, override)\n"
                "and names a routing exception (a fallback or a flag on another harness than routing chose).\n"
                "For any job in the other harness it prints a COMMAND instead of the PROMPT, with how to run it, and\n"
                "an IF IT FAILS line (for when the command exits non-zero or leaves no result) with the rule for this\n"
                "job and mode: a review falls back at once in every mode; any other job only in full-auto, else it is\n"
                "parked (sae job park) until the owner says yes. A review COMMAND runs read-only; any other job's\n"
                "COMMAND runs without a sandbox (bypass requested). The attempt records the launch. When the other\n"
                "harness's CLI is not on the PATH, dispatch refuses before anything changes and prints the fallback\n"
                "command with the same rule. --resume runs a running, parked or failed job again\n"
                "with --reason, or reopens a done research or planning job (a follow-up question; the planner\n"
                "after a plan review); sae collect then reads the updated report or result. The message also\n"
                "works for a fresh agent. A due spec or plan review is added first. Exit 3: an active hold (the\n"
                "message names the release command), or the task is parked after max-review-rounds (default 3)\n"
                "changes-required integration rounds. A decision job only advises, so it passes both. A dropped\n"
                "job never runs again.",
                ["dispatch claims-status STATUS-API", "dispatch claims-status STATUS-API --resume --reason verify-failed",
                 'dispatch claims-status PLAN --resume --reason "REVIEW-PLAN: changes required"'],
                [0, 1, 2, 3, 4], cmd_dispatch)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--provider", choices=HARNESSES, help="review jobs: the harness that reviews")
    p.add_argument("--harness", choices=HARNESSES, help="override the harness for this dispatch")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--reason")
