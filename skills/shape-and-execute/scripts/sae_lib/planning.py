"""Commands set, approve, check and job add|edit|remove|override."""

from __future__ import annotations

import json
import os

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
    SaeError,
    changed_by,
    emit,
    fail,
    iso,
    wrap,
    wrap_parts,
    write_atomic,
)
from .config import (
    REVIEW_PROVIDERS,
    ROUTING_KEYS_HELP,
    SET_KEYS,
    apply_routing_key,
    is_routing_key,
    level_routing_errors,
    load_config,
    parse_set_value,
    routing_layers,
    settings_card,
    settings_diff,
    settings_errors,
    task_difficulty,
)
from .gitutil import find_root, git_user
from .graph import last_round, requires_changes, run_check
from .routing import TASK_TARGETS, override_key, planned_review_target, resolve_model
from .tasks import Task, is_generated, job_file, new_job, open_task, template


def cmd_set(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        new = json.loads(json.dumps(task.settings))
        routing_changed = False
        for pair in args.pairs:
            if "=" not in pair:
                fail(EXIT_USAGE, f"Expected key=value, got {pair!r}. Keys: {', '.join(SET_KEYS)}, {ROUTING_KEYS_HELP}.")
            key, value = pair.split("=", 1)
            if is_routing_key(key):
                routing = new.setdefault("routing", {})
                apply_routing_key(routing, key, value)
                if not routing:
                    del new["routing"]
                routing_changed = True
                continue
            if key not in SET_KEYS:
                fail(EXIT_USAGE, f"Unknown key {key!r}. Keys: {', '.join(SET_KEYS)}, {ROUTING_KEYS_HELP}.")
            path = SET_KEYS[key]
            node = new
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = parse_set_value(key, value)
        errors = settings_errors(new)
        if not errors and routing_changed and new.get("routing"):
            config = load_config()
            errors = level_routing_errors(config, new["routing"], "routing",
                                          routing_layers(config, task.root, new))
        if errors:
            fail(EXIT_USAGE, "Invalid settings: " + "; ".join(errors))
        changes = settings_diff(task.settings, new)
        if changes:
            task.write_settings(new)
            task.event("settings.changed", changes=changes, by=changed_by())
        card = settings_card(new, task.info.get("orchestrator_harness"))
        emit(args, ("Settings:" if changes else "Settings (unchanged):") + "\n" + wrap_parts(card.split(" · ")),
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
        follow = (f"sae start {task.id}\n  (another session: sae start {task.id} --harness claude|codex)"
                  if gate == "plan" else "planning: load references/modes/plan.md")  # [RESUME-HARNESS-HINT]
        emit(args, (report + "\n" if report else "") + f"{gate.capitalize()} approved by {by}. Next: {follow}",
             {"approved": gate, "by": by, "phase": task.phase, "warnings": warnings})
    return EXIT_OK


def check_text(errors: list[str], warnings: list[str], added: list[str], task_id: str | None = None) -> str:
    """Lint lines; then the added reviews (sae approve) or, with `task_id`, the due ones (sae check)."""
    lines = [f"error: {e}" for e in errors] + [f"warning: {w}" for w in warnings]
    if task_id:
        lines += [f"{a} is due: sae dispatch {task_id} {a}" for a in added]
    else:
        lines += [f"Added {a}: dispatch it." for a in added]
    return "\n".join(lines)


def cmd_check(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task, write=False) as task:  # [READ-ONLY-COMMANDS]
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        errors, warnings, due = run_check(task, write=False)
        text = check_text(errors, warnings, due, task.id) or "Check passed: no errors, no warnings."
        if errors:
            text += f"\n{len(errors)} error(s)."
        emit(args, text, {"errors": errors, "warnings": warnings, "due": due})
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
            integration_round = target["kind"] == "review" and target.get("target") == "integration"
            if args.kind != "implementation" or (target["kind"] not in WRITER_KINDS and not integration_round):
                fail(EXIT_USAGE, "--fix-of: a fix job is an implementation job that fixes a writer job, or the "
                                 "findings of an integration review round.")
            last = last_round(task, "integration")
            if integration_round and (args.fix_of != last or not requires_changes(target)):
                if requires_changes(task.jobs[last]):
                    fail(EXIT_USAGE, f"--fix-of {args.fix_of}: fix jobs answer the last integration review round. "
                                     f"Use: sae job add {task.id} {job_id} --kind implementation --fix-of {last} "
                                     f"--reason \"<finding>\"")
                fail(EXIT_USAGE, f"--fix-of {args.fix_of}: {last} does not say changes-required, so it needs no fix "
                                 f"jobs. Add an ordinary job: sae job add {task.id} {job_id} --kind implementation "
                                 f"--reason \"<why>\"")
            if target["merged"]:
                fail(EXIT_USAGE, f"{args.fix_of} is already merged; add a normal job instead.")
        if args.kind == "planning" and args.difficulty == "mechanical":
            fail(EXIT_USAGE, "Planning is never mechanical: use --difficulty normal or hard.")
        require_reason(task, args.reason)
        needs = parse_needs(args.needs)
        difficulty = args.difficulty or (task_difficulty(task.settings) if args.kind == "planning" else "normal")
        args.difficulty = difficulty
        job = new_job(args.kind, needs, difficulty, review=args.review, final=args.final, fix_of=args.fix_of)
        task.jobs[job_id] = job
        notes = []
        fixed = task.jobs.get(args.fix_of) if args.fix_of else None
        if fixed is not None and fixed["kind"] in WRITER_KINDS and fixed["status"] == "parked" and fixed["review_rounds"]:
            # The owner chose another fix round: the target's work is done, its next review follows the fix.
            fixed["status"] = "done"
            task.touch(fixed)
            notes.append(f"{args.fix_of} is no longer parked: its next review round follows {job_id}.")
        if args.review and not {"selected-jobs", "all-jobs"} & set(task.settings["review"]["points"]):
            notes.append(wrap(f"warning: {job_id} is flagged for review, but job reviews are off "
                              "(review points have neither selected-jobs nor all-jobs)."))
        path = job_file(task, job_id)
        if not path.exists():
            name = "job-research.md" if args.kind == "research" else "job.md"
            text = template(name).replace("<JOB-ID>", job_id).replace("<TOPIC-ID>", job_id)
            write_atomic(path, text)
        task.event("job.added", job=job_id, kind=args.kind, needs=needs, difficulty=args.difficulty,
                   review=args.review, final=args.final, fix_of=args.fix_of, reason=args.reason)
        emit(args, "\n".join([wrap(f"Added {job_id} ({args.kind}, {args.difficulty}). Job file:"), f"  {path}"] + notes),
             {"job": job_id, "file": str(path), "notes": notes})
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
            if job["kind"] == "review" and job.get("target") in task.jobs:
                fail(EXIT_USAGE, f"{args.id} is a job review: it takes the difficulty of {job['target']}. "
                                 f"For an exception: sae job override {task.id} {job['target']} --review …")
            if job["kind"] in ("review", "planning") and args.difficulty == "mechanical":
                fail(EXIT_USAGE, f"{job['kind'].capitalize()} is never mechanical: use normal or hard.")
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


def cmd_job_override(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        if args.review:
            target = task.job(args.id)
            if target["kind"] == "review":
                fail(EXIT_USAGE, f"{args.id} is a review; name the job it reviews with --review, or drop --review.")
            key = f"REVIEW-{args.id}"
        elif args.id in task.jobs:
            key = override_key(task, args.id)
        elif planned_review_target(task, args.id) in TASK_TARGETS:
            key = args.id
        else:
            fail(EXIT_USAGE, f"No job {args.id} in task {task.id}. A planned review is REVIEW-SPEC, REVIEW-PLAN or "
                             f"REVIEW-INTEGRATION; the review of a job is <ID> --review.")
        covered = [i for i, j in task.jobs.items() if override_key(task, i) == key]
        busy = [i for i in covered if task.jobs[i]["status"] == "running"
                or (task.jobs[i]["kind"] != "review" and task.jobs[i]["status"] != "pending")]
        if busy:
            fail(EXIT_USAGE, f"{', '.join(busy)} is not pending; a running or finished job keeps its model.")
        overrides = task.info.setdefault("overrides", {})
        if args.clear:
            if args.harness or args.model or args.effort:
                fail(EXIT_USAGE, "--clear takes no --harness, --model or --effort.")
            old = overrides.pop(key, None)
            if old is None:
                emit(args, f"{key}: no override.", {"key": key, "override": None})
                return EXIT_OK
            if not overrides:
                del task.info["overrides"]
            task.event("override.cleared", job=key, harness=old.get("harness"), model=old.get("model"),
                       effort=old.get("effort"), reason=args.reason, by=changed_by())
            emit(args, f"{key}: override cleared; routing chooses again.", {"key": key, "override": None})
            return EXIT_OK
        if not (args.harness or args.model or args.effort):
            fail(EXIT_USAGE, "Give --harness, --model or --effort (or --clear).")
        override = {k: v for k, v in (("harness", args.harness), ("model", args.model), ("effort", args.effort)) if v}
        override["at"] = iso()
        if args.reason:
            override["reason"] = args.reason
        previous = overrides.get(key)
        overrides[key] = override
        probe = args.id if not args.review else (covered[0] if covered else key)
        try:
            res = resolve_model(task, probe, load_config(), exact=False)
        except SaeError as exc:
            if previous is None:
                overrides.pop(key)
            else:
                overrides[key] = previous
            fail(EXIT_USAGE, f"Override not set: {exc}")
        task.event("override.set", job=key, harness=override.get("harness"), model=override.get("model"),
                   effort=override.get("effort"), reason=args.reason, by=changed_by())
        emit(args, f"{key}: override {res['harness']} · {res['model']} · {res['effort']} (routing: "
                   + (f"{res['routed']['harness']} · {res['routed']['model_entry']} · {res['routed']['effort']})"
                      if res.get("routed") else "n/a)"),
             {"key": key, "override": override, "resolved": res})
    return EXIT_OK


def register_set(sub, command):
    """Add the `set` command to the parser."""
    p = command(sub, "set", "Change this task's settings (settings.json).",
                f"Keys: interaction ({'|'.join(INTERACTION_MODES)}); research, planning, execution, review-level\n"
                f"({'|'.join(LEVELS)}); review (comma list of {', '.join(REVIEW_POINTS)}; or off);\n"
                f"reviewer ({'|'.join(REVIEW_PROVIDERS)}; cross-harness: the harness that does not orchestrate);\n"
                "max-verify-failures (1-10; change it only when the user asks); task-difficulty (normal|hard: the\n"
                "planner and the spec, plan and integration reviews).\n"
                f"Routing keys (task level; inherit removes the task value): {ROUTING_KEYS_HELP}.\n"
                "Run it only on the user's word. The next dispatch uses the new values. Prints the settings card.",
                ["set claims-status execution=economy", "set claims-status review=spec,plan,selected-jobs,integration reviewer=cross-harness",
                 "set claims-status routing.codex.execution.max.hard=L4 tier.claude.L3=<model>:high"],
                [0, 1], cmd_set)
    p.add_argument("task")
    p.add_argument("pairs", nargs="+", metavar="key=value")


def register_approve(sub, command):
    """Add the `approve` command to the parser."""
    p = command(sub, "approve", "Record a gate approval: spec (shaping → planning) or plan.",
                "Runs check first; lint errors refuse. Refuses while REVIEW-SPEC (or REVIEW-PLAN) exists and is not\n"
                "collected; its verdict does not block. Plan approval also needs every planning and research job done.\n"
                "After plan approval: sae start <task>; another session resumes with --harness claude|codex.",
                ["approve claims-status spec", "approve claims-status plan"], [0, 1, 3], cmd_approve)
    p.add_argument("task")
    p.add_argument("gate", choices=("spec", "plan"))


def register_check(sub, command):
    """Add the `check` command to the parser."""
    p = command(sub, "check", "Lint the task and name a due spec or plan review. Read-only.",
                "In shaping: requirement IDs in specs.md and in the intent's ## Acceptance; after a clean check\n"
                "REVIEW-SPEC is due when spec is a review point. Later: the graph (unknown needs, cycles, job files\n"
                "and objectives, covers, requirement coverage, final jobs) and warnings (verify, scopes, hot files,\n"
                "brief length, riskiest assumptions, objective length); in planning REVIEW-PLAN is due after a clean\n"
                "check. A due review is listed by sae next and added by sae dispatch. Writes nothing.",
                ["check claims-status"], [0, 1, 3], cmd_check)
    p.add_argument("task")


def register_job(sub, command):
    """Add the `job` command group to the parser; returns the group parser."""
    job = sub.add_parser("job", help="Add, edit or remove a job of the graph.", parents=[],
                         description="Graph changes and per-job model overrides. sae job <add|edit|remove|override> --help.")
    job_sub = job.add_subparsers(dest="job_command", metavar="<add|edit|remove|override>", parser_class=Parser)
    p = command(job_sub, "add", "Register a job and scaffold jobs/<ID>.md.",
                f"Kinds: {', '.join(k for k in JOB_KINDS if k not in ('review', 'decision'))} (sae adds review jobs;\n"
                "decision jobs come from sae decision new). ID: UPPER-KEBAB. --needs: jobs that must be done (and\n"
                "merged, for writers) first. --review: review this job (selected-jobs). --final: the final validation.\n"
                "--fix-of <ID>: an implementation job that fixes a writer job in its workspace (after its job review),\n"
                "or answers a changes-required integration review round (an ordinary writer; when the round's fix\n"
                "jobs are merged, sae adds the next round). --reason: required during execution.",
                ["job add claims-status STATUS-API --kind implementation --needs STATUS-CONTRACT --difficulty hard --review",
                 'job add claims-status STATUS-API-FIX-1 --kind implementation --fix-of STATUS-API --reason "REVIEW-STATUS-API: changes required"',
                 'job add claims-status INTEGRATION-FIX-1 --kind implementation --fix-of REVIEW-INTEGRATION --reason "finding 1"'],
                [0, 1], cmd_job_add)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--kind", required=True, choices=[k for k in JOB_KINDS if k not in ("review", "decision")])
    p.add_argument("--needs", metavar="A,B")
    p.add_argument("--difficulty", choices=DIFFICULTIES,
                   help="default normal; a planning job takes the task difficulty and is never mechanical")
    p.add_argument("--review", action="store_true")
    p.add_argument("--final", action="store_true")
    p.add_argument("--fix-of", metavar="ID", help="the writer job this fix repairs (it works on that job's branch), "
                                               "or the integration review round whose findings it answers")
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
    p = command(job_sub, "override", "Run one job, or its review, on another harness, model or effort.",
                "Only on the user's word. <ID> is a job or a planned review (REVIEW-SPEC, REVIEW-PLAN,\n"
                "REVIEW-INTEGRATION); --review means the review of job <ID> (all its rounds). Any subset of --harness,\n"
                "--model and --effort; the rest comes from routing for the override's harness. The model must be in\n"
                "the harness's model list and accept the effort. Refused for a running or finished job. sae dispatch\n"
                "uses it and prints it as an override; --clear returns the job to routing.",
                ["job override claims-status STATUS-API --review --harness codex --effort high",
                 "job override claims-status STATUS-API --review --clear"], [0, 1, 2], cmd_job_override)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--review", action="store_true", help="the override is for the review of job <ID>")
    p.add_argument("--harness", choices=HARNESSES, help="the harness that runs it")
    p.add_argument("--model", help="a model from that harness's model list")
    p.add_argument("--effort", help="an effort that model accepts")
    p.add_argument("--clear", action="store_true", help="remove the override")
    p.add_argument("--reason", help="why (logged)")
    return job
