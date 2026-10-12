"""Needs graph, waits_for, writer slots, holds, requirement IDs, plan lint and the check run."""

from __future__ import annotations

import re
from pathlib import Path

from .common import (
    BRIEF_MAX_LINES,
    JOB_ID_RE,
    JOB_KINDS,
    KINDS_BY_PHASE,
    REVIEW_TARGET_BY_PHASE,
    WRITER_KINDS,
    read_text,
)
from .config import cfg
from .findings import resolves_errors
from .markdown import has_content, md_section, split_frontmatter, strip_html_comments
from .tasks import Task, as_list, is_generated, job_file, job_meta, new_job, tasks_dir


def ancestors(jobs: dict, job_id: str) -> set[str]:
    seen: set[str] = set()
    stack = list(jobs.get(job_id, {}).get("needs", []))
    while stack:
        current = stack.pop()
        if current in seen or current not in jobs:
            continue
        seen.add(current)
        stack.extend(jobs[current]["needs"])
    return seen


def find_cycle(jobs: dict) -> list[str] | None:
    color: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = 1
        path.append(node)
        for need in jobs[node]["needs"]:
            if need not in jobs:
                continue
            if color.get(need) == 1:
                return path[path.index(need):] + [need]
            if color.get(need) is None:
                found = visit(need)
                if found:
                    return found
        color[node] = 2
        path.pop()
        return None

    for job_id in jobs:
        if color.get(job_id) is None:
            found = visit(job_id)
            if found:
                return found
    return None


def parallel_possible(jobs: dict, a: str, b: str) -> bool:
    return a not in ancestors(jobs, b) and b not in ancestors(jobs, a)


def kind_allowed_now(task: Task, job: dict) -> bool:
    phase = task.phase
    if job["kind"] not in KINDS_BY_PHASE.get(phase, set()):
        return False
    if job["kind"] == "review" and phase in REVIEW_TARGET_BY_PHASE:
        return job.get("target") == REVIEW_TARGET_BY_PHASE[phase]
    return True


def review_rounds(task: Task, target: str) -> list[str]:
    """The review jobs of one target (a job ID, `spec`, `plan` or `integration`), by round."""
    ids = [i for i, j in task.jobs.items() if j["kind"] == "review" and j.get("target") == target]
    return sorted(ids, key=lambda i: task.jobs[i].get("round") or 1)


def last_round(task: Task, target: str) -> str | None:
    rounds = review_rounds(task, target)
    return rounds[-1] if rounds else None


def requires_changes(job: dict) -> bool:
    return job["status"] == "done" and job.get("verdict") == "changes-required"


def fix_target(task: Task, job_id: str) -> str | None:
    """The writer job that a fix job repairs: the fix works on its branch and merges with it.
    A fix job of an integration review round is an ordinary writer, so None."""
    fix = task.jobs[job_id].get("fix_of")
    target = task.jobs.get(fix) if fix else None
    return fix if target is not None and target["kind"] in WRITER_KINDS else None


def integration_parked(task: Task) -> str | None:
    """The integration review round that parks the task, or None: its second (or later)
    changes-required round while no fix job of that round exists (07-cli-spec §6)."""
    rounds = review_rounds(task, "integration")
    if not rounds or not requires_changes(task.jobs[rounds[-1]]):
        return None
    if sum(1 for i in rounds if requires_changes(task.jobs[i])) < 2:
        return None
    if any(j.get("fix_of") == rounds[-1] for j in task.jobs.values()):
        return None
    return rounds[-1]


def works_on_unmerged(task: Task, job: dict, need: str) -> bool:
    """Reviews and integration jobs work on their unmerged target; a job review also on the
    target's fix jobs, which merge together with it after the review (DL-94)."""
    target = job.get("target")
    if need == target:
        return True
    return job["kind"] == "review" and target is not None and fix_target(task, need) == target


def waits_for(task: Task, job_id: str) -> list[str]:
    """What a pending job waits for; empty when it is ready."""
    jobs = task.jobs
    job = jobs[job_id]
    reasons = []
    for need in job["needs"]:
        other = jobs.get(need)
        if other is None:
            reasons.append(f"{need} (unknown job)")
        elif other["status"] != "done":
            reasons.append(need)
        elif (other["kind"] in WRITER_KINDS and task.uses_worktrees and not other["merged"]
              and not works_on_unmerged(task, job, need)):
            reasons.append(f"{need} (merge)")
    if job["final"]:
        open_jobs = [i for i, j in jobs.items() if i != job_id and j["status"] != "done"]
        if open_jobs:
            reasons.append("all other jobs: " + ", ".join(open_jobs))
        last = last_round(task, "integration")
        if last and requires_changes(jobs[last]):
            reasons.append(f"{last} (changes-required: fix jobs, then the next round)")
    parked = integration_parked(task)
    if parked:
        reasons.append(f"the task is parked: {parked} requires changes again")
    for held in active_holds(task):
        reasons.append(f"hold after {held}")
    if not kind_allowed_now(task, job):
        reasons.append(f"phase {task.phase}")
    return reasons


def is_ready(task: Task, job_id: str) -> bool:
    return task.jobs[job_id]["status"] == "pending" and not waits_for(task, job_id)


def hold_active(task: Task, job_id: str) -> bool:
    """A hold after a job is active once the job is done, and merged for a writer in the
    worktrees layout ([HOLD-AFTER-JOB], 07-cli-spec §6)."""
    job = task.jobs.get(job_id)
    if job is None or job["status"] != "done":
        return False
    return not (job["kind"] in WRITER_KINDS and task.uses_worktrees and not job["merged"])


def active_holds(task: Task) -> list[str]:
    return [i for i in (task.info.get("holds") or {}) if hold_active(task, i)]


def release_command(task: Task, job_id: str) -> str:
    return f"sae hold {task.id} {job_id} --release"


def scopes_overlap(a: list[str], b: list[str]) -> bool:
    def prefix(pattern: str) -> str:
        return re.split(r"[*?\[]", pattern, maxsplit=1)[0]

    for pa in a:
        for pb in b:
            x, y = prefix(pa), prefix(pb)
            if x.startswith(y) or y.startswith(x):
                return True
    return False


def writer_slots(task: Task, config: dict | None) -> int:
    if task.uses_worktrees:
        return int(cfg(config, "parallel.max_writers"))
    return 1


def writer_blocked(task: Task, job_id: str, config: dict | None) -> str | None:
    """Why a ready writer job cannot start now, or None."""
    running = [i for i, j in task.jobs.items() if j["kind"] in WRITER_KINDS and j["status"] == "running" and i != job_id]
    if not running:
        return None
    if not task.info.get("git"):
        # Without git a second writer runs only when both declare disjoint scopes.
        mine = as_list(job_meta(task, job_id).get("scope"))
        if len(running) == 1:
            theirs = as_list(job_meta(task, running[0]).get("scope"))
            if mine and theirs and not scopes_overlap(mine, theirs):
                return None
        return f"writer running: {', '.join(running)}"
    slots = writer_slots(task, config)
    if len(running) >= slots:
        return f"all writer slots busy: {', '.join(running)}; {writer_slot_text(task, len(running), slots)}"
    return None


def writer_slot_text(task: Task, used: int, slots: int) -> str:
    """The writer-slot notice with the source of the limit ([SETTINGS-VISIBLE])."""
    if task.uses_worktrees:
        return f"writer slots {used}/{slots} (parallel.max_writers in the user config)"
    return f"writer slots {used}/{slots} (chain layout: one writer at a time)"


def writer_slot_notice(task: Task, config: dict | None) -> str | None:
    """The notice when every writer slot is busy and a ready writer waits, else None."""
    if not task.info.get("git") or task.phase != "executing":
        return None
    running = [i for i, j in task.jobs.items() if j["kind"] in WRITER_KINDS and j["status"] == "running"]
    slots = writer_slots(task, config)
    if len(running) < slots:
        return None
    waiting = [i for i, j in task.jobs.items()
               if j["kind"] in WRITER_KINDS and is_ready(task, i)]
    if not waiting:
        return None
    return f"Full: {writer_slot_text(task, len(running), slots)}."


REQ_HEADING_RE = re.compile(r"^###\s+\[([^\]]*)\]")
ACCEPT_ITEM_RE = re.compile(r"^\s*[-*]\s+\[([^\]]*)\]")


def requirement_ids(task: Task) -> tuple[list[str], list[str], list[str]]:
    """(requirement IDs, errors, warnings) from specs.md `## Requirements` and the intent's
    `## Acceptance`."""
    ids: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    seen_heading_ids: dict[str, int] = {}
    spec = read_text(task.dir / "specs.md")
    if spec is not None:
        clean = strip_html_comments(spec)
        fence = False
        for line in clean.splitlines():
            if line.lstrip().startswith("```"):
                fence = not fence
            m = None if fence else REQ_HEADING_RE.match(line)
            if m:
                seen_heading_ids[m.group(1)] = seen_heading_ids.get(m.group(1), 0) + 1
        for heading_id, count in seen_heading_ids.items():
            if not JOB_ID_RE.match(heading_id):
                errors.append(f"specs.md: invalid ID [{heading_id}] (use UPPER-KEBAB)")
            elif count > 1:
                errors.append(f"specs.md: duplicate ID [{heading_id}]")
        requirements = md_section(clean, "Requirements") or ""
        current, has_checks = None, False
        for line in requirements.splitlines() + ["### [END-OF-SECTION]"]:
            m = REQ_HEADING_RE.match(line)
            if m:
                if current and JOB_ID_RE.match(current):
                    ids.append(current)
                    if not has_checks:
                        warnings.append(f"specs.md: requirement [{current}] has no acceptance checks")
                current, has_checks = m.group(1), False
            elif re.match(r"^\s*[-*]\s+\[[ xX]\]", line):
                has_checks = True
    intent = read_text(task.dir / "intent.md", "")
    acceptance = md_section(strip_html_comments(intent), "Acceptance")
    for line in (acceptance or "").splitlines():
        m = ACCEPT_ITEM_RE.match(line)
        if not m or m.group(1).strip() in ("", "x", "X"):
            continue
        item_id = m.group(1)
        if not JOB_ID_RE.match(item_id):
            errors.append(f"intent.md: invalid acceptance ID [{item_id}] (use UPPER-KEBAB)")
        elif item_id in ids:
            errors.append(f"intent.md: duplicate ID [{item_id}]")
        else:
            ids.append(item_id)
    return ids, errors, warnings


def hot_files(root: Path) -> list[str]:
    profile = read_text(tasks_dir(root) / "repo" / "profile.md")
    if not profile:
        return []
    section = strip_html_comments(md_section(profile, "Hot files") or "")
    return [m.group(1).strip() for m in re.finditer(r"^\s*[-*]\s+(.+)$", section, flags=re.M)]


def lint_plan(task: Task) -> tuple[list[str], list[str]]:
    jobs = task.jobs
    errors: list[str] = []
    warnings: list[str] = []
    req_ids, req_errors, _ = requirement_ids(task)
    errors.extend(req_errors)
    covered: set[str] = set()
    metas = {}
    for job_id, job in jobs.items():
        if not JOB_ID_RE.match(job_id):
            errors.append(f"{job_id}: invalid job ID")
        if job["kind"] not in JOB_KINDS:
            errors.append(f"{job_id}: invalid kind {job['kind']}")
        for need in job["needs"]:
            if need not in jobs:
                errors.append(f"{job_id}: needs unknown job {need}")
        if is_generated(job_id, job):
            errors.extend(resolves_errors(task, job_id, job["kind"], job_meta(task, job_id)))
            continue
        text = read_text(job_file(task, job_id))
        if text is None:
            errors.append(f"{job_id}: no job file jobs/{job_id}.md")
            continue
        meta, body = split_frontmatter(text)
        metas[job_id] = meta
        objective = md_section(body, "Objective")
        if not has_content(objective):
            errors.append(f"{job_id}: the job file has no objective")
        else:
            sentence_ends = re.findall(r"[.!?](?:\s|$)", strip_html_comments(objective).strip())
            if len(sentence_ends) > 1:
                warnings.append(f"{job_id}: the objective is longer than one sentence")
        for req in as_list(meta.get("covers")):
            if req not in req_ids:
                errors.append(f"{job_id}: covers [{req}], which does not exist")
            elif job["kind"] != "review":
                covered.add(req)
        errors.extend(resolves_errors(task, job_id, job["kind"], meta))
        if job["kind"] in WRITER_KINDS + ("validation",) and not as_list(meta.get("verify")):
            warnings.append(f"{job_id}: no verify commands (only judgement checks this job)")
    cycle = find_cycle(jobs)
    if cycle:
        errors.append("cycle in needs: " + " → ".join(cycle))
    for req in req_ids:
        if req not in covered:
            errors.append(f"requirement [{req}] is not covered by any job")
    finals = [i for i, j in jobs.items() if j["final"]]
    if len(finals) > 1:
        errors.append(f"more than one final job: {', '.join(finals)}")
    writers = [i for i, j in jobs.items() if j["kind"] in WRITER_KINDS and j["status"] in ("pending", "running")]
    hot = hot_files(task.root)
    if not cycle:
        for index, a in enumerate(writers):
            for b in writers[index + 1:]:
                if not parallel_possible(jobs, a, b):
                    continue
                sa, sb = as_list(metas.get(a, {}).get("scope")), as_list(metas.get(b, {}).get("scope"))
                if sa and sb and scopes_overlap(sa, sb):
                    warnings.append(f"{a} and {b} can run in parallel and their scopes overlap")
                elif hot and (not sa or not sb):
                    warnings.append(f"{a} and {b} can run in parallel, one has no scope, and the repo has hot files")
    brief = read_text(task.dir / "brief.md")
    if brief is not None and len(brief.splitlines()) > BRIEF_MAX_LINES:
        warnings.append(f"brief.md has {len(brief.splitlines())} lines (keep it under {BRIEF_MAX_LINES})")
    planned = [i for i, j in jobs.items() if not is_generated(i, j) and j["kind"] not in ("planning", "research")]
    if len(planned) >= 2:
        plan = read_text(task.dir / "plan.md")
        if plan is None or not has_content(md_section(plan, "Riskiest assumptions")):
            warnings.append('plan.md has no "Riskiest assumptions" section')
    return errors, warnings


def add_generated_job(task: Task, job_id: str, kind: str, needs: list[str], difficulty: str | None,
                      target: str | None, reason: str, round_: int | None = None) -> dict:
    """Adds a job that sae generates (a review, INTEGRATE-<ID>). Its needs are real edges
    ([GENERATED-JOB-EDGES]); `generated: true` and `by: sae` tell them from planner edges."""
    job = new_job(kind, needs, difficulty, target=target)
    job["generated"] = True
    job["round"] = round_ if round_ is not None else (1 if kind == "review" else None)
    task.jobs[job_id] = job
    task.event("job.added", job=job_id, kind=kind, needs=needs, difficulty=difficulty, target=target,
               round=job["round"], reason=reason, by="sae")
    return job


def place_final_after(task: Task, review_id: str) -> None:
    """The final validation needs the last integration review round, instead of the earlier
    round. The edge is generated: listed in `generated_needs`, its event has `by: sae`."""
    rounds = set(review_rounds(task, "integration"))
    for job_id, job in task.jobs.items():
        if not job["final"] or job["status"] not in ("pending", "running"):
            continue  # a running one is stale after a late merge: it runs again after review_id
        needs = [n for n in job["needs"] if n not in rounds] + [review_id]
        if needs == job["needs"]:
            continue
        old = job["needs"]
        job["needs"] = needs
        job["generated_needs"] = [n for n in job.get("generated_needs", []) if n not in rounds] + [review_id]
        task.touch(job)
        task.event("job.changed", job=job_id, changes={"needs": [old, needs]},
                   reason=f"the final validation runs after {review_id}", by="sae")


def check_lint(task: Task) -> tuple[list[str], list[str]]:
    """(errors, warnings) of `sae check` by phase; writes nothing."""
    if task.phase == "shaping":
        _, errors, warnings = requirement_ids(task)
        return errors, warnings
    errors, warnings = lint_plan(task)
    from .reviews import review_mark  # late import: reviews imports this module
    unreviewed = [i for i in task.jobs if task.jobs[i]["kind"] in WRITER_KINDS
                  and not (review_mark(task, i) or {"reviewed": True})["reviewed"]]
    if unreviewed:
        warnings.append(f"flagged for review, but job reviews are off: {', '.join(unreviewed)}")
    return errors, warnings


def due_reviews(task: Task, errors: list[str] | None = None) -> list[str]:
    """The spec or plan review that is due but not yet a job (07-cli-spec §10.1): its review
    point is on, the check is clean, and the thing to review exists (`specs.md`; a plan with
    jobs and no open planning or research job). Computed, never stored: `sae next` lists it as
    ready, `sae dispatch` adds it."""
    points = task.settings["review"]["points"]
    jobs = task.jobs
    if task.phase == "shaping":
        point, target, review_id = "spec", "spec", "REVIEW-SPEC"
        if not (task.dir / "specs.md").exists():
            return []
    elif task.phase == "planning":
        point, target, review_id = "plan", "plan", "REVIEW-PLAN"
        if any(j["kind"] in ("planning", "research") and j["status"] != "done" for j in jobs.values()):
            return []
        if not any(not is_generated(i, j) and j["kind"] not in ("planning", "research") for i, j in jobs.items()):
            return []
    else:
        return []
    if point not in points or any(j["kind"] == "review" and j.get("target") == target for j in jobs.values()):
        return []
    if errors is None:
        errors = check_lint(task)[0]
    return [] if errors else [review_id]


def add_due_review(task: Task, review_id: str) -> None:
    target = "spec" if review_id == "REVIEW-SPEC" else "plan"
    # Difficulty null: a task-level review follows the task difficulty (07-cli-spec §5.1).
    add_generated_job(task, review_id, "review", [], None, target, f"{target} review is a review point")


def run_check(task: Task, write: bool = True) -> tuple[list[str], list[str], list[str]]:
    """Lints by phase. Returns (errors, warnings, due spec or plan reviews). With `write` (sae
    approve) it also logs the check and adds the due reviews; `sae check` passes False."""
    errors, warnings = check_lint(task)
    due = due_reviews(task, errors)
    if write:
        task.event("spec.checked" if task.phase == "shaping" else "plan.checked",
                   errors=len(errors), warnings=len(warnings))
        for review_id in due:
            add_due_review(task, review_id)
    return errors, warnings, due
