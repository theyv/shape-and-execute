#!/usr/bin/env python3
"""sae: the command-line half of the shape-and-execute skill.

Agents decide; sae records, checks, computes and moves files and git refs. It never calls a
model, never pushes, and holds no configuration value of its own: models, level maps, the
worktree root and the defaults for new tasks come from the user config.

Run `sae --help` for every command, `sae <command> --help` for one command.
Python >= 3.10, standard library only, non-interactive.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
VIEWER_VERSION = 1

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_CONFIG = 2
EXIT_GATE = 3
EXIT_GIT = 4
EXIT_VERIFY = 5

EXIT_CODES_HELP = """\
Exit codes:
  0  ok
  1  usage or precondition error
  2  user config missing or invalid: offer setup mode
  3  gate refused: lint errors, approval or review missing
  4  git problem: dirty tree, merge conflict, worktree or setup failure
  5  re-run verify failed: resume the same worker"""

# The vocabulary of the skill. These are not configuration values: the skill's prose uses
# the same words, so changing one here means changing the skill.
PHASES = ("shaping", "planning", "executing", "done", "abandoned")
JOB_KINDS = ("research", "planning", "implementation", "integration", "validation", "review", "decision")
WRITER_KINDS = ("implementation", "integration")
JOB_STATUSES = ("pending", "running", "done", "failed", "parked")
DIFFICULTIES = ("mechanical", "normal", "hard")
LEVELS = ("economy", "balanced", "max")
LEVEL_PHASES = ("research", "planning", "execution", "review")
INTERACTION_MODES = ("full-auto", "auto", "critical-only", "collaborative", "interactive")
REVIEW_POINTS = ("spec", "plan", "selected-jobs", "all-jobs", "integration")
HARNESSES = ("claude", "codex")
RUNGS = ("L1", "L2", "L3")
DECISION_CLASSES = ("routine", "clear-choice", "open-tradeoff", "consequential", "spec-clarification", "spec-change")
VERDICTS = ("pass", "pass-with-notes", "changes-required")
FINDING_TYPES = ("friction", "defect", "follow-up")
CONFIDENCES = ("high", "medium", "low")
PROVENANCES = ("human", "agent", "joint")

KINDS_BY_PHASE = {
    "shaping": {"research", "review"},
    "planning": {"planning", "research", "review"},
    "executing": {"research", "implementation", "integration", "validation", "review", "decision"},
}
REVIEW_TARGET_BY_PHASE = {"shaping": "spec", "planning": "plan"}
LEVEL_PHASE_OF_KIND = {"research": "research", "planning": "planning"}  # every other kind: execution

# The mode table of references/interaction-modes.md, reduced to what sae prints.
ASK_CLASSES = {
    "full-auto": (),
    "auto": (),
    "critical-only": ("consequential", "spec-clarification", "spec-change"),
    "collaborative": ("open-tradeoff", "consequential", "spec-clarification", "spec-change"),
    "interactive": ("clear-choice", "open-tradeoff", "consequential", "spec-clarification", "spec-change"),
}
PARK_CLASSES = {"auto": ("spec-change",)}
HARD_STOPS_LINE = ("Hard stops: no push/deploy, no secrets, no CI/permission changes outside the plan, "
                   "no destroying what a job did not create.")

# DL-73: the limit of failed verify re-runs per job. A settings.json without the key uses it;
# `sae new` writes it into every new task unless config.defaults.max_verify_failures says otherwise.
DEFAULT_MAX_VERIFY_FAILURES = 3
STALE_RUNNING_MINUTES = 60   # `sae status`: a running job without change this long → "check on it"
BRIEF_MAX_LINES = 80         # `sae check`: warning above this length

# Codex shell detection: the Codex shell tool sets these in every command it runs
# (codex-cli 0.160.1; CODEX_SANDBOX is absent with danger-full-access, so it is not used).
CODEX_ENV_VARS = ("CODEX_THREAD_ID", "CODEX_SESSION_ID")
# Codex caps open subagents per session (agents.max_threads; default 3 for multi-agent v2
# models, 6 for v1). An orchestrator runs writers, reviews and research at once, so setup and
# doctor recommend raising a cap below the minimum.
CODEX_MIN_SUBAGENTS = 8
CODEX_RECOMMENDED_SUBAGENTS = 10

JOB_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")
TASK_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}--[a-z0-9][a-z0-9-]*$")
STAMPED_FILE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})--")

CONFIG_HINT = ('Run the shape-and-execute skill in setup mode: "/shape-and-execute setup" (Claude Code)\n'
               'or "$shape-and-execute setup" (Codex).')


class SaeError(Exception):
    """An error with the exit code it maps to."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def fail(code: int, message: str):
    raise SaeError(code, message)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------------------------
# Time, text and files


def now() -> dt.datetime:
    return dt.datetime.now().astimezone().replace(microsecond=0)


def iso(moment: dt.datetime | None = None) -> str:
    return (moment or now()).isoformat()


def file_stamp() -> str:
    return now().strftime("%Y-%m-%d-%H%M")


def stamp_time(name: str) -> str | None:
    """ISO time from a `YYYY-MM-DD-HHMM--slug` file or folder name."""
    m = STAMPED_FILE_RE.match(name)
    if not m:
        return None
    y, mo, d, h, mi = (int(x) for x in m.groups())
    return dt.datetime(y, mo, d, h, mi).astimezone().isoformat()


def age_text(when: str | None) -> str:
    if not when:
        return "never"
    try:
        seconds = (now() - dt.datetime.fromisoformat(when)).total_seconds()
    except ValueError:
        return when
    minutes = int(seconds // 60)
    if minutes < 1:
        return "just now"
    if minutes < 120:
        return f"{minutes} min ago"
    if minutes < 48 * 60:
        return f"{minutes // 60} h ago"
    return f"{minutes // (24 * 60)} d ago"


def minutes_since(when: str | None) -> float:
    if not when:
        return 0.0
    return (now() - dt.datetime.fromisoformat(when)).total_seconds() / 60


def slugify(text: str) -> str:
    text = text.replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return slug[:40].rstrip("-") or "task"


def read_text(path: Path, default: str | None = None) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def write_json(path: Path, data) -> None:
    write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------------------------
# Frontmatter and markdown (the small subset the skill's templates use)


def _strip_yaml_comment(line: str) -> str:
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _yaml_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(part) for part in _split_inline_list(inner)]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    if value in ("null", "~", ""):
        return None
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _split_inline_list(inner: str) -> list[str]:
    parts, current, quote = [], "", None
    for ch in inner:
        if quote:
            current += ch
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            current += ch
        elif ch == ",":
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Returns (frontmatter, body). Supports `key: scalar`, `key: [a, b]` and block lists."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return {}, text
    for end in range(1, len(lines)):
        if lines[end].rstrip("\r\n") == "---":
            break
    else:
        return {}, text
    data: dict = {}
    key = None
    for raw in lines[1:end]:
        line = _strip_yaml_comment(raw.rstrip("\r\n")).rstrip()
        if not line.strip():
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and key is not None and raw[:1] in (" ", "\t", "-"):
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_yaml_scalar(item.group(1)))
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if pair:
            key = pair.group(1)
            data[key] = _yaml_scalar(pair.group(2))
    return data, "".join(lines[end + 1:])


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def md_section(text: str, title: str, level: int = 2) -> str | None:
    """The text under the heading `<#*level> <title>` up to the next heading of the same or a
    higher level, or None when the heading is missing. Fenced code is not scanned."""
    out, inside, fence = [], False, False
    want = title.strip().lower()
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            depth = len(m.group(1))
            if inside and depth <= level:
                break
            if depth == level and m.group(2).strip().lower() == want:
                inside = True
                continue
        if inside:
            out.append(line)
    return "\n".join(out) if inside else None


def has_content(section: str | None) -> bool:
    if section is None:
        return False
    text = strip_html_comments(section)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped not in ("-", "- [ ]", "*"):
            return True
    return False


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.*)$", line)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------------------------
# Processes and git


def run(cmd: list[str], cwd: Path, check: bool = False, timeout: float | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=check,
                          timeout=timeout, env=env)


def git(cwd: Path, *args: str, check: bool = True) -> str:
    try:
        proc = run(["git", *args], cwd)
    except FileNotFoundError:
        fail(EXIT_GIT, "git is not installed")
    if check and proc.returncode != 0:
        fail(EXIT_GIT, f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()}")
    return proc.stdout.strip()


def git_ok(cwd: Path, *args: str) -> bool:
    try:
        return run(["git", *args], cwd).returncode == 0
    except FileNotFoundError:
        return False


def hash8(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:8]


def find_root() -> tuple[Path, bool]:
    """The repository root and whether it is a git repository.

    A job worktree (`<worktrees.root>/<repo>-<hash8>/<task-id>/<JOB-ID>`) resolves to its main
    checkout, so a worker's `sae finding new` writes to the one live `.tasks/`."""
    cwd = Path.cwd()
    top = None
    with contextlib.suppress(FileNotFoundError):
        proc = run(["git", "rev-parse", "--show-toplevel"], cwd)
        if proc.returncode == 0:
            top = Path(proc.stdout.strip())
    if top is not None:
        common = git(top, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False)
        if common:
            main = Path(common).parent
            if (main != top and TASK_ID_RE.match(top.parent.name)
                    and top.parent.parent.name == f"{main.name}-{hash8(main)}"):
                return main, True
        return top, True
    for folder in (cwd, *cwd.parents):
        if (folder / ".tasks").is_dir():
            return folder, False
    return cwd, False


def git_user(root: Path) -> str:
    name = git(root, "config", "user.name", check=False) if shutil.which("git") else ""
    if name:
        return name
    import getpass
    return getpass.getuser()


# ---------------------------------------------------------------------------------------------
# User config


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


def worktree_root(config: dict) -> Path:
    return Path(cfg(config, "worktrees.root")).expanduser()


# ---------------------------------------------------------------------------------------------
# Settings


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


# ---------------------------------------------------------------------------------------------
# Harness detection


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


# ---------------------------------------------------------------------------------------------
# Tasks


def tasks_dir(root: Path) -> Path:
    return root / ".tasks"


def list_task_ids(root: Path) -> list[str]:
    folder = tasks_dir(root)
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir()
                  if p.is_dir() and TASK_ID_RE.match(p.name) and (p / "state.json").exists())


def resolve_task(root: Path, ref: str) -> str:
    ref = ref.rstrip("/").split("/")[-1]
    ids = list_task_ids(root)
    if ref in ids:
        return ref
    matches = [i for i in ids if i.endswith(ref)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        fail(EXIT_USAGE, f"No task matches {ref!r} in {tasks_dir(root)}.")
    fail(EXIT_USAGE, f"{ref!r} matches several tasks: {', '.join(matches)}. Use more of the ID.")


class Task:
    """One task folder. Changes are buffered and written by `save()`."""

    def __init__(self, root: Path, task_id: str):
        self.root = root
        self.id = task_id
        self.dir = tasks_dir(root) / task_id
        self.state: dict = {}
        self.settings: dict = {}
        self.new_events: list[dict] = []
        self.dirty = False

    # paths
    @property
    def state_path(self) -> Path:
        return self.dir / "state.json"

    @property
    def settings_path(self) -> Path:
        return self.dir / "settings.json"

    @property
    def events_path(self) -> Path:
        return self.dir / "events.jsonl"

    # shortcuts
    @property
    def info(self) -> dict:
        return self.state["task"]

    @property
    def jobs(self) -> dict:
        return self.state["jobs"]

    @property
    def phase(self) -> str:
        return self.info["phase"]

    @property
    def uses_worktrees(self) -> bool:
        return bool(self.info.get("git")) and self.info.get("layout") == "worktrees"

    def job(self, job_id: str) -> dict:
        if job_id not in self.jobs:
            fail(EXIT_USAGE, f"No job {job_id} in task {self.id}.")
        return self.jobs[job_id]

    def load(self) -> None:
        self.state = read_json(self.state_path)
        try:
            settings = read_json(self.settings_path)
        except FileNotFoundError:
            fail(EXIT_USAGE, f"{self.settings_path} is missing.")
        except json.JSONDecodeError as exc:
            fail(EXIT_USAGE, f"{self.settings_path} is not valid JSON: {exc}")
        errors = settings_errors(settings)
        if errors:
            fail(EXIT_USAGE, f"{self.settings_path}: " + "; ".join(errors))
        self.settings = settings
        seen = self.info.get("settings_seen")
        if seen != settings:
            changes = settings_diff(seen or {}, settings)
            if changes:
                self.event("settings.changed", changes=changes, by="external")
            self.info["settings_seen"] = settings
            self.dirty = True

    def event(self, type_: str, **fields) -> None:
        self.new_events.append({"at": iso(), "type": type_, **fields})
        self.dirty = True

    def touch(self, job: dict | None = None) -> None:
        if job is not None:
            job["last_change"] = iso()
        self.dirty = True

    def events(self) -> list[dict]:
        events = []
        text = read_text(self.events_path, "")
        for line in text.splitlines():
            if line.strip():
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(line))
        return events + self.new_events

    def save(self) -> None:
        self.info["last_change"] = iso()
        write_json(self.state_path, self.state)
        if self.new_events:
            with self.events_path.open("a", encoding="utf-8") as handle:
                for event in self.new_events:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.new_events = []
        self.dirty = False

    def write_settings(self, settings: dict) -> None:
        write_json(self.settings_path, settings)
        self.settings = settings
        self.info["settings_seen"] = settings
        self.dirty = True


@contextlib.contextmanager
def open_task(root: Path, ref: str):
    """Locks the task, loads it, and saves it when the block ends without an exception.
    After the lock is released, a changed task re-renders the viewer data."""
    task = Task(root, resolve_task(root, ref))
    with (task.dir / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        task.load()
        yield task
        changed = task.dirty
        if changed:
            task.save()
    if changed:
        render_viewer_safely(root, [task.id])


def append_event_to(root: Path, ref: str, type_: str, **fields) -> None:
    """Appends one event to another task (backlog and finding sources)."""
    with open_task(root, ref) as task:
        task.event(type_, **fields)


def ensure_tasks_folder(root: Path) -> None:
    folder = tasks_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / ".gitignore").exists():
        write_atomic(folder / ".gitignore", ".viewer/\n.lock\n")
    if not (folder / ".gitattributes").exists():
        write_atomic(folder / ".gitattributes", "findings/closed.md merge=union\n")


def template(name: str) -> str:
    text = read_text(SKILL_DIR / "templates" / name)
    if text is None:
        fail(EXIT_USAGE, f"Template {SKILL_DIR / 'templates' / name} is missing: the skill is incomplete.")
    return text


def new_job(kind: str, needs: list[str], difficulty: str, review: bool = False, final: bool = False,
            fix_of: str | None = None, target: str | None = None) -> dict:
    return {
        "kind": kind, "needs": needs, "difficulty": difficulty, "review": review, "final": final,
        "fix_of": fix_of, "target": target, "status": "pending", "merged": False,
        "review_rounds": 0, "last_change": iso(), "attempts": [], "commits": [],
    }


def is_generated(job_id: str, job: dict) -> bool:
    """Jobs that sae adds itself: reviews and integration jobs. They have no job file."""
    return job["kind"] == "review" or job_id.startswith("INTEGRATE-")


def job_file(task: Task, job_id: str) -> Path:
    return task.dir / "jobs" / f"{job_id}.md"


def result_file(task: Task, job_id: str) -> Path:
    kind = task.jobs[job_id]["kind"]
    if kind == "research":
        return task.dir / "research" / f"{job_id}.md"
    if kind == "review":
        return task.dir / "reviews" / f"{job_id}.md"
    if kind == "decision":
        return task.dir / "decisions" / f"{job_id}.md"
    return task.dir / "jobs" / f"{job_id}.result.md"


def job_meta(task: Task, job_id: str) -> dict:
    text = read_text(job_file(task, job_id))
    return split_frontmatter(text)[0] if text else {}


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None and v != ""]
    return [value]


# ---------------------------------------------------------------------------------------------
# Graph and readiness


def ancestors(jobs: dict, job_id: str) -> set[str]:
    seen: set[str] = set()
    stack = list(jobs.get(job_id, {}).get("needs", []))
    while stack:
        current = stack.pop()
        if current in seen or current not in jobs:
            continue
        seen.add(current)
        stack.extend(jobs[current]["needs"])
    return seen


def find_cycle(jobs: dict) -> list[str] | None:
    color: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = 1
        path.append(node)
        for need in jobs[node]["needs"]:
            if need not in jobs:
                continue
            if color.get(need) == 1:
                return path[path.index(need):] + [need]
            if color.get(need) is None:
                found = visit(need)
                if found:
                    return found
        color[node] = 2
        path.pop()
        return None

    for job_id in jobs:
        if color.get(job_id) is None:
            found = visit(job_id)
            if found:
                return found
    return None


def parallel_possible(jobs: dict, a: str, b: str) -> bool:
    return a not in ancestors(jobs, b) and b not in ancestors(jobs, a)


def kind_allowed_now(task: Task, job: dict) -> bool:
    phase = task.phase
    if job["kind"] not in KINDS_BY_PHASE.get(phase, set()):
        return False
    if job["kind"] == "review" and phase in REVIEW_TARGET_BY_PHASE:
        return job.get("target") == REVIEW_TARGET_BY_PHASE[phase]
    return True


def waits_for(task: Task, job_id: str) -> list[str]:
    """What a pending job waits for; empty when it is ready."""
    jobs = task.jobs
    job = jobs[job_id]
    reasons = []
    for need in job["needs"]:
        other = jobs.get(need)
        if other is None:
            reasons.append(f"{need} (unknown job)")
        elif other["status"] != "done":
            reasons.append(need)
        elif (other["kind"] in WRITER_KINDS and task.uses_worktrees and not other["merged"]
              and job.get("target") != need):  # reviews and integration jobs work on their unmerged target
            reasons.append(f"{need} (merge)")
    if job["final"]:
        open_jobs = [i for i, j in jobs.items() if i != job_id and j["status"] != "done"]
        if open_jobs:
            reasons.append("all other jobs: " + ", ".join(open_jobs))
    if not kind_allowed_now(task, job):
        reasons.append(f"phase {task.phase}")
    return reasons


def is_ready(task: Task, job_id: str) -> bool:
    return task.jobs[job_id]["status"] == "pending" and not waits_for(task, job_id)


def scopes_overlap(a: list[str], b: list[str]) -> bool:
    def prefix(pattern: str) -> str:
        return re.split(r"[*?\[]", pattern, maxsplit=1)[0]

    for pa in a:
        for pb in b:
            x, y = prefix(pa), prefix(pb)
            if x.startswith(y) or y.startswith(x):
                return True
    return False


def writer_slots(task: Task, config: dict | None) -> int:
    if task.uses_worktrees:
        return int(cfg(config, "parallel.max_writers"))
    return 1


def writer_blocked(task: Task, job_id: str, config: dict | None) -> str | None:
    """Why a ready writer job cannot start now, or None."""
    running = [i for i, j in task.jobs.items() if j["kind"] in WRITER_KINDS and j["status"] == "running" and i != job_id]
    if not running:
        return None
    if not task.info.get("git"):
        # Without git a second writer runs only when both declare disjoint scopes.
        mine = as_list(job_meta(task, job_id).get("scope"))
        if len(running) == 1:
            theirs = as_list(job_meta(task, running[0]).get("scope"))
            if mine and theirs and not scopes_overlap(mine, theirs):
                return None
        return f"writer running: {', '.join(running)}"
    if len(running) >= writer_slots(task, config):
        return f"all writer slots busy: {', '.join(running)}"
    return None


# ---------------------------------------------------------------------------------------------
# Model resolution (07-cli-spec §5)


def resolve_model(task: Task, job: dict, config: dict, harness: str | None = None,
                  provider: str | None = None) -> dict:
    settings = task.settings
    if job["kind"] == "review":
        chosen = provider or harness or settings["review"]["provider"]
        rung = cfg(config, f"review_level_map.{settings['levels']['review']}")
    else:
        chosen = harness or task.info.get("orchestrator_harness")
        if not chosen:
            fail(EXIT_USAGE, "The task has no orchestrator harness. Add --harness claude|codex.")
        level = settings["levels"][LEVEL_PHASE_OF_KIND.get(job["kind"], "execution")]
        rung = cfg(config, f"level_map.{level}.{job['difficulty']}")
    entry = cfg(config, f"rungs.{chosen}.{rung}")
    model = cfg(config, f"rungs.{chosen}.{rung}.model")
    effort = entry.get("effort") if chosen == "codex" else None
    return {"harness": chosen, "rung": rung, "model": model, "effort": effort}


# ---------------------------------------------------------------------------------------------
# Requirement IDs and lint (07-cli-spec `sae check`)


REQ_HEADING_RE = re.compile(r"^###\s+\[([^\]]*)\]")
ACCEPT_ITEM_RE = re.compile(r"^\s*[-*]\s+\[([^\]]*)\]")


def requirement_ids(task: Task) -> tuple[list[str], list[str], list[str]]:
    """(requirement IDs, errors, warnings) from specs.md `## Requirements` and the intent's
    `## Acceptance`."""
    ids: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    seen_heading_ids: dict[str, int] = {}
    spec = read_text(task.dir / "specs.md")
    if spec is not None:
        clean = strip_html_comments(spec)
        fence = False
        for line in clean.splitlines():
            if line.lstrip().startswith("```"):
                fence = not fence
            m = None if fence else REQ_HEADING_RE.match(line)
            if m:
                seen_heading_ids[m.group(1)] = seen_heading_ids.get(m.group(1), 0) + 1
        for heading_id, count in seen_heading_ids.items():
            if not JOB_ID_RE.match(heading_id):
                errors.append(f"specs.md: invalid ID [{heading_id}] (use UPPER-KEBAB)")
            elif count > 1:
                errors.append(f"specs.md: duplicate ID [{heading_id}]")
        requirements = md_section(clean, "Requirements") or ""
        current, has_checks = None, False
        for line in requirements.splitlines() + ["### [END-OF-SECTION]"]:
            m = REQ_HEADING_RE.match(line)
            if m:
                if current and JOB_ID_RE.match(current):
                    ids.append(current)
                    if not has_checks:
                        warnings.append(f"specs.md: requirement [{current}] has no acceptance checks")
                current, has_checks = m.group(1), False
            elif re.match(r"^\s*[-*]\s+\[[ xX]\]", line):
                has_checks = True
    intent = read_text(task.dir / "intent.md", "")
    acceptance = md_section(strip_html_comments(intent), "Acceptance")
    for line in (acceptance or "").splitlines():
        m = ACCEPT_ITEM_RE.match(line)
        if not m or m.group(1).strip() in ("", "x", "X"):
            continue
        item_id = m.group(1)
        if not JOB_ID_RE.match(item_id):
            errors.append(f"intent.md: invalid acceptance ID [{item_id}] (use UPPER-KEBAB)")
        elif item_id in ids:
            errors.append(f"intent.md: duplicate ID [{item_id}]")
        else:
            ids.append(item_id)
    return ids, errors, warnings


def hot_files(root: Path) -> list[str]:
    profile = read_text(tasks_dir(root) / "repo" / "profile.md")
    if not profile:
        return []
    section = strip_html_comments(md_section(profile, "Hot files") or "")
    return [m.group(1).strip() for m in re.finditer(r"^\s*[-*]\s+(.+)$", section, flags=re.M)]


def lint_plan(task: Task) -> tuple[list[str], list[str]]:
    jobs = task.jobs
    errors: list[str] = []
    warnings: list[str] = []
    req_ids, req_errors, _ = requirement_ids(task)
    errors.extend(req_errors)
    covered: set[str] = set()
    metas = {}
    for job_id, job in jobs.items():
        if not JOB_ID_RE.match(job_id):
            errors.append(f"{job_id}: invalid job ID")
        if job["kind"] not in JOB_KINDS:
            errors.append(f"{job_id}: invalid kind {job['kind']}")
        for need in job["needs"]:
            if need not in jobs:
                errors.append(f"{job_id}: needs unknown job {need}")
        if is_generated(job_id, job):
            continue
        text = read_text(job_file(task, job_id))
        if text is None:
            errors.append(f"{job_id}: no job file jobs/{job_id}.md")
            continue
        meta, body = split_frontmatter(text)
        metas[job_id] = meta
        objective = md_section(body, "Objective")
        if not has_content(objective):
            errors.append(f"{job_id}: the job file has no objective")
        else:
            sentence_ends = re.findall(r"[.!?](?:\s|$)", strip_html_comments(objective).strip())
            if len(sentence_ends) > 1:
                warnings.append(f"{job_id}: the objective is longer than one sentence")
        for req in as_list(meta.get("covers")):
            if req not in req_ids:
                errors.append(f"{job_id}: covers [{req}], which does not exist")
            elif job["kind"] != "review":
                covered.add(req)
        if job["kind"] in WRITER_KINDS + ("validation",) and not as_list(meta.get("verify")):
            warnings.append(f"{job_id}: no verify commands (only judgement checks this job)")
    cycle = find_cycle(jobs)
    if cycle:
        errors.append("cycle in needs: " + " → ".join(cycle))
    for req in req_ids:
        if req not in covered:
            errors.append(f"requirement [{req}] is not covered by any job")
    finals = [i for i, j in jobs.items() if j["final"]]
    if len(finals) > 1:
        errors.append(f"more than one final job: {', '.join(finals)}")
    writers = [i for i, j in jobs.items() if j["kind"] in WRITER_KINDS and j["status"] in ("pending", "running")]
    hot = hot_files(task.root)
    if not cycle:
        for index, a in enumerate(writers):
            for b in writers[index + 1:]:
                if not parallel_possible(jobs, a, b):
                    continue
                sa, sb = as_list(metas.get(a, {}).get("scope")), as_list(metas.get(b, {}).get("scope"))
                if sa and sb and scopes_overlap(sa, sb):
                    warnings.append(f"{a} and {b} can run in parallel and their scopes overlap")
                elif hot and (not sa or not sb):
                    warnings.append(f"{a} and {b} can run in parallel, one has no scope, and the repo has hot files")
    brief = read_text(task.dir / "brief.md")
    if brief is not None and len(brief.splitlines()) > BRIEF_MAX_LINES:
        warnings.append(f"brief.md has {len(brief.splitlines())} lines (keep it under {BRIEF_MAX_LINES})")
    planned = [i for i, j in jobs.items() if not is_generated(i, j) and j["kind"] not in ("planning", "research")]
    if len(planned) >= 2:
        plan = read_text(task.dir / "plan.md")
        if plan is None or not has_content(md_section(plan, "Riskiest assumptions")):
            warnings.append('plan.md has no "Riskiest assumptions" section')
    return errors, warnings


def add_generated_job(task: Task, job_id: str, kind: str, needs: list[str], difficulty: str,
                      target: str | None, reason: str) -> dict:
    job = new_job(kind, needs, difficulty, target=target)
    task.jobs[job_id] = job
    task.event("job.added", job=job_id, kind=kind, needs=needs, difficulty=difficulty, target=target,
               reason=reason, by="sae")
    return job


def run_check(task: Task) -> tuple[list[str], list[str], list[str]]:
    """Lints by phase and materializes due spec and plan reviews. Returns (errors, warnings,
    added job IDs)."""
    added: list[str] = []
    points = task.settings["review"]["points"]
    if task.phase == "shaping":
        _, errors, warnings = requirement_ids(task)
        task.event("spec.checked", errors=len(errors), warnings=len(warnings))
        if (not errors and "spec" in points and (task.dir / "specs.md").exists()
                and not any(j["kind"] == "review" and j.get("target") == "spec" for j in task.jobs.values())):
            add_generated_job(task, "REVIEW-SPEC", "review", [], "normal", "spec", "spec review is a review point")
            added.append("REVIEW-SPEC")
        return errors, warnings, added
    errors, warnings = lint_plan(task)
    task.event("plan.checked", errors=len(errors), warnings=len(warnings))
    if (task.phase == "planning" and not errors and "plan" in points
            and not any(j["kind"] == "review" and j.get("target") == "plan" for j in task.jobs.values())):
        add_generated_job(task, "REVIEW-PLAN", "review", [], "normal", "plan", "plan review is a review point")
        added.append("REVIEW-PLAN")
    return errors, warnings, added


# ---------------------------------------------------------------------------------------------
# Output helpers


def emit(args, text: str, data=None) -> None:
    if getattr(args, "json", False):
        print(json.dumps(data if data is not None else {"text": text}, indent=2, ensure_ascii=False))
    elif text:
        print(text)


def table(rows: list[list[str]], indent: str = "  ") -> str:
    if not rows:
        return ""
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    return "\n".join(indent + "  ".join(str(c).ljust(w) for c, w in zip(row, widths)).rstrip() for row in rows)


def sae_prefix() -> str:
    return f"python3 {shlex.quote(str(SKILL_DIR / 'scripts' / 'sae.py'))}"


def mode_line(mode: str) -> str:
    ask, park = ASK_CLASSES[mode], PARK_CLASSES.get(mode, ())
    parts = []
    if ask:
        parts.append("ask on: " + ", ".join(ask))
    if park:
        parts.append("park on: " + ", ".join(park))
    if not parts:
        parts.append("decide every class yourself and log it with --by agent")
    return f"Mode: {mode} — " + "; ".join(parts) + "."


def last_model(job: dict) -> str:
    if not job["attempts"]:
        return "-"
    attempt = job["attempts"][-1]
    effort = f" ({attempt['effort']})" if attempt.get("effort") else ""
    return f"{attempt['model']}{effort}"


def job_summary(task: Task, job_id: str) -> str:
    job = task.jobs[job_id]
    return job.get("summary") or ""


def parked_reason(task: Task, job_id: str) -> str:
    summary = job_summary(task, job_id)
    path = result_file(task, job_id)
    text = read_text(path)
    if text:
        request = md_section(split_frontmatter(text)[1], "Decision request")
        if has_content(request):
            first = [l.strip() for l in strip_html_comments(request).splitlines() if l.strip()][:2]
            return (summary + " — " if summary else "") + " ".join(first)
    return summary or "see the result file"


# ---------------------------------------------------------------------------------------------
# Viewer data (07-cli-spec §12, 13-viewer-spec)


def render_viewer_safely(root: Path, task_ids: list[str] | None = None) -> Path | None:
    try:
        return render_viewer(root, task_ids)
    except Exception as exc:  # rendering never fails a command
        warn(f"viewer not rendered: {exc}")
        return None


def render_viewer(root: Path, task_ids: list[str] | None = None) -> Path:
    """Writes .tasks/.viewer/: the shell (when missing or older), data/index.js, and
    data/<task-id>.js for the given tasks (None: every task of every checkout)."""
    viewer = tasks_dir(root) / ".viewer"
    shell = SKILL_DIR / "assets" / "viewer" / "index.html"
    target = viewer / "index.html"
    if shell.exists():
        if viewer_version(target) < viewer_version(shell):
            viewer.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(shell, target)
    else:
        warn(f"viewer shell {shell} is missing; data only")
    checkouts = task_locations(root)
    index = build_index(root, checkouts)
    write_atomic(viewer / "data" / "index.js", "window.SAE_INDEX = " + json.dumps(index, ensure_ascii=False) + ";\n")
    wanted = set(checkouts) if task_ids is None else set(task_ids) & set(checkouts)
    for task_id in sorted(wanted):
        data = build_task_data(checkouts[task_id] / task_id)
        write_atomic(viewer / "data" / f"{task_id}.js",
                     "window.SAE_TASKS = window.SAE_TASKS || {};\n"
                     f"window.SAE_TASKS[{json.dumps(task_id)}] = " + json.dumps(data, ensure_ascii=False) + ";\n")
    return target


def viewer_version(path: Path) -> int:
    text = read_text(path)
    if not text:
        return 0
    m = re.search(r'<meta\s+name="sae-viewer-version"\s+content="(\d+)"', text)
    return int(m.group(1)) if m else 0


def task_locations(root: Path) -> dict[str, Path]:
    """Task ID → the .tasks folder that holds its newest copy, across every checkout of the
    repository except job worktrees."""
    checkouts = [root]
    if git_ok(root, "rev-parse", "--git-dir"):
        listing = git(root, "worktree", "list", "--porcelain", check=False)
        for line in listing.splitlines():
            if line.startswith("worktree "):
                path = Path(line[len("worktree "):])
                if path.resolve() != root.resolve() and not is_job_worktree(path):
                    checkouts.append(path)
    found: dict[str, tuple[str, Path]] = {}
    for checkout in checkouts:
        for task_id in list_task_ids(checkout):
            folder = tasks_dir(checkout)
            with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
                last = read_json(folder / task_id / "state.json")["task"].get("last_change", "")
                if task_id not in found or last > found[task_id][0]:
                    found[task_id] = (last, folder)
    return {task_id: folder for task_id, (_, folder) in found.items()}


def is_job_worktree(path: Path) -> bool:
    return bool(TASK_ID_RE.match(path.parent.name)) and bool(JOB_ID_RE.match(path.name))


def stamped_items(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.glob("*.md") if STAMPED_FILE_RE.match(p.name)), reverse=True)


def build_index(root: Path, locations: dict[str, Path]) -> dict:
    tasks = []
    for task_id, folder in locations.items():
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            state = read_json(folder / task_id / "state.json")
            counts: dict[str, int] = {}
            for job in state["jobs"].values():
                counts[job["status"]] = counts.get(job["status"], 0) + 1
            info = state["task"]
            entry = {"id": task_id, "title": info.get("title"), "phase": info.get("phase"),
                     "last_change": info.get("last_change"), "counts": counts,
                     "parked": counts.get("parked", 0), "plan_approved": "plan" in info.get("approvals", {}),
                     "branch": info.get("branch")}
            checkout = folder.parent
            if checkout.resolve() != root.resolve():
                entry["checkout"] = str(checkout)
            tasks.append(entry)
    tasks.sort(key=lambda t: t["id"], reverse=True)
    findings = []
    for path in stamped_items(tasks_dir(root) / "findings"):
        meta, body = split_frontmatter(read_text(path, ""))
        findings.append({"file": rel(path, root), "title": first_heading(body) or path.stem,
                         "type": meta.get("type"), "confidence": meta.get("confidence"),
                         "source": meta.get("source"), "created": stamp_time(path.name), "text": body})
    backlog = []
    for path in stamped_items(tasks_dir(root) / "backlog"):
        meta, body = split_frontmatter(read_text(path, ""))
        title = first_heading(body) or path.stem
        backlog.append({"file": rel(path, root), "title": re.sub(r"^Intent:\s*", "", title),
                        "source": meta.get("source"), "created": stamp_time(path.name), "text": body})
    return {
        "generated": iso(), "viewer_version": VIEWER_VERSION, "repo": root.name, "root": str(root),
        "sae": sae_prefix(), "tasks": tasks, "findings": findings, "backlog": backlog,
        "closed_findings": read_text(tasks_dir(root) / "findings" / "closed.md", ""),
    }


def build_task_data(folder: Path) -> dict:
    files = {}
    for name in ("intent.md", "specs.md", "brief.md", "plan.md"):
        text = read_text(folder / name)
        if text is not None:
            files[name] = text
    for sub in ("jobs", "research", "reviews", "decisions"):
        directory = folder / sub
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix in (".md", ".log"):
                    files[f"{sub}/{path.name}"] = read_text(path, "")
    events = []
    for line in read_text(folder / "events.jsonl", "").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            if line.strip():
                events.append(json.loads(line))
    settings = None
    with contextlib.suppress(OSError, json.JSONDecodeError):
        settings = read_json(folder / "settings.json")
    return {"generated": iso(), "state": read_json(folder / "state.json"), "settings": settings,
            "settings_default_max_verify_failures": DEFAULT_MAX_VERIFY_FAILURES,
            "events": events, "files": files, "folder": str(folder)}


# ---------------------------------------------------------------------------------------------
# Workspaces and worktrees (07-cli-spec §7)


def job_branch(task: Task, job_id: str) -> str:
    return f"job/{task.id}/{job_id}"


def task_worktrees_dir(task: Task, config: dict) -> Path:
    return worktree_root(config) / f"{task.root.name}-{hash8(task.root)}" / task.id


def workspace_owner(task: Task, job_id: str) -> str:
    """Fix jobs work in the workspace of the job they fix."""
    return task.jobs[job_id].get("fix_of") or job_id


def workspace_of(task: Task, job_id: str, config: dict | None) -> tuple[Path, str | None]:
    """(workdir, branch) of a job, without creating anything."""
    job = task.jobs[job_id]
    if job["kind"] not in WRITER_KINDS or not task.info.get("git"):
        return task.root, None
    if not task.uses_worktrees:
        return task.root, task.info.get("branch")
    owner = workspace_owner(task, job_id)
    return task_worktrees_dir(task, config) / owner, job_branch(task, owner)


def tracked_changes_outside_tasks(root: Path) -> list[str]:
    proc = run(["git", "status", "--porcelain", "--untracked-files=no"], root)
    if proc.returncode != 0:
        fail(EXIT_GIT, f"git status failed: {proc.stderr.strip()}")
    paths = []
    for line in proc.stdout.splitlines():  # unstripped: the first column is significant
        path = line[3:].split(" -> ")[-1].strip('"')
        if not path.startswith(".tasks/"):
            paths.append(path)
    return paths


def require_on_task_branch(task: Task) -> None:
    branch = task.info.get("branch")
    current = git(task.root, "branch", "--show-current", check=False)
    if current != branch:
        fail(EXIT_GIT, f"The repository root is on {current or 'a detached HEAD'}, not on {branch}. "
                       f"Run: git switch {branch}")
    dirty = tracked_changes_outside_tasks(task.root)
    if dirty:
        fail(EXIT_GIT, "Tracked files outside .tasks/ have uncommitted changes in the repository root: "
                       + ", ".join(dirty[:10]))


def copy_worktree_includes(root: Path, worktree: Path) -> list[str]:
    copied = []
    for pattern_file in (tasks_dir(root) / "repo" / "worktreeinclude", root / ".worktreeinclude"):
        if not pattern_file.exists():
            continue
        listing = git(root, "ls-files", "--others", "--ignored", f"--exclude-from={pattern_file}", check=False)
        candidates = [line for line in listing.splitlines() if line]
        if not candidates:
            continue
        proc = subprocess.run(["git", "check-ignore", "--stdin"], cwd=str(root), input="\n".join(candidates),
                              capture_output=True, text=True)
        for path in proc.stdout.splitlines():
            source, dest = root / path, worktree / path
            if source.is_file() and not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                copied.append(path)
    return copied


def run_setup_script(root: Path, worktree: Path, task_id: str, job_id: str, log: Path) -> None:
    """Runs .tasks/repo/setup.sh in a new worktree; a non-zero exit is exit 4."""
    script = tasks_dir(root) / "repo" / "setup.sh"
    if not script.exists():
        return
    env = {**os.environ, "SAE_REPO_ROOT": str(root), "SAE_WORKTREE": str(worktree),
           "SAE_TASK": task_id, "SAE_JOB": job_id}
    proc = subprocess.run(["sh", str(script)], cwd=str(worktree), capture_output=True, text=True, env=env)
    write_atomic(log, f"$ sh {script}\nexit {proc.returncode}\n\n{proc.stdout}\n{proc.stderr}")
    if proc.returncode != 0:
        fail(EXIT_GIT, f"Worktree setup failed (exit {proc.returncode}). Log: {log}\n"
                       f"The worktree is kept for inspection: {worktree}")


def prepare_workspace(task: Task, job_id: str, config: dict | None) -> tuple[Path, str | None]:
    job = task.jobs[job_id]
    workdir, branch = workspace_of(task, job_id, config)
    if job["kind"] not in WRITER_KINDS or not task.info.get("git"):
        return workdir, branch
    if not task.uses_worktrees:
        require_on_task_branch(task)
        return workdir, branch
    owner = workspace_owner(task, job_id)
    fresh = not task.jobs[owner]["attempts"]
    if not workdir.exists():
        workdir.parent.mkdir(parents=True, exist_ok=True)
        if git_ok(task.root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
            git(task.root, "worktree", "add", str(workdir), branch)
        else:
            git(task.root, "worktree", "add", "-b", branch, str(workdir), task.info["branch"])
        copy_worktree_includes(task.root, workdir)
        fresh = True
    if fresh:
        run_setup_script(task.root, workdir, task.id, job_id, task.dir / "jobs" / f"{job_id}.setup.log")
        if job["kind"] == "integration" and job.get("target"):
            # The worker resolves the conflicts of this merge; a non-zero exit is expected.
            run(["git", "merge", "--no-commit", "--no-ff", job_branch(task, job["target"])], workdir)
    return workdir, branch


def remove_worktree(task: Task, path: Path) -> bool:
    if not path.exists():
        return True
    proc = run(["git", "worktree", "remove", str(path)], task.root)
    if proc.returncode != 0:
        warn(f"worktree kept (it has changes): {path}")
        return False
    return True


def remove_task_worktrees(task: Task, config: dict | None) -> list[str]:
    if not task.info.get("git") or config is None or "worktrees" not in config:
        return []
    folder = task_worktrees_dir(task, config)
    kept = []
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.is_dir() and not remove_worktree(task, path):
                kept.append(str(path))
        with contextlib.suppress(OSError):
            folder.rmdir()
    git(task.root, "worktree", "prune", check=False)
    return kept


# ---------------------------------------------------------------------------------------------
# Dispatch prompts (07-cli-spec §9)


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
        effort = f" -c model_reasoning_effort={q(model['effort'])}" if model.get("effort") else ""
        return (f"rm -f {q(str(result))} && codex exec -m {q(model['model'])}{effort} -s read-only "
                f"-C {q(str(task.root))} -o {q(str(result))} --ephemeral {q(prompt)} < /dev/null")
    return (f"cd {q(str(task.root))} && claude -p {q(prompt)} --model {q(model['model'])} --permission-mode dontAsk "
            f"--allowedTools {q('Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(git show *)')} "
            f"> {q(str(result))}")


# ---------------------------------------------------------------------------------------------
# Collect, verify, merge (07-cli-spec §8, §10, §11)


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


# ---------------------------------------------------------------------------------------------
# Commands: tasks


def cmd_new(args) -> int:
    root, is_git = find_root()
    title = args.title.strip()
    if not title:
        fail(EXIT_USAGE, "The title is empty.")
    slug = slugify(args.slug or title)
    if args.backlog:
        return new_backlog_item(args, root, title, slug)
    config = load_config()
    defaults = cfg(config, "defaults")
    settings = {"schema": SCHEMA_VERSION, "interaction": cfg(config, "defaults.interaction"),
                "levels": dict(cfg(config, "defaults.levels")), "review": dict(cfg(config, "defaults.review")),
                "max_verify_failures": defaults.get("max_verify_failures", DEFAULT_MAX_VERIFY_FAILURES)}
    errors = settings_errors(settings)
    if errors:
        fail(EXIT_CONFIG, f"config.defaults: {'; '.join(errors)}.\n{CONFIG_HINT}")
    harness = require_harness(args.harness)
    from_item = None
    intent = template("intent.md").replace("<title>", title)
    if args.from_file:
        item = Path(args.from_file)
        item = item if item.is_absolute() else (Path.cwd() / item)
        text = read_text(item)
        if text is None:
            fail(EXIT_USAGE, f"No backlog item at {item}.")
        meta, body = split_frontmatter(text)
        intent = body.lstrip("\n")
        from_item = {"file": rel(item, root), "source": meta.get("source")}
    task_id = f"{file_stamp()}--{slug}"
    folder = tasks_dir(root) / task_id
    if folder.exists():
        fail(EXIT_USAGE, f"Task {task_id} exists. Choose another --slug.")
    ensure_tasks_folder(root)
    folder.mkdir()
    author = git_user(root)
    write_atomic(folder / "intent.md", intent)
    write_json(folder / "settings.json", settings)
    state = {"schema": SCHEMA_VERSION, "task": {
        "id": task_id, "title": title, "created": iso(), "author": author, "phase": "shaping", "git": is_git,
        "layout": None, "orchestrator_harness": harness, "branch": None, "base": None, "approvals": {},
        "settings_seen": settings, "last_change": iso()}, "jobs": {}}
    write_json(folder / "state.json", state)
    event = {"at": iso(), "type": "task.created", "title": title, "author": author}
    if from_item:
        event["from"] = from_item
    write_atomic(folder / "events.jsonl", json.dumps(event, ensure_ascii=False) + "\n")
    if from_item:
        os.remove(root / from_item["file"])
    render_viewer_safely(root, [task_id])
    text = (f"Task: {task_id}\nFolder: {folder}\nIntent: {folder / 'intent.md'}\n"
            f"Settings: {settings_card(settings)}")
    if from_item:
        text += f"\nPicked up from the backlog: {from_item['file']} (sae start commits its removal)."
    emit(args, text, {"task": task_id, "folder": str(folder), "intent": str(folder / "intent.md"),
                      "settings": settings, "from": from_item})
    return EXIT_OK


def new_backlog_item(args, root: Path, title: str, slug: str) -> int:
    source = resolve_task(root, args.source) if args.source else None
    ensure_tasks_folder(root)
    path = tasks_dir(root) / "backlog" / f"{file_stamp()}--{slug}.md"
    if path.exists():
        fail(EXIT_USAGE, f"{path} exists. Choose another --slug.")
    body = template("intent.md").replace("<title>", title)
    front = f"---\nsource: {source}   # the task during which the owner deferred the work\n---\n\n" if source else ""
    write_atomic(path, front + body)
    if source:
        append_event_to(root, source, "backlog.created", file=rel(path, root))
    else:
        render_viewer_safely(root, [])
    emit(args, f"Backlog item: {path}", {"file": str(path), "source": source})
    return EXIT_OK


def next_command(task: Task) -> str:
    phase, jobs = task.phase, task.jobs
    ready = [i for i in jobs if is_ready(task, i)]
    if phase == "shaping":
        if ready:
            return f"sae dispatch {task.id} {ready[0]}"
        if any(j["status"] == "running" for j in jobs.values()):
            return f"sae collect {task.id} <ID> when the subagent returns"
        return f"sae check {task.id}, then sae approve {task.id} spec"
    if phase == "planning":
        if ready:
            return f"sae dispatch {task.id} {ready[0]}"
        if any(j["status"] == "running" for j in jobs.values()):
            return f"sae collect {task.id} <ID> when the subagent returns"
        if "plan" in task.info["approvals"]:
            return f"sae start {task.id}"
        return f"sae check {task.id}, then sae approve {task.id} plan"
    if phase == "executing":
        return f"sae next {task.id}"
    return "none"


def task_status_data(task: Task) -> dict:
    rows, parked, ready, warnings = [], [], [], []
    for job_id, job in task.jobs.items():
        rows.append({"id": job_id, "kind": job["kind"], "status": job["status"], "merged": job["merged"],
                     "last_change": job["last_change"], "model": last_model(job),
                     "attempts": len(job["attempts"]), "needs": job["needs"], "difficulty": job["difficulty"]})
        if job["status"] == "parked":
            parked.append({"id": job_id, "reason": parked_reason(task, job_id)})
        if is_ready(task, job_id):
            ready.append(job_id)
        if job["status"] == "running" and minutes_since(job["last_change"]) >= STALE_RUNNING_MINUTES:
            if not result_file(task, job_id).exists():
                warnings.append(f"{job_id}: running with no change for {age_text(job['last_change'])[:-4]} — check on it")
            else:
                warnings.append(f"{job_id}: a result file exists — collect it")
    return {"task": task.id, "title": task.info["title"], "phase": task.phase, "branch": task.info.get("branch"),
            "layout": task.info.get("layout"), "last_change": task.info.get("last_change"),
            "settings": task.settings, "settings_card": settings_card(task.settings),
            "approvals": task.info.get("approvals", {}), "jobs": rows, "parked": parked, "ready": ready,
            "warnings": warnings, "next": next_command(task)}


def cmd_status(args) -> int:
    root, _ = find_root()
    if args.task:
        with open_task(root, args.task) as task:
            data = task_status_data(task)
        lines = [f"{data['title']}", f"{data['task']} · phase: {data['phase']}"
                 + (f" · branch: {data['branch']}" if data["branch"] else "")
                 + (f" · layout: {data['layout']}" if data["layout"] else ""),
                 f"Settings: {data['settings_card']}", f"Last change: {age_text(data['last_change'])}"]
        approvals = ", ".join(f"{k} by {v['by']}" for k, v in data["approvals"].items())
        if approvals:
            lines.append(f"Approved: {approvals}")
        if data["jobs"]:
            rows = [["ID", "kind", "status", "last change", "model"]]
            for r in data["jobs"]:
                status = r["status"] + (" ✓merged" if r["merged"] else "")
                rows.append([r["id"], r["kind"], status, age_text(r["last_change"]), r["model"]])
            lines += ["", "Jobs:", table(rows)]
        if data["parked"]:
            lines += ["", "Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
        if data["ready"]:
            lines += ["", "Ready: " + ", ".join(data["ready"])]
        if data["warnings"]:
            lines += ["", "Warnings:"] + [f"  - {w}" for w in data["warnings"]]
        lines += ["", f"Next: {data['next']}"]
        emit(args, "\n".join(lines), data)
        return EXIT_OK
    tasks = []
    for task_id in reversed(list_task_ids(root)):
        with contextlib.suppress(OSError, json.JSONDecodeError, KeyError):
            state = read_json(tasks_dir(root) / task_id / "state.json")
            statuses = [j["status"] for j in state["jobs"].values()]
            tasks.append({"id": task_id, "title": state["task"]["title"], "phase": state["task"]["phase"],
                          "last_change": state["task"].get("last_change"), "running": statuses.count("running"),
                          "parked": statuses.count("parked")})
    backlog = []
    for path in stamped_items(tasks_dir(root) / "backlog"):
        meta, body = split_frontmatter(read_text(path, ""))
        backlog.append({"file": rel(path, root), "title": re.sub(r"^Intent:\s*", "", first_heading(body) or path.stem),
                        "source": meta.get("source"), "created": stamp_time(path.name)})
    findings = len(stamped_items(tasks_dir(root) / "findings"))
    lines = []
    if tasks:
        rows = [["task", "phase", "title", "last change", "running", "parked"]]
        rows += [[t["id"], t["phase"], t["title"], age_text(t["last_change"]), str(t["running"]), str(t["parked"])]
                 for t in tasks]
        lines += ["Tasks:", table(rows)]
    else:
        lines.append("No tasks.")
    if backlog:
        rows = [[b["file"], b["title"], age_text(b["created"]), f"from {b['source']}" if b["source"] else ""]
                for b in backlog]
        lines += ["", "Backlog:", table(rows)]
    lines += ["", f"Open findings: {findings}"]
    emit(args, "\n".join(lines), {"tasks": tasks, "backlog": backlog, "open_findings": findings})
    return EXIT_OK


SET_KEYS = {
    "interaction": ("interaction",), "research": ("levels", "research"), "planning": ("levels", "planning"),
    "execution": ("levels", "execution"), "review-level": ("levels", "review"), "review": ("review", "points"),
    "reviewer": ("review", "provider"), "max-verify-failures": ("max_verify_failures",),
}


def cmd_set(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        new = json.loads(json.dumps(task.settings))
        for pair in args.pairs:
            if "=" not in pair:
                fail(EXIT_USAGE, f"Expected key=value, got {pair!r}. Keys: {', '.join(SET_KEYS)}.")
            key, value = pair.split("=", 1)
            if key not in SET_KEYS:
                fail(EXIT_USAGE, f"Unknown key {key!r}. Keys: {', '.join(SET_KEYS)}.")
            path = SET_KEYS[key]
            parsed: object = value
            if key == "review":
                parsed = [] if value == "off" else [p.strip() for p in value.split(",") if p.strip()]
            elif key == "max-verify-failures":
                if not re.fullmatch(r"\d+", value):
                    fail(EXIT_USAGE, "max-verify-failures must be an integer from 1 to 10.")
                parsed = int(value)
            node = new
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = parsed
        errors = settings_errors(new)
        if errors:
            fail(EXIT_USAGE, "Invalid settings: " + "; ".join(errors))
        changes = settings_diff(task.settings, new)
        if changes:
            task.write_settings(new)
            task.event("settings.changed", changes=changes, by="cli")
        emit(args, f"Settings: {settings_card(new)}" + ("" if changes else " (unchanged)"),
             {"settings": new, "changes": changes})
    return EXIT_OK


def cmd_approve(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        gate = args.gate
        if gate == "spec" and task.phase != "shaping":
            fail(EXIT_USAGE, f"Spec approval needs phase shaping; the task is in {task.phase}.")
        if gate == "plan" and task.phase != "planning":
            fail(EXIT_USAGE, f"Plan approval needs phase planning; the task is in {task.phase}.")
        if gate == "spec" and not (task.dir / "intent.md").exists():
            fail(EXIT_GATE, "intent.md is missing.")
        errors, warnings, added = run_check(task)
        task.save()  # keep the check event and a materialized review even when the gate refuses
        report = check_text(errors, warnings, added)
        if errors:
            fail(EXIT_GATE, f"{report}\nApproval refused: fix the errors first.")
        target = "spec" if gate == "spec" else "plan"
        for job_id, job in task.jobs.items():
            if job["kind"] == "review" and job.get("target") == target and job["status"] != "done":
                fail(EXIT_GATE, f"{report}\nApproval refused: {job_id} is {job['status']}. "
                                f"Dispatch and collect it first: sae dispatch {task.id} {job_id}")
        if gate == "plan":
            open_jobs = [i for i, j in task.jobs.items()
                         if j["kind"] in ("planning", "research") and j["status"] != "done"]
            if open_jobs:
                fail(EXIT_GATE, f"Approval refused: {', '.join(open_jobs)} not done.")
            if not any(not is_generated(i, j) and j["kind"] not in ("planning", "research")
                       for i, j in task.jobs.items()):
                fail(EXIT_GATE, "Approval refused: the plan has no jobs. Add them with sae job add.")
        by = git_user(root)
        task.info["approvals"][gate] = {"at": iso(), "by": by}
        if gate == "spec":
            task.info["phase"] = "planning"
        task.event(f"{gate}.approved", by=by)
        follow = f"sae start {task.id}" if gate == "plan" else "planning: load references/modes/plan.md"
        emit(args, (report + "\n" if report else "") + f"{gate.capitalize()} approved by {by}. Next: {follow}",
             {"approved": gate, "by": by, "phase": task.phase, "warnings": warnings})
    return EXIT_OK


def check_text(errors: list[str], warnings: list[str], added: list[str]) -> str:
    lines = [f"error: {e}" for e in errors] + [f"warning: {w}" for w in warnings]
    lines += [f"Added {a}: dispatch it." for a in added]
    return "\n".join(lines)


def cmd_check(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        errors, warnings, added = run_check(task)
        text = check_text(errors, warnings, added) or "Check passed: no errors, no warnings."
        if errors:
            text += f"\n{len(errors)} error(s)."
        emit(args, text, {"errors": errors, "warnings": warnings, "added": added})
        return EXIT_GATE if errors else EXIT_OK


def parse_needs(value: str | None) -> list[str]:
    needs = [n.strip() for n in (value or "").split(",") if n.strip()]
    for need in needs:
        if not JOB_ID_RE.match(need):
            fail(EXIT_USAGE, f"Invalid job ID in --needs: {need}")
    return needs


def require_reason(task: Task, reason: str | None) -> None:
    if task.phase == "executing" and not (reason or "").strip():
        fail(EXIT_USAGE, "--reason is required during execution (graph adaptation).")


def cmd_job_add(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job_id = args.id
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        if not JOB_ID_RE.match(job_id):
            fail(EXIT_USAGE, f"Invalid job ID {job_id!r}: use UPPER-KEBAB, for example STATUS-API.")
        if job_id in task.jobs:
            fail(EXIT_USAGE, f"Job {job_id} exists.")
        if args.kind == "review":
            fail(EXIT_USAGE, "sae adds review jobs itself (review points in settings, --review on a job).")
        if args.kind == "decision":
            fail(EXIT_USAGE, f"Use: sae decision new {task.id} --from <parked job>")
        if args.final and args.kind != "validation":
            fail(EXIT_USAGE, "--final is only for validation jobs.")
        if args.final and any(j["final"] for j in task.jobs.values()):
            fail(EXIT_USAGE, "The task already has a final job.")
        if args.fix_of:
            target = task.job(args.fix_of)
            if target["kind"] not in WRITER_KINDS or args.kind != "implementation":
                fail(EXIT_USAGE, "--fix-of: a fix job is an implementation job that fixes a writer job.")
            if target["merged"]:
                fail(EXIT_USAGE, f"{args.fix_of} is already merged; add a normal job instead.")
        require_reason(task, args.reason)
        needs = parse_needs(args.needs)
        job = new_job(args.kind, needs, args.difficulty, review=args.review, final=args.final, fix_of=args.fix_of)
        task.jobs[job_id] = job
        path = job_file(task, job_id)
        if not path.exists():
            name = "job-research.md" if args.kind == "research" else "job.md"
            text = template(name).replace("<JOB-ID>", job_id).replace("<TOPIC-ID>", job_id)
            write_atomic(path, text)
        task.event("job.added", job=job_id, kind=args.kind, needs=needs, difficulty=args.difficulty,
                   review=args.review, final=args.final, fix_of=args.fix_of, reason=args.reason)
        emit(args, f"Added {job_id} ({args.kind}, {args.difficulty}). Job file: {path}",
             {"job": job_id, "file": str(path)})
    return EXIT_OK


def cmd_job_edit(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        if job["status"] != "pending":
            fail(EXIT_USAGE, f"{args.id} is {job['status']}; only pending jobs change.")
        require_reason(task, args.reason)
        changes = {}
        if args.needs is not None:
            changes["needs"] = [job["needs"], parse_needs(args.needs)]
        if args.difficulty:
            changes["difficulty"] = [job["difficulty"], args.difficulty]
        if args.review is not None:
            changes["review"] = [job["review"], args.review]
        changes = {k: v for k, v in changes.items() if v[0] != v[1]}
        if not changes:
            emit(args, f"{args.id}: nothing changed.", {"job": args.id, "changes": {}})
            return EXIT_OK
        for key, (_, value) in changes.items():
            job[key] = value
        task.touch(job)
        task.event("job.changed", job=args.id, changes=changes, reason=args.reason)
        emit(args, f"{args.id}: " + ", ".join(f"{k} {v[0]} → {v[1]}" for k, v in changes.items()),
             {"job": args.id, "changes": changes})
    return EXIT_OK


def cmd_job_remove(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        job = task.job(args.id)
        if job["status"] != "pending":
            fail(EXIT_USAGE, f"{args.id} is {job['status']}; only pending jobs can be removed.")
        if not args.reason.strip():
            fail(EXIT_USAGE, "--reason is required.")
        dependants = [i for i, j in task.jobs.items() if args.id in j["needs"]]
        if dependants:
            fail(EXIT_USAGE, f"{', '.join(dependants)} need {args.id}. Edit their --needs first.")
        del task.jobs[args.id]
        path = job_file(task, args.id)
        if path.exists():
            os.replace(path, path.with_name(f"{args.id}.removed.md"))
        task.event("job.removed", job=args.id, kind=job["kind"], reason=args.reason)
        emit(args, f"Removed {args.id}. Its job file is kept as jobs/{args.id}.removed.md.", {"job": args.id})
    return EXIT_OK


# ---------------------------------------------------------------------------------------------
# Commands: execution


def cmd_start(args) -> int:
    root, is_git = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        if task.phase not in ("planning", "executing"):
            fail(EXIT_USAGE, f"The task is in {task.phase}.")
        if "plan" not in task.info["approvals"]:
            fail(EXIT_GATE, f"The plan is not approved. Run: sae approve {task.id} plan")
        if args.harness:
            task.info["orchestrator_harness"] = args.harness
        elif not task.info.get("orchestrator_harness"):
            task.info["orchestrator_harness"] = require_harness(None)
        lines = []
        resumed = task.phase == "executing"
        task.info["git"] = is_git
        if is_git:
            if not git_ok(root, "rev-parse", "--verify", "--quiet", "HEAD"):
                fail(EXIT_GIT, "The repository has no commits. Make a first commit, then run sae start again.")
            dirty = tracked_changes_outside_tasks(root)
            if dirty and not args.allow_dirty:
                fail(EXIT_GIT, "Tracked files outside .tasks/ have uncommitted changes: " + ", ".join(dirty[:10])
                     + "\nCommit or stash them, or add --allow-dirty.")
            branch = f"task/{task.id}"
            current = git(root, "branch", "--show-current", check=False)
            if git_ok(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
                if current != branch:
                    git(root, "switch", "--quiet", branch)
            else:
                task.info["base"] = {"branch": current or None, "commit": git(root, "rev-parse", "--short", "HEAD")}
                git(root, "switch", "--quiet", "-c", branch)
            task.info["branch"] = branch
            if not task.info.get("base"):
                task.info["base"] = {"branch": None, "commit": git(root, "rev-parse", "--short", "HEAD")}
            commit_backlog_pickup(task, lines)
        else:
            lines.append("No git: no branches, worktrees or commits. Agents change files directly; nothing "
                         "can undo their changes. Copy the folder first if you want a way back.")
        if not task.info.get("layout"):
            writers = [i for i, j in task.jobs.items() if j["kind"] in WRITER_KINDS]
            chained = all(not parallel_possible(task.jobs, a, b) for x, a in enumerate(writers) for b in writers[x + 1:])
            task.info["layout"] = "chain" if chained or not is_git else "worktrees"
        if task.uses_worktrees:
            cfg(config, "worktrees.root")
            cfg(config, "parallel.max_writers")
        task.info["phase"] = "executing"
        task.event("execution.started", branch=task.info.get("branch"), base=task.info.get("base"),
                   layout=task.info["layout"], resumed=resumed)
        lines.insert(0, f"Executing {task.id} · branch: {task.info.get('branch') or '-'} · layout: {task.info['layout']}")
        lines += ["", next_text(task, config)]
        emit(args, "\n".join(lines), {"task": task.id, "branch": task.info.get("branch"),
                                      "layout": task.info["layout"], "base": task.info.get("base")})
    return EXIT_OK


def commit_backlog_pickup(task: Task, out: list[str]) -> None:
    created = next((e for e in task.events() if e["type"] == "task.created"), {})
    item = (created.get("from") or {}).get("file")
    if not item or not git_ok(task.root, "cat-file", "-e", f"HEAD:{item}"):
        return
    git(task.root, "rm", "--quiet", "--cached", "--ignore-unmatch", "--", item)
    git(task.root, "commit", "--quiet", "-m", f"{task.id}: picked up from backlog", "-m", f"Task: {task.id}",
        "--", item)
    out.append(f"Committed the removal of {item}.")


def next_text(task: Task, config: dict | None) -> str:
    data = next_data(task, config)
    lines = [mode_line(task.settings["interaction"]), HARD_STOPS_LINE, ""]
    if data["running"]:
        lines += ["Running:"] + [f"  {r['id']} — last change {age_text(r['last_change'])}" for r in data["running"]]
    if data["parked"]:
        lines += ["Parked:"] + [f"  {p['id']} — {p['reason']}" for p in data["parked"]]
    if data["ready"]:
        rows = [[r["id"], r["kind"], r["difficulty"], r["model"], r["workspace"], r.get("blocked") or ""]
                for r in data["ready"]]
        lines += ["Ready (dispatch each: sae dispatch <task> <ID>):", table(rows)]
    if data["blocked"]:
        lines += ["Blocked:"] + [f"  {b['id']} — waits for {', '.join(b['waits_for'])}" for b in data["blocked"]]
    if data["failed"]:
        lines += ["Failed:"] + [f"  {f['id']} — {f['summary']}" for f in data["failed"]]
    if data["all_done"]:
        lines.append(f"All jobs done. Run: sae finish {task.id}")
    elif not (data["running"] or data["ready"] or data["parked"]):
        lines.append("Nothing can run. Adapt the graph, resume a failed job, or finish with --with-open.")
    return "\n".join(lines).rstrip()


def next_data(task: Task, config: dict | None) -> dict:
    running, parked, ready, blocked, failed = [], [], [], [], []
    for job_id, job in task.jobs.items():
        status = job["status"]
        if status == "running":
            running.append({"id": job_id, "last_change": job["last_change"]})
        elif status == "parked":
            parked.append({"id": job_id, "reason": parked_reason(task, job_id)})
        elif status == "failed":
            failed.append({"id": job_id, "summary": job_summary(task, job_id)})
        elif status == "pending":
            reasons = waits_for(task, job_id)
            if reasons:
                blocked.append({"id": job_id, "waits_for": reasons})
                continue
            model = resolve_model(task, job, config) if config is not None else None
            if model is None:
                cfg(config, "rungs")
            workdir, _ = workspace_of(task, job_id, config)
            entry = {"id": job_id, "kind": job["kind"], "difficulty": job["difficulty"],
                     "model": f"{model['model']}" + (f" ({model['effort']})" if model.get("effort") else "")
                              + f" · {model['harness']} {model['rung']}",
                     "workspace": "worktree" if workdir != task.root else
                                  ("repo root, writes" if job["kind"] in WRITER_KINDS else "repo root, read-only")}
            if job["kind"] in WRITER_KINDS:
                entry["blocked"] = writer_blocked(task, job_id, config)
            ready.append(entry)
    open_statuses = {j["status"] for j in task.jobs.values()} & {"running", "pending", "parked"}
    return {"running": running, "parked": parked, "ready": ready, "blocked": blocked, "failed": failed,
            "all_done": not open_statuses and task.phase == "executing"}


def cmd_next(args) -> int:
    root, _ = find_root()
    config = load_config()
    with open_task(root, args.task) as task:
        if task.phase != "executing":
            fail(EXIT_USAGE, f"The task is in {task.phase}. Next: {next_command(task)}")
        out: list[str] = []
        materialize_integration_review(task, out)
        text = ("\n".join(out) + "\n" if out else "") + next_text(task, config)
        data = next_data(task, config)
        data["reminder"] = [mode_line(task.settings["interaction"]), HARD_STOPS_LINE]
        emit(args, text, data)
    return EXIT_OK


def cmd_dispatch(args) -> int:
    root, _ = find_root()
    config = load_config()
    with open_task(root, args.task) as task:
        job_id = args.id
        job = task.job(job_id)
        if args.resume:
            if not (args.reason or "").strip():
                fail(EXIT_USAGE, "--resume needs --reason.")
            if job["status"] not in ("running", "parked", "failed"):
                fail(EXIT_USAGE, f"{job_id} is {job['status']}; --resume is for running, parked or failed jobs.")
            if not kind_allowed_now(task, job):
                fail(EXIT_USAGE, f"{job['kind']} jobs do not run in phase {task.phase}.")
        else:
            if job["status"] != "pending":
                fail(EXIT_USAGE, f"{job_id} is {job['status']}. To run it again: --resume --reason \"<why>\".")
            reasons = waits_for(task, job_id)
            if reasons:
                fail(EXIT_USAGE, f"{job_id} is not ready: waits for {', '.join(reasons)}.")
        if job["kind"] in WRITER_KINDS and job["status"] != "running":
            blocked = writer_blocked(task, job_id, config)
            if blocked:
                fail(EXIT_USAGE, f"{job_id} must wait: {blocked}.")
        model = resolve_model(task, job, config, harness=args.harness, provider=args.provider)
        workdir, branch = prepare_workspace(task, job_id, config)
        head = git(workdir, "rev-parse", "HEAD") if (task.info.get("git") and job["kind"] in WRITER_KINDS) else None
        attempt = {"n": len(job["attempts"]) + 1, "harness": model["harness"], "rung": model["rung"],
                   "model": model["model"], "effort": model["effort"], "started": iso(), "ended": None,
                   "tokens": None, "duration_s": None, "agent_ref": None, "reason": args.reason, "head": head}
        job["attempts"].append(attempt)
        job["status"] = "running"
        task.touch(job)
        task.event("job.dispatched", job=job_id, attempt=attempt["n"], harness=model["harness"], rung=model["rung"],
                   model=model["model"], effort=model["effort"], workspace=rel(workdir, root) or ".",
                   reason=args.reason)
        external = job["kind"] == "review" and model["harness"] != task.info.get("orchestrator_harness")
        prompt = build_prompt(task, job_id, workdir, branch, model, config, external=external)
        if args.resume:
            extra = []
            log = task.dir / "jobs" / f"{job_id}.verify.log"
            if args.reason.startswith("verify") and log.exists():
                extra.append(f"Read first: {log}")
            follow = md_section(read_text(job_file(task, job_id), "") or "", "Follow-up questions")
            if has_content(follow):
                extra.append(f"Read first: the \"Follow-up questions\" section of {job_file(task, job_id)}")
            prompt = "\n".join([f"RESUME {job_id} — reason: {args.reason}", *extra,
                                "Continue from your earlier work and commits; the pointers are unchanged.", "",
                                prompt])
        header = (f"MODEL: {model['model']} · effort: {model['effort'] or 'n/a'} · harness: {model['harness']} "
                  f"· rung: {model['rung']}")
        data = {"job": job_id, "attempt": attempt["n"], "workspace": str(workdir), "branch": branch, **model}
        if external:
            command = external_review_command(task, job_id, model, prompt)
            fallback = (f"{sae_prefix()} dispatch {task.id} {job_id} --provider {task.info['orchestrator_harness']} "
                        f"--resume --reason \"provider failed: <exit code or empty result>\"")
            data.update({"command": command, "if_it_fails": fallback})
            emit(args, f"{header}\nCOMMAND:\n{command}\nIF IT FAILS:\n{fallback}", data)
        else:
            data["prompt"] = prompt
            emit(args, f"{header}\nPROMPT:\n{prompt}", data)
    return EXIT_OK


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


def cmd_decision_new(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        source = task.job(args.from_job)
        if source["status"] != "parked":
            fail(EXIT_USAGE, f"{args.from_job} is {source['status']}; decision jobs answer parked jobs.")
        n = 1 + sum(1 for i in task.jobs if i.startswith(f"DECISION-{args.from_job}-"))
        job_id = f"DECISION-{args.from_job}-{n}"
        task.jobs[job_id] = new_job("decision", [], args.difficulty, target=args.from_job)
        result = rel(result_file(task, args.from_job), task.dir)
        write_atomic(job_file(task, job_id),
                     f"---\nid: {job_id}\n---\n\n# {job_id}: decision for {args.from_job}\n\n## Objective\n"
                     f"Answer the decision request of {args.from_job}.\n\n## Inputs\n"
                     f"- The section \"Decision request\" of {result}.\n")
        task.event("job.added", job=job_id, kind="decision", needs=[], difficulty=args.difficulty,
                   target=args.from_job, reason=f"decision for {args.from_job}")
        emit(args, f"Added {job_id}. Dispatch it: sae dispatch {task.id} {job_id}", {"job": job_id})
    return EXIT_OK


def cmd_log(args) -> int:
    root, _ = find_root()
    with open_task(root, args.task) as task:
        if args.job:
            task.job(args.job)
        if args.type == "decision":
            if args.decision_class and args.decision_class not in DECISION_CLASSES:
                fail(EXIT_USAGE, f"--class must be one of {', '.join(DECISION_CLASSES)}")
            fields = {"class": args.decision_class, "by": args.by, "summary": args.summary, "job": args.job,
                      "file": args.file}
            task.event("decision", **{k: v for k, v in fields.items() if v is not None})
        elif args.type == "amendment":
            if not args.amend_id:
                fail(EXIT_USAGE, "An amendment needs --id <AMEND-ID> (the ID under ## Amendments in specs.md).")
            spec = read_text(task.dir / "specs.md", "")
            if f"[{args.amend_id}]" not in spec:
                warn(f"[{args.amend_id}] is not in specs.md; write the amendment text there first.")
            task.event("amendment", id=args.amend_id, by=args.by, summary=args.summary)
        else:
            task.event("note", text=args.summary, **({"job": args.job} if args.job else {}))
        emit(args, f"Logged {args.type}.", {"type": args.type})
    return EXIT_OK


# ---------------------------------------------------------------------------------------------
# Commands: findings


def cmd_finding_new(args) -> int:
    root, _ = find_root()
    source_task, source = None, None
    if args.source:
        task_ref, _, job_id = args.source.partition("/")
        source_task = resolve_task(root, task_ref)
        source = f"{source_task}/{job_id}" if job_id else source_task
    ensure_tasks_folder(root)
    path = tasks_dir(root) / "findings" / f"{file_stamp()}--{slugify(args.title)}.md"
    if path.exists():
        path = path.with_name(f"{path.stem}-2.md")
    paths = [p.strip() for p in (args.paths or "").split(",") if p.strip()]
    body = split_frontmatter(template("finding.md"))[1].replace("<title>", args.title)
    front = (f"---\ntype: {args.type}\nconfidence: {args.confidence}\n"
             + (f"source: {source}\n" if source else "")
             + f"paths: [{', '.join(paths)}]\n---\n")
    write_atomic(path, front + body)
    if source_task:
        append_event_to(root, source_task, "finding.created", finding=rel(path, root))
    else:
        render_viewer_safely(root, [])
    emit(args, f"Finding: {path}", {"file": str(path)})
    return EXIT_OK


CLOSE_OUTCOME_RE = re.compile(r"^(fixed in \S+|moved to backlog/\S+|rejected: .+|duplicate of \S+)$")


def cmd_finding_close(args) -> int:
    root, _ = find_root()
    path = Path(args.file)
    if not path.is_absolute():
        candidates = [Path.cwd() / path, root / path, tasks_dir(root) / "findings" / path.name]
        path = next((c for c in candidates if c.exists()), candidates[0])
    text = read_text(path)
    if text is None:
        fail(EXIT_USAGE, f"No finding at {args.file}.")
    if not CLOSE_OUTCOME_RE.match(args.outcome):
        fail(EXIT_USAGE, 'Outcome must be "fixed in <task-id>", "moved to backlog/<file>", '
                         '"rejected: <reason>" or "duplicate of <finding>".')
    title = first_heading(split_frontmatter(text)[1]) or path.stem
    closed = tasks_dir(root) / "findings" / "closed.md"
    if not closed.exists():
        write_atomic(closed, "# Closed findings\n\n")
    with closed.open("a", encoding="utf-8") as handle:
        handle.write(f"- {now().date().isoformat()} · {path.stem} · {title} · {args.outcome}\n")
    os.remove(path)
    render_viewer_safely(root, [])
    emit(args, f"Closed {path.stem}: {args.outcome}", {"finding": path.stem, "outcome": args.outcome})
    return EXIT_OK


# ---------------------------------------------------------------------------------------------
# Commands: finish, abandon


def final_report(task: Task, with_open: bool) -> str:
    jobs = task.jobs
    events = task.events()
    lines = [f"# Final report: {task.info['title']}", f"Task: {task.id}"]
    finals = [i for i, j in jobs.items() if j["final"]]
    if finals:
        job = jobs[finals[0]]
        lines += ["", "## Outcome", f"Final validation {finals[0]}: {job['status']} — {job.get('summary', '')}",
                  f"Details per requirement: {result_file(task, finals[0])}"]
    rows = [["job", "kind", "status", "attempts", "models", "tokens"]]
    for job_id, job in jobs.items():
        models = ", ".join(dict.fromkeys(a["model"] for a in job["attempts"])) or "-"
        tokens = sum(a.get("tokens") or 0 for a in job["attempts"])
        rows.append([job_id, job["kind"], job["status"] + (" ✓merged" if job["merged"] else ""),
                     str(len(job["attempts"])), models, str(tokens) if tokens else "-"])
    lines += ["", "## Jobs", table(rows, "")]
    reviews = [e for e in events if e["type"] == "review.completed"]
    if reviews:
        lines += ["", "## Reviews"] + [f"- {e['job']} → {e['target']}: {e['verdict']} ({e.get('provider')}, "
                                       f"{e.get('model')})" for e in reviews]
    agent = [e for e in events if e["type"] in ("decision", "amendment") and e.get("by") == "agent"]
    lines += ["", "## To check before you merge"]
    lines += [f"- {e['type']}{' ' + e['id'] if e.get('id') else ''}: {e.get('summary')}"
              + (f" ({e['class']})" if e.get("class") else "") for e in agent] or ["- No agent decisions or amendments."]
    if with_open:
        open_items = [(i, j) for i, j in jobs.items() if j["status"] in ("pending", "parked", "failed")]
        if open_items:
            lines += ["", "## Open items"] + [f"- {i}: {j['status']} — {j.get('summary') or parked_reason(task, i)}"
                                              for i, j in open_items]
    created = [e.get("finding") or e.get("file") for e in events if e["type"] in ("finding.created", "backlog.created")]
    if created:
        lines += ["", "## Findings and backlog items from this task"] + [f"- {c}" for c in created]
    lines += ["", "## Branch"]
    if task.info.get("git"):
        base = task.info.get("base") or {}
        count = git(task.root, "rev-list", "--count", f"{base.get('commit')}..{task.info['branch']}", check=False)
        lines.append(f"{task.info['branch']} (base {base.get('branch') or '-'} @ {base.get('commit')}), "
                     f"{count or '?'} commits.")
        lines.append("Nothing was pushed. Merge or open a merge request yourself.")
    else:
        lines.append("No git: the changes are in the working folder.")
    return "\n".join(lines)


def cmd_finish(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        if task.phase != "executing":
            fail(EXIT_USAGE, f"The task is in {task.phase}; finish needs executing.")
        jobs = task.jobs
        running = [i for i, j in jobs.items() if j["status"] == "running"]
        if running:
            fail(EXIT_GATE, f"Still running: {', '.join(running)}. Collect them first.")
        open_jobs = [i for i, j in jobs.items() if j["status"] in ("pending", "parked")]
        if open_jobs and not args.with_open:
            fail(EXIT_GATE, f"Open jobs: {', '.join(open_jobs)}. Finish them, or add --with-open when the user "
                            "accepts open items.")
        finals = [i for i, j in jobs.items() if j["final"] and j["status"] != "done"]
        if finals:
            fail(EXIT_GATE, f"The final validation {finals[0]} is not done.")
        integration = [i for i, j in jobs.items() if j["kind"] == "review" and j.get("target") == "integration"]
        if integration and jobs[integration[0]]["status"] != "done":
            fail(EXIT_GATE, f"{integration[0]} is not done.")
        out: list[str] = []
        if task.info.get("git"):
            require_on_task_branch(task)
            for job_id, job in list(jobs.items()):
                if (job["kind"] in WRITER_KINDS and job["status"] == "done" and not job["merged"]
                        and not job.get("fix_of") and last_verdict(task, job_id) != "changes-required"
                        and not any(j["kind"] == "review" and j.get("target") == job_id and j["status"] != "done"
                                    for j in jobs.values())):
                    code = merge_job(task, job_id, config, out)
                    if code != EXIT_OK:
                        emit(args, "\n".join(out), {"exit": code, "messages": out})
                        return code
            kept = remove_task_worktrees(task, config)
            for job_id, job in jobs.items():
                if job["merged"] and not job.get("fix_of"):
                    run(["git", "branch", "-d", job_branch(task, job_id)], root)
            if kept:
                out.append("Worktrees kept (uncommitted changes): " + ", ".join(kept))
        report = final_report(task, args.with_open)
        head = git(root, "rev-parse", "--short", "HEAD") if task.info.get("git") else None
        task.info["phase"] = "done"
        task.event("task.finished", branch=task.info.get("branch"), commit=head)
        task.save()
        if task.info.get("git"):
            commit_task_record(task, out)
        emit(args, "\n".join(out + ["", report]).strip(), {"report": report, "messages": out})
    render_viewer_safely(root, [task.id])
    return EXIT_OK


def commit_task_record(task: Task, out: list[str]) -> None:
    root = task.root
    paths = [f".tasks/{task.id}"]
    for folder in ("findings", "backlog"):
        for path in stamped_items(tasks_dir(root) / folder):
            source = str(split_frontmatter(read_text(path, ""))[0].get("source") or "")
            if source == task.id or source.startswith(task.id + "/"):
                paths.append(rel(path, root))
    for extra in (".tasks/repo", ".tasks/.gitignore", ".tasks/.gitattributes"):
        if (root / extra).exists():
            paths.append(extra)
    git(root, "add", "--", *paths)
    staged = git(root, "diff", "--cached", "--name-only", "--", *paths)
    if not staged:
        return
    git(root, "commit", "--quiet", "-m", f"{task.id}: task record", "-m", f"Task: {task.id}", "--", *paths)
    out.append(f"Committed the task record on {task.info['branch']}.")


def cmd_abandon(args) -> int:
    root, _ = find_root()
    config = load_config(required=False)
    with open_task(root, args.task) as task:
        if task.phase in ("done", "abandoned"):
            fail(EXIT_USAGE, f"The task is {task.phase}.")
        kept = remove_task_worktrees(task, config)
        task.info["phase"] = "abandoned"
        task.event("task.abandoned", reason=args.reason)
        text = f"Abandoned {task.id}. Branches are kept."
        if kept:
            text += "\nWorktrees kept (uncommitted changes): " + ", ".join(kept)
        emit(args, text, {"task": task.id, "kept_worktrees": kept})
    return EXIT_OK


def cmd_view(args) -> int:
    root, _ = find_root()
    task_id = resolve_task(root, args.task) if args.task else None
    target = render_viewer(root, None)
    url = target.resolve().as_uri() + (f"#task={task_id}&tab=plan" if task_id else "")
    if args.open:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        if shutil.which(opener):
            subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            warn(f"{opener} not found; open the URL yourself")
    emit(args, url, {"url": url})
    return EXIT_OK


# ---------------------------------------------------------------------------------------------
# Commands: setup and doctor


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


def cmd_doctor(args) -> int:
    checks: list[tuple[str, str, str]] = []  # (mark, text, fix)

    def check(ok: bool | None, text: str, fix: str = "") -> None:
        checks.append(("✓" if ok else ("!" if ok is None else "✗"), text, "" if ok else fix))

    check(sys.version_info >= (3, 10), f"Python {platform.python_version()}", "Install Python 3.10 or newer.")
    config, config_ok = None, False
    try:
        config = load_config()
        errors = validate_config(config)
        config_ok = not errors
        check(config_ok, f"config {config_path()}" + ("" if config_ok else ": " + "; ".join(errors)),
              "Run setup mode and save a valid config.")
    except SaeError:
        check(False, f"config {config_path()} missing or not JSON", "Run setup mode: \"/shape-and-execute setup\".")
    if config_ok:
        root = worktree_root(config)
        writable = root.is_dir() and os.access(root, os.W_OK)
        check(writable, f"worktree root {root}", f"mkdir -p {shlex.quote(str(root))}")
    check(bool(shutil.which("git")), "git on PATH", "Install git (or run tasks without git).")
    harness = detect_harness(None)
    check(bool(harness), f"harness: {harness or 'not detected'}",
          "Set SAE_HARNESS=claude|codex, or pass --harness to new and start.")
    if config_ok:
        other = [h for h in config["rungs"] if h != harness]
        for name in other:
            check(bool(shutil.which(name)) or None, f"{name} CLI on PATH (only for cross-model review)",
                  f"Install {name}, or set the review provider to {harness}.")
    if shutil.which("codex") or (config_ok and "codex" in config["rungs"]):
        cap = codex_subagent_cap()
        check(cap["ok"], codex_cap_text(cap).splitlines()[0],
              f"Set [agents] max_threads = {cap['recommended']} in {cap['config']} (setup mode can do it).")
    if args.repo:
        doctor_repo(config if config_ok else None, check)
    lines = [f"{mark} {text}" + (f"\n    fix: {fix}" if fix else "") for mark, text, fix in checks]
    failed = [c for c in checks if c[0] == "✗"]
    emit(args, "\n".join(lines), {"checks": [{"ok": m != "✗", "mark": m, "text": t, "fix": f} for m, t, f in checks]})
    if not config_ok:
        return EXIT_CONFIG
    return EXIT_USAGE if failed else EXIT_OK


def doctor_repo(config: dict | None, check) -> None:
    root, is_git = find_root()
    folder = tasks_dir(root)
    folder_ok = (folder.is_dir() and os.access(folder, os.W_OK)) or (not folder.exists() and os.access(root, os.W_OK))
    check(folder_ok, f".tasks/ writable in {root}", "Fix the folder permissions.")
    check((folder / "repo" / "profile.md").exists() or None, "repo profile .tasks/repo/profile.md",
          "Setup mode drafts it from the repository (optional).")
    if is_git and config is not None and git_ok(root, "rev-parse", "--verify", "--quiet", "HEAD"):
        branch = f"sae-doctor-{file_stamp()}"
        path = worktree_root(config) / f"{root.name}-{hash8(root)}" / "_doctor"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            git(root, "worktree", "add", "--quiet", "-b", branch, str(path), "HEAD")
            copy_worktree_includes(root, path)
            log = Path(tempfile.gettempdir()) / f"sae-doctor-setup-{hash8(root)}.log"
            run_setup_script(root, path, "_doctor", "_doctor", log)
            git(path, "commit", "--quiet", "--allow-empty", "-m", "sae doctor: throwaway commit")
            check(True, "throwaway worktree: create, setup.sh, commit")
        except SaeError as exc:
            check(False, f"throwaway worktree: {exc}", "Check the harness permissions (sae setup snippets) and setup.sh.")
        finally:
            run(["git", "worktree", "remove", "--force", str(path)], root)
            run(["git", "branch", "-D", branch], root)
            run(["git", "worktree", "prune"], root)
    elif is_git:
        check(None, "throwaway worktree skipped (no valid config or no commit yet)")
    target = render_viewer_safely(root, None)
    check(target is not None, f"viewer rendered: {target.resolve().as_uri() if target else 'failed'}",
          "See the warning above.")


# ---------------------------------------------------------------------------------------------
# Command line


class Parser(argparse.ArgumentParser):
    """Usage errors exit 1; exit 2 means a missing user config."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        sys.exit(EXIT_USAGE)


CODE_TEXT = {0: "ok", 1: "usage or precondition error", 2: "user config missing or invalid: offer setup mode",
             3: "gate refused", 4: "git problem (dirty tree, merge conflict, worktree or setup failure)",
             5: "re-run verify failed: resume the same worker"}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print a JSON object instead of text")
    parser = Parser(
        prog="sae", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="The CLI of the shape-and-execute skill. It records task state, checks gates, computes what is\n"
                    "ready and which model runs it, prints dispatch prompts, and moves git branches and worktrees.\n"
                    "Agents decide; sae never calls a model and never pushes.\n\n"
                    "Invoke: python3 <SKILL_DIR>/scripts/sae.py <command> [args]. <task> is a task ID or a unique\n"
                    "end of it (usually the slug). Details of one command: sae <command> --help.",
        epilog=EXIT_CODES_HELP)
    sub = parser.add_subparsers(dest="command", metavar="<command>", title="commands", parser_class=Parser)

    def command(parent, name: str, summary: str, details: str, examples: list[str], codes: list[int], func,
                parents=True):
        epilog = "Examples:\n" + "\n".join(f"  sae {e}" for e in examples)
        epilog += "\n\nExit codes:\n" + "\n".join(f"  {c}  {CODE_TEXT[c]}" for c in codes)
        p = parent.add_parser(name, help=summary, description=f"{summary}\n\n{details}".strip(), epilog=epilog,
                              formatter_class=argparse.RawDescriptionHelpFormatter,
                              parents=[common] if parents else [])
        p.set_defaults(func=func)
        return p

    # tasks
    p = command(sub, "new", "Create a task, or a backlog item with --backlog.",
                "Creates .tasks/<id>/ with intent.md, settings.json (from the config defaults), state.json\n"
                "(phase shaping) and events.jsonl. Prints the task ID and paths.\n"
                "--from <file>: the backlog item becomes intent.md and leaves the backlog (sae start commits that).\n"
                "--backlog: creates .tasks/backlog/<stamp>--<slug>.md for work the user deferred; no task, no config.",
                ['new "Claims status self-service"', 'new "Billing export" --from .tasks/backlog/2026-10-06-1520--billing.md',
                 'new "Billing export" --backlog --source claims-status'], [0, 1, 2], cmd_new)
    p.add_argument("title")
    p.add_argument("--slug", help="folder slug; default: from the title")
    p.add_argument("--harness", choices=HARNESSES, help="orchestrator harness; default: detected")
    p.add_argument("--from", dest="from_file", metavar="FILE", help="backlog item to turn into this task")
    p.add_argument("--backlog", action="store_true", help="create a backlog item instead of a task")
    p.add_argument("--source", metavar="TASK", help="with --backlog: the task during which the user deferred the work")

    p = command(sub, "status", "Where things are. The first command after any context reset.",
                "Without a task: every task, the backlog and the number of open findings.\n"
                "With a task: settings card, phase, branch, jobs, parked jobs with reasons, ready jobs, warnings,\n"
                "and the next suggested command.", ["status", "status claims-status --json"], [0, 1], cmd_status)
    p.add_argument("task", nargs="?")

    p = command(sub, "set", "Change this task's settings (settings.json).",
                f"Keys: interaction ({'|'.join(INTERACTION_MODES)}); research, planning, execution, review-level\n"
                f"({'|'.join(LEVELS)}); review (comma list of {', '.join(REVIEW_POINTS)}; or off);\n"
                f"reviewer ({'|'.join(HARNESSES)}); max-verify-failures (1-10; change it only when the user asks).\n"
                "The next dispatch uses the new values. Prints the settings card.",
                ["set claims-status execution=economy", "set claims-status review=spec,plan,selected-jobs,integration reviewer=codex"],
                [0, 1], cmd_set)
    p.add_argument("task")
    p.add_argument("pairs", nargs="+", metavar="key=value")

    p = command(sub, "approve", "Record a gate approval: spec (shaping → planning) or plan.",
                "Runs check first; lint errors refuse. Refuses while REVIEW-SPEC (or REVIEW-PLAN) exists and is not\n"
                "collected; its verdict does not block. Plan approval also needs every planning and research job done.",
                ["approve claims-status spec", "approve claims-status plan"], [0, 1, 3], cmd_approve)
    p.add_argument("task")
    p.add_argument("gate", choices=("spec", "plan"))

    p = command(sub, "check", "Lint the task and add due spec or plan reviews.",
                "In shaping: requirement IDs in specs.md and in the intent's ## Acceptance; a clean check adds\n"
                "REVIEW-SPEC when spec is a review point. Later: the graph (unknown needs, cycles, job files and\n"
                "objectives, covers, requirement coverage, final jobs) and warnings (verify, scopes, hot files, brief\n"
                "length, riskiest assumptions, objective length); a clean check in planning adds REVIEW-PLAN.",
                ["check claims-status"], [0, 1, 3], cmd_check)
    p.add_argument("task")

    p = command(sub, "start", "Begin execution: task branch, layout, then the first next.",
                "Needs the plan approval. With git: refuses when tracked files outside .tasks/ have changes (unless\n"
                "--allow-dirty), creates or switches to task/<id>, records the base, fixes the layout (chain or\n"
                "worktrees), and commits the removal of a picked-up backlog item. Without git: prints the notice.",
                ["start claims-status"], [0, 1, 2, 3, 4], cmd_start)
    p.add_argument("task")
    p.add_argument("--harness", choices=HARNESSES)
    p.add_argument("--allow-dirty", action="store_true")

    p = command(sub, "finish", "Merge the rest, remove worktrees, commit the task record, print the final report.",
                "Needs nothing running; nothing pending or parked unless --with-open; the final validation and a due\n"
                "integration review done. Never pushes.", ["finish claims-status", "finish claims-status --with-open"],
                [0, 1, 3, 4], cmd_finish)
    p.add_argument("task")
    p.add_argument("--with-open", action="store_true", help="the user accepts open jobs; they are listed in the report")

    p = command(sub, "abandon", "Stop a task: phase abandoned, worktrees removed, branches kept.", "",
                ['abandon claims-status --reason "superseded by billing work"'], [0, 1], cmd_abandon)
    p.add_argument("task")
    p.add_argument("--reason", required=True)

    p = command(sub, "view", "Render the viewer and print its file:// URL.",
                "With a task, the URL opens its Plan tab. --open opens it in the browser.",
                ["view", "view claims-status --open"], [0, 1], cmd_view)
    p.add_argument("task", nargs="?")
    p.add_argument("--open", action="store_true")

    # graph
    job = sub.add_parser("job", help="Add, edit or remove a job of the graph.", parents=[],
                         description="Graph changes. sae job <add|edit|remove> --help for details.")
    job_sub = job.add_subparsers(dest="job_command", metavar="<add|edit|remove>", parser_class=Parser)
    p = command(job_sub, "add", "Register a job and scaffold jobs/<ID>.md.",
                f"Kinds: {', '.join(k for k in JOB_KINDS if k not in ('review', 'decision'))} (sae adds review jobs;\n"
                "decision jobs come from sae decision new). ID: UPPER-KEBAB. --needs: jobs that must be done (and\n"
                "merged, for writers) first. --review: review this job (selected-jobs). --final: the final validation.\n"
                "--fix-of: an implementation job that fixes a writer job in its workspace. --reason: required during\n"
                "execution.",
                ["job add claims-status STATUS-API --kind implementation --needs STATUS-CONTRACT --difficulty hard --review",
                 'job add claims-status STATUS-API-FIX-1 --kind implementation --fix-of STATUS-API --reason "REVIEW-STATUS-API: changes required"'],
                [0, 1], cmd_job_add)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--kind", required=True, choices=[k for k in JOB_KINDS if k not in ("review", "decision")])
    p.add_argument("--needs", metavar="A,B")
    p.add_argument("--difficulty", choices=DIFFICULTIES, default="normal")
    p.add_argument("--review", action="store_true")
    p.add_argument("--final", action="store_true")
    p.add_argument("--fix-of", metavar="ID")
    p.add_argument("--reason")
    p = command(job_sub, "edit", "Change the scheduling fields of a pending job.", "--reason: required during execution.",
                ['job edit claims-status STATUS-UI --needs STATUS-API --reason "UI needs the real endpoint"'], [0, 1],
                cmd_job_edit)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--needs", metavar="A,B", help="replaces the list; empty string clears it")
    p.add_argument("--difficulty", choices=DIFFICULTIES)
    p.add_argument("--review", dest="review", action="store_true", default=None)
    p.add_argument("--no-review", dest="review", action="store_false")
    p.add_argument("--reason")
    p = command(job_sub, "remove", "Remove a pending job; its file is kept as jobs/<ID>.removed.md.",
                "Refuses while another job needs it.", ['job remove claims-status STATUS-CACHE --reason "not needed"'],
                [0, 1], cmd_job_remove)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--reason", required=True)

    # execution
    p = command(sub, "next", "Reminder lines, then running, parked, ready and blocked jobs.",
                "Read the two reminder lines every time. Ready jobs show the model and the workspace kind.",
                ["next claims-status"], [0, 1, 2], cmd_next)
    p.add_argument("task")

    p = command(sub, "dispatch", "Prepare the workspace and print MODEL and PROMPT for one job.",
                "Spawn a subagent with the printed PROMPT and MODEL (Codex: also the effort). For a review in the\n"
                "other harness it prints COMMAND (run it in the background) and an IF IT FAILS line (run it when the\n"
                "command exits non-zero or leaves no review). --resume runs a running, parked or failed job again\n"
                "with --reason; the message also works for a fresh agent.",
                ["dispatch claims-status STATUS-API", "dispatch claims-status STATUS-API --resume --reason verify-failed"],
                [0, 1, 2, 4], cmd_dispatch)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--provider", choices=HARNESSES, help="review jobs: the harness that reviews")
    p.add_argument("--harness", choices=HARNESSES, help="override the harness for this dispatch")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--reason")

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

    p = command(sub, "merge", "Merge a done writer job now; --accept-review merges despite changes-required.",
                "Normally automatic. --accept-review logs a decision event with the reason.",
                ['merge claims-status STATUS-API --accept-review "remaining finding is cosmetic"'], [0, 1, 3, 4], cmd_merge)
    p.add_argument("task")
    p.add_argument("id")
    p.add_argument("--accept-review", metavar="REASON")

    decision = sub.add_parser("decision", help="Create a decision job for a parked job.",
                              description="sae decision new --help for details.")
    decision_sub = decision.add_subparsers(dest="decision_command", metavar="<new>", parser_class=Parser)
    p = command(decision_sub, "new", "Add DECISION-<ID>-<n> for a parked job; prints the new ID.",
                "Its job file points to the ## Decision request section of the parked result.",
                ["decision new claims-status --from STATUS-API"], [0, 1], cmd_decision_new)
    p.add_argument("task")
    p.add_argument("--from", dest="from_job", required=True, metavar="ID")
    p.add_argument("--difficulty", choices=DIFFICULTIES, default="normal")

    p = command(sub, "log", "Record a decision, an amendment or a note.",
                "Write an amendment into specs.md under ## Amendments first, then log it with its --id.\n"
                "--by: human | agent | joint (default agent; agent entries appear in the final report).",
                ['log claims-status decision "Cache status for 60 s" --by agent --class open-tradeoff --job STATUS-API',
                 'log claims-status amendment "Drop CSV export" --id AMEND-1 --by human'], [0, 1], cmd_log)
    p.add_argument("task")
    p.add_argument("type", choices=("decision", "amendment", "note"))
    p.add_argument("summary")
    p.add_argument("--job", metavar="ID")
    p.add_argument("--by", choices=PROVENANCES, default="agent")
    p.add_argument("--class", dest="decision_class", choices=DECISION_CLASSES)
    p.add_argument("--id", dest="amend_id", metavar="AMEND-ID")
    p.add_argument("--file")

    # findings
    finding = sub.add_parser("finding", help="File or close a finding (out-of-scope observations).",
                             description="sae finding <new|close> --help for details.")
    finding_sub = finding.add_subparsers(dest="finding_command", metavar="<new|close>", parser_class=Parser)
    p = command(finding_sub, "new", "File a finding in .tasks/findings/; prints its path.",
                "Types: friction (the repository made agent work hard), defect (something looks broken), follow-up\n"
                "(work worth doing outside the task). Fill the printed file. Never fix it on the side.",
                ['finding new "Status lookup is slow" --type defect --confidence medium --source claims-status/STATUS-API --paths src/status'],
                [0, 1], cmd_finding_new)
    p.add_argument("title")
    p.add_argument("--type", required=True, choices=FINDING_TYPES)
    p.add_argument("--confidence", required=True, choices=CONFIDENCES)
    p.add_argument("--source", metavar="TASK/JOB")
    p.add_argument("--paths", metavar="A,B")
    p = command(finding_sub, "close", "Close a finding: delete its file, log a line in findings/closed.md.",
                'Outcome: "fixed in <task-id>", "moved to backlog/<file>", "rejected: <reason>" or "duplicate of <finding>".',
                ['finding close .tasks/findings/2026-10-06-1512--slow-status-lookup.md --outcome "rejected: expected"'],
                [0, 1], cmd_finding_close)
    p.add_argument("file")
    p.add_argument("--outcome", required=True)

    # setup
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

    p = command(sub, "doctor", "Check the environment; prints a fix for each problem.",
                "Python, config, worktree root, git, harness detection, the other harness CLI, the Codex subagent cap.\n"
                "--repo also checks .tasks/, the repo profile, a throwaway worktree (setup.sh, commit) and the viewer.",
                ["doctor", "doctor --repo"], [0, 1, 2], cmd_doctor)
    p.add_argument("--repo", action="store_true")

    for name, group in (("job", job), ("decision", decision), ("finding", finding), ("setup", setup)):
        group.set_defaults(func=lambda args, g=group: (g.print_help(), EXIT_USAGE)[1])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return int(args.func(args) or 0)
    except SaeError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
