"""Task worktrees: `sae start`, task discovery, backlog pickup, hooks off, setup source.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [TASK-WORKTREE], [BACKLOG-PICKUP], [GIT-HOOKS-OFF-FOR-SAE], [SETUP-SOURCE], [DONE-FOLDER],
[FLOW-PARALLEL-WORK], [EDGE-OLD-TASKS].
"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from saetest import SaeTestCase, Sandbox, config_for, covers_of, dispatch_workspace


def plan(sb: Sandbox, slug: str, jobs: list[tuple[str, str]], cwd: Path | None = None) -> str:
    """A task with approved plan; jobs are (ID, needs), all implementation."""
    task = sb.json("new", slug.title(), "--slug", slug, cwd=cwd)["task"]
    sb.approve_spec(slug, cwd=cwd)
    for job_id, needs in jobs:
        write_job_file(sb, cwd or sb.repo, task, job_id)
        sb.sae("job", "add", slug, job_id, "--kind", "implementation", *(["--needs", needs] if needs else []),
               cwd=cwd)
    sb.sae("approve", slug, "plan", cwd=cwd)
    return task


def write_job_file(sb: Sandbox, checkout: Path, task: str, job_id: str) -> None:
    folder = checkout / ".tasks" / task / "jobs"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{job_id}.md").write_text(f"---\nid: {job_id}\ncovers: {json.dumps(covers_of(folder.parent))}\nverify: []\n---\n\n# {job_id}\n\n## Objective\nDo one thing.\n")


def finish_job(sb: Sandbox, task: str, slug: str, job_id: str, file: str) -> Path:
    ws = dispatch_workspace(sb, task, job_id)
    sb.work(ws, file, f"{job_id}\n", f"{job_id}: work")
    sb.result(task, f"jobs/{job_id}.result.md", status="done", summary=job_id, validation="pass", changes="made")
    sb.sae("collect", slug, job_id)
    return ws


class StartTests(SaeTestCase):
    def test_start_leaves_the_home_checkout_alone_and_a_second_task_starts_at_once(self):
        """[FLOW-PARALLEL-WORK] up to "B runs in its worktree", then a commit on main meanwhile."""
        sb = self.sandbox()
        (sb.repo / "app.txt").write_text("scan in progress\n")   # tracked change
        (sb.repo / "scan.log").write_text("untracked\n")          # untracked, not ignored
        task = plan(sb, "task-b", [("ONE", ""), ("TWO", "ONE")])
        out = sb.sae("start", "task-b").stdout
        wt = sb.task_worktree(task)
        self.assertIn(f"Task worktree: {wt}", out)
        self.assertIn("Not part of the task (uncommitted in the home checkout): app.txt, scan.log",
                      " ".join(out.split()))
        self.assertEqual(wt, sb.worktrees / wt.parent.parent.name / task / "task")
        self.assertEqual(sb.git("branch", "--show-current"), "main")
        self.assertEqual(sb.git("branch", "--show-current", cwd=wt), f"task/{task}")
        self.assertEqual((sb.repo / "app.txt").read_text(), "scan in progress\n")
        self.assertEqual((wt / "app.txt").read_text(), "line one\n")
        self.assertFalse((sb.repo / ".tasks" / task).exists())        # the folder moved
        self.assertTrue((wt / ".tasks" / task / "state.json").exists())
        state = sb.state(task)["task"]
        self.assertEqual(state["home"], str(sb.repo))
        self.assertEqual(state["base"]["branch"], "main")
        self.assertEqual(state["layout"], "chain")
        # B runs in its worktree while the owner commits the scan on main
        ws = dispatch_workspace(sb, task, "ONE")
        self.assertEqual(ws, wt)
        sb.git("add", "app.txt", "scan.log")
        sb.git("commit", "-q", "-m", "scan results")
        sb.work(ws, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="one", validation="pass", changes="made")
        sb.sae("collect", "task-b", "ONE")
        self.assertEqual(sb.git("log", "--format=%s", "-1", f"task/{task}"), "ONE: work")
        self.assertEqual(sb.git("log", "--format=%s", "-1", "main"), "scan results")
        self.assertEqual(sb.state(task)["jobs"]["ONE"]["status"], "done")
        # a second task starts from the same home checkout at once
        second = plan(sb, "task-c", [("SOLO", "")])
        sb.sae("start", "task-c")
        wt2 = sb.task_worktree(second)
        self.assertNotEqual(wt2, wt)
        self.assertEqual(wt2.parent.parent, wt.parent.parent)          # one cache folder per repository
        self.assertEqual(sb.git("branch", "--show-current"), "main")
        self.assertEqual(sb.git("log", "--format=%s", "-2", f"task/{second}").splitlines(),
                         ["scan results", "init"])                     # builds on the home checkout's HEAD

    def test_status_from_home_checkout_task_worktree_and_job_worktree(self):
        sb = self.sandbox()
        task = plan(sb, "where", [("LEFT", ""), ("RIGHT", "")])
        sb.sae("start", "where")
        wt = sb.task_worktree(task)
        ws = dispatch_workspace(sb, task, "LEFT")
        self.assertEqual(ws.parent, wt.parent)
        for cwd in (sb.repo, wt, ws):
            data = sb.json("status", "where", cwd=cwd)
            self.assertEqual(data["phase"], "executing")
            self.assertEqual(data["worktree"], str(wt))
            listing = sb.json("status", cwd=cwd)
            self.assertEqual([t["id"] for t in listing["tasks"]], [task])
            self.assertEqual(listing["tasks"][0]["location"], str(wt))
        self.assertIn(f"Task worktree: {wt}", sb.sae("status", "where").stdout)
        # writing commands work from every checkout too
        sb.sae("log", "where", "note", "from the job worktree", cwd=ws)
        self.assertTrue(any(e.get("text") == "from the job worktree" for e in sb.events(task)))
        self.assertFalse((sb.repo / ".tasks" / task).exists())

    def test_resume_records_the_harness_and_keeps_the_worktree(self):
        sb = self.sandbox()
        task = plan(sb, "again", [("ONE", "")])
        sb.sae("start", "again")
        wt = sb.task_worktree(task)
        out = sb.sae("start", "again", "--harness", "codex").stdout
        self.assertIn(f"Task worktree: {wt}", out)
        self.assertEqual(sb.state(task)["task"]["orchestrator_harness"], "codex")
        self.assertEqual(sb.task_worktree(task), wt)

    def test_existing_task_branch_is_refused_without_changes(self):
        sb = self.sandbox()
        task = plan(sb, "taken", [("ONE", "")])
        sb.git("branch", f"task/{task}")
        proc = sb.sae("start", "taken", code=4)
        self.assertIn("exists already", proc.stderr)
        self.assertEqual(sb.state(task)["task"]["phase"], "planning")
        self.assertEqual(list(sb.worktrees.iterdir()), [])


class BacklogPickupTests(SaeTestCase):
    def committed_item(self, sb: Sandbox) -> Path:
        item = Path(sb.json("new", "Labels", "--backlog")["file"])
        sb.git("add", ".tasks/backlog")
        sb.git("commit", "-q", "-m", "backlog")
        return item

    def test_pilot_project_failure_task_created_in_one_checkout_started_from_another(self):
        """FORENSICS §4: created with --from in SP, folder moved to a detached checkout SPF of main,
        sae start there. It failed with "nothing added to commit" and left the branch checked out."""
        sb = self.sandbox()
        item = self.committed_item(sb)
        rel_item = str(item.relative_to(sb.repo))
        task = sb.json("new", "Labels", "--from", rel_item)["task"]
        self.assertTrue(item.exists())
        sb.approve_spec(task)
        write_job_file(sb, sb.repo, task, "WORK")
        sb.sae("job", "add", task, "WORK", "--kind", "implementation")
        sb.sae("approve", task, "plan")
        spf = self.tmp / "spf"
        sb.git("worktree", "add", "--detach", str(spf), "main")
        shutil.move(str(sb.repo / ".tasks" / task), str(spf / ".tasks" / task))
        sb.sae("start", task, cwd=spf)
        wt = sb.task_worktree(task)
        self.assertEqual(sb.git("log", "--format=%s", f"main..task/{task}"), f"{task}: picked up from backlog")
        self.assertNotIn(rel_item, sb.git("ls-tree", "-r", "--name-only", f"task/{task}"))
        self.assertIn(rel_item, sb.git("ls-tree", "-r", "--name-only", "main"))   # base branch untouched
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=no", cwd=spf), "")
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=no"), "")
        self.assertEqual(sb.git("rev-parse", "--abbrev-ref", "HEAD", cwd=spf), "HEAD")  # still detached
        state = sb.state(task)["task"]
        self.assertEqual(state["base"]["branch"], None)
        self.assertEqual(state["home"], str(sb.repo))
        self.assertEqual(state["phase"], "executing")
        self.assertTrue((wt / ".tasks" / task).is_dir())
        # the home checkout marks the item as picked up
        backlog = sb.json("status")["backlog"]
        self.assertEqual(backlog[0]["picked_up_by"], task)

    def test_start_from_another_checkout_finds_the_task_in_its_home(self):
        sb = self.sandbox()
        item = self.committed_item(sb)
        task = sb.json("new", "Labels", "--from", str(item.relative_to(sb.repo)))["task"]
        sb.approve_spec(task)
        write_job_file(sb, sb.repo, task, "WORK")
        sb.sae("job", "add", task, "WORK", "--kind", "implementation")
        sb.sae("approve", task, "plan")
        other = self.tmp / "other"
        sb.git("worktree", "add", "-q", "-b", "side", str(other))
        sb.sae("start", task, cwd=other)
        self.assertEqual(sb.git("log", "--format=%s", "-1", f"task/{task}"), f"{task}: picked up from backlog")
        self.assertEqual(sb.git("branch", "--show-current", cwd=other), "side")
        self.assertEqual(sb.git("branch", "--show-current"), "main")

    def test_forced_setup_failure_leaves_the_repository_as_it_was(self):
        sb = self.sandbox()
        repo_files = sb.repo / ".tasks" / "repo"
        repo_files.mkdir(parents=True)
        (repo_files / "setup.sh").write_text("echo broken >&2\nexit 3\n")
        item = Path(sb.json("new", "Never committed", "--backlog")["file"])   # an untracked item
        task = sb.json("new", "Pickup", "--from", str(item.relative_to(sb.repo)))["task"]
        source_finding = sb.repo / ".tasks" / "findings" / "2026-10-10-1200--from-planning.md"
        source_finding.parent.mkdir(parents=True)
        source_finding.write_text(f"---\nsource: {task}/PLAN\n---\n\n# From planning\n")
        sb.approve_spec(task)
        write_job_file(sb, sb.repo, task, "WORK")
        sb.sae("job", "add", task, "WORK", "--kind", "implementation")
        sb.sae("approve", task, "plan")
        before_state = sb.state(task)
        before_events = (sb.task_dir(task) / "events.jsonl").read_text()
        before_status = sb.git("status", "--porcelain", "--untracked-files=all")
        proc = sb.sae("start", task, code=4)
        self.assertIn("Starting was undone", " ".join(proc.stderr.split()))
        self.assertIn("task.setup.log", proc.stderr)
        self.assertEqual(sb.git("branch", "--list", "task/*"), "")
        self.assertEqual(len(sb.git("worktree", "list").splitlines()), 1)
        self.assertEqual(list(sb.worktrees.iterdir()), [])
        self.assertTrue(item.exists() and source_finding.exists())
        state = sb.state(task)
        self.assertEqual(state["task"]["phase"], "planning")
        self.assertEqual(state["task"]["approvals"], before_state["task"]["approvals"])
        self.assertEqual((sb.task_dir(task) / "events.jsonl").read_text(), before_events)
        self.assertIn("broken", (sb.task_dir(task) / "jobs" / "task.setup.log").read_text())
        after_status = [l for l in sb.git("status", "--porcelain", "--untracked-files=all").splitlines()
                        if "task.setup.log" not in l]
        self.assertEqual(after_status, before_status.splitlines())
        # a second run works once setup is fixed
        (repo_files / "setup.sh").write_text("echo ok > setup-marker\n")
        sb.sae("start", task)
        wt = sb.task_worktree(task)
        self.assertTrue((wt / "setup-marker").exists())
        self.assertFalse(item.exists())
        self.assertFalse((wt / item.relative_to(sb.repo)).exists())    # deleted after the start succeeded
        self.assertTrue((wt / ".tasks" / "findings" / source_finding.name).exists())
        self.assertFalse(source_finding.exists())
        self.assertTrue((wt / ".tasks" / "repo" / "setup.sh").exists())
        self.assertTrue((sb.repo / ".tasks" / "repo" / "setup.sh").exists())   # kept for the next task
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=all", "--", ".tasks/.lock",
                                f".tasks/{task}/.lock", cwd=wt), "")


    def assert_start_undone(self, sb: Sandbox, task: str, before_state: dict, before_events: str,
                            moved: list[Path]) -> None:
        self.assertEqual(sb.git("branch", "--list", "task/*"), "")
        self.assertEqual(len(sb.git("worktree", "list").splitlines()), 1)
        self.assertEqual(list(sb.worktrees.iterdir()), [])
        self.assertTrue(all(path.exists() for path in moved))
        self.assertEqual(sb.task_dir(task), sb.repo / ".tasks" / task)
        self.assertEqual(sb.state(task), before_state)
        self.assertEqual((sb.task_dir(task) / "events.jsonl").read_text(), before_events)

    def test_model_resolution_fails_before_any_change(self):
        """REVIEW-SAE-TASK-WORKTREE 1: a Claude-only config and --harness codex."""
        sb = self.sandbox()
        sb.config.write_text(json.dumps(config_for(sb.worktrees, codex=False)))
        task = plan(sb, "routed", [("ONE", "")])
        before_state = sb.state(task)
        before_events = (sb.task_dir(task) / "events.jsonl").read_text()
        sb.sae("start", task, "--harness", "codex", code=2)
        self.assert_start_undone(sb, task, before_state, before_events, [])
        sb.sae("start", task)
        self.assertEqual(sb.state(task)["task"]["phase"], "executing")

    def test_failure_after_setup_until_the_state_is_saved_is_undone(self):
        """REVIEW-SAE-TASK-WORKTREE 1: setup passes, saving the events fails; a retry succeeds."""
        sb = self.sandbox()
        repo_files = sb.repo / ".tasks" / "repo"
        repo_files.mkdir(parents=True)
        (repo_files / "setup.sh").write_text('chmod a-w "$SAE_WORKTREE/.tasks/$SAE_TASK/events.jsonl"\n')
        item = Path(sb.json("new", "Never committed", "--backlog")["file"])
        task = sb.json("new", "Pickup", "--from", str(item.relative_to(sb.repo)))["task"]
        sb.approve_spec(task)
        write_job_file(sb, sb.repo, task, "WORK")
        sb.sae("job", "add", task, "WORK", "--kind", "implementation")
        sb.sae("approve", task, "plan")
        before_state = sb.state(task)
        before_events = (sb.task_dir(task) / "events.jsonl").read_text()
        proc = sb.sae("start", task, code=1)
        self.assertIn("PermissionError", proc.stderr)
        self.assert_start_undone(sb, task, before_state, before_events, [item])
        (repo_files / "setup.sh").write_text("true\n")
        sb.sae("start", task)
        wt = sb.task_worktree(task)
        self.assertEqual(sb.state(task)["task"]["phase"], "executing")
        self.assertFalse(item.exists())
        self.assertFalse((wt / item.relative_to(sb.repo)).exists())
        self.assertEqual(sum(e["type"] == "execution.started" for e in sb.events(task)), 1)


class HooksOffTests(SaeTestCase):
    def test_post_merge_hook_that_rewrites_a_tracked_file_does_not_block_job_merges(self):
        sb = self.sandbox()
        for name in ("post-merge", "post-checkout", "post-commit"):
            sb.hook(name, 'echo "rewritten by a hook" > app.txt')
        task = plan(sb, "hooked", [("A", ""), ("B", ""), ("C", "")])
        sb.sae("start", "hooked")
        wt = sb.task_worktree(task)
        self.assertEqual((wt / "app.txt").read_text(), "line one\n")   # no post-checkout for sae's worktree add
        for job_id in ("A", "B", "C"):
            ws = dispatch_workspace(sb, task, job_id)
            self.assertEqual((ws / "app.txt").read_text(), "line one\n")
            (ws / f"{job_id}.txt").write_text(job_id)
            sb.git("add", f"{job_id}.txt", cwd=ws)
            sb.git("commit", "-q", "-m", f"{job_id}: work", cwd=ws)   # the worker's commit keeps its hooks
            self.assertEqual((ws / "app.txt").read_text(), "rewritten by a hook\n")
            (ws / "app.txt").write_text("line one\n")  # the worker cleans up after its own hook
            sb.result(task, f"jobs/{job_id}.result.md", status="done", summary=job_id, validation="pass",
                      changes="made")
        for job_id in ("A", "B", "C"):
            sb.sae("collect", "hooked", job_id)
        jobs = sb.state(task)["jobs"]
        self.assertTrue(all(jobs[j]["merged"] for j in ("A", "B", "C")))
        self.assertEqual((wt / "app.txt").read_text(), "line one\n")
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=no", cwd=wt), "")
        # the owner's own merge still runs the hook
        sb.git("merge", "-q", "--no-ff", "-m", "owner merge", f"task/{task}")
        self.assertEqual((sb.repo / "app.txt").read_text(), "rewritten by a hook\n")

    def test_doctor_repo_points_to_setup_sh_when_hooks_exist(self):
        sb = self.sandbox()
        sb.hook("post-merge", "true")
        out = sb.sae("doctor", "--repo", code=1).stdout
        self.assertIn(f"git hooks found: core.hooksPath = {sb.hooks}", " ".join(out.split()))
        self.assertIn(".tasks/repo/setup.sh", out)

    def test_doctor_repo_reads_the_hooks_folder_when_no_hooks_path_is_set(self):
        """REVIEW-SAE-TASK-WORKTREE 3: doctor reads the real configuration, not sae's override."""
        sb = self.sandbox()
        empty = self.tmp / "empty.gitconfig"
        empty.write_text("")
        sb.env["GIT_CONFIG_GLOBAL"] = str(empty)   # the owner's global hooks path stays out
        sb.git("config", "--unset", "core.hooksPath")
        out = sb.sae("doctor", "--repo", code=1).stdout
        self.assertNotIn("git hooks found", out)
        hooks = sb.repo / ".git" / "hooks"
        hooks.mkdir(exist_ok=True)
        (hooks / "post-merge").write_text("#!/bin/sh\ntrue\n")
        out = sb.sae("doctor", "--repo", code=1).stdout
        self.assertIn(f"git hooks found: {hooks}: post-merge", " ".join(out.split()))


class SetupSourceTests(SaeTestCase):
    def test_setup_files_come_from_the_main_worktree(self):
        sb = self.sandbox()
        (sb.repo / ".gitignore").write_text(".env\nnode_modules/\n")
        sb.git("add", ".gitignore")
        sb.git("commit", "-q", "-m", "ignore")
        (sb.repo / ".env").write_text("FROM=main\n")
        (sb.repo / "node_modules" / "pkg").mkdir(parents=True)
        (sb.repo / "node_modules" / "pkg" / "index.js").write_text("main\n")
        second = self.tmp / "second"
        sb.git("worktree", "add", "-q", "-b", "side", str(second))
        (second / ".tasks" / "repo").mkdir(parents=True)
        (second / ".tasks" / "repo" / "worktreeinclude").write_text(".env\nnode_modules/\nlocal.cfg\nnowhere/\n")
        (second / ".gitignore").write_text(".env\nnode_modules/\nlocal.cfg\n")
        (second / "local.cfg").write_text("only here\n")   # missing in the main worktree
        sb.git("add", ".gitignore", cwd=second)
        sb.git("commit", "-q", "-m", "ignore local.cfg", cwd=second)
        task = plan(sb, "from-side", [("LEFT", ""), ("RIGHT", "")], cwd=second)
        proc = sb.sae("start", "from-side", cwd=second)
        wt = sb.task_worktree(task)
        self.assertEqual((wt / ".env").read_text(), "FROM=main\n")
        self.assertEqual((wt / "node_modules" / "pkg" / "index.js").read_text(), "main\n")
        self.assertEqual((wt / "local.cfg").read_text(), "only here\n")
        self.assertIn("'nowhere/'", proc.stdout + proc.stderr)
        self.assertNotIn("'local.cfg'", proc.stdout + proc.stderr)
        self.assertIn("nowhere/", (wt / ".tasks" / task / "jobs" / "task.setup.log").read_text())
        ws = dispatch_workspace(sb, task, "LEFT")
        self.assertEqual((ws / ".env").read_text(), "FROM=main\n")
        self.assertTrue((ws / "node_modules" / "pkg" / "index.js").exists())

    def test_untracked_root_worktreeinclude_serves_the_task_and_its_jobs(self):
        """REVIEW-SAE-TASK-WORKTREE 2: the list is copied like the .tasks/repo/ files."""
        sb = self.sandbox()
        (sb.repo / ".gitignore").write_text(".env\n")
        sb.git("add", ".gitignore")
        sb.git("commit", "-q", "-m", "ignore")
        (sb.repo / ".env").write_text("SECRET=1\n")
        (sb.repo / ".worktreeinclude").write_text(".env\nnowhere/\n")   # untracked
        task = plan(sb, "rooted", [("LEFT", ""), ("RIGHT", "")])
        proc = sb.sae("start", "rooted")
        wt = sb.task_worktree(task)
        self.assertEqual((wt / ".env").read_text(), "SECRET=1\n")
        self.assertIn("'nowhere/'", proc.stdout + proc.stderr)
        self.assertTrue((sb.repo / ".worktreeinclude").exists())         # kept for the next task
        self.assertTrue((wt / ".worktreeinclude").exists())
        ws = dispatch_workspace(sb, task, "LEFT")
        self.assertNotEqual(ws, wt)
        self.assertEqual((ws / ".env").read_text(), "SECRET=1\n")


class DiscoveryTests(SaeTestCase):
    def test_task_in_done_folder_is_found(self):
        sb = self.sandbox()
        task = sb.new_task("Old one", "old-one")
        done = sb.repo / ".tasks" / "done"
        done.mkdir()
        shutil.move(str(sb.repo / ".tasks" / task), str(done / task))
        self.assertEqual(sb.json("status", "old-one")["task"], task)
        self.assertEqual([t["id"] for t in sb.json("status")["tasks"]], [task])

    def test_live_copy_wins_over_a_committed_record(self):
        sb = self.sandbox()
        task = plan(sb, "twice", [("ONE", "")])
        sb.sae("start", "twice")
        wt = sb.task_worktree(task)
        stale = sb.repo / ".tasks" / task
        shutil.copytree(wt / ".tasks" / task, stale)
        state = json.loads((stale / "state.json").read_text())
        state["task"]["phase"] = "done"
        state["task"]["last_change"] = "2099-01-01T00:00:00+00:00"   # newer, but committed
        (stale / "state.json").write_text(json.dumps(state))
        sb.git("add", "-f", f".tasks/{task}/state.json")
        sb.git("commit", "-q", "-m", "stale record")
        self.assertEqual(sb.json("status", "twice")["phase"], "executing")

    def test_old_task_executing_in_place_continues_in_place(self):
        """[EDGE-OLD-TASKS]: started by the old sae, no task worktree in its state."""
        sb = self.sandbox()
        task = plan(sb, "legacy", [("ONE", "")])
        sb.git("switch", "-q", "-c", f"task/{task}")
        state = sb.state(task)
        state["task"].update({"phase": "executing", "git": True, "layout": "chain", "branch": f"task/{task}",
                              "base": {"branch": "main", "commit": sb.git("rev-parse", "--short", "main")}})
        (sb.task_dir(task) / "state.json").write_text(json.dumps(state))
        out = sb.sae("start", "legacy").stdout
        self.assertIn("Executes in place", out)
        ws = dispatch_workspace(sb, task, "ONE")
        self.assertEqual(ws, sb.repo)
        self.assertEqual(list(sb.worktrees.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
