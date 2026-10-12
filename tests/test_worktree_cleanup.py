"""Worktree cleanup and finished tasks: removal with preservation, the sweep of merged task
worktrees, `sae doctor --discard`, `.tasks/done/`, no writes into finished tasks.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [WORKTREE-CLEANUP], [TASK-WORKTREE-LIFECYCLE], [DONE-FOLDER], [FINISHED-TASKS-READ-ONLY],
[DECISION-DRAFTS] (finish commits drafts), [FLOW-PARALLEL-WORK], [RULE-BASE-BRANCH], [EDGE-OLD-TASKS].
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from saetest import SAE, SCRIPTS, SaeTestCase, Sandbox, dispatch_workspace


def plan(sb: Sandbox, slug: str, jobs: list[str]) -> str:
    """A task with an approved plan of independent implementation jobs (worktrees layout when
    there are two or more)."""
    task = sb.new_task(slug.title(), slug)
    for job_id in jobs:
        sb.sae("job", "add", slug, job_id, "--kind", "implementation")
        sb.job_file(task, job_id)
    sb.approve_plan(slug)
    return task


def done_job(sb: Sandbox, task: str, slug: str, job_id: str, status: str = "done") -> Path:
    ws = dispatch_workspace(sb, task, job_id)
    sb.work(ws, f"{job_id.lower()}.txt", f"{job_id}\n", f"{job_id}: work")
    sb.result(task, f"jobs/{job_id}.result.md", status=status, summary=job_id, validation="pass", changes="made")
    sb.sae("collect", slug, job_id)
    return ws


def doctor(sb: Sandbox, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """`sae doctor`; its exit code depends on the machine (Python version, harness CLIs)."""
    return subprocess.run([sys.executable, str(SAE), "doctor", *args], cwd=cwd or sb.repo, capture_output=True,
                          text=True, env=sb.env)


def finished(sb: Sandbox, slug: str, jobs=("LEFT", "RIGHT")) -> tuple[str, Path]:
    task = plan(sb, slug, list(jobs))
    sb.sae("start", slug)
    for job_id in jobs:
        done_job(sb, task, slug, job_id)
    out = sb.sae("finish", slug).stdout
    # the first task of a repository: `sae new` left .tasks/.gitignore and .gitattributes untracked at home;
    # finish removes them, as the task record commits them unchanged ([OWNER-MERGE-FIRST-TASK])
    assert "Removed untracked copies" in out and ".tasks/.gitignore" in out, out
    return task, sb.task_worktree(task)


def owner_merges(sb: Sandbox, task: str) -> None:
    """The owner merges the task branch into main, with no manual step first."""
    sb.git("merge", "-q", "--no-ff", "-m", "merge", f"task/{task}")


class JobWorktreeTests(SaeTestCase):
    def test_hook_that_rewrites_a_tracked_file_on_checkout_does_not_keep_the_worktree(self):
        """[WORKTREE-CLEANUP]: the hook does not run for sae's worktree add, so the merged job's
        worktree is clean and goes."""
        sb = self.sandbox()
        sb.hook("post-checkout", 'echo "rewritten by a hook" > app.txt')
        task = plan(sb, "hooked", ["LEFT", "RIGHT"])
        sb.sae("start", "hooked")
        ws = dispatch_workspace(sb, task, "LEFT")
        self.assertEqual((ws / "app.txt").read_text(), "line one\n")
        sb.work(ws, "left.txt", "left\n", "LEFT: work")
        sb.result(task, "jobs/LEFT.result.md", status="done", summary="l", validation="pass", changes="made")
        sb.sae("collect", "hooked", "LEFT")
        self.assertTrue(sb.state(task)["jobs"]["LEFT"]["merged"])
        self.assertFalse(ws.exists())
        self.assertNotIn(str(ws), sb.git("worktree", "list"))

    def test_file_created_after_the_status_check_survives_cleanup(self):
        """[WORKTREE-CLEANUP]: cleanup deletes only the copies it verified in its one status
        read; a file that appears after that read keeps the worktree."""
        sb = self.sandbox()
        wt = sb.tmp / "worktrees" / "probe"
        sb.git("worktree", "add", "-q", "-b", "probe", str(wt))
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib import workspaces
        finally:
            sys.path.remove(str(SCRIPTS))
        real_run = workspaces.run

        def run_then_write(cmd, cwd, *args, **kwargs):
            proc = real_run(cmd, cwd, *args, **kwargs)
            if cmd[:2] == ["git", "status"]:
                (wt / "scratch.txt").write_text("written meanwhile\n")
            return proc

        with mock.patch.object(workspaces, "run", side_effect=run_then_write):
            reason = workspaces.remove_clean_worktree(sb.repo, wt)
        self.assertIsNotNone(reason)
        self.assertEqual((wt / "scratch.txt").read_text(), "written meanwhile\n")

    def test_uncommitted_work_survives_finish_and_doctor_until_discard(self):
        sb = self.sandbox()
        task = plan(sb, "careful", ["LEFT", "RIGHT"])
        sb.sae("start", "careful")
        done_job(sb, task, "careful", "LEFT")
        ws = dispatch_workspace(sb, task, "RIGHT")
        sb.work(ws, "right.txt", "right\n", "RIGHT: work")
        (ws / "notes.txt").write_text("the worker's notes\n")       # untracked, not ignored
        sb.result(task, "jobs/RIGHT.result.md", status="done", summary="r", validation="pass", changes="made")
        proc = sb.sae("collect", "careful", "RIGHT")
        self.assertTrue(sb.state(task)["jobs"]["RIGHT"]["merged"])
        self.assertIn("it holds uncommitted work: notes.txt", proc.stderr)
        out = sb.sae("finish", "careful").stdout
        self.assertIn(f"## Kept worktrees\n- {ws}: it holds uncommitted work: notes.txt", out)
        self.assertTrue((ws / "notes.txt").exists())
        kept = [e for e in sb.events(task) if e["type"] == "worktree.kept"]
        self.assertTrue(kept and kept[-1]["path"] == str(ws))
        report = doctor(sb).stdout
        self.assertIn(f"! worktree {ws}", report)
        self.assertIn("notes.txt", report)
        self.assertIn(f"sae doctor --discard {ws}", report)
        self.assertTrue((ws / "notes.txt").exists())                  # doctor alone removes nothing
        out = doctor(sb, "--discard", str(ws)).stdout
        self.assertIn("Lost: notes.txt.", out)
        self.assertIn(f"Branch job/{task}/RIGHT stays.", out)
        self.assertFalse(ws.exists())
        self.assertTrue(sb.git("branch", "--list", f"job/{task}/RIGHT"))

    def test_discard_refuses_the_worktree_of_a_running_task_and_foreign_paths(self):
        sb = self.sandbox()
        task = plan(sb, "busy", ["ONE"])
        sb.sae("start", "busy")
        wt = sb.task_worktree(task)
        proc = doctor(sb, "--discard", str(wt))
        self.assertEqual(proc.returncode, 4)
        self.assertIn("sae abandon", proc.stderr)
        proc = doctor(sb, "--discard", str(sb.repo))
        self.assertEqual(proc.returncode, 4)
        self.assertTrue((wt / ".tasks" / task / "state.json").exists())
        self.assertTrue((sb.repo / "README.md").exists())

    def test_doctor_lists_a_live_task_worktree_without_discard(self):
        sb = self.sandbox()
        task = plan(sb, "alive", ["ONE"])
        sb.sae("start", "alive")
        wt = sb.task_worktree(task)
        report = doctor(sb).stdout
        self.assertIn(f"✓ worktree {wt}", report)
        self.assertIn("task worktree of the live task (executing)", report)
        self.assertNotIn(f".tasks/{task}/", report)                  # its own live files are no leftover work
        self.assertNotIn(f"--discard {wt}", report)
        (wt / "stray.txt").write_text("not saved anywhere\n")
        report = doctor(sb).stdout
        self.assertIn("it holds uncommitted work: stray.txt", " ".join(report.split()))  # other work is still named
        self.assertNotIn(f"--discard {wt}", report)

    def test_doctor_protects_running_jobs_but_offers_discard_after_failure(self):
        sb = self.sandbox()
        task = plan(sb, "active-worker", ["SAE-WORKTREE-CLEANUP-FIX-1", "OTHER"])
        sb.sae("start", "active-worker")
        job = "SAE-WORKTREE-CLEANUP-FIX-1"
        ws = dispatch_workspace(sb, task, job)
        for dirty in (False, True):
            if dirty:
                (ws / "notes.txt").write_text("uncommitted worker notes\n")
                (ws / "app.txt").write_text("worker's tracked edit\n")
            for checkout in (sb.repo, sb.task_worktree(task), ws):
                with self.subTest(dirty=dirty, checkout=checkout):
                    report = doctor(sb, cwd=checkout).stdout
                    self.assertIn(f"✓ worktree {ws}", report)
                    self.assertIn(f"job running: {job}", " ".join(report.split()))
                    self.assertNotIn(f"--discard {ws}", report)
                    proc = doctor(sb, "--discard", str(ws), cwd=checkout)
                    self.assertEqual(proc.returncode, 4, proc.stderr)
                    self.assertIn("job running", " ".join(proc.stderr.split()))
                    self.assertTrue(ws.exists())
            if dirty:
                self.assertEqual((ws / "notes.txt").read_text(), "uncommitted worker notes\n")
                self.assertEqual((ws / "app.txt").read_text(), "worker's tracked edit\n")
        sb.result(task, f"jobs/{job}.result.md", status="failed", summary="worker failed",
                  validation="fail", changes="none")
        sb.sae("collect", "active-worker", job)
        report = doctor(sb).stdout
        self.assertIn(f"! worktree {ws}", report)
        self.assertIn("failed: kept for inspection", " ".join(report.split()))
        self.assertIn(f"sae doctor --discard {ws}", report)
        proc = doctor(sb, "--discard", str(ws))
        self.assertIn("Lost: app.txt, notes.txt.", " ".join(proc.stdout.split()))
        self.assertFalse(ws.exists())
        self.assertTrue(sb.git("branch", "--list", f"job/{task}/{job}"))

    def test_doctor_protects_a_running_fix_in_its_targets_worktree(self):
        sb = self.sandbox(points=["selected-jobs"])
        task = plan(sb, "active-fix", ["CORE", "OTHER"])
        sb.sae("job", "edit", "active-fix", "CORE", "--review")
        sb.sae("start", "active-fix")
        ws = done_job(sb, task, "active-fix", "CORE")
        sb.sae("dispatch", "active-fix", "REVIEW-CORE")
        sb.result(task, "reviews/REVIEW-CORE.md", target="CORE", verdict="changes-required")
        sb.sae("collect", "active-fix", "REVIEW-CORE")
        sb.sae("job", "add", "active-fix", "CORE-FIX-1", "--kind", "implementation",
               "--fix-of", "CORE", "--reason", "repair review findings")
        sb.job_file(task, "CORE-FIX-1")
        self.assertEqual(dispatch_workspace(sb, task, "CORE-FIX-1"), ws)
        (ws / "notes.txt").write_text("fix worker's notes\n")
        report = doctor(sb).stdout
        self.assertIn(f"✓ worktree {ws}", report)
        self.assertIn("job running: CORE-FIX-1", " ".join(report.split()))
        self.assertNotIn(f"--discard {ws}", report)
        proc = doctor(sb, "--discard", str(ws))
        self.assertEqual(proc.returncode, 4, proc.stderr)
        self.assertIn("job running", " ".join(proc.stderr.split()))
        self.assertEqual((ws / "notes.txt").read_text(), "fix worker's notes\n")

    def test_doctor_accepts_python_3_9(self):
        """07-cli-spec §1: Python 3.9+; doctor's own check must not demand more."""
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib import doctor as doctor_module
        finally:
            sys.path.remove(str(SCRIPTS))
        with mock.patch.object(doctor_module.sys, "version_info", (3, 9, 6)), \
                mock.patch.object(doctor_module.platform, "python_version", return_value="3.9.6"), \
                mock.patch.object(doctor_module.shutil, "which", return_value=None), \
                mock.patch.object(doctor_module, "detect_harness", return_value="claude"):
            checks = []
            with mock.patch.object(doctor_module, "emit", side_effect=lambda a, t, d: checks.extend(d["checks"])), \
                    mock.patch.object(doctor_module, "doctor_worktrees", return_value=[]), \
                    mock.patch.object(doctor_module, "load_config", side_effect=doctor_module.SaeError(2, "x")):
                doctor_module.cmd_doctor(mock.Mock(repo=False, discard=None))
        python = next(c for c in checks if c["text"].startswith("Python"))
        self.assertTrue(python["ok"], python)

    def test_after_finish_the_cache_holds_only_the_task_worktree(self):
        sb = self.sandbox()
        task = plan(sb, "tidy", ["LEFT", "RIGHT"])
        sb.sae("start", "tidy")
        for job_id in ("LEFT", "RIGHT"):
            done_job(sb, task, "tidy", job_id)
        out = sb.sae("finish", "tidy").stdout
        wt = sb.task_worktree(task)
        self.assertIn(f"Task worktree, test the result here:\n  {wt}\n"
                      f"After you merge task/{task}, sae removes the task worktree.", out)
        self.assertEqual([p.name for p in wt.parent.iterdir()], ["task"])
        self.assertEqual([p.name for p in wt.parent.parent.iterdir()], [task])
        self.assertEqual(sb.git("branch", "--list", f"job/{task}/*"), "")

    def test_failed_job_worktree_is_kept_at_abandon_and_the_rest_goes(self):
        sb = self.sandbox()
        task = plan(sb, "dropped", ["LEFT", "RIGHT"])
        sb.sae("start", "dropped")
        wt = sb.task_worktree(task)
        ws_left = dispatch_workspace(sb, task, "LEFT")
        ws_right = dispatch_workspace(sb, task, "RIGHT")
        sb.work(ws_right, "right.txt", "r\n", "RIGHT: half done")
        sb.result(task, "jobs/RIGHT.result.md", status="failed", summary="gave up", validation="fail",
                  changes="made")
        sb.sae("collect", "dropped", "RIGHT")
        self.assertEqual(sb.state(task)["jobs"]["RIGHT"]["status"], "failed")
        out = sb.sae("abandon", "dropped", "--reason", "superseded").stdout
        self.assertIn(f"Moved the task folder back to {sb.repo / '.tasks' / task}.", out)
        self.assertIn(f"Worktree kept: {ws_right}: the job failed: kept for inspection", " ".join(out.split()))
        self.assertTrue((sb.repo / ".tasks" / task / "state.json").exists())   # back home, untracked
        self.assertEqual(sb.state(task)["task"]["phase"], "abandoned")
        self.assertFalse(ws_left.exists())
        self.assertFalse(wt.exists())
        self.assertTrue(ws_right.exists())
        for branch in (f"task/{task}", f"job/{task}/LEFT", f"job/{task}/RIGHT"):
            self.assertTrue(sb.git("branch", "--list", branch), branch)    # abandon keeps branches
        self.assertIn("job RIGHT failed: kept for inspection", doctor(sb).stdout)


class TaskWorktreeLifecycleTests(SaeTestCase):
    def test_flow_parallel_work_from_finish_to_the_removal_of_the_worktree(self):
        """[FLOW-PARALLEL-WORK]: B finishes → the owner tests in the task worktree → merges →
        sae removes the worktree and the merged branch."""
        sb = self.sandbox()
        task, wt = finished(sb, "flow-b")
        self.assertTrue(wt.exists())                                   # stays after finish
        self.assertEqual(sb.json("status", "flow-b")["phase"], "done")
        sb.sae("new", "Unrelated", "--slug", "unrelated")              # a writing command before the merge
        self.assertTrue(wt.exists())
        subprocess.run(["sh", "-c", "cat left.txt right.txt > /dev/null"], cwd=wt, check=True)  # the owner tests
        owner_merges(sb, task)
        report = doctor(sb).stdout
        self.assertIn(f"Removed the task worktree of {task} (task/{task} is merged into main) "
                      f"and deleted task/{task}.", " ".join(report.split()))
        self.assertFalse(wt.exists())
        self.assertEqual(list(sb.worktrees.iterdir()), [])             # empty cache folders go too
        self.assertEqual(sb.git("branch", "--list", f"task/{task}"), "")
        self.assertEqual(sb.json("status", "flow-b")["phase"], "done")   # found in main's .tasks/done/

    def test_any_later_writing_command_sweeps_but_read_only_ones_do_not(self):
        sb = self.sandbox()
        task, wt = finished(sb, "swept")
        owner_merges(sb, task)
        sb.sae("status", "swept")
        sb.sae("status")
        self.assertTrue(wt.exists())
        proc = sb.sae("new", "Next thing", "--slug", "next-thing")
        self.assertIn(f"Removed the task worktree of {task}", proc.stderr)
        self.assertFalse(wt.exists())

    def test_merged_task_with_the_owners_uncommitted_test_changes_stays_intact(self):
        sb = self.sandbox()
        task, wt = finished(sb, "tested")
        (wt / "app.txt").write_text("owner's test tweak\n")
        (wt / "scratch.txt").write_text("owner's notes\n")
        owner_merges(sb, task)
        report = doctor(sb).stdout
        self.assertIn(f"! worktree {wt}", report)
        self.assertIn("task finished and merged into main; it holds uncommitted work: app.txt, scratch.txt",
                      " ".join(report.split()))
        self.assertEqual((wt / "app.txt").read_text(), "owner's test tweak\n")
        self.assertTrue((wt / "scratch.txt").exists())
        self.assertTrue(sb.git("branch", "--list", f"task/{task}"))
        proc = sb.sae("new", "Later", "--slug", "later")
        self.assertIn("task worktree kept", proc.stderr)
        self.assertTrue(wt.exists())

    def test_unmerged_finished_task_is_listed_with_its_reason(self):
        sb = self.sandbox()
        task, wt = finished(sb, "waiting")
        report = doctor(sb).stdout
        self.assertIn(f"✓ worktree {wt}", report)
        self.assertIn(f"task finished; task/{task} is not merged into main yet", " ".join(report.split()))


class DoneFolderTests(SaeTestCase):
    def committed_finished_task(self, sb: Sandbox, slug: str, phase: str) -> str:
        task = sb.new_task(slug.title(), slug)
        path = sb.repo / ".tasks" / task / "state.json"
        state = json.loads(path.read_text())
        state["task"]["phase"] = phase
        path.write_text(json.dumps(state))
        sb.git("add", f".tasks/{task}", ".tasks/.gitignore", ".tasks/.gitattributes")
        sb.git("commit", "-q", "-m", f"record of {slug}")
        return task

    def test_earlier_finished_tasks_move_to_done_at_the_next_finish_and_main_stays(self):
        """[DONE-FOLDER] on the pilot-project case: three finished tasks at the top of .tasks/."""
        sb = self.sandbox()
        earlier = [self.committed_finished_task(sb, s, p)
                   for s, p in (("old-one", "done"), ("old-two", "done"), ("old-three", "abandoned"))]
        main_tree = sb.git("ls-tree", "-r", "--name-only", "main")
        main_head = sb.git("rev-parse", "main")
        task = plan(sb, "current", ["ONLY"])
        sb.sae("start", "current")
        wt = sb.task_worktree(task)
        draft = wt / ".tasks" / "adr" / "2026-10-10-keep-records.md"
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text(f"---\ntitle: Keep records\nstatus: proposed\nsource: {task}\n---\n\n# Keep records\n")
        done_job(sb, task, "current", "ONLY")
        out = sb.sae("finish", "current").stdout
        self.assertIn("with 3 earlier finished task(s) moved to .tasks/done/", " ".join(out.split()))
        tree = sb.git("ls-tree", "-r", "--name-only", f"task/{task}").splitlines()
        for other in earlier + [task]:
            self.assertIn(f".tasks/done/{other}/state.json", tree)
            self.assertNotIn(f".tasks/{other}/state.json", tree)
        self.assertIn(".tasks/adr/2026-10-10-keep-records.md", tree)
        self.assertEqual(sb.git("status", "--porcelain", "--", ".tasks", cwd=wt), "")
        self.assertEqual(sb.git("rev-parse", "main"), main_head)       # [RULE-BASE-BRANCH]
        self.assertEqual(sb.git("ls-tree", "-r", "--name-only", "main"), main_tree)
        self.assertEqual(sb.json("status", "current")["phase"], "done")
        self.assertEqual(sb.json("status", "old-one")["phase"], "done")

    def test_drafts_and_findings_made_during_execution_are_committed_by_finish(self):
        """INTEGRATION-REVIEW finding 4: created from the home checkout and from a job worktree."""
        sb = self.sandbox()
        task = plan(sb, "drafting", ["LEFT", "RIGHT"])
        sb.sae("start", "drafting")
        wt = sb.task_worktree(task)
        home_draft = Path(sb.json("adr", "new", "drafting", "Keep records at home", "--type", "architecture")["file"])
        ws = dispatch_workspace(sb, task, "LEFT")
        job_draft = Path(sb.json("adr", "new", "drafting", "Keep records in jobs", "--type", "business", cwd=ws)["file"])
        finding = Path(sb.json("finding", "new", "Slow lookup", "--type", "defect", "--confidence", "low",
                               "--body", "4 s", "--source", f"{task}/LEFT", cwd=ws)["file"])
        for path in (home_draft, job_draft, finding):
            self.assertEqual(path.parents[2], wt, path)
        self.assertFalse((sb.repo / ".tasks" / "adr").exists())
        sb.work(ws, "left.txt", "LEFT\n", "LEFT: work")
        sb.result(task, "jobs/LEFT.result.md", status="done", summary="LEFT", validation="pass", changes="made")
        sb.sae("collect", "drafting", "LEFT")
        done_job(sb, task, "drafting", "RIGHT")
        sb.sae("finish", "drafting")
        tree = sb.git("ls-tree", "-r", "--name-only", f"task/{task}").splitlines()
        for path in (home_draft, job_draft, finding):
            self.assertIn(path.relative_to(wt).as_posix(), tree)

    def set_phase(self, sb: Sandbox, task: str, phase: str) -> None:
        path = sb.task_dir(task) / "state.json"
        state = json.loads(path.read_text())
        state["task"]["phase"] = phase
        path.write_text(json.dumps(state))

    def test_untracked_abandoned_record_moves_to_done_and_live_tasks_stay(self):
        """[DONE-FOLDER]: `abandon` leaves records untracked in the home checkout; the next finish
        commits them in .tasks/done/ on the task branch. A live task stays where it is."""
        sb = self.sandbox()
        dropped = sb.new_task("Dropped", "dropped")
        self.set_phase(sb, dropped, "abandoned")
        live = sb.new_task("Live", "live-one")
        main_head = sb.git("rev-parse", "main")
        task = plan(sb, "current", ["ONLY"])
        sb.sae("start", "current")
        done_job(sb, task, "current", "ONLY")
        out = sb.sae("finish", "current").stdout
        self.assertIn("with 1 earlier finished task(s) moved to .tasks/done/", " ".join(out.split()))
        tree = sb.git("ls-tree", "-r", "--name-only", f"task/{task}").splitlines()
        self.assertIn(f".tasks/done/{dropped}/state.json", tree)
        self.assertNotIn(f".tasks/{live}/state.json", tree)
        self.assertFalse((sb.repo / ".tasks" / dropped).exists())
        self.assertTrue((sb.repo / ".tasks" / live / "state.json").exists())
        self.assertEqual(sb.git("rev-parse", "main"), main_head)
        self.assertEqual(sb.json("status", "dropped")["phase"], "abandoned")

    def test_old_task_executing_in_place_moves_to_done_at_finish(self):
        """[EDGE-OLD-TASKS]: started by the old sae, no task worktree."""
        sb = self.sandbox()
        task = plan(sb, "legacy", ["ONE"])
        sb.git("switch", "-q", "-c", f"task/{task}")
        state = sb.state(task)
        state["task"].update({"phase": "executing", "git": True, "layout": "chain", "branch": f"task/{task}",
                              "base": {"branch": "main", "commit": sb.git("rev-parse", "--short", "main")}})
        (sb.task_dir(task) / "state.json").write_text(json.dumps(state))
        ws = dispatch_workspace(sb, task, "ONE")
        sb.work(ws, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="one", validation="pass", changes="made")
        sb.sae("collect", "legacy", "ONE")
        sb.sae("finish", "legacy")
        self.assertFalse((sb.repo / ".tasks" / task).exists())
        self.assertIn(f".tasks/done/{task}/state.json",
                      sb.git("ls-tree", "-r", "--name-only", f"task/{task}").splitlines())
        self.assertEqual(sb.git("log", "--format=%s", "-1", "main"), "init")

    def test_finish_without_git_moves_the_folder_to_done(self):
        sb = self.sandbox(git=False)
        task = plan(sb, "plain", ["ONE"])
        sb.sae("start", "plain")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="one", validation="pass", changes="made")
        sb.sae("dispatch", "plain", "ONE")
        sb.sae("collect", "plain", "ONE")
        sb.sae("finish", "plain")
        self.assertTrue((sb.repo / ".tasks" / "done" / task / "state.json").exists())
        self.assertFalse((sb.repo / ".tasks" / task).exists())


    def test_finish_without_git_moves_earlier_finished_records_by_phase(self):
        sb = self.sandbox(git=False)
        dropped = sb.new_task("Dropped", "dropped")
        self.set_phase(sb, dropped, "abandoned")
        live = sb.new_task("Live", "live-one")
        task = plan(sb, "plain", ["ONE"])
        sb.sae("start", "plain")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="one", validation="pass", changes="made")
        sb.sae("dispatch", "plain", "ONE")
        sb.sae("collect", "plain", "ONE")
        sb.sae("finish", "plain")
        self.assertTrue((sb.repo / ".tasks" / "done" / dropped / "state.json").exists())
        self.assertFalse((sb.repo / ".tasks" / dropped).exists())
        self.assertTrue((sb.repo / ".tasks" / live / "state.json").exists())
        self.assertFalse((sb.repo / ".tasks" / "done" / live).exists())


class FinishedTasksReadOnlyTests(SaeTestCase):
    def test_backlog_item_with_a_finished_source_changes_nothing_else(self):
        sb = self.sandbox()
        task, _ = finished(sb, "closed")
        owner_merges(sb, task)
        doctor(sb)                                                     # sweep: the record now lives on main
        record = sb.repo / ".tasks" / "done" / task / "events.jsonl"
        before = record.read_text()
        self.assertEqual(sb.git("status", "--porcelain"), "")
        item = Path(sb.json("new", "Later idea", "--backlog", "--source", "closed")["file"])
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=all"),
                         f"?? {item.relative_to(sb.repo)}")
        self.assertTrue(item.read_text().startswith(f"---\nsource: {task}"))
        sb.json("finding", "new", "Odd thing", "--type", "friction", "--confidence", "low",
                "--source", f"closed/LEFT", "--body", "Seen after the merge.")
        self.assertEqual(record.read_text(), before)                  # no finding.created either

    def test_log_and_set_on_a_finished_task_are_refused(self):
        sb = self.sandbox()
        task, wt = finished(sb, "sealed")
        record = wt / ".tasks" / "done" / task
        before = {name: (record / name).read_text() for name in ("state.json", "events.jsonl", "settings.json")}
        proc = sb.sae("log", "sealed", "note", "late thought", code=1)
        self.assertIn("read-only", proc.stderr)
        proc = sb.sae("set", "sealed", "interaction=auto", code=1)
        self.assertIn("read-only", proc.stderr)
        self.assertEqual({name: (record / name).read_text() for name in before}, before)
        self.assertEqual(sb.json("status", "sealed")["phase"], "done")

    def test_backlog_item_of_an_executing_task_goes_to_its_task_worktree(self):
        sb = self.sandbox()
        task = plan(sb, "live", ["ONLY"])
        sb.sae("start", "live")
        wt = sb.task_worktree(task)
        item = Path(sb.json("new", "Deferred", "--backlog", "--source", "live")["file"])
        self.assertEqual(item.parent, wt / ".tasks" / "backlog")
        done_job(sb, task, "live", "ONLY")
        sb.sae("finish", "live")
        self.assertIn(str(item.relative_to(wt)), sb.git("ls-tree", "-r", "--name-only", f"task/{task}"))


if __name__ == "__main__":
    unittest.main()
