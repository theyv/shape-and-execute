"""Dispatch prompts and the external review command (model and effort always explicit)."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Callable

from .common import ASK_CLASSES, PARK_CLASSES, SKILL_DIR, WRITER_KINDS, in_scope, read_text, sae_prefix
from .config import cfg
from .findings import ADR_INDEX, adr_folders, adr_pointer_records
from .gitutil import git
from .graph import fix_target, review_rounds
from .markdown import split_frontmatter
from .routing import job_context
from .tasks import Task, as_list, job_file, job_meta, result_file, tasks_dir
from .workspaces import job_branch, workspace_of, workspace_owner


def profile_meta(task: Task) -> dict:
    profile = read_text(tasks_dir(task.root) / "repo" / "profile.md")
    return split_frontmatter(profile)[0] if profile else {}


def artifact_language(task: Task, config: dict) -> str:
    return profile_meta(task).get("artifact_language") or cfg(config, "language.artifacts")


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


def diff_span(task: Task, job_id: str) -> tuple[str, str] | None:
    """The start and end of a job's diff: its first attempt's head and its branch (or last commit)."""
    job = task.jobs[job_id]
    if not task.info.get("git") or not job["attempts"]:
        return None
    start = job["attempts"][0].get("head")
    if task.uses_worktrees:
        end = job_branch(task, workspace_owner(task, job_id))
    else:
        commits = list(job["commits"])
        for other_id, other in task.jobs.items():
            if fix_target(task, other_id) == job_id:
                commits += other["commits"]
        end = commits[-1] if commits else None
    return (start, end) if start and end else None


def diff_command(task: Task, job_id: str, config: dict | None) -> str | None:
    span = diff_span(task, job_id)
    return f"git -C {shlex.quote(str(task.root))} diff {span[0]}..{span[1]}" if span else None


POINTER_LIMIT = 10  # [POINTER-LIMIT] record lines; directory lines do not count
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")


def path_tokens(text: str) -> list[str]:
    """The relative paths a text names word for word: words with a `/`, never `..`."""
    tokens = (t.rstrip(".") for t in re.findall(r"(?<![\w./-])[\w.-]+(?:/[\w.-]+)+/?", text))
    return [t for t in tokens if ".." not in t.split("/")]


def guarded_paths(task: Task, job_id: str) -> tuple[list[str], Callable[[str], bool]]:
    """The paths a job works on and the test of a record's path entry against them
    ([DECISION-MATCH]): a review on the diff, a worker on `scope`, else on its job file."""
    job = task.jobs[job_id]
    if job["kind"] == "review":
        target, span = job.get("target"), None
        if target == "integration":  # the whole task diff
            base, branch = (task.info.get("base") or {}).get("commit"), task.info.get("branch")
            span = (base, branch) if base and branch else None
        elif target in task.jobs:
            span = diff_span(task, target)
        changed = []
        if span and task.info.get("git"):
            changed = git(task.root, "diff", "--name-only", f"{span[0]}..{span[1]}", check=False).splitlines()
        return changed, lambda entry: any(in_scope(f, [entry]) for f in changed)
    scope = [str(s).strip("`").strip() for s in as_list(job_meta(task, job_id).get("scope"))]
    if scope:  # an entry inside the scope, or the scope inside a folder entry
        return scope, lambda entry: any(in_scope(entry, [s]) or in_scope(s, [entry]) for s in scope)
    named = path_tokens(read_text(job_file(task, job_id), "") or "")
    # the job file names the entry, a path inside a folder entry, or the entry's folder
    return named, lambda entry: any(in_scope(t, [entry]) or t.rstrip("/") == entry.rpartition("/")[0]
                                    for t in named)


def guard_lines(task: Task, job_id: str, checkout: Path) -> list[str]:
    """[WORKER-POINTERS], [REVIEW-POINTERS], [DIR-POINTERS]: the index lines of the records that
    guard the job's paths, at most POINTER_LIMIT, then the AGENTS.md / CLAUDE.md files in the
    folders of those paths below the repository root. Links open from `checkout`."""
    if task.jobs[job_id]["kind"] not in ("implementation", "integration", "validation", "review"):
        return []
    paths, guards = guarded_paths(task, job_id)
    if not paths:
        return []
    hits = [(folder, line) for folder, line, entries in adr_pointer_records(checkout, profile_meta(task))
            if any(guards(entry) for entry in entries)]
    lines = []
    if hits:
        lines += ["Decision records that guard these paths — open the ones your work touches:",
                  *(line for _, line in hits[:POINTER_LIMIT])]
        rest = hits[POINTER_LIMIT:]
        if rest:
            indexes = dict.fromkeys(f"{folder}/{ADR_INDEX}" for folder, _ in rest)
            lines.append(f"+{len(rest)} more, see {', '.join(indexes)}")
    folders = []
    for path in paths:
        parts = path.strip("/").split("/")
        literal = next((i for i, part in enumerate(parts) if re.search(r"[*?\[]", part)), len(parts))
        folders += ["/".join(parts[:i]) for i in range(1, literal + 1)]
    files = [f"{folder}/{name}" for folder in dict.fromkeys(folders) for name in INSTRUCTION_FILES
             if (checkout / folder / name).is_file()]
    if files:
        lines += ["Directory instructions for these paths — read them:", *(f"- {f}" for f in files)]
    return lines


def index_lines(task: Task) -> list[str]:
    """[INDEX-POINTER]: the index.md of each ADR folder that has one (planner, decision worker)."""
    return [f"Decision-record index:                 {task.root / folder / ADR_INDEX}"
            for folder in adr_folders(task.root, profile_meta(task)) if (task.root / folder / ADR_INDEX).is_file()]


def earlier_round(task: Task, review_id: str) -> str | None:
    """The previous round of a review, or None for round 1."""
    rounds = review_rounds(task, task.jobs[review_id].get("target"))
    index = rounds.index(review_id) if review_id in rounds else 0
    return rounds[index - 1] if index > 0 else None


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
        f"Task: {task.id} · Job: {job_id} ({kind}, {job_context(task, job_id)['difficulty']})",
    ]
    spec, intent = d / "specs.md", d / "intent.md"
    spec_pointer = pointer("Spec — read the parts your job covers: ", spec)
    profile = tasks_dir(task.root) / "repo" / "profile.md"
    if kind in ("implementation", "integration", "validation"):
        lines += [
            pointer("Job file — what to achieve:            ", job_file(task, job_id)),
            pointer("Shared brief — read first:             ", d / "brief.md"),
            spec_pointer,
            pointer("Repo profile — validation, hot files:  ", profile),
        ]
        if job.get("fix_of"):
            target = job["fix_of"]
            if fix_target(task, job_id):
                done = [r for r in review_rounds(task, target) if task.jobs[r]["status"] == "done"]
                lines.append(f"Fixes job {target}" + (f" — review to address: {result_file(task, done[-1])}"
                                                      if done else ""))
            elif target in task.jobs:
                lines.append(f"Fixes findings of {target} — review to address: {result_file(task, target)}")
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
            lines += index_lines(task)
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
            branch = task.info.get("branch")
            git_c = f"git -C {shlex.quote(str(task.root))}"
            previous = earlier_round(task, job_id)
            since = job.get("since")
            if previous and job.get("limit") == "changes":
                lines.append(f"Round {job.get('round')} after a late merge — review only the changes since {previous}.")
                if since and branch:
                    lines.append(f"Diff — the new changes: {git_c} diff {since}..{branch}")
            elif previous:
                lines.append(f"Round {job.get('round')} — check only the findings of: {result_file(task, previous)}")
                if since and branch:
                    lines.append(f"Diff — the fixes: {git_c} diff {since}..{branch}")
            elif base and branch:
                lines.append(f"Diff — the whole change: {git_c} diff {base}..{branch}")
        else:
            lines += [pointer("Job file:                              ", job_file(task, target)),
                      pointer("Result:                                ", result_file(task, target)),
                      spec_pointer]
            diff = diff_command(task, target, config)
            if diff:
                lines.append(f"Diff: {diff}")
            target_dir, _ = workspace_of(task, target, config)
            if target_dir != task.root and target_dir.exists():
                lines.append(f"Job worktree (read only): {target_dir}")
            previous = earlier_round(task, job_id)
            if previous:
                lines.append(f"Round {job.get('round')} — check only the findings of: {result_file(task, previous)}")
        lines += ["Workdir — read-only; run every command here:", f"  {task.root}"]
        result_template = "review.md"
    else:  # decision
        target = job.get("target")
        lines += [pointer("Job file — the question:               ", job_file(task, job_id))]
        if target in task.jobs:
            lines.append(pointer("Decision request (section \"Decision request\"): ", result_file(task, target)))
        lines += [spec_pointer, pointer("Brief:                                 ", d / "brief.md"),
                  *index_lines(task), "Workdir — read-only; run every command here:", f"  {task.root}"]
        result_template = "decision.md"
    lines += guard_lines(task, job_id, task.root if kind == "review" else workdir)
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


# [REVIEW-TOKENS]: the COMMAND keeps the harness's machine-readable output here, next to the result file.
REVIEW_OUTPUT_SUFFIX = {"codex": ".codex.jsonl", "claude": ".claude.json"}
# The Claude COMMAND writes the review text (`result` of the JSON output) to the result file.
CLAUDE_RESULT_TEXT = ("import json, sys; text = json.load(open(sys.argv[1]))['result']; "
                      "sys.stdout.write(text if text.endswith('\\n') else text + '\\n')")


def review_output_file(task: Task, job_id: str, harness: str) -> Path:
    """Where the external review COMMAND for `harness` keeps the harness's JSON output."""
    result = result_file(task, job_id)
    return result.with_name(result.stem + REVIEW_OUTPUT_SUFFIX[harness])


def review_output_tokens(path: Path, harness: str) -> int | None:
    """[REVIEW-TOKENS] Every input token (cached included) plus output tokens, summed over turns;
    None when the output is missing, unreadable or has no usage."""
    try:
        text = read_text(path)
    except (OSError, UnicodeDecodeError):  # no permission, invalid UTF-8: usage unavailable
        return None
    if not text:
        return None
    if harness == "codex":
        usages = []
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "turn.completed":
                usages.append((event.get("usage"), ("input_tokens", "output_tokens")))
    else:
        try:
            output = json.loads(text)
        except ValueError:
            return None
        if not isinstance(output, dict):
            return None
        usages = [(output.get("usage"), ("input_tokens", "cache_creation_input_tokens",
                                         "cache_read_input_tokens", "output_tokens"))]
    total, found = 0, False
    for usage, keys in usages:
        if not isinstance(usage, dict):
            continue
        for key in keys:
            value = usage.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                total, found = total + value, True
    return total if found else None


def external_review_command(task: Task, job_id: str, model: dict, prompt: str) -> str:
    """Print one shell line; printf restores the literal newlines in the review prompt."""
    result = result_file(task, job_id)
    result.parent.mkdir(parents=True, exist_ok=True)
    output = review_output_file(task, job_id, model["harness"])
    q = shlex.quote
    escaped_prompt = prompt.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
    prompt_arg = '"$(printf %b ' + q(escaped_prompt) + ')"'
    clean = f"rm -f {q(str(result))} {q(str(output))}"
    if model["harness"] == "codex":
        return (f"{clean} && codex exec -m {q(model['model'])} "
                f"-c model_reasoning_effort={q(model['effort'])} -s read-only "
                f"-C {q(str(task.root))} -o {q(str(result))} --ephemeral --json {prompt_arg} "
                f"< /dev/null > {q(str(output))}")
    return (f"cd {q(str(task.root))} && {clean} && claude -p {prompt_arg} --output-format json "
            f"--model {q(model['model'])} "
            f"--effort {q(model['effort'])} --permission-mode dontAsk "
            f"--allowedTools {q('Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(git show *)')} "
            f"> {q(str(output))} && python3 -c {q(CLAUDE_RESULT_TEXT)} {q(str(output))} > {q(str(result))}")
