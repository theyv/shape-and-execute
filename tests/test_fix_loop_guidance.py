"""Guidance in a fix loop: the approach paragraph near the round limit, the pointer to an Approach
proposal in the next review round, and the story of a park at the round limit.

Run from the repository root:  python3 tests/run.py test_fix_loop_guidance
Spec: [APPROACH-CHECK], [FIX-WORKER], [PARK-STORY]; audit 2026-11-20 proposals 2 and 3.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from saetest import SCRIPTS, Sandbox
from test_reviews import ReviewFlowCase

sys.path.insert(0, str(SCRIPTS))
from sae_lib.park_story import PARK_OPENING  # noqa: E402

OPENING = "run an option only after the user answers"
PARAGRAPH = "Before you patch, read the earlier review rounds of"
POINTER = 'Read first: the "Approach proposal" in'
COLLECT_PROPOSAL = "read that section; it is a decision (references/modes/execute.md, Decision flow)."


def review_text(target: str, verdict: str, findings: list[tuple[str, str]]) -> str:
    lines = ["---", f"target: {target}", f"verdict: {verdict}", "---", "", "# Review", "", "## Findings", ""]
    for n, (title, fix) in enumerate(findings, start=1):
        lines += [f"### {n}. {title} — major", "**Evidence:** app.txt:1", "**Expected:** it works **Actual:** no",
                  f"**Suggested fix:** {fix}", ""]
    return "\n".join(lines)


def fix_job_text(job: str, objective: str, limits: list[str]) -> str:
    return "\n".join(["---", f"id: {job}", "covers: [TEST-REQ]", "verify: []", "---", "", f"# {job}: fix", "",
                      "## Objective", objective, "", "## Boundaries", *[f"- {l}" for l in limits], ""])


def result_text(summary: str, proposal: str | None = None) -> str:
    lines = ["---", "status: done", f"summary: {summary}", "validation: pass", "changes: made", "---", "",
             "# Result", ""]
    if proposal is not None:
        lines += ["## Approach proposal", "<!-- Only when a different approach would help. -->", proposal, ""]
    return "\n".join(lines)


class GuidanceCase(ReviewFlowCase):
    def review_round(self, sb: Sandbox, task: str, slug: str, review: str, target: str,
                     findings: list[tuple[str, str]], verdict: str = "changes-required") -> dict:
        data = sb.json("dispatch", slug, review)
        (sb.task_dir(task) / "reviews").mkdir(exist_ok=True)
        (sb.task_dir(task) / "reviews" / f"{review}.md").write_text(review_text(target, verdict, findings))
        data["collect"] = sb.sae("collect", slug, review).stdout
        return data

    def fix(self, sb: Sandbox, task: str, slug: str, fix: str, fix_of: str, *, limits=(), summary="fixed",
            proposal: str | None = None) -> dict:
        """Adds, dispatches and collects one fix job; returns the dispatch data with `collect`."""
        sb.sae("job", "add", slug, fix, "--kind", "implementation", "--fix-of", fix_of, "--reason", "fix")
        (sb.task_dir(task) / "jobs" / f"{fix}.md").write_text(fix_job_text(fix, f"Fix {fix_of}.", list(limits)))
        data = sb.json("dispatch", slug, fix)
        sb.work(Path(data["workspace"]), f"{fix.lower()}.txt", f"{fix}\n", f"{fix}: work")
        (sb.task_dir(task) / "jobs" / f"{fix}.result.md").write_text(result_text(summary, proposal))
        data["collect"] = sb.sae("collect", slug, fix).stdout
        return data

    def job_task(self, sb: Sandbox, slug: str, rounds: int) -> str:
        task = self.planned(sb, slug, [("CORE", "implementation", "", ["--review"])],
                            settings=["review=selected-jobs", f"max-review-rounds={rounds}"])
        sb.job_file(task, "CORE", objective="Cache the claim status for the portal.")
        self.run_writer(sb, task, slug, "CORE")
        return task


class JobApproachCheckTests(GuidanceCase):
    def test_three_rounds_paragraph_story_and_raised_limit(self):
        sb = self.sandbox()
        task = self.job_task(sb, "jthree", 3)
        self.review_round(sb, task, "jthree", "REVIEW-CORE", "CORE", [("Stale status after an update", "Clear the cache on write")])
        first = self.fix(sb, task, "jthree", "CORE-FIX-1", "CORE",
                         limits=["Do not touch the portal, because the portal is out of scope."], summary="clears on write")
        self.assertNotIn(PARAGRAPH, first["prompt"])  # N = 3: not after round 1
        self.assertNotIn("approach_check", sb.state(task)["jobs"]["CORE-FIX-1"])
        self.review_round(sb, task, "jthree", "REVIEW-CORE-2", "CORE", [("Stale status after a delete", "Clear it on delete too")])
        second = self.fix(sb, task, "jthree", "CORE-FIX-2", "CORE", summary="clears on delete")
        self.assertIn("FIX 2 of CORE. CORE parks for the owner after review round 3.", second["prompt"])
        self.assertIn(PARAGRAPH + " CORE", second["prompt"])
        self.assertIn(str(sb.task_dir(task) / "reviews" / "REVIEW-CORE.md"), second["prompt"])
        self.assertIn(str(sb.task_dir(task) / "reviews" / "REVIEW-CORE-2.md"), second["prompt"])
        parked = self.review_round(sb, task, "jthree", "REVIEW-CORE-3", "CORE",
                                   [("Stale status after a bulk import", "Store the status once, not derived")])
        # audit proposal 2: the park message opens with the round-limit line and points to the story,
        # which alone prints the options in full
        self.assertEqual(parked["collect"].strip().split("\n")[1:], [
            PARK_OPENING,
            "CORE parked: 3 review rounds required changes (max-review-rounds is 3). "
            f"The story and the options to relay: sae next {task}"])
        for command in ("next", "status"):
            text = sb.sae(command, "jthree").stdout
            story = text[text.index(PARK_OPENING):]
            self.assertIn("CORE is parked for the user: 3 review rounds required changes (max-review-rounds 3).", story)
            self.assertIn("Objective of CORE: Cache the claim status for the portal.", story)
            self.assertIn("Its result: CORE", story)
            self.assertIn("Round 1 — REVIEW-CORE: changes-required\n  Finding: Stale status after an update\n"
                          "    Suggested fix: Clear the cache on write\n  Fix CORE-FIX-1 (done): clears on write\n"
                          "    Limit: Do not touch the portal, because the portal is out of scope.", story)
            self.assertIn("Round 2 — REVIEW-CORE-2: changes-required", story)
            self.assertIn("  Fix CORE-FIX-2 (done): clears on delete", story)
            self.assertIn("Round 3 — REVIEW-CORE-3: changes-required\n  Finding: Stale status after a bulk import\n"
                          "    Suggested fix: Store the status once, not derived", story)
            for option in ("another round:", "change the approach:", "reduce the requirement:", "accept:"):
                self.assertIn(f"  - {option}", story)
            self.assertIn("\n".join([
                "Options:",
                "  - another round:",
                f'    sae job add {task} CORE-FIX-3 --kind implementation --fix-of CORE '
                f'--reason "REVIEW-CORE-3: changes required"',
                f"    sae set {task} max-review-rounds=4",
                "  - change the approach:",
                f'    sae job drop {task} CORE --reason "<why>"',
                f"    sae decision new {task} --from REVIEW-CORE-3",
                "  - reduce the requirement: append an amendment under ## Amendments in specs.md, then log it:",
                f'    sae log {task} amendment "<summary>" --id <AMEND-ID> --by human',
                "  - accept:",
                f'    sae merge {task} CORE --accept-review "<why>"',
                f'While you wait for the answer: sae ask {task} "<question>" --job CORE']), story)
            self.assertNotIn("close anyway", story)  # sae finish --override would wait for CORE's merge
        data = sb.json("next", "jthree")
        self.assertEqual([s["target"] for s in data["park_stories"]], ["CORE"])
        story = data["park_stories"][0]
        self.assertEqual((story["parked_by"], story["changes_rounds"], story["max_rounds"]), ("REVIEW-CORE-3", 3, 3))
        self.assertEqual(story["rounds"][0]["fixes"][0]["do_not"],
                         ["Do not touch the portal, because the portal is out of scope."])
        self.assertEqual(sb.json("status", "jthree")["park_stories"], data["park_stories"])
        # the owner raises the limit on the parked round: the next fix still gets the paragraph
        sb.sae("set", "jthree", "max-review-rounds=5")
        third = self.fix(sb, task, "jthree", "CORE-FIX-3", "CORE")
        self.assertIn("FIX 3 of CORE. CORE parks for the owner after review round 5.", third["prompt"])
        self.assertEqual(sb.json("next", "jthree")["park_stories"], [])

    def test_once_a_fix_got_the_paragraph_later_fixes_get_it_after_a_raise(self):
        sb = self.sandbox()
        task = self.job_task(sb, "jsticky", 2)
        self.review_round(sb, task, "jsticky", "REVIEW-CORE", "CORE", [("A", "a")])
        self.assertIn("FIX 1 of CORE", self.fix(sb, task, "jsticky", "CORE-FIX-1", "CORE")["prompt"])
        sb.sae("set", "jsticky", "max-review-rounds=8")  # before round 2: no park
        self.review_round(sb, task, "jsticky", "REVIEW-CORE-2", "CORE", [("B", "b")])
        self.assertIn("FIX 2 of CORE. CORE parks for the owner after review round 8.",
                      self.fix(sb, task, "jsticky", "CORE-FIX-2", "CORE")["prompt"])

    def test_one_round_every_fix_gets_the_paragraph(self):
        sb = self.sandbox()
        task = self.job_task(sb, "jone", 1)
        parked = self.review_round(sb, task, "jone", "REVIEW-CORE", "CORE", [("A", "a")])
        self.assertIn(PARK_OPENING, parked["collect"])
        first = self.fix(sb, task, "jone", "CORE-FIX-1", "CORE")
        self.assertIn("FIX 1 of CORE. CORE parks for the owner after review round 2.", first["prompt"])


class IntegrationApproachCheckTests(GuidanceCase):
    def test_three_integration_rounds_paragraph_and_task_story(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "ithree")
        sb.sae("set", "ithree", "max-review-rounds=3")
        self.review_round(sb, task, "ithree", "REVIEW-INTEGRATION", "integration", [("Two retry rules", "One retry helper")])
        first = self.fix(sb, task, "ithree", "INTEGRATION-FIX-1", "REVIEW-INTEGRATION",
                         limits=["Never change the API, because clients depend on it."], summary="one helper")
        self.assertNotIn(PARAGRAPH, first["prompt"])
        self.review_round(sb, task, "ithree", "REVIEW-INTEGRATION-2", "integration", [("Retry in LEFT", "Call the helper")])
        second = self.fix(sb, task, "ithree", "INTEGRATION-FIX-2", "REVIEW-INTEGRATION-2")
        self.assertIn("FIX 2 of REVIEW-INTEGRATION. REVIEW-INTEGRATION parks for the owner after review round 3.",
                      second["prompt"])
        parked = self.review_round(sb, task, "ithree", "REVIEW-INTEGRATION-3", "integration", [("Retry in RIGHT", "Same")])
        self.assertIn(PARK_OPENING + "\nThe task is parked: REVIEW-INTEGRATION-3", parked["collect"])
        self.assertNotIn("Options:", parked["collect"])
        for command in ("next", "status"):
            text = sb.sae(command, "ithree").stdout
            self.assertEqual(text.count(PARK_OPENING), 1, text)
            story = text[text.index(PARK_OPENING):]
            self.assertIn("The task is parked for the user: REVIEW-INTEGRATION-3", story)
            self.assertIn("Task: ithree", story)
            self.assertIn("Round 1 — REVIEW-INTEGRATION: changes-required\n  Finding: Two retry rules\n"
                          "    Suggested fix: One retry helper\n  Fix INTEGRATION-FIX-1 (done): one helper\n"
                          "    Limit: Never change the API, because clients depend on it.", story)
            self.assertIn("\n".join([
                "  - change the approach:",  # no drop: every writer is merged before the integration review
                f"    sae decision new {task} --from REVIEW-INTEGRATION-3",
                "  - reduce the requirement: append an amendment under ## Amendments in specs.md, then log it:"]), story)
            self.assertNotIn("<ID>", story)
            self.assertIn(f'    sae accept-review {task} REVIEW-INTEGRATION-3 --reason "<why>"', story)
            self.assertIn(f'  - close anyway:\n    sae finish {task} --override "<reason>"', story)
        self.assertEqual(sb.json("next", "ithree")["park_stories"][0]["target"], "integration")

    def test_one_round_the_fix_after_the_park_gets_the_paragraph(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "ione")
        sb.sae("set", "ione", "max-review-rounds=1")
        parked = self.review_round(sb, task, "ione", "REVIEW-INTEGRATION", "integration", [("A", "a")])
        self.assertIn(OPENING, parked["collect"])
        first = self.fix(sb, task, "ione", "INTEGRATION-FIX-1", "REVIEW-INTEGRATION")
        self.assertIn("FIX 1 of REVIEW-INTEGRATION. REVIEW-INTEGRATION parks for the owner after review round 2.",
                      first["prompt"])


class ApproachProposalTests(GuidanceCase):
    def test_pointer_and_collect_line_with_and_without_the_section(self):
        sb = self.sandbox()
        task = self.job_task(sb, "jprop", 5)
        self.review_round(sb, task, "jprop", "REVIEW-CORE", "CORE", [("A", "a")])
        plain = self.fix(sb, task, "jprop", "CORE-FIX-1", "CORE", proposal="")  # template comment only
        self.assertNotIn(COLLECT_PROPOSAL, plain["collect"])
        round2 = self.review_round(sb, task, "jprop", "REVIEW-CORE-2", "CORE", [("B", "b")])
        self.assertNotIn(POINTER, round2["prompt"])
        with_section = self.fix(sb, task, "jprop", "CORE-FIX-2", "CORE",
                                proposal="Store the status once; every reader calls one function.")
        path = sb.task_dir(task) / "jobs" / "CORE-FIX-2.result.md"
        self.assertIn(f"Approach proposal in {path}: {COLLECT_PROPOSAL}", with_section["collect"])
        round3 = self.review_round(sb, task, "jprop", "REVIEW-CORE-3", "CORE", [], verdict="pass")
        self.assertIn(f"{POINTER} {path}", round3["prompt"])
        self.assertNotIn("CORE-FIX-1.result.md", round3["prompt"].split(POINTER, 1)[1].split("\n", 1)[0])

    def test_integration_round_points_to_the_fix_proposal(self):
        sb = self.sandbox()
        task = self.integration_task(sb, "iprop")
        self.review_round(sb, task, "iprop", "REVIEW-INTEGRATION", "integration", [("A", "a")])
        self.fix(sb, task, "iprop", "INTEGRATION-FIX-1", "REVIEW-INTEGRATION", proposal="One helper for both.")
        prompt = sb.json("dispatch", "iprop", "REVIEW-INTEGRATION-2")["prompt"]
        self.assertIn(f"{POINTER} {sb.task_dir(task) / 'jobs' / 'INTEGRATION-FIX-1.result.md'}", prompt)


if __name__ == "__main__":
    unittest.main()
