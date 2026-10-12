"""Review flow: finish gates, integration rounds, stale checks, generated edges, fix rounds,
resumed research and planning jobs, effective review marks and planned reviews.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from saetest import SCRIPTS, Sandbox, SaeTestCase, dispatch_workspace, wide_lines


class ReviewFlowCase(SaeTestCase):
    def planned(self, sb: Sandbox, slug: str, jobs: list[tuple], settings: list[str] = ()) -> str:
        task = sb.new_task(slug, slug)
        if settings:
            sb.sae("set", slug, *settings)
        for job_id, kind, needs, extra in jobs:
            sb.sae("job", "add", slug, job_id, "--kind", kind, *(["--needs", needs] if needs else []), *extra)
            sb.job_file(task, job_id)
        sb.approve_plan(slug)
        sb.sae("start", slug)
        return task

    def run_writer(self, sb: Sandbox, task: str, slug: str, job: str, *, collect: bool = True) -> str:
        ws = dispatch_workspace(sb, task, job)
        sb.work(ws, f"{job.lower()}.txt", f"{job}\n", f"{job}: work")
        sb.result(task, f"jobs/{job}.result.md", status="done", summary=job, validation="pass", changes="made")
        return sb.sae("collect", slug, job).stdout if collect else ""

    def review(self, sb: Sandbox, task: str, slug: str, review: str, target: str, verdict: str) -> dict:
        data = sb.json("dispatch", slug, review)
        sb.result(task, f"reviews/{review}.md", target=target, verdict=verdict)
        out = sb.sae("collect", slug, review).stdout
        data["collect"] = out
        return data

    def final(self, sb: Sandbox, task: str, slug: str) -> None:
        sb.sae("dispatch", slug, "FINAL")
        sb.result(task, "jobs/FINAL.result.md", status="done", summary="all met", validation="pass", changes="none")
        sb.sae("collect", slug, "FINAL")

    def integration_task(self, sb: Sandbox, slug: str) -> str:
        """Two independent writers (worktrees layout) and a final validation, integration review on."""
        task = self.planned(sb, slug, [
            ("LEFT", "implementation", "", []),
            ("RIGHT", "implementation", "", []),
            ("FINAL", "validation", "LEFT,RIGHT", ["--final"]),
        ], settings=["review=integration"])
        self.run_writer(sb, task, slug, "LEFT")
        out = self.run_writer(sb, task, slug, "RIGHT")
        self.assertIn("Added REVIEW-INTEGRATION", out)
        return task


class IntegrationRoundTests(ReviewFlowCase):
    def test_pilot_project_case_generated_edges_and_finish_refused(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "pilot")
        jobs = sb.state(task)["jobs"]
        # [GENERATED-JOB-EDGES]: the review after the last writers, the final validation after the review
        self.assertEqual(sorted(jobs["REVIEW-INTEGRATION"]["needs"]), ["LEFT", "RIGHT"])
        self.assertTrue(jobs["REVIEW-INTEGRATION"]["generated"])
        self.assertIn("REVIEW-INTEGRATION", jobs["FINAL"]["needs"])
        self.assertEqual(jobs["FINAL"]["generated_needs"], ["REVIEW-INTEGRATION"])
        changed = [e for e in sb.events(task) if e["type"] == "job.changed" and e["job"] == "FINAL"]
        self.assertEqual([e["by"] for e in changed], ["sae"])
        self.assertEqual([r["id"] for r in sb.json("next", "pilot")["ready"]], ["REVIEW-INTEGRATION"])
        out = self.review(sb, task, "pilot", "REVIEW-INTEGRATION", "integration", "changes-required")["collect"]
        self.assertIn("--fix-of REVIEW-INTEGRATION", out)
        # the pilot-project agent added a fix job without --fix-of
        sb.sae("job", "add", "pilot", "INTEGRATION-FIX-1", "--kind", "implementation",
               "--needs", "REVIEW-INTEGRATION", "--reason", "REVIEW-INTEGRATION findings")
        sb.job_file(task, "INTEGRATION-FIX-1")
        self.run_writer(sb, task, "pilot", "INTEGRATION-FIX-1")
        self.assertNotIn("REVIEW-INTEGRATION-2", sb.state(task)["jobs"])  # not declared as a fix: no round
        nxt = sb.sae("next", "pilot").stdout
        self.assertIn("REVIEW-INTEGRATION requires changes", nxt)
        self.assertNotIn("All jobs done", nxt)
        sb.sae("dispatch", "pilot", "FINAL", code=1)  # waits for a positive round
        proc = sb.sae("finish", "pilot", code=3)
        self.assertIn("REVIEW-INTEGRATION says changes-required", proc.stderr)
        self.assertIn("--fix-of REVIEW-INTEGRATION", proc.stderr)
        self.assertIn(f"sae finish {task} --override", proc.stderr)
        sb.sae("finish", "pilot", "--with-open", code=3)  # --with-open never passes the verdict gate
        self.assertEqual(sb.state(task)["task"]["phase"], "executing")

    def test_override_closes_and_the_report_lists_it(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "override")
        self.review(sb, task, "override", "REVIEW-INTEGRATION", "integration", "changes-required")
        sb.sae("finish", "override", "--override", " ", code=1)
        report = sb.sae("finish", "override", "--override", "owner accepts the remaining findings").stdout
        self.assertIn("## Overridden gates", report)
        self.assertIn("verdict gate: REVIEW-INTEGRATION, FINAL. Reason: owner accepts the remaining findings",
                      " ".join(report.split()))  # wrapped within 72 columns
        events = [e for e in sb.events(task) if e["type"] == "gate.overridden"]
        self.assertEqual(events[0]["gate"], "verdict")
        self.assertEqual(events[0]["reason"], "owner accepts the remaining findings")
        self.assertEqual(sb.state(task)["task"]["phase"], "done")

    def test_two_integration_rounds_then_park(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "rounds2")
        self.review(sb, task, "rounds2", "REVIEW-INTEGRATION", "integration", "changes-required")
        sb.sae("job", "add", "rounds2", "INTEGRATION-FIX-1", "--kind", "implementation",
               "--fix-of", "REVIEW-INTEGRATION", "--reason", "finding 1")
        sb.job_file(task, "INTEGRATION-FIX-1")
        fix = sb.json("dispatch", "rounds2", "INTEGRATION-FIX-1")
        self.assertIn("Fixes findings of REVIEW-INTEGRATION", fix["prompt"])
        self.assertIn("reviews/REVIEW-INTEGRATION.md", fix["prompt"])
        self.assertIn(f"job/{task}/INTEGRATION-FIX-1", fix["branch"])  # an ordinary writer with its own branch
        sb.work(Path(fix["workspace"]), "fix.txt", "fix\n", "INTEGRATION-FIX-1: fix")
        sb.result(task, "jobs/INTEGRATION-FIX-1.result.md", status="done", summary="fix", validation="pass",
                  changes="made")
        out = sb.sae("collect", "rounds2", "INTEGRATION-FIX-1").stdout
        self.assertIn("Added REVIEW-INTEGRATION-2", out)
        jobs = sb.state(task)["jobs"]
        self.assertTrue(jobs["INTEGRATION-FIX-1"]["merged"])
        self.assertEqual(sorted(jobs["REVIEW-INTEGRATION-2"]["needs"]), ["INTEGRATION-FIX-1", "LEFT", "RIGHT"])
        self.assertEqual(jobs["REVIEW-INTEGRATION-2"]["round"], 2)
        self.assertEqual(jobs["FINAL"]["needs"], ["LEFT", "RIGHT", "REVIEW-INTEGRATION-2"])
        data = self.review(sb, task, "rounds2", "REVIEW-INTEGRATION-2", "integration", "changes-required")
        self.assertIn("Round 2 — check only the findings of:", data["prompt"])
        self.assertIn("reviews/REVIEW-INTEGRATION.md", data["prompt"])
        self.assertIn("Diff — the fixes:", data["prompt"])
        self.assertIn("The task is parked", data["collect"])
        nxt = sb.json("next", "rounds2")
        self.assertEqual(nxt["parked_task"], "REVIEW-INTEGRATION-2")
        self.assertEqual(nxt["ready"], [])
        self.assertIn("parked for the owner", sb.sae("next", "rounds2").stdout)
        self.assertIn("parked for the owner", sb.sae("status", "rounds2").stdout)
        proc = sb.sae("dispatch", "rounds2", "FINAL", code=3)
        self.assertIn("--override", proc.stderr)
        sb.sae("job", "add", "rounds2", "INTEGRATION-FIX-2", "--kind", "implementation",
               "--fix-of", "REVIEW-INTEGRATION", "--reason", "old round", code=1)  # only the last round
        sb.sae("job", "add", "rounds2", "INTEGRATION-FIX-2", "--kind", "implementation",
               "--fix-of", "REVIEW-INTEGRATION-2", "--reason", "owner wants one more round")
        self.assertIsNone(sb.json("next", "rounds2")["parked_task"])  # a fix job ends the parking


class StaleCheckTests(ReviewFlowCase):
    def passed_task(self, sb: Sandbox, slug: str) -> str:
        task = self.integration_task(sb, slug)
        self.review(sb, task, slug, "REVIEW-INTEGRATION", "integration", "pass")
        self.final(sb, task, slug)
        self.assertIn("All jobs done", sb.sae("next", slug).stdout)
        sb.sae("job", "add", slug, "LATE", "--kind", "implementation", "--reason", "found late")
        sb.job_file(task, "LATE")
        return task

    def test_late_merge_adds_a_round_and_resets_the_final_validation(self):
        sb = self.sandbox()
        task = self.passed_task(sb, "late")
        out = self.run_writer(sb, task, "late", "LATE")
        self.assertIn("FINAL is pending again", out)
        self.assertIn("Added REVIEW-INTEGRATION-2", out)
        jobs = sb.state(task)["jobs"]
        self.assertEqual(jobs["FINAL"]["status"], "pending")
        self.assertEqual(jobs["REVIEW-INTEGRATION-2"]["limit"], "changes")
        self.assertIn("LATE", jobs["REVIEW-INTEGRATION-2"]["needs"])
        self.assertTrue(any(e["type"] == "job.reset" and e["job"] == "FINAL" for e in sb.events(task)))
        proc = sb.sae("finish", "late", code=3)
        self.assertIn("REVIEW-INTEGRATION-2 (added by a late merge) has not run", proc.stderr)
        self.assertIn("FINAL (reset by a late merge) has not run again", proc.stderr)
        data = self.review(sb, task, "late", "REVIEW-INTEGRATION-2", "integration", "pass")
        self.assertIn("review only the changes since REVIEW-INTEGRATION", data["prompt"])
        since = jobs["REVIEW-INTEGRATION-2"]["since"]
        self.assertIn(f"diff {since}..task/{task}", data["prompt"])
        sb.sae("finish", "late", code=3)  # the final validation has not run again
        self.final(sb, task, "late")
        report = sb.sae("finish", "late").stdout
        self.assertIn("REVIEW-INTEGRATION-2 → integration, round 2: pass", report)
        self.assertNotIn("## Overridden gates", report)

    def test_finish_meets_a_done_unmerged_writer_after_the_checks(self):
        """REVIEW-PLAN finding 1: finish must not merge a writer after its gates passed."""
        sb = self.sandbox()
        task = self.passed_task(sb, "unmerged")
        self.run_writer(sb, task, "unmerged", "LATE", collect=False)
        state = sb.state(task)  # a collect that did not merge (an old sae, an interrupted run)
        state["jobs"]["LATE"]["status"] = "done"
        (sb.task_dir(task) / "state.json").write_text(json.dumps(state))
        proc = sb.sae("finish", "unmerged", code=3)
        self.assertIn("LATE is done but not merged", proc.stderr)
        self.assertIn(f"sae merge {task} LATE", proc.stderr)
        self.assertFalse(sb.state(task)["jobs"]["LATE"]["merged"])  # nothing merged by the refusal
        report = sb.sae("finish", "unmerged", "--override", "owner tested LATE by hand").stdout
        self.assertIn("stale gate: LATE. Reason: owner tested LATE by hand", report)
        self.assertTrue(sb.state(task)["jobs"]["LATE"]["merged"])
        self.assertEqual(sb.state(task)["task"]["phase"], "done")

    def test_merge_of_the_unmerged_writer_needs_fresh_checks(self):
        sb = self.sandbox()
        task = self.passed_task(sb, "remerge")
        self.run_writer(sb, task, "remerge", "LATE", collect=False)
        state = sb.state(task)
        state["jobs"]["LATE"]["status"] = "done"
        (sb.task_dir(task) / "state.json").write_text(json.dumps(state))
        out = sb.sae("merge", "remerge", "LATE").stdout
        self.assertIn("Added REVIEW-INTEGRATION-2", out)
        sb.sae("finish", "remerge", code=3)
        self.review(sb, task, "remerge", "REVIEW-INTEGRATION-2", "integration", "pass")
        self.final(sb, task, "remerge")
        sb.sae("finish", "remerge")


    def test_merge_while_the_final_validation_runs_makes_its_result_stale(self):
        """INTEGRATION-REVIEW finding 1: FINAL started before a late writer merged."""
        sb = self.sandbox()
        task = self.integration_task(sb, "racing")
        self.review(sb, task, "racing", "REVIEW-INTEGRATION", "integration", "pass")
        sb.sae("dispatch", "racing", "FINAL")
        sb.sae("job", "add", "racing", "LATE", "--kind", "implementation", "--reason", "found late")
        sb.job_file(task, "LATE")
        out = self.run_writer(sb, task, "racing", "LATE")
        self.assertIn("FINAL is running on older code", out)
        self.assertIn("Added REVIEW-INTEGRATION-2", out)
        jobs = sb.state(task)["jobs"]
        self.assertIn("REVIEW-INTEGRATION-2", jobs["FINAL"]["needs"])
        self.review(sb, task, "racing", "REVIEW-INTEGRATION-2", "integration", "pass")
        sb.result(task, "jobs/FINAL.result.md", status="done", summary="all met", validation="pass", changes="none")
        data = sb.json("collect", "racing", "FINAL")  # the result of the run that started before LATE
        self.assertEqual(data["status"], "pending")
        self.assertIn("its result does not count", " ".join(data["messages"]))
        proc = sb.sae("finish", "racing", code=3)
        self.assertIn("FINAL (reset by a late merge) has not run again", proc.stderr)
        self.final(sb, task, "racing")
        self.assertEqual(sb.state(task)["jobs"]["FINAL"]["status"], "done")
        sb.sae("finish", "racing")


class DisputedFindingTests(ReviewFlowCase):
    def test_collect_counts_disputes_that_the_summary_hides(self):
        """INTEGRATION-REVIEW finding 5: a done fix job with disputed findings."""
        sb = self.sandbox()
        task = self.planned(sb, "disputes", [("FIX", "implementation", "", []), ("QUIET", "implementation", "", [])])
        for job, section in (("FIX", "- Finding 2: the cache is not shared; see cache.py.\n"
                                     "  Evidence: one instance per process.\n"
                                     "- Finding 4: already handled by the retry loop.\n"),
                             ("QUIET", "<!-- Only when your job answers a review. -->\nNone.\n")):
            ws = dispatch_workspace(sb, task, job)
            sb.work(ws, f"{job.lower()}.txt", "x\n", f"{job}: work")
            sb.result(task, f"jobs/{job}.result.md", status="done", summary="fixed the review findings",
                      validation="pass", changes="made")
            path = sb.task_dir(task) / "jobs" / f"{job}.result.md"
            path.write_text(path.read_text() + "## Disputed findings\n" + section + "\n## Risks\n- none\n")
        data = sb.json("collect", "disputes", "FIX")
        self.assertEqual(data["disputed"], 2)
        self.assertIn("2 disputed findings: settle them (see execute.md)", data["messages"][0])
        quiet = sb.json("collect", "disputes", "QUIET")
        self.assertEqual(quiet["disputed"], 0)
        self.assertNotIn("disputed", " ".join(quiet["messages"]))
        collected = {e["job"]: e for e in sb.events(task) if e["type"] == "job.collected"}
        self.assertEqual((collected["FIX"]["disputed"], collected["QUIET"]["disputed"]), (2, 0))


class JobReviewRoundTests(ReviewFlowCase):
    def test_round_two_waits_for_the_fix_done_not_merged(self):
        sb = self.sandbox()
        task = self.planned(sb, "fixround", [
            ("CORE", "implementation", "", ["--review"]),
            ("SIDE", "implementation", "", []),
        ], settings=["review=selected-jobs"])
        self.assertEqual(sb.json("status", "fixround")["layout"], "worktrees")
        out = self.run_writer(sb, task, "fixround", "CORE")
        self.assertIn("Added REVIEW-CORE", out)
        self.review(sb, task, "fixround", "REVIEW-CORE", "CORE", "changes-required")
        sb.sae("job", "add", "fixround", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE",
               "--reason", "REVIEW-CORE: changes required")
        sb.job_file(task, "CORE-FIX-1")
        out = self.run_writer(sb, task, "fixround", "CORE-FIX-1")
        self.assertIn("Added REVIEW-CORE-2", out)
        jobs = sb.state(task)["jobs"]
        self.assertEqual(jobs["REVIEW-CORE-2"]["needs"], ["CORE", "CORE-FIX-1"])
        self.assertFalse(jobs["CORE-FIX-1"]["merged"])
        self.assertIn("REVIEW-CORE-2", [r["id"] for r in sb.json("next", "fixround")["ready"]])
        self.review(sb, task, "fixround", "REVIEW-CORE-2", "CORE", "pass")
        jobs = sb.state(task)["jobs"]
        self.assertTrue(jobs["CORE"]["merged"] and jobs["CORE-FIX-1"]["merged"])
        self.assertEqual((sb.task_worktree(task) / "core-fix-1.txt").read_text(), "CORE-FIX-1\n")

    def test_verdict_gate_on_an_unmerged_job_review(self):
        sb = self.sandbox(points=["all-jobs"])
        task = self.planned(sb, "jobgate", [("CORE", "implementation", "", [])])
        self.run_writer(sb, task, "jobgate", "CORE")
        self.review(sb, task, "jobgate", "REVIEW-CORE", "CORE", "changes-required")
        proc = sb.sae("finish", "jobgate", code=3)
        self.assertIn("REVIEW-CORE says changes-required", proc.stderr)
        self.assertIn("--fix-of CORE", proc.stderr)


class ResumeDoneJobTests(ReviewFlowCase):
    def test_research_follow_up(self):
        sb = self.sandbox()
        task = sb.new_task("Follow up", "follow")
        sb.sae("job", "add", "follow", "TOPIC", "--kind", "research")
        sb.sae("dispatch", "follow", "TOPIC")
        sb.result(task, "research/TOPIC.md", status="done", confidence="medium")
        sb.sae("collect", "follow", "TOPIC")
        path = sb.task_dir(task) / "jobs" / "TOPIC.md"
        path.write_text(path.read_text() + "\n- Does it scale?\n")  # under the template's section
        data = sb.json("dispatch", "follow", "TOPIC", "--resume", "--reason", "follow-up question")
        self.assertIn("Follow-up questions", data["prompt"])
        self.assertEqual(data["attempt"], 2)
        sb.result(task, "research/TOPIC.md", status="done", confidence="high")
        out = sb.sae("collect", "follow", "TOPIC").stdout
        self.assertIn("confidence high", out)
        sb.sae("dispatch", "follow", "TOPIC", "--resume", code=1)  # a reason is required

    def test_resume_done_planner_after_plan_review(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Replan", "replan")
        sb.sae("approve", "replan", "spec")
        sb.sae("job", "add", "replan", "PLAN", "--kind", "planning")
        sb.sae("dispatch", "replan", "PLAN")
        sb.sae("job", "add", "replan", "WORK", "--kind", "implementation")
        sb.job_file(task, "WORK", verify=["true"])
        sb.job_file(task, "PLAN")
        sb.result(task, "jobs/PLAN.result.md", status="done", summary="planned", validation="pass", changes="none")
        sb.sae("collect", "replan", "PLAN")
        self.assertEqual(sb.json("check", "replan")["due"], ["REVIEW-PLAN"])
        self.review(sb, task, "replan", "REVIEW-PLAN", "plan", "changes-required")
        data = sb.json("dispatch", "replan", "PLAN", "--resume", "--reason", "REVIEW-PLAN: changes required")
        self.assertIn("reviews/REVIEW-PLAN.md", data["prompt"])
        sb.sae("approve", "replan", "plan", code=3)  # the planner is running again
        sb.result(task, "jobs/PLAN.result.md", status="done", summary="replanned", validation="pass", changes="none")
        self.assertIn("replanned", sb.sae("collect", "replan", "PLAN").stdout)
        sb.sae("approve", "replan", "plan")


class ReviewMarkTests(ReviewFlowCase):
    def load(self, sb: Sandbox, task: str):
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib.reviews import planned_reviews, review_mark
            from sae_lib.tasks import Task
        finally:
            sys.path.remove(str(SCRIPTS))
        loaded = Task(sb.repo, task)
        loaded.load()
        return loaded, review_mark, planned_reviews

    def test_flags_without_job_reviews_and_forced_reviews(self):
        sb = self.sandbox(points=["spec", "plan", "integration"])
        task = sb.new_task("Marks", "marks")
        sb.sae("approve", "marks", "spec")
        for job, extra in (("FLAGGED", ["--review"]), ("PLAIN", []), ("FINAL", ["--kind", "validation", "--final"])):
            kind = [] if "--kind" in extra else ["--kind", "implementation"]
            out = sb.sae("job", "add", "marks", job, *kind, *extra).stdout
            if job == "FLAGGED":
                self.assertIn("job reviews are off", out)
            sb.job_file(task, job)
        loaded, review_mark, planned_reviews = self.load(sb, task)
        self.assertEqual(review_mark(loaded, "FLAGGED")["mark"], "no review · forced by settings")
        self.assertIsNone(review_mark(loaded, "PLAIN"))
        self.assertIsNone(review_mark(loaded, "FINAL"))
        planned = {p["id"]: p for p in planned_reviews(loaded)}
        self.assertEqual(sorted(planned), ["REVIEW-INTEGRATION", "REVIEW-PLAN"])
        self.assertEqual(sorted(planned["REVIEW-INTEGRATION"]["needs"]), ["FLAGGED", "PLAIN"])
        self.assertEqual(planned["REVIEW-INTEGRATION"]["needed_by"], ["FINAL"])
        warnings = sb.json("check", "marks")["warnings"]
        self.assertIn("flagged for review, but job reviews are off: FLAGGED", warnings)
        sb.sae("set", "marks", "review=all-jobs,integration")
        loaded, review_mark, planned_reviews = self.load(sb, task)
        self.assertEqual(review_mark(loaded, "PLAIN")["mark"], "review · forced by settings")
        self.assertEqual(review_mark(loaded, "FLAGGED")["mark"], "review")
        self.assertTrue(review_mark(loaded, "PLAIN")["reason"])
        planned = {p["id"]: p for p in planned_reviews(loaded, json.loads(sb.config.read_text()))}
        self.assertEqual(planned["REVIEW-PLAIN"]["needs"], ["PLAIN"])
        self.assertTrue(planned["REVIEW-PLAIN"]["model"])
        self.assertNotIn("job reviews are off", " ".join(sb.json("check", "marks")["warnings"]))



class NarrowReviewOutputTests(ReviewFlowCase):
    """[NARROW-OUTPUT] for the notices that ask for a decision, and the final report (07-cli-spec
    §13): 72 columns, commands and paths on their own lines."""

    def assert_narrow(self, *texts: str) -> None:
        for text in texts:
            self.assertEqual(wide_lines(text), [], text)

    def test_job_review_notices_fit_72_columns(self):
        sb = self.sandbox()
        task = self.planned(sb, "narrow-job-review-notices", [
            ("A-LONG-CORE-JOB-IDENTIFIER", "implementation", "", ["--review"]),
            ("SIDE", "implementation", "", []),
        ], settings=["review=selected-jobs,integration"])
        self.run_writer(sb, task, "narrow-job-review-notices", "A-LONG-CORE-JOB-IDENTIFIER")
        job_review = self.review(sb, task, "narrow-job-review-notices", "REVIEW-A-LONG-CORE-JOB-IDENTIFIER",
                                 "A-LONG-CORE-JOB-IDENTIFIER", "changes-required")["collect"]
        self.assertIn("changes required. Add fix jobs:", job_review)
        open_jobs = sb.sae("finish", "narrow-job-review-notices", code=3).stderr
        self.assertIn("Open jobs: SIDE", open_jobs)
        refused = sb.sae("finish", "narrow-job-review-notices", "--with-open", code=3).stderr
        self.assertIn("Finish refused", refused)
        self.assert_narrow(job_review, open_jobs, refused)

    def test_integration_review_notices_fit_72_columns(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "narrow-integration-review-notices")
        collect = self.review(sb, task, "narrow-integration-review-notices", "REVIEW-INTEGRATION", "integration",
                              "changes-required")["collect"]
        nxt = sb.sae("next", "narrow-integration-review-notices").stdout
        refused = sb.sae("finish", "narrow-integration-review-notices", code=3).stderr
        self.assertIn("REVIEW-INTEGRATION requires changes", nxt)
        self.assertIn("--fix-of REVIEW-INTEGRATION", collect)
        self.assert_narrow(collect, nxt, refused)

    def test_final_report_is_narrow_points_into_done_and_lists_drafts_and_effort(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "narrow-final-report")
        self.review(sb, task, "narrow-final-report", "REVIEW-INTEGRATION", "integration", "pass")
        self.final(sb, task, "narrow-final-report")
        draft = sb.json("adr", "new", "narrow-final-report", "Keep the status cache for sixty seconds",
                        "--type", "business")["file"]
        out = sb.sae("finish", "narrow-final-report").stdout
        report = out[out.index("# Final report"):]
        self.assert_narrow(report)
        details = report.splitlines()[report.splitlines().index("Details per requirement:") + 1].strip()
        self.assertIn(f"/.tasks/done/{task}/jobs/FINAL.result.md", details)
        self.assertTrue(Path(details).is_file(), details)
        self.assertIn(Path(draft).name, report)
        self.assertIn("## Findings, backlog items and decision drafts", report)
        self.assertIn("- LEFT · implementation · done, merged", report)
        self.assertIn("  attempt 1: claude · c-mid · low", report)  # model · effort per attempt
        self.assertNotIn("| models", report)

if __name__ == "__main__":
    unittest.main()
