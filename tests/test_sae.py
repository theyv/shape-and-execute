"""End-to-end tests of scripts/sae.py on throwaway repositories.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Standard library only. Every test builds its own git repository, user config and worktree root
in a temporary folder; nothing outside it is touched.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path

from saetest import SCRIPTS, SKILL_DIR, Sandbox, SaeTestCase, config_for, dispatch_workspace

class HelpTests(SaeTestCase):
    def test_every_command_has_help_with_exit_codes(self):
        sb = self.sandbox()
        commands = ["new", "status", "set", "approve", "check", "start", "finish", "abandon", "view", "next",
                    "dispatch", "collect", "merge", "log", "doctor"]
        nested = [("job", "add"), ("job", "edit"), ("job", "remove"), ("decision", "new"), ("finding", "new"),
                  ("finding", "close"), ("setup", "show"), ("setup", "save"), ("setup", "snippets")]
        for args in [[c] for c in commands] + [list(n) for n in nested]:
            out = sb.sae(*args, "--help").stdout
            self.assertIn("Exit codes:", out, args)
            self.assertIn("Examples:", out, args)
        top = sb.sae("--help").stdout
        self.assertIn("5  re-run verify failed", top)

    def test_usage_error_is_exit_1(self):
        sb = self.sandbox()
        sb.sae("new", code=1)
        sb.sae("nonsense", code=1)


class TaskTests(SaeTestCase):
    def test_missing_config_is_exit_2(self):
        sb = self.sandbox(write_config=False)
        proc = sb.sae("new", "Anything", code=2)
        self.assertIn("setup", proc.stderr)
        # backlog items, help and doctor work without config
        sb.sae("new", "Later", "--backlog")
        sb.sae("doctor", code=2)

    def test_new_status_set_and_external_settings_edit(self):
        sb = self.sandbox()
        task = sb.new_task("Claims status self-service", "claims-status")
        self.assertRegex(task, r"^\d{4}-\d{2}-\d{2}-\d{4}--claims-status$")
        folder = sb.task_dir(task)
        for name in ("intent.md", "settings.json", "state.json", "events.jsonl"):
            self.assertTrue((folder / name).exists(), name)
        self.assertIn("Intent: Claims status self-service", (folder / "intent.md").read_text())
        settings = json.loads((folder / "settings.json").read_text())
        self.assertEqual(settings["max_verify_failures"], 3)
        self.assertEqual((sb.repo / ".tasks" / ".gitignore").read_text(), ".lock\n")
        self.assertEqual(sb.state(task)["task"]["orchestrator_harness"], "claude")
        status = sb.json("status", "claims-status")
        self.assertEqual(status["phase"], "shaping")
        self.assertIn("  review points    off\n", status["settings_card"])
        sb.sae("set", "claims-status", "execution=economy", "review=spec,plan", "reviewer=codex")
        sb.sae("set", "claims-status", "review=selected-jobs,all-jobs", code=1)
        sb.sae("set", "claims-status", "max-verify-failures=11", code=1)
        changed = [e for e in sb.events(task) if e["type"] == "settings.changed"]
        self.assertEqual(changed[-1]["by"], "cli")
        self.assertEqual(changed[-1]["changes"]["levels.execution"], ["balanced", "economy"])
        # a hand or viewer edit; a missing max_verify_failures means 3
        settings = json.loads((folder / "settings.json").read_text())
        settings["interaction"] = "auto"
        del settings["max_verify_failures"]
        (folder / "settings.json").write_text(json.dumps(settings))
        sb.sae("status", "claims-status")  # read-only: logs nothing
        self.assertEqual([e for e in sb.events(task) if e["type"] == "settings.changed"][-1]["by"], "cli")
        sb.sae("job", "add", "claims-status", "TOPIC", "--kind", "research")  # a writing command logs it
        external = [e for e in sb.events(task) if e["type"] == "settings.changed"][-1]
        self.assertEqual(external["by"], "external")
        self.assertEqual(external["changes"], {"interaction": ["critical-only", "auto"]})
        # invalid settings are exit 1 with the field
        settings["interaction"] = "yolo"
        (folder / "settings.json").write_text(json.dumps(settings))
        self.assertIn("interaction", sb.sae("status", "claims-status", code=1).stderr)

    def test_task_reference_must_be_unique(self):
        sb = self.sandbox()
        sb.new_task("One", "alpha-status")
        sb.new_task("Two", "beta-status")
        sb.sae("status", "status", code=1)
        sb.sae("status", "alpha-status")
        sb.sae("status", "nothing", code=1)

    def test_backlog_item_round_trip(self):
        sb = self.sandbox()
        source = sb.new_task("Source", "source-task")
        item = Path(sb.json("new", "Billing export", "--backlog", "--source", "source-task")["file"])
        self.assertTrue(item.read_text().startswith(f"---\nsource: {source}"))
        self.assertFalse(any(e["type"] == "backlog.created" for e in sb.events(source)))  # only the item knows
        sb.git("add", ".tasks/backlog")
        sb.git("commit", "-q", "-m", "backlog")
        task = sb.json("new", "Billing export", "--from", str(item.relative_to(sb.repo)))["task"]
        self.assertTrue(item.exists())  # the file stays until sae start
        intent = (sb.task_dir(task) / "intent.md").read_text()
        self.assertTrue(intent.startswith("# Intent: Billing export"))
        created = sb.events(task)[0]
        self.assertEqual(created["from"]["source"], source)
        sb.job_file(task, "WORK")
        sb.sae("job", "add", "billing-export", "WORK", "--kind", "implementation")
        sb.approve_plan("billing-export")
        sb.sae("start", "billing-export")
        log = sb.git("log", "--format=%s", "-1", f"task/{task}")
        self.assertEqual(log, f"{task}: picked up from backlog")
        wt = sb.task_worktree(task)
        self.assertEqual(sb.git("status", "--porcelain", "--", ".tasks/backlog", cwd=wt), "")
        self.assertTrue(item.exists())  # the home checkout keeps it until the owner merges
        self.assertEqual(sb.git("branch", "--show-current"), "main")


class ShapingAndPlanningTests(SaeTestCase):
    def test_spec_lint_review_and_gate(self):
        sb = self.sandbox(points=["spec", "plan"])
        task = sb.new_task("Spec work", "spec-work")
        spec = sb.task_dir(task) / "specs.md"
        spec.write_text("# Spec\n\n## Requirements\n\n### [claim-status] bad\n\n### [CLAIM-NEXT] Next step\n"
                        "Acceptance:\n- [ ] shows next step\n")
        out = sb.sae("check", "spec-work", code=3).stdout
        self.assertIn("invalid ID [claim-status]", out)
        spec.write_text("# Spec\n\n## Requirements\n\n### [CLAIM-STATUS] Status\nNo checks.\n\n"
                        "### [CLAIM-NEXT] Next step\nAcceptance:\n- [ ] shows next step\n\n"
                        "## Research basis\n- research/TOPIC.md\n")
        data = sb.json("check", "spec-work")
        self.assertIn("REVIEW-SPEC", data["due"])  # check writes nothing; dispatch adds it
        self.assertTrue(any("[CLAIM-STATUS] has no acceptance" in w for w in data["warnings"]))
        self.assertIn("REVIEW-SPEC is pending", sb.sae("approve", "spec-work", "spec", code=3).stderr)
        prompt = sb.json("dispatch", "spec-work", "REVIEW-SPEC")
        self.assertEqual(prompt["model"], "c-big")  # review level max → L3
        self.assertIn("reviewer.md", prompt["prompt"])
        self.assertIn("specs.md", prompt["prompt"])
        sb.sae("collect", "spec-work", "REVIEW-SPEC", code=1)  # no result file yet
        sb.result(task, "reviews/REVIEW-SPEC.md", target="spec", verdict="changes-required")
        sb.sae("collect", "spec-work", "REVIEW-SPEC")
        sb.approve_spec("spec-work")
        self.assertEqual(sb.state(task)["task"]["phase"], "planning")

    def test_plan_lint_and_gate(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Plan work", "plan-work")
        (sb.task_dir(task) / "specs.md").write_text("# Spec\n\n## Requirements\n\n### [EXPORT-CSV] Export\n"
                                                     "- [ ] export\n<!-- ### [IGNORED] comment -->\n")
        sb.approve_spec("plan-work")
        sb.sae("approve", "plan-work", "plan", code=3)  # no jobs
        sb.sae("job", "add", "plan-work", "A", "--kind", "implementation", "--needs", "B")
        sb.sae("job", "add", "plan-work", "B", "--kind", "implementation", "--needs", "A")
        sb.sae("job", "add", "plan-work", "bad-id", "--kind", "implementation", code=1)
        sb.sae("job", "add", "plan-work", "R", "--kind", "review", code=1)
        sb.sae("job", "add", "plan-work", "TOPIC", "--kind", "research")
        self.assertIn("## Objective", (sb.task_dir(task) / "jobs" / "TOPIC.md").read_text())  # lint needs it
        sb.sae("job", "remove", "plan-work", "TOPIC", "--reason", "template check only")
        sb.job_file(task, "A", covers=["NOPE"])
        errors = sb.json("check", "plan-work", code=3)["errors"]
        joined = "\n".join(errors)
        self.assertIn("cycle in needs", joined)
        self.assertIn("covers [NOPE]", joined)
        self.assertIn("B: the job file has no objective", joined)  # scaffolded template has no objective
        self.assertIn("requirement [EXPORT-CSV] is not covered", joined)
        sb.sae("job", "edit", "plan-work", "B", "--needs", "")
        sb.job_file(task, "A", covers=["EXPORT-CSV"], verify=["true"])
        sb.job_file(task, "B", objective="First part. Second sentence.")
        data = sb.json("check", "plan-work")
        self.assertEqual(data["due"], ["REVIEW-PLAN"])
        self.assertTrue(any("longer than one sentence" in w for w in data["warnings"]))
        self.assertTrue(any("Riskiest assumptions" in w for w in data["warnings"]))
        self.assertTrue(any("B: no verify" in w for w in data["warnings"]))
        sb.sae("approve", "plan-work", "plan", code=3)
        sb.sae("dispatch", "plan-work", "A", code=1)  # implementation does not run in planning
        sb.sae("dispatch", "plan-work", "REVIEW-PLAN")
        sb.result(task, "reviews/REVIEW-PLAN.md", target="plan", verdict="pass")
        sb.sae("collect", "plan-work", "REVIEW-PLAN")
        sb.sae("approve", "plan-work", "plan")
        sb.sae("job", "remove", "plan-work", "B", "--reason", "x", code=1)  # A needs B
        sb.sae("job", "edit", "plan-work", "A", "--needs", "")
        sb.sae("job", "remove", "plan-work", "B", "--reason", "not needed")
        self.assertTrue((sb.task_dir(task) / "jobs" / "B.removed.md").exists())


class ExecutionTests(SaeTestCase):
    def planned(self, sb: Sandbox, slug: str, jobs: list[tuple], settings: list[str] = ()) -> str:
        task = sb.new_task(slug, slug)
        if settings:
            sb.sae("set", slug, *settings)
        for job_id, kind, needs, extra, file_kwargs in jobs:
            sb.sae("job", "add", slug, job_id, "--kind", kind, *(["--needs", needs] if needs else []), *extra)
            sb.job_file(task, job_id, **file_kwargs)
        sb.approve_plan(slug)
        return task

    def test_worktrees_review_verify_and_finish(self):
        sb = self.sandbox()
        task = self.planned(sb, "wt-flow", [
            ("A", "implementation", "", ["--review"], {"scope": ["a/**"]}),
            ("B", "implementation", "", ["--difficulty", "hard"], {"verify": ["test -f b.txt && grep -q good b.txt"]}),
            ("C", "implementation", "A,B", [], {}),
            ("FINAL", "validation", "C", ["--final"], {"verify": ["test -f c.txt"]}),
        ], settings=["review=selected-jobs,integration"])
        start = sb.sae("start", "wt-flow").stdout
        self.assertIn("layout: worktrees", start)
        self.assertIn("Mode: critical-only — ask on: consequential, spec-clarification, spec-change.", start)
        self.assertEqual(sb.git("branch", "--show-current"), "main")  # the home checkout never switches
        wt = sb.task_worktree(task)
        self.assertEqual(sb.git("branch", "--show-current", cwd=wt), f"task/{task}")
        nxt = sb.json("next", "wt-flow")
        self.assertEqual(sorted(r["id"] for r in nxt["ready"]), ["A", "B"])
        # A: works outside its scope, gets reviewed, then merges
        data = sb.json("dispatch", "wt-flow", "A")
        ws_a = Path(data["workspace"])
        self.assertTrue(str(ws_a).startswith(str(sb.worktrees)))
        self.assertIn(f"Branch: job/{task}/A", data["prompt"])
        self.assertIn("Commit trailers: Task:", data["prompt"])
        self.assertNotIn("brief.md", data["prompt"])  # no brief: line omitted
        (ws_a / "a").mkdir()
        sb.work(ws_a, "a/x.txt", "a\n", "A: add a")
        sb.work(ws_a, "stray.txt", "s\n", "A: stray")
        sb.result(task, "jobs/A.result.md", status="done", summary="did A", validation="pass", changes="made")
        out = sb.sae("collect", "wt-flow", "A", "--tokens", "1000").stdout
        self.assertIn("Added REVIEW-A", out)
        self.assertIn("outside its scope: stray.txt", out)
        rev = sb.json("dispatch", "wt-flow", "REVIEW-A")
        self.assertIn(f"diff {sb.state(task)['jobs']['A']['attempts'][0]['head']}..job/{task}/A", rev["prompt"])
        sb.result(task, "reviews/REVIEW-A.md", target="A", verdict="pass-with-notes")
        sb.sae("collect", "wt-flow", "REVIEW-A")
        state = sb.state(task)
        self.assertTrue(state["jobs"]["A"]["merged"])
        self.assertFalse(ws_a.exists())  # worktree removed after merge
        # B: verify fails once (exit 5), resume, then passes
        ws_b = dispatch_workspace(sb, task, "B")
        self.assertEqual(sb.state(task)["jobs"]["B"]["attempts"][0]["model"], "c-big")  # balanced + hard → L3
        sb.work(ws_b, "b.txt", "bad\n", "B: first try")
        sb.result(task, "jobs/B.result.md", status="done", summary="did B", validation="pass", changes="made")
        proc = sb.sae("collect", "wt-flow", "B", code=5)
        self.assertIn("--resume --reason verify-failed", proc.stdout)
        self.assertTrue((sb.task_dir(task) / "jobs" / "B.verify.log").exists())
        resumed = sb.json("dispatch", "wt-flow", "B", "--resume", "--reason", "verify-failed")
        self.assertIn("B.verify.log", resumed["prompt"])
        sb.work(ws_b, "b.txt", "good\n", "B: fix")
        sb.sae("collect", "wt-flow", "B")
        self.assertTrue(sb.state(task)["jobs"]["B"]["merged"])
        # C and the final validation; the integration review comes before the final job
        ws_c = dispatch_workspace(sb, task, "C")
        self.assertTrue((ws_c / "a" / "x.txt").exists() and (ws_c / "b.txt").exists())
        sb.work(ws_c, "c.txt", "c\n", "C: add c")
        sb.result(task, "jobs/C.result.md", status="done", summary="did C", validation="pass", changes="made")
        out = sb.sae("collect", "wt-flow", "C").stdout
        self.assertIn("REVIEW-INTEGRATION", out)
        self.assertEqual([r["id"] for r in sb.json("next", "wt-flow")["ready"]], ["REVIEW-INTEGRATION"])
        sb.sae("finish", "wt-flow", code=3)
        sb.sae("dispatch", "wt-flow", "REVIEW-INTEGRATION")
        sb.result(task, "reviews/REVIEW-INTEGRATION.md", target="integration", verdict="pass")
        sb.sae("collect", "wt-flow", "REVIEW-INTEGRATION")
        fin = sb.json("dispatch", "wt-flow", "FINAL")
        self.assertIn("read-only", fin["prompt"])
        sb.result(task, "jobs/FINAL.result.md", status="done", summary="all requirements met", validation="pass",
                  changes="none")
        sb.sae("collect", "wt-flow", "FINAL")
        self.assertIn("All jobs done", sb.sae("next", "wt-flow").stdout)
        sb.log = sb.sae("log", "wt-flow", "decision", "Chose plain files", "--class", "clear-choice", "--job", "C")
        report = sb.sae("finish", "wt-flow").stdout
        self.assertIn("## To check before you merge", report)
        self.assertIn("Chose plain files", report)
        self.assertIn("Nothing was pushed", report)
        self.assertEqual(sb.git("log", "--format=%s", "-1", cwd=wt), f"{task}: task record")
        self.assertEqual(sb.git("status", "--porcelain", "--", ".tasks", cwd=wt), "")
        tracked = sb.git("ls-files", f".tasks/done/{task}", cwd=wt)
        self.assertIn("state.json", tracked)
        self.assertNotIn(".lock", tracked)
        self.assertEqual(sb.git("branch", "--list", f"job/{task}/*"), "")
        self.assertEqual(sb.state(task)["task"]["phase"], "done")
        self.assertEqual(sb.git("log", "--format=%s", "main"), "init")  # base untouched
        self.assertNotIn("c.txt", sb.git("ls-tree", "--name-only", "main"))

    def test_merge_conflict_creates_integration_job(self):
        sb = self.sandbox()
        task = self.planned(sb, "conflict", [
            ("LEFT", "implementation", "", [], {}),
            ("RIGHT", "implementation", "", [], {}),
        ])
        sb.sae("start", "conflict")
        ws_l = dispatch_workspace(sb, task, "LEFT")
        ws_r = dispatch_workspace(sb, task, "RIGHT")
        sb.work(ws_l, "app.txt", "left\n", "LEFT: edit")
        sb.work(ws_r, "app.txt", "right\n", "RIGHT: edit")
        for job in ("LEFT", "RIGHT"):
            sb.result(task, f"jobs/{job}.result.md", status="done", summary=job, validation="pass", changes="made")
        sb.sae("collect", "conflict", "LEFT")
        proc = sb.sae("collect", "conflict", "RIGHT", code=4)
        self.assertIn("INTEGRATE-RIGHT", proc.stdout)
        wt = sb.task_worktree(task)
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=no", cwd=wt), "")  # merge aborted
        data = sb.json("dispatch", "conflict", "INTEGRATE-RIGHT")
        self.assertIn("integration-worker.md", data["prompt"])
        ws_i = Path(data["workspace"])
        self.assertIn("<<<<<<<", (ws_i / "app.txt").read_text())
        (ws_i / "app.txt").write_text("left and right\n")
        sb.git("add", "app.txt", cwd=ws_i)
        sb.git("commit", "-q", "--no-edit", cwd=ws_i)
        sb.result(task, "jobs/INTEGRATE-RIGHT.result.md", status="done", summary="merged", validation="pass",
                  changes="made")
        sb.sae("collect", "conflict", "INTEGRATE-RIGHT")
        jobs = sb.state(task)["jobs"]
        self.assertTrue(jobs["RIGHT"]["merged"] and jobs["INTEGRATE-RIGHT"]["merged"])
        self.assertEqual((wt / "app.txt").read_text(), "left and right\n")
        self.assertEqual((sb.repo / "app.txt").read_text(), "line one\n")  # the home checkout is untouched
        sb.sae("finish", "conflict")
        self.assertEqual([p.name for p in wt.parent.iterdir()], ["task"])  # only the task worktree stays

    def test_verify_failure_limit_and_parking_and_decision(self):
        sb = self.sandbox()
        task = self.planned(sb, "limits", [
            ("ONLY", "implementation", "", [], {"verify": ["false"]}),
            ("ASK", "implementation", "", [], {}),
        ], settings=["max-verify-failures=2"])
        sb.sae("start", "limits")
        self.assertEqual(sb.json("status", "limits")["layout"], "worktrees")  # ONLY and ASK are independent
        ws = dispatch_workspace(sb, task, "ONLY")
        sb.work(ws, "o.txt", "o\n", "ONLY: work")
        sb.result(task, "jobs/ONLY.result.md", status="done", summary="o", validation="pass", changes="made")
        sb.sae("collect", "limits", "ONLY", code=5)
        sb.sae("dispatch", "limits", "ONLY", "--resume", "--reason", "verify-failed")
        out = sb.sae("collect", "limits", "ONLY").stdout
        self.assertIn("verify failed 2 times", out)
        self.assertEqual(sb.state(task)["jobs"]["ONLY"]["status"], "failed")
        # a parked worker and a decision job
        sb.sae("dispatch", "limits", "ASK")
        (sb.task_dir(task) / "jobs" / "ASK.result.md").write_text(
            "---\nstatus: parked\nsummary: needs a choice\nvalidation: not-run\nchanges: none\n---\n\n"
            "## Decision request\n**Decision required:** table or column?\n")
        out = sb.sae("collect", "limits", "ASK").stdout
        self.assertIn("table or column", out)
        new = sb.json("decision", "new", "limits", "--from", "ASK")
        self.assertEqual(new["job"], "DECISION-ASK-1")
        prompt = sb.json("dispatch", "limits", "DECISION-ASK-1")["prompt"]
        self.assertIn("decision-worker.md", prompt)
        self.assertIn("ASK.result.md", prompt)
        sb.result(task, "decisions/DECISION-ASK-1.md", **{"class": "consequential",
                                                          "recommendation": "human-required", "decision": "column"})
        sb.sae("collect", "limits", "DECISION-ASK-1")
        sb.sae("log", "limits", "decision", "Column, says the user", "--by", "human", "--class", "consequential",
               "--job", "ASK")
        sb.sae("finish", "limits", code=3)  # ASK parked
        report = sb.sae("finish", "limits", "--with-open").stdout
        self.assertIn("## Open items", report)

    def test_review_rounds_fix_jobs_and_accept(self):
        sb = self.sandbox(points=["all-jobs"])
        task = self.planned(sb, "rounds", [("CORE", "implementation", "", [], {})])
        sb.sae("start", "rounds")
        self.assertEqual(sb.json("status", "rounds")["layout"], "chain")
        ws = dispatch_workspace(sb, task, "CORE")
        self.assertEqual(ws, sb.task_worktree(task))  # chain layout: the task worktree on the task branch
        sb.work(ws, "core.txt", "v1\n", "CORE: v1")
        sb.result(task, "jobs/CORE.result.md", status="done", summary="core", validation="pass", changes="made")
        sb.sae("collect", "rounds", "CORE")
        sb.sae("dispatch", "rounds", "REVIEW-CORE")
        sb.result(task, "reviews/REVIEW-CORE.md", target="CORE", verdict="changes-required")
        out = sb.sae("collect", "rounds", "REVIEW-CORE").stdout
        self.assertIn("CORE-FIX-1", out)
        sb.sae("merge", "rounds", "CORE", code=3)
        sb.sae("job", "add", "rounds", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE", code=1)  # reason
        sb.sae("job", "add", "rounds", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE",
               "--reason", "REVIEW-CORE: changes required")
        sb.job_file(task, "CORE-FIX-1")
        fix_ws = dispatch_workspace(sb, task, "CORE-FIX-1")
        self.assertEqual(fix_ws, ws)
        sb.work(fix_ws, "core.txt", "v2\n", "CORE-FIX-1: v2")
        sb.result(task, "jobs/CORE-FIX-1.result.md", status="done", summary="fix", validation="pass", changes="made")
        out = sb.sae("collect", "rounds", "CORE-FIX-1").stdout
        self.assertIn("REVIEW-CORE-2", out)
        prompt = sb.json("dispatch", "rounds", "REVIEW-CORE-2")["prompt"]
        self.assertIn("Round 2 — check only the findings of", prompt)
        sb.result(task, "reviews/REVIEW-CORE-2.md", target="CORE", verdict="changes-required")
        sb.sae("collect", "rounds", "REVIEW-CORE-2")
        self.assertEqual(sb.state(task)["jobs"]["CORE"]["status"], "parked")
        sb.sae("merge", "rounds", "CORE", "--accept-review", "owner accepts the rest")
        jobs = sb.state(task)["jobs"]
        self.assertTrue(jobs["CORE"]["merged"] and jobs["CORE-FIX-1"]["merged"])
        self.assertEqual((ws / "core.txt").read_text(), "v2\n")
        self.assertTrue(any(e["type"] == "decision" and "owner accepts" in e["summary"] for e in sb.events(task)))

    def test_external_review_command_and_fallback(self):
        sb = self.sandbox(points=["all-jobs"], provider="codex")
        task = self.planned(sb, "external", [("ONE", "implementation", "", [], {})])
        sb.sae("start", "external")
        ws = dispatch_workspace(sb, task, "ONE")
        sb.work(ws, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="one", validation="pass", changes="made")
        sb.sae("collect", "external", "ONE")
        out = sb.sae("dispatch", "external", "REVIEW-ONE").stdout
        self.assertIn("HARNESS: codex · MODEL: cx-2-core (core, newest) · EFFORT: medium", out)
        self.assertIn("COMMAND:\nrm -f ", out)
        self.assertIn("codex exec -m cx-2-core -c model_reasoning_effort=medium -s read-only", out)
        self.assertIn("< /dev/null", out)
        self.assertIn("Do not write files. Reply with the review only", out)
        self.assertIn("IF IT FAILS:", out)
        fallback = out.split("IF IT FAILS:\n")[1].strip()
        self.assertIn("dispatch " + task + " REVIEW-ONE --provider claude --resume", fallback)
        # a failed provider leaves an error text without a verdict
        (sb.task_dir(task) / "reviews").mkdir(exist_ok=True)
        (sb.task_dir(task) / "reviews" / "REVIEW-ONE.md").write_text("API Error: 401\n")
        self.assertIn("IF IT FAILS", sb.sae("collect", "external", "REVIEW-ONE", code=1).stderr)
        again = sb.json("dispatch", "external", "REVIEW-ONE", "--provider", "claude", "--resume",
                        "--reason", "provider failed: 1")
        self.assertIn("prompt", again)
        self.assertEqual(again["harness"], "claude")

    def test_no_git_task(self):
        sb = self.sandbox(git=False)
        task = self.planned(sb, "plain", [
            ("ONE", "implementation", "", [], {"scope": ["one/**"]}),
            ("TWO", "implementation", "", [], {"scope": ["two/**"]}),
            ("THREE", "implementation", "", [], {}),
        ])
        out = sb.sae("start", "plain").stdout
        self.assertIn("No git", out)
        state = sb.state(task)["task"]
        self.assertFalse(state["git"])
        self.assertEqual(state["layout"], "chain")
        sb.sae("dispatch", "plain", "ONE")
        sb.sae("dispatch", "plain", "TWO")  # disjoint scopes
        sb.sae("dispatch", "plain", "THREE", code=1)
        for job in ("ONE", "TWO"):
            sb.result(task, f"jobs/{job}.result.md", status="done", summary=job, validation="pass", changes="made")
            sb.sae("collect", "plain", job)
        self.assertTrue(sb.state(task)["jobs"]["ONE"]["merged"])

    def test_sourced_finding_from_a_job_worktree_goes_to_the_task_worktree(self):
        sb = self.sandbox()
        task = self.planned(sb, "finds", [("X", "implementation", "", [], {}), ("Y", "implementation", "", [], {})])
        sb.sae("start", "finds")
        ws = dispatch_workspace(sb, task, "X")
        path = Path(sb.json("finding", "new", "Slow lookup", "--type", "defect", "--confidence", "medium",
                            "--source", f"finds/X", "--paths", "src/a,src/b", "--body", "Lookup takes 4 s.", cwd=ws)["file"])
        self.assertEqual(path.parent, sb.task_worktree(task) / ".tasks" / "findings")  # finish commits it
        text = path.read_text()
        self.assertIn(f"source: {task}/X", text)
        self.assertIn("paths: [src/a, src/b]", text)
        self.assertTrue(any(e["type"] == "finding.created" for e in sb.events(task)))
        sb.sae("finding", "close", str(path), "--outcome", "maybe", code=1)
        sb.sae("finding", "close", str(path), "--outcome", "rejected: expected behavior")
        self.assertFalse(path.exists())
        self.assertIn("Slow lookup · rejected: expected behavior",
                      (sb.repo / ".tasks" / "findings" / "closed.md").read_text())


class ViewerAndSetupTests(SaeTestCase):
    def test_no_viewer_data_files_are_written(self):
        # the viewer server reads live (test_viewer_server.py); commands generate nothing for it
        sb = self.sandbox()
        sb.new_task("Viewer data", "viewer-data")
        sb.sae("new", "Later thing", "--backlog")
        sb.sae("set", "viewer-data", "execution=economy")
        self.assertFalse((sb.repo / ".tasks" / ".viewer").exists())

    def test_setup_save_validates_and_backs_up(self):
        sb = self.sandbox()
        bad = config_for(sb.worktrees)
        bad["routing"]["claude"]["tables"]["execution"]["max"]["hard"] = {"tier": "L9"}
        out = sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr
        self.assertIn("routing.claude.tables.execution.max.hard", out)
        good = config_for(sb.worktrees)
        good["parallel"]["max_writers"] = 2
        sb.sae("setup", "save", stdin=json.dumps(good))
        self.assertTrue(Path(str(sb.config) + ".bak").exists())
        self.assertEqual(json.loads(sb.config.read_text())["parallel"]["max_writers"], 2)
        show = sb.json("setup", "show")
        self.assertEqual(show["errors"], [])
        snippets = sb.sae("setup", "snippets").stdout
        self.assertIn(f'"{sb.worktrees}" = "write"', snippets)
        self.assertIn("max_threads = 10", snippets)
        self.assertIn(f"Edit(/{sb.worktrees}/**)", snippets)

    def test_codex_subagent_cap_check(self):
        sb = self.sandbox()
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib import setup_mode  # noqa: the package is importable from the scripts folder
        finally:
            sys.path.pop(0)
        old = os.environ.get("CODEX_HOME")
        try:
            os.environ["CODEX_HOME"] = str(sb.codex_home)
            cap = setup_mode.codex_subagent_cap()
            self.assertIsNone(cap["subagents"])
            self.assertFalse(cap["ok"])
            (sb.codex_home / "config.toml").write_text("[agents]\nmax_threads = 6\n")
            self.assertEqual(setup_mode.codex_subagent_cap()["subagents"], 6)
            self.assertIn("max_threads = 10", setup_mode.codex_cap_text(setup_mode.codex_subagent_cap()))
            (sb.codex_home / "config.toml").write_text("[agents]\nmax_threads = 10\n")
            self.assertTrue(setup_mode.codex_subagent_cap()["ok"])
            (sb.codex_home / "config.toml").write_text(
                "[agents]\nmax_threads = 10\n[features.multi_agent_v2]\nmax_concurrent_threads_per_session = 4\n")
            self.assertEqual(setup_mode.codex_subagent_cap()["subagents"], 3)
        finally:
            if old is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = old

    def test_doctor_repo(self):
        sb = self.sandbox()
        (sb.repo / ".tasks" / "repo").mkdir(parents=True)
        (sb.repo / ".tasks" / "repo" / "setup.sh").write_text("echo setup ran > setup-marker\n")
        (sb.repo / ".tasks" / "repo" / "worktreeinclude").write_text(".env\n")
        (sb.repo / ".gitignore").write_text(".env\n.tasks/.viewer/\n")
        (sb.repo / ".env").write_text("SECRET=1\n")
        out = sb.sae("doctor", "--repo", code=1).stdout  # Codex cap is not set in the sandbox
        self.assertIn("✓ throwaway worktree", out)
        self.assertIn("✗ Codex subagent cap", out)
        self.assertEqual(sb.git("branch", "--list", "sae-doctor-*"), "")
        self.assertIn("✓ viewer files exist; repository known", out)


if __name__ == "__main__":
    unittest.main()
