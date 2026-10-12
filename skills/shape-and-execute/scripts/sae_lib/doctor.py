"""The doctor command."""

from __future__ import annotations

import contextlib
import os
import platform
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

from .common import EXIT_CONFIG, EXIT_OK, EXIT_USAGE, SaeError, emit, file_stamp, wrap_notice_lines
from .config import config_path, detect_harness, load_config, validate_config, worktree_root
from .gitutil import configured_hooks_path, find_root, git, git_ok, hash8, repo_cache_name, run
from .setup_mode import codex_cap_text, codex_subagent_cap
from .tasks import locate_tasks, tasks_dir
from .viewer import render_viewer_safely
from .workspaces import discard_worktree, leftover_reason, sae_worktrees, setup_worktree, sweep_merged_task_worktrees


def cmd_doctor(args) -> int:
    checks: list[tuple[str, str, str]] = []  # (mark, text, fix)

    def check(ok: bool | None, text: str, fix: str = "") -> None:
        checks.append(("✓" if ok else ("!" if ok is None else "✗"), text, "" if ok else fix))

    check(sys.version_info >= (3, 9), f"Python {platform.python_version()}", "Install Python 3.9 or newer.")
    config, config_ok = None, False
    try:
        config = load_config(allow_old=True)
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
        other = [h for h in config["models"] if h != harness]
        for name in other:
            check(bool(shutil.which(name)) or None, f"{name} CLI on PATH (only for cross-model review)",
                  f"Install {name}, or set the review provider to {harness}.")
    if shutil.which("codex") or (config_ok and "codex" in config["models"]):
        cap = codex_subagent_cap()
        check(cap["ok"], codex_cap_text(cap).splitlines()[0],
              f"Set [agents] max_threads = {cap['recommended']} in {cap['config']} (setup mode can do it).")
    discarded = doctor_worktrees(config if config_ok else None, check, args.discard)
    if args.repo:
        doctor_repo(config if config_ok else None, check)
    lines = discarded + [f"{mark} {text}" + (f"\n    fix: {fix}" if fix else "") for mark, text, fix in checks]
    failed = [c for c in checks if c[0] == "✗"]
    emit(args, wrap_notice_lines("\n".join(lines)),
         {"checks": [{"ok": m != "✗", "mark": m, "text": t, "fix": f} for m, t, f in checks]})
    if not config_ok:
        return EXIT_CONFIG
    return EXIT_USAGE if failed else EXIT_OK


def doctor_worktrees(config: dict | None, check, discard: str | None) -> list[str]:
    """`--discard`, then the sweep of merged task worktrees, then every leftover worktree of this
    repository with the reason it stays ([WORKTREE-CLEANUP], 07-cli-spec §7.4). Returns the
    lines of a discard."""
    root, is_git = find_root()
    if not is_git:
        if discard:
            raise SaeError(EXIT_USAGE, "--discard needs a git repository: run it in the repository.")
        return []
    discarded = discard_worktree(root, Path(discard), locate_tasks(root)) if discard else []
    removed, _ = sweep_merged_task_worktrees(root, quiet=True)
    for line in removed:
        check(True, line)
    located = locate_tasks(root)
    registered = sae_worktrees(root)
    for path, task_id, name in registered:
        reason, attention = leftover_reason(root, path, task_id, name, located)
        check(None if attention else True, f"worktree {path}\n    why it stays: {reason}",
              f"Commit or move what you need, then:\n      sae doctor --discard {shlex.quote(str(path))}")
    if config is not None:
        cache = worktree_root(config) / repo_cache_name(root)
        known = {p.resolve() for p, _, _ in registered}
        for folder in sorted(cache.glob("*/*")) if cache.is_dir() else []:
            if folder.is_dir() and not folder.parent.name.startswith("_") and folder.resolve() not in known:
                check(None, f"folder kept: {folder}\n    why: not a git worktree any more",
                      "Look inside, then delete it by hand if nothing in it matters.")
        for folder in sorted(cache.glob("*")) if cache.is_dir() else []:
            if folder.is_dir():
                with contextlib.suppress(OSError):
                    folder.rmdir()  # empty task folders of the cache
        with contextlib.suppress(OSError):
            cache.rmdir()
    if not registered:
        check(True, "no leftover worktrees")
    return discarded


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
                "In a git repository: removes the task worktrees of finished tasks whose branch is merged (when\n"
                "they hold no uncommitted work), then lists every leftover worktree with the reason it stays.\n"
                "--repo also checks .tasks/, the repo profile, a throwaway worktree (setup.sh, commit) and the viewer.\n"
                "--discard <worktree> removes one sae worktree although it holds work, after printing what is\n"
                "lost; its branch stays. It refuses running jobs' worktrees and the task worktree of a task\n"
                "that is not finished or abandoned.",
                ["doctor", "doctor --repo", "doctor --discard ~/Library/Caches/shape-and-execute/worktrees/app-1a2b3c4d/"
                 "2026-10-06-1430--claims-status/task"], [0, 1, 2, 4], cmd_doctor)
    p.add_argument("--repo", action="store_true", help="also check this repository's setup")
    p.add_argument("--discard", metavar="WORKTREE",
                   help="remove this sae worktree although it holds work (the owner's explicit word)")
