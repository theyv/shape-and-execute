#!/usr/bin/env python3
"""Publish check for this repository (push or release): preconditions, changes, privacy scan.

Read-only. --mode push scans what a push of the current branch would send (HEAD against its
upstream, else origin/main). --mode release (default) compares HEAD with the latest tag, on
main only. Exit 0: go on with the skill. Exit 1: fix what the output names first.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Changes here alter the first run or an upgrade: the repo profile's owner-walkthrough rule applies.
SETUP_PATHS = (
    "skills/shape-and-execute/references/modes/setup.md",
    "skills/shape-and-execute/scripts/sae_lib/setup_mode.py",
    "skills/shape-and-execute/scripts/sae_lib/config.py",
    "skills/shape-and-execute/scripts/sae_lib/doctor.py",
    "skills/shape-and-execute/templates/repo/profile.md",
)
USER_FACING_PREFIX = "skills/shape-and-execute/"

# Generic patterns only: this file is public, so it names no person and no private project.
# A home folder at the start of a path (not "$SB/home/..."), with a lowercase user name.
HOME_PATH = re.compile(r"(?<![\w$}\]).-])(/Users/|/home/|[A-Za-z]:\\Users\\)(?!Shared\b)[a-z0-9_][a-z0-9._-]*")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Reserved example domains (RFC 2606) and the noreply addresses commits use.
ALLOWED_EMAIL = re.compile(r"(@users\.noreply\.github\.com|^noreply@anthropic\.com|@example\.(com|org|net)|"
                           r"\.(invalid|test|example)|@localhost)$")
# Task records are committed on purpose; any other JSON Lines file looks like a raw log.
ALLOWED_JSONL = re.compile(r"^\.tasks/(done/)?[^/]+/events\.jsonl$")


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def private_terms() -> list[str]:
    """Terms the owner keeps outside the repository, one per line (names, private projects)."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / "sae-release" / "private-terms.txt"
    if not path.is_file():
        return []
    return [t.strip() for t in path.read_text().splitlines() if t.strip() and not t.startswith("#")]


def scan(base: str) -> list[str]:
    hits = []
    terms = [t.lower() for t in private_terms()]
    current = "?"
    for line in git("diff", f"{base}..HEAD", "--unified=0", "--no-color").splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        text = line[1:]
        if HOME_PATH.search(text):
            hits.append(f"{current}: home path: {text.strip()[:120]}")
        for mail in EMAIL.findall(text):
            if not ALLOWED_EMAIL.search(mail):
                hits.append(f"{current}: e-mail address: {mail}")
        for term in terms:
            if term in text.lower():
                hits.append(f"{current}: private term from your list: {text.strip()[:120]}")
    for name in git("diff", "--name-only", "--diff-filter=A", f"{base}..HEAD").splitlines():
        if name.endswith(".jsonl") and not ALLOWED_JSONL.match(name):
            hits.append(f"{name}: a JSON Lines file that is not a task record (raw log?)")
    for entry in git("log", f"{base}..HEAD", "--format=%h%x09%ae%x09%ce%x09%B%x00").split("\x00"):
        if not entry.strip():
            continue
        sha, author, committer, body = (entry.strip("\n").split("\t", 3) + ["", "", ""])[:4]
        for mail in (author, committer):
            if not ALLOWED_EMAIL.search(mail):
                hits.append(f"commit {sha}: author or committer e-mail {mail}")
        if HOME_PATH.search(body) or any(t in body.lower() for t in terms):
            hits.append(f"commit {sha}: message holds a home path or a private term")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=("push", "release"), default="release",
                        help="push: what a push would send; release: everything since the latest tag")
    parser.add_argument("--base", help="compare with this ref instead of the default base")
    args = parser.parse_args()

    problems = []
    branch = git("branch", "--show-current").strip()
    git("fetch", "--quiet", "origin")
    dirty = [l[3:] for l in git("status", "--porcelain").splitlines() if not l.startswith("??")]
    if args.mode == "push":
        upstream = subprocess.run(["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
                                  capture_output=True, text=True).stdout.strip()
        base = args.base or upstream or "origin/main"
        if dirty:
            print("Note: uncommitted changes are not part of the push: " + ", ".join(dirty))
        behind = git("rev-list", "--count", f"HEAD..{base}").strip()
        if behind != "0":
            problems.append(f"{branch} is {behind} commit(s) behind {base}; pull first")
    else:
        base = args.base or git("describe", "--tags", "--abbrev=0").strip()
        if branch != "main":
            problems.append(f"on branch {branch!r}; releases are made from main")
        if dirty:
            problems.append("uncommitted changes: " + ", ".join(dirty))
        behind = git("rev-list", "--count", "HEAD..origin/main").strip()
        if behind != "0":
            problems.append(f"main is {behind} commit(s) behind origin/main; pull first")

    commits = git("rev-list", "--count", f"{base}..HEAD").strip()
    changed = git("diff", "--name-only", f"{base}..HEAD").splitlines()
    tasks = sorted({p.split("/")[2] for p in changed if p.startswith(".tasks/done/") and p.count("/") >= 3})
    setup = [p for p in changed if p in SETUP_PATHS]
    user_facing = any(p.startswith(USER_FACING_PREFIX) for p in changed)

    print(f"Mode: {args.mode} · base: {base} · {commits} commit(s) since")
    if args.mode == "release":
        print("Tasks finished since the base:" + ("".join(f"\n  {t}" for t in tasks) or " none"))
        if setup:
            print("Setup or upgrade files changed (owner-walkthrough rule applies):"
                  + "".join(f"\n  {p}" for p in setup))
        if user_facing and "README.md" not in changed:
            print("The skill changed but README.md did not: check README against the changes.")

    hits = scan(base)
    if not private_terms():
        print("Note: no private-terms list; only generic patterns were scanned"
              " ($XDG_CONFIG_HOME/sae-release/private-terms.txt, one term per line).")
    for p in problems:
        print(f"PROBLEM: {p}")
    for h in hits:
        print(f"PRIVACY: {h}")
    if problems or hits:
        print("Next: fix the lines above, commit, and run this check again.")
        return 1
    print("Next: push." if args.mode == "push" else "Next: continue with step 2 of the release in SKILL.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
