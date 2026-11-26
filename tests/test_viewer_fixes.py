"""Viewer fixes: the process-map steps in the task data, effective difficulty in prompts and the viewer,
known Claude families in the settings answer, a state path below a file, `by` of hold events,
the routing mode switch (Tiers mode | Free mode).

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [VIEWER-PROCESS-MAP], [DIFFICULTY-DISPLAY], [SETTINGS-CLAUDE-FAMILIES], [VIEWER-STATE-PATH],
[HOLD-BY], [AMEND-3].
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest

from saetest import SAE, SCRIPTS
from test_reviews import ReviewFlowCase
from test_task_worktree import plan
from test_viewer_server import ViewerServerCase, request, run_node

sys.path.insert(0, str(SCRIPTS))

from sae_lib.setup_mode import CLAUDE_FAMILIES  # noqa: E402


# app.js and task-views.js in node: the slim header, the job table and the job header of one job
TASK_VIEW_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, scrollTop: 0, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
const panel = el();
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: (s) => s === "#panel" ? panel : el(), querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 4)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
ctx.ID = process.argv[5];
vm.runInContext(`readHash(); IDX = {sae: "sae", tasks: []}; S.task = TASK.state.task.id; TASKS[S.task] = TASK;
  S.tab = "plan"; S.job = ID; renderPanel()`, ctx);
const out = vm.runInContext("({head: slimHead(TASK), jobs: TAB.jobs(TASK)})", ctx);
out.header = panel.innerHTML;
console.log(JSON.stringify(out));
"""


# app.js and settings.js in node: the "Add family" dropdown of the Claude model list
ADD_FAMILY_JS = r"""
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
  var html = sxModelsSec(), opts = [...html.matchAll(/<option value="([^"]*)"/g)].map(m => m[1]);
  ({opts, button: html.includes(">Add family</button>")})`, ctx)));
"""


# app.js, task-views.js and settings.js in node: the routing mode switch, then clicks on it (argv: scope, values)
MODE_SWITCH_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}}, addEventListener() {}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
const clicks = [];
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: el, querySelectorAll: () => [], createElement: el,
    addEventListener(type, fn) { if (type === "click") clicks.push(fn) }}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.ANSWER = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
const scope = process.argv[6], posts = [];
vm.runInContext(`readHash(); S.repo = "R"; S.task = null; SX.h = "claude"; SX.cur = {key: "R|null", proj: ANSWER};
  renderMain = () => {}; sxLoad = () => {}; render = () => {}; loadTask = () => {}`, ctx);
ctx.post = (route, body) => { posts.push(body.pairs); return Promise.resolve({ok: true}) };
const out = {html: vm.runInContext(`sxRouting("${scope}")`, ctx), after: []};
for (const v of process.argv.slice(7)) {
  const button = {dataset: {act: "sxtic", k: scope + "|tiers-in-cells.claude", v}, disabled: false};
  const ev = {target: {closest: s => s === "[data-act]" ? button : null}, stopPropagation() {}, preventDefault() {}};
  for (const fn of clicks) fn(ev);
  out.after.push(vm.runInContext(`(c => c && JSON.parse(JSON.stringify(c.routing.claude)))(SX.draft && SX.draft.c)`, ctx) || null);
}
Promise.resolve().then(() => vm.runInContext("SX.q", ctx)).then(() => {
  out.posts = posts; console.log(JSON.stringify(out)) });
"""


class DifficultyDisplayTests(ViewerServerCase, ReviewFlowCase):
    def test_spec_review_prompt_names_the_task_difficulty(self):
        """[DIFFICULTY-DISPLAY]: REVIEW-SPEC is stored with difficulty null; its prompt names the task's."""
        sb = self.sandbox(points=["spec"])
        task = sb.new_task("Spec work", "spec-work")
        sb.sae("set", "spec-work", "task-difficulty=hard")
        (sb.task_dir(task) / "specs.md").write_text(
            "# Spec\n\n## Requirements\n\n### [CLAIM-NEXT] Next step\nAcceptance:\n- [ ] shows next step\n")
        data = sb.json("dispatch", "spec-work", "REVIEW-SPEC")
        self.assertIsNone(sb.state(task)["jobs"]["REVIEW-SPEC"]["difficulty"])
        self.assertIn("Job: REVIEW-SPEC (review, hard)", data["prompt"])
        self.assertNotIn("None", data["prompt"].splitlines()[2])

    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_job_review_of_a_mechanical_job_shows_normal_in_prompt_and_viewer(self):
        """[DIFFICULTY-DISPLAY], [VIEWER-PROCESS-MAP]: prompt, job table and job header show the
        difficulty of `sae next`; the task data carries the process-map steps of `sae status`, and the
        page draws them as the step bar of the slim header ([HEADER-SLIM]), not as the process map."""
        sb = self.sandbox()
        task = self.planned(sb, "mech", [("MECH", "implementation", "", ["--difficulty", "mechanical"])],
                            settings=["review=all-jobs"])
        self.run_writer(sb, task, "mech", "MECH")
        ready = {r["id"]: r for r in sb.json("next", "mech")["ready"]}
        self.assertEqual(ready["REVIEW-MECH"]["difficulty"], "normal")
        view = self.view(sb, "mech")
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(data["difficulty"]["REVIEW-MECH"], "normal")
        self.assertNotIn("map", data)
        self.assertTrue(data["steps"])
        out = run_node(TASK_VIEW_JS, "app.js", "task-views.js", data=data, args=["REVIEW-MECH"])
        self.assertIn("review · normal", out["header"])
        self.assertIn('review<span class="mut"> · normal</span>', out["jobs"])
        self.assertNotIn("review · null", out["header"])
        self.assertIn('class="stepbar"', out["head"])
        self.assertIn('aria-current="step">◐ Execute 1/1</li>', out["head"])
        self.assertNotIn("pmap", out["head"])
        prompt = sb.json("dispatch", "mech", "REVIEW-MECH")["prompt"]
        self.assertIn("Job: REVIEW-MECH (review, normal)", prompt)

    def test_task_data_carries_the_process_map_before_execution(self):
        """[VIEWER-PROCESS-MAP]: every phase, not only executing; the steps, not the map's lines ([HEADER-SLIM])."""
        sb = self.sandbox()
        task = sb.new_task("Shaping", "shaping")
        view = self.view(sb, "shaping")
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(data["state"]["task"]["phase"], "shaping")
        self.assertTrue(sb.json("status", "shaping")["map"])  # the CLI keeps printing its process map
        self.assertNotIn("map", data)
        self.assertEqual([s["phase"] for s in data["steps"]][:1], ["shape"])


class ClaudeFamilyTests(ViewerServerCase):
    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_add_family_offers_every_known_family_missing_from_the_list(self):
        """[SETTINGS-CLAUDE-FAMILIES]: the settings answer sends the families; the dropdown offers the missing."""
        sb = self.sandbox()
        sb.new_task("Families", "families")
        view = self.view(sb)
        _, answer, _ = request(view["port"], "GET", f"/api/settings?repo={view['repo']}")
        self.assertEqual(answer["claude_families"], list(CLAUDE_FAMILIES))
        listed = list(CLAUDE_FAMILIES[1:3])
        answer["config"]["models"]["claude"] = [{"model": m, "family": True, "enabled": True,
                                                 "efforts": ["low", "high"]} for m in listed]
        out = run_node(ADD_FAMILY_JS, "app.js", "task-views.js", "settings.js", data=answer)
        self.assertEqual(sorted(out["opts"]), sorted("cf:" + f for f in CLAUDE_FAMILIES if f not in listed))
        self.assertTrue(out["button"])


@unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
class RoutingModeSwitchTests(ViewerServerCase):
    """[AMEND-3]: the switch names Tiers mode and Free mode and still flips `tiers_in_cells`."""

    def answer(self) -> dict:
        sb = self.sandbox()
        sb.new_task("Modes", "modes")
        view = self.view(sb)
        return request(view["port"], "GET", f"/api/settings?repo={view['repo']}")[1]

    def test_global_switch_names_both_modes_and_flips_the_draft(self):
        out = run_node(MODE_SWITCH_JS, "app.js", "task-views.js", "settings.js", data=self.answer(),
                       args=["global", "tiers", "free", "free", "tiers"])
        html = out["html"]
        self.assertRegex(html, r'aria-checked="true" data-act="sxtic"[^>]*data-v="tiers"[^>]*>Tiers mode</button>')
        self.assertRegex(html, r'aria-checked="false" data-act="sxtic"[^>]*data-v="free"[^>]*>Free mode</button>')
        self.assertNotIn("Tiers in cells", html)
        tiers_now, free, free_again, tiers_back = out["after"]
        self.assertIsNone(tiers_now)  # the mode already shown: no draft
        self.assertIs(free["tiers_in_cells"], False)
        cell, tiers = free["tables"]["execution"]["balanced"]["hard"], free["tiers"]
        self.assertEqual({k: cell[k] for k in ("model", "effort")}, tiers[cell["tier"]])  # the switch changes no route
        self.assertEqual(free_again, free)
        self.assertIs(tiers_back["tiers_in_cells"], True)

    def test_project_switch_saves_free_mode_with_the_tier_copies(self):
        out = run_node(MODE_SWITCH_JS, "app.js", "task-views.js", "settings.js", data=self.answer(),
                       args=["project", "free"])
        self.assertIn(">Free mode</button>", out["html"])
        self.assertEqual(len(out["posts"]), 1)
        pairs = out["posts"][0]
        self.assertEqual(pairs[0], "tiers-in-cells.claude=off")
        self.assertTrue(any(p.startswith("routing.claude.execution.balanced.hard=") for p in pairs[1:]), pairs)


class HoldByTests(ViewerServerCase):
    def test_a_hold_from_the_viewer_is_logged_by_viewer_and_from_the_cli_by_cli(self):
        """[HOLD-BY]."""
        sb = self.sandbox()
        task = plan(sb, "held", [("ONE", ""), ("TWO", "ONE")])
        sb.sae("start", "held")
        view = self.view(sb, "held")
        port, key, token = view["port"], view["repo"], self.token(view["port"])
        status, answer, _ = self.post(port, "hold", {"repo": key, "task": "held", "job": "ONE", "reason": "look"}, token)
        self.assertEqual((status, answer["ok"]), (200, True), answer)
        self.post(port, "hold", {"repo": key, "task": "held", "job": "ONE", "release": True}, token)
        sb.sae("hold", "held", "TWO", "--reason", "cli")
        holds = [(e["type"], e["job"], e["by"]) for e in sb.events(task) if e["type"].startswith("hold.")]
        self.assertEqual(holds, [("hold.set", "ONE", "viewer"), ("hold.released", "ONE", "viewer"),
                                 ("hold.set", "TWO", "cli")])


class StatePathTests(ViewerServerCase):
    def test_a_state_path_below_a_file_is_a_refusal_with_the_start_command(self):
        """[VIEWER-STATE-PATH]: no traceback; the fallback and the start command, as for an unwritable folder."""
        sb = self.sandbox()
        task = sb.new_task("Blocked", "blocked")
        blocked = sb.tmp / "blocked"
        blocked.write_text("a file\n")
        env = dict(sb.env, SAE_STATE_DIR=str(blocked / "viewer-state"))
        proc = subprocess.run([sys.executable, str(SAE), "view", "blocked"], cwd=sb.repo, env=env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn("The viewer cannot start here", proc.stderr)
        self.assertIn(f"view {task} --open", proc.stderr)
        self.assertEqual(blocked.read_text(), "a file\n")


if __name__ == "__main__":
    unittest.main()
