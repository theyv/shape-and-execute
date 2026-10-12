"""Commands setup show|save|snippets and the Codex facts they print."""

from __future__ import annotations

import contextlib
import copy
import functools
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .common import (
    CODEX_MIN_SUBAGENTS,
    CODEX_RECOMMENDED_SUBAGENTS,
    EXIT_OK,
    EXIT_USAGE,
    HARNESSES,
    INTERACTION_MODES,
    LEVELS,
    LEVEL_PHASES,
    Parser,
    REVIEW_POINTS,
    SKILL_DIR,
    emit,
    fail,
    read_text,
    table,
    warn,
)
from .config import (
    CONFIG_SCHEMA,
    PHASE_DIFFICULTIES,
    REVIEW_PROVIDERS,
    ROUTING_KEYS_HELP,
    SET_KEYS,
    TIERS,
    apply_routing_key,
    config_path,
    effective_routing,
    flatten_routing,
    is_routing_key,
    load_config,
    parse_set_value,
    project_errors,
    project_key,
    provider_text,
    save_config,
    validate_config,
    worktree_root,
)
from .gitutil import find_root
from .markdown import _strip_yaml_comment, _yaml_scalar


def default_worktree_root() -> str:
    if platform.system() == "Darwin":
        return str(Path.home() / "Library" / "Caches" / "shape-and-execute" / "worktrees")
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return str(Path(base) / "shape-and-execute" / "worktrees")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()


def read_toml(path: Path) -> dict | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        import tomllib  # Python >= 3.11
        return tomllib.loads(text)
    except ImportError:
        pass
    except ValueError as exc:
        warn(f"{path}: {exc}")
        return {}
    # Python 3.10: tables and simple scalar keys only, enough for the keys sae reads.
    data: dict = {}
    node = data
    for raw in text.splitlines():
        line = _strip_yaml_comment(raw).strip()
        header = re.match(r"^\[([^\[\]]+)\]$", line)
        if header:
            node = data
            for part in [p.strip().strip('"') for p in header.group(1).split(".")]:
                node = node.setdefault(part, {})
            continue
        pair = re.match(r'^([A-Za-z0-9_.-]+|"[^"]+")\s*=\s*(.+)$', line)
        if pair:
            node[pair.group(1).strip('"')] = _yaml_scalar(pair.group(2))
    return data


def codex_subagent_cap() -> dict:
    """How many subagents a Codex session may hold open, from $CODEX_HOME/config.toml."""
    path = codex_home() / "config.toml"
    data = read_toml(path) or {}
    agents = data.get("agents") if isinstance(data.get("agents"), dict) else {}
    features = data.get("features") if isinstance(data.get("features"), dict) else {}
    v2 = features.get("multi_agent_v2")
    subagents, source = None, None
    if isinstance(v2, dict) and isinstance(v2.get("max_concurrent_threads_per_session"), int):
        subagents = v2["max_concurrent_threads_per_session"] - 1
        source = "features.multi_agent_v2.max_concurrent_threads_per_session (counts the root session)"
    else:
        for key in ("max_concurrent_threads_per_session", "max_threads"):
            if isinstance(agents.get(key), int):
                subagents, source = agents[key], f"agents.{key}"
                break
    return {"config": str(path), "exists": path.exists(), "subagents": subagents, "source": source,
            "ok": subagents is not None and subagents >= CODEX_MIN_SUBAGENTS,
            "minimum": CODEX_MIN_SUBAGENTS, "recommended": CODEX_RECOMMENDED_SUBAGENTS}


def codex_cap_text(cap: dict, indent: str = "") -> str:
    """The cap, each line after `indent`; the first line alone is the summary that `sae doctor`
    prints."""
    if cap["subagents"] is not None:
        lines = [f"Codex subagent cap: {cap['subagents']} subagents", f"  from {cap['source']}"]
    else:
        lines = ["Codex subagent cap: not set (Codex default)",
                 "  The default is 3 subagents for multi-agent v2 models, 6 for v1."]
    if not cap["ok"]:
        lines += [f"Below {cap['minimum']}: parallel writers, reviews and research hit \"agent thread limit reached\".",
                  "Recommended, in:", f"  {cap['config']}", "  [agents]", f"  max_threads = {cap['recommended']}",
                  "Setup mode can apply it after you agree (with a backup)."]
    return "\n".join(indent + line for line in lines)


@functools.lru_cache(maxsize=1)
def _codex_catalog() -> tuple | None:
    models = None
    cache = codex_home() / "models_cache.json"
    with contextlib.suppress(OSError, ValueError, AttributeError):
        models = json.loads(cache.read_text(encoding="utf-8")).get("models")
    if models is None and shutil.which("codex"):
        try:
            proc = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=30,
                                  stdin=subprocess.DEVNULL)
            models = json.loads(proc.stdout.strip().splitlines()[-1])["models"]
        except (subprocess.TimeoutExpired, OSError, ValueError, KeyError, IndexError):
            models = None
    if not isinstance(models, list):
        return None
    out = []
    for model in models:
        if not isinstance(model, dict) or not model.get("slug"):
            continue
        levels = model.get("supported_reasoning_levels") or []
        efforts = [lvl.get("effort") if isinstance(lvl, dict) else lvl for lvl in levels]
        out.append({"model": model["slug"], "efforts": [e for e in efforts if e], "visibility": model.get("visibility")})
    return tuple(out)


# The Claude families sae knows: the viewer's "Add family" offers each one missing from the
# model list ([SETTINGS-CLAUDE-FAMILIES]). The only model names in code.
CLAUDE_FAMILIES = ("haiku", "sonnet", "opus", "fable")


def codex_catalog() -> list[dict] | None:
    """The Codex model catalog: $CODEX_HOME/models_cache.json, else `codex debug models`."""
    catalog = _codex_catalog()
    return [dict(m) for m in catalog] if catalog is not None else None


def codex_models() -> list[dict] | None:
    catalog = codex_catalog()
    if catalog is None:
        return None
    return [{"model": m["model"], "efforts": m["efforts"]} for m in catalog if m["visibility"] in (None, "list")]


def family_of(slug: str) -> str | None:
    """The family of a versioned slug (`<name>-<version>-<family>`), or None."""
    last = slug.rsplit("-", 1)[-1]
    return last if "-" in slug and last.isalpha() and re.search(r"\d", slug) else None


def codex_families(models: list[dict]) -> dict:
    """{family: {newest, efforts, older: [{model, efforts}]}} from the visible catalog."""
    from .routing import newest_of_family, version_key
    families: dict = {}
    for name in sorted({f for f in (family_of(m["model"]) for m in models) if f}):
        newest = newest_of_family(models, name)
        older = sorted((m for m in models if family_of(m["model"]) == name and m is not newest),
                       key=lambda m: version_key(m["model"]), reverse=True)
        families[name] = {"newest": newest["model"], "efforts": newest["efforts"],
                          "older": [{"model": m["model"], "efforts": m["efforts"]} for m in older]}
    return families


def setup_facts() -> dict:
    facts = {"os": platform.system(), "python": platform.python_version(), "config_path": str(config_path()),
             "claude_on_path": bool(shutil.which("claude")), "codex_on_path": bool(shutil.which("codex")),
             "default_worktree_root": default_worktree_root(), "git_on_path": bool(shutil.which("git"))}
    models = codex_models()
    if facts["codex_on_path"] or models:
        facts["codex_models"] = models
        facts["codex_families"] = codex_families(models) if models else None
        facts["codex_subagent_cap"] = codex_subagent_cap()
    return facts


def config_skeleton(facts: dict) -> dict:
    """A schema-2 proposal skeleton: every value to fill is a `<...>` placeholder."""
    models, routing = {}, {}

    def block() -> dict:
        tables = {phase: {lvl: {d: {"tier": "<L1-L4>", "model": "<model, used when tiers are off>",
                                    "effort": "<effort>"} for d in PHASE_DIFFICULTIES[phase]}
                          for lvl in LEVELS} for phase in LEVEL_PHASES}
        return {"tiers_in_cells": True, "tiers": {t: {"model": "<model>", "effort": "<effort>"} for t in TIERS},
                "tables": tables}

    if facts["claude_on_path"]:
        models["claude"] = [{"model": "<family>", "family": True, "enabled": True, "efforts": ["<effort>"]}]
        routing["claude"] = block()
    if facts.get("codex_families") or facts["codex_on_path"]:
        families = facts.get("codex_families") or {"<family>": {"efforts": ["<effort>"]}}
        models["codex"] = [{"model": name, "family": True, "enabled": True, "efforts": info["efforts"]}
                           for name, info in families.items()]
        routing["codex"] = block()
    return {
        "schema": CONFIG_SCHEMA, "models": models, "routing": routing,
        "defaults": {"interaction": f"<{'|'.join(INTERACTION_MODES)}>",
                     "levels": {p: f"<{'|'.join(LEVELS)}>" for p in LEVEL_PHASES},
                     "review": {"points": [f"<{'|'.join(REVIEW_POINTS)}>"],
                                "provider": f"<{'|'.join(REVIEW_PROVIDERS)}>"}},
        "projects": {},
        "language": {"conversation": "<code>", "artifacts": "<code>"},
        "worktrees": {"root": facts["default_worktree_root"]},
        "parallel": {"max_writers": "<integer>"},
        "verify": {"timeout_s": "<seconds>"},
    }


def convert_schema1(old: dict, catalog: list[dict] | None) -> dict:
    """The schema-2 proposal for a schema-1 config: each rung becomes a tier,
    each cell points to the tier the old level map chose. Claude rungs had no effort: `<choose>`."""
    by_slug = {m["model"]: m for m in catalog or []}
    models, routing = {}, {}
    for harness, rungs in (old.get("rungs") or {}).items():
        if harness not in HARNESSES or not isinstance(rungs, dict):
            continue
        entries: dict = {}
        tiers = {}
        for rung in sorted(rungs):
            spec = rungs[rung] if isinstance(rungs[rung], dict) else {}
            model = spec.get("model")
            if not model:
                continue
            effort = spec.get("effort") or "<choose>"
            tiers[rung] = {"model": model, "effort": effort}
            entry = entries.setdefault(model, {"model": model, "family": harness == "claude", "enabled": True,
                                               "efforts": []})
            known = by_slug.get(model, {}).get("efforts") if harness == "codex" else None
            if known:
                entry["efforts"] = list(known)
            elif effort not in entry["efforts"]:
                entry["efforts"].append(effort)
        level_map = old.get("level_map") or {}
        review_map = old.get("review_level_map") or {}
        tables = {}
        for phase, columns in PHASE_DIFFICULTIES.items():
            tables[phase] = {}
            for level in LEVELS:
                row = {}
                for difficulty in columns:
                    tier = review_map.get(level) if phase == "review" else (level_map.get(level) or {}).get(difficulty)
                    row[difficulty] = {"tier": tier or "<L1-L4>"}
                tables[phase][level] = row
        models[harness] = list(entries.values())
        routing[harness] = {"tiers_in_cells": True, "tiers": tiers, "tables": tables}
    defaults = dict(old.get("defaults") or {})
    return {"schema": CONFIG_SCHEMA, "models": models, "routing": routing, "defaults": defaults, "projects": {},
            **{k: old[k] for k in ("language", "worktrees", "parallel", "verify") if k in old}}


def cell_text(effective: dict, cell: dict) -> str:
    tiers_on = effective.get("tiers_in_cells", (True, None))[0]
    if tiers_on and cell.get("tier"):
        return cell["tier"]
    if "model" in cell:
        return f"{cell['model']} · {cell.get('effort')}"
    return cell.get("tier", "?")


def routing_tables_text(layers: list, harness: str, marks: bool = False) -> list[str]:
    """The tiers and one small table per phase for one harness (`marks`: a source letter)."""
    effective = effective_routing(layers, harness)
    letter = {"global": "", "project": "ᵖ", "task": "ᵗ"}
    lines = [f"  tiers in cells: {'on' if effective.get('tiers_in_cells', (True,))[0] else 'off'}"]
    for name in TIERS:
        if name in effective["tiers"]:
            tier, source = effective["tiers"][name]
            lines.append(f"  {name}  {tier.get('model')} · {tier.get('effort')}" + (f" ({source})" if marks and source != "global" else ""))
    for phase in LEVEL_PHASES:
        columns = PHASE_DIFFICULTIES[phase]
        rows = [["level", *columns]]
        for level in LEVELS:
            row = [level]
            for difficulty in columns:
                found = effective["tables"].get(phase, {}).get(level, {}).get(difficulty)
                row.append(cell_text(effective, found[0]) + (letter[found[1]] if marks else "") if found else "-")
            rows.append(row)
        lines += ["", f"  {harness} · {phase}", table(rows, indent="  ")]
    return lines


def config_text(config: dict) -> list[str]:
    """The config, readable: model lists, tiers, tables, defaults, projects, the rest."""
    lines = []
    layers = [("global", config.get("routing") or {})]
    for harness, entries in (config.get("models") or {}).items():
        lines += ["", f"{harness} models (lightest first):"]
        for i, entry in enumerate(entries if isinstance(entries, list) else [], 1):
            kind = "family" if entry.get("family") else "exact"
            off = "" if entry.get("enabled", True) else " · off"
            lines.append(f"  {i}. {entry.get('model')} ({kind}{off}) · {', '.join(entry.get('efforts') or [])}")
        if harness in (config.get("routing") or {}):
            lines += [f"{harness} routing:"] + routing_tables_text(layers, harness)
    defaults = config.get("defaults") or {}
    review = defaults.get("review") or {}
    lines += ["", "Defaults for new tasks:",
              f"  interaction: {defaults.get('interaction')}",
              "  levels: " + ", ".join(f"{k} {v}" for k, v in (defaults.get("levels") or {}).items()),
              f"  review: {', '.join(review.get('points') or []) or 'off'} · {provider_text(review.get('provider'))}"]
    for path, entry in (config.get("projects") or {}).items():
        lines.append(f"Project {path}:")
        lines += [f"  {k} = {json.dumps(v)}" for k, v in flatten_project(entry).items()]
    lines += ["", f"language: {json.dumps(config.get('language'))}",
              f"worktree root: {(config.get('worktrees') or {}).get('root')}",
              f"writer cap: {(config.get('parallel') or {}).get('max_writers')} · "
              f"verify timeout: {(config.get('verify') or {}).get('timeout_s')} s"]
    return lines


def cmd_setup_show(args) -> int:
    facts = setup_facts()
    config = load_config(required=False, allow_old=True)
    lines = ["Detected:", f"  OS: {facts['os']} · Python {facts['python']} · git: {'yes' if facts['git_on_path'] else 'NO'}",
             f"  claude on PATH: {'yes' if facts['claude_on_path'] else 'no'} · "
             f"codex on PATH: {'yes' if facts['codex_on_path'] else 'no'}",
             f"  default worktree root: {facts['default_worktree_root']}"]
    if facts.get("codex_families"):
        lines.append("  Codex families (newest · older versions):")
        for name, info in facts["codex_families"].items():
            older = ", ".join(m["model"] for m in info["older"]) or "-"
            lines += [f"    {name}: {info['newest']}", f"      efforts: {', '.join(info['efforts'])}",
                      f"      older: {older}"]
    if facts.get("codex_subagent_cap"):
        lines.append(codex_cap_text(facts["codex_subagent_cap"], indent="  "))
    if config is not None and config.get("schema") == 1:
        proposal = convert_schema1(config, codex_catalog())
        lines += ["", f"Your config ({config_path()}) is schema 1 (rungs).",
                  "Proposed conversion to schema 2 (each rung is a tier; fill every <choose> with an effort, "
                  "then save it in setup mode). Save:",
                  "  sae setup save"]
        lines += config_text(proposal)
        lines += ["", "As JSON:", json.dumps(proposal, indent=2, ensure_ascii=False)]
        data = {"facts": facts, "config": config, "schema": 1, "proposal": proposal}
    elif config is not None:
        errors = validate_config(config, codex_catalog())
        lines += ["", f"Current config ({config_path()}):"] + config_text(config)
        if errors:
            lines += ["", "Problems:"] + [f"  - {e}" for e in errors]
        data = {"facts": facts, "config": config, "errors": errors}
    else:
        skeleton = config_skeleton(facts)
        lines += ["", f"No config at {config_path()}. Proposal skeleton (fill every <...>):",
                  json.dumps(skeleton, indent=2, ensure_ascii=False)]
        data = {"facts": facts, "config": None, "skeleton": skeleton}
    emit(args, "\n".join(lines), data)
    return EXIT_OK


def cmd_setup_save(args) -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(EXIT_USAGE, f"stdin is not valid JSON: {exc}")
    errors = validate_config(data, codex_catalog())
    if errors:
        fail(EXIT_USAGE, "Config not saved:\n" + "\n".join(f"  - {e}" for e in errors))
    path = save_config(data)
    backup = path.with_name(path.name + ".bak")
    emit(args, f"Saved {path}" + (f" (backup: {backup.name})" if backup.exists() else ""), {"path": str(path)})
    return EXIT_OK


# ---------------------------------------------------------------- project defaults

PROJECT_KEYS = tuple(k for k in SET_KEYS if k != "task-difficulty")


def flatten_project(entry: dict) -> dict:
    """{sae key: value} of one project entry."""
    flat = {}
    defaults = entry.get("defaults") or {}
    for key in PROJECT_KEYS:
        node = defaults
        for part in SET_KEYS[key]:
            node = node.get(part) if isinstance(node, dict) else None
        if node is not None:
            flat[key] = node
    for key, value in flatten_routing(entry.get("routing")).items():
        flat[key] = value
    return flat


def project_for_cwd(config: dict) -> tuple[str, dict]:
    root, is_git = find_root()
    key = project_key(root)
    return key, copy.deepcopy((config.get("projects") or {}).get(key) or {})


def cmd_project_show(args) -> int:
    config = load_config()
    key, entry = project_for_cwd(config)
    flat = flatten_project(entry)
    global_flat = flatten_project({"defaults": config.get("defaults") or {}, "routing": config.get("routing") or {}})
    lines = [f"Project: {key}"]
    if not flat:
        lines.append("No project values: new tasks use the global defaults and routing.")
    for name, value in flat.items():
        lines.append(f"  {name} = {json.dumps(value)}  (global: {json.dumps(global_flat.get(name))})")
    emit(args, "\n".join(lines), {"project": key, "values": flat,
                                  "global": {k: global_flat.get(k) for k in flat}})
    return EXIT_OK


def change_project(args, unset: bool) -> int:
    config = load_config()
    key, entry = project_for_cwd(config)
    for pair in args.pairs:
        name, sep, value = pair.partition("=")
        if unset:
            name, value = pair, "inherit"
        elif not sep:
            fail(EXIT_USAGE, f"Expected key=value, got {pair!r}.")
        if is_routing_key(name):
            routing = entry.setdefault("routing", {})
            apply_routing_key(routing, name, value)
            if not routing:
                del entry["routing"]
        elif name in PROJECT_KEYS:
            defaults = entry.setdefault("defaults", {})
            path = SET_KEYS[name]
            if unset:
                node = defaults
                for part in path[:-1]:
                    node = node.get(part) or {}
                node.pop(path[-1], None)
                if len(path) > 1 and not defaults.get(path[0]):
                    defaults.pop(path[0], None)
            else:
                node = defaults
                for part in path[:-1]:
                    node = node.setdefault(part, {})
                node[path[-1]] = parse_set_value(name, value)
            if not defaults:
                del entry["defaults"]
        else:
            fail(EXIT_USAGE, f"Unknown key {name!r}. Keys: {', '.join(PROJECT_KEYS)}, {ROUTING_KEYS_HELP}.")
    new = copy.deepcopy(config)
    projects = new.setdefault("projects", {})
    if entry:
        projects[key] = entry
    else:
        projects.pop(key, None)
    errors = project_errors(new, key, entry) if entry else []
    if errors:
        fail(EXIT_USAGE, "Project values not saved:\n" + "\n".join(f"  - {e}" for e in errors))
    save_config(new)
    flat = flatten_project(entry)
    lines = [f"Project {key}:"] + ([f"  {k} = {json.dumps(v)}" for k, v in flat.items()] or ["  no project values"])
    emit(args, "\n".join(lines), {"project": key, "values": flat})
    return EXIT_OK


def cmd_project_set(args) -> int:
    return change_project(args, unset=False)


def cmd_project_unset(args) -> int:
    return change_project(args, unset=True)


def cmd_setup_snippets(args) -> int:
    config = load_config()
    root = str(worktree_root(config))
    sae = str(SKILL_DIR / "scripts" / "sae.py")
    codex_profile = f'''default_permissions = "shape-and-execute"

[permissions.shape-and-execute]
description = "workspace-write + git writes (hooks/config read-only) + sae worktree root"
extends = ":workspace"

[permissions.shape-and-execute.filesystem.":workspace_roots"]
".git" = "write"
".git/hooks" = "read"
".git/config" = "read"
".codex" = "read"
".agents" = "read"

[permissions.shape-and-execute.filesystem]
"{root}" = "write"

[agents]
max_threads = {CODEX_RECOMMENDED_SUBAGENTS}
'''
    claude = {"permissions": {"additionalDirectories": [root],
                              "allow": ["Bash(git *)", f"Bash(python3 {sae} *)", f"Edit(/{root}/**)"]}}
    profile_file = codex_home() / "shape-and-execute.config.toml"
    lines = [
        "## Codex",
        "Without a permission profile Codex keeps .git read-only and blocks the worktree root: every commit, "
        "merge and worktree fails. Option A (recommended) limits it to task sessions: save this as",
        f"  {profile_file}",
        "and start task sessions with `codex -p shape-and-execute`. Option B: put the same lines in the "
        "following file (every session; never define [permissions.*] there without default_permissions):",
        f"  {codex_home() / 'config.toml'}",
        "",
        codex_profile.rstrip(),
        "",
        codex_cap_text(codex_subagent_cap()),
        "",
        "## Claude Code",
        "The worktree root must be an additional directory. The allow rules are for users who do not run with "
        "bypassed permissions. Merge into ~/.claude/settings.json:",
        "",
        json.dumps(claude, indent=2),
    ]
    emit(args, "\n".join(lines), {"codex_profile_file": str(profile_file), "codex_profile": codex_profile,
                                  "codex_subagent_cap": codex_subagent_cap(), "claude_settings": claude})
    return EXIT_OK


def register_setup(sub, command):
    """Add the `setup` command group to the parser; returns the group parser."""
    setup = sub.add_parser("setup", help="Show, save or print harness snippets for the user config.",
                           description="sae setup <show|save|snippets> --help for details.")
    setup_sub = setup.add_subparsers(dest="setup_command", metavar="<show|save|snippets>", parser_class=Parser)
    command(setup_sub, "show", "Print the config readably, a schema-1 conversion, or a proposal skeleton.",
            "Facts: OS, claude and codex on PATH, the Codex catalog (families with their newest and older versions),\n"
            "the Codex subagent cap, the default worktree root. The config: model lists, tiers and one routing table\n"
            "per phase and harness, defaults, projects. A schema-1 config: the proposed schema-2 conversion.",
            ["setup show"], [0, 1], cmd_setup_show)
    command(setup_sub, "save", "Validate config JSON from stdin and write it (old file kept as .bak).",
            "Refuses unfilled <...> values, and any cell or tier whose model is not in the harness's model list\n"
            "or whose effort that model does not accept. With a Codex catalog it also refuses a Codex exact\n"
            "version that the catalog does not offer or hides, and an effort it does not list for that version.",
            ["setup save < proposal.json"], [0, 1], cmd_setup_save)
    command(setup_sub, "snippets", "Print harness permission snippets for the configured worktree root.",
            "Codex: a permission profile (git writes, worktree root) and the subagent cap. Claude Code:\n"
            "additionalDirectories and allow rules. Apply them only after the user agrees, with a backup.",
            ["setup snippets"], [0, 2], cmd_setup_snippets)
    return setup


def register_project(sub, command):
    """Add the `project` command group (project defaults in the user config); returns the group."""
    project = sub.add_parser("project", help="Show or change this repository's project defaults (user config).",
                             description="sae project <show|set|unset> --help for details.")
    project_sub = project.add_subparsers(dest="project_command", metavar="<show|set|unset>", parser_class=Parser)
    details = ("Project defaults are personal overrides for new tasks in one repository, kept in the user config\n"
               "under the repository's main worktree path; nothing is written into the repository. sae new copies\n"
               "the default keys into the new task; routing keys apply at every dispatch (task → project → global).\n"
               f"Default keys: {', '.join(PROJECT_KEYS)}.\nRouting keys: {ROUTING_KEYS_HELP}.")
    command(project_sub, "show", "Print each project value next to the global one (read-only).", details,
            ["project show"], [0, 1, 2], cmd_project_show)
    p = command(project_sub, "set", "Set project values; validates and writes the user config (backup kept).",
                details, ["project set execution=economy", "project set tier.codex.L2=<model>:medium"], [0, 1, 2],
                cmd_project_set)
    p.add_argument("pairs", nargs="+", metavar="key=value", help="project values to set")
    p = command(project_sub, "unset", "Return project keys to the global value.", details,
                ["project unset execution routing.codex.execution.economy.hard"], [0, 1, 2], cmd_project_unset)
    p.add_argument("pairs", nargs="+", metavar="key", help="keys to return to the global value")
    return project
