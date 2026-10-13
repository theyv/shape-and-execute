"""Main-session tokens ([MAIN-TOKENS]) and the per-phase stats of a task ([OVERVIEW-PHASE-STATS]).

Writing commands the orchestrator already runs (`sae new`, `approve spec`, `approve plan`,
`start`, `finish`, and `dispatch` and `collect` during execution) add a `session.snapshot` event:
the harness, the session ID and the session's cumulative token total, read from the harness's
own session file. Read-only commands never take one ([AMEND-1]). A phase's main-session tokens
are the sum of the differences between consecutive snapshots of the same session inside it.

The session files are internal to the harnesses and may change: every reader fails soft. A
missing session ID, file or field, or an unknown shape gives no snapshot, never an error and
never a guess ([DECISION-MAIN-TOKENS]).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

from .common import HARNESSES, iso

SNAPSHOT_EVENT = "session.snapshot"
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")  # also keeps glob characters out
CLAUDE_USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
CLAUDE_REQUIRED_FIELDS = ("input_tokens", "output_tokens")  # the API omits a cache field it did not use
TAIL_BLOCK = 1 << 20  # a Codex rollout can hold hundreds of MB: read it from the end
# (row name, task phase) of the phase-stats table.
PHASE_ROWS = (("shape", "shaping"), ("plan", "planning"), ("execution", "executing"))
NOTE_NO_SNAPSHOT = "no session snapshot: session file not readable, or an older sae"
NOTE_ONE_SNAPSHOT = "one snapshot per session: no difference to count yet"
NOTE_OTHER_SESSION = "the phase changed in another session"
NOTE_NOT_STARTED = "phase not started"


# ---------------------------------------------------------------- snapshot

def session_harness(env) -> str | None:
    """The harness whose session runs this `sae` command, from the environment only.
    SAE_HARNESS wins, as in config.detect_harness; an invalid value gives None here."""
    forced = env.get("SAE_HARNESS")
    if forced:
        return forced if forced in HARNESSES else None
    if env.get("CLAUDECODE") == "1" or env.get("CLAUDE_CODE_SESSION_ID"):
        return "claude"
    if env.get("CODEX_THREAD_ID"):
        return "codex"
    return None


def home_dir(env) -> Path:
    return Path(env["HOME"]) if env.get("HOME") else Path.home()


def only_match(paths) -> Path | None:
    """The single file a glob found; none or several give None (never a guess)."""
    found = [p for p in paths if p.is_file()]
    return found[0] if len(found) == 1 else None


def claude_transcript(session: str, env) -> Path | None:
    """`<config dir>/projects/*/<session-id>.jsonl`; config dir = CLAUDE_CONFIG_DIR, else ~/.claude."""
    base = Path(env["CLAUDE_CONFIG_DIR"]) if env.get("CLAUDE_CONFIG_DIR") else home_dir(env) / ".claude"
    return only_match((base / "projects").glob(f"*/{session}.jsonl"))


def codex_rollout(thread: str, env) -> Path | None:
    """`<CODEX_HOME>/sessions/YYYY/MM/DD/rollout-<stamp>-<thread-id>.jsonl`; CODEX_HOME defaults to ~/.codex."""
    base = Path(env["CODEX_HOME"]) if env.get("CODEX_HOME") else home_dir(env) / ".codex"
    return only_match((base / "sessions").glob(f"*/*/*/rollout-*-{thread}.jsonl"))


def is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def claude_total(path: Path) -> int | None:
    """Input + cache creation + cache read + output tokens of the main session's assistant
    entries. One API response is written as several entries with the same `message.id`: each
    id counts once. Sidechain (subagent) entries do not count; `sae collect` records those."""
    usage_by_id: dict[str, int] = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"usage"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue  # a line the harness is still writing
            if not isinstance(entry, dict) or entry.get("type") != "assistant" or entry.get("isSidechain"):
                continue
            message = entry.get("message")
            if not isinstance(message, dict) or "usage" not in message:
                continue
            usage, message_id = message["usage"], message.get("id")
            if not isinstance(usage, dict) or not isinstance(message_id, str) or not message_id:
                return None  # unknown shape
            if not all(is_count(usage.get(k)) for k in CLAUDE_REQUIRED_FIELDS) or \
                    not all(is_count(usage.get(k, 0)) for k in CLAUDE_USAGE_FIELDS):
                return None
            usage_by_id[message_id] = sum(usage.get(k, 0) for k in CLAUDE_USAGE_FIELDS)
    return sum(usage_by_id.values()) if usage_by_id else None


def lines_from_end(path: Path):
    """The lines of a file, last first, read in blocks from the end."""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        position, rest = handle.tell(), b""
        while position > 0:
            size = min(TAIL_BLOCK, position)
            position -= size
            handle.seek(position)
            lines = (handle.read(size) + rest).split(b"\n")
            rest = lines.pop(0)
            yield from reversed(lines)
        yield rest


def codex_total(path: Path) -> int | None:
    """`total_tokens` of the last `token_count` event's `info.total_token_usage`. A
    `token_count` event without `info` (rate limits only) carries no total and is passed over."""
    for raw in lines_from_end(path):
        if b'"token_count"' not in raw:
            continue
        try:
            entry = json.loads(raw.decode("utf-8", errors="replace"))
        except ValueError:
            continue  # a line the harness is still writing
        if not isinstance(entry, dict) or entry.get("type") != "event_msg":
            continue
        payload = entry.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue
        info = payload.get("info")
        if info is None:
            continue
        usage = info.get("total_token_usage") if isinstance(info, dict) else None
        total = usage.get("total_tokens") if isinstance(usage, dict) else None
        return total if is_count(total) else None  # unknown shape
    return None


def session_total(env=None) -> dict | None:
    """{"harness", "session", "total"} of the session that runs this command, or None."""
    env = os.environ if env is None else env
    try:
        harness = session_harness(env)
        if harness == "claude":
            session = env.get("CLAUDE_CODE_SESSION_ID") or ""
            find, count = claude_transcript, claude_total
        elif harness == "codex":
            session = env.get("CODEX_THREAD_ID") or ""
            find, count = codex_rollout, codex_total
        else:
            return None
        if not SESSION_ID_RE.match(session):
            return None
        path = find(session, env)
        total = count(path) if path else None
    except Exception:  # noqa: BLE001 - an internal format changed: no snapshot, never an error
        return None
    if total is None:
        return None
    return {"harness": harness, "session": session, "total": total}


def snapshot_event(command: str, phase_before: str | None, phase: str, env=None) -> dict | None:
    """The `session.snapshot` event of one command, or None. `phase_before`: the task's phase
    when the command began (None for `sae new`); `phase`: its phase after the command. The
    tokens since the session's previous snapshot belong to `phase_before`."""
    snapshot = session_total(env)
    if snapshot is None:
        return None
    return {"at": iso(), "type": SNAPSHOT_EVENT, "command": command, "phase_before": phase_before,
            "phase": phase, **snapshot}


def record_session_snapshot(task, command: str, phase_before: str | None) -> None:
    """Adds the snapshot event to a task opened for writing; adds nothing when there is none."""
    event = snapshot_event(command, phase_before, task.phase)
    if event is not None:
        fields = {k: v for k, v in event.items() if k not in ("at", "type")}
        task.event(SNAPSHOT_EVENT, **fields)


# ---------------------------------------------------------------- per-phase stats

def parse_time(value) -> dt.datetime | None:
    try:
        moment = dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.astimezone()


def phase_bounds(info: dict, events: list[dict]) -> dict:
    """{task phase: [start, end]} from the phase-change events: task.created, spec.approved, the
    first execution.started, task.finished; task.abandoned ends the phase it stopped."""
    def first(type_: str, **match):
        for event in events:
            if event.get("type") == type_ and all(event.get(k) == v for k, v in match.items()):
                return parse_time(event.get("at"))
        return None

    approvals = info.get("approvals") or {}
    created = first("task.created") or parse_time(info.get("created"))
    spec = first("spec.approved") or parse_time((approvals.get("spec") or {}).get("at"))
    started = first("execution.started", resumed=False) or first("execution.started")
    bounds = {"shaping": [created, spec], "planning": [spec, started],
              "executing": [started, first("task.finished")]}
    abandoned = first("task.abandoned")
    if abandoned:
        for phase in ("executing", "planning", "shaping"):
            if bounds[phase][0] and not bounds[phase][1]:
                bounds[phase][1] = abandoned
                break
    return bounds


def attempt_phase(job: dict, attempt: dict, bounds: dict) -> str:
    """The phase the attempt was dispatched in; by its job's kind when its start time is unknown."""
    started = parse_time(attempt.get("started"))
    if started:
        for phase in ("executing", "planning"):
            start = bounds[phase][0]
            if start and started >= start:
                return phase
        return "shaping"
    if job.get("kind") == "review":
        return {"spec": "shaping", "plan": "planning"}.get(job.get("target"), "executing")
    return "planning" if job.get("kind") == "planning" else "executing"


def main_session_tokens(events: list[dict]) -> tuple[dict, dict]:
    """(tokens by phase, notes by phase). A difference counts for a phase
    when the later snapshot began in the phase the earlier one left the task in; a difference
    across a phase change made by another session is a gap, not a guess."""
    chains: dict[tuple, list[dict]] = {}
    for event in events:
        if event.get("type") == SNAPSHOT_EVENT and is_count(event.get("total")) and event.get("session"):
            chains.setdefault((event.get("harness"), event["session"]), []).append(event)
    tokens: dict[str, int] = {}
    straddled: set[str] = set()
    for chain in chains.values():
        for earlier, later in zip(chain, chain[1:]):
            phase = earlier.get("phase")
            if later.get("phase_before") != phase:
                straddled.add(phase)
                continue
            delta = later["total"] - earlier["total"]
            if delta >= 0:  # a total never shrinks; a smaller one is a different count
                tokens[phase] = tokens.get(phase, 0) + delta
    notes = {phase: NOTE_OTHER_SESSION for phase in straddled}
    return tokens, notes


def phase_stats(state: dict, events: list[dict], now: dt.datetime | None = None) -> list[dict]:
    """Per-phase stats of a task ([OVERVIEW-PHASE-STATS]) from its state.json and events. Pure:
    reads no file. One row per phase, in order shape, plan, execution:

        phase           "shape" | "plan" | "execution"
        started, ended  ISO time of the phase change, or None (not started, or still running)
        running         True while the task is in this phase
        wall_s          seconds from start to end, or to `now` while running; None if not started
        main_tokens     main-session tokens, or None when unknown ...
        main_note       ... and then why (short text), else None
        subagent_tokens tokens `sae collect` recorded on the phase's attempts (unrecorded count 0)
        tokens          main_tokens + subagent_tokens, or None when main_tokens is unknown
        subagent_s      the attempts' recorded duration_s, summed
        jobs, attempts  jobs with an attempt in the phase, and those attempts

    An attempt belongs to the phase it was dispatched in. Old tasks (no snapshots) get
    main_tokens None and NOTE_NO_SNAPSHOT."""
    info = state.get("task") or {}
    now = now or dt.datetime.now().astimezone()
    bounds = phase_bounds(info, events)
    main, notes = main_session_tokens(events)
    snapshot_phases = {e.get(k) for e in events if e.get("type") == SNAPSHOT_EVENT for k in ("phase", "phase_before")}
    rows = {phase: {"subagent_tokens": 0, "subagent_s": 0, "jobs": set(), "attempts": 0} for _, phase in PHASE_ROWS}
    for job_id, job in (state.get("jobs") or {}).items():
        for attempt in job.get("attempts") or []:
            row = rows[attempt_phase(job, attempt, bounds)]
            row["attempts"] += 1
            row["jobs"].add(job_id)
            if is_count(attempt.get("tokens")):
                row["subagent_tokens"] += attempt["tokens"]
            if isinstance(attempt.get("duration_s"), (int, float)) and not isinstance(attempt["duration_s"], bool):
                row["subagent_s"] += attempt["duration_s"]
    out = []
    for name, phase in PHASE_ROWS:
        start, end = bounds[phase]
        running = info.get("phase") == phase and start is not None and end is None
        wall = (end or (now if running else None))
        tokens = main.get(phase)
        if tokens is not None:
            note = None
        elif start is None:
            note = NOTE_NOT_STARTED
        elif phase in notes:
            note = notes[phase]
        elif phase in snapshot_phases:
            note = NOTE_ONE_SNAPSHOT
        else:
            note = NOTE_NO_SNAPSHOT
        row = rows[phase]
        out.append({"phase": name, "started": start.isoformat() if start else None,
                    "ended": end.isoformat() if end else None, "running": running,
                    "wall_s": int((wall - start).total_seconds()) if start and wall else None,
                    "main_tokens": tokens, "main_note": note,
                    "subagent_tokens": row["subagent_tokens"],
                    "tokens": tokens + row["subagent_tokens"] if tokens is not None else None,
                    "subagent_s": round(row["subagent_s"]), "jobs": len(row["jobs"]), "attempts": row["attempts"]})
    return out
