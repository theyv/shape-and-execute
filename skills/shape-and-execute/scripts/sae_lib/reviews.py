"""Verify re-run, collect, review rounds, merges, integration review and finish gates."""

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
    emit,
    fail,
    iso,
    read_text,
    write_atomic,
)
from .config import cfg, load_config, max_verify_failures
from .gitutil import find_root, git, run
from .graph import add_generated_job
from .markdown import split_frontmatter
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


def review_due(task: Task, job_id: str) -> bool:
    points = task.settings["review"]["points"]
    return "all-jobs" in points or ("selected-jobs" in points and task.jobs[job_id].get("review"))


def last_verdict(task: Task, target: str) -> str | None:
    verdict = None
    for job_id, job in task.jobs.items():
        if job["kind"] == "review" and job.get("target") == target and job["status"] == "done":
            verdict = job.get("verdict", verdict)
    return verdict


def merge_job(task: Task, job_id: str, config: dict | None, out: list[str]) -> int:
    """Merges a done writer job (and its fix jobs) into the task branch, or only marks it
    merged in the chain layout and without git. Returns an exit code."""
    job = task.jobs[job_id]
    group = [job_id] + [i for i, j in task.jobs.items() if j.get("fix_of") == job_id and j["status"] == "done"]
    if job["kind"] == "integration" and job.get("target") in task.jobs:
        group.append(job["target"])
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
    return EXIT_OK


def after_writer_done(task: Task, job_id: str, config: dict | None, out: list[str]) -> int:
    """A writer job is done: add its review, or merge it."""
    job = task.jobs[job_id]
    target = job.get("fix_of")
    if target:
        rounds = task.jobs[target]["review_rounds"]
        if rounds >= 1:
            review_id = f"REVIEW-{target}-{rounds + 1}"
            if review_id not in task.jobs:
                review = add_generated_job(task, review_id, "review", [job_id], "normal", target,
                                           f"round {rounds + 1} after {job_id}")
                review["round"] = rounds + 1
                out.append(f"Added {review_id}: dispatch it.")
            return EXIT_OK
        return merge_job(task, target, config, out)
    if review_due(task, job_id):
        review_id = f"REVIEW-{job_id}"
        if review_id not in task.jobs:
            add_generated_job(task, review_id, "review", [job_id], "normal", job_id, "job review is due")
        out.append(f"Added {review_id}: {job_id} merges after the review passes.")
        return EXIT_OK
    return merge_job(task, job_id, config, out)


def materialize_integration_review(task: Task, out: list[str]) -> None:
    if "integration" not in task.settings["review"]["points"] or task.phase != "executing":
        return
    if any(j["kind"] == "review" and j.get("target") == "integration" for j in task.jobs.values()):
        return
    writers = [j for j in task.jobs.values() if j["kind"] in WRITER_KINDS]
    if not writers or not all(j["merged"] for j in writers):
        return
    if any(j["status"] in ("pending", "running") and not j["final"] and j["kind"] != "review"
           for j in task.jobs.values()):
        return
    add_generated_job(task, "REVIEW-INTEGRATION", "review", [], "normal", "integration",
                      "every writer job is merged")
    out.append("Added REVIEW-INTEGRATION: review the whole change.")


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


def check_finish_gates(task: Task, with_open: bool) -> None:
    """Refuse (exit 3) before `sae finish` merges anything: running or open jobs, final validation, integration review."""
    jobs = task.jobs
    running = [i for i, j in jobs.items() if j["status"] == "running"]
    if running:
        fail(EXIT_GATE, f"Still running: {', '.join(running)}. Collect them first.")
    open_jobs = [i for i, j in jobs.items() if j["status"] in ("pending", "parked")]
    if open_jobs and not with_open:
        fail(EXIT_GATE, f"Open jobs: {', '.join(open_jobs)}. Finish them, or add --with-open when the user "
                        "accepts open items.")
    finals = [i for i, j in jobs.items() if j["final"] and j["status"] != "done"]
    if finals:
        fail(EXIT_GATE, f"The final validation {finals[0]} is not done.")
    integration = [i for i, j in jobs.items() if j["kind"] == "review" and j.get("target") == "integration"]
    if integration and jobs[integration[0]]["status"] != "done":
        fail(EXIT_GATE, f"{integration[0]} is not done.")


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
        meta, _ = split_frontmatter(text)
        status, summary, fields = interpret_result(job["kind"], meta, path)
        attempt = job["attempts"][-1] if job["attempts"] else {}
        attempt.update({"ended": iso()})
        for key, value in (("tokens", args.tokens), ("duration_s", args.duration_s), ("agent_ref", args.agent_ref)):
            if value is not None:
                attempt[key] = value
        job["summary"] = summary
        job.update(fields)
        task.touch(job)
        out: list[str] = [f"{job_id}: {status}" + (f" — {summary}" if summary else "")]
        code = EXIT_OK
        task.event("job.collected", job=job_id, attempt=attempt.get("n"), status=status, summary=summary,
                   tokens=attempt.get("tokens"), duration_s=attempt.get("duration_s"))
        if status == "done" and job["kind"] in WRITER_KINDS + ("validation",):
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
            out.append("Decision flow: answer it, or sae decision new, or ask the user (mode table).")
        materialize_integration_review(task, out)
        emit(args, "\n".join(out), {"job": job_id, "status": job["status"], "summary": summary, "exit": code,
                                    "messages": out[1:]})
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
            fail(EXIT_USAGE, f"{job_id} reports changes but made no commit since dispatch. Resume the worker: "
                             f"commit your work (sae dispatch {task.id} {job_id} --resume --reason \"commit your work\").")
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
            out.append(f"Verify failed ({count} of {limit}): `{command}` exit {exit_code}. Log: {log}\n"
                       f"Resume the same worker: sae dispatch {task.id} {job_id} --resume --reason verify-failed")
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
    if writer:
        return after_writer_done(task, job_id, config, out)
    return EXIT_OK


def apply_review(task: Task, review_id: str, config: dict | None, out: list[str]) -> int:
    review = task.jobs[review_id]
    target, verdict = review.get("target"), review.get("verdict")
    model = review["attempts"][-1] if review["attempts"] else {}
    task.event("review.completed", job=review_id, target=target, provider=model.get("harness"),
               model=model.get("model"), verdict=verdict)
    if target not in task.jobs:
        out.append(f"Review of {target}: {verdict}. Read {result_file(task, review_id)}.")
        return EXIT_OK
    subject = task.jobs[target]
    if verdict in ("pass", "pass-with-notes"):
        return merge_job(task, target, config, out)
    subject["review_rounds"] += 1
    task.touch(subject)
    if subject["review_rounds"] >= 2:
        subject["status"] = "parked"
        subject["summary"] = f"{review_id}: changes required after two review rounds — human decision"
        out.append(f"{target} parked: the second review round still requires changes. Ask the user; "
                   f"accept with sae merge {task.id} {target} --accept-review \"<why>\", or adapt the graph.")
    else:
        out.append(f"{target}: changes required. Add fix jobs: sae job add {task.id} {target}-FIX-1 --kind "
                   f"implementation --fix-of {target} --reason \"{review_id}: changes required\"\n"
                   f"or accept when the mode lets you decide: sae merge {task.id} {target} --accept-review \"<why>\"")
    return EXIT_OK


def cmd_merge(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        if job["kind"] not in WRITER_KINDS or job.get("fix_of"):
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
