"""The doctor command."""

from __future__ import annotations

import os
import platform
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

from .common import EXIT_CONFIG, EXIT_OK, EXIT_USAGE, SaeError, emit, file_stamp
from .config import config_path, detect_harness, load_config, validate_config, worktree_root
from .gitutil import configured_hooks_path, find_root, git, git_ok, hash8, repo_cache_name, run
from .setup_mode import codex_cap_text, codex_subagent_cap
from .tasks import tasks_dir
from .viewer import render_viewer_safely
from .workspaces import setup_worktree


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
    if is_git:
        hooks = hooks_found(root)
        if hooks:
            check(None, f"git hooks found: {hooks}",
                  "sae runs its own git operations without hooks. Move dependency installs from a hook into "
                  ".tasks/repo/setup.sh, which runs in every new worktree.")
    if is_git and config is not None and git_ok(root, "rev-parse", "--verify", "--quiet", "HEAD"):
        branch = f"sae-doctor-{file_stamp()}"
        path = worktree_root(config) / repo_cache_name(root) / "_doctor"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            git(root, "worktree", "add", "--quiet", "-b", branch, str(path), "HEAD")
            log = Path(tempfile.gettempdir()) / f"sae-doctor-setup-{hash8(root)}.log"
            setup_worktree(root, path, "_doctor", "_doctor", log)
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


def hooks_found(root: Path) -> str:
    """A hooks path (`core.hooksPath`) or hook scripts in the repository's hooks folder."""
    configured = configured_hooks_path(root)
    if configured:
        return f"core.hooksPath = {configured}"
    folder = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False) or ".") / "hooks"
    scripts = sorted(p.name for p in folder.iterdir() if p.is_file() and not p.name.endswith(".sample")) \
        if folder.is_dir() else []
    return f"{folder}: {', '.join(scripts)}" if scripts else ""


def register_doctor(sub, command):
    """Add the `doctor` command to the parser."""
    p = command(sub, "doctor", "Check the environment; prints a fix for each problem.",
                "Python, config, worktree root, git, harness detection, the other harness CLI, the Codex subagent cap.\n"
                "--repo also checks .tasks/, the repo profile, a throwaway worktree (setup.sh, commit) and the viewer.",
                ["doctor", "doctor --repo"], [0, 1, 2], cmd_doctor)
    p.add_argument("--repo", action="store_true")
