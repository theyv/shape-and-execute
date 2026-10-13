"""The gaps the final validation found: +0 −0 changed lines before the first merge into the task
branch, the Overview's "Needs you" listing the server's waiting reasons, readable Timeline text
for ask and session snapshot events, and the viewer README's Plan and Finish edge rule.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [GIT-LINES], [ASK-COMMAND], [OVERVIEW-LAYOUT].
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from saetest import SCRIPTS, SKILL_DIR
from test_header_overview import git, text
from test_sae_ask import AskCase
from test_viewer_server import ViewerServerCase, request, run_node

sys.path.insert(0, str(SCRIPTS))

from sae_lib.server import git_lines  # noqa: E402

# app.js and task-views.js in node: the Overview and the Timeline of one task
VIEWS_JS = r"""
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
  ({overview: TAB.overview(TASK), timeline: TAB.timeline(TASK)})`, ctx)));
"""


class GitLinesAtStartTests(unittest.TestCase):
    """[GIT-LINES]: a task branch still at its start commit has changed nothing: +0 −0, not missing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "a.txt").write_text("a\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "branch", "task/x")
        self.info = {"git": True, "branch": "task/x", "base": {"branch": "main", "commit": self.base[:7]}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_started_branch_at_its_start_commit_gives_zeros(self):
        zeros = {"added": 0, "removed": 0, "files": 0}
        self.assertEqual(git_lines(self.repo, self.info), zeros)
        # the base branch moves on: still nothing of the task's own
        (self.repo / "b.txt").write_text("b\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "elsewhere")
        self.assertEqual(git_lines(self.repo, self.info), zeros)

    def test_fast_forward_merge_stays_missing(self):
        git(self.repo, "checkout", "-q", "task/x")
        (self.repo / "b.txt").write_text("b\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "work")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--ff-only", "task/x")
        self.assertIsNone(git_lines(self.repo, self.info))


@unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
class OverviewAndTimelineTests(ViewerServerCase, AskCase):
    def data(self, sb, task: str) -> dict:
        view = getattr(self, "_view", None) or self.view(sb, task)
        self._view = view
        code, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(code, 200, data)
        return data

    def views(self, data: dict) -> dict:
        return run_node(VIEWS_JS, "app.js", "task-views.js", data=data)

    def needs_you(self, overview: str) -> str:
        return text(overview.split(">Needs you<", 1)[1].split('<div class="sec', 1)[0])

    def test_needs_you_lists_open_asks_and_active_holds(self):
        """[ASK-COMMAND]: the Overview never says "Nothing needs you" while the server's waiting list holds a reason."""
        sb = self.sandbox()
        task = self.started(sb, "gaps", jobs=("A", "B"))
        self.assertIn("Nothing needs you.", self.needs_you(self.views(self.data(sb, task))["overview"]))
        sb.sae("ask", "gaps", "Which colour for the button?")
        sb.sae("hold", "gaps", "A", "--reason", "look first")
        data = self.data(sb, task)
        self.assertEqual([w["kind"] for w in data["waiting"]], ["ask"], "a hold waits once its job is done")
        data["waiting"].append({"kind": "hold", "job": "A", "text": "Hold after A: look first"})
        overview = self.views(data)["overview"]
        need = self.needs_you(overview)
        self.assertNotIn("Nothing needs you.", need)
        self.assertIn("Which colour for the button?", need)
        self.assertIn("Hold after A: look first", need)
        self.assertIn('data-act="hold" data-id="A" data-v="release"', overview)

    def test_timeline_shows_ask_and_session_snapshot_events_as_text(self):
        sb = self.sandbox()
        task = self.started(sb, "tl", jobs=("A",))
        sb.sae("ask", "tl", "Release today?", "--job", "A")
        sb.sae("ask", "tl", "--answered")
        data = self.data(sb, task)
        data["events"].append({"at": "2026-10-14T10:00:00+02:00", "type": "session.snapshot", "command": "dispatch",
                               "phase_before": "executing", "phase": "executing", "harness": "claude",
                               "session": "s1", "total": 123456})
        timeline = self.views(data)["timeline"]
        self.assertNotIn("{&quot;", timeline, "no raw JSON")
        self.assertNotIn('{"', timeline, "no raw JSON")
        plain = text(timeline)
        self.assertIn("Asked the owner (A): Release today?", plain)
        self.assertIn("Ask #1 answered", plain)
        self.assertIn("Main session: executing, 123.5K tokens", plain)


class ViewerReadmeTests(unittest.TestCase):
    def test_readme_states_the_job_graph_rule_for_plan_and_finish_edges(self):
        readme = (SKILL_DIR / "assets" / "viewer" / "README.md").read_text()
        self.assertNotIn("the card with the cycle's last job gets the Finish edge", readme)
        rule = re.sub(r"\s+", " ", readme)
        self.assertIn("every card that holds an entry job", rule)
        self.assertIn("every card that holds a terminal job (nothing needs it) → Finish, except a card outside a cycle "
                      "that already has an edge out", rule)


if __name__ == "__main__":
    unittest.main()
