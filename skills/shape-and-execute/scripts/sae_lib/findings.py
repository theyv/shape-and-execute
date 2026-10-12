"""Commands finding new|close, decision new, log, adr and triage; the closed-findings rule and
the closing of the findings a job resolves."""

from __future__ import annotations

import datetime as dt
import os
import re
import shutil
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
    stamp_time,
    table,
    warn,
    write_atomic,
)
from .gitutil import find_root, git, git_ok, main_worktree
from .markdown import first_heading, split_frontmatter
from .tasks import (
    append_event_to,
    as_list,
    ensure_tasks_folder,
    job_file,
    job_meta,
    live_checkout,
    locate_tasks,
    new_job,
    open_task,
    resolve_task,
    result_file,
    task_copies,
    task_phase,
    tasks_dir,
    template,
)
from .viewer import remember_repo_safely, stamped_items


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


FINDING_TITLE_MAX = 80
FINDING_FORM = ('sae finding new "<short title>" --type friction|defect|follow-up '
                '--confidence high|medium|low --body "<what you saw>" [--source <task>/<JOB-ID>]')


def finding_body(args) -> str:
    """The observation from --body or --body-file; refuses a finding without one."""
    if len(args.title) > FINDING_TITLE_MAX:
        fail(EXIT_USAGE, f"The title has {len(args.title)} characters (max {FINDING_TITLE_MAX}). "
                         "Keep it short and move the text into --body.")
    body = args.body
    if args.body_file:
        body = read_text(Path(args.body_file))
        if body is None:
            fail(EXIT_USAGE, f"No file at {args.body_file}.")
    if not (body or "").strip():
        fail(EXIT_USAGE, f"A finding needs its observation. Expected form:\n  {FINDING_FORM}")
    return body.strip()


def cmd_finding_new(args) -> int:
    body_text = finding_body(args)
    root, _ = find_root()
    source_task, source, home = None, None, root
    if args.source:
        task_ref, _, job_id = args.source.partition("/")
        source_task = resolve_task(root, task_ref)
        source = f"{source_task}/{job_id}" if job_id else source_task
        home = live_checkout(root, source_task)  # finish commits it with the task record
    ensure_tasks_folder(home)
    path = tasks_dir(home) / "findings" / f"{file_stamp()}--{slugify(args.title)}.md"
    if path.exists():
        path = path.with_name(f"{path.stem}-2.md")
    paths = [p.strip() for p in (args.paths or "").split(",") if p.strip()]
    body = split_frontmatter(template("finding.md"))[1].replace("<title>", args.title)
    body = body.replace("<observation>", body_text)
    front = (f"---\ntype: {args.type}\nconfidence: {args.confidence}\n"
             + (f"source: {source}\n" if source else "")
             + f"paths: [{', '.join(paths)}]\n---\n")
    write_atomic(path, front + body)
    if source_task:
        append_event_to(root, source_task, "finding.created", finding=rel(path, home))
    else:
        remember_repo_safely(root)
    emit(args, f"Finding: {path}", {"file": str(path)})
    return EXIT_OK


CLOSE_OUTCOME_RE = re.compile(r"^(fixed in \S+(?: by \S+)?|moved to backlog/\S+|rejected: .+|duplicate of \S+)$")


def fixed_outcome(task_id: str, job_id: str) -> str:
    """The job form of the outcome ([RESOLVES-CLOSE]): `fixed in <task-id> by <JOB-ID>`."""
    return f"fixed in {task_id} by {job_id}"


def cmd_finding_close(args) -> int:
    root, _ = find_root()
    path = Path(args.file)
    if not path.is_absolute():
        candidates = [Path.cwd() / path, root / path, tasks_dir(root) / "findings" / path.name]
        path = next((c for c in candidates if c.exists()), candidates[0])
    if read_text(path) is None:
        fail(EXIT_USAGE, f"No finding at {args.file}.")
    if not CLOSE_OUTCOME_RE.match(args.outcome):
        fail(EXIT_USAGE, 'Outcome must be "fixed in <task-id>", "fixed in <task-id> by <JOB-ID>", '
                         '"moved to backlog/<file>", "rejected: <reason>" or "duplicate of <finding>".')
    close_finding(root, path, args.outcome)
    remember_repo_safely(root)
    emit(args, f"Closed {path.stem}: {args.outcome}", {"finding": path.stem, "outcome": args.outcome})
    return EXIT_OK


# ---- closing findings ([RESOLVES-CLOSE], [CLOSED-VISIBLE], [RULE-ONE-CLOSE]) ----------------

RESOLVING_KINDS = ("implementation", "integration", "validation")  # [RESOLVES-FIELD]


def finding_stem(entry) -> str:
    """A `resolves`/`resolved` entry or a finding path → its file stem (no folder, no `.md`)."""
    name = Path(str(entry).strip()).name
    return name[:-3] if name.endswith(".md") else name


def close_finding(checkout: Path, path: Path, outcome: str, remove: bool = True) -> str:
    """The one close path of `sae finding close` and of a resolving job: appends the line
    `- <date> · <stem> · <title> · <outcome>` to `closed.md` of `checkout` and deletes the
    finding file (`remove=False` keeps a file that lies in another checkout). Returns the line."""
    title = first_heading(split_frontmatter(read_text(path, ""))[1]) or path.stem
    closed = tasks_dir(checkout) / "findings" / "closed.md"
    if not closed.exists():
        write_atomic(closed, "# Closed findings\n\n")
    line = f"- {now().date().isoformat()} · {path.stem} · {title} · {outcome}"
    with closed.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    if remove and path.exists():
        os.remove(path)
    return line


def finding_checkouts(root: Path) -> list[Path]:
    """[CLOSED-VISIBLE]: the checkouts whose `closed.md` counts: `root`, the home checkout (the
    main worktree) and the checkout of every task that is not abandoned (its task worktree while
    it runs, and after `finish` until the owner merges it). Job worktrees do not count: their
    work is not merged. Without git: `root` only."""
    if not git_ok(root, "rev-parse", "--git-dir"):
        return [root]
    candidates = [root, main_worktree(root)]
    candidates += [c.checkout for c in task_copies(root) if task_phase(c) != "abandoned"]
    found: dict[Path, Path] = {}
    for checkout in candidates:
        found.setdefault(checkout.resolve(), checkout)
    return list(found.values())


def closed_lines(root: Path) -> dict[str, str]:
    """Finding stem → its line in `closed.md`, from every checkout of `finding_checkouts`."""
    lines: dict[str, str] = {}
    for checkout in finding_checkouts(root):
        for line in read_text(tasks_dir(checkout) / "findings" / "closed.md", "").splitlines():
            parts = line.lstrip("-* ").split(" · ")
            if line.lstrip().startswith(("-", "*")) and len(parts) >= 2:
                lines.setdefault(parts[1].strip(), line)
    return lines


def closed_text(root: Path) -> str:
    """`closed.md` of `root`, plus the lines that only other counting checkouts hold."""
    text = read_text(tasks_dir(root) / "findings" / "closed.md", "")
    extra = [line for line in closed_lines(root).values() if line not in text]
    if extra:
        text = (text or "# Closed findings\n\n") + ("" if not text or text.endswith("\n") else "\n")
        text += "\n".join(extra) + "\n"
    return text


def open_findings(root: Path) -> list[Path]:
    """The finding files of `root` that count as open: not listed in any counting `closed.md`
    ([CLOSED-VISIBLE]). `sae triage`, `sae status` and the viewer use this rule."""
    closed = closed_lines(root)
    return [p for p in stamped_items(tasks_dir(root) / "findings") if p.stem not in closed]


def finding_file(root: Path, stem: str) -> Path | None:
    """The file of an open finding in any counting checkout, `root` first."""
    for checkout in finding_checkouts(root):
        path = tasks_dir(checkout) / "findings" / f"{stem}.md"
        if path.is_file():
            return path
    return None


def resolves_errors(task, job_id: str, kind: str, meta: dict) -> list[str]:
    """[RESOLVES-FIELD] for `sae check`: `resolves` only on resolving kinds; each entry an open
    finding file or a line of `closed.md`."""
    entries = [str(e) for e in as_list(meta.get("resolves"))]
    if not entries:
        return []
    if kind not in RESOLVING_KINDS:
        return [f"{job_id}: resolves on a {kind} job; only {', '.join(RESOLVING_KINDS)} jobs resolve findings"]
    closed = closed_lines(task.root)
    return [f"{job_id}: resolves {entry}, which is neither an open finding in .tasks/findings/ nor in closed.md"
            for entry in entries
            if finding_stem(entry) not in closed and finding_file(task.root, finding_stem(entry)) is None]


def resolution(task, job_id: str) -> tuple[list[str], list[str], list[str]]:
    """(to close, stays open, ignored) of a job: `resolves` ∩ `resolved`, `resolves` without
    `resolved`, `resolved` without `resolves`. Stems, in the order of the files."""
    resolves = [finding_stem(e) for e in as_list(job_meta(task, job_id).get("resolves"))]
    if task.jobs[job_id]["kind"] not in RESOLVING_KINDS:
        resolves = []
    result = split_frontmatter(read_text(result_file(task, job_id), ""))[0]
    resolved = [finding_stem(e) for e in as_list(result.get("resolved"))]
    return ([s for s in resolves if s in resolved], [s for s in resolves if s not in resolved],
            [s for s in resolved if s not in resolves])


def resolution_notes(task, job_id: str) -> list[str]:
    """Collect output of a done job: the findings that stay open, the `resolved` entries ignored."""
    _, stays, ignored = resolution(task, job_id)
    notes = [f"Finding stays open: {s} ({job_id} resolves it, its result does not list it as resolved)."
             for s in stays]
    notes += [f"Ignored: {s} is in the resolved list of {job_id}, not in its resolves." for s in ignored]
    return notes


def close_resolved(task, job_ids: list[str], out: list[str]) -> list[str]:
    """[RESOLVES-CLOSE]: closes the findings that the succeeded jobs `job_ids` resolved (a merged
    fix group closes the findings of every member, [EDGE-FIX-GROUP]). A finding already in a
    counting `closed.md` is named and left alone ([RULE-ONE-CLOSE], [EDGE-RESOLVES-CLOSED]). The
    closure lands in the task's checkout, and with git as one commit on the task branch; the
    home checkout's branch never changes. Returns the closed stems."""
    root = task.root
    is_git = bool(task.info.get("git"))
    closed_now: list[str] = []
    closers: list[str] = []
    commit_paths: list[str] = []
    closed = closed_lines(root)
    for job_id in job_ids:
        to_close = resolution(task, job_id)[0]
        if not to_close:
            continue
        if is_git and task.info.get("branch") and \
                git(root, "branch", "--show-current", check=False) != task.info["branch"]:
            out.append(f"Findings not closed: {root} is not on {task.info['branch']}. Close them by hand: "
                       + ", ".join(to_close))
            continue
        for stem in to_close:
            if stem in closed:
                outcome = closed[stem].rsplit(" · ", 1)[-1].strip()
                out.append(f"Finding {stem} was closed already ({outcome}); {job_id} closes nothing more.")
                continue
            path = finding_file(root, stem)
            if path is None:
                out.append(f"Finding {stem} ({job_id} resolves it) has no file and no line in closed.md; "
                           "nothing to close.")
                continue
            local = path.parent == tasks_dir(root) / "findings"
            relative = rel(path, root)
            tracked = local and is_git and git_ok(root, "ls-files", "--error-unmatch", "--", relative)
            closed[stem] = close_finding(root, path, fixed_outcome(task.id, job_id), remove=local)
            if tracked:
                commit_paths.append(relative)
            closed_now.append(stem)
            closers += [job_id] if job_id not in closers else []
            task.event("finding.closed", finding=stem, job=job_id, outcome=fixed_outcome(task.id, job_id))
            out.append(f"Closed finding {stem}: {fixed_outcome(task.id, job_id)}.")
    if closed_now and is_git:
        closed_file = rel(tasks_dir(root) / "findings" / "closed.md", root)
        paths = [closed_file] + commit_paths
        git(root, "add", "--", *paths)
        git(root, "commit", "--quiet", "-m", f"{', '.join(closers)}: close resolved findings",
            "-m", f"Task: {task.id}", "--", *paths)
    return closed_now


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
                "(work worth doing outside the task). The title stays short (max 80 characters); --body or --body-file\n"
                "carries the observation. Fill the rest of the printed file. Never fix it on the side.",
                ['finding new "Status lookup is slow" --type defect --confidence medium '
                 '--body "GET /status takes 4 s on 100 claims" --source claims-status/STATUS-API --paths src/status'],
                [0, 1], cmd_finding_new)
    p.add_argument("title")
    p.add_argument("--type", required=True, choices=FINDING_TYPES)
    p.add_argument("--confidence", required=True, choices=CONFIDENCES)
    p.add_argument("--source", metavar="TASK/JOB")
    p.add_argument("--paths", metavar="A,B")
    given = p.add_mutually_exclusive_group()
    given.add_argument("--body", metavar="TEXT", help="the observation: what you saw (required, or --body-file)")
    given.add_argument("--body-file", metavar="PATH", help="read the observation from this file")
    p = command(finding_sub, "close", "Close a finding: delete its file, log a line in findings/closed.md.",
                'Outcome: "fixed in <task-id>", "fixed in <task-id> by <JOB-ID>" (the form sae writes when a job\n'
                'resolves it), "moved to backlog/<file>", "rejected: <reason>" or "duplicate of <finding>".',
                ['finding close .tasks/findings/2026-10-06-1512--slow-status-lookup.md --outcome "rejected: expected"'],
                [0, 1], cmd_finding_close)
    p.add_argument("file")
    p.add_argument("--outcome", required=True)
    register_adr(sub, command)
    register_triage(sub, command)
    return finding


# ---- decision-record drafts ([DECISION-DRAFTS], [DECISION-RECORD-FORMAT]) -------------------

ADR_FOLDERS = ("docs/decisions", "docs/adr", "doc/adr", "docs/architecture/decisions", "adr")
ADR_DEFAULT_FOLDER = "docs/decisions"
ADR_TYPES = ("architecture", "business")


def adr_dir(root: Path) -> Path:
    return tasks_dir(root) / "adr"


def _replace_front(text: str, key: str, value: str) -> str:
    """Set one frontmatter line `key: value`, keeping the rest of the file as written."""
    return re.sub(rf"(?m)^{re.escape(key)}:[^\n]*$", f"{key}: {value}", text, count=1)


def cmd_adr_new(args) -> int:
    root, _ = find_root()
    task_id = resolve_task(root, args.task)
    home = live_checkout(root, task_id)  # finish commits the draft with the task record
    folder = adr_dir(home)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{now().date().isoformat()}-{slugify(args.title)}"
    path, n = folder / f"{stem}.md", 2
    while path.exists():
        path, n = folder / f"{stem}-{n}.md", n + 1
    applies = [a.strip() for a in (args.applies_to or "").split(",") if a.strip()]
    text = (template("decision-record.md").replace("<title>", args.title)
            .replace("<date>", now().date().isoformat()).replace("<task-id>", task_id))
    text = _replace_front(text, "type", args.type)
    text = _replace_front(text, "applies-to", f"[{', '.join(applies)}]")
    write_atomic(path, text)
    append_event_to(root, task_id, "adr.created", file=rel(path, home))
    emit(args, f"Draft: {path}\nWrite the text; triage decides whether it becomes a record.", {"file": str(path)})
    return EXIT_OK


def find_draft(root: Path, ref: str) -> Path:
    path = Path(ref)
    candidates = [path] if path.is_absolute() else [Path.cwd() / path, root / path, adr_dir(root) / path.name,
                                                   adr_dir(root) / f"{path.name}.md"]
    found = next((c for c in candidates if c.is_file()), None)
    if found is None or found.name == "closed.md":
        fail(EXIT_USAGE, f"No decision-record draft at {ref}.")
    return found


def adr_target_folder(root: Path) -> Path:
    """The `adr_folder` pin of the repo profile, else an existing ADR folder, else docs/decisions/."""
    profile = read_text(tasks_dir(root) / "repo" / "profile.md")
    pin = split_frontmatter(profile)[0].get("adr_folder") if profile else None
    if pin:
        return root / str(pin).strip("/")
    existing = next((name for name in ADR_FOLDERS if (root / name).is_dir()), None)
    return root / (existing or ADR_DEFAULT_FOLDER)


def cmd_adr_accept(args) -> int:
    root, _ = find_root()
    draft = find_draft(root, args.draft)
    target_dir = adr_target_folder(root)
    first = not (target_dir.is_dir() and any(p.suffix == ".md" for p in target_dir.iterdir()))
    target = target_dir / draft.name
    if target.exists():
        fail(EXIT_USAGE, f"{rel(target, root)} already exists; rename the draft first.")
    target_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(target, _replace_front(read_text(draft), "status", "accepted"))
    os.remove(draft)
    remember_repo_safely(root)
    note = ("\nFirst record in this folder: propose one line for the agent instructions "
            "that points to it.") if first else ""
    emit(args, f"Accepted: {rel(target, root)} (uncommitted){note}",
         {"file": str(target), "first": first})
    return EXIT_OK


def cmd_adr_reject(args) -> int:
    root, _ = find_root()
    draft = find_draft(root, args.draft)
    meta = split_frontmatter(read_text(draft))[0]
    title = meta.get("title") or draft.stem
    # Absolute draft paths may point into the live task worktree from the home checkout.
    if draft.parent.name == "adr" and draft.parent.parent.name == ".tasks":
        root = draft.resolve().parents[2]
    closed = adr_dir(root) / "closed.md"
    if not closed.exists():
        write_atomic(closed, "# Closed decision-record drafts\n\n")
    with closed.open("a", encoding="utf-8") as handle:
        handle.write(f"- {now().date().isoformat()} · {draft.stem} · {title} · rejected: {args.reason}\n")
    attributes = tasks_dir(root) / ".gitattributes"
    known = read_text(attributes, "")
    if "adr/closed.md" not in known:
        write_atomic(attributes, known + ("" if not known or known.endswith("\n") else "\n")
                     + "adr/closed.md merge=union\n")
    os.remove(draft)
    if meta.get("source") in locate_tasks(root):
        append_event_to(root, str(meta["source"]), "adr.rejected", file=rel(draft, root),
                        closed=rel(closed, root), reason=args.reason)
    remember_repo_safely(root)
    emit(args, f"Rejected {draft.stem}: {args.reason}", {"draft": draft.stem, "reason": args.reason})
    return EXIT_OK


def register_adr(sub, command):
    """Add the `adr` command group to the parser."""
    adr = sub.add_parser("adr", help="Draft, accept or reject decision records.",
                         description="sae adr <new|accept|reject> --help for details.")
    adr_sub = adr.add_subparsers(dest="adr_command", metavar="<new|accept|reject>", parser_class=Parser)
    p = command(adr_sub, "new", "Create a decision-record draft in .tasks/adr/; prints its path.",
                "Status proposed, source the task. Draft only durable decisions a later agent could not\n"
                "rebuild from the code. Fill the printed file. Never blocks a run.",
                ['adr new claims-status "Status is cached for 60 s" --type architecture --applies-to src/status,StatusCache'],
                [0, 1], cmd_adr_new)
    p.add_argument("task")
    p.add_argument("title", help="short title of the decision")
    p.add_argument("--type", required=True, choices=ADR_TYPES, help="architecture | business")
    p.add_argument("--applies-to", metavar="A,B", help="comma list of paths and code names the decision governs")
    p = command(adr_sub, "accept", "Accept a draft: status accepted, moved into the ADR folder.",
                "Folder: adr_folder in .tasks/repo/profile.md, else an existing ADR folder, else\n"
                "docs/decisions/. Leaves the change uncommitted for the owner.",
                ["adr accept .tasks/adr/2026-10-10-status-is-cached-for-60-s.md"], [0, 1], cmd_adr_accept)
    p.add_argument("draft", help="path or file name of the draft")
    p = command(adr_sub, "reject", "Reject a draft: delete it, log a line in adr/closed.md.",
                "", ['adr reject 2026-10-10-status-is-cached-for-60-s.md --reason "visible in the code"'],
                [0, 1], cmd_adr_reject)
    p.add_argument("draft", help="path or file name of the draft")
    p.add_argument("--reason", required=True, help="why the draft is rejected")
    adr.set_defaults(func=lambda args: (adr.print_help(), EXIT_USAGE)[1])


# ---- triage counts ([TRIAGE-TWO-QUEUES]) ----------------------------------------------------

def _days_text(when: dt.date | None) -> str:
    if when is None:
        return "-"
    days = (now().date() - when).days
    return f"{days} day" if days == 1 else f"{days} days"


def _draft_date(path: Path) -> dt.date | None:
    value = split_frontmatter(read_text(path, ""))[0].get("date")
    for candidate in (str(value or ""), path.name[:10]):
        try:
            return dt.date.fromisoformat(candidate[:10])
        except ValueError:
            continue
    return None


def triage_counts(root: Path) -> list[dict]:
    queues = {t: [] for t in FINDING_TYPES}
    for path in open_findings(root):
        kind = split_frontmatter(read_text(path, ""))[0].get("type")
        stamp = stamp_time(path.name)
        queues.setdefault(str(kind), []).append(dt.date.fromisoformat(stamp[:10]) if stamp else None)
    drafts = [_draft_date(p) for p in sorted(adr_dir(root).glob("*.md")) if p.name != "closed.md"] \
        if adr_dir(root).is_dir() else []
    queues["decision drafts"] = drafts
    rows = []
    for name, dates in queues.items():
        known = [d for d in dates if d]
        rows.append({"queue": name, "open": len(dates), "oldest": min(known).isoformat() if known else None,
                     "age": _days_text(min(known)) if known else "-"})
    return rows


def cmd_triage(args) -> int:
    root, _ = find_root()
    rows = triage_counts(root)
    lines = [["Queue", "Open", "Oldest"]] + [[r["queue"], str(r["open"]), r["age"]] for r in rows]
    emit(args, table(lines, indent=""), {"queues": rows})
    return EXIT_OK


def register_triage(sub, command):
    """Add the read-only `triage` command."""
    command(sub, "triage", "Print the triage counts: findings by type and decision drafts.",
            "Read-only. Then pick one queue: findings or decision drafts. A finding listed in closed.md of the\n"
            "home checkout or of a task's worktree counts as closed.", ["triage"], [0], cmd_triage)
