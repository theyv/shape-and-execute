"""Exits from a fix loop: decision jobs at any time, `sae job drop`, `sae accept-review`, the
`--let-go` log and the final report's list of what was let go.

Spec: [DECISION-ANYTIME], [JOB-DROP], [ACCEPT-INTEGRATION], [LET-GO-REPORT], [TRIAGE]; the
changes-required lines of audit 2026-11-20, proposal 2.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from saetest import Sandbox, dispatch_workspace
from test_reviews import ReviewFlowCase


def review_text(target: str, verdict: str, findings: list[str]) -> str:
    """A review file with numbered findings in the shape of templates/review.md."""
    lines = ["---", f"target: {target}", f"verdict: {verdict}", "---", "", "# Review", "", "## Findings", ""]
    for n, title in enumerate(findings, 1):
        lines += [f"### {n}. {title} — major", "**Expected:** it works **Actual:** it does not", ""]
    return "\n".join(lines + ["## Notes", ""])


class FixLoopCase(ReviewFlowCase):
    def review_with(self, sb: Sandbox, task: str, slug: str, review: str, target: str, verdict: str,
                    findings: list[str]) -> str:
        sb.json("dispatch", slug, review)
        path = sb.task_dir(task) / "reviews" / f"{review}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(review_text(target, verdict, findings))
        return sb.sae("collect", slug, review).stdout

    def snapshot(self, sb: Sandbox, task: str) -> tuple[bytes, bytes]:
        folder = sb.task_dir(task)
        return (folder / "state.json").read_bytes(), (folder / "events.jsonl").read_bytes()

    def report(self, out: str) -> str:
        return out[out.index("# Final report"):]

    def section(self, report: str, heading: str) -> list[str]:
        lines = report.splitlines()
        start = lines.index(heading) + 1
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
        return [line for line in lines[start:end] if line.strip()]


class DecisionAnytimeTests(FixLoopCase):
    """[DECISION-ANYTIME]: --from any job or review round, --question, and a decision job that runs
    while the task is parked or held."""

    def test_question_alone_points_to_the_question(self):
        sb = self.sandbox()
        task = self.planned(sb, "dq", [("A", "implementation", "", [])])
        sb.sae("decision", "new", "dq", code=1)  # neither --from nor --question
        new = sb.json("decision", "new", "dq", "--question", "Keep the cache, or read through?")
        self.assertEqual(new["job"], "DECISION-1")
        text = (sb.task_dir(task) / "jobs" / "DECISION-1.md").read_text()
        self.assertIn("## Question\nKeep the cache, or read through?", text)
        self.assertNotIn("## Inputs", text)
        prompt = sb.json("dispatch", "dq", "DECISION-1")["prompt"]
        self.assertIn("jobs/DECISION-1.md", prompt)
        self.assertNotIn("Decision request", prompt)
        self.assertEqual(sb.json("decision", "new", "dq", "--question", "Second?")["job"], "DECISION-2")

    def test_review_round_parked_and_done_job_sources(self):
        sb = self.sandbox()
        task = self.planned(sb, "dsrc", [("A", "implementation", "", ["--review"]),
                                         ("P", "implementation", "", [])],
                            settings=["review=selected-jobs"])
        self.run_writer(sb, task, "dsrc", "A")
        self.review_with(sb, task, "dsrc", "REVIEW-A", "A", "changes-required", ["Wrong cache key"])
        # a review round: the job file and the prompt point to the review file
        new = sb.json("decision", "new", "dsrc", "--from", "REVIEW-A")
        self.assertEqual(new["job"], "DECISION-REVIEW-A-1")
        text = (sb.task_dir(task) / "jobs" / "DECISION-REVIEW-A-1.md").read_text()
        self.assertIn("reviews/REVIEW-A.md", text)
        self.assertNotIn("Decision request", text)
        prompt = sb.json("dispatch", "dsrc", "DECISION-REVIEW-A-1")["prompt"]
        self.assertIn("- Review round REVIEW-A — the findings: reviews/REVIEW-A.md", text)
        self.assertIn(f"Review round REVIEW-A — the findings:  {sb.task_dir(task) / 'reviews' / 'REVIEW-A.md'}",
                      prompt)
        self.assertNotIn("Decision request", prompt)
        # a done job that did not park: its job file and result, no Decision request section
        sb.json("decision", "new", "dsrc", "--from", "A", "--question", "Is the cache worth it?")
        text = (sb.task_dir(task) / "jobs" / "DECISION-A-1.md").read_text()
        self.assertIn("## Question\nIs the cache worth it?", text)
        # one list of inputs: the job file with relative paths, the prompt with absolute ones
        self.assertIn("## Inputs\n- Job file of A: jobs/A.md\n- Result of A: jobs/A.result.md\n", text)
        prompt = sb.json("dispatch", "dsrc", "DECISION-A-1")["prompt"]
        self.assertIn(f"Job file of A:                         {sb.task_dir(task) / 'jobs' / 'A.md'}\n"
                      f"Result of A:                           {sb.task_dir(task) / 'jobs' / 'A.result.md'}", prompt)
        self.assertNotIn("Decision request", prompt)
        # a parked job: as before, the Decision request of its result
        sb.sae("dispatch", "dsrc", "P")
        (sb.task_dir(task) / "jobs" / "P.result.md").write_text(
            "---\nstatus: parked\nsummary: needs a choice\nvalidation: not-run\nchanges: none\n---\n\n"
            "## Decision request\n**Decision required:** table or column?\n")
        sb.sae("collect", "dsrc", "P")
        self.assertEqual(sb.json("decision", "new", "dsrc", "--from", "P")["job"], "DECISION-P-1")
        text = (sb.task_dir(task) / "jobs" / "DECISION-P-1.md").read_text()
        self.assertIn('Answer the decision request of P.', text)
        self.assertIn('- Decision request of P (section "Decision request"): jobs/P.result.md', text)
        prompt = sb.json("dispatch", "dsrc", "DECISION-P-1")["prompt"]
        self.assertIn(f'Decision request of P (section "Decision request"): {sb.task_dir(task) / "jobs" / "P.result.md"}',
                      prompt)

    def test_decision_job_runs_while_the_round_limit_parks_the_task(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "dpark")
        sb.sae("set", "dpark", "max-review-rounds=1")
        self.review_with(sb, task, "dpark", "REVIEW-INTEGRATION", "integration", "changes-required", ["Slow path"])
        self.assertEqual(sb.json("status", "dpark")["parked_task"], "REVIEW-INTEGRATION")
        sb.sae("job", "add", "dpark", "LATE", "--kind", "implementation", "--reason", "more work")
        sb.job_file(task, "LATE")
        self.assertIn("The task is parked", sb.sae("dispatch", "dpark", "LATE", code=3).stderr)  # writers wait
        sb.json("decision", "new", "dpark", "--from", "REVIEW-INTEGRATION")
        self.assertIn("DECISION-REVIEW-INTEGRATION-1", [r["id"] for r in sb.json("next", "dpark")["ready"]])
        prompt = sb.json("dispatch", "dpark", "DECISION-REVIEW-INTEGRATION-1")["prompt"]
        self.assertIn("reviews/REVIEW-INTEGRATION.md", prompt)
        sb.result(task, "decisions/DECISION-REVIEW-INTEGRATION-1.md",
                  **{"class": "open-tradeoff", "recommendation": "human-required", "decision": "accept"})
        sb.sae("collect", "dpark", "DECISION-REVIEW-INTEGRATION-1")
        self.assertEqual(sb.state(task)["jobs"]["DECISION-REVIEW-INTEGRATION-1"]["status"], "done")
        self.assertEqual(sb.json("status", "dpark")["parked_task"], "REVIEW-INTEGRATION")  # it only advised

    def test_gate_order_during_a_hold(self):
        """A decision job passes a hold, a writer still waits, and a missing CLI changes nothing."""
        sb = self.sandbox()
        task = self.planned(sb, "dhold", [("A", "implementation", "", []), ("B", "implementation", "", [])])
        sb.sae("hold", "dhold", "A")
        self.run_writer(sb, task, "dhold", "A")
        self.assertEqual(sb.json("next", "dhold")["holds_active"], ["A"])
        sb.json("decision", "new", "dhold", "--from", "A")
        sb.without_cli("codex")
        before = self.snapshot(sb, task)
        refused = sb.sae("dispatch", "dhold", "DECISION-A-1", "--harness", "codex", code=1).stderr
        self.assertIn("codex CLI is not on the PATH", refused)
        self.assertEqual(self.snapshot(sb, task), before)
        self.assertIn("Hold after A", sb.sae("dispatch", "dhold", "B", code=3).stderr)
        self.assertEqual(self.snapshot(sb, task), before)
        ready = [r["id"] for r in sb.json("next", "dhold")["ready"]]
        self.assertEqual(ready, ["DECISION-A-1"])
        sb.sae("dispatch", "dhold", "DECISION-A-1")
        sb.result(task, "decisions/DECISION-A-1.md",
                  **{"class": "routine", "recommendation": "agent-decides", "decision": "go on"})
        sb.sae("collect", "dhold", "DECISION-A-1")
        self.assertEqual(sb.state(task)["jobs"]["DECISION-A-1"]["status"], "done")


class ChangesRequiredLinesTests(FixLoopCase):
    """Audit 2026-11-20, proposal 2: lead line, fix command with a fresh ID, let-go line, accept line."""

    def test_job_rounds(self):
        sb = self.sandbox()
        task = self.planned(sb, "lines", [("A", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs"])
        self.run_writer(sb, task, "lines", "A")
        out = self.review_with(sb, task, "lines", "REVIEW-A", "A", "changes-required", ["One"])
        self.assertEqual(out.strip().split("\n"), [
            "REVIEW-A: done — verdict: changes-required",
            "Triage the findings first (references/modes/execute.md, Loop step 3).",
            "Fix job for the findings you keep:",
            f'  sae job add {task} A-FIX-1 --kind implementation --fix-of A --reason "REVIEW-A: changes required"',
            "Each finding you set aside, logged with its reason:",
            f'  sae log {task} decision "<number>: <reason>" --job REVIEW-A --let-go',
            "Or accept the round when the mode lets you decide:",
            f'  sae merge {task} A --accept-review "<why>"'])  # no close: finish would wait for A's merge
        sb.sae("job", "add", "lines", "A-FIX-1", "--kind", "implementation", "--fix-of", "A", "--reason", "round 1")
        sb.job_file(task, "A-FIX-1")
        self.run_writer(sb, task, "lines", "A-FIX-1")
        out = self.review_with(sb, task, "lines", "REVIEW-A-2", "A", "changes-required", ["Two"])
        self.assertIn(f'sae job add {task} A-FIX-2 --kind implementation --fix-of A '
                      f'--reason "REVIEW-A-2: changes required"', out)
        self.assertIn(f'--job REVIEW-A-2 --let-go', out)
        self.assertIn(f'sae merge {task} A --accept-review "<why>"', out)

    def test_integration_round(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "ilines")
        out = self.review_with(sb, task, "ilines", "REVIEW-INTEGRATION", "integration", "changes-required", ["One"])
        lines = [
            "Triage the findings first (references/modes/execute.md, Loop step 3).",
            "Fix job for the findings you keep (sae adds the next round when it is merged):",
            f'  sae job add {task} INTEGRATION-FIX-1 --kind implementation --fix-of REVIEW-INTEGRATION '
            f'--reason "REVIEW-INTEGRATION: changes required"',
            "Each finding you set aside, logged with its reason:",
            f'  sae log {task} decision "<number>: <reason>" --job REVIEW-INTEGRATION --let-go',
            "Or accept the round when the mode lets you decide:",
            f'  sae accept-review {task} REVIEW-INTEGRATION --reason "<why>"',
            "Or close anyway, on the user's word:",
            f'  sae finish {task} --override "<reason>"']
        self.assertEqual(out.strip().split("\n"), ["REVIEW-INTEGRATION: done — verdict: changes-required"] + lines)
        refused = sb.sae("finish", "ilines", code=3).stderr
        self.assertIn(f'sae accept-review {task} REVIEW-INTEGRATION --reason "<why>"', refused)
        self.assertIn("  - or close anyway, on the user's word:", refused)
        # sae next names the round, then the same ways forward
        self.assertIn("\n".join(["REVIEW-INTEGRATION requires changes."] + lines), sb.sae("next", "ilines").stdout)


class AcceptIntegrationTests(FixLoopCase):
    """[ACCEPT-INTEGRATION], [LET-GO-REPORT]."""

    def test_accepted_round_lets_the_final_validation_and_finish_run(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "accint")
        self.review_with(sb, task, "accint", "REVIEW-INTEGRATION", "integration", "changes-required",
                         ["Log line too chatty", "Missing retry on a rare race", "Old name in a comment"])
        sb.sae("dispatch", "accint", "FINAL", code=1)  # waits for a positive round
        # one finding logged on its own, by its number: it keeps its own reason and appears once
        sb.sae("log", "accint", "decision", "2: beyond the Project Stakes", "--job", "REVIEW-INTEGRATION", "--let-go")
        out = sb.sae("accept-review", "accint", "REVIEW-INTEGRATION", "--reason", "cosmetic").stdout
        self.assertIn("REVIEW-INTEGRATION accepted: cosmetic", out)
        self.assertIn("FINAL", [r["id"] for r in sb.json("next", "accint")["ready"]])
        self.assertIsNone(sb.json("status", "accint")["integration"])
        sb.sae("accept-review", "accint", "REVIEW-INTEGRATION", "--reason", "again", code=1)
        self.final(sb, task, "accint")
        report = self.report(sb.sae("finish", "accint").stdout)  # no --override
        self.assertNotIn("## Overridden gates", report)
        self.assertEqual(self.section(report, "## Accepted integration rounds"), ["- REVIEW-INTEGRATION: cosmetic"])
        self.assertEqual(self.section(report, "## Findings let go"), [
            "- REVIEW-INTEGRATION: Missing retry on a rare race — let go: beyond the Project Stakes",
            "- REVIEW-INTEGRATION: Log line too chatty — accepted: cosmetic",
            "- REVIEW-INTEGRATION: Old name in a comment — accepted: cosmetic"])
        decision = [e for e in sb.events(task) if e["type"] == "decision" and e.get("accepted_review")]
        self.assertEqual(decision[0]["reason"], "cosmetic")

    def test_accept_at_the_round_limit_ends_the_park(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "acclimit")
        sb.sae("set", "acclimit", "max-review-rounds=1")
        self.review_with(sb, task, "acclimit", "REVIEW-INTEGRATION", "integration", "changes-required", ["X"])
        self.assertIn(f'sae accept-review {task} REVIEW-INTEGRATION --reason "<why>"', sb.sae("next", "acclimit").stdout)
        self.assertEqual(sb.json("status", "acclimit")["parked_task"], "REVIEW-INTEGRATION")
        sb.sae("accept-review", "acclimit", "REVIEW-INTEGRATION", "--reason", "user: good enough")
        self.assertIsNone(sb.json("status", "acclimit")["parked_task"])
        self.assertEqual([r["id"] for r in sb.json("next", "acclimit")["ready"]], ["FINAL"])
        refused = sb.sae("job", "add", "acclimit", "INTEGRATION-FIX-1", "--kind", "implementation",
                         "--fix-of", "REVIEW-INTEGRATION", "--reason", "x", code=1).stderr
        self.assertIn("accepted", refused)

    def test_refusals(self):
        sb = self.sandbox()
        task = self.planned(sb, "accref", [("A", "implementation", "", ["--review"]),
                                           ("B", "implementation", "", [])],
                            settings=["review=selected-jobs,integration"])
        self.run_writer(sb, task, "accref", "A")
        self.review_with(sb, task, "accref", "REVIEW-A", "A", "changes-required", ["One"])
        self.assertIn(f'--reason is empty: sae accept-review {task} REVIEW-A --reason "<why>"',
                      sb.sae("accept-review", "accref", "REVIEW-A", "--reason", "", code=1).stderr)
        refused = sb.sae("accept-review", "accref", "REVIEW-A", "--reason", "x", code=1).stderr
        self.assertIn(f'sae merge {task} A --accept-review "<why>"', refused)
        sb.sae("accept-review", "accref", "A", "--reason", "x", code=1)  # not a review round
        sb.sae("merge", "accref", "A", "--accept-review", "fine")
        self.run_writer(sb, task, "accref", "B")
        self.review_with(sb, task, "accref", "REVIEW-INTEGRATION", "integration", "pass", [])
        refused = sb.sae("accept-review", "accref", "REVIEW-INTEGRATION", "--reason", "x", code=1).stderr
        self.assertIn("only a changes-required round is accepted", refused)


class LetGoReportTests(FixLoopCase):
    """[TRIAGE], [LET-GO-REPORT]: findings set aside in triage and accepted job reviews."""

    def test_triage_scenario_one_fix_one_finding_let_go(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "triage")
        self.review_with(sb, task, "triage", "REVIEW-INTEGRATION", "integration", "changes-required",
                         ["Startup crashes without a config", "Lock for a nearly impossible race"])
        sb.sae("log", "triage", "decision", "2: beyond the Project Stakes", "--job", "REVIEW-INTEGRATION", "--let-go")
        sb.sae("log", "triage", "decision", "x: y", "--job", "LEFT", "--let-go", code=1)  # not a review
        sb.sae("log", "triage", "note", "x", "--job", "REVIEW-INTEGRATION", "--let-go", code=1)
        sb.sae("job", "add", "triage", "INTEGRATION-FIX-1", "--kind", "implementation",
               "--fix-of", "REVIEW-INTEGRATION", "--reason", "finding 1")
        sb.job_file(task, "INTEGRATION-FIX-1")
        out = self.run_writer(sb, task, "triage", "INTEGRATION-FIX-1")
        self.assertIn("Added REVIEW-INTEGRATION-2", out)
        self.review_with(sb, task, "triage", "REVIEW-INTEGRATION-2", "integration", "pass", [])
        self.final(sb, task, "triage")
        report = self.report(sb.sae("finish", "triage").stdout)
        self.assertEqual(self.section(report, "## Findings let go"),
                         ["- REVIEW-INTEGRATION: Lock for a nearly impossible race — let go: beyond the Project Stakes"])
        self.assertNotIn("Startup crashes", report)
        check = self.section(report, "## To check before you merge")
        self.assertFalse([line for line in check if "nearly impossible race" in line])  # listed once

    def test_accepted_job_review_lists_each_finding_once(self):
        sb = self.sandbox()
        task = self.planned(sb, "jaccept", [("A", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs"])
        self.run_writer(sb, task, "jaccept", "A")
        self.review_with(sb, task, "jaccept", "REVIEW-A", "A", "changes-required",
                         ["Name is unclear", "Speculative lock", "Missing docstring"])
        sb.sae("log", "jaccept", "decision", "2: no concurrent caller exists", "--job", "REVIEW-A", "--let-go")
        sb.sae("merge", "jaccept", "A", "--accept-review", "style only")
        report = self.report(sb.sae("finish", "jaccept").stdout)
        self.assertEqual(self.section(report, "## Findings let go"), [
            "- REVIEW-A: Speculative lock — let go: no concurrent caller exists",
            "- REVIEW-A: Name is unclear — accepted: style only",
            "- REVIEW-A: Missing docstring — accepted: style only"])
        self.assertEqual(report.count("Speculative lock"), 1)


class JobDropTests(FixLoopCase):
    """[JOB-DROP]."""

    def drop_task(self, sb: Sandbox, slug: str) -> str:
        """LEFT, RIGHT (reviewed, one fix round), FINAL needs both; integration review on."""
        task = self.planned(sb, slug, [
            ("LEFT", "implementation", "", []),
            ("RIGHT", "implementation", "", ["--review"]),
            ("FINAL", "validation", "LEFT,RIGHT", ["--final"]),
        ], settings=["review=selected-jobs,integration"])
        self.run_writer(sb, task, slug, "RIGHT")
        self.review_with(sb, task, slug, "REVIEW-RIGHT", "RIGHT", "changes-required", ["Wrong approach"])
        sb.sae("job", "add", slug, "RIGHT-FIX-1", "--kind", "implementation", "--fix-of", "RIGHT",
               "--reason", "round 1")
        sb.job_file(task, "RIGHT-FIX-1")
        return task

    def test_drop_then_the_integration_review_and_final_validation_run(self):
        sb = self.sandbox()
        task = self.drop_task(sb, "drop")
        ws = dispatch_workspace(sb, task, "RIGHT-FIX-1")
        # a running member blocks the drop, before any change
        before = self.snapshot(sb, task)
        refused = sb.sae("job", "drop", "drop", "RIGHT", "--reason", "x", code=1).stderr
        self.assertIn("RIGHT-FIX-1 is running", refused)
        self.assertEqual(self.snapshot(sb, task), before)
        sb.work(ws, "right-fix.txt", "fix\n", "RIGHT-FIX-1: fix")
        sb.result(task, "jobs/RIGHT-FIX-1.result.md", status="done", summary="fix", validation="pass",
                  changes="made")
        self.assertIn("Added REVIEW-RIGHT-2", sb.sae("collect", "drop", "RIGHT-FIX-1").stdout)
        # a fix job alone is refused with its target
        refused = sb.sae("job", "drop", "drop", "RIGHT-FIX-1", "--reason", "x", code=1).stderr
        self.assertIn(f"sae job drop {task} RIGHT", refused)
        # a job outside the group needs RIGHT: refused with the edit call, before any change
        before = self.snapshot(sb, task)
        refused = sb.sae("job", "drop", "drop", "RIGHT", "--reason", "x", code=1).stderr
        self.assertIn(f'sae job edit {task} FINAL --needs "LEFT" --reason "RIGHT is dropped"', refused)
        self.assertEqual(self.snapshot(sb, task), before)
        sb.sae("job", "edit", "drop", "FINAL", "--needs", "LEFT", "--reason", "RIGHT is dropped")
        # FIX-LOOP-TEXTS issue 8: argparse owns a missing --reason; sae names an empty one
        self.assertIn("the following arguments are required: --reason",
                      sb.sae("job", "drop", "drop", "RIGHT", code=1).stderr)
        self.assertIn("--reason is empty: give the user's reason to drop the job.",
                      sb.sae("job", "drop", "drop", "RIGHT", "--reason", " ", code=1).stderr)
        out = sb.sae("job", "drop", "drop", "RIGHT", "--reason", "user: wrong approach").stdout
        self.assertIn("Dropped RIGHT, RIGHT-FIX-1, REVIEW-RIGHT, REVIEW-RIGHT-2: user: wrong approach", out)
        jobs = sb.state(task)["jobs"]
        for member in ("RIGHT", "RIGHT-FIX-1", "REVIEW-RIGHT", "REVIEW-RIGHT-2"):
            self.assertEqual(jobs[member]["status"], "dropped", member)
            self.assertEqual(jobs[member]["drop"]["group"], "RIGHT")
        self.assertEqual(jobs["REVIEW-RIGHT-2"]["drop"]["was"], "pending")
        types = [e["type"] for e in sb.events(task)]
        self.assertIn("job.dropped", types)
        decision = [e for e in sb.events(task) if e["type"] == "decision" and e.get("dropped")]
        self.assertEqual(decision[0]["by"], "human")
        # dropped jobs never merge and never run again
        self.assertIn("dropped", sb.sae("merge", "drop", "RIGHT", "--accept-review", "x", code=1).stderr)
        self.assertIn("dropped", sb.sae("dispatch", "drop", "REVIEW-RIGHT-2", code=1).stderr)
        refused = sb.sae("job", "add", "drop", "RIGHT-FIX-2", "--kind", "implementation", "--fix-of", "RIGHT",
                         "--reason", "x", code=1).stderr
        self.assertIn("RIGHT is dropped", refused)
        # the integration review becomes ready once the other writer merges
        self.assertNotIn("REVIEW-INTEGRATION", sb.state(task)["jobs"])
        out = self.run_writer(sb, task, "drop", "LEFT")
        self.assertIn("Added REVIEW-INTEGRATION", out)
        self.assertEqual(sb.state(task)["jobs"]["REVIEW-INTEGRATION"]["needs"], ["LEFT"])
        self.assertEqual([r["id"] for r in sb.json("next", "drop")["ready"]], ["REVIEW-INTEGRATION"])
        self.review_with(sb, task, "drop", "REVIEW-INTEGRATION", "integration", "pass", [])
        self.assertEqual([r["id"] for r in sb.json("next", "drop")["ready"]], ["FINAL"])
        self.final(sb, task, "drop")
        self.assertIn("All jobs done", sb.sae("next", "drop").stdout)
        report = self.report(sb.sae("finish", "drop").stdout)  # no --with-open, no --override
        self.assertEqual(self.section(report, "## Dropped jobs"), [
            "- RIGHT (with RIGHT-FIX-1, REVIEW-RIGHT, REVIEW-RIGHT-2): user: wrong approach",
            "  Their branches stay; nothing of them was merged."])
        # FIX-LOOP-TEXTS issue 10: the dropped group's reviews are no open verdicts, and a member
        # that never ran is no job line; "Dropped jobs" names them
        self.assertEqual([line for line in self.section(report, "## Reviews") if "RIGHT" in line], [])
        jobs_section = self.section(report, "## Jobs")
        self.assertFalse([line for line in jobs_section if line.startswith("- REVIEW-RIGHT-2 ")])
        self.assertIn("- RIGHT · implementation · dropped", jobs_section)
        files = sb.git("ls-tree", "-r", "--name-only", f"task/{task}").splitlines()
        self.assertIn("left.txt", files)
        self.assertNotIn("right.txt", files)
        self.assertNotIn("right-fix.txt", files)
        self.assertTrue(sb.git("branch", "--list", f"job/{task}/RIGHT"))  # the branch stays
        self.assertTrue((sb.task_dir(task) / "jobs" / "RIGHT-FIX-1.result.md").is_file())

    def test_refused_without_worktrees_before_any_change(self):
        sb = self.sandbox(points=["all-jobs"])
        task = self.planned(sb, "dchain", [("CORE", "implementation", "", [])])
        sb.sae("set", "dchain", "max-review-rounds=1")
        self.assertEqual(sb.json("status", "dchain")["layout"], "chain")
        self.run_writer(sb, task, "dchain", "CORE")
        self.review_with(sb, task, "dchain", "REVIEW-CORE", "CORE", "changes-required", ["X"])
        self.assertEqual(sb.state(task)["jobs"]["CORE"]["status"], "parked")
        before = self.snapshot(sb, task)
        refused = sb.sae("job", "drop", "dchain", "CORE", "--reason", "x", code=1).stderr
        self.assertIn("a task without worktrees", refused)
        self.assertEqual(self.snapshot(sb, task), before)

    def test_refused_for_pending_merged_and_non_writer_jobs(self):
        sb = self.sandbox()
        task = self.planned(sb, "dother", [("A", "implementation", "", []), ("B", "implementation", "", [])])
        self.assertIn("sae job remove", sb.sae("job", "drop", "dother", "B", "--reason", "x", code=1).stderr)
        self.run_writer(sb, task, "dother", "A")
        self.assertIn("merged already", sb.sae("job", "drop", "dother", "A", "--reason", "x", code=1).stderr)
        sb.json("decision", "new", "dother", "--question", "q?")
        sb.sae("job", "drop", "dother", "DECISION-1", "--reason", "x", code=1)


class ReviewFixLoopExitsTests(FixLoopCase):
    """REVIEW-FIX-LOOP-EXITS findings 1-4."""

    def test_integrate_job_is_not_dropped_alone(self):
        """Finding 1: INTEGRATE-<ID> dropped alone would leave its target unmergeable."""
        sb = self.sandbox()
        task = self.planned(sb, "dint", [("LEFT", "implementation", "", []), ("RIGHT", "implementation", "", [])])
        ws_l = dispatch_workspace(sb, task, "LEFT")
        ws_r = dispatch_workspace(sb, task, "RIGHT")
        sb.work(ws_l, "app.txt", "left\n", "LEFT: edit")
        sb.work(ws_r, "app.txt", "right\n", "RIGHT: edit")
        for job in ("LEFT", "RIGHT"):
            sb.result(task, f"jobs/{job}.result.md", status="done", summary=job, validation="pass", changes="made")
        sb.sae("collect", "dint", "LEFT")
        self.assertIn("INTEGRATE-RIGHT", sb.sae("collect", "dint", "RIGHT", code=4).stdout)
        sb.sae("dispatch", "dint", "INTEGRATE-RIGHT")
        (sb.task_dir(task) / "jobs" / "INTEGRATE-RIGHT.result.md").write_text(
            "---\nstatus: parked\nsummary: unclear\nvalidation: not-run\nchanges: none\n---\n\n"
            "## Decision request\n**Decision required:** which side wins?\n")
        sb.sae("collect", "dint", "INTEGRATE-RIGHT")
        before = self.snapshot(sb, task)
        refused = sb.sae("job", "drop", "dint", "INTEGRATE-RIGHT", "--reason", "x", code=1).stderr
        self.assertIn(f'sae job drop {task} RIGHT --reason "<why>"', refused)
        self.assertEqual(self.snapshot(sb, task), before)
        out = sb.sae("job", "drop", "dint", "RIGHT", "--reason", "owner: not needed").stdout
        self.assertIn("Dropped RIGHT, INTEGRATE-RIGHT", out)

    def test_accept_review_records_the_completed_round_not_a_pending_one(self):
        """Finding 2: a newer round still pending is not the round the merge bypasses."""
        sb = self.sandbox()
        task = self.planned(sb, "apend", [("A", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs"])
        self.run_writer(sb, task, "apend", "A")
        self.review_with(sb, task, "apend", "REVIEW-A", "A", "changes-required", ["Name is unclear", "Odd log"])
        sb.sae("job", "add", "apend", "A-FIX-1", "--kind", "implementation", "--fix-of", "A", "--reason", "round 1")
        sb.job_file(task, "A-FIX-1")
        self.assertIn("Added REVIEW-A-2", self.run_writer(sb, task, "apend", "A-FIX-1"))
        sb.sae("merge", "apend", "A", "--accept-review", "style only")
        decision = [e for e in sb.events(task) if e["type"] == "decision" and e.get("accepted_review")]
        self.assertEqual(decision[0]["accepted_review"], "REVIEW-A")
        report = self.report(sb.sae("finish", "apend", "--with-open").stdout)
        self.assertEqual(self.section(report, "## Findings let go"), [
            "- REVIEW-A: Name is unclear — accepted: style only",
            "- REVIEW-A: Odd log — accepted: style only"])

    def test_accept_review_after_a_passing_round_records_no_accepted_round(self):
        """REVIEW-FIX-LOOP-EXITS-2 finding 1: round 2 passed, the merge then conflicted; accepting
        the review must not list the superseded round 1's findings as let go."""
        sb = self.sandbox()
        task = self.planned(sb, "apass", [("LEFT", "implementation", "", []),
                                          ("A", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs"])
        ws_l = dispatch_workspace(sb, task, "LEFT")
        ws_a = dispatch_workspace(sb, task, "A")
        sb.work(ws_l, "app.txt", "left\n", "LEFT: edit")
        sb.work(ws_a, "app.txt", "a\n", "A: edit")
        for job in ("LEFT", "A"):
            sb.result(task, f"jobs/{job}.result.md", status="done", summary=job, validation="pass", changes="made")
            sb.sae("collect", "apass", job)
        self.review_with(sb, task, "apass", "REVIEW-A", "A", "changes-required", ["Name is unclear"])
        sb.sae("job", "add", "apass", "A-FIX-1", "--kind", "implementation", "--fix-of", "A", "--reason", "round 1")
        sb.job_file(task, "A-FIX-1")
        self.assertIn("Added REVIEW-A-2", self.run_writer(sb, task, "apass", "A-FIX-1"))
        sb.json("dispatch", "apass", "REVIEW-A-2")
        path = sb.task_dir(task) / "reviews" / "REVIEW-A-2.md"
        path.write_text(review_text("A", "pass", []))
        sb.sae("collect", "apass", "REVIEW-A-2", code=4)
        self.assertFalse(sb.state(task)["jobs"]["A"]["merged"])
        sb.sae("merge", "apass", "A", "--accept-review", "conflict resolved by hand", code=4)
        decisions = [e for e in sb.events(task) if e["type"] == "decision" and e.get("job") == "A"]
        self.assertTrue(decisions)
        self.assertNotIn("accepted_review", decisions[-1])

    def test_let_go_refuses_an_absent_finding(self):
        """REVIEW-FIX-LOOP-EXITS-2 finding 2: the number must name exactly one finding of the
        review."""
        sb = self.sandbox()
        task = self.integration_task(sb, "letabs")
        self.review_with(sb, task, "letabs", "REVIEW-INTEGRATION", "integration", "changes-required", ["One"])
        before = self.snapshot(sb, task)
        refused = sb.sae("log", "letabs", "decision", "2: rare", "--job", "REVIEW-INTEGRATION", "--let-go",
                         code=1).stderr
        self.assertIn("REVIEW-INTEGRATION has no finding 2; its findings are 1:", refused)
        self.assertEqual(self.snapshot(sb, task), before)

    def test_let_go_by_title_when_the_review_numbers_no_finding(self):
        """FIX-LOOP-TEXTS issue 14: a review without numbered findings still lets a finding go, by
        its title; a review without a verdict says when its findings can go."""
        sb = self.sandbox()
        task = self.integration_task(sb, "lettitle")
        sb.json("dispatch", "lettitle", "REVIEW-INTEGRATION")
        refused = sb.sae("log", "lettitle", "decision", "1: rare", "--job", "REVIEW-INTEGRATION", "--let-go",
                         code=1).stderr
        self.assertIn(f"REVIEW-INTEGRATION is running: it has no findings to let go yet. Log them after "
                      f"sae collect {task} REVIEW-INTEGRATION.", refused)
        path = sb.task_dir(task) / "reviews" / "REVIEW-INTEGRATION.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text("---\ntarget: integration\nverdict: changes-required\n---\n\n# Review\n\n## Findings\n\n"
                        "### Slow path — major\n**Expected:** fast\n\n### Odd log — minor\n**Expected:** quiet\n")
        out = sb.sae("collect", "lettitle", "REVIEW-INTEGRATION").stdout
        line = f'sae log {task} decision "<finding>: <reason>" --job REVIEW-INTEGRATION --let-go'
        self.assertIn(f"  {line}", out)
        before = self.snapshot(sb, task)
        refused = sb.sae("log", "lettitle", "decision", "2: rare", "--job", "REVIEW-INTEGRATION", "--let-go",
                         code=1).stderr
        self.assertEqual(refused.strip().split("\n")[-2:], [
            "REVIEW-INTEGRATION numbers none of its findings: name the finding by its title.", f"  {line}"])
        refused = sb.sae("log", "lettitle", "decision", "Odd log:", "--job", "REVIEW-INTEGRATION", "--let-go",
                         code=1).stderr
        self.assertIn('--let-go needs a reason after "Odd log:"', refused)
        self.assertEqual(self.snapshot(sb, task), before)
        sb.sae("log", "lettitle", "decision", "Odd log: cosmetic", "--job", "REVIEW-INTEGRATION", "--let-go")
        sb.sae("accept-review", "lettitle", "REVIEW-INTEGRATION", "--reason", "slow only in tests")
        self.final(sb, task, "lettitle")
        report = self.report(sb.sae("finish", "lettitle").stdout)
        self.assertEqual(self.section(report, "## Findings let go"), [
            "- REVIEW-INTEGRATION: Odd log — let go: cosmetic",
            "- REVIEW-INTEGRATION: Slow path — accepted: slow only in tests"])

    def test_let_go_refuses_a_blank_reason(self):
        """REVIEW-FIX-LOOP-EXITS-2 finding 2: "2:" names a finding but gives no reason."""
        sb = self.sandbox()
        task = self.integration_task(sb, "letblank")
        self.review_with(sb, task, "letblank", "REVIEW-INTEGRATION", "integration", "changes-required",
                         ["Retry", "Odd log"])
        before = self.snapshot(sb, task)
        for summary in ("2:", "2:   "):
            refused = sb.sae("log", "letblank", "decision", summary, "--job", "REVIEW-INTEGRATION", "--let-go",
                             code=1).stderr
            self.assertIn("reason", refused)
        self.assertEqual(self.snapshot(sb, task), before)

    def test_let_go_names_one_finding_by_number(self):
        """Finding 3: a title that starts another finding's title hides nothing."""
        sb = self.sandbox()
        task = self.integration_task(sb, "letnum")
        out = self.review_with(sb, task, "letnum", "REVIEW-INTEGRATION", "integration", "changes-required",
                               ["Retry", "Retry on timeout"])
        self.assertIn(f'sae log {task} decision "<number>: <reason>" --job REVIEW-INTEGRATION --let-go', out)
        refused = sb.sae("log", "letnum", "decision", "Retry on timeout: rare", "--job", "REVIEW-INTEGRATION",
                         "--let-go", code=1).stderr
        self.assertIn("by its number", refused)
        refused = sb.sae("log", "letnum", "decision", "3: rare", "--job", "REVIEW-INTEGRATION", "--let-go",
                         code=1).stderr
        self.assertIn("REVIEW-INTEGRATION has no finding 3", refused)
        sb.sae("log", "letnum", "decision", "2: too rare", "--job", "REVIEW-INTEGRATION", "--let-go")
        sb.sae("log", "letnum", "decision", "#2: rare in production", "--job", "REVIEW-INTEGRATION", "--let-go")
        sb.sae("accept-review", "letnum", "REVIEW-INTEGRATION", "--reason", "cosmetic")
        self.final(sb, task, "letnum")
        report = self.report(sb.sae("finish", "letnum").stdout)
        self.assertEqual(self.section(report, "## Findings let go"), [
            "- REVIEW-INTEGRATION: Retry on timeout — let go: rare in production",
            "- REVIEW-INTEGRATION: Retry — accepted: cosmetic"])

    def test_decision_job_for_a_review_limit_park_points_to_the_review(self):
        """Finding 4: sae parked the job at the round limit; its result holds no Decision request."""
        sb = self.sandbox()
        task = self.planned(sb, "dlim", [("A", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs", "max-review-rounds=1"])
        self.run_writer(sb, task, "dlim", "A")
        self.review_with(sb, task, "dlim", "REVIEW-A", "A", "changes-required", ["Wrong cache key"])
        self.assertEqual(sb.state(task)["jobs"]["A"]["status"], "parked")
        sb.json("decision", "new", "dlim", "--from", "A")
        text = (sb.task_dir(task) / "jobs" / "DECISION-A-1.md").read_text()
        self.assertNotIn("Decision request", text)
        self.assertIn("## Inputs\n- Review round that parked A: reviews/REVIEW-A.md\n- Job file of A: jobs/A.md\n"
                      "- Result of A: jobs/A.result.md\n", text)
        prompt = sb.json("dispatch", "dlim", "DECISION-A-1")["prompt"]
        self.assertNotIn("Decision request", prompt)
        self.assertIn(f"Review round that parked A:            {sb.task_dir(task) / 'reviews' / 'REVIEW-A.md'}", prompt)


if __name__ == "__main__":
    unittest.main()
