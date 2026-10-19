"""Tests of [RECORD-PRIVACY]: a committed task record holds no harness output log and no path into
the user's home folder; the readers of a finished record still find its worktree and home checkout.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
The sandbox's HOME is its temporary folder, so every path sae writes lies in the home folder.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import SCRIPTS, SaeTestCase, dispatch_workspace  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
from sae_lib import findings, lifecycle  # noqa: E402


class RecordPrivacyTests(SaeTestCase):
    def test_finish_commits_no_harness_log_and_no_home_path(self):
        sb = self.sandbox()
        sb.env["HOME"] = str(sb.tmp)
        task = sb.new_task("Privacy", "privacy")
        sb.sae("job", "add", "privacy", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        sb.approve_plan("privacy")
        sb.sae("start", "privacy")
        wt = sb.task_worktree(task)  # absolute while the task runs
        self.assertTrue(str(wt).startswith(str(sb.tmp) + "/"))
        ws = dispatch_workspace(sb, task, "ONE")
        sb.work(ws, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "privacy", "ONE")
        record = sb.task_dir(task)
        # logs left behind: an orchestrator's own Codex run, a review that was never collected
        (record / "jobs" / "ONE.codex.jsonl").write_text('{"type": "turn.completed"}\n')
        (record / "reviews").mkdir(exist_ok=True)
        (record / "reviews" / "REVIEW-X.claude.json").write_text("{}\n")
        # not logs: a same-named fixture elsewhere, and a script that must stay executable
        (record / "prototypes").mkdir()
        (record / "prototypes" / "fixture.claude.json").write_text("{}\n")
        script = record / "prototypes" / "run.sh"
        script.write_text(f"#!/bin/sh\ncd {sb.tmp}/repo\n")
        script.chmod(0o755)
        # a finding of the task, with an untracked copy in the home checkout
        finding = Path(sb.json("finding", "new", "Slow lookup", "--type", "defect", "--confidence", "low",
                               "--body", f"See {sb.tmp}/repo/app.txt.", "--source", f"{task}/ONE", cwd=wt)["file"])
        finding_rel = finding.relative_to(wt).as_posix()
        (sb.repo / finding_rel).parent.mkdir(parents=True, exist_ok=True)
        (sb.repo / finding_rel).write_text(finding.read_text())
        # a multiline note: events.jsonl holds a JSON `\n` right before the home path
        sb.sae("log", "privacy", "decision", f"See\n{sb.tmp}/repo/app.txt", "--class", "clear-choice")
        # repo config is not rewritten, so a home copy that differs only by the home folder stays
        (wt / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        (wt / ".tasks" / "repo" / "setup.sh").write_text('exec "~/bin/tool"\n')
        (sb.repo / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        (sb.repo / ".tasks" / "repo" / "setup.sh").write_text(f'exec "{sb.tmp}/bin/tool"\n')
        out = sb.sae("finish", "privacy").stdout
        tracked = sb.git("ls-files", f".tasks/done/{task}", cwd=wt).splitlines()
        self.assertIn(f".tasks/done/{task}/state.json", tracked)
        self.assertEqual([p for p in tracked if p.endswith((".codex.jsonl", ".claude.json"))],
                         [f".tasks/done/{task}/prototypes/fixture.claude.json"])
        self.assertIn("See ~/repo/app.txt.", sb.git("show", f"HEAD:{finding_rel}", cwd=wt))
        self.assertIn(finding_rel, out)  # the home copy differed only by the home folder: removed
        self.assertFalse((sb.repo / finding_rel).exists())
        self.assertIn("See\\n~/repo/app.txt", sb.git("show", f"HEAD:.tasks/done/{task}/events.jsonl", cwd=wt))
        self.assertIn("move these untracked files", out)
        self.assertEqual((sb.repo / ".tasks" / "repo" / "setup.sh").read_text(), f'exec "{sb.tmp}/bin/tool"\n')
        run_sh = f".tasks/done/{task}/prototypes/run.sh"
        self.assertEqual(sb.git("show", f"HEAD:{run_sh}", cwd=wt), "#!/bin/sh\ncd ~/repo")
        self.assertTrue(sb.git("ls-files", "-s", run_sh, cwd=wt).startswith("100755 "))
        self.assertEqual((wt / run_sh).stat().st_mode & 0o777, 0o755)
        grep = subprocess.run(["git", "grep", "-l", "-F", str(sb.tmp), "HEAD", "--", ".tasks"], cwd=wt,
                              capture_output=True, text=True, env=sb.env)
        self.assertEqual((grep.returncode, grep.stdout), (1, ""))  # 1: no match
        info = json.loads(sb.git("show", f"HEAD:.tasks/done/{task}/state.json", cwd=wt))["task"]
        self.assertEqual((info["home"], info["worktree"]), ("~/repo", "~/" + str(wt.relative_to(sb.tmp))))
        self.assertEqual(sb.git("status", "--porcelain", "--", ".tasks", cwd=wt), "")
        # readers expand `~`: the finished task's worktree counts, and the sweep removes it after the merge
        with mock.patch.dict(os.environ, {"HOME": str(sb.tmp)}):
            self.assertIn(wt, findings.task_worktrees(sb.repo))
        sb.sae("status", "privacy")
        (sb.repo / ".tasks" / "repo" / "setup.sh").unlink()  # the owner moves it aside, as finish said
        sb.git("merge", "-q", "--no-ff", "-m", "merge", f"task/{task}")
        proc = sb.sae("new", "Next thing", "--slug", "next-thing")
        self.assertIn(f"Removed the task worktree of {task}", proc.stderr)
        self.assertFalse(wt.exists())

    def test_tilde_home_replaces_only_the_home_folder(self):
        with mock.patch.dict(os.environ, {"HOME": "/home/ann"}):
            text = '{"home": "/home/ann", "dir": "/home/ann/repo/x.md", "other": "/home/anna/y", "tmp": "/tmp/a"}'
            self.assertEqual(lifecycle.tilde_home(text),
                             '{"home": "~", "dir": "~/repo/x.md", "other": "/home/anna/y", "tmp": "/tmp/a"}')
            for kept in ("/mnt/home/ann/repo", "/home/ann+backup/repo", "~/home/ann", "x/home/ann"):
                self.assertEqual(lifecycle.tilde_home(kept), kept)
            self.assertEqual(lifecycle.tilde_home("`/home/ann`, (/home/ann) /home/ann: /home/ann\n"),
                             "`~`, (~) ~: ~\n")
            self.assertEqual(lifecycle.tilde_home(r'{"note": "See\n/home/ann/x\t/home/ann\nnext"}'),
                             r'{"note": "See\n~/x\t~\nnext"}')


if __name__ == "__main__":
    unittest.main()
