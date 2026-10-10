"""Commands setup show|save|snippets and the Codex facts they print."""

from __future__ import annotations

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
    DIFFICULTIES,
    EXIT_OK,
    EXIT_USAGE,
    HARNESSES,
    INTERACTION_MODES,
    LEVELS,
    LEVEL_PHASES,
    Parser,
    REVIEW_POINTS,
    RUNGS,
    SCHEMA_VERSION,
    SKILL_DIR,
    emit,
    fail,
    read_text,
    warn,
    write_json,
)
from .config import config_path, load_config, validate_config, worktree_root
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


def codex_cap_text(cap: dict) -> str:
    current = (f"{cap['subagents']} subagents ({cap['source']})" if cap["subagents"] is not None
               else "not set: Codex default, 3 subagents for multi-agent v2 models, 6 for v1")
    if cap["ok"]:
        return f"Codex subagent cap: {current}."
    return (f"Codex subagent cap: {current}. Below {cap['minimum']}: parallel writers, reviews and research "
            f"hit \"agent thread limit reached\".\n"
            f"Recommended, in {cap['config']}:\n  [agents]\n  max_threads = {cap['recommended']}\n"
            f"Setup mode can apply it after you agree (with a backup).")


def codex_models() -> list[dict] | None:
    if not shutil.which("codex"):
        return None
    try:
        proc = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL)
        models = json.loads(proc.stdout.strip().splitlines()[-1])["models"]
    except (subprocess.TimeoutExpired, OSError, ValueError, KeyError, IndexError):
        return None
    out = []
    for model in models:
        if model.get("visibility") not in (None, "list"):
            continue
        levels = model.get("supported_reasoning_levels") or []
        efforts = [lvl.get("effort") if isinstance(lvl, dict) else lvl for lvl in levels]
        out.append({"model": model.get("slug"), "efforts": [e for e in efforts if e]})
    return out


def setup_facts() -> dict:
    facts = {"os": platform.system(), "python": platform.python_version(), "config_path": str(config_path()),
             "claude_on_path": bool(shutil.which("claude")), "codex_on_path": bool(shutil.which("codex")),
             "default_worktree_root": default_worktree_root(), "git_on_path": bool(shutil.which("git"))}
    if facts["codex_on_path"]:
        facts["codex_models"] = codex_models()
        facts["codex_subagent_cap"] = codex_subagent_cap()
    return facts


def config_skeleton(facts: dict) -> dict:
    rungs = {}
    if facts["claude_on_path"]:
        rungs["claude"] = {r: {"model": "<alias your Agent tool accepts>"} for r in RUNGS}
    if facts["codex_on_path"]:
        rungs["codex"] = {r: {"model": "<id from codex_models>", "effort": "<effort>"} for r in RUNGS}
    return {
        "schema": SCHEMA_VERSION, "rungs": rungs,
        "level_map": {lvl: {d: "<L1|L2|L3>" for d in DIFFICULTIES} for lvl in LEVELS},
        "review_level_map": {lvl: "<L1|L2|L3>" for lvl in LEVELS},
        "defaults": {"interaction": f"<{'|'.join(INTERACTION_MODES)}>",
                     "levels": {p: f"<{'|'.join(LEVELS)}>" for p in LEVEL_PHASES},
                     "review": {"points": [f"<{'|'.join(REVIEW_POINTS)}>"], "provider": f"<{'|'.join(HARNESSES)}>"}},
        "language": {"conversation": "<code>", "artifacts": "<code>"},
        "worktrees": {"root": facts["default_worktree_root"]},
        "parallel": {"max_writers": "<integer>"},
        "verify": {"timeout_s": "<seconds>"},
    }


def cmd_setup_show(args) -> int:
    facts = setup_facts()
    config = load_config(required=False)
    lines = ["Detected:", f"  OS: {facts['os']} · Python {facts['python']} · git: {'yes' if facts['git_on_path'] else 'NO'}",
             f"  claude on PATH: {'yes' if facts['claude_on_path'] else 'no'} · "
             f"codex on PATH: {'yes' if facts['codex_on_path'] else 'no'}",
             f"  default worktree root: {facts['default_worktree_root']}"]
    if facts.get("codex_models"):
        lines.append("  Codex models: " + "; ".join(f"{m['model']} ({', '.join(m['efforts'])})"
                                                    for m in facts["codex_models"]))
    if facts.get("codex_subagent_cap"):
        lines.append("  " + codex_cap_text(facts["codex_subagent_cap"]).replace("\n", "\n  "))
    if config is not None:
        errors = validate_config(config)
        lines += ["", f"Current config ({config_path()}):", json.dumps(config, indent=2, ensure_ascii=False)]
        if errors:
            lines += ["Problems:"] + [f"  - {e}" for e in errors]
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
    errors = validate_config(data)
    if errors:
        fail(EXIT_USAGE, "Config not saved:\n" + "\n".join(f"  - {e}" for e in errors))
    path = config_path()
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    write_json(path, data)
    emit(args, f"Saved {path}" + (f" (backup: {path.name}.bak)" if path.with_name(path.name + '.bak').exists() else ""),
         {"path": str(path)})
    return EXIT_OK


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
        "Without a permission profile Codex keeps .git read-only and blocks the worktree root: every commit,",
        "merge and worktree fails. Option A (recommended) limits it to task sessions: save this as",
        f"  {profile_file}",
        "and start task sessions with `codex -p shape-and-execute`. Option B: put the same lines in",
        f"  {codex_home() / 'config.toml'} (every session; never define [permissions.*] there without",
        "  default_permissions).",
        "",
        codex_profile.rstrip(),
        "",
        codex_cap_text(codex_subagent_cap()),
        "",
        "## Claude Code",
        "The worktree root must be an additional directory. The allow rules are for users who do not run with",
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
    command(setup_sub, "show", "Print the config, or a proposal skeleton, with detected facts.",
            "Facts: OS, claude and codex on PATH, the Codex model list, the Codex subagent cap, the default worktree root.",
            ["setup show"], [0, 1], cmd_setup_show)
    command(setup_sub, "save", "Validate config JSON from stdin and write it (old file kept as .bak).", "",
            ["setup save < proposal.json"], [0, 1], cmd_setup_save)
    command(setup_sub, "snippets", "Print harness permission snippets for the configured worktree root.",
            "Codex: a permission profile (git writes, worktree root) and the subagent cap. Claude Code:\n"
            "additionalDirectories and allow rules. Apply them only after the user agrees, with a backup.",
            ["setup snippets"], [0, 2], cmd_setup_snippets)
    return setup
