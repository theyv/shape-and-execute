"""Viewer fixes: process map in the task data, effective difficulty in prompts and the viewer,
known Claude families in the settings answer, a state path below a file, `by` of hold events.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [VIEWER-PROCESS-MAP], [DIFFICULTY-DISPLAY], [SETTINGS-CLAUDE-FAMILIES], [VIEWER-STATE-PATH],
[HOLD-BY].
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


# app.js and task-views.js in node: the process map, the job table and the job header of one job
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
const out = vm.runInContext("({map: pmap(TASK), jobs: TAB.jobs(TASK)})", ctx);
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
        difficulty of `sae next`; the task data carries the process map of `sae status`."""
        sb = self.sandbox()
        task = self.planned(sb, "mech", [("MECH", "implementation", "", ["--difficulty", "mechanical"])],
                            settings=["review=all-jobs"])
        self.run_writer(sb, task, "mech", "MECH")
        ready = {r["id"]: r for r in sb.json("next", "mech")["ready"]}
        self.assertEqual(ready["REVIEW-MECH"]["difficulty"], "normal")
        view = self.view(sb, "mech")
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(data["difficulty"]["REVIEW-MECH"], "normal")
        self.assertEqual(data["map"], sb.json("status", "mech")["map"])
        self.assertTrue(data["map"])
        out = run_node(TASK_VIEW_JS, "app.js", "task-views.js", data=data, args=["REVIEW-MECH"])
        self.assertIn("review · normal", out["header"])
        self.assertIn('review<span class="mut"> · normal</span>', out["jobs"])
        self.assertNotIn("review · null", out["header"])
        for line in data["map"]:
            self.assertIn(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), out["map"])
        prompt = sb.json("dispatch", "mech", "REVIEW-MECH")["prompt"]
        self.assertIn("Job: REVIEW-MECH (review, normal)", prompt)

    def test_task_data_carries_the_process_map_before_execution(self):
        """[VIEWER-PROCESS-MAP]: every phase, not only executing."""
        sb = self.sandbox()
        task = sb.new_task("Shaping", "shaping")
        view = self.view(sb, "shaping")
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(data["state"]["task"]["phase"], "shaping")
        self.assertEqual(data["map"], sb.json("status", "shaping")["map"])
        self.assertTrue(data["map"])


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
