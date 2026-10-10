"""Model resolution (07-cli-spec §5): which harness, model and effort run a job, and why.

`resolve_model` is the one function behind the dispatch header, `sae next`, the launch card,
the viewer and the review-mark tooltips. It returns a dict:

  harness, model (exact: a Codex family resolved to its newest version), model_entry (the model
  list entry), effort, tier (or None), phase, level, difficulty, source (global | project | task
  | override: the nearest level that chose the pair), sources ({cell, tier, harness}), override
  (the override applied, or None), routed (what routing alone would choose, when an override
  applies), family ({family, newest} when a Codex family was resolved).
"""

from __future__ import annotations

import re

from .common import CONFIG_HINT, EXIT_CONFIG, EXIT_USAGE, LEVEL_PHASE_OF_KIND, SaeError, fail
from .config import (
    PHASE_DIFFICULTIES,
    cell_use,
    effective_routing,
    model_entry,
    other_harness,
    pair_error,
    routing_layers,
    task_difficulty,
)
from .tasks import Task

TASK_TARGETS = ("spec", "plan", "integration")
SOURCE_RANK = {"global": 0, "project": 1, "task": 2, "override": 3}


def phase_of(kind: str) -> str:
    if kind == "review":
        return "review"
    return LEVEL_PHASE_OF_KIND.get(kind, "execution")


def planned_review_target(task: Task, job_id: str) -> str | None:
    """The target of a review ID that is not (yet) a job: REVIEW-SPEC, REVIEW-<JOB-ID>, …"""
    if not job_id.startswith("REVIEW-"):
        return None
    rest = job_id[len("REVIEW-"):]
    if rest.lower() in TASK_TARGETS:
        return rest.lower()
    return rest if rest in task.jobs else None


def override_key(task: Task, job_id: str) -> str:
    """The key in task.overrides: a job ID, or the round-1 ID of a review (all its rounds)."""
    job = task.jobs.get(job_id)
    if job and job["kind"] == "review" and job.get("target"):
        target = job["target"]
        return f"REVIEW-{target.upper()}" if target in TASK_TARGETS else f"REVIEW-{target}"
    return job_id


def job_context(task: Task, job_id: str) -> dict:
    """Kind, phase, level and difficulty of a job or a planned review (07-cli-spec §5.1)."""
    job = task.jobs.get(job_id)
    if job is None:
        target = planned_review_target(task, job_id)
        if target is None:
            fail(EXIT_USAGE, f"No job {job_id} in task {task.id}.")
        job = {"kind": "review", "target": target, "difficulty": None}
    kind = job["kind"]
    phase = phase_of(kind)
    if kind == "review":
        target = job.get("target")
        if target in task.jobs and target not in TASK_TARGETS:
            difficulty = task.jobs[target].get("difficulty") or "normal"
        else:
            difficulty = job.get("difficulty") or task_difficulty(task.settings)
    else:
        difficulty = job.get("difficulty") or "normal"
    if difficulty not in PHASE_DIFFICULTIES[phase]:
        difficulty = "normal"  # a review of a mechanical job; planning is never mechanical
    return {"kind": kind, "phase": phase, "level": task.settings["levels"][phase], "difficulty": difficulty,
            "target": job.get("target")}


def routed_harness(task: Task, kind: str) -> str:
    orchestrator = task.info.get("orchestrator_harness")
    if kind == "review":
        provider = task.settings["review"]["provider"]
        if provider != "cross-harness":
            return provider
        if not orchestrator:
            fail(EXIT_USAGE, "The task has no orchestrator harness. Add --harness claude|codex.")
        return other_harness(orchestrator)
    if not orchestrator:
        fail(EXIT_USAGE, "The task has no orchestrator harness. Add --harness claude|codex.")
    return orchestrator


def route(config: dict, layers: list, harness: str, ctx: dict) -> dict:
    """The cell of the job's phase table for one harness: model entry, effort, tier, sources."""
    if harness not in (config.get("routing") or {}) or harness not in (config.get("models") or {}):
        fail(EXIT_CONFIG, f"The user config has no models or routing for {harness}. Set the review provider "
                          f"(sae set <task> reviewer=…) to a configured harness, or add {harness} in setup.\n"
                          f"{CONFIG_HINT}")
    effective = effective_routing(layers, harness)
    where = f"routing.{harness}.tables.{ctx['phase']}.{ctx['level']}.{ctx['difficulty']}"
    found = effective["tables"].get(ctx["phase"], {}).get(ctx["level"], {}).get(ctx["difficulty"])
    if not found:
        fail(EXIT_CONFIG, f'Key "{where}" missing in the user config.\n{CONFIG_HINT}')
    cell, cell_source = found
    tier, pair = cell_use(effective, cell)
    if pair is None:
        what = f"tier {tier} is not defined" if tier else "the cell has no model and effort while tiers are off"
        fail(EXIT_CONFIG, f"{where} ({cell_source}): {what}.\n{CONFIG_HINT}")
    tier_source = effective["tiers"][tier][1] if tier else None
    nearest = max((s for s in (cell_source, tier_source) if s), key=SOURCE_RANK.get)
    return {"harness": harness, "model_entry": pair["model"], "effort": pair["effort"], "tier": tier,
            "source": nearest, "sources": {"cell": cell_source, "tier": tier_source},
            "where": f"routing.{harness}.tiers.{tier}" if tier else where}


def version_key(slug: str) -> tuple:
    found = re.search(r"\d+(?:\.\d+)*", slug)
    return tuple(int(p) for p in found.group(0).split(".")) if found else ()


def newest_of_family(catalog: list[dict], family: str) -> dict | None:
    matches = [m for m in catalog if m.get("visibility") in (None, "list")
               and isinstance(m.get("model"), str) and m["model"].endswith(f"-{family}")]
    return max(matches, key=lambda m: version_key(m["model"])) if matches else None


def resolve_family(harness: str, entry: dict, effort: str) -> tuple[str, dict | None]:
    """(exact model, {family, newest}) — a Codex family resolves to the newest catalog version."""
    if harness != "codex" or not entry.get("family"):
        return entry["model"], None
    from .setup_mode import codex_catalog
    family = entry["model"]
    newest = newest_of_family(codex_catalog() or [], family)
    if newest is None:
        fail(EXIT_CONFIG, f"cannot resolve family '{family}': pin an exact version in setup.\n{CONFIG_HINT}")
    if newest.get("efforts") and effort not in newest["efforts"]:
        fail(EXIT_CONFIG, f"{newest['model']} (newest {family}) does not accept effort {effort!r} "
                          f"(accepts {', '.join(newest['efforts'])}).\n{CONFIG_HINT}")
    return newest["model"], {"family": family, "newest": newest["model"]}


def resolve_model(task: Task, job_id: str, config: dict, harness: str | None = None,
                  provider: str | None = None, exact: bool = True) -> dict:
    """Harness, model and effort for one dispatch of `job_id` (a job or a planned review).

    `harness`/`provider` are the dispatch flags (one dispatch only). `exact=False` leaves Codex
    families unresolved (no catalog read), for read-only listings."""
    ctx = job_context(task, job_id)
    layers = routing_layers(config, task.root, task.settings)
    override = (task.info.get("overrides") or {}).get(override_key(task, job_id))
    routed = routed_harness(task, ctx["kind"])
    flag = (provider or harness) if ctx["kind"] == "review" else harness
    natural = (override or {}).get("harness") or routed
    applies = bool(override) and (not flag or flag == natural)
    chosen = flag or (natural if applies else routed)
    result = route(config, layers, chosen, ctx)
    harness_source = "flag" if flag else ("override" if applies and override.get("harness") else "routing")
    result["sources"]["harness"] = harness_source
    routed_choice = None
    if applies:
        try:
            base = result if chosen == routed else route(config, layers, routed, ctx)
            routed_choice = {k: base[k] for k in ("harness", "model_entry", "effort", "tier", "source")}
        except SaeError:
            routed_choice = None
        if override.get("model") or override.get("effort"):
            result["model_entry"] = override.get("model") or result["model_entry"]
            result["effort"] = override.get("effort") or result["effort"]
            result["tier"] = None
            result["where"] = f"override of {override_key(task, job_id)}"
        result["source"] = "override"
    error = pair_error(config, chosen, result["model_entry"], result["effort"], result["where"])
    if error:
        fail(EXIT_CONFIG, f"{error}.\n{CONFIG_HINT}")
    entry = model_entry(config, chosen, result["model_entry"])
    family = None
    model = result["model_entry"]
    if exact:
        model, family = resolve_family(chosen, entry, result["effort"])
    result.update({"model": model, "family": family, "override": override if applies else None,
                   "routed": routed_choice, **{k: ctx[k] for k in ("phase", "level", "difficulty")}})
    result.pop("where")
    return result


def model_text(res: dict) -> str:
    """`<exact> (<family>, newest)` for a resolved Codex family, else the model."""
    if res.get("family"):
        return f"{res['model']} ({res['family']['family']}, newest)"
    return res["model"]


def routing_text(res: dict) -> str:
    """One line: where the pair came from (dispatch header, `sae next`)."""
    if res.get("override"):
        at = (res["override"].get("at") or "")[:10]
        routed = res.get("routed")
        was = (f"; routing: {routed['harness']} · {routed['model_entry']} · {routed['effort']}" if routed else "")
        return f"override (set {at}){was}"
    head = f"{res['phase']} · {res['level']} · {res['difficulty']}"
    sources = res["sources"]
    if res.get("tier"):
        return f"{head} → tier {res['tier']} (cell: {sources['cell']}, tier: {sources['tier']})"
    return f"{head} → cell ({sources['cell']})"


def short_text(res: dict) -> str:
    """`harness · model · effort` plus the source when it is not global (cards, lists)."""
    text = f"{res['harness']} · {res['model']} · {res['effort']}"
    if res.get("override"):
        return text + " · override"
    return text + ("" if res["source"] == "global" else f" ({res['source']})")

