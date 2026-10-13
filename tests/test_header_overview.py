"""The slim header and the Overview: the step bar and key stats, the changed lines from git, the
merge checks first, the table of stats per phase; the server's `git_lines` and `phase_stats`.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [HEADER-SLIM], [GIT-LINES], [OVERVIEW-LAYOUT], [OVERVIEW-PHASE-STATS], [EDGE-OLD-TASKS].
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from saetest import SCRIPTS, SKILL_DIR
from test_reviews import ReviewFlowCase
from test_viewer_server import ViewerServerCase, request, run_node

sys.path.insert(0, str(SCRIPTS))

from sae_lib.server import git_lines  # noqa: E402
from sae_lib.session_tokens import phase_stats  # noqa: E402

DONE = SKILL_DIR.parents[1] / ".tasks" / "done"
FINDINGS_DOCS = "2026-10-12-1846--sae-findings-docs"
NODE = shutil.which("node")

# app.js and task-views.js in node: the slim header, the Overview tab and the phase cards of graph()
HEAD_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, dataset: {}, style: {}, classList: {toggle() {}, contains() { return false }}},
  {get: (t, k) => k in t ? t[k] : () => null});
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, documentElement: {dataset: {}}, body: el(), querySelector: el, querySelectorAll: () => [],
    addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 4)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
console.log(JSON.stringify(vm.runInContext(`readHash(); IDX = {sae: "sae", tasks: []}; S.task = TASK.state.task.id;
  var g = graph(TASK), pc = id => g.cards.find(c => c.id === id) || {};
  ({head: slimHead(TASK), overview: TAB.overview(TASK),
    shape: {tk: pc("@shape").tk || "", l3: pc("@shape").l3 || "", tip: pc("@shape").tip || ""},
    plan: {tk: pc("@plan").tk || "", l3: pc("@plan").l3 || ""}})`, ctx)));
"""


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def shortstat(cwd: Path, base: str, branch: str) -> dict:
    """`git diff --shortstat` by hand, from the merge base of base and branch to branch."""
    out = git(cwd, "diff", "--shortstat", git(cwd, "merge-base", base, branch), branch)
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (file|insertion|deletion)", out)}
    return {"added": counts.get("insertion", 0), "removed": counts.get("deletion", 0), "files": counts.get("file", 0)}


def text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


class GitLinesTests(unittest.TestCase):
    """[GIT-LINES] on a throwaway repository: merge base to tip; missing without a task branch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "a.txt").write_text("one\ntwo\nthree\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-qb", "task/x")
        (self.repo / "a.txt").write_text("one\nTWO\nthree\nfour\n")
        (self.repo / "b.txt").write_text("b\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "work")
        git(self.repo, "checkout", "-q", "main")
        # the base branch moves on: its own changes are not the task's
        (self.repo / "c.txt").write_text("c\nc\nc\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "elsewhere")
        self.info = {"git": True, "branch": "task/x", "base": {"branch": "main", "commit": self.base[:7]}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_counts_from_the_merge_base_to_the_task_branch(self):
        expected = shortstat(self.repo, "main", "task/x")
        self.assertEqual(expected, {"added": 3, "removed": 1, "files": 2})
        self.assertEqual(git_lines(self.repo, self.info), expected)

    def test_missing_without_a_task_branch_never_wrong(self):
        for info in ({**self.info, "branch": None}, {**self.info, "git": False}, {**self.info, "branch": "task/gone"}):
            with self.subTest(info=info):
                self.assertIsNone(git_lines(self.repo, info))
        git(self.repo, "branch", "-qD", "task/x")
        self.assertIsNone(git_lines(self.repo, self.info), "deleted after the merge")

    def test_merged_and_kept_branch_counts_from_the_start_commit(self):
        expected = shortstat(self.repo, "main", "task/x")
        git(self.repo, "merge", "-q", "--no-edit", "task/x")
        self.assertEqual(git_lines(self.repo, self.info), expected, "not +0 −0 once the base holds the tip")

    def test_merged_after_taking_newer_base_commits_counts_only_the_task_change(self):
        # the task takes the base's newer commit, then merges: c.txt is not the task's change
        own = shortstat(self.repo, "main", "task/x")
        git(self.repo, "checkout", "-q", "task/x")
        git(self.repo, "merge", "-q", "--no-edit", "main")
        git(self.repo, "checkout", "-q", "main")
        (self.repo / "d.txt").write_text("d\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "more elsewhere")
        git(self.repo, "merge", "-q", "--no-edit", "task/x")
        self.assertEqual(git_lines(self.repo, self.info), own)

    def test_fast_forward_merge_is_missing_not_wrong(self):
        git(self.repo, "checkout", "-q", "task/x")
        git(self.repo, "merge", "-q", "--no-edit", "main")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--ff-only", "task/x")
        self.assertIsNone(git_lines(self.repo, self.info), "the history no longer separates the task's commits")

    def test_deleted_base_branch_uses_the_start_commit(self):
        git(self.repo, "checkout", "-q", "task/x")
        git(self.repo, "branch", "-qD", "main")
        self.assertEqual(git_lines(self.repo, self.info), {"added": 3, "removed": 1, "files": 2})


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class HeaderOverviewCase(ViewerServerCase, ReviewFlowCase):
    def data(self, sb, task: str) -> dict:
        view = getattr(self, "_view", None) or self.view(sb, task)
        self._view = view
        code, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(code, 200, data)
        return data

    def page(self, data: dict) -> dict:
        return run_node(HEAD_JS, "app.js", "task-views.js", data=data)


class ServerDataTests(HeaderOverviewCase):
    def test_task_data_serves_git_lines_and_phase_stats(self):
        """[GIT-LINES], [OVERVIEW-PHASE-STATS]: the server's numbers; no lines before the task branch."""
        sb = self.sandbox()
        shaping = sb.new_task("Shaping", "shaping")
        data = self.data(sb, shaping)
        self.assertIsNone(data["git_lines"], "no task branch while shaping")
        self.assertEqual([r["phase"] for r in data["phase_stats"]], ["shape", "plan", "execution"])
        task = self.planned(sb, "lines", [("CORE", "implementation", "", [])])
        self.run_writer(sb, task, "lines", "CORE")
        state = (sb.task_dir(task) / "state.json").read_bytes()
        data = self.data(sb, task)
        self.assertEqual((sb.task_dir(task) / "state.json").read_bytes(), state, "the read writes nothing")
        info = data["state"]["task"]
        expected = shortstat(sb.repo, info["base"]["branch"], info["branch"])
        self.assertEqual(data["git_lines"], expected)
        self.assertGreaterEqual(expected["added"], 1)
        # the same function as SESSION-TOKENS gives; a running phase's wall time is left to the page
        rows = phase_stats(data["state"], data["events"])
        for row in rows:
            if row["running"]:
                row["wall_s"] = None
        self.assertEqual(data["phase_stats"], rows)
        execution = data["phase_stats"][2]
        self.assertTrue(execution["running"])
        self.assertIsNone(execution["wall_s"])
        self.assertEqual((execution["jobs"], execution["attempts"]), (1, 1))
        page = self.page(data)
        self.assertIn(f"+{expected['added']}", text(page["head"]))
        self.assertIn("lines", text(page["head"]))
        self.assertIn("Execute 1/1", text(page["head"]))
        self.assertIn("running · ", text(page["overview"]))
        self.assertNotIn("pmap", page["head"])


class PageTests(HeaderOverviewCase):
    def test_overview_layout_and_lines_kpi(self):
        """[OVERVIEW-LAYOUT]: Needs you first, then the merge checks, then the risks; Running and the
        phase table below; the KPI Lines, "–" without a task branch."""
        sb = self.sandbox()
        task = self.planned(sb, "layout", [("CORE", "implementation", "", []), ("NEXT", "implementation", "CORE", [])])
        (sb.task_dir(task) / "plan.md").write_text("# Plan\n\n## Riskiest assumptions\n- the merge base is right\n")
        sb.json("dispatch", "layout", "CORE")
        data = self.data(sb, task)
        ov = text(self.page(data)["overview"])
        start = ov.index("Needs you")  # after the KPI row, which also says "Running"
        order = [ov.index(h, start) for h in ("Needs you", "To check before you merge", "Riskiest assumptions", "Running",
                                              "Stats per phase")]
        self.assertEqual(order, sorted(order), ov)
        self.assertIn("Lines", ov)
        data["git_lines"] = None
        ov = self.page(data)["overview"]
        self.assertIn("No task branch", ov)

    def test_header_and_phase_cards_show_the_sum_where_known(self):
        """[OVERVIEW-PHASE-STATS], [HEADER-SLIM]: the sum with the main session where every started phase
        knows it; "subagents only" and "–" with the note where not."""
        sb = self.sandbox()
        task = self.planned(sb, "sum", [("CORE", "implementation", "", [])])
        self.run_writer(sb, task, "sum", "CORE")
        data = self.data(sb, task)
        sub = sum(a.get("tokens") or 0 for j in data["state"]["jobs"].values() for a in j.get("attempts") or [])
        # unknown main-session tokens (no snapshots in the sandbox)
        page = self.page(data)
        self.assertIn("tokens · subagents only", text(page["head"]))
        ov = text(page["overview"])
        self.assertIn("main session unknown", ov)
        self.assertRegex(ov, r"Shape–")
        # known: every started phase has its main-session tokens
        known = copy.deepcopy(data)
        for i, row in enumerate(known["phase_stats"]):
            if row["started"]:
                row["main_tokens"], row["main_note"] = 1000 * (i + 1), None
                row["tokens"] = row["main_tokens"] + row["subagent_tokens"]
        page = self.page(known)
        head = text(page["head"])
        self.assertNotIn("subagents only", head)
        main = sum(r["main_tokens"] for r in known["phase_stats"] if r["started"])
        self.assertIn(re.sub(r"\.0(?=[KM])", "", f"{(sub + main) / 1000:.1f}K") if sub + main >= 1e4 else f"{sub + main:,}", head)
        self.assertEqual(page["shape"]["l3"], "")
        self.assertIn("main session 1,000", page["shape"]["tip"])
        self.assertNotIn("main session unknown", text(page["overview"]))

    def test_old_tasks_render_their_phase_rows_without_errors(self):
        """[EDGE-OLD-TASKS]: every task in .tasks/done/ draws its header and Overview; missing numbers are "–"."""
        found = sorted(p.name for p in DONE.iterdir() if p.is_dir()) if DONE.is_dir() else []
        if not found:
            self.skipTest("no finished task records in .tasks/done/")
        sb = self.sandbox()
        for name in found:
            shutil.copytree(DONE / name, sb.repo / ".tasks" / "done" / name)
        for name in found:
            with self.subTest(task=name):
                data = self.data(sb, name)
                self.assertEqual([r["phase"] for r in data["phase_stats"]], ["shape", "plan", "execution"])
                self.assertIsNone(data["git_lines"], "the sandbox has no task branch for a copied record")
                page = self.page(data)
                for part in (page["head"], page["overview"]):
                    self.assertNotIn("undefined", part)
                    self.assertNotIn("NaN", part)
                    self.assertNotIn("null", text(part))
                self.assertIn("✓ Finish", text(page["head"]))
                ov = text(page["overview"])
                self.assertIn("Stats per phase", ov)
                self.assertIn("Final report", ov)
                if any(r["started"] and r["main_tokens"] is None for r in data["phase_stats"]):
                    self.assertIn("–", ov)
                    self.assertIn("main session unknown", ov)
                if name == FINDINGS_DOCS:
                    self.assertEqual(page["plan"]["tk"], "293k tk · 26m")
                    self.assertEqual(page["plan"]["l3"], "subagents only")


if __name__ == "__main__":
    unittest.main()
