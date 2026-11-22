"""Jobs on the harness that does not orchestrate: the launch COMMAND, its record, the missing-CLI
check, the fallback rule, routing exceptions and `sae job park`.

[WRITER-COMMAND] Every job routed to the other harness gets a COMMAND: a review runs read-only (as
before), every other job runs without a sandbox ([DECISION-YOLO-WRITERS]). The COMMAND keeps the
harness's machine-readable output next to the result file; `sae collect` reads its tokens.
[LAUNCH-RECORD] Each COMMAND attempt stores `launch`: harness, model, effort, the command with
placeholders instead of the prompt and paths, and the request (`bypass requested` or
`read-only requested`), never the effective permissions.
[HARNESS-FALLBACK] `sae dispatch` refuses before any state change when the other harness's CLI is
not on the PATH, and prints the fallback command with the rule for the case at hand
([DECISION-FALLBACK-BY-MODE]). The fallback command's `--reason` carries the requested route in a
fixed format; the dispatch that runs it records a routing exception from there.
Every dispatch moves an existing result aside (`tasks.empty_result_slot`), so `sae collect` sees
only a result the current attempt wrote; the retry's prompt points to the moved file.
"""

from __future__ import annotations

import re
import shlex
import shutil
from pathlib import Path

from .common import EXIT_OK, EXIT_USAGE, WRITER_KINDS, SaeError, changed_by, emit, fail, iso, sae_prefix
from .gitutil import find_root
from .prompts import CLAUDE_RESULT_TEXT, review_output_file, review_output_tokens
from .routing import PLANNER_ID, job_context, override_key, resolve_model
from .tasks import Task, open_task, result_file

BYPASS_REQUESTED = "bypass requested"
READ_ONLY_REQUESTED = "read-only requested"
CODEX_BYPASS_FLAG = "--dangerously-bypass-approvals-and-sandbox"
CODEX_NO_GIT_FLAG = "--skip-git-repo-check"  # codex exec refuses a folder outside a Git repository without it
CLAUDE_BYPASS_MODE = "bypassPermissions"
CLAUDE_REVIEW_TOOLS = "Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(git show *)"
# [LAUNCH-RECORD] what stands in the recorded command for the prompt and the private paths
PLACEHOLDERS = {"prompt": "<prompt>", "workdir": "<workdir>", "task_folder": "<task-folder>",
                "output": "<output>", "result": "<result>"}
# The fixed `--reason` format of a fallback command (brief "How"): the requested route, then why.
FALLBACK_REASON = "harness fallback: requested {harness} · {model} · {effort}; {why}"
FALLBACK_REASON_RE = re.compile(r"^harness fallback: requested (\S+) · (\S+) · (\S+); (.*)$", re.S)


def is_command_job(task: Task, harness: str) -> bool:
    """A job runs through a COMMAND when it routes to another harness than the orchestrator's."""
    return harness != task.info.get("orchestrator_harness")


# ------------------------------------------------------------------ the COMMAND

def command_line(harness: str, review: bool, model: str, effort: str, prompt: str, workdir: str,
                 task_folder: str, output: str, result: str, git: bool = True) -> str:
    """One shell line from shell-ready words (quoted values, or the placeholders of the record).
    A review: read-only, its review text goes to the result file. Any other job: no sandbox; the
    worker writes its own result file; a Codex worker in a task without git skips the repo check."""
    q = shlex.quote
    if review:
        clean = f"rm -f {result} {output}"
        if harness == "codex":
            return (f"{clean} && codex exec -m {model} -c model_reasoning_effort={effort} -s read-only "
                    f"-C {workdir} -o {result} --ephemeral --json {prompt} < /dev/null > {output}")
        return (f"cd {workdir} && {clean} && claude -p {prompt} --output-format json --model {model} "
                f"--effort {effort} --permission-mode dontAsk --allowedTools {q(CLAUDE_REVIEW_TOOLS)} "
                f"> {output} && python3 -c {q(CLAUDE_RESULT_TEXT)} {output} > {result}")
    if harness == "codex":
        no_git = "" if git else f"{CODEX_NO_GIT_FLAG} "
        return (f"rm -f {output} && codex exec -m {model} -c model_reasoning_effort={effort} {CODEX_BYPASS_FLAG} "
                f"{no_git}-C {workdir} --ephemeral --json {prompt} < /dev/null > {output}")
    # --add-dir: the worker writes its result into the task folder, outside a job worktree
    return (f"cd {workdir} && rm -f {output} && claude -p {prompt} --output-format json --model {model} "
            f"--effort {effort} --permission-mode {CLAUDE_BYPASS_MODE} --add-dir {task_folder} > {output}")


def launch_command(task: Task, job_id: str, model: dict, prompt: str, workdir: Path) -> str:
    """The COMMAND to print: printf restores the literal newlines of the prompt."""
    q = shlex.quote
    result = result_file(task, job_id)
    result.parent.mkdir(parents=True, exist_ok=True)
    escaped = prompt.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
    review = task.jobs[job_id]["kind"] == "review"
    return command_line(model["harness"], review, q(model["model"]),
                        q(model["effort"]), prompt='"$(printf %b ' + q(escaped) + ')"', workdir=q(str(workdir)),
                        task_folder=q(str(task.dir)),
                        output=q(str(review_output_file(task, job_id, model["harness"]))), result=q(str(result)),
                        git=review or bool(task.info.get("git")))


def launch_record(task: Task, job_id: str, model: dict) -> dict:
    """[LAUNCH-RECORD] What the attempt stores: no prompt text and no absolute path."""
    review = task.jobs[job_id]["kind"] == "review"
    q = shlex.quote
    return {"harness": model["harness"], "model": model["model"], "effort": model["effort"],
            "command": command_line(model["harness"], review, q(model["model"]), q(model["effort"]), **PLACEHOLDERS,
                                    git=review or bool(task.info.get("git"))),
            "request": READ_ONLY_REQUESTED if review else BYPASS_REQUESTED}


def how_to_run_line(task: Task, job_id: str) -> str:
    """Printed with every COMMAND (audit proposal 1, point 1)."""
    return (f"Run it in a shell in the background, not as a subagent. When it exits: sae collect {task.id} {job_id} "
            "(no --tokens: sae reads them from the output the COMMAND keeps).")


def command_tokens(task: Task, job_id: str, attempt: dict) -> int | None:
    """[REVIEW-TOKENS] for every COMMAND attempt: the tokens in the output it kept. An attempt
    without a launch record is a COMMAND attempt when it is a review in the other harness (older
    records)."""
    harness = attempt.get("harness")
    if harness not in ("codex", "claude"):
        return None
    if not attempt.get("launch") and not (task.jobs[job_id]["kind"] == "review"
                                         and harness != task.info.get("orchestrator_harness")):
        return None
    return review_output_tokens(review_output_file(task, job_id, harness), harness)


# ------------------------------------------------------------------ fallback

def fallback_reason(route: dict, why: str) -> str:
    return FALLBACK_REASON.format(harness=route["harness"], model=route["model"], effort=route["effort"], why=why)


def parse_fallback_reason(reason: str | None) -> dict | None:
    """The requested route of a fallback dispatch, read from its `--reason`; None for any other reason."""
    found = FALLBACK_REASON_RE.match((reason or "").strip())
    if not found:
        return None
    harness, model, effort, why = found.groups()
    return {"harness": harness, "model": model, "effort": effort, "why": why.strip()}


def fallback_command(task: Task, job_id: str, kind: str, route: dict, why: str, resume: bool) -> str:
    """`sae dispatch` on the orchestrator's harness; `--provider` for a review, else `--harness`."""
    flag = "--provider" if kind == "review" else "--harness"
    reason = fallback_reason(route, why).replace('"', "'")
    return (f"{sae_prefix()} dispatch {task.id} {job_id} {flag} {task.info['orchestrator_harness']}"
            + (" --resume" if resume else "") + f" --reason \"{reason}\"")


def fallback_rule(task: Task, job_id: str, kind: str, status: str, harness: str, command: str, why: str) -> list[str]:
    """[HARNESS-FALLBACK] Only the branch of the rule that applies: by job kind, job status
    (`pending` or `running` can be parked; a done, failed or parked job stays as it is) and the
    task's interaction mode. `command` is the fallback command printed above the rule."""
    mode = task.settings["interaction"]
    if kind == "review":
        return [f"Rule (mode {mode}): a review falls back in every mode. Run it now; sae records the routing exception."]
    if mode == "full-auto":
        return ["Rule (mode full-auto): run it now; sae records the routing exception."]
    orchestrator = task.info["orchestrator_harness"]
    article = "an" if kind[0] in "aeiou" else "a"
    lines = [f"Rule (mode {mode}): {article} {kind} job falls back only on the owner's yes."]
    steps = []
    if status in ("pending", "running"):
        steps.append(f"sae job park {task.id} {job_id} --reason \"harness fallback: {why}\" "
                     "(it leaves the ready queue and frees its writer slot)")
    else:
        lines[0] += f" The job stays {status}; do not park it."
    steps += [f"sae ask {task.id} \"Run {job_id} on {orchestrator} instead of {harness}? {why}\" --job {job_id}",
              "Continue with independent work.",
              f"On the owner's yes: sae log {task.id} decision \"harness fallback: {job_id}: <answer>\" --by human "
              f"--job {job_id}, then run:"]
    lines += [f"  {n}. {step}" for n, step in enumerate(steps, 1)]
    resumed = command if " --resume " in command else command.replace(" --reason ", " --resume --reason ", 1)
    lines.append(f"     {resumed}")
    return lines


def refuse_missing_cli(task: Task, job_id: str, config: dict, harness_flag: str | None, provider_flag: str | None,
                       resume: bool) -> None:
    """[HARNESS-FALLBACK] Refuses the dispatch when the job routes to the other harness and its CLI
    is not on the PATH. Called before the due review is added, the workspace is prepared or the
    attempt is appended, so nothing changes. The route is read without a Codex catalog lookup."""
    orchestrator = task.info.get("orchestrator_harness")
    route = resolve_model(task, job_id, config, harness=harness_flag, provider=provider_flag, exact=False)
    if not orchestrator or route["harness"] == orchestrator or shutil.which(route["harness"]):
        return
    kind = job_context(task, job_id)["kind"]
    status = task.jobs[job_id]["status"] if job_id in task.jobs else "pending"
    why = f"{route['harness']} CLI not on PATH"
    command = fallback_command(task, job_id, kind, route, why, resume)
    fail(EXIT_USAGE, "\n".join(
        [f"{job_id} routes to {route['harness']}, but the {route['harness']} CLI is not on the PATH. "
         "Nothing was dispatched and nothing changed.", "Fallback command:", command]
        + fallback_rule(task, job_id, kind, status, route["harness"], command, why)))


def if_it_fails(task: Task, job_id: str, model: dict) -> tuple[str, list[str]]:
    """The IF IT FAILS command of a COMMAND (the job is running: it resumes) and its rule."""
    kind = task.jobs[job_id]["kind"]
    why = ("provider failed: <exit code or empty result>" if kind == "review"
           else "COMMAND failed: <exit code or missing result>")
    command = fallback_command(task, job_id, kind, model, why, resume=True)
    return command, fallback_rule(task, job_id, kind, "running", model["harness"], command, why)


# ------------------------------------------------------------------ routing exceptions

def route_of(res: dict) -> dict:
    return {"harness": res["harness"], "model": res["model"], "effort": res["effort"]}


def routing_exception(task: Task, job_id: str, config: dict, model: dict, harness_flag: str | None,
                      provider_flag: str | None, reason: str | None) -> dict | None:
    """A dispatch on another harness than routing chose: `{requested, actual, reason}`, else None.
    A fallback names the requested route in its `--reason` (also a route requested only by a
    dispatch flag); another flag dispatch compares with what routing alone chooses."""
    parsed = parse_fallback_reason(reason)
    if parsed:
        why = parsed.pop("why")
        requested = parsed
    elif harness_flag or provider_flag:
        try:
            natural = resolve_model(task, job_id, config, exact=False)
        except SaeError:
            return None
        requested = route_of(natural)
        why = (reason or "").strip() or f"--{'provider' if provider_flag else 'harness'} {provider_flag or harness_flag}"
    else:
        return None
    if requested["harness"] == model["harness"]:
        return None
    return {"requested": requested, "actual": route_of(model), "reason": why}


def route_text(route: dict) -> str:
    return " · ".join(str(route.get(k)) for k in ("harness", "model", "effort"))


def exception_text(exception: dict) -> str:
    return (f"routing exception: requested {route_text(exception['requested'])}, ran "
            f"{route_text(exception['actual'])} — {exception['reason']}")


def routing_exceptions(task: Task) -> list[dict]:
    """Every recorded routing exception: `{job, attempt, requested, actual, reason}`, in job order."""
    found = []
    for job_id, job in task.jobs.items():
        for n, attempt in enumerate(job["attempts"], 1):
            exception = attempt.get("routing_exception")
            if exception:
                found.append({"job": job_id, "attempt": attempt.get("n", n), **exception})
    return found


def exception_report_lines(task: Task) -> list[str]:
    """The final report's section ([HARNESS-FALLBACK]); empty without exceptions."""
    found = routing_exceptions(task)
    if not found:
        return []
    return ["", "## Routing exceptions"] + [
        f"- {e['job']} attempt {e['attempt']}: requested {route_text(e['requested'])}, ran {route_text(e['actual'])}. "
        f"Reason: {e['reason']}" for e in found]


# ------------------------------------------------------------------ bypass line

def bypass_jobs(task: Task) -> list[str]:
    """Non-review jobs that start, or started, on the other harness: an override with the other
    harness (routing itself keeps them on the orchestrator) or an attempt with a bypass request."""
    orchestrator = task.info.get("orchestrator_harness")
    if not orchestrator:
        return []
    overrides = task.info.get("overrides") or {}
    found = []
    for job_id, job in task.jobs.items():
        if job["kind"] == "review":
            continue
        harness = (overrides.get(override_key(task, job_id)) or {}).get("harness")
        if (harness and harness != orchestrator) or any(
                (a.get("launch") or {}).get("request") == BYPASS_REQUESTED for a in job["attempts"]):
            found.append(job_id)
    planned = (overrides.get(PLANNER_ID) or {}).get("harness")
    if PLANNER_ID not in task.jobs and planned and planned != orchestrator:
        found.append(PLANNER_ID)
    return found


def bypass_line(task: Task) -> str | None:
    """[NO-SANDBOX-VISIBLE] The one `sae status` line when the task sends a non-review job to the
    other harness; None otherwise. Reads only."""
    jobs = bypass_jobs(task)
    if not jobs:
        return None
    return (f"Bypass: jobs on the other harness start with a bypass request (no sandbox, no approvals): "
            f"{', '.join(jobs)}")


# ------------------------------------------------------------------ sae job park

def cmd_job_park(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        reason = (args.reason or "").strip()
        if not reason:
            fail(EXIT_USAGE, "--reason is required.")
        if job["kind"] == "review":
            fail(EXIT_USAGE, f"{args.id} is a review: a review falls back in every mode. Run the fallback command "
                             "that sae dispatch printed.")
        if job["status"] not in ("pending", "running"):
            fail(EXIT_USAGE, f"{args.id} is {job['status']}; sae job park parks a pending job, or a running one "
                             "whose COMMAND failed.")
        was = job["status"]
        attempt = job["attempts"][-1] if was == "running" and job["attempts"] else None
        if attempt is not None and not attempt.get("ended"):
            attempt["ended"] = iso()  # the failed COMMAND's attempt ends here
        job["status"] = "parked"
        job["summary"] = reason
        task.touch(job)
        task.event("job.parked", job=args.id, was=was, attempt=attempt.get("n") if attempt else None,
                   reason=reason, by=changed_by())
        freed = " and frees its writer slot" if was == "running" and job["kind"] in WRITER_KINDS else ""
        emit(args, f"{args.id} is parked: {reason}\nIt leaves the ready queue{freed}. On the owner's yes, run the "
                   "fallback command with --resume.",
             {"job": args.id, "status": "parked", "was": was, "reason": reason})
    return EXIT_OK


def register_job_park(job_sub, command) -> None:
    """Add `sae job park` to the `job` command group."""
    p = command(job_sub, "park", "Park a job that waits for the owner's yes to a harness fallback.",
                "For the rule that sae dispatch prints when the other harness cannot run a job: a pending job, or a\n"
                "running one whose COMMAND failed (its attempt ends). The parked job leaves the ready queue and frees\n"
                "its writer slot; sae status shows the reason. The owner's yes runs the printed fallback command with\n"
                "--resume. Reviews are never parked for this: they fall back in every mode.",
                ['job park claims-status STATUS-API --reason "harness fallback: codex CLI not on PATH"'], [0, 1],
                cmd_job_park)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--reason", required=True, help='"harness fallback: <why>"; sae status shows it')
