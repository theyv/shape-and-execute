"""Fixes of REVIEW-INTEGRATION: an uncommitted home finding leaves at closure ([RESOLVES-CLOSE],
[CLOSED-VISIBLE]); a new ADR index lists the files already in the folder ([AMEND-ADR-INDEX]).

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from saetest import SaeTestCase
from test_adr_index import index_problems
from test_resolves import closed_md, finding, planned, run_writer, triage_open


class UncommittedHomeFindingTests(SaeTestCase):
    def test_closure_removes_the_untracked_home_copy_and_the_merge_keeps_it_gone(self):
        sb = self.sandbox()
        name = finding(sb, "Filed, never committed", "app.txt")
        home_file = sb.repo / ".tasks" / "findings" / name
        main_head = sb.git("rev-parse", "HEAD")
        task = planned(sb, "uncommitted", [("FIX", "implementation", "", [], [name])])
        self.assertTrue(home_file.exists())
        out = run_writer(sb, task, "uncommitted", "FIX", resolved=[name])
        self.assertIn(f"Closed finding {name[:-3]}: fixed in {task} by FIX.", out)
        self.assertFalse(home_file.exists())
        self.assertIn(f"fixed in {task} by FIX", closed_md(sb.task_worktree(task)))
        self.assertEqual(sb.git("rev-parse", "HEAD"), main_head)
        self.assertEqual(triage_open(sb), 0)
        sb.sae("finish", "uncommitted")
        sb.git("merge", "-q", "--no-ff", "-m", "merge task", f"task/{task}")
        self.assertFalse(home_file.exists())
        self.assertIn(f"fixed in {task} by FIX", closed_md(sb.repo))
        self.assertEqual(triage_open(sb), 0)


class NewIndexListsExistingFilesTests(SaeTestCase):
    def test_accept_into_a_populated_folder_without_index(self):
        sb = self.sandbox()
        sb.new_task("drafts", "drafts")
        folder = sb.repo / "docs" / "decisions"
        (folder / "research").mkdir(parents=True)
        (folder / "_intent.md").write_text("# Intent: app\n\nWhy.\n")
        (folder / "2026-01-01-old-choice.md").write_text(
            "---\ntitle: Old choice\nstatus: accepted\n---\n\n# Old choice\n\n## Decision\n[human] Keep it old. Why.\n")
        (folder / "research" / "facts.md").write_text("# Facts\n\nFacts about the tool. More.\n")
        draft = Path(sb.json("adr", "new", "drafts", "New choice", "--type", "architecture")["file"])
        sb.json("adr", "accept", str(draft))
        lines = (folder / "index.md").read_text().splitlines()
        links = [line for line in lines if line.startswith("- [")]
        self.assertEqual(links, ["- [Intent: app](_intent.md) — Why the code exists and what it must do; "
                                 "read it first.",
                                 "- [Old choice](2026-01-01-old-choice.md) — Keep it old.",
                                 f"- [New choice]({draft.name})",
                                 "- [Facts](research/facts.md) — Facts about the tool."])
        self.assertIn("## Research notes", lines)
        self.assertEqual(index_problems(folder), [])


if __name__ == "__main__":
    unittest.main()
