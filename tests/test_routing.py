"""Tests of routing: config schema 2, model lists, three levels, overrides, effort, cross-harness.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
Every sandbox points SAE_CONFIG and CODEX_HOME into a temporary folder.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import Sandbox, SaeTestCase, config_for, dispatch_workspace, schema1_config, write_codex_catalog  # noqa: E402

# The harness's tier L3 and an alternative pair, per harness (fake models of saetest).
L3 = {"claude": ("c-big", "c-big", "high"), "codex": ("core", "cx-2-core", "medium")}
OTHER = {"claude": ("c-mid", "c-mid", "max"), "codex": ("lite", "cx-2-lite", "high")}


class RoutingTestCase(SaeTestCase):
    def task(self, sb: Sandbox, slug: str, harness: str = "claude") -> str:
        return sb.json("new", slug, "--slug", slug, "--harness", harness)["task"]

    def second(self, name: str, **kwargs) -> Sandbox:
        """Another sandbox in its own folder (one test, several repositories or configs)."""
        folder = self.tmp / name
        folder.mkdir()
        return Sandbox(folder, **kwargs)

    def research(self, sb: Sandbox, slug: str, job: str, difficulty: str = "hard") -> dict:
        sb.sae("job", "add", slug, job, "--kind", "research", "--difficulty", difficulty)
        return sb.json("dispatch", slug, job)

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


class ResolutionTests(RoutingTestCase):
    def test_tier_project_and_task_levels_resolve_for_both_harnesses(self):
        sb = self.sandbox()
        for harness in ("claude", "codex"):
            slug = f"levels-{harness}"
            task = self.task(sb, slug, harness)
            # global: research balanced + hard → tier L3
            entry, exact, effort = L3[harness]
            data = self.research(sb, slug, "R1")
            self.assertEqual((data["harness"], data["model_entry"], data["model"], data["effort"]),
                             (harness, entry, exact, effort))
            self.assertEqual((data["tier"], data["source"]), ("L3", "global"))
            # project: tier L3 changed → every cell on L3 follows; the cell stays global
            entry, exact, effort = OTHER[harness]
            sb.sae("project", "set", f"tier.{harness}.L3={entry}:{effort}")
            data = self.research(sb, slug, "R2")
            self.assertEqual((data["model"], data["effort"], data["tier"]), (exact, effort, "L3"))
            self.assertEqual(data["source"], "project")
            self.assertEqual(data["sources"], {"cell": "global", "tier": "project", "harness": "routing"})
            out = sb.sae("dispatch", slug, "R2", "--resume", "--reason", "header").stdout
            self.assertIn("ROUTING: research · balanced · hard → tier L3 (cell: global, tier: project)",
                          " ".join(out.split()))
            # project: one cell points to another tier
            sb.sae("project", "set", f"routing.{harness}.research.balanced.normal=L4")
            data = self.research(sb, slug, "R3", "normal")
            self.assertEqual((data["tier"], data["sources"]["cell"], data["sources"]["tier"]), ("L4", "project", "global"))
            # task: a cell with its own model and effort wins over project and global
            sb.sae("set", slug, f"routing.{harness}.research.balanced.hard={L3[harness][0]}:low")
            data = self.research(sb, slug, "R4")
            self.assertEqual((data["model"], data["effort"], data["tier"], data["source"]),
                             (L3[harness][1], "low", None, "task"))
            attempt = sb.state(task)["jobs"]["R4"]["attempts"][0]
            self.assertEqual({k: attempt[k] for k in ("harness", "model", "model_entry", "effort", "source", "tier")},
                             {"harness": harness, "model": L3[harness][1], "model_entry": L3[harness][0],
                              "effort": "low", "source": "task", "tier": None})
            # inherit removes the task value again
            sb.sae("set", slug, f"routing.{harness}.research.balanced.hard=inherit")
            self.assertNotIn("routing", json.loads((sb.task_dir(task) / "settings.json").read_text()))
            sb.sae("project", "unset", f"tier.{harness}.L3", f"routing.{harness}.research.balanced.normal")

    def test_tiers_off_uses_the_cell_model(self):
        sb = self.sandbox()
        self.task(sb, "tiers-off")
        # every global cell holds only a tier: switching tiers off leaves nothing usable
        out = sb.sae("set", "tiers-off", "tiers-in-cells.claude=off", code=1).stderr
        self.assertIn("routing.claude.tables.research.balanced.hard (global): nothing usable", " ".join(out.split()))
        # cells that hold a tier and a pair: the switch picks one
        config = json.loads(sb.config.read_text())
        block = config["routing"]["claude"]
        for table in block["tables"].values():
            for row in table.values():
                for cell in row.values():
                    cell.update(block["tiers"][cell["tier"]])
        block["tables"]["research"]["balanced"]["hard"] = {"tier": "L3", "model": "c-small", "effort": "xhigh"}
        sb.sae("setup", "save", stdin=json.dumps(config))
        self.assertEqual(self.research(sb, "tiers-off", "A")["model"], "c-big")
        sb.sae("set", "tiers-off", "tiers-in-cells.claude=off")
        data = self.research(sb, "tiers-off", "B")
        self.assertEqual((data["model"], data["effort"], data["tier"]), ("c-small", "xhigh", None))
        # with tiers off, a task cell that has only a tier is unusable: refused when set
        out = sb.sae("set", "tiers-off", "routing.claude.research.economy.hard=L2", code=1).stderr
        self.assertIn("routing.claude.tables.research.economy.hard (task): nothing usable", " ".join(out.split()))

    def test_codex_families_resolve_to_the_newest_listed_version(self):
        sb = self.sandbox(provider="codex")
        task = self.task(sb, "families", "codex")
        sb.sae("set", "families", "routing.codex.research.balanced.hard=lite:high")
        data = self.research(sb, "families", "A")
        self.assertEqual(data["model"], "cx-2-lite")  # cx-3-lite is hidden in the catalog
        self.assertEqual(data["family"], {"family": "lite", "newest": "cx-2-lite"})
        out = sb.sae("dispatch", "families", "A", "--resume", "--reason", "header").stdout
        self.assertIn("HARNESS: codex · MODEL: cx-2-lite (lite, newest) · EFFORT: high", out)
        # an exact older version passes as it is
        sb.sae("set", "families", "routing.codex.research.balanced.hard=cx-1-lite:high")
        self.assertEqual(self.research(sb, "families", "B")["model"], "cx-1-lite")
        # no catalog: the family cannot resolve
        sb.sae("set", "families", "routing.codex.research.balanced.hard=inherit")
        (sb.codex_home / "models_cache.json").unlink()
        sb.env["PATH"] = "/usr/bin:/bin"  # no codex CLI either
        sb.sae("job", "add", "families", "C", "--kind", "research", "--difficulty", "hard")
        out = sb.sae("dispatch", "families", "C", code=2).stderr
        self.assertIn("cannot resolve family 'core'", out)
        write_codex_catalog(sb.codex_home)
        self.assertEqual(sb.state(task)["jobs"]["C"]["status"], "pending")

    def test_job_review_takes_its_job_difficulty_and_planning_is_never_mechanical(self):
        sb = self.sandbox(points=["all-jobs"])
        plans = self.task(sb, "plans")
        out = sb.sae("job", "add", "plans", "PLAN", "--kind", "planning", "--difficulty", "mechanical", code=1).stderr
        self.assertIn("never mechanical", out)
        sb.sae("set", "plans", "task-difficulty=hard")
        sb.sae("job", "add", "plans", "PLAN", "--kind", "planning")
        self.assertEqual(sb.state(plans)["jobs"]["PLAN"]["difficulty"], "hard")

        sb2 = self.second("two", points=["all-jobs"])
        task = self.executing(sb2, "jobrev", [("MECH", ["--difficulty", "mechanical"]), ("HARD", ["--difficulty", "hard"])])
        for job_id in ("MECH", "HARD"):
            ws = dispatch_workspace(sb2, task, job_id)
            sb2.work(ws, f"{job_id}.txt", "x\n", f"{job_id}: work")
            sb2.result(task, f"jobs/{job_id}.result.md", status="done", summary="s", validation="pass", changes="made")
            sb2.sae("collect", "jobrev", job_id)
        sb2.sae("set", "jobrev", "review-level=economy")
        mech = sb2.json("dispatch", "jobrev", "REVIEW-MECH")
        self.assertEqual((mech["phase"], mech["difficulty"], mech["tier"]), ("review", "normal", "L2"))
        out = sb2.sae("job", "edit", "jobrev", "REVIEW-HARD", "--difficulty", "normal", "--reason", "try",
                      code=1).stderr
        self.assertIn("takes the difficulty of HARD", out)
        hard = sb2.json("dispatch", "jobrev", "REVIEW-HARD")
        self.assertEqual(hard["difficulty"], "hard")

    def test_task_level_reviews_of_a_hard_task_dispatch_as_planned(self):
        """INTEGRATION-REVIEW finding 3: next (and its launch card) and dispatch resolve the
        same column for the spec, plan and integration reviews of a hard task."""
        sb = self.sandbox(points=["spec", "plan", "integration"])
        task = sb.new_task("Hard", "hard")
        sb.sae("set", "hard", "task-difficulty=hard")
        (sb.task_dir(task) / "specs.md").write_text("# Spec\n\n## Requirements\n\n### [ONE] One\n"
                                                     "Acceptance:\n- [ ] one\n")

        def same_column(review: str, want: str = "hard") -> None:
            planned = {r["id"]: r for r in sb.json("next", "hard")["ready"]}[review]
            dispatched = sb.json("dispatch", "hard", review)
            self.assertEqual((review, planned["difficulty"], dispatched["difficulty"]), (review, want, want))

        same_column("REVIEW-SPEC")
        self.assertIsNone(sb.state(task)["jobs"]["REVIEW-SPEC"]["difficulty"])
        sb.result(task, "reviews/REVIEW-SPEC.md", target="spec", verdict="pass")
        sb.sae("collect", "hard", "REVIEW-SPEC")
        sb.sae("approve", "hard", "spec")
        sb.sae("job", "add", "hard", "ONLY", "--kind", "implementation")
        sb.job_file(task, "ONLY", covers=["ONE"])
        same_column("REVIEW-PLAN")
        sb.result(task, "reviews/REVIEW-PLAN.md", target="plan", verdict="pass")
        sb.sae("collect", "hard", "REVIEW-PLAN")
        sb.sae("approve", "hard", "plan")
        sb.sae("start", "hard")
        ws = dispatch_workspace(sb, task, "ONLY")
        sb.work(ws, "only.txt", "x\n", "ONLY: work")
        sb.result(task, "jobs/ONLY.result.md", status="done", summary="s", validation="pass", changes="made")
        self.assertIn("Added REVIEW-INTEGRATION", sb.sae("collect", "hard", "ONLY").stdout)
        self.assertIsNone(sb.state(task)["jobs"]["REVIEW-INTEGRATION"]["difficulty"])
        self.assertEqual({r["id"]: r for r in sb.json("next", "hard")["ready"]}["REVIEW-INTEGRATION"]["difficulty"],
                         "hard")
        sb.sae("job", "edit", "hard", "REVIEW-INTEGRATION", "--difficulty", "normal", "--reason", "small change")
        same_column("REVIEW-INTEGRATION", "normal")  # an edited difficulty wins, on the card and at dispatch

    def test_config_tables_have_no_mechanical_planning_or_review_column(self):
        sb = self.sandbox()
        bad = config_for(sb.worktrees)
        bad["routing"]["codex"]["tables"]["review"]["max"]["mechanical"] = {"tier": "L1"}
        out = sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr
        self.assertIn("routing.codex.tables.review.max.mechanical: the review table has only normal, hard",
                      " ".join(out.split()))
        sb.new_task("t", "t")
        out = sb.sae("set", "t", "routing.claude.planning.max.mechanical=L1", code=1).stderr
        self.assertIn("the planning table has only normal, hard", " ".join(out.split()))


class ModelListTests(RoutingTestCase):
    def test_a_model_outside_the_list_fails_setup_save_and_dispatch(self):
        sb = self.sandbox()
        bad = config_for(sb.worktrees)
        bad["routing"]["claude"]["tiers"]["L2"] = {"model": "c-unknown", "effort": "low"}
        out = sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr
        self.assertIn("routing.claude.tiers.L2: model 'c-unknown' is not in models.claude", out)
        # efforts are recorded per model: ultra only where the list has it
        bad = config_for(sb.worktrees)
        bad["routing"]["codex"]["tiers"]["L1"] = {"model": "lite", "effort": "ultra"}
        out = sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr
        self.assertIn("routing.codex.tiers.L1: lite does not accept effort 'ultra'", out)
        good = config_for(sb.worktrees)
        good["routing"]["codex"]["tiers"]["L4"] = {"model": "core", "effort": "ultra"}
        sb.sae("setup", "save", stdin=json.dumps(good))
        # a switched-off model is refused too
        bad = config_for(sb.worktrees)
        bad["models"]["claude"][0]["enabled"] = False
        out = sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr
        self.assertIn("model 'c-small' is switched off in models.claude", " ".join(out.split()))
        # a config edited by hand: dispatch names the cell and exits 2
        self.task(sb, "handedit")
        config = json.loads(sb.config.read_text())
        config["routing"]["claude"]["tables"]["research"]["balanced"]["hard"] = {"model": "c-gone", "effort": "low"}
        config["routing"]["claude"]["tiers_in_cells"] = False
        sb.config.write_text(json.dumps(config))
        sb.sae("job", "add", "handedit", "R", "--kind", "research", "--difficulty", "hard")
        out = sb.sae("dispatch", "handedit", "R", code=2).stderr
        self.assertIn("routing.claude.tables.research.balanced.hard: model 'c-gone' is not in models.claude",
                      " ".join(out.split()))
        # sae set refuses an unknown model for a task cell
        out = sb.sae("set", "handedit", "tier.claude.L1=c-gone:low", code=1).stderr
        self.assertIn("not in models.claude", " ".join(out.split()))

    def test_claude_entries_are_families_and_placeholders_are_refused(self):
        sb = self.sandbox()
        bad = config_for(sb.worktrees)
        bad["models"]["claude"][0]["family"] = False
        out = sb.sae("setup", "save", stdin=json.dumps(bad), code=1).stderr
        self.assertIn("Claude entries are families", out)
        self.assertEqual(sb.json("setup", "show")["errors"], [])
        os.remove(sb.config)
        show = sb.json("setup", "show")
        self.assertEqual(show["skeleton"]["schema"], 2)
        out = sb.sae("setup", "save", stdin=json.dumps(show["skeleton"]), code=1).stderr
        self.assertIn("fill in <", out)


class SchemaOneTests(RoutingTestCase):
    def test_schema_1_exits_2_and_setup_converts_it(self):
        sb = self.sandbox()
        sb.config.write_text(json.dumps(schema1_config(sb.worktrees)))
        out = sb.sae("new", "Old config", code=2).stderr
        self.assertIn("schema 1 (rungs and level maps)", out)
        self.assertIn("setup", out)
        shown = sb.json("setup", "show")
        proposal = shown["proposal"]
        self.assertEqual(proposal["schema"], 2)
        claude, codex = proposal["routing"]["claude"], proposal["routing"]["codex"]
        self.assertTrue(claude["tiers_in_cells"])
        self.assertEqual(claude["tiers"]["L2"], {"model": "c-big", "effort": "<choose>"})
        self.assertEqual(codex["tiers"]["L1"], {"model": "cx-2-lite", "effort": "xhigh"})
        self.assertEqual([m["model"] for m in proposal["models"]["claude"]], ["c-mid", "c-big"])
        # efforts of Codex models come from the catalog
        self.assertIn("ultra", proposal["models"]["codex"][1]["efforts"])
        self.assertEqual(codex["tables"]["execution"]["balanced"]["hard"], {"tier": "L3"})
        self.assertEqual(codex["tables"]["planning"]["economy"], {"normal": {"tier": "L1"}, "hard": {"tier": "L2"}})
        self.assertEqual(codex["tables"]["review"]["max"], {"normal": {"tier": "L3"}, "hard": {"tier": "L3"}})
        text = sb.sae("setup", "show").stdout
        self.assertIn("schema 1", text)
        self.assertIn("claude · review", text)
        # placeholders are refused; filled in, the conversion saves and sae works again
        out = sb.sae("setup", "save", stdin=json.dumps(proposal), code=1).stderr
        self.assertIn("<choose>", out)
        for tier in claude["tiers"].values():
            tier["effort"] = "high"
        for entry in proposal["models"]["claude"]:
            entry["efforts"] = ["low", "medium", "high"]
        sb.sae("setup", "save", stdin=json.dumps(proposal))
        sb.new_task("New config", "new-config")


class SetupShowTests(RoutingTestCase):
    def test_setup_show_prints_every_table_readably(self):
        sb = self.sandbox()
        text = sb.sae("setup", "show").stdout
        for harness in ("claude", "codex"):
            for phase in ("research", "planning", "execution", "review"):
                self.assertIn(f"  {harness} · {phase}\n", text)
        self.assertIn("Codex families (newest · older versions):", text)
        self.assertIn("lite: cx-2-lite", text)
        self.assertIn("older: cx-1-lite", text)
        self.assertNotIn("cx-3-lite", text)  # hidden in the catalog
        tables = text.split("claude routing:")[1].split("codex models")[0]
        self.assertIn("level     normal  hard", tables)
        self.assertTrue(all(len(line) <= 72 for line in tables.splitlines()), tables)


class EffortAndProviderTests(RoutingTestCase):
    def test_claude_dispatch_prints_and_records_effort(self):
        sb = self.sandbox()
        task = self.executing(sb, "effort", [("ONE", [])])
        out = sb.sae("dispatch", "effort", "ONE").stdout
        self.assertIn("HARNESS: claude · MODEL: c-mid · EFFORT: low", out)  # balanced + normal → L2
        self.assertIn("ROUTING: execution · balanced · normal → tier L2 (cell: global, tier: global)",
                      " ".join(out.split()))
        self.assertNotIn("n/a", out.split("PROMPT:")[0])
        self.assertIn("Commit trailers: Task: " + task + " · Job: ONE · Model: c-mid", out)
        attempt = sb.state(task)["jobs"]["ONE"]["attempts"][0]
        self.assertEqual((attempt["effort"], attempt["tier"], attempt["source"]), ("low", "L2", "global"))
        event = [e for e in sb.events(task) if e["type"] == "job.dispatched"][-1]
        self.assertEqual((event["model"], event["effort"], event["source"]), ("c-mid", "low", "global"))

    def test_cross_harness_review_runs_in_the_other_harness(self):
        for orchestrator, needle in (("claude", "codex exec -m cx-2-core -c model_reasoning_effort=medium"),
                                     ("codex", "claude -p ")):
            sb = self.second(orchestrator, points=["all-jobs"], provider="cross-harness")
            sb.env["SAE_HARNESS"] = orchestrator
            task = self.executing(sb, "cross", [("ONE", [])])
            card = sb.sae("status", "cross").stdout
            other = "codex" if orchestrator == "claude" else "claude"
            self.assertIn(f"cross-harness ({other} reviews)", card)
            ws = dispatch_workspace(sb, task, "ONE")
            sb.work(ws, "one.txt", "1\n", "ONE: work")
            sb.result(task, "jobs/ONE.result.md", status="done", summary="s", validation="pass", changes="made")
            sb.sae("collect", "cross", "ONE")
            out = sb.sae("dispatch", "cross", "REVIEW-ONE").stdout
            self.assertIn(f"HARNESS: {other} ·", out)
            self.assertIn(needle, out)
            if other == "claude":
                self.assertIn("--model c-big --effort high --permission-mode dontAsk", out)
            self.assertIn(f"--provider {orchestrator} --resume", out.split("IF IT FAILS:")[1])
            # the fallback runs in the orchestrator's harness
            again = sb.json("dispatch", "cross", "REVIEW-ONE", "--provider", orchestrator, "--resume",
                            "--reason", "provider failed: 1")
            self.assertEqual(again["harness"], orchestrator)
            self.assertIn("prompt", again)


class OverrideTests(RoutingTestCase):
    def test_override_for_a_job_and_for_its_review(self):
        sb = self.sandbox(points=["all-jobs"])
        task = self.executing(sb, "over", [("ONE", []), ("TWO", [])])
        out = sb.sae("job", "override", "over", "ONE", "--model", "c-small", "--effort", "xhigh",
                     "--reason", "owner asked").stdout
        self.assertIn("ONE: override claude · c-small · xhigh (routing: claude · c-mid · low)", out)
        workdir = dispatch_workspace(sb, task, "ONE")
        out = sb.sae("dispatch", "over", "ONE", "--resume", "--reason", "header").stdout
        self.assertIn("HARNESS: claude · MODEL: c-small · EFFORT: xhigh", out)
        self.assertIn("ROUTING: override (set ", out)
        self.assertIn("; routing: claude · c-mid · low", out)
        self.assertEqual(sb.state(task)["jobs"]["ONE"]["attempts"][0]["source"], "override")
        # a running job keeps its model
        out = sb.sae("job", "override", "over", "ONE", "--effort", "max", code=1).stderr
        self.assertIn("not pending", out)
        # the review of ONE runs on Codex, all rounds; reviews otherwise run on Claude
        sb.sae("job", "override", "over", "ONE", "--review", "--harness", "codex", "--effort", "high")
        self.assertEqual(sb.state(task)["task"]["overrides"]["REVIEW-ONE"]["harness"], "codex")
        # an invalid pair is refused and leaves nothing behind
        out = sb.sae("job", "override", "over", "TWO", "--model", "c-gone", code=1).stderr
        self.assertIn("not in models.claude", " ".join(out.split()))
        self.assertNotIn("TWO", sb.state(task)["task"]["overrides"])
        sb.work(workdir, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "over", "ONE")
        out = sb.sae("dispatch", "over", "REVIEW-ONE").stdout
        self.assertIn("HARNESS: codex · MODEL: cx-2-core (core, newest) · EFFORT: high", out)
        self.assertIn("COMMAND:", out)
        self.assertIn("ROUTING: override (set ", out)
        # set on a planned review and cleared; both logged
        sb.sae("job", "override", "over", "REVIEW-INTEGRATION", "--effort", "max")
        sb.sae("job", "override", "over", "REVIEW-INTEGRATION", "--clear")
        types = [(e["type"], e["job"]) for e in sb.events(task) if e["type"].startswith("override.")]
        self.assertEqual(types, [("override.set", "ONE"), ("override.set", "REVIEW-ONE"),
                                 ("override.set", "REVIEW-INTEGRATION"), ("override.cleared", "REVIEW-INTEGRATION")])
        self.assertNotIn("REVIEW-INTEGRATION", sb.state(task)["task"]["overrides"])


class ProjectDefaultsTests(RoutingTestCase):
    def test_project_defaults_reach_new_tasks_and_stay_in_the_user_config(self):
        sb = self.sandbox()
        before = sb.config.read_text()
        show = sb.json("project", "show")
        self.assertEqual(show["values"], {})
        self.assertEqual(sb.config.read_text(), before)  # show is read-only
        sb.sae("project", "set", "execution=economy", "reviewer=cross-harness", "review=spec,integration")
        config = json.loads(sb.config.read_text())
        key = str(sb.repo.resolve())
        self.assertEqual(config["projects"][key]["defaults"],
                         {"levels": {"execution": "economy"}, "review": {"provider": "cross-harness",
                                                                         "points": ["spec", "integration"]}})
        self.assertTrue(Path(str(sb.config) + ".bak").exists())
        task = sb.new_task("Light", "light")
        settings = json.loads((sb.task_dir(task) / "settings.json").read_text())
        self.assertEqual(settings["levels"]["execution"], "economy")
        self.assertEqual(settings["levels"]["planning"], "max")
        self.assertEqual(settings["review"], {"points": ["spec", "integration"], "provider": "cross-harness"})
        # nothing personal in the repository: only the task folder is new
        self.assertEqual(sb.git("status", "--porcelain"), "?? .tasks/")
        for path in (sb.repo / ".tasks").rglob("*"):
            if path.is_file():
                self.assertNotIn('"projects"', path.read_text())
        shown = sb.sae("project", "show").stdout
        self.assertIn('execution = "economy"  (global: "balanced")', shown)
        out = sb.sae("project", "set", "tier.codex.L2=c-big:low", code=1).stderr
        self.assertIn("not in models.codex", out)
        sb.sae("project", "unset", "execution", "reviewer", "review")
        self.assertNotIn(key, json.loads(sb.config.read_text())["projects"])

    def test_tests_never_touch_the_real_config(self):
        sb = self.sandbox()
        self.assertTrue(sb.env["SAE_CONFIG"].startswith(str(self.tmp)))
        self.assertTrue(sb.env["CODEX_HOME"].startswith(str(self.tmp)))


if __name__ == "__main__":
    unittest.main()
