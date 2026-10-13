"""The review-round limit as a setting and the clearer verify-limit label: `max-review-rounds`
parks a job (job reviews) or the task (integration review) after that many changes-required
rounds; a settings.json without the key reads as 3; the Settings tab and the header show both
limits.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [REVIEW-ROUNDS-LIMIT], [SETTINGS-VERIFY-LABEL], [AMEND-4].
"""

from __future__ import annotations

import json
import shutil
import sys
import unittest

from saetest import SCRIPTS, Sandbox, SaeTestCase
from test_reviews import ReviewFlowCase
from test_viewer_server import run_node

sys.path.insert(0, str(SCRIPTS))
from sae_lib.config import max_review_rounds, settings_errors  # noqa: E402

# app.js, task-views.js and settings.js in node: the editable header card, the read-only header
# pairs and the Task level of the Settings tab for one task's data.
SETTINGS_JS = r"""
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
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
console.log(JSON.stringify(vm.runInContext(`readHash(); S.repo = "R"; S.task = TASK.state.task.id; TASKS[S.task] = TASK;
  ({card: headerCard(TASK), pairs: setPairs(TASK, settingsOf(TASK)), tab: sxDefaults("task"),
    help: {verify: HELP.verify, rounds: HELP.rounds}})`, ctx)));
"""


class RoundsCase(ReviewFlowCase):
    def job_rounds(self, sb: Sandbox, slug: str, settings: list[str], *, drop_key: bool = False) -> tuple[str, list[str]]:
        """CORE under review: changes-required, fix, … until it parks (at most five rounds).
        Returns the task and the collect output of every round."""
        task = self.planned(sb, slug, [("CORE", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs", *settings])
        if drop_key:  # a settings.json that an older sae wrote
            path = sb.task_dir(task) / "settings.json"
            data = json.loads(path.read_text())
            del data["max_review_rounds"]
            path.write_text(json.dumps(data))
        self.run_writer(sb, task, slug, "CORE")
        outs = []
        for n in range(1, 6):
            review_id = "REVIEW-CORE" if n == 1 else f"REVIEW-CORE-{n}"
            outs.append(self.review(sb, task, slug, review_id, "CORE", "changes-required")["collect"])
            if sb.state(task)["jobs"]["CORE"]["status"] == "parked":
                break
            fix = f"CORE-FIX-{n}"
            sb.sae("job", "add", slug, fix, "--kind", "implementation", "--fix-of", "CORE", "--reason", "fix")
            sb.job_file(task, fix)
            self.run_writer(sb, task, slug, fix)
        return task, outs

    def integration_rounds(self, sb: Sandbox, slug: str, settings: list[str], *, drop_key: bool = False) -> list[str]:
        """Integration review rounds, each changes-required, until the task parks (at most five)."""
        task = self.integration_task(sb, slug)
        if settings:
            sb.sae("set", slug, *settings)
        if drop_key:
            path = sb.task_dir(task) / "settings.json"
            data = json.loads(path.read_text())
            data.pop("max_review_rounds", None)
            path.write_text(json.dumps(data))
        outs = []
        for n in range(1, 6):
            review_id = "REVIEW-INTEGRATION" if n == 1 else f"REVIEW-INTEGRATION-{n}"
            outs.append(self.review(sb, task, slug, review_id, "integration", "changes-required")["collect"])
            if sb.json("next", slug)["parked_task"]:
                break
            fix = f"INTEGRATION-FIX-{n}"
            sb.sae("job", "add", slug, fix, "--kind", "implementation", "--fix-of", review_id, "--reason", "fix")
            sb.job_file(task, fix)
            self.run_writer(sb, task, slug, fix)
        return outs


class JobReviewLimitTests(RoundsCase):
    def test_three_rounds_park_after_the_third_not_the_second(self):
        sb = self.sandbox()
        task, outs = self.job_rounds(sb, "three", ["max-review-rounds=3"])
        self.assertEqual(len(outs), 3)
        self.assertNotIn("parked", outs[1])
        self.assertIn("CORE parked: 3 review rounds required changes (max-review-rounds is 3)", outs[2])
        self.assertIn(f"sae set {task} max-review-rounds=4", outs[2])
        self.assertIn("max-review-rounds 3", sb.state(task)["jobs"]["CORE"]["summary"])

    def test_a_settings_json_without_the_key_parks_after_the_third_round(self):
        sb = self.sandbox()
        _, outs = self.job_rounds(sb, "oldjob", [], drop_key=True)
        self.assertEqual(len(outs), 3)
        self.assertIn("max-review-rounds is 3", outs[2])

    def test_one_round_parks_at_once(self):
        sb = self.sandbox()
        _, outs = self.job_rounds(sb, "one", ["max-review-rounds=1"])
        self.assertEqual(len(outs), 1)
        self.assertIn("max-review-rounds=2", outs[0])


class IntegrationReviewLimitTests(RoundsCase):
    def test_three_integration_rounds_park_after_the_third(self):
        sb = self.sandbox()
        outs = self.integration_rounds(sb, "intthree", ["max-review-rounds=3"])
        self.assertEqual(len(outs), 3)
        self.assertNotIn("The task is parked", outs[1])
        self.assertIn("The task is parked", outs[2])
        self.assertIn("max-review-rounds is 3", outs[2])

    def test_a_settings_json_without_the_key_parks_after_the_third_integration_round(self):
        sb = self.sandbox()
        outs = self.integration_rounds(sb, "intold", [], drop_key=True)
        self.assertEqual(len(outs), 3)
        self.assertIn("The task is parked", outs[2])


class SettingTests(SaeTestCase):
    def test_new_task_set_bounds_help_and_old_settings(self):
        sb = self.sandbox()
        task = sb.new_task("Limits", "limits")
        path = sb.task_dir(task) / "settings.json"
        self.assertEqual(json.loads(path.read_text())["max_review_rounds"], 3)
        sb.sae("set", "limits", "max-review-rounds=0", code=1)
        sb.sae("set", "limits", "max-review-rounds=11", code=1)
        sb.sae("set", "limits", "max-review-rounds=x", code=1)
        sb.sae("set", "limits", "max-review-rounds=5")
        self.assertEqual(json.loads(path.read_text())["max_review_rounds"], 5)
        changed = [e for e in sb.events(task) if e["type"] == "settings.changed"]
        self.assertEqual(changed[-1]["changes"]["max_review_rounds"], [3, 5])
        self.assertIn("max-review-rounds (1-10, default 3", sb.sae("set", "--help").stdout)
        self.assertEqual(max_review_rounds({}), 3)
        self.assertEqual(settings_errors({"max_review_rounds": True})[-1],
                         "max_review_rounds must be an integer from 1 to 10")

    def test_a_card_recorded_before_the_setting_shows_no_change(self):
        sb = self.sandbox()
        task = sb.new_task("Old card", "oldcard")
        sb.sae("job", "add", "oldcard", "A", "--kind", "implementation")
        sb.job_file(task, "A")
        sb.approve_plan("oldcard")
        sb.sae("start", "oldcard")
        state_path = sb.task_dir(task) / "state.json"
        state = json.loads(state_path.read_text())
        card = state["task"].get("last_card") or {}
        snapshot = card.get("settings") or {}
        if "max_review_rounds" not in snapshot:
            self.skipTest("the recorded card keeps no settings snapshot")
        del snapshot["max_review_rounds"]
        state_path.write_text(json.dumps(state))
        self.assertNotIn("max_review_rounds", sb.sae("next", "oldcard").stdout)


def task_data(settings: dict, *, phase: str = "executing", default=None) -> dict:
    data = {"state": {"task": {"id": "2026-10-01-1000--limits", "phase": phase, "title": "Limits"}, "jobs": {}},
            "settings": settings, "settings_default_max_verify_failures": 3, "events": [], "files": []}
    if default is not None:
        data["settings_default_max_review_rounds"] = default
    return data


SETTINGS = {"schema": 2, "interaction": "auto", "max_verify_failures": 4,
            "levels": {"research": "balanced", "planning": "balanced", "execution": "balanced", "review": "balanced"},
            "review": {"points": ["integration"], "provider": "claude"}}


@unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
class ViewerTests(unittest.TestCase):
    def render(self, data: dict) -> dict:
        return run_node(SETTINGS_JS, "app.js", "task-views.js", "settings.js", data=data)

    def test_settings_tab_names_both_limits_with_help(self):
        out = self.render(task_data({**SETTINGS, "max_review_rounds": 5}, default=3))
        self.assertIn("Tests verify limit", out["tab"])
        self.assertNotIn(">Verify limit<", out["tab"])
        self.assertIn("Max review rounds", out["tab"])
        self.assertIn('data-k="task|max-review-rounds" value="5"', out["tab"])
        self.assertIn('data-k="task|max-verify-failures" value="4"', out["tab"])
        self.assertIn("not review rounds", out["help"]["verify"])
        self.assertIn("<code>verify</code>", out["help"]["verify"])
        self.assertIn("changes-required", out["help"]["rounds"])
        # the header keeps the short "verify limit" and adds "review limit"
        self.assertIn("<span>verify limit</span> <b>4</b>", out["card"])
        self.assertIn("<span>review limit</span> <b>5</b>", out["card"])
        self.assertIn(["verify limit", 4], out["pairs"])
        self.assertIn(["review limit", 5], out["pairs"])

    def test_an_old_task_without_the_key_shows_review_limit_3(self):
        # a done task from an older sae, served by a server with or without the default field
        for default in (3, None):
            out = self.render(task_data(dict(SETTINGS), phase="done", default=default))
            self.assertIn(["review limit", 3], out["pairs"])
            self.assertIn("<span>review limit</span> <b>3</b>", out["card"])
            self.assertIn('data-k="task|max-review-rounds" value="3"', out["tab"])


if __name__ == "__main__":
    unittest.main()
