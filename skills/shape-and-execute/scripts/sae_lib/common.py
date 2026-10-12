"""Constants, exit codes, errors, time, file I/O and output helpers shared by every module."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import shlex
import sys
import tempfile
import textwrap
import unicodedata
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent.parent
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
OUTPUT_WIDTH = 72            # owner-facing text: cards, notices, hints ([NARROW-OUTPUT]); map lines excepted
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
CONFIG_HINT = ('Run the shape-and-execute skill in setup mode.\n'
               'Claude Code:\n  /shape-and-execute setup\n'
               'Codex:\n  $shape-and-execute setup')


class SaeError(Exception):
    """An error with the exit code it maps to."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def fail(code: int, message: str):
    raise SaeError(code, message)


def warn(message: str) -> None:
    print(wrap_notice_lines(f"warning: {message}"), file=sys.stderr)


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


def emit(args, text: str, data=None, *, verbatim: tuple[str, ...] = ()) -> None:
    """Print owner text through the shared wrapper; JSON and explicit agent artifacts stay exact."""
    if getattr(args, "json", False):
        print(json.dumps(data if data is not None else {"text": text}, indent=2, ensure_ascii=False))
    elif text:
        print(wrap_notice_lines(text, verbatim=verbatim))


def table(rows: list[list[str]], indent: str = "  ") -> str:
    if not rows:
        return ""
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    return "\n".join(indent + "  ".join(str(c).ljust(w) for c, w in zip(row, widths)).rstrip() for row in rows)


def wrap(text: str, indent: str = "", hang: str = "  ", width: int = OUTPUT_WIDTH) -> str:
    """One owner-facing line wrapped within `width` columns; continuation lines get `hang`
    after `indent` ([NARROW-OUTPUT])."""
    return wrap_notice_lines("\n".join(indent + line for line in text.split("\n")), hang=hang, width=width)


OWNER_COMMAND_PREFIXES = ("sae ", "python3 ", "cd ", "/shape-and-execute ", "$shape-and-execute ")
PROCESS_MAP_PREFIXES = ("💡", "📐", "🔨")
LABELED_COMMAND_RE = re.compile(r"^(.*?:)\s+((?:sae|python3|cd|/shape-and-execute|\$shape-and-execute) .*)$")


def wrap_notice_lines(text: str, *, hang: str = "  ", width: int = OUTPUT_WIDTH,
                      verbatim: tuple[str, ...] = ()) -> str:
    """One owner output formatter: wrap prose, indent whole commands and preserve paste artifacts.

    Commands belong after a label or on their own line. Only explicit agent artifacts,
    process map lines, whole commands and paths with short labels may exceed the width.
    """
    if verbatim:
        blocks = set(block for block in verbatim if block)
        if blocks:
            pattern = "(" + "|".join(re.escape(block) for block in sorted(blocks, key=len, reverse=True)) + ")"
            return "".join(part if part in blocks else wrap_notice_lines(part, hang=hang, width=width)
                           for part in re.split(pattern, text))
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        if line.startswith(PROCESS_MAP_PREFIXES):
            lines.append(line)
            continue
        if stripped.startswith(OWNER_COMMAND_PREFIXES):
            lines.append((indent or "  ") + stripped)
            continue
        labeled = LABELED_COMMAND_RE.match(stripped)
        if labeled:
            label, command = labeled.groups()
            lines.append(wrap_notice_lines(indent + label, hang=hang, width=width))
            lines.append(indent + "  " + command)
            continue
        if len(line) <= width:
            lines.append(line)
            continue
        words = stripped.split()
        path_line = bool(words and "/" in words[-1] and len(stripped) - len(words[-1]) <= 30)
        if path_line:
            lines.append(line)
            continue
        # A long path stays copyable. Other free-text words must obey the width too.
        available = max(1, width - len(indent) - len(hang))
        prose = " ".join(word if "/" in word else " ".join(word[i:i + available]
                        for i in range(0, len(word), available)) for word in words)
        lines.append("\n".join(textwrap.wrap(prose, width=width, initial_indent=indent,
                                            subsequent_indent=indent + hang, break_long_words=False,
                                            break_on_hyphens=False)) or indent.rstrip())
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def wrap_parts(parts: list[str], indent: str = "  ", sep: str = " · ", width: int = OUTPUT_WIDTH,
               hang: str = "") -> str:
    """Joins `parts` with `sep`, breaking lines only between parts, each line within `width`
    when every part fits ([NARROW-OUTPUT])."""
    lines, current = [], ""
    for part in parts:
        line_indent = indent + (hang if lines else "")
        candidate = f"{current}{sep}{part}" if current else part
        if current and len(line_indent) + len(candidate) > width:
            lines.append(line_indent + current)
            candidate = part
        current = candidate
    if current:
        lines.append(indent + (hang if lines else "") + current)
    return "\n".join(lines)


def sae_prefix() -> str:
    return f"python3 {shlex.quote(str(SKILL_DIR / 'scripts' / 'sae.py'))}"


def changed_by() -> str:
    """`by` of a change event: `viewer` when the viewer server runs the command
    (SAE_CHANGED_BY=viewer), else `cli`."""
    return "viewer" if os.environ.get("SAE_CHANGED_BY") == "viewer" else "cli"


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


class Parser(argparse.ArgumentParser):
    """Usage errors exit 1; exit 2 means a missing user config."""

    def error(self, message):
        print(wrap_notice_lines(self.format_usage()).rstrip(), file=sys.stderr)
        print(wrap_notice_lines(f"error ({self.prog}): {message}"), file=sys.stderr)
        sys.exit(EXIT_USAGE)
