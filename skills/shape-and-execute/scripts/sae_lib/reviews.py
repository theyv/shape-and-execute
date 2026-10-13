"""Verify re-run, collect, review rounds, planned reviews, review marks, merges and finish gates."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .common import (
    DECISION_CLASSES,
    EXIT_GATE,
    EXIT_GIT,
    EXIT_OK,
    EXIT_USAGE,
    EXIT_VERIFY,
    VERDICTS,
    WRITER_KINDS,
    SaeError,
    emit,
    fail,
    iso,
    read_text,
    write_atomic,
)
from .config import cfg, load_config, max_verify_failures
from .findings import close_resolved, resolution_notes
from .gitutil import find_root, git, run
from .graph import (
    add_generated_job,
    fix_target,
    integration_parked,
    last_round,
    place_final_after,
    requires_changes,
    review_rounds,
)
from .markdown import md_section, split_frontmatter, strip_html_comments
from .routing import override_key, resolve_model
from .tasks import Task, as_list, job_meta, open_task, parked_reason, result_file
from .workspaces import (
    job_branch,
    remove_worktree,
    require_on_task_branch,
    task_worktrees_dir,
    workspace_of,
    workspace_owner,
)


def glob_regex(pattern: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + "$")


def in_scope(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        plain = pattern.rstrip("/")
        if path == plain or path.startswith(plain + "/") or glob_regex(pattern).match(path):
            return True
    return False


def run_verify(task: Task, job_id: str, workdir: Path, config: dict) -> tuple[bool, str | None, int | None]:
    commands = [str(c) for c in as_list(job_meta(task, job_id).get("verify"))]
    if not commands:
        return True, None, None
    timeout = cfg(config, "verify.timeout_s")
    log = []
    for command in commands:
        try:
            proc = subprocess.run(command, shell=True, cwd=str(workdir), capture_output=True, text=True, timeout=timeout)
            code, output = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as exc:
            code, output = 124, f"timeout after {timeout} s\n{exc.stdout or ''}{exc.stderr or ''}"
        log.append(f"$ {command}\nexit {code}\n{output}")
        if code != 0:
            write_atomic(task.dir / "jobs" / f"{job_id}.verify.log", f"# verify {iso()} in {workdir}\n\n" + "\n".join(log))
            return False, command, code
    return True, None, None


MARK_REVIEW = "review"
MARK_FORCED_REVIEW = "review · forced by settings"
MARK_FORCED_NO_REVIEW = "no review · forced by settings"
POSITIVE_VERDICTS = ("pass", "pass-with-notes")


def review_mark(task: Task, job_id: str) -> dict | None:
    """The effective review mark of a job ([JOB-REVIEW-FLAG-HONESTY]): the
    planner's flag and the review points together. None when the job shows no mark (not a
    writer, a fix job, or unflagged without `all-jobs`). `reviewed` says whether a job review
    will run, `forced` whether the settings overrule the planner, `reason` why."""
    job = task.jobs[job_id]
    if job["kind"] not in WRITER_KINDS or job.get("fix_of"):
        return None
    points = task.settings["review"]["points"]
    flagged = bool(job.get("review"))
    if "all-jobs" in points:
        if flagged:
            return {"mark": MARK_REVIEW, "reviewed": True, "forced": False,
                    "reason": "flagged by the planner; review points include all-jobs"}
        return {"mark": MARK_FORCED_REVIEW, "reviewed": True, "forced": True,
                "reason": "not flagged, but review points include all-jobs: every writer job is reviewed"}
    if flagged and "selected-jobs" in points:
        return {"mark": MARK_REVIEW, "reviewed": True, "forced": False,
                "reason": "flagged by the planner; review points include selected-jobs"}
    if flagged:
        return {"mark": MARK_FORCED_NO_REVIEW, "reviewed": False, "forced": True,
                "reason": "flagged by the planner, but job reviews are off "
                          "(review points have neither selected-jobs nor all-jobs)"}
    return None


def review_due(task: Task, job_id: str) -> bool:
    return bool((review_mark(task, job_id) or {}).get("reviewed"))


def planned_reviews(task: Task, config: dict | None = None) -> list[dict]:
    """The reviews that will run but do not exist yet, each with its future
    ID, target, round, `needs` (its place in the graph), `needed_by` (the jobs that will need it)
    and, with a config, the resolved harness, model and effort. Never stored, never counted in
    progress."""
    if task.phase not in ("shaping", "planning", "executing"):
        return []
    jobs = task.jobs
    points = task.settings["review"]["points"]
    planned: list[dict] = []

    def plan(review_id: str, target: str, needs: list[str], needed_by: list[str]) -> None:
        entry = {"id": review_id, "target": target, "round": 1, "needs": needs, "needed_by": needed_by,
                 "harness": None, "model": None, "effort": None}
        if config is not None:
            try:
                # A planned review ID resolves like a job (difficulty, overrides); exact=False: a
                # read-only listing names Codex families and never reads the model catalog.
                model = resolve_model(task, review_id, config, exact=False)
                entry.update({"harness": model.get("harness"), "model": model.get("model"),
                              "effort": model.get("effort")})
            except SaeError:
                pass  # incomplete routing: the review is still planned, without a model
        planned.append(entry)

    if "spec" in points and task.phase == "shaping" and not review_rounds(task, "spec"):
        plan("REVIEW-SPEC", "spec", [], [])
    if "plan" in points and task.phase in ("shaping", "planning") and not review_rounds(task, "plan"):
        plan("REVIEW-PLAN", "plan", [], [])
    for job_id, job in jobs.items():
        if (review_due(task, job_id) and not job["merged"] and job["status"] not in ("failed",)
                and not review_rounds(task, job_id) and f"REVIEW-{job_id}" not in jobs):
            plan(f"REVIEW-{job_id}", job_id, [job_id], [])
    if "integration" in points and not review_rounds(task, "integration") and "REVIEW-INTEGRATION" not in jobs:
        writers = [i for i, j in jobs.items() if j["kind"] in WRITER_KINDS]
        if writers:
            finals = [i for i, j in jobs.items() if j["final"]]
            plan("REVIEW-INTEGRATION", "integration", writers, finals)
    return planned


def next_review_rounds(task: Task, config: dict | None = None) -> list[dict]:
    """The next review round of a changes-required round while its fix jobs are open: sae adds it
    when they are done (a job review, `after_writer_done`) or merged (the integration review,
    `materialize_integration_review`). Entries as in `planned_reviews`, plus `key` (the override
    key of every round) and `like` (the last round: the next one routes as it does, with the same
    target difficulty, or the difficulty that carries over). For the viewer; never stored."""
    if task.phase != "executing":
        return []
    jobs = task.jobs
    planned: list[dict] = []

    def plan(review_id: str, target: str, number: int, last: str, needs: list[str], needed_by: list[str]) -> None:
        if review_id in jobs:
            return
        entry = {"id": review_id, "target": target, "round": number, "needs": needs, "needed_by": needed_by,
                 "key": override_key(task, last), "like": last, "harness": None, "model": None, "effort": None}
        if config is not None:
            try:
                model = resolve_model(task, last, config, exact=False)
                entry.update({"harness": model.get("harness"), "model": model.get("model"),
                              "effort": model.get("effort")})
            except SaeError:
                pass  # incomplete routing: the round is still planned, without a model
        planned.append(entry)

    for job_id, job in jobs.items():
        rounds = review_rounds(task, job_id)
        if job["kind"] not in WRITER_KINDS or job["merged"] or not rounds or not requires_changes(jobs[rounds[-1]]):
            continue
        fixes = [i for i in jobs if fix_target(task, i) == job_id]
        if any(jobs[i]["status"] != "done" for i in fixes):
            number = (job.get("review_rounds") or 0) + 1
            plan(f"REVIEW-{job_id}-{number}", job_id, number, rounds[-1], [job_id] + fixes, [])
    rounds = review_rounds(task, "integration")
    if "integration" in task.settings["review"]["points"] and rounds and requires_changes(jobs[rounds[-1]]):
        fixes = [i for i, j in jobs.items() if j.get("fix_of") == rounds[-1]]
        if any(not jobs[i]["merged"] for i in fixes):
            number = (jobs[rounds[-1]].get("round") or len(rounds)) + 1
            plan(f"REVIEW-INTEGRATION-{number}", "integration", number, rounds[-1],
                 [i for i, j in jobs.items() if j["kind"] in WRITER_KINDS], [i for i, j in jobs.items() if j["final"]])
    return planned


def last_verdict(task: Task, target: str) -> str | None:
    verdict = None
    for review_id in review_rounds(task, target):
        job = task.jobs[review_id]
        if job["status"] == "done":
            verdict = job.get("verdict", verdict)
    return verdict


def merged_after(task: Task, review_id: str) -> list[str]:
    """Writer jobs merged after the review was last collected: a late merge ([NO-STALE-CHECKS])."""
    seen, merged = False, []
    for event in task.events():
        if event["type"] == "review.completed" and event.get("job") == review_id:
            seen, merged = True, []
        elif seen and event["type"] == "job.merged" and event.get("job") in task.jobs:
            merged.append(event["job"])
    return merged


def merge_job(task: Task, job_id: str, config: dict | None, out: list[str]) -> int:
    """Merges a done writer job (and its fix jobs) into the task branch, or only marks it
    merged in the chain layout and without git, then closes the findings the group resolved.
    Returns an exit code."""
    job = task.jobs[job_id]
    group = [job_id] + [i for i, j in task.jobs.items() if fix_target(task, i) == job_id and j["status"] == "done"]
    if job["kind"] == "integration" and job.get("target") in task.jobs:
        # The integration branch carries the target and its fix jobs ([EDGE-FIX-GROUP]).
        target = job["target"]
        group += [target] + [i for i, j in task.jobs.items()
                             if fix_target(task, i) == target and j["status"] == "done" and i not in group]
    commit = None
    if task.uses_worktrees:
        require_on_task_branch(task)
        branch = job_branch(task, job_id)
        proc = run(["git", "merge", "--no-ff", "-m", f"{job_id}: merge into task branch", "-m",
                    f"Task: {task.id}\nJob: {job_id}", branch], task.root)
        if proc.returncode != 0:
            files = git(task.root, "diff", "--name-only", "--diff-filter=U", check=False).splitlines()
            run(["git", "merge", "--abort"], task.root)
            if job["kind"] == "integration" or not files:
                fail(EXIT_GIT, f"Merge of {branch} failed: {(proc.stderr or proc.stdout).strip()}")
            integration_id = f"INTEGRATE-{job_id}"
            if integration_id not in task.jobs:
                add_generated_job(task, integration_id, "integration", [job_id], "hard", job_id,
                                  f"merge conflict of {job_id}")
            task.event("merge.conflict", job=job_id, files=files, integration_job=integration_id)
            out.append(f"Merge conflict: {job_id} ({', '.join(files)}). Added {integration_id}; dispatch it.")
            return EXIT_GIT
        commit = git(task.root, "rev-parse", "--short", "HEAD")
        for owner in {workspace_owner(task, i) for i in group}:
            remove_worktree(task, task_worktrees_dir(task, config) / owner)
    for member in group:
        task.jobs[member]["merged"] = True
        task.touch(task.jobs[member])
    task.event("job.merged", job=job_id, commit=commit)
    out.append(f"{job_id}: merged" + (f" into {task.info['branch']} ({commit})" if commit else ""))
    close_resolved(task, group, out)  # [RESOLVES-CLOSE], [EDGE-FIX-GROUP]
    reset_final_after_late_merge(task, job_id, group, out)
    return EXIT_OK


def reset_final_after_late_merge(task: Task, job_id: str, group: list[str], out: list[str]) -> None:
    """[NO-STALE-CHECKS]: a final validation that already ran goes back to pending; a running one
    is marked `stale`, so its collection sends it back to pending instead of done. The next
    integration round follows from materialize_integration_review."""
    for final_id, final in task.jobs.items():
        if not final["final"] or final_id in group:
            continue
        if final["status"] == "done":
            final["status"] = "pending"
            task.touch(final)
            task.event("job.reset", job=final_id, reason=f"{job_id} merged after it ran", by="sae")
            out.append(f"{final_id} is pending again: {job_id} merged after it ran.")
        elif final["status"] == "running":
            final["stale"] = f"{job_id} merged while it ran"
            task.touch(final)
            task.event("job.reset", job=final_id, reason=final["stale"], running=True, by="sae")
            out.append(f"{final_id} is running on older code: {job_id} merged while it ran. Its result "
                       "will not count; it runs again after the next integration round.")


def after_writer_done(task: Task, job_id: str, config: dict | None, out: list[str]) -> int:
    """A writer job is done: add its review, or merge it."""
    target = fix_target(task, job_id)
    if target:
        fixes = [i for i in task.jobs if fix_target(task, i) == target]
        open_fixes = [i for i in fixes if task.jobs[i]["status"] in ("pending", "running")]
        if open_fixes:
            out.append(f"{target}: the next review round waits for {', '.join(open_fixes)}.")
            return EXIT_OK
        rounds = task.jobs[target]["review_rounds"]
        if rounds >= 1:
            review_id = f"REVIEW-{target}-{rounds + 1}"
            if review_id not in task.jobs:
                # Done is enough for the target and its fix jobs: they merge after this round
                # (record 2026-10-10-a-review-waits-for-its-target-to-be-done.md).
                add_generated_job(task, review_id, "review", [target] + fixes, None, target,
                                  f"round {rounds + 1} after {', '.join(fixes)}", round_=rounds + 1)
                out.append(f"Added {review_id}: dispatch it.")
            return EXIT_OK
        return merge_job(task, target, config, out)
    if review_due(task, job_id):
        review_id = f"REVIEW-{job_id}"
        if review_id not in task.jobs:
            add_generated_job(task, review_id, "review", [job_id], None, job_id, "job review is due")
        out.append(f"Added {review_id}: {job_id} merges after the review passes.")
        return EXIT_OK
    return merge_job(task, job_id, config, out)


def materialize_integration_review(task: Task, out: list[str]) -> None:
    """Adds the integration review round that is due: round 1 when every
    writer job is merged; the next round when the fix jobs of a changes-required round are
    merged (limited to its findings), or when a writer merged after a passed round (limited to
    the new changes). Each round needs every writer job; the final validation needs the round."""
    if "integration" not in task.settings["review"]["points"] or task.phase != "executing":
        return
    jobs = task.jobs
    writers = [i for i, j in jobs.items() if j["kind"] in WRITER_KINDS]
    if not writers or not all(jobs[i]["merged"] for i in writers):
        return
    if any(j["status"] in ("pending", "running") and not j["final"] and j["kind"] != "review"
           for j in jobs.values()):
        return
    rounds = review_rounds(task, "integration")
    # Difficulty null: the round follows the task difficulty; a difficulty set
    # with `job edit` on the previous round carries over.
    difficulty = None
    if not rounds:
        review_id, number, limit, since, reason = "REVIEW-INTEGRATION", 1, None, None, "every writer job is merged"
    else:
        previous = jobs[rounds[-1]]
        if previous["status"] != "done":
            return
        if requires_changes(previous):
            fixes = [i for i, j in jobs.items() if j.get("fix_of") == rounds[-1]]
            if not fixes:
                return
            limit, reason = "findings", f"fix jobs of {rounds[-1]} merged: {', '.join(fixes)}"
        else:
            late = merged_after(task, rounds[-1])
            if not late:
                return
            limit, reason = "changes", f"merged after {rounds[-1]} passed: {', '.join(late)}"
        number = (previous.get("round") or len(rounds)) + 1
        review_id = f"REVIEW-INTEGRATION-{number}"
        since = (previous["attempts"][-1] if previous["attempts"] else {}).get("head")
        difficulty = previous.get("difficulty")
        if review_id in jobs:
            return
    review = add_generated_job(task, review_id, "review", writers, difficulty, "integration", reason, round_=number)
    review["limit"], review["since"] = limit, since
    place_final_after(task, review_id)
    scope = {None: "review the whole change", "findings": f"check the findings of {rounds[-1] if rounds else ''}",
             "changes": "review the changes since the last round"}[limit]
    out.append(f"Added {review_id}: {scope}.")


def interpret_result(kind: str, meta: dict, path: Path) -> tuple[str, str, dict]:
    """(status, summary, kind-specific fields) from a result file's frontmatter."""
    if kind == "review":
        verdict = meta.get("verdict")
        if verdict not in VERDICTS:
            fail(EXIT_USAGE, f"No valid verdict in {path} (got {verdict!r}). If an external reviewer wrote it, "
                             "the provider failed: run the IF IT FAILS line that dispatch printed.")
        return "done", f"verdict: {verdict}", {"verdict": verdict}
    if kind == "research":
        status = meta.get("status")
        if status not in ("done", "partial"):
            fail(EXIT_USAGE, f"{path}: frontmatter status must be done or partial (got {status!r}).")
        return "done", f"research {status}, confidence {meta.get('confidence')}", {
            "research_status": status, "confidence": meta.get("confidence")}
    if kind == "decision":
        fields = {"class": meta.get("class"), "recommendation": meta.get("recommendation"),
                  "decision": meta.get("decision")}
        if fields["class"] not in DECISION_CLASSES or fields["recommendation"] not in ("agent-decides", "human-required"):
            fail(EXIT_USAGE, f"{path}: frontmatter needs class (a decision class) and recommendation "
                             "(agent-decides | human-required).")
        return "done", f"{fields['class']}, {fields['recommendation']}: {fields['decision']}", fields
    status = meta.get("status")
    if status not in ("done", "failed", "parked"):
        fail(EXIT_USAGE, f"{path}: frontmatter status must be done, failed or parked (got {status!r}).")
    return status, str(meta.get("summary") or ""), {}


DISPUTE_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+(.*)$")  # top-level only: no indent
DISPUTE_HEADING_RE = re.compile(r"^(#{3,6})\s+(.*)$")
NO_DISPUTE_RE = re.compile(r"^[\s*_`(]*(none|n/?a|no disputed findings|no disputes|nothing|-+)[\s.*_`)]*$", re.I)


def disputed_findings(body: str) -> int:
    """[FINDINGS-ARE-CLAIMS], [DISPUTE-COUNT]: the number of substantive findings under
    `## Disputed findings`. Finding headings count (the highest heading level used, so `####`
    subsections do not); with no heading, top-level list items count (not nested bullets); text
    without items counts as one. Template comments and "none" placeholders count as zero."""
    section = md_section(body, "Disputed findings")
    if section is None:
        return 0
    lines = [line for line in strip_html_comments(section).splitlines() if line.strip()]
    headings = [m for m in (DISPUTE_HEADING_RE.match(line) for line in lines) if m]
    if headings:
        top = min(len(m.group(1)) for m in headings)
        items = [m.group(2) for m in headings if len(m.group(1)) == top]
    else:
        items = [m.group(1) for m in (DISPUTE_ITEM_RE.match(line) for line in lines) if m]
    if items:
        return sum(1 for item in items if item.strip() and not NO_DISPUTE_RE.match(item))
    return 0 if all(NO_DISPUTE_RE.match(line) for line in lines) else 1


def finish_merges(task: Task) -> list[str]:
    """Done writer jobs that `sae finish` would still merge."""
    jobs = task.jobs
    return [i for i, j in jobs.items()
            if j["kind"] in WRITER_KINDS and j["status"] == "done" and not j["merged"] and not fix_target(task, i)
            and last_verdict(task, i) != "changes-required"
            and not any(jobs[r]["status"] != "done" for r in review_rounds(task, i))]


def fix_job_command(task: Task, target: str) -> str:
    """The `sae job add` line of the next fix job of a job, or of an integration review round."""
    stem = "INTEGRATION" if target in task.jobs and task.jobs[target]["kind"] == "review" else target
    n = 1
    while f"{stem}-FIX-{n}" in task.jobs:
        n += 1
    return (f"sae job add {task.id} {stem}-FIX-{n} --kind implementation --fix-of {target} "
            f"--reason \"<finding>\"")


def verdict_gate(task: Task) -> tuple[list[tuple[str, str]], set[str]]:
    """[FINISH-VERDICT-GATE]: ([(review, fix-of target)], held-back jobs) for the last round of
    the integration review, and of each job review of an unmerged job, that says
    changes-required."""
    jobs = task.jobs
    blocks: list[tuple[str, str]] = []
    held: set[str] = set()
    last = last_round(task, "integration")
    if last and requires_changes(jobs[last]):
        blocks.append((last, last))
        held |= {i for i, j in jobs.items() if j["final"] and j["status"] != "done"}
    for job_id, job in jobs.items():
        if job["kind"] not in WRITER_KINDS or job["merged"]:
            continue
        review = last_round(task, job_id)
        if review and requires_changes(jobs[review]):
            blocks.append((review, job_id))
            held.add(job_id)
    return blocks, held


def stale_gate(task: Task) -> tuple[list[str], set[str]]:
    """[NO-STALE-CHECKS]: (problems, held-back jobs) while checks do not cover the code that will
    be closed. `finish` refuses before it merges a done writer when an integration review or a
    final validation would then not cover it, so it never merges after its gates passed."""
    jobs = task.jobs
    problems: list[str] = []
    held: set[str] = set()
    integration = "integration" in task.settings["review"]["points"]
    events = task.events()
    for review_id in review_rounds(task, "integration"):
        if jobs[review_id].get("limit") == "changes" and jobs[review_id]["status"] != "done":
            problems.append(f"{review_id} (added by a late merge) has not run")
            held.add(review_id)
    for job_id, job in jobs.items():
        if job["final"] and job["status"] != "done" and any(
                e["type"] == "job.reset" and e.get("job") == job_id for e in events):
            problems.append(f"{job_id} (reset by a late merge) has not run again")
            held.add(job_id)
    last = last_round(task, "integration")
    if integration and last and jobs[last]["status"] == "done" and not requires_changes(jobs[last]):
        late = merged_after(task, last)
        if late:
            problems.append(f"{', '.join(late)} merged after {last} passed; no round covers "
                            f"{'it' if len(late) == 1 else 'them'} yet. Add the next round:\n  sae next {task.id}")
            held |= {i for i, j in jobs.items() if j["final"] and j["status"] != "done"}
    pending = finish_merges(task)
    if pending and (integration or any(j["final"] for j in jobs.values())):
        for job_id in pending:
            problems.append(f"{job_id} is done but not merged: the checks would not cover it. "
                            f"Merge it first:\n  sae merge {task.id} {job_id}\nThen:\n  sae next {task.id}")
    return problems, held


def check_finish_gates(task: Task, with_open: bool, override: str | None) -> list[dict]:
    """The gates of `sae finish`, checked before it merges anything. Refuses
    (exit 3), or returns the gates that `--override` passes: [{"gate", "jobs"}]."""
    jobs = task.jobs
    forward = f"sae finish {task.id} --override \"<reason>\""
    running = [i for i, j in jobs.items() if j["status"] == "running"]
    if running:
        fail(EXIT_GATE, f"Still running: {', '.join(running)}. Collect them first:\n"
                        f"  sae collect {task.id} <ID>")
    verdicts, verdict_held = verdict_gate(task)
    stale, stale_held = stale_gate(task)
    held = verdict_held | stale_held
    open_jobs = [i for i, j in jobs.items() if j["status"] in ("pending", "parked") and i not in held]
    if open_jobs and not with_open:
        fail(EXIT_GATE, f"Open jobs: {', '.join(open_jobs)}. Finish them, or add --with-open when the user "
                        "accepts open items.")
    overridden: list[dict] = []
    if verdicts:
        if override is None:
            lines = [f"Finish refused: {review} says changes-required." for review, _ in verdicts]
            lines.append("Ways forward:")
            for _, target in verdicts:
                lines += ["  - fix jobs:", f"    {fix_job_command(task, target)}"]
            lines += ["  - or close anyway, with the owner's reason:", f"    {forward}"]
            fail(EXIT_GATE, "\n".join(lines))
        overridden.append({"gate": "verdict", "jobs": [r for r, _ in verdicts] + sorted(verdict_held)})
    if stale:
        if override is None:
            fail(EXIT_GATE, "\n".join(["Finish refused: the checks do not cover the code that will be closed."]
                                      + [f"  - {p}" for p in stale]
                                      + ["Run the checks:", f"  sae next {task.id}",
                                         "Or close anyway, with the owner's reason:", f"  {forward}"]))
        overridden.append({"gate": "stale", "jobs": sorted(stale_held) + finish_merges(task)})
    passed = held if override is not None else set()
    finals = [i for i, j in jobs.items() if j["final"] and j["status"] != "done" and i not in passed]
    if finals:
        fail(EXIT_GATE, f"The final validation {finals[0]} is not done. Next:\n  sae next {task.id}")
    last = last_round(task, "integration")
    if last and jobs[last]["status"] != "done" and last not in passed:
        fail(EXIT_GATE, f"{last} is not done. Next:\n  sae dispatch {task.id} {last}")
    return overridden


def finish_readiness(task: Task) -> dict:
    """The Finish card of the viewer ([GRAPH-PLACEHOLDER-FINISH]): `state` waiting | ready | blocked |
    done | abandoned and the `reason` `sae finish` would refuse with. The same gates as `sae finish`,
    without --with-open or --override and without side effects; blocked only once every job is done."""
    if task.phase in ("done", "abandoned"):
        return {"state": task.phase, "reason": None}
    if task.phase != "executing":
        return {"state": "waiting", "reason": None}
    try:
        check_finish_gates(task, False, None)
    except SaeError as exc:
        done = all(j["status"] == "done" for j in task.jobs.values())
        return {"state": "blocked" if done else "waiting", "reason": str(exc)}
    return {"state": "ready", "reason": None}


def cmd_collect(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        job_id = args.id
        job = task.job(job_id)
        if job["status"] != "running":
            fail(EXIT_USAGE, f"{job_id} is {job['status']}, not running.")
        path = result_file(task, job_id)
        text = read_text(path)
        if text is None:
            fail(EXIT_USAGE, f"No result file at {path}.")
        if not text.strip():
            fail(EXIT_USAGE, f"The result file {path} is empty. If an external reviewer wrote it, the provider "
                             "failed: run the IF IT FAILS line that dispatch printed.")
        meta, body = split_frontmatter(text)
        status, summary, fields = interpret_result(job["kind"], meta, path)
        disputed = disputed_findings(body)
        attempt = job["attempts"][-1] if job["attempts"] else {}
        attempt.update({"ended": iso()})
        for key, value in (("tokens", args.tokens), ("duration_s", args.duration_s), ("agent_ref", args.agent_ref)):
            if value is not None:
                attempt[key] = value
        job["summary"] = summary
        job.update(fields)
        task.touch(job)
        out: list[str] = [f"{job_id}: {status}" + (f" — {summary}" if summary else "")]
        if disputed:
            out.append(f"{disputed} disputed finding{'s' if disputed > 1 else ''}: settle "
                       f"{'them' if disputed > 1 else 'it'} (see execute.md). Read {path}.")
        code = EXIT_OK
        task.event("job.collected", job=job_id, attempt=attempt.get("n"), status=status, summary=summary,
                   tokens=attempt.get("tokens"), duration_s=attempt.get("duration_s"), disputed=disputed)
        if status == "done" and job.get("stale"):
            # [NO-STALE-CHECKS]: a writer merged while this final validation ran.
            reason = job.pop("stale")
            job["status"] = "pending"
            task.event("job.reset", job=job_id, reason=f"result not counted: {reason}", by="sae")
            after = last_round(task, "integration")
            out.append(f"{job_id} is pending again: its result does not count ({reason}). Run it again"
                       + (f" after {after}." if after else "."))
        elif status == "done" and job["kind"] in WRITER_KINDS + ("validation",):
            code = collect_checked_job(task, job_id, meta, config, out)
        elif status == "done":
            job["status"] = "done"
            if job["kind"] == "review":
                code = apply_review(task, job_id, config, out)
        elif status == "failed":
            job["status"] = "failed"
        else:
            job["status"] = "parked"
            out.append(f"Parked: {parked_reason(task, job_id)}")
            out.append(f"Decision flow: answer it, or ask the user (mode table). To add a decision job:\n"
                       f"  sae decision new {task.id} --from {job_id}")
        materialize_integration_review(task, out)
        emit(args, "\n".join(out), {"job": job_id, "status": job["status"], "summary": summary, "exit": code,
                                    "disputed": disputed, "messages": out[1:]})
    return code


def collect_checked_job(task: Task, job_id: str, meta: dict, config: dict | None, out: list[str]) -> int:
    """done writer or validation job: commits, verify re-run, scope audit, then review or merge."""
    job = task.jobs[job_id]
    workdir, _ = workspace_of(task, job_id, config)
    writer = job["kind"] in WRITER_KINDS
    new_commits: list[str] = []
    if writer and task.info.get("git"):
        # Commits since the job's first dispatch: a resumed worker may have committed earlier.
        head = (job["attempts"][0] if job["attempts"] else {}).get("head")
        if head:
            new_commits = git(workdir, "rev-list", "--reverse", f"{head}..HEAD").split()
        if meta.get("changes") == "made" and not new_commits:
            fail(EXIT_USAGE, f"{job_id} reports changes but made no commit since dispatch. Resume the worker:\n"
                             f"  sae dispatch {task.id} {job_id} --resume --reason \"commit your work\"")
    if as_list(job_meta(task, job_id).get("verify")):
        ok, command, exit_code = run_verify(task, job_id, workdir, config if config is not None else load_config())
        if not ok:
            count = 1 + sum(1 for e in task.events() if e["type"] == "job.verify_failed" and e.get("job") == job_id)
            task.event("job.verify_failed", job=job_id, command=command, exit_code=exit_code, count=count)
            limit = max_verify_failures(task.settings)
            log = task.dir / "jobs" / f"{job_id}.verify.log"
            if count >= limit:
                job["status"] = "failed"
                job["summary"] = f"verify failed {count} times (limit {limit}): {command}"
                out.append(f"{job_id}: failed — verify failed {count} times. Log: {log}")
                return EXIT_OK
            out.append(f"Verify failed ({count} of {limit}): `{command}` exit {exit_code}.\nLog: {log}\n"
                       f"Resume the same worker:\n  sae dispatch {task.id} {job_id} --resume --reason verify-failed")
            return EXIT_VERIFY
    if writer and task.info.get("git"):
        scope = [str(s) for s in as_list(job_meta(task, job_id).get("scope"))]
        first = (job["attempts"][0] if job["attempts"] else {}).get("head")
        if scope and first:
            changed = git(workdir, "diff", "--name-only", f"{first}..HEAD").splitlines()
            outside = [p for p in changed if not in_scope(p, scope)]
            if outside:
                task.event("job.scope_warning", job=job_id, files=outside)
                out.append(f"warning: {job_id} changed files outside its scope: {', '.join(outside)}")
        job["commits"] = job["commits"] + [c for c in new_commits if c not in job["commits"]]
    job["status"] = "done"
    out.extend(resolution_notes(task, job_id))
    if writer:
        return after_writer_done(task, job_id, config, out)
    close_resolved(task, [job_id], out)  # a validation job succeeds when it is collected done
    return EXIT_OK


def apply_review(task: Task, review_id: str, config: dict | None, out: list[str]) -> int:
    review = task.jobs[review_id]
    target, verdict = review.get("target"), review.get("verdict")
    model = review["attempts"][-1] if review["attempts"] else {}
    task.event("review.completed", job=review_id, target=target, round=review.get("round") or 1,
               provider=model.get("harness"), model=model.get("model"), effort=model.get("effort"), verdict=verdict)
    if target == "integration":
        return apply_integration_review(task, review_id, out)
    if target not in task.jobs:
        out.append(f"Review of {target}: {verdict}. Read {result_file(task, review_id)}.")
        return EXIT_OK
    subject = task.jobs[target]
    if verdict in ("pass", "pass-with-notes"):
        if subject["status"] == "parked":
            # [PARKED-THEN-PASSED]: a later round passed, so the park for a human decision is over.
            subject["status"] = "done"
            subject["summary"] = f"{review_id}: {verdict}"
            task.touch(subject)
            out.append(f"{target} is no longer parked: {review_id} passed.")
        return merge_job(task, target, config, out)
    subject["review_rounds"] += 1
    task.touch(subject)
    if subject["review_rounds"] >= 2:
        subject["status"] = "parked"
        subject["summary"] = f"{review_id}: changes required after two review rounds — human decision"
        out.append("\n".join([f"{target} parked: the second review round still requires changes. Ask the user. "
                               "Accept with:",
                               f"  sae merge {task.id} {target} --accept-review \"<why>\"",
                               "Or adapt the graph."]))
    else:
        out.append("\n".join([f"{target}: changes required. Add fix jobs:",
                               f"  sae job add {task.id} {target}-FIX-1 --kind implementation --fix-of {target} "
                               f"--reason \"{review_id}: changes required\"",
                               "Or accept when the mode lets you decide:",
                               f"  sae merge {task.id} {target} --accept-review \"<why>\""]))
    return EXIT_OK


def apply_integration_review(task: Task, review_id: str, out: list[str]) -> int:
    verdict = task.jobs[review_id].get("verdict")
    if verdict in POSITIVE_VERDICTS:
        out.append(f"{review_id}: {verdict}. The final validation can run.")
        return EXIT_OK
    forward = f"sae finish {task.id} --override \"<reason>\""
    if integration_parked(task):
        out.append("\n".join([f"The task is parked: {review_id} still requires changes after a fix round. "
                               "Ask the owner:",
                               "  - more fix jobs:", f"    {fix_job_command(task, review_id)}",
                               "  - or close anyway:", f"    {forward}"]))
    else:
        out.append("\n".join([f"{review_id}: changes required. Add fix jobs (sae adds the next round when "
                               "they are merged):", f"  {fix_job_command(task, review_id)}",
                               "Or, on the owner's word, close anyway:", f"  {forward}"]))
    return EXIT_OK


def cmd_merge(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        if job["kind"] not in WRITER_KINDS or fix_target(task, args.id):
            fail(EXIT_USAGE, f"{args.id} is not a writer job that merges (fix jobs merge with their target).")
        if job["merged"]:
            fail(EXIT_USAGE, f"{args.id} is already merged.")
        accepted_park = job["status"] == "parked" and args.accept_review
        if job["status"] != "done" and not accepted_park:
            fail(EXIT_USAGE, f"{args.id} is {job['status']}, not done.")
        pending_reviews = [i for i, j in task.jobs.items()
                           if j["kind"] == "review" and j.get("target") == args.id and j["status"] != "done"]
        if pending_reviews and not args.accept_review:
            fail(EXIT_GATE, f"Review pending: {', '.join(pending_reviews)}.")
        if last_verdict(task, args.id) == "changes-required" and not args.accept_review:
            fail(EXIT_GATE, f"The last review of {args.id} requires changes. Add fix jobs, or "
                            f"--accept-review \"<why>\".")
        if args.accept_review:
            task.event("decision", **{"class": "consequential", "by": "agent",
                                      "summary": f"merge {args.id} despite review: {args.accept_review}",
                                      "job": args.id})
            job["status"] = "done"
        out: list[str] = []
        code = merge_job(task, args.id, config, out)
        materialize_integration_review(task, out)
        emit(args, "\n".join(out), {"job": args.id, "exit": code, "messages": out})
    return code


def register_collect(sub, command):
    """Add the `collect` command to the parser."""
    p = command(sub, "collect", "Read a job's result file, re-run verify, then merge or add its review.",
                "Add --tokens, --duration-s and --agent-ref when your harness reports them. Exit 5: resume the same\n"
                "worker with --reason verify-failed; after the task's limit the job is failed instead (exit 0).\n"
                "Exit 4: merge conflict, sae added INTEGRATE-<ID>.",
                ["collect claims-status STATUS-API --tokens 48210 --duration-s 312 --agent-ref a1b2c3"],
                [0, 1, 2, 4, 5], cmd_collect)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--tokens", type=int)
    p.add_argument("--duration-s", type=int)
    p.add_argument("--agent-ref")


def register_merge(sub, command):
    """Add the `merge` command to the parser."""
    p = command(sub, "merge", "Merge a done writer job now; --accept-review merges despite changes-required.",
                "Normally automatic. --accept-review logs a decision event with the reason.",
                ['merge claims-status STATUS-API --accept-review "remaining finding is cosmetic"'], [0, 1, 3, 4], cmd_merge)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--accept-review", metavar="REASON")
