"""Dispatch prompts and the external review command (model and effort always explicit)."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from .common import ASK_CLASSES, PARK_CLASSES, SKILL_DIR, WRITER_KINDS, read_text, sae_prefix
from .config import cfg
from .markdown import split_frontmatter
from .tasks import Task, job_file, result_file, tasks_dir
from .workspaces import job_branch, workspace_of, workspace_owner


def artifact_language(task: Task, config: dict) -> str:
    profile = read_text(tasks_dir(task.root) / "repo" / "profile.md")
    pin = split_frontmatter(profile)[0].get("artifact_language") if profile else None
    return pin or cfg(config, "language.artifacts")


def interaction_lines(mode: str) -> list[str]:
    escalate = ASK_CLASSES[mode] + PARK_CLASSES.get(mode, ())
    modes_ref = SKILL_DIR / "references" / "interaction-modes.md"
    if escalate:
        return [f"Interaction mode: {mode} — escalate decisions of these classes:",
                f"  {', '.join(escalate)} ({modes_ref})"]
    return [f"Interaction mode: {mode} — decide every decision class yourself ({modes_ref})"]


def hard_stop_lines() -> list[str]:
    return ["Hard stops — read before you start, escalate every one:",
            f"  {SKILL_DIR / 'references' / 'interaction-modes.md'}, section \"Hard stops\""]


def pointer(label: str, path: Path) -> str | None:
    return f"{label}{path}" if path.exists() else None


def diff_command(task: Task, job_id: str, config: dict | None) -> str | None:
    job = task.jobs[job_id]
    if not task.info.get("git") or not job["attempts"]:
        return None
    start = job["attempts"][0].get("head")
    if task.uses_worktrees:
        end = job_branch(task, workspace_owner(task, job_id))
    else:
        commits = list(job["commits"])
        for other in task.jobs.values():
            if other.get("fix_of") == job_id:
                commits += other["commits"]
        end = commits[-1] if commits else None
    if not start or not end:
        return None
    return f"git -C {shlex.quote(str(task.root))} diff {start}..{end}"


def build_prompt(task: Task, job_id: str, workdir: Path, branch: str | None, model: dict,
                 config: dict, external: bool = False) -> str:
    job = task.jobs[job_id]
    kind = job["kind"]
    d = task.dir
    skill = SKILL_DIR
    roles = skill / "references" / "roles"
    protocol = {
        "implementation": "worker.md", "validation": "worker.md", "integration": "integration-worker.md",
        "research": "research-worker.md", "planning": "planner.md", "review": "reviewer.md",
        "decision": "decision-worker.md",
    }[kind]
    who = {"review": "a reviewer", "decision": "a decision worker", "research": "a research worker",
           "planning": "the planner"}.get(kind, "a worker")
    lines: list[str | None] = [
        f"You are {who} for the shape-and-execute skill. Follow your protocol:",
        f"  {roles / protocol}",
        f"Task: {task.id} · Job: {job_id} ({kind}, {job['difficulty']})",
    ]
    spec, intent = d / "specs.md", d / "intent.md"
    spec_or_intent = (pointer("Spec — read the parts your job covers: ", spec) if spec.exists()
                      else pointer("Intent — acceptance criteria:          ", intent))
    profile = tasks_dir(task.root) / "repo" / "profile.md"
    if kind in ("implementation", "integration", "validation"):
        lines += [
            pointer("Job file — what to achieve:            ", job_file(task, job_id)),
            pointer("Shared brief — read first:             ", d / "brief.md"),
            spec_or_intent,
            pointer("Repo profile — validation, hot files:  ", profile),
        ]
        if job.get("fix_of"):
            target = job["fix_of"]
            reviews = sorted((d / "reviews").glob(f"REVIEW-{target}*.md")) if (d / "reviews").is_dir() else []
            lines.append(f"Fixes job {target}" + (f" — review to address: {reviews[-1]}" if reviews else ""))
        if kind == "integration" and job.get("target"):
            lines.append(f"Merge in progress in the workdir: {job_branch(task, job['target'])} into the task "
                         f"branch. Resolve the conflicts, keep both jobs' intent, commit the merge.")
        if kind == "validation":
            lines += ["Workdir — read-only; run every command here:", f"  {workdir}"]
        else:
            lines += ["Workdir — work only here, absolute paths, run every command here:", f"  {workdir}"]
            if branch:
                lines += [f"Branch: {branch} — commit here; never push; never switch branches.",
                          f"Commit format — read before your first commit: {skill / 'references' / 'commit-message.md'}",
                          f"Commit trailers: Task: {task.id} · Job: {job_id} · Model: {model['model']}"]
            else:
                lines.append("No git: change files directly; never delete a file that existed before the task "
                             "unless the spec asks for it.")
        result_template = "job-result.md"
    elif kind in ("research", "planning"):
        lines += [
            pointer("Job file — what to find out:           " if kind == "research" else
                    "Job file — what to plan:               ", job_file(task, job_id)),
            pointer("Intent:                                ", intent),
            pointer("Spec:                                  ", spec),
            pointer("Repo profile:                          ", profile),
        ]
        if kind == "planning":
            lines += [f"Task folder — write the brief, the plan and job files only here: {d}",
                      f"Register jobs and lint with sae: {sae_prefix()} job add | check {task.id}"]
        lines += ["Workdir — read-only; run every command here:", f"  {task.root}"]
        result_template = "research-report.md" if kind == "research" else "job-result.md"
    elif kind == "review":
        target = job.get("target")
        lines.append(f"Target: {target}")
        if target == "spec":
            lines += [pointer("Intent:                                ", intent),
                      pointer("Spec — under review:                   ", spec)]
            spec_text = read_text(spec, "")
            for name in sorted(set(re.findall(r"research/([A-Za-z0-9-]+)\.md", spec_text))):
                lines.append(pointer("Research report linked by the spec:    ", d / "research" / f"{name}.md"))
        elif target == "plan":
            lines += [pointer("Intent:                                ", intent),
                      pointer("Spec:                                  ", spec),
                      pointer("Brief:                                 ", d / "brief.md"),
                      pointer("Plan:                                  ", d / "plan.md"),
                      f"Job files:                             {d / 'jobs'}",
                      f"Graph (needs, kinds, difficulty):      {sae_prefix()} status {task.id}"]
        elif target == "integration":
            base = (task.info.get("base") or {}).get("commit")
            lines += [pointer("Intent:                                ", intent),
                      pointer("Spec:                                  ", spec)]
            if base and task.info.get("branch"):
                lines.append(f"Diff — the whole change: git -C {shlex.quote(str(task.root))} diff {base}..{task.info['branch']}")
        else:
            lines += [pointer("Job file:                              ", job_file(task, target)),
                      pointer("Result:                                ", result_file(task, target)),
                      spec_or_intent]
            diff = diff_command(task, target, config)
            if diff:
                lines.append(f"Diff: {diff}")
            target_dir, _ = workspace_of(task, target, config)
            if target_dir != task.root and target_dir.exists():
                lines.append(f"Job worktree (read only): {target_dir}")
            if job.get("round", 1) > 1:
                earlier = sorted((d / "reviews").glob(f"REVIEW-{target}*.md"))
                if earlier:
                    lines.append(f"Second round — check only the findings of: {earlier[-1]}")
        lines += ["Workdir — read-only; run every command here:", f"  {task.root}"]
        result_template = "review.md"
    else:  # decision
        target = job.get("target")
        lines += [pointer("Job file — the question:               ", job_file(task, job_id))]
        if target in task.jobs:
            lines.append(pointer("Decision request (section \"Decision request\"): ", result_file(task, target)))
        lines += [spec_or_intent, pointer("Brief:                                 ", d / "brief.md"),
                  "Workdir — read-only; run every command here:", f"  {task.root}"]
        result_template = "decision.md"
    if kind != "review":
        lines += interaction_lines(task.settings["interaction"])
        lines += hard_stop_lines()
    lines.append(f"Artifact language: {artifact_language(task, config)}"
                 + (" (code comments follow the repository's existing convention)." if kind in WRITER_KINDS else "."))
    if kind not in ("review",):
        lines.append(f"Out-of-scope problems: {sae_prefix()} finding new \"<title>\" --type defect|friction|follow-up "
                     f"--confidence high|medium|low --source {task.id}/{job_id}")
    result = result_file(task, job_id)
    if external:
        lines += [f"Do not write files. Reply with the review only, in the format of {skill / 'templates' / result_template}",
                  "  (frontmatter with target and verdict first)."]
    else:
        lines += [f"Write your result to: {result}", f"  (template: {skill / 'templates' / result_template})",
                  "When you stop, reply with the result file path only."]
    return "\n".join(line for line in lines if line)


def external_review_command(task: Task, job_id: str, model: dict, prompt: str) -> str:
    result = result_file(task, job_id)
    result.parent.mkdir(parents=True, exist_ok=True)
    q = shlex.quote
    if model["harness"] == "codex":
        return (f"rm -f {q(str(result))} && codex exec -m {q(model['model'])} "
                f"-c model_reasoning_effort={q(model['effort'])} -s read-only "
                f"-C {q(str(task.root))} -o {q(str(result))} --ephemeral {q(prompt)} < /dev/null")
    return (f"cd {q(str(task.root))} && claude -p {q(prompt)} --model {q(model['model'])} "
            f"--effort {q(model['effort'])} --permission-mode dontAsk "
            f"--allowedTools {q('Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(git show *)')} "
            f"> {q(str(result))}")
