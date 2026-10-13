"""Shared helpers of the sae tests: a throwaway repository, user config and worktree root.

Used by every test_<area>.py in this folder. Standard library only.
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # importing sae must not leave __pycache__ inside the skill's scripts/

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "shape-and-execute"
SCRIPTS = SKILL_DIR / "scripts"
SAE = SCRIPTS / "sae.py"


# Fake model names only: the skill never names real models, and neither do its tests.
EFFORTS = ["low", "medium", "high", "xhigh", "max"]
CLAUDE_MODELS = ["c-small", "c-mid", "c-big"]          # families, lightest first
CODEX_CATALOG = [                                      # $CODEX_HOME/models_cache.json of every sandbox
    {"slug": "cx-2-core", "visibility": "list", "efforts": EFFORTS + ["ultra"]},
    {"slug": "cx-2-lite", "visibility": "list", "efforts": EFFORTS},
    {"slug": "cx-1-core", "visibility": "list", "efforts": EFFORTS + ["ultra"]},
    {"slug": "cx-1-lite", "visibility": "list", "efforts": EFFORTS},
    {"slug": "cx-3-lite", "visibility": "hide", "efforts": EFFORTS},
]
# The tiers of the old rungs (L1-L3) plus L4, and the old level maps as tier cells.
LEVEL_TIERS = {"economy": {"mechanical": "L1", "normal": "L1", "hard": "L2"},
               "balanced": {"mechanical": "L1", "normal": "L2", "hard": "L3"},
               "max": {"mechanical": "L2", "normal": "L3", "hard": "L3"}}
REVIEW_TIERS = {"economy": "L2", "balanced": "L2", "max": "L3"}


def routing_block(tiers: dict) -> dict:
    tables = {}
    for phase in ("research", "planning", "execution", "review"):
        columns = ("normal", "hard") if phase in ("planning", "review") else ("mechanical", "normal", "hard")
        tables[phase] = {level: {d: {"tier": REVIEW_TIERS[level] if phase == "review" else LEVEL_TIERS[level][d]}
                                 for d in columns} for level in LEVEL_TIERS}
    return {"tiers_in_cells": True, "tiers": tiers, "tables": tables}


def config_for(worktrees: Path, points=None, provider="claude", codex=True) -> dict:
    """A schema-2 user config with fake models; review max → L3, execution balanced + hard → L3."""
    models = {"claude": [{"model": m, "family": True, "enabled": True, "efforts": list(EFFORTS)}
                         for m in CLAUDE_MODELS]}
    routing = {"claude": routing_block({"L1": {"model": "c-small", "effort": "medium"},
                                        "L2": {"model": "c-mid", "effort": "low"},
                                        "L3": {"model": "c-big", "effort": "high"},
                                        "L4": {"model": "c-big", "effort": "max"}})}
    if codex:
        models["codex"] = [{"model": "lite", "family": True, "enabled": True, "efforts": list(EFFORTS)},
                           {"model": "cx-1-lite", "family": False, "enabled": True, "efforts": list(EFFORTS)},
                           {"model": "core", "family": True, "enabled": True, "efforts": EFFORTS + ["ultra"]}]
        routing["codex"] = routing_block({"L1": {"model": "lite", "effort": "xhigh"},
                                          "L2": {"model": "core", "effort": "low"},
                                          "L3": {"model": "core", "effort": "medium"},
                                          "L4": {"model": "core", "effort": "high"}})
    return {
        "schema": 2, "models": models, "routing": routing,
        "defaults": {"interaction": "critical-only",
                     "levels": {"research": "balanced", "planning": "max", "execution": "balanced", "review": "max"},
                     "review": {"points": points if points is not None else [], "provider": provider}},
        "projects": {},
        "language": {"conversation": "pl", "artifacts": "en"},
        "worktrees": {"root": str(worktrees)},
        "parallel": {"max_writers": 3},
        "verify": {"timeout_s": 60},
    }


def schema1_config(worktrees: Path) -> dict:
    """The old user config (rungs and level maps), for the conversion tests."""
    return {
        "schema": 1,
        "rungs": {"claude": {"L1": {"model": "c-mid"}, "L2": {"model": "c-big"}, "L3": {"model": "c-big"}},
                  "codex": {"L1": {"model": "cx-2-lite", "effort": "xhigh"}, "L2": {"model": "cx-2-core", "effort": "medium"},
                            "L3": {"model": "cx-2-core", "effort": "high"}}},
        "level_map": LEVEL_TIERS, "review_level_map": REVIEW_TIERS,
        "defaults": {"interaction": "critical-only",
                     "levels": {"research": "balanced", "planning": "max", "execution": "balanced", "review": "max"},
                     "review": {"points": ["spec"], "provider": "codex"}},
        "language": {"conversation": "pl", "artifacts": "en"},
        "worktrees": {"root": str(worktrees)},
        "parallel": {"max_writers": 3},
        "verify": {"timeout_s": 60},
    }


def write_codex_catalog(codex_home: Path, catalog=None) -> None:
    models = [{"slug": m["slug"], "visibility": m["visibility"],
               "supported_reasoning_levels": [{"effort": e, "description": ""} for e in m["efforts"]]}
              for m in (CODEX_CATALOG if catalog is None else catalog)]
    (codex_home / "models_cache.json").write_text(json.dumps({"models": models}))


GIT_IDENTITY = {"GIT_AUTHOR_NAME": "Tester", "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "Tester", "GIT_COMMITTER_EMAIL": "t@example.com",
                "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin"}


def clean_env() -> dict:
    """os.environ without the owner's git, harness and sae variables, plus the test git identity."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CODEX_", "CLAUDE", "SAE_", "GIT_"))}
    env.update(GIT_IDENTITY)
    return env


_base_repo: Path | None = None


def base_repo() -> Path:
    """The throwaway repository every git Sandbox starts from: built once per process, copied per test.

    One commit (README.md, app.txt) on `main`, test identity in the repository config. Its
    core.hooksPath points to an empty folder of the base; each Sandbox repoints it to its own.
    """
    global _base_repo
    if _base_repo is None:
        root = Path(tempfile.mkdtemp(prefix="sae-base-")).resolve()
        atexit.register(shutil.rmtree, root, True)
        repo, hooks, env = root / "repo", root / "hooks", clean_env()
        repo.mkdir()
        hooks.mkdir()

        def git(*args):
            proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env)
            if proc.returncode != 0:
                raise AssertionError(f"git {args} failed: {proc.stderr}")

        git("init", "-q", "-b", "main")
        git("config", "user.name", "Tester")
        git("config", "user.email", "t@example.com")
        git("config", "core.hooksPath", str(hooks))
        (repo / "README.md").write_text("# demo\n")
        (repo / "app.txt").write_text("line one\n")
        git("add", ".")
        git("commit", "-q", "-m", "init")
        _base_repo = repo
    return _base_repo


_pycache: Path | None = None


def sae_pycache() -> Path:
    """A bytecode cache of sae for PYTHONPYCACHEPREFIX: built once per process, outside the skill.

    sae never writes bytecode, so every call compiled all of sae_lib again; reading it from
    here makes each sae call about a third faster. sae still runs as a subprocess.
    """
    global _pycache
    if _pycache is None:
        root = Path(tempfile.mkdtemp(prefix="sae-pycache-")).resolve()
        atexit.register(shutil.rmtree, root, True)
        warm = ("import importlib, pkgutil, sys; sys.path.insert(0, sys.argv[1]); import sae_lib; "
                "[importlib.import_module('sae_lib.' + m.name) for m in pkgutil.iter_modules(sae_lib.__path__)]")
        subprocess.run([sys.executable, "-c", warm, str(SCRIPTS)], check=True,
                       env={**clean_env(), "PYTHONPYCACHEPREFIX": str(root)})
        _pycache = root
    return _pycache


class Sandbox:
    """A repository, a user config and a worktree root in one temporary folder."""

    def __init__(self, tmp: Path, git: bool = True, points=None, provider="claude", write_config=True):
        self.tmp = tmp
        self.repo = tmp / "repo"
        if git:
            shutil.copytree(base_repo(), self.repo, symlinks=True)
        else:
            self.repo.mkdir()
        self.worktrees = tmp / "worktrees"
        self.worktrees.mkdir()
        self.config = tmp / "config.json"
        self.codex_home = tmp / "codex-home"
        self.codex_home.mkdir()
        write_codex_catalog(self.codex_home)
        self.hooks = tmp / "hooks"  # the repository's own hooks path: the owner's global hooks stay out
        self.hooks.mkdir()
        if write_config:
            self.config.write_text(json.dumps(config_for(self.worktrees, points, provider)))
        self.env = clean_env()
        self.viewer_state = tmp / "viewer-state"  # the viewer server's state folder, never the owner's
        self.env.update({"SAE_CONFIG": str(self.config), "SAE_HARNESS": "claude", "CODEX_HOME": str(self.codex_home),
                         "SAE_STATE_DIR": str(self.viewer_state), "SAE_VIEWER": "off",
                         "PYTHONPYCACHEPREFIX": str(sae_pycache())})
        if git:
            self.git("config", "core.hooksPath", str(self.hooks))

    def git(self, *args, cwd: Path | None = None) -> str:
        proc = subprocess.run(["git", *args], cwd=cwd or self.repo, capture_output=True, text=True, env=self.env)
        if proc.returncode != 0:
            raise AssertionError(f"git {args} failed: {proc.stderr}")
        return proc.stdout.strip()

    def sae(self, *args, code: int = 0, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
        proc = subprocess.run([sys.executable, str(SAE), *args], cwd=cwd or self.repo, capture_output=True,
                              text=True, env=self.env, input=stdin)
        if proc.returncode != code:
            raise AssertionError(f"sae {' '.join(args)}: exit {proc.returncode}, expected {code}\n"
                                 f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        return proc

    def json(self, *args, code: int = 0, cwd: Path | None = None) -> dict:
        return json.loads(self.sae(*args, "--json", code=code, cwd=cwd).stdout)

    def new_task(self, title: str, slug: str) -> str:
        return self.json("new", title, "--slug", slug)["task"]

    def task_dir(self, task: str) -> Path:
        """The live task folder: the home checkout before start, the task worktree after."""
        home = self.repo / ".tasks" / task
        if home.exists():
            return home
        for found in (*self.worktrees.glob(f"*/{task}/task/.tasks/{task}"),
                      *self.worktrees.glob(f"*/{task}/task/.tasks/done/{task}"), self.repo / ".tasks" / "done" / task):
            if found.exists():
                return found
        return home

    def task_worktree(self, task: str) -> Path:
        return Path(self.state(task)["task"]["worktree"])

    def hook(self, name: str, body: str) -> None:
        path = self.hooks / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def state(self, task: str) -> dict:
        return json.loads((self.task_dir(task) / "state.json").read_text())

    def events(self, task: str) -> list[dict]:
        return [json.loads(l) for l in (self.task_dir(task) / "events.jsonl").read_text().splitlines() if l]

    def job_file(self, task: str, job: str, objective: str = "Do one thing.", covers=(), verify=(), scope=()):
        def yaml_list(items):
            return "[" + ", ".join(json.dumps(i) for i in items) + "]"
        text = (f"---\nid: {job}\ncovers: {yaml_list(covers)}\nverify: {yaml_list(verify)}\n"
                + (f"scope: {yaml_list(scope)}\n" if scope else "")
                + f"---\n\n# {job}: test job\n\n## Objective\n{objective}\n")
        (self.task_dir(task) / "jobs").mkdir(exist_ok=True)
        (self.task_dir(task) / "jobs" / f"{job}.md").write_text(text)

    def result(self, task: str, rel_path: str, **front) -> None:
        path = self.task_dir(task) / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["---"] + [f"{k}: {v}" for k, v in front.items()] + ["---", "", "# Result", ""]
        path.write_text("\n".join(lines))

    def work(self, workdir: Path, file: str, text: str, message: str) -> None:
        (workdir / file).write_text(text)
        self.git("add", file, cwd=workdir)
        self.git("commit", "-q", "-m", message, cwd=workdir)

    def approve_plan(self, task: str) -> None:
        self.sae("approve", task, "spec")
        self.sae("approve", task, "plan")


def dispatch_workspace(sb: Sandbox, task: str, job: str, *extra: str) -> Path:
    data = sb.json("dispatch", task, job, *extra)
    return Path(data["workspace"])


class SaeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def sandbox(self, **kwargs) -> Sandbox:
        return Sandbox(self.tmp, **kwargs)
