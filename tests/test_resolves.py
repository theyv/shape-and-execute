"""Findings a job resolves: the `resolves` field, closing on success, the closed-findings rule
across checkouts, and the final report sections (closed, to check, worktrees).

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [RESOLVES-FIELD], [RESOLVES-CLOSE], [CLOSED-VISIBLE], [RESOLVES-REPORT],
[FINAL-REPORT-WORKTREES], [RULE-ONE-CLOSE], [EDGE-RESOLVES-CLOSED], [EDGE-FIX-GROUP].
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from saetest import SCRIPTS, Sandbox, SaeTestCase, covers_of, dispatch_workspace


def finding(sb: Sandbox, title: str, paths: str = "") -> str:
    """A finding filed in the home checkout; returns its file name."""
    args = ["finding", "new", title, "--type", "defect", "--confidence", "high", "--body", f"{title}."]
    return Path(sb.json(*args, *(["--paths", paths] if paths else []))["file"]).name


def commit_tasks_folder(sb: Sandbox) -> None:
    """The findings and the `.tasks/` git files on main, as in a repository that used sae before."""
    sb.git("add", ".tasks")
    sb.git("commit", "-q", "-m", "findings")


def job_file(sb: Sandbox, task: str, job_id: str, resolves=(), verify=()) -> None:
    front = f"---\nid: {job_id}\ncovers: {json.dumps(covers_of(sb.task_dir(task)))}\nverify: {json.dumps(list(verify))}\n"
    if resolves:
        front += "resolves:\n" + "".join(f"  - {r}\n" for r in resolves)
    folder = sb.task_dir(task) / "jobs"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{job_id}.md").write_text(front + f"---\n\n# {job_id}\n\n## Objective\nDo one thing.\n")


def planned(sb: Sandbox, slug: str, jobs: list[tuple], settings=(), start: bool = True) -> str:
    """jobs: (ID, kind, needs, extra args, resolves)."""
    task = sb.new_task(slug, slug)
    if settings:
        sb.sae("set", slug, *settings)
    for job_id, kind, needs, extra, resolves in jobs:
        sb.sae("job", "add", slug, job_id, "--kind", kind, *(["--needs", needs] if needs else []), *extra)
        job_file(sb, task, job_id, resolves)
    sb.approve_plan(slug)
    if start:
        sb.sae("start", slug)
    return task


def run_writer(sb: Sandbox, task: str, slug: str, job: str, resolved=(), status: str = "done",
               code: int = 0) -> str:
    ws = dispatch_workspace(sb, task, job)
    sb.work(ws, f"{job.lower()}.txt", f"{job}\n", f"{job}: work")
    sb.result(task, f"jobs/{job}.result.md", status=status, summary=job, validation="pass", changes="made",
              resolved="[" + ", ".join(resolved) + "]")
    return sb.sae("collect", slug, job, code=code).stdout


def closed_md(checkout: Path) -> str:
    path = checkout / ".tasks" / "findings" / "closed.md"
    return path.read_text() if path.exists() else ""


def triage_open(sb: Sandbox, cwd: Path | None = None) -> int:
    return sum(r["open"] for r in sb.json("triage", cwd=cwd)["queues"] if r["queue"] != "decision drafts")


class ResolvesFieldTests(SaeTestCase):
    def check(self, sb: Sandbox, slug: str, code: int) -> str:
        proc = sb.sae("check", slug, code=code)
        return proc.stdout + proc.stderr

    def test_open_finding_passes_and_a_missing_one_is_refused(self):
        sb = self.sandbox()
        name = finding(sb, "Slow lookup")
        task = planned(sb, "field", [("FIX", "implementation", "", [], [name])], start=False)
        self.assertNotIn("resolves", self.check(sb, "field", 0))
        job_file(sb, task, "FIX", ["2026-01-01-0000--gone.md"])
        out = self.check(sb, "field", 3)
        self.assertIn("FIX: resolves 2026-01-01-0000--gone.md", out)

    def test_an_entry_in_closed_md_passes(self):
        sb = self.sandbox()
        name = finding(sb, "Closed earlier")
        task = planned(sb, "closedok", [("FIX", "implementation", "", [], [])], start=False)
        sb.sae("finding", "close", f".tasks/findings/{name}", "--outcome", "rejected: expected")
        job_file(sb, task, "FIX", [name])
        self.check(sb, "closedok", 0)

    def test_research_and_review_jobs_may_not_resolve(self):
        sb = self.sandbox()
        name = finding(sb, "Some defect")
        task = planned(sb, "kinds", [("FIX", "implementation", "", [], [])], start=False)
        sb.sae("job", "add", "kinds", "LOOK", "--kind", "research")
        job_file(sb, task, "LOOK", [name])
        self.assertIn("LOOK: resolves on a research job", self.check(sb, "kinds", 3))
        job_file(sb, task, "LOOK")
        state_path = sb.task_dir(task) / "state.json"
        state = json.loads(state_path.read_text())
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib.tasks import new_job
        finally:
            sys.path.remove(str(SCRIPTS))
        state["jobs"]["REVIEW-FIX"] = dict(new_job("review", ["FIX"], "normal", target="FIX"), round=1)
        state_path.write_text(json.dumps(state))
        self.check(sb, "kinds", 0)
        job_file(sb, task, "REVIEW-FIX", [name])
        self.assertIn("REVIEW-FIX: resolves on a review job", self.check(sb, "kinds", 3))

    def test_templates_show_the_fields(self):
        skill = SCRIPTS.parent
        self.assertIn("resolves:", (skill / "templates" / "job.md").read_text())
        self.assertIn("resolved:", (skill / "templates" / "job-result.md").read_text())


class CloseOnSuccessTests(SaeTestCase):
    def test_merge_closes_on_the_task_branch_and_home_sees_it_at_once(self):
        """[RESOLVES-CLOSE] fix job, [CLOSED-VISIBLE] from the home checkout, then the owner's merge."""
        sb = self.sandbox()
        name = finding(sb, "Bug in app", "app.txt")
        commit_tasks_folder(sb)
        main_head = sb.git("rev-parse", "HEAD")
        self.assertEqual(triage_open(sb), 1)
        task = planned(sb, "fix", [("FIX", "implementation", "", [], [name])])
        wt = sb.task_worktree(task)
        out = run_writer(sb, task, "fix", "FIX", resolved=[name])
        stem = name[:-3]
        self.assertIn(f"Closed finding {stem}: fixed in {task} by FIX.", out)
        self.assertFalse((wt / ".tasks" / "findings" / name).exists())
        self.assertIn(f" · {stem} · Bug in app · fixed in {task} by FIX", closed_md(wt))
        self.assertEqual(sb.git("status", "--porcelain", "--", ".tasks/findings", cwd=wt), "")
        self.assertEqual(sb.git("log", "-1", "--format=%s", cwd=wt), "FIX: close resolved findings")
        # the home checkout: main untouched, the finding no longer counts
        self.assertTrue((sb.repo / ".tasks" / "findings" / name).exists())
        self.assertEqual(sb.git("rev-parse", "HEAD"), main_head)
        self.assertEqual(sb.git("status", "--porcelain", "--", ".tasks/findings"), "")
        self.assertEqual(triage_open(sb), 0)
        self.assertEqual(sb.json("status")["open_findings"], 0)
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib import server
            with mock.patch.object(server, "repo_by_key", return_value=sb.repo):
                data = server.repo_data("key")
        finally:
            sys.path.remove(str(SCRIPTS))
        self.assertEqual(data["findings"], [])
        self.assertIn(f"fixed in {task} by FIX", data["closed_findings"])
        # after finish and the owner's merge: gone on main, the line on main
        sb.sae("finish", "fix")
        sb.git("merge", "-q", "--no-ff", "-m", "merge task", f"task/{task}")
        self.assertFalse((sb.repo / ".tasks" / "findings" / name).exists())
        self.assertIn(f"fixed in {task} by FIX", closed_md(sb.repo))
        self.assertEqual(triage_open(sb), 0)

    def test_validation_job_without_changes_closes_when_collected_done(self):
        sb = self.sandbox()
        name = finding(sb, "Maybe fixed already")
        commit_tasks_folder(sb)
        task = planned(sb, "valid", [("CHECK", "validation", "", [], [name])])
        sb.sae("dispatch", "valid", "CHECK")
        sb.result(task, "jobs/CHECK.result.md", status="done", summary="confirmed", validation="pass",
                  changes="none", resolved=f"[{name}]")
        out = sb.sae("collect", "valid", "CHECK").stdout
        wt = sb.task_worktree(task)
        self.assertIn(f"Closed finding {name[:-3]}: fixed in {task} by CHECK.", out)
        self.assertFalse((wt / ".tasks" / "findings" / name).exists())
        self.assertIn(f"fixed in {task} by CHECK", closed_md(wt))
        self.assertEqual(triage_open(sb), 0)

    def test_failed_parked_and_removed_jobs_close_nothing(self):
        sb = self.sandbox()
        names = {job: finding(sb, f"Defect {job.lower()}") for job in ("FAILS", "PARKS", "GOES")}
        commit_tasks_folder(sb)
        task = planned(sb, "nothing", [(job, "implementation", "", [], [name]) for job, name in names.items()])
        run_writer(sb, task, "nothing", "FAILS", resolved=[names["FAILS"]], status="failed")
        run_writer(sb, task, "nothing", "PARKS", resolved=[names["PARKS"]], status="parked")
        sb.sae("job", "remove", "nothing", "GOES", "--reason", "not needed")
        wt = sb.task_worktree(task)
        for name in names.values():
            self.assertTrue((wt / ".tasks" / "findings" / name).exists())
        self.assertEqual(closed_md(wt), "")
        self.assertEqual(triage_open(sb), 3)
        self.assertFalse([e for e in sb.events(task) if e["type"] == "finding.closed"])

    def test_unresolved_entry_stays_open_and_collect_names_it(self):
        sb = self.sandbox()
        fixed, kept = finding(sb, "Fixed one"), finding(sb, "Disputed one")
        other = finding(sb, "Not asked")
        commit_tasks_folder(sb)
        task = planned(sb, "partial", [("FIX", "implementation", "", [], [fixed, kept])])
        out = " ".join(run_writer(sb, task, "partial", "FIX", resolved=[fixed, other]).split())
        self.assertIn(f"Finding stays open: {kept[:-3]}", out)
        self.assertIn(f"Ignored: {other[:-3]} is in the resolved list of FIX, not in its resolves.", out)
        wt = sb.task_worktree(task)
        self.assertFalse((wt / ".tasks" / "findings" / fixed).exists())
        self.assertTrue((wt / ".tasks" / "findings" / kept).exists())
        self.assertTrue((wt / ".tasks" / "findings" / other).exists())
        self.assertEqual(triage_open(sb), 2)

    def test_finding_close_accepts_the_job_form(self):
        sb = self.sandbox()
        name = finding(sb, "By hand")
        sb.sae("finding", "close", f".tasks/findings/{name}", "--outcome", "fixed in 2026-10-12-1846--x by JOB-A")
        self.assertIn("fixed in 2026-10-12-1846--x by JOB-A", closed_md(sb.repo))
        other = finding(sb, "Bad outcome")
        sb.sae("finding", "close", f".tasks/findings/{other}", "--outcome", "fixed in x by", code=1)


class CloseOnceTests(SaeTestCase):
    def test_second_success_finds_it_closed(self):
        """[RULE-ONE-CLOSE]"""
        sb = self.sandbox()
        name = finding(sb, "Shared cause")
        commit_tasks_folder(sb)
        task = planned(sb, "twice", [("LEFT", "implementation", "", [], [name]),
                                     ("RIGHT", "implementation", "", [], [name])])
        self.assertIn(f"Closed finding {name[:-3]}", run_writer(sb, task, "twice", "LEFT", resolved=[name]))
        out = " ".join(run_writer(sb, task, "twice", "RIGHT", resolved=[name]).split())
        self.assertIn(f"Finding {name[:-3]} was closed already (fixed in {task} by LEFT); RIGHT closes nothing more.",
                      out)
        self.assertEqual(closed_md(sb.task_worktree(task)).count(name[:-3]), 1)

    def test_closed_by_hand_meanwhile_is_noted(self):
        """[EDGE-RESOLVES-CLOSED]: closed in the home checkout after start."""
        sb = self.sandbox()
        name = finding(sb, "Closed by hand")
        commit_tasks_folder(sb)
        task = planned(sb, "meanwhile", [("FIX", "implementation", "", [], [name])])
        sb.sae("finding", "close", f".tasks/findings/{name}", "--outcome", "rejected: not a bug")
        out = " ".join(run_writer(sb, task, "meanwhile", "FIX", resolved=[name]).split())
        self.assertIn(f"Finding {name[:-3]} was closed already (rejected: not a bug)", out)
        wt = sb.task_worktree(task)
        self.assertEqual(closed_md(wt), "")
        self.assertEqual(sb.state(task)["jobs"]["FIX"]["merged"], True)

    def test_merged_fix_group_closes_every_member(self):
        """[EDGE-FIX-GROUP]"""
        sb = self.sandbox()
        first, second = finding(sb, "Target finding"), finding(sb, "Fix finding")
        commit_tasks_folder(sb)
        task = planned(sb, "group", [("CORE", "implementation", "", ["--review"], [first]),
                                     ("SIDE", "implementation", "", [], [])], settings=["review=selected-jobs"])
        out = run_writer(sb, task, "group", "CORE", resolved=[first])
        self.assertIn("Added REVIEW-CORE", out)
        self.assertNotIn("Closed finding", out)            # not merged yet: not a success
        self.review(sb, task, "group", "REVIEW-CORE", "changes-required")
        sb.sae("job", "add", "group", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE",
               "--reason", "REVIEW-CORE: changes required")
        job_file(sb, task, "CORE-FIX-1", [second])
        self.assertIn("Added REVIEW-CORE-2", run_writer(sb, task, "group", "CORE-FIX-1", resolved=[second]))
        out = self.review(sb, task, "group", "REVIEW-CORE-2", "pass")
        self.assertIn(f"Closed finding {first[:-3]}: fixed in {task} by CORE.", out)
        self.assertIn(f"Closed finding {second[:-3]}: fixed in {task} by CORE-FIX-1.", out)
        self.assertEqual(triage_open(sb), 0)

    def review(self, sb: Sandbox, task: str, slug: str, review: str, verdict: str) -> str:
        sb.sae("dispatch", slug, review)
        sb.result(task, f"reviews/{review}.md", target="CORE", verdict=verdict)
        return " ".join(sb.sae("collect", slug, review).stdout.split())


class CountingCheckoutTests(SaeTestCase):
    def test_inherited_task_records_do_not_make_a_checkout_count(self):
        """[CLOSED-VISIBLE]: a job worktree and an abandoned task's kept worktree inherit a finished
        task's record from main; a closure written only there does not hide the finding."""
        sb = self.sandbox()
        name = finding(sb, "Still open")
        commit_tasks_folder(sb)
        old = planned(sb, "old", [("ONE", "implementation", "", [], [])])
        run_writer(sb, old, "old", "ONE")
        sb.sae("finish", "old")
        sb.git("merge", "-q", "--no-ff", "-m", "merge old", f"task/{old}")
        line = f"- 2026-10-12 · {name[:-3]} · Still open · rejected: not merged\n"
        task = planned(sb, "live", [("JOB", "implementation", "", [], []), ("PAR", "implementation", "", [], [])])
        ws = dispatch_workspace(sb, task, "JOB")
        self.assertNotEqual(ws, sb.task_worktree(task))
        self.assertTrue((ws / ".tasks" / "done" / old / "state.json").exists())
        (ws / ".tasks" / "findings" / "closed.md").write_text("# Closed findings\n\n" + line)
        gone = planned(sb, "gone", [("TWO", "implementation", "", [], [])])
        kept = sb.task_worktree(gone)
        (kept / "notes.txt").write_text("uncommitted\n")  # abandon keeps the worktree
        sb.sae("abandon", "gone", "--reason", "not needed")
        (kept / ".tasks" / "findings" / "closed.md").write_text("# Closed findings\n\n" + line)
        self.assertTrue((kept / ".tasks" / "done" / old / "state.json").exists())
        self.assertEqual(triage_open(sb), 1)
        self.assertEqual(sb.json("status")["open_findings"], 1)


class ConflictGroupTests(SaeTestCase):
    def test_integration_of_a_fix_group_closes_the_fix_findings(self):
        """[EDGE-FIX-GROUP] through a merge conflict: the integration carries CORE and CORE-FIX-1."""
        sb = self.sandbox()
        first, second = finding(sb, "Target finding"), finding(sb, "Fix finding")
        commit_tasks_folder(sb)
        task = planned(sb, "clash", [("CORE", "implementation", "", ["--review"], [first]),
                                     ("SIDE", "implementation", "", [], [])], settings=["review=selected-jobs"])
        side = dispatch_workspace(sb, task, "SIDE")
        core = dispatch_workspace(sb, task, "CORE")
        sb.work(side, "app.txt", "side\n", "SIDE: edit")
        sb.result(task, "jobs/SIDE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "clash", "SIDE")
        sb.work(core, "app.txt", "core\n", "CORE: edit")
        sb.result(task, "jobs/CORE.result.md", status="done", summary="c", validation="pass", changes="made",
                  resolved=f"[{first}]")
        sb.sae("collect", "clash", "CORE")
        self.review(sb, task, "REVIEW-CORE", "changes-required")
        sb.sae("job", "add", "clash", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE",
               "--reason", "REVIEW-CORE: changes required")
        job_file(sb, task, "CORE-FIX-1", [second])
        run_writer(sb, task, "clash", "CORE-FIX-1", resolved=[second])
        self.assertIn("INTEGRATE-CORE", self.review(sb, task, "REVIEW-CORE-2", "pass", code=4))
        ws = dispatch_workspace(sb, task, "INTEGRATE-CORE")
        (ws / "app.txt").write_text("side and core\n")
        sb.git("add", "app.txt", cwd=ws)
        sb.git("commit", "-q", "--no-edit", cwd=ws)
        sb.result(task, "jobs/INTEGRATE-CORE.result.md", status="done", summary="i", validation="pass",
                  changes="made")
        out = " ".join(sb.sae("collect", "clash", "INTEGRATE-CORE").stdout.split())
        self.assertIn(f"Closed finding {first[:-3]}: fixed in {task} by CORE.", out)
        self.assertIn(f"Closed finding {second[:-3]}: fixed in {task} by CORE-FIX-1.", out)
        self.assertTrue(sb.state(task)["jobs"]["CORE-FIX-1"]["merged"])
        self.assertEqual(triage_open(sb), 0)

    def review(self, sb: Sandbox, task: str, review: str, verdict: str, code: int = 0) -> str:
        sb.sae("dispatch", "clash", review)
        sb.result(task, f"reviews/{review}.md", target="CORE", verdict=verdict)
        return " ".join(sb.sae("collect", "clash", review, code=code).stdout.split())


class FinalReportTests(SaeTestCase):
    def test_closed_and_check_sections_branch_lines_and_kept_worktrees(self):
        """[RESOLVES-REPORT], [FINAL-REPORT-WORKTREES]"""
        sb = self.sandbox()
        fixed = finding(sb, "Fixed here")
        touched = finding(sb, "About left", "left.txt")
        finding(sb, "Elsewhere", "docs/")
        commit_tasks_folder(sb)
        task = planned(sb, "report", [("LEFT", "implementation", "", [], [fixed]),
                                      ("RIGHT", "implementation", "", [], [])])
        run_writer(sb, task, "report", "LEFT", resolved=[fixed])
        ws = dispatch_workspace(sb, task, "RIGHT")
        sb.work(ws, "right.txt", "r\n", "RIGHT: work")
        (ws / "notes.txt").write_text("kept\n")
        sb.result(task, "jobs/RIGHT.result.md", status="done", summary="r", validation="pass", changes="made")
        sb.sae("collect", "report", "RIGHT")
        out = sb.sae("finish", "report").stdout
        wt = sb.task_worktree(task)
        self.assertIn(f"## Findings closed by this task\n- {fixed[:-3]} · LEFT\n", out)
        self.assertIn(f"## Check these findings\nOpen findings about files this task changed:\n"
                      f"- .tasks/findings/{touched} (left.txt)\n", out)
        self.assertNotIn("Elsewhere", out)
        self.assertIn(f"Task worktree, test the result here:\n  {wt}\n"
                      f"After you merge task/{task}, sae removes the task worktree.", out)
        self.assertIn(f"## Kept worktrees\n- {ws}: it holds uncommitted work: notes.txt", out)
        self.assertNotIn("Worktree kept:", out)
        report = out[out.index("# Final report"):]
        self.assertLess(report.index("## Branch"), report.index("## Kept worktrees"))

    def test_a_finding_filed_at_home_after_start_is_checked(self):
        """[RESOLVES-REPORT]: open findings of the home checkout count, not only the task's copy."""
        sb = self.sandbox()
        task = planned(sb, "late", [("APP", "implementation", "", [], [])])
        name = finding(sb, "Filed later", "app.txt")
        ws = dispatch_workspace(sb, task, "APP")
        sb.work(ws, "app.txt", "changed\n", "APP: edit")
        sb.result(task, "jobs/APP.result.md", status="done", summary="a", validation="pass", changes="made")
        sb.sae("collect", "late", "APP")
        out = sb.sae("finish", "late").stdout
        self.assertIn(f"## Check these findings\nOpen findings about files this task changed:\n"
                      f"- {sb.repo / '.tasks' / 'findings' / name} (app.txt)\n", out)

    def test_sections_are_absent_when_empty(self):
        sb = self.sandbox()
        finding(sb, "Unrelated", "docs/")
        commit_tasks_folder(sb)
        task = planned(sb, "quiet", [("ONE", "implementation", "", [], [])])
        run_writer(sb, task, "quiet", "ONE")
        out = sb.sae("finish", "quiet").stdout
        for heading in ("## Findings closed by this task", "## Check these findings", "## Kept worktrees"):
            self.assertNotIn(heading, out)
        self.assertIn("Task worktree, test the result here:", out)


if __name__ == "__main__":
    unittest.main()
