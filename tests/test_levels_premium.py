"""Levels are economy, balanced, premium; files that still say `max` are read as premium.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [LEVEL-NAMES], [DECISION-LEVEL-PREMIUM], [EDGE-OLD-TASKS].
"""

from __future__ import annotations

import json
import unittest

from saetest import config_for, old_level_names
from test_viewer_server import ViewerServerCase, request


def old_settings(sb, task: str) -> None:
    """Rewrite a task's settings.json and its last seen settings as an older sae left them."""
    folder = sb.task_dir(task)
    settings = json.loads((folder / "settings.json").read_text())
    settings["routing"] = {"claude": {"tables": {"execution": {"premium": {"hard": {"tier": "L1"}}}}}}
    (folder / "settings.json").write_text(json.dumps(old_level_names(settings)))
    state = json.loads((folder / "state.json").read_text())
    state["task"]["settings_seen"] = old_level_names(settings)
    (folder / "state.json").write_text(json.dumps(state))


class OldLevelNameTests(ViewerServerCase):
    def old_config(self, sb, project: dict | None = None) -> None:
        config = config_for(sb.worktrees)
        if project is not None:
            config["projects"] = {str(sb.repo.resolve()): project}
        sb.config.write_text(json.dumps(old_level_names(config)))
        self.assertIn('"max"', sb.config.read_text())

    def test_a_config_with_max_loads_and_new_tasks_say_premium(self):
        sb = self.sandbox()
        self.old_config(sb, {"defaults": {"levels": {"execution": "premium"}},
                             "routing": {"claude": {"tables": {"execution": {"premium": {"hard": {"tier": "L1"}}}}}}})
        task = sb.new_task("Old config", "old-config")
        settings = json.loads((sb.task_dir(task) / "settings.json").read_text())
        self.assertEqual(settings["levels"], {"research": "balanced", "planning": "premium",
                                              "execution": "premium", "review": "premium"})
        self.assertIn("  planning         premium\n", sb.sae("status", "old-config").stdout)
        self.assertEqual(sb.json("project", "show")["values"],
                         {"execution": "premium", "routing.claude.tables.execution.premium.hard": {"tier": "L1"}})
        shown = sb.sae("setup", "show").stdout
        self.assertRegex(shown, r"(?m)^\W*premium\b")
        self.assertNotRegex(shown, r"(?m)^\W*max\b")

    def test_a_settings_json_with_max_loads_shows_premium_and_is_written_as_premium(self):
        sb = self.sandbox()
        task = sb.new_task("Old task", "old-task")
        old_settings(sb, task)
        folder = sb.task_dir(task)
        events = len((folder / "events.jsonl").read_text().splitlines())
        status = sb.json("status", "old-task")
        self.assertEqual(status["settings"]["levels"]["planning"], "premium")
        self.assertIn("  planning         premium\n", sb.sae("status", "old-task").stdout)
        sb.sae("next", "old-task")  # a writing load: the rename is no external settings change
        self.assertNotIn('"by": "external"', "\n".join((folder / "events.jsonl").read_text().splitlines()[events:]))
        sb.sae("set", "old-task", "interaction=auto")
        written = json.loads((folder / "settings.json").read_text())
        self.assertEqual(written["levels"]["review"], "premium")
        self.assertEqual(written["routing"], {"claude": {"tables": {"execution": {"premium": {"hard": {"tier": "L1"}}}}}})
        self.assertNotIn('"max"', (folder / "settings.json").read_text())

    def test_set_project_set_and_setup_save_write_premium_for_max(self):
        sb = self.sandbox()
        task = sb.new_task("Set", "set-max")
        sb.sae("set", "set-max", "planning=max", "routing.claude.review.max.hard=L1")
        written = json.loads((sb.task_dir(task) / "settings.json").read_text())
        self.assertEqual(written["levels"]["planning"], "premium")
        self.assertEqual(written["routing"]["claude"]["tables"]["review"], {"premium": {"hard": {"tier": "L1"}}})
        sb.sae("project", "set", "execution=max")
        self.assertEqual(json.loads(sb.config.read_text())["projects"][str(sb.repo.resolve())]["defaults"],
                         {"levels": {"execution": "premium"}})
        sb.sae("setup", "save", stdin=json.dumps(old_level_names(config_for(sb.worktrees))))
        saved = json.loads(sb.config.read_text())
        self.assertEqual(saved["defaults"]["levels"]["review"], "premium")
        self.assertEqual(sorted(saved["routing"]["codex"]["tables"]["planning"]), ["balanced", "economy", "premium"])
        self.assertNotIn('"max": {', sb.config.read_text())
        self.assertNotIn('": "max",', sb.config.read_text())

    def test_the_viewer_serves_premium_for_old_configs_and_tasks(self):
        sb = self.sandbox()
        task = sb.new_task("Old task", "old-task")
        old_settings(sb, task)
        self.old_config(sb)
        view = self.view(sb)
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertNotIn("error", data)
        self.assertEqual(data["settings"]["levels"]["planning"], "premium")
        _, answer, _ = request(view["port"], "GET", f"/api/settings?repo={view['repo']}&task={task}")
        self.assertEqual(answer["task_settings"]["levels"]["review"], "premium")
        self.assertEqual(answer["config"]["defaults"]["levels"]["planning"], "premium")
        self.assertEqual(sorted(answer["routing"]["claude"]["tables"]["execution"]),
                         ["balanced", "economy", "premium"])
        self.assertEqual(answer["routing"]["claude"]["tables"]["execution"]["premium"]["hard"],
                         {"value": {"tier": "L1"}, "source": "task"})
        self.assertEqual(sorted(answer["config"]["routing"]["claude"]["tables"]["review"]),
                         ["balanced", "economy", "premium"])


if __name__ == "__main__":
    unittest.main()
