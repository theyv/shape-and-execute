"""The viewer server's life: state folder, known repositories, start and reuse,
`sae view` and the viewer link of `sae new`. The server itself is server.py."""

from __future__ import annotations

import contextlib
import errno
import fcntl
import hashlib
import http.client
import json
import os
import platform
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from .common import (
    EXIT_OK,
    EXIT_USAGE,
    SKILL_DIR,
    STAMPED_FILE_RE,
    SaeError,
    emit,
    iso,
    read_json,
    sae_prefix,
    warn,
    write_json,
)
from .gitutil import find_root, hash8

STATE_DIR_ENV = "SAE_STATE_DIR"
IDLE_ENV = "SAE_VIEWER_IDLE_S"
VIEWER_SWITCH_ENV = "SAE_VIEWER"       # "off": `sae new` prints the start command, no server (tests)
DEFAULT_IDLE_S = 4 * 3600
START_TIMEOUT_S = 8.0
VIEWER_ASSETS = SKILL_DIR / "assets" / "viewer"


class NoSockets(Exception):
    """Binding a local port is not allowed here (a sandbox without network)."""


class NoStateFolder(Exception):
    """The state folder cannot be written here: a sandbox that confines writes to the workspace,
    or a state path that is not a folder (below a regular file)."""


# What a sandbox answers to a forbidden write; any other OSError is a real failure.
FORBIDDEN_ERRNOS = (errno.EPERM, errno.EACCES, errno.EROFS)
# What a state path below a regular file, or a file in place of the folder, answers.
NOT_A_FOLDER_ERRNOS = (errno.ENOTDIR, errno.EEXIST)


# ---------------------------------------------------------------- state folder

def state_dir() -> Path:
    if os.environ.get(STATE_DIR_ENV):
        return Path(os.environ[STATE_DIR_ENV]).expanduser()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "shape-and-execute"
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base).expanduser() / "shape-and-execute"


def state_path(name: str) -> Path:
    return state_dir() / name


def write_private(path: Path, data) -> None:
    """A state file, mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
    os.chmod(path, 0o600)


def read_state(name: str) -> dict | None:
    with contextlib.suppress(OSError, ValueError):
        data = read_json(state_path(name))
        return data if isinstance(data, dict) else None
    return None


@contextlib.contextmanager
def state_lock(name: str):
    path = state_path(name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600), "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def idle_limit() -> float:
    """SAE_VIEWER_IDLE_S when it is a number (tests), else the built-in four hours."""
    with contextlib.suppress(ValueError, TypeError):
        return max(0.5, float(os.environ.get(IDLE_ENV, DEFAULT_IDLE_S)))
    return float(DEFAULT_IDLE_S)


def code_version() -> str:
    """The `sae` version a running server must share to be reused: the code and viewer files."""
    digest = hashlib.sha256(str(SKILL_DIR).encode())
    files = sorted((SKILL_DIR / "scripts").rglob("*.py")) + sorted(VIEWER_ASSETS.glob("*"))
    for path in files:
        with contextlib.suppress(OSError):
            stat = path.stat()
            digest.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode())
    return digest.hexdigest()[:12]


# ---------------------------------------------------------------- known repositories

def repo_key(path: Path) -> str:
    return hash8(path)


def known_repos() -> list[dict]:
    """The known repositories whose main worktree still exists, the most recently seen first."""
    repos = (read_state("repos.json") or {}).get("repos") or []
    alive = [r for r in repos if isinstance(r, dict) and r.get("path") and Path(r["path"]).is_dir()]
    return sorted(alive, key=lambda r: r.get("last_seen") or "", reverse=True)


def remember_repo(root: Path, touch: bool = False) -> dict:
    """Adds the repository of `root` to the known list when missing; `touch` also renews its
    `last_seen` (`sae view`). Read-only commands never call it."""
    from .config import main_worktree  # resolved path, the key of project defaults too
    main = main_worktree(root)
    key = repo_key(main)
    entry = {"key": key, "name": main.name, "path": str(main), "last_seen": iso()}
    current = next((r for r in (read_state("repos.json") or {}).get("repos") or [] if r.get("key") == key), None)
    if current and not touch:
        return current
    with state_lock("repos.json"):
        repos = [r for r in (read_state("repos.json") or {}).get("repos") or []
                 if isinstance(r, dict) and r.get("key") != key]
        write_private(state_path("repos.json"), {"repos": repos + [entry]})
    return entry


def remember_repo_safely(root: Path) -> None:
    try:
        remember_repo(root)
    except Exception as exc:  # the known list never fails a command
        warn(f"viewer: repository not added to the known list: {exc}")


def repo_known(root: Path) -> bool:
    """Whether the repository of `root` is on the known list (`sae doctor --repo`)."""
    from .config import main_worktree
    key = repo_key(main_worktree(root))
    return any(isinstance(r, dict) and r.get("key") == key
               for r in (read_state("repos.json") or {}).get("repos") or [])


def stamped_items(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.glob("*.md") if STAMPED_FILE_RE.match(p.name)), reverse=True)


# ---------------------------------------------------------------- start, reuse, stop

def health(port: int, timeout: float = 1.5) -> dict | None:
    """The answer of a server on `port` to /api/health, or None."""
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        conn.request("GET", "/api/health", headers={"Host": f"127.0.0.1:{port}"})
        response = conn.getresponse()
        body = response.read()
        conn.close()
        if response.status != 200:
            return None
        data = json.loads(body)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, http.client.HTTPException):
        return None


def running_server() -> dict | None:
    """viewer.pid of a server that answers, with its health; None when there is none."""
    info = read_state("viewer.pid")
    if not info or not isinstance(info.get("port"), int):
        return None
    answer = health(info["port"])
    if not answer or answer.get("pid") != info.get("pid"):
        return None
    return {**info, **answer}


def check_sockets() -> None:
    """Raises NoSockets where binding 127.0.0.1 is forbidden (a Codex sandbox without network)."""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except OSError as exc:
        raise NoSockets(str(exc))
    try:
        probe.bind(("127.0.0.1", 0))
    except OSError as exc:
        if exc.errno in (errno.EPERM, errno.EACCES):
            raise NoSockets(str(exc))
        raise
    finally:
        probe.close()


def stop_server(info: dict, wait_s: float = 5.0) -> bool:
    """Stops the server of `info` (its health said this pid) and waits until it is gone."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.kill(info["pid"], signal.SIGTERM)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            os.kill(info["pid"], 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.05)
    return False


def start_server() -> dict:
    """Starts a detached server and waits for its health; raises NoSockets or SaeError."""
    check_sockets()
    log = state_path("viewer.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as out:
        os.chmod(log, 0o600)
        proc = subprocess.Popen([sys.executable, str(SKILL_DIR / "scripts" / "sae.py"), "view", "--serve"],
                                stdin=subprocess.DEVNULL, stdout=out, stderr=out, cwd=str(state_dir()),
                                start_new_session=True)
    deadline = time.time() + START_TIMEOUT_S
    while time.time() < deadline:
        info = running_server()
        if info and info.get("pid") == proc.pid:
            return info
        if proc.poll() is not None:
            tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
            if any("Operation not permitted" in line or "Permission denied" in line for line in tail):
                raise NoSockets(" ".join(tail))
            raise SaeError(EXIT_USAGE, "The viewer server did not start: " + (" ".join(tail) or "no output")
                           + f"\nLog: {log}")
        time.sleep(0.05)
    raise SaeError(EXIT_USAGE, f"The viewer server did not answer within {START_TIMEOUT_S:.0f} s. Log: {log}")


def ensure_server() -> dict:
    """The running server of this `sae` version, started when needed."""
    with state_lock("viewer"):
        info = running_server()
        if info and info.get("version") == code_version():
            return info
        if info:
            stop_server(info)
        return start_server()


def start_for(root: Path) -> tuple[dict, dict]:
    """(known-list entry, running server) for `root`. Sockets are checked before any state write,
    so a sandbox reaches the fallback ([EDGE-NO-SOCKETS]); raises NoSockets or NoStateFolder
    where the sandbox forbids either or the state path is not a folder."""
    check_sockets()
    try:
        entry = remember_repo(root, touch=True)
        return entry, ensure_server()
    except OSError as exc:
        if exc.errno in FORBIDDEN_ERRNOS + NOT_A_FOLDER_ERRNOS:
            raise NoStateFolder(f"{state_dir()}: {exc.strerror or exc}") from exc
        raise


def viewer_url(info: dict, repo: str | None = None, task_id: str | None = None) -> str:
    hash_parts = [f"repo={repo}"] if repo else []
    if task_id:
        hash_parts += [f"task={task_id}", "tab=plan"]
    return f"http://127.0.0.1:{info['port']}/" + ("#" + "&".join(hash_parts) if hash_parts else "")


def start_command(root: Path, task_id: str | None) -> str:
    """The one command that starts the viewer in the owner's terminal ([EDGE-NO-SOCKETS])."""
    return f"cd {shlex.quote(str(root))} && {sae_prefix()} view" + (f" {task_id}" if task_id else "") + " --open"


def open_url(url: str) -> None:
    opener = "open" if platform.system() == "Darwin" else "xdg-open"
    if shutil.which(opener):
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        warn(f"{opener} not found; open the URL yourself")


def viewer_link(root: Path, task_id: str) -> tuple[str | None, str]:
    """For `sae new` ([VIEWER-LINK-AT-NEW]): (URL, line to print). Never fails: where the
    server cannot start, the line names the command that starts it."""
    command = start_command(root, task_id)
    if os.environ.get(VIEWER_SWITCH_ENV) == "off":
        return None, f"Viewer:\n  {command}"
    try:
        entry, info = start_for(root)
        url = viewer_url(info, entry["key"], task_id)
        return url, f"Viewer: {url}"
    except NoSockets:
        return None, f"Viewer: cannot start here (no local sockets). In your terminal:\n  {command}"
    except NoStateFolder as exc:
        return None, f"Viewer: cannot start here (state folder not writable: {exc}). In your terminal:\n  {command}"
    except Exception as exc:  # the viewer never fails `sae new`
        return None, f"Viewer: not started ({str(exc).splitlines()[0]}). In your terminal:\n  {command}"


# ---------------------------------------------------------------- the command

def cmd_view(args) -> int:
    if args.serve:
        from .server import serve
        return serve()
    if args.stop:
        info = running_server()
        if not info:
            with contextlib.suppress(FileNotFoundError):
                state_path("viewer.pid").unlink()
            emit(args, "No viewer server is running.", {"stopped": False})
            return EXIT_OK
        stopped = stop_server(info)
        emit(args, f"Viewer server on port {info['port']} stopped." if stopped
             else f"The viewer server (pid {info['pid']}) did not stop.", {"stopped": stopped})
        return EXIT_OK if stopped else EXIT_USAGE
    root, _ = find_root()
    task_id = None
    if args.task:
        from .tasks import resolve_task
        task_id = resolve_task(root, args.task)
    try:
        entry, info = start_for(root)
    except (NoSockets, NoStateFolder) as exc:
        command = start_command(root, task_id)
        why = ("this sandbox forbids local sockets" if isinstance(exc, NoSockets)
               else f"the state folder cannot be written ({exc})")
        print(f"The viewer cannot start here: {why}.\nRun this in your own terminal:\n  {command}", file=sys.stderr)
        if args.json:
            print(json.dumps({"url": None, "command": command}))
        return EXIT_USAGE
    url = viewer_url(info, entry["key"], task_id)
    if args.open:
        open_url(url)
    emit(args, url, {"url": url, "port": info["port"], "pid": info["pid"], "repo": entry["key"]})
    return EXIT_OK


def register_view(sub, command):
    """Add the `view` command to the parser."""
    p = command(sub, "view", "Start the viewer server, or reuse the running one, and print its URL.",
                "One server serves every repository where sae has run; the URL opens this repository\n"
                "(with a task: its Plan tab). It listens on 127.0.0.1 only and stops by itself after\n"
                f"{DEFAULT_IDLE_S // 3600} hours without requests. Where local sockets are forbidden (a sandbox), it exits 1\n"
                "and prints the one command that starts it in your terminal.",
                ["view", "view claims-status --open", "view --stop"], [0, 1], cmd_view)
    p.add_argument("task", nargs="?")
    p.add_argument("--open", action="store_true")
    p.add_argument("--stop", action="store_true", help="stop the running viewer server")
    p.add_argument("--serve", action="store_true",
                   help="run the server in this process (what sae view starts detached)")
