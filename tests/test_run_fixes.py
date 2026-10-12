"""Run fixes: a later passing review ends a park, collect counts disputed findings (not their
parts), the owner merges a repository's first task without a manual step.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [PARKED-THEN-PASSED], [DISPUTE-COUNT], [OWNER-MERGE-FIRST-TASK], [DECISION-MERGE-CLEANUP].
"""

from __future__ import annotations

import json
import sys
import unittest

from saetest import SCRIPTS, Sandbox, SaeTestCase, dispatch_workspace

sys.path.insert(0, str(SCRIPTS))
from sae_lib.reviews import disputed_findings  # noqa: E402


def run_writer(sb: Sandbox, task: str, slug: str, job: str) -> str:
    ws = dispatch_workspace(sb, task, job)
    sb.work(ws, f"{job.lower()}.txt", f"{job}\n", f"{job}: work")
    sb.result(task, f"jobs/{job}.result.md", status="done", summary=job, validation="pass", changes="made")
    return sb.sae("collect", slug, job).stdout


def review(sb: Sandbox, task: str, slug: str, review_id: str, target: str, verdict: str) -> str:
    sb.sae("dispatch", slug, review_id)
    sb.result(task, f"reviews/{review_id}.md", target=target, verdict=verdict)
    return sb.sae("collect", slug, review_id).stdout


class ParkedThenPassedTests(SaeTestCase):
    def three_rounds(self, sb: Sandbox, slug: str, *, old_sae_park: bool) -> str:
        """CORE: review fails, fix, review fails (parked), fix, review passes."""
        task = sb.new_task(slug, slug)
        sb.sae("job", "add", slug, "CORE", "--kind", "implementation")
        sb.job_file(task, "CORE")
        sb.approve_plan(slug)
        sb.sae("start", slug)
        run_writer(sb, task, slug, "CORE")
        review(sb, task, slug, "REVIEW-CORE", "CORE", "changes-required")
        for n, round_id in ((1, "REVIEW-CORE-2"), (2, "REVIEW-CORE-3")):
            fix = f"CORE-FIX-{n}"
            sb.sae("job", "add", slug, fix, "--kind", "implementation", "--fix-of", "CORE", "--reason", "fix")
            sb.job_file(task, fix)
            self.assertIn(f"Added {round_id}", run_writer(sb, task, slug, fix))
            if round_id == "REVIEW-CORE-2":
                review(sb, task, slug, round_id, "CORE", "changes-required")
                self.assertEqual(sb.state(task)["jobs"]["CORE"]["status"], "parked")
        sb.sae("dispatch", slug, "REVIEW-CORE-3")
        if old_sae_park:
            # A task that an older sae ran: the target stayed parked while its next round ran.
            state_path = sb.task_dir(task) / "state.json"
            state = json.loads(state_path.read_text())
            state["jobs"]["CORE"]["status"] = "parked"
            state_path.write_text(json.dumps(state))
        sb.result(task, "reviews/REVIEW-CORE-3.md", target="CORE", verdict="pass")
        out = sb.sae("collect", slug, "REVIEW-CORE-3").stdout
        self.assertIn("CORE: merged", out)
        jobs = sb.state(task)["jobs"]
        self.assertEqual(jobs["CORE"]["status"], "done")
        self.assertTrue(jobs["CORE"]["merged"] and jobs["CORE-FIX-1"]["merged"] and jobs["CORE-FIX-2"]["merged"])
        self.assertEqual(sb.json("next", slug)["parked"], [])
        return out

    def test_fail_fail_pass_ends_done_and_merged(self):
        sb = self.sandbox(points=["all-jobs"])
        self.three_rounds(sb, "rounds", old_sae_park=False)

    def test_a_parked_target_whose_later_round_passes_is_done(self):
        sb = self.sandbox(points=["all-jobs"])
        out = self.three_rounds(sb, "oldpark", old_sae_park=True)
        self.assertIn("CORE is no longer parked: REVIEW-CORE-3 passed.", out)


class DisputeCountTests(unittest.TestCase):
    def count(self, section: str) -> int:
        return disputed_findings("# Result\n\n## Disputed findings\n" + section + "\n## Risks\n- none\n")

    def test_a_finding_heading_with_subsections_counts_once(self):
        self.assertEqual(self.count("### Finding 1: the cache is shared\n#### Reason\nIt is.\n"
                                    "#### Evidence\n- cache.py:12\n- cache.py:40\n"), 1)

    def test_two_finding_headings_count_two(self):
        self.assertEqual(self.count("### Finding 1\n#### Reason\nx\n### Finding 4\n#### Reason\ny\n"), 2)

    def test_a_list_item_with_nested_evidence_counts_once(self):
        self.assertEqual(self.count("- Finding 2: the cache is not shared.\n  - Evidence: cache.py:12\n"
                                    "  - Evidence: one instance per process\n"), 1)

    def test_top_level_items_without_headings(self):
        self.assertEqual(self.count("- Finding 2: wrong.\n- Finding 4: handled.\n"), 2)
        self.assertEqual(self.count("<!-- Only when your job answers a review. -->\nNone.\n"), 0)


class OwnerMergeFirstTaskTests(SaeTestCase):
    def test_identical_copies_go_and_a_differing_file_stays(self):
        sb = self.sandbox()
        task = sb.new_task("First", "first")
        repo_file = sb.repo / ".tasks" / "repo" / "profile.md"
        repo_file.parent.mkdir(parents=True, exist_ok=True)
        repo_file.write_text("# Profile\n")
        sb.sae("job", "add", "first", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        sb.approve_plan("first")
        sb.sae("start", "first")
        run_writer(sb, task, "first", "ONE")
        repo_file.write_text("# Profile\nedited at home after start\n")  # differs from the task record
        out = sb.sae("finish", "first").stdout
        self.assertIn("Removed untracked copies", out)
        for name in (".gitignore", ".gitattributes"):
            self.assertFalse((sb.repo / ".tasks" / name).exists(), name)
        self.assertIn("move these untracked files", out)
        self.assertIn(".tasks/repo/profile.md", out)
        self.assertEqual(repo_file.read_text(), "# Profile\nedited at home after start\n")
        # A writing command before the merge does not bring the copies back: the task branch has them.
        sb.sae("new", "Next", "--slug", "next")
        self.assertFalse((sb.repo / ".tasks" / ".gitignore").exists())
        # The owner moves the one differing file aside, as told, and merges.
        aside = sb.tmp / "profile.md"
        repo_file.rename(aside)
        sb.git("merge", "-q", "--no-ff", "-m", "merge", f"task/{task}")
        self.assertTrue((sb.repo / ".tasks" / ".gitignore").is_file())
        self.assertEqual(aside.read_text(), "# Profile\nedited at home after start\n")


if __name__ == "__main__":
    unittest.main()
