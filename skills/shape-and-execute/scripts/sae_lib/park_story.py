"""Guidance in a fix loop: the approach check near the round limit ([APPROACH-CHECK]), the
Approach proposal of a fix result ([FIX-WORKER]) and the story of a park at the round limit
([PARK-STORY]). Everything here reads the task's files; only `mark_*` write, and only the
writing commands call them (dispatch, collect)."""

from __future__ import annotations

import re
from pathlib import Path

from .config import max_review_rounds
from .fix_loop import EXECUTE_MD, FINDING_HEADING_RE, accept_line, close_anyway_command, fix_job_command
from .graph import fix_target, integration_parked, requires_changes, review_rounds
from .markdown import has_content, md_section, split_frontmatter, strip_html_comments
from .tasks import Task, job_file, result_file

# Audit 2026-11-20, proposal 2 (owner accepted): the opening of every park message at the round
# limit and of every story, for a parked job and for the parked task.
PARK_OPENING = ("Parked at the round limit: the choice is the user's, in every mode. Relay the story with your "
                "recommendation and its reason, and run an option only after the user answers.")
# Audit 2026-11-20, proposal 3: `sae collect` of a done result with an Approach proposal.
APPROACH_PROPOSAL_COLLECT = ("Approach proposal in {path}: read that section; it is a decision "
                             f"({EXECUTE_MD}, Decision flow).")
INTEGRATION = "integration"
INTEGRATION_LABEL = "REVIEW-INTEGRATION"  # the target name in the approach paragraph of an integration fix


# ------------------------------------------------------------------- fix rounds

def fix_key(task: Task, fix_id: str) -> str | None:
    """The target whose review rounds a fix job answers: the writer job it repairs, or
    `integration` for a fix of an integration review round; None for any other job."""
    fix_of = task.jobs[fix_id].get("fix_of")
    if not fix_of or fix_of not in task.jobs:
        return None
    if task.jobs[fix_of]["kind"] == "review" and task.jobs[fix_of].get("target") == INTEGRATION:
        return INTEGRATION
    return fix_target(task, fix_id)


def answered_round(task: Task, fix_id: str, events: list[dict] | None = None) -> str | None:
    """The changes-required review round a fix job answers. An integration fix names it in
    `fix_of`; a job fix answers the last changes-required round of its target that completed
    before the fix was added (events.jsonl keeps the order)."""
    key = fix_key(task, fix_id)
    if key == INTEGRATION:
        return task.jobs[fix_id]["fix_of"]
    if key is None:
        return None
    last = None
    for event in events if events is not None else task.events():
        if (event.get("type") == "review.completed" and event.get("target") == key
                and event.get("verdict") == "changes-required"):
            last = event.get("job")
        elif event.get("type") == "job.added" and event.get("job") == fix_id:
            return last
    return last


def changes_count(task: Task, key: str, up_to: str | None = None) -> int:
    """Changes-required rounds of a target, up to and including `up_to` when given."""
    rounds = review_rounds(task, key)
    if up_to in rounds:
        rounds = rounds[:rounds.index(up_to) + 1]
    return sum(1 for r in rounds if requires_changes(task.jobs[r]))


def fixes_of(task: Task, key: str) -> list[str]:
    return [i for i in task.jobs if task.jobs[i].get("fix_of") and fix_key(task, i) == key]


# -------------------------------------------------------------- approach check

def approach_check(task: Task, fix_id: str) -> dict | None:
    """[APPROACH-CHECK]: the fill-ins of the approach paragraph for a fix job, or None. Due when
    the fix answers changes-required round k with k >= N - 1 (N = max-review-rounds now), and
    from then on for every fix of the same target: once an earlier fix got the paragraph, or a
    round of the target parked it at the limit, whatever N is raised to."""
    key = fix_key(task, fix_id)
    answered = answered_round(task, fix_id) if key else None
    if not answered or answered not in task.jobs:
        return None
    k = changes_count(task, key, answered)
    limit = max_review_rounds(task.settings)
    sticky = (any(task.jobs[r].get("limit_park") for r in review_rounds(task, key))
              or any(task.jobs[f].get("approach_check") for f in fixes_of(task, key) if f != fix_id)
              or task.jobs[fix_id].get("approach_check"))
    if k < limit - 1 and not sticky:
        return None
    rounds = review_rounds(task, key)
    earlier = [r for r in rounds[:rounds.index(answered) + 1] if requires_changes(task.jobs[r])]
    return {"fix": k, "target": INTEGRATION_LABEL if key == INTEGRATION else key, "round": answered,
            # the next changes-required round parks; after a raise, at the new limit
            "max_rounds": max(limit, k + 1), "earlier_rounds": [str(result_file(task, r)) for r in earlier]}


def mark_approach_check(task: Task, fix_id: str) -> dict | None:
    """`sae dispatch`: record on the fix job that its prompt carries the approach paragraph, so
    every later fix of its target gets it too."""
    check = approach_check(task, fix_id)
    if check:
        task.jobs[fix_id]["approach_check"] = {"round": check["round"], "fix": check["fix"],
                                               "max_rounds": check["max_rounds"]}
    return check


def mark_limit_park(task: Task, review_id: str) -> None:
    """`sae collect`: the review round parked its target (a job or the task) at the round limit."""
    task.jobs[review_id]["limit_park"] = max_review_rounds(task.settings)
    task.touch(task.jobs[review_id])


# ----------------------------------------------------------- approach proposal

def approach_proposal(path: Path) -> bool:
    return has_content(md_section(split_frontmatter(read(path))[1], "Approach proposal"))


def approach_proposal_line(path: Path, body: str) -> str | None:
    """The `sae collect` line for a done result with a non-empty `## Approach proposal`."""
    return APPROACH_PROPOSAL_COLLECT.format(path=path) if has_content(md_section(body, "Approach proposal")) else None


def proposal_results(task: Task, review_id: str) -> list[Path]:
    """[FIX-WORKER]: the results of the fix jobs of the previous round that hold an Approach
    proposal, for the prompt of review round `review_id`."""
    key = task.jobs[review_id].get("target")
    rounds = review_rounds(task, key) if key else []
    if review_id not in rounds or rounds.index(review_id) == 0:
        return []
    previous = rounds[rounds.index(review_id) - 1]
    events = task.events()
    found = []
    for fix in fixes_of(task, key):
        path = result_file(task, fix)
        if (task.jobs[fix]["status"] == "done" and answered_round(task, fix, events) == previous
                and approach_proposal(path)):
            found.append(path)
    return found


# ------------------------------------------------------------------ park story

def read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def section_text(text: str, title: str) -> str:
    lines = [l.strip() for l in strip_html_comments(md_section(text, title) or "").splitlines() if l.strip()]
    return " ".join(lines)


def result_summary(path: Path) -> str | None:
    meta = split_frontmatter(read(path))[0]
    summary = str(meta.get("summary") or "").strip()
    return summary or None


FIELD_RE = re.compile(r"^\*\*([^*]+?):?\*\*:?\s*(.*)$")


def round_findings(path: Path) -> list[dict]:
    """`{number, title, suggested_fix}` of each finding of a review file; only titles and
    suggested fixes, never evidence."""
    body = split_frontmatter(read(path))[1]
    found: list[dict] = []
    field = None
    for line in strip_html_comments(md_section(body, "Findings") or "").splitlines():
        stripped = line.strip()
        heading = FINDING_HEADING_RE.match(stripped) if stripped.startswith("###") else None
        if heading:
            found.append({"number": heading.group(1), "title": heading.group(2).strip(), "suggested_fix": None})
            field = None
            continue
        m = FIELD_RE.match(stripped)
        if m:
            field = m.group(1).strip().lower()
            if field == "suggested fix" and found:
                found[-1]["suggested_fix"] = m.group(2).strip() or None
        elif stripped and field == "suggested fix" and found:
            found[-1]["suggested_fix"] = " ".join(filter(None, [found[-1]["suggested_fix"], stripped]))
        elif not stripped:
            field = None
    return [f for f in found if not f["title"].startswith("<")]


DO_NOT_RE = re.compile(r"\b(do not|don't|never)\b", re.I)


def do_not_limits(path: Path) -> list[str]:
    """The "do not" lines of a fix job file, with the reasons they give."""
    body = split_frontmatter(read(path))[1]
    return [re.sub(r"^[-*]\s+|^\d+[.)]\s+", "", l.strip()) for l in strip_html_comments(body).splitlines()
            if DO_NOT_RE.search(l) and not l.lstrip().startswith("#")]


def limit_parked_jobs(task: Task) -> list[str]:
    """Writer jobs parked by sae at the review-round limit (not by their worker)."""
    limit = max_review_rounds(task.settings)
    out = []
    for job_id, job in task.jobs.items():
        if job["status"] != "parked" or not job.get("review_rounds"):
            continue
        rounds = review_rounds(task, job_id)
        if job["review_rounds"] >= limit or any(task.jobs[r].get("limit_park") for r in rounds):
            out.append(job_id)
    return out


def park_options(task: Task, key: str, review_id: str) -> list[dict]:
    """The choices at the round limit, each with the commands to run once the user chose it
    (audit 2026-11-20, proposal 2). A parked task has no drop: the integration review runs only
    after every writer merged, and a merged job cannot be dropped."""
    limit = max_review_rounds(task.settings)
    integration = key == INTEGRATION
    another = [fix_job_command(task, review_id if integration else key)]
    if limit < 10:
        another.append(f"sae set {task.id} max-review-rounds={limit + 1}")
    approach = [] if integration else [f'sae job drop {task.id} {key} --reason "<why>"']
    options = [
        {"choice": "another round", "commands": another},
        {"choice": "change the approach", "commands": approach + [f"sae decision new {task.id} --from {review_id}"]},
        {"choice": "reduce the requirement: append an amendment under ## Amendments in specs.md, then log it",
         "commands": [f"sae log {task.id} amendment \"<summary>\" --id <AMEND-ID> --by human"]},
        {"choice": "accept", "commands": [accept_line(task, review_id, key)]},
    ]
    # Not for a parked job: sae finish --override still waits for the final validation, which
    # waits for the unmerged job.
    if integration:
        options.append({"choice": "close anyway", "commands": [close_anyway_command(task)]})
    return options


def option_lines(task: Task, key: str, review_id: str) -> list[str]:
    lines = ["Options:"]
    for option in park_options(task, key, review_id):
        lines.append(f"  - {option['choice']}:")
        lines += [f"    {c}" for c in option["commands"]]
    return lines + [f"While you wait for the answer: {wait_line(task, key, review_id)}"]


def wait_line(task: Task, key: str, review_id: str) -> str:
    return f"sae ask {task.id} \"<question>\" --job {review_id if key == INTEGRATION else key}"


def park_story(task: Task, key: str) -> dict | None:
    """[PARK-STORY]: the story of a job (`key` its ID) or of the task (`key` "integration")
    parked at the round limit, or None when it is not parked there. Built only from job files,
    result summaries, review finding titles and suggested fixes, and the fix jobs' "do not"
    lines. The data shape is the one `sae next --json`, `sae status --json` and the viewer get."""
    if key == INTEGRATION:
        parked_by = integration_parked(task)
        if not parked_by:
            return None
        objective, first = task.info.get("title"), None
    else:
        if key not in limit_parked_jobs(task):
            return None
        rounds = [r for r in review_rounds(task, key) if requires_changes(task.jobs[r])]
        parked_by = rounds[-1] if rounds else None
        if not parked_by:
            return None
        objective = section_text(split_frontmatter(read(job_file(task, key)))[1], "Objective") or None
        first = result_summary(result_file(task, key))
    events = task.events()
    answers = {f: answered_round(task, f, events) for f in fixes_of(task, key)}
    rounds_out = []
    for number, review_id in enumerate(review_rounds(task, key), start=1):
        review = task.jobs[review_id]
        if review["status"] != "done":
            continue
        fixes = [{"id": f, "status": task.jobs[f]["status"], "summary": result_summary(result_file(task, f)),
                  "do_not": do_not_limits(job_file(task, f))}
                 for f, answered in answers.items() if answered == review_id]
        rounds_out.append({"id": review_id, "round": review.get("round") or number, "verdict": review.get("verdict"),
                           "accepted": bool(review.get("accepted")),
                           "findings": round_findings(result_file(task, review_id)), "fixes": fixes})
    return {"target": key, "parked_by": parked_by, "opening": PARK_OPENING,
            "changes_rounds": changes_count(task, key), "max_rounds": max_review_rounds(task.settings),
            "objective": objective, "first_summary": first, "rounds": rounds_out,
            "options": park_options(task, key, parked_by), "wait": wait_line(task, key, parked_by)}


def park_stories(task: Task) -> list[dict]:
    """Every story of the task: the jobs parked at the round limit, then the parked task."""
    stories = [park_story(task, j) for j in limit_parked_jobs(task)] + [park_story(task, INTEGRATION)]
    return [s for s in stories if s]


def park_story_text(task: Task, story: dict) -> str:
    """The story as `sae next` and `sae status` print it."""
    key, n, limit = story["target"], story["changes_rounds"], story["max_rounds"]
    if key == INTEGRATION:
        head = (f"The task is parked for the user: {story['parked_by']} still requires changes after a fix round "
                f"({n} changes-required integration rounds, max-review-rounds {limit}). Nothing is dispatched "
                "until the user chooses (decision jobs still run).")
        lines = [story["opening"], head, f"Task: {story['objective']}"]
    else:
        head = (f"{key} is parked for the user: {n} review round{'s' if n != 1 else ''} required changes "
                f"(max-review-rounds {limit}).")
        lines = [story["opening"], head]
        if story["objective"]:
            lines.append(f"Objective of {key}: {story['objective']}")
        if story["first_summary"]:
            lines.append(f"Its result: {story['first_summary']}")
    for r in story["rounds"]:
        verdict = r["verdict"] + (", accepted" if r["accepted"] else "")
        lines.append(f"Round {r['round']} — {r['id']}: {verdict}")
        for f in r["findings"]:
            lines.append(f"  Finding: {f['title']}")
            if f["suggested_fix"]:
                lines.append(f"    Suggested fix: {f['suggested_fix']}")
        if not r["findings"] and r["verdict"] == "changes-required":
            lines.append("  (no finding titles in its review file)")
        for fix in r["fixes"]:
            lines.append(f"  Fix {fix['id']} ({fix['status']}): {fix['summary'] or 'no summary'}")
            lines += [f"    Limit: {d}" for d in fix["do_not"]]
    lines += option_lines(task, key, story["parked_by"])
    return "\n".join(lines)
