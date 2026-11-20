"""The fourth difficulty `easy` and its fallback to the `mechanical` cell.

Run from the repository root:  python3 tests/run.py test_easy_difficulty
Spec: [DIFF-EASY], [EASY-UPGRADE], [DECISION-EASY-UPGRADE]. The sandbox config (`config_for`) has
no easy cells: it stands for a configuration from before `easy`.
"""

from __future__ import annotations

import json
import re
import shutil
import unittest

from saetest import Sandbox, SaeTestCase, config_for, dispatch_workspace
from test_viewer_server import ViewerServerCase, request, run_node


def with_easy(config: dict, cell: dict, harness: str = "claude") -> dict:
    """`config` with `cell` as every easy cell of the execution and research tables."""
    for phase in ("research", "execution"):
        for row in config["routing"][harness]["tables"][phase].values():
            row["easy"] = dict(cell)
    return config


def with_pairs(config: dict, harness: str = "claude") -> dict:
    """Every cell without a model · effort gets its tier's, for a config with tiers off."""
    block = config["routing"][harness]
    for table in block["tables"].values():
        for row in table.values():
            for cell in row.values():
                if "model" not in cell:
                    cell.update(block["tiers"][cell["tier"]])
    return config


class EasyCase(SaeTestCase):
    def executing(self, sb: Sandbox, slug: str, jobs, settings=()) -> str:
        task = sb.new_task(slug, slug)
        if settings:
            sb.sae("set", slug, *settings)
        for job_id, extra in jobs:
            sb.sae("job", "add", slug, job_id, "--kind", "implementation", *extra)
            sb.job_file(task, job_id)
        sb.approve_plan(slug)
        sb.sae("start", slug)
        return task


class DifficultyTests(EasyCase):
    def test_easy_is_accepted_for_execution_and_research_and_refused_for_planning_and_review(self):
        sb = self.sandbox()
        task = sb.new_task("t", "t")
        sb.sae("job", "add", "t", "R1", "--kind", "research", "--difficulty", "easy")
        sb.sae("job", "add", "t", "IMPL", "--kind", "implementation", "--difficulty", "easy")
        jobs = sb.state(task)["jobs"]
        self.assertEqual((jobs["R1"]["difficulty"], jobs["IMPL"]["difficulty"]), ("easy", "easy"))
        out = sb.sae("job", "add", "t", "PLAN", "--kind", "planning", "--difficulty", "easy", code=1).stderr
        self.assertIn("Planning takes --difficulty normal or hard, not easy", out)
        sb.sae("job", "add", "t", "PLAN", "--kind", "planning")
        out = sb.sae("job", "edit", "t", "PLAN", "--difficulty", "easy", code=1).stderr
        self.assertIn("Planning takes --difficulty normal or hard, not easy", out)
        help_text = " ".join(sb.sae("job", "add", "--help").stdout.split())
        self.assertIn("mechanical,easy,normal,hard", help_text)
        self.assertIn("easy", sb.sae("decision", "new", "--help").stdout)

    def test_a_review_of_an_easy_job_routes_through_the_review_normal_cell(self):
        sb = self.sandbox(points=["all-jobs"])
        task = self.executing(sb, "rev", [("EASY", ["--difficulty", "easy"])])
        ws = dispatch_workspace(sb, task, "EASY")
        sb.work(ws, "easy.txt", "x\n", "EASY: work")
        sb.result(task, "jobs/EASY.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "rev", "EASY")
        sb.sae("set", "rev", "review-level=economy")
        review = sb.json("dispatch", "rev", "REVIEW-EASY")
        self.assertEqual((review["phase"], review["difficulty"], review["tier"]), ("review", "normal", "L2"))
        self.assertIsNone(review["fallback"])


class FallbackTests(EasyCase):
    def test_without_easy_cells_an_easy_job_uses_the_mechanical_cell_named_on_the_card(self):
        sb = self.sandbox()
        self.executing(sb, "fb", [("EASY", ["--difficulty", "easy"])])
        ready = {r["id"]: r for r in sb.json("next", "fb")["ready"]}["EASY"]
        self.assertEqual(ready["difficulty"], "easy")
        self.assertEqual((ready["routing"]["tier"], ready["routing"]["fallback"]), ("L1", "mechanical"))
        self.assertIn("mechanical cell", ready["model"])
        card = sb.sae("next", "fb").stdout
        self.assertIn("claude · c-small · medium · mechanical cell", card)
        data = sb.json("dispatch", "fb", "EASY")
        self.assertEqual((data["model"], data["effort"], data["tier"], data["fallback"]),
                         ("c-small", "medium", "L1", "mechanical"))
        header = sb.sae("dispatch", "fb", "EASY", "--resume", "--reason", "again").stdout.splitlines()[1]
        self.assertIn("execution · balanced · easy (no easy cell: uses the mechanical cell; fix: setup mode)",
                      header)

    def test_the_fallback_is_the_effective_mechanical_cell(self):
        """No layer sets easy: a task-level mechanical cell is the one easy uses."""
        sb = self.sandbox()
        self.executing(sb, "eff", [("EASY", ["--difficulty", "easy"])],
                       settings=["routing.claude.execution.balanced.mechanical=L4"])
        data = sb.json("dispatch", "eff", "EASY")
        self.assertEqual((data["tier"], data["source"], data["fallback"]), ("L4", "task", "mechanical"))

    def test_a_global_easy_cell_wins_over_a_task_level_mechanical_override(self):
        sb = self.sandbox()
        sb.config.write_text(json.dumps(with_easy(config_for(sb.worktrees), {"tier": "L2"})))
        self.executing(sb, "glob", [("EASY", ["--difficulty", "easy"])],
                       settings=["routing.claude.execution.balanced.mechanical=L4"])
        data = sb.json("dispatch", "glob", "EASY")
        self.assertEqual((data["tier"], data["model"], data["effort"], data["source"], data["fallback"]),
                         ("L2", "c-mid", "low", "global", None))
        self.assertNotIn("claude:", sb.json("status", "glob")["routing_notice"])  # codex has no easy cells

    def test_tiers_on_and_off(self):
        sb = self.sandbox()
        config = with_easy(config_for(sb.worktrees), {"tier": "L2", "model": "c-small", "effort": "high"})
        sb.config.write_text(json.dumps(config))
        self.executing(sb, "tiers", [("ON", ["--difficulty", "easy"]), ("OFF", ["--difficulty", "easy"])])
        on = sb.json("dispatch", "tiers", "ON")
        self.assertEqual((on["tier"], on["model"], on["effort"]), ("L2", "c-mid", "low"))
        config["routing"]["claude"]["tiers_in_cells"] = False
        sb.config.write_text(json.dumps(with_pairs(config)))
        off = sb.json("dispatch", "tiers", "OFF")
        self.assertEqual((off["tier"], off["model"], off["effort"]), (None, "c-small", "high"))

    def test_tiers_off_without_easy_cells_uses_the_mechanical_model_and_effort(self):
        sb = self.sandbox()
        config = config_for(sb.worktrees)
        for row in config["routing"]["claude"]["tables"]["execution"].values():
            row["mechanical"].update({"model": "c-mid", "effort": "high"})
        config["routing"]["claude"]["tiers_in_cells"] = False
        sb.config.write_text(json.dumps(config))
        self.executing(sb, "off", [("EASY", ["--difficulty", "easy"])])
        data = sb.json("dispatch", "off", "EASY")
        self.assertEqual((data["tier"], data["model"], data["effort"], data["fallback"]),
                         (None, "c-mid", "high", "mechanical"))


class ConfigTests(EasyCase):
    def test_a_three_column_config_saves_and_an_easy_column_only_where_allowed(self):
        sb = self.sandbox()
        sb.sae("setup", "save", stdin=json.dumps(config_for(sb.worktrees)))
        sb.sae("setup", "save", stdin=json.dumps(with_easy(config_for(sb.worktrees), {"tier": "L2"})))
        bad = config_for(sb.worktrees)
        bad["routing"]["claude"]["tables"]["review"]["balanced"]["easy"] = {"tier": "L2"}
        out = " ".join(sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr.split())
        self.assertIn("routing.claude.tables.review.balanced.easy: the review table has only normal, hard", out)
        sb.new_task("t", "t")
        sb.sae("set", "t", "routing.claude.execution.balanced.easy=L3")
        sb.sae("set", "t", "routing.codex.research.premium.easy=lite:low")
        out = " ".join(sb.sae("set", "t", "routing.claude.planning.balanced.easy=L3", code=1).stderr.split())
        self.assertIn("the planning table has only normal, hard", out)
        sb.sae("set", "t", "routing.claude.execution.balanced.easy=inherit")
        sb.sae("project", "set", "routing.claude.execution.economy.easy=L2")
        out = " ".join(sb.sae("project", "set", "routing.claude.review.economy.easy=L2", code=1).stderr.split())
        self.assertIn("the review table has only normal, hard", out)

    def test_status_doctor_and_setup_show_say_when_easy_falls_back(self):
        sb = self.sandbox()
        (sb.codex_home / "config.toml").write_text("[agents]\nmax_threads = 10\n")  # doctor: no other failure
        sb.new_task("t", "t")
        status = sb.sae("status", "t").stdout
        self.assertIn("easy falls back to the mechanical cell (claude: 6 of 6 cells; codex: 6 of 6 cells)", status)
        self.assertIn("Fix: setup mode", status)
        self.assertIn("easy falls back", sb.json("status", "t")["routing_notice"])
        self.assertIn("! easy falls back to the mechanical cell", sb.sae("doctor").stdout)
        show = sb.sae("setup", "show").stdout
        self.assertRegex(show, r"level +mechanical +easy +normal +hard")
        self.assertIn("= mechanical", show)
        # a task-level easy cell: one fewer falls back for this task only
        sb.sae("set", "t", "routing.claude.execution.balanced.easy=L2")
        self.assertIn("claude: 5 of 6 cells", sb.sae("status", "t").stdout)
        sb.config.write_text(json.dumps(with_easy(with_easy(config_for(sb.worktrees), {"tier": "L2"}),
                                                  {"tier": "L2"}, "codex")))
        self.assertNotIn("easy falls back", sb.sae("status", "t").stdout)
        self.assertNotIn("easy falls back", sb.sae("doctor").stdout)
        self.assertNotIn("= mechanical", sb.sae("setup", "show").stdout)


# app.js, task-views.js and settings.js in node: the routing panel of one Settings tab
ROUTING_PANEL_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}}, addEventListener() {}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: el, querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.ANSWER = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
console.log(JSON.stringify(vm.runInContext(`readHash(); S.repo = "R"; S.task = null; SX.h = "claude";
  SX.cur = {key: "R|null", proj: ANSWER};
  ({project: sxRouting("project"), global: sxRouting("global"), bad: sxBad()})`, ctx)));
"""


@unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
class ViewerTests(ViewerServerCase):
    def panel(self, sb: Sandbox) -> dict:
        view = self.view(sb)
        _, answer, _ = request(view["port"], "GET", f"/api/settings?repo={view['repo']}")
        return answer, run_node(ROUTING_PANEL_JS, "app.js", "task-views.js", "settings.js", data=answer)

    def test_the_routing_panel_shows_the_easy_column_and_its_fallback(self):
        sb = self.sandbox()
        answer, out = self.panel(sb)
        self.assertNotIn("easy", json.dumps(answer["routing"]["claude"]["tables"]))  # what the panel reads
        for scope in ("project", "global"):
            html = out[scope]
            self.assertIn("<th>easy</th>", html)
            self.assertIn("easy falls back to the mechanical cell in 6 of 6 cells", html)
            self.assertIn("uses the mechanical cell", html)
            self.assertIn('data-k="' + scope + '|routing.claude.execution.balanced.easy"', html)
            self.assertNotIn('data-k="' + scope + '|routing.claude.review.balanced.easy"', html)
            self.assertEqual(len(re.findall(r'<td class="na"><div>not used</div></td>', html)), 2 * 3 * 2)
        self.assertEqual(out["bad"], 0)

    def test_the_routing_panel_with_easy_cells(self):
        sb = self.sandbox()
        sb.config.write_text(json.dumps(with_easy(config_for(sb.worktrees), {"tier": "L2"})))
        answer, out = self.panel(sb)
        self.assertEqual(answer["routing"]["claude"]["tables"]["execution"]["balanced"]["easy"]["value"], {"tier": "L2"})
        for scope in ("project", "global"):
            self.assertIn("<th>easy</th>", out[scope])
            self.assertNotIn("easy falls back", out[scope])
            self.assertNotIn("uses the mechanical cell", out[scope])
        self.assertEqual(out["bad"], 0)


if __name__ == "__main__":
    unittest.main()
