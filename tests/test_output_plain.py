"""Plain owner output: unwrapped prose and the fixed-layout blocks.

[OUT-NO-PROSE-WRAP], [OUT-MAP-LAYOUT], [OUT-SETTINGS-CARD], [OUT-NEXT-STEP-CARD], [VIEWER-RENAME].
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from types import SimpleNamespace

from saetest import SCRIPTS, SKILL_DIR, SaeTestCase

sys.path.insert(0, str(SCRIPTS))
from sae_lib.cli import build_parser  # noqa: E402
from sae_lib.common import emit  # noqa: E402
from sae_lib.prompts import external_review_command  # noqa: E402

SHAPING_MAP = """\
💡 SHAPE
✓ intake | ► research | □ spec
□ spec-review | □ spec approval
        ↓
📐 PLAN
□ planner | □ plan-review | □ plan approval
        ↓
🔨 EXECUTE
□ jobs 0/0 | – job-reviews (off)
□ integration-review | – final-validation (none)
□ finish"""

PLANNING_MAP = """\
💡 SHAPE
✓ intake | – research (none) | ✓ spec
– spec-review (off) | ✓ spec approval
        ↓
📐 PLAN
– planner (none) | ► plan-review | □ plan approval
        ↓
🔨 EXECUTE
□ jobs 0/1 | – job-reviews (off)
– integration-review (off) | – final-validation (none)
□ finish"""

EXECUTING_MAP = """\
💡 SHAPE
✓ intake | – research (none) | ✓ spec
– spec-review (off) | ✓ spec approval
        ↓
📐 PLAN
– planner (none) | ✓ plan-review | ✓ plan approval
        ↓
🔨 EXECUTE
► jobs 0/1 | – job-reviews (off)
– integration-review (off) | – final-validation (none)
□ finish"""


def subparser(parser: argparse.ArgumentParser, *names: str) -> argparse.ArgumentParser:
    for name in names:
        action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        parser = action.choices[name]
    return parser


class MapLayoutTests(SaeTestCase):
    def test_status_and_next_print_the_map_template_in_shaping(self):
        sb = self.sandbox(points=["spec", "plan", "integration"])
        sb.new_task("Map", "map")
        for command in ("status", "next"):
            self.assertIn(SHAPING_MAP, sb.sae(command, "map").stdout)
        self.assertEqual(sb.json("status", "map")["map"], SHAPING_MAP.splitlines())

    def test_status_and_next_print_the_map_template_in_planning_and_executing(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Map", "mapplan")
        sb.approve_spec("mapplan")
        sb.sae("job", "add", "mapplan", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        for command in ("status", "next"):
            self.assertIn(PLANNING_MAP, sb.sae(command, "mapplan").stdout)
        sb.sae("dispatch", "mapplan", "REVIEW-PLAN")
        sb.result(task, "reviews/REVIEW-PLAN.md", target="plan", verdict="pass")
        sb.sae("collect", "mapplan", "REVIEW-PLAN")
        sb.sae("approve", "mapplan", "plan")
        self.assertIn(EXECUTING_MAP, sb.sae("start", "mapplan").stdout)
        for command in ("status", "next"):
            out = sb.sae(command, "mapplan").stdout
            self.assertIn(EXECUTING_MAP, out)
            self.assertNotIn("⬥", out)


class SettingsCardTests(SaeTestCase):
    def test_new_set_and_status_print_one_setting_per_line(self):
        sb = self.sandbox(points=["spec", "plan", "integration"], provider="codex")
        card = ("Settings\n"
                "  interaction      critical-only\n"
                "  research         balanced\n"
                "  planning         max\n"
                "  execution        balanced\n"
                "  review points    spec, plan, integration\n"
                "  review           max · codex\n"
                "  task difficulty  normal")
        self.assertIn(card + "\n", sb.sae("new", "Card", "--slug", "card").stdout)
        self.assertIn(card + "\n", sb.sae("status", "card").stdout)
        changed = sb.sae("set", "card", "interaction=auto", "task-difficulty=hard", "review=off").stdout
        self.assertEqual(changed, "Settings\n"
                                  "  interaction      auto\n"
                                  "  research         balanced\n"
                                  "  planning         max\n"
                                  "  execution        balanced\n"
                                  "  review points    off\n"
                                  "  task difficulty  hard\n")
        same = sb.sae("set", "card", "interaction=auto").stdout
        self.assertTrue(same.startswith("Settings (unchanged)\n  interaction      auto\n"), same)


class NextStepCardTests(SaeTestCase):
    def test_header_reads_next_step_and_a_long_purpose_prints_whole(self):
        sb = self.sandbox(points=[])
        task = sb.new_task("Card", "nextstep")
        sb.approve_spec("nextstep")
        sb.sae("job", "add", "nextstep", "PLAN", "--kind", "planning")
        purpose = ("Plan the jobs of the status page so that every claim shows its current state and the "
                   "next step the customer has to take, in plain words.")
        sb.job_file(task, "PLAN", objective=purpose + " Then stop.")
        text = sb.json("next", "nextstep")["card"]["text"]
        self.assertTrue(text.startswith("NEXT STEP · planner · 1 job\n"), text)
        self.assertIn("\n  " + purpose + "\n", text)
        self.assertIn("First next-step card of this task.", text)
        self.assertNotIn("Then stop", text)


class PlainProseTests(SaeTestCase):
    def test_usage_error_prints_the_argparse_usage_unchanged(self):
        sb = self.sandbox()
        sb.new_task("Usage", "usage")
        err = sb.sae("job", "add", "usage", "ONE", "--kind", "review", code=1).stderr
        usage = subparser(build_parser(), "job", "add").format_usage()
        self.assertTrue(err.startswith(usage), err)
        self.assertIn("{research,planning,implementation,integration,validation}", err)

    def test_start_keeps_the_git_command_for_an_existing_branch_in_one_piece(self):
        sb = self.sandbox()
        task = sb.new_task("Branch exists already for this long task name", "branch-exists-already-long")
        sb.approve_spec("branch-exists-already-long")
        sb.sae("job", "add", "branch-exists-already-long", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        sb.sae("approve", "branch-exists-already-long", "plan")
        sb.git("branch", f"task/{task}")
        err = sb.sae("start", "branch-exists-already-long", code=4).stderr
        self.assertIn(f"\n  git branch -D task/{task}\n", err)

    def test_long_prose_is_one_line_and_a_doctor_fix_indents_under_its_label(self):
        sb = self.sandbox(write_config=False)
        out = sb.sae("doctor", code=2).stdout
        self.assertIn("    fix: Run setup mode:\n      /shape-and-execute setup\n", out)
        text = "Owner notice: " + "long prose " * 20 + "sae merge would overwrite this."
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            emit(argparse.Namespace(json=False), text)
        self.assertEqual(output.getvalue(), text + "\n")

    def test_external_review_commands_copy_as_one_line_and_preserve_prompt(self):
        sb = self.sandbox()
        fake_bin = self.tmp / "fake-harness-bin"
        fake_bin.mkdir()
        script = (f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                  "args = sys.argv[1:]\n"
                  "if '-o' in args:\n    Path(args[args.index('-o') + 1]).write_text(json.dumps(args))\n"
                  "else:\n    print(json.dumps(args))\n")
        for harness in ("claude", "codex"):
            executable = fake_bin / harness
            executable.write_text(script)
            executable.chmod(0o755)
        env = dict(sb.env, PATH=str(fake_bin) + os.pathsep + sb.env["PATH"])
        task = SimpleNamespace(root=sb.repo, dir=sb.repo / ".tasks" / "example task",
                               jobs={"REVIEW": {"kind": "review"}})
        prompt = "First line with 'quotes', \"quotes\", `touch injected`, $(touch injected) and \\literal\nSecond line\rThird"
        for harness in ("claude", "codex"):
            with self.subTest(harness=harness):
                command = external_review_command(task, "REVIEW", {"harness": harness, "model": "fake", "effort": "high"}, prompt)
                self.assertEqual(len(command.splitlines()), 1)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    emit(argparse.Namespace(json=False), "COMMAND:\n" + command)
                self.assertEqual(output.getvalue(), "COMMAND:\n" + command + "\n")
                proc = subprocess.run(command, shell=True, cwd=sb.repo, env=env, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                args = json.loads((task.dir / "reviews" / "REVIEW.md").read_text())
                self.assertIn(prompt, args)
                self.assertFalse((sb.repo / "injected").exists())


class ViewerRenameTests(SaeTestCase):
    def test_doctor_repo_checks_viewer_files_and_known_repository(self):
        sb = self.sandbox()
        sb.new_task("Viewer", "viewer")
        self.assertEqual((sb.repo / ".tasks" / ".gitignore").read_text(), ".lock\n")
        out = sb.sae("doctor", "--repo", code=1).stdout  # the sandbox has no Codex subagent cap
        self.assertIn("✓ viewer files exist; repository known", out)
        repos = json.loads((sb.viewer_state / "repos.json").read_text())["repos"]
        self.assertEqual(len(repos), 1)


if __name__ == "__main__":
    unittest.main()
