"""Exits from a fix loop: `sae job drop` ([JOB-DROP]), `sae accept-review` ([ACCEPT-INTEGRATION]),
the lines that changes-required messages print, and the final report's list of what was let go
([LET-GO-REPORT], [TRIAGE])."""

from __future__ import annotations

import re

from .common import EXIT_OK, EXIT_USAGE, WRITER_KINDS, changed_by, emit, fail, iso, read_text
from .gitutil import find_root
from .graph import fix_target, is_dropped, last_round, requires_changes, review_rounds
from .markdown import md_section, split_frontmatter, strip_html_comments
from .tasks import Task, open_task, result_file


# ------------------------------------------------------------- changes-required lines

def let_go_line(task: Task, review_id: str) -> str:
    """[TRIAGE]: the command that logs one finding the orchestrator sets aside."""
    return f'sae log {task.id} decision "<finding>: <reason>" --job {review_id} --let-go'


def accept_line(task: Task, review_id: str, target: str | None) -> str:
    """The command that accepts a changes-required round: a job review merges with
    `sae merge --accept-review`, an integration round is accepted with `sae accept-review`."""
    if target == "integration":
        return f'sae accept-review {task.id} {review_id} --reason "<why>"'
    return f'sae merge {task.id} {target} --accept-review "<why>"'


def changes_required_lines(task: Task, review_id: str, target: str, fix_command: str) -> list[str]:
    """The message of a changes-required round below the round limit: the lead line, a fix job
    with a fresh ID, the let-go line and the accept line (audit 2026-11-20, proposal 2)."""
    lead = review_id if target == "integration" else target
    after = " (sae adds the next round when it is merged)" if target == "integration" else ""
    return [f"{lead}: changes required. Triage first (execute.md, Loop step 3).",
            f"Fix job for the findings you keep{after}:", f"  {fix_command}",
            "Each finding you set aside, logged with its reason:", f"  {let_go_line(task, review_id)}",
            "Or accept when the mode lets you decide:", f"  {accept_line(task, review_id, target)}"]


# ------------------------------------------------------------------- sae job drop

def drop_group(task: Task, job_id: str) -> list[str]:
    """[JOB-DROP]: the job, every fix job that commits to its branch (also fixes of fixes), the
    INTEGRATE-<ID> job that would merge one of them, and the review rounds of each."""
    group = [job_id]
    grown = True
    while grown:
        grown = False
        for other, job in task.jobs.items():
            if other in group:
                continue
            if fix_target(task, other) in group or (job["kind"] == "integration" and job.get("target") in group):
                group.append(other)
                grown = True
    for writer in list(group):
        group += [r for r in review_rounds(task, writer) if r not in group]
    return group


def needs_command(task: Task, job_id: str, group: list[str], dropped: str) -> str:
    keep = ",".join(n for n in task.jobs[job_id]["needs"] if n not in group)
    return f'sae job edit {task.id} {job_id} --needs "{keep}" --reason "{dropped} is dropped"'


def cmd_job_drop(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job_id = args.id
        job = task.job(job_id)
        reason = (args.reason or "").strip()
        if not reason:
            fail(EXIT_USAGE, "--reason is required: the owner's reason to drop the job.")
        if job["kind"] not in WRITER_KINDS:
            fail(EXIT_USAGE, f"{job_id} is a {job['kind']} job; only writer jobs are dropped.")
        target = fix_target(task, job_id)
        if target:
            fail(EXIT_USAGE, f"{job_id} is a fix job of {target} and commits to its branch. Drop the group: "
                             f"sae job drop {task.id} {target} --reason \"<why>\"")
        if job["merged"]:
            fail(EXIT_USAGE, f"{job_id} is merged already; a drop cannot take it out of the task branch.")
        if is_dropped(job):
            fail(EXIT_USAGE, f"{job_id} is dropped already.")
        if job["status"] == "pending":
            fail(EXIT_USAGE, f"{job_id} is pending: it never ran. Remove it instead: "
                             f"sae job remove {task.id} {job_id} --reason \"<why>\"")
        if not task.uses_worktrees:
            where = "a task without git" if not task.info.get("git") else "a task without worktrees"
            fail(EXIT_USAGE, f"{job_id} cannot be dropped: in {where} its changes are already in the shared "
                             "checkout. Undo them with a new job instead.")
        group = drop_group(task, job_id)
        running = [i for i in group if task.jobs[i]["status"] == "running"]
        if running:
            fail(EXIT_USAGE, f"{', '.join(running)} is running. Collect it first: sae collect {task.id} {running[0]}")
        needing = [i for i, j in task.jobs.items() if i not in group and set(j["needs"]) & set(group)
                   and not (j["kind"] == "review" and j.get("target") == "integration")]
        if needing:
            fail(EXIT_USAGE, "\n".join([f"{', '.join(needing)} need{'s' if len(needing) == 1 else ''} a job of the "
                                        f"group of {job_id}. Change the needs first:"]
                                       + [f"  {needs_command(task, i, group, job_id)}" for i in needing]))
        was = {}
        for member in group:
            other = task.jobs[member]
            was[member] = other["status"]
            other["drop"] = {"group": job_id, "reason": reason, "was": other["status"], "at": iso()}
            other["status"] = "dropped"
            task.touch(other)
        task.event("job.dropped", job=job_id, group=group, was=was, reason=reason, by=changed_by())
        task.event("decision", **{"class": "consequential", "by": "human", "job": job_id, "dropped": group,
                                  "summary": f"drop {job_id}" + (f" with {', '.join(group[1:])}" if group[1:] else "")
                                             + f": {reason}"})
        out = [f"Dropped {', '.join(group)}: {reason}",
               "Dropped jobs never merge; their branches and result files stay."]
        from .reviews import materialize_integration_review  # late import: reviews imports this module
        materialize_integration_review(task, out)
        out.append(f"Next: sae next {task.id}")
        emit(args, "\n".join(out), {"job": job_id, "group": group, "was": was, "reason": reason, "messages": out})
    return EXIT_OK


def register_job_drop(job_sub, command) -> None:
    """Add `sae job drop` to the `job` command group."""
    p = command(job_sub, "drop", "Drop an unmerged writer job and its fix chain, on the owner's word.",
                "Only on the owner's word. <ID> is a parked, failed or done writer job that is not merged. Its group\n"
                "is dropped with it: every fix job that commits to its branch, an INTEGRATE-<ID> job that would\n"
                "merge it, and their review rounds. Dropped is final: the jobs never merge (sae merge, collect and\n"
                "finish refuse them), and the integration review, the final validation and the finish gates\n"
                "ignore them. Branches and result files stay. Refuses before any change when: a fix job is named\n"
                "alone (drop its target), a group member is running, the task has no worktrees or no git (the\n"
                "changes are already in the shared checkout), or a job outside the group needs a member (it\n"
                "prints the sae job edit --needs call to run first). Logs a decision; the final report lists\n"
                "the dropped jobs.",
                ['job drop claims-status STATUS-API --reason "owner: the cache approach is wrong; rebuild it"'],
                [0, 1], cmd_job_drop)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--reason", required=True, help="the owner's reason; logged and listed in the final report")


# --------------------------------------------------------------- sae accept-review

def cmd_accept_review(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        review_id = args.id
        review = task.job(review_id)
        reason = (args.reason or "").strip()
        if not reason:
            fail(EXIT_USAGE, f"--reason is required: sae accept-review {task.id} {review_id} --reason \"<why>\"")
        target = review.get("target")
        if review["kind"] != "review":
            fail(EXIT_USAGE, f"{review_id} is a {review['kind']} job, not a review round.")
        if target in task.jobs:
            fail(EXIT_USAGE, f"{review_id} reviews the job {target}. Accept a job review with:\n"
                             f"  sae merge {task.id} {target} --accept-review \"<why>\"")
        if target != "integration":
            fail(EXIT_USAGE, f"{review_id} reviews the {target}; its verdict does not block, so there is nothing "
                             "to accept.")
        last = last_round(task, "integration")
        if review_id != last:
            fail(EXIT_USAGE, f"{review_id} is not the last integration round; {last} is. Accept that one:\n"
                             f"  sae accept-review {task.id} {last} --reason \"<why>\"")
        if not requires_changes(review):
            state = f"verdict {review.get('verdict')}" if review["status"] == "done" else review["status"]
            fail(EXIT_USAGE, f"{review_id} is {state}; only a changes-required round is accepted.")
        if review.get("accepted"):
            fail(EXIT_USAGE, f"{review_id} is accepted already: {review['accepted'].get('reason')}")
        review["accepted"] = {"reason": reason, "at": iso(), "by": changed_by()}
        task.touch(review)
        task.event("decision", **{"class": "consequential", "by": "agent", "job": review_id,
                                  "accepted_review": review_id, "reason": reason,
                                  "summary": f"accept {review_id} despite changes-required: {reason}"})
        out = [f"{review_id} accepted: {reason}",
               "The task continues as after a pass: the final validation and sae finish need no --override "
               "for this round. The final report lists its findings with this reason."]
        from .reviews import materialize_integration_review  # late import: reviews imports this module
        materialize_integration_review(task, out)
        out.append(f"Next: sae next {task.id}")
        emit(args, "\n".join(out), {"review": review_id, "reason": reason, "messages": out})
    return EXIT_OK


def register_accept_review(sub, command) -> None:
    """Add the `accept-review` command to the parser."""
    p = command(sub, "accept-review", "Accept the last changes-required integration review round with a reason.",
                "When the mode lets you decide, or on the owner's word at the round limit. The integration gate, the\n"
                "final validation and sae finish then proceed as after a pass, without --override; a park at the\n"
                "round limit ends. Logs a decision; the final report lists every finding of the round with this\n"
                "reason. A job review is accepted with sae merge <task> <ID> --accept-review \"<why>\" instead.",
                ['accept-review claims-status REVIEW-INTEGRATION-2 --reason "remaining findings are beyond the '
                 'Project Stakes"'], [0, 1], cmd_accept_review)
    p.add_argument("task")
    p.add_argument("id", metavar="REVIEW-ID", help="the last integration review round")
    p.add_argument("--reason", required=True, help="why the round is accepted; logged and listed in the final report")


# ------------------------------------------------------------------ final report

FINDING_HEADING_RE = re.compile(r"^###\s+(?:(\d+)[.)]\s*)?(.+?)(?:\s+[—–-]+\s+(?:blocking|major|minor)\b.*)?\s*$",
                                re.I)


def review_findings(text: str | None) -> list[tuple[str | None, str]]:
    """(number, title) of each `### <n>. <title> — <severity>` under `## Findings` of a review."""
    section = md_section(split_frontmatter(text or "")[1], "Findings") or ""
    found = []
    for line in strip_html_comments(section).splitlines():
        m = FINDING_HEADING_RE.match(line.strip())
        if m and not m.group(2).startswith("<"):
            found.append((m.group(1), m.group(2).strip()))
    return found


def logged_alone(let_go: list[dict], review_id: str, number: str | None, title: str) -> bool:
    """A finding of an accepted review that a --let-go decision already names: by its title at the
    start of the summary, or by its number ("2", "#2", "finding 2")."""
    for event in let_go:
        if event.get("job") != review_id:
            continue
        summary = str(event.get("summary") or "").strip().lower()
        head = summary.split(":", 1)[0].strip()
        if summary.startswith(title.lower()) or (number and re.fullmatch(rf"(finding\s*)?#?{number}\.?", head)):
            return True
    return False


def let_go_lines(task: Task, events: list[dict]) -> list[str]:
    """[LET-GO-REPORT]: every finding let go, with its reason: each --let-go decision, then each
    finding of an accepted review or round that no --let-go decision named."""
    decisions = [e for e in events if e["type"] == "decision"]
    let_go = [e for e in decisions if e.get("let_go")]
    lines = [f"- {e.get('job')}: {e.get('summary')}" for e in let_go]
    for event in decisions:
        review_id = event.get("accepted_review")
        if not review_id:
            continue
        reason = event.get("reason") or event.get("summary")
        text = read_text(result_file(task, review_id)) if review_id in task.jobs else None
        findings = review_findings(text)
        if not findings:
            lines.append(f"- {review_id}: every finding (no finding titles in its review file) — accepted: {reason}")
        lines += [f"- {review_id}: {title} — accepted: {reason}" for number, title in findings
                  if not logged_alone(let_go, review_id, number, title)]
    return lines


def fix_loop_report_lines(task: Task, events: list[dict]) -> list[str]:
    """The final report's sections about the fix loops: findings let go, accepted integration
    rounds and dropped jobs."""
    lines: list[str] = []
    let_go = let_go_lines(task, events)
    if let_go:
        lines += ["", "## Findings let go"] + let_go
    accepted = [(i, j["accepted"]) for i, j in task.jobs.items() if j["kind"] == "review" and j.get("accepted")]
    if accepted:
        lines += ["", "## Accepted integration rounds"] + [f"- {i}: {a.get('reason')}" for i, a in accepted]
    drops = [e for e in events if e["type"] == "job.dropped"]
    if drops:
        lines += ["", "## Dropped jobs"]
        for event in drops:
            others = [m for m in event.get("group") or [] if m != event["job"]]
            lines.append(f"- {event['job']}" + (f" (with {', '.join(others)})" if others else "")
                         + f": {event.get('reason')}")
        lines.append("  Their branches stay; nothing of them was merged.")
    return lines
