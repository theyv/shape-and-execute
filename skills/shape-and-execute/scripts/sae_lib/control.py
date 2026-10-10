"""Owner control: the launch card, the process map and holds ([LAUNCH-CARD], [PROCESS-MAP],
[HOLD-AFTER-JOB]; 07-cli-spec §8 "Launch card" and "Process map", `sae hold`).

`sae next` and `sae status` only compute and print the card and the map. The writing command
that starts the launch records the card: `sae dispatch` of a job on it, `sae start` for the
start card (through `next_text` on a writable task)."""

from __future__ import annotations

import re

from .common import (
    EXIT_OK,
    EXIT_USAGE,
    HARNESSES,
    LEVEL_PHASES,
    SaeError,
    WRITER_KINDS,
    emit,
    fail,
    iso,
    read_text,
    wrap,
)
from .config import PHASE_DIFFICULTIES, effective_routing, flatten_settings, routing_layers
from .gitutil import find_root
from .graph import active_holds, hold_active, release_command, review_rounds
from .markdown import has_content, md_section, split_frontmatter, strip_html_comments
from .routing import TASK_TARGETS, resolve_model, route, short_text
from .tasks import Task, is_generated, job_file, open_task

# ---------------------------------------------------------------- launch card

LAUNCH_LABELS = {"research": "research", "planning": "planner", "spec": "spec review", "plan": "plan review",
                 "integration": "integration review"}
REVIEW_PURPOSE = {"spec": "Review the spec before spec approval.",
                  "plan": "Review the job graph before plan approval.",
                  "integration": "Review the merged task branch."}
EXECUTION_ONLY_KINDS = ("implementation", "integration", "validation", "decision")


def job_view(task: Task, job_id: str) -> dict:
    """Kind and target of a job or of a due review that is not a job yet."""
    job = task.jobs.get(job_id)
    if job is not None:
        return {"kind": job["kind"], "target": job.get("target")}
    return {"kind": "review", "target": job_id[len("REVIEW-"):].lower()}


def launch_label(task: Task, job_id: str) -> str | None:
    """The launch a ready job belongs to, or None: job reviews and ordinary writers get no card."""
    view = job_view(task, job_id)
    if view["kind"] in ("research", "planning"):
        return LAUNCH_LABELS[view["kind"]]
    if view["kind"] == "review" and view["target"] in TASK_TARGETS:
        return LAUNCH_LABELS[view["target"]]
    return None


def start_card_due(task: Task) -> bool:
    """The first `next` of execution: no execution card recorded and no execution job started."""
    if task.phase != "executing":
        return False
    last = task.info.get("last_card") or {}
    if last.get("phase") == "executing":
        return False
    return not any(j["attempts"] for j in task.jobs.values()
                   if j["kind"] in EXECUTION_ONLY_KINDS
                   or (j["kind"] == "review" and j.get("target") not in ("spec", "plan")))


def purpose(task: Task, job_id: str) -> str:
    view = job_view(task, job_id)
    job = task.jobs.get(job_id)
    if view["kind"] == "review" and (job is None or is_generated(job_id, job)):
        target = view["target"]
        return REVIEW_PURPOSE.get(target, f"Review {target} before it merges.")
    _, body = split_frontmatter(read_text(job_file(task, job_id), "") or "")
    objective = " ".join(strip_html_comments(md_section(body, "Objective") or "").split())
    first = re.split(r"(?<=[.!?])\s", objective, maxsplit=1)[0] if objective else "(no objective yet)"
    return first if len(first) <= 68 else first[:67].rstrip() + "…"


def settings_snapshot(task: Task, config: dict | None) -> dict:
    """Effective task settings, the resolved routing of every cell the task can use, overrides
    and holds, as flat `{label: text}` (07-cli-spec §8 "Launch card")."""
    snap = {k: v for k, v in flatten_settings(task.settings).items() if not k.startswith("routing.")}
    if config is not None:
        layers = routing_layers(config, task.root, task.settings)
        for harness in HARNESSES:
            if harness not in (config.get("routing") or {}):
                continue
            for phase in LEVEL_PHASES:
                level = task.settings["levels"][phase]
                for difficulty in PHASE_DIFFICULTIES[phase]:
                    ctx = {"phase": phase, "level": level, "difficulty": difficulty}
                    try:
                        cell = route(config, layers, harness, ctx)
                    except SaeError:
                        text = "missing"
                    else:
                        text = f"tier {cell['tier']}" if cell["tier"] else f"{cell['model_entry']} · {cell['effort']}"
                        source = cell["sources"]["cell"]
                        text += "" if source == "global" else f" ({source})"
                        if cell["tier"]:
                            tier = effective_routing(layers, harness)["tiers"][cell["tier"]]
                            snap[f"tier {harness} {cell['tier']}"] = (
                                f"{tier[0]['model']} · {tier[0]['effort']}"
                                + ("" if tier[1] == "global" else f" ({tier[1]})"))
                    snap[f"routing {harness} {phase} {level} {difficulty}"] = text
    for key, value in (task.info.get("overrides") or {}).items():
        snap[f"override {key}"] = " · ".join(str(value[k]) for k in ("harness", "model", "effort") if value.get(k))
    for key, value in (task.info.get("holds") or {}).items():
        snap[f"hold after {key}"] = "set"
    return snap


def change_lines(old: dict, new: dict) -> list[str]:
    """One line per difference between two snapshots."""
    lines = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a == b:
            continue
        if key == "review.points" and isinstance(a, list) and isinstance(b, list):
            parts = [f"{p} added" for p in b if p not in a] + [f"{p} removed" for p in a if p not in b]
            lines.append("review points: " + (", ".join(parts) or "reordered"))
        elif a is None:
            lines.append(f"{key}: {b} (new)")
        elif b is None:
            lines.append(f"{key}: removed (was {a})")
        else:
            lines.append(f"{key}: {a} → {b}")
    return lines


def unreviewed_flagged(task: Task) -> list[str]:
    from .reviews import review_mark  # late import: reviews imports graph, which tasks feeds
    return [i for i, j in task.jobs.items() if j["kind"] in WRITER_KINDS
            and not (review_mark(task, i) or {"reviewed": True})["reviewed"]]


def launch_card(task: Task, config: dict | None, ready: list[str]) -> dict | None:
    """The card due for these ready jobs (IDs; due reviews included), or None.

    `{"jobs", "title", "changes", "first", "unreviewed", "snapshot", "unchanged", "text"}`;
    `unchanged` means every job was on the last recorded card and nothing changed, and `text` is
    then the one-line replacement."""
    start = start_card_due(task)
    jobs = list(ready) if start else [i for i in ready if launch_label(task, i)]
    if not jobs:
        return None
    labels = ["start of execution"] if start else list(dict.fromkeys(launch_label(task, i) for i in jobs))
    last = task.info.get("last_card")
    snapshot = settings_snapshot(task, config)
    changes = change_lines(last["settings"], snapshot) if last else []
    unchanged = bool(last) and not changes and set(jobs) <= set(last.get("jobs") or [])
    blocks = []
    for job_id in jobs:
        try:
            model = short_text(resolve_model(task, job_id, config, exact=False)) if config else "(no user config)"
        except SaeError as exc:
            model = f"(routing error: {str(exc).splitlines()[0]})"
        blocks.append({"id": job_id, "model": model, "purpose": purpose(task, job_id)})
    unreviewed = unreviewed_flagged(task) if (start or task.phase == "planning") else []
    count = f"{len(jobs)} job" + ("" if len(jobs) == 1 else "s")
    title = f"LAUNCH · {', '.join(labels)} · {count}"
    card = {"title": title, "jobs": blocks, "changes": changes, "first": last is None, "unreviewed": unreviewed,
            "snapshot": snapshot, "unchanged": unchanged, "start": start}
    if unchanged:
        card["text"] = f"Launch card shown at {last['at'][11:16]}; no change."
        return card
    lines = [title, ""]
    for block in blocks:
        lines += [f"  {block['id']}", wrap(block["model"], "  "), wrap(block["purpose"], "  "), ""]
    if last is None:
        lines.append("First launch card of this task.")
    elif changes:
        lines += ["Changed since the last card:"] + [wrap(c, "  ") for c in changes]
    else:
        lines.append("No settings change since the last card.")
    if unreviewed:
        lines.append(wrap("Flagged, but no job review will run: " + ", ".join(unreviewed)))
    card["text"] = "\n".join(lines)
    return card


def record_card(task: Task, card: dict) -> None:
    """Stores the card as `task.last_card` and appends `card.shown` (sae dispatch, sae start)."""
    if card is None or card["unchanged"]:
        return
    jobs = [b["id"] for b in card["jobs"]]
    task.info["last_card"] = {"at": iso(), "phase": task.phase, "jobs": jobs, "settings": card["snapshot"]}
    task.event("card.shown", jobs=jobs, changes=card["changes"])
    task.touch()


# ---------------------------------------------------------------- process map

MAP_PHASES = (("💡 SHAPE   ", "shape"), ("📐 PLAN    ", "plan"), ("🔨 EXECUTE ", "execute"))


def shaping_research(task: Task) -> list[str]:
    """Research jobs added before spec approval."""
    ids = []
    for event in task.events():
        if event.get("type") == "spec.approved":
            break
        if event.get("type") == "job.added" and event.get("kind") == "research" and event.get("job") in task.jobs:
            ids.append(event["job"])
    return ids


def review_done(task: Task, target: str) -> bool:
    rounds = review_rounds(task, target)
    return bool(rounds) and task.jobs[rounds[-1]]["status"] == "done"


def map_steps(task: Task) -> list[dict]:
    """Every step of the task with `phase`, `name`, `state` (done | off | none | pending), `gate`
    and `note` (07-cli-spec §8 "Process map")."""
    jobs, info = task.jobs, task.info
    points = task.settings["review"]["points"]
    approvals = info.get("approvals") or {}
    steps: list[dict] = []

    def step(phase: str, name: str, state: str, gate: bool = False, note: str = "") -> None:
        steps.append({"phase": phase, "name": name, "state": state, "gate": gate, "note": note})

    has_spec = (task.dir / "specs.md").exists() or has_content(md_section(read_text(task.dir / "intent.md", "")
                                                                           or "", "Acceptance"))
    step("shape", "intake", "done")
    research = shaping_research(task)
    if research:
        step("shape", "research", "done" if all(jobs[i]["status"] == "done" for i in research) else "pending")
    else:
        step("shape", "research", "none" if has_spec or "spec" in approvals else "pending")
    spec_reviewed = bool(review_rounds(task, "spec"))
    step("shape", "spec", "done" if "spec" in approvals or (has_spec and spec_reviewed) else "pending")
    if "spec" not in points and not spec_reviewed:
        step("shape", "spec-review", "off")
    else:
        step("shape", "spec-review", "done" if review_done(task, "spec") or "spec" in approvals else "pending")
    step("shape", "spec approval", "done" if "spec" in approvals else "pending", gate=True)

    planners = [i for i, j in jobs.items() if j["kind"] == "planning"]
    planned = [i for i, j in jobs.items() if not is_generated(i, j) and j["kind"] not in ("planning", "research")]
    if planners:
        step("plan", "planner", "done" if all(jobs[i]["status"] == "done" for i in planners) else "pending")
    else:
        step("plan", "planner", "none" if planned or "plan" in approvals else "pending")
    if "plan" not in points and not review_rounds(task, "plan"):
        step("plan", "plan-review", "off")
    else:
        step("plan", "plan-review", "done" if review_done(task, "plan") or "plan" in approvals else "pending")
    step("plan", "plan approval", "done" if "plan" in approvals else "pending", gate=True)

    work = [i for i in planned if not jobs[i]["final"]]
    done = sum(1 for i in work if jobs[i]["status"] == "done")
    started = task.phase in ("executing", "done")
    step("execute", f"jobs {done}/{len(work)}", "done" if started and done == len(work) else "pending")
    from .reviews import planned_reviews, review_due  # late import: reviews imports this module's deps
    if not ({"selected-jobs", "all-jobs"} & set(points)):
        step("execute", "job-reviews", "off")
    elif not any(review_due(task, i) for i in jobs):
        step("execute", "job-reviews", "none")
    else:
        job_reviews = [i for i, j in jobs.items() if j["kind"] == "review" and j.get("target") in jobs]
        open_planned = [p for p in planned_reviews(task) if p["target"] in jobs]
        finished = started and not open_planned and all(jobs[i]["status"] == "done" for i in job_reviews)
        step("execute", "job-reviews", "done" if finished else "pending")
    rounds = review_rounds(task, "integration")
    if "integration" not in points and not rounds:
        step("execute", "integration-review", "off")
    else:
        last = jobs[rounds[-1]] if rounds else None
        passed = bool(last) and last["status"] == "done" and last.get("verdict") in ("pass", "pass-with-notes")
        note = f"round {len(rounds)}" if len(rounds) > 1 and not passed else ""
        step("execute", "integration-review", "done" if passed else "pending", note=note)
    finals = [i for i, j in jobs.items() if j["final"]]
    if finals:
        step("execute", "final-validation", "done" if jobs[finals[0]]["status"] == "done" else "pending")
    else:
        step("execute", "final-validation", "none")
    step("execute", "finish", "done" if task.phase == "done" else "pending")

    if task.phase not in ("done", "abandoned"):
        current = next((s for s in steps if s["state"] == "pending"), None)
        if current is not None:
            current["state"] = "current"
            holds = active_holds(task)
            if holds:
                current["note"] = ", ".join(filter(None, [current["note"], "hold after " + ", ".join(holds)]))
    return steps


def step_text(step: dict) -> str:
    state = step["state"]
    if state == "done":
        mark = "✓"
    elif state == "current":
        mark = "►"
    elif state in ("off", "none"):
        mark = "–"
    else:
        mark = "⬥" if step["gate"] else "□"
    text = f"{mark} {step['name']}"
    if state in ("off", "none"):
        text += f" ({state})"
    if step["note"]:
        text += f" ({step['note']})"
    return text


def process_map(task: Task) -> dict:
    steps = map_steps(task)
    lines = []
    for label, phase in MAP_PHASES:
        lines.append(f"{label} " + " | ".join(step_text(s) for s in steps if s["phase"] == phase))
    return {"steps": steps, "lines": lines, "text": "\n\n".join(lines)}


# ---------------------------------------------------------------- holds

def hold_notices(task: Task) -> list[str]:
    """The active holds with their release command ([HOLD-AFTER-JOB])."""
    out = []
    for job_id in active_holds(task):
        out.append(wrap(f"Hold after {job_id}: {job_id} is done. Nothing new is dispatched. "
                        "Report to the owner.") + "\n" + wrap(f"Release: {release_command(task, job_id)}", "  "))
    return out


def holds_data(task: Task) -> list[dict]:
    return [{"job": i, "at": h.get("at"), "reason": h.get("reason"), "active": hold_active(task, i)}
            for i, h in (task.info.get("holds") or {}).items()]


def cmd_hold(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        holds = task.info.setdefault("holds", {})
        job_id = args.id
        if args.release:
            if job_id not in holds:
                fail(EXIT_USAGE, f"No hold after {job_id}.")
            reason = holds.pop(job_id).get("reason")
            task.event("hold.released", job=job_id, reason=reason, by="cli")
            emit(args, f"Released the hold after {job_id}.", {"job": job_id, "released": True})
            return EXIT_OK
        if job_id not in task.jobs:
            fail(EXIT_USAGE, f"No job {job_id} in task {task.id}: a hold needs an existing job.")
        holds[job_id] = {"at": iso(), "reason": args.reason}
        task.event("hold.set", job=job_id, reason=args.reason, by="cli")
        task.touch()
        if hold_active(task, job_id):
            when = f"{job_id} is done: nothing new is dispatched from now on."
        else:
            merged = " and merged" if task.jobs[job_id]["kind"] in WRITER_KINDS and task.uses_worktrees else ""
            when = f"Once {job_id} is done{merged}, nothing new is dispatched."
        text = "\n".join([f"Hold after {job_id}.", wrap(when + " Running jobs finish and are collected."),
                          wrap(f"Release: {release_command(task, job_id)}")])
        emit(args, text, {"job": job_id, "hold": holds[job_id], "active": hold_active(task, job_id)})
    return EXIT_OK


def register_hold(sub, command):
    """Add the `hold` command to the parser."""
    p = command(sub, "hold", "Set or release a hold after a job: once it is done, nothing new starts.",
                "A hold after job X is active once X is done (and merged, for a writer in the worktrees layout).\n"
                "While it is active sae next lists no ready jobs and sae dispatch refuses (exit 3); running jobs\n"
                "finish and are collected. Works in every interaction mode. Run it on the owner's word.",
                ["hold claims-status STATUS-API --reason \"check the API first\"",
                 "hold claims-status STATUS-API --release"], [0, 1], cmd_hold)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--reason", help="why the owner wants to stop there")
    p.add_argument("--release", action="store_true", help="remove the hold; dispatching continues")
