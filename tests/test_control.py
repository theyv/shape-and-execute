"""Owner control: holds, next-step cards, the process map, read-only commands.

[HOLD-AFTER-JOB], [FLOW-HOLD], [EDGE-HOLD-ON-RUNNING], [OUT-NEXT-STEP-CARD], [OUT-MAP-LAYOUT],
[SETTINGS-VISIBLE], [RESUME-HARNESS-HINT], [READ-ONLY-COMMANDS].
"""

from __future__ import annotations

import os
import stat
import unittest
from pathlib import Path

from saetest import Sandbox, SaeTestCase, dispatch_workspace


class ControlCase(SaeTestCase):
    def planned(self, sb: Sandbox, slug: str, jobs: list[tuple], settings: tuple = ()) -> str:
        task = sb.new_task(slug, slug)
        if settings:
            sb.sae("set", slug, *settings)
        for job_id, needs in jobs:
            sb.sae("job", "add", slug, job_id, "--kind", "implementation", *(["--needs", needs] if needs else []))
            sb.job_file(task, job_id, objective=f"Build the {job_id.lower()} part of the demo.")
        sb.approve_plan(slug)
        return task

    def finish_writer(self, sb: Sandbox, task: str, slug: str, job: str, ws: Path) -> str:
        sb.work(ws, f"{job.lower()}.txt", f"{job}\n", f"{job}: work")
        sb.result(task, f"jobs/{job}.result.md", status="done", summary="ok", validation="pass", changes="made")
        return sb.sae("collect", slug, job).stdout


class HoldTests(ControlCase):
    def test_flow_hold_in_full_auto(self):
        """[FLOW-HOLD]: a hold set before start stops dispatching once VERIFY is done and merged."""
        sb = self.sandbox()
        task = self.planned(sb, "holdflow", [("VERIFY", ""), ("OTHER", ""), ("NEXT", "VERIFY")],
                            settings=("interaction=full-auto",))
        sb.sae("hold", "holdflow", "NEXT", code=0)
        sb.sae("hold", "holdflow", "NEXT", "--release")
        sb.sae("hold", "holdflow", "NOPE", code=1)  # a hold needs an existing job
        out = sb.sae("hold", "holdflow", "VERIFY", "--reason", "check first").stdout
        self.assertIn("sae hold", out)
        sb.sae("start", "holdflow")
        ws = dispatch_workspace(sb, task, "VERIFY")
        self.assertIn("VERIFY", sb.sae("status", "holdflow").stdout.split("Holds:")[1])
        self.finish_writer(sb, task, "holdflow", "VERIFY", ws)
        self.assertTrue(sb.state(task)["jobs"]["VERIFY"]["merged"])
        nxt = sb.json("next", "holdflow")
        self.assertEqual(nxt["ready"], [])
        self.assertEqual(nxt["holds_active"], ["VERIFY"])
        self.assertEqual(nxt["holds"][0]["reason"], "check first")
        text = sb.sae("next", "holdflow").stdout
        self.assertIn("Hold after VERIFY", text)
        self.assertIn(f"sae hold {task} VERIFY --release", text)
        current = next(line for line in text.splitlines() if "►" in line)
        self.assertIn("hold after VERIFY", current)  # the map's current step names it
        refused = sb.sae("dispatch", "holdflow", "OTHER", code=3).stderr
        self.assertIn("--release", refused)
        self.assertIn("(active)", sb.sae("status", "holdflow").stdout)
        sb.sae("hold", "holdflow", "VERIFY", "--release")
        self.assertEqual(sorted(r["id"] for r in sb.json("next", "holdflow")["ready"]), ["NEXT", "OTHER"])
        types = [e["type"] for e in sb.events(task)]
        self.assertIn("hold.set", types)
        self.assertIn("hold.released", types)

    def test_hold_set_while_a_dependant_runs(self):
        """[EDGE-HOLD-ON-RUNNING]: running jobs finish, are collected and merged; new ones wait."""
        sb = self.sandbox()
        task = self.planned(sb, "holdrun", [("A", ""), ("B", ""), ("C", "A")])
        sb.sae("start", "holdrun")
        ws_a = dispatch_workspace(sb, task, "A")
        ws_b = dispatch_workspace(sb, task, "B")
        sb.sae("hold", "holdrun", "A")
        self.finish_writer(sb, task, "holdrun", "A", ws_a)
        sb.sae("dispatch", "holdrun", "C", code=3)
        self.finish_writer(sb, task, "holdrun", "B", ws_b)  # B ran before the hold was active
        jobs = sb.state(task)["jobs"]
        self.assertTrue(jobs["B"]["merged"])
        self.assertEqual(jobs["C"]["status"], "pending")
        self.assertEqual(sb.json("next", "holdrun")["ready"], [])


class CardAndMapTests(ControlCase):
    def test_removed_review_point_is_on_the_next_card(self):
        sb = self.sandbox(points=["spec", "plan"])
        task = sb.new_task("Cards", "cards")
        (sb.task_dir(task) / "specs.md").write_text("# Spec\n\n## Requirements\n\n### [ONE] One\n"
                                                     "Acceptance:\n- [ ] one\n")
        nxt = sb.json("next", "cards")
        self.assertEqual([r["id"] for r in nxt["ready"]], ["REVIEW-SPEC"])
        self.assertIn("NEXT STEP · spec review · 1 job", nxt["card"]["text"])
        self.assertNotIn("REVIEW-SPEC", sb.state(task)["jobs"])  # next only prints the card
        sb.sae("dispatch", "cards", "REVIEW-SPEC")
        state = sb.state(task)
        self.assertEqual(state["task"]["last_card"]["jobs"], ["REVIEW-SPEC"])
        self.assertIn("card.shown", [e["type"] for e in sb.events(task)])
        sb.result(task, "reviews/REVIEW-SPEC.md", target="spec", verdict="pass")
        sb.sae("collect", "cards", "REVIEW-SPEC")
        sb.sae("approve", "cards", "spec")
        sb.sae("set", "cards", "review=spec")
        sb.sae("job", "add", "cards", "PLAN", "--kind", "planning")
        sb.job_file(task, "PLAN", objective="Plan the jobs. Then stop.")
        card = sb.json("next", "cards")["card"]
        self.assertIn("NEXT STEP · planner · 1 job", card["text"])
        self.assertIn("review points: plan removed", card["changes"])
        self.assertIn("Plan the jobs.", card["text"])
        self.assertNotIn("Then stop", card["text"])
        sb.sae("dispatch", "cards", "PLAN")
        sb.sae("dispatch", "cards", "PLAN", "--resume", "--reason", "follow-up")
        self.assertEqual(sb.json("next", "cards")["card"], None)  # PLAN is running, nothing ready

    def test_start_card(self):
        sb = self.sandbox(points=["plan", "selected-jobs"])
        task = sb.new_task("Width", "width")
        sb.sae("approve", "width", "spec")
        long = ("Make the status page show every claim with its current state and the next step the "
                "customer has to take, in plain words.")
        sb.sae("job", "add", "width", "A-VERY-LONG-JOB-IDENTIFIER-FOR-WIDTH", "--kind", "implementation", "--review")
        sb.job_file(task, "A-VERY-LONG-JOB-IDENTIFIER-FOR-WIDTH", objective=long)
        sb.sae("set", "width", "review=plan")  # the flagged job loses its review
        sb.sae("dispatch", "width", "REVIEW-PLAN")
        sb.result(task, "reviews/REVIEW-PLAN.md", target="plan", verdict="pass")
        sb.sae("collect", "width", "REVIEW-PLAN")
        sb.sae("approve", "width", "plan")
        start = sb.sae("start", "width").stdout
        self.assertIn("NEXT STEP · start of execution · 1 job", start)
        self.assertIn("Flagged, but no job review will run: A-VERY-LONG-JOB-IDENTIFIER-FOR-WIDTH", start)
        self.assertIn("--harness claude|codex", start)
        self.assertEqual(sb.state(task)["task"]["last_card"]["phase"], "executing")  # start records it
        nxt = sb.sae("next", "width").stdout
        self.assertNotIn("NEXT STEP", nxt)  # recorded: an ordinary writer gets no new card

    def test_new_set_job_add_and_setup_show_output(self):
        """The settings that `new` and `set` print, the `job add --review` warning and
        `sae setup show`."""
        sb = self.sandbox(points=["spec", "plan", "integration"], provider="cross-harness")
        new = sb.sae("new", "Width of the settings", "--slug", "widths").stdout
        changed = sb.sae("set", "widths", "interaction=collaborative", "task-difficulty=hard").stdout
        same = sb.sae("set", "widths", "interaction=collaborative").stdout
        added = sb.sae("job", "add", "widths", "A-VERY-LONG-JOB-IDENTIFIER-FOR-WIDTH", "--kind", "implementation",
                       "--review").stdout
        shown = sb.sae("setup", "show").stdout
        self.assertIn("Settings\n  interaction      critical-only\n", new)
        self.assertIn("  interaction      collaborative\n", changed)
        self.assertIn("Settings (unchanged)\n", same)
        self.assertIn("job reviews are off", added)
        self.assertIn("Codex subagent cap", shown)

    def test_map_with_review_points_off(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Map", "mapoff")
        lines = sb.json("status", "mapoff")["map"]
        self.assertEqual(lines[:3], ["💡 SHAPE", "✓ intake | ► research | □ spec", "– spec-review (off) | □ spec approval"])
        self.assertEqual(lines[-4:], ["🔨 EXECUTE", "□ jobs 0/0 | – job-reviews (off)",
                                      "– integration-review (off) | – final-validation (none)", "□ finish"])
        sb.sae("approve", "mapoff", "spec")
        sb.sae("job", "add", "mapoff", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        text = sb.sae("status", "mapoff").stdout
        self.assertIn("📐 PLAN\n– planner (none) | ► plan-review | □ plan approval\n", text)
        self.assertIn("– spec-review (off)", text)
        self.assertIn("\n        ↓\n📐 PLAN", text)  # an arrow line between phases


class ReadOnlyTests(ControlCase):
    def test_status_next_check_without_write_permission(self):
        sb = self.sandbox()
        task = self.planned(sb, "ro", [("ONE", "")])
        sb.sae("start", "ro")
        folder = sb.task_dir(task)
        before = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
        tasks_dir = folder.parent
        modes = {}
        for path in (folder, tasks_dir, *folder.rglob("*")):
            modes[path] = path.stat().st_mode
            os.chmod(path, path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        try:
            self.assertIn("ro", sb.sae("status", "ro").stdout)
            self.assertIn("Ready", sb.sae("next", "ro").stdout)
            sb.sae("check", "ro")
            sb.sae("--help")
            sb.sae("status", "--help")
        finally:
            for path, mode in sorted(modes.items(), key=lambda kv: len(kv[0].parts)):
                os.chmod(path, mode)
        self.assertFalse((folder / ".lock").exists() and ".lock" not in before)
        after = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
