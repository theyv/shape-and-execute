"""User config, settings validation and card, harness detection, settings of a new task.

The user config is schema 2: model lists and routing tables per harness,
defaults for new tasks and personal project entries. Routing has three levels, global (the
config), project (`projects.<main worktree>`) and task (`settings.json`); `routing_layers` and
`effective_routing` merge them, and `routing.py` resolves one job against the result.
"""

from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import os
import shutil
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
    OLD_LEVEL_NAMES,
    REVIEW_POINTS,
    SCHEMA_VERSION,
    fail,
    read_json,
    write_json,
)
from .gitutil import run

CONFIG_SCHEMA = 2
REVIEW_PROVIDERS = HARNESSES + ("cross-harness",)
TASK_DIFFICULTIES = ("normal", "hard")
TIERS = ("L1", "L2", "L3", "L4")
# Task setting `ask_signal` ([ASK-SETTING]): on, off, or absent (unset). Unset follows the
# interaction mode: on in these modes, off in collaborative and interactive.
ASK_SIGNAL_VALUES = ("on", "off")
ASK_SIGNAL_MODES = ("full-auto", "auto", "critical-only")
# Planning and review are never mechanical work: their tables have no mechanical column.
PHASE_DIFFICULTIES = {"research": DIFFICULTIES, "planning": TASK_DIFFICULTIES,
                      "execution": DIFFICULTIES, "review": TASK_DIFFICULTIES}
ROUTING_SOURCES = ("global", "project", "task")
SCHEMA1_TEXT = ("Your user config uses schema 1 (rungs and level maps).\n"
                "This sae needs schema 2 (routing tables). Run setup mode to\n"
                'convert it. Claude Code:\n  /shape-and-execute setup\n'
                'Codex:\n  $shape-and-execute setup')


# ---------------------------------------------------------------- reading and writing

def config_path() -> Path:
    if os.environ.get("SAE_CONFIG"):
        return Path(os.environ["SAE_CONFIG"]).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "shape-and-execute" / "config.json"


def load_config(required: bool = True, allow_old: bool = False) -> dict | None:
    """The user config. A schema-1 config exits 2 unless `allow_old` (setup, doctor)."""
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
    upgrade_level_names(data)
    if not allow_old and data.get("schema") != CONFIG_SCHEMA:
        if data.get("schema") == 1:
            fail(EXIT_CONFIG, SCHEMA1_TEXT)
        fail(EXIT_CONFIG, f"User config {path}: schema must be {CONFIG_SCHEMA}.\n{CONFIG_HINT}")
    return data


def upgrade_level_names(data):
    """In place: old level names (`max`) become the new ones (`premium`) in a user config, a
    project entry or a settings.json — level values in `levels`, rows of routing tables, also
    under `defaults` and `projects`. A row present under both names stays as it is, so the
    validation reports it. Returns `data`."""
    if not isinstance(data, dict):
        return data
    levels = data.get("levels")
    if isinstance(levels, dict):
        for phase, level in levels.items():
            if isinstance(level, str) and level in OLD_LEVEL_NAMES:
                levels[phase] = OLD_LEVEL_NAMES[level]
    routing = data.get("routing")
    for block in routing.values() if isinstance(routing, dict) else ():
        tables = block.get("tables") if isinstance(block, dict) else None
        for table in tables.values() if isinstance(tables, dict) else ():
            if isinstance(table, dict) and any(o in table and n not in table for o, n in OLD_LEVEL_NAMES.items()):
                rows = list(table.items())
                table.clear()
                table.update((OLD_LEVEL_NAMES.get(k, k), v) for k, v in rows)
    upgrade_level_names(data.get("defaults"))
    projects = data.get("projects")
    for entry in projects.values() if isinstance(projects, dict) else ():
        upgrade_level_names(entry)
    return data


def level_name(value):
    """A level as given on the command line; an old name is read as the new one."""
    return OLD_LEVEL_NAMES.get(value, value) if isinstance(value, str) else value


def save_config(data: dict) -> Path:
    """Write the user config atomically, after a copy to config.json.bak, under a lock."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        write_json(path, data)
    return path


def cfg(config: dict | None, dotted: str):
    """A config value that a command needs; missing → exit 2."""
    node = config
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            fail(EXIT_CONFIG, f'No user config at {config_path()} (or key "{dotted}" missing).\n{CONFIG_HINT}')
        node = node[part]
    return node


# ---------------------------------------------------------------- projects

def main_worktree(root: Path) -> Path:
    """The repository's main worktree (first entry of `git worktree list`); `root` without git."""
    with contextlib.suppress(FileNotFoundError, OSError):
        proc = run(["git", "worktree", "list", "--porcelain"], root)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if line.startswith("worktree "):
                    return Path(line[len("worktree "):]).resolve()
    return root.resolve()


def project_key(root: Path) -> str:
    return str(main_worktree(root))


def project_entry(config: dict | None, root: Path | None) -> dict:
    if not config or root is None:
        return {}
    projects = config.get("projects") or {}
    entry = projects.get(project_key(root))
    return entry if isinstance(entry, dict) else {}


def merge_defaults(base: dict, override: dict) -> dict:
    """`defaults` with a project's partial `defaults` on top (levels and review per key)."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if key in ("levels", "review") and isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(copy.deepcopy(value))
        else:
            out[key] = copy.deepcopy(value)
    return out


# ---------------------------------------------------------------- model lists and pairs

def model_entry(config: dict, harness: str, model: str) -> dict | None:
    for entry in (config.get("models") or {}).get(harness) or []:
        if isinstance(entry, dict) and entry.get("model") == model:
            return entry
    return None


def pair_error(config: dict, harness: str, model, effort, where: str) -> str | None:
    """Why a model · effort pair is invalid for `harness`, or None."""
    if not isinstance(model, str) or not model or not isinstance(effort, str) or not effort:
        return f"{where}: needs model and effort"
    entry = model_entry(config, harness, model)
    if entry is None:
        return f"{where}: model {model!r} is not in models.{harness}"
    if not entry.get("enabled", True):
        return f"{where}: model {model!r} is switched off in models.{harness}"
    if effort not in (entry.get("efforts") or []):
        return (f"{where}: {model} does not accept effort {effort!r} "
                f"(accepts {', '.join(entry.get('efforts') or [])})")
    return None


def model_list_errors(data: dict) -> list[str]:
    errors: list[str] = []
    models = data.get("models")
    if not isinstance(models, dict) or not models:
        return ["models: at least one harness (claude, codex) with a model list"]
    for harness, entries in models.items():
        where = f"models.{harness}"
        if harness not in HARNESSES:
            errors.append(f"{where}: unknown harness")
            continue
        if not isinstance(entries, list) or not entries:
            errors.append(f"{where} must be a non-empty list")
            continue
        seen = set()
        for i, entry in enumerate(entries):
            at = f"{where}[{i}]"
            if not isinstance(entry, dict):
                errors.append(f"{at} must be an object")
                continue
            name = entry.get("model")
            if not isinstance(name, str) or not name.strip():
                errors.append(f"{at}.model must be a non-empty string")
            elif name in seen:
                errors.append(f"{at}: {name} is listed twice")
            seen.add(name)
            if not isinstance(entry.get("family"), bool):
                errors.append(f"{at}.family must be true or false")
            elif harness == "claude" and not entry["family"]:
                errors.append(f"{at}: Claude entries are families (the Agent tool accepts family names only)")
            if not isinstance(entry.get("enabled"), bool):
                errors.append(f"{at}.enabled must be true or false")
            efforts = entry.get("efforts")
            if (not isinstance(efforts, list) or not efforts
                    or any(not isinstance(e, str) or not e for e in efforts) or len(set(efforts)) != len(efforts)):
                errors.append(f"{at}.efforts must be a non-empty list of distinct effort names")
    return errors


def codex_catalog_errors(data: dict, catalog: list[dict] | None) -> list[str]:
    """Enabled Codex exact versions and their efforts against the Codex catalog
    ([CODEX-CATALOG-CHECK]); none without a catalog. Families resolve at dispatch."""
    if catalog is None:
        return []
    by_slug = {m.get("model"): m for m in catalog}
    errors: list[str] = []
    for i, entry in enumerate((data.get("models") or {}).get("codex") or []):
        if entry.get("family") or not entry.get("enabled"):
            continue
        at, name = f"models.codex[{i}]", entry["model"]
        found = by_slug.get(name)
        if found is None:
            errors.append(f"{at}: {name} is not in the Codex catalog (pick versions from `sae setup show`)")
        elif found.get("visibility") not in (None, "list"):
            errors.append(f"{at}: {name} is hidden in the Codex catalog")
        elif found.get("efforts"):
            extra = [e for e in entry["efforts"] if e not in found["efforts"]]
            if extra:
                errors.append(f"{at}: the Codex catalog lists no effort {', '.join(map(repr, extra))} for {name} "
                              f"(lists {', '.join(found['efforts'])})")
    return errors


# ---------------------------------------------------------------- routing blocks

def routing_shape_errors(block, where: str, partial: bool) -> list[str]:
    """Shape of one harness's routing block; `partial` for project and task levels."""
    errors: list[str] = []
    if not isinstance(block, dict):
        return [f"{where} must be an object"]
    for key in block:
        if key not in ("tiers_in_cells", "tiers", "tables"):
            errors.append(f"{where}.{key}: unknown key (tiers_in_cells, tiers, tables)")
    if "tiers_in_cells" in block or not partial:
        if not isinstance(block.get("tiers_in_cells"), bool):
            errors.append(f"{where}.tiers_in_cells must be true or false")
    tiers = block.get("tiers", {})
    if not isinstance(tiers, dict):
        errors.append(f"{where}.tiers must be an object")
    else:
        for name, tier in tiers.items():
            if name not in TIERS:
                errors.append(f"{where}.tiers.{name}: tiers are {', '.join(TIERS)}")
            elif not isinstance(tier, dict) or set(tier) != {"model", "effort"}:
                errors.append(f"{where}.tiers.{name} must be {{model, effort}}")
    tables = block.get("tables")
    if tables is None and partial:
        return errors
    if not isinstance(tables, dict):
        return errors + [f"{where}.tables must be an object"]
    for phase in tables:
        if phase not in PHASE_DIFFICULTIES:
            errors.append(f"{where}.tables.{phase}: phases are {', '.join(LEVEL_PHASES)}")
    for phase, columns in PHASE_DIFFICULTIES.items():
        table = tables.get(phase)
        if table is None and partial:
            continue
        if not isinstance(table, dict):
            errors.append(f"{where}.tables.{phase} missing")
            continue
        for level in table:
            if level not in LEVELS:
                errors.append(f"{where}.tables.{phase}.{level}: levels are {', '.join(LEVELS)}")
        for level in LEVELS:
            row = table.get(level)
            if row is None and partial:
                continue
            if not isinstance(row, dict):
                errors.append(f"{where}.tables.{phase}.{level} missing")
                continue
            for difficulty in row:
                if difficulty not in columns:
                    errors.append(f"{where}.tables.{phase}.{level}.{difficulty}: the {phase} table has only "
                                  f"{', '.join(columns)}")
            for difficulty in columns:
                cell = row.get(difficulty)
                at = f"{where}.tables.{phase}.{level}.{difficulty}"
                if cell is None and partial:
                    continue
                errors.extend(cell_shape_errors(cell, at))
    return errors


def cell_shape_errors(cell, where: str) -> list[str]:
    if not isinstance(cell, dict) or not cell:
        return [f"{where} must be an object with tier, or model and effort"]
    errors = []
    for key in cell:
        if key not in ("tier", "model", "effort"):
            errors.append(f"{where}.{key}: unknown key (tier, model, effort)")
    if "tier" in cell and cell["tier"] not in TIERS:
        errors.append(f"{where}.tier must be one of {', '.join(TIERS)}")
    if ("model" in cell) != ("effort" in cell):
        errors.append(f"{where}: model and effort go together")
    return errors


def routing_pair_errors(config: dict, harness: str, block: dict, where: str) -> list[str]:
    """Every model · effort named in a (partial) block must be in the harness's model list."""
    errors = []
    for name, tier in (block.get("tiers") or {}).items():
        if isinstance(tier, dict):
            error = pair_error(config, harness, tier.get("model"), tier.get("effort"), f"{where}.tiers.{name}")
            if error:
                errors.append(error)
    for phase, table in (block.get("tables") or {}).items():
        for level, row in (table or {}).items() if isinstance(table, dict) else ():
            for difficulty, cell in (row or {}).items() if isinstance(row, dict) else ():
                if isinstance(cell, dict) and "model" in cell:
                    error = pair_error(config, harness, cell.get("model"), cell.get("effort"),
                                       f"{where}.tables.{phase}.{level}.{difficulty}")
                    if error:
                        errors.append(error)
    return errors


def routing_layers(config: dict, root: Path | None = None, settings: dict | None = None,
                   project: dict | None = None) -> list[tuple[str, dict]]:
    """[(source, routing by harness)] from the farthest level to the nearest."""
    if project is None:
        project = project_entry(config, root)
    layers = [("global", config.get("routing") or {}), ("project", project.get("routing") or {})]
    if settings is not None:
        layers.append(("task", settings.get("routing") or {}))
    return layers


def effective_routing(layers: list[tuple[str, dict]], harness: str) -> dict:
    """One harness's routing with each value from the nearest level that sets it.

    Returns {"tiers_in_cells": (value, source), "tiers": {L: (tier, source)},
    "tables": {phase: {level: {difficulty: (cell, source)}}}}; a value no level sets is absent."""
    out: dict = {"tiers": {}, "tables": {}}
    for source, routing in layers:
        block = routing.get(harness)
        if not isinstance(block, dict):
            continue
        if "tiers_in_cells" in block:
            out["tiers_in_cells"] = (block["tiers_in_cells"], source)
        for name, tier in (block.get("tiers") or {}).items():
            out["tiers"][name] = (tier, source)
        for phase, table in (block.get("tables") or {}).items():
            for level, row in (table or {}).items():
                for difficulty, cell in (row or {}).items():
                    out["tables"].setdefault(phase, {}).setdefault(level, {})[difficulty] = (cell, source)
    return out


def cell_use(effective: dict, cell: dict) -> tuple[str | None, dict | None]:
    """(tier name or None, the {model, effort} the cell uses) under the effective tier switch."""
    tiers_on = effective.get("tiers_in_cells", (True, None))[0]
    if tiers_on and cell.get("tier"):
        tier = effective["tiers"].get(cell["tier"])
        return cell["tier"], (tier[0] if tier else None)
    if "model" in cell and "effort" in cell:
        return None, {"model": cell["model"], "effort": cell["effort"]}
    return None, None


def usability_errors(effective: dict, harness: str, label: str) -> list[str]:
    """Every cell of the merged block resolves to a model · effort."""
    errors = []
    for phase, columns in PHASE_DIFFICULTIES.items():
        for level in LEVELS:
            for difficulty in columns:
                found = effective["tables"].get(phase, {}).get(level, {}).get(difficulty)
                where = f"routing.{harness}.tables.{phase}.{level}.{difficulty}"
                if not found:
                    errors.append(f"{where} missing{label}")
                    continue
                tier, pair = cell_use(effective, found[0])
                if pair is None:
                    errors.append(f"{where} ({found[1]}): " + (f"tier {tier} is not defined" if tier else
                                  "nothing usable: tiers in cells are off and the cell has no model and effort"))
    return errors


def routing_errors(config: dict) -> list[str]:
    """The global routing: complete for every harness with a model list, every pair valid."""
    errors: list[str] = []
    routing = config.get("routing")
    models = config.get("models") if isinstance(config.get("models"), dict) else {}
    if not isinstance(routing, dict) or not routing:
        return ["routing: one block per harness of models"]
    for harness in routing:
        if harness not in HARNESSES:
            errors.append(f"routing.{harness}: unknown harness")
        elif harness not in models:
            errors.append(f"routing.{harness}: models.{harness} is missing")
    for harness in models:
        if harness in HARNESSES and harness not in routing:
            errors.append(f"routing.{harness} missing (models.{harness} exists)")
    for harness, block in routing.items():
        if harness not in HARNESSES or harness not in models:
            continue
        shape = routing_shape_errors(block, f"routing.{harness}", partial=False)
        errors += shape
        if shape:
            continue
        errors += routing_pair_errors(config, harness, block, f"routing.{harness}")
        errors += usability_errors(effective_routing([("global", routing)], harness), harness, "")
    return errors


def level_routing_errors(config: dict, routing, where: str, layers: list[tuple[str, dict]]) -> list[str]:
    """A project's or task's partial routing: shape, pairs, and every merged cell usable."""
    if routing is None:
        return []
    if not isinstance(routing, dict):
        return [f"{where} must be an object"]
    errors = []
    for harness, block in routing.items():
        if harness not in HARNESSES:
            errors.append(f"{where}.{harness}: unknown harness")
            continue
        if harness not in (config.get("routing") or {}):
            errors.append(f"{where}.{harness}: the user config has no routing for {harness}")
            continue
        shape = routing_shape_errors(block, f"{where}.{harness}", partial=True)
        errors += shape
        if shape:
            continue
        errors += routing_pair_errors(config, harness, block, f"{where}.{harness}")
        errors += usability_errors(effective_routing(layers, harness), harness, "")
    return errors


# ---------------------------------------------------------------- the whole config

def validate_config(data, catalog: list[dict] | None = None) -> list[str]:
    """Errors against the config schema 2; with the Codex `catalog`, also its
    Codex exact versions and efforts against it."""
    errors: list[str] = []

    def need(cond: bool, message: str) -> bool:
        if not cond:
            errors.append(message)
        return cond

    if not need(isinstance(data, dict), "config must be a JSON object"):
        return errors
    if data.get("schema") == 1:
        return ["schema 1 (rungs and level maps): run setup mode to convert it to schema 2"]
    need(data.get("schema") == CONFIG_SCHEMA, f"schema must be {CONFIG_SCHEMA}")
    placeholders = placeholder_errors(data)
    if placeholders:
        return placeholders
    model_errors = model_list_errors(data)
    errors += model_errors
    if not model_errors:
        errors += codex_catalog_errors(data, catalog)
        errors += routing_errors(data)
    defaults = data.get("defaults")
    if need(isinstance(defaults, dict), "defaults missing"):
        errors.extend(f"defaults.{e}" for e in settings_errors(defaults_as_settings(defaults)))
        provider = (defaults.get("review") or {}).get("provider") if isinstance(defaults.get("review"), dict) else None
        configured = set((data.get("models") or {}) if isinstance(data.get("models"), dict) else ())
        if provider in HARNESSES and provider not in configured:
            errors.append(f"defaults.review.provider is {provider}, but models.{provider} is missing")
    projects = data.get("projects", {})
    if need(isinstance(projects, dict), "projects must be an object"):
        for path, entry in projects.items():
            errors += project_errors(data, path, entry)
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


def defaults_as_settings(defaults: dict) -> dict:
    skeleton = {"schema": SCHEMA_VERSION, **{k: defaults.get(k) for k in ("interaction", "levels", "review")}}
    if "max_verify_failures" in defaults:
        skeleton["max_verify_failures"] = defaults["max_verify_failures"]
    return skeleton


PROJECT_DEFAULT_KEYS = ("interaction", "levels", "review", "max_verify_failures")


def project_errors(config: dict, path: str, entry) -> list[str]:
    where = f"projects.{path}"
    if not Path(path).is_absolute():
        return [f"{where}: the key must be the absolute path of the repository's main worktree"]
    if not isinstance(entry, dict):
        return [f"{where} must be an object"]
    errors = [f"{where}.{k}: unknown key (defaults, routing)" for k in entry if k not in ("defaults", "routing")]
    defaults = entry.get("defaults", {})
    if not isinstance(defaults, dict):
        errors.append(f"{where}.defaults must be an object")
    else:
        errors += [f"{where}.defaults.{k}: unknown key" for k in defaults if k not in PROJECT_DEFAULT_KEYS]
        merged = merge_defaults(config.get("defaults") or {}, defaults)
        errors += [f"{where}.defaults: {e}" for e in settings_errors(defaults_as_settings(merged))]
    errors += level_routing_errors(config, entry.get("routing"), f"{where}.routing",
                                   routing_layers(config, project=entry))
    return errors


def new_task_settings(config: dict, root: Path | None = None) -> dict:
    """The settings.json of a new task: config defaults, then the project's defaults."""
    if root is None:
        from .gitutil import find_root
        root = find_root()[0]
    defaults = merge_defaults(cfg(config, "defaults"), project_entry(config, root).get("defaults") or {})
    settings = {"schema": SCHEMA_VERSION, "interaction": cfg({"defaults": defaults}, "defaults.interaction"),
                "levels": dict(cfg({"defaults": defaults}, "defaults.levels")),
                "review": dict(cfg({"defaults": defaults}, "defaults.review")),
                "max_verify_failures": defaults.get("max_verify_failures", DEFAULT_MAX_VERIFY_FAILURES)}
    errors = settings_errors(settings)
    if errors:
        fail(EXIT_CONFIG, f"config.defaults: {'; '.join(errors)}.\n{CONFIG_HINT}")
    return settings


def worktree_root(config: dict) -> Path:
    return Path(cfg(config, "worktrees.root")).expanduser()


# ---------------------------------------------------------------- task settings

def settings_errors(s) -> list[str]:
    """Shape of settings.json. Task routing pairs are checked against the config by `sae set` and
    at dispatch, where the config is loaded. Reads old level names as the new ones first, in place
    (`upgrade_level_names`): every reader of a task's settings.json validates it here."""
    errors: list[str] = []
    if not isinstance(s, dict):
        return ["settings must be a JSON object"]
    upgrade_level_names(s)
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
        if review.get("provider") not in REVIEW_PROVIDERS:
            errors.append(f"review.provider must be one of {', '.join(REVIEW_PROVIDERS)}")
    if "max_verify_failures" in s:
        value = s["max_verify_failures"]
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
            errors.append("max_verify_failures must be an integer from 1 to 10")
    if "task_difficulty" in s and s["task_difficulty"] not in TASK_DIFFICULTIES:
        errors.append(f"task_difficulty must be one of {', '.join(TASK_DIFFICULTIES)}")
    if "ask_signal" in s and s["ask_signal"] not in ASK_SIGNAL_VALUES:
        errors.append("ask_signal must be on or off (leave it out to follow the interaction mode)")
    routing = s.get("routing")
    if routing is not None:
        if not isinstance(routing, dict):
            errors.append("routing must be an object")
        else:
            for harness, block in routing.items():
                if harness not in HARNESSES:
                    errors.append(f"routing.{harness}: unknown harness")
                else:
                    errors += routing_shape_errors(block, f"routing.{harness}", partial=True)
    return errors


# ---------------------------------------------------------------- `sae set` and `sae project set` keys

# key → path in settings.json (and in a project's `defaults`, without task-difficulty)
SET_KEYS = {
    "interaction": ("interaction",), "research": ("levels", "research"), "planning": ("levels", "planning"),
    "execution": ("levels", "execution"), "review-level": ("levels", "review"), "review": ("review", "points"),
    "reviewer": ("review", "provider"), "max-verify-failures": ("max_verify_failures",),
    "task-difficulty": ("task_difficulty",),
}
ROUTING_KEYS_HELP = ("routing.<harness>.<phase>.<level>.<difficulty>=<model>:<effort>|<tier>|inherit, "
                     "tier.<harness>.<L1-L4>=<model>:<effort>|inherit, tiers-in-cells.<harness>=on|off|inherit")


def parse_set_value(key: str, value: str):
    if key == "review":
        return [] if value == "off" else [p.strip() for p in value.split(",") if p.strip()]
    if key == "max-verify-failures":
        if not value.isdigit():
            fail(EXIT_USAGE, "max-verify-failures must be an integer from 1 to 10.")
        return int(value)
    if SET_KEYS.get(key, ("",))[0] == "levels":
        return level_name(value)
    return value


def is_routing_key(key: str) -> bool:
    return key.startswith(("routing.", "tier.", "tiers-in-cells."))


def apply_routing_key(routing: dict, key: str, value: str) -> None:
    """Set or (with `inherit`) remove one routing value in a partial routing block, in place."""
    parts = key.split(".")
    head, harness = parts[0], (parts[1] if len(parts) > 1 else None)
    if harness not in HARNESSES:
        fail(EXIT_USAGE, f"{key}: the harness is one of {', '.join(HARNESSES)}. Keys: {ROUTING_KEYS_HELP}.")

    def pair(text: str) -> dict:
        model, sep, effort = text.rpartition(":")
        if not sep or not model or not effort:
            fail(EXIT_USAGE, f"{key}={text}: expected <model>:<effort>.")
        return {"model": model, "effort": effort}

    if head == "tiers-in-cells" and len(parts) == 2:
        if value not in ("on", "off", "inherit"):
            fail(EXIT_USAGE, f"{key} is on, off or inherit.")
        path, new = ["tiers_in_cells"], (None if value == "inherit" else value == "on")
    elif head == "tier" and len(parts) == 3 and parts[2] in TIERS:
        path, new = ["tiers", parts[2]], (None if value == "inherit" else pair(value))
    elif head == "routing" and len(parts) == 5:
        phase, level, difficulty = parts[2:]
        level = level_name(level)
        if phase not in PHASE_DIFFICULTIES or level not in LEVELS:
            fail(EXIT_USAGE, f"{key}: phases are {', '.join(LEVEL_PHASES)}; levels are {', '.join(LEVELS)}.")
        if difficulty not in PHASE_DIFFICULTIES[phase]:
            fail(EXIT_USAGE, f"{key}: the {phase} table has only {', '.join(PHASE_DIFFICULTIES[phase])}.")
        path = ["tables", phase, level, difficulty]
        new = None if value == "inherit" else ({"tier": value} if value in TIERS else pair(value))
    else:
        fail(EXIT_USAGE, f"Unknown routing key {key!r}. Keys: {ROUTING_KEYS_HELP}.")
    nodes = [routing.setdefault(harness, {})]
    for part in path[:-1]:
        nodes.append(nodes[-1].setdefault(part, {}))
    if new is None:
        nodes[-1].pop(path[-1], None)
        for node, part in zip(reversed(nodes[:-1]), reversed(path[:-1])):  # prune empty parents
            if not node[part]:
                del node[part]
        if not routing[harness]:
            del routing[harness]
    else:
        nodes[-1][path[-1]] = new


def placeholder_errors(data, where: str = "config") -> list[str]:
    """Unfilled `<...>` values left from a proposal skeleton or a schema-1 conversion."""
    if isinstance(data, dict):
        return [e for k, v in data.items() for e in placeholder_errors(v, f"{where}.{k}")]
    if isinstance(data, list):
        return [e for i, v in enumerate(data) for e in placeholder_errors(v, f"{where}[{i}]")]
    if isinstance(data, str) and data.startswith("<") and data.endswith(">"):
        return [f"{where}: fill in {data}"]
    return []


def task_difficulty(settings: dict) -> str:
    return settings.get("task_difficulty") or "normal"


def ask_signal(settings: dict) -> dict:
    """The effective ask signal ([ASK-SETTING]): `{"on": bool, "set": "on" | "off" | None,
    "text": "on" | "off" | "on (mode default)" | "off (mode default)"}`. `set` is the task's own
    value; None means it follows the interaction mode."""
    own = settings.get("ask_signal")
    on = own == "on" if own in ASK_SIGNAL_VALUES else settings.get("interaction") in ASK_SIGNAL_MODES
    return {"on": on, "set": own if own in ASK_SIGNAL_VALUES else None,
            "text": ("on" if on else "off") + ("" if own in ASK_SIGNAL_VALUES else " (mode default)")}


def max_verify_failures(settings: dict) -> int:
    return settings.get("max_verify_failures", DEFAULT_MAX_VERIFY_FAILURES)


def flatten_routing(routing: dict | None, prefix: str = "routing") -> dict:
    flat = {}
    for harness, block in (routing or {}).items():
        if not isinstance(block, dict):
            continue
        if "tiers_in_cells" in block:
            flat[f"{prefix}.{harness}.tiers_in_cells"] = block["tiers_in_cells"]
        for name, tier in (block.get("tiers") or {}).items():
            flat[f"{prefix}.{harness}.tiers.{name}"] = tier
        for phase, table in (block.get("tables") or {}).items():
            for level, row in (table or {}).items():
                for difficulty, cell in (row or {}).items():
                    flat[f"{prefix}.{harness}.tables.{phase}.{level}.{difficulty}"] = cell
    return flat


def flatten_settings(s: dict) -> dict:
    flat = {"interaction": s.get("interaction")}
    for phase, level in (s.get("levels") or {}).items():
        flat[f"levels.{phase}"] = level
    review = s.get("review") or {}
    flat["review.points"] = review.get("points")
    flat["review.provider"] = review.get("provider")
    flat["max_verify_failures"] = max_verify_failures(s)
    flat["task_difficulty"] = task_difficulty(s)
    flat["ask_signal"] = s.get("ask_signal")
    flat.update(flatten_routing(s.get("routing")))
    return flat


def settings_diff(old: dict, new: dict) -> dict:
    # an old level name in `old` (settings_seen of an older sae) is not a change
    a, b = flatten_settings(upgrade_level_names(copy.deepcopy(old or {}))), flatten_settings(new)
    return {key: [a.get(key), b.get(key)] for key in sorted(set(a) | set(b)) if a.get(key) != b.get(key)}


def other_harness(harness: str) -> str:
    return next(h for h in HARNESSES if h != harness)


def provider_text(provider: str, harness: str | None = None) -> str:
    """The review provider for cards; cross-harness says what it means in a few words."""
    if provider != "cross-harness":
        return provider
    if harness in HARNESSES:
        return f"cross-harness ({other_harness(harness)} reviews)"
    return "cross-harness (the other harness reviews)"


def settings_card(s: dict, harness: str | None = None, title: str = "Settings") -> str:
    """The settings card ([OUT-SETTINGS-CARD]): `title`, then one setting per line, its value in
    a fixed column."""
    levels = s["levels"]
    points = s["review"]["points"]
    rows = [("interaction", s["interaction"]), ("research", levels["research"]),
            ("planning", levels["planning"]), ("execution", levels["execution"]),
            ("review points", ", ".join(points) or "off")]
    if points:
        rows.append(("review", f"{levels['review']} · {provider_text(s['review']['provider'], harness)}"))
    rows.append(("task difficulty", task_difficulty(s)))
    if s.get("ask_signal"):  # shown when set; unset follows the interaction mode
        rows.append(("ask signal", s["ask_signal"]))
    if s.get("routing"):
        count = len(flatten_routing(s["routing"]))
        rows.append(("routing", f"{count} task value" + ("" if count == 1 else "s")))
    return "\n".join([title] + [f"  {label:<17}{value}" for label, value in rows])


# ---------------------------------------------------------------- harness

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
