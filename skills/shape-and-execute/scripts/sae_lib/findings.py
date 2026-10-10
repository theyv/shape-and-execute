"""Commands finding new|close, decision new and log."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .common import (
    CONFIDENCES,
    DECISION_CLASSES,
    DIFFICULTIES,
    EXIT_OK,
    EXIT_USAGE,
    FINDING_TYPES,
    PROVENANCES,
    Parser,
    emit,
    fail,
    file_stamp,
    now,
    read_text,
    rel,
    slugify,
    warn,
    write_atomic,
)
from .gitutil import find_root
from .markdown import first_heading, split_frontmatter
from .tasks import (
    append_event_to,
    ensure_tasks_folder,
    job_file,
    new_job,
    open_task,
    resolve_task,
    result_file,
    tasks_dir,
    template,
)
from .viewer import render_viewer_safely


def cmd_decision_new(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        source = task.job(args.from_job)
        if source["status"] != "parked":
            fail(EXIT_USAGE, f"{args.from_job} is {source['status']}; decision jobs answer parked jobs.")
        n = 1 + sum(1 for i in task.jobs if i.startswith(f"DECISION-{args.from_job}-"))
        job_id = f"DECISION-{args.from_job}-{n}"
        task.jobs[job_id] = new_job("decision", [], args.difficulty, target=args.from_job)
        result = rel(result_file(task, args.from_job), task.dir)
        write_atomic(job_file(task, job_id),
                     f"---\nid: {job_id}\n---\n\n# {job_id}: decision for {args.from_job}\n\n## Objective\n"
                     f"Answer the decision request of {args.from_job}.\n\n## Inputs\n"
                     f"- The section \"Decision request\" of {result}.\n")
        task.event("job.added", job=job_id, kind="decision", needs=[], difficulty=args.difficulty,
                   target=args.from_job, reason=f"decision for {args.from_job}")
        emit(args, f"Added {job_id}. Dispatch it: sae dispatch {task.id} {job_id}", {"job": job_id})
    return EXIT_OK


def cmd_log(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if args.job:
            task.job(args.job)
        if args.type == "decision":
            if args.decision_class and args.decision_class not in DECISION_CLASSES:
                fail(EXIT_USAGE, f"--class must be one of {', '.join(DECISION_CLASSES)}")
            fields = {"class": args.decision_class, "by": args.by, "summary": args.summary, "job": args.job,
                      "file": args.file}
            task.event("decision", **{k: v for k, v in fields.items() if v is not None})
        elif args.type == "amendment":
            if not args.amend_id:
                fail(EXIT_USAGE, "An amendment needs --id <AMEND-ID> (the ID under ## Amendments in specs.md).")
            spec = read_text(task.dir / "specs.md", "")
            if f"[{args.amend_id}]" not in spec:
                warn(f"[{args.amend_id}] is not in specs.md; write the amendment text there first.")
            task.event("amendment", id=args.amend_id, by=args.by, summary=args.summary)
        else:
            task.event("note", text=args.summary, **({"job": args.job} if args.job else {}))
        emit(args, f"Logged {args.type}.", {"type": args.type})
    return EXIT_OK


def cmd_finding_new(args) -> int:
    root, _ = find_root()
    source_task, source = None, None
    if args.source:
        task_ref, _, job_id = args.source.partition("/")
        source_task = resolve_task(root, task_ref)
        source = f"{source_task}/{job_id}" if job_id else source_task
    ensure_tasks_folder(root)
    path = tasks_dir(root) / "findings" / f"{file_stamp()}--{slugify(args.title)}.md"
    if path.exists():
        path = path.with_name(f"{path.stem}-2.md")
    paths = [p.strip() for p in (args.paths or "").split(",") if p.strip()]
    body = split_frontmatter(template("finding.md"))[1].replace("<title>", args.title)
    front = (f"---\ntype: {args.type}\nconfidence: {args.confidence}\n"
             + (f"source: {source}\n" if source else "")
             + f"paths: [{', '.join(paths)}]\n---\n")
    write_atomic(path, front + body)
    if source_task:
        append_event_to(root, source_task, "finding.created", finding=rel(path, root))
    else:
        render_viewer_safely(root, [])
    emit(args, f"Finding: {path}", {"file": str(path)})
    return EXIT_OK


CLOSE_OUTCOME_RE = re.compile(r"^(fixed in \S+|moved to backlog/\S+|rejected: .+|duplicate of \S+)$")


def cmd_finding_close(args) -> int:
    root, _ = find_root()
    path = Path(args.file)
    if not path.is_absolute():
        candidates = [Path.cwd() / path, root / path, tasks_dir(root) / "findings" / path.name]
        path = next((c for c in candidates if c.exists()), candidates[0])
    text = read_text(path)
    if text is None:
        fail(EXIT_USAGE, f"No finding at {args.file}.")
    if not CLOSE_OUTCOME_RE.match(args.outcome):
        fail(EXIT_USAGE, 'Outcome must be "fixed in <task-id>", "moved to backlog/<file>", '
                         '"rejected: <reason>" or "duplicate of <finding>".')
    title = first_heading(split_frontmatter(text)[1]) or path.stem
    closed = tasks_dir(root) / "findings" / "closed.md"
    if not closed.exists():
        write_atomic(closed, "# Closed findings\n\n")
    with closed.open("a", encoding="utf-8") as handle:
        handle.write(f"- {now().date().isoformat()} · {path.stem} · {title} · {args.outcome}\n")
    os.remove(path)
    render_viewer_safely(root, [])
    emit(args, f"Closed {path.stem}: {args.outcome}", {"finding": path.stem, "outcome": args.outcome})
    return EXIT_OK


def register_decision(sub, command):
    """Add the `decision` command group to the parser; returns the group parser."""
    decision = sub.add_parser("decision", help="Create a decision job for a parked job.",
                              description="sae decision new --help for details.")
    decision_sub = decision.add_subparsers(dest="decision_command", metavar="<new>", parser_class=Parser)
    p = command(decision_sub, "new", "Add DECISION-<ID>-<n> for a parked job; prints the new ID.",
                "Its job file points to the ## Decision request section of the parked result.",
                ["decision new claims-status --from STATUS-API"], [0, 1], cmd_decision_new)
    p.add_argument("task")
    p.add_argument("--from", dest="from_job", required=True, metavar="ID")
    p.add_argument("--difficulty", choices=DIFFICULTIES, default="normal")
    return decision


def register_log(sub, command):
    """Add the `log` command to the parser."""
    p = command(sub, "log", "Record a decision, an amendment or a note.",
                "Write an amendment into specs.md under ## Amendments first, then log it with its --id.\n"
                "--by: human | agent | joint (default agent; agent entries appear in the final report).",
                ['log claims-status decision "Cache status for 60 s" --by agent --class open-tradeoff --job STATUS-API',
                 'log claims-status amendment "Drop CSV export" --id AMEND-1 --by human'], [0, 1], cmd_log)
    p.add_argument("task")
    p.add_argument("type", choices=("decision", "amendment", "note"))
    p.add_argument("summary")
    p.add_argument("--job", metavar="ID")
    p.add_argument("--by", choices=PROVENANCES, default="agent")
    p.add_argument("--class", dest="decision_class", choices=DECISION_CLASSES)
    p.add_argument("--id", dest="amend_id", metavar="AMEND-ID")
    p.add_argument("--file")


def register_finding(sub, command):
    """Add the `finding` command group to the parser; returns the group parser."""
    finding = sub.add_parser("finding", help="File or close a finding (out-of-scope observations).",
                             description="sae finding <new|close> --help for details.")
    finding_sub = finding.add_subparsers(dest="finding_command", metavar="<new|close>", parser_class=Parser)
    p = command(finding_sub, "new", "File a finding in .tasks/findings/; prints its path.",
                "Types: friction (the repository made agent work hard), defect (something looks broken), follow-up\n"
                "(work worth doing outside the task). Fill the printed file. Never fix it on the side.",
                ['finding new "Status lookup is slow" --type defect --confidence medium --source claims-status/STATUS-API --paths src/status'],
                [0, 1], cmd_finding_new)
    p.add_argument("title")
    p.add_argument("--type", required=True, choices=FINDING_TYPES)
    p.add_argument("--confidence", required=True, choices=CONFIDENCES)
    p.add_argument("--source", metavar="TASK/JOB")
    p.add_argument("--paths", metavar="A,B")
    p = command(finding_sub, "close", "Close a finding: delete its file, log a line in findings/closed.md.",
                'Outcome: "fixed in <task-id>", "moved to backlog/<file>", "rejected: <reason>" or "duplicate of <finding>".',
                ['finding close .tasks/findings/2026-10-06-1512--slow-status-lookup.md --outcome "rejected: expected"'],
                [0, 1], cmd_finding_close)
    p.add_argument("file")
    p.add_argument("--outcome", required=True)
    return finding
