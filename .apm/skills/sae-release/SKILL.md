---
name: sae-release
description: "Push or release this repository (shape-and-execute). Push mode: a privacy and precondition check of what the push would send, then the push. Release mode: the same check, README and setup guide brought in line with the changes since the last tag, tests, then a tag and a GitHub release after the owner's yes. Use whenever this repository is pushed or released."
---

# sae-release

This repository is public: everything pushed or released is published. Run every command
from the repository root. Talk to the owner in their language; write release notes, commits
and docs in English.

**Pick the mode.** The owner asks to push → **push mode**: step 1, then push. The owner asks
for a release → **release mode**: steps 1 to 7.

**When you are an orchestrator** (you coordinate other agents, for example in a
shape-and-execute session), keep your context clean: give steps 2, 4 and the notes draft of
step 5 to subagents that report back in a few lines. Keep the owner's decisions, the fixes the
owner approved, and publishing (steps 6 and 7) yourself.

## 1. Check

    python3 <this skill's folder>/scripts/publish_check.py --mode push|release

Read-only; `--help` shows the options. Push mode checks what the push would send (HEAD against
its upstream). Release mode compares HEAD with the latest tag on `main` and also lists the
finished tasks since then, changed setup files and a README hint. Both scan for private data:
home paths, e-mail addresses, author identities, raw logs, and the terms in the owner's
private list outside the repository. The privacy rules themselves are in `AGENTS.md`.

Exit 1: fix what it names, commit, run it again. Exit 0 in push mode: `git push`, and stop.

## 2. Docs in sync

For each finished task the check lists, read its `.tasks/done/<task>/specs.md` (requirement
headings and `## Amendments`) and skim `git log <tag>..HEAD`. Then read `README.md` and the
guide in `skills/shape-and-execute/references/modes/setup.md` (step 2), and list every
statement that the changes made wrong or that misses a user-visible feature. Show the list to
the owner, fix after their yes, and commit.

## 3. Walkthrough

When the check lists changed setup files, the owner-walkthrough rule in `.tasks/repo/profile.md`
applies. If none of the listed tasks has `jobs/FIRST-RUN-WALKTHROUGH.result.md`, offer the
owner a walkthrough with `tests/tools/walkthrough/` (its README) before you go on.

## 4. Tests

Run the full suite from `.tasks/repo/profile.md`, section "Validation commands". A failure
stops the release.

## 5. Version and notes

- Version: propose the next one. Before 1.0, new features raise the minor number and fixes
  only raise the patch number. The owner decides.
- Notes: follow the shape of the last release (`gh release view <tag>`): one summary line,
  grouped bullets with a bold lead-in each, the install command at the end. Write from the
  user's side; no job IDs or task internals. Save them to a temporary file outside the
  repository and show them to the owner.

## 6. Publish (after the owner's yes to version and notes)

    git push origin main
    git tag -a v<X.Y.Z> -m "shape-and-execute <X.Y.Z>"
    git push origin v<X.Y.Z>
    gh release create v<X.Y.Z> --title "shape-and-execute <X.Y.Z>" --notes-file <notes file>

Never force-push and never move an existing tag. If a step fails, stop and report.

## 7. After

If the owner installs the skill globally through APM, offer `apm update -g --yes`. It changes
their global agent setup, so ask first. Then check that the installed `sae --help` shows the
new commands.
