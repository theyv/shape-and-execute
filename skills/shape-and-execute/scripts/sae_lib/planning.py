"""Commands set, approve, check and job add|edit|remove."""

from __future__ import annotations

import json
import os
import re

from .common import (
    DIFFICULTIES,
    EXIT_GATE,
    EXIT_OK,
    EXIT_USAGE,
    HARNESSES,
    INTERACTION_MODES,
    JOB_ID_RE,
    JOB_KINDS,
    LEVELS,
    Parser,
    REVIEW_POINTS,
    WRITER_KINDS,
    emit,
    fail,
    iso,
    write_atomic,
)
from .config import settings_card, settings_diff, settings_errors
from .gitutil import find_root, git_user
from .graph import run_check
from .tasks import Task, is_generated, job_file, new_job, open_task, template


SET_KEYS = {
    "interaction": ("interaction",), "research": ("levels", "research"), "planning": ("levels", "planning"),
    "execution": ("levels", "execution"), "review-level": ("levels", "review"), "review": ("review", "points"),
    "reviewer": ("review", "provider"), "max-verify-failures": ("max_verify_failures",),
}


def cmd_set(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        new = json.loads(json.dumps(task.settings))
        for pair in args.pairs:
            if "=" not in pair:
                fail(EXIT_USAGE, f"Expected key=value, got {pair!r}. Keys: {', '.join(SET_KEYS)}.")
            key, value = pair.split("=", 1)
            if key not in SET_KEYS:
                fail(EXIT_USAGE, f"Unknown key {key!r}. Keys: {', '.join(SET_KEYS)}.")
            path = SET_KEYS[key]
            parsed: object = value
            if key == "review":
                parsed = [] if value == "off" else [p.strip() for p in value.split(",") if p.strip()]
            elif key == "max-verify-failures":
                if not re.fullmatch(r"\d+", value):
                    fail(EXIT_USAGE, "max-verify-failures must be an integer from 1 to 10.")
                parsed = int(value)
            node = new
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = parsed
        errors = settings_errors(new)
        if errors:
            fail(EXIT_USAGE, "Invalid settings: " + "; ".join(errors))
        changes = settings_diff(task.settings, new)
        if changes:
            task.write_settings(new)
            task.event("settings.changed", changes=changes, by="cli")
        emit(args, f"Settings: {settings_card(new)}" + ("" if changes else " (unchanged)"),
             {"settings": new, "changes": changes})
    return EXIT_OK


def cmd_approve(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        gate = args.gate
        if gate == "spec" and task.phase != "shaping":
            fail(EXIT_USAGE, f"Spec approval needs phase shaping; the task is in {task.phase}.")
        if gate == "plan" and task.phase != "planning":
            fail(EXIT_USAGE, f"Plan approval needs phase planning; the task is in {task.phase}.")
        if gate == "spec" and not (task.dir / "intent.md").exists():
            fail(EXIT_GATE, "intent.md is missing.")
        errors, warnings, added = run_check(task)
        task.save()  # keep the check event and a materialized review even when the gate refuses
        report = check_text(errors, warnings, added)
        if errors:
            fail(EXIT_GATE, f"{report}\nApproval refused: fix the errors first.")
        target = "spec" if gate == "spec" else "plan"
        for job_id, job in task.jobs.items():
            if job["kind"] == "review" and job.get("target") == target and job["status"] != "done":
                fail(EXIT_GATE, f"{report}\nApproval refused: {job_id} is {job['status']}. "
                                f"Dispatch and collect it first: sae dispatch {task.id} {job_id}")
        if gate == "plan":
            open_jobs = [i for i, j in task.jobs.items()
                         if j["kind"] in ("planning", "research") and j["status"] != "done"]
            if open_jobs:
                fail(EXIT_GATE, f"Approval refused: {', '.join(open_jobs)} not done.")
            if not any(not is_generated(i, j) and j["kind"] not in ("planning", "research")
                       for i, j in task.jobs.items()):
                fail(EXIT_GATE, "Approval refused: the plan has no jobs. Add them with sae job add.")
        by = git_user(root)
        task.info["approvals"][gate] = {"at": iso(), "by": by}
        if gate == "spec":
            task.info["phase"] = "planning"
        task.event(f"{gate}.approved", by=by)
        follow = f"sae start {task.id}" if gate == "plan" else "planning: load references/modes/plan.md"
        emit(args, (report + "\n" if report else "") + f"{gate.capitalize()} approved by {by}. Next: {follow}",
             {"approved": gate, "by": by, "phase": task.phase, "warnings": warnings})
    return EXIT_OK


def check_text(errors: list[str], warnings: list[str], added: list[str]) -> str:
    lines = [f"error: {e}" for e in errors] + [f"warning: {w}" for w in warnings]
    lines += [f"Added {a}: dispatch it." for a in added]
    return "\n".join(lines)


def cmd_check(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        errors, warnings, added = run_check(task)
        text = check_text(errors, warnings, added) or "Check passed: no errors, no warnings."
        if errors:
            text += f"\n{len(errors)} error(s)."
        emit(args, text, {"errors": errors, "warnings": warnings, "added": added})
        return EXIT_GATE if errors else EXIT_OK


def parse_needs(value: str | None) -> list[str]:
    needs = [n.strip() for n in (value or "").split(",") if n.strip()]
    for need in needs:
        if not JOB_ID_RE.match(need):
            fail(EXIT_USAGE, f"Invalid job ID in --needs: {need}")
    return needs


def require_reason(task: Task, reason: str | None) -> None:
    if task.phase == "executing" and not (reason or "").strip():
        fail(EXIT_USAGE, "--reason is required during execution (graph adaptation).")


def cmd_job_add(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job_id = args.id
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        if not JOB_ID_RE.match(job_id):
            fail(EXIT_USAGE, f"Invalid job ID {job_id!r}: use UPPER-KEBAB, for example STATUS-API.")
        if job_id in task.jobs:
            fail(EXIT_USAGE, f"Job {job_id} exists.")
        if args.kind == "review":
            fail(EXIT_USAGE, "sae adds review jobs itself (review points in settings, --review on a job).")
        if args.kind == "decision":
            fail(EXIT_USAGE, f"Use: sae decision new {task.id} --from <parked job>")
        if args.final and args.kind != "validation":
            fail(EXIT_USAGE, "--final is only for validation jobs.")
        if args.final and any(j["final"] for j in task.jobs.values()):
            fail(EXIT_USAGE, "The task already has a final job.")
        if args.fix_of:
            target = task.job(args.fix_of)
            if target["kind"] not in WRITER_KINDS or args.kind != "implementation":
                fail(EXIT_USAGE, "--fix-of: a fix job is an implementation job that fixes a writer job.")
            if target["merged"]:
                fail(EXIT_USAGE, f"{args.fix_of} is already merged; add a normal job instead.")
        require_reason(task, args.reason)
        needs = parse_needs(args.needs)
        job = new_job(args.kind, needs, args.difficulty, review=args.review, final=args.final, fix_of=args.fix_of)
        task.jobs[job_id] = job
        path = job_file(task, job_id)
        if not path.exists():
            name = "job-research.md" if args.kind == "research" else "job.md"
            text = template(name).replace("<JOB-ID>", job_id).replace("<TOPIC-ID>", job_id)
            write_atomic(path, text)
        task.event("job.added", job=job_id, kind=args.kind, needs=needs, difficulty=args.difficulty,
                   review=args.review, final=args.final, fix_of=args.fix_of, reason=args.reason)
        emit(args, f"Added {job_id} ({args.kind}, {args.difficulty}). Job file: {path}",
             {"job": job_id, "file": str(path)})
    return EXIT_OK


def cmd_job_edit(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        if job["status"] != "pending":
            fail(EXIT_USAGE, f"{args.id} is {job['status']}; only pending jobs change.")
        require_reason(task, args.reason)
        changes = {}
        if args.needs is not None:
            changes["needs"] = [job["needs"], parse_needs(args.needs)]
        if args.difficulty:
            changes["difficulty"] = [job["difficulty"], args.difficulty]
        if args.review is not None:
            changes["review"] = [job["review"], args.review]
        changes = {k: v for k, v in changes.items() if v[0] != v[1]}
        if not changes:
            emit(args, f"{args.id}: nothing changed.", {"job": args.id, "changes": {}})
            return EXIT_OK
        for key, (_, value) in changes.items():
            job[key] = value
        task.touch(job)
        task.event("job.changed", job=args.id, changes=changes, reason=args.reason)
        emit(args, f"{args.id}: " + ", ".join(f"{k} {v[0]} → {v[1]}" for k, v in changes.items()),
             {"job": args.id, "changes": changes})
    return EXIT_OK


def cmd_job_remove(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        if job["status"] != "pending":
            fail(EXIT_USAGE, f"{args.id} is {job['status']}; only pending jobs can be removed.")
        if not args.reason.strip():
            fail(EXIT_USAGE, "--reason is required.")
        dependants = [i for i, j in task.jobs.items() if args.id in j["needs"]]
        if dependants:
            fail(EXIT_USAGE, f"{', '.join(dependants)} need {args.id}. Edit their --needs first.")
        del task.jobs[args.id]
        path = job_file(task, args.id)
        if path.exists():
            os.replace(path, path.with_name(f"{args.id}.removed.md"))
        task.event("job.removed", job=args.id, kind=job["kind"], reason=args.reason)
        emit(args, f"Removed {args.id}. Its job file is kept as jobs/{args.id}.removed.md.", {"job": args.id})
    return EXIT_OK


def register_set(sub, command):
    """Add the `set` command to the parser."""
    p = command(sub, "set", "Change this task's settings (settings.json).",
                f"Keys: interaction ({'|'.join(INTERACTION_MODES)}); research, planning, execution, review-level\n"
                f"({'|'.join(LEVELS)}); review (comma list of {', '.join(REVIEW_POINTS)}; or off);\n"
                f"reviewer ({'|'.join(HARNESSES)}); max-verify-failures (1-10; change it only when the user asks).\n"
                "The next dispatch uses the new values. Prints the settings card.",
                ["set claims-status execution=economy", "set claims-status review=spec,plan,selected-jobs,integration reviewer=codex"],
                [0, 1], cmd_set)
    p.add_argument("task")
    p.add_argument("pairs", nargs="+", metavar="key=value")


def register_approve(sub, command):
    """Add the `approve` command to the parser."""
    p = command(sub, "approve", "Record a gate approval: spec (shaping → planning) or plan.",
                "Runs check first; lint errors refuse. Refuses while REVIEW-SPEC (or REVIEW-PLAN) exists and is not\n"
                "collected; its verdict does not block. Plan approval also needs every planning and research job done.",
                ["approve claims-status spec", "approve claims-status plan"], [0, 1, 3], cmd_approve)
    p.add_argument("task")
    p.add_argument("gate", choices=("spec", "plan"))


def register_check(sub, command):
    """Add the `check` command to the parser."""
    p = command(sub, "check", "Lint the task and add due spec or plan reviews.",
                "In shaping: requirement IDs in specs.md and in the intent's ## Acceptance; a clean check adds\n"
                "REVIEW-SPEC when spec is a review point. Later: the graph (unknown needs, cycles, job files and\n"
                "objectives, covers, requirement coverage, final jobs) and warnings (verify, scopes, hot files, brief\n"
                "length, riskiest assumptions, objective length); a clean check in planning adds REVIEW-PLAN.",
                ["check claims-status"], [0, 1, 3], cmd_check)
    p.add_argument("task")


def register_job(sub, command):
    """Add the `job` command group to the parser; returns the group parser."""
    job = sub.add_parser("job", help="Add, edit or remove a job of the graph.", parents=[],
                         description="Graph changes. sae job <add|edit|remove> --help for details.")
    job_sub = job.add_subparsers(dest="job_command", metavar="<add|edit|remove>", parser_class=Parser)
    p = command(job_sub, "add", "Register a job and scaffold jobs/<ID>.md.",
                f"Kinds: {', '.join(k for k in JOB_KINDS if k not in ('review', 'decision'))} (sae adds review jobs;\n"
                "decision jobs come from sae decision new). ID: UPPER-KEBAB. --needs: jobs that must be done (and\n"
                "merged, for writers) first. --review: review this job (selected-jobs). --final: the final validation.\n"
                "--fix-of: an implementation job that fixes a writer job in its workspace. --reason: required during\n"
                "execution.",
                ["job add claims-status STATUS-API --kind implementation --needs STATUS-CONTRACT --difficulty hard --review",
                 'job add claims-status STATUS-API-FIX-1 --kind implementation --fix-of STATUS-API --reason "REVIEW-STATUS-API: changes required"'],
                [0, 1], cmd_job_add)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--kind", required=True, choices=[k for k in JOB_KINDS if k not in ("review", "decision")])
    p.add_argument("--needs", metavar="A,B")
    p.add_argument("--difficulty", choices=DIFFICULTIES, default="normal")
    p.add_argument("--review", action="store_true")
    p.add_argument("--final", action="store_true")
    p.add_argument("--fix-of", metavar="ID")
    p.add_argument("--reason")
    p = command(job_sub, "edit", "Change the scheduling fields of a pending job.", "--reason: required during execution.",
                ['job edit claims-status STATUS-UI --needs STATUS-API --reason "UI needs the real endpoint"'], [0, 1],
                cmd_job_edit)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--needs", metavar="A,B", help="replaces the list; empty string clears it")
    p.add_argument("--difficulty", choices=DIFFICULTIES)
    p.add_argument("--review", dest="review", action="store_true", default=None)
    p.add_argument("--no-review", dest="review", action="store_false")
    p.add_argument("--reason")
    p = command(job_sub, "remove", "Remove a pending job; its file is kept as jobs/<ID>.removed.md.",
                "Refuses while another job needs it.", ['job remove claims-status STATUS-CACHE --reason "not needed"'],
                [0, 1], cmd_job_remove)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    return job
