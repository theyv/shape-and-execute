"""User config, settings validation and card, harness detection, settings of a new task."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .common import (
    CODEX_ENV_VARS,
    CONFIG_HINT,
    DEFAULT_MAX_VERIFY_FAILURES,
    DIFFICULTIES,
    EXIT_CONFIG,
    EXIT_USAGE,
    HARNESSES,
    INTERACTION_MODES,
    LEVELS,
    LEVEL_PHASES,
    REVIEW_POINTS,
    RUNGS,
    SCHEMA_VERSION,
    fail,
    read_json,
)


def config_path() -> Path:
    if os.environ.get("SAE_CONFIG"):
        return Path(os.environ["SAE_CONFIG"]).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "shape-and-execute" / "config.json"


def load_config(required: bool = True) -> dict | None:
    path = config_path()
    if not path.exists():
        if required:
            fail(EXIT_CONFIG, f"No user config at {path}.\n{CONFIG_HINT}")
        return None
    try:
        data = read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        fail(EXIT_CONFIG, f"User config {path} is not valid JSON: {exc}.\n{CONFIG_HINT}")
    if not isinstance(data, dict):
        fail(EXIT_CONFIG, f"User config {path} must be a JSON object.\n{CONFIG_HINT}")
    return data


def cfg(config: dict | None, dotted: str):
    """A config value that a command needs; missing → exit 2."""
    node = config
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            fail(EXIT_CONFIG, f'No user config at {config_path()} (or key "{dotted}" missing).\n{CONFIG_HINT}')
        node = node[part]
    return node


def validate_config(data) -> list[str]:
    """Errors against the config schema v1 (07-cli-spec §3.1)."""
    errors: list[str] = []

    def need(cond: bool, message: str) -> bool:
        if not cond:
            errors.append(message)
        return cond

    if not need(isinstance(data, dict), "config must be a JSON object"):
        return errors
    need(data.get("schema") == SCHEMA_VERSION, f"schema must be {SCHEMA_VERSION}")
    rungs = data.get("rungs")
    if need(isinstance(rungs, dict) and rungs, "rungs: at least one harness (claude, codex)"):
        for harness, table in rungs.items():
            if not need(harness in HARNESSES, f"rungs.{harness}: unknown harness"):
                continue
            if not need(isinstance(table, dict), f"rungs.{harness} must be an object"):
                continue
            for rung in RUNGS:
                entry = table.get(rung)
                if need(isinstance(entry, dict), f"rungs.{harness}.{rung} missing"):
                    need(isinstance(entry.get("model"), str) and entry["model"].strip() != "",
                         f"rungs.{harness}.{rung}.model must be a non-empty string")
                    if harness == "claude":
                        need("effort" not in entry or entry["effort"] is None,
                             f"rungs.claude.{rung}.effort: Claude Code cannot set effort per dispatch")
                    else:
                        need(isinstance(entry.get("effort"), str), f"rungs.{harness}.{rung}.effort must be a string")
    level_map = data.get("level_map")
    if need(isinstance(level_map, dict), "level_map missing"):
        for level in LEVELS:
            row = level_map.get(level)
            if need(isinstance(row, dict), f"level_map.{level} missing"):
                for difficulty in DIFFICULTIES:
                    need(row.get(difficulty) in RUNGS, f"level_map.{level}.{difficulty} must be one of {', '.join(RUNGS)}")
    review_map = data.get("review_level_map")
    if need(isinstance(review_map, dict), "review_level_map missing"):
        for level in LEVELS:
            need(review_map.get(level) in RUNGS, f"review_level_map.{level} must be one of {', '.join(RUNGS)}")
    defaults = data.get("defaults")
    if need(isinstance(defaults, dict), "defaults missing"):
        skeleton = {"schema": SCHEMA_VERSION, **{k: defaults.get(k) for k in ("interaction", "levels", "review")}}
        if "max_verify_failures" in defaults:
            skeleton["max_verify_failures"] = defaults["max_verify_failures"]
        errors.extend(f"defaults.{e}" for e in settings_errors(skeleton))
        provider = (defaults.get("review") or {}).get("provider") if isinstance(defaults.get("review"), dict) else None
        if isinstance(rungs, dict) and provider in HARNESSES and provider not in rungs:
            errors.append(f"defaults.review.provider is {provider}, but rungs.{provider} is missing")
    language = data.get("language")
    if need(isinstance(language, dict), "language missing"):
        for key in ("conversation", "artifacts"):
            need(isinstance(language.get(key), str) and language[key] != "", f"language.{key} must be a language code")
    worktrees = data.get("worktrees")
    if need(isinstance(worktrees, dict), "worktrees missing"):
        root = worktrees.get("root")
        need(isinstance(root, str) and Path(root).expanduser().is_absolute(), "worktrees.root must be an absolute path")
    parallel = data.get("parallel")
    if need(isinstance(parallel, dict), "parallel missing"):
        value = parallel.get("max_writers")
        need(isinstance(value, int) and not isinstance(value, bool) and value >= 1, "parallel.max_writers must be an integer >= 1")
    verify = data.get("verify")
    if need(isinstance(verify, dict), "verify missing"):
        value = verify.get("timeout_s")
        need(isinstance(value, int) and not isinstance(value, bool) and value > 0, "verify.timeout_s must be an integer > 0")
    return errors


def new_task_settings(config: dict) -> dict:
    """The settings.json of a new task, from the config defaults."""
    defaults = cfg(config, "defaults")
    settings = {"schema": SCHEMA_VERSION, "interaction": cfg(config, "defaults.interaction"),
                "levels": dict(cfg(config, "defaults.levels")), "review": dict(cfg(config, "defaults.review")),
                "max_verify_failures": defaults.get("max_verify_failures", DEFAULT_MAX_VERIFY_FAILURES)}
    errors = settings_errors(settings)
    if errors:
        fail(EXIT_CONFIG, f"config.defaults: {'; '.join(errors)}.\n{CONFIG_HINT}")
    return settings


def worktree_root(config: dict) -> Path:
    return Path(cfg(config, "worktrees.root")).expanduser()


def settings_errors(s) -> list[str]:
    errors: list[str] = []
    if not isinstance(s, dict):
        return ["settings must be a JSON object"]
    if s.get("schema") != SCHEMA_VERSION:
        errors.append(f"schema must be {SCHEMA_VERSION}")
    if s.get("interaction") not in INTERACTION_MODES:
        errors.append(f"interaction must be one of {', '.join(INTERACTION_MODES)}")
    levels = s.get("levels")
    if not isinstance(levels, dict):
        errors.append("levels must be an object")
    else:
        for phase in LEVEL_PHASES:
            if levels.get(phase) not in LEVELS:
                errors.append(f"levels.{phase} must be one of {', '.join(LEVELS)}")
    review = s.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        points = review.get("points")
        if not isinstance(points, list) or any(p not in REVIEW_POINTS for p in points):
            errors.append(f"review.points must be a list of {', '.join(REVIEW_POINTS)}")
        elif "selected-jobs" in points and "all-jobs" in points:
            errors.append("review.points: selected-jobs and all-jobs are exclusive")
        elif len(set(points)) != len(points):
            errors.append("review.points has duplicates")
        if review.get("provider") not in HARNESSES:
            errors.append(f"review.provider must be one of {', '.join(HARNESSES)}")
    if "max_verify_failures" in s:
        value = s["max_verify_failures"]
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
            errors.append("max_verify_failures must be an integer from 1 to 10")
    return errors


def max_verify_failures(settings: dict) -> int:
    return settings.get("max_verify_failures", DEFAULT_MAX_VERIFY_FAILURES)


def flatten_settings(s: dict) -> dict:
    flat = {"interaction": s.get("interaction")}
    for phase, level in (s.get("levels") or {}).items():
        flat[f"levels.{phase}"] = level
    review = s.get("review") or {}
    flat["review.points"] = review.get("points")
    flat["review.provider"] = review.get("provider")
    flat["max_verify_failures"] = max_verify_failures(s)
    return flat


def settings_diff(old: dict, new: dict) -> dict:
    a, b = flatten_settings(old or {}), flatten_settings(new)
    return {key: [a.get(key), b.get(key)] for key in sorted(set(a) | set(b)) if a.get(key) != b.get(key)}


def settings_card(s: dict) -> str:
    levels = s["levels"]
    points = s["review"]["points"]
    review = (f"review: {', '.join(points)} · {levels['review']} · {s['review']['provider']}"
              if points else "review: off")
    return (f"interaction: {s['interaction']} · research: {levels['research']} · "
            f"planning: {levels['planning']} · execution: {levels['execution']} · {review}")


def detect_harness(flag: str | None) -> str | None:
    if flag:
        return flag
    env = os.environ.get("SAE_HARNESS")
    if env:
        if env not in HARNESSES:
            fail(EXIT_USAGE, f"SAE_HARNESS must be one of {', '.join(HARNESSES)}, not {env!r}")
        return env
    if os.environ.get("CLAUDECODE") == "1":
        return "claude"
    if any(os.environ.get(name) for name in CODEX_ENV_VARS):
        return "codex"
    return None


def require_harness(flag: str | None) -> str:
    harness = detect_harness(flag)
    if not harness:
        fail(EXIT_USAGE, "Cannot detect the harness. Add --harness claude or --harness codex.")
    return harness
